import { EventEmitter } from 'events';

export interface ReputationScore {
  userId: string;
  overall: number;
  reliability: number;
  performance: number;
  communication: number;
  security: number;
  uptime: number;
  responseTime: number;
  lastUpdated: Date;
}

export interface ReputationEvent {
  id: string;
  userId: string;
  type: 'job_completion' | 'uptime' | 'performance' | 'security_incident' | 'communication' | 'dispute';
  category: 'positive' | 'negative' | 'neutral';
  impact: number; // -100 to +100
  description: string;
  evidenceHash?: string;
  timestamp: Date;
  jobId?: string;
  reporterId?: string;
}

export interface ReputationMetrics {
  totalJobs: number;
  completedJobs: number;
  failedJobs: number;
  avgResponseTime: number;
  uptimePercentage: number;
  securityIncidents: number;
  disputeResolutions: number;
  totalEarnings: number;
  clientSatisfaction: number;
}

export interface ReputationTier {
  name: string;
  minScore: number;
  maxScore: number;
  benefits: string[];
  requirements: string[];
  color: string;
}

export interface UserProfile {
  userId: string;
  username: string;
  joinDate: Date;
  verificationLevel: 'unverified' | 'email' | 'phone' | 'id' | 'full';
  specializations: string[];
  badges: ReputationBadge[];
  tier: ReputationTier;
  publicKey?: string;
}

export interface ReputationBadge {
  id: string;
  name: string;
  description: string;
  icon: string;
  earnedDate: Date;
  criteria: string;
  rarity: 'common' | 'uncommon' | 'rare' | 'legendary';
}

export interface DisputeCase {
  id: string;
  jobId: string;
  complainantId: string;
  respondentId: string;
  type: 'quality' | 'deadline' | 'payment' | 'communication' | 'terms';
  status: 'open' | 'investigating' | 'resolved' | 'escalated';
  description: string;
  evidence: DisputeEvidence[];
  resolution?: string;
  moderatorId?: string;
  createdAt: Date;
  resolvedAt?: Date;
}

export interface DisputeEvidence {
  type: 'text' | 'image' | 'document' | 'log' | 'transaction';
  content: string;
  hash: string;
  submittedBy: string;
  timestamp: Date;
}

export class ReputationSystem extends EventEmitter {
  private scores: Map<string, ReputationScore> = new Map();
  private events: Map<string, ReputationEvent[]> = new Map();
  private metrics: Map<string, ReputationMetrics> = new Map();
  private profiles: Map<string, UserProfile> = new Map();
  private disputes: Map<string, DisputeCase> = new Map();
  private tiers: ReputationTier[] = [];
  private badges: Map<string, ReputationBadge[]> = new Map();
  private decayInterval: NodeJS.Timeout | null = null;

  constructor() {
    super();
    this.initializeTiers();
    this.startReputationDecay();
  }

  private initializeTiers(): void {
    this.tiers = [
      {
        name: 'Bronze',
        minScore: 0,
        maxScore: 25,
        benefits: ['Basic marketplace access', 'Standard support'],
        requirements: ['Complete identity verification'],
        color: '#CD7F32'
      },
      {
        name: 'Silver',
        minScore: 25,
        maxScore: 50,
        benefits: ['Priority job matching', '5% lower fees', 'Enhanced profile'],
        requirements: ['Complete 10 successful jobs', 'Maintain 90% uptime'],
        color: '#C0C0C0'
      },
      {
        name: 'Gold',
        minScore: 50,
        maxScore: 75,
        benefits: ['Premium job access', '10% lower fees', 'Early feature access'],
        requirements: ['Complete 50 successful jobs', 'Maintain 95% uptime', 'Zero security incidents'],
        color: '#FFD700'
      },
      {
        name: 'Platinum',
        minScore: 75,
        maxScore: 90,
        benefits: ['Exclusive high-value jobs', '15% lower fees', 'Priority support'],
        requirements: ['Complete 200 successful jobs', 'Maintain 99% uptime', 'Top 10% performance'],
        color: '#E5E4E2'
      },
      {
        name: 'Diamond',
        minScore: 90,
        maxScore: 100,
        benefits: ['Enterprise job access', '20% lower fees', 'Revenue sharing opportunities'],
        requirements: ['Complete 500 successful jobs', 'Maintain 99.9% uptime', 'Top 1% performance'],
        color: '#B9F2FF'
      }
    ];
  }

