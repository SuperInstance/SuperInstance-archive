const logger = require('../config/logger');
const redis = require('../config/redis');
const moment = require('moment-timezone');
const { v4: uuidv4 } = require('uuid');

class MultiLocationService {
  constructor() {
    this.locations = new Map();
    this.syncInterval = parseInt(process.env.LOCATION_SYNC_INTERVAL) || 300000; // 5 minutes
    this.defaultTimezone = process.env.DEFAULT_TIMEZONE || 'America/New_York';
    
    this.locationTypes = {
      WAREHOUSE: 'warehouse',
      RETAIL_STORE: 'retail_store',
      DISTRIBUTION_CENTER: 'distribution_center',
      PICKUP_POINT: 'pickup_point',
      VIRTUAL: 'virtual'
    };

    this.syncStatus = {
      SYNCED: 'synced',
      SYNCING: 'syncing',
      OUT_OF_SYNC: 'out_of_sync',
      ERROR: 'error'
    };

    // Initialize sync scheduler
    this.initializeSyncScheduler();
  }

  /**
   * Initialize location sync scheduler
   */
  initializeSyncScheduler() {
    if (process.env.MULTI_LOCATION_ENABLED !== 'true') {
      logger.info('Multi-location support disabled');
      return;
    }

    setInterval(() => {
      this.syncAllLocations();
    }, this.syncInterval);
  }

  /**
   * Register a new location
   */
  async registerLocation(locationData) {
    try {
      const locationId = locationData.locationId || uuidv4();
      
      const location = {
        locationId,
        name: locationData.name,
        type: locationData.type || this.locationTypes.RETAIL_STORE,
        address: locationData.address,
        coordinates: locationData.coordinates, // { lat, lng }
        timezone: locationData.timezone || this.defaultTimezone,
        workingHours: locationData.workingHours || {
          monday: { open: '09:00', close: '18:00' },
          tuesday: { open: '09:00', close: '18:00' },
          wednesday: { open: '09:00', close: '18:00' },
          thursday: { open: '09:00', close: '18:00' },
          friday: { open: '09:00', close: '18:00' },
          saturday: { open: '10:00', close: '17:00' },
          sunday: { closed: true }
        },
        contact: locationData.contact,
        manager: locationData.manager,
        capacity: locationData.capacity || {},
        features: locationData.features || [],
        status: 'active',
        syncStatus: this.syncStatus.SYNCED,
        metadata: locationData.metadata || {},
        createdAt: new Date().toISOString(),
        lastSyncAt: new Date().toISOString()
      };

      // Store in memory cache
      this.locations.set(locationId, location);

      // Cache in Redis
      await redis.syncLocationData(locationId, {
        locationData: JSON.stringify(location),
        lastSync: new Date().toISOString()
      });

      logger.logInventoryEvent('location_registered', locationId, 'system', {
        name: location.name,
        type: location.type,
        features: location.features
      });

      return location;
    } catch (error) {
      logger.error('Error registering location:', error);
      throw error;
    }
  }

  /**
   * Get location details
   */
  async getLocation(locationId) {
    try {
      // Check memory cache first
      if (this.locations.has(locationId)) {
        return this.locations.get(locationId);
      }

      // Check Redis cache
      const locationData = await redis.getLocationData(locationId);
      if (locationData && locationData.locationData) {
        const location = JSON.parse(locationData.locationData);
        this.locations.set(locationId, location);
        return location;
      }

      return null;
    } catch (error) {
      logger.error('Error getting location:', error);
      return null;
    }
  }

  /**
   * Get all registered locations
   */
  async getAllLocations(filters = {}) {
    try {
      const allLocations = Array.from(this.locations.values());
      
      let filteredLocations = allLocations;

      // Apply filters
      if (filters.type) {
        filteredLocations = filteredLocations.filter(loc => loc.type === filters.type);
      }
      
      if (filters.status) {
        filteredLocations = filteredLocations.filter(loc => loc.status === filters.status);
      }
      
      if (filters.features && filters.features.length > 0) {
        filteredLocations = filteredLocations.filter(loc => 
          filters.features.some(feature => loc.features.includes(feature))
        );
      }

      // Sort by name by default
      filteredLocations.sort((a, b) => a.name.localeCompare(b.name));

      return filteredLocations;
    } catch (error) {
      logger.error('Error getting all locations:', error);
      return [];
    }
  }

