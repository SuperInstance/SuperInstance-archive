const { EventEmitter } = require('events');
const crypto = require('crypto');
const Redis = require('ioredis');

class SessionManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      sessionLifetime: options.sessionLifetime || 86400, // 24 hours
      renewalThreshold: options.renewalThreshold || 3600, // 1 hour
      maxSessions: options.maxSessions || 10, // Max concurrent sessions per user
      enableSlidingExpiration: options.enableSlidingExpiration !== false,
      enableCrossDomainSessions: options.enableCrossDomainSessions || true,
      cookieName: options.cookieName || 'activelog_session',
      cookieDomain: options.cookieDomain || '.activelog.com',
      redisUrl: options.redisUrl || 'redis://localhost:6379',
      ...options
    };
    
    this.sessions = new Map(); // In-memory sessions (fallback)
    this.userSessions = new Map(); // User ID -> Session IDs mapping
    this.crossDomainTokens = new Map(); // Cross-domain session tokens
    
    this.initializeRedis();
    this.setupCleanupInterval();
  }

  async initializeRedis() {
    try {
      this.redis = new Redis(this.options.redisUrl);
      this.redis.on('error', (error) => {
        console.error('Redis error:', error);
        this.emit('error', error);
      });
      
      this.redis.on('connect', () => {
        console.log('Connected to Redis for session storage');
      });
    } catch (error) {
      console.warn('Redis not available, falling back to in-memory storage');
      this.redis = null;
    }
  }

  // Session Creation and Management
  async createSession(user, options = {}) {
    const sessionId = this.generateSessionId();
    const deviceInfo = options.deviceInfo || {};
    
    const sessionData = {
      id: sessionId,
      userId: user.id,
      username: user.username,
      email: user.email,
      roles: user.roles || [],
      permissions: user.permissions || [],
      organization: user.organization,
      
      // Session metadata
      createdAt: new Date(),
      lastAccessedAt: new Date(),
      expiresAt: new Date(Date.now() + this.options.sessionLifetime * 1000),
      
      // Device and location info
      deviceInfo: {
        userAgent: deviceInfo.userAgent,
        fingerprint: deviceInfo.fingerprint,
        ip: deviceInfo.ip,
        location: deviceInfo.location,
        deviceType: deviceInfo.deviceType,
        browser: deviceInfo.browser,
        os: deviceInfo.os
      },
      
      // Session attributes
      attributes: options.attributes || {},
      scopes: options.scopes || [],
      
      // Security flags
      isActive: true,
      requiresMFA: user.mfaEnabled && !options.mfaVerified,
      riskScore: this.calculateRiskScore(deviceInfo, user),
      
      // Cross-domain support
      crossDomainToken: options.enableCrossDomain ? this.generateCrossDomainToken() : null
    };

    // Store session
    await this.storeSession(sessionId, sessionData);
    
    // Track user sessions
    await this.trackUserSession(user.id, sessionId);
    
    // Handle session limits
    await this.enforceSessionLimits(user.id);
    
    // Store cross-domain token if enabled
    if (sessionData.crossDomainToken) {
      await this.storeCrossDomainToken(sessionData.crossDomainToken, sessionId);
    }
    
    this.emit('sessionCreated', sessionData);
    return sessionData;
  }

  async getSession(sessionId) {
    let sessionData;
    
    if (this.redis) {
      try {
        const data = await this.redis.get(`session:${sessionId}`);
        sessionData = data ? JSON.parse(data) : null;
      } catch (error) {
        console.error('Redis get error:', error);
        sessionData = this.sessions.get(sessionId);
      }
    } else {
      sessionData = this.sessions.get(sessionId);
    }
    
    if (!sessionData) {
      return null;
    }
    
    // Convert date strings back to Date objects
    sessionData.createdAt = new Date(sessionData.createdAt);
    sessionData.lastAccessedAt = new Date(sessionData.lastAccessedAt);
    sessionData.expiresAt = new Date(sessionData.expiresAt);
    
    // Check if session is expired
    if (sessionData.expiresAt < new Date()) {
      await this.destroySession(sessionId);
      return null;
    }
    
    // Check if session is active
    if (!sessionData.isActive) {
      return null;
    }
    
    return sessionData;
  }

  async updateSession(sessionId, updates) {
    const session = await this.getSession(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    
    const updatedSession = {
      ...session,
      ...updates,
      lastAccessedAt: new Date()
    };
    
    // Update expiration if sliding expiration is enabled
    if (this.options.enableSlidingExpiration) {
      const timeUntilExpiry = session.expiresAt.getTime() - Date.now();
      if (timeUntilExpiry < this.options.renewalThreshold * 1000) {
        updatedSession.expiresAt = new Date(Date.now() + this.options.sessionLifetime * 1000);
      }
    }
    
    await this.storeSession(sessionId, updatedSession);
    this.emit('sessionUpdated', updatedSession);
    return updatedSession;
  }

  async renewSession(sessionId) {
    const session = await this.getSession(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    
    const renewedSession = {
      ...session,
      lastAccessedAt: new Date(),
      expiresAt: new Date(Date.now() + this.options.sessionLifetime * 1000)
    };
    
    await this.storeSession(sessionId, renewedSession);
    this.emit('sessionRenewed', renewedSession);
    return renewedSession;
  }

  async destroySession(sessionId) {
    const session = await this.getSession(sessionId);
    if (!session) {
      return false;
    }
    
    // Remove from storage
    if (this.redis) {
      try {
        await this.redis.del(`session:${sessionId}`);
      } catch (error) {
        console.error('Redis delete error:', error);
      }
    }
    this.sessions.delete(sessionId);
    
    // Remove from user sessions tracking
    await this.removeUserSession(session.userId, sessionId);
    
    // Remove cross-domain token
    if (session.crossDomainToken) {
      await this.removeCrossDomainToken(session.crossDomainToken);
    }
    
    this.emit('sessionDestroyed', session);
    return true;
  }

  async destroyUserSessions(userId, exceptSessionId = null) {
    const userSessionIds = await this.getUserSessions(userId);
    
    for (const sessionId of userSessionIds) {
      if (sessionId !== exceptSessionId) {
        await this.destroySession(sessionId);
      }
    }
    
    this.emit('userSessionsDestroyed', { userId, exceptSessionId });
  }

  // Cross-Domain Session Support
  async createCrossDomainSession(sessionId, targetDomain) {
    const session = await this.getSession(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    
    const crossDomainToken = this.generateCrossDomainToken();
    const tokenData = {
      sessionId,
      targetDomain,
      createdAt: new Date(),
      expiresAt: new Date(Date.now() + 300000), // 5 minutes
      used: false
    };
    
    await this.storeCrossDomainToken(crossDomainToken, tokenData);
    
    this.emit('crossDomainTokenCreated', { sessionId, targetDomain, token: crossDomainToken });
    return crossDomainToken;
  }

  async consumeCrossDomainToken(token) {
    let tokenData;
    
    if (this.redis) {
      try {
        const data = await this.redis.get(`crossdomain:${token}`);
        tokenData = data ? JSON.parse(data) : null;
      } catch (error) {
        console.error('Redis get error:', error);
        tokenData = this.crossDomainTokens.get(token);
      }
    } else {
      tokenData = this.crossDomainTokens.get(token);
    }
    
    if (!tokenData) {
      throw new Error('Invalid cross-domain token');
    }
    
    // Convert date strings back to Date objects
    if (typeof tokenData.createdAt === 'string') {
      tokenData.createdAt = new Date(tokenData.createdAt);
      tokenData.expiresAt = new Date(tokenData.expiresAt);
    }
    
    if (tokenData.expiresAt < new Date()) {
      await this.removeCrossDomainToken(token);
      throw new Error('Cross-domain token expired');
    }
    
    if (tokenData.used) {
      throw new Error('Cross-domain token already used');
    }
    
    // Mark as used
    tokenData.used = true;
    await this.storeCrossDomainToken(token, tokenData);
    
    // Get the original session
    const session = await this.getSession(tokenData.sessionId);
    if (!session) {
      throw new Error('Original session not found');
    }
    
    this.emit('crossDomainTokenConsumed', { token, sessionId: tokenData.sessionId });
    return session;
  }

  // Session Analysis and Security
  calculateRiskScore(deviceInfo, user) {
    let riskScore = 0;
    
    // Unknown device
    if (!deviceInfo.fingerprint || !this.isKnownDevice(user.id, deviceInfo.fingerprint)) {
      riskScore += 30;
    }
    
    // Unusual location
    if (deviceInfo.location && this.isUnusualLocation(user.id, deviceInfo.location)) {
      riskScore += 25;
    }
    
    // Suspicious user agent
    if (deviceInfo.userAgent && this.isSuspiciousUserAgent(deviceInfo.userAgent)) {
      riskScore += 20;
    }
    
    // Time-based factors
    const hour = new Date().getHours();
    if (hour < 6 || hour > 22) { // Outside normal hours
      riskScore += 10;
    }
    
    // Account age
    if (user.createdAt && Date.now() - user.createdAt.getTime() < 86400000) { // New account
      riskScore += 15;
    }
    
    return Math.min(riskScore, 100);
  }

  async getSessionAnalytics(userId, timeRange = 30) {
    const sessions = await this.getUserSessionHistory(userId, timeRange);
    
    const analytics = {
      totalSessions: sessions.length,
      activeSessions: sessions.filter(s => s.isActive).length,
      averageSessionDuration: this.calculateAverageSessionDuration(sessions),
      deviceTypes: this.groupSessionsByDeviceType(sessions),
      locations: this.groupSessionsByLocation(sessions),
      browsers: this.groupSessionsByBrowser(sessions),
      riskDistribution: this.analyzeRiskDistribution(sessions),
      timePatterns: this.analyzeTimePatterns(sessions)
    };
    
    return analytics;
  }

  // Session Validation and Security Checks
  async validateSession(sessionId, options = {}) {
    const session = await this.getSession(sessionId);
    if (!session) {
      return { valid: false, reason: 'Session not found' };
    }
    
    // Check basic validity
    if (!session.isActive) {
      return { valid: false, reason: 'Session inactive' };
    }
    
    if (session.expiresAt < new Date()) {
      return { valid: false, reason: 'Session expired' };
    }
    
    // Device fingerprint validation
    if (options.deviceFingerprint && session.deviceInfo.fingerprint !== options.deviceFingerprint) {
      await this.flagSuspiciousActivity(sessionId, 'device_mismatch');
      return { valid: false, reason: 'Device fingerprint mismatch' };
    }
    
    // IP address validation
    if (options.ipAddress && this.isSignificantIPChange(session.deviceInfo.ip, options.ipAddress)) {
      await this.flagSuspiciousActivity(sessionId, 'ip_change');
      return { valid: false, reason: 'Suspicious IP change' };
    }
    
    // MFA requirement check
    if (session.requiresMFA && !options.mfaVerified) {
      return { valid: false, reason: 'MFA required' };
    }
    
    // Risk score check
    if (session.riskScore > 75 && !options.highRiskApproved) {
      return { valid: false, reason: 'High risk session' };
    }
    
    return { valid: true, session };
  }

  async flagSuspiciousActivity(sessionId, activityType, details = {}) {
    const session = await this.getSession(sessionId);
    if (!session) {
      return;
    }
    
    const suspiciousActivity = {
      sessionId,
      userId: session.userId,
      activityType,
      details,
      timestamp: new Date(),
      resolved: false
    };
    
    // Store suspicious activity (in real implementation, use persistent storage)
    this.suspiciousActivities = this.suspiciousActivities || [];
    this.suspiciousActivities.push(suspiciousActivity);
    
    this.emit('suspiciousActivity', suspiciousActivity);
    
    // Auto-actions based on activity type
    if (activityType === 'device_mismatch' || activityType === 'ip_change') {
      // Require re-authentication
      await this.updateSession(sessionId, { requiresMFA: true });
    }
  }

  // Utility Methods
  async storeSession(sessionId, sessionData) {
    if (this.redis) {
      try {
        await this.redis.setex(
          `session:${sessionId}`,
          this.options.sessionLifetime,
          JSON.stringify(sessionData)
        );
      } catch (error) {
        console.error('Redis setex error:', error);
        this.sessions.set(sessionId, sessionData);
      }
    } else {
      this.sessions.set(sessionId, sessionData);
    }
  }

  async storeCrossDomainToken(token, tokenData) {
    if (this.redis) {
      try {
        await this.redis.setex(
          `crossdomain:${token}`,
          300, // 5 minutes
          JSON.stringify(tokenData)
        );
      } catch (error) {
        console.error('Redis setex error:', error);
        this.crossDomainTokens.set(token, tokenData);
      }
    } else {
      this.crossDomainTokens.set(token, tokenData);
    }
  }

  async removeCrossDomainToken(token) {
    if (this.redis) {
      try {
        await this.redis.del(`crossdomain:${token}`);
      } catch (error) {
        console.error('Redis delete error:', error);
      }
    }
    this.crossDomainTokens.delete(token);
  }

  async trackUserSession(userId, sessionId) {
    if (this.redis) {
      try {
        await this.redis.sadd(`user_sessions:${userId}`, sessionId);
      } catch (error) {
        console.error('Redis sadd error:', error);
        this.trackUserSessionInMemory(userId, sessionId);
      }
    } else {
      this.trackUserSessionInMemory(userId, sessionId);
    }
  }

  trackUserSessionInMemory(userId, sessionId) {
    if (!this.userSessions.has(userId)) {
      this.userSessions.set(userId, new Set());
    }
    this.userSessions.get(userId).add(sessionId);
  }

  async removeUserSession(userId, sessionId) {
    if (this.redis) {
      try {
        await this.redis.srem(`user_sessions:${userId}`, sessionId);
      } catch (error) {
        console.error('Redis srem error:', error);
        this.removeUserSessionInMemory(userId, sessionId);
      }
    } else {
      this.removeUserSessionInMemory(userId, sessionId);
    }
  }

  removeUserSessionInMemory(userId, sessionId) {
    if (this.userSessions.has(userId)) {
      this.userSessions.get(userId).delete(sessionId);
      if (this.userSessions.get(userId).size === 0) {
        this.userSessions.delete(userId);
      }
    }
  }

  async getUserSessions(userId) {
    if (this.redis) {
      try {
        return await this.redis.smembers(`user_sessions:${userId}`);
      } catch (error) {
        console.error('Redis smembers error:', error);
        return Array.from(this.userSessions.get(userId) || []);
      }
    } else {
      return Array.from(this.userSessions.get(userId) || []);
    }
  }

  async enforceSessionLimits(userId) {
    const sessionIds = await this.getUserSessions(userId);
    
    if (sessionIds.length <= this.options.maxSessions) {
      return;
    }
    
    // Get all sessions with their last access times
    const sessions = [];
    for (const sessionId of sessionIds) {
      const session = await this.getSession(sessionId);
      if (session) {
        sessions.push(session);
      }
    }
    
    // Sort by last access time (oldest first)
    sessions.sort((a, b) => a.lastAccessedAt.getTime() - b.lastAccessedAt.getTime());
    
    // Remove oldest sessions to stay within limit
    const sessionsToRemove = sessions.slice(0, sessions.length - this.options.maxSessions);
    for (const session of sessionsToRemove) {
      await this.destroySession(session.id);
    }
    
    this.emit('sessionLimitEnforced', { userId, removedSessions: sessionsToRemove.length });
  }

  generateSessionId() {
    return crypto.randomBytes(32).toString('hex');
  }

  generateCrossDomainToken() {
    return crypto.randomBytes(16).toString('base64url');
  }

  isKnownDevice(userId, fingerprint) {
    // Implementation would check against known device fingerprints
    return false;
  }

  isUnusualLocation(userId, location) {
    // Implementation would check against user's location history
    return false;
  }

  isSuspiciousUserAgent(userAgent) {
    // Basic checks for suspicious user agents
    const suspiciousPatterns = [
      /bot/i,
      /crawler/i,
      /spider/i,
      /scraper/i,
      /curl/i,
      /wget/i
    ];
    
    return suspiciousPatterns.some(pattern => pattern.test(userAgent));
  }

  isSignificantIPChange(oldIP, newIP) {
    if (!oldIP || !newIP) return false;
    
    // For IPv4, check if they're in different /24 subnets
    const oldParts = oldIP.split('.').slice(0, 3).join('.');
    const newParts = newIP.split('.').slice(0, 3).join('.');
    
    return oldParts !== newParts;
  }

  setupCleanupInterval() {
    // Clean up expired sessions every 15 minutes
    setInterval(async () => {
      await this.cleanupExpiredSessions();
    }, 15 * 60 * 1000);
  }

  async cleanupExpiredSessions() {
    // This is a simplified cleanup - in production you'd scan Redis keys
    const now = new Date();
    
    for (const [sessionId, session] of this.sessions) {
      if (session.expiresAt < now) {
        await this.destroySession(sessionId);
      }
    }
    
    // Clean up cross-domain tokens
    for (const [token, tokenData] of this.crossDomainTokens) {
      if (tokenData.expiresAt < now) {
        await this.removeCrossDomainToken(token);
      }
    }
  }

  // Analytics helper methods
  calculateAverageSessionDuration(sessions) {
    if (sessions.length === 0) return 0;
    
    const totalDuration = sessions.reduce((sum, session) => {
      const endTime = session.isActive ? new Date() : session.expiresAt;
      return sum + (endTime.getTime() - session.createdAt.getTime());
    }, 0);
    
    return totalDuration / sessions.length;
  }

  groupSessionsByDeviceType(sessions) {
    return sessions.reduce((groups, session) => {
      const deviceType = session.deviceInfo.deviceType || 'unknown';
      groups[deviceType] = (groups[deviceType] || 0) + 1;
      return groups;
    }, {});
  }

  groupSessionsByLocation(sessions) {
    return sessions.reduce((groups, session) => {
      const location = session.deviceInfo.location?.country || 'unknown';
      groups[location] = (groups[location] || 0) + 1;
      return groups;
    }, {});
  }

  groupSessionsByBrowser(sessions) {
    return sessions.reduce((groups, session) => {
      const browser = session.deviceInfo.browser || 'unknown';
      groups[browser] = (groups[browser] || 0) + 1;
      return groups;
    }, {});
  }

  analyzeRiskDistribution(sessions) {
    const distribution = { low: 0, medium: 0, high: 0 };
    
    sessions.forEach(session => {
      if (session.riskScore < 30) distribution.low++;
      else if (session.riskScore < 70) distribution.medium++;
      else distribution.high++;
    });
    
    return distribution;
  }

  analyzeTimePatterns(sessions) {
    const patterns = {
      hourly: new Array(24).fill(0),
      daily: new Array(7).fill(0)
    };
    
    sessions.forEach(session => {
      const hour = session.createdAt.getHours();
      const day = session.createdAt.getDay();
      patterns.hourly[hour]++;
      patterns.daily[day]++;
    });
    
    return patterns;
  }

  async getUserSessionHistory(userId, days) {
    // Simplified - in production would query persistent storage
    const sessions = [];
    const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    
    for (const session of this.sessions.values()) {
      if (session.userId === userId && session.createdAt > cutoff) {
        sessions.push(session);
      }
    }
    
    return sessions;
  }

  getStats() {
    return {
      activeSessions: this.sessions.size,
      crossDomainTokens: this.crossDomainTokens.size,
      usersWithSessions: this.userSessions.size,
      suspiciousActivities: this.suspiciousActivities?.length || 0
    };
  }

  reset() {
    this.sessions.clear();
    this.userSessions.clear();
    this.crossDomainTokens.clear();
    this.suspiciousActivities = [];
  }
}

module.exports = SessionManager;