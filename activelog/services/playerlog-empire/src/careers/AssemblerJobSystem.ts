/**
 * Assembler Job System
 * Manages manufacturing jobs, assembly lines, worker training, and production optimization
 * Integrates with equipment and product development systems
 */

import { EventEmitter } from 'events';
import {
  Company,
  Employee,
  AssemblyLine,
  ProductionJob,
  WorkStation,
  SkillLevel,
  TrainingProgram,
  QualityMetrics,
  ProductionMetrics,
  ShiftSchedule,
  SafetyRecord
} from '../types/game-types';
import { EconomyEngine } from '../economy/EconomyEngine';

export interface AssemblerRole {
  id: string;
  title: string;
  description: string;
  requiredSkills: Record<string, number>; // skill -> required level (1-10)
  baseSalary: number;
  experienceLevel: 'entry' | 'experienced' | 'senior' | 'expert';
  responsibilities: string[];
  careerPath: string[];
  certificationRequirements?: string[];
}

export interface ProductionLine {
  id: string;
  companyId: string;
  name: string;
  product: string;
  capacity: number; // units per hour
  efficiency: number; // 0-1
  utilization: number; // 0-1
  stations: WorkStation[];
  workers: AssemblerWorker[];
  shifts: ShiftSchedule[];
  qualityGate: QualityControl;
  maintenanceSchedule: MaintenanceWindow[];
  safetyProtocols: SafetyProtocol[];
  createdAt: number;
}

export interface AssemblerWorker {
  id: string;
  employeeId: string;
  role: AssemblerRole;
  currentStation: string;
  skills: Record<string, number>;
  productivity: number; // 0-2 (100% = 1.0)
  qualityScore: number; // 0-1
  attendance: number; // 0-1
  experience: number; // months
  certifications: string[];
  trainingHistory: TrainingRecord[];
  performanceMetrics: WorkerMetrics;
  shiftPreference: 'day' | 'evening' | 'night' | 'rotating';
  safetyRecord: SafetyRecord;
  hiredAt: number;
}

export interface WorkStation {
  id: string;
  name: string;
  type: 'manual' | 'semi_automated' | 'automated';
  equipmentId?: string;
  requiredSkills: Record<string, number>;
  cycleTime: number; // minutes per unit
  qualityRate: number; // 0-1 (defect rate = 1 - qualityRate)
  maintenanceRequired: boolean;
  lastMaintenance?: number;
  assignedWorker?: string;
  status: 'operational' | 'maintenance' | 'breakdown' | 'idle';
}

export interface QualityControl {
  inspectionPoints: InspectionPoint[];
  qualityStandards: QualityStandard[];
  defectTracking: DefectRecord[];
  reworkProcess: ReworkProcedure[];
  qualityMetrics: QualityMetrics;
}

export interface TrainingProgram {
  id: string;
  name: string;
  description: string;
  duration: number; // hours
  cost: number;
  skillsImproved: Record<string, number>;
  prerequisites: string[];
  certification?: string;
  provider: 'internal' | 'external' | 'vendor';
  difficulty: 'basic' | 'intermediate' | 'advanced';
}

export interface ProductionSchedule {
  companyId: string;
  lineId: string;
  shifts: ShiftAssignment[];
  productionTargets: ProductionTarget[];
  resourceAllocation: ResourceAllocation;
  bottleneckAnalysis: BottleneckAnalysis;
  optimizationRecommendations: string[];
}

export interface ShiftAssignment {
  shift: 'day' | 'evening' | 'night';
  startTime: string; // HH:MM
  endTime: string; // HH:MM
  workers: string[]; // worker IDs
  supervisor: string;
  targets: {
    units: number;
    quality: number;
    efficiency: number;
  };
}

export interface ProductionMetrics {
  overall: {
    unitsProduced: number;
    defectRate: number;
    efficiency: number;
    throughput: number;
    costPerUnit: number;
  };
  byLine: Record<string, LineMetrics>;
  byWorker: Record<string, WorkerMetrics>;
  trends: {
    productivity: number[];
    quality: number[];
    efficiency: number[];
  };
}

