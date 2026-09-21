const express = require('express');
const AffiliateService = require('../services/AffiliateService');
const { authMiddleware } = require('../middleware/auth');
const logger = require('../utils/logger');

const router = express.Router();
const affiliateService = new AffiliateService();

// Register as affiliate (no auth required for public registration)
router.post('/register', async (req, res) => {
  try {
    const { 
      name, 
      email, 
      website, 
      socialMedia, 
      audience, 
      promotionMethod,
      taxId,
      paymentMethod = 'stripe'
    } = req.body;

    if (!name || !email) {
      return res.status(400).json({
        error: 'Name and email are required'
      });
    }

    const affiliate = await affiliateService.registerAffiliate({
      name,
      email,
      website,
      socialMedia,
      audience,
      promotionMethod,
      taxId,
      paymentMethod
    });

    logger.affiliate('New affiliate registered', {
      affiliateId: affiliate.id,
      email,
      name
    });

    res.status(201).json({
      success: true,
      affiliate: {
        id: affiliate.id,
        affiliateCode: affiliate.affiliate_code,
        status: affiliate.status,
        email: affiliate.email
      },
      message: 'Affiliate registration submitted for approval'
    });
  } catch (error) {
    logger.error('Failed to register affiliate:', error);
    res.status(500).json({
      error: 'Failed to register affiliate',
      message: error.message
    });
  }
});

// Get affiliate dashboard data (requires affiliate auth)
router.get('/dashboard', authMiddleware, async (req, res) => {
  try {
    const affiliate = await affiliateService.getAffiliateByUserId(req.user.id);
    
    if (!affiliate) {
      return res.status(404).json({
        error: 'Affiliate account not found'
      });
    }

    const dashboard = await affiliateService.getAffiliateDashboard(affiliate.id);

    res.json({
      success: true,
      dashboard: {
        affiliate: {
          id: affiliate.id,
          code: affiliate.affiliate_code,
          status: affiliate.status,
          commissionRate: affiliate.commission_rate,
          tierLevel: affiliate.tier_level
        },
        stats: dashboard.stats,
        earnings: dashboard.earnings,
        referrals: dashboard.referrals,
        links: dashboard.links
      }
    });
  } catch (error) {
    logger.error('Failed to get affiliate dashboard:', error);
    res.status(500).json({
      error: 'Failed to get dashboard data',
      message: error.message
    });
  }
});

// Generate affiliate link
router.post('/links', authMiddleware, async (req, res) => {
  try {
    const { 
      targetUrl, 
      campaign = 'default',
      medium = 'affiliate',
      content = null
    } = req.body;

    if (!targetUrl) {
      return res.status(400).json({
        error: 'Target URL is required'
      });
    }

    const affiliate = await affiliateService.getAffiliateByUserId(req.user.id);
    
    if (!affiliate) {
      return res.status(404).json({
        error: 'Affiliate account not found'
      });
    }

    const link = await affiliateService.generateAffiliateLink(affiliate.id, {
      targetUrl,
      campaign,
      medium,
      content
    });

    logger.affiliate('Affiliate link generated', {
      affiliateId: affiliate.id,
      linkId: link.id,
      targetUrl,
      campaign
    });

    res.status(201).json({
      success: true,
      link: {
        id: link.id,
        url: link.affiliate_url,
        shortUrl: link.short_url,
        targetUrl: link.target_url,
        campaign: link.campaign,
        medium: link.medium,
        content: link.content,
        createdAt: link.created_at
      }
    });
  } catch (error) {
    logger.error('Failed to generate affiliate link:', error);
    res.status(500).json({
      error: 'Failed to generate affiliate link',
      message: error.message
    });
  }
});

// Get affiliate links
router.get('/links', authMiddleware, async (req, res) => {
  try {
    const { page = 1, limit = 20, campaign } = req.query;
    
    const affiliate = await affiliateService.getAffiliateByUserId(req.user.id);
    
    if (!affiliate) {
      return res.status(404).json({
        error: 'Affiliate account not found'
      });
    }

    const links = await affiliateService.getAffiliateLinks(
      affiliate.id,
      parseInt(page),
      parseInt(limit),
      campaign
    );

    res.json({
      success: true,
      links: links.data.map(link => ({
        id: link.id,
        url: link.affiliate_url,
        shortUrl: link.short_url,
        targetUrl: link.target_url,
        campaign: link.campaign,
        medium: link.medium,
        content: link.content,
        clicks: link.total_clicks,
        conversions: link.total_conversions,
        earnings: link.total_earnings,
        createdAt: link.created_at
      })),
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: links.total,
        pages: Math.ceil(links.total / parseInt(limit))
      }
    });
  } catch (error) {
    logger.error('Failed to get affiliate links:', error);
    res.status(500).json({
      error: 'Failed to get affiliate links',
      message: error.message
    });
  }
});

