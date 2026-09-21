const EventEmitter = require('events');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegStatic = require('ffmpeg-static');
const sharp = require('sharp');
const moment = require('moment');

ffmpeg.setFfmpegPath(ffmpegStatic);

class ShotByShotEditor extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        this.projects = new Map();
        this.sessions = new Map();
        
        this.editModes = {
            FRAME_BY_FRAME: 'frame_by_frame',
            SHOT_SEQUENCE: 'shot_sequence',
            TIMELINE: 'timeline',
            MULTI_TRACK: 'multi_track'
        };
        
        this.shotTypes = {
            ESTABLISHING: 'establishing',
            CLOSE_UP: 'close_up',
            WIDE_SHOT: 'wide_shot',
            MEDIUM_SHOT: 'medium_shot',
            CUT_AWAY: 'cut_away',
            INSERT: 'insert',
            REACTION: 'reaction',
            TRANSITION: 'transition'
        };
        
        this.transitionTypes = {
            CUT: 'cut',
            FADE: 'fade',
            DISSOLVE: 'dissolve',
            WIPE: 'wipe',
            ZOOM: 'zoom',
            SLIDE: 'slide'
        };
        
        this.setupEventListeners();
        this.logger.info('Shot-by-Shot Editor service initialized');
    }
    
    setupEventListeners() {
        this.on('project_created', (data) => {
            this.io.to(`project_${data.projectId}`).emit('project_created', data);
        });
        
        this.on('shot_added', (data) => {
            this.io.to(`project_${data.projectId}`).emit('shot_added', data);
        });
        
        this.on('shot_edited', (data) => {
            this.io.to(`project_${data.projectId}`).emit('shot_edited', data);
        });
        
        this.on('timeline_updated', (data) => {
            this.io.to(`project_${data.projectId}`).emit('timeline_updated', data);
        });
    }
    
    async createProject(projectData) {
        try {
            const projectId = uuidv4();
            const project = {
                id: projectId,
                name: projectData.name || 'Untitled Project',
                description: projectData.description || '',
                frameRate: projectData.frameRate || 30,
                resolution: projectData.resolution || { width: 1920, height: 1080 },
                editMode: projectData.editMode || this.editModes.TIMELINE,
                shots: [],
                timeline: {
                    tracks: [
                        { id: 'video_1', type: 'video', name: 'Video Track 1', clips: [] },
                        { id: 'audio_1', type: 'audio', name: 'Audio Track 1', clips: [] },
                        { id: 'audio_2', type: 'audio', name: 'Audio Track 2', clips: [] },
                        { id: 'effects_1', type: 'effects', name: 'Effects Track 1', clips: [] }
                    ],
                    duration: 0,
                    playhead: 0
                },
                metadata: {
                    created: new Date(),
                    lastModified: new Date(),
                    version: '1.0.0',
                    author: projectData.author || 'Unknown',
                    tags: projectData.tags || []
                },
                settings: {
                    autoSave: true,
                    snapToGrid: true,
                    gridSize: 1000, // 1 second in milliseconds
                    previewQuality: 'medium'
                }
            };
            
            this.projects.set(projectId, project);
            await this.redis.setEx(`editor_project:${projectId}`, 3600, JSON.stringify(project));
            
            this.emit('project_created', { projectId, project });
            this.logger.info(`Shot-by-shot project created: ${projectId}`);
            
            return { success: true, projectId, project };
        } catch (error) {
            this.logger.error('Create project error:', error);
            throw error;
        }
    }
    
    async addShot(shotData) {
        try {
            const { projectId, mediaFile, shotType, position, metadata } = shotData;
            const project = await this.getProject(projectId);
            
            if (!project) {
                throw new Error(`Project ${projectId} not found`);
            }
            
            const shotId = uuidv4();
            const shot = {
                id: shotId,
                mediaFile: mediaFile,
                shotType: shotType || this.shotTypes.MEDIUM_SHOT,
                position: position || { start: 0, end: 5000 }, // milliseconds
                metadata: {
                    duration: metadata?.duration || 5000,
                    frameCount: metadata?.frameCount || 150,
                    originalFile: mediaFile,
                    thumbnail: null,
                    created: new Date(),
                    ...metadata
                },
                effects: [],
                transitions: {
                    in: { type: this.transitionTypes.CUT, duration: 0 },
                    out: { type: this.transitionTypes.CUT, duration: 0 }
                },
                properties: {
                    opacity: 1.0,
                    volume: 1.0,
                    speed: 1.0,
                    stabilization: false,
                    colorCorrection: {
                        brightness: 0,
                        contrast: 0,
                        saturation: 0,
                        hue: 0
                    }
                }
            };
            
            // Generate thumbnail for the shot
            if (mediaFile && fs.existsSync) {
                try {
                    const thumbnailPath = await this.generateShotThumbnail(mediaFile, shotId);
                    shot.metadata.thumbnail = thumbnailPath;
                } catch (thumbError) {
                    this.logger.warn(`Failed to generate thumbnail for shot ${shotId}:`, thumbError);
                }
            }
            
            project.shots.push(shot);
            project.metadata.lastModified = new Date();
            
            // Update timeline if in timeline mode
            if (project.editMode === this.editModes.TIMELINE) {
                const videoTrack = project.timeline.tracks.find(t => t.type === 'video');
                if (videoTrack) {
                    const clip = {
                        id: uuidv4(),
                        shotId: shotId,
                        start: project.timeline.duration,
                        duration: shot.metadata.duration,
                        trackId: videoTrack.id
                    };
                    videoTrack.clips.push(clip);
                    project.timeline.duration += shot.metadata.duration;
                }
            }
            
            await this.updateProject(project);
            
            this.emit('shot_added', { projectId, shotId, shot });
            this.logger.info(`Shot added to project ${projectId}: ${shotId}`);
            
            return { success: true, shotId, shot };
        } catch (error) {
            this.logger.error('Add shot error:', error);
            throw error;
        }
    }
    
    async editShot(shotId, editData) {
        try {
            const { projectId, properties, effects, transitions, metadata } = editData;
            const project = await this.getProject(projectId);
            
            if (!project) {
                throw new Error(`Project ${projectId} not found`);
            }
            
            const shot = project.shots.find(s => s.id === shotId);
            if (!shot) {
                throw new Error(`Shot ${shotId} not found in project ${projectId}`);
            }
            
            // Update shot properties
            if (properties) {
                shot.properties = { ...shot.properties, ...properties };
            }
            
            // Update effects
            if (effects) {
                shot.effects = effects;
            }
            
            // Update transitions
            if (transitions) {
                shot.transitions = { ...shot.transitions, ...transitions };
            }
            
            // Update metadata
            if (metadata) {
                shot.metadata = { ...shot.metadata, ...metadata };
            }
            
            project.metadata.lastModified = new Date();
            await this.updateProject(project);
            
            this.emit('shot_edited', { projectId, shotId, shot, changes: editData });
            this.logger.info(`Shot edited in project ${projectId}: ${shotId}`);
            
            return { success: true, shotId, shot };
        } catch (error) {
            this.logger.error('Edit shot error:', error);
            throw error;
        }
    }
    
    async generateShotThumbnail(mediaFile, shotId) {
        return new Promise((resolve, reject) => {
            const thumbnailDir = '/tmp/thumbnails';
            const thumbnailPath = path.join(thumbnailDir, `${shotId}_thumb.jpg`);
            
            // Ensure thumbnail directory exists
            fs.mkdir(thumbnailDir, { recursive: true }).then(() => {
                ffmpeg(mediaFile)
                    .screenshots({
                        count: 1,
                        folder: thumbnailDir,
                        filename: `${shotId}_thumb.jpg`,
                        timemarks: ['5%']
                    })
                    .on('end', () => {
                        resolve(thumbnailPath);
                    })
                    .on('error', (error) => {
                        reject(error);
                    });
            }).catch(reject);
        });
    }
    
    async updateTimeline(projectId, timelineData) {
        try {
            const project = await this.getProject(projectId);
            
            if (!project) {
                throw new Error(`Project ${projectId} not found`);
            }
            
            project.timeline = { ...project.timeline, ...timelineData };
            project.metadata.lastModified = new Date();
            
            await this.updateProject(project);
            
            this.emit('timeline_updated', { projectId, timeline: project.timeline });
            this.logger.info(`Timeline updated for project ${projectId}`);
            
            return { success: true, timeline: project.timeline };
        } catch (error) {
            this.logger.error('Update timeline error:', error);
            throw error;
        }
    }
    
    async addTrack(projectId, trackData) {
        try {
            const project = await this.getProject(projectId);
            
            if (!project) {
                throw new Error(`Project ${projectId} not found`);
            }
            
            const trackId = uuidv4();
            const track = {
                id: trackId,
                type: trackData.type || 'video',
                name: trackData.name || `${trackData.type} Track`,
                clips: [],
                muted: false,
                locked: false,
                visible: true
            };
            
            project.timeline.tracks.push(track);
            project.metadata.lastModified = new Date();
            
            await this.updateProject(project);
            
            this.emit('track_added', { projectId, trackId, track });
            this.logger.info(`Track added to project ${projectId}: ${trackId}`);
            
            return { success: true, trackId, track };
        } catch (error) {
            this.logger.error('Add track error:', error);
            throw error;
        }
    }
    
    async renderProject(projectId, renderOptions = {}) {
        try {
            const project = await this.getProject(projectId);
            
            if (!project) {
                throw new Error(`Project ${projectId} not found`);
            }
            
            const renderId = uuidv4();
            const outputPath = renderOptions.outputPath || `/tmp/renders/${projectId}_${renderId}.mp4`;
            
            // Create render directory
            await fs.mkdir(path.dirname(outputPath), { recursive: true });
            
            const renderConfig = {
                id: renderId,
                projectId: projectId,
                status: 'rendering',
                progress: 0,
                outputPath: outputPath,
                startTime: new Date(),
                options: {
                    format: renderOptions.format || 'mp4',
                    quality: renderOptions.quality || 'high',
                    resolution: renderOptions.resolution || project.resolution,
                    frameRate: renderOptions.frameRate || project.frameRate,
                    codec: renderOptions.codec || 'h264'
                }
            };
            
            await this.redis.setEx(`render:${renderId}`, 3600, JSON.stringify(renderConfig));
            
            // Start rendering process
            this.startRenderProcess(project, renderConfig);
            
            this.logger.info(`Project render started: ${projectId} -> ${renderId}`);
            
            return { success: true, renderId, renderConfig };
        } catch (error) {
            this.logger.error('Render project error:', error);
            throw error;
        }
    }
    
    async startRenderProcess(project, renderConfig) {
        try {
            const outputCommand = ffmpeg();
            
            // Add video inputs from timeline
            const videoTrack = project.timeline.tracks.find(t => t.type === 'video');
            if (videoTrack && videoTrack.clips.length > 0) {
                for (const clip of videoTrack.clips) {
                    const shot = project.shots.find(s => s.id === clip.shotId);
                    if (shot && shot.mediaFile) {
                        outputCommand.input(shot.mediaFile);
                    }
                }
            }
            
            // Configure output settings
            outputCommand
                .size(`${renderConfig.options.resolution.width}x${renderConfig.options.resolution.height}`)
                .fps(renderConfig.options.frameRate)
                .videoCodec(renderConfig.options.codec === 'h264' ? 'libx264' : 'libx265')
                .audioCodec('aac')
                .format(renderConfig.options.format);
            
            // Apply quality settings
            if (renderConfig.options.quality === 'high') {
                outputCommand.videoBitrate('5000k').audioBitrate('256k');
            } else if (renderConfig.options.quality === 'medium') {
                outputCommand.videoBitrate('2500k').audioBitrate('128k');
            } else {
                outputCommand.videoBitrate('1000k').audioBitrate('96k');
            }
            
            outputCommand
                .output(renderConfig.outputPath)
                .on('progress', (progress) => {
                    renderConfig.progress = Math.round(progress.percent || 0);
                    this.redis.setEx(`render:${renderConfig.id}`, 3600, JSON.stringify(renderConfig));
                    this.io.to(`project_${project.id}`).emit('render_progress', {
                        renderId: renderConfig.id,
                        progress: renderConfig.progress
                    });
                })
                .on('end', async () => {
                    renderConfig.status = 'completed';
                    renderConfig.endTime = new Date();
                    renderConfig.progress = 100;
                    await this.redis.setEx(`render:${renderConfig.id}`, 3600, JSON.stringify(renderConfig));
                    this.io.to(`project_${project.id}`).emit('render_completed', renderConfig);
                    this.logger.info(`Render completed: ${renderConfig.id}`);
                })
                .on('error', async (error) => {
                    renderConfig.status = 'failed';
                    renderConfig.error = error.message;
                    renderConfig.endTime = new Date();
                    await this.redis.setEx(`render:${renderConfig.id}`, 3600, JSON.stringify(renderConfig));
                    this.io.to(`project_${project.id}`).emit('render_failed', renderConfig);
                    this.logger.error(`Render failed: ${renderConfig.id}`, error);
                })
                .run();
        } catch (error) {
            this.logger.error('Start render process error:', error);
            throw error;
        }
    }
    
    async getProject(projectId) {
        try {
            if (this.projects.has(projectId)) {
                return this.projects.get(projectId);
            }
            
            const cached = await this.redis.get(`editor_project:${projectId}`);
            if (cached) {
                const project = JSON.parse(cached);
                this.projects.set(projectId, project);
                return project;
            }
            
            return null;
        } catch (error) {
            this.logger.error('Get project error:', error);
            throw error;
        }
    }
    
    async updateProject(project) {
        try {
            this.projects.set(project.id, project);
            await this.redis.setEx(`editor_project:${project.id}`, 3600, JSON.stringify(project));
        } catch (error) {
            this.logger.error('Update project error:', error);
            throw error;
        }
    }
    
    async getStats() {
        try {
            const stats = {
                totalProjects: this.projects.size,
                activeSessions: this.sessions.size,
                editModes: this.editModes,
                shotTypes: this.shotTypes,
                transitionTypes: this.transitionTypes,
                timestamp: new Date()
            };
            
            return stats;
        } catch (error) {
            this.logger.error('Get stats error:', error);
            throw error;
        }
    }
}

module.exports = ShotByShotEditor;