const { v4: uuidv4 } = require('uuid');
const logger = require('../config/logger');
const redis = require('../config/redis');
const EventEmitter = require('events');

class MultiLocationManager extends EventEmitter {
    constructor(socketIO, realTimeTracker) {
        super();
        this.io = socketIO;
        this.realTimeTracker = realTimeTracker;
        this.redis = redis.client;
        this.locations = new Map();
        this.transferRequests = new Map();
        this.locationNetworks = new Map();
        this.syncQueues = new Map();

        this.setupEventHandlers();
        this.startLocationSync();
    }

    setupEventHandlers() {
        this.on('location_added', this.handleLocationAdded.bind(this));
        this.on('location_updated', this.handleLocationUpdated.bind(this));
        this.on('inventory_transfer_requested', this.handleInventoryTransferRequested.bind(this));
        this.on('inventory_transfer_completed', this.handleInventoryTransferCompleted.bind(this));
        this.on('location_sync_required', this.handleLocationSyncRequired.bind(this));
    }

    async registerLocation(locationData) {
        const locationId = locationData.locationId || uuidv4();
        const timestamp = new Date();

        try {
            const location = {
                locationId,
                name: locationData.name,
                type: locationData.type, // 'warehouse', 'store', 'distribution_center', 'pop_up'
                address: locationData.address,
                coordinates: locationData.coordinates, // { lat, lng }
                timezone: locationData.timezone || 'UTC',
                operatingHours: locationData.operatingHours,
                capacity: locationData.capacity,
                isActive: locationData.isActive !== false,
                parentLocationId: locationData.parentLocationId,
                networkId: locationData.networkId || 'default',
                settings: {
                    allowTransfers: locationData.allowTransfers !== false,
                    autoSync: locationData.autoSync !== false,
                    syncInterval: locationData.syncInterval || 300, // 5 minutes
                    alertNotifications: locationData.alertNotifications !== false,
                    lowStockThreshold: locationData.lowStockThreshold || 10,
                    maxCapacity: locationData.maxCapacity || 10000
                },
                metadata: locationData.metadata || {},
                registeredAt: timestamp.toISOString(),
                lastSyncAt: timestamp.toISOString(),
                status: 'active'
            };

            // Store in Redis
            const locationKey = `location:${locationId}`;
            await this.redis.hmset(locationKey, {
                ...location,
                coordinates: JSON.stringify(location.coordinates),
                operatingHours: JSON.stringify(location.operatingHours),
                settings: JSON.stringify(location.settings),
                metadata: JSON.stringify(location.metadata)
            });

            // Store in memory cache
            this.locations.set(locationId, location);

            // Add to network
            await this.addLocationToNetwork(locationId, location.networkId);

            // Initialize sync queue for this location
            this.syncQueues.set(locationId, []);

            // Emit location added event
            this.emit('location_added', location);

            // Notify connected clients
            this.io.to('locations:all').emit('location_registered', {
                locationId,
                name: location.name,
                type: location.type,
                isActive: location.isActive,
                timestamp: timestamp.toISOString()
            });

            logger.logInventoryEvent('location_registered', locationId, 'system', {
                name: location.name,
                type: location.type,
                networkId: location.networkId
            });

            return location;

        } catch (error) {
            logger.error('Failed to register location', {
                locationData,
                error: error.message,
                stack: error.stack
            });
            throw error;
        }
    }

    async addLocationToNetwork(locationId, networkId) {
        if (!this.locationNetworks.has(networkId)) {
            this.locationNetworks.set(networkId, {
                networkId,
                locations: new Set(),
                transferRules: new Map(),
                syncRules: {
                    syncInterval: 300,
                    priorityItems: [],
                    conflictResolution: 'last_updated_wins'
                },
                createdAt: new Date().toISOString()
            });
        }

        const network = this.locationNetworks.get(networkId);
        network.locations.add(locationId);

        // Store network in Redis
        const networkKey = `network:${networkId}`;
        await this.redis.sadd(networkKey, locationId);

        logger.logInventoryEvent('location_added_to_network', locationId, 'system', {
            networkId,
            networkSize: network.locations.size
        });
    }

