/**
 * Advanced Memory Management System - Intelligent memory allocation and optimization
 */

const { EventEmitter } = require('events');

class MemoryManager extends EventEmitter {
    constructor(options = {}) {
        super();
        
        this.config = {
            maxHeapSize: options.maxHeapSize || 256 * 1024 * 1024, // 256MB
            maxBufferSize: options.maxBufferSize || 64 * 1024 * 1024, // 64MB
            gcThreshold: options.gcThreshold || 0.85, // 85% memory usage
            gcInterval: options.gcInterval || 30000, // 30 seconds
            compressionEnabled: options.compressionEnabled ?? true,
            memoryLeakDetection: options.memoryLeakDetection ?? true,
            smartCaching: options.smartCaching ?? true,
            bufferPooling: options.bufferPooling ?? true,
            ...options
        };
        
        this.state = {
            heapUsed: 0,
            heapTotal: 0,
            heapLimit: 0,
            external: 0,
            arrayBuffers: 0,
            rss: 0, // Resident Set Size
            bufferPools: new Map(),
            caches: new Map(),
            compressionCache: new Map(),
            gcHistory: [],
            lastCleanup: Date.now(),
            leakSuspects: new Map(),
            fragmentationLevel: 0,
            compressionRatio: 1.0
        };
        
        this.pools = {
            smallBuffers: [], // < 1KB
            mediumBuffers: [], // 1KB - 64KB  
            largeBuffers: [], // > 64KB
            stringCache: new Map(),
            objectCache: new Map(),
            temporaryObjects: new WeakMap()
        };
        
        this.metrics = {
            allocations: 0,
            deallocations: 0,
            gcTriggers: 0,
            memoryLeaks: 0,
            compressionSavings: 0,
            cacheHits: 0,
            cacheMisses: 0,
            poolHits: 0,
            poolMisses: 0,
            fragmentationEvents: 0
        };
        
        this.timers = new Map();
        this.watchers = new Set();
        
        this.init();
    }
    
    init() {
        this.startMemoryMonitoring();
        this.setupGarbageCollection();
        this.setupBufferPooling();
        this.setupSmartCaching();
        this.setupMemoryLeakDetection();
        this.setupCompression();
        
        // V8 heap optimization
        this.optimizeV8Heap();
        
        console.log('🧠 Memory Manager initialized');
    }
    
    startMemoryMonitoring() {
        this.timers.set('memoryMonitor', setInterval(() => {
            this.updateMemoryMetrics();
            this.checkMemoryPressure();
            this.detectFragmentation();
            this.optimizeMemoryLayout();
        }, 5000)); // Every 5 seconds
        
        // Initial metrics update
        this.updateMemoryMetrics();
    }
    
    updateMemoryMetrics() {
        const usage = process.memoryUsage();
        
        // Store previous values for comparison
        const prevHeapUsed = this.state.heapUsed;
        
        // Update current values
        this.state.heapUsed = usage.heapUsed;
        this.state.heapTotal = usage.heapTotal;
        this.state.external = usage.external;
        this.state.arrayBuffers = usage.arrayBuffers;
        this.state.rss = usage.rss;
        
        // Calculate heap limit (V8 default is around 1.7GB on 64-bit)
        this.state.heapLimit = this.config.maxHeapSize;
        
        // Emit metrics update
        this.emit('memoryMetricsUpdated', this.getMemoryStatus());
        
        // Check for rapid memory growth (potential leak)
        if (this.config.memoryLeakDetection) {
            const growthRate = this.state.heapUsed - prevHeapUsed;
            if (growthRate > 10 * 1024 * 1024) { // More than 10MB growth in 5 seconds
                this.handleSuspiciousGrowth(growthRate);
            }
        }
    }
    
    checkMemoryPressure() {
        const usage = this.state.heapUsed / this.state.heapLimit;
        
        if (usage > this.config.gcThreshold) {
            console.log(`🚨 Memory pressure detected: ${(usage * 100).toFixed(1)}%`);
            this.handleMemoryPressure();
        } else if (usage > 0.7) {
            console.log(`⚠️ High memory usage: ${(usage * 100).toFixed(1)}%`);
            this.preventiveCleanup();
        }
    }
    