// Track click (public endpoint)
router.get('/click/:linkId', async (req, res) => {
  try {
    const { linkId } = req.params;
    const { 
      ref, 
      utm_source, 
      utm_medium, 
      utm_campaign,
      utm_content,
      utm_term
    } = req.query;

    const clientInfo = {
      ip: req.ip || req.connection.remoteAddress,
      userAgent: req.get('User-Agent'),
      referer: req.get('Referer'),
      acceptLanguage: req.get('Accept-Language')
    };

    const clickData = await affiliateService.trackClick(linkId, {
      ...clientInfo,
      ref,
      utm_source,
      utm_medium,
      utm_campaign,
      utm_content,
      utm_term
    });

    logger.affiliate('Affiliate click tracked', {
      linkId,
      clickId: clickData.clickId,
      ip: clientInfo.ip,
      referer: clientInfo.referer
    });

    // Redirect to target URL
    res.redirect(302, clickData.targetUrl);
  } catch (error) {
    logger.error('Failed to track affiliate click:', error);
    // Still redirect even if tracking fails
    res.redirect(302, process.env.DEFAULT_REDIRECT_URL || 'https://activelog.com');
  }
});

// Track conversion (requires auth for the user making the purchase)
router.post('/conversion', authMiddleware, async (req, res) => {
  try {
    const {
      referralCode,
      orderId,
      orderValue,
      currency = 'usd',
      productType = 'subscription'
    } = req.body;

    if (!referralCode || !orderId || !orderValue) {
      return res.status(400).json({
        error: 'Referral code, order ID, and order value are required'
      });
    }

    const conversion = await affiliateService.trackConversion({
      referralCode,
      customerId: req.user.id,
      orderId,
      orderValue,
      currency,
      productType
    });

    if (conversion) {
      logger.affiliate('Conversion tracked', {
        conversionId: conversion.id,
        affiliateId: conversion.affiliate_id,
        customerId: req.user.id,
        orderValue,
        commission: conversion.commission_amount
      });

      res.json({
        success: true,
        conversion: {
          id: conversion.id,
          commissionAmount: conversion.commission_amount,
          commissionRate: conversion.commission_rate
        }
      });
    } else {
      res.json({
        success: false,
        message: 'No valid referral found'
      });
    }
  } catch (error) {
    logger.error('Failed to track conversion:', error);
    res.status(500).json({
      error: 'Failed to track conversion',
      message: error.message
    });
  }
});

// Get referral statistics
router.get('/stats', authMiddleware, async (req, res) => {
  try {
    const { 
      period = '30d',
      startDate,
      endDate
    } = req.query;

    const affiliate = await affiliateService.getAffiliateByUserId(req.user.id);
    
    if (!affiliate) {
      return res.status(404).json({
        error: 'Affiliate account not found'
      });
    }

    const stats = await affiliateService.getAffiliateStats(affiliate.id, {
      period,
      startDate: startDate ? new Date(startDate) : null,
      endDate: endDate ? new Date(endDate) : null
    });

    res.json({
      success: true,
      stats: {
        period: stats.period,
        clicks: stats.clicks,
        conversions: stats.conversions,
        conversionRate: stats.conversionRate,
        earnings: {
          total: stats.totalEarnings,
          pending: stats.pendingEarnings,
          paid: stats.paidEarnings
        },
        topPerformingLinks: stats.topLinks,
        conversionsByProduct: stats.conversionsByProduct,
        dailyStats: stats.dailyStats
      }
    });
  } catch (error) {
    logger.error('Failed to get affiliate stats:', error);
    res.status(500).json({
      error: 'Failed to get affiliate stats',
      message: error.message
    });
  }
});

