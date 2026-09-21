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
const ExposedFolderProcessor = require('./services/exposedFolderProcessor');
const PersonalizedAdServer = require('./services/personalizedAdServer');
const AffiliateTracker = require('./services/affiliateTracker');
const ConversionOptimizer = require('./services/conversionOptimizer');
const ABTestingEngine = require('./services/abTestingEngine');
const EmailCampaignManager = require('./services/emailCampaignManager');
const SocialMediaIntegrator = require('./services/socialMediaIntegrator');
const SEOOptimizer = require('./services/seoOptimizer');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

// Configuration
const PORT = process.env.PORT || 8313;
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
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));
app.use(morgan('combined', { stream: { write: message => logger.info(message.trim()) } }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // Limit each IP to 100 requests per windowMs
    message: 'Too many requests from this IP'
});
app.use('/api/', limiter);

// Initialize services
let services = {};

async function initializeServices() {
    try {
        services.exposedFolderProcessor = new ExposedFolderProcessor(redisClient, io, logger);
        services.personalizedAdServer = new PersonalizedAdServer(redisClient, io, logger);
        services.affiliateTracker = new AffiliateTracker(redisClient, io, logger);
        services.conversionOptimizer = new ConversionOptimizer(redisClient, io, logger);
        services.abTestingEngine = new ABTestingEngine(redisClient, io, logger);
        services.emailCampaignManager = new EmailCampaignManager(redisClient, io, logger);
        services.socialMediaIntegrator = new SocialMediaIntegrator(redisClient, io, logger);
        services.seoOptimizer = new SEOOptimizer(redisClient, io, logger);

        logger.info('All marketing services initialized successfully');
    } catch (error) {
        logger.error('Failed to initialize services:', error);
        process.exit(1);
    }
}

