const { stripe } = require('../config/stripe');
const logger = require('../utils/logger');
const database = require('../config/database');

class StripeService {
  
  // Payment Intent methods
  async createPaymentIntent(params) {
    try {
      const paymentIntent = await stripe.paymentIntents.create(params);
      
      // Store payment intent in database
      await database('payment_intents').insert({
        stripe_payment_intent_id: paymentIntent.id,
        amount: paymentIntent.amount,
        currency: paymentIntent.currency,
        status: paymentIntent.status,
        customer_id: paymentIntent.customer,
        metadata: JSON.stringify(paymentIntent.metadata),
        created_at: new Date(paymentIntent.created * 1000),
        updated_at: new Date()
      });
      
      return paymentIntent;
    } catch (error) {
      logger.error('StripeService: Failed to create payment intent', error);
      throw error;
    }
  }
  
  async updatePaymentIntent(paymentIntentId, params) {
    try {
      const paymentIntent = await stripe.paymentIntents.update(paymentIntentId, params);
      
      // Update payment intent in database
      await database('payment_intents')
        .where('stripe_payment_intent_id', paymentIntentId)
        .update({
          status: paymentIntent.status,
          metadata: JSON.stringify(paymentIntent.metadata),
          updated_at: new Date()
        });
      
      return paymentIntent;
    } catch (error) {
      logger.error('StripeService: Failed to update payment intent', error);
      throw error;
    }
  }
  
  // Customer methods
  async createCustomer(params) {
    try {
      const customer = await stripe.customers.create(params);
      
      // Store customer in database
      await database('stripe_customers').insert({
        stripe_customer_id: customer.id,
        email: customer.email,
        name: customer.name,
        phone: customer.phone,
        address: customer.address ? JSON.stringify(customer.address) : null,
        metadata: JSON.stringify(customer.metadata),
        created_at: new Date(customer.created * 1000)
      });
      
      return customer;
    } catch (error) {
      logger.error('StripeService: Failed to create customer', error);
      throw error;
    }
  }
  
  async updateCustomer(customerId, params) {
    try {
      const customer = await stripe.customers.update(customerId, params);
      
      // Update customer in database
      await database('stripe_customers')
        .where('stripe_customer_id', customerId)
        .update({
          email: customer.email,
          name: customer.name,
          phone: customer.phone,
          address: customer.address ? JSON.stringify(customer.address) : null,
          metadata: JSON.stringify(customer.metadata),
          updated_at: new Date()
        });
      
      return customer;
    } catch (error) {
      logger.error('StripeService: Failed to update customer', error);
      throw error;
    }
  }
  
  // Subscription methods
  async createSubscription(params) {
    try {
      const subscription = await stripe.subscriptions.create(params);
      
      // Store subscription in database
      await database('subscriptions').insert({
        stripe_subscription_id: subscription.id,
        customer_id: subscription.customer,
        status: subscription.status,
        current_period_start: new Date(subscription.current_period_start * 1000),
        current_period_end: new Date(subscription.current_period_end * 1000),
        trial_start: subscription.trial_start ? new Date(subscription.trial_start * 1000) : null,
        trial_end: subscription.trial_end ? new Date(subscription.trial_end * 1000) : null,
        cancel_at: subscription.cancel_at ? new Date(subscription.cancel_at * 1000) : null,
        canceled_at: subscription.canceled_at ? new Date(subscription.canceled_at * 1000) : null,
        metadata: JSON.stringify(subscription.metadata),
        created_at: new Date(subscription.created * 1000),
        updated_at: new Date()
      });
      
      return subscription;
    } catch (error) {
      logger.error('StripeService: Failed to create subscription', error);
      throw error;
    }
  }
  
  async updateSubscription(subscriptionId, params) {
    try {
      const subscription = await stripe.subscriptions.update(subscriptionId, params);
      
      // Update subscription in database
      await database('subscriptions')
        .where('stripe_subscription_id', subscriptionId)
        .update({
          status: subscription.status,
          current_period_start: new Date(subscription.current_period_start * 1000),
          current_period_end: new Date(subscription.current_period_end * 1000),
          trial_start: subscription.trial_start ? new Date(subscription.trial_start * 1000) : null,
          trial_end: subscription.trial_end ? new Date(subscription.trial_end * 1000) : null,
          cancel_at: subscription.cancel_at ? new Date(subscription.cancel_at * 1000) : null,
          canceled_at: subscription.canceled_at ? new Date(subscription.canceled_at * 1000) : null,
          metadata: JSON.stringify(subscription.metadata),
          updated_at: new Date()
        });
      
      return subscription;
    } catch (error) {
      logger.error('StripeService: Failed to update subscription', error);
      throw error;
    }
  }
  
