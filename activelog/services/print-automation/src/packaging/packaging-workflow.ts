import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import QRCode from 'qrcode';

export interface PackagingWorkflow {
  id: string;
  name: string;
  description: string;
  steps: PackagingStep[];
  triggers: {
    autoStart: boolean;
    qualityCheckRequired: boolean;
    customerApprovalRequired: boolean;
    inventoryCheckRequired: boolean;
  };
  materials: PackagingMaterial[];
  equipment: string[];
  estimatedTime: number; // minutes
  costPerUnit: number;
  isActive: boolean;
  createdBy: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface PackagingStep {
  id: string;
  name: string;
  type: 'preparation' | 'protection' | 'labeling' | 'documentation' | 'quality-check' | 'sealing' | 'shipping';
  description: string;
  order: number;
  automated: boolean;
  required: boolean;
  estimatedTime: number; // minutes
  instructions: string[];
  materials: string[]; // Material IDs
  equipment: string[];
  qualityChecks?: string[];
  outputs: string[];
  conditions?: {
    skipIf?: string;
    requireIf?: string;
  };
}

export interface PackagingMaterial {
  id: string;
  name: string;
  type: 'box' | 'bubble-wrap' | 'foam' | 'tape' | 'label' | 'bag' | 'divider' | 'desiccant' | 'cushioning';
  specifications: {
    dimensions?: { length: number; width: number; height: number };
    weight?: number;
    material: string;
    color?: string;
    thickness?: number;
    adhesive?: boolean;
    waterproof?: boolean;
    antistatic?: boolean;
  };
  costPerUnit: number;
  stockQuantity: number;
  minimumStock: number;
  supplier: {
    name: string;
    partNumber: string;
    leadTimeDays: number;
  };
  compatibleWith: string[]; // Part types or sizes
  environmentalRating: 'standard' | 'moisture-resistant' | 'temperature-stable' | 'chemical-resistant';
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface PackagingJob {
  id: string;
  printJobId: string;
  workflowId: string;
  customerId: string;
  orderNumber: string;
  items: PackagingItem[];
  status: 'pending' | 'in-progress' | 'quality-check' | 'completed' | 'failed' | 'cancelled';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  currentStep: number;
  completedSteps: string[];
  assignedOperator?: string;
  workstation?: string;
  startedAt?: Date;
  estimatedCompletionAt?: Date;
  actualCompletionAt?: Date;
  totalCost: number;
  materialsUsed: MaterialUsage[];
  documentation: PackagingDocumentation[];
  qualityChecks: PackagingQualityCheck[];
  shippingInfo?: ShippingInfo;
  trackingNumbers: string[];
  notes?: string;
  issues: PackagingIssue[];
  createdAt: Date;
  updatedAt: Date;
}

export interface PackagingItem {
  id: string;
  partName: string;
  quantity: number;
  dimensions: { length: number; width: number; height: number };
  weight: number;
  fragility: 'low' | 'medium' | 'high' | 'extreme';
  specialHandling?: string[];
  protectionLevel: 'basic' | 'standard' | 'premium' | 'custom';
  customInstructions?: string;
}

export interface MaterialUsage {
  materialId: string;
  quantityUsed: number;
  cost: number;
  wasteAmount?: number;
  notes?: string;
}

export interface PackagingDocumentation {
  id: string;
  type: 'invoice' | 'packing-list' | 'certificate' | 'warranty' | 'instructions' | 'safety-sheet';
  filename: string;
  url: string;
  language: string;
  required: boolean;
  generated: boolean;
  printRequired: boolean;
  copies: number;
  createdAt: Date;
}

export interface PackagingQualityCheck {
  id: string;
  checkType: 'seal-integrity' | 'label-placement' | 'protection-adequacy' | 'documentation' | 'weight-verification';
  result: 'pass' | 'fail' | 'warning';
  checkedBy: string;
  checkedAt: Date;
  notes?: string;
  images?: string[];
  measurements?: { parameter: string; value: number; expected: number; tolerance: number }[];
}

export interface ShippingInfo {
  carrier: string;
  service: string;
  trackingNumber: string;
  estimatedDelivery: Date;
  cost: number;
  dimensions: { length: number; width: number; height: number };
  weight: number;
  insurance?: {
    value: number;
    cost: number;
  };
  signatures: {
    packed: string;
    checked: string;
    shipped: string;
  };
}

export interface PackagingIssue {
  id: string;
  type: 'material-shortage' | 'equipment-failure' | 'quality-failure' | 'damage' | 'documentation-missing';
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  impact: string;
  resolution?: string;
  resolvedBy?: string;
  resolvedAt?: Date;
  cost?: number;
  createdAt: Date;
}

export interface PackagingMetrics {
  totalJobs: number;
  completedJobs: number;
  averageProcessingTime: number;
  onTimeDelivery: number;
  qualityRate: number;
  costPerJob: number;
  materialUtilization: number;
  throughputPerHour: number;
  operatorEfficiency: Array<{
    operatorId: string;
    jobsCompleted: number;
    averageTime: number;
    qualityScore: number;
    efficiency: number;
  }>;
  materialConsumption: Array<{
    materialId: string;
    totalUsed: number;
    cost: number;
    wasteRate: number;
  }>;
  issueAnalysis: {
    totalIssues: number;
    byType: Array<{ type: string; count: number; percentage: number }>;
    averageResolutionTime: number;
    costImpact: number;
  };
}

export interface PackagingStation {
  id: string;
  name: string;
  type: 'manual' | 'semi-automated' | 'fully-automated';
  capabilities: string[];
  equipment: string[];
  maxThroughput: number; // jobs per hour
  currentJob?: string;
  operatorId?: string;
  status: 'available' | 'busy' | 'maintenance' | 'offline';
  location: {
    facility: string;
    zone: string;
    position: string;
  };
  lastMaintenanceDate: Date;
  nextMaintenanceDate: Date;
  utilizationRate: number;
  qualityScore: number;
  totalJobsProcessed: number;
  createdAt: Date;
  updatedAt: Date;
}

export class PackagingWorkflowManager extends EventEmitter {
  private workflows: Map<string, PackagingWorkflow> = new Map();
  private materials: Map<string, PackagingMaterial> = new Map();
  private jobs: Map<string, PackagingJob> = new Map();
  private stations: Map<string, PackagingStation> = new Map();
  private workflowProcessor?: NodeJS.Timeout;

