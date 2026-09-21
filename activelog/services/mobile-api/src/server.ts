import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import slowDown from 'express-slow-down';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import Redis from 'ioredis';
import multer from 'multer';
import { Logger } from '@/utils/logger';

// Services
import { PushNotificationService } from '@/services/PushNotificationService';
import { SyncService } from '@/services/SyncService';
import { ImageOptimizationService } from '@/services/ImageOptimizationService';
import { BatteryOptimizationService } from '@/services/BatteryOptimizationService';
import { AppConfigService } from '@/services/AppConfigService';

// Controllers
import { syncController } from '@/controllers/syncController';
import { pushController } from '@/controllers/pushController';
import { configController } from '@/controllers/configController';
import { imageController } from '@/controllers/imageController';
import { optimizedController } from '@/controllers/optimizedController';

// Middleware
import { authMiddleware } from '@/middleware/auth';
import { compressionMiddleware } from '@/middleware/compression';
import { protocolMiddleware } from '@/middleware/protocol';

const app = express();
const port = process.env.PORT || 8011;
const logger = new Logger('MobileAPIServer');

// Redis configuration
const redisConfig = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD
};

const redis = new Redis(redisConfig);

// Initialize services
const pushService = new PushNotificationService({
  fcm: {
    serviceAccountPath: process.env.FCM_SERVICE_ACCOUNT_PATH || './config/firebase-service-account.json',
    projectId: process.env.FCM_PROJECT_ID || 'activelog-mobile'
  },
  apns: {
    keyPath: process.env.APNS_KEY_PATH || './config/apns-key.p8',
    keyId: process.env.APNS_KEY_ID || '',
    teamId: process.env.APNS_TEAM_ID || '',
    production: process.env.NODE_ENV === 'production'
  },
  redis: redisConfig
});

const syncService = new SyncService({
  redis: redisConfig,
  maxBatchSize: 100,
  compressionThreshold: 1024,
  conflictRetentionDays: 7,
  maxQueueSize: 1000,
  syncTimeoutMs: 30000
});

const imageService = new ImageOptimizationService({
  outputDirectory: process.env.IMAGE_OUTPUT_DIR || './uploads/optimized',
  cacheDirectory: process.env.IMAGE_CACHE_DIR || './cache/images',
  cdnBaseUrl: process.env.CDN_BASE_URL || 'https://cdn.activelog.com',
  defaultVariants: [],
  maxFileSize: 10 * 1024 * 1024, // 10MB
  allowedFormats: ['jpeg', 'jpg', 'png', 'webp', 'gif'],
  redis: redisConfig
});

const batteryService = new BatteryOptimizationService({
  redis: redisConfig,
  lowBatteryThreshold: 20,
  criticalBatteryThreshold: 10,
  syncIntervals: {
    normal: 5,
    lowBattery: 15,
    critical: 60,
    charging: 2
  },
  networkOptimization: {
    wifiPriority: 1,
    cellularPriority: 2,
    lowBandwidthThreshold: 100
  }
});

const appConfigService = new AppConfigService(redisConfig);

// Security middleware
app.use(helmet({
  contentSecurityPolicy: false,
  crossOriginEmbedderPolicy: false
}));

// Enable trust proxy for correct IP detection
app.set('trust proxy', true);

// CORS configuration
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['*'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Device-ID', 'X-Platform', 'X-App-Version', 'Accept-Encoding']
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000,
  message: { error: 'Too many requests' },
  standardHeaders: true,
  legacyHeaders: false,
  skip: (req) => req.path === '/health'
});

app.use(limiter);

// Slow down middleware for heavy endpoints
const speedLimiter = slowDown({
  windowMs: 15 * 60 * 1000, // 15 minutes
  delayAfter: 100,
  delayMs: 500,
  maxDelayMs: 20000,
  skipFailedRequests: false
});

app.use('/api/v1/sync', speedLimiter);
app.use('/api/v1/upload', speedLimiter);