  public async initializeUser(userId: string, profile: Partial<UserProfile>): Promise<void> {
    const defaultScore: ReputationScore = {
      userId,
      overall: 50, // Start at neutral
      reliability: 50,
      performance: 50,
      communication: 50,
      security: 50,
      uptime: 50,
      responseTime: 50,
      lastUpdated: new Date()
    };

    const defaultMetrics: ReputationMetrics = {
      totalJobs: 0,
      completedJobs: 0,
      failedJobs: 0,
      avgResponseTime: 0,
      uptimePercentage: 0,
      securityIncidents: 0,
      disputeResolutions: 0,
      totalEarnings: 0,
      clientSatisfaction: 0
    };

    const userProfile: UserProfile = {
      userId,
      username: profile.username || `user_${userId.slice(0, 8)}`,
      joinDate: new Date(),
      verificationLevel: 'unverified',
      specializations: profile.specializations || [],
      badges: [],
      tier: this.tiers[0], // Start at Bronze
      publicKey: profile.publicKey
    };

    this.scores.set(userId, defaultScore);
    this.metrics.set(userId, defaultMetrics);
    this.profiles.set(userId, userProfile);
    this.events.set(userId, []);
    this.badges.set(userId, []);

    this.emit('userInitialized', userId, userProfile);
  }

  public async recordEvent(event: Omit<ReputationEvent, 'id' | 'timestamp'>): Promise<void> {
    const fullEvent: ReputationEvent = {
      ...event,
      id: this.generateEventId(),
      timestamp: new Date()
    };

    const userEvents = this.events.get(event.userId) || [];
    userEvents.push(fullEvent);
    this.events.set(event.userId, userEvents);

    await this.updateReputationScore(event.userId, fullEvent);
    await this.updateMetrics(event.userId, fullEvent);
    await this.checkBadgeEligibility(event.userId);

    this.emit('reputationEvent', fullEvent);
  }

  private async updateReputationScore(userId: string, event: ReputationEvent): Promise<void> {
    const score = this.scores.get(userId);
    if (!score) return;

    const impact = event.impact * this.getEventWeight(event.type);
    const decayFactor = this.calculateDecayFactor(event.timestamp);

    switch (event.type) {
      case 'job_completion':
        score.reliability += impact * decayFactor;
        score.overall += impact * 0.3 * decayFactor;
        break;
      case 'performance':
        score.performance += impact * decayFactor;
        score.overall += impact * 0.25 * decayFactor;
        break;
      case 'uptime':
        score.uptime += impact * decayFactor;
        score.reliability += impact * 0.5 * decayFactor;
        score.overall += impact * 0.2 * decayFactor;
        break;
      case 'security_incident':
        score.security += impact * decayFactor;
        score.overall += impact * 0.4 * decayFactor; // Security heavily weighted
        break;
      case 'communication':
        score.communication += impact * decayFactor;
        score.overall += impact * 0.15 * decayFactor;
        break;
      case 'dispute':
        const disputeImpact = event.category === 'positive' ? 10 : -15;
        score.overall += disputeImpact * decayFactor;
        break;
    }

    // Clamp scores to 0-100 range
    Object.keys(score).forEach(key => {
      if (key !== 'userId' && key !== 'lastUpdated') {
        (score as any)[key] = Math.max(0, Math.min(100, (score as any)[key]));
      }
    });

    score.lastUpdated = new Date();
    this.scores.set(userId, score);

    await this.updateUserTier(userId);
    this.emit('scoreUpdated', userId, score);
  }

  private async updateMetrics(userId: string, event: ReputationEvent): Promise<void> {
    const metrics = this.metrics.get(userId);
    if (!metrics) return;

    switch (event.type) {
      case 'job_completion':
        metrics.totalJobs++;
        if (event.category === 'positive') {
          metrics.completedJobs++;
        } else {
          metrics.failedJobs++;
        }
        break;
      case 'security_incident':
        if (event.category === 'negative') {
          metrics.securityIncidents++;
        }
        break;
      case 'dispute':
        if (event.category === 'positive') {
          metrics.disputeResolutions++;
        }
        break;
    }

    this.metrics.set(userId, metrics);
  }

