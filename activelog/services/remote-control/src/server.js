const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const compression = require('compression');

// Import all the systems we've built
const PermissionSystem = require('./auth/permissionSystem');
const AdaptiveStreaming = require('./streaming/adaptiveStreaming');
const BackgroundCapture = require('./capture/backgroundCapture');
const MobileControl = require('./mobile/mobileControl');
const VoiceControl = require('./voice/voiceControl');
const ParentalMonitoring = require('./monitoring/parentalMonitoring');
const ProductivityTracking = require('./monitoring/productivityTracking');
const FindMyDevice = require('./device-discovery/findMyDevice');
const TeamTools = require('./collaboration/teamTools');
const PermissionWarningSystem = require('./security/permissionWarningSystem');
const AuditTrail = require('./security/auditTrail');

// Utilities
const logger = require('./core/logger');

class RemoteControlServer {
  constructor(options = {}) {
    this.options = {
      port: options.port || process.env.PORT || 8370,
      host: options.host || '0.0.0.0',
      
      // Demo mode for headless environments
      demoMode: options.demoMode || process.env.DEMO_MODE === 'true',
      
      // Security settings
      enableSecurity: options.enableSecurity !== false,
      corsOrigins: options.corsOrigins || ['http://localhost:3000'],
      rateLimitWindow: options.rateLimitWindow || 15 * 60 * 1000, // 15 minutes
      rateLimitMax: options.rateLimitMax || 100,
      
      // Feature flags
      enabledFeatures: options.enabledFeatures || [
        'permissions',
        'streaming',
        'capture',
        'mobile',
        'voice',
        'parental',
        'productivity',
        'findDevice',
        'collaboration',
        'warnings',
        'audit'
      ],
      
      ...options
    };

    this.app = express();
    this.server = http.createServer(this.app);
    this.io = socketIo(this.server, {
      cors: {
        origin: this.options.corsOrigins,
        methods: ['GET', 'POST'],
        credentials: true
      }
    });

    // Initialize all systems
    this.systems = {};
    
    // Connection management
    this.connectedClients = new Map();
    this.activeStreams = new Map();
    
    // System state
    this.isRunning = false;
    this.startTime = null;
    
    // Metrics
    this.metrics = {
      requestsHandled: 0,
      connectionsTotal: 0,
      activeConnections: 0,
      systemErrors: 0,
      uptime: 0
    };
  }

  async initialize() {
    logger.info('Initializing Remote Control Server...');
    
    try {
      // Setup middleware
      this.setupMiddleware();
      
      // Initialize systems based on feature flags
      await this.initializeSystems();
      
      // Setup routes
      this.setupRoutes();
      
      // Setup WebSocket handlers
      this.setupSocketHandlers();
      
      logger.info(`Remote Control Server initialized successfully`);
      logger.info(`Demo Mode: ${this.options.demoMode ? 'ENABLED' : 'DISABLED'}`);
      logger.info(`Enabled Features: ${this.options.enabledFeatures.join(', ')}`);
    } catch (error) {
      logger.error('Failed to initialize Remote Control Server:', error);
      throw error;
    }
  }

