const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const session = require('express-session');
const RedisStore = require('connect-redis')(session);
const redis = require('redis');
const winston = require('winston');

// Import safety systems
const ParentApprovalSystem = require('./safety/parent-approval-system');
const SchoolPartnershipManager = require('./partnerships/school-partnership-manager');
const ParentMonitoringSystem = require('./monitoring/parent-monitoring-system');
const PrivateDiarySystem = require('./privacy/private-diary-system');
const ActivitySummaryGenerator = require('./reporting/activity-summary-generator');
const IllegalActivityDetector = require('./security/illegal-activity-detector');
const ParentAlertSystem = require('./alerts/parent-alert-system');
const TimeAccessController = require('./controls/time-access-controller');
const ContentFilter = require('./filtering/content-filter');
const CulturalExchangeProgram = require('./programs/cultural-exchange-program');
const LanguagePracticeManager = require('./language/language-practice-manager');
const TeacherSupervisionTools = require('./supervision/teacher-supervision-tools');

// Import routes
const authRoutes = require('./routes/auth');
const connectionRoutes = require('./routes/connections');
const monitoringRoutes = require('./routes/monitoring');
const alertRoutes = require('./routes/alerts');
const reportRoutes = require('./routes/reports');

class KidsConnectServer {
    constructor() {
        this.app = express();
        this.server = http.createServer(this.app);
        this.io = socketIo(this.server, {
            cors: {
                origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
                methods: ["GET", "POST"],
                credentials: true
            }
        });
        
        this.port = process.env.PORT || 8308;
        this.redisClient = null;
        
        // Initialize safety systems
        this.parentApprovalSystem = new ParentApprovalSystem();
        this.schoolPartnershipManager = new SchoolPartnershipManager();
        this.parentMonitoringSystem = new ParentMonitoringSystem();
        this.privateDiarySystem = new PrivateDiarySystem();
        this.activitySummaryGenerator = new ActivitySummaryGenerator();
        this.illegalActivityDetector = new IllegalActivityDetector();
        this.parentAlertSystem = new ParentAlertSystem();
        this.timeAccessController = new TimeAccessController();
        this.contentFilter = new ContentFilter();
        this.culturalExchangeProgram = new CulturalExchangeProgram();
        this.languagePracticeManager = new LanguagePracticeManager();
        this.teacherSupervisionTools = new TeacherSupervisionTools();
        
        this.initializeLogger();
        this.setupSafetySystems();
    }

    async initialize() {
        await this.setupRedis();
        this.setupMiddleware();
        this.setupRoutes();
        this.setupSocketHandlers();
        this.startSecurityMonitoring();
        this.startScheduledTasks();
    }

    initializeLogger() {
        this.logger = winston.createLogger({
            level: 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json()
            ),
            defaultMeta: { service: 'kids-connect' },
            transports: [
                new winston.transports.File({ 
                    filename: 'logs/error.log', 
                    level: 'error',
                    maxsize: 5242880, // 5MB
                    maxFiles: 5
                }),
                new winston.transports.File({ 
                    filename: 'logs/combined.log',
                    maxsize: 5242880,
                    maxFiles: 5
                }),
                new winston.transports.File({ 
                    filename: 'logs/security.log',
                    level: 'warn',
                    maxsize: 5242880,
                    maxFiles: 10
                })
            ]
        });

