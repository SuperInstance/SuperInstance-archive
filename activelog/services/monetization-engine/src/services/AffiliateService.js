const database = require('../config/database');
const logger = require('../utils/logger');
const crypto = require('crypto');

class AffiliateService {

  // Register new affiliate
  async registerAffiliate(affiliateData) {
    const transaction = await database.transaction();
    
    try {
      // Check if email already exists
      const existingAffiliate = await database('affiliates')
        .where('email', affiliateData.email)
        .first();

      if (existingAffiliate) {
        throw new Error('Affiliate with this email already exists');
      }

      // Generate unique affiliate code
      const affiliateCode = await this.generateUniqueAffiliateCode();

      const affiliate = await database('affiliates')
        .insert({
          name: affiliateData.name,
          email: affiliateData.email,
          affiliate_code: affiliateCode,
          website: affiliateData.website,
          social_media: JSON.stringify(affiliateData.socialMedia),
          audience: affiliateData.audience,
          promotion_method: affiliateData.promotionMethod,
          tax_id: affiliateData.taxId,
          payment_method: affiliateData.paymentMethod,
          commission_rate: 0.15, // Default 15% commission
          tier_level: 'bronze',
          status: 'pending', // Requires approval
          created_at: new Date(),
          updated_at: new Date()
        })
        .returning('*')
        .first();

      await transaction.commit();

      logger.affiliate('New affiliate registered', {
        affiliateId: affiliate.id,
        email: affiliateData.email,
        name: affiliateData.name
      });

      return affiliate;
    } catch (error) {
      await transaction.rollback();
      logger.error('Failed to register affiliate:', error);
      throw error;
    }
  }

  // Generate unique affiliate code
  async generateUniqueAffiliateCode() {
    let attempts = 0;
    const maxAttempts = 10;

    while (attempts < maxAttempts) {
      const code = this.generateAffiliateCode();
      
      const existing = await database('affiliates')
        .where('affiliate_code', code)
        .first();

      if (!existing) {
        return code;
      }
      
      attempts++;
    }

    // Fallback to timestamp-based code if all attempts fail
    return `AFL${Date.now().toString(36).toUpperCase()}`;
  }

  generateAffiliateCode() {
    // Generate 8-character alphanumeric code
    return crypto.randomBytes(4).toString('hex').toUpperCase();
  }

  // Get affiliate by user ID
  async getAffiliateByUserId(userId) {
    try {
      return await database('affiliates')
        .where('user_id', userId)
        .first();
    } catch (error) {
      logger.error('Failed to get affiliate by user ID:', error);
      throw error;
    }
  }

  // Get affiliate by code
  async getAffiliateByCode(affiliateCode) {
    try {
      return await database('affiliates')
        .where('affiliate_code', affiliateCode.toUpperCase())
        .first();
    } catch (error) {
      logger.error('Failed to get affiliate by code:', error);
      throw error;
    }
  }

  // Get affiliate dashboard data
  async getAffiliateDashboard(affiliateId) {
    try {
      const [stats, earnings, recentReferrals, topLinks] = await Promise.all([
        this.getAffiliateStatsOverview(affiliateId),
        this.getAffiliateEarnings(affiliateId),
        this.getRecentReferrals(affiliateId, 5),
        this.getTopPerformingLinks(affiliateId, 5)
      ]);

      return {
        stats,
        earnings,
        referrals: recentReferrals,
        links: topLinks
      };
    } catch (error) {
      logger.error('Failed to get affiliate dashboard:', error);
      throw error;
    }
  }

