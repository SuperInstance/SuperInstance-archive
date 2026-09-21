import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { createServer } from 'http';
import { Server } from 'socket.io';
import compression from 'compression';
import morgan from 'morgan';
import dotenv from 'dotenv';

// Import our social hub modules
import MultiPlatformConnector from './connectors/MultiPlatformConnector.js';
import AutomatedResponseSystem from './automation/AutomatedResponseSystem.js';
import ContentCurationTools from './curation/ContentCurationTools.js';
import CrossPlatformPosting from './posting/CrossPlatformPosting.js';
import YouTubeDirectUpload from './youtube/YouTubeDirectUpload.js';
import ScheduledContentRelease from './scheduling/ScheduledContentRelease.js';

dotenv.config();

class SocialHubServer {
    constructor() {
        this.app = express();
        this.server = createServer(this.app);
        this.io = new Server(this.server, {
            cors: {
                origin: process.env.CORS_ORIGIN || "*",
                methods: ["GET", "POST"]
            }
        });

        this.port = process.env.PORT || 8383;
        
        // Initialize services
        this.initializeServices();
        this.setupMiddleware();
        this.setupRoutes();
        this.setupWebSocketHandlers();
        this.setupErrorHandling();
    }

    async initializeServices() {
        console.log('🚀 Initializing Social Hub services...');

        try {
            // Initialize core services
            this.platformConnector = new MultiPlatformConnector({
                twitter: {
                    consumer_key: process.env.TWITTER_API_KEY,
                    consumer_secret: process.env.TWITTER_API_SECRET,
                    access_token: process.env.TWITTER_ACCESS_TOKEN,
                    access_token_secret: process.env.TWITTER_ACCESS_SECRET
                },
                facebook: {
                    app_id: process.env.FACEBOOK_APP_ID,
                    app_secret: process.env.FACEBOOK_APP_SECRET,
                    access_token: process.env.FACEBOOK_ACCESS_TOKEN
                },
                instagram: {
                    client_id: process.env.INSTAGRAM_CLIENT_ID,
                    client_secret: process.env.INSTAGRAM_CLIENT_SECRET,
                    access_token: process.env.INSTAGRAM_ACCESS_TOKEN
                },
                youtube: {
                    client_id: process.env.YOUTUBE_CLIENT_ID,
                    client_secret: process.env.YOUTUBE_CLIENT_SECRET,
                    refresh_token: process.env.YOUTUBE_REFRESH_TOKEN
                }
            });

            this.automatedResponse = new AutomatedResponseSystem({
                openai_api_key: process.env.OPENAI_API_KEY
            });

            this.contentCuration = new ContentCurationTools({
                openai_api_key: process.env.OPENAI_API_KEY
            });

            this.crossPosting = new CrossPlatformPosting({
                activelog_endpoints: {
                    content_feed: process.env.ACTIVELOG_CONTENT_FEED || 'http://localhost:8080/api/content/feed',
                    project_updates: process.env.ACTIVELOG_PROJECT_UPDATES || 'http://localhost:8080/api/projects/updates'
                }
            });

            this.youtubeUpload = new YouTubeDirectUpload({
                client_id: process.env.YOUTUBE_CLIENT_ID,
                client_secret: process.env.YOUTUBE_CLIENT_SECRET,
                refresh_token: process.env.YOUTUBE_REFRESH_TOKEN
            });

            this.scheduledContent = new ScheduledContentRelease({
                openai_api_key: process.env.OPENAI_API_KEY
            });

            this.setupServiceEventHandlers();
            console.log('✅ All services initialized successfully');

        } catch (error) {
            console.error('❌ Service initialization failed:', error);
            throw error;
        }
    }

