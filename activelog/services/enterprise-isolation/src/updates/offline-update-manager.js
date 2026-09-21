const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const winston = require('winston');
const archiver = require('archiver');
const unzipper = require('unzipper');
const moment = require('moment');

class OfflineUpdateManager {
    constructor(options = {}) {
        this.config = {
            updateStoragePath: options.updateStoragePath || path.join(process.cwd(), 'offline-updates'),
            packageValidationEnabled: options.packageValidationEnabled !== false,
            rollbackEnabled: options.rollbackEnabled !== false,
            updateChannels: {
                'security': {
                    priority: 'critical',
                    autoApply: true,
                    testingRequired: true,
                    approvalRequired: true
                },
                'stable': {
                    priority: 'high',
                    autoApply: false,
                    testingRequired: true,
                    approvalRequired: true
                },
                'maintenance': {
                    priority: 'medium',
                    autoApply: false,
                    testingRequired: false,
                    approvalRequired: false
                },
                'feature': {
                    priority: 'low',
                    autoApply: false,
                    testingRequired: true,
                    approvalRequired: true
                }
            },
            signatureVerification: {
                enabled: true,
                publicKeyPath: options.publicKeyPath || path.join(process.cwd(), 'keys', 'update-public.key'),
                algorithm: 'RSA-SHA512',
                requiredSignatures: 2 // Require dual signatures for security
            },
            backupBeforeUpdate: options.backupBeforeUpdate !== false,
            maxUpdateSize: options.maxUpdateSize || 1024 * 1024 * 1024, // 1GB
            updateTimeout: options.updateTimeout || 30 * 60 * 1000, // 30 minutes
            complianceRequirements: options.complianceRequirements || ['SOX', 'HIPAA', 'GDPR'],
            airgapValidation: {
                enabled: true,
                networkCheckRequired: true,
                isolationVerification: true
            }
        };

        this.logger = winston.createLogger({
            level: 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json()
            ),
            defaultMeta: { service: 'offline-update-manager' },
            transports: [
                new winston.transports.File({
                    filename: 'logs/update-error.log',
                    level: 'error'
                }),
                new winston.transports.File({
                    filename: 'logs/update.log'
                })
            ]
        });

        this.activeUpdates = new Map();
        this.updateHistory = [];
        this.rollbackQueue = [];
        this.currentVersion = null;
        this.updateMetrics = {
            totalUpdates: 0,
            successfulUpdates: 0,
            failedUpdates: 0,
            rolledBackUpdates: 0,
            lastUpdateTime: null
        };