  // Get affiliate stats overview
  async getAffiliateStatsOverview(affiliateId) {
    try {
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

      const [clicksResult, conversionsResult] = await Promise.all([
        database('affiliate_clicks')
          .where('affiliate_id', affiliateId)
          .where('created_at', '>=', thirtyDaysAgo)
          .count('* as total'),
        
        database('affiliate_conversions')
          .where('affiliate_id', affiliateId)
          .where('created_at', '>=', thirtyDaysAgo)
          .count('* as total')
          .sum('commission_amount as earnings')
      ]);

      const clicks = clicksResult[0]?.total || 0;
      const conversions = conversionsResult[0]?.total || 0;
      const earnings = conversionsResult[0]?.earnings || 0;
      const conversionRate = clicks > 0 ? (conversions / clicks) * 100 : 0;

      return {
        last30Days: {
          clicks: parseInt(clicks),
          conversions: parseInt(conversions),
          earnings: parseInt(earnings),
          conversionRate: parseFloat(conversionRate.toFixed(2))
        }
      };
    } catch (error) {
      logger.error('Failed to get affiliate stats overview:', error);
      throw error;
    }
  }

  // Get affiliate earnings summary
  async getAffiliateEarnings(affiliateId) {
    try {
      const [totalResult, pendingResult, paidResult] = await Promise.all([
        database('affiliate_conversions')
          .where('affiliate_id', affiliateId)
          .sum('commission_amount as total'),
        
        database('affiliate_conversions')
          .where('affiliate_id', affiliateId)
          .where('status', 'pending')
          .sum('commission_amount as pending'),
        
        database('affiliate_payouts')
          .where('affiliate_id', affiliateId)
          .where('status', 'completed')
          .sum('amount as paid')
      ]);

      return {
        total: totalResult[0]?.total || 0,
        pending: pendingResult[0]?.pending || 0,
        paid: paidResult[0]?.paid || 0,
        available: (totalResult[0]?.total || 0) - (paidResult[0]?.paid || 0)
      };
    } catch (error) {
      logger.error('Failed to get affiliate earnings:', error);
      throw error;
    }
  }

  // Generate affiliate link
  async generateAffiliateLink(affiliateId, linkData) {
    try {
      const shortCode = this.generateShortCode();
      const baseUrl = process.env.AFFILIATE_BASE_URL || 'https://activelog.com/ref';
      
      const affiliateUrl = this.buildAffiliateUrl(linkData.targetUrl, {
        affiliateId,
        campaign: linkData.campaign,
        medium: linkData.medium,
        content: linkData.content
      });

      const link = await database('affiliate_links')
        .insert({
          affiliate_id: affiliateId,
          short_code: shortCode,
          target_url: linkData.targetUrl,
          affiliate_url: affiliateUrl,
          short_url: `${baseUrl}/${shortCode}`,
          campaign: linkData.campaign,
          medium: linkData.medium,
          content: linkData.content,
          total_clicks: 0,
          total_conversions: 0,
          total_earnings: 0,
          is_active: true,
          created_at: new Date(),
          updated_at: new Date()
        })
        .returning('*')
        .first();

      return link;
    } catch (error) {
      logger.error('Failed to generate affiliate link:', error);
      throw error;
    }
  }

  // Build affiliate URL with tracking parameters
  buildAffiliateUrl(targetUrl, params) {
    try {
      const url = new URL(targetUrl);
      
      // Add affiliate tracking parameters
      url.searchParams.set('ref', params.affiliateId);
      url.searchParams.set('utm_source', 'affiliate');
      url.searchParams.set('utm_medium', params.medium);
      url.searchParams.set('utm_campaign', params.campaign);
      
      if (params.content) {
        url.searchParams.set('utm_content', params.content);
      }
      
      return url.toString();
    } catch (error) {
      logger.error('Failed to build affiliate URL:', error);
      return targetUrl;
    }
  }

  // Generate short code for links
  generateShortCode() {
    return crypto.randomBytes(4).toString('base64url');
  }

