import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import Redis from 'ioredis';
import winston from 'winston';
import DailyRotateFile from 'winston-daily-rotate-file';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import session from 'express-session';
import ConnectRedis from 'connect-redis';

// Import service modules
import { EnterprisePricingService } from './services/enterprise-pricing.js';
import { PayAsYouGoService } from './services/pay-as-you-go.js';
import { NonprofitPricingService } from './services/nonprofit-pricing.js';
import { BulkMembershipService } from './services/bulk-membership.js';
import { BudgetAllocationService } from './services/budget-allocation.js';
import { UsageTrackingService } from './services/usage-tracking.js';
import { ComplianceReportingService } from './services/compliance-reporting.js';
import { SSOService } from './services/sso.js';
import { RoleBasedLimitsService } from './services/role-based-limits.js';
import { OrganizationAnalyticsService } from './services/organization-analytics.js';
import { ChargebackService } from './services/chargeback.js';
import { InvoiceAutomationService } from './services/invoice-automation.js';

// Import API routes
import { createEnterprisePricingRoutes } from './routes/enterprise-pricing.js';
import { createPayAsYouGoRoutes } from './routes/pay-as-you-go.js';
import { createNonprofitPricingRoutes } from './routes/nonprofit-pricing.js';
import { createBulkMembershipRoutes } from './routes/bulk-membership.js';
import { createBudgetAllocationRoutes } from './routes/budget-allocation.js';
import { createUsageTrackingRoutes } from './routes/usage-tracking.js';
import { createComplianceReportingRoutes } from './routes/compliance-reporting.js';
import { createSSORoutes } from './routes/sso.js';
import { createRoleBasedLimitsRoutes } from './routes/role-based-limits.js';
import { createOrganizationAnalyticsRoutes } from './routes/organization-analytics.js';
import { createChargebackRoutes } from './routes/chargeback.js';
import { createInvoiceAutomationRoutes } from './routes/invoice-automation.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class OrganizationTiersServer {
    constructor() {
        this.app = express();
        this.server = createServer(this.app);
        this.io = new SocketIOServer(this.server, {
            cors: {
                origin: process.env.FRONTEND_URLS?.split(',') || ['http://localhost:3000'],
                methods: ['GET', 'POST'],
                credentials: true
            }
        });
        
        this.port = process.env.PORT || 8329;
        this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
        
        this.setupLogging();
        this.setupMiddleware();
        this.setupServices();
        this.setupRoutes();
        this.setupWebSocket();
        this.setupErrorHandling();
    }

    setupLogging() {
        this.logger = winston.createLogger({
            level: process.env.LOG_LEVEL || 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json()
            ),
            defaultMeta: { service: 'org-tiers' },
            transports: [
                new winston.transports.Console({
                    format: winston.format.combine(
                        winston.format.colorize(),
                        winston.format.simple()
                    )
                }),
                new DailyRotateFile({
                    filename: 'logs/org-tiers-%DATE%.log',
                    datePattern: 'YYYY-MM-DD',
                    zippedArchive: true,
                    maxSize: '20m',
                    maxFiles: '14d'
                })
            ]
        });
    }

    setupMiddleware() {
        // Security
        this.app.use(helmet({
            crossOriginEmbedderPolicy: false,
            contentSecurityPolicy: {
                directives: {
                    defaultSrc: ["'self'"],
                    styleSrc: ["'self'", "'unsafe-inline'"],
                    scriptSrc: ["'self'"],
                    imgSrc: ["'self'", "data:", "https:"],
                    connectSrc: ["'self'", "ws:", "wss:"]
                }
            }
        }));

        // CORS
        this.app.use(cors({
            origin: process.env.FRONTEND_URLS?.split(',') || ['http://localhost:3000'],
            credentials: true
        }));

        // Rate limiting
        const limiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: 200, // Higher limit for enterprise use
            message: 'Too many requests from this IP'
        });
        this.app.use('/api/', limiter);

        // Body parsing
        this.app.use(express.json({ limit: '50mb' })); // Larger for enterprise
        this.app.use(express.urlencoded({ extended: true, limit: '50mb' }));
        
        // Compression
        this.app.use(compression());
        
        // Logging
        this.app.use(morgan('combined', {
            stream: { write: (message) => this.logger.info(message.trim()) }
        }));

        // Session management
        const RedisStore = new ConnectRedis({
            client: this.redis
        });
        this.app.use(session({
            store: RedisStore,
            secret: process.env.SESSION_SECRET || 'org-tiers-secret',
            resave: false,
            saveUninitialized: false,
            cookie: {
                secure: process.env.NODE_ENV === 'production',
                httpOnly: true,
                maxAge: 24 * 60 * 60 * 1000 // 24 hours
            }
        }));
    }

    setupServices() {
        // Initialize all organization tier services
        this.services = {
            enterprisePricing: new EnterprisePricingService(this.redis, this.logger),
            payAsYouGo: new PayAsYouGoService(this.redis, this.logger),
            nonprofitPricing: new NonprofitPricingService(this.redis, this.logger),
            bulkMembership: new BulkMembershipService(this.redis, this.logger),
            budgetAllocation: new BudgetAllocationService(this.redis, this.logger),
            usageTracking: new UsageTrackingService(this.redis, this.logger),
            complianceReporting: new ComplianceReportingService(this.redis, this.logger),
            sso: new SSOService(this.redis, this.logger),
            roleBasedLimits: new RoleBasedLimitsService(this.redis, this.logger),
            organizationAnalytics: new OrganizationAnalyticsService(this.redis, this.logger),
            chargeback: new ChargebackService(this.redis, this.logger),
            invoiceAutomation: new InvoiceAutomationService(this.redis, this.logger)
        };

        // Start service schedulers
        Object.values(this.services).forEach(service => {
            if (service.startScheduler) {
                service.startScheduler();
            }
        });

        this.logger.info('Organization Tiers services initialized');
    }

    setupRoutes() {
        // Health check
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                service: 'org-tiers',
                version: '1.0.0'
            });
        });

        // API routes
        this.app.use('/api/enterprise-pricing', createEnterprisePricingRoutes(this.services.enterprisePricing));
        this.app.use('/api/pay-as-you-go', createPayAsYouGoRoutes(this.services.payAsYouGo));
        this.app.use('/api/nonprofit-pricing', createNonprofitPricingRoutes(this.services.nonprofitPricing));
        this.app.use('/api/bulk-membership', createBulkMembershipRoutes(this.services.bulkMembership));
        this.app.use('/api/budget-allocation', createBudgetAllocationRoutes(this.services.budgetAllocation));
        this.app.use('/api/usage-tracking', createUsageTrackingRoutes(this.services.usageTracking));
        this.app.use('/api/compliance-reporting', createComplianceReportingRoutes(this.services.complianceReporting));
        this.app.use('/api/sso', createSSORoutes(this.services.sso));
        this.app.use('/api/role-based-limits', createRoleBasedLimitsRoutes(this.services.roleBasedLimits));
        this.app.use('/api/organization-analytics', createOrganizationAnalyticsRoutes(this.services.organizationAnalytics));
        this.app.use('/api/chargeback', createChargebackRoutes(this.services.chargeback));
        this.app.use('/api/invoice-automation', createInvoiceAutomationRoutes(this.services.invoiceAutomation));

        // Service status endpoint
        this.app.get('/api/status', async (req, res) => {
            try {
                const serviceStatuses = {};
                
                for (const [name, service] of Object.entries(this.services)) {
                    serviceStatuses[name] = {
                        active: service.isActive || true,
                        lastActivity: service.lastActivity || new Date().toISOString(),
                        stats: await service.getStats?.() || {}
                    };
                }

                res.json({
                    server: 'Organization Tiers Service',
                    status: 'operational',
                    services: serviceStatuses,
                    timestamp: new Date().toISOString()
                });
            } catch (error) {
                this.logger.error('Status check failed:', error);
                res.status(500).json({ error: 'Status check failed' });
            }
        });

        // 404 handler
        this.app.use('*', (req, res) => {
            res.status(404).json({
                error: 'Not Found',
                message: 'The requested endpoint does not exist',
                availableEndpoints: [
                    '/health',
                    '/api/status',
                    '/api/enterprise-pricing',
                    '/api/pay-as-you-go',
                    '/api/nonprofit-pricing',
                    '/api/bulk-membership',
                    '/api/budget-allocation',
                    '/api/usage-tracking',
                    '/api/compliance-reporting',
                    '/api/sso',
                    '/api/role-based-limits',
                    '/api/organization-analytics',
                    '/api/chargeback',
                    '/api/invoice-automation'
                ]
            });
        });
    }

    setupWebSocket() {
        this.io.on('connection', (socket) => {
            this.logger.info(`Organization client connected: ${socket.id}`);

            socket.on('subscribe-org-analytics', (orgId) => {
                socket.join(`org-analytics-${orgId}`);
                this.logger.info(`Client ${socket.id} subscribed to analytics for org ${orgId}`);
            });

            socket.on('subscribe-usage-alerts', (orgId) => {
                socket.join(`usage-alerts-${orgId}`);
                this.logger.info(`Client ${socket.id} subscribed to usage alerts for org ${orgId}`);
            });

            socket.on('subscribe-billing-updates', (orgId) => {
                socket.join(`billing-updates-${orgId}`);
                this.logger.info(`Client ${socket.id} subscribed to billing updates for org ${orgId}`);
            });

            socket.on('subscribe-compliance-alerts', (orgId) => {
                socket.join(`compliance-alerts-${orgId}`);
                this.logger.info(`Client ${socket.id} subscribed to compliance alerts for org ${orgId}`);
            });

            socket.on('disconnect', () => {
                this.logger.info(`Organization client disconnected: ${socket.id}`);
            });
        });

        // Broadcast real-time updates
        this.broadcastUpdate = (channel, data) => {
            this.io.to(channel).emit('update', data);
        };

        // Make broadcast available to services
        Object.values(this.services).forEach(service => {
            service.broadcast = this.broadcastUpdate;
        });
    }

    setupErrorHandling() {
        this.app.use((error, req, res, next) => {
            this.logger.error('Unhandled error:', error);
            
            res.status(error.status || 500).json({
                error: process.env.NODE_ENV === 'production' 
                    ? 'Internal Server Error' 
                    : error.message,
                timestamp: new Date().toISOString()
            });
        });

        process.on('unhandledRejection', (reason, promise) => {
            this.logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
        });

        process.on('uncaughtException', (error) => {
            this.logger.error('Uncaught Exception:', error);
            process.exit(1);
        });
    }

    async start() {
        try {
            // Test Redis connection
            await this.redis.ping();
            this.logger.info('Redis connection established');

            // Start server
            this.server.listen(this.port, () => {
                this.logger.info(`Organization Tiers Service running on port ${this.port}`);
                this.logger.info('Available services:', Object.keys(this.services));
            });

        } catch (error) {
            this.logger.error('Failed to start server:', error);
            process.exit(1);
        }
    }

    async stop() {
        this.logger.info('Shutting down Organization Tiers Service...');
        
        // Stop all service schedulers
        Object.values(this.services).forEach(service => {
            if (service.stopScheduler) {
                service.stopScheduler();
            }
        });

        // Close connections
        await this.redis.quit();
        this.server.close(() => {
            this.logger.info('Organization Tiers Service stopped');
            process.exit(0);
        });
    }
}

// Start the server
const server = new OrganizationTiersServer();
await server.start();

// Graceful shutdown
process.on('SIGTERM', () => server.stop());
process.on('SIGINT', () => server.stop());

export default OrganizationTiersServer;