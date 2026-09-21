const { v4: uuidv4 } = require('uuid');
const logger = require('../config/logger');
const redis = require('../config/redis');
const EventEmitter = require('events');

class RealTimeInventoryTracker extends EventEmitter {
    constructor(socketIO) {
        super();
        this.io = socketIO;
        this.redis = redis.client;
        this.locationStockLevels = new Map();
        this.stockMovements = new Map();
        this.alertThresholds = new Map();
        this.realtimeSubscribers = new Map();
        
        this.setupEventHandlers();
        this.startStockMonitoring();
    }

    setupEventHandlers() {
        // Listen for database changes
        this.on('stock_level_changed', this.handleStockLevelChange.bind(this));
        this.on('low_stock_alert', this.handleLowStockAlert.bind(this));
        this.on('out_of_stock_alert', this.handleOutOfStockAlert.bind(this));
        this.on('stock_movement', this.handleStockMovement.bind(this));
        this.on('reservation_created', this.handleReservationCreated.bind(this));
        this.on('reservation_expired', this.handleReservationExpired.bind(this));
    }

    async trackInventoryChange(locationId, itemId, changeData) {
        const trackingId = uuidv4();
        const timestamp = new Date();

        try {
            const inventoryKey = `inventory:${locationId}:${itemId}`;
            const movementKey = `movement:${locationId}:${itemId}:${trackingId}`;
            
            // Get current stock level
            const currentStock = await this.redis.hget(inventoryKey, 'quantity') || 0;
            const parsedCurrentStock = parseInt(currentStock, 10);
            
            // Calculate new stock level
            const newQuantity = this.calculateNewQuantity(parsedCurrentStock, changeData);
            
            // Create movement record
            const movement = {
                trackingId,
                locationId,
                itemId,
                changeType: changeData.changeType,
                previousQuantity: parsedCurrentStock,
                newQuantity,
                quantityChanged: newQuantity - parsedCurrentStock,
                reason: changeData.reason || 'manual_adjustment',
                userId: changeData.userId,
                transactionId: changeData.transactionId,
                timestamp: timestamp.toISOString(),
                metadata: changeData.metadata || {}
            };

            // Store movement in Redis for real-time tracking
            await this.redis.hset(movementKey, movement);
            await this.redis.expire(movementKey, 86400 * 30); // 30 days

            // Update current stock level
            await this.redis.hmset(inventoryKey, {
                quantity: newQuantity,
                lastUpdated: timestamp.toISOString(),
                lastMovementId: trackingId
            });

            // Update in-memory cache
            this.updateLocationStockLevel(locationId, itemId, newQuantity);

            // Check for alerts
            await this.checkStockAlerts(locationId, itemId, newQuantity);

            // Emit real-time updates
            this.emitInventoryUpdate(locationId, itemId, movement);

            // Log the change
            logger.logInventoryEvent('stock_change', locationId, changeData.userId || 'system', {
                trackingId,
                itemId,
                changeType: changeData.changeType,
                previousQuantity: parsedCurrentStock,
                newQuantity,
                reason: changeData.reason
            });

            return {
                trackingId,
                locationId,
                itemId,
                previousQuantity: parsedCurrentStock,
                newQuantity,
                movement
            };

        } catch (error) {
            logger.error('Failed to track inventory change', {
                locationId,
                itemId,
                changeData,
                error: error.message,
                stack: error.stack
            });
            throw error;
        }
    }

    calculateNewQuantity(currentQuantity, changeData) {
        switch (changeData.changeType) {
            case 'increase':
            case 'restock':
            case 'return':
                return currentQuantity + (changeData.quantity || changeData.quantityChanged || 0);
            
            case 'decrease':
            case 'sale':
            case 'damage':
            case 'theft':
                return Math.max(0, currentQuantity - (changeData.quantity || changeData.quantityChanged || 0));
            
            case 'adjustment':
            case 'set':
                return changeData.newQuantity || changeData.quantity || 0;
            
            case 'transfer_out':
                return Math.max(0, currentQuantity - (changeData.quantity || 0));
            
            case 'transfer_in':
                return currentQuantity + (changeData.quantity || 0);
            
            default:
                if (changeData.newQuantity !== undefined) {
                    return changeData.newQuantity;
                }
                return currentQuantity;
        }
    }

    updateLocationStockLevel(locationId, itemId, newQuantity) {
        if (!this.locationStockLevels.has(locationId)) {
            this.locationStockLevels.set(locationId, new Map());
        }
        
        this.locationStockLevels.get(locationId).set(itemId, {
            quantity: newQuantity,
            lastUpdated: new Date(),
            alerts: []
        });
    }