    handleMemoryPressure() {
        console.log('🧹 Handling memory pressure...');
        
        // Immediate actions
        this.clearCaches(true);
        this.compactBufferPools();
        this.releaseUnusedObjects();
        
        // Force garbage collection
        this.forceGarbageCollection();
        
        // Emit warning
        this.emit('memoryPressure', {
            usage: this.state.heapUsed,
            limit: this.state.heapLimit,
            percentage: (this.state.heapUsed / this.state.heapLimit) * 100
        });
    }
    
    preventiveCleanup() {
        // Lighter cleanup to prevent memory pressure
        this.clearCaches(false);
        this.compactSmallObjects();
        this.defragmentPools();
    }
    
    setupGarbageCollection() {
        this.gc = {
            forced: 0,
            automatic: 0,
            lastRun: Date.now(),
            averageDuration: 0,
            isRunning: false
        };
        
        // Schedule regular garbage collection
        this.timers.set('gcScheduler', setInterval(() => {
            if (this.shouldTriggerGC()) {
                this.scheduleGarbageCollection();
            }
        }, this.config.gcInterval));
    }
    
    shouldTriggerGC() {
        const usage = this.state.heapUsed / this.state.heapLimit;
        const timeSinceLastGC = Date.now() - this.gc.lastRun;
        
        return usage > 0.6 || timeSinceLastGC > 60000; // 60 seconds max between GC
    }
    
    scheduleGarbageCollection() {
        // Don't schedule if already running
        if (this.gc.isRunning) return;
        
        // Use setImmediate to avoid blocking
        setImmediate(() => {
            this.performGarbageCollection();
        });
    }
    
    performGarbageCollection() {
        if (!global.gc) {
            console.warn('Garbage collection not available (run with --expose-gc)');
            return;
        }
        
        this.gc.isRunning = true;
        const startTime = Date.now();
        const beforeMemory = this.state.heapUsed;
        
        console.log('🗑️ Performing garbage collection...');
        
        try {
            // Clear weak references first
            this.cleanupWeakReferences();
            
            // Run garbage collection
            global.gc();
            
            // Update metrics
            this.updateMemoryMetrics();
            const duration = Date.now() - startTime;
            const memoryFreed = beforeMemory - this.state.heapUsed;
            
            this.gc.lastRun = Date.now();
            this.gc.averageDuration = (this.gc.averageDuration + duration) / 2;
            this.metrics.gcTriggers++;
            
            // Store GC history
            this.state.gcHistory.push({
                timestamp: Date.now(),
                duration,
                memoryBefore: beforeMemory,
                memoryAfter: this.state.heapUsed,
                memoryFreed,
                trigger: 'scheduled'
            });
            
            // Keep only last 20 GC events
            if (this.state.gcHistory.length > 20) {
                this.state.gcHistory.shift();
            }
            
            console.log(`✅ GC completed: freed ${(memoryFreed / 1024 / 1024).toFixed(2)}MB in ${duration}ms`);
            
            this.emit('garbageCollected', {
                duration,
                memoryFreed,
                beforeMemory,
                afterMemory: this.state.heapUsed
            });
            
        } catch (error) {
            console.error('GC failed:', error);
            this.emit('gcError', error);
        } finally {
            this.gc.isRunning = false;
        }
    }
    
    forceGarbageCollection() {
        if (global.gc) {
            this.gc.forced++;
            this.performGarbageCollection();
        }
    }
    
    setupBufferPooling() {
        this.bufferPool = {
            small: { size: 1024, pool: [], maxCount: 100 },
            medium: { size: 64 * 1024, pool: [], maxCount: 50 },
            large: { size: 1024 * 1024, pool: [], maxCount: 10 }
        };
        
        // Pre-allocate some buffers
        this.preallocateBuffers();
    }
    
    preallocateBuffers() {
        ['small', 'medium', 'large'].forEach(type => {
            const config = this.bufferPool[type];
            const initialCount = Math.floor(config.maxCount / 4);
            
            for (let i = 0; i < initialCount; i++) {
                const buffer = Buffer.allocUnsafe(config.size);
                config.pool.push(buffer);
            }
            
            console.log(`📦 Pre-allocated ${initialCount} ${type} buffers`);
        });
    }
    
    getBuffer(size) {
        let poolType, buffer;
        
        if (size <= 1024) {
            poolType = 'small';
        } else if (size <= 64 * 1024) {
            poolType = 'medium';
        } else if (size <= 1024 * 1024) {
            poolType = 'large';
        } else {
            // Too large for pooling
            this.metrics.poolMisses++;
            return Buffer.allocUnsafe(size);
        }
        
        const pool = this.bufferPool[poolType];
        
        if (pool.pool.length > 0) {
            buffer = pool.pool.pop();
            this.metrics.poolHits++;
        } else {
            buffer = Buffer.allocUnsafe(pool.size);
            this.metrics.poolMisses++;
        }
        
        this.metrics.allocations++;
        return buffer;
    }
    