export class AssemblerJobSystem extends EventEmitter {
  private assemblerRoles: Map<string, AssemblerRole> = new Map();
  private productionLines: Map<string, ProductionLine> = new Map();
  private workers: Map<string, AssemblerWorker> = new Map();
  private trainingPrograms: Map<string, TrainingProgram> = new Map();
  private schedules: Map<string, ProductionSchedule> = new Map();
  private economyEngine: EconomyEngine;

  constructor(economyEngine: EconomyEngine) {
    super();
    this.economyEngine = economyEngine;
    this.initializeAssemblerRoles();
    this.initializeTrainingPrograms();
  }

  /**
   * Initialize available assembler roles and career paths
   */
  private initializeAssemblerRoles(): void {
    const roles: AssemblerRole[] = [
      {
        id: 'assembly_trainee',
        title: 'Assembly Trainee',
        description: 'Entry-level position learning basic assembly operations',
        requiredSkills: {
          manual_dexterity: 3,
          attention_to_detail: 4,
          following_instructions: 5
        },
        baseSalary: 35000,
        experienceLevel: 'entry',
        responsibilities: [
          'Learn basic assembly procedures',
          'Follow safety protocols',
          'Maintain clean workspace',
          'Report quality issues'
        ],
        careerPath: ['assembly_operator', 'quality_inspector', 'team_lead']
      },
      {
        id: 'assembly_operator',
        title: 'Assembly Operator',
        description: 'Skilled worker performing standard assembly operations',
        requiredSkills: {
          manual_dexterity: 5,
          attention_to_detail: 6,
          equipment_operation: 4,
          quality_control: 4
        },
        baseSalary: 42000,
        experienceLevel: 'experienced',
        responsibilities: [
          'Operate assembly equipment',
          'Perform quality checks',
          'Meet production targets',
          'Train new employees'
        ],
        careerPath: ['senior_operator', 'quality_inspector', 'team_lead', 'setup_technician']
      },
      {
        id: 'senior_operator',
        title: 'Senior Assembly Operator',
        description: 'Experienced operator handling complex assemblies',
        requiredSkills: {
          manual_dexterity: 7,
          attention_to_detail: 7,
          equipment_operation: 6,
          quality_control: 6,
          problem_solving: 5
        },
        baseSalary: 52000,
        experienceLevel: 'senior',
        responsibilities: [
          'Handle complex assemblies',
          'Troubleshoot production issues',
          'Mentor junior operators',
          'Participate in continuous improvement'
        ],
        careerPath: ['team_lead', 'setup_technician', 'quality_supervisor', 'production_supervisor']
      },
      {
        id: 'setup_technician',
        title: 'Setup Technician',
        description: 'Specialist in equipment setup and changeovers',
        requiredSkills: {
          equipment_operation: 8,
          technical_knowledge: 7,
          problem_solving: 6,
          documentation: 5
        },
        baseSalary: 58000,
        experienceLevel: 'senior',
        responsibilities: [
          'Configure production equipment',
          'Perform line changeovers',
          'Optimize setup procedures',
          'Create setup documentation'
        ],
        careerPath: ['production_engineer', 'maintenance_specialist', 'production_supervisor'],
        certificationRequirements: ['equipment_certification', 'safety_certification']
      },
      {
        id: 'quality_inspector',
        title: 'Quality Inspector',
        description: 'Ensures product quality through inspection and testing',
        requiredSkills: {
          attention_to_detail: 8,
          quality_control: 7,
          measurement: 6,
          documentation: 6,
          analytical_thinking: 5
        },
        baseSalary: 50000,
        experienceLevel: 'experienced',
        responsibilities: [
          'Perform quality inspections',
          'Maintain quality records',
          'Investigate defects',
          'Recommend improvements'
        ],
        careerPath: ['quality_supervisor', 'quality_engineer', 'production_supervisor'],
        certificationRequirements: ['quality_certification']
      },
      {
        id: 'team_lead',
        title: 'Team Leader',
        description: 'Leads small production teams and coordinates activities',
        requiredSkills: {
          leadership: 6,
          communication: 6,
          equipment_operation: 6,
          quality_control: 6,
          problem_solving: 5
        },
        baseSalary: 55000,
        experienceLevel: 'senior',
        responsibilities: [
          'Lead production teams',
          'Coordinate daily activities',
          'Monitor performance',
          'Handle escalations'
        ],
        careerPath: ['production_supervisor', 'quality_supervisor', 'training_coordinator']
      },
      {
        id: 'production_supervisor',
        title: 'Production Supervisor',
        description: 'Manages entire production lines and multiple teams',
        requiredSkills: {
          leadership: 8,
          communication: 7,
          planning: 7,
          quality_control: 7,
          problem_solving: 7,
          cost_management: 5
        },
        baseSalary: 68000,
        experienceLevel: 'expert',
        responsibilities: [
          'Manage production operations',
          'Develop production schedules',
          'Ensure safety compliance',
          'Drive continuous improvement'
        ],
        careerPath: ['production_manager', 'operations_manager', 'plant_manager'],
        certificationRequirements: ['supervision_certification', 'safety_certification']
      }
    ];

    roles.forEach(role => {
      this.assemblerRoles.set(role.id, role);
    });
  }

