import Stripe from 'stripe';
import mongoose from 'mongoose';
import crypto from 'crypto';
import jwt from 'jsonwebtoken';

class MonetizationService {
  constructor() {
    this.stripe = null;
    this.subscriptionPlans = new Map();
    this.contentTiers = new Map();
    this.affiliateProgram = new Map();
    this.donationGoals = new Map();
    
    this.initializeStripe();
    this.setupSubscriptionPlans();
    this.setupContentTiers();
    this.setupAffiliateProgram();
  }

  initializeStripe() {
    if (process.env.STRIPE_SECRET_KEY) {
      this.stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
    } else {
      console.warn('Stripe not configured - payments disabled');
    }
  }

  setupSubscriptionPlans() {
    this.subscriptionPlans.set('free', {
      id: 'free',
      name: 'Free Adventurer',
      price: 0,
      interval: 'lifetime',
      features: [
        'Basic campaign management',
        'Up to 5 characters',
        'Standard dice roller',
        'Basic battle maps',
        'Community access'
      ],
      limits: {
        campaigns: 3,
        characters: 5,
        storage: '100MB',
        sessions_per_month: 20
      }
    });

    this.subscriptionPlans.set('pro', {
      id: 'pro',
      name: 'Pro Dungeon Master',
      price: 9.99,
      interval: 'month',
      stripeProductId: process.env.STRIPE_PRO_PRODUCT_ID,
      features: [
        'Unlimited campaigns',
        'Unlimited characters',
        '3D dice physics',
        'Advanced battle maps',
        '3D printing marketplace access',
        'Streaming overlays',
        'Advanced export options',
        'Priority support'
      ],
      limits: {
        campaigns: -1, // unlimited
        characters: -1,
        storage: '5GB',
        sessions_per_month: -1
      }
    });

    this.subscriptionPlans.set('legendary', {
      id: 'legendary',
      name: 'Legendary Master',
      price: 19.99,
      interval: 'month',
      stripeProductId: process.env.STRIPE_LEGENDARY_PRODUCT_ID,
      features: [
        'Everything in Pro',
        'AI-powered campaign assistance',
        'Advanced monetization tools',
        'White-label options',
        'API access',
        'Custom branding',
        'Advanced analytics',
        'Dedicated support'
      ],
      limits: {
        campaigns: -1,
        characters: -1,
        storage: '50GB',
        sessions_per_month: -1,
        api_calls: 10000
      }
    });
  }

  setupContentTiers() {
    // Content creator tiers for monetizing campaigns/content
    this.contentTiers.set('supporter', {
      id: 'supporter',
      name: 'Supporter',
      price: 2.99,
      benefits: [
        'Access to exclusive campaigns',
        'Early access to new content',
        'Supporter badge',
        'Discord access'
      ]
    });

    this.contentTiers.set('patron', {
      id: 'patron',
      name: 'Patron',
      price: 7.99,
      benefits: [
        'Everything in Supporter',
        'Custom character creation requests',
        'Monthly one-shot campaigns',
        'Direct message access',
        'Campaign notes access'
      ]
    });

    this.contentTiers.set('champion', {
      id: 'champion',
      name: 'Champion',
      price: 19.99,
      benefits: [
        'Everything in Patron',
        'Personal campaign consultation',
        'Custom content creation',
        'Co-DM opportunities',
        'Credit in published content'
      ]
    });
  }

  setupAffiliateProgram() {
    this.affiliateProgram.set('standard', {
      commission_rate: 0.20, // 20%
      cookie_duration: 30, // 30 days
      minimum_payout: 25.00,
      payment_schedule: 'monthly'
    });

    this.affiliateProgram.set('premium', {
      commission_rate: 0.30, // 30%
      cookie_duration: 60, // 60 days
      minimum_payout: 25.00,
      payment_schedule: 'monthly',
      requirements: {
        monthly_referrals: 10,
        total_earnings: 500
      }
    });
  }

