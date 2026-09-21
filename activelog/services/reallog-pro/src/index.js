import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';
import dotenv from 'dotenv';
import rateLimit from 'express-rate-limit';
import slowDown from 'express-slow-down';
import session from 'express-session';
import RedisStore from 'connect-redis';
import { createClient } from 'redis';
import path from 'path';
import { fileURLToPath } from 'url';
import http from 'http';
import { Server } from 'socket.io';

// Services
import SocialMediaService from './social/SocialMediaService.js';
import CommentManagementService from './comments/CommentManagementService.js';
import AutomationService from './automation/AutomationService.js';
import ProfileCurationService from './profile/ProfileCurationService.js';
import ExposureOptimizationService from './exposure/ExposureOptimizationService.js';
import AffiliateTrackingService from './affiliate/AffiliateTrackingService.js';
import VideoHostingService from './video/VideoHostingService.js';
import DiscountCodeService from './discounts/DiscountCodeService.js';
import AnalyticsService from './analytics/AnalyticsService.js';
import ContentCalendarService from './calendar/ContentCalendarService.js';
import CollaborationMarketplace from './marketplace/CollaborationMarketplace.js';
import BrandPartnershipService from './partnerships/BrandPartnershipService.js';

// Config and utilities
import logger from './lib/logger.js';
import config from './config/config.js';
import authRoutes from './routes/auth.js';
import socialRoutes from './routes/social.js';
import commentRoutes from './routes/comments.js';
import automationRoutes from './routes/automation.js';
import profileRoutes from './routes/profile.js';
import exposureRoutes from './routes/exposure.js';
import affiliateRoutes from './routes/affiliate.js';
import videoRoutes from './routes/video.js';
import discountRoutes from './routes/discounts.js';
import analyticsRoutes from './routes/analytics.js';
import calendarRoutes from './routes/calendar.js';
import marketplaceRoutes from './routes/marketplace.js';
import partnershipRoutes from './routes/partnerships.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class RealLogProServer {
  constructor() {
    this.app = express();
    this.port = process.env.PORT || 8318;
    this.redis = null;
    this.services = {};
    
    this.initializeRedis();
    this.setupMiddleware();
    this.initializeServices();
    this.setupRoutes();
    this.setupErrorHandling();
  }

  async initializeRedis() {
    try {
      this.redis = createClient({
        host: process.env.REDIS_HOST || 'localhost',
        port: process.env.REDIS_PORT || 6379,
        password: process.env.REDIS_PASSWORD || undefined
      });

      await this.redis.connect();
      logger.info('Connected to Redis');
    } catch (error) {
      logger.error('Redis connection failed:', error);
    }
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

    // Rate limiting
    const limiter = rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 1000, // limit each IP to 1000 requests per windowMs
      message: 'Too many requests from this IP, please try again later.',
      standardHeaders: true,
      legacyHeaders: false
    });

    const speedLimiter = slowDown({
      windowMs: 15 * 60 * 1000, // 15 minutes
      delayAfter: 100, // allow 100 requests per 15 minutes without delay
      delayMs: () => 500 // add 500ms delay per request after delayAfter
    });

    this.app.use(limiter);
    this.app.use(speedLimiter);

    // CORS configuration
    this.app.use(cors({
      origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization']
    }));

    // Session configuration
    if (this.redis) {
      this.app.use(session({
        store: new RedisStore({ client: this.redis }),
        secret: process.env.SESSION_SECRET || 'reallog-pro-secret',
        resave: false,
        saveUninitialized: false,
        cookie: {
          secure: process.env.NODE_ENV === 'production',
          httpOnly: true,
          maxAge: 24 * 60 * 60 * 1000 // 24 hours
        }
      }));
    }

    // Body parsing
    this.app.use(express.json({ limit: '50mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '50mb' }));

    // Compression and logging
    this.app.use(compression());
    this.app.use(morgan('combined', { stream: logger.stream }));

    // Static files
    this.app.use('/uploads', express.static(path.join(__dirname, '../uploads')));
    this.app.use('/public', express.static(path.join(__dirname, '../public')));
  }

  async initializeServices() {
    try {
      // Initialize all services
      this.services.socialMedia = new SocialMediaService(this.redis);
      this.services.commentManagement = new CommentManagementService(this.redis);
      this.services.automation = new AutomationService(this.redis);
      this.services.profileCuration = new ProfileCurationService(this.redis);
      this.services.exposureOptimization = new ExposureOptimizationService(this.redis);
      this.services.affiliateTracking = new AffiliateTrackingService(this.redis);
      this.services.videoHosting = new VideoHostingService(this.redis);
      this.services.discountCode = new DiscountCodeService(this.redis);
      this.services.analytics = new AnalyticsService(this.redis);
      this.services.contentCalendar = new ContentCalendarService(this.redis);
      this.services.collaborationMarketplace = new CollaborationMarketplace(this.redis);
      this.services.brandPartnership = new BrandPartnershipService(this.redis);

      // Initialize all services
      for (const [name, service] of Object.entries(this.services)) {
        if (service.initialize) {
          await service.initialize();
          logger.info(`${name} service initialized`);
        }
      }

      logger.info('All services initialized successfully');
    } catch (error) {
      logger.error('Service initialization failed:', error);
      throw error;
    }
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        version: process.env.npm_package_version || '1.0.0',
        services: Object.keys(this.services).reduce((acc, key) => {
          acc[key] = 'active';
          return acc;
        }, {})
      });
    });

    // API routes
    this.app.use('/api/auth', authRoutes);
    this.app.use('/api/social', socialRoutes(this.services.socialMedia));
    this.app.use('/api/comments', commentRoutes(this.services.commentManagement));
    this.app.use('/api/automation', automationRoutes(this.services.automation));
    this.app.use('/api/profile', profileRoutes(this.services.profileCuration));
    this.app.use('/api/exposure', exposureRoutes(this.services.exposureOptimization));
    this.app.use('/api/affiliate', affiliateRoutes(this.services.affiliateTracking));
    this.app.use('/api/video', videoRoutes(this.services.videoHosting));
    this.app.use('/api/discounts', discountRoutes(this.services.discountCode));
    this.app.use('/api/analytics', analyticsRoutes(this.services.analytics));
    this.app.use('/api/calendar', calendarRoutes(this.services.contentCalendar));
    this.app.use('/api/marketplace', marketplaceRoutes(this.services.collaborationMarketplace));
    this.app.use('/api/partnerships', partnershipRoutes(this.services.brandPartnership));

    // WebSocket support for real-time features
    this.setupWebSocket();

    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Endpoint not found',
        message: `Cannot ${req.method} ${req.originalUrl}`
      });
    });
  }

  setupWebSocket() {
    const server = http.createServer(this.app);
    const io = new Server(server, {
      cors: {
        origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
        methods: ['GET', 'POST']
      }
    });

    // Real-time notifications
    io.on('connection', (socket) => {
      logger.info(`Client connected: ${socket.id}`);

      socket.on('join_room', (room) => {
        socket.join(room);
        logger.info(`Client ${socket.id} joined room: ${room}`);
      });

      socket.on('leave_room', (room) => {
        socket.leave(room);
        logger.info(`Client ${socket.id} left room: ${room}`);
      });

      socket.on('disconnect', () => {
        logger.info(`Client disconnected: ${socket.id}`);
      });
    });

    // Attach io to services for real-time updates
    Object.values(this.services).forEach(service => {
      if (service.setSocketIO) {
        service.setSocketIO(io);
      }
    });

    this.io = io;
    this.server = server;
  }

  setupErrorHandling() {
    // Global error handler
    this.app.use((error, req, res, next) => {
      logger.error('Unhandled error:', error);
      
      res.status(error.status || 500).json({
        error: process.env.NODE_ENV === 'production' ? 'Internal Server Error' : error.message,
        ...(process.env.NODE_ENV !== 'production' && { stack: error.stack })
      });
    });

    // Handle unhandled promise rejections
    process.on('unhandledRejection', (reason, promise) => {
      logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
    });

    // Handle uncaught exceptions
    process.on('uncaughtException', (error) => {
      logger.error('Uncaught Exception:', error);
      process.exit(1);
    });

    // Graceful shutdown
    process.on('SIGTERM', () => this.gracefulShutdown());
    process.on('SIGINT', () => this.gracefulShutdown());
  }

  async gracefulShutdown() {
    logger.info('Starting graceful shutdown...');

    // Close server
    if (this.server) {
      this.server.close(() => {
        logger.info('HTTP server closed');
      });
    }

    // Close Redis connection
    if (this.redis) {
      await this.redis.quit();
      logger.info('Redis connection closed');
    }

    // Shutdown services
    for (const [name, service] of Object.entries(this.services)) {
      if (service.shutdown) {
        await service.shutdown();
        logger.info(`${name} service shut down`);
      }
    }

    logger.info('Graceful shutdown completed');
    process.exit(0);
  }

  start() {
    const server = this.server || this.app;
    server.listen(this.port, () => {
      logger.info(`RealLog Pro Server running on port ${this.port}`);
      logger.info('Available endpoints:');
      logger.info('  GET  /health - Health check');
      logger.info('  POST /api/auth/* - Authentication');
      logger.info('  *    /api/social/* - Social media management');
      logger.info('  *    /api/comments/* - Comment management');
      logger.info('  *    /api/automation/* - Response automation');
      logger.info('  *    /api/profile/* - Profile curation');
      logger.info('  *    /api/exposure/* - Exposure optimization');
      logger.info('  *    /api/affiliate/* - Affiliate tracking');
      logger.info('  *    /api/video/* - Video hosting');
      logger.info('  *    /api/discounts/* - Discount codes');
      logger.info('  *    /api/analytics/* - Analytics dashboard');
      logger.info('  *    /api/calendar/* - Content calendar');
      logger.info('  *    /api/marketplace/* - Collaboration marketplace');
      logger.info('  *    /api/partnerships/* - Brand partnerships');
    });

    return server;
  }
}

// Start server if this file is run directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const server = new RealLogProServer();
  server.start();
}

export default RealLogProServer;