        this.initializeUpdateSystem();
    }

    async initializeUpdateSystem() {
        try {
            // Create update storage directories
            await fs.mkdir(this.config.updateStoragePath, { recursive: true, mode: 0o700 });
            await fs.mkdir(path.join(this.config.updateStoragePath, 'packages'), { recursive: true, mode: 0o700 });
            await fs.mkdir(path.join(this.config.updateStoragePath, 'staging'), { recursive: true, mode: 0o700 });
            await fs.mkdir(path.join(this.config.updateStoragePath, 'backups'), { recursive: true, mode: 0o700 });
            await fs.mkdir(path.join(this.config.updateStoragePath, 'metadata'), { recursive: true, mode: 0o700 });

            // Load current version
            await this.loadCurrentVersion();

            // Load update history
            await this.loadUpdateHistory();

            // Validate air-gap status if required
            if (this.config.airgapValidation.enabled) {
                await this.validateAirgapStatus();
            }

            this.logger.info('Offline update system initialized', {
                updateStoragePath: this.config.updateStoragePath,
                currentVersion: this.currentVersion,
                signatureVerification: this.config.signatureVerification.enabled,
                airgapValidation: this.config.airgapValidation.enabled
            });

        } catch (error) {
            this.logger.error('Failed to initialize update system', { error: error.message });
            throw error;
        }
    }

    async importUpdatePackage(packagePath, options = {}) {
        const importId = crypto.randomUUID();
        
        this.logger.info('Starting update package import', {
            importId,
            packagePath,
            options
        });

        try {
            // Validate package file exists and size
            const packageStats = await fs.stat(packagePath);
            if (packageStats.size > this.config.maxUpdateSize) {
                throw new Error(`Package size ${packageStats.size} exceeds maximum ${this.config.maxUpdateSize}`);
            }

            // Extract and validate package metadata
            const packageInfo = await this.extractPackageMetadata(packagePath);
            
            // Validate package signatures if enabled
            if (this.config.signatureVerification.enabled) {
                const signatureValid = await this.verifyPackageSignatures(packagePath, packageInfo);
                if (!signatureValid) {
                    throw new Error('Package signature verification failed');
                }
            }

            // Check if package is newer than current version
            const versionComparison = this.compareVersions(packageInfo.version, this.currentVersion);
            if (versionComparison <= 0 && !options.forceImport) {
                throw new Error(`Package version ${packageInfo.version} is not newer than current ${this.currentVersion}`);
            }

            // Copy package to secure storage
            const packageFileName = `${packageInfo.name}-${packageInfo.version}-${packageInfo.channel}.pkg`;
            const storedPackagePath = path.join(this.config.updateStoragePath, 'packages', packageFileName);
            await fs.copyFile(packagePath, storedPackagePath);

            // Create package registry entry
            const packageEntry = {
                id: importId,
                name: packageInfo.name,
                version: packageInfo.version,
                channel: packageInfo.channel || 'stable',
                path: storedPackagePath,
                size: packageStats.size,
                importedAt: new Date(),
                importedBy: options.importedBy || 'system',
                metadata: packageInfo,
                status: 'imported',
                tested: false,
                approved: false,
                signatures: packageInfo.signatures || []
            };

            // Save package registry
            await this.savePackageRegistry(packageEntry);

            this.logger.info('Update package imported successfully', {
                importId,
                packageName: packageInfo.name,
                version: packageInfo.version,
                channel: packageInfo.channel,
                size: packageStats.size
            });

            return packageEntry;

        } catch (error) {
            this.logger.error('Failed to import update package', {
                importId,
                packagePath,
                error: error.message
            });
            throw error;
        }
    }

    async extractPackageMetadata(packagePath) {
        const stagingPath = path.join(this.config.updateStoragePath, 'staging', crypto.randomUUID());
        
        try {
            await fs.mkdir(stagingPath, { recursive: true });

            // Extract package to staging area
            await this.extractPackage(packagePath, stagingPath);

            // Read package metadata
            const metadataPath = path.join(stagingPath, 'package.json');
            const metadataContent = await fs.readFile(metadataPath, 'utf8');
            const metadata = JSON.parse(metadataContent);

            // Validate required metadata fields
            const requiredFields = ['name', 'version', 'description', 'updateType', 'dependencies'];
            for (const field of requiredFields) {
                if (!metadata[field]) {
                    throw new Error(`Missing required metadata field: ${field}`);
                }
            }

            // Read signatures if they exist
            const signaturesPath = path.join(stagingPath, 'signatures.json');
            try {
                const signaturesContent = await fs.readFile(signaturesPath, 'utf8');
                metadata.signatures = JSON.parse(signaturesContent);
            } catch {
                metadata.signatures = [];
            }

            return metadata;

        } finally {
            // Clean up staging directory
            try {
                await fs.rmdir(stagingPath, { recursive: true });
            } catch {
                // Ignore cleanup errors
            }
        }
    }

    async extractPackage(packagePath, targetPath) {
        return new Promise((resolve, reject) => {
            const stream = require('fs').createReadStream(packagePath)
                .pipe(unzipper.Extract({ path: targetPath }));
                
            stream.on('close', resolve);
            stream.on('error', reject);
        });
    }

    async verifyPackageSignatures(packagePath, packageInfo) {
        if (!packageInfo.signatures || packageInfo.signatures.length < this.config.signatureVerification.requiredSignatures) {
            this.logger.error('Insufficient signatures', {
                provided: packageInfo.signatures?.length || 0,
                required: this.config.signatureVerification.requiredSignatures
            });
            return false;
        }

        try {
            // Load public key(s)
            const publicKey = await fs.readFile(this.config.signatureVerification.publicKeyPath, 'utf8');

            // Calculate package hash
            const packageHash = await this.calculateFileHash(packagePath, 'sha512');

            // Verify each signature
            let validSignatures = 0;
            for (const signature of packageInfo.signatures) {
                try {
                    const verify = crypto.createVerify(this.config.signatureVerification.algorithm);
                    verify.update(packageHash);
                    
                    const signatureValid = verify.verify(publicKey, signature.signature, 'base64');
                    if (signatureValid) {
                        validSignatures++;
                        this.logger.debug('Signature verified', {
                            signer: signature.signer,
                            timestamp: signature.timestamp
                        });
                    }
                } catch (error) {
                    this.logger.warn('Signature verification failed', {
                        signer: signature.signer,
                        error: error.message
                    });
                }
            }

            const signatureValid = validSignatures >= this.config.signatureVerification.requiredSignatures;
            
            this.logger.info('Package signature verification completed', {
                validSignatures,
                requiredSignatures: this.config.signatureVerification.requiredSignatures,
                result: signatureValid ? 'VALID' : 'INVALID'
            });

            return signatureValid;

        } catch (error) {
            this.logger.error('Signature verification error', { error: error.message });
            return false;
        }
    }

    async applyUpdate(packageId, options = {}) {
        const updateId = crypto.randomUUID();
        const packageEntry = await this.getPackageById(packageId);
        
        if (!packageEntry) {
            throw new Error(`Package not found: ${packageId}`);
        }

        const channelConfig = this.config.updateChannels[packageEntry.channel];
        
        // Check if approval is required
        if (channelConfig.approvalRequired && !packageEntry.approved && !options.forceApply) {
            throw new Error('Update requires approval before application');
        }

        // Check if testing is required
        if (channelConfig.testingRequired && !packageEntry.tested && !options.skipTesting) {
            throw new Error('Update requires testing before application');
        }

        const updateJob = {
            id: updateId,
            packageId,
            packageEntry,
            startTime: new Date(),
            status: 'running',
            progress: 0,
            steps: [],
            options: {
                createBackup: this.config.backupBeforeUpdate,
                rollbackOnFailure: this.config.rollbackEnabled,
                validateIntegrity: true,
                ...options
            },
            rollbackInfo: null
        };

        this.activeUpdates.set(updateId, updateJob);

        this.logger.info('Starting update application', {
            updateId,
            packageId,
            packageName: packageEntry.name,
            version: packageEntry.version,
            channel: packageEntry.channel
        });

        try {
            // Step 1: Validate air-gap status
            if (this.config.airgapValidation.enabled) {
                updateJob.steps.push({ step: 'airgap_validation', status: 'running', startTime: new Date() });
                await this.validateAirgapStatus();
                updateJob.steps[updateJob.steps.length - 1].status = 'completed';
                updateJob.steps[updateJob.steps.length - 1].endTime = new Date();
                updateJob.progress = 10;
            }

            // Step 2: Create system backup
            if (updateJob.options.createBackup) {
                updateJob.steps.push({ step: 'backup_creation', status: 'running', startTime: new Date() });
                const backupInfo = await this.createSystemBackup(updateId);
                updateJob.rollbackInfo = backupInfo;
                updateJob.steps[updateJob.steps.length - 1].status = 'completed';
                updateJob.steps[updateJob.steps.length - 1].endTime = new Date();
                updateJob.steps[updateJob.steps.length - 1].backupPath = backupInfo.backupPath;
                updateJob.progress = 25;
            }

            // Step 3: Extract update package
            updateJob.steps.push({ step: 'package_extraction', status: 'running', startTime: new Date() });
            const extractPath = await this.extractUpdatePackage(packageEntry, updateId);
            updateJob.steps[updateJob.steps.length - 1].status = 'completed';
            updateJob.steps[updateJob.steps.length - 1].endTime = new Date();
            updateJob.steps[updateJob.steps.length - 1].extractPath = extractPath;
            updateJob.progress = 40;

            // Step 4: Validate update integrity
            if (updateJob.options.validateIntegrity) {
                updateJob.steps.push({ step: 'integrity_validation', status: 'running', startTime: new Date() });
                await this.validateUpdateIntegrity(extractPath, packageEntry.metadata);
                updateJob.steps[updateJob.steps.length - 1].status = 'completed';
                updateJob.steps[updateJob.steps.length - 1].endTime = new Date();
                updateJob.progress = 55;
            }

            // Step 5: Execute pre-update scripts
            updateJob.steps.push({ step: 'pre_update_scripts', status: 'running', startTime: new Date() });
            await this.executePreUpdateScripts(extractPath, packageEntry.metadata);
            updateJob.steps[updateJob.steps.length - 1].status = 'completed';
            updateJob.steps[updateJob.steps.length - 1].endTime = new Date();
            updateJob.progress = 70;

            // Step 6: Apply update files
            updateJob.steps.push({ step: 'file_deployment', status: 'running', startTime: new Date() });
            await this.deployUpdateFiles(extractPath, packageEntry.metadata);
            updateJob.steps[updateJob.steps.length - 1].status = 'completed';
            updateJob.steps[updateJob.steps.length - 1].endTime = new Date();
            updateJob.progress = 85;

            // Step 7: Execute post-update scripts
            updateJob.steps.push({ step: 'post_update_scripts', status: 'running', startTime: new Date() });
            await this.executePostUpdateScripts(extractPath, packageEntry.metadata);
            updateJob.steps[updateJob.steps.length - 1].status = 'completed';
            updateJob.steps[updateJob.steps.length - 1].endTime = new Date();
            updateJob.progress = 95;

            // Step 8: Update version information
            updateJob.steps.push({ step: 'version_update', status: 'running', startTime: new Date() });
            await this.updateVersionInfo(packageEntry.version, packageEntry.metadata);
            updateJob.steps[updateJob.steps.length - 1].status = 'completed';
            updateJob.steps[updateJob.steps.length - 1].endTime = new Date();
            updateJob.progress = 100;

            // Finalize update
            updateJob.status = 'completed';
            updateJob.endTime = new Date();
            updateJob.duration = updateJob.endTime - updateJob.startTime;

            // Update metrics
            this.updateMetrics.totalUpdates++;
            this.updateMetrics.successfulUpdates++;
            this.updateMetrics.lastUpdateTime = updateJob.endTime;

            // Save to history
            this.updateHistory.push(updateJob);
            await this.saveUpdateHistory();

            // Clean up extraction directory
            try {
                await fs.rmdir(extractPath, { recursive: true });
            } catch {
                // Ignore cleanup errors
            }

            this.logger.info('Update applied successfully', {
                updateId,
                packageName: packageEntry.name,
                fromVersion: this.currentVersion,
                toVersion: packageEntry.version,
                duration: updateJob.duration,
                channel: packageEntry.channel
            });

            this.currentVersion = packageEntry.version;
            await this.saveCurrentVersion();

            return updateJob;

        } catch (error) {
            updateJob.status = 'failed';
            updateJob.error = error.message;
            updateJob.endTime = new Date();

            // Mark current step as failed
            if (updateJob.steps.length > 0) {
                const currentStep = updateJob.steps[updateJob.steps.length - 1];
                if (currentStep.status === 'running') {
                    currentStep.status = 'failed';
                    currentStep.endTime = new Date();
                    currentStep.error = error.message;
                }
            }

            this.updateMetrics.totalUpdates++;
            this.updateMetrics.failedUpdates++;

            // Attempt rollback if enabled
            if (updateJob.options.rollbackOnFailure && updateJob.rollbackInfo) {
                try {
                    await this.performRollback(updateJob);
                } catch (rollbackError) {
                    this.logger.error('Rollback failed', {
                        updateId,
                        rollbackError: rollbackError.message
                    });
                }
            }

            this.logger.error('Update failed', {
                updateId,
                packageName: packageEntry.name,
                version: packageEntry.version,
                error: error.message,
                steps: updateJob.steps
            });

            throw error;

        } finally {
            this.activeUpdates.delete(updateId);
        }
    }

    async validateAirgapStatus() {
        if (!this.config.airgapValidation.networkCheckRequired) {
            return true;
        }

        // Verify network isolation
        const networkChecks = [
            this.checkNetworkConnectivity(),
            this.checkDNSResolution(),
            this.checkRunningNetworkServices()
        ];

        const results = await Promise.allSettled(networkChecks);
        const failures = results.filter(result => result.status === 'rejected' || result.value === false);

        if (failures.length > 0) {
            this.logger.info('Air-gap status verified - network isolation confirmed');
            return true;
        } else {
            throw new Error('Air-gap validation failed - network connectivity detected');
        }
    }

    async checkNetworkConnectivity() {
        // Try to ping common external hosts - should fail in air-gapped environment
        const { exec } = require('child_process');
        const util = require('util');
        const execAsync = util.promisify(exec);

        const hosts = ['8.8.8.8', '1.1.1.1', 'google.com'];
        
        for (const host of hosts) {
            try {
                await execAsync(`ping -c 1 -W 1 ${host}`, { timeout: 2000 });
                return true; // Network is accessible (not air-gapped)
            } catch {
                // Expected in air-gapped environment
            }
        }

        return false; // No network connectivity found
    }

    async checkDNSResolution() {
        const dns = require('dns');
        const util = require('util');
        const lookup = util.promisify(dns.lookup);

        try {
            await lookup('google.com');
            return true; // DNS is working (not air-gapped)
        } catch {
            return false; // No DNS resolution (expected in air-gapped)
        }
    }

    async checkRunningNetworkServices() {
        // Check if any services are listening on external interfaces
        const { exec } = require('child_process');
        const util = require('util');
        const execAsync = util.promisify(exec);

        try {
            const { stdout } = await execAsync('netstat -tuln');
            const lines = stdout.split('\n');
            
            for (const line of lines) {
                if (line.includes(':80 ') || line.includes(':443 ') || line.includes(':22 ')) {
                    // Check if listening on all interfaces (0.0.0.0)
                    if (line.includes('0.0.0.0:')) {
                        return true; // External services running
                    }
                }
            }
        } catch {
            // Command failed - assume secure
        }

        return false; // No external services detected
    }

    async createSystemBackup(updateId) {
        const backupPath = path.join(this.config.updateStoragePath, 'backups', `pre-update-${updateId}.backup`);
        
        // Create backup of critical system files
        const backupData = {
            version: this.currentVersion,
            timestamp: new Date(),
            updateId,
            files: {}
        };

        // Backup application files
        const appFiles = ['package.json', 'package-lock.json'];
        for (const file of appFiles) {
            const filePath = path.join(process.cwd(), file);
            try {
                const content = await fs.readFile(filePath, 'utf8');
                backupData.files[file] = content;
            } catch {
                // File doesn't exist
            }
        }

        // Backup configuration
        const configPath = path.join(process.cwd(), 'config');
        try {
            const configFiles = await fs.readdir(configPath);
            for (const configFile of configFiles) {
                const fullPath = path.join(configPath, configFile);
                const stats = await fs.stat(fullPath);
                if (stats.isFile()) {
                    const content = await fs.readFile(fullPath, 'utf8');
                    backupData.files[`config/${configFile}`] = content;
                }
            }
        } catch {
            // Config directory doesn't exist
        }

        // Save backup
        await fs.writeFile(backupPath, JSON.stringify(backupData, null, 2), { mode: 0o600 });

        this.logger.info('System backup created', {
            updateId,
            backupPath,
            fileCount: Object.keys(backupData.files).length
        });

        return { backupPath, backupData };
    }

    async extractUpdatePackage(packageEntry, updateId) {
        const extractPath = path.join(this.config.updateStoragePath, 'staging', `update-${updateId}`);
        await fs.mkdir(extractPath, { recursive: true });

        await this.extractPackage(packageEntry.path, extractPath);

        this.logger.debug('Update package extracted', {
            packagePath: packageEntry.path,
            extractPath,
            updateId
        });

        return extractPath;
    }

    async validateUpdateIntegrity(extractPath, metadata) {
        // Validate checksums if provided
        if (metadata.checksums) {
            for (const [file, expectedHash] of Object.entries(metadata.checksums)) {
                const filePath = path.join(extractPath, file);
                try {
                    const actualHash = await this.calculateFileHash(filePath, 'sha256');
                    if (actualHash !== expectedHash) {
                        throw new Error(`Integrity check failed for file: ${file}`);
                    }
                } catch (error) {
                    throw new Error(`Failed to validate integrity of ${file}: ${error.message}`);
                }
            }
        }

        // Validate required files exist
        if (metadata.requiredFiles) {
            for (const requiredFile of metadata.requiredFiles) {
                const filePath = path.join(extractPath, requiredFile);
                try {
                    await fs.access(filePath);
                } catch {
                    throw new Error(`Required file missing: ${requiredFile}`);
                }
            }
        }

        this.logger.debug('Update integrity validation completed', {
            extractPath,
            checksumValidations: metadata.checksums ? Object.keys(metadata.checksums).length : 0,
            requiredFileChecks: metadata.requiredFiles ? metadata.requiredFiles.length : 0
        });
    }

    async executePreUpdateScripts(extractPath, metadata) {
        if (!metadata.scripts || !metadata.scripts.preUpdate) {
            return;
        }

        const scriptPath = path.join(extractPath, metadata.scripts.preUpdate);
        
        try {
            await fs.access(scriptPath);
            
            // Execute script with appropriate permissions
            const { exec } = require('child_process');
            const util = require('util');
            const execAsync = util.promisify(exec);

            const { stdout, stderr } = await execAsync(`node "${scriptPath}"`, {
                cwd: extractPath,
                timeout: this.config.updateTimeout,
                env: { ...process.env, UPDATE_MODE: 'pre' }
            });

            this.logger.debug('Pre-update script executed', {
                script: metadata.scripts.preUpdate,
                stdout: stdout.substring(0, 1000),
                stderr: stderr.substring(0, 1000)
            });

        } catch (error) {
            throw new Error(`Pre-update script failed: ${error.message}`);
        }
    }

    async deployUpdateFiles(extractPath, metadata) {
        const deploymentMap = metadata.deployment || {};

        for (const [source, destination] of Object.entries(deploymentMap)) {
            const sourcePath = path.join(extractPath, source);
            const destPath = path.resolve(process.cwd(), destination);

            try {
                // Ensure destination directory exists
                await fs.mkdir(path.dirname(destPath), { recursive: true });

                // Copy file
                await fs.copyFile(sourcePath, destPath);

                this.logger.debug('File deployed', { source, destination: destPath });

            } catch (error) {
                throw new Error(`Failed to deploy ${source} to ${destination}: ${error.message}`);
            }
        }

        // If no deployment map is provided, copy all files except metadata
        if (Object.keys(deploymentMap).length === 0) {
            const files = await this.getFilesRecursively(extractPath);
            const excludeFiles = ['package.json', 'signatures.json', 'scripts/'];

            for (const file of files) {
                const relativePath = path.relative(extractPath, file);
                
                if (excludeFiles.some(exclude => relativePath.startsWith(exclude))) {
                    continue;
                }

                const destPath = path.join(process.cwd(), relativePath);
                await fs.mkdir(path.dirname(destPath), { recursive: true });
                await fs.copyFile(file, destPath);
            }
        }
    }

    async executePostUpdateScripts(extractPath, metadata) {
        if (!metadata.scripts || !metadata.scripts.postUpdate) {
            return;
        }

        const scriptPath = path.join(extractPath, metadata.scripts.postUpdate);
        
        try {
            await fs.access(scriptPath);
            
            const { exec } = require('child_process');
            const util = require('util');
            const execAsync = util.promisify(exec);

            const { stdout, stderr } = await execAsync(`node "${scriptPath}"`, {
                cwd: process.cwd(),
                timeout: this.config.updateTimeout,
                env: { ...process.env, UPDATE_MODE: 'post' }
            });

            this.logger.debug('Post-update script executed', {
                script: metadata.scripts.postUpdate,
                stdout: stdout.substring(0, 1000),
                stderr: stderr.substring(0, 1000)
            });

        } catch (error) {
            throw new Error(`Post-update script failed: ${error.message}`);
        }
    }

    async updateVersionInfo(newVersion, metadata) {
        this.currentVersion = newVersion;
        
        // Update package.json if it exists
        const packageJsonPath = path.join(process.cwd(), 'package.json');
        try {
            const packageJson = JSON.parse(await fs.readFile(packageJsonPath, 'utf8'));
            packageJson.version = newVersion;
            
            if (metadata.updatePackageJson) {
                Object.assign(packageJson, metadata.updatePackageJson);
            }

            await fs.writeFile(packageJsonPath, JSON.stringify(packageJson, null, 2));
            
        } catch (error) {
            this.logger.warn('Could not update package.json', { error: error.message });
        }

        await this.saveCurrentVersion();
    }

    async performRollback(updateJob) {
        if (!updateJob.rollbackInfo) {
            throw new Error('No rollback information available');
        }

        const rollbackId = crypto.randomUUID();
        
        this.logger.info('Starting rollback', {
            rollbackId,
            updateId: updateJob.id,
            backupPath: updateJob.rollbackInfo.backupPath
        });

        try {
            // Load backup data
            const backupContent = await fs.readFile(updateJob.rollbackInfo.backupPath, 'utf8');
            const backupData = JSON.parse(backupContent);

            // Restore files from backup
            for (const [relativePath, content] of Object.entries(backupData.files)) {
                const filePath = path.join(process.cwd(), relativePath);
                await fs.mkdir(path.dirname(filePath), { recursive: true });
                await fs.writeFile(filePath, content);
            }

            // Restore version
            this.currentVersion = backupData.version;
            await this.saveCurrentVersion();

            // Update metrics
            this.updateMetrics.rolledBackUpdates++;

            // Add to rollback queue for tracking
            this.rollbackQueue.push({
                rollbackId,
                updateId: updateJob.id,
                rollbackTime: new Date(),
                restoredVersion: backupData.version
            });

            this.logger.info('Rollback completed successfully', {
                rollbackId,
                updateId: updateJob.id,
                restoredVersion: backupData.version
            });

        } catch (error) {
            this.logger.error('Rollback failed', {
                rollbackId,
                updateId: updateJob.id,
                error: error.message
            });
            throw error;
        }
    }

    async listAvailableUpdates() {
        const packagesPath = path.join(this.config.updateStoragePath, 'metadata', 'packages.json');
        
        try {
            const packagesContent = await fs.readFile(packagesPath, 'utf8');
            const packagesData = JSON.parse(packagesContent);
            
            return packagesData.packages.filter(pkg => {
                // Only show packages newer than current version
                return this.compareVersions(pkg.version, this.currentVersion) > 0;
            }).sort((a, b) => {
                // Sort by version descending
                return this.compareVersions(b.version, a.version);
            });
            
        } catch (error) {
            this.logger.warn('Could not load available updates', { error: error.message });
            return [];
        }
    }

    async approveUpdate(packageId, approvedBy) {
        const packageEntry = await this.getPackageById(packageId);
        if (!packageEntry) {
            throw new Error(`Package not found: ${packageId}`);
        }

        packageEntry.approved = true;
        packageEntry.approvedBy = approvedBy;
        packageEntry.approvedAt = new Date();

        await this.updatePackageRegistry(packageEntry);

        this.logger.info('Update approved', {
            packageId,
            packageName: packageEntry.name,
            version: packageEntry.version,
            approvedBy
        });
    }

    async testUpdate(packageId, testResults) {
        const packageEntry = await this.getPackageById(packageId);
        if (!packageEntry) {
            throw new Error(`Package not found: ${packageId}`);
        }

        packageEntry.tested = true;
        packageEntry.testResults = testResults;
        packageEntry.testedAt = new Date();

        await this.updatePackageRegistry(packageEntry);

        this.logger.info('Update tested', {
            packageId,
            packageName: packageEntry.name,
            version: packageEntry.version,
            testResults: testResults.summary
        });
    }

    compareVersions(version1, version2) {
        if (!version1 || !version2) return 0;
        
        const v1Parts = version1.split('.').map(Number);
        const v2Parts = version2.split('.').map(Number);
        
        for (let i = 0; i < Math.max(v1Parts.length, v2Parts.length); i++) {
            const v1Part = v1Parts[i] || 0;
            const v2Part = v2Parts[i] || 0;
            
            if (v1Part > v2Part) return 1;
            if (v1Part < v2Part) return -1;
        }
        
        return 0;
    }

    async calculateFileHash(filePath, algorithm = 'sha256') {
        const hash = crypto.createHash(algorithm);
        const stream = require('fs').createReadStream(filePath);

        return new Promise((resolve, reject) => {
            stream.on('data', data => hash.update(data));
            stream.on('end', () => resolve(hash.digest('hex')));
            stream.on('error', reject);
        });
    }

    async getFilesRecursively(dir) {
        const files = [];
        const items = await fs.readdir(dir);

        for (const item of items) {
            const fullPath = path.join(dir, item);
            const stats = await fs.stat(fullPath);

            if (stats.isDirectory()) {
                const subFiles = await this.getFilesRecursively(fullPath);
                files.push(...subFiles);
            } else {
                files.push(fullPath);
            }
        }

        return files;
    }

    async loadCurrentVersion() {
        const versionPath = path.join(this.config.updateStoragePath, '.current-version');
        
        try {
            const versionContent = await fs.readFile(versionPath, 'utf8');
            this.currentVersion = versionContent.trim();
        } catch {
            // Try to load from package.json
            try {
                const packageJsonPath = path.join(process.cwd(), 'package.json');
                const packageJson = JSON.parse(await fs.readFile(packageJsonPath, 'utf8'));
                this.currentVersion = packageJson.version || '1.0.0';
            } catch {
                this.currentVersion = '1.0.0';
            }
        }
    }

    async saveCurrentVersion() {
        const versionPath = path.join(this.config.updateStoragePath, '.current-version');
        await fs.writeFile(versionPath, this.currentVersion, { mode: 0o600 });
    }

    async savePackageRegistry(packageEntry) {
        const packagesPath = path.join(this.config.updateStoragePath, 'metadata', 'packages.json');
        
        let packagesData = { packages: [] };
        try {
            const existing = await fs.readFile(packagesPath, 'utf8');
            packagesData = JSON.parse(existing);
        } catch {
            // New registry
        }

        packagesData.packages.push(packageEntry);
        await fs.writeFile(packagesPath, JSON.stringify(packagesData, null, 2), { mode: 0o600 });
    }

    async updatePackageRegistry(packageEntry) {
        const packagesPath = path.join(this.config.updateStoragePath, 'metadata', 'packages.json');
        
        try {
            const packagesContent = await fs.readFile(packagesPath, 'utf8');
            const packagesData = JSON.parse(packagesContent);
            
            const index = packagesData.packages.findIndex(pkg => pkg.id === packageEntry.id);
            if (index !== -1) {
                packagesData.packages[index] = packageEntry;
                await fs.writeFile(packagesPath, JSON.stringify(packagesData, null, 2), { mode: 0o600 });
            }
        } catch (error) {
            this.logger.error('Failed to update package registry', { error: error.message });
        }
    }

    async getPackageById(packageId) {
        const packagesPath = path.join(this.config.updateStoragePath, 'metadata', 'packages.json');
        
        try {
            const packagesContent = await fs.readFile(packagesPath, 'utf8');
            const packagesData = JSON.parse(packagesContent);
            
            return packagesData.packages.find(pkg => pkg.id === packageId);
        } catch {
            return null;
        }
    }

    async loadUpdateHistory() {
        const historyPath = path.join(this.config.updateStoragePath, 'metadata', 'history.json');
        
        try {
            const historyContent = await fs.readFile(historyPath, 'utf8');
            const historyData = JSON.parse(historyContent);
            this.updateHistory = historyData.history || [];
        } catch {
            this.updateHistory = [];
        }
    }

    async saveUpdateHistory() {
        const historyPath = path.join(this.config.updateStoragePath, 'metadata', 'history.json');
        
        const historyData = {
            lastUpdated: new Date(),
            history: this.updateHistory.slice(-100) // Keep last 100 updates
        };

        await fs.writeFile(historyPath, JSON.stringify(historyData, null, 2), { mode: 0o600 });
    }

    getUpdateStatus() {
        return {
            currentVersion: this.currentVersion,
            activeUpdates: Array.from(this.activeUpdates.values()),
            metrics: this.updateMetrics,
            recentHistory: this.updateHistory.slice(-10),
            rollbackQueue: this.rollbackQueue.slice(-5),
            airgapStatus: this.config.airgapValidation.enabled
        };
    }
}

module.exports = OfflineUpdateManager;