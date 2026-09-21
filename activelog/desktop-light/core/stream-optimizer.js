/**
 * Streaming Optimization Engine - Efficient data streaming with minimal overhead
 */

const { EventEmitter } = require('events');
const { Transform, Readable, Writable } = require('stream');
const zlib = require('zlib');
const crypto = require('crypto');

class StreamOptimizer extends EventEmitter {
    constructor(options = {}) {
        super();
        
        this.config = {
            compression: options.compression ?? true,
            compressionLevel: options.compressionLevel || 6,
            bufferSize: options.bufferSize || 64 * 1024, // 64KB
            maxBufferSize: options.maxBufferSize || 1024 * 1024, // 1MB
            streamTimeout: options.streamTimeout || 30000,
            enableWebStreams: options.enableWebStreams ?? true,
            enableBrotli: options.enableBrotli ?? true,
            adaptiveBitrate: options.adaptiveBitrate ?? true,
            networkQualityThreshold: options.networkQualityThreshold || 0.8,
            ...options
        };
        
        this.state = {
            activeStreams: new Map(),
            streamStats: new Map(),
            compressionRatio: 1.0,
            networkQuality: 1.0,
            totalBytesStreamed: 0,
            totalCompressionSavings: 0,
            lastOptimization: Date.now()
        };
        
        this.bufferPool = new BufferPool();
        this.compressionCache = new Map();
        this.qualityMonitor = new NetworkQualityMonitor();
        
        this.init();
    }
    
    init() {
        this.setupCompressionStrategies();
        this.setupNetworkMonitoring();
        this.setupAdaptiveBitrate();
        this.setupStreamPooling();
        
        // Periodic optimization
        setInterval(() => {
            this.optimizeStreams();
        }, 10000); // Every 10 seconds
        
        console.log('🌊 Stream Optimizer initialized');
    }
    
    setupCompressionStrategies() {
        this.compression = {
            gzip: {
                compress: zlib.createGzip.bind(zlib, {
                    level: this.config.compressionLevel,
                    windowBits: 15,
                    memLevel: 8
                }),
                decompress: zlib.createGunzip.bind(zlib)
            },
            
            deflate: {
                compress: zlib.createDeflate.bind(zlib, {
                    level: this.config.compressionLevel,
                    windowBits: 15,
                    memLevel: 8
                }),
                decompress: zlib.createInflate.bind(zlib)
            },
            
            brotli: this.config.enableBrotli ? {
                compress: zlib.createBrotliCompress.bind(zlib, {
                    params: {
                        [zlib.constants.BROTLI_PARAM_QUALITY]: this.config.compressionLevel,
                        [zlib.constants.BROTLI_PARAM_SIZE_HINT]: this.config.bufferSize
                    }
                }),
                decompress: zlib.createBrotliDecompress.bind(zlib)
            } : null
        };
        
        // Remove brotli if not supported
        if (!this.compression.brotli) {
            delete this.compression.brotli;
        }
    }
    
    setupNetworkMonitoring() {
        this.qualityMonitor.on('qualityChange', (quality) => {
            this.state.networkQuality = quality;
            this.adaptToNetworkQuality(quality);
        });
        
        this.qualityMonitor.start();
    }
    
    setupAdaptiveBitrate() {
        if (!this.config.adaptiveBitrate) return;
        
        this.bitrateController = {
            currentBitrate: 1000000, // 1Mbps default
            targetBitrate: 1000000,
            bitrateHistory: [],
            adaptationThreshold: 0.1,
            
            adapt: (networkQuality) => {
                const oldBitrate = this.bitrateController.currentBitrate;
                
                if (networkQuality > 0.8) {
                    this.bitrateController.targetBitrate = Math.min(
                        oldBitrate * 1.2,
                        5000000 // 5Mbps max
                    );
                } else if (networkQuality < 0.5) {
                    this.bitrateController.targetBitrate = Math.max(
                        oldBitrate * 0.8,
                        100000 // 100Kbps min
                    );
                }
                
                // Smooth transition
                this.bitrateController.currentBitrate = 
                    oldBitrate + (this.bitrateController.targetBitrate - oldBitrate) * 0.1;
                
                this.bitrateController.bitrateHistory.push({
                    timestamp: Date.now(),
                    bitrate: this.bitrateController.currentBitrate,
                    networkQuality
                });
                
                // Limit history size
                if (this.bitrateController.bitrateHistory.length > 100) {
                    this.bitrateController.bitrateHistory.shift();
                }
            }
        };
    }
    
