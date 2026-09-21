import cron from 'node-cron';
import { v4 as uuidv4 } from 'uuid';
import moment from 'moment';
import Decimal from 'decimal.js';

export class CoffeePromptService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null; // Will be set by main server
        
        // Coffee configurations
        this.coffeeTypes = {
            'espresso': {
                name: 'Espresso Shot',
                cost: new Decimal('2.50'),
                description: 'A quick pick-me-up for the creator',
                emoji: '☕',
                energy: 25
            },
            'latte': {
                name: 'Creamy Latte',
                cost: new Decimal('4.50'),
                description: 'Smooth and comforting support',
                emoji: '🥛',
                energy: 50
            },
            'cappuccino': {
                name: 'Frothy Cappuccino',
                cost: new Decimal('4.00'),
                description: 'Artistic appreciation for creators',
                emoji: '☕',
                energy: 45
            },
            'americano': {
                name: 'Bold Americano',
                cost: new Decimal('3.50'),
                description: 'Strong support for ambitious projects',
                emoji: '☕',
                energy: 40
            },
            'mocha': {
                name: 'Indulgent Mocha',
                cost: new Decimal('5.50'),
                description: 'Sweet encouragement with extra love',
                emoji: '🍫',
                energy: 60
            },
            'cold_brew': {
                name: 'Refreshing Cold Brew',
                cost: new Decimal('4.75'),
                description: 'Cool support for summer creativity',
                emoji: '🧊',
                energy: 55
            },
            'custom': {
                name: 'Custom Coffee',
                baseCost: new Decimal('1.00'),
                maxCost: new Decimal('50.00'),
                description: 'Your own personalized support amount',
                emoji: '💝',
                energy: 'variable'
            }
        };

        // Prompt triggers and contexts
        this.promptTriggers = {
            'content_view': {
                frequency: 0.15, // 15% chance
                message: "Enjoying this content? Buy {creator} a {coffee_type}!",
                timing: 'after_engagement'
            },
            'download': {
                frequency: 0.30, // 30% chance
                message: "This download was helpful! Consider buying {creator} a {coffee_type}",
                timing: 'after_action'
            },
            'time_spent': {
                threshold: 300000, // 5 minutes
                frequency: 0.20, // 20% chance
                message: "You've been here a while! How about a {coffee_type} for {creator}?",
                timing: 'time_based'
            },
            'return_visitor': {
                frequency: 0.25, // 25% chance
                message: "Welcome back! Show {creator} some love with a {coffee_type}",
                timing: 'on_return'
            },
            'milestone': {
                frequency: 1.0, // Always show
                message: "Help {creator} celebrate reaching {milestone}!",
                timing: 'milestone_reached'
            }
        };

        // Personal messages and gratitude levels
        this.gratitudeMessages = {
            'first_time': [
                "Thank you so much for your first coffee! ☕ It means the world to me!",
                "You just made my day with your first coffee support! 🌟",
                "Your first coffee gave me such a boost! Thank you! ⚡"
            ],
            'repeat': [
                "Another coffee? You're absolutely amazing! 🙌",
                "Your continued support keeps me going! ☕💪",
                "You're becoming my favorite coffee buddy! 😊"
            ],
            'generous': [
                "WOW! This generous coffee will fuel so much creativity! 🚀",
                "Your incredible generosity just blew me away! 💝",
                "This amazing support will help me create something special! ✨"
            ],
            'milestone': [
                "Thanks to supporters like you, I've reached {count} coffees! 🎉",
                "Celebrating {count} coffees with grateful tears! 😭❤️",
                "The {count}th coffee tastes the sweetest! Thank you! 🥳"
            ]
        };
    }

    async createCoffeePrompt(contentId, creatorId, userId, triggerType, context = {}) {
        try {
            const promptId = uuidv4();
            const timestamp = Date.now();
            
            // Check if user should see prompt based on frequency
            const shouldShow = await this.shouldShowPrompt(userId, triggerType, contentId);
            if (!shouldShow) {
                return null;
            }

            // Select appropriate coffee type and customize message
            const coffeeType = await this.selectCoffeeType(creatorId, context);
            const message = await this.generatePromptMessage(creatorId, triggerType, coffeeType, context);
            
            const promptData = {
                id: promptId,
                contentId,
                creatorId,
                userId,
                triggerType,
                coffeeType: coffeeType.type,
                message,
                cost: coffeeType.cost.toString(),
                context: JSON.stringify(context),
                status: 'shown',
                createdAt: timestamp,
                expiresAt: timestamp + (24 * 60 * 60 * 1000) // 24 hours
            };

            // Store prompt
            await this.redis.hset(`coffee_prompt:${promptId}`, promptData);
            
            // Track prompt history
            await this.redis.sadd(`user_prompts:${userId}`, promptId);
            await this.redis.sadd(`creator_prompts:${creatorId}`, promptId);
            
            // Update prompt frequency tracking
            await this.updatePromptFrequency(userId, triggerType);

            this.logger.info(`Created coffee prompt: ${promptId} for creator: ${creatorId}`);

            return {
                promptId,
                message,
                coffeeType: coffeeType.type,
                coffeeName: coffeeType.name,
                coffeeEmoji: coffeeType.emoji,
                cost: coffeeType.cost.toString(),
                creatorName: context.creatorName || 'this creator'
            };
        } catch (error) {
            this.logger.error('Error creating coffee prompt:', error);
            throw error;
        }
    }

    async shouldShowPrompt(userId, triggerType, contentId) {
        try {
            // Check cooldown period (don't spam users)
            const lastPrompt = await this.redis.get(`last_prompt:${userId}:${triggerType}`);
            const cooldownPeriod = 60 * 60 * 1000; // 1 hour
            
            if (lastPrompt && (Date.now() - parseInt(lastPrompt)) < cooldownPeriod) {
                return false;
            }

            // Check if user has already bought coffee for this content recently
            const recentPurchase = await this.redis.get(`recent_coffee:${userId}:${contentId}`);
            if (recentPurchase) {
                return false;
            }

            // Check user's prompt preferences
            const userPrefs = await this.getUserPromptPreferences(userId);
            if (userPrefs.disabled || userPrefs.frequency === 'never') {
                return false;
            }

            // Apply frequency rules
            const trigger = this.promptTriggers[triggerType];
            let frequency = trigger.frequency;

            // Adjust based on user preferences
            if (userPrefs.frequency === 'low') {
                frequency *= 0.5;
            } else if (userPrefs.frequency === 'high') {
                frequency *= 1.5;
            }

            return Math.random() < frequency;
        } catch (error) {
            this.logger.error('Error checking prompt eligibility:', error);
            return false;
        }
    }

    async selectCoffeeType(creatorId, context = {}) {
        try {
            // Get creator's preferred coffee types
            const creatorPrefs = await this.getCreatorCoffeePreferences(creatorId);
            
            // Consider context for coffee selection
            let availableTypes = Object.keys(this.coffeeTypes).filter(type => type !== 'custom');
            
            if (creatorPrefs.preferredTypes && creatorPrefs.preferredTypes.length > 0) {
                availableTypes = creatorPrefs.preferredTypes;
            }

            // Weight selection based on context
            if (context.isFirstTime) {
                // Favor smaller amounts for first-time supporters
                availableTypes = availableTypes.filter(type => 
                    this.coffeeTypes[type].cost.lte(new Decimal('4.00'))
                );
            } else if (context.isGenerous) {
                // Show premium options for generous supporters
                availableTypes = availableTypes.filter(type => 
                    this.coffeeTypes[type].cost.gte(new Decimal('4.00'))
                );
            }

            // Random selection from available types
            const selectedType = availableTypes[Math.floor(Math.random() * availableTypes.length)];
            const coffeeConfig = this.coffeeTypes[selectedType];

            return {
                type: selectedType,
                name: coffeeConfig.name,
                cost: coffeeConfig.cost,
                description: coffeeConfig.description,
                emoji: coffeeConfig.emoji
            };
        } catch (error) {
            this.logger.error('Error selecting coffee type:', error);
            // Fallback to espresso
            return {
                type: 'espresso',
                name: this.coffeeTypes.espresso.name,
                cost: this.coffeeTypes.espresso.cost,
                description: this.coffeeTypes.espresso.description,
                emoji: this.coffeeTypes.espresso.emoji
            };
        }
    }

    async generatePromptMessage(creatorId, triggerType, coffeeType, context) {
        try {
            const trigger = this.promptTriggers[triggerType];
            let message = trigger.message;

            // Replace placeholders
            message = message.replace('{creator}', context.creatorName || 'this creator');
            message = message.replace('{coffee_type}', coffeeType.name.toLowerCase());
            message = message.replace('{milestone}', context.milestone || '');

            // Add personal touch based on relationship
            const relationship = await this.getCreatorUserRelationship(creatorId, context.userId);
            if (relationship.isRegularSupporter) {
                message += " Your support has been incredible! 💜";
            } else if (relationship.isFirstTime) {
                message += " Every bit of support helps! 🌟";
            }

            return message;
        } catch (error) {
            this.logger.error('Error generating prompt message:', error);
            return `Support this creator with a ${coffeeType.name.toLowerCase()}! ☕`;
        }
    }

    async processCoffeePurchase(promptId, paymentMethod, paymentDetails, customAmount = null, personalMessage = null) {
        try {
            const promptData = await this.redis.hgetall(`coffee_prompt:${promptId}`);
            if (!promptData.id) {
                throw new Error(`Coffee prompt not found: ${promptId}`);
            }

            // Calculate final amount
            let finalAmount = new Decimal(promptData.cost);
            if (customAmount && new Decimal(customAmount).gt(finalAmount)) {
                finalAmount = new Decimal(customAmount);
            }

            // Process payment
            const paymentResult = await this.processPaymentTransaction(
                finalAmount,
                paymentMethod,
                paymentDetails
            );

            if (paymentResult.success) {
                const coffeeId = uuidv4();
                const timestamp = Date.now();

                const coffeeData = {
                    id: coffeeId,
                    promptId,
                    creatorId: promptData.creatorId,
                    userId: promptData.userId,
                    contentId: promptData.contentId,
                    coffeeType: promptData.coffeeType,
                    amount: finalAmount.toString(),
                    personalMessage: personalMessage || '',
                    paymentId: paymentResult.paymentId,
                    status: 'completed',
                    createdAt: timestamp
                };

                // Store coffee purchase
                await this.redis.hset(`coffee_purchase:${coffeeId}`, coffeeData);
                
                // Update prompt status
                await this.redis.hset(`coffee_prompt:${promptId}`, {
                    status: 'purchased',
                    coffeeId,
                    purchasedAt: timestamp
                });

                // Track purchases
                await this.redis.sadd(`creator_coffees:${promptData.creatorId}`, coffeeId);
                await this.redis.sadd(`user_coffee_purchases:${promptData.userId}`, coffeeId);

                // Record analytics
                await this.recordCoffeeAnalytics(coffeeData);

                // Send gratitude message
                const gratitudeMessage = await this.generateGratitudeMessage(coffeeData);
                
                // Set cooldown for recent coffee purchase
                await this.redis.setex(
                    `recent_coffee:${promptData.userId}:${promptData.contentId}`,
                    24 * 60 * 60, // 24 hours
                    timestamp
                );

                // Broadcast updates
                if (this.broadcast) {
                    this.broadcast(`earnings-${promptData.creatorId}`, {
                        type: 'coffee_received',
                        coffeeId,
                        amount: finalAmount.toString(),
                        message: personalMessage,
                        timestamp
                    });

                    this.broadcast(`user-${promptData.userId}`, {
                        type: 'coffee_sent',
                        coffeeId,
                        gratitudeMessage,
                        timestamp
                    });
                }

                this.logger.info(`Coffee purchase completed: ${coffeeId}`);

                return {
                    success: true,
                    coffeeId,
                    gratitudeMessage,
                    amount: finalAmount.toString()
                };

            } else {
                return {
                    success: false,
                    error: paymentResult.error
                };
            }

        } catch (error) {
            this.logger.error('Error processing coffee purchase:', error);
            throw error;
        }
    }

    async processPaymentTransaction(amount, paymentMethod, paymentDetails) {
        // Mock payment processing - integrate with actual payment service
        try {
            // Simulate processing delay
            await new Promise(resolve => setTimeout(resolve, 800));

            // Mock success (95% success rate for small amounts)
            const success = Math.random() > 0.05;
            
            if (success) {
                return {
                    success: true,
                    paymentId: `coffee_pay_${uuidv4()}`,
                    transactionId: `coffee_txn_${uuidv4()}`,
                    amount: amount.toString(),
                    method: paymentMethod
                };
            } else {
                return {
                    success: false,
                    error: 'Payment processing failed'
                };
            }
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async generateGratitudeMessage(coffeeData) {
        try {
            const creatorId = coffeeData.creatorId;
            const userId = coffeeData.userId;
            const amount = new Decimal(coffeeData.amount);

            // Determine gratitude category
            let category = 'repeat';
            
            // Check if first time supporter
            const userCoffees = await this.redis.smembers(`user_coffee_purchases:${userId}`);
            if (userCoffees.length === 1) {
                category = 'first_time';
            }
            
            // Check if generous amount
            if (amount.gt(new Decimal('8.00'))) {
                category = 'generous';
            }

            // Check for milestone
            const totalCoffees = await this.redis.scard(`creator_coffees:${creatorId}`);
            if (totalCoffees % 10 === 0) { // Every 10th coffee
                category = 'milestone';
            }

            const messages = this.gratitudeMessages[category];
            let message = messages[Math.floor(Math.random() * messages.length)];

            // Replace placeholders
            if (category === 'milestone') {
                message = message.replace('{count}', totalCoffees);
            }

            return message;
        } catch (error) {
            this.logger.error('Error generating gratitude message:', error);
            return "Thank you so much for the coffee! ☕ Your support means everything!";
        }
    }

    async recordCoffeeAnalytics(coffeeData) {
        try {
            const timestamp = Date.now();
            const analyticsRecord = {
                ...coffeeData,
                timestamp
            };

            // Store analytics
            await this.redis.lpush('coffee_analytics', JSON.stringify(analyticsRecord));
            
            // Update daily totals
            const today = moment().format('YYYY-MM-DD');
            await this.redis.incrbyfloat(`coffee_daily:${today}`, parseFloat(coffeeData.amount));
            await this.redis.incrbyfloat(`creator_daily:${coffeeData.creatorId}:${today}`, parseFloat(coffeeData.amount));

        } catch (error) {
            this.logger.error('Error recording coffee analytics:', error);
        }
    }

    async getUserPromptPreferences(userId) {
        try {
            const prefs = await this.redis.hgetall(`user_coffee_prefs:${userId}`);
            return {
                disabled: prefs.disabled === 'true',
                frequency: prefs.frequency || 'normal', // low, normal, high, never
                preferredTypes: prefs.preferredTypes ? prefs.preferredTypes.split(',') : [],
                maxAmount: prefs.maxAmount || '50.00'
            };
        } catch (error) {
            this.logger.error('Error getting user preferences:', error);
            return { disabled: false, frequency: 'normal', preferredTypes: [], maxAmount: '50.00' };
        }
    }

    async getCreatorCoffeePreferences(creatorId) {
        try {
            const prefs = await this.redis.hgetall(`creator_coffee_prefs:${creatorId}`);
            return {
                enabled: prefs.enabled !== 'false',
                preferredTypes: prefs.preferredTypes ? prefs.preferredTypes.split(',') : [],
                customMessage: prefs.customMessage || '',
                goalAmount: prefs.goalAmount || null,
                goalMessage: prefs.goalMessage || ''
            };
        } catch (error) {
            this.logger.error('Error getting creator preferences:', error);
            return { enabled: true, preferredTypes: [], customMessage: '', goalAmount: null, goalMessage: '' };
        }
    }

    async getCreatorUserRelationship(creatorId, userId) {
        try {
            const userCoffees = await this.redis.smembers(`user_coffee_purchases:${userId}`);
            const creatorCoffees = [];

            for (const coffeeId of userCoffees) {
                const coffeeData = await this.redis.hgetall(`coffee_purchase:${coffeeId}`);
                if (coffeeData.creatorId === creatorId) {
                    creatorCoffees.push(coffeeData);
                }
            }

            return {
                isFirstTime: creatorCoffees.length === 0,
                isRegularSupporter: creatorCoffees.length >= 3,
                totalSupported: creatorCoffees.reduce((sum, coffee) => 
                    sum.add(new Decimal(coffee.amount || '0')), new Decimal('0')
                ).toString(),
                coffeeCount: creatorCoffees.length
            };
        } catch (error) {
            this.logger.error('Error getting creator-user relationship:', error);
            return { isFirstTime: true, isRegularSupporter: false, totalSupported: '0', coffeeCount: 0 };
        }
    }

    async updatePromptFrequency(userId, triggerType) {
        const key = `last_prompt:${userId}:${triggerType}`;
        await this.redis.set(key, Date.now());
    }

    async getCreatorCoffeeStats(creatorId, timeframe = '30d') {
        try {
            const creatorCoffees = await this.redis.smembers(`creator_coffees:${creatorId}`);
            let totalAmount = new Decimal('0');
            let coffeeCount = 0;
            const coffeeTypes = {};
            const dailyStats = {};

            const cutoffTime = Date.now() - (timeframe === '7d' ? 7 : 30) * 24 * 60 * 60 * 1000;

            for (const coffeeId of creatorCoffees) {
                const coffeeData = await this.redis.hgetall(`coffee_purchase:${coffeeId}`);
                
                if (parseInt(coffeeData.createdAt) >= cutoffTime) {
                    totalAmount = totalAmount.add(new Decimal(coffeeData.amount || '0'));
                    coffeeCount++;
                    
                    const coffeeType = coffeeData.coffeeType;
                    coffeeTypes[coffeeType] = (coffeeTypes[coffeeType] || 0) + 1;

                    const day = moment(parseInt(coffeeData.createdAt)).format('YYYY-MM-DD');
                    dailyStats[day] = (dailyStats[day] || new Decimal('0')).add(new Decimal(coffeeData.amount || '0'));
                }
            }

            return {
                totalAmount: totalAmount.toString(),
                coffeeCount,
                averageAmount: coffeeCount > 0 ? totalAmount.div(coffeeCount).toString() : '0',
                coffeeTypes,
                dailyStats: Object.fromEntries(
                    Object.entries(dailyStats).map(([date, amount]) => [date, amount.toString()])
                ),
                timeframe
            };
        } catch (error) {
            this.logger.error('Error getting creator coffee stats:', error);
            return { totalAmount: '0', coffeeCount: 0, averageAmount: '0', coffeeTypes: {}, dailyStats: {} };
        }
    }

    async getStats() {
        try {
            const allPrompts = await this.redis.keys('coffee_prompt:*');
            const allPurchases = await this.redis.keys('coffee_purchase:*');
            
            let totalRevenue = new Decimal('0');
            let totalPrompts = allPrompts.length;
            let completedPurchases = 0;
            const coffeeTypeStats = {};

            for (const purchaseKey of allPurchases) {
                const purchaseData = await this.redis.hgetall(purchaseKey);
                
                if (purchaseData.status === 'completed') {
                    completedPurchases++;
                    totalRevenue = totalRevenue.add(new Decimal(purchaseData.amount || '0'));
                    
                    const coffeeType = purchaseData.coffeeType;
                    coffeeTypeStats[coffeeType] = (coffeeTypeStats[coffeeType] || 0) + 1;
                }
            }

            const conversionRate = totalPrompts > 0 ? (completedPurchases / totalPrompts) * 100 : 0;

            return {
                totalPrompts,
                completedPurchases,
                totalRevenue: totalRevenue.toString(),
                conversionRate: conversionRate.toFixed(2),
                averageCoffeeAmount: completedPurchases > 0 ? totalRevenue.div(completedPurchases).toString() : '0',
                coffeeTypeStats
            };
        } catch (error) {
            this.logger.error('Error getting coffee stats:', error);
            return {};
        }
    }

    startScheduler() {
        // Clean up expired prompts every hour
        cron.schedule('0 * * * *', async () => {
            await this.cleanupExpiredPrompts();
        });

        this.logger.info('Coffee prompts scheduler started');
    }

    async cleanupExpiredPrompts() {
        try {
            const now = Date.now();
            const promptKeys = await this.redis.keys('coffee_prompt:*');
            
            for (const key of promptKeys) {
                const promptData = await this.redis.hgetall(key);
                if (parseInt(promptData.expiresAt) <= now) {
                    await this.redis.del(key);
                }
            }
        } catch (error) {
            this.logger.error('Error cleaning up expired prompts:', error);
        }
    }

    stopScheduler() {
        this.logger.info('Coffee prompts scheduler stopped');
    }
}