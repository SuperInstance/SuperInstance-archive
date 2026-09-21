const express = require('express');
const router = express.Router();
const Order = require('../models/Order');
const orderPipelineService = require('../services/orderPipelineService');
const pricingAggregationService = require('../services/pricingAggregationService');
const proximityMatchingService = require('../services/proximityMatchingService');
const logger = require('../config/logger');
const { asyncHandler, BusinessError, NotFoundError } = require('../middleware/errorHandler');
const { 
  authenticateToken, 
  authenticateDMLog, 
  authenticateMakerLog,
  checkOrderOwnership,
  authorize 
} = require('../middleware/auth');

/**
 * POST /api/orders/dmlog/create
 * Create new order from DMLog
 */
router.post('/dmlog/create', authenticateDMLog, asyncHandler(async (req, res) => {
  const dmlogOrderData = req.body;

  // Validate required fields
  if (!dmlogOrderData.orderId || !dmlogOrderData.customer || !dmlogOrderData.specifications) {
    throw new BusinessError('Missing required order data', 'MISSING_ORDER_DATA');
  }

  logger.logBusinessEvent('dmlog_order_create_request', {
    dmlogOrderId: dmlogOrderData.orderId,
    customerId: dmlogOrderData.customer.userId,
    material: dmlogOrderData.specifications.material
  });

  // Process the order through the pipeline
  const result = await orderPipelineService.processDMLogOrder(dmlogOrderData);

  res.status(201).json({
    success: true,
    message: 'Order created and processing started',
    data: result
  });
}));

/**
 * GET /api/orders/:orderId
 * Get order details
 */
router.get('/:orderId', authenticateToken, checkOrderOwnership, asyncHandler(async (req, res) => {
  const order = req.order; // Set by checkOrderOwnership middleware

  // Filter sensitive information based on user role
  const filteredOrder = await filterOrderByUserRole(order, req.user);

  res.json({
    success: true,
    data: filteredOrder
  });
}));

/**
 * GET /api/orders
 * Get orders list with filtering and pagination
 */
router.get('/', authenticateToken, asyncHandler(async (req, res) => {
  const {
    page = 1,
    limit = 20,
    status,
    material,
    urgency,
    startDate,
    endDate,
    sortBy = 'createdAt',
    sortOrder = 'desc'
  } = req.query;

  const { userId, role, app } = req.user;

  // Build query based on user role and app
  let query = {};
  
  if (role === 'admin' || role === 'system') {
    // Admin can see all orders
  } else if (app === 'dmlog') {
    query['customer.dmlogUserId'] = userId;
  } else if (app === 'makerlog') {
    query['makers.selected.makerUserId'] = userId;
  } else {
    throw new BusinessError('Invalid user context', 'INVALID_USER_CONTEXT');
  }

  // Apply filters
  if (status) query.status = status;
  if (material) query['printSpecs.material.type'] = material;
  if (urgency) query['printSpecs.requirements.urgency'] = urgency;
  
  if (startDate || endDate) {
    query.createdAt = {};
    if (startDate) query.createdAt.$gte = new Date(startDate);
    if (endDate) query.createdAt.$lte = new Date(endDate);
  }

  // Execute query with pagination
  const skip = (page - 1) * limit;
  const sort = { [sortBy]: sortOrder === 'desc' ? -1 : 1 };

  const [orders, totalCount] = await Promise.all([
    Order.find(query)
      .sort(sort)
      .skip(skip)
      .limit(parseInt(limit))
      .lean(),
    Order.countDocuments(query)
  ]);

  // Filter orders based on user role
  const filteredOrders = await Promise.all(
    orders.map(order => filterOrderByUserRole(order, req.user))
  );

  const totalPages = Math.ceil(totalCount / limit);

  res.json({
    success: true,
    data: {
      orders: filteredOrders,
      pagination: {
        currentPage: parseInt(page),
        totalPages,
        totalCount,
        hasNextPage: page < totalPages,
        hasPrevPage: page > 1
      }
    }
  });
}));

/**
 * PUT /api/orders/:orderId/status
 * Update order status
 */
