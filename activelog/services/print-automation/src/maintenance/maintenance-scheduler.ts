import { EventEmitter } from 'events';
import { CronJob } from 'cron';

export interface MaintenanceTask {
  id: string;
  printerId: string;
  type: MaintenanceType;
  title: string;
  description: string;
  estimatedDuration: number;
  priority: MaintenancePriority;
  requiredTools: string[];
  requiredParts: string[];
  instructions: string[];
  safetyNotes: string[];
  createdAt: Date;
  scheduledFor?: Date;
  completedAt?: Date;
  completedBy?: string;
  notes?: string;
  status: MaintenanceStatus;
}

export enum MaintenanceType {
  PREVENTIVE = 'preventive',
  CORRECTIVE = 'corrective',
  PREDICTIVE = 'predictive',
  EMERGENCY = 'emergency',
  CALIBRATION = 'calibration',
  CLEANING = 'cleaning',
  UPGRADE = 'upgrade'
}

export enum MaintenancePriority {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low'
}

export enum MaintenanceStatus {
  SCHEDULED = 'scheduled',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
  OVERDUE = 'overdue'
}

export interface MaintenanceSchedule {
  id: string;
  printerId: string;
  taskType: MaintenanceType;
  interval: MaintenanceInterval;
  cronPattern?: string;
  usageThreshold?: number;
  conditionThreshold?: number;
  isEnabled: boolean;
  lastExecuted?: Date;
  nextDue: Date;
  autoSchedule: boolean;
  template: MaintenanceTemplate;
}

export interface MaintenanceInterval {
  type: 'time' | 'usage' | 'condition';
  value: number;
  unit: 'hours' | 'days' | 'weeks' | 'months' | 'print_hours' | 'filament_meters' | 'cycles';
}

export interface MaintenanceTemplate {
  type: MaintenanceType;
  title: string;
  description: string;
  estimatedDuration: number;
  requiredTools: string[];
  requiredParts: string[];
  instructions: string[];
  safetyNotes: string[];
  priority: MaintenancePriority;
}

export interface PrinterUsageStats {
  printerId: string;
  totalPrintTime: number;
  totalFilamentUsed: number;
  totalPrintCycles: number;
  lastMaintenanceDate?: Date;
  currentConditionScore: number;
  hotendTemperatureHistory: number[];
  bedTemperatureHistory: number[];
  errorCount: number;
  lastUpdated: Date;
}

export interface MaintenanceRecord {
  taskId: string;
  printerId: string;
  type: MaintenanceType;
  completedAt: Date;
  completedBy: string;
  duration: number;
  partsReplaced: string[];
  issues: string[];
  recommendations: string[];
  cost: number;
  nextRecommendedMaintenance?: Date;
}

export class MaintenanceScheduler extends EventEmitter {
  private tasks: Map<string, MaintenanceTask> = new Map();
  private schedules: Map<string, MaintenanceSchedule> = new Map();
  private usageStats: Map<string, PrinterUsageStats> = new Map();
  private records: Map<string, MaintenanceRecord> = new Map();
  private cronJobs: Map<string, CronJob> = new Map();
  private templates: Map<string, MaintenanceTemplate> = new Map();
  private monitoringInterval?: NodeJS.Timeout;

  constructor() {
    super();
    this.initializeDefaultTemplates();
    this.startMonitoring();
  }

