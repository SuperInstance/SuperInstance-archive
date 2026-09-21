const EventEmitter = require('events');

class DatabaseConnectionPool extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      min: config.min || 2,
      max: config.max || 20,
      acquireTimeoutMillis: config.acquireTimeoutMillis || 30000,
      createTimeoutMillis: config.createTimeoutMillis || 30000,
      destroyTimeoutMillis: config.destroyTimeoutMillis || 5000,
      idleTimeoutMillis: config.idleTimeoutMillis || 300000,
      reapIntervalMillis: config.reapIntervalMillis || 1000,
      createRetryIntervalMillis: config.createRetryIntervalMillis || 200,
      maxUses: config.maxUses || 1000, // Max uses per connection before refresh
      testOnBorrow: config.testOnBorrow ?? true,
      testOnReturn: config.testOnReturn ?? false,
      validateQuery: config.validateQuery || 'SELECT 1',
      ...config
    };

    this.pool = [];
    this.waitingQueue = [];
    this.connectionCount = 0;
    this.stats = {
      totalConnections: 0,
      activeConnections: 0,
      idleConnections: 0,
      waitingRequests: 0,
      acquiredCount: 0,
      releasedCount: 0,
      createdCount: 0,
      destroyedCount: 0,
      errors: 0
    };

    this.startReaper();
  }

  // Create a new database connection
  async createConnection() {
    try {
      const connection = await this.config.factory.create();
      
      const wrappedConnection = {
        raw: connection,
        id: `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        createdAt: new Date(),
        lastUsed: new Date(),
        usageCount: 0,
        isValid: true
      };

      this.stats.createdCount++;
      this.connectionCount++;
      
      this.emit('connectionCreated', wrappedConnection.id);
      
      return wrappedConnection;
    } catch (error) {
      this.stats.errors++;
      this.emit('error', error);
      throw error;
    }
  }

  // Destroy a database connection
  async destroyConnection(wrappedConnection) {
    try {
      if (this.config.factory.destroy) {
        await this.config.factory.destroy(wrappedConnection.raw);
      }
      
      this.connectionCount--;
      this.stats.destroyedCount++;
      
      this.emit('connectionDestroyed', wrappedConnection.id);
    } catch (error) {
      this.stats.errors++;
      this.emit('error', error);
    }
  }

  // Validate connection is still usable
  async validateConnection(wrappedConnection) {
    if (!this.config.testOnBorrow) return true;
    
    try {
      await wrappedConnection.raw.query(this.config.validateQuery);
      return true;
    } catch (error) {
      wrappedConnection.isValid = false;
      return false;
    }
  }

  // Acquire a connection from the pool
  async acquire() {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        // Remove from waiting queue
        const index = this.waitingQueue.findIndex(req => req.resolve === resolve);
        if (index !== -1) {
          this.waitingQueue.splice(index, 1);
          this.stats.waitingRequests = this.waitingQueue.length;
        }
        
        reject(new Error(`Connection acquisition timeout after ${this.config.acquireTimeoutMillis}ms`));
      }, this.config.acquireTimeoutMillis);

      this.waitingQueue.push({
        resolve: (connection) => {
          clearTimeout(timeout);
          resolve(connection);
        },
        reject: (error) => {
          clearTimeout(timeout);
          reject(error);
        },
        timestamp: Date.now()
      });

      this.stats.waitingRequests = this.waitingQueue.length;
      this.processWaitingQueue();
    });
  }

  // Process the waiting queue
  async processWaitingQueue() {
    while (this.waitingQueue.length > 0 && this.canAcquire()) {
      const request = this.waitingQueue.shift();
      this.stats.waitingRequests = this.waitingQueue.length;
      
      try {
        const connection = await this.getConnection();
        this.stats.acquiredCount++;
        request.resolve(connection);
      } catch (error) {
        this.stats.errors++;
        request.reject(error);
      }
    }
  }

  // Check if we can acquire a connection
  canAcquire() {
    const availableConnections = this.pool.filter(conn => conn.isAvailable).length;
    return availableConnections > 0 || this.connectionCount < this.config.max;
  }

  // Get a connection (from pool or create new)
  async getConnection() {
    // Try to get from pool first
    const availableConnection = this.pool.find(conn => conn.isAvailable && conn.isValid);
    
    if (availableConnection) {
      availableConnection.isAvailable = false;
      availableConnection.lastUsed = new Date();
      availableConnection.usageCount++;
      
      // Validate connection if required
      if (this.config.testOnBorrow) {
        const isValid = await this.validateConnection(availableConnection);
        if (!isValid) {
          // Remove invalid connection and try again
          this.removeConnection(availableConnection);
          return this.getConnection();
        }
      }
      
      this.updateStats();
      return availableConnection;
    }

    // Create new connection if under limit
    if (this.connectionCount < this.config.max) {
      const newConnection = await this.createConnection();
      newConnection.isAvailable = false;
      newConnection.usageCount = 1;
      
      this.pool.push(newConnection);
      this.updateStats();
      
      return newConnection;
    }

    throw new Error('No connections available and max limit reached');
  }

  // Release a connection back to the pool
  async release(wrappedConnection) {
    if (!wrappedConnection) return;

    try {
      // Test connection on return if configured
      if (this.config.testOnReturn) {
        const isValid = await this.validateConnection(wrappedConnection);
        if (!isValid) {
          this.removeConnection(wrappedConnection);
          this.stats.releasedCount++;
          this.updateStats();
          this.processWaitingQueue();
          return;
        }
      }

      // Check if connection should be retired
      if (wrappedConnection.usageCount >= this.config.maxUses) {
        this.removeConnection(wrappedConnection);
        this.stats.releasedCount++;
        this.updateStats();
        this.processWaitingQueue();
        return;
      }

      // Return to pool
      wrappedConnection.isAvailable = true;
      wrappedConnection.lastUsed = new Date();
      
      this.stats.releasedCount++;
      this.updateStats();
      
      // Process waiting queue
      this.processWaitingQueue();
      
    } catch (error) {
      this.stats.errors++;
      this.emit('error', error);
      this.removeConnection(wrappedConnection);
    }
  }

  // Remove connection from pool and destroy it
  async removeConnection(wrappedConnection) {
    const index = this.pool.indexOf(wrappedConnection);
    if (index !== -1) {
      this.pool.splice(index, 1);
    }
    
    await this.destroyConnection(wrappedConnection);
  }

  // Update connection statistics
  updateStats() {
    this.stats.totalConnections = this.pool.length;
    this.stats.activeConnections = this.pool.filter(conn => !conn.isAvailable).length;
    this.stats.idleConnections = this.pool.filter(conn => conn.isAvailable).length;
  }

  // Start the connection reaper (removes idle connections)
  startReaper() {
    this.reaperInterval = setInterval(() => {
      this.reapIdleConnections();
    }, this.config.reapIntervalMillis);
  }

  // Remove idle connections that have exceeded idle timeout
  async reapIdleConnections() {
    const now = Date.now();
    const connectionsToReap = this.pool.filter(conn => {
      return conn.isAvailable && 
             (now - conn.lastUsed.getTime()) > this.config.idleTimeoutMillis &&
             this.pool.length > this.config.min;
    });

    for (const connection of connectionsToReap) {
      await this.removeConnection(connection);
      this.emit('connectionReaped', connection.id);
    }

    if (connectionsToReap.length > 0) {
      this.updateStats();
    }
  }

  // Ensure minimum connections are maintained
  async ensureMinConnections() {
    while (this.pool.length < this.config.min && this.connectionCount < this.config.max) {
      try {
        const newConnection = await this.createConnection();
        newConnection.isAvailable = true;
        this.pool.push(newConnection);
      } catch (error) {
        this.emit('error', error);
        break;
      }
    }
    
    this.updateStats();
  }

  // Get pool status and statistics
  getStatus() {
    return {
      config: {
        min: this.config.min,
        max: this.config.max,
        acquireTimeout: this.config.acquireTimeoutMillis,
        idleTimeout: this.config.idleTimeoutMillis
      },
      stats: { ...this.stats },
      pool: {
        total: this.pool.length,
        available: this.pool.filter(conn => conn.isAvailable).length,
        busy: this.pool.filter(conn => !conn.isAvailable).length,
        waiting: this.waitingQueue.length
      }
    };
  }

  // Drain the pool (close all connections)
  async drain() {
    clearInterval(this.reaperInterval);
    
    // Wait for all connections to be released
    while (this.stats.activeConnections > 0) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    // Destroy all connections
    const connections = [...this.pool];
    for (const connection of connections) {
      await this.removeConnection(connection);
    }
    
    // Reject all waiting requests
    while (this.waitingQueue.length > 0) {
      const request = this.waitingQueue.shift();
      request.reject(new Error('Connection pool is draining'));
    }
    
    this.updateStats();
    this.emit('drained');
  }

  // Health check for the pool
  async healthCheck() {
    const status = this.getStatus();
    const issues = [];
    
    // Check for too many waiting requests
    if (status.pool.waiting > status.config.max * 0.5) {
      issues.push('High number of waiting connection requests');
    }
    
    // Check for low available connections
    if (status.pool.available === 0 && status.pool.total === status.config.max) {
      issues.push('All connections are busy and pool is at maximum capacity');
    }
    
    // Check error rate
    const errorRate = status.stats.errors / Math.max(status.stats.acquiredCount, 1);
    if (errorRate > 0.05) { // More than 5% error rate
      issues.push('High error rate in connection pool');
    }
    
    return {
      healthy: issues.length === 0,
      issues,
      status
    };
  }
}

// Factory for creating PostgreSQL connections
class PostgreSQLConnectionFactory {
  constructor(config) {
    this.config = config;
    this.pg = require('pg');
  }

  async create() {
    const client = new this.pg.Client(this.config);
    await client.connect();
    return client;
  }

  async destroy(connection) {
    await connection.end();
  }
}

// Factory for creating MySQL connections  
class MySQLConnectionFactory {
  constructor(config) {
    this.config = config;
    this.mysql = require('mysql2/promise');
  }

  async create() {
    return await this.mysql.createConnection(this.config);
  }

  async destroy(connection) {
    await connection.end();
  }
}

// Connection pool manager for multiple databases
class ConnectionPoolManager {
  constructor() {
    this.pools = new Map();
  }

  // Create a connection pool
  createPool(name, config) {
    if (this.pools.has(name)) {
      throw new Error(`Connection pool '${name}' already exists`);
    }

    const pool = new DatabaseConnectionPool(config);
    this.pools.set(name, pool);
    
    return pool;
  }

  // Get a connection pool by name
  getPool(name) {
    return this.pools.get(name);
  }

  // Get all pool statuses
  getAllStatuses() {
    const statuses = {};
    for (const [name, pool] of this.pools) {
      statuses[name] = pool.getStatus();
    }
    return statuses;
  }

  // Perform health check on all pools
  async healthCheckAll() {
    const results = {};
    for (const [name, pool] of this.pools) {
      results[name] = await pool.healthCheck();
    }
    return results;
  }

  // Drain all pools
  async drainAll() {
    const drainPromises = [];
    for (const pool of this.pools.values()) {
      drainPromises.push(pool.drain());
    }
    await Promise.all(drainPromises);
  }
}

module.exports = {
  DatabaseConnectionPool,
  ConnectionPoolManager,
  PostgreSQLConnectionFactory,
  MySQLConnectionFactory
};