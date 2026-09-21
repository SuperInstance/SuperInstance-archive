const EventEmitter = require('events');
const screenshot = require('screenshot-desktop');
const sharp = require('sharp');
const logger = require('../core/logger');
const fs = require('fs').promises;
const path = require('path');

class BackgroundCapture extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      // Capture settings
      fps: options.fps || 30,
      quality: options.quality || 80,
      format: options.format || 'jpeg',
      
      // Multi-monitor support
      captureAllMonitors: options.captureAllMonitors !== false,
      primaryMonitorOnly: options.primaryMonitorOnly || false,
      monitorSelection: options.monitorSelection || 'auto', // 'auto', 'primary', 'all', [0,1,2]
      
      // Background optimizations
      lowPriority: options.lowPriority !== false,
      adaptiveFps: options.adaptiveFps !== false,
      powerAware: options.powerAware !== false,
      
      // Performance settings
      maxConcurrentCaptures: options.maxConcurrentCaptures || 2,
      captureTimeout: options.captureTimeout || 5000,
      retryAttempts: options.retryAttempts || 3,
      
      // Storage settings
      tempStorage: options.tempStorage || './storage/temp',
      maxStorageSize: options.maxStorageSize || 1024 * 1024 * 1024, // 1GB
      
      ...options
    };

    // Capture state
    this.isCapturing = false;
    this.captureInterval = null;
    this.monitors = [];
    this.activeCaptures = new Map();
    
    // Performance tracking
    this.metrics = {
      totalCaptures: 0,
      successfulCaptures: 0,
      failedCaptures: 0,
      averageLatency: 0,
      currentFps: this.options.fps,
      droppedFrames: 0,
      storageUsed: 0
    };
    
    // Power management
    this.powerState = 'normal'; // normal, low-power, critical
    this.systemLoad = 0;
    
    // Frame queues for different monitors
    this.frameQueues = new Map();
  }

  async initialize() {
    logger.info('Initializing Background Capture system...');
    
    try {
      // Detect available monitors
      await this.detectMonitors();
      
      // Setup storage
      await this.setupStorage();
      
      // Initialize frame queues
      this.initializeFrameQueues();
      
      // Setup power monitoring
      this.setupPowerMonitoring();
      
      // Setup performance monitoring
      this.setupPerformanceMonitoring();
      
      logger.info(`Background Capture initialized with ${this.monitors.length} monitors`);
      
    } catch (error) {
      logger.error('Failed to initialize Background Capture:', error);
      throw error;
    }
  }

  async detectMonitors() {
    try {
      // Get all available displays
      const displays = await screenshot.listDisplays();
      
      this.monitors = displays.map((display, index) => ({
        id: display.id || index,
        name: display.name || `Monitor ${index + 1}`,
        primary: display.primary || index === 0,
        bounds: {
          x: display.left || 0,
          y: display.top || 0,
          width: display.width || 1920,
          height: display.height || 1080
        },
        scaleFactor: display.scaleFactor || 1,
        active: true
      }));
      
      logger.info('Detected monitors:', this.monitors.map(m => `${m.name} (${m.bounds.width}x${m.bounds.height})`));
      
    } catch (error) {
      logger.warn('Monitor detection failed, using default configuration:', error.message);
      // Fallback to single monitor
      this.monitors = [{
        id: 0,
        name: 'Default Monitor',
        primary: true,
        bounds: { x: 0, y: 0, width: 1920, height: 1080 },
        scaleFactor: 1,
        active: true
      }];
    }
  }

  async setupStorage() {
    try {
      await fs.mkdir(this.options.tempStorage, { recursive: true });
      logger.debug(`Storage setup completed: ${this.options.tempStorage}`);
    } catch (error) {
      logger.error('Storage setup failed:', error);
      throw error;
    }
  }

  initializeFrameQueues() {
    for (const monitor of this.monitors) {
      this.frameQueues.set(monitor.id, {
        frames: [],
        lastCapture: null,
        capturePending: false,
        stats: {
          captures: 0,
          failures: 0,
          avgLatency: 0
        }
      });
    }
  }

  setupPowerMonitoring() {
    // Monitor system performance every 30 seconds
    setInterval(() => {
      this.updatePowerState();
    }, 30000);
  }

  setupPerformanceMonitoring() {
    setInterval(() => {
      this.updatePerformanceMetrics();
      this.emit('performance-update', this.metrics);
    }, 5000);
  }

  async start() {
    if (this.isCapturing) {
      logger.warn('Background capture already running');
      return;
    }

    logger.info(`Starting background capture at ${this.metrics.currentFps} FPS`);
    this.isCapturing = true;
    
    // Calculate capture interval
    const captureInterval = Math.floor(1000 / this.metrics.currentFps);
    
    this.captureInterval = setInterval(async () => {
      await this.performCapture();
    }, captureInterval);
    
    this.emit('capture-started');
  }

  async stop() {
    if (!this.isCapturing) {
      logger.warn('Background capture not running');
      return;
    }

    logger.info('Stopping background capture');
    this.isCapturing = false;
    
    if (this.captureInterval) {
      clearInterval(this.captureInterval);
      this.captureInterval = null;
    }
    
    // Wait for active captures to complete
    await this.waitForActiveCaptures();
    
    this.emit('capture-stopped');
  }

  async performCapture() {
    if (this.activeCaptures.size >= this.options.maxConcurrentCaptures) {
      this.metrics.droppedFrames++;
      return;
    }

    const targetMonitors = this.getTargetMonitors();
    const capturePromises = [];
    
    for (const monitor of targetMonitors) {
      const queue = this.frameQueues.get(monitor.id);
      if (queue && !queue.capturePending) {
        queue.capturePending = true;
        capturePromises.push(this.captureMonitor(monitor));
      }
    }
    
    if (capturePromises.length > 0) {
      try {
        await Promise.all(capturePromises);
      } catch (error) {
        logger.error('Capture batch error:', error);
      }
    }
  }

  async captureMonitor(monitor) {
    const captureId = `${monitor.id}_${Date.now()}`;
    const startTime = Date.now();
    
    this.activeCaptures.set(captureId, {
      monitorId: monitor.id,
      startTime
    });
    
    try {
      // Capture screenshot for specific monitor
      const screenshotOptions = {
        screen: monitor.id,
        format: 'png'
      };
      
      // Add region if not capturing full screen
      if (monitor.bounds && !this.options.captureAllMonitors) {
        screenshotOptions.region = monitor.bounds;
      }
      
      const rawBuffer = await screenshot(screenshotOptions);
      
      // Process the captured frame
      const frameData = await this.processFrame(rawBuffer, monitor, startTime);
      
      // Add to frame queue
      const queue = this.frameQueues.get(monitor.id);
      if (queue) {
        queue.frames.push(frameData);
        queue.lastCapture = Date.now();
        queue.stats.captures++;
        queue.stats.avgLatency = (queue.stats.avgLatency + (Date.now() - startTime)) / 2;
        
        // Maintain queue size (keep last 30 seconds worth)
        const maxFrames = this.metrics.currentFps * 30;
        if (queue.frames.length > maxFrames) {
          queue.frames = queue.frames.slice(-maxFrames);
        }
        
        queue.capturePending = false;
      }
      
      // Update metrics
      this.metrics.totalCaptures++;
      this.metrics.successfulCaptures++;
      
      // Emit frame event
      this.emit('frame-captured', {
        monitorId: monitor.id,
        frameData,
        captureTime: Date.now() - startTime
      });
      
    } catch (error) {
      logger.error(`Monitor ${monitor.id} capture failed:`, error);
      
      const queue = this.frameQueues.get(monitor.id);
      if (queue) {
        queue.stats.failures++;
        queue.capturePending = false;
      }
      
      this.metrics.failedCaptures++;
      
      this.emit('capture-error', {
        monitorId: monitor.id,
        error: error.message
      });
      
    } finally {
      this.activeCaptures.delete(captureId);
    }
  }

  async processFrame(rawBuffer, monitor, timestamp) {
    try {
      const frameData = {
        id: `frame_${monitor.id}_${timestamp}`,
        monitorId: monitor.id,
        timestamp,
        size: rawBuffer.length,
        original: rawBuffer,
        metadata: {
          monitorName: monitor.name,
          bounds: monitor.bounds,
          primary: monitor.primary,
          scaleFactor: monitor.scaleFactor
        }
      };
      
      // Compress frame if needed
      if (this.options.format === 'jpeg') {
        const compressed = await sharp(rawBuffer)
          .jpeg({ 
            quality: this.options.quality,
            progressive: true 
          })
          .toBuffer();
        
        frameData.compressed = compressed;
        frameData.format = 'jpeg';
        frameData.compressedSize = compressed.length;
      }
      
      // Add monitor-specific metadata
      frameData.metadata.resolution = `${monitor.bounds.width}x${monitor.bounds.height}`;
      frameData.metadata.aspectRatio = monitor.bounds.width / monitor.bounds.height;
      
      return frameData;
      
    } catch (error) {
      logger.error('Frame processing error:', error);
      throw error;
    }
  }

  getTargetMonitors() {
    switch (this.options.monitorSelection) {
      case 'primary':
        return this.monitors.filter(m => m.primary);
      
      case 'all':
        return this.monitors.filter(m => m.active);
      
      case 'auto':
        // Smart selection based on activity or user focus
        return this.monitors.filter(m => m.active && (m.primary || this.hasActivity(m.id)));
      
      default:
        if (Array.isArray(this.options.monitorSelection)) {
          return this.monitors.filter(m => this.options.monitorSelection.includes(m.id));
        }
        return this.monitors.filter(m => m.primary);
    }
  }

  hasActivity(monitorId) {
    const queue = this.frameQueues.get(monitorId);
    if (!queue || queue.frames.length < 2) return false;
    
    // Check if there's been recent activity
    return Date.now() - (queue.lastCapture || 0) < 60000; // 1 minute
  }

  updatePowerState() {
    // Simulate power state monitoring
    const memoryUsage = process.memoryUsage();
    const heapPercent = memoryUsage.heapUsed / memoryUsage.heapTotal;
    
    if (heapPercent > 0.9) {
      this.powerState = 'critical';
      this.adaptToLowPower();
    } else if (heapPercent > 0.7) {
      this.powerState = 'low-power';
      this.adaptToLowPower();
    } else {
      this.powerState = 'normal';
      this.restoreNormalPower();
    }
  }

  adaptToLowPower() {
    if (this.options.powerAware) {
      const oldFps = this.metrics.currentFps;
      this.metrics.currentFps = Math.max(5, Math.floor(this.options.fps / 2));
      
      if (this.isCapturing && oldFps !== this.metrics.currentFps) {
        // Restart capture with new FPS
        this.stop();
        setTimeout(() => this.start(), 1000);
      }
      
      logger.info(`Adapted to ${this.powerState} mode: FPS reduced to ${this.metrics.currentFps}`);
    }
  }

  restoreNormalPower() {
    if (this.options.powerAware && this.metrics.currentFps !== this.options.fps) {
      const oldFps = this.metrics.currentFps;
      this.metrics.currentFps = this.options.fps;
      
      if (this.isCapturing) {
        this.stop();
        setTimeout(() => this.start(), 1000);
      }
      
      logger.info(`Restored to normal power mode: FPS increased to ${this.metrics.currentFps}`);
    }
  }

  updatePerformanceMetrics() {
    // Calculate average latency across all monitors
    const latencies = Array.from(this.frameQueues.values())
      .map(queue => queue.stats.avgLatency)
      .filter(l => l > 0);
    
    this.metrics.averageLatency = latencies.length > 0
      ? latencies.reduce((sum, l) => sum + l, 0) / latencies.length
      : 0;
    
    // Update storage usage
    this.updateStorageUsage();
  }

  async updateStorageUsage() {
    try {
      const stats = await fs.stat(this.options.tempStorage);
      this.metrics.storageUsed = stats.size || 0;
      
      // Clean up if storage limit exceeded
      if (this.metrics.storageUsed > this.options.maxStorageSize) {
        await this.cleanupStorage();
      }
    } catch (error) {
      // Storage directory might not exist yet
      this.metrics.storageUsed = 0;
    }
  }

  async cleanupStorage() {
    try {
      const files = await fs.readdir(this.options.tempStorage);
      const fileStats = await Promise.all(
        files.map(async file => {
          const filePath = path.join(this.options.tempStorage, file);
          const stats = await fs.stat(filePath);
          return { file: filePath, mtime: stats.mtime };
        })
      );
      
      // Sort by modification time (oldest first)
      fileStats.sort((a, b) => a.mtime - b.mtime);
      
      // Remove oldest files until under limit
      const targetSize = this.options.maxStorageSize * 0.8; // 80% of limit
      let removedSize = 0;
      
      for (const { file } of fileStats) {
        if (this.metrics.storageUsed - removedSize <= targetSize) break;
        
        try {
          const stats = await fs.stat(file);
          await fs.unlink(file);
          removedSize += stats.size;
        } catch (error) {
          logger.warn(`Failed to remove file ${file}:`, error.message);
        }
      }
      
      if (removedSize > 0) {
        logger.info(`Cleaned up ${removedSize} bytes from storage`);
      }
    } catch (error) {
      logger.error('Storage cleanup failed:', error);
    }
  }

  async waitForActiveCaptures() {
    const maxWait = 10000; // 10 seconds
    const startWait = Date.now();
    
    while (this.activeCaptures.size > 0 && Date.now() - startWait < maxWait) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    if (this.activeCaptures.size > 0) {
      logger.warn(`${this.activeCaptures.size} captures still active after timeout`);
    }
  }

  // Public API methods
  getMonitors() {
    return [...this.monitors];
  }

  getFrameBuffer(monitorId = null) {
    if (monitorId !== null) {
      const queue = this.frameQueues.get(monitorId);
      return queue ? [...queue.frames] : [];
    }
    
    // Return all frames from all monitors
    const allFrames = [];
    for (const queue of this.frameQueues.values()) {
      allFrames.push(...queue.frames);
    }
    
    // Sort by timestamp
    return allFrames.sort((a, b) => a.timestamp - b.timestamp);
  }

  getLatestFrame(monitorId = null) {
    if (monitorId !== null) {
      const queue = this.frameQueues.get(monitorId);
      return queue && queue.frames.length > 0 ? queue.frames[queue.frames.length - 1] : null;
    }
    
    // Return latest frame from primary monitor or first available
    const primaryMonitor = this.monitors.find(m => m.primary) || this.monitors[0];
    return this.getLatestFrame(primaryMonitor?.id);
  }

  setMonitorActive(monitorId, active) {
    const monitor = this.monitors.find(m => m.id === monitorId);
    if (monitor) {
      monitor.active = active;
      logger.info(`Monitor ${monitor.name} set to ${active ? 'active' : 'inactive'}`);
      return true;
    }
    return false;
  }

  getCapturingStatus() {
    return {
      isCapturing: this.isCapturing,
      currentFps: this.metrics.currentFps,
      powerState: this.powerState,
      activeCaptures: this.activeCaptures.size,
      monitors: this.monitors.map(m => ({
        id: m.id,
        name: m.name,
        active: m.active,
        primary: m.primary,
        lastCapture: this.frameQueues.get(m.id)?.lastCapture,
        frameCount: this.frameQueues.get(m.id)?.frames.length || 0
      }))
    };
  }

  getMetrics() {
    return {
      ...this.metrics,
      monitorStats: Array.from(this.frameQueues.entries()).map(([id, queue]) => ({
        monitorId: id,
        ...queue.stats,
        frameCount: queue.frames.length,
        lastCapture: queue.lastCapture
      }))
    };
  }

  async cleanup() {
    await this.stop();
    
    this.frameQueues.clear();
    this.activeCaptures.clear();
    
    this.removeAllListeners();
    logger.info('Background Capture system cleaned up');
  }
}

module.exports = BackgroundCapture;