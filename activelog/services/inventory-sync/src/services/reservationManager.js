const { v4: uuidv4 } = require('uuid');
const moment = require('moment');
const logger = require('../config/logger');
const redis = require('../config/redis');
const EventEmitter = require('events');

class ReservationManager extends EventEmitter {
    constructor(socketIO, realTimeTracker, multiLocationManager) {
        super();
        this.io = socketIO;
        this.realTimeTracker = realTimeTracker;
        this.multiLocationManager = multiLocationManager;
        this.redis = redis.client;
        this.reservations = new Map();
        this.expirationQueue = new Map();
        this.reservationPolicies = new Map();

        this.setupEventHandlers();
        this.startExpirationMonitoring();
    }

    setupEventHandlers() {
        this.on('reservation_created', this.handleReservationCreated.bind(this));
        this.on('reservation_confirmed', this.handleReservationConfirmed.bind(this));
        this.on('reservation_expired', this.handleReservationExpired.bind(this));
        this.on('reservation_cancelled', this.handleReservationCancelled.bind(this));
        this.on('reservation_fulfilled', this.handleReservationFulfilled.bind(this));
    }

    async createReservation(reservationRequest) {
        const reservationId = uuidv4();
        const timestamp = new Date();

        try {
            const {
                customerId,
                items, // Array of { itemId, quantity, locationId }
                reservationType = 'customer_pickup',
                expirationMinutes = 60,
                priority = 'normal',
                notes = '',
                customerInfo = {},
                contactPreferences = {},
                metadata = {}
            } = reservationRequest;

            // Validate items and availability
            await this.validateReservationItems(items);

            // Calculate expiration time
            const expiresAt = moment().add(expirationMinutes, 'minutes').toDate();

            // Create reservation object
            const reservation = {
                reservationId,
                customerId,
                items: items.map(item => ({
                    ...item,
                    itemReservationId: uuidv4(),
                    reservedQuantity: item.quantity,
                    confirmedQuantity: 0,
                    status: 'reserved'
                })),
                reservationType,
                status: 'active',
                priority,
                notes,
                customerInfo: {
                    name: customerInfo.name || '',
                    email: customerInfo.email || '',
                    phone: customerInfo.phone || '',
                    alternatePhone: customerInfo.alternatePhone || '',
                    ...customerInfo
                },
                contactPreferences: {
                    email: contactPreferences.email !== false,
                    sms: contactPreferences.sms !== false,
                    push: contactPreferences.push !== false,
                    ...contactPreferences
                },
                createdAt: timestamp.toISOString(),
                updatedAt: timestamp.toISOString(),
                expiresAt: expiresAt.toISOString(),
                confirmedAt: null,
                cancelledAt: null,
                fulfilledAt: null,
                pickupScheduledAt: null,
                notifications: {
                    created: false,
                    reminder: false,
                    expiring: false,
                    expired: false
                },
                history: [{
                    action: 'created',
                    timestamp: timestamp.toISOString(),
                    details: { expirationMinutes, itemCount: items.length }
                }],
                totalValue: 0,
                metadata
            };

            // Reserve inventory for each item
            for (const item of reservation.items) {
                await this.reserveInventoryItem(item, reservationId, customerId);
            }

            // Calculate total value (placeholder - would come from item pricing)
            reservation.totalValue = await this.calculateReservationValue(reservation.items);

            // Store reservation
            await this.storeReservation(reservation);

            // Add to expiration queue
            this.scheduleExpiration(reservationId, expiresAt);

            // Emit reservation created event
            this.emit('reservation_created', reservation);

            // Send notifications
            await this.sendReservationNotification(reservation, 'created');

            // Notify location staff
            const locationIds = [...new Set(items.map(item => item.locationId))];
            for (const locationId of locationIds) {
                this.io.to(`location:${locationId}`).emit('reservation_created', {
                    reservationId,
                    customerId,
                    items: items.filter(item => item.locationId === locationId),
                    expiresAt: expiresAt.toISOString(),
                    timestamp: timestamp.toISOString()
                });
            }

            logger.logInventoryEvent('reservation_created', locationIds[0], customerId, {
                reservationId,
                itemCount: items.length,
                totalValue: reservation.totalValue,
                expiresAt: expiresAt.toISOString()
            });

            return reservation;

        } catch (error) {
            logger.error('Failed to create reservation', {
                reservationRequest,
                error: error.message,
                stack: error.stack
            });
            throw error;
        }
    }

