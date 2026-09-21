const { v4: uuidv4 } = require('uuid');
const moment = require('moment-timezone');
const logger = require('../config/logger');
const redis = require('../config/redis');
const EventEmitter = require('events');

class PickupScheduler extends EventEmitter {
    constructor(socketIO, reservationManager, multiLocationManager) {
        super();
        this.io = socketIO;
        this.reservationManager = reservationManager;
        this.multiLocationManager = multiLocationManager;
        this.redis = redis.client;
        this.pickupSchedules = new Map();
        this.timeSlots = new Map();
        this.locationCapacities = new Map();
        this.recurringSchedules = new Map();

        this.setupEventHandlers();
        this.initializeDefaultTimeSlots();
        this.startScheduleMonitoring();
    }

    setupEventHandlers() {
        this.on('pickup_scheduled', this.handlePickupScheduled.bind(this));
        this.on('pickup_confirmed', this.handlePickupConfirmed.bind(this));
        this.on('pickup_completed', this.handlePickupCompleted.bind(this));
        this.on('pickup_cancelled', this.handlePickupCancelled.bind(this));
        this.on('pickup_rescheduled', this.handlePickupRescheduled.bind(this));
        this.on('pickup_reminder_due', this.handlePickupReminderDue.bind(this));
    }

    async schedulePickup(pickupRequest) {
        const pickupId = uuidv4();
        const timestamp = new Date();

        try {
            const {
                reservationId,
                customerId,
                locationId,
                preferredDate,
                preferredTimeSlot,
                alternativeTimeSlots = [],
                specialInstructions = '',
                vehicleType = 'standard',
                estimatedDuration = 30,
                priority = 'normal',
                contactInfo = {},
                metadata = {}
            } = pickupRequest;

            // Validate reservation exists and is confirmed
            const reservation = await this.reservationManager.getReservation(reservationId);
            if (!reservation) {
                throw new Error(`Reservation not found: ${reservationId}`);
            }

            if (reservation.status !== 'confirmed') {
                throw new Error(`Reservation must be confirmed before scheduling pickup. Status: ${reservation.status}`);
            }

            // Find available time slot
            const timeSlot = await this.findAvailableTimeSlot(
                locationId,
                preferredDate,
                preferredTimeSlot,
                estimatedDuration,
                alternativeTimeSlots
            );

            if (!timeSlot) {
                throw new Error(`No available time slots found for the requested date and location`);
            }

            // Create pickup schedule
            const pickup = {
                pickupId,
                reservationId,
                customerId,
                locationId,
                scheduledDate: timeSlot.date,
                timeSlot: {
                    id: timeSlot.id,
                    startTime: timeSlot.startTime,
                    endTime: timeSlot.endTime,
                    duration: estimatedDuration
                },
                status: 'scheduled',
                priority,
                specialInstructions,
                vehicleType,
                estimatedDuration,
                contactInfo: {
                    name: contactInfo.name || reservation.customerInfo.name,
                    phone: contactInfo.phone || reservation.customerInfo.phone,
                    email: contactInfo.email || reservation.customerInfo.email,
                    alternatePhone: contactInfo.alternatePhone || reservation.customerInfo.alternatePhone,
                    ...contactInfo
                },
                items: reservation.items.filter(item => item.locationId === locationId),
                notifications: {
                    scheduled: false,
                    reminder24h: false,
                    reminder1h: false,
                    arrived: false,
                    completed: false
                },
                history: [{
                    action: 'scheduled',
                    timestamp: timestamp.toISOString(),
                    details: {
                        originalPreferredDate: preferredDate,
                        originalPreferredTimeSlot: preferredTimeSlot,
                        assignedTimeSlot: timeSlot
                    }
                }],
                createdAt: timestamp.toISOString(),
                updatedAt: timestamp.toISOString(),
                scheduledAt: timestamp.toISOString(),
                confirmedAt: null,
                arrivedAt: null,
                completedAt: null,
                cancelledAt: null,
                metadata
            };

            // Reserve time slot
            await this.reserveTimeSlot(locationId, timeSlot.id, pickupId, estimatedDuration);

            // Store pickup schedule
            await this.storePickupSchedule(pickup);

            // Update reservation with pickup information
            await this.linkReservationToPickup(reservationId, pickupId, timeSlot);

            // Emit pickup scheduled event
            this.emit('pickup_scheduled', pickup);

            // Send notifications
            await this.sendPickupNotification(pickup, 'scheduled');

            // Schedule reminders
            await this.schedulePickupReminders(pickup);

            // Notify location staff
            this.io.to(`location:${locationId}`).emit('pickup_scheduled', {
                pickupId,
                customerId,
                reservationId,
                timeSlot: pickup.timeSlot,
                items: pickup.items,
                specialInstructions,
                timestamp: timestamp.toISOString()
            });

            logger.logPickupEvent('pickup_scheduled', pickupId, {
                locationId,
                customerId,
                reservationId,
                scheduledDate: pickup.scheduledDate,
                timeSlot: pickup.timeSlot
            });

            return pickup;

        } catch (error) {
            logger.error('Failed to schedule pickup', {
                pickupRequest,
                error: error.message,
                stack: error.stack
            });
            throw error;
        }
    }

