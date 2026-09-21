import { v4 as uuidv4 } from 'uuid';
import crypto from 'crypto';

export interface ReferralProgram {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'paused' | 'ended';
  startDate: Date;
  endDate?: Date;
  
  // Referral structure
  referrerReward: ReferralReward;
  refereeReward: ReferralReward;
  
  // Qualification rules
  qualificationRules: {
    minSignupTime?: number; // days user must remain active
    requiredActions?: string[]; // actions referee must complete
    minSpending?: number; // minimum spending by referee
    excludeExistingUsers?: boolean;
    maxReferralsPerUser?: number;
    geographicRestrictions?: string[]; // country codes
  };
  
  // Campaign settings
  campaignSettings: {
    autoApprove: boolean;
    trackingCookieDuration: number; // days
    allowSelfReferral: boolean;
    requireEmailVerification: boolean;
    customLandingPage?: string;
    socialSharingEnabled: boolean;
  };
}

export interface ReferralReward {
  type: 'percentage' | 'fixed' | 'credits' | 'subscription_months' | 'feature_unlock';
  value: number;
  currency?: string;
  maxValue?: number;
  description: string;
  restrictions?: {
    oneTimeOnly?: boolean;
    expirationDays?: number;
    minimumPurchase?: number;
    applicableProducts?: string[];
  };
}

export interface ReferralCode {
  id: string;
  code: string;
  userId: string;
  programId: string;
  createdAt: Date;
  expiresAt?: Date;
  isActive: boolean;
  
  // Usage tracking
  totalClicks: number;
  totalSignups: number;
  totalConversions: number;
  totalRevenueGenerated: number;
  
  // Custom settings
  customReward?: ReferralReward;
  customLandingPage?: string;
  notes?: string;
}

export interface ReferralTracking {
  id: string;
  referralCodeId: string;
  referrerId: string;
  refereeId?: string;
  sessionId: string;
  
  // Journey tracking
  clickedAt: Date;
  signedUpAt?: Date;
  convertedAt?: Date;
  firstPurchaseAt?: Date;
  
  // Attribution
  source: string; // email, social, direct, etc.
  medium: string; // organic, paid, etc.
  campaign?: string;
  userAgent: string;
  ipAddress: string;
  referrerUrl?: string;
  landingPageUrl: string;
  
  // Status
  status: 'clicked' | 'signed_up' | 'converted' | 'qualified' | 'rewarded' | 'rejected';
  qualificationDate?: Date;
  rewardDate?: Date;
  rejectionReason?: string;
  
  // Revenue tracking
  revenueGenerated: number;
  currency: string;
  
  // Metadata
  metadata?: Record<string, any>;
}

export interface ReferralRewardTransaction {
  id: string;
  trackingId: string;
  userId: string;
  userType: 'referrer' | 'referee';
  
  // Reward details
  rewardType: ReferralReward['type'];
  rewardValue: number;
  currency?: string;
  description: string;
  
  // Transaction info
  transactionDate: Date;
  status: 'pending' | 'approved' | 'paid' | 'rejected' | 'expired';
  approvedBy?: string;
  approvedAt?: Date;
  paidAt?: Date;
  rejectionReason?: string;
  
  // Payment details
  paymentMethod?: 'account_credit' | 'paypal' | 'bank_transfer' | 'gift_card' | 'subscription_credit';
  paymentReference?: string;
  
  // Expiration
  expiresAt?: Date;
}

export interface ReferralAnalytics {
  programId: string;
  period: {
    start: Date;
    end: Date;
  };
  
  // Overview metrics
  totalReferralCodes: number;
  activeReferralCodes: number;
  totalClicks: number;
  totalSignups: number;
  totalConversions: number;
  totalRevenueGenerated: number;
  totalRewardsPaid: number;
  
  // Conversion rates
  clickToSignupRate: number;
  signupToConversionRate: number;
  overallConversionRate: number;
  
