const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const Order = require('../models/Order');
const Maker = require('../models/Maker');
const logger = require('../config/logger');
const redis = require('../config/redis');
const { BusinessError, ServiceError } = require('../middleware/errorHandler');

class EscrowPaymentService {
  constructor() {
    this.escrowHoldPeriod = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds
    this.disputePeriod = 14 * 24 * 60 * 60 * 1000; // 14 days for disputes
    this.serviceFeeRate = 0.05; // 5% service fee
    this.stripeFeeRate = 0.029; // 2.9% + $0.30 Stripe fee
    this.stripeFeeFixed = 0.30;
  }

  /**
   * Create escrow payment for an order
   */
  async createEscrowPayment(orderId, paymentMethodId, customerId) {
    try {
      const order = await Order.findOne({ orderId });
      if (!order) {
        throw new BusinessError('Order not found', 'ORDER_NOT_FOUND');
      }

      // Validate order state
      if (order.status !== 'maker_selected') {
        throw new BusinessError('Order not ready for payment', 'INVALID_ORDER_STATE');
      }

      // Calculate total amount including fees
      const pricing = this.calculateEscrowPricing(order);
      
      logger.logBusinessEvent('escrow_payment_initiated', {
        orderId: order.orderId,
        customerId,
        totalAmount: pricing.totalAmount,
        escrowAmount: pricing.escrowAmount
      });

      // Create Stripe Payment Intent with manual capture
      const paymentIntent = await stripe.paymentIntents.create({
        amount: Math.round(pricing.totalAmount * 100), // Convert to cents
        currency: 'usd',
        payment_method: paymentMethodId,
        customer: customerId,
        capture_method: 'manual', // Don't capture immediately
        confirm: true,
        metadata: {
          orderId: order.orderId,
          type: 'escrow_payment',
          makerUserId: order.makers.selected.makerUserId,
          escrowAmount: pricing.escrowAmount.toString(),
          serviceFee: pricing.serviceFee.toString()
        },
        description: `Escrow payment for 3D print order ${order.orderId}`
      });

      // Create escrow record
      const escrowData = {
        orderId: order.orderId,
        paymentIntentId: paymentIntent.id,
        customerId: order.customer.dmlogUserId,
        makerId: order.makers.selected.makerId,
        
        amounts: {
          orderTotal: pricing.orderAmount,
          serviceFee: pricing.serviceFee,
          stripeFee: pricing.stripeFee,
          totalCharged: pricing.totalAmount,
          escrowAmount: pricing.escrowAmount,
          makerPayout: pricing.makerPayout
        },
        
        status: 'authorized',
        createdAt: new Date(),
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days to capture
        
        milestones: {
          orderStarted: false,
          orderCompleted: false,
          qualityApproved: false,
          shipped: false,
          delivered: false,
          customerApproved: false
        },
        
        releaseConditions: {
          autoRelease: true,
          releaseAfterDays: 7,
          requireCustomerApproval: false,
          requireDeliveryConfirmation: true
        }
      };

      // Store escrow data in Redis and database
      await redis.set(`escrow:${order.orderId}`, JSON.stringify(escrowData), 30 * 24 * 60 * 60); // 30 day TTL
      
      // Update order with payment information
      order.pricing.payment = {
        method: 'credit_card',
        status: 'authorized',
        transactionId: paymentIntent.id,
        escrowId: `escrow_${order.orderId}`,
        paymentDate: new Date(),
        amount: pricing.totalAmount
      };

      order.status = 'confirmed';
      await order.save();

      logger.logBusinessEvent('escrow_payment_created', {
        orderId: order.orderId,
        escrowId: escrowData.escrowId,
        paymentIntentId: paymentIntent.id,
        amount: pricing.totalAmount,
        status: paymentIntent.status
      });

      return {
        success: true,
        escrowId: `escrow_${order.orderId}`,
        paymentIntentId: paymentIntent.id,
        status: paymentIntent.status,
        amounts: escrowData.amounts,
        holdPeriod: '7 days after delivery',
        releaseConditions: escrowData.releaseConditions
      };

    } catch (error) {
      if (error.type === 'StripeCardError') {
        throw new BusinessError(error.message, 'PAYMENT_DECLINED');
      } else if (error.type === 'StripeError') {
        throw new ServiceError(error.message, 'stripe', 'STRIPE_ERROR');
      }
      
      logger.error('Error creating escrow payment:', error);
      throw error;
    }
  }

