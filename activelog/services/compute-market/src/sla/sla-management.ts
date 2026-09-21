import { EventEmitter } from 'events';

export interface ServiceLevelAgreement {
  id: string;
  contractId: string;
  providerId: string;
  clientId: string;
  jobId?: string;
  name: string;
  description: string;
  status: 'active' | 'violated' | 'fulfilled' | 'suspended' | 'terminated';
  createdAt: Date;
  effectiveFrom: Date;
  expiresAt?: Date;
  lastUpdated: Date;
  objectives: ServiceLevelObjective[];
  penalties: SLAPenalty[];
  rewards: SLAReward[];
  metadata?: Record<string, any>;
}

export interface ServiceLevelObjective {
  id: string;
  name: string;
  description: string;
  category: 'performance' | 'availability' | 'reliability' | 'security' | 'capacity' | 'response_time';
  type: 'threshold' | 'target' | 'minimum' | 'maximum' | 'range';
  metrics: SLAMetric[];
  priority: 'critical' | 'high' | 'medium' | 'low';
  measurementWindow: string; // e.g., '1h', '24h', '7d'
  evaluationFrequency: string; // e.g., '5m', '1h', '1d'
  status: 'met' | 'at_risk' | 'violated' | 'unknown';
  lastEvaluation?: Date;
  violations: SLAViolation[];
}

export interface SLAMetric {
  name: string;
  source: string; // data source identifier
  query?: string;
  threshold?: number;
  target?: number;
  unit: string;
  aggregation: 'avg' | 'max' | 'min' | 'sum' | 'count' | 'percentile';
  percentile?: number; // for percentile aggregation
  operator: '>' | '<' | '>=' | '<=' | '==' | '!=' | 'between';
  value?: [number, number]; // for 'between' operator
}

export interface SLAViolation {
  id: string;
  objectiveId: string;
  startTime: Date;
  endTime?: Date;
  severity: 'minor' | 'major' | 'critical';
  description: string;
  actualValue: number;
  expectedValue: number;
  impact: ViolationImpact;
  resolution?: ViolationResolution;
  acknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: Date;
}

export interface ViolationImpact {
  affectedUsers: number;
  financialImpact: number;
  reputationImpact: number;
  serviceImpact: 'low' | 'medium' | 'high' | 'critical';
  downtimeMinutes?: number;
}

export interface ViolationResolution {
  status: 'investigating' | 'identified' | 'fixing' | 'resolved' | 'escalated';
  description: string;
  actionsTaken: string[];
  resolvedBy?: string;
  resolvedAt?: Date;
  rootCause?: string;
  preventiveMeasures?: string[];
}

export interface SLAPenalty {
  id: string;
  name: string;
  description: string;
  condition: PenaltyCondition;
  penalty: PenaltyAction;
  maxApplications?: number; // per period
  period?: string; // e.g., '1month'
  applied: number;
  lastApplied?: Date;
}

export interface PenaltyCondition {
  objectiveId: string;
  violationType: 'single' | 'repeated' | 'duration' | 'cumulative';
  threshold?: number;
  timeWindow?: string;
  severity?: SLAViolation['severity'];
}

export interface PenaltyAction {
  type: 'financial' | 'service_credit' | 'contract_adjustment' | 'termination' | 'escalation';
  amount?: number;
  percentage?: number;
  description: string;
  autoApply: boolean;
}

export interface SLAReward {
  id: string;
  name: string;
  description: string;
  condition: RewardCondition;
  reward: RewardAction;
  maxApplications?: number;
  period?: string;
  applied: number;
  lastApplied?: Date;
}

export interface RewardCondition {
  objectiveId: string;
  achievementType: 'exceeds_target' | 'consistent_performance' | 'improvement';
  threshold?: number;
  timeWindow: string;
  minimumDuration?: string;
}

export interface RewardAction {
  type: 'financial_bonus' | 'service_credit' | 'contract_extension' | 'reputation_boost';
  amount?: number;
  percentage?: number;
  description: string;
  autoApply: boolean;
}

