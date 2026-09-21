import express from 'express';

export function createRoleBasedLimitsRoutes(roleBasedLimitsService) {
    const router = express.Router();

    router.post('/set-limits', async (req, res) => {
        try {
            const { orgId, role, limits } = req.body;
            const result = await roleBasedLimitsService.setRoleLimits(orgId, role, limits);
            res.json({ success: true, data: result });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/user-limits/:userId/:role/:orgId', async (req, res) => {
        try {
            const { userId, role, orgId } = req.params;
            const limits = await roleBasedLimitsService.getUserLimits(userId, role, orgId);
            res.json({ success: true, limits });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.post('/validate-request', async (req, res) => {
        try {
            const { userId, role, orgId, resourceType, requestedAmount } = req.body;
            const validation = await roleBasedLimitsService.validateResourceRequest(
                userId, role, orgId, resourceType, requestedAmount
            );
            res.json({ success: true, validation });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await roleBasedLimitsService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}