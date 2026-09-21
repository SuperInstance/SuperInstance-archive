import express from 'express';
import logger from '../lib/logger.js';

export default function createProfileRoutes(profileService) {
  const router = express.Router();

  router.post('/', async (req, res) => {
    try {
      const result = await profileService.createProfile(req.body);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Create profile error:', error);
      res.status(500).json({ error: 'Failed to create profile', message: error.message });
    }
  });

  router.get('/', async (req, res) => {
    try {
      const profiles = await profileService.getProfiles();
      res.json({ success: true, data: profiles });
    } catch (error) {
      logger.error('Get profiles error:', error);
      res.status(500).json({ error: 'Failed to get profiles', message: error.message });
    }
  });

  router.post('/:id/optimize', async (req, res) => {
    try {
      const result = await profileService.optimizeProfile(req.params.id, req.body.goals);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Optimize profile error:', error);
      res.status(500).json({ error: 'Failed to optimize profile', message: error.message });
    }
  });

  return router;
}
