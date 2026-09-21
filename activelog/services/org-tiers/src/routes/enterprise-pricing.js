import express from 'express';

export function createEnterprisePricingRoutes(enterprisePricingService) {
    const router = express.Router();

    router.post('/calculate-pricing', async (req, res) => {
        try {
            const { tier, userCount, billingCycle, addons } = req.body;
            const pricing = await enterprisePricingService.calculatePricing(tier, userCount, billingCycle, addons);
            res.json({ success: true, pricing });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.post('/generate-quote', async (req, res) => {
        try {
            const { orgId, tier, userCount, billingCycle, addons, customizations } = req.body;
            const quote = await enterprisePricingService.generateQuote(orgId, tier, userCount, billingCycle, addons, customizations);
            res.json({ success: true, quote });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/tiers', async (req, res) => {
        try {
            const tiers = await enterprisePricingService.getAvailableTiers();
            res.json({ success: true, tiers });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await enterprisePricingService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}