export interface SLAReport {
  id: string;
  slaId: string;
  reportType: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'annual' | 'custom';
  periodStart: Date;
  periodEnd: Date;
  generatedAt: Date;
  summary: SLASummary;
  objectives: ObjectiveReport[];
  violations: ViolationSummary[];
  penalties: PenaltyReport[];
  rewards: RewardReport[];
  trends: TrendAnalysis[];
  recommendations: string[];
}

export interface SLASummary {
  overallCompliance: number; // percentage
  totalViolations: number;
  criticalViolations: number;
  averageResolutionTime: number; // minutes
  totalPenalties: number;
  totalRewards: number;
  uptime: number; // percentage
  availability: number; // percentage
}

export interface ObjectiveReport {
  objectiveId: string;
  name: string;
  compliance: number; // percentage
  actualValue: number;
  targetValue: number;
  trend: 'improving' | 'stable' | 'degrading';
  violationCount: number;
  lastViolation?: Date;
}

export interface ViolationSummary {
  severity: SLAViolation['severity'];
  count: number;
  totalDuration: number; // minutes
  averageDuration: number; // minutes
  impact: ViolationImpact;
}

export interface PenaltyReport {
  penaltyId: string;
  name: string;
  applications: number;
  totalAmount: number;
  description: string;
}

export interface RewardReport {
  rewardId: string;
  name: string;
  applications: number;
  totalAmount: number;
  description: string;
}

export interface TrendAnalysis {
  metric: string;
  period: string;
  trend: 'improving' | 'stable' | 'degrading';
  changePercentage: number;
  significance: 'high' | 'medium' | 'low';
  forecast?: number[];
}

export interface SLATemplate {
  id: string;
  name: string;
  description: string;
  category: 'compute' | 'storage' | 'network' | 'application' | 'custom';
  version: string;
  objectives: Omit<ServiceLevelObjective, 'id' | 'status' | 'lastEvaluation' | 'violations'>[];
  penalties: Omit<SLAPenalty, 'id' | 'applied' | 'lastApplied'>[];
  rewards: Omit<SLAReward, 'id' | 'applied' | 'lastApplied'>[];
  requiredMetrics: string[];
  recommendedEvaluation: string;
}

export class SLAManager extends EventEmitter {
  private slas: Map<string, ServiceLevelAgreement> = new Map();
  private violations: Map<string, SLAViolation[]> = new Map();
  private reports: Map<string, SLAReport[]> = new Map();
  private templates: Map<string, SLATemplate> = new Map();
  private evaluationTimer: NodeJS.Timeout | null = null;
  private reportTimer: NodeJS.Timeout | null = null;
  private metricsProvider: MetricsProvider;

  constructor(metricsProvider: MetricsProvider) {
    super();
    this.metricsProvider = metricsProvider;
    this.initializeDefaultTemplates();
    this.startEvaluationEngine();
  }

  public async createSLA(sla: Omit<ServiceLevelAgreement, 'id' | 'createdAt' | 'lastUpdated' | 'status'>): Promise<string> {
    const slaId = this.generateSLAId();
    const fullSLA: ServiceLevelAgreement = {
      ...sla,
      id: slaId,
      status: 'active',
      createdAt: new Date(),
      lastUpdated: new Date(),
      objectives: sla.objectives.map(obj => ({
        ...obj,
        status: 'unknown' as const,
        violations: []
      }))
    };

    this.slas.set(slaId, fullSLA);
    this.violations.set(slaId, []);
    this.reports.set(slaId, []);

    this.emit('slaCreated', fullSLA);
    return slaId;
  }