        if (process.env.NODE_ENV !== 'production') {
            this.logger.add(new winston.transports.Console({
                format: winston.format.simple()
            }));
        }
    }

    async setupRedis() {
        try {
            this.redisClient = redis.createClient({
                host: process.env.REDIS_HOST || 'localhost',
                port: process.env.REDIS_PORT || 6379,
                password: process.env.REDIS_PASSWORD
            });
            
            await this.redisClient.connect();
            this.logger.info('Redis connection established');
        } catch (error) {
            this.logger.error('Redis connection failed:', error);
            throw error;
        }
    }

    setupMiddleware() {
        // Security middleware
        this.app.use(helmet({
            contentSecurityPolicy: {
                directives: {
                    defaultSrc: ["'self'"],
                    styleSrc: ["'self'", "'unsafe-inline'"],
                    scriptSrc: ["'self'"],
                    imgSrc: ["'self'", "data:", "https:"],
                    connectSrc: ["'self'", "wss:"],
                    fontSrc: ["'self'"],
                    objectSrc: ["'none'"],
                    mediaSrc: ["'self'"],
                    frameSrc: ["'none'"],
                },
            },
            crossOriginEmbedderPolicy: false
        }));

        // CORS configuration
        this.app.use(cors({
            origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
            credentials: true,
            methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
        }));

        // Rate limiting - stricter for children's platform
        const limiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: 50, // Limit each IP to 50 requests per windowMs
            message: 'Too many requests from this IP, please try again later.',
            standardHeaders: true,
            legacyHeaders: false,
            handler: (req, res, next, options) => {
                this.logger.warn(`Rate limit exceeded for IP: ${req.ip}`);
                res.status(options.statusCode).json({
                    error: options.message,
                    retryAfter: Math.round(options.windowMs / 1000)
                });
            }
        });
        this.app.use(limiter);

        // Session configuration with Redis
        this.app.use(session({
            store: new RedisStore({ client: this.redisClient }),
            secret: process.env.SESSION_SECRET || 'kids-connect-super-secret-key-change-in-production',
            resave: false,
            saveUninitialized: false,
            cookie: {
                secure: process.env.NODE_ENV === 'production',
                httpOnly: true,
                maxAge: 1000 * 60 * 60 * 2, // 2 hours
                sameSite: 'strict'
            },
            name: 'kc.session'
        }));

        // Body parsing
        this.app.use(express.json({ 
            limit: '1mb',
            verify: (req, res, buf) => {
                // Log all incoming requests for security auditing
                this.logger.info(`Request: ${req.method} ${req.url}`, {
                    ip: req.ip,
                    userAgent: req.get('User-Agent'),
                    contentLength: buf.length
                });
            }
        }));
        this.app.use(express.urlencoded({ extended: true, limit: '1mb' }));

        // Custom safety middleware
        this.app.use(this.safetyCheckMiddleware.bind(this));
    }

    setupRoutes() {
        // Health check endpoint
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                version: process.env.npm_package_version || '1.0.0'
            });
        });

        // API routes
        this.app.use('/api/auth', authRoutes);
        this.app.use('/api/connections', connectionRoutes);
        this.app.use('/api/monitoring', monitoringRoutes);
        this.app.use('/api/alerts', alertRoutes);
        this.app.use('/api/reports', reportRoutes);

        // Safety system endpoints
        this.app.use('/api/parent-approval', this.createParentApprovalRoutes());
        this.app.use('/api/school-partnerships', this.createSchoolPartnershipRoutes());
        this.app.use('/api/time-controls', this.createTimeControlRoutes());
        this.app.use('/api/content-filter', this.createContentFilterRoutes());
        this.app.use('/api/cultural-exchange', this.createCulturalExchangeRoutes());
        this.app.use('/api/language-practice', this.createLanguagePracticeRoutes());
        this.app.use('/api/teacher-supervision', this.createTeacherSupervisionRoutes());

        // Catch all for undefined routes
        this.app.use('*', (req, res) => {
            this.logger.warn(`404 - Route not found: ${req.originalUrl}`, { ip: req.ip });
            res.status(404).json({ error: 'Route not found' });
        });

        // Error handling middleware
        this.app.use(this.errorHandlerMiddleware.bind(this));
    }

    setupSocketHandlers() {
        this.io.use(this.socketAuthenticationMiddleware.bind(this));
        this.io.use(this.socketSafetyMiddleware.bind(this));

        this.io.on('connection', (socket) => {
            this.logger.info(`Socket connection established: ${socket.id}`, {
                userId: socket.userId,
                ip: socket.handshake.address
            });

            // Set up real-time monitoring for this socket
            this.parentMonitoringSystem.addSocketMonitoring(socket);
            
            // Handle connection requests
            socket.on('connection-request', async (data) => {
                await this.handleConnectionRequest(socket, data);
            });

            // Handle messages with safety checks
            socket.on('message', async (data) => {
                await this.handleMessage(socket, data);
            });

            // Handle cultural exchange activities
            socket.on('cultural-activity', async (data) => {
                await this.handleCulturalActivity(socket, data);
            });

            // Handle language practice sessions
            socket.on('language-practice', async (data) => {
                await this.handleLanguagePractice(socket, data);
            });

            socket.on('disconnect', (reason) => {
                this.logger.info(`Socket disconnected: ${socket.id}`, {
                    userId: socket.userId,
                    reason: reason
                });
                this.parentMonitoringSystem.removeSocketMonitoring(socket);
            });
        });
    }

    setupSafetySystems() {
        // Connect safety systems to each other
        this.illegalActivityDetector.on('illegalActivityDetected', (alert) => {
            this.parentAlertSystem.sendUrgentAlert(alert);
            this.logger.error('Illegal activity detected:', alert);
        });

        this.contentFilter.on('inappropriateContent', (incident) => {
            this.parentAlertSystem.sendContentAlert(incident);
            this.parentMonitoringSystem.logIncident(incident);
        });

        this.parentApprovalSystem.on('connectionApproved', (connection) => {
            this.parentMonitoringSystem.startMonitoring(connection);
        });

        this.timeAccessController.on('accessViolation', (violation) => {
            this.parentAlertSystem.sendTimeViolationAlert(violation);
        });
    }

    async safetyCheckMiddleware(req, res, next) {
        try {
            // Check if user has access during allowed times
            if (req.session && req.session.userId) {
                const hasAccess = await this.timeAccessController.checkAccess(
                    req.session.userId,
                    new Date()
                );
                
                if (!hasAccess) {
                    return res.status(403).json({
                        error: 'Access not allowed at this time',
                        code: 'TIME_RESTRICTION'
                    });
                }
            }

            // Log all activity for monitoring
            if (req.session && req.session.userId) {
                this.parentMonitoringSystem.logActivity(req.session.userId, {
                    type: 'api-request',
                    endpoint: req.path,
                    method: req.method,
                    timestamp: new Date(),
                    ip: req.ip
                });
            }

            next();
        } catch (error) {
            this.logger.error('Safety check middleware error:', error);
            next(error);
        }
    }

    async socketAuthenticationMiddleware(socket, next) {
        try {
            // Verify socket authentication
            const token = socket.handshake.auth.token;
            if (!token) {
                return next(new Error('Authentication required'));
            }

            // Verify user and get user data
            const userData = await this.verifyUserToken(token);
            if (!userData) {
                return next(new Error('Invalid authentication'));
            }

            socket.userId = userData.userId;
            socket.userRole = userData.role;
            socket.schoolId = userData.schoolId;
            
            next();
        } catch (error) {
            this.logger.error('Socket authentication error:', error);
            next(new Error('Authentication failed'));
        }
    }

    async socketSafetyMiddleware(socket, next) {
        try {
            // Check time-based access
            const hasAccess = await this.timeAccessController.checkAccess(socket.userId, new Date());
            if (!hasAccess) {
                return next(new Error('Access not allowed at this time'));
            }

            // Set up safety monitoring for this socket
            socket.safetyMonitoring = {
                messageCount: 0,
                warningCount: 0,
                startTime: new Date()
            };

            next();
        } catch (error) {
            this.logger.error('Socket safety middleware error:', error);
            next(error);
        }
    }

    async handleConnectionRequest(socket, data) {
        try {
            // Validate connection request
            const validation = await this.parentApprovalSystem.validateConnectionRequest(
                socket.userId,
                data.targetUserId,
                data.requestType
            );

            if (!validation.approved) {
                socket.emit('connection-request-denied', {
                    reason: validation.reason,
                    requiresParentApproval: validation.requiresParentApproval
                });
                return;
            }

            // Process approved connection
            const connection = await this.parentApprovalSystem.createConnection(
                socket.userId,
                data.targetUserId,
                data.requestType,
                validation.approvalId
            );

            socket.emit('connection-established', connection);
            
            // Notify parents
            await this.parentAlertSystem.sendConnectionAlert(connection);
            
        } catch (error) {
            this.logger.error('Connection request error:', error);
            socket.emit('connection-error', { error: 'Failed to process connection request' });
        }
    }

    async handleMessage(socket, data) {
        try {
            // Content safety check
            const contentCheck = await this.contentFilter.checkMessage(data.message, socket.userId);
            
            if (!contentCheck.allowed) {
                socket.emit('message-blocked', {
                    reason: contentCheck.reason,
                    severity: contentCheck.severity
                });
                
                // Alert parents if severe
                if (contentCheck.severity === 'high') {
                    await this.parentAlertSystem.sendContentViolationAlert({
                        userId: socket.userId,
                        content: data.message,
                        reason: contentCheck.reason,
                        timestamp: new Date()
                    });
                }
                return;
            }

            // Check for illegal activity
            const illegalCheck = await this.illegalActivityDetector.analyzeContent(data.message, {
                userId: socket.userId,
                recipientId: data.recipientId,
                timestamp: new Date()
            });

            if (illegalCheck.isIllegal) {
                // Immediate escalation
                await this.handleIllegalActivity(socket, illegalCheck);
                return;
            }

            // Process safe message
            const processedMessage = {
                id: require('uuid').v4(),
                senderId: socket.userId,
                recipientId: data.recipientId,
                content: contentCheck.processedContent || data.message,
                timestamp: new Date(),
                type: data.type || 'text'
            };

            // Log for parent monitoring (except private diary)
            if (data.type !== 'diary') {
                this.parentMonitoringSystem.logMessage(processedMessage);
            }

            // Send message to recipient
            this.io.to(data.recipientId).emit('new-message', processedMessage);
            socket.emit('message-sent', { messageId: processedMessage.id });
            
        } catch (error) {
            this.logger.error('Message handling error:', error);
            socket.emit('message-error', { error: 'Failed to send message' });
        }
    }

    async handleCulturalActivity(socket, data) {
        try {
            const activity = await this.culturalExchangeProgram.processActivity(socket.userId, data);
            
            // Log cultural learning activity
            this.parentMonitoringSystem.logActivity(socket.userId, {
                type: 'cultural-exchange',
                activity: activity.type,
                partner: activity.partnerId,
                timestamp: new Date()
            });

            socket.emit('cultural-activity-result', activity);
            
        } catch (error) {
            this.logger.error('Cultural activity error:', error);
            socket.emit('cultural-activity-error', { error: 'Failed to process activity' });
        }
    }

    async handleLanguagePractice(socket, data) {
        try {
            const session = await this.languagePracticeManager.processSession(socket.userId, data);
            
            // Log language learning
            this.parentMonitoringSystem.logActivity(socket.userId, {
                type: 'language-practice',
                language: session.language,
                partner: session.partnerId,
                duration: session.duration,
                timestamp: new Date()
            });

            socket.emit('language-practice-result', session);
            
        } catch (error) {
            this.logger.error('Language practice error:', error);
            socket.emit('language-practice-error', { error: 'Failed to process session' });
        }
    }

    async handleIllegalActivity(socket, illegalCheck) {
        // Immediate actions for illegal activity
        this.logger.error('ILLEGAL ACTIVITY DETECTED', {
            userId: socket.userId,
            content: illegalCheck.content,
            reasons: illegalCheck.reasons,
            severity: illegalCheck.severity
        });

        // Disconnect user immediately
        socket.disconnect(true);

        // Alert all relevant parties
        await this.parentAlertSystem.sendUrgentAlert({
            type: 'illegal-activity',
            userId: socket.userId,
            severity: illegalCheck.severity,
            reasons: illegalCheck.reasons,
            timestamp: new Date(),
            action: 'user-disconnected'
        });

        // Notify school authorities
        await this.teacherSupervisionTools.reportIncident({
            userId: socket.userId,
            type: 'illegal-activity',
            details: illegalCheck,
            timestamp: new Date()
        });
    }

    createParentApprovalRoutes() {
        const router = express.Router();
        
        router.post('/request-connection', async (req, res) => {
            try {
                const result = await this.parentApprovalSystem.requestConnection(
                    req.session.userId,
                    req.body
                );
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        router.get('/pending-approvals/:parentId', async (req, res) => {
            try {
                const approvals = await this.parentApprovalSystem.getPendingApprovals(
                    req.params.parentId
                );
                res.json(approvals);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        router.post('/approve-connection', async (req, res) => {
            try {
                const result = await this.parentApprovalSystem.approveConnection(
                    req.body.approvalId,
                    req.body.approved,
                    req.body.conditions
                );
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        return router;
    }

    createSchoolPartnershipRoutes() {
        const router = express.Router();
        
        router.post('/create-partnership', async (req, res) => {
            try {
                const partnership = await this.schoolPartnershipManager.createPartnership(req.body);
                res.json(partnership);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        router.get('/partnerships/:schoolId', async (req, res) => {
            try {
                const partnerships = await this.schoolPartnershipManager.getSchoolPartnerships(
                    req.params.schoolId
                );
                res.json(partnerships);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        return router;
    }

    createTimeControlRoutes() {
        const router = express.Router();
        
        router.post('/set-schedule/:userId', async (req, res) => {
            try {
                const schedule = await this.timeAccessController.setUserSchedule(
                    req.params.userId,
                    req.body.schedule
                );
                res.json(schedule);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        router.get('/check-access/:userId', async (req, res) => {
            try {
                const hasAccess = await this.timeAccessController.checkAccess(
                    req.params.userId,
                    new Date()
                );
                res.json({ hasAccess });
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        return router;
    }

    createContentFilterRoutes() {
        const router = express.Router();
        
        router.post('/check-content', async (req, res) => {
            try {
                const result = await this.contentFilter.checkContent(
                    req.body.content,
                    req.body.userId,
                    req.body.contentType
                );
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        router.get('/filter-settings/:userId', async (req, res) => {
            try {
                const settings = await this.contentFilter.getUserSettings(req.params.userId);
                res.json(settings);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        return router;
    }

    createCulturalExchangeRoutes() {
        const router = express.Router();
        
        router.get('/programs', async (req, res) => {
            try {
                const programs = await this.culturalExchangeProgram.getAvailablePrograms();
                res.json(programs);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        router.post('/join-program', async (req, res) => {
            try {
                const result = await this.culturalExchangeProgram.joinProgram(
                    req.session.userId,
                    req.body.programId
                );
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        return router;
    }

    createLanguagePracticeRoutes() {
        const router = express.Router();
        
        router.post('/find-partner', async (req, res) => {
            try {
                const partner = await this.languagePracticeManager.findPracticePartner(
                    req.session.userId,
                    req.body.targetLanguage,
                    req.body.nativeLanguage
                );
                res.json(partner);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        router.get('/sessions/:userId', async (req, res) => {
            try {
                const sessions = await this.languagePracticeManager.getUserSessions(
                    req.params.userId
                );
                res.json(sessions);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        return router;
    }

    createTeacherSupervisionRoutes() {
        const router = express.Router();
        
        router.get('/classroom-activity/:classroomId', async (req, res) => {
            try {
                const activity = await this.teacherSupervisionTools.getClassroomActivity(
                    req.params.classroomId
                );
                res.json(activity);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        router.get('/student-report/:studentId', async (req, res) => {
            try {
                const report = await this.teacherSupervisionTools.generateStudentReport(
                    req.params.studentId
                );
                res.json(report);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        return router;
    }

    async verifyUserToken(token) {
        // Implement JWT token verification
        // Return user data if valid, null if invalid
        try {
            const jwt = require('jsonwebtoken');
            const decoded = jwt.verify(token, process.env.JWT_SECRET || 'fallback-secret');
            return decoded;
        } catch (error) {
            return null;
        }
    }

    errorHandlerMiddleware(error, req, res, next) {
        this.logger.error('Unhandled error:', error);
        
        res.status(500).json({
            error: 'Internal server error',
            message: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
        });
    }

    startSecurityMonitoring() {
        // Start automated security monitoring
        setInterval(() => {
            this.illegalActivityDetector.performRoutineCheck();
        }, 60000); // Every minute

        setInterval(() => {
            this.parentMonitoringSystem.generateHourlyReports();
        }, 3600000); // Every hour
    }

    startScheduledTasks() {
        const cron = require('node-cron');
        
        // Daily activity summaries
        cron.schedule('0 20 * * *', async () => {
            try {
                await this.activitySummaryGenerator.generateDailySummaries();
                this.logger.info('Daily activity summaries generated');
            } catch (error) {
                this.logger.error('Failed to generate daily summaries:', error);
            }
        });

        // Weekly partnership reports
        cron.schedule('0 9 * * 1', async () => {
            try {
                await this.schoolPartnershipManager.generateWeeklyReports();
                this.logger.info('Weekly partnership reports generated');
            } catch (error) {
                this.logger.error('Failed to generate weekly reports:', error);
            }
        });

        // Monthly safety audits
        cron.schedule('0 2 1 * *', async () => {
            try {
                await this.performMonthlySecurityAudit();
                this.logger.info('Monthly security audit completed');
            } catch (error) {
                this.logger.error('Failed to perform security audit:', error);
            }
        });
    }

    async performMonthlySecurityAudit() {
        // Comprehensive security audit
        const auditResults = {
            timestamp: new Date(),
            userAccounts: await this.auditUserAccounts(),
            connections: await this.auditConnections(),
            content: await this.auditContent(),
            incidents: await this.auditIncidents()
        };

        this.logger.info('Security audit results:', auditResults);
        return auditResults;
    }

    async start() {
        try {
            await this.initialize();
            
            this.server.listen(this.port, () => {
                this.logger.info(`Kids Connect Safety System running on port ${this.port}`, {
                    environment: process.env.NODE_ENV || 'development',
                    version: process.env.npm_package_version || '1.0.0'
                });
            });

            // Graceful shutdown
            process.on('SIGTERM', () => this.shutdown());
            process.on('SIGINT', () => this.shutdown());
            
        } catch (error) {
            this.logger.error('Failed to start server:', error);
            process.exit(1);
        }
    }

    async shutdown() {
        this.logger.info('Shutting down Kids Connect Safety System...');
        
        try {
            // Close server connections
            this.server.close();
            
            // Close Redis connection
            if (this.redisClient) {
                await this.redisClient.disconnect();
            }
            
            this.logger.info('Shutdown complete');
            process.exit(0);
        } catch (error) {
            this.logger.error('Error during shutdown:', error);
            process.exit(1);
        }
    }
}

// Start the server
if (require.main === module) {
    const server = new KidsConnectServer();
    server.start();
}

module.exports = KidsConnectServer;