    async findAvailableTimeSlot(locationId, preferredDate, preferredTimeSlot, duration, alternatives = []) {
        try {
            const location = await this.multiLocationManager.getLocationInfo(locationId);
            if (!location) {
                throw new Error(`Location not found: ${locationId}`);
            }

            const targetDate = moment.tz(preferredDate, location.timezone);
            const timeSlotsForLocation = await this.getLocationTimeSlots(locationId);
            
            // Try preferred time slot first
            if (preferredTimeSlot) {
                const slot = await this.checkTimeSlotAvailability(
                    locationId,
                    targetDate.format('YYYY-MM-DD'),
                    preferredTimeSlot,
                    duration
                );
                
                if (slot) {
                    return {
                        id: `${targetDate.format('YYYY-MM-DD')}_${preferredTimeSlot}`,
                        date: targetDate.format('YYYY-MM-DD'),
                        startTime: preferredTimeSlot,
                        endTime: moment(preferredTimeSlot, 'HH:mm').add(duration, 'minutes').format('HH:mm'),
                        available: true
                    };
                }
            }

            // Try alternative time slots
            for (const altTimeSlot of alternatives) {
                const slot = await this.checkTimeSlotAvailability(
                    locationId,
                    targetDate.format('YYYY-MM-DD'),
                    altTimeSlot,
                    duration
                );
                
                if (slot) {
                    return {
                        id: `${targetDate.format('YYYY-MM-DD')}_${altTimeSlot}`,
                        date: targetDate.format('YYYY-MM-DD'),
                        startTime: altTimeSlot,
                        endTime: moment(altTimeSlot, 'HH:mm').add(duration, 'minutes').format('HH:mm'),
                        available: true
                    };
                }
            }

            // Find any available slot for the day
            const availableSlots = await this.getAvailableTimeSlotsForDate(locationId, targetDate.format('YYYY-MM-DD'), duration);
            
            if (availableSlots.length > 0) {
                const firstAvailable = availableSlots[0];
                return {
                    id: `${targetDate.format('YYYY-MM-DD')}_${firstAvailable.startTime}`,
                    date: targetDate.format('YYYY-MM-DD'),
                    startTime: firstAvailable.startTime,
                    endTime: firstAvailable.endTime,
                    available: true
                };
            }

            // Try next few days if nothing available today
            for (let i = 1; i <= 7; i++) {
                const nextDate = moment(targetDate).add(i, 'days');
                const nextDaySlots = await this.getAvailableTimeSlotsForDate(
                    locationId, 
                    nextDate.format('YYYY-MM-DD'), 
                    duration
                );
                
                if (nextDaySlots.length > 0) {
                    const firstAvailable = nextDaySlots[0];
                    return {
                        id: `${nextDate.format('YYYY-MM-DD')}_${firstAvailable.startTime}`,
                        date: nextDate.format('YYYY-MM-DD'),
                        startTime: firstAvailable.startTime,
                        endTime: firstAvailable.endTime,
                        available: true
                    };
                }
            }

            return null; // No slots available

        } catch (error) {
            logger.error('Failed to find available time slot', {
                locationId,
                preferredDate,
                preferredTimeSlot,
                duration,
                error: error.message
            });
            throw error;
        }
    }