  // Subscription Management
  async createSubscription(userId, planId, paymentMethodId) {
    if (!this.stripe) throw new Error('Stripe not configured');

    const plan = this.subscriptionPlans.get(planId);
    if (!plan || plan.id === 'free') {
      throw new Error('Invalid subscription plan');
    }

    try {
      // Create or retrieve customer
      const customer = await this.getOrCreateStripeCustomer(userId);
      
      // Attach payment method
      await this.stripe.paymentMethods.attach(paymentMethodId, {
        customer: customer.id
      });

      // Create subscription
      const subscription = await this.stripe.subscriptions.create({
        customer: customer.id,
        items: [{
          price: plan.stripeProductId
        }],
        default_payment_method: paymentMethodId,
        expand: ['latest_invoice.payment_intent']
      });

      // Update user subscription in database
      await this.updateUserSubscription(userId, {
        planId,
        stripeSubscriptionId: subscription.id,
        status: subscription.status,
        currentPeriodEnd: new Date(subscription.current_period_end * 1000),
        features: plan.features,
        limits: plan.limits
      });

      return {
        subscription,
        clientSecret: subscription.latest_invoice.payment_intent.client_secret
      };
    } catch (error) {
      console.error('Subscription creation failed:', error);
      throw error;
    }
  }

  async cancelSubscription(userId) {
    if (!this.stripe) throw new Error('Stripe not configured');

    try {
      const user = await this.getUserSubscription(userId);
      if (!user.stripeSubscriptionId) {
        throw new Error('No active subscription found');
      }

      // Cancel at period end
      const subscription = await this.stripe.subscriptions.update(
        user.stripeSubscriptionId,
        { cancel_at_period_end: true }
      );

      // Update database
      await this.updateUserSubscription(userId, {
        status: 'canceling',
        cancelAtPeriodEnd: true
      });

      return subscription;
    } catch (error) {
      console.error('Subscription cancellation failed:', error);
      throw error;
    }
  }

  // Content Monetization
  async createContentSubscription(creatorId, supporterId, tierId) {
    if (!this.stripe) throw new Error('Stripe not configured');

    const tier = this.contentTiers.get(tierId);
    if (!tier) throw new Error('Invalid content tier');

    try {
      const customer = await this.getOrCreateStripeCustomer(supporterId);
      const creator = await this.getCreatorStripeAccount(creatorId);

      // Calculate application fee (platform takes 5%)
      const applicationFee = Math.round(tier.price * 100 * 0.05);

      const subscription = await this.stripe.subscriptions.create({
        customer: customer.id,
        items: [{
          price_data: {
            currency: 'usd',
            product_data: {
              name: `${tier.name} - Creator Support`
            },
            recurring: {
              interval: 'month'
            },
            unit_amount: Math.round(tier.price * 100)
          }
        }],
        application_fee_percent: 5,
        transfer_data: {
          destination: creator.stripeAccountId
        }
      });

      // Record in database
      await this.recordContentSubscription(creatorId, supporterId, {
        tierId,
        stripeSubscriptionId: subscription.id,
        status: subscription.status,
        benefits: tier.benefits
      });

      return subscription;
    } catch (error) {
      console.error('Content subscription creation failed:', error);
      throw error;
    }
  }

  // One-time Donations/Tips
  async processDonation(creatorId, supporterId, amount, message = '') {
    if (!this.stripe) throw new Error('Stripe not configured');

    try {
      const customer = await this.getOrCreateStripeCustomer(supporterId);
      const creator = await this.getCreatorStripeAccount(creatorId);

      // Create payment intent
      const paymentIntent = await this.stripe.paymentIntents.create({
        amount: Math.round(amount * 100), // Convert to cents
        currency: 'usd',
        customer: customer.id,
        application_fee_amount: Math.round(amount * 100 * 0.05), // 5% platform fee
        transfer_data: {
          destination: creator.stripeAccountId
        },
        metadata: {
          type: 'donation',
          creator_id: creatorId,
          supporter_id: supporterId,
          message: message.substring(0, 200) // Limit message length
        }
      });

      return paymentIntent;
    } catch (error) {
      console.error('Donation processing failed:', error);
      throw error;
    }
  }

  // Marketplace Transactions
  async processMarketplacePayment(buyerId, sellerId, itemId, amount) {
    if (!this.stripe) throw new Error('Stripe not configured');

    try {
      const customer = await this.getOrCreateStripeCustomer(buyerId);
      const seller = await this.getCreatorStripeAccount(sellerId);

      // Platform takes 10% for marketplace transactions
      const platformFee = Math.round(amount * 100 * 0.10);

      const paymentIntent = await this.stripe.paymentIntents.create({
        amount: Math.round(amount * 100),
        currency: 'usd',
        customer: customer.id,
        application_fee_amount: platformFee,
        transfer_data: {
          destination: seller.stripeAccountId
        },
        metadata: {
          type: 'marketplace_purchase',
          item_id: itemId,
          buyer_id: buyerId,
          seller_id: sellerId
        }
      });

      return paymentIntent;
    } catch (error) {
      console.error('Marketplace payment failed:', error);
      throw error;
    }
  }