router.put('/:orderId/status', 
  authenticateToken, 
  authorize(['admin', 'system', 'maker']), 
  checkOrderOwnership,
  asyncHandler(async (req, res) => {
    const { status, notes } = req.body;
    const order = req.order;

    if (!status) {
      throw new BusinessError('Status is required', 'MISSING_STATUS');
    }

    // Validate status transition
    const validTransitions = getValidStatusTransitions(order.status);
    if (!validTransitions.includes(status)) {
      throw new BusinessError(
        `Invalid status transition from ${order.status} to ${status}`,
        'INVALID_STATUS_TRANSITION'
      );
    }

    // Update order status
    await order.updateStatus(status, notes);

    logger.logBusinessEvent('order_status_updated', {
      orderId: order.orderId,
      oldStatus: order.status,
      newStatus: status,
      userId: req.user.userId,
      app: req.user.app
    });

    res.json({
      success: true,
      message: 'Order status updated successfully',
      data: {
        orderId: order.orderId,
        status: order.status,
        updatedAt: order.updatedAt
      }
    });
  })
);

/**
 * POST /api/orders/:orderId/quotes/request
 * Request quotes for an order (manual trigger)
 */
router.post('/:orderId/quotes/request',
  authenticateToken,
  authorize(['admin', 'system', 'customer']),
  checkOrderOwnership,
  asyncHandler(async (req, res) => {
    const order = req.order;
    const { urgency, maxMakers = 10 } = req.body;

    // Check if order is in correct state for quote requests
    if (!['pending', 'analyzing', 'matching_makers'].includes(order.status)) {
      throw new BusinessError(
        'Order is not in a state that allows quote requests',
        'INVALID_ORDER_STATE'
      );
    }

    // Update urgency if provided
    if (urgency && urgency !== order.printSpecs.requirements.urgency) {
      order.printSpecs.requirements.urgency = urgency;
      if (urgency === 'rush') {
        order.metadata.priority = 'high';
      }
      await order.save();
    }

    // Find eligible makers
    const proximityResult = await proximityMatchingService.findMakersNearCustomer(
      order.customer.shippingAddress.coordinates,
      order.printSpecs,
      { maxMakers, urgentOnly: urgency === 'rush' }
    );

    // Request quotes
    const quotes = await pricingAggregationService.aggregatePricing(
      order.orderId,
      proximityResult.makers
    );

    // Update order with quotes
    order.makers.eligible = proximityResult.makers;
    order.pricing.quotes = quotes.quotes.recommended;
    order.status = 'quotes_received';
    await order.save();

    logger.logBusinessEvent('quotes_requested_manually', {
      orderId: order.orderId,
      makersFound: proximityResult.makers.length,
      quotesReceived: quotes.totalQuotes,
      userId: req.user.userId
    });

    res.json({
      success: true,
      message: 'Quotes requested successfully',
      data: {
        orderId: order.orderId,
        makersFound: proximityResult.makers.length,
        quotesReceived: quotes.totalQuotes,
        priceRange: quotes.priceStatistics,
        recommendations: quotes.recommendations
      }
    });
  })
);

/**
 * POST /api/orders/:orderId/maker/select
 * Select a maker for the order
 */
router.post('/:orderId/maker/select',
  authenticateToken,
  authorize(['admin', 'system', 'customer']),
  checkOrderOwnership,
  asyncHandler(async (req, res) => {
    const order = req.order;
    const { makerId, quoteId } = req.body;

    if (!makerId) {
      throw new BusinessError('Maker ID is required', 'MISSING_MAKER_ID');
    }

    // Check if order is in correct state
    if (order.status !== 'quotes_received') {
      throw new BusinessError(
        'Order must have quotes available to select a maker',
        'INVALID_ORDER_STATE'
      );
    }

    // Find the selected maker in eligible makers
    const selectedMakerInfo = order.makers.eligible.find(m => m.makerId === makerId);
    if (!selectedMakerInfo) {
      throw new BusinessError('Maker not eligible for this order', 'MAKER_NOT_ELIGIBLE');
    }

    // Find the quote
    const selectedQuote = order.pricing.quotes.find(q => 
      q.makerId === makerId && (!quoteId || q._id.toString() === quoteId)
    );
    if (!selectedQuote) {
      throw new BusinessError('Quote not found for selected maker', 'QUOTE_NOT_FOUND');
    }

    // Update order with selected maker
    order.makers.selected = {
      makerId: selectedMakerInfo.makerId,
      makerUserId: selectedMakerInfo.makerUserId,
      businessName: selectedMakerInfo.businessName,
      contactInfo: {
        // Contact info would be populated from maker profile
        email: 'contact@maker.com', // Placeholder
        phone: null
      },
      selectedAt: new Date(),
      quote: selectedQuote.quote
    };

    order.pricing.finalPricing = {
      subtotal: selectedQuote.quote.totalPrice,
      tax: selectedQuote.quote.totalPrice * 0.08, // 8% tax (simplified)
      serviceFee: selectedQuote.quote.totalPrice * 0.05, // 5% service fee
      totalAmount: selectedQuote.quote.totalPrice * 1.13 // Including tax and fees
    };

    order.status = 'maker_selected';
    await order.save();

    logger.logBusinessEvent('maker_selected', {
      orderId: order.orderId,
      makerId: makerId,
      quoteAmount: selectedQuote.quote.totalPrice,
      userId: req.user.userId
    });

    res.json({
      success: true,
      message: 'Maker selected successfully',
      data: {
        orderId: order.orderId,
        selectedMaker: order.makers.selected,
        finalPricing: order.pricing.finalPricing,
        nextStep: 'payment_processing'
      }
    });
  })
);

