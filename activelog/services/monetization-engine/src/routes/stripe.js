const express = require('express');
const { stripe, PRICING_PLANS, WEBHOOK_EVENTS } = require('../config/stripe');
const logger = require('../utils/logger');
const StripeService = require('../services/StripeService');
const { authMiddleware } = require('../middleware/auth');

const router = express.Router();
const stripeService = new StripeService();

// Create payment intent
router.post('/payment-intent', authMiddleware, async (req, res) => {
  try {
    const { amount, currency = 'usd', metadata = {}, customerId } = req.body;
    
    if (!amount || amount <= 0) {
      return res.status(400).json({
        error: 'Invalid amount. Amount must be greater than 0.'
      });
    }

    const paymentIntent = await stripeService.createPaymentIntent({
      amount,
      currency,
      customer: customerId,
      metadata: {
        userId: req.user.id,
        ...metadata
      },
      automatic_payment_methods: {
        enabled: true
      }
    });

    logger.payment('Payment intent created', {
      paymentIntentId: paymentIntent.id,
      amount,
      currency,
      userId: req.user.id,
      customerId
    });

    res.json({
      clientSecret: paymentIntent.client_secret,
      paymentIntentId: paymentIntent.id
    });
  } catch (error) {
    logger.error('Failed to create payment intent:', error);
    res.status(500).json({
      error: 'Failed to create payment intent',
      message: error.message
    });
  }
});

// Create subscription
router.post('/subscription', authMiddleware, async (req, res) => {
  try {
    const { plan, paymentMethodId, customerId, trialDays = 0 } = req.body;
    
    if (!PRICING_PLANS[plan]) {
      return res.status(400).json({
        error: 'Invalid pricing plan'
      });
    }

    if (plan === 'free') {
      return res.status(400).json({
        error: 'Free plan does not require Stripe subscription'
      });
    }

    const subscription = await stripeService.createSubscription({
      customer: customerId,
      items: [{
        price: PRICING_PLANS[plan].priceId
      }],
      payment_behavior: 'default_incomplete',
      payment_settings: {
        save_default_payment_method: 'on_subscription'
      },
      expand: ['latest_invoice.payment_intent'],
      trial_period_days: trialDays > 0 ? trialDays : undefined,
      metadata: {
        userId: req.user.id,
        plan
      }
    });

    if (paymentMethodId) {
      await stripeService.attachPaymentMethod(paymentMethodId, customerId);
      await stripeService.updateCustomerDefaultPaymentMethod(customerId, paymentMethodId);
    }

    logger.subscription('Subscription created', {
      subscriptionId: subscription.id,
      plan,
      userId: req.user.id,
      customerId,
      trialDays
    });

    res.json({
      subscriptionId: subscription.id,
      clientSecret: subscription.latest_invoice.payment_intent.client_secret,
      status: subscription.status
    });
  } catch (error) {
    logger.error('Failed to create subscription:', error);
    res.status(500).json({
      error: 'Failed to create subscription',
      message: error.message
    });
  }
});

// Update subscription
router.put('/subscription/:subscriptionId', authMiddleware, async (req, res) => {
  try {
    const { subscriptionId } = req.params;
    const { plan, prorate = true } = req.body;
    
    if (!PRICING_PLANS[plan]) {
      return res.status(400).json({
        error: 'Invalid pricing plan'
      });
    }

    const subscription = await stripeService.updateSubscription(subscriptionId, {
      items: [{
        id: subscriptionId,
        price: PRICING_PLANS[plan].priceId
      }],
      proration_behavior: prorate ? 'create_prorations' : 'none',
      metadata: {
        userId: req.user.id,
        plan,
        updatedAt: new Date().toISOString()
      }
    });

    logger.subscription('Subscription updated', {
      subscriptionId,
      newPlan: plan,
      userId: req.user.id,
      prorate
    });

    res.json({
      subscriptionId: subscription.id,
      status: subscription.status,
      currentPeriodEnd: subscription.current_period_end
    });
  } catch (error) {
    logger.error('Failed to update subscription:', error);
    res.status(500).json({
      error: 'Failed to update subscription',
      message: error.message
    });
  }
});

// Cancel subscription
router.delete('/subscription/:subscriptionId', authMiddleware, async (req, res) => {
  try {
    const { subscriptionId } = req.params;
    const { immediately = false } = req.query;
    
    const subscription = await stripeService.cancelSubscription(subscriptionId, {
      cancel_at_period_end: !immediately,
      metadata: {
        userId: req.user.id,
        canceledAt: new Date().toISOString(),
        cancelType: immediately ? 'immediate' : 'end_of_period'
      }
    });

    logger.subscription('Subscription canceled', {
      subscriptionId,
      userId: req.user.id,
      immediately,
      cancelAt: subscription.cancel_at
    });

    res.json({
      subscriptionId: subscription.id,
      status: subscription.status,
      cancelAt: subscription.cancel_at,
      currentPeriodEnd: subscription.current_period_end
    });
  } catch (error) {
    logger.error('Failed to cancel subscription:', error);
    res.status(500).json({
      error: 'Failed to cancel subscription',
      message: error.message
    });
  }
});