  // Track affiliate click
  async trackClick(linkId, clickData) {
    const transaction = await database.transaction();
    
    try {
      // Get affiliate link
      const link = await database('affiliate_links')
        .where('id', linkId)
        .where('is_active', true)
        .first();

      if (!link) {
        throw new Error('Affiliate link not found or inactive');
      }

      // Record click
      const click = await database('affiliate_clicks')
        .insert({
          affiliate_id: link.affiliate_id,
          affiliate_link_id: link.id,
          ip_address: clickData.ip,
          user_agent: clickData.userAgent,
          referer: clickData.referer,
          accept_language: clickData.acceptLanguage,
          utm_source: clickData.utm_source,
          utm_medium: clickData.utm_medium,
          utm_campaign: clickData.utm_campaign,
          utm_content: clickData.utm_content,
          utm_term: clickData.utm_term,
          created_at: new Date()
        })
        .returning('*')
        .first();

      // Update link click count
      await database('affiliate_links')
        .where('id', link.id)
        .increment('total_clicks', 1)
        .update('updated_at', new Date());

      await transaction.commit();

      // Set cookie for attribution (30-day window)
      const attributionToken = this.generateAttributionToken(link.affiliate_id);
      
      return {
        clickId: click.id,
        targetUrl: link.target_url,
        attributionToken
      };
    } catch (error) {
      await transaction.rollback();
      logger.error('Failed to track affiliate click:', error);
      throw error;
    }
  }

  // Generate attribution token for tracking conversions
  generateAttributionToken(affiliateId) {
    const payload = {
      affiliateId,
      timestamp: Date.now()
    };
    
    return Buffer.from(JSON.stringify(payload)).toString('base64url');
  }

  // Track affiliate conversion
  async trackConversion(conversionData) {
    const transaction = await database.transaction();
    
    try {
      // Find affiliate by referral code
      const affiliate = await database('affiliates')
        .where('affiliate_code', conversionData.referralCode.toUpperCase())
        .where('status', 'active')
        .first();

      if (!affiliate) {
        return null; // No valid affiliate found
      }

      // Check for recent click (within 30 days)
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

      const recentClick = await database('affiliate_clicks')
        .where('affiliate_id', affiliate.id)
        .where('created_at', '>=', thirtyDaysAgo)
        .orderBy('created_at', 'desc')
        .first();

      // Calculate commission
      const commissionRate = affiliate.commission_rate;
      const commissionAmount = Math.round(conversionData.orderValue * commissionRate);

      // Record conversion
      const conversion = await database('affiliate_conversions')
        .insert({
          affiliate_id: affiliate.id,
          affiliate_click_id: recentClick?.id || null,
          customer_id: conversionData.customerId,
          order_id: conversionData.orderId,
          order_value: conversionData.orderValue,
          currency: conversionData.currency,
          product_type: conversionData.productType,
          commission_rate: commissionRate,
          commission_amount: commissionAmount,
          status: 'confirmed',
          created_at: new Date(),
          updated_at: new Date()
        })
        .returning('*')
        .first();

      // Update affiliate link stats if click exists
      if (recentClick?.affiliate_link_id) {
        await database('affiliate_links')
          .where('id', recentClick.affiliate_link_id)
          .increment({
            total_conversions: 1,
            total_earnings: commissionAmount
          })
          .update('updated_at', new Date());
      }

      // Update affiliate tier if needed
      await this.updateAffiliateTier(affiliate.id);

      await transaction.commit();

      logger.affiliate('Conversion tracked', {
        conversionId: conversion.id,
        affiliateId: affiliate.id,
        orderValue: conversionData.orderValue,
        commission: commissionAmount
      });

      return conversion;
    } catch (error) {
      await transaction.rollback();
      logger.error('Failed to track conversion:', error);
      throw error;
    }
  }

