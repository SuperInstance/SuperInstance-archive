const redis = require('redis');
const logger = require('./logger');

class RedisConfig {
  constructor() {
    this.client = null;
    this.subscriber = null;
    this.publisher = null;
    this.isConnected = false;
  }

  async connect() {
    try {
      const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
      
      const config = {
        url: redisUrl,
        retry_unfulfilled_commands: true,
        retry_delay_on_cluster_down: 300,
        retry_delay_on_failover: 100,
        max_attempts: 3,
        connect_timeout: 60000,
        lazyConnect: true
      };

      // Main client for general operations
      this.client = redis.createClient(config);
      
      // Separate clients for pub/sub
      this.subscriber = redis.createClient(config);
      this.publisher = redis.createClient(config);

      // Setup error handlers
      this.client.on('error', (err) => {
        logger.error('Redis client error:', err);
        this.isConnected = false;
      });

      this.client.on('connect', () => {
        logger.info('Redis client connected');
        this.isConnected = true;
      });

      this.client.on('ready', () => {
        logger.info('Redis client ready');
      });

      this.client.on('end', () => {
        logger.warn('Redis client connection ended');
        this.isConnected = false;
      });

      // Connect all clients
      await Promise.all([
        this.client.connect(),
        this.subscriber.connect(),
        this.publisher.connect()
      ]);

      logger.info('Redis connections established successfully');
      return this.client;
    } catch (error) {
      logger.warn('Failed to connect to Redis, running without Redis:', error.message);
      this.isConnected = false;
      return null;
    }
  }

  async disconnect() {
    try {
      if (this.client) await this.client.quit();
      if (this.subscriber) await this.subscriber.quit();
      if (this.publisher) await this.publisher.quit();
      
      this.isConnected = false;
      logger.info('Redis connections closed');
    } catch (error) {
      logger.error('Error closing Redis connections:', error);
    }
  }

  async healthCheck() {
    try {
      if (!this.isConnected || !this.client) {
        return { status: 'disconnected', healthy: false };
      }

      const pong = await this.client.ping();
      const info = await this.client.info('server');
      
      return {
        status: 'connected',
        healthy: true,
        ping: pong,
        version: this.extractVersion(info)
      };
    } catch (error) {
      return {
        status: 'error',
        healthy: false,
        error: error.message
      };
    }
  }

  extractVersion(info) {
    const match = info.match(/redis_version:([^\r\n]+)/);
    return match ? match[1] : 'unknown';
  }

  // Cache operations
  async get(key) {
    try {
      return await this.client.get(key);
    } catch (error) {
      logger.error(`Redis GET error for key ${key}:`, error);
      throw error;
    }
  }

  async set(key, value, ttl = null) {
    try {
      if (ttl) {
        return await this.client.setEx(key, ttl, value);
      }
      return await this.client.set(key, value);
    } catch (error) {
      logger.error(`Redis SET error for key ${key}:`, error);
      throw error;
    }
  }

  async del(key) {
    try {
      return await this.client.del(key);
    } catch (error) {
      logger.error(`Redis DEL error for key ${key}:`, error);
      throw error;
    }
  }

  async exists(key) {
    try {
      return await this.client.exists(key);
    } catch (error) {
      logger.error(`Redis EXISTS error for key ${key}:`, error);
      throw error;
    }
  }

  // Hash operations
  async hget(key, field) {
    try {
      return await this.client.hGet(key, field);
    } catch (error) {
      logger.error(`Redis HGET error for key ${key}, field ${field}:`, error);
      throw error;
    }
  }

  async hset(key, field, value) {
    try {
      return await this.client.hSet(key, field, value);
    } catch (error) {
      logger.error(`Redis HSET error for key ${key}, field ${field}:`, error);
      throw error;
    }
  }

  async hgetall(key) {
    try {
      return await this.client.hGetAll(key);
    } catch (error) {
      logger.error(`Redis HGETALL error for key ${key}:`, error);
      throw error;
    }
  }

  // List operations
  async lpush(key, value) {
    try {
      return await this.client.lPush(key, value);
    } catch (error) {
      logger.error(`Redis LPUSH error for key ${key}:`, error);
      throw error;
    }
  }

  async rpop(key) {
    try {
      return await this.client.rPop(key);
    } catch (error) {
      logger.error(`Redis RPOP error for key ${key}:`, error);
      throw error;
    }
  }

  async llen(key) {
    try {
      return await this.client.lLen(key);
    } catch (error) {
      logger.error(`Redis LLEN error for key ${key}:`, error);
      throw error;
    }
  }

  // Pub/Sub operations
  async publish(channel, message) {
    try {
      return await this.publisher.publish(channel, JSON.stringify(message));
    } catch (error) {
      logger.error(`Redis PUBLISH error for channel ${channel}:`, error);
      throw error;
    }
  }

  async subscribe(channel, callback) {
    try {
      await this.subscriber.subscribe(channel, (message) => {
        try {
          const parsed = JSON.parse(message);
          callback(parsed);
        } catch (parseError) {
          logger.error('Error parsing Redis message:', parseError);
          callback(message);
        }
      });
    } catch (error) {
      logger.error(`Redis SUBSCRIBE error for channel ${channel}:`, error);
      throw error;
    }
  }

  // Set operations
  async sadd(key, member) {
    try {
      return await this.client.sAdd(key, member);
    } catch (error) {
      logger.error(`Redis SADD error for key ${key}:`, error);
      throw error;
    }
  }

  async srem(key, member) {
    try {
      return await this.client.sRem(key, member);
    } catch (error) {
      logger.error(`Redis SREM error for key ${key}:`, error);
      throw error;
    }
  }

  async smembers(key) {
    try {
      return await this.client.sMembers(key);
    } catch (error) {
      logger.error(`Redis SMEMBERS error for key ${key}:`, error);
      throw error;
    }
  }
}

module.exports = new RedisConfig();