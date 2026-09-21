const express = require('express');
const AdSenseService = require('../services/AdSenseService');
const { subscriptionMiddleware } = require('../middleware/auth');
const logger = require('../utils/logger');

const router = express.Router();
const adsenseService = new AdSenseService();

// Get ad configuration for user's subscription tier
router.get('/config', async (req, res) => {
  try {
    const subscription = await adsenseService.getUserSubscription(req.user.id);
    const plan = subscription?.plan || 'free';
    
    const adConfig = adsenseService.getAdConfigForPlan(plan);
    
    res.json({
      success: true,
      plan,
      adConfig: {
        enabled: adConfig.enabled,
        adUnits: adConfig.adUnits,
        frequency: adConfig.frequency,
        placements: adConfig.placements
      }
    });
  } catch (error) {
    logger.error('Failed to get ad config:', error);
    res.status(500).json({
      error: 'Failed to get ad configuration',
      message: error.message
    });
  }
});

// Get available ad units
router.get('/units', async (req, res) => {
  try {
    const subscription = await adsenseService.getUserSubscription(req.user.id);
    const plan = subscription?.plan || 'free';
    
    if (plan !== 'free') {
      return res.json({
        success: true,
        adUnits: [],
        message: 'Ads are disabled for paid plans'
      });
    }

    const adUnits = adsenseService.getAvailableAdUnits();
    
    res.json({
      success: true,
      adUnits
    });
  } catch (error) {
    logger.error('Failed to get ad units:', error);
    res.status(500).json({
      error: 'Failed to get ad units',
      message: error.message
    });
  }
});

// Track ad impression
router.post('/impression', async (req, res) => {
  try {
    const { 
      adUnitId, 
      placement, 
      pageUrl,
      referrer,
      deviceType = 'desktop'
    } = req.body;

    if (!adUnitId || !placement) {
      return res.status(400).json({
        error: 'Ad unit ID and placement are required'
      });
    }

    const impression = await adsenseService.trackImpression(req.user.id, {
      adUnitId,
      placement,
      pageUrl,
      referrer,
      deviceType,
      userAgent: req.get('User-Agent'),
      ip: req.ip
    });

    logger.info('Ad impression tracked', {
      userId: req.user.id,
      adUnitId,
      placement,
      impressionId: impression.id
    });

    res.json({
      success: true,
      impressionId: impression.id
    });
  } catch (error) {
    logger.error('Failed to track ad impression:', error);
    res.status(500).json({
      error: 'Failed to track impression',
      message: error.message
    });
  }
});

// Track ad click
router.post('/click', async (req, res) => {
  try {
    const { 
      impressionId,
      adUnitId,
      clickUrl,
      placement
    } = req.body;

    if (!impressionId && !adUnitId) {
      return res.status(400).json({
        error: 'Either impression ID or ad unit ID is required'
      });
    }

    const click = await adsenseService.trackClick(req.user.id, {
      impressionId,
      adUnitId,
      clickUrl,
      placement,
      userAgent: req.get('User-Agent'),
      ip: req.ip
    });

    logger.info('Ad click tracked', {
      userId: req.user.id,
      impressionId,
      adUnitId,
      clickId: click.id
    });

    res.json({
      success: true,
      clickId: click.id
    });
  } catch (error) {
    logger.error('Failed to track ad click:', error);
    res.status(500).json({
      error: 'Failed to track click',
      message: error.message
    });
  }
});

// Get ad performance statistics (admin only)
router.get('/stats', subscriptionMiddleware('pro'), async (req, res) => {
  try {
    const { 
      period = '30d',
      startDate,
      endDate,
      adUnitId,
      placement
    } = req.query;

    const stats = await adsenseService.getAdStats(req.user.id, {
      period,
      startDate: startDate ? new Date(startDate) : null,
      endDate: endDate ? new Date(endDate) : null,
      adUnitId,
      placement
    });

    res.json({
      success: true,
      stats: {
        period: stats.period,
        impressions: stats.impressions,
        clicks: stats.clicks,
        ctr: stats.ctr,
        revenue: stats.revenue,
        rpm: stats.rpm,
        topPerformingUnits: stats.topPerformingUnits,
        performanceByPlacement: stats.performanceByPlacement,
        dailyStats: stats.dailyStats
      }
    });
  } catch (error) {
    logger.error('Failed to get ad stats:', error);
    res.status(500).json({
      error: 'Failed to get ad statistics',
      message: error.message
    });
  }
});

