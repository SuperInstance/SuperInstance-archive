import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import { createCanvas, Canvas } from 'canvas';
import sharp from 'sharp';

export interface QualityCheckpoint {
  id: string;
  name: string;
  description: string;
  type: 'pre-print' | 'mid-print' | 'post-print' | 'packaging';
  automated: boolean;
  required: boolean;
  order: number;
  checks: QualityCheck[];
  passThreshold: number; // Percentage
  timeoutMinutes?: number;
  retryCount: number;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface QualityCheck {
  id: string;
  name: string;
  category: 'dimensional' | 'visual' | 'functional' | 'material' | 'surface' | 'structural';
  method: 'measurement' | 'vision' | 'sensor' | 'manual' | 'stress-test' | 'burn-test';
  parameters: {
    tolerance?: number;
    units?: string;
    expectedValue?: number;
    minValue?: number;
    maxValue?: number;
    pattern?: string;
    algorithm?: string;
    threshold?: number;
  };
  weight: number; // Importance weight for scoring
  automatable: boolean;
  equipment?: string[];
  instructions?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface QualityInspection {
  id: string;
  jobId: string;
  printerId: string;
  checkpointId: string;
  inspectorId: string;
  inspectorType: 'human' | 'automated' | 'ai-vision';
  status: 'pending' | 'in-progress' | 'completed' | 'failed' | 'skipped';
  startedAt: Date;
  completedAt?: Date;
  overallScore: number;
  passed: boolean;
  checkResults: QualityCheckResult[];
  images?: InspectionImage[];
  measurements?: QualityMeasurement[];
  defects?: QualityDefect[];
  notes?: string;
  actionRequired?: 'none' | 'rework' | 'scrap' | 'approve-with-note';
  reworkInstructions?: string;
  approvedBy?: string;
  approvedAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface QualityCheckResult {
  checkId: string;
  result: 'pass' | 'fail' | 'warning' | 'na';
  score: number;
  measuredValue?: number;
  expectedValue?: number;
  deviation?: number;
  confidence?: number;
  method: string;
  equipment?: string;
  notes?: string;
  timestamp: Date;
}

export interface InspectionImage {
  id: string;
  filename: string;
  url: string;
  type: 'overall' | 'defect' | 'measurement' | 'before' | 'after';
  annotations?: ImageAnnotation[];
  analysisResults?: VisionAnalysisResult;
  capturedAt: Date;
}

export interface ImageAnnotation {
  id: string;
  type: 'defect' | 'measurement' | 'note' | 'dimension';
  coordinates: { x: number; y: number; width?: number; height?: number };
  label: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  description?: string;
}

export interface VisionAnalysisResult {
  defectDetection: {
    defectsFound: number;
    defectTypes: string[];
    confidence: number;
    boundingBoxes: Array<{
      x: number; y: number; width: number; height: number;
      type: string; confidence: number;
    }>;
  };
  dimensionAnalysis?: {
    measurements: Array<{
      dimension: string;
      measuredValue: number;
      expectedValue: number;
      tolerance: number;
      passed: boolean;
    }>;
  };
  surfaceQuality?: {
    roughness: number;
    uniformity: number;
    colorConsistency: number;
    overallScore: number;
  };
}

export interface QualityMeasurement {
  id: string;
  dimension: string;
  measuredValue: number;
  expectedValue: number;
  tolerance: number;
  units: string;
  method: 'caliper' | 'micrometer' | 'cmm' | 'laser' | 'vision' | 'gauge';
  equipment: string;
  location: string;
  passed: boolean;
  deviation: number;
  timestamp: Date;
}

export interface QualityDefect {
  id: string;
  type: 'stringing' | 'layer-adhesion' | 'warping' | 'under-extrusion' | 'over-extrusion' | 
        'surface-finish' | 'dimension-error' | 'support-marks' | 'bridging' | 'infill-showing' |
        'layer-shift' | 'elephant-foot' | 'z-banding' | 'ghosting' | 'blob' | 'missing-layers';
  severity: 'minor' | 'major' | 'critical';
  location: string;
  description: string;
  cause?: string;
  recommendedAction: 'accept' | 'rework' | 'scrap' | 'adjust-settings';
  images?: string[];
  measurements?: string[];
  detectMethod: 'visual' | 'automated' | 'measurement';
  confidence?: number;
  createdAt: Date;
}

export interface QualityTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  materialTypes: string[];
  applicationTypes: string[];
  checkpoints: string[];
  customChecks?: QualityCheck[];
  tolerances: {
    dimensional: number;
    surface: number;
    functional: number;
  };
  isDefault: boolean;
  usageCount: number;
  createdBy: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface QualityMetrics {
  totalInspections: number;
  passRate: number;
  failRate: number;
  averageScore: number;
  inspectionTime: {
    average: number;
    median: number;
    percentile95: number;
  };
  defectAnalysis: {
    mostCommon: Array<{ type: string; count: number; percentage: number }>;
    bySeverity: { minor: number; major: number; critical: number };
    trends: Array<{ date: string; count: number }>;
  };
  printerPerformance: Array<{
    printerId: string;
    passRate: number;
    avgScore: number;
    commonDefects: string[];
  }>;
  materialPerformance: Array<{
    materialType: string;
    passRate: number;
    avgScore: number;
    reliabilityScore: number;
  }>;
  inspectorPerformance: Array<{
    inspectorId: string;
    inspectorType: string;
    throughput: number;
    accuracy: number;
    avgTime: number;
  }>;
}

export class QualityControlSystem extends EventEmitter {
  private checkpoints: Map<string, QualityCheckpoint> = new Map();
  private qualityChecks: Map<string, QualityCheck> = new Map();
  private inspections: Map<string, QualityInspection> = new Map();
  private templates: Map<string, QualityTemplate> = new Map();
  private visionAI: VisionAIEngine;

  constructor() {
    super();
    this.visionAI = new VisionAIEngine();
    this.initializeDefaultCheckpoints();
    this.initializeDefaultTemplates();
  }

  private initializeDefaultCheckpoints(): void {
    const defaultCheckpoints: Omit<QualityCheckpoint, 'id' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'Pre-Print Setup Check',
        description: 'Verify printer setup before starting print job',
        type: 'pre-print',
        automated: true,
        required: true,
        order: 1,
        checks: [],
        passThreshold: 95,
        timeoutMinutes: 10,
        retryCount: 2,
        isActive: true
      },
      {
        name: 'First Layer Inspection',
        description: 'Check first layer adhesion and quality',
        type: 'mid-print',
        automated: true,
        required: true,
        order: 2,
        checks: [],
        passThreshold: 90,
        timeoutMinutes: 5,
        retryCount: 1,
        isActive: true
      },
      {
        name: 'Mid-Print Progress Check',
        description: 'Monitor print progress and detect issues',
        type: 'mid-print',
        automated: true,
        required: false,
        order: 3,
        checks: [],
        passThreshold: 85,
        timeoutMinutes: 15,
        retryCount: 0,
        isActive: true
      },
      {
        name: 'Final Print Inspection',
        description: 'Comprehensive quality check of finished print',
        type: 'post-print',
        automated: false,
        required: true,
        order: 4,
        checks: [],
        passThreshold: 80,
        timeoutMinutes: 30,
        retryCount: 0,
        isActive: true
      },
      {
        name: 'Packaging Quality Check',
        description: 'Verify part condition before packaging',
        type: 'packaging',
        automated: false,
        required: true,
        order: 5,
        checks: [],
        passThreshold: 95,
        timeoutMinutes: 10,
        retryCount: 0,
        isActive: true
      }
    ];

    const defaultChecks: Omit<QualityCheck, 'id' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'Bed Leveling Check',
        category: 'dimensional',
        method: 'sensor',
        parameters: { tolerance: 0.1, units: 'mm' },
        weight: 10,
        automatable: true,
        equipment: ['bed-level-sensor']
      },
      {
        name: 'Nozzle Temperature Verification',
        category: 'material',
        method: 'sensor',
        parameters: { tolerance: 5, units: '°C' },
        weight: 8,
        automatable: true,
        equipment: ['thermocouple']
      },
      {
        name: 'First Layer Adhesion',
        category: 'visual',
        method: 'vision',
        parameters: { threshold: 0.85 },
        weight: 15,
        automatable: true,
        equipment: ['camera', 'ai-vision']
      },
      {
        name: 'Dimensional Accuracy',
        category: 'dimensional',
        method: 'measurement',
        parameters: { tolerance: 0.1, units: 'mm' },
        weight: 20,
        automatable: false,
        equipment: ['calipers', 'micrometer'],
        instructions: 'Measure critical dimensions with calipers'
      },
      {
        name: 'Surface Finish Quality',
        category: 'surface',
        method: 'vision',
        parameters: { threshold: 0.8 },
        weight: 15,
        automatable: true,
        equipment: ['camera', 'ai-vision']
      },
      {
        name: 'Layer Adhesion Test',
        category: 'structural',
        method: 'manual',
        parameters: {},
        weight: 12,
        automatable: false,
        instructions: 'Gently test layer adhesion by applying pressure'
      },
      {
        name: 'Overhangs and Bridges',
        category: 'structural',
        method: 'vision',
        parameters: { threshold: 0.9 },
        weight: 10,
        automatable: true,
        equipment: ['camera', 'ai-vision']
      },
      {
        name: 'Support Removal Quality',
        category: 'surface',
        method: 'manual',
        parameters: {},
        weight: 8,
        automatable: false,
        instructions: 'Check for clean support removal without damage'
      },
      {
        name: 'Color Consistency',
        category: 'visual',
        method: 'vision',
        parameters: { threshold: 0.95 },
        weight: 5,
        automatable: true,
        equipment: ['color-sensor', 'camera']
      },
      {
        name: 'Packaging Integrity',
        category: 'functional',
        method: 'manual',
        parameters: {},
        weight: 10,
        automatable: false,
        instructions: 'Verify protective packaging and labeling'
      }
    ];

