const v8 = require('v8');
const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');

class MemoryLeakDetector extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      // Detection thresholds
      heapGrowthThreshold: config.heapGrowthThreshold || 50 * 1024 * 1024, // 50MB
      heapUsageThreshold: config.heapUsageThreshold || 0.8, // 80% of max heap
      memoryGrowthRate: config.memoryGrowthRate || 10 * 1024 * 1024, // 10MB/minute
      consecutiveGrowthLimit: config.consecutiveGrowthLimit || 5, // 5 consecutive increases
      
      // Monitoring intervals
      monitoringInterval: config.monitoringInterval || 30000, // 30 seconds
      detailedAnalysisInterval: config.detailedAnalysisInterval || 300000, // 5 minutes
      gcForceInterval: config.gcForceInterval || 600000, // 10 minutes
      
      // Heap snapshot settings
      enableHeapSnapshots: config.enableHeapSnapshots ?? true,
      maxHeapSnapshots: config.maxHeapSnapshots || 10,
      heapSnapshotPath: config.heapSnapshotPath || './heap-snapshots',
      
      // Alerting
      enableAlerts: config.enableAlerts ?? true,
      alertThresholds: config.alertThresholds || {
        warning: 0.7,  // 70% heap usage
        critical: 0.9  // 90% heap usage
      },
      
      // Analysis
      enableObjectTracking: config.enableObjectTracking ?? true,
      enableEventListenerTracking: config.enableEventListenerTracking ?? true,
      enableTimerTracking: config.enableTimerTracking ?? true,
      
      ...config
    };

    this.memoryHistory = [];
    this.heapSnapshots = [];
    this.objectCounts = new Map();
    this.eventListeners = new Map();
    this.timers = new Map();
    this.leaks = [];
    
    this.stats = {
      totalChecks: 0,
      leaksDetected: 0,
      heapSnapshotsTaken: 0,
      gcForced: 0,
      alertsSent: 0
    };

    this.consecutiveGrowth = 0;
    this.lastMemoryCheck = null;
    this.monitoringTimer = null;
    this.detailedAnalysisTimer = null;
    this.gcTimer = null;

    this.initializeDetection();
  }

  // Initialize memory leak detection
  initializeDetection() {
    this.ensureHeapSnapshotDirectory();
    this.startMonitoring();
    this.setupGlobalErrorHandling();
    
    if (this.config.enableObjectTracking) {
      this.startObjectTracking();
    }
    
    if (this.config.enableEventListenerTracking) {
      this.startEventListenerTracking();
    }
    
    if (this.config.enableTimerTracking) {
      this.startTimerTracking();
    }
  }

  // Ensure heap snapshot directory exists
  ensureHeapSnapshotDirectory() {
    if (this.config.enableHeapSnapshots) {
      const dir = this.config.heapSnapshotPath;
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    }
  }

  // Start continuous monitoring
  startMonitoring() {
    this.monitoringTimer = setInterval(() => {
      this.checkMemoryUsage();
    }, this.config.monitoringInterval);

    this.detailedAnalysisTimer = setInterval(() => {
      this.performDetailedAnalysis();
    }, this.config.detailedAnalysisInterval);

    if (global.gc) {
      this.gcTimer = setInterval(() => {
        this.forceGarbageCollection();
      }, this.config.gcForceInterval);
    }
  }

  // Check current memory usage
  checkMemoryUsage() {
    this.stats.totalChecks++;
    
    const memoryUsage = process.memoryUsage();
    const heapStats = v8.getHeapStatistics();
    
    const currentMemory = {
      timestamp: Date.now(),
      rss: memoryUsage.rss,
      heapUsed: memoryUsage.heapUsed,
      heapTotal: memoryUsage.heapTotal,
      external: memoryUsage.external,
      arrayBuffers: memoryUsage.arrayBuffers,
      heapSizeLimit: heapStats.heap_size_limit,
      usedHeapRatio: memoryUsage.heapUsed / heapStats.heap_size_limit
    };

    this.memoryHistory.push(currentMemory);
    
    // Keep only recent history
    if (this.memoryHistory.length > 100) {
      this.memoryHistory.shift();
    }

    // Analyze for potential leaks
    this.analyzeMemoryTrend(currentMemory);
    
    // Check thresholds
    this.checkAlertThresholds(currentMemory);
    
    this.lastMemoryCheck = currentMemory;
    this.emit('memoryCheck', currentMemory);
  }

  // Analyze memory usage trends
  analyzeMemoryTrend(currentMemory) {
    if (this.memoryHistory.length < 2) return;

    const previousMemory = this.memoryHistory[this.memoryHistory.length - 2];
    const heapGrowth = currentMemory.heapUsed - previousMemory.heapUsed;
    const timeElapsed = currentMemory.timestamp - previousMemory.timestamp;
    
    // Check for significant heap growth
    if (heapGrowth > this.config.heapGrowthThreshold) {
      this.consecutiveGrowth++;
      
      if (this.consecutiveGrowth >= this.config.consecutiveGrowthLimit) {
        this.detectPotentialLeak('heap_growth', {
          growth: heapGrowth,
          consecutiveGrowth: this.consecutiveGrowth,
          growthRate: heapGrowth / (timeElapsed / 1000 / 60) // MB per minute
        });
      }
    } else {
      this.consecutiveGrowth = 0;
    }

    // Check growth rate
    if (this.memoryHistory.length >= 5) {
      const fiveMinutesAgo = this.memoryHistory[this.memoryHistory.length - 5];
      const totalGrowth = currentMemory.heapUsed - fiveMinutesAgo.heapUsed;
      const totalTime = currentMemory.timestamp - fiveMinutesAgo.timestamp;
      const growthRate = totalGrowth / (totalTime / 1000 / 60); // MB per minute
      
      if (growthRate > this.config.memoryGrowthRate) {
        this.detectPotentialLeak('growth_rate', {
          growthRate,
          timespan: totalTime,
          totalGrowth
        });
      }
    }
  }

  // Check alert thresholds
  checkAlertThresholds(currentMemory) {
    const heapRatio = currentMemory.usedHeapRatio;
    
    if (heapRatio >= this.config.alertThresholds.critical) {
      this.sendAlert('critical', 'Critical memory usage detected', currentMemory);
    } else if (heapRatio >= this.config.alertThresholds.warning) {
      this.sendAlert('warning', 'High memory usage detected', currentMemory);
    }
  }

  // Send memory alert
  sendAlert(level, message, memoryData) {
    if (!this.config.enableAlerts) return;
    
    this.stats.alertsSent++;
    
    const alert = {
      level,
      message,
      timestamp: Date.now(),
      memoryData,
      heapUsagePercent: (memoryData.usedHeapRatio * 100).toFixed(2)
    };
    
    this.emit('memoryAlert', alert);
    
    if (level === 'critical' && this.config.enableHeapSnapshots) {
      this.takeHeapSnapshot('critical_memory');
    }
  }

  // Detect potential memory leak
  detectPotentialLeak(type, details) {
    this.stats.leaksDetected++;
    
    const leak = {
      id: `leak_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      timestamp: Date.now(),
      details,
      memoryAtDetection: this.lastMemoryCheck,
      stackTrace: this.captureStackTrace()
    };
    
    this.leaks.push(leak);
    
    // Keep only recent leaks
    if (this.leaks.length > 50) {
      this.leaks.shift();
    }
    
    this.emit('leakDetected', leak);
    
    if (this.config.enableHeapSnapshots) {
      this.takeHeapSnapshot(`leak_${type}`);
    }
  }

  // Perform detailed memory analysis
  async performDetailedAnalysis() {
    const analysis = {
      timestamp: Date.now(),
      objectCounts: this.analyzeObjectCounts(),
      eventListeners: this.analyzeEventListeners(),
      timers: this.analyzeTimers(),
      heapSpaces: this.analyzeHeapSpaces(),
      largestObjects: this.findLargestObjects()
    };
    
    this.emit('detailedAnalysis', analysis);
    
    // Check for suspicious patterns
    this.checkSuspiciousPatterns(analysis);
    
    return analysis;
  }

  // Analyze object counts
  analyzeObjectCounts() {
    if (!this.config.enableObjectTracking) return {};
    
    const counts = {};
    for (const [type, count] of this.objectCounts.entries()) {
      counts[type] = count;
    }
    
    return counts;
  }

  // Analyze event listeners
  analyzeEventListeners() {
    if (!this.config.enableEventListenerTracking) return {};
    
    const listeners = {};
    for (const [event, count] of this.eventListeners.entries()) {
      listeners[event] = count;
    }
    
    return listeners;
  }

  // Analyze active timers
  analyzeTimers() {
    if (!this.config.enableTimerTracking) return {};
    
    const timers = {};
    for (const [type, count] of this.timers.entries()) {
      timers[type] = count;
    }
    
    return timers;
  }

  // Analyze heap spaces
  analyzeHeapSpaces() {
    const heapSpaces = v8.getHeapSpaceStatistics();
    return heapSpaces.map(space => ({
      name: space.space_name,
      size: space.space_size,
      used: space.space_used_size,
      available: space.space_available_size,
      physical: space.physical_space_size
    }));
  }

  // Find largest objects in heap
  findLargestObjects() {
    // This is a simplified implementation
    // In practice, you'd use heap snapshots for detailed object analysis
    return {
      note: 'Detailed object analysis requires heap snapshot examination'
    };
  }

  // Check for suspicious patterns
  checkSuspiciousPatterns(analysis) {
    // Check for excessive event listeners
    Object.entries(analysis.eventListeners).forEach(([event, count]) => {
      if (count > 100) {
        this.detectPotentialLeak('excessive_listeners', {
          eventType: event,
          count
        });
      }
    });
    
    // Check for timer leaks
    Object.entries(analysis.timers).forEach(([type, count]) => {
      if (count > 1000) {
        this.detectPotentialLeak('timer_leak', {
          timerType: type,
          count
        });
      }
    });
  }

  // Take heap snapshot
  async takeHeapSnapshot(reason = 'manual') {
    if (!this.config.enableHeapSnapshots) return null;
    
    this.stats.heapSnapshotsTaken++;
    
    const timestamp = Date.now();
    const filename = `heap-${timestamp}-${reason}.heapsnapshot`;
    const filepath = path.join(this.config.heapSnapshotPath, filename);
    
    try {
      const heapSnapshot = v8.getHeapSnapshot();
      const writeStream = fs.createWriteStream(filepath);
      
      await new Promise((resolve, reject) => {
        heapSnapshot.pipe(writeStream);
        writeStream.on('finish', resolve);
        writeStream.on('error', reject);
      });
      
      const snapshot = {
        timestamp,
        filename,
        filepath,
        reason,
        size: fs.statSync(filepath).size
      };
      
      this.heapSnapshots.push(snapshot);
      
      // Remove old snapshots if we exceed the limit
      while (this.heapSnapshots.length > this.config.maxHeapSnapshots) {
        const oldSnapshot = this.heapSnapshots.shift();
        try {
          fs.unlinkSync(oldSnapshot.filepath);
        } catch (error) {
          console.warn('Failed to delete old heap snapshot:', error.message);
        }
      }
      
      this.emit('heapSnapshotTaken', snapshot);
      return snapshot;
      
    } catch (error) {
      this.emit('heapSnapshotError', { reason, error });
      return null;
    }
  }

  // Force garbage collection
  forceGarbageCollection() {
    if (!global.gc) {
      console.warn('Garbage collection not exposed. Run with --expose-gc flag.');
      return;
    }
    
    this.stats.gcForced++;
    
    const beforeGC = process.memoryUsage();
    global.gc();
    const afterGC = process.memoryUsage();
    
    const collected = {
      heapUsed: beforeGC.heapUsed - afterGC.heapUsed,
      heapTotal: beforeGC.heapTotal - afterGC.heapTotal,
      rss: beforeGC.rss - afterGC.rss
    };
    
    this.emit('garbageCollected', { beforeGC, afterGC, collected });
  }

  // Start object tracking
  startObjectTracking() {
    const originalCreate = Object.create;
    const detector = this;
    
    Object.create = function(prototype, properties) {
      const obj = originalCreate.call(this, prototype, properties);
      detector.trackObject(obj.constructor.name || 'Object');
      return obj;
    };
  }

  // Track object creation
  trackObject(type) {
    const current = this.objectCounts.get(type) || 0;
    this.objectCounts.set(type, current + 1);
  }

  // Start event listener tracking
  startEventListenerTracking() {
    const EventEmitter = require('events');
    const originalAddListener = EventEmitter.prototype.addListener;
    const originalRemoveListener = EventEmitter.prototype.removeListener;
    const detector = this;
    
    EventEmitter.prototype.addListener = function(event, listener) {
      detector.trackEventListener(event, 'add');
      return originalAddListener.call(this, event, listener);
    };
    
    EventEmitter.prototype.removeListener = function(event, listener) {
      detector.trackEventListener(event, 'remove');
      return originalRemoveListener.call(this, event, listener);
    };
  }

  // Track event listener changes
  trackEventListener(event, action) {
    const key = `${event}_listeners`;
    const current = this.eventListeners.get(key) || 0;
    
    if (action === 'add') {
      this.eventListeners.set(key, current + 1);
    } else if (action === 'remove') {
      this.eventListeners.set(key, Math.max(0, current - 1));
    }
  }

  // Start timer tracking
  startTimerTracking() {
    const originalSetTimeout = global.setTimeout;
    const originalSetInterval = global.setInterval;
    const originalClearTimeout = global.clearTimeout;
    const originalClearInterval = global.clearInterval;
    const detector = this;
    
    global.setTimeout = function(...args) {
      detector.trackTimer('timeout', 'create');
      return originalSetTimeout.apply(this, args);
    };
    
    global.setInterval = function(...args) {
      detector.trackTimer('interval', 'create');
      return originalSetInterval.apply(this, args);
    };
    
    global.clearTimeout = function(...args) {
      detector.trackTimer('timeout', 'clear');
      return originalClearTimeout.apply(this, args);
    };
    
    global.clearInterval = function(...args) {
      detector.trackTimer('interval', 'clear');
      return originalClearInterval.apply(this, args);
    };
  }

  // Track timer creation/clearing
  trackTimer(type, action) {
    const current = this.timers.get(type) || 0;
    
    if (action === 'create') {
      this.timers.set(type, current + 1);
    } else if (action === 'clear') {
      this.timers.set(type, Math.max(0, current - 1));
    }
  }

  // Setup global error handling
  setupGlobalErrorHandling() {
    process.on('uncaughtException', (error) => {
      this.emit('uncaughtException', { error, memory: process.memoryUsage() });
    });
    
    process.on('unhandledRejection', (reason, promise) => {
      this.emit('unhandledRejection', { reason, promise, memory: process.memoryUsage() });
    });
  }

  // Capture stack trace
  captureStackTrace() {
    const obj = {};
    Error.captureStackTrace(obj, this.captureStackTrace);
    return obj.stack;
  }

  // Generate memory report
  generateReport() {
    const currentMemory = process.memoryUsage();
    const heapStats = v8.getHeapStatistics();
    
    return {
      timestamp: new Date().toISOString(),
      currentMemory: {
        ...currentMemory,
        heapUsagePercent: (currentMemory.heapUsed / heapStats.heap_size_limit * 100).toFixed(2)
      },
      heapStatistics: heapStats,
      memoryTrend: this.analyzeMemoryTrend(),
      leaks: this.leaks.slice(-10), // Last 10 leaks
      statistics: this.stats,
      objectCounts: Object.fromEntries(this.objectCounts),
      eventListeners: Object.fromEntries(this.eventListeners),
      timers: Object.fromEntries(this.timers),
      heapSnapshots: this.heapSnapshots.map(s => ({
        timestamp: new Date(s.timestamp).toISOString(),
        reason: s.reason,
        size: this.formatBytes(s.size)
      }))
    };
  }

  // Analyze memory trend
  analyzeMemoryTrend() {
    if (this.memoryHistory.length < 2) {
      return { trend: 'insufficient_data' };
    }
    
    const recent = this.memoryHistory.slice(-10);
    const first = recent[0];
    const last = recent[recent.length - 1];
    
    const growth = last.heapUsed - first.heapUsed;
    const timespan = last.timestamp - first.timestamp;
    const growthRate = growth / (timespan / 1000 / 60); // MB per minute
    
    let trend = 'stable';
    if (growthRate > 5 * 1024 * 1024) { // 5MB/min
      trend = 'increasing';
    } else if (growthRate < -1 * 1024 * 1024) { // -1MB/min
      trend = 'decreasing';
    }
    
    return {
      trend,
      growth: this.formatBytes(growth),
      growthRate: `${this.formatBytes(growthRate)}/min`,
      timespan: `${(timespan / 1000).toFixed(0)}s`
    };
  }

  // Format bytes for display
  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // Get current statistics
  getStats() {
    return {
      ...this.stats,
      memoryHistoryLength: this.memoryHistory.length,
      currentLeaks: this.leaks.length,
      heapSnapshotsStored: this.heapSnapshots.length,
      isMonitoring: !!this.monitoringTimer
    };
  }

  // Stop monitoring
  stopMonitoring() {
    if (this.monitoringTimer) {
      clearInterval(this.monitoringTimer);
      this.monitoringTimer = null;
    }
    
    if (this.detailedAnalysisTimer) {
      clearInterval(this.detailedAnalysisTimer);
      this.detailedAnalysisTimer = null;
    }
    
    if (this.gcTimer) {
      clearInterval(this.gcTimer);
      this.gcTimer = null;
    }
    
    this.emit('monitoringStopped');
  }

  // Health check
  async healthCheck() {
    const currentMemory = process.memoryUsage();
    const heapStats = v8.getHeapStatistics();
    const heapUsage = currentMemory.heapUsed / heapStats.heap_size_limit;
    
    const healthy = heapUsage < this.config.alertThresholds.warning && 
                   this.leaks.length < 10;
    
    return {
      healthy,
      heapUsagePercent: (heapUsage * 100).toFixed(2),
      currentMemory: this.formatBytes(currentMemory.heapUsed),
      maxMemory: this.formatBytes(heapStats.heap_size_limit),
      recentLeaks: this.leaks.slice(-5).length,
      isMonitoring: !!this.monitoringTimer
    };
  }

  // Cleanup resources
  destroy() {
    this.stopMonitoring();
    this.memoryHistory = [];
    this.leaks = [];
    this.objectCounts.clear();
    this.eventListeners.clear();
    this.timers.clear();
    this.removeAllListeners();
  }
}

// Express middleware for memory monitoring
function createMemoryMiddleware(detector, options = {}) {
  return (req, res, next) => {
    const start = Date.now();
    const startMemory = process.memoryUsage();
    
    res.on('finish', () => {
      const endMemory = process.memoryUsage();
      const duration = Date.now() - start;
      const memoryDelta = endMemory.heapUsed - startMemory.heapUsed;
      
      if (memoryDelta > (options.threshold || 1024 * 1024)) { // 1MB threshold
        detector.emit('requestMemoryLeak', {
          url: req.originalUrl,
          method: req.method,
          duration,
          memoryDelta,
          userAgent: req.headers['user-agent']
        });
      }
    });
    
    next();
  };
}

module.exports = {
  MemoryLeakDetector,
  createMemoryMiddleware
};