const express = require('express');
const BillingService = require('../services/BillingService');
const { USAGE_RATES } = require('../config/stripe');
const logger = require('../utils/logger');

const router = express.Router();
const billingService = new BillingService();

// Calculate usage-based billing for current period
router.get('/usage-calculation', async (req, res) => {
  try {
    const billing = await billingService.calculateUsageBilling(req.user.id);
    
    res.json({
      success: true,
      billing: {
        period: billing.period,
        baseSubscription: billing.baseSubscription,
        overages: billing.overages,
        usageCharges: billing.usageCharges,
        totalAmount: billing.totalAmount,
        currency: billing.currency,
        breakdown: billing.breakdown
      },
      nextBillingDate: billing.nextBillingDate
    });
  } catch (error) {
    logger.error('Failed to calculate usage billing:', error);
    res.status(500).json({
      error: 'Failed to calculate usage billing',
      message: error.message
    });
  }
});

// Get detailed usage breakdown
router.get('/usage-breakdown', async (req, res) => {
  try {
    const { period } = req.query; // YYYY-MM format, defaults to current month
    
    const breakdown = await billingService.getUsageBreakdown(req.user.id, period);
    
    res.json({
      success: true,
      breakdown: {
        period: breakdown.period,
        usage: {
          storage: {
            current: breakdown.storage.used,
            limit: breakdown.storage.limit,
            overage: breakdown.storage.overage,
            cost: breakdown.storage.cost
          },
          apiCalls: {
            current: breakdown.apiCalls.used,
            limit: breakdown.apiCalls.limit,
            overage: breakdown.apiCalls.overage,
            cost: breakdown.apiCalls.cost
          },
          bandwidth: {
            current: breakdown.bandwidth.used,
            limit: breakdown.bandwidth.limit,
            overage: breakdown.bandwidth.overage,
            cost: breakdown.bandwidth.cost
          },
          computeCredits: {
            purchased: breakdown.computeCredits.purchased,
            used: breakdown.computeCredits.used,
            remaining: breakdown.computeCredits.remaining,
            cost: breakdown.computeCredits.cost
          }
        },
        dailyUsage: breakdown.dailyUsage,
        projectedMonthly: breakdown.projectedMonthly
      }
    });
  } catch (error) {
    logger.error('Failed to get usage breakdown:', error);
    res.status(500).json({
      error: 'Failed to get usage breakdown',
      message: error.message
    });
  }
});

// Purchase compute credits
router.post('/credits/purchase', async (req, res) => {
  try {
    const { amount, paymentMethodId } = req.body;
    
    if (!amount || amount < 100) {
      return res.status(400).json({
        error: 'Minimum credit purchase is 100 credits'
      });
    }
    
    const purchase = await billingService.purchaseComputeCredits(
      req.user.id, 
      amount, 
      paymentMethodId
    );
    
    logger.billing('Compute credits purchased', {
      userId: req.user.id,
      amount,
      cost: purchase.cost,
      paymentIntentId: purchase.paymentIntentId
    });
    
    res.json({
      success: true,
      purchase: {
        credits: purchase.credits,
        cost: purchase.cost,
        discount: purchase.discount,
        paymentIntentId: purchase.paymentIntentId
      },
      message: `Successfully purchased ${amount} compute credits`
    });
  } catch (error) {
    logger.error('Failed to purchase compute credits:', error);
    res.status(500).json({
      error: 'Failed to purchase compute credits',
      message: error.message
    });
  }
});

// Get credit purchase pricing
router.get('/credits/pricing', (req, res) => {
  const { amount } = req.query;
  
  if (!amount) {
    return res.json({
      pricing: USAGE_RATES.computeCredits,
      bulkDiscounts: Object.entries(USAGE_RATES.computeCredits.bulkDiscounts).map(([threshold, discount]) => ({
        threshold: parseInt(threshold),
        discount: (1 - discount) * 100, // Convert to percentage discount
        multiplier: discount
      }))
    });
  }
  
  const creditAmount = parseInt(amount);
  if (creditAmount < 100) {
    return res.status(400).json({
      error: 'Minimum credit purchase is 100 credits'
    });
  }
  
  const calculation = billingService.calculateCreditCost(creditAmount);
  
  res.json({
    credits: creditAmount,
    baseCost: calculation.baseCost,
    discount: calculation.discount,
    finalCost: calculation.finalCost,
    costPer100: calculation.costPer100,
    savings: calculation.savings
  });
});

// Get billing history
router.get('/history', async (req, res) => {
  try {
    const { page = 1, limit = 10, type } = req.query;
    
    const history = await billingService.getBillingHistory(
      req.user.id,
      parseInt(page),
      parseInt(limit),
      type
    );
    
    res.json({
      success: true,
      history: history.data,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: history.total,
        pages: Math.ceil(history.total / parseInt(limit))
      }
    });
  } catch (error) {
    logger.error('Failed to get billing history:', error);
    res.status(500).json({
      error: 'Failed to get billing history',
      message: error.message
    });
  }
});

// Set billing alerts
router.post('/alerts', async (req, res) => {
  try {
    const { type, threshold, enabled = true } = req.body;
    
    const validTypes = ['usage_threshold', 'cost_threshold', 'credit_low'];
    if (!validTypes.includes(type)) {
      return res.status(400).json({
        error: 'Invalid alert type',
        validTypes
      });
    }
    
    const alert = await billingService.setBillingAlert(req.user.id, {
      type,
      threshold,
      enabled
    });
    
    logger.billing('Billing alert set', {
      userId: req.user.id,
      type,
      threshold,
      enabled
    });
    
    res.json({
      success: true,
      alert,
      message: `Billing alert ${enabled ? 'enabled' : 'disabled'} for ${type}`
    });
  } catch (error) {
    logger.error('Failed to set billing alert:', error);
    res.status(500).json({
      error: 'Failed to set billing alert',
      message: error.message
    });
  }
});

