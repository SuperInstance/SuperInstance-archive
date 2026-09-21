require('dotenv').config();

const config = {
  port: parseInt(process.env.PORT) || 8007,
  
  outputDir: process.env.OUTPUT_DIR || './output',
  tempDir: process.env.TEMP_DIR || './temp',
  
  maxConcurrentStreams: parseInt(process.env.MAX_CONCURRENT_STREAMS) || 5,
  
  upload: {
    maxFileSize: parseInt(process.env.MAX_FILE_SIZE) || 1024 * 1024 * 1024,
    allowedTypes: (process.env.ALLOWED_TYPES || 'video/mp4,video/avi,video/mkv,video/mov,video/wmv,video/flv').split(',')
  },
  
  cors: {
    origins: process.env.CORS_ORIGINS ? process.env.CORS_ORIGINS.split(',') : ['*']
  },
  
  keyframe: {
    threshold: parseFloat(process.env.KEYFRAME_THRESHOLD) || 0.3,
    minFrameDistance: parseInt(process.env.KEYFRAME_MIN_DISTANCE) || 30,
    maxKeyframes: parseInt(process.env.KEYFRAME_MAX_COUNT) || 50
  },
  
  thumbnail: {
    sizes: [
      { width: 160, height: 90, suffix: 'small' },
      { width: 320, height: 180, suffix: 'medium' },
      { width: 640, height: 360, suffix: 'large' }
    ],
    previewDuration: parseInt(process.env.PREVIEW_DURATION) || 10,
    previewFramerate: parseInt(process.env.PREVIEW_FRAMERATE) || 15
  },
  
  scene: {
    threshold: parseFloat(process.env.SCENE_THRESHOLD) || 0.4,
    minDuration: parseInt(process.env.SCENE_MIN_DURATION) || 2,
    adaptiveThreshold: process.env.SCENE_ADAPTIVE_THRESHOLD === 'true'
  },
  
  ocr: {
    languages: (process.env.OCR_LANGUAGES || 'eng').split(','),
    confidence: parseInt(process.env.OCR_CONFIDENCE) || 30,
    frameInterval: parseInt(process.env.OCR_FRAME_INTERVAL) || 30,
    preprocessing: {
      resize: process.env.OCR_RESIZE !== 'false',
      denoise: process.env.OCR_DENOISE !== 'false',
      contrast: process.env.OCR_CONTRAST !== 'false',
      sharpen: process.env.OCR_SHARPEN === 'true'
    }
  },
  
  ai: {
    provider: process.env.AI_PROVIDER || 'openai',
    model: process.env.AI_MODEL || 'gpt-3.5-turbo',
    maxTokens: parseInt(process.env.AI_MAX_TOKENS) || 1000,
    temperature: parseFloat(process.env.AI_TEMPERATURE) || 0.7,
    orchestratorUrl: process.env.AI_ORCHESTRATOR_URL || 'http://localhost:8003',
    apiKey: process.env.OPENAI_API_KEY || process.env.AI_API_KEY
  },
  
  subtitle: {
    indexGranularity: parseInt(process.env.SUBTITLE_INDEX_GRANULARITY) || 30,
    supportedFormats: ['srt', 'vtt', 'ass', 'ssa'],
    generateTranscript: process.env.GENERATE_TRANSCRIPT === 'true'
  },
  
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    format: process.env.LOG_FORMAT || 'combined',
    file: process.env.LOG_FILE || './logs/video-processor.log'
  },
  
  performance: {
    enableProfiling: process.env.ENABLE_PROFILING === 'true',
    maxMemoryUsage: parseInt(process.env.MAX_MEMORY_USAGE) || 2048,
    gcInterval: parseInt(process.env.GC_INTERVAL) || 300000
  },
  
  security: {
    enableRateLimit: process.env.ENABLE_RATE_LIMIT !== 'false',
    rateLimitMax: parseInt(process.env.RATE_LIMIT_MAX) || 100,
    rateLimitWindow: parseInt(process.env.RATE_LIMIT_WINDOW) || 900000,
    enableAuth: process.env.ENABLE_AUTH === 'true',
    authSecret: process.env.AUTH_SECRET || 'video-processor-secret'
  },
  
  database: {
    enabled: process.env.DB_ENABLED === 'true',
    type: process.env.DB_TYPE || 'sqlite',
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT) || 5432,
    name: process.env.DB_NAME || 'video_processor',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || '',
    connectionPool: {
      min: parseInt(process.env.DB_POOL_MIN) || 2,
      max: parseInt(process.env.DB_POOL_MAX) || 10
    }
  },
  
  redis: {
    enabled: process.env.REDIS_ENABLED === 'true',
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT) || 6379,
    password: process.env.REDIS_PASSWORD || '',
    db: parseInt(process.env.REDIS_DB) || 0,
    keyPrefix: process.env.REDIS_KEY_PREFIX || 'video-processor:'
  },
  
  monitoring: {
    enableMetrics: process.env.ENABLE_METRICS === 'true',
    metricsPort: parseInt(process.env.METRICS_PORT) || 9090,
    healthCheckInterval: parseInt(process.env.HEALTH_CHECK_INTERVAL) || 30000
  },
  
  cleanup: {
    tempFileRetention: parseInt(process.env.TEMP_FILE_RETENTION) || 86400000,
    outputFileRetention: parseInt(process.env.OUTPUT_FILE_RETENTION) || 604800000,
    cleanupInterval: parseInt(process.env.CLEANUP_INTERVAL) || 3600000
  }
};

function validateConfig() {
  const required = ['port', 'outputDir', 'tempDir'];
  const missing = required.filter(key => !config[key]);
  
  if (missing.length > 0) {
    throw new Error(`Missing required configuration: ${missing.join(', ')}`);
  }
  
  if (config.port < 1 || config.port > 65535) {
    throw new Error('Port must be between 1 and 65535');
  }
  
  if (config.maxConcurrentStreams < 1) {
    throw new Error('maxConcurrentStreams must be at least 1');
  }
  
  if (config.upload.maxFileSize < 1024 * 1024) {
    throw new Error('maxFileSize must be at least 1MB');
  }
}

try {
  validateConfig();
} catch (error) {
  console.error('Configuration validation failed:', error.message);
  process.exit(1);
}

module.exports = config;