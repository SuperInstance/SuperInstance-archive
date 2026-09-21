const zlib = require('zlib');
const { promisify } = require('util');
const crypto = require('crypto');
const { EventEmitter } = require('events');

// Promisify compression methods
const gzipAsync = promisify(zlib.gzip);
const deflateAsync = promisify(zlib.deflate);
const brotliCompressAsync = promisify(zlib.brotliCompress);

class ResponseCompressor extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      // Compression algorithms (in order of preference)
      algorithms: config.algorithms || ['br', 'gzip', 'deflate'],
      
      // Compression levels (0-11 for brotli, 0-9 for gzip/deflate)
      levels: {
        br: config.levels?.br || 6,
        gzip: config.levels?.gzip || 6,
        deflate: config.levels?.deflate || 6
      },
      
      // Thresholds
      threshold: config.threshold || 1024, // Minimum bytes to compress
      maxSize: config.maxSize || 10 * 1024 * 1024, // 10MB max compression
      
      // Content type filters
      compressibleTypes: config.compressibleTypes || [
        'text/html',
        'text/css',
        'text/javascript',
        'text/plain',
        'text/xml',
        'application/javascript',
        'application/json',
        'application/xml',
        'application/rss+xml',
        'application/atom+xml',
        'image/svg+xml'
      ],
      
      // Advanced options
      enableCaching: config.enableCaching ?? true,
      cacheMaxAge: config.cacheMaxAge || 3600, // 1 hour
      enableETag: config.enableETag ?? true,
      enableVary: config.enableVary ?? true,
      
      // Performance
      enableStreaming: config.enableStreaming ?? true,
      chunkSize: config.chunkSize || 16384, // 16KB chunks
      enableWorkerThreads: config.enableWorkerThreads ?? false,
      maxConcurrency: config.maxConcurrency || 10,
      
      // Quality settings
      enableSmartCompression: config.enableSmartCompression ?? true,
      adaptiveLevels: config.adaptiveLevels ?? true,
      
      ...config
    };

    this.cache = new Map();
    this.activeCompressions = new Map();
    this.stats = {
      totalRequests: 0,
      compressed: 0,
      bytesIn: 0,
      bytesOut: 0,
      compressionRatio: 0,
      avgCompressionTime: 0,
      cacheHits: 0
    };

    this.initializeWorkerPool();
  }

  // Initialize worker pool for CPU-intensive compression
  initializeWorkerPool() {
    if (this.config.enableWorkerThreads) {
      const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');
      
      if (isMainThread) {
        this.workers = [];
        this.workerQueue = [];
        
        // Create worker pool
        for (let i = 0; i < this.config.maxConcurrency; i++) {
          const worker = new Worker(__filename, {
            workerData: { isWorker: true }
          });
          
          worker.on('message', (result) => {
            this.handleWorkerResult(result);
          });
          
          this.workers.push(worker);
        }
      }
    }
  }

  // Main compression entry point
  async compress(data, options = {}) {
    this.stats.totalRequests++;
    this.stats.bytesIn += data.length;
    
    const startTime = Date.now();
    
    try {
      // Check if compression is worthwhile
      if (!this.shouldCompress(data, options)) {
        return {
          compressed: false,
          data,
          encoding: 'identity',
          originalSize: data.length,
          compressedSize: data.length,
          compressionRatio: 1
        };
      }

      // Check cache first
      if (this.config.enableCaching) {
        const cached = await this.getCachedCompression(data, options);
        if (cached) {
          this.stats.cacheHits++;
          this.emit('cacheHit', { size: data.length });
          return cached;
        }
      }

      // Choose best compression algorithm
      const algorithm = this.chooseCompressionAlgorithm(options);
      
      // Perform compression
      let result;
      if (this.config.enableWorkerThreads && data.length > 100 * 1024) {
        result = await this.compressWithWorker(data, algorithm, options);
      } else {
        result = await this.compressSync(data, algorithm, options);
      }

      // Update statistics
      this.updateStats(result, Date.now() - startTime);
      
      // Cache result if beneficial
      if (this.config.enableCaching && this.shouldCache(result)) {
        await this.cacheCompression(data, result, options);
      }

      this.emit('compressed', result);
      return result;

    } catch (error) {
      this.emit('compressionError', { error, dataSize: data.length });
      
      // Return uncompressed on error
      return {
        compressed: false,
        data,
        encoding: 'identity',
        originalSize: data.length,
        compressedSize: data.length,
        compressionRatio: 1,
        error: error.message
      };
    }
  }

  // Check if data should be compressed
  shouldCompress(data, options = {}) {
    // Size checks
    if (data.length < this.config.threshold || data.length > this.config.maxSize) {
      return false;
    }

    // Content type check
    if (options.contentType && !this.isCompressibleType(options.contentType)) {
      return false;
    }

    // Already compressed check
    if (options.contentEncoding && options.contentEncoding !== 'identity') {
      return false;
    }

    // Smart compression: analyze entropy
    if (this.config.enableSmartCompression && !this.hasCompressionPotential(data)) {
      return false;
    }

    return true;
  }

  // Check if content type is compressible
  isCompressibleType(contentType) {
    const type = contentType.toLowerCase().split(';')[0];
    return this.config.compressibleTypes.some(compressible => 
      type.includes(compressible)
    );
  }

  // Analyze data for compression potential
  hasCompressionPotential(data) {
    // Quick entropy check - sample first 1KB
    const sample = data.slice(0, Math.min(1024, data.length));
    const uniqueBytes = new Set(sample).size;
    const entropy = uniqueBytes / 256;
    
    // If entropy is too high (> 0.9), data is likely already compressed
    return entropy < 0.9;
  }

  // Choose best compression algorithm
  chooseCompressionAlgorithm(options = {}) {
    const acceptEncoding = options.acceptEncoding || '';
    
    for (const algorithm of this.config.algorithms) {
      if (acceptEncoding.includes(algorithm)) {
        return algorithm;
      }
    }
    
    return this.config.algorithms[0]; // Default to first preference
  }

  // Synchronous compression
  async compressSync(data, algorithm, options = {}) {
    const level = this.getCompressionLevel(algorithm, data.length);
    let compressedData;
    let encoding;

    switch (algorithm) {
      case 'br':
        compressedData = await brotliCompressAsync(data, {
          params: {
            [zlib.constants.BROTLI_PARAM_QUALITY]: level,
            [zlib.constants.BROTLI_PARAM_SIZE_HINT]: data.length
          }
        });
        encoding = 'br';
        break;
        
      case 'gzip':
        compressedData = await gzipAsync(data, { level });
        encoding = 'gzip';
        break;
        
      case 'deflate':
        compressedData = await deflateAsync(data, { level });
        encoding = 'deflate';
        break;
        
      default:
        throw new Error(`Unsupported compression algorithm: ${algorithm}`);
    }

    const compressionRatio = compressedData.length / data.length;
    
    return {
      compressed: true,
      data: compressedData,
      encoding,
      algorithm,
      originalSize: data.length,
      compressedSize: compressedData.length,
      compressionRatio,
      compressionLevel: level
    };
  }

  // Get adaptive compression level
  getCompressionLevel(algorithm, dataSize) {
    if (!this.config.adaptiveLevels) {
      return this.config.levels[algorithm];
    }

    // Adjust level based on data size for better speed/compression tradeoff
    const baseLevel = this.config.levels[algorithm];
    
    if (dataSize < 10 * 1024) { // < 10KB
      return Math.max(1, baseLevel - 2); // Faster compression for small files
    } else if (dataSize > 1024 * 1024) { // > 1MB
      return Math.min(9, baseLevel + 1); // Better compression for large files
    }
    
    return baseLevel;
  }

  // Compression with worker threads
  async compressWithWorker(data, algorithm, options = {}) {
    return new Promise((resolve, reject) => {
      const taskId = crypto.randomUUID();
      
      const task = {
        id: taskId,
        data,
        algorithm,
        level: this.getCompressionLevel(algorithm, data.length),
        resolve,
        reject,
        timestamp: Date.now()
      };

      this.workerQueue.push(task);
      this.processWorkerQueue();
    });
  }

  // Process worker queue
  processWorkerQueue() {
    if (this.workerQueue.length === 0) return;
    
    const availableWorker = this.workers.find(w => !w.busy);
    if (!availableWorker) return;

    const task = this.workerQueue.shift();
    availableWorker.busy = true;
    availableWorker.currentTask = task.id;

    availableWorker.postMessage({
      id: task.id,
      data: task.data,
      algorithm: task.algorithm,
      level: task.level
    });

    this.activeCompressions.set(task.id, task);
  }

  // Handle worker result
  handleWorkerResult(result) {
    const task = this.activeCompressions.get(result.id);
    if (!task) return;

    const worker = this.workers.find(w => w.currentTask === result.id);
    if (worker) {
      worker.busy = false;
      worker.currentTask = null;
    }

    this.activeCompressions.delete(result.id);

    if (result.error) {
      task.reject(new Error(result.error));
    } else {
      task.resolve({
        compressed: true,
        data: Buffer.from(result.data),
        encoding: result.encoding,
        algorithm: result.algorithm,
        originalSize: result.originalSize,
        compressedSize: result.compressedSize,
        compressionRatio: result.compressionRatio,
        compressionLevel: result.level
      });
    }

    // Process next task
    this.processWorkerQueue();
  }

  // Stream compression for large data
  createCompressionStream(algorithm, options = {}) {
    const level = this.getCompressionLevel(algorithm, options.estimatedSize || 0);
    
    switch (algorithm) {
      case 'br':
        return zlib.createBrotliCompress({
          params: {
            [zlib.constants.BROTLI_PARAM_QUALITY]: level
          }
        });
        
      case 'gzip':
        return zlib.createGzip({ level });
        
      case 'deflate':
        return zlib.createDeflate({ level });
        
      default:
        throw new Error(`Unsupported streaming algorithm: ${algorithm}`);
    }
  }

  // Cache management
  generateCacheKey(data, options = {}) {
    const hash = crypto.createHash('sha256');
    hash.update(data);
    hash.update(JSON.stringify(options));
    return hash.digest('hex');
  }

  async getCachedCompression(data, options = {}) {
    const key = this.generateCacheKey(data, options);
    const cached = this.cache.get(key);
    
    if (cached && Date.now() - cached.timestamp < this.config.cacheMaxAge * 1000) {
      return cached.result;
    }
    
    return null;
  }

  async cacheCompression(data, result, options = {}) {
    const key = this.generateCacheKey(data, options);
    
    // Don't cache if result is too large or compression ratio is poor
    if (result.compressedSize > 1024 * 1024 || result.compressionRatio > 0.9) {
      return;
    }

    this.cache.set(key, {
      result,
      timestamp: Date.now()
    });

    // Clean up old cache entries
    this.cleanupCache();
  }

  shouldCache(result) {
    return result.compressed && 
           result.compressionRatio < 0.8 && 
           result.compressedSize < 1024 * 1024; // 1MB
  }

  cleanupCache() {
    if (this.cache.size < 1000) return; // Only cleanup when cache gets large
    
    const now = Date.now();
    const maxAge = this.config.cacheMaxAge * 1000;
    
    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > maxAge) {
        this.cache.delete(key);
      }
    }
  }

  // Update statistics
  updateStats(result, compressionTime) {
    if (result.compressed) {
      this.stats.compressed++;
      this.stats.bytesOut += result.compressedSize;
      
      // Update running average
      const totalTime = this.stats.avgCompressionTime * (this.stats.compressed - 1) + compressionTime;
      this.stats.avgCompressionTime = totalTime / this.stats.compressed;
      
      // Update compression ratio
      this.stats.compressionRatio = this.stats.bytesOut / this.stats.bytesIn;
    }
  }

  // Get compression statistics
  getStats() {
    const compressionRate = this.stats.totalRequests > 0 
      ? ((this.stats.compressed / this.stats.totalRequests) * 100).toFixed(2) 
      : 0;

    const bandwidthSaved = this.stats.bytesIn - this.stats.bytesOut;
    const bandwidthSavings = this.stats.bytesIn > 0 
      ? ((bandwidthSaved / this.stats.bytesIn) * 100).toFixed(2)
      : 0;

    return {
      ...this.stats,
      compressionRate: `${compressionRate}%`,
      bandwidthSaved: this.formatBytes(bandwidthSaved),
      bandwidthSavings: `${bandwidthSavings}%`,
      cacheSize: this.cache.size,
      activeCompressions: this.activeCompressions.size
    };
  }

  // Format bytes for display
  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // Health check
  async healthCheck() {
    const testData = Buffer.from('Hello, World! '.repeat(100));
    
    try {
      const result = await this.compress(testData, { contentType: 'text/plain' });
      
      return {
        healthy: result.compressed,
        compressionRatio: result.compressionRatio,
        algorithm: result.algorithm,
        stats: this.getStats()
      };
    } catch (error) {
      return {
        healthy: false,
        error: error.message
      };
    }
  }

  // Cleanup resources
  destroy() {
    if (this.workers) {
      for (const worker of this.workers) {
        worker.terminate();
      }
    }
    
    this.cache.clear();
    this.activeCompressions.clear();
  }
}