// Configure ad settings for user
router.post('/settings', async (req, res) => {
  try {
    const { 
      personalizedAds = true,
      adFrequency = 'normal',
      blockedCategories = []
    } = req.body;

    const settings = await adsenseService.updateAdSettings(req.user.id, {
      personalizedAds,
      adFrequency,
      blockedCategories
    });

    logger.info('Ad settings updated', {
      userId: req.user.id,
      personalizedAds,
      adFrequency,
      blockedCategories: blockedCategories.length
    });

    res.json({
      success: true,
      settings,
      message: 'Ad settings updated successfully'
    });
  } catch (error) {
    logger.error('Failed to update ad settings:', error);
    res.status(500).json({
      error: 'Failed to update ad settings',
      message: error.message
    });
  }
});

// Get user's ad settings
router.get('/settings', async (req, res) => {
  try {
    const settings = await adsenseService.getAdSettings(req.user.id);
    
    res.json({
      success: true,
      settings: {
        personalizedAds: settings.personalized_ads,
        adFrequency: settings.ad_frequency,
        blockedCategories: settings.blocked_categories || []
      }
    });
  } catch (error) {
    logger.error('Failed to get ad settings:', error);
    res.status(500).json({
      error: 'Failed to get ad settings',
      message: error.message
    });
  }
});

// Report inappropriate ad
router.post('/report', async (req, res) => {
  try {
    const {
      adUnitId,
      impressionId,
      reason,
      description,
      adContent
    } = req.body;

    if (!reason) {
      return res.status(400).json({
        error: 'Reason is required for reporting ads'
      });
    }

    const report = await adsenseService.reportAd(req.user.id, {
      adUnitId,
      impressionId,
      reason,
      description,
      adContent,
      userAgent: req.get('User-Agent'),
      ip: req.ip
    });

    logger.info('Ad reported', {
      userId: req.user.id,
      reportId: report.id,
      adUnitId,
      reason
    });

    res.json({
      success: true,
      reportId: report.id,
      message: 'Ad report submitted successfully'
    });
  } catch (error) {
    logger.error('Failed to report ad:', error);
    res.status(500).json({
      error: 'Failed to report ad',
      message: error.message
    });
  }
});

// Get ad revenue sharing info (for transparency)
router.get('/revenue-sharing', async (req, res) => {
  try {
    const subscription = await adsenseService.getUserSubscription(req.user.id);
    const plan = subscription?.plan || 'free';
    
    if (plan !== 'free') {
      return res.json({
        success: true,
        revenueSharing: null,
        message: 'Revenue sharing only applies to free plan users'
      });
    }

    const revenueInfo = adsenseService.getRevenueShareInfo();
    
    res.json({
      success: true,
      revenueSharing: {
        userShare: revenueInfo.userShare,
        platformShare: revenueInfo.platformShare,
        description: revenueInfo.description,
        minimumPayout: revenueInfo.minimumPayout
      }
    });
  } catch (error) {
    logger.error('Failed to get revenue sharing info:', error);
    res.status(500).json({
      error: 'Failed to get revenue sharing information',
      message: error.message
    });
  }
});

// Get user's ad earnings (if revenue sharing is enabled)
router.get('/earnings', async (req, res) => {
  try {
    const subscription = await adsenseService.getUserSubscription(req.user.id);
    const plan = subscription?.plan || 'free';
    
    if (plan !== 'free') {
      return res.json({
        success: true,
        earnings: null,
        message: 'Ad earnings only apply to free plan users'
      });
    }

    const earnings = await adsenseService.getUserAdEarnings(req.user.id);
    
    res.json({
      success: true,
      earnings: {
        total: earnings.total,
        thisMonth: earnings.thisMonth,
        lastMonth: earnings.lastMonth,
        pending: earnings.pending,
        paid: earnings.paid,
        nextPayoutDate: earnings.nextPayoutDate,
        minimumPayout: earnings.minimumPayout
      }
    });
  } catch (error) {
    logger.error('Failed to get ad earnings:', error);
    res.status(500).json({
      error: 'Failed to get ad earnings',
      message: error.message
    });
  }
});

module.exports = router;