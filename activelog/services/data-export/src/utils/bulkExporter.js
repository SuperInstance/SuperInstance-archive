const EventEmitter = require('events');
const fs = require('fs-extra');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');
const cron = require('node-cron');
const logger = require('./logger');

class BulkExporter extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      maxConcurrentJobs: options.maxConcurrentJobs || 3,
      jobTimeout: options.jobTimeout || 30 * 60 * 1000, // 30 minutes
      retryAttempts: options.retryAttempts || 3,
      retryDelay: options.retryDelay || 5000, // 5 seconds
      progressUpdateInterval: options.progressUpdateInterval || 1000, // 1 second
      enableScheduling: options.enableScheduling || false,
      tempDir: options.tempDir || path.join(__dirname, '../../temp'),
      ...options
    };

    this.jobs = new Map();
    this.queue = [];
    this.activeJobs = new Set();
    this.completedJobs = new Map();
    this.failedJobs = new Map();
    
    this.setupProgressTracking();
    this.setupScheduler();
  }

  async addBulkExportJob(jobConfig) {
    try {
      const jobId = uuidv4();
      const job = {
        id: jobId,
        type: jobConfig.type || 'bulk_export',
        name: jobConfig.name || `Bulk Export ${jobId.slice(0, 8)}`,
        config: jobConfig,
        status: 'queued',
        progress: 0,
        totalItems: jobConfig.items ? jobConfig.items.length : 0,
        processedItems: 0,
        failedItems: 0,
        createdAt: moment().toISOString(),
        startedAt: null,
        completedAt: null,
        outputPaths: [],
        errors: [],
        metadata: jobConfig.metadata || {}
      };

      this.jobs.set(jobId, job);
      this.queue.push(jobId);

      logger.info(`Bulk export job added: ${jobId} (${job.name})`);
      this.emit('job_added', job);

      // Start processing if there's capacity
      this.processQueue();

      return { jobId, status: 'queued' };
    } catch (error) {
      logger.error('Failed to add bulk export job:', error);
      throw error;
    }
  }

  async processQueue() {
    while (this.queue.length > 0 && this.activeJobs.size < this.options.maxConcurrentJobs) {
      const jobId = this.queue.shift();
      await this.startJob(jobId);
    }
  }

  async startJob(jobId) {
    const job = this.jobs.get(jobId);
    if (!job) return;

    try {
      job.status = 'running';
      job.startedAt = moment().toISOString();
      this.activeJobs.add(jobId);

      logger.info(`Starting bulk export job: ${jobId}`);
      this.emit('job_started', job);

      // Set timeout for job
      const timeout = setTimeout(() => {
        this.handleJobTimeout(jobId);
      }, this.options.jobTimeout);

      // Process job based on type
      const result = await this.executeJob(job);

      clearTimeout(timeout);

      job.status = 'completed';
      job.completedAt = moment().toISOString();
      job.progress = 100;
      job.outputPaths = result.outputPaths || [];

      this.activeJobs.delete(jobId);
      this.completedJobs.set(jobId, job);

      logger.info(`Bulk export job completed: ${jobId}`);
      this.emit('job_completed', job);

      // Process next job in queue
      this.processQueue();

    } catch (error) {
      await this.handleJobError(jobId, error);
    }
  }

  async executeJob(job) {
    const { config } = job;
    const results = { outputPaths: [], errors: [] };

    switch (job.type) {
      case 'bulk_export':
        return await this.executeBulkExport(job, results);
      case 'scheduled_export':
        return await this.executeScheduledExport(job, results);
      case 'batch_process':
        return await this.executeBatchProcess(job, results);
      default:
        throw new Error(`Unknown job type: ${job.type}`);
    }
  }

  async executeBulkExport(job, results) {
    const { config } = job;
    const { items, exporters, options } = config;

    // Create temporary directory for this job
    const jobTempDir = path.join(this.options.tempDir, `job_${job.id}`);
    await fs.ensureDir(jobTempDir);

    try {
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        
        try {
          await this.updateJobProgress(job, (i / items.length) * 100, `Processing item ${i + 1}/${items.length}`);

          const itemResult = await this.processExportItem(item, exporters, options, jobTempDir);
          results.outputPaths.push(...itemResult.outputPaths);
          
          job.processedItems++;
        } catch (error) {
          job.failedItems++;
          results.errors.push({
            item: item.id || i,
            error: error.message
          });
          logger.warn(`Failed to process export item ${i}:`, error);
        }
      }

      // Create final consolidated output if requested
      if (options.consolidateOutputs) {
        const consolidatedPath = await this.consolidateOutputs(results.outputPaths, job, options);
        results.outputPaths = [consolidatedPath];
      }

      return results;
    } finally {
      // Cleanup temporary directory
      if (options.cleanupTemp !== false) {
        await fs.remove(jobTempDir);
      }
    }
  }

  async executeScheduledExport(job, results) {
    // Execute export based on schedule configuration
    const { config } = job;
    const { schedule, exportConfig } = config;

    // Create bulk export job for scheduled data
    const scheduledData = await this.gatherScheduledData(schedule);
    
    const bulkConfig = {
      ...exportConfig,
      items: scheduledData
    };

    return await this.executeBulkExport({ ...job, config: bulkConfig }, results);
  }

  async executeBatchProcess(job, results) {
    const { config } = job;
    const { batches, batchSize } = config;

    for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
      const batch = batches[batchIndex];
      
      await this.updateJobProgress(
        job, 
        (batchIndex / batches.length) * 100, 
        `Processing batch ${batchIndex + 1}/${batches.length}`
      );

      try {
        const batchResult = await this.processBatch(batch, job.config);
        results.outputPaths.push(...batchResult.outputPaths);
      } catch (error) {
        results.errors.push({
          batch: batchIndex,
          error: error.message
        });
      }
    }

    return results;
  }

  async processExportItem(item, exporters, options, tempDir) {
    const itemResults = { outputPaths: [] };

    for (const exporterConfig of exporters) {
      const { type, options: exporterOptions } = exporterConfig;
      const outputPath = path.join(tempDir, `${item.id || 'item'}_${type}_${Date.now()}`);

      const exporter = this.getExporter(type);
      const result = await exporter.export(item.data, outputPath, {
        ...exporterOptions,
        metadata: item.metadata
      });

      itemResults.outputPaths.push(result.outputPath);
    }

    return itemResults;
  }

  async consolidateOutputs(outputPaths, job, options) {
    const consolidationType = options.consolidationType || 'zip';
    const consolidatedPath = path.join(
      this.options.tempDir,
      `consolidated_${job.id}.${consolidationType}`
    );

    switch (consolidationType) {
      case 'zip':
        const ArchiveExporter = require('../exporters/archiveExporter');
        const archiver = new ArchiveExporter();
        const sources = outputPaths.map(path => ({ path, name: path.split('/').pop() }));
        await archiver.createZipArchive(sources, consolidatedPath, job.metadata);
        break;
      
      case 'tar.gz':
        const tarArchiver = new ArchiveExporter();
        const tarSources = outputPaths.map(path => ({ path, name: path.split('/').pop() }));
        await tarArchiver.createTarGzArchive(tarSources, consolidatedPath, job.metadata);
        break;
      
      default:
        throw new Error(`Unsupported consolidation type: ${consolidationType}`);
    }

    return consolidatedPath;
  }

  async updateJobProgress(job, progress, status) {
    job.progress = Math.round(progress);
    job.currentStatus = status;
    job.updatedAt = moment().toISOString();

    this.emit('job_progress', {
      jobId: job.id,
      progress: job.progress,
      status,
      processedItems: job.processedItems,
      totalItems: job.totalItems
    });
  }

  async handleJobError(jobId, error) {
    const job = this.jobs.get(jobId);
    if (!job) return;

    job.errors.push({
      timestamp: moment().toISOString(),
      error: error.message,
      stack: error.stack
    });

    // Retry logic
    if (job.retryCount < this.options.retryAttempts) {
      job.retryCount = (job.retryCount || 0) + 1;
      job.status = 'retrying';
      
      logger.warn(`Retrying job ${jobId} (attempt ${job.retryCount}/${this.options.retryAttempts})`);
      this.emit('job_retrying', job);

      setTimeout(() => {
        this.startJob(jobId);
      }, this.options.retryDelay);
    } else {
      job.status = 'failed';
      job.completedAt = moment().toISOString();
      this.activeJobs.delete(jobId);
      this.failedJobs.set(jobId, job);

      logger.error(`Job failed permanently: ${jobId}`, error);
      this.emit('job_failed', job);

      // Process next job in queue
      this.processQueue();
    }
  }

  handleJobTimeout(jobId) {
    const job = this.jobs.get(jobId);
    if (job && job.status === 'running') {
      const error = new Error(`Job timeout: ${this.options.jobTimeout}ms`);
      this.handleJobError(jobId, error);
    }
  }

  getJobStatus(jobId) {
    const job = this.jobs.get(jobId);
    if (!job) {
      return { error: 'Job not found' };
    }

    return {
      id: job.id,
      name: job.name,
      type: job.type,
      status: job.status,
      progress: job.progress,
      totalItems: job.totalItems,
      processedItems: job.processedItems,
      failedItems: job.failedItems,
      createdAt: job.createdAt,
      startedAt: job.startedAt,
      completedAt: job.completedAt,
      outputPaths: job.outputPaths,
      errors: job.errors,
      currentStatus: job.currentStatus
    };
  }

  getAllJobStatuses() {
    const statuses = {};
    
    for (const [jobId, job] of this.jobs) {
      statuses[jobId] = this.getJobStatus(jobId);
    }

    return statuses;
  }

  async cancelJob(jobId) {
    const job = this.jobs.get(jobId);
    if (!job) {
      throw new Error('Job not found');
    }

    if (job.status === 'completed' || job.status === 'failed') {
      throw new Error('Cannot cancel completed or failed job');
    }

    if (job.status === 'running') {
      job.status = 'cancelled';
      this.activeJobs.delete(jobId);
    } else if (job.status === 'queued') {
      const queueIndex = this.queue.indexOf(jobId);
      if (queueIndex > -1) {
        this.queue.splice(queueIndex, 1);
      }
      job.status = 'cancelled';
    }

    job.completedAt = moment().toISOString();
    logger.info(`Job cancelled: ${jobId}`);
    this.emit('job_cancelled', job);

    return { success: true, status: 'cancelled' };
  }

  async pauseJob(jobId) {
    const job = this.jobs.get(jobId);
    if (!job) {
      throw new Error('Job not found');
    }

    if (job.status === 'running') {
      job.status = 'paused';
      this.emit('job_paused', job);
      return { success: true, status: 'paused' };
    }

    throw new Error('Can only pause running jobs');
  }

  async resumeJob(jobId) {
    const job = this.jobs.get(jobId);
    if (!job) {
      throw new Error('Job not found');
    }

    if (job.status === 'paused') {
      job.status = 'queued';
      this.queue.unshift(jobId); // Add to front of queue
      this.emit('job_resumed', job);
      this.processQueue();
      return { success: true, status: 'queued' };
    }

    throw new Error('Can only resume paused jobs');
  }

  scheduleExport(schedule, exportConfig) {
    if (!this.options.enableScheduling) {
      throw new Error('Scheduling is not enabled');
    }

    const scheduleId = uuidv4();
    
    const task = cron.schedule(schedule.cronExpression, async () => {
      try {
        logger.info(`Executing scheduled export: ${scheduleId}`);
        
        const jobConfig = {
          type: 'scheduled_export',
          name: schedule.name || `Scheduled Export ${scheduleId.slice(0, 8)}`,
          schedule,
          exportConfig,
          metadata: {
            scheduleId,
            isScheduled: true
          }
        };

        await this.addBulkExportJob(jobConfig);
      } catch (error) {
        logger.error(`Scheduled export failed: ${scheduleId}`, error);
      }
    }, {
      scheduled: false,
      timezone: schedule.timezone || 'UTC'
    });

    task.start();
    
    logger.info(`Export scheduled: ${scheduleId} with cron ${schedule.cronExpression}`);
    return { scheduleId, success: true };
  }

  setupProgressTracking() {
    setInterval(() => {
      this.activeJobs.forEach(jobId => {
        const job = this.jobs.get(jobId);
        if (job && job.status === 'running') {
          this.emit('heartbeat', {
            jobId: job.id,
            progress: job.progress,
            status: job.currentStatus,
            uptime: moment().diff(moment(job.startedAt), 'seconds')
          });
        }
      });
    }, this.options.progressUpdateInterval);
  }

  setupScheduler() {
    // Cleanup completed jobs older than 24 hours
    cron.schedule('0 0 * * *', () => {
      const cutoff = moment().subtract(24, 'hours');
      
      for (const [jobId, job] of this.completedJobs) {
        if (moment(job.completedAt).isBefore(cutoff)) {
          this.completedJobs.delete(jobId);
          this.jobs.delete(jobId);
        }
      }

      for (const [jobId, job] of this.failedJobs) {
        if (moment(job.completedAt).isBefore(cutoff)) {
          this.failedJobs.delete(jobId);
          this.jobs.delete(jobId);
        }
      }

      logger.info('Cleaned up old job records');
    });
  }

  getExporter(type) {
    const exporters = {
      pdf: require('../exporters/pdfExporter'),
      zip: require('../exporters/archiveExporter'),
      website: require('../generators/websiteGenerator'),
      photobook: require('../generators/photoBookGenerator'),
      gdpr: require('../exporters/gdprExporter')
    };

    const ExporterClass = exporters[type];
    if (!ExporterClass) {
      throw new Error(`Unknown exporter type: ${type}`);
    }

    return new ExporterClass();
  }

  async gatherScheduledData(schedule) {
    // This would typically connect to data sources to gather data for scheduled exports
    // For now, return empty array - implement based on your data sources
    return [];
  }

  async processBatch(batch, config) {
    // Process a batch of items
    const results = { outputPaths: [] };
    // Implementation depends on batch configuration
    return results;
  }

  getQueueStatus() {
    return {
      queueLength: this.queue.length,
      activeJobs: this.activeJobs.size,
      completedJobs: this.completedJobs.size,
      failedJobs: this.failedJobs.size,
      maxConcurrentJobs: this.options.maxConcurrentJobs
    };
  }

  getMetrics() {
    const allJobs = Array.from(this.jobs.values());
    const completedJobs = allJobs.filter(job => job.status === 'completed');
    const failedJobs = allJobs.filter(job => job.status === 'failed');
    
    const totalItems = allJobs.reduce((sum, job) => sum + job.totalItems, 0);
    const processedItems = allJobs.reduce((sum, job) => sum + job.processedItems, 0);
    
    const avgProcessingTime = completedJobs.length > 0 
      ? completedJobs.reduce((sum, job) => {
          const duration = moment(job.completedAt).diff(moment(job.startedAt), 'seconds');
          return sum + duration;
        }, 0) / completedJobs.length
      : 0;

    return {
      totalJobs: allJobs.length,
      completedJobs: completedJobs.length,
      failedJobs: failedJobs.length,
      successRate: allJobs.length > 0 ? (completedJobs.length / allJobs.length) * 100 : 0,
      totalItems,
      processedItems,
      itemSuccessRate: totalItems > 0 ? (processedItems / totalItems) * 100 : 0,
      avgProcessingTimeSeconds: Math.round(avgProcessingTime),
      queueStatus: this.getQueueStatus()
    };
  }
}

module.exports = BulkExporter;