  // Financial metrics
  costPerAcquisition: number;
  averageRevenuePerReferral: number;
  returnOnInvestment: number;
  
  // Top performers
  topReferrers: Array<{
    userId: string;
    referrals: number;
    revenue: number;
    rewards: number;
  }>;
  
  // Channel performance
  channelPerformance: Record<string, {
    clicks: number;
    conversions: number;
    revenue: number;
  }>;
  
  // Geographic data
  geographicData: Record<string, {
    referrals: number;
    revenue: number;
  }>;
}

class ReferralSystem {
  private programs: Map<string, ReferralProgram> = new Map();
  private referralCodes: Map<string, ReferralCode> = new Map();
  private trackingData: Map<string, ReferralTracking> = new Map();
  private rewardTransactions: Map<string, ReferralRewardTransaction> = new Map();

  constructor() {
    this.initializeDefaultPrograms();
  }

  public createProgram(program: Omit<ReferralProgram, 'id'>): ReferralProgram {
    const newProgram: ReferralProgram = {
      ...program,
      id: uuidv4(),
    };
    
    this.programs.set(newProgram.id, newProgram);
    return newProgram;
  }

  public createReferralCode(
    userId: string,
    programId: string,
    customCode?: string,
    customSettings?: {
      customReward?: ReferralReward;
      customLandingPage?: string;
      expirationDays?: number;
      notes?: string;
    }
  ): ReferralCode {
    const program = this.programs.get(programId);
    if (!program) {
      throw new Error(`Program ${programId} not found`);
    }

    // Check if user already has a code for this program
    const existingCode = Array.from(this.referralCodes.values())
      .find(code => code.userId === userId && code.programId === programId && code.isActive);
    
    if (existingCode) {
      return existingCode;
    }

    const code = customCode || this.generateReferralCode(userId);
    
    const referralCode: ReferralCode = {
      id: uuidv4(),
      code,
      userId,
      programId,
      createdAt: new Date(),
      expiresAt: customSettings?.expirationDays 
        ? new Date(Date.now() + customSettings.expirationDays * 24 * 60 * 60 * 1000)
        : undefined,
      isActive: true,
      totalClicks: 0,
      totalSignups: 0,
      totalConversions: 0,
      totalRevenueGenerated: 0,
      customReward: customSettings?.customReward,
      customLandingPage: customSettings?.customLandingPage,
      notes: customSettings?.notes,
    };

    this.referralCodes.set(referralCode.id, referralCode);
    return referralCode;
  }

  public generateReferralLink(
    referralCodeId: string,
    appVariant?: string,
    customParams?: Record<string, string>
  ): string {
    const referralCode = this.referralCodes.get(referralCodeId);
    if (!referralCode) {
      throw new Error(`Referral code ${referralCodeId} not found`);
    }

    const baseUrl = this.getBaseUrlForVariant(appVariant);
    const params = new URLSearchParams({
      ref: referralCode.code,
      ...customParams,
    });

    if (referralCode.customLandingPage) {
      return `${baseUrl}${referralCode.customLandingPage}?${params.toString()}`;
    }

    return `${baseUrl}/signup?${params.toString()}`;
  }

  public trackClick(
    referralCode: string,
    request: {
      userAgent: string;
      ipAddress: string;
      referrerUrl?: string;
      landingPageUrl: string;
      source?: string;
      medium?: string;
      campaign?: string;
    }
  ): ReferralTracking {
    const code = Array.from(this.referralCodes.values())
      .find(c => c.code === referralCode && c.isActive);
    
    if (!code) {
      throw new Error(`Invalid or inactive referral code: ${referralCode}`);
    }

    // Check if code is expired
    if (code.expiresAt && code.expiresAt < new Date()) {
      throw new Error(`Referral code expired: ${referralCode}`);
    }

    const tracking: ReferralTracking = {
      id: uuidv4(),
      referralCodeId: code.id,
      referrerId: code.userId,
      sessionId: this.generateSessionId(),
      clickedAt: new Date(),
      source: request.source || 'direct',
      medium: request.medium || 'referral',
      campaign: request.campaign,
      userAgent: request.userAgent,
      ipAddress: this.hashIPAddress(request.ipAddress),
      referrerUrl: request.referrerUrl,
      landingPageUrl: request.landingPageUrl,
      status: 'clicked',
      revenueGenerated: 0,
      currency: 'USD',
    };

    this.trackingData.set(tracking.id, tracking);
    
    // Update referral code stats
    code.totalClicks++;
    this.referralCodes.set(code.id, code);

    return tracking;
  }

