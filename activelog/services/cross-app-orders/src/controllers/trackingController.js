const express = require('express');
const router = express.Router();
const { asyncHandler } = require('../middleware/errorHandler');
const { authenticateToken, checkOrderOwnership } = require('../middleware/auth');

/**
 * GET /api/tracking/:orderId
 * Get order tracking information
 */
router.get('/:orderId', 
  authenticateToken,
  checkOrderOwnership,
  asyncHandler(async (req, res) => {
    const order = req.order;

    const trackingData = {
      orderId: order.orderId,
      status: order.status,
      progress: calculateProgress(order.status),
      timeline: generateTimeline(order),
      currentLocation: order.shipping?.currentLocation,
      estimatedDelivery: order.shipping?.estimatedDelivery
    };

    res.json({
      success: true,
      data: trackingData
    });
  })
);

function calculateProgress(status) {
  const statusProgress = {
    'pending': 10, 'analyzing': 20, 'matching_makers': 30,
    'quotes_received': 40, 'maker_selected': 50, 'confirmed': 60,
    'paid': 70, 'printing': 80, 'quality_check': 90,
    'shipping': 95, 'delivered': 100, 'completed': 100
  };
  return statusProgress[status] || 0;
}

function generateTimeline(order) {
  // Simplified timeline generation
  return [
    { stage: 'Order Placed', timestamp: order.createdAt, completed: true },
    { stage: 'In Production', timestamp: order.production?.startedAt, completed: !!order.production?.startedAt },
    { stage: 'Quality Check', timestamp: null, completed: false },
    { stage: 'Shipping', timestamp: order.shipping?.shippedAt, completed: !!order.shipping?.shippedAt },
    { stage: 'Delivered', timestamp: order.shipping?.deliveredAt, completed: !!order.shipping?.deliveredAt }
  ];
}

module.exports = router;