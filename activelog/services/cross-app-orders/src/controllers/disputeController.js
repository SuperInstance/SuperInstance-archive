const express = require('express');
const router = express.Router();
const { asyncHandler } = require('../middleware/errorHandler');

// Dispute resolution system endpoints  
router.get('/cases', asyncHandler(async (req, res) => {
  res.json({ success: true, message: 'Dispute resolution API - Coming soon' });
}));

module.exports = router;