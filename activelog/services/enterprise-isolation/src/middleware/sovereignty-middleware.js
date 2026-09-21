const DataSovereigntyController = require('../core/data-sovereignty-controller');
const winston = require('winston');

class SovereigntyMiddleware {
    constructor(options = {}) {
        this.sovereignty = new DataSovereigntyController(options);
        
        this.logger = winston.createLogger({
            level: 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json()
            ),
            defaultMeta: { service: 'sovereignty-middleware' },
            transports: [
                new winston.transports.File({
                    filename: 'logs/sovereignty-middleware.log'
                })
            ]
        });

        this.requestMetrics = {
            totalRequests: 0,
            blockedRequests: 0,
            jurisdictionViolations: 0,
            complianceViolations: 0
        };
    }

    // Middleware to check data sovereignty for incoming requests
    checkDataSovereignty() {
        return async (req, res, next) => {
            try {
                this.requestMetrics.totalRequests++;

                // Extract client location information
                const clientIP = this.getClientIP(req);
                const clientJurisdiction = await this.sovereignty.determineJurisdiction(clientIP);
                
                // Add sovereignty information to request
                req.sovereignty = {
                    clientIP,
                    clientJurisdiction,
                    serverJurisdiction: process.env.SERVER_JURISDICTION || 'US'
                };

                // Check if client jurisdiction is allowed
                const jurisdictionAllowed = await this.validateClientJurisdiction(clientJurisdiction);
                if (!jurisdictionAllowed) {
                    this.requestMetrics.blockedRequests++;
                    this.requestMetrics.jurisdictionViolations++;
                    
                    this.logger.warn('Request blocked due to jurisdiction restriction', {
                        clientIP,
                        clientJurisdiction,
                        userAgent: req.get('User-Agent'),
                        path: req.path
                    });

                    return res.status(403).json({
                        error: 'Access denied: Jurisdiction restriction',
                        code: 'JURISDICTION_BLOCKED',
                        allowedJurisdictions: this.sovereignty.config.allowedJurisdictions
                    });
                }

                // Check for data transfer restrictions on file uploads
                if (req.method === 'POST' || req.method === 'PUT') {
                    const transferValidation = await this.validateDataTransfer(req);
                    if (!transferValidation.allowed) {
                        this.requestMetrics.blockedRequests++;
                        this.requestMetrics.complianceViolations++;

                        this.logger.warn('Data transfer blocked', {
                            clientIP,
                            clientJurisdiction,
                            reason: transferValidation.reason,
                            violatedPolicies: transferValidation.violatedPolicies,
                            path: req.path
                        });

                        return res.status(403).json({
                            error: 'Data transfer not permitted',
                            reason: transferValidation.reason,
                            violatedPolicies: transferValidation.violatedPolicies,
                            code: 'TRANSFER_BLOCKED'
                        });
                    }
                }

                next();
            } catch (error) {
                this.logger.error('Sovereignty middleware error', {
                    error: error.message,
                    stack: error.stack,
                    path: req.path,
                    method: req.method
                });

                res.status(500).json({
                    error: 'Data sovereignty validation failed',
                    code: 'SOVEREIGNTY_ERROR'
                });
            }
        };
    }

    // Middleware to validate outgoing data transfers
    validateDataResponse() {
        return async (req, res, next) => {
            const originalSend = res.send;
            const self = this;

            res.send = async function(body) {
                try {
                    // Check if response contains sensitive data
                    const dataClassification = self.classifyResponseData(body, req.path);
                    
                    if (dataClassification) {
                        const transferValidation = await self.sovereignty.validateDataTransfer(
                            req.sovereignty.serverJurisdiction,
                            req.sovereignty.clientJurisdiction,
                            dataClassification.level,
                            dataClassification.compliance || []
                        );

                        if (!transferValidation.allowed) {
                            self.logger.warn('Outgoing data transfer blocked', {
                                clientJurisdiction: req.sovereignty.clientJurisdiction,
                                dataClassification: dataClassification.level,
                                reason: transferValidation.reason,
                                path: req.path
                            });

                            return originalSend.call(this, JSON.stringify({
                                error: 'Data cannot be transferred to your jurisdiction',
                                reason: transferValidation.reason,
                                code: 'EXPORT_RESTRICTED'
                            }));
                        }

                        // Add transfer audit log
                        self.logger.info('Data transfer approved', {
                            transferId: transferValidation.transferId,
                            fromJurisdiction: transferValidation.fromJurisdiction,
                            toJurisdiction: transferValidation.toJurisdiction,
                            dataClassification: dataClassification.level,
                            path: req.path
                        });
                    }

                    return originalSend.call(this, body);
                } catch (error) {
                    self.logger.error('Response validation error', {
                        error: error.message,
                        path: req.path
                    });
                    return originalSend.call(this, body);
                }
            };

            next();
        };
    }

    // Middleware to enforce data residency requirements
    enforceDataResidency() {
        return async (req, res, next) => {
            try {
                // Check if request involves data that must remain in specific jurisdiction
                const dataResidencyRequirements = await this.getDataResidencyRequirements(req);
                
                for (const requirement of dataResidencyRequirements) {
                    const compliance = await this.sovereignty.enforceDataResidency(
                        requirement.assetId,
                        requirement.requiredJurisdiction
                    );

                    if (!compliance.compliant && !compliance.relocationPlan) {
                        this.logger.warn('Data residency violation', {
                            assetId: requirement.assetId,
                            requiredJurisdiction: requirement.requiredJurisdiction,
                            currentJurisdiction: compliance.jurisdiction,
                            path: req.path
                        });

                        return res.status(403).json({
                            error: 'Data residency requirement violated',
                            assetId: requirement.assetId,
                            requiredJurisdiction: requirement.requiredJurisdiction,
                            code: 'RESIDENCY_VIOLATION'
                        });
                    }
                }

                next();
            } catch (error) {
                this.logger.error('Data residency enforcement error', {
                    error: error.message,
                    path: req.path
                });
                next(error);
            }
        };
    }

    async validateClientJurisdiction(jurisdiction) {
        return this.sovereignty.config.allowedJurisdictions.includes(jurisdiction) &&
               !this.sovereignty.config.exportRestrictedCountries.includes(jurisdiction);
    }

    async validateDataTransfer(req) {
        // Extract data classification from request headers or body
        const dataClassification = req.headers['x-data-classification'] || 'internal';
        const complianceRequirements = req.headers['x-compliance-requirements'] 
            ? req.headers['x-compliance-requirements'].split(',')
            : [];

        const serverJurisdiction = process.env.SERVER_JURISDICTION || 'US';
        
        return await this.sovereignty.validateDataTransfer(
            req.sovereignty.clientJurisdiction,
            serverJurisdiction,
            dataClassification,
            complianceRequirements
        );
    }

    classifyResponseData(body, path) {
        // Simple classification based on path and content
        if (typeof body === 'string') {
            try {
                body = JSON.parse(body);
            } catch (e) {
                return null;
            }
        }

        // Check for PII indicators
        const piiFields = ['ssn', 'socialSecurityNumber', 'passport', 'creditCard', 'email', 'phone'];
        const hasPII = this.containsFields(body, piiFields);

        // Check for financial data
        const financialFields = ['accountNumber', 'routingNumber', 'bankAccount', 'payment'];
        const hasFinancial = this.containsFields(body, financialFields);

        // Check for health data
        const healthFields = ['medicalRecord', 'diagnosis', 'prescription', 'healthData'];
        const hasHealth = this.containsFields(body, healthFields);

        if (hasHealth) {
            return {
                level: 'restricted',
                compliance: ['HIPAA']
            };
        }

        if (hasFinancial) {
            return {
                level: 'confidential',
                compliance: ['SOX', 'PCI-DSS']
            };
        }

        if (hasPII) {
            return {
                level: 'confidential',
                compliance: ['GDPR', 'CCPA']
            };
        }

        // Path-based classification
        if (path.includes('/admin') || path.includes('/internal')) {
            return {
                level: 'internal',
                compliance: []
            };
        }

        if (path.includes('/public')) {
            return {
                level: 'public',
                compliance: []
            };
        }

        return {
            level: 'internal',
            compliance: []
        };
    }

    containsFields(obj, fields) {
        if (!obj || typeof obj !== 'object') return false;

        const objString = JSON.stringify(obj).toLowerCase();
        return fields.some(field => objString.includes(field.toLowerCase()));
    }

    async getDataResidencyRequirements(req) {
        const requirements = [];

        // Extract asset IDs from request
        const assetId = req.params.assetId || req.body?.assetId || req.query.assetId;
        if (assetId) {
            // In a real implementation, this would query a database
            // For now, return example requirements
            requirements.push({
                assetId,
                requiredJurisdiction: req.headers['x-required-jurisdiction'] || 'US'
            });
        }

        return requirements;
    }

    getClientIP(req) {
        return req.headers['x-forwarded-for']?.split(',')[0] ||
               req.headers['x-real-ip'] ||
               req.connection?.remoteAddress ||
               req.socket?.remoteAddress ||
               req.ip ||
               '127.0.0.1';
    }

    getMetrics() {
        const totalRequests = this.requestMetrics.totalRequests;
        
        return {
            ...this.requestMetrics,
            blockRate: totalRequests ? ((this.requestMetrics.blockedRequests / totalRequests) * 100).toFixed(2) + '%' : '0%',
            jurisdictionViolationRate: totalRequests ? ((this.requestMetrics.jurisdictionViolations / totalRequests) * 100).toFixed(2) + '%' : '0%',
            complianceViolationRate: totalRequests ? ((this.requestMetrics.complianceViolations / totalRequests) * 100).toFixed(2) + '%' : '0%'
        };
    }

    resetMetrics() {
        this.requestMetrics = {
            totalRequests: 0,
            blockedRequests: 0,
            jurisdictionViolations: 0,
            complianceViolations: 0
        };
    }
}

module.exports = SovereigntyMiddleware;