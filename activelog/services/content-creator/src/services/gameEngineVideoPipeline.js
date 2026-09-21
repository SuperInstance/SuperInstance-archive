const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const ffmpeg = require('fluent-ffmpeg');
const path = require('path');
const fs = require('fs').promises;

class GameEngineVideoPipeline extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        // Supported game engines and their capture methods
        this.gameEngines = {
            'unity': {
                name: 'Unity Engine',
                capture_methods: ['screen_capture', 'unity_recorder', 'obs_integration'],
                supported_formats: ['mp4', 'mov', 'avi', 'mkv'],
                default_settings: {
                    resolution: '1920x1080',
                    framerate: 60,
                    bitrate: '10M',
                    codec: 'h264'
                },
                integration: {
                    api_endpoint: '/unity-capture',
                    event_hooks: ['scene_change', 'gameplay_event', 'ui_interaction']
                }
            },
            
            'unreal': {
                name: 'Unreal Engine',
                capture_methods: ['sequencer', 'screen_capture', 'movie_render_queue'],
                supported_formats: ['mp4', 'mov', 'exr_sequence', 'png_sequence'],
                default_settings: {
                    resolution: '3840x2160',
                    framerate: 24,
                    bitrate: '50M',
                    codec: 'prores'
                },
                integration: {
                    api_endpoint: '/unreal-capture',
                    event_hooks: ['level_stream', 'cinematic_event', 'blueprint_event']
                }
            },
            
            'godot': {
                name: 'Godot Engine',
                capture_methods: ['screen_capture', 'scene_recorder'],
                supported_formats: ['mp4', 'webm', 'ogv'],
                default_settings: {
                    resolution: '1920x1080',
                    framerate: 30,
                    bitrate: '8M',
                    codec: 'vp9'
                },
                integration: {
                    api_endpoint: '/godot-capture',
                    event_hooks: ['scene_ready', 'signal_emitted', 'node_event']
                }
            },
            
            'custom': {
                name: 'Custom Engine/Application',
                capture_methods: ['screen_capture', 'window_capture', 'api_capture'],
                supported_formats: ['mp4', 'mov', 'avi'],
                default_settings: {
                    resolution: '1920x1080',
                    framerate: 30,
                    bitrate: '5M',
                    codec: 'h264'
                },
                integration: {
                    api_endpoint: '/custom-capture',
                    event_hooks: ['custom_event']
                }
            }
        };
        
        // Capture session states
        this.captureStates = {
            'idle': 'Ready to start capture',
            'initializing': 'Setting up capture system',
            'recording': 'Actively recording gameplay',
            'paused': 'Recording paused',
            'stopping': 'Finalizing recording',
            'processing': 'Post-processing footage',
            'completed': 'Capture and processing complete',
            'error': 'Error occurred during capture'
        };
        
        // Post-processing workflows
        this.processingWorkflows = {
            'gameplay_highlight': {
                name: 'Gameplay Highlight Reel',
                description: 'Extract exciting moments and create highlight compilation',
                steps: [
                    'analyze_audio_peaks',
                    'detect_action_scenes',
                    'extract_highlights',
                    'add_transitions',
                    'apply_color_grading',
                    'add_music_overlay'
                ]
            },
            
            'tutorial_creation': {
                name: 'Tutorial Video Creation',
                description: 'Process gameplay into educational content',
                steps: [
                    'segment_by_actions',
                    'add_annotation_markers',
                    'insert_explanation_pauses',
                    'add_overlay_graphics',
                    'synchronize_voiceover',
                    'create_chapter_markers'
                ]
            },
            
            'livestream_vod': {
                name: 'Livestream VOD Processing',
                description: 'Convert livestream to on-demand content',
                steps: [
                    'remove_dead_air',
                    'enhance_audio_quality',
                    'add_chat_overlay',
                    'create_thumbnail_moments',
                    'generate_timestamps',
                    'optimize_for_platforms'
                ]
            },
            
            'cinematic_showcase': {
                name: 'Cinematic Game Showcase',
                description: 'Create movie-like presentation of gameplay',
                steps: [
                    'apply_cinematic_filters',
                    'add_dramatic_music',
                    'create_smooth_transitions',
                    'add_title_sequences',
                    'apply_color_grading',
                    'add_special_effects'
                ]
            }
        };
        
        // Active capture sessions
        this.activeSessions = new Map();
    }

    async startCapture(options = {}) {
        try {
            const sessionId = uuidv4();
            const gameEngine = options.game_engine || 'custom';
            const captureMethod = options.capture_method || 'screen_capture';
            
            if (!this.gameEngines[gameEngine]) {
                throw new Error(`Unsupported game engine: ${gameEngine}`);
            }
            
            const engineConfig = this.gameEngines[gameEngine];
            
            const captureSession = {
                id: sessionId,
                game_engine: gameEngine,
                capture_method: captureMethod,
                state: 'initializing',
                
                // Capture settings
                settings: {
                    ...engineConfig.default_settings,
                    ...options.settings,
                    output_path: options.output_path || `/tmp/captures/${sessionId}`,
                    project_name: options.project_name || `Capture_${sessionId}`,
                    description: options.description || ''
                },
                
                // Session metadata
                started_at: new Date(),
                game_info: {
                    title: options.game_title || 'Unknown Game',
                    version: options.game_version || '1.0',
                    scene: options.initial_scene || 'Main Menu',
                    player_info: options.player_info || {}
                },
                
                // Capture data
                recorded_segments: [],
                events: [],
                performance_metrics: {
                    fps: 0,
                    dropped_frames: 0,
                    cpu_usage: 0,
                    memory_usage: 0,
                    disk_usage: 0
                },
                
                // Processing queue
                post_processing: {
                    workflow: options.workflow || 'gameplay_highlight',
                    settings: options.processing_settings || {},
                    status: 'pending'
                }
            };
            
            // Initialize capture system
            await this._initializeCaptureSystem(captureSession);
            
            // Store session
            this.activeSessions.set(sessionId, captureSession);
            await this.redis.setex(
                `capture_session:${sessionId}`,
                86400 * 7, // 7 days
                JSON.stringify(captureSession)
            );
            
            // Start actual recording
            await this._startRecording(captureSession);
            
            this.logger.info(`Started capture session: ${sessionId}`);
            this.io.emit('capture_started', { 
                sessionId, 
                gameEngine,
                settings: captureSession.settings 
            });
            
            return {
                session_id: sessionId,
                status: 'recording',
                capture_info: {
                    game_engine: gameEngine,
                    method: captureMethod,
                    settings: captureSession.settings
                },
                estimated_file_size: this._estimateFileSize(captureSession.settings),
                stream_url: `http://localhost:8322/api/pipeline/stream/${sessionId}`
            };
            
        } catch (error) {
            this.logger.error('Error starting capture:', error);
            throw error;
        }
    }

    async stopCapture(options = {}) {
        try {
            const sessionId = options.session_id;
            
            if (!sessionId || !this.activeSessions.has(sessionId)) {
                throw new Error('Invalid or inactive capture session');
            }
            
            const session = this.activeSessions.get(sessionId);
            session.state = 'stopping';
            session.stopped_at = new Date();
            
            // Stop recording process
            await this._stopRecording(session);
            
            // Calculate session statistics
            const sessionStats = this._calculateSessionStats(session);
            session.statistics = sessionStats;
            
            // Queue for post-processing if requested
            if (options.auto_process !== false) {
                session.post_processing.status = 'queued';
                await this._queuePostProcessing(session);
            }
            
            session.state = 'completed';
            
            // Update storage
            await this.redis.setex(
                `capture_session:${sessionId}`,
                86400 * 7,
                JSON.stringify(session)
            );
            
            this.logger.info(`Stopped capture session: ${sessionId}`);
            this.io.emit('capture_stopped', { 
                sessionId, 
                duration: sessionStats.duration,
                fileSize: sessionStats.total_size 
            });
            
            return {
                session_id: sessionId,
                status: 'completed',
                statistics: sessionStats,
                recorded_segments: session.recorded_segments.length,
                next_steps: {
                    post_processing_available: true,
                    processing_workflows: Object.keys(this.processingWorkflows)
                }
            };
            
        } catch (error) {
            this.logger.error('Error stopping capture:', error);
            throw error;
        }
    }

    async processGameplayFootage(options = {}) {
        try {
            const processingId = uuidv4();
            const sessionId = options.session_id;
            const workflow = options.workflow || 'gameplay_highlight';
            
            if (!this.processingWorkflows[workflow]) {
                throw new Error(`Unknown processing workflow: ${workflow}`);
            }
            
            // Get capture session data
            const sessionData = await this.redis.get(`capture_session:${sessionId}`);
            if (!sessionData) {
                throw new Error('Capture session not found');
            }
            
            const session = JSON.parse(sessionData);
            const workflowConfig = this.processingWorkflows[workflow];
            
            const processingJob = {
                id: processingId,
                session_id: sessionId,
                workflow: workflow,
                workflow_config: workflowConfig,
                
                // Processing settings
                settings: {
                    ...options.settings,
                    output_format: options.output_format || 'mp4',
                    quality_preset: options.quality_preset || 'high',
                    target_duration: options.target_duration || 'auto',
                    aspect_ratio: options.aspect_ratio || '16:9'
                },
                
                // Job status
                status: 'processing',
                started_at: new Date(),
                current_step: 0,
                total_steps: workflowConfig.steps.length,
                
                // Output information
                output: {
                    files: [],
                    metadata: {},
                    preview_url: null,
                    download_url: null
                },
                
                // Progress tracking
                progress: {
                    percentage: 0,
                    current_operation: 'Initializing...',
                    estimated_time_remaining: 0,
                    processed_segments: 0
                }
            };
            
            // Start processing workflow
            await this._executeProcessingWorkflow(processingJob, session);
            
            // Store processing job
            await this.redis.setex(
                `processing_job:${processingId}`,
                86400 * 3, // 3 days
                JSON.stringify(processingJob)
            );
            
            this.logger.info(`Started processing: ${workflow} for session ${sessionId}`);
            this.io.emit('processing_started', { 
                processingId, 
                sessionId,
                workflow: workflowConfig.name 
            });
            
            return {
                processing_id: processingId,
                workflow: workflowConfig,
                estimated_duration: this._estimateProcessingTime(session, workflow),
                progress_url: `http://localhost:8322/api/pipeline/processing/${processingId}/status`
            };
            
        } catch (error) {
            this.logger.error('Error processing gameplay footage:', error);
            throw error;
        }
    }

    async getCaptureSession(sessionId) {
        try {
            const sessionData = await this.redis.get(`capture_session:${sessionId}`);
            if (!sessionData) {
                throw new Error('Capture session not found');
            }
            
            return JSON.parse(sessionData);
        } catch (error) {
            this.logger.error('Error retrieving capture session:', error);
            throw error;
        }
    }

    async getProcessingStatus(processingId) {
        try {
            const jobData = await this.redis.get(`processing_job:${processingId}`);
            if (!jobData) {
                throw new Error('Processing job not found');
            }
            
            return JSON.parse(jobData);
        } catch (error) {
            this.logger.error('Error retrieving processing status:', error);
            throw error;
        }
    }

    // Private methods for capture system implementation
    async _initializeCaptureSystem(session) {
        const gameEngine = session.game_engine;
        const method = session.capture_method;
        
        // Create output directory
        await fs.mkdir(session.settings.output_path, { recursive: true });
        
        // Initialize capture method
        switch (method) {
            case 'screen_capture':
                await this._initializeScreenCapture(session);
                break;
            case 'window_capture':
                await this._initializeWindowCapture(session);
                break;
            case 'unity_recorder':
                await this._initializeUnityRecorder(session);
                break;
            case 'unreal_sequencer':
                await this._initializeUnrealSequencer(session);
                break;
            default:
                await this._initializeGenericCapture(session);
        }
        
        session.state = 'ready';
    }

    async _startRecording(session) {
        session.state = 'recording';
        session.recording_start_time = Date.now();
        
        // Start performance monitoring
        this._startPerformanceMonitoring(session);
        
        // Begin capture based on method
        switch (session.capture_method) {
            case 'screen_capture':
                await this._startScreenRecording(session);
                break;
            case 'unity_recorder':
                await this._startUnityRecording(session);
                break;
            case 'unreal_sequencer':
                await this._startUnrealRecording(session);
                break;
            default:
                await this._startGenericRecording(session);
        }
        
        // Set up event listeners for game engine events
        this._setupGameEngineEventListeners(session);
    }

    async _stopRecording(session) {
        session.recording_end_time = Date.now();
        
        // Stop capture process
        if (session.capture_process) {
            session.capture_process.kill('SIGTERM');
        }
        
        // Stop performance monitoring
        this._stopPerformanceMonitoring(session);
        
        // Finalize recorded files
        await this._finalizeRecordedFiles(session);
    }

    async _executeProcessingWorkflow(job, session) {
        const workflow = this.processingWorkflows[job.workflow];
        
        for (let i = 0; i < workflow.steps.length; i++) {
            const step = workflow.steps[i];
            job.current_step = i;
            job.progress.current_operation = `Executing: ${step}`;
            job.progress.percentage = (i / workflow.steps.length) * 100;
            
            // Execute processing step
            await this._executeProcessingStep(step, job, session);
            
            // Update progress
            this.io.emit('processing_progress', {
                processingId: job.id,
                progress: job.progress
            });
            
            // Update Redis
            await this.redis.setex(
                `processing_job:${job.id}`,
                86400 * 3,
                JSON.stringify(job)
            );
        }
        
        job.status = 'completed';
        job.completed_at = new Date();
        job.progress.percentage = 100;
        job.progress.current_operation = 'Processing complete';
        
        // Generate final output
        await this._generateFinalOutput(job, session);
    }

    async _executeProcessingStep(step, job, session) {
        switch (step) {
            case 'analyze_audio_peaks':
                await this._analyzeAudioPeaks(job, session);
                break;
            case 'detect_action_scenes':
                await this._detectActionScenes(job, session);
                break;
            case 'extract_highlights':
                await this._extractHighlights(job, session);
                break;
            case 'add_transitions':
                await this._addTransitions(job, session);
                break;
            case 'apply_color_grading':
                await this._applyColorGrading(job, session);
                break;
            case 'add_music_overlay':
                await this._addMusicOverlay(job, session);
                break;
            default:
                this.logger.warn(`Unknown processing step: ${step}`);
        }
    }

    // Capture method implementations (simplified)
    async _initializeScreenCapture(session) {
        session.capture_config = {
            method: 'ffmpeg',
            input: ':0.0',
            options: [
                '-f', 'x11grab',
                '-r', session.settings.framerate.toString(),
                '-s', session.settings.resolution,
                '-i', ':0.0'
            ]
        };
    }

    async _initializeUnityRecorder(session) {
        session.capture_config = {
            method: 'unity_api',
            recorder_settings: {
                format: 'mp4',
                codec: session.settings.codec,
                bitrate: session.settings.bitrate
            }
        };
    }

    async _startScreenRecording(session) {
        const outputFile = path.join(session.settings.output_path, 'recording.mp4');
        
        session.capture_process = ffmpeg()
            .input(':0.0')
            .inputOptions([
                '-f', 'x11grab',
                '-r', session.settings.framerate.toString(),
                '-s', session.settings.resolution
            ])
            .videoCodec(session.settings.codec)
            .videoBitrate(session.settings.bitrate)
            .output(outputFile)
            .on('start', () => {
                this.logger.info(`Started screen recording: ${outputFile}`);
            })
            .on('progress', (progress) => {
                session.progress = progress;
                this.io.emit('capture_progress', {
                    sessionId: session.id,
                    progress: progress
                });
            })
            .on('end', () => {
                this.logger.info(`Completed screen recording: ${outputFile}`);
                session.recorded_segments.push({
                    file: outputFile,
                    duration: session.progress?.timemark || '00:00:00',
                    size: 0 // Will be calculated
                });
            })
            .on('error', (err) => {
                this.logger.error('Screen recording error:', err);
                session.state = 'error';
                session.error = err.message;
            });
        
        // Don't start immediately - wait for explicit start command
        // session.capture_process.run();
    }

    // Processing step implementations (simplified)
    async _analyzeAudioPeaks(job, session) {
        // Analyze audio for exciting moments (loud sounds, music peaks, etc.)
        job.analysis = job.analysis || {};
        job.analysis.audio_peaks = [
            { timestamp: '00:01:23', intensity: 0.8, type: 'explosion' },
            { timestamp: '00:03:45', intensity: 0.9, type: 'music_climax' },
            { timestamp: '00:05:12', intensity: 0.7, type: 'combat_audio' }
        ];
    }

    async _detectActionScenes(job, session) {
        // Use computer vision/ML to detect action scenes
        job.analysis.action_scenes = [
            { start: '00:01:20', end: '00:01:35', confidence: 0.85, type: 'combat' },
            { start: '00:03:40', end: '00:04:10', confidence: 0.92, type: 'chase' },
            { start: '00:05:05', end: '00:05:25', confidence: 0.78, type: 'boss_fight' }
        ];
    }

    async _extractHighlights(job, session) {
        // Extract the most exciting moments based on analysis
        const highlights = [];
        const audioPeaks = job.analysis.audio_peaks || [];
        const actionScenes = job.analysis.action_scenes || [];
        
        // Combine audio and visual analysis to create highlight segments
        for (const scene of actionScenes) {
            if (scene.confidence > 0.8) {
                highlights.push({
                    start: scene.start,
                    end: scene.end,
                    type: scene.type,
                    score: scene.confidence
                });
            }
        }
        
        job.highlights = highlights;
    }

    // Helper methods
    _estimateFileSize(settings) {
        // Rough estimation based on resolution, framerate, and bitrate
        const { resolution, framerate, bitrate } = settings;
        const [width, height] = resolution.split('x').map(Number);
        const bitrateNum = parseInt(bitrate.replace('M', ''));
        
        const estimatedMBPerMinute = (bitrateNum * 60) / 8; // Convert from Mbps to MB/min
        
        return {
            per_minute: `${estimatedMBPerMinute}MB`,
            per_hour: `${estimatedMBPerMinute * 60}MB`,
            daily_storage_estimate: `${estimatedMBPerMinute * 60 * 8}MB`
        };
    }

    _calculateSessionStats(session) {
        const duration = session.stopped_at - session.started_at;
        
        return {
            duration: Math.floor(duration / 1000), // seconds
            segments_recorded: session.recorded_segments.length,
            total_size: session.recorded_segments.reduce((total, seg) => total + (seg.size || 0), 0),
            average_fps: session.performance_metrics.fps,
            dropped_frames: session.performance_metrics.dropped_frames,
            quality_score: this._calculateQualityScore(session)
        };
    }

    _calculateQualityScore(session) {
        // Calculate overall quality score based on various metrics
        let score = 100;
        
        if (session.performance_metrics.dropped_frames > 100) score -= 20;
        if (session.performance_metrics.fps < 30) score -= 15;
        if (session.performance_metrics.cpu_usage > 80) score -= 10;
        
        return Math.max(score, 0);
    }

    _estimateProcessingTime(session, workflow) {
        // Estimate processing time based on recorded duration and workflow complexity
        const sessionDuration = session.statistics?.duration || 3600; // Default 1 hour
        const workflowComplexity = {
            'gameplay_highlight': 0.5,
            'tutorial_creation': 1.0,
            'livestream_vod': 0.3,
            'cinematic_showcase': 1.5
        };
        
        const complexity = workflowComplexity[workflow] || 1.0;
        const estimatedSeconds = sessionDuration * complexity * 0.1; // 10% of duration per complexity unit
        
        return `${Math.ceil(estimatedSeconds / 60)} minutes`;
    }

    // Stub implementations for methods that would require actual capture hardware/software
    async _initializeWindowCapture(session) { /* Implementation */ }
    async _initializeUnrealSequencer(session) { /* Implementation */ }
    async _initializeGenericCapture(session) { /* Implementation */ }
    async _startUnityRecording(session) { /* Implementation */ }
    async _startUnrealRecording(session) { /* Implementation */ }
    async _startGenericRecording(session) { /* Implementation */ }
    _startPerformanceMonitoring(session) { /* Implementation */ }
    _stopPerformanceMonitoring(session) { /* Implementation */ }
    _setupGameEngineEventListeners(session) { /* Implementation */ }
    async _finalizeRecordedFiles(session) { /* Implementation */ }
    async _queuePostProcessing(session) { /* Implementation */ }
    async _addTransitions(job, session) { /* Implementation */ }
    async _applyColorGrading(job, session) { /* Implementation */ }
    async _addMusicOverlay(job, session) { /* Implementation */ }
    async _generateFinalOutput(job, session) { /* Implementation */ }

    async getStats() {
        try {
            const captureKeys = await this.redis.keys('capture_session:*');
            const processingKeys = await this.redis.keys('processing_job:*');
            
            let totalCaptures = captureKeys.length;
            let totalProcessingJobs = processingKeys.length;
            let totalDuration = 0;
            let engineDistribution = {};
            
            for (const key of captureKeys.slice(0, 100)) {
                try {
                    const data = await this.redis.get(key);
                    if (data) {
                        const session = JSON.parse(data);
                        if (session.statistics?.duration) {
                            totalDuration += session.statistics.duration;
                        }
                        const engine = session.game_engine;
                        engineDistribution[engine] = (engineDistribution[engine] || 0) + 1;
                    }
                } catch (error) {
                    // Skip invalid sessions
                }
            }
            
            return {
                total_captures: totalCaptures,
                total_processing_jobs: totalProcessingJobs,
                total_duration_hours: Math.floor(totalDuration / 3600),
                engine_distribution: engineDistribution,
                active_sessions: this.activeSessions.size
            };
            
        } catch (error) {
            this.logger.error('Error getting pipeline stats:', error);
            return {
                total_captures: 0,
                total_processing_jobs: 0,
                total_duration_hours: 0,
                engine_distribution: {},
                active_sessions: 0
            };
        }
    }
}

module.exports = GameEngineVideoPipeline;