const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const winston = require('winston');
const archiver = require('archiver');
const tar = require('tar');
const moment = require('moment');

class EnterpriseBackupSystem {
    constructor(options = {}) {
        this.config = {
            backupLocation: options.backupLocation || path.join(process.cwd(), 'enterprise-backups'),
            offlineBackupLocation: options.offlineBackupLocation || '/mnt/offline-storage',
            encryptionEnabled: options.encryptionEnabled !== false,
            compressionLevel: options.compressionLevel || 9,
            retentionPolicy: {
                daily: 30,    // Keep 30 daily backups
                weekly: 12,   // Keep 12 weekly backups  
                monthly: 12,  // Keep 12 monthly backups
                yearly: 5     // Keep 5 yearly backups
            },
            backupTypes: {
                'full': {
                    frequency: 'weekly',
                    includes: ['application', 'database', 'logs', 'configuration', 'audit_trails', 'keys'],
                    priority: 'high',
                    maxDuration: 7200000 // 2 hours
                },
                'incremental': {
                    frequency: 'daily',
                    includes: ['database', 'logs', 'audit_trails'],
                    priority: 'medium',
                    maxDuration: 1800000 // 30 minutes
                },
                'configuration': {
                    frequency: 'on-change',
                    includes: ['configuration', 'keys'],
                    priority: 'critical',
                    maxDuration: 300000 // 5 minutes
                },
                'disaster_recovery': {
                    frequency: 'monthly',
                    includes: ['application', 'database', 'logs', 'configuration', 'audit_trails', 'keys', 'system_state'],
                    priority: 'critical',
                    maxDuration: 14400000 // 4 hours
                }
            },
            encryptionConfig: {
                algorithm: 'aes-256-gcm',
                keyDerivation: 'pbkdf2',
                iterations: 600000,
                saltLength: 32,
                ivLength: 16
            },
            integrityChecks: {
                enabled: true,
                algorithm: 'sha512',
                verifyOnRestore: true,
                checksumStorage: 'separate'
            },
            replicationTargets: options.replicationTargets || [],
            airgapCompliant: options.airgapCompliant !== false,
            complianceRequirements: options.complianceRequirements || ['SOX', 'HIPAA', 'GDPR']
        };

        this.logger = winston.createLogger({
            level: 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json()
            ),
            defaultMeta: { service: 'enterprise-backup' },
            transports: [
                new winston.transports.File({
                    filename: 'logs/backup-error.log',
                    level: 'error'
                }),
                new winston.transports.File({
                    filename: 'logs/backup.log'
                })
            ]
        });

        this.backupJobs = new Map();
        this.activeBackups = new Set();
        this.backupMetrics = {
            totalBackups: 0,
            successfulBackups: 0,
            failedBackups: 0,
            totalDataBacked: 0,
            averageBackupTime: 0,
            lastBackupTime: null
        };

        this.encryptionKey = null;
        this.masterKey = null;

