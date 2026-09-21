const express = require('express');
const { MARKETPLACE_FEES } = require('../config/stripe');
const logger = require('../utils/logger');

const router = express.Router();

// Get marketplace fee structure
router.get('/fees', (req, res) => {
  try {
    res.json({
      success: true,
      fees: {
        commission: MARKETPLACE_FEES.commission,
        paymentProcessing: MARKETPLACE_FEES.paymentProcessing,
        minimumFee: MARKETPLACE_FEES.minimumFee
      }
    });
  } catch (error) {
    logger.error('Failed to get marketplace fees:', error);
    res.status(500).json({
      error: 'Failed to get marketplace fees',
      message: error.message
    });
  }
});

// Calculate transaction fees
router.post('/calculate-fees', (req, res) => {
  try {
    const { amount, productType = 'digital', paymentMethod = 'stripe' } = req.body;
    
    if (!amount || amount <= 0) {
      return res.status(400).json({
        error: 'Valid amount is required'
      });
    }
    
    // Calculate commission fee
    const commissionRate = MARKETPLACE_FEES.commission[productType] || MARKETPLACE_FEES.commission.digital;
    const commissionFee = Math.round(amount * commissionRate);
    
    // Calculate payment processing fee
    const processingRate = MARKETPLACE_FEES.paymentProcessing[paymentMethod] || MARKETPLACE_FEES.paymentProcessing.stripe;
    const processingFee = Math.round(amount * processingRate) + (MARKETPLACE_FEES.paymentProcessing.stripeFee || 0);
    
    const totalFees = Math.max(commissionFee + processingFee, MARKETPLACE_FEES.minimumFee);
    const sellerReceives = amount - totalFees;
    
    res.json({
      success: true,
      calculation: {
        grossAmount: amount,
        commissionFee,
        processingFee,
        totalFees,
        sellerReceives,
        breakdown: {
          commissionRate: (commissionRate * 100).toFixed(1) + '%',
          processingRate: (processingRate * 100).toFixed(1) + '%'
        }
      }
    });
  } catch (error) {
    logger.error('Failed to calculate marketplace fees:', error);
    res.status(500).json({
      error: 'Failed to calculate fees',
      message: error.message
    });
  }
});

module.exports = router;