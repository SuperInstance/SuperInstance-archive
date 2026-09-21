const express = require('express');
const { PRICING_PLANS } = require('../config/stripe');
const SubscriptionService = require('../services/SubscriptionService');
const logger = require('../utils/logger');

const router = express.Router();
const subscriptionService = new SubscriptionService();

// Get user subscription details
router.get('/current', async (req, res) => {
  try {
    const subscription = await subscriptionService.getUserSubscription(req.user.id);
    
    if (!subscription) {
      return res.json({
        subscription: null,
        plan: 'free',
        features: PRICING_PLANS.free.features,
        status: 'active'
      });
    }

    const planDetails = PRICING_PLANS[subscription.plan] || PRICING_PLANS.free;
    
    res.json({
      subscription: {
        id: subscription.id,
        stripeSubscriptionId: subscription.stripe_subscription_id,
        plan: subscription.plan,
        status: subscription.status,
        currentPeriodStart: subscription.current_period_start,
        currentPeriodEnd: subscription.current_period_end,
        trialStart: subscription.trial_start,
        trialEnd: subscription.trial_end,
        cancelAt: subscription.cancel_at,
        canceledAt: subscription.canceled_at,
        createdAt: subscription.created_at
      },
      plan: subscription.plan,
      features: planDetails.features,
      usage: subscription.usage || {}
    });
  } catch (error) {
    logger.error('Failed to get current subscription:', error);
    res.status(500).json({
      error: 'Failed to get subscription details',
      message: error.message
    });
  }
});

// Get subscription usage and limits
router.get('/usage', async (req, res) => {
  try {
    const usage = await subscriptionService.getUserUsage(req.user.id);
    const subscription = await subscriptionService.getUserSubscription(req.user.id);
    
    const plan = subscription?.plan || 'free';
    const limits = PRICING_PLANS[plan]?.features || PRICING_PLANS.free.features;
    
    // Calculate usage percentages
    const usageWithPercentages = {
      storage: {
        used: usage.storage_gb || 0,
        limit: limits.storageGB === -1 ? 'unlimited' : limits.storageGB,
        percentage: limits.storageGB === -1 ? 0 : ((usage.storage_gb || 0) / limits.storageGB) * 100
      },
      apiCalls: {
        used: usage.api_calls_current_month || 0,
        limit: limits.apiCallsPerMonth === -1 ? 'unlimited' : limits.apiCallsPerMonth,
        percentage: limits.apiCallsPerMonth === -1 ? 0 : ((usage.api_calls_current_month || 0) / limits.apiCallsPerMonth) * 100
      },
      users: {
        used: usage.active_users || 1,
        limit: limits.usersLimit === -1 ? 'unlimited' : limits.usersLimit,
        percentage: limits.usersLimit === -1 ? 0 : ((usage.active_users || 1) / limits.usersLimit) * 100
      },
      computeCredits: {
        used: usage.compute_credits_used || 0,
        available: usage.compute_credits_available || limits.computeCredits,
        limit: limits.computeCredits
      }
    };
    
    res.json({
      usage: usageWithPercentages,
      billingPeriod: {
        start: subscription?.current_period_start || new Date(),
        end: subscription?.current_period_end || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
      },
      overages: await subscriptionService.calculateOverages(req.user.id)
    });
  } catch (error) {
    logger.error('Failed to get usage data:', error);
    res.status(500).json({
      error: 'Failed to get usage data',
      message: error.message
    });
  }
});

// Update subscription plan
router.put('/plan', async (req, res) => {
  try {
    const { newPlan, prorate = true } = req.body;
    
    if (!PRICING_PLANS[newPlan]) {
      return res.status(400).json({
        error: 'Invalid plan selected'
      });
    }
    
    const currentSubscription = await subscriptionService.getUserSubscription(req.user.id);
    const currentPlan = currentSubscription?.plan || 'free';
    
    if (currentPlan === newPlan) {
      return res.status(400).json({
        error: 'User is already on the selected plan'
      });
    }
    
    // Handle upgrade/downgrade logic
    let result;
    if (newPlan === 'free') {
      // Downgrade to free - cancel current subscription
      if (currentSubscription) {
        result = await subscriptionService.cancelSubscription(req.user.id, false);
      } else {
        result = { plan: 'free', status: 'active' };
      }
    } else if (currentPlan === 'free') {
      // Upgrade from free - create new subscription
      result = await subscriptionService.createSubscription(req.user.id, newPlan);
    } else {
      // Change between paid plans
      result = await subscriptionService.updateSubscriptionPlan(req.user.id, newPlan, prorate);
    }
    
    logger.subscription('Subscription plan updated', {
      userId: req.user.id,
      oldPlan: currentPlan,
      newPlan,
      prorate
    });
    
    res.json({
      success: true,
      subscription: result,
      message: `Successfully ${newPlan === 'free' ? 'downgraded to' : 'upgraded to'} ${PRICING_PLANS[newPlan].name}`
    });
  } catch (error) {
    logger.error('Failed to update subscription plan:', error);
    res.status(500).json({
      error: 'Failed to update subscription plan',
      message: error.message
    });
  }
});