    async confirmReservation(reservationId, confirmedBy, confirmationDetails = {}) {
        try {
            const reservation = await this.getReservation(reservationId);
            if (!reservation) {
                throw new Error(`Reservation not found: ${reservationId}`);
            }

            if (reservation.status !== 'active') {
                throw new Error(`Reservation ${reservationId} cannot be confirmed. Status: ${reservation.status}`);
            }

            const timestamp = new Date();

            // Update reservation status
            reservation.status = 'confirmed';
            reservation.confirmedAt = timestamp.toISOString();
            reservation.updatedAt = timestamp.toISOString();

            // Update item confirmation details
            for (const item of reservation.items) {
                const itemDetails = confirmationDetails.items?.find(i => i.itemId === item.itemId);
                if (itemDetails) {
                    item.confirmedQuantity = Math.min(itemDetails.confirmedQuantity || item.reservedQuantity, item.reservedQuantity);
                    item.notes = itemDetails.notes || '';
                    item.status = item.confirmedQuantity === item.reservedQuantity ? 'confirmed' : 'partially_confirmed';
                }
            }

            // Add to history
            reservation.history.push({
                action: 'confirmed',
                timestamp: timestamp.toISOString(),
                confirmedBy,
                details: confirmationDetails
            });

            // Update stored reservation
            await this.storeReservation(reservation);

            // Remove from expiration queue (confirmed reservations don't expire)
            this.cancelExpiration(reservationId);

            // Emit confirmation event
            this.emit('reservation_confirmed', reservation);

            // Send notifications
            await this.sendReservationNotification(reservation, 'confirmed');

            // Notify location staff
            const locationIds = [...new Set(reservation.items.map(item => item.locationId))];
            for (const locationId of locationIds) {
                this.io.to(`location:${locationId}`).emit('reservation_confirmed', {
                    reservationId,
                    confirmedBy,
                    timestamp: timestamp.toISOString()
                });
            }

            logger.logInventoryEvent('reservation_confirmed', locationIds[0], confirmedBy, {
                reservationId,
                customerId: reservation.customerId
            });

            return reservation;

        } catch (error) {
            logger.error('Failed to confirm reservation', {
                reservationId,
                confirmedBy,
                error: error.message
            });
            throw error;
        }
    }

    async cancelReservation(reservationId, cancelledBy, reason = 'customer_request') {
        try {
            const reservation = await this.getReservation(reservationId);
            if (!reservation) {
                throw new Error(`Reservation not found: ${reservationId}`);
            }

            if (!['active', 'confirmed'].includes(reservation.status)) {
                throw new Error(`Reservation ${reservationId} cannot be cancelled. Status: ${reservation.status}`);
            }

            const timestamp = new Date();

            // Update reservation status
            reservation.status = 'cancelled';
            reservation.cancelledAt = timestamp.toISOString();
            reservation.updatedAt = timestamp.toISOString();

            // Release reserved inventory
            for (const item of reservation.items) {
                await this.releaseReservedInventory(item, reservationId, reason);
            }

            // Add to history
            reservation.history.push({
                action: 'cancelled',
                timestamp: timestamp.toISOString(),
                cancelledBy,
                reason
            });

            // Update stored reservation
            await this.storeReservation(reservation);

            // Remove from expiration queue
            this.cancelExpiration(reservationId);

            // Emit cancellation event
            this.emit('reservation_cancelled', { reservation, reason, cancelledBy });

            // Send notifications
            await this.sendReservationNotification(reservation, 'cancelled', { reason });

            // Notify location staff
            const locationIds = [...new Set(reservation.items.map(item => item.locationId))];
            for (const locationId of locationIds) {
                this.io.to(`location:${locationId}`).emit('reservation_cancelled', {
                    reservationId,
                    reason,
                    cancelledBy,
                    timestamp: timestamp.toISOString()
                });
            }

            logger.logInventoryEvent('reservation_cancelled', locationIds[0], cancelledBy, {
                reservationId,
                customerId: reservation.customerId,
                reason
            });

            return reservation;

        } catch (error) {
            logger.error('Failed to cancel reservation', {
                reservationId,
                cancelledBy,
                reason,
                error: error.message
            });
            throw error;
        }
    }

