const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const mongoose = require('mongoose');
const redis = require('redis');
const rateLimit = require('express-rate-limit');
const winston = require('winston');
const cron = require('node-cron');
const path = require('path');

// Import configuration and routes
const config = require('../config/config');
const routes = require('../routes');
const ParentChildController = require('../controllers/ParentChildController');

// Initialize Express app
const app = express();

// Logger setup
const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'ad-engine' },
  transports: [
    new winston.transports.File({ 
      filename: 'logs/error.log', 
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5
    }),
    new winston.transports.File({ 
      filename: 'logs/combined.log',
      maxsize: 5242880, // 5MB
      maxFiles: 5
    })
  ]
});

// Add console transport for development
if (config.env === 'development') {
  logger.add(new winston.transports.Console({
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.simple()
    )
  }));
}

// Global error handler
process.on('uncaughtException', (error) => {
  logger.error('Uncaught Exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Initialize Redis client
let redisClient;
try {
  redisClient = redis.createClient(config.redis);
  redisClient.on('error', (err) => {
    logger.error('Redis Client Error:', err);
  });
  redisClient.on('connect', () => {
    logger.info('Connected to Redis');
  });
} catch (error) {
  logger.warn('Redis not available, running without cache:', error.message);
}

// Middleware setup
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
}));

app.use(cors({
  origin: process.env.NODE_ENV === 'production' 
    ? ['https://activelog.com', 'https://app.activelog.com']
    : true,
  credentials: true,
  optionsSuccessStatus: 200
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: config.rateLimiting.windowMs,
  max: config.rateLimiting.max,
  message: config.rateLimiting.message,
  standardHeaders: true,
  legacyHeaders: false,
  handler: (req, res) => {
    logger.warn(`Rate limit exceeded for IP: ${req.ip}`);
    res.status(429).json({ error: config.rateLimiting.message });
  }
});

app.use('/api', limiter);

// Body parsing middleware
app.use(express.json({ 
  limit: '10mb',
  verify: (req, res, buf) => {
    req.rawBody = buf;
  }
}));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    logger.info('HTTP Request', {
      method: req.method,
      url: req.url,
      status: res.statusCode,
      duration: `${duration}ms`,
      ip: req.ip,
      userAgent: req.get('User-Agent')
    });
  });
  
  next();
});

// Health check endpoint (before auth middleware)
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'ad-engine',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    version: '1.0.0'
  });
});

// Authentication middleware (mock implementation)
const authMiddleware = async (req, res, next) => {
  try {
    // In a real app, this would validate JWT tokens
    const userId = req.params.userId || req.params.parentId || req.params.childId;
    
    if (!userId) {
      return res.status(400).json({ error: 'User ID required' });
    }
    
    // Mock user validation - in real app, validate JWT and load user
    req.user = {
      id: userId,
      authenticated: true,
      timestamp: new Date()
    };
    
    next();
  } catch (error) {
    logger.error('Authentication error:', error);
    res.status(401).json({ error: 'Authentication required' });
  }
};

// Apply auth middleware to protected routes
app.use('/api/users', authMiddleware);
app.use('/api/parents', authMiddleware);
app.use('/api/children', authMiddleware);

// API routes
app.use('/api', routes);

// Static file serving for ad assets
app.use('/assets', express.static(path.join(__dirname, '../public'), {
  maxAge: '1d',
  etag: false
}));

// Mock ad assets endpoints
app.get('/api/ads/mock/:type', (req, res) => {
  const { type } = req.params;
  const mockAds = {
    'banner.jpg': { width: 728, height: 90, format: 'image/jpeg' },
    'interstitial.jpg': { width: 320, height: 480, format: 'image/jpeg' },
    'video.mp4': { duration: 30, format: 'video/mp4' },
    'welcome.jpg': { width: 300, height: 250, format: 'image/jpeg' }
  };
  
  const adInfo = mockAds[type];
  if (!adInfo) {
    return res.status(404).json({ error: 'Ad asset not found' });
  }
  
  // Return mock ad metadata
  res.json({
    type,
    url: `/assets/ads/${type}`,
    metadata: adInfo,
    timestamp: new Date().toISOString()
  });
});

// Database connection
const connectDatabase = async () => {
  try {
    await mongoose.connect(config.mongodb.uri, config.mongodb.options);
    logger.info('Connected to MongoDB');
    
    // Create indexes for better performance
    const User = require('../models/User');
    await User.createIndexes();
    logger.info('Database indexes created');
    
  } catch (error) {
    logger.error('Database connection failed:', error);
    
    if (config.env === 'production') {
      process.exit(1);
    } else {
      logger.warn('Running without database connection in development mode');
    }
  }
};