    setupStreamPooling() {
        this.streamPool = {
            readStreams: [],
            writeStreams: [],
            transformStreams: [],
            maxPoolSize: 10,
            
            getReadStream: () => {
                return this.streamPool.readStreams.pop() || new OptimizedReadableStream();
            },
            
            getWriteStream: () => {
                return this.streamPool.writeStreams.pop() || new OptimizedWritableStream();
            },
            
            getTransformStream: () => {
                return this.streamPool.transformStreams.pop() || new OptimizedTransformStream();
            },
            
            recycleStream: (stream, type) => {
                stream.reset?.();
                
                const pool = this.streamPool[`${type}Streams`];
                if (pool && pool.length < this.streamPool.maxPoolSize) {
                    pool.push(stream);
                }
            }
        };
    }
    
    createOptimizedStream(source, options = {}) {
        const streamId = this.generateStreamId();
        const startTime = Date.now();
        
        console.log(`🌊 Creating optimized stream: ${streamId}`);
        
        const streamConfig = {
            ...this.config,
            ...options,
            streamId,
            compression: this.selectOptimalCompression(options.dataType),
            bufferSize: this.calculateOptimalBufferSize(),
            networkQuality: this.state.networkQuality
        };
        
        const optimizedStream = new OptimizedStream(source, streamConfig);
        
        // Track stream
        this.state.activeStreams.set(streamId, {
            stream: optimizedStream,
            config: streamConfig,
            stats: {
                startTime,
                bytesIn: 0,
                bytesOut: 0,
                compressionRatio: 1.0,
                avgThroughput: 0,
                quality: this.state.networkQuality
            }
        });
        
        // Setup stream monitoring
        this.setupStreamMonitoring(optimizedStream, streamId);
        
        return optimizedStream;
    }
    
    selectOptimalCompression(dataType) {
        if (!this.config.compression) return null;
        
        // Select compression based on data type and network quality
        const compressionStrategies = {
            'text': 'gzip',
            'json': 'gzip',
            'binary': 'deflate',
            'image': null, // Already compressed
            'video': null, // Already compressed
            'audio': null  // Already compressed
        };
        
        const strategy = compressionStrategies[dataType] || 'gzip';
        
        // Adjust based on network quality
        if (this.state.networkQuality < 0.5 && strategy) {
            // Use faster compression on poor networks
            return 'deflate';
        } else if (this.state.networkQuality > 0.8 && this.compression.brotli && strategy) {
            // Use better compression on good networks
            return 'brotli';
        }
        
        return strategy;
    }
    
    calculateOptimalBufferSize() {
        const networkQuality = this.state.networkQuality;
        const baseSize = this.config.bufferSize;
        
        if (networkQuality > 0.8) {
            return Math.min(baseSize * 2, this.config.maxBufferSize);
        } else if (networkQuality < 0.5) {
            return Math.max(baseSize / 2, 4096); // 4KB minimum
        }
        
        return baseSize;
    }
    
    setupStreamMonitoring(stream, streamId) {
        const stats = this.state.activeStreams.get(streamId).stats;
        
        stream.on('data', (chunk) => {
            stats.bytesOut += chunk.length;
            this.state.totalBytesStreamed += chunk.length;
        });
        
        stream.on('input', (chunk) => {
            stats.bytesIn += chunk.length;
            stats.compressionRatio = stats.bytesOut / Math.max(stats.bytesIn, 1);
        });
        
        stream.on('end', () => {
            this.onStreamEnd(streamId);
        });
        
        stream.on('error', (error) => {
            this.onStreamError(streamId, error);
        });
        
        // Throughput monitoring
        setInterval(() => {
            const duration = Date.now() - stats.startTime;
            stats.avgThroughput = stats.bytesOut / (duration / 1000); // bytes/sec
        }, 1000);
    }
    
    onStreamEnd(streamId) {
        const streamInfo = this.state.activeStreams.get(streamId);
        if (!streamInfo) return;
        
        const { stats, config } = streamInfo;
        const duration = Date.now() - stats.startTime;
        
        // Update global stats
        this.state.totalCompressionSavings += stats.bytesIn - stats.bytesOut;
        
        // Store stream stats
        this.state.streamStats.set(streamId, {
            ...stats,
            duration,
            efficiency: stats.compressionRatio,
            throughput: stats.bytesOut / (duration / 1000)
        });
        
        // Remove from active streams
        this.state.activeStreams.delete(streamId);
        
        console.log(`✅ Stream completed: ${streamId} (${duration}ms, ${stats.compressionRatio.toFixed(2)}x compression)`);
        
        this.emit('streamCompleted', { streamId, stats, duration });
    }
    
    onStreamError(streamId, error) {
        console.error(`❌ Stream error: ${streamId}`, error.message);
        
        const streamInfo = this.state.activeStreams.get(streamId);
        if (streamInfo) {
            streamInfo.stats.error = error.message;
        }
        
        this.state.activeStreams.delete(streamId);
        this.emit('streamError', { streamId, error });
    }
    