    async getMultiLocationInventory(itemId, options = {}) {
        try {
            const {
                includeReserved = true,
                includeTransitItems = true,
                networkId = null,
                sortBy = 'quantity',
                sortOrder = 'desc'
            } = options;

            const inventoryData = {
                itemId,
                locations: [],
                totalQuantity: 0,
                totalReserved: 0,
                totalInTransit: 0,
                availableQuantity: 0,
                lastUpdated: new Date().toISOString()
            };

            // Get all locations to check
            const locationsToCheck = networkId ? 
                Array.from(this.locationNetworks.get(networkId)?.locations || []) :
                Array.from(this.locations.keys());

            for (const locationId of locationsToCheck) {
                const location = await this.getLocationInfo(locationId);
                if (!location || !location.isActive) continue;

                // Get inventory data for this location
                const stockLevel = await this.realTimeTracker.getRealtimeStockLevel(locationId, itemId);
                
                // Get reserved quantity
                let reservedQuantity = 0;
                if (includeReserved) {
                    reservedQuantity = await this.getReservedQuantity(locationId, itemId);
                }

                // Get in-transit quantity
                let inTransitQuantity = 0;
                if (includeTransitItems) {
                    inTransitQuantity = await this.getInTransitQuantity(locationId, itemId);
                }

                const availableAtLocation = Math.max(0, stockLevel.quantity - reservedQuantity);

                const locationInventory = {
                    locationId,
                    locationName: location.name,
                    locationType: location.type,
                    coordinates: location.coordinates,
                    timezone: location.timezone,
                    quantity: stockLevel.quantity,
                    reservedQuantity,
                    inTransitQuantity,
                    availableQuantity: availableAtLocation,
                    lastUpdated: stockLevel.lastUpdated,
                    alerts: stockLevel.alerts || [],
                    canTransferTo: await this.canTransferTo(locationId),
                    canTransferFrom: await this.canTransferFrom(locationId)
                };

                inventoryData.locations.push(locationInventory);
                inventoryData.totalQuantity += stockLevel.quantity;
                inventoryData.totalReserved += reservedQuantity;
                inventoryData.totalInTransit += inTransitQuantity;
                inventoryData.availableQuantity += availableAtLocation;
            }

            // Sort locations
            inventoryData.locations.sort((a, b) => {
                const aValue = a[sortBy] || 0;
                const bValue = b[sortBy] || 0;
                
                if (sortOrder === 'asc') {
                    return aValue - bValue;
                } else {
                    return bValue - aValue;
                }
            });

            // Add recommendations
            inventoryData.recommendations = await this.generateInventoryRecommendations(itemId, inventoryData);

            return inventoryData;

        } catch (error) {
            logger.error('Failed to get multi-location inventory', {
                itemId,
                options,
                error: error.message
            });
            throw error;
        }
    }