  private initializeDefaultTemplates(): void {
    const templates: MaintenanceTemplate[] = [
      {
        type: MaintenanceType.PREVENTIVE,
        title: 'Hotend Cleaning',
        description: 'Clean and inspect hotend assembly',
        estimatedDuration: 30,
        requiredTools: ['allen keys', 'cleaning filament', 'wire brush'],
        requiredParts: [],
        instructions: [
          'Heat hotend to 200°C',
          'Remove filament',
          'Insert cleaning filament',
          'Purge cleaning filament',
          'Cool down and inspect nozzle'
        ],
        safetyNotes: ['Use heat-resistant gloves', 'Ensure proper ventilation'],
        priority: MaintenancePriority.MEDIUM
      },
      {
        type: MaintenanceType.PREVENTIVE,
        title: 'Bed Leveling',
        description: 'Check and adjust print bed leveling',
        estimatedDuration: 15,
        requiredTools: ['feeler gauge', 'allen keys'],
        requiredParts: [],
        instructions: [
          'Home all axes',
          'Heat bed to printing temperature',
          'Check corner distances with feeler gauge',
          'Adjust bed screws as needed',
          'Run test print'
        ],
        safetyNotes: ['Wait for bed to heat up completely'],
        priority: MaintenancePriority.HIGH
      },
      {
        type: MaintenanceType.CALIBRATION,
        title: 'Belt Tension Check',
        description: 'Inspect and adjust belt tension',
        estimatedDuration: 20,
        requiredTools: ['belt tension gauge'],
        requiredParts: [],
        instructions: [
          'Power off printer',
          'Check X-axis belt tension',
          'Check Y-axis belt tension',
          'Adjust tension screws if needed',
          'Test axis movement'
        ],
        safetyNotes: ['Ensure printer is powered off'],
        priority: MaintenancePriority.MEDIUM
      },
      {
        type: MaintenanceType.CLEANING,
        title: 'Full Printer Cleaning',
        description: 'Complete cleaning of printer components',
        estimatedDuration: 60,
        requiredTools: ['compressed air', 'isopropyl alcohol', 'microfiber cloths'],
        requiredParts: [],
        instructions: [
          'Power off and unplug printer',
          'Remove print bed',
          'Clean bed with isopropyl alcohol',
          'Blow out dust with compressed air',
          'Clean exterior surfaces',
          'Lubricate moving parts'
        ],
        safetyNotes: ['Ensure printer is unplugged', 'Use proper ventilation'],
        priority: MaintenancePriority.LOW
      }
    ];

    templates.forEach(template => {
      const key = `${template.type}_${template.title.toLowerCase().replace(/\s+/g, '_')}`;
      this.templates.set(key, template);
    });
  }

  public createMaintenanceSchedule(
    printerId: string,
    taskType: MaintenanceType,
    interval: MaintenanceInterval,
    options: {
      cronPattern?: string;
      usageThreshold?: number;
      conditionThreshold?: number;
      autoSchedule?: boolean;
    } = {}
  ): string {
    const scheduleId = `schedule_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const templateKey = `${taskType}_${this.getDefaultTemplateKey(taskType)}`;
    const template = this.templates.get(templateKey) || this.createBasicTemplate(taskType);

    const schedule: MaintenanceSchedule = {
      id: scheduleId,
      printerId,
      taskType,
      interval,
      cronPattern: options.cronPattern,
      usageThreshold: options.usageThreshold,
      conditionThreshold: options.conditionThreshold,
      isEnabled: true,
      nextDue: this.calculateNextDueDate(interval),
      autoSchedule: options.autoSchedule || false,
      template
    };

    this.schedules.set(scheduleId, schedule);

    if (schedule.cronPattern && schedule.autoSchedule) {
      this.setupCronJob(schedule);
    }

    this.emit('scheduleCreated', schedule);
    return scheduleId;
  }

  private getDefaultTemplateKey(type: MaintenanceType): string {
    switch (type) {
      case MaintenanceType.PREVENTIVE:
        return 'hotend_cleaning';
      case MaintenanceType.CALIBRATION:
        return 'bed_leveling';
      case MaintenanceType.CLEANING:
        return 'full_printer_cleaning';
      default:
        return 'basic_maintenance';
    }
  }

  private createBasicTemplate(type: MaintenanceType): MaintenanceTemplate {
    return {
      type,
      title: `${type} Maintenance`,
      description: `Perform ${type} maintenance task`,
      estimatedDuration: 30,
      requiredTools: [],
      requiredParts: [],
      instructions: ['Follow standard maintenance procedures'],
      safetyNotes: ['Follow safety guidelines'],
      priority: MaintenancePriority.MEDIUM
    };
  }

  private calculateNextDueDate(interval: MaintenanceInterval): Date {
    const now = new Date();
    const nextDue = new Date(now);

    switch (interval.unit) {
      case 'hours':
        nextDue.setHours(nextDue.getHours() + interval.value);
        break;
      case 'days':
        nextDue.setDate(nextDue.getDate() + interval.value);
        break;
      case 'weeks':
        nextDue.setDate(nextDue.getDate() + interval.value * 7);
        break;
      case 'months':
        nextDue.setMonth(nextDue.getMonth() + interval.value);
        break;
      default:
        nextDue.setDate(nextDue.getDate() + 7);
    }

    return nextDue;
  }

  private setupCronJob(schedule: MaintenanceSchedule): void {
    if (!schedule.cronPattern) return;

    const job = new CronJob(schedule.cronPattern, () => {
      this.createMaintenanceTask(schedule);
    });

    this.cronJobs.set(schedule.id, job);
    job.start();
  }

  public createMaintenanceTask(
    schedule: MaintenanceSchedule,
    options: {
      scheduledFor?: Date;
      priority?: MaintenancePriority;
      customInstructions?: string[];
    } = {}
  ): string {
    const taskId = `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const task: MaintenanceTask = {
      id: taskId,
      printerId: schedule.printerId,
      type: schedule.taskType,
      title: schedule.template.title,
      description: schedule.template.description,
      estimatedDuration: schedule.template.estimatedDuration,
      priority: options.priority || schedule.template.priority,
      requiredTools: [...schedule.template.requiredTools],
      requiredParts: [...schedule.template.requiredParts],
      instructions: options.customInstructions || [...schedule.template.instructions],
      safetyNotes: [...schedule.template.safetyNotes],
      createdAt: new Date(),
      scheduledFor: options.scheduledFor || schedule.nextDue,
      status: MaintenanceStatus.SCHEDULED
    };

    this.tasks.set(taskId, task);
    
    schedule.lastExecuted = new Date();
    schedule.nextDue = this.calculateNextDueDate(schedule.interval);

    this.emit('taskCreated', task);
    return taskId;
  }

