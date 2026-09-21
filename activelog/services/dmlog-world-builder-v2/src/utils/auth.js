const jwt = require('jsonwebtoken');
const logger = require('./logger');

// JWT secret key (in production, this should be in environment variables)
const JWT_SECRET = process.env.JWT_SECRET || 'dmlog-world-builder-secret-key-change-in-production';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '24h';

// Authentication middleware
function requireAuth(req, res, next) {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader) {
      return res.status(401).json({
        success: false,
        error: 'Authorization header required'
      });
    }
    
    const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : authHeader;
    
    if (!token) {
      return res.status(401).json({
        success: false,
        error: 'Authentication token required'
      });
    }
    
    // Verify JWT token
    const decoded = jwt.verify(token, JWT_SECRET);
    
    // Add user info to request
    req.user = {
      id: decoded.userId || decoded.id,
      name: decoded.name || decoded.userName,
      email: decoded.email,
      roles: decoded.roles || [],
      permissions: decoded.permissions || []
    };
    
    next();
    
  } catch (error) {
    logger.security('Authentication failed', {
      error: error.message,
      headers: req.headers,
      ip: req.ip
    });
    
    return res.status(401).json({
      success: false,
      error: 'Invalid or expired token'
    });
  }
}

// Optional authentication (sets user if token is valid, but doesn't require it)
function optionalAuth(req, res, next) {
  try {
    const authHeader = req.headers.authorization;
    
    if (authHeader) {
      const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : authHeader;
      
      if (token) {
        const decoded = jwt.verify(token, JWT_SECRET);
        req.user = {
          id: decoded.userId || decoded.id,
          name: decoded.name || decoded.userName,
          email: decoded.email,
          roles: decoded.roles || [],
          permissions: decoded.permissions || []
        };
      }
    }
    
    next();
    
  } catch (error) {
    // For optional auth, we just continue without user info
    next();
  }
}

// Role-based authorization middleware
function requireRole(role) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        error: 'Authentication required'
      });
    }
    
    if (!req.user.roles.includes(role) && !req.user.roles.includes('admin')) {
      logger.security('Insufficient permissions', {
        userId: req.user.id,
        requiredRole: role,
        userRoles: req.user.roles
      });
      
      return res.status(403).json({
        success: false,
        error: 'Insufficient permissions'
      });
    }
    
    next();
  };
}

// Permission-based authorization middleware
function requirePermission(permission) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        error: 'Authentication required'
      });
    }
    
    if (!req.user.permissions.includes(permission) && !req.user.roles.includes('admin')) {
      logger.security('Permission denied', {
        userId: req.user.id,
        requiredPermission: permission,
        userPermissions: req.user.permissions
      });
      
      return res.status(403).json({
        success: false,
        error: 'Permission denied'
      });
    }
    
    next();
  };
}

// Generate JWT token
function generateToken(user) {
  const payload = {
    userId: user.id || user.userId,
    name: user.name || user.userName,
    email: user.email,
    roles: user.roles || [],
    permissions: user.permissions || [],
    iat: Math.floor(Date.now() / 1000)
  };
  
  return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
}

// Verify JWT token
function verifyToken(token) {
  try {
    return jwt.verify(token, JWT_SECRET);
  } catch (error) {
    throw new Error('Invalid token');
  }
}

// Decode JWT token without verification (for debugging)
function decodeToken(token) {
  try {
    return jwt.decode(token);
  } catch (error) {
    return null;
  }
}

// Check if user has specific permission
function hasPermission(user, permission) {
  if (!user) return false;
  if (user.roles && user.roles.includes('admin')) return true;
  if (user.permissions && user.permissions.includes(permission)) return true;
  return false;
}

// Check if user has specific role
function hasRole(user, role) {
  if (!user) return false;
  if (user.roles && user.roles.includes('admin')) return true;
  if (user.roles && user.roles.includes(role)) return true;
  return false;
}

