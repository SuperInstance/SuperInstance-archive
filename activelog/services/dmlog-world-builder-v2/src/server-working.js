const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
require('dotenv').config();

// Import services (with fallbacks)
const logger = require('./utils/logger');

// Import routes
const worldRoutes = require('./routes/world');
const storyRoutes = require('./routes/story');
const characterRoutes = require('./routes/character');
const mapRoutes = require('./routes/map');
const aiRoutes = require('./routes/ai');
const collaborationRoutes = require('./routes/collaboration');

// Create Express app and HTTP server
const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: process.env.FRONTEND_URL || "http://localhost:3000",
    methods: ["GET", "POST"],
    credentials: true
  }
});

const PORT = process.env.PORT || 8407;

// Security middleware
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

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000, // limit each IP to 1000 requests per windowMs
  message: 'Too many requests from this IP, please try again later.',
});
app.use('/api/', limiter);

// AI-specific rate limiting
const aiLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 20, // limit each IP to 20 AI requests per minute
  message: 'AI request limit exceeded, please wait before making more requests.',
});
app.use('/api/ai/', aiLimiter);

// Middleware
app.use(cors({
  origin: process.env.FRONTEND_URL || "http://localhost:3000",
  credentials: true
}));
app.use(compression());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'dmlog-world-builder-v2',
    version: '2.0.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    connections: io.engine.clientsCount || 0
  });
});

// API Routes
app.use('/api/world', worldRoutes);
app.use('/api/story', storyRoutes);
app.use('/api/character', characterRoutes);
app.use('/api/map', mapRoutes);
app.use('/api/ai', aiRoutes);
app.use('/api/collaboration', collaborationRoutes);

// Socket.IO connection handling (basic implementation)
io.on('connection', (socket) => {
  logger.info(`Client connected: ${socket.id}`);
  
  socket.on('join-world', (worldId) => {
    socket.join(`world:${worldId}`);
    logger.info(`Socket ${socket.id} joined world ${worldId}`);
  });
  
  socket.on('disconnect', () => {
    logger.info(`Client disconnected: ${socket.id}`);
  });
});

// Global error handling
app.use((err, req, res, next) => {
  logger.error('Unhandled error:', err);
  
  if (err.code === 'LIMIT_FILE_SIZE') {
    return res.status(400).json({
      error: 'File size too large',
      maxSize: '10MB'
    });
  }
  
  res.status(err.status || 500).json({
    error: err.message || 'Internal server error',
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Route not found',
    path: req.originalUrl
  });
});

// Graceful shutdown
process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

function gracefulShutdown(signal) {
  logger.info(`Received ${signal}. Starting graceful shutdown...`);
  
  server.close(() => {
    logger.info('HTTP server closed');
    process.exit(0);
  });
  
  // Force close after 30 seconds
  setTimeout(() => {
    logger.error('Could not close connections in time, forcefully shutting down');
    process.exit(1);
  }, 30000);
}

// Start server
async function startServer() {
  try {
    server.listen(PORT, () => {
      console.log(`🌍 DMLog World Builder v2 running on port ${PORT}`);
      console.log(`📊 Health check: http://localhost:${PORT}/health`);
      logger.info(`🌍 DMLog World Builder v2 running on port ${PORT}`);
      logger.info(`📊 Health check: http://localhost:${PORT}/health`);
      logger.info(`⚡ Real-time collaboration: Active`);
    });

    // Initialize database and other services in background
    setTimeout(async () => {
      try {
        // Try to connect to MongoDB (optional)
        try {
          const { connectDatabase } = require('./db/connection');
          await connectDatabase();
          logger.info('Database connected successfully');
        } catch (error) {
          logger.warn('Database connection failed, continuing without database:', error.message);
        }

        // Initialize Redis (optional)
        try {
          const { initializeRedis } = require('./utils/redis');
          await initializeRedis();
          logger.info('Redis initialized successfully');
        } catch (error) {
          logger.warn('Redis initialization failed, continuing without cache:', error.message);
        }

        logger.info('🤖 AI Assistant: Ready (requires OPENAI_API_KEY)');
        
      } catch (error) {
        logger.error('Background service initialization failed:', error);
      }
    }, 2000);
    
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Only start if this file is run directly
if (require.main === module) {
  startServer();
}

module.exports = { app, server, io };