    async getAvailableTimeSlotsForDate(locationId, date, duration) {
        try {
            const location = await this.multiLocationManager.getLocationInfo(locationId);
            const operatingHours = location.operatingHours;
            
            // Get day of week
            const dayOfWeek = moment(date).format('dddd').toLowerCase();
            const hoursForDay = operatingHours[dayOfWeek];
            
            if (!hoursForDay || !hoursForDay.open || !hoursForDay.close) {
                return []; // Location closed on this day
            }

            // Generate time slots for the day
            const openTime = moment(`${date} ${hoursForDay.open}`);
            const closeTime = moment(`${date} ${hoursForDay.close}`);
            const slotDuration = 30; // 30 minute slots
            
            const availableSlots = [];
            let currentSlot = openTime.clone();

            while (currentSlot.clone().add(duration, 'minutes').isSameOrBefore(closeTime)) {
                const slotId = `${date}_${currentSlot.format('HH:mm')}`;
                const isAvailable = await this.isTimeSlotAvailable(locationId, slotId, duration);
                
                if (isAvailable) {
                    availableSlots.push({
                        startTime: currentSlot.format('HH:mm'),
                        endTime: currentSlot.clone().add(duration, 'minutes').format('HH:mm'),
                        available: true,
                        capacity: await this.getSlotCapacity(locationId, slotId)
                    });
                }

                currentSlot.add(slotDuration, 'minutes');
            }

            return availableSlots;

        } catch (error) {
            logger.error('Failed to get available time slots for date', {
                locationId,
                date,
                duration,
                error: error.message
            });
            throw error;
        }
    }

    async checkTimeSlotAvailability(locationId, date, timeSlot, duration) {
        const slotId = `${date}_${timeSlot}`;
        return await this.isTimeSlotAvailable(locationId, slotId, duration);
    }

    async isTimeSlotAvailable(locationId, slotId, duration) {
        try {
            const slotKey = `timeslot:${locationId}:${slotId}`;
            const slotData = await this.redis.hgetall(slotKey);
            
            const maxCapacity = await this.getSlotCapacity(locationId, slotId);
            const currentBookings = parseInt(slotData.bookings || '0', 10);
            
            return currentBookings < maxCapacity;

        } catch (error) {
            logger.error('Failed to check time slot availability', {
                locationId,
                slotId,
                duration,
                error: error.message
            });
            return false;
        }
    }

    async reserveTimeSlot(locationId, slotId, pickupId, duration) {
        const slotKey = `timeslot:${locationId}:${slotId}`;
        const pickupKey = `timeslot_pickup:${locationId}:${slotId}:${pickupId}`;
        
        // Increment bookings count
        await this.redis.hincrby(slotKey, 'bookings', 1);
        
        // Store pickup association
        await this.redis.hmset(pickupKey, {
            pickupId,
            locationId,
            slotId,
            duration,
            reservedAt: new Date().toISOString()
        });
        
        // Set expiration (24 hours after the slot time)
        await this.redis.expire(pickupKey, 86400);
    }

    async releaseTimeSlot(locationId, slotId, pickupId) {
        const slotKey = `timeslot:${locationId}:${slotId}`;
        const pickupKey = `timeslot_pickup:${locationId}:${slotId}:${pickupId}`;
        
        // Decrement bookings count
        await this.redis.hincrby(slotKey, 'bookings', -1);
        
        // Remove pickup association
        await this.redis.del(pickupKey);
    }

    async getSlotCapacity(locationId, slotId) {
        // Default capacity - could be customized per location/time slot
        const location = await this.multiLocationManager.getLocationInfo(locationId);
        return location?.settings?.pickupCapacityPerSlot || 5;
    }

    async confirmPickup(pickupId, confirmedBy) {
        try {
            const pickup = await this.getPickupSchedule(pickupId);
            if (!pickup) {
                throw new Error(`Pickup not found: ${pickupId}`);
            }

            if (pickup.status !== 'scheduled') {
                throw new Error(`Pickup cannot be confirmed. Current status: ${pickup.status}`);
            }

            const timestamp = new Date();

            // Update pickup status
            pickup.status = 'confirmed';
            pickup.confirmedAt = timestamp.toISOString();
            pickup.updatedAt = timestamp.toISOString();

            // Add to history
            pickup.history.push({
                action: 'confirmed',
                timestamp: timestamp.toISOString(),
                confirmedBy
            });

            // Store updated pickup
            await this.storePickupSchedule(pickup);

            // Emit confirmation event
            this.emit('pickup_confirmed', pickup);

            // Send notifications
            await this.sendPickupNotification(pickup, 'confirmed');

            // Notify location staff
            this.io.to(`location:${pickup.locationId}`).emit('pickup_confirmed', {
                pickupId,
                confirmedBy,
                timestamp: timestamp.toISOString()
            });

            logger.logPickupEvent('pickup_confirmed', pickupId, {
                locationId: pickup.locationId,
                customerId: pickup.customerId,
                confirmedBy
            });

            return pickup;

        } catch (error) {
            logger.error('Failed to confirm pickup', {
                pickupId,
                confirmedBy,
                error: error.message
            });
            throw error;
        }
    }