    setupServiceEventHandlers() {
        // Platform connector events
        this.platformConnector.on('platforms_initialized', (platforms) => {
            console.log('📱 Connected platforms:', platforms);
            this.io.emit('platform_status', { connected_platforms: platforms });
        });

        this.platformConnector.on('post_success', (result) => {
            this.io.emit('post_success', result);
        });

        this.platformConnector.on('post_error', (error) => {
            this.io.emit('post_error', error);
        });

        // Automated response events
        this.automatedResponse.on('message_processed', (data) => {
            this.io.emit('message_processed', data);
        });

        this.automatedResponse.on('response_ready', (data) => {
            // Forward response to platform connector
            this.platformConnector.post(data.platform, {
                text: data.content,
                reply_to: data.response_to
            });
        });

        this.automatedResponse.on('team_notification', (notification) => {
            this.io.emit('team_notification', notification);
        });

        // Content curation events
        this.contentCuration.on('curation_cycle_completed', (stats) => {
            this.io.emit('curation_completed', stats);
        });

        this.contentCuration.on('content_notification', (notification) => {
            this.io.emit('content_notification', notification);
        });

        // Cross-posting events
        this.crossPosting.on('cross_post_scheduled', (data) => {
            this.io.emit('cross_post_scheduled', data);
        });

        this.crossPosting.on('execute_post', async (postData) => {
            // Execute post via platform connector
            const result = await this.platformConnector.post(postData.platform, postData.content);
            this.io.emit('cross_post_executed', { post_data: postData, result });
        });

        // YouTube upload events
        this.youtubeUpload.on('upload_completed', (data) => {
            this.io.emit('youtube_upload_completed', data);
        });

        this.youtubeUpload.on('upload_progress', (progress) => {
            this.io.emit('youtube_upload_progress', progress);
        });

        // Scheduled content events
        this.scheduledContent.on('schedule_executed', (data) => {
            this.io.emit('schedule_executed', data);
        });

        this.scheduledContent.on('execute_scheduled_post', async (post) => {
            // Execute scheduled post
            const result = await this.platformConnector.post(post.platform, post.content);
            this.io.emit('scheduled_post_executed', { post, result });
        });
    }

