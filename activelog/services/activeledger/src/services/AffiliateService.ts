import { Decimal } from 'decimal.js';
import { v4 as uuidv4 } from 'uuid';
import { EventEmitter } from 'events';
import { 
  AffiliateProgram, 
  AffiliateReferral, 
  AffiliateTier, 
  AffiliateStatus,
  PaymentProvider,
  CurrencyCode,
  ComputeCredit 
} from '../types';
import { CCreditSystem } from '../core/CCreditSystem';

export class AffiliateService extends EventEmitter {
  private ccreditSystem: CCreditSystem;
  
  // Affiliate tier configuration
  private readonly TIER_CONFIG = {
    bronze: { minReferrals: 0, commissionRate: 0.10, bonusMultiplier: 1.0 },
    silver: { minReferrals: 10, commissionRate: 0.15, bonusMultiplier: 1.2 },
    gold: { minReferrals: 50, commissionRate: 0.20, bonusMultiplier: 1.5 },
    platinum: { minReferrals: 200, commissionRate: 0.25, bonusMultiplier: 2.0 }
  };

  constructor(ccreditSystem: CCreditSystem) {
    super();
    this.ccreditSystem = ccreditSystem;
  }

  /**
   * Create an affiliate program for a user
   */
  async createAffiliateProgram(
    userId: string,
    customAffiliateCode?: string
  ): Promise<AffiliateProgram> {
    // Generate unique affiliate code
    const affiliateCode = customAffiliateCode || this.generateAffiliateCode(userId);
    
    // Check if code already exists
    const existingProgram = await this.getAffiliateByCode(affiliateCode);
    if (existingProgram) {
      throw new Error('Affiliate code already exists');
    }

    const affiliateProgram: AffiliateProgram = {
      id: uuidv4(),
      userId,
      affiliateCode,
      tier: 'bronze',
      totalReferrals: 0,
      totalEarnings: new Decimal(0),
      currentMonthEarnings: new Decimal(0),
      commissionRate: new Decimal(this.TIER_CONFIG.bronze.commissionRate),
      status: 'active',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.emit('affiliateProgramCreated', { affiliateProgram });
    return affiliateProgram;
  }

  /**
   * Track a referral conversion
   */
  async trackReferral(
    affiliateCode: string,
    referredUserId: string,
    conversionType: 'signup' | 'subscription' | 'purchase',
    conversionValue: Decimal,
    currency: CurrencyCode = 'USD'
  ): Promise<AffiliateReferral> {
    const affiliateProgram = await this.getAffiliateByCode(affiliateCode);
    if (!affiliateProgram) {
      throw new Error('Invalid affiliate code');
    }

    if (affiliateProgram.status !== 'active') {
      throw new Error('Affiliate program is not active');
    }

    // Calculate commission amount
    const commissionAmount = conversionValue.mul(affiliateProgram.commissionRate);
    const tierConfig = this.TIER_CONFIG[affiliateProgram.tier];
    const bonusMultiplier = new Decimal(tierConfig.bonusMultiplier);
    const finalCommission = commissionAmount.mul(bonusMultiplier);

    // Convert commission to CC credits
    const ccCreditsAwarded = this.ccreditSystem.getUSDValueInCC(
      currency === 'USD' ? finalCommission : await this.convertToUSD(finalCommission, currency)
    );

    const referral: AffiliateReferral = {
      id: uuidv4(),
      affiliateUserId: affiliateProgram.userId,
      referredUserId,
      affiliateCode,
      conversionType,
      conversionValue,
      commissionAmount: finalCommission,
      ccCreditsAwarded,
      status: 'pending',
      createdAt: new Date()
    };

    this.emit('referralTracked', { referral, affiliateProgram });
    return referral;
  }

  /**
   * Confirm a referral and award CC credits
   */
  async confirmReferral(referralId: string): Promise<{
    referral: AffiliateReferral;
    creditAwarded: ComputeCredit;
    updatedProgram: AffiliateProgram;
  }> {
    const referral = await this.getReferral(referralId);
    if (!referral) {
      throw new Error('Referral not found');
    }

    if (referral.status !== 'pending') {
      throw new Error('Referral has already been processed');
    }

    // Award CC credits to affiliate
    const creditAwarded = await this.ccreditSystem.awardCredits(
      referral.affiliateUserId,
      referral.ccCreditsAwarded,
      'USD',
      'affiliate',
      referralId,
      undefined,
      {
        referralId,
        referredUserId: referral.referredUserId,
        conversionType: referral.conversionType,
        conversionValue: referral.conversionValue.toString(),
        commissionAmount: referral.commissionAmount.toString()
      }
    );

    // Update referral status
    referral.status = 'confirmed';
    referral.paidAt = new Date();

    // Update affiliate program stats
    const updatedProgram = await this.updateAffiliateStats(
      referral.affiliateUserId,
      referral.commissionAmount
    );

    this.emit('referralConfirmed', { referral, creditAwarded, updatedProgram });
    
    return { referral, creditAwarded, updatedProgram };
  }

  /**
   * Get affiliate program for user
   */
  async getAffiliateProgram(userId: string): Promise<AffiliateProgram | null> {
    // Mock implementation - would fetch from database
    const mockProgram: AffiliateProgram = {
      id: uuidv4(),
      userId,
      affiliateCode: `AL${userId.slice(-6).toUpperCase()}`,
      tier: 'bronze',
      totalReferrals: 5,
      totalEarnings: new Decimal('150.00'),
      currentMonthEarnings: new Decimal('25.00'),
      commissionRate: new Decimal('0.15'),
      status: 'active',
      payoutMethod: 'stripe',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    return mockProgram;
  }

  /**
   * Get referrals for an affiliate
   */
  async getAffiliateReferrals(
    userId: string,
    status?: 'pending' | 'confirmed' | 'paid',
    limit: number = 50,
    offset: number = 0
  ): Promise<{
    referrals: AffiliateReferral[];
    totalCount: number;
    totalEarnings: Decimal;
    pendingEarnings: Decimal;
  }> {
    // Mock referrals data
    const mockReferrals: AffiliateReferral[] = [
      {
        id: uuidv4(),
        affiliateUserId: userId,
        referredUserId: 'user-456',
        affiliateCode: 'AL123456',
        conversionType: 'subscription',
        conversionValue: new Decimal('29.99'),
        commissionAmount: new Decimal('4.50'),
        ccCreditsAwarded: new Decimal('450'),
        status: 'confirmed',
        createdAt: new Date(),
        paidAt: new Date()
      }
    ];

    const filteredReferrals = status 
      ? mockReferrals.filter(r => r.status === status)
      : mockReferrals;

    const totalEarnings = mockReferrals.reduce(
      (sum, r) => sum.add(r.commissionAmount), 
      new Decimal(0)
    );

    const pendingEarnings = mockReferrals
      .filter(r => r.status === 'pending')
      .reduce((sum, r) => sum.add(r.commissionAmount), new Decimal(0));

    return {
      referrals: filteredReferrals.slice(offset, offset + limit),
      totalCount: filteredReferrals.length,
      totalEarnings,
      pendingEarnings
    };
  }

  /**
   * Get affiliate performance analytics
   */
  async getAffiliateAnalytics(
    userId: string,
    period: 'daily' | 'weekly' | 'monthly' = 'monthly',
    timeRange?: { start: Date; end: Date }
  ): Promise<{
    performanceData: Array<{
      period: string;
      referrals: number;
      conversions: number;
      earnings: Decimal;
      conversionRate: number;
    }>;
    topConversionSources: Array<{
      type: string;
      count: number;
      earnings: Decimal;
    }>;
    tierProgress: {
      currentTier: AffiliateTier;
      nextTier: AffiliateTier | null;
      progressToNext: number; // percentage
      referralsToNext: number;
    };
  }> {
    const affiliateProgram = await this.getAffiliateProgram(userId);
    if (!affiliateProgram) {
      throw new Error('Affiliate program not found');
    }

    // Mock analytics data
    const performanceData = [
      {
        period: '2024-01',
        referrals: 8,
        conversions: 5,
        earnings: new Decimal('75.00'),
        conversionRate: 62.5
      },
      {
        period: '2024-02',
        referrals: 12,
        conversions: 8,
        earnings: new Decimal('120.00'),
        conversionRate: 66.7
      }
    ];

    const topConversionSources = [
      { type: 'subscription', count: 8, earnings: new Decimal('120.00') },
      { type: 'purchase', count: 3, earnings: new Decimal('45.00') },
      { type: 'signup', count: 2, earnings: new Decimal('30.00') }
    ];

    const tierProgress = this.calculateTierProgress(affiliateProgram);

    return {
      performanceData,
      topConversionSources,
      tierProgress
    };
  }

  /**
   * Generate affiliate marketing materials
   */
  async generateMarketingMaterials(userId: string): Promise<{
    referralLinks: Array<{
      type: 'signup' | 'landing' | 'specific_plan';
      url: string;
      description: string;
    }>;
    banners: Array<{
      size: string;
      url: string;
      htmlCode: string;
    }>;
    emailTemplates: Array<{
      subject: string;
      content: string;
      type: 'introduction' | 'follow_up' | 'promotion';
    }>;
    socialMediaPosts: Array<{
      platform: 'twitter' | 'facebook' | 'linkedin';
      content: string;
    }>;
  }> {
    const affiliateProgram = await this.getAffiliateProgram(userId);
    if (!affiliateProgram) {
      throw new Error('Affiliate program not found');
    }

    const baseUrl = 'https://activelog.com';
    const affiliateCode = affiliateProgram.affiliateCode;

    return {
      referralLinks: [
        {
          type: 'signup',
          url: `${baseUrl}/signup?ref=${affiliateCode}`,
          description: 'General signup link with your affiliate code'
        },
        {
          type: 'landing',
          url: `${baseUrl}/features?ref=${affiliateCode}`,
          description: 'Features page with your affiliate code'
        },
        {
          type: 'specific_plan',
          url: `${baseUrl}/pricing?ref=${affiliateCode}&plan=pro`,
          description: 'Direct link to Pro plan pricing'
        }
      ],
      banners: [
        {
          size: '728x90',
          url: `${baseUrl}/assets/banners/728x90.png`,
          htmlCode: `<a href="${baseUrl}/signup?ref=${affiliateCode}"><img src="${baseUrl}/assets/banners/728x90.png" alt="ActiveLog - Your Digital Life, Organized" /></a>`
        },
        {
          size: '300x250',
          url: `${baseUrl}/assets/banners/300x250.png`,
          htmlCode: `<a href="${baseUrl}/signup?ref=${affiliateCode}"><img src="${baseUrl}/assets/banners/300x250.png" alt="ActiveLog - Your Digital Life, Organized" /></a>`
        }
      ],
      emailTemplates: [
        {
          subject: 'Discover ActiveLog - The Ultimate Digital Organization Tool',
          content: `Hi there!\n\nI've been using ActiveLog to organize my digital life and it's been amazing. It automatically organizes files, predicts what I need, and even helps me find things I didn't know I was looking for.\n\nTry it free: ${baseUrl}/signup?ref=${affiliateCode}\n\nBest regards!`,
          type: 'introduction'
        }
      ],
      socialMediaPosts: [
        {
          platform: 'twitter',
          content: `🚀 Tired of digital chaos? ActiveLog automatically organizes your files and predicts what you need next! Try it free: ${baseUrl}/signup?ref=${affiliateCode} #ProductivityTools #DigitalOrganization`
        },
        {
          platform: 'linkedin',
          content: `Professional recommendation: ActiveLog has revolutionized how I manage my digital workspace. It uses AI to predict what files I'll need and keeps everything perfectly organized. Check it out: ${baseUrl}/signup?ref=${affiliateCode}`
        }
      ]
    };
  }

  /**
   * Update affiliate payout method
   */
  async updatePayoutMethod(
    userId: string,
    payoutMethod: PaymentProvider
  ): Promise<AffiliateProgram> {
    const affiliateProgram = await this.getAffiliateProgram(userId);
    if (!affiliateProgram) {
      throw new Error('Affiliate program not found');
    }

    affiliateProgram.payoutMethod = payoutMethod;
    affiliateProgram.updatedAt = new Date();

    this.emit('payoutMethodUpdated', { userId, payoutMethod });
    return affiliateProgram;
  }

  /**
   * Process affiliate payouts
   */
  async processAffiliatePayouts(): Promise<{
    processedPayouts: number;
    totalAmount: Decimal;
    errors: string[];
  }> {
    let processedPayouts = 0;
    let totalAmount = new Decimal(0);
    const errors: string[] = [];

    // Get all confirmed referrals that need payout
    const unpaidReferrals = await this.getUnpaidReferrals();

    for (const referral of unpaidReferrals) {
      try {
        // Process payout via CC credits (already handled in confirmReferral)
        // or external payment method if configured
        
        referral.status = 'paid';
        referral.paidAt = new Date();
        
        processedPayouts++;
        totalAmount = totalAmount.add(referral.commissionAmount);
      } catch (error) {
        errors.push(`Failed to process payout for referral ${referral.id}: ${error}`);
      }
    }

    this.emit('affiliatePayoutsProcessed', { 
      processedPayouts, 
      totalAmount, 
      errorCount: errors.length 
    });

    return { processedPayouts, totalAmount, errors };
  }

  /**
   * Get affiliate leaderboard
   */
  async getAffiliateLeaderboard(
    period: 'current_month' | 'last_month' | 'all_time' = 'current_month',
    limit: number = 10
  ): Promise<Array<{
    rank: number;
    userId: string;
    affiliateCode: string;
    tier: AffiliateTier;
    referrals: number;
    earnings: Decimal;
    conversionRate: number;
  }>> {
    // Mock leaderboard data
    return [
      {
        rank: 1,
        userId: 'user-top1',
        affiliateCode: 'ALTOP1',
        tier: 'platinum',
        referrals: 45,
        earnings: new Decimal('1250.00'),
        conversionRate: 85.2
      },
      {
        rank: 2,
        userId: 'user-top2',
        affiliateCode: 'ALTOP2',
        tier: 'gold',
        referrals: 32,
        earnings: new Decimal('896.00'),
        conversionRate: 78.1
      }
    ].slice(0, limit);
  }

  // Private helper methods

  private generateAffiliateCode(userId: string): string {
    const randomSuffix = Math.random().toString(36).substring(2, 8).toUpperCase();
    return `AL${randomSuffix}`;
  }

  private async getAffiliateByCode(affiliateCode: string): Promise<AffiliateProgram | null> {
    // Mock implementation - would query database
    return null;
  }

  private async getReferral(referralId: string): Promise<AffiliateReferral | null> {
    // Mock implementation
    return {
      id: referralId,
      affiliateUserId: 'user-123',
      referredUserId: 'user-456',
      affiliateCode: 'AL123456',
      conversionType: 'subscription',
      conversionValue: new Decimal('29.99'),
      commissionAmount: new Decimal('4.50'),
      ccCreditsAwarded: new Decimal('450'),
      status: 'pending',
      createdAt: new Date()
    };
  }

  private async updateAffiliateStats(
    userId: string,
    commissionAmount: Decimal
  ): Promise<AffiliateProgram> {
    const affiliateProgram = await this.getAffiliateProgram(userId);
    if (!affiliateProgram) {
      throw new Error('Affiliate program not found');
    }

    // Update stats
    affiliateProgram.totalReferrals += 1;
    affiliateProgram.totalEarnings = affiliateProgram.totalEarnings.add(commissionAmount);
    affiliateProgram.currentMonthEarnings = affiliateProgram.currentMonthEarnings.add(commissionAmount);

    // Check for tier upgrade
    const newTier = this.calculateAffiliateTier(affiliateProgram.totalReferrals);
    if (newTier !== affiliateProgram.tier) {
      affiliateProgram.tier = newTier;
      affiliateProgram.commissionRate = new Decimal(this.TIER_CONFIG[newTier].commissionRate);
      
      this.emit('affiliateTierUpgraded', { 
        userId, 
        oldTier: affiliateProgram.tier, 
        newTier,
        totalReferrals: affiliateProgram.totalReferrals
      });
    }

    affiliateProgram.updatedAt = new Date();
    return affiliateProgram;
  }

  private calculateAffiliateTier(totalReferrals: number): AffiliateTier {
    if (totalReferrals >= this.TIER_CONFIG.platinum.minReferrals) return 'platinum';
    if (totalReferrals >= this.TIER_CONFIG.gold.minReferrals) return 'gold';
    if (totalReferrals >= this.TIER_CONFIG.silver.minReferrals) return 'silver';
    return 'bronze';
  }

  private calculateTierProgress(affiliateProgram: AffiliateProgram): {
    currentTier: AffiliateTier;
    nextTier: AffiliateTier | null;
    progressToNext: number;
    referralsToNext: number;
  } {
    const currentTier = affiliateProgram.tier;
    const totalReferrals = affiliateProgram.totalReferrals;

    const tierOrder: AffiliateTier[] = ['bronze', 'silver', 'gold', 'platinum'];
    const currentIndex = tierOrder.indexOf(currentTier);
    const nextTier = currentIndex < tierOrder.length - 1 ? tierOrder[currentIndex + 1] : null;

    if (!nextTier) {
      return {
        currentTier,
        nextTier: null,
        progressToNext: 100,
        referralsToNext: 0
      };
    }

    const nextTierRequirement = this.TIER_CONFIG[nextTier].minReferrals;
    const currentTierRequirement = this.TIER_CONFIG[currentTier].minReferrals;
    
    const progressToNext = Math.min(
      100,
      ((totalReferrals - currentTierRequirement) / 
       (nextTierRequirement - currentTierRequirement)) * 100
    );

    const referralsToNext = Math.max(0, nextTierRequirement - totalReferrals);

    return {
      currentTier,
      nextTier,
      progressToNext,
      referralsToNext
    };
  }

  private async getUnpaidReferrals(): Promise<AffiliateReferral[]> {
    // Mock implementation - would query database for confirmed but unpaid referrals
    return [];
  }

  private async convertToUSD(amount: Decimal, currency: CurrencyCode): Promise<Decimal> {
    // Mock conversion - would use exchange rate service
    const conversionRates: Record<CurrencyCode, number> = {
      USD: 1,
      EUR: 1.1,
      GBP: 1.25,
      JPY: 0.007,
      CAD: 0.75,
      AUD: 0.65,
      CHF: 1.1,
      CNY: 0.14,
      INR: 0.012,
      BRL: 0.18
    };

    return amount.mul(conversionRates[currency] || 1);
  }
}