    async recordCustomerArrival(pickupId, arrivedBy) {
        try {
            const pickup = await this.getPickupSchedule(pickupId);
            if (!pickup) {
                throw new Error(`Pickup not found: ${pickupId}`);
            }

            if (!['confirmed', 'scheduled'].includes(pickup.status)) {
                throw new Error(`Cannot record arrival for pickup with status: ${pickup.status}`);
            }

            const timestamp = new Date();

            // Update pickup status
            pickup.status = 'customer_arrived';
            pickup.arrivedAt = timestamp.toISOString();
            pickup.updatedAt = timestamp.toISOString();

            // Add to history
            pickup.history.push({
                action: 'customer_arrived',
                timestamp: timestamp.toISOString(),
                arrivedBy
            });

            // Store updated pickup
            await this.storePickupSchedule(pickup);

            // Send notifications
            await this.sendPickupNotification(pickup, 'arrived');

            // Notify location staff
            this.io.to(`location:${pickup.locationId}`).emit('customer_arrived', {
                pickupId,
                customerId: pickup.customerId,
                timeSlot: pickup.timeSlot,
                items: pickup.items,
                specialInstructions: pickup.specialInstructions,
                timestamp: timestamp.toISOString()
            });

            // Notify customer
            this.io.to(`customer:${pickup.customerId}`).emit('arrival_acknowledged', {
                pickupId,
                estimatedWaitTime: 5, // Could be calculated based on current queue
                timestamp: timestamp.toISOString()
            });

            logger.logPickupEvent('customer_arrived', pickupId, {
                locationId: pickup.locationId,
                customerId: pickup.customerId,
                arrivedBy
            });

            return pickup;

        } catch (error) {
            logger.error('Failed to record customer arrival', {
                pickupId,
                arrivedBy,
                error: error.message
            });
            throw error;
        }
    }

    async completePickup(pickupId, completedBy, completionDetails = {}) {
        try {
            const pickup = await this.getPickupSchedule(pickupId);
            if (!pickup) {
                throw new Error(`Pickup not found: ${pickupId}`);
            }

            if (pickup.status !== 'customer_arrived') {
                throw new Error(`Pickup must be in customer_arrived status to complete. Current: ${pickup.status}`);
            }

            const timestamp = new Date();

            // Update pickup status
            pickup.status = 'completed';
            pickup.completedAt = timestamp.toISOString();
            pickup.updatedAt = timestamp.toISOString();

            // Store completion details
            pickup.completionDetails = {
                completedBy,
                actualCompletionTime: timestamp.toISOString(),
                itemsPickedUp: completionDetails.itemsPickedUp || pickup.items,
                customerSatisfaction: completionDetails.customerSatisfaction,
                notes: completionDetails.notes || '',
                ...completionDetails
            };

            // Add to history
            pickup.history.push({
                action: 'completed',
                timestamp: timestamp.toISOString(),
                completedBy,
                details: pickup.completionDetails
            });

            // Store updated pickup
            await this.storePickupSchedule(pickup);

            // Release time slot
            await this.releaseTimeSlot(pickup.locationId, pickup.timeSlot.id, pickupId);

            // Fulfill the reservation
            await this.reservationManager.fulfillReservation(
                pickup.reservationId,
                completedBy,
                {
                    items: pickup.completionDetails.itemsPickedUp.map(item => ({
                        itemId: item.itemId,
                        fulfilledQuantity: item.quantity
                    })),
                    pickupId,
                    completedAt: timestamp.toISOString()
                }
            );

            // Emit completion event
            this.emit('pickup_completed', pickup);

            // Send notifications
            await this.sendPickupNotification(pickup, 'completed');

            // Notify location staff and customer
            this.io.to(`location:${pickup.locationId}`).emit('pickup_completed', {
                pickupId,
                customerId: pickup.customerId,
                completedBy,
                timestamp: timestamp.toISOString()
            });

            this.io.to(`customer:${pickup.customerId}`).emit('pickup_completed', {
                pickupId,
                reservationId: pickup.reservationId,
                completionDetails: pickup.completionDetails,
                timestamp: timestamp.toISOString()
            });

            logger.logPickupEvent('pickup_completed', pickupId, {
                locationId: pickup.locationId,
                customerId: pickup.customerId,
                completedBy,
                duration: moment(pickup.completedAt).diff(moment(pickup.arrivedAt), 'minutes')
            });

            return pickup;

        } catch (error) {
            logger.error('Failed to complete pickup', {
                pickupId,
                completedBy,
                error: error.message
            });
            throw error;
        }
    }

