const express = require('express');
const router = express.Router();
const { asyncHandler, BusinessError } = require('../middleware/errorHandler');
const multiLocationService = require('../services/multiLocationService');

// Get all locations
router.get('/', asyncHandler(async (req, res) => {
  const { type, status, features } = req.query;
  
  const filters = {};
  if (type) filters.type = type;
  if (status) filters.status = status;
  if (features) filters.features = features.split(',');
  
  const locations = await multiLocationService.getAllLocations(filters);
  
  res.json({
    success: true,
    locations,
    count: locations.length
  });
}));

// Get specific location
router.get('/:locationId', asyncHandler(async (req, res) => {
  const { locationId } = req.params;
  
  const location = await multiLocationService.getLocation(locationId);
  if (!location) {
    throw new BusinessError('Location not found', 'LOCATION_NOT_FOUND', 404);
  }
  
  res.json({
    success: true,
    location
  });
}));

// Register new location
router.post('/', asyncHandler(async (req, res) => {
  const locationData = req.body;
  
  const location = await multiLocationService.registerLocation(locationData);
  
  res.status(201).json({
    success: true,
    location,
    message: 'Location registered successfully'
  });
}));

// Find nearby locations
router.post('/nearby', asyncHandler(async (req, res) => {
  const { coordinates, radius, filters } = req.body;
  
  if (!coordinates || !coordinates.lat || !coordinates.lng) {
    throw new BusinessError('Valid coordinates required', 'INVALID_COORDINATES');
  }
  
  const locations = await multiLocationService.findNearbyLocations(
    coordinates, 
    radius || 50, 
    filters || {}
  );
  
  res.json({
    success: true,
    locations,
    count: locations.length,
    searchRadius: radius || 50
  });
}));

// Get location operating status
router.get('/:locationId/status', asyncHandler(async (req, res) => {
  const { locationId } = req.params;
  const { checkTime } = req.query;
  
  const status = await multiLocationService.getLocationOperatingStatus(
    locationId, 
    checkTime ? new Date(checkTime) : null
  );
  
  res.json({
    success: true,
    locationId,
    operatingStatus: status
  });
}));

// Get location capacity
router.get('/:locationId/capacity', asyncHandler(async (req, res) => {
  const { locationId } = req.params;
  
  const capacity = await multiLocationService.getLocationCapacity(locationId);
  
  res.json({
    success: true,
    capacity
  });
}));

// Transfer inventory between locations
router.post('/transfer', asyncHandler(async (req, res) => {
  const { fromLocationId, toLocationId, itemId, quantity, transferData } = req.body;
  
  if (!fromLocationId || !toLocationId || !itemId || !quantity) {
    throw new BusinessError('Missing required transfer parameters', 'MISSING_PARAMETERS');
  }
  
  const transfer = await multiLocationService.transferInventory(
    fromLocationId,
    toLocationId, 
    itemId,
    quantity,
    transferData || {}
  );
  
  res.json({
    success: true,
    transfer,
    message: 'Inventory transfer initiated'
  });
}));

module.exports = router;