/**
 * POST /api/orders/:orderId/cancel
 * Cancel an order
 */
router.post('/:orderId/cancel',
  authenticateToken,
  checkOrderOwnership,
  asyncHandler(async (req, res) => {
    const order = req.order;
    const { reason } = req.body;

    // Check if order can be cancelled
    const cancellableStates = [
      'pending', 'analyzing', 'matching_makers', 'quotes_requested', 
      'quotes_received', 'maker_selected'
    ];

    if (!cancellableStates.includes(order.status)) {
      throw new BusinessError(
        'Order cannot be cancelled in current state',
        'ORDER_NOT_CANCELLABLE'
      );
    }

    // Update order status
    await order.updateStatus('cancelled', reason || 'Cancelled by customer');

    // Add cancellation metadata
    order.metadata.cancellation = {
      cancelledBy: req.user.userId,
      cancelledAt: new Date(),
      reason: reason || 'No reason provided',
      app: req.user.app
    };

    await order.save();

    logger.logBusinessEvent('order_cancelled', {
      orderId: order.orderId,
      cancelledBy: req.user.userId,
      reason: reason,
      previousStatus: order.status
    });

    res.json({
      success: true,
      message: 'Order cancelled successfully',
      data: {
        orderId: order.orderId,
        status: order.status,
        cancellation: order.metadata.cancellation
      }
    });
  })
);

/**
 * GET /api/orders/:orderId/tracking
 * Get order tracking information
 */
router.get('/:orderId/tracking',
  authenticateToken,
  checkOrderOwnership,
  asyncHandler(async (req, res) => {
    const order = req.order;

    const trackingData = {
      orderId: order.orderId,
      status: order.status,
      timeline: generateOrderTimeline(order),
      currentStage: getCurrentStage(order),
      estimatedCompletion: order.production?.estimatedCompletion,
      shipping: order.shipping ? {
        method: order.shipping.method,
        trackingNumber: order.shipping.trackingNumber,
        carrier: order.shipping.carrier,
        estimatedDelivery: order.shipping.estimatedDelivery
      } : null,
      progress: {
        overall: calculateOverallProgress(order),
        stages: order.production?.stages || []
      }
    };

    res.json({
      success: true,
      data: trackingData
    });
  })
);

/**
 * Helper function to filter order data based on user role
 */
async function filterOrderByUserRole(order, user) {
  const filtered = { ...order };

  // Remove sensitive information based on role
  if (user.role !== 'admin' && user.role !== 'system') {
    // Remove internal notes and sensitive data
    delete filtered.metadata?.internalNotes;
    delete filtered.makers?.eligible; // Only show selected maker to non-admins
    
    // For customers, hide maker internal information
    if (user.app === 'dmlog') {
      if (filtered.makers?.selected) {
        delete filtered.makers.selected.contactInfo;
        delete filtered.makers.selected.quote?.breakdown;
      }
    }
    
    // For makers, hide customer internal information
    if (user.app === 'makerlog') {
      delete filtered.customer?.internalNotes;
      delete filtered.pricing?.quotes; // Hide other makers' quotes
    }
  }

  return filtered;
}

/**
 * Get valid status transitions for current status
 */