  constructor() {
    super();
    this.initializeDefaultData();
    this.startWorkflowProcessor();
  }

  private initializeDefaultData(): void {
    this.createDefaultMaterials();
    this.createDefaultWorkflows();
    this.createDefaultStations();
  }

  private createDefaultMaterials(): void {
    const materials: Omit<PackagingMaterial, 'id' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'Small Cardboard Box',
        type: 'box',
        specifications: {
          dimensions: { length: 150, width: 100, height: 50 },
          material: 'Corrugated Cardboard',
          weight: 50
        },
        costPerUnit: 0.25,
        stockQuantity: 1000,
        minimumStock: 100,
        supplier: {
          name: 'PackCorp',
          partNumber: 'CB-150-100-50',
          leadTimeDays: 5
        },
        compatibleWith: ['small-parts', 'electronics'],
        environmentalRating: 'standard',
        isActive: true
      },
      {
        name: 'Medium Cardboard Box',
        type: 'box',
        specifications: {
          dimensions: { length: 250, width: 200, height: 100 },
          material: 'Corrugated Cardboard',
          weight: 120
        },
        costPerUnit: 0.45,
        stockQuantity: 500,
        minimumStock: 50,
        supplier: {
          name: 'PackCorp',
          partNumber: 'CB-250-200-100',
          leadTimeDays: 5
        },
        compatibleWith: ['medium-parts', 'prototypes'],
        environmentalRating: 'standard',
        isActive: true
      },
      {
        name: 'Bubble Wrap Roll',
        type: 'bubble-wrap',
        specifications: {
          material: 'Polyethylene',
          thickness: 3,
          waterproof: true
        },
        costPerUnit: 0.02, // per sq cm
        stockQuantity: 50000,
        minimumStock: 5000,
        supplier: {
          name: 'BubblePack Ltd',
          partNumber: 'BW-3MM-500M',
          leadTimeDays: 3
        },
        compatibleWith: ['fragile-items', 'electronics'],
        environmentalRating: 'moisture-resistant',
        isActive: true
      },
      {
        name: 'Anti-static Foam',
        type: 'foam',
        specifications: {
          material: 'Polyethylene Foam',
          thickness: 10,
          antistatic: true
        },
        costPerUnit: 0.05, // per sq cm
        stockQuantity: 10000,
        minimumStock: 1000,
        supplier: {
          name: 'ElectroSafe',
          partNumber: 'AS-FOAM-10MM',
          leadTimeDays: 7
        },
        compatibleWith: ['electronic-parts', 'sensitive-components'],
        environmentalRating: 'standard',
        isActive: true
      },
      {
        name: 'Packing Tape',
        type: 'tape',
        specifications: {
          material: 'Polypropylene',
          adhesive: true,
          waterproof: true
        },
        costPerUnit: 0.01, // per cm
        stockQuantity: 100000,
        minimumStock: 10000,
        supplier: {
          name: 'TapeMaster',
          partNumber: 'PP-TAPE-50M',
          leadTimeDays: 2
        },
        compatibleWith: ['all'],
        environmentalRating: 'moisture-resistant',
        isActive: true
      },
      {
        name: 'Shipping Label',
        type: 'label',
        specifications: {
          dimensions: { length: 100, width: 150, height: 0.1 },
          material: 'Thermal Paper',
          adhesive: true
        },
        costPerUnit: 0.10,
        stockQuantity: 5000,
        minimumStock: 500,
        supplier: {
          name: 'LabelPro',
          partNumber: 'TH-LABEL-100x150',
          leadTimeDays: 3
        },
        compatibleWith: ['all'],
        environmentalRating: 'standard',
        isActive: true
      }
    ];

