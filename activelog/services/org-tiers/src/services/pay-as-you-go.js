import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';
import moment from 'moment';
import cron from 'node-cron';

export class PayAsYouGoService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
        
        // Compute resource pricing
        this.computePricing = {
            'cpu': {
                name: 'CPU Hours',
                unit: 'hour',
                price: new Decimal('0.05'), // $0.05 per CPU hour
                description: 'General purpose compute processing'
            },
            'gpu': {
                name: 'GPU Hours',
                unit: 'hour',
                price: new Decimal('0.50'), // $0.50 per GPU hour
                description: 'High-performance GPU computing'
            },
            'memory': {
                name: 'Memory',
                unit: 'GB-hour',
                price: new Decimal('0.01'), // $0.01 per GB-hour
                description: 'RAM usage per hour'
            },
            'storage': {
                name: 'Storage',
                unit: 'GB-month',
                price: new Decimal('0.10'), // $0.10 per GB per month
                description: 'Persistent storage'
            },
            'bandwidth': {
                name: 'Data Transfer',
                unit: 'GB',
                price: new Decimal('0.12'), // $0.12 per GB
                description: 'Data transfer and bandwidth'
            },
            'ai_processing': {
                name: 'AI Processing',
                unit: 'request',
                price: new Decimal('0.002'), // $0.002 per AI request
                description: 'AI model inference and processing'
            },
            'database': {
                name: 'Database Operations',
                unit: 'operation',
                price: new Decimal('0.0001'), // $0.0001 per operation
                description: 'Database read/write operations'
            }
        };

        // Volume discounts based on monthly usage
        this.volumeDiscounts = [
            { threshold: new Decimal('100'), discount: new Decimal('0.05') }, // 5% off $100+
            { threshold: new Decimal('500'), discount: new Decimal('0.10') }, // 10% off $500+
            { threshold: new Decimal('1000'), discount: new Decimal('0.15') }, // 15% off $1000+
            { threshold: new Decimal('5000'), discount: new Decimal('0.20') }, // 20% off $5000+
            { threshold: new Decimal('10000'), discount: new Decimal('0.25') } // 25% off $10000+
        ];

        // Credit packages for prepaid usage
        this.creditPackages = {
            'starter': {
                name: 'Starter Pack',
                credits: new Decimal('50'),
                price: new Decimal('45'), // $45 for $50 worth (10% bonus)
                bonus: new Decimal('0.10')
            },
            'professional': {
                name: 'Professional Pack',
                credits: new Decimal('250'),
                price: new Decimal('225'), // $225 for $250 worth (10% bonus)
                bonus: new Decimal('0.10')
            },
            'enterprise': {
                name: 'Enterprise Pack',
                credits: new Decimal('1000'),
                price: new Decimal('850'), // $850 for $1000 worth (15% bonus)
                bonus: new Decimal('0.15')
            },
            'enterprise_plus': {
                name: 'Enterprise Plus Pack',
                credits: new Decimal('5000'),
                price: new Decimal('4000'), // $4000 for $5000 worth (20% bonus)
                bonus: new Decimal('0.20')
            }
        };
    }

    async createComputeSession(orgId, departmentId, userId, resourceType, estimatedUsage = null) {
        try {
            const sessionId = uuidv4();
            const timestamp = Date.now();
            
            if (!this.computePricing[resourceType]) {
                throw new Error(`Invalid resource type: ${resourceType}`);
            }

            // Check organization compute limits
            const limits = await this.getOrganizationLimits(orgId, departmentId);
            await this.validateComputeLimits(limits, resourceType, estimatedUsage);

            const sessionData = {
                id: sessionId,
                orgId,
                departmentId,
                userId,
                resourceType,
                estimatedUsage: estimatedUsage?.toString() || null,
                actualUsage: '0',
                startTime: timestamp,
                endTime: null,
                cost: '0',
                status: 'active',
                metadata: JSON.stringify({}),
                createdAt: timestamp
            };

            await this.redis.hset(`compute_session:${sessionId}`, sessionData);
            await this.redis.sadd(`org_compute_sessions:${orgId}`, sessionId);
            await this.redis.sadd(`dept_compute_sessions:${departmentId}`, sessionId);
            await this.redis.sadd(`user_compute_sessions:${userId}`, sessionId);
            
            // Track active sessions
            await this.redis.sadd('active_compute_sessions', sessionId);

            this.logger.info(`Created compute session: ${sessionId} for org: ${orgId}`);
            return sessionData;
        } catch (error) {
            this.logger.error('Error creating compute session:', error);
            throw error;
        }
    }

    async updateComputeUsage(sessionId, usageAmount, metadata = {}) {
        try {
            const sessionData = await this.redis.hgetall(`compute_session:${sessionId}`);
            if (!sessionData.id) {
                throw new Error(`Compute session not found: ${sessionId}`);
            }

            if (sessionData.status !== 'active') {
                throw new Error(`Cannot update inactive session: ${sessionId}`);
            }

            const currentUsage = new Decimal(sessionData.actualUsage || '0');
            const newUsage = currentUsage.add(new Decimal(usageAmount));
            
            // Calculate cost
            const resourceType = sessionData.resourceType;
            const unitPrice = this.computePricing[resourceType].price;
            const additionalCost = unitPrice.mul(new Decimal(usageAmount));
            const currentCost = new Decimal(sessionData.cost || '0');
            const newCost = currentCost.add(additionalCost);

            // Update session
            await this.redis.hset(`compute_session:${sessionId}`, {
                actualUsage: newUsage.toString(),
                cost: newCost.toString(),
                metadata: JSON.stringify({ ...JSON.parse(sessionData.metadata || '{}'), ...metadata }),
                updatedAt: Date.now()
            });

            // Update organization usage tracking
            await this.updateOrganizationUsage(sessionData.orgId, sessionData.departmentId, resourceType, usageAmount, additionalCost);

            // Check for budget alerts
            await this.checkBudgetAlerts(sessionData.orgId, sessionData.departmentId);

            this.logger.info(`Updated compute usage for session ${sessionId}: +${usageAmount} ${resourceType}`);
            return { newUsage: newUsage.toString(), newCost: newCost.toString() };
        } catch (error) {
            this.logger.error('Error updating compute usage:', error);
            throw error;
        }
    }

    async endComputeSession(sessionId) {
        try {
            const sessionData = await this.redis.hgetall(`compute_session:${sessionId}`);
            if (!sessionData.id) {
                throw new Error(`Compute session not found: ${sessionId}`);
            }

            const endTime = Date.now();
            const totalCost = new Decimal(sessionData.cost || '0');

            await this.redis.hset(`compute_session:${sessionId}`, {
                status: 'completed',
                endTime,
                updatedAt: endTime
            });

            // Remove from active sessions
            await this.redis.srem('active_compute_sessions', sessionId);

            // Record billing entry
            await this.createBillingEntry(sessionData.orgId, sessionData.departmentId, {
                sessionId,
                resourceType: sessionData.resourceType,
                usage: sessionData.actualUsage,
                cost: totalCost.toString(),
                period: moment().format('YYYY-MM'),
                timestamp: endTime
            });

            // Broadcast usage update
            if (this.broadcast) {
                this.broadcast(`org-analytics-${sessionData.orgId}`, {
                    type: 'compute_session_ended',
                    sessionId,
                    resourceType: sessionData.resourceType,
                    totalCost: totalCost.toString(),
                    usage: sessionData.actualUsage
                });
            }

            this.logger.info(`Ended compute session: ${sessionId}, total cost: $${totalCost}`);
            return { totalCost: totalCost.toString(), usage: sessionData.actualUsage };
        } catch (error) {
            this.logger.error('Error ending compute session:', error);
            throw error;
        }
    }

    async getOrganizationLimits(orgId, departmentId) {
        const orgLimits = await this.redis.hgetall(`org_compute_limits:${orgId}`);
        const deptLimits = await this.redis.hgetall(`dept_compute_limits:${departmentId}`);
        
        return {
            organization: {
                maxMonthlyCost: orgLimits.maxMonthlyCost || '10000', // $10k default
                maxConcurrentSessions: parseInt(orgLimits.maxConcurrentSessions || '100'),
                resourceLimits: JSON.parse(orgLimits.resourceLimits || '{}')
            },
            department: {
                maxMonthlyCost: deptLimits.maxMonthlyCost || '1000', // $1k default
                maxConcurrentSessions: parseInt(deptLimits.maxConcurrentSessions || '10'),
                resourceLimits: JSON.parse(deptLimits.resourceLimits || '{}')
            }
        };
    }

    async validateComputeLimits(limits, resourceType, estimatedUsage) {
        // Check concurrent sessions
        const activeSessions = await this.redis.scard('active_compute_sessions');
        if (activeSessions >= limits.organization.maxConcurrentSessions) {
            throw new Error('Organization concurrent session limit exceeded');
        }

        // Check monthly cost limits (simplified check)
        const currentMonth = moment().format('YYYY-MM');
        const monthlyCost = await this.redis.get(`monthly_cost:${currentMonth}`) || '0';
        const maxMonthlyCost = new Decimal(limits.organization.maxMonthlyCost);
        
        if (new Decimal(monthlyCost).gte(maxMonthlyCost)) {
            throw new Error('Monthly cost limit exceeded');
        }

        // Additional resource-specific validation could be added here
        return true;
    }

    async updateOrganizationUsage(orgId, departmentId, resourceType, usageAmount, cost) {
        const currentMonth = moment().format('YYYY-MM');
        
        // Update organization monthly totals
        await this.redis.incrbyfloat(`org_monthly_cost:${orgId}:${currentMonth}`, parseFloat(cost.toString()));
        await this.redis.incrbyfloat(`org_monthly_usage:${orgId}:${resourceType}:${currentMonth}`, parseFloat(usageAmount));
        
        // Update department monthly totals
        await this.redis.incrbyfloat(`dept_monthly_cost:${departmentId}:${currentMonth}`, parseFloat(cost.toString()));
        await this.redis.incrbyfloat(`dept_monthly_usage:${departmentId}:${resourceType}:${currentMonth}`, parseFloat(usageAmount));
        
        // Update daily totals for analytics
        const today = moment().format('YYYY-MM-DD');
        await this.redis.incrbyfloat(`org_daily_cost:${orgId}:${today}`, parseFloat(cost.toString()));
        await this.redis.incrbyfloat(`dept_daily_cost:${departmentId}:${today}`, parseFloat(cost.toString()));
    }

    async checkBudgetAlerts(orgId, departmentId) {
        try {
            const currentMonth = moment().format('YYYY-MM');
            const orgMonthlyCost = new Decimal(await this.redis.get(`org_monthly_cost:${orgId}:${currentMonth}`) || '0');
            const deptMonthlyCost = new Decimal(await this.redis.get(`dept_monthly_cost:${departmentId}:${currentMonth}`) || '0');
            
            const limits = await this.getOrganizationLimits(orgId, departmentId);
            const orgLimit = new Decimal(limits.organization.maxMonthlyCost);
            const deptLimit = new Decimal(limits.department.maxMonthlyCost);
            
            // Check for 80% and 95% thresholds
            const orgPercentage = orgMonthlyCost.div(orgLimit).mul(100);
            const deptPercentage = deptMonthlyCost.div(deptLimit).mul(100);
            
            if (orgPercentage.gte(80) || deptPercentage.gte(80)) {
                const alertLevel = orgPercentage.gte(95) || deptPercentage.gte(95) ? 'critical' : 'warning';
                
                if (this.broadcast) {
                    this.broadcast(`usage-alerts-${orgId}`, {
                        type: 'budget_alert',
                        level: alertLevel,
                        organization: {
                            spent: orgMonthlyCost.toString(),
                            limit: orgLimit.toString(),
                            percentage: orgPercentage.toFixed(1)
                        },
                        department: {
                            spent: deptMonthlyCost.toString(),
                            limit: deptLimit.toString(),
                            percentage: deptPercentage.toFixed(1)
                        },
                        timestamp: Date.now()
                    });
                }
            }
        } catch (error) {
            this.logger.error('Error checking budget alerts:', error);
        }
    }

    async createBillingEntry(orgId, departmentId, details) {
        const billingId = uuidv4();
        const billingData = {
            id: billingId,
            orgId,
            departmentId,
            ...details,
            createdAt: Date.now()
        };
        
        await this.redis.hset(`billing_entry:${billingId}`, billingData);
        await this.redis.sadd(`org_billing:${orgId}:${details.period}`, billingId);
        await this.redis.sadd(`dept_billing:${departmentId}:${details.period}`, billingId);
    }

    async purchaseCredits(orgId, packageName, paymentDetails) {
        try {
            if (!this.creditPackages[packageName]) {
                throw new Error(`Invalid credit package: ${packageName}`);
            }

            const package_ = this.creditPackages[packageName];
            const purchaseId = uuidv4();
            
            // Process payment
            const paymentResult = await this.processCreditsPayment(package_.price, paymentDetails);
            
            if (paymentResult.success) {
                const purchaseData = {
                    id: purchaseId,
                    orgId,
                    packageName,
                    creditsAmount: package_.credits.toString(),
                    price: package_.price.toString(),
                    bonus: package_.bonus.toString(),
                    paymentId: paymentResult.paymentId,
                    status: 'completed',
                    createdAt: Date.now()
                };
                
                await this.redis.hset(`credit_purchase:${purchaseId}`, purchaseData);
                
                // Add credits to organization balance
                await this.redis.incrbyfloat(`org_credit_balance:${orgId}`, parseFloat(package_.credits.toString()));
                
                // Record transaction
                await this.recordCreditTransaction(orgId, package_.credits, 'purchase', purchaseId);
                
                this.logger.info(`Credits purchased: ${purchaseId} for org: ${orgId}`);
                return { success: true, purchaseId, credits: package_.credits.toString() };
            } else {
                return { success: false, error: paymentResult.error };
            }
        } catch (error) {
            this.logger.error('Error purchasing credits:', error);
            throw error;
        }
    }

    async processCreditsPayment(amount, paymentDetails) {
        // Mock payment processing
        await new Promise(resolve => setTimeout(resolve, 1500));
        return {
            success: Math.random() > 0.05,
            paymentId: `cred_pay_${uuidv4()}`,
            transactionId: `cred_txn_${uuidv4()}`
        };
    }

    async recordCreditTransaction(orgId, amount, type, referenceId) {
        const transactionId = uuidv4();
        const transactionData = {
            id: transactionId,
            orgId,
            amount: amount.toString(),
            type, // 'purchase', 'usage', 'refund'
            referenceId,
            timestamp: Date.now()
        };
        
        await this.redis.hset(`credit_transaction:${transactionId}`, transactionData);
        await this.redis.sadd(`org_credit_transactions:${orgId}`, transactionId);
    }

    async getOrganizationUsage(orgId, period = null) {
        try {
            const currentPeriod = period || moment().format('YYYY-MM');
            
            const usage = {
                period: currentPeriod,
                totalCost: new Decimal('0'),
                resourceUsage: {},
                departmentBreakdown: {},
                creditBalance: new Decimal('0')
            };

            // Get total monthly cost
            const monthlyCost = await this.redis.get(`org_monthly_cost:${orgId}:${currentPeriod}`) || '0';
            usage.totalCost = new Decimal(monthlyCost);
            
            // Get resource usage breakdown
            for (const resourceType of Object.keys(this.computePricing)) {
                const resourceUsage = await this.redis.get(`org_monthly_usage:${orgId}:${resourceType}:${currentPeriod}`) || '0';
                usage.resourceUsage[resourceType] = resourceUsage;
            }
            
            // Get department breakdown
            const departments = await this.getOrganizationDepartments(orgId);
            for (const deptId of departments) {
                const deptCost = await this.redis.get(`dept_monthly_cost:${deptId}:${currentPeriod}`) || '0';
                usage.departmentBreakdown[deptId] = new Decimal(deptCost);
            }
            
            // Get credit balance
            const creditBalance = await this.redis.get(`org_credit_balance:${orgId}`) || '0';
            usage.creditBalance = new Decimal(creditBalance);
            
            // Apply volume discounts
            usage.volumeDiscount = this.calculateVolumeDiscount(usage.totalCost);
            usage.discountedCost = usage.totalCost.mul(new Decimal('1').sub(usage.volumeDiscount));
            
            return {
                ...usage,
                totalCost: usage.totalCost.toString(),
                creditBalance: usage.creditBalance.toString(),
                volumeDiscount: usage.volumeDiscount.toString(),
                discountedCost: usage.discountedCost.toString(),
                departmentBreakdown: Object.fromEntries(
                    Object.entries(usage.departmentBreakdown).map(([dept, cost]) => [dept, cost.toString()])
                )
            };
        } catch (error) {
            this.logger.error('Error getting organization usage:', error);
            throw error;
        }
    }

    calculateVolumeDiscount(totalCost) {
        let discount = new Decimal('0');
        
        for (const tier of this.volumeDiscounts.reverse()) {
            if (totalCost.gte(tier.threshold)) {
                discount = tier.discount;
                break;
            }
        }
        
        return discount;
    }

    async getOrganizationDepartments(orgId) {
        // This would typically come from the organization service
        return await this.redis.smembers(`org_departments:${orgId}`) || [];
    }

    async getStats() {
        try {
            const stats = {
                activeSessions: await this.redis.scard('active_compute_sessions'),
                totalOrganizations: 0,
                totalRevenue: new Decimal('0'),
                resourceUsageStats: {},
                creditPackageStats: {},
                averageSessionCost: new Decimal('0')
            };

            // Get resource usage stats
            for (const resourceType of Object.keys(this.computePricing)) {
                const usage = await this.redis.get(`global_usage:${resourceType}`) || '0';
                stats.resourceUsageStats[resourceType] = usage;
            }

            // Get credit package stats
            const creditPurchaseKeys = await this.redis.keys('credit_purchase:*');
            let totalSessions = 0;
            let totalSessionCost = new Decimal('0');
            
            for (const key of creditPurchaseKeys) {
                const purchase = await this.redis.hgetall(key);
                if (purchase.status === 'completed') {
                    stats.totalRevenue = stats.totalRevenue.add(new Decimal(purchase.price || '0'));
                    stats.creditPackageStats[purchase.packageName] = (stats.creditPackageStats[purchase.packageName] || 0) + 1;
                }
            }

            const sessionKeys = await this.redis.keys('compute_session:*');
            for (const key of sessionKeys) {
                const session = await this.redis.hgetall(key);
                if (session.status === 'completed') {
                    totalSessions++;
                    totalSessionCost = totalSessionCost.add(new Decimal(session.cost || '0'));
                }
            }

            stats.averageSessionCost = totalSessions > 0 ? totalSessionCost.div(totalSessions) : new Decimal('0');
            stats.totalOrganizations = new Set((await this.redis.keys('org_monthly_cost:*')).map(key => key.split(':')[1])).size;

            return {
                ...stats,
                totalRevenue: stats.totalRevenue.toString(),
                averageSessionCost: stats.averageSessionCost.toString()
            };
        } catch (error) {
            this.logger.error('Error getting pay-as-you-go stats:', error);
            return {};
        }
    }

    startScheduler() {
        // Process monthly billing on the 1st of each month
        cron.schedule('0 0 1 * *', async () => {
            await this.processMonthlyBilling();
        });

        // Clean up old usage data every week
        cron.schedule('0 0 * * 0', async () => {
            await this.cleanupOldUsageData();
        });

        this.logger.info('Pay-as-you-go scheduler started');
    }

    async processMonthlyBilling() {
        try {
            this.logger.info('Processing monthly pay-as-you-go billing');
            const lastMonth = moment().subtract(1, 'month').format('YYYY-MM');
            
            // Process billing for all organizations with usage last month
            const orgKeys = await this.redis.keys(`org_monthly_cost:*:${lastMonth}`);
            
            for (const key of orgKeys) {
                const orgId = key.split(':')[1];
                await this.generateMonthlyBill(orgId, lastMonth);
            }
        } catch (error) {
            this.logger.error('Error processing monthly billing:', error);
        }
    }

    async generateMonthlyBill(orgId, period) {
        const usage = await this.getOrganizationUsage(orgId, period);
        const billId = uuidv4();
        
        const billData = {
            id: billId,
            orgId,
            period,
            totalCost: usage.totalCost,
            discountedCost: usage.discountedCost,
            volumeDiscount: usage.volumeDiscount,
            resourceBreakdown: JSON.stringify(usage.resourceUsage),
            departmentBreakdown: JSON.stringify(usage.departmentBreakdown),
            generatedAt: Date.now(),
            status: 'pending'
        };
        
        await this.redis.hset(`monthly_bill:${billId}`, billData);
        await this.redis.sadd(`org_bills:${orgId}`, billId);
        
        this.logger.info(`Generated monthly bill ${billId} for org ${orgId}: $${usage.discountedCost}`);
    }

    async cleanupOldUsageData() {
        try {
            const cutoffDate = moment().subtract(13, 'months').format('YYYY-MM');
            const keys = await this.redis.keys(`*:${cutoffDate}`);
            
            if (keys.length > 0) {
                await this.redis.del(...keys);
                this.logger.info(`Cleaned up ${keys.length} old usage data keys from ${cutoffDate}`);
            }
        } catch (error) {
            this.logger.error('Error cleaning up old usage data:', error);
        }
    }

    stopScheduler() {
        this.logger.info('Pay-as-you-go scheduler stopped');
    }

    // Additional route methods
    async recordUsage(orgId, resourceType, amount, metadata = {}) {
        // Create a session for the usage recording
        const departmentId = metadata.departmentId || 'default';
        const userId = metadata.userId || 'system';
        
        const session = await this.createComputeSession(orgId, departmentId, userId, resourceType, amount);
        await this.updateComputeUsage(session.id, amount, metadata);
        const result = await this.endComputeSession(session.id);
        
        return {
            sessionId: session.id,
            orgId,
            resourceType,
            amount: amount.toString(),
            cost: result.totalCost,
            metadata
        };
    }

    async calculateCost(orgId, usageData) {
        let totalCost = new Decimal('0');
        
        for (const [resourceType, amount] of Object.entries(usageData)) {
            const pricing = this.computePricing[resourceType];
            if (pricing) {
                const cost = pricing.price.mul(amount);
                totalCost = totalCost.add(cost);
            }
        }

        // Apply volume discount
        const volumeDiscount = this.calculateVolumeDiscount(totalCost);
        const discountedCost = totalCost.mul(new Decimal('1').sub(volumeDiscount));

        return {
            totalCost: totalCost.toString(),
            volumeDiscount: volumeDiscount.toString(),
            discountedCost: discountedCost.toString(),
            resourceBreakdown: Object.fromEntries(
                Object.entries(usageData).map(([resource, amount]) => [
                    resource, 
                    this.computePricing[resource] ? this.computePricing[resource].price.mul(amount).toString() : '0'
                ])
            )
        };
    }

    async generateUsageReport(orgId, period) {
        return await this.getOrganizationUsage(orgId, period);
    }

    async getCurrentPricing() {
        return Object.entries(this.computePricing).map(([key, pricing]) => ({
            resourceType: key,
            ...pricing,
            price: pricing.price.toString()
        }));
    }
}