const EventEmitter = require('events');
const logger = require('../core/logger');
const path = require('path');

class AIBasedMomentDetection extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      modelPath: options.modelPath || './models/moment-detection.json',
      confidenceThreshold: options.confidenceThreshold || 0.7,
      batchSize: options.batchSize || 1,
      inputSize: options.inputSize || 224,
      enablePreprocessing: options.enablePreprocessing !== false,
      momentTypes: options.momentTypes || [
        'chart_change',
        'radar_contact',
        'alarm_trigger',
        'navigation_change',
        'fish_detected',
        'weather_alert',
        'vessel_proximity',
        'route_deviation',
        'depth_change',
        'anchorage_alert'
      ],
      ...options
    };

    this.model = null;
    this.isReady = false;
    this.frameQueue = [];
    this.processingQueue = [];
    this.maxQueueSize = 100;
    
    // Detection state
    this.lastAnalysis = null;
    this.continuousMoments = new Map();
    this.momentHistory = [];
    this.maxHistoryLength = 1000;
    
    // Performance metrics
    this.metrics = {
      totalAnalyses: 0,
      averageProcessingTime: 0,
      detectedMoments: 0,
      confidenceDistribution: {},
      momentTypeCount: {}
    };

    // Initialize moment type counters
    this.options.momentTypes.forEach(type => {
      this.metrics.momentTypeCount[type] = 0;
    });
  }

  async initialize() {
    logger.info('Initializing AI Moment Detection system (simplified)...');
    
    try {
      // For now, just mark as ready - we'll use pattern matching instead of AI
      this.isReady = true;
      logger.info('AI Moment Detection system initialized successfully (using pattern matching)');
      
    } catch (error) {
      logger.error('Failed to initialize AI Moment Detection:', error);
      throw error;
    }
  }

  async start() {
    if (!this.isReady) {
      throw new Error('AI Detection system not initialized');
    }
    
    logger.info('Starting AI Moment Detection');
    this.isActive = true;
    
    // Start processing queue
    this.startProcessingLoop();
  }

  async stop() {
    logger.info('Stopping AI Moment Detection');
    this.isActive = false;
    
    // Clear queues
    this.frameQueue.length = 0;
    this.processingQueue.length = 0;
  }

  startProcessingLoop() {
    const processNext = async () => {
      if (!this.isActive) return;
      
      if (this.processingQueue.length > 0) {
        const item = this.processingQueue.shift();
        try {
          await this.processFrame(item.frameData, item.resolve, item.reject);
        } catch (error) {
          item.reject(error);
        }
      }
      
      // Continue processing
      setTimeout(processNext, 10);
    };
    
    processNext();
  }

  async analyzeFrame(frameData) {
    return new Promise((resolve, reject) => {
      // Add to processing queue
      this.processingQueue.push({
        frameData,
        resolve,
        reject,
        timestamp: Date.now()
      });
      
      // Maintain queue size
      if (this.processingQueue.length > this.maxQueueSize) {
        const dropped = this.processingQueue.shift();
        dropped.reject(new Error('Frame dropped - processing queue full'));
      }
    });
  }

  async processFrame(frameData, resolve, reject) {
    const startTime = Date.now();
    
    try {
      // Use pattern-based detection instead of AI for now
      const analysis = await this.performPatternAnalysis(frameData);
      
      // Update metrics
      this.updateMetrics(startTime, analysis);
      
      // Store analysis
      this.lastAnalysis = analysis;
      this.addToHistory(analysis);
      
      // Emit significant moments
      if (analysis.significantMoments.length > 0) {
        this.emit('significant-moment', analysis);
      }
      
      resolve(analysis);
      
    } catch (error) {
      logger.error('AI analysis error:', error);
      reject(error);
    }
  }

  async performPatternAnalysis(frameData) {
    const analysis = {
      timestamp: Date.now(),
      frameId: frameData.id,
      predictions: new Array(this.options.momentTypes.length).fill(0),
      significantMoments: [],
      averageConfidence: 0,
      maxConfidence: 0,
      detectedTypes: [],
      marineContext: {
        chartActivity: false,
        radarActivity: false,
        fishingActivity: false,
        navigationActivity: false
      }
    };

    // Simple pattern-based detection based on frame metadata
    if (frameData.metadata) {
      const { hasMotion, motionLevel, significantChange } = frameData.metadata;
      
      // Detect moments based on motion and change patterns
      if (significantChange && motionLevel > 0.1) {
        const confidence = Math.min(0.9, motionLevel * 2);
        
        // Classify based on motion patterns
        let momentType = 'navigation_change';
        if (motionLevel > 0.5) {
          momentType = 'chart_change';
        } else if (motionLevel > 0.3) {
          momentType = 'radar_contact';
        }
        
        const moment = {
          type: momentType,
          confidence: confidence,
          timestamp: analysis.timestamp,
          frameId: frameData.id,
          context: this.getMarineContext(momentType),
          metadata: {
            motionLevel,
            hasMotion,
            significantChange,
            confidence
          }
        };
        
        analysis.significantMoments.push(moment);
        analysis.detectedTypes.push(momentType);
        
        // Update marine context
        this.updateMarineContext(analysis.marineContext, momentType);
        
        // Set predictions array
        const typeIndex = this.options.momentTypes.indexOf(momentType);
        if (typeIndex >= 0) {
          analysis.predictions[typeIndex] = confidence;
        }
        
        // Emit specific moment type
        this.emit('moment-detected', moment);
      }
    }

    // Calculate statistics
    analysis.averageConfidence = analysis.predictions.reduce((sum, p) => sum + p, 0) / analysis.predictions.length;
    analysis.maxConfidence = Math.max(...analysis.predictions);
    
    return analysis;
  }

  getMarineContext(momentType) {
    const contexts = {
      'chart_change': { category: 'navigation', priority: 'medium', action: 'observe' },
      'radar_contact': { category: 'safety', priority: 'high', action: 'track' },
      'alarm_trigger': { category: 'emergency', priority: 'critical', action: 'respond' },
      'navigation_change': { category: 'navigation', priority: 'medium', action: 'verify' },
      'fish_detected': { category: 'fishing', priority: 'low', action: 'mark' },
      'weather_alert': { category: 'safety', priority: 'high', action: 'assess' },
      'vessel_proximity': { category: 'safety', priority: 'high', action: 'monitor' },
      'route_deviation': { category: 'navigation', priority: 'medium', action: 'correct' },
      'depth_change': { category: 'navigation', priority: 'medium', action: 'note' },
      'anchorage_alert': { category: 'navigation', priority: 'medium', action: 'prepare' }
    };
    
    return contexts[momentType] || { category: 'general', priority: 'low', action: 'observe' };
  }

  updateMarineContext(context, momentType) {
    const typeMap = {
      'chart_change': 'chartActivity',
      'navigation_change': 'navigationActivity',
      'route_deviation': 'navigationActivity',
      'depth_change': 'navigationActivity',
      'anchorage_alert': 'navigationActivity',
      'radar_contact': 'radarActivity',
      'vessel_proximity': 'radarActivity',
      'fish_detected': 'fishingActivity'
    };
    
    const contextKey = typeMap[momentType];
    if (contextKey) {
      context[contextKey] = true;
    }
  }

  updateMetrics(startTime, analysis) {
    const processingTime = Date.now() - startTime;
    
    this.metrics.totalAnalyses++;
    this.metrics.averageProcessingTime = 
      (this.metrics.averageProcessingTime * (this.metrics.totalAnalyses - 1) + processingTime) / 
      this.metrics.totalAnalyses;
    
    this.metrics.detectedMoments += analysis.significantMoments.length;
    
    // Update confidence distribution
    const confidenceBucket = Math.floor(analysis.maxConfidence * 10) / 10;
    this.metrics.confidenceDistribution[confidenceBucket] = 
      (this.metrics.confidenceDistribution[confidenceBucket] || 0) + 1;
    
    // Update moment type counts
    analysis.detectedTypes.forEach(type => {
      this.metrics.momentTypeCount[type]++;
    });
  }

  addToHistory(analysis) {
    this.momentHistory.push({
      timestamp: analysis.timestamp,
      detectedTypes: analysis.detectedTypes,
      maxConfidence: analysis.maxConfidence,
      momentCount: analysis.significantMoments.length
    });
    
    // Maintain history size
    if (this.momentHistory.length > this.maxHistoryLength) {
      this.momentHistory.shift();
    }
  }

  // Public API methods
  isReady() {
    return this.isReady;
  }

  getMetrics() {
    return { ...this.metrics };
  }

  getLastAnalysis() {
    return this.lastAnalysis;
  }

  getMomentHistory() {
    return [...this.momentHistory];
  }

  setConfidenceThreshold(threshold) {
    this.options.confidenceThreshold = Math.max(0, Math.min(1, threshold));
    logger.info(`Confidence threshold set to: ${this.options.confidenceThreshold}`);
  }

  enableMomentType(momentType) {
    if (!this.options.momentTypes.includes(momentType)) {
      this.options.momentTypes.push(momentType);
      this.metrics.momentTypeCount[momentType] = 0;
      logger.info(`Moment type enabled: ${momentType}`);
    }
  }

  disableMomentType(momentType) {
    const index = this.options.momentTypes.indexOf(momentType);
    if (index > -1) {
      this.options.momentTypes.splice(index, 1);
      delete this.metrics.momentTypeCount[momentType];
      logger.info(`Moment type disabled: ${momentType}`);
    }
  }
}

module.exports = AIBasedMomentDetection;