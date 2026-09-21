import express from 'express';
import { body, param, query, validationResult } from 'express-validator';

const router = express.Router();

export default function createCoffeePromptRoutes(coffeePromptService) {
    
    // Create a coffee prompt
    router.post('/prompt',
        [
            body('contentId').notEmpty().withMessage('Content ID is required'),
            body('creatorId').notEmpty().withMessage('Creator ID is required'),
            body('userId').notEmpty().withMessage('User ID is required'),
            body('triggerType').isIn(['content_view', 'download', 'time_spent', 'return_visitor', 'milestone']).withMessage('Invalid trigger type'),
            body('context').optional().isObject().withMessage('Context must be an object')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { contentId, creatorId, userId, triggerType, context } = req.body;

                const prompt = await coffeePromptService.createCoffeePrompt(
                    contentId,
                    creatorId,
                    userId,
                    triggerType,
                    context || {}
                );

                if (prompt) {
                    res.json({
                        success: true,
                        prompt
                    });
                } else {
                    res.json({
                        success: false,
                        message: 'Prompt not shown due to frequency limits'
                    });
                }

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to create coffee prompt',
                    details: error.message
                });
            }
        }
    );

    // Purchase coffee
    router.post('/purchase/:promptId',
        [
            param('promptId').isUUID().withMessage('Invalid prompt ID'),
            body('paymentMethod').notEmpty().withMessage('Payment method is required'),
            body('paymentDetails').isObject().withMessage('Payment details are required'),
            body('customAmount').optional().isFloat({ min: 0 }).withMessage('Custom amount must be positive'),
            body('personalMessage').optional().isString().isLength({ max: 500 }).withMessage('Message too long (max 500 characters)')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { promptId } = req.params;
                const { paymentMethod, paymentDetails, customAmount, personalMessage } = req.body;

                const purchaseResult = await coffeePromptService.processCoffeePurchase(
                    promptId,
                    paymentMethod,
                    paymentDetails,
                    customAmount,
                    personalMessage
                );

                if (purchaseResult.success) {
                    res.json({
                        success: true,
                        coffeeId: purchaseResult.coffeeId,
                        gratitudeMessage: purchaseResult.gratitudeMessage,
                        amount: purchaseResult.amount
                    });
                } else {
                    res.status(400).json({
                        success: false,
                        error: 'Coffee purchase failed',
                        details: purchaseResult.error
                    });
                }

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to process coffee purchase',
                    details: error.message
                });
            }
        }
    );

    // Get coffee types and pricing
    router.get('/types', async (req, res) => {
        try {
            const coffeeTypes = coffeePromptService.coffeeTypes;
            
            // Format for frontend consumption
            const formattedTypes = Object.entries(coffeeTypes).map(([key, config]) => ({
                id: key,
                name: config.name,
                cost: config.cost?.toString() || config.baseCost?.toString(),
                maxCost: config.maxCost?.toString(),
                description: config.description,
                emoji: config.emoji,
                energy: config.energy
            }));

            res.json({
                coffeeTypes: formattedTypes
            });

        } catch (error) {
            res.status(500).json({
                error: 'Failed to get coffee types',
                details: error.message
            });
        }
    });

    // Get user's coffee purchase history
    router.get('/history/:userId',
        [
            param('userId').notEmpty().withMessage('User ID is required'),
            query('limit').optional().isInt({ min: 1, max: 50 }).withMessage('Limit must be between 1 and 50'),
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

                const userCoffees = await coffeePromptService.redis.smembers(`user_coffee_purchases:${userId}`);
                const coffees = [];

                for (const coffeeId of userCoffees.slice(offset, offset + limit)) {
                    const coffeeData = await coffeePromptService.redis.hgetall(`coffee_purchase:${coffeeId}`);
                    if (coffeeData.id) {
                        coffees.push(coffeeData);
                    }
                }

                // Sort by creation time (most recent first)
                coffees.sort((a, b) => parseInt(b.createdAt) - parseInt(a.createdAt));

                res.json({
                    userId,
                    coffees,
                    total: userCoffees.length,
                    limit,
                    offset
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get coffee history',
                    details: error.message
                });
            }
        }
    );

    // Get creator's received coffees
    router.get('/received/:creatorId',
        [
            param('creatorId').notEmpty().withMessage('Creator ID is required'),
            query('timeframe').optional().isIn(['7d', '30d', 'all']).withMessage('Invalid timeframe'),
            query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { creatorId } = req.params;
                const timeframe = req.query.timeframe || '30d';
                const limit = parseInt(req.query.limit) || 50;

                const creatorCoffees = await coffeePromptService.redis.smembers(`creator_coffees:${creatorId}`);
                const coffees = [];

                const cutoffTime = timeframe === 'all' ? 0 : 
                    Date.now() - (timeframe === '7d' ? 7 : 30) * 24 * 60 * 60 * 1000;

                for (const coffeeId of creatorCoffees.slice(0, limit)) {
                    const coffeeData = await coffeePromptService.redis.hgetall(`coffee_purchase:${coffeeId}`);
                    
                    if (coffeeData.id && parseInt(coffeeData.createdAt) >= cutoffTime) {
                        coffees.push(coffeeData);
                    }
                }

                // Sort by creation time (most recent first)
                coffees.sort((a, b) => parseInt(b.createdAt) - parseInt(a.createdAt));

                res.json({
                    creatorId,
                    coffees,
                    timeframe,
                    total: coffees.length
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get received coffees',
                    details: error.message
                });
            }
        }
    );

    // Get creator coffee statistics
    router.get('/stats/:creatorId',
        [
            param('creatorId').notEmpty().withMessage('Creator ID is required'),
            query('timeframe').optional().isIn(['7d', '30d']).withMessage('Invalid timeframe')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { creatorId } = req.params;
                const timeframe = req.query.timeframe || '30d';

                const stats = await coffeePromptService.getCreatorCoffeeStats(creatorId, timeframe);

                res.json({
                    creatorId,
                    stats
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get creator coffee stats',
                    details: error.message
                });
            }
        }
    );

    // Update user coffee preferences
    router.put('/preferences/:userId',
        [
            param('userId').notEmpty().withMessage('User ID is required'),
            body('disabled').optional().isBoolean().withMessage('Disabled must be boolean'),
            body('frequency').optional().isIn(['low', 'normal', 'high', 'never']).withMessage('Invalid frequency'),
            body('preferredTypes').optional().isArray().withMessage('Preferred types must be array'),
            body('maxAmount').optional().isFloat({ min: 1 }).withMessage('Max amount must be positive')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { userId } = req.params;
                const preferences = req.body;

                // Validate preferred types if provided
                if (preferences.preferredTypes) {
                    const validTypes = Object.keys(coffeePromptService.coffeeTypes);
                    const invalidTypes = preferences.preferredTypes.filter(type => !validTypes.includes(type));
                    
                    if (invalidTypes.length > 0) {
                        return res.status(400).json({
                            error: 'Invalid coffee types',
                            invalidTypes
                        });
                    }
                }

                // Update preferences in Redis
                const prefData = {
                    disabled: preferences.disabled ? 'true' : 'false',
                    frequency: preferences.frequency || 'normal',
                    preferredTypes: preferences.preferredTypes ? preferences.preferredTypes.join(',') : '',
                    maxAmount: preferences.maxAmount ? preferences.maxAmount.toString() : '50.00'
                };

                await coffeePromptService.redis.hset(`user_coffee_prefs:${userId}`, prefData);

                res.json({
                    success: true,
                    message: 'Preferences updated successfully',
                    preferences: prefData
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to update preferences',
                    details: error.message
                });
            }
        }
    );

    // Update creator coffee settings
    router.put('/creator-settings/:creatorId',
        [
            param('creatorId').notEmpty().withMessage('Creator ID is required'),
            body('enabled').optional().isBoolean().withMessage('Enabled must be boolean'),
            body('preferredTypes').optional().isArray().withMessage('Preferred types must be array'),
            body('customMessage').optional().isString().isLength({ max: 500 }).withMessage('Custom message too long'),
            body('goalAmount').optional().isFloat({ min: 0 }).withMessage('Goal amount must be positive'),
            body('goalMessage').optional().isString().isLength({ max: 200 }).withMessage('Goal message too long')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { creatorId } = req.params;
                const settings = req.body;

                // Update creator settings in Redis
                const settingsData = {
                    enabled: settings.enabled !== false ? 'true' : 'false',
                    preferredTypes: settings.preferredTypes ? settings.preferredTypes.join(',') : '',
                    customMessage: settings.customMessage || '',
                    goalAmount: settings.goalAmount ? settings.goalAmount.toString() : '',
                    goalMessage: settings.goalMessage || ''
                };

                await coffeePromptService.redis.hset(`creator_coffee_prefs:${creatorId}`, settingsData);

                res.json({
                    success: true,
                    message: 'Creator settings updated successfully',
                    settings: settingsData
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to update creator settings',
                    details: error.message
                });
            }
        }
    );

    // Get user preferences
    router.get('/preferences/:userId',
        [
            param('userId').notEmpty().withMessage('User ID is required')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { userId } = req.params;
                const preferences = await coffeePromptService.getUserPromptPreferences(userId);

                res.json({
                    userId,
                    preferences
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get user preferences',
                    details: error.message
                });
            }
        }
    );

    // Get creator settings
    router.get('/creator-settings/:creatorId',
        [
            param('creatorId').notEmpty().withMessage('Creator ID is required')
        ],
        async (req, res) => {
            try {
                const errors = validationResult(req);
                if (!errors.isEmpty()) {
                    return res.status(400).json({ errors: errors.array() });
                }

                const { creatorId } = req.params;
                const settings = await coffeePromptService.getCreatorCoffeePreferences(creatorId);

                res.json({
                    creatorId,
                    settings
                });

            } catch (error) {
                res.status(500).json({
                    error: 'Failed to get creator settings',
                    details: error.message
                });
            }
        }
    );

    // Get prompt triggers configuration
    router.get('/triggers', async (req, res) => {
        try {
            res.json({
                triggers: coffeePromptService.promptTriggers
            });
        } catch (error) {
            res.status(500).json({
                error: 'Failed to get trigger configuration',
                details: error.message
            });
        }
    });

    // Get overall coffee service statistics
    router.get('/overall-stats', async (req, res) => {
        try {
            const stats = await coffeePromptService.getStats();
            res.json(stats);
        } catch (error) {
            res.status(500).json({
                error: 'Failed to get overall statistics',
                details: error.message
            });
        }
    });

    return router;
}