import { Decimal } from 'decimal.js';
import { v4 as uuidv4 } from 'uuid';
import { EventEmitter } from 'events';
import { 
  AdRevenue, 
  AdNetwork, 
  CurrencyCode, 
  ComputeCredit 
} from '../types';
import { CCreditSystem } from '../core/CCreditSystem';

export class AdRevenueService extends EventEmitter {
  private ccreditSystem: CCreditSystem;
  private readonly USER_REVENUE_SHARE = 0.90; // 90% to users
  private readonly PLATFORM_REVENUE_SHARE = 0.10; // 10% to platform

  constructor(ccreditSystem: CCreditSystem) {
    super();
    this.ccreditSystem = ccreditSystem;
  }

  /**
   * Create a new ad network configuration
   */
  async createAdNetwork(
    name: string,
    apiKey: string,
    revenueSharePercentage: number = 10,
    minPayoutThreshold: Decimal = new Decimal(1)
  ): Promise<AdNetwork> {
    const adNetwork: AdNetwork = {
      id: uuidv4(),
      name,
      apiKey,
      revenueSharePercentage,
      minPayoutThreshold,
      isActive: true,
      createdAt: new Date()
    };

    this.emit('adNetworkCreated', { adNetwork });
    return adNetwork;
  }

  /**
   * Track ad revenue for a user
   */
  async trackAdRevenue(
    userId: string,
    adNetworkId: string,
    impressions: number,
    clicks: number,
    revenue: Decimal,
    currency: CurrencyCode,
    reportingPeriod: Date
  ): Promise<AdRevenue> {
    // Calculate revenue shares
    const userShare = revenue.mul(this.USER_REVENUE_SHARE);
    const platformShare = revenue.mul(this.PLATFORM_REVENUE_SHARE);

    // Convert user share to CC credits (1 USD = 100 CC)
    const ccCreditsAwarded = this.ccreditSystem.getUSDValueInCC(
      currency === 'USD' ? userShare : await this.convertToUSD(userShare, currency)
    );

    const adRevenue: AdRevenue = {
      id: uuidv4(),
      userId,
      adNetworkId,
      impressions,
      clicks,
      revenue,
      currency,
      userShare,
      platformShare,
      ccCreditsAwarded,
      reportingPeriod,
      status: 'pending',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.emit('adRevenueTracked', { adRevenue });
    return adRevenue;
  }

  /**
   * Confirm ad revenue and award CC credits to user
   */
  async confirmAdRevenue(adRevenueId: string): Promise<{
    adRevenue: AdRevenue;
    creditAwarded: ComputeCredit;
  }> {
    // Fetch ad revenue record (mock implementation)
    const adRevenue = await this.getAdRevenue(adRevenueId);
    
    if (adRevenue.status !== 'pending') {
      throw new Error('Ad revenue has already been processed');
    }

    // Award CC credits to user
    const creditAwarded = await this.ccreditSystem.awardCredits(
      adRevenue.userId,
      adRevenue.ccCreditsAwarded,
      adRevenue.currency,
      'ad_revenue',
      adRevenueId,
      undefined,
      {
        adNetworkId: adRevenue.adNetworkId,
        impressions: adRevenue.impressions,
        clicks: adRevenue.clicks,
        revenue: adRevenue.revenue.toString(),
        userShare: adRevenue.userShare.toString(),
        reportingPeriod: adRevenue.reportingPeriod.toISOString()
      }
    );

    // Update ad revenue status
    adRevenue.status = 'confirmed';
    adRevenue.updatedAt = new Date();

    this.emit('adRevenueConfirmed', { adRevenue, creditAwarded });
    return { adRevenue, creditAwarded };
  }

  /**
   * Get user's ad revenue history
   */
  async getUserAdRevenue(
    userId: string,
    startDate?: Date,
    endDate?: Date,
    limit: number = 50,
    offset: number = 0
  ): Promise<{
    adRevenues: AdRevenue[];
    totalRevenue: Decimal;
    totalCCCredits: Decimal;
    summary: {
      totalImpressions: number;
      totalClicks: number;
      averageCTR: number;
      averageRevenue: Decimal;
    };
  }> {
    // Mock implementation - would query database
    const mockAdRevenues: AdRevenue[] = [
      {
        id: uuidv4(),
        userId,
        adNetworkId: 'network-1',
        impressions: 10000,
        clicks: 50,
        revenue: new Decimal('5.00'),
        currency: 'USD',
        userShare: new Decimal('4.50'),
        platformShare: new Decimal('0.50'),
        ccCreditsAwarded: new Decimal('450'),
        reportingPeriod: new Date('2024-01-01'),
        status: 'confirmed',
        createdAt: new Date('2024-01-02'),
        updatedAt: new Date('2024-01-02')
      }
    ];

    const filteredRevenues = mockAdRevenues.filter(ar => {
      if (startDate && new Date(ar.reportingPeriod) < startDate) return false;
      if (endDate && new Date(ar.reportingPeriod) > endDate) return false;
      return true;
    }).slice(offset, offset + limit);

    const totalRevenue = filteredRevenues.reduce(
      (sum, ar) => sum.add(ar.userShare), 
      new Decimal(0)
    );

    const totalCCCredits = filteredRevenues.reduce(
      (sum, ar) => sum.add(ar.ccCreditsAwarded), 
      new Decimal(0)
    );

    const totalImpressions = filteredRevenues.reduce(
      (sum, ar) => sum + ar.impressions, 
      0
    );

    const totalClicks = filteredRevenues.reduce(
      (sum, ar) => sum + ar.clicks, 
      0
    );

    return {
      adRevenues: filteredRevenues,
      totalRevenue,
      totalCCCredits,
      summary: {
        totalImpressions,
        totalClicks,
        averageCTR: totalImpressions > 0 ? (totalClicks / totalImpressions) * 100 : 0,
        averageRevenue: filteredRevenues.length > 0 
          ? totalRevenue.div(filteredRevenues.length) 
          : new Decimal(0)
      }
    };
  }

  /**
   * Sync ad revenue from external ad networks
   */
  async syncAdNetworkRevenue(adNetworkId: string, reportingPeriod: Date): Promise<{
    syncedRevenues: AdRevenue[];
    totalSynced: number;
    errors: string[];
  }> {
    const adNetwork = await this.getAdNetwork(adNetworkId);
    const syncedRevenues: AdRevenue[] = [];
    const errors: string[] = [];

    try {
      // Mock external API call to fetch ad data
      const externalAdData = await this.fetchExternalAdData(adNetwork, reportingPeriod);
      
      for (const adData of externalAdData) {
        try {
          const adRevenue = await this.trackAdRevenue(
            adData.userId,
            adNetworkId,
            adData.impressions,
            adData.clicks,
            new Decimal(adData.revenue),
            adData.currency || 'USD',
            reportingPeriod
          );

          // Auto-confirm if revenue is above threshold
          if (adRevenue.userShare.gte(adNetwork.minPayoutThreshold)) {
            await this.confirmAdRevenue(adRevenue.id);
          }

          syncedRevenues.push(adRevenue);
        } catch (error) {
          errors.push(`Failed to sync revenue for user ${adData.userId}: ${error}`);
        }
      }
    } catch (error) {
      errors.push(`Failed to fetch data from ad network: ${error}`);
    }

    this.emit('adRevenueSynced', { 
      adNetworkId, 
      reportingPeriod, 
      syncedCount: syncedRevenues.length,
      errorCount: errors.length 
    });

    return {
      syncedRevenues,
      totalSynced: syncedRevenues.length,
      errors
    };
  }

  /**
   * Get ad revenue analytics for a user
   */
  async getAdRevenueAnalytics(
    userId: string,
    period: 'daily' | 'weekly' | 'monthly' = 'monthly',
    timeRange?: { start: Date; end: Date }
  ): Promise<{
    periodData: Array<{
      period: string;
      impressions: number;
      clicks: number;
      revenue: Decimal;
      ccCredits: Decimal;
      ctr: number;
      rpm: Decimal; // Revenue per mille (1000 impressions)
    }>;
    trends: {
      revenueGrowth: number; // percentage
      impressionGrowth: number;
      ctrTrend: number;
    };
    topPerformingNetworks: Array<{
      networkId: string;
      networkName: string;
      revenue: Decimal;
      impressions: number;
      ctr: number;
    }>;
  }> {
    // Mock analytics data
    const periodData = [
      {
        period: '2024-01',
        impressions: 50000,
        clicks: 250,
        revenue: new Decimal('25.00'),
        ccCredits: new Decimal('2250'),
        ctr: 0.5,
        rpm: new Decimal('0.50')
      },
      {
        period: '2024-02',
        impressions: 55000,
        clicks: 275,
        revenue: new Decimal('27.50'),
        ccCredits: new Decimal('2475'),
        ctr: 0.5,
        rpm: new Decimal('0.50')
      }
    ];

    return {
      periodData,
      trends: {
        revenueGrowth: 10.0, // 10% growth
        impressionGrowth: 10.0,
        ctrTrend: 0.0 // No change in CTR
      },
      topPerformingNetworks: [
        {
          networkId: 'network-1',
          networkName: 'Google AdSense',
          revenue: new Decimal('52.50'),
          impressions: 105000,
          ctr: 0.5
        }
      ]
    };
  }

  /**
   * Set minimum payout threshold for a user
   */
  async setUserPayoutThreshold(
    userId: string,
    threshold: Decimal,
    currency: CurrencyCode = 'USD'
  ): Promise<void> {
    // Store user's custom payout threshold
    // This would be saved to database
    
    this.emit('payoutThresholdUpdated', { userId, threshold, currency });
  }

  /**
   * Process pending ad revenue payouts
   */
  async processPayouts(): Promise<{
    processedPayouts: number;
    totalCCAwarded: Decimal;
    errors: string[];
  }> {
    let processedPayouts = 0;
    let totalCCAwarded = new Decimal(0);
    const errors: string[] = [];

    // Get all pending ad revenues that meet payout threshold
    const pendingRevenues = await this.getPendingAdRevenues();

    for (const adRevenue of pendingRevenues) {
      try {
        const { creditAwarded } = await this.confirmAdRevenue(adRevenue.id);
        processedPayouts++;
        totalCCAwarded = totalCCAwarded.add(creditAwarded.amount);
      } catch (error) {
        errors.push(`Failed to process payout for ${adRevenue.id}: ${error}`);
      }
    }

    this.emit('payoutsProcessed', { processedPayouts, totalCCAwarded, errorCount: errors.length });

    return {
      processedPayouts,
      totalCCAwarded,
      errors
    };
  }

  /**
   * Get ad network performance metrics
   */
  async getAdNetworkMetrics(adNetworkId: string): Promise<{
    totalRevenue: Decimal;
    totalImpressions: number;
    totalClicks: number;
    averageCTR: number;
    averageRPM: Decimal;
    activeUsers: number;
    revenueByMonth: Array<{
      month: string;
      revenue: Decimal;
      impressions: number;
      clicks: number;
    }>;
  }> {
    // Mock metrics
    return {
      totalRevenue: new Decimal('1250.00'),
      totalImpressions: 2500000,
      totalClicks: 12500,
      averageCTR: 0.5,
      averageRPM: new Decimal('0.50'),
      activeUsers: 250,
      revenueByMonth: [
        {
          month: '2024-01',
          revenue: new Decimal('500.00'),
          impressions: 1000000,
          clicks: 5000
        },
        {
          month: '2024-02',
          revenue: new Decimal('750.00'),
          impressions: 1500000,
          clicks: 7500
        }
      ]
    };
  }

  // Private helper methods

  private async getAdRevenue(adRevenueId: string): Promise<AdRevenue> {
    // Mock implementation - would fetch from database
    return {
      id: adRevenueId,
      userId: 'user-123',
      adNetworkId: 'network-1',
      impressions: 10000,
      clicks: 50,
      revenue: new Decimal('5.00'),
      currency: 'USD',
      userShare: new Decimal('4.50'),
      platformShare: new Decimal('0.50'),
      ccCreditsAwarded: new Decimal('450'),
      reportingPeriod: new Date(),
      status: 'pending',
      createdAt: new Date(),
      updatedAt: new Date()
    };
  }

  private async getAdNetwork(adNetworkId: string): Promise<AdNetwork> {
    // Mock implementation - would fetch from database
    return {
      id: adNetworkId,
      name: 'Google AdSense',
      apiKey: 'mock-api-key',
      revenueSharePercentage: 10,
      minPayoutThreshold: new Decimal('1.00'),
      isActive: true,
      createdAt: new Date()
    };
  }

  private async fetchExternalAdData(
    adNetwork: AdNetwork,
    reportingPeriod: Date
  ): Promise<Array<{
    userId: string;
    impressions: number;
    clicks: number;
    revenue: number;
    currency?: CurrencyCode;
  }>> {
    // Mock external API integration
    return [
      {
        userId: 'user-123',
        impressions: 10000,
        clicks: 50,
        revenue: 5.00,
        currency: 'USD'
      }
    ];
  }

  private async getPendingAdRevenues(): Promise<AdRevenue[]> {
    // Mock implementation - would query database for pending revenues
    return [];
  }

  private async convertToUSD(amount: Decimal, currency: CurrencyCode): Promise<Decimal> {
    // Use exchange rate service to convert to USD
    if (currency === 'USD') return amount;
    
    // Mock conversion rate
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