// Express middleware for response compression
function createCompressionMiddleware(compressor, options = {}) {
  return async (req, res, next) => {
    const originalSend = res.send;
    const originalEnd = res.end;
    
    // Check if client accepts compression
    const acceptEncoding = req.headers['accept-encoding'] || '';
    
    if (!acceptEncoding) {
      return next();
    }

    // Override send method
    res.send = async function(data) {
      if (this.headersSent || !data) {
        return originalSend.call(this, data);
      }

      try {
        const buffer = Buffer.isBuffer(data) ? data : Buffer.from(data);
        const contentType = this.get('Content-Type') || 'text/html';
        
        const result = await compressor.compress(buffer, {
          acceptEncoding,
          contentType,
          contentEncoding: this.get('Content-Encoding')
        });

        if (result.compressed) {
          this.set('Content-Encoding', result.encoding);
          this.set('Content-Length', result.compressedSize);
          
          if (compressor.config.enableVary) {
            this.set('Vary', 'Accept-Encoding');
          }

          if (compressor.config.enableETag) {
            const etag = crypto.createHash('md5').update(result.data).digest('hex');
            this.set('ETag', `"${etag}"`);
          }
        }

        originalSend.call(this, result.data);
      } catch (error) {
        console.warn('Compression middleware error:', error.message);
        originalSend.call(this, data);
      }
    };

    // Override end method for streaming responses
    res.end = function(chunk, encoding) {
      if (chunk && !this.headersSent) {
        return this.send(chunk);
      }
      
      return originalEnd.call(this, chunk, encoding);
    };

    next();
  };
}

