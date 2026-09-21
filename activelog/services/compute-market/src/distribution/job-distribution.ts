import { EventEmitter } from 'events';

export interface ComputeJob {
  id: string;
  clientId: string;
  title: string;
  description: string;
  requirements: ComputeRequirements;
  budget: JobBudget;
  deadline: Date;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'created' | 'queued' | 'matching' | 'assigned' | 'running' | 'completed' | 'failed' | 'cancelled';
  createdAt: Date;
  assignedAt?: Date;
  completedAt?: Date;
  assignedProvider?: string;
  executionDetails?: JobExecution;
  tags: string[];
  attachments: JobAttachment[];
  estimatedDuration: number; // in minutes
}

export interface ComputeRequirements {
  cpu: {
    cores: number;
    architecture: 'x86_64' | 'arm64' | 'any';
    minClockSpeed?: number; // GHz
    features?: string[]; // AVX, SSE, etc.
  };
  memory: {
    amount: number; // GB
    type?: 'DDR4' | 'DDR5' | 'any';
  };
  gpu?: {
    required: boolean;
    type?: 'nvidia' | 'amd' | 'intel' | 'any';
    vram?: number; // GB
    computeCapability?: string;
    count?: number;
  };
  storage: {
    amount: number; // GB
    type: 'hdd' | 'ssd' | 'nvme' | 'any';
    iops?: number;
  };
  network: {
    bandwidth: number; // Mbps
    latency?: number; // ms
    region?: string;
  };
  os: {
    type: 'linux' | 'windows' | 'macos' | 'any';
    distribution?: string;
    version?: string;
  };
  containerization: {
    required: boolean;
    type?: 'docker' | 'kubernetes' | 'podman';
    isolation?: 'container' | 'vm' | 'bare_metal';
  };
  specialized: {
    ai_ml?: boolean;
    blockchain?: boolean;
    rendering?: boolean;
    scientific?: boolean;
    gaming?: boolean;
  };
}

export interface JobBudget {
  maxAmount: number;
  currency: 'USD' | 'EUR' | 'BTC' | 'ETH';
  paymentType: 'hourly' | 'fixed' | 'per_task';
  escrowRequired: boolean;
  autoRelease: boolean;
  bonusConditions?: BonusCondition[];
}

export interface BonusCondition {
  description: string;
  amount: number;
  criteria: 'early_completion' | 'high_quality' | 'low_resource_usage' | 'custom';
  threshold?: number;
}

export interface JobExecution {
  providerId: string;
  startTime: Date;
  endTime?: Date;
  resourcesUsed: ResourceUsage;
  outputLocation: string;
  logLocation: string;
  exitCode?: number;
  errorMessage?: string;
  checkpoints: ExecutionCheckpoint[];
}

export interface ResourceUsage {
  cpu: {
    averageUsage: number; // percentage
    peakUsage: number;
    coreHours: number;
  };
  memory: {
    averageUsage: number; // GB
    peakUsage: number;
  };
  gpu?: {
    averageUsage: number; // percentage
    peakUsage: number;
    memoryUsed: number; // GB
  };
  storage: {
    read: number; // GB
    write: number; // GB
    peak_iops: number;
  };
  network: {
    inbound: number; // GB
    outbound: number; // GB
    peakBandwidth: number; // Mbps
  };
}

export interface ExecutionCheckpoint {
  timestamp: Date;
  status: string;
  progress: number; // 0-100
  message?: string;
  resourceSnapshot: Partial<ResourceUsage>;
}

export interface JobAttachment {
  id: string;
  name: string;
  size: number; // bytes
  type: string;
  hash: string;
  downloadUrl: string;
  uploadedAt: Date;
}

export interface Provider {
  id: string;
  userId: string;
  name: string;
  capabilities: ComputeRequirements;
  availability: ProviderAvailability;
  pricing: ProviderPricing;
  reputation: number;
  location: string;
  status: 'online' | 'offline' | 'busy' | 'maintenance';
  lastSeen: Date;
  specializations: string[];
  certifications: string[];
}

