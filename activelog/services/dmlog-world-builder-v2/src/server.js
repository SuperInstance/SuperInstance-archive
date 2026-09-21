const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const mongoose = require('mongoose');
require('dotenv').config();

// Import services
const logger = require('./utils/logger');
const { connectDatabase } = require('./db/connection');
const { initializeRedis } = require('./utils/redis');
const { initializeQueues } = require('./utils/queues');

// Import routes
const worldRoutes = require('./routes/world');
const storyRoutes = require('./routes/story');
const characterRoutes = require('./routes/character');
const mapRoutes = require('./routes/map');
const aiRoutes = require('./routes/ai');
const collaborationRoutes = require('./routes/collaboration');

// Import socket handlers
const { handleCollaboration } = require('./services/collaboration');
const { handleVersionControl } = require('./services/versionControl');

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

// AI-specific rate limiting (more restrictive)
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
    connections: io.engine.clientsCount
  });
});

// API Routes
app.use('/api/world', worldRoutes);
app.use('/api/story', storyRoutes);
app.use('/api/character', characterRoutes);
app.use('/api/map', mapRoutes);
app.use('/api/ai', aiRoutes);
app.use('/api/collaboration', collaborationRoutes);

// Socket.IO connection handling
io.on('connection', (socket) => {
  logger.info(`Client connected: ${socket.id}`);
  
  // Join collaboration room
  socket.on('join-world', (worldId) => {
    socket.join(`world:${worldId}`);
    logger.info(`Socket ${socket.id} joined world ${worldId}`);
  });
  
  // Handle real-time collaboration
  handleCollaboration(socket, io);
  
  // Handle version control operations
  handleVersionControl(socket, io);
  
  // Handle auto-save operations
  socket.on('auto-save', async (data) => {
    try {
      const { worldId, type, content, userId } = data;
      
      // Broadcast to other clients in the same world
      socket.to(`world:${worldId}`).emit('content-updated', {
        type,
        content,
        userId,
        timestamp: Date.now()
      });
      
      logger.info(`Auto-save completed for world ${worldId}, type: ${type}`);
    } catch (error) {
      logger.error('Auto-save error:', error);
      socket.emit('auto-save-error', { error: error.message });
    }
  });
  
  // Handle seamless context switching
  socket.on('switch-context', (data) => {
    const { worldId, fromContext, toContext, contextData } = data;
    
    socket.to(`world:${worldId}`).emit('context-switched', {
      userId: socket.userId,
      fromContext,
      toContext,
      contextData,
      timestamp: Date.now()
    });
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

async function gracefulShutdown(signal) {
  logger.info(`Received ${signal}. Starting graceful shutdown...`);
  
  // Close server
  server.close(() => {
    logger.info('HTTP server closed');
    
    // Close database connection
    mongoose.connection.close(false, () => {
      logger.info('MongoDB connection closed');
      process.exit(0);
    });
  });
  
  // Force close after 30 seconds
  setTimeout(() => {
    logger.error('Could not close connections in time, forcefully shutting down');
    process.exit(1);
  }, 30000);
}

// Initialize and start server
async function startServer() {
  try {
    // Start server first
    server.listen(PORT, () => {
      logger.info(`🌍 DMLog World Builder v2 running on port ${PORT}`);
      logger.info(`📊 Health check: http://localhost:${PORT}/health`);
      console.log(`🌍 DMLog World Builder v2 running on port ${PORT}`);
      console.log(`📊 Health check: http://localhost:${PORT}/health`);
    });

    // Initialize services in background (non-blocking)
    setTimeout(async () => {
      try {
        // Connect to database
        await connectDatabase();
        logger.info('Database connected successfully');
        
        // Initialize Redis for caching and sessions (optional)
        try {
          await initializeRedis();
          logger.info('Redis initialized successfully');
        } catch (error) {
          logger.warn('Redis initialization failed, continuing without cache:', error.message);
        }
        
        // Initialize background job queues (optional)
        try {
          await initializeQueues();
          logger.info('Background queues initialized');
        } catch (error) {
          logger.warn('Queue initialization failed, continuing without background jobs:', error.message);
        }
        
        logger.info(`🤖 AI Assistant: Ready for world building`);
        logger.info(`⚡ Real-time collaboration: Active`);
        
      } catch (error) {
        logger.error('Service initialization failed, but server continues:', error);
      }
    }, 1000);
    
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