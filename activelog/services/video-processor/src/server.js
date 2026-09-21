const express = require('express');
const multer = require('multer');
const WebSocket = require('ws');
const http = require('http');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const path = require('path');
const fs = require('fs').promises;
const { v4: uuidv4 } = require('uuid');

const KeyframeExtractor = require('./keyframeExtractor');
const ThumbnailGenerator = require('./thumbnailGenerator');
const SceneDetector = require('./sceneDetector');
const OCRProcessor = require('./ocrProcessor');
const AISummarizer = require('./aiSummarizer');
const SubtitleProcessor = require('./subtitleProcessor');
const StreamProcessor = require('./streamProcessor');
const logger = require('./utils/logger');
const config = require('./config/config');

class VideoProcessorServer {
  constructor() {
    this.app = express();
    this.server = http.createServer(this.app);
    this.wss = new WebSocket.Server({ server: this.server });
    this.port = config.port || 8007;
    
    this.setupMiddleware();
    this.setupRoutes();
    this.setupWebSocket();
    
    this.processors = this.initializeProcessors();
    this.streamProcessor = new StreamProcessor({
      outputDir: config.outputDir,
      tempDir: config.tempDir,
      maxConcurrentStreams: config.maxConcurrentStreams
    });
  }

  initializeProcessors() {
    return {
      keyframeExtractor: new KeyframeExtractor({
        outputDir: path.join(config.outputDir, 'keyframes'),
        threshold: config.keyframe?.threshold,
        maxKeyframes: config.keyframe?.maxKeyframes
      }),
      
      thumbnailGenerator: new ThumbnailGenerator({
        outputDir: path.join(config.outputDir, 'thumbnails'),
        previewDir: path.join(config.outputDir, 'previews'),
        thumbnailSizes: config.thumbnail?.sizes
      }),
      
      sceneDetector: new SceneDetector({
        outputDir: path.join(config.outputDir, 'scenes'),
        threshold: config.scene?.threshold,
        minSceneDuration: config.scene?.minDuration
      }),
      
      ocrProcessor: new OCRProcessor({
        outputDir: path.join(config.outputDir, 'ocr'),
        languages: config.ocr?.languages,
        confidence: config.ocr?.confidence
      }),
      
      aiSummarizer: new AISummarizer({
        outputDir: path.join(config.outputDir, 'summaries'),
        aiProvider: config.ai?.provider,
        model: config.ai?.model,
        aiOrchestratorUrl: config.ai?.orchestratorUrl
      }),
      
      subtitleProcessor: new SubtitleProcessor({
        outputDir: path.join(config.outputDir, 'subtitles'),
        indexGranularity: config.subtitle?.indexGranularity
      })
    };
  }

  setupMiddleware() {
    this.app.use(helmet());
    this.app.use(compression());
    this.app.use(cors({
      origin: config.cors?.origins || '*',
      credentials: true
    }));
    this.app.use(express.json({ limit: '50mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '50mb' }));

    const storage = multer.diskStorage({
      destination: async (req, file, cb) => {
        const uploadDir = path.join(config.tempDir, 'uploads');
        await fs.mkdir(uploadDir, { recursive: true });
        cb(null, uploadDir);
      },
      filename: (req, file, cb) => {
        const uniqueName = `${uuidv4()}_${file.originalname}`;
        cb(null, uniqueName);
      }
    });

    this.upload = multer({
      storage,
      limits: {
        fileSize: config.upload?.maxFileSize || 1024 * 1024 * 1024,
      },
      fileFilter: (req, file, cb) => {
        const allowedTypes = config.upload?.allowedTypes || [
          'video/mp4', 'video/avi', 'video/mkv', 'video/mov', 'video/wmv', 'video/flv'
        ];
        
        if (allowedTypes.includes(file.mimetype)) {
          cb(null, true);
        } else {
          cb(new Error(`Unsupported file type: ${file.mimetype}`));
        }
      }
    });

    this.app.use('/output', express.static(config.outputDir));
    this.app.use('/temp', express.static(config.tempDir));
  }

  setupRoutes() {
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: require('../package.json').version,
        uptime: process.uptime()
      });
    });

