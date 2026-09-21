import cron from 'node-cron';
import { v4 as uuidv4 } from 'uuid';
import moment from 'moment';
import Decimal from 'decimal.js';

export class TieredAccessService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null; // Will be set by main server
        
        // Tier definitions with progressive features
        this.accessTiers = {
            'free': {
                name: 'Free Tier',
                cost: new Decimal('0'),
                level: 0,
                features: {
                    view: true,
                    download: false,
                    comment: false,
                    like: true,
                    share: true,
                    remix: false,
                    highQuality: false,
                    sourceFiles: false,
                    earlyAccess: false,
                    creatorContact: false,
                    customization: false
                },
                limits: {
                    viewsPerDay: 5,
                    downloadSize: 0,
                    commentLength: 0,
                    storageSpace: 0
                },
                description: 'Basic viewing access with limited features'
            },
            'basic': {
                name: 'Basic Access',
                cost: new Decimal('2.99'),
                level: 1,
                features: {
                    view: true,
                    download: true,
                    comment: true,
                    like: true,
                    share: true,
                    remix: false,
                    highQuality: false,
                    sourceFiles: false,
                    earlyAccess: false,
                    creatorContact: false,
                    customization: false
                },
                limits: {
                    viewsPerDay: 50,
                    downloadSize: 10 * 1024 * 1024, // 10MB
                    commentLength: 500,
                    storageSpace: 100 * 1024 * 1024 // 100MB
                },
                description: 'Standard access with downloading and commenting'
            },
            'premium': {
                name: 'Premium Access',
                cost: new Decimal('7.99'),
                level: 2,
                features: {
                    view: true,
                    download: true,
                    comment: true,
                    like: true,
                    share: true,
                    remix: true,
                    highQuality: true,
                    sourceFiles: false,
                    earlyAccess: false,
                    creatorContact: false,
                    customization: true
                },
                limits: {
                    viewsPerDay: 200,
                    downloadSize: 100 * 1024 * 1024, // 100MB
                    commentLength: 2000,
                    storageSpace: 1024 * 1024 * 1024 // 1GB
                },
                description: 'Enhanced access with remix rights and high quality content'
            },
            'pro': {
                name: 'Professional',
                cost: new Decimal('19.99'),
                level: 3,
                features: {
                    view: true,
                    download: true,
                    comment: true,
                    like: true,
                    share: true,
                    remix: true,
                    highQuality: true,
                    sourceFiles: true,
                    earlyAccess: true,
                    creatorContact: true,
                    customization: true
                },
                limits: {
                    viewsPerDay: 1000,
                    downloadSize: 500 * 1024 * 1024, // 500MB
                    commentLength: 5000,
                    storageSpace: 5 * 1024 * 1024 * 1024 // 5GB
                },
                description: 'Professional access with source files and creator contact'
            },
            'enterprise': {
                name: 'Enterprise',
                cost: new Decimal('49.99'),
                level: 4,
                features: {
                    view: true,
                    download: true,
                    comment: true,
                    like: true,
                    share: true,
                    remix: true,
                    highQuality: true,
                    sourceFiles: true,
                    earlyAccess: true,
                    creatorContact: true,
                    customization: true,
                    apiAccess: true,
                    bulkOperations: true,
                    whitelabeling: true,
                    prioritySupport: true
                },
                limits: {
                    viewsPerDay: -1, // Unlimited
                    downloadSize: -1, // Unlimited
                    commentLength: 10000,
                    storageSpace: 50 * 1024 * 1024 * 1024 // 50GB
                },
                description: 'Enterprise-grade access with unlimited usage and API access'
            }
        };

        // Content classification system
        this.contentClassifications = {
            'public': {
                name: 'Public Content',
                minTier: 'free',
                description: 'Freely accessible content'
            },
            'premium': {
                name: 'Premium Content',
                minTier: 'basic',
                description: 'Requires at least basic tier access'
            },
            'exclusive': {
                name: 'Exclusive Content',
                minTier: 'premium',
                description: 'Requires premium tier or higher'
            },
            'professional': {
                name: 'Professional Content',
                minTier: 'pro',
                description: 'Professional-grade content with source files'
            },
            'enterprise': {
                name: 'Enterprise Content',
                minTier: 'enterprise',
                description: 'Enterprise-only content with advanced features'
            }
        };
    }

    async createTieredAccess(contentId, userId, tier, duration = null, customFeatures = null) {
        try {
            const accessId = uuidv4();
            const timestamp = Date.now();
            
            // Validate tier
            if (!this.accessTiers[tier]) {
                throw new Error(`Invalid access tier: ${tier}`);
            }

            const tierConfig = this.accessTiers[tier];
            
            // Calculate cost and duration
            const cost = await this.calculateTierCost(contentId, tier, duration);
            const accessDuration = duration || (30 * 24 * 60 * 60 * 1000); // Default 30 days
            
            // Merge custom features with tier features
            const features = customFeatures ? 
                { ...tierConfig.features, ...customFeatures } : 
                tierConfig.features;

            const accessData = {
                id: accessId,
                contentId,
                userId,
                tier,
                cost: cost.toString(),
                duration: accessDuration,
                startTime: timestamp,
                endTime: timestamp + accessDuration,
                features: JSON.stringify(features),
                limits: JSON.stringify(tierConfig.limits),
                status: 'pending_payment',
                customFeatures: customFeatures ? JSON.stringify(customFeatures) : null,
                createdAt: timestamp,
                updatedAt: timestamp
            };

            // Store access record
            await this.redis.hset(`tiered_access:${accessId}`, accessData);
            
            // Index by user and content
            await this.redis.sadd(`user_tiered_access:${userId}`, accessId);
            await this.redis.sadd(`content_tiered_access:${contentId}`, accessId);
            
            // Track tier usage statistics
            await this.redis.incr(`tier_usage:${tier}`);

            this.logger.info(`Created tiered access: ${accessId} for content: ${contentId}, tier: ${tier}`);

            return accessData;
        } catch (error) {
            this.logger.error('Error creating tiered access:', error);
            throw error;
        }
    }

    async calculateTierCost(contentId, tier, duration = null) {
        try {
            const baseCost = this.accessTiers[tier].cost;
            let finalCost = baseCost;

            // Apply duration multiplier if custom duration
            if (duration) {
                const days = Math.ceil(duration / (24 * 60 * 60 * 1000));
                const monthlyRate = baseCost;
                const dailyRate = monthlyRate.div(30);
                finalCost = dailyRate.mul(days);
            }

            // Apply content-specific pricing
            const contentPricing = await this.getContentTierPricing(contentId);
            if (contentPricing.multiplier) {
                finalCost = finalCost.mul(new Decimal(contentPricing.multiplier));
            }

            // Apply volume discounts for higher tiers
            const tierLevel = this.accessTiers[tier].level;
            if (tierLevel >= 3) {
                const discount = new Decimal('0.1'); // 10% discount for pro and enterprise
                finalCost = finalCost.mul(new Decimal('1').sub(discount));
            }

            return finalCost;
        } catch (error) {
            this.logger.error('Error calculating tier cost:', error);
            throw error;
        }
    }

    async getContentTierPricing(contentId) {
        const pricing = await this.redis.hgetall(`content_tier_pricing:${contentId}`);
        return {
            multiplier: pricing.multiplier || '1.0',
            customTiers: pricing.customTiers ? JSON.parse(pricing.customTiers) : {},
            restrictions: pricing.restrictions ? JSON.parse(pricing.restrictions) : {}
        };
    }

    async processUpgrade(currentAccessId, newTier) {
        try {
            const currentAccess = await this.redis.hgetall(`tiered_access:${currentAccessId}`);
            if (!currentAccess.id) {
                throw new Error(`Access record not found: ${currentAccessId}`);
            }

            const currentTierLevel = this.accessTiers[currentAccess.tier].level;
            const newTierLevel = this.accessTiers[newTier].level;

            if (newTierLevel <= currentTierLevel) {
                throw new Error(`Cannot upgrade to same or lower tier`);
            }

            // Calculate upgrade cost (prorated)
            const remainingTime = parseInt(currentAccess.endTime) - Date.now();
            const upgradeCost = await this.calculateUpgradeCost(
                currentAccess.tier,
                newTier,
                remainingTime,
                currentAccess.contentId
            );

            const upgradeId = uuidv4();
            const upgradeData = {
                id: upgradeId,
                originalAccessId: currentAccessId,
                fromTier: currentAccess.tier,
                toTier: newTier,
                cost: upgradeCost.toString(),
                remainingTime,
                status: 'pending_payment',
                createdAt: Date.now()
            };

            // Store upgrade request
            await this.redis.hset(`tier_upgrade:${upgradeId}`, upgradeData);

            return upgradeData;
        } catch (error) {
            this.logger.error('Error processing upgrade:', error);
            throw error;
        }
    }

    async calculateUpgradeCost(fromTier, toTier, remainingTime, contentId) {
        const fromCost = this.accessTiers[fromTier].cost;
        const toCost = this.accessTiers[toTier].cost;
        
        // Calculate prorated difference
        const costDifference = toCost.sub(fromCost);
        const totalDuration = 30 * 24 * 60 * 60 * 1000; // 30 days
        const proratedCost = costDifference.mul(remainingTime).div(totalDuration);

        // Apply content pricing
        const contentPricing = await this.getContentTierPricing(contentId);
        if (contentPricing.multiplier) {
            return proratedCost.mul(new Decimal(contentPricing.multiplier));
        }

        return proratedCost;
    }

    async checkAccess(contentId, userId, requiredFeature = null, requiredLevel = null) {
        try {
            const userAccesses = await this.redis.smembers(`user_tiered_access:${userId}`);
            let highestAccess = null;
            let activeAccesses = [];

            for (const accessId of userAccesses) {
                const accessData = await this.redis.hgetall(`tiered_access:${accessId}`);
                
                if (accessData.contentId === contentId && accessData.status === 'active') {
                    const currentTime = Date.now();
                    const endTime = parseInt(accessData.endTime);

                    if (currentTime <= endTime) {
                        const features = JSON.parse(accessData.features || '{}');
                        const limits = JSON.parse(accessData.limits || '{}');
                        const tierLevel = this.accessTiers[accessData.tier].level;

                        const access = {
                            ...accessData,
                            features,
                            limits,
                            tierLevel,
                            timeRemaining: endTime - currentTime
                        };

                        activeAccesses.push(access);

                        // Track highest access level
                        if (!highestAccess || tierLevel > highestAccess.tierLevel) {
                            highestAccess = access;
                        }
                    } else {
                        // Access expired
                        await this.redis.hset(`tiered_access:${accessId}`, {
                            status: 'expired',
                            updatedAt: currentTime
                        });
                    }
                }
            }

            // Check content classification requirements
            const contentClassification = await this.getContentClassification(contentId);
            const hasRequiredTier = this.checkTierRequirement(highestAccess?.tier, contentClassification.minTier);

            // Check specific feature access
            let hasFeature = true;
            if (requiredFeature && highestAccess) {
                hasFeature = highestAccess.features[requiredFeature] === true;
            }

            // Check level requirement
            let hasLevel = true;
            if (requiredLevel && highestAccess) {
                hasLevel = highestAccess.tierLevel >= requiredLevel;
            }

            return {
                hasAccess: hasRequiredTier && hasFeature && hasLevel,
                highestTier: highestAccess?.tier || 'free',
                tierLevel: highestAccess?.tierLevel || 0,
                features: highestAccess?.features || this.accessTiers.free.features,
                limits: highestAccess?.limits || this.accessTiers.free.limits,
                activeAccesses,
                contentClassification,
                remainingTime: highestAccess?.timeRemaining || 0
            };
        } catch (error) {
            this.logger.error('Error checking tiered access:', error);
            return {
                hasAccess: false,
                highestTier: 'free',
                tierLevel: 0,
                features: this.accessTiers.free.features,
                limits: this.accessTiers.free.limits,
                activeAccesses: [],
                remainingTime: 0
            };
        }
    }

    checkTierRequirement(userTier, requiredTier) {
        if (!requiredTier || requiredTier === 'free') {
            return true;
        }

        if (!userTier || userTier === 'free') {
            return requiredTier === 'free';
        }

        const userLevel = this.accessTiers[userTier]?.level || 0;
        const requiredLevel = this.accessTiers[requiredTier]?.level || 0;

        return userLevel >= requiredLevel;
    }

    async getContentClassification(contentId) {
        const classification = await this.redis.hget(`content_classification:${contentId}`, 'classification');
        return this.contentClassifications[classification] || this.contentClassifications.public;
    }

    async setContentClassification(contentId, classification, creatorId) {
        try {
            if (!this.contentClassifications[classification]) {
                throw new Error(`Invalid content classification: ${classification}`);
            }

            const classificationData = {
                classification,
                creatorId,
                setAt: Date.now()
            };

            await this.redis.hset(`content_classification:${contentId}`, classificationData);

            this.logger.info(`Set content classification: ${contentId} -> ${classification}`);

            return classificationData;
        } catch (error) {
            this.logger.error('Error setting content classification:', error);
            throw error;
        }
    }

    async createCustomTier(creatorId, tierName, features, limits, cost) {
        try {
            const tierId = uuidv4();
            const tierData = {
                id: tierId,
                creatorId,
                name: tierName,
                features: JSON.stringify(features),
                limits: JSON.stringify(limits),
                cost: cost.toString(),
                level: 99, // Custom tiers get high level
                isCustom: true,
                createdAt: Date.now()
            };

            await this.redis.hset(`custom_tier:${tierId}`, tierData);
            await this.redis.sadd(`creator_custom_tiers:${creatorId}`, tierId);

            return tierData;
        } catch (error) {
            this.logger.error('Error creating custom tier:', error);
            throw error;
        }
    }

    async trackUsage(accessId, action, metadata = {}) {
        try {
            const accessData = await this.redis.hgetall(`tiered_access:${accessId}`);
            if (!accessData.id) {
                return;
            }

            const limits = JSON.parse(accessData.limits || '{}');
            const usageKey = `usage:${accessId}:${action}`;
            
            // Track usage against limits
            const currentUsage = await this.redis.get(usageKey) || '0';
            const newUsage = parseInt(currentUsage) + 1;

            await this.redis.set(usageKey, newUsage);

            // Check if user exceeded limits
            if (limits[action] && limits[action] > 0 && newUsage > limits[action]) {
                // Log limit exceeded
                this.logger.warn(`Usage limit exceeded for ${accessId}: ${action} (${newUsage}/${limits[action]})`);
                
                // Optionally broadcast warning
                if (this.broadcast) {
                    this.broadcast(`user-${accessData.userId}`, {
                        type: 'usage_limit_warning',
                        action,
                        usage: newUsage,
                        limit: limits[action]
                    });
                }

                return { exceeded: true, usage: newUsage, limit: limits[action] };
            }

            return { exceeded: false, usage: newUsage, limit: limits[action] || -1 };
        } catch (error) {
            this.logger.error('Error tracking usage:', error);
            return { exceeded: false, usage: 0, limit: -1 };
        }
    }

    async getTierComparison(tiers = null) {
        const comparison = {};
        const tiersToCompare = tiers || Object.keys(this.accessTiers);

        for (const tier of tiersToCompare) {
            const tierConfig = this.accessTiers[tier];
            if (tierConfig) {
                comparison[tier] = {
                    name: tierConfig.name,
                    cost: tierConfig.cost.toString(),
                    level: tierConfig.level,
                    features: tierConfig.features,
                    limits: tierConfig.limits,
                    description: tierConfig.description
                };
            }
        }

        return comparison;
    }

    async getUsageAnalytics(accessId) {
        try {
            const accessData = await this.redis.hgetall(`tiered_access:${accessId}`);
            if (!accessData.id) {
                throw new Error(`Access record not found: ${accessId}`);
            }

            const limits = JSON.parse(accessData.limits || '{}');
            const analytics = {};

            for (const action of Object.keys(limits)) {
                const usageKey = `usage:${accessId}:${action}`;
                const usage = await this.redis.get(usageKey) || '0';
                
                analytics[action] = {
                    usage: parseInt(usage),
                    limit: limits[action],
                    percentage: limits[action] > 0 ? (parseInt(usage) / limits[action]) * 100 : 0
                };
            }

            return analytics;
        } catch (error) {
            this.logger.error('Error getting usage analytics:', error);
            return {};
        }
    }

    async getStats() {
        try {
            const stats = {
                totalAccesses: 0,
                activeTierAccesses: {},
                tierUsage: {},
                totalRevenue: new Decimal('0'),
                averageAccessDuration: 0,
                upgradeRate: 0
            };

            // Get tier usage stats
            for (const tier of Object.keys(this.accessTiers)) {
                const usage = await this.redis.get(`tier_usage:${tier}`) || '0';
                stats.tierUsage[tier] = parseInt(usage);
                stats.totalAccesses += parseInt(usage);
            }

            // Get active accesses by tier
            const accessKeys = await this.redis.keys('tiered_access:*');
            let totalDuration = 0;
            let activeCount = 0;

            for (const key of accessKeys) {
                const accessData = await this.redis.hgetall(key);
                
                if (accessData.status === 'active' && parseInt(accessData.endTime) > Date.now()) {
                    const tier = accessData.tier;
                    stats.activeTierAccesses[tier] = (stats.activeTierAccesses[tier] || 0) + 1;
                    activeCount++;
                }

                if (accessData.cost) {
                    stats.totalRevenue = stats.totalRevenue.add(new Decimal(accessData.cost));
                }

                if (accessData.duration) {
                    totalDuration += parseInt(accessData.duration);
                }
            }

            stats.averageAccessDuration = accessKeys.length > 0 ? totalDuration / accessKeys.length : 0;
            stats.totalRevenue = stats.totalRevenue.toString();

            return stats;
        } catch (error) {
            this.logger.error('Error getting tiered access stats:', error);
            return {};
        }
    }

    startScheduler() {
        // Check for expired accesses every hour
        cron.schedule('0 * * * *', async () => {
            await this.processExpiredAccesses();
        });

        this.logger.info('Tiered access scheduler started');
    }

    async processExpiredAccesses() {
        try {
            const now = Date.now();
            const accessKeys = await this.redis.keys('tiered_access:*');

            for (const key of accessKeys) {
                const accessData = await this.redis.hgetall(key);
                
                if (accessData.status === 'active' && parseInt(accessData.endTime) <= now) {
                    await this.redis.hset(key, {
                        status: 'expired',
                        updatedAt: now
                    });

                    this.logger.info(`Expired access: ${accessData.id}`);
                }
            }
        } catch (error) {
            this.logger.error('Error processing expired accesses:', error);
        }
    }

    stopScheduler() {
        this.logger.info('Tiered access scheduler stopped');
    }
}