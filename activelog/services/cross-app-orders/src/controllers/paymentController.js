const express = require('express');
const router = express.Router();
const escrowPaymentService = require('../services/escrowPaymentService');
const Order = require('../models/Order');
const logger = require('../config/logger');
const { asyncHandler, BusinessError } = require('../middleware/errorHandler');
const { authenticateToken, checkOrderOwnership, authorize } = require('../middleware/auth');

/**
 * POST /api/payments/escrow/create
 * Create escrow payment for an order
 */
router.post('/escrow/create', 
  authenticateToken,
  authorize(['customer', 'admin']),
  asyncHandler(async (req, res) => {
    const { orderId, paymentMethodId } = req.body;

    if (!orderId || !paymentMethodId) {
      throw new BusinessError('Order ID and payment method are required', 'MISSING_PAYMENT_DATA');
    }

    // Verify order ownership
    const order = await Order.findOne({ orderId });
    if (!order) {
      throw new BusinessError('Order not found', 'ORDER_NOT_FOUND');
    }

    if (order.customer.dmlogUserId !== req.user.userId && req.user.role !== 'admin') {
      throw new BusinessError('Access denied', 'ORDER_ACCESS_DENIED');
    }

    logger.logBusinessEvent('escrow_payment_create_request', {
      orderId,
      userId: req.user.userId,
      paymentMethod: paymentMethodId.substring(0, 8) + '...'
    });

    const result = await escrowPaymentService.createEscrowPayment(
      orderId, 
      paymentMethodId, 
      req.user.stripeCustomerId
    );

    res.status(201).json({
      success: true,
      message: 'Escrow payment created successfully',
      data: result
    });
  })
);

/**
 * POST /api/payments/escrow/:orderId/capture
 * Capture authorized escrow payment when production starts
 */
router.post('/escrow/:orderId/capture',
  authenticateToken,
  authorize(['maker', 'admin', 'system']),
  asyncHandler(async (req, res) => {
    const { orderId } = req.params;

    // Verify order and maker relationship
    const order = await Order.findOne({ orderId });
    if (!order) {
      throw new BusinessError('Order not found', 'ORDER_NOT_FOUND');
    }

    if (req.user.role !== 'admin' && req.user.role !== 'system') {
      if (order.makers.selected?.makerUserId !== req.user.userId) {
        throw new BusinessError('Access denied - not assigned maker', 'MAKER_ACCESS_DENIED');
      }
    }

    logger.logBusinessEvent('escrow_payment_capture_request', {
      orderId,
      userId: req.user.userId,
      role: req.user.role
    });

    const result = await escrowPaymentService.captureEscrowPayment(orderId);

    res.json({
      success: true,
      message: 'Payment captured and held in escrow',
      data: result
    });
  })
);

/**
 * PUT /api/payments/escrow/:orderId/milestone
 * Update escrow milestone (triggers release conditions check)
 */
router.put('/escrow/:orderId/milestone',
  authenticateToken,
  authorize(['maker', 'admin', 'system']),
  asyncHandler(async (req, res) => {
    const { orderId } = req.params;
    const { milestone } = req.body;

    if (!milestone) {
      throw new BusinessError('Milestone is required', 'MISSING_MILESTONE');
    }

    const validMilestones = [
      'orderStarted',
      'orderCompleted', 
      'qualityApproved',
      'shipped',
      'delivered',
      'customerApproved'
    ];

    if (!validMilestones.includes(milestone)) {
      throw new BusinessError(
        'Invalid milestone', 
        'INVALID_MILESTONE',
        400,
        { validMilestones }
      );
    }

    // Verify order access
    const order = await Order.findOne({ orderId });
    if (!order) {
      throw new BusinessError('Order not found', 'ORDER_NOT_FOUND');
    }

    if (req.user.role !== 'admin' && req.user.role !== 'system') {
      if (order.makers.selected?.makerUserId !== req.user.userId) {
        throw new BusinessError('Access denied - not assigned maker', 'MAKER_ACCESS_DENIED');
      }
    }

    logger.logBusinessEvent('escrow_milestone_update_request', {
      orderId,
      milestone,
      userId: req.user.userId
    });

    const result = await escrowPaymentService.updateEscrowMilestone(orderId, milestone);

    res.json({
      success: true,
      message: `Milestone ${milestone} updated successfully`,
      data: result
    });
  })
);