  /**
   * Capture the authorized payment when order starts production
   */
  async captureEscrowPayment(orderId) {
    try {
      const escrowData = await this.getEscrowData(orderId);
      if (!escrowData) {
        throw new BusinessError('Escrow payment not found', 'ESCROW_NOT_FOUND');
      }

      if (escrowData.status !== 'authorized') {
        throw new BusinessError('Payment already captured or failed', 'INVALID_ESCROW_STATUS');
      }

      // Capture the Stripe Payment Intent
      const paymentIntent = await stripe.paymentIntents.capture(escrowData.paymentIntentId);

      // Update escrow status
      escrowData.status = 'captured';
      escrowData.capturedAt = new Date();
      escrowData.milestones.orderStarted = true;
      
      // Start the release timer
      escrowData.releaseScheduledFor = new Date(Date.now() + this.escrowHoldPeriod);

      await this.updateEscrowData(orderId, escrowData);

      // Update order status
      const order = await Order.findOne({ orderId });
      if (order) {
        order.pricing.payment.status = 'captured';
        order.status = 'paid';
        await order.save();
      }

      // Schedule automatic release
      await this.scheduleAutomaticRelease(orderId, escrowData.releaseScheduledFor);

      logger.logBusinessEvent('escrow_payment_captured', {
        orderId,
        paymentIntentId: paymentIntent.id,
        amount: paymentIntent.amount_received / 100,
        releaseScheduledFor: escrowData.releaseScheduledFor
      });

      return {
        success: true,
        status: 'captured',
        capturedAmount: paymentIntent.amount_received / 100,
        releaseScheduledFor: escrowData.releaseScheduledFor
      };

    } catch (error) {
      logger.error('Error capturing escrow payment:', error);
      throw error;
    }
  }

  /**
   * Update escrow milestones as order progresses
   */
  async updateEscrowMilestone(orderId, milestone) {
    try {
      const escrowData = await this.getEscrowData(orderId);
      if (!escrowData) {
        throw new BusinessError('Escrow payment not found', 'ESCROW_NOT_FOUND');
      }

      // Update milestone
      escrowData.milestones[milestone] = true;
      escrowData.lastUpdated = new Date();

      // Check if conditions are met for early release
      if (this.shouldTriggerEarlyRelease(escrowData)) {
        await this.releaseEscrowPayment(orderId, 'milestone_completion');
        return { released: true, reason: 'milestone_completion' };
      }

      await this.updateEscrowData(orderId, escrowData);

      logger.logBusinessEvent('escrow_milestone_updated', {
        orderId,
        milestone,
        allMilestones: escrowData.milestones
      });

      return {
        success: true,
        milestone,
        updated: true,
        milestones: escrowData.milestones
      };

    } catch (error) {
      logger.error('Error updating escrow milestone:', error);
      throw error;
    }
  }

  /**
   * Release escrow payment to maker
   */
  async releaseEscrowPayment(orderId, reason = 'automatic') {
    try {
      const escrowData = await this.getEscrowData(orderId);
      if (!escrowData) {
        throw new BusinessError('Escrow payment not found', 'ESCROW_NOT_FOUND');
      }

      if (escrowData.status === 'released') {
        return { success: true, message: 'Payment already released' };
      }

      if (escrowData.status !== 'captured') {
        throw new BusinessError('Payment must be captured before release', 'INVALID_ESCROW_STATUS');
      }

      // Get maker information
      const maker = await Maker.findOne({ makerId: escrowData.makerId });
      if (!maker) {
        throw new BusinessError('Maker not found', 'MAKER_NOT_FOUND');
      }

      // Create transfer to maker's Stripe account
      const transfer = await this.transferToMaker(escrowData, maker);

      // Update escrow status
      escrowData.status = 'released';
      escrowData.releasedAt = new Date();
      escrowData.releasedReason = reason;
      escrowData.transferId = transfer.id;

      await this.updateEscrowData(orderId, escrowData);

      // Update maker earnings
      await this.updateMakerEarnings(escrowData.makerId, escrowData.amounts.makerPayout);

      // Update order status
      const order = await Order.findOne({ orderId });
      if (order) {
        order.pricing.payment.status = 'completed';
        order.pricing.payment.releaseDate = new Date();
        await order.save();
      }

      logger.logBusinessEvent('escrow_payment_released', {
        orderId,
        makerId: escrowData.makerId,
        amount: escrowData.amounts.makerPayout,
        reason,
        transferId: transfer.id
      });

      return {
        success: true,
        status: 'released',
        amount: escrowData.amounts.makerPayout,
        transferId: transfer.id,
        releasedAt: escrowData.releasedAt
      };

    } catch (error) {
      logger.error('Error releasing escrow payment:', error);
      throw error;
    }
  }