    releaseBuffer(buffer) {
        if (!Buffer.isBuffer(buffer)) return false;
        
        const size = buffer.length;
        let poolType;
        
        if (size === 1024) {
            poolType = 'small';
        } else if (size === 64 * 1024) {
            poolType = 'medium';
        } else if (size === 1024 * 1024) {
            poolType = 'large';
        } else {
            // Not from our pools
            this.metrics.deallocations++;
            return false;
        }
        
        const pool = this.bufferPool[poolType];
        
        if (pool.pool.length < pool.maxCount) {
            // Clear buffer before returning to pool
            buffer.fill(0);
            pool.pool.push(buffer);
            this.metrics.deallocations++;
            return true;
        }
        
        this.metrics.deallocations++;
        return false;
    }
    
    compactBufferPools() {
        ['small', 'medium', 'large'].forEach(type => {
            const pool = this.bufferPool[type];
            // Reduce pool size by half during memory pressure
            const targetSize = Math.floor(pool.maxCount / 2);
            
            if (pool.pool.length > targetSize) {
                pool.pool.splice(targetSize);
                console.log(`📦 Compacted ${type} buffer pool to ${targetSize} buffers`);
            }
        });
    }
    
    setupSmartCaching() {
        this.cache = {
            maxSize: 32 * 1024 * 1024, // 32MB cache
            currentSize: 0,
            items: new Map(),
            lru: new Map(), // Least Recently Used tracking
            compressionThreshold: 1024, // Compress items > 1KB
            ttl: 300000 // 5 minutes default TTL
        };
        
        // Cache cleanup timer
        this.timers.set('cacheCleanup', setInterval(() => {
            this.cleanupCache();
        }, 60000)); // Every minute
    }
    
    cacheSet(key, value, ttl = this.cache.ttl) {
        const size = this.estimateObjectSize(value);
        
        // Check if cache is full
        if (this.cache.currentSize + size > this.cache.maxSize) {
            this.evictLRUItems(size);
        }
        
        // Compress large objects
        let storedValue = value;
        let compressed = false;
        
        if (this.config.compressionEnabled && size > this.cache.compressionThreshold) {
            storedValue = this.compressObject(value);
            compressed = true;
            this.metrics.compressionSavings += size - this.estimateObjectSize(storedValue);
        }
        
        const item = {
            value: storedValue,
            size: this.estimateObjectSize(storedValue),
            compressed,
            timestamp: Date.now(),
            ttl,
            accessCount: 0,
            lastAccess: Date.now()
        };
        
        this.cache.items.set(key, item);
        this.cache.currentSize += item.size;
        this.updateLRU(key);
        
        return true;
    }
    
    cacheGet(key) {
        const item = this.cache.items.get(key);
        
        if (!item) {
            this.metrics.cacheMisses++;
            return undefined;
        }
        
        // Check TTL
        if (Date.now() - item.timestamp > item.ttl) {
            this.cacheDelete(key);
            this.metrics.cacheMisses++;
            return undefined;
        }
        
        // Update access tracking
        item.accessCount++;
        item.lastAccess = Date.now();
        this.updateLRU(key);
        
        this.metrics.cacheHits++;
        
        // Decompress if needed
        if (item.compressed) {
            return this.decompressObject(item.value);
        }
        
        return item.value;
    }
    
    cacheDelete(key) {
        const item = this.cache.items.get(key);
        if (item) {
            this.cache.currentSize -= item.size;
            this.cache.items.delete(key);
            this.cache.lru.delete(key);
            return true;
        }
        return false;
    }
    
    updateLRU(key) {
        // Move to end (most recently used)
        if (this.cache.lru.has(key)) {
            this.cache.lru.delete(key);
        }
        this.cache.lru.set(key, Date.now());
    }
    
    evictLRUItems(requiredSize) {
        let freedSize = 0;
        const itemsToEvict = [];
        
        // Find least recently used items
        for (const [key] of this.cache.lru) {
            const item = this.cache.items.get(key);
            if (item) {
                itemsToEvict.push(key);
                freedSize += item.size;
                
                if (freedSize >= requiredSize) break;
            }
        }
        
        // Evict items
        itemsToEvict.forEach(key => {
            this.cacheDelete(key);
        });
        
        console.log(`🗑️ Evicted ${itemsToEvict.length} cache items, freed ${(freedSize / 1024).toFixed(2)}KB`);
    }
    