  /**
   * Initialize training programs
   */
  private initializeTrainingPrograms(): void {
    const programs: TrainingProgram[] = [
      {
        id: 'basic_assembly',
        name: 'Basic Assembly Techniques',
        description: 'Fundamental assembly skills and safety',
        duration: 40,
        cost: 500,
        skillsImproved: {
          manual_dexterity: 1,
          attention_to_detail: 1,
          following_instructions: 2
        },
        prerequisites: [],
        provider: 'internal',
        difficulty: 'basic'
      },
      {
        id: 'quality_fundamentals',
        name: 'Quality Control Fundamentals',
        description: 'Basic quality control principles and techniques',
        duration: 24,
        cost: 800,
        skillsImproved: {
          quality_control: 2,
          attention_to_detail: 1,
          measurement: 1
        },
        prerequisites: ['basic_assembly'],
        provider: 'external',
        difficulty: 'basic'
      },
      {
        id: 'equipment_operation',
        name: 'Equipment Operation Certification',
        description: 'Safe and efficient equipment operation',
        duration: 32,
        cost: 1200,
        skillsImproved: {
          equipment_operation: 2,
          technical_knowledge: 1,
          safety_awareness: 2
        },
        prerequisites: ['basic_assembly'],
        certification: 'equipment_certified',
        provider: 'vendor',
        difficulty: 'intermediate'
      },
      {
        id: 'lean_manufacturing',
        name: 'Lean Manufacturing Principles',
        description: 'Continuous improvement and waste reduction',
        duration: 16,
        cost: 1500,
        skillsImproved: {
          problem_solving: 2,
          analytical_thinking: 1,
          process_improvement: 2
        },
        prerequisites: ['quality_fundamentals'],
        provider: 'external',
        difficulty: 'intermediate'
      },
      {
        id: 'leadership_development',
        name: 'Leadership Development Program',
        description: 'Leadership skills for team leads and supervisors',
        duration: 40,
        cost: 2500,
        skillsImproved: {
          leadership: 3,
          communication: 2,
          planning: 1,
          conflict_resolution: 2
        },
        prerequisites: ['lean_manufacturing'],
        certification: 'leadership_certified',
        provider: 'external',
        difficulty: 'advanced'
      },
      {
        id: 'advanced_troubleshooting',
        name: 'Advanced Troubleshooting',
        description: 'Complex problem-solving and root cause analysis',
        duration: 24,
        cost: 1800,
        skillsImproved: {
          problem_solving: 3,
          analytical_thinking: 2,
          technical_knowledge: 2
        },
        prerequisites: ['equipment_operation'],
        provider: 'vendor',
        difficulty: 'advanced'
      }
    ];

    programs.forEach(program => {
      this.trainingPrograms.set(program.id, program);
    });
  }

