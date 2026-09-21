const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const winston = require('winston');
const config = require('./config/config');

// Import core services
const UnrealEngineService = require('./services/UnrealEngineService');
const UnityConnectorService = require('./services/UnityConnectorService');
const RetroEngineService = require('./services/RetroEngineService');
const FFTacticsRendererService = require('./services/FFTacticsRendererService');
const VoiceListenerService = require('./services/VoiceListenerService');
const SceneGeneratorService = require('./services/SceneGeneratorService');
const CharacterModelService = require('./services/CharacterModelService');
const CameraOptimizerService = require('./services/CameraOptimizerService');
const VideoGeneratorService = require('./services/VideoGeneratorService');
const MusicWeaverService = require('./services/MusicWeaverService');
const StyleTemplateService = require('./services/StyleTemplateService');
const FilmmakerModeService = require('./services/FilmmakerModeService');
const StreamingExportService = require('./services/StreamingExportService');

// Import routes
const unrealRoutes = require('./routes/unrealRoutes');
const unityRoutes = require('./routes/unityRoutes');
const retroRoutes = require('./routes/retroRoutes');
const battleRoutes = require('./routes/battleRoutes');
const voiceRoutes = require('./routes/voiceRoutes');
const sceneRoutes = require('./routes/sceneRoutes');
const characterRoutes = require('./routes/characterRoutes');
const cameraRoutes = require('./routes/cameraRoutes');
const videoRoutes = require('./routes/videoRoutes');
const musicRoutes = require('./routes/musicRoutes');
const styleRoutes = require('./routes/styleRoutes');
const filmmakerRoutes = require('./routes/filmmakerRoutes');
const exportRoutes = require('./routes/exportRoutes');

// Import middleware
const authMiddleware = require('./middleware/auth');
const rateLimiter = require('./middleware/rateLimiter');
const errorHandler = require('./middleware/errorHandler');

// Logger setup
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.colorize(),
    winston.format.simple()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'dmlog-visualizer.log' })
  ]
});

class DMLogVisualizerService {
  constructor() {
    this.app = express();
    this.server = http.createServer(this.app);
    this.io = socketIo(this.server, {
      cors: {
        origin: "*",
        methods: ["GET", "POST", "PUT", "DELETE"]
      },
      transports: ['websocket', 'polling']
    });
    
    this.services = {};
    this.activeConnections = new Map();
    this.renderingSessions = new Map();
    this.voiceStreams = new Map();
    
    this.setupMiddleware();
    this.initializeServices();
    this.setupRoutes();
    this.setupSocketHandlers();
    this.setupErrorHandling();
  }

