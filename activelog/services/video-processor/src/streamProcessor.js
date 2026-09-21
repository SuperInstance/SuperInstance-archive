const WebSocket = require('ws');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const logger = require('./utils/logger');
const KeyframeExtractor = require('./keyframeExtractor');
const ThumbnailGenerator = require('./thumbnailGenerator');
const SceneDetector = require('./sceneDetector');
const OCRProcessor = require('./ocrProcessor');
const AISummarizer = require('./aiSummarizer');
const SubtitleProcessor = require('./subtitleProcessor');

class StreamProcessor {
  constructor(options = {}) {
    this.outputDir = options.outputDir || './output/streams';
    this.tempDir = options.tempDir || './temp/streams';
    this.chunkSize = options.chunkSize || 60;
    this.maxConcurrentStreams = options.maxConcurrentStreams || 5;
    this.processingQueue = [];
    this.activeStreams = new Map();
    this.wsConnections = new Map();
    this.processorInstances = this.initializeProcessors(options);
  }

  initializeProcessors(options) {
    return {
      keyframeExtractor: new KeyframeExtractor({
        outputDir: path.join(this.outputDir, 'keyframes'),
        ...options.keyframe
      }),
      thumbnailGenerator: new ThumbnailGenerator({
        outputDir: path.join(this.outputDir, 'thumbnails'),
        ...options.thumbnail
      }),
      sceneDetector: new SceneDetector({
        outputDir: path.join(this.outputDir, 'scenes'),
        ...options.scene
      }),
      ocrProcessor: new OCRProcessor({
        outputDir: path.join(this.outputDir, 'ocr'),
        ...options.ocr
      }),
      aiSummarizer: new AISummarizer({
        outputDir: path.join(this.outputDir, 'summaries'),
        ...options.ai
      }),
      subtitleProcessor: new SubtitleProcessor({
        outputDir: path.join(this.outputDir, 'subtitles'),
        ...options.subtitle
      })
    };
  }

  async ensureOutputDirs() {
    try {
      await fs.mkdir(this.outputDir, { recursive: true });
      await fs.mkdir(this.tempDir, { recursive: true });
    } catch (error) {
      logger.error('Failed to create output directories:', error);
      throw error;
    }
  }

  async startStreamProcessing(videoPath, processingOptions = {}, wsConnection = null) {
    const sessionId = uuidv4();
    logger.info(`Starting stream processing for ${videoPath} (session: ${sessionId})`);

    try {
      await this.ensureOutputDirs();

      if (this.activeStreams.size >= this.maxConcurrentStreams) {
        throw new Error('Maximum concurrent streams reached');
      }

      const streamConfig = {
        sessionId,
        videoPath,
        startTime: Date.now(),
        status: 'initializing',
        progress: {
          overall: 0,
          currentTask: 'initializing',
          completedTasks: [],
          activeTasks: [],
          pendingTasks: []
        },
        results: {},
        options: processingOptions
      };

      this.activeStreams.set(sessionId, streamConfig);
      
      if (wsConnection) {
        this.wsConnections.set(sessionId, wsConnection);
        this.setupWebSocketHandlers(sessionId, wsConnection);
      }

      this.processStreamAsync(sessionId, streamConfig);

      return {
        sessionId,
        status: 'started',
        message: 'Stream processing initiated'
      };

    } catch (error) {
      logger.error(`Failed to start stream processing for ${videoPath}:`, error);
      throw error;
    }
  }

