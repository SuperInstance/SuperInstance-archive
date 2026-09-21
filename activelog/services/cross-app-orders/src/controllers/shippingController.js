const express = require('express');
const router = express.Router();
const { asyncHandler } = require('../middleware/errorHandler');

// Shipping and label generation endpoints
router.post('/labels/generate', asyncHandler(async (req, res) => {
  res.json({ success: true, message: 'Shipping labels API - Coming soon' });
}));

module.exports = router;