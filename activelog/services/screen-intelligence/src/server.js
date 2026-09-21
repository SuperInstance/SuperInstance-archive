const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const morgan = require('morgan');
const path = require('path');

// Core modules
const logger = require('./core/logger');
const config = require('../config/config');
const FrameCapture = require('./core/frameCapture');
const AIBasedMomentDetection = require('./ai/momentDetection');
const RadarAnalysisSystem = require('./vision/radarAnalysis');
const VesselRecognition = require('./vision/vesselRecognition');
const OverlaySystem = require('./overlay/overlaySystem');
const HeatMapSystem = require('./overlay/heatmaps');
const TimeZeroIntegration = require('./integration/timezero');
const ChartExtractor = require('./integration/chartExtractor');
const MobileStreaming = require('./mobile/streaming');
const GestureControl = require('./mobile/gestureControl');
const AutomationEngine = require('./automation/automationEngine');
const HistoricalPlayback = require('./playback/playbackEngine');

class ScreenIntelligenceServer {
  constructor() {
    this.app = express();
    this.server = http.createServer(this.app);
    this.io = socketIo(this.server, {
      cors: {
        origin: ["http://localhost:3000", "http://localhost:8369"],
        methods: ["GET", "POST"]
      }
    });
    
    this.port = process.env.PORT || 8369;
    
    // System components
    this.systems = {};
    this.connectedClients = new Map();
    this.isRunning = false;
    this.demoMode = process.env.DEMO_MODE !== 'false'; // Default to demo mode
    
    this.setupMiddleware();
    this.setupRoutes();
    this.setupSocketHandlers();
    this.initializeSystems();
  }

  setupMiddleware() {
    this.app.use(helmet({
      contentSecurityPolicy: false // Allow inline scripts for demo
    }));
    this.app.use(compression());
    this.app.use(cors({
      origin: ["http://localhost:3000", "http://localhost:8369"],
      credentials: true
    }));
    this.app.use(morgan('combined'));
    this.app.use(express.json());
    this.app.use(express.static(path.join(__dirname, '../public')));
  }

  async initializeSystems() {
    try {
      logger.info('Initializing Screen Intelligence systems...');
      
      // Initialize core systems
      this.systems.radarAnalysis = new RadarAnalysisSystem();
      this.systems.vesselRecognition = new VesselRecognition();
      this.systems.overlaySystem = new OverlaySystem();
      this.systems.heatMapSystem = new HeatMapSystem();
      this.systems.timeZeroIntegration = new TimeZeroIntegration();
      this.systems.chartExtractor = new ChartExtractor();
      this.systems.mobileStreaming = new MobileStreaming();
      this.systems.gestureControl = new GestureControl();
      this.systems.automationEngine = new AutomationEngine();
      this.systems.historicalPlayback = new HistoricalPlayback();
      
      // Initialize all systems
      await Promise.all([
        this.systems.overlaySystem.initialize(),
        this.systems.heatMapSystem.initialize(),
        this.systems.timeZeroIntegration.initialize(),
        this.systems.chartExtractor.initialize(),
        this.systems.mobileStreaming.initialize(),
        this.systems.historicalPlayback.initialize()
      ]);

      logger.info('All systems initialized successfully');
      
      // Initialize frame capture and AI systems (these might fail in headless mode)
      if (!this.demoMode) {
        await this.initializeAdvancedSystems();
      } else {
        logger.info('Running in demo mode - advanced systems simulated');
        this.setupDemoData();
      }
      
    } catch (error) {
      logger.error('Failed to initialize systems:', error);
      // Continue in demo mode if initialization fails
      this.demoMode = true;
      this.setupDemoData();
    }
  }

  async initializeAdvancedSystems() {
    try {
      // Try to initialize frame capture
      this.systems.frameCapture = new FrameCapture(config.frameCapture);
      await this.systems.frameCapture.initialize();
      
      // Initialize AI detection
      this.systems.aiDetection = new AIBasedMomentDetection(config.aiDetection);
      await this.systems.aiDetection.initialize();
      
      // Connect frame capture to AI analysis
      this.systems.frameCapture.on('frame', async (frameData) => {
        try {
          const analysis = await this.systems.aiDetection.analyzeFrame(frameData);
          this.handleFrameAnalysis(frameData, analysis);
        } catch (error) {
          logger.error('Frame analysis error:', error);
        }
      });
      
      logger.info('Advanced systems initialized successfully');
    } catch (error) {
      logger.error('Advanced systems failed to initialize:', error);
      throw error;
    }
  }

  setupDemoData() {
    // Create demo data generators
    this.demoInterval = setInterval(() => {
      this.generateDemoEvents();
    }, 2000);
    
    logger.info('Demo mode activated - generating simulated data');
  }