// Cancel subscription
router.delete('/cancel', async (req, res) => {
  try {
    const { immediate = false } = req.query;
    
    const result = await subscriptionService.cancelSubscription(req.user.id, immediate === 'true');
    
    logger.subscription('Subscription canceled', {
      userId: req.user.id,
      immediate,
      cancelAt: result.cancelAt
    });
    
    res.json({
      success: true,
      subscription: result,
      message: immediate 
        ? 'Subscription canceled immediately' 
        : 'Subscription will be canceled at the end of the current billing period'
    });
  } catch (error) {
    logger.error('Failed to cancel subscription:', error);
    res.status(500).json({
      error: 'Failed to cancel subscription',
      message: error.message
    });
  }
});

// Reactivate canceled subscription
router.post('/reactivate', async (req, res) => {
  try {
    const result = await subscriptionService.reactivateSubscription(req.user.id);
    
    logger.subscription('Subscription reactivated', {
      userId: req.user.id,
      subscriptionId: result.id
    });
    
    res.json({
      success: true,
      subscription: result,
      message: 'Subscription successfully reactivated'
    });
  } catch (error) {
    logger.error('Failed to reactivate subscription:', error);
    res.status(500).json({
      error: 'Failed to reactivate subscription',
      message: error.message
    });
  }
});

// Get subscription history
router.get('/history', async (req, res) => {
  try {
    const { page = 1, limit = 10 } = req.query;
    
    const history = await subscriptionService.getSubscriptionHistory(
      req.user.id, 
      parseInt(page), 
      parseInt(limit)
    );
    
    res.json({
      history: history.data,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: history.total,
        pages: Math.ceil(history.total / parseInt(limit))
      }
    });
  } catch (error) {
    logger.error('Failed to get subscription history:', error);
    res.status(500).json({
      error: 'Failed to get subscription history',
      message: error.message
    });
  }
});

// Preview plan change costs
router.post('/preview-change', async (req, res) => {
  try {
    const { newPlan, prorate = true } = req.body;
    
    if (!PRICING_PLANS[newPlan]) {
      return res.status(400).json({
        error: 'Invalid plan selected'
      });
    }
    
    const preview = await subscriptionService.previewPlanChange(req.user.id, newPlan, prorate);
    
    res.json({
      preview,
      newPlanDetails: {
        name: PRICING_PLANS[newPlan].name,
        price: PRICING_PLANS[newPlan].price,
        features: PRICING_PLANS[newPlan].features
      }
    });
  } catch (error) {
    logger.error('Failed to preview plan change:', error);
    res.status(500).json({
      error: 'Failed to preview plan change',
      message: error.message
    });
  }
});

// Apply promo code
router.post('/promo-code', async (req, res) => {
  try {
    const { promoCode } = req.body;
    
    if (!promoCode || typeof promoCode !== 'string') {
      return res.status(400).json({
        error: 'Valid promo code is required'
      });
    }
    
    const result = await subscriptionService.applyPromoCode(req.user.id, promoCode);
    
    logger.subscription('Promo code applied', {
      userId: req.user.id,
      promoCode,
      discount: result.discount
    });
    
    res.json({
      success: true,
      discount: result.discount,
      message: result.message
    });
  } catch (error) {
    logger.error('Failed to apply promo code:', error);
    res.status(500).json({
      error: 'Failed to apply promo code',
      message: error.message
    });
  }
});

// Get available plans
router.get('/plans', (req, res) => {
  const plans = Object.entries(PRICING_PLANS).map(([key, plan]) => ({
    id: key,
    name: plan.name,
    price: plan.price,
    interval: plan.interval || null,
    features: plan.features,
    popular: key === 'pro', // Mark pro as popular
    description: getplanDescription(key)
  }));
  
  res.json({ plans });
});

// Helper function to get plan descriptions
function getplanDescription(planId) {
  const descriptions = {
    free: 'Perfect for individuals getting started with basic features',
    pro: 'Ideal for professionals and small teams who need advanced features',
    enterprise: 'Built for organizations requiring unlimited usage and enterprise features'
  };
  
  return descriptions[planId] || '';
}

// Check if user can upgrade/downgrade
router.get('/can-change/:newPlan', async (req, res) => {
  try {
    const { newPlan } = req.params;
    
    if (!PRICING_PLANS[newPlan]) {
      return res.status(400).json({
        error: 'Invalid plan'
      });
    }
    
    const canChange = await subscriptionService.canChangePlan(req.user.id, newPlan);
    
    res.json({
      canChange: canChange.allowed,
      reason: canChange.reason,
      requirements: canChange.requirements || []
    });
  } catch (error) {
    logger.error('Failed to check plan change eligibility:', error);
    res.status(500).json({
      error: 'Failed to check plan change eligibility',
      message: error.message
    });
  }
});

module.exports = router;