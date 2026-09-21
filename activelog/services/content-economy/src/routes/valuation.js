import express from 'express';
const router = express.Router();

export default function createValuationRoutes(valuationService) {
    router.post('/calculate/:contentId', async (req, res) => {
        try {
            const { contentId } = req.params;
            const { metrics } = req.body;
            const value = await valuationService.calculateContentValue(contentId, metrics);
            res.json({ success: true, contentId, value: value.toString() });
        } catch (error) {
            res.status(500).json({ error: 'Failed to calculate content value', details: error.message });
        }
    });

    router.get('/valuation/:contentId', async (req, res) => {
        try {
            const { contentId } = req.params;
            const valuation = await valuationService.getContentValuation(contentId);
            res.json({ valuation });
        } catch (error) {
            res.status(500).json({ error: 'Failed to get content valuation', details: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await valuationService.getStats();
            res.json(stats);
        } catch (error) {
            res.status(500).json({ error: 'Failed to get stats', details: error.message });
        }
    });

    return router;
}