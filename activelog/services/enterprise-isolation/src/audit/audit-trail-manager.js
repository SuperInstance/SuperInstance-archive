const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const winston = require('winston');
const moment = require('moment');

class AuditTrailManager {
    constructor(options = {}) {
        this.config = {
            storageLocation: options.storageLocation || path.join(process.cwd(), 'audit-trails'),
            retentionPeriods: {
                'authentication': 2555, // 7 years in days
                'data_access': 2190, // 6 years
                'system_changes': 2555, // 7 years
                'financial': 2555, // 7 years (SOX requirement)
                'security_events': 1825, // 5 years
                'admin_actions': 2190, // 6 years
                'compliance': 2555, // 7 years
                'default': 1095 // 3 years
            },
            encryptionKey: options.encryptionKey || crypto.randomBytes(32),
            integrityKey: options.integrityKey || crypto.randomBytes(32),
            maxLogFileSize: options.maxLogFileSize || 100 * 1024 * 1024, // 100MB
            compressionEnabled: options.compressionEnabled !== false,
            tamperProofing: {
                enabled: true,
                hashAlgorithm: 'sha512',
                signatureRequired: true,
                blockchainIntegrity: options.blockchainIntegrity || false
            },
            eventCategories: {
                'AUTHENTICATION': {
                    level: 'info',
                    retention: 2555,
                    encryption: true,
                    realTimeAlert: true
                },
                'AUTHORIZATION': {
                    level: 'info',
                    retention: 2190,
                    encryption: true,
                    realTimeAlert: true
                },
                'DATA_ACCESS': {
                    level: 'info',
                    retention: 2190,
                    encryption: true,
                    realTimeAlert: false
                },
                'DATA_MODIFICATION': {
                    level: 'warn',
                    retention: 2555,
                    encryption: true,
                    realTimeAlert: true
                },
                'SYSTEM_CONFIGURATION': {
                    level: 'warn',
                    retention: 2555,
                    encryption: true,
                    realTimeAlert: true
                },
                'SECURITY_EVENT': {
                    level: 'error',
                    retention: 1825,
                    encryption: true,
                    realTimeAlert: true
                },
                'ADMIN_ACTION': {
                    level: 'warn',
                    retention: 2190,
                    encryption: true,
                    realTimeAlert: true
                },
                'COMPLIANCE': {
                    level: 'info',
                    retention: 2555,
                    encryption: true,
                    realTimeAlert: false
                },
                'FINANCIAL': {
                    level: 'warn',
                    retention: 2555,
                    encryption: true,
                    realTimeAlert: true
                },
                'PRIVACY': {
                    level: 'info',
                    retention: 2190,
                    encryption: true,
                    realTimeAlert: true
                }
            }
        };

        this.logger = winston.createLogger({
            level: 'debug',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json()
            ),
            defaultMeta: { service: 'audit-trail-manager' },
            transports: [
                new winston.transports.File({
                    filename: 'logs/audit-manager-error.log',
                    level: 'error'
                }),
                new winston.transports.File({
                    filename: 'logs/audit-manager.log'
                })
            ]
        });

        this.auditChain = [];
        this.pendingEntries = new Map();
        this.sequenceNumber = 0;
        this.currentLogFiles = new Map();
        this.integrityChecks = new Map();

