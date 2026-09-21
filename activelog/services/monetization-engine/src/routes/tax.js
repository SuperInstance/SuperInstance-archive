const express = require('express');
const { TAX_RATES } = require('../config/stripe');
const logger = require('../utils/logger');

const router = express.Router();

// Calculate tax for a transaction
router.post('/calculate', async (req, res) => {
  try {
    const { amount, country, state, zipCode } = req.body;
    
    if (!amount || amount <= 0) {
      return res.status(400).json({
        error: 'Valid amount is required'
      });
    }
    
    let taxRate = 0;
    let taxAmount = 0;
    
    // Simple tax calculation based on country/state
    if (country === 'US' && state) {
      taxRate = TAX_RATES.US.states[state] || TAX_RATES.US.default;
    } else if (TAX_RATES[country]) {
      taxRate = TAX_RATES[country].default;
    }
    
    taxAmount = Math.round(amount * taxRate);
    
    res.json({
      success: true,
      tax: {
        rate: taxRate,
        amount: taxAmount,
        total: amount + taxAmount,
        jurisdiction: state || country || 'Unknown'
      }
    });
  } catch (error) {
    logger.error('Failed to calculate tax:', error);
    res.status(500).json({
      error: 'Failed to calculate tax',
      message: error.message
    });
  }
});

module.exports = router;