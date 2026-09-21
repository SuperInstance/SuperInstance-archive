/**
 * Advanced Network Optimization Layer - Intelligent bandwidth management and connection optimization
 */

const { EventEmitter } = require('events');
const net = require('net');
const dns = require('dns');
const https = require('https');

class NetworkOptimizer extends EventEmitter {
    constructor(options = {}) {
        super();
        
        this.config = {
            maxConcurrentConnections: options.maxConcurrentConnections || 10,
            connectionTimeout: options.connectionTimeout || 30000,
            retryAttempts: options.retryAttempts || 3,
            bandwidthLimit: options.bandwidthLimit || 1024 * 1024, // 1MB/s
            compressionEnabled: options.compressionEnabled ?? true,
            cachingEnabled: options.cachingEnabled ?? true,
            priorityQueueing: options.priorityQueueing ?? true,
            adaptiveBitrate: options.adaptiveBitrate ?? true,
            networkQualityMonitoring: options.networkQualityMonitoring ?? true,
            ...options
        };
        
        this.state = {
            activeConnections: new Map(),
            connectionPool: new Map(),
            pendingRequests: new Map(),
            networkQuality: 'good',
            latency: 0,
            bandwidth: 0,
            packetLoss: 0,
            isThrottling: false,
            totalBytesIn: 0,
            totalBytesOut: 0,
            connectionStats: new Map(),
            dnsCache: new Map()
        };
        
        this.queues = {
            critical: [], // Real-time, critical requests
            high: [], // Interactive requests
            normal: [], // Standard requests  
            low: [], // Background requests
            batch: [] // Batch/bulk requests
        };
        
        this.metrics = {
            requestsSent: 0,
            requestsCompleted: 0,
            requestsFailed: 0,
            bytesTransferred: 0,
            averageLatency: 0,
            connectionReuses: 0,
            cacheHits: 0,
            compressionSavings: 0,
            throttlingEvents: 0,
            retryAttempts: 0
        };
        
        this.optimizations = {
            keepAlive: new Map(),
            compression: new Map(),
            caching: new Map(),
            prefetching: new Set(),
            bundling: new Map(),
            priorities: new Map()
        };
        
        this.timers = new Map();
        
        this.init();
    }
    
    init() {
        this.setupConnectionPooling();
        this.setupNetworkMonitoring();
        this.setupRequestQueuing();
        this.setupCaching();
        this.setupCompression();
        this.setupDNSOptimization();
        this.setupBandwidthThrottling();
        
        console.log('🌐 Network Optimizer initialized');
    }
    
    setupConnectionPooling() {
        this.connectionPool = {
            pools: new Map(), // hostname -> connection pool
            maxPoolSize: 5,
            maxIdleTime: 30000,
            cleanupInterval: 60000
        };
        
        // Cleanup idle connections
        this.timers.set('connectionCleanup', setInterval(() => {
            this.cleanupIdleConnections();
        }, this.connectionPool.cleanupInterval));
    }
    
    setupNetworkMonitoring() {
        this.networkMonitor = {
            measurements: [],
            lastCheck: Date.now(),
            testEndpoints: [
                'https://www.google.com/generate_204',
                'https://www.cloudflare.com/cdn-cgi/trace',
                'https://httpbin.org/delay/0'
            ],
            currentEndpoint: 0
        };
        
        this.timers.set('networkMonitor', setInterval(() => {
            this.measureNetworkQuality();
        }, 30000)); // Every 30 seconds
        
        // Initial measurement
        this.measureNetworkQuality();
    }
    
