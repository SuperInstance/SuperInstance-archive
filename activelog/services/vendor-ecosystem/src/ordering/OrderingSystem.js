/**
 * One-Click Ordering System
 * Handles streamlined order processing with intelligent automation
 */

import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/ordering.log' })
  ]
});

export class OrderingSystem extends EventEmitter {
  constructor(dependencies) {
    super();
    this.priceComparisonEngine = dependencies.priceComparisonEngine;
    this.shippingOptimizer = dependencies.shippingOptimizer;
    this.compatibilityChecker = dependencies.compatibilityChecker;
    this.paymentProcessor = dependencies.paymentProcessor;
    this.orderTracker = dependencies.orderTracker;
    this.inventorySyncManager = dependencies.inventorySyncManager;
    
    this.orders = new Map();
    this.carts = new Map();
    this.savedAddresses = new Map();
    this.savedPaymentMethods = new Map();
    this.orderTemplates = new Map();
    this.autoReorderRules = new Map();
  }

  async initialize() {
    logger.info('🛒 One-Click Ordering System initialized');
  }

  /**
   * Create a new order with full customization
   */
  async createOrder(orderData) {
    try {
      const orderId = uuidv4();
      
      // Validate order data
      await this.validateOrderData(orderData);
      
      // Check product availability
      await this.checkProductAvailability(orderData.items);
      
      // Apply compatibility checking if enabled
      if (orderData.checkCompatibility) {
        const compatibilityResults = await this.compatibilityChecker.checkOrderCompatibility(
          orderData.items
        );
        
        if (compatibilityResults.hasIncompatibilities) {
          return {
            success: false,
            error: 'Product compatibility issues detected',
            compatibilityResults
          };
        }
      }

      // Get pricing with comparison
      const pricingResult = await this.calculateOrderPricing(orderData);
      
      // Optimize shipping
      const shippingResult = await this.optimizeOrderShipping(orderData, pricingResult);
      
      // Create order object
      const order = {
        id: orderId,
        customerId: orderData.customerId,
        status: 'pending_payment',
        items: await this.processOrderItems(orderData.items),
        pricing: pricingResult,
        shipping: shippingResult,
        billing: {
          subtotal: pricingResult.subtotal,
          tax: pricingResult.tax,
          shipping: shippingResult.cost,
          total: pricingResult.total + shippingResult.cost
        },
        addresses: {
          shipping: orderData.shippingAddress,
          billing: orderData.billingAddress || orderData.shippingAddress
        },
        payment: {
          method: orderData.paymentMethod,
          status: 'pending'
        },
        metadata: {
          source: 'manual',
          userAgent: orderData.userAgent,
          ipAddress: orderData.ipAddress
        },
        timeline: {
          created: Date.now(),
          estimatedFulfillment: shippingResult.estimatedFulfillment,
          estimatedDelivery: shippingResult.estimatedDelivery
        },
        notes: orderData.notes || ''
      };

      // Process payment
      if (orderData.processPayment !== false) {
        const paymentResult = await this.processOrderPayment(order);
        
        if (!paymentResult.success) {
          return {
            success: false,
            error: 'Payment processing failed',
            paymentError: paymentResult.error,
            order: this.sanitizeOrder(order)
          };
        }
        
        order.payment = paymentResult.payment;
        order.status = 'confirmed';
      }

      // Save order
      this.orders.set(orderId, order);
      
      // Emit order created event
      this.emit('order:created', order);
      
      // If confirmed, start fulfillment process
      if (order.status === 'confirmed') {
        await this.initiateOrderFulfillment(order);
        this.emit('order:placed', order);
      }

      logger.info(`📦 Order created: ${orderId} for customer: ${orderData.customerId}`);
      
      return {
        success: true,
        order: this.sanitizeOrder(order)
      };

    } catch (error) {
      logger.error('Failed to create order:', error);
      throw error;
    }
  }

