const crypto = require('crypto');
const fs = require('fs').promises;
const path = require('path');
const winston = require('winston');
const argon2 = require('argon2');
const forge = require('node-forge');

class EmbassySecurityManager {
    constructor(options = {}) {
        this.config = {
            securityLevel: options.securityLevel || 'embassy-grade',
            encryptionAlgorithm: 'aes-256-gcm',
            keyDerivationFunction: 'PBKDF2-SHA512',
            keyStretchingIterations: 600000,
            saltLength: 32,
            ivLength: 16,
            tagLength: 16,
            maxSessionDuration: options.maxSessionDuration || 3600000, // 1 hour
            maxFailedAttempts: options.maxFailedAttempts || 3,
            lockoutDuration: options.lockoutDuration || 900000, // 15 minutes
            passwordComplexity: {
                minLength: 14,
                requireUppercase: true,
                requireLowercase: true,
                requireNumbers: true,
                requireSpecialChars: true,
                minUniqueChars: 8,
                forbiddenPatterns: ['123', 'abc', 'password', 'admin']
            },
            networkSecurity: {
                allowedCIDR: options.allowedCIDR || ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'],
                blockedPorts: [22, 23, 135, 139, 445, 1433, 3389],
                requireTLS: true,
                minTLSVersion: '1.3',
                allowedCiphers: [
                    'ECDHE-ECDSA-AES256-GCM-SHA384',
                    'ECDHE-RSA-AES256-GCM-SHA384',
                    'ECDHE-ECDSA-CHACHA20-POLY1305',
                    'ECDHE-RSA-CHACHA20-POLY1305'
                ]
            },
            physicalSecurity: {
                requireSmartCard: options.requireSmartCard || false,
                requireBiometric: options.requireBiometric || false,
                temperTamperProtection: true,
                secureBootRequired: true
            }
        };

        this.logger = winston.createLogger({
            level: 'debug',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json()
            ),
            defaultMeta: { service: 'embassy-security' },
            transports: [
                new winston.transports.File({
                    filename: 'logs/embassy-security-error.log',
                    level: 'error'
                }),
                new winston.transports.File({
                    filename: 'logs/embassy-security.log'
                })
            ]
        });

        this.activeThreats = new Map();
        this.securityMetrics = {
            totalSecurityEvents: 0,
            blockedAttacks: 0,
            cryptographicOperations: 0,
            securityViolations: 0,
            intrusionAttempts: 0
        };

