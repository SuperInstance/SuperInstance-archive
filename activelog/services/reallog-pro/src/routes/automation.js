import express from 'express';
import logger from '../lib/logger.js';

export default function createAutomationRoutes(automationService) {
  const router = express.Router();

  router.post('/', async (req, res) => {
    try {
      const result = await automationService.createAutomation(req.body);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Create automation error:', error);
      res.status(500).json({ error: 'Failed to create automation', message: error.message });
    }
  });

  router.get('/', async (req, res) => {
    try {
      const automations = await automationService.getAutomations();
      res.json({ success: true, data: automations });
    } catch (error) {
      logger.error('Get automations error:', error);
      res.status(500).json({ error: 'Failed to get automations', message: error.message });
    }
  });

  router.get('/analytics', async (req, res) => {
    try {
      const analytics = await automationService.getAnalytics();
      res.json({ success: true, data: analytics });
    } catch (error) {
      logger.error('Get automation analytics error:', error);
      res.status(500).json({ error: 'Failed to get analytics', message: error.message });
    }
  });

  return router;
}
