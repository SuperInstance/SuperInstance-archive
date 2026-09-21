import express from 'express';

export function createChargebackRoutes(chargebackService) {
    const router = express.Router();

    router.post('/allocate', async (req, res) => {
        try {
            const { orgId, departmentId, charges } = req.body;
            const allocation = await chargebackService.allocateCharges(orgId, departmentId, charges);
            res.json({ success: true, allocation });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await chargebackService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}