    async checkStockAlerts(locationId, itemId, currentQuantity) {
        const alertKey = `alerts:${locationId}:${itemId}`;
        const thresholds = await this.getAlertThresholds(locationId, itemId);
        
        const alerts = [];

        // Check for out of stock
        if (currentQuantity === 0) {
            alerts.push({
                type: 'out_of_stock',
                severity: 'critical',
                message: `Item ${itemId} is out of stock at location ${locationId}`,
                threshold: 0,
                currentQuantity,
                timestamp: new Date().toISOString()
            });
            
            this.emit('out_of_stock_alert', {
                locationId,
                itemId,
                currentQuantity,
                timestamp: new Date()
            });
        }
        
        // Check for low stock
        else if (thresholds.lowStockThreshold && currentQuantity <= thresholds.lowStockThreshold) {
            alerts.push({
                type: 'low_stock',
                severity: 'warning',
                message: `Item ${itemId} is low in stock at location ${locationId}`,
                threshold: thresholds.lowStockThreshold,
                currentQuantity,
                timestamp: new Date().toISOString()
            });
            
            this.emit('low_stock_alert', {
                locationId,
                itemId,
                currentQuantity,
                threshold: thresholds.lowStockThreshold,
                timestamp: new Date()
            });
        }

        // Check for critical stock level
        if (thresholds.criticalStockThreshold && currentQuantity <= thresholds.criticalStockThreshold) {
            alerts.push({
                type: 'critical_stock',
                severity: 'high',
                message: `Item ${itemId} has reached critical stock level at location ${locationId}`,
                threshold: thresholds.criticalStockThreshold,
                currentQuantity,
                timestamp: new Date().toISOString()
            });
        }

        // Check for overstock
        if (thresholds.maxStockThreshold && currentQuantity >= thresholds.maxStockThreshold) {
            alerts.push({
                type: 'overstock',
                severity: 'info',
                message: `Item ${itemId} is overstocked at location ${locationId}`,
                threshold: thresholds.maxStockThreshold,
                currentQuantity,
                timestamp: new Date().toISOString()
            });
        }

        // Store alerts in Redis if any
        if (alerts.length > 0) {
            await this.redis.setex(alertKey, 3600, JSON.stringify(alerts)); // 1 hour expiry
            
            // Update in-memory cache
            if (this.locationStockLevels.has(locationId)) {
                const locationStock = this.locationStockLevels.get(locationId);
                if (locationStock.has(itemId)) {
                    locationStock.get(itemId).alerts = alerts;
                }
            }
        }

        return alerts;
    }

    async getAlertThresholds(locationId, itemId) {
        const thresholdKey = `thresholds:${locationId}:${itemId}`;
        const cached = await this.redis.hgetall(thresholdKey);
        
        if (Object.keys(cached).length > 0) {
            return {
                lowStockThreshold: parseInt(cached.lowStockThreshold) || 10,
                criticalStockThreshold: parseInt(cached.criticalStockThreshold) || 5,
                maxStockThreshold: parseInt(cached.maxStockThreshold) || 1000
            };
        }
        
        // Default thresholds
        return {
            lowStockThreshold: 10,
            criticalStockThreshold: 5,
            maxStockThreshold: 1000
        };
    }

    emitInventoryUpdate(locationId, itemId, movement) {
        const updateData = {
            locationId,
            itemId,
            movement,
            timestamp: new Date().toISOString()
        };

        // Emit to location-specific room
        this.io.to(`inventory:${locationId}`).emit('inventory_updated', updateData);
        
        // Emit to global inventory room
        this.io.to('inventory:all').emit('inventory_updated', updateData);
        
        // Emit to item-specific subscribers
        this.io.to(`item:${itemId}`).emit('item_updated', updateData);
        
        // Emit stock level change event
        this.emit('stock_level_changed', updateData);
    }

    async getRealtimeStockLevel(locationId, itemId) {
        try {
            const inventoryKey = `inventory:${locationId}:${itemId}`;
            const stockData = await this.redis.hgetall(inventoryKey);
            
            if (Object.keys(stockData).length === 0) {
                return {
                    locationId,
                    itemId,
                    quantity: 0,
                    lastUpdated: null,
                    alerts: [],
                    status: 'not_tracked'
                };
            }

            // Get current alerts
            const alertKey = `alerts:${locationId}:${itemId}`;
            const alertsData = await this.redis.get(alertKey);
            const alerts = alertsData ? JSON.parse(alertsData) : [];

            return {
                locationId,
                itemId,
                quantity: parseInt(stockData.quantity) || 0,
                lastUpdated: stockData.lastUpdated,
                lastMovementId: stockData.lastMovementId,
                alerts,
                status: 'tracked'
            };

        } catch (error) {
            logger.error('Failed to get realtime stock level', {
                locationId,
                itemId,
                error: error.message
            });
            throw error;
        }
    }

