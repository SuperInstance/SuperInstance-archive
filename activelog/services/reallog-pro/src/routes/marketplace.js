import express from 'express';
import logger from '../lib/logger.js';

export default function createMarketplaceRoutes(marketplaceService) {
  const router = express.Router();

  router.post('/collaborations', async (req, res) => {
    try {
      const result = await marketplaceService.createCollaborationRequest(req.body);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Create collaboration error:', error);
      res.status(500).json({ error: 'Failed to create collaboration', message: error.message });
    }
  });

  router.get('/collaborations', async (req, res) => {
    try {
      const collaborations = await marketplaceService.getCollaborations(req.query);
      res.json({ success: true, data: collaborations });
    } catch (error) {
      logger.error('Get collaborations error:', error);
      res.status(500).json({ error: 'Failed to get collaborations', message: error.message });
    }
  });

  router.post('/proposals', async (req, res) => {
    try {
      const result = await marketplaceService.submitProposal(req.body.collaborationId, req.body);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Submit proposal error:', error);
      res.status(500).json({ error: 'Failed to submit proposal', message: error.message });
    }
  });

  return router;
}