  public async createSLAFromTemplate(
    templateId: string,
    contractDetails: {
      contractId: string;
      providerId: string;
      clientId: string;
      jobId?: string;
      name: string;
      effectiveFrom: Date;
      expiresAt?: Date;
      customizations?: Partial<ServiceLevelAgreement>;
    }
  ): Promise<string> {
    const template = this.templates.get(templateId);
    if (!template) {
      throw new Error('SLA template not found');
    }

    const sla: Omit<ServiceLevelAgreement, 'id' | 'createdAt' | 'lastUpdated' | 'status'> = {
      contractId: contractDetails.contractId,
      providerId: contractDetails.providerId,
      clientId: contractDetails.clientId,
      jobId: contractDetails.jobId,
      name: contractDetails.name,
      description: template.description,
      effectiveFrom: contractDetails.effectiveFrom,
      expiresAt: contractDetails.expiresAt,
      objectives: template.objectives.map(obj => ({
        ...obj,
        id: this.generateObjectiveId(),
        status: 'unknown' as const,
        lastEvaluation: undefined,
        violations: []
      })),
      penalties: template.penalties.map(penalty => ({
        ...penalty,
        id: this.generatePenaltyId(),
        applied: 0,
        lastApplied: undefined
      })),
      rewards: template.rewards.map(reward => ({
        ...reward,
        id: this.generateRewardId(),
        applied: 0,
        lastApplied: undefined
      })),
      ...contractDetails.customizations
    };

    return await this.createSLA(sla);
  }

  public async updateSLA(slaId: string, updates: Partial<ServiceLevelAgreement>): Promise<void> {
    const sla = this.slas.get(slaId);
    if (!sla) {
      throw new Error('SLA not found');
    }

    const updatedSLA = {
      ...sla,
      ...updates,
      lastUpdated: new Date()
    };

    this.slas.set(slaId, updatedSLA);
    this.emit('slaUpdated', updatedSLA);
  }

  public async evaluateObjective(slaId: string, objectiveId: string): Promise<void> {
    const sla = this.slas.get(slaId);
    if (!sla) {
      throw new Error('SLA not found');
    }

    const objective = sla.objectives.find(obj => obj.id === objectiveId);
    if (!objective) {
      throw new Error('Objective not found');
    }

    const now = new Date();
    const windowStart = this.calculateWindowStart(now, objective.measurementWindow);
    
    try {
      const metricResults = await Promise.all(
        objective.metrics.map(metric => this.evaluateMetric(metric, windowStart, now))
      );

      const isObjectiveMet = this.evaluateObjectiveResults(objective, metricResults);
      const previousStatus = objective.status;
      
      objective.status = isObjectiveMet ? 'met' : 'violated';
      objective.lastEvaluation = now;

      if (!isObjectiveMet && previousStatus !== 'violated') {
        await this.createViolation(slaId, objective, metricResults);
      }

      if (previousStatus !== objective.status) {
        await this.handleStatusChange(slaId, objective, previousStatus);
      }

      sla.lastUpdated = now;
      this.slas.set(slaId, sla);

      this.emit('objectiveEvaluated', slaId, objective);

    } catch (error) {
      console.error(`Failed to evaluate objective ${objectiveId}:`, error);
      objective.status = 'unknown';
      objective.lastEvaluation = now;
    }
  }

  private async evaluateMetric(metric: SLAMetric, startTime: Date, endTime: Date): Promise<number> {
    try {
      const result = await this.metricsProvider.query(metric.source, {
        metric: metric.name,
        query: metric.query,
        aggregation: metric.aggregation,
        percentile: metric.percentile,
        startTime,
        endTime
      });

      return result.value;
    } catch (error) {
      console.error(`Failed to evaluate metric ${metric.name}:`, error);
      throw error;
    }
  }

  private evaluateObjectiveResults(objective: ServiceLevelObjective, metricResults: number[]): boolean {
    // Simple evaluation - all metrics must meet criteria
    for (let i = 0; i < objective.metrics.length; i++) {
      const metric = objective.metrics[i];
      const result = metricResults[i];

      if (!this.evaluateMetricResult(metric, result)) {
        return false;
      }
    }
    return true;
  }

  private evaluateMetricResult(metric: SLAMetric, value: number): boolean {
    switch (metric.operator) {
      case '>':
        return value > (metric.threshold || metric.target || 0);
      case '<':
        return value < (metric.threshold || metric.target || 0);
      case '>=':
        return value >= (metric.threshold || metric.target || 0);
      case '<=':
        return value <= (metric.threshold || metric.target || 0);
      case '==':
        return value === (metric.threshold || metric.target || 0);
      case '!=':
        return value !== (metric.threshold || metric.target || 0);
      case 'between':
        const [min, max] = metric.value || [0, 0];
        return value >= min && value <= max;
      default:
        return false;
    }
  }

