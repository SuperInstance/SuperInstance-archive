import express from 'express';
import { body, param, query, validationResult } from 'express-validator';

const router = express.Router();

export default function createIPLicensingRoutes(ipLicensingService) {
    router.post('/create', async (req, res) => {
        try {
            const { contentId, creatorId, licenseType, customTerms, royaltyModel } = req.body;
            const license = await ipLicensingService.createLicense(contentId, creatorId, licenseType, customTerms, royaltyModel);
            res.json({ success: true, license });
        } catch (error) {
            res.status(500).json({ error: 'Failed to create license', details: error.message });
        }
    });

    router.post('/purchase/:licenseId', async (req, res) => {
        try {
            const { licenseId } = req.params;
            const { licenseeId, paymentDetails } = req.body;
            const result = await ipLicensingService.purchaseLicense(licenseId, licenseeId, paymentDetails);
            res.json({ success: true, ...result });
        } catch (error) {
            res.status(500).json({ error: 'Failed to purchase license', details: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await ipLicensingService.getStats();
            res.json(stats);
        } catch (error) {
            res.status(500).json({ error: 'Failed to get stats', details: error.message });
        }
    });

    return router;
}