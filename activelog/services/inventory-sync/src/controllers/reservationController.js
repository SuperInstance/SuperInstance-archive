const express = require('express');
const router = express.Router();
const { asyncHandler, BusinessError } = require('../middleware/errorHandler');
const reservationService = require('../services/reservationService');

// Create reservation
router.post('/create', asyncHandler(async (req, res) => {
  const { locationId, itemId, quantity, customerId, duration, customerInfo, reason, metadata } = req.body;
  
  if (!locationId || !itemId || !quantity) {
    throw new BusinessError('Missing required reservation parameters', 'MISSING_PARAMETERS');
  }
  
  const reservation = await reservationService.createReservation(locationId, itemId, quantity, {
    customerId,
    duration,
    customerInfo,
    reason,
    metadata
  });
  
  res.status(201).json({
    success: true,
    reservation,
    message: 'Reservation created successfully'
  });
}));

// Get reservation
router.get('/:reservationId', asyncHandler(async (req, res) => {
  const { reservationId } = req.params;
  
  const reservation = await reservationService.getReservation(reservationId);
  if (!reservation) {
    throw new BusinessError('Reservation not found', 'RESERVATION_NOT_FOUND', 404);
  }
  
  res.json({
    success: true,
    reservation
  });
}));

// Confirm reservation
router.post('/:reservationId/confirm', asyncHandler(async (req, res) => {
  const { reservationId } = req.params;
  const { confirmedBy, orderId } = req.body;
  
  const reservation = await reservationService.confirmReservation(reservationId, {
    confirmedBy,
    orderId
  });
  
  res.json({
    success: true,
    reservation,
    message: 'Reservation confirmed successfully'
  });
}));

// Cancel reservation
router.post('/:reservationId/cancel', asyncHandler(async (req, res) => {
  const { reservationId } = req.params;
  const { cancelledBy, reason } = req.body;
  
  const reservation = await reservationService.cancelReservation(reservationId, {
    cancelledBy,
    reason
  });
  
  res.json({
    success: true,
    reservation,
    message: 'Reservation cancelled successfully'
  });
}));

// Extend reservation
router.post('/:reservationId/extend', asyncHandler(async (req, res) => {
  const { reservationId } = req.params;
  const { additionalTime } = req.body;
  
  if (!additionalTime || additionalTime <= 0) {
    throw new BusinessError('Valid additional time required', 'INVALID_DURATION');
  }
  
  const reservation = await reservationService.extendReservation(reservationId, additionalTime);
  
  res.json({
    success: true,
    reservation,
    message: 'Reservation extended successfully'
  });
}));

module.exports = router;