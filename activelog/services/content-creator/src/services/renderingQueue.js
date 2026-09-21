const EventEmitter = require('events');
const Queue = require('bull');
const { v4: uuidv4 } = require('uuid');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegStatic = require('ffmpeg-static');
const fs = require('fs').promises;
const path = require('path');

ffmpeg.setFfmpegPath(ffmpegStatic);

class RenderingQueue extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        // Initialize render queues with different priorities
        this.queues = {
            high: new Queue('high priority renders', { redis: { port: 6379, host: 'localhost' } }),
            normal: new Queue('normal priority renders', { redis: { port: 6379, host: 'localhost' } }),
            low: new Queue('low priority renders', { redis: { port: 6379, host: 'localhost' } })
        };
        
        this.renderTypes = {
            PREVIEW: 'preview',
            FINAL: 'final',
            EXPORT: 'export',
            THUMBNAIL: 'thumbnail',
            PROXY: 'proxy'
        };
        
        this.priorities = {
            URGENT: 1,
            HIGH: 2,
            NORMAL: 3,
            LOW: 4,
            BATCH: 5
        };
        
        this.renderFormats = {
            MP4_H264: 'mp4_h264',
            MP4_H265: 'mp4_h265',
            WEBM: 'webm',
            MOV: 'mov',
            AVI: 'avi',
            MKV: 'mkv'
        };
        
        this.qualityPresets = {
            ULTRA: { bitrate: '10000k', crf: 18, preset: 'slow' },
            HIGH: { bitrate: '5000k', crf: 23, preset: 'medium' },
            MEDIUM: { bitrate: '2500k', crf: 28, preset: 'fast' },
            LOW: { bitrate: '1000k', crf: 32, preset: 'faster' },
            PROXY: { bitrate: '500k', crf: 35, preset: 'ultrafast' }
        };
        
        this.activeRenders = new Map();
        this.renderHistory = [];
        this.setupQueues();
        this.setupEventListeners();
        
        this.logger.info('Rendering Queue service initialized');
    }
    
    setupQueues() {
        // Process jobs for each queue
        Object.keys(this.queues).forEach(priority => {
            this.queues[priority].process('render', this.processRenderJob.bind(this));
            
            this.queues[priority].on('completed', (job, result) => {
                this.handleJobCompleted(job, result);
            });
            
            this.queues[priority].on('failed', (job, error) => {
                this.handleJobFailed(job, error);
            });
            
            this.queues[priority].on('progress', (job, progress) => {
                this.handleJobProgress(job, progress);
            });
        });
    }
    
    setupEventListeners() {
        this.on('render_submitted', (data) => {
            this.io.emit('render_submitted', data);
        });
        
        this.on('render_started', (data) => {
            this.io.to(`render_queue_${data.queueId}`).emit('render_started', data);
        });
        
        this.on('render_progress', (data) => {
            this.io.to(`render_queue_${data.queueId}`).emit('render_progress', data);
        });
        
        this.on('render_completed', (data) => {
            this.io.to(`render_queue_${data.queueId}`).emit('render_completed', data);
        });
        
        this.on('render_failed', (data) => {
            this.io.to(`render_queue_${data.queueId}`).emit('render_failed', data);
        });
    }
    
    async submitRenderJob(jobData) {
        try {
            const jobId = uuidv4();
            const {
                projectId,
                type,
                priority,
                format,
                quality,
                resolution,
                frameRate,
                inputFiles,
                outputPath,
                timeline,
                effects,
                metadata
            } = jobData;
            
            const renderJob = {
                id: jobId,
                projectId: projectId || 'unknown',
                type: type || this.renderTypes.FINAL,
                priority: priority || this.priorities.NORMAL,
                format: format || this.renderFormats.MP4_H264,
                quality: quality || 'HIGH',
                settings: {
                    resolution: resolution || { width: 1920, height: 1080 },
                    frameRate: frameRate || 30,
                    outputPath: outputPath || `/tmp/renders/${jobId}.mp4`,
                    inputFiles: inputFiles || [],
                    timeline: timeline || null,
                    effects: effects || [],
                    ...this.qualityPresets[quality || 'HIGH']
                },
                status: 'queued',
                progress: 0,
                estimatedDuration: this.estimateRenderDuration(jobData),
                metadata: {
                    submitted: new Date(),
                    submittedBy: metadata?.submittedBy || 'system',
                    tags: metadata?.tags || [],
                    ...metadata
                }
            };
            
            // Determine queue based on priority
            const queueName = this.getQueueForPriority(priority);
            const queue = this.queues[queueName];
            
            // Submit job to appropriate queue
            const bullJob = await queue.add('render', renderJob, {
                priority: priority || this.priorities.NORMAL,
                delay: 0,
                attempts: 3,
                backoff: {
                    type: 'exponential',
                    delay: 2000
                },
                removeOnComplete: 50,
                removeOnFail: 20
            });
            
            renderJob.bullJobId = bullJob.id;
            
            await this.redis.setEx(`render_job:${jobId}`, 7200, JSON.stringify(renderJob));
            
            this.emit('render_submitted', { jobId, renderJob, queueName });
            this.logger.info(`Render job submitted: ${jobId} in ${queueName} queue`);
            
            return { success: true, jobId, renderJob };
        } catch (error) {
            this.logger.error('Submit render job error:', error);
            throw error;
        }
    }
    
    async processRenderJob(job) {
        const renderJob = job.data;
        const jobId = renderJob.id;
        
        try {
            this.logger.info(`Starting render job: ${jobId}`);
            
            renderJob.status = 'rendering';
            renderJob.startTime = new Date();
            this.activeRenders.set(jobId, renderJob);
            
            await this.updateRenderJob(renderJob);
            this.emit('render_started', { jobId, renderJob });
            
            // Create output directory
            await fs.mkdir(path.dirname(renderJob.settings.outputPath), { recursive: true });
            
            const result = await this.executeRender(renderJob, job);
            
            renderJob.status = 'completed';
            renderJob.endTime = new Date();
            renderJob.progress = 100;
            renderJob.outputFile = result.outputPath;
            renderJob.fileSize = result.fileSize;
            
            this.activeRenders.delete(jobId);
            this.renderHistory.push({ ...renderJob, completedAt: new Date() });
            
            await this.updateRenderJob(renderJob);
            this.emit('render_completed', { jobId, renderJob, result });
            
            return result;
        } catch (error) {
            renderJob.status = 'failed';
            renderJob.error = error.message;
            renderJob.endTime = new Date();
            
            this.activeRenders.delete(jobId);
            
            await this.updateRenderJob(renderJob);
            this.emit('render_failed', { jobId, renderJob, error: error.message });
            
            throw error;
        }
    }
    
    async executeRender(renderJob, bullJob) {
        return new Promise((resolve, reject) => {
            try {
                const { settings } = renderJob;
                let command = ffmpeg();
                
                // Add input files
                if (settings.inputFiles && settings.inputFiles.length > 0) {
                    settings.inputFiles.forEach(file => {
                        command = command.input(file);
                    });
                } else if (settings.timeline) {
                    // Process timeline-based render
                    command = this.processTimelineRender(command, settings.timeline);
                }
                
                // Configure video settings
                command = command
                    .size(`${settings.resolution.width}x${settings.resolution.height}`)
                    .fps(settings.frameRate)
                    .videoBitrate(settings.bitrate)
                    .videoCodec(this.getVideoCodec(renderJob.format));
                
                // Configure audio settings
                if (renderJob.type !== this.renderTypes.THUMBNAIL) {
                    command = command
                        .audioCodec('aac')
                        .audioBitrate('256k')
                        .audioChannels(2);
                }
                
                // Apply effects
                if (settings.effects && settings.effects.length > 0) {
                    command = this.applyEffects(command, settings.effects);
                }
                
                // Configure output format
                command = command.format(this.getOutputFormat(renderJob.format));
                
                // Apply quality preset
                if (settings.preset) {
                    command = command.preset(settings.preset);
                }
                
                if (settings.crf) {
                    command = command.addOption('-crf', settings.crf);
                }
                
                command
                    .output(settings.outputPath)
                    .on('start', (commandLine) => {
                        this.logger.info(`FFmpeg command: ${commandLine}`);
                    })
                    .on('progress', (progress) => {
                        const percent = Math.round(progress.percent || 0);
                        renderJob.progress = percent;
                        
                        bullJob.progress(percent);
                        this.updateRenderJob(renderJob);
                        
                        this.emit('render_progress', {
                            jobId: renderJob.id,
                            progress: percent,
                            timemarks: progress.timemark,
                            fps: progress.currentFps
                        });
                    })
                    .on('end', async () => {
                        try {
                            const stats = await fs.stat(settings.outputPath);
                            resolve({
                                success: true,
                                outputPath: settings.outputPath,
                                fileSize: stats.size,
                                duration: renderJob.estimatedDuration
                            });
                        } catch (statsError) {
                            reject(statsError);
                        }
                    })
                    .on('error', (error) => {
                        reject(error);
                    })
                    .run();
            } catch (error) {
                reject(error);
            }
        });
    }
    
    processTimelineRender(command, timeline) {
        // Process timeline tracks and clips
        const videoTrack = timeline.tracks.find(t => t.type === 'video');
        const audioTracks = timeline.tracks.filter(t => t.type === 'audio');
        
        if (videoTrack && videoTrack.clips.length > 0) {
            videoTrack.clips.forEach(clip => {
                if (clip.mediaFile) {
                    command = command.input(clip.mediaFile);
                }
            });
        }
        
        // Add complex filter for timeline assembly
        const filterComplex = this.buildTimelineFilter(timeline);
        if (filterComplex) {
            command = command.complexFilter(filterComplex);
        }
        
        return command;
    }
    
    buildTimelineFilter(timeline) {
        const filters = [];
        const videoTrack = timeline.tracks.find(t => t.type === 'video');
        
        if (videoTrack && videoTrack.clips.length > 1) {
            // Create concat filter for multiple clips
            const inputs = videoTrack.clips.map((_, i) => `[${i}:v]`).join('');
            filters.push(`${inputs}concat=n=${videoTrack.clips.length}:v=1:a=0[outv]`);
        }
        
        return filters.length > 0 ? filters : null;
    }
    
    applyEffects(command, effects) {
        const videoFilters = [];
        const audioFilters = [];
        
        effects.forEach(effect => {
            switch (effect.type) {
                case 'fade':
                    videoFilters.push(`fade=in:0:${effect.duration || 30}`);
                    break;
                case 'blur':
                    videoFilters.push(`boxblur=${effect.strength || 5}`);
                    break;
                case 'scale':
                    videoFilters.push(`scale=${effect.width}:${effect.height}`);
                    break;
                case 'colorbalance':
                    videoFilters.push(`colorbalance=rs=${effect.shadows || 0}:gs=${effect.midtones || 0}:bs=${effect.highlights || 0}`);
                    break;
                case 'volume':
                    audioFilters.push(`volume=${effect.level || 1.0}`);
                    break;
            }
        });
        
        if (videoFilters.length > 0) {
            command = command.videoFilter(videoFilters.join(','));
        }
        
        if (audioFilters.length > 0) {
            command = command.audioFilter(audioFilters.join(','));
        }
        
        return command;
    }
    
    getVideoCodec(format) {
        const codecs = {
            [this.renderFormats.MP4_H264]: 'libx264',
            [this.renderFormats.MP4_H265]: 'libx265',
            [this.renderFormats.WEBM]: 'libvpx-vp9',
            [this.renderFormats.MOV]: 'libx264',
            [this.renderFormats.AVI]: 'libx264',
            [this.renderFormats.MKV]: 'libx264'
        };
        
        return codecs[format] || 'libx264';
    }
    
    getOutputFormat(format) {
        const formats = {
            [this.renderFormats.MP4_H264]: 'mp4',
            [this.renderFormats.MP4_H265]: 'mp4',
            [this.renderFormats.WEBM]: 'webm',
            [this.renderFormats.MOV]: 'mov',
            [this.renderFormats.AVI]: 'avi',
            [this.renderFormats.MKV]: 'matroska'
        };
        
        return formats[format] || 'mp4';
    }
    
    getQueueForPriority(priority) {
        if (priority <= this.priorities.HIGH) return 'high';
        if (priority >= this.priorities.LOW) return 'low';
        return 'normal';
    }
    
    estimateRenderDuration(jobData) {
        const baseTime = 60; // 1 minute base
        let multiplier = 1;
        
        // Adjust based on quality
        if (jobData.quality === 'ULTRA') multiplier *= 3;
        else if (jobData.quality === 'HIGH') multiplier *= 2;
        else if (jobData.quality === 'LOW') multiplier *= 0.5;
        
        // Adjust based on resolution
        const pixels = (jobData.resolution?.width || 1920) * (jobData.resolution?.height || 1080);
        if (pixels > 2073600) multiplier *= 2; // 4K
        else if (pixels < 921600) multiplier *= 0.7; // 720p
        
        // Adjust based on effects
        if (jobData.effects && jobData.effects.length > 0) {
            multiplier *= (1 + jobData.effects.length * 0.3);
        }
        
        return Math.round(baseTime * multiplier);
    }
    
    async handleJobCompleted(job, result) {
        const renderJob = job.data;
        this.logger.info(`Render job completed: ${renderJob.id}`);
        
        // Clean up temporary files if needed
        await this.cleanupTempFiles(renderJob);
    }
    
    async handleJobFailed(job, error) {
        const renderJob = job.data;
        this.logger.error(`Render job failed: ${renderJob.id}`, error);
        
        // Clean up any partial files
        await this.cleanupFailedRender(renderJob);
    }
    
    async handleJobProgress(job, progress) {
        const renderJob = job.data;
        this.emit('render_progress', {
            jobId: renderJob.id,
            progress: progress
        });
    }
    
    async getQueueStatus(queueId) {
        try {
            const stats = {};
            
            for (const [priority, queue] of Object.entries(this.queues)) {
                const waiting = await queue.getWaiting();
                const active = await queue.getActive();
                const completed = await queue.getCompleted();
                const failed = await queue.getFailed();
                
                stats[priority] = {
                    waiting: waiting.length,
                    active: active.length,
                    completed: completed.length,
                    failed: failed.length
                };
            }
            
            return {
                success: true,
                queueId,
                stats,
                activeRenders: Array.from(this.activeRenders.values()),
                recentHistory: this.renderHistory.slice(-10),
                timestamp: new Date()
            };
        } catch (error) {
            this.logger.error('Get queue status error:', error);
            throw error;
        }
    }
    
    async cancelRenderJob(jobId) {
        try {
            const renderJob = await this.getRenderJob(jobId);
            if (!renderJob) {
                throw new Error(`Render job ${jobId} not found`);
            }
            
            // Find and cancel the Bull job
            for (const queue of Object.values(this.queues)) {
                const job = await queue.getJob(renderJob.bullJobId);
                if (job) {
                    await job.remove();
                    break;
                }
            }
            
            renderJob.status = 'cancelled';
            renderJob.endTime = new Date();
            this.activeRenders.delete(jobId);
            
            await this.updateRenderJob(renderJob);
            
            this.emit('render_cancelled', { jobId, renderJob });
            this.logger.info(`Render job cancelled: ${jobId}`);
            
            return { success: true, jobId };
        } catch (error) {
            this.logger.error('Cancel render job error:', error);
            throw error;
        }
    }
    
    async getRenderJob(jobId) {
        try {
            const cached = await this.redis.get(`render_job:${jobId}`);
            return cached ? JSON.parse(cached) : null;
        } catch (error) {
            this.logger.error('Get render job error:', error);
            return null;
        }
    }
    
    async updateRenderJob(renderJob) {
        try {
            await this.redis.setEx(`render_job:${renderJob.id}`, 7200, JSON.stringify(renderJob));
        } catch (error) {
            this.logger.error('Update render job error:', error);
        }
    }
    
    async cleanupTempFiles(renderJob) {
        try {
            // Clean up any temporary processing files
            if (renderJob.tempFiles) {
                for (const tempFile of renderJob.tempFiles) {
                    try {
                        await fs.unlink(tempFile);
                    } catch (unlinkError) {
                        this.logger.warn(`Failed to cleanup temp file: ${tempFile}`, unlinkError);
                    }
                }
            }
        } catch (error) {
            this.logger.warn('Cleanup temp files error:', error);
        }
    }
    
    async cleanupFailedRender(renderJob) {
        try {
            // Remove partial output file if it exists
            try {
                await fs.access(renderJob.settings.outputPath);
                await fs.unlink(renderJob.settings.outputPath);
            } catch (accessError) {
                // File doesn't exist, nothing to clean up
            }
            
            // Clean up temp files
            await this.cleanupTempFiles(renderJob);
        } catch (error) {
            this.logger.warn('Cleanup failed render error:', error);
        }
    }
    
    async getStats() {
        try {
            const stats = {
                renderTypes: this.renderTypes,
                priorities: this.priorities,
                renderFormats: this.renderFormats,
                qualityPresets: Object.keys(this.qualityPresets),
                activeRenders: this.activeRenders.size,
                totalProcessed: this.renderHistory.length,
                queues: {},
                timestamp: new Date()
            };
            
            // Get queue statistics
            for (const [priority, queue] of Object.entries(this.queues)) {
                stats.queues[priority] = {
                    waiting: await queue.getWaiting().then(jobs => jobs.length),
                    active: await queue.getActive().then(jobs => jobs.length),
                    completed: await queue.getCompleted().then(jobs => jobs.length),
                    failed: await queue.getFailed().then(jobs => jobs.length)
                };
            }
            
            return stats;
        } catch (error) {
            this.logger.error('Get stats error:', error);
            throw error;
        }
    }
}

module.exports = RenderingQueue;