  // Update affiliate tier based on performance
  async updateAffiliateTier(affiliateId) {
    try {
      const stats = await database('affiliate_conversions')
        .where('affiliate_id', affiliateId)
        .where('created_at', '>=', new Date(Date.now() - 365 * 24 * 60 * 60 * 1000)) // Last year
        .select(
          database.raw('COUNT(*) as total_conversions'),
          database.raw('SUM(commission_amount) as total_earnings')
        )
        .first();

      const conversions = parseInt(stats.total_conversions) || 0;
      const earnings = parseInt(stats.total_earnings) || 0;

      let newTier = 'bronze';
      let newCommissionRate = 0.15;

      if (conversions >= 100 && earnings >= 10000) { // $100+ earnings, 100+ conversions
        newTier = 'platinum';
        newCommissionRate = 0.25; // 25%
      } else if (conversions >= 50 && earnings >= 5000) { // $50+ earnings, 50+ conversions
        newTier = 'gold';
        newCommissionRate = 0.20; // 20%
      } else if (conversions >= 20 && earnings >= 2000) { // $20+ earnings, 20+ conversions
        newTier = 'silver';
        newCommissionRate = 0.17; // 17%
      }

      await database('affiliates')
        .where('id', affiliateId)
        .update({
          tier_level: newTier,
          commission_rate: newCommissionRate,
          updated_at: new Date()
        });

      logger.affiliate('Affiliate tier updated', {
        affiliateId,
        newTier,
        newCommissionRate,
        conversions,
        earnings
      });
    } catch (error) {
      logger.error('Failed to update affiliate tier:', error);
      // Don't throw - this is a background task
    }
  }

  // Get affiliate links
  async getAffiliateLinks(affiliateId, page = 1, limit = 20, campaign = null) {
    try {
      let query = database('affiliate_links')
        .where('affiliate_id', affiliateId);

      if (campaign) {
        query = query.where('campaign', campaign);
      }

      const offset = (page - 1) * limit;

      const [links, [{ count }]] = await Promise.all([
        query
          .orderBy('created_at', 'desc')
          .limit(limit)
          .offset(offset)
          .select('*'),
        
        query.clone().count('* as count')
      ]);

      return {
        data: links,
        total: parseInt(count)
      };
    } catch (error) {
      logger.error('Failed to get affiliate links:', error);
      throw error;
    }
  }

  // Get affiliate stats with date range
  async getAffiliateStats(affiliateId, options = {}) {
    try {
      const { period, startDate, endDate } = options;
      
      let dateFilter = {};
      if (startDate && endDate) {
        dateFilter.start = startDate;
        dateFilter.end = endDate;
      } else if (period) {
        dateFilter = this.parsePeriod(period);
      } else {
        dateFilter = this.parsePeriod('30d');
      }

      const [clickStats, conversionStats, topLinks, productStats] = await Promise.all([
        this.getClickStats(affiliateId, dateFilter),
        this.getConversionStats(affiliateId, dateFilter),
        this.getTopPerformingLinks(affiliateId, 5, dateFilter),
        this.getConversionsByProduct(affiliateId, dateFilter)
      ]);

      const conversionRate = clickStats.total > 0 ? 
        (conversionStats.total / clickStats.total) * 100 : 0;

      return {
        period: dateFilter,
        clicks: clickStats.total,
        conversions: conversionStats.total,
        conversionRate: parseFloat(conversionRate.toFixed(2)),
        totalEarnings: conversionStats.earnings,
        pendingEarnings: conversionStats.pending,
        paidEarnings: conversionStats.paid,
        topLinks,
        conversionsByProduct: productStats,
        dailyStats: await this.getDailyStats(affiliateId, dateFilter)
      };
    } catch (error) {
      logger.error('Failed to get affiliate stats:', error);
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
    } else if (period === '1y') {
      start.setFullYear(start.getFullYear() - 1);
    }

    return { start, end, period };
  }

  // Get click statistics
  async getClickStats(affiliateId, dateFilter) {
    try {
      const result = await database('affiliate_clicks')
        .where('affiliate_id', affiliateId)
        .whereBetween('created_at', [dateFilter.start, dateFilter.end])
        .count('* as total')
        .first();

      return { total: parseInt(result.total) || 0 };
    } catch (error) {
      logger.error('Failed to get click stats:', error);
      throw error;
    }
  }