    async cancelPickup(pickupId, cancelledBy, reason = 'customer_request') {
        try {
            const pickup = await this.getPickupSchedule(pickupId);
            if (!pickup) {
                throw new Error(`Pickup not found: ${pickupId}`);
            }

            if (['completed', 'cancelled'].includes(pickup.status)) {
                throw new Error(`Pickup cannot be cancelled. Current status: ${pickup.status}`);
            }

            const timestamp = new Date();

            // Update pickup status
            pickup.status = 'cancelled';
            pickup.cancelledAt = timestamp.toISOString();
            pickup.updatedAt = timestamp.toISOString();

            // Add to history
            pickup.history.push({
                action: 'cancelled',
                timestamp: timestamp.toISOString(),
                cancelledBy,
                reason
            });

            // Store updated pickup
            await this.storePickupSchedule(pickup);

            // Release time slot
            await this.releaseTimeSlot(pickup.locationId, pickup.timeSlot.id, pickupId);

            // Cancel pickup reminders
            await this.cancelPickupReminders(pickupId);

            // Emit cancellation event
            this.emit('pickup_cancelled', { pickup, reason, cancelledBy });

            // Send notifications
            await this.sendPickupNotification(pickup, 'cancelled', { reason });

            // Notify location staff
            this.io.to(`location:${pickup.locationId}`).emit('pickup_cancelled', {
                pickupId,
                reason,
                cancelledBy,
                timestamp: timestamp.toISOString()
            });

            logger.logPickupEvent('pickup_cancelled', pickupId, {
                locationId: pickup.locationId,
                customerId: pickup.customerId,
                cancelledBy,
                reason
            });

            return pickup;

        } catch (error) {
            logger.error('Failed to cancel pickup', {
                pickupId,
                cancelledBy,
                reason,
                error: error.message
            });
            throw error;
        }
    }

    async reschedulePickup(pickupId, newDate, newTimeSlot, rescheduledBy) {
        try {
            const pickup = await this.getPickupSchedule(pickupId);
            if (!pickup) {
                throw new Error(`Pickup not found: ${pickupId}`);
            }

            if (!['scheduled', 'confirmed'].includes(pickup.status)) {
                throw new Error(`Pickup cannot be rescheduled. Current status: ${pickup.status}`);
            }

            // Find new available time slot
            const newSlot = await this.findAvailableTimeSlot(
                pickup.locationId,
                newDate,
                newTimeSlot,
                pickup.estimatedDuration
            );

            if (!newSlot) {
                throw new Error(`No available time slot found for the new date and time`);
            }

            const timestamp = new Date();
            const oldSlot = pickup.timeSlot;

            // Release old time slot
            await this.releaseTimeSlot(pickup.locationId, oldSlot.id, pickupId);

            // Reserve new time slot
            await this.reserveTimeSlot(pickup.locationId, newSlot.id, pickupId, pickup.estimatedDuration);

            // Update pickup with new schedule
            pickup.scheduledDate = newSlot.date;
            pickup.timeSlot = {
                id: newSlot.id,
                startTime: newSlot.startTime,
                endTime: newSlot.endTime,
                duration: pickup.estimatedDuration
            };
            pickup.updatedAt = timestamp.toISOString();

            // Add to history
            pickup.history.push({
                action: 'rescheduled',
                timestamp: timestamp.toISOString(),
                rescheduledBy,
                details: {
                    oldDate: oldSlot.date || pickup.scheduledDate,
                    oldTimeSlot: oldSlot,
                    newDate: newSlot.date,
                    newTimeSlot: newSlot
                }
            });

            // Store updated pickup
            await this.storePickupSchedule(pickup);

            // Cancel old reminders and schedule new ones
            await this.cancelPickupReminders(pickupId);
            await this.schedulePickupReminders(pickup);

            // Emit rescheduling event
            this.emit('pickup_rescheduled', pickup);

            // Send notifications
            await this.sendPickupNotification(pickup, 'rescheduled', {
                oldTimeSlot: oldSlot,
                newTimeSlot: newSlot
            });

            // Notify location staff
            this.io.to(`location:${pickup.locationId}`).emit('pickup_rescheduled', {
                pickupId,
                oldTimeSlot: oldSlot,
                newTimeSlot: pickup.timeSlot,
                rescheduledBy,
                timestamp: timestamp.toISOString()
            });

            logger.logPickupEvent('pickup_rescheduled', pickupId, {
                locationId: pickup.locationId,
                customerId: pickup.customerId,
                rescheduledBy,
                oldDate: oldSlot.date || pickup.scheduledDate,
                newDate: pickup.scheduledDate
            });

            return pickup;

        } catch (error) {
            logger.error('Failed to reschedule pickup', {
                pickupId,
                newDate,
                newTimeSlot,
                rescheduledBy,
                error: error.message
            });
            throw error;
        }
    }