// Worker thread code for CPU-intensive compression
if (require.main === module && process.env.WORKER_THREADS_ENABLED) {
  const { parentPort, workerData } = require('worker_threads');
  
  if (workerData && workerData.isWorker && parentPort) {
    parentPort.on('message', async (task) => {
      try {
        const { id, data, algorithm, level } = task;
        let compressedData;
        let encoding;

        switch (algorithm) {
          case 'br':
            compressedData = await brotliCompressAsync(data, {
              params: {
                [zlib.constants.BROTLI_PARAM_QUALITY]: level
              }
            });
            encoding = 'br';
            break;
            
          case 'gzip':
            compressedData = await gzipAsync(data, { level });
            encoding = 'gzip';
            break;
            
          case 'deflate':
            compressedData = await deflateAsync(data, { level });
            encoding = 'deflate';
            break;
        }

        parentPort.postMessage({
          id,
          data: Array.from(compressedData),
          encoding,
          algorithm,
          level,
          originalSize: data.length,
          compressedSize: compressedData.length,
          compressionRatio: compressedData.length / data.length
        });
      } catch (error) {
        parentPort.postMessage({
          id: task.id,
          error: error.message
        });
      }
    });
  }
}

module.exports = {
  ResponseCompressor,
  createCompressionMiddleware
};