    async findNearbyLocations(coordinates, radiusKm = 50, options = {}) {
        try {
            const {
                includeOutOfStock = false,
                itemId = null,
                minQuantity = 1,
                locationType = null,
                networkId = null
            } = options;

            const nearbyLocations = [];
            const locationsToCheck = networkId ? 
                Array.from(this.locationNetworks.get(networkId)?.locations || []) :
                Array.from(this.locations.keys());

            for (const locationId of locationsToCheck) {
                const location = await this.getLocationInfo(locationId);
                if (!location || !location.isActive) continue;

                // Filter by location type if specified
                if (locationType && location.type !== locationType) continue;

                // Calculate distance
                const distance = this.calculateDistance(
                    coordinates.lat, coordinates.lng,
                    location.coordinates.lat, location.coordinates.lng
                );

                if (distance <= radiusKm) {
                    const locationData = {
                        locationId,
                        name: location.name,
                        type: location.type,
                        address: location.address,
                        coordinates: location.coordinates,
                        distance: Math.round(distance * 100) / 100, // Round to 2 decimal places
                        operatingHours: location.operatingHours,
                        isOpen: this.isLocationOpen(location),
                        canPickup: location.settings.allowPickup !== false
                    };

                    // Check item availability if specified
                    if (itemId) {
                        const stockLevel = await this.realTimeTracker.getRealtimeStockLevel(locationId, itemId);
                        const reservedQuantity = await this.getReservedQuantity(locationId, itemId);
                        const availableQuantity = Math.max(0, stockLevel.quantity - reservedQuantity);

                        locationData.inventory = {
                            quantity: stockLevel.quantity,
                            reservedQuantity,
                            availableQuantity,
                            hasStock: availableQuantity >= minQuantity,
                            lastUpdated: stockLevel.lastUpdated
                        };

                        // Skip if out of stock and not including out of stock locations
                        if (!includeOutOfStock && availableQuantity < minQuantity) {
                            continue;
                        }
                    }

                    nearbyLocations.push(locationData);
                }
            }

            // Sort by distance
            nearbyLocations.sort((a, b) => a.distance - b.distance);

            return nearbyLocations;

        } catch (error) {
            logger.error('Failed to find nearby locations', {
                coordinates,
                radiusKm,
                options,
                error: error.message
            });
            throw error;
        }
    }

    async requestInventoryTransfer(transferRequest) {
        const transferId = uuidv4();
        const timestamp = new Date();

        try {
            const {
                itemId,
                fromLocationId,
                toLocationId,
                quantity,
                priority = 'normal',
                requestedBy,
                reason = 'stock_rebalancing',
                expectedDeliveryDate = null,
                notes = ''
            } = transferRequest;

            // Validate locations and inventory
            await this.validateTransferRequest(itemId, fromLocationId, toLocationId, quantity);

            const transfer = {
                transferId,
                itemId,
                fromLocationId,
                toLocationId,
                quantity,
                priority,
                status: 'pending_approval',
                requestedBy,
                reason,
                expectedDeliveryDate,
                notes,
                requestedAt: timestamp.toISOString(),
                approvedAt: null,
                startedAt: null,
                completedAt: null,
                approvedBy: null,
                cancelledBy: null,
                trackingInfo: {
                    carrier: null,
                    trackingNumber: null,
                    estimatedDelivery: expectedDeliveryDate
                },
                metadata: transferRequest.metadata || {}
            };

            // Store transfer request
            const transferKey = `transfer:${transferId}`;
            await this.redis.hmset(transferKey, {
                ...transfer,
                trackingInfo: JSON.stringify(transfer.trackingInfo),
                metadata: JSON.stringify(transfer.metadata)
            });
            await this.redis.expire(transferKey, 86400 * 30); // 30 days

            this.transferRequests.set(transferId, transfer);

            // Add to sync queues
            this.addToSyncQueue(fromLocationId, {
                type: 'transfer_out',
                transferId,
                itemId,
                quantity
            });

            this.addToSyncQueue(toLocationId, {
                type: 'transfer_in',
                transferId,
                itemId,
                quantity
            });

            // Emit transfer requested event
            this.emit('inventory_transfer_requested', transfer);

            // Notify locations
            this.io.to(`location:${fromLocationId}`).emit('transfer_requested', {
                type: 'outbound',
                transferId,
                itemId,
                quantity,
                destination: toLocationId,
                timestamp: timestamp.toISOString()
            });

            this.io.to(`location:${toLocationId}`).emit('transfer_requested', {
                type: 'inbound',
                transferId,
                itemId,
                quantity,
                source: fromLocationId,
                timestamp: timestamp.toISOString()
            });

            logger.logInventoryEvent('transfer_requested', fromLocationId, requestedBy, {
                transferId,
                itemId,
                toLocationId,
                quantity,
                priority
            });

            return transfer;

        } catch (error) {
            logger.error('Failed to request inventory transfer', {
                transferRequest,
                error: error.message
            });
            throw error;
        }
    }

