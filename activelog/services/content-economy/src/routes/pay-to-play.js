import express from 'express';
import { body, param, query, validationResult } from 'express-validator';

const router = express.Router();

export default function createPayToPlayRoutes(payToPlayService) {
    
    // Create pay-to-play access
    router.post('/create',
        [
            body('contentId').notEmpty().withMessage('Content ID is required'),
            body('userId').notEmpty().withMessage('User ID is required'),
            body('timerType').isIn(['30_days', '1_year', 'custom']).withMessage('Invalid timer type'),
            body('tier').optional().isIn(['basic', 'premium', 'exclusive', 'vip']).withMessage('Invalid tier'),
            body('customDuration').optional().isInt({ min: 1 }).withMessage('Custom duration must be positive integer')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { contentId, userId, timerType, customDuration, tier } = req.body;

                const accessData = await payToPlayService.createPayToPlayAccess(
                    contentId,
                    userId,
                    timerType,
                    customDuration,
                    tier || 'basic'
                );

                res.json({
                    success: true,
                    access: accessData
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to create pay-to-play access',
                    details: error.message
                });
            }
        }
    );

    // Process payment for access
    router.post('/payment/:accessId',
        [
            param('accessId').isUUID().withMessage('Invalid access ID'),
            body('paymentMethod').notEmpty().withMessage('Payment method is required'),
            body('paymentDetails').isObject().withMessage('Payment details are required')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { accessId } = req.params;
                const { paymentMethod, paymentDetails } = req.body;

                const paymentResult = await payToPlayService.processPayment(
                    accessId,
                    paymentMethod,
                    paymentDetails
                );

                if (paymentResult.success) {
                    res.json({
                        success: true,
                        message: 'Payment processed successfully',
                        accessId: paymentResult.accessId,
                        paymentId: paymentResult.paymentId
                    });
                } else {
                    res.status(400).json({
                        success: false,
                        error: 'Payment failed',
                        details: paymentResult.error
                    });
                }

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to process payment',
                    details: error.message
                });
            }
        }
    );

    // Check user access to content
    router.get('/check/:contentId/:userId',
        [
            param('contentId').notEmpty().withMessage('Content ID is required'),
            param('userId').notEmpty().withMessage('User ID is required')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { contentId, userId } = req.params;

                const accessResult = await payToPlayService.checkAccess(contentId, userId);

                res.json({
                    contentId,
                    userId,
                    hasAccess: accessResult.hasAccess,
                    accesses: accessResult.accesses
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to check access',
                    details: error.message
                });
            }
        }
    );

    // Calculate cost for access
    router.post('/calculate-cost',
        [
            body('contentId').notEmpty().withMessage('Content ID is required'),
            body('timerType').isIn(['30_days', '1_year', 'custom']).withMessage('Invalid timer type'),
            body('tier').optional().isIn(['basic', 'premium', 'exclusive', 'vip']).withMessage('Invalid tier'),
            body('customDuration').optional().isInt({ min: 1 }).withMessage('Custom duration must be positive integer')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { contentId, timerType, customDuration, tier } = req.body;

                const cost = await payToPlayService.calculateCost(
                    contentId,
                    timerType,
                    customDuration,
                    tier || 'basic'
                );

                const duration = payToPlayService.calculateDuration(timerType, customDuration);
                const discounts = await payToPlayService.calculateDiscounts(contentId, timerType, tier || 'basic');

                res.json({
                    contentId,
                    timerType,
                    tier: tier || 'basic',
                    duration,
                    cost: cost.toString(),
                    discounts: discounts.discounts,
                    totalDiscount: discounts.totalDiscount.toString()
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to calculate cost',
                    details: error.message
                });
            }
        }
    );

    // Extend existing access
    router.post('/extend/:accessId',
        [
            param('accessId').isUUID().withMessage('Invalid access ID'),
            body('additionalDuration').isInt({ min: 1 }).withMessage('Additional duration must be positive integer'),
            body('tier').optional().isIn(['basic', 'premium', 'exclusive', 'vip']).withMessage('Invalid tier')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { accessId } = req.params;
                const { additionalDuration, tier } = req.body;

                const extensionData = await payToPlayService.extendAccess(
                    accessId,
                    parseInt(additionalDuration),
                    tier
                );

                res.json({
                    success: true,
                    extension: extensionData
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to extend access',
                    details: error.message
                });
            }
        }
    );

    // Get access details
    router.get('/access/:accessId',
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
                const accessData = await payToPlayService.redis.hgetall(`pay_to_play:${accessId}`);

                if (!accessData.id) {
                    return res.status(404).json({
                        error: 'Access record not found'
                    });
                }

                // Calculate remaining time
                const currentTime = Date.now();
                const endTime = parseInt(accessData.endTime);
                const timeRemaining = Math.max(0, endTime - currentTime);

                res.json({
                    access: {
                        ...accessData,
                        timeRemaining,
                        percentRemaining: timeRemaining > 0 
                            ? ((timeRemaining / parseInt(accessData.duration)) * 100) 
                            : 0,
                        isActive: accessData.status === 'active' && timeRemaining > 0
                    }
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get access details',
                    details: error.message
                });
            }
        }
    );

    // Get user's access history
    router.get('/history/:userId',
        [
            param('userId').notEmpty().withMessage('User ID is required'),
            query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
            query('offset').optional().isInt({ min: 0 }).withMessage('Offset must be non-negative')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { userId } = req.params;
                const limit = parseInt(req.query.limit) || 20;
                const offset = parseInt(req.query.offset) || 0;

                const userAccesses = await payToPlayService.redis.smembers(`user_access:${userId}`);
                const accesses = [];

                for (const accessId of userAccesses.slice(offset, offset + limit)) {
                    const accessData = await payToPlayService.redis.hgetall(`pay_to_play:${accessId}`);
                    if (accessData.id) {
                        const currentTime = Date.now();
                        const endTime = parseInt(accessData.endTime);
                        const timeRemaining = Math.max(0, endTime - currentTime);

                        accesses.push({
                            ...accessData,
                            timeRemaining,
                            isActive: accessData.status === 'active' && timeRemaining > 0
                        });
                    }
                }

                // Sort by creation time (most recent first)
                accesses.sort((a, b) => parseInt(b.createdAt) - parseInt(a.createdAt));

                res.json({
                    userId,
                    accesses,
                    total: userAccesses.length,
                    limit,
                    offset
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get access history',
                    details: error.message
                });
            }
        }
    );

    // Get timer configurations
    router.get('/config', async (req, res) => {
        try {
            res.json({
                timerConfigs: payToPlayService.timerConfigs,
                contentTiers: payToPlayService.contentTiers
            });
        } catch (error) {
            res.status(500).json({
                error: 'Failed to get configuration',
                details: error.message
            });
        }
    });

    // Get service statistics
    router.get('/stats', async (req, res) => {
        try {
            const stats = await payToPlayService.getStats();
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