    async getLocationInventorySnapshot(locationId) {
        try {
            const pattern = `inventory:${locationId}:*`;
            const keys = await this.redis.keys(pattern);
            
            const snapshot = {
                locationId,
                timestamp: new Date().toISOString(),
                items: [],
                totalItems: 0,
                totalValue: 0,
                alerts: []
            };

            for (const key of keys) {
                const itemId = key.split(':')[2];
                const stockLevel = await this.getRealtimeStockLevel(locationId, itemId);
                
                if (stockLevel.status === 'tracked') {
                    snapshot.items.push(stockLevel);
                    snapshot.totalItems += stockLevel.quantity;
                    
                    // Add alerts to summary
                    snapshot.alerts = snapshot.alerts.concat(stockLevel.alerts.map(alert => ({
                        ...alert,
                        itemId
                    })));
                }
            }

            // Sort alerts by severity
            snapshot.alerts.sort((a, b) => {
                const severityOrder = { critical: 0, high: 1, warning: 2, info: 3 };
                return severityOrder[a.severity] - severityOrder[b.severity];
            });

            return snapshot;

        } catch (error) {
            logger.error('Failed to get location inventory snapshot', {
                locationId,
                error: error.message
            });
            throw error;
        }
    }

    async getStockMovementHistory(locationId, itemId, options = {}) {
        try {
            const {
                startDate = new Date(Date.now() - 24 * 60 * 60 * 1000), // 24 hours ago
                endDate = new Date(),
                limit = 100,
                changeType = null
            } = options;

            const pattern = `movement:${locationId}:${itemId}:*`;
            const keys = await this.redis.keys(pattern);
            
            const movements = [];
            
            for (const key of keys) {
                const movement = await this.redis.hgetall(key);
                
                if (Object.keys(movement).length > 0) {
                    const movementDate = new Date(movement.timestamp);
                    
                    // Filter by date range
                    if (movementDate >= startDate && movementDate <= endDate) {
                        // Filter by change type if specified
                        if (!changeType || movement.changeType === changeType) {
                            movements.push({
                                ...movement,
                                previousQuantity: parseInt(movement.previousQuantity),
                                newQuantity: parseInt(movement.newQuantity),
                                quantityChanged: parseInt(movement.quantityChanged),
                                metadata: movement.metadata ? JSON.parse(movement.metadata) : {}
                            });
                        }
                    }
                }
            }

            // Sort by timestamp (most recent first)
            movements.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

            // Apply limit
            return movements.slice(0, limit);

        } catch (error) {
            logger.error('Failed to get stock movement history', {
                locationId,
                itemId,
                error: error.message
            });
            throw error;
        }
    }

    async subscribeToRealtimeUpdates(socketId, subscriptions) {
        try {
            const subscriptionData = {
                socketId,
                subscriptions, // { locations: [], items: [], alertTypes: [] }
                subscribedAt: new Date().toISOString()
            };

            this.realtimeSubscribers.set(socketId, subscriptionData);

            // Join appropriate Socket.IO rooms
            const socket = this.io.sockets.sockets.get(socketId);
            if (socket) {
                // Subscribe to location updates
                for (const locationId of subscriptions.locations || []) {
                    socket.join(`inventory:${locationId}`);
                    socket.join(`alerts:${locationId}`);
                }

                // Subscribe to item updates
                for (const itemId of subscriptions.items || []) {
                    socket.join(`item:${itemId}`);
                }

                // Subscribe to global updates if requested
                if (subscriptions.global) {
                    socket.join('inventory:all');
                    socket.join('alerts:all');
                }
            }

            logger.logInventoryEvent('realtime_subscription', 'system', socketId, {
                subscriptions
            });

            return subscriptionData;

        } catch (error) {
            logger.error('Failed to subscribe to realtime updates', {
                socketId,
                subscriptions,
                error: error.message
            });
            throw error;
        }
    }

    unsubscribeFromRealtimeUpdates(socketId) {
        this.realtimeSubscribers.delete(socketId);
        logger.logInventoryEvent('realtime_unsubscription', 'system', socketId);
    }