        this.initializeCryptoSystem();
    }

    async initializeCryptoSystem() {
        // Generate master encryption keys if they don't exist
        try {
            await this.generateMasterKeys();
            await this.initializeHSM();
            this.logger.info('Embassy-grade cryptographic system initialized');
        } catch (error) {
            this.logger.error('Failed to initialize crypto system', { error: error.message });
            throw error;
        }
    }

    async generateMasterKeys() {
        const keysPath = path.join(process.cwd(), 'keys');
        
        try {
            await fs.access(keysPath);
        } catch {
            await fs.mkdir(keysPath, { mode: 0o700, recursive: true });
        }

        // Check if master key exists
        const masterKeyPath = path.join(keysPath, 'master.key');
        try {
            await fs.access(masterKeyPath);
            this.masterKey = await fs.readFile(masterKeyPath);
        } catch {
            // Generate new master key
            this.masterKey = crypto.randomBytes(32);
            await fs.writeFile(masterKeyPath, this.masterKey, { mode: 0o600 });
            this.logger.info('New master encryption key generated');
        }

        // Generate key encryption key (KEK)
        this.keyEncryptionKey = crypto.pbkdf2Sync(
            this.masterKey,
            'embassy-kek-salt',
            this.config.keyStretchingIterations,
            32,
            'sha512'
        );

        // Generate integrity key
        this.integrityKey = crypto.pbkdf2Sync(
            this.masterKey,
            'embassy-hmac-salt',
            this.config.keyStretchingIterations,
            32,
            'sha512'
        );
    }

    async initializeHSM() {
        // Simulate Hardware Security Module initialization
        // In a real implementation, this would connect to actual HSM
        this.hsmAvailable = process.env.HSM_AVAILABLE === 'true';
        
        if (this.hsmAvailable) {
            this.logger.info('HSM detected and initialized');
        } else {
            this.logger.warn('No HSM available, using software cryptography');
        }
    }

    async encryptSensitiveData(data, dataClassification = 'confidential') {
        try {
            this.securityMetrics.cryptographicOperations++;

            const plaintext = Buffer.from(JSON.stringify(data));
            const salt = crypto.randomBytes(this.config.saltLength);
            const iv = crypto.randomBytes(this.config.ivLength);

            // Derive encryption key based on classification level
            const encryptionKey = await this.deriveEncryptionKey(salt, dataClassification);

            // Encrypt data
            const cipher = crypto.createCipher(this.config.encryptionAlgorithm, encryptionKey, { iv });
            const encrypted = Buffer.concat([cipher.update(plaintext), cipher.final()]);
            const tag = cipher.getAuthTag();

            // Create integrity MAC
            const mac = this.createIntegrityMac(encrypted, salt, iv, tag);

            const result = {
                algorithm: this.config.encryptionAlgorithm,
                classification: dataClassification,
                salt: salt.toString('hex'),
                iv: iv.toString('hex'),
                tag: tag.toString('hex'),
                mac: mac,
                encrypted: encrypted.toString('hex'),
                timestamp: Date.now()
            };

            this.logger.debug('Data encrypted', {
                classification: dataClassification,
                size: plaintext.length,
                algorithm: this.config.encryptionAlgorithm
            });

            return result;
        } catch (error) {
            this.logger.error('Encryption failed', { error: error.message });
            throw new Error('Embassy-grade encryption failed');
        }
    }

    async decryptSensitiveData(encryptedData, requiredClassification = null) {
        try {
            this.securityMetrics.cryptographicOperations++;

            if (requiredClassification && encryptedData.classification !== requiredClassification) {
                throw new Error(`Data classification mismatch: expected ${requiredClassification}, got ${encryptedData.classification}`);
            }

            const salt = Buffer.from(encryptedData.salt, 'hex');
            const iv = Buffer.from(encryptedData.iv, 'hex');
            const tag = Buffer.from(encryptedData.tag, 'hex');
            const encrypted = Buffer.from(encryptedData.encrypted, 'hex');

            // Verify integrity MAC
            const expectedMac = this.createIntegrityMac(encrypted, salt, iv, tag);
            if (!crypto.timingSafeEqual(Buffer.from(expectedMac, 'hex'), Buffer.from(encryptedData.mac, 'hex'))) {
                this.securityMetrics.securityViolations++;
                throw new Error('Data integrity check failed - possible tampering detected');
            }

            // Derive decryption key
            const decryptionKey = await this.deriveEncryptionKey(salt, encryptedData.classification);

            // Decrypt data
            const decipher = crypto.createDecipher(this.config.encryptionAlgorithm, decryptionKey, { iv });
            decipher.setAuthTag(tag);
            const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);

            this.logger.debug('Data decrypted', {
                classification: encryptedData.classification,
                size: decrypted.length
            });

            return JSON.parse(decrypted.toString());
        } catch (error) {
            this.logger.error('Decryption failed', { error: error.message });
            throw new Error('Embassy-grade decryption failed');
        }
    }

    async deriveEncryptionKey(salt, classification) {
        const classificationSeeds = {
            'public': 'public-data-seed',
            'internal': 'internal-data-seed',
            'confidential': 'confidential-data-seed',
            'restricted': 'restricted-data-seed',
            'top-secret': 'top-secret-data-seed'
        };

        const seed = classificationSeeds[classification] || classificationSeeds['internal'];
        
        return crypto.pbkdf2Sync(
            this.keyEncryptionKey,
            Buffer.concat([salt, Buffer.from(seed)]),
            this.config.keyStretchingIterations,
            32,
            'sha512'
        );
    }

    createIntegrityMac(encrypted, salt, iv, tag) {
        const hmac = crypto.createHmac('sha512', this.integrityKey);
        hmac.update(encrypted);
        hmac.update(salt);
        hmac.update(iv);
        hmac.update(tag);
        return hmac.digest('hex');
    }

    async validatePasswordComplexity(password) {
        const rules = this.config.passwordComplexity;
        const violations = [];

        if (password.length < rules.minLength) {
            violations.push(`Password must be at least ${rules.minLength} characters`);
        }

        if (rules.requireUppercase && !/[A-Z]/.test(password)) {
            violations.push('Password must contain uppercase letters');
        }

        if (rules.requireLowercase && !/[a-z]/.test(password)) {
            violations.push('Password must contain lowercase letters');
        }

        if (rules.requireNumbers && !/[0-9]/.test(password)) {
            violations.push('Password must contain numbers');
        }

        if (rules.requireSpecialChars && !/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\?]/.test(password)) {
            violations.push('Password must contain special characters');
        }

        const uniqueChars = new Set(password.toLowerCase()).size;
        if (uniqueChars < rules.minUniqueChars) {
            violations.push(`Password must contain at least ${rules.minUniqueChars} unique characters`);
        }

        for (const pattern of rules.forbiddenPatterns) {
            if (password.toLowerCase().includes(pattern)) {
                violations.push(`Password cannot contain common patterns like "${pattern}"`);
            }
        }

        // Check for keyboard patterns
        const keyboardPatterns = ['qwerty', 'asdf', '1234', 'abcd'];
        for (const pattern of keyboardPatterns) {
            if (password.toLowerCase().includes(pattern)) {
                violations.push('Password cannot contain keyboard patterns');
                break;
            }
        }

        return {
            valid: violations.length === 0,
            violations,
            score: this.calculatePasswordScore(password)
        };
    }

    calculatePasswordScore(password) {
        let score = 0;
        
        // Length scoring
        score += Math.min(password.length * 2, 50);
        
        // Character diversity
        if (/[a-z]/.test(password)) score += 5;
        if (/[A-Z]/.test(password)) score += 5;
        if (/[0-9]/.test(password)) score += 5;
        if (/[^A-Za-z0-9]/.test(password)) score += 10;
        
        // Unique characters
        const uniqueRatio = new Set(password).size / password.length;
        score += uniqueRatio * 20;
        
        return Math.min(score, 100);
    }

    async generateSecurePassword(length = 16) {
        const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        const lowercase = 'abcdefghijklmnopqrstuvwxyz';
        const numbers = '0123456789';
        const symbols = '!@#$%^&*()_+-=[]{}|;:,.<>?';
        
        let password = '';
        
        // Ensure at least one character from each required set
        password += uppercase[crypto.randomInt(0, uppercase.length)];
        password += lowercase[crypto.randomInt(0, lowercase.length)];
        password += numbers[crypto.randomInt(0, numbers.length)];
        password += symbols[crypto.randomInt(0, symbols.length)];
        
        // Fill remaining length with random characters from all sets
        const allChars = uppercase + lowercase + numbers + symbols;
        for (let i = 4; i < length; i++) {
            password += allChars[crypto.randomInt(0, allChars.length)];
        }
        
        // Shuffle the password to avoid predictable patterns
        return password.split('').sort(() => 0.5 - Math.random()).join('');
    }

    async detectSecurityThreats(request) {
        const threats = [];
        const clientIP = request.ip;
        const userAgent = request.get('User-Agent') || '';
        const path = request.path;

        // SQL injection detection
        const sqlPatterns = [
            /(\bunion\b.*\bselect\b)|(\bselect\b.*\bunion\b)/i,
            /\b(select|insert|update|delete|drop|create|alter)\b.*\b(from|into|table|database)\b/i,
            /'.*(\bor\b|\band\b).*'/i,
            /\b(exec|execute|sp_|xp_)\b/i
        ];

        for (const pattern of sqlPatterns) {
            if (pattern.test(JSON.stringify(request.body) + request.url)) {
                threats.push({
                    type: 'SQL_INJECTION',
                    severity: 'HIGH',
                    pattern: pattern.toString(),
                    location: 'request_body_or_url'
                });
            }
        }

        // XSS detection
        const xssPatterns = [
            /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
            /javascript:/i,
            /on\w+\s*=/i,
            /<iframe\b/i,
            /<object\b/i,
            /<embed\b/i
        ];

        for (const pattern of xssPatterns) {
            if (pattern.test(JSON.stringify(request.body) + request.url)) {
                threats.push({
                    type: 'XSS',
                    severity: 'HIGH',
                    pattern: pattern.toString(),
                    location: 'request_body_or_url'
                });
            }
        }

        // Path traversal detection
        const pathTraversalPatterns = [
            /\.\.[\/\\]/,
            /%2e%2e[\/\\]/i,
            /\.\.[%2f%5c]/i
        ];

        for (const pattern of pathTraversalPatterns) {
            if (pattern.test(request.url)) {
                threats.push({
                    type: 'PATH_TRAVERSAL',
                    severity: 'HIGH',
                    pattern: pattern.toString(),
                    location: 'url_path'
                });
            }
        }

        // Command injection detection
        const commandPatterns = [
            /[;&|`$()]/,
            /\b(cat|ls|pwd|id|whoami|netstat|ps|kill|rm|mv|cp)\b/,
            /\$\(.*\)/,
            /`.*`/
        ];

        for (const pattern of commandPatterns) {
            if (pattern.test(JSON.stringify(request.body))) {
                threats.push({
                    type: 'COMMAND_INJECTION',
                    severity: 'CRITICAL',
                    pattern: pattern.toString(),
                    location: 'request_body'
                });
            }
        }

        // Suspicious user agent detection
        const suspiciousUAPatterns = [
            /sqlmap/i,
            /nikto/i,
            /nmap/i,
            /burp/i,
            /python-requests/i,
            /curl/i,
            /wget/i
        ];

        for (const pattern of suspiciousUAPatterns) {
            if (pattern.test(userAgent)) {
                threats.push({
                    type: 'SUSPICIOUS_USER_AGENT',
                    severity: 'MEDIUM',
                    userAgent,
                    pattern: pattern.toString()
                });
            }
        }

        // Rate limiting and brute force detection
        const currentTime = Date.now();
        const timeWindow = 60000; // 1 minute
        const maxRequests = 100;

        if (!this.activeThreats.has(clientIP)) {
            this.activeThreats.set(clientIP, { requests: [], failedLogins: 0, lastFailedLogin: 0 });
        }

        const clientData = this.activeThreats.get(clientIP);
        clientData.requests = clientData.requests.filter(time => currentTime - time < timeWindow);
        clientData.requests.push(currentTime);

        if (clientData.requests.length > maxRequests) {
            threats.push({
                type: 'RATE_LIMIT_EXCEEDED',
                severity: 'MEDIUM',
                requestCount: clientData.requests.length,
                timeWindow: timeWindow
            });
        }

        if (threats.length > 0) {
            this.securityMetrics.totalSecurityEvents++;
            this.securityMetrics.intrusionAttempts++;

            this.logger.warn('Security threats detected', {
                clientIP,
                userAgent,
                path,
                threats: threats.map(t => ({ type: t.type, severity: t.severity })),
                threatCount: threats.length
            });
        }

        return threats;
    }

    async blockThreats(threats, clientIP) {
        const criticalThreats = threats.filter(t => t.severity === 'CRITICAL');
        const highThreats = threats.filter(t => t.severity === 'HIGH');

        if (criticalThreats.length > 0) {
            // Immediate IP blocking for critical threats
            this.blockIP(clientIP, 3600000); // 1 hour
            this.securityMetrics.blockedAttacks++;
            
            this.logger.error('Critical security threat - IP blocked', {
                clientIP,
                threats: criticalThreats,
                blockDuration: '1 hour'
            });

            return { blocked: true, reason: 'Critical security threat detected', duration: 3600000 };
        }

        if (highThreats.length >= 3) {
            // Progressive blocking for multiple high severity threats
            this.blockIP(clientIP, 900000); // 15 minutes
            this.securityMetrics.blockedAttacks++;

            this.logger.warn('Multiple high-severity threats - IP blocked', {
                clientIP,
                threats: highThreats,
                blockDuration: '15 minutes'
            });

            return { blocked: true, reason: 'Multiple high-severity threats', duration: 900000 };
        }

        return { blocked: false };
    }

    blockIP(ip, duration) {
        const unblockTime = Date.now() + duration;
        
        if (!this.activeThreats.has(ip)) {
            this.activeThreats.set(ip, { requests: [], failedLogins: 0, lastFailedLogin: 0 });
        }
        
        this.activeThreats.get(ip).blockedUntil = unblockTime;
        
        setTimeout(() => {
            const clientData = this.activeThreats.get(ip);
            if (clientData && clientData.blockedUntil === unblockTime) {
                delete clientData.blockedUntil;
            }
        }, duration);
    }

    isIPBlocked(ip) {
        const clientData = this.activeThreats.get(ip);
        return clientData && clientData.blockedUntil && clientData.blockedUntil > Date.now();
    }

    async generateSecureToken(payload, expiresIn = '1h') {
        const header = {
            alg: 'HS512',
            typ: 'JWT'
        };

        const now = Math.floor(Date.now() / 1000);
        const exp = now + this.parseTimeString(expiresIn);

        const jwtPayload = {
            ...payload,
            iat: now,
            exp: exp,
            jti: crypto.randomUUID()
        };

        const encodedHeader = Buffer.from(JSON.stringify(header)).toString('base64url');
        const encodedPayload = Buffer.from(JSON.stringify(jwtPayload)).toString('base64url');
        
        const signature = crypto.createHmac('sha512', this.integrityKey)
            .update(`${encodedHeader}.${encodedPayload}`)
            .digest('base64url');

        return `${encodedHeader}.${encodedPayload}.${signature}`;
    }

    async validateSecureToken(token) {
        try {
            const [encodedHeader, encodedPayload, providedSignature] = token.split('.');
            
            const expectedSignature = crypto.createHmac('sha512', this.integrityKey)
                .update(`${encodedHeader}.${encodedPayload}`)
                .digest('base64url');

            if (!crypto.timingSafeEqual(
                Buffer.from(providedSignature, 'base64url'),
                Buffer.from(expectedSignature, 'base64url')
            )) {
                throw new Error('Invalid token signature');
            }

            const payload = JSON.parse(Buffer.from(encodedPayload, 'base64url').toString());
            
            if (payload.exp <= Math.floor(Date.now() / 1000)) {
                throw new Error('Token expired');
            }

            return { valid: true, payload };
        } catch (error) {
            return { valid: false, error: error.message };
        }
    }

    parseTimeString(timeStr) {
        const units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        };

        const match = timeStr.match(/^(\d+)([smhd])$/);
        if (!match) return 3600; // Default 1 hour

        const [, number, unit] = match;
        return parseInt(number) * units[unit];
    }

    getSecurityMetrics() {
        const totalEvents = this.securityMetrics.totalSecurityEvents;
        
        return {
            ...this.securityMetrics,
            blockRate: totalEvents ? ((this.securityMetrics.blockedAttacks / totalEvents) * 100).toFixed(2) + '%' : '0%',
            violationRate: totalEvents ? ((this.securityMetrics.securityViolations / totalEvents) * 100).toFixed(2) + '%' : '0%',
            activeThreats: this.activeThreats.size,
            hsmStatus: this.hsmAvailable ? 'active' : 'unavailable'
        };
    }

    async performSecurityAudit() {
        const auditReport = {
            timestamp: new Date(),
            securityLevel: this.config.securityLevel,
            cryptoStatus: {
                algorithm: this.config.encryptionAlgorithm,
                keyDerivation: this.config.keyDerivationFunction,
                hsmAvailable: this.hsmAvailable
            },
            networkSecurity: {
                tlsRequired: this.config.networkSecurity.requireTLS,
                minTlsVersion: this.config.networkSecurity.minTLSVersion,
                allowedCiphers: this.config.networkSecurity.allowedCiphers.length
            },
            passwordPolicy: this.config.passwordComplexity,
            metrics: this.getSecurityMetrics(),
            recommendations: []
        };

        // Security recommendations
        if (!this.hsmAvailable) {
            auditReport.recommendations.push('Deploy Hardware Security Module for enhanced key protection');
        }

        if (this.securityMetrics.violationRate > 5) {
            auditReport.recommendations.push('High security violation rate detected - review access controls');
        }

        if (this.activeThreats.size > 100) {
            auditReport.recommendations.push('Large number of active threats - consider additional rate limiting');
        }

        return auditReport;
    }
}

module.exports = EmbassySecurityManager;