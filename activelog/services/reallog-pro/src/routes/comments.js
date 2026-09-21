import express from 'express';
import logger from '../lib/logger.js';

export default function createCommentRoutes(commentService) {
  const router = express.Router();

  router.get('/:platform/:postId', async (req, res) => {
    try {
      const comments = await commentService.fetchComments(req.params.platform, req.params.postId);
      res.json({ success: true, data: comments });
    } catch (error) {
      logger.error('Fetch comments error:', error);
      res.status(500).json({ error: 'Failed to fetch comments', message: error.message });
    }
  });

  router.post('/moderate', async (req, res) => {
    try {
      const result = await commentService.moderateComment(req.body.comment, req.body.action);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Moderate comment error:', error);
      res.status(500).json({ error: 'Failed to moderate comment', message: error.message });
    }
  });

  router.get('/analytics', async (req, res) => {
    try {
      const analytics = await commentService.getAnalytics();
      res.json({ success: true, data: analytics });
    } catch (error) {
      logger.error('Get comment analytics error:', error);
      res.status(500).json({ error: 'Failed to get analytics', message: error.message });
    }
  });

  return router;
}