import express from 'express';
import { body, param, query, validationResult } from 'express-validator';

const router = express.Router();

export default function createTieredAccessRoutes(tieredAccessService) {
    
    // Create tiered access
    router.post('/create',
        [
            body('contentId').notEmpty().withMessage('Content ID is required'),
            body('userId').notEmpty().withMessage('User ID is required'),
            body('tier').isIn(['free', 'basic', 'premium', 'pro', 'enterprise']).withMessage('Invalid tier'),
            body('duration').optional().isInt({ min: 1 }).withMessage('Duration must be positive integer'),
            body('customFeatures').optional().isObject().withMessage('Custom features must be object')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { contentId, userId, tier, duration, customFeatures } = req.body;

                const accessData = await tieredAccessService.createTieredAccess(
                    contentId,
                    userId,
                    tier,
                    duration,
                    customFeatures
                );

                res.json({
                    success: true,
                    access: accessData
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to create tiered access',
                    details: error.message
                });
            }
        }
    );

    // Check user access
    router.get('/check/:contentId/:userId',
        [
            param('contentId').notEmpty().withMessage('Content ID is required'),
            param('userId').notEmpty().withMessage('User ID is required'),
            query('feature').optional().isString().withMessage('Feature must be string'),
            query('level').optional().isInt({ min: 0 }).withMessage('Level must be non-negative')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { contentId, userId } = req.params;
                const { feature, level } = req.query;

                const accessResult = await tieredAccessService.checkAccess(
                    contentId,
                    userId,
                    feature,
                    level ? parseInt(level) : null
                );

                res.json({
                    contentId,
                    userId,
                    access: accessResult
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to check access',
                    details: error.message
                });
            }
        }
    );

    // Process tier upgrade
    router.post('/upgrade/:accessId',
        [
            param('accessId').isUUID().withMessage('Invalid access ID'),
            body('newTier').isIn(['basic', 'premium', 'pro', 'enterprise']).withMessage('Invalid tier')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { accessId } = req.params;
                const { newTier } = req.body;

                const upgradeData = await tieredAccessService.processUpgrade(accessId, newTier);

                res.json({
                    success: true,
                    upgrade: upgradeData
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to process upgrade',
                    details: error.message
                });
            }
        }
    );

    // Track usage
    router.post('/usage/:accessId',
        [
            param('accessId').isUUID().withMessage('Invalid access ID'),
            body('action').notEmpty().withMessage('Action is required'),
            body('metadata').optional().isObject().withMessage('Metadata must be object')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { accessId } = req.params;
                const { action, metadata } = req.body;

                const usageResult = await tieredAccessService.trackUsage(accessId, action, metadata);

                res.json({
                    success: true,
                    usage: usageResult
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to track usage',
                    details: error.message
                });
            }
        }
    );

    // Get tier comparison
    router.get('/tiers/compare', async (req, res) => {
        try {
            const tiers = req.query.tiers ? req.query.tiers.split(',') : null;
            const comparison = await tieredAccessService.getTierComparison(tiers);
            
            res.json({
                tiers: comparison
            });
        } catch (error) {
            res.status(500).json({
                error: 'Failed to get tier comparison',
                details: error.message
            });
        }
    });

    // Get usage analytics
    router.get('/analytics/:accessId',
        [
            param('accessId').isUUID().withMessage('Invalid access ID')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { accessId } = req.params;
                const analytics = await tieredAccessService.getUsageAnalytics(accessId);

                res.json({
                    accessId,
                    analytics
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get usage analytics',
                    details: error.message
                });
            }
        }
    );

    // Set content classification
    router.post('/classify/:contentId',
        [
            param('contentId').notEmpty().withMessage('Content ID is required'),
            body('classification').isIn(['public', 'premium', 'exclusive', 'professional', 'enterprise']).withMessage('Invalid classification'),
            body('creatorId').notEmpty().withMessage('Creator ID is required')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { contentId } = req.params;
                const { classification, creatorId } = req.body;

                const result = await tieredAccessService.setContentClassification(
                    contentId,
                    classification,
                    creatorId
                );

                res.json({
                    success: true,
                    classification: result
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to set content classification',
                    details: error.message
                });
            }
        }
    );

    // Get service statistics
    router.get('/stats', async (req, res) => {
        try {
            const stats = await tieredAccessService.getStats();
            res.json(stats);
        } catch (error) {
            res.status(500).json({
                error: 'Failed to get statistics',
                details: error.message
            });
        }
    });

    return router;
}