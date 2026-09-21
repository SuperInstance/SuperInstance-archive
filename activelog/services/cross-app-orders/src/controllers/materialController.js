const express = require('express');
const router = express.Router();
const { asyncHandler } = require('../middleware/errorHandler');

// Material specification standardization endpoints
router.get('/specifications', asyncHandler(async (req, res) => {
  res.json({ success: true, message: 'Material specifications API - Coming soon' });
}));

module.exports = router;