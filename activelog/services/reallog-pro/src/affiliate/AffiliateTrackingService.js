import logger from '../lib/logger.js';
import config from '../config/config.js';

class AffiliateTrackingService {
  constructor(redis) {
    this.redis = redis;
    this.affiliateLinks = new Map();
    this.campaigns = new Map();
    this.clicks = new Map();
    this.conversions = new Map();
    this.commissions = new Map();
    this.analytics = {
      totalClicks: 0,
      totalConversions: 0,
      totalCommissions: 0,
      conversionRate: 0,
      averageCommission: 0
    };
  }

  async initialize() {
    try {
      await this.loadAffiliateCampaigns();
      this.startClickTracking();
      this.startConversionTracking();
      
      logger.info('Affiliate Tracking Service initialized');
    } catch (error) {
      logger.error('Failed to initialize Affiliate Tracking Service:', error);
      throw error;
    }
  }

  async loadAffiliateCampaigns() {
    // Load default affiliate campaigns
    this.campaigns.set('amazon_associates', {
      name: 'Amazon Associates',
      baseUrl: 'https://amzn.to/',
      commission: 0.04,
      type: 'product',
      enabled: true
    });

    this.campaigns.set('course_affiliate', {
      name: 'Online Courses',
      baseUrl: 'https://learn.example.com/',
      commission: 0.30,
      type: 'digital',
      enabled: true
    });
  }

  startClickTracking() {
    logger.info('Click tracking started');
  }

  startConversionTracking() {
    logger.info('Conversion tracking started');
  }

  async createAffiliateLink(linkData) {
    try {
      const linkId = `aff_${Date.now()}`;
      const affiliateLink = {
        id: linkId,
        originalUrl: linkData.originalUrl,
        campaign: linkData.campaign,
        product: linkData.product || '',
        customTag: linkData.customTag || '',
        createdAt: new Date(),
        clicks: 0,
        conversions: 0,
        revenue: 0,
        status: 'active'
      };

      this.affiliateLinks.set(linkId, affiliateLink);
      
      await this.redis.set(
        `affiliate_link:${linkId}`,
        JSON.stringify(affiliateLink),
        'EX',
        60 * 60 * 24 * 365 // 1 year
      );

      logger.info(`Affiliate link created: ${linkId}`);
      return { linkId, link: affiliateLink };
    } catch (error) {
      logger.error('Failed to create affiliate link:', error);
      throw error;
    }
  }

  async trackClick(linkId, clickData = {}) {
    try {
      const clickId = `click_${Date.now()}`;
      const click = {
        id: clickId,
        linkId,
        timestamp: new Date(),
        userAgent: clickData.userAgent || '',
        referrer: clickData.referrer || '',
        ipAddress: clickData.ipAddress || '',
        platform: clickData.platform || 'web',
        location: clickData.location || {}
      };

      this.clicks.set(clickId, click);
      this.analytics.totalClicks++;

      // Update link click count
      const link = this.affiliateLinks.get(linkId);
      if (link) {
        link.clicks++;
        this.affiliateLinks.set(linkId, link);
      }

      await this.redis.set(
        `affiliate_click:${clickId}`,
        JSON.stringify(click),
        'EX',
        60 * 60 * 24 * 90 // 90 days
      );

      logger.info(`Click tracked: ${linkId}`);
      return click;
    } catch (error) {
      logger.error('Failed to track click:', error);
      throw error;
    }
  }

  async trackConversion(linkId, conversionData) {
    try {
      const conversionId = `conv_${Date.now()}`;
      const conversion = {
        id: conversionId,
        linkId,
        timestamp: new Date(),
        amount: conversionData.amount || 0,
        currency: conversionData.currency || 'USD',
        commission: conversionData.commission || 0,
        orderId: conversionData.orderId || '',
        productId: conversionData.productId || '',
        status: 'pending'
      };

      this.conversions.set(conversionId, conversion);
      this.analytics.totalConversions++;
      this.analytics.totalCommissions += conversion.commission;

      // Update link conversion count
      const link = this.affiliateLinks.get(linkId);
      if (link) {
        link.conversions++;
        link.revenue += conversion.amount;
        this.affiliateLinks.set(linkId, link);
      }

      // Calculate conversion rate
      if (this.analytics.totalClicks > 0) {
        this.analytics.conversionRate = 
          (this.analytics.totalConversions / this.analytics.totalClicks) * 100;
      }

      await this.redis.set(
        `affiliate_conversion:${conversionId}`,
        JSON.stringify(conversion),
        'EX',
        60 * 60 * 24 * 365 // 1 year
      );

      logger.info(`Conversion tracked: ${linkId}`, { amount: conversion.amount });
      return conversion;
    } catch (error) {
      logger.error('Failed to track conversion:', error);
      throw error;
    }
  }

  async getAffiliateLinks() {
    return Array.from(this.affiliateLinks.values());
  }

  async getLinkPerformance(linkId) {
    const link = this.affiliateLinks.get(linkId);
    if (!link) {
      throw new Error('Affiliate link not found');
    }

    const performance = {
      ...link,
      conversionRate: link.clicks > 0 ? (link.conversions / link.clicks) * 100 : 0,
      averageOrderValue: link.conversions > 0 ? link.revenue / link.conversions : 0,
      totalCommission: link.revenue * (this.campaigns.get(link.campaign)?.commission || 0)
    };

    return performance;
  }

  async getAnalytics() {
    return {
      ...this.analytics,
      totalLinks: this.affiliateLinks.size,
      totalCampaigns: this.campaigns.size,
      averageCommission: this.analytics.totalConversions > 0 
        ? this.analytics.totalCommissions / this.analytics.totalConversions 
        : 0
    };
  }

  setSocketIO(io) {
    this.io = io;
  }

  async shutdown() {
    logger.info('Affiliate Tracking Service shutting down');
  }
}

export default AffiliateTrackingService;