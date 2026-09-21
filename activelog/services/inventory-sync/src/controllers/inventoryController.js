const express = require('express');
const router = express.Router();
const { asyncHandler, BusinessError } = require('../middleware/errorHandler');
const realTimeInventoryService = require('../services/realTimeInventoryService');
const multiLocationService = require('../services/multiLocationService');
const qrCodeService = require('../services/qrCodeService');

// Get real-time inventory status
router.get('/status/:locationId/:itemId', asyncHandler(async (req, res) => {
  const { locationId, itemId } = req.params;
  
  const status = await realTimeInventoryService.getInventoryStatus(locationId, itemId);
  
  res.json({
    success: true,
    status,
    locationId,
    itemId,
    timestamp: new Date().toISOString()
  });
}));

// Update inventory (stock change)
router.post('/update/:locationId/:itemId', asyncHandler(async (req, res) => {
  const { locationId, itemId } = req.params;
  const { changeType, newQuantity, oldQuantity, reason, userId, metadata } = req.body;
  
  const update = await realTimeInventoryService.trackInventoryChange(locationId, itemId, {
    changeType: changeType || 'manual_update',
    oldQuantity: oldQuantity || 0,
    newQuantity,
    reason: reason || 'manual_adjustment',
    userId: userId || 'system',
    metadata: metadata || {}
  });
  
  res.json({
    success: true,
    update,
    message: 'Inventory updated successfully'
  });
}));

// Get inventory across multiple locations
router.get('/multi-location/:itemId', asyncHandler(async (req, res) => {
  const { itemId } = req.params;
  const { locations } = req.query;
  
  const locationIds = locations ? locations.split(',') : null;
  const inventory = await multiLocationService.getMultiLocationInventory(itemId, locationIds);
  
  res.json({
    success: true,
    inventory
  });
}));

// Generate QR code for inventory item
router.post('/qr-code/:locationId/:itemId', asyncHandler(async (req, res) => {
  const { locationId, itemId } = req.params;
  const { size, darkColor, lightColor, format } = req.body;
  
  const qrCode = await qrCodeService.generateInventoryQR(locationId, itemId, {
    size,
    darkColor,
    lightColor,
    format
  });
  
  res.json({
    success: true,
    qrCode,
    message: 'QR code generated successfully'
  });
}));

// Bulk update inventory
router.post('/bulk-update/:locationId', asyncHandler(async (req, res) => {
  const { locationId } = req.params;
  const { updates } = req.body;
  
  if (!Array.isArray(updates)) {
    throw new BusinessError('Updates must be an array', 'INVALID_FORMAT');
  }
  
  const results = await realTimeInventoryService.bulkUpdateInventory(locationId, updates);
  
  res.json({
    success: true,
    results,
    message: `${results.length} items updated successfully`
  });
}));

// Get inventory movement analytics
router.get('/analytics/:locationId/:itemId', asyncHandler(async (req, res) => {
  const { locationId, itemId } = req.params;
  const { timeframe } = req.query;
  
  const analytics = await realTimeInventoryService.getInventoryMovementAnalytics(
    locationId, 
    itemId, 
    timeframe || '24h'
  );
  
  res.json({
    success: true,
    analytics
  });
}));

module.exports = router;