    adaptToNetworkQuality(quality) {
        console.log(`📶 Network quality changed: ${(quality * 100).toFixed(1)}%`);
        
        // Adjust compression level
        if (quality < 0.3) {
            this.config.compressionLevel = Math.max(1, this.config.compressionLevel - 2);
        } else if (quality > 0.8) {
            this.config.compressionLevel = Math.min(9, this.config.compressionLevel + 1);
        }
        
        // Adjust buffer size for active streams
        const newBufferSize = this.calculateOptimalBufferSize();
        
        for (const [streamId, streamInfo] of this.state.activeStreams) {
            streamInfo.stream.adjustBufferSize?.(newBufferSize);
        }
        
        // Adapt bitrate if enabled
        if (this.config.adaptiveBitrate) {
            this.bitrateController.adapt(quality);
        }
        
        this.emit('networkQualityChanged', { quality, compressionLevel: this.config.compressionLevel });
    }
    
    optimizeStreams() {
        if (this.state.activeStreams.size === 0) return;
        
        console.log(`🔧 Optimizing ${this.state.activeStreams.size} active streams`);
        
        const now = Date.now();
        const optimizations = [];
        
        for (const [streamId, streamInfo] of this.state.activeStreams) {
            const { stream, stats, config } = streamInfo;
            const age = now - stats.startTime;
            
            // Timeout check
            if (age > this.config.streamTimeout) {
                stream.destroy(new Error('Stream timeout'));
                optimizations.push({ streamId, action: 'timeout', reason: 'exceeded_timeout' });
                continue;
            }
            
            // Performance optimization
            if (stats.compressionRatio > 5.0) {
                // Very high compression ratio, might be inefficient
                stream.adjustCompression?.('deflate');
                optimizations.push({ streamId, action: 'compression', reason: 'high_ratio' });
            }
            
            // Throughput optimization
            if (stats.avgThroughput < 1000 && age > 5000) {
                // Very slow stream, increase buffer size
                const newBufferSize = Math.min(config.bufferSize * 2, this.config.maxBufferSize);
                stream.adjustBufferSize?.(newBufferSize);
                optimizations.push({ streamId, action: 'buffer', reason: 'low_throughput' });
            }
        }
        
        if (optimizations.length > 0) {
            console.log(`✨ Applied ${optimizations.length} stream optimizations`);
            this.emit('streamsOptimized', optimizations);
        }
        
        this.state.lastOptimization = now;
    }
    
