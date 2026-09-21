const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const session = require('express-session');
const MongoStore = require('connect-mongo');
const passport = require('passport');
const http = require('http');
const socketIo = require('socket.io');
require('dotenv').config();

// Import services
const SSOProvider = require('./src/auth/SSOProvider');
const PermissionManager = require('./src/services/PermissionManager');
const OrganizationSeparator = require('./src/services/OrganizationSeparator');
const CredentialPortabilityManager = require('./src/services/CredentialPortabilityManager');
const PrivacyControlManager = require('./src/services/PrivacyControlManager');
const ConsentManager = require('./src/services/ConsentManager');
const AuditLogger = require('./src/services/AuditLogger');
const SessionManager = require('./src/services/SessionManager');
const DeviceManager = require('./src/services/DeviceManager');
const EmergencyAccessManager = require('./src/services/EmergencyAccessManager');

// Import models
const { User, Organization } = require('./src/models');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: process.env.ALLOWED_ORIGINS?.split(',') || "*",
    methods: ["GET", "POST"],
    credentials: true
  }
});

const PORT = process.env.PORT || 8312;

// Database connection
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/identity_federation', {
  useNewUrlParser: true,
  useUnifiedTopology: true
}).then(() => {
  console.log('✓ Connected to MongoDB');
}).catch(error => {
  console.error('MongoDB connection error:', error);
  process.exit(1);
});

// Middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'", "ws:", "wss:"]
    }
  }
}));

app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true
}));

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Rate limiting
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000, // 15 minutes
  max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests, please try again later' }
});
app.use('/api/', limiter);

// Stricter rate limiting for auth endpoints
const authLimiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_LOGIN_WINDOW_MS) || 5 * 60 * 1000, // 5 minutes
  max: parseInt(process.env.RATE_LIMIT_LOGIN_MAX_ATTEMPTS) || 5,
  message: { error: 'Too many authentication attempts, please try again later' }
});

// Session configuration
app.use(session({
  secret: process.env.SESSION_SECRET,
  name: 'identity.sid',
  resave: false,
  saveUninitialized: false,
  store: MongoStore.create({
    mongoUrl: process.env.MONGODB_URI || 'mongodb://localhost:27017/identity_federation',
    touchAfter: 24 * 3600 // lazy session update
  }),
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    maxAge: 24 * 60 * 60 * 1000, // 24 hours
    sameSite: process.env.NODE_ENV === 'production' ? 'strict' : 'lax',
    domain: process.env.SESSION_COOKIE_DOMAIN
  }
}));

// Initialize Passport
app.use(passport.initialize());
app.use(passport.session());

// Initialize services
const auditLogger = new AuditLogger();
const ssoProvider = new SSOProvider();
const permissionManager = new PermissionManager();
const orgSeparator = new OrganizationSeparator();
const credentialManager = new CredentialPortabilityManager();
const privacyManager = new PrivacyControlManager();
const consentManager = new ConsentManager();
const sessionManager = new SessionManager();
const deviceManager = new DeviceManager();
const emergencyAccessManager = new EmergencyAccessManager();

// Authentication middleware
const authenticate = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '') || req.session?.accessToken;
    
    if (!token) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const decoded = await ssoProvider.verifyToken(token);
    const user = await User.findById(decoded.userId).populate('organizations');
    
    if (!user || !user.isActive) {
      return res.status(401).json({ error: 'Invalid user' });
    }

    req.user = user;
    req.userId = user._id.toString();
    req.tokenData = decoded;
    
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

// Permission check middleware
const requirePermission = (permission) => {
  return async (req, res, next) => {
    try {
      const hasPermission = await permissionManager.checkPermission(
        req.userId,
        permission,
        { organizationId: req.headers['x-organization-id'] }
      );
      
      if (!hasPermission) {
        return res.status(403).json({ error: 'Insufficient permissions' });
      }
      
      next();
    } catch (error) {
      res.status(500).json({ error: 'Permission check failed' });
    }
  };
};

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '1.0.0',
    services: {
      database: mongoose.connection.readyState === 1,
      redis: sessionManager?.redis?.status === 'ready'
    }
  });
});

// Authentication routes
app.post('/auth/login', authLimiter, async (req, res, next) => {
  passport.authenticate('local', async (err, user, info) => {
    if (err) return next(err);
    
    if (!user) {
      return res.status(401).json({ 
        error: info.message,
        requiresMFA: info.requiresMFA,
        userId: info.userId
      });
    }

    // Generate tokens
    const { accessToken, refreshToken } = await ssoProvider.generateTokenPair(user, {
      organizationId: req.body.organizationId
    });

    // Create session
    const sessionResult = await sessionManager.createSession(user._id, {
      fingerprint: req.body.deviceFingerprint,
      userAgent: req.get('User-Agent'),
      platform: req.body.platform,
      browser: req.body.browser,
      os: req.body.os
    }, {
      ipAddress: req.ip,
      location: req.body.location
    });

    // Register device
    const deviceResult = await deviceManager.registerDevice(user._id, {
      userAgent: req.get('User-Agent'),
      screen: req.body.screen,
      timezone: req.body.timezone,
      language: req.body.language,
      platform: req.body.platform,
      capabilities: req.body.capabilities
    }, {
      ipAddress: req.ip,
      location: req.body.location
    });

    res.json({
      accessToken,
      refreshToken,
      user: {
        id: user._id,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        organizations: user.organizations
      },
      session: {
        sessionId: sessionResult.sessionId,
        expiresAt: sessionResult.expiresAt
      },
      device: {
        deviceId: deviceResult.deviceId,
        requiresVerification: deviceResult.requiresVerification
      }
    });
  })(req, res, next);
});

