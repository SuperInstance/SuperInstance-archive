import express from 'express';
import logger from '../lib/logger.js';

export default function createDiscountRoutes(discountService) {
  const router = express.Router();

  router.post('/', async (req, res) => {
    try {
      const result = await discountService.createDiscountCode(req.body);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Create discount code error:', error);
      res.status(500).json({ error: 'Failed to create discount code', message: error.message });
    }
  });

  router.post('/validate', async (req, res) => {
    try {
      const result = await discountService.validateDiscountCode(req.body.code, req.body.orderData);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Validate discount code error:', error);
      res.status(500).json({ error: 'Failed to validate discount code', message: error.message });
    }
  });

  router.post('/redeem', async (req, res) => {
    try {
      const result = await discountService.redeemDiscountCode(req.body.code, req.body.orderData);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Redeem discount code error:', error);
      res.status(500).json({ error: 'Failed to redeem discount code', message: error.message });
    }
  });

  return router;
}
