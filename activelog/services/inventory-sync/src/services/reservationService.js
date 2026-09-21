const logger = require('../config/logger');
const redis = require('../config/redis');
const { v4: uuidv4 } = require('uuid');

class ReservationService {
  constructor() {
    this.defaultTimeout = parseInt(process.env.RESERVATION_TIMEOUT) || 1800000; // 30 minutes
    this.maxDuration = parseInt(process.env.MAX_RESERVATION_DURATION) || 86400000; // 24 hours
    this.cleanupInterval = parseInt(process.env.RESERVATION_CLEANUP_INTERVAL) || 300000; // 5 minutes
    
    // Initialize cleanup scheduler
    this.initializeCleanupScheduler();
  }

  initializeCleanupScheduler() {
    setInterval(() => {
      this.cleanupExpiredReservations();
    }, this.cleanupInterval);
  }

  /**
   * Create inventory reservation
   */
  async createReservation(locationId, itemId, quantity, reservationData = {}) {
    try {
      const reservationId = uuidv4();
      const now = new Date();
      const expiresAt = new Date(now.getTime() + (reservationData.duration || this.defaultTimeout));

      const reservation = {
        reservationId,
        locationId,
        itemId,
        quantity,
        customerId: reservationData.customerId,
        customerInfo: reservationData.customerInfo || {},
        reason: reservationData.reason || 'customer_hold',
        status: 'active',
        createdAt: now.toISOString(),
        expiresAt: expiresAt.toISOString(),
        metadata: reservationData.metadata || {}
      };

      // Store reservation with TTL
      const ttlSeconds = Math.ceil((expiresAt - now) / 1000);
      await redis.createReservation(reservationId, reservation, ttlSeconds);

      logger.logReservationEvent('reservation_created', reservationId, {
        locationId,
        itemId,
        quantity,
        customerId: reservationData.customerId,
        expiresAt: expiresAt.toISOString()
      });

      return reservation;
    } catch (error) {
      logger.error('Error creating reservation:', error);
      throw error;
    }
  }

  /**
   * Get reservation details
   */
  async getReservation(reservationId) {
    try {
      return await redis.getReservation(reservationId);
    } catch (error) {
      logger.error('Error getting reservation:', error);
      return null;
    }
  }

  /**
   * Confirm reservation (convert to actual inventory reduction)
   */
  async confirmReservation(reservationId, confirmationData = {}) {
    try {
      const reservation = await redis.getReservation(reservationId);
      if (!reservation) {
        throw new Error('Reservation not found');
      }

      if (reservation.status !== 'active') {
        throw new Error('Reservation is not active');
      }

      // Update reservation status
      reservation.status = 'confirmed';
      reservation.confirmedAt = new Date().toISOString();
      reservation.confirmedBy = confirmationData.confirmedBy || 'system';
      reservation.orderId = confirmationData.orderId;

      // Update reservation
      await redis.createReservation(reservationId, reservation, 86400); // Keep confirmed reservations for 24 hours

      logger.logReservationEvent('reservation_confirmed', reservationId, {
        locationId: reservation.locationId,
        itemId: reservation.itemId,
        quantity: reservation.quantity,
        confirmedBy: reservation.confirmedBy,
        orderId: reservation.orderId
      });

      return reservation;
    } catch (error) {
      logger.error('Error confirming reservation:', error);
      throw error;
    }
  }

  /**
   * Cancel reservation
   */
  async cancelReservation(reservationId, cancellationData = {}) {
    try {
      const reservation = await redis.getReservation(reservationId);
      if (!reservation) {
        throw new Error('Reservation not found');
      }

      reservation.status = 'cancelled';
      reservation.cancelledAt = new Date().toISOString();
      reservation.cancelledBy = cancellationData.cancelledBy || 'system';
      reservation.cancellationReason = cancellationData.reason || 'manual_cancellation';

      // Update reservation
      await redis.createReservation(reservationId, reservation, 3600); // Keep cancelled reservations for 1 hour

      logger.logReservationEvent('reservation_cancelled', reservationId, {
        locationId: reservation.locationId,
        itemId: reservation.itemId,
        quantity: reservation.quantity,
        reason: reservation.cancellationReason
      });

      return reservation;
    } catch (error) {
      logger.error('Error cancelling reservation:', error);
      throw error;
    }
  }

  /**
   * Extend reservation duration
   */
  async extendReservation(reservationId, additionalTime) {
    try {
      const reservation = await redis.getReservation(reservationId);
      if (!reservation) {
        throw new Error('Reservation not found');
      }

      if (reservation.status !== 'active') {
        throw new Error('Can only extend active reservations');
      }

      const currentExpiry = new Date(reservation.expiresAt);
      const newExpiry = new Date(currentExpiry.getTime() + additionalTime);
      
      // Check against maximum duration
      const totalDuration = newExpiry.getTime() - new Date(reservation.createdAt).getTime();
      if (totalDuration > this.maxDuration) {
        throw new Error('Reservation extension would exceed maximum duration');
      }

      reservation.expiresAt = newExpiry.toISOString();
      reservation.extendedAt = new Date().toISOString();

      // Update reservation with new TTL
      const ttlSeconds = Math.ceil((newExpiry - new Date()) / 1000);
      await redis.createReservation(reservationId, reservation, ttlSeconds);

      logger.logReservationEvent('reservation_extended', reservationId, {
        locationId: reservation.locationId,
        itemId: reservation.itemId,
        newExpiresAt: reservation.expiresAt,
        additionalTime: additionalTime
      });

      return reservation;
    } catch (error) {
      logger.error('Error extending reservation:', error);
      throw error;
    }
  }

  /**
   * Clean up expired reservations
   */
  async cleanupExpiredReservations() {
    try {
      // This would typically query for expired reservations
      // For now, Redis TTL handles most of the cleanup automatically
      logger.debug('Running reservation cleanup');
      
      // Log cleanup run
      logger.logReservationEvent('cleanup_run', 'system', {
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      logger.error('Error during reservation cleanup:', error);
    }
  }
}

module.exports = new ReservationService();