  private getEventWeight(eventType: string): number {
    const weights: Record<string, number> = {
      'job_completion': 1.0,
      'uptime': 0.8,
      'performance': 0.9,
      'security_incident': 1.5,
      'communication': 0.6,
      'dispute': 1.2
    };
    return weights[eventType] || 1.0;
  }

  private calculateDecayFactor(eventTime: Date): number {
    const ageInDays = (Date.now() - eventTime.getTime()) / (1000 * 60 * 60 * 24);
    return Math.max(0.1, Math.exp(-ageInDays / 180)); // Decay over 6 months
  }

  private async updateUserTier(userId: string): Promise<void> {
    const score = this.scores.get(userId);
    const profile = this.profiles.get(userId);
    
    if (!score || !profile) return;

    const newTier = this.tiers.find(tier => 
      score.overall >= tier.minScore && score.overall <= tier.maxScore
    );

    if (newTier && newTier !== profile.tier) {
      profile.tier = newTier;
      this.profiles.set(userId, profile);
      this.emit('tierUpdated', userId, newTier);

      // Award tier badge
      await this.awardBadge(userId, {
        id: `tier_${newTier.name.toLowerCase()}`,
        name: `${newTier.name} Tier`,
        description: `Achieved ${newTier.name} reputation tier`,
        icon: newTier.color,
        earnedDate: new Date(),
        criteria: `Reputation score: ${newTier.minScore}-${newTier.maxScore}`,
        rarity: this.getTierRarity(newTier.name)
      });
    }
  }

  private getTierRarity(tierName: string): 'common' | 'uncommon' | 'rare' | 'legendary' {
    switch (tierName) {
      case 'Bronze': return 'common';
      case 'Silver': return 'uncommon';
      case 'Gold': return 'rare';
      case 'Platinum': case 'Diamond': return 'legendary';
      default: return 'common';
    }
  }

  private async checkBadgeEligibility(userId: string): Promise<void> {
    const metrics = this.metrics.get(userId);
    const userBadges = this.badges.get(userId) || [];
    
    if (!metrics) return;

    const potentialBadges: ReputationBadge[] = [];

    // Job completion badges
    if (metrics.completedJobs >= 10 && !userBadges.find(b => b.id === 'first_10_jobs')) {
      potentialBadges.push({
        id: 'first_10_jobs',
        name: 'Getting Started',
        description: 'Completed your first 10 jobs',
        icon: '🎯',
        earnedDate: new Date(),
        criteria: 'Complete 10 jobs',
        rarity: 'common'
      });
    }

    if (metrics.completedJobs >= 100 && !userBadges.find(b => b.id === 'centurion')) {
      potentialBadges.push({
        id: 'centurion',
        name: 'Centurion',
        description: 'Completed 100 jobs',
        icon: '💯',
        earnedDate: new Date(),
        criteria: 'Complete 100 jobs',
        rarity: 'uncommon'
      });
    }

    // Reliability badges
    if (metrics.uptimePercentage >= 99.9 && !userBadges.find(b => b.id === 'rock_solid')) {
      potentialBadges.push({
        id: 'rock_solid',
        name: 'Rock Solid',
        description: 'Maintained 99.9% uptime',
        icon: '⛰️',
        earnedDate: new Date(),
        criteria: 'Maintain 99.9% uptime',
        rarity: 'rare'
      });
    }

    // Security badges
    if (metrics.securityIncidents === 0 && metrics.completedJobs >= 50 && !userBadges.find(b => b.id === 'security_champion')) {
      potentialBadges.push({
        id: 'security_champion',
        name: 'Security Champion',
        description: 'Zero security incidents with 50+ jobs',
        icon: '🛡️',
        earnedDate: new Date(),
        criteria: 'Zero security incidents, 50+ jobs completed',
        rarity: 'rare'
      });
    }

    for (const badge of potentialBadges) {
      await this.awardBadge(userId, badge);
    }
  }

  private async awardBadge(userId: string, badge: ReputationBadge): Promise<void> {
    const userBadges = this.badges.get(userId) || [];
    userBadges.push(badge);
    this.badges.set(userId, userBadges);

    const profile = this.profiles.get(userId);
    if (profile) {
      profile.badges = userBadges;
      this.profiles.set(userId, profile);
    }

    this.emit('badgeAwarded', userId, badge);
  }

