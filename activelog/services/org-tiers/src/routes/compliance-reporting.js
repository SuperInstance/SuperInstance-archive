import express from 'express';

export function createComplianceReportingRoutes(complianceReportingService) {
    const router = express.Router();

    router.post('/generate-report', async (req, res) => {
        try {
            const { orgId, framework, period } = req.body;
            const report = await complianceReportingService.generateComplianceReport(orgId, framework, period);
            res.json({ success: true, report });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.post('/schedule-reports', async (req, res) => {
        try {
            const { orgId, frameworks, frequency } = req.body;
            const schedule = await complianceReportingService.scheduleAutomaticReports(orgId, frameworks, frequency);
            res.json({ success: true, schedule });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await complianceReportingService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}