    async measureNetworkQuality() {
        try {
            const endpoint = this.networkMonitor.testEndpoints[this.networkMonitor.currentEndpoint];
            this.networkMonitor.currentEndpoint = (this.networkMonitor.currentEndpoint + 1) % this.networkMonitor.testEndpoints.length;
            
            const startTime = Date.now();
            
            const response = await this.makeRequest({
                url: endpoint,
                method: 'GET',
                timeout: 5000
            });
            
            const latency = Date.now() - startTime;
            
            // Update metrics
            this.state.latency = (this.state.latency + latency) / 2;
            this.metrics.averageLatency = this.state.latency;
            
            // Determine network quality
            this.updateNetworkQuality(latency, response);
            
            // Store measurement
            this.networkMonitor.measurements.push({
                timestamp: Date.now(),
                latency,
                endpoint,
                success: true
            });
            
            // Keep only last 20 measurements
            if (this.networkMonitor.measurements.length > 20) {
                this.networkMonitor.measurements.shift();
            }
            
            this.emit('networkQualityUpdated', {
                quality: this.state.networkQuality,
                latency: this.state.latency,
                bandwidth: this.state.bandwidth
            });
            
        } catch (error) {
            console.warn('Network quality measurement failed:', error.message);
            
            this.networkMonitor.measurements.push({
                timestamp: Date.now(),
                latency: -1,
                endpoint: this.networkMonitor.testEndpoints[this.networkMonitor.currentEndpoint - 1],
                success: false,
                error: error.message
            });
            
            this.handleNetworkError(error);
        }
    }
    
    updateNetworkQuality(latency, response) {
        let quality = 'good';
        
        if (latency > 1000) {
            quality = 'poor';
        } else if (latency > 500) {
            quality = 'fair';
        } else if (latency > 200) {
            quality = 'good';
        } else {
            quality = 'excellent';
        }
        
        if (this.state.networkQuality !== quality) {
            console.log(`📶 Network quality changed: ${this.state.networkQuality} → ${quality}`);
            this.state.networkQuality = quality;
            this.adaptToNetworkConditions(quality);
        }
    }
    
    adaptToNetworkConditions(quality) {
        switch (quality) {
            case 'poor':
                this.config.maxConcurrentConnections = 2;
                this.config.connectionTimeout = 60000;
                this.enableAggressiveOptimizations();
                break;
                
            case 'fair':
                this.config.maxConcurrentConnections = 5;
                this.config.connectionTimeout = 45000;
                this.enableModerateOptimizations();
                break;
                
            case 'good':
                this.config.maxConcurrentConnections = 10;
                this.config.connectionTimeout = 30000;
                this.enableStandardOptimizations();
                break;
                
            case 'excellent':
                this.config.maxConcurrentConnections = 15;
                this.config.connectionTimeout = 15000;
                this.enableMinimalOptimizations();
                break;
        }
        
        this.emit('networkAdaptation', { quality, config: this.config });
    }
    
    enableAggressiveOptimizations() {
        console.log('🔧 Enabling aggressive network optimizations');
        this.optimizations.compression.set('level', 9);
        this.optimizations.bundling.set('enabled', true);
        this.optimizations.bundling.set('size', 100); // Bundle 100 requests
        this.pauseLowPriorityRequests();
    }
    
    enableModerateOptimizations() {
        console.log('🔧 Enabling moderate network optimizations');
        this.optimizations.compression.set('level', 6);
        this.optimizations.bundling.set('enabled', true);
        this.optimizations.bundling.set('size', 50);
        this.throttleLowPriorityRequests();
    }
    
    enableStandardOptimizations() {
        console.log('🔧 Enabling standard network optimizations');
        this.optimizations.compression.set('level', 3);
        this.optimizations.bundling.set('enabled', false);
        this.resumeAllRequests();
    }
    
    enableMinimalOptimizations() {
        console.log('🔧 Enabling minimal network optimizations');
        this.optimizations.compression.set('level', 1);
        this.optimizations.bundling.set('enabled', false);
        this.resumeAllRequests();
    }
    
    setupRequestQueuing() {
        this.requestProcessor = {
            isProcessing: false,
            currentBatch: [],
            batchSize: 10,
            processingRate: 100 // requests per second
        };
        
        // Start request processing loop
        this.startRequestProcessor();
    }
    
