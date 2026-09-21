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
const GameRandomizer = require('./services/gameRandomizer');
const AIDMPersonalityGenerator = require('./services/aiDMPersonalityGenerator');
const AIPlayerBots = require('./services/aiPlayerBots');
const NaturalLanguageCustomizer = require('./services/naturalLanguageCustomizer');
const PersonalLogImporter = require('./services/personalLogImporter');
const SketchToCharacterConverter = require('./services/sketchToCharacterConverter');
const StyleSelector = require('./services/styleSelector');
const CampaignGenerator = require('./services/campaignGenerator');
const TutorialEngine = require('./services/tutorialEngine');
const ProgressiveComplexitySystem = require('./services/progressiveComplexitySystem');
const ShareableTemplates = require('./services/shareableTemplates');
const QuickStartWizard = require('./services/quickStartWizard');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

// Configuration
const PORT = process.env.PORT || 8321;
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
        services.gameRandomizer = new GameRandomizer(redisClient, io, logger);
        services.aiDMPersonalityGenerator = new AIDMPersonalityGenerator(redisClient, io, logger);
        services.aiPlayerBots = new AIPlayerBots(redisClient, io, logger);
        services.naturalLanguageCustomizer = new NaturalLanguageCustomizer(redisClient, io, logger);
        services.personalLogImporter = new PersonalLogImporter(redisClient, io, logger);
        services.sketchToCharacterConverter = new SketchToCharacterConverter(redisClient, io, logger);
        services.styleSelector = new StyleSelector(redisClient, io, logger);
        services.campaignGenerator = new CampaignGenerator(redisClient, io, logger);
        services.tutorialEngine = new TutorialEngine(redisClient, io, logger);
        services.progressiveComplexitySystem = new ProgressiveComplexitySystem(redisClient, io, logger);
        services.shareableTemplates = new ShareableTemplates(redisClient, io, logger);
        services.quickStartWizard = new QuickStartWizard(redisClient, io, logger);

        logger.info('All DMLOG Instant services initialized successfully');
    } catch (error) {
        logger.error('Failed to initialize services:', error);
        process.exit(1);
    }
}

