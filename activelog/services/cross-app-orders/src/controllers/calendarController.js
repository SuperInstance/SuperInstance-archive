const express = require('express');
const router = express.Router();
const { asyncHandler } = require('../middleware/errorHandler');

// Maker availability calendar endpoints
router.get('/availability', asyncHandler(async (req, res) => {
  res.json({ success: true, message: 'Calendar API - Coming soon' });
}));

module.exports = router;