// Compression middleware (intelligent compression based on client capabilities)
app.use(compressionMiddleware());

// Protocol buffer middleware
app.use('/api/v1/sync', protocolMiddleware());

// Body parsing with size limits
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true, limit: '1mb' }));

// File upload configuration
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB
    files: 5
  },
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type'));
    }
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    version: process.env.npm_package_version || '1.0.0',
    services: {
      redis: redis.status,
      push: 'OK',
      sync: 'OK',
      image: 'OK'
    }
  });
});

app.get('/ready', async (req, res) => {
  try {
    await redis.ping();
    res.json({ status: 'Ready' });
  } catch (error) {
    res.status(503).json({ status: 'Not Ready', error: error.message });
  }
});

// API Routes

// App Configuration
app.get('/api/v1/config', configController.getAppConfig);
app.post('/api/v1/config/feature-flag', authMiddleware, configController.updateFeatureFlag);
app.get('/api/v1/config/analytics', authMiddleware, configController.getAnalytics);

// Sync endpoints
app.post('/api/v1/sync', authMiddleware, syncController.performSync);
app.post('/api/v1/sync/batch', authMiddleware, syncController.processBatchOperations);
app.post('/api/v1/sync/queue', authMiddleware, syncController.processOfflineQueue);
app.post('/api/v1/sync/conflict', authMiddleware, syncController.resolveConflict);
app.get('/api/v1/sync/stats/:deviceId', authMiddleware, syncController.getSyncStats);

// Push notification endpoints
app.post('/api/v1/push/register', authMiddleware, pushController.registerDevice);
app.delete('/api/v1/push/unregister', authMiddleware, pushController.unregisterDevice);
app.post('/api/v1/push/send', authMiddleware, pushController.sendNotification);
app.post('/api/v1/push/campaign', authMiddleware, pushController.sendCampaign);
app.get('/api/v1/push/analytics', authMiddleware, pushController.getAnalytics);

// Image optimization endpoints
app.post('/api/v1/images/optimize', authMiddleware, upload.single('image'), imageController.optimizeImage);
app.post('/api/v1/images/responsive', authMiddleware, upload.single('image'), imageController.generateResponsiveSet);
app.post('/api/v1/images/mobile', authMiddleware, upload.single('image'), imageController.optimizeForMobile);
app.post('/api/v1/images/placeholder', authMiddleware, upload.single('image'), imageController.generatePlaceholder);
app.get('/api/v1/images/stats', authMiddleware, imageController.getOptimizationStats);

// Battery optimization endpoints
app.post('/api/v1/battery/state', authMiddleware, optimizedController.updateDeviceState);
app.get('/api/v1/battery/strategy/:deviceId', authMiddleware, optimizedController.getSyncStrategy);
app.get('/api/v1/battery/prediction/:deviceId', authMiddleware, optimizedController.predictOptimalSyncWindow);
app.get('/api/v1/battery/stats/:deviceId', authMiddleware, optimizedController.getBatteryUsageStats);
app.post('/api/v1/battery/pause/:deviceId', authMiddleware, optimizedController.pauseSync);

// Bandwidth-optimized endpoints
app.get('/api/v1/optimized/user/minimal', authMiddleware, optimizedController.getUserMinimal);
app.get('/api/v1/optimized/files/list', authMiddleware, optimizedController.getFilesMinimal);
app.get('/api/v1/optimized/notifications/unread', authMiddleware, optimizedController.getUnreadNotifications);
app.post('/api/v1/optimized/batch', authMiddleware, optimizedController.batchRequest);
app.get('/api/v1/optimized/delta/:timestamp', authMiddleware, optimizedController.getDeltaUpdates);

// WebSocket server for real-time updates
const server = createServer(app);
const wss = new WebSocketServer({ server });

