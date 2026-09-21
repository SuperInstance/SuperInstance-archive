const crypto = require('crypto');
const EventEmitter = require('events');

class APIKeyVault extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            encryptionKey: config.encryptionKey || process.env.VAULT_ENCRYPTION_KEY || this.generateEncryptionKey(),
            algorithm: 'aes-256-gcm',
            keyRotationInterval: config.keyRotationInterval || 24 * 60 * 60 * 1000, // 24 hours
            auditLogging: config.auditLogging !== false,
            accessTiers: {
                free: { maxKeys: 5, keyTypes: ['basic'] },
                pro: { maxKeys: 25, keyTypes: ['basic', 'advanced'] },
                enterprise: { maxKeys: 100, keyTypes: ['basic', 'advanced', 'premium'] }
            },
            ...config
        };

        this.vault = new Map();
        this.keyMetadata = new Map();
        this.accessLog = [];
        this.rotationSchedule = new Map();

        this.initializeVault();
    }

    initializeVault() {
        this.startKeyRotationScheduler();
        this.emit('vault-initialized', {
            timestamp: new Date(),
            encryptionAlgorithm: this.config.algorithm
        });
    }

    generateEncryptionKey() {
        return crypto.randomBytes(32).toString('hex');
    }

    encrypt(data) {
        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipher(this.config.algorithm, this.config.encryptionKey);
        cipher.setAAD(Buffer.from('api-key-vault'));
        
        let encrypted = cipher.update(data, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        
        const authTag = cipher.getAuthTag();
        
        return {
            encrypted,
            iv: iv.toString('hex'),
            authTag: authTag.toString('hex')
        };
    }

    decrypt(encryptedData) {
        const decipher = crypto.createDecipher(this.config.algorithm, this.config.encryptionKey);
        decipher.setAAD(Buffer.from('api-key-vault'));
        decipher.setAuthTag(Buffer.from(encryptedData.authTag, 'hex'));
        
        let decrypted = decipher.update(encryptedData.encrypted, 'hex', 'utf8');
        decrypted += decipher.final('utf8');
        
        return decrypted;
    }

    async storeAPIKey(userId, userTier, keyConfig) {
        try {
            const tierLimits = this.config.accessTiers[userTier] || this.config.accessTiers.free;
            const userKeys = this.getUserKeys(userId);

            if (userKeys.length >= tierLimits.maxKeys) {
                throw new Error(`Key limit reached for ${userTier} tier (${tierLimits.maxKeys})`);
            }

            if (!tierLimits.keyTypes.includes(keyConfig.type)) {
                throw new Error(`Key type '${keyConfig.type}' not allowed for ${userTier} tier`);
            }

            const keyId = this.generateKeyId();
            const encryptedKey = this.encrypt(keyConfig.value);
            
            const keyData = {
                id: keyId,
                userId,
                name: keyConfig.name,
                type: keyConfig.type,
                service: keyConfig.service,
                encrypted: encryptedKey,
                created: new Date(),
                lastAccessed: null,
                rotationEnabled: keyConfig.rotationEnabled || false,
                rotationInterval: keyConfig.rotationInterval || this.config.keyRotationInterval,
                permissions: keyConfig.permissions || ['read'],
                environment: keyConfig.environment || 'development',
                tags: keyConfig.tags || []
            };

            this.vault.set(keyId, keyData);
            this.keyMetadata.set(keyId, {
                accessCount: 0,
                lastRotation: new Date(),
                status: 'active'
            });

            if (keyData.rotationEnabled) {
                this.scheduleKeyRotation(keyId, keyData.rotationInterval);
            }

            this.logAccess(userId, 'store', keyId, 'success');
            this.emit('key-stored', { userId, keyId, service: keyConfig.service });

            return {
                keyId,
                name: keyConfig.name,
                service: keyConfig.service,
                created: keyData.created
            };
        } catch (error) {
            this.logAccess(userId, 'store', null, 'error', error.message);
            throw error;
        }
    }

    async retrieveAPIKey(userId, keyId, context = {}) {
        try {
            const keyData = this.vault.get(keyId);
            if (!keyData) {
                throw new Error('API key not found');
            }

            if (keyData.userId !== userId) {
                throw new Error('Access denied: Key belongs to different user');
            }

            if (!this.hasPermission(keyData, context.operation || 'read')) {
                throw new Error('Insufficient permissions for this operation');
            }

            const decryptedValue = this.decrypt(keyData.encrypted);
            
            keyData.lastAccessed = new Date();
            const metadata = this.keyMetadata.get(keyId);
            metadata.accessCount++;

            this.logAccess(userId, 'retrieve', keyId, 'success');
            this.emit('key-accessed', { userId, keyId, operation: context.operation });

            return {
                id: keyId,
                name: keyData.name,
                value: decryptedValue,
                service: keyData.service,
                type: keyData.type,
                environment: keyData.environment,
                permissions: keyData.permissions,
                lastAccessed: keyData.lastAccessed
            };
        } catch (error) {
            this.logAccess(userId, 'retrieve', keyId, 'error', error.message);
            throw error;
        }
    }

    async updateAPIKey(userId, keyId, updates) {
        try {
            const keyData = this.vault.get(keyId);
            if (!keyData || keyData.userId !== userId) {
                throw new Error('API key not found or access denied');
            }

            const allowedUpdates = ['name', 'permissions', 'tags', 'rotationEnabled', 'rotationInterval'];
            const filteredUpdates = Object.keys(updates)
                .filter(key => allowedUpdates.includes(key))
                .reduce((obj, key) => {
                    obj[key] = updates[key];
                    return obj;
                }, {});

            if (updates.value) {
                filteredUpdates.encrypted = this.encrypt(updates.value);
            }

            Object.assign(keyData, filteredUpdates, { lastModified: new Date() });

            if (updates.rotationEnabled !== undefined) {
                if (updates.rotationEnabled) {
                    this.scheduleKeyRotation(keyId, updates.rotationInterval || keyData.rotationInterval);
                } else {
                    this.cancelKeyRotation(keyId);
                }
            }

            this.logAccess(userId, 'update', keyId, 'success');
            this.emit('key-updated', { userId, keyId, updates: Object.keys(filteredUpdates) });

            return { success: true, updated: Object.keys(filteredUpdates) };
        } catch (error) {
            this.logAccess(userId, 'update', keyId, 'error', error.message);
            throw error;
        }
    }

    async deleteAPIKey(userId, keyId) {
        try {
            const keyData = this.vault.get(keyId);
            if (!keyData || keyData.userId !== userId) {
                throw new Error('API key not found or access denied');
            }

            this.vault.delete(keyId);
            this.keyMetadata.delete(keyId);
            this.cancelKeyRotation(keyId);

            this.logAccess(userId, 'delete', keyId, 'success');
            this.emit('key-deleted', { userId, keyId, service: keyData.service });

            return { success: true, keyId };
        } catch (error) {
            this.logAccess(userId, 'delete', keyId, 'error', error.message);
            throw error;
        }
    }

    getUserKeys(userId) {
        return Array.from(this.vault.values())
            .filter(key => key.userId === userId)
            .map(key => ({
                id: key.id,
                name: key.name,
                service: key.service,
                type: key.type,
                environment: key.environment,
                created: key.created,
                lastAccessed: key.lastAccessed,
                rotationEnabled: key.rotationEnabled,
                status: this.keyMetadata.get(key.id)?.status || 'unknown'
            }));
    }

    async rotateAPIKey(keyId) {
        try {
            const keyData = this.vault.get(keyId);
            if (!keyData) {
                throw new Error('API key not found for rotation');
            }

            const newValue = this.generateNewKeyValue(keyData.service, keyData.type);
            const encryptedNewValue = this.encrypt(newValue);

            const oldEncrypted = keyData.encrypted;
            keyData.encrypted = encryptedNewValue;
            keyData.lastRotated = new Date();

            const metadata = this.keyMetadata.get(keyId);
            metadata.lastRotation = new Date();
            metadata.rotationCount = (metadata.rotationCount || 0) + 1;

            this.emit('key-rotated', {
                userId: keyData.userId,
                keyId,
                service: keyData.service,
                timestamp: new Date()
            });

            this.logAccess(keyData.userId, 'rotate', keyId, 'success');

            return {
                keyId,
                newValue,
                rotatedAt: keyData.lastRotated
            };
        } catch (error) {
            this.emit('key-rotation-failed', { keyId, error: error.message });
            throw error;
        }
    }

    generateNewKeyValue(service, type) {
        const prefixes = {
            'github': 'ghp_',
            'openai': 'sk-',
            'aws': 'AKIA',
            'stripe': 'sk_',
            'basic': 'key_',
            'advanced': 'adv_',
            'premium': 'prem_'
        };

        const prefix = prefixes[service] || prefixes[type] || 'api_';
        const randomPart = crypto.randomBytes(32).toString('hex').substring(0, 40);
        
        return `${prefix}${randomPart}`;
    }

    scheduleKeyRotation(keyId, interval) {
        if (this.rotationSchedule.has(keyId)) {
            clearInterval(this.rotationSchedule.get(keyId));
        }

        const rotationTimer = setInterval(async () => {
            try {
                await this.rotateAPIKey(keyId);
            } catch (error) {
                console.error(`Failed to rotate key ${keyId}:`, error);
            }
        }, interval);

        this.rotationSchedule.set(keyId, rotationTimer);
    }

    cancelKeyRotation(keyId) {
        if (this.rotationSchedule.has(keyId)) {
            clearInterval(this.rotationSchedule.get(keyId));
            this.rotationSchedule.delete(keyId);
        }
    }

    startKeyRotationScheduler() {
        setInterval(() => {
            const now = new Date();
            for (const [keyId, keyData] of this.vault.entries()) {
                if (keyData.rotationEnabled) {
                    const metadata = this.keyMetadata.get(keyId);
                    const timeSinceLastRotation = now - metadata.lastRotation;
                    
                    if (timeSinceLastRotation >= keyData.rotationInterval) {
                        this.rotateAPIKey(keyId).catch(console.error);
                    }
                }
            }
        }, 60000); // Check every minute
    }

    hasPermission(keyData, operation) {
        const operationMap = {
            'read': ['read', 'write', 'admin'],
            'write': ['write', 'admin'],
            'delete': ['admin'],
            'rotate': ['admin']
        };

        const allowedRoles = operationMap[operation] || ['admin'];
        return keyData.permissions.some(perm => allowedRoles.includes(perm));
    }

    generateKeyId() {
        return `key_${crypto.randomBytes(16).toString('hex')}`;
    }

    logAccess(userId, operation, keyId, status, error = null) {
        if (!this.config.auditLogging) return;

        const logEntry = {
            timestamp: new Date(),
            userId,
            operation,
            keyId,
            status,
            error,
            ip: null, // Would be populated by middleware
            userAgent: null // Would be populated by middleware
        };

        this.accessLog.push(logEntry);

        // Keep only last 10000 log entries
        if (this.accessLog.length > 10000) {
            this.accessLog.splice(0, this.accessLog.length - 10000);
        }

        this.emit('access-logged', logEntry);
    }

    getAuditLog(userId, filters = {}) {
        return this.accessLog
            .filter(entry => {
                if (filters.userId && entry.userId !== filters.userId) return false;
                if (filters.operation && entry.operation !== filters.operation) return false;
                if (filters.keyId && entry.keyId !== filters.keyId) return false;
                if (filters.status && entry.status !== filters.status) return false;
                if (filters.startDate && entry.timestamp < filters.startDate) return false;
                if (filters.endDate && entry.timestamp > filters.endDate) return false;
                return true;
            })
            .slice(0, filters.limit || 100);
    }

    getVaultStatistics() {
        const totalKeys = this.vault.size;
        const keysByService = {};
        const keysByType = {};
        const keysByUser = {};

        for (const keyData of this.vault.values()) {
            keysByService[keyData.service] = (keysByService[keyData.service] || 0) + 1;
            keysByType[keyData.type] = (keysByType[keyData.type] || 0) + 1;
            keysByUser[keyData.userId] = (keysByUser[keyData.userId] || 0) + 1;
        }

        const rotationStats = {
            enabled: Array.from(this.vault.values()).filter(k => k.rotationEnabled).length,
            scheduled: this.rotationSchedule.size
        };

        return {
            totalKeys,
            keysByService,
            keysByType,
            keysByUser,
            rotationStats,
            totalAccesses: this.accessLog.length
        };
    }

    async exportKeys(userId, format = 'json') {
        const userKeys = this.getUserKeys(userId);
        
        if (format === 'json') {
            return JSON.stringify(userKeys, null, 2);
        } else if (format === 'csv') {
            const headers = 'ID,Name,Service,Type,Environment,Created,LastAccessed,Status\n';
            const rows = userKeys.map(key => 
                `${key.id},${key.name},${key.service},${key.type},${key.environment},${key.created},${key.lastAccessed || 'Never'},${key.status}`
            ).join('\n');
            return headers + rows;
        }

        throw new Error('Unsupported export format');
    }

    async importKeys(userId, userTier, keysData, format = 'json') {
        let keys;
        
        if (format === 'json') {
            keys = JSON.parse(keysData);
        } else {
            throw new Error('Unsupported import format');
        }

        const results = [];
        for (const keyConfig of keys) {
            try {
                const result = await this.storeAPIKey(userId, userTier, keyConfig);
                results.push({ success: true, ...result });
            } catch (error) {
                results.push({ success: false, error: error.message, name: keyConfig.name });
            }
        }

        return results;
    }

    shutdown() {
        for (const timer of this.rotationSchedule.values()) {
            clearInterval(timer);
        }
        this.rotationSchedule.clear();
        this.emit('vault-shutdown', { timestamp: new Date() });
    }
}

module.exports = APIKeyVault;