    async approveTransfer(transferId, approvedBy) {
        try {
            const transfer = await this.getTransferRequest(transferId);
            if (!transfer) {
                throw new Error(`Transfer request not found: ${transferId}`);
            }

            if (transfer.status !== 'pending_approval') {
                throw new Error(`Transfer ${transferId} cannot be approved. Current status: ${transfer.status}`);
            }

            // Update transfer status
            const timestamp = new Date();
            transfer.status = 'approved';
            transfer.approvedAt = timestamp.toISOString();
            transfer.approvedBy = approvedBy;

            // Update in Redis
            const transferKey = `transfer:${transferId}`;
            await this.redis.hmset(transferKey, {
                status: transfer.status,
                approvedAt: transfer.approvedAt,
                approvedBy: transfer.approvedBy
            });

            // Update in memory
            this.transferRequests.set(transferId, transfer);

            // Reserve inventory at source location
            await this.realTimeTracker.trackInventoryChange(
                transfer.fromLocationId,
                transfer.itemId,
                {
                    changeType: 'reservation',
                    quantity: transfer.quantity,
                    reason: 'transfer_reserved',
                    userId: approvedBy,
                    transactionId: transferId,
                    metadata: {
                        transferId,
                        destinationLocationId: transfer.toLocationId
                    }
                }
            );

            // Notify locations
            this.io.to(`location:${transfer.fromLocationId}`).emit('transfer_approved', {
                transferId,
                status: 'approved',
                timestamp: timestamp.toISOString()
            });

            this.io.to(`location:${transfer.toLocationId}`).emit('transfer_approved', {
                transferId,
                status: 'approved',
                timestamp: timestamp.toISOString()
            });

            logger.logInventoryEvent('transfer_approved', transfer.fromLocationId, approvedBy, {
                transferId,
                itemId: transfer.itemId,
                quantity: transfer.quantity
            });

            return transfer;

        } catch (error) {
            logger.error('Failed to approve transfer', {
                transferId,
                approvedBy,
                error: error.message
            });
            throw error;
        }
    }

    async startTransfer(transferId, startedBy, carrierInfo = {}) {
        try {
            const transfer = await this.getTransferRequest(transferId);
            if (!transfer) {
                throw new Error(`Transfer request not found: ${transferId}`);
            }

            if (transfer.status !== 'approved') {
                throw new Error(`Transfer ${transferId} cannot be started. Current status: ${transfer.status}`);
            }

            // Update transfer status
            const timestamp = new Date();
            transfer.status = 'in_transit';
            transfer.startedAt = timestamp.toISOString();
            transfer.trackingInfo = {
                ...transfer.trackingInfo,
                ...carrierInfo,
                shippedAt: timestamp.toISOString()
            };

            // Update in Redis
            const transferKey = `transfer:${transferId}`;
            await this.redis.hmset(transferKey, {
                status: transfer.status,
                startedAt: transfer.startedAt,
                trackingInfo: JSON.stringify(transfer.trackingInfo)
            });

            // Update in memory
            this.transferRequests.set(transferId, transfer);

            // Move inventory out of source location
            await this.realTimeTracker.trackInventoryChange(
                transfer.fromLocationId,
                transfer.itemId,
                {
                    changeType: 'transfer_out',
                    quantity: transfer.quantity,
                    reason: 'inventory_transfer',
                    userId: startedBy,
                    transactionId: transferId,
                    metadata: {
                        transferId,
                        destinationLocationId: transfer.toLocationId,
                        trackingInfo: transfer.trackingInfo
                    }
                }
            );

            // Notify locations
            this.io.to(`location:${transfer.fromLocationId}`).emit('transfer_shipped', {
                transferId,
                trackingInfo: transfer.trackingInfo,
                timestamp: timestamp.toISOString()
            });

            this.io.to(`location:${transfer.toLocationId}`).emit('transfer_shipped', {
                transferId,
                trackingInfo: transfer.trackingInfo,
                estimatedDelivery: transfer.trackingInfo.estimatedDelivery,
                timestamp: timestamp.toISOString()
            });

            logger.logInventoryEvent('transfer_shipped', transfer.fromLocationId, startedBy, {
                transferId,
                itemId: transfer.itemId,
                quantity: transfer.quantity,
                trackingNumber: carrierInfo.trackingNumber
            });

            return transfer;

        } catch (error) {
            logger.error('Failed to start transfer', {
                transferId,
                startedBy,
                carrierInfo,
                error: error.message
            });
            throw error;
        }
    }