  async processStreamAsync(sessionId, streamConfig) {
    try {
      await this.updateStreamStatus(sessionId, 'processing', 'Video analysis started');

      const processingPlan = this.createProcessingPlan(streamConfig.options);
      streamConfig.progress.pendingTasks = [...processingPlan];

      let completedResults = {};

      for (const task of processingPlan) {
        try {
          await this.updateStreamProgress(sessionId, {
            currentTask: task.name,
            activeTasks: [task.name],
            pendingTasks: streamConfig.progress.pendingTasks.filter(t => t.name !== task.name)
          });

          const taskResult = await this.executeProcessingTask(
            task, 
            streamConfig.videoPath, 
            completedResults,
            (progress) => this.updateTaskProgress(sessionId, task.name, progress)
          );

          completedResults[task.name] = taskResult;
          streamConfig.results[task.name] = taskResult;

          await this.updateStreamProgress(sessionId, {
            completedTasks: [...streamConfig.progress.completedTasks, task.name],
            activeTasks: [],
            overall: ((streamConfig.progress.completedTasks.length + 1) / processingPlan.length) * 100
          });

          await this.sendWebSocketUpdate(sessionId, {
            type: 'task_completed',
            task: task.name,
            result: taskResult,
            progress: streamConfig.progress
          });

        } catch (taskError) {
          logger.warn(`Task ${task.name} failed for session ${sessionId}:`, taskError);
          
          await this.sendWebSocketUpdate(sessionId, {
            type: 'task_error',
            task: task.name,
            error: taskError.message
          });

          if (task.required) {
            throw taskError;
          }
        }
      }

      const finalResults = await this.generateFinalResults(sessionId, completedResults);
      streamConfig.results.final = finalResults;

      await this.updateStreamStatus(sessionId, 'completed', 'All processing tasks completed');
      
      await this.sendWebSocketUpdate(sessionId, {
        type: 'processing_complete',
        results: finalResults,
        sessionId
      });

      await this.saveStreamResults(sessionId, streamConfig);

    } catch (error) {
      logger.error(`Stream processing failed for session ${sessionId}:`, error);
      
      await this.updateStreamStatus(sessionId, 'failed', error.message);
      
      await this.sendWebSocketUpdate(sessionId, {
        type: 'processing_error',
        error: error.message,
        sessionId
      });
    } finally {
      setTimeout(() => {
        this.activeStreams.delete(sessionId);
        this.wsConnections.delete(sessionId);
      }, 300000);
    }
  }

  createProcessingPlan(options) {
    const plan = [];

    if (options.extractKeyframes !== false) {
      plan.push({
        name: 'keyframes',
        processor: 'keyframeExtractor',
        method: 'extractKeyframes',
        required: false,
        priority: 1
      });
    }

    if (options.generateThumbnails !== false) {
      plan.push({
        name: 'thumbnails',
        processor: 'thumbnailGenerator',
        method: 'generateThumbnail',
        required: false,
        priority: 2
      });
    }

    if (options.detectScenes !== false) {
      plan.push({
        name: 'scenes',
        processor: 'sceneDetector',
        method: 'detectScenes',
        required: false,
        priority: 3
      });
    }

    if (options.extractOCR !== false) {
      plan.push({
        name: 'ocr',
        processor: 'ocrProcessor',
        method: 'extractTextFromVideo',
        required: false,
        priority: 4
      });
    }

    if (options.extractSubtitles !== false) {
      plan.push({
        name: 'subtitles',
        processor: 'subtitleProcessor',
        method: 'extractSubtitles',
        required: false,
        priority: 5
      });
    }

    if (options.generateSummary !== false) {
      plan.push({
        name: 'summary',
        processor: 'aiSummarizer',
        method: 'generateVideoSummary',
        required: false,
        priority: 6,
        dependsOn: ['scenes', 'keyframes', 'ocr', 'subtitles']
      });
    }

    return plan.sort((a, b) => a.priority - b.priority);
  }

