import express from 'express';
const router = express.Router();

export default function createDigitalOwnershipRoutes(digitalOwnershipService) {
    router.post('/create-asset', async (req, res) => {
        try {
            const { contentId, creatorId, ownershipType, metadata, supply } = req.body;
            const asset = await digitalOwnershipService.createDigitalAsset(contentId, creatorId, ownershipType, metadata, supply);
            res.json({ success: true, asset });
        } catch (error) {
            res.status(500).json({ error: 'Failed to create digital asset', details: error.message });
        }
    });

    router.post('/mint/:assetId', async (req, res) => {
        try {
            const { assetId } = req.params;
            const { ownerId, paymentDetails } = req.body;
            const ownership = await digitalOwnershipService.mintOwnership(assetId, ownerId, paymentDetails);
            res.json({ success: true, ownership });
        } catch (error) {
            res.status(500).json({ error: 'Failed to mint ownership', details: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await digitalOwnershipService.getStats();
            res.json(stats);
        } catch (error) {
            res.status(500).json({ error: 'Failed to get stats', details: error.message });
        }
    });

    return router;
}