    this.app.get('/api/status', async (req, res) => {
      try {
        const activeStreams = await this.streamProcessor.getAllActiveStreams();
        res.json({
          activeStreams: activeStreams.length,
          streams: activeStreams,
          processors: Object.keys(this.processors),
          config: {
            maxConcurrentStreams: config.maxConcurrentStreams,
            supportedFormats: config.upload?.allowedTypes || []
          }
        });
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/upload', this.upload.single('video'), async (req, res) => {
      try {
        if (!req.file) {
          return res.status(400).json({ error: 'No video file provided' });
        }

        const sessionId = uuidv4();
        const processingOptions = {
          extractKeyframes: req.body.extractKeyframes !== 'false',
          generateThumbnails: req.body.generateThumbnails !== 'false',
          detectScenes: req.body.detectScenes !== 'false',
          extractOCR: req.body.extractOCR !== 'false',
          extractSubtitles: req.body.extractSubtitles !== 'false',
          generateSummary: req.body.generateSummary !== 'false',
          ...JSON.parse(req.body.options || '{}')
        };

        const result = await this.streamProcessor.startStreamProcessing(
          req.file.path,
          processingOptions
        );

        res.json({
          ...result,
          fileInfo: {
            originalName: req.file.originalname,
            size: req.file.size,
            uploadPath: req.file.path
          },
          websocketUrl: `/ws?sessionId=${result.sessionId}`
        });

      } catch (error) {
        logger.error('Upload processing failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/process-url', async (req, res) => {
      try {
        const { videoUrl, options = {} } = req.body;
        
        if (!videoUrl) {
          return res.status(400).json({ error: 'No video URL provided' });
        }

        const sessionId = uuidv4();
        const result = await this.streamProcessor.startStreamProcessing(
          videoUrl,
          options
        );

        res.json({
          ...result,
          websocketUrl: `/ws?sessionId=${result.sessionId}`
        });

      } catch (error) {
        logger.error('URL processing failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/keyframes/:videoPath', async (req, res) => {
      try {
        const videoPath = decodeURIComponent(req.params.videoPath);
        const options = {
          method: req.query.method || 'adaptive',
          count: parseInt(req.query.count) || undefined,
          onProgress: (progress) => {
            if (req.query.realtime === 'true') {
              res.write(`data: ${JSON.stringify({ progress })}\n\n`);
            }
          }
        };

        if (req.query.realtime === 'true') {
          res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
          });
        }

        const result = options.method === 'uniform' ?
          await this.processors.keyframeExtractor.extractUniformKeyframes(videoPath, options.count) :
          await this.processors.keyframeExtractor.extractKeyframes(videoPath, options);

        if (req.query.realtime === 'true') {
          res.write(`data: ${JSON.stringify(result)}\n\n`);
          res.end();
        } else {
          res.json(result);
        }

      } catch (error) {
        logger.error('Keyframe extraction failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/thumbnails', async (req, res) => {
      try {
        const { videoPath, timestamps, options = {} } = req.body;
        
        if (!videoPath) {
          return res.status(400).json({ error: 'Video path required' });
        }

        const result = timestamps && timestamps.length > 0 ?
          await this.processors.thumbnailGenerator.generateMultipleThumbnails(videoPath, timestamps, options) :
          await this.processors.thumbnailGenerator.generateThumbnail(videoPath, options.timestamp, options);

        res.json(result);

      } catch (error) {
        logger.error('Thumbnail generation failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/scenes', async (req, res) => {
      try {
        const { videoPath, options = {} } = req.body;
        
        if (!videoPath) {
          return res.status(400).json({ error: 'Video path required' });
        }

        const result = await this.processors.sceneDetector.detectScenes(videoPath, options);
        res.json(result);

      } catch (error) {
        logger.error('Scene detection failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/ocr', async (req, res) => {
      try {
        const { videoPath, options = {} } = req.body;
        
        if (!videoPath) {
          return res.status(400).json({ error: 'Video path required' });
        }

        const result = await this.processors.ocrProcessor.extractTextFromVideo(videoPath, options);
        res.json(result);

      } catch (error) {
        logger.error('OCR processing failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/subtitles', async (req, res) => {
      try {
        const { videoPath, options = {} } = req.body;
        
        if (!videoPath) {
          return res.status(400).json({ error: 'Video path required' });
        }

        const result = await this.processors.subtitleProcessor.extractSubtitles(videoPath, options);
        res.json(result);

      } catch (error) {
        logger.error('Subtitle extraction failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/search-subtitles', async (req, res) => {
      try {
        const { sessionId, query, options = {} } = req.body;
        
        if (!sessionId || !query) {
          return res.status(400).json({ error: 'Session ID and query required' });
        }

        const indexPath = path.join(config.outputDir, 'subtitles', `search_index_${sessionId}.json`);
        const indexData = JSON.parse(await fs.readFile(indexPath, 'utf8'));
        
        const result = await this.processors.subtitleProcessor.searchSubtitles(indexData, query, options);
        res.json(result);

      } catch (error) {
        logger.error('Subtitle search failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/summary', async (req, res) => {
      try {
        const { videoData, options = {} } = req.body;
        
        if (!videoData) {
          return res.status(400).json({ error: 'Video data required' });
        }

        const result = await this.processors.aiSummarizer.generateVideoSummary(videoData, options);
        res.json(result);

      } catch (error) {
        logger.error('Summary generation failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/stream/:sessionId', async (req, res) => {
      try {
        const { sessionId } = req.params;
        const result = await this.streamProcessor.getStreamStatus(sessionId);
        res.json(result);

      } catch (error) {
        logger.error('Stream status failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.delete('/api/stream/:sessionId', async (req, res) => {
      try {
        const { sessionId } = req.params;
        await this.streamProcessor.cancelStreamProcessing(sessionId);
        res.json({ message: 'Stream cancelled' });

      } catch (error) {
        logger.error('Stream cancellation failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/results/:sessionId', async (req, res) => {
      try {
        const { sessionId } = req.params;
        const resultsPath = path.join(config.outputDir, `stream_results_${sessionId}.json`);
        
        const resultsData = JSON.parse(await fs.readFile(resultsPath, 'utf8'));
        res.json(resultsData);

      } catch (error) {
        if (error.code === 'ENOENT') {
          res.status(404).json({ error: 'Results not found' });
        } else {
          logger.error('Results retrieval failed:', error);
          res.status(500).json({ error: error.message });
        }
      }
    });

    this.app.use((err, req, res, next) => {
      logger.error('Unhandled error:', err);
      res.status(500).json({
        error: 'Internal server error',
        message: err.message
      });
    });

    this.app.use((req, res) => {
      res.status(404).json({
        error: 'Not found',
        path: req.path
      });
    });
  }

  setupWebSocket() {
    this.wss.on('connection', (ws, req) => {
      const url = new URL(req.url, `http://${req.headers.host}`);
      const sessionId = url.searchParams.get('sessionId');

      if (!sessionId) {
        ws.close(1008, 'Session ID required');
        return;
      }

      logger.info(`WebSocket connection established for session ${sessionId}`);

      ws.send(JSON.stringify({
        type: 'connection_established',
        sessionId,
        timestamp: new Date().toISOString()
      }));

      ws.on('error', (error) => {
        logger.error(`WebSocket error for session ${sessionId}:`, error);
      });

      ws.on('close', () => {
        logger.info(`WebSocket connection closed for session ${sessionId}`);
      });
    });
  }

  async start() {
    try {
      await fs.mkdir(config.outputDir, { recursive: true });
      await fs.mkdir(config.tempDir, { recursive: true });

      this.server.listen(this.port, () => {
        logger.info(`Video Processor Server started on port ${this.port}`);
        logger.info(`Health check: http://localhost:${this.port}/health`);
        logger.info(`API endpoints: http://localhost:${this.port}/api/`);
        logger.info(`WebSocket endpoint: ws://localhost:${this.port}/ws`);
      });

      process.on('SIGTERM', () => this.gracefulShutdown());
      process.on('SIGINT', () => this.gracefulShutdown());

    } catch (error) {
      logger.error('Failed to start server:', error);
      process.exit(1);
    }
  }

  async gracefulShutdown() {
    logger.info('Shutting down gracefully...');

    try {
      await this.streamProcessor.cleanup();
      
      this.wss.close(() => {
        logger.info('WebSocket server closed');
      });

      this.server.close(() => {
        logger.info('HTTP server closed');
        process.exit(0);
      });

      setTimeout(() => {
        logger.error('Forced shutdown after timeout');
        process.exit(1);
      }, 30000);

    } catch (error) {
      logger.error('Error during shutdown:', error);
      process.exit(1);
    }
  }
}

if (require.main === module) {
  const server = new VideoProcessorServer();
  server.start();
}

module.exports = VideoProcessorServer;