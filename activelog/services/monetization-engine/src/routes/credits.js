const express = require('express');
const CreditsService = require('../services/CreditsService');
const logger = require('../utils/logger');

const router = express.Router();
const creditsService = new CreditsService();

// Get user's credit balance and usage
router.get('/balance', async (req, res) => {
  try {
    const balance = await creditsService.getUserCreditBalance(req.user.id);
    
    res.json({
      success: true,
      balance: {
        available: balance.available,
        used: balance.used,
        total: balance.total,
        lastUpdated: balance.lastUpdated,
        expiresAt: balance.expiresAt
      }
    });
  } catch (error) {
    logger.error('Failed to get credit balance:', error);
    res.status(500).json({
      error: 'Failed to get credit balance',
      message: error.message
    });
  }
});

// Get credit usage history
router.get('/usage', async (req, res) => {
  try {
    const { page = 1, limit = 20, type, startDate, endDate } = req.query;
    
    const usage = await creditsService.getCreditUsageHistory(req.user.id, {
      page: parseInt(page),
      limit: parseInt(limit),
      type,
      startDate: startDate ? new Date(startDate) : null,
      endDate: endDate ? new Date(endDate) : null
    });
    
    res.json({
      success: true,
      usage: usage.data.map(transaction => ({
        id: transaction.id,
        type: transaction.transaction_type,
        credits: transaction.credits,
        description: transaction.description,
        service: transaction.service_name,
        timestamp: transaction.created_at,
        metadata: transaction.metadata
      })),
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: usage.total,
        pages: Math.ceil(usage.total / parseInt(limit))
      }
    });
  } catch (error) {
    logger.error('Failed to get credit usage history:', error);
    res.status(500).json({
      error: 'Failed to get credit usage history',
      message: error.message
    });
  }
});

// Spend credits for a service
router.post('/spend', async (req, res) => {
  try {
    const { 
      credits, 
      serviceName, 
      description, 
      metadata = {},
      operationId 
    } = req.body;
    
    if (!credits || credits <= 0) {
      return res.status(400).json({
        error: 'Credits amount must be greater than 0'
      });
    }
    
    if (!serviceName || !description) {
      return res.status(400).json({
        error: 'Service name and description are required'
      });
    }
    
    const transaction = await creditsService.spendCredits(req.user.id, {
      credits,
      serviceName,
      description,
      metadata,
      operationId
    });
    
    logger.info('Credits spent', {
      userId: req.user.id,
      credits,
      serviceName,
      transactionId: transaction.id,
      operationId
    });
    
    res.json({
      success: true,
      transaction: {
        id: transaction.id,
        credits: transaction.credits,
        remainingBalance: transaction.remaining_balance,
        timestamp: transaction.created_at
      }
    });
  } catch (error) {
    logger.error('Failed to spend credits:', error);
    res.status(500).json({
      error: 'Failed to spend credits',
      message: error.message
    });
  }
});

// Add credits (admin or system operation)
router.post('/add', async (req, res) => {
  try {
    const { 
      credits, 
      reason, 
      description = null,
      expiresAt = null,
      metadata = {}
    } = req.body;
    
    if (!credits || credits <= 0) {
      return res.status(400).json({
        error: 'Credits amount must be greater than 0'
      });
    }
    
    if (!reason) {
      return res.status(400).json({
        error: 'Reason for adding credits is required'
      });
    }
    
    const transaction = await creditsService.addCredits(req.user.id, {
      credits,
      reason,
      description,
      expiresAt: expiresAt ? new Date(expiresAt) : null,
      metadata
    });
    
    logger.audit('Credits added', {
      userId: req.user.id,
      credits,
      reason,
      transactionId: transaction.id,
      addedBy: req.user.id
    });
    
    res.json({
      success: true,
      transaction: {
        id: transaction.id,
        credits: transaction.credits,
        newBalance: transaction.new_balance,
        timestamp: transaction.created_at
      }
    });
  } catch (error) {
    logger.error('Failed to add credits:', error);
    res.status(500).json({
      error: 'Failed to add credits',
      message: error.message
    });
  }
});

// Get credit pricing and packages
router.get('/pricing', (req, res) => {
  try {
    const pricing = creditsService.getCreditPricingPackages();
    
    res.json({
      success: true,
      pricing: {
        packages: pricing.packages,
        bulkDiscounts: pricing.bulkDiscounts,
        baseRate: pricing.baseRate,
        currency: pricing.currency
      }
    });
  } catch (error) {
    logger.error('Failed to get credit pricing:', error);
    res.status(500).json({
      error: 'Failed to get credit pricing',
      message: error.message
    });
  }
});

// Get credit usage rates for different services
router.get('/rates', (req, res) => {
  try {
    const rates = creditsService.getServiceRates();
    
    res.json({
      success: true,
      rates: rates.map(service => ({
        serviceName: service.name,
        displayName: service.displayName,
        category: service.category,
        rateType: service.rateType,
        baseRate: service.baseRate,
        tiers: service.tiers,
        description: service.description,
        examples: service.examples
      }))
    });
  } catch (error) {
    logger.error('Failed to get service rates:', error);
    res.status(500).json({
      error: 'Failed to get service rates',
      message: error.message
    });
  }
});

