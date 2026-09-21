try {
  require('dotenv').config();
} catch (error) {
  // dotenv not available, using environment variables directly
}

module.exports = {
  port: process.env.PORT || 8315,
  nodeEnv: process.env.NODE_ENV || 'development',
  
  // Database Configuration
  mongodb: {
    uri: process.env.MONGODB_URI || 'mongodb://localhost:27017/dmlog-visualizer',
    options: {
      useNewUrlParser: true,
      useUnifiedTopology: true
    }
  },
  
  // Redis Configuration
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: process.env.REDIS_PORT || 6379,
    password: process.env.REDIS_PASSWORD || null,
    db: process.env.REDIS_DB || 1
  },
  
  // JWT Configuration
  jwt: {
    secret: process.env.JWT_SECRET || 'dmlog-visualizer-jwt-secret-key-change-in-production',
    expiresIn: process.env.JWT_EXPIRES_IN || '24h'
  },
  
  // API Keys
  openai: {
    apiKey: process.env.OPENAI_API_KEY || null,
    model: process.env.OPENAI_MODEL || 'gpt-4'
  },
  
  googleCloud: {
    speechApiKey: process.env.GOOGLE_CLOUD_SPEECH_API_KEY || null,
    ttsApiKey: process.env.GOOGLE_CLOUD_TTS_API_KEY || null,
    credentials: process.env.GOOGLE_APPLICATION_CREDENTIALS || null
  },
  
  azure: {
    speechKey: process.env.AZURE_SPEECH_KEY || null,
    speechRegion: process.env.AZURE_SPEECH_REGION || 'eastus'
  },
  
  aws: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID || null,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || null,
    region: process.env.AWS_REGION || 'us-east-1'
  },
  
  // Engine Paths
  engines: {
    unrealPath: process.env.UNREAL_ENGINE_PATH || '/UnrealEngine',
    unityPath: process.env.UNITY_PATH || '/Applications/Unity/Hub/Editor/2023.3.0f1/Unity.app/Contents/MacOS/Unity'
  },
  
  // Rendering Configuration
  rendering: {
    outputPath: process.env.RENDER_OUTPUT_PATH || './renders',
    tempPath: process.env.TEMP_PATH || './temp',
    maxConcurrentRenders: parseInt(process.env.MAX_CONCURRENT_RENDERS) || 3,
    defaultResolution: {
      width: parseInt(process.env.DEFAULT_WIDTH) || 1920,
      height: parseInt(process.env.DEFAULT_HEIGHT) || 1080
    }
  },
  
  // Audio Configuration
  audio: {
    sampleRate: parseInt(process.env.AUDIO_SAMPLE_RATE) || 16000,
    channels: parseInt(process.env.AUDIO_CHANNELS) || 1,
    bufferSize: parseInt(process.env.AUDIO_BUFFER_SIZE) || 4096
  },
  
  // Streaming Configuration
  streaming: {
    youtube: {
      apiKey: process.env.YOUTUBE_API_KEY || null,
      clientId: process.env.YOUTUBE_CLIENT_ID || null,
      clientSecret: process.env.YOUTUBE_CLIENT_SECRET || null
    },
    twitch: {
      clientId: process.env.TWITCH_CLIENT_ID || null,
      clientSecret: process.env.TWITCH_CLIENT_SECRET || null
    }
  },
  
  // Logging Configuration
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: process.env.LOG_FILE || 'logs/dmlog-visualizer.log',
    maxFiles: parseInt(process.env.LOG_MAX_FILES) || 5,
    maxSize: process.env.LOG_MAX_SIZE || '10m'
  },
  
  // Rate Limiting
  rateLimiting: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW) || 15 * 60 * 1000,
    maxRequests: parseInt(process.env.RATE_LIMIT_MAX) || 100
  },
  
  // CORS Configuration
  cors: {
    origins: process.env.CORS_ORIGINS ? process.env.CORS_ORIGINS.split(',') : ['http://localhost:3000', 'http://localhost:8080'],
    credentials: true
  },
  
  // File Upload Configuration
  upload: {
    maxFileSize: parseInt(process.env.MAX_FILE_SIZE) || 100 * 1024 * 1024, // 100MB
    allowedTypes: ['image/png', 'image/jpeg', 'audio/wav', 'audio/mp3', 'video/mp4']
  }
};