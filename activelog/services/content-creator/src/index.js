const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const Redis = require('redis');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const morgan = require('morgan');
const winston = require('winston');

// Service imports
const GameEngineVideoPipeline = require('./services/gameEngineVideoPipeline');
const MultiPlatformPublisher = require('./services/multiPlatformPublisher');
const ShotByShotEditor = require('./services/shotByShotEditor');
const AISceneGenerator = require('./services/aiSceneGenerator');
const RenderingQueue = require('./services/renderingQueue');
const CollaborativeEditor = require('./services/collaborativeEditor');
const VersionControl = require('./services/versionControl');
const RenderFarmIntegration = require('./services/renderFarmIntegration');
const FormatOptimizer = require('./services/formatOptimizer');
const ThumbnailGenerator = require('./services/thumbnailGenerator');
const SEOOptimizer = require('./services/seoOptimizer');
const MonetizationTracker = require('./services/monetizationTracker');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

// Configuration
const PORT = process.env.PORT || 8322;
const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

// Logger setup
const logger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
    ),
    transports: [
        new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
        new winston.transports.File({ filename: 'logs/combined.log' }),
        new winston.transports.Console()
    ]
});

// Redis client
const redisClient = Redis.createClient({ url: REDIS_URL });
redisClient.on('error', (err) => logger.error('Redis error:', err));
redisClient.connect();

// Middleware
app.use(helmet());
app.use(cors());
app.use(compression());
app.use(express.json({ limit: '100mb' }));
app.use(express.urlencoded({ extended: true, limit: '100mb' }));
app.use(morgan('combined', { stream: { write: message => logger.info(message.trim()) } }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 1000, // Limit each IP to 1000 requests per windowMs
    message: 'Too many requests from this IP'
});
app.use('/api/', limiter);

// Initialize services
let services = {};

async function initializeServices() {
    try {
        services.gameEngineVideoPipeline = new GameEngineVideoPipeline(redisClient, io, logger);
        services.multiPlatformPublisher = new MultiPlatformPublisher(redisClient, io, logger);
        services.shotByShotEditor = new ShotByShotEditor(redisClient, io, logger);
        services.aiSceneGenerator = new AISceneGenerator(redisClient, io, logger);
        services.renderingQueue = new RenderingQueue(redisClient, io, logger);
        services.collaborativeEditor = new CollaborativeEditor(redisClient, io, logger);
        services.versionControl = new VersionControl(redisClient, io, logger);
        services.renderFarmIntegration = new RenderFarmIntegration(redisClient, io, logger);
        services.formatOptimizer = new FormatOptimizer(redisClient, io, logger);
        services.thumbnailGenerator = new ThumbnailGenerator(redisClient, io, logger);
        services.seoOptimizer = new SEOOptimizer(redisClient, io, logger);
        services.monetizationTracker = new MonetizationTracker(redisClient, io, logger);

        logger.info('All Content Creator services initialized successfully');
    } catch (error) {
        logger.error('Failed to initialize services:', error);
        process.exit(1);
    }
}

// Socket.IO connection handling
io.on('connection', (socket) => {
    logger.info('Content Creator client connected:', socket.id);
    
    socket.on('join_project', (projectId) => {
        socket.join(`project_${projectId}`);
        logger.info(`Client ${socket.id} joined project ${projectId}`);
    });
    
    socket.on('join_render_queue', (queueId) => {
        socket.join(`render_queue_${queueId}`);
        logger.info(`Client ${socket.id} joined render queue ${queueId}`);
    });
    
    socket.on('editor_action', (data) => {
        socket.to(`project_${data.projectId}`).emit('editor_action', data);
    });
    
    socket.on('render_update', (data) => {
        socket.to(`render_queue_${data.queueId}`).emit('render_update', data);
    });
    
    socket.on('disconnect', () => {
        logger.info('Content Creator client disconnected:', socket.id);
    });
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.status(200).json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        services: Object.keys(services).length,
        uptime: process.uptime()
    });
});

