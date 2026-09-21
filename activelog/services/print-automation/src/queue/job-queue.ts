import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import { PrintJob, Printer3D, MaterialSpool } from '../fleet/printer-management';

export interface QueuedJob extends PrintJob {
  queuePosition: number;
  submittedAt: Date;
  scheduledFor?: Date;
  dependencies?: string[];
  batchId?: string;
  retryCount: number;
  maxRetries: number;
  timeoutMinutes?: number;
  requiredCapabilities?: string[];
  preferredPrinter?: string;
  estimatedStartTime?: Date;
  estimatedCompletionTime?: Date;
}

export interface JobBatch {
  id: string;
  name: string;
  description?: string;
  jobs: string[];
  priority: 'low' | 'normal' | 'high' | 'urgent';
  parallelExecution: boolean;
  maxConcurrentJobs?: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  progress: {
    total: number;
    completed: number;
    failed: number;
    percentage: number;
  };
}

export interface QueueMetrics {
  totalJobs: number;
  queuedJobs: number;
  runningJobs: number;
  completedJobs: number;
  failedJobs: number;
  averageWaitTime: number;
  averageProcessingTime: number;
  throughputPerHour: number;
  queueEfficiency: number;
  printerUtilization: number;
}

export interface JobFilter {
  status?: QueuedJob['status'];
  priority?: QueuedJob['priority'];
  customerId?: string;
  printerId?: string;
  materialType?: string;
  dateRange?: {
    start: Date;
    end: Date;
  };
  tags?: string[];
}

export interface SchedulingRule {
  id: string;
  name: string;
  description: string;
  isActive: boolean;
  priority: number;
  conditions: {
    timeWindow?: {
      start: string; // HH:MM format
      end: string; // HH:MM format
      days: ('monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday')[];
    };
    printerCriteria?: {
      models?: string[];
      capabilities?: string[];
      excludePrinters?: string[];
    };
    jobCriteria?: {
      maxPrintTime?: number;
      minPrintTime?: number;
      materialTypes?: string[];
      priorities?: QueuedJob['priority'][];
    };
  };
  actions: {
    adjustPriority?: number;
    assignToPrinter?: string;
    delayUntil?: string;
    requireApproval?: boolean;
    notifyUsers?: string[];
  };
  createdAt: Date;
  updatedAt: Date;
}

export class JobQueueManager extends EventEmitter {
  private queue: Map<string, QueuedJob> = new Map();
  private batches: Map<string, JobBatch> = new Map();
  private schedulingRules: Map<string, SchedulingRule> = new Map();
  private processingJobs: Set<string> = new Set();
  private queueProcessor?: NodeJS.Timeout;
  private isProcessing = false;

  constructor() {
    super();
    this.initializeSchedulingRules();
    this.startQueueProcessor();
  }