  async cancelSubscription(subscriptionId, params = {}) {
    try {
      const subscription = await stripe.subscriptions.update(subscriptionId, {
        cancel_at_period_end: params.cancel_at_period_end || false,
        metadata: params.metadata || {}
      });
      
      // Update subscription in database
      await database('subscriptions')
        .where('stripe_subscription_id', subscriptionId)
        .update({
          status: subscription.status,
          cancel_at: subscription.cancel_at ? new Date(subscription.cancel_at * 1000) : null,
          canceled_at: subscription.canceled_at ? new Date(subscription.canceled_at * 1000) : null,
          metadata: JSON.stringify(subscription.metadata),
          updated_at: new Date()
        });
      
      return subscription;
    } catch (error) {
      logger.error('StripeService: Failed to cancel subscription', error);
      throw error;
    }
  }
  
  // Setup Intent methods
  async createSetupIntent(params) {
    try {
      return await stripe.setupIntents.create(params);
    } catch (error) {
      logger.error('StripeService: Failed to create setup intent', error);
      throw error;
    }
  }
  
  // Payment Method methods
  async attachPaymentMethod(paymentMethodId, customerId) {
    try {
      return await stripe.paymentMethods.attach(paymentMethodId, {
        customer: customerId
      });
    } catch (error) {
      logger.error('StripeService: Failed to attach payment method', error);
      throw error;
    }
  }
  
  async detachPaymentMethod(paymentMethodId) {
    try {
      return await stripe.paymentMethods.detach(paymentMethodId);
    } catch (error) {
      logger.error('StripeService: Failed to detach payment method', error);
      throw error;
    }
  }
  
  async listPaymentMethods(customerId, type = 'card') {
    try {
      return await stripe.paymentMethods.list({
        customer: customerId,
        type
      });
    } catch (error) {
      logger.error('StripeService: Failed to list payment methods', error);
      throw error;
    }
  }
  
  async updateCustomerDefaultPaymentMethod(customerId, paymentMethodId) {
    try {
      return await stripe.customers.update(customerId, {
        invoice_settings: {
          default_payment_method: paymentMethodId
        }
      });
    } catch (error) {
      logger.error('StripeService: Failed to update default payment method', error);
      throw error;
    }
  }
  
  // Invoice methods
  async listInvoices(params) {
    try {
      return await stripe.invoices.list(params);
    } catch (error) {
      logger.error('StripeService: Failed to list invoices', error);
      throw error;
    }
  }
  
  async createInvoice(params) {
    try {
      const invoice = await stripe.invoices.create(params);
      await stripe.invoices.finalizeInvoice(invoice.id);
      return invoice;
    } catch (error) {
      logger.error('StripeService: Failed to create invoice', error);
      throw error;
    }
  }
  
  // Usage Record methods for metered billing
  async createUsageRecord(subscriptionItemId, quantity, timestamp = null) {
    try {
      return await stripe.subscriptionItems.createUsageRecord(subscriptionItemId, {
        quantity,
        timestamp: timestamp || Math.floor(Date.now() / 1000),
        action: 'increment'
      });
    } catch (error) {
      logger.error('StripeService: Failed to create usage record', error);
      throw error;
    }
  }
  