  private async createViolation(
    slaId: string,
    objective: ServiceLevelObjective,
    metricResults: number[]
  ): Promise<void> {
    const violationId = this.generateViolationId();
    const slaViolations = this.violations.get(slaId) || [];

    // Calculate severity based on deviation from target
    const severity = this.calculateViolationSeverity(objective, metricResults);
    
    const violation: SLAViolation = {
      id: violationId,
      objectiveId: objective.id,
      startTime: new Date(),
      severity,
      description: this.generateViolationDescription(objective, metricResults),
      actualValue: metricResults[0] || 0, // Primary metric result
      expectedValue: objective.metrics[0]?.threshold || objective.metrics[0]?.target || 0,
      impact: await this.calculateViolationImpact(slaId, objective, severity),
      acknowledged: false
    };

    objective.violations.push(violation);
    slaViolations.push(violation);
    this.violations.set(slaId, slaViolations);

    await this.applyPenalties(slaId, violation);
    this.emit('slaViolation', slaId, violation);
  }

  private calculateViolationSeverity(
    objective: ServiceLevelObjective,
    metricResults: number[]
  ): SLAViolation['severity'] {
    // Simplified severity calculation
    const primaryMetric = objective.metrics[0];
    const result = metricResults[0] || 0;
    const expected = primaryMetric?.threshold || primaryMetric?.target || 0;
    
    if (expected === 0) return 'minor';
    
    const deviation = Math.abs((result - expected) / expected);
    
    if (deviation > 0.5) return 'critical';
    if (deviation > 0.2) return 'major';
    return 'minor';
  }

  private generateViolationDescription(
    objective: ServiceLevelObjective,
    metricResults: number[]
  ): string {
    const primaryMetric = objective.metrics[0];
    const result = metricResults[0] || 0;
    const expected = primaryMetric?.threshold || primaryMetric?.target || 0;
    
    return `${objective.name}: ${primaryMetric?.name} ${result}${primaryMetric?.unit} ${primaryMetric?.operator} ${expected}${primaryMetric?.unit}`;
  }

  private async calculateViolationImpact(
    slaId: string,
    objective: ServiceLevelObjective,
    severity: SLAViolation['severity']
  ): Promise<ViolationImpact> {
    // Simplified impact calculation
    const baseImpact = {
      'minor': { users: 10, financial: 100, reputation: 5, service: 'low' as const },
      'major': { users: 100, financial: 1000, reputation: 15, service: 'medium' as const },
      'critical': { users: 1000, financial: 10000, reputation: 30, service: 'critical' as const }
    };

    const impact = baseImpact[severity];
    
    return {
      affectedUsers: impact.users,
      financialImpact: impact.financial,
      reputationImpact: impact.reputation,
      serviceImpact: impact.service,
      downtimeMinutes: severity === 'critical' ? 60 : severity === 'major' ? 15 : 0
    };
  }

  private async applyPenalties(slaId: string, violation: SLAViolation): Promise<void> {
    const sla = this.slas.get(slaId);
    if (!sla) return;

    for (const penalty of sla.penalties) {
      if (this.shouldApplyPenalty(penalty, violation)) {
        await this.applyPenalty(slaId, penalty, violation);
      }
    }
  }

  private shouldApplyPenalty(penalty: SLAPenalty, violation: SLAViolation): boolean {
    const condition = penalty.condition;
    
    // Check objective match
    if (condition.objectiveId !== violation.objectiveId) {
      return false;
    }

    // Check severity match
    if (condition.severity && condition.severity !== violation.severity) {
      return false;
    }

    // Check max applications
    if (penalty.maxApplications && penalty.applied >= penalty.maxApplications) {
      return false;
    }

    // Additional condition checks would go here
    return true;
  }