  /**
   * Handle dispute initiation
   */
  async initiateDispute(orderId, disputeReason, initiatedBy, evidence = []) {
    try {
      const escrowData = await this.getEscrowData(orderId);
      if (!escrowData) {
        throw new BusinessError('Escrow payment not found', 'ESCROW_NOT_FOUND');
      }

      if (escrowData.status === 'released') {
        throw new BusinessError('Cannot dispute after payment has been released', 'PAYMENT_ALREADY_RELEASED');
      }

      // Freeze the escrow
      escrowData.status = 'disputed';
      escrowData.dispute = {
        initiatedBy,
        reason: disputeReason,
        initiatedAt: new Date(),
        evidence,
        status: 'open'
      };

      await this.updateEscrowData(orderId, escrowData);

      // Cancel any scheduled releases
      await this.cancelScheduledRelease(orderId);

      // Create Stripe dispute if payment was captured
      if (escrowData.paymentIntentId) {
        // Note: In practice, disputes are usually initiated by cardholders
        // Here we're tracking internal disputes
      }

      // Notify relevant parties
      await this.notifyDisputeCreated(orderId, escrowData.dispute);

      logger.logBusinessEvent('escrow_dispute_initiated', {
        orderId,
        initiatedBy,
        reason: disputeReason,
        evidenceCount: evidence.length
      });

      return {
        success: true,
        disputeId: `dispute_${orderId}`,
        status: 'disputed',
        dispute: escrowData.dispute
      };

    } catch (error) {
      logger.error('Error initiating dispute:', error);
      throw error;
    }
  }

  /**
   * Resolve dispute
   */
  async resolveDispute(orderId, resolution, resolvedBy, refundAmount = 0) {
    try {
      const escrowData = await this.getEscrowData(orderId);
      if (!escrowData || !escrowData.dispute) {
        throw new BusinessError('No dispute found for this order', 'NO_DISPUTE_FOUND');
      }

      if (escrowData.dispute.status !== 'open') {
        throw new BusinessError('Dispute is not open', 'DISPUTE_NOT_OPEN');
      }

      // Update dispute status
      escrowData.dispute.status = 'resolved';
      escrowData.dispute.resolution = resolution;
      escrowData.dispute.resolvedAt = new Date();
      escrowData.dispute.resolvedBy = resolvedBy;

      if (refundAmount > 0) {
        // Process refund
        const refund = await this.processRefund(escrowData, refundAmount);
        escrowData.dispute.refundId = refund.id;
        escrowData.dispute.refundAmount = refundAmount;
      }

      // Update escrow status based on resolution
      if (resolution === 'release_to_maker') {
        await this.releaseEscrowPayment(orderId, 'dispute_resolution');
      } else if (resolution === 'refund_customer') {
        escrowData.status = 'refunded';
      } else if (resolution === 'partial_refund') {
        // Partial refund and partial release
        const remainingAmount = escrowData.amounts.makerPayout - refundAmount;
        if (remainingAmount > 0) {
          await this.releasePartialPayment(orderId, remainingAmount);
        }
      }

      await this.updateEscrowData(orderId, escrowData);

      logger.logBusinessEvent('escrow_dispute_resolved', {
        orderId,
        resolution,
        resolvedBy,
        refundAmount
      });

      return {
        success: true,
        resolution,
        refundAmount,
        resolvedAt: escrowData.dispute.resolvedAt
      };

    } catch (error) {
      logger.error('Error resolving dispute:', error);
      throw error;
    }
  }

  /**
   * Get escrow status for an order
   */
  async getEscrowStatus(orderId) {
    try {
      const escrowData = await this.getEscrowData(orderId);
      if (!escrowData) {
        return { found: false };
      }

      return {
        found: true,
        orderId: escrowData.orderId,
        status: escrowData.status,
        amounts: escrowData.amounts,
        milestones: escrowData.milestones,
        releaseScheduledFor: escrowData.releaseScheduledFor,
        createdAt: escrowData.createdAt,
        dispute: escrowData.dispute || null,
        canDispute: this.canInitiateDispute(escrowData),
        daysUntilAutoRelease: this.calculateDaysUntilRelease(escrowData)
      };
    } catch (error) {
      logger.error('Error getting escrow status:', error);
      throw error;
    }
  }

