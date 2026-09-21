const database = require('../config/database');
const StripeService = require('./StripeService');
const { PRICING_PLANS, USAGE_RATES } = require('../config/stripe');
const logger = require('../utils/logger');

class SubscriptionService {
  constructor() {
    this.stripeService = new StripeService();
  }

  // Get user's current subscription
  async getUserSubscription(userId) {
    try {
      const subscription = await database('subscriptions')
        .join('users', 'subscriptions.user_id', 'users.id')
        .where('users.id', userId)
        .where('subscriptions.status', '!=', 'canceled')
        .select(
          'subscriptions.*',
          'subscriptions.plan',
          'subscriptions.status'
        )
        .first();
      
      return subscription;
    } catch (error) {
      logger.error('Failed to get user subscription:', error);
      throw error;
    }
  }

  // Get user usage data
  async getUserUsage(userId) {
    try {
      const currentMonth = new Date();
      currentMonth.setDate(1);
      currentMonth.setHours(0, 0, 0, 0);

      const usage = await database('usage_metrics')
        .where('user_id', userId)
        .where('period_start', '>=', currentMonth)
        .first();

      if (!usage) {
        // Create initial usage record
        await database('usage_metrics').insert({
          user_id: userId,
          period_start: currentMonth,
          period_end: new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0),
          storage_gb: 0,
          api_calls_current_month: 0,
          active_users: 1,
          compute_credits_used: 0,
          compute_credits_available: 0,
          bandwidth_gb: 0,
          created_at: new Date(),
          updated_at: new Date()
        });

        return {
          storage_gb: 0,
          api_calls_current_month: 0,
          active_users: 1,
          compute_credits_used: 0,
          compute_credits_available: 0,
          bandwidth_gb: 0
        };
      }

      return usage;
    } catch (error) {
      logger.error('Failed to get user usage:', error);
      throw error;
    }
  }

  // Calculate overage charges
  async calculateOverages(userId) {
    try {
      const subscription = await this.getUserSubscription(userId);
      const usage = await this.getUserUsage(userId);
      const plan = subscription?.plan || 'free';
      const planLimits = PRICING_PLANS[plan]?.features || PRICING_PLANS.free.features;

      const overages = {
        storage: 0,
        apiCalls: 0,
        bandwidth: 0,
        total: 0
      };

      // Calculate storage overage
      if (planLimits.storageGB !== -1 && usage.storage_gb > planLimits.storageGB) {
        const overage = usage.storage_gb - planLimits.storageGB;
        overages.storage = Math.ceil(overage) * USAGE_RATES.storage.ratePerGB;
      }

      // Calculate API calls overage
      if (planLimits.apiCallsPerMonth !== -1 && usage.api_calls_current_month > planLimits.apiCallsPerMonth) {
        const overage = usage.api_calls_current_month - planLimits.apiCallsPerMonth;
        overages.apiCalls = Math.ceil(overage / 1000) * USAGE_RATES.apiCalls.ratePerThousand;
      }

      // Calculate bandwidth overage
      if (usage.bandwidth_gb > USAGE_RATES.bandwidth.freeGB) {
        const overage = usage.bandwidth_gb - USAGE_RATES.bandwidth.freeGB;
        overages.bandwidth = Math.ceil(overage) * USAGE_RATES.bandwidth.ratePerGB;
      }

      overages.total = overages.storage + overages.apiCalls + overages.bandwidth;

      return overages;
    } catch (error) {
      logger.error('Failed to calculate overages:', error);
      throw error;
    }
  }

  // Create new subscription
  async createSubscription(userId, plan, paymentMethodId = null, trialDays = 0) {
    const transaction = await database.transaction();
    
    try {
      if (!PRICING_PLANS[plan] || plan === 'free') {
        throw new Error('Invalid subscription plan');
      }

      // Get or create Stripe customer
      let stripeCustomer = await database('stripe_customers')
        .join('users', 'stripe_customers.user_id', 'users.id')
        .where('users.id', userId)
        .select('stripe_customers.*')
        .first();

      if (!stripeCustomer) {
        const user = await database('users').where('id', userId).first();
        if (!user) {
          throw new Error('User not found');
        }

        const customer = await this.stripeService.createCustomer({
          email: user.email,
          name: user.name,
          metadata: { userId }
        });

        stripeCustomer = await database('stripe_customers')
          .insert({
            user_id: userId,
            stripe_customer_id: customer.id,
            email: customer.email,
            name: customer.name,
            created_at: new Date()
          })
          .returning('*')
          .first();
      }

      // Create Stripe subscription
      const subscription = await this.stripeService.createSubscription({
        customer: stripeCustomer.stripe_customer_id,
        items: [{
          price: PRICING_PLANS[plan].priceId
        }],
        trial_period_days: trialDays > 0 ? trialDays : undefined,
        metadata: {
          userId,
          plan
        }
      });

      // Save subscription to database
      const dbSubscription = await database('subscriptions')
        .insert({
          user_id: userId,
          stripe_subscription_id: subscription.id,
          stripe_customer_id: stripeCustomer.stripe_customer_id,
          plan,
          status: subscription.status,
          current_period_start: new Date(subscription.current_period_start * 1000),
          current_period_end: new Date(subscription.current_period_end * 1000),
          trial_start: subscription.trial_start ? new Date(subscription.trial_start * 1000) : null,
          trial_end: subscription.trial_end ? new Date(subscription.trial_end * 1000) : null,
          created_at: new Date(),
          updated_at: new Date()
        })
        .returning('*')
        .first();

      await transaction.commit();

      logger.subscription('Subscription created', {
        userId,
        subscriptionId: subscription.id,
        plan,
        trialDays
      });

      return dbSubscription;
    } catch (error) {
      await transaction.rollback();
      logger.error('Failed to create subscription:', error);
      throw error;
    }
  }

  // Update subscription plan
  async updateSubscriptionPlan(userId, newPlan, prorate = true) {
    try {
      const currentSubscription = await this.getUserSubscription(userId);
      if (!currentSubscription) {
        throw new Error('No active subscription found');
      }

      if (!PRICING_PLANS[newPlan] || newPlan === 'free') {
        throw new Error('Invalid subscription plan');
      }

      // Update Stripe subscription
      const updatedSubscription = await this.stripeService.updateSubscription(
        currentSubscription.stripe_subscription_id,
        {
          items: [{
            id: currentSubscription.stripe_subscription_id,
            price: PRICING_PLANS[newPlan].priceId
          }],
          proration_behavior: prorate ? 'create_prorations' : 'none',
          metadata: {
            userId,
            plan: newPlan,
            updatedAt: new Date().toISOString()
          }
        }
      );

      // Update database record
      const dbSubscription = await database('subscriptions')
        .where('id', currentSubscription.id)
        .update({
          plan: newPlan,
          status: updatedSubscription.status,
          current_period_start: new Date(updatedSubscription.current_period_start * 1000),
          current_period_end: new Date(updatedSubscription.current_period_end * 1000),
          updated_at: new Date()
        })
        .returning('*')
        .first();

      logger.subscription('Subscription plan updated', {
        userId,
        oldPlan: currentSubscription.plan,
        newPlan,
        prorate
      });

      return dbSubscription;
    } catch (error) {
      logger.error('Failed to update subscription plan:', error);
      throw error;
    }
  }

  // Cancel subscription
  async cancelSubscription(userId, immediate = false) {
    try {
      const subscription = await this.getUserSubscription(userId);
      if (!subscription) {
        throw new Error('No active subscription found');
      }

      // Cancel Stripe subscription
      const canceledSubscription = await this.stripeService.cancelSubscription(
        subscription.stripe_subscription_id,
        {
          cancel_at_period_end: !immediate,
          metadata: {
            userId,
            canceledAt: new Date().toISOString(),
            cancelType: immediate ? 'immediate' : 'end_of_period'
          }
        }
      );

      // Update database record
      const dbSubscription = await database('subscriptions')
        .where('id', subscription.id)
        .update({
          status: canceledSubscription.status,
          cancel_at: canceledSubscription.cancel_at ? new Date(canceledSubscription.cancel_at * 1000) : null,
          canceled_at: canceledSubscription.canceled_at ? new Date(canceledSubscription.canceled_at * 1000) : null,
          updated_at: new Date()
        })
        .returning('*')
        .first();

      logger.subscription('Subscription canceled', {
        userId,
        subscriptionId: subscription.stripe_subscription_id,
        immediate,
        cancelAt: canceledSubscription.cancel_at
      });

      return dbSubscription;
    } catch (error) {
      logger.error('Failed to cancel subscription:', error);
      throw error;
    }
  }

  // Reactivate subscription
  async reactivateSubscription(userId) {
    try {
      const subscription = await database('subscriptions')
        .where('user_id', userId)
        .where('status', 'canceled')
        .where('cancel_at', '>', new Date())
        .orderBy('created_at', 'desc')
        .first();

      if (!subscription) {
        throw new Error('No reactivatable subscription found');
      }

      // Reactivate Stripe subscription
      const reactivatedSubscription = await this.stripeService.updateSubscription(
        subscription.stripe_subscription_id,
        {
          cancel_at_period_end: false,
          metadata: {
            userId,
            reactivatedAt: new Date().toISOString()
          }
        }
      );

      // Update database record
      const dbSubscription = await database('subscriptions')
        .where('id', subscription.id)
        .update({
          status: reactivatedSubscription.status,
          cancel_at: null,
          canceled_at: null,
          updated_at: new Date()
        })
        .returning('*')
        .first();

      logger.subscription('Subscription reactivated', {
        userId,
        subscriptionId: subscription.stripe_subscription_id
      });

      return dbSubscription;
    } catch (error) {
      logger.error('Failed to reactivate subscription:', error);
      throw error;
    }
  }

  // Get subscription history
  async getSubscriptionHistory(userId, page = 1, limit = 10) {
    try {
      const offset = (page - 1) * limit;

      const [history, [{ count }]] = await Promise.all([
        database('subscriptions')
          .where('user_id', userId)
          .orderBy('created_at', 'desc')
          .limit(limit)
          .offset(offset)
          .select('*'),
        
        database('subscriptions')
          .where('user_id', userId)
          .count('* as count')
      ]);

      return {
        data: history,
        total: parseInt(count)
      };
    } catch (error) {
      logger.error('Failed to get subscription history:', error);
      throw error;
    }
  }

  // Preview plan change costs
  async previewPlanChange(userId, newPlan, prorate = true) {
    try {
      const subscription = await this.getUserSubscription(userId);
      const currentPlan = subscription?.plan || 'free';
      const currentPrice = PRICING_PLANS[currentPlan]?.price || 0;
      const newPrice = PRICING_PLANS[newPlan]?.price || 0;

      const preview = {
        currentPlan,
        newPlan,
        currentPrice,
        newPrice,
        difference: newPrice - currentPrice,
        isUpgrade: newPrice > currentPrice,
        isDowngrade: newPrice < currentPrice,
        immediate: false,
        prorationAmount: 0
      };

      if (subscription && prorate && newPrice !== currentPrice) {
        // Calculate proration for the remaining period
        const now = new Date();
        const periodEnd = new Date(subscription.current_period_end);
        const periodStart = new Date(subscription.current_period_start);
        
        const totalPeriodDays = Math.ceil((periodEnd - periodStart) / (1000 * 60 * 60 * 24));
        const remainingDays = Math.ceil((periodEnd - now) / (1000 * 60 * 60 * 24));
        const remainingRatio = remainingDays / totalPeriodDays;

        if (preview.isUpgrade) {
          preview.prorationAmount = Math.round(preview.difference * remainingRatio);
          preview.immediate = true;
        } else if (preview.isDowngrade) {
          preview.creditAmount = Math.round(Math.abs(preview.difference) * remainingRatio);
          preview.immediate = false; // Apply at next billing cycle
        }
      }

      return preview;
    } catch (error) {
      logger.error('Failed to preview plan change:', error);
      throw error;
    }
  }

  // Apply promo code
  async applyPromoCode(userId, promoCode) {
    try {
      const promo = await database('promo_codes')
        .where('code', promoCode.toUpperCase())
        .where('active', true)
        .where('expires_at', '>', new Date())
        .first();

      if (!promo) {
        throw new Error('Invalid or expired promo code');
      }

      // Check if user already used this promo code
      const existingUsage = await database('promo_code_usage')
        .where('user_id', userId)
        .where('promo_code_id', promo.id)
        .first();

      if (existingUsage) {
        throw new Error('Promo code already used');
      }

      // Check usage limits
      const usageCount = await database('promo_code_usage')
        .where('promo_code_id', promo.id)
        .count('* as count')
        .first();

      if (promo.max_uses && parseInt(usageCount.count) >= promo.max_uses) {
        throw new Error('Promo code usage limit reached');
      }

      // Record promo code usage
      await database('promo_code_usage').insert({
        user_id: userId,
        promo_code_id: promo.id,
        discount_amount: promo.discount_amount,
        discount_percentage: promo.discount_percentage,
        applied_at: new Date()
      });

      logger.subscription('Promo code applied', {
        userId,
        promoCode,
        discountAmount: promo.discount_amount,
        discountPercentage: promo.discount_percentage
      });

      return {
        discount: {
          amount: promo.discount_amount,
          percentage: promo.discount_percentage,
          type: promo.discount_type
        },
        message: `Successfully applied promo code: ${promo.description}`
      };
    } catch (error) {
      logger.error('Failed to apply promo code:', error);
      throw error;
    }
  }

  // Check if user can change to a specific plan
  async canChangePlan(userId, newPlan) {
    try {
      const subscription = await this.getUserSubscription(userId);
      const currentPlan = subscription?.plan || 'free';
      const usage = await this.getUserUsage(userId);
      const newPlanLimits = PRICING_PLANS[newPlan]?.features;

      if (!newPlanLimits) {
        return { allowed: false, reason: 'Invalid plan' };
      }

      if (currentPlan === newPlan) {
        return { allowed: false, reason: 'Already on this plan' };
      }

      const requirements = [];
      
      // Check storage limits
      if (newPlanLimits.storageGB !== -1 && usage.storage_gb > newPlanLimits.storageGB) {
        requirements.push(`Reduce storage usage to ${newPlanLimits.storageGB}GB (currently using ${usage.storage_gb}GB)`);
      }

      // Check user limits
      if (newPlanLimits.usersLimit !== -1 && usage.active_users > newPlanLimits.usersLimit) {
        requirements.push(`Reduce active users to ${newPlanLimits.usersLimit} (currently have ${usage.active_users} users)`);
      }

      // Check if downgrading would cause issues
      if (requirements.length > 0) {
        return {
          allowed: false,
          reason: 'Usage exceeds plan limits',
          requirements
        };
      }

      return { allowed: true, reason: 'Plan change allowed' };
    } catch (error) {
      logger.error('Failed to check plan change eligibility:', error);
      throw error;
    }
  }

  // Record usage metrics
  async recordUsage(userId, usageType, amount) {
    try {
      const currentMonth = new Date();
      currentMonth.setDate(1);
      currentMonth.setHours(0, 0, 0, 0);

      await database('usage_metrics')
        .where('user_id', userId)
        .where('period_start', currentMonth)
        .increment(usageType, amount)
        .orInsert({
          user_id: userId,
          period_start: currentMonth,
          period_end: new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0),
          [usageType]: amount,
          created_at: new Date(),
          updated_at: new Date()
        });

      logger.info('Usage recorded', {
        userId,
        usageType,
        amount,
        period: currentMonth.toISOString()
      });
    } catch (error) {
      logger.error('Failed to record usage:', error);
      throw error;
    }
  }
}

module.exports = SubscriptionService;