  public trackSignup(
    referralCode: string,
    newUserId: string,
    signupData?: {
      email: string;
      source?: string;
      metadata?: Record<string, any>;
    }
  ): void {
    const code = Array.from(this.referralCodes.values())
      .find(c => c.code === referralCode && c.isActive);
    
    if (!code) {
      console.warn(`Referral code not found for signup: ${referralCode}`);
      return;
    }

    // Find recent tracking record for this code
    const recentTracking = Array.from(this.trackingData.values())
      .filter(t => t.referralCodeId === code.id && t.status === 'clicked')
      .sort((a, b) => b.clickedAt.getTime() - a.clickedAt.getTime())[0];

    if (recentTracking) {
      recentTracking.refereeId = newUserId;
      recentTracking.signedUpAt = new Date();
      recentTracking.status = 'signed_up';
      if (signupData?.metadata) {
        recentTracking.metadata = signupData.metadata;
      }
      this.trackingData.set(recentTracking.id, recentTracking);
    } else {
      // Create new tracking record for direct signups
      const tracking: ReferralTracking = {
        id: uuidv4(),
        referralCodeId: code.id,
        referrerId: code.userId,
        refereeId: newUserId,
        sessionId: this.generateSessionId(),
        clickedAt: new Date(),
        signedUpAt: new Date(),
        source: signupData?.source || 'direct',
        medium: 'referral',
        userAgent: '',
        ipAddress: '',
        landingPageUrl: '',
        status: 'signed_up',
        revenueGenerated: 0,
        currency: 'USD',
        metadata: signupData?.metadata,
      };
      this.trackingData.set(tracking.id, tracking);
    }

    // Update referral code stats
    code.totalSignups++;
    this.referralCodes.set(code.id, code);
  }

  public trackConversion(
    userId: string,
    conversionData: {
      revenue: number;
      currency?: string;
      transactionId?: string;
      productId?: string;
      metadata?: Record<string, any>;
    }
  ): void {
    // Find tracking record for this user
    const tracking = Array.from(this.trackingData.values())
      .find(t => t.refereeId === userId && ['signed_up', 'converted'].includes(t.status));

    if (!tracking) {
      console.warn(`No referral tracking found for user: ${userId}`);
      return;
    }

    tracking.convertedAt = new Date();
    tracking.status = 'converted';
    tracking.revenueGenerated += conversionData.revenue;
    tracking.currency = conversionData.currency || tracking.currency;
    
    if (conversionData.metadata) {
      tracking.metadata = { ...tracking.metadata, ...conversionData.metadata };
    }

    if (!tracking.firstPurchaseAt) {
      tracking.firstPurchaseAt = new Date();
    }

    this.trackingData.set(tracking.id, tracking);

    // Update referral code stats
    const code = this.referralCodes.get(tracking.referralCodeId);
    if (code) {
      code.totalConversions++;
      code.totalRevenueGenerated += conversionData.revenue;
      this.referralCodes.set(code.id, code);
    }

    // Check if this qualifies for rewards
    this.processQualification(tracking.id);
  }