    async fulfillReservation(reservationId, fulfilledBy, fulfillmentDetails = {}) {
        try {
            const reservation = await this.getReservation(reservationId);
            if (!reservation) {
                throw new Error(`Reservation not found: ${reservationId}`);
            }

            if (reservation.status !== 'confirmed') {
                throw new Error(`Reservation ${reservationId} must be confirmed before fulfillment. Status: ${reservation.status}`);
            }

            const timestamp = new Date();

            // Update reservation status
            reservation.status = 'fulfilled';
            reservation.fulfilledAt = timestamp.toISOString();
            reservation.updatedAt = timestamp.toISOString();

            // Process fulfillment for each item
            for (const item of reservation.items) {
                const itemDetails = fulfillmentDetails.items?.find(i => i.itemId === item.itemId);
                const fulfilledQuantity = itemDetails?.fulfilledQuantity || item.confirmedQuantity;

                // Track inventory change for fulfilled items
                await this.realTimeTracker.trackInventoryChange(
                    item.locationId,
                    item.itemId,
                    {
                        changeType: 'sale',
                        quantity: fulfilledQuantity,
                        reason: 'reservation_fulfilled',
                        userId: fulfilledBy,
                        transactionId: reservationId,
                        metadata: {
                            reservationId,
                            customerId: reservation.customerId,
                            originalReservedQuantity: item.reservedQuantity,
                            confirmedQuantity: item.confirmedQuantity
                        }
                    }
                );

                // Update item status
                item.fulfilledQuantity = fulfilledQuantity;
                item.status = 'fulfilled';
            }

            // Add to history
            reservation.history.push({
                action: 'fulfilled',
                timestamp: timestamp.toISOString(),
                fulfilledBy,
                details: fulfillmentDetails
            });

            // Update stored reservation
            await this.storeReservation(reservation);

            // Emit fulfillment event
            this.emit('reservation_fulfilled', reservation);

            // Send notifications
            await this.sendReservationNotification(reservation, 'fulfilled');

            // Notify location staff
            const locationIds = [...new Set(reservation.items.map(item => item.locationId))];
            for (const locationId of locationIds) {
                this.io.to(`location:${locationId}`).emit('reservation_fulfilled', {
                    reservationId,
                    fulfilledBy,
                    timestamp: timestamp.toISOString()
                });
            }

            logger.logInventoryEvent('reservation_fulfilled', locationIds[0], fulfilledBy, {
                reservationId,
                customerId: reservation.customerId,
                totalValue: reservation.totalValue
            });

            return reservation;

        } catch (error) {
            logger.error('Failed to fulfill reservation', {
                reservationId,
                fulfilledBy,
                error: error.message
            });
            throw error;
        }
    }

    async extendReservation(reservationId, extensionMinutes, extendedBy) {
        try {
            const reservation = await this.getReservation(reservationId);
            if (!reservation) {
                throw new Error(`Reservation not found: ${reservationId}`);
            }

            if (reservation.status !== 'active') {
                throw new Error(`Only active reservations can be extended. Status: ${reservation.status}`);
            }

            const timestamp = new Date();
            const currentExpiration = new Date(reservation.expiresAt);
            const newExpiration = moment(currentExpiration).add(extensionMinutes, 'minutes').toDate();

            // Update expiration
            reservation.expiresAt = newExpiration.toISOString();
            reservation.updatedAt = timestamp.toISOString();

            // Add to history
            reservation.history.push({
                action: 'extended',
                timestamp: timestamp.toISOString(),
                extendedBy,
                details: {
                    extensionMinutes,
                    previousExpiration: currentExpiration.toISOString(),
                    newExpiration: newExpiration.toISOString()
                }
            });

            // Update stored reservation
            await this.storeReservation(reservation);

            // Update expiration queue
            this.cancelExpiration(reservationId);
            this.scheduleExpiration(reservationId, newExpiration);

            // Send notifications
            await this.sendReservationNotification(reservation, 'extended', {
                extensionMinutes,
                newExpiration: newExpiration.toISOString()
            });

            logger.logInventoryEvent('reservation_extended', reservation.items[0]?.locationId || 'unknown', extendedBy, {
                reservationId,
                customerId: reservation.customerId,
                extensionMinutes,
                newExpiration: newExpiration.toISOString()
            });

            return reservation;

        } catch (error) {
            logger.error('Failed to extend reservation', {
                reservationId,
                extensionMinutes,
                extendedBy,
                error: error.message
            });
            throw error;
        }
    }

