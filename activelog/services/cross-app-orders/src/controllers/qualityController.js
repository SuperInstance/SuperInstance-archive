const express = require('express');
const router = express.Router();
const { asyncHandler } = require('../middleware/errorHandler');

// Quality assurance workflow endpoints
router.get('/standards', asyncHandler(async (req, res) => {
  res.json({ success: true, message: 'Quality standards API - Coming soon' });
}));

module.exports = router;