// Socket.IO connection handling
io.on('connection', (socket) => {
    logger.info('Marketing client connected:', socket.id);
    
    socket.on('join_campaign', (campaignId) => {
        socket.join(`campaign_${campaignId}`);
        logger.info(`Client ${socket.id} joined campaign ${campaignId}`);
    });
    
    socket.on('join_affiliate', (affiliateId) => {
        socket.join(`affiliate_${affiliateId}`);
        logger.info(`Client ${socket.id} joined affiliate ${affiliateId}`);
    });
    
    socket.on('disconnect', () => {
        logger.info('Marketing client disconnected:', socket.id);
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

// API Routes

// Exposed Folder Processing Routes
app.post('/api/exposed-folders/process', async (req, res) => {
    try {
        const result = await services.exposedFolderProcessor.processFolder(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Exposed folder processing error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/exposed-folders/:folderId/assets', async (req, res) => {
    try {
        const assets = await services.exposedFolderProcessor.getFolderAssets(req.params.folderId);
        res.json(assets);
    } catch (error) {
        logger.error('Get folder assets error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Personalized Ad Server Routes
app.post('/api/ads/serve', async (req, res) => {
    try {
        const ad = await services.personalizedAdServer.serveAd(req.body);
        res.json(ad);
    } catch (error) {
        logger.error('Ad serving error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/ads/campaigns', async (req, res) => {
    try {
        const campaign = await services.personalizedAdServer.createCampaign(req.body);
        res.json(campaign);
    } catch (error) {
        logger.error('Campaign creation error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/ads/campaigns/:campaignId/performance', async (req, res) => {
    try {
        const performance = await services.personalizedAdServer.getCampaignPerformance(req.params.campaignId);
        res.json(performance);
    } catch (error) {
        logger.error('Campaign performance error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Affiliate Tracking Routes
app.post('/api/affiliates/register', async (req, res) => {
    try {
        const affiliate = await services.affiliateTracker.registerAffiliate(req.body);
        res.json(affiliate);
    } catch (error) {
        logger.error('Affiliate registration error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/affiliates/track-click', async (req, res) => {
    try {
        const tracking = await services.affiliateTracker.trackClick(req.body);
        res.json(tracking);
    } catch (error) {
        logger.error('Affiliate click tracking error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/affiliates/:affiliateId/performance', async (req, res) => {
    try {
        const performance = await services.affiliateTracker.getAffiliatePerformance(req.params.affiliateId);
        res.json(performance);
    } catch (error) {
        logger.error('Affiliate performance error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Conversion Optimization Routes
app.post('/api/conversions/track', async (req, res) => {
    try {
        const conversion = await services.conversionOptimizer.trackConversion(req.body);
        res.json(conversion);
    } catch (error) {
        logger.error('Conversion tracking error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/conversions/optimize', async (req, res) => {
    try {
        const optimization = await services.conversionOptimizer.optimizeConversions(req.body);
        res.json(optimization);
    } catch (error) {
        logger.error('Conversion optimization error:', error);
        res.status(500).json({ error: error.message });
    }
});

// A/B Testing Routes
app.post('/api/ab-tests/create', async (req, res) => {
    try {
        const test = await services.abTestingEngine.createTest(req.body);
        res.json(test);
    } catch (error) {
        logger.error('A/B test creation error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/ab-tests/:testId/participate', async (req, res) => {
    try {
        const participation = await services.abTestingEngine.participateInTest(req.params.testId, req.body);
        res.json(participation);
    } catch (error) {
        logger.error('A/B test participation error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/ab-tests/:testId/results', async (req, res) => {
    try {
        const results = await services.abTestingEngine.getTestResults(req.params.testId);
        res.json(results);
    } catch (error) {
        logger.error('A/B test results error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Email Campaign Routes
app.post('/api/email/campaigns', async (req, res) => {
    try {
        const campaign = await services.emailCampaignManager.createCampaign(req.body);
        res.json(campaign);
    } catch (error) {
        logger.error('Email campaign creation error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/email/campaigns/:campaignId/send', async (req, res) => {
    try {
        const result = await services.emailCampaignManager.sendCampaign(req.params.campaignId, req.body);
        res.json(result);
    } catch (error) {
        logger.error('Email campaign send error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/email/campaigns/:campaignId/analytics', async (req, res) => {
    try {
        const analytics = await services.emailCampaignManager.getCampaignAnalytics(req.params.campaignId);
        res.json(analytics);
    } catch (error) {
        logger.error('Email campaign analytics error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Social Media Integration Routes
app.post('/api/social/accounts/connect', async (req, res) => {
    try {
        const connection = await services.socialMediaIntegrator.connectAccount(req.body);
        res.json(connection);
    } catch (error) {
        logger.error('Social account connection error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/social/posts/schedule', async (req, res) => {
    try {
        const post = await services.socialMediaIntegrator.schedulePost(req.body);
        res.json(post);
    } catch (error) {
        logger.error('Social post scheduling error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/social/analytics/:accountId', async (req, res) => {
    try {
        const analytics = await services.socialMediaIntegrator.getAnalytics(req.params.accountId);
        res.json(analytics);
    } catch (error) {
        logger.error('Social analytics error:', error);
        res.status(500).json({ error: error.message });
    }
});

// SEO Optimization Routes
app.post('/api/seo/analyze', async (req, res) => {
    try {
        const analysis = await services.seoOptimizer.analyzePage(req.body);
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

app.get('/api/seo/rankings/:domain', async (req, res) => {
    try {
        const rankings = await services.seoOptimizer.trackRankings(req.params.domain);
        res.json(rankings);
    } catch (error) {
        logger.error('SEO rankings error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Unified Analytics Route
app.get('/api/analytics/dashboard', async (req, res) => {
    try {
        const [
            adPerformance,
            affiliateStats,
            conversionStats,
            emailStats,
            socialStats,
            seoStats
        ] = await Promise.all([
            services.personalizedAdServer.getOverallPerformance(),
            services.affiliateTracker.getOverallStats(),
            services.conversionOptimizer.getOverallStats(),
            services.emailCampaignManager.getOverallStats(),
            services.socialMediaIntegrator.getOverallStats(),
            services.seoOptimizer.getOverallStats()
        ]);

        res.json({
            ads: adPerformance,
            affiliates: affiliateStats,
            conversions: conversionStats,
            email: emailStats,
            social: socialStats,
            seo: seoStats,
            timestamp: new Date()
        });
    } catch (error) {
        logger.error('Dashboard analytics error:', error);
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
            logger.info(`Marketing automation system running on port ${PORT}`);
            console.log(`🚀 Marketing Automation System is running on http://localhost:${PORT}`);
            console.log(`📊 Dashboard available at http://localhost:${PORT}/api/analytics/dashboard`);
        });
    } catch (error) {
        logger.error('Failed to start server:', error);
        process.exit(1);
    }
}

startServer();