    generateStreamId() {
        return `stream_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    // Public API methods
    
    compressData(data, algorithm = 'gzip') {
        return new Promise((resolve, reject) => {
            const compressor = this.compression[algorithm];
            if (!compressor) {
                return reject(new Error(`Compression algorithm not supported: ${algorithm}`));
            }
            
            const chunks = [];
            const compress = compressor.compress();
            
            compress.on('data', chunk => chunks.push(chunk));
            compress.on('end', () => resolve(Buffer.concat(chunks)));
            compress.on('error', reject);
            
            compress.write(data);
            compress.end();
        });
    }
    
    decompressData(data, algorithm = 'gzip') {
        return new Promise((resolve, reject) => {
            const decompressor = this.compression[algorithm];
            if (!decompressor) {
                return reject(new Error(`Decompression algorithm not supported: ${algorithm}`));
            }
            
            const chunks = [];
            const decompress = decompressor.decompress();
            
            decompress.on('data', chunk => chunks.push(chunk));
            decompress.on('end', () => resolve(Buffer.concat(chunks)));
            decompress.on('error', reject);
            
            decompress.write(data);
            decompress.end();
        });
    }
    
    createWebStream(source, options = {}) {
        if (!this.config.enableWebStreams) {
            throw new Error('Web streams not enabled');
        }
        
        return new ReadableStream({
            start(controller) {
                const optimizedStream = this.createOptimizedStream(source, options);
                
                optimizedStream.on('data', chunk => {
                    controller.enqueue(chunk);
                });
                
                optimizedStream.on('end', () => {
                    controller.close();
                });
                
                optimizedStream.on('error', error => {
                    controller.error(error);
                });
            }
        });
    }
    
    getStreamStats(streamId) {
        return this.state.streamStats.get(streamId) || 
               this.state.activeStreams.get(streamId)?.stats;
    }
    
    getGlobalStats() {
        const compressionRatio = this.state.totalCompressionSavings > 0 ? 
            this.state.totalBytesStreamed / (this.state.totalBytesStreamed - this.state.totalCompressionSavings) : 1.0;
        
        return {
            activeStreams: this.state.activeStreams.size,
            totalStreams: this.state.streamStats.size + this.state.activeStreams.size,
            totalBytesStreamed: this.state.totalBytesStreamed,
            totalCompressionSavings: this.state.totalCompressionSavings,
            avgCompressionRatio: compressionRatio,
            networkQuality: this.state.networkQuality,
            currentBitrate: this.bitrateController?.currentBitrate,
            lastOptimization: this.state.lastOptimization
        };
    }
    
    listActiveStreams() {
        return Array.from(this.state.activeStreams.entries()).map(([id, info]) => ({
            id,
            age: Date.now() - info.stats.startTime,
            bytesIn: info.stats.bytesIn,
            bytesOut: info.stats.bytesOut,
            compressionRatio: info.stats.compressionRatio,
            throughput: info.stats.avgThroughput
        }));
    }
    
    async shutdown() {
        console.log('🔄 Shutting down Stream Optimizer...');
        
        // Close all active streams
        for (const [streamId, streamInfo] of this.state.activeStreams) {
            streamInfo.stream.destroy();
        }
        
        this.state.activeStreams.clear();
        
        // Stop quality monitoring
        this.qualityMonitor.stop();
        
        // Clear caches
        this.compressionCache.clear();
        this.bufferPool.clear();
        
        console.log('✅ Stream Optimizer shutdown complete');
    }
}

// Helper classes

class OptimizedStream extends Transform {
    constructor(source, options) {
        super({ objectMode: false });
        
        this.config = options;
        this.source = source;
        this.compressor = null;
        this.buffer = Buffer.alloc(options.bufferSize);
        this.bufferPos = 0;
        
        if (options.compression) {
            const StreamOptimizer = require('./stream-optimizer');
            const optimizer = new StreamOptimizer();
            this.compressor = optimizer.compression[options.compression].compress();
            
            this.compressor.on('data', (chunk) => {
                this.push(chunk);
            });
        }
        
        this.setupSource();
    }
    
    setupSource() {
        if (typeof this.source === 'function') {
            this.source((data) => this.writeToBuffer(data));
        } else if (this.source.readable) {
            this.source.on('data', (data) => this.writeToBuffer(data));
            this.source.on('end', () => this.end());
        }
    }
    
    writeToBuffer(data) {
        this.emit('input', data);
        
        if (this.compressor) {
            this.compressor.write(data);
        } else {
            this.push(data);
        }
    }
    
    _transform(chunk, encoding, callback) {
        // Pass through transform
        callback(null, chunk);
    }
    
    adjustBufferSize(newSize) {
        this.config.bufferSize = newSize;
        this.buffer = Buffer.alloc(newSize);
        this.bufferPos = 0;
    }
    
    adjustCompression(algorithm) {
        // Implementation would recreate compressor with new algorithm
        this.config.compression = algorithm;
    }
}

class OptimizedReadableStream extends Readable {
    constructor(options = {}) {
        super(options);
        this.readIndex = 0;
    }
    
    _read(size) {
        // Implementation for readable stream
    }
    
    reset() {
        this.readIndex = 0;
    }
}

class OptimizedWritableStream extends Writable {
    constructor(options = {}) {
        super(options);
        this.writeIndex = 0;
    }
    
    _write(chunk, encoding, callback) {
        this.writeIndex += chunk.length;
        callback();
    }
    
    reset() {
        this.writeIndex = 0;
    }
}

class OptimizedTransformStream extends Transform {
    constructor(options = {}) {
        super(options);
    }
    
    _transform(chunk, encoding, callback) {
        callback(null, chunk);
    }
    
    reset() {
        // Reset transform state
    }
}

class BufferPool {
    constructor() {
        this.pools = new Map();
    }
    
    get(size) {
        const pool = this.pools.get(size) || [];
        return pool.pop() || Buffer.alloc(size);
    }
    
    return(buffer) {
        const size = buffer.length;
        if (!this.pools.has(size)) {
            this.pools.set(size, []);
        }
        
        const pool = this.pools.get(size);
        if (pool.length < 10) { // Max 10 buffers per size
            pool.push(buffer);
        }
    }
    
    clear() {
        this.pools.clear();
    }
}

class NetworkQualityMonitor extends EventEmitter {
    constructor() {
        super();
        
        this.quality = 1.0;
        this.measurements = [];
        this.interval = null;
    }
    
    start() {
        this.interval = setInterval(() => {
            this.measureQuality();
        }, 5000); // Every 5 seconds
    }
    
    stop() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    }
    
    measureQuality() {
        // Simplified quality measurement
        // In real implementation would measure latency, packet loss, etc.
        const newQuality = Math.max(0.1, Math.min(1.0, 
            this.quality + (Math.random() - 0.5) * 0.2
        ));
        
        if (Math.abs(newQuality - this.quality) > 0.1) {
            this.quality = newQuality;
            this.emit('qualityChange', this.quality);
        }
        
        this.measurements.push({
            timestamp: Date.now(),
            quality: this.quality
        });
        
        // Keep last 100 measurements
        if (this.measurements.length > 100) {
            this.measurements.shift();
        }
    }
}

module.exports = StreamOptimizer;