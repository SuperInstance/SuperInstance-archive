const database = require('../config/database');
const logger = require('../utils/logger');

class AdSenseService {
  
  // Get user subscription to determine ad eligibility
  async getUserSubscription(userId) {
    try {
      return await database('subscriptions')
        .where('user_id', userId)
        .where('status', '!=', 'canceled')
        .first();
    } catch (error) {
      logger.error('Failed to get user subscription for ads:', error);
      return null;
    }
  }

  // Get ad configuration based on subscription plan
  getAdConfigForPlan(plan) {
    const configs = {
      free: {
        enabled: true,
        adUnits: [
          {
            id: 'banner-top',
            type: 'display',
            size: '728x90',
            placement: 'header',
            code: process.env.ADSENSE_BANNER_TOP_UNIT || 'ca-pub-XXXXXXXXXXXXXXXX/XXXXXXXXXX'
          },
          {
            id: 'sidebar-medium',
            type: 'display',
            size: '300x250',
            placement: 'sidebar',
            code: process.env.ADSENSE_SIDEBAR_UNIT || 'ca-pub-XXXXXXXXXXXXXXXX/XXXXXXXXXX'
          },
          {
            id: 'content-inline',
            type: 'display',
            size: '320x100',
            placement: 'content',
            code: process.env.ADSENSE_CONTENT_UNIT || 'ca-pub-XXXXXXXXXXXXXXXX/XXXXXXXXXX'
          }
        ],
        frequency: {
          impressions: 5, // Show ad every 5 page views
          timeInterval: 30, // Minimum 30 seconds between ads
          maxPerSession: 10 // Maximum 10 ads per session
        },
        placements: ['header', 'sidebar', 'content', 'footer']
      },
      pro: {
        enabled: false,
        adUnits: [],
        frequency: {},
        placements: []
      },
      enterprise: {
        enabled: false,
        adUnits: [],
        frequency: {},
        placements: []
      }
    };

    return configs[plan] || configs.free;
  }

  // Get available ad units
  getAvailableAdUnits() {
    return [
      {
        id: 'banner-top',
        name: 'Top Banner',
        type: 'display',
        sizes: ['728x90', '970x90'],
        placement: 'header',
        description: 'Horizontal banner at the top of the page'
      },
      {
        id: 'sidebar-medium',
        name: 'Sidebar Rectangle',
        type: 'display',
        sizes: ['300x250', '336x280'],
        placement: 'sidebar',
        description: 'Medium rectangle in the sidebar'
      },
      {
        id: 'content-inline',
        name: 'In-Content Ad',
        type: 'display',
        sizes: ['320x100', '300x100'],
        placement: 'content',
        description: 'Small banner within content'
      },
      {
        id: 'mobile-banner',
        name: 'Mobile Banner',
        type: 'display',
        sizes: ['320x50', '320x100'],
        placement: 'mobile',
        description: 'Banner optimized for mobile devices'
      }
    ];
  }

  // Track ad impression
  async trackImpression(userId, impressionData) {
    try {
      // Check if user should see ads
      const subscription = await this.getUserSubscription(userId);
      const plan = subscription?.plan || 'free';
      
      if (plan !== 'free') {
        throw new Error('Ads are not shown to paid plan users');
      }

      // Check impression frequency limits
      await this.checkImpressionLimits(userId);

      const impression = await database('ad_impressions').insert({
        user_id: userId,
        ad_unit_id: impressionData.adUnitId,
        placement: impressionData.placement,
        page_url: impressionData.pageUrl,
        referrer: impressionData.referrer,
        device_type: impressionData.deviceType,
        user_agent: impressionData.userAgent,
        ip_address: impressionData.ip,
        created_at: new Date()
      }).returning('*').first();

      // Update user's ad impression count
      await this.updateUserAdStats(userId, 'impressions', 1);

      return impression;
    } catch (error) {
      logger.error('Failed to track ad impression:', error);
      throw error;
    }
  }

  // Track ad click
  async trackClick(userId, clickData) {
    try {
      const click = await database('ad_clicks').insert({
        user_id: userId,
        ad_impression_id: clickData.impressionId,
        ad_unit_id: clickData.adUnitId,
        placement: clickData.placement,
        click_url: clickData.clickUrl,
        user_agent: clickData.userAgent,
        ip_address: clickData.ip,
        created_at: new Date()
      }).returning('*').first();

      // Update user's ad click count
      await this.updateUserAdStats(userId, 'clicks', 1);

      // Calculate and record revenue (simplified - real AdSense integration would get actual revenue)
      const estimatedRevenue = this.calculateEstimatedRevenue(clickData.adUnitId);
      if (estimatedRevenue > 0) {
        await this.recordAdRevenue(userId, click.id, estimatedRevenue);
      }

      return click;
    } catch (error) {
      logger.error('Failed to track ad click:', error);
      throw error;
    }
  }

