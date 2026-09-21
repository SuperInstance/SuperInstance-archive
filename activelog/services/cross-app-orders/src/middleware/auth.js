const jwt = require('jsonwebtoken');
const logger = require('../config/logger');
const redis = require('../config/redis');

/**
 * Authentication middleware for verifying JWT tokens
 */
const authenticateToken = async (req, res, next) => {
  try {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

    if (!token) {
      return res.status(401).json({
        error: 'Access token required',
        code: 'NO_TOKEN'
      });
    }

    // Check if token is blacklisted
    const isBlacklisted = await redis.get(`blacklist:${token}`);
    if (isBlacklisted) {
      return res.status(401).json({
        error: 'Token has been revoked',
        code: 'TOKEN_REVOKED'
      });
    }

    // Verify token
    const secret = process.env.JWT_SECRET || 'your-secret-key';
    const decoded = jwt.verify(token, secret);

    // Add user info to request
    req.user = decoded;
    req.token = token;

    // Log authentication success
    logger.debug('Authentication successful', {
      userId: decoded.userId,
      role: decoded.role,
      app: decoded.app
    });

    next();
  } catch (error) {
    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({
        error: 'Invalid token',
        code: 'INVALID_TOKEN'
      });
    }
    
    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({
        error: 'Token expired',
        code: 'TOKEN_EXPIRED'
      });
    }

    logger.error('Authentication error:', error);
    return res.status(500).json({
      error: 'Authentication failed',
      code: 'AUTH_ERROR'
    });
  }
};

/**
 * Authorization middleware for checking user roles and permissions
 */
const authorize = (requiredRoles = [], requiredApps = []) => {
  return (req, res, next) => {
    try {
      if (!req.user) {
        return res.status(401).json({
          error: 'Authentication required',
          code: 'NOT_AUTHENTICATED'
        });
      }

      const { role, app, permissions = [] } = req.user;

      // Check role authorization
      if (requiredRoles.length > 0 && !requiredRoles.includes(role)) {
        logger.logSecurity('unauthorized_access_attempt', {
          userId: req.user.userId,
          requiredRoles,
          userRole: role,
          endpoint: req.originalUrl,
          ip: req.ip
        });

        return res.status(403).json({
          error: 'Insufficient role privileges',
          code: 'INSUFFICIENT_ROLE',
          required: requiredRoles,
          current: role
        });
      }

      // Check app authorization
      if (requiredApps.length > 0 && !requiredApps.includes(app)) {
        return res.status(403).json({
          error: 'App not authorized for this resource',
          code: 'APP_NOT_AUTHORIZED',
          required: requiredApps,
          current: app
        });
      }

      next();
    } catch (error) {
      logger.error('Authorization error:', error);
      return res.status(500).json({
        error: 'Authorization failed',
        code: 'AUTHORIZATION_ERROR'
      });
    }
  };
};

/**
 * DMLog app authentication middleware
 */
const authenticateDMLog = async (req, res, next) => {
  try {
    // Check for DMLog API key in headers
    const apiKey = req.headers['x-dmlog-api-key'];
    
    if (!apiKey) {
      return res.status(401).json({
        error: 'DMLog API key required',
        code: 'NO_DMLOG_API_KEY'
      });
    }

    // Verify API key (in production, this would be stored securely)
    const validApiKey = process.env.DMLOG_API_KEY;
    if (apiKey !== validApiKey) {
      logger.logSecurity('invalid_dmlog_api_key', {
        providedKey: apiKey.substring(0, 8) + '...',
        ip: req.ip,
        userAgent: req.headers['user-agent']
      });

      return res.status(401).json({
        error: 'Invalid DMLog API key',
        code: 'INVALID_DMLOG_API_KEY'
      });
    }

    // Add DMLog context to request
    req.dmlog = {
      authenticated: true,
      app: 'dmlog'
    };

    next();
  } catch (error) {
    logger.error('DMLog authentication error:', error);
    return res.status(500).json({
      error: 'DMLog authentication failed',
      code: 'DMLOG_AUTH_ERROR'
    });
  }
};