  /**
   * Find locations near coordinates
   */
  async findNearbyLocations(coordinates, radiusKm = 50, filters = {}) {
    try {
      const allLocations = await this.getAllLocations(filters);
      
      const nearbyLocations = allLocations
        .filter(location => location.coordinates)
        .map(location => ({
          ...location,
          distance: this.calculateDistance(
            coordinates,
            location.coordinates
          )
        }))
        .filter(location => location.distance <= radiusKm)
        .sort((a, b) => a.distance - b.distance);

      return nearbyLocations;
    } catch (error) {
      logger.error('Error finding nearby locations:', error);
      return [];
    }
  }

  /**
   * Calculate distance between two coordinates using Haversine formula
   */
  calculateDistance(coord1, coord2) {
    const R = 6371; // Earth's radius in kilometers
    const dLat = this.toRadians(coord2.lat - coord1.lat);
    const dLon = this.toRadians(coord2.lng - coord1.lng);
    
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(this.toRadians(coord1.lat)) * Math.cos(this.toRadians(coord2.lat)) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  /**
   * Convert degrees to radians
   */
  toRadians(degrees) {
    return degrees * (Math.PI / 180);
  }

  /**
   * Get inventory across multiple locations
   */
  async getMultiLocationInventory(itemId, locationIds = null) {
    try {
      const targetLocations = locationIds || Array.from(this.locations.keys());
      const inventoryData = [];

      for (const locationId of targetLocations) {
        const location = await this.getLocation(locationId);
        if (!location) continue;

        const inventory = await redis.getInventoryItem(locationId, itemId);
        
        inventoryData.push({
          locationId,
          locationName: location.name,
          locationType: location.type,
          inventory: inventory || { quantity: 0, status: 'not_found' },
          distance: null, // Would be calculated based on user location
          timezone: location.timezone,
          workingHours: location.workingHours
        });
      }

      return {
        itemId,
        locations: inventoryData,
        totalQuantity: inventoryData.reduce((sum, loc) => sum + (loc.inventory.quantity || 0), 0),
        availableLocations: inventoryData.filter(loc => (loc.inventory.quantity || 0) > 0).length,
        lastUpdated: new Date().toISOString()
      };
    } catch (error) {
      logger.error('Error getting multi-location inventory:', error);
      throw error;
    }
  }

  /**
   * Transfer inventory between locations
   */
  async transferInventory(fromLocationId, toLocationId, itemId, quantity, transferData = {}) {
    try {
      const transferId = uuidv4();
      const timestamp = new Date().toISOString();

      // Validate locations
      const fromLocation = await this.getLocation(fromLocationId);
      const toLocation = await this.getLocation(toLocationId);
      
      if (!fromLocation || !toLocation) {
        throw new Error('Invalid location(s) for transfer');
      }

      // Check source inventory
      const sourceInventory = await redis.getInventoryItem(fromLocationId, itemId);
      if (!sourceInventory || sourceInventory.quantity < quantity) {
        throw new Error('Insufficient inventory at source location');
      }

      const transfer = {
        transferId,
        itemId,
        fromLocationId,
        toLocationId,
        quantity,
        status: 'initiated',
        requestedBy: transferData.requestedBy || 'system',
        reason: transferData.reason || 'inventory_transfer',
        estimatedDelivery: transferData.estimatedDelivery,
        trackingNumber: transferData.trackingNumber,
        metadata: transferData.metadata || {},
        timestamps: {
          initiated: timestamp,
          inTransit: null,
          completed: null,
          cancelled: null
        }
      };

      // Store transfer record
      await redis.client?.setEx(
        `transfer:${transferId}`,
        86400 * 7, // 7 days
        JSON.stringify(transfer)
      );

      // Update inventory at source (decrease)
      const sourceUpdate = {
        changeType: 'transfer_out',
        oldQuantity: sourceInventory.quantity,
        newQuantity: sourceInventory.quantity - quantity,
        reason: `Transfer to ${toLocation.name}`,
        userId: transferData.requestedBy || 'system',
        transactionId: transferId,
        metadata: { transferId, targetLocation: toLocationId }
      };

      // Note: In real implementation, you'd import the real-time service
      // await realTimeInventoryService.trackInventoryChange(fromLocationId, itemId, sourceUpdate);

      logger.logInventoryEvent('inventory_transfer_initiated', fromLocationId, itemId, {
        transferId,
        toLocationId,
        quantity,
        requestedBy: transferData.requestedBy
      });

      return transfer;
    } catch (error) {
      logger.error('Error transferring inventory:', error);
      throw error;
    }
  }

  /**
   * Complete inventory transfer
   */
  async completeInventoryTransfer(transferId, completionData = {}) {
    try {
      // Get transfer record
      const transferData = await redis.client?.get(`transfer:${transferId}`);
      if (!transferData) {
        throw new Error('Transfer not found');
      }

      const transfer = JSON.parse(transferData);
      if (transfer.status === 'completed') {
        throw new Error('Transfer already completed');
      }

      // Update transfer status
      transfer.status = 'completed';
      transfer.timestamps.completed = new Date().toISOString();
      transfer.completedBy = completionData.completedBy || 'system';
      transfer.actualDelivery = completionData.actualDelivery || new Date().toISOString();

      // Get destination inventory
      const destInventory = await redis.getInventoryItem(transfer.toLocationId, transfer.itemId) || { quantity: 0 };

      // Update inventory at destination (increase)
      const destUpdate = {
        changeType: 'transfer_in',
        oldQuantity: destInventory.quantity,
        newQuantity: destInventory.quantity + transfer.quantity,
        reason: `Transfer from location ${transfer.fromLocationId}`,
        userId: transfer.completedBy,
        transactionId: transferId,
        metadata: { transferId, sourceLocation: transfer.fromLocationId }
      };

      // Update transfer record
      await redis.client?.setEx(
        `transfer:${transferId}`,
        86400 * 7,
        JSON.stringify(transfer)
      );

      logger.logInventoryEvent('inventory_transfer_completed', transfer.toLocationId, transfer.itemId, {
        transferId,
        fromLocationId: transfer.fromLocationId,
        quantity: transfer.quantity,
        completedBy: transfer.completedBy
      });

      return transfer;
    } catch (error) {
      logger.error('Error completing inventory transfer:', error);
      throw error;
    }
  }

  /**
   * Sync all locations
   */
  async syncAllLocations() {
    try {
      const locations = Array.from(this.locations.keys());
      const syncPromises = locations.map(locationId => this.syncLocation(locationId));
      
      const results = await Promise.allSettled(syncPromises);
      
      let successCount = 0;
      let errorCount = 0;

      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          successCount++;
        } else {
          errorCount++;
          logger.error(`Sync failed for location ${locations[index]}:`, result.reason);
        }
      });

