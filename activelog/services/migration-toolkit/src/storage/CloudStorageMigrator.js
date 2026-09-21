import AWS from 'aws-sdk';
import { Storage } from '@google-cloud/storage';
import { BlobServiceClient } from '@azure/storage-blob';
import fs from 'fs-extra';
import path from 'path';
import crypto from 'crypto';
import { EventEmitter } from 'events';
import logger from '../lib/logger.js';
import archiver from 'archiver';
import unzipper from 'unzipper';
import { createReadStream, createWriteStream } from 'fs';

/**
 * Cloud Storage Migration Service
 * Supports AWS S3, Google Cloud Storage, Azure Blob Storage, and more
 */
export class CloudStorageMigrator extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      concurrency: 5,
      chunkSize: 5 * 1024 * 1024, // 5MB chunks
      retryAttempts: 3,
      retryDelay: 1000,
      checksumValidation: true,
      compression: false,
      encryption: false,
      preserveMetadata: true,
      enableDeduplication: true,
      progressReporting: true,
      bandwidthLimit: null, // bytes per second
      ...options
    };

    this.providers = new Map();
    this.activeMigrations = new Map();
    this.migrationHistory = [];
    this.deduplicationCache = new Map();
    
    this.setupProviders();
    this.stats = {
      totalFiles: 0,
      transferredFiles: 0,
      totalBytes: 0,
      transferredBytes: 0,
      failedFiles: 0,
      skippedFiles: 0,
      deduplicatedFiles: 0,
      startTime: null,
      endTime: null,
      errors: []
    };
  }

  /**
   * Setup cloud storage providers
   */
  setupProviders() {
    // AWS S3 Provider
    this.registerProvider('aws', {
      name: 'Amazon S3',
      client: null,
      multipartThreshold: 100 * 1024 * 1024, // 100MB
      supportedFeatures: ['versioning', 'lifecycle', 'encryption', 'compression']
    });

    // Google Cloud Storage Provider
    this.registerProvider('gcp', {
      name: 'Google Cloud Storage',
      client: null,
      resumableThreshold: 100 * 1024 * 1024, // 100MB
      supportedFeatures: ['versioning', 'lifecycle', 'encryption']
    });

    // Azure Blob Storage Provider
    this.registerProvider('azure', {
      name: 'Azure Blob Storage',
      client: null,
      blockSize: 100 * 1024 * 1024, // 100MB
      supportedFeatures: ['versioning', 'lifecycle', 'encryption']
    });

    // Local File System Provider
    this.registerProvider('local', {
      name: 'Local File System',
      client: null,
      supportedFeatures: ['compression', 'encryption']
    });

    // FTP/SFTP Provider
    this.registerProvider('ftp', {
      name: 'FTP/SFTP',
      client: null,
      supportedFeatures: []
    });
  }

  /**
   * Register storage provider
   */
  registerProvider(name, config) {
    this.providers.set(name, config);
    logger.info(`Registered storage provider: ${name}`);
  }

  /**
   * Initialize provider client
   */
  async initializeProvider(providerName, config) {
    const provider = this.providers.get(providerName);
    if (!provider) {
      throw new Error(`Provider ${providerName} not found`);
    }

    switch (providerName) {
      case 'aws':
        AWS.config.update({
          accessKeyId: config.accessKeyId,
          secretAccessKey: config.secretAccessKey,
          region: config.region || 'us-east-1'
        });
        provider.client = new AWS.S3({
          endpoint: config.endpoint,
          s3ForcePathStyle: config.pathStyle || false,
          signatureVersion: 'v4'
        });
        break;

      case 'gcp':
        const gcpConfig = {
          projectId: config.projectId,
          keyFilename: config.keyFile
        };
        if (config.credentials) {
          gcpConfig.credentials = config.credentials;
        }
        provider.client = new Storage(gcpConfig);
        break;

      case 'azure':
        const connectionString = config.connectionString ||
          `DefaultEndpointsProtocol=https;AccountName=${config.accountName};AccountKey=${config.accountKey};EndpointSuffix=core.windows.net`;
        provider.client = BlobServiceClient.fromConnectionString(connectionString);
        break;

      case 'local':
        provider.client = {
          basePath: config.basePath || '/tmp/storage'
        };
        await fs.ensureDir(provider.client.basePath);
        break;

      case 'ftp':
        // FTP client initialization would go here
        provider.client = {
          host: config.host,
          port: config.port || 21,
          username: config.username,
          password: config.password,
          secure: config.secure || false
        };
        break;
    }

    logger.info(`Initialized ${providerName} provider`);
  }

  /**
   * Start migration between storage systems
   */
  async migrateStorage(migrationConfig) {
    const migrationId = this.generateMigrationId();
    logger.info(`Starting storage migration ${migrationId}`);

    const migration = {
      id: migrationId,
      source: migrationConfig.source,
      destination: migrationConfig.destination,
      options: { ...this.options, ...migrationConfig.options },
      status: 'in_progress',
      startTime: new Date(),
      endTime: null,
      stats: { ...this.stats },
      errors: []
    };

    this.activeMigrations.set(migrationId, migration);
    this.stats.startTime = migration.startTime;

    try {
      // Initialize providers
      await this.initializeProvider(migration.source.provider, migration.source.config);
      await this.initializeProvider(migration.destination.provider, migration.destination.config);

      // Scan source storage
      logger.info('Scanning source storage...');
      const sourceFiles = await this.scanStorage(migration.source);
      migration.stats.totalFiles = sourceFiles.length;
      migration.stats.totalBytes = sourceFiles.reduce((sum, file) => sum + file.size, 0);

      logger.info(`Found ${sourceFiles.length} files (${this.formatBytes(migration.stats.totalBytes)})`);

      // Create migration plan
      const migrationPlan = await this.createMigrationPlan(sourceFiles, migration);

      // Execute migration
      await this.executeMigration(migrationPlan, migration);

      migration.status = 'completed';
      migration.endTime = new Date();
      migration.stats.endTime = migration.endTime;

      this.migrationHistory.push(migration);
      this.activeMigrations.delete(migrationId);

      logger.info(`Storage migration ${migrationId} completed successfully`);
      this.emit('migrationCompleted', migration);

      return migration;

    } catch (error) {
      migration.status = 'failed';
      migration.endTime = new Date();
      migration.errors.push(error.message);

      logger.error(`Storage migration ${migrationId} failed:`, error);
      this.emit('migrationFailed', { migration, error });

      throw error;
    }
  }

  /**
   * Scan storage for files
   */
  async scanStorage(storageConfig) {
    const provider = this.providers.get(storageConfig.provider);
    if (!provider) {
      throw new Error(`Provider ${storageConfig.provider} not found`);
    }

    switch (storageConfig.provider) {
      case 'aws':
        return await this.scanS3Storage(provider.client, storageConfig);
      case 'gcp':
        return await this.scanGCPStorage(provider.client, storageConfig);
      case 'azure':
        return await this.scanAzureStorage(provider.client, storageConfig);
      case 'local':
        return await this.scanLocalStorage(provider.client, storageConfig);
      default:
        throw new Error(`Scanning not implemented for provider: ${storageConfig.provider}`);
    }
  }

  /**
   * Scan AWS S3 storage
   */
  async scanS3Storage(s3Client, config) {
    const files = [];
    let continuationToken = null;

    do {
      const params = {
        Bucket: config.bucket,
        Prefix: config.prefix || '',
        MaxKeys: 1000,
        ContinuationToken: continuationToken
      };

      const response = await s3Client.listObjectsV2(params).promise();
      
      for (const object of response.Contents || []) {
        files.push({
          key: object.Key,
          size: object.Size,
          lastModified: object.LastModified,
          etag: object.ETag,
          storageClass: object.StorageClass,
          metadata: {}
        });
      }

      continuationToken = response.NextContinuationToken;
    } while (continuationToken);

    return files;
  }

  /**
   * Scan Google Cloud Storage
   */
  async scanGCPStorage(gcpClient, config) {
    const files = [];
    const bucket = gcpClient.bucket(config.bucket);
    
    const [objects] = await bucket.getFiles({
      prefix: config.prefix || '',
      autoPaginate: true
    });

    for (const object of objects) {
      const [metadata] = await object.getMetadata();
      files.push({
        key: object.name,
        size: parseInt(metadata.size),
        lastModified: new Date(metadata.updated),
        etag: metadata.etag,
        storageClass: metadata.storageClass,
        metadata: metadata.metadata || {}
      });
    }

    return files;
  }

  /**
   * Scan Azure Blob Storage
   */
  async scanAzureStorage(blobClient, config) {
    const files = [];
    const containerClient = blobClient.getContainerClient(config.container);

    for await (const blob of containerClient.listBlobsFlat({
      prefix: config.prefix || ''
    })) {
      files.push({
        key: blob.name,
        size: blob.properties.contentLength,
        lastModified: blob.properties.lastModified,
        etag: blob.properties.etag,
        storageClass: blob.properties.accessTier,
        metadata: blob.metadata || {}
      });
    }

    return files;
  }

  /**
   * Scan local file system storage
   */
  async scanLocalStorage(localClient, config) {
    const files = [];
    const basePath = path.join(localClient.basePath, config.path || '');

    const scanDirectory = async (dirPath, relativePath = '') => {
      const items = await fs.readdir(dirPath, { withFileTypes: true });

      for (const item of items) {
        const fullPath = path.join(dirPath, item.name);
        const relativeFilePath = path.join(relativePath, item.name);

        if (item.isDirectory()) {
          await scanDirectory(fullPath, relativeFilePath);
        } else if (item.isFile()) {
          const stats = await fs.stat(fullPath);
          files.push({
            key: relativeFilePath,
            size: stats.size,
            lastModified: stats.mtime,
            etag: null,
            storageClass: null,
            metadata: {},
            localPath: fullPath
          });
        }
      }
    };

    await scanDirectory(basePath);
    return files;
  }

  /**
   * Create migration plan
   */
  async createMigrationPlan(sourceFiles, migration) {
    const plan = {
      batches: [],
      totalFiles: sourceFiles.length,
      totalBytes: sourceFiles.reduce((sum, file) => sum + file.size, 0),
      estimatedTime: null,
      deduplicationPossible: 0
    };

    // Group files into batches for concurrent processing
    const batchSize = Math.ceil(sourceFiles.length / this.options.concurrency);
    
    for (let i = 0; i < sourceFiles.length; i += batchSize) {
      const batch = sourceFiles.slice(i, i + batchSize);
      plan.batches.push(batch);
    }

    // Check for deduplication opportunities
    if (this.options.enableDeduplication) {
      await this.analyzeDuplication(sourceFiles, plan);
    }

    // Estimate migration time based on file sizes and bandwidth
    if (this.options.bandwidthLimit) {
      plan.estimatedTime = Math.ceil(plan.totalBytes / this.options.bandwidthLimit);
    }

    return plan;
  }

  /**
   * Analyze files for deduplication
   */
  async analyzeDuplication(files, plan) {
    const checksumMap = new Map();
    let deduplicatedBytes = 0;

    for (const file of files) {
      if (!file.checksum) {
        // Calculate checksum if not available
        file.checksum = await this.calculateChecksum(file);
      }

      if (checksumMap.has(file.checksum)) {
        plan.deduplicationPossible++;
        deduplicatedBytes += file.size;
        file.isDuplicate = true;
        file.originalFile = checksumMap.get(file.checksum);
      } else {
        checksumMap.set(file.checksum, file);
      }
    }

    plan.deduplicatedBytes = deduplicatedBytes;
    logger.info(`Deduplication analysis: ${plan.deduplicationPossible} duplicate files (${this.formatBytes(deduplicatedBytes)} saved)`);
  }

  /**
   * Execute migration plan
   */
  async executeMigration(plan, migration) {
    const promises = plan.batches.map((batch, index) => 
      this.processBatch(batch, migration, index)
    );

    await Promise.all(promises);
  }

  /**
   * Process a batch of files
   */
  async processBatch(batch, migration, batchIndex) {
    logger.info(`Processing batch ${batchIndex + 1}/${migration.plan?.batches?.length || 'unknown'}`);

    for (const file of batch) {
      try {
        // Skip duplicates if deduplication is enabled
        if (this.options.enableDeduplication && file.isDuplicate) {
          migration.stats.skippedFiles++;
          migration.stats.deduplicatedFiles++;
          continue;
        }

        // Check if file already exists at destination
        if (await this.fileExistsAtDestination(file, migration.destination)) {
          if (!migration.options.overwrite) {
            migration.stats.skippedFiles++;
            continue;
          }
        }

        await this.transferFile(file, migration);
        migration.stats.transferredFiles++;
        migration.stats.transferredBytes += file.size;

        // Emit progress event
        if (this.options.progressReporting) {
          this.emit('progress', {
            migrationId: migration.id,
            file: file.key,
            progress: migration.stats.transferredFiles / migration.stats.totalFiles,
            transferredBytes: migration.stats.transferredBytes,
            totalBytes: migration.stats.totalBytes
          });
        }

        // Rate limiting
        if (this.options.bandwidthLimit) {
          const delay = (file.size / this.options.bandwidthLimit) * 1000;
          await this.sleep(delay);
        }

      } catch (error) {
        migration.stats.failedFiles++;
        migration.errors.push({
          file: file.key,
          error: error.message
        });
        
        logger.error(`Failed to transfer file ${file.key}:`, error);
      }
    }
  }

  /**
   * Transfer individual file
   */
  async transferFile(file, migration) {
    const source = migration.source;
    const destination = migration.destination;

    // Download from source
    const tempFile = await this.downloadFile(file, source);
    
    try {
      // Apply transformations if needed
      let processedFile = tempFile;
      
      if (this.options.compression) {
        processedFile = await this.compressFile(tempFile);
      }
      
      if (this.options.encryption) {
        processedFile = await this.encryptFile(processedFile);
      }

      // Upload to destination
      await this.uploadFile(file, processedFile, destination);

      // Verify transfer if enabled
      if (this.options.checksumValidation) {
        await this.verifyTransfer(file, destination);
      }

    } finally {
      // Clean up temporary files
      await fs.remove(tempFile);
      if (tempFile !== processedFile) {
        await fs.remove(processedFile);
      }
    }
  }

  /**
   * Download file from source storage
   */
  async downloadFile(file, sourceConfig) {
    const provider = this.providers.get(sourceConfig.provider);
    const tempFile = path.join('/tmp', `migration_${Date.now()}_${path.basename(file.key)}`);

    switch (sourceConfig.provider) {
      case 'aws':
        const s3Stream = provider.client.getObject({
          Bucket: sourceConfig.bucket,
          Key: file.key
        }).createReadStream();
        
        await this.streamToFile(s3Stream, tempFile);
        break;

      case 'gcp':
        const bucket = provider.client.bucket(sourceConfig.bucket);
        const gcpFile = bucket.file(file.key);
        await gcpFile.download({ destination: tempFile });
        break;

      case 'azure':
        const containerClient = provider.client.getContainerClient(sourceConfig.container);
        const blobClient = containerClient.getBlobClient(file.key);
        await blobClient.downloadToFile(tempFile);
        break;

      case 'local':
        await fs.copy(file.localPath, tempFile);
        break;

      default:
        throw new Error(`Download not implemented for provider: ${sourceConfig.provider}`);
    }

    return tempFile;
  }

  /**
   * Upload file to destination storage
   */
  async uploadFile(originalFile, localFile, destinationConfig) {
    const provider = this.providers.get(destinationConfig.provider);
    
    switch (destinationConfig.provider) {
      case 'aws':
        const uploadParams = {
          Bucket: destinationConfig.bucket,
          Key: path.join(destinationConfig.prefix || '', originalFile.key),
          Body: createReadStream(localFile),
          Metadata: this.options.preserveMetadata ? originalFile.metadata : undefined
        };

        if (originalFile.size > provider.multipartThreshold) {
          await provider.client.upload(uploadParams).promise();
        } else {
          await provider.client.putObject(uploadParams).promise();
        }
        break;

      case 'gcp':
        const bucket = provider.client.bucket(destinationConfig.bucket);
        const fileName = path.join(destinationConfig.prefix || '', originalFile.key);
        
        await bucket.upload(localFile, {
          destination: fileName,
          metadata: {
            metadata: this.options.preserveMetadata ? originalFile.metadata : undefined
          }
        });
        break;

      case 'azure':
        const containerClient = provider.client.getContainerClient(destinationConfig.container);
        const blobName = path.join(destinationConfig.prefix || '', originalFile.key);
        const blockBlobClient = containerClient.getBlockBlobClient(blobName);
        
        await blockBlobClient.uploadFile(localFile, {
          metadata: this.options.preserveMetadata ? originalFile.metadata : undefined
        });
        break;

      case 'local':
        const destPath = path.join(
          provider.client.basePath,
          destinationConfig.path || '',
          originalFile.key
        );
        
        await fs.ensureDir(path.dirname(destPath));
        await fs.copy(localFile, destPath);
        break;

      default:
        throw new Error(`Upload not implemented for provider: ${destinationConfig.provider}`);
    }
  }

  /**
   * Check if file exists at destination
   */
  async fileExistsAtDestination(file, destinationConfig) {
    const provider = this.providers.get(destinationConfig.provider);
    
    try {
      switch (destinationConfig.provider) {
        case 'aws':
          await provider.client.headObject({
            Bucket: destinationConfig.bucket,
            Key: path.join(destinationConfig.prefix || '', file.key)
          }).promise();
          return true;

        case 'gcp':
          const bucket = provider.client.bucket(destinationConfig.bucket);
          const gcpFile = bucket.file(path.join(destinationConfig.prefix || '', file.key));
          const [exists] = await gcpFile.exists();
          return exists;

        case 'azure':
          const containerClient = provider.client.getContainerClient(destinationConfig.container);
          const blobClient = containerClient.getBlobClient(path.join(destinationConfig.prefix || '', file.key));
          return await blobClient.exists();

        case 'local':
          const destPath = path.join(
            provider.client.basePath,
            destinationConfig.path || '',
            file.key
          );
          return await fs.pathExists(destPath);

        default:
          return false;
      }
    } catch (error) {
      return false;
    }
  }

  /**
   * Verify file transfer integrity
   */
  async verifyTransfer(file, destinationConfig) {
    // Download a small portion of the file and compare checksums
    const tempFile = `/tmp/verify_${Date.now()}_${path.basename(file.key)}`;
    
    try {
      // This is a simplified verification - in production, you'd want more robust checking
      await this.downloadFile({ ...file, key: path.join(destinationConfig.prefix || '', file.key) }, destinationConfig);
      
      const destChecksum = await this.calculateChecksum({ localPath: tempFile });
      const sourceChecksum = file.checksum || await this.calculateChecksum(file);
      
      if (destChecksum !== sourceChecksum) {
        throw new Error(`Checksum mismatch for file ${file.key}`);
      }
      
      logger.debug(`Verified transfer integrity for ${file.key}`);
      
    } finally {
      await fs.remove(tempFile);
    }
  }

  /**
   * Calculate file checksum
   */
  async calculateChecksum(file) {
    const hash = crypto.createHash('sha256');
    const filePath = file.localPath || file.key;
    
    return new Promise((resolve, reject) => {
      const stream = createReadStream(filePath);
      
      stream.on('data', (data) => {
        hash.update(data);
      });
      
      stream.on('end', () => {
        resolve(hash.digest('hex'));
      });
      
      stream.on('error', reject);
    });
  }

  /**
   * Compress file
   */
  async compressFile(inputFile) {
    const outputFile = `${inputFile}.gz`;
    const archive = archiver('gzip', { level: 9 });
    const output = createWriteStream(outputFile);
    
    return new Promise((resolve, reject) => {
      output.on('close', () => {
        resolve(outputFile);
      });
      
      archive.on('error', reject);
      archive.pipe(output);
      archive.file(inputFile, { name: path.basename(inputFile) });
      archive.finalize();
    });
  }

  /**
   * Encrypt file
   */
  async encryptFile(inputFile, key = null) {
    const outputFile = `${inputFile}.enc`;
    const algorithm = 'aes-256-cbc';
    const encryptionKey = key || crypto.randomBytes(32);
    const iv = crypto.randomBytes(16);
    
    const cipher = crypto.createCipher(algorithm, encryptionKey);
    const input = createReadStream(inputFile);
    const output = createWriteStream(outputFile);
    
    return new Promise((resolve, reject) => {
      output.on('finish', () => {
        resolve(outputFile);
      });
      
      input.on('error', reject);
      output.on('error', reject);
      cipher.on('error', reject);
      
      input.pipe(cipher).pipe(output);
    });
  }

  /**
   * Create incremental backup/sync
   */
  async createIncrementalSync(syncConfig) {
    const syncId = this.generateMigrationId();
    logger.info(`Starting incremental sync ${syncId}`);

    const lastSyncTime = syncConfig.lastSyncTime || new Date(0);
    
    // Get modified files since last sync
    const sourceFiles = await this.scanStorage(syncConfig.source);
    const modifiedFiles = sourceFiles.filter(file => 
      file.lastModified > lastSyncTime
    );

    if (modifiedFiles.length === 0) {
      logger.info('No files modified since last sync');
      return { syncId, modifiedFiles: 0 };
    }

    // Migrate only modified files
    const migrationConfig = {
      source: syncConfig.source,
      destination: syncConfig.destination,
      options: {
        ...syncConfig.options,
        overwrite: true // Always overwrite in sync mode
      }
    };

    // Override file list to only include modified files
    const originalScanMethod = this.scanStorage;
    this.scanStorage = async () => modifiedFiles;
    
    try {
      const result = await this.migrateStorage(migrationConfig);
      
      // Update last sync time
      syncConfig.lastSyncTime = new Date();
      
      return {
        syncId,
        modifiedFiles: modifiedFiles.length,
        transferredBytes: result.stats.transferredBytes,
        duration: result.endTime - result.startTime
      };
      
    } finally {
      // Restore original scan method
      this.scanStorage = originalScanMethod;
    }
  }

  /**
   * Pause migration
   */
  pauseMigration(migrationId) {
    const migration = this.activeMigrations.get(migrationId);
    if (migration) {
      migration.status = 'paused';
      logger.info(`Migration ${migrationId} paused`);
      this.emit('migrationPaused', migration);
    }
  }

  /**
   * Resume migration
   */
  resumeMigration(migrationId) {
    const migration = this.activeMigrations.get(migrationId);
    if (migration && migration.status === 'paused') {
      migration.status = 'in_progress';
      logger.info(`Migration ${migrationId} resumed`);
      this.emit('migrationResumed', migration);
    }
  }

  /**
   * Cancel migration
   */
  cancelMigration(migrationId) {
    const migration = this.activeMigrations.get(migrationId);
    if (migration) {
      migration.status = 'cancelled';
      migration.endTime = new Date();
      
      this.activeMigrations.delete(migrationId);
      logger.info(`Migration ${migrationId} cancelled`);
      this.emit('migrationCancelled', migration);
    }
  }

  /**
   * Get migration status
   */
  getMigrationStatus(migrationId) {
    const migration = this.activeMigrations.get(migrationId);
    if (!migration) {
      // Check migration history
      return this.migrationHistory.find(m => m.id === migrationId) || null;
    }
    
    return {
      id: migration.id,
      status: migration.status,
      progress: migration.stats.transferredFiles / migration.stats.totalFiles,
      transferredFiles: migration.stats.transferredFiles,
      totalFiles: migration.stats.totalFiles,
      transferredBytes: migration.stats.transferredBytes,
      totalBytes: migration.stats.totalBytes,
      failedFiles: migration.stats.failedFiles,
      skippedFiles: migration.stats.skippedFiles,
      startTime: migration.startTime,
      estimatedTimeRemaining: this.calculateRemainingTime(migration),
      currentTransferRate: this.calculateTransferRate(migration)
    };
  }

  /**
   * Get all migration statuses
   */
  getAllMigrations() {
    const active = Array.from(this.activeMigrations.values());
    const completed = this.migrationHistory.slice(-10); // Last 10 completed
    
    return {
      active: active.map(m => this.getMigrationStatus(m.id)),
      completed: completed.map(m => ({
        id: m.id,
        status: m.status,
        startTime: m.startTime,
        endTime: m.endTime,
        transferredFiles: m.stats.transferredFiles,
        totalFiles: m.stats.totalFiles,
        transferredBytes: m.stats.transferredBytes,
        duration: m.endTime - m.startTime
      }))
    };
  }

  /**
   * Utility functions
   */
  generateMigrationId() {
    return `migration_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  formatBytes(bytes) {
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  }

  calculateRemainingTime(migration) {
    if (migration.stats.transferredFiles === 0) return null;
    
    const elapsed = Date.now() - migration.startTime.getTime();
    const rate = migration.stats.transferredFiles / elapsed;
    const remaining = migration.stats.totalFiles - migration.stats.transferredFiles;
    
    return remaining / rate;
  }

  calculateTransferRate(migration) {
    const elapsed = Date.now() - migration.startTime.getTime();
    return migration.stats.transferredBytes / (elapsed / 1000); // bytes per second
  }

  streamToFile(stream, filePath) {
    return new Promise((resolve, reject) => {
      const writeStream = createWriteStream(filePath);
      
      stream.pipe(writeStream);
      
      writeStream.on('finish', resolve);
      writeStream.on('error', reject);
      stream.on('error', reject);
    });
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}