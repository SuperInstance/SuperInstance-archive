const axios = require('axios');
const { MongoClient } = require('mongodb');
const Redis = require('redis');

// Global test utilities
global.testUtils = {
  // HTTP client with default configuration
  http: axios.create({
    timeout: 10000,
    validateStatus: false // Don't throw on HTTP error status
  }),

  // Database connections
  mongodb: null,
  redis: null,

  // Test data generators
  generateUser: (overrides = {}) => ({
    id: `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    email: `test-${Date.now()}@example.com`,
    firstName: 'Test',
    lastName: 'User',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides
  }),

  generateLogEntry: (overrides = {}) => ({
    id: `entry-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    title: 'Test Log Entry',
    content: 'This is a test log entry for integration testing.',
    category: 'personal',
    tags: ['test', 'integration'],
    priority: 'medium',
    status: 'published',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides
  }),

  generateProject: (overrides = {}) => ({
    id: `project-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    name: 'Test Project',
    description: 'Test project for integration testing',
    status: 'active',
    startDate: new Date().toISOString(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides
  }),

  // Wait utilities
  waitFor: (conditionFn, timeout = 10000, interval = 100) => {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      
      const check = async () => {
        try {
          const result = await conditionFn();
          if (result) {
            resolve(result);
            return;
          }
        } catch (error) {
          // Continue waiting
        }
        
        if (Date.now() - startTime > timeout) {
          reject(new Error(`Condition not met within ${timeout}ms`));
          return;
        }
        
        setTimeout(check, interval);
      };
      
      check();
    });
  },

  sleep: (ms) => new Promise(resolve => setTimeout(resolve, ms))
};

// Setup database connections
beforeAll(async () => {
  // Connect to MongoDB
  if (process.env.MONGODB_URL) {
    global.testUtils.mongodb = new MongoClient(process.env.MONGODB_URL);
    await global.testUtils.mongodb.connect();
    console.log('Connected to test MongoDB');
  }

  // Connect to Redis
  if (process.env.REDIS_URL) {
    global.testUtils.redis = Redis.createClient({
      url: process.env.REDIS_URL
    });
    await global.testUtils.redis.connect();
    console.log('Connected to test Redis');
  }
});

// Cleanup after all tests
afterAll(async () => {
  // Close database connections
  if (global.testUtils.mongodb) {
    await global.testUtils.mongodb.close();
    console.log('Disconnected from test MongoDB');
  }

  if (global.testUtils.redis) {
    await global.testUtils.redis.quit();
    console.log('Disconnected from test Redis');
  }
});

// Clean database between tests
beforeEach(async () => {
  // Clear MongoDB test data
  if (global.testUtils.mongodb) {
    const db = global.testUtils.mongodb.db();
    const collections = await db.listCollections().toArray();
    
    for (const collection of collections) {
      if (collection.name.startsWith('test_')) {
        await db.collection(collection.name).deleteMany({});
      }
    }
  }

  // Clear Redis test data
  if (global.testUtils.redis) {
    const keys = await global.testUtils.redis.keys('test:*');
    if (keys.length > 0) {
      await global.testUtils.redis.del(keys);
    }
  }
});

// Global error handling
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
});