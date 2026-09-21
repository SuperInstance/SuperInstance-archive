import express from 'express';
import logger from '../lib/logger.js';

export default function createAffiliateRoutes(affiliateService) {
  const router = express.Router();

  router.post('/links', async (req, res) => {
    try {
      const result = await affiliateService.createAffiliateLink(req.body);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Create affiliate link error:', error);
      res.status(500).json({ error: 'Failed to create affiliate link', message: error.message });
    }
  });

  router.get('/links', async (req, res) => {
    try {
      const links = await affiliateService.getAffiliateLinks();
      res.json({ success: true, data: links });
    } catch (error) {
      logger.error('Get affiliate links error:', error);
      res.status(500).json({ error: 'Failed to get affiliate links', message: error.message });
    }
  });

  router.post('/track/click/:linkId', async (req, res) => {
    try {
      const result = await affiliateService.trackClick(req.params.linkId, req.body);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Track click error:', error);
      res.status(500).json({ error: 'Failed to track click', message: error.message });
    }
  });

  return router;
}
