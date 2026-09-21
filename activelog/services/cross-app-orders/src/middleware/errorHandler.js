const logger = require('../config/logger');

/**
 * Global error handling middleware
 */
const errorHandler = (err, req, res, next) => {
  // Log the error
  logger.error('Unhandled error:', {
    error: err.message,
    stack: err.stack,
    url: req.originalUrl,
    method: req.method,
    ip: req.ip,
    userAgent: req.headers['user-agent'],
    userId: req.user?.userId,
    requestId: req.id
  });

  // Set default error
  let error = {
    message: err.message || 'Internal server error',
    status: err.status || 500,
    code: err.code || 'INTERNAL_ERROR'
  };

  // Handle specific error types
  if (err.name === 'ValidationError') {
    // Mongoose validation error
    error = {
      message: 'Validation failed',
      status: 400,
      code: 'VALIDATION_ERROR',
      details: Object.values(err.errors).map(e => ({
        field: e.path,
        message: e.message,
        value: e.value
      }))
    };
  } else if (err.name === 'CastError') {
    // Mongoose cast error (invalid ObjectId, etc.)
    error = {
      message: 'Invalid data format',
      status: 400,
      code: 'INVALID_DATA_FORMAT',
      field: err.path,
      value: err.value
    };
  } else if (err.code === 11000) {
    // MongoDB duplicate key error
    const field = Object.keys(err.keyPattern)[0];
    error = {
      message: `Duplicate value for ${field}`,
      status: 409,
      code: 'DUPLICATE_VALUE',
      field: field,
      value: err.keyValue[field]
    };
  } else if (err.name === 'JsonWebTokenError') {
    // JWT errors
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
  } else if (err.name === 'MulterError') {
    // File upload errors
    if (err.code === 'LIMIT_FILE_SIZE') {
      error = {
        message: 'File too large',
        status: 413,
        code: 'FILE_TOO_LARGE',
        maxSize: err.limit
      };
    } else if (err.code === 'LIMIT_FILE_COUNT') {
      error = {
        message: 'Too many files',
        status: 413,
        code: 'TOO_MANY_FILES',
        maxCount: err.limit
      };
    } else {
      error = {
        message: 'File upload error',
        status: 400,
        code: 'FILE_UPLOAD_ERROR',
        details: err.message
      };
    }
  } else if (err.type === 'entity.parse.failed') {
    // JSON parsing error
    error = {
      message: 'Invalid JSON in request body',
      status: 400,
      code: 'INVALID_JSON'
    };
  } else if (err.type === 'entity.too.large') {
    // Request entity too large
    error = {
      message: 'Request entity too large',
      status: 413,
      code: 'REQUEST_TOO_LARGE'
    };
  }

  // Handle business logic errors
  if (err.isBusinessError) {
    error = {
      message: err.message,
      status: err.status || 400,
      code: err.code || 'BUSINESS_ERROR',
      details: err.details
    };
  }

  // Handle third-party service errors
  if (err.isServiceError) {
    error = {
      message: 'External service error',
      status: 502,
      code: 'SERVICE_ERROR',
      service: err.service,
      details: process.env.NODE_ENV === 'development' ? err.message : 'Service temporarily unavailable'
    };
  }

  // Don't expose internal errors in production
  if (process.env.NODE_ENV === 'production' && error.status >= 500) {
    error.message = 'Internal server error';
    delete error.details;
    delete error.stack;
  }

  // Add helpful information for development
  if (process.env.NODE_ENV === 'development') {
    error.stack = err.stack;
    error.timestamp = new Date().toISOString();
    error.requestId = req.id;
  }

  // Set security headers for error responses
  res.set({
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block'
  });

  // Send error response
  res.status(error.status).json({
    error: error.message,
    code: error.code,
    ...(error.details && { details: error.details }),
    ...(error.field && { field: error.field }),
    ...(error.value && { value: error.value }),
    ...(error.maxSize && { maxSize: error.maxSize }),
    ...(error.maxCount && { maxCount: error.maxCount }),
    ...(error.service && { service: error.service }),
    ...(error.stack && { stack: error.stack }),
    ...(error.timestamp && { timestamp: error.timestamp }),
    ...(error.requestId && { requestId: error.requestId })
  });
};

