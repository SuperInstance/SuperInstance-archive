import { Decimal } from 'decimal.js';
import { v4 as uuidv4 } from 'uuid';
import { EventEmitter } from 'events';
import Stripe from 'stripe';
import * as paypal from 'paypal-rest-sdk';
import { 
  PaymentMethod, 
  Payment, 
  PaymentProvider, 
  PaymentStatus, 
  PaymentPurpose,
  CurrencyCode 
} from '../types';

export class PaymentGatewayService extends EventEmitter {
  private stripe: Stripe;
  private paypalConfigured: boolean = false;

  constructor(
    stripeSecretKey: string,
    paypalConfig?: {
      clientId: string;
      clientSecret: string;
      environment: 'sandbox' | 'production';
    }
  ) {
    super();
    
    // Initialize Stripe
    this.stripe = new Stripe(stripeSecretKey, {
      apiVersion: '2023-10-16'
    });

    // Initialize PayPal if config provided
    if (paypalConfig) {
      paypal.configure({
        mode: paypalConfig.environment,
        client_id: paypalConfig.clientId,
        client_secret: paypalConfig.clientSecret
      });
      this.paypalConfigured = true;
    }
  }

  /**
   * Add a payment method for a user
   */
  async addPaymentMethod(
    userId: string,
    provider: PaymentProvider,
    token: string, // Payment token from frontend
    isDefault: boolean = false
  ): Promise<PaymentMethod> {
    let paymentMethod: PaymentMethod;

    switch (provider) {
      case 'stripe':
        paymentMethod = await this.addStripePaymentMethod(userId, token, isDefault);
        break;
      case 'paypal':
        paymentMethod = await this.addPayPalPaymentMethod(userId, token, isDefault);
        break;
      case 'google_pay':
        paymentMethod = await this.addGooglePayMethod(userId, token, isDefault);
        break;
      case 'venmo':
        paymentMethod = await this.addVenmoMethod(userId, token, isDefault);
        break;
      case 'zelle':
        paymentMethod = await this.addZelleMethod(userId, token, isDefault);
        break;
      default:
        throw new Error(`Unsupported payment provider: ${provider}`);
    }

    this.emit('paymentMethodAdded', { userId, paymentMethod });
    return paymentMethod;
  }

  /**
   * Process a payment
   */
  async processPayment(
    userId: string,
    amount: Decimal,
    currency: CurrencyCode,
    paymentMethodId: string,
    purpose: PaymentPurpose,
    purposeId: string,
    metadata?: Record<string, any>
  ): Promise<Payment> {
    const paymentMethod = await this.getPaymentMethod(paymentMethodId);
    if (!paymentMethod || paymentMethod.userId !== userId) {
      throw new Error('Invalid payment method');
    }

    let payment: Payment;

    switch (paymentMethod.provider) {
      case 'stripe':
        payment = await this.processStripePayment(
          userId, amount, currency, paymentMethod, purpose, purposeId, metadata
        );
        break;
      case 'paypal':
        payment = await this.processPayPalPayment(
          userId, amount, currency, paymentMethod, purpose, purposeId, metadata
        );
        break;
      case 'google_pay':
        payment = await this.processGooglePayPayment(
          userId, amount, currency, paymentMethod, purpose, purposeId, metadata
        );
        break;
      case 'venmo':
        payment = await this.processVenmoPayment(
          userId, amount, currency, paymentMethod, purpose, purposeId, metadata
        );
        break;
      case 'zelle':
        payment = await this.processZellePayment(
          userId, amount, currency, paymentMethod, purpose, purposeId, metadata
        );
        break;
      default:
        throw new Error(`Unsupported payment provider: ${paymentMethod.provider}`);
    }

    this.emit('paymentProcessed', { payment });
    return payment;
  }

  /**
   * Refund a payment
   */
  async refundPayment(
    paymentId: string,
    amount?: Decimal,
    reason?: string
  ): Promise<Payment> {
    const payment = await this.getPayment(paymentId);
    if (!payment) {
      throw new Error('Payment not found');
    }

    if (payment.status !== 'completed') {
      throw new Error('Can only refund completed payments');
    }

    const refundAmount = amount || payment.amount;

    let updatedPayment: Payment;

    switch (payment.provider) {
      case 'stripe':
        updatedPayment = await this.refundStripePayment(payment, refundAmount, reason);
        break;
      case 'paypal':
        updatedPayment = await this.refundPayPalPayment(payment, refundAmount, reason);
        break;
      default:
        throw new Error(`Refunds not supported for provider: ${payment.provider}`);
    }

    this.emit('paymentRefunded', { payment: updatedPayment, refundAmount, reason });
    return updatedPayment;
  }