/**
 * MakerLog app authentication middleware
 */
const authenticateMakerLog = async (req, res, next) => {
  try {
    // Check for MakerLog API key in headers
    const apiKey = req.headers['x-makerlog-api-key'];
    
    if (!apiKey) {
      return res.status(401).json({
        error: 'MakerLog API key required',
        code: 'NO_MAKERLOG_API_KEY'
      });
    }

    // Verify API key
    const validApiKey = process.env.MAKERLOG_API_KEY;
    if (apiKey !== validApiKey) {
      logger.logSecurity('invalid_makerlog_api_key', {
        providedKey: apiKey.substring(0, 8) + '...',
        ip: req.ip,
        userAgent: req.headers['user-agent']
      });

      return res.status(401).json({
        error: 'Invalid MakerLog API key',
        code: 'INVALID_MAKERLOG_API_KEY'
      });
    }

    // Add MakerLog context to request
    req.makerlog = {
      authenticated: true,
      app: 'makerlog'
    };

    next();
  } catch (error) {
    logger.error('MakerLog authentication error:', error);
    return res.status(500).json({
      error: 'MakerLog authentication failed',
      code: 'MAKERLOG_AUTH_ERROR'
    });
  }
};

/**
 * Internal service authentication (for service-to-service communication)
 */
const authenticateInternal = async (req, res, next) => {
  try {
    const serviceToken = req.headers['x-service-token'];
    
    if (!serviceToken) {
      return res.status(401).json({
        error: 'Service token required',
        code: 'NO_SERVICE_TOKEN'
      });
    }

    // Verify service token
    const validServiceToken = process.env.INTERNAL_SERVICE_TOKEN;
    if (serviceToken !== validServiceToken) {
      logger.logSecurity('invalid_service_token', {
        ip: req.ip,
        userAgent: req.headers['user-agent']
      });

      return res.status(401).json({
        error: 'Invalid service token',
        code: 'INVALID_SERVICE_TOKEN'
      });
    }

    req.internal = {
      authenticated: true,
      service: req.headers['x-service-name'] || 'unknown'
    };

    next();
  } catch (error) {
    logger.error('Internal authentication error:', error);
    return res.status(500).json({
      error: 'Internal authentication failed',
      code: 'INTERNAL_AUTH_ERROR'
    });
  }
};

/**
 * Order ownership middleware - ensures user can only access their own orders
 */
const checkOrderOwnership = async (req, res, next) => {
  try {
    const orderId = req.params.orderId || req.body.orderId;
    
    if (!orderId) {
      return res.status(400).json({
        error: 'Order ID required',
        code: 'NO_ORDER_ID'
      });
    }

    // Get order from database
    const Order = require('../models/Order');
    const order = await Order.findOne({ orderId });

    if (!order) {
      return res.status(404).json({
        error: 'Order not found',
        code: 'ORDER_NOT_FOUND'
      });
    }

    // Check ownership based on user role and app
    const { userId, role, app } = req.user;

    let hasAccess = false;

    // Admin and system roles have full access
    if (['admin', 'system'].includes(role)) {
      hasAccess = true;
    }
    // DMLog users can access their own orders
    else if (app === 'dmlog' && order.customer.dmlogUserId === userId) {
      hasAccess = true;
    }
    // MakerLog users can access orders assigned to them
    else if (app === 'makerlog' && order.makers.selected?.makerUserId === userId) {
      hasAccess = true;
    }

    if (!hasAccess) {
      logger.logSecurity('unauthorized_order_access', {
        userId,
        orderId,
        role,
        app,
        ip: req.ip
      });

      return res.status(403).json({
        error: 'Access denied - not your order',
        code: 'ORDER_ACCESS_DENIED'
      });
    }

    // Add order to request for use in controller
    req.order = order;
    next();

  } catch (error) {
    logger.error('Order ownership check error:', error);
    return res.status(500).json({
      error: 'Access check failed',
      code: 'ACCESS_CHECK_ERROR'
    });
  }
};

