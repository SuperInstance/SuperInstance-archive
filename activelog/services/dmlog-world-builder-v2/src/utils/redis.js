const Redis = require('redis');
const logger = require('./logger');

class RedisClient {
  constructor() {
    this.client = null;
    this.isConnected = false;
    this.retryAttempts = 0;
    this.maxRetryAttempts = 5;
  }

  async connect() {
    try {
      const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
      
      this.client = Redis.createClient({
        url: redisUrl,
        retryDelayOnFailover: 100,
        enableOfflineQueue: false,
        maxRetriesPerRequest: 3,
        retryDelayOnClusterDown: 300,
        socket: {
          connectTimeout: 5000,
          lazyConnect: true,
          reconnectDelay: 1000,
          keepAlive: true
        }
      });

      // Event handlers
      this.client.on('connect', () => {
        logger.info('Redis client connecting...');
      });

      this.client.on('ready', () => {
        logger.info('Redis client connected and ready');
        this.isConnected = true;
        this.retryAttempts = 0;
      });

      this.client.on('error', (err) => {
        logger.error('Redis client error:', err);
        this.isConnected = false;
        
        if (this.retryAttempts < this.maxRetryAttempts) {
          this.retryAttempts++;
          logger.info(`Attempting Redis reconnection (${this.retryAttempts}/${this.maxRetryAttempts})`);
        }
      });

      this.client.on('end', () => {
        logger.warn('Redis client connection ended');
        this.isConnected = false;
      });

      this.client.on('reconnecting', () => {
        logger.info('Redis client reconnecting...');
      });

      await this.client.connect();
      
      // Test connection
      await this.client.ping();
      
      return this.client;

    } catch (error) {
      logger.error('Failed to connect to Redis:', error);
      this.isConnected = false;
      
      // Don't throw error, allow service to run without Redis
      return null;
    }
  }

  async disconnect() {
    if (this.client && this.isConnected) {
      await this.client.quit();
      this.isConnected = false;
      logger.info('Redis client disconnected');
    }
  }

  // Cache operations
  async get(key) {
    if (!this.isConnected) return null;
    
    try {
      const value = await this.client.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      logger.error('Redis GET error:', error);
      return null;
    }
  }

  async set(key, value, ttl = 3600) {
    if (!this.isConnected) return false;
    
    try {
      const serialized = JSON.stringify(value);
      if (ttl > 0) {
        await this.client.setEx(key, ttl, serialized);
      } else {
        await this.client.set(key, serialized);
      }
      return true;
    } catch (error) {
      logger.error('Redis SET error:', error);
      return false;
    }
  }

  async del(key) {
    if (!this.isConnected) return false;
    
    try {
      await this.client.del(key);
      return true;
    } catch (error) {
      logger.error('Redis DEL error:', error);
      return false;
    }
  }

  async exists(key) {
    if (!this.isConnected) return false;
    
    try {
      const exists = await this.client.exists(key);
      return exists === 1;
    } catch (error) {
      logger.error('Redis EXISTS error:', error);
      return false;
    }
  }

  async expire(key, ttl) {
    if (!this.isConnected) return false;
    
    try {
      await this.client.expire(key, ttl);
      return true;
    } catch (error) {
      logger.error('Redis EXPIRE error:', error);
      return false;
    }
  }

  // Hash operations
  async hget(key, field) {
    if (!this.isConnected) return null;
    
    try {
      const value = await this.client.hGet(key, field);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      logger.error('Redis HGET error:', error);
      return null;
    }
  }

  async hset(key, field, value, ttl = 3600) {
    if (!this.isConnected) return false;
    
    try {
      const serialized = JSON.stringify(value);
      await this.client.hSet(key, field, serialized);
      
      if (ttl > 0) {
        await this.client.expire(key, ttl);
      }
      
      return true;
    } catch (error) {
      logger.error('Redis HSET error:', error);
      return false;
    }
  }

  async hgetall(key) {
    if (!this.isConnected) return {};
    
    try {
      const hash = await this.client.hGetAll(key);
      const result = {};
      
      for (const [field, value] of Object.entries(hash)) {
        try {
          result[field] = JSON.parse(value);
        } catch (e) {
          result[field] = value;
        }
      }
      
      return result;
    } catch (error) {
      logger.error('Redis HGETALL error:', error);
      return {};
    }
  }

  async hdel(key, field) {
    if (!this.isConnected) return false;
    
    try {
      await this.client.hDel(key, field);
      return true;
    } catch (error) {
      logger.error('Redis HDEL error:', error);
      return false;
    }
  }

  // List operations
  async lpush(key, value) {
    if (!this.isConnected) return false;
    
    try {
      const serialized = JSON.stringify(value);
      await this.client.lPush(key, serialized);
      return true;
    } catch (error) {
      logger.error('Redis LPUSH error:', error);
      return false;
    }
  }

  async rpush(key, value) {
    if (!this.isConnected) return false;
    
    try {
      const serialized = JSON.stringify(value);
      await this.client.rPush(key, serialized);
      return true;
    } catch (error) {
      logger.error('Redis RPUSH error:', error);
      return false;
    }
  }