  /**
   * Create new production line
   */
  async createProductionLine(
    companyId: string,
    config: {
      name: string;
      product: string;
      capacity: number;
      layout: 'linear' | 'u_shape' | 'cellular';
      automationLevel: 'manual' | 'semi' | 'automated';
      qualityStandards: string[];
    }
  ): Promise<ProductionLine> {
    const company = await this.getCompany(companyId);
    if (!company) {
      throw new Error('Company not found');
    }

    const stations = this.generateWorkStations(config);
    const setupCost = this.calculateSetupCost(config, stations);

    if (company.cashFlow < setupCost) {
      throw new Error(`Insufficient funds for production line. Required: $${setupCost.toLocaleString()}`);
    }

    // Deduct setup cost
    company.cashFlow -= setupCost;

    const line: ProductionLine = {
      id: `line_${companyId}_${Date.now()}`,
      companyId,
      name: config.name,
      product: config.product,
      capacity: config.capacity,
      efficiency: 0.7, // Start at 70% efficiency
      utilization: 0,
      stations,
      workers: [],
      shifts: this.createDefaultShifts(),
      qualityGate: this.createQualityControl(config.qualityStandards),
      maintenanceSchedule: [],
      safetyProtocols: this.createSafetyProtocols(),
      createdAt: Date.now()
    };

    this.productionLines.set(line.id, line);

    this.emit('production:line:created', {
      companyId,
      lineId: line.id,
      setupCost,
      capacity: config.capacity
    });

    return line;
  }

  /**
   * Hire assembler worker
   */
  async hireWorker(
    companyId: string,
    roleId: string,
    candidateProfile: {
      skills: Record<string, number>;
      experience: number;
      salaryExpectation: number;
      availability: 'day' | 'evening' | 'night' | 'rotating';
    }
  ): Promise<AssemblerWorker> {
    const company = await this.getCompany(companyId);
    if (!company) {
      throw new Error('Company not found');
    }

    const role = this.assemblerRoles.get(roleId);
    if (!role) {
      throw new Error(`Role not found: ${roleId}`);
    }

    // Check if candidate meets requirements
    const meetsRequirements = this.evaluateCandidate(candidateProfile, role);
    if (!meetsRequirements.qualified) {
      throw new Error(`Candidate does not meet requirements: ${meetsRequirements.reasons.join(', ')}`);
    }

    // Calculate final salary offer
    const salaryOffer = this.calculateSalaryOffer(role, candidateProfile);

    if (company.cashFlow < salaryOffer * 12) {
      throw new Error('Insufficient funds for annual salary');
    }

    // Create employee record
    const employee: Employee = {
      id: `emp_${companyId}_${Date.now()}`,
      name: `Worker ${Date.now()}`,
      position: role.title,
      salary: salaryOffer,
      department: 'manufacturing',
      skills: candidateProfile.skills,
      hiredAt: Date.now(),
      performance: 1.0
    };

    const worker: AssemblerWorker = {
      id: `worker_${companyId}_${Date.now()}`,
      employeeId: employee.id,
      role,
      currentStation: '',
      skills: candidateProfile.skills,
      productivity: 0.8 + (candidateProfile.experience / 120), // Experience factor
      qualityScore: 0.85,
      attendance: 0.95,
      experience: candidateProfile.experience,
      certifications: [],
      trainingHistory: [],
      performanceMetrics: {
        productivity: [],
        quality: [],
        attendance: [],
        safety: []
      },
      shiftPreference: candidateProfile.availability,
      safetyRecord: {
        incidents: [],
        trainingCompleted: [],
        lastSafetyTraining: 0,
        safetyScore: 1.0
      },
      hiredAt: Date.now()
    };

    this.workers.set(worker.id, worker);

    // Add to company payroll
    company.employees = (company.employees || 0) + 1;
    company.cashFlow -= salaryOffer / 12; // First month salary

    this.emit('worker:hired', {
      companyId,
      workerId: worker.id,
      role: role.title,
      salary: salaryOffer
    });

    return worker;
  }