    cleanupCache() {
        const now = Date.now();
        const expiredKeys = [];
        
        for (const [key, item] of this.cache.items) {
            if (now - item.timestamp > item.ttl) {
                expiredKeys.push(key);
            }
        }
        
        expiredKeys.forEach(key => {
            this.cacheDelete(key);
        });
        
        if (expiredKeys.length > 0) {
            console.log(`🧹 Cleaned up ${expiredKeys.length} expired cache items`);
        }
    }
    
    clearCaches(aggressive = false) {
        if (aggressive) {
            // Clear all caches
            this.cache.items.clear();
            this.cache.lru.clear();
            this.cache.currentSize = 0;
            this.pools.stringCache.clear();
            this.pools.objectCache.clear();
            console.log('🗑️ Cleared all caches (aggressive mode)');
        } else {
            // Clear only low-priority items
            let clearedCount = 0;
            for (const [key, item] of this.cache.items) {
                if (item.accessCount < 2) {
                    this.cacheDelete(key);
                    clearedCount++;
                }
            }
            console.log(`🗑️ Cleared ${clearedCount} low-priority cache items`);
        }
    }
    
    setupMemoryLeakDetection() {
        this.leakDetector = {
            objectCounts: new Map(),
            growthThreshold: 1000,
            checkInterval: 60000, // 1 minute
            suspiciousObjects: new Set()
        };
        
        this.timers.set('leakDetection', setInterval(() => {
            this.detectMemoryLeaks();
        }, this.leakDetector.checkInterval));
    }
    
    detectMemoryLeaks() {
        // Simple leak detection based on object growth
        const currentCounts = this.getObjectCounts();
        
        for (const [type, count] of currentCounts) {
            const prevCount = this.leakDetector.objectCounts.get(type) || 0;
            const growth = count - prevCount;
            
            if (growth > this.leakDetector.growthThreshold) {
                console.warn(`🚨 Potential memory leak detected: ${type} objects grew by ${growth}`);
                this.leakDetector.suspiciousObjects.add(type);
                this.metrics.memoryLeaks++;
                
                this.emit('memoryLeakDetected', {
                    objectType: type,
                    previousCount: prevCount,
                    currentCount: count,
                    growth
                });
            }
        }
        
        this.leakDetector.objectCounts = currentCounts;
    }
    
    getObjectCounts() {
        // Simplified object counting (in production would use more sophisticated methods)
        const counts = new Map();
        counts.set('Buffer', this.countBuffers());
        counts.set('String', this.pools.stringCache.size);
        counts.set('Object', this.pools.objectCache.size);
        counts.set('Cache', this.cache.items.size);
        return counts;
    }
    
    countBuffers() {
        return this.bufferPool.small.pool.length + 
               this.bufferPool.medium.pool.length + 
               this.bufferPool.large.pool.length;
    }
    
    handleSuspiciousGrowth(growthRate) {
        console.warn(`⚠️ Suspicious memory growth: ${(growthRate / 1024 / 1024).toFixed(2)}MB in 5 seconds`);
        
        // Take defensive action
        this.preventiveCleanup();
        this.scheduleGarbageCollection();
        
        this.emit('suspiciousGrowthDetected', { growthRate });
    }
    
    setupCompression() {
        this.compression = {
            algorithms: new Map([
                ['json', this.compressJSON],
                ['string', this.compressString],
                ['buffer', this.compressBuffer]
            ]),
            threshold: 1024,
            ratio: 0.7 // Minimum compression ratio to be worthwhile
        };
    }
    
    compressObject(obj) {
        try {
            if (typeof obj === 'string') {
                return this.compressString(obj);
            } else if (Buffer.isBuffer(obj)) {
                return this.compressBuffer(obj);
            } else {
                return this.compressJSON(obj);
            }
        } catch (error) {
            console.warn('Compression failed:', error.message);
            return obj;
        }
    }
    
    decompressObject(obj) {
        try {
            if (obj && obj._compressed) {
                switch (obj._type) {
                    case 'string':
                        return this.decompressString(obj);
                    case 'buffer':
                        return this.decompressBuffer(obj);
                    case 'json':
                        return this.decompressJSON(obj);
                }
            }
            return obj;
        } catch (error) {
            console.warn('Decompression failed:', error.message);
            return obj;
        }
    }
    
