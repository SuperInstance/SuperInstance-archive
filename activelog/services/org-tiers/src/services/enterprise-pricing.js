import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';
import moment from 'moment';
import cron from 'node-cron';

export class EnterprisePricingService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null; // Will be set by main server
        
        // Enterprise pricing tiers
        this.enterpriseTiers = {
            'business': {
                name: 'Business',
                pricePerUser: new Decimal('2.00'),
                minUsers: 5,
                maxUsers: 100,
                features: {
                    basicSSO: true,
                    standardSupport: true,
                    basicReporting: true,
                    apiAccess: true,
                    dataRetention: '1year',
                    computeCredits: 1000,
                    storagePerUser: '10GB'
                },
                description: 'Perfect for small to medium businesses'
            },
            'enterprise': {
                name: 'Enterprise',
                pricePerUser: new Decimal('2.00'),
                minUsers: 101,
                maxUsers: 1000,
                features: {
                    advancedSSO: true,
                    prioritySupport: true,
                    advancedReporting: true,
                    apiAccess: true,
                    dataRetention: '3years',
                    computeCredits: 5000,
                    storagePerUser: '50GB',
                    complianceReporting: true,
                    budgetManagement: true,
                    departmentTracking: true
                },
                volumeDiscount: new Decimal('0.10'), // 10% discount
                description: 'Comprehensive solution for large organizations'
            },
            'enterprise_plus': {
                name: 'Enterprise Plus',
                pricePerUser: new Decimal('2.00'),
                minUsers: 1001,
                maxUsers: -1, // unlimited
                features: {
                    customSSO: true,
                    dedicatedSupport: true,
                    customReporting: true,
                    fullApiAccess: true,
                    dataRetention: 'unlimited',
                    computeCredits: 25000,
                    storagePerUser: '500GB',
                    complianceReporting: true,
                    budgetManagement: true,
                    departmentTracking: true,
                    customIntegrations: true,
                    dedicatedInfrastructure: true,
                    SLA: '99.9%'
                },
                volumeDiscount: new Decimal('0.20'), // 20% discount
                customPricing: true,
                description: 'Ultimate enterprise solution with custom features'
            }
        };

        // Additional enterprise features pricing
        this.addOnFeatures = {
            'audit_logging': {
                name: 'Advanced Audit Logging',
                pricePerUser: new Decimal('0.50'),
                description: 'Comprehensive audit trails and compliance logging'
            },
            'advanced_analytics': {
                name: 'Advanced Analytics',
                pricePerUser: new Decimal('1.00'),
                description: 'Deep insights and custom dashboards'
            },
            'data_export': {
                name: 'Advanced Data Export',
                pricePerUser: new Decimal('0.25'),
                description: 'Automated data export and backup'
            },
            'custom_branding': {
                name: 'Custom Branding',
                flatFee: new Decimal('500.00'),
                description: 'White-label branding and customization'
            },
            'dedicated_support': {
                name: 'Dedicated Support Manager',
                flatFee: new Decimal('2000.00'),
                description: 'Dedicated customer success manager'
            }
        };

        // Payment schedules
        this.billingCycles = {
            'monthly': {
                name: 'Monthly Billing',
                discount: new Decimal('0.00')
            },
            'quarterly': {
                name: 'Quarterly Billing',
                discount: new Decimal('0.05') // 5% discount
            },
            'annual': {
                name: 'Annual Billing',
                discount: new Decimal('0.15') // 15% discount
            }
        };
    }

    async createEnterpriseContract(orgId, tierName, userCount, billingCycle = 'monthly', addOns = [], customTerms = null) {
        try {
            const contractId = uuidv4();
            const timestamp = Date.now();
            
            // Validate tier and user count
            const tier = this.enterpriseTiers[tierName];
            if (!tier) {
                throw new Error(`Invalid enterprise tier: ${tierName}`);
            }

            if (userCount < tier.minUsers || (tier.maxUsers > 0 && userCount > tier.maxUsers)) {
                throw new Error(`User count ${userCount} outside valid range for ${tierName}`);
            }

            // Calculate pricing
            const pricing = await this.calculateEnterprisePrice(tierName, userCount, billingCycle, addOns);
            
            const contractData = {
                id: contractId,
                orgId,
                tierName,
                userCount,
                billingCycle,
                addOns: JSON.stringify(addOns),
                customTerms: customTerms ? JSON.stringify(customTerms) : null,
                pricing: JSON.stringify({
                    basePrice: pricing.basePrice.toString(),
                    addOnPrice: pricing.addOnPrice.toString(),
                    totalPrice: pricing.totalPrice.toString(),
                    billingFrequency: pricing.billingFrequency,
                    nextBillingDate: pricing.nextBillingDate
                }),
                features: JSON.stringify(tier.features),
                status: 'draft',
                createdAt: timestamp,
                updatedAt: timestamp,
                effectiveDate: null,
                expirationDate: null
            };

            // Store contract
            await this.redis.hset(`enterprise_contract:${contractId}`, contractData);
            await this.redis.sadd(`org_contracts:${orgId}`, contractId);

            this.logger.info(`Created enterprise contract: ${contractId} for org: ${orgId}`);

            return {
                ...contractData,
                pricing: JSON.parse(contractData.pricing),
                features: JSON.parse(contractData.features),
                addOns: JSON.parse(contractData.addOns),
                customTerms: contractData.customTerms ? JSON.parse(contractData.customTerms) : null
            };
        } catch (error) {
            this.logger.error('Error creating enterprise contract:', error);
            throw error;
        }
    }

    async calculateEnterprisePrice(tierName, userCount, billingCycle, addOns = []) {
        try {
            const tier = this.enterpriseTiers[tierName];
            const billing = this.billingCycles[billingCycle];
            
            // Base price calculation
            let basePrice = tier.pricePerUser.mul(userCount);
            
            // Apply volume discount
            if (tier.volumeDiscount) {
                basePrice = basePrice.mul(new Decimal('1').sub(tier.volumeDiscount));
            }

            // Calculate add-on pricing
            let addOnPrice = new Decimal('0');
            for (const addOnId of addOns) {
                const addOn = this.addOnFeatures[addOnId];
                if (addOn) {
                    if (addOn.pricePerUser) {
                        addOnPrice = addOnPrice.add(addOn.pricePerUser.mul(userCount));
                    } else if (addOn.flatFee) {
                        addOnPrice = addOnPrice.add(addOn.flatFee);
                    }
                }
            }

            // Apply billing cycle discount
            const totalBeforeDiscount = basePrice.add(addOnPrice);
            const billingDiscount = totalBeforeDiscount.mul(billing.discount);
            const totalPrice = totalBeforeDiscount.sub(billingDiscount);

            // Calculate billing frequency and next billing date
            let billingFrequency;
            let nextBillingDate;
            const now = moment();
            
            switch (billingCycle) {
                case 'monthly':
                    billingFrequency = 'monthly';
                    nextBillingDate = now.add(1, 'month').valueOf();
                    break;
                case 'quarterly':
                    billingFrequency = 'quarterly';
                    nextBillingDate = now.add(3, 'months').valueOf();
                    break;
                case 'annual':
                    billingFrequency = 'annual';
                    nextBillingDate = now.add(1, 'year').valueOf();
                    break;
            }

            return {
                basePrice,
                addOnPrice,
                totalPrice,
                billingFrequency,
                nextBillingDate,
                billingDiscount,
                userCount,
                tier: tierName
            };
        } catch (error) {
            this.logger.error('Error calculating enterprise price:', error);
            throw error;
        }
    }

    async activateContract(contractId, paymentDetails, startDate = null) {
        try {
            const contractData = await this.redis.hgetall(`enterprise_contract:${contractId}`);
            if (!contractData.id) {
                throw new Error(`Contract not found: ${contractId}`);
            }

            if (contractData.status !== 'draft' && contractData.status !== 'pending') {
                throw new Error(`Cannot activate contract in status: ${contractData.status}`);
            }

            const pricing = JSON.parse(contractData.pricing);
            
            // Process payment
            const paymentResult = await this.processEnterprisePayment(
                contractId,
                pricing.totalPrice,
                paymentDetails
            );

            if (paymentResult.success) {
                const effectiveDate = startDate || Date.now();
                const expirationDate = this.calculateExpirationDate(effectiveDate, contractData.billingCycle);

                await this.redis.hset(`enterprise_contract:${contractId}`, {
                    status: 'active',
                    effectiveDate,
                    expirationDate,
                    paymentId: paymentResult.paymentId,
                    activatedAt: Date.now(),
                    updatedAt: Date.now()
                });

                // Set up billing schedule
                await this.scheduleRecurringBilling(contractId, pricing.nextBillingDate);

                // Initialize usage tracking
                await this.initializeUsageTracking(contractId, contractData.orgId);

                // Broadcast activation
                if (this.broadcast) {
                    this.broadcast(`org-analytics-${contractData.orgId}`, {
                        type: 'contract_activated',
                        contractId,
                        tier: contractData.tierName,
                        userCount: contractData.userCount,
                        totalPrice: pricing.totalPrice
                    });
                }

                this.logger.info(`Activated enterprise contract: ${contractId}`);
                return { success: true, contractId, paymentId: paymentResult.paymentId };
            } else {
                await this.redis.hset(`enterprise_contract:${contractId}`, {
                    status: 'payment_failed',
                    paymentError: paymentResult.error,
                    updatedAt: Date.now()
                });
                return { success: false, error: paymentResult.error };
            }
        } catch (error) {
            this.logger.error('Error activating contract:', error);
            throw error;
        }
    }

    calculateExpirationDate(effectiveDate, billingCycle) {
        const effective = moment(effectiveDate);
        
        switch (billingCycle) {
            case 'monthly':
                return effective.add(1, 'month').valueOf();
            case 'quarterly':
                return effective.add(3, 'months').valueOf();
            case 'annual':
                return effective.add(1, 'year').valueOf();
            default:
                return effective.add(1, 'month').valueOf();
        }
    }

    async processEnterprisePayment(contractId, amount, paymentDetails) {
        // Mock enterprise payment processing - integrate with actual payment service
        try {
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // 98% success rate for enterprise payments
            const success = Math.random() > 0.02;
            
            if (success) {
                return {
                    success: true,
                    paymentId: `ent_pay_${uuidv4()}`,
                    transactionId: `ent_txn_${uuidv4()}`,
                    amount: amount.toString(),
                    processedAt: Date.now()
                };
            } else {
                return {
                    success: false,
                    error: 'Enterprise payment processing failed'
                };
            }
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async scheduleRecurringBilling(contractId, nextBillingDate) {
        await this.redis.zadd('enterprise_billing_schedule', nextBillingDate, contractId);
    }

    async initializeUsageTracking(contractId, orgId) {
        const trackingData = {
            contractId,
            orgId,
            currentPeriodStart: Date.now(),
            currentPeriodEnd: null,
            usage: {
                activeUsers: 0,
                computeCreditsUsed: 0,
                storageUsed: 0,
                apiCalls: 0
            },
            createdAt: Date.now()
        };

        await this.redis.hset(`usage_tracking:${contractId}`, trackingData);
    }

    async updateUserCount(contractId, newUserCount, effective = null) {
        try {
            const contractData = await this.redis.hgetall(`enterprise_contract:${contractId}`);
            if (!contractData.id) {
                throw new Error(`Contract not found: ${contractId}`);
            }

            const currentCount = parseInt(contractData.userCount);
            const tier = this.enterpriseTiers[contractData.tierName];
            
            // Validate new user count against tier limits
            if (newUserCount < tier.minUsers || (tier.maxUsers > 0 && newUserCount > tier.maxUsers)) {
                throw new Error(`New user count ${newUserCount} outside valid range for ${contractData.tierName}`);
            }

            // Calculate prorated billing adjustment
            const adjustment = await this.calculateUserCountAdjustment(
                contractId,
                currentCount,
                newUserCount,
                effective || Date.now()
            );

            // Update contract
            await this.redis.hset(`enterprise_contract:${contractId}`, {
                userCount: newUserCount,
                updatedAt: Date.now()
            });

            // Record adjustment for billing
            if (adjustment.amount.gt(0)) {
                const adjustmentId = uuidv4();
                await this.redis.hset(`billing_adjustment:${adjustmentId}`, {
                    id: adjustmentId,
                    contractId,
                    type: 'user_count_change',
                    fromCount: currentCount,
                    toCount: newUserCount,
                    amount: adjustment.amount.toString(),
                    effectiveDate: effective || Date.now(),
                    createdAt: Date.now()
                });
            }

            this.logger.info(`Updated user count for contract ${contractId}: ${currentCount} -> ${newUserCount}`);
            return { adjustment, newUserCount };
        } catch (error) {
            this.logger.error('Error updating user count:', error);
            throw error;
        }
    }

    async calculateUserCountAdjustment(contractId, oldCount, newCount, effectiveDate) {
        const contractData = await this.redis.hgetall(`enterprise_contract:${contractId}`);
        const pricing = JSON.parse(contractData.pricing);
        const tier = this.enterpriseTiers[contractData.tierName];
        
        const pricePerUser = tier.pricePerUser;
        if (tier.volumeDiscount) {
            pricePerUser.mul(new Decimal('1').sub(tier.volumeDiscount));
        }

        const userDifference = newCount - oldCount;
        const daysInPeriod = this.getDaysInBillingPeriod(contractData.billingCycle);
        const daysRemaining = this.getDaysRemaining(contractData, effectiveDate);
        
        const proratedAmount = pricePerUser
            .mul(userDifference)
            .mul(daysRemaining)
            .div(daysInPeriod);

        return {
            amount: proratedAmount,
            userDifference,
            daysRemaining,
            effectiveDate
        };
    }

    getDaysInBillingPeriod(billingCycle) {
        switch (billingCycle) {
            case 'monthly': return 30;
            case 'quarterly': return 90;
            case 'annual': return 365;
            default: return 30;
        }
    }

    getDaysRemaining(contractData, effectiveDate) {
        const pricing = JSON.parse(contractData.pricing);
        const nextBilling = moment(pricing.nextBillingDate);
        const effective = moment(effectiveDate);
        return nextBilling.diff(effective, 'days');
    }

    async processRecurringBilling() {
        try {
            const now = Date.now();
            const dueContracts = await this.redis.zrangebyscore('enterprise_billing_schedule', '-inf', now);
            
            for (const contractId of dueContracts) {
                await this.processBillingForContract(contractId);
                await this.redis.zrem('enterprise_billing_schedule', contractId);
            }
        } catch (error) {
            this.logger.error('Error processing recurring billing:', error);
        }
    }

    async processBillingForContract(contractId) {
        try {
            const contractData = await this.redis.hgetall(`enterprise_contract:${contractId}`);
            if (contractData.status !== 'active') {
                return;
            }

            const pricing = JSON.parse(contractData.pricing);
            
            // Process payment for next period
            const paymentResult = await this.processRecurringPayment(contractId, pricing.totalPrice);
            
            if (paymentResult.success) {
                // Update billing dates
                const nextBillingDate = this.calculateNextBillingDate(contractData.billingCycle);
                const updatedPricing = {
                    ...pricing,
                    nextBillingDate
                };

                await this.redis.hset(`enterprise_contract:${contractId}`, {
                    pricing: JSON.stringify(updatedPricing),
                    lastBillingDate: Date.now(),
                    updatedAt: Date.now()
                });

                // Schedule next billing
                await this.scheduleRecurringBilling(contractId, nextBillingDate);

                this.logger.info(`Processed recurring billing for contract: ${contractId}`);
            } else {
                // Handle failed payment
                await this.handleFailedPayment(contractId, paymentResult.error);
            }
        } catch (error) {
            this.logger.error(`Error processing billing for contract ${contractId}:`, error);
        }
    }

    calculateNextBillingDate(billingCycle) {
        const now = moment();
        
        switch (billingCycle) {
            case 'monthly':
                return now.add(1, 'month').valueOf();
            case 'quarterly':
                return now.add(3, 'months').valueOf();
            case 'annual':
                return now.add(1, 'year').valueOf();
            default:
                return now.add(1, 'month').valueOf();
        }
    }

    async handleFailedPayment(contractId, error) {
        await this.redis.hset(`enterprise_contract:${contractId}`, {
            status: 'payment_overdue',
            paymentError: error,
            overdueDate: Date.now(),
            updatedAt: Date.now()
        });

        // Send alert to organization
        const contractData = await this.redis.hgetall(`enterprise_contract:${contractId}`);
        if (this.broadcast) {
            this.broadcast(`billing-updates-${contractData.orgId}`, {
                type: 'payment_failed',
                contractId,
                error,
                timestamp: Date.now()
            });
        }
    }

    async getContractDetails(contractId) {
        const contractData = await this.redis.hgetall(`enterprise_contract:${contractId}`);
        if (!contractData.id) {
            return null;
        }

        return {
            ...contractData,
            pricing: JSON.parse(contractData.pricing),
            features: JSON.parse(contractData.features),
            addOns: JSON.parse(contractData.addOns),
            customTerms: contractData.customTerms ? JSON.parse(contractData.customTerms) : null
        };
    }

    async getOrganizationContracts(orgId) {
        const contractIds = await this.redis.smembers(`org_contracts:${orgId}`);
        const contracts = [];

        for (const contractId of contractIds) {
            const contract = await this.getContractDetails(contractId);
            if (contract) {
                contracts.push(contract);
            }
        }

        return contracts.sort((a, b) => parseInt(b.createdAt) - parseInt(a.createdAt));
    }

    async getStats() {
        try {
            const stats = {
                totalContracts: 0,
                activeContracts: 0,
                totalRevenue: new Decimal('0'),
                averageUserCount: 0,
                tierDistribution: {},
                billingCycleDistribution: {},
                totalUsers: 0
            };

            const contractKeys = await this.redis.keys('enterprise_contract:*');
            let totalUsers = 0;
            let totalActiveUsers = 0;

            for (const key of contractKeys) {
                const contract = await this.redis.hgetall(key);
                stats.totalContracts++;
                totalUsers += parseInt(contract.userCount || 0);

                // Track tier distribution
                stats.tierDistribution[contract.tierName] = (stats.tierDistribution[contract.tierName] || 0) + 1;
                
                // Track billing cycle distribution
                stats.billingCycleDistribution[contract.billingCycle] = (stats.billingCycleDistribution[contract.billingCycle] || 0) + 1;

                if (contract.status === 'active') {
                    stats.activeContracts++;
                    totalActiveUsers += parseInt(contract.userCount || 0);
                    
                    const pricing = JSON.parse(contract.pricing || '{}');
                    if (pricing.totalPrice) {
                        stats.totalRevenue = stats.totalRevenue.add(new Decimal(pricing.totalPrice));
                    }
                }
            }

            stats.totalUsers = totalUsers;
            stats.averageUserCount = stats.activeContracts > 0 ? Math.round(totalActiveUsers / stats.activeContracts) : 0;
            stats.totalRevenue = stats.totalRevenue.toString();

            return stats;
        } catch (error) {
            this.logger.error('Error getting enterprise pricing stats:', error);
            return {};
        }
    }

    startScheduler() {
        // Process recurring billing daily at 2 AM
        cron.schedule('0 2 * * *', async () => {
            await this.processRecurringBilling();
        });

        this.logger.info('Enterprise pricing scheduler started');
    }

    stopScheduler() {
        this.logger.info('Enterprise pricing scheduler stopped');
    }

    // Additional route methods
    async calculatePricing(tier, userCount, billingCycle, addons = []) {
        return await this.calculateEnterprisePrice(tier, userCount, billingCycle, addons);
    }

    async generateQuote(orgId, tier, userCount, billingCycle, addons = [], customizations = {}) {
        const pricing = await this.calculateEnterprisePrice(tier, userCount, billingCycle, addons);
        const quoteId = uuidv4();
        
        const quote = {
            id: quoteId,
            orgId,
            tier,
            userCount,
            billingCycle,
            addons,
            customizations,
            pricing,
            validUntil: moment().add(30, 'days').valueOf(),
            createdAt: Date.now()
        };

        await this.redis.hset(`enterprise_quote:${quoteId}`, JSON.stringify(quote));
        return quote;
    }

    async getAvailableTiers() {
        return Object.entries(this.enterpriseTiers).map(([key, tier]) => ({
            id: key,
            ...tier,
            pricePerUser: tier.pricePerUser.toString()
        }));
    }
}