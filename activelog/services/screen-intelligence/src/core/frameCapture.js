const screenshot = require('screenshot-desktop');
const sharp = require('sharp');
const EventEmitter = require('events');
const fs = require('fs').promises;
const path = require('path');
const logger = require('./logger');

class FrameCapture extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      fps: options.fps || 1,
      quality: options.quality || 80,
      detectActions: options.detectActions !== false,
      format: options.format || 'png',
      screen: options.screen || 0,
      region: options.region || null, // { x, y, width, height }
      enableDifference: options.enableDifference !== false,
      differenceThreshold: options.differenceThreshold || 0.05,
      compressionLevel: options.compressionLevel || 6,
      ...options
    };

    this.isActive = false;
    this.captureInterval = null;
    this.lastFrame = null;
    this.frameBuffer = [];
    this.maxBufferSize = 30; // Keep last 30 frames
    this.captureCount = 0;
    this.actionDetectionEnabled = this.options.detectActions;
    
    // Action detection state
    this.previousFrame = null;
    this.motionThreshold = 0.02;
    this.significantChangeThreshold = 0.15;
    
    // Performance metrics
    this.metrics = {
      capturesPerSecond: 0,
      averageProcessingTime: 0,
      totalCaptures: 0,
      failedCaptures: 0,
      lastCaptureTime: null
    };

    this.setupPerformanceMonitoring();
  }

  setupPerformanceMonitoring() {
    setInterval(() => {
      const now = Date.now();
      const timeSinceLastCapture = this.metrics.lastCaptureTime ? 
        (now - this.metrics.lastCaptureTime) / 1000 : 0;
      
      this.emit('metrics', {
        ...this.metrics,
        isActive: this.isActive,
        timeSinceLastCapture,
        bufferSize: this.frameBuffer.length,
        memoryUsage: process.memoryUsage()
      });
    }, 5000);
  }

  async initialize() {
    logger.info('Initializing Frame Capture system...');
    
    try {
      // Test screenshot capability
      await this.testScreenshot();
      
      // Create storage directory
      await this.ensureStorageDirectory();
      
      logger.info('Frame Capture system initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Frame Capture:', error);
      throw error;
    }
  }

  async testScreenshot() {
    try {
      const testCapture = await screenshot({ format: 'png' });
      logger.info(`Screenshot test successful. Size: ${testCapture.length} bytes`);
    } catch (error) {
      logger.error('Screenshot test failed:', error);
      throw new Error('Screen capture not available on this system');
    }
  }

  async ensureStorageDirectory() {
    const storageDir = path.join(process.cwd(), 'storage', 'frames');
    try {
      await fs.mkdir(storageDir, { recursive: true });
      this.storageDir = storageDir;
    } catch (error) {
      logger.error('Failed to create storage directory:', error);
      throw error;
    }
  }

  async start() {
    if (this.isActive) {
      logger.warn('Frame capture already active');
      return;
    }

    logger.info(`Starting frame capture at ${this.options.fps} FPS`);
    this.isActive = true;
    
    const captureInterval = Math.floor(1000 / this.options.fps);
    
    this.captureInterval = setInterval(async () => {
      await this.captureFrame();
    }, captureInterval);

    this.emit('started');
  }

  async stop() {
    if (!this.isActive) {
      logger.warn('Frame capture not active');
      return;
    }

    logger.info('Stopping frame capture');
    this.isActive = false;

    if (this.captureInterval) {
      clearInterval(this.captureInterval);
      this.captureInterval = null;
    }

    this.emit('stopped');
  }

  async captureFrame() {
    const startTime = Date.now();
    
    try {
      // Capture screenshot
      const screenshotOptions = {
        format: this.options.format,
        screen: this.options.screen
      };

      if (this.options.region) {
        screenshotOptions.region = this.options.region;
      }

      const rawBuffer = await screenshot(screenshotOptions);
      
      // Process the frame
      const frameData = await this.processFrame(rawBuffer, startTime);
      
      // Update metrics
      this.updateMetrics(startTime);
      
      // Emit frame event
      this.emit('frame', frameData);
      
      // Store in buffer
      this.addToBuffer(frameData);
      
    } catch (error) {
      logger.error('Frame capture error:', error);
      this.metrics.failedCaptures++;
      this.emit('capture-error', error);
    }
  }

  async processFrame(rawBuffer, timestamp) {
    const frameData = {
      id: `frame_${Date.now()}_${this.captureCount++}`,
      timestamp,
      size: rawBuffer.length,
      original: rawBuffer,
      processed: null,
      compressed: null,
      base64: null,
      metadata: {
        width: null,
        height: null,
        channels: null,
        hasMotion: false,
        motionLevel: 0,
        significantChange: false,
        actionDetected: null
      }
    };

    try {
      // Get image metadata
      const sharpImage = sharp(rawBuffer);
      const metadata = await sharpImage.metadata();
      
      frameData.metadata.width = metadata.width;
      frameData.metadata.height = metadata.height;
      frameData.metadata.channels = metadata.channels;

      // Compress frame
      const compressedBuffer = await sharpImage
        .png({ 
          quality: this.options.quality,
          compressionLevel: this.options.compressionLevel
        })
        .toBuffer();
      
      frameData.compressed = compressedBuffer;
      frameData.base64 = compressedBuffer.toString('base64');
      frameData.processed = compressedBuffer;

      // Basic action detection (simplified without OpenCV)
      if (this.actionDetectionEnabled) {
        const actionData = await this.detectBasicActions(rawBuffer, metadata);
        frameData.metadata = { ...frameData.metadata, ...actionData };
      }

      // Difference detection
      if (this.options.enableDifference && this.lastFrame) {
        const difference = await this.calculateFrameDifference(compressedBuffer, this.lastFrame.compressed);
        frameData.metadata.differenceScore = difference;
        frameData.metadata.significantChange = difference > this.significantChangeThreshold;
      }

      this.lastFrame = frameData;
      return frameData;

    } catch (error) {
      logger.error('Frame processing error:', error);
      return frameData; // Return basic frame data even if processing fails
    }
  }

  async detectBasicActions(rawBuffer, metadata) {
    const actionData = {
      hasMotion: false,
      motionLevel: 0,
      actionDetected: null,
      motionRegions: []
    };

    try {
      // Basic motion detection using image histogram comparison
      if (this.lastFrame) {
        const currentHistogram = await this.calculateImageHistogram(rawBuffer);
        const lastHistogram = await this.calculateImageHistogram(this.lastFrame.original);
        
        const motionLevel = this.compareHistograms(currentHistogram, lastHistogram);
        
        actionData.motionLevel = motionLevel;
        actionData.hasMotion = motionLevel > this.motionThreshold;

        // Simple action classification
        if (actionData.hasMotion) {
          actionData.actionDetected = this.classifyBasicAction(motionLevel);
        }
      }
      
    } catch (error) {
      logger.error('Basic action detection error:', error);
    }

    return actionData;
  }

  async calculateImageHistogram(buffer) {
    try {
      const image = sharp(buffer).resize(64, 64).greyscale();
      const pixels = await image.raw().toBuffer();
      
      const histogram = new Array(256).fill(0);
      for (let i = 0; i < pixels.length; i++) {
        histogram[pixels[i]]++;
      }
      
      return histogram;
    } catch (error) {
      logger.error('Histogram calculation error:', error);
      return new Array(256).fill(0);
    }
  }

  compareHistograms(hist1, hist2) {
    let totalDiff = 0;
    let totalPixels = 0;
    
    for (let i = 0; i < 256; i++) {
      totalDiff += Math.abs(hist1[i] - hist2[i]);
      totalPixels += Math.max(hist1[i], hist2[i]);
    }
    
    return totalPixels > 0 ? totalDiff / totalPixels : 0;
  }

  classifyBasicAction(motionLevel) {
    if (motionLevel > 0.3) {
      return 'high_activity';
    } else if (motionLevel > 0.1) {
      return 'moderate_activity';
    } else if (motionLevel > 0.02) {
      return 'low_activity';
    }
    return 'idle';
  }

  async calculateFrameDifference(buffer1, buffer2) {
    try {
      const image1 = sharp(buffer1).resize(100, 100).greyscale();
      const image2 = sharp(buffer2).resize(100, 100).greyscale();
      
      const [pixels1, pixels2] = await Promise.all([
        image1.raw().toBuffer(),
        image2.raw().toBuffer()
      ]);
      
      let totalDiff = 0;
      const pixelCount = pixels1.length;
      
      for (let i = 0; i < pixelCount; i++) {
        totalDiff += Math.abs(pixels1[i] - pixels2[i]);
      }
      
      return totalDiff / (pixelCount * 255);
      
    } catch (error) {
      logger.error('Frame difference calculation error:', error);
      return 0;
    }
  }

  addToBuffer(frameData) {
    this.frameBuffer.push(frameData);
    
    // Maintain buffer size
    if (this.frameBuffer.length > this.maxBufferSize) {
      this.frameBuffer.shift();
    }
  }

  updateMetrics(startTime) {
    const processingTime = Date.now() - startTime;
    
    this.metrics.totalCaptures++;
    this.metrics.lastCaptureTime = Date.now();
    this.metrics.averageProcessingTime = 
      (this.metrics.averageProcessingTime * (this.metrics.totalCaptures - 1) + processingTime) / 
      this.metrics.totalCaptures;
  }

  // Public API methods
  isActive() {
    return this.isActive;
  }

  getLastFrame() {
    return this.lastFrame;
  }

  getFrameBuffer() {
    return [...this.frameBuffer];
  }

  getMetrics() {
    return { ...this.metrics };
  }

  async saveFrame(frameId, directory = null) {
    const frame = this.frameBuffer.find(f => f.id === frameId) || this.lastFrame;
    if (!frame) {
      throw new Error('Frame not found');
    }

    const saveDir = directory || this.storageDir;
    const filename = `${frame.id}.png`;
    const filepath = path.join(saveDir, filename);
    
    await fs.writeFile(filepath, frame.processed || frame.original);
    
    return {
      filename,
      filepath,
      size: frame.size,
      timestamp: frame.timestamp
    };
  }

  setOptions(newOptions) {
    this.options = { ...this.options, ...newOptions };
    
    // Restart capture if settings changed and capture is active
    if (this.isActive && (newOptions.fps || newOptions.screen || newOptions.region)) {
      this.stop();
      setTimeout(() => this.start(), 100);
    }
  }

  // Configuration methods
  enableActionDetection() {
    this.actionDetectionEnabled = true;
    logger.info('Action detection enabled');
  }

  disableActionDetection() {
    this.actionDetectionEnabled = false;
    logger.info('Action detection disabled');
  }

  setRegion(x, y, width, height) {
    this.options.region = { x, y, width, height };
    logger.info(`Capture region set to: ${x}, ${y}, ${width}x${height}`);
  }

  clearRegion() {
    this.options.region = null;
    logger.info('Capture region cleared - using full screen');
  }
}

module.exports = FrameCapture;