  /**
   * One-click ordering for streamlined purchases
   */
  async oneClickOrder(orderData) {
    try {
      const { customerId, productId, quantity = 1, savedAddressId, savedPaymentId } = orderData;
      
      // Get saved customer data
      const savedAddress = await this.getSavedAddress(customerId, savedAddressId);
      const savedPayment = await this.getSavedPaymentMethod(customerId, savedPaymentId);
      
      if (!savedAddress || !savedPayment) {
        throw new Error('Saved address and payment method required for one-click ordering');
      }

      // Get product information
      const product = await this.getProductInfo(productId);
      if (!product) {
        throw new Error('Product not found');
      }

      // Check availability
      if (product.quantity < quantity) {
        throw new Error('Insufficient inventory');
      }

      // Create streamlined order data
      const streamlinedOrderData = {
        customerId,
        items: [{
          productId,
          quantity,
          unitPrice: product.price
        }],
        shippingAddress: savedAddress,
        billingAddress: savedAddress,
        paymentMethod: savedPayment,
        processPayment: true,
        checkCompatibility: false, // Skip for one-click speed
        source: 'one_click'
      };

      // Use fastest shipping by default
      const shippingOptions = await this.shippingOptimizer.getShippingOptions(
        streamlinedOrderData.items,
        savedAddress
      );
      
      const fastestShipping = shippingOptions.reduce((fastest, option) => 
        option.estimatedDays < fastest.estimatedDays ? option : fastest
      );
      
      streamlinedOrderData.shippingMethod = fastestShipping.id;

      // Create order with optimized flow
      const result = await this.createOrder(streamlinedOrderData);
      
      if (result.success) {
        // Update one-click metrics
        await this.updateOneClickMetrics(customerId);
        
        logger.info(`⚡ One-click order completed: ${result.order.id}`);
        
        this.emit('order:one_click_completed', {
          orderId: result.order.id,
          customerId,
          productId,
          processingTime: Date.now() - result.order.timeline.created
        });
      }

      return result;

    } catch (error) {
      logger.error('One-click order failed:', error);
      throw error;
    }
  }

  /**
   * Add items to shopping cart
   */
  async addToCart(customerId, items) {
    try {
      let cart = this.carts.get(customerId);
      
      if (!cart) {
        cart = {
          id: uuidv4(),
          customerId,
          items: [],
          createdAt: Date.now(),
          updatedAt: Date.now()
        };
      }

      // Process each item
      for (const item of items) {
        // Validate product exists and has inventory
        const product = await this.getProductInfo(item.productId);
        if (!product) {
          throw new Error(`Product not found: ${item.productId}`);
        }

        // Check if item already in cart
        const existingItemIndex = cart.items.findIndex(
          cartItem => cartItem.productId === item.productId
        );

        if (existingItemIndex >= 0) {
          // Update quantity
          cart.items[existingItemIndex].quantity += item.quantity || 1;
        } else {
          // Add new item
          cart.items.push({
            productId: item.productId,
            quantity: item.quantity || 1,
            unitPrice: product.price,
            addedAt: Date.now()
          });
        }
      }

      // Update cart metadata
      cart.updatedAt = Date.now();
      cart.itemCount = cart.items.reduce((sum, item) => sum + item.quantity, 0);
      cart.subtotal = cart.items.reduce((sum, item) => sum + (item.unitPrice * item.quantity), 0);

      this.carts.set(customerId, cart);

      this.emit('cart:updated', {
        customerId,
        cart: this.sanitizeCart(cart),
        action: 'items_added'
      });

      return this.sanitizeCart(cart);

    } catch (error) {
      logger.error('Failed to add items to cart:', error);
      throw error;
    }
  }

  /**
   * Get shopping cart
   */
  async getCart(customerId) {
    const cart = this.carts.get(customerId);
    return cart ? this.sanitizeCart(cart) : null;
  }

  /**
   * Update cart item
   */
  async updateCartItem(customerId, productId, updates) {
    try {
      const cart = this.carts.get(customerId);
      if (!cart) {
        throw new Error('Cart not found');
      }

      const itemIndex = cart.items.findIndex(item => item.productId === productId);
      if (itemIndex === -1) {
        throw new Error('Item not found in cart');
      }

      // Update item
      if (updates.quantity !== undefined) {
        if (updates.quantity <= 0) {
          // Remove item if quantity is 0 or less
          cart.items.splice(itemIndex, 1);
        } else {
          cart.items[itemIndex].quantity = updates.quantity;
        }
      }

      // Recalculate cart totals
      cart.updatedAt = Date.now();
      cart.itemCount = cart.items.reduce((sum, item) => sum + item.quantity, 0);
      cart.subtotal = cart.items.reduce((sum, item) => sum + (item.unitPrice * item.quantity), 0);

      this.carts.set(customerId, cart);

      this.emit('cart:updated', {
        customerId,
        cart: this.sanitizeCart(cart),
        action: 'item_updated'
      });

      return this.sanitizeCart(cart);

    } catch (error) {
      logger.error('Failed to update cart item:', error);
      throw error;
    }
  }