  private initializeSchedulingRules(): void {
    // Create default scheduling rules
    const defaultRules: Omit<SchedulingRule, 'id' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'Urgent Jobs Priority',
        description: 'Process urgent jobs immediately',
        isActive: true,
        priority: 100,
        conditions: {
          jobCriteria: {
            priorities: ['urgent']
          }
        },
        actions: {
          adjustPriority: 1000
        }
      },
      {
        name: 'Night Shift Large Jobs',
        description: 'Schedule long jobs during night hours',
        isActive: true,
        priority: 80,
        conditions: {
          timeWindow: {
            start: '18:00',
            end: '06:00',
            days: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
          },
          jobCriteria: {
            minPrintTime: 8 * 60 * 60 // 8 hours in seconds
          }
        },
        actions: {
          adjustPriority: 50
        }
      },
      {
        name: 'Quick Jobs Business Hours',
        description: 'Prioritize quick jobs during business hours',
        isActive: true,
        priority: 70,
        conditions: {
          timeWindow: {
            start: '09:00',
            end: '17:00',
            days: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
          },
          jobCriteria: {
            maxPrintTime: 2 * 60 * 60 // 2 hours in seconds
          }
        },
        actions: {
          adjustPriority: 25
        }
      },
      {
        name: 'High-End Printer Assignment',
        description: 'Assign precision jobs to high-end printers',
        isActive: true,
        priority: 90,
        conditions: {
          printerCriteria: {
            capabilities: ['auto-leveling', 'enclosure']
          },
          jobCriteria: {
            materialTypes: ['ABS', 'PETG', 'Nylon']
          }
        },
        actions: {
          adjustPriority: 30
        }
      }
    ];

    defaultRules.forEach(ruleData => {
      const rule: SchedulingRule = {
        ...ruleData,
        id: uuidv4(),
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.schedulingRules.set(rule.id, rule);
    });
  }

  private startQueueProcessor(): void {
    this.queueProcessor = setInterval(() => {
      if (!this.isProcessing) {
        this.processQueue();
      }
    }, 5000); // Process every 5 seconds
  }

  async addJob(jobData: Omit<QueuedJob, 'id' | 'queuePosition' | 'submittedAt' | 'retryCount' | 'estimatedStartTime' | 'estimatedCompletionTime' | 'createdAt' | 'updatedAt'>): Promise<QueuedJob> {
    const job: QueuedJob = {
      ...jobData,
      id: uuidv4(),
      queuePosition: this.queue.size + 1,
      submittedAt: new Date(),
      retryCount: 0,
      maxRetries: jobData.maxRetries || 3,
      status: 'queued',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    // Apply scheduling rules
    this.applySchedulingRules(job);

    // Calculate estimated times
    this.calculateEstimatedTimes(job);

    this.queue.set(job.id, job);
    this.updateQueuePositions();

    this.emit('jobAdded', job);
    return job;
  }

  async addBatch(batchData: Omit<JobBatch, 'id' | 'createdAt' | 'progress'>): Promise<JobBatch> {
    const batch: JobBatch = {
      ...batchData,
      id: uuidv4(),
      createdAt: new Date(),
      progress: {
        total: batchData.jobs.length,
        completed: 0,
        failed: 0,
        percentage: 0
      }
    };

    this.batches.set(batch.id, batch);

    // Update jobs with batch ID
    batchData.jobs.forEach(jobId => {
      const job = this.queue.get(jobId);
      if (job) {
        job.batchId = batch.id;
        job.updatedAt = new Date();
      }
    });

    this.emit('batchCreated', batch);
    return batch;
  }

  private applySchedulingRules(job: QueuedJob): void {
    const activeRules = Array.from(this.schedulingRules.values())
      .filter(rule => rule.isActive)
      .sort((a, b) => b.priority - a.priority);

    for (const rule of activeRules) {
      if (this.matchesRuleConditions(job, rule)) {
        this.applyRuleActions(job, rule);
        this.emit('ruleApplied', { job: job.id, rule: rule.id });
      }
    }
  }

  private matchesRuleConditions(job: QueuedJob, rule: SchedulingRule): boolean {
    const { conditions } = rule;

    // Check time window
    if (conditions.timeWindow) {
      const now = new Date();
      const dayName = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'][now.getDay()];
      
      if (!conditions.timeWindow.days.includes(dayName as any)) {
        return false;
      }

      const currentTime = now.getHours() * 60 + now.getMinutes();
      const [startHour, startMin] = conditions.timeWindow.start.split(':').map(Number);
      const [endHour, endMin] = conditions.timeWindow.end.split(':').map(Number);
      const startTime = startHour * 60 + startMin;
      const endTime = endHour * 60 + endMin;

      if (startTime <= endTime) {
        if (currentTime < startTime || currentTime > endTime) {
          return false;
        }
      } else { // Crosses midnight
        if (currentTime > endTime && currentTime < startTime) {
          return false;
        }
      }
    }

    // Check job criteria
    if (conditions.jobCriteria) {
      const { jobCriteria } = conditions;
      
      if (jobCriteria.maxPrintTime && job.estimatedTime > jobCriteria.maxPrintTime) {
        return false;
      }
      
      if (jobCriteria.minPrintTime && job.estimatedTime < jobCriteria.minPrintTime) {
        return false;
      }
      
      if (jobCriteria.materialTypes && !jobCriteria.materialTypes.includes(job.materialRequirements.type)) {
        return false;
      }
      
      if (jobCriteria.priorities && !jobCriteria.priorities.includes(job.priority)) {
        return false;
      }
    }

    return true;
  }

  private applyRuleActions(job: QueuedJob, rule: SchedulingRule): void {
    const { actions } = rule;

    if (actions.adjustPriority) {
      // Adjust priority score for sorting
      job.priority = this.adjustPriorityLevel(job.priority, actions.adjustPriority);
    }

    if (actions.assignToPrinter) {
      job.preferredPrinter = actions.assignToPrinter;
    }

    if (actions.delayUntil) {
      const [hour, minute] = actions.delayUntil.split(':').map(Number);
      const delayDate = new Date();
      delayDate.setHours(hour, minute, 0, 0);
      
      if (delayDate <= new Date()) {
        delayDate.setDate(delayDate.getDate() + 1);
      }
      
      job.scheduledFor = delayDate;
    }

    if (actions.requireApproval) {
      job.status = 'waiting';
      this.emit('approvalRequired', job);
    }

    job.updatedAt = new Date();
  }

  private adjustPriorityLevel(currentPriority: QueuedJob['priority'], adjustment: number): QueuedJob['priority'] {
    const priorityValues = { low: 1, normal: 2, high: 3, urgent: 4 };
    const priorities = ['low', 'normal', 'high', 'urgent'] as const;
    
    const currentValue = priorityValues[currentPriority];
    const newValue = Math.max(1, Math.min(4, currentValue + Math.sign(adjustment)));
    
    return priorities[newValue - 1];
  }

  private calculateEstimatedTimes(job: QueuedJob): void {
    const queuedJobsAhead = Array.from(this.queue.values())
      .filter(j => j.status === 'queued' && j.priority >= job.priority)
      .length;

    const averageProcessingTime = 3600; // 1 hour default
    const estimatedWaitTime = queuedJobsAhead * averageProcessingTime;

    job.estimatedStartTime = new Date(Date.now() + estimatedWaitTime * 1000);
    job.estimatedCompletionTime = new Date(job.estimatedStartTime.getTime() + job.estimatedTime * 1000);
  }

  private async processQueue(): Promise<void> {
    this.isProcessing = true;

    try {
      const readyJobs = this.getReadyJobs();
      const availablePrinters = await this.getAvailablePrinters();

      for (const job of readyJobs) {
        if (availablePrinters.length === 0) break;

        const selectedPrinter = this.selectOptimalPrinter(job, availablePrinters);
        if (selectedPrinter) {
          await this.assignJobToPrinter(job, selectedPrinter);
          availablePrinters.splice(availablePrinters.indexOf(selectedPrinter), 1);
        }
      }

      // Process batches
      await this.processBatches();

      // Clean up completed jobs
      this.cleanupCompletedJobs();

    } catch (error) {
      this.emit('queueProcessingError', error);
    } finally {
      this.isProcessing = false;
    }
  }

  private getReadyJobs(): QueuedJob[] {
    const now = new Date();
    
    return Array.from(this.queue.values())
      .filter(job => {
        if (job.status !== 'queued') return false;
        if (job.scheduledFor && job.scheduledFor > now) return false;
        if (job.dependencies && !this.areDependenciesMet(job.dependencies)) return false;
        return true;
      })
      .sort((a, b) => {
        // Sort by priority first, then by submission time
        const priorityOrder = { urgent: 4, high: 3, normal: 2, low: 1 };
        const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
        
        if (priorityDiff !== 0) return priorityDiff;
        return a.submittedAt.getTime() - b.submittedAt.getTime();
      });
  }

  private areDependenciesMet(dependencies: string[]): boolean {
    return dependencies.every(depId => {
      const depJob = this.queue.get(depId);
      return depJob?.status === 'completed';
    });
  }

  private async getAvailablePrinters(): Promise<Printer3D[]> {
    // This would integrate with the printer fleet manager
    // For now, return mock data
    return [];
  }

  private selectOptimalPrinter(job: QueuedJob, availablePrinters: Printer3D[]): Printer3D | null {
    if (availablePrinters.length === 0) return null;

    // Prefer specific printer if specified
    if (job.preferredPrinter) {
      const preferred = availablePrinters.find(p => p.id === job.preferredPrinter);
      if (preferred) return preferred;
    }

    // Score printers based on job requirements
    const scoredPrinters = availablePrinters.map(printer => ({
      printer,
      score: this.calculatePrinterScore(job, printer)
    }));

    scoredPrinters.sort((a, b) => b.score - a.score);
    return scoredPrinters[0].printer;
  }

  private calculatePrinterScore(job: QueuedJob, printer: Printer3D): number {
    let score = 0;

    // Base score from printer quality metrics
    score += printer.qualityMetrics.successRate;

    // Material compatibility
    if (printer.materialLoaded?.type === job.materialRequirements.type) {
      score += 20;
    }

    // Build volume efficiency
    const jobVolume = job.estimatedMaterialUsage / 1.2; // Approximate volume from material
    const printerVolume = printer.specifications.buildVolume.x * 
                         printer.specifications.buildVolume.y * 
                         printer.specifications.buildVolume.z;
    
    if (jobVolume <= printerVolume * 0.8) {
      score += 15;
    }

    // Capability matching
    if (job.requiredCapabilities) {
      const printerCapabilities = this.getPrinterCapabilities(printer);
      const matchedCapabilities = job.requiredCapabilities
        .filter(cap => printerCapabilities.includes(cap)).length;
      
      score += matchedCapabilities * 10;
    }

    // Operation mode preference (garage vs enterprise)
    if (job.priority === 'urgent' && printer.operationMode === 'enterprise') {
      score += 25;
    }

    // Recent maintenance bonus
    const daysSinceLastMaintenance = Math.floor(
      (Date.now() - printer.qualityMetrics.lastQualityCheck.getTime()) / (24 * 60 * 60 * 1000)
    );
    
    if (daysSinceLastMaintenance <= 7) {
      score += 10;
    }

    return score;
  }

  private getPrinterCapabilities(printer: Printer3D): string[] {
    const capabilities: string[] = [];
    
    if (printer.specifications.hasAutoLeveling) capabilities.push('auto-leveling');
    if (printer.specifications.hasEnclosure) capabilities.push('enclosure');
    if (printer.specifications.hasFilamentSensor) capabilities.push('filament-sensor');
    if (printer.specifications.hasCamera) capabilities.push('camera');
    if (printer.specifications.hasHeatedBed) capabilities.push('heated-bed');
    
    if (printer.specifications.maxHotendTemp >= 280) capabilities.push('high-temp');
    if (printer.specifications.nozzleDiameter.includes(0.2)) capabilities.push('fine-detail');
    if (printer.specifications.buildVolume.x >= 300) capabilities.push('large-build');
    
    return capabilities;
  }

  private async assignJobToPrinter(job: QueuedJob, printer: Printer3D): Promise<void> {
    job.status = 'preparing';
    job.printerId = printer.id;
    job.updatedAt = new Date();
    
    this.processingJobs.add(job.id);
    this.emit('jobAssigned', { job, printer });

    // This would integrate with the printer fleet manager
    // For now, just emit the event
  }

  private async processBatches(): Promise<void> {
    for (const [batchId, batch] of this.batches) {
      if (batch.status !== 'pending' && batch.status !== 'running') continue;

      const batchJobs = batch.jobs.map(jobId => this.queue.get(jobId)).filter(Boolean) as QueuedJob[];
      const completedJobs = batchJobs.filter(job => job.status === 'completed');
      const failedJobs = batchJobs.filter(job => job.status === 'failed');
      const runningJobs = batchJobs.filter(job => job.status === 'printing' || job.status === 'preparing');

      // Update batch progress
      batch.progress.completed = completedJobs.length;
      batch.progress.failed = failedJobs.length;
      batch.progress.percentage = Math.round((completedJobs.length / batch.progress.total) * 100);

      // Update batch status
      if (batch.status === 'pending' && runningJobs.length > 0) {
        batch.status = 'running';
        batch.startedAt = new Date();
        this.emit('batchStarted', batch);
      } else if (completedJobs.length + failedJobs.length === batch.progress.total) {
        batch.status = failedJobs.length === 0 ? 'completed' : 'failed';
        batch.completedAt = new Date();
        this.emit('batchCompleted', batch);
      }
    }
  }

  private cleanupCompletedJobs(): void {
    const cutoffDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000); // 7 days ago
    
    for (const [jobId, job] of this.queue) {
      if ((job.status === 'completed' || job.status === 'failed') && 
          job.completedAt && job.completedAt < cutoffDate) {
        this.queue.delete(jobId);
        this.processingJobs.delete(jobId);
        this.emit('jobArchived', job);
      }
    }
  }

  private updateQueuePositions(): void {
    const sortedJobs = Array.from(this.queue.values())
      .filter(job => job.status === 'queued')
      .sort((a, b) => {
        const priorityOrder = { urgent: 4, high: 3, normal: 2, low: 1 };
        const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
        if (priorityDiff !== 0) return priorityDiff;
        return a.submittedAt.getTime() - b.submittedAt.getTime();
      });

    sortedJobs.forEach((job, index) => {
      job.queuePosition = index + 1;
    });
  }

  async updateJobStatus(jobId: string, status: QueuedJob['status'], metadata?: any): Promise<boolean> {
    const job = this.queue.get(jobId);
    if (!job) return false;

    const oldStatus = job.status;
    job.status = status;
    job.updatedAt = new Date();

    if (status === 'completed' || status === 'failed') {
      job.completedAt = new Date();
      this.processingJobs.delete(jobId);
    }

    if (metadata) {
      Object.assign(job, metadata);
    }

    this.emit('jobStatusChanged', { job, oldStatus, newStatus: status });
    return true;
  }

  async retryJob(jobId: string): Promise<boolean> {
    const job = this.queue.get(jobId);
    if (!job || job.retryCount >= job.maxRetries) return false;

    job.status = 'queued';
    job.retryCount++;
    job.updatedAt = new Date();
    job.queuePosition = 1; // High priority for retries

    this.updateQueuePositions();
    this.emit('jobRetried', job);
    return true;
  }

  async cancelJob(jobId: string): Promise<boolean> {
    const job = this.queue.get(jobId);
    if (!job) return false;

    job.status = 'cancelled';
    job.completedAt = new Date();
    job.updatedAt = new Date();
    
    this.processingJobs.delete(jobId);
    this.emit('jobCancelled', job);
    return true;
  }

  async pauseQueue(): Promise<void> {
    this.isProcessing = true; // Prevent new job assignments
    this.emit('queuePaused');
  }

  async resumeQueue(): Promise<void> {
    this.isProcessing = false;
    this.emit('queueResumed');
  }

  async getQueueMetrics(): Promise<QueueMetrics> {
    const jobs = Array.from(this.queue.values());
    const totalJobs = jobs.length;
    const queuedJobs = jobs.filter(j => j.status === 'queued').length;
    const runningJobs = jobs.filter(j => j.status === 'preparing' || j.status === 'printing').length;
    const completedJobs = jobs.filter(j => j.status === 'completed').length;
    const failedJobs = jobs.filter(j => j.status === 'failed').length;

    const completedJobsWithTimes = jobs.filter(j => j.status === 'completed' && j.startedAt && j.completedAt);
    
    const waitTimes = jobs
      .filter(j => j.startedAt)
      .map(j => (j.startedAt!.getTime() - j.submittedAt.getTime()) / 1000 / 60); // minutes
    
    const processingTimes = completedJobsWithTimes
      .map(j => (j.completedAt!.getTime() - j.startedAt!.getTime()) / 1000 / 60); // minutes

    const averageWaitTime = waitTimes.length > 0 
      ? waitTimes.reduce((sum, time) => sum + time, 0) / waitTimes.length 
      : 0;

    const averageProcessingTime = processingTimes.length > 0
      ? processingTimes.reduce((sum, time) => sum + time, 0) / processingTimes.length
      : 0;

    // Calculate throughput for last 24 hours
    const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const recentCompletedJobs = jobs.filter(j => 
      j.status === 'completed' && j.completedAt && j.completedAt > dayAgo
    );
    const throughputPerHour = recentCompletedJobs.length;

    return {
      totalJobs,
      queuedJobs,
      runningJobs,
      completedJobs,
      failedJobs,
      averageWaitTime: Math.round(averageWaitTime * 100) / 100,
      averageProcessingTime: Math.round(averageProcessingTime * 100) / 100,
      throughputPerHour,
      queueEfficiency: completedJobs > 0 ? (completedJobs / (completedJobs + failedJobs)) * 100 : 0,
      printerUtilization: 0 // This would come from printer fleet manager
    };
  }

  getJob(jobId: string): QueuedJob | undefined {
    return this.queue.get(jobId);
  }

  getAllJobs(): QueuedJob[] {
    return Array.from(this.queue.values());
  }

  getJobsByFilter(filter: JobFilter): QueuedJob[] {
    return Array.from(this.queue.values()).filter(job => {
      if (filter.status && job.status !== filter.status) return false;
      if (filter.priority && job.priority !== filter.priority) return false;
      if (filter.customerId && job.customerId !== filter.customerId) return false;
      if (filter.printerId && job.printerId !== filter.printerId) return false;
      if (filter.materialType && job.materialRequirements.type !== filter.materialType) return false;
      
      if (filter.dateRange) {
        const jobDate = job.createdAt;
        if (jobDate < filter.dateRange.start || jobDate > filter.dateRange.end) return false;
      }

      if (filter.tags) {
        const jobTags = job.tags || [];
        if (!filter.tags.every(tag => jobTags.includes(tag))) return false;
      }

      return true;
    });
  }

  getQueuedJobs(): QueuedJob[] {
    return Array.from(this.queue.values())
      .filter(job => job.status === 'queued')
      .sort((a, b) => a.queuePosition - b.queuePosition);
  }

  getBatch(batchId: string): JobBatch | undefined {
    return this.batches.get(batchId);
  }

  getAllBatches(): JobBatch[] {
    return Array.from(this.batches.values());
  }

  getSchedulingRules(): SchedulingRule[] {
    return Array.from(this.schedulingRules.values());
  }

  async addSchedulingRule(ruleData: Omit<SchedulingRule, 'id' | 'createdAt' | 'updatedAt'>): Promise<SchedulingRule> {
    const rule: SchedulingRule = {
      ...ruleData,
      id: uuidv4(),
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.schedulingRules.set(rule.id, rule);
    this.emit('schedulingRuleAdded', rule);
    return rule;
  }

  async updateSchedulingRule(ruleId: string, updates: Partial<SchedulingRule>): Promise<boolean> {
    const rule = this.schedulingRules.get(ruleId);
    if (!rule) return false;

    Object.assign(rule, updates, { updatedAt: new Date() });
    this.emit('schedulingRuleUpdated', rule);
    return true;
  }

  async deleteSchedulingRule(ruleId: string): Promise<boolean> {
    const rule = this.schedulingRules.get(ruleId);
    if (!rule) return false;

    this.schedulingRules.delete(ruleId);
    this.emit('schedulingRuleDeleted', rule);
    return true;
  }

  destroy(): void {
    if (this.queueProcessor) {
      clearInterval(this.queueProcessor);
      this.queueProcessor = undefined;
    }
    
    this.removeAllListeners();
  }
}

export const jobQueue = new JobQueueManager();