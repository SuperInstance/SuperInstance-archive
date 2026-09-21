const express = require('express');
const { WHITE_LABEL_TIERS } = require('../config/stripe');
const logger = require('../utils/logger');

const router = express.Router();

// Get enterprise licensing options
router.get('/enterprise', (req, res) => {
  try {
    const enterpriseOptions = {
      plans: [
        {
          id: 'enterprise-starter',
          name: 'Enterprise Starter',
          price: 9999, // $99.99/month
          features: [
            'Up to 100 users',
            'Priority support',
            'Custom integrations',
            'Advanced analytics',
            'SSO integration',
            'Dedicated account manager'
          ]
        },
        {
          id: 'enterprise-professional',
          name: 'Enterprise Professional',
          price: 19999, // $199.99/month
          features: [
            'Up to 500 users',
            '24/7 phone support',
            'Custom development',
            'Advanced security features',
            'On-premise deployment option',
            'Training and onboarding'
          ]
        },
        {
          id: 'enterprise-unlimited',
          name: 'Enterprise Unlimited',
          price: 'custom',
          features: [
            'Unlimited users',
            'Dedicated infrastructure',
            'White-label options',
            'Custom SLA',
            'Source code access',
            'Dedicated support team'
          ]
        }
      ]
    };
    
    res.json({
      success: true,
      enterpriseLicensing: enterpriseOptions
    });
  } catch (error) {
    logger.error('Failed to get enterprise licensing:', error);
    res.status(500).json({
      error: 'Failed to get enterprise licensing options',
      message: error.message
    });
  }
});

// Get white-label pricing
router.get('/white-label', (req, res) => {
  try {
    const whiteLabelOptions = Object.entries(WHITE_LABEL_TIERS).map(([key, tier]) => ({
      id: key,
      name: tier.name,
      price: tier.price,
      priceId: tier.priceId,
      features: tier.features
    }));
    
    res.json({
      success: true,
      whiteLabelTiers: whiteLabelOptions
    });
  } catch (error) {
    logger.error('Failed to get white-label pricing:', error);
    res.status(500).json({
      error: 'Failed to get white-label pricing',
      message: error.message
    });
  }
});

module.exports = router;