    async getCustomerReservations(customerId, options = {}) {
        try {
            const {
                status = null,
                limit = 50,
                offset = 0,
                sortBy = 'createdAt',
                sortOrder = 'desc'
            } = options;

            // Search for customer reservations
            const pattern = 'reservation:*';
            const keys = await this.redis.keys(pattern);
            
            const reservations = [];

            for (const key of keys) {
                const reservationData = await this.redis.hgetall(key);
                if (Object.keys(reservationData).length > 0) {
                    const reservation = this.parseReservationData(reservationData);
                    
                    if (reservation.customerId === customerId) {
                        if (!status || reservation.status === status) {
                            reservations.push(reservation);
                        }
                    }
                }
            }

            // Sort reservations
            reservations.sort((a, b) => {
                const aValue = new Date(a[sortBy]);
                const bValue = new Date(b[sortBy]);
                
                if (sortOrder === 'asc') {
                    return aValue - bValue;
                } else {
                    return bValue - aValue;
                }
            });

            // Apply pagination
            const paginatedReservations = reservations.slice(offset, offset + limit);

            return {
                customerId,
                reservations: paginatedReservations,
                total: reservations.length,
                limit,
                offset
            };

        } catch (error) {
            logger.error('Failed to get customer reservations', {
                customerId,
                options,
                error: error.message
            });
            throw error;
        }
    }

    async getLocationReservations(locationId, options = {}) {
        try {
            const {
                status = null,
                date = null,
                limit = 100,
                offset = 0
            } = options;

            const pattern = 'reservation:*';
            const keys = await this.redis.keys(pattern);
            
            const reservations = [];

            for (const key of keys) {
                const reservationData = await this.redis.hgetall(key);
                if (Object.keys(reservationData).length > 0) {
                    const reservation = this.parseReservationData(reservationData);
                    
                    // Check if reservation has items from this location
                    const hasLocationItems = reservation.items.some(item => item.locationId === locationId);
                    
                    if (hasLocationItems) {
                        if (!status || reservation.status === status) {
                            if (!date || moment(reservation.createdAt).format('YYYY-MM-DD') === date) {
                                reservations.push(reservation);
                            }
                        }
                    }
                }
            }

            // Sort by creation time (most recent first)
            reservations.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

            // Apply pagination
            const paginatedReservations = reservations.slice(offset, offset + limit);

            return {
                locationId,
                reservations: paginatedReservations,
                total: reservations.length,
                limit,
                offset
            };

        } catch (error) {
            logger.error('Failed to get location reservations', {
                locationId,
                options,
                error: error.message
            });
            throw error;
        }
    }

    async getReservation(reservationId) {
        if (this.reservations.has(reservationId)) {
            return this.reservations.get(reservationId);
        }

        // Load from Redis
        const reservationKey = `reservation:${reservationId}`;
        const reservationData = await this.redis.hgetall(reservationKey);

        if (Object.keys(reservationData).length === 0) {
            return null;
        }

        const reservation = this.parseReservationData(reservationData);
        this.reservations.set(reservationId, reservation);

        return reservation;
    }

    async validateReservationItems(items) {
        for (const item of items) {
            const { itemId, quantity, locationId } = item;

            if (!itemId || !quantity || !locationId) {
                throw new Error('Each item must have itemId, quantity, and locationId');
            }

            if (quantity <= 0) {
                throw new Error(`Invalid quantity for item ${itemId}: ${quantity}`);
            }

            // Check availability
            const stockLevel = await this.realTimeTracker.getRealtimeStockLevel(locationId, itemId);
            const reservedQuantity = await this.getReservedQuantityForItem(locationId, itemId);
            const availableQuantity = Math.max(0, stockLevel.quantity - reservedQuantity);

            if (availableQuantity < quantity) {
                throw new Error(`Insufficient inventory for item ${itemId} at location ${locationId}. Available: ${availableQuantity}, Requested: ${quantity}`);
            }
        }

        return true;
    }