    setupMiddleware() {
        // Security middleware
        this.app.use(helmet());
        this.app.use(compression());
        
        // CORS
        this.app.use(cors({
            origin: process.env.CORS_ORIGIN || '*',
            credentials: true
        }));

        // Rate limiting
        const limiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: 100, // Limit each IP to 100 requests per windowMs
            message: 'Too many requests from this IP, please try again later.'
        });
        this.app.use('/api/', limiter);

        // Body parsing
        this.app.use(express.json({ limit: '10mb' }));
        this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

        // Logging
        this.app.use(morgan('combined'));

        // Health check endpoint
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                services: {
                    platform_connector: 'running',
                    automated_response: 'running',
                    content_curation: 'running',
                    cross_posting: 'running',
                    youtube_upload: 'running',
                    scheduled_content: 'running'
                }
            });
        });
    }

    setupRoutes() {
        // Platform connection routes
        this.app.get('/api/platforms/status', (req, res) => {
            res.json(this.platformConnector.getPlatformStatus());
        });

        this.app.post('/api/platforms/:platform/post', async (req, res) => {
            try {
                const { platform } = req.params;
                const { content } = req.body;

                const result = await this.platformConnector.post(platform, content);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        this.app.post('/api/platforms/cross-post', async (req, res) => {
            try {
                const { content, platforms, options } = req.body;
                const result = await this.crossPosting.createManualCrossPost(content, platforms, options);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        // Content curation routes
        this.app.post('/api/curation/run', async (req, res) => {
            try {
                const result = await this.contentCuration.runCurationCycle();
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        this.app.get('/api/curation/collections', (req, res) => {
            const collections = Array.from(this.contentCuration.collections.values());
            res.json({ collections });
        });

        this.app.post('/api/curation/content/:contentId/approve', async (req, res) => {
            try {
                const { contentId } = req.params;
                const result = await this.contentCuration.approveContent(contentId);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        this.app.get('/api/curation/stats', (req, res) => {
            const { timeframe } = req.query;
            const stats = this.contentCuration.getCurationStats(timeframe);
            res.json({ stats });
        });

        // Automated response routes
        this.app.post('/api/automation/process-message', async (req, res) => {
            try {
                const messageData = req.body;
                const result = await this.automatedResponse.processMessage(messageData);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        this.app.get('/api/automation/stats', (req, res) => {
            const { timeframe } = req.query;
            const stats = this.automatedResponse.getResponseStats(timeframe);
            res.json({ stats });
        });

        this.app.get('/api/automation/health', (req, res) => {
            const health = this.automatedResponse.getAutomationHealth();
            res.json({ health });
        });

        this.app.post('/api/automation/templates', async (req, res) => {
            try {
                const template = req.body;
                const result = await this.automatedResponse.addResponseTemplate(template);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        // YouTube upload routes
        this.app.post('/api/youtube/upload', async (req, res) => {
            try {
                const videoData = req.body;
                const result = await this.youtubeUpload.uploadVideo(videoData);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        this.app.post('/api/youtube/upload-series', async (req, res) => {
            try {
                const seriesData = req.body;
                const result = await this.youtubeUpload.uploadVideoSeries(seriesData);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        this.app.get('/api/youtube/queue/status', (req, res) => {
            const status = this.youtubeUpload.getQueueStatus();
            res.json({ status });
        });

        this.app.get('/api/youtube/stats', (req, res) => {
            const { timeframe } = req.query;
            const stats = this.youtubeUpload.getUploadStats(timeframe);
            res.json({ stats });
        });

        this.app.post('/api/youtube/create-livestream', async (req, res) => {
            try {
                const streamData = req.body;
                const result = await this.youtubeUpload.createLiveStream(streamData);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        // Scheduled content routes
        this.app.post('/api/scheduling/schedules', async (req, res) => {
            try {
                const scheduleData = req.body;
                const result = await this.scheduledContent.createSchedule(scheduleData);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        this.app.get('/api/scheduling/schedules', (req, res) => {
            const schedules = Array.from(this.scheduledContent.schedules.values());
            res.json({ schedules });
        });

        this.app.put('/api/scheduling/schedules/:scheduleId/pause', async (req, res) => {
            try {
                const { scheduleId } = req.params;
                const result = await this.scheduledContent.pauseSchedule(scheduleId);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        this.app.put('/api/scheduling/schedules/:scheduleId/resume', async (req, res) => {
            try {
                const { scheduleId } = req.params;
                const result = await this.scheduledContent.resumeSchedule(scheduleId);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        this.app.get('/api/scheduling/stats', (req, res) => {
            const stats = this.scheduledContent.getScheduleStats();
            res.json({ stats });
        });

        this.app.get('/api/scheduling/calendar', (req, res) => {
            const { start_date, end_date } = req.query;
            const calendar = this.scheduledContent.getContentCalendar(start_date, end_date);
            res.json({ calendar });
        });

        this.app.post('/api/scheduling/campaigns', async (req, res) => {
            try {
                const campaignData = req.body;
                const result = await this.scheduledContent.createCampaign(campaignData);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        // Analytics and reporting routes
        this.app.get('/api/analytics/dashboard', async (req, res) => {
            try {
                const dashboard = {
                    platform_status: this.platformConnector.getPlatformStatus(),
                    curation_stats: this.contentCuration.getCurationStats(),
                    automation_health: this.automatedResponse.getAutomationHealth(),
                    cross_posting_stats: this.crossPosting.getCrossPostingStats(),
                    youtube_stats: await this.youtubeUpload.getUploadStats(),
                    schedule_stats: this.scheduledContent.getScheduleStats(),
                    timestamp: new Date().toISOString()
                };

                res.json({ dashboard });
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        this.app.get('/api/analytics/youtube-channel', async (req, res) => {
            try {
                const analytics = await this.youtubeUpload.getChannelAnalytics();
                res.json({ analytics });
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        // Configuration routes
        this.app.get('/api/config/templates', (req, res) => {
            const templates = {
                video_templates: Array.from(this.youtubeUpload.videoTemplates.values()),
                response_templates: Array.from(this.automatedResponse.responseTemplates.values()),
                schedule_templates: Array.from(this.scheduledContent.templates.values())
            };
            res.json({ templates });
        });

        this.app.post('/api/config/automation-rules', async (req, res) => {
            try {
                const { rule_id, updates } = req.body;
                const result = await this.automatedResponse.updateAutomationRule(rule_id, updates);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });
    }

    setupWebSocketHandlers() {
        this.io.on('connection', (socket) => {
            console.log(`🔌 Client connected: ${socket.id}`);

            socket.on('subscribe_notifications', (data) => {
                socket.join('notifications');
                console.log(`📢 Client ${socket.id} subscribed to notifications`);
            });

            socket.on('subscribe_platform_events', (platform) => {
                socket.join(`platform_${platform}`);
                console.log(`📱 Client ${socket.id} subscribed to ${platform} events`);
            });

            socket.on('subscribe_upload_progress', (upload_id) => {
                socket.join(`upload_${upload_id}`);
                console.log(`📤 Client ${socket.id} subscribed to upload ${upload_id}`);
            });

            socket.on('request_dashboard_update', () => {
                this.sendDashboardUpdate(socket);
            });

            socket.on('disconnect', () => {
                console.log(`🔌 Client disconnected: ${socket.id}`);
            });
        });

        // Periodic dashboard updates
        setInterval(() => {
            this.broadcastDashboardUpdate();
        }, 30000); // Every 30 seconds
    }

    async sendDashboardUpdate(socket) {
        try {
            const update = {
                platform_status: this.platformConnector.getPlatformStatus(),
                queue_status: {
                    youtube_uploads: this.youtubeUpload.getQueueStatus(),
                    scheduled_content: this.scheduledContent.getScheduleStats(),
                    cross_posting: this.crossPosting.getQueueStatus()
                },
                recent_activity: {
                    automation_responses: this.automatedResponse.getResponseStats('1h'),
                    curation_stats: this.contentCuration.getCurationStats('1h')
                },
                timestamp: new Date().toISOString()
            };

            socket.emit('dashboard_update', update);
        } catch (error) {
            console.error('Dashboard update error:', error);
        }
    }

    async broadcastDashboardUpdate() {
        try {
            const update = {
                timestamp: new Date().toISOString(),
                active_connections: this.io.engine.clientsCount,
                system_status: 'operational'
            };

            this.io.emit('system_heartbeat', update);
        } catch (error) {
            console.error('Broadcast update error:', error);
        }
    }

    setupErrorHandling() {
        this.app.use((err, req, res, next) => {
            console.error('❌ API Error:', err);
            res.status(500).json({
                error: 'Internal server error',
                message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong',
                timestamp: new Date().toISOString()
            });
        });

        process.on('uncaughtException', (error) => {
            console.error('💥 Uncaught Exception:', error);
            process.exit(1);
        });

        process.on('unhandledRejection', (reason, promise) => {
            console.error('💥 Unhandled Rejection at:', promise, 'reason:', reason);
        });
    }

    async start() {
        try {
            this.server.listen(this.port, () => {
                console.log(`🚀 Social Hub Server running on port ${this.port}`);
                console.log(`📊 Dashboard available at http://localhost:${this.port}/health`);
                console.log(`🔌 WebSocket server ready for connections`);
                console.log('');
                console.log('📱 Supported platforms:', Object.keys(this.platformConnector.getPlatformStatus()));
                console.log('🤖 Automation systems:', 'Response, Curation, Scheduling');
                console.log('📤 Upload services:', 'YouTube Direct Upload');
                console.log('⏰ Scheduling:', 'Multi-platform content scheduling');
                console.log('');
                console.log('✅ Social Hub is ready for social media management!');
            });
        } catch (error) {
            console.error('💥 Failed to start server:', error);
            process.exit(1);
        }
    }

    async stop() {
        console.log('🛑 Shutting down Social Hub Server...');
        
        // Close WebSocket connections
        this.io.close();
        
        // Close HTTP server
        this.server.close(() => {
            console.log('✅ Social Hub Server shut down gracefully');
            process.exit(0);
        });
    }
}

// Start the server
const socialHubServer = new SocialHubServer();

// Graceful shutdown handlers
process.on('SIGTERM', () => socialHubServer.stop());
process.on('SIGINT', () => socialHubServer.stop());

// Start the server
socialHubServer.start().catch(error => {
    console.error('💥 Failed to start Social Hub Server:', error);
    process.exit(1);
});

export default SocialHubServer;