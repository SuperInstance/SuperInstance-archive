import express from 'express';
import logger from '../lib/logger.js';

export default function createAnalyticsRoutes(analyticsService) {
  const router = express.Router();

  router.post('/track', async (req, res) => {
    try {
      const result = await analyticsService.trackEvent(req.body);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Track event error:', error);
      res.status(500).json({ error: 'Failed to track event', message: error.message });
    }
  });

  router.get('/reports/:type', async (req, res) => {
    try {
      const report = await analyticsService.generateReport(req.params.type, req.query);
      res.json({ success: true, data: report });
    } catch (error) {
      logger.error('Generate report error:', error);
      res.status(500).json({ error: 'Failed to generate report', message: error.message });
    }
  });

  router.get('/dashboard/:id', async (req, res) => {
    try {
      const dashboard = await analyticsService.getDashboardData(req.params.id);
      res.json({ success: true, data: dashboard });
    } catch (error) {
      logger.error('Get dashboard error:', error);
      res.status(500).json({ error: 'Failed to get dashboard', message: error.message });
    }
  });

  return router;
}
