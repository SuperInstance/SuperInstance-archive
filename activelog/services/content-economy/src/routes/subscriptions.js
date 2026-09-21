import express from 'express';
const router = express.Router();

export default function createSubscriptionRoutes(subscriptionService) {
    router.post('/create', async (req, res) => {
        try {
            const { subscriberId, creatorId, tier, billingCycle } = req.body;
            const subscription = await subscriptionService.createSubscription(subscriberId, creatorId, tier, billingCycle);
            res.json({ success: true, subscription });
        } catch (error) {
            res.status(500).json({ error: 'Failed to create subscription', details: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await subscriptionService.getStats();
            res.json(stats);
        } catch (error) {
            res.status(500).json({ error: 'Failed to get stats', details: error.message });
        }
    });

    return router;
}