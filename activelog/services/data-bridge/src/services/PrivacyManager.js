const { EventEmitter } = require('events');
const crypto = require('crypto');

class PrivacyManager extends EventEmitter {
    constructor(options = {}) {
        super();
        this.policies = new Map();
        this.dataClassifications = new Map();
        this.consentRecords = new Map();
        this.accessLogs = [];
        this.anonymizers = new Map();
        this.encryptionKeys = new Map();
        this.auditTrail = [];
        
        this.defaultClassification = options.defaultClassification || 'internal';
        this.encryptionAlgorithm = options.encryptionAlgorithm || 'aes-256-gcm';
        this.maxAuditEntries = options.maxAuditEntries || 10000;
        
        this.initializeDataClassifications();
        this.initializeAnonymizers();
        this.setupEventHandlers();
    }

    initializeDataClassifications() {
        // Define standard data classification levels
        this.registerClassification('public', {
            level: 1,
            description: 'Public information with no access restrictions',
            shareableWith: ['*'],
            encryptionRequired: false,
            anonymizationRequired: false,
            retentionPeriod: null
        });

        this.registerClassification('internal', {
            level: 2,
            description: 'Internal information for organization members',
            shareableWith: ['internal-users'],
            encryptionRequired: false,
            anonymizationRequired: false,
            retentionPeriod: 86400000 * 365 * 7 // 7 years
        });

        this.registerClassification('confidential', {
            level: 3,
            description: 'Confidential information with restricted access',
            shareableWith: ['authorized-users'],
            encryptionRequired: true,
            anonymizationRequired: false,
            retentionPeriod: 86400000 * 365 * 5 // 5 years
        });

        this.registerClassification('restricted', {
            level: 4,
            description: 'Highly sensitive information with minimal access',
            shareableWith: ['admin-users'],
            encryptionRequired: true,
            anonymizationRequired: true,
            retentionPeriod: 86400000 * 365 * 3 // 3 years
        });

        this.registerClassification('personal', {
            level: 5,
            description: 'Personal data subject to privacy regulations',
            shareableWith: ['data-owner', 'authorized-processors'],
            encryptionRequired: true,
            anonymizationRequired: true,
            retentionPeriod: 86400000 * 365 * 2, // 2 years
            requiresConsent: true,
            gdprCompliant: true
        });
    }

    initializeAnonymizers() {
        // Hash anonymizer
        this.registerAnonymizer('hash', (value, options = {}) => {
            const salt = options.salt || '';
            return crypto.createHash('sha256').update(value + salt).digest('hex').substring(0, 8);
        });

        // Mask anonymizer
        this.registerAnonymizer('mask', (value, options = {}) => {
            const maskChar = options.maskChar || '*';
            const visibleChars = options.visibleChars || 2;
            
            if (typeof value !== 'string' || value.length <= visibleChars * 2) {
                return maskChar.repeat(value.length || 4);
            }
            
            const start = value.substring(0, visibleChars);
            const end = value.substring(value.length - visibleChars);
            const middle = maskChar.repeat(value.length - visibleChars * 2);
            
            return start + middle + end;
        });

        // Generalize anonymizer
        this.registerAnonymizer('generalize', (value, options = {}) => {
            if (typeof value === 'number') {
                const range = options.range || 10;
                return Math.floor(value / range) * range;
            }
            
            if (value instanceof Date) {
                return new Date(value.getFullYear(), value.getMonth(), 1);
            }
            
            return '[GENERALIZED]';
        });

        // Remove anonymizer
        this.registerAnonymizer('remove', () => '[REMOVED]');

        // Fake data anonymizer
        this.registerAnonymizer('fake', (value, options = {}) => {
            switch (options.type) {
                case 'email':
                    return `user${Math.random().toString(36).substring(2, 8)}@example.com`;
                case 'name':
                    const names = ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown'];
                    return names[Math.floor(Math.random() * names.length)];
                case 'phone':
                    return `555-${Math.floor(Math.random() * 900) + 100}-${Math.floor(Math.random() * 9000) + 1000}`;
                case 'ssn':
                    return `XXX-XX-${Math.floor(Math.random() * 9000) + 1000}`;
                default:
                    return '[FAKE_DATA]';
            }
        });
    }

    registerClassification(name, config) {
        const classification = {
            name,
            level: config.level,
            description: config.description,
            shareableWith: config.shareableWith || [],
            encryptionRequired: config.encryptionRequired || false,
            anonymizationRequired: config.anonymizationRequired || false,
            retentionPeriod: config.retentionPeriod,
            requiresConsent: config.requiresConsent || false,
            gdprCompliant: config.gdprCompliant || false,
            complianceRules: config.complianceRules || [],
            createdAt: new Date()
        };

        this.dataClassifications.set(name, classification);
        this.emit('classification:registered', classification);
        return classification;
    }

