const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const multer = require('multer');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { RateLimiterMemory } = require('rate-limiter-flexible');
const { Server } = require('socket.io');
const http = require('http');
const path = require('path');
const fs = require('fs-extra');
const moment = require('moment');

// Import exporters and generators
const PDFExporter = require('./exporters/pdfExporter');
const ArchiveExporter = require('./exporters/archiveExporter');
const GDPRExporter = require('./exporters/gdprExporter');
const WebsiteGenerator = require('./generators/websiteGenerator');
const PhotoBookGenerator = require('./generators/photoBookGenerator');
const BulkExporter = require('./utils/bulkExporter');
const { CloudProviderManager } = require('./cloud/cloudProviders');

// Import utilities
const logger = require('./utils/logger');
const config = require('./config/config');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: config.cors.origin,
    methods: ['GET', 'POST']
  }
});

// Initialize components
const bulkExporter = new BulkExporter(config.bulkExport);
const cloudManager = new CloudProviderManager(config.cloudProviders);

// Middleware
app.use(helmet());
app.use(compression());
app.use(cors(config.cors));
app.use(morgan('combined', {
  stream: { write: (message) => logger.info(message.trim()) }
}));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Rate limiting
const rateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP'
});
app.use('/api/', rateLimiter);

// Advanced rate limiting for export operations
const exportLimiter = new RateLimiterMemory({
  keyName: 'export_operations',
  points: 10, // Number of operations
  duration: 60, // per 60 seconds
});

// File upload configuration
const storage = multer.memoryStorage();
const upload = multer({
  storage,
  limits: {
    fileSize: config.upload.maxFileSize || 100 * 1024 * 1024 // 100MB
  },
  fileFilter: (req, file, cb) => {
    const allowedTypes = config.upload.allowedTypes || [
      'application/pdf',
      'application/zip',
      'image/jpeg',
      'image/png',
      'text/plain',
      'application/json'
    ];
    
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error(`File type not allowed: ${file.mimetype}`));
    }
  }
});

// Socket.IO for real-time progress updates
io.on('connection', (socket) => {
  logger.info(`Client connected: ${socket.id}`);
  
  socket.on('subscribe_job', (jobId) => {
    socket.join(`job_${jobId}`);
    logger.info(`Client ${socket.id} subscribed to job ${jobId}`);
  });
  
  socket.on('disconnect', () => {
    logger.info(`Client disconnected: ${socket.id}`);
  });
});

// Bulk exporter event handlers
bulkExporter.on('job_progress', (data) => {
  io.to(`job_${data.jobId}`).emit('progress', data);
});

bulkExporter.on('job_completed', (job) => {
  io.to(`job_${job.id}`).emit('completed', job);
});

bulkExporter.on('job_failed', (job) => {
  io.to(`job_${job.id}`).emit('failed', job);
});

// Helper middleware for export rate limiting
async function checkExportRateLimit(req, res, next) {
  try {
    await exportLimiter.consume(req.ip);
    next();
  } catch (rejRes) {
    res.status(429).json({
      success: false,
      error: 'Too many export operations',
      retryAfter: Math.round(rejRes.msBeforeNext / 1000)
    });
  }
}

// Helper function to save uploaded file
async function saveUploadedFile(file) {
  const tempDir = path.join(__dirname, '../temp');
  await fs.ensureDir(tempDir);
  
  const filename = `${Date.now()}_${file.originalname}`;
  const filepath = path.join(tempDir, filename);
  
  await fs.writeFile(filepath, file.buffer);
  return { filepath, filename };
}

// API Routes

// Health check
app.get('/api/health', (req, res) => {
  res.json({
    success: true,
    status: 'healthy',
    timestamp: moment().toISOString(),
    services: {
      bulkExporter: 'running',
      cloudProviders: cloudManager.getAvailableProviders(),
      uptime: process.uptime()
    }
  });
});

