import express from 'express';

export function createInvoiceAutomationRoutes(invoiceAutomationService) {
    const router = express.Router();

    router.post('/generate', async (req, res) => {
        try {
            const { orgId, period, charges } = req.body;
            const invoice = await invoiceAutomationService.generateInvoice(orgId, period, charges);
            res.json({ success: true, invoice });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await invoiceAutomationService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}