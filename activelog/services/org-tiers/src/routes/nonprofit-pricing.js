import express from 'express';

export function createNonprofitPricingRoutes(nonprofitPricingService) {
    const router = express.Router();

    router.post('/apply-nonprofit-status', async (req, res) => {
        try {
            const { orgId, nonprofitType, verificationData } = req.body;
            const application = await nonprofitPricingService.applyForNonprofitStatus(orgId, nonprofitType, verificationData);
            res.json({ success: true, application });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.post('/verify-nonprofit', async (req, res) => {
        try {
            const { orgId, applicationId, verificationResult } = req.body;
            const result = await nonprofitPricingService.verifyNonprofitStatus(orgId, applicationId, verificationResult);
            res.json({ success: true, result });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.post('/calculate-pricing', async (req, res) => {
        try {
            const { orgId, tier, userCount, billingCycle } = req.body;
            const pricing = await nonprofitPricingService.calculateNonprofitPricing(orgId, tier, userCount, billingCycle);
            res.json({ success: true, pricing });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/nonprofit-types', async (req, res) => {
        try {
            const types = await nonprofitPricingService.getSupportedNonprofitTypes();
            res.json({ success: true, types });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await nonprofitPricingService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}