// Extract user ID from request (handles various auth scenarios)
function getUserId(req) {
  if (req.user && req.user.id) return req.user.id;
  if (req.userId) return req.userId;
  
  // Try to extract from JWT token
  try {
    const authHeader = req.headers.authorization;
    if (authHeader) {
      const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : authHeader;
      const decoded = jwt.verify(token, JWT_SECRET);
      return decoded.userId || decoded.id;
    }
  } catch (error) {
    // Ignore errors, just return null
  }
  
  return null;
}

// Create guest user token (for anonymous access to public worlds)
function createGuestToken(guestId = null) {
  const payload = {
    userId: guestId || `guest_${Date.now()}`,
    name: 'Guest User',
    email: null,
    roles: ['guest'],
    permissions: ['view_public_worlds'],
    isGuest: true,
    iat: Math.floor(Date.now() / 1000)
  };
  
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '1h' });
}

// Middleware to allow guest access to public resources
function allowGuests(req, res, next) {
  try {
    // First try normal authentication
    const authHeader = req.headers.authorization;
    
    if (authHeader) {
      const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : authHeader;
      
      if (token) {
        try {
          const decoded = jwt.verify(token, JWT_SECRET);
          req.user = {
            id: decoded.userId || decoded.id,
            name: decoded.name || decoded.userName,
            email: decoded.email,
            roles: decoded.roles || [],
            permissions: decoded.permissions || [],
            isGuest: decoded.isGuest || false
          };
          
          return next();
        } catch (error) {
          // Token invalid, fall through to guest access
        }
      }
    }
    
    // Create guest user
    req.user = {
      id: `guest_${Date.now()}`,
      name: 'Guest User',
      email: null,
      roles: ['guest'],
      permissions: ['view_public_worlds'],
      isGuest: true
    };
    
    next();
    
  } catch (error) {
    logger.error('Guest auth error:', error);
    res.status(500).json({
      success: false,
      error: 'Authentication error'
    });
  }
}

// Rate limiting by user ID
function getUserRateLimit(userId) {
  // Return different limits based on user type
  if (!userId || userId.startsWith('guest_')) {
    return {
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 50 // 50 requests per window for guests
    };
  }
  
  return {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 1000 // 1000 requests per window for authenticated users
  };
}

// Refresh token if it's close to expiring
function refreshTokenIfNeeded(token) {
  try {
    const decoded = jwt.decode(token);
    const now = Math.floor(Date.now() / 1000);
    const timeUntilExpiry = decoded.exp - now;
    
    // Refresh if token expires in less than 1 hour
    if (timeUntilExpiry < 3600) {
      // Create new token with same payload but extended expiry
      const newPayload = {
        ...decoded,
        iat: now
      };
      delete newPayload.exp; // Let jwt.sign set new expiry
      
      return jwt.sign(newPayload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
    }
    
    return token;
    
  } catch (error) {
    return token;
  }
}

// Create API key for service-to-service authentication
function createApiKey(service, permissions = []) {
  const payload = {
    service,
    permissions,
    type: 'api_key',
    iat: Math.floor(Date.now() / 1000)
  };
  
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '365d' });
}

// Validate API key
function validateApiKey(req, res, next) {
  try {
    const apiKey = req.headers['x-api-key'] || req.query.api_key;
    
    if (!apiKey) {
      return res.status(401).json({
        success: false,
        error: 'API key required'
      });
    }
    
    const decoded = jwt.verify(apiKey, JWT_SECRET);
    
    if (decoded.type !== 'api_key') {
      return res.status(401).json({
        success: false,
        error: 'Invalid API key'
      });
    }
    
    req.service = {
      name: decoded.service,
      permissions: decoded.permissions || []
    };
    
    next();
    
  } catch (error) {
    logger.security('API key validation failed', {
      error: error.message,
      headers: req.headers,
      ip: req.ip
    });
    
    return res.status(401).json({
      success: false,
      error: 'Invalid API key'
    });
  }
}

module.exports = {
  requireAuth,
  optionalAuth,
  requireRole,
  requirePermission,
  generateToken,
  verifyToken,
  decodeToken,
  hasPermission,
  hasRole,
  getUserId,
  createGuestToken,
  allowGuests,
  getUserRateLimit,
  refreshTokenIfNeeded,
  createApiKey,
  validateApiKey
};