  /**
   * Get user's payment methods
   */
  async getUserPaymentMethods(userId: string): Promise<PaymentMethod[]> {
    // Mock implementation - would fetch from database
    const mockPaymentMethods: PaymentMethod[] = [
      {
        id: uuidv4(),
        userId,
        type: 'card',
        provider: 'stripe',
        providerPaymentMethodId: 'pm_mock_stripe',
        isDefault: true,
        last4: '4242',
        expiryMonth: 12,
        expiryYear: 2025,
        brand: 'visa',
        country: 'US',
        isActive: true,
        createdAt: new Date()
      }
    ];

    return mockPaymentMethods;
  }

  /**
   * Set default payment method
   */
  async setDefaultPaymentMethod(userId: string, paymentMethodId: string): Promise<void> {
    // Update database to set new default and unset others
    this.emit('defaultPaymentMethodChanged', { userId, paymentMethodId });
  }

  /**
   * Remove a payment method
   */
  async removePaymentMethod(userId: string, paymentMethodId: string): Promise<void> {
    const paymentMethod = await this.getPaymentMethod(paymentMethodId);
    
    if (!paymentMethod || paymentMethod.userId !== userId) {
      throw new Error('Payment method not found');
    }

    // Remove from provider
    switch (paymentMethod.provider) {
      case 'stripe':
        await this.stripe.paymentMethods.detach(paymentMethod.providerPaymentMethodId);
        break;
      case 'paypal':
        // PayPal removal logic
        break;
    }

    // Mark as inactive in database
    this.emit('paymentMethodRemoved', { userId, paymentMethodId });
  }

  /**
   * Get supported payment methods by country
   */
  getSupportedPaymentMethods(countryCode: string): {
    providers: PaymentProvider[];
    currencies: CurrencyCode[];
  } {
    const countrySupport: Record<string, {
      providers: PaymentProvider[];
      currencies: CurrencyCode[];
    }> = {
      'US': {
        providers: ['stripe', 'paypal', 'google_pay', 'venmo', 'zelle'],
        currencies: ['USD']
      },
      'CA': {
        providers: ['stripe', 'paypal', 'google_pay'],
        currencies: ['CAD', 'USD']
      },
      'GB': {
        providers: ['stripe', 'paypal', 'google_pay'],
        currencies: ['GBP', 'EUR', 'USD']
      },
      'DE': {
        providers: ['stripe', 'paypal', 'google_pay'],
        currencies: ['EUR', 'USD']
      },
      'JP': {
        providers: ['stripe', 'paypal', 'google_pay'],
        currencies: ['JPY', 'USD']
      }
    };

    return countrySupport[countryCode] || {
      providers: ['stripe', 'paypal'],
      currencies: ['USD']
    };
  }

  // Private Stripe methods

  private async addStripePaymentMethod(
    userId: string,
    token: string,
    isDefault: boolean
  ): Promise<PaymentMethod> {
    try {
      const stripePaymentMethod = await this.stripe.paymentMethods.retrieve(token);
      
      // Attach to customer (create customer if needed)
      const customer = await this.getOrCreateStripeCustomer(userId);
      await this.stripe.paymentMethods.attach(token, { customer: customer.id });

      const paymentMethod: PaymentMethod = {
        id: uuidv4(),
        userId,
        type: stripePaymentMethod.type === 'card' ? 'card' : 'bank_account',
        provider: 'stripe',
        providerPaymentMethodId: stripePaymentMethod.id,
        isDefault,
        last4: stripePaymentMethod.card?.last4,
        expiryMonth: stripePaymentMethod.card?.exp_month,
        expiryYear: stripePaymentMethod.card?.exp_year,
        brand: stripePaymentMethod.card?.brand,
        country: stripePaymentMethod.card?.country,
        isActive: true,
        createdAt: new Date()
      };

      return paymentMethod;
    } catch (error) {
      throw new Error(`Failed to add Stripe payment method: ${error}`);
    }
  }

