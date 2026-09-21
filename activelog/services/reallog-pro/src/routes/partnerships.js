import express from 'express';
import logger from '../lib/logger.js';

export default function createPartnershipRoutes(partnershipService) {
  const router = express.Router();

  router.post('/', async (req, res) => {
    try {
      const result = await partnershipService.createPartnership(req.body);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Create partnership error:', error);
      res.status(500).json({ error: 'Failed to create partnership', message: error.message });
    }
  });

  router.get('/', async (req, res) => {
    try {
      const partnerships = await partnershipService.getPartnerships(req.query);
      res.json({ success: true, data: partnerships });
    } catch (error) {
      logger.error('Get partnerships error:', error);
      res.status(500).json({ error: 'Failed to get partnerships', message: error.message });
    }
  });

  router.get('/campaigns', async (req, res) => {
    try {
      const campaigns = await partnershipService.getCampaigns(req.query);
      res.json({ success: true, data: campaigns });
    } catch (error) {
      logger.error('Get campaigns error:', error);
      res.status(500).json({ error: 'Failed to get campaigns', message: error.message });
    }
  });

  router.post('/applications', async (req, res) => {
    try {
      const result = await partnershipService.submitApplication(req.body.campaignId, req.body);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Submit application error:', error);
      res.status(500).json({ error: 'Failed to submit application', message: error.message });
    }
  });

  return router;
}