    async getPickupSchedule(pickupId) {
        if (this.pickupSchedules.has(pickupId)) {
            return this.pickupSchedules.get(pickupId);
        }

        // Load from Redis
        const pickupKey = `pickup:${pickupId}`;
        const pickupData = await this.redis.hgetall(pickupKey);

        if (Object.keys(pickupData).length === 0) {
            return null;
        }

        const pickup = this.parsePickupData(pickupData);
        this.pickupSchedules.set(pickupId, pickup);

        return pickup;
    }

    async getLocationPickups(locationId, date = null, status = null) {
        try {
            const pattern = 'pickup:*';
            const keys = await this.redis.keys(pattern);
            
            const pickups = [];

            for (const key of keys) {
                const pickupData = await this.redis.hgetall(key);
                if (Object.keys(pickupData).length > 0) {
                    const pickup = this.parsePickupData(pickupData);
                    
                    if (pickup.locationId === locationId) {
                        if (!date || pickup.scheduledDate === date) {
                            if (!status || pickup.status === status) {
                                pickups.push(pickup);
                            }
                        }
                    }
                }
            }

            // Sort by scheduled time
            pickups.sort((a, b) => {
                const aTime = moment(`${a.scheduledDate} ${a.timeSlot.startTime}`);
                const bTime = moment(`${b.scheduledDate} ${b.timeSlot.startTime}`);
                return aTime - bTime;
            });

            return pickups;

        } catch (error) {
            logger.error('Failed to get location pickups', {
                locationId,
                date,
                status,
                error: error.message
            });
            throw error;
        }
    }

    async getCustomerPickups(customerId, options = {}) {
        try {
            const {
                limit = 50,
                offset = 0,
                status = null,
                sortOrder = 'desc'
            } = options;

            const pattern = 'pickup:*';
            const keys = await this.redis.keys(pattern);
            
            const pickups = [];

            for (const key of keys) {
                const pickupData = await this.redis.hgetall(key);
                if (Object.keys(pickupData).length > 0) {
                    const pickup = this.parsePickupData(pickupData);
                    
                    if (pickup.customerId === customerId) {
                        if (!status || pickup.status === status) {
                            pickups.push(pickup);
                        }
                    }
                }
            }

            // Sort by creation time
            pickups.sort((a, b) => {
                const aTime = new Date(a.createdAt);
                const bTime = new Date(b.createdAt);
                return sortOrder === 'asc' ? aTime - bTime : bTime - aTime;
            });

            // Apply pagination
            const paginatedPickups = pickups.slice(offset, offset + limit);

            return {
                customerId,
                pickups: paginatedPickups,
                total: pickups.length,
                limit,
                offset
            };

        } catch (error) {
            logger.error('Failed to get customer pickups', {
                customerId,
                options,
                error: error.message
            });
            throw error;
        }
    }

    async storePickupSchedule(pickup) {
        const pickupKey = `pickup:${pickup.pickupId}`;
        
        await this.redis.hmset(pickupKey, {
            pickupId: pickup.pickupId,
            reservationId: pickup.reservationId,
            customerId: pickup.customerId,
            locationId: pickup.locationId,
            scheduledDate: pickup.scheduledDate,
            timeSlot: JSON.stringify(pickup.timeSlot),
            status: pickup.status,
            priority: pickup.priority,
            specialInstructions: pickup.specialInstructions,
            vehicleType: pickup.vehicleType,
            estimatedDuration: pickup.estimatedDuration,
            contactInfo: JSON.stringify(pickup.contactInfo),
            items: JSON.stringify(pickup.items),
            notifications: JSON.stringify(pickup.notifications),
            history: JSON.stringify(pickup.history),
            createdAt: pickup.createdAt,
            updatedAt: pickup.updatedAt,
            scheduledAt: pickup.scheduledAt || '',
            confirmedAt: pickup.confirmedAt || '',
            arrivedAt: pickup.arrivedAt || '',
            completedAt: pickup.completedAt || '',
            cancelledAt: pickup.cancelledAt || '',
            completionDetails: JSON.stringify(pickup.completionDetails || {}),
            metadata: JSON.stringify(pickup.metadata || {})
        });

        // Set expiration (30 days)
        await this.redis.expire(pickupKey, 86400 * 30);

        // Update in-memory cache
        this.pickupSchedules.set(pickup.pickupId, pickup);
    }

