import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

export interface Printer3D {
  id: string;
  name: string;
  model: string;
  manufacturer: string;
  octoprintUrl: string;
  octoprintApiKey: string;
  ipAddress: string;
  macAddress?: string;
  serialNumber?: string;
  location: {
    facility: string;
    zone: string;
    position: string;
    coordinates?: { x: number; y: number; z: number };
  };
  specifications: {
    buildVolume: { x: number; y: number; z: number };
    layerHeight: { min: number; max: number };
    nozzleDiameter: number[];
    filamentDiameters: number[];
    maxHotendTemp: number;
    maxBedTemp: number;
    maxPrintSpeed: number;
    hasHeatedBed: boolean;
    hasEnclosure: boolean;
    hasCamera: boolean;
    hasFilamentSensor: boolean;
    hasAutoLeveling: boolean;
  };
  status: PrinterStatus;
  currentJob?: PrintJob;
  materialLoaded?: MaterialSpool;
  maintenanceSchedule: MaintenanceRecord[];
  qualityMetrics: QualityMetrics;
  operationMode: 'garage' | 'enterprise';
  isOnline: boolean;
  lastHeartbeat: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface PrinterStatus {
  state: 'idle' | 'printing' | 'paused' | 'error' | 'maintenance' | 'offline';
  temperatures: {
    hotend: { actual: number; target: number };
    bed: { actual: number; target: number };
    chamber?: { actual: number; target: number };
  };
  progress?: {
    completion: number;
    printTime: number;
    printTimeLeft: number;
    filepos: number;
  };
  position?: { x: number; y: number; z: number; e: number };
  speeds?: {
    printSpeed: number;
    flowRate: number;
    fanSpeed: number;
  };
  flags: {
    operational: boolean;
    paused: boolean;
    printing: boolean;
    cancelling: boolean;
    pausing: boolean;
    error: boolean;
    ready: boolean;
    sdReady: boolean;
  };
  errorMessage?: string;
  lastUpdated: Date;
}

export interface PrintJob {
  id: string;
  filename: string;
  filePath: string;
  gcodePath: string;
  printerId: string;
  customerId: string;
  orderNumber: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  materialRequirements: {
    type: string;
    color: string;
    weight: number;
    length?: number;
  };
  settings: {
    layerHeight: number;
    infill: number;
    printSpeed: number;
    supportMaterial: boolean;
    raftBrim: 'none' | 'brim' | 'raft';
  };
  estimatedTime: number;
  estimatedMaterialUsage: number;
  estimatedCost: number;
  actualTime?: number;
  actualMaterialUsage?: number;
  status: 'queued' | 'preparing' | 'printing' | 'post-processing' | 'quality-check' | 'packaging' | 'completed' | 'failed' | 'cancelled';
  qualityCheckResults?: QualityCheckResult;
  slicingResults?: SlicingResults;
  startedAt?: Date;
  completedAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface MaterialSpool {
  id: string;
  type: string;
  brand: string;
  color: string;
  diameter: number;
  weight: {
    total: number;
    remaining: number;
    used: number;
  };
  temperature: {
    hotend: number;
    bed: number;
  };
  properties: {
    density: number;
    shrinkage: number;
    strength: string;
    flexibility: string;
    supportRequired: boolean;
  };
  cost: {
    perKg: number;
    perGram: number;
  };
  expirationDate?: Date;
  lotNumber?: string;
  qrCode?: string;
  printedJobs: string[];
  createdAt: Date;
  updatedAt: Date;
}

export interface MaintenanceRecord {
  id: string;
  type: 'preventive' | 'corrective' | 'calibration' | 'upgrade';
  status: 'scheduled' | 'in-progress' | 'completed' | 'overdue';
  priority: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  scheduledDate: Date;
  completedDate?: Date;
  nextDueDate?: Date;
  technician?: string;
  duration?: number;
  cost?: number;
  parts?: { name: string; quantity: number; cost: number }[];
  notes?: string;
  attachments?: string[];
  createdAt: Date;
  updatedAt: Date;
}

export interface QualityMetrics {
  successRate: number;
  averageAccuracy: number;
  dimensionalAccuracy: number;
  surfaceFinish: number;
  layerAdhesion: number;
  failureRate: number;
  commonFailures: { type: string; frequency: number }[];
  totalPrints: number;
  totalRuntime: number;
  averagePrintTime: number;
  materialWaste: number;
  lastCalibration: Date;
  lastQualityCheck: Date;
}

export interface QualityCheckResult {
  id: string;
  jobId: string;
  checkType: 'visual' | 'dimensional' | 'functional' | 'automated';
  inspector: string;
  result: 'pass' | 'fail' | 'rework';
  score: number;
  measurements?: {
    dimension: string;
    expected: number;
    actual: number;
    tolerance: number;
    pass: boolean;
  }[];
  defects?: {
    type: string;
    severity: 'minor' | 'major' | 'critical';
    location: string;
    description: string;
    image?: string;
  }[];
  notes?: string;
  reworkRequired?: string;
  checkedAt: Date;
}

export interface SlicingResults {
  layers: number;
  estimatedPrintTime: number;
  materialUsage: number;
  supportMaterial: number;
  filamentLength: number;
  boundingBox: { x: number; y: number; z: number };
  volumetricFlow: number;
  retractionsCount: number;
  settings: Record<string, any>;
  warnings: string[];
  errors: string[];
  slicedAt: Date;
}

export interface FleetMetrics {
  totalPrinters: number;
  onlinePrinters: number;
  activePrinters: number;
  utilizationRate: number;
  averageUptime: number;
  totalJobsCompleted: number;
  totalMaterialUsed: number;
  totalRevenue: number;
  qualityRate: number;
  maintenanceCosts: number;
  energyConsumption: number;
  carbonFootprint: number;
}

export class PrinterFleetManager extends EventEmitter {
  private printers: Map<string, Printer3D> = new Map();
  private printJobs: Map<string, PrintJob> = new Map();
  private materialSpools: Map<string, MaterialSpool> = new Map();
  private maintenanceRecords: Map<string, MaintenanceRecord> = new Map();
  private qualityChecks: Map<string, QualityCheckResult> = new Map();