  public processQualification(trackingId: string): void {
    const tracking = this.trackingData.get(trackingId);
    if (!tracking || tracking.status !== 'converted') return;

    const code = this.referralCodes.get(tracking.referralCodeId);
    if (!code) return;

    const program = this.programs.get(code.programId);
    if (!program) return;

    // Check qualification rules
    const isQualified = this.checkQualificationRules(tracking, program);
    
    if (isQualified) {
      tracking.status = 'qualified';
      tracking.qualificationDate = new Date();
      this.trackingData.set(trackingId, tracking);

      // Create reward transactions
      this.createRewardTransactions(tracking, program, code);
    } else {
      tracking.status = 'rejected';
      tracking.rejectionReason = 'Failed qualification rules';
      this.trackingData.set(trackingId, tracking);
    }
  }

  public processRewardPayment(transactionId: string, approvedBy: string): void {
    const transaction = this.rewardTransactions.get(transactionId);
    if (!transaction || transaction.status !== 'pending') return;

    transaction.status = 'approved';
    transaction.approvedBy = approvedBy;
    transaction.approvedAt = new Date();

    // Simulate payment processing
    setTimeout(() => {
      transaction.status = 'paid';
      transaction.paidAt = new Date();
      transaction.paymentReference = `PAY_${Date.now()}`;
      this.rewardTransactions.set(transactionId, transaction);

      // Update tracking status
      const tracking = Array.from(this.trackingData.values())
        .find(t => t.id === transaction.trackingId);
      if (tracking) {
        tracking.status = 'rewarded';
        tracking.rewardDate = new Date();
        this.trackingData.set(tracking.id, tracking);
      }
    }, 1000);

    this.rewardTransactions.set(transactionId, transaction);
  }

  public generateAnalytics(
    programId: string,
    startDate: Date,
    endDate: Date
  ): ReferralAnalytics {
    const program = this.programs.get(programId);
    if (!program) {
      throw new Error(`Program ${programId} not found`);
    }

    const relevantCodes = Array.from(this.referralCodes.values())
      .filter(code => code.programId === programId);

    const relevantTracking = Array.from(this.trackingData.values())
      .filter(tracking => {
        const code = this.referralCodes.get(tracking.referralCodeId);
        return code?.programId === programId && 
               tracking.clickedAt >= startDate && 
               tracking.clickedAt <= endDate;
      });

    const totalClicks = relevantTracking.length;
    const totalSignups = relevantTracking.filter(t => t.signedUpAt).length;
    const totalConversions = relevantTracking.filter(t => t.convertedAt).length;
    const totalRevenue = relevantTracking.reduce((sum, t) => sum + t.revenueGenerated, 0);

    const rewardTransactions = Array.from(this.rewardTransactions.values())
      .filter(rt => {
        const tracking = this.trackingData.get(rt.trackingId);
        return tracking && relevantTracking.includes(tracking) && rt.status === 'paid';
      });

    const totalRewardsPaid = rewardTransactions.reduce((sum, rt) => sum + rt.rewardValue, 0);

    return {
      programId,
      period: { start: startDate, end: endDate },
      totalReferralCodes: relevantCodes.length,
      activeReferralCodes: relevantCodes.filter(c => c.isActive).length,
      totalClicks,
      totalSignups,
      totalConversions,
      totalRevenueGenerated: totalRevenue,
      totalRewardsPaid,
      clickToSignupRate: totalClicks > 0 ? (totalSignups / totalClicks) * 100 : 0,
      signupToConversionRate: totalSignups > 0 ? (totalConversions / totalSignups) * 100 : 0,
      overallConversionRate: totalClicks > 0 ? (totalConversions / totalClicks) * 100 : 0,
      costPerAcquisition: totalConversions > 0 ? totalRewardsPaid / totalConversions : 0,
      averageRevenuePerReferral: totalConversions > 0 ? totalRevenue / totalConversions : 0,
      returnOnInvestment: totalRewardsPaid > 0 ? ((totalRevenue - totalRewardsPaid) / totalRewardsPaid) * 100 : 0,
      topReferrers: this.getTopReferrers(relevantTracking, 10),
      channelPerformance: this.getChannelPerformance(relevantTracking),
      geographicData: {}, // Would need IP geolocation service
    };
  }