  private async processStripePayment(
    userId: string,
    amount: Decimal,
    currency: CurrencyCode,
    paymentMethod: PaymentMethod,
    purpose: PaymentPurpose,
    purposeId: string,
    metadata?: Record<string, any>
  ): Promise<Payment> {
    try {
      const customer = await this.getOrCreateStripeCustomer(userId);
      
      const paymentIntent = await this.stripe.paymentIntents.create({
        amount: amount.mul(100).toNumber(), // Convert to cents
        currency: currency.toLowerCase(),
        customer: customer.id,
        payment_method: paymentMethod.providerPaymentMethodId,
        confirmation_method: 'manual',
        confirm: true,
        metadata: {
          userId,
          purpose,
          purposeId,
          ...metadata
        }
      });

      const payment: Payment = {
        id: uuidv4(),
        userId,
        amount,
        currency,
        status: this.mapStripeStatus(paymentIntent.status),
        provider: 'stripe',
        providerTransactionId: paymentIntent.id,
        paymentMethodId: paymentMethod.id,
        purpose,
        purposeId,
        createdAt: new Date(),
        updatedAt: new Date(),
        metadata
      };

      return payment;
    } catch (error) {
      throw new Error(`Stripe payment failed: ${error}`);
    }
  }

  private async refundStripePayment(
    payment: Payment,
    amount: Decimal,
    reason?: string
  ): Promise<Payment> {
    try {
      const refund = await this.stripe.refunds.create({
        payment_intent: payment.providerTransactionId,
        amount: amount.mul(100).toNumber(),
        reason: reason === 'fraudulent' ? 'fraudulent' : 'requested_by_customer'
      });

      payment.status = amount.equals(payment.amount) ? 'refunded' : 'completed';
      payment.updatedAt = new Date();
      payment.metadata = {
        ...payment.metadata,
        refund: {
          id: refund.id,
          amount: amount.toString(),
          reason
        }
      };

      return payment;
    } catch (error) {
      throw new Error(`Stripe refund failed: ${error}`);
    }
  }

  private async getOrCreateStripeCustomer(userId: string): Promise<Stripe.Customer> {
    // Check if customer exists (would use database lookup)
    try {
      const customers = await this.stripe.customers.list({
        metadata: { userId },
        limit: 1
      });

      if (customers.data.length > 0) {
        return customers.data[0];
      }

      // Create new customer
      return await this.stripe.customers.create({
        metadata: { userId }
      });
    } catch (error) {
      throw new Error(`Failed to create Stripe customer: ${error}`);
    }
  }

  private mapStripeStatus(stripeStatus: string): PaymentStatus {
    switch (stripeStatus) {
      case 'succeeded':
        return 'completed';
      case 'processing':
        return 'processing';
      case 'requires_payment_method':
      case 'requires_confirmation':
        return 'pending';
      case 'canceled':
        return 'canceled';
      default:
        return 'failed';
    }
  }

  // Private PayPal methods

  private async addPayPalPaymentMethod(
    userId: string,
    token: string,
    isDefault: boolean
  ): Promise<PaymentMethod> {
    if (!this.paypalConfigured) {
      throw new Error('PayPal not configured');
    }

    // PayPal payment method integration
    const paymentMethod: PaymentMethod = {
      id: uuidv4(),
      userId,
      type: 'digital_wallet',
      provider: 'paypal',
      providerPaymentMethodId: token,
      isDefault,
      isActive: true,
      createdAt: new Date()
    };

    return paymentMethod;
  }

  private async processPayPalPayment(
    userId: string,
    amount: Decimal,
    currency: CurrencyCode,
    paymentMethod: PaymentMethod,
    purpose: PaymentPurpose,
    purposeId: string,
    metadata?: Record<string, any>
  ): Promise<Payment> {
    if (!this.paypalConfigured) {
      throw new Error('PayPal not configured');
    }

    // Mock PayPal payment processing
    const payment: Payment = {
      id: uuidv4(),
      userId,
      amount,
      currency,
      status: 'completed',
      provider: 'paypal',
      providerTransactionId: `PAYPAL_${uuidv4()}`,
      paymentMethodId: paymentMethod.id,
      purpose,
      purposeId,
      createdAt: new Date(),
      updatedAt: new Date(),
      metadata
    };

    return payment;
  }

  private async refundPayPalPayment(
    payment: Payment,
    amount: Decimal,
    reason?: string
  ): Promise<Payment> {
    // PayPal refund logic
    payment.status = 'refunded';
    payment.updatedAt = new Date();
    return payment;
  }