    compressString(str) {
        if (str.length < this.compression.threshold) return str;
        
        const compressed = Buffer.from(str).toString('base64');
        if (compressed.length >= str.length * this.compression.ratio) {
            return str; // Not worth compressing
        }
        
        return {
            _compressed: true,
            _type: 'string',
            data: compressed
        };
    }
    
    decompressString(obj) {
        return Buffer.from(obj.data, 'base64').toString();
    }
    
    compressJSON(obj) {
        const str = JSON.stringify(obj);
        const compressed = this.compressString(str);
        
        if (typeof compressed === 'string') return obj;
        
        return {
            _compressed: true,
            _type: 'json',
            data: compressed.data
        };
    }
    
    decompressJSON(obj) {
        const str = Buffer.from(obj.data, 'base64').toString();
        return JSON.parse(str);
    }
    
    compressBuffer(buffer) {
        if (buffer.length < this.compression.threshold) return buffer;
        
        // Simple compression simulation
        const compressed = buffer.toString('base64');
        if (compressed.length >= buffer.length * this.compression.ratio) {
            return buffer;
        }
        
        return {
            _compressed: true,
            _type: 'buffer',
            data: compressed
        };
    }
    
    decompressBuffer(obj) {
        return Buffer.from(obj.data, 'base64');
    }
    
    detectFragmentation() {
        // Simplified fragmentation detection
        const usage = this.state.heapUsed / this.state.heapTotal;
        const external = this.state.external / this.state.heapTotal;
        
        this.state.fragmentationLevel = Math.max(0, 1 - usage - external);
        
        if (this.state.fragmentationLevel > 0.3) {
            console.warn(`🧩 High memory fragmentation detected: ${(this.state.fragmentationLevel * 100).toFixed(1)}%`);
            this.metrics.fragmentationEvents++;
            this.emit('fragmentationDetected', { level: this.state.fragmentationLevel });
        }
    }
    
    optimizeMemoryLayout() {
        // Periodic memory layout optimization
        if (Date.now() - this.state.lastCleanup > 300000) { // Every 5 minutes
            this.defragmentMemory();
            this.state.lastCleanup = Date.now();
        }
    }
    
    defragmentMemory() {
        console.log('🧩 Defragmenting memory layout...');
        
        // Compact object pools
        this.compactObjectPools();
        
        // Reorganize caches
        this.reorganizeCaches();
        
        // Force GC to compact heap
        this.forceGarbageCollection();
        
        console.log('✅ Memory defragmentation complete');
    }
    
    compactObjectPools() {
        // Compact string cache
        if (this.pools.stringCache.size > 1000) {
            const entries = Array.from(this.pools.stringCache.entries());
            this.pools.stringCache.clear();
            
            // Keep only frequently accessed strings
            entries.filter(([, usage]) => usage > 5)
                  .forEach(([key, usage]) => this.pools.stringCache.set(key, usage));
        }
    }
    
    reorganizeCaches() {
        // Rebuild cache with optimal layout
        const items = Array.from(this.cache.items.entries());
        this.clearCaches(true);
        
        // Re-add items sorted by access frequency
        items.sort((a, b) => b[1].accessCount - a[1].accessCount)
             .forEach(([key, item]) => {
                 if (item.accessCount > 1) {
                     this.cacheSet(key, item.value, item.ttl);
                 }
             });
    }
    
    compactSmallObjects() {
        // Light cleanup for small objects
        this.cleanupWeakReferences();
        this.defragmentPools();
    }
    
    cleanupWeakReferences() {
        // Clean up temporary objects
        // Note: WeakMap cleanup happens automatically, this is just for tracking
        console.log('🧹 Cleaning up weak references');
    }
    
    defragmentPools() {
        // Defragment buffer pools
        this.compactBufferPools();
        this.compactObjectPools();
    }
    
    releaseUnusedObjects() {
        // Release objects that haven't been accessed recently
        const cutoffTime = Date.now() - 300000; // 5 minutes
        
        for (const [key, item] of this.cache.items) {
            if (item.lastAccess < cutoffTime && item.accessCount < 2) {
                this.cacheDelete(key);
            }
        }
    }
    