    async completeTransfer(transferId, completedBy, receivedQuantity = null) {
        try {
            const transfer = await this.getTransferRequest(transferId);
            if (!transfer) {
                throw new Error(`Transfer request not found: ${transferId}`);
            }

            if (transfer.status !== 'in_transit') {
                throw new Error(`Transfer ${transferId} cannot be completed. Current status: ${transfer.status}`);
            }

            const actualQuantity = receivedQuantity !== null ? receivedQuantity : transfer.quantity;
            const timestamp = new Date();

            // Update transfer status
            transfer.status = 'completed';
            transfer.completedAt = timestamp.toISOString();
            transfer.actualQuantity = actualQuantity;

            // Update in Redis
            const transferKey = `transfer:${transferId}`;
            await this.redis.hmset(transferKey, {
                status: transfer.status,
                completedAt: transfer.completedAt,
                actualQuantity: actualQuantity
            });

            // Update in memory
            this.transferRequests.set(transferId, transfer);

            // Add inventory to destination location
            await this.realTimeTracker.trackInventoryChange(
                transfer.toLocationId,
                transfer.itemId,
                {
                    changeType: 'transfer_in',
                    quantity: actualQuantity,
                    reason: 'inventory_transfer',
                    userId: completedBy,
                    transactionId: transferId,
                    metadata: {
                        transferId,
                        sourceLocationId: transfer.fromLocationId,
                        originalQuantity: transfer.quantity,
                        actualQuantity
                    }
                }
            );

            // Handle quantity discrepancy if any
            if (actualQuantity !== transfer.quantity) {
                const discrepancy = transfer.quantity - actualQuantity;
                logger.logInventoryEvent('transfer_quantity_discrepancy', transfer.fromLocationId, completedBy, {
                    transferId,
                    itemId: transfer.itemId,
                    expectedQuantity: transfer.quantity,
                    actualQuantity,
                    discrepancy
                });

                // You might want to create an adjustment record or investigation task here
            }

            // Emit transfer completed event
            this.emit('inventory_transfer_completed', transfer);

            // Notify locations
            this.io.to(`location:${transfer.fromLocationId}`).emit('transfer_completed', {
                transferId,
                actualQuantity,
                timestamp: timestamp.toISOString()
            });

            this.io.to(`location:${transfer.toLocationId}`).emit('transfer_completed', {
                transferId,
                actualQuantity,
                timestamp: timestamp.toISOString()
            });

            logger.logInventoryEvent('transfer_completed', transfer.toLocationId, completedBy, {
                transferId,
                itemId: transfer.itemId,
                quantity: actualQuantity
            });

            return transfer;

        } catch (error) {
            logger.error('Failed to complete transfer', {
                transferId,
                completedBy,
                receivedQuantity,
                error: error.message
            });
            throw error;
        }
    }

