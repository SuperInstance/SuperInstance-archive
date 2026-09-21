const express = require('express');
const router = express.Router();
const Maker = require('../models/Maker');
const proximityMatchingService = require('../services/proximityMatchingService');
const logger = require('../config/logger');
const { asyncHandler, BusinessError } = require('../middleware/errorHandler');
const { authenticateToken, checkMakerOwnership, authorize } = require('../middleware/auth');

/**
 * GET /api/makers/search
 * Search makers by location and capabilities
 */
router.get('/search', asyncHandler(async (req, res) => {
  const { 
    lat, 
    lng, 
    radius = 50,
    material,
    technology,
    minRating = 0,
    maxResults = 20 
  } = req.query;

  if (!lat || !lng) {
    throw new BusinessError('Location coordinates are required', 'MISSING_COORDINATES');
  }

  const customerLocation = { 
    latitude: parseFloat(lat), 
    longitude: parseFloat(lng) 
  };

  const searchOptions = {
    radius: parseInt(radius),
    maxMakers: parseInt(maxResults),
    minQuality: parseFloat(minRating)
  };

  // Mock order specs for search
  const orderSpecs = {
    material: { type: material || 'PLA' },
    requirements: { urgency: 'standard' }
  };

  const result = await proximityMatchingService.findMakersNearCustomer(
    customerLocation,
    orderSpecs,
    searchOptions
  );

  res.json({
    success: true,
    data: {
      makers: result.makers,
      searchParams: {
        location: customerLocation,
        radius: result.searchRadius,
        material,
        technology
      },
      stats: result.searchStats
    }
  });
}));

/**
 * GET /api/makers/:makerId
 * Get maker profile
 */
router.get('/:makerId', asyncHandler(async (req, res) => {
  const { makerId } = req.params;
  
  const maker = await Maker.findOne({ makerId });
  if (!maker) {
    throw new BusinessError('Maker not found', 'MAKER_NOT_FOUND');
  }

  res.json({
    success: true,
    data: maker
  });
}));

module.exports = router;