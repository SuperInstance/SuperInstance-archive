const { EventEmitter } = require('events');
const crypto = require('crypto');

class CacheManager extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      // Cache storage backends
      backends: config.backends || ['memory', 'redis'],
      primaryBackend: config.primaryBackend || 'memory',
      fallbackBackend: config.fallbackBackend || 'redis',
      
      // Cache policies
      defaultTTL: config.defaultTTL || 3600, // 1 hour
      maxMemoryUsage: config.maxMemoryUsage || 100 * 1024 * 1024, // 100MB
      maxKeys: config.maxKeys || 10000,
      
      // Eviction policies
      evictionPolicy: config.evictionPolicy || 'lru', // lru, lfu, fifo, random
      evictionThreshold: config.evictionThreshold || 0.8, // 80%
      
      // Performance
      enableCompression: config.enableCompression ?? true,
      compressionThreshold: config.compressionThreshold || 1024, // 1KB
      enableStats: config.enableStats ?? true,
      
      // Advanced features
      enableTagging: config.enableTagging ?? true,
      enablePartitioning: config.enablePartitioning ?? false,
      enableReplication: config.enableReplication ?? false,
      
      ...config
    };

    this.backends = new Map();
    this.stats = {
      hits: 0,
      misses: 0,
      sets: 0,
      deletes: 0,
      evictions: 0,
      memory_usage: 0,
      key_count: 0
    };

    this.initializeBackends();
  }

  // Initialize cache backends
  initializeBackends() {
    // Memory backend (always available)
    this.backends.set('memory', new MemoryCacheBackend({
      maxSize: this.config.maxMemoryUsage,
      maxKeys: this.config.maxKeys,
      evictionPolicy: this.config.evictionPolicy
    }));

    // Redis backend (if configured)
    if (this.config.backends.includes('redis') && this.config.redis) {
      this.backends.set('redis', new RedisCacheBackend(this.config.redis));
    }

    // File system backend
    if (this.config.backends.includes('filesystem')) {
      this.backends.set('filesystem', new FileSystemCacheBackend(this.config.filesystem));
    }

    console.log(`Initialized ${this.backends.size} cache backends`);
  }

  // Get cache backend
  getBackend(name) {
    return this.backends.get(name || this.config.primaryBackend);
  }

  // Get value from cache
  async get(key, options = {}) {
    const startTime = Date.now();
    
    try {
      const backend = this.getBackend(options.backend);
      const result = await backend.get(key);
      
      if (result) {
        this.stats.hits++;
        this.emit('hit', { key, backend: backend.name, responseTime: Date.now() - startTime });
        
        // Deserialize if needed
        return this.deserialize(result);
      } else {
        this.stats.misses++;
        this.emit('miss', { key, backend: backend.name });
        
        // Try fallback backend
        if (options.useFallback !== false && this.config.fallbackBackend) {
          return await this.get(key, { ...options, backend: this.config.fallbackBackend, useFallback: false });
        }
        
        return null;
      }
    } catch (error) {
      this.emit('error', { operation: 'get', key, error });
      throw error;
    }
  }

  // Set value in cache
  async set(key, value, ttl, options = {}) {
    try {
      const serialized = await this.serialize(value);
      const actualTTL = ttl || this.config.defaultTTL;
      
      const backend = this.getBackend(options.backend);
      await backend.set(key, serialized, actualTTL, options);
      
      this.stats.sets++;
      this.stats.key_count++;
      
      this.emit('set', { key, ttl: actualTTL, backend: backend.name });
      
      // Replicate to other backends if enabled
      if (this.config.enableReplication) {
        await this.replicateToOtherBackends(key, serialized, actualTTL, backend.name);
      }
      
      return true;
    } catch (error) {
      this.emit('error', { operation: 'set', key, error });
      throw error;
    }
  }

  // Delete value from cache
  async delete(key, options = {}) {
    try {
      const backend = this.getBackend(options.backend);
      const deleted = await backend.delete(key);
      
      if (deleted) {
        this.stats.deletes++;
        this.stats.key_count--;
        this.emit('delete', { key, backend: backend.name });
      }
      
      return deleted;
    } catch (error) {
      this.emit('error', { operation: 'delete', key, error });
      throw error;
    }
  }

  // Clear all cache
  async clear(options = {}) {
    try {
      const backend = this.getBackend(options.backend);
      await backend.clear();
      
      this.stats.key_count = 0;
      this.emit('clear', { backend: backend.name });
      
      return true;
    } catch (error) {
      this.emit('error', { operation: 'clear', error });
      throw error;
    }
  }

  // Check if key exists
  async has(key, options = {}) {
    try {
      const backend = this.getBackend(options.backend);
      return await backend.has(key);
    } catch (error) {
      this.emit('error', { operation: 'has', key, error });
      throw error;
    }
  }

  // Get multiple keys
  async mget(keys, options = {}) {
    try {
      const backend = this.getBackend(options.backend);
      const results = await backend.mget(keys);
      
      const deserializedResults = {};
      for (const [key, value] of Object.entries(results)) {
        deserializedResults[key] = value ? this.deserialize(value) : null;
      }
      
      return deserializedResults;
    } catch (error) {
      this.emit('error', { operation: 'mget', keys, error });
      throw error;
    }
  }

  // Set multiple keys
  async mset(keyValuePairs, ttl, options = {}) {
    try {
      const backend = this.getBackend(options.backend);
      const serializedPairs = {};
      
      for (const [key, value] of Object.entries(keyValuePairs)) {
        serializedPairs[key] = await this.serialize(value);
      }
      
      const actualTTL = ttl || this.config.defaultTTL;
      await backend.mset(serializedPairs, actualTTL, options);
      
      this.stats.sets += Object.keys(keyValuePairs).length;
      this.stats.key_count += Object.keys(keyValuePairs).length;
      
      return true;
    } catch (error) {
      this.emit('error', { operation: 'mset', error });
      throw error;
    }
  }

  // Get with fallback function
  async getOrSet(key, fallbackFn, ttl, options = {}) {
    let value = await this.get(key, options);
    
    if (value === null) {
      value = await fallbackFn();
      await this.set(key, value, ttl, options);
    }
    
    return value;
  }

  // Increment counter
  async increment(key, amount = 1, options = {}) {
    try {
      const backend = this.getBackend(options.backend);
      return await backend.increment(key, amount);
    } catch (error) {
      this.emit('error', { operation: 'increment', key, error });
      throw error;
    }
  }

  // Decrement counter
  async decrement(key, amount = 1, options = {}) {
    try {
      const backend = this.getBackend(options.backend);
      return await backend.decrement(key, amount);
    } catch (error) {
      this.emit('error', { operation: 'decrement', key, error });
      throw error;
    }
  }

  // Tag-based cache operations
  async setWithTags(key, value, tags, ttl, options = {}) {
    if (!this.config.enableTagging) {
      return await this.set(key, value, ttl, options);
    }

    await this.set(key, value, ttl, options);
    
    // Store tag associations
    for (const tag of tags) {
      const tagKey = `tag:${tag}`;
      const taggedKeys = (await this.get(tagKey)) || new Set();
      taggedKeys.add(key);
      await this.set(tagKey, taggedKeys, ttl * 2); // Tags live longer
    }
    
    return true;
  }

  // Invalidate by tags
  async invalidateByTag(tag, options = {}) {
    if (!this.config.enableTagging) {
      return false;
    }

    const tagKey = `tag:${tag}`;
    const taggedKeys = await this.get(tagKey);
    
    if (taggedKeys && taggedKeys.size > 0) {
      const deletePromises = Array.from(taggedKeys).map(key => this.delete(key, options));
      await Promise.all(deletePromises);
      await this.delete(tagKey, options);
      
      this.emit('tagInvalidated', { tag, keysInvalidated: taggedKeys.size });
      return true;
    }
    
    return false;
  }

  // Cache warming
  async warm(warmingData, options = {}) {
    console.log(`Warming cache with ${Object.keys(warmingData).length} entries...`);
    
    const promises = Object.entries(warmingData).map(([key, { value, ttl, tags }]) => {
      if (tags) {
        return this.setWithTags(key, value, tags, ttl, options);
      } else {
        return this.set(key, value, ttl, options);
      }
    });
    
    const results = await Promise.allSettled(promises);
    const successful = results.filter(r => r.status === 'fulfilled').length;
    
    console.log(`Cache warming completed: ${successful}/${results.length} successful`);
    this.emit('warmed', { total: results.length, successful });
    
    return { total: results.length, successful };
  }

  // Cache serialization
  async serialize(value) {
    try {
      let serialized = JSON.stringify({
        type: typeof value,
        data: value,
        timestamp: Date.now()
      });

      // Compress if enabled and threshold met
      if (this.config.enableCompression && serialized.length > this.config.compressionThreshold) {
        const zlib = require('zlib');
        const compressed = zlib.gzipSync(serialized);
        return {
          compressed: true,
          data: compressed.toString('base64')
        };
      }

      return { compressed: false, data: serialized };
    } catch (error) {
      throw new Error(`Serialization failed: ${error.message}`);
    }
  }

  // Cache deserialization
  deserialize(serialized) {
    try {
      let data = serialized.data;

      // Decompress if needed
      if (serialized.compressed) {
        const zlib = require('zlib');
        const decompressed = zlib.gunzipSync(Buffer.from(data, 'base64'));
        data = decompressed.toString();
      }

      const parsed = JSON.parse(data);
      return parsed.data;
    } catch (error) {
      throw new Error(`Deserialization failed: ${error.message}`);
    }
  }

  // Replicate to other backends
  async replicateToOtherBackends(key, value, ttl, excludeBackend) {
    const replicationPromises = [];
    
    for (const [name, backend] of this.backends) {
      if (name !== excludeBackend) {
        replicationPromises.push(
          backend.set(key, value, ttl).catch(error => {
            console.warn(`Replication to ${name} failed:`, error.message);
          })
        );
      }
    }
    
    await Promise.all(replicationPromises);
  }

  // Generate cache key
  generateKey(prefix, ...parts) {
    const keyParts = [prefix, ...parts.map(part => 
      typeof part === 'object' ? JSON.stringify(part) : String(part)
    )];
    return keyParts.join(':');
  }

  // Hash for consistent key generation
  hash(input) {
    return crypto.createHash('md5').update(String(input)).digest('hex');
  }

  // Get cache statistics
  getStats() {
    const hitRate = this.stats.hits + this.stats.misses > 0 
      ? (this.stats.hits / (this.stats.hits + this.stats.misses) * 100).toFixed(2)
      : 0;

    return {
      ...this.stats,
      hit_rate: `${hitRate}%`,
      backends: Array.from(this.backends.keys()),
      memory_usage_mb: (this.stats.memory_usage / 1024 / 1024).toFixed(2)
    };
  }

  // Health check
  async healthCheck() {
    const results = {};
    
    for (const [name, backend] of this.backends) {
      try {
        const testKey = `health:${Date.now()}`;
        await backend.set(testKey, 'ok', 60);
        const value = await backend.get(testKey);
        await backend.delete(testKey);
        
        results[name] = {
          healthy: value === 'ok',
          responseTime: Date.now() - parseInt(testKey.split(':')[1])
        };
      } catch (error) {
        results[name] = {
          healthy: false,
          error: error.message
        };
      }
    }
    
    return results;
  }
}

