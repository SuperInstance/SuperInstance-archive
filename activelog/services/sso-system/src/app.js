const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const session = require('express-session');
const RedisStore = require('connect-redis')(session);
const cookieParser = require('cookie-parser');
const passport = require('passport');
const rateLimit = require('express-rate-limit');
const winston = require('winston');

// Import SSO services
const OAuth2Provider = require('./services/OAuth2Provider');
const SessionManager = require('./services/SessionManager');
const TokenExchange = require('./services/TokenExchange');
const RBACManager = require('./services/RBACManager');
const PermissionInheritance = require('./services/PermissionInheritance');
const APIKeyManager = require('./services/APIKeyManager');
const MFAManager = require('./services/MFAManager');
const SocialLoginManager = require('./services/SocialLoginManager');
const EnterpriseSSO = require('./services/EnterpriseSSO');
const DeviceFingerprinting = require('./services/DeviceFingerprinting');
const SessionAnalytics = require('./services/SessionAnalytics');
const AuditLogger = require('./services/AuditLogger');

class SSOApp {
  constructor() {
    this.app = express();
    this.server = http.createServer(this.app);
    this.wss = new WebSocket.Server({ server: this.server });
    
    this.services = {};
    this.connections = new Map();
    
    this.setupLogger();
    this.setupMiddleware();
    this.initializeServices();
    this.setupPassport();
    this.setupRoutes();
    this.setupWebSocketServer();
    this.setupEventListeners();
  }

