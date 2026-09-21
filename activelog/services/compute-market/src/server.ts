import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import path from 'path';
import { fileURLToPath } from 'url';

// Import all system components
import ComputeDetector from './detection/compute-detector.js';
import ComputeIsolationManager from './isolation/compute-isolation.js';
import PricingAlgorithm from './pricing/pricing-algorithm.js';
import ReputationSystem from './reputation/reputation-system.js';
import PaymentProcessor from './payment/payment-processor.js';
import JobDistributionSystem from './distribution/job-distribution.js';
import PerformanceMonitor from './monitoring/performance-monitor.js';
import SLAManager from './sla/sla-management.js';
import DeveloperMarketplace from './marketplace/developer-marketplace.js';
import PlugAndPlaySetup from './setup/plug-and-play-setup.js';

// Types for the integrated system
interface ComputeMarketConfig {
  port: number;
  host: string;
  environment: 'development' | 'production' | 'test';
  database: {
    url: string;
    options?: Record<string, any>;
  };
  redis: {
    url: string;
    options?: Record<string, any>;
  };
  security: {
    jwtSecret: string;
    apiKeys: string[];
    corsOrigins: string[];
  };
  monitoring: {
    enabled: boolean;
    metricsPort: number;
    alerting: {
      email?: string;
      webhook?: string;
    };
  };
  features: {
    autoDiscovery: boolean;
    autoScaling: boolean;
    developmentMode: boolean;
  };
}

interface SystemComponents {
  detector: ComputeDetector;
  isolation: ComputeIsolationManager;
  pricing: PricingAlgorithm;
  reputation: ReputationSystem;
  payments: PaymentProcessor;
  distribution: JobDistributionSystem;
  monitoring: PerformanceMonitor;
  sla: SLAManager;
  marketplace: DeveloperMarketplace;
  setup: PlugAndPlaySetup;
}

// Mock metrics database for demonstration
class MockMetricsDatabase {
  private data = new Map();

  async store(metrics: any): Promise<void> {
    const key = `${metrics.nodeId}_${metrics.timestamp.getTime()}`;
    this.data.set(key, metrics);
  }

  async query(nodeId: string, startTime: Date, endTime: Date, metrics?: string[]): Promise<any[]> {
    const results = [];
    for (const [key, value] of this.data.entries()) {
      if (key.startsWith(nodeId) && 
          value.timestamp >= startTime && 
          value.timestamp <= endTime) {
        results.push(value);
      }
    }
    return results;
  }

  async aggregate(nodeId: string, interval: string, startTime: Date, endTime: Date): Promise<any[]> {
    return await this.query(nodeId, startTime, endTime);
  }

  async cleanup(olderThan: Date): Promise<number> {
    let deleted = 0;
    for (const [key, value] of this.data.entries()) {
      if (value.timestamp < olderThan) {
        this.data.delete(key);
        deleted++;
      }
    }
    return deleted;
  }
}

// Mock metrics provider for SLA
class MockMetricsProvider {
  async query(source: string, params: any): Promise<{ value: number; timestamp: Date }> {
    // Simulate realistic metrics
    return {
      value: 95 + Math.random() * 5, // 95-100% uptime simulation
      timestamp: new Date()
    };
  }
}

class ComputeMarketServer {
  private app: express.Application;
  private server: any;
  private io: SocketIOServer;
  private config: ComputeMarketConfig;
  private components: SystemComponents;
  private isStarted = false;

  constructor(config: ComputeMarketConfig) {
    this.config = config;
    this.app = express();
    this.server = createServer(this.app);
    this.io = new SocketIOServer(this.server, {
      cors: {
        origin: config.security.corsOrigins,
        methods: ['GET', 'POST']
      }
    });

    // Initialize all system components
    this.initializeComponents();
    this.setupMiddleware();
    this.setupRoutes();
    this.setupWebSocket();
    this.setupEventHandlers();
  }