    // Create quality checks
    defaultChecks.forEach(checkData => {
      const qualityCheck: QualityCheck = {
        ...checkData,
        id: uuidv4(),
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.qualityChecks.set(qualityCheck.id, qualityCheck);
    });

    // Create checkpoints and assign checks
    defaultCheckpoints.forEach((checkpointData, index) => {
      const checkpoint: QualityCheckpoint = {
        ...checkpointData,
        id: uuidv4(),
        createdAt: new Date(),
        updatedAt: new Date()
      };

      // Assign relevant checks to each checkpoint
      const allChecks = Array.from(this.qualityChecks.values());
      
      switch (checkpoint.type) {
        case 'pre-print':
          checkpoint.checks = allChecks
            .filter(check => ['Bed Leveling Check', 'Nozzle Temperature Verification'].includes(check.name))
            .map(check => check.id);
          break;
        case 'mid-print':
          if (checkpoint.name.includes('First Layer')) {
            checkpoint.checks = allChecks
              .filter(check => check.name === 'First Layer Adhesion')
              .map(check => check.id);
          } else {
            checkpoint.checks = allChecks
              .filter(check => ['Surface Finish Quality', 'Color Consistency'].includes(check.name))
              .map(check => check.id);
          }
          break;
        case 'post-print':
          checkpoint.checks = allChecks
            .filter(check => ['Dimensional Accuracy', 'Layer Adhesion Test', 'Overhangs and Bridges', 'Support Removal Quality'].includes(check.name))
            .map(check => check.id);
          break;
        case 'packaging':
          checkpoint.checks = allChecks
            .filter(check => check.name === 'Packaging Integrity')
            .map(check => check.id);
          break;
      }

      this.checkpoints.set(checkpoint.id, checkpoint);
    });
  }