// Get current billing alerts
router.get('/alerts', async (req, res) => {
  try {
    const alerts = await billingService.getBillingAlerts(req.user.id);
    
    res.json({
      success: true,
      alerts
    });
  } catch (error) {
    logger.error('Failed to get billing alerts:', error);
    res.status(500).json({
      error: 'Failed to get billing alerts',
      message: error.message
    });
  }
});

// Update billing alert
router.put('/alerts/:alertId', async (req, res) => {
  try {
    const { alertId } = req.params;
    const { threshold, enabled } = req.body;
    
    const alert = await billingService.updateBillingAlert(req.user.id, alertId, {
      threshold,
      enabled
    });
    
    logger.billing('Billing alert updated', {
      userId: req.user.id,
      alertId,
      threshold,
      enabled
    });
    
    res.json({
      success: true,
      alert,
      message: 'Billing alert updated successfully'
    });
  } catch (error) {
    logger.error('Failed to update billing alert:', error);
    res.status(500).json({
      error: 'Failed to update billing alert',
      message: error.message
    });
  }
});

// Delete billing alert
router.delete('/alerts/:alertId', async (req, res) => {
  try {
    const { alertId } = req.params;
    
    await billingService.deleteBillingAlert(req.user.id, alertId);
    
    logger.billing('Billing alert deleted', {
      userId: req.user.id,
      alertId
    });
    
    res.json({
      success: true,
      message: 'Billing alert deleted successfully'
    });
  } catch (error) {
    logger.error('Failed to delete billing alert:', error);
    res.status(500).json({
      error: 'Failed to delete billing alert',
      message: error.message
    });
  }
});

// Generate cost estimate for projected usage
router.post('/estimate', async (req, res) => {
  try {
    const { projectedUsage } = req.body;
    
    if (!projectedUsage) {
      return res.status(400).json({
        error: 'Projected usage data is required'
      });
    }
    
    const estimate = await billingService.generateCostEstimate(req.user.id, projectedUsage);
    
    res.json({
      success: true,
      estimate: {
        projectedUsage,
        currentPlan: estimate.currentPlan,
        estimatedCosts: estimate.costs,
        recommendations: estimate.recommendations,
        potentialSavings: estimate.potentialSavings
      }
    });
  } catch (error) {
    logger.error('Failed to generate cost estimate:', error);
    res.status(500).json({
      error: 'Failed to generate cost estimate',
      message: error.message
    });
  }
});

// Export billing data
router.get('/export', async (req, res) => {
  try {
    const { format = 'csv', period } = req.query;
    
    const validFormats = ['csv', 'json', 'pdf'];
    if (!validFormats.includes(format)) {
      return res.status(400).json({
        error: 'Invalid export format',
        validFormats
      });
    }
    
    const exportData = await billingService.exportBillingData(
      req.user.id,
      format,
      period
    );
    
    logger.billing('Billing data exported', {
      userId: req.user.id,
      format,
      period,
      recordCount: exportData.recordCount
    });
    
    if (format === 'pdf') {
      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', `attachment; filename=billing-${period || 'all'}.pdf`);
    } else if (format === 'csv') {
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', `attachment; filename=billing-${period || 'all'}.csv`);
    } else {
      res.setHeader('Content-Type', 'application/json');
      res.setHeader('Content-Disposition', `attachment; filename=billing-${period || 'all'}.json`);
    }
    
    res.send(exportData.data);
  } catch (error) {
    logger.error('Failed to export billing data:', error);
    res.status(500).json({
      error: 'Failed to export billing data',
      message: error.message
    });
  }
});

// Check spending limits
router.get('/spending-limits', async (req, res) => {
  try {
    const limits = await billingService.getSpendingLimits(req.user.id);
    
    res.json({
      success: true,
      limits: {
        monthly: limits.monthlyLimit,
        current: limits.currentSpending,
        remaining: limits.remainingBudget,
        percentage: limits.spendingPercentage,
        alerts: limits.alertThresholds
      }
    });
  } catch (error) {
    logger.error('Failed to get spending limits:', error);
    res.status(500).json({
      error: 'Failed to get spending limits',
      message: error.message
    });
  }
});

// Set spending limits
router.post('/spending-limits', async (req, res) => {
  try {
    const { monthlyLimit, alertThresholds = [50, 80, 95] } = req.body;
    
    if (!monthlyLimit || monthlyLimit <= 0) {
      return res.status(400).json({
        error: 'Valid monthly spending limit is required'
      });
    }
    
    const limits = await billingService.setSpendingLimits(req.user.id, {
      monthlyLimit,
      alertThresholds
    });
    
    logger.billing('Spending limits set', {
      userId: req.user.id,
      monthlyLimit,
      alertThresholds
    });
    
    res.json({
      success: true,
      limits,
      message: 'Spending limits updated successfully'
    });
  } catch (error) {
    logger.error('Failed to set spending limits:', error);
    res.status(500).json({
      error: 'Failed to set spending limits',
      message: error.message
    });
  }
});

module.exports = router;