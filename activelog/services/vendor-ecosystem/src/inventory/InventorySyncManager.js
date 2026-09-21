/**
 * Real-time Inventory Synchronization Manager
 * Handles bidirectional inventory sync between vendors and the platform
 */

import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import winston from 'winston';
import Redis from 'ioredis';
import axios from 'axios';
import cron from 'node-cron';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/inventory-sync.log' })
  ]
});

export class InventorySyncManager extends EventEmitter {
  constructor(io) {
    super();
    this.io = io;
    this.redis = null;
    this.inventoryCache = new Map();
    this.syncJobs = new Map();
    this.webhookEndpoints = new Map();
    this.syncStrategies = new Map();
    this.conflictResolvers = new Map();
    
    this.initializeSyncStrategies();
    this.initializeConflictResolvers();
  }

  async initialize() {
    try {
      // Initialize Redis connection
      this.redis = new Redis({
        host: process.env.REDIS_HOST || 'localhost',
        port: process.env.REDIS_PORT || 6379,
        retryDelayOnFailover: 100,
        enableReadyCheck: true,
        maxRetriesPerRequest: 3
      });

      this.redis.on('connect', () => {
        logger.info('✅ Redis connected for inventory sync');
      });

      this.redis.on('error', (error) => {
        logger.error('Redis connection error:', error);
      });

      // Set up periodic sync jobs
      this.setupPeriodicSync();

      // Set up real-time sync listeners
      this.setupRealTimeSync();

      logger.info('📦 Inventory Sync Manager initialized');
    } catch (error) {
      logger.error('Failed to initialize Inventory Sync Manager:', error);
      throw error;
    }
  }

  /**
   * Initialize synchronization strategies
   */
  initializeSyncStrategies() {
    this.syncStrategies.set('full', {
      name: 'Full Synchronization',
      description: 'Complete inventory sync, slower but most accurate',
      frequency: 'daily',
      execute: this.executeFullSync.bind(this)
    });

    this.syncStrategies.set('incremental', {
      name: 'Incremental Synchronization',
      description: 'Only sync changes since last update',
      frequency: 'hourly',
      execute: this.executeIncrementalSync.bind(this)
    });

    this.syncStrategies.set('real_time', {
      name: 'Real-time Synchronization',
      description: 'Immediate sync on inventory changes',
      frequency: 'continuous',
      execute: this.executeRealTimeSync.bind(this)
    });

    this.syncStrategies.set('batch', {
      name: 'Batch Synchronization',
      description: 'Sync in batches for performance',
      frequency: 'configurable',
      execute: this.executeBatchSync.bind(this)
    });
  }

  /**
   * Initialize conflict resolution strategies
   */
  initializeConflictResolvers() {
    this.conflictResolvers.set('vendor_wins', {
      name: 'Vendor Data Wins',
      description: 'Always use vendor data in conflicts',
      resolve: (vendorData, platformData) => vendorData
    });

    this.conflictResolvers.set('platform_wins', {
      name: 'Platform Data Wins',
      description: 'Always use platform data in conflicts',
      resolve: (vendorData, platformData) => platformData
    });

    this.conflictResolvers.set('most_recent', {
      name: 'Most Recent Wins',
      description: 'Use the most recently updated data',
      resolve: (vendorData, platformData) => {
        return new Date(vendorData.lastUpdated) > new Date(platformData.lastUpdated)
          ? vendorData : platformData;
      }
    });

    this.conflictResolvers.set('manual_review', {
      name: 'Manual Review Required',
      description: 'Flag for manual resolution',
      resolve: (vendorData, platformData) => {
        this.flagForManualReview(vendorData, platformData);
        return null; // No automatic resolution
      }
    });
  }

