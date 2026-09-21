import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import dotenv from 'dotenv';
import logger from './lib/logger.js';
import { APIWrapper } from './api-wrapper/APIWrapper.js';
import { AppAnalyzer } from './analyzers/AppAnalyzer.js';
import { DatabaseMigrator } from './database/DatabaseMigrator.js';
import { AIServiceIntegrator } from './ai-services/AIServiceIntegrator.js';
import { CloudStorageMigrator } from './storage/CloudStorageMigrator.js';
import { ComputeAugmentationService } from './compute/ComputeAugmentationService.js';
import { HybridOrchestrator } from './orchestrator/HybridOrchestrator.js';
import { ThrottlingController } from './throttling/ThrottlingController.js';
import { EdgeAIEnabler } from './edge/EdgeAIEnabler.js';
import { PaymentIntegrator } from './payments/PaymentIntegrator.js';
import { GradualMigrationManager } from './gradual/GradualMigrationManager.js';
import { RollbackManager } from './rollback/RollbackManager.js';
import path from 'path';

// Load environment variables
dotenv.config();

/**
 * Migration Toolkit Main Application
 * Comprehensive migration system for apps, databases, and AI services
 */
class MigrationToolkit {
  constructor() {
    this.app = express();
    this.port = process.env.PORT || 8317;
    this.isRunning = false;
    
    // Initialize services
    this.apiWrapper = null;
    this.appAnalyzer = null;
    this.databaseMigrator = null;
    this.aiIntegrator = null;
    this.storageMigrator = null;
    this.computeService = null;
    this.orchestrator = null;
    this.throttlingController = null;
    this.edgeEnabler = null;
    this.paymentIntegrator = null;
    this.gradualMigrator = null;
    this.rollbackManager = null;
    
    this.setupMiddleware();
    this.initializeServices();
    this.setupRoutes();
  }