  /**
   * Convert cart to order
   */
  async cartToOrder(customerId, orderData) {
    try {
      const cart = this.carts.get(customerId);
      if (!cart || cart.items.length === 0) {
        throw new Error('Cart is empty');
      }

      // Create order from cart
      const orderFromCart = {
        customerId,
        items: cart.items,
        shippingAddress: orderData.shippingAddress,
        billingAddress: orderData.billingAddress,
        paymentMethod: orderData.paymentMethod,
        processPayment: orderData.processPayment,
        checkCompatibility: orderData.checkCompatibility,
        notes: orderData.notes
      };

      const result = await this.createOrder(orderFromCart);

      if (result.success) {
        // Clear cart after successful order
        this.carts.delete(customerId);
        
        this.emit('cart:converted_to_order', {
          customerId,
          orderId: result.order.id,
          cartId: cart.id
        });
      }

      return result;

    } catch (error) {
      logger.error('Failed to convert cart to order:', error);
      throw error;
    }
  }

  /**
   * Save customer address
   */
  async saveAddress(customerId, addressData) {
    try {
      const addressId = uuidv4();
      
      const address = {
        id: addressId,
        customerId,
        type: addressData.type || 'shipping', // shipping, billing, both
        label: addressData.label || 'Home',
        firstName: addressData.firstName,
        lastName: addressData.lastName,
        company: addressData.company,
        address1: addressData.address1,
        address2: addressData.address2,
        city: addressData.city,
        state: addressData.state,
        zipCode: addressData.zipCode,
        country: addressData.country || 'US',
        phone: addressData.phone,
        isDefault: addressData.isDefault || false,
        createdAt: Date.now()
      };

      // Get customer's existing addresses
      const customerAddresses = this.savedAddresses.get(customerId) || [];
      
      // If this is set as default, remove default from others
      if (address.isDefault) {
        customerAddresses.forEach(addr => addr.isDefault = false);
      }
      
      // If this is the first address, make it default
      if (customerAddresses.length === 0) {
        address.isDefault = true;
      }

      customerAddresses.push(address);
      this.savedAddresses.set(customerId, customerAddresses);

      this.emit('address:saved', {
        customerId,
        addressId,
        address: this.sanitizeAddress(address)
      });

      return this.sanitizeAddress(address);

    } catch (error) {
      logger.error('Failed to save address:', error);
      throw error;
    }
  }

  /**
   * Save customer payment method
   */
  async savePaymentMethod(customerId, paymentData) {
    try {
      const paymentId = uuidv4();
      
      // In production, this would integrate with payment processor's vault
      const paymentMethod = {
        id: paymentId,
        customerId,
        type: paymentData.type, // credit_card, debit_card, paypal, etc.
        label: paymentData.label || 'Default',
        lastFour: paymentData.lastFour,
        expiryMonth: paymentData.expiryMonth,
        expiryYear: paymentData.expiryYear,
        brand: paymentData.brand, // visa, mastercard, etc.
        isDefault: paymentData.isDefault || false,
        vaultToken: paymentData.vaultToken, // Secure token from payment processor
        createdAt: Date.now()
      };

      // Get customer's existing payment methods
      const customerPayments = this.savedPaymentMethods.get(customerId) || [];
      
      // If this is set as default, remove default from others
      if (paymentMethod.isDefault) {
        customerPayments.forEach(payment => payment.isDefault = false);
      }
      
      // If this is the first payment method, make it default
      if (customerPayments.length === 0) {
        paymentMethod.isDefault = true;
      }

      customerPayments.push(paymentMethod);
      this.savedPaymentMethods.set(customerId, customerPayments);

      this.emit('payment_method:saved', {
        customerId,
        paymentId,
        paymentMethod: this.sanitizePaymentMethod(paymentMethod)
      });

      return this.sanitizePaymentMethod(paymentMethod);

    } catch (error) {
      logger.error('Failed to save payment method:', error);
      throw error;
    }
  }