  private initializeComponents(): void {
    console.log('🔧 Initializing compute market components...');

    // Initialize core systems
    this.components = {
      detector: new ComputeDetector(),
      isolation: new ComputeIsolationManager(),
      pricing: new PricingAlgorithm(),
      reputation: new ReputationSystem(),
      payments: new PaymentProcessor(),
      distribution: new JobDistributionSystem(),
      monitoring: new PerformanceMonitor(new MockMetricsDatabase()),
      sla: new SLAManager(new MockMetricsProvider()),
      marketplace: new DeveloperMarketplace(),
      setup: new PlugAndPlaySetup()
    };

    console.log('✅ All components initialized successfully');
  }

  private setupMiddleware(): void {
    // Security middleware
    this.app.use(helmet());
    this.app.use(cors({
      origin: this.config.security.corsOrigins,
      credentials: true
    }));

    // General middleware
    this.app.use(compression());
    this.app.use(express.json({ limit: '50mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '50mb' }));

    // Request logging
    this.app.use((req, res, next) => {
      console.log(`${req.method} ${req.path} - ${req.ip}`);
      next();
    });
  }

  private setupRoutes(): void {
    // Health check endpoint
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date(),
        version: '1.0.0',
        components: {
          detector: 'running',
          isolation: 'running',
          pricing: 'running',
          reputation: 'running',
          payments: 'running',
          distribution: 'running',
          monitoring: 'running',
          sla: 'running',
          marketplace: 'running',
          setup: 'running'
        }
      });
    });

    // System info endpoint
    this.app.get('/api/system/info', async (req, res) => {
      try {
        const systemInfo = await this.components.setup.getSystemInfo();
        res.json(systemInfo);
      } catch (error) {
        res.status(500).json({ error: 'Failed to get system info' });
      }
    });

    // Compute detection endpoints
    this.app.get('/api/compute/capacity', async (req, res) => {
      try {
        const capacity = await this.components.detector.detectLocalCapacity();
        res.json(capacity);
      } catch (error) {
        res.status(500).json({ error: 'Failed to detect compute capacity' });
      }
    });

    this.app.post('/api/compute/scan', async (req, res) => {
      try {
        await this.components.detector.scanForComputeResources();
        const nodes = this.components.detector.getDetectedNodes();
        res.json({ message: 'Scan initiated', nodes: Array.from(nodes.values()) });
      } catch (error) {
        res.status(500).json({ error: 'Failed to scan for compute resources' });
      }
    });