    registerAnonymizer(name, anonymizerFn) {
        this.anonymizers.set(name, anonymizerFn);
        this.emit('anonymizer:registered', { name, anonymizerFn });
        return this;
    }

    createPrivacyPolicy(policyId, config) {
        const policy = {
            id: policyId,
            name: config.name || policyId,
            description: config.description,
            dataTypes: config.dataTypes || [],
            classification: config.classification || this.defaultClassification,
            allowedPurposes: config.allowedPurposes || [],
            allowedRecipients: config.allowedRecipients || [],
            retentionPeriod: config.retentionPeriod,
            anonymizationRules: config.anonymizationRules || {},
            encryptionRequired: config.encryptionRequired || false,
            consentRequired: config.consentRequired || false,
            crossBorderTransfer: config.crossBorderTransfer || false,
            accessControls: config.accessControls || [],
            auditRequired: config.auditRequired !== false,
            createdAt: new Date(),
            updatedAt: new Date(),
            version: '1.0.0'
        };

        this.policies.set(policyId, policy);
        this.emit('policy:created', policy);
        return policy;
    }

    async processDataSharing(data, sourceApp, targetApp, options = {}) {
        const sharingId = crypto.randomUUID();
        const sharingInfo = {
            id: sharingId,
            sourceApp,
            targetApp,
            dataSize: this.calculateDataSize(data),
            requestedBy: options.userId,
            purpose: options.purpose,
            startTime: new Date()
        };

        this.emit('sharing:started', sharingInfo);

        try {
            // 1. Classify the data
            const classification = await this.classifyData(data, options);
            sharingInfo.classification = classification.name;

            // 2. Check sharing permissions
            await this.validateSharingPermission(data, sourceApp, targetApp, classification, options);

            // 3. Check consent if required
            if (classification.requiresConsent) {
                await this.validateConsent(data, options.purpose, options.userId);
            }

            // 4. Apply anonymization if required
            let processedData = data;
            if (classification.anonymizationRequired || options.forceAnonymize) {
                processedData = await this.anonymizeData(data, classification, options);
                sharingInfo.anonymized = true;
            }

            // 5. Apply encryption if required
            if (classification.encryptionRequired || options.forceEncrypt) {
                processedData = await this.encryptData(processedData, targetApp, options);
                sharingInfo.encrypted = true;
            }

            // 6. Log the access
            this.logDataAccess({
                sharingId,
                sourceApp,
                targetApp,
                dataType: data.type,
                userId: options.userId,
                purpose: options.purpose,
                classification: classification.name,
                success: true
            });

            sharingInfo.endTime = new Date();
            sharingInfo.success = true;
            sharingInfo.resultSize = this.calculateDataSize(processedData);

            this.emit('sharing:completed', sharingInfo);
            return {
                data: processedData,
                metadata: {
                    sharingId,
                    classification: classification.name,
                    anonymized: sharingInfo.anonymized || false,
                    encrypted: sharingInfo.encrypted || false,
                    processedAt: new Date()
                }
            };

        } catch (error) {
            sharingInfo.endTime = new Date();
            sharingInfo.success = false;
            sharingInfo.error = error.message;

            this.logDataAccess({
                sharingId,
                sourceApp,
                targetApp,
                dataType: data.type,
                userId: options.userId,
                purpose: options.purpose,
                success: false,
                error: error.message
            });

            this.emit('sharing:failed', sharingInfo);
            throw error;
        }
    }

    async classifyData(data, options = {}) {
        // Use explicit classification if provided
        if (options.classification) {
            const classification = this.dataClassifications.get(options.classification);
            if (classification) {
                return classification;
            }
        }

        // Auto-classify based on data content
        const autoClassification = this.autoClassifyData(data);
        return this.dataClassifications.get(autoClassification) || 
               this.dataClassifications.get(this.defaultClassification);
    }

    autoClassifyData(data) {
        const content = JSON.stringify(data).toLowerCase();
        
        // Check for personal data indicators
        const personalIndicators = [
            'email', 'phone', 'ssn', 'social security', 'passport', 'driver license',
            'credit card', 'bank account', 'medical', 'health', 'biometric'
        ];
        
        if (personalIndicators.some(indicator => content.includes(indicator))) {
            return 'personal';
        }

        // Check for confidential data indicators
        const confidentialIndicators = [
            'password', 'secret', 'key', 'token', 'confidential', 'proprietary',
            'salary', 'compensation', 'financial', 'revenue'
        ];
        
        if (confidentialIndicators.some(indicator => content.includes(indicator))) {
            return 'confidential';
        }

        // Check for restricted data indicators
        const restrictedIndicators = [
            'top secret', 'classified', 'restricted', 'national security'
        ];
        
        if (restrictedIndicators.some(indicator => content.includes(indicator))) {
            return 'restricted';
        }

        return this.defaultClassification;
    }