  constructor() {
    super();
    this.initializeFleet();
    this.startHealthMonitoring();
  }

  private initializeFleet(): void {
    // Initialize with sample printers for both garage and enterprise modes
    this.createSamplePrinters();
    this.createSampleMaterials();
  }

  private createSamplePrinters(): void {
    // Garage setup - 3-5 printers
    const garagePrinters: Omit<Printer3D, 'id' | 'createdAt' | 'updatedAt' | 'lastHeartbeat' | 'qualityMetrics'>[] = [
      {
        name: 'Ender 3 V2 #1',
        model: 'Ender 3 V2',
        manufacturer: 'Creality',
        octoprintUrl: 'http://192.168.1.101',
        octoprintApiKey: 'sample-api-key-1',
        ipAddress: '192.168.1.101',
        location: {
          facility: 'Home Garage',
          zone: 'Main Area',
          position: 'Shelf 1'
        },
        specifications: {
          buildVolume: { x: 220, y: 220, z: 250 },
          layerHeight: { min: 0.1, max: 0.3 },
          nozzleDiameter: [0.4],
          filamentDiameters: [1.75],
          maxHotendTemp: 260,
          maxBedTemp: 100,
          maxPrintSpeed: 180,
          hasHeatedBed: true,
          hasEnclosure: false,
          hasCamera: true,
          hasFilamentSensor: false,
          hasAutoLeveling: false
        },
        status: {
          state: 'idle',
          temperatures: {
            hotend: { actual: 23, target: 0 },
            bed: { actual: 22, target: 0 }
          },
          flags: {
            operational: true,
            paused: false,
            printing: false,
            cancelling: false,
            pausing: false,
            error: false,
            ready: true,
            sdReady: true
          },
          lastUpdated: new Date()
        },
        maintenanceSchedule: [],
        operationMode: 'garage',
        isOnline: true
      },
      {
        name: 'Prusa MK3S+ #1',
        model: 'i3 MK3S+',
        manufacturer: 'Prusa Research',
        octoprintUrl: 'http://192.168.1.102',
        octoprintApiKey: 'sample-api-key-2',
        ipAddress: '192.168.1.102',
        location: {
          facility: 'Home Garage',
          zone: 'Main Area',
          position: 'Shelf 2'
        },
        specifications: {
          buildVolume: { x: 250, y: 210, z: 210 },
          layerHeight: { min: 0.05, max: 0.35 },
          nozzleDiameter: [0.4, 0.6, 0.8],
          filamentDiameters: [1.75],
          maxHotendTemp: 300,
          maxBedTemp: 120,
          maxPrintSpeed: 200,
          hasHeatedBed: true,
          hasEnclosure: false,
          hasCamera: false,
          hasFilamentSensor: true,
          hasAutoLeveling: true
        },
        status: {
          state: 'idle',
          temperatures: {
            hotend: { actual: 24, target: 0 },
            bed: { actual: 23, target: 0 }
          },
          flags: {
            operational: true,
            paused: false,
            printing: false,
            cancelling: false,
            pausing: false,
            error: false,
            ready: true,
            sdReady: true
          },
          lastUpdated: new Date()
        },
        maintenanceSchedule: [],
        operationMode: 'garage',
        isOnline: true
      }
    ];

    // Enterprise setup - 10-50 printers
    const enterprisePrinters: Omit<Printer3D, 'id' | 'createdAt' | 'updatedAt' | 'lastHeartbeat' | 'qualityMetrics'>[] = [
      {
        name: 'Ultimaker S5 #1',
        model: 'Ultimaker S5',
        manufacturer: 'Ultimaker',
        octoprintUrl: 'http://10.0.1.101',
        octoprintApiKey: 'enterprise-api-key-1',
        ipAddress: '10.0.1.101',
        location: {
          facility: 'Factory Floor A',
          zone: 'Production Line 1',
          position: 'Station 1',
          coordinates: { x: 10, y: 5, z: 1 }
        },
        specifications: {
          buildVolume: { x: 330, y: 240, z: 300 },
          layerHeight: { min: 0.06, max: 0.6 },
          nozzleDiameter: [0.25, 0.4, 0.6, 0.8],
          filamentDiameters: [2.85],
          maxHotendTemp: 280,
          maxBedTemp: 140,
          maxPrintSpeed: 300,
          hasHeatedBed: true,
          hasEnclosure: true,
          hasCamera: true,
          hasFilamentSensor: true,
          hasAutoLeveling: true
        },
        status: {
          state: 'printing',
          temperatures: {
            hotend: { actual: 215, target: 215 },
            bed: { actual: 60, target: 60 },
            chamber: { actual: 45, target: 45 }
          },
          progress: {
            completion: 45.6,
            printTime: 3600,
            printTimeLeft: 4320,
            filepos: 1456789
          },
          flags: {
            operational: true,
            paused: false,
            printing: true,
            cancelling: false,
            pausing: false,
            error: false,
            ready: true,
            sdReady: true
          },
          lastUpdated: new Date()
        },
        maintenanceSchedule: [],
        operationMode: 'enterprise',
        isOnline: true
      }
    ];

    // Add printers to fleet
    [...garagePrinters, ...enterprisePrinters].forEach(printerData => {
      const printer: Printer3D = {
        ...printerData,
        id: uuidv4(),
        qualityMetrics: {
          successRate: 92 + Math.random() * 8,
          averageAccuracy: 95 + Math.random() * 5,
          dimensionalAccuracy: 0.1 + Math.random() * 0.05,
          surfaceFinish: 85 + Math.random() * 15,
          layerAdhesion: 88 + Math.random() * 12,
          failureRate: Math.random() * 8,
          commonFailures: [
            { type: 'adhesion', frequency: 3 },
            { type: 'stringing', frequency: 2 },
            { type: 'warping', frequency: 1 }
          ],
          totalPrints: Math.floor(Math.random() * 1000) + 100,
          totalRuntime: Math.floor(Math.random() * 8760) + 100,
          averagePrintTime: Math.floor(Math.random() * 300) + 60,
          materialWaste: Math.random() * 5 + 1,
          lastCalibration: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000),
          lastQualityCheck: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000)
        },
        createdAt: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000),
        updatedAt: new Date(),
        lastHeartbeat: new Date()
      };