// Memory cache backend
class MemoryCacheBackend {
  constructor(config = {}) {
    this.name = 'memory';
    this.config = config;
    this.cache = new Map();
    this.timers = new Map();
    this.accessOrder = new Map(); // For LRU
    this.accessCount = new Map(); // For LFU
    this.memoryUsage = 0;
  }

  async get(key) {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return null;
    }

    // Check expiration
    if (entry.expiresAt && Date.now() > entry.expiresAt) {
      this.delete(key);
      return null;
    }

    // Update access patterns
    this.updateAccessPatterns(key);
    
    return entry.value;
  }

  async set(key, value, ttl = 3600) {
    // Check if we need to evict
    if (this.shouldEvict()) {
      await this.evict();
    }

    const entry = {
      value,
      createdAt: Date.now(),
      expiresAt: ttl > 0 ? Date.now() + (ttl * 1000) : null,
      size: JSON.stringify(value).length
    };

    // Remove existing entry
    if (this.cache.has(key)) {
      const oldEntry = this.cache.get(key);
      this.memoryUsage -= oldEntry.size;
    }

    this.cache.set(key, entry);
    this.memoryUsage += entry.size;
    this.updateAccessPatterns(key);

    // Set expiration timer
    if (ttl > 0) {
      const timer = setTimeout(() => {
        this.delete(key);
      }, ttl * 1000);
      
      this.timers.set(key, timer);
    }

    return true;
  }

  async delete(key) {
    const entry = this.cache.get(key);
    if (!entry) {
      return false;
    }

    this.cache.delete(key);
    this.accessOrder.delete(key);
    this.accessCount.delete(key);
    this.memoryUsage -= entry.size;

    // Clear timer
    const timer = this.timers.get(key);
    if (timer) {
      clearTimeout(timer);
      this.timers.delete(key);
    }

    return true;
  }

  async clear() {
    this.cache.clear();
    this.accessOrder.clear();
    this.accessCount.clear();
    this.memoryUsage = 0;
    
    // Clear all timers
    for (const timer of this.timers.values()) {
      clearTimeout(timer);
    }
    this.timers.clear();
  }

  async has(key) {
    return this.cache.has(key);
  }

  async mget(keys) {
    const results = {};
    for (const key of keys) {
      results[key] = await this.get(key);
    }
    return results;
  }

  async mset(keyValuePairs, ttl) {
    for (const [key, value] of Object.entries(keyValuePairs)) {
      await this.set(key, value, ttl);
    }
  }

  async increment(key, amount = 1) {
    const current = await this.get(key) || 0;
    const newValue = Number(current) + amount;
    await this.set(key, newValue);
    return newValue;
  }

  async decrement(key, amount = 1) {
    return await this.increment(key, -amount);
  }

  // Update access patterns for eviction policies
  updateAccessPatterns(key) {
    // LRU: Update access order
    this.accessOrder.set(key, Date.now());
    
    // LFU: Update access count
    const count = this.accessCount.get(key) || 0;
    this.accessCount.set(key, count + 1);
  }

  // Check if eviction is needed
  shouldEvict() {
    return this.cache.size >= this.config.maxKeys || 
           this.memoryUsage >= this.config.maxSize;
  }

  // Evict entries based on policy
  async evict() {
    const evictCount = Math.ceil(this.cache.size * 0.1); // Evict 10%
    let keysToEvict = [];

    switch (this.config.evictionPolicy) {
      case 'lru':
        keysToEvict = this.getLRUKeys(evictCount);
        break;
      case 'lfu':
        keysToEvict = this.getLFUKeys(evictCount);
        break;
      case 'fifo':
        keysToEvict = this.getFIFOKeys(evictCount);
        break;
      case 'random':
        keysToEvict = this.getRandomKeys(evictCount);
        break;
      default:
        keysToEvict = this.getLRUKeys(evictCount);
    }

    for (const key of keysToEvict) {
      await this.delete(key);
    }
  }

  getLRUKeys(count) {
    const sorted = Array.from(this.accessOrder.entries())
      .sort((a, b) => a[1] - b[1]);
    return sorted.slice(0, count).map(([key]) => key);
  }

  getLFUKeys(count) {
    const sorted = Array.from(this.accessCount.entries())
      .sort((a, b) => a[1] - b[1]);
    return sorted.slice(0, count).map(([key]) => key);
  }

  getFIFOKeys(count) {
    const keys = Array.from(this.cache.keys());
    return keys.slice(0, count);
  }

  getRandomKeys(count) {
    const keys = Array.from(this.cache.keys());
    const shuffled = keys.sort(() => 0.5 - Math.random());
    return shuffled.slice(0, count);
  }
}