    async validateSharingPermission(data, sourceApp, targetApp, classification, options) {
        // Check if target app is in allowed recipients
        const allowedRecipients = classification.shareableWith;
        
        if (!allowedRecipients.includes('*') && 
            !allowedRecipients.includes(targetApp) &&
            !allowedRecipients.includes(options.userRole)) {
            throw new Error(`Data sharing not allowed: ${targetApp} not in allowed recipients`);
        }

        // Check cross-border transfer restrictions
        if (options.crossBorder && !this.isCrossBorderAllowed(classification, options)) {
            throw new Error('Cross-border data transfer not allowed for this classification');
        }

        // Check purpose limitation
        const policy = this.findApplicablePolicy(data, sourceApp, targetApp);
        if (policy && policy.allowedPurposes.length > 0) {
            if (!policy.allowedPurposes.includes(options.purpose)) {
                throw new Error(`Purpose '${options.purpose}' not allowed by privacy policy`);
            }
        }

        return true;
    }

    async validateConsent(data, purpose, userId) {
        const consentKey = this.generateConsentKey(data, purpose, userId);
        const consent = this.consentRecords.get(consentKey);
        
        if (!consent) {
            throw new Error('No consent record found for data processing');
        }

        if (consent.status !== 'granted') {
            throw new Error(`Consent status is '${consent.status}', not 'granted'`);
        }

        if (consent.expiresAt && new Date() > consent.expiresAt) {
            throw new Error('Consent has expired');
        }

        if (consent.purposes && !consent.purposes.includes(purpose)) {
            throw new Error(`Purpose '${purpose}' not covered by consent`);
        }

        return true;
    }

    async anonymizeData(data, classification, options = {}) {
        const anonymized = { ...data };
        const rules = options.anonymizationRules || this.getDefaultAnonymizationRules(classification);

        for (const [field, rule] of Object.entries(rules)) {
            if (anonymized[field] !== undefined) {
                anonymized[field] = await this.applyAnonymization(anonymized[field], rule);
            }
        }

        // Apply nested field anonymization
        if (rules._nested) {
            for (const [path, rule] of Object.entries(rules._nested)) {
                const value = this.getNestedValue(anonymized, path);
                if (value !== undefined) {
                    this.setNestedValue(anonymized, path, await this.applyAnonymization(value, rule));
                }
            }
        }

        return anonymized;
    }

    async applyAnonymization(value, rule) {
        if (typeof rule === 'string') {
            const anonymizer = this.anonymizers.get(rule);
            if (!anonymizer) {
                throw new Error(`Unknown anonymizer: ${rule}`);
            }
            return anonymizer(value);
        }

        if (typeof rule === 'object') {
            const { method, ...options } = rule;
            const anonymizer = this.anonymizers.get(method);
            if (!anonymizer) {
                throw new Error(`Unknown anonymizer: ${method}`);
            }
            return anonymizer(value, options);
        }

        return value;
    }

    getDefaultAnonymizationRules(classification) {
        const rules = {};

        switch (classification.name) {
            case 'personal':
                rules.email = 'hash';
                rules.phone = 'mask';
                rules.ssn = 'mask';
                rules.name = 'fake';
                rules.address = 'generalize';
                break;
            case 'restricted':
                rules.email = 'hash';
                rules.phone = 'remove';
                rules.ssn = 'remove';
                rules.name = 'remove';
                rules.salary = 'generalize';
                break;
        }

        return rules;
    }