  /**
   * Assign worker to production line
   */
  async assignWorkerToLine(workerId: string, lineId: string, stationId: string): Promise<void> {
    const worker = this.workers.get(workerId);
    if (!worker) {
      throw new Error('Worker not found');
    }

    const line = this.productionLines.get(lineId);
    if (!line) {
      throw new Error('Production line not found');
    }

    const station = line.stations.find(s => s.id === stationId);
    if (!station) {
      throw new Error('Work station not found');
    }

    // Check if worker has required skills
    const skillsCheck = this.checkWorkerSkills(worker, station);
    if (!skillsCheck.qualified) {
      throw new Error(`Worker lacks required skills: ${skillsCheck.missingSkills.join(', ')}`);
    }

    // Remove from previous assignment if any
    if (worker.currentStation) {
      await this.unassignWorkerFromStation(workerId);
    }

    // Assign to new station
    worker.currentStation = stationId;
    station.assignedWorker = workerId;
    station.status = 'operational';

    // Add to line workers if not already there
    if (!line.workers.find(w => w.id === workerId)) {
      line.workers.push(worker);
    }

    this.emit('worker:assigned', {
      workerId,
      lineId,
      stationId,
      workerSkills: worker.skills
    });
  }

  /**
   * Provide training to worker
   */
  async trainWorker(workerId: string, programId: string): Promise<{
    success: boolean;
    skillsImproved: Record<string, number>;
    certification?: string;
    cost: number;
  }> {
    const worker = this.workers.get(workerId);
    if (!worker) {
      throw new Error('Worker not found');
    }

    const program = this.trainingPrograms.get(programId);
    if (!program) {
      throw new Error('Training program not found');
    }

    const company = await this.getCompany(worker.id.split('_')[1]); // Extract company ID
    if (!company) {
      throw new Error('Company not found');
    }

    // Check prerequisites
    const hasPrerequisites = program.prerequisites.every(prereq => {
      return worker.trainingHistory.some(t => t.programId === prereq && t.completed);
    });

    if (!hasPrerequisites) {
      throw new Error(`Worker does not meet prerequisites: ${program.prerequisites.join(', ')}`);
    }

    // Check funding
    if (company.cashFlow < program.cost) {
      throw new Error('Insufficient funds for training');
    }

    // Deduct cost
    company.cashFlow -= program.cost;

    // Apply skill improvements
    Object.entries(program.skillsImproved).forEach(([skill, improvement]) => {
      worker.skills[skill] = Math.min(10, (worker.skills[skill] || 0) + improvement);
    });

    // Add training record
    const trainingRecord = {
      programId,
      programName: program.name,
      completedAt: Date.now(),
      skillsGained: program.skillsImproved,
      certification: program.certification,
      cost: program.cost,
      completed: true
    };

    worker.trainingHistory.push(trainingRecord);

    // Add certification if applicable
    if (program.certification) {
      worker.certifications.push(program.certification);
    }

    // Improve productivity based on training
    const productivityBonus = Object.values(program.skillsImproved).reduce((sum, val) => sum + val, 0) * 0.02;
    worker.productivity = Math.min(2.0, worker.productivity + productivityBonus);

    this.emit('worker:trained', {
      workerId,
      programId,
      skillsImproved: program.skillsImproved,
      newProductivity: worker.productivity,
      cost: program.cost
    });

    return {
      success: true,
      skillsImproved: program.skillsImproved,
      certification: program.certification,
      cost: program.cost
    };
  }