  private async applyPenalty(slaId: string, penalty: SLAPenalty, violation: SLAViolation): Promise<void> {
    if (!penalty.penalty.autoApply) {
      this.emit('penaltyRequiresApproval', slaId, penalty, violation);
      return;
    }

    penalty.applied++;
    penalty.lastApplied = new Date();

    const sla = this.slas.get(slaId);
    if (sla) {
      sla.lastUpdated = new Date();
      this.slas.set(slaId, sla);
    }

    this.emit('penaltyApplied', slaId, penalty, violation);
  }

  public async acknowledgeViolation(
    slaId: string,
    violationId: string,
    acknowledgedBy: string,
    notes?: string
  ): Promise<void> {
    const slaViolations = this.violations.get(slaId) || [];
    const violation = slaViolations.find(v => v.id === violationId);
    
    if (violation) {
      violation.acknowledged = true;
      violation.acknowledgedBy = acknowledgedBy;
      violation.acknowledgedAt = new Date();
      
      this.emit('violationAcknowledged', slaId, violation, notes);
    }
  }

  public async resolveViolation(
    slaId: string,
    violationId: string,
    resolution: ViolationResolution
  ): Promise<void> {
    const slaViolations = this.violations.get(slaId) || [];
    const violation = slaViolations.find(v => v.id === violationId);
    
    if (violation) {
      violation.endTime = new Date();
      violation.resolution = resolution;
      
      this.emit('violationResolved', slaId, violation);
    }
  }

  private async handleStatusChange(
    slaId: string,
    objective: ServiceLevelObjective,
    previousStatus: ServiceLevelObjective['status']
  ): Promise<void> {
    if (objective.status === 'met' && previousStatus === 'violated') {
      await this.checkRewards(slaId, objective);
    }

    this.emit('objectiveStatusChanged', slaId, objective, previousStatus);
  }

  private async checkRewards(slaId: string, objective: ServiceLevelObjective): Promise<void> {
    const sla = this.slas.get(slaId);
    if (!sla) return;

    for (const reward of sla.rewards) {
      if (this.shouldApplyReward(reward, objective)) {
        await this.applyReward(slaId, reward, objective);
      }
    }
  }

  private shouldApplyReward(reward: SLAReward, objective: ServiceLevelObjective): boolean {
    const condition = reward.condition;
    
    if (condition.objectiveId !== objective.id) {
      return false;
    }

    if (reward.maxApplications && reward.applied >= reward.maxApplications) {
      return false;
    }

    // Additional reward condition checks would go here
    return true;
  }

  private async applyReward(slaId: string, reward: SLAReward, objective: ServiceLevelObjective): Promise<void> {
    if (!reward.reward.autoApply) {
      this.emit('rewardRequiresApproval', slaId, reward, objective);
      return;
    }

    reward.applied++;
    reward.lastApplied = new Date();

    const sla = this.slas.get(slaId);
    if (sla) {
      sla.lastUpdated = new Date();
      this.slas.set(slaId, sla);
    }

    this.emit('rewardApplied', slaId, reward, objective);
  }

  public async generateReport(
    slaId: string,
    reportType: SLAReport['reportType'],
    periodStart?: Date,
    periodEnd?: Date
  ): Promise<SLAReport> {
    const sla = this.slas.get(slaId);
    if (!sla) {
      throw new Error('SLA not found');
    }

    const now = new Date();
    const period = this.calculateReportPeriod(reportType, periodStart, periodEnd, now);
    
    const reportId = this.generateReportId();
    const report: SLAReport = {
      id: reportId,
      slaId,
      reportType,
      periodStart: period.start,
      periodEnd: period.end,
      generatedAt: now,
      summary: await this.generateSummary(slaId, period.start, period.end),
      objectives: await this.generateObjectiveReports(sla.objectives, period.start, period.end),
      violations: await this.generateViolationSummary(slaId, period.start, period.end),
      penalties: await this.generatePenaltyReports(sla.penalties, period.start, period.end),
      rewards: await this.generateRewardReports(sla.rewards, period.start, period.end),
      trends: await this.generateTrendAnalysis(slaId, period.start, period.end),
      recommendations: await this.generateRecommendations(slaId, period.start, period.end)
    };

    const slaReports = this.reports.get(slaId) || [];
    slaReports.push(report);
    this.reports.set(slaId, slaReports);

    this.emit('reportGenerated', report);
    return report;
  }

