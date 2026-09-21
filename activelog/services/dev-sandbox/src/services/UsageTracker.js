const EventEmitter = require('events');
const { performance } = require('perf_hooks');

class UsageTracker extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            billingCycle: config.billingCycle || 'monthly', // monthly, weekly, daily
            tierLimits: {
                free: {
                    cpuHours: 10,
                    memoryGBHours: 5,
                    storageGB: 1,
                    apiCalls: 1000,
                    deployments: 5,
                    collaborators: 2
                },
                pro: {
                    cpuHours: 100,
                    memoryGBHours: 50,
                    storageGB: 10,
                    apiCalls: 10000,
                    deployments: 50,
                    collaborators: 10
                },
                enterprise: {
                    cpuHours: 1000,
                    memoryGBHours: 500,
                    storageGB: 100,
                    apiCalls: 100000,
                    deployments: 500,
                    collaborators: 100
                }
            },
            pricing: {
                cpu: { perHour: 0.05 }, // $0.05 per CPU hour
                memory: { perGBHour: 0.01 }, // $0.01 per GB-hour
                storage: { perGBMonth: 0.10 }, // $0.10 per GB per month
                apiCall: { per1000: 0.002 }, // $0.002 per 1000 API calls
                deployment: { each: 0.01 }, // $0.01 per deployment
                collaborator: { perMonth: 5.00 } // $5.00 per collaborator per month
            },
            aggregationInterval: config.aggregationInterval || 300000, // 5 minutes
            ...config
        };

        this.usage = new Map(); // userId -> usage data
        this.activeResources = new Map(); // Track active resource usage
        this.billingPeriods = new Map(); // Track billing periods
        this.invoices = new Map(); // Store generated invoices

        this.initializeTracker();
    }

    initializeTracker() {
        this.startUsageAggregation();
        this.startBillingCycleMonitor();
        this.emit('tracker-initialized', {
            timestamp: new Date(),
            billingCycle: this.config.billingCycle
        });
    }

    startUsageTracking(userId, userTier, resourceType, resourceId, metadata = {}) {
        const trackingId = `${userId}-${resourceType}-${resourceId}`;
        const startTime = performance.now();

        const trackingData = {
            userId,
            userTier,
            resourceType,
            resourceId,
            startTime,
            metadata,
            timestamp: new Date()
        };

        this.activeResources.set(trackingId, trackingData);
        this.emit('tracking-started', trackingData);

        return trackingId;
    }

    stopUsageTracking(trackingId, metadata = {}) {
        const trackingData = this.activeResources.get(trackingId);
        if (!trackingData) {
            throw new Error(`No active tracking found for ${trackingId}`);
        }

        const endTime = performance.now();
        const duration = (endTime - trackingData.startTime) / 1000; // Convert to seconds

        const usageRecord = {
            ...trackingData,
            endTime,
            duration,
            endMetadata: metadata,
            cost: this.calculateResourceCost(trackingData.resourceType, duration, metadata)
        };

        this.recordUsage(trackingData.userId, usageRecord);
        this.activeResources.delete(trackingId);

        this.emit('tracking-stopped', usageRecord);
        return usageRecord;
    }

    recordUsage(userId, usageRecord) {
        if (!this.usage.has(userId)) {
            this.initializeUserUsage(userId);
        }

        const userUsage = this.usage.get(userId);
        const currentPeriod = this.getCurrentBillingPeriod();

        if (!userUsage.periods[currentPeriod]) {
            userUsage.periods[currentPeriod] = this.createEmptyPeriodUsage();
        }

        const periodUsage = userUsage.periods[currentPeriod];

        switch (usageRecord.resourceType) {
            case 'cpu':
                periodUsage.cpu.hours += usageRecord.duration / 3600;
                periodUsage.cpu.cost += usageRecord.cost;
                break;
            case 'memory':
                const memoryGB = usageRecord.endMetadata.memoryUsageBytes / (1024 ** 3);
                const memoryGBHours = memoryGB * (usageRecord.duration / 3600);
                periodUsage.memory.gbHours += memoryGBHours;
                periodUsage.memory.cost += usageRecord.cost;
                break;
            case 'storage':
                periodUsage.storage.gb = Math.max(periodUsage.storage.gb, usageRecord.endMetadata.storageGB || 0);
                periodUsage.storage.cost = this.calculateStorageCost(periodUsage.storage.gb);
                break;
            case 'api':
                periodUsage.api.calls += 1;
                periodUsage.api.cost += usageRecord.cost;
                break;
            case 'deployment':
                periodUsage.deployments.count += 1;
                periodUsage.deployments.cost += usageRecord.cost;
                break;
            case 'collaboration':
                periodUsage.collaboration.activeUsers = new Set([
                    ...Array.from(periodUsage.collaboration.activeUsers || []),
                    usageRecord.metadata.collaboratorId
                ]);
                periodUsage.collaboration.cost = this.calculateCollaborationCost(
                    periodUsage.collaboration.activeUsers.size
                );
                break;
        }

        periodUsage.records.push(usageRecord);
        periodUsage.totalCost = this.calculateTotalPeriodCost(periodUsage);
        userUsage.totalCost = Object.values(userUsage.periods).reduce(
            (sum, period) => sum + period.totalCost, 0
        );

        this.emit('usage-recorded', { userId, usageRecord, periodUsage });
    }

    initializeUserUsage(userId) {
        this.usage.set(userId, {
            userId,
            periods: {},
            totalCost: 0,
            tier: 'free',
            created: new Date()
        });
    }

    createEmptyPeriodUsage() {
        return {
            cpu: { hours: 0, cost: 0 },
            memory: { gbHours: 0, cost: 0 },
            storage: { gb: 0, cost: 0 },
            api: { calls: 0, cost: 0 },
            deployments: { count: 0, cost: 0 },
            collaboration: { activeUsers: new Set(), cost: 0 },
            records: [],
            totalCost: 0,
            period: this.getCurrentBillingPeriod(),
            startDate: this.getPeriodStartDate(),
            endDate: this.getPeriodEndDate()
        };
    }

    calculateResourceCost(resourceType, duration, metadata = {}) {
        const pricing = this.config.pricing;

        switch (resourceType) {
            case 'cpu':
                return (duration / 3600) * pricing.cpu.perHour;
            case 'memory':
                const memoryGB = metadata.memoryUsageBytes / (1024 ** 3);
                const memoryGBHours = memoryGB * (duration / 3600);
                return memoryGBHours * pricing.memory.perGBHour;
            case 'api':
                return pricing.apiCall.per1000 / 1000;
            case 'deployment':
                return pricing.deployment.each;
            case 'storage':
                return metadata.storageGB * pricing.storage.perGBMonth;
            case 'collaboration':
                return pricing.collaborator.perMonth / 30; // Daily rate
            default:
                return 0;
        }
    }

    calculateStorageCost(storageGB) {
        return storageGB * this.config.pricing.storage.perGBMonth;
    }

    calculateCollaborationCost(activeCollaborators) {
        return activeCollaborators * this.config.pricing.collaborator.perMonth;
    }

    calculateTotalPeriodCost(periodUsage) {
        return periodUsage.cpu.cost +
               periodUsage.memory.cost +
               periodUsage.storage.cost +
               periodUsage.api.cost +
               periodUsage.deployments.cost +
               periodUsage.collaboration.cost;
    }

    getUserUsage(userId, period = null) {
        const userUsage = this.usage.get(userId);
        if (!userUsage) {
            return null;
        }

        if (period) {
            return userUsage.periods[period] || null;
        }

        return {
            ...userUsage,
            currentPeriod: userUsage.periods[this.getCurrentBillingPeriod()] || this.createEmptyPeriodUsage()
        };
    }

    checkUserLimits(userId, userTier, resourceType) {
        const limits = this.config.tierLimits[userTier] || this.config.tierLimits.free;
        const usage = this.getUserUsage(userId);
        
        if (!usage) {
            return { withinLimits: true, limit: limits[resourceType], used: 0 };
        }

        const currentPeriod = usage.currentPeriod || this.createEmptyPeriodUsage();
        let used = 0;

        switch (resourceType) {
            case 'cpuHours':
                used = currentPeriod.cpu.hours;
                break;
            case 'memoryGBHours':
                used = currentPeriod.memory.gbHours;
                break;
            case 'storageGB':
                used = currentPeriod.storage.gb;
                break;
            case 'apiCalls':
                used = currentPeriod.api.calls;
                break;
            case 'deployments':
                used = currentPeriod.deployments.count;
                break;
            case 'collaborators':
                used = currentPeriod.collaboration.activeUsers?.size || 0;
                break;
        }

        const withinLimits = used < limits[resourceType];
        const remaining = Math.max(0, limits[resourceType] - used);

        return {
            withinLimits,
            limit: limits[resourceType],
            used,
            remaining,
            percentage: (used / limits[resourceType]) * 100
        };
    }

    async generateInvoice(userId, period = null) {
        const targetPeriod = period || this.getCurrentBillingPeriod();
        const usage = this.getUserUsage(userId, targetPeriod);
        
        if (!usage) {
            throw new Error('No usage data found for user');
        }

        const invoiceId = this.generateInvoiceId();
        const invoice = {
            id: invoiceId,
            userId,
            period: targetPeriod,
            generated: new Date(),
            dueDate: this.calculateDueDate(),
            lineItems: [
                {
                    description: `CPU Usage (${usage.cpu.hours.toFixed(2)} hours)`,
                    quantity: usage.cpu.hours,
                    unitPrice: this.config.pricing.cpu.perHour,
                    total: usage.cpu.cost
                },
                {
                    description: `Memory Usage (${usage.memory.gbHours.toFixed(2)} GB-hours)`,
                    quantity: usage.memory.gbHours,
                    unitPrice: this.config.pricing.memory.perGBHour,
                    total: usage.memory.cost
                },
                {
                    description: `Storage Usage (${usage.storage.gb.toFixed(2)} GB)`,
                    quantity: usage.storage.gb,
                    unitPrice: this.config.pricing.storage.perGBMonth,
                    total: usage.storage.cost
                },
                {
                    description: `API Calls (${usage.api.calls})`,
                    quantity: usage.api.calls,
                    unitPrice: this.config.pricing.apiCall.per1000 / 1000,
                    total: usage.api.cost
                },
                {
                    description: `Deployments (${usage.deployments.count})`,
                    quantity: usage.deployments.count,
                    unitPrice: this.config.pricing.deployment.each,
                    total: usage.deployments.cost
                },
                {
                    description: `Collaborators (${usage.collaboration.activeUsers?.size || 0})`,
                    quantity: usage.collaboration.activeUsers?.size || 0,
                    unitPrice: this.config.pricing.collaborator.perMonth,
                    total: usage.collaboration.cost
                }
            ],
            subtotal: usage.totalCost,
            tax: usage.totalCost * 0.08, // 8% tax
            total: usage.totalCost * 1.08,
            status: 'pending',
            paymentMethod: null
        };

        this.invoices.set(invoiceId, invoice);
        this.emit('invoice-generated', { userId, invoiceId, amount: invoice.total });

        return invoice;
    }

    getUsageAnalytics(userId, options = {}) {
        const usage = this.getUserUsage(userId);
        if (!usage) {
            return null;
        }

        const periods = Object.keys(usage.periods).sort();
        const analytics = {
            trends: {},
            predictions: {},
            recommendations: []
        };

        // Calculate trends
        if (periods.length >= 2) {
            const current = usage.periods[periods[periods.length - 1]];
            const previous = usage.periods[periods[periods.length - 2]];

            analytics.trends = {
                cpu: this.calculateTrend(previous.cpu.hours, current.cpu.hours),
                memory: this.calculateTrend(previous.memory.gbHours, current.memory.gbHours),
                storage: this.calculateTrend(previous.storage.gb, current.storage.gb),
                api: this.calculateTrend(previous.api.calls, current.api.calls),
                cost: this.calculateTrend(previous.totalCost, current.totalCost)
            };
        }

        // Generate predictions
        if (periods.length >= 3) {
            const recent = periods.slice(-3).map(p => usage.periods[p]);
            analytics.predictions = {
                nextPeriodCost: this.predictNextPeriodCost(recent),
                resourceExhaustion: this.predictResourceExhaustion(usage, analytics.trends)
            };
        }

        // Generate recommendations
        analytics.recommendations = this.generateRecommendations(usage, analytics.trends);

        return analytics;
    }

    calculateTrend(previous, current) {
        if (previous === 0) return current > 0 ? 100 : 0;
        return ((current - previous) / previous) * 100;
    }

    predictNextPeriodCost(recentPeriods) {
        const costs = recentPeriods.map(p => p.totalCost);
        const sum = costs.reduce((a, b) => a + b, 0);
        const average = sum / costs.length;
        
        // Simple linear regression for trend
        const trend = (costs[2] - costs[0]) / 2;
        return Math.max(0, average + trend);
    }

    predictResourceExhaustion(usage, trends) {
        const current = usage.currentPeriod;
        const predictions = {};

        // Predict when resources might be exhausted based on current trends
        Object.keys(trends).forEach(resource => {
            if (trends[resource] > 0) {
                const currentUsage = current[resource === 'cost' ? 'totalCost' : resource];
                const growthRate = trends[resource] / 100;
                const daysToExhaustion = Math.log(2) / Math.log(1 + growthRate);
                predictions[resource] = Math.ceil(daysToExhaustion);
            }
        });

        return predictions;
    }

    generateRecommendations(usage, trends) {
        const recommendations = [];
        const current = usage.currentPeriod;

        // Cost optimization recommendations
        if (trends.cost > 20) {
            recommendations.push({
                type: 'cost-optimization',
                priority: 'high',
                message: 'Your costs are increasing rapidly. Consider optimizing resource usage.',
                actions: ['Review CPU-intensive operations', 'Optimize memory usage', 'Clean up unused storage']
            });
        }

        // Tier upgrade recommendations
        const highUsageResources = Object.keys(trends).filter(r => trends[r] > 50);
        if (highUsageResources.length > 2) {
            recommendations.push({
                type: 'tier-upgrade',
                priority: 'medium',
                message: 'Consider upgrading your tier for better resource limits.',
                actions: ['Review Pro tier benefits', 'Calculate cost savings']
            });
        }

        // Storage cleanup
        if (current.storage.gb > 0.8) {
            recommendations.push({
                type: 'storage-cleanup',
                priority: 'medium',
                message: 'Storage usage is high. Consider cleaning up unused files.',
                actions: ['Delete old deployments', 'Compress large files', 'Archive old projects']
            });
        }

        return recommendations;
    }

    startUsageAggregation() {
        setInterval(() => {
            this.aggregateActiveUsage();
        }, this.config.aggregationInterval);
    }

    aggregateActiveUsage() {
        const now = new Date();
        
        for (const [trackingId, trackingData] of this.activeResources.entries()) {
            if (trackingData.resourceType === 'cpu' || trackingData.resourceType === 'memory') {
                const duration = (performance.now() - trackingData.startTime) / 1000;
                
                // Record incremental usage for long-running resources
                const incrementalRecord = {
                    ...trackingData,
                    duration: this.config.aggregationInterval / 1000,
                    endTime: performance.now(),
                    cost: this.calculateResourceCost(
                        trackingData.resourceType, 
                        this.config.aggregationInterval / 1000, 
                        trackingData.metadata
                    ),
                    incremental: true
                };

                this.recordUsage(trackingData.userId, incrementalRecord);
                
                // Reset start time for next interval
                trackingData.startTime = performance.now();
            }
        }

        this.emit('usage-aggregated', { timestamp: now, activeResources: this.activeResources.size });
    }

    startBillingCycleMonitor() {
        const checkInterval = 24 * 60 * 60 * 1000; // Check daily
        
        setInterval(() => {
            this.processBillingCycle();
        }, checkInterval);
    }

    async processBillingCycle() {
        const currentPeriod = this.getCurrentBillingPeriod();
        const previousPeriod = this.getPreviousBillingPeriod();

        // Generate invoices for completed periods
        for (const [userId, userUsage] of this.usage.entries()) {
            if (userUsage.periods[previousPeriod] && !this.hasInvoiceForPeriod(userId, previousPeriod)) {
                try {
                    await this.generateInvoice(userId, previousPeriod);
                } catch (error) {
                    this.emit('billing-error', { userId, period: previousPeriod, error: error.message });
                }
            }
        }

        this.emit('billing-cycle-processed', { period: currentPeriod });
    }

    getCurrentBillingPeriod() {
        const now = new Date();
        if (this.config.billingCycle === 'monthly') {
            return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
        } else if (this.config.billingCycle === 'weekly') {
            const weekNumber = this.getWeekNumber(now);
            return `${now.getFullYear()}-W${weekNumber}`;
        } else {
            return now.toISOString().split('T')[0];
        }
    }

    getPreviousBillingPeriod() {
        const now = new Date();
        if (this.config.billingCycle === 'monthly') {
            const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            return `${prev.getFullYear()}-${String(prev.getMonth() + 1).padStart(2, '0')}`;
        } else if (this.config.billingCycle === 'weekly') {
            const prevWeek = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
            const weekNumber = this.getWeekNumber(prevWeek);
            return `${prevWeek.getFullYear()}-W${weekNumber}`;
        } else {
            const prev = new Date(now.getTime() - 24 * 60 * 60 * 1000);
            return prev.toISOString().split('T')[0];
        }
    }

    getPeriodStartDate() {
        const now = new Date();
        if (this.config.billingCycle === 'monthly') {
            return new Date(now.getFullYear(), now.getMonth(), 1);
        } else if (this.config.billingCycle === 'weekly') {
            const dayOfWeek = now.getDay();
            const startOfWeek = new Date(now.getTime() - dayOfWeek * 24 * 60 * 60 * 1000);
            return startOfWeek;
        } else {
            return new Date(now.getFullYear(), now.getMonth(), now.getDate());
        }
    }

    getPeriodEndDate() {
        const now = new Date();
        if (this.config.billingCycle === 'monthly') {
            return new Date(now.getFullYear(), now.getMonth() + 1, 0);
        } else if (this.config.billingCycle === 'weekly') {
            const dayOfWeek = now.getDay();
            const endOfWeek = new Date(now.getTime() + (6 - dayOfWeek) * 24 * 60 * 60 * 1000);
            return endOfWeek;
        } else {
            return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
        }
    }

    getWeekNumber(date) {
        const firstDayOfYear = new Date(date.getFullYear(), 0, 1);
        const pastDaysOfYear = (date - firstDayOfYear) / 86400000;
        return Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);
    }

    generateInvoiceId() {
        return `inv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    calculateDueDate() {
        const now = new Date();
        return new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000); // 30 days from now
    }

    hasInvoiceForPeriod(userId, period) {
        return Array.from(this.invoices.values())
            .some(invoice => invoice.userId === userId && invoice.period === period);
    }

    getInvoice(invoiceId) {
        return this.invoices.get(invoiceId);
    }

    getUserInvoices(userId) {
        return Array.from(this.invoices.values())
            .filter(invoice => invoice.userId === userId)
            .sort((a, b) => new Date(b.generated) - new Date(a.generated));
    }

    exportUsageReport(userId, format = 'json', period = null) {
        const usage = this.getUserUsage(userId, period);
        if (!usage) {
            throw new Error('No usage data found');
        }

        if (format === 'json') {
            return JSON.stringify(usage, null, 2);
        } else if (format === 'csv') {
            const headers = 'Resource,Usage,Cost,Period\n';
            let rows = '';
            
            if (period) {
                const p = usage;
                rows += `CPU,${p.cpu.hours} hours,${p.cpu.cost},${period}\n`;
                rows += `Memory,${p.memory.gbHours} GB-hours,${p.memory.cost},${period}\n`;
                rows += `Storage,${p.storage.gb} GB,${p.storage.cost},${period}\n`;
                rows += `API Calls,${p.api.calls},${p.api.cost},${period}\n`;
                rows += `Deployments,${p.deployments.count},${p.deployments.cost},${period}\n`;
            } else {
                Object.entries(usage.periods).forEach(([periodKey, p]) => {
                    rows += `CPU,${p.cpu.hours} hours,${p.cpu.cost},${periodKey}\n`;
                    rows += `Memory,${p.memory.gbHours} GB-hours,${p.memory.cost},${periodKey}\n`;
                    rows += `Storage,${p.storage.gb} GB,${p.storage.cost},${periodKey}\n`;
                    rows += `API Calls,${p.api.calls},${p.api.cost},${periodKey}\n`;
                    rows += `Deployments,${p.deployments.count},${p.deployments.cost},${periodKey}\n`;
                });
            }
            
            return headers + rows;
        }

        throw new Error('Unsupported export format');
    }

    getSystemWideStats() {
        const totalUsers = this.usage.size;
        const totalRevenue = Array.from(this.usage.values())
            .reduce((sum, user) => sum + user.totalCost, 0);
        
        const resourceUsage = {
            cpu: 0,
            memory: 0,
            storage: 0,
            api: 0,
            deployments: 0
        };

        Array.from(this.usage.values()).forEach(user => {
            Object.values(user.periods).forEach(period => {
                resourceUsage.cpu += period.cpu.hours;
                resourceUsage.memory += period.memory.gbHours;
                resourceUsage.storage += period.storage.gb;
                resourceUsage.api += period.api.calls;
                resourceUsage.deployments += period.deployments.count;
            });
        });

        return {
            totalUsers,
            totalRevenue,
            resourceUsage,
            activeTrackingSessions: this.activeResources.size,
            totalInvoices: this.invoices.size
        };
    }

    shutdown() {
        // Stop all active tracking
        for (const trackingId of this.activeResources.keys()) {
            try {
                this.stopUsageTracking(trackingId);
            } catch (error) {
                // Continue shutdown even if some tracking fails to stop
            }
        }
        
        this.emit('tracker-shutdown', { 
            timestamp: new Date(),
            finalStats: this.getSystemWideStats()
        });
    }
}

module.exports = UsageTracker;