    async reserveInventoryItem(item, reservationId, customerId) {
        // Create reservation record in Redis
        const reservationKey = `item_reservation:${item.locationId}:${item.itemId}:${reservationId}`;
        await this.redis.hmset(reservationKey, {
            reservationId,
            itemId: item.itemId,
            locationId: item.locationId,
            quantity: item.quantity,
            customerId,
            createdAt: new Date().toISOString(),
            expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString() // 1 hour default
        });

        // Set expiration for the key
        await this.redis.expire(reservationKey, 3600); // 1 hour

        // Track inventory change
        await this.realTimeTracker.trackInventoryChange(
            item.locationId,
            item.itemId,
            {
                changeType: 'reservation',
                quantity: item.quantity,
                reason: 'item_reserved',
                userId: customerId,
                transactionId: reservationId,
                metadata: {
                    reservationId,
                    customerId
                }
            }
        );
    }

    async releaseReservedInventory(item, reservationId, reason) {
        // Remove reservation record
        const reservationKey = `item_reservation:${item.locationId}:${item.itemId}:${reservationId}`;
        await this.redis.del(reservationKey);

        // Track inventory change
        await this.realTimeTracker.trackInventoryChange(
            item.locationId,
            item.itemId,
            {
                changeType: 'release_reservation',
                quantity: item.reservedQuantity,
                reason: `reservation_${reason}`,
                userId: 'system',
                transactionId: reservationId,
                metadata: {
                    reservationId,
                    originalReason: reason
                }
            }
        );
    }

    async getReservedQuantityForItem(locationId, itemId) {
        const pattern = `item_reservation:${locationId}:${itemId}:*`;
        const keys = await this.redis.keys(pattern);
        
        let totalReserved = 0;
        const now = new Date();

        for (const key of keys) {
            const reservationData = await this.redis.hgetall(key);
            if (Object.keys(reservationData).length > 0) {
                const expiresAt = new Date(reservationData.expiresAt);
                if (expiresAt > now) {
                    totalReserved += parseInt(reservationData.quantity, 10);
                }
            }
        }

        return totalReserved;
    }

    async calculateReservationValue(items) {
        // Placeholder for pricing calculation
        // In a real implementation, you would fetch item prices from a pricing service
        let totalValue = 0;
        
        for (const item of items) {
            // Mock price calculation
            const estimatedPrice = 10.00; // Would come from pricing service
            totalValue += estimatedPrice * item.quantity;
        }

        return totalValue;
    }

    scheduleExpiration(reservationId, expiresAt) {
        const timeToExpire = expiresAt.getTime() - Date.now();
        
        if (timeToExpire > 0) {
            const timeoutId = setTimeout(async () => {
                await this.expireReservation(reservationId);
            }, timeToExpire);

            this.expirationQueue.set(reservationId, {
                timeoutId,
                expiresAt
            });
        }
    }

    cancelExpiration(reservationId) {
        const expiration = this.expirationQueue.get(reservationId);
        if (expiration) {
            clearTimeout(expiration.timeoutId);
            this.expirationQueue.delete(reservationId);
        }
    }

    async expireReservation(reservationId) {
        try {
            const reservation = await this.getReservation(reservationId);
            if (!reservation || reservation.status !== 'active') {
                return;
            }

            const timestamp = new Date();

            // Update reservation status
            reservation.status = 'expired';
            reservation.updatedAt = timestamp.toISOString();

            // Release reserved inventory
            for (const item of reservation.items) {
                await this.releaseReservedInventory(item, reservationId, 'expired');
            }

            // Add to history
            reservation.history.push({
                action: 'expired',
                timestamp: timestamp.toISOString(),
                details: { autoExpired: true }
            });

            // Update stored reservation
            await this.storeReservation(reservation);

            // Remove from expiration queue
            this.expirationQueue.delete(reservationId);

            // Emit expiration event
            this.emit('reservation_expired', reservation);

            // Send notifications
            await this.sendReservationNotification(reservation, 'expired');

            // Notify location staff
            const locationIds = [...new Set(reservation.items.map(item => item.locationId))];
            for (const locationId of locationIds) {
                this.io.to(`location:${locationId}`).emit('reservation_expired', {
                    reservationId,
                    customerId: reservation.customerId,
                    timestamp: timestamp.toISOString()
                });
            }

            logger.logInventoryEvent('reservation_expired', locationIds[0], 'system', {
                reservationId,
                customerId: reservation.customerId
            });

        } catch (error) {
            logger.error('Failed to expire reservation', {
                reservationId,
                error: error.message
            });
        }
    }

