const config = {
  // Server Configuration
  port: process.env.PORT || 8381,
  env: process.env.NODE_ENV || 'development',
  
  // Database Configuration
  mongodb: {
    uri: process.env.MONGODB_URI || 'mongodb://localhost:27017/activelog_ad_engine',
    options: {
      useNewUrlParser: true,
      useUnifiedTopology: true,
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000,
    }
  },
  
  // Redis Configuration
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: process.env.REDIS_PORT || 6379,
    password: process.env.REDIS_PASSWORD || null,
    db: process.env.REDIS_DB || 0
  },
  
  // JWT Configuration
  jwt: {
    secret: process.env.JWT_SECRET || 'ad-engine-secret-key-change-in-production',
    expiresIn: '24h'
  },
  
  // Ad Engine Configuration
  adEngine: {
    // Base compute costs (in CCC - Compute Currency Credits)
    computeCosts: {
      light: 1,    // Simple operations
      medium: 5,   // AI processing
      heavy: 15,   // Video processing
      extreme: 50  // Complex ML tasks
    },
    
    // Ad viewing rewards (CCC earned per ad)
    adRewards: {
      banner: 2,
      interstitial: 5,
      video: 10,
      rewarded: 15
    },
    
    // Usage-based ad frequency thresholds
    usageThresholds: {
      light: { daily: 10, weekly: 50 },      // Low usage users
      moderate: { daily: 50, weekly: 200 },   // Regular users  
      heavy: { daily: 200, weekly: 1000 },    // Power users
      extreme: { daily: 500, weekly: 2500 }   // Heavy users
    },
    
    // Ad frequency by user tier
    adFrequency: {
      light: { minInterval: 30, maxPerHour: 2 },      // 30 min between ads, max 2/hour
      moderate: { minInterval: 15, maxPerHour: 4 },    // 15 min between ads, max 4/hour
      heavy: { minInterval: 10, maxPerHour: 6 },       // 10 min between ads, max 6/hour
      extreme: { minInterval: 5, maxPerHour: 12 }      // 5 min between ads, max 12/hour
    },
    
    // Compute threshold for ad-free usage
    adFreeThresholds: {
      daily: 100,   // 100 CCC balance = no ads for light usage
      buffer: 20    // Keep 20 CCC buffer before showing ads
    },
    
    // Startup ad configuration
    startupAd: {
      enabled: true,
      frequency: 'daily', // 'always', 'daily', 'weekly'
      message: 'Watch a quick ad to support ActiveLog and earn compute credits!',
      skipAfter: 5, // seconds before skip button appears
      rewardAmount: 10 // CCC earned for watching
    },
    
    // Double banner configuration
    doubleBanner: {
      enabled: true,
      extraReward: 3, // Additional CCC for double banner
      maxPerDay: 10   // Maximum double banners per day
    }
  },
  
  // Review System Configuration
  reviewSystem: {
    // CCC rewards for different review types
    reviewRewards: {
      basic: 5,      // Simple star rating
      detailed: 15,  // Written review
      photo: 10,     // Review with photos
      video: 25      // Video review
    },
    
    // Reputation-based multipliers
    reputationMultipliers: {
      newcomer: 1.0,    // 0-10 reviews
      contributor: 1.2, // 11-50 reviews
      expert: 1.5,      // 51-200 reviews
      master: 2.0       // 200+ reviews
    },
    
    // Quality thresholds
    qualityThresholds: {
      minLength: 50,     // Minimum characters for detailed review
      maxDaily: 20,      // Maximum reviews per day
      cooldown: 3600     // 1 hour cooldown between reviews
    }
  },
  
  // Educational Participation
  education: {
    // Rewards for educational activities
    activityRewards: {
      quiz: 3,           // Complete a quiz
      tutorial: 5,       // Complete a tutorial
      lesson: 8,         // Complete a lesson
      course: 50,        // Complete a full course
      achievement: 15    // Unlock an achievement
    },
    
    // Bonus multipliers
    streakBonuses: {
      week: 1.2,   // 7-day streak
      month: 1.5,  // 30-day streak
      quarter: 2.0 // 90-day streak
    }
  },
  
  // Parent-Child System
  parentChild: {
    // Default allowances by age group
    defaultAllowances: {
      child: { daily: 20, weekly: 100 },      // Under 13
      teen: { daily: 50, weekly: 300 },       // 13-17
      young_adult: { daily: 100, weekly: 600 } // 18-21
    },
    
    // Spending approval thresholds
    approvalThresholds: {
      child: 10,      // Require approval for spending > 10 CCC
      teen: 25,       // Require approval for spending > 25 CCC
      young_adult: 50 // Require approval for spending > 50 CCC
    },
    
    // Parent notification settings
    notifications: {
      spending: true,
      earning: true,
      milestones: true,
      safety: true
    }
  },
  
  // Rate Limiting
  rateLimiting: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // limit each IP to 100 requests per windowMs
    message: 'Too many requests from this IP, please try again later.'
  },
  
  // Logging Configuration
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: process.env.LOG_FILE || 'logs/ad-engine.log'
  },
  
  // External Services
  externalServices: {
    // Mock ad providers for development
    adProviders: {
      primary: {
        name: 'AdMob',
        endpoint: 'https://api.admob.example.com',
        apiKey: process.env.ADMOB_API_KEY || 'mock-key'
      },
      secondary: {
        name: 'Facebook Audience Network',
        endpoint: 'https://api.facebook.com/ads',
        apiKey: process.env.FACEBOOK_API_KEY || 'mock-key'
      }
    },
    
    // Payment processors
    payments: {
      stripe: {
        publicKey: process.env.STRIPE_PUBLIC_KEY || 'pk_test_mock',
        secretKey: process.env.STRIPE_SECRET_KEY || 'sk_test_mock'
      }
    }
  }
};

module.exports = config;