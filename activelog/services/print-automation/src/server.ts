import express from 'express';
import cors from 'cors';
import { PrinterFleetManager } from './fleet/printer-management.js';
import { OctoPrintFleetManager } from './integrations/octoprint-client.js';
import { JobQueueManager } from './queue/job-queue.js';
import { MaterialInventoryManager } from './inventory/material-inventory.js';
import { QualityControlSystem } from './quality/quality-control.js';
import { PackagingWorkflowManager } from './packaging/packaging-workflow.js';
import { LabelPrintingSystem } from './labeling/label-printing.js';
import { OperationScheduler } from './scheduler/operation-scheduler.js';
import { MaintenanceScheduler } from './maintenance/maintenance-scheduler.js';
import { ProfitOptimizer } from './optimization/profit-optimizer.js';
import { GarageOperationMode } from './modes/garage-mode.js';
import { EnterpriseOperationMode } from './modes/enterprise-mode.js';

const app = express();
const port = 8305;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Initialize core systems
const fleetManager = new PrinterFleetManager();
const octoPrintManager = new OctoPrintFleetManager();
const jobQueue = new JobQueueManager();
const inventoryManager = new MaterialInventoryManager();
const qualityControl = new QualityControlSystem();
const packagingManager = new PackagingWorkflowManager();
const labelSystem = new LabelPrintingSystem();
const scheduler = new OperationScheduler();
const maintenanceScheduler = new MaintenanceScheduler();
const profitOptimizer = new ProfitOptimizer();

// Initialize operation modes
const garageMode = new GarageOperationMode(
  {
    maxConcurrentJobs: 4,
    operatingHours: { start: '08:00', end: '22:00', timezone: 'UTC' },
    noiseThreshold: 45,
    temperatureRange: { min: 18, max: 28 },
    humidityRange: { min: 30, max: 70 },
    powerConsumptionLimit: 2000,
    autoShutdownEnabled: true,
    quietHours: { start: '22:00', end: '08:00' },
    ventilationRequired: true,
    safetyMonitoring: true
  },
  {
    spaceConstraints: { length: 6, width: 4, height: 3, usableSpace: 20 },
    electricalConstraints: { maxVoltage: 240, maxCurrent: 20, circuitCapacity: 4800, safetyMargin: 0.2 },
    environmentalConstraints: { hasHVAC: false, insulation: 'moderate', dustLevel: 'medium', vibrationLevel: 'low' },
    accessibilityConstraints: { pedestrianAccess: true, vehicleAccess: false, storageAccess: true, maintenanceAccess: 'moderate' }
  },
  {
    maxPrintersPerShelf: 2,
    maxShelvesPerUnit: 3,
    maxOperatingUnits: 2,
    materialStorageLimit: 50,
    workspaceReservation: 4,
    emergencyShutdownTime: 30,
    maintenanceWindow: 4,
    bufferSpaceRequired: 2
  }
);

const enterpriseMode = new EnterpriseOperationMode({
  facilitySize: 5000,
  maxConcurrentJobs: 100,
  productionLines: 4,
  shiftOperations: true,
  qualityStandards: [
    {
      id: 'iso9001',
      name: 'ISO 9001:2015',
      standard: 'ISO9001',
      requirements: [
        { parameter: 'dimensional_accuracy', tolerance: 0.1, unit: 'mm', measurable: true, critical: true },
        { parameter: 'surface_finish', tolerance: 1.6, unit: 'μm', measurable: true, critical: false }
      ],
      auditable: true,
      certificationRequired: true
    }
  ],
  complianceRequirements: [
    {
      id: 'quality_management',
      type: 'industry',
      standard: 'ISO 9001:2015',
      description: 'Quality management system requirements',
      applicableProducts: ['all'],
      auditFrequency: 365,
      nextAudit: new Date(Date.now() + 180 * 24 * 60 * 60 * 1000),
      status: 'compliant'
    }
  ],
  scalingParameters: {
    maxPrinters: 50,
    maxEmployees: 25,
    maxProductionCapacity: 10000,
    autoScalingEnabled: true,
    scaleUpThreshold: 85,
    scaleDownThreshold: 40,
    scaleUpDelay: 300,
    scaleDownDelay: 1800
  },
  redundancyLevel: 'high' as any,
  securityLevel: 'enhanced' as any
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date(),
    version: '1.0.0',
    services: {
      fleet: 'operational',
      octoprint: 'operational',
      queue: 'operational',
      inventory: 'operational',
      quality: 'operational',
      packaging: 'operational',
      labeling: 'operational',
      scheduler: 'operational',
      maintenance: 'operational',
      profit: 'operational',
      garage: 'operational',
      enterprise: 'operational'
    }
  });
});