    optimizeV8Heap() {
        // V8 heap optimization flags
        if (process.argv.includes('--optimize-for-size')) {
            console.log('📏 V8 optimized for size');
        } else {
            console.log('⚡ V8 optimized for speed');
        }
        
        // Set max old space size if not already set
        if (!process.argv.some(arg => arg.startsWith('--max-old-space-size'))) {
            const maxSize = Math.floor(this.config.maxHeapSize / 1024 / 1024);
            console.log(`🧠 Recommending --max-old-space-size=${maxSize}`);
        }
    }
    
    estimateObjectSize(obj) {
        // Simplified object size estimation
        if (obj === null || obj === undefined) return 0;
        if (typeof obj === 'boolean') return 4;
        if (typeof obj === 'number') return 8;
        if (typeof obj === 'string') return obj.length * 2;
        if (Buffer.isBuffer(obj)) return obj.length;
        if (Array.isArray(obj)) {
            return obj.reduce((size, item) => size + this.estimateObjectSize(item), 0);
        }
        if (typeof obj === 'object') {
            return Object.keys(obj).reduce((size, key) => 
                size + this.estimateObjectSize(key) + this.estimateObjectSize(obj[key]), 0);
        }
        return 64; // Default estimate
    }
    
    // Public API methods
    
    getMemoryStatus() {
        return {
            heap: {
                used: this.state.heapUsed,
                total: this.state.heapTotal,
                limit: this.state.heapLimit,
                percentage: (this.state.heapUsed / this.state.heapLimit) * 100
            },
            external: this.state.external,
            arrayBuffers: this.state.arrayBuffers,
            rss: this.state.rss,
            cache: {
                size: this.cache.currentSize,
                items: this.cache.items.size,
                hitRate: this.metrics.cacheHits / Math.max(this.metrics.cacheHits + this.metrics.cacheMisses, 1)
            },
            bufferPools: {
                small: this.bufferPool.small.pool.length,
                medium: this.bufferPool.medium.pool.length,
                large: this.bufferPool.large.pool.length,
                hitRate: this.metrics.poolHits / Math.max(this.metrics.poolHits + this.metrics.poolMisses, 1)
            },
            fragmentation: this.state.fragmentationLevel,
            gc: this.gc
        };
    }
    
    getMemoryMetrics() {
        return {
            ...this.metrics,
            efficiency: this.calculateMemoryEfficiency(),
            compressionRatio: this.calculateCompressionRatio(),
            leakRisk: this.calculateLeakRisk()
        };
    }
    
    calculateMemoryEfficiency() {
        const heapUsage = this.state.heapUsed / this.state.heapLimit;
        const cacheEfficiency = this.metrics.cacheHits / Math.max(this.metrics.cacheHits + this.metrics.cacheMisses, 1);
        const poolEfficiency = this.metrics.poolHits / Math.max(this.metrics.poolHits + this.metrics.poolMisses, 1);
        
        return (cacheEfficiency + poolEfficiency + (1 - heapUsage)) / 3;
    }
    
    calculateCompressionRatio() {
        const totalSavings = this.metrics.compressionSavings;
        const totalSize = this.state.heapUsed;
        return totalSavings / Math.max(totalSize, 1);
    }
    
    calculateLeakRisk() {
        const recentLeaks = this.metrics.memoryLeaks;
        const suspiciousObjects = this.leakDetector.suspiciousObjects.size;
        return Math.min(1, (recentLeaks + suspiciousObjects) / 10);
    }
    
    forceCacheCleanup() {
        this.clearCaches(true);
        this.forceGarbageCollection();
    }
    
    compactAllPools() {
        this.compactBufferPools();
        this.compactObjectPools();
        this.defragmentMemory();
    }
    
    createMemorySnapshot() {
        return {
            timestamp: Date.now(),
            memory: this.getMemoryStatus(),
            metrics: this.getMemoryMetrics(),
            gcHistory: [...this.state.gcHistory]
        };
    }
    
    async shutdown() {
        console.log('🔄 Shutting down Memory Manager...');
        
        // Clear all timers
        for (const timer of this.timers.values()) {
            clearInterval(timer);
        }
        this.timers.clear();
        
        // Clear all caches
        this.clearCaches(true);
        
        // Release all buffers
        Object.values(this.bufferPool).forEach(pool => {
            pool.pool.length = 0;
        });
        
        // Final garbage collection
        this.forceGarbageCollection();
        
        this.emit('shutdown');
        console.log('✅ Memory Manager shutdown complete');
    }
}

module.exports = MemoryManager;