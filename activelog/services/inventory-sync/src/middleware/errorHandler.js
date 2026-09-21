const logger = require('../config/logger');

class BusinessError extends Error {
  constructor(message, code = 'BUSINESS_ERROR', statusCode = 400) {
    super(message);
    this.name = 'BusinessError';
    this.code = code;
    this.statusCode = statusCode;
  }
}

const asyncHandler = (fn) => {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

const errorHandler = (error, req, res, next) => {
  logger.error('Unhandled error:', {
    error: error.message,
    stack: error.stack,
    url: req.url,
    method: req.method,
    ip: req.ip,
    userAgent: req.get('User-Agent'),
    requestId: req.id
  });

  // Business errors
  if (error instanceof BusinessError) {
    return res.status(error.statusCode).json({
      error: error.message,
      code: error.code,
      requestId: req.id
    });
  }

  // Default error
  res.status(500).json({
    error: 'Internal server error',
    code: 'INTERNAL_ERROR',
    requestId: req.id
  });
};

const notFoundHandler = (req, res) => {
  res.status(404).json({
    error: 'Endpoint not found',
    code: 'NOT_FOUND',
    path: req.originalUrl,
    method: req.method
  });
};

module.exports = {
  BusinessError,
  asyncHandler, 
  errorHandler,
  notFoundHandler
};