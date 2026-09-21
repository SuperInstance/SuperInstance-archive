import express from 'express';

export function createUsageTrackingRoutes(usageTrackingService) {
    const router = express.Router();

    router.post('/track-usage', async (req, res) => {
        try {
            const { orgId, departmentId, userId, resourceType, amount, metadata } = req.body;
            const usage = await usageTrackingService.trackUsage(orgId, departmentId, userId, resourceType, amount, metadata);
            res.json({ success: true, usage });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/department-usage/:orgId/:departmentId/:period', async (req, res) => {
        try {
            const { orgId, departmentId, period } = req.params;
            const usage = await usageTrackingService.getDepartmentUsage(orgId, departmentId, period);
            res.json({ success: true, usage });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.post('/set-alerts', async (req, res) => {
        try {
            const { orgId, departmentId, alertThresholds, notificationChannels } = req.body;
            const alert = await usageTrackingService.setUsageAlerts(orgId, departmentId, alertThresholds, notificationChannels);
            res.json({ success: true, alert });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await usageTrackingService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}