// Game Engine to Video Pipeline Routes
app.post('/api/pipeline/capture/start', async (req, res) => {
    try {
        const result = await services.gameEngineVideoPipeline.startCapture(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Start capture error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/pipeline/capture/stop', async (req, res) => {
    try {
        const result = await services.gameEngineVideoPipeline.stopCapture(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Stop capture error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/pipeline/process', async (req, res) => {
    try {
        const result = await services.gameEngineVideoPipeline.processGameplayFootage(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Process footage error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Multi-Platform Publishing Routes
app.post('/api/publisher/platforms/connect', async (req, res) => {
    try {
        const result = await services.multiPlatformPublisher.connectPlatform(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Connect platform error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/publisher/publish', async (req, res) => {
    try {
        const result = await services.multiPlatformPublisher.publishToMultiplePlatforms(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Multi-platform publish error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/publisher/platforms/:platformId/analytics', async (req, res) => {
    try {
        const analytics = await services.multiPlatformPublisher.getPlatformAnalytics(req.params.platformId);
        res.json(analytics);
    } catch (error) {
        logger.error('Get platform analytics error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Shot-by-Shot Editor Routes
app.post('/api/editor/projects/create', async (req, res) => {
    try {
        const project = await services.shotByShotEditor.createProject(req.body);
        res.json(project);
    } catch (error) {
        logger.error('Create project error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/editor/shots/add', async (req, res) => {
    try {
        const shot = await services.shotByShotEditor.addShot(req.body);
        res.json(shot);
    } catch (error) {
        logger.error('Add shot error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.put('/api/editor/shots/:shotId/edit', async (req, res) => {
    try {
        const result = await services.shotByShotEditor.editShot(req.params.shotId, req.body);
        res.json(result);
    } catch (error) {
        logger.error('Edit shot error:', error);
        res.status(500).json({ error: error.message });
    }
});

// AI Scene Generation Routes
app.post('/api/ai/scenes/generate', async (req, res) => {
    try {
        const scene = await services.aiSceneGenerator.generateScene(req.body);
        res.json(scene);
    } catch (error) {
        logger.error('Generate scene error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/ai/scripts/generate', async (req, res) => {
    try {
        const script = await services.aiSceneGenerator.generateScript(req.body);
        res.json(script);
    } catch (error) {
        logger.error('Generate script error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Rendering Queue Routes
app.post('/api/render/queue/submit', async (req, res) => {
    try {
        const job = await services.renderingQueue.submitRenderJob(req.body);
        res.json(job);
    } catch (error) {
        logger.error('Submit render job error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/render/queue/:queueId/status', async (req, res) => {
    try {
        const status = await services.renderingQueue.getQueueStatus(req.params.queueId);
        res.json(status);
    } catch (error) {
        logger.error('Get queue status error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Collaborative Editing Routes
app.post('/api/collaboration/sessions/create', async (req, res) => {
    try {
        const session = await services.collaborativeEditor.createCollaborationSession(req.body);
        res.json(session);
    } catch (error) {
        logger.error('Create collaboration session error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/collaboration/invite', async (req, res) => {
    try {
        const result = await services.collaborativeEditor.inviteCollaborator(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Invite collaborator error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Version Control Routes
app.post('/api/version/projects/:projectId/commit', async (req, res) => {
    try {
        const commit = await services.versionControl.createCommit(req.params.projectId, req.body);
        res.json(commit);
    } catch (error) {
        logger.error('Create commit error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/version/projects/:projectId/branch', async (req, res) => {
    try {
        const branch = await services.versionControl.createBranch(req.params.projectId, req.body);
        res.json(branch);
    } catch (error) {
        logger.error('Create branch error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Render Farm Integration Routes
app.post('/api/renderfarm/nodes/register', async (req, res) => {
    try {
        const node = await services.renderFarmIntegration.registerRenderNode(req.body);
        res.json(node);
    } catch (error) {
        logger.error('Register render node error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/renderfarm/distribute', async (req, res) => {
    try {
        const result = await services.renderFarmIntegration.distributeRenderTask(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Distribute render task error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Format Optimization Routes
app.post('/api/format/optimize', async (req, res) => {
    try {
        const result = await services.formatOptimizer.optimizeForPlatform(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Format optimization error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/format/presets/:platform', async (req, res) => {
    try {
        const presets = await services.formatOptimizer.getPlatformPresets(req.params.platform);
        res.json(presets);
    } catch (error) {
        logger.error('Get platform presets error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Thumbnail Generator Routes
app.post('/api/thumbnails/generate', async (req, res) => {
    try {
        const thumbnail = await services.thumbnailGenerator.generateThumbnail(req.body);
        res.json(thumbnail);
    } catch (error) {
        logger.error('Generate thumbnail error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/thumbnails/a-b-test', async (req, res) => {
    try {
        const test = await services.thumbnailGenerator.createABTest(req.body);
        res.json(test);
    } catch (error) {
        logger.error('Create A/B test error:', error);
        res.status(500).json({ error: error.message });
    }
});

// SEO Optimization Routes
app.post('/api/seo/analyze', async (req, res) => {
    try {
        const analysis = await services.seoOptimizer.analyzeContent(req.body);
        res.json(analysis);
    } catch (error) {
        logger.error('SEO analysis error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/seo/keywords/research', async (req, res) => {
    try {
        const keywords = await services.seoOptimizer.researchKeywords(req.body);
        res.json(keywords);
    } catch (error) {
        logger.error('Keyword research error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Monetization Tracking Routes
app.post('/api/monetization/revenue/track', async (req, res) => {
    try {
        const result = await services.monetizationTracker.trackRevenue(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Track revenue error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/monetization/analytics/:projectId', async (req, res) => {
    try {
        const analytics = await services.monetizationTracker.getMonetizationAnalytics(req.params.projectId);
        res.json(analytics);
    } catch (error) {
        logger.error('Get monetization analytics error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Unified Dashboard Route
app.get('/api/dashboard', async (req, res) => {
    try {
        const [
            pipelineStats,
            publisherStats,
            editorStats,
            renderStats,
            monetizationStats
        ] = await Promise.all([
            services.gameEngineVideoPipeline.getStats(),
            services.multiPlatformPublisher.getStats(),
            services.shotByShotEditor.getStats(),
            services.renderingQueue.getStats(),
            services.monetizationTracker.getStats()
        ]);

        res.json({
            pipeline: pipelineStats,
            publisher: publisherStats,
            editor: editorStats,
            rendering: renderStats,
            monetization: monetizationStats,
            timestamp: new Date()
        });
    } catch (error) {
        logger.error('Dashboard error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    logger.error('Unhandled error:', err);
    res.status(500).json({ error: 'Internal server error' });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({ error: 'Route not found' });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
    logger.info('SIGTERM received, shutting down gracefully');
    server.close(() => {
        redisClient.disconnect();
        process.exit(0);
    });
});

// Start server
async function startServer() {
    try {
        await initializeServices();
        
        server.listen(PORT, () => {
            logger.info(`Content Creator system running on port ${PORT}`);
            console.log(`🎬 Content Creator Pipeline is running on http://localhost:${PORT}`);
            console.log(`📊 Dashboard available at http://localhost:${PORT}/api/dashboard`);
        });
    } catch (error) {
        logger.error('Failed to start server:', error);
        process.exit(1);
    }
}

startServer();