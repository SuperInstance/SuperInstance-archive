/**
 * Product Marketplace Platform Server
 * Comprehensive marketplace for hardware designs, devices, and community-driven products
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
import HardwareDesignSystem from './hardware/HardwareDesignSystem.js';
import ActiveLogDeviceCatalog from './devices/ActiveLogDeviceCatalog.js';
import SolarCameraMarketplace from './cameras/SolarCameraMarketplace.js';
import FishCounterSystems from './counters/FishCounterSystems.js';
import SensorPackageConfigurator from './sensors/SensorPackageConfigurator.js';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const PORT = process.env.PORT || 8380;
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
      filename: 'logs/product-market.log' 
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
      imgSrc: ["'self'", "data:", "blob:", "https:"],
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
let hardwareDesignSystem;
let activeLogDeviceCatalog;
let solarCameraMarketplace;
let fishCounterSystems;
let sensorPackageConfigurator;

async function initializeSystems() {
  try {
    logger.info('🔄 Initializing Product Marketplace systems...');

    // Initialize core systems
    hardwareDesignSystem = new HardwareDesignSystem();
    logger.info('✅ Hardware Design System initialized');

    activeLogDeviceCatalog = new ActiveLogDeviceCatalog();
    logger.info('✅ ActiveLog Device Catalog initialized');

    solarCameraMarketplace = new SolarCameraMarketplace();
    logger.info('✅ Solar Camera Marketplace initialized');

    fishCounterSystems = new FishCounterSystems();
    logger.info('✅ Fish Counter Systems initialized');

    sensorPackageConfigurator = new SensorPackageConfigurator();
    logger.info('✅ Sensor Package Configurator initialized');

    // Set up inter-system event handlers
    setupSystemEventHandlers();

    logger.info('✅ All Product Marketplace systems initialized successfully');
  } catch (error) {
    logger.error('❌ Failed to initialize systems:', error);
    process.exit(1);
  }
}

function setupSystemEventHandlers() {
  // Hardware design events
  hardwareDesignSystem.on('designCreated', (design) => {
    io.emit('design_created', design);
    logger.info(`🎨 New hardware design created: ${design.name}`);
  });

  hardwareDesignSystem.on('designForked', (data) => {
    io.emit('design_forked', data);
    logger.info(`🍴 Design forked: ${data.originalDesign.name}`);
  });

  // Device catalog events
  activeLogDeviceCatalog.on('deviceAdded', (device) => {
    io.emit('device_added', device);
    logger.info(`📱 New device added: ${device.name}`);
  });

  // Camera marketplace events
  solarCameraMarketplace.on('cameraListed', (camera) => {
    io.emit('camera_listed', camera);
    logger.info(`📷 New camera listed: ${camera.name}`);
  });

  // Fish counter events
  fishCounterSystems.on('deploymentCreated', (deployment) => {
    io.emit('fish_counter_deployed', deployment);
    logger.info(`🐟 Fish counter deployed: ${deployment.deployment_name}`);
  });

  fishCounterSystems.on('dataProcessed', (data) => {
    io.to(`deployment_${data.deployment_id}`).emit('fish_count_update', data);
  });

  // Sensor configurator events
  sensorPackageConfigurator.on('packageCreated', (package) => {
    io.emit('sensor_package_created', package);
    logger.info(`🔧 Sensor package created: ${package.name}`);
  });
}

// REST API Routes

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    service: 'product-market',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    port: PORT,
    environment: NODE_ENV
  });
});

// Hardware Design System endpoints
app.post('/api/hardware/designs', async (req, res) => {
  try {
    const designData = req.body;
    const design = await hardwareDesignSystem.createDesign(designData);
    
    res.json(design);
  } catch (error) {
    logger.error('Failed to create hardware design:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/hardware/designs', async (req, res) => {
  try {
    const searchCriteria = req.query;
    const results = await hardwareDesignSystem.searchDesigns(searchCriteria);
    
    res.json(results);
  } catch (error) {
    logger.error('Failed to search hardware designs:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/hardware/designs/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const design = hardwareDesignSystem.designs.get(id);
    
    if (!design) {
      return res.status(404).json({ error: 'Design not found' });
    }
    
    res.json(design);
  } catch (error) {
    logger.error('Failed to get hardware design:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/hardware/designs/:id/fork', async (req, res) => {
  try {
    const { id } = req.params;
    const forkData = req.body;
    
    const forkedDesign = await hardwareDesignSystem.forkDesign(id, forkData);
    
    res.json(forkedDesign);
  } catch (error) {
    logger.error('Failed to fork hardware design:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/hardware/designs/:id/validate', async (req, res) => {
  try {
    const { id } = req.params;
    const validationCriteria = req.body;
    
    const validation = await hardwareDesignSystem.validateDesign(id, validationCriteria);
    
    res.json(validation);
  } catch (error) {
    logger.error('Failed to validate hardware design:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/hardware/designs/:id/quote', async (req, res) => {
  try {
    const { id } = req.params;
    const { quantity, manufacturingOptions } = req.body;
    
    const quote = await hardwareDesignSystem.generateManufacturingQuote(id, quantity, manufacturingOptions);
    
    res.json(quote);
  } catch (error) {
    logger.error('Failed to generate manufacturing quote:', error);
    res.status(500).json({ error: error.message });
  }
});

// ActiveLog Device Catalog endpoints
app.get('/api/devices', async (req, res) => {
  try {
    const searchCriteria = req.query;
    const results = await activeLogDeviceCatalog.searchDevices(searchCriteria);
    
    res.json(results);
  } catch (error) {
    logger.error('Failed to search devices:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/devices/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const device = activeLogDeviceCatalog.devices.get(id);
    
    if (!device) {
      return res.status(404).json({ error: 'Device not found' });
    }
    
    res.json(device);
  } catch (error) {
    logger.error('Failed to get device:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/devices/compatibility', async (req, res) => {
  try {
    const { deviceIds, systemRequirements } = req.body;
    
    const compatibility = await activeLogDeviceCatalog.checkCompatibility(deviceIds, systemRequirements);
    
    res.json(compatibility);
  } catch (error) {
    logger.error('Failed to check device compatibility:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/devices/integration-guide', async (req, res) => {
  try {
    const { deviceIds } = req.body;
    
    const guide = await activeLogDeviceCatalog.generateIntegrationGuide(deviceIds);
    
    res.json(guide);
  } catch (error) {
    logger.error('Failed to generate integration guide:', error);
    res.status(500).json({ error: error.message });
  }
});

// Solar Camera Marketplace endpoints
app.get('/api/cameras', async (req, res) => {
  try {
    const searchCriteria = req.query;
    const results = await solarCameraMarketplace.searchCameras(searchCriteria);
    
    res.json(results);
  } catch (error) {
    logger.error('Failed to search cameras:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/cameras/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const camera = solarCameraMarketplace.cameras.get(id);
    
    if (!camera) {
      return res.status(404).json({ error: 'Camera not found' });
    }
    
    res.json(camera);
  } catch (error) {
    logger.error('Failed to get camera:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/cameras/installation-plan', async (req, res) => {
  try {
    const { cameraIds, siteInformation } = req.body;
    
    const plan = await solarCameraMarketplace.generateInstallationPlan(cameraIds, siteInformation);
    
    res.json(plan);
  } catch (error) {
    logger.error('Failed to generate installation plan:', error);
    res.status(500).json({ error: error.message });
  }
});

// Fish Counter Systems endpoints
app.post('/api/fish-counters/deploy', async (req, res) => {
  try {
    const deploymentRequest = req.body;
    
    const deployment = await fishCounterSystems.deployFishCounter(deploymentRequest);
    
    res.json(deployment);
  } catch (error) {
    logger.error('Failed to deploy fish counter:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/fish-counters/deployments/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const deployment = fishCounterSystems.deploymentSites.get(id);
    
    if (!deployment) {
      return res.status(404).json({ error: 'Deployment not found' });
    }
    
    res.json(deployment);
  } catch (error) {
    logger.error('Failed to get fish counter deployment:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/fish-counters/deployments/:id/data', async (req, res) => {
  try {
    const { id } = req.params;
    const rawData = req.body;
    
    const processedData = await fishCounterSystems.processCountingData(id, rawData);
    
    res.json(processedData);
  } catch (error) {
    logger.error('Failed to process fish counting data:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/fish-counters/deployments/:id/analytics', async (req, res) => {
  try {
    const { id } = req.params;
    const reportParams = req.query;
    
    const report = await fishCounterSystems.generateAnalyticsReport(id, reportParams);
    
    res.json(report);
  } catch (error) {
    logger.error('Failed to generate analytics report:', error);
    res.status(500).json({ error: error.message });
  }
});

// Sensor Package Configurator endpoints
app.get('/api/sensors', async (req, res) => {
  try {
    const searchCriteria = req.query;
    const results = await sensorPackageConfigurator.searchSensors(searchCriteria);
    
    res.json(results);
  } catch (error) {
    logger.error('Failed to search sensors:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/sensors/packages/templates', async (req, res) => {
  try {
    const searchCriteria = req.query;
    const results = await sensorPackageConfigurator.searchPackageTemplates(searchCriteria);
    
    res.json(results);
  } catch (error) {
    logger.error('Failed to search package templates:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/sensors/packages/custom', async (req, res) => {
  try {
    const packageRequest = req.body;
    
    const customPackage = await sensorPackageConfigurator.createCustomPackage(packageRequest);
    
    res.json(customPackage);
  } catch (error) {
    logger.error('Failed to create custom sensor package:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/sensors/packages/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const package = sensorPackageConfigurator.customPackages.get(id) ||
                   sensorPackageConfigurator.packageTemplates.get(id);
    
    if (!package) {
      return res.status(404).json({ error: 'Package not found' });
    }
    
    res.json(package);
  } catch (error) {
    logger.error('Failed to get sensor package:', error);
    res.status(500).json({ error: error.message });
  }
});

// System statistics endpoint
app.get('/api/system/stats', (req, res) => {
  try {
    const stats = {
      hardware_designs: hardwareDesignSystem.getSystemStats(),
      device_catalog: activeLogDeviceCatalog.getSystemStats(),
      solar_cameras: solarCameraMarketplace.getSystemStats(),
      fish_counters: fishCounterSystems.getSystemStats(),
      sensor_configurator: sensorPackageConfigurator.getSystemStats(),
      system_info: {
        uptime: process.uptime(),
        memory_usage: process.memoryUsage(),
        node_version: process.version,
        port: PORT,
        environment: NODE_ENV
      }
    };
    
    res.json(stats);
  } catch (error) {
    logger.error('Failed to get system stats:', error);
    res.status(500).json({ error: error.message });
  }
});

// Socket.IO real-time communication
io.on('connection', (socket) => {
  logger.info(`🔌 Client connected: ${socket.id}`);
  
  // Join deployment room for fish counter updates
  socket.on('join_deployment', (deploymentId) => {
    socket.join(`deployment_${deploymentId}`);
    logger.info(`🐟 Socket ${socket.id} joined deployment: ${deploymentId}`);
  });
  
  // Join design room for hardware design updates
  socket.on('join_design', (designId) => {
    socket.join(`design_${designId}`);
    logger.info(`🎨 Socket ${socket.id} joined design: ${designId}`);
  });
  
  // Real-time fish counting data
  socket.on('fish_count_data', async (data) => {
    try {
      const processedData = await fishCounterSystems.processCountingData(data.deploymentId, data);
      socket.to(`deployment_${data.deploymentId}`).emit('fish_count_update', processedData);
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  });
  
  // Real-time design collaboration
  socket.on('design_update', (data) => {
    socket.to(`design_${data.designId}`).emit('design_changed', {
      designId: data.designId,
      change: data.change,
      timestamp: Date.now()
    });
  });
  
  // Camera installation updates
  socket.on('installation_progress', (data) => {
    io.emit('installation_update', {
      installationId: data.installationId,
      progress: data.progress,
      status: data.status,
      timestamp: Date.now()
    });
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
    
    // Close all system connections
    const systems = [
      hardwareDesignSystem,
      activeLogDeviceCatalog,
      solarCameraMarketplace,
      fishCounterSystems,
      sensorPackageConfigurator
    ];
    
    systems.forEach(system => {
      if (system && typeof system.close === 'function') {
        system.close();
      }
    });
    
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
      logger.info(`🚀 Product Marketplace Platform started on port ${PORT}`);
      logger.info(`🌍 Environment: ${NODE_ENV}`);
      logger.info(`🎯 All systems operational`);
      
      console.log(`
╔════════════════════════════════════════════╗
║        Product Marketplace Platform        ║
║                                            ║
║  🎨 Custom Hardware Design System          ║
║  📱 ActiveLog Device Catalog               ║
║  📷 Solar Camera Marketplace               ║
║  🐟 AI Fish Counter Systems                ║
║  🔧 Sensor Package Configurator            ║
║  🛠️ DIY Kits Platform (Coming Soon)        ║
║  🔨 Assembly Services (Coming Soon)        ║
║  📚 Installation Guides (Coming Soon)      ║
║  🤝 Community Designs (Coming Soon)        ║
║  ⚖️ Patent Protection (Coming Soon)         ║
║  💰 Revenue Sharing (Coming Soon)          ║
║  🦠 Viral Product Tracking (Coming Soon)   ║
║                                            ║
║  Port: ${PORT.toString().padEnd(33)} ║
║  Status: READY                             ║
╚════════════════════════════════════════════╝
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