      this.printers.set(printer.id, printer);
      this.emit('printerAdded', printer);
    });
  }

  private createSampleMaterials(): void {
    const materials = [
      { type: 'PLA', brand: 'Hatchbox', color: 'Black', diameter: 1.75, weight: 1000, cost: 25 },
      { type: 'PLA', brand: 'Hatchbox', color: 'White', diameter: 1.75, weight: 1000, cost: 25 },
      { type: 'PETG', brand: 'Overture', color: 'Clear', diameter: 1.75, weight: 1000, cost: 28 },
      { type: 'ABS', brand: 'eSUN', color: 'Red', diameter: 1.75, weight: 1000, cost: 22 },
      { type: 'TPU', brand: 'NinjaFlex', color: 'Blue', diameter: 1.75, weight: 500, cost: 45 }
    ];

    materials.forEach(mat => {
      const spool: MaterialSpool = {
        id: uuidv4(),
        type: mat.type,
        brand: mat.brand,
        color: mat.color,
        diameter: mat.diameter,
        weight: {
          total: mat.weight,
          remaining: mat.weight - Math.random() * mat.weight * 0.5,
          used: 0
        },
        temperature: {
          hotend: mat.type === 'PLA' ? 200 : mat.type === 'PETG' ? 235 : mat.type === 'ABS' ? 250 : 220,
          bed: mat.type === 'PLA' ? 60 : mat.type === 'PETG' ? 80 : mat.type === 'ABS' ? 100 : 50
        },
        properties: {
          density: mat.type === 'PLA' ? 1.24 : mat.type === 'PETG' ? 1.27 : mat.type === 'ABS' ? 1.04 : 1.2,
          shrinkage: mat.type === 'PLA' ? 0.2 : mat.type === 'PETG' ? 0.7 : mat.type === 'ABS' ? 1.5 : 0.5,
          strength: mat.type === 'ABS' ? 'high' : mat.type === 'PETG' ? 'high' : 'medium',
          flexibility: mat.type === 'TPU' ? 'high' : 'low',
          supportRequired: mat.type === 'PLA' ? false : true
        },
        cost: {
          perKg: mat.cost,
          perGram: mat.cost / 1000
        },
        printedJobs: [],
        createdAt: new Date(),
        updatedAt: new Date()
      };

      spool.weight.used = spool.weight.total - spool.weight.remaining;
      this.materialSpools.set(spool.id, spool);
    });
  }

  private startHealthMonitoring(): void {
    setInterval(() => {
      this.checkPrinterHealth();
    }, 30000); // Check every 30 seconds

    setInterval(() => {
      this.updatePrinterStatuses();
    }, 5000); // Update statuses every 5 seconds
  }

  private checkPrinterHealth(): void {
    this.printers.forEach((printer, printerId) => {
      const timeSinceHeartbeat = Date.now() - printer.lastHeartbeat.getTime();
      
      if (timeSinceHeartbeat > 60000) { // 1 minute without heartbeat
        printer.isOnline = false;
        printer.status.state = 'offline';
        this.emit('printerOffline', printer);
      } else if (!printer.isOnline && timeSinceHeartbeat <= 60000) {
        printer.isOnline = true;
        printer.status.state = 'idle';
        this.emit('printerOnline', printer);
      }
    });
  }

  private updatePrinterStatuses(): void {
    // Simulate real-time status updates
    this.printers.forEach((printer) => {
      if (printer.isOnline) {
        printer.lastHeartbeat = new Date();
        
        // Simulate temperature fluctuations
        if (printer.status.state === 'printing') {
          const tempVariation = (Math.random() - 0.5) * 2;
          printer.status.temperatures.hotend.actual += tempVariation;
          printer.status.temperatures.bed.actual += tempVariation * 0.5;
          
          // Update progress if printing
          if (printer.status.progress) {
            printer.status.progress.completion += Math.random() * 0.1;
            printer.status.progress.printTime += 5;
            printer.status.progress.printTimeLeft = Math.max(0, printer.status.progress.printTimeLeft - 5);
            
            if (printer.status.progress.completion >= 100) {
              this.completePrintJob(printer.id);
            }
          }
        }
        
        printer.status.lastUpdated = new Date();
        this.emit('printerStatusUpdated', printer);
      }
    });
  }

  async addPrinter(printerData: Omit<Printer3D, 'id' | 'createdAt' | 'updatedAt' | 'lastHeartbeat' | 'qualityMetrics'>): Promise<Printer3D> {
    const printer: Printer3D = {
      ...printerData,
      id: uuidv4(),
      qualityMetrics: {
        successRate: 100,
        averageAccuracy: 100,
        dimensionalAccuracy: 0.05,
        surfaceFinish: 100,
        layerAdhesion: 100,
        failureRate: 0,
        commonFailures: [],
        totalPrints: 0,
        totalRuntime: 0,
        averagePrintTime: 0,
        materialWaste: 0,
        lastCalibration: new Date(),
        lastQualityCheck: new Date()
      },
      createdAt: new Date(),
      updatedAt: new Date(),
      lastHeartbeat: new Date()
    };

    this.printers.set(printer.id, printer);
    this.emit('printerAdded', printer);
    
    return printer;
  }

  async removePrinter(printerId: string): Promise<boolean> {
    const printer = this.printers.get(printerId);
    if (!printer) return false;

    // Stop any active job
    if (printer.currentJob) {
      await this.cancelPrintJob(printer.currentJob.id);
    }

    this.printers.delete(printerId);
    this.emit('printerRemoved', printer);
    
    return true;
  }

  async updatePrinter(printerId: string, updates: Partial<Printer3D>): Promise<boolean> {
    const printer = this.printers.get(printerId);
    if (!printer) return false;

    Object.assign(printer, updates, { updatedAt: new Date() });
    this.emit('printerUpdated', printer);
    
    return true;
  }

  async assignPrintJob(printerId: string, job: PrintJob): Promise<boolean> {
    const printer = this.printers.get(printerId);
    if (!printer || !printer.isOnline || printer.status.state !== 'idle') {
      return false;
    }

    // Check material compatibility
    const requiredMaterial = this.findCompatibleMaterial(job.materialRequirements);
    if (!requiredMaterial) {
      this.emit('jobAssignmentFailed', { job, reason: 'No compatible material available' });
      return false;
    }

    printer.currentJob = job;
    printer.materialLoaded = requiredMaterial;
    printer.status.state = 'preparing';
    
    job.status = 'preparing';
    job.startedAt = new Date();
    
    this.printJobs.set(job.id, job);
    this.emit('jobAssigned', { printer, job });

    // Start print simulation
    setTimeout(() => {
      this.startPrinting(printerId);
    }, 5000);

    return true;
  }

  private findCompatibleMaterial(requirements: PrintJob['materialRequirements']): MaterialSpool | null {
    for (const [, spool] of this.materialSpools) {
      if (spool.type === requirements.type && 
          spool.color === requirements.color && 
          spool.weight.remaining >= requirements.weight) {
        return spool;
      }
    }
    return null;
  }

  private startPrinting(printerId: string): void {
    const printer = this.printers.get(printerId);
    if (!printer || !printer.currentJob) return;

    printer.status.state = 'printing';
    printer.status.temperatures.hotend.target = printer.materialLoaded?.temperature.hotend || 200;
    printer.status.temperatures.bed.target = printer.materialLoaded?.temperature.bed || 60;
    printer.status.progress = {
      completion: 0,
      printTime: 0,
      printTimeLeft: printer.currentJob.estimatedTime,
      filepos: 0
    };

    printer.currentJob.status = 'printing';
    this.emit('printStarted', { printer, job: printer.currentJob });
  }

  private completePrintJob(printerId: string): void {
    const printer = this.printers.get(printerId);
    if (!printer || !printer.currentJob) return;

    const job = printer.currentJob;
    job.status = 'post-processing';
    job.actualTime = printer.status.progress?.printTime || job.estimatedTime;
    job.completedAt = new Date();

    // Update material usage
    if (printer.materialLoaded) {
      const materialUsed = job.estimatedMaterialUsage * (0.9 + Math.random() * 0.2);
      printer.materialLoaded.weight.remaining -= materialUsed;
      printer.materialLoaded.weight.used += materialUsed;
      printer.materialLoaded.printedJobs.push(job.id);
      job.actualMaterialUsage = materialUsed;
    }

    // Update printer metrics
    printer.qualityMetrics.totalPrints++;
    printer.qualityMetrics.totalRuntime += job.actualTime;
    printer.qualityMetrics.averagePrintTime = printer.qualityMetrics.totalRuntime / printer.qualityMetrics.totalPrints;

    printer.status.state = 'idle';
    printer.status.progress = undefined;
    printer.status.temperatures.hotend.target = 0;
    printer.status.temperatures.bed.target = 0;
    printer.currentJob = undefined;
    printer.materialLoaded = undefined;

    this.emit('printCompleted', { printer, job });

    // Schedule quality check
    setTimeout(() => {
      this.performQualityCheck(job.id);
    }, 1000);
  }

  async cancelPrintJob(jobId: string): Promise<boolean> {
    const job = this.printJobs.get(jobId);
    if (!job) return false;

    const printer = Array.from(this.printers.values()).find(p => p.currentJob?.id === jobId);
    if (printer) {
      printer.status.state = 'idle';
      printer.status.progress = undefined;
      printer.status.temperatures.hotend.target = 0;
      printer.status.temperatures.bed.target = 0;
      printer.currentJob = undefined;
    }

    job.status = 'cancelled';
    job.completedAt = new Date();

    this.emit('jobCancelled', { printer, job });
    return true;
  }

  private performQualityCheck(jobId: string): void {
    const job = this.printJobs.get(jobId);
    if (!job) return;

    // Simulate quality check
    const qualityCheck: QualityCheckResult = {
      id: uuidv4(),
      jobId,
      checkType: 'automated',
      inspector: 'QC System',
      result: Math.random() > 0.1 ? 'pass' : 'fail',
      score: 85 + Math.random() * 15,
      measurements: [
        {
          dimension: 'length',
          expected: 100,
          actual: 99.8 + Math.random() * 0.4,
          tolerance: 0.5,
          pass: true
        }
      ],
      checkedAt: new Date()
    };

    this.qualityChecks.set(qualityCheck.id, qualityCheck);
    job.qualityCheckResults = qualityCheck;

    if (qualityCheck.result === 'pass') {
      job.status = 'packaging';
      setTimeout(() => {
        job.status = 'completed';
        this.emit('jobCompleted', job);
      }, 2000);
    } else {
      job.status = 'failed';
      this.emit('jobFailed', { job, qualityCheck });
    }
  }

  async scheduleMaintenance(printerId: string, maintenance: Omit<MaintenanceRecord, 'id' | 'createdAt' | 'updatedAt'>): Promise<MaintenanceRecord> {
    const record: MaintenanceRecord = {
      ...maintenance,
      id: uuidv4(),
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.maintenanceRecords.set(record.id, record);
    
    const printer = this.printers.get(printerId);
    if (printer) {
      printer.maintenanceSchedule.push(record);
      this.emit('maintenanceScheduled', { printer, maintenance: record });
    }

    return record;
  }

  async getFleetMetrics(): Promise<FleetMetrics> {
    const totalPrinters = this.printers.size;
    const onlinePrinters = Array.from(this.printers.values()).filter(p => p.isOnline).length;
    const activePrinters = Array.from(this.printers.values()).filter(p => p.status.state === 'printing').length;
    
    const allJobs = Array.from(this.printJobs.values());
    const completedJobs = allJobs.filter(j => j.status === 'completed');
    
    const totalRuntime = Array.from(this.printers.values()).reduce((sum, p) => sum + p.qualityMetrics.totalRuntime, 0);
    const totalPossibleRuntime = totalPrinters * 24 * 365; // hours per year
    
    return {
      totalPrinters,
      onlinePrinters,
      activePrinters,
      utilizationRate: totalPossibleRuntime > 0 ? (totalRuntime / totalPossibleRuntime) * 100 : 0,
      averageUptime: onlinePrinters > 0 ? (onlinePrinters / totalPrinters) * 100 : 0,
      totalJobsCompleted: completedJobs.length,
      totalMaterialUsed: Array.from(this.materialSpools.values()).reduce((sum, s) => sum + s.weight.used, 0),
      totalRevenue: completedJobs.reduce((sum, job) => sum + (job.estimatedCost || 0), 0),
      qualityRate: Array.from(this.printers.values()).reduce((sum, p) => sum + p.qualityMetrics.successRate, 0) / totalPrinters,
      maintenanceCosts: Array.from(this.maintenanceRecords.values()).reduce((sum, r) => sum + (r.cost || 0), 0),
      energyConsumption: activePrinters * 200, // watts average per active printer
      carbonFootprint: activePrinters * 0.1 // kg CO2 per hour
    };
  }

  getPrinter(id: string): Printer3D | undefined {
    return this.printers.get(id);
  }

  getAllPrinters(): Printer3D[] {
    return Array.from(this.printers.values());
  }

  getPrintersByMode(mode: 'garage' | 'enterprise'): Printer3D[] {
    return Array.from(this.printers.values()).filter(p => p.operationMode === mode);
  }

  getAvailablePrinters(): Printer3D[] {
    return Array.from(this.printers.values()).filter(p => 
      p.isOnline && p.status.state === 'idle'
    );
  }

  getPrintJob(id: string): PrintJob | undefined {
    return this.printJobs.get(id);
  }

  getAllPrintJobs(): PrintJob[] {
    return Array.from(this.printJobs.values());
  }

  getJobsByStatus(status: PrintJob['status']): PrintJob[] {
    return Array.from(this.printJobs.values()).filter(j => j.status === status);
  }

  getMaterialSpools(): MaterialSpool[] {
    return Array.from(this.materialSpools.values());
  }

  getMaintenanceRecords(): MaintenanceRecord[] {
    return Array.from(this.maintenanceRecords.values());
  }

  getQualityChecks(): QualityCheckResult[] {
    return Array.from(this.qualityChecks.values());
  }
}

export const printerFleet = new PrinterFleetManager();