// Request payout
router.post('/payout', authMiddleware, async (req, res) => {
  try {
    const { 
      amount,
      method = 'stripe',
      notes = null
    } = req.body;

    const affiliate = await affiliateService.getAffiliateByUserId(req.user.id);
    
    if (!affiliate) {
      return res.status(404).json({
        error: 'Affiliate account not found'
      });
    }

    const payout = await affiliateService.requestPayout(affiliate.id, {
      amount,
      method,
      notes
    });

    logger.affiliate('Payout requested', {
      affiliateId: affiliate.id,
      payoutId: payout.id,
      amount,
      method
    });

    res.json({
      success: true,
      payout: {
        id: payout.id,
        amount: payout.amount,
        method: payout.payment_method,
        status: payout.status,
        requestedAt: payout.created_at
      },
      message: 'Payout request submitted successfully'
    });
  } catch (error) {
    logger.error('Failed to request payout:', error);
    res.status(500).json({
      error: 'Failed to request payout',
      message: error.message
    });
  }
});

// Get payout history
router.get('/payouts', authMiddleware, async (req, res) => {
  try {
    const { page = 1, limit = 10, status } = req.query;
    
    const affiliate = await affiliateService.getAffiliateByUserId(req.user.id);
    
    if (!affiliate) {
      return res.status(404).json({
        error: 'Affiliate account not found'
      });
    }

    const payouts = await affiliateService.getPayoutHistory(
      affiliate.id,
      parseInt(page),
      parseInt(limit),
      status
    );

    res.json({
      success: true,
      payouts: payouts.data.map(payout => ({
        id: payout.id,
        amount: payout.amount,
        method: payout.payment_method,
        status: payout.status,
        requestedAt: payout.created_at,
        processedAt: payout.processed_at,
        notes: payout.notes
      })),
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: payouts.total,
        pages: Math.ceil(payouts.total / parseInt(limit))
      }
    });
  } catch (error) {
    logger.error('Failed to get payout history:', error);
    res.status(500).json({
      error: 'Failed to get payout history',
      message: error.message
    });
  }
});

// Update affiliate profile
router.put('/profile', authMiddleware, async (req, res) => {
  try {
    const {
      website,
      socialMedia,
      audience,
      promotionMethod,
      paymentMethod,
      taxId
    } = req.body;

    const affiliate = await affiliateService.getAffiliateByUserId(req.user.id);
    
    if (!affiliate) {
      return res.status(404).json({
        error: 'Affiliate account not found'
      });
    }

    const updated = await affiliateService.updateAffiliateProfile(affiliate.id, {
      website,
      socialMedia,
      audience,
      promotionMethod,
      paymentMethod,
      taxId
    });

    logger.affiliate('Affiliate profile updated', {
      affiliateId: affiliate.id,
      changes: Object.keys(req.body)
    });

    res.json({
      success: true,
      affiliate: {
        id: updated.id,
        website: updated.website,
        socialMedia: updated.social_media,
        audience: updated.audience,
        promotionMethod: updated.promotion_method,
        paymentMethod: updated.payment_method
      },
      message: 'Profile updated successfully'
    });
  } catch (error) {
    logger.error('Failed to update affiliate profile:', error);
    res.status(500).json({
      error: 'Failed to update affiliate profile',
      message: error.message
    });
  }
});

// Get affiliate marketing materials
router.get('/materials', authMiddleware, async (req, res) => {
  try {
    const affiliate = await affiliateService.getAffiliateByUserId(req.user.id);
    
    if (!affiliate) {
      return res.status(404).json({
        error: 'Affiliate account not found'
      });
    }

    const materials = await affiliateService.getMarketingMaterials(affiliate.tier_level);

    res.json({
      success: true,
      materials: {
        banners: materials.banners,
        textAds: materials.textAds,
        emailTemplates: materials.emailTemplates,
        socialMediaPosts: materials.socialMediaPosts,
        productInfo: materials.productInfo,
        guidelines: materials.guidelines
      }
    });
  } catch (error) {
    logger.error('Failed to get marketing materials:', error);
    res.status(500).json({
      error: 'Failed to get marketing materials',
      message: error.message
    });
  }
});

// Public endpoint to get affiliate info by code (for referral validation)
router.get('/info/:affiliateCode', async (req, res) => {
  try {
    const { affiliateCode } = req.params;
    
    const affiliate = await affiliateService.getAffiliateByCode(affiliateCode);
    
    if (!affiliate || affiliate.status !== 'active') {
      return res.status(404).json({
        error: 'Affiliate not found or inactive'
      });
    }

    res.json({
      success: true,
      affiliate: {
        code: affiliate.affiliate_code,
        name: affiliate.name,
        isActive: affiliate.status === 'active'
      }
    });
  } catch (error) {
    logger.error('Failed to get affiliate info:', error);
    res.status(500).json({
      error: 'Failed to get affiliate info',
      message: error.message
    });
  }
});

module.exports = router;