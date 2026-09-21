import express from 'express';
const router = express.Router();

export default function createAnalyticsRoutes(analyticsService) {
    router.post('/track', async (req, res) => {
        try {
            const { eventType, userId, contentId, metadata } = req.body;
            const event = await analyticsService.trackEvent(eventType, userId, contentId, metadata);
            res.json({ success: true, event });
        } catch (error) {
            res.status(500).json({ error: 'Failed to track event', details: error.message });
        }
    });

    router.get('/dashboard/:creatorId', async (req, res) => {
        try {
            const { creatorId } = req.params;
            const { timeframe } = req.query;
            const dashboard = await analyticsService.getCreatorDashboard(creatorId, timeframe);
            res.json({ dashboard });
        } catch (error) {
            res.status(500).json({ error: 'Failed to get creator dashboard', details: error.message });
        }
    });

    router.get('/report/:creatorId/:reportType', async (req, res) => {
        try {
            const { creatorId, reportType } = req.params;
            const { timeframe } = req.query;
            const report = await analyticsService.generateReports(creatorId, reportType, timeframe);
            res.json({ report });
        } catch (error) {
            res.status(500).json({ error: 'Failed to generate report', details: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await analyticsService.getStats();
            res.json(stats);
        } catch (error) {
            res.status(500).json({ error: 'Failed to get stats', details: error.message });
        }
    });

    return router;
}