/**
 * POST /api/payments/escrow/:orderId/release
 * Manually release escrow payment (admin only)
 */
router.post('/escrow/:orderId/release',
  authenticateToken,
  authorize(['admin']),
  asyncHandler(async (req, res) => {
    const { orderId } = req.params;
    const { reason } = req.body;

    logger.logBusinessEvent('escrow_manual_release_request', {
      orderId,
      reason,
      adminUserId: req.user.userId
    });

    const result = await escrowPaymentService.releaseEscrowPayment(
      orderId, 
      reason || 'manual_admin_release'
    );

    res.json({
      success: true,
      message: 'Escrow payment released to maker',
      data: result
    });
  })
);

/**
 * POST /api/payments/escrow/:orderId/dispute
 * Initiate dispute for escrow payment
 */
router.post('/escrow/:orderId/dispute',
  authenticateToken,
  checkOrderOwnership,
  asyncHandler(async (req, res) => {
    const { orderId } = req.params;
    const { reason, description, evidence = [] } = req.body;

    if (!reason || !description) {
      throw new BusinessError('Dispute reason and description are required', 'MISSING_DISPUTE_DATA');
    }

    const validReasons = [
      'quality_issues',
      'not_delivered',
      'wrong_specifications',
      'damaged_item',
      'communication_issues',
      'other'
    ];

    if (!validReasons.includes(reason)) {
      throw new BusinessError(
        'Invalid dispute reason',
        'INVALID_DISPUTE_REASON',
        400,
        { validReasons }
      );
    }

    logger.logBusinessEvent('escrow_dispute_initiation_request', {
      orderId,
      reason,
      initiatedBy: req.user.userId,
      evidenceCount: evidence.length
    });

    const result = await escrowPaymentService.initiateDispute(
      orderId,
      { reason, description },
      req.user.userId,
      evidence
    );

    res.status(201).json({
      success: true,
      message: 'Dispute initiated successfully',
      data: result
    });
  })
);

/**
 * PUT /api/payments/escrow/:orderId/dispute/resolve
 * Resolve escrow dispute (admin only)
 */
router.put('/escrow/:orderId/dispute/resolve',
  authenticateToken,
  authorize(['admin']),
  asyncHandler(async (req, res) => {
    const { orderId } = req.params;
    const { resolution, refundAmount = 0, notes } = req.body;

    const validResolutions = [
      'release_to_maker',
      'refund_customer', 
      'partial_refund',
      'no_action'
    ];

    if (!resolution || !validResolutions.includes(resolution)) {
      throw new BusinessError(
        'Valid resolution is required',
        'INVALID_RESOLUTION',
        400,
        { validResolutions }
      );
    }

    if (resolution === 'partial_refund' && (!refundAmount || refundAmount <= 0)) {
      throw new BusinessError('Refund amount required for partial refund', 'MISSING_REFUND_AMOUNT');
    }

    logger.logBusinessEvent('escrow_dispute_resolution_request', {
      orderId,
      resolution,
      refundAmount,
      adminUserId: req.user.userId,
      notes
    });

    const result = await escrowPaymentService.resolveDispute(
      orderId,
      resolution,
      req.user.userId,
      refundAmount
    );

    res.json({
      success: true,
      message: 'Dispute resolved successfully',
      data: result
    });
  })
);

/**
 * GET /api/payments/escrow/:orderId/status
 * Get escrow payment status
 */
router.get('/escrow/:orderId/status',
  authenticateToken,
  checkOrderOwnership,
  asyncHandler(async (req, res) => {
    const { orderId } = req.params;

    const status = await escrowPaymentService.getEscrowStatus(orderId);

    if (!status.found) {
      return res.status(404).json({
        success: false,
        message: 'Escrow payment not found for this order'
      });
    }

    res.json({
      success: true,
      data: status
    });
  })
);

/**
 * GET /api/payments/pricing/calculate
 * Calculate pricing breakdown for escrow payment
 */
