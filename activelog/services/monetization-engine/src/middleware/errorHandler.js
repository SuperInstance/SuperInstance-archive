const logger = require('../utils/logger');

const errorHandler = (err, req, res, next) => {
  // Log the error
  logger.error('Unhandled error:', {
    error: err.message,
    stack: err.stack,
    url: req.originalUrl,
    method: req.method,
    ip: req.ip,
    userAgent: req.get('User-Agent'),
    userId: req.user?.id || 'anonymous'
  });

  // Default error
  let error = {
    message: 'Internal server error',
    status: 500,
    code: 'INTERNAL_ERROR'
  };

  // Handle specific error types
  if (err.name === 'ValidationError') {
    error = {
      message: 'Validation error',
      status: 400,
      code: 'VALIDATION_ERROR',
      details: err.details
    };
  } else if (err.name === 'CastError') {
    error = {
      message: 'Invalid ID format',
      status: 400,
      code: 'INVALID_ID'
    };
  } else if (err.code === '23505') { // PostgreSQL unique constraint violation
    error = {
      message: 'Duplicate entry',
      status: 409,
      code: 'DUPLICATE_ENTRY'
    };
  } else if (err.code === '23503') { // PostgreSQL foreign key constraint violation
    error = {
      message: 'Referenced resource not found',
      status: 400,
      code: 'INVALID_REFERENCE'
    };
  } else if (err.code === '23502') { // PostgreSQL not null constraint violation
    error = {
      message: 'Required field missing',
      status: 400,
      code: 'MISSING_FIELD'
    };
  } else if (err.name === 'SequelizeValidationError') {
    error = {
      message: 'Validation error',
      status: 400,
      code: 'VALIDATION_ERROR',
      details: err.errors?.map(e => ({
        field: e.path,
        message: e.message
      }))
    };
  } else if (err.name === 'SequelizeUniqueConstraintError') {
    error = {
      message: 'Duplicate entry',
      status: 409,
      code: 'DUPLICATE_ENTRY',
      field: err.errors?.[0]?.path
    };
  } else if (err.name === 'JsonWebTokenError') {
    error = {
      message: 'Invalid token',
      status: 401,
      code: 'INVALID_TOKEN'
    };
  } else if (err.name === 'TokenExpiredError') {
    error = {
      message: 'Token expired',
      status: 401,
      code: 'TOKEN_EXPIRED'
    };
  } else if (err.type === 'StripeCardError') {
    error = {
      message: 'Card error: ' + err.message,
      status: 402,
      code: 'CARD_ERROR',
      stripeCode: err.code
    };
  } else if (err.type === 'StripeInvalidRequestError') {
    error = {
      message: 'Payment processing error',
      status: 400,
      code: 'PAYMENT_ERROR',
      stripeCode: err.code
    };
  } else if (err.type === 'StripeRateLimitError') {
    error = {
      message: 'Too many requests to payment processor',
      status: 429,
      code: 'RATE_LIMITED'
    };
  } else if (err.type === 'StripeConnectionError') {
    error = {
      message: 'Payment service unavailable',
      status: 503,
      code: 'SERVICE_UNAVAILABLE'
    };
  } else if (err.type === 'StripeAuthenticationError') {
    error = {
      message: 'Payment authentication error',
      status: 500,
      code: 'PAYMENT_AUTH_ERROR'
    };
  } else if (err.status || err.statusCode) {
    // Error already has status code
    error = {
      message: err.message,
      status: err.status || err.statusCode,
      code: err.code || 'ERROR'
    };
  }

  // Don't expose sensitive information in production
  if (process.env.NODE_ENV === 'production') {
    // Remove stack trace and internal details
    delete err.stack;
    
    if (error.status >= 500) {
      error.message = 'Internal server error';
      delete error.details;
    }
  }

  // Send error response
  res.status(error.status).json({
    error: error.message,
    code: error.code,
    ...(error.details && { details: error.details }),
    ...(error.field && { field: error.field }),
    ...(error.stripeCode && { stripeCode: error.stripeCode }),
    timestamp: new Date().toISOString(),
    requestId: req.id || generateRequestId()
  });
};

// Generate a simple request ID for tracking
const generateRequestId = () => {
  return Math.random().toString(36).substring(2, 15) + 
         Math.random().toString(36).substring(2, 15);
};

// Not found middleware
const notFoundHandler = (req, res) => {
  logger.info('Route not found', {
    url: req.originalUrl,
    method: req.method,
    ip: req.ip,
    userAgent: req.get('User-Agent')
  });

  res.status(404).json({
    error: 'Route not found',
    code: 'NOT_FOUND',
    path: req.originalUrl,
    method: req.method,
    timestamp: new Date().toISOString()
  });
};

// Async error wrapper to catch async/await errors
const asyncWrapper = (fn) => {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

// Validation error formatter
const formatValidationErrors = (errors) => {
  if (Array.isArray(errors)) {
    return errors.map(error => ({
      field: error.path || error.key,
      message: error.message,
      value: error.value
    }));
  }
  
  return [];
};

module.exports = {
  errorHandler,
  notFoundHandler,
  asyncWrapper,
  formatValidationErrors
};