// Redis cache backend
class RedisCacheBackend {
  constructor(config) {
    this.name = 'redis';
    this.config = config;
    this.redis = require('redis').createClient(config);
  }

  async get(key) {
    return await this.redis.get(key);
  }

  async set(key, value, ttl = 3600) {
    if (ttl > 0) {
      await this.redis.setEx(key, ttl, value);
    } else {
      await this.redis.set(key, value);
    }
    return true;
  }

  async delete(key) {
    const result = await this.redis.del(key);
    return result > 0;
  }

  async clear() {
    await this.redis.flushDb();
  }

  async has(key) {
    const result = await this.redis.exists(key);
    return result > 0;
  }

  async mget(keys) {
    const values = await this.redis.mGet(keys);
    const results = {};
    keys.forEach((key, index) => {
      results[key] = values[index];
    });
    return results;
  }

  async mset(keyValuePairs, ttl) {
    const pipeline = this.redis.multi();
    
    for (const [key, value] of Object.entries(keyValuePairs)) {
      if (ttl > 0) {
        pipeline.setEx(key, ttl, value);
      } else {
        pipeline.set(key, value);
      }
    }
    
    await pipeline.exec();
  }

  async increment(key, amount = 1) {
    return await this.redis.incrBy(key, amount);
  }

  async decrement(key, amount = 1) {
    return await this.redis.decrBy(key, amount);
  }
}

