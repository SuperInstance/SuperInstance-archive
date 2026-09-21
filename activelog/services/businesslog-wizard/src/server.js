/**
 * BusinessLog Wizard Server
 * Intelligent business setup and management platform
 * Main server entry point with Express and Socket.IO
 */

import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import winston from 'winston';
import dotenv from 'dotenv';

// Import core modules
import { BusinessInterviewSystem } from './core/BusinessInterviewSystem.js';
import { InterfaceGenerator } from './core/InterfaceGenerator.js';
import { EmployeeManager } from './employee/EmployeeManager.js';
import { SecurityCameraSystem } from './security/SecurityCameraSystem.js';
import { InventoryMigrator } from './inventory/InventoryMigrator.js';
import { SupplierCatalog } from './suppliers/SupplierCatalog.js';
import { MaintenanceScheduler } from './maintenance/MaintenanceScheduler.js';
import { BlindSpotDetector } from './vision/BlindSpotDetector.js';
import { RecommendationEngine } from './ai/RecommendationEngine.js';
import { ComplexityManager } from './core/ComplexityManager.js';
import { SoftwareController } from './integration/SoftwareController.js';
import { DataMigrationTools } from './migration/DataMigrationTools.js';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const PORT = process.env.PORT || 8372;
const NODE_ENV = process.env.NODE_ENV || 'development';

// Logger setup
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    }),
    new winston.transports.File({ 
      filename: 'logs/error.log', 
      level: 'error' 
    }),
    new winston.transports.File({ 
      filename: 'logs/wizard.log' 
    })
  ]
});

// Express app setup
const app = express();
const server = createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
    methods: ["GET", "POST", "PUT", "DELETE"],
    credentials: true
  },
  transports: ['websocket', 'polling']
});

// Middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "blob:"],
      mediaSrc: ["'self'", "blob:"],
      connectSrc: ["'self'", "ws:", "wss:"]
    }
  }
}));
app.use(compression());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
  credentials: true
}));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Static files
app.use('/static', express.static(join(__dirname, '../public')));
app.use('/uploads', express.static(join(__dirname, '../uploads')));

// Initialize core systems
let businessInterviewSystem;
let interfaceGenerator;
let employeeManager;
let securityCameraSystem;
let inventoryMigrator;
let supplierCatalog;
let maintenanceScheduler;
let blindSpotDetector;
let recommendationEngine;
let complexityManager;
let softwareController;
let dataMigrationTools;

async function initializeSystems() {
  try {
    logger.info('🔄 Initializing BusinessLog Wizard systems...');

    // Initialize AI and ML models first
    recommendationEngine = new RecommendationEngine();
    await recommendationEngine.initialize();

    blindSpotDetector = new BlindSpotDetector();
    await blindSpotDetector.initialize();

    // Initialize core business systems
    businessInterviewSystem = new BusinessInterviewSystem(recommendationEngine);
    interfaceGenerator = new InterfaceGenerator();
    
    // Initialize management systems
    employeeManager = new EmployeeManager();
    securityCameraSystem = new SecurityCameraSystem(blindSpotDetector);
    inventoryMigrator = new InventoryMigrator();
    supplierCatalog = new SupplierCatalog();
    maintenanceScheduler = new MaintenanceScheduler();
    
    // Initialize utility systems
    complexityManager = new ComplexityManager();
    softwareController = new SoftwareController();
    dataMigrationTools = new DataMigrationTools();

    // Connect systems
    businessInterviewSystem.on('interview:completed', (data) => {
      interfaceGenerator.generateCustomInterface(data.businessProfile);
      complexityManager.initializeComplexityLevel(data.businessProfile);
    });

    employeeManager.on('employee:added', (employee) => {
      securityCameraSystem.updateEmployeeDatabase(employee);
    });

    inventoryMigrator.on('migration:completed', (data) => {
      recommendationEngine.analyzeInventoryPatterns(data);
    });

    logger.info('✅ All systems initialized successfully');
  } catch (error) {
    logger.error('❌ Failed to initialize systems:', error);
    process.exit(1);
  }
}

// REST API Routes

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    service: 'businesslog-wizard',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    port: PORT,
    environment: NODE_ENV
  });
});