  private calculateReportPeriod(
    reportType: SLAReport['reportType'],
    periodStart?: Date,
    periodEnd?: Date,
    now: Date
  ): { start: Date; end: Date } {
    if (periodStart && periodEnd) {
      return { start: periodStart, end: periodEnd };
    }

    const periodMap = {
      'daily': 24 * 60 * 60 * 1000,
      'weekly': 7 * 24 * 60 * 60 * 1000,
      'monthly': 30 * 24 * 60 * 60 * 1000,
      'quarterly': 90 * 24 * 60 * 60 * 1000,
      'annual': 365 * 24 * 60 * 60 * 1000,
      'custom': 24 * 60 * 60 * 1000
    };

    const duration = periodMap[reportType];
    return {
      start: new Date(now.getTime() - duration),
      end: now
    };
  }

  private async generateSummary(slaId: string, startTime: Date, endTime: Date): Promise<SLASummary> {
    const violations = this.violations.get(slaId) || [];
    const periodViolations = violations.filter(v => 
      v.startTime >= startTime && v.startTime <= endTime
    );

    const criticalViolations = periodViolations.filter(v => v.severity === 'critical').length;
    const totalViolations = periodViolations.length;

    // Calculate other summary metrics
    const averageResolutionTime = this.calculateAverageResolutionTime(periodViolations);
    const uptime = this.calculateUptime(slaId, startTime, endTime);

    return {
      overallCompliance: totalViolations === 0 ? 100 : Math.max(0, 100 - (criticalViolations * 10)),
      totalViolations,
      criticalViolations,
      averageResolutionTime,
      totalPenalties: 0, // Would be calculated from actual penalty applications
      totalRewards: 0, // Would be calculated from actual reward applications
      uptime,
      availability: uptime
    };
  }

  private calculateAverageResolutionTime(violations: SLAViolation[]): number {
    const resolvedViolations = violations.filter(v => v.endTime && v.resolution);
    if (resolvedViolations.length === 0) return 0;

    const totalResolutionTime = resolvedViolations.reduce((sum, v) => {
      return sum + (v.endTime!.getTime() - v.startTime.getTime());
    }, 0);

    return totalResolutionTime / resolvedViolations.length / (1000 * 60); // Convert to minutes
  }

  private calculateUptime(slaId: string, startTime: Date, endTime: Date): number {
    // Simplified uptime calculation
    // In a real implementation, this would integrate with monitoring data
    return 99.9;
  }

  private async generateObjectiveReports(
    objectives: ServiceLevelObjective[],
    startTime: Date,
    endTime: Date
  ): Promise<ObjectiveReport[]> {
    return objectives.map(objective => {
      const periodViolations = objective.violations.filter(v => 
        v.startTime >= startTime && v.startTime <= endTime
      );

      return {
        objectiveId: objective.id,
        name: objective.name,
        compliance: periodViolations.length === 0 ? 100 : 85, // Simplified calculation
        actualValue: 95, // Would be calculated from actual metrics
        targetValue: 99, // From objective definition
        trend: 'stable' as const,
        violationCount: periodViolations.length,
        lastViolation: periodViolations.length > 0 ? 
          periodViolations[periodViolations.length - 1].startTime : undefined
      };
    });
  }

  private async generateViolationSummary(
    slaId: string,
    startTime: Date,
    endTime: Date
  ): Promise<ViolationSummary[]> {
    const violations = this.violations.get(slaId) || [];
    const periodViolations = violations.filter(v => 
      v.startTime >= startTime && v.startTime <= endTime
    );

    const summaryMap = new Map<SLAViolation['severity'], ViolationSummary>();

    for (const violation of periodViolations) {
      if (!summaryMap.has(violation.severity)) {
        summaryMap.set(violation.severity, {
          severity: violation.severity,
          count: 0,
          totalDuration: 0,
          averageDuration: 0,
          impact: {
            affectedUsers: 0,
            financialImpact: 0,
            reputationImpact: 0,
            serviceImpact: 'low',
            downtimeMinutes: 0
          }
        });
      }

      const summary = summaryMap.get(violation.severity)!;
      summary.count++;
      
      if (violation.endTime) {
        const duration = violation.endTime.getTime() - violation.startTime.getTime();
        summary.totalDuration += duration / (1000 * 60); // Convert to minutes
      }

      // Aggregate impact
      summary.impact.affectedUsers += violation.impact.affectedUsers;
      summary.impact.financialImpact += violation.impact.financialImpact;
      summary.impact.reputationImpact += violation.impact.reputationImpact;
      summary.impact.downtimeMinutes += violation.impact.downtimeMinutes || 0;
    }

    // Calculate averages
    for (const summary of summaryMap.values()) {
      summary.averageDuration = summary.count > 0 ? summary.totalDuration / summary.count : 0;
    }

    return Array.from(summaryMap.values());
  }