  private checkQualificationRules(tracking: ReferralTracking, program: ReferralProgram): boolean {
    const rules = program.qualificationRules;

    // Check minimum signup time
    if (rules.minSignupTime && tracking.signedUpAt) {
      const daysSinceSignup = Math.floor(
        (new Date().getTime() - tracking.signedUpAt.getTime()) / (1000 * 60 * 60 * 24)
      );
      if (daysSinceSignup < rules.minSignupTime) return false;
    }

    // Check minimum spending
    if (rules.minSpending && tracking.revenueGenerated < rules.minSpending) {
      return false;
    }

    // Additional rule checks would go here...

    return true;
  }

  private createRewardTransactions(
    tracking: ReferralTracking,
    program: ReferralProgram,
    code: ReferralCode
  ): void {
    // Create referrer reward
    const referrerReward = code.customReward || program.referrerReward;
    const referrerTransaction: ReferralRewardTransaction = {
      id: uuidv4(),
      trackingId: tracking.id,
      userId: tracking.referrerId,
      userType: 'referrer',
      rewardType: referrerReward.type,
      rewardValue: this.calculateRewardValue(referrerReward, tracking.revenueGenerated),
      currency: referrerReward.currency || 'USD',
      description: `Referrer reward for ${tracking.refereeId}`,
      transactionDate: new Date(),
      status: program.campaignSettings.autoApprove ? 'approved' : 'pending',
      paymentMethod: 'account_credit',
    };

    if (referrerReward.restrictions?.expirationDays) {
      referrerTransaction.expiresAt = new Date(
        Date.now() + referrerReward.restrictions.expirationDays * 24 * 60 * 60 * 1000
      );
    }

    this.rewardTransactions.set(referrerTransaction.id, referrerTransaction);

    // Create referee reward if applicable
    if (program.refereeReward) {
      const refereeTransaction: ReferralRewardTransaction = {
        id: uuidv4(),
        trackingId: tracking.id,
        userId: tracking.refereeId!,
        userType: 'referee',
        rewardType: program.refereeReward.type,
        rewardValue: this.calculateRewardValue(program.refereeReward, tracking.revenueGenerated),
        currency: program.refereeReward.currency || 'USD',
        description: `Referee welcome reward`,
        transactionDate: new Date(),
        status: program.campaignSettings.autoApprove ? 'approved' : 'pending',
        paymentMethod: 'account_credit',
      };

      if (program.refereeReward.restrictions?.expirationDays) {
        refereeTransaction.expiresAt = new Date(
          Date.now() + program.refereeReward.restrictions.expirationDays * 24 * 60 * 60 * 1000
        );
      }

      this.rewardTransactions.set(refereeTransaction.id, refereeTransaction);
    }
  }

  private calculateRewardValue(reward: ReferralReward, revenue: number): number {
    let value = reward.value;

    if (reward.type === 'percentage') {
      value = (revenue * reward.value) / 100;
    }

    if (reward.maxValue && value > reward.maxValue) {
      value = reward.maxValue;
    }

    return Math.round(value * 100) / 100; // Round to 2 decimal places
  }