  /**
   * Create order template for recurring orders
   */
  async createOrderTemplate(customerId, templateData) {
    try {
      const templateId = uuidv4();
      
      const template = {
        id: templateId,
        customerId,
        name: templateData.name,
        description: templateData.description,
        items: templateData.items,
        shippingAddress: templateData.shippingAddress,
        paymentMethod: templateData.paymentMethod,
        frequency: templateData.frequency, // weekly, monthly, quarterly, etc.
        isActive: templateData.isActive !== false,
        nextOrderDate: templateData.nextOrderDate,
        createdAt: Date.now()
      };

      this.orderTemplates.set(templateId, template);

      // Schedule recurring orders if active
      if (template.isActive && template.frequency) {
        await this.scheduleRecurringOrder(template);
      }

      this.emit('order_template:created', {
        customerId,
        templateId,
        template: this.sanitizeOrderTemplate(template)
      });

      return this.sanitizeOrderTemplate(template);

    } catch (error) {
      logger.error('Failed to create order template:', error);
      throw error;
    }
  }

  /**
   * Process order payment
   */
  async processOrderPayment(order) {
    try {
      const paymentResult = await this.paymentProcessor.processPayment({
        orderId: order.id,
        amount: order.billing.total,
        currency: 'USD',
        paymentMethod: order.payment.method,
        billingAddress: order.addresses.billing,
        customer: {
          id: order.customerId
        }
      });

      if (paymentResult.success) {
        return {
          success: true,
          payment: {
            id: paymentResult.paymentId,
            status: 'completed',
            amount: paymentResult.amount,
            currency: paymentResult.currency,
            method: order.payment.method,
            transactionId: paymentResult.transactionId,
            processedAt: Date.now()
          }
        };
      } else {
        return {
          success: false,
          error: paymentResult.error,
          payment: {
            status: 'failed',
            error: paymentResult.error,
            attemptedAt: Date.now()
          }
        };
      }

    } catch (error) {
      logger.error('Payment processing error:', error);
      return {
        success: false,
        error: error.message,
        payment: {
          status: 'error',
          error: error.message,
          attemptedAt: Date.now()
        }
      };
    }
  }

  /**
   * Helper methods
   */
  async validateOrderData(orderData) {
    if (!orderData.customerId) {
      throw new Error('Customer ID is required');
    }
    
    if (!orderData.items || orderData.items.length === 0) {
      throw new Error('Order items are required');
    }
    
    if (!orderData.shippingAddress) {
      throw new Error('Shipping address is required');
    }
    
    if (!orderData.paymentMethod) {
      throw new Error('Payment method is required');
    }

    // Validate each item
    for (const item of orderData.items) {
      if (!item.productId || !item.quantity || item.quantity <= 0) {
        throw new Error('Invalid item data');
      }
    }
  }

  async checkProductAvailability(items) {
    for (const item of items) {
      const product = await this.getProductInfo(item.productId);
      if (!product) {
        throw new Error(`Product not found: ${item.productId}`);
      }
      
      if (product.quantity < item.quantity) {
        throw new Error(`Insufficient inventory for product: ${item.productId}`);
      }
    }
  }

  async calculateOrderPricing(orderData) {
    // Get pricing comparison for all items
    const pricingPromises = orderData.items.map(item => 
      this.priceComparisonEngine.comparePrice(item.productId, {
        quantity: item.quantity
      })
    );
    
    const pricingResults = await Promise.all(pricingPromises);
    
    let subtotal = 0;
    const itemPricing = [];
    
    for (let i = 0; i < orderData.items.length; i++) {
      const item = orderData.items[i];
      const pricing = pricingResults[i];
      
      const itemTotal = pricing.bestPrice * item.quantity;
      subtotal += itemTotal;
      
      itemPricing.push({
        productId: item.productId,
        quantity: item.quantity,
        unitPrice: pricing.bestPrice,
        totalPrice: itemTotal,
        savings: pricing.savings || 0,
        bestVendor: pricing.bestVendor
      });
    }
    
    // Calculate tax (simplified - 8.25% for example)
    const taxRate = 0.0825;
    const tax = Math.round(subtotal * taxRate * 100) / 100;
    
    return {
      items: itemPricing,
      subtotal: Math.round(subtotal * 100) / 100,
      tax: tax,
      total: Math.round((subtotal + tax) * 100) / 100
    };
  }