// OAuth routes
app.get('/auth/google', passport.authenticate('google', { scope: ['profile', 'email'] }));
app.get('/auth/google/callback', passport.authenticate('google'), async (req, res) => {
  const { accessToken } = await ssoProvider.generateTokenPair(req.user);
  res.redirect(`${process.env.CLIENT_URL}?token=${accessToken}`);
});

app.get('/auth/microsoft', passport.authenticate('microsoft'));
app.get('/auth/microsoft/callback', passport.authenticate('microsoft'), async (req, res) => {
  const { accessToken } = await ssoProvider.generateTokenPair(req.user);
  res.redirect(`${process.env.CLIENT_URL}?token=${accessToken}`);
});

app.get('/auth/github', passport.authenticate('github'));
app.get('/auth/github/callback', passport.authenticate('github'), async (req, res) => {
  const { accessToken } = await ssoProvider.generateTokenPair(req.user);
  res.redirect(`${process.env.CLIENT_URL}?token=${accessToken}`);
});

// SAML routes
app.get('/auth/saml', passport.authenticate('saml'));
app.post('/auth/saml/callback', passport.authenticate('saml'), async (req, res) => {
  const { accessToken } = await ssoProvider.generateTokenPair(req.user);
  res.redirect(`${process.env.CLIENT_URL}?token=${accessToken}`);
});

// Token refresh
app.post('/auth/refresh', async (req, res) => {
  try {
    const { refreshToken } = req.body;
    const result = await ssoProvider.refreshAccessToken(refreshToken);
    res.json(result);
  } catch (error) {
    res.status(401).json({ error: error.message });
  }
});

// Logout
app.post('/auth/logout', authenticate, async (req, res) => {
  try {
    const sessionId = req.headers['x-session-id'];
    if (sessionId) {
      await sessionManager.terminateSession(sessionId, 'user_logout');
    }
    
    req.session.destroy();
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Logout failed' });
  }
});

// User management routes
app.get('/api/user/profile', authenticate, (req, res) => {
  res.json({
    id: req.user._id,
    email: req.user.email,
    firstName: req.user.firstName,
    lastName: req.user.lastName,
    avatar: req.user.avatar,
    organizations: req.user.organizations,
    preferences: req.user.preferences,
    privacyProfile: req.user.privacyProfile
  });
});