export interface ProviderAvailability {
  totalCapacity: ComputeRequirements;
  availableCapacity: ComputeRequirements;
  queueLength: number;
  estimatedWaitTime: number; // minutes
  schedule?: AvailabilitySchedule[];
}

export interface AvailabilitySchedule {
  dayOfWeek: number; // 0-6
  startTime: string; // HH:MM
  endTime: string; // HH:MM
  timezone: string;
}

export interface ProviderPricing {
  cpu: number; // per core-hour
  memory: number; // per GB-hour
  gpu?: number; // per GPU-hour
  storage: number; // per GB-hour
  network: number; // per GB transfer
  baseRate: number; // minimum charge
  currency: string;
  discounts: PricingDiscount[];
}

export interface PricingDiscount {
  type: 'bulk' | 'duration' | 'loyalty' | 'off_peak';
  threshold: number;
  discount: number; // percentage
  description: string;
}

export interface JobMatch {
  jobId: string;
  providerId: string;
  score: number; // 0-100 compatibility score
  estimatedCost: number;
  estimatedDuration: number;
  availabilityWindow: {
    start: Date;
    end: Date;
  };
  matchFactors: MatchFactors;
}

export interface MatchFactors {
  requirementMatch: number; // 0-100
  priceMatch: number; // 0-100
  reputationScore: number; // 0-100
  locationMatch: number; // 0-100
  availabilityMatch: number; // 0-100
  specializationMatch: number; // 0-100
}

export interface DistributionQueue {
  priority: 'low' | 'medium' | 'high' | 'urgent';
  jobs: string[]; // job IDs
  processingOrder: 'fifo' | 'priority' | 'shortest_first' | 'cheapest_first';
}

export class JobDistributionSystem extends EventEmitter {
  private jobs: Map<string, ComputeJob> = new Map();
  private providers: Map<string, Provider> = new Map();
  private matches: Map<string, JobMatch[]> = new Map();
  private queues: Map<string, DistributionQueue> = new Map();
  private activeJobs: Map<string, string> = new Map(); // jobId -> providerId
  private providerWorkloads: Map<string, string[]> = new Map(); // providerId -> jobIds
  private matchingTimer: NodeJS.Timeout | null = null;
  private loadBalancer: LoadBalancer;

  constructor() {
    super();
    this.initializeQueues();
    this.loadBalancer = new LoadBalancer();
    this.startJobMatching();
  }

  private initializeQueues(): void {
    const priorities: ('low' | 'medium' | 'high' | 'urgent')[] = ['low', 'medium', 'high', 'urgent'];
    priorities.forEach(priority => {
      this.queues.set(priority, {
        priority,
        jobs: [],
        processingOrder: priority === 'urgent' ? 'shortest_first' : 'fifo'
      });
    });
  }

  public async submitJob(job: Omit<ComputeJob, 'id' | 'status' | 'createdAt'>): Promise<string> {
    const jobId = this.generateJobId();
    const computeJob: ComputeJob = {
      ...job,
      id: jobId,
      status: 'created',
      createdAt: new Date()
    };

    this.jobs.set(jobId, computeJob);
    await this.queueJob(jobId);

    this.emit('jobSubmitted', computeJob);
    return jobId;
  }

  private async queueJob(jobId: string): Promise<void> {
    const job = this.jobs.get(jobId);
    if (!job) return;

    job.status = 'queued';
    const queue = this.queues.get(job.priority);
    if (queue) {
      queue.jobs.push(jobId);
      this.jobs.set(jobId, job);
      this.emit('jobQueued', job);
    }
  }

  public async registerProvider(provider: Omit<Provider, 'id' | 'lastSeen'>): Promise<string> {
    const providerId = this.generateProviderId();
    const fullProvider: Provider = {
      ...provider,
      id: providerId,
      lastSeen: new Date()
    };

    this.providers.set(providerId, fullProvider);
    this.providerWorkloads.set(providerId, []);

    this.emit('providerRegistered', fullProvider);
    return providerId;
  }