  private async generatePenaltyReports(
    penalties: SLAPenalty[],
    startTime: Date,
    endTime: Date
  ): Promise<PenaltyReport[]> {
    return penalties
      .filter(penalty => penalty.lastApplied && 
        penalty.lastApplied >= startTime && penalty.lastApplied <= endTime)
      .map(penalty => ({
        penaltyId: penalty.id,
        name: penalty.name,
        applications: penalty.applied,
        totalAmount: (penalty.penalty.amount || 0) * penalty.applied,
        description: penalty.description
      }));
  }

  private async generateRewardReports(
    rewards: SLAReward[],
    startTime: Date,
    endTime: Date
  ): Promise<RewardReport[]> {
    return rewards
      .filter(reward => reward.lastApplied && 
        reward.lastApplied >= startTime && reward.lastApplied <= endTime)
      .map(reward => ({
        rewardId: reward.id,
        name: reward.name,
        applications: reward.applied,
        totalAmount: (reward.reward.amount || 0) * reward.applied,
        description: reward.description
      }));
  }

  private async generateTrendAnalysis(
    slaId: string,
    startTime: Date,
    endTime: Date
  ): Promise<TrendAnalysis[]> {
    // Simplified trend analysis
    // In a real implementation, this would analyze historical data
    return [
      {
        metric: 'compliance',
        period: '30d',
        trend: 'stable',
        changePercentage: 0.5,
        significance: 'low',
        forecast: [98.5, 98.7, 98.9]
      }
    ];
  }

  private async generateRecommendations(
    slaId: string,
    startTime: Date,
    endTime: Date
  ): Promise<string[]> {
    const recommendations: string[] = [];
    
    const violations = this.violations.get(slaId) || [];
    const periodViolations = violations.filter(v => 
      v.startTime >= startTime && v.startTime <= endTime
    );

    if (periodViolations.length > 0) {
      recommendations.push('Consider implementing automated monitoring alerts for early violation detection');
    }

    const criticalViolations = periodViolations.filter(v => v.severity === 'critical');
    if (criticalViolations.length > 0) {
      recommendations.push('Review and strengthen disaster recovery procedures to reduce critical incident impact');
    }

    return recommendations;
  }

  private calculateWindowStart(endTime: Date, window: string): Date {
    const windowMap: Record<string, number> = {
      '1m': 60 * 1000,
      '5m': 5 * 60 * 1000,
      '15m': 15 * 60 * 1000,
      '1h': 60 * 60 * 1000,
      '4h': 4 * 60 * 60 * 1000,
      '12h': 12 * 60 * 60 * 1000,
      '24h': 24 * 60 * 60 * 1000,
      '7d': 7 * 24 * 60 * 60 * 1000,
      '30d': 30 * 24 * 60 * 60 * 1000
    };

    const duration = windowMap[window] || windowMap['1h'];
    return new Date(endTime.getTime() - duration);
  }

