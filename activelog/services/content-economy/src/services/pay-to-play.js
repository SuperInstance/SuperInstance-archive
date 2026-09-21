import cron from 'node-cron';
import { v4 as uuidv4 } from 'uuid';
import moment from 'moment';
import Decimal from 'decimal.js';

export class PayToPlayService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null; // Will be set by main server
        
        // Timer configurations
        this.timerConfigs = {
            '30_days': {
                duration: 30 * 24 * 60 * 60 * 1000, // 30 days in ms
                baseCost: new Decimal('4.99'),
                name: '30 Day Access',
                description: 'Access content for 30 days'
            },
            '1_year': {
                duration: 365 * 24 * 60 * 60 * 1000, // 1 year in ms
                baseCost: new Decimal('39.99'),
                name: '1 Year Access',
                description: 'Access content for 1 full year',
                discount: new Decimal('0.15') // 15% discount compared to monthly
            },
            'custom': {
                minDuration: 1 * 24 * 60 * 60 * 1000, // 1 day
                maxDuration: 2 * 365 * 24 * 60 * 60 * 1000, // 2 years
                baseCostPerDay: new Decimal('0.20'),
                name: 'Custom Duration',
                description: 'Set your own access duration'
            }
        };

        // Payment tiers based on content type
        this.contentTiers = {
            'basic': {
                multiplier: new Decimal('1.0'),
                features: ['view', 'download']
            },
            'premium': {
                multiplier: new Decimal('1.5'),
                features: ['view', 'download', 'remix', 'comment']
            },
            'exclusive': {
                multiplier: new Decimal('2.0'),
                features: ['view', 'download', 'remix', 'comment', 'early_access', 'creator_contact']
            },
            'vip': {
                multiplier: new Decimal('3.0'),
                features: ['all_features', 'private_feedback', 'collaboration_invite', 'source_files']
            }
        };
    }

    async createPayToPlayAccess(contentId, userId, timerType, customDuration = null, tier = 'basic') {
        try {
            const accessId = uuidv4();
            const timestamp = Date.now();
            
            // Calculate duration and cost
            const duration = this.calculateDuration(timerType, customDuration);
            const cost = await this.calculateCost(contentId, timerType, customDuration, tier);
            
            const accessData = {
                id: accessId,
                contentId,
                userId,
                timerType,
                tier,
                duration,
                cost: cost.toString(),
                startTime: timestamp,
                endTime: timestamp + duration,
                customDuration,
                status: 'pending_payment',
                features: this.contentTiers[tier].features,
                createdAt: timestamp,
                updatedAt: timestamp
            };

            // Store access record
            await this.redis.hset(`pay_to_play:${accessId}`, accessData);
            
            // Index by user and content
            await this.redis.sadd(`user_access:${userId}`, accessId);
            await this.redis.sadd(`content_access:${contentId}`, accessId);
            
            // Set expiration reminder
            await this.scheduleExpirationReminder(accessId, accessData.endTime);

            this.logger.info(`Created pay-to-play access: ${accessId} for content: ${contentId}`);

            return accessData;
        } catch (error) {
            this.logger.error('Error creating pay-to-play access:', error);
            throw error;
        }
    }

    calculateDuration(timerType, customDuration = null) {
        if (timerType === 'custom' && customDuration) {
            const duration = parseInt(customDuration);
            const config = this.timerConfigs.custom;
            
            if (duration < config.minDuration || duration > config.maxDuration) {
                throw new Error(`Custom duration must be between ${config.minDuration} and ${config.maxDuration} milliseconds`);
            }
            
            return duration;
        }

        const config = this.timerConfigs[timerType];
        if (!config) {
            throw new Error(`Invalid timer type: ${timerType}`);
        }

        return config.duration;
    }

    async calculateCost(contentId, timerType, customDuration = null, tier = 'basic') {
        try {
            let baseCost;
            
            if (timerType === 'custom' && customDuration) {
                const days = Math.ceil(customDuration / (24 * 60 * 60 * 1000));
                baseCost = this.timerConfigs.custom.baseCostPerDay.mul(days);
            } else {
                baseCost = this.timerConfigs[timerType].baseCost;
            }

            // Apply tier multiplier
            const tierMultiplier = this.contentTiers[tier].multiplier;
            let finalCost = baseCost.mul(tierMultiplier);

            // Apply content-specific pricing
            const contentPricing = await this.getContentPricing(contentId);
            if (contentPricing.priceMultiplier) {
                finalCost = finalCost.mul(new Decimal(contentPricing.priceMultiplier));
            }

            // Apply discounts
            const discounts = await this.calculateDiscounts(contentId, timerType, tier);
            finalCost = finalCost.mul(new Decimal(1).sub(discounts.totalDiscount));

            // Minimum cost floor
            const minimumCost = new Decimal('0.99');
            if (finalCost.lt(minimumCost)) {
                finalCost = minimumCost;
            }

            return finalCost;
        } catch (error) {
            this.logger.error('Error calculating cost:', error);
            throw error;
        }
    }

    async getContentPricing(contentId) {
        const pricing = await this.redis.hgetall(`content_pricing:${contentId}`);
        return {
            priceMultiplier: pricing.priceMultiplier || '1.0',
            customPricing: pricing.customPricing === 'true',
            creatorSet: pricing.creatorSet === 'true'
        };
    }

    async calculateDiscounts(contentId, timerType, tier) {
        let totalDiscount = new Decimal('0');
        const discounts = [];

        // Volume discount for longer periods
        if (timerType === '1_year') {
            const yearDiscount = this.timerConfigs['1_year'].discount || new Decimal('0.15');
            totalDiscount = totalDiscount.add(yearDiscount);
            discounts.push({ type: 'year_subscription', amount: yearDiscount.toString() });
        }

        // Loyalty discount for repeat customers
        const userPurchases = await this.redis.scard(`user_purchases:${contentId}`);
        if (userPurchases > 0) {
            const loyaltyDiscount = new Decimal('0.05'); // 5% for returning customers
            totalDiscount = totalDiscount.add(loyaltyDiscount);
            discounts.push({ type: 'loyalty', amount: loyaltyDiscount.toString() });
        }

        // Creator-specific discounts
        const creatorDiscounts = await this.redis.hget(`content_discounts:${contentId}`, 'active');
        if (creatorDiscounts) {
            const discount = new Decimal(creatorDiscounts);
            totalDiscount = totalDiscount.add(discount);
            discounts.push({ type: 'creator_special', amount: discount.toString() });
        }

        // Cap total discount at 50%
        if (totalDiscount.gt(new Decimal('0.5'))) {
            totalDiscount = new Decimal('0.5');
        }

        return { totalDiscount, discounts };
    }

    async processPayment(accessId, paymentMethod, paymentDetails) {
        try {
            const accessData = await this.redis.hgetall(`pay_to_play:${accessId}`);
            if (!accessData.id) {
                throw new Error(`Access record not found: ${accessId}`);
            }

            if (accessData.status !== 'pending_payment') {
                throw new Error(`Invalid access status: ${accessData.status}`);
            }

            // Process payment (integrate with payment service)
            const paymentResult = await this.processPaymentTransaction(
                accessData.cost, 
                paymentMethod, 
                paymentDetails
            );

            if (paymentResult.success) {
                // Update access status
                await this.redis.hset(`pay_to_play:${accessId}`, {
                    status: 'active',
                    paymentId: paymentResult.paymentId,
                    paidAt: Date.now(),
                    updatedAt: Date.now()
                });

                // Start access timer
                await this.startAccessTimer(accessId);

                // Record purchase for analytics
                await this.recordPurchase(accessData);

                // Broadcast update
                if (this.broadcast) {
                    this.broadcast(`earnings-${accessData.creatorId}`, {
                        type: 'new_purchase',
                        accessId,
                        amount: accessData.cost,
                        timestamp: Date.now()
                    });
                }

                this.logger.info(`Payment processed for access: ${accessId}`);
                return { success: true, accessId, paymentId: paymentResult.paymentId };
            } else {
                // Update status to failed
                await this.redis.hset(`pay_to_play:${accessId}`, {
                    status: 'payment_failed',
                    paymentError: paymentResult.error,
                    updatedAt: Date.now()
                });

                return { success: false, error: paymentResult.error };
            }
        } catch (error) {
            this.logger.error('Error processing payment:', error);
            throw error;
        }
    }

    async processPaymentTransaction(amount, paymentMethod, paymentDetails) {
        // Mock payment processing - integrate with actual payment service
        try {
            // Simulate payment processing delay
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Mock success (90% success rate)
            const success = Math.random() > 0.1;
            
            if (success) {
                return {
                    success: true,
                    paymentId: `pay_${uuidv4()}`,
                    transactionId: `txn_${uuidv4()}`,
                    amount: amount.toString(),
                    method: paymentMethod
                };
            } else {
                return {
                    success: false,
                    error: 'Payment declined by bank'
                };
            }
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async startAccessTimer(accessId) {
        const accessData = await this.redis.hgetall(`pay_to_play:${accessId}`);
        const endTime = parseInt(accessData.endTime);
        
        // Schedule expiration
        await this.redis.zadd('access_expirations', endTime, accessId);
        
        // Set up notifications
        const reminderTimes = [
            endTime - (24 * 60 * 60 * 1000), // 1 day before
            endTime - (60 * 60 * 1000),      // 1 hour before
            endTime - (5 * 60 * 1000)        // 5 minutes before
        ];

        for (const reminderTime of reminderTimes) {
            if (reminderTime > Date.now()) {
                await this.redis.zadd('access_reminders', reminderTime, `${accessId}:${reminderTime}`);
            }
        }
    }

    async checkAccess(contentId, userId) {
        try {
            const userAccesses = await this.redis.smembers(`user_access:${userId}`);
            const activeAccesses = [];

            for (const accessId of userAccesses) {
                const accessData = await this.redis.hgetall(`pay_to_play:${accessId}`);
                
                if (accessData.contentId === contentId && accessData.status === 'active') {
                    const currentTime = Date.now();
                    const endTime = parseInt(accessData.endTime);

                    if (currentTime <= endTime) {
                        activeAccesses.push({
                            ...accessData,
                            timeRemaining: endTime - currentTime,
                            percentRemaining: ((endTime - currentTime) / parseInt(accessData.duration)) * 100
                        });
                    } else {
                        // Access expired, update status
                        await this.redis.hset(`pay_to_play:${accessId}`, {
                            status: 'expired',
                            updatedAt: currentTime
                        });
                    }
                }
            }

            return {
                hasAccess: activeAccesses.length > 0,
                accesses: activeAccesses
            };
        } catch (error) {
            this.logger.error('Error checking access:', error);
            return { hasAccess: false, accesses: [] };
        }
    }

    async extendAccess(accessId, additionalDuration, tier = null) {
        try {
            const accessData = await this.redis.hgetall(`pay_to_play:${accessId}`);
            if (!accessData.id) {
                throw new Error(`Access record not found: ${accessId}`);
            }

            const currentEndTime = parseInt(accessData.endTime);
            const newEndTime = currentEndTime + additionalDuration;
            
            // Calculate extension cost
            const extensionCost = await this.calculateExtensionCost(
                accessData.contentId, 
                additionalDuration, 
                tier || accessData.tier
            );

            const extensionData = {
                extensionId: uuidv4(),
                accessId,
                additionalDuration,
                cost: extensionCost.toString(),
                tier: tier || accessData.tier,
                status: 'pending_payment',
                createdAt: Date.now()
            };

            // Store extension request
            await this.redis.hset(`access_extension:${extensionData.extensionId}`, extensionData);

            return extensionData;
        } catch (error) {
            this.logger.error('Error creating access extension:', error);
            throw error;
        }
    }

    async calculateExtensionCost(contentId, additionalDuration, tier) {
        const days = Math.ceil(additionalDuration / (24 * 60 * 60 * 1000));
        const baseCost = this.timerConfigs.custom.baseCostPerDay.mul(days);
        const tierMultiplier = this.contentTiers[tier].multiplier;
        
        return baseCost.mul(tierMultiplier);
    }

    async scheduleExpirationReminder(accessId, endTime) {
        const reminderTime = endTime - (24 * 60 * 60 * 1000); // 24 hours before expiration
        
        if (reminderTime > Date.now()) {
            await this.redis.zadd('expiration_reminders', reminderTime, accessId);
        }
    }

    async processExpirationReminders() {
        const now = Date.now();
        const expiredReminders = await this.redis.zrangebyscore(
            'expiration_reminders', 
            '-inf', 
            now
        );

        for (const accessId of expiredReminders) {
            await this.sendExpirationReminder(accessId);
            await this.redis.zrem('expiration_reminders', accessId);
        }
    }

    async sendExpirationReminder(accessId) {
        try {
            const accessData = await this.redis.hgetall(`pay_to_play:${accessId}`);
            const timeRemaining = parseInt(accessData.endTime) - Date.now();
            
            if (this.broadcast) {
                this.broadcast(`user-${accessData.userId}`, {
                    type: 'access_expiration_reminder',
                    accessId,
                    contentId: accessData.contentId,
                    timeRemaining,
                    extensionAvailable: true
                });
            }

            this.logger.info(`Sent expiration reminder for access: ${accessId}`);
        } catch (error) {
            this.logger.error('Error sending expiration reminder:', error);
        }
    }

    async recordPurchase(accessData) {
        const timestamp = Date.now();
        const purchaseRecord = {
            accessId: accessData.id,
            contentId: accessData.contentId,
            userId: accessData.userId,
            amount: accessData.cost,
            tier: accessData.tier,
            duration: accessData.duration,
            timestamp
        };

        // Store purchase record
        await this.redis.lpush('purchase_history', JSON.stringify(purchaseRecord));
        await this.redis.sadd(`user_purchases:${accessData.userId}`, accessData.id);
        await this.redis.sadd(`content_purchases:${accessData.contentId}`, accessData.id);
    }

    async getStats() {
        try {
            const stats = {
                totalAccesses: await this.redis.scard('all_accesses') || 0,
                activeAccesses: 0,
                totalRevenue: new Decimal('0'),
                averageAccessDuration: 0,
                popularTiers: {},
                revenueByTier: {}
            };

            // Calculate active accesses and revenue
            const allAccesses = await this.redis.smembers('all_accesses') || [];
            let totalDuration = 0;

            for (const accessId of allAccesses) {
                const accessData = await this.redis.hgetall(`pay_to_play:${accessId}`);
                
                if (accessData.status === 'active' && parseInt(accessData.endTime) > Date.now()) {
                    stats.activeAccesses++;
                }

                if (accessData.cost) {
                    stats.totalRevenue = stats.totalRevenue.add(new Decimal(accessData.cost));
                }

                if (accessData.tier) {
                    stats.popularTiers[accessData.tier] = (stats.popularTiers[accessData.tier] || 0) + 1;
                    stats.revenueByTier[accessData.tier] = (stats.revenueByTier[accessData.tier] || new Decimal('0')).add(new Decimal(accessData.cost || '0'));
                }

                if (accessData.duration) {
                    totalDuration += parseInt(accessData.duration);
                }
            }

            stats.averageAccessDuration = allAccesses.length > 0 ? totalDuration / allAccesses.length : 0;
            stats.totalRevenue = stats.totalRevenue.toString();

            // Convert Decimal values in revenueByTier to strings
            for (const [tier, revenue] of Object.entries(stats.revenueByTier)) {
                stats.revenueByTier[tier] = revenue.toString();
            }

            return stats;
        } catch (error) {
            this.logger.error('Error getting stats:', error);
            return {};
        }
    }

    startScheduler() {
        // Check for expired accesses and send reminders every minute
        cron.schedule('* * * * *', async () => {
            await this.processExpirationReminders();
        });

        this.logger.info('Pay-to-play scheduler started');
    }

    stopScheduler() {
        // Scheduler cleanup handled by cron library
        this.logger.info('Pay-to-play scheduler stopped');
    }
}