    async syncLocationInventory(locationId, targetLocationId = null) {
        try {
            const timestamp = new Date();
            const syncId = uuidv4();

            // Get all inventory items for the location
            const pattern = `inventory:${locationId}:*`;
            const inventoryKeys = await this.redis.keys(pattern);

            const syncResults = {
                syncId,
                locationId,
                targetLocationId,
                startedAt: timestamp.toISOString(),
                itemsSynced: 0,
                conflicts: [],
                errors: [],
                status: 'running'
            };

            if (targetLocationId) {
                // Sync with specific location
                await this.syncBetweenLocations(locationId, targetLocationId, syncResults);
            } else {
                // Sync with network
                const location = await this.getLocationInfo(locationId);
                const network = this.locationNetworks.get(location.networkId);
                
                if (network) {
                    for (const otherLocationId of network.locations) {
                        if (otherLocationId !== locationId) {
                            await this.syncBetweenLocations(locationId, otherLocationId, syncResults);
                        }
                    }
                }
            }

            syncResults.completedAt = new Date().toISOString();
            syncResults.status = 'completed';

            // Update last sync time for location
            await this.redis.hset(`location:${locationId}`, 'lastSyncAt', syncResults.completedAt);

            // Emit sync completed event
            this.emit('location_sync_completed', syncResults);

            logger.logInventoryEvent('location_sync_completed', locationId, 'system', {
                syncId,
                itemsSynced: syncResults.itemsSynced,
                conflicts: syncResults.conflicts.length,
                errors: syncResults.errors.length
            });

            return syncResults;

        } catch (error) {
            logger.error('Failed to sync location inventory', {
                locationId,
                targetLocationId,
                error: error.message
            });
            throw error;
        }
    }

    // Helper methods

    async getLocationInfo(locationId) {
        if (this.locations.has(locationId)) {
            return this.locations.get(locationId);
        }

        // Load from Redis
        const locationKey = `location:${locationId}`;
        const locationData = await this.redis.hgetall(locationKey);

        if (Object.keys(locationData).length === 0) {
            return null;
        }

        const location = {
            ...locationData,
            coordinates: JSON.parse(locationData.coordinates || '{}'),
            operatingHours: JSON.parse(locationData.operatingHours || '{}'),
            settings: JSON.parse(locationData.settings || '{}'),
            metadata: JSON.parse(locationData.metadata || '{}'),
            isActive: locationData.isActive === 'true'
        };

        this.locations.set(locationId, location);
        return location;
    }

    async getReservedQuantity(locationId, itemId) {
        const reservationKey = `reservations:${locationId}:${itemId}`;
        const reservations = await this.redis.hgetall(reservationKey);
        
        let totalReserved = 0;
        const now = new Date();

        for (const [reservationId, reservationData] of Object.entries(reservations)) {
            const reservation = JSON.parse(reservationData);
            const expiresAt = new Date(reservation.expiresAt);
            
            if (expiresAt > now) {
                totalReserved += reservation.quantity;
            }
        }

        return totalReserved;
    }

    async getInTransitQuantity(locationId, itemId) {
        const transfers = Array.from(this.transferRequests.values());
        let inTransitQuantity = 0;

        for (const transfer of transfers) {
            if (transfer.itemId === itemId && 
                transfer.toLocationId === locationId && 
                transfer.status === 'in_transit') {
                inTransitQuantity += transfer.quantity;
            }
        }

        return inTransitQuantity;
    }

    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth's radius in kilometers
        const dLat = this.toRadians(lat2 - lat1);
        const dLon = this.toRadians(lon2 - lon1);
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    toRadians(degrees) {
        return degrees * (Math.PI/180);
    }

    isLocationOpen(location) {
        if (!location.operatingHours) return true;
        
        const now = new Date();
        const currentDay = now.toLocaleLowerCase();
        const currentTime = now.getHours() * 100 + now.getMinutes(); // HHMM format
        
        const todayHours = location.operatingHours[currentDay];
        if (!todayHours) return false;
        
        const openTime = parseInt(todayHours.open.replace(':', ''));
        const closeTime = parseInt(todayHours.close.replace(':', ''));
        
        return currentTime >= openTime && currentTime <= closeTime;
    }

