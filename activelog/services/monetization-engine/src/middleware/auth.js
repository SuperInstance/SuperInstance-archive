const jwt = require('jsonwebtoken');
const logger = require('../utils/logger');

const authMiddleware = (req, res, next) => {
  try {
    const authHeader = req.header('Authorization');
    
    if (!authHeader) {
      return res.status(401).json({
        error: 'Access denied. No token provided.',
        code: 'NO_TOKEN'
      });
    }

    // Extract token from "Bearer <token>" format
    const token = authHeader.startsWith('Bearer ')
      ? authHeader.substring(7)
      : authHeader;

    if (!token) {
      return res.status(401).json({
        error: 'Access denied. Invalid token format.',
        code: 'INVALID_FORMAT'
      });
    }

    try {
      // Verify the JWT token
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      
      // Add user information to request object
      req.user = {
        id: decoded.userId || decoded.id,
        email: decoded.email,
        role: decoded.role || 'user',
        subscription: decoded.subscription,
        permissions: decoded.permissions || []
      };

      // Log successful authentication for audit purposes
      logger.audit('User authenticated', {
        userId: req.user.id,
        email: req.user.email,
        endpoint: req.originalUrl,
        method: req.method,
        ip: req.ip
      });

      next();
    } catch (jwtError) {
      let errorMessage = 'Invalid token.';
      let errorCode = 'INVALID_TOKEN';

      if (jwtError.name === 'TokenExpiredError') {
        errorMessage = 'Token has expired.';
        errorCode = 'TOKEN_EXPIRED';
      } else if (jwtError.name === 'JsonWebTokenError') {
        errorMessage = 'Malformed token.';
        errorCode = 'MALFORMED_TOKEN';
      }

      logger.security('Authentication failed', {
        error: jwtError.message,
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        endpoint: req.originalUrl
      });

      return res.status(401).json({
        error: errorMessage,
        code: errorCode
      });
    }
  } catch (error) {
    logger.error('Auth middleware error:', error);
    return res.status(500).json({
      error: 'Internal authentication error.',
      code: 'AUTH_ERROR'
    });
  }
};

// Optional auth middleware - doesn't fail if no token provided
const optionalAuthMiddleware = (req, res, next) => {
  const authHeader = req.header('Authorization');
  
  if (!authHeader) {
    req.user = null;
    return next();
  }

  const token = authHeader.startsWith('Bearer ')
    ? authHeader.substring(7)
    : authHeader;

  if (!token) {
    req.user = null;
    return next();
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = {
      id: decoded.userId || decoded.id,
      email: decoded.email,
      role: decoded.role || 'user',
      subscription: decoded.subscription,
      permissions: decoded.permissions || []
    };
  } catch (error) {
    // Silently fail for optional auth
    req.user = null;
  }

  next();
};

// Admin role middleware
const adminMiddleware = (req, res, next) => {
  if (!req.user) {
    return res.status(401).json({
      error: 'Authentication required.',
      code: 'AUTH_REQUIRED'
    });
  }

  if (req.user.role !== 'admin' && req.user.role !== 'super_admin') {
    logger.security('Unauthorized admin access attempt', {
      userId: req.user.id,
      role: req.user.role,
      endpoint: req.originalUrl,
      ip: req.ip
    });

    return res.status(403).json({
      error: 'Admin privileges required.',
      code: 'ADMIN_REQUIRED'
    });
  }

  next();
};

// Subscription tier middleware
const subscriptionMiddleware = (requiredTier) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        error: 'Authentication required.',
        code: 'AUTH_REQUIRED'
      });
    }

    const tierHierarchy = {
      'free': 0,
      'pro': 1,
      'enterprise': 2
    };

    const userTier = req.user.subscription?.plan || 'free';
    const userTierLevel = tierHierarchy[userTier] || 0;
    const requiredTierLevel = tierHierarchy[requiredTier] || 0;

    if (userTierLevel < requiredTierLevel) {
      logger.billing('Subscription upgrade required', {
        userId: req.user.id,
        currentTier: userTier,
        requiredTier,
        endpoint: req.originalUrl
      });

      return res.status(402).json({
        error: `${requiredTier} subscription required.`,
        code: 'UPGRADE_REQUIRED',
        currentPlan: userTier,
        requiredPlan: requiredTier,
        upgradeUrl: `/api/subscriptions/plans`
      });
    }

    next();
  };
};

// Permission-based middleware
const permissionMiddleware = (requiredPermissions) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        error: 'Authentication required.',
        code: 'AUTH_REQUIRED'
      });
    }

    const userPermissions = req.user.permissions || [];
    const hasRequiredPermissions = Array.isArray(requiredPermissions)
      ? requiredPermissions.some(permission => userPermissions.includes(permission))
      : userPermissions.includes(requiredPermissions);

    if (!hasRequiredPermissions) {
      logger.security('Insufficient permissions', {
        userId: req.user.id,
        userPermissions,
        requiredPermissions,
        endpoint: req.originalUrl,
        ip: req.ip
      });

      return res.status(403).json({
        error: 'Insufficient permissions.',
        code: 'INSUFFICIENT_PERMISSIONS',
        required: requiredPermissions
      });
    }

    next();
  };
};

// Rate limiting middleware for specific users
const userRateLimitMiddleware = (maxRequests, windowMs) => {
  const userRequests = new Map();

  return (req, res, next) => {
    if (!req.user) {
      return next();
    }

    const userId = req.user.id;
    const now = Date.now();
    const windowStart = now - windowMs;

    // Get user's request history
    const userHistory = userRequests.get(userId) || [];
    
    // Remove old requests outside the window
    const validRequests = userHistory.filter(timestamp => timestamp > windowStart);
    
    if (validRequests.length >= maxRequests) {
      logger.security('User rate limit exceeded', {
        userId,
        requestCount: validRequests.length,
        maxRequests,
        windowMs,
        ip: req.ip
      });

      return res.status(429).json({
        error: 'Rate limit exceeded. Please try again later.',
        code: 'RATE_LIMIT_EXCEEDED',
        resetTime: new Date(validRequests[0] + windowMs).toISOString()
      });
    }

    // Add current request timestamp
    validRequests.push(now);
    userRequests.set(userId, validRequests);

    next();
  };
};

// API key middleware for external integrations
const apiKeyMiddleware = (req, res, next) => {
  const apiKey = req.header('X-API-Key') || req.query.api_key;

  if (!apiKey) {
    return res.status(401).json({
      error: 'API key required.',
      code: 'API_KEY_REQUIRED'
    });
  }

  // In a real implementation, you'd validate the API key against a database
  // For now, we'll use environment variables for demo purposes
  const validApiKeys = process.env.VALID_API_KEYS?.split(',') || [];

  if (!validApiKeys.includes(apiKey)) {
    logger.security('Invalid API key attempt', {
      apiKey: apiKey.substring(0, 8) + '...',
      ip: req.ip,
      endpoint: req.originalUrl
    });

    return res.status(401).json({
      error: 'Invalid API key.',
      code: 'INVALID_API_KEY'
    });
  }

  logger.audit('API key authentication successful', {
    apiKey: apiKey.substring(0, 8) + '...',
    ip: req.ip,
    endpoint: req.originalUrl
  });

  next();
};

module.exports = {
  authMiddleware,
  optionalAuthMiddleware,
  adminMiddleware,
  subscriptionMiddleware,
  permissionMiddleware,
  userRateLimitMiddleware,
  apiKeyMiddleware
};