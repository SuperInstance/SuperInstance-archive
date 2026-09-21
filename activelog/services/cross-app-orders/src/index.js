require('dotenv').config();

const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');
const rateLimit = require('express-rate-limit');

const logger = require('./config/logger');
const database = require('./config/database');
const redis = require('./config/redis');

// Import routes
const orderRoutes = require('./controllers/orderController');
const makerRoutes = require('./controllers/makerController');
const pricingRoutes = require('./controllers/pricingController');
const paymentRoutes = require('./controllers/paymentController');
const trackingRoutes = require('./controllers/trackingController');
const qualityRoutes = require('./controllers/qualityController');
const disputeRoutes = require('./controllers/disputeController');
const calendarRoutes = require('./controllers/calendarController');
const materialRoutes = require('./controllers/materialController');
const shippingRoutes = require('./controllers/shippingController');
const notificationRoutes = require('./controllers/notificationController');

// Import middleware
const authMiddleware = require('./middleware/auth');
const { errorHandler, notFoundHandler } = require('./middleware/errorHandler');

class CrossAppOrderService {
  constructor() {
    this.app = express();
    this.port = process.env.PORT || 8301;
    this.setupMiddleware();
    this.setupRoutes();
    this.setupErrorHandling();
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
          connectSrc: ["'self'"]
        }
      }
    }));

    // CORS configuration
    this.app.use(cors({
      origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000', 'http://localhost:3001'],
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
    }));

    // Compression
    this.app.use(compression({
      filter: (req, res) => {
        if (req.headers['x-no-compression']) return false;
        return compression.filter(req, res);
      },
      threshold: 1024
    }));

    // Rate limiting
    const limiter = rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: process.env.NODE_ENV === 'production' ? 100 : 1000,
      message: {
        error: 'Too many requests from this IP, please try again later',
        retryAfter: '15 minutes'
      },
      standardHeaders: true,
      legacyHeaders: false
    });
    this.app.use(limiter);

    // Body parsing middleware
    this.app.use(express.json({ 
      limit: '10mb',
      verify: (req, res, buf) => {
        req.rawBody = buf;
      }
    }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // Request logging
    this.app.use((req, res, next) => {
      logger.http(req, res);
      next();
    });

    // Request ID middleware
    this.app.use((req, res, next) => {
      req.id = req.headers['x-request-id'] || require('uuid').v4();
      res.setHeader('X-Request-ID', req.id);
      next();
    });

    // Health check endpoint
    this.app.get('/health', async (req, res) => {
      try {
        const dbHealth = await database.healthCheck();
        const redisHealth = await redis.healthCheck();
        
        const health = {
          status: 'ok',
          timestamp: new Date().toISOString(),
          service: 'cross-app-orders',
          version: process.env.npm_package_version || '1.0.0',
          uptime: process.uptime(),
          database: dbHealth,
          redis: redisHealth,
          memory: process.memoryUsage(),
          pid: process.pid
        };

        const isHealthy = dbHealth.healthy && redisHealth.healthy;
        res.status(isHealthy ? 200 : 503).json(health);
      } catch (error) {
        logger.error('Health check failed:', error);
        res.status(503).json({
          status: 'error',
          error: error.message,
          timestamp: new Date().toISOString()
        });
      }
    });

    // API info endpoint
    this.app.get('/', (req, res) => {
      res.json({
        service: 'Cross-App Orders Service',
        description: 'Order routing system for cross-platform 3D printing between DMLog and MakerLog',
        version: process.env.npm_package_version || '1.0.0',
        documentation: '/api/docs',
        health: '/health',
        timestamp: new Date().toISOString()
      });
    });
  }

  setupRoutes() {
    // API routes
    this.app.use('/api/orders', orderRoutes);
    this.app.use('/api/makers', makerRoutes);
    this.app.use('/api/pricing', pricingRoutes);
    this.app.use('/api/payments', paymentRoutes);
    this.app.use('/api/tracking', trackingRoutes);
    this.app.use('/api/quality', qualityRoutes);
    this.app.use('/api/disputes', disputeRoutes);
    this.app.use('/api/calendar', calendarRoutes);
    this.app.use('/api/materials', materialRoutes);
    this.app.use('/api/shipping', shippingRoutes);
    this.app.use('/api/notifications', notificationRoutes);

    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Route not found',
        method: req.method,
        path: req.originalUrl,
        timestamp: new Date().toISOString()
      });
    });
  }

  setupErrorHandling() {
    this.app.use(errorHandler);

    // Global error handlers
    process.on('uncaughtException', (error) => {
      console.error('Uncaught Exception:', error);
      this.gracefulShutdown('SIGTERM');
    });

    process.on('unhandledRejection', (reason, promise) => {
      console.error('Unhandled Rejection at:', promise, 'reason:', reason);
      this.gracefulShutdown('SIGTERM');
    });

    process.on('SIGTERM', () => {
      console.log('SIGTERM received, shutting down gracefully');
      this.gracefulShutdown('SIGTERM');
    });

    process.on('SIGINT', () => {
      console.log('SIGINT received, shutting down gracefully');
      this.gracefulShutdown('SIGINT');
    });
  }

  async start() {
    try {
      // Connect to databases
      await database.connect();
      await redis.connect();

      // Start HTTP server
      this.server = this.app.listen(this.port, () => {
        logger.info(`Cross-App Orders Service started`, {
          port: this.port,
          environment: process.env.NODE_ENV || 'development',
          pid: process.pid,
          timestamp: new Date().toISOString()
        });
      });

      // Setup server timeouts
      this.server.timeout = 30000; // 30 seconds
      this.server.keepAliveTimeout = 65000; // 65 seconds
      this.server.headersTimeout = 66000; // 66 seconds

      return this.server;
    } catch (error) {
      logger.error('Failed to start service:', error);
      process.exit(1);
    }
  }

  async gracefulShutdown(signal) {
    logger.info(`${signal} received, starting graceful shutdown...`);

    // Stop accepting new requests
    if (this.server) {
      this.server.close(async () => {
        logger.info('HTTP server closed');

        try {
          // Close database connections
          await database.disconnect();
          await redis.disconnect();

          logger.info('All connections closed, exiting process');
          process.exit(0);
        } catch (error) {
          logger.error('Error during graceful shutdown:', error);
          process.exit(1);
        }
      });

      // Force shutdown after timeout
      setTimeout(() => {
        logger.error('Graceful shutdown timeout, forcing exit');
        process.exit(1);
      }, 30000);
    } else {
      process.exit(0);
    }
  }
}

// Start the service if this file is run directly
if (require.main === module) {
  const service = new CrossAppOrderService();
  service.start().catch((error) => {
    logger.error('Service startup failed:', error);
    process.exit(1);
  });
}

module.exports = CrossAppOrderService;