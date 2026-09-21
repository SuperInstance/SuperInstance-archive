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
import { PayToPlayService } from './services/pay-to-play.js';
import { CoffeePromptService } from './services/coffee-prompts.js';
import { TieredAccessService } from './services/tiered-access.js';
import { IPLicensingService } from './services/ip-licensing.js';
import { RevenueShareService } from './services/revenue-share.js';
import { ContentAgingService } from './services/content-aging.js';
import { DonationService } from './services/donations.js';
import { SubscriptionService } from './services/subscriptions.js';
import { DigitalOwnershipService } from './services/digital-ownership.js';
import { RoyaltyService } from './services/royalties.js';
import { ValuationService } from './services/valuation.js';
import { AnalyticsService } from './services/analytics.js';

// Import API routes
import payToPlayRoutes from './routes/pay-to-play.js';
import coffeePromptRoutes from './routes/coffee-prompts.js';
import tieredAccessRoutes from './routes/tiered-access.js';
import ipLicensingRoutes from './routes/ip-licensing.js';
import revenueShareRoutes from './routes/revenue-share.js';
import contentAgingRoutes from './routes/content-aging.js';
import donationRoutes from './routes/donations.js';
import subscriptionRoutes from './routes/subscriptions.js';
import digitalOwnershipRoutes from './routes/digital-ownership.js';
import royaltyRoutes from './routes/royalties.js';
import valuationRoutes from './routes/valuation.js';
import analyticsRoutes from './routes/analytics.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class ContentEconomyServer {
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
        
        this.port = process.env.PORT || 8328;
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
            defaultMeta: { service: 'content-economy' },
            transports: [
                new winston.transports.Console({
                    format: winston.format.combine(
                        winston.format.colorize(),
                        winston.format.simple()
                    )
                }),
                new DailyRotateFile({
                    filename: 'logs/content-economy-%DATE%.log',
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
            max: 100, // Limit each IP to 100 requests per windowMs
            message: 'Too many requests from this IP'
        });
        this.app.use('/api/', limiter);

        // Body parsing
        this.app.use(express.json({ limit: '10mb' }));
        this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));
        
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
            secret: process.env.SESSION_SECRET || 'content-economy-secret',
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
        // Initialize all content economy services
        this.services = {
            payToPlay: new PayToPlayService(this.redis, this.logger),
            coffeePrompts: new CoffeePromptService(this.redis, this.logger),
            tieredAccess: new TieredAccessService(this.redis, this.logger),
            ipLicensing: new IPLicensingService(this.redis, this.logger),
            revenueShare: new RevenueShareService(this.redis, this.logger),
            contentAging: new ContentAgingService(this.redis, this.logger),
            donations: new DonationService(this.redis, this.logger),
            subscriptions: new SubscriptionService(this.redis, this.logger),
            digitalOwnership: new DigitalOwnershipService(this.redis, this.logger),
            royalties: new RoyaltyService(this.redis, this.logger),
            valuation: new ValuationService(this.redis, this.logger),
            analytics: new AnalyticsService(this.redis, this.logger)
        };

        // Start service schedulers
        Object.values(this.services).forEach(service => {
            if (service.startScheduler) {
                service.startScheduler();
            }
        });

        this.logger.info('Content Economy services initialized');
    }

    setupRoutes() {
        // Health check
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                service: 'content-economy',
                version: '1.0.0'
            });
        });

        // API routes
        this.app.use('/api/pay-to-play', payToPlayRoutes(this.services.payToPlay));
        this.app.use('/api/coffee-prompts', coffeePromptRoutes(this.services.coffeePrompts));
        this.app.use('/api/tiered-access', tieredAccessRoutes(this.services.tieredAccess));
        this.app.use('/api/ip-licensing', ipLicensingRoutes(this.services.ipLicensing));
        this.app.use('/api/revenue-share', revenueShareRoutes(this.services.revenueShare));
        this.app.use('/api/content-aging', contentAgingRoutes(this.services.contentAging));
        this.app.use('/api/donations', donationRoutes(this.services.donations));
        this.app.use('/api/subscriptions', subscriptionRoutes(this.services.subscriptions));
        this.app.use('/api/digital-ownership', digitalOwnershipRoutes(this.services.digitalOwnership));
        this.app.use('/api/royalties', royaltyRoutes(this.services.royalties));
        this.app.use('/api/valuation', valuationRoutes(this.services.valuation));
        this.app.use('/api/analytics', analyticsRoutes(this.services.analytics));

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
                    server: 'Content Economy Service',
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
                    '/api/pay-to-play',
                    '/api/coffee-prompts',
                    '/api/tiered-access',
                    '/api/ip-licensing',
                    '/api/revenue-share',
                    '/api/content-aging',
                    '/api/donations',
                    '/api/subscriptions',
                    '/api/digital-ownership',
                    '/api/royalties',
                    '/api/valuation',
                    '/api/analytics'
                ]
            });
        });
    }

    setupWebSocket() {
        this.io.on('connection', (socket) => {
            this.logger.info(`Client connected: ${socket.id}`);

            socket.on('subscribe-analytics', (contentId) => {
                socket.join(`analytics-${contentId}`);
                this.logger.info(`Client ${socket.id} subscribed to analytics for ${contentId}`);
            });

            socket.on('subscribe-earnings', (creatorId) => {
                socket.join(`earnings-${creatorId}`);
                this.logger.info(`Client ${socket.id} subscribed to earnings for ${creatorId}`);
            });

            socket.on('subscribe-donations', (creatorId) => {
                socket.join(`donations-${creatorId}`);
                this.logger.info(`Client ${socket.id} subscribed to donations for ${creatorId}`);
            });

            socket.on('subscribe-subscriptions', (creatorId) => {
                socket.join(`subscriptions-${creatorId}`);
                this.logger.info(`Client ${socket.id} subscribed to subscriptions for ${creatorId}`);
            });

            socket.on('disconnect', () => {
                this.logger.info(`Client disconnected: ${socket.id}`);
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
                this.logger.info(`Content Economy Service running on port ${this.port}`);
                this.logger.info('Available services:', Object.keys(this.services));
            });

        } catch (error) {
            this.logger.error('Failed to start server:', error);
            process.exit(1);
        }
    }

    async stop() {
        this.logger.info('Shutting down Content Economy Service...');
        
        // Stop all service schedulers
        Object.values(this.services).forEach(service => {
            if (service.stopScheduler) {
                service.stopScheduler();
            }
        });

        // Close connections
        await this.redis.quit();
        this.server.close(() => {
            this.logger.info('Content Economy Service stopped');
            process.exit(0);
        });
    }
}

// Start the server
const server = new ContentEconomyServer();
await server.start();

// Graceful shutdown
process.on('SIGTERM', () => server.stop());
process.on('SIGINT', () => server.stop());

export default ContentEconomyServer;