  // Private Google Pay methods

  private async addGooglePayMethod(
    userId: string,
    token: string,
    isDefault: boolean
  ): Promise<PaymentMethod> {
    const paymentMethod: PaymentMethod = {
      id: uuidv4(),
      userId,
      type: 'digital_wallet',
      provider: 'google_pay',
      providerPaymentMethodId: token,
      isDefault,
      isActive: true,
      createdAt: new Date()
    };

    return paymentMethod;
  }

  private async processGooglePayPayment(
    userId: string,
    amount: Decimal,
    currency: CurrencyCode,
    paymentMethod: PaymentMethod,
    purpose: PaymentPurpose,
    purposeId: string,
    metadata?: Record<string, any>
  ): Promise<Payment> {
    // Mock Google Pay processing
    const payment: Payment = {
      id: uuidv4(),
      userId,
      amount,
      currency,
      status: 'completed',
      provider: 'google_pay',
      providerTransactionId: `GPAY_${uuidv4()}`,
      paymentMethodId: paymentMethod.id,
      purpose,
      purposeId,
      createdAt: new Date(),
      updatedAt: new Date(),
      metadata
    };

    return payment;
  }

  // Private Venmo methods

  private async addVenmoMethod(
    userId: string,
    token: string,
    isDefault: boolean
  ): Promise<PaymentMethod> {
    const paymentMethod: PaymentMethod = {
      id: uuidv4(),
      userId,
      type: 'digital_wallet',
      provider: 'venmo',
      providerPaymentMethodId: token,
      isDefault,
      isActive: true,
      createdAt: new Date()
    };

    return paymentMethod;
  }

  private async processVenmoPayment(
    userId: string,
    amount: Decimal,
    currency: CurrencyCode,
    paymentMethod: PaymentMethod,
    purpose: PaymentPurpose,
    purposeId: string,
    metadata?: Record<string, any>
  ): Promise<Payment> {
    // Mock Venmo processing
    const payment: Payment = {
      id: uuidv4(),
      userId,
      amount,
      currency,
      status: 'completed',
      provider: 'venmo',
      providerTransactionId: `VENMO_${uuidv4()}`,
      paymentMethodId: paymentMethod.id,
      purpose,
      purposeId,
      createdAt: new Date(),
      updatedAt: new Date(),
      metadata
    };

    return payment;
  }

  // Private Zelle methods

  private async addZelleMethod(
    userId: string,
    token: string,
    isDefault: boolean
  ): Promise<PaymentMethod> {
    const paymentMethod: PaymentMethod = {
      id: uuidv4(),
      userId,
      type: 'bank_account',
      provider: 'zelle',
      providerPaymentMethodId: token,
      isDefault,
      isActive: true,
      createdAt: new Date()
    };

    return paymentMethod;
  }

  private async processZellePayment(
    userId: string,
    amount: Decimal,
    currency: CurrencyCode,
    paymentMethod: PaymentMethod,
    purpose: PaymentPurpose,
    purposeId: string,
    metadata?: Record<string, any>
  ): Promise<Payment> {
    // Mock Zelle processing
    const payment: Payment = {
      id: uuidv4(),
      userId,
      amount,
      currency,
      status: 'completed',
      provider: 'zelle',
      providerTransactionId: `ZELLE_${uuidv4()}`,
      paymentMethodId: paymentMethod.id,
      purpose,
      purposeId,
      createdAt: new Date(),
      updatedAt: new Date(),
      metadata
    };

    return payment;
  }

  // Helper methods

  private async getPaymentMethod(paymentMethodId: string): Promise<PaymentMethod | null> {
    // Mock implementation - would fetch from database
    return {
      id: paymentMethodId,
      userId: 'user-123',
      type: 'card',
      provider: 'stripe',
      providerPaymentMethodId: 'pm_mock',
      isDefault: true,
      isActive: true,
      createdAt: new Date()
    };
  }

  private async getPayment(paymentId: string): Promise<Payment | null> {
    // Mock implementation - would fetch from database
    return {
      id: paymentId,
      userId: 'user-123',
      amount: new Decimal(10),
      currency: 'USD',
      status: 'completed',
      provider: 'stripe',
      providerTransactionId: 'pi_mock',
      paymentMethodId: 'pm_mock',
      purpose: 'cc_purchase',
      purposeId: 'purchase-123',
      createdAt: new Date(),
      updatedAt: new Date()
    };
  }
}