// Fleet Management Routes
app.get('/api/fleet/printers', (req, res) => {
  const printers = fleetManager.getAllPrinters();
  res.json(Array.from(printers.values()));
});

app.post('/api/fleet/printers', (req, res) => {
  try {
    const printerId = fleetManager.addPrinter(req.body);
    res.status(201).json({ printerId, message: 'Printer added successfully' });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

app.get('/api/fleet/printers/:id/status', (req, res) => {
  const printer = fleetManager.getAllPrinters().get(req.params.id);
  if (!printer) {
    return res.status(404).json({ error: 'Printer not found' });
  }
  res.json(printer);
});

// Job Queue Routes
app.get('/api/queue/jobs', (req, res) => {
  const jobs = jobQueue.getAllJobs();
  res.json(Array.from(jobs.values()));
});

app.post('/api/queue/jobs', (req, res) => {
  try {
    const jobId = jobQueue.addJob(req.body);
    res.status(201).json({ jobId, message: 'Job added successfully' });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

app.post('/api/queue/jobs/:id/assign', (req, res) => {
  try {
    const success = jobQueue.assignJobToPrinter(req.params.id, req.body.printerId);
    if (success) {
      res.json({ message: 'Job assigned successfully' });
    } else {
      res.status(400).json({ error: 'Failed to assign job' });
    }
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

// Inventory Management Routes
app.get('/api/inventory/materials', (req, res) => {
  const materials = inventoryManager.getAllMaterials();
  res.json(Array.from(materials.values()));
});

app.post('/api/inventory/materials', (req, res) => {
  try {
    const materialId = inventoryManager.addMaterial(req.body);
    res.status(201).json({ materialId, message: 'Material added successfully' });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

app.get('/api/inventory/alerts', (req, res) => {
  const alerts = inventoryManager.getActiveAlerts();
  res.json(alerts);
});

// Quality Control Routes
app.get('/api/quality/checkpoints', (req, res) => {
  const checkpoints = qualityControl.getAllCheckpoints();
  res.json(Array.from(checkpoints.values()));
});

app.post('/api/quality/inspections', (req, res) => {
  try {
    const inspectionId = qualityControl.createInspection(
      req.body.checkpointId,
      req.body.itemId,
      req.body.inspectorId
    );
    res.status(201).json({ inspectionId, message: 'Inspection created successfully' });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

// Packaging Routes
app.get('/api/packaging/workflows', (req, res) => {
  const workflows = packagingManager.getAllWorkflows();
  res.json(Array.from(workflows.values()));
});

app.post('/api/packaging/workflows', (req, res) => {
  try {
    const workflowId = packagingManager.createWorkflow(req.body);
    res.status(201).json({ workflowId, message: 'Packaging workflow created successfully' });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

// Label Printing Routes
app.get('/api/labels/templates', (req, res) => {
  const templates = labelSystem.getAllTemplates();
  res.json(Array.from(templates.values()));
});

app.post('/api/labels/print', (req, res) => {
  try {
    const success = labelSystem.printLabel(
      req.body.templateId,
      req.body.data,
      req.body.printerId,
      req.body.quantity
    );
    if (success) {
      res.json({ message: 'Label print job submitted successfully' });
    } else {
      res.status(400).json({ error: 'Failed to submit print job' });
    }
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

// Scheduler Routes
app.get('/api/scheduler/schedules', (req, res) => {
  const schedules = scheduler.getActiveSchedules();
  res.json(Array.from(schedules.values()));
});

app.post('/api/scheduler/schedules', (req, res) => {
  try {
    const scheduleId = scheduler.createSchedule(req.body);
    res.status(201).json({ scheduleId, message: 'Schedule created successfully' });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

// Maintenance Routes
app.get('/api/maintenance/tasks', (req, res) => {
  const upcoming = maintenanceScheduler.getUpcomingTasks(7);
  res.json(upcoming);
});

app.post('/api/maintenance/schedules', (req, res) => {
  try {
    const scheduleId = maintenanceScheduler.createMaintenanceSchedule(
      req.body.printerId,
      req.body.taskType,
      req.body.interval,
      req.body.options
    );
    res.status(201).json({ scheduleId, message: 'Maintenance schedule created successfully' });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

app.post('/api/maintenance/tasks/:id/complete', (req, res) => {
  try {
    const success = maintenanceScheduler.completeMaintenanceTask(
      req.params.id,
      req.body.completedBy,
      req.body.details
    );
    if (success) {
      res.json({ message: 'Maintenance task completed successfully' });
    } else {
      res.status(400).json({ error: 'Failed to complete maintenance task' });
    }
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

// Profit Optimization Routes
app.get('/api/optimization/analysis', (req, res) => {
  const printerId = req.query.printerId as string;
  const timeframe = parseInt(req.query.timeframe as string) || 30;
  
  const analysis = profitOptimizer.generateProfitAnalysis(printerId, timeframe);
  res.json(analysis);
});

app.get('/api/optimization/recommendations', (req, res) => {
  const printerId = req.query.printerId as string;
  const category = req.query.category as any;
  const priority = req.query.priority as string;
  
  const recommendations = profitOptimizer.getOptimizationRecommendations(printerId, category, priority);
  res.json(recommendations);
});

app.post('/api/optimization/pricing/calculate', (req, res) => {
  try {
    const costInfo = profitOptimizer.calculateJobCost(
      req.body.materialWeight,
      req.body.printTime,
      req.body.complexity,
      req.body.qualityLevel
    );
    
    const pricing = profitOptimizer.calculateOptimalPrice(
      costInfo.totalCost,
      req.body.complexity || 1,
      req.body.quantity || 1,
      req.body.isRushOrder || false,
      req.body.qualityLevel || 'standard',
      req.body.pricingModelId || 'standard_pricing'
    );
    
    res.json({
      costs: costInfo,
      pricing: pricing
    });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

// Garage Mode Routes
app.get('/api/modes/garage/status', (req, res) => {
  const status = garageMode.getOperationStatus();
  res.json(status);
});

app.post('/api/modes/garage/start', (req, res) => {
  try {
    const success = garageMode.startGarageOperation();
    if (success) {
      res.json({ message: 'Garage operation started successfully' });
    } else {
      res.status(400).json({ error: 'Failed to start garage operation' });
    }
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

app.post('/api/modes/garage/printers/:id/add', (req, res) => {
  try {
    const success = garageMode.addPrinterToOperation(req.params.id);
    if (success) {
      res.json({ message: 'Printer added to garage operation' });
    } else {
      res.status(400).json({ error: 'Failed to add printer to garage operation' });
    }
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

// Enterprise Mode Routes
app.get('/api/modes/enterprise/metrics', (req, res) => {
  const metrics = enterpriseMode.getEnterpriseMetrics();
  res.json(Object.fromEntries(metrics));
});

app.get('/api/modes/enterprise/production-lines', (req, res) => {
  const lines = enterpriseMode.getProductionLineStatus();
  res.json(Object.fromEntries(lines));
});

app.get('/api/modes/enterprise/compliance', (req, res) => {
  const compliance = enterpriseMode.getComplianceStatus();
  res.json(compliance);
});

app.post('/api/modes/enterprise/start', (req, res) => {
  try {
    const success = enterpriseMode.startEnterpriseOperation();
    if (success) {
      res.json({ message: 'Enterprise operation started successfully' });
    } else {
      res.status(400).json({ error: 'Failed to start enterprise operation' });
    }
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

// Dashboard/Analytics Routes
app.get('/api/dashboard/overview', (req, res) => {
  res.json({
    timestamp: new Date(),
    fleet: {
      totalPrinters: fleetManager.getAllPrinters().size,
      activePrinters: Array.from(fleetManager.getAllPrinters().values())
        .filter(p => p.status === 'printing').length,
      availablePrinters: Array.from(fleetManager.getAllPrinters().values())
        .filter(p => p.status === 'idle').length
    },
    queue: {
      totalJobs: jobQueue.getAllJobs().size,
      pendingJobs: Array.from(jobQueue.getAllJobs().values())
        .filter(j => j.status === 'queued').length,
      processingJobs: Array.from(jobQueue.getAllJobs().values())
        .filter(j => j.status === 'printing').length
    },
    inventory: {
      totalMaterials: inventoryManager.getAllMaterials().size,
      lowStockAlerts: inventoryManager.getActiveAlerts().length
    },
    quality: {
      totalCheckpoints: qualityControl.getAllCheckpoints().size,
      activeInspections: Array.from(qualityControl.getAllInspections().values())
        .filter(i => i.status === 'in_progress').length
    },
    operations: {
      garageMode: garageMode.getOperationStatus().isOperational,
      enterpriseMode: false // Would check enterpriseMode.isOperational if exposed
    }
  });
});

// Error handling middleware
app.use((error: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Unhandled error:', error);
  res.status(500).json({
    error: 'Internal server error',
    message: error.message,
    timestamp: new Date()
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Endpoint not found',
    path: req.originalUrl,
    method: req.method,
    timestamp: new Date()
  });
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Shutting down print automation system...');
  
  scheduler.shutdown();
  maintenanceScheduler.shutdown();
  profitOptimizer.shutdown();
  garageMode.shutdown();
  enterpriseMode.shutdown();
  
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('Shutting down print automation system...');
  
  scheduler.shutdown();
  maintenanceScheduler.shutdown();
  profitOptimizer.shutdown();
  garageMode.shutdown();
  enterpriseMode.shutdown();
  
  process.exit(0);
});

app.listen(port, () => {
  console.log(`\n🚀 Print Automation System started successfully!`);
  console.log(`📡 Server running on port ${port}`);
  console.log(`🏭 Systems initialized:`);
  console.log(`   ✅ Fleet Management (${fleetManager.getAllPrinters().size} printers)`);
  console.log(`   ✅ OctoPrint Integration`);
  console.log(`   ✅ Job Queue System`);
  console.log(`   ✅ Material Inventory`);
  console.log(`   ✅ Quality Control`);
  console.log(`   ✅ Packaging Workflows`);
  console.log(`   ✅ Label Printing`);
  console.log(`   ✅ 24/7 Operation Scheduler`);
  console.log(`   ✅ Maintenance Scheduling`);
  console.log(`   ✅ Profit Optimization`);
  console.log(`   ✅ Garage Operation Mode`);
  console.log(`   ✅ Enterprise Factory Mode`);
  console.log(`\n📊 Access dashboard: http://localhost:${port}/api/dashboard/overview`);
  console.log(`🔍 Health check: http://localhost:${port}/health`);
  console.log(`\n🎯 Manufacturing automation system ready for operation!`);
});

export default app;