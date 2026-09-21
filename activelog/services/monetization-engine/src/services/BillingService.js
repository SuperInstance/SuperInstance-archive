const database = require('../config/database');
const StripeService = require('./StripeService');
const { PRICING_PLANS, USAGE_RATES } = require('../config/stripe');
const logger = require('../utils/logger');

class BillingService {
  constructor() {
    this.stripeService = new StripeService();
  }

  // Calculate usage-based billing for current period
  async calculateUsageBilling(userId) {
    try {
      const subscription = await database('subscriptions')
        .where('user_id', userId)
        .where('status', '!=', 'canceled')
        .first();

      const plan = subscription?.plan || 'free';
      const planDetails = PRICING_PLANS[plan];
      
      // Get current period usage
      const currentMonth = new Date();
      currentMonth.setDate(1);
      currentMonth.setHours(0, 0, 0, 0);

      const usage = await database('usage_metrics')
        .where('user_id', userId)
        .where('period_start', '>=', currentMonth)
        .first();

      if (!usage) {
        return {
          period: {
            start: currentMonth,
            end: new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0)
          },
          baseSubscription: planDetails?.price || 0,
          overages: { storage: 0, apiCalls: 0, bandwidth: 0, total: 0 },
          usageCharges: { computeCredits: 0 },
          totalAmount: planDetails?.price || 0,
          currency: 'usd',
          breakdown: [],
          nextBillingDate: subscription?.current_period_end || null
        };
      }

      const planLimits = planDetails?.features || PRICING_PLANS.free.features;
      
      // Calculate overages
      const overages = {
        storage: 0,
        apiCalls: 0,
        bandwidth: 0,
        total: 0
      };

      const breakdown = [];

      // Base subscription cost
      const baseSubscription = planDetails?.price || 0;
      if (baseSubscription > 0) {
        breakdown.push({
          type: 'subscription',
          description: `${planDetails.name} Plan`,
          amount: baseSubscription,
          currency: 'usd'
        });
      }

      // Storage overage
      if (planLimits.storageGB !== -1 && usage.storage_gb > planLimits.storageGB) {
        const overage = usage.storage_gb - planLimits.storageGB;
        overages.storage = Math.ceil(overage) * USAGE_RATES.storage.ratePerGB;
        breakdown.push({
          type: 'storage_overage',
          description: `Storage overage: ${overage.toFixed(2)}GB`,
          amount: overages.storage,
          currency: 'usd'
        });
      }

      // API calls overage
      if (planLimits.apiCallsPerMonth !== -1 && usage.api_calls_current_month > planLimits.apiCallsPerMonth) {
        const overage = usage.api_calls_current_month - planLimits.apiCallsPerMonth;
        overages.apiCalls = Math.ceil(overage / 1000) * USAGE_RATES.apiCalls.ratePerThousand;
        breakdown.push({
          type: 'api_overage',
          description: `API calls overage: ${overage.toLocaleString()} calls`,
          amount: overages.apiCalls,
          currency: 'usd'
        });
      }

      // Bandwidth overage
      if (usage.bandwidth_gb > USAGE_RATES.bandwidth.freeGB) {
        const overage = usage.bandwidth_gb - USAGE_RATES.bandwidth.freeGB;
        overages.bandwidth = Math.ceil(overage) * USAGE_RATES.bandwidth.ratePerGB;
        breakdown.push({
          type: 'bandwidth_overage',
          description: `Bandwidth overage: ${overage.toFixed(2)}GB`,
          amount: overages.bandwidth,
          currency: 'usd'
        });
      }

      overages.total = overages.storage + overages.apiCalls + overages.bandwidth;

      // Compute credits purchased this period
      const creditPurchases = await database('compute_credit_transactions')
        .where('user_id', userId)
        .where('created_at', '>=', currentMonth)
        .where('transaction_type', 'purchase')
        .sum('amount_cents as total');

      const usageCharges = {
        computeCredits: creditPurchases[0]?.total || 0
      };

      if (usageCharges.computeCredits > 0) {
        breakdown.push({
          type: 'compute_credits',
          description: 'Compute credits purchased',
          amount: usageCharges.computeCredits,
          currency: 'usd'
        });
      }

      const totalAmount = baseSubscription + overages.total + usageCharges.computeCredits;

      return {
        period: {
          start: currentMonth,
          end: new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0)
        },
        baseSubscription,
        overages,
        usageCharges,
        totalAmount,
        currency: 'usd',
        breakdown,
        nextBillingDate: subscription?.current_period_end || null
      };
    } catch (error) {
      logger.error('Failed to calculate usage billing:', error);
      throw error;
    }
  }

  // Get detailed usage breakdown
  async getUsageBreakdown(userId, period = null) {
    try {
      const periodDate = period ? new Date(`${period}-01`) : new Date();
      periodDate.setDate(1);
      periodDate.setHours(0, 0, 0, 0);

      const subscription = await database('subscriptions')
        .where('user_id', userId)
        .where('status', '!=', 'canceled')
        .first();

      const plan = subscription?.plan || 'free';
      const planLimits = PRICING_PLANS[plan]?.features || PRICING_PLANS.free.features;

      const usage = await database('usage_metrics')
        .where('user_id', userId)
        .where('period_start', '>=', periodDate)
        .first();

      if (!usage) {
        return this.getEmptyUsageBreakdown(periodDate, planLimits);
      }

      // Calculate costs for each usage type
      const breakdown = {
        period: {
          start: periodDate,
          end: new Date(periodDate.getFullYear(), periodDate.getMonth() + 1, 0)
        },
        storage: this.calculateStorageCost(usage.storage_gb, planLimits.storageGB),
        apiCalls: this.calculateApiCallsCost(usage.api_calls_current_month, planLimits.apiCallsPerMonth),
        bandwidth: this.calculateBandwidthCost(usage.bandwidth_gb, USAGE_RATES.bandwidth.freeGB),
        computeCredits: await this.getComputeCreditsBreakdown(userId, periodDate)
      };

      // Get daily usage data for the period
      const dailyUsage = await this.getDailyUsageData(userId, periodDate);
      
      // Calculate projected monthly usage based on current usage
      const projectedMonthly = this.calculateProjectedUsage(usage, periodDate);

      return {
        ...breakdown,
        dailyUsage,
        projectedMonthly
      };
    } catch (error) {
      logger.error('Failed to get usage breakdown:', error);
      throw error;
    }
  }

  // Purchase compute credits
  async purchaseComputeCredits(userId, amount, paymentMethodId = null) {
    const transaction = await database.transaction();
    
    try {
      if (amount < 100) {
        throw new Error('Minimum credit purchase is 100 credits');
      }

      const costCalculation = this.calculateCreditCost(amount);

      // Create payment intent
      const stripeCustomer = await database('stripe_customers')
        .join('users', 'stripe_customers.user_id', 'users.id')
        .where('users.id', userId)
        .select('stripe_customers.stripe_customer_id')
        .first();

      if (!stripeCustomer) {
        throw new Error('Stripe customer not found');
      }

      const paymentIntent = await this.stripeService.createPaymentIntent({
        amount: costCalculation.finalCost,
        currency: 'usd',
        customer: stripeCustomer.stripe_customer_id,
        payment_method: paymentMethodId,
        confirm: !!paymentMethodId,
        metadata: {
          userId,
          type: 'compute_credits',
          credits: amount,
          discount: costCalculation.discount
        }
      });

      // Record the credit purchase
      const creditTransaction = await database('compute_credit_transactions')
        .insert({
          user_id: userId,
          transaction_type: 'purchase',
          credits: amount,
          amount_cents: costCalculation.finalCost,
          discount_amount: costCalculation.savings,
          stripe_payment_intent_id: paymentIntent.id,
          status: paymentIntent.status === 'succeeded' ? 'completed' : 'pending',
          created_at: new Date(),
          updated_at: new Date()
        })
        .returning('*')
        .first();

      // If payment succeeded, add credits to user balance
      if (paymentIntent.status === 'succeeded') {
        await database('usage_metrics')
          .where('user_id', userId)
          .where('period_start', '>=', new Date(new Date().getFullYear(), new Date().getMonth(), 1))
          .increment('compute_credits_available', amount);
      }

      await transaction.commit();

      logger.billing('Compute credits purchase initiated', {
        userId,
        credits: amount,
        cost: costCalculation.finalCost,
        paymentIntentId: paymentIntent.id,
        status: paymentIntent.status
      });

      return {
        credits: amount,
        cost: costCalculation.finalCost,
        discount: costCalculation.discount,
        savings: costCalculation.savings,
        paymentIntentId: paymentIntent.id,
        status: paymentIntent.status,
        transaction: creditTransaction
      };
    } catch (error) {
      await transaction.rollback();
      logger.error('Failed to purchase compute credits:', error);
      throw error;
    }
  }

  // Calculate compute credit cost with bulk discounts
  calculateCreditCost(amount) {
    const baseCostPer100 = USAGE_RATES.computeCredits.ratePer100Credits;
    const baseCost = Math.ceil(amount / 100) * baseCostPer100;

    let discount = 1;
    const bulkDiscounts = USAGE_RATES.computeCredits.bulkDiscounts;
    
    // Find the highest applicable discount
    const sortedThresholds = Object.keys(bulkDiscounts)
      .map(t => parseInt(t))
      .sort((a, b) => b - a);

    for (const threshold of sortedThresholds) {
      if (amount >= threshold) {
        discount = bulkDiscounts[threshold];
        break;
      }
    }

    const finalCost = Math.round(baseCost * discount);
    const savings = baseCost - finalCost;

    return {
      baseCost,
      discount: (1 - discount) * 100, // Convert to percentage
      finalCost,
      savings,
      costPer100: Math.round(baseCostPer100 * discount)
    };
  }

  // Get billing history
  async getBillingHistory(userId, page = 1, limit = 10, type = null) {
    try {
      let query = database('billing_history')
        .where('user_id', userId);

      if (type) {
        query = query.where('transaction_type', type);
      }

      const offset = (page - 1) * limit;

      const [history, [{ count }]] = await Promise.all([
        query
          .orderBy('created_at', 'desc')
          .limit(limit)
          .offset(offset)
          .select('*'),
        
        query.clone().count('* as count')
      ]);

      return {
        data: history,
        total: parseInt(count)
      };
    } catch (error) {
      logger.error('Failed to get billing history:', error);
      throw error;
    }
  }

  // Set billing alert
  async setBillingAlert(userId, alertConfig) {
    try {
      const existingAlert = await database('billing_alerts')
        .where('user_id', userId)
        .where('alert_type', alertConfig.type)
        .first();

      if (existingAlert) {
        const updated = await database('billing_alerts')
          .where('id', existingAlert.id)
          .update({
            threshold: alertConfig.threshold,
            enabled: alertConfig.enabled,
            updated_at: new Date()
          })
          .returning('*')
          .first();
        
        return updated;
      } else {
        const created = await database('billing_alerts')
          .insert({
            user_id: userId,
            alert_type: alertConfig.type,
            threshold: alertConfig.threshold,
            enabled: alertConfig.enabled,
            created_at: new Date(),
            updated_at: new Date()
          })
          .returning('*')
          .first();
        
        return created;
      }
    } catch (error) {
      logger.error('Failed to set billing alert:', error);
      throw error;
    }
  }

  // Get billing alerts
  async getBillingAlerts(userId) {
    try {
      return await database('billing_alerts')
        .where('user_id', userId)
        .orderBy('created_at', 'desc')
        .select('*');
    } catch (error) {
      logger.error('Failed to get billing alerts:', error);
      throw error;
    }
  }

  // Update billing alert
  async updateBillingAlert(userId, alertId, updates) {
    try {
      const alert = await database('billing_alerts')
        .where('id', alertId)
        .where('user_id', userId)
        .update({
          ...updates,
          updated_at: new Date()
        })
        .returning('*')
        .first();

      if (!alert) {
        throw new Error('Billing alert not found');
      }

      return alert;
    } catch (error) {
      logger.error('Failed to update billing alert:', error);
      throw error;
    }
  }

  // Delete billing alert
  async deleteBillingAlert(userId, alertId) {
    try {
      const deleted = await database('billing_alerts')
        .where('id', alertId)
        .where('user_id', userId)
        .del();

      if (deleted === 0) {
        throw new Error('Billing alert not found');
      }

      return true;
    } catch (error) {
      logger.error('Failed to delete billing alert:', error);
      throw error;
    }
  }

  // Generate cost estimate
  async generateCostEstimate(userId, projectedUsage) {
    try {
      const subscription = await database('subscriptions')
        .where('user_id', userId)
        .where('status', '!=', 'canceled')
        .first();

      const currentPlan = subscription?.plan || 'free';
      const planDetails = PRICING_PLANS[currentPlan];

      // Calculate costs for each plan with projected usage
      const planEstimates = {};
      
      for (const [planId, plan] of Object.entries(PRICING_PLANS)) {
        planEstimates[planId] = this.calculatePlanCost(projectedUsage, plan);
      }

      // Generate recommendations
      const recommendations = this.generatePlanRecommendations(
        currentPlan,
        projectedUsage,
        planEstimates
      );

      return {
        currentPlan,
        costs: planEstimates,
        recommendations,
        potentialSavings: this.calculatePotentialSavings(currentPlan, planEstimates)
      };
    } catch (error) {
      logger.error('Failed to generate cost estimate:', error);
      throw error;
    }
  }

  // Export billing data
  async exportBillingData(userId, format, period) {
    try {
      let query = database('billing_history')
        .where('user_id', userId);

      if (period) {
        const periodDate = new Date(`${period}-01`);
        const periodEnd = new Date(periodDate.getFullYear(), periodDate.getMonth() + 1, 0);
        query = query.whereBetween('created_at', [periodDate, periodEnd]);
      }

      const billingData = await query
        .orderBy('created_at', 'desc')
        .select('*');

      if (format === 'csv') {
        return this.formatBillingDataCSV(billingData);
      } else if (format === 'pdf') {
        return this.formatBillingDataPDF(billingData, userId, period);
      } else {
        return {
          data: JSON.stringify(billingData, null, 2),
          recordCount: billingData.length
        };
      }
    } catch (error) {
      logger.error('Failed to export billing data:', error);
      throw error;
    }
  }

  // Helper methods
  getEmptyUsageBreakdown(periodDate, planLimits) {
    return {
      period: {
        start: periodDate,
        end: new Date(periodDate.getFullYear(), periodDate.getMonth() + 1, 0)
      },
      storage: { used: 0, limit: planLimits.storageGB, overage: 0, cost: 0 },
      apiCalls: { used: 0, limit: planLimits.apiCallsPerMonth, overage: 0, cost: 0 },
      bandwidth: { used: 0, limit: USAGE_RATES.bandwidth.freeGB, overage: 0, cost: 0 },
      computeCredits: { purchased: 0, used: 0, remaining: 0, cost: 0 },
      dailyUsage: [],
      projectedMonthly: { storage: 0, apiCalls: 0, bandwidth: 0, computeCredits: 0 }
    };
  }

  calculateStorageCost(used, limit) {
    const overage = limit === -1 ? 0 : Math.max(0, used - limit);
    const cost = overage > 0 ? Math.ceil(overage) * USAGE_RATES.storage.ratePerGB : 0;
    
    return { used, limit, overage, cost };
  }

  calculateApiCallsCost(used, limit) {
    const overage = limit === -1 ? 0 : Math.max(0, used - limit);
    const cost = overage > 0 ? Math.ceil(overage / 1000) * USAGE_RATES.apiCalls.ratePerThousand : 0;
    
    return { used, limit, overage, cost };
  }

  calculateBandwidthCost(used, freeAmount) {
    const overage = Math.max(0, used - freeAmount);
    const cost = overage > 0 ? Math.ceil(overage) * USAGE_RATES.bandwidth.ratePerGB : 0;
    
    return { used, limit: freeAmount, overage, cost };
  }

  async getComputeCreditsBreakdown(userId, periodDate) {
    const purchases = await database('compute_credit_transactions')
      .where('user_id', userId)
      .where('created_at', '>=', periodDate)
      .where('transaction_type', 'purchase')
      .sum('credits as purchased')
      .sum('amount_cents as cost');

    const usage = await database('compute_credit_transactions')
      .where('user_id', userId)
      .where('created_at', '>=', periodDate)
      .where('transaction_type', 'usage')
      .sum('credits as used');

    const current = await database('usage_metrics')
      .where('user_id', userId)
      .where('period_start', '>=', periodDate)
      .first();

    return {
      purchased: purchases[0]?.purchased || 0,
      used: usage[0]?.used || 0,
      remaining: current?.compute_credits_available || 0,
      cost: purchases[0]?.cost || 0
    };
  }

  async getDailyUsageData(userId, periodDate) {
    // This would typically come from a more granular usage tracking table
    // For now, return mock data structure
    return [];
  }

  calculateProjectedUsage(usage, periodDate) {
    const now = new Date();
    const daysInMonth = new Date(periodDate.getFullYear(), periodDate.getMonth() + 1, 0).getDate();
    const daysSoFar = now.getDate();
    const projectionMultiplier = daysInMonth / daysSoFar;

    return {
      storage: usage.storage_gb, // Storage doesn't project, it's current usage
      apiCalls: Math.round(usage.api_calls_current_month * projectionMultiplier),
      bandwidth: Math.round(usage.bandwidth_gb * projectionMultiplier),
      computeCredits: Math.round(usage.compute_credits_used * projectionMultiplier)
    };
  }

  calculatePlanCost(projectedUsage, plan) {
    const baseCost = plan.price || 0;
    let overageCosts = 0;

    // Calculate overages for this plan
    if (plan.features.storageGB !== -1 && projectedUsage.storage > plan.features.storageGB) {
      const overage = projectedUsage.storage - plan.features.storageGB;
      overageCosts += Math.ceil(overage) * USAGE_RATES.storage.ratePerGB;
    }

    if (plan.features.apiCallsPerMonth !== -1 && projectedUsage.apiCalls > plan.features.apiCallsPerMonth) {
      const overage = projectedUsage.apiCalls - plan.features.apiCallsPerMonth;
      overageCosts += Math.ceil(overage / 1000) * USAGE_RATES.apiCalls.ratePerThousand;
    }

    if (projectedUsage.bandwidth > USAGE_RATES.bandwidth.freeGB) {
      const overage = projectedUsage.bandwidth - USAGE_RATES.bandwidth.freeGB;
      overageCosts += Math.ceil(overage) * USAGE_RATES.bandwidth.ratePerGB;
    }

    return {
      baseCost,
      overageCosts,
      totalCost: baseCost + overageCosts
    };
  }

  generatePlanRecommendations(currentPlan, projectedUsage, planEstimates) {
    const recommendations = [];
    const currentCost = planEstimates[currentPlan].totalCost;

    // Find the most cost-effective plan
    let bestPlan = currentPlan;
    let bestCost = currentCost;

    for (const [planId, estimate] of Object.entries(planEstimates)) {
      if (estimate.totalCost < bestCost) {
        bestPlan = planId;
        bestCost = estimate.totalCost;
      }
    }

    if (bestPlan !== currentPlan) {
      const savings = currentCost - bestCost;
      recommendations.push({
        type: 'plan_change',
        plan: bestPlan,
        savings,
        reason: `Switch to ${PRICING_PLANS[bestPlan].name} to save $${(savings / 100).toFixed(2)} per month`
      });
    }

    // Check for high overages
    const currentPlanEstimate = planEstimates[currentPlan];
    if (currentPlanEstimate.overageCosts > currentPlanEstimate.baseCost * 0.5) {
      recommendations.push({
        type: 'usage_optimization',
        reason: 'Consider upgrading your plan to avoid high overage charges',
        potentialSavings: currentPlanEstimate.overageCosts
      });
    }

    return recommendations;
  }

  calculatePotentialSavings(currentPlan, planEstimates) {
    const currentCost = planEstimates[currentPlan].totalCost;
    let maxSavings = 0;
    let bestPlan = currentPlan;

    for (const [planId, estimate] of Object.entries(planEstimates)) {
      const savings = currentCost - estimate.totalCost;
      if (savings > maxSavings) {
        maxSavings = savings;
        bestPlan = planId;
      }
    }

    return {
      amount: maxSavings,
      plan: bestPlan,
      percentage: currentCost > 0 ? (maxSavings / currentCost) * 100 : 0
    };
  }

  formatBillingDataCSV(billingData) {
    const csvWriter = require('csv-writer').createObjectCsvStringifier({
      header: [
        { id: 'created_at', title: 'Date' },
        { id: 'transaction_type', title: 'Type' },
        { id: 'description', title: 'Description' },
        { id: 'amount_cents', title: 'Amount (cents)' },
        { id: 'currency', title: 'Currency' },
        { id: 'status', title: 'Status' }
      ]
    });

    return {
      data: csvWriter.getHeaderString() + csvWriter.stringifyRecords(billingData),
      recordCount: billingData.length
    };
  }

  async formatBillingDataPDF(billingData, userId, period) {
    // This would use a PDF generation library like PDFKit
    // For now, return a placeholder
    return {
      data: Buffer.from('PDF content placeholder'),
      recordCount: billingData.length
    };
  }

  // Get/Set spending limits
  async getSpendingLimits(userId) {
    try {
      const limits = await database('spending_limits')
        .where('user_id', userId)
        .first();

      if (!limits) {
        return {
          monthlyLimit: null,
          currentSpending: 0,
          remainingBudget: null,
          spendingPercentage: 0,
          alertThresholds: []
        };
      }

      // Get current month spending
      const currentMonth = new Date();
      currentMonth.setDate(1);
      currentMonth.setHours(0, 0, 0, 0);

      const spending = await database('billing_history')
        .where('user_id', userId)
        .where('created_at', '>=', currentMonth)
        .sum('amount_cents as total');

      const currentSpending = spending[0]?.total || 0;
      const remainingBudget = limits.monthly_limit - currentSpending;
      const spendingPercentage = (currentSpending / limits.monthly_limit) * 100;

      return {
        monthlyLimit: limits.monthly_limit,
        currentSpending,
        remainingBudget,
        spendingPercentage,
        alertThresholds: limits.alert_thresholds || []
      };
    } catch (error) {
      logger.error('Failed to get spending limits:', error);
      throw error;
    }
  }

  async setSpendingLimits(userId, limitsConfig) {
    try {
      const existing = await database('spending_limits')
        .where('user_id', userId)
        .first();

      if (existing) {
        const updated = await database('spending_limits')
          .where('user_id', userId)
          .update({
            monthly_limit: limitsConfig.monthlyLimit,
            alert_thresholds: JSON.stringify(limitsConfig.alertThresholds),
            updated_at: new Date()
          })
          .returning('*')
          .first();
        
        return updated;
      } else {
        const created = await database('spending_limits')
          .insert({
            user_id: userId,
            monthly_limit: limitsConfig.monthlyLimit,
            alert_thresholds: JSON.stringify(limitsConfig.alertThresholds),
            created_at: new Date(),
            updated_at: new Date()
          })
          .returning('*')
          .first();
        
        return created;
      }
    } catch (error) {
      logger.error('Failed to set spending limits:', error);
      throw error;
    }
  }
}

module.exports = BillingService;