    // Event handlers
    handleStockLevelChange(data) {
        logger.logInventoryEvent('stock_level_changed', data.locationId, 'tracker', {
            itemId: data.itemId,
            movement: data.movement
        });
    }

    handleLowStockAlert(data) {
        // Emit to alerts room
        this.io.to(`alerts:${data.locationId}`).emit('low_stock_alert', {
            type: 'low_stock',
            locationId: data.locationId,
            itemId: data.itemId,
            currentQuantity: data.currentQuantity,
            threshold: data.threshold,
            timestamp: data.timestamp.toISOString(),
            severity: 'warning'
        });

        // Emit to global alerts room
        this.io.to('alerts:all').emit('stock_alert', {
            type: 'low_stock',
            locationId: data.locationId,
            itemId: data.itemId,
            currentQuantity: data.currentQuantity,
            threshold: data.threshold,
            timestamp: data.timestamp.toISOString(),
            severity: 'warning'
        });

        logger.logInventoryEvent('low_stock_alert', data.locationId, 'tracker', {
            itemId: data.itemId,
            currentQuantity: data.currentQuantity,
            threshold: data.threshold
        });
    }

    handleOutOfStockAlert(data) {
        // Emit to alerts room
        this.io.to(`alerts:${data.locationId}`).emit('out_of_stock_alert', {
            type: 'out_of_stock',
            locationId: data.locationId,
            itemId: data.itemId,
            timestamp: data.timestamp.toISOString(),
            severity: 'critical'
        });

        // Emit to global alerts room
        this.io.to('alerts:all').emit('stock_alert', {
            type: 'out_of_stock',
            locationId: data.locationId,
            itemId: data.itemId,
            timestamp: data.timestamp.toISOString(),
            severity: 'critical'
        });

        logger.logInventoryEvent('out_of_stock_alert', data.locationId, 'tracker', {
            itemId: data.itemId
        });
    }

    handleStockMovement(data) {
        // This can be used for analytics and reporting
        logger.logInventoryEvent('stock_movement', data.locationId, data.userId || 'system', {
            itemId: data.itemId,
            changeType: data.changeType,
            quantity: data.quantity
        });
    }

    handleReservationCreated(data) {
        // Update available quantity for real-time tracking
        this.trackInventoryChange(data.locationId, data.itemId, {
            changeType: 'reservation',
            quantity: data.quantity,
            reason: 'item_reserved',
            userId: data.customerId,
            transactionId: data.reservationId,
            metadata: {
                reservationId: data.reservationId,
                expiresAt: data.expiresAt
            }
        });
    }

    handleReservationExpired(data) {
        // Release reserved quantity back to available stock
        this.trackInventoryChange(data.locationId, data.itemId, {
            changeType: 'release_reservation',
            quantity: data.quantity,
            reason: 'reservation_expired',
            userId: 'system',
            transactionId: data.reservationId,
            metadata: {
                reservationId: data.reservationId,
                expiredAt: data.expiredAt
            }
        });
    }

    startStockMonitoring() {
        // Monitor stock levels every 30 seconds for any anomalies
        setInterval(async () => {
            try {
                await this.performStockAnomalyDetection();
            } catch (error) {
                logger.error('Stock anomaly detection failed', error);
            }
        }, 30000);

        logger.info('Real-time stock monitoring started');
    }

    async performStockAnomalyDetection() {
        // This is a placeholder for more advanced anomaly detection
        // Could include:
        // - Detecting unusual stock movements
        // - Identifying potential inventory discrepancies
        // - Monitoring for suspicious patterns
        
        const locations = await this.redis.keys('inventory:*');
        const anomalies = [];

        // For now, just log the monitoring activity
        logger.debug('Performing stock anomaly detection', {
            locationsMonitored: locations.length,
            timestamp: new Date().toISOString()
        });

        return anomalies;
    }

    async getRealtimeMetrics() {
        const metrics = {
            activeSubscribers: this.realtimeSubscribers.size,
            locationsTracked: this.locationStockLevels.size,
            totalItemsTracked: 0,
            alertsGenerated: 0,
            timestamp: new Date().toISOString()
        };

        // Count total items tracked
        for (const [locationId, items] of this.locationStockLevels) {
            metrics.totalItemsTracked += items.size;
            
            // Count alerts
            for (const [itemId, stockInfo] of items) {
                metrics.alertsGenerated += stockInfo.alerts.length;
            }
        }

        return metrics;
    }
}

module.exports = RealTimeInventoryTracker;