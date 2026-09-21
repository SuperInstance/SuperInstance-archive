import express from 'express';
const router = express.Router();

export default function createDonationRoutes(donationService) {
    router.post('/create', async (req, res) => {
        try {
            const { donorId, creatorId, amount, type, message, goalId } = req.body;
            const donation = await donationService.createDonation(donorId, creatorId, amount, type, message, goalId);
            res.json({ success: true, donation });
        } catch (error) {
            res.status(500).json({ error: 'Failed to create donation', details: error.message });
        }
    });

    router.post('/process/:donationId', async (req, res) => {
        try {
            const { donationId } = req.params;
            const { paymentDetails } = req.body;
            const result = await donationService.processDonation(donationId, paymentDetails);
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: 'Failed to process donation', details: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await donationService.getStats();
            res.json(stats);
        } catch (error) {
            res.status(500).json({ error: 'Failed to get stats', details: error.message });
        }
    });

    return router;
}