/**
 * Maker ownership middleware - ensures makers can only access their own data
 */
const checkMakerOwnership = async (req, res, next) => {
  try {
    const makerId = req.params.makerId || req.body.makerId;
    
    if (!makerId) {
      return res.status(400).json({
        error: 'Maker ID required',
        code: 'NO_MAKER_ID'
      });
    }

    const Maker = require('../models/Maker');
    const maker = await Maker.findOne({ makerId });

    if (!maker) {
      return res.status(404).json({
        error: 'Maker not found',
        code: 'MAKER_NOT_FOUND'
      });
    }

    // Check ownership
    const { userId, role, app } = req.user;

    let hasAccess = false;

    // Admin and system roles have full access
    if (['admin', 'system'].includes(role)) {
      hasAccess = true;
    }
    // MakerLog users can access their own maker profile
    else if (app === 'makerlog' && maker.makerlogUserId === userId) {
      hasAccess = true;
    }

    if (!hasAccess) {
      logger.logSecurity('unauthorized_maker_access', {
        userId,
        makerId,
        role,
        app,
        ip: req.ip
      });

      return res.status(403).json({
        error: 'Access denied - not your maker profile',
        code: 'MAKER_ACCESS_DENIED'
      });
    }

    req.maker = maker;
    next();

  } catch (error) {
    logger.error('Maker ownership check error:', error);
    return res.status(500).json({
      error: 'Access check failed',
      code: 'ACCESS_CHECK_ERROR'
    });
  }
};

/**
 * Rate limiting by user
 */
const rateLimitByUser = (maxRequests = 100, windowMs = 15 * 60 * 1000) => {
  return async (req, res, next) => {
    try {
      const userId = req.user?.userId || req.ip;
      const key = `rate_limit:${userId}`;
      
      const current = await redis.get(key);
      const requestCount = current ? parseInt(current) : 0;

      if (requestCount >= maxRequests) {
        return res.status(429).json({
          error: 'Rate limit exceeded',
          code: 'RATE_LIMIT_EXCEEDED',
          maxRequests,
          windowMs,
          retryAfter: Math.ceil(windowMs / 1000)
        });
      }

      // Increment counter
      await redis.set(key, requestCount + 1, windowMs / 1000);

      // Add rate limit headers
      res.set({
        'X-RateLimit-Limit': maxRequests,
        'X-RateLimit-Remaining': Math.max(0, maxRequests - requestCount - 1),
        'X-RateLimit-Reset': new Date(Date.now() + windowMs).toISOString()
      });

      next();
    } catch (error) {
      logger.error('Rate limiting error:', error);
      next(); // Don't block request on rate limiting errors
    }
  };
};

/**
 * IP whitelist middleware
 */
const ipWhitelist = (allowedIPs = []) => {
  return (req, res, next) => {
    const clientIP = req.ip || req.connection.remoteAddress;
    
    // Allow localhost and internal IPs in development
    if (process.env.NODE_ENV !== 'production') {
      const localIPs = ['127.0.0.1', '::1', '::ffff:127.0.0.1'];
      if (localIPs.includes(clientIP)) {
        return next();
      }
    }

    if (allowedIPs.length > 0 && !allowedIPs.includes(clientIP)) {
      logger.logSecurity('ip_not_whitelisted', {
        ip: clientIP,
        userAgent: req.headers['user-agent']
      });

      return res.status(403).json({
        error: 'IP address not allowed',
        code: 'IP_NOT_ALLOWED'
      });
    }

    next();
  };
};

module.exports = {
  authenticateToken,
  authorize,
  authenticateDMLog,
  authenticateMakerLog,
  authenticateInternal,
  checkOrderOwnership,
  checkMakerOwnership,
  rateLimitByUser,
  ipWhitelist
};