  /**
   * Run production shift
   */
  async runProductionShift(
    lineId: string,
    shift: 'day' | 'evening' | 'night',
    duration: number = 8
  ): Promise<{
    unitsProduced: number;
    defects: number;
    efficiency: number;
    costs: number;
    incidents: number;
    metrics: ShiftMetrics;
  }> {
    const line = this.productionLines.get(lineId);
    if (!line) {
      throw new Error('Production line not found');
    }

    const company = await this.getCompany(line.companyId);
    if (!company) {
      throw new Error('Company not found');
    }

    // Calculate production metrics
    const activeStations = line.stations.filter(s => s.status === 'operational' && s.assignedWorker);
    if (activeStations.length === 0) {
      throw new Error('No operational stations with assigned workers');
    }

    let totalUnitsProduced = 0;
    let totalDefects = 0;
    let totalCosts = 0;
    let incidents = 0;

    // Process each station
    for (const station of activeStations) {
      const worker = this.workers.get(station.assignedWorker!);
      if (!worker) continue;

      const stationMetrics = this.calculateStationProduction(station, worker, duration);
      
      totalUnitsProduced += stationMetrics.unitsProduced;
      totalDefects += stationMetrics.defects;
      totalCosts += stationMetrics.costs;
      incidents += stationMetrics.incidents;

      // Update worker metrics
      this.updateWorkerMetrics(worker, stationMetrics);
    }

    // Apply line efficiency
    totalUnitsProduced = Math.floor(totalUnitsProduced * line.efficiency);

    // Calculate overall efficiency
    const theoreticalMax = line.capacity * duration;
    const efficiency = Math.min(1, totalUnitsProduced / theoreticalMax);

    // Update line metrics
    line.efficiency = Math.min(1, line.efficiency + (efficiency > line.efficiency ? 0.01 : -0.005));
    line.utilization = activeStations.length / line.stations.length;

    // Deduct production costs
    company.cashFlow -= totalCosts;

    // Generate revenue (simplified)
    const revenuePerUnit = 50; // Placeholder
    const revenue = totalUnitsProduced * revenuePerUnit * (1 - (totalDefects / Math.max(1, totalUnitsProduced)));
    company.revenue = (company.revenue || 0) + revenue;
    company.cashFlow += revenue;

    const metrics = {
      efficiency,
      qualityRate: 1 - (totalDefects / Math.max(1, totalUnitsProduced)),
      utilizationRate: line.utilization,
      throughput: totalUnitsProduced / duration,
      costPerUnit: totalCosts / Math.max(1, totalUnitsProduced)
    };

    this.emit('production:shift:completed', {
      lineId,
      shift,
      unitsProduced: totalUnitsProduced,
      revenue,
      efficiency,
      defectRate: totalDefects / Math.max(1, totalUnitsProduced)
    });

    return {
      unitsProduced: totalUnitsProduced,
      defects: totalDefects,
      efficiency,
      costs: totalCosts,
      incidents,
      metrics
    };
  }

  /**
   * Helper methods
   */
  private generateWorkStations(config: any): WorkStation[] {
    const stationCount = Math.ceil(config.capacity / 100);
    const stations: WorkStation[] = [];

    for (let i = 0; i < stationCount; i++) {
      stations.push({
        id: `station_${i + 1}`,
        name: `Assembly Station ${i + 1}`,
        type: config.automationLevel === 'manual' ? 'manual' : 
              config.automationLevel === 'semi' ? 'semi_automated' : 'automated',
        requiredSkills: {
          manual_dexterity: 5,
          attention_to_detail: 6,
          equipment_operation: config.automationLevel === 'manual' ? 3 : 7
        },
        cycleTime: 5, // minutes
        qualityRate: 0.95,
        maintenanceRequired: false,
        status: 'idle'
      });
    }

    return stations;
  }

