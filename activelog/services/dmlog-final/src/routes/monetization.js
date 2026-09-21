import express from 'express';

const router = express.Router();

// POST /api/monetization/subscribe - Create subscription
router.post('/subscribe', async (req, res) => {
  try {
    const { monetization } = req.app.locals.services;
    const subscription = await monetization.createSubscription(
      req.user.id, 
      req.body.planId, 
      req.body.paymentMethodId
    );
    res.status(201).json(subscription);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/monetization/cancel - Cancel subscription
router.post('/cancel', async (req, res) => {
  try {
    const { monetization } = req.app.locals.services;
    const result = await monetization.cancelSubscription(req.user.id);
    res.json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/monetization/donate - Process donation
router.post('/donate', async (req, res) => {
  try {
    const { monetization } = req.app.locals.services;
    const donation = await monetization.processDonation(
      req.body.creatorId,
      req.user.id,
      req.body.amount,
      req.body.message
    );
    res.json(donation);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// GET /api/monetization/analytics - Get revenue analytics
router.get('/analytics', async (req, res) => {
  try {
    const { monetization } = req.app.locals.services;
    const analytics = await monetization.getRevenueAnalytics(req.user.id, req.query.timeframe);
    res.json(analytics);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/monetization/affiliate - Generate affiliate link
router.post('/affiliate', async (req, res) => {
  try {
    const { monetization } = req.app.locals.services;
    const link = await monetization.generateAffiliateLink(req.user.id, req.body.campaignId);
    res.json(link);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

export default router;