  /**
   * Setup Express middleware
   */
  setupMiddleware() {
    this.app.use(helmet());
    this.app.use(cors());
    this.app.use(compression());
    this.app.use(express.json({ limit: '100mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '100mb' }));

    // Request logging
    this.app.use((req, res, next) => {
      logger.info(`${req.method} ${req.path}`, {
        ip: req.ip,
        userAgent: req.get('user-agent')
      });
      next();
    });
  }

  /**
   * Initialize all services
   */
  async initializeServices() {
    try {
      logger.info('Initializing Migration Toolkit services...');

      // API Wrapper for non-migrated apps
      this.apiWrapper = new APIWrapper({
        port: this.port + 1, // Run on port 8318
        enableMetrics: true,
        enableCaching: true,
        enableAuthentication: false // Disable for initial setup
      });

      // Application Analyzer
      this.appAnalyzer = new AppAnalyzer({
        scanDepth: 15,
        analyzeDockerfiles: true,
        analyzeKubernetesManifests: true,
        generateMigrationPlan: true
      });

      // Database Migrator
      this.databaseMigrator = new DatabaseMigrator({
        batchSize: 1000,
        enableCompression: true,
        validateData: true,
        createBackups: true
      });

      // AI Service Integrator
      this.aiIntegrator = new AIServiceIntegrator({
        enableCaching: true,
        enableMetrics: true,
        costTracking: true,
        fallbackProviders: ['anthropic', 'local']
      });

      // Cloud Storage Migrator
      this.storageMigrator = new CloudStorageMigrator({
        concurrency: 5,
        checksumValidation: true,
        enableDeduplication: true,
        progressReporting: true
      });

      // Compute Augmentation Service
      this.computeService = new ComputeAugmentationService({
        autoScaling: true,
        maxInstances: 10,
        costOptimization: true
      });

      // Hybrid Orchestrator
      this.orchestrator = new HybridOrchestrator({
        enableLoadBalancing: true,
        healthCheckInterval: 30000,
        failoverEnabled: true
      });

      // Throttling Controller
      this.throttlingController = new ThrottlingController({
        defaultLimits: {
          requests: 1000,
          compute: 100,
          storage: 1000000000 // 1GB
        }
      });

      // Edge AI Enabler
      this.edgeEnabler = new EdgeAIEnabler({
        autoDiscovery: true,
        modelOptimization: true
      });

      // Payment Integrator
      this.paymentIntegrator = new PaymentIntegrator({
        providers: ['stripe', 'paypal'],
        enableWebhooks: true
      });

      // Gradual Migration Manager
      this.gradualMigrator = new GradualMigrationManager({
        phaseValidation: true,
        rollbackOnFailure: true
      });

      // Rollback Manager
      this.rollbackManager = new RollbackManager({
        automaticSnapshots: true,
        retentionDays: 30
      });

      logger.info('All services initialized successfully');

    } catch (error) {
      logger.error('Failed to initialize services:', error);
      throw error;
    }
  }

  /**
   * Setup API routes
   */
  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
        services: {
          apiWrapper: this.apiWrapper ? 'initialized' : 'not_initialized',
          appAnalyzer: this.appAnalyzer ? 'initialized' : 'not_initialized',
          databaseMigrator: this.databaseMigrator ? 'initialized' : 'not_initialized',
          aiIntegrator: this.aiIntegrator ? 'initialized' : 'not_initialized',
          storageMigrator: this.storageMigrator ? 'initialized' : 'not_initialized',
          computeService: this.computeService ? 'initialized' : 'not_initialized',
          orchestrator: this.orchestrator ? 'initialized' : 'not_initialized',
          throttlingController: this.throttlingController ? 'initialized' : 'not_initialized',
          edgeEnabler: this.edgeEnabler ? 'initialized' : 'not_initialized',
          paymentIntegrator: this.paymentIntegrator ? 'initialized' : 'not_initialized',
          gradualMigrator: this.gradualMigrator ? 'initialized' : 'not_initialized',
          rollbackManager: this.rollbackManager ? 'initialized' : 'not_initialized'
        }
      });
    });

    // App Analysis Routes
    this.app.post('/api/analyze/application', async (req, res) => {
      try {
        const { projectPath, options } = req.body;
        const analysis = await this.appAnalyzer.analyzeApplication(projectPath, options);
        res.json(analysis);
      } catch (error) {
        logger.error('Application analysis failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // Database Migration Routes
    this.app.post('/api/migrate/database', async (req, res) => {
      try {
        const { sourceConfig, targetConfig, options } = req.body;
        const result = await this.databaseMigrator.migrateDatabase(sourceConfig, targetConfig, options);
        res.json(result);
      } catch (error) {
        logger.error('Database migration failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // AI Service Routes
    this.app.post('/api/ai/completion', async (req, res) => {
      try {
        const result = await this.aiIntegrator.generateCompletion(req.body);
        res.json(result);
      } catch (error) {
        logger.error('AI completion failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/ai/embeddings', async (req, res) => {
      try {
        const result = await this.aiIntegrator.generateEmbeddings(req.body);
        res.json(result);
      } catch (error) {
        logger.error('AI embeddings generation failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/ai/image', async (req, res) => {
      try {
        const result = await this.aiIntegrator.generateImage(req.body);
        res.json(result);
      } catch (error) {
        logger.error('AI image generation failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // Storage Migration Routes
    this.app.post('/api/migrate/storage', async (req, res) => {
      try {
        const result = await this.storageMigrator.migrateStorage(req.body);
        res.json(result);
      } catch (error) {
        logger.error('Storage migration failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/migrate/storage/:migrationId/status', (req, res) => {
      try {
        const status = this.storageMigrator.getMigrationStatus(req.params.migrationId);
        if (!status) {
          return res.status(404).json({ error: 'Migration not found' });
        }
        res.json(status);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    // Compute Augmentation Routes
    this.app.post('/api/compute/provision', async (req, res) => {
      try {
        const result = await this.computeService.provisionResources(req.body);
        res.json(result);
      } catch (error) {
        logger.error('Compute provisioning failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/compute/status', (req, res) => {
      try {
        const status = this.computeService.getStatus();
        res.json(status);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    // Orchestrator Routes
    this.app.post('/api/orchestrate/deploy', async (req, res) => {
      try {
        const result = await this.orchestrator.deployService(req.body);
        res.json(result);
      } catch (error) {
        logger.error('Service deployment failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/orchestrate/services', (req, res) => {
      try {
        const services = this.orchestrator.getServices();
        res.json(services);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    // Throttling Routes
    this.app.post('/api/throttle/limits', async (req, res) => {
      try {
        const { userId, limits } = req.body;
        await this.throttlingController.setLimits(userId, limits);
        res.json({ message: 'Limits updated successfully' });
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/throttle/usage/:userId', (req, res) => {
      try {
        const usage = this.throttlingController.getUsage(req.params.userId);
        res.json(usage);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    // Edge AI Routes
    this.app.post('/api/edge/deploy', async (req, res) => {
      try {
        const result = await this.edgeEnabler.deployModel(req.body);
        res.json(result);
      } catch (error) {
        logger.error('Edge deployment failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/edge/devices', (req, res) => {
      try {
        const devices = this.edgeEnabler.getEdgeDevices();
        res.json(devices);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    // Payment Routes
    this.app.post('/api/payments/create-intent', async (req, res) => {
      try {
        const result = await this.paymentIntegrator.createPaymentIntent(req.body);
        res.json(result);
      } catch (error) {
        logger.error('Payment intent creation failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/payments/webhook/:provider', async (req, res) => {
      try {
        await this.paymentIntegrator.handleWebhook(req.params.provider, req.body, req.headers);
        res.json({ received: true });
      } catch (error) {
        logger.error('Payment webhook failed:', error);
        res.status(400).json({ error: error.message });
      }
    });

    // Gradual Migration Routes
    this.app.post('/api/migrate/gradual/start', async (req, res) => {
      try {
        const result = await this.gradualMigrator.startMigration(req.body);
        res.json(result);
      } catch (error) {
        logger.error('Gradual migration start failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/migrate/gradual/:migrationId/next-phase', async (req, res) => {
      try {
        const result = await this.gradualMigrator.executeNextPhase(req.params.migrationId);
        res.json(result);
      } catch (error) {
        logger.error('Migration phase execution failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // Rollback Routes
    this.app.post('/api/rollback/create-snapshot', async (req, res) => {
      try {
        const result = await this.rollbackManager.createSnapshot(req.body);
        res.json(result);
      } catch (error) {
        logger.error('Snapshot creation failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.post('/api/rollback/restore/:snapshotId', async (req, res) => {
      try {
        const result = await this.rollbackManager.restoreSnapshot(req.params.snapshotId);
        res.json(result);
      } catch (error) {
        logger.error('Snapshot restoration failed:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // API Wrapper Management Routes
    this.app.post('/api/wrapper/services/register', async (req, res) => {
      try {
        await this.apiWrapper.registerService(req.body.name, req.body.config);
        res.json({ message: 'Service registered successfully' });
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/wrapper/stats', (req, res) => {
      try {
        const stats = this.apiWrapper.getStats();
        res.json(stats);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    // Statistics and Monitoring Routes
    this.app.get('/api/stats/overview', (req, res) => {
      try {
        const overview = {
          uptime: process.uptime(),
          memory: process.memoryUsage(),
          timestamp: new Date().toISOString(),
          services: {
            apiWrapper: this.apiWrapper?.getStats(),
            aiIntegrator: this.aiIntegrator?.getStats(),
            storageMigrator: this.storageMigrator?.getAllMigrations(),
            computeService: this.computeService?.getStatus(),
            orchestrator: this.orchestrator?.getStats(),
            throttling: this.throttlingController?.getGlobalStats(),
            edge: this.edgeEnabler?.getStats(),
            payments: this.paymentIntegrator?.getStats(),
            gradual: this.gradualMigrator?.getActiveMigrations(),
            rollback: this.rollbackManager?.getStats()
          }
        };
        res.json(overview);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });

    // Error handling middleware
    this.app.use((error, req, res, next) => {
      logger.error('Unhandled error:', error);
      res.status(500).json({
        error: 'Internal server error',
        message: error.message,
        timestamp: new Date().toISOString()
      });
    });

    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Endpoint not found',
        path: req.originalUrl,
        method: req.method,
        timestamp: new Date().toISOString()
      });
    });
  }

  /**
   * Start the migration toolkit server
   */
  async start() {
    if (this.isRunning) {
      logger.warn('Migration Toolkit is already running');
      return;
    }

    try {
      // Initialize services if not already done
      await this.initializeServices();

      // Start API wrapper on separate port
      if (this.apiWrapper) {
        await this.apiWrapper.start();
      }

      // Start main server
      await new Promise((resolve, reject) => {
        this.server = this.app.listen(this.port, (error) => {
          if (error) {
            reject(error);
          } else {
            this.isRunning = true;
            logger.info(`Migration Toolkit started on port ${this.port}`);
            logger.info('Available endpoints:');
            logger.info(`  - Health Check: http://localhost:${this.port}/health`);
            logger.info(`  - API Wrapper: http://localhost:${this.port + 1}`);
            logger.info(`  - Documentation: http://localhost:${this.port}/api/docs`);
            resolve();
          }
        });
      });

    } catch (error) {
      logger.error('Failed to start Migration Toolkit:', error);
      throw error;
    }
  }

  /**
   * Stop the migration toolkit server
   */
  async stop() {
    if (!this.isRunning) {
      logger.warn('Migration Toolkit is not running');
      return;
    }

    try {
      // Stop API wrapper
      if (this.apiWrapper) {
        await this.apiWrapper.stop();
      }

      // Stop main server
      if (this.server) {
        await new Promise((resolve, reject) => {
          this.server.close((error) => {
            if (error) {
              reject(error);
            } else {
              this.isRunning = false;
              logger.info('Migration Toolkit stopped');
              resolve();
            }
          });
        });
      }

    } catch (error) {
      logger.error('Error stopping Migration Toolkit:', error);
      throw error;
    }
  }
}

// Create and start the migration toolkit
const migrationToolkit = new MigrationToolkit();

// Handle process signals
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully...');
  await migrationToolkit.stop();
  process.exit(0);
});

process.on('SIGINT', async () => {
  logger.info('SIGINT received, shutting down gracefully...');
  await migrationToolkit.stop();
  process.exit(0);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

process.on('uncaughtException', (error) => {
  logger.error('Uncaught Exception:', error);
  process.exit(1);
});

// Start the application
if (process.env.NODE_ENV !== 'test') {
  migrationToolkit.start().catch((error) => {
    logger.error('Failed to start Migration Toolkit:', error);
    process.exit(1);
  });
}

export default MigrationToolkit;