  /**
   * Register vendor for inventory synchronization
   */
  async registerVendorSync(vendorId, syncConfig) {
    try {
      const syncProfile = {
        vendorId,
        strategy: syncConfig.strategy || 'incremental',
        frequency: syncConfig.frequency || 'hourly',
        endpoints: {
          inventory: syncConfig.inventoryEndpoint,
          webhook: syncConfig.webhookEndpoint,
          auth: syncConfig.authConfig
        },
        mapping: syncConfig.fieldMapping || this.getDefaultMapping(),
        filters: syncConfig.filters || {},
        conflictResolution: syncConfig.conflictResolution || 'most_recent',
        isActive: true,
        lastSync: null,
        totalSyncs: 0,
        errors: [],
        createdAt: Date.now()
      };

      // Store sync profile
      await this.redis.hset('vendor_sync_profiles', vendorId, JSON.stringify(syncProfile));

      // Set up webhook endpoint if provided
      if (syncConfig.webhookEndpoint) {
        this.webhookEndpoints.set(vendorId, syncConfig.webhookEndpoint);
      }

      // Schedule initial sync
      await this.scheduleSync(vendorId, syncProfile.strategy, true);

      this.emit('vendor:sync_registered', { vendorId, syncProfile });

      logger.info(`📋 Registered vendor sync: ${vendorId} with strategy: ${syncProfile.strategy}`);

      return syncProfile;
    } catch (error) {
      logger.error(`Failed to register vendor sync: ${vendorId}`, error);
      throw error;
    }
  }

  /**
   * Synchronize vendor inventory
   */
  async syncInventory(vendorId, inventoryData = null) {
    try {
      const syncProfileData = await this.redis.hget('vendor_sync_profiles', vendorId);
      if (!syncProfileData) {
        throw new Error(`No sync profile found for vendor: ${vendorId}`);
      }

      const syncProfile = JSON.parse(syncProfileData);
      const strategy = this.syncStrategies.get(syncProfile.strategy);
      
      if (!strategy) {
        throw new Error(`Unknown sync strategy: ${syncProfile.strategy}`);
      }

      logger.info(`🔄 Starting ${strategy.name} for vendor: ${vendorId}`);

      // Execute sync strategy
      const syncResult = await strategy.execute(vendorId, syncProfile, inventoryData);

      // Update sync profile
      syncProfile.lastSync = Date.now();
      syncProfile.totalSyncs++;
      if (syncResult.error) {
        syncProfile.errors.push({
          timestamp: Date.now(),
          error: syncResult.error,
          details: syncResult.details
        });
        // Keep only last 10 errors
        if (syncProfile.errors.length > 10) {
          syncProfile.errors = syncProfile.errors.slice(-10);
        }
      }

      await this.redis.hset('vendor_sync_profiles', vendorId, JSON.stringify(syncProfile));

      // Emit sync completed event
      this.emit('inventory:synced', {
        vendorId,
        strategy: syncProfile.strategy,
        result: syncResult,
        timestamp: Date.now()
      });

      // Notify connected clients
      this.io.to(`vendor_${vendorId}`).emit('inventory_sync_completed', {
        vendorId,
        result: syncResult
      });

      return syncResult;
    } catch (error) {
      logger.error(`Failed to sync inventory for vendor: ${vendorId}`, error);
      throw error;
    }
  }

  /**
   * Execute full synchronization
   */
  async executeFullSync(vendorId, syncProfile, providedData = null) {
    try {
      let inventoryData;

      if (providedData) {
        inventoryData = providedData;
      } else {
        // Fetch full inventory from vendor
        inventoryData = await this.fetchVendorInventory(vendorId, syncProfile);
      }

      if (!inventoryData || !inventoryData.products) {
        throw new Error('No inventory data received from vendor');
      }

      // Process all products
      const results = {
        processed: 0,
        updated: 0,
        created: 0,
        errors: 0,
        conflicts: 0,
        items: []
      };

      for (const vendorProduct of inventoryData.products) {
        try {
          const result = await this.processInventoryItem(
            vendorId,
            vendorProduct,
            syncProfile
          );
          
          results.items.push(result);
          results.processed++;
          
          if (result.action === 'created') results.created++;
          if (result.action === 'updated') results.updated++;
          if (result.conflict) results.conflicts++;

        } catch (error) {
          logger.error(`Error processing product ${vendorProduct.id}:`, error);
          results.errors++;
          results.items.push({
            productId: vendorProduct.id,
            action: 'error',
            error: error.message
          });
        }
      }

      // Cache successful sync data
      await this.cacheInventoryData(vendorId, inventoryData, 'full');

      logger.info(`✅ Full sync completed for vendor ${vendorId}: ${results.processed} items processed`);

      return results;
    } catch (error) {
      logger.error(`Full sync failed for vendor ${vendorId}:`, error);
      return {
        success: false,
        error: error.message,
        processed: 0,
        updated: 0,
        created: 0,
        errors: 1
      };
    }
  }

