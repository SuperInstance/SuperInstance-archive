const EventEmitter = require('events');
const redis = require('ioredis');
const crypto = require('crypto');
const jwt = require('jsonwebtoken');
const Session = require('../models/Session');
const AuditLogger = require('./AuditLogger');

class SessionManager extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      sessionTimeout: config.sessionTimeout || 24 * 60 * 60 * 1000, // 24 hours
      extendOnActivity: config.extendOnActivity !== false,
      maxConcurrentSessions: config.maxConcurrentSessions || 5,
      secureSessionId: config.secureSessionId !== false,
      trackLocation: config.trackLocation !== false,
      ...config
    };
    
    this.auditLogger = new AuditLogger();
    this.redis = new redis({
      host: process.env.REDIS_HOST || 'localhost',
      port: process.env.REDIS_PORT || 6379,
      password: process.env.REDIS_PASSWORD
    });
    
    this.activeSessions = new Map();
    this.cleanupInterval = setInterval(() => this.cleanupExpiredSessions(), 60000);
  }

  async createSession(userId, deviceInfo, context = {}) {
    try {
      const sessionId = this.generateSecureSessionId();
      const expiresAt = new Date(Date.now() + this.config.sessionTimeout);
      
      // Check concurrent session limit
      await this.enforceSessionLimits(userId);
      
      const session = {
        sessionId,
        userId,
        status: 'active',
        createdAt: new Date(),
        lastActivityAt: new Date(),
        expiresAt,
        device: {
          fingerprint: deviceInfo.fingerprint,
          userAgent: deviceInfo.userAgent,
          platform: deviceInfo.platform,
          browser: deviceInfo.browser,
          os: deviceInfo.os,
          screen: deviceInfo.screen
        },
        location: context.location,
        ipAddress: context.ipAddress,
        metadata: context.metadata || {}
      };
      
      // Store in Redis for fast access
      await this.redis.setex(
        `session:${sessionId}`,
        Math.floor(this.config.sessionTimeout / 1000),
        JSON.stringify(session)
      );
      
      // Store in database for persistence
      const sessionDoc = new Session(session);
      await sessionDoc.save();
      
      // Track active session
      this.activeSessions.set(sessionId, session);
      
      await this.auditLogger.log('session_created', 'success', {
        userId,
        sessionId,
        deviceFingerprint: deviceInfo.fingerprint,
        ipAddress: context.ipAddress,
        userAgent: deviceInfo.userAgent
      });
      
      this.emit('session_created', { session, userId });
      
      return {
        sessionId,
        expiresAt,
        token: this.generateSessionToken(session)
      };
    } catch (error) {
      await this.auditLogger.log('session_created', 'failed', {
        userId,
        error: error.message,
        ipAddress: context.ipAddress
      });
      throw error;
    }
  }

  async getSession(sessionId) {
    try {
      // Try Redis first
      const cached = await this.redis.get(`session:${sessionId}`);
      if (cached) {
        return JSON.parse(cached);
      }
      
      // Fallback to database
      const session = await Session.findOne({ sessionId, status: 'active' });
      if (session && session.expiresAt > new Date()) {
        // Restore to Redis
        await this.redis.setex(
          `session:${sessionId}`,
          Math.floor((session.expiresAt - new Date()) / 1000),
          JSON.stringify(session.toObject())
        );
        return session.toObject();
      }
      
      return null;
    } catch (error) {
      console.error('Error retrieving session:', error);
      return null;
    }
  }

  async extendSession(sessionId, extensionTime) {
    try {
      const session = await this.getSession(sessionId);
      if (!session) {
        throw new Error('Session not found');
      }
      
      const newExpiresAt = new Date(Date.now() + (extensionTime || this.config.sessionTimeout));
      session.expiresAt = newExpiresAt;
      session.lastActivityAt = new Date();
      
      // Update Redis
      await this.redis.setex(
        `session:${sessionId}`,
        Math.floor((newExpiresAt - new Date()) / 1000),
        JSON.stringify(session)
      );
      
      // Update database
      await Session.updateOne(
        { sessionId },
        { 
          expiresAt: newExpiresAt,
          lastActivityAt: session.lastActivityAt
        }
      );
      
      this.activeSessions.set(sessionId, session);
      
      await this.auditLogger.log('session_extended', 'success', {
        userId: session.userId,
        sessionId,
        newExpiresAt
      });
      
      return session;
    } catch (error) {
      await this.auditLogger.log('session_extended', 'failed', {
        sessionId,
        error: error.message
      });
      throw error;
    }
  }

  async terminateSession(sessionId, reason = 'user_logout') {
    try {
      const session = await this.getSession(sessionId);
      if (!session) {
        return false;
      }
      
      // Remove from Redis
      await this.redis.del(`session:${sessionId}`);
      
      // Update database
      await Session.updateOne(
        { sessionId },
        { 
          status: 'terminated',
          terminatedAt: new Date(),
          terminationReason: reason
        }
      );
      
      // Remove from active sessions
      this.activeSessions.delete(sessionId);
      
      await this.auditLogger.log('session_terminated', 'success', {
        userId: session.userId,
        sessionId,
        reason
      });
      
      this.emit('session_terminated', { sessionId, userId: session.userId, reason });
      
      return true;
    } catch (error) {
      await this.auditLogger.log('session_terminated', 'failed', {
        sessionId,
        error: error.message
      });
      throw error;
    }
  }

  async revokeUserSessions(userId, exceptSessionId = null) {
    try {
      const sessions = await Session.find({
        userId,
        status: 'active',
        sessionId: { $ne: exceptSessionId }
      });
      
      const terminatedSessions = [];
      
      for (const session of sessions) {
        await this.terminateSession(session.sessionId, 'admin_revocation');
        terminatedSessions.push(session.sessionId);
      }
      
      await this.auditLogger.log('user_sessions_revoked', 'success', {
        userId,
        terminatedSessions: terminatedSessions.length,
        exceptSessionId
      });
      
      return terminatedSessions;
    } catch (error) {
      await this.auditLogger.log('user_sessions_revoked', 'failed', {
        userId,
        error: error.message
      });
      throw error;
    }
  }

  async getUserActiveSessions(userId) {
    try {
      const sessions = await Session.find({
        userId,
        status: 'active',
        expiresAt: { $gt: new Date() }
      }).sort({ lastActivityAt: -1 });
      
      return sessions.map(session => ({
        sessionId: session.sessionId,
        createdAt: session.createdAt,
        lastActivityAt: session.lastActivityAt,
        expiresAt: session.expiresAt,
        device: session.device,
        location: session.location,
        ipAddress: session.ipAddress,
        isCurrent: this.activeSessions.has(session.sessionId)
      }));
    } catch (error) {
      console.error('Error retrieving user sessions:', error);
      return [];
    }
  }

  async detectSuspiciousActivity(sessionId, activityData) {
    try {
      const session = await this.getSession(sessionId);
      if (!session) return false;
      
      const suspiciousFactors = [];
      
      // Check for location changes
      if (this.config.trackLocation && session.location && activityData.location) {
        const distance = this.calculateDistance(session.location, activityData.location);
        if (distance > 1000) { // 1000km
          suspiciousFactors.push('location_change');
        }
      }
      
      // Check for device fingerprint changes
      if (session.device.fingerprint !== activityData.deviceFingerprint) {
        suspiciousFactors.push('device_change');
      }
      
      // Check for rapid IP changes
      if (session.ipAddress !== activityData.ipAddress) {
        const timeDiff = new Date() - new Date(session.lastActivityAt);
        if (timeDiff < 300000) { // 5 minutes
          suspiciousFactors.push('rapid_ip_change');
        }
      }
      
      if (suspiciousFactors.length > 0) {
        await this.auditLogger.log('suspicious_activity_detected', 'warning', {
          userId: session.userId,
          sessionId,
          factors: suspiciousFactors,
          activityData
        });
        
        this.emit('suspicious_activity', {
          sessionId,
          userId: session.userId,
          factors: suspiciousFactors,
          session,
          activityData
        });
        
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Error detecting suspicious activity:', error);
      return false;
    }
  }

  async enforceSessionLimits(userId) {
    const activeSessions = await this.getUserActiveSessions(userId);
    
    if (activeSessions.length >= this.config.maxConcurrentSessions) {
      // Terminate oldest sessions
      const sessionsToTerminate = activeSessions
        .sort((a, b) => a.lastActivityAt - b.lastActivityAt)
        .slice(0, activeSessions.length - this.config.maxConcurrentSessions + 1);
      
      for (const session of sessionsToTerminate) {
        await this.terminateSession(session.sessionId, 'session_limit_exceeded');
      }
    }
  }

  async cleanupExpiredSessions() {
    try {
      const expiredSessions = await Session.find({
        status: 'active',
        expiresAt: { $lt: new Date() }
      });
      
      for (const session of expiredSessions) {
        await this.terminateSession(session.sessionId, 'expired');
      }
      
      // Clean up Redis keys
      const keys = await this.redis.keys('session:*');
      for (const key of keys) {
        const sessionData = await this.redis.get(key);
        if (sessionData) {
          const session = JSON.parse(sessionData);
          if (new Date(session.expiresAt) < new Date()) {
            await this.redis.del(key);
          }
        }
      }
    } catch (error) {
      console.error('Session cleanup error:', error);
    }
  }

  generateSecureSessionId() {
    return crypto.randomBytes(32).toString('hex');
  }

  generateSessionToken(session) {
    return jwt.sign(
      {
        sessionId: session.sessionId,
        userId: session.userId,
        iat: Math.floor(Date.now() / 1000)
      },
      process.env.JWT_SECRET,
      { expiresIn: '24h' }
    );
  }

  calculateDistance(loc1, loc2) {
    const R = 6371; // Earth's radius in km
    const dLat = this.deg2rad(loc2.lat - loc1.lat);
    const dLon = this.deg2rad(loc2.lon - loc1.lon);
    const a = 
      Math.sin(dLat/2) * Math.sin(dLat/2) +
      Math.cos(this.deg2rad(loc1.lat)) * Math.cos(this.deg2rad(loc2.lat)) * 
      Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  }

  deg2rad(deg) {
    return deg * (Math.PI/180);
  }

  destroy() {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
    if (this.redis) {
      this.redis.disconnect();
    }
  }
}

module.exports = SessionManager;