  public async updateProviderStatus(providerId: string, status: Provider['status']): Promise<void> {
    const provider = this.providers.get(providerId);
    if (!provider) throw new Error('Provider not found');

    provider.status = status;
    provider.lastSeen = new Date();
    this.providers.set(providerId, provider);

    this.emit('providerStatusUpdated', provider);
  }

  public async updateProviderCapacity(providerId: string, capacity: Partial<ComputeRequirements>): Promise<void> {
    const provider = this.providers.get(providerId);
    if (!provider) throw new Error('Provider not found');

    provider.availability.availableCapacity = {
      ...provider.availability.availableCapacity,
      ...capacity
    };
    provider.lastSeen = new Date();
    this.providers.set(providerId, provider);

    this.emit('providerCapacityUpdated', provider);
  }

  private async findJobMatches(jobId: string): Promise<JobMatch[]> {
    const job = this.jobs.get(jobId);
    if (!job) return [];

    const availableProviders = Array.from(this.providers.values())
      .filter(p => p.status === 'online' && this.canHandleJob(p, job));

    const matches: JobMatch[] = [];

    for (const provider of availableProviders) {
      const match = await this.calculateMatch(job, provider);
      if (match.score >= 60) { // Minimum match threshold
        matches.push(match);
      }
    }

    // Sort by score descending, then by cost ascending
    matches.sort((a, b) => {
      if (Math.abs(a.score - b.score) < 5) {
        return a.estimatedCost - b.estimatedCost;
      }
      return b.score - a.score;
    });

    return matches.slice(0, 10); // Top 10 matches
  }

  private canHandleJob(provider: Provider, job: ComputeJob): boolean {
    const { requirements } = job;
    const { availableCapacity } = provider.availability;

    // Check basic resource requirements
    if (availableCapacity.cpu.cores < requirements.cpu.cores) return false;
    if (availableCapacity.memory.amount < requirements.memory.amount) return false;
    if (availableCapacity.storage.amount < requirements.storage.amount) return false;

    // Check GPU requirements
    if (requirements.gpu?.required && !availableCapacity.gpu) return false;
    if (requirements.gpu?.vram && (!availableCapacity.gpu || availableCapacity.gpu.vram! < requirements.gpu.vram)) {
      return false;
    }

    // Check network requirements
    if (availableCapacity.network.bandwidth < requirements.network.bandwidth) return false;

    // Check OS compatibility
    if (requirements.os.type !== 'any' && !this.isOSCompatible(provider.capabilities.os, requirements.os)) {
      return false;
    }

    return true;
  }

  private isOSCompatible(providerOS: any, requiredOS: any): boolean {
    if (requiredOS.type === 'any') return true;
    if (providerOS.type !== requiredOS.type) return false;
    
    // Additional OS-specific checks could go here
    return true;
  }

  private async calculateMatch(job: ComputeJob, provider: Provider): Promise<JobMatch> {
    const requirementMatch = this.calculateRequirementMatch(job.requirements, provider.capabilities);
    const priceMatch = this.calculatePriceMatch(job.budget, provider.pricing, job.requirements);
    const reputationScore = provider.reputation;
    const locationMatch = this.calculateLocationMatch(job.requirements.network.region, provider.location);
    const availabilityMatch = this.calculateAvailabilityMatch(provider.availability, job.estimatedDuration);
    const specializationMatch = this.calculateSpecializationMatch(job.tags, provider.specializations);

    const weightedScore = 
      (requirementMatch * 0.3) +
      (priceMatch * 0.25) +
      (reputationScore * 0.2) +
      (locationMatch * 0.1) +
      (availabilityMatch * 0.1) +
      (specializationMatch * 0.05);

    const estimatedCost = this.calculateJobCost(job, provider);
    const estimatedDuration = this.estimateJobDuration(job, provider);

    return {
      jobId: job.id,
      providerId: provider.id,
      score: Math.round(weightedScore),
      estimatedCost,
      estimatedDuration,
      availabilityWindow: {
        start: new Date(),
        end: new Date(Date.now() + provider.availability.estimatedWaitTime * 60 * 1000)
      },
      matchFactors: {
        requirementMatch,
        priceMatch,
        reputationScore,
        locationMatch,
        availabilityMatch,
        specializationMatch
      }
    };
  }

