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

  // Inventory caching
  async cacheInventoryItem(locationId, itemId, data, ttl = 3600) {
    try {
      const key = `inventory:${locationId}:${itemId}`;
      return await this.client.setEx(key, ttl, JSON.stringify(data));
    } catch (error) {
      logger.error(`Inventory cache error for ${locationId}:${itemId}:`, error);
      return null;
    }
  }

  async getInventoryItem(locationId, itemId) {
    try {
      const key = `inventory:${locationId}:${itemId}`;
      const data = await this.client.get(key);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      logger.error(`Inventory retrieval error for ${locationId}:${itemId}:`, error);
      return null;
    }
  }

  // Real-time inventory updates
  async publishInventoryUpdate(locationId, update) {
    try {
      const channel = `inventory_updates:${locationId}`;
      const message = {
        ...update,
        timestamp: new Date().toISOString()
      };
      return await this.publisher.publish(channel, JSON.stringify(message));
    } catch (error) {
      logger.error(`Inventory update publish error for ${locationId}:`, error);
      return null;
    }
  }

  async subscribeToInventoryUpdates(locationId, callback) {
    try {
      const channel = `inventory_updates:${locationId}`;
      await this.subscriber.subscribe(channel, (message) => {
        try {
          const parsed = JSON.parse(message);
          callback(parsed);
        } catch (parseError) {
          logger.error('Error parsing inventory update:', parseError);
          callback({ error: 'Parse error', raw: message });
        }
      });
    } catch (error) {
      logger.error(`Inventory subscription error for ${locationId}:`, error);
    }
  }

  // Reservation management
  async createReservation(reservationId, data, ttl) {
    try {
      const key = `reservation:${reservationId}`;
      return await this.client.setEx(key, ttl, JSON.stringify(data));
    } catch (error) {
      logger.error(`Reservation creation error ${reservationId}:`, error);
      return null;
    }
  }

  async getReservation(reservationId) {
    try {
      const key = `reservation:${reservationId}`;
      const data = await this.client.get(key);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      logger.error(`Reservation retrieval error ${reservationId}:`, error);
      return null;
    }
  }

  async deleteReservation(reservationId) {
    try {
      const key = `reservation:${reservationId}`;
      return await this.client.del(key);
    } catch (error) {
      logger.error(`Reservation deletion error ${reservationId}:`, error);
      return null;
    }
  }

  // Location sync
  async syncLocationData(locationId, data) {
    try {
      const key = `location_sync:${locationId}`;
      return await this.client.hSet(key, data);
    } catch (error) {
      logger.error(`Location sync error for ${locationId}:`, error);
      return null;
    }
  }

  async getLocationData(locationId) {
    try {
      const key = `location_sync:${locationId}`;
      return await this.client.hGetAll(key);
    } catch (error) {
      logger.error(`Location data retrieval error for ${locationId}:`, error);
      return {};
    }
  }

  // Price optimization cache
  async cachePriceAnalysis(itemId, analysis, ttl = 86400) {
    try {
      const key = `price_analysis:${itemId}`;
      return await this.client.setEx(key, ttl, JSON.stringify(analysis));
    } catch (error) {
      logger.error(`Price analysis cache error for ${itemId}:`, error);
      return null;
    }
  }

  async getPriceAnalysis(itemId) {
    try {
      const key = `price_analysis:${itemId}`;
      const data = await this.client.get(key);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      logger.error(`Price analysis retrieval error for ${itemId}:`, error);
      return null;
    }
  }

  // Pickup scheduling
  async cachePickupSlots(locationId, date, slots) {
    try {
      const key = `pickup_slots:${locationId}:${date}`;
      return await this.client.setEx(key, 3600, JSON.stringify(slots)); // 1 hour TTL
    } catch (error) {
      logger.error(`Pickup slots cache error for ${locationId}:${date}:`, error);
      return null;
    }
  }

  async getPickupSlots(locationId, date) {
    try {
      const key = `pickup_slots:${locationId}:${date}`;
      const data = await this.client.get(key);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      logger.error(`Pickup slots retrieval error for ${locationId}:${date}:`, error);
      return null;
    }
  }

  // POS integration cache
  async cachePOSTransaction(transactionId, data, ttl = 86400) {
    try {
      const key = `pos_transaction:${transactionId}`;
      return await this.client.setEx(key, ttl, JSON.stringify(data));
    } catch (error) {
      logger.error(`POS transaction cache error ${transactionId}:`, error);
      return null;
    }
  }

  async getPOSTransaction(transactionId) {
    try {
      const key = `pos_transaction:${transactionId}`;
      const data = await this.client.get(key);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      logger.error(`POS transaction retrieval error ${transactionId}:`, error);
      return null;
    }
  }

  // Supply chain tracking
  async cacheSupplyChainEvent(eventId, data, ttl = 86400) {
    try {
      const key = `supply_chain:${eventId}`;
      return await this.client.setEx(key, ttl, JSON.stringify(data));
    } catch (error) {
      logger.error(`Supply chain cache error ${eventId}:`, error);
      return null;
    }
  }

  // Reorder automation
  async setReorderFlag(itemId, locationId, priority = 'normal') {
    try {
      const key = `reorder_queue`;
      const data = { itemId, locationId, priority, timestamp: Date.now() };
      return await this.client.lPush(key, JSON.stringify(data));
    } catch (error) {
      logger.error(`Reorder flag error for ${itemId}:${locationId}:`, error);
      return null;
    }
  }

  async getReorderQueue(limit = 100) {
    try {
      const key = `reorder_queue`;
      const items = await this.client.lRange(key, 0, limit - 1);
      return items.map(item => JSON.parse(item));
    } catch (error) {
      logger.error('Reorder queue retrieval error:', error);
      return [];
    }
  }
}

module.exports = new RedisConfig();