    async validateTransferRequest(itemId, fromLocationId, toLocationId, quantity) {
        // Check if locations exist and are active
        const fromLocation = await this.getLocationInfo(fromLocationId);
        const toLocation = await this.getLocationInfo(toLocationId);

        if (!fromLocation || !fromLocation.isActive) {
            throw new Error(`Source location ${fromLocationId} is not available`);
        }

        if (!toLocation || !toLocation.isActive) {
            throw new Error(`Destination location ${toLocationId} is not available`);
        }

        // Check if transfers are allowed
        if (!fromLocation.settings.allowTransfers) {
            throw new Error(`Transfers are not allowed from location ${fromLocationId}`);
        }

        // Check available inventory
        const stockLevel = await this.realTimeTracker.getRealtimeStockLevel(fromLocationId, itemId);
        const reservedQuantity = await this.getReservedQuantity(fromLocationId, itemId);
        const availableQuantity = Math.max(0, stockLevel.quantity - reservedQuantity);

        if (availableQuantity < quantity) {
            throw new Error(`Insufficient inventory. Available: ${availableQuantity}, Requested: ${quantity}`);
        }

        return true;
    }

    async canTransferTo(locationId) {
        const location = await this.getLocationInfo(locationId);
        return location?.settings?.allowTransfers !== false;
    }

    async canTransferFrom(locationId) {
        const location = await this.getLocationInfo(locationId);
        return location?.settings?.allowTransfers !== false;
    }

    async getTransferRequest(transferId) {
        if (this.transferRequests.has(transferId)) {
            return this.transferRequests.get(transferId);
        }

        // Load from Redis
        const transferKey = `transfer:${transferId}`;
        const transferData = await this.redis.hgetall(transferKey);

        if (Object.keys(transferData).length === 0) {
            return null;
        }

        const transfer = {
            ...transferData,
            quantity: parseInt(transferData.quantity),
            trackingInfo: JSON.parse(transferData.trackingInfo || '{}'),
            metadata: JSON.parse(transferData.metadata || '{}')
        };

        this.transferRequests.set(transferId, transfer);
        return transfer;
    }

    addToSyncQueue(locationId, syncItem) {
        if (!this.syncQueues.has(locationId)) {
            this.syncQueues.set(locationId, []);
        }
        
        this.syncQueues.get(locationId).push({
            ...syncItem,
            queuedAt: new Date().toISOString()
        });
    }

    async generateInventoryRecommendations(itemId, inventoryData) {
        const recommendations = [];

        // Find locations with excess inventory
        const locationsWithStock = inventoryData.locations.filter(loc => loc.availableQuantity > 0);
        const locationsWithoutStock = inventoryData.locations.filter(loc => loc.availableQuantity === 0);

        // Recommend transfers from overstocked to understocked locations
        if (locationsWithStock.length > 0 && locationsWithoutStock.length > 0) {
            const overStocked = locationsWithStock.filter(loc => loc.availableQuantity > 50); // arbitrary threshold
            
            for (const sourceLocation of overStocked) {
                for (const targetLocation of locationsWithoutStock) {
                    const distance = this.calculateDistance(
                        sourceLocation.coordinates.lat,
                        sourceLocation.coordinates.lng,
                        targetLocation.coordinates.lat,
                        targetLocation.coordinates.lng
                    );

                    if (distance <= 100) { // Within 100km
                        recommendations.push({
                            type: 'transfer_suggestion',
                            priority: targetLocation.alerts.some(a => a.type === 'out_of_stock') ? 'high' : 'medium',
                            fromLocationId: sourceLocation.locationId,
                            toLocationId: targetLocation.locationId,
                            suggestedQuantity: Math.min(sourceLocation.availableQuantity / 2, 25),
                            distance,
                            reason: 'stock_balancing'
                        });
                    }
                }
            }
        }

        // Recommend reordering for locations with consistent low stock
        for (const location of inventoryData.locations) {
            if (location.alerts.some(alert => alert.type === 'low_stock' || alert.type === 'out_of_stock')) {
                recommendations.push({
                    type: 'reorder_suggestion',
                    priority: location.availableQuantity === 0 ? 'critical' : 'high',
                    locationId: location.locationId,
                    suggestedQuantity: 50, // Could be based on historical sales data
                    reason: location.availableQuantity === 0 ? 'out_of_stock' : 'low_stock'
                });
            }
        }

        return recommendations;
    }