  private calculateRequirementMatch(requirements: ComputeRequirements, capabilities: ComputeRequirements): number {
    let score = 0;
    let totalChecks = 0;

    // CPU match
    if (capabilities.cpu.cores >= requirements.cpu.cores) score += 20;
    totalChecks += 20;

    // Memory match
    if (capabilities.memory.amount >= requirements.memory.amount) score += 20;
    totalChecks += 20;

    // GPU match
    if (requirements.gpu?.required) {
      if (capabilities.gpu && capabilities.gpu.vram! >= (requirements.gpu.vram || 0)) {
        score += 20;
      }
      totalChecks += 20;
    } else {
      score += 20;
      totalChecks += 20;
    }

    // Storage match
    if (capabilities.storage.amount >= requirements.storage.amount) score += 20;
    totalChecks += 20;

    // Network match
    if (capabilities.network.bandwidth >= requirements.network.bandwidth) score += 20;
    totalChecks += 20;

    return totalChecks > 0 ? (score / totalChecks) * 100 : 0;
  }

  private calculatePriceMatch(budget: JobBudget, pricing: ProviderPricing, requirements: ComputeRequirements): number {
    const estimatedCost = this.estimateProviderCost(pricing, requirements);
    if (estimatedCost <= budget.maxAmount) {
      const ratio = estimatedCost / budget.maxAmount;
      return (1 - ratio) * 100; // Lower cost = higher score
    }
    return 0;
  }

  private calculateLocationMatch(preferredRegion: string | undefined, providerLocation: string): number {
    if (!preferredRegion) return 75; // Neutral score
    if (preferredRegion === providerLocation) return 100;
    
    // Simple region matching (could be enhanced with geographic distance)
    const regionMapping: Record<string, string[]> = {
      'us': ['us-east', 'us-west', 'us-central'],
      'europe': ['eu-west', 'eu-central', 'eu-north'],
      'asia': ['asia-east', 'asia-southeast', 'asia-south']
    };

    for (const [region, subRegions] of Object.entries(regionMapping)) {
      if (subRegions.includes(preferredRegion) && subRegions.includes(providerLocation)) {
        return 85;
      }
    }

    return 50; // Different regions
  }

  private calculateAvailabilityMatch(availability: ProviderAvailability, jobDuration: number): number {
    const queueWaitScore = Math.max(0, 100 - (availability.queueLength * 10));
    const waitTimeScore = Math.max(0, 100 - (availability.estimatedWaitTime / 60)); // Convert to hours
    return (queueWaitScore + waitTimeScore) / 2;
  }

  private calculateSpecializationMatch(jobTags: string[], providerSpecializations: string[]): number {
    if (jobTags.length === 0) return 50;
    
    const matches = jobTags.filter(tag => 
      providerSpecializations.some(spec => 
        spec.toLowerCase().includes(tag.toLowerCase()) || 
        tag.toLowerCase().includes(spec.toLowerCase())
      )
    );

    return (matches.length / jobTags.length) * 100;
  }