// Estimate credits needed for an operation
router.post('/estimate', async (req, res) => {
  try {
    const { serviceName, operationType, parameters = {} } = req.body;
    
    if (!serviceName || !operationType) {
      return res.status(400).json({
        error: 'Service name and operation type are required'
      });
    }
    
    const estimate = await creditsService.estimateCreditsNeeded(
      serviceName, 
      operationType, 
      parameters
    );
    
    res.json({
      success: true,
      estimate: {
        serviceName,
        operationType,
        estimatedCredits: estimate.credits,
        breakdown: estimate.breakdown,
        confidence: estimate.confidence,
        factors: estimate.factors
      }
    });
  } catch (error) {
    logger.error('Failed to estimate credits:', error);
    res.status(500).json({
      error: 'Failed to estimate credits',
      message: error.message
    });
  }
});

// Get credit usage analytics
router.get('/analytics', async (req, res) => {
  try {
    const { period = '30d', groupBy = 'service' } = req.query;
    
    const analytics = await creditsService.getCreditAnalytics(req.user.id, {
      period,
      groupBy
    });
    
    res.json({
      success: true,
      analytics: {
        period: analytics.period,
        totalCreditsUsed: analytics.totalUsed,
        totalCreditsPurchased: analytics.totalPurchased,
        efficiency: analytics.efficiency,
        topServices: analytics.topServices,
        dailyUsage: analytics.dailyUsage,
        projectedUsage: analytics.projectedUsage,
        recommendations: analytics.recommendations
      }
    });
  } catch (error) {
    logger.error('Failed to get credit analytics:', error);
    res.status(500).json({
      error: 'Failed to get credit analytics',
      message: error.message
    });
  }
});

// Set up credit usage alerts
router.post('/alerts', async (req, res) => {
  try {
    const { 
      type, 
      threshold, 
      enabled = true,
      notificationMethod = 'email'
    } = req.body;
    
    const validTypes = ['low_balance', 'high_usage', 'unusual_activity'];
    if (!validTypes.includes(type)) {
      return res.status(400).json({
        error: 'Invalid alert type',
        validTypes
      });
    }
    
    const alert = await creditsService.setCreditAlert(req.user.id, {
      type,
      threshold,
      enabled,
      notificationMethod
    });
    
    logger.info('Credit alert configured', {
      userId: req.user.id,
      alertId: alert.id,
      type,
      threshold
    });
    
    res.json({
      success: true,
      alert: {
        id: alert.id,
        type: alert.alert_type,
        threshold: alert.threshold,
        enabled: alert.enabled,
        notificationMethod: alert.notification_method
      }
    });
  } catch (error) {
    logger.error('Failed to set credit alert:', error);
    res.status(500).json({
      error: 'Failed to set credit alert',
      message: error.message
    });
  }
});

// Get user's credit alerts
router.get('/alerts', async (req, res) => {
  try {
    const alerts = await creditsService.getCreditAlerts(req.user.id);
    
    res.json({
      success: true,
      alerts: alerts.map(alert => ({
        id: alert.id,
        type: alert.alert_type,
        threshold: alert.threshold,
        enabled: alert.enabled,
        notificationMethod: alert.notification_method,
        lastTriggered: alert.last_triggered,
        createdAt: alert.created_at
      }))
    });
  } catch (error) {
    logger.error('Failed to get credit alerts:', error);
    res.status(500).json({
      error: 'Failed to get credit alerts',
      message: error.message
    });
  }
});

// Transfer credits to another user (if enabled)
router.post('/transfer', async (req, res) => {
  try {
    const { recipientUserId, credits, message = null } = req.body;
    
    if (!recipientUserId || !credits || credits <= 0) {
      return res.status(400).json({
        error: 'Recipient user ID and valid credits amount are required'
      });
    }
    
    if (recipientUserId === req.user.id) {
      return res.status(400).json({
        error: 'Cannot transfer credits to yourself'
      });
    }
    
    const transfer = await creditsService.transferCredits(
      req.user.id, 
      recipientUserId, 
      credits, 
      message
    );
    
    logger.audit('Credits transferred', {
      fromUserId: req.user.id,
      toUserId: recipientUserId,
      credits,
      transferId: transfer.id
    });
    
    res.json({
      success: true,
      transfer: {
        id: transfer.id,
        credits: transfer.credits,
        recipientUserId: transfer.recipient_user_id,
        message: transfer.message,
        timestamp: transfer.created_at
      }
    });
  } catch (error) {
    logger.error('Failed to transfer credits:', error);
    res.status(500).json({
      error: 'Failed to transfer credits',
      message: error.message
    });
  }
});

// Get credit transfer history
router.get('/transfers', async (req, res) => {
  try {
    const { page = 1, limit = 20, type = 'all' } = req.query;
    
    const transfers = await creditsService.getCreditTransferHistory(req.user.id, {
      page: parseInt(page),
      limit: parseInt(limit),
      type // 'sent', 'received', 'all'
    });
    
    res.json({
      success: true,
      transfers: transfers.data.map(transfer => ({
        id: transfer.id,
        type: transfer.sender_user_id === req.user.id ? 'sent' : 'received',
        credits: transfer.credits,
        otherUserId: transfer.sender_user_id === req.user.id ? transfer.recipient_user_id : transfer.sender_user_id,
        message: transfer.message,
        status: transfer.status,
        timestamp: transfer.created_at
      })),
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: transfers.total,
        pages: Math.ceil(transfers.total / parseInt(limit))
      }
    });
  } catch (error) {
    logger.error('Failed to get transfer history:', error);
    res.status(500).json({
      error: 'Failed to get transfer history',
      message: error.message
    });
  }
});

module.exports = router;