    async storeReservation(reservation) {
        const reservationKey = `reservation:${reservation.reservationId}`;
        
        await this.redis.hmset(reservationKey, {
            reservationId: reservation.reservationId,
            customerId: reservation.customerId,
            items: JSON.stringify(reservation.items),
            reservationType: reservation.reservationType,
            status: reservation.status,
            priority: reservation.priority,
            notes: reservation.notes,
            customerInfo: JSON.stringify(reservation.customerInfo),
            contactPreferences: JSON.stringify(reservation.contactPreferences),
            createdAt: reservation.createdAt,
            updatedAt: reservation.updatedAt,
            expiresAt: reservation.expiresAt || '',
            confirmedAt: reservation.confirmedAt || '',
            cancelledAt: reservation.cancelledAt || '',
            fulfilledAt: reservation.fulfilledAt || '',
            pickupScheduledAt: reservation.pickupScheduledAt || '',
            notifications: JSON.stringify(reservation.notifications),
            history: JSON.stringify(reservation.history),
            totalValue: reservation.totalValue,
            metadata: JSON.stringify(reservation.metadata)
        });

        // Set expiration for the key (30 days)
        await this.redis.expire(reservationKey, 86400 * 30);

        // Update in-memory cache
        this.reservations.set(reservation.reservationId, reservation);
    }

    parseReservationData(reservationData) {
        return {
            ...reservationData,
            items: JSON.parse(reservationData.items || '[]'),
            customerInfo: JSON.parse(reservationData.customerInfo || '{}'),
            contactPreferences: JSON.parse(reservationData.contactPreferences || '{}'),
            notifications: JSON.parse(reservationData.notifications || '{}'),
            history: JSON.parse(reservationData.history || '[]'),
            totalValue: parseFloat(reservationData.totalValue || '0'),
            metadata: JSON.parse(reservationData.metadata || '{}')
        };
    }

    async sendReservationNotification(reservation, type, additionalData = {}) {
        // Placeholder for notification implementation
        // In a real system, this would integrate with email/SMS services
        
        const notificationData = {
            reservationId: reservation.reservationId,
            customerId: reservation.customerId,
            customerInfo: reservation.customerInfo,
            type,
            timestamp: new Date().toISOString(),
            ...additionalData
        };

        // Mark notification as sent
        reservation.notifications[type] = true;

        logger.debug('Reservation notification sent', {
            reservationId: reservation.reservationId,
            customerId: reservation.customerId,
            type,
            channels: Object.keys(reservation.contactPreferences).filter(
                key => reservation.contactPreferences[key]
            )
        });

        // Emit notification event for external handlers
        this.io.emit('reservation_notification', notificationData);
    }

    // Event handlers
    handleReservationCreated(reservation) {
        logger.logInventoryEvent('reservation_created', 'system', reservation.customerId, {
            reservationId: reservation.reservationId,
            itemCount: reservation.items.length,
            totalValue: reservation.totalValue
        });
    }

    handleReservationConfirmed(reservation) {
        logger.logInventoryEvent('reservation_confirmed', 'system', reservation.customerId, {
            reservationId: reservation.reservationId
        });
    }

    handleReservationExpired(reservation) {
        logger.logInventoryEvent('reservation_expired', 'system', 'system', {
            reservationId: reservation.reservationId,
            customerId: reservation.customerId
        });
    }

    handleReservationCancelled({ reservation, reason, cancelledBy }) {
        logger.logInventoryEvent('reservation_cancelled', 'system', cancelledBy, {
            reservationId: reservation.reservationId,
            customerId: reservation.customerId,
            reason
        });
    }

    handleReservationFulfilled(reservation) {
        logger.logInventoryEvent('reservation_fulfilled', 'system', 'system', {
            reservationId: reservation.reservationId,
            customerId: reservation.customerId,
            totalValue: reservation.totalValue
        });
    }