  // Affiliate System
  async generateAffiliateLink(userId, campaignId = null) {
    const affiliateCode = crypto.randomBytes(8).toString('hex');
    
    const linkData = {
      affiliateId: userId,
      code: affiliateCode,
      campaignId,
      createdAt: new Date(),
      clicks: 0,
      conversions: 0,
      earnings: 0
    };

    // Save to database
    await this.saveAffiliateLink(linkData);

    const baseUrl = process.env.FRONTEND_URL || 'https://dmlog.activelog.com';
    const affiliateUrl = campaignId 
      ? `${baseUrl}/campaign/${campaignId}?ref=${affiliateCode}`
      : `${baseUrl}?ref=${affiliateCode}`;

    return {
      url: affiliateUrl,
      code: affiliateCode,
      ...linkData
    };
  }

  async trackAffiliateClick(affiliateCode, visitorId) {
    try {
      await this.incrementAffiliateClicks(affiliateCode);
      
      // Set tracking cookie (30 days default)
      const trackingData = {
        affiliateCode,
        visitorId,
        timestamp: Date.now(),
        expiresAt: Date.now() + (30 * 24 * 60 * 60 * 1000)
      };

      return this.createTrackingToken(trackingData);
    } catch (error) {
      console.error('Affiliate click tracking failed:', error);
    }
  }

  async processAffiliateConversion(trackingToken, purchaseAmount) {
    try {
      const trackingData = this.verifyTrackingToken(trackingToken);
      if (!trackingData) return;

      const program = this.affiliateProgram.get('standard');
      const commission = purchaseAmount * program.commission_rate;

      await this.recordAffiliateEarning({
        affiliateCode: trackingData.affiliateCode,
        purchaseAmount,
        commission,
        conversionDate: new Date()
      });

      return commission;
    } catch (error) {
      console.error('Affiliate conversion processing failed:', error);
    }
  }

  // Campaign Funding Goals
  async createFundingGoal(creatorId, goalData) {
    const goal = {
      id: crypto.randomUUID(),
      creatorId,
      title: goalData.title,
      description: goalData.description,
      targetAmount: goalData.targetAmount,
      currentAmount: 0,
      deadline: new Date(goalData.deadline),
      rewards: goalData.rewards || [],
      status: 'active',
      createdAt: new Date()
    };

    this.donationGoals.set(goal.id, goal);
    await this.saveFundingGoal(goal);

    return goal;
  }

  async contributeToFundingGoal(goalId, contributorId, amount) {
    const goal = this.donationGoals.get(goalId);
    if (!goal || goal.status !== 'active') {
      throw new Error('Invalid or inactive funding goal');
    }

    // Process payment
    const paymentIntent = await this.processDonation(
      goal.creatorId, 
      contributorId, 
      amount,
      `Contribution to: ${goal.title}`
    );

    if (paymentIntent.status === 'succeeded') {
      goal.currentAmount += amount;
      
      // Check if goal reached
      if (goal.currentAmount >= goal.targetAmount) {
        goal.status = 'completed';
        goal.completedAt = new Date();
      }

      await this.updateFundingGoal(goal);
    }

    return { goal, paymentIntent };
  }

  // Revenue Analytics
  async getRevenueAnalytics(userId, timeframe = 'month') {
    try {
      const analytics = {
        subscriptions: await this.getSubscriptionRevenue(userId, timeframe),
        donations: await this.getDonationRevenue(userId, timeframe),
        marketplace: await this.getMarketplaceRevenue(userId, timeframe),
        affiliates: await this.getAffiliateRevenue(userId, timeframe),
        total: 0
      };

      analytics.total = Object.values(analytics).reduce((sum, val) => {
        return sum + (typeof val === 'number' ? val : val.total || 0);
      }, 0);

      return analytics;
    } catch (error) {
      console.error('Revenue analytics failed:', error);
      return { error: error.message };
    }
  }