    parsePickupData(pickupData) {
        return {
            ...pickupData,
            timeSlot: JSON.parse(pickupData.timeSlot || '{}'),
            estimatedDuration: parseInt(pickupData.estimatedDuration, 10),
            contactInfo: JSON.parse(pickupData.contactInfo || '{}'),
            items: JSON.parse(pickupData.items || '[]'),
            notifications: JSON.parse(pickupData.notifications || '{}'),
            history: JSON.parse(pickupData.history || '[]'),
            completionDetails: JSON.parse(pickupData.completionDetails || '{}'),
            metadata: JSON.parse(pickupData.metadata || '{}')
        };
    }

    async linkReservationToPickup(reservationId, pickupId, timeSlot) {
        // Update reservation with pickup information
        const reservation = await this.reservationManager.getReservation(reservationId);
        if (reservation) {
            reservation.pickupScheduledAt = new Date().toISOString();
            reservation.pickupId = pickupId;
            reservation.pickupTimeSlot = timeSlot;
            
            // Add to reservation history
            reservation.history.push({
                action: 'pickup_scheduled',
                timestamp: new Date().toISOString(),
                details: { pickupId, timeSlot }
            });

            await this.reservationManager.storeReservation(reservation);
        }
    }

    async sendPickupNotification(pickup, type, additionalData = {}) {
        // Placeholder for notification implementation
        const notificationData = {
            pickupId: pickup.pickupId,
            customerId: pickup.customerId,
            reservationId: pickup.reservationId,
            type,
            timestamp: new Date().toISOString(),
            ...additionalData
        };

        // Mark notification as sent
        pickup.notifications[type] = true;

        logger.debug('Pickup notification sent', {
            pickupId: pickup.pickupId,
            customerId: pickup.customerId,
            type
        });

        // Emit notification event
        this.io.emit('pickup_notification', notificationData);
    }

    async schedulePickupReminders(pickup) {
        const scheduledDateTime = moment(`${pickup.scheduledDate} ${pickup.timeSlot.startTime}`);
        
        // 24 hour reminder
        const reminder24h = scheduledDateTime.clone().subtract(24, 'hours');
        if (reminder24h.isAfter(moment())) {
            setTimeout(async () => {
                await this.sendPickupReminder(pickup.pickupId, '24h');
            }, reminder24h.diff(moment()));
        }

        // 1 hour reminder
        const reminder1h = scheduledDateTime.clone().subtract(1, 'hour');
        if (reminder1h.isAfter(moment())) {
            setTimeout(async () => {
                await this.sendPickupReminder(pickup.pickupId, '1h');
            }, reminder1h.diff(moment()));
        }
    }

    async cancelPickupReminders(pickupId) {
        // In a production system, you would cancel the scheduled reminders
        // For now, just log the cancellation
        logger.debug('Pickup reminders cancelled', { pickupId });
    }

    async sendPickupReminder(pickupId, reminderType) {
        try {
            const pickup = await this.getPickupSchedule(pickupId);
            if (!pickup || pickup.status !== 'confirmed') {
                return;
            }

            const reminderKey = `reminder${reminderType === '24h' ? '24h' : '1h'}`;
            
            if (!pickup.notifications[reminderKey]) {
                await this.sendPickupNotification(pickup, 'reminder', {
                    reminderType,
                    scheduledDateTime: `${pickup.scheduledDate} ${pickup.timeSlot.startTime}`
                });

                pickup.notifications[reminderKey] = true;
                await this.storePickupSchedule(pickup);

                this.emit('pickup_reminder_due', { pickup, reminderType });
            }

        } catch (error) {
            logger.error('Failed to send pickup reminder', {
                pickupId,
                reminderType,
                error: error.message
            });
        }
    }

    // Event handlers
    handlePickupScheduled(pickup) {
        logger.logPickupEvent('pickup_scheduled', pickup.pickupId, {
            locationId: pickup.locationId,
            customerId: pickup.customerId
        });
    }

    handlePickupConfirmed(pickup) {
        logger.logPickupEvent('pickup_confirmed', pickup.pickupId, {
            locationId: pickup.locationId,
            customerId: pickup.customerId
        });
    }

    handlePickupCompleted(pickup) {
        logger.logPickupEvent('pickup_completed', pickup.pickupId, {
            locationId: pickup.locationId,
            customerId: pickup.customerId
        });
    }

