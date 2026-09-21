import express from 'express';

export function createBudgetAllocationRoutes(budgetAllocationService) {
    const router = express.Router();

    router.post('/allocate-budget', async (req, res) => {
        try {
            const { orgId, departmentId, budget, period, limits } = req.body;
            const allocation = await budgetAllocationService.allocateBudget(orgId, departmentId, budget, period, limits);
            res.json({ success: true, allocation });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.post('/check-budget', async (req, res) => {
        try {
            const { orgId, departmentId, requestedAmount, resourceType } = req.body;
            const check = await budgetAllocationService.checkBudgetAvailability(orgId, departmentId, requestedAmount, resourceType);
            res.json({ success: true, check });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/budget-status/:orgId/:departmentId', async (req, res) => {
        try {
            const { orgId, departmentId } = req.params;
            const status = await budgetAllocationService.getBudgetStatus(orgId, departmentId);
            res.json({ success: true, status });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await budgetAllocationService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}