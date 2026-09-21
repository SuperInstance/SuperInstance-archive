import dotenv from 'dotenv';

dotenv.config();

const config = {
  // Server configuration
  server: {
    port: process.env.PORT || 8318,
    env: process.env.NODE_ENV || 'development',
    cors: {
      origins: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000']
    }
  },

  // Database configuration
  database: {
    mongodb: {
      uri: process.env.MONGODB_URI || 'mongodb://localhost:27017/reallog-pro',
      options: {
        useNewUrlParser: true,
        useUnifiedTopology: true,
        maxPoolSize: 10,
        serverSelectionTimeoutMS: 5000,
        socketTimeoutMS: 45000
      }
    },
    redis: {
      host: process.env.REDIS_HOST || 'localhost',
      port: process.env.REDIS_PORT || 6379,
      password: process.env.REDIS_PASSWORD || undefined,
      db: process.env.REDIS_DB || 0
    }
  },

  // Authentication
  auth: {
    jwtSecret: process.env.JWT_SECRET || 'reallog-pro-jwt-secret',
    jwtExpiresIn: process.env.JWT_EXPIRES_IN || '24h',
    sessionSecret: process.env.SESSION_SECRET || 'reallog-pro-session-secret',
    bcryptRounds: 12
  },

  // Social media platform API configurations
  socialMedia: {
    instagram: {
      clientId: process.env.INSTAGRAM_CLIENT_ID,
      clientSecret: process.env.INSTAGRAM_CLIENT_SECRET,
      redirectUri: process.env.INSTAGRAM_REDIRECT_URI
    },
    twitter: {
      apiKey: process.env.TWITTER_API_KEY,
      apiSecret: process.env.TWITTER_API_SECRET,
      accessToken: process.env.TWITTER_ACCESS_TOKEN,
      accessTokenSecret: process.env.TWITTER_ACCESS_TOKEN_SECRET
    },
    facebook: {
      appId: process.env.FACEBOOK_APP_ID,
      appSecret: process.env.FACEBOOK_APP_SECRET,
      accessToken: process.env.FACEBOOK_ACCESS_TOKEN
    },
    youtube: {
      clientId: process.env.YOUTUBE_CLIENT_ID,
      clientSecret: process.env.YOUTUBE_CLIENT_SECRET,
      apiKey: process.env.YOUTUBE_API_KEY
    },
    tiktok: {
      clientId: process.env.TIKTOK_CLIENT_ID,
      clientSecret: process.env.TIKTOK_CLIENT_SECRET
    },
    linkedin: {
      clientId: process.env.LINKEDIN_CLIENT_ID,
      clientSecret: process.env.LINKEDIN_CLIENT_SECRET
    },
    pinterest: {
      clientId: process.env.PINTEREST_CLIENT_ID,
      clientSecret: process.env.PINTEREST_CLIENT_SECRET
    },
    twitch: {
      clientId: process.env.TWITCH_CLIENT_ID,
      clientSecret: process.env.TWITCH_CLIENT_SECRET
    },
    discord: {
      token: process.env.DISCORD_BOT_TOKEN,
      clientId: process.env.DISCORD_CLIENT_ID
    },
    telegram: {
      botToken: process.env.TELEGRAM_BOT_TOKEN
    },
    snapchat: {
      clientId: process.env.SNAPCHAT_CLIENT_ID,
      clientSecret: process.env.SNAPCHAT_CLIENT_SECRET
    },
    reddit: {
      clientId: process.env.REDDIT_CLIENT_ID,
      clientSecret: process.env.REDDIT_CLIENT_SECRET,
      username: process.env.REDDIT_USERNAME,
      password: process.env.REDDIT_PASSWORD
    }
  },

  // AI services for content generation and analysis
  ai: {
    openai: {
      apiKey: process.env.OPENAI_API_KEY,
      model: process.env.OPENAI_MODEL || 'gpt-4',
      maxTokens: 4000
    },
    anthropic: {
      apiKey: process.env.ANTHROPIC_API_KEY,
      model: process.env.ANTHROPIC_MODEL || 'claude-3-sonnet-20240229'
    },
    google: {
      apiKey: process.env.GOOGLE_AI_API_KEY,
      model: process.env.GOOGLE_AI_MODEL || 'gemini-pro'
    }
  },

  // Cloud storage for video hosting
  storage: {
    aws: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      region: process.env.AWS_REGION || 'us-east-1',
      s3Bucket: process.env.AWS_S3_BUCKET
    },
    googleCloud: {
      projectId: process.env.GOOGLE_CLOUD_PROJECT_ID,
      keyFilename: process.env.GOOGLE_CLOUD_KEY_FILE,
      bucket: process.env.GOOGLE_CLOUD_BUCKET
    },
    azure: {
      accountName: process.env.AZURE_STORAGE_ACCOUNT,
      accountKey: process.env.AZURE_STORAGE_KEY,
      containerName: process.env.AZURE_CONTAINER_NAME
    }
  },

  // Payment processing
  payments: {
    stripe: {
      publishableKey: process.env.STRIPE_PUBLISHABLE_KEY,
      secretKey: process.env.STRIPE_SECRET_KEY,
      webhookSecret: process.env.STRIPE_WEBHOOK_SECRET
    },
    paypal: {
      clientId: process.env.PAYPAL_CLIENT_ID,
      clientSecret: process.env.PAYPAL_CLIENT_SECRET,
      mode: process.env.PAYPAL_MODE || 'sandbox'
    }
  },

  // Email and SMS services
  notifications: {
    email: {
      service: process.env.EMAIL_SERVICE || 'gmail',
      user: process.env.EMAIL_USER,
      password: process.env.EMAIL_PASSWORD,
      from: process.env.EMAIL_FROM
    },
    sms: {
      twilio: {
        accountSid: process.env.TWILIO_ACCOUNT_SID,
        authToken: process.env.TWILIO_AUTH_TOKEN,
        fromNumber: process.env.TWILIO_FROM_NUMBER
      }
    }
  },

  // Rate limiting
  rateLimiting: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 1000, // limit each IP to 1000 requests per windowMs
    message: 'Too many requests from this IP, please try again later.'
  },

  // File upload limits
  uploads: {
    maxFileSize: 100 * 1024 * 1024, // 100MB
    allowedTypes: {
      images: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
      videos: ['video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/flv'],
      documents: ['application/pdf', 'text/plain', 'application/msword']
    }
  },

  // Content moderation
  moderation: {
    enableAutoModeration: process.env.ENABLE_AUTO_MODERATION === 'true',
    toxicityThreshold: parseFloat(process.env.TOXICITY_THRESHOLD) || 0.7,
    spamThreshold: parseFloat(process.env.SPAM_THRESHOLD) || 0.8
  },

  // Analytics
  analytics: {
    googleAnalytics: {
      trackingId: process.env.GOOGLE_ANALYTICS_TRACKING_ID
    },
    mixpanel: {
      token: process.env.MIXPANEL_TOKEN
    }
  },

  // Feature flags
  features: {
    enableVideoHosting: process.env.ENABLE_VIDEO_HOSTING === 'true',
    enableCollaborationMarketplace: process.env.ENABLE_COLLABORATION_MARKETPLACE === 'true',
    enableBrandPartnerships: process.env.ENABLE_BRAND_PARTNERSHIPS === 'true',
    enableAffiliateTracking: process.env.ENABLE_AFFILIATE_TRACKING === 'true',
    enableAutomatedResponses: process.env.ENABLE_AUTOMATED_RESPONSES === 'true',
    enableExposureOptimization: process.env.ENABLE_EXPOSURE_OPTIMIZATION === 'true'
  },

  // Automation settings
  automation: {
    maxDailyPosts: parseInt(process.env.MAX_DAILY_POSTS) || 10,
    maxHourlyComments: parseInt(process.env.MAX_HOURLY_COMMENTS) || 30,
    responseDelayMin: parseInt(process.env.RESPONSE_DELAY_MIN) || 5, // minutes
    responseDelayMax: parseInt(process.env.RESPONSE_DELAY_MAX) || 60, // minutes
    enableSmartScheduling: process.env.ENABLE_SMART_SCHEDULING === 'true'
  },

  // Video processing
  video: {
    ffmpegPath: process.env.FFMPEG_PATH || 'ffmpeg',
    maxVideoDuration: parseInt(process.env.MAX_VIDEO_DURATION) || 3600, // seconds
    defaultQuality: process.env.DEFAULT_VIDEO_QUALITY || '720p',
    enableTranscoding: process.env.ENABLE_VIDEO_TRANSCODING === 'true'
  },

  // Affiliate tracking
  affiliate: {
    cookieExpiration: parseInt(process.env.AFFILIATE_COOKIE_EXPIRATION) || 30, // days
    commissionRate: parseFloat(process.env.DEFAULT_COMMISSION_RATE) || 0.05,
    minimumPayout: parseFloat(process.env.MINIMUM_PAYOUT) || 50.00
  },

  // Brand partnerships
  partnerships: {
    minimumFollowers: parseInt(process.env.MINIMUM_FOLLOWERS_FOR_PARTNERSHIPS) || 1000,
    verificationRequired: process.env.PARTNERSHIP_VERIFICATION_REQUIRED === 'true'
  }
};

export default config;