// Scheduled tasks
const setupScheduledTasks = () => {
  const parentChildController = new ParentChildController();
  
  // Daily allowance reset at midnight
  cron.schedule('0 0 * * *', async () => {
    try {
      logger.info('Running daily allowance reset task');
      // This would typically make an internal API call or run the logic directly
      const result = await parentChildController.processDailyAllowanceReset(
        { body: {} }, 
        { 
          json: (data) => {
            logger.info('Daily allowance reset completed:', data);
          }
        }
      );
    } catch (error) {
      logger.error('Daily allowance reset failed:', error);
    }
  });
  
  // Weekly usage tier recalculation
  cron.schedule('0 2 * * 0', async () => {
    try {
      logger.info('Running weekly usage tier recalculation');
      // This would recalculate user tiers based on weekly usage
      // Implementation would go here
    } catch (error) {
      logger.error('Usage tier recalculation failed:', error);
    }
  });
  
  // Hourly metrics collection
  cron.schedule('0 * * * *', async () => {
    try {
      // Collect and log system metrics
      const metrics = {
        timestamp: new Date().toISOString(),
        memory: process.memoryUsage(),
        uptime: process.uptime(),
        // Additional metrics would be collected here
      };
      
      logger.info('System metrics:', metrics);
    } catch (error) {
      logger.error('Metrics collection failed:', error);
    }
  });
  
  logger.info('Scheduled tasks initialized');
};

// Analytics and monitoring
const setupAnalytics = () => {
  // Track service metrics
  setInterval(() => {
    const metrics = {
      memoryUsage: process.memoryUsage(),
      uptime: process.uptime(),
      timestamp: new Date().toISOString()
    };
    
    // In production, this would send metrics to monitoring service
    if (config.env === 'development') {
      logger.debug('Service metrics:', metrics);
    }
  }, 60000); // Every minute
};

// Graceful shutdown
const gracefulShutdown = (signal) => {
  logger.info(`Received ${signal}. Starting graceful shutdown...`);
  
  const cleanup = async () => {
    try {
      // Close database connection
      if (mongoose.connection.readyState === 1) {
        await mongoose.connection.close();
        logger.info('Database connection closed');
      }
      
      // Close Redis connection
      if (redisClient && redisClient.isOpen) {
        await redisClient.quit();
        logger.info('Redis connection closed');
      }
      
      logger.info('Graceful shutdown completed');
      process.exit(0);
      
    } catch (error) {
      logger.error('Error during shutdown:', error);
      process.exit(1);
    }
  };
  
  // Set timeout for forceful shutdown
  const shutdownTimeout = setTimeout(() => {
    logger.error('Shutdown timeout exceeded, forcing exit');
    process.exit(1);
  }, 10000); // 10 seconds
  
  cleanup().then(() => {
    clearTimeout(shutdownTimeout);
  });
};

// Register shutdown handlers
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// 404 handler for non-API routes
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: 'The requested resource was not found',
    availableEndpoints: {
      api: '/api',
      health: '/health',
      docs: '/api/docs',
      status: '/api/status'
    }
  });
});

// Global error handler
app.use((error, req, res, next) => {
  logger.error('Unhandled error:', {
    error: error.message,
    stack: error.stack,
    url: req.url,
    method: req.method,
    ip: req.ip
  });
  
  // Don't expose internal errors in production
  const message = config.env === 'production' 
    ? 'Internal Server Error' 
    : error.message;
  
  res.status(error.status || 500).json({
    error: 'Internal Server Error',
    message,
    timestamp: new Date().toISOString(),
    requestId: req.get('X-Request-ID') || 'unknown'
  });
});

// Start server
const startServer = async () => {
  try {
    // Connect to database
    await connectDatabase();
    
    // Connect to Redis (optional)
    if (redisClient) {
      try {
        await redisClient.connect();
      } catch (error) {
        logger.warn('Redis connection failed, continuing without cache:', error.message);
      }
    }
    
    // Setup scheduled tasks
    setupScheduledTasks();
    
    // Setup analytics
    setupAnalytics();
    
    // Start HTTP server
    const server = app.listen(config.port, () => {
      logger.info(`🚀 Ad Engine server running on port ${config.port}`);
      logger.info(`📊 Environment: ${config.env}`);
      logger.info(`🔗 API Documentation: http://localhost:${config.port}/api/docs`);
      logger.info(`❤️  Health Check: http://localhost:${config.port}/health`);
      
      console.log(`
╔════════════════════════════════════════╗
║        ActiveLog Ad Engine             ║
║                                        ║
║  🎯 Smart Ad Monetization System       ║
║  💰 Compute Currency Credits (CCC)     ║
║  📊 Usage-Based Ad Frequency           ║
║  👨‍👩‍👧‍👦 Parent-Child Controls            ║
║  🎓 Educational Rewards                ║
║  ⭐ Review-Based Earnings              ║
║                                        ║
║  Port: ${config.port.toString().padEnd(31)} ║
║  Status: http://localhost:${config.port}/health${' '.repeat(7)} ║
║  Docs: http://localhost:${config.port}/api/docs${' '.repeat(5)} ║
╚════════════════════════════════════════╝
      `);
    });
    
    // Handle server errors
    server.on('error', (error) => {
      if (error.code === 'EADDRINUSE') {
        logger.error(`Port ${config.port} is already in use`);
        process.exit(1);
      } else {
        logger.error('Server error:', error);
      }
    });
    
    // Graceful shutdown handler
    const shutdown = () => {
      logger.info('Shutting down HTTP server...');
      server.close(() => {
        logger.info('HTTP server closed');
        gracefulShutdown('SERVER_CLOSE');
      });
    };
    
    process.on('SIGTERM', shutdown);
    process.on('SIGINT', shutdown);
    
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
};

// Export app for testing
module.exports = app;

// Start server if this file is run directly
if (require.main === module) {
  startServer().catch((error) => {
    logger.error('Server startup failed:', error);
    process.exit(1);
  });
}