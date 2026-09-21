const express = require('express');
const router = express.Router();
const { requireAuth } = require('../utils/auth');

// Placeholder for character routes - will integrate with existing character system
router.use(requireAuth);

router.get('/', (req, res) => {
  res.json({ 
    success: true, 
    message: 'Character routes - Integration with existing character system pending',
    data: []
  });
});

module.exports = router;