  private initializeDefaultTemplates(): void {
    const computeTemplate: SLATemplate = {
      id: 'compute_standard',
      name: 'Standard Compute SLA',
      description: 'Standard SLA for compute resource provision',
      category: 'compute',
      version: '1.0',
      objectives: [
        {
          name: 'Uptime',
          description: 'System availability',
          category: 'availability',
          type: 'minimum',
          metrics: [{
            name: 'uptime_percentage',
            source: 'monitoring',
            target: 99.9,
            unit: '%',
            aggregation: 'avg',
            operator: '>='
          }],
          priority: 'critical',
          measurementWindow: '24h',
          evaluationFrequency: '5m'
        }
      ],
      penalties: [
        {
          name: 'Downtime Penalty',
          description: 'Penalty for uptime violations',
          condition: {
            objectiveId: 'uptime',
            violationType: 'single',
            severity: 'critical'
          },
          penalty: {
            type: 'service_credit',
            percentage: 10,
            description: '10% service credit for downtime',
            autoApply: true
          }
        }
      ],
      rewards: [],
      requiredMetrics: ['uptime_percentage', 'response_time', 'error_rate'],
      recommendedEvaluation: '5m'
    };

    this.templates.set(computeTemplate.id, computeTemplate);
  }

  private startEvaluationEngine(): void {
    this.evaluationTimer = setInterval(async () => {
      await this.evaluateAllObjectives();
    }, 60 * 1000); // Every minute

    this.reportTimer = setInterval(async () => {
      await this.generateScheduledReports();
    }, 24 * 60 * 60 * 1000); // Daily
  }

  private async evaluateAllObjectives(): Promise<void> {
    for (const [slaId, sla] of this.slas) {
      if (sla.status !== 'active') continue;

      for (const objective of sla.objectives) {
        const evaluationDue = this.isEvaluationDue(objective);
        if (evaluationDue) {
          try {
            await this.evaluateObjective(slaId, objective.id);
          } catch (error) {
            console.error(`Failed to evaluate objective ${objective.id}:`, error);
          }
        }
      }
    }
  }

  private isEvaluationDue(objective: ServiceLevelObjective): boolean {
    if (!objective.lastEvaluation) return true;

    const frequencyMap: Record<string, number> = {
      '1m': 60 * 1000,
      '5m': 5 * 60 * 1000,
      '15m': 15 * 60 * 1000,
      '1h': 60 * 60 * 1000,
      '4h': 4 * 60 * 60 * 1000,
      '24h': 24 * 60 * 60 * 1000
    };

    const frequency = frequencyMap[objective.evaluationFrequency] || frequencyMap['1h'];
    const timeSinceLastEvaluation = Date.now() - objective.lastEvaluation.getTime();

    return timeSinceLastEvaluation >= frequency;
  }

  private async generateScheduledReports(): Promise<void> {
    // Generate daily reports for all active SLAs
    for (const [slaId, sla] of this.slas) {
      if (sla.status === 'active') {
        try {
          await this.generateReport(slaId, 'daily');
        } catch (error) {
          console.error(`Failed to generate daily report for SLA ${slaId}:`, error);
        }
      }
    }
  }

  public getSLA(slaId: string): ServiceLevelAgreement | undefined {
    return this.slas.get(slaId);
  }

  public getSLAViolations(slaId: string): SLAViolation[] {
    return this.violations.get(slaId) || [];
  }

  public getSLAReports(slaId: string): SLAReport[] {
    return this.reports.get(slaId) || [];
  }

  public getTemplate(templateId: string): SLATemplate | undefined {
    return this.templates.get(templateId);
  }

  public getAllTemplates(): SLATemplate[] {
    return Array.from(this.templates.values());
  }

  private generateSLAId(): string {
    return `sla_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateObjectiveId(): string {
    return `obj_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateViolationId(): string {
    return `vio_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generatePenaltyId(): string {
    return `pen_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateRewardId(): string {
    return `rew_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateReportId(): string {
    return `rep_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  public stop(): void {
    if (this.evaluationTimer) {
      clearInterval(this.evaluationTimer);
      this.evaluationTimer = null;
    }
    if (this.reportTimer) {
      clearInterval(this.reportTimer);
      this.reportTimer = null;
    }
  }
}

// Interface for metrics provider
export interface MetricsProvider {
  query(source: string, params: {
    metric: string;
    query?: string;
    aggregation: string;
    percentile?: number;
    startTime: Date;
    endTime: Date;
  }): Promise<{ value: number; timestamp: Date }>;
}

export default SLAManager;