    async syncBetweenLocations(locationId1, locationId2, syncResults) {
        // This is a placeholder for actual sync logic
        // In a real implementation, you would:
        // 1. Compare inventory levels between locations
        // 2. Detect conflicts
        // 3. Apply conflict resolution rules
        // 4. Update both locations
        
        syncResults.itemsSynced += 1;
    }

    // Event handlers
    handleLocationAdded(location) {
        logger.logInventoryEvent('location_added', location.locationId, 'system', {
            name: location.name,
            type: location.type
        });
    }

    handleLocationUpdated(location) {
        logger.logInventoryEvent('location_updated', location.locationId, 'system', {
            name: location.name
        });
    }

    handleInventoryTransferRequested(transfer) {
        logger.logInventoryEvent('transfer_requested', transfer.fromLocationId, transfer.requestedBy, {
            transferId: transfer.transferId,
            itemId: transfer.itemId,
            quantity: transfer.quantity
        });
    }

    handleInventoryTransferCompleted(transfer) {
        logger.logInventoryEvent('transfer_completed', transfer.toLocationId, 'system', {
            transferId: transfer.transferId,
            itemId: transfer.itemId,
            quantity: transfer.actualQuantity || transfer.quantity
        });
    }

    handleLocationSyncRequired(data) {
        // Queue sync operation
        this.addToSyncQueue(data.locationId, {
            type: 'full_sync',
            reason: data.reason,
            priority: data.priority || 'normal'
        });
    }

    startLocationSync() {
        // Process sync queues every 5 minutes
        setInterval(async () => {
            for (const [locationId, syncQueue] of this.syncQueues) {
                if (syncQueue.length > 0) {
                    try {
                        await this.processSyncQueue(locationId);
                    } catch (error) {
                        logger.error('Failed to process sync queue', {
                            locationId,
                            error: error.message
                        });
                    }
                }
            }
        }, 300000); // 5 minutes

        logger.info('Multi-location sync started');
    }

    async processSyncQueue(locationId) {
        const syncQueue = this.syncQueues.get(locationId) || [];
        if (syncQueue.length === 0) return;

        logger.debug('Processing sync queue', {
            locationId,
            queueSize: syncQueue.length
        });

        // Process items in queue (simplified implementation)
        this.syncQueues.set(locationId, []);
    }

    async getNetworkMetrics(networkId = null) {
        const metrics = {
            networks: networkId ? 1 : this.locationNetworks.size,
            totalLocations: 0,
            activeTransfers: 0,
            pendingTransfers: 0,
            syncQueueSize: 0,
            timestamp: new Date().toISOString()
        };

        const networksToCheck = networkId ? [networkId] : Array.from(this.locationNetworks.keys());

        for (const network of networksToCheck) {
            const networkData = this.locationNetworks.get(network);
            if (networkData) {
                metrics.totalLocations += networkData.locations.size;
            }
        }

        // Count transfers
        for (const transfer of this.transferRequests.values()) {
            if (transfer.status === 'in_transit') {
                metrics.activeTransfers++;
            } else if (transfer.status === 'pending_approval') {
                metrics.pendingTransfers++;
            }
        }

        // Count sync queue items
        for (const queue of this.syncQueues.values()) {
            metrics.syncQueueSize += queue.length;
        }

        return metrics;
    }
}

module.exports = MultiLocationManager;