  setupMiddleware() {
    // Security
    if (this.options.enableSecurity) {
      this.app.use(helmet());
      this.app.use(cors({
        origin: this.options.corsOrigins,
        credentials: true
      }));
      
      // Rate limiting
      const limiter = rateLimit({
        windowMs: this.options.rateLimitWindow,
        max: this.options.rateLimitMax,
        message: 'Too many requests from this IP'
      });
      this.app.use('/api/', limiter);
    }

    // General middleware
    this.app.use(compression());
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true }));

    // Request logging and metrics
    this.app.use((req, res, next) => {
      this.metrics.requestsHandled++;
      
      // Audit API calls if audit system is enabled
      if (this.systems.auditTrail) {
        this.systems.auditTrail.auditEvent({
          category: 'api_calls',
          eventType: 'api_request',
          userId: req.user?.id || 'anonymous',
          action: `${req.method} ${req.path}`,
          result: 'pending',
          description: `API request: ${req.method} ${req.path}`,
          targetResource: req.path,
          ipAddress: req.ip,
          userAgent: req.get('User-Agent')
        });
      }
      
      next();
    });
  }

  async initializeSystems() {
    const features = this.options.enabledFeatures;

    // Initialize Permission System (required for security)
    if (features.includes('permissions')) {
      this.systems.permissionSystem = new PermissionSystem({
        demoMode: this.options.demoMode
      });
      await this.systems.permissionSystem.initialize();
      logger.info('Permission System initialized ✓');
    }

    // Initialize Audit Trail (should be early for logging)
    if (features.includes('audit')) {
      this.systems.auditTrail = new AuditTrail({
        storageDir: './data/audit-trail'
      });
      await this.systems.auditTrail.initialize();
      logger.info('Audit Trail initialized ✓');
    }

    // Initialize Warning System
    if (features.includes('warnings')) {
      this.systems.warningSystem = new PermissionWarningSystem();
      await this.systems.warningSystem.initialize();
      logger.info('Warning System initialized ✓');
    }

    // Initialize Streaming System
    if (features.includes('streaming')) {
      this.systems.adaptiveStreaming = new AdaptiveStreaming({
        gamingMode: true,
        motionDetection: true
      });
      await this.systems.adaptiveStreaming.initialize();
      logger.info('Adaptive Streaming initialized ✓');
    }

    // Initialize Background Capture
    if (features.includes('capture')) {
      this.systems.backgroundCapture = new BackgroundCapture({
        demoMode: this.options.demoMode,
        multiMonitorSupport: true
      });
      await this.systems.backgroundCapture.initialize();
      logger.info('Background Capture initialized ✓');
    }

    // Initialize Mobile Control
    if (features.includes('mobile')) {
      this.systems.mobileControl = new MobileControl();
      await this.systems.mobileControl.initialize();
      logger.info('Mobile Control initialized ✓');
    }

    // Initialize Voice Control
    if (features.includes('voice')) {
      this.systems.voiceControl = new VoiceControl();
      await this.systems.voiceControl.initialize();
      logger.info('Voice Control initialized ✓');
    }

    // Initialize Parental Monitoring
    if (features.includes('parental')) {
      this.systems.parentalMonitoring = new ParentalMonitoring({
        replayDuration: 30000 // 30 seconds
      });
      await this.systems.parentalMonitoring.initialize();
      logger.info('Parental Monitoring initialized ✓');
    }

    // Initialize Productivity Tracking
    if (features.includes('productivity')) {
      this.systems.productivityTracking = new ProductivityTracking();
      await this.systems.productivityTracking.initialize();
      logger.info('Productivity Tracking initialized ✓');
    }

    // Initialize Find My Device
    if (features.includes('findDevice')) {
      this.systems.findMyDevice = new FindMyDevice();
      await this.systems.findMyDevice.initialize();
      logger.info('Find My Device initialized ✓');
    }

    // Initialize Team Collaboration Tools
    if (features.includes('collaboration')) {
      this.systems.teamTools = new TeamTools();
      await this.systems.teamTools.initialize();
      logger.info('Team Tools initialized ✓');
    }

    // Setup system integrations
    this.setupSystemIntegrations();
  }

  setupSystemIntegrations() {
    // Integrate warning system with permission system
    if (this.systems.permissionSystem && this.systems.warningSystem) {
      this.systems.permissionSystem.on('authentication-failed', (event) => {
        this.systems.warningSystem.checkPermissionAccess(
          event.userId, 'authentication', 'login', 
          { success: false, ip: event.ip }
        );
      });
    }

    // Integrate audit trail with all systems
    if (this.systems.auditTrail) {
      // Permission system events
      if (this.systems.permissionSystem) {
        this.systems.permissionSystem.on('user-authenticated', (event) => {
          this.systems.auditTrail.auditAuthentication(
            event.user, 'login', 'success', { sessionId: event.session }
          );
        });
      }

      // Team collaboration events
      if (this.systems.teamTools) {
        this.systems.teamTools.on('session-created', (session) => {
          this.systems.auditTrail.auditEvent({
            category: 'collaboration',
            eventType: 'session_created',
            userId: session.hostUserId,
            action: 'create_session',
            result: 'success',
            description: `Team session created: ${session.title}`,
            targetResource: 'collaboration_session',
            targetId: session.id
          });
        });
      }
    }

    logger.info('System integrations configured ✓');
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      const health = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: Date.now() - this.startTime,
        version: '1.0.0',
        demoMode: this.options.demoMode,
        systems: {}
      };

      // Check system health
      Object.keys(this.systems).forEach(systemName => {
        health.systems[systemName] = {
          status: 'operational',
          metrics: this.systems[systemName].getMetrics?.() || {}
        };
      });

      res.json(health);
    });

    // System metrics
    this.app.get('/api/metrics', this.requireAuth.bind(this), (req, res) => {
      const metrics = {
        server: this.metrics,
        systems: {}
      };

      Object.keys(this.systems).forEach(systemName => {
        if (this.systems[systemName].getMetrics) {
          metrics.systems[systemName] = this.systems[systemName].getMetrics();
        }
      });

      res.json(metrics);
    });

    // Authentication routes
    if (this.systems.permissionSystem) {
      this.app.post('/api/auth/login', async (req, res) => {
        try {
          const { username, password } = req.body;
          const clientInfo = {
            ip: req.ip,
            userAgent: req.get('User-Agent')
          };

          const result = await this.systems.permissionSystem.authenticate(
            username, password, clientInfo
          );

          res.json(result);
        } catch (error) {
          this.metrics.systemErrors++;
          res.status(500).json({ error: error.message });
        }
      });

      this.app.post('/api/auth/logout', this.requireAuth.bind(this), async (req, res) => {
        try {
          await this.systems.permissionSystem.revokeSession(req.sessionId);
          res.json({ success: true });
        } catch (error) {
          res.status(500).json({ error: error.message });
        }
      });
    }

    // Streaming routes
    if (this.systems.adaptiveStreaming) {
      this.app.get('/api/stream/clients', this.requireAuth.bind(this), (req, res) => {
        const stats = this.systems.adaptiveStreaming.getStreamingStats();
        res.json(stats);
      });

      this.app.post('/api/stream/quality/:clientId', this.requireAuth.bind(this), async (req, res) => {
        try {
          const { clientId } = req.params;
          const { quality } = req.body;
          
          const result = this.systems.adaptiveStreaming.setClientQuality(clientId, quality);
          res.json({ success: result });
        } catch (error) {
          res.status(500).json({ error: error.message });
        }
      });
    }

    // Mobile control routes
    if (this.systems.mobileControl) {
      this.app.get('/api/mobile/devices', this.requireAuth.bind(this), (req, res) => {
        const devices = this.systems.mobileControl.getConnectedDevices();
        res.json(devices);
      });

      this.app.post('/api/mobile/input', this.requireAuth.bind(this), async (req, res) => {
        try {
          const { deviceId, inputData } = req.body;
          const result = await this.systems.mobileControl.processInput(deviceId, inputData);
          res.json(result);
        } catch (error) {
          res.status(500).json({ error: error.message });
        }
      });
    }

    // Voice control routes
    if (this.systems.voiceControl) {
      this.app.get('/api/voice/commands', this.requireAuth.bind(this), (req, res) => {
        const commands = this.systems.voiceControl.getCommands();
        res.json(commands);
      });

      this.app.post('/api/voice/activate', this.requireAuth.bind(this), async (req, res) => {
        try {
          await this.systems.voiceControl.activate();
          res.json({ success: true, status: 'activated' });
        } catch (error) {
          res.status(500).json({ error: error.message });
        }
      });
    }

    // Team collaboration routes
    if (this.systems.teamTools) {
      this.app.get('/api/team/sessions', this.requireAuth.bind(this), (req, res) => {
        const sessions = this.systems.teamTools.getActiveSessions(req.userId);
        res.json(sessions);
      });

      this.app.post('/api/team/sessions', this.requireAuth.bind(this), async (req, res) => {
        try {
          const session = await this.systems.teamTools.createSession(req.userId, req.body);
          res.json(session);
        } catch (error) {
          res.status(500).json({ error: error.message });
        }
      });
    }

    // Find My Device routes
    if (this.systems.findMyDevice) {
      this.app.get('/api/devices', this.requireAuth.bind(this), (req, res) => {
        const devices = this.systems.findMyDevice.getUserDevices(req.userId);
        res.json(devices);
      });

      this.app.post('/api/devices', this.requireAuth.bind(this), async (req, res) => {
        try {
          const device = await this.systems.findMyDevice.registerDevice(req.userId, req.body);
          res.json(device);
        } catch (error) {
          res.status(500).json({ error: error.message });
        }
      });
    }

    // Audit routes (admin only)
    if (this.systems.auditTrail) {
      this.app.get('/api/audit/summary', this.requireAdminAuth.bind(this), async (req, res) => {
        try {
          const timeRange = req.query.range || '24h';
          const summary = await this.systems.auditTrail.getAuditSummary(timeRange);
          res.json(summary);
        } catch (error) {
          res.status(500).json({ error: error.message });
        }
      });

      this.app.post('/api/audit/query', this.requireAdminAuth.bind(this), async (req, res) => {
        try {
          const query = { ...req.body, requestedBy: req.userId };
          const results = await this.systems.auditTrail.queryAuditTrail(query);
          res.json(results);
        } catch (error) {
          res.status(500).json({ error: error.message });
        }
      });
    }

    // Demo mode routes
    if (this.options.demoMode) {
      this.app.get('/api/demo/status', (req, res) => {
        res.json({
          demoMode: true,
          message: 'Remote Control Service running in demo mode',
          features: this.options.enabledFeatures,
          connectedClients: this.connectedClients.size
        });
      });
    }

    // Error handling
    this.app.use((error, req, res, next) => {
      this.metrics.systemErrors++;
      logger.error('API Error:', error);
      
      res.status(error.status || 500).json({
        error: error.message || 'Internal server error',
        timestamp: new Date().toISOString()
      });
    });

    // 404 handler
    this.app.use((req, res) => {
      res.status(404).json({
        error: 'Endpoint not found',
        path: req.path,
        method: req.method
      });
    });
  }

  async requireAuth(req, res, next) {
    try {
      const token = req.headers.authorization?.replace('Bearer ', '');
      
      if (!token) {
        return res.status(401).json({ error: 'Authentication required' });
      }

      if (this.systems.permissionSystem) {
        const validation = await this.systems.permissionSystem.validateSession(token);
        if (!validation.valid) {
          return res.status(401).json({ error: validation.error });
        }

        req.user = validation.session;
        req.userId = validation.session.userId;
        req.sessionId = validation.session.id;
        req.permissions = validation.permissions;
      }

      next();
    } catch (error) {
      res.status(401).json({ error: 'Authentication failed' });
    }
  }

  async requireAdminAuth(req, res, next) {
    await this.requireAuth(req, res, () => {
      if (this.systems.permissionSystem) {
        const hasAdminPermission = this.systems.permissionSystem.hasPermission(
          req.permissions, 
          this.systems.permissionSystem.PERMISSIONS.ADMIN
        );
        
        if (!hasAdminPermission) {
          return res.status(403).json({ error: 'Admin privileges required' });
        }
      }
      next();
    });
  }

  setupSocketHandlers() {
    this.io.on('connection', (socket) => {
      this.metrics.connectionsTotal++;
      this.metrics.activeConnections++;

      logger.info(`Client connected: ${socket.id}`, {
        totalConnections: this.connectedClients.size + 1
      });

      // Store client info
      this.connectedClients.set(socket.id, {
        socketId: socket.id,
        connectedAt: Date.now(),
        ip: socket.request.connection.remoteAddress,
        userAgent: socket.request.headers['user-agent']
      });

      // Authentication for socket connections
      socket.on('authenticate', async (data) => {
        try {
          if (this.systems.permissionSystem && data.token) {
            const validation = await this.systems.permissionSystem.validateSession(data.token);
            if (validation.valid) {
              socket.userId = validation.session.userId;
              socket.authenticated = true;
              socket.emit('authenticated', { success: true });
              
              const client = this.connectedClients.get(socket.id);
              client.userId = socket.userId;
              client.authenticated = true;
            } else {
              socket.emit('authentication-failed', { error: validation.error });
            }
          }
        } catch (error) {
          socket.emit('authentication-failed', { error: error.message });
        }
      });

      // Screen sharing
      socket.on('start-stream', async (data) => {
        if (!socket.authenticated) {
          return socket.emit('error', { message: 'Authentication required' });
        }

        try {
          if (this.systems.adaptiveStreaming) {
            const streamConfig = await this.systems.adaptiveStreaming.addClient(
              socket.id, 
              { ...data, userId: socket.userId }
            );
            
            this.activeStreams.set(socket.id, streamConfig);
            socket.emit('stream-started', streamConfig);
          }
        } catch (error) {
          socket.emit('stream-error', { error: error.message });
        }
      });

      // Mobile input
      socket.on('mobile-input', async (data) => {
        if (!socket.authenticated) {
          return socket.emit('error', { message: 'Authentication required' });
        }

        try {
          if (this.systems.mobileControl) {
            const result = await this.systems.mobileControl.processInput(socket.id, data);
            socket.emit('input-processed', result);
          }
        } catch (error) {
          socket.emit('input-error', { error: error.message });
        }
      });

      // Team collaboration
      socket.on('join-session', async (data) => {
        if (!socket.authenticated) {
          return socket.emit('error', { message: 'Authentication required' });
        }

        try {
          if (this.systems.teamTools) {
            const result = await this.systems.teamTools.joinSession(
              socket.userId, 
              data.sessionId, 
              { ...data.userInfo, socketId: socket.id }
            );
            
            socket.join(`session_${data.sessionId}`);
            socket.emit('session-joined', result);
            socket.to(`session_${data.sessionId}`).emit('participant-joined', {
              userId: socket.userId,
              displayName: data.userInfo?.displayName
            });
          }
        } catch (error) {
          socket.emit('session-error', { error: error.message });
        }
      });

      // Voice commands
      socket.on('voice-command', async (data) => {
        if (!socket.authenticated) {
          return socket.emit('error', { message: 'Authentication required' });
        }

        try {
          if (this.systems.voiceControl) {
            // Process simulated voice command
            const result = await this.systems.voiceControl.processRecognitionResult({
              transcript: data.transcript,
              confidence: data.confidence || 0.8,
              isFinal: true
            });
            
            socket.emit('voice-command-processed', result);
          }
        } catch (error) {
          socket.emit('voice-error', { error: error.message });
        }
      });

      // Disconnect handling
      socket.on('disconnect', () => {
        this.metrics.activeConnections--;
        
        // Cleanup streaming
        if (this.activeStreams.has(socket.id)) {
          if (this.systems.adaptiveStreaming) {
            this.systems.adaptiveStreaming.removeClient(socket.id);
          }
          this.activeStreams.delete(socket.id);
        }

        // Cleanup mobile device
        if (this.systems.mobileControl) {
          this.systems.mobileControl.disconnectMobileDevice(socket.id);
        }

        // Cleanup team sessions
        if (this.systems.teamTools && socket.userId) {
          // Leave any active sessions
          const userSessions = this.systems.teamTools.getUserSessions(socket.userId);
          userSessions.forEach(session => {
            this.systems.teamTools.leaveSession(socket.userId, session.id);
          });
        }

        this.connectedClients.delete(socket.id);

        logger.info(`Client disconnected: ${socket.id}`, {
          remainingConnections: this.connectedClients.size
        });
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

          logger.info(`🚀 Remote Control Server started successfully!`);
          logger.info(`📡 Server listening on ${this.options.host}:${this.options.port}`);
          logger.info(`🌐 Health check: http://${this.options.host}:${this.options.port}/health`);
          
          if (this.options.demoMode) {
            logger.info(`🎭 Demo status: http://${this.options.host}:${this.options.port}/api/demo/status`);
          }

          // Start metrics reporting
          this.startMetricsReporting();

          resolve();
        });
      });
    } catch (error) {
      logger.error('Failed to start Remote Control Server:', error);
      throw error;
    }
  }

  startMetricsReporting() {
    setInterval(() => {
      this.metrics.uptime = Date.now() - this.startTime;
      
      logger.info('Server Metrics', {
        uptime: Math.round(this.metrics.uptime / 1000) + 's',
        requestsHandled: this.metrics.requestsHandled,
        activeConnections: this.metrics.activeConnections,
        connectedClients: this.connectedClients.size,
        systemErrors: this.metrics.systemErrors
      });
    }, 60000); // Every minute
  }

  async stop() {
    if (!this.isRunning) return;

    logger.info('Shutting down Remote Control Server...');

    // Cleanup systems
    for (const [systemName, system] of Object.entries(this.systems)) {
      try {
        if (system.cleanup) {
          await system.cleanup();
          logger.info(`${systemName} cleaned up ✓`);
        }
      } catch (error) {
        logger.error(`Error cleaning up ${systemName}:`, error);
      }
    }

    // Close server
    return new Promise((resolve) => {
      this.server.close(() => {
        this.isRunning = false;
        logger.info('Remote Control Server stopped ✓');
        resolve();
      });
    });
  }
}

// Create and start server if running directly
if (require.main === module) {
  const server = new RemoteControlServer({
    demoMode: process.env.DEMO_MODE === 'true',
    port: process.env.PORT || 8370
  });

  // Graceful shutdown
  process.on('SIGTERM', async () => {
    logger.info('Received SIGTERM, shutting down gracefully...');
    await server.stop();
    process.exit(0);
  });

  process.on('SIGINT', async () => {
    logger.info('Received SIGINT, shutting down gracefully...');
    await server.stop();
    process.exit(0);
  });

  // Start the server
  server.start().catch(error => {
    logger.error('Failed to start server:', error);
    process.exit(1);
  });
}

module.exports = RemoteControlServer;