    materials.forEach(materialData => {
      const material: PackagingMaterial = {
        ...materialData,
        id: uuidv4(),
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.materials.set(material.id, material);
    });
  }

  private createDefaultWorkflows(): void {
    const materialIds = Array.from(this.materials.keys());

    const workflows: Omit<PackagingWorkflow, 'id' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'Standard Packaging',
        description: 'Basic packaging workflow for most items',
        steps: [
          {
            id: uuidv4(),
            name: 'Pre-packaging Inspection',
            type: 'quality-check',
            description: 'Visual inspection of printed parts',
            order: 1,
            automated: false,
            required: true,
            estimatedTime: 5,
            instructions: [
              'Check for obvious defects',
              'Verify part completeness',
              'Ensure support material removal'
            ],
            materials: [],
            equipment: ['inspection-light'],
            qualityChecks: ['visual-inspection'],
            outputs: ['inspection-report']
          },
          {
            id: uuidv4(),
            name: 'Protection Wrapping',
            type: 'protection',
            description: 'Wrap parts in protective material',
            order: 2,
            automated: false,
            required: true,
            estimatedTime: 10,
            instructions: [
              'Select appropriate protection material',
              'Wrap parts securely',
              'Ensure no sharp edges exposed'
            ],
            materials: [materialIds[2]], // Bubble wrap
            equipment: ['cutting-tool'],
            outputs: ['protected-parts']
          },
          {
            id: uuidv4(),
            name: 'Boxing',
            type: 'preparation',
            description: 'Place items in shipping box',
            order: 3,
            automated: false,
            required: true,
            estimatedTime: 8,
            instructions: [
              'Select appropriate box size',
              'Place parts carefully',
              'Add cushioning as needed'
            ],
            materials: [materialIds[0], materialIds[1]], // Boxes
            equipment: [],
            outputs: ['boxed-items']
          },
          {
            id: uuidv4(),
            name: 'Documentation',
            type: 'documentation',
            description: 'Generate and include documentation',
            order: 4,
            automated: true,
            required: true,
            estimatedTime: 3,
            instructions: [
              'Generate packing list',
              'Print shipping label',
              'Include any certificates'
            ],
            materials: [materialIds[5]], // Labels
            equipment: ['printer'],
            outputs: ['documentation-package']
          },
          {
            id: uuidv4(),
            name: 'Final Sealing',
            type: 'sealing',
            description: 'Seal the package for shipping',
            order: 5,
            automated: false,
            required: true,
            estimatedTime: 5,
            instructions: [
              'Apply tape securely',
              'Verify seal integrity',
              'Apply shipping label'
            ],
            materials: [materialIds[4]], // Tape
            equipment: ['tape-dispenser'],
            outputs: ['sealed-package']
          }
        ],
        triggers: {
          autoStart: true,
          qualityCheckRequired: true,
          customerApprovalRequired: false,
          inventoryCheckRequired: true
        },
        materials: materialIds.slice(0, 6),
        equipment: ['inspection-light', 'cutting-tool', 'printer', 'tape-dispenser'],
        estimatedTime: 31,
        costPerUnit: 1.50,
        isActive: true,
        createdBy: 'system'
      },
      {
        name: 'Premium Packaging',
        description: 'Enhanced packaging for high-value or fragile items',
        steps: [
          {
            id: uuidv4(),
            name: 'Quality Verification',
            type: 'quality-check',
            description: 'Thorough quality inspection',
            order: 1,
            automated: false,
            required: true,
            estimatedTime: 10,
            instructions: [
              'Detailed visual inspection',
              'Dimensional verification',
              'Surface finish check'
            ],
            materials: [],
            equipment: ['inspection-light', 'calipers'],
            qualityChecks: ['dimensional-check', 'surface-quality'],
            outputs: ['quality-certificate']
          },
          {
            id: uuidv4(),
            name: 'Anti-static Protection',
            type: 'protection',
            description: 'Apply anti-static protection',
            order: 2,
            automated: false,
            required: true,
            estimatedTime: 8,
            instructions: [
              'Use anti-static foam',
              'Ensure complete coverage',
              'Seal in anti-static bag if needed'
            ],
            materials: [materialIds[3]], // Anti-static foam
            equipment: ['cutting-tool'],
            outputs: ['protected-parts']
          },
          {
            id: uuidv4(),
            name: 'Custom Boxing',
            type: 'preparation',
            description: 'Custom box preparation with extra cushioning',
            order: 3,
            automated: false,
            required: true,
            estimatedTime: 15,
            instructions: [
              'Prepare custom box if needed',
              'Add multiple layers of cushioning',
              'Secure parts to prevent movement'
            ],
            materials: [materialIds[0], materialIds[1], materialIds[2]], // Boxes and bubble wrap
            equipment: ['box-cutter', 'tape-dispenser'],
            outputs: ['premium-package']
          },
          {
            id: uuidv4(),
            name: 'Complete Documentation',
            type: 'documentation',
            description: 'Generate complete documentation package',
            order: 4,
            automated: true,
            required: true,
            estimatedTime: 7,
            instructions: [
              'Generate detailed packing list',
              'Include material certificates',
              'Add handling instructions',
              'Prepare shipping documentation'
            ],
            materials: [materialIds[5]], // Labels
            equipment: ['printer', 'laminator'],
            outputs: ['complete-documentation']
          },
          {
            id: uuidv4(),
            name: 'Premium Sealing',
            type: 'sealing',
            description: 'Professional sealing and labeling',
            order: 5,
            automated: false,
            required: true,
            estimatedTime: 8,
            instructions: [
              'Apply reinforced tape sealing',
              'Add fragile stickers if needed',
              'Apply premium shipping labels',
              'Add tracking codes'
            ],
            materials: [materialIds[4], materialIds[5]], // Tape and labels
            equipment: ['tape-dispenser', 'label-printer'],
            outputs: ['premium-sealed-package']
          }
        ],
        triggers: {
          autoStart: false,
          qualityCheckRequired: true,
          customerApprovalRequired: true,
          inventoryCheckRequired: true
        },
        materials: materialIds,
        equipment: ['inspection-light', 'calipers', 'cutting-tool', 'box-cutter', 'tape-dispenser', 'printer', 'laminator', 'label-printer'],
        estimatedTime: 48,
        costPerUnit: 3.75,
        isActive: true,
        createdBy: 'system'
      }
    ];

