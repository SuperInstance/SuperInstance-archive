import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import { Server as SocketIOServer } from 'socket.io';
import { createServer } from 'http';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

// Import our core components
import DocumentToPodcastConverter from './converter/DocumentToPodcastConverter.js';
import VoiceSynthesizer from './voices/VoiceSynthesizer.js';
import StyleSelector from './styles/StyleSelector.js';
import InteractiveChatbotEditor from './editing/InteractiveChatbotEditor.js';
import DetailLevelAdjuster from './details/DetailLevelAdjuster.js';
import SegmentRegenerator from './regeneration/SegmentRegenerator.js';
import IntroOutroAutomator from './automation/IntroOutroAutomator.js';
import BackgroundMusicIntegrator from './music/BackgroundMusicIntegrator.js';
import TranscriptGenerator from './transcription/TranscriptGenerator.js';
import DistributionAutomator from './distribution/DistributionAutomator.js';
import SponsorshipManager from './sponsors/SponsorshipManager.js';
import AudienceAnalytics from './analytics/AudienceAnalytics.js';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class PodcastGeneratorServer {
    constructor() {
        this.app = express();
        this.server = createServer(this.app);
        this.io = new SocketIOServer(this.server, {
            cors: {
                origin: "*",
                methods: ["GET", "POST"]
            }
        });
        
        this.port = process.env.PORT || 8384;
        this.activeConnections = new Map();
        this.processingJobs = new Map();
        
        // Initialize core components
        this.initializeComponents();
        this.setupMiddleware();
        this.setupRoutes();
        this.setupSocketHandlers();
        this.setupErrorHandlers();
    }

    initializeComponents() {
        console.log('Initializing podcast generation components...');
        
        try {
            this.documentConverter = new DocumentToPodcastConverter();
            this.voiceSynthesizer = new VoiceSynthesizer();
            this.styleSelector = new StyleSelector();
            this.chatbotEditor = new InteractiveChatbotEditor();
            this.detailAdjuster = new DetailLevelAdjuster();
            this.segmentRegenerator = new SegmentRegenerator();
            this.introOutroAutomator = new IntroOutroAutomator();
            this.musicIntegrator = new BackgroundMusicIntegrator();
            this.transcriptGenerator = new TranscriptGenerator();
            this.distributionAutomator = new DistributionAutomator();
            this.sponsorshipManager = new SponsorshipManager();
            this.audienceAnalytics = new AudienceAnalytics();

            // Setup event listeners for real-time updates
            this.setupComponentEventListeners();
            
            console.log('✅ All components initialized successfully');
        } catch (error) {
            console.error('❌ Failed to initialize components:', error);
            process.exit(1);
        }
    }

    setupComponentEventListeners() {
        // Document Converter events
        this.documentConverter.on('conversion-started', (data) => {
            this.io.emit('conversion-started', data);
        });
        
        this.documentConverter.on('conversion-progress', (data) => {
            this.io.emit('conversion-progress', data);
        });
        
        this.documentConverter.on('conversion-completed', (data) => {
            this.io.emit('conversion-completed', data);
        });

        // Voice Synthesizer events
        this.voiceSynthesizer.on('synthesis-started', (data) => {
            this.io.emit('synthesis-started', data);
        });
        
        this.voiceSynthesizer.on('segment-synthesized', (data) => {
            this.io.emit('segment-synthesized', data);
        });
        
        this.voiceSynthesizer.on('synthesis-completed', (data) => {
            this.io.emit('synthesis-completed', data);
        });

        // Interactive Editor events
        this.chatbotEditor.on('user-message-processed', (data) => {
            this.io.emit('editing-update', data);
        });

        // Segment Regenerator events
        this.segmentRegenerator.on('regeneration-started', (data) => {
            this.io.emit('regeneration-started', data);
        });
        
        this.segmentRegenerator.on('regeneration-completed', (data) => {
            this.io.emit('regeneration-completed', data);
        });
    }

    setupMiddleware() {
        // Security middleware
        this.app.use(helmet({
            contentSecurityPolicy: {
                directives: {
                    defaultSrc: ["'self'"],
                    styleSrc: ["'self'", "'unsafe-inline'"],
                    scriptSrc: ["'self'"],
                    imgSrc: ["'self'", "data:", "https:"],
                    connectSrc: ["'self'", "ws:", "wss:"]
                }
            }
        }));

        // CORS
        this.app.use(cors({
            origin: process.env.ALLOWED_ORIGINS?.split(',') || '*',
            credentials: true
        }));

        // Rate limiting
        const limiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: 100, // limit each IP to 100 requests per windowMs
            message: {
                error: 'Too many requests from this IP, please try again later.',
                retryAfter: '15 minutes'
            }
        });
        this.app.use(limiter);

        // Body parsing and compression
        this.app.use(compression());
        this.app.use(express.json({ limit: '50mb' }));
        this.app.use(express.urlencoded({ extended: true, limit: '50mb' }));

        // Logging
        this.app.use(morgan('combined'));

        // Serve static files
        this.app.use('/assets', express.static(path.join(__dirname, '../assets')));
        this.app.use('/output', express.static(path.join(__dirname, '../output')));
    }

    setupRoutes() {
        // Health check
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                version: '1.0.0',
                components: {
                    documentConverter: 'ready',
                    voiceSynthesizer: 'ready',
                    styleSelector: 'ready',
                    chatbotEditor: 'ready',
                    detailAdjuster: 'ready',
                    segmentRegenerator: 'ready',
                    introOutroAutomator: 'ready',
                    musicIntegrator: 'ready',
                    transcriptGenerator: 'ready',
                    distributionAutomator: 'ready',
                    sponsorshipManager: 'ready',
                    audienceAnalytics: 'ready'
                }
            });
        });

        // API Documentation
        this.app.get('/', (req, res) => {
            res.json({
                name: 'ActiveLog Podcast Generation Engine',
                version: '1.0.0',
                description: 'AI-powered podcast generation from documents with multi-voice synthesis',
                endpoints: {
                    'GET /health': 'Health check',
                    'POST /convert': 'Convert document to podcast',
                    'POST /synthesize': 'Synthesize voice for podcast',
                    'GET /styles': 'Get available conversation styles',
                    'POST /styles/select': 'Select conversation style',
                    'POST /edit/start': 'Start interactive editing session',
                    'POST /edit/message': 'Send message to editing chatbot',
                    'POST /adjust-detail': 'Adjust detail level',
                    'POST /regenerate': 'Regenerate segments',
                    'POST /intro-outro': 'Generate intro/outro',
                    'POST /add-music': 'Add background music',
                    'POST /generate-transcript': 'Generate transcripts',
                    'POST /distribute': 'Distribute to platforms',
                    'POST /sponsors': 'Manage sponsorships',
                    'POST /track-analytics': 'Track audience analytics'
                },
                websocket: 'Real-time updates on port ' + this.port
            });
        });

        // Document to Podcast Conversion
        this.app.post('/convert', async (req, res) => {
            try {
                const { document_path, document_type, style_preferences, output_options } = req.body;
                
                if (!document_path) {
                    return res.status(400).json({ error: 'document_path is required' });
                }

                const conversionRequest = {
                    document_path,
                    document_type: document_type || 'auto-detect',
                    style_preferences: style_preferences || {},
                    output_options: output_options || {}
                };

                const result = await this.documentConverter.convertDocument(conversionRequest);
                
                res.json({
                    success: true,
                    conversion_id: result.conversionId,
                    script: result.script,
                    metadata: result.metadata
                });

            } catch (error) {
                console.error('Conversion error:', error);
                res.status(500).json({
                    error: 'Conversion failed',
                    details: error.message
                });
            }
        });

        // Voice Synthesis
        this.app.post('/synthesize', async (req, res) => {
            try {
                const { dialogue_script, voice_assignments, options } = req.body;
                
                if (!dialogue_script) {
                    return res.status(400).json({ error: 'dialogue_script is required' });
                }

                const result = await this.voiceSynthesizer.synthesizePodcast(
                    dialogue_script,
                    voice_assignments || {},
                    options || {}
                );
                
                res.json({
                    success: true,
                    task_id: result.taskId,
                    final_audio_path: result.finalAudioPath,
                    processing_time: result.processingTime
                });

            } catch (error) {
                console.error('Synthesis error:', error);
                res.status(500).json({
                    error: 'Synthesis failed',
                    details: error.message
                });
            }
        });

        // Style Selection
        this.app.get('/styles', (req, res) => {
            try {
                const styles = this.styleSelector.getAvailableStyles();
                const presets = this.styleSelector.getStylePresets();
                
                res.json({
                    success: true,
                    styles: styles,
                    presets: presets
                });
            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get styles',
                    details: error.message
                });
            }
        });

        this.app.post('/styles/select', async (req, res) => {
            try {
                const selectionRequest = req.body;
                const result = this.styleSelector.selectStyle(selectionRequest);
                
                res.json({
                    success: true,
                    selection: result
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Style selection failed',
                    details: error.message
                });
            }
        });

        // Interactive Editing
        this.app.post('/edit/start', async (req, res) => {
            try {
                const { podcast_script, session_config } = req.body;
                
                if (!podcast_script) {
                    return res.status(400).json({ error: 'podcast_script is required' });
                }

                const result = await this.chatbotEditor.startEditingSession(
                    podcast_script,
                    session_config || {}
                );
                
                res.json({
                    success: true,
                    session_id: result.session_id,
                    welcome_message: result.welcome_message,
                    available_commands: result.available_commands
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to start editing session',
                    details: error.message
                });
            }
        });

        this.app.post('/edit/message', async (req, res) => {
            try {
                const { session_id, message } = req.body;
                
                if (!session_id || !message) {
                    return res.status(400).json({ error: 'session_id and message are required' });
                }

                const result = await this.chatbotEditor.processUserMessage(session_id, message);
                
                res.json({
                    success: true,
                    response: result.response,
                    edit_results: result.edit_results,
                    current_script: result.current_script
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to process message',
                    details: error.message
                });
            }
        });

        // Detail Level Adjustment
        this.app.post('/adjust-detail', async (req, res) => {
            try {
                const { script, target_detail_level, options } = req.body;
                
                if (!script || !target_detail_level) {
                    return res.status(400).json({ error: 'script and target_detail_level are required' });
                }

                const result = await this.detailAdjuster.adjustDetailLevel(
                    script,
                    target_detail_level,
                    options || {}
                );
                
                res.json({
                    success: true,
                    adjustment_id: result.adjustment_id,
                    adjusted_script: result.adjusted_script,
                    summary: result.adjustment_summary
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Detail adjustment failed',
                    details: error.message
                });
            }
        });

        this.app.get('/detail-levels', (req, res) => {
            try {
                const levels = this.detailAdjuster.getDetailLevels();
                res.json({ success: true, detail_levels: levels });
            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get detail levels',
                    details: error.message
                });
            }
        });

        // Segment Regeneration
        this.app.post('/regenerate', async (req, res) => {
            try {
                const { script, segment_index, regeneration_request } = req.body;
                
                if (!script || segment_index === undefined || !regeneration_request) {
                    return res.status(400).json({ 
                        error: 'script, segment_index, and regeneration_request are required' 
                    });
                }

                const result = await this.segmentRegenerator.regenerateSegment(
                    script,
                    segment_index,
                    regeneration_request
                );
                
                res.json({
                    success: true,
                    task_id: result.task_id,
                    regenerated_segment: result.regenerated_segment,
                    quality_score: result.quality_score
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Regeneration failed',
                    details: error.message
                });
            }
        });

        this.app.get('/regeneration-strategies', (req, res) => {
            try {
                const strategies = this.segmentRegenerator.getRegenerationStrategies();
                res.json({ success: true, strategies: strategies });
            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get regeneration strategies',
                    details: error.message
                });
            }
        });

        // Intro/Outro Generation
        this.app.post('/intro-outro', async (req, res) => {
            try {
                const { podcast_metadata, episode_metadata, episode_summary, options } = req.body;
                
                if (!podcast_metadata || !episode_metadata) {
                    return res.status(400).json({ 
                        error: 'podcast_metadata and episode_metadata are required' 
                    });
                }

                const result = await this.introOutroAutomator.createCompleteIntroOutroPackage(
                    podcast_metadata,
                    episode_metadata,
                    episode_summary,
                    options || {}
                );
                
                res.json({
                    success: true,
                    package_info: result.package_info,
                    intro: result.intro,
                    outro: result.outro
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Intro/outro generation failed',
                    details: error.message
                });
            }
        });

        this.app.get('/intro-outro/templates', (req, res) => {
            try {
                const introTemplates = this.introOutroAutomator.getIntroTemplates();
                const outroTemplates = this.introOutroAutomator.getOutroTemplates();
                
                res.json({
                    success: true,
                    intro_templates: introTemplates,
                    outro_templates: outroTemplates
                });
            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get templates',
                    details: error.message
                });
            }
        });

        // Voice Profiles
        this.app.get('/voices', (req, res) => {
            try {
                const voiceProfiles = this.voiceSynthesizer.getVoiceProfiles();
                res.json({ success: true, voice_profiles: voiceProfiles });
            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get voice profiles',
                    details: error.message
                });
            }
        });

        // Background Music Integration
        this.app.post('/add-music', async (req, res) => {
            try {
                const { podcast_audio_path, music_integration_request } = req.body;
                
                if (!podcast_audio_path) {
                    return res.status(400).json({ error: 'podcast_audio_path is required' });
                }

                const result = await this.musicIntegrator.integrateBackgroundMusic(
                    podcast_audio_path,
                    music_integration_request || {}
                );
                
                res.json({
                    success: true,
                    task_id: result.task_id,
                    output_path: result.output_path
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Music integration failed',
                    details: error.message
                });
            }
        });

        this.app.get('/music-profiles', (req, res) => {
            try {
                const profiles = this.musicIntegrator.getMusicProfiles();
                res.json({ success: true, music_profiles: profiles });
            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get music profiles',
                    details: error.message
                });
            }
        });

        // Transcript Generation
        this.app.post('/generate-transcript', async (req, res) => {
            try {
                const { podcast_script, audio_file_path, transcription_options } = req.body;
                
                if (!podcast_script) {
                    return res.status(400).json({ error: 'podcast_script is required' });
                }

                const result = await this.transcriptGenerator.generateTranscript(
                    podcast_script,
                    audio_file_path,
                    transcription_options || {}
                );
                
                res.json({
                    success: true,
                    task_id: result.task_id,
                    generated_files: result.generated_files
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Transcript generation failed',
                    details: error.message
                });
            }
        });

        this.app.get('/transcript-formats', (req, res) => {
            try {
                const formats = this.transcriptGenerator.getTranscriptFormats();
                res.json({ success: true, transcript_formats: formats });
            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get transcript formats',
                    details: error.message
                });
            }
        });

        // Distribution Automation
        this.app.post('/distribute', async (req, res) => {
            try {
                const distributionRequest = req.body;
                
                if (!distributionRequest.podcast_metadata || !distributionRequest.episodes) {
                    return res.status(400).json({ 
                        error: 'podcast_metadata and episodes are required' 
                    });
                }

                const result = await this.distributionAutomator.distributeToMultiplePlatforms(distributionRequest);
                
                res.json({
                    success: true,
                    task_id: result.task_id,
                    rss_feed: result.rss_feed,
                    platform_results: result.platform_results
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Distribution failed',
                    details: error.message
                });
            }
        });

        this.app.get('/distribution-platforms', (req, res) => {
            try {
                const platforms = this.distributionAutomator.getDistributionPlatforms();
                res.json({ success: true, distribution_platforms: platforms });
            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get distribution platforms',
                    details: error.message
                });
            }
        });

        // Sponsorship Management
        this.app.post('/sponsors', async (req, res) => {
            try {
                const { action, data } = req.body;
                let result;

                switch (action) {
                    case 'create_sponsor':
                        result = await this.sponsorshipManager.createSponsor(data);
                        break;
                    case 'generate_segment':
                        result = await this.sponsorshipManager.generateSponsorSegment(data);
                        break;
                    case 'insert_segments':
                        result = await this.sponsorshipManager.insertSponsorSegments(data.script, data.insertions);
                        break;
                    default:
                        return res.status(400).json({ error: 'Invalid action' });
                }
                
                res.json({ success: true, result: result });

            } catch (error) {
                res.status(500).json({
                    error: 'Sponsorship operation failed',
                    details: error.message
                });
            }
        });

        this.app.get('/sponsor-templates', (req, res) => {
            try {
                const templates = this.sponsorshipManager.getSponsorTemplates();
                res.json({ success: true, sponsor_templates: templates });
            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get sponsor templates',
                    details: error.message
                });
            }
        });

        // Audience Analytics
        this.app.post('/track-analytics', async (req, res) => {
            try {
                const { action, data } = req.body;
                let result;

                switch (action) {
                    case 'track_event':
                        result = await this.audienceAnalytics.trackListenerEvent(data);
                        break;
                    case 'generate_report':
                        result = await this.audienceAnalytics.generateAudienceReport(data);
                        break;
                    case 'export_data':
                        result = await this.audienceAnalytics.exportAnalyticsData(data.format, data.timeRange);
                        break;
                    default:
                        return res.status(400).json({ error: 'Invalid action' });
                }
                
                res.json({ success: true, result: result });

            } catch (error) {
                res.status(500).json({
                    error: 'Analytics operation failed',
                    details: error.message
                });
            }
        });

        this.app.get('/analytics-metrics', (req, res) => {
            try {
                const metrics = this.audienceAnalytics.getMetricDefinitions();
                res.json({ success: true, metric_definitions: metrics });
            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get analytics metrics',
                    details: error.message
                });
            }
        });

        // Job Status Endpoints
        this.app.get('/jobs/:jobId/status', (req, res) => {
            const jobId = req.params.jobId;
            const job = this.processingJobs.get(jobId);
            
            if (!job) {
                return res.status(404).json({ error: 'Job not found' });
            }
            
            res.json({ success: true, job: job });
        });

        // Complete Workflow Endpoint
        this.app.post('/generate-complete-podcast', async (req, res) => {
            const jobId = Date.now().toString();
            
            try {
                const {
                    document_path,
                    document_type,
                    podcast_metadata,
                    episode_metadata,
                    style_preferences,
                    voice_preferences,
                    options
                } = req.body;

                // Store job
                this.processingJobs.set(jobId, {
                    id: jobId,
                    status: 'processing',
                    started_at: new Date().toISOString(),
                    steps: []
                });

                // Send immediate response with job ID
                res.json({
                    success: true,
                    job_id: jobId,
                    message: 'Podcast generation started. Use WebSocket or check /jobs/{jobId}/status for updates.'
                });

                // Process in background
                this.processCompleteWorkflow(jobId, {
                    document_path,
                    document_type,
                    podcast_metadata,
                    episode_metadata,
                    style_preferences,
                    voice_preferences,
                    options
                }).catch(error => {
                    console.error(`Job ${jobId} failed:`, error);
                    const job = this.processingJobs.get(jobId);
                    if (job) {
                        job.status = 'failed';
                        job.error = error.message;
                        job.completed_at = new Date().toISOString();
                    }
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to start podcast generation',
                    details: error.message
                });
            }
        });
    }

    async processCompleteWorkflow(jobId, params) {
        const job = this.processingJobs.get(jobId);
        
        try {
            // Step 1: Convert document
            job.steps.push({ step: 'document_conversion', status: 'processing', started_at: new Date() });
            this.io.emit('job-update', { jobId, step: 'document_conversion', status: 'processing' });
            
            const conversionResult = await this.documentConverter.convertDocument({
                document_path: params.document_path,
                document_type: params.document_type,
                style_preferences: params.style_preferences
            });
            
            job.steps[job.steps.length - 1].status = 'completed';
            job.script = conversionResult.script;

            // Step 2: Generate intro/outro
            if (params.podcast_metadata && params.episode_metadata) {
                job.steps.push({ step: 'intro_outro_generation', status: 'processing', started_at: new Date() });
                this.io.emit('job-update', { jobId, step: 'intro_outro_generation', status: 'processing' });
                
                const introOutroResult = await this.introOutroAutomator.createCompleteIntroOutroPackage(
                    params.podcast_metadata,
                    params.episode_metadata,
                    'Generated podcast content'
                );
                
                job.steps[job.steps.length - 1].status = 'completed';
                job.intro_outro = introOutroResult;
            }

            // Step 3: Voice synthesis
            job.steps.push({ step: 'voice_synthesis', status: 'processing', started_at: new Date() });
            this.io.emit('job-update', { jobId, step: 'voice_synthesis', status: 'processing' });
            
            const synthesisResult = await this.voiceSynthesizer.synthesizePodcast(
                job.script,
                params.voice_preferences?.voice_assignments || {},
                params.options?.synthesis_options || {}
            );
            
            job.steps[job.steps.length - 1].status = 'completed';
            job.audio_result = synthesisResult;

            // Complete job
            job.status = 'completed';
            job.completed_at = new Date().toISOString();
            job.final_output = {
                script: job.script,
                audio_path: synthesisResult.finalAudioPath,
                intro_outro: job.intro_outro
            };

            this.io.emit('job-completed', { jobId, result: job.final_output });

        } catch (error) {
            job.status = 'failed';
            job.error = error.message;
            job.completed_at = new Date().toISOString();
            this.io.emit('job-failed', { jobId, error: error.message });
            throw error;
        }
    }

    setupSocketHandlers() {
        this.io.on('connection', (socket) => {
            console.log(`Client connected: ${socket.id}`);
            
            this.activeConnections.set(socket.id, {
                connected_at: new Date().toISOString(),
                last_activity: new Date().toISOString()
            });

            socket.on('join-job', (jobId) => {
                socket.join(`job-${jobId}`);
                console.log(`Client ${socket.id} joined job ${jobId}`);
            });

            socket.on('ping', () => {
                const connection = this.activeConnections.get(socket.id);
                if (connection) {
                    connection.last_activity = new Date().toISOString();
                }
                socket.emit('pong');
            });

            socket.on('disconnect', () => {
                console.log(`Client disconnected: ${socket.id}`);
                this.activeConnections.delete(socket.id);
            });
        });
    }

    setupErrorHandlers() {
        // Handle 404
        this.app.use('*', (req, res) => {
            res.status(404).json({
                error: 'Endpoint not found',
                requested_path: req.originalUrl,
                method: req.method,
                message: 'Check the API documentation at /'
            });
        });

        // Global error handler
        this.app.use((error, req, res, next) => {
            console.error('Unhandled error:', error);
            
            res.status(500).json({
                error: 'Internal server error',
                message: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong',
                timestamp: new Date().toISOString()
            });
        });

        // Handle unhandled promise rejections
        process.on('unhandledRejection', (reason, promise) => {
            console.error('Unhandled Rejection at:', promise, 'reason:', reason);
        });

        // Handle uncaught exceptions
        process.on('uncaughtException', (error) => {
            console.error('Uncaught Exception:', error);
            process.exit(1);
        });
    }

    start() {
        this.server.listen(this.port, () => {
            console.log(`
🎙️  ActiveLog Podcast Generation Engine
🚀 Server running on port ${this.port}
📡 WebSocket enabled for real-time updates
🌐 API Documentation: http://localhost:${this.port}
💡 Health Check: http://localhost:${this.port}/health

Components ready:
✅ Document-to-Podcast Converter
✅ Multi-Voice Synthesizer  
✅ Conversation Style Selector
✅ Interactive Chatbot Editor
✅ Detail Level Adjuster
✅ Segment Regenerator
✅ Intro/Outro Automator
✅ Background Music Integrator
✅ Transcript Generator
✅ Distribution Automator
✅ Sponsorship Manager
✅ Audience Analytics

Ready to generate podcasts! 🎧
            `);
        });
    }

    async stop() {
        console.log('Shutting down server...');
        
        // Close all active connections
        this.io.close();
        
        // Close server
        await new Promise((resolve) => {
            this.server.close(resolve);
        });
        
        console.log('Server shut down complete.');
    }
}

// Start the server
const podcastServer = new PodcastGeneratorServer();
podcastServer.start();

// Handle graceful shutdown
process.on('SIGTERM', async () => {
    console.log('SIGTERM received, shutting down gracefully...');
    await podcastServer.stop();
    process.exit(0);
});

process.on('SIGINT', async () => {
    console.log('SIGINT received, shutting down gracefully...');
    await podcastServer.stop();
    process.exit(0);
});

export default PodcastGeneratorServer;