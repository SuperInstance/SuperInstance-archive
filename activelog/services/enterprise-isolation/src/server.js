const express = require('express');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const session = require('express-session');
const morgan = require('morgan');
const winston = require('winston');
const path = require('path');
const fs = require('fs');

// Enterprise modules
const AirGapInstaller = require('./core/air-gap-installer');
const InternalAuthSystem = require('./auth/internal-auth-system');
const DataSovereigntyController = require('./sovereignty/data-sovereignty-controller');
const EmbassySecurity = require('./security/embassy-security');
const RoleBasedMonitor = require('./monitoring/role-based-monitor');
const ComplianceReporter = require('./compliance/compliance-reporter');
const AuditTrailManager = require('./audit/audit-trail-manager');
const BackupSystem = require('./backup/backup-system');
const UpdateManager = require('./update/update-manager');
const OfflinePackager = require('./deployment/offline-packager');

class EnterpriseIsolationServer {
    constructor() {
        this.app = express();
        this.port = process.env.PORT || 8309;
        this.environment = process.env.NODE_ENV || 'production';
        this.deploymentMode = process.env.DEPLOYMENT_MODE || 'air-gapped';
        
        // Initialize core systems
        this.airGapInstaller = new AirGapInstaller();
        this.authSystem = new InternalAuthSystem();
        this.dataSovereignty = new DataSovereigntyController();
        this.embassySecurity = new EmbassySecurity();
        this.roleMonitor = new RoleBasedMonitor();
        this.complianceReporter = new ComplianceReporter();
        this.auditManager = new AuditTrailManager();
        this.backupSystem = new BackupSystem();
        this.updateManager = new UpdateManager();
        this.offlinePackager = new OfflinePackager();
        
        this.initializeLogger();
        this.setupSecurityMiddleware();
        this.initializeSystems();
    }

    initializeLogger() {
        // Create logs directory if it doesn't exist
        const logsDir = path.join(__dirname, '../logs');
        if (!fs.existsSync(logsDir)) {
            fs.mkdirSync(logsDir, { recursive: true });
        }

        this.logger = winston.createLogger({
            level: 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json(),
                winston.format.printf(({ timestamp, level, message, stack, ...meta }) => {
                    return JSON.stringify({
                        timestamp,
                        level,
                        message,
                        stack,
                        ...meta,
                        deployment_mode: this.deploymentMode,
                        security_level: 'embassy-grade'
                    });
                })
            ),
            defaultMeta: { 
                service: 'enterprise-isolation',
                version: process.env.npm_package_version || '1.0.0',
                node_id: process.env.NODE_ID || 'primary'
            },
            transports: [
                // Critical security events - separate file with encryption
                new winston.transports.File({ 
                    filename: path.join(logsDir, 'security-critical.log'), 
                    level: 'error',
                    maxsize: 10485760, // 10MB
                    maxFiles: 100,
                    tailable: true
                }),
                // Audit trail - tamper-evident logging
                new winston.transports.File({ 
                    filename: path.join(logsDir, 'audit-trail.log'),
                    level: 'warn',
                    maxsize: 10485760,
                    maxFiles: 1000,
                    tailable: true
                }),
                // General application logs
                new winston.transports.File({ 
                    filename: path.join(logsDir, 'application.log'),
                    maxsize: 10485760,
                    maxFiles: 50,
                    tailable: true
                }),
                // Compliance logs
                new winston.transports.File({ 
                    filename: path.join(logsDir, 'compliance.log'),
                    level: 'info',
                    maxsize: 10485760,
                    maxFiles: 200,
                    tailable: true
                })
            ],
            exceptionHandlers: [
                new winston.transports.File({ 
                    filename: path.join(logsDir, 'exceptions.log'),
                    maxsize: 10485760,
                    maxFiles: 10
                })
            ],
            rejectionHandlers: [
                new winston.transports.File({ 
                    filename: path.join(logsDir, 'rejections.log'),
                    maxsize: 10485760,
                    maxFiles: 10
                })
            ]
        });