        this.initializeAuditSystem();
    }

    async initializeAuditSystem() {
        try {
            // Create audit storage directory
            await fs.mkdir(this.config.storageLocation, { recursive: true, mode: 0o700 });

            // Initialize integrity chain
            await this.initializeIntegrityChain();

            // Load existing sequence number
            await this.loadSequenceNumber();

            // Start background processes
            this.startBackgroundProcesses();

            this.logger.info('Audit trail system initialized', {
                storageLocation: this.config.storageLocation,
                tamperProofing: this.config.tamperProofing.enabled,
                categories: Object.keys(this.config.eventCategories).length
            });

        } catch (error) {
            this.logger.error('Failed to initialize audit system', { error: error.message });
            throw error;
        }
    }

    async logEvent(eventData) {
        const timestamp = new Date();
        const eventId = crypto.randomUUID();
        const category = eventData.category || 'GENERAL';
        
        // Validate required fields
        const validationResult = this.validateEventData(eventData);
        if (!validationResult.valid) {
            throw new Error(`Invalid audit event data: ${validationResult.errors.join(', ')}`);
        }

        // Create audit entry
        const auditEntry = {
            eventId,
            sequenceNumber: ++this.sequenceNumber,
            timestamp: timestamp.toISOString(),
            category,
            eventType: eventData.eventType,
            userId: eventData.userId,
            sessionId: eventData.sessionId,
            sourceIP: eventData.sourceIP,
            userAgent: eventData.userAgent,
            resource: eventData.resource,
            action: eventData.action,
            outcome: eventData.outcome || 'SUCCESS',
            details: eventData.details || {},
            severity: eventData.severity || 'INFO',
            complianceRelevant: eventData.complianceRelevant !== false,
            dataClassification: eventData.dataClassification || 'INTERNAL',
            jurisdiction: eventData.jurisdiction || 'US',
            correlationId: eventData.correlationId,
            parentEventId: eventData.parentEventId,
            metadata: {
                hostname: require('os').hostname(),
                processId: process.pid,
                nodeVersion: process.version,
                systemTime: timestamp.getTime(),
                timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
            }
        };

        // Add integrity information
        const integrityData = await this.createIntegrityData(auditEntry);
        auditEntry.integrity = integrityData;

        // Encrypt sensitive data if required
        const categoryConfig = this.config.eventCategories[category];
        if (categoryConfig && categoryConfig.encryption) {
            auditEntry.encrypted = await this.encryptSensitiveData(auditEntry);
        }

        // Store the audit entry
        await this.storeAuditEntry(auditEntry);

        // Update audit chain for tamper detection
        this.updateAuditChain(auditEntry);

        // Send real-time alerts if configured
        if (categoryConfig && categoryConfig.realTimeAlert) {
            await this.sendRealTimeAlert(auditEntry);
        }

        // Log to system logger as backup
        this.logger.info('Audit event logged', {
            eventId,
            category,
            eventType: auditEntry.eventType,
            userId: auditEntry.userId,
            outcome: auditEntry.outcome
        });

        return eventId;
    }

    validateEventData(eventData) {
        const errors = [];
        const required = ['eventType', 'userId', 'action'];

        for (const field of required) {
            if (!eventData[field]) {
                errors.push(`Missing required field: ${field}`);
            }
        }

        if (eventData.category && !this.config.eventCategories[eventData.category]) {
            errors.push(`Invalid category: ${eventData.category}`);
        }

        if (eventData.outcome && !['SUCCESS', 'FAILURE', 'WARNING', 'ERROR'].includes(eventData.outcome)) {
            errors.push(`Invalid outcome: ${eventData.outcome}`);
        }

        return {
            valid: errors.length === 0,
            errors
        };
    }

    async createIntegrityData(auditEntry) {
        const entryString = JSON.stringify({
            eventId: auditEntry.eventId,
            sequenceNumber: auditEntry.sequenceNumber,
            timestamp: auditEntry.timestamp,
            category: auditEntry.category,
            eventType: auditEntry.eventType,
            userId: auditEntry.userId,
            action: auditEntry.action,
            outcome: auditEntry.outcome
        });

        const hash = crypto.createHash(this.config.tamperProofing.hashAlgorithm)
            .update(entryString)
            .digest('hex');

        const signature = crypto.createHmac('sha512', this.config.integrityKey)
            .update(entryString)
            .digest('hex');

        // Chain with previous entry
        const previousHash = this.auditChain.length > 0 
            ? this.auditChain[this.auditChain.length - 1].hash 
            : '0000000000000000000000000000000000000000000000000000000000000000';

        const chainHash = crypto.createHash('sha256')
            .update(previousHash + hash)
            .digest('hex');

        return {
            hash,
            signature,
            chainHash,
            previousHash,
            algorithm: this.config.tamperProofing.hashAlgorithm,
            timestamp: Date.now()
        };
    }

    async encryptSensitiveData(auditEntry) {
        const sensitiveFields = ['details', 'metadata'];
        const encryptedData = {};

        for (const field of sensitiveFields) {
            if (auditEntry[field]) {
                const plaintext = JSON.stringify(auditEntry[field]);
                const iv = crypto.randomBytes(16);
                const cipher = crypto.createCipher('aes-256-gcm', this.config.encryptionKey, { iv });
                
                let encrypted = cipher.update(plaintext, 'utf8', 'hex');
                encrypted += cipher.final('hex');
                
                const authTag = cipher.getAuthTag();

                encryptedData[field] = {
                    data: encrypted,
                    iv: iv.toString('hex'),
                    authTag: authTag.toString('hex'),
                    algorithm: 'aes-256-gcm'
                };

                // Remove original data
                delete auditEntry[field];
            }
        }

        return encryptedData;
    }

    async decryptAuditData(encryptedData) {
        const decryptedData = {};

        for (const [field, encryption] of Object.entries(encryptedData)) {
            try {
                const iv = Buffer.from(encryption.iv, 'hex');
                const authTag = Buffer.from(encryption.authTag, 'hex');
                const decipher = crypto.createDecipher('aes-256-gcm', this.config.encryptionKey, { iv });
                
                decipher.setAuthTag(authTag);
                
                let decrypted = decipher.update(encryption.data, 'hex', 'utf8');
                decrypted += decipher.final('utf8');
                
                decryptedData[field] = JSON.parse(decrypted);
            } catch (error) {
                this.logger.error('Failed to decrypt audit data', {
                    field,
                    error: error.message
                });
                decryptedData[field] = { error: 'Decryption failed' };
            }
        }

        return decryptedData;
    }

    async storeAuditEntry(auditEntry) {
        const category = auditEntry.category;
        const date = moment(auditEntry.timestamp).format('YYYY-MM-DD');
        const fileName = `audit-${category.toLowerCase()}-${date}.jsonl`;
        const filePath = path.join(this.config.storageLocation, fileName);

        // Check if we need to rotate the log file
        await this.checkLogRotation(filePath);

        // Append to log file
        const logLine = JSON.stringify(auditEntry) + '\n';
        await fs.appendFile(filePath, logLine, { mode: 0o600 });

        // Update file tracking
        if (!this.currentLogFiles.has(category)) {
            this.currentLogFiles.set(category, new Set());
        }
        this.currentLogFiles.get(category).add(filePath);

        // Store in pending entries for batch processing
        this.pendingEntries.set(auditEntry.eventId, auditEntry);
    }

    async checkLogRotation(filePath) {
        try {
            const stats = await fs.stat(filePath);
            if (stats.size > this.config.maxLogFileSize) {
                await this.rotateLogFile(filePath);
            }
        } catch (error) {
            // File doesn't exist yet, no rotation needed
        }
    }

    async rotateLogFile(filePath) {
        const timestamp = moment().format('YYYYMMDDHHmmss');
        const rotatedPath = `${filePath}.${timestamp}`;
        
        await fs.rename(filePath, rotatedPath);
        
        // Compress rotated file if enabled
        if (this.config.compressionEnabled) {
            await this.compressLogFile(rotatedPath);
        }

        this.logger.info('Log file rotated', {
            originalPath: filePath,
            rotatedPath,
            compressed: this.config.compressionEnabled
        });
    }

    async compressLogFile(filePath) {
        const zlib = require('zlib');
        const pipeline = require('util').promisify(require('stream').pipeline);
        
        const gzip = zlib.createGzip({ level: 9 });
        const source = require('fs').createReadStream(filePath);
        const destination = require('fs').createWriteStream(filePath + '.gz');

        await pipeline(source, gzip, destination);
        await fs.unlink(filePath); // Remove uncompressed file
    }

    updateAuditChain(auditEntry) {
        this.auditChain.push({
            eventId: auditEntry.eventId,
            hash: auditEntry.integrity.hash,
            chainHash: auditEntry.integrity.chainHash,
            timestamp: auditEntry.timestamp
        });

        // Keep only last 10000 entries in memory
        if (this.auditChain.length > 10000) {
            this.auditChain = this.auditChain.slice(-10000);
        }
    }

    async sendRealTimeAlert(auditEntry) {
        // Send alerts for critical events
        const alertConditions = [
            auditEntry.category === 'SECURITY_EVENT',
            auditEntry.outcome === 'FAILURE' && auditEntry.category === 'AUTHENTICATION',
            auditEntry.severity === 'CRITICAL' || auditEntry.severity === 'HIGH',
            auditEntry.eventType === 'PRIVILEGE_ESCALATION',
            auditEntry.eventType === 'DATA_EXFILTRATION'
        ];

        if (alertConditions.some(condition => condition)) {
            // In a real implementation, this would send to SIEM, email, SMS, etc.
            this.logger.error('SECURITY ALERT: Critical audit event', {
                eventId: auditEntry.eventId,
                category: auditEntry.category,
                eventType: auditEntry.eventType,
                userId: auditEntry.userId,
                outcome: auditEntry.outcome,
                timestamp: auditEntry.timestamp
            });

            // Emit event for other systems to handle
            process.emit('securityAlert', auditEntry);
        }
    }

    async queryAuditTrail(query) {
        const {
            startDate,
            endDate,
            category,
            userId,
            eventType,
            outcome,
            sourceIP,
            limit = 1000,
            offset = 0,
            includeEncrypted = false
        } = query;

        const results = [];
        const searchPattern = this.buildSearchPattern(query);

        // Determine which log files to search
        const filesToSearch = await this.getLogFilesForDateRange(startDate, endDate, category);

        for (const filePath of filesToSearch) {
            try {
                const entries = await this.searchLogFile(filePath, searchPattern, limit - results.length);
                
                // Decrypt entries if requested and user has permission
                for (const entry of entries) {
                    if (entry.encrypted && includeEncrypted) {
                        const decryptedData = await this.decryptAuditData(entry.encrypted);
                        Object.assign(entry, decryptedData);
                        delete entry.encrypted;
                    }
                    results.push(entry);
                }

                if (results.length >= limit) break;
            } catch (error) {
                this.logger.error('Error searching log file', {
                    filePath,
                    error: error.message
                });
            }
        }

        // Sort by timestamp and apply offset/limit
        const sortedResults = results
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(offset, offset + limit);

        return {
            results: sortedResults,
            totalFound: results.length,
            query,
            searchedFiles: filesToSearch.length
        };
    }

    buildSearchPattern(query) {
        const patterns = [];

        if (query.category) patterns.push(`"category":"${query.category}"`);
        if (query.userId) patterns.push(`"userId":"${query.userId}"`);
        if (query.eventType) patterns.push(`"eventType":"${query.eventType}"`);
        if (query.outcome) patterns.push(`"outcome":"${query.outcome}"`);
        if (query.sourceIP) patterns.push(`"sourceIP":"${query.sourceIP}"`);

        return new RegExp(patterns.join('.*'), 'i');
    }

    async getLogFilesForDateRange(startDate, endDate, category) {
        const files = [];
        const start = moment(startDate || moment().subtract(30, 'days'));
        const end = moment(endDate || moment());

        const storageFiles = await fs.readdir(this.config.storageLocation);

        for (const file of storageFiles) {
            // Match audit log files
            const match = file.match(/^audit-(.+)-(\d{4}-\d{2}-\d{2})\.jsonl/);
            if (!match) continue;

            const [, fileCategory, dateStr] = match;
            const fileDate = moment(dateStr);

            // Check if file matches criteria
            if (category && fileCategory !== category.toLowerCase()) continue;
            if (fileDate.isBefore(start) || fileDate.isAfter(end)) continue;

            files.push(path.join(this.config.storageLocation, file));
        }

        return files.sort().reverse(); // Most recent first
    }

    async searchLogFile(filePath, pattern, maxResults) {
        const results = [];
        const data = await fs.readFile(filePath, 'utf8');
        const lines = data.split('\n').filter(line => line.trim());

        for (const line of lines) {
            if (results.length >= maxResults) break;

            try {
                if (pattern.test(line)) {
                    const entry = JSON.parse(line);
                    results.push(entry);
                }
            } catch (error) {
                // Skip malformed lines
                this.logger.warn('Malformed audit log line', { filePath, line: line.substring(0, 100) });
            }
        }

        return results;
    }

    async verifyIntegrity(options = {}) {
        const { category, startDate, endDate, deep = false } = options;
        const verificationResult = {
            verified: true,
            totalEntries: 0,
            verifiedEntries: 0,
            failedEntries: 0,
            corruptedEntries: [],
            chainIntegrity: true,
            timestamp: new Date()
        };

        try {
            // Get log files to verify
            const filesToVerify = await this.getLogFilesForDateRange(startDate, endDate, category);

            for (const filePath of filesToVerify) {
                const entries = await this.getEntriesFromFile(filePath);
                
                for (const entry of entries) {
                    verificationResult.totalEntries++;

                    // Verify individual entry integrity
                    const entryValid = await this.verifyEntryIntegrity(entry);
                    if (entryValid) {
                        verificationResult.verifiedEntries++;
                    } else {
                        verificationResult.failedEntries++;
                        verificationResult.verified = false;
                        verificationResult.corruptedEntries.push({
                            eventId: entry.eventId,
                            filePath,
                            reason: 'Integrity hash mismatch'
                        });
                    }

                    // Deep verification includes chain verification
                    if (deep && entry.integrity) {
                        const chainValid = await this.verifyChainIntegrity(entry);
                        if (!chainValid) {
                            verificationResult.chainIntegrity = false;
                            verificationResult.verified = false;
                        }
                    }
                }
            }

            this.logger.info('Integrity verification completed', verificationResult);
            return verificationResult;

        } catch (error) {
            this.logger.error('Integrity verification failed', { error: error.message });
            return {
                ...verificationResult,
                verified: false,
                error: error.message
            };
        }
    }

    async getEntriesFromFile(filePath) {
        const entries = [];
        const data = await fs.readFile(filePath, 'utf8');
        const lines = data.split('\n').filter(line => line.trim());

        for (const line of lines) {
            try {
                entries.push(JSON.parse(line));
            } catch (error) {
                this.logger.warn('Failed to parse audit entry', { filePath, error: error.message });
            }
        }

        return entries;
    }

    async verifyEntryIntegrity(entry) {
        if (!entry.integrity) return false;

        try {
            const entryString = JSON.stringify({
                eventId: entry.eventId,
                sequenceNumber: entry.sequenceNumber,
                timestamp: entry.timestamp,
                category: entry.category,
                eventType: entry.eventType,
                userId: entry.userId,
                action: entry.action,
                outcome: entry.outcome
            });

            const expectedHash = crypto.createHash(this.config.tamperProofing.hashAlgorithm)
                .update(entryString)
                .digest('hex');

            const expectedSignature = crypto.createHmac('sha512', this.config.integrityKey)
                .update(entryString)
                .digest('hex');

            return entry.integrity.hash === expectedHash && 
                   entry.integrity.signature === expectedSignature;

        } catch (error) {
            this.logger.error('Error verifying entry integrity', {
                eventId: entry.eventId,
                error: error.message
            });
            return false;
        }
    }

    async verifyChainIntegrity(entry) {
        if (!entry.integrity || !entry.integrity.chainHash) return false;

        try {
            const expectedChainHash = crypto.createHash('sha256')
                .update(entry.integrity.previousHash + entry.integrity.hash)
                .digest('hex');

            return entry.integrity.chainHash === expectedChainHash;
        } catch (error) {
            this.logger.error('Error verifying chain integrity', {
                eventId: entry.eventId,
                error: error.message
            });
            return false;
        }
    }

    async exportAuditData(options = {}) {
        const {
            format = 'json',
            startDate,
            endDate,
            category,
            includeEncrypted = false,
            outputPath
        } = options;

        const query = { startDate, endDate, category, limit: 100000 };
        const auditData = await this.queryAuditTrail(query);

        let exportData;
        switch (format.toLowerCase()) {
            case 'json':
                exportData = JSON.stringify(auditData, null, 2);
                break;
            case 'csv':
                exportData = await this.convertToCSV(auditData.results);
                break;
            case 'xml':
                exportData = await this.convertToXML(auditData.results);
                break;
            default:
                throw new Error(`Unsupported export format: ${format}`);
        }

        if (outputPath) {
            await fs.writeFile(outputPath, exportData, { mode: 0o600 });
            this.logger.info('Audit data exported', {
                format,
                outputPath,
                recordCount: auditData.results.length
            });
        }

        return exportData;
    }

    async convertToCSV(entries) {
        if (entries.length === 0) return '';

        const headers = Object.keys(entries[0]).filter(key => key !== 'encrypted' && key !== 'integrity');
        const rows = entries.map(entry => 
            headers.map(header => {
                const value = entry[header];
                if (typeof value === 'object') return JSON.stringify(value);
                return String(value || '');
            })
        );

        return [headers, ...rows]
            .map(row => row.map(field => `"${field.replace(/"/g, '""')}"`).join(','))
            .join('\n');
    }

    async convertToXML(entries) {
        let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<AuditTrail>\n';
        
        for (const entry of entries) {
            xml += '  <AuditEntry>\n';
            for (const [key, value] of Object.entries(entry)) {
                if (key === 'encrypted' || key === 'integrity') continue;
                const xmlValue = typeof value === 'object' ? JSON.stringify(value) : String(value || '');
                xml += `    <${key}>${this.escapeXML(xmlValue)}</${key}>\n`;
            }
            xml += '  </AuditEntry>\n';
        }
        
        xml += '</AuditTrail>';
        return xml;
    }

    escapeXML(str) {
        return str.replace(/[<>&'"]/g, char => {
            switch (char) {
                case '<': return '&lt;';
                case '>': return '&gt;';
                case '&': return '&amp;';
                case "'": return '&apos;';
                case '"': return '&quot;';
                default: return char;
            }
        });
    }

    async performRetentionCleanup() {
        const currentDate = moment();
        let deletedFiles = 0;
        let deletedEntries = 0;

        try {
            const storageFiles = await fs.readdir(this.config.storageLocation);

            for (const file of storageFiles) {
                const match = file.match(/^audit-(.+)-(\d{4}-\d{2}-\d{2})\.jsonl/);
                if (!match) continue;

                const [, category, dateStr] = match;
                const fileDate = moment(dateStr);
                const retentionDays = this.config.retentionPeriods[category] || this.config.retentionPeriods.default;
                const deleteDate = currentDate.clone().subtract(retentionDays, 'days');

                if (fileDate.isBefore(deleteDate)) {
                    const filePath = path.join(this.config.storageLocation, file);
                    
                    // Count entries before deletion
                    try {
                        const data = await fs.readFile(filePath, 'utf8');
                        const entries = data.split('\n').filter(line => line.trim()).length;
                        deletedEntries += entries;
                    } catch (error) {
                        this.logger.warn('Could not count entries in expired file', { file, error: error.message });
                    }

                    await fs.unlink(filePath);
                    deletedFiles++;

                    this.logger.info('Expired audit file deleted', {
                        file,
                        category,
                        fileDate: dateStr,
                        retentionDays
                    });
                }
            }

            this.logger.info('Retention cleanup completed', {
                deletedFiles,
                deletedEntries,
                totalRetentionPolicies: Object.keys(this.config.retentionPeriods).length
            });

            return { deletedFiles, deletedEntries };

        } catch (error) {
            this.logger.error('Retention cleanup failed', { error: error.message });
            throw error;
        }
    }

    startBackgroundProcesses() {
        // Run retention cleanup daily at 2 AM
        const cleanupInterval = 24 * 60 * 60 * 1000; // 24 hours
        setInterval(() => {
            this.performRetentionCleanup().catch(error => {
                this.logger.error('Background retention cleanup failed', { error: error.message });
            });
        }, cleanupInterval);

        // Batch process pending entries every 5 minutes
        const batchInterval = 5 * 60 * 1000; // 5 minutes
        setInterval(() => {
            this.processPendingEntries().catch(error => {
                this.logger.error('Background batch processing failed', { error: error.message });
            });
        }, batchInterval);

        // Save sequence number every hour
        const sequenceInterval = 60 * 60 * 1000; // 1 hour
        setInterval(() => {
            this.saveSequenceNumber().catch(error => {
                this.logger.error('Failed to save sequence number', { error: error.message });
            });
        }, sequenceInterval);
    }

    async processPendingEntries() {
        if (this.pendingEntries.size === 0) return;

        const processedCount = this.pendingEntries.size;
        this.pendingEntries.clear();

        this.logger.debug('Processed pending audit entries', { count: processedCount });
    }

    async saveSequenceNumber() {
        const sequenceFile = path.join(this.config.storageLocation, '.sequence');
        await fs.writeFile(sequenceFile, String(this.sequenceNumber), { mode: 0o600 });
    }

    async loadSequenceNumber() {
        const sequenceFile = path.join(this.config.storageLocation, '.sequence');
        
        try {
            const data = await fs.readFile(sequenceFile, 'utf8');
            this.sequenceNumber = parseInt(data.trim()) || 0;
        } catch (error) {
            this.sequenceNumber = 0;
        }
    }

    async initializeIntegrityChain() {
        const chainFile = path.join(this.config.storageLocation, '.audit-chain');
        
        try {
            const data = await fs.readFile(chainFile, 'utf8');
            this.auditChain = JSON.parse(data);
        } catch (error) {
            this.auditChain = [];
        }
    }

    getAuditStatistics() {
        return {
            sequenceNumber: this.sequenceNumber,
            chainLength: this.auditChain.length,
            pendingEntries: this.pendingEntries.size,
            currentLogFiles: Array.from(this.currentLogFiles.keys()).length,
            supportedCategories: Object.keys(this.config.eventCategories),
            retentionPolicies: Object.keys(this.config.retentionPeriods).length,
            tamperProofingEnabled: this.config.tamperProofing.enabled
        };
    }
}

module.exports = AuditTrailManager;