  // Check impression limits to prevent ad fatigue
  async checkImpressionLimits(userId) {
    try {
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const todayImpressions = await database('ad_impressions')
        .where('user_id', userId)
        .where('created_at', '>=', today)
        .count('* as count')
        .first();

      const count = parseInt(todayImpressions.count);
      const maxDailyImpressions = 50; // Reasonable limit

      if (count >= maxDailyImpressions) {
        throw new Error('Daily ad impression limit reached');
      }
    } catch (error) {
      logger.error('Failed to check impression limits:', error);
      throw error;
    }
  }

  // Update user's ad statistics
  async updateUserAdStats(userId, statType, increment = 1) {
    try {
      const currentMonth = new Date();
      currentMonth.setDate(1);
      currentMonth.setHours(0, 0, 0, 0);

      await database('user_ad_stats')
        .where('user_id', userId)
        .where('period_start', currentMonth)
        .increment(statType, increment)
        .orInsert({
          user_id: userId,
          period_start: currentMonth,
          period_end: new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0),
          impressions: statType === 'impressions' ? increment : 0,
          clicks: statType === 'clicks' ? increment : 0,
          revenue_cents: 0,
          created_at: new Date(),
          updated_at: new Date()
        });
    } catch (error) {
      logger.error('Failed to update user ad stats:', error);
      // Don't throw - this is not critical
    }
  }

  // Calculate estimated revenue per click (simplified model)
  calculateEstimatedRevenue(adUnitId) {
    // These are estimated CPCs in cents - real implementation would use actual AdSense data
    const cpcRates = {
      'banner-top': 25, // $0.25
      'sidebar-medium': 35, // $0.35
      'content-inline': 20, // $0.20
      'mobile-banner': 15 // $0.15
    };

    return cpcRates[adUnitId] || 20; // Default $0.20
  }

  // Record ad revenue for user
  async recordAdRevenue(userId, clickId, revenueCents) {
    try {
      // Revenue sharing: 60% to user, 40% to platform
      const userShare = Math.round(revenueCents * 0.6);
      const platformShare = revenueCents - userShare;

      await database('ad_revenues').insert({
        user_id: userId,
        ad_click_id: clickId,
        total_revenue_cents: revenueCents,
        user_share_cents: userShare,
        platform_share_cents: platformShare,
        created_at: new Date()
      });

      // Update user's total ad stats
      await this.updateUserAdStats(userId, 'revenue_cents', userShare);

      logger.info('Ad revenue recorded', {
        userId,
        clickId,
        totalRevenue: revenueCents,
        userShare
      });
    } catch (error) {
      logger.error('Failed to record ad revenue:', error);
      // Don't throw - this is not critical for click tracking
    }
  }

  // Get ad performance statistics
  async getAdStats(userId, options = {}) {
    try {
      const { period, startDate, endDate, adUnitId, placement } = options;
      
      let dateFilter = {};
      if (startDate && endDate) {
        dateFilter.start = startDate;
        dateFilter.end = endDate;
      } else if (period) {
        dateFilter = this.parsePeriod(period);
      } else {
        dateFilter = this.parsePeriod('30d');
      }

      // Build base queries
      let impressionsQuery = database('ad_impressions')
        .where('user_id', userId)
        .whereBetween('created_at', [dateFilter.start, dateFilter.end]);

      let clicksQuery = database('ad_clicks')
        .where('user_id', userId)
        .whereBetween('created_at', [dateFilter.start, dateFilter.end]);

      if (adUnitId) {
        impressionsQuery = impressionsQuery.where('ad_unit_id', adUnitId);
        clicksQuery = clicksQuery.where('ad_unit_id', adUnitId);
      }

      if (placement) {
        impressionsQuery = impressionsQuery.where('placement', placement);
        clicksQuery = clicksQuery.where('placement', placement);
      }

      // Get statistics
      const [impressionsResult, clicksResult, revenueResult] = await Promise.all([
        impressionsQuery.count('* as total').first(),
        clicksQuery.count('* as total').first(),
        database('ad_revenues')
          .where('user_id', userId)
          .whereBetween('created_at', [dateFilter.start, dateFilter.end])
          .sum('user_share_cents as revenue')
          .first()
      ]);

      const impressions = parseInt(impressionsResult.total) || 0;
      const clicks = parseInt(clicksResult.total) || 0;
      const revenue = parseInt(revenueResult.revenue) || 0;

      const ctr = impressions > 0 ? (clicks / impressions) * 100 : 0;
      const rpm = impressions > 0 ? (revenue / impressions) * 1000 : 0;

      return {
        period: dateFilter,
        impressions,
        clicks,
        ctr: parseFloat(ctr.toFixed(2)),
        revenue,
        rpm: parseFloat(rpm.toFixed(2)),
        topPerformingUnits: await this.getTopPerformingAdUnits(userId, dateFilter),
        performanceByPlacement: await this.getPerformanceByPlacement(userId, dateFilter),
        dailyStats: await this.getDailyAdStats(userId, dateFilter)
      };
    } catch (error) {
      logger.error('Failed to get ad stats:', error);
      throw error;
    }
  }

  // Parse period string to date range
  parsePeriod(period) {
    const end = new Date();
    const start = new Date();

    if (period === '7d') {
      start.setDate(start.getDate() - 7);
    } else if (period === '30d') {
      start.setDate(start.getDate() - 30);
    } else if (period === '90d') {
      start.setDate(start.getDate() - 90);
    }

    return { start, end, period };
  }

  // Get top performing ad units
  async getTopPerformingAdUnits(userId, dateFilter) {
    try {
      return await database('ad_impressions')
        .leftJoin('ad_clicks', 'ad_impressions.id', 'ad_clicks.ad_impression_id')
        .where('ad_impressions.user_id', userId)
        .whereBetween('ad_impressions.created_at', [dateFilter.start, dateFilter.end])
        .groupBy('ad_impressions.ad_unit_id')
        .select('ad_impressions.ad_unit_id as adUnitId')
        .count('ad_impressions.id as impressions')
        .count('ad_clicks.id as clicks')
        .orderBy('impressions', 'desc')
        .limit(5);
    } catch (error) {
      logger.error('Failed to get top performing ad units:', error);
      return [];
    }
  }

  // Get performance by placement
  async getPerformanceByPlacement(userId, dateFilter) {
    try {
      return await database('ad_impressions')
        .leftJoin('ad_clicks', 'ad_impressions.id', 'ad_clicks.ad_impression_id')
        .where('ad_impressions.user_id', userId)
        .whereBetween('ad_impressions.created_at', [dateFilter.start, dateFilter.end])
        .groupBy('ad_impressions.placement')
        .select('ad_impressions.placement')
        .count('ad_impressions.id as impressions')
        .count('ad_clicks.id as clicks');
    } catch (error) {
      logger.error('Failed to get performance by placement:', error);
      return [];
    }
  }

  // Get daily ad statistics
  async getDailyAdStats(userId, dateFilter) {
    try {
      const [impressions, clicks] = await Promise.all([
        database('ad_impressions')
          .where('user_id', userId)
          .whereBetween('created_at', [dateFilter.start, dateFilter.end])
          .select(database.raw('DATE(created_at) as date'))
          .count('* as impressions')
          .groupBy(database.raw('DATE(created_at)'))
          .orderBy('date'),
        
        database('ad_clicks')
          .where('user_id', userId)
          .whereBetween('created_at', [dateFilter.start, dateFilter.end])
          .select(database.raw('DATE(created_at) as date'))
          .count('* as clicks')
          .groupBy(database.raw('DATE(created_at)'))
          .orderBy('date')
      ]);

      // Merge data
      const dailyStats = {};
      impressions.forEach(day => {
        dailyStats[day.date] = { impressions: parseInt(day.impressions), clicks: 0 };
      });
      clicks.forEach(day => {
        if (dailyStats[day.date]) {
          dailyStats[day.date].clicks = parseInt(day.clicks);
        } else {
          dailyStats[day.date] = { impressions: 0, clicks: parseInt(day.clicks) };
        }
      });

      return Object.entries(dailyStats).map(([date, stats]) => ({
        date,
        ...stats,
        ctr: stats.impressions > 0 ? (stats.clicks / stats.impressions) * 100 : 0
      }));
    } catch (error) {
      logger.error('Failed to get daily ad stats:', error);
      return [];
    }
  }

  // Update user's ad settings
  async updateAdSettings(userId, settings) {
    try {
      const existing = await database('user_ad_settings')
        .where('user_id', userId)
        .first();

      if (existing) {
        return await database('user_ad_settings')
          .where('user_id', userId)
          .update({
            personalized_ads: settings.personalizedAds,
            ad_frequency: settings.adFrequency,
            blocked_categories: JSON.stringify(settings.blockedCategories),
            updated_at: new Date()
          })
          .returning('*')
          .first();
      } else {
        return await database('user_ad_settings')
          .insert({
            user_id: userId,
            personalized_ads: settings.personalizedAds,
            ad_frequency: settings.adFrequency,
            blocked_categories: JSON.stringify(settings.blockedCategories),
            created_at: new Date(),
            updated_at: new Date()
          })
          .returning('*')
          .first();
      }
    } catch (error) {
      logger.error('Failed to update ad settings:', error);
      throw error;
    }
  }

  // Get user's ad settings
  async getAdSettings(userId) {
    try {
      const settings = await database('user_ad_settings')
        .where('user_id', userId)
        .first();

      return settings || {
        personalized_ads: true,
        ad_frequency: 'normal',
        blocked_categories: []
      };
    } catch (error) {
      logger.error('Failed to get ad settings:', error);
      throw error;
    }
  }

  // Report inappropriate ad
  async reportAd(userId, reportData) {
    try {
      const report = await database('ad_reports').insert({
        user_id: userId,
        ad_unit_id: reportData.adUnitId,
        ad_impression_id: reportData.impressionId,
        reason: reportData.reason,
        description: reportData.description,
        ad_content: reportData.adContent,
        user_agent: reportData.userAgent,
        ip_address: reportData.ip,
        status: 'pending',
        created_at: new Date()
      }).returning('*').first();

      return report;
    } catch (error) {
      logger.error('Failed to report ad:', error);
      throw error;
    }
  }

  // Get revenue sharing information
  getRevenueShareInfo() {
    return {
      userShare: 60, // 60% to user
      platformShare: 40, // 40% to platform
      description: 'Free plan users receive 60% of ad revenue generated from their usage',
      minimumPayout: 1000 // $10.00 minimum payout
    };
  }

  // Get user's ad earnings
  async getUserAdEarnings(userId) {
    try {
      const [totalResult, thisMonthResult, lastMonthResult, pendingResult, paidResult] = await Promise.all([
        database('ad_revenues')
          .where('user_id', userId)
          .sum('user_share_cents as total')
          .first(),
        
        // This month
        database('ad_revenues')
          .where('user_id', userId)
          .where('created_at', '>=', new Date(new Date().getFullYear(), new Date().getMonth(), 1))
          .sum('user_share_cents as thisMonth')
          .first(),
        
        // Last month
        database('ad_revenues')
          .where('user_id', userId)
          .whereBetween('created_at', [
            new Date(new Date().getFullYear(), new Date().getMonth() - 1, 1),
            new Date(new Date().getFullYear(), new Date().getMonth(), 0)
          ])
          .sum('user_share_cents as lastMonth')
          .first(),
        
        // Pending (unpaid)
        database('ad_revenues')
          .where('user_id', userId)
          .where('paid_out', false)
          .sum('user_share_cents as pending')
          .first(),
        
        // Paid out
        database('ad_payouts')
          .where('user_id', userId)
          .where('status', 'completed')
          .sum('amount_cents as paid')
          .first()
      ]);

      const total = parseInt(totalResult.total) || 0;
      const thisMonth = parseInt(thisMonthResult.thisMonth) || 0;
      const lastMonth = parseInt(lastMonthResult.lastMonth) || 0;
      const pending = parseInt(pendingResult.pending) || 0;
      const paid = parseInt(paidResult.paid) || 0;
      const minimumPayout = 1000; // $10.00

      // Next payout date (first of next month if above minimum)
      const nextPayoutDate = pending >= minimumPayout 
        ? new Date(new Date().getFullYear(), new Date().getMonth() + 1, 1)
        : null;

      return {
        total,
        thisMonth,
        lastMonth,
        pending,
        paid,
        nextPayoutDate,
        minimumPayout
      };
    } catch (error) {
      logger.error('Failed to get user ad earnings:', error);
      throw error;
    }
  }
}

module.exports = AdSenseService;