  async lpop(key) {
    if (!this.isConnected) return null;
    
    try {
      const value = await this.client.lPop(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      logger.error('Redis LPOP error:', error);
      return null;
    }
  }

  async rpop(key) {
    if (!this.isConnected) return null;
    
    try {
      const value = await this.client.rPop(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      logger.error('Redis RPOP error:', error);
      return null;
    }
  }

  async lrange(key, start = 0, end = -1) {
    if (!this.isConnected) return [];
    
    try {
      const values = await this.client.lRange(key, start, end);
      return values.map(value => {
        try {
          return JSON.parse(value);
        } catch (e) {
          return value;
        }
      });
    } catch (error) {
      logger.error('Redis LRANGE error:', error);
      return [];
    }
  }

  // Set operations
  async sadd(key, member) {
    if (!this.isConnected) return false;
    
    try {
      const serialized = JSON.stringify(member);
      await this.client.sAdd(key, serialized);
      return true;
    } catch (error) {
      logger.error('Redis SADD error:', error);
      return false;
    }
  }

  async srem(key, member) {
    if (!this.isConnected) return false;
    
    try {
      const serialized = JSON.stringify(member);
      await this.client.sRem(key, serialized);
      return true;
    } catch (error) {
      logger.error('Redis SREM error:', error);
      return false;
    }
  }

  async smembers(key) {
    if (!this.isConnected) return [];
    
    try {
      const members = await this.client.sMembers(key);
      return members.map(member => {
        try {
          return JSON.parse(member);
        } catch (e) {
          return member;
        }
      });
    } catch (error) {
      logger.error('Redis SMEMBERS error:', error);
      return [];
    }
  }

  async sismember(key, member) {
    if (!this.isConnected) return false;
    
    try {
      const serialized = JSON.stringify(member);
      const exists = await this.client.sIsMember(key, serialized);
      return exists;
    } catch (error) {
      logger.error('Redis SISMEMBER error:', error);
      return false;
    }
  }

  // Pub/Sub operations
  async publish(channel, message) {
    if (!this.isConnected) return false;
    
    try {
      const serialized = JSON.stringify(message);
      await this.client.publish(channel, serialized);
      return true;
    } catch (error) {
      logger.error('Redis PUBLISH error:', error);
      return false;
    }
  }

  async subscribe(channel, callback) {
    if (!this.isConnected) return false;
    
    try {
      const subscriber = this.client.duplicate();
      await subscriber.connect();
      
      await subscriber.subscribe(channel, (message) => {
        try {
          const parsed = JSON.parse(message);
          callback(parsed);
        } catch (e) {
          callback(message);
        }
      });
      
      return subscriber;
    } catch (error) {
      logger.error('Redis SUBSCRIBE error:', error);
      return false;
    }
  }

  // Session operations
  async setSession(sessionId, sessionData, ttl = 86400) {
    return await this.set(`session:${sessionId}`, sessionData, ttl);
  }

  async getSession(sessionId) {
    return await this.get(`session:${sessionId}`);
  }

  async deleteSession(sessionId) {
    return await this.del(`session:${sessionId}`);
  }

  // Cache world data
  async cacheWorld(worldId, worldData, ttl = 3600) {
    return await this.set(`world:${worldId}`, worldData, ttl);
  }

  async getCachedWorld(worldId) {
    return await this.get(`world:${worldId}`);
  }

  async invalidateWorldCache(worldId) {
    return await this.del(`world:${worldId}`);
  }

  // Collaboration tracking
  async addCollaborator(worldId, userId, userData) {
    return await this.hset(`collaborators:${worldId}`, userId, userData, 7200); // 2 hours
  }

  async removeCollaborator(worldId, userId) {
    return await this.hdel(`collaborators:${worldId}`, userId);
  }

  async getCollaborators(worldId) {
    return await this.hgetall(`collaborators:${worldId}`);
  }

  // Rate limiting
  async incrementRateLimit(key, window = 900) { // 15 minutes default
    if (!this.isConnected) return { count: 1, ttl: window };
    
    try {
      const current = await this.client.incr(key);
      
      if (current === 1) {
        await this.client.expire(key, window);
      }
      
      const ttl = await this.client.ttl(key);
      
      return { count: current, ttl: ttl };
    } catch (error) {
      logger.error('Redis rate limit error:', error);
      return { count: 1, ttl: window };
    }
  }

  // Health check
  async healthCheck() {
    if (!this.isConnected) return false;
    
    try {
      const result = await this.client.ping();
      return result === 'PONG';
    } catch (error) {
      logger.error('Redis health check failed:', error);
      return false;
    }
  }

  // Get Redis info
  async getInfo() {
    if (!this.isConnected) return null;
    
    try {
      return {
        connected: this.isConnected,
        retryAttempts: this.retryAttempts,
        maxRetryAttempts: this.maxRetryAttempts,
        serverInfo: await this.client.info()
      };
    } catch (error) {
      logger.error('Redis info error:', error);
      return null;
    }
  }
}

// Create singleton instance
const redisClient = new RedisClient();

// Initialize Redis connection
async function initializeRedis() {
  try {
    await redisClient.connect();
    return redisClient;
  } catch (error) {
    logger.error('Failed to initialize Redis:', error);
    return null;
  }
}

module.exports = {
  redisClient,
  initializeRedis
};