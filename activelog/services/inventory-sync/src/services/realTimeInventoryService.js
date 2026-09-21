const logger = require('../config/logger');
const redis = require('../config/redis');
const { v4: uuidv4 } = require('uuid');

class RealTimeInventoryService {
  constructor() {
    this.updateQueue = new Map();
    this.batchSize = parseInt(process.env.INVENTORY_UPDATE_BATCH_SIZE) || 100;
    this.debounceMs = parseInt(process.env.SYNC_DEBOUNCE_MS) || 1000;
    this.subscribers = new Map();
    
    // Initialize batch processing
    this.initializeBatchProcessor();
  }

  /**
   * Initialize batch processor for inventory updates
   */
  initializeBatchProcessor() {
    setInterval(() => {
      this.processBatchUpdates();
    }, this.debounceMs);
  }

  /**
   * Track real-time inventory change
   */
  async trackInventoryChange(locationId, itemId, changeData) {
    try {
      const updateId = uuidv4();
      const timestamp = new Date().toISOString();
      
      const update = {
        updateId,
        locationId,
        itemId,
        changeType: changeData.changeType, // 'stock_increase', 'stock_decrease', 'reservation', 'sale', etc.
        oldQuantity: changeData.oldQuantity,
        newQuantity: changeData.newQuantity,
        quantityDelta: changeData.newQuantity - changeData.oldQuantity,
        reason: changeData.reason,
        userId: changeData.userId,
        transactionId: changeData.transactionId,
        metadata: changeData.metadata || {},
        timestamp
      };

      // Add to update queue for batch processing
      const queueKey = `${locationId}:${itemId}`;
      if (!this.updateQueue.has(queueKey)) {
        this.updateQueue.set(queueKey, []);
      }
      this.updateQueue.get(queueKey).push(update);

      // Publish real-time update immediately
      await this.publishUpdate(locationId, update);

      // Update cache
      await this.updateInventoryCache(locationId, itemId, update);

      // Check for low stock alerts
      await this.checkLowStockAlerts(locationId, itemId, update.newQuantity);

      logger.logInventoryEvent('real_time_update', locationId, itemId, {
        changeType: update.changeType,
        quantityDelta: update.quantityDelta,
        newQuantity: update.newQuantity
      });

      return update;
    } catch (error) {
      logger.error('Error tracking inventory change:', error);
      throw error;
    }
  }

  /**
   * Publish real-time update to subscribers
   */
  async publishUpdate(locationId, update) {
    try {
      // Publish to Redis pub/sub for cross-service communication
      await redis.publishInventoryUpdate(locationId, update);
      
      // Publish to WebSocket subscribers if available
      if (this.socketIO) {
        const room = `inventory:${locationId}`;
        this.socketIO.to(room).emit('inventory_update', update);
        
        // Also publish to global inventory room
        this.socketIO.to('inventory:all').emit('inventory_update', update);
      }

      return true;
    } catch (error) {
      logger.error('Error publishing inventory update:', error);
      return false;
    }
  }

  /**
   * Update inventory cache with latest data
   */
  async updateInventoryCache(locationId, itemId, update) {
    try {
      // Get current cached data
      let cachedItem = await redis.getInventoryItem(locationId, itemId);
      
      if (!cachedItem) {
        // Create new cache entry
        cachedItem = {
          locationId,
          itemId,
          quantity: update.newQuantity,
          lastUpdated: update.timestamp,
          recentChanges: []
        };
      } else {
        // Update existing cache
        cachedItem.quantity = update.newQuantity;
        cachedItem.lastUpdated = update.timestamp;
      }

      // Add to recent changes (keep last 10)
      cachedItem.recentChanges.unshift({
        changeType: update.changeType,
        quantityDelta: update.quantityDelta,
        reason: update.reason,
        timestamp: update.timestamp
      });
      
      if (cachedItem.recentChanges.length > 10) {
        cachedItem.recentChanges = cachedItem.recentChanges.slice(0, 10);
      }

      // Cache with 1 hour TTL
      await redis.cacheInventoryItem(locationId, itemId, cachedItem, 3600);

      return cachedItem;
    } catch (error) {
      logger.error('Error updating inventory cache:', error);
      return null;
    }
  }

