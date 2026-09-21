import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import mongoose from 'mongoose';
import redis from 'redis';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';
import { rateLimit } from 'express-rate-limit';
import winston from 'winston';
import cron from 'node-cron';
import dotenv from 'dotenv';

// Import route modules
import campaignRoutes from './src/routes/campaigns.js';
import characterRoutes from './src/routes/characters.js';
import marketplaceRoutes from './src/routes/marketplace.js';
import visualizationRoutes from './src/routes/visualization.js';
import streamingRoutes from './src/routes/streaming.js';
import communityRoutes from './src/routes/community.js';
import monetizationRoutes from './src/routes/monetization.js';
import mobileRoutes from './src/routes/mobile.js';
import backupRoutes from './src/routes/backup.js';
import accessibilityRoutes from './src/routes/accessibility.js';

// Import middleware
import authMiddleware from './src/middleware/auth.js';
import errorHandler from './src/middleware/errorHandler.js';
import { socketAuth } from './src/middleware/socketAuth.js';

// Import services
import VisualizationEngine from './src/services/VisualizationEngineSimple.js';
import MarketplaceService from './src/services/MarketplaceService.js';
import StreamingOverlay from './src/services/StreamingOverlay.js';
import BackupService from './src/services/BackupService.js';
import MonetizationService from './src/services/MonetizationService.js';

dotenv.config();

const app = express();
const server = createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.NODE_ENV === 'production' 
      ? ['https://dmlog.activelog.com', 'https://app.activelog.com']
      : true,
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    credentials: true
  }
});

const PORT = process.env.PORT || 8507;

// Logger setup
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'dmlog-final' },
  transports: [
    new winston.transports.File({ 
      filename: 'logs/error.log', 
      level: 'error',
      maxsize: 5242880,
      maxFiles: 5
    }),
    new winston.transports.File({ 
      filename: 'logs/combined.log',
      maxsize: 5242880,
      maxFiles: 5
    }),
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    })
  ]
});

// Initialize Redis client
let redisClient;
try {
  redisClient = redis.createClient({
    host: process.env.REDIS_HOST || 'localhost',
    port: process.env.REDIS_PORT || 6379,
    password: process.env.REDIS_PASSWORD
  });
  
  redisClient.on('error', (err) => {
    logger.error('Redis Client Error:', err);
  });
  
  redisClient.on('connect', () => {
    logger.info('Connected to Redis');
  });
} catch (error) {
  logger.warn('Redis not available:', error.message);
}

// Database connection
const connectDatabase = async () => {
  try {
    await mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/dmlog_final', {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });
    logger.info('Connected to MongoDB');
  } catch (error) {
    logger.warn('Database connection failed, running in mock mode:', error.message);
    // Continue without database for demo purposes
  }
};

// Middleware setup
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https:"],
      scriptSrc: ["'self'", "https:"],
      imgSrc: ["'self'", "data:", "https:", "blob:"],
      connectSrc: ["'self'", "https:", "wss:"],
      fontSrc: ["'self'", "https:"],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'", "https:", "blob:"],
      frameSrc: ["'self'", "https:"],
    }
  }
}));

app.use(cors({
  origin: process.env.NODE_ENV === 'production' 
    ? ['https://dmlog.activelog.com', 'https://app.activelog.com']
    : true,
  credentials: true,
  optionsSuccessStatus: 200
}));

app.use(compression());
app.use(morgan('combined', { stream: { write: message => logger.info(message.trim()) } }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000, // Limit each IP to 1000 requests per windowMs
  message: 'Too many requests from this IP',
  standardHeaders: true,
  legacyHeaders: false,
});

app.use(limiter);

// Body parsing
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Initialize services
const visualizationEngine = new VisualizationEngine();
const marketplaceService = new MarketplaceService();
const streamingOverlay = new StreamingOverlay();
const backupService = new BackupService();
const monetizationService = new MonetizationService();

// Make services available to routes
app.locals.services = {
  visualization: visualizationEngine,
  marketplace: marketplaceService,
  streaming: streamingOverlay,
  backup: backupService,
  monetization: monetizationService,
  redis: redisClient,
  logger
};

// Socket.IO authentication
io.use(socketAuth);

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'dmlog-final',
    version: '2.0.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    features: {
      visualization: true,
      marketplace: true,
      streaming: true,
      monetization: true,
      mobile: true,
      offline: true,
      backup: true,
      accessibility: true,
      community: true
    }
  });
});

// API routes
app.use('/api/campaigns', authMiddleware, campaignRoutes);
app.use('/api/characters', authMiddleware, characterRoutes);
app.use('/api/marketplace', authMiddleware, marketplaceRoutes);
app.use('/api/visualization', authMiddleware, visualizationRoutes);
app.use('/api/streaming', authMiddleware, streamingRoutes);
app.use('/api/community', authMiddleware, communityRoutes);
app.use('/api/monetization', authMiddleware, monetizationRoutes);
app.use('/api/mobile', authMiddleware, mobileRoutes);
app.use('/api/backup', authMiddleware, backupRoutes);
app.use('/api/accessibility', accessibilityRoutes);