// Create customer
router.post('/customer', authMiddleware, async (req, res) => {
  try {
    const { email, name, phone, address, metadata = {} } = req.body;
    
    const customer = await stripeService.createCustomer({
      email,
      name,
      phone,
      address,
      metadata: {
        userId: req.user.id,
        ...metadata
      }
    });

    logger.audit('Stripe customer created', {
      customerId: customer.id,
      userId: req.user.id,
      email
    });

    res.json({
      customerId: customer.id,
      email: customer.email,
      name: customer.name
    });
  } catch (error) {
    logger.error('Failed to create customer:', error);
    res.status(500).json({
      error: 'Failed to create customer',
      message: error.message
    });
  }
});

// Create setup intent for saving payment method
router.post('/setup-intent', authMiddleware, async (req, res) => {
  try {
    const { customerId, usage = 'off_session' } = req.body;
    
    const setupIntent = await stripeService.createSetupIntent({
      customer: customerId,
      usage,
      payment_method_types: ['card'],
      metadata: {
        userId: req.user.id
      }
    });

    logger.payment('Setup intent created', {
      setupIntentId: setupIntent.id,
      customerId,
      userId: req.user.id
    });

    res.json({
      clientSecret: setupIntent.client_secret,
      setupIntentId: setupIntent.id
    });
  } catch (error) {
    logger.error('Failed to create setup intent:', error);
    res.status(500).json({
      error: 'Failed to create setup intent',
      message: error.message
    });
  }
});

// List customer payment methods
router.get('/customer/:customerId/payment-methods', authMiddleware, async (req, res) => {
  try {
    const { customerId } = req.params;
    const { type = 'card' } = req.query;
    
    const paymentMethods = await stripeService.listPaymentMethods(customerId, type);
    
    res.json({
      paymentMethods: paymentMethods.data.map(pm => ({
        id: pm.id,
        type: pm.type,
        card: pm.card ? {
          brand: pm.card.brand,
          last4: pm.card.last4,
          expMonth: pm.card.exp_month,
          expYear: pm.card.exp_year
        } : null,
        created: pm.created
      }))
    });
  } catch (error) {
    logger.error('Failed to list payment methods:', error);
    res.status(500).json({
      error: 'Failed to list payment methods',
      message: error.message
    });
  }
});

// Detach payment method
router.delete('/payment-method/:paymentMethodId', authMiddleware, async (req, res) => {
  try {
    const { paymentMethodId } = req.params;
    
    const paymentMethod = await stripeService.detachPaymentMethod(paymentMethodId);
    
    logger.audit('Payment method detached', {
      paymentMethodId,
      userId: req.user.id
    });

    res.json({
      paymentMethodId: paymentMethod.id,
      status: 'detached'
    });
  } catch (error) {
    logger.error('Failed to detach payment method:', error);
    res.status(500).json({
      error: 'Failed to detach payment method',
      message: error.message
    });
  }
});

// Webhook endpoint for Stripe events
router.post('/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
  const sig = req.headers['stripe-signature'];
  
  let event;
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, process.env.STRIPE_WEBHOOK_SECRET);
  } catch (err) {
    logger.error('Webhook signature verification failed:', err);
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  try {
    await stripeService.handleWebhook(event);
    
    logger.audit('Stripe webhook processed', {
      eventId: event.id,
      eventType: event.type,
      objectId: event.data.object.id
    });
    
    res.json({ received: true });
  } catch (error) {
    logger.error('Webhook processing failed:', error);
    res.status(500).json({
      error: 'Webhook processing failed',
      message: error.message
    });
  }
});

// Get pricing plans
router.get('/pricing', (req, res) => {
  const plans = Object.entries(PRICING_PLANS).map(([key, plan]) => ({
    id: key,
    name: plan.name,
    price: plan.price,
    interval: plan.interval || null,
    features: plan.features
  }));

  res.json({ plans });
});

// Get customer billing history
router.get('/customer/:customerId/invoices', authMiddleware, async (req, res) => {
  try {
    const { customerId } = req.params;
    const { limit = 10, starting_after } = req.query;
    
    const invoices = await stripeService.listInvoices({
      customer: customerId,
      limit: parseInt(limit),
      starting_after
    });

    res.json({
      invoices: invoices.data.map(invoice => ({
        id: invoice.id,
        number: invoice.number,
        status: invoice.status,
        amount: invoice.total,
        currency: invoice.currency,
        created: invoice.created,
        periodStart: invoice.period_start,
        periodEnd: invoice.period_end,
        invoiceUrl: invoice.hosted_invoice_url,
        pdfUrl: invoice.invoice_pdf
      })),
      hasMore: invoices.has_more
    });
  } catch (error) {
    logger.error('Failed to fetch invoices:', error);
    res.status(500).json({
      error: 'Failed to fetch invoices',
      message: error.message
    });
  }
});

module.exports = router;