  // Get conversion statistics
  async getConversionStats(affiliateId, dateFilter) {
    try {
      const [totalResult, pendingResult, paidResult] = await Promise.all([
        database('affiliate_conversions')
          .where('affiliate_id', affiliateId)
          .whereBetween('created_at', [dateFilter.start, dateFilter.end])
          .count('* as total')
          .sum('commission_amount as earnings')
          .first(),
        
        database('affiliate_conversions')
          .where('affiliate_id', affiliateId)
          .whereBetween('created_at', [dateFilter.start, dateFilter.end])
          .where('status', 'pending')
          .sum('commission_amount as pending')
          .first(),
        
        // Get paid amount from payouts in this period
        database('affiliate_payouts')
          .where('affiliate_id', affiliateId)
          .whereBetween('processed_at', [dateFilter.start, dateFilter.end])
          .where('status', 'completed')
          .sum('amount as paid')
          .first()
      ]);

      return {
        total: parseInt(totalResult.total) || 0,
        earnings: parseInt(totalResult.earnings) || 0,
        pending: parseInt(pendingResult.pending) || 0,
        paid: parseInt(paidResult.paid) || 0
      };
    } catch (error) {
      logger.error('Failed to get conversion stats:', error);
      throw error;
    }
  }

  // Request payout
  async requestPayout(affiliateId, payoutData) {
    try {
      // Check minimum payout amount
      const minPayout = 5000; // $50 minimum
      if (payoutData.amount < minPayout) {
        throw new Error(`Minimum payout amount is $${minPayout / 100}`);
      }

      // Check available balance
      const earnings = await this.getAffiliateEarnings(affiliateId);
      if (payoutData.amount > earnings.available) {
        throw new Error('Insufficient balance for payout request');
      }

      const payout = await database('affiliate_payouts')
        .insert({
          affiliate_id: affiliateId,
          amount: payoutData.amount,
          payment_method: payoutData.method,
          status: 'requested',
          notes: payoutData.notes,
          created_at: new Date(),
          updated_at: new Date()
        })
        .returning('*')
        .first();

      return payout;
    } catch (error) {
      logger.error('Failed to request payout:', error);
      throw error;
    }
  }

  // Get payout history
  async getPayoutHistory(affiliateId, page = 1, limit = 10, status = null) {
    try {
      let query = database('affiliate_payouts')
        .where('affiliate_id', affiliateId);

      if (status) {
        query = query.where('status', status);
      }

      const offset = (page - 1) * limit;

      const [payouts, [{ count }]] = await Promise.all([
        query
          .orderBy('created_at', 'desc')
          .limit(limit)
          .offset(offset)
          .select('*'),
        
        query.clone().count('* as count')
      ]);

      return {
        data: payouts,
        total: parseInt(count)
      };
    } catch (error) {
      logger.error('Failed to get payout history:', error);
      throw error;
    }
  }

  // Update affiliate profile
  async updateAffiliateProfile(affiliateId, profileData) {
    try {
      const updated = await database('affiliates')
        .where('id', affiliateId)
        .update({
          website: profileData.website,
          social_media: profileData.socialMedia ? JSON.stringify(profileData.socialMedia) : null,
          audience: profileData.audience,
          promotion_method: profileData.promotionMethod,
          payment_method: profileData.paymentMethod,
          tax_id: profileData.taxId,
          updated_at: new Date()
        })
        .returning('*')
        .first();

      return updated;
    } catch (error) {
      logger.error('Failed to update affiliate profile:', error);
      throw error;
    }
  }

