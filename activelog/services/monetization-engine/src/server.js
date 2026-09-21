const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
require('dotenv').config();

const logger = require('./utils/logger');
const database = require('./config/database');
const redis = require('./config/redis');

// Import routes
const stripeRoutes = require('./routes/stripe');
const subscriptionRoutes = require('./routes/subscriptions');
const billingRoutes = require('./routes/billing');
const affiliateRoutes = require('./routes/affiliate');
const adsenseRoutes = require('./routes/adsense');
const marketplaceRoutes = require('./routes/marketplace');
const creditsRoutes = require('./routes/credits');
const licenseRoutes = require('./routes/licenses');
const analyticsRoutes = require('./routes/analytics');
const invoiceRoutes = require('./routes/invoices');
const taxRoutes = require('./routes/tax');
const refundRoutes = require('./routes/refunds');
const reportRoutes = require('./routes/reports');

// Import middleware
const { authMiddleware } = require('./middleware/auth');
const { errorHandler } = require('./middleware/errorHandler');

const app = express();
const PORT = process.env.PORT || 8300;

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https:"],
      scriptSrc: ["'self'", "https://js.stripe.com", "https://pagead2.googlesyndication.com"],
      frameSrc: ["https://js.stripe.com", "https://googleads.g.doubleclick.net"],
      connectSrc: ["'self'", "https://api.stripe.com"]
    }
  }
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000, // 15 minutes
  max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 100,
  message: {
    error: 'Too many requests from this IP, please try again later.'
  },
  standardHeaders: true,
  legacyHeaders: false,
});

app.use(limiter);
app.use(cors());
app.use(compression());
app.use(morgan('combined', { stream: { write: message => logger.info(message.trim()) } }));

// Body parsing middleware
app.use('/webhooks/stripe', express.raw({ type: 'application/json' })); // Raw body for Stripe webhooks
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Health check endpoint
app.get('/health', async (req, res) => {
  let databaseStatus = 'disconnected';
  let redisStatus = 'disconnected';
  
  // Check database connection
  try {
    await database.raw('SELECT 1');
    databaseStatus = 'connected';
  } catch (dbErr) {
    logger.warn('Database health check failed:', dbErr.message);
  }
  
  // Check Redis connection
  try {
    await redis.ping();
    redisStatus = 'connected';
  } catch (redisErr) {
    logger.warn('Redis health check failed:', redisErr.message);
  }
  
  const isHealthy = databaseStatus === 'connected' || process.env.NODE_ENV === 'development';
  
  res.status(isHealthy ? 200 : 503).json({
    status: isHealthy ? 'healthy' : 'unhealthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    version: process.env.npm_package_version || '1.0.0',
    services: {
      database: databaseStatus,
      redis: redisStatus
    },
    mode: process.env.NODE_ENV || 'development'
  });
});

// API Routes
app.use('/api/stripe', stripeRoutes);
app.use('/api/subscriptions', authMiddleware, subscriptionRoutes);
app.use('/api/billing', authMiddleware, billingRoutes);
app.use('/api/affiliate', affiliateRoutes);
app.use('/api/adsense', authMiddleware, adsenseRoutes);
app.use('/api/marketplace', authMiddleware, marketplaceRoutes);
app.use('/api/credits', authMiddleware, creditsRoutes);
app.use('/api/licenses', authMiddleware, licenseRoutes);
app.use('/api/analytics', authMiddleware, analyticsRoutes);
app.use('/api/invoices', authMiddleware, invoiceRoutes);
app.use('/api/tax', authMiddleware, taxRoutes);
app.use('/api/refunds', authMiddleware, refundRoutes);
app.use('/api/reports', authMiddleware, reportRoutes);

// Static files for analytics dashboard
app.use('/dashboard', express.static('public/dashboard'));

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Route not found',
    path: req.originalUrl,
    method: req.method
  });
});

// Error handling middleware
app.use(errorHandler);

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully');
  
  try {
    await database.destroy();
    try {
      await redis.disconnect();
    } catch (redisErr) {
      logger.warn('Redis disconnect error:', redisErr.message);
    }
    logger.info('Database and Redis connections closed');
  } catch (error) {
    logger.error('Error during shutdown:', error);
  }
  
  process.exit(0);
});

process.on('SIGINT', async () => {
  logger.info('SIGINT received, shutting down gracefully');
  
  try {
    await database.destroy();
    try {
      await redis.disconnect();
    } catch (redisErr) {
      logger.warn('Redis disconnect error:', redisErr.message);
    }
    logger.info('Database and Redis connections closed');
  } catch (error) {
    logger.error('Error during shutdown:', error);
  }
  
  process.exit(0);
});

// Start server
app.listen(PORT, () => {
  logger.info(`Monetization Engine server running on port ${PORT}`);
  logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
  
  // Initialize background jobs
  require('./jobs');
});

module.exports = app;