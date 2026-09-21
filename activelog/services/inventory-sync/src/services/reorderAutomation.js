const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');

class ReorderAutomationManager extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.reorderRules = new Map();
        this.pendingReorders = new Map();
        this.seasonalPatterns = new Map();
        this.demandForecasts = new Map();
        this.approvalWorkflows = new Map();
        
        this.setupEventHandlers();
        this.startAutomationEngine();
        this.startDemandAnalysis();
    }

    setupEventHandlers() {
        this.on('stock_level_low', this.handleLowStockAlert.bind(this));
        this.on('reorder_triggered', this.handleReorderTriggered.bind(this));
        this.on('seasonal_demand_detected', this.handleSeasonalDemand.bind(this));
        this.on('supplier_lead_time_changed', this.handleLeadTimeChange.bind(this));
    }

    async createReorderRule(ruleData) {
        try {
            const ruleId = uuidv4();
            const rule = {
                id: ruleId,
                locationId: ruleData.locationId,
                itemId: ruleData.itemId,
                name: ruleData.name || `Auto-reorder for ${ruleData.itemId}`,
                type: ruleData.type || 'threshold', // threshold, predictive, scheduled
                parameters: {
                    minimumStock: ruleData.minimumStock,
                    reorderPoint: ruleData.reorderPoint,
                    reorderQuantity: ruleData.reorderQuantity,
                    maxStock: ruleData.maxStock,
                    safetyStock: ruleData.safetyStock || 0,
                    leadTimeDays: ruleData.leadTimeDays || 7,
                    seasonalAdjustment: ruleData.seasonalAdjustment || false,
                    demandForecastWeight: ruleData.demandForecastWeight || 0.3
                },
                suppliers: ruleData.suppliers || [],
                conditions: {
                    activeHours: ruleData.activeHours || { start: '09:00', end: '17:00' },
                    activeDays: ruleData.activeDays || [1, 2, 3, 4, 5], // Mon-Fri
                    excludeDates: ruleData.excludeDates || [],
                    minimumDaysBetweenOrders: ruleData.minimumDaysBetweenOrders || 1
                },
                approval: {
                    required: ruleData.approvalRequired || false,
                    threshold: ruleData.approvalThreshold || 1000,
                    approvers: ruleData.approvers || [],
                    autoApproveBelow: ruleData.autoApproveBelow || 500
                },
                status: 'active',
                createdAt: new Date(),
                createdBy: ruleData.createdBy,
                lastTriggered: null,
                totalTriggers: 0,
                performance: {
                    stockouts: 0,
                    overstock: 0,
                    totalOrders: 0,
                    averageOrderValue: 0,
                    costSavings: 0
                }
            };

            this.reorderRules.set(ruleId, rule);
            await this.redis.hset('reorder_rules', ruleId, JSON.stringify(rule));
            
            this.logger.info('Reorder rule created', { 
                ruleId, 
                itemId: rule.itemId, 
                type: rule.type 
            });
            
            this.io.to(`location_${rule.locationId}`).emit('reorder_rule_created', {
                ruleId,
                itemId: rule.itemId,
                type: rule.type,
                reorderPoint: rule.parameters.reorderPoint
            });
            
            return { success: true, ruleId, rule: this.sanitizeRuleData(rule) };
        } catch (error) {
            this.logger.error('Failed to create reorder rule', { error: error.message, ruleData });
            throw new Error(`Reorder rule creation failed: ${error.message}`);
        }
    }

    async checkInventoryLevels(locationId, itemId = null) {
        try {
            const itemsToCheck = itemId ? [itemId] : await this.getAllLocationItems(locationId);
            const alerts = [];
            
            for (const item of itemsToCheck) {
                const currentStock = await this.getCurrentStockLevel(locationId, item);
                const rules = await this.getRulesForItem(locationId, item);
                
                for (const rule of rules) {
                    if (rule.status !== 'active') continue;
                    
                    const shouldReorder = await this.evaluateReorderCondition(rule, currentStock, item);
                    
                    if (shouldReorder) {
                        alerts.push({
                            ruleId: rule.id,
                            itemId: item,
                            currentStock,
                            reorderPoint: rule.parameters.reorderPoint,
                            recommendedQuantity: await this.calculateOptimalOrderQuantity(rule, currentStock)
                        });
                        
                        this.emit('stock_level_low', {
                            locationId,
                            itemId: item,
                            currentStock,
                            rule
                        });
                    }
                }
            }
            
            return alerts;
        } catch (error) {
            this.logger.error('Failed to check inventory levels', { error: error.message, locationId, itemId });
            throw error;
        }
    }

    async evaluateReorderCondition(rule, currentStock, itemId) {
        const now = new Date();
        
        // Check if within active hours
        if (!this.isWithinActiveHours(now, rule.conditions)) {
            return false;
        }
        
        // Check minimum days between orders
        if (rule.lastTriggered) {
            const daysSinceLastOrder = moment(now).diff(moment(rule.lastTriggered), 'days');
            if (daysSinceLastOrder < rule.conditions.minimumDaysBetweenOrders) {
                return false;
            }
        }
        
        switch (rule.type) {
            case 'threshold':
                return currentStock <= rule.parameters.reorderPoint;
                
            case 'predictive':
                return await this.evaluatePredictiveReorder(rule, currentStock, itemId);
                
            case 'scheduled':
                return this.evaluateScheduledReorder(rule);
                
            default:
                return currentStock <= rule.parameters.reorderPoint;
        }
    }

    async evaluatePredictiveReorder(rule, currentStock, itemId) {
        try {
            const forecast = await this.getDemandForecast(rule.locationId, itemId);
            const leadTimeDays = rule.parameters.leadTimeDays;
            
            // Calculate predicted demand during lead time
            const predictedDemand = forecast.dailyAverage * leadTimeDays;
            const adjustedReorderPoint = predictedDemand + rule.parameters.safetyStock;
            
            // Apply seasonal adjustment
            if (rule.parameters.seasonalAdjustment) {
                const seasonalFactor = await this.getSeasonalFactor(rule.locationId, itemId);
                return currentStock <= (adjustedReorderPoint * seasonalFactor);
            }
            
            return currentStock <= adjustedReorderPoint;
        } catch (error) {
            this.logger.error('Predictive reorder evaluation failed', { error: error.message });
            // Fallback to threshold-based reorder
            return currentStock <= rule.parameters.reorderPoint;
        }
    }

    evaluateScheduledReorder(rule) {
        // Implementation for scheduled reorders (e.g., weekly, monthly)
        const now = moment();
        const schedule = rule.parameters.schedule;
        
        if (schedule.frequency === 'weekly') {
            return now.day() === schedule.dayOfWeek && 
                   now.hour() >= parseInt(schedule.time.split(':')[0]);
        }
        
        if (schedule.frequency === 'monthly') {
            return now.date() === schedule.dayOfMonth && 
                   now.hour() >= parseInt(schedule.time.split(':')[0]);
        }
        
        return false;
    }

    async calculateOptimalOrderQuantity(rule, currentStock) {
        try {
            const forecast = await this.getDemandForecast(rule.locationId, rule.itemId);
            const leadTimeDays = rule.parameters.leadTimeDays;
            
            // Economic Order Quantity (EOQ) calculation
            const annualDemand = forecast.dailyAverage * 365;
            const orderingCost = rule.parameters.orderingCost || 25; // Default $25 per order
            const holdingCostRate = rule.parameters.holdingCostRate || 0.20; // 20% annual holding cost
            const unitCost = await this.getItemUnitCost(rule.locationId, rule.itemId);
            
            const eoq = Math.sqrt((2 * annualDemand * orderingCost) / (holdingCostRate * unitCost));
            
            // Adjust for current stock and maximum stock level
            let optimalQuantity = Math.max(
                eoq - currentStock,
                rule.parameters.reorderQuantity || eoq
            );
            
            // Don't exceed maximum stock level
            if (rule.parameters.maxStock) {
                optimalQuantity = Math.min(optimalQuantity, rule.parameters.maxStock - currentStock);
            }
            
            // Apply seasonal adjustments
            if (rule.parameters.seasonalAdjustment) {
                const seasonalFactor = await this.getSeasonalFactor(rule.locationId, rule.itemId);
                optimalQuantity = Math.round(optimalQuantity * seasonalFactor);
            }
            
            return Math.max(optimalQuantity, 1);
        } catch (error) {
            this.logger.error('Failed to calculate optimal order quantity', { error: error.message });
            return rule.parameters.reorderQuantity || 10; // Fallback quantity
        }
    }

    async triggerReorder(ruleId, overrideQuantity = null) {
        try {
            const rule = this.reorderRules.get(ruleId) || 
                JSON.parse(await this.redis.hget('reorder_rules', ruleId));
            
            if (!rule) {
                throw new Error(`Reorder rule ${ruleId} not found`);
            }
            
            const currentStock = await this.getCurrentStockLevel(rule.locationId, rule.itemId);
            const recommendedQuantity = overrideQuantity || 
                await this.calculateOptimalOrderQuantity(rule, currentStock);
            
            const reorder = {
                id: uuidv4(),
                ruleId,
                locationId: rule.locationId,
                itemId: rule.itemId,
                currentStock,
                requestedQuantity: recommendedQuantity,
                estimatedCost: recommendedQuantity * await this.getItemUnitCost(rule.locationId, rule.itemId),
                suppliers: await this.selectOptimalSuppliers(rule, recommendedQuantity),
                status: 'pending',
                priority: this.calculatePriority(rule, currentStock),
                createdAt: new Date(),
                approvalStatus: rule.approval.required ? 'pending_approval' : 'auto_approved',
                metadata: {
                    triggerReason: 'automated_reorder',
                    forecastData: await this.getDemandForecast(rule.locationId, rule.itemId),
                    seasonalFactor: await this.getSeasonalFactor(rule.locationId, rule.itemId)
                }
            };
            
            this.pendingReorders.set(reorder.id, reorder);
            await this.redis.hset('pending_reorders', reorder.id, JSON.stringify(reorder));
            
            // Update rule statistics
            rule.lastTriggered = new Date();
            rule.totalTriggers++;
            this.reorderRules.set(ruleId, rule);
            await this.redis.hset('reorder_rules', ruleId, JSON.stringify(rule));
            
            this.logger.info('Reorder triggered', { 
                reorderId: reorder.id, 
                itemId: rule.itemId, 
                quantity: recommendedQuantity 
            });
            
            this.io.to(`location_${rule.locationId}`).emit('reorder_triggered', {
                reorderId: reorder.id,
                itemId: rule.itemId,
                quantity: recommendedQuantity,
                estimatedCost: reorder.estimatedCost,
                priority: reorder.priority
            });
            
            this.emit('reorder_triggered', reorder);
            
            // Auto-process if approval not required or under auto-approval threshold
            if (!rule.approval.required || reorder.estimatedCost < rule.approval.autoApproveBelow) {
                await this.processReorder(reorder.id);
            } else {
                await this.requestApproval(reorder);
            }
            
            return { success: true, reorderId: reorder.id, reorder: this.sanitizeReorderData(reorder) };
        } catch (error) {
            this.logger.error('Failed to trigger reorder', { error: error.message, ruleId });
            throw new Error(`Reorder trigger failed: ${error.message}`);
        }
    }

    async processReorder(reorderId) {
        try {
            const reorder = this.pendingReorders.get(reorderId) || 
                JSON.parse(await this.redis.hget('pending_reorders', reorderId));
            
            if (!reorder) {
                throw new Error(`Reorder ${reorderId} not found`);
            }
            
            if (reorder.approvalStatus === 'pending_approval') {
                throw new Error(`Reorder ${reorderId} requires approval`);
            }
            
            // Create purchase orders for each supplier
            const purchaseOrders = [];
            
            for (const supplierAllocation of reorder.suppliers) {
                const orderData = {
                    supplierId: supplierAllocation.supplierId,
                    locationId: reorder.locationId,
                    items: [{
                        sku: reorder.itemId,
                        name: await this.getItemName(reorder.itemId),
                        quantity: supplierAllocation.quantity,
                        unitCost: supplierAllocation.unitCost,
                        expectedDeliveryDate: moment().add(supplierAllocation.leadTimeDays, 'days').toDate()
                    }],
                    expectedDeliveryDate: moment().add(supplierAllocation.leadTimeDays, 'days').toDate(),
                    createdBy: 'reorder_automation',
                    notes: `Automated reorder - Rule: ${reorder.ruleId}`,
                    metadata: {
                        reorderId: reorder.id,
                        ruleId: reorder.ruleId,
                        automationTriggered: true
                    }
                };
                
                // Create purchase order (assuming we have access to supply chain tracker)
                const purchaseOrder = await this.createPurchaseOrder(orderData);
                purchaseOrders.push(purchaseOrder);
            }
            
            reorder.status = 'processed';
            reorder.purchaseOrders = purchaseOrders.map(po => po.orderId);
            reorder.processedAt = new Date();
            
            this.pendingReorders.set(reorderId, reorder);
            await this.redis.hset('pending_reorders', reorderId, JSON.stringify(reorder));
            
            // Update rule performance
            const rule = this.reorderRules.get(reorder.ruleId);
            if (rule) {
                rule.performance.totalOrders++;
                rule.performance.averageOrderValue = 
                    ((rule.performance.averageOrderValue * (rule.performance.totalOrders - 1)) + 
                     reorder.estimatedCost) / rule.performance.totalOrders;
                
                this.reorderRules.set(reorder.ruleId, rule);
                await this.redis.hset('reorder_rules', reorder.ruleId, JSON.stringify(rule));
            }
            
            this.logger.info('Reorder processed successfully', { 
                reorderId, 
                purchaseOrders: purchaseOrders.length 
            });
            
            this.io.to(`location_${reorder.locationId}`).emit('reorder_processed', {
                reorderId,
                purchaseOrders: purchaseOrders.length,
                totalValue: reorder.estimatedCost
            });
            
            return { success: true, purchaseOrders };
        } catch (error) {
            this.logger.error('Failed to process reorder', { error: error.message, reorderId });
            throw error;
        }
    }

    async analyzeDemandPatterns(locationId, itemId, timeframeDays = 90) {
        try {
            const endDate = new Date();
            const startDate = moment(endDate).subtract(timeframeDays, 'days').toDate();
            
            const salesHistory = await this.getSalesHistory(locationId, itemId, startDate, endDate);
            
            if (salesHistory.length === 0) {
                return {
                    dailyAverage: 0,
                    trend: 'stable',
                    seasonality: 'none',
                    volatility: 'low'
                };
            }
            
            // Calculate daily averages
            const dailySales = this.aggregateDailySales(salesHistory);
            const dailyAverage = dailySales.reduce((sum, day) => sum + day.quantity, 0) / dailySales.length;
            
            // Trend analysis
            const trend = this.calculateTrend(dailySales);
            
            // Seasonality detection
            const seasonality = this.detectSeasonality(dailySales);
            
            // Volatility calculation
            const volatility = this.calculateVolatility(dailySales, dailyAverage);
            
            const analysis = {
                dailyAverage,
                trend,
                seasonality,
                volatility,
                confidence: this.calculateConfidence(salesHistory.length, volatility),
                lastUpdated: new Date()
            };
            
            // Store forecast for future use
            this.demandForecasts.set(`${locationId}:${itemId}`, analysis);
            await this.redis.hset('demand_forecasts', `${locationId}:${itemId}`, JSON.stringify(analysis));
            
            return analysis;
        } catch (error) {
            this.logger.error('Failed to analyze demand patterns', { error: error.message, locationId, itemId });
            throw error;
        }
    }

    async selectOptimalSuppliers(rule, requestedQuantity) {
        try {
            // Get available suppliers for this item
            const availableSuppliers = await this.getSuppliersForItem(rule.itemId);
            
            if (availableSuppliers.length === 0) {
                throw new Error(`No suppliers found for item ${rule.itemId}`);
            }
            
            // Score suppliers based on multiple criteria
            const supplierScores = availableSuppliers.map(supplier => ({
                ...supplier,
                score: this.calculateSupplierScore(supplier, requestedQuantity)
            }));
            
            // Sort by score (highest first)
            supplierScores.sort((a, b) => b.score - a.score);
            
            // Allocate quantity among top suppliers (diversification strategy)
            const allocations = [];
            let remainingQuantity = requestedQuantity;
            
            // Allocate to primary supplier (70% if possible)
            const primarySupplier = supplierScores[0];
            const primaryQuantity = Math.min(
                Math.ceil(requestedQuantity * 0.7),
                primarySupplier.maxOrderQuantity || requestedQuantity,
                remainingQuantity
            );
            
            if (primaryQuantity > 0) {
                allocations.push({
                    supplierId: primarySupplier.id,
                    quantity: primaryQuantity,
                    unitCost: primarySupplier.unitCost,
                    leadTimeDays: primarySupplier.leadTimeDays,
                    reliability: primarySupplier.performance.onTimeDeliveryRate
                });
                remainingQuantity -= primaryQuantity;
            }
            
            // Allocate remaining to secondary suppliers
            for (let i = 1; i < supplierScores.length && remainingQuantity > 0; i++) {
                const supplier = supplierScores[i];
                const allocationQuantity = Math.min(
                    remainingQuantity,
                    supplier.maxOrderQuantity || remainingQuantity
                );
                
                if (allocationQuantity > 0 && 
                    (!supplier.minimumOrderQuantity || allocationQuantity >= supplier.minimumOrderQuantity)) {
                    allocations.push({
                        supplierId: supplier.id,
                        quantity: allocationQuantity,
                        unitCost: supplier.unitCost,
                        leadTimeDays: supplier.leadTimeDays,
                        reliability: supplier.performance.onTimeDeliveryRate
                    });
                    remainingQuantity -= allocationQuantity;
                }
            }
            
            if (remainingQuantity > 0) {
                this.logger.warn('Could not fully allocate order quantity to suppliers', {
                    itemId: rule.itemId,
                    requestedQuantity,
                    remainingQuantity
                });
            }
            
            return allocations;
        } catch (error) {
            this.logger.error('Failed to select optimal suppliers', { error: error.message });
            throw error;
        }
    }

    calculateSupplierScore(supplier, requestedQuantity) {
        let score = 0;
        
        // On-time delivery rate (40% weight)
        score += (supplier.performance.onTimeDeliveryRate / 100) * 40;
        
        // Quality score (25% weight)
        score += (supplier.performance.qualityScore / 100) * 25;
        
        // Cost competitiveness (20% weight)
        const costScore = Math.max(0, 100 - supplier.unitCost); // Simple inverse cost scoring
        score += (costScore / 100) * 20;
        
        // Lead time (10% weight)
        const leadTimeScore = Math.max(0, 30 - supplier.leadTimeDays) / 30 * 100;
        score += (leadTimeScore / 100) * 10;
        
        // Capacity availability (5% weight)
        if (supplier.maxOrderQuantity && supplier.maxOrderQuantity >= requestedQuantity) {
            score += 5;
        }
        
        return Math.round(score * 100) / 100;
    }

    startAutomationEngine() {
        // Check inventory levels every 15 minutes
        setInterval(async () => {
            try {
                await this.runAutomationCycle();
            } catch (error) {
                this.logger.error('Automation engine error', { error: error.message });
            }
        }, 15 * 60 * 1000);
    }

    startDemandAnalysis() {
        // Update demand forecasts every 6 hours
        setInterval(async () => {
            try {
                await this.updateDemandForecasts();
            } catch (error) {
                this.logger.error('Demand analysis error', { error: error.message });
            }
        }, 6 * 60 * 60 * 1000);
    }

    async runAutomationCycle() {
        const activeRules = Array.from(this.reorderRules.values())
            .filter(rule => rule.status === 'active');
        
        for (const rule of activeRules) {
            try {
                const alerts = await this.checkInventoryLevels(rule.locationId, rule.itemId);
                
                for (const alert of alerts) {
                    if (alert.ruleId === rule.id) {
                        await this.triggerReorder(rule.id);
                    }
                }
            } catch (error) {
                this.logger.error('Rule processing error', { 
                    error: error.message, 
                    ruleId: rule.id 
                });
            }
        }
    }

    // Helper methods
    async getCurrentStockLevel(locationId, itemId) {
        const stockData = await this.redis.hget(`current_stock:${locationId}`, itemId);
        return stockData ? parseInt(stockData) : 0;
    }

    async getRulesForItem(locationId, itemId) {
        return Array.from(this.reorderRules.values())
            .filter(rule => rule.locationId === locationId && rule.itemId === itemId);
    }

    isWithinActiveHours(now, conditions) {
        const currentHour = now.getHours();
        const currentDay = now.getDay(); // 0 = Sunday
        
        const startHour = parseInt(conditions.activeHours.start.split(':')[0]);
        const endHour = parseInt(conditions.activeHours.end.split(':')[0]);
        
        return conditions.activeDays.includes(currentDay) && 
               currentHour >= startHour && 
               currentHour <= endHour;
    }

    calculatePriority(rule, currentStock) {
        const stockRatio = currentStock / rule.parameters.reorderPoint;
        
        if (stockRatio <= 0.1) return 'critical';
        if (stockRatio <= 0.3) return 'high';
        if (stockRatio <= 0.6) return 'medium';
        return 'low';
    }

    sanitizeRuleData(rule) {
        return rule;
    }

    sanitizeReorderData(reorder) {
        return reorder;
    }

    handleLowStockAlert(data) {
        this.logger.info('Low stock alert triggered', {
            locationId: data.locationId,
            itemId: data.itemId,
            currentStock: data.currentStock
        });
    }

    handleReorderTriggered(reorder) {
        this.logger.info('Reorder triggered successfully', {
            reorderId: reorder.id,
            itemId: reorder.itemId,
            quantity: reorder.requestedQuantity
        });
    }

    handleSeasonalDemand(data) {
        this.logger.info('Seasonal demand pattern detected', data);
    }

    handleLeadTimeChange(data) {
        this.logger.info('Supplier lead time changed', data);
    }
}

module.exports = ReorderAutomationManager;