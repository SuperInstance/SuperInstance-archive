const express = require('express');
const router = express.Router();
const pricingAggregationService = require('../services/pricingAggregationService');
const { asyncHandler } = require('../middleware/errorHandler');

/**
 * POST /api/pricing/aggregate
 * Get aggregated pricing from multiple makers
 */
router.post('/aggregate', asyncHandler(async (req, res) => {
  const { orderId, eligibleMakers } = req.body;

  const result = await pricingAggregationService.aggregatePricing(orderId, eligibleMakers);

  res.json({
    success: true,
    data: result
  });
}));

module.exports = router;