  public updatePrinterUsage(printerId: string, stats: Partial<PrinterUsageStats>): void {
    const existing = this.usageStats.get(printerId) || {
      printerId,
      totalPrintTime: 0,
      totalFilamentUsed: 0,
      totalPrintCycles: 0,
      currentConditionScore: 100,
      hotendTemperatureHistory: [],
      bedTemperatureHistory: [],
      errorCount: 0,
      lastUpdated: new Date()
    };

    const updated: PrinterUsageStats = {
      ...existing,
      ...stats,
      lastUpdated: new Date()
    };

    this.usageStats.set(printerId, updated);
    this.checkUsageBasedMaintenance(updated);
  }

  private checkUsageBasedMaintenance(stats: PrinterUsageStats): void {
    for (const [scheduleId, schedule] of this.schedules) {
      if (schedule.printerId !== stats.printerId || !schedule.isEnabled) continue;

      let shouldTrigger = false;

      if (schedule.interval.type === 'usage') {
        switch (schedule.interval.unit) {
          case 'print_hours':
            shouldTrigger = stats.totalPrintTime >= (schedule.usageThreshold || schedule.interval.value);
            break;
          case 'filament_meters':
            shouldTrigger = stats.totalFilamentUsed >= (schedule.usageThreshold || schedule.interval.value);
            break;
          case 'cycles':
            shouldTrigger = stats.totalPrintCycles >= (schedule.usageThreshold || schedule.interval.value);
            break;
        }
      } else if (schedule.interval.type === 'condition') {
        shouldTrigger = stats.currentConditionScore <= (schedule.conditionThreshold || 70);
      }

      if (shouldTrigger && schedule.autoSchedule) {
        this.createMaintenanceTask(schedule);
      }
    }
  }

  public completeMaintenanceTask(
    taskId: string,
    completedBy: string,
    details: {
      duration?: number;
      partsReplaced?: string[];
      issues?: string[];
      recommendations?: string[];
      cost?: number;
      notes?: string;
    } = {}
  ): boolean {
    const task = this.tasks.get(taskId);
    if (!task || task.status === MaintenanceStatus.COMPLETED) {
      return false;
    }

    task.status = MaintenanceStatus.COMPLETED;
    task.completedAt = new Date();
    task.completedBy = completedBy;
    task.notes = details.notes;

    const record: MaintenanceRecord = {
      taskId,
      printerId: task.printerId,
      type: task.type,
      completedAt: task.completedAt,
      completedBy,
      duration: details.duration || task.estimatedDuration,
      partsReplaced: details.partsReplaced || [],
      issues: details.issues || [],
      recommendations: details.recommendations || [],
      cost: details.cost || 0,
      nextRecommendedMaintenance: this.calculateNextMaintenanceDate(task.type)
    };

    this.records.set(taskId, record);

    const stats = this.usageStats.get(task.printerId);
    if (stats) {
      stats.lastMaintenanceDate = task.completedAt;
      stats.currentConditionScore = Math.min(100, stats.currentConditionScore + 20);
    }

    this.emit('taskCompleted', task, record);
    return true;
  }