  private calculateSetupCost(config: any, stations: WorkStation[]): number {
    const baseSetupCost = 50000;
    const stationCost = stations.length * 25000;
    const automationMultiplier = {
      manual: 1,
      semi: 1.5,
      automated: 3
    };

    return Math.floor((baseSetupCost + stationCost) * automationMultiplier[config.automationLevel as keyof typeof automationMultiplier]);
  }

  private createDefaultShifts(): ShiftSchedule[] {
    return [
      { shift: 'day', startTime: '06:00', endTime: '14:00', workers: [] },
      { shift: 'evening', startTime: '14:00', endTime: '22:00', workers: [] },
      { shift: 'night', startTime: '22:00', endTime: '06:00', workers: [] }
    ];
  }

  private createQualityControl(standards: string[]): QualityControl {
    return {
      inspectionPoints: [],
      qualityStandards: [],
      defectTracking: [],
      reworkProcess: [],
      qualityMetrics: {
        defectRate: 0,
        reworkRate: 0,
        firstPassYield: 0.95,
        customerComplaints: 0,
        qualityScore: 0.95
      }
    };
  }

  private createSafetyProtocols(): SafetyProtocol[] {
    return [];
  }

  private evaluateCandidate(profile: any, role: AssemblerRole): { qualified: boolean; reasons: string[] } {
    const reasons: string[] = [];
    let qualified = true;

    Object.entries(role.requiredSkills).forEach(([skill, required]) => {
      const candidateSkill = profile.skills[skill] || 0;
      if (candidateSkill < required) {
        qualified = false;
        reasons.push(`${skill}: required ${required}, candidate has ${candidateSkill}`);
      }
    });

    return { qualified, reasons };
  }

  private calculateSalaryOffer(role: AssemblerRole, profile: any): number {
    let offer = role.baseSalary;
    
    // Experience premium
    offer += profile.experience * 500;
    
    // Skill premium
    const skillBonus = Object.values(profile.skills).reduce((sum: number, skill: number) => sum + skill, 0) * 200;
    offer += skillBonus;

    // Market rate adjustment
    offer = Math.min(offer, profile.salaryExpectation * 1.1); // Don't exceed expectation by more than 10%

    return Math.floor(offer);
  }

  private checkWorkerSkills(worker: AssemblerWorker, station: WorkStation): { qualified: boolean; missingSkills: string[] } {
    const missingSkills: string[] = [];
    let qualified = true;

    Object.entries(station.requiredSkills).forEach(([skill, required]) => {
      const workerSkill = worker.skills[skill] || 0;
      if (workerSkill < required) {
        qualified = false;
        missingSkills.push(`${skill} (need ${required}, has ${workerSkill})`);
      }
    });

    return { qualified, missingSkills };
  }

  private async unassignWorkerFromStation(workerId: string): Promise<void> {
    const worker = this.workers.get(workerId);
    if (!worker || !worker.currentStation) return;

    // Find and clear station assignment
    for (const line of this.productionLines.values()) {
      const station = line.stations.find(s => s.assignedWorker === workerId);
      if (station) {
        station.assignedWorker = undefined;
        station.status = 'idle';
        break;
      }
    }

    worker.currentStation = '';
  }

  private calculateStationProduction(station: WorkStation, worker: AssemblerWorker, duration: number): any {
    const unitsPerHour = 60 / station.cycleTime;
    const baseUnits = unitsPerHour * duration * worker.productivity;
    const unitsProduced = Math.floor(baseUnits * (Math.random() * 0.2 + 0.9)); // ±10% variation

    const defects = Math.floor(unitsProduced * (1 - station.qualityRate) * (1 / worker.qualityScore));
    const costs = duration * (worker.role.baseSalary / 12 / 160); // Hourly cost approximation
    const incidents = Math.random() < 0.01 ? 1 : 0; // 1% chance of incident

    return { unitsProduced, defects, costs, incidents };
  }