  // Payout Management
  async requestPayout(userId, amount) {
    if (!this.stripe) throw new Error('Stripe not configured');

    try {
      const creator = await this.getCreatorStripeAccount(userId);
      const balance = await this.getCreatorBalance(userId);

      if (amount > balance.available) {
        throw new Error('Insufficient balance for payout');
      }

      // Create payout
      const payout = await this.stripe.payouts.create({
        amount: Math.round(amount * 100),
        currency: 'usd',
        method: 'instant'
      }, {
        stripeAccount: creator.stripeAccountId
      });

      // Record payout
      await this.recordPayout(userId, {
        stripePayoutId: payout.id,
        amount,
        status: payout.status,
        requestedAt: new Date()
      });

      return payout;
    } catch (error) {
      console.error('Payout request failed:', error);
      throw error;
    }
  }

  // Helper Methods
  createTrackingToken(data) {
    return jwt.sign(data, process.env.JWT_SECRET, { expiresIn: '30d' });
  }

  verifyTrackingToken(token) {
    try {
      return jwt.verify(token, process.env.JWT_SECRET);
    } catch (error) {
      return null;
    }
  }

  async getOrCreateStripeCustomer(userId) {
    // Implementation would check database for existing customer
    // Create new customer if none exists
    const user = await this.getUserById(userId);
    
    if (user.stripeCustomerId) {
      return await this.stripe.customers.retrieve(user.stripeCustomerId);
    }

    const customer = await this.stripe.customers.create({
      email: user.email,
      metadata: { userId }
    });

    await this.updateUserStripeData(userId, { stripeCustomerId: customer.id });
    return customer;
  }

  async getCreatorStripeAccount(creatorId) {
    // Implementation would check database for existing Stripe Connect account
    const creator = await this.getUserById(creatorId);
    
    if (!creator.stripeAccountId) {
      throw new Error('Creator has not set up payouts');
    }

    return creator;
  }

  // Database interaction methods (simplified - would use actual models)
  async getUserById(userId) {
    return await mongoose.model('User').findById(userId);
  }

  async getUserSubscription(userId) {
    return await mongoose.model('User').findById(userId).select('subscription');
  }

  async updateUserSubscription(userId, subscriptionData) {
    return await mongoose.model('User').findByIdAndUpdate(
      userId, 
      { subscription: subscriptionData },
      { new: true }
    );
  }

  async updateUserStripeData(userId, stripeData) {
    return await mongoose.model('User').findByIdAndUpdate(userId, stripeData);
  }

  async saveAffiliateLink(linkData) {
    return await mongoose.model('AffiliateLink').create(linkData);
  }

  async incrementAffiliateClicks(affiliateCode) {
    return await mongoose.model('AffiliateLink').findOneAndUpdate(
      { code: affiliateCode },
      { $inc: { clicks: 1 } }
    );
  }

  async recordAffiliateEarning(earningData) {
    return await mongoose.model('AffiliateEarning').create(earningData);
  }

  async saveFundingGoal(goal) {
    return await mongoose.model('FundingGoal').create(goal);
  }

  async updateFundingGoal(goal) {
    return await mongoose.model('FundingGoal').findByIdAndUpdate(goal.id, goal);
  }

  async recordContentSubscription(creatorId, supporterId, subscriptionData) {
    return await mongoose.model('ContentSubscription').create({
      creatorId,
      supporterId,
      ...subscriptionData
    });
  }

  async recordPayout(userId, payoutData) {
    return await mongoose.model('Payout').create({
      userId,
      ...payoutData
    });
  }

  // Revenue query methods
  async getSubscriptionRevenue(userId, timeframe) {
    // Implementation would query subscription revenue
    return { total: 0, count: 0, growth: 0 };
  }

  async getDonationRevenue(userId, timeframe) {
    // Implementation would query donation revenue  
    return { total: 0, count: 0, growth: 0 };
  }

  async getMarketplaceRevenue(userId, timeframe) {
    // Implementation would query marketplace revenue
    return { total: 0, count: 0, growth: 0 };
  }

  async getAffiliateRevenue(userId, timeframe) {
    // Implementation would query affiliate revenue
    return { total: 0, count: 0, growth: 0 };
  }

  async getCreatorBalance(userId) {
    // Implementation would calculate available balance
    return { available: 0, pending: 0 };
  }
}

export default MonetizationService;