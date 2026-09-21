const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');

// Import core systems only
const PermissionSystem = require('./auth/permissionSystem');
const logger = require('./core/logger');

class SimpleRemoteControlServer {
  constructor(options = {}) {
    this.options = {
      port: options.port || process.env.PORT || 8370,
      host: options.host || '0.0.0.0',
      demoMode: options.demoMode || process.env.DEMO_MODE === 'true'
    };

    this.app = express();
    this.server = http.createServer(this.app);
    this.io = socketIo(this.server);

    this.connectedClients = new Map();
    this.isRunning = false;
    this.startTime = null;
    
    this.metrics = {
      requestsHandled: 0,
      connectionsTotal: 0,
      activeConnections: 0
    };
  }

  async initialize() {
    logger.info('Initializing Simple Remote Control Server...');
    
    try {
      // Setup basic middleware
      this.app.use(helmet());
      this.app.use(cors());
      this.app.use(compression());
      this.app.use(express.json());

      // Initialize permission system
      this.permissionSystem = new PermissionSystem({
        demoMode: this.options.demoMode
      });
      await this.permissionSystem.initialize();

      // Setup routes
      this.setupRoutes();
      
      // Setup WebSocket handlers
      this.setupSocketHandlers();
      
      logger.info('Simple Remote Control Server initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Simple Remote Control Server:', error);
      throw error;
    }
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      const health = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: this.startTime ? Date.now() - this.startTime : 0,
        version: '1.0.0-simple',
        demoMode: this.options.demoMode,
        connectedClients: this.connectedClients.size,
        metrics: this.metrics
      };

      res.json(health);
    });

    // Demo status
    this.app.get('/api/demo/status', (req, res) => {
      res.json({
        demoMode: this.options.demoMode,
        message: 'Simple Remote Control Service running',
        connectedClients: this.connectedClients.size,
        features: ['permissions', 'websockets']
      });
    });

    // Authentication
    this.app.post('/api/auth/login', async (req, res) => {
      try {
        const { username, password } = req.body;
        const clientInfo = {
          ip: req.ip,
          userAgent: req.get('User-Agent')
        };

        const result = await this.permissionSystem.authenticate(
          username, password, clientInfo
        );

        res.json(result);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    // 404 handler
    this.app.use((req, res) => {
      res.status(404).json({
        error: 'Endpoint not found',
        path: req.path
      });
    });
  }

  setupSocketHandlers() {
    this.io.on('connection', (socket) => {
      this.metrics.connectionsTotal++;
      this.metrics.activeConnections++;

      logger.info(`Client connected: ${socket.id}`);

      this.connectedClients.set(socket.id, {
        socketId: socket.id,
        connectedAt: Date.now()
      });

      socket.on('authenticate', async (data) => {
        try {
          if (data.token) {
            const validation = await this.permissionSystem.validateSession(data.token);
            if (validation.valid) {
              socket.authenticated = true;
              socket.emit('authenticated', { success: true });
            } else {
              socket.emit('authentication-failed', { error: validation.error });
            }
          }
        } catch (error) {
          socket.emit('authentication-failed', { error: error.message });
        }
      });

      socket.on('ping', () => {
        socket.emit('pong', { timestamp: Date.now() });
      });

      socket.on('disconnect', () => {
        this.metrics.activeConnections--;
        this.connectedClients.delete(socket.id);
        logger.info(`Client disconnected: ${socket.id}`);
      });
    });
  }

  async start() {
    try {
      await this.initialize();
      
      return new Promise((resolve, reject) => {
        this.server.listen(this.options.port, this.options.host, (error) => {
          if (error) {
            reject(error);
            return;
          }

          this.isRunning = true;
          this.startTime = Date.now();

          logger.info(`🚀 Simple Remote Control Server started!`);
          logger.info(`📡 Server listening on ${this.options.host}:${this.options.port}`);
          logger.info(`🌐 Health check: http://${this.options.host}:${this.options.port}/health`);
          
          if (this.options.demoMode) {
            logger.info(`🎭 Demo status: http://${this.options.host}:${this.options.port}/api/demo/status`);
          }

          resolve();
        });
      });
    } catch (error) {
      logger.error('Failed to start Simple Remote Control Server:', error);
      throw error;
    }
  }

  async stop() {
    if (!this.isRunning) return;

    logger.info('Shutting down Simple Remote Control Server...');

    if (this.permissionSystem && this.permissionSystem.cleanup) {
      await this.permissionSystem.cleanup();
    }

    return new Promise((resolve) => {
      this.server.close(() => {
        this.isRunning = false;
        logger.info('Simple Remote Control Server stopped ✓');
        resolve();
      });
    });
  }
}

// Create and start server if running directly
if (require.main === module) {
  const server = new SimpleRemoteControlServer({
    demoMode: process.env.DEMO_MODE === 'true',
    port: process.env.PORT || 8370
  });

  // Graceful shutdown
  process.on('SIGTERM', async () => {
    await server.stop();
    process.exit(0);
  });

  process.on('SIGINT', async () => {
    await server.stop();
    process.exit(0);
  });

  // Start the server
  server.start().catch(error => {
    logger.error('Failed to start server:', error);
    process.exit(1);
  });
}

module.exports = SimpleRemoteControlServer;