    async encryptData(data, targetApp, options = {}) {
        const key = await this.getEncryptionKey(targetApp);
        const algorithm = options.algorithm || this.encryptionAlgorithm;
        
        const dataString = JSON.stringify(data);
        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipher(algorithm, key);
        
        let encrypted = cipher.update(dataString, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        
        return {
            encrypted: true,
            algorithm,
            iv: iv.toString('hex'),
            data: encrypted,
            metadata: {
                encryptedAt: new Date(),
                encryptedFor: targetApp
            }
        };
    }

    async getEncryptionKey(targetApp) {
        let key = this.encryptionKeys.get(targetApp);
        
        if (!key) {
            key = crypto.randomBytes(32).toString('hex');
            this.encryptionKeys.set(targetApp, key);
        }
        
        return key;
    }

    recordConsent(userId, dataType, purposes, options = {}) {
        const consentId = crypto.randomUUID();
        const consent = {
            id: consentId,
            userId,
            dataType,
            purposes: Array.isArray(purposes) ? purposes : [purposes],
            status: 'granted',
            grantedAt: new Date(),
            expiresAt: options.expiresAt,
            withdrawableAfter: options.withdrawableAfter,
            legalBasis: options.legalBasis || 'consent',
            processingDetails: options.processingDetails,
            metadata: options.metadata || {}
        };

        const consentKey = this.generateConsentKey({ type: dataType }, purposes[0], userId);
        this.consentRecords.set(consentKey, consent);

        this.emit('consent:granted', consent);
        return consent;
    }

    withdrawConsent(userId, dataType, purpose) {
        const consentKey = this.generateConsentKey({ type: dataType }, purpose, userId);
        const consent = this.consentRecords.get(consentKey);

        if (consent) {
            consent.status = 'withdrawn';
            consent.withdrawnAt = new Date();
            this.emit('consent:withdrawn', consent);
        }

        return consent;
    }

    generateConsentKey(data, purpose, userId) {
        return crypto
            .createHash('sha256')
            .update(`${userId}:${data.type}:${purpose}`)
            .digest('hex');
    }

    logDataAccess(accessInfo) {
        const log = {
            id: crypto.randomUUID(),
            timestamp: new Date(),
            ...accessInfo
        };

        this.accessLogs.push(log);
        this.auditTrail.push({
            event: 'data_access',
            details: log
        });

        // Trim audit trail if it gets too large
        if (this.auditTrail.length > this.maxAuditEntries) {
            this.auditTrail.splice(0, this.auditTrail.length - this.maxAuditEntries);
        }

        this.emit('access:logged', log);
    }

    findApplicablePolicy(data, sourceApp, targetApp) {
        for (const [policyId, policy] of this.policies) {
            if (policy.dataTypes.length === 0 || policy.dataTypes.includes(data.type)) {
                return policy;
            }
        }
        return null;
    }

    isCrossBorderAllowed(classification, options) {
        // Simplified cross-border transfer validation
        if (classification.name === 'personal' && !options.adequacyDecision) {
            return false;
        }
        return true;
    }

    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => current?.[key], obj);
    }

    setNestedValue(obj, path, value) {
        const keys = path.split('.');
        let current = obj;
        
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i];
            if (!current[key] || typeof current[key] !== 'object') {
                current[key] = {};
            }
            current = current[key];
        }
        
        current[keys[keys.length - 1]] = value;
    }

    calculateDataSize(data) {
        return Buffer.byteLength(JSON.stringify(data), 'utf8');
    }

    setupEventHandlers() {
        this.on('sharing:completed', (info) => {
            console.log(`Data sharing completed: ${info.sourceApp} -> ${info.targetApp} (${info.classification})`);
        });

        this.on('sharing:failed', (info) => {
            console.error(`Data sharing failed: ${info.sourceApp} -> ${info.targetApp} - ${info.error}`);
        });

        this.on('consent:withdrawn', (consent) => {
            console.log(`Consent withdrawn: ${consent.userId} for ${consent.dataType}`);
        });
    }

    getPrivacyReport() {
        const report = {
            policies: this.policies.size,
            classifications: this.dataClassifications.size,
            consents: this.consentRecords.size,
            accessLogs: this.accessLogs.length,
            auditEntries: this.auditTrail.length,
            anonymizers: this.anonymizers.size,
            encryptionKeys: this.encryptionKeys.size,
            recentActivity: this.accessLogs
                .slice(-10)
                .map(log => ({
                    timestamp: log.timestamp,
                    sourceApp: log.sourceApp,
                    targetApp: log.targetApp,
                    success: log.success
                }))
        };

        return report;
    }

    getDataClassifications() {
        return Array.from(this.dataClassifications.values());
    }

    getPolicies() {
        return Array.from(this.policies.values());
    }

    getConsentRecords(userId) {
        const userConsents = [];
        for (const [key, consent] of this.consentRecords) {
            if (!userId || consent.userId === userId) {
                userConsents.push(consent);
            }
        }
        return userConsents;
    }

    getAccessLogs(filters = {}) {
        let logs = [...this.accessLogs];

        if (filters.userId) {
            logs = logs.filter(log => log.userId === filters.userId);
        }

        if (filters.sourceApp) {
            logs = logs.filter(log => log.sourceApp === filters.sourceApp);
        }

        if (filters.targetApp) {
            logs = logs.filter(log => log.targetApp === filters.targetApp);
        }

        if (filters.since) {
            const since = new Date(filters.since);
            logs = logs.filter(log => log.timestamp >= since);
        }

        return logs.sort((a, b) => b.timestamp - a.timestamp);
    }

    reset() {
        this.policies.clear();
        this.consentRecords.clear();
        this.encryptionKeys.clear();
        this.accessLogs.length = 0;
        this.auditTrail.length = 0;
        this.initializeDataClassifications();
        this.emit('reset');
    }
}

module.exports = PrivacyManager;