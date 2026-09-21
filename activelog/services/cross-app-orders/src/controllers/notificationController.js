const express = require('express');
const router = express.Router();
const { asyncHandler } = require('../middleware/errorHandler');

// Pickup notification system endpoints
router.post('/send', asyncHandler(async (req, res) => {
  res.json({ success: true, message: 'Notifications API - Coming soon' });
}));

module.exports = router;