  /**
   * Calculate escrow pricing breakdown
   */
  calculateEscrowPricing(order) {
    const orderAmount = order.pricing.finalPricing?.totalAmount || 
                       order.makers.selected?.quote?.totalPrice || 0;

    const serviceFee = orderAmount * this.serviceFeeRate;
    const stripeFee = (orderAmount + serviceFee) * this.stripeFeeRate + this.stripeFeeFixed;
    const totalAmount = orderAmount + serviceFee + stripeFee;
    
    // Amount held in escrow (excluding our fees)
    const escrowAmount = orderAmount;
    // Amount paid out to maker (minus our service fee)
    const makerPayout = orderAmount - serviceFee;

    return {
      orderAmount: Math.round(orderAmount * 100) / 100,
      serviceFee: Math.round(serviceFee * 100) / 100,
      stripeFee: Math.round(stripeFee * 100) / 100,
      totalAmount: Math.round(totalAmount * 100) / 100,
      escrowAmount: Math.round(escrowAmount * 100) / 100,
      makerPayout: Math.round(makerPayout * 100) / 100
    };
  }

  /**
   * Transfer funds to maker
   */
  async transferToMaker(escrowData, maker) {
    try {
      // In a real implementation, this would transfer to the maker's Stripe Connect account
      // For now, we'll simulate the transfer
      
      const transfer = await stripe.transfers.create({
        amount: Math.round(escrowData.amounts.makerPayout * 100),
        currency: 'usd',
        destination: maker.financial?.stripeAccountId || 'acct_placeholder',
        metadata: {
          orderId: escrowData.orderId,
          makerId: escrowData.makerId,
          type: 'escrow_release'
        }
      });

      return transfer;
    } catch (error) {
      logger.error('Error transferring to maker:', error);
      throw new ServiceError('Transfer to maker failed', 'stripe', 'TRANSFER_FAILED');
    }
  }

  /**
   * Process refund to customer
   */
  async processRefund(escrowData, refundAmount) {
    try {
      const refund = await stripe.refunds.create({
        payment_intent: escrowData.paymentIntentId,
        amount: Math.round(refundAmount * 100),
        metadata: {
          orderId: escrowData.orderId,
          type: 'escrow_dispute_refund'
        }
      });

      return refund;
    } catch (error) {
      logger.error('Error processing refund:', error);
      throw new ServiceError('Refund processing failed', 'stripe', 'REFUND_FAILED');
    }
  }

  /**
   * Helper methods
   */
  async getEscrowData(orderId) {
    const data = await redis.get(`escrow:${orderId}`);
    return data ? JSON.parse(data) : null;
  }

  async updateEscrowData(orderId, escrowData) {
    escrowData.lastUpdated = new Date();
    await redis.set(`escrow:${orderId}`, JSON.stringify(escrowData), 30 * 24 * 60 * 60);
  }

  shouldTriggerEarlyRelease(escrowData) {
    const { milestones } = escrowData;
    return milestones.orderCompleted && 
           milestones.qualityApproved && 
           milestones.delivered &&
           !escrowData.dispute;
  }

  canInitiateDispute(escrowData) {
    return escrowData.status === 'captured' && 
           !escrowData.dispute &&
           escrowData.createdAt > new Date(Date.now() - this.disputePeriod);
  }

  calculateDaysUntilRelease(escrowData) {
    if (!escrowData.releaseScheduledFor) return null;
    const msUntilRelease = new Date(escrowData.releaseScheduledFor).getTime() - Date.now();
    return Math.max(0, Math.ceil(msUntilRelease / (24 * 60 * 60 * 1000)));
  }

  async scheduleAutomaticRelease(orderId, releaseDate) {
    const delay = new Date(releaseDate).getTime() - Date.now();
    if (delay > 0) {
      setTimeout(async () => {
        try {
          await this.releaseEscrowPayment(orderId, 'automatic');
        } catch (error) {
          logger.error(`Failed to automatically release escrow for order ${orderId}:`, error);
        }
      }, delay);
    }
  }

  async cancelScheduledRelease(orderId) {
    // In a production system, you'd use a job queue to cancel scheduled tasks
    logger.debug(`Cancelled scheduled release for order ${orderId}`);
  }

  async updateMakerEarnings(makerId, amount) {
    try {
      await Maker.updateOne(
        { makerId },
        { 
          $inc: { 
            'financial.totalEarned': amount,
            'financial.currentBalance': amount
          }
        }
      );
    } catch (error) {
      logger.error('Error updating maker earnings:', error);
    }
  }

  async releasePartialPayment(orderId, amount) {
    // Implementation for partial payments would go here
    logger.info(`Partial payment release of $${amount} for order ${orderId}`);
  }

  async notifyDisputeCreated(orderId, dispute) {
    // Send notifications to relevant parties about the dispute
    logger.info(`Dispute created for order ${orderId} by ${dispute.initiatedBy}`);
  }
}

module.exports = new EscrowPaymentService();