// File system cache backend
class FileSystemCacheBackend {
  constructor(config = {}) {
    this.name = 'filesystem';
    this.config = { cacheDir: './cache', ...config };
    this.fs = require('fs');
    this.path = require('path');
    
    // Ensure cache directory exists
    if (!this.fs.existsSync(this.config.cacheDir)) {
      this.fs.mkdirSync(this.config.cacheDir, { recursive: true });
    }
  }

  getFilePath(key) {
    const hash = crypto.createHash('md5').update(key).digest('hex');
    return this.path.join(this.config.cacheDir, `${hash}.cache`);
  }

  async get(key) {
    const filePath = this.getFilePath(key);
    
    try {
      if (!this.fs.existsSync(filePath)) {
        return null;
      }

      const content = this.fs.readFileSync(filePath, 'utf8');
      const entry = JSON.parse(content);

      // Check expiration
      if (entry.expiresAt && Date.now() > entry.expiresAt) {
        this.fs.unlinkSync(filePath);
        return null;
      }

      return entry.value;
    } catch (error) {
      return null;
    }
  }

  async set(key, value, ttl = 3600) {
    const filePath = this.getFilePath(key);
    const entry = {
      value,
      createdAt: Date.now(),
      expiresAt: ttl > 0 ? Date.now() + (ttl * 1000) : null
    };

    try {
      this.fs.writeFileSync(filePath, JSON.stringify(entry));
      return true;
    } catch (error) {
      throw new Error(`Failed to write cache file: ${error.message}`);
    }
  }

