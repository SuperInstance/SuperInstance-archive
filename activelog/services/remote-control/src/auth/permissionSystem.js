const EventEmitter = require('events');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const { v4: uuidv4 } = require('uuid');
const logger = require('../core/logger');

class PermissionSystem extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      jwtSecret: options.jwtSecret || process.env.JWT_SECRET || 'remote-control-secret-key',
      sessionTimeout: options.sessionTimeout || 3600000, // 1 hour
      maxFailedAttempts: options.maxFailedAttempts || 5,
      lockoutDuration: options.lockoutDuration || 900000, // 15 minutes
      requireTwoFactor: options.requireTwoFactor || false,
      ...options
    };

    // Permission levels
    this.PERMISSIONS = {
      NONE: 0,
      VIEW_ONLY: 1,
      INTERACT: 2,
      CONTROL: 3,
      ADMIN: 4,
      OWNER: 5
    };

    // Active sessions and permissions
    this.activeSessions = new Map();
    this.userPermissions = new Map();
    this.failedAttempts = new Map();
    this.pendingAuthorizations = new Map();
    this.warningQueue = [];
    
    // Default admin user (in production, this would be in a database)
    this.initializeDefaultUsers();
  }

  async initialize() {
    logger.info('Initializing Permission System...');
    
    // Clean up expired sessions
    setInterval(() => {
      this.cleanupExpiredSessions();
    }, 60000); // Check every minute
    
    // Clean up failed attempts
    setInterval(() => {
      this.cleanupFailedAttempts();
    }, 300000); // Check every 5 minutes
    
    logger.info('Permission System initialized successfully');
  }

  initializeDefaultUsers() {
    // Create default admin account
    this.userPermissions.set('admin', {
      id: 'admin',
      username: 'admin',
      passwordHash: bcrypt.hashSync('admin123', 10), // Change in production!
      permissions: this.PERMISSIONS.OWNER,
      roles: ['admin', 'owner'],
      createdAt: Date.now(),
      lastLogin: null,
      twoFactorEnabled: false,
      allowedIPs: [],
      restrictions: {
        timeWindows: [], // No time restrictions for admin
        maxSessions: 5,
        requireApproval: false
      }
    });

    // Create default viewer account
    this.userPermissions.set('viewer', {
      id: 'viewer',
      username: 'viewer',
      passwordHash: bcrypt.hashSync('viewer123', 10),
      permissions: this.PERMISSIONS.VIEW_ONLY,
      roles: ['viewer'],
      createdAt: Date.now(),
      lastLogin: null,
      twoFactorEnabled: false,
      allowedIPs: [],
      restrictions: {
        timeWindows: [],
        maxSessions: 2,
        requireApproval: true
      }
    });
  }

  async authenticate(username, password, clientInfo = {}) {
    try {
      const user = this.userPermissions.get(username);
      if (!user) {
        await this.recordFailedAttempt(username, clientInfo.ip);
        logger.warn(`Authentication failed: User '${username}' not found`, { ip: clientInfo.ip });
        return { success: false, error: 'Invalid credentials' };
      }

      // Check if user is locked out
      if (await this.isLockedOut(username)) {
        logger.warn(`Authentication blocked: User '${username}' is locked out`, { ip: clientInfo.ip });
        return { success: false, error: 'Account temporarily locked due to failed attempts' };
      }

      // Check IP restrictions
      if (user.allowedIPs.length > 0 && !user.allowedIPs.includes(clientInfo.ip)) {
        logger.warn(`Authentication failed: IP '${clientInfo.ip}' not allowed for user '${username}'`);
        return { success: false, error: 'Access denied from this location' };
      }

      // Verify password
      const passwordValid = await bcrypt.compare(password, user.passwordHash);
      if (!passwordValid) {
        await this.recordFailedAttempt(username, clientInfo.ip);
        logger.warn(`Authentication failed: Invalid password for user '${username}'`, { ip: clientInfo.ip });
        return { success: false, error: 'Invalid credentials' };
      }

      // Check if approval is required
      if (user.restrictions.requireApproval) {
        const authId = await this.requestApproval(user, clientInfo);
        return { 
          success: false, 
          requiresApproval: true, 
          authId,
          message: 'Access request sent for approval' 
        };
      }

      // Create session
      const session = await this.createSession(user, clientInfo);
      
      // Clear failed attempts
      this.failedAttempts.delete(username);
      
      // Update last login
      user.lastLogin = Date.now();
      
      logger.info(`User '${username}' authenticated successfully`, { 
        ip: clientInfo.ip, 
        sessionId: session.id 
      });
      
      this.emit('user-authenticated', { user: user.username, session: session.id, clientInfo });
      
      return { 
        success: true, 
        token: session.token, 
        sessionId: session.id,
        permissions: user.permissions,
        expiresAt: session.expiresAt
      };

    } catch (error) {
      logger.error('Authentication error:', error);
      return { success: false, error: 'Authentication failed' };
    }
  }

  async createSession(user, clientInfo) {
    const sessionId = uuidv4();
    const now = Date.now();
    const expiresAt = now + this.options.sessionTimeout;
    
    const session = {
      id: sessionId,
      userId: user.id,
      username: user.username,
      permissions: user.permissions,
      roles: user.roles,
      clientInfo,
      createdAt: now,
      expiresAt,
      lastActivity: now,
      token: jwt.sign(
        { 
          sessionId, 
          userId: user.id, 
          username: user.username,
          permissions: user.permissions 
        },
        this.options.jwtSecret,
        { expiresIn: this.options.sessionTimeout / 1000 }
      )
    };

    // Check session limits
    const userSessions = Array.from(this.activeSessions.values())
      .filter(s => s.userId === user.id);
    
    if (userSessions.length >= user.restrictions.maxSessions) {
      // Remove oldest session
      const oldestSession = userSessions.sort((a, b) => a.lastActivity - b.lastActivity)[0];
      this.activeSessions.delete(oldestSession.id);
      logger.info(`Removed oldest session for user '${user.username}' due to session limit`);
    }

    this.activeSessions.set(sessionId, session);
    return session;
  }

  async requestApproval(user, clientInfo) {
    const authId = uuidv4();
    const request = {
      id: authId,
      user: user.username,
      clientInfo,
      requestedAt: Date.now(),
      status: 'pending',
      expiresAt: Date.now() + 300000 // 5 minutes
    };

    this.pendingAuthorizations.set(authId, request);
    
    // Notify admins
    this.emit('approval-requested', request);
    
    // Add to warning queue
    this.warningQueue.push({
      type: 'access_request',
      message: `User '${user.username}' requesting access from ${clientInfo.ip}`,
      data: request,
      timestamp: Date.now()
    });

    logger.info(`Access approval requested for user '${user.username}'`, { 
      authId, 
      ip: clientInfo.ip 
    });

    return authId;
  }

  async approveAccess(authId, approvedBy) {
    const request = this.pendingAuthorizations.get(authId);
    if (!request) {
      return { success: false, error: 'Authorization request not found' };
    }

    if (Date.now() > request.expiresAt) {
      this.pendingAuthorizations.delete(authId);
      return { success: false, error: 'Authorization request expired' };
    }

    const user = this.userPermissions.get(request.user);
    if (!user) {
      this.pendingAuthorizations.delete(authId);
      return { success: false, error: 'User not found' };
    }

    // Create session
    const session = await this.createSession(user, request.clientInfo);
    
    // Clean up
    this.pendingAuthorizations.delete(authId);
    
    // Log approval
    logger.info(`Access approved for user '${user.username}' by '${approvedBy}'`, {
      authId,
      sessionId: session.id
    });
    
    this.emit('access-approved', { 
      user: user.username, 
      approvedBy, 
      sessionId: session.id 
    });

    return {
      success: true,
      token: session.token,
      sessionId: session.id,
      permissions: user.permissions,
      expiresAt: session.expiresAt
    };
  }

  async denyAccess(authId, deniedBy, reason) {
    const request = this.pendingAuthorizations.get(authId);
    if (!request) {
      return { success: false, error: 'Authorization request not found' };
    }

    this.pendingAuthorizations.delete(authId);
    
    logger.info(`Access denied for user '${request.user}' by '${deniedBy}'`, {
      authId,
      reason
    });
    
    this.emit('access-denied', {
      user: request.user,
      deniedBy,
      reason,
      authId
    });

    return { success: true, message: 'Access denied' };
  }

  async validateSession(token) {
    try {
      const decoded = jwt.verify(token, this.options.jwtSecret);
      const session = this.activeSessions.get(decoded.sessionId);
      
      if (!session) {
        return { valid: false, error: 'Session not found' };
      }

      if (Date.now() > session.expiresAt) {
        this.activeSessions.delete(session.id);
        return { valid: false, error: 'Session expired' };
      }

      // Update activity
      session.lastActivity = Date.now();
      
      return { 
        valid: true, 
        session,
        permissions: session.permissions,
        roles: session.roles
      };
    } catch (error) {
      return { valid: false, error: 'Invalid token' };
    }
  }

  hasPermission(sessionOrPermissions, requiredPermission) {
    const userPermissions = typeof sessionOrPermissions === 'object' 
      ? sessionOrPermissions.permissions 
      : sessionOrPermissions;
    
    return userPermissions >= requiredPermission;
  }

  async revokeSession(sessionId, reason = 'Manual revocation') {
    const session = this.activeSessions.get(sessionId);
    if (session) {
      this.activeSessions.delete(sessionId);
      
      logger.info(`Session revoked for user '${session.username}'`, {
        sessionId,
        reason
      });
      
      this.emit('session-revoked', { session, reason });
      return true;
    }
    return false;
  }

  async revokeAllSessions(userId, reason = 'Security action') {
    const sessions = Array.from(this.activeSessions.values())
      .filter(s => s.userId === userId);
    
    for (const session of sessions) {
      this.activeSessions.delete(session.id);
    }
    
    logger.info(`All sessions revoked for user ID '${userId}'`, {
      sessionCount: sessions.length,
      reason
    });
    
    this.emit('all-sessions-revoked', { userId, sessionCount: sessions.length, reason });
    return sessions.length;
  }

  async recordFailedAttempt(username, ip) {
    const key = `${username}:${ip}`;
    const attempts = this.failedAttempts.get(key) || { count: 0, firstAttempt: Date.now() };
    attempts.count++;
    attempts.lastAttempt = Date.now();
    
    this.failedAttempts.set(key, attempts);
    
    // Add warning if approaching lockout
    if (attempts.count >= this.options.maxFailedAttempts - 1) {
      this.warningQueue.push({
        type: 'security_alert',
        message: `Multiple failed login attempts for user '${username}' from ${ip}`,
        data: { username, ip, attempts: attempts.count },
        timestamp: Date.now()
      });
    }
  }

  async isLockedOut(username, ip) {
    const key = `${username}:${ip || '*'}`;
    const attempts = this.failedAttempts.get(key);
    
    if (!attempts || attempts.count < this.options.maxFailedAttempts) {
      return false;
    }
    
    const lockoutExpires = attempts.lastAttempt + this.options.lockoutDuration;
    return Date.now() < lockoutExpires;
  }

  cleanupExpiredSessions() {
    const now = Date.now();
    let cleaned = 0;
    
    for (const [sessionId, session] of this.activeSessions) {
      if (now > session.expiresAt) {
        this.activeSessions.delete(sessionId);
        cleaned++;
      }
    }
    
    if (cleaned > 0) {
      logger.debug(`Cleaned up ${cleaned} expired sessions`);
    }
  }

  cleanupFailedAttempts() {
    const now = Date.now();
    let cleaned = 0;
    
    for (const [key, attempts] of this.failedAttempts) {
      const expireTime = attempts.lastAttempt + this.options.lockoutDuration;
      if (now > expireTime) {
        this.failedAttempts.delete(key);
        cleaned++;
      }
    }
    
    if (cleaned > 0) {
      logger.debug(`Cleaned up ${cleaned} expired failed attempts`);
    }
  }

  // Public API methods
  getActiveSessions() {
    return Array.from(this.activeSessions.values()).map(session => ({
      id: session.id,
      username: session.username,
      permissions: session.permissions,
      clientInfo: session.clientInfo,
      createdAt: session.createdAt,
      lastActivity: session.lastActivity,
      expiresAt: session.expiresAt
    }));
  }

  getPendingApprovals() {
    return Array.from(this.pendingAuthorizations.values());
  }

  getWarnings() {
    const warnings = [...this.warningQueue];
    this.warningQueue = []; // Clear after reading
    return warnings;
  }

  getSystemStats() {
    return {
      activeSessions: this.activeSessions.size,
      pendingApprovals: this.pendingAuthorizations.size,
      failedAttempts: this.failedAttempts.size,
      totalUsers: this.userPermissions.size,
      warnings: this.warningQueue.length
    };
  }

  async cleanup() {
    this.activeSessions.clear();
    this.pendingAuthorizations.clear();
    this.failedAttempts.clear();
    this.warningQueue = [];
    this.removeAllListeners();
    
    logger.info('Permission System cleaned up');
  }
}

module.exports = PermissionSystem;