    startRequestProcessor() {
        const processNext = async () => {
            if (this.requestProcessor.isProcessing) {
                setTimeout(processNext, 10);
                return;
            }
            
            this.requestProcessor.isProcessing = true;
            
            try {
                await this.processNextBatch();
            } catch (error) {
                console.error('Request processor error:', error);
            } finally {
                this.requestProcessor.isProcessing = false;
            }
            
            // Calculate delay based on processing rate
            const delay = 1000 / this.requestProcessor.processingRate;
            setTimeout(processNext, delay);
        };
        
        processNext();
    }
    
    async processNextBatch() {
        const batch = this.getNextRequestBatch();
        if (batch.length === 0) return;
        
        console.log(`📦 Processing batch of ${batch.length} requests`);
        
        // Process requests concurrently with connection limit
        const concurrencyLimit = Math.min(batch.length, this.config.maxConcurrentConnections);
        const promises = [];
        
        for (let i = 0; i < concurrencyLimit; i++) {
            promises.push(this.processRequestsConcurrently(batch, i, concurrencyLimit));
        }
        
        await Promise.allSettled(promises);
    }
    
    async processRequestsConcurrently(batch, startIndex, step) {
        for (let i = startIndex; i < batch.length; i += step) {
            const request = batch[i];
            try {
                await this.executeRequest(request);
            } catch (error) {
                this.handleRequestError(request, error);
            }
        }
    }
    
    getNextRequestBatch() {
        const batch = [];
        const maxBatchSize = this.requestProcessor.batchSize;
        
        // Process by priority
        for (const priority of ['critical', 'high', 'normal', 'low', 'batch']) {
            const queue = this.queues[priority];
            
            while (queue.length > 0 && batch.length < maxBatchSize) {
                batch.push(queue.shift());
            }
            
            if (batch.length >= maxBatchSize) break;
        }
        
        return batch;
    }
    
    async executeRequest(request) {
        const startTime = Date.now();
        
        try {
            // Check cache first
            if (this.config.cachingEnabled && request.method === 'GET') {
                const cached = this.getCachedResponse(request);
                if (cached) {
                    this.metrics.cacheHits++;
                    request.resolve(cached);
                    return;
                }
            }
            
            // Get or create connection
            const connection = await this.getConnection(request);
            
            // Execute request with optimizations
            const response = await this.sendOptimizedRequest(connection, request);
            
            // Cache response if applicable
            if (this.config.cachingEnabled && response.cacheable) {
                this.cacheResponse(request, response);
            }
            
            // Update metrics
            const duration = Date.now() - startTime;
            this.updateRequestMetrics(request, response, duration, true);
            
            // Release connection back to pool
            this.releaseConnection(request.hostname, connection);
            
            request.resolve(response);
            
        } catch (error) {
            const duration = Date.now() - startTime;
            this.updateRequestMetrics(request, null, duration, false);
            throw error;
        }
    }
    
    async getConnection(request) {
        const hostname = request.hostname;
        const pool = this.connectionPool.pools.get(hostname) || { connections: [], inUse: new Set() };
        
        // Try to reuse existing connection
        if (pool.connections.length > 0) {
            const connection = pool.connections.pop();
            pool.inUse.add(connection);
            this.metrics.connectionReuses++;
            return connection;
        }
        
        // Create new connection
        const connection = await this.createConnection(request);
        pool.inUse.add(connection);
        
        // Store pool reference
        if (!this.connectionPool.pools.has(hostname)) {
            this.connectionPool.pools.set(hostname, pool);
        }
        
        return connection;
    }
    
    async createConnection(request) {
        return new Promise((resolve, reject) => {
            const options = {
                host: request.hostname,
                port: request.port || 443,
                timeout: this.config.connectionTimeout
            };
            
            const connection = net.createConnection(options);
            
            connection.on('connect', () => {
                connection.lastUsed = Date.now();
                connection.hostname = request.hostname;
                resolve(connection);
            });
            
            connection.on('error', reject);
            connection.on('timeout', () => {
                reject(new Error('Connection timeout'));
            });
        });
    }
    