  async optimizeOrderShipping(orderData, pricingResult) {
    return await this.shippingOptimizer.optimizeShipping(
      pricingResult.items,
      orderData.shippingAddress,
      {
        priority: orderData.shippingPriority || 'balanced', // speed, cost, balanced
        method: orderData.shippingMethod
      }
    );
  }

  async processOrderItems(items) {
    return items.map(item => ({
      id: uuidv4(),
      productId: item.productId,
      quantity: item.quantity,
      unitPrice: item.unitPrice,
      totalPrice: item.unitPrice * item.quantity,
      status: 'pending_fulfillment'
    }));
  }

  async initiateOrderFulfillment(order) {
    // This would trigger fulfillment process
    // - Reserve inventory
    // - Notify vendors
    // - Create picking lists
    // - Schedule shipping
    
    logger.info(`🚚 Initiating fulfillment for order: ${order.id}`);
    
    this.emit('order:fulfillment_initiated', {
      orderId: order.id,
      customerId: order.customerId
    });
  }

  async getSavedAddress(customerId, addressId) {
    const addresses = this.savedAddresses.get(customerId) || [];
    return addresses.find(addr => addr.id === addressId);
  }

  async getSavedPaymentMethod(customerId, paymentId) {
    const payments = this.savedPaymentMethods.get(customerId) || [];
    return payments.find(payment => payment.id === paymentId);
  }

  async getProductInfo(productId) {
    // In production, this would query your product catalog
    // For now, return mock data
    return {
      id: productId,
      name: `Product ${productId}`,
      price: 99.99,
      quantity: 100
    };
  }

  async updateOneClickMetrics(customerId) {
    // Track one-click usage metrics
    logger.info(`📊 Updated one-click metrics for customer: ${customerId}`);
  }

  async scheduleRecurringOrder(template) {
    // Schedule recurring order based on template
    logger.info(`📅 Scheduled recurring order for template: ${template.id}`);
  }

  // Sanitization methods
  sanitizeOrder(order) {
    return {
      ...order,
      payment: {
        ...order.payment,
        method: order.payment.method ? { 
          type: order.payment.method.type,
          lastFour: order.payment.method.lastFour 
        } : null
      }
    };
  }

  sanitizeCart(cart) {
    return { ...cart };
  }

  sanitizeAddress(address) {
    return { ...address };
  }

  sanitizePaymentMethod(paymentMethod) {
    const sanitized = { ...paymentMethod };
    delete sanitized.vaultToken;
    return sanitized;
  }

  sanitizeOrderTemplate(template) {
    return { ...template };
  }

  /**
   * Public API methods
   */
  async getOrder(orderId) {
    const order = this.orders.get(orderId);
    return order ? this.sanitizeOrder(order) : null;
  }

  async getCustomerOrders(customerId, options = {}) {
    const orders = Array.from(this.orders.values())
      .filter(order => order.customerId === customerId)
      .sort((a, b) => b.timeline.created - a.timeline.created);

    if (options.limit) {
      return orders.slice(0, options.limit);
    }

    return orders.map(order => this.sanitizeOrder(order));
  }

  async getOrdersByStatus(status, options = {}) {
    const orders = Array.from(this.orders.values())
      .filter(order => order.status === status)
      .sort((a, b) => b.timeline.created - a.timeline.created);

    if (options.limit) {
      return orders.slice(0, options.limit);
    }

    return orders.map(order => this.sanitizeOrder(order));
  }

  async updateOrderStatus(orderId, newStatus, notes = '') {
    const order = this.orders.get(orderId);
    if (!order) {
      throw new Error('Order not found');
    }

    const oldStatus = order.status;
    order.status = newStatus;
    
    if (notes) {
      order.notes = order.notes ? `${order.notes}\n${notes}` : notes;
    }

    this.emit('order:status_updated', {
      orderId,
      oldStatus,
      newStatus,
      customerId: order.customerId,
      timestamp: Date.now()
    });

    return this.sanitizeOrder(order);
  }
}