  /**
   * Check for low stock alerts and trigger notifications
   */
  async checkLowStockAlerts(locationId, itemId, currentQuantity) {
    try {
      const lowStockThreshold = parseInt(process.env.LOW_STOCK_THRESHOLD) || 10;
      const criticalStockThreshold = parseInt(process.env.CRITICAL_STOCK_THRESHOLD) || 5;

      if (currentQuantity <= criticalStockThreshold) {
        await this.triggerStockAlert(locationId, itemId, 'critical', currentQuantity);
        
        // Auto-trigger reorder if enabled
        if (process.env.AUTO_REORDER_ENABLED === 'true') {
          await this.triggerAutoReorder(locationId, itemId, 'critical');
        }
      } else if (currentQuantity <= lowStockThreshold) {
        await this.triggerStockAlert(locationId, itemId, 'low', currentQuantity);
        
        if (process.env.AUTO_REORDER_ENABLED === 'true') {
          await this.triggerAutoReorder(locationId, itemId, 'normal');
        }
      }

      return true;
    } catch (error) {
      logger.error('Error checking low stock alerts:', error);
      return false;
    }
  }

  /**
   * Trigger stock alert
   */
  async triggerStockAlert(locationId, itemId, severity, currentQuantity) {
    try {
      const alert = {
        alertId: uuidv4(),
        type: 'stock_alert',
        severity,
        locationId,
        itemId,
        currentQuantity,
        timestamp: new Date().toISOString(),
        acknowledged: false
      };

      // Publish alert
      if (this.socketIO) {
        this.socketIO.to(`alerts:${locationId}`).emit('stock_alert', alert);
      }

      // Store alert for later retrieval
      await redis.client?.setEx(
        `alert:${alert.alertId}`,
        86400, // 24 hours
        JSON.stringify(alert)
      );

      logger.logInventoryEvent('stock_alert_triggered', locationId, itemId, {
        severity,
        currentQuantity,
        alertId: alert.alertId
      });

      return alert;
    } catch (error) {
      logger.error('Error triggering stock alert:', error);
      return null;
    }
  }

  /**
   * Trigger auto-reorder
   */
  async triggerAutoReorder(locationId, itemId, priority) {
    try {
      await redis.setReorderFlag(itemId, locationId, priority);
      
      logger.logInventoryEvent('auto_reorder_triggered', locationId, itemId, {
        priority,
        timestamp: new Date().toISOString()
      });

      return true;
    } catch (error) {
      logger.error('Error triggering auto-reorder:', error);
      return false;
    }
  }

  /**
   * Process batch updates to database
   */
  async processBatchUpdates() {
    if (this.updateQueue.size === 0) return;

    try {
      const batchUpdates = [];
      const processedKeys = [];

      // Collect updates from queue
      for (const [queueKey, updates] of this.updateQueue.entries()) {
        if (updates.length === 0) continue;

        // Take up to batchSize updates
        const batch = updates.splice(0, this.batchSize);
        batchUpdates.push(...batch);
        
        if (updates.length === 0) {
          processedKeys.push(queueKey);
        }
      }

      // Remove processed keys
      processedKeys.forEach(key => this.updateQueue.delete(key));

      if (batchUpdates.length === 0) return;

      // Process batch in database (would typically use MongoDB bulk operations)
      await this.processBatchInDatabase(batchUpdates);

      logger.logInventoryEvent('batch_processed', 'system', 'batch', {
        batchSize: batchUpdates.length,
        processedAt: new Date().toISOString()
      });

    } catch (error) {
      logger.error('Error processing batch updates:', error);
    }
  }

  /**
   * Process batch updates in database
   */
  async processBatchInDatabase(updates) {
    try {
      // Group updates by location and item for efficient processing
      const grouped = updates.reduce((acc, update) => {
        const key = `${update.locationId}:${update.itemId}`;
        if (!acc[key]) acc[key] = [];
        acc[key].push(update);
        return acc;
      }, {});

      // Process each group
      for (const [key, updateGroup] of Object.entries(grouped)) {
        const [locationId, itemId] = key.split(':');
        const latestUpdate = updateGroup[updateGroup.length - 1];
        
        // Update inventory record in database
        await this.updateInventoryInDatabase(locationId, itemId, latestUpdate, updateGroup);
      }

      return true;
    } catch (error) {
      logger.error('Error processing batch in database:', error);
      throw error;
    }
  }

  /**
   * Update inventory in database
   */
  async updateInventoryInDatabase(locationId, itemId, latestUpdate, updateHistory) {
    try {
      // This would typically update MongoDB documents
      // For now, we'll simulate the database operation
      
      const inventoryUpdate = {
        locationId,
        itemId,
        quantity: latestUpdate.newQuantity,
        lastUpdated: latestUpdate.timestamp,
        updateHistory: updateHistory.map(update => ({
          updateId: update.updateId,
          changeType: update.changeType,
          quantityDelta: update.quantityDelta,
          reason: update.reason,
          userId: update.userId,
          timestamp: update.timestamp
        }))
      };

      // Simulate database update
      logger.debug('Database inventory update', {
        locationId,
        itemId,
        newQuantity: latestUpdate.newQuantity,
        historyCount: updateHistory.length
      });

      return inventoryUpdate;
    } catch (error) {
      logger.error('Error updating inventory in database:', error);
      throw error;
    }
  }