function getValidStatusTransitions(currentStatus) {
  const transitions = {
    'pending': ['analyzing', 'cancelled'],
    'analyzing': ['matching_makers', 'failed', 'cancelled'],
    'matching_makers': ['quotes_requested', 'failed', 'cancelled'],
    'quotes_requested': ['quotes_received', 'failed', 'cancelled'],
    'quotes_received': ['maker_selected', 'cancelled'],
    'maker_selected': ['confirmed', 'cancelled'],
    'confirmed': ['paid', 'cancelled'],
    'paid': ['printing', 'cancelled'],
    'printing': ['quality_check', 'failed'],
    'quality_check': ['approved', 'failed'],
    'approved': ['shipping'],
    'shipping': ['delivered', 'failed'],
    'delivered': ['completed'],
    'cancelled': [], // Terminal state
    'failed': [], // Terminal state
    'completed': [] // Terminal state
  };

  return transitions[currentStatus] || [];
}

/**
 * Generate order timeline for tracking
 */
function generateOrderTimeline(order) {
  const timeline = [];
  
  timeline.push({
    stage: 'Order Placed',
    status: 'completed',
    timestamp: order.createdAt,
    description: 'Order received from DMLog'
  });

  if (order.metadata?.processingTime?.analyzed) {
    timeline.push({
      stage: 'Analysis Complete',
      status: 'completed',
      timestamp: order.metadata.processingTime.analyzed,
      description: 'Order requirements analyzed'
    });
  }

  if (order.metadata?.processingTime?.quoted) {
    timeline.push({
      stage: 'Quotes Received',
      status: 'completed',
      timestamp: order.metadata.processingTime.quoted,
      description: 'Maker quotes available'
    });
  }

  if (order.makers?.selected?.selectedAt) {
    timeline.push({
      stage: 'Maker Selected',
      status: 'completed',
      timestamp: order.makers.selected.selectedAt,
      description: `Selected ${order.makers.selected.businessName}`
    });
  }

  if (order.metadata?.processingTime?.paid) {
    timeline.push({
      stage: 'Payment Processed',
      status: 'completed',
      timestamp: order.metadata.processingTime.paid,
      description: 'Payment confirmed'
    });
  }

  if (order.production?.startedAt) {
    timeline.push({
      stage: 'Production Started',
      status: 'completed',
      timestamp: order.production.startedAt,
      description: 'Printing in progress'
    });
  }

  // Add future stages based on current status
  const futureStages = getFutureStages(order.status);
  futureStages.forEach(stage => {
    timeline.push({
      stage: stage.name,
      status: 'pending',
      timestamp: null,
      description: stage.description
    });
  });

  return timeline.sort((a, b) => {
    if (!a.timestamp) return 1;
    if (!b.timestamp) return -1;
    return new Date(a.timestamp) - new Date(b.timestamp);
  });
}

/**
 * Get current stage information
 */
function getCurrentStage(order) {
  const stageMap = {
    'pending': 'Order Processing',
    'analyzing': 'Analyzing Requirements',
    'matching_makers': 'Finding Makers',
    'quotes_requested': 'Requesting Quotes',
    'quotes_received': 'Awaiting Maker Selection',
    'maker_selected': 'Awaiting Payment',
    'confirmed': 'Payment Processing',
    'paid': 'In Production Queue',
    'printing': 'Printing in Progress',
    'quality_check': 'Quality Inspection',
    'approved': 'Preparing for Shipping',
    'shipping': 'In Transit',
    'delivered': 'Delivered',
    'completed': 'Order Complete',
    'cancelled': 'Order Cancelled',
    'failed': 'Order Failed'
  };

  return stageMap[order.status] || 'Unknown';
}

/**
 * Get future stages based on current status
 */
function getFutureStages(currentStatus) {
  // Simplified - in reality would be more complex
  const allStages = [
    { name: 'Quality Check', description: 'Final quality inspection' },
    { name: 'Shipping', description: 'Package in transit' },
    { name: 'Delivered', description: 'Order delivered to customer' }
  ];

  // Return appropriate future stages based on current status
  if (['delivered', 'completed', 'cancelled', 'failed'].includes(currentStatus)) {
    return [];
  }

  return allStages;
}

/**
 * Calculate overall progress percentage
 */
function calculateOverallProgress(order) {
  const statusProgress = {
    'pending': 5,
    'analyzing': 15,
    'matching_makers': 25,
    'quotes_requested': 35,
    'quotes_received': 45,
    'maker_selected': 55,
    'confirmed': 65,
    'paid': 70,
    'printing': 80,
    'quality_check': 90,
    'approved': 95,
    'shipping': 98,
    'delivered': 100,
    'completed': 100,
    'cancelled': 0,
    'failed': 0
  };

  return statusProgress[order.status] || 0;
}

module.exports = router;