    handlePickupCancelled({ pickup, reason, cancelledBy }) {
        logger.logPickupEvent('pickup_cancelled', pickup.pickupId, {
            locationId: pickup.locationId,
            customerId: pickup.customerId,
            reason,
            cancelledBy
        });
    }

    handlePickupRescheduled(pickup) {
        logger.logPickupEvent('pickup_rescheduled', pickup.pickupId, {
            locationId: pickup.locationId,
            customerId: pickup.customerId
        });
    }

    handlePickupReminderDue({ pickup, reminderType }) {
        logger.logPickupEvent('pickup_reminder_sent', pickup.pickupId, {
            locationId: pickup.locationId,
            customerId: pickup.customerId,
            reminderType
        });
    }

    initializeDefaultTimeSlots() {
        // Default time slot configuration
        const defaultSlots = {
            duration: 30, // 30 minutes
            startTime: '09:00',
            endTime: '18:00',
            breakTimes: [
                { start: '12:00', end: '13:00' }, // Lunch break
                { start: '15:00', end: '15:15' }  // Afternoon break
            ]
        };

        this.timeSlots.set('default', defaultSlots);
        logger.info('Default time slots initialized');
    }

    async getLocationTimeSlots(locationId) {
        // Get location-specific time slots or use defaults
        return this.timeSlots.get(locationId) || this.timeSlots.get('default');
    }

    startScheduleMonitoring() {
        // Monitor for upcoming pickups every minute
        setInterval(async () => {
            try {
                await this.checkUpcomingPickups();
            } catch (error) {
                logger.error('Failed to check upcoming pickups', error);
            }
        }, 60000); // 1 minute

        // Clean up expired pickups daily
        setInterval(async () => {
            try {
                await this.cleanupExpiredPickups();
            } catch (error) {
                logger.error('Failed to cleanup expired pickups', error);
            }
        }, 86400000); // 24 hours

        logger.info('Pickup schedule monitoring started');
    }

    async checkUpcomingPickups() {
        const now = moment();
        const upcoming = now.clone().add(15, 'minutes'); // Check 15 minutes ahead
        
        // Find pickups starting soon
        const pattern = 'pickup:*';
        const keys = await this.redis.keys(pattern);

        for (const key of keys) {
            const pickupData = await this.redis.hgetall(key);
            if (Object.keys(pickupData).length > 0) {
                const pickup = this.parsePickupData(pickupData);
                
                if (pickup.status === 'confirmed') {
                    const pickupTime = moment(`${pickup.scheduledDate} ${pickup.timeSlot.startTime}`);
                    
                    if (pickupTime.isBetween(now, upcoming)) {
                        // Notify location about upcoming pickup
                        this.io.to(`location:${pickup.locationId}`).emit('pickup_upcoming', {
                            pickupId: pickup.pickupId,
                            customerId: pickup.customerId,
                            timeSlot: pickup.timeSlot,
                            items: pickup.items,
                            minutesUntilPickup: pickupTime.diff(now, 'minutes')
                        });
                    }
                }
            }
        }
    }

    async cleanupExpiredPickups() {
        const cutoffDate = moment().subtract(30, 'days');
        const pattern = 'pickup:*';
        const keys = await this.redis.keys(pattern);

        let cleanedCount = 0;

        for (const key of keys) {
            const pickupData = await this.redis.hgetall(key);
            if (Object.keys(pickupData).length > 0) {
                const pickup = this.parsePickupData(pickupData);
                const pickupDate = moment(pickup.createdAt);
                
                if (pickupDate.isBefore(cutoffDate) && 
                    ['completed', 'cancelled'].includes(pickup.status)) {
                    
                    await this.redis.del(key);
                    this.pickupSchedules.delete(pickup.pickupId);
                    cleanedCount++;
                }
            }
        }

        if (cleanedCount > 0) {
            logger.info('Cleaned up expired pickups', { count: cleanedCount });
        }
    }

    async getPickupMetrics(locationId = null, startDate = null, endDate = null) {
        const metrics = {
            totalPickups: 0,
            scheduledPickups: 0,
            confirmedPickups: 0,
            completedPickups: 0,
            cancelledPickups: 0,
            averageWaitTime: 0,
            averageServiceTime: 0,
            customerSatisfaction: 0,
            slotUtilization: 0,
            timestamp: new Date().toISOString()
        };

        // Implementation would collect and analyze pickup data
        // This is a simplified version

        return metrics;
    }
}

module.exports = PickupScheduler;