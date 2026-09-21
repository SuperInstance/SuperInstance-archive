import express from 'express';

export function createOrganizationAnalyticsRoutes(organizationAnalyticsService) {
    const router = express.Router();

    router.post('/generate-report', async (req, res) => {
        try {
            const { orgId, period } = req.body;
            const report = await organizationAnalyticsService.generateOrgReport(orgId, period);
            res.json({ success: true, report });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await organizationAnalyticsService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}