    releaseConnection(hostname, connection) {
        const pool = this.connectionPool.pools.get(hostname);
        if (!pool) return;
        
        pool.inUse.delete(connection);
        
        // Return to pool if still healthy and under limit
        if (connection.readyState === 'open' && pool.connections.length < this.connectionPool.maxPoolSize) {
            connection.lastUsed = Date.now();
            pool.connections.push(connection);
        } else {
            connection.destroy();
        }
    }
    
    cleanupIdleConnections() {
        const now = Date.now();
        let cleanedUp = 0;
        
        for (const [hostname, pool] of this.connectionPool.pools) {
            pool.connections = pool.connections.filter(connection => {
                const isIdle = now - connection.lastUsed > this.connectionPool.maxIdleTime;
                if (isIdle) {
                    connection.destroy();
                    cleanedUp++;
                    return false;
                }
                return true;
            });
            
            // Remove empty pools
            if (pool.connections.length === 0 && pool.inUse.size === 0) {
                this.connectionPool.pools.delete(hostname);
            }
        }
        
        if (cleanedUp > 0) {
            console.log(`🧹 Cleaned up ${cleanedUp} idle connections`);
        }
    }
    
    async sendOptimizedRequest(connection, request) {
        // Apply compression if enabled
        if (this.config.compressionEnabled) {
            request = this.applyCompression(request);
        }
        
        // Apply bandwidth throttling if needed
        if (this.state.isThrottling) {
            await this.throttleRequest(request);
        }
        
        // Send request with retries
        return await this.sendWithRetries(connection, request);
    }
    
    applyCompression(request) {
        if (!request.body || request.body.length < 1024) {
            return request; // Don't compress small payloads
        }
        
        const compressionLevel = this.optimizations.compression.get('level') || 6;
        
        // Simulate compression (in production would use actual compression)
        const originalSize = request.body.length;
        const compressedSize = Math.floor(originalSize * (1 - compressionLevel / 10));
        
        this.metrics.compressionSavings += originalSize - compressedSize;
        
        return {
            ...request,
            body: request.body.substring(0, compressedSize),
            headers: {
                ...request.headers,
                'content-encoding': 'gzip',
                'content-length': compressedSize
            }
        };
    }
    