  setupMiddleware() {
    // Security and performance middleware
    this.app.use(helmet({
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
          scriptSrc: ["'self'", "'unsafe-eval'"],
          imgSrc: ["'self'", "data:", "blob:", "https:"],
          mediaSrc: ["'self'", "blob:", "https:"],
          connectSrc: ["'self'", "ws:", "wss:", "https:"]
        }
      }
    }));
    
    this.app.use(compression());
    this.app.use(cors({
      origin: process.env.NODE_ENV === 'production' ? 
        config.allowedOrigins : true,
      credentials: true
    }));
    
    this.app.use(express.json({ limit: '50mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '50mb' }));
    
    // Rate limiting
    this.app.use('/api/', rateLimiter);
    
    // Request logging
    this.app.use((req, res, next) => {
      logger.info(`${req.method} ${req.path} - ${req.ip}`);
      next();
    });
  }

  async initializeServices() {
    try {
      logger.info('Initializing DMLog Visualizer services...');
      
      // Initialize core rendering engines
      this.services.unrealEngine = new UnrealEngineService({
        enginePath: config.unreal.enginePath,
        projectPath: config.unreal.projectPath,
        renderSettings: config.unreal.renderSettings
      });
      
      this.services.unityConnector = new UnityConnectorService({
        unityPath: config.unity.unityPath,
        projectPath: config.unity.projectPath,
        buildSettings: config.unity.buildSettings
      });
      
      this.services.retroEngine = new RetroEngineService({
        spriteLibrary: config.retro.spriteLibrary,
        audioLibrary: config.retro.audioLibrary,
        renderSettings: config.retro.renderSettings
      });
      
      this.services.fftacticsRenderer = new FFTacticsRendererService({
        tilesets: config.ffTactics.tilesets,
        characterSprites: config.ffTactics.characterSprites,
        effects: config.ffTactics.effects
      });
      
      // Initialize AI and processing services
      this.services.voiceListener = new VoiceListenerService({
        speechToTextService: config.ai.speechToText,
        languageModels: config.ai.languageModels,
        realtimeProcessing: true
      });
      
      this.services.sceneGenerator = new SceneGeneratorService({
        aiModels: config.ai.models,
        sceneTemplates: config.scenes.templates,
        environmentLibrary: config.scenes.environments
      });
      
      this.services.characterModel = new CharacterModelService({
        modelLibrary: config.characters.modelLibrary,
        customizationOptions: config.characters.customization,
        animationSets: config.characters.animations
      });
      
      this.services.cameraOptimizer = new CameraOptimizerService({
        cinematicRules: config.camera.cinematicRules,
        aiOptimization: config.camera.aiOptimization
      });
      
      // Initialize media and export services
      this.services.videoGenerator = new VideoGeneratorService({
        renderSettings: config.video.renderSettings,
        aiEditing: config.video.aiEditing,
        templates: config.video.templates
      });
      
      this.services.musicWeaver = new MusicWeaverService({
        musicLibrary: config.audio.musicLibrary,
        aiComposition: config.audio.aiComposition,
        themes: config.audio.themes
      });
      
      this.services.styleTemplate = new StyleTemplateService({
        visualStyles: config.styles.visualStyles,
        campaigns: config.styles.campaigns
      });
      
      this.services.filmmakerMode = new FilmmakerModeService({
        previewTools: config.filmmaker.previewTools,
        planning: config.filmmaker.planning
      });
      
      this.services.streamingExport = new StreamingExportService({
        platforms: config.streaming.platforms,
        encodingSettings: config.streaming.encoding
      });
      
      // Initialize all services
      const servicePromises = Object.values(this.services).map(service => {
        if (service.initialize) {
          return service.initialize();
        }
      });
      
      await Promise.all(servicePromises);
      
      logger.info('All DMLog Visualizer services initialized successfully');
      
    } catch (error) {
      logger.error('Failed to initialize services:', error);
      throw error;
    }
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      const serviceStatus = {};
      Object.keys(this.services).forEach(key => {
        serviceStatus[key] = this.services[key].isHealthy ? this.services[key].isHealthy() : 'unknown';
      });
      
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: process.env.npm_package_version || '1.0.0',
        services: serviceStatus,
        activeConnections: this.activeConnections.size,
        renderingSessions: this.renderingSessions.size,
        voiceStreams: this.voiceStreams.size
      });
    });

    // API routes
    this.app.use('/api/unreal', authMiddleware, unrealRoutes);
    this.app.use('/api/unity', authMiddleware, unityRoutes);
    this.app.use('/api/retro', authMiddleware, retroRoutes);
    this.app.use('/api/battle', authMiddleware, battleRoutes);
    this.app.use('/api/voice', authMiddleware, voiceRoutes);
    this.app.use('/api/scene', authMiddleware, sceneRoutes);
    this.app.use('/api/character', authMiddleware, characterRoutes);
    this.app.use('/api/camera', authMiddleware, cameraRoutes);
    this.app.use('/api/video', authMiddleware, videoRoutes);
    this.app.use('/api/music', authMiddleware, musicRoutes);
    this.app.use('/api/style', authMiddleware, styleRoutes);
    this.app.use('/api/filmmaker', authMiddleware, filmmakerRoutes);
    this.app.use('/api/export', authMiddleware, exportRoutes);

    // Service info endpoint
    this.app.get('/api/info', (req, res) => {
      res.json({
        serviceName: 'DMLog Visualizer',
        version: '1.0.0',
        description: 'Advanced game engine integration service for DMLog with battle visualization and cinematic rendering',
        features: [
          'Unreal Engine Integration',
          'Unity Connector',
          'Retro Engine Support (SNES-style)',
          'Final Fantasy Tactics Renderer',
          'Real-time DM Voice Recognition',
          'Automatic Scene Generation',
          'Character Model Library',
          'AI Camera Optimization',
          'Recap Video Generation',
          'Music Theme Weaving',
          'Visual Style Templates',
          'Filmmaker Mockup Mode',
          'Streaming Platform Export'
        ],
        endpoints: {
          unreal: '/api/unreal',
          unity: '/api/unity',
          retro: '/api/retro',
          battle: '/api/battle',
          voice: '/api/voice',
          scene: '/api/scene',
          character: '/api/character',
          camera: '/api/camera',
          video: '/api/video',
          music: '/api/music',
          style: '/api/style',
          filmmaker: '/api/filmmaker',
          export: '/api/export'
        },
        supportedEngines: [
          'Unreal Engine 5',
          'Unity 2023 LTS',
          'Retro Pixel Engine',
          'FFTactics-style Renderer',
          'Three.js WebGL',
          'Babylon.js'
        ],
        supportedPlatforms: [
          'YouTube',
          'Twitch',
          'Discord',
          'OBS Studio',
          'RTMP Streaming',
          'WebRTC'
        ]
      });
    });
  }

  setupSocketHandlers() {
    this.io.on('connection', (socket) => {
      logger.info(`New client connected: ${socket.id}`);
      this.activeConnections.set(socket.id, {
        connectedAt: new Date(),
        userId: null,
        campaignId: null,
        renderingEngine: null
      });

      // Authentication
      socket.on('authenticate', async (data) => {
        try {
          // Verify JWT token and set user info
          const connection = this.activeConnections.get(socket.id);
          connection.userId = data.userId;
          connection.campaignId = data.campaignId;
          
          socket.join(`campaign:${data.campaignId}`);
          socket.emit('authenticated', { status: 'success' });
          
          logger.info(`Client ${socket.id} authenticated for campaign ${data.campaignId}`);
        } catch (error) {
          socket.emit('authentication_error', { error: error.message });
        }
      });

      // Voice stream handling
      socket.on('voice_stream_start', (data) => {
        const { campaignId, dmId } = data;
        const streamId = `${campaignId}_${dmId}`;
        
        this.voiceStreams.set(streamId, {
          socketId: socket.id,
          campaignId,
          dmId,
          startedAt: new Date(),
          processor: this.services.voiceListener.createStream(streamId)
        });
        
        logger.info(`Voice stream started: ${streamId}`);
        socket.emit('voice_stream_ready', { streamId });
      });

      socket.on('voice_data', async (data) => {
        const { streamId, audioData } = data;
        const stream = this.voiceStreams.get(streamId);
        
        if (stream) {
          try {
            const result = await stream.processor.processAudio(audioData);
            if (result.transcription) {
              // Process DM narration for scene generation
              const sceneUpdate = await this.services.sceneGenerator.processNarration(
                result.transcription,
                stream.campaignId
              );
              
              if (sceneUpdate) {
                this.io.to(`campaign:${stream.campaignId}`).emit('scene_update', sceneUpdate);
              }
            }
          } catch (error) {
            logger.error(`Voice processing error: ${error.message}`);
          }
        }
      });

      // Rendering session handling
      socket.on('start_rendering', async (data) => {
        const { engine, sceneData, campaignId } = data;
        const sessionId = `${campaignId}_${Date.now()}`;
        
        try {
          let renderer;
          switch (engine) {
            case 'unreal':
              renderer = this.services.unrealEngine;
              break;
            case 'unity':
              renderer = this.services.unityConnector;
              break;
            case 'retro':
              renderer = this.services.retroEngine;
              break;
            case 'fftactics':
              renderer = this.services.fftacticsRenderer;
              break;
            default:
              throw new Error(`Unsupported engine: ${engine}`);
          }
          
          const session = await renderer.startRenderSession(sessionId, sceneData);
          this.renderingSessions.set(sessionId, {
            engine,
            renderer,
            session,
            socketId: socket.id,
            campaignId,
            startedAt: new Date()
          });
          
          socket.emit('rendering_started', { sessionId, status: 'active' });
          logger.info(`Rendering session started: ${sessionId} using ${engine}`);
          
        } catch (error) {
          socket.emit('rendering_error', { error: error.message });
          logger.error(`Rendering start error: ${error.message}`);
        }
      });

      // Real-time scene updates
      socket.on('scene_update', async (data) => {
        const { sessionId, updates } = data;
        const session = this.renderingSessions.get(sessionId);
        
        if (session) {
          try {
            await session.renderer.updateScene(session.session, updates);
            
            // Broadcast to all campaign participants
            this.io.to(`campaign:${session.campaignId}`).emit('scene_rendered', {
              sessionId,
              updates,
              timestamp: new Date()
            });
          } catch (error) {
            socket.emit('scene_update_error', { error: error.message });
          }
        }
      });

      // Battle visualization
      socket.on('battle_start', async (data) => {
        const { campaignId, battleData, visualStyle } = data;
        
        try {
          const battleSession = await this.services.fftacticsRenderer.initializeBattle(
            battleData,
            visualStyle
          );
          
          this.io.to(`campaign:${campaignId}`).emit('battle_initialized', {
            battleId: battleSession.id,
            initialState: battleSession.state
          });
          
        } catch (error) {
          socket.emit('battle_error', { error: error.message });
        }
      });

      // Video generation requests
      socket.on('generate_recap_video', async (data) => {
        const { campaignId, sessionData, style } = data;
        
        try {
          const videoJob = await this.services.videoGenerator.createRecapVideo(
            sessionData,
            style,
            campaignId
          );
          
          socket.emit('video_generation_started', { jobId: videoJob.id });
          
          // Monitor video generation progress
          videoJob.on('progress', (progress) => {
            socket.emit('video_progress', { jobId: videoJob.id, progress });
          });
          
          videoJob.on('complete', (result) => {
            socket.emit('video_complete', { 
              jobId: videoJob.id, 
              videoUrl: result.url,
              metadata: result.metadata
            });
          });
          
        } catch (error) {
          socket.emit('video_error', { error: error.message });
        }
      });

      // Disconnect handling
      socket.on('disconnect', () => {
        logger.info(`Client disconnected: ${socket.id}`);
        
        // Clean up resources
        this.activeConnections.delete(socket.id);
        
        // Clean up voice streams
        for (const [streamId, stream] of this.voiceStreams.entries()) {
          if (stream.socketId === socket.id) {
            stream.processor.cleanup();
            this.voiceStreams.delete(streamId);
          }
        }
        
        // Clean up rendering sessions
        for (const [sessionId, session] of this.renderingSessions.entries()) {
          if (session.socketId === socket.id) {
            session.renderer.cleanupSession(session.session);
            this.renderingSessions.delete(sessionId);
          }
        }
      });
    });
  }

  setupErrorHandling() {
    this.app.use(errorHandler);

    process.on('uncaughtException', (error) => {
      logger.error('Uncaught Exception:', error);
      process.exit(1);
    });

    process.on('unhandledRejection', (reason, promise) => {
      logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
    });
  }

  async start() {
    try {
      const PORT = config.server.port || 8315;
      
      this.server.listen(PORT, '0.0.0.0', () => {
        logger.info(`DMLog Visualizer Service running on port ${PORT}`);
        logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
        logger.info('Supported engines: Unreal Engine 5, Unity 2023, Retro Engine, FFTactics Renderer');
        logger.info('Features: Voice-to-Scene, Battle Visualization, Cinematic Rendering, Video Generation');
      });

      // Graceful shutdown
      process.on('SIGTERM', () => {
        logger.info('SIGTERM received, shutting down gracefully');
        this.server.close(() => {
          logger.info('Process terminated');
          process.exit(0);
        });
      });

    } catch (error) {
      logger.error('Failed to start DMLog Visualizer Service:', error);
      process.exit(1);
    }
  }
}

// Start the service
const visualizerService = new DMLogVisualizerService();
visualizerService.start().catch(console.error);

module.exports = DMLogVisualizerService;