  async delete(key) {
    const filePath = this.getFilePath(key);
    
    try {
      if (this.fs.existsSync(filePath)) {
        this.fs.unlinkSync(filePath);
        return true;
      }
      return false;
    } catch (error) {
      return false;
    }
  }

  async clear() {
    const files = this.fs.readdirSync(this.config.cacheDir);
    
    for (const file of files) {
      if (file.endsWith('.cache')) {
        this.fs.unlinkSync(this.path.join(this.config.cacheDir, file));
      }
    }
  }

  async has(key) {
    const filePath = this.getFilePath(key);
    return this.fs.existsSync(filePath);
  }

  async mget(keys) {
    const results = {};
    for (const key of keys) {
      results[key] = await this.get(key);
    }
    return results;
  }

  async mset(keyValuePairs, ttl) {
    for (const [key, value] of Object.entries(keyValuePairs)) {
      await this.set(key, value, ttl);
    }
  }

  async increment(key, amount = 1) {
    const current = await this.get(key) || 0;
    const newValue = Number(current) + amount;
    await this.set(key, newValue);
    return newValue;
  }

  async decrement(key, amount = 1) {
    return await this.increment(key, -amount);
  }
}

// Express middleware for automatic caching
function createCacheMiddleware(cacheManager, options = {}) {
  return (req, res, next) => {
    const originalSend = res.send;
    const cacheKey = options.keyGenerator 
      ? options.keyGenerator(req) 
      : `${req.method}:${req.originalUrl}`;

    // Check cache first
    cacheManager.get(cacheKey).then(cachedResponse => {
      if (cachedResponse && !options.skipCache) {
        res.set('X-Cache-Status', 'HIT');
        return res.send(cachedResponse);
      }

      // Override send to cache response
      res.send = function(body) {
        if (res.statusCode === 200) {
          cacheManager.set(cacheKey, body, options.ttl);
        }
        res.set('X-Cache-Status', 'MISS');
        originalSend.call(this, body);
      };

      next();
    }).catch(next);
  };
}

module.exports = {
  CacheManager,
  MemoryCacheBackend,
  RedisCacheBackend,
  FileSystemCacheBackend,
  createCacheMiddleware
};