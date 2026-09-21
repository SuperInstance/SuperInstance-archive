import express from 'express';
const router = express.Router();

export default function createContentAgingRoutes(contentAgingService) {
    router.post('/apply-model', async (req, res) => {
        try {
            const { contentId, model, basePrice, createdAt } = req.body;
            const currentValue = await contentAgingService.applyAgingModel(contentId, model, basePrice, createdAt);
            res.json({ success: true, currentValue: currentValue.toString() });
        } catch (error) {
            res.status(500).json({ error: 'Failed to apply aging model', details: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await contentAgingService.getStats();
            res.json(stats);
        } catch (error) {
            res.status(500).json({ error: 'Failed to get stats', details: error.message });
        }
    });

    return router;
}