/**
 * 404 handler for undefined routes
 */
const notFoundHandler = (req, res) => {
  const error = {
    message: 'Route not found',
    status: 404,
    code: 'ROUTE_NOT_FOUND',
    path: req.originalUrl,
    method: req.method
  };

  logger.warn('Route not found:', {
    url: req.originalUrl,
    method: req.method,
    ip: req.ip,
    userAgent: req.headers['user-agent']
  });

  res.status(404).json({
    error: error.message,
    code: error.code,
    path: error.path,
    method: error.method,
    timestamp: new Date().toISOString()
  });
};

/**
 * Custom error classes for better error handling
 */
class BusinessError extends Error {
  constructor(message, code = 'BUSINESS_ERROR', status = 400, details = null) {
    super(message);
    this.name = 'BusinessError';
    this.isBusinessError = true;
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

class ServiceError extends Error {
  constructor(message, service, code = 'SERVICE_ERROR', status = 502) {
    super(message);
    this.name = 'ServiceError';
    this.isServiceError = true;
    this.service = service;
    this.code = code;
    this.status = status;
  }
}

class ValidationError extends Error {
  constructor(message, field = null, value = null) {
    super(message);
    this.name = 'ValidationError';
    this.field = field;
    this.value = value;
    this.status = 400;
    this.code = 'VALIDATION_ERROR';
  }
}

class AuthenticationError extends Error {
  constructor(message, code = 'AUTHENTICATION_ERROR') {
    super(message);
    this.name = 'AuthenticationError';
    this.status = 401;
    this.code = code;
  }
}

class AuthorizationError extends Error {
  constructor(message, code = 'AUTHORIZATION_ERROR') {
    super(message);
    this.name = 'AuthorizationError';
    this.status = 403;
    this.code = code;
  }
}

class NotFoundError extends Error {
  constructor(message, resource = null) {
    super(message);
    this.name = 'NotFoundError';
    this.status = 404;
    this.code = 'NOT_FOUND';
    this.resource = resource;
  }
}

class ConflictError extends Error {
  constructor(message, code = 'CONFLICT') {
    super(message);
    this.name = 'ConflictError';
    this.status = 409;
    this.code = code;
  }
}

class RateLimitError extends Error {
  constructor(message = 'Rate limit exceeded', retryAfter = 60) {
    super(message);
    this.name = 'RateLimitError';
    this.status = 429;
    this.code = 'RATE_LIMIT_EXCEEDED';
    this.retryAfter = retryAfter;
  }
}

/**
 * Async error wrapper to catch async errors in route handlers
 */
const asyncHandler = (fn) => {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

/**
 * Error logging for different environments
 */
const logError = (error, req = null, additionalInfo = {}) => {
  const errorInfo = {
    message: error.message,
    name: error.name,
    stack: error.stack,
    code: error.code,
    status: error.status,
    ...additionalInfo
  };

  if (req) {
    errorInfo.request = {
      url: req.originalUrl,
      method: req.method,
      ip: req.ip,
      userAgent: req.headers['user-agent'],
      userId: req.user?.userId,
      requestId: req.id
    };
  }

  // Different logging levels based on error severity
  if (error.status >= 500) {
    logger.error('Server error:', errorInfo);
  } else if (error.status >= 400) {
    logger.warn('Client error:', errorInfo);
  } else {
    logger.info('Handled error:', errorInfo);
  }
};

module.exports = {
  errorHandler,
  notFoundHandler,
  asyncHandler,
  logError,
  // Error classes
  BusinessError,
  ServiceError,
  ValidationError,
  AuthenticationError,
  AuthorizationError,
  NotFoundError,
  ConflictError,
  RateLimitError
};