  setupLogger() {
    this.logger = winston.createLogger({
      level: process.env.LOG_LEVEL || 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
      ),
      transports: [
        new winston.transports.Console({
          format: winston.format.combine(
            winston.format.colorize(),
            winston.format.simple()
          )
        }),
        new winston.transports.File({ filename: './logs/sso-error.log', level: 'error' }),
        new winston.transports.File({ filename: './logs/sso-combined.log' })
      ]
    });
  }

  setupMiddleware() {
    // Security middleware
    this.app.use(helmet({
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          scriptSrc: ["'self'", "'unsafe-inline'", 'cdn.jsdelivr.net'],
          styleSrc: ["'self'", "'unsafe-inline'", 'cdn.jsdelivr.net'],
          imgSrc: ["'self'", 'data:', 'https:'],
          connectSrc: ["'self'", 'ws:', 'wss:']
        }
      }
    }));
    
    // CORS configuration
    this.app.use(cors({
      origin: function(origin, callback) {
        // Allow configured origins or localhost for development
        const allowedOrigins = [
          'http://localhost:3000',
          'https://app.activelog.com',
          'https://admin.activelog.com'
        ];
        
        if (!origin || allowedOrigins.includes(origin)) {
          callback(null, true);
        } else {
          callback(new Error('Not allowed by CORS'));
        }
      },
      credentials: true
    }));
    
    this.app.use(compression());
    this.app.use(cookieParser());
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));
    
    // Session middleware
    this.app.use(session({
      store: new RedisStore({ 
        url: process.env.REDIS_URL || 'redis://localhost:6379'
      }),
      secret: process.env.SESSION_SECRET || 'sso-session-secret',
      resave: false,
      saveUninitialized: false,
      name: 'activelog_session',
      cookie: {
        secure: process.env.NODE_ENV === 'production',
        httpOnly: true,
        maxAge: 24 * 60 * 60 * 1000, // 24 hours
        sameSite: 'lax'
      }
    }));
    
    // Rate limiting
    const limiter = rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: process.env.NODE_ENV === 'production' ? 100 : 1000,
      message: 'Too many requests from this IP',
      standardHeaders: true,
      legacyHeaders: false
    });
    this.app.use('/api/', limiter);
    
    // Request logging
    this.app.use((req, res, next) => {
      const start = Date.now();
      
      res.on('finish', () => {
        const duration = Date.now() - start;
        
        this.services.auditLogger?.info('HTTP Request', {
          method: req.method,
          url: req.url,
          ip: req.ip,
          userAgent: req.get('User-Agent'),
          statusCode: res.statusCode,
          duration,
          userId: req.user?.id,
          sessionId: req.sessionID
        });
      });
      
      next();
    });
  }

  async initializeServices() {
    try {
      // Initialize core services
      this.services.auditLogger = new AuditLogger({
        logLevel: process.env.LOG_LEVEL || 'info',
        enableConsole: true,
        enableFile: true
      });

      this.services.oauth2Provider = new OAuth2Provider({
        jwtSecret: process.env.JWT_SECRET || 'oauth2-secret',
        issuer: process.env.ISSUER || 'https://sso.activelog.com',
        accessTokenLifetime: 3600, // 1 hour
        refreshTokenLifetime: 1209600 // 2 weeks
      });

      this.services.sessionManager = new SessionManager({
        redisUrl: process.env.REDIS_URL || 'redis://localhost:6379',
        sessionLifetime: 86400000, // 24 hours
        enableSlidingExpiration: true
      });

      this.services.tokenExchange = new TokenExchange({
        jwtSecret: process.env.JWT_SECRET || 'oauth2-secret',
        issuer: process.env.ISSUER || 'https://sso.activelog.com'
      });

      this.services.rbacManager = new RBACManager({
        enableInheritance: true,
        enableDynamicRoles: true,
        cacheTimeout: 300000 // 5 minutes
      });

      this.services.permissionInheritance = new PermissionInheritance({
        maxInheritanceDepth: 20,
        enableConditionalInheritance: true
      });

      this.services.apiKeyManager = new APIKeyManager({
        keyLength: 32,
        secretLength: 64,
        enableRotation: true,
        maxKeysPerUser: 50
      });

      this.services.mfaManager = new MFAManager({
        issuer: 'ActiveLog SSO',
        enableSMS: false, // Disabled until SMS service configured
        enableEmail: false, // Disabled until email service configured
        enableWebAuthn: true
      });

      this.services.socialLoginManager = new SocialLoginManager({
        callbackUrl: process.env.CALLBACK_URL || 'http://localhost:8201',
        enableAccountLinking: true
      });

      this.services.enterpriseSSO = new EnterpriseSSO({
        entityId: 'activelog-sso',
        callbackUrl: process.env.CALLBACK_URL || 'http://localhost:8201'
      });

      this.services.deviceFingerprinting = new DeviceFingerprinting({
        enableLocationTracking: true,
        enableBehavioralAnalysis: true,
        deviceTrustThreshold: 0.8
      });

      this.services.sessionAnalytics = new SessionAnalytics({
        retentionDays: 90,
        enableRealTimeMetrics: true,
        enableGeoAnalytics: true
      });

      console.log('All SSO services initialized successfully');
      
    } catch (error) {
      console.error('Failed to initialize SSO services:', error);
      process.exit(1);
    }
  }

  setupPassport() {
    this.app.use(passport.initialize());
    this.app.use(passport.session());
    
    passport.serializeUser((user, done) => {
      done(null, user.id);
    });
    
    passport.deserializeUser(async (id, done) => {
      try {
        // This would integrate with your user service
        const user = { id, username: `user_${id}` };
        done(null, user);
      } catch (error) {
        done(error, null);
      }
    });
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: process.env.npm_package_version || '1.0.0',
        services: {
          oauth2Provider: 'running',
          sessionManager: 'running',
          rbacManager: 'running',
          apiKeyManager: 'running',
          mfaManager: 'running',
          socialLoginManager: 'running',
          enterpriseSSO: 'running',
          deviceFingerprinting: 'running',
          sessionAnalytics: 'running',
          auditLogger: 'running'
        }
      });
    });

    // OIDC Discovery
    this.app.get('/.well-known/openid_configuration', (req, res) => {
      const config = this.services.oauth2Provider.getWellKnownConfiguration();
      res.json(config);
    });

    this.app.get('/.well-known/jwks.json', (req, res) => {
      const jwks = this.services.oauth2Provider.getJWKS();
      res.json(jwks);
    });

    // OAuth2/OIDC endpoints
    this.app.get('/oauth/authorize', async (req, res) => {
      try {
        // This would implement the OAuth2 authorization endpoint
        res.json({ message: 'OAuth2 authorization endpoint' });
      } catch (error) {
        this.logger.error('OAuth authorization error:', error);
        res.status(500).json({ error: 'Authorization failed' });
      }
    });

    this.app.post('/oauth/token', async (req, res) => {
      try {
        // This would implement the OAuth2 token endpoint
        res.json({ message: 'OAuth2 token endpoint' });
      } catch (error) {
        this.logger.error('OAuth token error:', error);
        res.status(500).json({ error: 'Token request failed' });
      }
    });

    this.app.get('/oauth/userinfo', this.authenticateToken.bind(this), (req, res) => {
      try {
        // Return user information based on token
        res.json({
          sub: req.user.id,
          name: req.user.name,
          email: req.user.email
        });
      } catch (error) {
        this.logger.error('UserInfo error:', error);
        res.status(500).json({ error: 'UserInfo request failed' });
      }
    });

    // Token Exchange
    this.app.post('/oauth/token/exchange', async (req, res) => {
      try {
        const result = await this.services.tokenExchange.exchangeToken(req.body);
        res.json(result);
      } catch (error) {
        this.logger.error('Token exchange error:', error);
        res.status(400).json({ error: error.message });
      }
    });

    // Session Management
    this.app.post('/api/sessions', async (req, res) => {
      try {
        const deviceInfo = await this.extractDeviceInfo(req);
        const session = await this.services.sessionManager.createSession(req.body.user, {
          deviceInfo,
          enableCrossDomain: true
        });
        res.json(session);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/sessions/:sessionId', async (req, res) => {
      try {
        const session = await this.services.sessionManager.getSession(req.params.sessionId);
        if (!session) {
          return res.status(404).json({ error: 'Session not found' });
        }
        res.json(session);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.delete('/api/sessions/:sessionId', async (req, res) => {
      try {
        await this.services.sessionManager.destroySession(req.params.sessionId);
        res.json({ success: true });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // API Key Management
    this.app.post('/api/keys', this.authenticateUser.bind(this), async (req, res) => {
      try {
        const apiKey = await this.services.apiKeyManager.createAPIKey({
          ...req.body,
          userId: req.user.id
        });
        
        await this.services.auditLogger.logAPIKeyCreated(req.user.id, apiKey.name, {
          ip: req.ip,
          userAgent: req.get('User-Agent')
        });
        
        res.json(apiKey);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/keys', this.authenticateUser.bind(this), async (req, res) => {
      try {
        const keys = this.services.apiKeyManager.getUserAPIKeys(req.user.id);
        res.json(keys);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.delete('/api/keys/:keyId', this.authenticateUser.bind(this), async (req, res) => {
      try {
        await this.services.apiKeyManager.revokeAPIKey(req.params.keyId, 'Manual revocation', req.user.id);
        
        await this.services.auditLogger.logAPIKeyRevoked(req.user.id, req.params.keyId, 'Manual revocation', {
          ip: req.ip,
          userAgent: req.get('User-Agent')
        });
        
        res.json({ success: true });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // MFA Management
    this.app.post('/api/mfa/totp/setup', this.authenticateUser.bind(this), async (req, res) => {
      try {
        const result = await this.services.mfaManager.setupTOTP(req.user.id, req.body);
        res.json(result);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.post('/api/mfa/totp/verify', this.authenticateUser.bind(this), async (req, res) => {
      try {
        const result = await this.services.mfaManager.verifyTOTPSetup(req.user.id, req.body.code);
        
        await this.services.auditLogger.logMFAEvent(req.user.id, 'totp', true, {
          ip: req.ip,
          userAgent: req.get('User-Agent'),
          action: 'setup'
        });
        
        res.json(result);
      } catch (error) {
        await this.services.auditLogger.logMFAEvent(req.user.id, 'totp', false, {
          ip: req.ip,
          userAgent: req.get('User-Agent'),
          action: 'setup',
          error: error.message
        });
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/mfa/status', this.authenticateUser.bind(this), (req, res) => {
      try {
        const status = this.services.mfaManager.getUserMFAStatus(req.user.id);
        res.json(status);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Social Login Routes
    this.app.get('/auth/:provider', (req, res, next) => {
      const provider = req.params.provider;
      passport.authenticate(provider, {
        scope: req.query.scope ? req.query.scope.split(',') : undefined
      })(req, res, next);
    });

    this.app.get('/auth/:provider/callback', (req, res, next) => {
      const provider = req.params.provider;
      passport.authenticate(provider, (err, user) => {
        if (err) {
          return res.redirect(`/login?error=${encodeURIComponent(err.message)}`);
        }
        if (!user) {
          return res.redirect('/login?error=authentication_failed');
        }
        
        req.logIn(user, (loginErr) => {
          if (loginErr) {
            return res.redirect(`/login?error=${encodeURIComponent(loginErr.message)}`);
          }
          return res.redirect('/dashboard');
        });
      })(req, res, next);
    });

    // RBAC Management
    this.app.post('/api/rbac/roles', this.requirePermission('admin:roles'), async (req, res) => {
      try {
        const role = this.services.rbacManager.createRole(req.body);
        res.json(role);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/rbac/roles', this.authenticateUser.bind(this), async (req, res) => {
      try {
        const roles = this.services.rbacManager.getRoles(req.query);
        res.json(roles);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.post('/api/rbac/permissions', this.requirePermission('admin:permissions'), async (req, res) => {
      try {
        const permission = this.services.rbacManager.createPermission(req.body);
        res.json(permission);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Device Management
    this.app.post('/api/devices/recognize', async (req, res) => {
      try {
        const deviceInfo = await this.extractDeviceInfo(req);
        const result = await this.services.deviceFingerprinting.recognizeDevice(deviceInfo, req.user?.id);
        res.json(result);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/devices', this.authenticateUser.bind(this), async (req, res) => {
      try {
        const devices = this.services.deviceFingerprinting.getUserDevices(req.user.id);
        res.json(devices);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Analytics
    this.app.get('/api/analytics/sessions', this.requirePermission('analytics:read'), async (req, res) => {
      try {
        const analytics = await this.services.sessionAnalytics.getSessionAnalytics(req.query);
        res.json(analytics);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/analytics/realtime/:metric', this.requirePermission('analytics:read'), (req, res) => {
      try {
        const data = this.services.sessionAnalytics.getRealTimeMetrics(req.params.metric, req.query.minutes);
        res.json(data);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Audit Logs
    this.app.get('/api/audit/logs', this.requirePermission('audit:read'), (req, res) => {
      try {
        const logs = this.services.auditLogger.queryLogs(req.query);
        res.json(logs);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    this.app.get('/api/audit/stats', this.requirePermission('audit:read'), (req, res) => {
      try {
        const stats = this.services.auditLogger.getLogStats(req.query.timeRange);
        res.json(stats);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Service Statistics
    this.app.get('/api/stats', this.requirePermission('admin:read'), (req, res) => {
      try {
        const stats = {
          oauth2Provider: this.services.oauth2Provider.getStats(),
          sessionManager: this.services.sessionManager.getStats(),
          rbacManager: this.services.rbacManager.getStats(),
          apiKeyManager: this.services.apiKeyManager.getStats(),
          mfaManager: this.services.mfaManager.getStats(),
          socialLoginManager: this.services.socialLoginManager.getStats(),
          enterpriseSSO: this.services.enterpriseSSO.getStats(),
          deviceFingerprinting: this.services.deviceFingerprinting.getStats(),
          sessionAnalytics: this.services.sessionAnalytics.getStats(),
          auditLogger: this.services.auditLogger.getStats()
        };
        res.json(stats);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Error handling middleware
    this.app.use((error, req, res, next) => {
      this.logger.error('Unhandled error:', error);
      
      this.services.auditLogger?.error('Unhandled error', {
        error: error.message,
        stack: error.stack,
        url: req.url,
        method: req.method,
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        userId: req.user?.id
      });
      
      res.status(500).json({
        error: 'Internal server error',
        message: process.env.NODE_ENV === 'development' ? error.message : undefined
      });
    });

    // 404 handler
    this.app.use((req, res) => {
      res.status(404).json({ error: 'Endpoint not found' });
    });
  }

  setupWebSocketServer() {
    this.wss.on('connection', (ws, req) => {
      const connectionId = this.generateConnectionId();
      this.connections.set(connectionId, ws);
      
      console.log(`WebSocket client connected: ${connectionId}`);
      
      ws.on('message', (message) => {
        try {
          const data = JSON.parse(message);
          this.handleWebSocketMessage(ws, data);
        } catch (error) {
          ws.send(JSON.stringify({ error: 'Invalid JSON message' }));
        }
      });
      
      ws.on('close', () => {
        this.connections.delete(connectionId);
        console.log(`WebSocket client disconnected: ${connectionId}`);
      });
      
      ws.send(JSON.stringify({
        type: 'welcome',
        connectionId,
        timestamp: new Date().toISOString()
      }));
    });
  }

  handleWebSocketMessage(ws, data) {
    switch (data.type) {
      case 'subscribe_realtime_logs':
        this.handleLogSubscription(ws, data);
        break;
      case 'subscribe_metrics':
        this.handleMetricsSubscription(ws, data);
        break;
      default:
        ws.send(JSON.stringify({ error: `Unknown message type: ${data.type}` }));
    }
  }

  handleLogSubscription(ws, data) {
    const subscriberId = this.generateSubscriberId();
    this.services.auditLogger.subscribeRealTime(subscriberId, data.filters);
    
    ws.subscriberId = subscriberId;
    ws.send(JSON.stringify({ type: 'subscribed', subscriberId }));
  }

  setupEventListeners() {
    // Audit Logger Events
    this.services.auditLogger.on('realTimeLog', (subscriberId, logEntry) => {
      this.broadcastToSubscriber(subscriberId, {
        type: 'log',
        data: logEntry
      });
    });

    // Session Analytics Events
    this.services.sessionAnalytics.on('sessionStarted', (session) => {
      this.broadcastToAllConnections({
        type: 'session_started',
        data: session
      });
    });

    // Device Fingerprinting Events
    this.services.deviceFingerprinting.on('suspiciousDeviceDetected', (event) => {
      this.services.auditLogger.logSuspiciousDevice(
        event.userId,
        event.deviceId,
        event.riskScore,
        event.suspiciousFlags,
        { ip: event.ip }
      );
    });

    // MFA Events
    this.services.mfaManager.on('totpEnabled', (event) => {
      this.services.auditLogger.logMFAEvent(event.userId, 'totp', true, {
        action: 'enabled'
      });
    });

    // OAuth2 Events
    this.services.oauth2Provider.on('tokenExchanged', (event) => {
      this.services.auditLogger.logTokenExchange(
        event.subjectToken,
        'access_token',
        'access_token',
        { audience: event.audience }
      );
    });
  }

  // Middleware Functions
  async authenticateToken(req, res, next) {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];
    
    if (!token) {
      return res.status(401).json({ error: 'Access token required' });
    }
    
    try {
      const tokenInfo = await this.services.oauth2Provider.verifyJWTToken(token);
      if (!tokenInfo) {
        return res.status(403).json({ error: 'Invalid token' });
      }
      
      req.user = {
        id: tokenInfo.sub,
        username: tokenInfo.username,
        email: tokenInfo.email,
        roles: tokenInfo.roles || [],
        permissions: tokenInfo.permissions || []
      };
      
      next();
    } catch (error) {
      return res.status(403).json({ error: 'Token verification failed' });
    }
  }

  async authenticateUser(req, res, next) {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }
    next();
  }

  requirePermission(permission) {
    return async (req, res, next) => {
      if (!req.user) {
        return res.status(401).json({ error: 'Authentication required' });
      }
      
      try {
        const hasPermission = await this.services.rbacManager.hasPermission(
          req.user.id,
          permission,
          { ip: req.ip, userAgent: req.get('User-Agent') }
        );
        
        if (!hasPermission) {
          await this.services.auditLogger.logUnauthorizedAccess(
            req.user.id,
            req.path,
            req.method,
            { ip: req.ip, userAgent: req.get('User-Agent') }
          );
          
          return res.status(403).json({ error: 'Insufficient permissions' });
        }
        
        next();
      } catch (error) {
        return res.status(500).json({ error: 'Permission check failed' });
      }
    };
  }

  // Helper Methods
  async extractDeviceInfo(req) {
    const userAgent = req.get('User-Agent');
    const ip = req.ip;
    
    return {
      userAgent,
      ip,
      acceptLanguage: req.get('Accept-Language'),
      acceptEncoding: req.get('Accept-Encoding'),
      referer: req.get('Referer'),
      headers: req.headers
    };
  }

  broadcastToSubscriber(subscriberId, message) {
    for (const [connectionId, ws] of this.connections) {
      if (ws.subscriberId === subscriberId && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
      }
    }
  }

  broadcastToAllConnections(message) {
    for (const [connectionId, ws] of this.connections) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
      }
    }
  }

  generateConnectionId() {
    return `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  generateSubscriberId() {
    return `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  async start(port = 8201) {
    return new Promise((resolve, reject) => {
      try {
        this.server.listen(port, () => {
          console.log(`ActiveLog SSO System started on port ${port}`);
          console.log(`WebSocket server available on ws://localhost:${port}`);
          console.log(`OIDC Discovery: http://localhost:${port}/.well-known/openid_configuration`);
          console.log(`Health Check: http://localhost:${port}/health`);
          resolve();
        });
      } catch (error) {
        reject(error);
      }
    });
  }

  async stop() {
    // Close WebSocket connections
    for (const [connectionId, ws] of this.connections) {
      ws.terminate();
    }
    this.connections.clear();
    
    // Close HTTP server
    return new Promise((resolve) => {
      this.server.close(resolve);
    });
  }
}

// Start the application if this file is run directly
if (require.main === module) {
  const ssoApp = new SSOApp();
  
  ssoApp.start(process.env.PORT || 8201)
    .then(() => {
      console.log('ActiveLog SSO System is running successfully');
    })
    .catch(error => {
      console.error('Failed to start SSO System:', error);
      process.exit(1);
    });
  
  // Graceful shutdown
  process.on('SIGINT', async () => {
    console.log('\nShutting down SSO System...');
    try {
      await ssoApp.stop();
      console.log('SSO System stopped successfully');
      process.exit(0);
    } catch (error) {
      console.error('Error during shutdown:', error);
      process.exit(1);
    }
  });
}

module.exports = SSOApp;