      logger.logInventoryEvent('multi_location_sync', 'system', 'sync', {
        totalLocations: locations.length,
        successCount,
        errorCount,
        syncedAt: new Date().toISOString()
      });

      return { totalLocations: locations.length, successCount, errorCount };
    } catch (error) {
      logger.error('Error syncing all locations:', error);
      return { totalLocations: 0, successCount: 0, errorCount: 1 };
    }
  }

  /**
   * Sync individual location
   */
  async syncLocation(locationId) {
    try {
      const location = this.locations.get(locationId);
      if (!location) return false;

      // Update sync status
      location.syncStatus = this.syncStatus.SYNCING;
      location.lastSyncAt = new Date().toISOString();

      // Perform sync operations (inventory counts, status updates, etc.)
      await this.performLocationSync(locationId);

      // Update sync status to synced
      location.syncStatus = this.syncStatus.SYNCED;
      
      // Update Redis cache
      await redis.syncLocationData(locationId, {
        locationData: JSON.stringify(location),
        lastSync: location.lastSyncAt
      });

      return true;
    } catch (error) {
      logger.error(`Error syncing location ${locationId}:`, error);
      
      // Update sync status to error
      const location = this.locations.get(locationId);
      if (location) {
        location.syncStatus = this.syncStatus.ERROR;
        location.lastSyncError = error.message;
      }
      
      return false;
    }
  }

  /**
   * Perform actual location sync operations
   */
  async performLocationSync(locationId) {
    try {
      // This would typically involve:
      // 1. Sync inventory counts
      // 2. Update location status
      // 3. Sync working hours and capacity
      // 4. Update pricing information
      // 5. Sync staff schedules
      
      // For now, we'll simulate the sync
      logger.debug(`Performing sync for location ${locationId}`);
      
      // Simulate sync delay
      await new Promise(resolve => setTimeout(resolve, 100));
      
      return true;
    } catch (error) {
      logger.error(`Sync operation failed for location ${locationId}:`, error);
      throw error;
    }
  }

  /**
   * Get location operating status
   */
  async getLocationOperatingStatus(locationId, checkTime = null) {
    try {
      const location = await this.getLocation(locationId);
      if (!location) {
        return { status: 'unknown', reason: 'Location not found' };
      }

      const checkDateTime = checkTime ? moment(checkTime) : moment();
      const locationTime = checkDateTime.tz(location.timezone);
      const dayOfWeek = locationTime.format('dddd').toLowerCase();
      const currentTime = locationTime.format('HH:mm');

      const daySchedule = location.workingHours[dayOfWeek];
      
      if (!daySchedule || daySchedule.closed) {
        return {
          status: 'closed',
          reason: 'Closed on ' + dayOfWeek,
          nextOpen: this.getNextOpenTime(location, locationTime)
        };
      }

      const openTime = moment(daySchedule.open, 'HH:mm');
      const closeTime = moment(daySchedule.close, 'HH:mm');
      const currentMoment = moment(currentTime, 'HH:mm');

      if (currentMoment.isBefore(openTime)) {
        return {
          status: 'closed',
          reason: 'Opens at ' + daySchedule.open,
          opensIn: openTime.diff(currentMoment, 'minutes')
        };
      }

      if (currentMoment.isAfter(closeTime)) {
        return {
          status: 'closed',
          reason: 'Closed at ' + daySchedule.close,
          nextOpen: this.getNextOpenTime(location, locationTime)
        };
      }

      return {
        status: 'open',
        closesAt: daySchedule.close,
        closesIn: closeTime.diff(currentMoment, 'minutes')
      };
    } catch (error) {
      logger.error('Error checking location operating status:', error);
      return { status: 'error', reason: error.message };
    }
  }

  /**
   * Get next opening time for location
   */
  getNextOpenTime(location, fromTime) {
    const daysOfWeek = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    let checkTime = fromTime.clone().add(1, 'day');
    
    for (let i = 0; i < 7; i++) {
      const dayOfWeek = checkTime.format('dddd').toLowerCase();
      const daySchedule = location.workingHours[dayOfWeek];
      
      if (daySchedule && !daySchedule.closed) {
        return {
          date: checkTime.format('YYYY-MM-DD'),
          time: daySchedule.open,
          dayOfWeek: dayOfWeek
        };
      }
      
      checkTime.add(1, 'day');
    }
    
    return null; // Location is closed for the entire week
  }

  /**
   * Get location capacity information
   */
  async getLocationCapacity(locationId) {
    try {
      const location = await this.getLocation(locationId);
      if (!location) {
        throw new Error('Location not found');
      }

      // Get current utilization (this would typically come from inventory and reservation data)
      const currentUtilization = await this.calculateLocationUtilization(locationId);

      return {
        locationId,
        locationName: location.name,
        capacity: location.capacity,
        currentUtilization,
        availableCapacity: {
          storage: (location.capacity.storage || 0) - (currentUtilization.storage || 0),
          staff: (location.capacity.staff || 0) - (currentUtilization.staff || 0),
          equipment: (location.capacity.equipment || 0) - (currentUtilization.equipment || 0)
        },
        utilizationPercentage: {
          storage: location.capacity.storage ? (currentUtilization.storage / location.capacity.storage * 100) : 0,
          staff: location.capacity.staff ? (currentUtilization.staff / location.capacity.staff * 100) : 0,
          equipment: location.capacity.equipment ? (currentUtilization.equipment / location.capacity.equipment * 100) : 0
        }
      };
    } catch (error) {
      logger.error('Error getting location capacity:', error);
      throw error;
    }
  }

  /**
   * Calculate current location utilization
   */
  async calculateLocationUtilization(locationId) {
    try {
      // This would typically involve complex calculations based on:
      // - Current inventory levels
      // - Active reservations
      // - Staff schedules
      // - Equipment usage
      
      // For now, return mock data
      return {
        storage: Math.floor(Math.random() * 1000),
        staff: Math.floor(Math.random() * 10),
        equipment: Math.floor(Math.random() * 20)
      };
    } catch (error) {
      logger.error('Error calculating location utilization:', error);
      return { storage: 0, staff: 0, equipment: 0 };
    }
  }

  /**
   * Update location configuration
   */
  async updateLocation(locationId, updates) {
    try {
      const location = this.locations.get(locationId);
      if (!location) {
        throw new Error('Location not found');
      }

      // Apply updates
      Object.assign(location, updates, {
        lastUpdated: new Date().toISOString()
      });

      // Update memory cache
      this.locations.set(locationId, location);

      // Update Redis cache
      await redis.syncLocationData(locationId, {
        locationData: JSON.stringify(location),
        lastSync: new Date().toISOString()
      });

      logger.logInventoryEvent('location_updated', locationId, 'system', {
        updatedFields: Object.keys(updates),
        updatedAt: location.lastUpdated
      });

      return location;
    } catch (error) {
      logger.error('Error updating location:', error);
      throw error;
    }
  }
}

module.exports = new MultiLocationService();