  // Webhook handler
  async handleWebhook(event) {
    try {
      switch (event.type) {
        case 'payment_intent.succeeded':
          await this.handlePaymentIntentSucceeded(event.data.object);
          break;
          
        case 'payment_intent.payment_failed':
          await this.handlePaymentIntentFailed(event.data.object);
          break;
          
        case 'invoice.payment_succeeded':
          await this.handleInvoicePaymentSucceeded(event.data.object);
          break;
          
        case 'invoice.payment_failed':
          await this.handleInvoicePaymentFailed(event.data.object);
          break;
          
        case 'customer.subscription.created':
          await this.handleSubscriptionCreated(event.data.object);
          break;
          
        case 'customer.subscription.updated':
          await this.handleSubscriptionUpdated(event.data.object);
          break;
          
        case 'customer.subscription.deleted':
          await this.handleSubscriptionDeleted(event.data.object);
          break;
          
        case 'setup_intent.succeeded':
          await this.handleSetupIntentSucceeded(event.data.object);
          break;
          
        default:
          logger.info(`Unhandled webhook event type: ${event.type}`);
      }
    } catch (error) {
      logger.error('StripeService: Webhook handling failed', error);
      throw error;
    }
  }
  
  // Webhook event handlers
  async handlePaymentIntentSucceeded(paymentIntent) {
    await database('payment_intents')
      .where('stripe_payment_intent_id', paymentIntent.id)
      .update({
        status: 'succeeded',
        updated_at: new Date()
      });
      
    logger.payment('Payment succeeded', {
      paymentIntentId: paymentIntent.id,
      amount: paymentIntent.amount,
      currency: paymentIntent.currency
    });
  }
  
  async handlePaymentIntentFailed(paymentIntent) {
    await database('payment_intents')
      .where('stripe_payment_intent_id', paymentIntent.id)
      .update({
        status: 'failed',
        updated_at: new Date()
      });
      
    logger.payment('Payment failed', {
      paymentIntentId: paymentIntent.id,
      amount: paymentIntent.amount,
      currency: paymentIntent.currency,
      lastPaymentError: paymentIntent.last_payment_error
    });
  }
  
  async handleInvoicePaymentSucceeded(invoice) {
    if (invoice.subscription) {
      await database('subscriptions')
        .where('stripe_subscription_id', invoice.subscription)
        .update({
          status: 'active',
          updated_at: new Date()
        });
    }
    
    logger.billing('Invoice payment succeeded', {
      invoiceId: invoice.id,
      subscriptionId: invoice.subscription,
      amount: invoice.amount_paid
    });
  }
  
  async handleInvoicePaymentFailed(invoice) {
    if (invoice.subscription) {
      await database('subscriptions')
        .where('stripe_subscription_id', invoice.subscription)
        .update({
          status: 'past_due',
          updated_at: new Date()
        });
    }
    
    logger.billing('Invoice payment failed', {
      invoiceId: invoice.id,
      subscriptionId: invoice.subscription,
      amount: invoice.amount_due
    });
  }
  
  async handleSubscriptionCreated(subscription) {
    await database('subscriptions')
      .where('stripe_subscription_id', subscription.id)
      .update({
        status: subscription.status,
        updated_at: new Date()
      });
      
    logger.subscription('Subscription created via webhook', {
      subscriptionId: subscription.id,
      customerId: subscription.customer,
      status: subscription.status
    });
  }
  
  async handleSubscriptionUpdated(subscription) {
    await database('subscriptions')
      .where('stripe_subscription_id', subscription.id)
      .update({
        status: subscription.status,
        current_period_start: new Date(subscription.current_period_start * 1000),
        current_period_end: new Date(subscription.current_period_end * 1000),
        cancel_at: subscription.cancel_at ? new Date(subscription.cancel_at * 1000) : null,
        canceled_at: subscription.canceled_at ? new Date(subscription.canceled_at * 1000) : null,
        updated_at: new Date()
      });
      
    logger.subscription('Subscription updated via webhook', {
      subscriptionId: subscription.id,
      status: subscription.status
    });
  }
  
  async handleSubscriptionDeleted(subscription) {
    await database('subscriptions')
      .where('stripe_subscription_id', subscription.id)
      .update({
        status: 'canceled',
        canceled_at: new Date(subscription.canceled_at * 1000),
        updated_at: new Date()
      });
      
    logger.subscription('Subscription deleted via webhook', {
      subscriptionId: subscription.id,
      canceledAt: subscription.canceled_at
    });
  }
  
  async handleSetupIntentSucceeded(setupIntent) {
    logger.payment('Setup intent succeeded', {
      setupIntentId: setupIntent.id,
      customerId: setupIntent.customer,
      paymentMethodId: setupIntent.payment_method
    });
  }
}

module.exports = StripeService;