import express from 'express';
const router = express.Router();

export default function createRevenueShareRoutes(revenueShareService) {
    router.post('/create', async (req, res) => {
        try {
            const { collaborationId, participants, shares, terms } = req.body;
            const revenueShare = await revenueShareService.createRevenueShare(collaborationId, participants, shares, terms);
            res.json({ success: true, revenueShare });
        } catch (error) {
            res.status(500).json({ error: 'Failed to create revenue share', details: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await revenueShareService.getStats();
            res.json(stats);
        } catch (error) {
            res.status(500).json({ error: 'Failed to get stats', details: error.message });
        }
    });

    return router;
}