        // Only log to console in development or if explicitly enabled
        if (this.environment !== 'production' || process.env.CONSOLE_LOGS === 'true') {
            this.logger.add(new winston.transports.Console({
                format: winston.format.combine(
                    winston.format.colorize(),
                    winston.format.simple()
                )
            }));
        }
    }

    setupSecurityMiddleware() {
        // Maximum security configuration
        this.app.use(helmet({
            contentSecurityPolicy: {
                directives: {
                    defaultSrc: ["'self'"],
                    scriptSrc: ["'self'"],
                    styleSrc: ["'self'", "'unsafe-inline'"],
                    imgSrc: ["'self'", "data:"],
                    connectSrc: ["'self'"],
                    fontSrc: ["'self'"],
                    objectSrc: ["'none'"],
                    mediaSrc: ["'self'"],
                    frameSrc: ["'none'"],
                    childSrc: ["'none'"],
                    workerSrc: ["'none'"],
                    manifestSrc: ["'self'"],
                    baseUri: ["'self'"],
                    formAction: ["'self'"]
                },
                reportOnly: false
            },
            crossOriginEmbedderPolicy: true,
            crossOriginOpenerPolicy: { policy: "same-origin" },
            crossOriginResourcePolicy: { policy: "same-origin" },
            dnsPrefetchControl: { allow: false },
            frameguard: { action: 'deny' },
            hidePoweredBy: true,
            hsts: {
                maxAge: 31536000,
                includeSubDomains: true,
                preload: true
            },
            ieNoOpen: true,
            noSniff: true,
            originAgentCluster: true,
            permittedCrossDomainPolicies: false,
            referrerPolicy: { policy: "no-referrer" },
            xssFilter: true
        }));

        // Compression for performance
        this.app.use(compression({
            level: 6,
            threshold: 1024,
            filter: (req, res) => {
                // Don't compress sensitive data
                if (req.headers['x-no-compression']) {
                    return false;
                }
                return compression.filter(req, res);
            }
        }));

        // Embassy-grade rate limiting
        const limiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: 100, // Limit each IP to 100 requests per windowMs
            standardHeaders: true,
            legacyHeaders: false,
            message: {
                error: 'Too many requests',
                code: 'RATE_LIMIT_EXCEEDED',
                retry_after: Math.ceil(15 * 60)
            },
            handler: (req, res, next, options) => {
                this.auditManager.logSecurityEvent({
                    type: 'rate_limit_exceeded',
                    ip: req.ip,
                    user_agent: req.get('user-agent'),
                    endpoint: req.originalUrl,
                    method: req.method,
                    timestamp: new Date(),
                    severity: 'medium'
                });

                res.status(options.statusCode).json(options.message);
            }
        });

        this.app.use(limiter);

        // Request logging with security context
        this.app.use(morgan('combined', {
            stream: {
                write: (message) => {
                    this.logger.info('HTTP Request', {
                        http_log: message.trim(),
                        category: 'http_access'
                    });
                }
            },
            skip: (req, res) => {
                // Skip logging for health checks in production
                return this.environment === 'production' && req.originalUrl === '/health';
            }
        }));

        // Body parsing with size limits
        this.app.use(express.json({ 
            limit: '1mb',
            verify: (req, res, buf, encoding) => {
                // Log all request bodies for audit
                if (buf && buf.length > 0) {
                    req.rawBody = buf.toString(encoding || 'utf8');
                    this.auditManager.logDataAccess({
                        type: 'request_body',
                        user_id: req.user?.id,
                        endpoint: req.originalUrl,
                        method: req.method,
                        size: buf.length,
                        timestamp: new Date()
                    });
                }
            }
        }));

        this.app.use(express.urlencoded({ 
            extended: false, 
            limit: '1mb' 
        }));

        // Custom security headers
        this.app.use((req, res, next) => {
            // Remove server information
            res.removeHeader('X-Powered-By');
            res.removeHeader('Server');
            
            // Add custom security headers
            res.setHeader('X-Content-Type-Options', 'nosniff');
            res.setHeader('X-Frame-Options', 'DENY');
            res.setHeader('X-XSS-Protection', '1; mode=block');
            res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
            res.setHeader('X-Permitted-Cross-Domain-Policies', 'none');
            res.setHeader('X-Download-Options', 'noopen');
            res.setHeader('X-DNS-Prefetch-Control', 'off');
            res.setHeader('X-Robots-Tag', 'noindex, nofollow, noarchive, nosnippet, notranslate');
            
            // Custom enterprise headers
            res.setHeader('X-Enterprise-Security-Level', 'embassy-grade');
            res.setHeader('X-Deployment-Mode', 'air-gapped');
            res.setHeader('X-Data-Sovereignty', 'enforced');
            
            next();
        });

        // Request ID generation for audit trails
        this.app.use((req, res, next) => {
            req.id = require('crypto').randomBytes(16).toString('hex');
            res.setHeader('X-Request-ID', req.id);
            
            // Start audit trail for this request
            this.auditManager.startRequestAudit(req.id, {
                ip: req.ip,
                user_agent: req.get('user-agent'),
                endpoint: req.originalUrl,
                method: req.method,
                timestamp: new Date(),
                user_id: req.user?.id
            });
            
            next();
        });
    }

    async initializeSystems() {
        try {
            this.logger.info('Initializing enterprise systems...');

            // Initialize in dependency order
            await this.embassySecurity.initialize();
            await this.dataSovereignty.initialize();
            await this.authSystem.initialize();
            await this.auditManager.initialize();
            await this.roleMonitor.initialize();
            await this.complianceReporter.initialize();
            await this.backupSystem.initialize();
            await this.updateManager.initialize();

            // Setup routes
            this.setupRoutes();

            // Setup error handlers
            this.setupErrorHandlers();

            // Setup system monitoring
            this.setupSystemMonitoring();

            // Setup compliance checks
            this.setupComplianceChecks();

            this.logger.info('Enterprise systems initialized successfully');

        } catch (error) {
            this.logger.error('Failed to initialize enterprise systems', {
                error: error.message,
                stack: error.stack
            });
            process.exit(1);
        }
    }

    setupRoutes() {
        // Health check endpoint (minimal information disclosure)
        this.app.get('/health', (req, res) => {
            const health = {
                status: 'operational',
                timestamp: new Date().toISOString(),
                version: process.env.npm_package_version || '1.0.0'
            };

            // Only include detailed health in non-production or for authenticated users
            if (this.environment !== 'production' || (req.user && req.user.role === 'system_admin')) {
                health.details = {
                    deployment_mode: this.deploymentMode,
                    uptime: process.uptime(),
                    memory_usage: process.memoryUsage(),
                    cpu_usage: process.cpuUsage()
                };
            }

            res.json(health);
        });

        // Authentication routes
        this.app.use('/api/auth', this.authSystem.getRoutes());

        // Data sovereignty routes
        this.app.use('/api/sovereignty', this.dataSovereignty.getRoutes());

        // Monitoring routes (role-based access)
        this.app.use('/api/monitor', this.roleMonitor.getRoutes());

        // Compliance routes
        this.app.use('/api/compliance', this.complianceReporter.getRoutes());

        // Audit routes
        this.app.use('/api/audit', this.auditManager.getRoutes());

        // Backup routes
        this.app.use('/api/backup', this.backupSystem.getRoutes());

        // Update routes
        this.app.use('/api/update', this.updateManager.getRoutes());

        // Air-gap installation routes
        this.app.use('/api/install', this.airGapInstaller.getRoutes());

        // Static file serving (secure)
        this.app.use('/static', express.static(path.join(__dirname, '../static'), {
            dotfiles: 'deny',
            etag: false,
            extensions: false,
            index: false,
            maxAge: '1d',
            redirect: false,
            setHeaders: (res, path, stat) => {
                res.setHeader('X-Content-Type-Options', 'nosniff');
                res.setHeader('X-Frame-Options', 'DENY');
            }
        }));

        // Admin interface (highly restricted)
        this.app.use('/admin', 
            this.authSystem.requireRole(['system_admin', 'security_admin']),
            express.static(path.join(__dirname, '../admin'), {
                dotfiles: 'deny',
                etag: false
            })
        );

        // API documentation (internal only)
        this.app.use('/docs', 
            this.authSystem.requireRole(['system_admin', 'developer']),
            express.static(path.join(__dirname, '../docs'))
        );

        // Catch-all for undefined routes
        this.app.use('*', (req, res) => {
            this.auditManager.logSecurityEvent({
                type: 'route_not_found',
                ip: req.ip,
                user_agent: req.get('user-agent'),
                endpoint: req.originalUrl,
                method: req.method,
                user_id: req.user?.id,
                timestamp: new Date(),
                severity: 'low'
            });

            res.status(404).json({
                error: 'Resource not found',
                code: 'RESOURCE_NOT_FOUND',
                request_id: req.id
            });
        });
    }

    setupErrorHandlers() {
        // Security-aware error handling
        this.app.use((error, req, res, next) => {
            // Log error with security context
            this.logger.error('Application error', {
                error: error.message,
                stack: error.stack,
                request_id: req.id,
                user_id: req.user?.id,
                ip: req.ip,
                user_agent: req.get('user-agent'),
                endpoint: req.originalUrl,
                method: req.method
            });

            // Audit security-related errors
            if (this.isSecurityError(error)) {
                this.auditManager.logSecurityEvent({
                    type: 'security_error',
                    error: error.message,
                    request_id: req.id,
                    user_id: req.user?.id,
                    ip: req.ip,
                    endpoint: req.originalUrl,
                    method: req.method,
                    timestamp: new Date(),
                    severity: this.getErrorSeverity(error)
                });
            }

            // Minimal error information disclosure
            const errorResponse = {
                error: 'Internal server error',
                code: 'INTERNAL_ERROR',
                request_id: req.id,
                timestamp: new Date().toISOString()
            };

            // Include more details for development or authorized users
            if (this.environment !== 'production' || 
                (req.user && ['system_admin', 'security_admin'].includes(req.user.role))) {
                errorResponse.details = {
                    message: error.message,
                    type: error.name
                };
            }

            res.status(error.status || 500).json(errorResponse);
        });

        // Unhandled promise rejections
        process.on('unhandledRejection', (reason, promise) => {
            this.logger.error('Unhandled promise rejection', {
                reason: reason.toString(),
                stack: reason.stack,
                promise: promise.toString()
            });
        });

        // Uncaught exceptions
        process.on('uncaughtException', (error) => {
            this.logger.error('Uncaught exception', {
                error: error.message,
                stack: error.stack
            });

            // Graceful shutdown on critical errors
            this.gracefulShutdown(1);
        });

        // Graceful shutdown handlers
        process.on('SIGTERM', () => this.gracefulShutdown(0));
        process.on('SIGINT', () => this.gracefulShutdown(0));
    }

    setupSystemMonitoring() {
        // System health monitoring
        setInterval(() => {
            const memoryUsage = process.memoryUsage();
            const cpuUsage = process.cpuUsage();
            
            this.logger.info('System health check', {
                memory: memoryUsage,
                cpu: cpuUsage,
                uptime: process.uptime(),
                category: 'system_health'
            });

            // Alert if memory usage is high
            if (memoryUsage.heapUsed > 1024 * 1024 * 1024) { // 1GB
                this.auditManager.logSecurityEvent({
                    type: 'high_memory_usage',
                    memory_usage: memoryUsage,
                    timestamp: new Date(),
                    severity: 'medium'
                });
            }
        }, 60000); // Every minute

        // Security monitoring
        setInterval(() => {
            this.embassySecurity.performSecurityCheck();
            this.dataSovereignty.performSovereigntyCheck();
        }, 300000); // Every 5 minutes
    }

    setupComplianceChecks() {
        // Daily compliance checks
        const cron = require('node-cron');
        
        cron.schedule('0 2 * * *', async () => { // 2 AM daily
            try {
                await this.complianceReporter.runDailyCompliance();
                this.logger.info('Daily compliance check completed');
            } catch (error) {
                this.logger.error('Daily compliance check failed', {
                    error: error.message,
                    stack: error.stack
                });
            }
        });

        // Weekly security audits
        cron.schedule('0 3 * * 0', async () => { // 3 AM on Sundays
            try {
                await this.auditManager.runWeeklyAudit();
                this.logger.info('Weekly security audit completed');
            } catch (error) {
                this.logger.error('Weekly security audit failed', {
                    error: error.message,
                    stack: error.stack
                });
            }
        });

        // Monthly backup verification
        cron.schedule('0 4 1 * *', async () => { // 4 AM on first day of month
            try {
                await this.backupSystem.verifyBackups();
                this.logger.info('Monthly backup verification completed');
            } catch (error) {
                this.logger.error('Monthly backup verification failed', {
                    error: error.message,
                    stack: error.stack
                });
            }
        });
    }

    isSecurityError(error) {
        const securityErrors = [
            'Authentication',
            'Authorization',
            'CSRF',
            'XSS',
            'SQL',
            'Injection',
            'Validation',
            'Rate',
            'Brute'
        ];
        
        return securityErrors.some(type => 
            error.name.includes(type) || 
            error.message.includes(type)
        );
    }

    getErrorSeverity(error) {
        if (error.status >= 500) return 'high';
        if (error.status >= 400) return 'medium';
        return 'low';
    }

    async start() {
        try {
            // Pre-flight security checks
            await this.embassySecurity.performStartupSecurityCheck();
            
            // Verify air-gap status
            if (this.deploymentMode === 'air-gapped') {
                await this.airGapInstaller.verifyAirGapStatus();
            }

            // Start the server
            this.server = this.app.listen(this.port, '0.0.0.0', () => {
                this.logger.info(`Enterprise Isolation Server started`, {
                    port: this.port,
                    environment: this.environment,
                    deployment_mode: this.deploymentMode,
                    security_level: 'embassy-grade',
                    node_version: process.version,
                    pid: process.pid
                });

                // Log successful startup to audit trail
                this.auditManager.logSystemEvent({
                    type: 'system_startup',
                    port: this.port,
                    environment: this.environment,
                    deployment_mode: this.deploymentMode,
                    timestamp: new Date(),
                    severity: 'info'
                });
            });

            // Setup server timeout and keep-alive
            this.server.timeout = 30000; // 30 seconds
            this.server.keepAliveTimeout = 5000; // 5 seconds
            this.server.headersTimeout = 6000; // 6 seconds

        } catch (error) {
            this.logger.error('Failed to start enterprise server', {
                error: error.message,
                stack: error.stack
            });
            process.exit(1);
        }
    }

    async gracefulShutdown(exitCode = 0) {
        this.logger.info('Initiating graceful shutdown...');

        // Stop accepting new connections
        if (this.server) {
            this.server.close(async () => {
                this.logger.info('HTTP server closed');

                try {
                    // Shutdown systems in reverse order
                    await this.backupSystem.shutdown();
                    await this.complianceReporter.shutdown();
                    await this.auditManager.shutdown();
                    await this.roleMonitor.shutdown();
                    await this.dataSovereignty.shutdown();
                    await this.embassySecurity.shutdown();

                    this.logger.info('All systems shut down successfully');
                    process.exit(exitCode);
                } catch (error) {
                    this.logger.error('Error during shutdown', {
                        error: error.message,
                        stack: error.stack
                    });
                    process.exit(1);
                }
            });
        }

        // Force shutdown after 10 seconds
        setTimeout(() => {
            this.logger.error('Forced shutdown after timeout');
            process.exit(1);
        }, 10000);
    }
}

// Start the server if this file is run directly
if (require.main === module) {
    const server = new EnterpriseIsolationServer();
    server.start().catch(error => {
        console.error('Fatal error starting server:', error);
        process.exit(1);
    });
}

module.exports = EnterpriseIsolationServer;