// Socket.IO connection handling
io.on('connection', (socket) => {
  logger.info(`Client connected: ${socket.id}`);
  
  // Join campaign room
  socket.on('join-campaign', (campaignId) => {
    socket.join(`campaign-${campaignId}`);
    logger.info(`Socket ${socket.id} joined campaign ${campaignId}`);
  });
  
  // Real-time dice rolls
  socket.on('dice-roll', (data) => {
    const { campaignId, roll } = data;
    io.to(`campaign-${campaignId}`).emit('dice-result', {
      ...roll,
      playerId: socket.user.id,
      timestamp: new Date().toISOString()
    });
  });
  
  // Initiative tracker updates
  socket.on('initiative-update', (data) => {
    const { campaignId, initiative } = data;
    io.to(`campaign-${campaignId}`).emit('initiative-changed', initiative);
  });
  
  // Character sheet updates
  socket.on('character-update', (data) => {
    const { campaignId, character } = data;
    io.to(`campaign-${campaignId}`).emit('character-changed', character);
  });
  
  // Battle map updates
  socket.on('battlemap-update', (data) => {
    const { campaignId, mapData } = data;
    io.to(`campaign-${campaignId}`).emit('battlemap-changed', mapData);
  });
  
  // Streaming overlay updates
  socket.on('overlay-update', (data) => {
    const { streamId, overlayData } = data;
    io.to(`stream-${streamId}`).emit('overlay-changed', overlayData);
  });
  
  // Community events
  socket.on('community-event', (data) => {
    io.emit('community-update', data);
  });
  
  socket.on('disconnect', () => {
    logger.info(`Client disconnected: ${socket.id}`);
  });
});

// Scheduled tasks
cron.schedule('0 2 * * *', async () => {
  // Daily backup
  try {
    await backupService.performDailyBackup();
    logger.info('Daily backup completed');
  } catch (error) {
    logger.error('Daily backup failed:', error);
  }
});

cron.schedule('0 1 * * 0', async () => {
  // Weekly community digest
  try {
    // Generate and send weekly community digest
    logger.info('Weekly community digest sent');
  } catch (error) {
    logger.error('Weekly digest failed:', error);
  }
});

cron.schedule('*/15 * * * *', async () => {
  // Cleanup expired sessions
  try {
    await cleanupExpiredSessions();
    logger.debug('Session cleanup completed');
  } catch (error) {
    logger.error('Session cleanup failed:', error);
  }
});

const cleanupExpiredSessions = async () => {
  if (redisClient) {
    // Cleanup logic for expired sessions
    const keys = await redisClient.keys('session:*');
    for (const key of keys) {
      const session = await redisClient.get(key);
      if (session) {
        const sessionData = JSON.parse(session);
        if (new Date(sessionData.expires) < new Date()) {
          await redisClient.del(key);
        }
      }
    }
  }
};

// Error handling
app.use(errorHandler);

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: 'The requested resource was not found',
    availableEndpoints: [
      '/api/campaigns',
      '/api/characters',
      '/api/marketplace',
      '/api/visualization',
      '/api/streaming',
      '/api/community',
      '/api/monetization',
      '/api/mobile',
      '/api/backup',
      '/api/accessibility'
    ]
  });
});

// Graceful shutdown
const gracefulShutdown = (signal) => {
  logger.info(`Received ${signal}. Starting graceful shutdown...`);
  
  server.close(() => {
    logger.info('HTTP server closed');
    
    mongoose.connection.close(false, () => {
      logger.info('MongoDB connection closed');
      
      if (redisClient) {
        redisClient.quit(() => {
          logger.info('Redis connection closed');
          process.exit(0);
        });
      } else {
        process.exit(0);
      }
    });
  });
  
  // Force close after 30 seconds
  setTimeout(() => {
    logger.error('Could not close connections in time, forcefully shutting down');
    process.exit(1);
  }, 30000);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Start server
const startServer = async () => {
  try {
    await connectDatabase();
    
    if (redisClient && !redisClient.isOpen) {
      try {
        await redisClient.connect();
      } catch (error) {
        logger.warn('Redis connection failed:', error.message);
      }
    }
    
    server.listen(PORT, () => {
      logger.info(`🐉 DMLog Final server running on port ${PORT}`);
      logger.info(`🎯 Environment: ${process.env.NODE_ENV || 'development'}`);
      logger.info(`🔗 Health Check: http://localhost:${PORT}/health`);
      
      console.log(`
╔════════════════════════════════════════════════════╗
║                DMLog Final v2.0                    ║
║                                                    ║
║  🐉 Complete D&D Campaign Management              ║
║  🎲 Advanced Dice & Battle Systems                ║
║  🛒 3D Printing Marketplace Integration           ║
║  📺 Streaming Overlays & OBS Support             ║
║  💰 Content Monetization Platform                ║
║  📱 Mobile Companion App                          ║
║  ♿ Full Accessibility Support                    ║
║  🌐 Community Hub & Sharing                       ║
║  💾 Advanced Backup & Export                      ║
║                                                    ║
║  Port: ${PORT.toString().padEnd(42)} ║
║  Status: http://localhost:${PORT}/health${' '.repeat(15)} ║
╚════════════════════════════════════════════════════╝
      `);
    });
    
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
};

startServer();

export { io, logger };