  async executeProcessingTask(task, videoPath, completedResults, progressCallback) {
    const processor = this.processorInstances[task.processor];
    
    if (!processor) {
      throw new Error(`Processor ${task.processor} not found`);
    }

    if (task.dependsOn) {
      for (const dependency of task.dependsOn) {
        if (!completedResults[dependency]) {
          logger.warn(`Dependency ${dependency} not available for task ${task.name}`);
        }
      }
    }

    const taskOptions = {
      onProgress: progressCallback
    };

    switch (task.name) {
      case 'keyframes':
        return await processor[task.method](videoPath, taskOptions);
        
      case 'thumbnails':
        return await processor[task.method](videoPath, null, taskOptions);
        
      case 'scenes':
        return await processor[task.method](videoPath, taskOptions);
        
      case 'ocr':
        return await processor[task.method](videoPath, taskOptions);
        
      case 'subtitles':
        return await processor[task.method](videoPath, taskOptions);
        
      case 'summary':
        const summaryData = {
          videoPath,
          scenes: completedResults.scenes?.scenes || [],
          keyframes: completedResults.keyframes?.keyframes || [],
          ocrResults: completedResults.ocr?.ocrResults || [],
          subtitles: completedResults.subtitles?.subtitles?.processed || [],
          duration: completedResults.scenes?.totalFrames / completedResults.scenes?.fps || 0
        };
        return await processor[task.method](summaryData, taskOptions);
        
      default:
        throw new Error(`Unknown task: ${task.name}`);
    }
  }

  async generateFinalResults(sessionId, completedResults) {
    const finalResults = {
      sessionId,
      timestamp: new Date().toISOString(),
      processingTime: Date.now() - this.activeStreams.get(sessionId).startTime,
      summary: {
        tasksCompleted: Object.keys(completedResults).length,
        hasKeyframes: !!completedResults.keyframes,
        hasThumbnails: !!completedResults.thumbnails,
        hasScenes: !!completedResults.scenes,
        hasOCR: !!completedResults.ocr,
        hasSubtitles: !!completedResults.subtitles,
        hasSummary: !!completedResults.summary
      },
      results: completedResults,
      statistics: this.generateProcessingStatistics(completedResults)
    };

    return finalResults;
  }

  generateProcessingStatistics(results) {
    const stats = {
      totalProcessingTime: 0,
      dataPoints: {}
    };

    if (results.keyframes) {
      stats.dataPoints.keyframes = results.keyframes.keyframes?.length || 0;
    }

    if (results.scenes) {
      stats.dataPoints.scenes = results.scenes.scenes?.length || 0;
      stats.dataPoints.avgSceneDuration = results.scenes.statistics?.averageSceneDuration || 0;
    }

    if (results.ocr) {
      stats.dataPoints.ocrFrames = results.ocr.statistics?.totalTextFrames || 0;
      stats.dataPoints.totalWords = results.ocr.statistics?.totalWords || 0;
    }

    if (results.subtitles) {
      stats.dataPoints.subtitleSegments = results.subtitles.statistics?.totalSegments || 0;
    }

    if (results.thumbnails) {
      stats.dataPoints.thumbnails = results.thumbnails.thumbnails?.length || 0;
    }

    return stats;
  }

  async updateStreamStatus(sessionId, status, message = '') {
    const stream = this.activeStreams.get(sessionId);
    if (stream) {
      stream.status = status;
      stream.lastUpdate = Date.now();
      
      await this.sendWebSocketUpdate(sessionId, {
        type: 'status_update',
        status,
        message,
        timestamp: new Date().toISOString()
      });
    }
  }

  async updateStreamProgress(sessionId, progressUpdate) {
    const stream = this.activeStreams.get(sessionId);
    if (stream) {
      stream.progress = { ...stream.progress, ...progressUpdate };
      
      await this.sendWebSocketUpdate(sessionId, {
        type: 'progress_update',
        progress: stream.progress
      });
    }
  }

  async updateTaskProgress(sessionId, taskName, progress) {
    await this.sendWebSocketUpdate(sessionId, {
      type: 'task_progress',
      task: taskName,
      progress
    });
  }