  private getTopReferrers(trackingData: ReferralTracking[], limit: number) {
    const referrerStats = new Map<string, { referrals: number; revenue: number; rewards: number }>();

    trackingData.forEach(tracking => {
      if (tracking.status === 'qualified' || tracking.status === 'rewarded') {
        const current = referrerStats.get(tracking.referrerId) || { referrals: 0, revenue: 0, rewards: 0 };
        current.referrals++;
        current.revenue += tracking.revenueGenerated;
        referrerStats.set(tracking.referrerId, current);
      }
    });

    // Calculate rewards
    Array.from(this.rewardTransactions.values())
      .filter(rt => rt.userType === 'referrer' && rt.status === 'paid')
      .forEach(rt => {
        const tracking = this.trackingData.get(rt.trackingId);
        if (tracking) {
          const current = referrerStats.get(tracking.referrerId);
          if (current) {
            current.rewards += rt.rewardValue;
          }
        }
      });

    return Array.from(referrerStats.entries())
      .map(([userId, stats]) => ({ userId, ...stats }))
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, limit);
  }

  private getChannelPerformance(trackingData: ReferralTracking[]) {
    const channelStats: Record<string, { clicks: number; conversions: number; revenue: number }> = {};

    trackingData.forEach(tracking => {
      const channel = `${tracking.source}/${tracking.medium}`;
      if (!channelStats[channel]) {
        channelStats[channel] = { clicks: 0, conversions: 0, revenue: 0 };
      }

      channelStats[channel].clicks++;
      if (tracking.convertedAt) {
        channelStats[channel].conversions++;
        channelStats[channel].revenue += tracking.revenueGenerated;
      }
    });

    return channelStats;
  }

  private generateReferralCode(userId: string): string {
    // Generate a unique, user-friendly referral code
    const hash = crypto.createHash('md5').update(userId + Date.now()).digest('hex');
    return hash.substring(0, 8).toUpperCase();
  }

  private generateSessionId(): string {
    return crypto.randomBytes(16).toString('hex');
  }

  private hashIPAddress(ipAddress: string): string {
    // Hash IP address for privacy
    return crypto.createHash('sha256').update(ipAddress).digest('hex');
  }

  private getBaseUrlForVariant(appVariant?: string): string {
    const baseUrls = {
      'personal-log': 'https://personallog.com',
      'business-log': 'https://businesslog.com',
      'fitness-log': 'https://fitnesslog.com',
      'family-log': 'https://familylog.com',
      'travel-log': 'https://travellog.com',
      'education-log': 'https://educationlog.com',
    };

    return baseUrls[appVariant as keyof typeof baseUrls] || 'https://activelog.com';
  }

  private initializeDefaultPrograms(): void {
    const defaultProgram: ReferralProgram = {
      id: uuidv4(),
      name: 'Standard Referral Program',
      description: 'Refer friends and get rewarded',
      status: 'active',
      startDate: new Date(),
      referrerReward: {
        type: 'credits',
        value: 10,
        description: '$10 account credit for each successful referral',
        restrictions: {
          oneTimeOnly: false,
          expirationDays: 365,
        },
      },
      refereeReward: {
        type: 'percentage',
        value: 20,
        maxValue: 50,
        description: '20% off first purchase (up to $50)',
        restrictions: {
          oneTimeOnly: true,
          expirationDays: 30,
          minimumPurchase: 10,
        },
      },
      qualificationRules: {
        minSignupTime: 1,
        minSpending: 5,
        excludeExistingUsers: true,
        maxReferralsPerUser: 100,
      },
      campaignSettings: {
        autoApprove: false,
        trackingCookieDuration: 30,
        allowSelfReferral: false,
        requireEmailVerification: true,
        socialSharingEnabled: true,
      },
    };

    this.programs.set(defaultProgram.id, defaultProgram);
  }

  // Public getters for testing and debugging
  public getPrograms(): ReferralProgram[] {
    return Array.from(this.programs.values());
  }

  public getReferralCodes(userId?: string): ReferralCode[] {
    const codes = Array.from(this.referralCodes.values());
    return userId ? codes.filter(code => code.userId === userId) : codes;
  }

  public getTrackingData(referralCodeId?: string): ReferralTracking[] {
    const data = Array.from(this.trackingData.values());
    return referralCodeId ? data.filter(t => t.referralCodeId === referralCodeId) : data;
  }

  public getRewardTransactions(userId?: string): ReferralRewardTransaction[] {
    const transactions = Array.from(this.rewardTransactions.values());
    return userId ? transactions.filter(t => t.userId === userId) : transactions;
  }
}

export default ReferralSystem;