        this.initializeBackupSystem();
    }

    async initializeBackupSystem() {
        try {
            // Create backup directories
            await fs.mkdir(this.config.backupLocation, { recursive: true, mode: 0o700 });
            
            if (this.config.airgapCompliant) {
                try {
                    await fs.mkdir(this.config.offlineBackupLocation, { recursive: true, mode: 0o700 });
                } catch (error) {
                    this.logger.warn('Offline backup location not accessible', {
                        location: this.config.offlineBackupLocation,
                        error: error.message
                    });
                }
            }

            // Initialize encryption keys
            if (this.config.encryptionEnabled) {
                await this.initializeEncryption();
            }

            // Load existing backup metadata
            await this.loadBackupMetadata();

            // Start scheduled backup jobs
            this.startScheduledBackups();

            this.logger.info('Enterprise backup system initialized', {
                backupLocation: this.config.backupLocation,
                encryptionEnabled: this.config.encryptionEnabled,
                airgapCompliant: this.config.airgapCompliant,
                supportedTypes: Object.keys(this.config.backupTypes)
            });

        } catch (error) {
            this.logger.error('Failed to initialize backup system', { error: error.message });
            throw error;
        }
    }

    async initializeEncryption() {
        const keyPath = path.join(this.config.backupLocation, '.backup-keys');
        
        try {
            // Try to load existing keys
            const keyData = await fs.readFile(keyPath);
            const keys = JSON.parse(keyData.toString());
            this.masterKey = Buffer.from(keys.masterKey, 'hex');
            this.encryptionKey = Buffer.from(keys.encryptionKey, 'hex');
        } catch (error) {
            // Generate new keys
            this.masterKey = crypto.randomBytes(32);
            this.encryptionKey = crypto.randomBytes(32);

            const keyData = {
                masterKey: this.masterKey.toString('hex'),
                encryptionKey: this.encryptionKey.toString('hex'),
                createdAt: new Date().toISOString(),
                algorithm: this.config.encryptionConfig.algorithm
            };

            await fs.writeFile(keyPath, JSON.stringify(keyData, null, 2), { mode: 0o600 });
            this.logger.info('New backup encryption keys generated');
        }
    }

    async createBackup(backupType = 'incremental', options = {}) {
        const backupId = crypto.randomUUID();
        const timestamp = moment();
        const backupConfig = this.config.backupTypes[backupType];

        if (!backupConfig) {
            throw new Error(`Unknown backup type: ${backupType}`);
        }

        const backupJob = {
            id: backupId,
            type: backupType,
            startTime: timestamp.toDate(),
            status: 'running',
            progress: 0,
            includes: backupConfig.includes,
            priority: backupConfig.priority,
            metadata: {
                hostname: require('os').hostname(),
                nodeVersion: process.version,
                systemInfo: await this.getSystemInfo()
            },
            options: {
                encrypted: this.config.encryptionEnabled,
                compressed: true,
                verifyIntegrity: this.config.integrityChecks.enabled,
                ...options
            }
        };

        this.backupJobs.set(backupId, backupJob);
        this.activeBackups.add(backupId);

        this.logger.info('Starting backup', {
            backupId,
            type: backupType,
            includes: backupConfig.includes,
            priority: backupConfig.priority
        });

        try {
            // Create backup manifest
            const manifest = await this.createBackupManifest(backupJob);
            backupJob.manifest = manifest;

            // Create backup archive
            const backupPath = await this.createBackupArchive(backupJob);
            backupJob.path = backupPath;
            backupJob.progress = 70;

            // Generate integrity checksums
            if (this.config.integrityChecks.enabled) {
                backupJob.checksums = await this.generateIntegrityChecksums(backupPath);
                backupJob.progress = 85;
            }

            // Encrypt backup if enabled
            if (this.config.encryptionEnabled) {
                const encryptedPath = await this.encryptBackup(backupPath);
                await fs.unlink(backupPath); // Remove unencrypted version
                backupJob.path = encryptedPath;
                backupJob.encrypted = true;
                backupJob.progress = 95;
            }

            // Replicate to offline storage if air-gap compliant
            if (this.config.airgapCompliant) {
                await this.replicateToOfflineStorage(backupJob);
            }

            // Replicate to configured targets
            for (const target of this.config.replicationTargets) {
                await this.replicateToTarget(backupJob, target);
            }

            // Finalize backup
            backupJob.endTime = new Date();
            backupJob.duration = backupJob.endTime - backupJob.startTime;
            backupJob.status = 'completed';
            backupJob.progress = 100;

            // Update metrics
            this.updateBackupMetrics(backupJob, true);

            // Save backup metadata
            await this.saveBackupMetadata(backupJob);

            this.logger.info('Backup completed successfully', {
                backupId,
                type: backupType,
                duration: backupJob.duration,
                path: backupJob.path,
                encrypted: backupJob.encrypted
            });

            return backupJob;

        } catch (error) {
            backupJob.status = 'failed';
            backupJob.error = error.message;
            backupJob.endTime = new Date();

            this.updateBackupMetrics(backupJob, false);

            this.logger.error('Backup failed', {
                backupId,
                type: backupType,
                error: error.message
            });

            throw error;
        } finally {
            this.activeBackups.delete(backupId);
        }
    }

    async createBackupManifest(backupJob) {
        const manifest = {
            backupId: backupJob.id,
            type: backupJob.type,
            timestamp: backupJob.startTime,
            includes: backupJob.includes,
            version: '1.0',
            compliance: this.config.complianceRequirements,
            contents: {}
        };

        // Scan and catalog all items to be backed up
        for (const category of backupJob.includes) {
            manifest.contents[category] = await this.catalogBackupItems(category);
        }

        return manifest;
    }

    async catalogBackupItems(category) {
        const items = {
            category,
            files: [],
            size: 0,
            count: 0
        };

        switch (category) {
            case 'application':
                items.files = await this.catalogApplicationFiles();
                break;
            case 'database':
                items.files = await this.catalogDatabaseFiles();
                break;
            case 'logs':
                items.files = await this.catalogLogFiles();
                break;
            case 'configuration':
                items.files = await this.catalogConfigurationFiles();
                break;
            case 'audit_trails':
                items.files = await this.catalogAuditTrailFiles();
                break;
            case 'keys':
                items.files = await this.catalogKeyFiles();
                break;
            case 'system_state':
                items.files = await this.catalogSystemStateFiles();
                break;
        }

        // Calculate total size and count
        items.count = items.files.length;
        items.size = items.files.reduce((total, file) => total + (file.size || 0), 0);

        return items;
    }

    async createBackupArchive(backupJob) {
        const timestamp = moment(backupJob.startTime).format('YYYYMMDD-HHmmss');
        const fileName = `${backupJob.type}-backup-${timestamp}.tar.gz`;
        const archivePath = path.join(this.config.backupLocation, fileName);

        const archive = archiver('tar', {
            gzip: true,
            gzipOptions: { level: this.config.compressionLevel }
        });

        const output = require('fs').createWriteStream(archivePath);
        archive.pipe(output);

        // Add files based on manifest
        for (const [category, items] of Object.entries(backupJob.manifest.contents)) {
            for (const file of items.files) {
                try {
                    if (await this.fileExists(file.path)) {
                        archive.file(file.path, { name: path.join(category, path.basename(file.path)) });
                    }
                } catch (error) {
                    this.logger.warn('Could not add file to backup', {
                        file: file.path,
                        error: error.message
                    });
                }
            }
        }

        // Add manifest to archive
        const manifestPath = path.join(this.config.backupLocation, `manifest-${backupJob.id}.json`);
        await fs.writeFile(manifestPath, JSON.stringify(backupJob.manifest, null, 2));
        archive.file(manifestPath, { name: 'manifest.json' });

        await archive.finalize();

        // Clean up temporary manifest file
        await fs.unlink(manifestPath);

        return new Promise((resolve, reject) => {
            output.on('close', () => resolve(archivePath));
            output.on('error', reject);
            archive.on('error', reject);
        });
    }

    async encryptBackup(backupPath) {
        const encryptedPath = backupPath + '.enc';
        const salt = crypto.randomBytes(this.config.encryptionConfig.saltLength);
        const iv = crypto.randomBytes(this.config.encryptionConfig.ivLength);

        // Derive key from master key and salt
        const key = crypto.pbkdf2Sync(
            this.masterKey,
            salt,
            this.config.encryptionConfig.iterations,
            32,
            'sha512'
        );

        const cipher = crypto.createCipher(this.config.encryptionConfig.algorithm, key, { iv });
        
        const input = require('fs').createReadStream(backupPath);
        const output = require('fs').createWriteStream(encryptedPath);

        // Write encryption header
        const header = Buffer.concat([
            Buffer.from('EBKP', 'ascii'), // Magic bytes
            Buffer.from([1, 0]), // Version
            salt,
            iv
        ]);
        
        output.write(header);

        return new Promise((resolve, reject) => {
            input.pipe(cipher).pipe(output);
            output.on('finish', () => {
                // Write auth tag at the end
                const authTag = cipher.getAuthTag();
                require('fs').appendFileSync(encryptedPath, authTag);
                resolve(encryptedPath);
            });
            output.on('error', reject);
            input.on('error', reject);
            cipher.on('error', reject);
        });
    }

    async generateIntegrityChecksums(backupPath) {
        const checksums = {};
        
        // Generate file checksum
        const fileHash = crypto.createHash(this.config.integrityChecks.algorithm);
        const fileStream = require('fs').createReadStream(backupPath);

        return new Promise((resolve, reject) => {
            fileStream.on('data', data => fileHash.update(data));
            fileStream.on('end', () => {
                checksums.sha512 = fileHash.digest('hex');
                checksums.algorithm = this.config.integrityChecks.algorithm;
                checksums.timestamp = new Date().toISOString();
                resolve(checksums);
            });
            fileStream.on('error', reject);
        });
    }

    async replicateToOfflineStorage(backupJob) {
        try {
            const sourceFile = backupJob.path;
            const fileName = path.basename(sourceFile);
            const targetPath = path.join(this.config.offlineBackupLocation, fileName);

            await fs.copyFile(sourceFile, targetPath);

            // Copy checksums if they exist
            if (backupJob.checksums) {
                const checksumPath = targetPath + '.checksum';
                await fs.writeFile(checksumPath, JSON.stringify(backupJob.checksums, null, 2));
            }

            this.logger.info('Backup replicated to offline storage', {
                backupId: backupJob.id,
                source: sourceFile,
                target: targetPath
            });

        } catch (error) {
            this.logger.error('Failed to replicate to offline storage', {
                backupId: backupJob.id,
                error: error.message
            });
            throw error;
        }
    }

    async replicateToTarget(backupJob, target) {
        // Target replication would be implemented based on target type
        // (S3, NFS, SFTP, etc.) - placeholder implementation
        this.logger.info('Backup replication to target would be implemented', {
            backupId: backupJob.id,
            target
        });
    }

    async restoreBackup(backupId, restoreOptions = {}) {
        const backupMetadata = await this.loadBackupById(backupId);
        if (!backupMetadata) {
            throw new Error(`Backup not found: ${backupId}`);
        }

        const restoreJob = {
            id: crypto.randomUUID(),
            backupId,
            startTime: new Date(),
            status: 'running',
            progress: 0,
            options: {
                verifyIntegrity: true,
                restoreLocation: restoreOptions.restoreLocation || process.cwd(),
                includeCategories: restoreOptions.includeCategories || backupMetadata.includes,
                ...restoreOptions
            }
        };

        this.logger.info('Starting backup restore', {
            restoreId: restoreJob.id,
            backupId,
            backupType: backupMetadata.type,
            restoreLocation: restoreJob.options.restoreLocation
        });

        try {
            let backupPath = backupMetadata.path;
            
            // Decrypt backup if encrypted
            if (backupMetadata.encrypted) {
                backupPath = await this.decryptBackup(backupPath);
                restoreJob.progress = 20;
            }

            // Verify integrity if enabled
            if (restoreJob.options.verifyIntegrity && backupMetadata.checksums) {
                const verificationResult = await this.verifyBackupIntegrity(backupPath, backupMetadata.checksums);
                if (!verificationResult.valid) {
                    throw new Error(`Backup integrity verification failed: ${verificationResult.error}`);
                }
                restoreJob.progress = 40;
            }

            // Extract backup
            await this.extractBackup(backupPath, restoreJob);
            restoreJob.progress = 90;

            // Clean up decrypted file if it was temporary
            if (backupMetadata.encrypted && backupPath !== backupMetadata.path) {
                await fs.unlink(backupPath);
            }

            restoreJob.status = 'completed';
            restoreJob.endTime = new Date();
            restoreJob.duration = restoreJob.endTime - restoreJob.startTime;
            restoreJob.progress = 100;

            this.logger.info('Backup restore completed', {
                restoreId: restoreJob.id,
                backupId,
                duration: restoreJob.duration,
                restoreLocation: restoreJob.options.restoreLocation
            });

            return restoreJob;

        } catch (error) {
            restoreJob.status = 'failed';
            restoreJob.error = error.message;
            restoreJob.endTime = new Date();

            this.logger.error('Backup restore failed', {
                restoreId: restoreJob.id,
                backupId,
                error: error.message
            });

            throw error;
        }
    }

    async decryptBackup(encryptedPath) {
        const decryptedPath = encryptedPath.replace('.enc', '.decrypted');
        const input = require('fs').createReadStream(encryptedPath);
        const output = require('fs').createWriteStream(decryptedPath);

        // Read encryption header
        const headerBuffer = Buffer.alloc(42); // Magic(4) + Version(2) + Salt(32) + IV(16)
        const headerStream = require('fs').createReadStream(encryptedPath, { start: 0, end: 41 });

        return new Promise((resolve, reject) => {
            headerStream.on('data', data => {
                const magic = data.subarray(0, 4).toString('ascii');
                if (magic !== 'EBKP') {
                    reject(new Error('Invalid encrypted backup file'));
                    return;
                }

                const salt = data.subarray(6, 38);
                const iv = data.subarray(38, 54);

                // Derive key
                const key = crypto.pbkdf2Sync(
                    this.masterKey,
                    salt,
                    this.config.encryptionConfig.iterations,
                    32,
                    'sha512'
                );

                const decipher = crypto.createDecipher(this.config.encryptionConfig.algorithm, key, { iv });
                
                // Create stream for encrypted data (skip header)
                const encryptedStream = require('fs').createReadStream(encryptedPath, { start: 54 });
                
                encryptedStream.pipe(decipher).pipe(output);
                
                output.on('finish', () => resolve(decryptedPath));
                output.on('error', reject);
                encryptedStream.on('error', reject);
                decipher.on('error', reject);
            });
            
            headerStream.on('error', reject);
        });
    }

    async verifyBackupIntegrity(backupPath, expectedChecksums) {
        const actualHash = crypto.createHash(expectedChecksums.algorithm);
        const stream = require('fs').createReadStream(backupPath);

        return new Promise((resolve, reject) => {
            stream.on('data', data => actualHash.update(data));
            stream.on('end', () => {
                const actualChecksum = actualHash.digest('hex');
                const valid = actualChecksum === expectedChecksums.sha512;
                
                resolve({
                    valid,
                    expected: expectedChecksums.sha512,
                    actual: actualChecksum,
                    error: valid ? null : 'Checksum mismatch'
                });
            });
            stream.on('error', reject);
        });
    }

    async extractBackup(backupPath, restoreJob) {
        const extractPath = restoreJob.options.restoreLocation;
        
        // Extract using tar
        await tar.x({
            file: backupPath,
            cwd: extractPath,
            filter: (path, entry) => {
                // Filter based on included categories
                const category = path.split('/')[0];
                return restoreJob.options.includeCategories.includes(category);
            }
        });

        this.logger.info('Backup extracted successfully', {
            backupPath,
            extractPath,
            categories: restoreJob.options.includeCategories
        });
    }

    async listBackups(options = {}) {
        const { type, startDate, endDate, limit = 50, offset = 0 } = options;
        const metadataPath = path.join(this.config.backupLocation, '.metadata');
        
        try {
            const metadataContent = await fs.readFile(metadataPath, 'utf8');
            const allBackups = JSON.parse(metadataContent).backups || [];
            
            let filteredBackups = allBackups;

            // Apply filters
            if (type) {
                filteredBackups = filteredBackups.filter(backup => backup.type === type);
            }
            
            if (startDate) {
                filteredBackups = filteredBackups.filter(backup => 
                    new Date(backup.startTime) >= new Date(startDate)
                );
            }
            
            if (endDate) {
                filteredBackups = filteredBackups.filter(backup => 
                    new Date(backup.startTime) <= new Date(endDate)
                );
            }

            // Sort by date (newest first) and apply pagination
            const sortedBackups = filteredBackups
                .sort((a, b) => new Date(b.startTime) - new Date(a.startTime))
                .slice(offset, offset + limit);

            return {
                backups: sortedBackups,
                total: filteredBackups.length,
                limit,
                offset
            };

        } catch (error) {
            this.logger.error('Failed to list backups', { error: error.message });
            return { backups: [], total: 0, limit, offset };
        }
    }

    async deleteBackup(backupId) {
        const backup = await this.loadBackupById(backupId);
        if (!backup) {
            throw new Error(`Backup not found: ${backupId}`);
        }

        try {
            // Delete backup file
            if (await this.fileExists(backup.path)) {
                await fs.unlink(backup.path);
            }

            // Delete checksum file if it exists
            const checksumPath = backup.path + '.checksum';
            if (await this.fileExists(checksumPath)) {
                await fs.unlink(checksumPath);
            }

            // Delete from offline storage if it exists
            if (this.config.airgapCompliant) {
                const offlineFileName = path.basename(backup.path);
                const offlinePath = path.join(this.config.offlineBackupLocation, offlineFileName);
                
                try {
                    await fs.unlink(offlinePath);
                    await fs.unlink(offlinePath + '.checksum');
                } catch (error) {
                    // Offline file might not exist, continue
                }
            }

            // Remove from metadata
            await this.removeBackupFromMetadata(backupId);

            this.logger.info('Backup deleted successfully', {
                backupId,
                path: backup.path
            });

        } catch (error) {
            this.logger.error('Failed to delete backup', {
                backupId,
                error: error.message
            });
            throw error;
        }
    }

    async performRetentionCleanup() {
        const policy = this.config.retentionPolicy;
        const now = moment();
        let deletedCount = 0;

        try {
            const allBackups = await this.listBackups({ limit: 10000 });
            const backupsToDelete = [];

            // Group backups by type for retention analysis
            const backupsByType = {};
            for (const backup of allBackups.backups) {
                if (!backupsByType[backup.type]) {
                    backupsByType[backup.type] = [];
                }
                backupsByType[backup.type].push(backup);
            }

            // Apply retention policy for each backup type
            for (const [type, backups] of Object.entries(backupsByType)) {
                const sorted = backups.sort((a, b) => new Date(b.startTime) - new Date(a.startTime));

                // Keep based on retention policy
                const cutoffs = {
                    daily: now.clone().subtract(policy.daily, 'days'),
                    weekly: now.clone().subtract(policy.weekly, 'weeks'),
                    monthly: now.clone().subtract(policy.monthly, 'months'),
                    yearly: now.clone().subtract(policy.yearly, 'years')
                };

                for (let i = 0; i < sorted.length; i++) {
                    const backup = sorted[i];
                    const backupDate = moment(backup.startTime);
                    let shouldKeep = false;

                    // Keep if within daily retention
                    if (backupDate.isAfter(cutoffs.daily)) {
                        shouldKeep = true;
                    }
                    // Keep weekly if it's the first of the week within weekly retention
                    else if (backupDate.isAfter(cutoffs.weekly) && backupDate.isoWeekday() === 1) {
                        shouldKeep = true;
                    }
                    // Keep monthly if it's the first of the month within monthly retention
                    else if (backupDate.isAfter(cutoffs.monthly) && backupDate.date() === 1) {
                        shouldKeep = true;
                    }
                    // Keep yearly if it's January 1st within yearly retention
                    else if (backupDate.isAfter(cutoffs.yearly) && 
                             backupDate.month() === 0 && backupDate.date() === 1) {
                        shouldKeep = true;
                    }

                    if (!shouldKeep) {
                        backupsToDelete.push(backup);
                    }
                }
            }

            // Delete expired backups
            for (const backup of backupsToDelete) {
                try {
                    await this.deleteBackup(backup.id);
                    deletedCount++;
                } catch (error) {
                    this.logger.error('Failed to delete expired backup', {
                        backupId: backup.id,
                        error: error.message
                    });
                }
            }

            this.logger.info('Retention cleanup completed', {
                deletedCount,
                totalBackups: allBackups.total,
                retentionPolicy: policy
            });

            return { deletedCount, totalBackups: allBackups.total };

        } catch (error) {
            this.logger.error('Retention cleanup failed', { error: error.message });
            throw error;
        }
    }

    startScheduledBackups() {
        // Schedule incremental backups daily at 2 AM
        const incrementalSchedule = '0 2 * * *'; // Daily at 2 AM
        this.scheduleBackup('incremental', incrementalSchedule);

        // Schedule full backups weekly on Sunday at 1 AM
        const fullSchedule = '0 1 * * 0'; // Weekly on Sunday at 1 AM
        this.scheduleBackup('full', fullSchedule);

        // Schedule disaster recovery backups monthly on the 1st at midnight
        const drSchedule = '0 0 1 * *'; // Monthly on the 1st at midnight
        this.scheduleBackup('disaster_recovery', drSchedule);

        // Schedule retention cleanup daily at 4 AM
        const cleanupSchedule = '0 4 * * *'; // Daily at 4 AM
        this.scheduleRetentionCleanup(cleanupSchedule);

        this.logger.info('Backup schedules initialized');
    }

    scheduleBackup(backupType, cronSchedule) {
        // In a production environment, you would use a proper cron scheduler
        // For now, we'll simulate with setInterval for demonstration
        const interval = this.parseCronToInterval(cronSchedule);
        
        setInterval(async () => {
            try {
                await this.createBackup(backupType);
            } catch (error) {
                this.logger.error('Scheduled backup failed', {
                    backupType,
                    error: error.message
                });
            }
        }, interval);
    }

    scheduleRetentionCleanup(cronSchedule) {
        const interval = this.parseCronToInterval(cronSchedule);
        
        setInterval(async () => {
            try {
                await this.performRetentionCleanup();
            } catch (error) {
                this.logger.error('Scheduled retention cleanup failed', {
                    error: error.message
                });
            }
        }, interval);
    }

    parseCronToInterval(cronSchedule) {
        // Simplified cron parsing - in production use a proper cron library
        return 24 * 60 * 60 * 1000; // Default to daily
    }

    async getSystemInfo() {
        const os = require('os');
        return {
            platform: os.platform(),
            arch: os.arch(),
            release: os.release(),
            totalMemory: os.totalmem(),
            freeMemory: os.freemem(),
            loadAverage: os.loadavg(),
            uptime: os.uptime()
        };
    }

    // Catalog methods for different backup categories
    async catalogApplicationFiles() {
        // Catalog application source files
        return [
            { path: path.join(process.cwd(), 'src'), type: 'directory', size: await this.getDirectorySize('src') },
            { path: path.join(process.cwd(), 'package.json'), type: 'file', size: await this.getFileSize('package.json') }
        ];
    }

    async catalogDatabaseFiles() {
        // Catalog database files - implementation would depend on database type
        return [
            { path: '/var/lib/database', type: 'directory', size: 1000000, note: 'Database data directory' }
        ];
    }

    async catalogLogFiles() {
        return [
            { path: path.join(process.cwd(), 'logs'), type: 'directory', size: await this.getDirectorySize('logs') }
        ];
    }

    async catalogConfigurationFiles() {
        return [
            { path: path.join(process.cwd(), '.env'), type: 'file', size: await this.getFileSize('.env') },
            { path: path.join(process.cwd(), 'config'), type: 'directory', size: await this.getDirectorySize('config') }
        ];
    }

    async catalogAuditTrailFiles() {
        return [
            { path: path.join(process.cwd(), 'audit-trails'), type: 'directory', size: await this.getDirectorySize('audit-trails') }
        ];
    }

    async catalogKeyFiles() {
        return [
            { path: path.join(process.cwd(), 'keys'), type: 'directory', size: await this.getDirectorySize('keys') }
        ];
    }

    async catalogSystemStateFiles() {
        // System state would include process info, environment variables, etc.
        return [
            { path: '/proc/version', type: 'file', size: 100, note: 'System version info' }
        ];
    }

    async fileExists(filePath) {
        try {
            await fs.access(filePath);
            return true;
        } catch {
            return false;
        }
    }

    async getFileSize(filePath) {
        try {
            const stats = await fs.stat(filePath);
            return stats.size;
        } catch {
            return 0;
        }
    }

    async getDirectorySize(dirPath) {
        try {
            const stats = await fs.stat(dirPath);
            if (!stats.isDirectory()) return stats.size;
            
            // Simplified directory size calculation
            return 1000000; // Return estimated size
        } catch {
            return 0;
        }
    }

    updateBackupMetrics(backupJob, success) {
        this.backupMetrics.totalBackups++;
        
        if (success) {
            this.backupMetrics.successfulBackups++;
            this.backupMetrics.lastBackupTime = backupJob.endTime;
            
            // Update average backup time
            const totalTime = this.backupMetrics.averageBackupTime * (this.backupMetrics.successfulBackups - 1) + backupJob.duration;
            this.backupMetrics.averageBackupTime = totalTime / this.backupMetrics.successfulBackups;
        } else {
            this.backupMetrics.failedBackups++;
        }
    }

    async saveBackupMetadata(backupJob) {
        const metadataPath = path.join(this.config.backupLocation, '.metadata');
        
        try {
            let metadata = { backups: [] };
            
            try {
                const existing = await fs.readFile(metadataPath, 'utf8');
                metadata = JSON.parse(existing);
            } catch {
                // New metadata file
            }

            metadata.backups.push(backupJob);
            await fs.writeFile(metadataPath, JSON.stringify(metadata, null, 2), { mode: 0o600 });
            
        } catch (error) {
            this.logger.error('Failed to save backup metadata', {
                backupId: backupJob.id,
                error: error.message
            });
        }
    }

    async loadBackupMetadata() {
        const metadataPath = path.join(this.config.backupLocation, '.metadata');
        
        try {
            const data = await fs.readFile(metadataPath, 'utf8');
            const metadata = JSON.parse(data);
            
            // Update metrics from metadata
            this.backupMetrics.totalBackups = metadata.backups.length;
            this.backupMetrics.successfulBackups = metadata.backups.filter(b => b.status === 'completed').length;
            this.backupMetrics.failedBackups = metadata.backups.filter(b => b.status === 'failed').length;
            
        } catch (error) {
            // No existing metadata
        }
    }

    async loadBackupById(backupId) {
        const backupsList = await this.listBackups({ limit: 10000 });
        return backupsList.backups.find(backup => backup.id === backupId);
    }

    async removeBackupFromMetadata(backupId) {
        const metadataPath = path.join(this.config.backupLocation, '.metadata');
        
        try {
            const data = await fs.readFile(metadataPath, 'utf8');
            const metadata = JSON.parse(data);
            
            metadata.backups = metadata.backups.filter(backup => backup.id !== backupId);
            await fs.writeFile(metadataPath, JSON.stringify(metadata, null, 2), { mode: 0o600 });
            
        } catch (error) {
            this.logger.error('Failed to remove backup from metadata', {
                backupId,
                error: error.message
            });
        }
    }

    getBackupStatus() {
        return {
            activeBackups: Array.from(this.activeBackups),
            metrics: this.backupMetrics,
            config: {
                location: this.config.backupLocation,
                encryptionEnabled: this.config.encryptionEnabled,
                airgapCompliant: this.config.airgapCompliant,
                retentionPolicy: this.config.retentionPolicy
            }
        };
    }
}

module.exports = EnterpriseBackupSystem;