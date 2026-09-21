const EventEmitter = require('events');
const crypto = require('crypto');
const winston = require('winston');
const AuditLog = require('../models/AuditLog');

class AuditLogger extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      logLevel: config.logLevel || 'info',
      retentionDays: config.retentionDays || 90,
      encryptSensitiveData: config.encryptSensitiveData !== false,
      realTimeAlerts: config.realTimeAlerts !== false,
      batchSize: config.batchSize || 100,
      flushInterval: config.flushInterval || 5000, // 5 seconds
      alertThresholds: {
        failedLogins: 5,
        dataAccess: 100,
        permissionChanges: 10
      },
      ...config
    };

    this.logBuffer = [];
    this.alertCounts = new Map();
    this.sensitiveFields = [
      'password', 'token', 'secret', 'key', 'credential', 
      'ssn', 'credit_card', 'bank_account', 'phone', 'email'
    ];

    this.initializeWinston();
    this.startBatchProcessor();
    this.scheduleCleanup();
  }

  initializeWinston() {
    this.logger = winston.createLogger({
      level: this.config.logLevel,
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
      ),
      transports: [
        new winston.transports.File({
          filename: 'logs/audit-error.log',
          level: 'error',
          maxsize: 10485760, // 10MB
          maxFiles: 5
        }),
        new winston.transports.File({
          filename: 'logs/audit.log',
          maxsize: 10485760, // 10MB
          maxFiles: 10
        }),
        new winston.transports.Console({
          format: winston.format.combine(
            winston.format.colorize(),
            winston.format.simple()
          )
        })
      ]
    });
  }

  async log(action, status, data = {}, metadata = {}) {
    try {
      const logEntry = {
        id: crypto.randomUUID(),
        timestamp: new Date(),
        action,
        status,
        userId: data.userId,
        organizationId: data.organizationId,
        sessionId: data.sessionId,
        ipAddress: data.ipAddress,
        userAgent: data.userAgent,
        resource: data.resource,
        resourceId: data.resourceId,
        changes: data.changes,
        context: data.context || {},
        metadata: {
          source: metadata.source || 'identity-federation',
          version: metadata.version || '1.0',
          severity: this.calculateSeverity(action, status),
          category: this.categorizeAction(action),
          ...metadata
        }
      };

      // Sanitize sensitive data
      if (this.config.encryptSensitiveData) {
        logEntry.data = this.sanitizeData(data);
      } else {
        logEntry.data = data;
      }

      // Add to buffer for batch processing
      this.logBuffer.push(logEntry);

      // Log to Winston immediately for critical events
      if (logEntry.metadata.severity === 'critical' || status === 'failed') {
        this.logger.log(logEntry.metadata.severity, 'Audit Event', logEntry);
      }

      // Check for real-time alerts
      if (this.config.realTimeAlerts) {
        await this.checkAlertThresholds(logEntry);
      }

      this.emit('audit_logged', logEntry);
      return logEntry.id;
    } catch (error) {
      console.error('Failed to create audit log:', error);
      this.logger.error('Audit logging failed', { error: error.message, action, status });
      throw error;
    }
  }

  startBatchProcessor() {
    setInterval(async () => {
      if (this.logBuffer.length > 0) {
        await this.flushBuffer();
      }
    }, this.config.flushInterval);
  }

  async flushBuffer() {
    if (this.logBuffer.length === 0) return;

    const logsToProcess = this.logBuffer.splice(0, this.config.batchSize);
    
    try {
      // Save to database
      await AuditLog.insertMany(logsToProcess);

      // Log batch completion
      this.logger.info('Audit logs batch processed', { 
        count: logsToProcess.length,
        timestamp: new Date()
      });

      this.emit('batch_processed', {
        count: logsToProcess.length,
        logs: logsToProcess
      });
    } catch (error) {
      console.error('Failed to process audit log batch:', error);
      // Re-add logs to buffer for retry
      this.logBuffer.unshift(...logsToProcess);
      
      this.logger.error('Audit log batch processing failed', {
        error: error.message,
        count: logsToProcess.length
      });
    }
  }

  async getUserAuditLog(userId, options = {}) {
    try {
      const query = { userId };
      
      if (options.action) {
        query.action = options.action;
      }
      
      if (options.status) {
        query.status = options.status;
      }
      
      if (options.organizationIds && options.organizationIds.length > 0) {
        query.organizationId = { $in: options.organizationIds };
      }
      
      if (options.startDate || options.endDate) {
        query.timestamp = {};
        if (options.startDate) {
          query.timestamp.$gte = new Date(options.startDate);
        }
        if (options.endDate) {
          query.timestamp.$lte = new Date(options.endDate);
        }
      }

      const logs = await AuditLog.find(query)
        .sort({ timestamp: -1 })
        .limit(options.limit || 100)
        .skip(options.offset || 0);

      return logs.map(log => ({
        id: log.id,
        timestamp: log.timestamp,
        action: log.action,
        status: log.status,
        resource: log.resource,
        context: log.context,
        severity: log.metadata?.severity
      }));
    } catch (error) {
      this.logger.error('Failed to retrieve user audit log', {
        userId,
        error: error.message
      });
      throw error;
    }
  }

  async getOrganizationAuditLog(organizationId, options = {}) {
    try {
      const query = { organizationId };
      
      if (options.action) {
        query.action = options.action;
      }
      
      if (options.userId) {
        query.userId = options.userId;
      }
      
      if (options.startDate || options.endDate) {
        query.timestamp = {};
        if (options.startDate) {
          query.timestamp.$gte = new Date(options.startDate);
        }
        if (options.endDate) {
          query.timestamp.$lte = new Date(options.endDate);
        }
      }

      const logs = await AuditLog.find(query)
        .sort({ timestamp: -1 })
        .limit(options.limit || 100)
        .skip(options.offset || 0);

      return logs;
    } catch (error) {
      this.logger.error('Failed to retrieve organization audit log', {
        organizationId,
        error: error.message
      });
      throw error;
    }
  }

  async getSecurityEvents(options = {}) {
    try {
      const securityActions = [
        'authentication',
        'authorization_failed',
        'permission_granted',
        'permission_revoked',
        'role_assigned',
        'role_removed',
        'account_locked',
        'password_changed',
        'mfa_enabled',
        'mfa_disabled',
        'suspicious_activity',
        'data_breach',
        'unauthorized_access'
      ];

      const query = {
        action: { $in: securityActions }
      };

      if (options.severity) {
        query['metadata.severity'] = options.severity;
      }

      if (options.status) {
        query.status = options.status;
      }

      if (options.startDate || options.endDate) {
        query.timestamp = {};
        if (options.startDate) {
          query.timestamp.$gte = new Date(options.startDate);
        }
        if (options.endDate) {
          query.timestamp.$lte = new Date(options.endDate);
        }
      }

      const events = await AuditLog.find(query)
        .sort({ timestamp: -1 })
        .limit(options.limit || 50);

      return events;
    } catch (error) {
      this.logger.error('Failed to retrieve security events', {
        error: error.message
      });
      throw error;
    }
  }

  async generateComplianceReport(options = {}) {
    try {
      const startDate = options.startDate ? new Date(options.startDate) : new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
      const endDate = options.endDate ? new Date(options.endDate) : new Date();

      const pipeline = [
        {
          $match: {
            timestamp: { $gte: startDate, $lte: endDate }
          }
        },
        {
          $group: {
            _id: {
              action: '$action',
              status: '$status',
              category: '$metadata.category'
            },
            count: { $sum: 1 },
            users: { $addToSet: '$userId' },
            organizations: { $addToSet: '$organizationId' }
          }
        },
        {
          $project: {
            action: '$_id.action',
            status: '$_id.status',
            category: '$_id.category',
            count: 1,
            uniqueUsers: { $size: '$users' },
            uniqueOrganizations: { $size: '$organizations' }
          }
        },
        { $sort: { count: -1 } }
      ];

      const results = await AuditLog.aggregate(pipeline);

      const report = {
        period: { startDate, endDate },
        summary: {
          totalEvents: results.reduce((sum, r) => sum + r.count, 0),
          totalUsers: new Set(results.flatMap(r => r.users)).size,
          totalOrganizations: new Set(results.flatMap(r => r.organizations)).size
        },
        eventsByAction: results,
        complianceChecks: await this.runComplianceChecks(startDate, endDate)
      };

      this.emit('compliance_report_generated', report);
      return report;
    } catch (error) {
      this.logger.error('Failed to generate compliance report', {
        error: error.message
      });
      throw error;
    }
  }

  async runComplianceChecks(startDate, endDate) {
    const checks = {
      gdpr: await this.checkGDPRCompliance(startDate, endDate),
      dataRetention: await this.checkDataRetentionCompliance(),
      accessControls: await this.checkAccessControlCompliance(startDate, endDate),
      encryption: await this.checkEncryptionCompliance()
    };

    return checks;
  }

  async checkGDPRCompliance(startDate, endDate) {
    const gdprEvents = await AuditLog.find({
      timestamp: { $gte: startDate, $lte: endDate },
      action: {
        $in: [
          'data_access_request',
          'data_deletion_request',
          'consent_granted',
          'consent_withdrawn',
          'data_portability_request'
        ]
      }
    });

    return {
      totalRequests: gdprEvents.length,
      processed: gdprEvents.filter(e => e.status === 'completed').length,
      avgProcessingTime: this.calculateAvgProcessingTime(gdprEvents),
      compliance: gdprEvents.length > 0 ? gdprEvents.filter(e => e.status === 'completed').length / gdprEvents.length : 1
    };
  }

  async checkDataRetentionCompliance() {
    const expiredData = await AuditLog.find({
      timestamp: { $lt: new Date(Date.now() - this.config.retentionDays * 24 * 60 * 60 * 1000) }
    }).countDocuments();

    return {
      expiredRecords: expiredData,
      retentionPolicy: `${this.config.retentionDays} days`,
      compliant: expiredData === 0
    };
  }

  async checkAccessControlCompliance(startDate, endDate) {
    const accessEvents = await AuditLog.find({
      timestamp: { $gte: startDate, $lte: endDate },
      action: { $in: ['authorization_failed', 'unauthorized_access'] }
    });

    return {
      unauthorizedAttempts: accessEvents.length,
      blockedAttempts: accessEvents.filter(e => e.status === 'blocked').length,
      alertsTriggered: accessEvents.filter(e => e.metadata?.alertTriggered).length
    };
  }

  async checkEncryptionCompliance() {
    const encryptedLogs = await AuditLog.find({
      'metadata.encrypted': true
    }).countDocuments();

    const totalLogs = await AuditLog.countDocuments();

    return {
      encryptedRecords: encryptedLogs,
      totalRecords: totalLogs,
      encryptionRate: totalLogs > 0 ? encryptedLogs / totalLogs : 0
    };
  }

  async checkAlertThresholds(logEntry) {
    const { action, status, userId } = logEntry;
    const key = `${action}:${userId}`;
    const now = Date.now();
    const windowMs = 60 * 60 * 1000; // 1 hour window

    // Initialize or clean old entries
    if (!this.alertCounts.has(key)) {
      this.alertCounts.set(key, []);
    }

    const counts = this.alertCounts.get(key);
    const recentCounts = counts.filter(timestamp => now - timestamp < windowMs);
    recentCounts.push(now);
    this.alertCounts.set(key, recentCounts);

    // Check thresholds
    const threshold = this.config.alertThresholds[this.mapActionToThreshold(action)];
    if (threshold && recentCounts.length >= threshold) {
      await this.triggerAlert({
        type: 'threshold_exceeded',
        action,
        userId,
        count: recentCounts.length,
        threshold,
        timeWindow: '1 hour',
        logEntry
      });
    }

    // Check for specific patterns
    if (status === 'failed' && action === 'authentication') {
      if (recentCounts.length >= this.config.alertThresholds.failedLogins) {
        await this.triggerAlert({
          type: 'suspicious_login_activity',
          userId,
          count: recentCounts.length,
          logEntry
        });
      }
    }
  }

  async triggerAlert(alertData) {
    const alert = {
      id: crypto.randomUUID(),
      timestamp: new Date(),
      severity: this.calculateAlertSeverity(alertData),
      ...alertData
    };

    this.logger.warn('Security Alert Triggered', alert);
    this.emit('security_alert', alert);

    // Log the alert itself
    await this.log('security_alert', 'triggered', {
      alertId: alert.id,
      alertType: alert.type,
      severity: alert.severity
    });
  }

  scheduleCleanup() {
    // Run cleanup daily
    setInterval(async () => {
      await this.cleanupExpiredLogs();
    }, 24 * 60 * 60 * 1000);
  }

  async cleanupExpiredLogs() {
    try {
      const cutoffDate = new Date(Date.now() - this.config.retentionDays * 24 * 60 * 60 * 1000);
      
      const result = await AuditLog.deleteMany({
        timestamp: { $lt: cutoffDate }
      });

      this.logger.info('Audit log cleanup completed', {
        deletedCount: result.deletedCount,
        cutoffDate
      });

      this.emit('logs_cleaned', {
        deletedCount: result.deletedCount,
        cutoffDate
      });
    } catch (error) {
      this.logger.error('Audit log cleanup failed', {
        error: error.message
      });
    }
  }

  // Helper methods

  sanitizeData(data) {
    const sanitized = { ...data };
    
    for (const [key, value] of Object.entries(sanitized)) {
      if (this.isSensitiveField(key)) {
        if (this.config.encryptSensitiveData && typeof value === 'string') {
          sanitized[key] = this.encryptValue(value);
        } else {
          sanitized[key] = '[REDACTED]';
        }
      }
      
      if (typeof value === 'object' && value !== null) {
        sanitized[key] = this.sanitizeData(value);
      }
    }
    
    return sanitized;
  }

  isSensitiveField(fieldName) {
    const lowerName = fieldName.toLowerCase();
    return this.sensitiveFields.some(sensitive => lowerName.includes(sensitive));
  }

  encryptValue(value) {
    const algorithm = 'aes-256-gcm';
    const key = crypto.scryptSync(process.env.ENCRYPTION_KEY || 'default-key', 'salt', 32);
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipher(algorithm, key);
    
    let encrypted = cipher.update(value, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    return `encrypted:${iv.toString('hex')}:${encrypted}`;
  }

  calculateSeverity(action, status) {
    const criticalActions = ['data_breach', 'unauthorized_access', 'account_takeover'];
    const highActions = ['permission_granted', 'role_assigned', 'mfa_disabled'];
    const mediumActions = ['authentication', 'data_access', 'password_changed'];

    if (criticalActions.includes(action) || (status === 'failed' && highActions.includes(action))) {
      return 'critical';
    }
    
    if (highActions.includes(action) || (status === 'failed' && mediumActions.includes(action))) {
      return 'high';
    }
    
    if (mediumActions.includes(action) || status === 'failed') {
      return 'medium';
    }
    
    return 'low';
  }

  categorizeAction(action) {
    const categories = {
      'authentication': 'auth',
      'authorization': 'auth',
      'permission_granted': 'access',
      'permission_revoked': 'access',
      'role_assigned': 'access',
      'data_access': 'data',
      'data_export': 'data',
      'data_deletion': 'data',
      'consent_granted': 'privacy',
      'consent_withdrawn': 'privacy',
      'user_created': 'account',
      'user_deleted': 'account',
      'organization_created': 'organization',
      'organization_updated': 'organization'
    };

    return categories[action] || 'general';
  }

  calculateAlertSeverity(alertData) {
    if (alertData.type === 'suspicious_login_activity' || alertData.count > 20) {
      return 'critical';
    }
    
    if (alertData.count > 10) {
      return 'high';
    }
    
    return 'medium';
  }

  mapActionToThreshold(action) {
    const mapping = {
      'authentication': 'failedLogins',
      'authorization_failed': 'failedLogins',
      'data_access': 'dataAccess',
      'data_export': 'dataAccess',
      'permission_granted': 'permissionChanges',
      'permission_revoked': 'permissionChanges',
      'role_assigned': 'permissionChanges'
    };

    return mapping[action] || 'failedLogins';
  }

  calculateAvgProcessingTime(events) {
    const processedEvents = events.filter(e => e.completedAt && e.requestedAt);
    if (processedEvents.length === 0) return 0;

    const totalTime = processedEvents.reduce((sum, event) => {
      return sum + (new Date(event.completedAt) - new Date(event.requestedAt));
    }, 0);

    return Math.round(totalTime / processedEvents.length / (1000 * 60 * 60 * 24)); // Convert to days
  }
}

module.exports = AuditLogger;