    startExpirationMonitoring() {
        // Check for expired reservations every 5 minutes
        setInterval(async () => {
            try {
                await this.cleanupExpiredReservations();
            } catch (error) {
                logger.error('Failed to cleanup expired reservations', error);
            }
        }, 300000); // 5 minutes

        // Send expiration warnings 10 minutes before expiration
        setInterval(async () => {
            try {
                await this.sendExpirationWarnings();
            } catch (error) {
                logger.error('Failed to send expiration warnings', error);
            }
        }, 60000); // 1 minute

        logger.info('Reservation expiration monitoring started');
    }

    async cleanupExpiredReservations() {
        const now = new Date();
        
        // Find all active reservations that might be expired
        const pattern = 'reservation:*';
        const keys = await this.redis.keys(pattern);

        for (const key of keys) {
            const reservationData = await this.redis.hgetall(key);
            if (Object.keys(reservationData).length > 0) {
                const reservation = this.parseReservationData(reservationData);
                
                if (reservation.status === 'active' && 
                    reservation.expiresAt && 
                    new Date(reservation.expiresAt) <= now) {
                    await this.expireReservation(reservation.reservationId);
                }
            }
        }
    }

    async sendExpirationWarnings() {
        const warningThreshold = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes from now
        const pattern = 'reservation:*';
        const keys = await this.redis.keys(pattern);

        for (const key of keys) {
            const reservationData = await this.redis.hgetall(key);
            if (Object.keys(reservationData).length > 0) {
                const reservation = this.parseReservationData(reservationData);
                
                if (reservation.status === 'active' && 
                    reservation.expiresAt && 
                    !reservation.notifications.expiring &&
                    new Date(reservation.expiresAt) <= warningThreshold) {
                    
                    await this.sendReservationNotification(reservation, 'expiring', {
                        expiresAt: reservation.expiresAt
                    });
                    
                    // Update the reservation to mark warning as sent
                    reservation.notifications.expiring = true;
                    await this.storeReservation(reservation);
                }
            }
        }
    }

    async getReservationMetrics(options = {}) {
        const {
            locationId = null,
            startDate = new Date(Date.now() - 24 * 60 * 60 * 1000), // 24 hours ago
            endDate = new Date()
        } = options;

        const metrics = {
            totalReservations: 0,
            activeReservations: 0,
            confirmedReservations: 0,
            expiredReservations: 0,
            cancelledReservations: 0,
            fulfilledReservations: 0,
            averageReservationValue: 0,
            totalReservationValue: 0,
            fulfillmentRate: 0,
            cancellationRate: 0,
            expirationRate: 0,
            timestamp: new Date().toISOString()
        };

        // Get all reservations within date range
        const pattern = 'reservation:*';
        const keys = await this.redis.keys(pattern);
        
        let totalValue = 0;
        let reservationCount = 0;

        for (const key of keys) {
            const reservationData = await this.redis.hgetall(key);
            if (Object.keys(reservationData).length > 0) {
                const reservation = this.parseReservationData(reservationData);
                const createdAt = new Date(reservation.createdAt);
                
                // Filter by date range
                if (createdAt >= startDate && createdAt <= endDate) {
                    // Filter by location if specified
                    if (!locationId || reservation.items.some(item => item.locationId === locationId)) {
                        metrics.totalReservations++;
                        reservationCount++;
                        totalValue += reservation.totalValue;
                        
                        switch (reservation.status) {
                            case 'active':
                                metrics.activeReservations++;
                                break;
                            case 'confirmed':
                                metrics.confirmedReservations++;
                                break;
                            case 'expired':
                                metrics.expiredReservations++;
                                break;
                            case 'cancelled':
                                metrics.cancelledReservations++;
                                break;
                            case 'fulfilled':
                                metrics.fulfilledReservations++;
                                break;
                        }
                    }
                }
            }
        }

        // Calculate rates and averages
        if (reservationCount > 0) {
            metrics.averageReservationValue = totalValue / reservationCount;
            metrics.totalReservationValue = totalValue;
            metrics.fulfillmentRate = (metrics.fulfilledReservations / reservationCount) * 100;
            metrics.cancellationRate = (metrics.cancelledReservations / reservationCount) * 100;
            metrics.expirationRate = (metrics.expiredReservations / reservationCount) * 100;
        }

        return metrics;
    }
}

module.exports = ReservationManager;