  private calculateNextMaintenanceDate(type: MaintenanceType): Date {
    const now = new Date();
    const nextDate = new Date(now);

    switch (type) {
      case MaintenanceType.PREVENTIVE:
        nextDate.setDate(nextDate.getDate() + 30);
        break;
      case MaintenanceType.CALIBRATION:
        nextDate.setDate(nextDate.getDate() + 14);
        break;
      case MaintenanceType.CLEANING:
        nextDate.setDate(nextDate.getDate() + 7);
        break;
      default:
        nextDate.setDate(nextDate.getDate() + 21);
    }

    return nextDate;
  }

  private startMonitoring(): void {
    this.monitoringInterval = setInterval(() => {
      this.checkOverdueTasks();
      this.checkScheduledMaintenance();
      this.updateConditionScores();
    }, 60000);
  }

  private checkOverdueTasks(): void {
    const now = new Date();
    
    for (const [taskId, task] of this.tasks) {
      if (task.status === MaintenanceStatus.SCHEDULED && 
          task.scheduledFor && 
          task.scheduledFor < now) {
        task.status = MaintenanceStatus.OVERDUE;
        this.emit('taskOverdue', task);
      }
    }
  }

  private checkScheduledMaintenance(): void {
    const now = new Date();
    
    for (const [scheduleId, schedule] of this.schedules) {
      if (schedule.isEnabled && 
          schedule.nextDue <= now && 
          schedule.autoSchedule) {
        this.createMaintenanceTask(schedule);
      }
    }
  }

  private updateConditionScores(): void {
    for (const [printerId, stats] of this.usageStats) {
      const daysSinceLastMaintenance = stats.lastMaintenanceDate 
        ? (Date.now() - stats.lastMaintenanceDate.getTime()) / (1000 * 60 * 60 * 24)
        : 30;

      const degradationRate = Math.min(daysSinceLastMaintenance * 0.5, 20);
      const errorPenalty = stats.errorCount * 2;
      
      stats.currentConditionScore = Math.max(0, 
        100 - degradationRate - errorPenalty
      );
    }
  }

  public getUpcomingTasks(days: number = 7): MaintenanceTask[] {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() + days);

    return Array.from(this.tasks.values())
      .filter(task => 
        task.status === MaintenanceStatus.SCHEDULED &&
        task.scheduledFor &&
        task.scheduledFor <= cutoffDate
      )
      .sort((a, b) => {
        if (!a.scheduledFor || !b.scheduledFor) return 0;
        return a.scheduledFor.getTime() - b.scheduledFor.getTime();
      });
  }

  public getPrinterMaintenanceHistory(printerId: string): MaintenanceRecord[] {
    return Array.from(this.records.values())
      .filter(record => record.printerId === printerId)
      .sort((a, b) => b.completedAt.getTime() - a.completedAt.getTime());
  }

  public generateMaintenanceReport(printerId?: string): {
    summary: {
      totalTasks: number;
      completedTasks: number;
      overdueTasks: number;
      upcomingTasks: number;
      averageCompletionTime: number;
      totalCost: number;
    };
    tasksByType: Record<MaintenanceType, number>;
    printerConditions: Record<string, number>;
  } {
    const tasks = Array.from(this.tasks.values())
      .filter(task => !printerId || task.printerId === printerId);
    
    const records = Array.from(this.records.values())
      .filter(record => !printerId || record.printerId === printerId);

    const summary = {
      totalTasks: tasks.length,
      completedTasks: tasks.filter(t => t.status === MaintenanceStatus.COMPLETED).length,
      overdueTasks: tasks.filter(t => t.status === MaintenanceStatus.OVERDUE).length,
      upcomingTasks: this.getUpcomingTasks().length,
      averageCompletionTime: records.length ? 
        records.reduce((sum, r) => sum + r.duration, 0) / records.length : 0,
      totalCost: records.reduce((sum, r) => sum + r.cost, 0)
    };

    const tasksByType = tasks.reduce((acc, task) => {
      acc[task.type] = (acc[task.type] || 0) + 1;
      return acc;
    }, {} as Record<MaintenanceType, number>);

    const printerConditions = Object.fromEntries(
      Array.from(this.usageStats.entries())
        .filter(([id]) => !printerId || id === printerId)
        .map(([id, stats]) => [id, stats.currentConditionScore])
    );

    return {
      summary,
      tasksByType,
      printerConditions
    };
  }

  public shutdown(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }

    for (const job of this.cronJobs.values()) {
      job.stop();
    }

    this.cronJobs.clear();
  }
}