// Business interview endpoints
app.post('/api/interview/start', async (req, res) => {
  try {
    const { businessName, industry, ownerInfo } = req.body;
    
    const interview = await businessInterviewSystem.startInterview({
      businessName,
      industry,
      ownerInfo
    });
    
    logger.info(`🎯 Started business interview: ${interview.id}`);
    res.json(interview);
  } catch (error) {
    logger.error('Failed to start interview:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/interview/:id/answer', async (req, res) => {
  try {
    const { id } = req.params;
    const { questionId, answer } = req.body;
    
    const result = await businessInterviewSystem.submitAnswer(id, questionId, answer);
    
    res.json(result);
  } catch (error) {
    logger.error('Failed to submit answer:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/interview/:id/progress', async (req, res) => {
  try {
    const { id } = req.params;
    const progress = await businessInterviewSystem.getProgress(id);
    
    res.json(progress);
  } catch (error) {
    logger.error('Failed to get interview progress:', error);
    res.status(500).json({ error: error.message });
  }
});

// Interface generation endpoints
app.post('/api/interface/generate', async (req, res) => {
  try {
    const { businessProfile, complexity } = req.body;
    
    const customInterface = await interfaceGenerator.generateInterface(
      businessProfile, 
      complexity
    );
    
    logger.info(`🎨 Generated custom interface for ${businessProfile.businessName}`);
    res.json(customInterface);
  } catch (error) {
    logger.error('Failed to generate interface:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/interface/:businessId', async (req, res) => {
  try {
    const { businessId } = req.params;
    const interface = await interfaceGenerator.getInterface(businessId);
    
    res.json(interface);
  } catch (error) {
    logger.error('Failed to get interface:', error);
    res.status(500).json({ error: error.message });
  }
});

// Employee management endpoints
app.post('/api/employees', async (req, res) => {
  try {
    const employeeData = req.body;
    const employee = await employeeManager.addEmployee(employeeData);
    
    logger.info(`👤 Added employee: ${employee.name}`);
    res.json(employee);
  } catch (error) {
    logger.error('Failed to add employee:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/employees/:businessId', async (req, res) => {
  try {
    const { businessId } = req.params;
    const employees = await employeeManager.getEmployees(businessId);
    
    res.json(employees);
  } catch (error) {
    logger.error('Failed to get employees:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/employees/:id/schedule', async (req, res) => {
  try {
    const { id } = req.params;
    const { schedule } = req.body;
    
    const result = await employeeManager.updateSchedule(id, schedule);
    res.json(result);
  } catch (error) {
    logger.error('Failed to update employee schedule:', error);
    res.status(500).json({ error: error.message });
  }
});

// Security camera endpoints
app.post('/api/security/cameras', async (req, res) => {
  try {
    const { businessId, cameraConfig } = req.body;
    
    const camera = await securityCameraSystem.addCamera(businessId, cameraConfig);
    
    logger.info(`📹 Added security camera: ${camera.id}`);
    res.json(camera);
  } catch (error) {
    logger.error('Failed to add camera:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/security/cameras/:businessId', async (req, res) => {
  try {
    const { businessId } = req.params;
    const cameras = await securityCameraSystem.getCameras(businessId);
    
    res.json(cameras);
  } catch (error) {
    logger.error('Failed to get cameras:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/security/blind-spot-scan', async (req, res) => {
  try {
    const { businessId, images } = req.body;
    
    const analysis = await blindSpotDetector.analyzeBusiness(businessId, images);
    
    res.json(analysis);
  } catch (error) {
    logger.error('Failed to analyze blind spots:', error);
    res.status(500).json({ error: error.message });
  }
});

// Inventory migration endpoints
app.post('/api/inventory/migrate', async (req, res) => {
  try {
    const { businessId, sourceSystem, migrationConfig } = req.body;
    
    const migration = await inventoryMigrator.startMigration(
      businessId,
      sourceSystem,
      migrationConfig
    );
    
    logger.info(`📦 Started inventory migration: ${migration.id}`);
    res.json(migration);
  } catch (error) {
    logger.error('Failed to start inventory migration:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/inventory/migration/:id/status', async (req, res) => {
  try {
    const { id } = req.params;
    const status = await inventoryMigrator.getMigrationStatus(id);
    
    res.json(status);
  } catch (error) {
    logger.error('Failed to get migration status:', error);
    res.status(500).json({ error: error.message });
  }
});

// Supplier catalog endpoints
app.post('/api/suppliers/import', async (req, res) => {
  try {
    const { businessId, catalogSource, importConfig } = req.body;
    
    const importResult = await supplierCatalog.importCatalog(
      businessId,
      catalogSource,
      importConfig
    );
    
    logger.info(`🏪 Imported supplier catalog: ${importResult.suppliersCount} suppliers`);
    res.json(importResult);
  } catch (error) {
    logger.error('Failed to import supplier catalog:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/suppliers/:businessId', async (req, res) => {
  try {
    const { businessId } = req.params;
    const suppliers = await supplierCatalog.getSuppliers(businessId);
    
    res.json(suppliers);
  } catch (error) {
    logger.error('Failed to get suppliers:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/suppliers/search', async (req, res) => {
  try {
    const { query, filters, businessId } = req.body;
    
    const results = await supplierCatalog.searchSuppliers(businessId, query, filters);
    res.json(results);
  } catch (error) {
    logger.error('Failed to search suppliers:', error);
    res.status(500).json({ error: error.message });
  }
});

// Maintenance scheduling endpoints
app.post('/api/maintenance/schedule', async (req, res) => {
  try {
    const { businessId, equipment, maintenanceConfig } = req.body;
    
    const schedule = await maintenanceScheduler.createSchedule(
      businessId,
      equipment,
      maintenanceConfig
    );
    
    logger.info(`🔧 Created maintenance schedule: ${schedule.id}`);
    res.json(schedule);
  } catch (error) {
    logger.error('Failed to create maintenance schedule:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/maintenance/:businessId/upcoming', async (req, res) => {
  try {
    const { businessId } = req.params;
    const { days = 30 } = req.query;
    
    const upcoming = await maintenanceScheduler.getUpcomingMaintenance(businessId, parseInt(days));
    res.json(upcoming);
  } catch (error) {
    logger.error('Failed to get upcoming maintenance:', error);
    res.status(500).json({ error: error.message });
  }
});

// Recommendation engine endpoints
app.post('/api/recommendations/business', async (req, res) => {
  try {
    const { businessProfile, currentMetrics } = req.body;
    
    const recommendations = await recommendationEngine.getBusinessRecommendations(
      businessProfile,
      currentMetrics
    );
    
    res.json(recommendations);
  } catch (error) {
    logger.error('Failed to get business recommendations:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/recommendations/products', async (req, res) => {
  try {
    const { businessId, context } = req.body;
    
    const recommendations = await recommendationEngine.getProductRecommendations(
      businessId,
      context
    );
    
    res.json(recommendations);
  } catch (error) {
    logger.error('Failed to get product recommendations:', error);
    res.status(500).json({ error: error.message });
  }
});

// Complexity management endpoints
app.get('/api/complexity/:businessId', async (req, res) => {
  try {
    const { businessId } = req.params;
    const complexity = await complexityManager.getCurrentComplexity(businessId);
    
    res.json(complexity);
  } catch (error) {
    logger.error('Failed to get complexity level:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/complexity/:businessId/level-up', async (req, res) => {
  try {
    const { businessId } = req.params;
    const result = await complexityManager.increaseComplexity(businessId);
    
    logger.info(`📈 Increased complexity for business: ${businessId}`);
    res.json(result);
  } catch (error) {
    logger.error('Failed to increase complexity:', error);
    res.status(500).json({ error: error.message });
  }
});

// Software integration endpoints
app.get('/api/integrations/available', async (req, res) => {
  try {
    const integrations = await softwareController.getAvailableIntegrations();
    res.json(integrations);
  } catch (error) {
    logger.error('Failed to get available integrations:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/integrations/:businessId/connect', async (req, res) => {
  try {
    const { businessId } = req.params;
    const { software, credentials, config } = req.body;
    
    const connection = await softwareController.connectSoftware(
      businessId,
      software,
      credentials,
      config
    );
    
    logger.info(`🔗 Connected software integration: ${software}`);
    res.json(connection);
  } catch (error) {
    logger.error('Failed to connect software integration:', error);
    res.status(500).json({ error: error.message });
  }
});

// Data migration endpoints
app.post('/api/migration/analyze', async (req, res) => {
  try {
    const { businessId, dataSource } = req.body;
    
    const analysis = await dataMigrationTools.analyzeDataSource(businessId, dataSource);
    res.json(analysis);
  } catch (error) {
    logger.error('Failed to analyze data source:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/migration/execute', async (req, res) => {
  try {
    const { businessId, migrationPlan } = req.body;
    
    const migration = await dataMigrationTools.executeMigration(businessId, migrationPlan);
    
    logger.info(`🚀 Started data migration: ${migration.id}`);
    res.json(migration);
  } catch (error) {
    logger.error('Failed to execute data migration:', error);
    res.status(500).json({ error: error.message });
  }
});

// Socket.IO real-time communication
io.on('connection', (socket) => {
  logger.info(`🔌 Client connected: ${socket.id}`);
  
  // Join business room
  socket.on('join_business', (businessId) => {
    socket.join(`business_${businessId}`);
    logger.info(`👤 Socket ${socket.id} joined business: ${businessId}`);
  });
  
  // Real-time interview updates
  socket.on('interview_progress', async (data) => {
    try {
      const progress = await businessInterviewSystem.getProgress(data.interviewId);
      socket.emit('interview_update', progress);
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  });
  
  // Real-time security alerts
  socket.on('security_alert', (data) => {
    io.to(`business_${data.businessId}`).emit('security_alert', {
      type: data.type,
      message: data.message,
      timestamp: Date.now(),
      severity: data.severity
    });
  });
  
  // Real-time maintenance notifications
  socket.on('maintenance_due', (data) => {
    io.to(`business_${data.businessId}`).emit('maintenance_notification', {
      equipmentId: data.equipmentId,
      maintenanceType: data.type,
      dueDate: data.dueDate,
      priority: data.priority
    });
  });
  
  // Real-time inventory updates
  socket.on('inventory_update', (data) => {
    io.to(`business_${data.businessId}`).emit('inventory_change', {
      itemId: data.itemId,
      change: data.change,
      newQuantity: data.newQuantity,
      timestamp: Date.now()
    });
  });
  
  // Real-time recommendation updates
  socket.on('request_recommendations', async (data) => {
    try {
      const recommendations = await recommendationEngine.getBusinessRecommendations(
        data.businessProfile,
        data.currentMetrics
      );
      socket.emit('recommendations_updated', recommendations);
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  });
  
  // Handle disconnection
  socket.on('disconnect', () => {
    logger.info(`🔌 Client disconnected: ${socket.id}`);
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({ 
    error: 'Internal server error',
    message: NODE_ENV === 'development' ? err.message : 'Something went wrong'
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Graceful shutdown
const gracefulShutdown = (signal) => {
  logger.info(`📴 Received ${signal}, shutting down gracefully...`);
  
  server.close(() => {
    logger.info('HTTP server closed');
    
    // Close database connections
    if (employeeManager) employeeManager.close();
    if (inventoryMigrator) inventoryMigrator.close();
    if (dataMigrationTools) dataMigrationTools.close();
    
    // Close AI models
    if (recommendationEngine) recommendationEngine.close();
    if (blindSpotDetector) blindSpotDetector.close();
    
    logger.info('All connections closed, exiting...');
    process.exit(0);
  });
  
  // Force close after 30 seconds
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 30000);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Start server
async function startServer() {
  try {
    await initializeSystems();
    
    server.listen(PORT, () => {
      logger.info(`🚀 BusinessLog Wizard server started on port ${PORT}`);
      logger.info(`🌍 Environment: ${NODE_ENV}`);
      logger.info(`🎯 All systems operational`);
      
      console.log(`
╔══════════════════════════════════════════╗
║            BusinessLog Wizard            ║
║                                          ║
║  🧙‍♂️ Intelligent Business Setup Platform   ║
║  🎯 AI-Powered Business Interview        ║
║  🎨 Custom Interface Generation          ║
║  👥 Employee Management System           ║
║  📹 Security Camera Integration          ║
║  📦 Inventory System Migration           ║
║  🏪 Supplier Catalog Management          ║
║  🔧 Maintenance Scheduling               ║
║  👁️ Blind Spot Detection                 ║
║  🤖 AI Recommendation Engine             ║
║  📊 Gradual Complexity Management        ║
║  🔗 Existing Software Integration        ║
║  🚚 Data Migration Tools                 ║
║                                          ║
║  Port: ${PORT.toString().padEnd(31)} ║
║  Status: READY                           ║
╚══════════════════════════════════════════╝
      `);
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Start the server
startServer();

export { app, server, io };