    // Job distribution endpoints
    this.app.post('/api/jobs', async (req, res) => {
      try {
        const jobId = await this.components.distribution.submitJob(req.body);
        res.json({ jobId, message: 'Job submitted successfully' });
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    this.app.get('/api/jobs/:jobId', (req, res) => {
      const job = this.components.distribution.getJob(req.params.jobId);
      if (!job) {
        return res.status(404).json({ error: 'Job not found' });
      }
      res.json(job);
    });

    this.app.get('/api/jobs/:jobId/matches', (req, res) => {
      const matches = this.components.distribution.getJobMatches(req.params.jobId);
      res.json(matches);
    });

    // Provider registration endpoints
    this.app.post('/api/providers', async (req, res) => {
      try {
        const providerId = await this.components.distribution.registerProvider(req.body);
        res.json({ providerId, message: 'Provider registered successfully' });
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    this.app.put('/api/providers/:providerId/status', async (req, res) => {
      try {
        await this.components.distribution.updateProviderStatus(req.params.providerId, req.body.status);
        res.json({ message: 'Provider status updated' });
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    // Pricing endpoints
    this.app.post('/api/pricing/quote', async (req, res) => {
      try {
        const quote = await this.components.pricing.calculatePrice(req.body.resource, req.body.duration);
        res.json(quote);
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    this.app.post('/api/pricing/bulk-quote', async (req, res) => {
      try {
        const quotes = await this.components.pricing.getBulkPricing(req.body.resources, req.body.duration);
        res.json(quotes);
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    // Reputation endpoints
    this.app.post('/api/users/:userId/reputation/init', async (req, res) => {
      try {
        await this.components.reputation.initializeUser(req.params.userId, req.body);
        res.json({ message: 'User reputation initialized' });
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    this.app.get('/api/users/:userId/reputation', (req, res) => {
      const score = this.components.reputation.getUserScore(req.params.userId);
      const profile = this.components.reputation.getUserProfile(req.params.userId);
      const metrics = this.components.reputation.getUserMetrics(req.params.userId);
      
      if (!score) {
        return res.status(404).json({ error: 'User not found' });
      }
      
      res.json({ score, profile, metrics });
    });

    this.app.post('/api/users/:userId/reputation/event', async (req, res) => {
      try {
        await this.components.reputation.recordEvent({
          userId: req.params.userId,
          ...req.body
        });
        res.json({ message: 'Reputation event recorded' });
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    // Payment endpoints
    this.app.post('/api/payments/methods', async (req, res) => {
      try {
        const methodId = await this.components.payments.addPaymentMethod(req.body.userId, req.body.method);
        res.json({ methodId, message: 'Payment method added' });
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    this.app.post('/api/payments/intent', async (req, res) => {
      try {
        const intent = await this.components.payments.createPaymentIntent(
          req.body.payerId,
          req.body.amount,
          req.body.currency,
          req.body.options
        );
        res.json(intent);
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    this.app.post('/api/payments/:intentId/process', async (req, res) => {
      try {
        const transaction = await this.components.payments.processPayment(req.params.intentId, req.body.jobId);
        res.json(transaction);
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    // Marketplace endpoints
    this.app.post('/api/marketplace/boxes', async (req, res) => {
      try {
        const boxId = await this.components.marketplace.publishBox(req.body);
        res.json({ boxId, message: 'Developer box published' });
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    this.app.get('/api/marketplace/boxes/search', async (req, res) => {
      try {
        const results = await this.components.marketplace.searchBoxes(req.query);
        res.json(results);
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    this.app.get('/api/marketplace/boxes/:boxId', async (req, res) => {
      const box = await this.components.marketplace.getBox(req.params.boxId);
      if (!box) {
        return res.status(404).json({ error: 'Box not found' });
      }
      res.json(box);
    });

    this.app.post('/api/marketplace/orders', async (req, res) => {
      try {
        const orderId = await this.components.marketplace.orderBox(req.body);
        res.json({ orderId, message: 'Box ordered successfully' });
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    // Setup endpoints
    this.app.get('/api/setup/configurations', (req, res) => {
      const configurations = this.components.setup.getAllConfigurations();
      res.json(configurations);
    });

    this.app.post('/api/setup/:configId/validate', async (req, res) => {
      try {
        const validation = await this.components.setup.validateSystem(req.params.configId);
        res.json(validation);
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    this.app.post('/api/setup/:configId/start', async (req, res) => {
      try {
        const setupId = await this.components.setup.startSetup(req.params.configId, req.body.settings);
        res.json({ setupId, message: 'Setup started' });
      } catch (error) {
        res.status(400).json({ error: (error as Error).message });
      }
    });

    this.app.get('/api/setup/:setupId/progress', (req, res) => {
      const progress = this.components.setup.getSetupProgress(req.params.setupId);
      if (!progress) {
        return res.status(404).json({ error: 'Setup not found' });
      }
      res.json(progress);
    });

    // Queue status endpoint
    this.app.get('/api/queue/status', (req, res) => {
      const status = this.components.distribution.getQueueStatus();
      res.json(status);
    });

    // Metrics endpoint
    this.app.get('/api/metrics', (req, res) => {
      const metrics = {
        timestamp: new Date(),
        system: {
          uptime: process.uptime(),
          memory: process.memoryUsage(),
          cpu: process.cpuUsage()
        },
        components: {
          jobs: {
            queued: Object.values(this.components.distribution.getQueueStatus()).reduce((sum, count) => sum + count, 0)
          }
        }
      };
      res.json(metrics);
    });

    // Catch-all for API routes
    this.app.use('/api/*', (req, res) => {
      res.status(404).json({ error: 'API endpoint not found' });
    });

    // Serve static files in production
    if (this.config.environment === 'production') {
      const __filename = fileURLToPath(import.meta.url);
      const __dirname = path.dirname(__filename);
      
      this.app.use(express.static(path.join(__dirname, '../public')));
      
      // Catch-all handler for client-side routing
      this.app.get('*', (req, res) => {
        res.sendFile(path.join(__dirname, '../public/index.html'));
      });
    }

    // Global error handler
    this.app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
      console.error('Server error:', err);
      res.status(500).json({
        error: 'Internal server error',
        message: this.config.environment === 'development' ? err.message : undefined
      });
    });
  }

  private setupWebSocket(): void {
    this.io.on('connection', (socket) => {
      console.log(`🔌 Client connected: ${socket.id}`);

      // Join rooms based on user interests
      socket.on('join', (data) => {
        const { room, userId } = data;
        socket.join(room);
        socket.data.userId = userId;
        console.log(`User ${userId} joined room: ${room}`);
      });

      // Real-time job updates
      socket.on('subscribe-job', (jobId) => {
        socket.join(`job_${jobId}`);
      });

      // Real-time setup progress
      socket.on('subscribe-setup', (setupId) => {
        socket.join(`setup_${setupId}`);
      });

      // Real-time marketplace updates
      socket.on('subscribe-marketplace', () => {
        socket.join('marketplace_updates');
      });

      socket.on('disconnect', () => {
        console.log(`🔌 Client disconnected: ${socket.id}`);
      });
    });
  }

  private setupEventHandlers(): void {
    console.log('📡 Setting up event handlers...');

    // Job distribution events
    this.components.distribution.on('jobSubmitted', (job) => {
      this.io.to('general').emit('job_submitted', job);
    });

    this.components.distribution.on('jobAssigned', (job, provider) => {
      this.io.to(`job_${job.id}`).emit('job_assigned', { job, provider });
    });

    this.components.distribution.on('jobCompleted', (job) => {
      this.io.to(`job_${job.id}`).emit('job_completed', job);
    });

    // Setup events
    this.components.setup.on('setupStarted', (setupId, progress) => {
      this.io.to(`setup_${setupId}`).emit('setup_started', progress);
    });

    this.components.setup.on('stepCompleted', (setupId, step) => {
      this.io.to(`setup_${setupId}`).emit('step_completed', step);
    });

    this.components.setup.on('setupCompleted', (setupId, progress) => {
      this.io.to(`setup_${setupId}`).emit('setup_completed', progress);
    });

    // Marketplace events
    this.components.marketplace.on('boxPublished', (box) => {
      this.io.to('marketplace_updates').emit('box_published', box);
    });

    this.components.marketplace.on('boxDeployed', (order) => {
      this.io.to('marketplace_updates').emit('box_deployed', order);
    });

    // Reputation events
    this.components.reputation.on('reputationEvent', (event) => {
      this.io.to(`user_${event.userId}`).emit('reputation_event', event);
    });

    // Payment events
    this.components.payments.on('paymentCompleted', (transaction) => {
      this.io.to(`user_${transaction.payerId}`).emit('payment_completed', transaction);
    });

    // Performance monitoring events
    this.components.monitoring.on('alertTriggered', (alert) => {
      this.io.to('admins').emit('performance_alert', alert);
    });

    console.log('✅ Event handlers configured');
  }

  public async start(): Promise<void> {
    if (this.isStarted) {
      console.log('⚠️  Server is already running');
      return;
    }

    try {
      // Start all components
      console.log('🚀 Starting compute market server...');
      
      // Initialize auto-discovery if enabled
      if (this.config.features.autoDiscovery) {
        console.log('🔍 Starting auto-discovery...');
        await this.components.detector.scanForComputeResources();
      }

      // Start the HTTP server
      await new Promise<void>((resolve) => {
        this.server.listen(this.config.port, this.config.host, () => {
          console.log(`\n🎉 Compute Market Server is running!`);
          console.log(`📡 API Server: http://${this.config.host}:${this.config.port}`);
          console.log(`🌐 WebSocket: ws://${this.config.host}:${this.config.port}`);
          console.log(`📊 Health Check: http://${this.config.host}:${this.config.port}/health`);
          console.log(`📈 Metrics: http://${this.config.host}:${this.config.port}/api/metrics`);
          console.log(`\n🔧 Available Features:`);
          console.log(`  • Spare Compute Detection`);
          console.log(`  • Secure Compute Isolation`);
          console.log(`  • Dynamic Pricing Algorithm`);
          console.log(`  • Reputation System`);
          console.log(`  • Payment Processing`);
          console.log(`  • Job Distribution`);
          console.log(`  • Performance Monitoring`);
          console.log(`  • SLA Management`);
          console.log(`  • Developer Box Marketplace`);
          console.log(`  • Plug-and-Play Setup`);
          console.log(`\n✨ Ready to trade compute resources!`);
          
          this.isStarted = true;
          resolve();
        });
      });

    } catch (error) {
      console.error('❌ Failed to start server:', error);
      throw error;
    }
  }

  public async stop(): Promise<void> {
    if (!this.isStarted) {
      return;
    }

    console.log('🛑 Shutting down compute market server...');

    // Stop all components
    this.components.detector.stop();
    this.components.pricing.stop();
    this.components.reputation.stop();
    this.components.payments.stop();
    this.components.distribution.stop();
    this.components.monitoring.stop();
    this.components.sla.stop();

    // Close server
    await new Promise<void>((resolve) => {
      this.server.close(() => {
        console.log('✅ Server shut down successfully');
        this.isStarted = false;
        resolve();
      });
    });
  }

  public getComponents(): SystemComponents {
    return this.components;
  }

  public getApp(): express.Application {
    return this.app;
  }
}

// Default configuration
const defaultConfig: ComputeMarketConfig = {
  port: 8310,
  host: '0.0.0.0',
  environment: (process.env.NODE_ENV as any) || 'development',
  database: {
    url: process.env.DATABASE_URL || 'sqlite:./compute_market.db'
  },
  redis: {
    url: process.env.REDIS_URL || 'redis://localhost:6379'
  },
  security: {
    jwtSecret: process.env.JWT_SECRET || 'compute-market-secret-key',
    apiKeys: process.env.API_KEYS?.split(',') || [],
    corsOrigins: process.env.CORS_ORIGINS?.split(',') || ['http://localhost:3000', 'http://localhost:8310']
  },
  monitoring: {
    enabled: true,
    metricsPort: 8313,
    alerting: {
      email: process.env.ALERT_EMAIL,
      webhook: process.env.ALERT_WEBHOOK
    }
  },
  features: {
    autoDiscovery: process.env.AUTO_DISCOVERY === 'true',
    autoScaling: process.env.AUTO_SCALING === 'true',
    developmentMode: process.env.NODE_ENV === 'development'
  }
};

// Create and export server instance
const server = new ComputeMarketServer(defaultConfig);

// Graceful shutdown handling
process.on('SIGTERM', async () => {
  console.log('📟 Received SIGTERM, shutting down gracefully...');
  await server.stop();
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('📟 Received SIGINT, shutting down gracefully...');
  await server.stop();
  process.exit(0);
});

// Start server if this file is run directly
if (import.meta.url === `file://${process.argv[1]}`) {
  server.start().catch((error) => {
    console.error('💥 Failed to start server:', error);
    process.exit(1);
  });
}

export { ComputeMarketServer, ComputeMarketConfig, SystemComponents };
export default server;