  // Get marketing materials
  async getMarketingMaterials(tierLevel) {
    try {
      // Return different materials based on tier level
      const baseMaterials = {
        banners: [
          {
            size: '728x90',
            url: '/materials/banner-728x90.png',
            type: 'leaderboard'
          },
          {
            size: '300x250',
            url: '/materials/banner-300x250.png',
            type: 'rectangle'
          }
        ],
        textAds: [
          {
            title: 'Try ActiveLog Free',
            description: 'The complete project management solution.',
            cta: 'Start Free Trial'
          }
        ],
        emailTemplates: [
          {
            subject: 'Boost Your Productivity with ActiveLog',
            template: 'email-template-1.html'
          }
        ],
        socialMediaPosts: [
          {
            platform: 'twitter',
            text: 'Just discovered @ActiveLog - game changer for project management! 🚀',
            hashtags: ['productivity', 'projectmanagement']
          }
        ],
        productInfo: {
          features: ['Project Tracking', 'Team Collaboration', 'Analytics'],
          pricing: 'Starting at $29/month',
          benefits: ['Increase productivity by 40%', 'Save 10+ hours per week']
        },
        guidelines: {
          brandColors: ['#007bff', '#28a745', '#ffc107'],
          logoUsage: 'Always use the official ActiveLog logo',
          messaging: 'Focus on productivity and time-saving benefits'
        }
      };

      // Add premium materials for higher tiers
      if (['gold', 'platinum'].includes(tierLevel)) {
        baseMaterials.premiumBanners = [
          {
            size: '320x50',
            url: '/materials/premium-banner-320x50.png',
            type: 'mobile'
          }
        ];
        baseMaterials.videoMaterials = [
          {
            title: 'Product Demo Video',
            url: '/materials/demo-video.mp4',
            duration: '2:30'
          }
        ];
      }

      return baseMaterials;
    } catch (error) {
      logger.error('Failed to get marketing materials:', error);
      throw error;
    }
  }

  // Helper methods for statistics
  async getRecentReferrals(affiliateId, limit = 5) {
    try {
      return await database('affiliate_conversions')
        .where('affiliate_id', affiliateId)
        .orderBy('created_at', 'desc')
        .limit(limit)
        .select('*');
    } catch (error) {
      logger.error('Failed to get recent referrals:', error);
      return [];
    }
  }

  async getTopPerformingLinks(affiliateId, limit = 5, dateFilter = null) {
    try {
      let query = database('affiliate_links')
        .where('affiliate_id', affiliateId);

      if (dateFilter) {
        query = query.whereBetween('created_at', [dateFilter.start, dateFilter.end]);
      }

      return await query
        .orderBy('total_conversions', 'desc')
        .limit(limit)
        .select('*');
    } catch (error) {
      logger.error('Failed to get top performing links:', error);
      return [];
    }
  }

  async getConversionsByProduct(affiliateId, dateFilter) {
    try {
      return await database('affiliate_conversions')
        .where('affiliate_id', affiliateId)
        .whereBetween('created_at', [dateFilter.start, dateFilter.end])
        .groupBy('product_type')
        .select('product_type')
        .count('* as conversions')
        .sum('commission_amount as earnings');
    } catch (error) {
      logger.error('Failed to get conversions by product:', error);
      return [];
    }
  }

  async getDailyStats(affiliateId, dateFilter) {
    try {
      const [clicks, conversions] = await Promise.all([
        database('affiliate_clicks')
          .where('affiliate_id', affiliateId)
          .whereBetween('created_at', [dateFilter.start, dateFilter.end])
          .select(database.raw('DATE(created_at) as date'))
          .count('* as clicks')
          .groupBy(database.raw('DATE(created_at)'))
          .orderBy('date'),
        
        database('affiliate_conversions')
          .where('affiliate_id', affiliateId)
          .whereBetween('created_at', [dateFilter.start, dateFilter.end])
          .select(database.raw('DATE(created_at) as date'))
          .count('* as conversions')
          .sum('commission_amount as earnings')
          .groupBy(database.raw('DATE(created_at)'))
          .orderBy('date')
      ]);

      // Merge clicks and conversions data
      const dailyStats = {};
      
      clicks.forEach(day => {
        dailyStats[day.date] = { clicks: parseInt(day.clicks), conversions: 0, earnings: 0 };
      });
      
      conversions.forEach(day => {
        if (dailyStats[day.date]) {
          dailyStats[day.date].conversions = parseInt(day.conversions);
          dailyStats[day.date].earnings = parseInt(day.earnings);
        } else {
          dailyStats[day.date] = { clicks: 0, conversions: parseInt(day.conversions), earnings: parseInt(day.earnings) };
        }
      });

      return Object.entries(dailyStats).map(([date, stats]) => ({
        date,
        ...stats
      }));
    } catch (error) {
      logger.error('Failed to get daily stats:', error);
      return [];
    }
  }
}

module.exports = AffiliateService;