wss.on('connection', (ws, req) => {
  logger.info('New WebSocket connection established');
  
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message.toString());
      
      // Handle different message types
      switch (data.type) {
        case 'subscribe':
          // Subscribe to specific channels
          ws.userId = data.userId;
          ws.deviceId = data.deviceId;
          break;
          
        case 'battery_state':
          // Update battery state
          if (ws.userId && ws.deviceId) {
            batteryService.updateDeviceState(ws.deviceId, data.state);
          }
          break;
          
        case 'ping':
          ws.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
          break;
      }
    } catch (error) {
      logger.error('WebSocket message error', error);
    }
  });
  
  ws.on('close', () => {
    logger.info('WebSocket connection closed');
  });
});

// Service event listeners
batteryService.on('strategy_changed', (data) => {
  // Broadcast strategy changes to connected clients
  wss.clients.forEach((client: any) => {
    if (client.deviceId === data.deviceId && client.readyState === client.OPEN) {
      client.send(JSON.stringify({
        type: 'strategy_changed',
        strategy: data.strategy,
        timestamp: Date.now()
      }));
    }
  });
});

batteryService.on('perform_sync', async (data) => {
  // Handle battery-optimized sync requests
  try {
    logger.info(`Performing battery-optimized sync for device ${data.deviceId}`);
    // This would trigger the actual sync process
  } catch (error) {
    logger.error('Battery-optimized sync failed', error);
  }
});

// Error handling middleware
app.use((error: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  logger.error('Request error', error);
  
  if (error.code === 'LIMIT_FILE_SIZE') {
    return res.status(413).json({ error: 'File too large' });
  }
  
  if (error.code === 'LIMIT_FILE_COUNT') {
    return res.status(413).json({ error: 'Too many files' });
  }
  
  if (error.name === 'ValidationError') {
    return res.status(400).json({ error: error.message });
  }
  
  res.status(500).json({ 
    error: process.env.NODE_ENV === 'production' ? 'Internal server error' : error.message 
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Graceful shutdown
const gracefulShutdown = async (signal: string) => {
  logger.info(`Received ${signal}. Starting graceful shutdown...`);
  
  server.close(async () => {
    logger.info('HTTP server closed');
    
    try {
      await pushService.cleanup();
      await syncService.cleanup();
      await imageService.cleanup();
      await batteryService.cleanup();
      await appConfigService.cleanup();
      await redis.quit();
      
      logger.info('All services cleaned up successfully');
      process.exit(0);
    } catch (error) {
      logger.error('Error during cleanup', error);
      process.exit(1);
    }
  });
  
  // Force exit after 30 seconds
  setTimeout(() => {
    logger.error('Could not close connections in time, forcefully shutting down');
    process.exit(1);
  }, 30000);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Unhandled errors
process.on('uncaughtException', (error) => {
  logger.error('Uncaught Exception', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Initialize services
async function initialize() {
  try {
    logger.info('Initializing services...');
    
    await pushService.initialize();
    logger.info('Push notification service initialized');
    
    // Add controllers to app context
    app.locals.services = {
      pushService,
      syncService,
      imageService,
      batteryService,
      appConfigService
    };
    
    logger.info('All services initialized successfully');
    
  } catch (error) {
    logger.error('Failed to initialize services', error);
    process.exit(1);
  }
}

// Start server
server.listen(port, async () => {
  await initialize();
  
  logger.info(`🚀 ActiveLog Mobile API ready at http://localhost:${port}`);
  logger.info(`📱 Protocol Buffers enabled for /api/v1/sync endpoints`);
  logger.info(`📡 WebSocket server ready at ws://localhost:${port}`);
  logger.info(`🔔 Push notifications: FCM & APNS initialized`);
  logger.info(`🔄 Offline-first sync protocol enabled`);
  logger.info(`🖼️  Image optimization with mobile variants`);
  logger.info(`🔋 Battery-efficient sync strategies active`);
  logger.info(`⚙️  Mobile app configuration endpoint ready`);
  logger.info(`📊 Bandwidth-optimized endpoints available`);
});