// PDF Export
app.post('/api/export/pdf', checkExportRateLimit, upload.single('file'), async (req, res) => {
  try {
    const { data, metadata = '{}', options = '{}' } = req.body;
    const parsedMetadata = JSON.parse(metadata);
    const parsedOptions = JSON.parse(options);

    let exportData;
    if (req.file) {
      const { filepath } = await saveUploadedFile(req.file);
      // Process file content based on type
      exportData = await processFileForExport(filepath);
    } else {
      exportData = JSON.parse(data);
    }

    const outputPath = path.join(__dirname, '../output', `export_${Date.now()}.pdf`);
    await fs.ensureDir(path.dirname(outputPath));

    const pdfExporter = new PDFExporter(parsedOptions);
    const result = await pdfExporter.exportToPDF(exportData, outputPath, parsedMetadata);

    res.json({
      success: true,
      ...result,
      downloadUrl: `/api/download/${path.basename(outputPath)}`
    });
  } catch (error) {
    logger.error('PDF export failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Archive Export (ZIP/TAR.GZ)
app.post('/api/export/archive', checkExportRateLimit, upload.array('files'), async (req, res) => {
  try {
    const { format = 'zip', metadata = '{}', options = '{}' } = req.body;
    const parsedMetadata = JSON.parse(metadata);
    const parsedOptions = JSON.parse(options);

    if (!req.files || req.files.length === 0) {
      return res.status(400).json({
        success: false,
        error: 'No files provided'
      });
    }

    // Save uploaded files
    const sources = [];
    for (const file of req.files) {
      const { filepath, filename } = await saveUploadedFile(file);
      sources.push({
        path: filepath,
        name: filename
      });
    }

    const outputPath = path.join(__dirname, '../output', `archive_${Date.now()}.${format}`);
    await fs.ensureDir(path.dirname(outputPath));

    const archiveExporter = new ArchiveExporter(parsedOptions);
    
    let result;
    if (format === 'tar.gz' || format === 'tgz') {
      result = await archiveExporter.createTarGzArchive(sources, outputPath, parsedMetadata);
    } else {
      result = await archiveExporter.createZipArchive(sources, outputPath, parsedMetadata);
    }

    res.json({
      success: true,
      ...result,
      downloadUrl: `/api/download/${path.basename(outputPath)}`
    });
  } catch (error) {
    logger.error('Archive export failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Website Generation
app.post('/api/generate/website', checkExportRateLimit, async (req, res) => {
  try {
    const { data, metadata = '{}', options = '{}' } = req.body;
    const parsedData = typeof data === 'string' ? JSON.parse(data) : data;
    const parsedMetadata = JSON.parse(metadata);
    const parsedOptions = JSON.parse(options);

    const outputDir = path.join(__dirname, '../output', `website_${Date.now()}`);
    await fs.ensureDir(outputDir);

    const websiteGenerator = new WebsiteGenerator(parsedOptions);
    const result = await websiteGenerator.generateStaticWebsite(parsedData, outputDir, parsedMetadata);

    // Create ZIP of website
    const archiveExporter = new ArchiveExporter();
    const websiteZip = path.join(path.dirname(outputDir), `${path.basename(outputDir)}.zip`);
    const sources = [{ path: outputDir, name: path.basename(outputDir) }];
    await archiveExporter.createZipArchive(sources, websiteZip);

    res.json({
      success: true,
      ...result,
      downloadUrl: `/api/download/${path.basename(websiteZip)}`
    });
  } catch (error) {
    logger.error('Website generation failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Photo Book Generation
app.post('/api/generate/photobook', checkExportRateLimit, upload.array('photos'), async (req, res) => {
  try {
    const { metadata = '{}', options = '{}' } = req.body;
    const parsedMetadata = JSON.parse(metadata);
    const parsedOptions = JSON.parse(options);

    if (!req.files || req.files.length === 0) {
      return res.status(400).json({
        success: false,
        error: 'No photos provided'
      });
    }

    // Save uploaded photos
    const photos = [];
    for (const file of req.files) {
      const { filepath, filename } = await saveUploadedFile(file);
      photos.push({
        path: filepath,
        caption: '', // Could be extracted from metadata
        metadata: {}
      });
    }

    const outputPath = path.join(__dirname, '../output', `photobook_${Date.now()}.pdf`);
    await fs.ensureDir(path.dirname(outputPath));

    const photoBookGenerator = new PhotoBookGenerator(parsedOptions);
    const result = await photoBookGenerator.createPhotoBook(photos, outputPath, parsedMetadata);

    res.json({
      success: true,
      ...result,
      downloadUrl: `/api/download/${path.basename(outputPath)}`
    });
  } catch (error) {
    logger.error('Photo book generation failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// GDPR Export
app.post('/api/export/gdpr', checkExportRateLimit, async (req, res) => {
  try {
    const { userData, requestDetails = '{}', options = '{}' } = req.body;
    const parsedRequestDetails = JSON.parse(requestDetails);
    const parsedOptions = JSON.parse(options);

    const outputPath = path.join(__dirname, '../output', `gdpr_export_${Date.now()}.zip`);
    await fs.ensureDir(path.dirname(outputPath));

    const gdprExporter = new GDPRExporter(parsedOptions);
    const result = await gdprExporter.exportGDPRData(userData, outputPath, parsedRequestDetails);

    res.json({
      success: true,
      ...result,
      downloadUrl: `/api/download/${path.basename(outputPath)}`
    });
  } catch (error) {
    logger.error('GDPR export failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Bulk Export Operations
app.post('/api/bulk/export', checkExportRateLimit, async (req, res) => {
  try {
    const jobConfig = req.body;
    const result = await bulkExporter.addBulkExportJob(jobConfig);

    res.json({
      success: true,
      ...result
    });
  } catch (error) {
    logger.error('Bulk export job creation failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/bulk/job/:jobId', (req, res) => {
  try {
    const { jobId } = req.params;
    const status = bulkExporter.getJobStatus(jobId);

    if (status.error) {
      return res.status(404).json({
        success: false,
        error: status.error
      });
    }

    res.json({
      success: true,
      job: status
    });
  } catch (error) {
    logger.error('Job status retrieval failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/bulk/job/:jobId/cancel', (req, res) => {
  try {
    const { jobId } = req.params;
    const result = bulkExporter.cancelJob(jobId);

    res.json({
      success: true,
      ...result
    });
  } catch (error) {
    logger.error('Job cancellation failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/bulk/metrics', (req, res) => {
  try {
    const metrics = bulkExporter.getMetrics();
    res.json({
      success: true,
      metrics
    });
  } catch (error) {
    logger.error('Metrics retrieval failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Cloud Provider Integration
app.post('/api/cloud/upload', checkExportRateLimit, upload.single('file'), async (req, res) => {
  try {
    const { provider, options = '{}' } = req.body;
    const parsedOptions = JSON.parse(options);

    if (!req.file) {
      return res.status(400).json({
        success: false,
        error: 'No file provided'
      });
    }

    const { filepath } = await saveUploadedFile(req.file);
    const result = await cloudManager.uploadToCloud(filepath, provider, parsedOptions);

    // Cleanup local file
    await fs.remove(filepath);

    res.json({
      success: true,
      ...result
    });
  } catch (error) {
    logger.error('Cloud upload failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/cloud/share/:provider/:fileId', async (req, res) => {
  try {
    const { provider, fileId } = req.params;
    const { options = '{}' } = req.body;
    const parsedOptions = JSON.parse(options);

    const result = await cloudManager.shareFile(fileId, provider, parsedOptions);

    res.json({
      success: true,
      ...result
    });
  } catch (error) {
    logger.error('Cloud share failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/cloud/providers', (req, res) => {
  try {
    const providers = cloudManager.getAvailableProviders();
    res.json({
      success: true,
      providers
    });
  } catch (error) {
    logger.error('Provider list retrieval failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// File Download
app.get('/api/download/:filename', async (req, res) => {
  try {
    const { filename } = req.params;
    const filepath = path.join(__dirname, '../output', filename);

    if (!await fs.pathExists(filepath)) {
      return res.status(404).json({
        success: false,
        error: 'File not found'
      });
    }

    const stats = await fs.stat(filepath);
    res.setHeader('Content-Length', stats.size);
    res.setHeader('Content-Type', 'application/octet-stream');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);

    const stream = fs.createReadStream(filepath);
    stream.pipe(res);

    // Schedule file cleanup after download
    setTimeout(async () => {
      try {
        await fs.remove(filepath);
        logger.info(`Cleaned up downloaded file: ${filepath}`);
      } catch (error) {
        logger.warn(`Failed to cleanup file: ${filepath}`, error);
      }
    }, 60000); // 1 minute delay
  } catch (error) {
    logger.error('File download failed:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Error handling middleware
app.use((error, req, res, next) => {
  if (error instanceof multer.MulterError) {
    if (error.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({
        success: false,
        error: 'File too large'
      });
    }
  }

  logger.error('Unhandled error:', error);
  res.status(500).json({
    success: false,
    error: 'Internal server error'
  });
});

// Helper function to process files for export
async function processFileForExport(filepath) {
  const ext = path.extname(filepath).toLowerCase();
  
  switch (ext) {
    case '.json':
      return JSON.parse(await fs.readFile(filepath, 'utf8'));
    case '.txt':
      return await fs.readFile(filepath, 'utf8');
    case '.pdf':
    case '.jpg':
    case '.jpeg':
    case '.png':
      return {
        type: 'file',
        path: filepath,
        filename: path.basename(filepath)
      };
    default:
      return {
        type: 'binary',
        path: filepath,
        filename: path.basename(filepath)
      };
  }
}

// Cleanup old files periodically
setInterval(async () => {
  try {
    const tempDir = path.join(__dirname, '../temp');
    const outputDir = path.join(__dirname, '../output');
    
    const cutoff = Date.now() - (24 * 60 * 60 * 1000); // 24 hours
    
    await cleanupOldFiles(tempDir, cutoff);
    await cleanupOldFiles(outputDir, cutoff);
  } catch (error) {
    logger.error('File cleanup failed:', error);
  }
}, 60 * 60 * 1000); // Run every hour

async function cleanupOldFiles(dir, cutoff) {
  if (!await fs.pathExists(dir)) return;
  
  const files = await fs.readdir(dir);
  
  for (const file of files) {
    const filepath = path.join(dir, file);
    const stats = await fs.stat(filepath);
    
    if (stats.mtime.getTime() < cutoff) {
      await fs.remove(filepath);
      logger.info(`Cleaned up old file: ${filepath}`);
    }
  }
}

// Start server
const PORT = config.server.port || 8009;
const HOST = config.server.host || 'localhost';

server.listen(PORT, HOST, () => {
  logger.info(`Data Export Service running on http://${HOST}:${PORT}`);
  logger.info(`Available cloud providers: ${cloudManager.getAvailableProviders().join(', ')}`);
});

module.exports = app;