  /**
   * Get real-time inventory status
   */
  async getInventoryStatus(locationId, itemId = null) {
    try {
      if (itemId) {
        // Get specific item
        const cachedItem = await redis.getInventoryItem(locationId, itemId);
        return cachedItem || { locationId, itemId, quantity: 0, status: 'not_found' };
      } else {
        // Get all items for location (this would typically query the database)
        const locationData = await redis.getLocationData(locationId);
        return {
          locationId,
          summary: locationData,
          timestamp: new Date().toISOString()
        };
      }
    } catch (error) {
      logger.error('Error getting inventory status:', error);
      throw error;
    }
  }

  /**
   * Subscribe to real-time inventory updates
   */
  async subscribeToUpdates(locationId, callback) {
    try {
      await redis.subscribeToInventoryUpdates(locationId, callback);
      
      // Track subscription
      if (!this.subscribers.has(locationId)) {
        this.subscribers.set(locationId, new Set());
      }
      this.subscribers.get(locationId).add(callback);

      logger.logInventoryEvent('subscription_created', locationId, 'system', {
        subscriberCount: this.subscribers.get(locationId).size
      });

      return true;
    } catch (error) {
      logger.error('Error subscribing to inventory updates:', error);
      return false;
    }
  }

  /**
   * Get inventory movement analytics
   */
  async getInventoryMovementAnalytics(locationId, itemId, timeframe = '24h') {
    try {
      const cachedItem = await redis.getInventoryItem(locationId, itemId);
      
      if (!cachedItem || !cachedItem.recentChanges) {
        return {
          locationId,
          itemId,
          timeframe,
          movements: [],
          summary: {
            totalChanges: 0,
            stockIncreases: 0,
            stockDecreases: 0,
            netChange: 0
          }
        };
      }

      const movements = cachedItem.recentChanges;
      const summary = movements.reduce((acc, change) => {
        acc.totalChanges++;
        if (change.quantityDelta > 0) {
          acc.stockIncreases++;
        } else if (change.quantityDelta < 0) {
          acc.stockDecreases++;
        }
        acc.netChange += change.quantityDelta;
        return acc;
      }, {
        totalChanges: 0,
        stockIncreases: 0,
        stockDecreases: 0,
        netChange: 0
      });

      return {
        locationId,
        itemId,
        timeframe,
        currentQuantity: cachedItem.quantity,
        movements,
        summary,
        lastUpdated: cachedItem.lastUpdated
      };
    } catch (error) {
      logger.error('Error getting inventory movement analytics:', error);
      throw error;
    }
  }

  /**
   * Set Socket.IO instance for real-time communication
   */
  setSocketIO(io) {
    this.socketIO = io;
  }

  /**
   * Bulk update inventory items
   */
  async bulkUpdateInventory(locationId, updates) {
    try {
      const results = [];
      
      for (const update of updates) {
        const result = await this.trackInventoryChange(locationId, update.itemId, {
          changeType: update.changeType || 'bulk_update',
          oldQuantity: update.oldQuantity || 0,
          newQuantity: update.newQuantity,
          reason: update.reason || 'bulk_operation',
          userId: update.userId || 'system',
          metadata: update.metadata || {}
        });
        
        results.push(result);
      }

      logger.logInventoryEvent('bulk_update_completed', locationId, 'bulk', {
        itemCount: updates.length,
        results: results.length
      });

      return results;
    } catch (error) {
      logger.error('Error in bulk inventory update:', error);
      throw error;
    }
  }

  /**
   * Get active reservations affecting inventory
   */
  async getActiveReservations(locationId, itemId) {
    try {
      // This would typically query active reservations from database
      const reservations = [];
      
      // For now, return empty array - would be implemented with actual reservation service
      return {
        locationId,
        itemId,
        activeReservations: reservations,
        totalReservedQuantity: reservations.reduce((sum, r) => sum + r.quantity, 0)
      };
    } catch (error) {
      logger.error('Error getting active reservations:', error);
      return {
        locationId,
        itemId,
        activeReservations: [],
        totalReservedQuantity: 0
      };
    }
  }
}

module.exports = new RealTimeInventoryService();