// Socket.IO connection handling
io.on('connection', (socket) => {
    logger.info('DMLOG Instant client connected:', socket.id);
    
    socket.on('join_campaign', (campaignId) => {
        socket.join(`campaign_${campaignId}`);
        logger.info(`Client ${socket.id} joined campaign ${campaignId}`);
    });
    
    socket.on('join_game_session', (sessionId) => {
        socket.join(`session_${sessionId}`);
        logger.info(`Client ${socket.id} joined game session ${sessionId}`);
    });
    
    socket.on('player_action', (data) => {
        // Broadcast player actions to campaign members
        socket.to(`campaign_${data.campaignId}`).emit('player_action', data);
    });
    
    socket.on('dm_response', (data) => {
        // Broadcast DM responses
        socket.to(`campaign_${data.campaignId}`).emit('dm_response', data);
    });
    
    socket.on('disconnect', () => {
        logger.info('DMLOG Instant client disconnected:', socket.id);
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

// Game Randomizer Routes
app.post('/api/randomizer/generate', async (req, res) => {
    try {
        const result = await services.gameRandomizer.generateRandomGame(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Game randomizer error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/randomizer/elements/:category', async (req, res) => {
    try {
        const elements = await services.gameRandomizer.getRandomElements(req.params.category, req.query);
        res.json(elements);
    } catch (error) {
        logger.error('Random elements error:', error);
        res.status(500).json({ error: error.message });
    }
});

// AI DM Personality Routes
app.post('/api/dm/personality/generate', async (req, res) => {
    try {
        const personality = await services.aiDMPersonalityGenerator.generatePersonality(req.body);
        res.json(personality);
    } catch (error) {
        logger.error('DM personality generation error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/dm/personality/:personalityId', async (req, res) => {
    try {
        const personality = await services.aiDMPersonalityGenerator.getPersonality(req.params.personalityId);
        res.json(personality);
    } catch (error) {
        logger.error('Get DM personality error:', error);
        res.status(500).json({ error: error.message });
    }
});

// AI Player Bot Routes
app.post('/api/players/bots/create', async (req, res) => {
    try {
        const bot = await services.aiPlayerBots.createPlayerBot(req.body);
        res.json(bot);
    } catch (error) {
        logger.error('Player bot creation error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/players/bots/:botId/action', async (req, res) => {
    try {
        const action = await services.aiPlayerBots.generateBotAction(req.params.botId, req.body);
        res.json(action);
    } catch (error) {
        logger.error('Bot action error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Natural Language Customization Routes
app.post('/api/customizer/parse', async (req, res) => {
    try {
        const parsed = await services.naturalLanguageCustomizer.parseCustomization(req.body);
        res.json(parsed);
    } catch (error) {
        logger.error('NL customization error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/customizer/apply', async (req, res) => {
    try {
        const result = await services.naturalLanguageCustomizer.applyCustomization(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Apply customization error:', error);
        res.status(500).json({ error: error.message });
    }
});

// PersonalLog Import Routes
app.post('/api/import/personallog', async (req, res) => {
    try {
        const imported = await services.personalLogImporter.importContent(req.body);
        res.json(imported);
    } catch (error) {
        logger.error('PersonalLog import error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/import/personallog/:importId/status', async (req, res) => {
    try {
        const status = await services.personalLogImporter.getImportStatus(req.params.importId);
        res.json(status);
    } catch (error) {
        logger.error('Import status error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Sketch to Character Routes
app.post('/api/sketch/convert', async (req, res) => {
    try {
        const character = await services.sketchToCharacterConverter.convertSketch(req.body);
        res.json(character);
    } catch (error) {
        logger.error('Sketch conversion error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/sketch/analyze', async (req, res) => {
    try {
        const analysis = await services.sketchToCharacterConverter.analyzeSketch(req.body);
        res.json(analysis);
    } catch (error) {
        logger.error('Sketch analysis error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Style Selector Routes
app.get('/api/styles/available', async (req, res) => {
    try {
        const styles = await services.styleSelector.getAvailableStyles();
        res.json(styles);
    } catch (error) {
        logger.error('Get styles error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/styles/apply', async (req, res) => {
    try {
        const result = await services.styleSelector.applyStyle(req.body);
        res.json(result);
    } catch (error) {
        logger.error('Apply style error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Campaign Generator Routes
app.post('/api/campaigns/generate', async (req, res) => {
    try {
        const campaign = await services.campaignGenerator.generateCampaign(req.body);
        res.json(campaign);
    } catch (error) {
        logger.error('Campaign generation error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/campaigns/:campaignId', async (req, res) => {
    try {
        const campaign = await services.campaignGenerator.getCampaign(req.params.campaignId);
        res.json(campaign);
    } catch (error) {
        logger.error('Get campaign error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Tutorial Engine Routes
app.get('/api/tutorials/campaigns', async (req, res) => {
    try {
        const campaigns = await services.tutorialEngine.getTutorialCampaigns(req.query);
        res.json(campaigns);
    } catch (error) {
        logger.error('Get tutorial campaigns error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/tutorials/start', async (req, res) => {
    try {
        const session = await services.tutorialEngine.startTutorial(req.body);
        res.json(session);
    } catch (error) {
        logger.error('Start tutorial error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Progressive Complexity Routes
app.get('/api/complexity/assess/:playerId', async (req, res) => {
    try {
        const assessment = await services.progressiveComplexitySystem.assessPlayer(req.params.playerId);
        res.json(assessment);
    } catch (error) {
        logger.error('Complexity assessment error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/complexity/adjust', async (req, res) => {
    try {
        const adjustment = await services.progressiveComplexitySystem.adjustComplexity(req.body);
        res.json(adjustment);
    } catch (error) {
        logger.error('Complexity adjustment error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Shareable Templates Routes
app.get('/api/templates', async (req, res) => {
    try {
        const templates = await services.shareableTemplates.getTemplates(req.query);
        res.json(templates);
    } catch (error) {
        logger.error('Get templates error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/templates/create', async (req, res) => {
    try {
        const template = await services.shareableTemplates.createTemplate(req.body);
        res.json(template);
    } catch (error) {
        logger.error('Create template error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/templates/:templateId', async (req, res) => {
    try {
        const template = await services.shareableTemplates.getTemplate(req.params.templateId);
        res.json(template);
    } catch (error) {
        logger.error('Get template error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Quick Start Wizard Routes
app.post('/api/quickstart/begin', async (req, res) => {
    try {
        const wizard = await services.quickStartWizard.beginWizard(req.body);
        res.json(wizard);
    } catch (error) {
        logger.error('Quick start error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/quickstart/:wizardId/step', async (req, res) => {
    try {
        const result = await services.quickStartWizard.processStep(req.params.wizardId, req.body);
        res.json(result);
    } catch (error) {
        logger.error('Wizard step error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Unified Dashboard Route
app.get('/api/dashboard', async (req, res) => {
    try {
        const [
            gameStats,
            dmStats,
            playerStats,
            campaignStats,
            templateStats
        ] = await Promise.all([
            services.gameRandomizer.getStats(),
            services.aiDMPersonalityGenerator.getStats(),
            services.aiPlayerBots.getStats(),
            services.campaignGenerator.getStats(),
            services.shareableTemplates.getStats()
        ]);

        res.json({
            games: gameStats,
            dms: dmStats,
            players: playerStats,
            campaigns: campaignStats,
            templates: templateStats,
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
            logger.info(`DMLOG Instant system running on port ${PORT}`);
            console.log(`🎲 DMLOG Instant Play System is running on http://localhost:${PORT}`);
            console.log(`📊 Dashboard available at http://localhost:${PORT}/api/dashboard`);
        });
    } catch (error) {
        logger.error('Failed to start server:', error);
        process.exit(1);
    }
}

startServer();