  async sendWebSocketUpdate(sessionId, data) {
    const ws = this.wsConnections.get(sessionId);
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify(data));
      } catch (error) {
        logger.warn(`Failed to send WebSocket update for session ${sessionId}:`, error);
      }
    }
  }

  setupWebSocketHandlers(sessionId, ws) {
    ws.on('message', async (message) => {
      try {
        const data = JSON.parse(message);
        await this.handleWebSocketMessage(sessionId, data);
      } catch (error) {
        logger.warn(`Invalid WebSocket message for session ${sessionId}:`, error);
      }
    });

    ws.on('close', () => {
      logger.info(`WebSocket connection closed for session ${sessionId}`);
    });

    ws.on('error', (error) => {
      logger.warn(`WebSocket error for session ${sessionId}:`, error);
    });
  }

  async handleWebSocketMessage(sessionId, data) {
    switch (data.type) {
      case 'pause':
        await this.pauseStreamProcessing(sessionId);
        break;
        
      case 'resume':
        await this.resumeStreamProcessing(sessionId);
        break;
        
      case 'cancel':
        await this.cancelStreamProcessing(sessionId);
        break;
        
      case 'get_status':
        await this.sendStreamStatus(sessionId);
        break;
        
      default:
        logger.warn(`Unknown WebSocket message type: ${data.type}`);
    }
  }

  async pauseStreamProcessing(sessionId) {
    const stream = this.activeStreams.get(sessionId);
    if (stream && stream.status === 'processing') {
      stream.status = 'paused';
      await this.sendWebSocketUpdate(sessionId, {
        type: 'status_update',
        status: 'paused'
      });
    }
  }

  async resumeStreamProcessing(sessionId) {
    const stream = this.activeStreams.get(sessionId);
    if (stream && stream.status === 'paused') {
      stream.status = 'processing';
      await this.sendWebSocketUpdate(sessionId, {
        type: 'status_update',
        status: 'processing'
      });
    }
  }

  async cancelStreamProcessing(sessionId) {
    const stream = this.activeStreams.get(sessionId);
    if (stream) {
      stream.status = 'cancelled';
      await this.sendWebSocketUpdate(sessionId, {
        type: 'status_update',
        status: 'cancelled'
      });
      
      this.activeStreams.delete(sessionId);
      this.wsConnections.delete(sessionId);
    }
  }

  async sendStreamStatus(sessionId) {
    const stream = this.activeStreams.get(sessionId);
    if (stream) {
      await this.sendWebSocketUpdate(sessionId, {
        type: 'status_response',
        status: stream.status,
        progress: stream.progress,
        results: stream.results
      });
    }
  }

  async getStreamStatus(sessionId) {
    const stream = this.activeStreams.get(sessionId);
    if (!stream) {
      return { error: 'Stream not found' };
    }

    return {
      sessionId,
      status: stream.status,
      progress: stream.progress,
      startTime: stream.startTime,
      lastUpdate: stream.lastUpdate,
      hasResults: Object.keys(stream.results).length > 0
    };
  }

  async getAllActiveStreams() {
    const streams = [];
    
    for (const [sessionId, stream] of this.activeStreams) {
      streams.push({
        sessionId,
        status: stream.status,
        videoPath: stream.videoPath,
        startTime: stream.startTime,
        progress: stream.progress.overall
      });
    }

    return streams;
  }

  async saveStreamResults(sessionId, streamConfig) {
    try {
      const filename = `stream_results_${sessionId}.json`;
      const outputPath = path.join(this.outputDir, filename);
      
      const saveData = {
        sessionId,
        videoPath: streamConfig.videoPath,
        processingTime: Date.now() - streamConfig.startTime,
        status: streamConfig.status,
        results: streamConfig.results,
        options: streamConfig.options,
        timestamp: new Date().toISOString()
      };

      await fs.writeFile(outputPath, JSON.stringify(saveData, null, 2));
      logger.info(`Stream results saved to ${outputPath}`);
      
    } catch (error) {
      logger.warn(`Failed to save stream results for session ${sessionId}:`, error);
    }
  }

  async cleanup() {
    logger.info('Cleaning up stream processor...');
    
    for (const [sessionId, ws] of this.wsConnections) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    }
    
    this.wsConnections.clear();
    this.activeStreams.clear();
    this.processingQueue.length = 0;
  }
}

module.exports = StreamProcessor;