  private updateWorkerMetrics(worker: AssemblerWorker, stationMetrics: any): void {
    // Update worker performance metrics
    worker.performanceMetrics.productivity.push(stationMetrics.unitsProduced);
    worker.performanceMetrics.quality.push(1 - (stationMetrics.defects / Math.max(1, stationMetrics.unitsProduced)));
    worker.performanceMetrics.safety.push(stationMetrics.incidents === 0 ? 1 : 0);

    // Keep only last 30 records
    if (worker.performanceMetrics.productivity.length > 30) {
      worker.performanceMetrics.productivity = worker.performanceMetrics.productivity.slice(-30);
      worker.performanceMetrics.quality = worker.performanceMetrics.quality.slice(-30);
      worker.performanceMetrics.safety = worker.performanceMetrics.safety.slice(-30);
    }
  }

  private async getCompany(companyId: string): Promise<Company | null> {
    return null; // Placeholder
  }

  /**
   * Public API methods
   */
  getAssemblerRoles(): AssemblerRole[] {
    return Array.from(this.assemblerRoles.values());
  }

  getTrainingPrograms(): TrainingProgram[] {
    return Array.from(this.trainingPrograms.values());
  }

  getProductionLine(lineId: string): ProductionLine | null {
    return this.productionLines.get(lineId) || null;
  }

  getCompanyProductionLines(companyId: string): ProductionLine[] {
    return Array.from(this.productionLines.values()).filter(line => line.companyId === companyId);
  }

  getWorker(workerId: string): AssemblerWorker | null {
    return this.workers.get(workerId) || null;
  }

  getCompanyWorkers(companyId: string): AssemblerWorker[] {
    return Array.from(this.workers.values()).filter(worker => 
      worker.id.includes(companyId)
    );
  }

  getProductionMetrics(companyId: string): ProductionMetrics {
    const lines = this.getCompanyProductionLines(companyId);
    const workers = this.getCompanyWorkers(companyId);

    return {
      overall: {
        unitsProduced: 0,
        defectRate: 0,
        efficiency: 0,
        throughput: 0,
        costPerUnit: 0
      },
      byLine: {},
      byWorker: {},
      trends: {
        productivity: [],
        quality: [],
        efficiency: []
      }
    };
  }
}

// Supporting interfaces
interface TrainingRecord {
  programId: string;
  programName: string;
  completedAt: number;
  skillsGained: Record<string, number>;
  certification?: string;
  cost: number;
  completed: boolean;
}

interface WorkerMetrics {
  productivity: number[];
  quality: number[];
  attendance: number[];
  safety: number[];
}

interface LineMetrics {
  efficiency: number;
  throughput: number;
  qualityRate: number;
  utilization: number;
  costPerUnit: number;
}

interface ShiftMetrics {
  efficiency: number;
  qualityRate: number;
  utilizationRate: number;
  throughput: number;
  costPerUnit: number;
}

interface InspectionPoint {
  id: string;
  location: string;
  type: string;
  criteria: string[];
}

interface QualityStandard {
  id: string;
  parameter: string;
  tolerance: string;
  measurement: string;
}

interface DefectRecord {
  id: string;
  type: string;
  severity: string;
  station: string;
  worker: string;
  timestamp: number;
}

interface ReworkProcedure {
  defectType: string;
  procedure: string[];
  estimatedTime: number;
  success_rate: number;
}

interface SafetyProtocol {
  id: string;
  name: string;
  procedures: string[];
  equipment: string[];
  training_required: boolean;
}

interface MaintenanceWindow {
  id: string;
  station: string;
  type: 'preventive' | 'corrective' | 'emergency';
  scheduled: number;
  duration: number;
  technician: string;
}

interface ProductionTarget {
  shift: string;
  units: number;
  quality: number;
  efficiency: number;
}

interface ResourceAllocation {
  workers: Record<string, string>; // worker -> station
  equipment: Record<string, string>; // equipment -> station
  materials: Record<string, number>; // material -> quantity
}

interface BottleneckAnalysis {
  bottleneck: string;
  severity: number;
  impact: number;
  recommendations: string[];
}