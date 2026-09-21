import express from 'express';
import logger from '../lib/logger.js';

export default function createSocialRoutes(socialService) {
  const router = express.Router();

  router.get('/', async (req, res) => {
    try {
      const analytics = await socialService.getAnalytics();
      res.json({ success: true, data: analytics });
    } catch (error) {
      logger.error('Get social analytics error:', error);
      res.status(500).json({ error: 'Failed to get analytics', message: error.message });
    }
  });

  router.post('/post', async (req, res) => {
    try {
      const result = await socialService.postContent(req.body.content, req.body.platforms);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Post content error:', error);
      res.status(500).json({ error: 'Failed to post content', message: error.message });
    }
  });

  router.post('/schedule', async (req, res) => {
    try {
      const result = await socialService.schedulePost(req.body.content, req.body.platforms, req.body.scheduledTime);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Schedule post error:', error);
      res.status(500).json({ error: 'Failed to schedule post', message: error.message });
    }
  });

  router.get('/scheduled', async (req, res) => {
    try {
      const posts = await socialService.getScheduledPosts();
      res.json({ success: true, data: posts });
    } catch (error) {
      logger.error('Get scheduled posts error:', error);
      res.status(500).json({ error: 'Failed to get scheduled posts', message: error.message });
    }
  });

  return router;
}