    async throttleRequest(request) {
        const priority = request.priority || 'normal';
        const delays = {
            critical: 0,
            high: 10,
            normal: 50,
            low: 200,
            batch: 500
        };
        
        const delay = delays[priority] || 50;
        
        if (delay > 0) {
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    
    async sendWithRetries(connection, request) {
        let lastError = null;
        
        for (let attempt = 0; attempt < this.config.retryAttempts; attempt++) {
            try {
                return await this.sendRequest(connection, request);
            } catch (error) {
                lastError = error;
                this.metrics.retryAttempts++;
                
                if (attempt < this.config.retryAttempts - 1) {
                    const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
                    console.log(`🔄 Retry attempt ${attempt + 1} in ${delay}ms`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }
        
        throw lastError;
    }
    
    async sendRequest(connection, request) {
        return new Promise((resolve, reject) => {
            // Simulate HTTP request (in production would use actual HTTP client)
            const startTime = Date.now();
            
            setTimeout(() => {
                const duration = Date.now() - startTime;
                const responseSize = Math.floor(Math.random() * 10000) + 1000;
                
                this.state.totalBytesOut += request.body?.length || 0;
                this.state.totalBytesIn += responseSize;
                this.metrics.bytesTransferred += responseSize;
                
                const response = {
                    status: 200,
                    headers: { 'content-type': 'application/json' },
                    body: 'x'.repeat(responseSize),
                    duration,
                    cacheable: request.method === 'GET',
                    size: responseSize
                };
                
                resolve(response);
            }, Math.random() * 100 + 50); // Random delay 50-150ms
        });
    }
    
    setupCaching() {
        this.cache = {
            storage: new Map(),
            maxSize: 10 * 1024 * 1024, // 10MB
            currentSize: 0,
            defaultTTL: 300000, // 5 minutes
            lru: new Map()
        };
        
        // Cache cleanup timer
        this.timers.set('cacheCleanup', setInterval(() => {
            this.cleanupExpiredCache();
        }, 60000));
    }
    
    getCachedResponse(request) {
        const key = this.generateCacheKey(request);
        const entry = this.cache.storage.get(key);
        
        if (!entry) return null;
        
        // Check TTL
        if (Date.now() > entry.expiry) {
            this.cache.storage.delete(key);
            this.cache.lru.delete(key);
            this.cache.currentSize -= entry.size;
            return null;
        }
        
        // Update LRU
        this.cache.lru.delete(key);
        this.cache.lru.set(key, Date.now());
        
        return entry.response;
    }
    
    cacheResponse(request, response) {
        const key = this.generateCacheKey(request);
        const size = response.size || 0;
        
        // Check if we have space
        if (this.cache.currentSize + size > this.cache.maxSize) {
            this.evictLRUEntries(size);
        }
        
        const entry = {
            response,
            size,
            expiry: Date.now() + this.cache.defaultTTL,
            createdAt: Date.now()
        };
        
        this.cache.storage.set(key, entry);
        this.cache.lru.set(key, Date.now());
        this.cache.currentSize += size;
    }
    
    generateCacheKey(request) {
        return `${request.method}:${request.hostname}${request.path}:${JSON.stringify(request.query || {})}`;
    }
    
    evictLRUEntries(requiredSize) {
        let freedSize = 0;
        
        for (const [key] of this.cache.lru) {
            const entry = this.cache.storage.get(key);
            if (entry) {
                this.cache.storage.delete(key);
                this.cache.lru.delete(key);
                this.cache.currentSize -= entry.size;
                freedSize += entry.size;
                
                if (freedSize >= requiredSize) break;
            }
        }
    }
    
    cleanupExpiredCache() {
        const now = Date.now();
        let cleanedCount = 0;
        
        for (const [key, entry] of this.cache.storage) {
            if (now > entry.expiry) {
                this.cache.storage.delete(key);
                this.cache.lru.delete(key);
                this.cache.currentSize -= entry.size;
                cleanedCount++;
            }
        }
        
        if (cleanedCount > 0) {
            console.log(`🗑️ Cleaned ${cleanedCount} expired cache entries`);
        }
    }
    
    setupCompression() {
        this.compressionStrategies = new Map([
            ['gzip', { level: 6, threshold: 1024 }],
            ['deflate', { level: 6, threshold: 1024 }],
            ['brotli', { level: 4, threshold: 1024 }]
        ]);
        
        // Default to gzip
        this.optimizations.compression.set('algorithm', 'gzip');
        this.optimizations.compression.set('level', 6);
    }
    
    setupDNSOptimization() {
        this.dnsOptimizer = {
            cache: new Map(),
            ttl: 300000, // 5 minutes
            prefetchDomains: new Set(),
            failureCache: new Map()
        };
        
        // Override DNS resolution with caching
        this.originalDnsLookup = dns.lookup;
        dns.lookup = this.cachedDnsLookup.bind(this);
    }
    
    cachedDnsLookup(hostname, options, callback) {
        if (typeof options === 'function') {
            callback = options;
            options = {};
        }
        
        const cacheKey = `${hostname}:${JSON.stringify(options)}`;
        const cached = this.dnsOptimizer.cache.get(cacheKey);
        
        if (cached && Date.now() < cached.expiry) {
            setImmediate(() => callback(null, cached.address, cached.family));
            return;
        }
        
        // Check failure cache
        const failure = this.dnsOptimizer.failureCache.get(hostname);
        if (failure && Date.now() < failure.expiry) {
            setImmediate(() => callback(failure.error));
            return;
        }
        
        this.originalDnsLookup(hostname, options, (error, address, family) => {
            if (error) {
                // Cache failures temporarily
                this.dnsOptimizer.failureCache.set(hostname, {
                    error,
                    expiry: Date.now() + 30000 // 30 seconds
                });
            } else {
                // Cache success
                this.dnsOptimizer.cache.set(cacheKey, {
                    address,
                    family,
                    expiry: Date.now() + this.dnsOptimizer.ttl
                });
            }
            
            callback(error, address, family);
        });
    }
    
    setupBandwidthThrottling() {
        this.bandwidthThrottler = {
            bucket: this.config.bandwidthLimit,
            lastRefill: Date.now(),
            refillRate: this.config.bandwidthLimit, // bytes per second
            minBucket: 1024 // Minimum 1KB available
        };
        
        this.timers.set('bandwidthThrottler', setInterval(() => {
            this.refillBandwidthBucket();
        }, 1000)); // Refill every second
    }
    
    refillBandwidthBucket() {
        const now = Date.now();
        const elapsed = (now - this.bandwidthThrottler.lastRefill) / 1000;
        const refillAmount = this.bandwidthThrottler.refillRate * elapsed;
        
        this.bandwidthThrottler.bucket = Math.min(
            this.config.bandwidthLimit,
            this.bandwidthThrottler.bucket + refillAmount
        );
        
        this.bandwidthThrottler.lastRefill = now;
        
        // Check if we should stop throttling
        if (this.state.isThrottling && this.bandwidthThrottler.bucket > this.bandwidthThrottler.minBucket * 10) {
            this.state.isThrottling = false;
            console.log('🌐 Bandwidth throttling disabled');
        }
    }
    
    consumeBandwidth(bytes) {
        if (this.bandwidthThrottler.bucket < bytes) {
            this.state.isThrottling = true;
            this.metrics.throttlingEvents++;
            return false; // Not enough bandwidth
        }
        
        this.bandwidthThrottler.bucket -= bytes;
        return true;
    }
    
    handleNetworkError(error) {
        console.warn('Network error detected:', error.message);
        
        // Adapt to poor network conditions
        this.state.networkQuality = 'poor';
        this.adaptToNetworkConditions('poor');
        
        this.emit('networkError', error);
    }
    
    handleRequestError(request, error) {
        this.metrics.requestsFailed++;
        console.error(`Request failed: ${request.method} ${request.url}`, error.message);
        
        if (request.reject) {
            request.reject(error);
        }
        
        this.emit('requestFailed', { request, error });
    }
    
    updateRequestMetrics(request, response, duration, success) {
        if (success) {
            this.metrics.requestsCompleted++;
        } else {
            this.metrics.requestsFailed++;
        }
        
        this.metrics.requestsSent++;
        this.metrics.averageLatency = (this.metrics.averageLatency + duration) / 2;
    }
    
    pauseLowPriorityRequests() {
        console.log('⏸️ Pausing low priority requests');
        this.queues.low = [];
        this.queues.batch = [];
    }
    
    throttleLowPriorityRequests() {
        console.log('🐌 Throttling low priority requests');
        // Move low priority to batch
        this.queues.batch = [...this.queues.batch, ...this.queues.low];
        this.queues.low = [];
    }
    
    resumeAllRequests() {
        console.log('▶️ Resuming all request priorities');
        // No specific action needed, processing continues normally
    }
    
    // Public API methods
    
    async request(options) {
        return new Promise((resolve, reject) => {
            const request = this.createRequest(options, resolve, reject);
            this.queueRequest(request);
        });
    }
    
    createRequest(options, resolve, reject) {
        const url = new URL(options.url);
        
        return {
            id: `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            method: options.method || 'GET',
            url: options.url,
            hostname: url.hostname,
            port: url.port,
            path: url.pathname + url.search,
            query: Object.fromEntries(url.searchParams),
            headers: options.headers || {},
            body: options.body,
            priority: options.priority || 'normal',
            timeout: options.timeout || this.config.connectionTimeout,
            createdAt: Date.now(),
            resolve,
            reject
        };
    }
    
    queueRequest(request) {
        const priority = request.priority;
        
        if (!this.queues[priority]) {
            console.warn(`Unknown priority: ${priority}, using 'normal'`);
            request.priority = 'normal';
        }
        
        this.queues[request.priority].push(request);
        this.state.pendingRequests.set(request.id, request);
        
        this.emit('requestQueued', request);
    }
    
    makeRequest(options) {
        return this.request(options);
    }
    
    getNetworkStatus() {
        return {
            quality: this.state.networkQuality,
            latency: this.state.latency,
            bandwidth: this.state.bandwidth,
            packetLoss: this.state.packetLoss,
            isThrottling: this.state.isThrottling,
            activeConnections: this.state.activeConnections.size,
            pendingRequests: this.state.pendingRequests.size,
            queueLengths: {
                critical: this.queues.critical.length,
                high: this.queues.high.length,
                normal: this.queues.normal.length,
                low: this.queues.low.length,
                batch: this.queues.batch.length
            }
        };
    }
    
    getNetworkMetrics() {
        return {
            ...this.metrics,
            efficiency: this.calculateNetworkEfficiency(),
            cacheEfficiency: this.calculateCacheEfficiency(),
            compressionRatio: this.calculateCompressionRatio()
        };
    }
    
    calculateNetworkEfficiency() {
        if (this.metrics.requestsSent === 0) return 1;
        
        const successRate = this.metrics.requestsCompleted / this.metrics.requestsSent;
        const latencyEfficiency = Math.max(0, 1 - (this.state.latency / 1000)); // Normalize to 1 second
        
        return (successRate + latencyEfficiency) / 2;
    }
    
    calculateCacheEfficiency() {
        const totalRequests = this.metrics.requestsCompleted + this.metrics.requestsFailed;
        if (totalRequests === 0) return 0;
        
        return this.metrics.cacheHits / totalRequests;
    }
    
    calculateCompressionRatio() {
        if (this.metrics.bytesTransferred === 0) return 0;
        
        return this.metrics.compressionSavings / this.metrics.bytesTransferred;
    }
    
    enableBandwidthLimit(limitBytes) {
        this.config.bandwidthLimit = limitBytes;
        this.bandwidthThrottler.refillRate = limitBytes;
        console.log(`🌐 Bandwidth limit set to ${(limitBytes / 1024).toFixed(2)}KB/s`);
    }
    
    disableBandwidthLimit() {
        this.config.bandwidthLimit = Number.MAX_SAFE_INTEGER;
        this.bandwidthThrottler.refillRate = Number.MAX_SAFE_INTEGER;
        this.state.isThrottling = false;
        console.log('🌐 Bandwidth limit disabled');
    }
    
    clearCache() {
        this.cache.storage.clear();
        this.cache.lru.clear();
        this.cache.currentSize = 0;
        console.log('🗑️ Network cache cleared');
    }
    
    prefetchUrl(url, priority = 'low') {
        this.request({
            url,
            method: 'GET',
            priority
        }).catch(error => {
            console.warn('Prefetch failed:', url, error.message);
        });
    }
    
    createNetworkSnapshot() {
        return {
            timestamp: Date.now(),
            status: this.getNetworkStatus(),
            metrics: this.getNetworkMetrics(),
            measurements: [...this.networkMonitor.measurements]
        };
    }
    
    async shutdown() {
        console.log('🔄 Shutting down Network Optimizer...');
        
        // Restore original DNS lookup
        dns.lookup = this.originalDnsLookup;
        
        // Clear all timers
        for (const timer of this.timers.values()) {
            clearInterval(timer);
        }
        this.timers.clear();
        
        // Close all connections
        for (const pool of this.connectionPool.pools.values()) {
            pool.connections.forEach(connection => connection.destroy());
            pool.connections.length = 0;
        }
        
        // Clear caches
        this.clearCache();
        this.dnsOptimizer.cache.clear();
        
        // Reject pending requests
        for (const request of this.state.pendingRequests.values()) {
            if (request.reject) {
                request.reject(new Error('Network optimizer shutting down'));
            }
        }
        
        this.emit('shutdown');
        console.log('✅ Network Optimizer shutdown complete');
    }
}

module.exports = NetworkOptimizer;