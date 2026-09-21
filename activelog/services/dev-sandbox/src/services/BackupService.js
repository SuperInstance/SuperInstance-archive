const fs = require('fs').promises;
const path = require('path');
const { createHash } = require('crypto');
const { exec } = require('child_process');
const { promisify } = require('util');
const EventEmitter = require('events');
const tar = require('tar');

const execAsync = promisify(exec);

class BackupService extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            backupDir: config.backupDir || '/tmp/dev-sandbox-backups',
            maxBackups: config.maxBackups || 50,
            compressionEnabled: config.compressionEnabled !== false,
            incrementalBackups: config.incrementalBackups !== false,
            retentionDays: config.retentionDays || 30,
            backupTypes: {
                full: 'full',
                incremental: 'incremental',
                differential: 'differential'
            },
            excludePatterns: config.excludePatterns || [
                'node_modules',
                '.git',
                'tmp',
                '*.log',
                '.DS_Store',
                '__pycache__'
            ],
            ...config
        };

        this.backupHistory = new Map(); // userId -> backup history
        this.backupMetadata = new Map(); // backupId -> metadata
        this.activeBackups = new Set(); // Track ongoing backup operations

        this.initializeBackupService();
    }

    async initializeBackupService() {
        await this.ensureBackupDirectory();
        await this.loadBackupHistory();
        this.startCleanupScheduler();
        
        this.emit('backup-service-initialized', {
            timestamp: new Date(),
            backupDir: this.config.backupDir
        });
    }

    async ensureBackupDirectory() {
        try {
            await fs.access(this.config.backupDir);
        } catch {
            await fs.mkdir(this.config.backupDir, { recursive: true });
        }
    }

    async createBackupBeforeChange(userId, projectPath, changeDescription, options = {}) {
        if (this.activeBackups.has(`${userId}-${projectPath}`)) {
            throw new Error('Backup already in progress for this project');
        }

        const backupId = this.generateBackupId(userId, projectPath);
        this.activeBackups.add(`${userId}-${projectPath}`);

        try {
            const backupType = await this.determineBackupType(userId, projectPath, options);
            const backupPath = await this.performBackup(userId, projectPath, backupId, backupType);
            
            const metadata = await this.createBackupMetadata(
                backupId, 
                userId, 
                projectPath, 
                changeDescription, 
                backupType, 
                backupPath
            );

            await this.storeBackupMetadata(metadata);
            this.recordBackupInHistory(userId, metadata);

            this.emit('backup-created', {
                backupId,
                userId,
                projectPath,
                backupType,
                changeDescription
            });

            return {
                backupId,
                backupPath,
                backupType,
                timestamp: metadata.timestamp
            };
        } finally {
            this.activeBackups.delete(`${userId}-${projectPath}`);
        }
    }

    async determineBackupType(userId, projectPath, options) {
        if (options.forceFullBackup) {
            return this.config.backupTypes.full;
        }

        const userHistory = this.backupHistory.get(userId) || [];
        const projectBackups = userHistory.filter(b => b.projectPath === projectPath);

        if (projectBackups.length === 0) {
            return this.config.backupTypes.full;
        }

        if (!this.config.incrementalBackups) {
            return this.config.backupTypes.full;
        }

        const lastFullBackup = projectBackups
            .filter(b => b.backupType === this.config.backupTypes.full)
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0];

        const timeSinceLastFull = lastFullBackup ? 
            Date.now() - new Date(lastFullBackup.timestamp).getTime() : 
            Infinity;

        // Create full backup if last full backup is older than 7 days
        if (timeSinceLastFull > 7 * 24 * 60 * 60 * 1000) {
            return this.config.backupTypes.full;
        }

        return this.config.backupTypes.incremental;
    }

    async performBackup(userId, projectPath, backupId, backupType) {
        const backupFileName = `${backupId}.tar${this.config.compressionEnabled ? '.gz' : ''}`;
        const backupPath = path.join(this.config.backupDir, userId, backupFileName);
        const backupDir = path.dirname(backupPath);

        await fs.mkdir(backupDir, { recursive: true });

        if (backupType === this.config.backupTypes.full) {
            await this.createFullBackup(projectPath, backupPath);
        } else {
            await this.createIncrementalBackup(userId, projectPath, backupPath);
        }

        return backupPath;
    }

    async createFullBackup(projectPath, backupPath) {
        const excludeArgs = this.config.excludePatterns
            .map(pattern => `--exclude=${pattern}`)
            .join(' ');

        const compressionFlag = this.config.compressionEnabled ? 'z' : '';
        
        await tar.create({
            file: backupPath,
            gzip: this.config.compressionEnabled,
            cwd: path.dirname(projectPath),
            filter: (filePath) => {
                return !this.shouldExclude(filePath);
            }
        }, [path.basename(projectPath)]);

        this.emit('full-backup-created', { projectPath, backupPath });
    }

    async createIncrementalBackup(userId, projectPath, backupPath) {
        const lastBackup = await this.getLastBackup(userId, projectPath);
        if (!lastBackup) {
            return this.createFullBackup(projectPath, backupPath);
        }

        const changedFiles = await this.findChangedFiles(projectPath, lastBackup.timestamp);
        
        if (changedFiles.length === 0) {
            throw new Error('No changes detected since last backup');
        }

        await tar.create({
            file: backupPath,
            gzip: this.config.compressionEnabled,
            cwd: projectPath,
            filter: (filePath) => {
                const relativePath = path.relative(projectPath, filePath);
                return changedFiles.includes(relativePath) && !this.shouldExclude(filePath);
            }
        }, changedFiles);

        this.emit('incremental-backup-created', { 
            projectPath, 
            backupPath, 
            changedFiles: changedFiles.length 
        });
    }

    async findChangedFiles(projectPath, sinceTimestamp) {
        const changedFiles = [];
        
        async function scanDirectory(dirPath) {
            const entries = await fs.readdir(dirPath, { withFileTypes: true });
            
            for (const entry of entries) {
                const fullPath = path.join(dirPath, entry.name);
                const relativePath = path.relative(projectPath, fullPath);
                
                if (this.shouldExclude(relativePath)) {
                    continue;
                }
                
                if (entry.isDirectory()) {
                    await scanDirectory(fullPath);
                } else {
                    const stats = await fs.stat(fullPath);
                    if (stats.mtime > sinceTimestamp) {
                        changedFiles.push(relativePath);
                    }
                }
            }
        }

        await scanDirectory.call(this, projectPath);
        return changedFiles;
    }

    shouldExclude(filePath) {
        return this.config.excludePatterns.some(pattern => {
            if (pattern.includes('*')) {
                const regex = new RegExp(pattern.replace(/\*/g, '.*'));
                return regex.test(filePath);
            }
            return filePath.includes(pattern);
        });
    }

    async createBackupMetadata(backupId, userId, projectPath, changeDescription, backupType, backupPath) {
        const stats = await fs.stat(backupPath);
        const checksum = await this.calculateFileChecksum(backupPath);

        return {
            id: backupId,
            userId,
            projectPath,
            changeDescription,
            backupType,
            backupPath,
            timestamp: new Date(),
            size: stats.size,
            checksum,
            compressed: this.config.compressionEnabled,
            verified: false
        };
    }

    async calculateFileChecksum(filePath) {
        const fileBuffer = await fs.readFile(filePath);
        return createHash('sha256').update(fileBuffer).digest('hex');
    }

    async storeBackupMetadata(metadata) {
        this.backupMetadata.set(metadata.id, metadata);
        
        const metadataFile = path.join(
            this.config.backupDir, 
            metadata.userId, 
            `${metadata.id}.metadata.json`
        );
        
        await fs.writeFile(metadataFile, JSON.stringify(metadata, null, 2));
    }

    recordBackupInHistory(userId, metadata) {
        if (!this.backupHistory.has(userId)) {
            this.backupHistory.set(userId, []);
        }

        const userHistory = this.backupHistory.get(userId);
        userHistory.push({
            id: metadata.id,
            projectPath: metadata.projectPath,
            backupType: metadata.backupType,
            timestamp: metadata.timestamp,
            size: metadata.size
        });

        // Keep only recent backups in memory
        if (userHistory.length > this.config.maxBackups) {
            userHistory.splice(0, userHistory.length - this.config.maxBackups);
        }
    }

    async restoreFromBackup(userId, backupId, restorePath, options = {}) {
        const metadata = this.backupMetadata.get(backupId);
        if (!metadata || metadata.userId !== userId) {
            throw new Error('Backup not found or access denied');
        }

        if (!await this.verifyBackupIntegrity(backupId)) {
            throw new Error('Backup integrity verification failed');
        }

        const actualRestorePath = restorePath || metadata.projectPath;
        
        if (options.createBackupBeforeRestore) {
            await this.createBackupBeforeChange(
                userId, 
                actualRestorePath, 
                `Backup before restore from ${backupId}`,
                { forceFullBackup: true }
            );
        }

        if (metadata.backupType === this.config.backupTypes.full) {
            await this.restoreFullBackup(metadata.backupPath, actualRestorePath);
        } else {
            await this.restoreIncrementalBackup(userId, metadata, actualRestorePath);
        }

        this.emit('backup-restored', {
            userId,
            backupId,
            restorePath: actualRestorePath,
            backupType: metadata.backupType
        });

        return {
            backupId,
            restorePath: actualRestorePath,
            restoredAt: new Date()
        };
    }

    async restoreFullBackup(backupPath, restorePath) {
        const restoreDir = path.dirname(restorePath);
        await fs.mkdir(restoreDir, { recursive: true });

        await tar.extract({
            file: backupPath,
            cwd: restoreDir
        });

        this.emit('full-backup-restored', { backupPath, restorePath });
    }

    async restoreIncrementalBackup(userId, metadata, restorePath) {
        // For incremental restore, we need to find the base full backup
        const baseBackup = await this.findBaseFullBackup(userId, metadata);
        if (!baseBackup) {
            throw new Error('Cannot restore incremental backup without base full backup');
        }

        // First restore the full backup
        await this.restoreFullBackup(baseBackup.backupPath, restorePath);

        // Then apply all incremental changes up to the requested backup
        const incrementalBackups = await this.getIncrementalChain(userId, metadata);
        
        for (const incBackup of incrementalBackups) {
            await tar.extract({
                file: incBackup.backupPath,
                cwd: restorePath
            });
        }

        this.emit('incremental-backup-restored', { 
            restorePath, 
            baseBackup: baseBackup.id, 
            incrementalCount: incrementalBackups.length 
        });
    }

    async findBaseFullBackup(userId, incrementalMetadata) {
        const userHistory = this.backupHistory.get(userId) || [];
        const projectBackups = userHistory
            .filter(b => b.projectPath === incrementalMetadata.projectPath)
            .filter(b => b.backupType === this.config.backupTypes.full)
            .filter(b => new Date(b.timestamp) < new Date(incrementalMetadata.timestamp))
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        if (projectBackups.length === 0) {
            return null;
        }

        return this.backupMetadata.get(projectBackups[0].id);
    }

    async getIncrementalChain(userId, targetMetadata) {
        const baseBackup = await this.findBaseFullBackup(userId, targetMetadata);
        if (!baseBackup) {
            return [];
        }

        const userHistory = this.backupHistory.get(userId) || [];
        const incrementalBackups = userHistory
            .filter(b => b.projectPath === targetMetadata.projectPath)
            .filter(b => b.backupType === this.config.backupTypes.incremental)
            .filter(b => new Date(b.timestamp) > new Date(baseBackup.timestamp))
            .filter(b => new Date(b.timestamp) <= new Date(targetMetadata.timestamp))
            .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        return incrementalBackups.map(b => this.backupMetadata.get(b.id));
    }

    async verifyBackupIntegrity(backupId) {
        const metadata = this.backupMetadata.get(backupId);
        if (!metadata) {
            return false;
        }

        try {
            // Check if file exists
            await fs.access(metadata.backupPath);

            // Verify checksum
            const currentChecksum = await this.calculateFileChecksum(metadata.backupPath);
            const checksumValid = currentChecksum === metadata.checksum;

            // Verify file size
            const stats = await fs.stat(metadata.backupPath);
            const sizeValid = stats.size === metadata.size;

            const isValid = checksumValid && sizeValid;
            
            if (isValid) {
                metadata.verified = true;
                metadata.lastVerified = new Date();
            }

            this.emit('backup-verified', {
                backupId,
                isValid,
                checksumValid,
                sizeValid
            });

            return isValid;
        } catch (error) {
            this.emit('backup-verification-failed', {
                backupId,
                error: error.message
            });
            return false;
        }
    }

    async deleteBackup(userId, backupId) {
        const metadata = this.backupMetadata.get(backupId);
        if (!metadata || metadata.userId !== userId) {
            throw new Error('Backup not found or access denied');
        }

        // Check if this backup is required for incremental restore
        const dependentBackups = await this.findDependentBackups(userId, backupId);
        if (dependentBackups.length > 0) {
            throw new Error(`Cannot delete backup - ${dependentBackups.length} incremental backups depend on it`);
        }

        try {
            await fs.unlink(metadata.backupPath);
            
            const metadataFile = path.join(
                this.config.backupDir,
                userId,
                `${backupId}.metadata.json`
            );
            await fs.unlink(metadataFile);

            this.backupMetadata.delete(backupId);
            
            const userHistory = this.backupHistory.get(userId) || [];
            const updatedHistory = userHistory.filter(b => b.id !== backupId);
            this.backupHistory.set(userId, updatedHistory);

            this.emit('backup-deleted', { userId, backupId });

            return { success: true, backupId };
        } catch (error) {
            throw new Error(`Failed to delete backup: ${error.message}`);
        }
    }

    async findDependentBackups(userId, backupId) {
        const metadata = this.backupMetadata.get(backupId);
        if (!metadata || metadata.backupType !== this.config.backupTypes.full) {
            return [];
        }

        const userHistory = this.backupHistory.get(userId) || [];
        return userHistory.filter(backup => {
            if (backup.backupType !== this.config.backupTypes.incremental) {
                return false;
            }
            if (backup.projectPath !== metadata.projectPath) {
                return false;
            }
            return new Date(backup.timestamp) > new Date(metadata.timestamp);
        });
    }

    getUserBackups(userId, projectPath = null) {
        const userHistory = this.backupHistory.get(userId) || [];
        
        let backups = userHistory;
        if (projectPath) {
            backups = backups.filter(b => b.projectPath === projectPath);
        }

        return backups
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .map(backup => ({
                ...backup,
                metadata: this.backupMetadata.get(backup.id)
            }));
    }

    async getLastBackup(userId, projectPath) {
        const userHistory = this.backupHistory.get(userId) || [];
        const projectBackups = userHistory
            .filter(b => b.projectPath === projectPath)
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        return projectBackups.length > 0 ? 
            this.backupMetadata.get(projectBackups[0].id) : 
            null;
    }

    async loadBackupHistory() {
        try {
            const userDirs = await fs.readdir(this.config.backupDir);
            
            for (const userId of userDirs) {
                const userDir = path.join(this.config.backupDir, userId);
                const files = await fs.readdir(userDir);
                
                const metadataFiles = files.filter(f => f.endsWith('.metadata.json'));
                
                for (const metadataFile of metadataFiles) {
                    try {
                        const metadataPath = path.join(userDir, metadataFile);
                        const metadataContent = await fs.readFile(metadataPath, 'utf8');
                        const metadata = JSON.parse(metadataContent);
                        
                        this.backupMetadata.set(metadata.id, metadata);
                        this.recordBackupInHistory(userId, metadata);
                    } catch (error) {
                        console.error(`Failed to load backup metadata ${metadataFile}:`, error);
                    }
                }
            }

            this.emit('backup-history-loaded', {
                totalBackups: this.backupMetadata.size,
                users: this.backupHistory.size
            });
        } catch (error) {
            // Backup directory doesn't exist yet or is empty
            console.log('No existing backup history found');
        }
    }

    startCleanupScheduler() {
        // Run cleanup daily
        setInterval(() => {
            this.performCleanup().catch(console.error);
        }, 24 * 60 * 60 * 1000);
    }

    async performCleanup() {
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - this.config.retentionDays);

        let deletedCount = 0;

        for (const [userId, userHistory] of this.backupHistory.entries()) {
            const backupsToDelete = userHistory.filter(backup => 
                new Date(backup.timestamp) < cutoffDate
            );

            for (const backup of backupsToDelete) {
                try {
                    await this.deleteBackup(userId, backup.id);
                    deletedCount++;
                } catch (error) {
                    console.error(`Failed to cleanup backup ${backup.id}:`, error);
                }
            }
        }

        this.emit('cleanup-completed', {
            deletedCount,
            timestamp: new Date()
        });
    }

    getBackupStatistics() {
        const totalBackups = this.backupMetadata.size;
        const totalUsers = this.backupHistory.size;
        
        let totalSize = 0;
        let backupTypes = { full: 0, incremental: 0 };
        
        for (const metadata of this.backupMetadata.values()) {
            totalSize += metadata.size;
            backupTypes[metadata.backupType] = (backupTypes[metadata.backupType] || 0) + 1;
        }

        return {
            totalBackups,
            totalUsers,
            totalSize,
            backupTypes,
            activeBackups: this.activeBackups.size
        };
    }

    generateBackupId(userId, projectPath) {
        const timestamp = Date.now();
        const pathHash = createHash('md5').update(projectPath).digest('hex').substring(0, 8);
        return `backup_${userId}_${pathHash}_${timestamp}`;
    }

    async exportBackupIndex(format = 'json') {
        const index = {
            generated: new Date(),
            backups: []
        };

        for (const metadata of this.backupMetadata.values()) {
            index.backups.push({
                id: metadata.id,
                userId: metadata.userId,
                projectPath: metadata.projectPath,
                backupType: metadata.backupType,
                timestamp: metadata.timestamp,
                size: metadata.size,
                verified: metadata.verified
            });
        }

        if (format === 'json') {
            return JSON.stringify(index, null, 2);
        } else if (format === 'csv') {
            const headers = 'ID,UserID,ProjectPath,BackupType,Timestamp,Size,Verified\n';
            const rows = index.backups.map(b => 
                `${b.id},${b.userId},${b.projectPath},${b.backupType},${b.timestamp},${b.size},${b.verified}`
            ).join('\n');
            return headers + rows;
        }

        throw new Error('Unsupported export format');
    }

    shutdown() {
        // Wait for active backups to complete
        const activeBackupPromises = Array.from(this.activeBackups).map(async (backupKey) => {
            // Wait for backup to complete (with timeout)
            const timeout = 30000; // 30 seconds
            const startTime = Date.now();
            
            while (this.activeBackups.has(backupKey) && Date.now() - startTime < timeout) {
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        });

        Promise.all(activeBackupPromises).then(() => {
            this.emit('backup-service-shutdown', {
                timestamp: new Date(),
                stats: this.getBackupStatistics()
            });
        });
    }
}

module.exports = BackupService;