  generateDemoEvents() {
    // Generate simulated frame and analysis data
    const demoFrame = {
      id: `demo_frame_${Date.now()}`,
      timestamp: Date.now(),
      metadata: {
        width: 1920,
        height: 1080,
        hasMotion: Math.random() > 0.7,
        motionLevel: Math.random() * 0.5,
        significantChange: Math.random() > 0.8
      }
    };

    const demoAnalysis = {
      timestamp: Date.now(),
      frameId: demoFrame.id,
      significantMoments: Math.random() > 0.6 ? [{
        type: ['chart_change', 'radar_contact', 'navigation_change'][Math.floor(Math.random() * 3)],
        confidence: Math.random() * 0.4 + 0.6,
        timestamp: Date.now()
      }] : []
    };

    this.handleFrameAnalysis(demoFrame, demoAnalysis);
  }

  handleFrameAnalysis(frameData, analysis) {
    // Update heat maps
    this.systems.heatMapSystem.updateFromFrame(frameData, analysis);
    
    // Process with radar analysis
    this.systems.radarAnalysis.analyzeFrame(frameData);
    
    // Extract chart information
    this.systems.chartExtractor.extractFromFrame(frameData);
    
    // Emit to connected clients
    this.io.emit('frame-update', {
      frameId: frameData.id,
      timestamp: frameData.timestamp,
      hasMotion: frameData.metadata?.hasMotion,
      analysisComplete: !!analysis
    });
    
    if (analysis && analysis.significantMoments.length > 0) {
      this.io.emit('ai-event', {
        frameId: frameData.id,
        moments: analysis.significantMoments,
        timestamp: analysis.timestamp
      });
    }
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        systems: {
          frameCapture: !!this.systems.frameCapture,
          aiDetection: !!this.systems.aiDetection,
          radarAnalysis: !!this.systems.radarAnalysis,
          overlaySystem: !!this.systems.overlaySystem
        },
        connectedClients: this.connectedClients.size,
        demoMode: this.demoMode
      });
    });

    // Frame capture controls
    this.app.post('/api/capture/start', async (req, res) => {
      try {
        if (this.systems.frameCapture && !this.demoMode) {
          await this.systems.frameCapture.start();
          res.json({ success: true, message: 'Frame capture started' });
        } else {
          res.json({ success: true, message: 'Demo mode - simulated capture started' });
        }
      } catch (error) {
        res.status(500).json({ success: false, error: error.message });
      }
    });

    this.app.post('/api/capture/stop', async (req, res) => {
      try {
        if (this.systems.frameCapture && !this.demoMode) {
          await this.systems.frameCapture.stop();
          res.json({ success: true, message: 'Frame capture stopped' });
        } else {
          res.json({ success: true, message: 'Demo mode - simulated capture stopped' });
        }
      } catch (error) {
        res.status(500).json({ success: false, error: error.message });
      }
    });

    // Overlay system
    this.app.post('/api/overlay/create', async (req, res) => {
      try {
        const { type, data, position } = req.body;
        const overlayId = await this.systems.overlaySystem.createOverlay(type, data, position);
        res.json({ success: true, overlayId });
      } catch (error) {
        res.status(500).json({ success: false, error: error.message });
      }
    });

    this.app.delete('/api/overlay/:id', async (req, res) => {
      try {
        await this.systems.overlaySystem.removeOverlay(req.params.id);
        res.json({ success: true });
      } catch (error) {
        res.status(500).json({ success: false, error: error.message });
      }
    });

    // Heat maps
    this.app.get('/api/heatmaps', (req, res) => {
      try {
        const heatMaps = this.systems.heatMapSystem.getAllHeatMaps();
        res.json(heatMaps);
      } catch (error) {
        res.status(500).json({ success: false, error: error.message });
      }
    });

    this.app.get('/api/heatmaps/:type', (req, res) => {
      try {
        const heatMap = this.systems.heatMapSystem.getHeatMap(req.params.type);
        if (heatMap) {
          res.json(heatMap);
        } else {
          res.status(404).json({ error: 'Heat map not found' });
        }
      } catch (error) {
        res.status(500).json({ success: false, error: error.message });
      }
    });

    // Radar analysis
    this.app.get('/api/radar/targets', (req, res) => {
      try {
        const targets = this.systems.radarAnalysis.getDetectedTargets();
        res.json(targets);
      } catch (error) {
        res.status(500).json({ success: false, error: error.message });
      }
    });

    this.app.get('/api/radar/status', (req, res) => {
      try {
        const status = this.systems.radarAnalysis.getStatus();
        res.json(status);
      } catch (error) {
        res.status(500).json({ success: false, error: error.message });
      }
    });

    // TimeZero integration
    this.app.get('/api/timezero/vessels', (req, res) => {
      try {
        const vessels = this.systems.timeZeroIntegration.getVessels();
        res.json(vessels);
      } catch (error) {
        res.status(500).json({ success: false, error: error.message });
      }
    });

    this.app.get('/api/timezero/waypoints', (req, res) => {
      try {
        const waypoints = this.systems.timeZeroIntegration.getWaypoints();
        res.json(waypoints);
      } catch (error) {
        res.status(500).json({ success: false, error: error.message });
      }
    });

    // Chart extraction
    this.app.get('/api/charts/current', (req, res) => {
      try {
        const chart = this.systems.chartExtractor.getCurrentChart();
        res.json(chart || { message: 'No chart data available' });
      } catch (error) {
        res.status(500).json({ success: false, error: error.message });
      }
    });

    // System status
    this.app.get('/api/status', (req, res) => {
      res.json({
        timestamp: new Date().toISOString(),
        systems: {
          frameCapture: this.systems.frameCapture?.isActive() || false,
          aiDetection: this.systems.aiDetection?.isReady() || false,
          radarAnalysis: this.systems.radarAnalysis?.isAnalyzing || false,
          overlaySystem: this.systems.overlaySystem?.isActive() || false,
          mobileStreaming: this.systems.mobileStreaming?.isStreaming() || false
        },
        connectedClients: this.connectedClients.size,
        demoMode: this.demoMode
      });
    });

    // Default route
    this.app.get('/', (req, res) => {
      res.sendFile(path.join(__dirname, '../public/index.html'));
    });
  }

  setupSocketHandlers() {
    this.io.on('connection', (socket) => {
      logger.info(`Client connected: ${socket.id}`);
      this.connectedClients.set(socket.id, {
        id: socket.id,
        connectedAt: Date.now(),
        userAgent: socket.handshake.headers['user-agent']
      });

      // Send initial system status
      socket.emit('system-status', {
        frameCapture: this.systems.frameCapture?.isActive() || false,
        aiDetection: this.systems.aiDetection?.isReady() || false,
        demoMode: this.demoMode
      });

      // Handle mobile gestures
      socket.on('gesture', (data) => {
        this.systems.gestureControl.processGesture(data, socket.id);
      });

      // Handle automation commands
      socket.on('automation-command', async (data) => {
        try {
          const result = await this.systems.automationEngine.executeAction(data.action, data.parameters);
          socket.emit('automation-result', result);
        } catch (error) {
          socket.emit('automation-error', { error: error.message });
        }
      });

      socket.on('disconnect', () => {
        logger.info(`Client disconnected: ${socket.id}`);
        this.connectedClients.delete(socket.id);
      });
    });
  }

  async start() {
    try {
      this.server.listen(this.port, () => {
        logger.info(`🖥️  Screen Intelligence Server running on port ${this.port}`);
        logger.info(`📊 Dashboard: http://localhost:${this.port}`);
        logger.info(`🔧 API: http://localhost:${this.port}/api/status`);
        if (this.demoMode) {
          logger.info('🎮 Demo Mode: Generating simulated data');
        }
      });
      
      this.isRunning = true;

      // Graceful shutdown handling
      process.on('SIGINT', () => this.shutdown());
      process.on('SIGTERM', () => this.shutdown());
      process.on('uncaughtException', (error) => {
        logger.error('Uncaught Exception:', error);
        this.shutdown();
      });

    } catch (error) {
      logger.error('Failed to start server:', error);
      process.exit(1);
    }
  }

  async shutdown() {
    logger.info('Shutting down Screen Intelligence Server...');
    
    try {
      // Stop demo data generation
      if (this.demoInterval) {
        clearInterval(this.demoInterval);
      }

      // Stop frame capture if running
      if (this.systems.frameCapture) {
        if (this.systems.frameCapture.isActive && this.systems.frameCapture.isActive()) {
          await this.systems.frameCapture.stop();
        } else {
          logger.warn('Screen capture not running');
        }
      } else {
        logger.warn('Screen capture not running');
      }

      // Cleanup all systems
      await Promise.all([
        this.systems.overlaySystem?.cleanup(),
        this.systems.heatMapSystem?.cleanup?.(),
        this.systems.radarAnalysis?.cleanup(),
        this.systems.aiDetection?.cleanup?.(),
        this.systems.timeZeroIntegration?.cleanup(),
        this.systems.chartExtractor?.cleanup(),
        this.systems.mobileStreaming?.cleanup?.(),
        this.systems.historicalPlayback?.cleanup()
      ]);

      // Close server
      this.server.close(() => {
        logger.info('Screen Intelligence Server stopped');
        process.exit(0);
      });

    } catch (error) {
      logger.error('Error during shutdown:', error);
      process.exit(1);
    }
  }
}

// Start the server
const server = new ScreenIntelligenceServer();
server.start();

module.exports = ScreenIntelligenceServer;