  private calculateJobCost(job: ComputeJob, provider: Provider): number {
    const duration = job.estimatedDuration / 60; // Convert to hours
    const requirements = job.requirements;

    let cost = provider.pricing.baseRate;
    cost += provider.pricing.cpu * requirements.cpu.cores * duration;
    cost += provider.pricing.memory * requirements.memory.amount * duration;
    
    if (requirements.gpu?.required && provider.pricing.gpu) {
      cost += provider.pricing.gpu * (requirements.gpu.count || 1) * duration;
    }
    
    cost += provider.pricing.storage * requirements.storage.amount * duration;

    // Apply discounts
    for (const discount of provider.pricing.discounts) {
      if (this.qualifiesForDiscount(discount, cost, duration)) {
        cost *= (1 - discount.discount / 100);
      }
    }

    return cost;
  }

  private estimateProviderCost(pricing: ProviderPricing, requirements: ComputeRequirements): number {
    // Simplified cost estimation for matching
    const estimatedDuration = 1; // 1 hour default
    
    let cost = pricing.baseRate;
    cost += pricing.cpu * requirements.cpu.cores * estimatedDuration;
    cost += pricing.memory * requirements.memory.amount * estimatedDuration;
    
    if (requirements.gpu?.required && pricing.gpu) {
      cost += pricing.gpu * estimatedDuration;
    }

    return cost;
  }

  private qualifiesForDiscount(discount: PricingDiscount, cost: number, duration: number): boolean {
    switch (discount.type) {
      case 'bulk':
        return cost >= discount.threshold;
      case 'duration':
        return duration >= discount.threshold;
      default:
        return false;
    }
  }

  private estimateJobDuration(job: ComputeJob, provider: Provider): number {
    // This would use ML models or historical data in a real implementation
    const baseEstimate = job.estimatedDuration;
    const performanceFactor = provider.reputation / 100;
    return Math.round(baseEstimate / performanceFactor);
  }

  public async assignJob(jobId: string, providerId: string): Promise<void> {
    const job = this.jobs.get(jobId);
    const provider = this.providers.get(providerId);

    if (!job || !provider) {
      throw new Error('Job or provider not found');
    }

    if (job.status !== 'matching') {
      throw new Error(`Cannot assign job in status: ${job.status}`);
    }

    job.status = 'assigned';
    job.assignedProvider = providerId;
    job.assignedAt = new Date();

    this.jobs.set(jobId, job);
    this.activeJobs.set(jobId, providerId);

    // Add to provider workload
    const providerJobs = this.providerWorkloads.get(providerId) || [];
    providerJobs.push(jobId);
    this.providerWorkloads.set(providerId, providerJobs);

    // Update provider availability
    await this.updateProviderResourceAllocation(providerId, job.requirements, 'allocate');

    this.emit('jobAssigned', job, provider);
  }

  private async updateProviderResourceAllocation(
    providerId: string, 
    requirements: ComputeRequirements, 
    action: 'allocate' | 'deallocate'
  ): Promise<void> {
    const provider = this.providers.get(providerId);
    if (!provider) return;

    const multiplier = action === 'allocate' ? -1 : 1;
    const availability = provider.availability.availableCapacity;

    availability.cpu.cores += requirements.cpu.cores * multiplier;
    availability.memory.amount += requirements.memory.amount * multiplier;
    availability.storage.amount += requirements.storage.amount * multiplier;

    if (requirements.gpu?.required && availability.gpu) {
      availability.gpu.vram = (availability.gpu.vram || 0) + ((requirements.gpu.vram || 0) * multiplier);
    }

    this.providers.set(providerId, provider);
  }

  public async completeJob(jobId: string, executionDetails: JobExecution): Promise<void> {
    const job = this.jobs.get(jobId);
    if (!job) throw new Error('Job not found');

    job.status = 'completed';
    job.completedAt = new Date();
    job.executionDetails = executionDetails;

    this.jobs.set(jobId, job);

    // Remove from active jobs
    const providerId = this.activeJobs.get(jobId);
    if (providerId) {
      this.activeJobs.delete(jobId);
      
      // Remove from provider workload
      const providerJobs = this.providerWorkloads.get(providerId) || [];
      const jobIndex = providerJobs.indexOf(jobId);
      if (jobIndex !== -1) {
        providerJobs.splice(jobIndex, 1);
        this.providerWorkloads.set(providerId, providerJobs);
      }

      // Deallocate resources
      await this.updateProviderResourceAllocation(providerId, job.requirements, 'deallocate');
    }

    this.emit('jobCompleted', job);
  }

