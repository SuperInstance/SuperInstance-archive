import express from 'express';
import logger from '../lib/logger.js';

export default function createVideoRoutes(videoService) {
  const router = express.Router();

  router.post('/upload', async (req, res) => {
    try {
      const result = await videoService.uploadVideo(req.body, req.body.options);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Upload video error:', error);
      res.status(500).json({ error: 'Failed to upload video', message: error.message });
    }
  });

  router.get('/', async (req, res) => {
    try {
      const videos = await videoService.getVideos(req.query);
      res.json({ success: true, data: videos });
    } catch (error) {
      logger.error('Get videos error:', error);
      res.status(500).json({ error: 'Failed to get videos', message: error.message });
    }
  });

  router.get('/:id', async (req, res) => {
    try {
      const video = await videoService.getVideo(req.params.id);
      res.json({ success: true, data: video });
    } catch (error) {
      logger.error('Get video error:', error);
      res.status(500).json({ error: 'Failed to get video', message: error.message });
    }
  });

  return router;
}
