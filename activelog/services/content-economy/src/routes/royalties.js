import express from 'express';
const router = express.Router();

export default function createRoyaltyRoutes(royaltyService) {
    router.post('/create-agreement', async (req, res) => {
        try {
            const { contentId, creatorId, royaltyRate, terms } = req.body;
            const agreement = await royaltyService.createRoyaltyAgreement(contentId, creatorId, royaltyRate, terms);
            res.json({ success: true, agreement });
        } catch (error) {
            res.status(500).json({ error: 'Failed to create royalty agreement', details: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await royaltyService.getStats();
            res.json(stats);
        } catch (error) {
            res.status(500).json({ error: 'Failed to get stats', details: error.message });
        }
    });

    return router;
}