  private startJobMatching(): void {
    this.matchingTimer = setInterval(async () => {
      await this.processJobMatching();
    }, 10 * 1000); // Every 10 seconds
  }

  private async processJobMatching(): Promise<void> {
    // Process queues in priority order
    const priorities: ('urgent' | 'high' | 'medium' | 'low')[] = ['urgent', 'high', 'medium', 'low'];

    for (const priority of priorities) {
      const queue = this.queues.get(priority);
      if (!queue || queue.jobs.length === 0) continue;

      const jobsToProcess = queue.jobs.splice(0, 5); // Process up to 5 jobs per cycle

      for (const jobId of jobsToProcess) {
        await this.matchJob(jobId);
      }
    }
  }

  private async matchJob(jobId: string): Promise<void> {
    const job = this.jobs.get(jobId);
    if (!job || job.status !== 'queued') return;

    job.status = 'matching';
    this.jobs.set(jobId, job);

    const matches = await this.findJobMatches(jobId);
    this.matches.set(jobId, matches);

    if (matches.length > 0) {
      // Auto-assign to best match if conditions are met
      const bestMatch = matches[0];
      if (bestMatch.score >= 80 && job.budget.escrowRequired) {
        await this.assignJob(jobId, bestMatch.providerId);
      } else {
        this.emit('jobMatchesFound', job, matches);
      }
    } else {
      // No matches found, return to queue with lower priority
      job.status = 'queued';
      if (job.priority !== 'low') {
        const lowerPriority = this.getLowerPriority(job.priority);
        job.priority = lowerPriority;
      }
      await this.queueJob(jobId);
      this.emit('jobNoMatches', job);
    }
  }

  private getLowerPriority(priority: ComputeJob['priority']): ComputeJob['priority'] {
    const priorityMap: Record<ComputeJob['priority'], ComputeJob['priority']> = {
      'urgent': 'high',
      'high': 'medium',
      'medium': 'low',
      'low': 'low'
    };
    return priorityMap[priority];
  }

  public getJob(jobId: string): ComputeJob | undefined {
    return this.jobs.get(jobId);
  }

  public getJobMatches(jobId: string): JobMatch[] {
    return this.matches.get(jobId) || [];
  }

  public getProvider(providerId: string): Provider | undefined {
    return this.providers.get(providerId);
  }

  public getQueueStatus(): Record<string, number> {
    const status: Record<string, number> = {};
    for (const [priority, queue] of this.queues) {
      status[priority] = queue.jobs.length;
    }
    return status;
  }

  public getProviderWorkload(providerId: string): string[] {
    return this.providerWorkloads.get(providerId) || [];
  }

  private generateJobId(): string {
    return `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateProviderId(): string {
    return `provider_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  public stop(): void {
    if (this.matchingTimer) {
      clearInterval(this.matchingTimer);
      this.matchingTimer = null;
    }
  }
}

class LoadBalancer {
  public selectOptimalProvider(providers: Provider[], job: ComputeJob): Provider | null {
    if (providers.length === 0) return null;
    
    // Simple load balancing - select provider with lowest current workload
    // In a real implementation, this would be more sophisticated
    const workloadMap = new Map<string, number>();
    
    providers.forEach(provider => {
      workloadMap.set(provider.id, provider.availability.queueLength);
    });
    
    return providers.reduce((optimal, current) => {
      const currentLoad = workloadMap.get(current.id) || 0;
      const optimalLoad = workloadMap.get(optimal.id) || 0;
      return currentLoad < optimalLoad ? current : optimal;
    });
  }
}

export default JobDistributionSystem;