  private initializeDefaultTemplates(): void {
    const templates: Omit<QualityTemplate, 'id' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'Standard Prototype Template',
        description: 'Standard quality checks for prototype parts',
        category: 'prototyping',
        materialTypes: ['PLA', 'PETG'],
        applicationTypes: ['prototype', 'concept'],
        checkpoints: Array.from(this.checkpoints.keys()),
        tolerances: {
          dimensional: 0.2,
          surface: 0.8,
          functional: 0.9
        },
        isDefault: true,
        usageCount: 0,
        createdBy: 'system'
      },
      {
        name: 'Production Parts Template',
        description: 'Strict quality checks for production parts',
        category: 'production',
        materialTypes: ['ABS', 'PETG', 'Nylon'],
        applicationTypes: ['production', 'end-use'],
        checkpoints: Array.from(this.checkpoints.keys()),
        tolerances: {
          dimensional: 0.05,
          surface: 0.95,
          functional: 0.98
        },
        isDefault: true,
        usageCount: 0,
        createdBy: 'system'
      },
      {
        name: 'Functional Testing Template',
        description: 'Quality checks focused on functional requirements',
        category: 'functional',
        materialTypes: ['ABS', 'TPU', 'Nylon'],
        applicationTypes: ['functional', 'mechanical'],
        checkpoints: Array.from(this.checkpoints.keys()).slice(0, 4), // Exclude packaging
        tolerances: {
          dimensional: 0.1,
          surface: 0.7,
          functional: 0.95
        },
        isDefault: true,
        usageCount: 0,
        createdBy: 'system'
      }
    ];

    templates.forEach(templateData => {
      const template: QualityTemplate = {
        ...templateData,
        id: uuidv4(),
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.templates.set(template.id, template);
    });
  }

  async createInspection(inspectionData: Omit<QualityInspection, 'id' | 'status' | 'startedAt' | 'overallScore' | 'passed' | 'checkResults' | 'createdAt' | 'updatedAt'>): Promise<QualityInspection> {
    const inspection: QualityInspection = {
      ...inspectionData,
      id: uuidv4(),
      status: 'pending',
      startedAt: new Date(),
      overallScore: 0,
      passed: false,
      checkResults: [],
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.inspections.set(inspection.id, inspection);
    this.emit('inspectionCreated', inspection);

    // Start automated inspection if applicable
    const checkpoint = this.checkpoints.get(inspection.checkpointId);
    if (checkpoint?.automated) {
      setTimeout(() => {
        this.performAutomatedInspection(inspection.id);
      }, 1000);
    }

    return inspection;
  }

  private async performAutomatedInspection(inspectionId: string): Promise<void> {
    const inspection = this.inspections.get(inspectionId);
    if (!inspection) return;

    const checkpoint = this.checkpoints.get(inspection.checkpointId);
    if (!checkpoint) return;

    inspection.status = 'in-progress';
    inspection.updatedAt = new Date();

    this.emit('inspectionStarted', inspection);

    try {
      const checkResults: QualityCheckResult[] = [];
      
      for (const checkId of checkpoint.checks) {
        const qualityCheck = this.qualityChecks.get(checkId);
        if (!qualityCheck) continue;

        const result = await this.performAutomatedCheck(qualityCheck, inspection);
        checkResults.push(result);
      }

      // Calculate overall score
      const totalWeight = checkResults.reduce((sum, result) => {
        const check = this.qualityChecks.get(result.checkId);
        return sum + (check?.weight || 1);
      }, 0);

      const weightedScore = checkResults.reduce((sum, result) => {
        const check = this.qualityChecks.get(result.checkId);
        return sum + (result.score * (check?.weight || 1));
      }, 0);

      inspection.overallScore = totalWeight > 0 ? weightedScore / totalWeight : 0;
      inspection.passed = inspection.overallScore >= checkpoint.passThreshold;
      inspection.checkResults = checkResults;
      inspection.status = 'completed';
      inspection.completedAt = new Date();
      inspection.updatedAt = new Date();

      // Detect defects if failed
      if (!inspection.passed) {
        inspection.defects = await this.detectDefects(inspection);
      }

      this.emit('inspectionCompleted', inspection);

    } catch (error) {
      inspection.status = 'failed';
      inspection.updatedAt = new Date();
      inspection.notes = `Automated inspection failed: ${error.message}`;
      this.emit('inspectionFailed', { inspection, error });
    }
  }

  private async performAutomatedCheck(qualityCheck: QualityCheck, inspection: QualityInspection): Promise<QualityCheckResult> {
    const result: QualityCheckResult = {
      checkId: qualityCheck.id,
      result: 'pass',
      score: 0,
      method: qualityCheck.method,
      timestamp: new Date()
    };

    try {
      switch (qualityCheck.method) {
        case 'sensor':
          result.score = await this.performSensorCheck(qualityCheck, inspection);
          break;
        case 'vision':
          const visionResult = await this.performVisionCheck(qualityCheck, inspection);
          result.score = visionResult.score;
          result.confidence = visionResult.confidence;
          break;
        case 'measurement':
          result.score = await this.performMeasurementCheck(qualityCheck, inspection);
          break;
        default:
          result.score = 100; // Skip for manual checks in automated mode
      }

      result.result = result.score >= 80 ? 'pass' : 
                     result.score >= 60 ? 'warning' : 'fail';

    } catch (error) {
      result.result = 'fail';
      result.score = 0;
      result.notes = `Check failed: ${error.message}`;
    }

    return result;
  }

  private async performSensorCheck(qualityCheck: QualityCheck, inspection: QualityInspection): Promise<number> {
    // Simulate sensor reading
    const expectedValue = qualityCheck.parameters.expectedValue || 0;
    const tolerance = qualityCheck.parameters.tolerance || 1;
    
    // Simulate measurement with some variation
    const measuredValue = expectedValue + (Math.random() - 0.5) * tolerance * 0.5;
    const deviation = Math.abs(measuredValue - expectedValue);
    
    return Math.max(0, 100 - (deviation / tolerance) * 100);
  }

  private async performVisionCheck(qualityCheck: QualityCheck, inspection: QualityInspection): Promise<{ score: number; confidence: number }> {
    // This would integrate with actual camera system
    // For now, simulate vision analysis
    
    const mockImage = await this.captureImage(inspection.printerId);
    const analysisResult = await this.visionAI.analyzeImage(mockImage, qualityCheck);
    
    return {
      score: analysisResult.qualityScore,
      confidence: analysisResult.confidence
    };
  }

  private async performMeasurementCheck(qualityCheck: QualityCheck, inspection: QualityInspection): Promise<number> {
    // This would integrate with measurement equipment
    // For now, simulate measurement
    
    const expectedValue = qualityCheck.parameters.expectedValue || 100;
    const tolerance = qualityCheck.parameters.tolerance || 0.1;
    
    // Simulate measurement accuracy
    const measuredValue = expectedValue + (Math.random() - 0.5) * tolerance;
    const deviation = Math.abs(measuredValue - expectedValue);
    const accuracy = Math.max(0, 100 - (deviation / tolerance) * 50);
    
    return accuracy;
  }

  private async captureImage(printerId: string): Promise<Buffer> {
    // This would interface with actual camera system
    // For now, create a mock image
    const canvas = createCanvas(640, 480);
    const ctx = canvas.getContext('2d');
    
    // Create a simple mock image
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, 640, 480);
    
    ctx.fillStyle = '#333';
    ctx.fillRect(100, 100, 400, 300);
    
    return canvas.toBuffer('image/png');
  }

  private async detectDefects(inspection: QualityInspection): Promise<QualityDefect[]> {
    const defects: QualityDefect[] = [];
    
    // Analyze failed check results to determine likely defects
    for (const result of inspection.checkResults) {
      if (result.result === 'fail') {
        const qualityCheck = this.qualityChecks.get(result.checkId);
        if (!qualityCheck) continue;
        
        const possibleDefects = this.getDefectsForCheck(qualityCheck, result);
        defects.push(...possibleDefects);
      }
    }
    
    return defects;
  }

  private getDefectsForCheck(qualityCheck: QualityCheck, result: QualityCheckResult): QualityDefect[] {
    const defects: QualityDefect[] = [];
    
    const defectMap: Record<string, Partial<QualityDefect>> = {
      'First Layer Adhesion': {
        type: 'warping',
        severity: 'major',
        cause: 'Poor bed adhesion or incorrect bed temperature',
        recommendedAction: 'adjust-settings'
      },
      'Dimensional Accuracy': {
        type: 'dimension-error',
        severity: 'major',
        cause: 'Incorrect calibration or thermal expansion',
        recommendedAction: 'rework'
      },
      'Surface Finish Quality': {
        type: 'surface-finish',
        severity: 'minor',
        cause: 'Incorrect print settings or material quality',
        recommendedAction: 'accept'
      },
      'Layer Adhesion Test': {
        type: 'layer-adhesion',
        severity: 'critical',
        cause: 'Insufficient temperature or speed issues',
        recommendedAction: 'scrap'
      }
    };

    const defectData = defectMap[qualityCheck.name];
    if (defectData) {
      const defect: QualityDefect = {
        id: uuidv4(),
        type: defectData.type as any,
        severity: defectData.severity as any,
        location: 'Overall part',
        description: `Failed ${qualityCheck.name} with score ${result.score}`,
        cause: defectData.cause,
        recommendedAction: defectData.recommendedAction as any,
        detectMethod: 'automated',
        confidence: result.confidence || 0.8,
        createdAt: new Date()
      };
      
      defects.push(defect);
    }
    
    return defects;
  }

  async updateInspectionStatus(inspectionId: string, status: QualityInspection['status'], metadata?: Partial<QualityInspection>): Promise<boolean> {
    const inspection = this.inspections.get(inspectionId);
    if (!inspection) return false;

    inspection.status = status;
    inspection.updatedAt = new Date();

    if (status === 'completed') {
      inspection.completedAt = new Date();
    }

    if (metadata) {
      Object.assign(inspection, metadata);
    }

    this.emit('inspectionStatusUpdated', inspection);
    return true;
  }

  async addCheckResult(inspectionId: string, checkResult: QualityCheckResult): Promise<boolean> {
    const inspection = this.inspections.get(inspectionId);
    if (!inspection) return false;

    inspection.checkResults.push(checkResult);
    
    // Recalculate overall score
    const checkpoint = this.checkpoints.get(inspection.checkpointId);
    if (checkpoint) {
      const totalWeight = inspection.checkResults.reduce((sum, result) => {
        const check = this.qualityChecks.get(result.checkId);
        return sum + (check?.weight || 1);
      }, 0);

      const weightedScore = inspection.checkResults.reduce((sum, result) => {
        const check = this.qualityChecks.get(result.checkId);
        return sum + (result.score * (check?.weight || 1));
      }, 0);

      inspection.overallScore = totalWeight > 0 ? weightedScore / totalWeight : 0;
      inspection.passed = inspection.overallScore >= checkpoint.passThreshold;
    }

    inspection.updatedAt = new Date();
    this.emit('checkResultAdded', { inspection, checkResult });
    
    return true;
  }

  async addInspectionImage(inspectionId: string, imageData: Omit<InspectionImage, 'id'>): Promise<InspectionImage> {
    const inspection = this.inspections.get(inspectionId);
    if (!inspection) {
      throw new Error('Inspection not found');
    }

    const image: InspectionImage = {
      ...imageData,
      id: uuidv4()
    };

    if (!inspection.images) {
      inspection.images = [];
    }

    inspection.images.push(image);
    inspection.updatedAt = new Date();

    // Perform automated analysis if it's a defect or overall image
    if (image.type === 'defect' || image.type === 'overall') {
      try {
        const analysisResult = await this.visionAI.analyzeImageForDefects(image.url);
        image.analysisResults = analysisResult;
      } catch (error) {
        console.warn('Failed to analyze image:', error);
      }
    }

    this.emit('inspectionImageAdded', { inspection, image });
    return image;
  }

  async createQualityTemplate(templateData: Omit<QualityTemplate, 'id' | 'usageCount' | 'createdAt' | 'updatedAt'>): Promise<QualityTemplate> {
    const template: QualityTemplate = {
      ...templateData,
      id: uuidv4(),
      usageCount: 0,
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.templates.set(template.id, template);
    this.emit('qualityTemplateCreated', template);
    
    return template;
  }

  async getQualityMetrics(days: number = 30): Promise<QualityMetrics> {
    const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    const inspections = Array.from(this.inspections.values())
      .filter(inspection => inspection.createdAt >= startDate);

    const totalInspections = inspections.length;
    const passedInspections = inspections.filter(i => i.passed).length;
    const failedInspections = totalInspections - passedInspections;

    const passRate = totalInspections > 0 ? (passedInspections / totalInspections) * 100 : 0;
    const failRate = totalInspections > 0 ? (failedInspections / totalInspections) * 100 : 0;

    const scores = inspections.map(i => i.overallScore);
    const averageScore = scores.length > 0 ? scores.reduce((sum, score) => sum + score, 0) / scores.length : 0;

    // Calculate inspection times
    const completedInspections = inspections.filter(i => i.completedAt && i.startedAt);
    const inspectionTimes = completedInspections.map(i => 
      (i.completedAt!.getTime() - i.startedAt.getTime()) / 1000 / 60 // minutes
    );

    const averageTime = inspectionTimes.length > 0 
      ? inspectionTimes.reduce((sum, time) => sum + time, 0) / inspectionTimes.length 
      : 0;

    inspectionTimes.sort((a, b) => a - b);
    const median = inspectionTimes.length > 0 
      ? inspectionTimes[Math.floor(inspectionTimes.length / 2)]
      : 0;
    const percentile95 = inspectionTimes.length > 0
      ? inspectionTimes[Math.floor(inspectionTimes.length * 0.95)]
      : 0;

    // Defect analysis
    const allDefects = inspections.flatMap(i => i.defects || []);
    const defectCounts = new Map<string, number>();
    const severityCounts = { minor: 0, major: 0, critical: 0 };

    allDefects.forEach(defect => {
      defectCounts.set(defect.type, (defectCounts.get(defect.type) || 0) + 1);
      severityCounts[defect.severity]++;
    });

    const mostCommon = Array.from(defectCounts.entries())
      .map(([type, count]) => ({
        type,
        count,
        percentage: (count / Math.max(allDefects.length, 1)) * 100
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    // Generate trend data (daily defect counts)
    const trends: Array<{ date: string; count: number }> = [];
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(Date.now() - i * 24 * 60 * 60 * 1000);
      const dayStart = new Date(date.setHours(0, 0, 0, 0));
      const dayEnd = new Date(date.setHours(23, 59, 59, 999));
      
      const dayDefects = allDefects.filter(d => 
        d.createdAt >= dayStart && d.createdAt <= dayEnd
      ).length;
      
      trends.push({
        date: dayStart.toISOString().split('T')[0],
        count: dayDefects
      });
    }

    // Printer performance analysis
    const printerStats = new Map<string, { total: number; passed: number; scores: number[]; defects: string[] }>();
    
    inspections.forEach(inspection => {
      const stats = printerStats.get(inspection.printerId) || { total: 0, passed: 0, scores: [], defects: [] };
      stats.total++;
      if (inspection.passed) stats.passed++;
      stats.scores.push(inspection.overallScore);
      
      if (inspection.defects) {
        inspection.defects.forEach(defect => {
          if (!stats.defects.includes(defect.type)) {
            stats.defects.push(defect.type);
          }
        });
      }
      
      printerStats.set(inspection.printerId, stats);
    });

    const printerPerformance = Array.from(printerStats.entries()).map(([printerId, stats]) => ({
      printerId,
      passRate: stats.total > 0 ? (stats.passed / stats.total) * 100 : 0,
      avgScore: stats.scores.length > 0 ? stats.scores.reduce((sum, s) => sum + s, 0) / stats.scores.length : 0,
      commonDefects: stats.defects.slice(0, 3)
    }));

    return {
      totalInspections,
      passRate: Math.round(passRate * 100) / 100,
      failRate: Math.round(failRate * 100) / 100,
      averageScore: Math.round(averageScore * 100) / 100,
      inspectionTime: {
        average: Math.round(averageTime * 100) / 100,
        median: Math.round(median * 100) / 100,
        percentile95: Math.round(percentile95 * 100) / 100
      },
      defectAnalysis: {
        mostCommon,
        bySeverity: severityCounts,
        trends
      },
      printerPerformance,
      materialPerformance: [], // Would be calculated similarly
      inspectorPerformance: [] // Would be calculated similarly
    };
  }

  // Getter methods
  getCheckpoint(id: string): QualityCheckpoint | undefined {
    return this.checkpoints.get(id);
  }

  getAllCheckpoints(): QualityCheckpoint[] {
    return Array.from(this.checkpoints.values()).sort((a, b) => a.order - b.order);
  }

  getQualityCheck(id: string): QualityCheck | undefined {
    return this.qualityChecks.get(id);
  }

  getAllQualityChecks(): QualityCheck[] {
    return Array.from(this.qualityChecks.values());
  }

  getInspection(id: string): QualityInspection | undefined {
    return this.inspections.get(id);
  }

  getAllInspections(): QualityInspection[] {
    return Array.from(this.inspections.values());
  }

  getInspectionsByJob(jobId: string): QualityInspection[] {
    return Array.from(this.inspections.values()).filter(i => i.jobId === jobId);
  }

  getPendingInspections(): QualityInspection[] {
    return Array.from(this.inspections.values()).filter(i => i.status === 'pending');
  }

  getTemplate(id: string): QualityTemplate | undefined {
    return this.templates.get(id);
  }

  getAllTemplates(): QualityTemplate[] {
    return Array.from(this.templates.values());
  }

  getTemplatesForMaterial(materialType: string): QualityTemplate[] {
    return Array.from(this.templates.values())
      .filter(template => template.materialTypes.includes(materialType));
  }
}

// Vision AI Engine for automated defect detection
class VisionAIEngine {
  async analyzeImage(imageBuffer: Buffer, qualityCheck: QualityCheck): Promise<{ qualityScore: number; confidence: number }> {
    // This would integrate with actual AI/ML models
    // For now, simulate analysis based on check parameters
    
    const baseScore = 80 + Math.random() * 20;
    const confidence = 0.8 + Math.random() * 0.2;
    
    return {
      qualityScore: baseScore,
      confidence
    };
  }

  async analyzeImageForDefects(imageUrl: string): Promise<VisionAnalysisResult> {
    // This would use actual computer vision models
    // For now, simulate defect detection
    
    const defectTypes = ['stringing', 'layer-adhesion', 'surface-finish'];
    const defectsFound = Math.floor(Math.random() * 3);
    
    const boundingBoxes = [];
    for (let i = 0; i < defectsFound; i++) {
      boundingBoxes.push({
        x: Math.random() * 500,
        y: Math.random() * 400,
        width: 50 + Math.random() * 100,
        height: 50 + Math.random() * 100,
        type: defectTypes[Math.floor(Math.random() * defectTypes.length)],
        confidence: 0.7 + Math.random() * 0.3
      });
    }

    return {
      defectDetection: {
        defectsFound,
        defectTypes: defectTypes.slice(0, defectsFound),
        confidence: 0.85,
        boundingBoxes
      },
      surfaceQuality: {
        roughness: 0.1 + Math.random() * 0.5,
        uniformity: 0.8 + Math.random() * 0.2,
        colorConsistency: 0.9 + Math.random() * 0.1,
        overallScore: 80 + Math.random() * 20
      }
    };
  }
}

export const qualityControl = new QualityControlSystem();