  public async createDispute(dispute: Omit<DisputeCase, 'id' | 'createdAt' | 'status'>): Promise<string> {
    const disputeId = this.generateDisputeId();
    const fullDispute: DisputeCase = {
      ...dispute,
      id: disputeId,
      status: 'open',
      createdAt: new Date()
    };

    this.disputes.set(disputeId, fullDispute);
    this.emit('disputeCreated', fullDispute);

    return disputeId;
  }

  public async resolveDispute(disputeId: string, resolution: string, moderatorId: string): Promise<void> {
    const dispute = this.disputes.get(disputeId);
    if (!dispute) throw new Error('Dispute not found');

    dispute.status = 'resolved';
    dispute.resolution = resolution;
    dispute.moderatorId = moderatorId;
    dispute.resolvedAt = new Date();

    // Record reputation events based on resolution
    const isComplainantFavored = resolution.toLowerCase().includes('favor') && 
                                resolution.toLowerCase().includes('complainant');

    await this.recordEvent({
      userId: dispute.respondentId,
      type: 'dispute',
      category: isComplainantFavored ? 'negative' : 'positive',
      impact: isComplainantFavored ? -20 : 10,
      description: `Dispute resolved: ${resolution}`,
      jobId: dispute.jobId,
      reporterId: moderatorId
    });

    this.disputes.set(disputeId, dispute);
    this.emit('disputeResolved', dispute);
  }

  public getUserScore(userId: string): ReputationScore | undefined {
    return this.scores.get(userId);
  }

  public getUserProfile(userId: string): UserProfile | undefined {
    return this.profiles.get(userId);
  }

  public getUserMetrics(userId: string): ReputationMetrics | undefined {
    return this.metrics.get(userId);
  }

  public getUserEvents(userId: string, limit: number = 50): ReputationEvent[] {
    const events = this.events.get(userId) || [];
    return events.slice(-limit).reverse();
  }

  public getLeaderboard(metric: keyof ReputationScore = 'overall', limit: number = 100): Array<{userId: string, score: number, profile: UserProfile}> {
    const scores = Array.from(this.scores.entries());
    return scores
      .map(([userId, score]) => ({
        userId,
        score: score[metric] as number,
        profile: this.profiles.get(userId)!
      }))
      .filter(entry => entry.profile)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
  }

  public async verifyUser(userId: string, level: UserProfile['verificationLevel']): Promise<void> {
    const profile = this.profiles.get(userId);
    if (!profile) throw new Error('User profile not found');

    profile.verificationLevel = level;
    this.profiles.set(userId, profile);

    // Award verification bonus
    const bonusPoints = {
      'email': 5,
      'phone': 10,
      'id': 20,
      'full': 30
    }[level] || 0;

    if (bonusPoints > 0) {
      await this.recordEvent({
        userId,
        type: 'communication',
        category: 'positive',
        impact: bonusPoints,
        description: `Identity verification completed: ${level}`
      });
    }

    this.emit('userVerified', userId, level);
  }

  private startReputationDecay(): void {
    this.decayInterval = setInterval(async () => {
      await this.applyReputationDecay();
    }, 24 * 60 * 60 * 1000); // Daily decay
  }

  private async applyReputationDecay(): Promise<void> {
    const now = new Date();
    const decayRate = 0.001; // 0.1% per day for inactive users

    for (const [userId, score] of this.scores) {
      const daysSinceUpdate = (now.getTime() - score.lastUpdated.getTime()) / (1000 * 60 * 60 * 24);
      
      if (daysSinceUpdate > 7) { // Apply decay after 7 days of inactivity
        const decay = decayRate * daysSinceUpdate;
        
        Object.keys(score).forEach(key => {
          if (key !== 'userId' && key !== 'lastUpdated') {
            (score as any)[key] = Math.max(0, (score as any)[key] * (1 - decay));
          }
        });

        this.scores.set(userId, score);
        await this.updateUserTier(userId);
      }
    }
  }

  private generateEventId(): string {
    return `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateDisputeId(): string {
    return `dispute_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  public stop(): void {
    if (this.decayInterval) {
      clearInterval(this.decayInterval);
      this.decayInterval = null;
    }
  }
}

export default ReputationSystem;