    workflows.forEach(workflowData => {
      const workflow: PackagingWorkflow = {
        ...workflowData,
        id: uuidv4(),
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.workflows.set(workflow.id, workflow);
    });
  }

  private createDefaultStations(): void {
    const stations: Omit<PackagingStation, 'id' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'Packaging Station 1',
        type: 'manual',
        capabilities: ['visual-inspection', 'wrapping', 'boxing', 'labeling'],
        equipment: ['inspection-light', 'cutting-tool', 'tape-dispenser', 'scale'],
        maxThroughput: 8,
        status: 'available',
        location: {
          facility: 'Main Floor',
          zone: 'Packaging Area',
          position: 'Station 1'
        },
        lastMaintenanceDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
        nextMaintenanceDate: new Date(Date.now() + 60 * 24 * 60 * 60 * 1000),
        utilizationRate: 75,
        qualityScore: 95,
        totalJobsProcessed: 1250
      },
      {
        name: 'Premium Packaging Station',
        type: 'semi-automated',
        capabilities: ['detailed-inspection', 'premium-wrapping', 'custom-boxing', 'documentation-generation'],
        equipment: ['microscope', 'calipers', 'laminator', 'label-printer', 'automated-tape-dispenser'],
        maxThroughput: 4,
        status: 'available',
        location: {
          facility: 'Main Floor',
          zone: 'Premium Area',
          position: 'Station P1'
        },
        lastMaintenanceDate: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000),
        nextMaintenanceDate: new Date(Date.now() + 75 * 24 * 60 * 60 * 1000),
        utilizationRate: 60,
        qualityScore: 98,
        totalJobsProcessed: 450
      }
    ];

    stations.forEach(stationData => {
      const station: PackagingStation = {
        ...stationData,
        id: uuidv4(),
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.stations.set(station.id, station);
    });
  }

  private startWorkflowProcessor(): void {
    this.workflowProcessor = setInterval(() => {
      this.processPackagingJobs();
      this.checkMaterialLevels();
    }, 30000); // Check every 30 seconds
  }

  private async processPackagingJobs(): Promise<void> {
    const pendingJobs = Array.from(this.jobs.values())
      .filter(job => job.status === 'pending')
      .sort((a, b) => {
        // Priority sorting
        const priorityOrder = { urgent: 4, high: 3, normal: 2, low: 1 };
        return priorityOrder[b.priority] - priorityOrder[a.priority];
      });

    const availableStations = Array.from(this.stations.values())
      .filter(station => station.status === 'available');

    for (let i = 0; i < Math.min(pendingJobs.length, availableStations.length); i++) {
      const job = pendingJobs[i];
      const station = availableStations[i];
      
      await this.assignJobToStation(job.id, station.id);
    }
  }

  private checkMaterialLevels(): void {
    this.materials.forEach((material, materialId) => {
      if (material.stockQuantity <= material.minimumStock) {
        this.emit('materialLowStock', {
          material,
          currentStock: material.stockQuantity,
          minimumStock: material.minimumStock,
          reorderNeeded: material.minimumStock * 2 - material.stockQuantity
        });
      }
    });
  }

  async createPackagingJob(jobData: Omit<PackagingJob, 'id' | 'status' | 'currentStep' | 'completedSteps' | 'materialsUsed' | 'documentation' | 'qualityChecks' | 'trackingNumbers' | 'issues' | 'createdAt' | 'updatedAt'>): Promise<PackagingJob> {
    const job: PackagingJob = {
      ...jobData,
      id: uuidv4(),
      status: 'pending',
      currentStep: 0,
      completedSteps: [],
      materialsUsed: [],
      documentation: [],
      qualityChecks: [],
      trackingNumbers: [],
      issues: [],
      createdAt: new Date(),
      updatedAt: new Date()
    };

    // Calculate estimated completion time
    const workflow = this.workflows.get(job.workflowId);
    if (workflow) {
      job.estimatedCompletionAt = new Date(Date.now() + workflow.estimatedTime * 60 * 1000);
    }

    this.jobs.set(job.id, job);
    this.emit('packagingJobCreated', job);

    return job;
  }

  private async assignJobToStation(jobId: string, stationId: string): Promise<boolean> {
    const job = this.jobs.get(jobId);
    const station = this.stations.get(stationId);
    
    if (!job || !station || station.status !== 'available') {
      return false;
    }

    // Check if station has required capabilities
    const workflow = this.workflows.get(job.workflowId);
    if (workflow) {
      const requiredCapabilities = workflow.steps.map(step => step.type);
      const hasCapabilities = requiredCapabilities.every(cap => 
        station.capabilities.some(stationCap => stationCap.includes(cap))
      );
      
      if (!hasCapabilities) {
        return false;
      }
    }

    job.status = 'in-progress';
    job.workstation = stationId;
    job.startedAt = new Date();
    job.updatedAt = new Date();

    station.status = 'busy';
    station.currentJob = jobId;
    station.updatedAt = new Date();

    this.emit('jobAssignedToStation', { job, station });
    
    // Start processing the first step
    await this.processNextStep(jobId);

    return true;
  }

  private async processNextStep(jobId: string): Promise<void> {
    const job = this.jobs.get(jobId);
    if (!job) return;

    const workflow = this.workflows.get(job.workflowId);
    if (!workflow) return;

    const currentStep = workflow.steps[job.currentStep];
    if (!currentStep) {
      // Job completed
      await this.completePackagingJob(jobId);
      return;
    }

    this.emit('stepStarted', { job, step: currentStep });

    // Simulate step processing time
    setTimeout(async () => {
      await this.completeStep(jobId, currentStep.id);
    }, currentStep.estimatedTime * 60 * 1000);
  }

  private async completeStep(jobId: string, stepId: string): Promise<void> {
    const job = this.jobs.get(jobId);
    if (!job) return;

    const workflow = this.workflows.get(job.workflowId);
    if (!workflow) return;

    const step = workflow.steps.find(s => s.id === stepId);
    if (!step) return;

    // Record material usage
    step.materials.forEach(materialId => {
      const material = this.materials.get(materialId);
      if (material) {
        const usage = this.calculateMaterialUsage(material, job.items);
        job.materialsUsed.push({
          materialId,
          quantityUsed: usage.quantity,
          cost: usage.cost,
          wasteAmount: usage.waste
        });

        // Update material stock
        material.stockQuantity -= usage.quantity;
        material.updatedAt = new Date();
      }
    });

    // Generate documentation if needed
    if (step.type === 'documentation') {
      const documentation = await this.generateDocumentation(job);
      job.documentation.push(...documentation);
    }

    // Perform quality checks if needed
    if (step.qualityChecks && step.qualityChecks.length > 0) {
      const qualityCheck = await this.performQualityCheck(job, step);
      job.qualityChecks.push(qualityCheck);
      
      if (qualityCheck.result === 'fail') {
        await this.handleQualityFailure(jobId, qualityCheck);
        return;
      }
    }

    job.completedSteps.push(stepId);
    job.currentStep++;
    job.updatedAt = new Date();

    this.emit('stepCompleted', { job, step });

    // Process next step
    setTimeout(() => {
      this.processNextStep(jobId);
    }, 1000);
  }

  private calculateMaterialUsage(material: PackagingMaterial, items: PackagingItem[]): { quantity: number; cost: number; waste: number } {
    let totalQuantity = 0;
    let wasteAmount = 0;

    items.forEach(item => {
      switch (material.type) {
        case 'box':
          // One box per set of items that fit
          totalQuantity += Math.ceil(item.quantity / this.calculateBoxCapacity(material, item));
          break;
        case 'bubble-wrap':
          // Calculate surface area to cover
          const surfaceArea = 2 * (item.dimensions.length * item.dimensions.width + 
                                  item.dimensions.length * item.dimensions.height + 
                                  item.dimensions.width * item.dimensions.height);
          totalQuantity += surfaceArea * item.quantity * 1.2; // 20% overlap
          wasteAmount += surfaceArea * item.quantity * 0.1; // 10% waste
          break;
        case 'tape':
          // Estimate tape length needed
          const perimeter = 2 * (item.dimensions.length + item.dimensions.width);
          totalQuantity += perimeter * item.quantity * 3; // 3 layers
          break;
        case 'label':
          totalQuantity += item.quantity;
          break;
        default:
          totalQuantity += item.quantity;
      }
    });

    return {
      quantity: totalQuantity,
      cost: totalQuantity * material.costPerUnit,
      waste: wasteAmount
    };
  }

  private calculateBoxCapacity(box: PackagingMaterial, item: PackagingItem): number {
    if (!box.specifications.dimensions) return 1;

    const boxVolume = box.specifications.dimensions.length * 
                     box.specifications.dimensions.width * 
                     box.specifications.dimensions.height;

    const itemVolume = item.dimensions.length * 
                      item.dimensions.width * 
                      item.dimensions.height;

    // Account for packing efficiency (typically 60-80%)
    return Math.floor((boxVolume * 0.7) / itemVolume);
  }

  private async generateDocumentation(job: PackagingJob): Promise<PackagingDocumentation[]> {
    const documentation: PackagingDocumentation[] = [];

    // Generate packing list
    const packingList: PackagingDocumentation = {
      id: uuidv4(),
      type: 'packing-list',
      filename: `packing-list-${job.orderNumber}.pdf`,
      url: `/documents/packing-lists/${job.id}.pdf`,
      language: 'en',
      required: true,
      generated: true,
      printRequired: true,
      copies: 2,
      createdAt: new Date()
    };

    // Generate shipping label
    const shippingLabel: PackagingDocumentation = {
      id: uuidv4(),
      type: 'invoice',
      filename: `shipping-label-${job.orderNumber}.pdf`,
      url: `/documents/shipping-labels/${job.id}.pdf`,
      language: 'en',
      required: true,
      generated: true,
      printRequired: true,
      copies: 1,
      createdAt: new Date()
    };

    // Generate QR code for tracking
    const qrCodeData = {
      jobId: job.id,
      orderNumber: job.orderNumber,
      customerId: job.customerId
    };

    const qrCodeUrl = await QRCode.toDataURL(JSON.stringify(qrCodeData));
    
    documentation.push(packingList, shippingLabel);
    
    return documentation;
  }

  private async performQualityCheck(job: PackagingJob, step: PackagingStep): Promise<PackagingQualityCheck> {
    // Simulate quality check
    const checkTypes = step.qualityChecks || ['seal-integrity'];
    const checkType = checkTypes[0] as PackagingQualityCheck['checkType'];
    
    const qualityCheck: PackagingQualityCheck = {
      id: uuidv4(),
      checkType,
      result: Math.random() > 0.05 ? 'pass' : 'fail', // 95% pass rate
      checkedBy: job.assignedOperator || 'system',
      checkedAt: new Date(),
      notes: checkType === 'seal-integrity' ? 'Tape application checked' : 'Quality verification performed'
    };

    return qualityCheck;
  }

  private async handleQualityFailure(jobId: string, qualityCheck: PackagingQualityCheck): Promise<void> {
    const job = this.jobs.get(jobId);
    if (!job) return;

    const issue: PackagingIssue = {
      id: uuidv4(),
      type: 'quality-failure',
      severity: 'medium',
      description: `Quality check failed: ${qualityCheck.checkType}`,
      impact: 'Job needs rework before proceeding',
      createdAt: new Date()
    };

    job.issues.push(issue);
    job.status = 'quality-check';
    job.updatedAt = new Date();

    this.emit('qualityCheckFailed', { job, qualityCheck, issue });
  }

  private async completePackagingJob(jobId: string): Promise<void> {
    const job = this.jobs.get(jobId);
    if (!job) return;

    job.status = 'completed';
    job.actualCompletionAt = new Date();
    job.updatedAt = new Date();

    // Generate final tracking number
    job.trackingNumbers.push(`TRK-${job.orderNumber}-${Date.now()}`);

    // Release the workstation
    if (job.workstation) {
      const station = this.stations.get(job.workstation);
      if (station) {
        station.status = 'available';
        station.currentJob = undefined;
        station.totalJobsProcessed++;
        station.updatedAt = new Date();
      }
    }

    this.emit('packagingJobCompleted', job);
  }

  async updateJobStatus(jobId: string, status: PackagingJob['status'], metadata?: Partial<PackagingJob>): Promise<boolean> {
    const job = this.jobs.get(jobId);
    if (!job) return false;

    job.status = status;
    job.updatedAt = new Date();

    if (metadata) {
      Object.assign(job, metadata);
    }

    this.emit('jobStatusUpdated', job);
    return true;
  }

  async addPackagingIssue(jobId: string, issueData: Omit<PackagingIssue, 'id' | 'createdAt'>): Promise<PackagingIssue> {
    const job = this.jobs.get(jobId);
    if (!job) {
      throw new Error('Job not found');
    }

    const issue: PackagingIssue = {
      ...issueData,
      id: uuidv4(),
      createdAt: new Date()
    };

    job.issues.push(issue);
    job.updatedAt = new Date();

    this.emit('packagingIssueAdded', { job, issue });
    return issue;
  }

  async resolvePackagingIssue(jobId: string, issueId: string, resolution: string, resolvedBy: string): Promise<boolean> {
    const job = this.jobs.get(jobId);
    if (!job) return false;

    const issue = job.issues.find(i => i.id === issueId);
    if (!issue) return false;

    issue.resolution = resolution;
    issue.resolvedBy = resolvedBy;
    issue.resolvedAt = new Date();

    job.updatedAt = new Date();

    this.emit('packagingIssueResolved', { job, issue });
    return true;
  }

  async getPackagingMetrics(days: number = 30): Promise<PackagingMetrics> {
    const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    const jobs = Array.from(this.jobs.values())
      .filter(job => job.createdAt >= startDate);

    const totalJobs = jobs.length;
    const completedJobs = jobs.filter(j => j.status === 'completed').length;

    const processingTimes = jobs
      .filter(j => j.startedAt && j.actualCompletionAt)
      .map(j => (j.actualCompletionAt!.getTime() - j.startedAt!.getTime()) / 1000 / 60); // minutes

    const averageProcessingTime = processingTimes.length > 0
      ? processingTimes.reduce((sum, time) => sum + time, 0) / processingTimes.length
      : 0;

    const onTimeJobs = jobs.filter(j => 
      j.actualCompletionAt && j.estimatedCompletionAt && 
      j.actualCompletionAt <= j.estimatedCompletionAt
    ).length;

    const onTimeDelivery = completedJobs > 0 ? (onTimeJobs / completedJobs) * 100 : 0;

    const qualityPassed = jobs.filter(j => 
      j.qualityChecks.every(qc => qc.result === 'pass')
    ).length;

    const qualityRate = totalJobs > 0 ? (qualityPassed / totalJobs) * 100 : 0;

    const totalCost = jobs.reduce((sum, job) => sum + job.totalCost, 0);
    const costPerJob = totalJobs > 0 ? totalCost / totalJobs : 0;

    // Material usage analysis
    const materialUsage = new Map<string, { used: number; cost: number; waste: number }>();
    
    jobs.forEach(job => {
      job.materialsUsed.forEach(usage => {
        const current = materialUsage.get(usage.materialId) || { used: 0, cost: 0, waste: 0 };
        current.used += usage.quantityUsed;
        current.cost += usage.cost;
        current.waste += usage.wasteAmount || 0;
        materialUsage.set(usage.materialId, current);
      });
    });

    const materialConsumption = Array.from(materialUsage.entries()).map(([materialId, data]) => ({
      materialId,
      totalUsed: data.used,
      cost: data.cost,
      wasteRate: data.used > 0 ? (data.waste / data.used) * 100 : 0
    }));

    const totalMaterialUsed = Array.from(materialUsage.values()).reduce((sum, data) => sum + data.used, 0);
    const totalMaterialCost = Array.from(materialUsage.values()).reduce((sum, data) => sum + data.cost, 0);
    const materialUtilization = totalMaterialCost > 0 ? ((totalMaterialCost - totalMaterialCost * 0.1) / totalMaterialCost) * 100 : 0;

    // Issue analysis
    const allIssues = jobs.flatMap(job => job.issues);
    const issuesByType = new Map<string, number>();
    
    allIssues.forEach(issue => {
      issuesByType.set(issue.type, (issuesByType.get(issue.type) || 0) + 1);
    });

    const issueAnalysis = Array.from(issuesByType.entries()).map(([type, count]) => ({
      type,
      count,
      percentage: (count / Math.max(allIssues.length, 1)) * 100
    }));

    const resolvedIssues = allIssues.filter(issue => issue.resolvedAt);
    const resolutionTimes = resolvedIssues.map(issue => 
      (issue.resolvedAt!.getTime() - issue.createdAt.getTime()) / 1000 / 60 / 60 // hours
    );

    const averageResolutionTime = resolutionTimes.length > 0
      ? resolutionTimes.reduce((sum, time) => sum + time, 0) / resolutionTimes.length
      : 0;

    const costImpact = allIssues.reduce((sum, issue) => sum + (issue.cost || 0), 0);

    return {
      totalJobs,
      completedJobs,
      averageProcessingTime: Math.round(averageProcessingTime * 100) / 100,
      onTimeDelivery: Math.round(onTimeDelivery * 100) / 100,
      qualityRate: Math.round(qualityRate * 100) / 100,
      costPerJob: Math.round(costPerJob * 100) / 100,
      materialUtilization: Math.round(materialUtilization * 100) / 100,
      throughputPerHour: completedJobs / (days * 24),
      operatorEfficiency: [], // Would be calculated from operator data
      materialConsumption,
      issueAnalysis: {
        totalIssues: allIssues.length,
        byType: issueAnalysis,
        averageResolutionTime: Math.round(averageResolutionTime * 100) / 100,
        costImpact: Math.round(costImpact * 100) / 100
      }
    };
  }

  // Getter methods
  getWorkflow(id: string): PackagingWorkflow | undefined {
    return this.workflows.get(id);
  }

  getAllWorkflows(): PackagingWorkflow[] {
    return Array.from(this.workflows.values());
  }

  getActiveWorkflows(): PackagingWorkflow[] {
    return Array.from(this.workflows.values()).filter(w => w.isActive);
  }

  getMaterial(id: string): PackagingMaterial | undefined {
    return this.materials.get(id);
  }

  getAllMaterials(): PackagingMaterial[] {
    return Array.from(this.materials.values());
  }

  getActiveMaterials(): PackagingMaterial[] {
    return Array.from(this.materials.values()).filter(m => m.isActive);
  }

  getJob(id: string): PackagingJob | undefined {
    return this.jobs.get(id);
  }

  getAllJobs(): PackagingJob[] {
    return Array.from(this.jobs.values());
  }

  getJobsByStatus(status: PackagingJob['status']): PackagingJob[] {
    return Array.from(this.jobs.values()).filter(j => j.status === status);
  }

  getStation(id: string): PackagingStation | undefined {
    return this.stations.get(id);
  }

  getAllStations(): PackagingStation[] {
    return Array.from(this.stations.values());
  }

  getAvailableStations(): PackagingStation[] {
    return Array.from(this.stations.values()).filter(s => s.status === 'available');
  }

  destroy(): void {
    if (this.workflowProcessor) {
      clearInterval(this.workflowProcessor);
      this.workflowProcessor = undefined;
    }
    
    this.removeAllListeners();
  }
}

export const packagingWorkflow = new PackagingWorkflowManager();