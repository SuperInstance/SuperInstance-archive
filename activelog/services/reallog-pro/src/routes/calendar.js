import express from 'express';
import logger from '../lib/logger.js';

export default function createCalendarRoutes(calendarService) {
  const router = express.Router();

  router.post('/schedule', async (req, res) => {
    try {
      const result = await calendarService.scheduleContent(req.body);
      res.json({ success: true, data: result });
    } catch (error) {
      logger.error('Schedule content error:', error);
      res.status(500).json({ error: 'Failed to schedule content', message: error.message });
    }
  });

  router.get('/', async (req, res) => {
    try {
      const calendar = await calendarService.getCalendar(req.query.timeRange);
      res.json({ success: true, data: calendar });
    } catch (error) {
      logger.error('Get calendar error:', error);
      res.status(500).json({ error: 'Failed to get calendar', message: error.message });
    }
  });

  return router;
}
