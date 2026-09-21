const EventEmitter = require('events');
const logger = require('../core/logger');
const sharp = require('sharp');

class AdaptiveStreaming extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      // Quality levels
      qualityLevels: options.qualityLevels || [
        { name: 'ultra', width: 1920, height: 1080, fps: 60, bitrate: 8000, quality: 95 },
        { name: 'high', width: 1920, height: 1080, fps: 30, bitrate: 4000, quality: 85 },
        { name: 'medium', width: 1280, height: 720, fps: 30, bitrate: 2000, quality: 75 },
        { name: 'low', width: 854, height: 480, fps: 24, bitrate: 1000, quality: 65 },
        { name: 'potato', width: 640, height: 360, fps: 15, bitrate: 500, quality: 50 }
      ],
      
      // Adaptive settings
      targetLatency: options.targetLatency || 100, // milliseconds
      bufferSize: options.bufferSize || 3, // seconds
      maxRetries: options.maxRetries || 3,
      adaptationInterval: options.adaptationInterval || 5000, // 5 seconds
      
      // Gaming optimizations
      gamingMode: options.gamingMode || false,
      motionDetection: options.motionDetection !== false,
      frameSkipping: options.frameSkipping !== false,
      deltaCompression: options.deltaCompression !== false,
      
      ...options
    };

    // Streaming state
    this.currentQuality = this.options.qualityLevels[1]; // Start with 'high'
    this.streams = new Map(); // clientId -> streamConfig
    this.networkStats = new Map(); // clientId -> stats
    this.frameBuffer = new Map(); // clientId -> buffer
    this.lastFrames = new Map(); // clientId -> lastFrame for delta compression
    
    // Performance monitoring
    this.metrics = {
      totalClients: 0,
      averageLatency: 0,
      droppedFrames: 0,
      qualityChanges: 0,
      bytesTransmitted: 0,
      framesProcessed: 0
    };
    
    // Gaming optimization state
    this.motionAreas = new Map();
    this.priorityRegions = new Map();
  }

  async initialize() {
    logger.info('Initializing Adaptive Streaming system...');
    
    // Start adaptive quality monitoring
    this.startAdaptiveMonitoring();
    
    // Start performance monitoring
    this.startPerformanceMonitoring();
    
    logger.info('Adaptive Streaming system initialized successfully');
  }

  async addClient(clientId, clientInfo = {}) {
    const streamConfig = {
      id: clientId,
      quality: this.determineInitialQuality(clientInfo),
      connected: Date.now(),
      lastFrame: null,
      buffer: [],
      networkStats: {
        bandwidth: clientInfo.bandwidth || 0,
        latency: clientInfo.latency || 0,
        packetLoss: 0,
        jitter: 0,
        lastUpdate: Date.now()
      },
      adaptiveHistory: [],
      preferences: {
        maxQuality: clientInfo.maxQuality || 'ultra',
        minQuality: clientInfo.minQuality || 'potato',
        prioritizeFps: clientInfo.prioritizeFps || false,
        prioritizeLatency: clientInfo.prioritizeLatency || true
      }
    };
    
    this.streams.set(clientId, streamConfig);
    this.networkStats.set(clientId, streamConfig.networkStats);
    this.frameBuffer.set(clientId, []);
    
    this.metrics.totalClients++;
    
    logger.info(`Added streaming client: ${clientId}`, {
      quality: streamConfig.quality.name,
      bandwidth: streamConfig.networkStats.bandwidth
    });
    
    this.emit('client-added', { clientId, config: streamConfig });
    
    return streamConfig;
  }

  async removeClient(clientId) {
    if (this.streams.has(clientId)) {
      this.streams.delete(clientId);
      this.networkStats.delete(clientId);
      this.frameBuffer.delete(clientId);
      this.lastFrames.delete(clientId);
      
      this.metrics.totalClients--;
      
      logger.info(`Removed streaming client: ${clientId}`);
      this.emit('client-removed', { clientId });
    }
  }

  determineInitialQuality(clientInfo) {
    const bandwidth = clientInfo.bandwidth || 2000; // Default 2Mbps
    const connection = clientInfo.connectionType || 'unknown';
    const device = clientInfo.deviceType || 'desktop';
    
    // Mobile devices start lower
    if (device === 'mobile') {
      if (bandwidth < 1000) return this.options.qualityLevels[4]; // potato
      if (bandwidth < 2000) return this.options.qualityLevels[3]; // low
      return this.options.qualityLevels[2]; // medium
    }
    
    // Desktop/other devices
    if (bandwidth < 1000) return this.options.qualityLevels[3]; // low
    if (bandwidth < 2500) return this.options.qualityLevels[2]; // medium
    if (bandwidth < 5000) return this.options.qualityLevels[1]; // high
    return this.options.qualityLevels[0]; // ultra
  }

  async processFrame(frameData, targets = null) {
    const startTime = Date.now();
    
    try {
      // Detect motion if enabled
      let motionData = null;
      if (this.options.motionDetection) {
        motionData = await this.detectMotion(frameData);
      }
      
      // Process frame for each client
      const clientPromises = [];
      for (const [clientId, streamConfig] of this.streams) {
        clientPromises.push(this.processClientFrame(clientId, frameData, motionData));
      }
      
      await Promise.all(clientPromises);
      
      // Update metrics
      this.metrics.framesProcessed++;
      const processingTime = Date.now() - startTime;
      
      this.emit('frame-processed', {
        frameId: frameData.id,
        clients: this.streams.size,
        processingTime,
        motionDetected: motionData?.hasMotion || false
      });
      
    } catch (error) {
      logger.error('Frame processing error:', error);
      this.emit('processing-error', error);
    }
  }

  async processClientFrame(clientId, frameData, motionData) {
    const streamConfig = this.streams.get(clientId);
    if (!streamConfig) return;
    
    try {
      let processedFrame = frameData;
      
      // Apply quality scaling
      if (streamConfig.quality.width !== frameData.metadata?.width || 
          streamConfig.quality.height !== frameData.metadata?.height) {
        processedFrame = await this.scaleFrame(frameData, streamConfig.quality);
      }
      
      // Apply delta compression if enabled
      if (this.options.deltaCompression) {
        const lastFrame = this.lastFrames.get(clientId);
        if (lastFrame) {
          const deltaFrame = await this.createDeltaFrame(processedFrame, lastFrame);
          if (deltaFrame.size < processedFrame.size * 0.7) { // Use delta if 30% smaller
            processedFrame = deltaFrame;
          }
        }
        this.lastFrames.set(clientId, processedFrame);
      }
      
      // Gaming optimizations
      if (this.options.gamingMode) {
        processedFrame = await this.applyGamingOptimizations(processedFrame, motionData, clientId);
      }
      
      // Add to client buffer
      const buffer = this.frameBuffer.get(clientId);
      buffer.push({
        frame: processedFrame,
        timestamp: Date.now(),
        quality: streamConfig.quality.name,
        size: processedFrame.size || processedFrame.original?.length || 0
      });
      
      // Maintain buffer size
      if (buffer.length > streamConfig.quality.fps * this.options.bufferSize) {
        buffer.shift();
      }
      
      // Update metrics
      this.metrics.bytesTransmitted += processedFrame.size || 0;
      
      this.emit('client-frame-ready', {
        clientId,
        frame: processedFrame,
        quality: streamConfig.quality.name
      });
      
    } catch (error) {
      logger.error(`Client frame processing error for ${clientId}:`, error);
    }
  }

  async scaleFrame(frameData, quality) {
    try {
      const buffer = frameData.original || frameData.compressed;
      if (!buffer) return frameData;
      
      const scaledBuffer = await sharp(buffer)
        .resize(quality.width, quality.height, {
          fit: 'contain',
          background: { r: 0, g: 0, b: 0, alpha: 1 }
        })
        .jpeg({ quality: quality.quality, progressive: true })
        .toBuffer();
      
      return {
        ...frameData,
        compressed: scaledBuffer,
        size: scaledBuffer.length,
        metadata: {
          ...frameData.metadata,
          width: quality.width,
          height: quality.height,
          scaled: true
        }
      };
    } catch (error) {
      logger.error('Frame scaling error:', error);
      return frameData;
    }
  }

  async detectMotion(frameData) {
    try {
      // Simple motion detection using frame metadata
      const motionLevel = frameData.metadata?.motionLevel || 0;
      const hasMotion = frameData.metadata?.hasMotion || false;
      const motionRegions = frameData.metadata?.motionRegions || [];
      
      return {
        hasMotion,
        motionLevel,
        motionRegions,
        highMotionAreas: motionRegions.filter(region => region.area > 1000)
      };
    } catch (error) {
      logger.error('Motion detection error:', error);
      return { hasMotion: false, motionLevel: 0, motionRegions: [] };
    }
  }

  async createDeltaFrame(currentFrame, lastFrame) {
    try {
      // Simple delta compression - compare buffers
      const current = currentFrame.compressed || currentFrame.original;
      const last = lastFrame.compressed || lastFrame.original;
      
      if (!current || !last) return currentFrame;
      
      // Calculate difference (simplified)
      const delta = Buffer.alloc(Math.min(current.length, last.length));
      let differences = 0;
      
      for (let i = 0; i < delta.length; i++) {
        const diff = current[i] - last[i];
        delta[i] = diff;
        if (diff !== 0) differences++;
      }
      
      // Only use delta if significant compression
      const compressionRatio = differences / delta.length;
      if (compressionRatio < 0.3) {
        return {
          ...currentFrame,
          compressed: delta,
          size: delta.length,
          isDelta: true,
          compressionRatio
        };
      }
      
      return currentFrame;
    } catch (error) {
      logger.error('Delta frame creation error:', error);
      return currentFrame;
    }
  }

  async applyGamingOptimizations(frame, motionData, clientId) {
    try {
      // Priority regions for gaming (cursor, UI elements)
      const priorityRegions = this.priorityRegions.get(clientId) || [];
      
      // Higher quality for high-motion areas
      if (motionData?.highMotionAreas.length > 0) {
        // Mark high-motion areas for quality boost
        frame.priorityAreas = motionData.highMotionAreas;
      }
      
      // Reduce latency by skipping non-essential processing
      if (motionData?.motionLevel > 0.3) {
        frame.fastPath = true;
      }
      
      return frame;
    } catch (error) {
      logger.error('Gaming optimization error:', error);
      return frame;
    }
  }

  updateNetworkStats(clientId, stats) {
    const networkStats = this.networkStats.get(clientId);
    if (!networkStats) return;
    
    // Update network statistics
    Object.assign(networkStats, {
      ...stats,
      lastUpdate: Date.now()
    });
    
    // Trigger quality adaptation if needed
    this.adaptQualityForClient(clientId);
  }

  adaptQualityForClient(clientId) {
    const streamConfig = this.streams.get(clientId);
    const networkStats = this.networkStats.get(clientId);
    
    if (!streamConfig || !networkStats) return;
    
    const { bandwidth, latency, packetLoss } = networkStats;
    const currentQuality = streamConfig.quality;
    let newQuality = currentQuality;
    
    // Adapt based on network conditions
    if (latency > this.options.targetLatency * 2 || packetLoss > 0.05) {
      // Network issues - downgrade quality
      const currentIndex = this.options.qualityLevels.indexOf(currentQuality);
      if (currentIndex < this.options.qualityLevels.length - 1) {
        newQuality = this.options.qualityLevels[currentIndex + 1];
      }
    } else if (latency < this.options.targetLatency * 0.5 && packetLoss < 0.01) {
      // Good network - try to upgrade quality
      const currentIndex = this.options.qualityLevels.indexOf(currentQuality);
      if (currentIndex > 0) {
        const betterQuality = this.options.qualityLevels[currentIndex - 1];
        if (bandwidth >= betterQuality.bitrate) {
          newQuality = betterQuality;
        }
      }
    }
    
    // Apply quality change
    if (newQuality !== currentQuality) {
      streamConfig.quality = newQuality;
      streamConfig.adaptiveHistory.push({
        from: currentQuality.name,
        to: newQuality.name,
        reason: 'network_adaptation',
        timestamp: Date.now(),
        networkStats: { ...networkStats }
      });
      
      this.metrics.qualityChanges++;
      
      logger.info(`Quality adapted for client ${clientId}: ${currentQuality.name} → ${newQuality.name}`, {
        bandwidth,
        latency,
        packetLoss
      });
      
      this.emit('quality-changed', {
        clientId,
        oldQuality: currentQuality.name,
        newQuality: newQuality.name,
        reason: 'network_adaptation'
      });
    }
  }

  startAdaptiveMonitoring() {
    setInterval(() => {
      for (const clientId of this.streams.keys()) {
        this.adaptQualityForClient(clientId);
      }
    }, this.options.adaptationInterval);
  }

  startPerformanceMonitoring() {
    setInterval(() => {
      this.updatePerformanceMetrics();
      this.emit('performance-update', this.metrics);
    }, 10000); // Every 10 seconds
  }

  updatePerformanceMetrics() {
    // Calculate average latency
    const latencies = Array.from(this.networkStats.values())
      .map(stats => stats.latency)
      .filter(l => l > 0);
    
    this.metrics.averageLatency = latencies.length > 0 
      ? latencies.reduce((sum, l) => sum + l, 0) / latencies.length 
      : 0;
    
    // Update other metrics
    this.metrics.totalClients = this.streams.size;
  }

  // Public API methods
  getClientStream(clientId) {
    return this.streams.get(clientId);
  }

  getClientBuffer(clientId) {
    return this.frameBuffer.get(clientId) || [];
  }

  setClientQuality(clientId, qualityName) {
    const streamConfig = this.streams.get(clientId);
    if (!streamConfig) return false;
    
    const quality = this.options.qualityLevels.find(q => q.name === qualityName);
    if (!quality) return false;
    
    const oldQuality = streamConfig.quality;
    streamConfig.quality = quality;
    
    logger.info(`Manual quality change for client ${clientId}: ${oldQuality.name} → ${quality.name}`);
    
    this.emit('quality-changed', {
      clientId,
      oldQuality: oldQuality.name,
      newQuality: quality.name,
      reason: 'manual'
    });
    
    return true;
  }

  getStreamingStats() {
    return {
      ...this.metrics,
      clients: Array.from(this.streams.values()).map(config => ({
        id: config.id,
        quality: config.quality.name,
        connected: config.connected,
        networkStats: this.networkStats.get(config.id),
        bufferSize: this.frameBuffer.get(config.id)?.length || 0
      }))
    };
  }

  async cleanup() {
    this.streams.clear();
    this.networkStats.clear();
    this.frameBuffer.clear();
    this.lastFrames.clear();
    this.motionAreas.clear();
    this.priorityRegions.clear();
    
    this.removeAllListeners();
    logger.info('Adaptive Streaming system cleaned up');
  }
}

module.exports = AdaptiveStreaming;