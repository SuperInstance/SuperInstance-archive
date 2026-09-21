import express from 'express';

export function createPayAsYouGoRoutes(payAsYouGoService) {
    const router = express.Router();

    router.post('/record-usage', async (req, res) => {
        try {
            const { orgId, resourceType, amount, metadata } = req.body;
            const usage = await payAsYouGoService.recordUsage(orgId, resourceType, amount, metadata);
            res.json({ success: true, usage });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.post('/calculate-cost', async (req, res) => {
        try {
            const { orgId, usageData } = req.body;
            const cost = await payAsYouGoService.calculateCost(orgId, usageData);
            res.json({ success: true, cost });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/usage-report/:orgId/:period', async (req, res) => {
        try {
            const { orgId, period } = req.params;
            const report = await payAsYouGoService.generateUsageReport(orgId, period);
            res.json({ success: true, report });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/pricing', async (req, res) => {
        try {
            const pricing = await payAsYouGoService.getCurrentPricing();
            res.json({ success: true, pricing });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await payAsYouGoService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}