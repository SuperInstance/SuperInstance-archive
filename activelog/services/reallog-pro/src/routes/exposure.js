import express from 'express';
import logger from '../lib/logger.js';

export default function createExposureRoutes(exposureService) {
  const router = express.Router();

  router.post('/optimize', async (req, res) => {
    try {
      const result = await exposureService.optimizeExposure(req.body.contentId, req.body.goals);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Optimize exposure error:', error);
      res.status(500).json({ error: 'Failed to optimize exposure', message: error.message });
    }
  });

  router.get('/reports', async (req, res) => {
    try {
      const reports = await exposureService.getOptimizationReports(req.query.timeRange);
      res.json({ success: true, data: reports });
    } catch (error) {
      logger.error('Get exposure reports error:', error);
      res.status(500).json({ error: 'Failed to get reports', message: error.message });
    }
  });

  return router;
}