router.get('/pricing/calculate/:orderId',
  authenticateToken,
  checkOrderOwnership,
  asyncHandler(async (req, res) => {
    const { orderId } = req.params;
    
    const order = req.order; // Set by checkOrderOwnership middleware

    const pricing = escrowPaymentService.calculateEscrowPricing(order);

    res.json({
      success: true,
      data: {
        orderId: order.orderId,
        breakdown: {
          orderAmount: pricing.orderAmount,
          serviceFee: pricing.serviceFee,
          stripeFee: pricing.stripeFee,
          totalAmount: pricing.totalAmount
        },
        escrow: {
          escrowAmount: pricing.escrowAmount,
          makerPayout: pricing.makerPayout,
          holdPeriod: '7 days after delivery',
          serviceFeeRate: '5%'
        },
        timeline: {
          paymentDue: 'Before production starts',
          escrowHold: '7 days after delivery confirmation',
          disputePeriod: '14 days from payment'
        }
      }
    });
  })
);

/**
 * POST /api/payments/webhook/stripe
 * Handle Stripe webhooks for payment events
 */
router.post('/webhook/stripe',
  express.raw({ type: 'application/json' }),
  asyncHandler(async (req, res) => {
    const sig = req.headers['stripe-signature'];
    const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

    let event;
    try {
      event = stripe.webhooks.constructEvent(req.body, sig, webhookSecret);
    } catch (err) {
      logger.error('Stripe webhook signature verification failed:', err);
      return res.status(400).json({ error: 'Webhook signature verification failed' });
    }

    logger.debug('Stripe webhook received:', { type: event.type, id: event.id });

    try {
      switch (event.type) {
        case 'payment_intent.succeeded':
          await handlePaymentIntentSucceeded(event.data.object);
          break;
          
        case 'payment_intent.payment_failed':
          await handlePaymentIntentFailed(event.data.object);
          break;
          
        case 'transfer.created':
          await handleTransferCreated(event.data.object);
          break;
          
        case 'transfer.failed':
          await handleTransferFailed(event.data.object);
          break;
          
        default:
          logger.debug(`Unhandled Stripe webhook: ${event.type}`);
      }

      res.status(200).json({ received: true });
    } catch (error) {
      logger.error('Error processing Stripe webhook:', error);
      res.status(500).json({ error: 'Webhook processing failed' });
    }
  })
);

/**
 * Stripe webhook handlers
 */
async function handlePaymentIntentSucceeded(paymentIntent) {
  try {
    const orderId = paymentIntent.metadata.orderId;
    if (!orderId) return;

    logger.logBusinessEvent('stripe_payment_succeeded', {
      paymentIntentId: paymentIntent.id,
      orderId,
      amount: paymentIntent.amount_received / 100
    });

    // Update order payment status if needed
    await Order.updateOne(
      { orderId },
      { 
        'pricing.payment.status': 'completed',
        'pricing.payment.completedAt': new Date()
      }
    );
  } catch (error) {
    logger.error('Error handling payment success webhook:', error);
  }
}

async function handlePaymentIntentFailed(paymentIntent) {
  try {
    const orderId = paymentIntent.metadata.orderId;
    if (!orderId) return;

    logger.logBusinessEvent('stripe_payment_failed', {
      paymentIntentId: paymentIntent.id,
      orderId,
      failureReason: paymentIntent.last_payment_error?.message
    });

    // Update order status
    await Order.updateOne(
      { orderId },
      { 
        status: 'payment_failed',
        'pricing.payment.status': 'failed',
        'pricing.payment.failureReason': paymentIntent.last_payment_error?.message
      }
    );
  } catch (error) {
    logger.error('Error handling payment failure webhook:', error);
  }
}

async function handleTransferCreated(transfer) {
  try {
    const orderId = transfer.metadata.orderId;
    if (!orderId) return;

    logger.logBusinessEvent('stripe_transfer_created', {
      transferId: transfer.id,
      orderId,
      amount: transfer.amount / 100,
      destination: transfer.destination
    });
  } catch (error) {
    logger.error('Error handling transfer created webhook:', error);
  }
}

async function handleTransferFailed(transfer) {
  try {
    const orderId = transfer.metadata.orderId;
    if (!orderId) return;

    logger.error('Stripe transfer failed:', {
      transferId: transfer.id,
      orderId,
      failureCode: transfer.failure_code,
      failureMessage: transfer.failure_message
    });

    // Handle transfer failure - may need manual intervention
    // Could trigger notifications to admin team
  } catch (error) {
    logger.error('Error handling transfer failure webhook:', error);
  }
}

module.exports = router;