  /**
   * Execute incremental synchronization
   */
  async executeIncrementalSync(vendorId, syncProfile) {
    try {
      const lastSyncTime = syncProfile.lastSync || (Date.now() - 24 * 60 * 60 * 1000); // 24h ago if no previous sync

      // Fetch only changes since last sync
      const changes = await this.fetchInventoryChanges(vendorId, syncProfile, lastSyncTime);

      if (!changes || changes.length === 0) {
        return {
          success: true,
          message: 'No changes detected',
          processed: 0,
          updated: 0,
          created: 0,
          deleted: 0
        };
      }

      const results = {
        processed: 0,
        updated: 0,
        created: 0,
        deleted: 0,
        errors: 0,
        items: []
      };

      for (const change of changes) {
        try {
          let result;
          
          if (change.action === 'delete') {
            result = await this.processInventoryDeletion(vendorId, change.productId);
            if (result.success) results.deleted++;
          } else {
            result = await this.processInventoryItem(vendorId, change.product, syncProfile);
            if (result.action === 'created') results.created++;
            if (result.action === 'updated') results.updated++;
          }

          results.items.push(result);
          results.processed++;

        } catch (error) {
          logger.error(`Error processing change for ${change.productId}:`, error);
          results.errors++;
        }
      }

      logger.info(`✅ Incremental sync completed for vendor ${vendorId}: ${results.processed} changes processed`);

      return results;
    } catch (error) {
      logger.error(`Incremental sync failed for vendor ${vendorId}:`, error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Execute real-time synchronization
   */
  async executeRealTimeSync(vendorId, syncProfile, inventoryData) {
    try {
      if (!inventoryData) {
        throw new Error('No inventory data provided for real-time sync');
      }

      // Process single item or small batch immediately
      const results = {
        processed: 0,
        updated: 0,
        created: 0,
        errors: 0,
        items: []
      };

      const items = Array.isArray(inventoryData.products) ? inventoryData.products : [inventoryData];

      for (const item of items) {
        try {
          const result = await this.processInventoryItem(vendorId, item, syncProfile);
          
          results.items.push(result);
          results.processed++;
          
          if (result.action === 'created') results.created++;
          if (result.action === 'updated') results.updated++;

          // Emit real-time update
          this.io.emit('inventory_updated', {
            vendorId,
            productId: item.id,
            data: result.data,
            timestamp: Date.now()
          });

        } catch (error) {
          logger.error(`Error in real-time sync for ${item.id}:`, error);
          results.errors++;
        }
      }

      return results;
    } catch (error) {
      logger.error(`Real-time sync failed for vendor ${vendorId}:`, error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Execute batch synchronization
   */
  async executeBatchSync(vendorId, syncProfile, inventoryData) {
    try {
      const batchSize = syncProfile.batchSize || 100;
      const items = inventoryData.products || [];
      
      const results = {
        processed: 0,
        updated: 0,
        created: 0,
        errors: 0,
        batches: 0
      };

      // Process in batches
      for (let i = 0; i < items.length; i += batchSize) {
        const batch = items.slice(i, i + batchSize);
        
        try {
          const batchResult = await this.processBatch(vendorId, batch, syncProfile);
          
          results.processed += batchResult.processed;
          results.updated += batchResult.updated;
          results.created += batchResult.created;
          results.errors += batchResult.errors;
          results.batches++;

          // Brief pause between batches to prevent overwhelming
          await new Promise(resolve => setTimeout(resolve, 100));

        } catch (error) {
          logger.error(`Batch processing error:`, error);
          results.errors += batch.length;
        }
      }

      return results;
    } catch (error) {
      logger.error(`Batch sync failed for vendor ${vendorId}:`, error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Process individual inventory item
   */
  async processInventoryItem(vendorId, vendorProduct, syncProfile) {
    try {
      // Map vendor data to platform format
      const mappedProduct = this.mapVendorData(vendorProduct, syncProfile.mapping);
      
      // Check if product exists in platform
      const existingProduct = await this.getExistingProduct(vendorId, mappedProduct.id);
      
      let result;
      if (existingProduct) {
        // Handle potential conflicts
        const conflictResult = await this.resolveConflicts(
          mappedProduct,
          existingProduct,
          syncProfile.conflictResolution
        );
        
        if (conflictResult.requiresManualReview) {
          result = {
            productId: mappedProduct.id,
            action: 'conflict',
            conflict: true,
            data: conflictResult
          };
        } else {
          // Update existing product
          const updatedProduct = await this.updatePlatformProduct(
            vendorId,
            mappedProduct.id,
            conflictResult.resolvedData
          );
          
          result = {
            productId: mappedProduct.id,
            action: 'updated',
            data: updatedProduct,
            changes: conflictResult.changes
          };
        }
      } else {
        // Create new product
        const newProduct = await this.createPlatformProduct(vendorId, mappedProduct);
        
        result = {
          productId: mappedProduct.id,
          action: 'created',
          data: newProduct
        };
      }

      // Update cache
      await this.updateInventoryCache(vendorId, mappedProduct.id, result.data);

      return result;
    } catch (error) {
      logger.error(`Failed to process inventory item:`, error);
      throw error;
    }
  }

  /**
   * Fetch vendor inventory via API
   */
  async fetchVendorInventory(vendorId, syncProfile) {
    try {
      const endpoint = syncProfile.endpoints.inventory;
      const authConfig = syncProfile.endpoints.auth;

      const requestConfig = {
        method: 'GET',
        url: endpoint,
        timeout: 30000,
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'VendorEcosystem-Sync/1.0'
        }
      };

      // Add authentication
      if (authConfig) {
        if (authConfig.type === 'bearer') {
          requestConfig.headers.Authorization = `Bearer ${authConfig.token}`;
        } else if (authConfig.type === 'api_key') {
          requestConfig.headers[authConfig.headerName] = authConfig.apiKey;
        } else if (authConfig.type === 'basic') {
          const credentials = Buffer.from(`${authConfig.username}:${authConfig.password}`).toString('base64');
          requestConfig.headers.Authorization = `Basic ${credentials}`;
        }
      }

      const response = await axios(requestConfig);
      
      if (response.status !== 200) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response.data;
    } catch (error) {
      logger.error(`Failed to fetch vendor inventory for ${vendorId}:`, error);
      throw error;
    }
  }

  /**
   * Fetch inventory changes since last sync
   */
  async fetchInventoryChanges(vendorId, syncProfile, since) {
    try {
      const endpoint = `${syncProfile.endpoints.inventory}/changes`;
      const authConfig = syncProfile.endpoints.auth;

      const requestConfig = {
        method: 'GET',
        url: endpoint,
        timeout: 30000,
        params: {
          since: new Date(since).toISOString(),
          limit: 1000
        },
        headers: {
          'Content-Type': 'application/json'
        }
      };

      // Add authentication (same as fetchVendorInventory)
      if (authConfig) {
        if (authConfig.type === 'bearer') {
          requestConfig.headers.Authorization = `Bearer ${authConfig.token}`;
        } else if (authConfig.type === 'api_key') {
          requestConfig.headers[authConfig.headerName] = authConfig.apiKey;
        }
      }

      const response = await axios(requestConfig);
      return response.data.changes || [];
    } catch (error) {
      if (error.response?.status === 404) {
        // Endpoint doesn't support incremental sync, fall back to full sync
        logger.warn(`Vendor ${vendorId} doesn't support incremental sync, performing full sync`);
        return null;
      }
      throw error;
    }
  }

  /**
   * Map vendor data to platform format
   */
  mapVendorData(vendorProduct, mapping) {
    const mapped = {};
    
    for (const [platformField, vendorField] of Object.entries(mapping)) {
      if (typeof vendorField === 'string') {
        mapped[platformField] = this.getNestedValue(vendorProduct, vendorField);
      } else if (typeof vendorField === 'function') {
        mapped[platformField] = vendorField(vendorProduct);
      } else if (vendorField.transform) {
        const value = this.getNestedValue(vendorProduct, vendorField.field);
        mapped[platformField] = vendorField.transform(value);
      }
    }

    // Add metadata
    mapped.vendorId = vendorProduct.vendorId;
    mapped.lastSynced = Date.now();
    mapped.syncSource = 'vendor_api';

    return mapped;
  }

  /**
   * Get default field mapping
   */
  getDefaultMapping() {
    return {
      id: 'id',
      name: 'name',
      description: 'description',
      price: 'price',
      quantity: 'quantity',
      sku: 'sku',
      category: 'category',
      brand: 'brand',
      model: 'model',
      weight: 'weight',
      dimensions: 'dimensions',
      images: 'images',
      specifications: 'specifications',
      availability: 'availability',
      lastUpdated: 'lastUpdated'
    };
  }

  /**
   * Resolve data conflicts
   */
  async resolveConflicts(vendorData, existingData, strategy) {
    const resolver = this.conflictResolvers.get(strategy);
    if (!resolver) {
      throw new Error(`Unknown conflict resolution strategy: ${strategy}`);
    }

    const changes = this.detectChanges(vendorData, existingData);
    
    if (changes.length === 0) {
      return {
        resolvedData: existingData,
        changes: [],
        requiresManualReview: false
      };
    }

    const resolvedData = resolver.resolve(vendorData, existingData);
    
    return {
      resolvedData,
      changes,
      requiresManualReview: resolvedData === null,
      conflictStrategy: strategy
    };
  }

  /**
   * Detect changes between vendor and existing data
   */
  detectChanges(vendorData, existingData) {
    const changes = [];
    
    for (const key of Object.keys(vendorData)) {
      if (key === 'lastSynced' || key === 'syncSource') continue;
      
      const vendorValue = vendorData[key];
      const existingValue = existingData[key];
      
      if (JSON.stringify(vendorValue) !== JSON.stringify(existingValue)) {
        changes.push({
          field: key,
          oldValue: existingValue,
          newValue: vendorValue
        });
      }
    }
    
    return changes;
  }

  /**
   * Setup periodic synchronization jobs
   */
  setupPeriodicSync() {
    // Full sync daily at 2 AM
    cron.schedule('0 2 * * *', async () => {
      logger.info('🕐 Starting scheduled full sync for all vendors');
      await this.performScheduledSync('full');
    });

    // Incremental sync every hour
    cron.schedule('0 * * * *', async () => {
      logger.info('🕐 Starting scheduled incremental sync for all vendors');
      await this.performScheduledSync('incremental');
    });

    // Batch sync every 15 minutes
    cron.schedule('*/15 * * * *', async () => {
      await this.performScheduledSync('batch');
    });
  }

  /**
   * Setup real-time sync listeners
   */
  setupRealTimeSync() {
    // Listen for inventory update events
    this.on('inventory:update', async (data) => {
      try {
        await this.executeRealTimeSync(data.vendorId, data.syncProfile, data.inventoryData);
      } catch (error) {
        logger.error('Real-time sync error:', error);
      }
    });
  }

  /**
   * Perform scheduled sync for all vendors with given strategy
   */
  async performScheduledSync(strategy) {
    try {
      const vendorProfiles = await this.redis.hgetall('vendor_sync_profiles');
      
      for (const [vendorId, profileData] of Object.entries(vendorProfiles)) {
        try {
          const profile = JSON.parse(profileData);
          
          if (profile.isActive && profile.strategy === strategy) {
            await this.syncInventory(vendorId);
          }
        } catch (error) {
          logger.error(`Scheduled sync failed for vendor ${vendorId}:`, error);
        }
      }
    } catch (error) {
      logger.error('Scheduled sync error:', error);
    }
  }

  /**
   * Helper methods
   */
  getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  }

  async cacheInventoryData(vendorId, data, type) {
    const cacheKey = `inventory:${vendorId}:${type}`;
    await this.redis.setex(cacheKey, 3600, JSON.stringify(data)); // Cache for 1 hour
  }

  async updateInventoryCache(vendorId, productId, data) {
    const cacheKey = `product:${vendorId}:${productId}`;
    await this.redis.setex(cacheKey, 1800, JSON.stringify(data)); // Cache for 30 minutes
  }

  async getExistingProduct(vendorId, productId) {
    // This would typically query your database
    const cacheKey = `product:${vendorId}:${productId}`;
    const cached = await this.redis.get(cacheKey);
    
    if (cached) {
      return JSON.parse(cached);
    }
    
    // In a real implementation, query your product database here
    return null;
  }

  async createPlatformProduct(vendorId, productData) {
    // This would create the product in your platform's database
    const product = {
      ...productData,
      id: uuidv4(),
      createdAt: Date.now(),
      updatedAt: Date.now()
    };
    
    // Cache the new product
    await this.updateInventoryCache(vendorId, product.id, product);
    
    return product;
  }

  async updatePlatformProduct(vendorId, productId, productData) {
    // This would update the product in your platform's database
    const product = {
      ...productData,
      updatedAt: Date.now()
    };
    
    // Update cache
    await this.updateInventoryCache(vendorId, productId, product);
    
    return product;
  }

  async processInventoryDeletion(vendorId, productId) {
    try {
      // Remove from platform database
      // await this.deleteFromDatabase(vendorId, productId);
      
      // Remove from cache
      const cacheKey = `product:${vendorId}:${productId}`;
      await this.redis.del(cacheKey);
      
      return {
        success: true,
        productId,
        action: 'deleted'
      };
    } catch (error) {
      return {
        success: false,
        productId,
        action: 'delete_failed',
        error: error.message
      };
    }
  }

  async processBatch(vendorId, items, syncProfile) {
    const results = {
      processed: 0,
      updated: 0,
      created: 0,
      errors: 0
    };

    // Process items in parallel batches
    const promises = items.map(item => 
      this.processInventoryItem(vendorId, item, syncProfile)
        .then(result => {
          results.processed++;
          if (result.action === 'created') results.created++;
          if (result.action === 'updated') results.updated++;
          return result;
        })
        .catch(error => {
          results.errors++;
          logger.error(`Batch item processing error:`, error);
          return { error: error.message };
        })
    );

    await Promise.all(promises);
    
    return results;
  }

  flagForManualReview(vendorData, platformData) {
    // This would flag the conflict for manual review in your system
    logger.warn('Manual review required for data conflict', {
      vendorData: vendorData.id,
      platformData: platformData.id
    });
  }

  async scheduleSync(vendorId, strategy, immediate = false) {
    if (immediate) {
      // Execute sync immediately
      await this.syncInventory(vendorId);
    }
    
    // Schedule future syncs based on strategy
    const syncJob = {
      vendorId,
      strategy,
      nextRun: this.calculateNextRun(strategy),
      isActive: true
    };
    
    this.syncJobs.set(vendorId, syncJob);
  }

  calculateNextRun(strategy) {
    const now = Date.now();
    switch (strategy) {
      case 'full': return now + 24 * 60 * 60 * 1000; // Daily
      case 'incremental': return now + 60 * 60 * 1000; // Hourly
      case 'batch': return now + 15 * 60 * 1000; // Every 15 minutes
      case 'real_time': return now + 1000; // Every second
      default: return now + 60 * 60 * 1000; // Default hourly
    }
  }

  /**
   * Public API methods
   */
  async getVendorInventory(vendorId) {
    try {
      const cacheKey = `inventory:${vendorId}:current`;
      const cached = await this.redis.get(cacheKey);
      
      if (cached) {
        return JSON.parse(cached);
      }
      
      // If not cached, trigger a sync
      await this.syncInventory(vendorId);
      
      // Try cache again
      const refreshed = await this.redis.get(cacheKey);
      return refreshed ? JSON.parse(refreshed) : null;
    } catch (error) {
      logger.error(`Failed to get vendor inventory: ${vendorId}`, error);
      throw error;
    }
  }

  async updateInventory(vendorId, productId, quantity) {
    try {
      // Update inventory in real-time
      const inventoryData = {
        id: productId,
        quantity,
        lastUpdated: Date.now()
      };

      const syncProfileData = await this.redis.hget('vendor_sync_profiles', vendorId);
      if (syncProfileData) {
        const syncProfile = JSON.parse(syncProfileData);
        await this.executeRealTimeSync(vendorId, syncProfile, inventoryData);
      }

      this.emit('inventory:updated', {
        vendorId,
        productId,
        quantity,
        timestamp: Date.now()
      });
    } catch (error) {
      logger.error(`Failed to update inventory: ${vendorId}/${productId}`, error);
      throw error;
    }
  }

  /**
   * Close connections (for graceful shutdown)
   */
  close() {
    if (this.redis) {
      this.redis.disconnect();
    }
    logger.info('Inventory Sync Manager closed');
  }
}