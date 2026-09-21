import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import dotenv from 'dotenv';
import { WebSocketServer } from 'ws';
import http from 'http';
import cron from 'node-cron';
import rateLimit from 'express-rate-limit';

import { logger } from './utils/logger.js';
import { initializeDatabase } from './database/init.js';
import { initializeRedis } from './utils/redis.js';
import { setupWebSocket } from './websocket/server.js';
import { startBackgroundJobs } from './jobs/scheduler.js';
import { initializeMetrics } from './monitoring/metrics.js';

// Route imports
import authRoutes from './routes/auth.js';
import providersRoutes from './routes/providers.js';
import jobsRoutes from './routes/jobs.js';
import pricingRoutes from './routes/pricing.js';
import billingRoutes from './routes/billing.js';
import monitoringRoutes from './routes/monitoring.js';
import userRoutes from './routes/users.js';
import adminRoutes from './routes/admin.js';
import slaRoutes from './routes/sla.js';
import reputationRoutes from './routes/reputation.js';

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.PORT || 8320;

// Create HTTP server for WebSocket
const server = http.createServer(app);
const wss = new WebSocketServer({ server });

// Rate limiting
const limiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: parseInt(process.env.API_RATE_LIMIT_PER_MINUTE) || 100,
  message: {
    error: 'Too many requests from this IP, please try again later',
    retryAfter: '1 minute'
  },
  standardHeaders: true,
  legacyHeaders: false
});

// Middleware
app.use(helmet({
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

app.use(cors({
  origin: process.env.NODE_ENV === 'production' 
    ? ['https://compute-exchange.edu'] 
    : ['http://localhost:3000', 'http://localhost:3001'],
  credentials: true
}));

app.use(limiter);
app.use(morgan('combined', { stream: { write: message => logger.info(message.trim()) } }));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Add request ID for tracking
app.use((req, res, next) => {
  req.id = Math.random().toString(36).substr(2, 9);
  res.setHeader('X-Request-ID', req.id);
  next();
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    service: 'compute-exchange',
    version: process.env.npm_package_version || '1.0.0',
    environment: process.env.NODE_ENV,
    port: PORT
  });
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/providers', providersRoutes);
app.use('/api/jobs', jobsRoutes);
app.use('/api/pricing', pricingRoutes);
app.use('/api/billing', billingRoutes);
app.use('/api/monitoring', monitoringRoutes);
app.use('/api/users', userRoutes);
app.use('/api/admin', adminRoutes);
app.use('/api/sla', slaRoutes);
app.use('/api/reputation', reputationRoutes);

// Metrics endpoint for Prometheus
app.get('/metrics', (req, res) => {
  const register = app.locals.register;
  res.set('Content-Type', register.contentType);
  res.end(register.metrics());
});

// API documentation endpoint
app.get('/api', (req, res) => {
  res.json({
    service: 'Compute Exchange',
    version: '1.0.0',
    description: 'University compute resource exchange with dynamic pricing',
    endpoints: {
      auth: '/api/auth',
      providers: '/api/providers',
      jobs: '/api/jobs',
      pricing: '/api/pricing',
      billing: '/api/billing',
      monitoring: '/api/monitoring',
      users: '/api/users',
      admin: '/api/admin',
      sla: '/api/sla',
      reputation: '/api/reputation'
    },
    websocket: '/ws',
    health: '/health',
    metrics: '/metrics'
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error('Unhandled error:', {
    error: err.message,
    stack: err.stack,
    requestId: req.id,
    path: req.path,
    method: req.method,
    ip: req.ip
  });
  
  res.status(500).json({ 
    error: 'Internal server error', 
    requestId: req.id,
    timestamp: new Date().toISOString()
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ 
    error: 'Endpoint not found',
    path: req.path,
    method: req.method,
    timestamp: new Date().toISOString()
  });
});

// Initialize services
async function initializeServices() {
  try {
    logger.info('Initializing Compute Exchange Service...');
    
    // Initialize database
    await initializeDatabase();
    logger.info('Database initialized');
    
    // Initialize Redis
    await initializeRedis();
    logger.info('Redis initialized');
    
    // Initialize metrics
    app.locals.register = initializeMetrics();
    logger.info('Metrics initialized');
    
    // Setup WebSocket
    setupWebSocket(wss);
    logger.info('WebSocket server initialized');
    
    // Start background jobs
    startBackgroundJobs();
    logger.info('Background jobs started');
    
    logger.info('All services initialized successfully');
  } catch (error) {
    logger.error('Failed to initialize services:', error);
    process.exit(1);
  }
}

// Graceful shutdown
const gracefulShutdown = (signal) => {
  logger.info(`${signal} received, shutting down gracefully`);
  
  server.close(() => {
    logger.info('HTTP server closed');
    
    // Close database connections, redis, etc.
    process.exit(0);
  });
  
  // Force close after 10 seconds
  setTimeout(() => {
    logger.error('Forced shutdown after 10 seconds');
    process.exit(1);
  }, 10000);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Start server
async function startServer() {
  await initializeServices();
  
  server.listen(PORT, () => {
    logger.info(`Compute Exchange Service running on port ${PORT}`);
    logger.info(`Environment: ${process.env.NODE_ENV}`);
    logger.info(`API documentation available at: http://localhost:${PORT}/api`);
    logger.info(`Health check available at: http://localhost:${PORT}/health`);
    logger.info(`WebSocket server ready at: ws://localhost:${PORT}/ws`);
  });
}

startServer().catch(error => {
  logger.error('Failed to start server:', error);
  process.exit(1);
});