app.put('/api/user/profile', authenticate, async (req, res) => {
  try {
    const { firstName, lastName, avatar, preferences } = req.body;
    
    req.user.firstName = firstName || req.user.firstName;
    req.user.lastName = lastName || req.user.lastName;
    req.user.avatar = avatar || req.user.avatar;
    req.user.preferences = { ...req.user.preferences, ...preferences };
    
    await req.user.save();
    
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Organization management routes
app.get('/api/organizations', authenticate, async (req, res) => {
  try {
    const organizations = await orgSeparator.getUserOrganizations(req.userId, req.query.includePersonal !== 'false');
    res.json(organizations);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/organizations', authenticate, async (req, res) => {
  try {
    const organization = await orgSeparator.createCompanyOrganization(req.body, req.userId);
    res.status(201).json(organization);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.post('/api/organizations/:orgId/switch', authenticate, async (req, res) => {
  try {
    const result = await orgSeparator.switchContext(req.userId, req.params.orgId, {
      sessionId: req.headers['x-session-id'],
      ipAddress: req.ip,
      userAgent: req.get('User-Agent')
    });
    res.json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Device management routes
app.get('/api/devices', authenticate, async (req, res) => {
  try {
    const devices = await deviceManager.getUserDevices(req.userId, {
      currentDeviceId: req.headers['x-device-id']
    });
    res.json(devices);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/devices/:deviceId/verify', authenticate, async (req, res) => {
  try {
    const { method, code, token, biometricData } = req.body;
    const result = await deviceManager.verifyDevice(req.userId, req.params.deviceId, method, {
      code, token, biometricData
    });
    res.json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.delete('/api/devices/:deviceId', authenticate, async (req, res) => {
  try {
    await deviceManager.revokeDevice(req.userId, req.params.deviceId, 'user_request');
    res.json({ success: true });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Privacy and consent routes
app.get('/api/privacy/profile', authenticate, async (req, res) => {
  try {
    res.json(req.user.privacyProfile || {});
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/privacy/preferences', authenticate, async (req, res) => {
  try {
    const result = await privacyManager.updatePrivacyPreferences(req.userId, req.body, {
      ipAddress: req.ip,
      userAgent: req.get('User-Agent'),
      source: 'user_preferences'
    });
    res.json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.post('/api/privacy/requests', authenticate, async (req, res) => {
  try {
    const result = await privacyManager.submitDataSubjectRequest(req.userId, req.body.type, {
      ...req.body,
      ipAddress: req.ip,
      userAgent: req.get('User-Agent')
    });
    res.status(201).json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Consent management routes
app.get('/api/consent', authenticate, async (req, res) => {
  try {
    const result = await consentManager.getUserConsents(req.userId, req.query);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/consent/grant', authenticate, async (req, res) => {
  try {
    const { consentId, method, evidence, granularChoices } = req.body;
    const result = await consentManager.grantConsent(req.userId, consentId, {
      method, evidence, granularChoices
    }, {
      ipAddress: req.ip,
      userAgent: req.get('User-Agent')
    });
    res.json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.post('/api/consent/withdraw', authenticate, async (req, res) => {
  try {
    const { consentId, reason } = req.body;
    const result = await consentManager.withdrawConsent(req.userId, consentId, { reason }, {
      ipAddress: req.ip,
      userAgent: req.get('User-Agent')
    });
    res.json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Data portability routes
app.post('/api/data/export', authenticate, async (req, res) => {
  try {
    const result = await credentialManager.exportUserData(req.userId, req.body);
    res.status(202).json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Emergency access routes (admin only)
app.post('/api/emergency/request', authenticate, requirePermission('emergency:access'), async (req, res) => {
  try {
    const result = await emergencyAccessManager.requestEmergencyAccess({
      ...req.body,
      requestedBy: req.userId,
      ipAddress: req.ip,
      userAgent: req.get('User-Agent')
    });
    res.status(201).json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.post('/api/emergency/:requestId/approve', authenticate, requirePermission('emergency:approve'), async (req, res) => {
  try {
    const result = await emergencyAccessManager.approveEmergencyAccess(req.params.requestId, req.userId, req.body);
    res.json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Admin routes
app.get('/api/admin/audit', authenticate, requirePermission('system:audit'), async (req, res) => {
  try {
    const logs = await auditLogger.getUserAuditLog(req.query.userId, req.query);
    res.json(logs);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Federation metadata
app.get('/federation/metadata', (req, res) => {
  const metadata = {
    issuer: `${req.protocol}://${req.get('host')}`,
    authorization_endpoint: `${req.protocol}://${req.get('host')}/auth/authorize`,
    token_endpoint: `${req.protocol}://${req.get('host')}/auth/token`,
    userinfo_endpoint: `${req.protocol}://${req.get('host')}/api/user/profile`,
    jwks_uri: `${req.protocol}://${req.get('host')}/.well-known/jwks.json`,
    response_types_supported: ['code', 'token'],
    subject_types_supported: ['public'],
    id_token_signing_alg_values_supported: ['RS256']
  };
  
  res.json(metadata);
});

// WebSocket handling for real-time features
io.use(async (socket, next) => {
  try {
    const token = socket.handshake.auth.token;
    const decoded = await ssoProvider.verifyToken(token);
    const user = await User.findById(decoded.userId);
    
    if (user) {
      socket.userId = user._id.toString();
      socket.user = user;
      next();
    } else {
      next(new Error('Authentication error'));
    }
  } catch (error) {
    next(new Error('Authentication error'));
  }
});

io.on('connection', (socket) => {
  console.log(`User ${socket.userId} connected via WebSocket`);
  
  socket.join(`user:${socket.userId}`);
  
  socket.on('device:register', async (deviceInfo) => {
    try {
      const result = await deviceManager.registerDevice(socket.userId, deviceInfo);
      socket.emit('device:registered', result);
    } catch (error) {
      socket.emit('device:error', { error: error.message });
    }
  });
  
  socket.on('consent:request', async (consentData) => {
    try {
      const result = await consentManager.requestConsent(socket.userId, consentData);
      socket.emit('consent:requested', result);
    } catch (error) {
      socket.emit('consent:error', { error: error.message });
    }
  });
  
  socket.on('disconnect', () => {
    console.log(`User ${socket.userId} disconnected`);
  });
});

// Error handling middleware
app.use((error, req, res, next) => {
  console.error('Unhandled error:', error);
  
  auditLogger.log('system_error', 'error', {
    error: error.message,
    stack: error.stack,
    url: req.url,
    method: req.method,
    userId: req.userId,
    ipAddress: req.ip
  });
  
  res.status(500).json({ 
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully');
  
  server.close(() => {
    console.log('HTTP server closed');
    mongoose.connection.close(false, () => {
      console.log('MongoDB connection closed');
      process.exit(0);
    });
  });
});

// Start server
server.listen(PORT, () => {
  console.log(`🚀 Identity Federation Service running on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
  console.log(`🔐 Federation metadata: http://localhost:${PORT}/federation/metadata`);
  console.log(`📝 Environment: ${process.env.NODE_ENV || 'development'}`);
});

module.exports = app;