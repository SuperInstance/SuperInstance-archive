const EventEmitter = require('events');
const logger = require('../core/logger');
const { v4: uuidv4 } = require('uuid');

class PermissionWarningSystem extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      // Warning thresholds
      maxFailedAttempts: options.maxFailedAttempts || 3,
      suspiciousActivityThreshold: options.suspiciousActivityThreshold || 5,
      rapidRequestThreshold: options.rapidRequestThreshold || 10, // requests per minute
      
      // Warning levels
      warningLevels: options.warningLevels || {
        LOW: { priority: 1, color: 'yellow', retentionDays: 7 },
        MEDIUM: { priority: 2, color: 'orange', retentionDays: 14 },
        HIGH: { priority: 3, color: 'red', retentionDays: 30 },
        CRITICAL: { priority: 4, color: 'purple', retentionDays: 90 }
      },
      
      // Alert delivery
      enableEmailAlerts: options.enableEmailAlerts !== false,
      enableSmsAlerts: options.enableSmsAlerts || false,
      enableSlackAlerts: options.enableSlackAlerts || false,
      enablePushNotifications: options.enablePushNotifications !== false,
      
      // Rate limiting
      alertRateLimit: options.alertRateLimit || 60000, // 1 minute between similar alerts
      maxAlertsPerHour: options.maxAlertsPerHour || 50,
      
      // Admin notifications
      adminNotificationThreshold: options.adminNotificationThreshold || 'HIGH',
      autoEscalationEnabled: options.autoEscalationEnabled !== false,
      escalationTimeWindow: options.escalationTimeWindow || 300000, // 5 minutes
      
      // Monitoring
      trackUserBehavior: options.trackUserBehavior !== false,
      trackSystemAccess: options.trackSystemAccess !== false,
      trackDataAccess: options.trackDataAccess !== false,
      
      // Integration
      syslogEnabled: options.syslogEnabled || false,
      webhookUrl: options.webhookUrl,
      
      ...options
    };

    // Warning system state
    this.activeWarnings = new Map(); // warningId -> warning
    this.userWarnings = new Map(); // userId -> warnings[]
    this.warningHistory = new Map(); // date -> warnings[]
    this.alertQueue = [];
    this.suppressedAlerts = new Set(); // For rate limiting
    
    // User behavior tracking
    this.userSessions = new Map(); // userId -> session data
    this.accessPatterns = new Map(); // userId -> patterns
    this.failedAttempts = new Map(); // userId -> attempts[]
    this.suspiciousActivities = new Map(); // userId -> activities[]
    
    // System monitoring
    this.systemEvents = [];
    this.escalatedWarnings = new Map();
    this.adminNotifications = [];
    
    // Metrics
    this.metrics = {
      totalWarnings: 0,
      warningsByLevel: {
        LOW: 0,
        MEDIUM: 0,
        HIGH: 0,
        CRITICAL: 0
      },
      alertsSent: 0,
      falsePosistives: 0,
      resolvedWarnings: 0,
      escalatedWarnings: 0
    };

    // Warning rules
    this.warningRules = new Map();
    this.initializeDefaultRules();
  }

  async initialize() {
    logger.info('Initializing Permission Warning System...');
    
    try {
      // Start monitoring
      this.startSystemMonitoring();
      
      // Start cleanup routines
      this.startCleanupRoutines();
      
      // Start alert processing
      this.startAlertProcessing();
      
      logger.info('Permission Warning System initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Permission Warning System:', error);
      throw error;
    }
  }

  initializeDefaultRules() {
    // Authentication failures
    this.addWarningRule('failed_authentication', {
      threshold: this.options.maxFailedAttempts,
      timeWindow: 900000, // 15 minutes
      level: 'MEDIUM',
      description: 'Multiple failed authentication attempts',
      action: 'lock_account'
    });

    // Privilege escalation attempts
    this.addWarningRule('privilege_escalation', {
      threshold: 1,
      timeWindow: 60000,
      level: 'HIGH',
      description: 'Unauthorized privilege escalation attempt',
      action: 'alert_admin'
    });

    // Unusual access patterns
    this.addWarningRule('unusual_access_pattern', {
      threshold: 1,
      timeWindow: 300000,
      level: 'MEDIUM',
      description: 'Access from unusual location or time',
      action: 'require_additional_auth'
    });

    // Data access violations
    this.addWarningRule('data_access_violation', {
      threshold: 1,
      timeWindow: 60000,
      level: 'HIGH',
      description: 'Attempted access to restricted data',
      action: 'alert_admin'
    });

    // Rapid API requests
    this.addWarningRule('api_abuse', {
      threshold: this.options.rapidRequestThreshold,
      timeWindow: 60000,
      level: 'LOW',
      description: 'Unusual number of API requests',
      action: 'rate_limit'
    });

    // Permission changes
    this.addWarningRule('permission_change', {
      threshold: 1,
      timeWindow: 60000,
      level: 'HIGH',
      description: 'Unauthorized permission modification attempt',
      action: 'alert_admin'
    });

    // System access outside hours
    this.addWarningRule('after_hours_access', {
      threshold: 1,
      timeWindow: 3600000,
      level: 'MEDIUM',
      description: 'System access outside normal hours',
      action: 'log_and_monitor'
    });
  }

  addWarningRule(ruleId, rule) {
    this.warningRules.set(ruleId, {
      id: ruleId,
      ...rule,
      createdAt: Date.now(),
      enabled: true,
      triggerCount: 0
    });
  }

  async checkPermissionAccess(userId, resource, action, context = {}) {
    const event = {
      userId,
      resource,
      action,
      context,
      timestamp: Date.now(),
      ip: context.ip,
      userAgent: context.userAgent
    };

    // Check various warning conditions
    await this.checkFailedAttempts(event);
    await this.checkUnusualAccess(event);
    await this.checkPrivilegeEscalation(event);
    await this.checkDataAccess(event);
    await this.checkApiAbuse(event);

    // Track user behavior
    this.trackUserBehavior(event);
  }

  async checkFailedAttempts(event) {
    if (event.context.success === false) {
      const attempts = this.failedAttempts.get(event.userId) || [];
      attempts.push({
        timestamp: event.timestamp,
        resource: event.resource,
        action: event.action,
        ip: event.ip
      });

      // Keep only recent attempts
      const recentAttempts = attempts.filter(a => 
        event.timestamp - a.timestamp < 900000 // 15 minutes
      );

      this.failedAttempts.set(event.userId, recentAttempts);

      // Check threshold
      if (recentAttempts.length >= this.options.maxFailedAttempts) {
        await this.createWarning('failed_authentication', event, {
          attemptCount: recentAttempts.length,
          timeWindow: '15 minutes',
          lastAttempt: new Date(event.timestamp).toISOString()
        });
      }
    } else {
      // Clear failed attempts on success
      this.failedAttempts.delete(event.userId);
    }
  }

  async checkUnusualAccess(event) {
    const patterns = this.accessPatterns.get(event.userId) || {
      locations: new Set(),
      hours: new Set(),
      userAgents: new Set()
    };

    const hour = new Date(event.timestamp).getHours();
    const location = event.ip?.split('.').slice(0, 3).join('.') || 'unknown';

    // Check for new location
    if (event.ip && !patterns.locations.has(location)) {
      patterns.locations.add(location);
      
      if (patterns.locations.size > 1) {
        await this.createWarning('unusual_access_pattern', event, {
          reason: 'new_location',
          location,
          previousLocations: Array.from(patterns.locations)
        });
      }
    }

    // Check for unusual hours
    patterns.hours.add(hour);
    if (hour < 6 || hour > 22) { // Outside 6 AM - 10 PM
      const recentAfterHours = this.countRecentEvents(event.userId, 'after_hours_access', 3600000);
      if (recentAfterHours === 0) {
        await this.createWarning('after_hours_access', event, {
          hour,
          timestamp: new Date(event.timestamp).toISOString()
        });
      }
    }

    // Update patterns
    this.accessPatterns.set(event.userId, patterns);
  }

  async checkPrivilegeEscalation(event) {
    if (event.action === 'elevate_permissions' || 
        event.action === 'modify_permissions' ||
        event.resource.includes('admin') ||
        event.resource.includes('system')) {
      
      await this.createWarning('privilege_escalation', event, {
        attemptedResource: event.resource,
        attemptedAction: event.action,
        userRole: event.context.userRole
      });
    }
  }

  async checkDataAccess(event) {
    const restrictedResources = [
      'user_data', 'financial_data', 'personal_info',
      'credentials', 'system_config', 'audit_logs'
    ];

    if (restrictedResources.some(resource => event.resource.includes(resource))) {
      // Check if user has proper permissions
      if (!event.context.hasPermission) {
        await this.createWarning('data_access_violation', event, {
          restrictedResource: event.resource,
          userPermissions: event.context.permissions || []
        });
      }
    }
  }

  async checkApiAbuse(event) {
    const userId = event.userId;
    const now = event.timestamp;
    const timeWindow = 60000; // 1 minute
    
    // Count recent requests
    const recentRequests = this.countRecentEvents(userId, 'api_request', timeWindow);
    
    if (recentRequests >= this.options.rapidRequestThreshold) {
      await this.createWarning('api_abuse', event, {
        requestCount: recentRequests,
        timeWindow: '1 minute',
        threshold: this.options.rapidRequestThreshold
      });
    }

    // Track the request
    this.trackEvent(userId, 'api_request', event);
  }

  async createWarning(ruleId, event, details = {}) {
    const rule = this.warningRules.get(ruleId);
    if (!rule || !rule.enabled) return null;

    // Check if similar warning exists recently
    if (this.hasSimilarRecentWarning(ruleId, event.userId, 300000)) {
      return null; // Suppress duplicate
    }

    const warningId = uuidv4();
    const warning = {
      id: warningId,
      ruleId,
      ruleName: rule.description,
      level: rule.level,
      userId: event.userId,
      
      // Event details
      resource: event.resource,
      action: event.action,
      timestamp: event.timestamp,
      ip: event.ip,
      userAgent: event.userAgent,
      
      // Warning details
      details,
      status: 'active', // active, acknowledged, resolved, false_positive
      
      // Metadata
      createdAt: Date.now(),
      acknowledgedBy: null,
      acknowledgedAt: null,
      resolvedAt: null,
      escalated: false,
      
      // Actions taken
      actionsTaken: [],
      recommendedActions: this.getRecommendedActions(rule, details)
    };

    // Store warning
    this.activeWarnings.set(warningId, warning);
    
    // Add to user warnings
    const userWarnings = this.userWarnings.get(event.userId) || [];
    userWarnings.push(warningId);
    this.userWarnings.set(event.userId, userWarnings);

    // Update metrics
    this.metrics.totalWarnings++;
    this.metrics.warningsByLevel[rule.level]++;
    rule.triggerCount++;

    // Execute automatic actions
    await this.executeWarningActions(warning, rule);

    // Create alert
    await this.createAlert(warning);

    // Check for escalation
    if (this.shouldEscalate(warning)) {
      await this.escalateWarning(warning);
    }

    logger.warn(`Permission warning created: ${rule.description}`, {
      warningId,
      userId: event.userId,
      level: rule.level,
      resource: event.resource
    });

    this.emit('warning-created', warning);

    return warning;
  }

  async executeWarningActions(warning, rule) {
    const actions = [];

    switch (rule.action) {
      case 'lock_account':
        actions.push('Account temporarily locked');
        this.emit('account-lock-required', { userId: warning.userId, reason: rule.description });
        break;

      case 'alert_admin':
        actions.push('Administrator notified');
        await this.notifyAdministrators(warning);
        break;

      case 'require_additional_auth':
        actions.push('Additional authentication required');
        this.emit('additional-auth-required', { userId: warning.userId });
        break;

      case 'rate_limit':
        actions.push('Rate limiting applied');
        this.emit('rate-limit-required', { userId: warning.userId });
        break;

      case 'log_and_monitor':
        actions.push('Enhanced monitoring activated');
        break;
    }

    warning.actionsTaken = actions;
  }

  getRecommendedActions(rule, details) {
    const actions = [];

    switch (rule.id) {
      case 'failed_authentication':
        actions.push('Verify user identity');
        actions.push('Check for credential compromise');
        actions.push('Consider temporary account lock');
        break;

      case 'privilege_escalation':
        actions.push('Immediate investigation required');
        actions.push('Review user permissions');
        actions.push('Check system integrity');
        break;

      case 'unusual_access_pattern':
        actions.push('Verify user location');
        actions.push('Confirm user identity');
        actions.push('Monitor additional activities');
        break;

      case 'data_access_violation':
        actions.push('Investigate access attempt');
        actions.push('Review data permissions');
        actions.push('Consider security audit');
        break;

      default:
        actions.push('Review and investigate');
        break;
    }

    return actions;
  }

  async createAlert(warning) {
    const alertId = uuidv4();
    const alert = {
      id: alertId,
      warningId: warning.id,
      level: warning.level,
      title: `Security Warning: ${warning.ruleName}`,
      message: this.generateAlertMessage(warning),
      timestamp: Date.now(),
      channels: [],
      delivered: false,
      attempts: 0
    };

    // Determine delivery channels
    const levelPriority = this.options.warningLevels[warning.level].priority;

    if (levelPriority >= 2 && this.options.enableEmailAlerts) {
      alert.channels.push('email');
    }

    if (levelPriority >= 3 && this.options.enableSmsAlerts) {
      alert.channels.push('sms');
    }

    if (this.options.enableSlackAlerts) {
      alert.channels.push('slack');
    }

    if (levelPriority >= 2 && this.options.enablePushNotifications) {
      alert.channels.push('push');
    }

    // Check rate limiting
    const alertKey = `${warning.ruleId}_${warning.userId}`;
    if (!this.suppressedAlerts.has(alertKey)) {
      this.alertQueue.push(alert);
      this.suppressedAlerts.add(alertKey);
      
      // Remove suppression after rate limit period
      setTimeout(() => {
        this.suppressedAlerts.delete(alertKey);
      }, this.options.alertRateLimit);
    }

    return alert;
  }

  generateAlertMessage(warning) {
    return `
Security Warning: ${warning.ruleName}

User: ${warning.userId}
Level: ${warning.level}
Resource: ${warning.resource}
Action: ${warning.action}
Time: ${new Date(warning.timestamp).toISOString()}
IP: ${warning.ip}

Details:
${JSON.stringify(warning.details, null, 2)}

Recommended Actions:
${warning.recommendedActions.map(action => `• ${action}`).join('\n')}
    `.trim();
  }

  shouldEscalate(warning) {
    const levelPriority = this.options.warningLevels[warning.level].priority;
    const adminThresholdPriority = this.options.warningLevels[this.options.adminNotificationThreshold].priority;

    return levelPriority >= adminThresholdPriority;
  }

  async escalateWarning(warning) {
    if (warning.escalated) return;

    warning.escalated = true;
    this.escalatedWarnings.set(warning.id, {
      warningId: warning.id,
      escalatedAt: Date.now(),
      escalationReason: 'High priority security event'
    });

    this.metrics.escalatedWarnings++;

    await this.notifyAdministrators(warning);

    this.emit('warning-escalated', warning);

    logger.error(`Warning escalated: ${warning.ruleName}`, {
      warningId: warning.id,
      userId: warning.userId,
      level: warning.level
    });
  }

  async notifyAdministrators(warning) {
    const notification = {
      id: uuidv4(),
      warningId: warning.id,
      type: 'admin_notification',
      title: `ESCALATED: ${warning.ruleName}`,
      message: this.generateAlertMessage(warning),
      timestamp: Date.now(),
      priority: 'high'
    };

    this.adminNotifications.push(notification);

    // Emit for external handling
    this.emit('admin-notification', notification);

    logger.info(`Administrator notification created`, {
      notificationId: notification.id,
      warningId: warning.id
    });
  }

  async acknowledgeWarning(warningId, acknowledgedBy, notes = '') {
    const warning = this.activeWarnings.get(warningId);
    if (!warning || warning.status !== 'active') {
      throw new Error('Warning not found or already acknowledged');
    }

    warning.status = 'acknowledged';
    warning.acknowledgedBy = acknowledgedBy;
    warning.acknowledgedAt = Date.now();
    warning.acknowledgeNotes = notes;

    logger.info(`Warning acknowledged`, {
      warningId,
      acknowledgedBy,
      ruleName: warning.ruleName
    });

    this.emit('warning-acknowledged', warning);

    return warning;
  }

  async resolveWarning(warningId, resolvedBy, resolution = '') {
    const warning = this.activeWarnings.get(warningId);
    if (!warning) {
      throw new Error('Warning not found');
    }

    warning.status = 'resolved';
    warning.resolvedBy = resolvedBy;
    warning.resolvedAt = Date.now();
    warning.resolution = resolution;

    this.metrics.resolvedWarnings++;

    logger.info(`Warning resolved`, {
      warningId,
      resolvedBy,
      resolution
    });

    this.emit('warning-resolved', warning);

    return warning;
  }

  async markAsFalsePositive(warningId, markedBy, reason = '') {
    const warning = this.activeWarnings.get(warningId);
    if (!warning) {
      throw new Error('Warning not found');
    }

    warning.status = 'false_positive';
    warning.markedBy = markedBy;
    warning.markedAt = Date.now();
    warning.falsePositiveReason = reason;

    this.metrics.falsePosistives++;

    // Update rule if this is a pattern
    const rule = this.warningRules.get(warning.ruleId);
    if (rule) {
      rule.falsePositiveCount = (rule.falsePositiveCount || 0) + 1;
    }

    logger.info(`Warning marked as false positive`, {
      warningId,
      markedBy,
      reason
    });

    this.emit('warning-false-positive', warning);

    return warning;
  }

  hasSimilarRecentWarning(ruleId, userId, timeWindow) {
    const cutoffTime = Date.now() - timeWindow;
    
    for (const warning of this.activeWarnings.values()) {
      if (warning.ruleId === ruleId && 
          warning.userId === userId && 
          warning.timestamp > cutoffTime) {
        return true;
      }
    }
    
    return false;
  }

  countRecentEvents(userId, eventType, timeWindow) {
    // This would integrate with your event tracking system
    // Simplified implementation for demo
    return Math.floor(Math.random() * 5);
  }

  trackEvent(userId, eventType, event) {
    // Track events for pattern analysis
    // This would integrate with your event tracking system
    logger.debug(`Event tracked: ${eventType}`, { userId, timestamp: event.timestamp });
  }

  trackUserBehavior(event) {
    if (!this.options.trackUserBehavior) return;

    const session = this.userSessions.get(event.userId) || {
      startTime: event.timestamp,
      lastActivity: event.timestamp,
      events: [],
      patterns: {}
    };

    session.lastActivity = event.timestamp;
    session.events.push({
      resource: event.resource,
      action: event.action,
      timestamp: event.timestamp,
      success: event.context.success
    });

    // Keep only recent events
    session.events = session.events.filter(e => 
      event.timestamp - e.timestamp < 3600000 // 1 hour
    );

    this.userSessions.set(event.userId, session);
  }

  startSystemMonitoring() {
    setInterval(() => {
      // Monitor system health and patterns
      this.analyzeSystemPatterns();
      this.checkForAnomalies();
    }, 60000); // Every minute
  }

  startCleanupRoutines() {
    setInterval(() => {
      this.cleanupOldWarnings();
      this.cleanupOldSessions();
    }, 3600000); // Every hour
  }

  cleanupOldWarnings() {
    const now = Date.now();
    let cleaned = 0;

    for (const [warningId, warning] of this.activeWarnings) {
      const retentionPeriod = this.options.warningLevels[warning.level].retentionDays * 24 * 60 * 60 * 1000;
      
      if (warning.status === 'resolved' && now - warning.resolvedAt > retentionPeriod) {
        this.activeWarnings.delete(warningId);
        cleaned++;
      } else if (warning.status === 'false_positive' && now - warning.markedAt > retentionPeriod) {
        this.activeWarnings.delete(warningId);
        cleaned++;
      }
    }

    if (cleaned > 0) {
      logger.debug(`Cleaned up ${cleaned} old warnings`);
    }
  }

  cleanupOldSessions() {
    const cutoffTime = Date.now() - 3600000; // 1 hour
    let cleaned = 0;

    for (const [userId, session] of this.userSessions) {
      if (session.lastActivity < cutoffTime) {
        this.userSessions.delete(userId);
        cleaned++;
      }
    }

    if (cleaned > 0) {
      logger.debug(`Cleaned up ${cleaned} old user sessions`);
    }
  }

  startAlertProcessing() {
    setInterval(async () => {
      if (this.alertQueue.length === 0) return;

      const alert = this.alertQueue.shift();
      try {
        await this.deliverAlert(alert);
        this.metrics.alertsSent++;
      } catch (error) {
        logger.error('Failed to deliver alert:', error);
        
        // Retry logic
        alert.attempts++;
        if (alert.attempts < 3) {
          this.alertQueue.push(alert);
        }
      }
    }, 5000); // Every 5 seconds
  }

  async deliverAlert(alert) {
    for (const channel of alert.channels) {
      switch (channel) {
        case 'email':
          await this.sendEmailAlert(alert);
          break;
        case 'sms':
          await this.sendSmsAlert(alert);
          break;
        case 'slack':
          await this.sendSlackAlert(alert);
          break;
        case 'push':
          await this.sendPushNotification(alert);
          break;
      }
    }

    alert.delivered = true;
    alert.deliveredAt = Date.now();
  }

  async sendEmailAlert(alert) {
    // Email implementation would go here
    logger.debug(`Email alert sent: ${alert.title}`);
    this.emit('email-sent', alert);
  }

  async sendSmsAlert(alert) {
    // SMS implementation would go here
    logger.debug(`SMS alert sent: ${alert.title}`);
    this.emit('sms-sent', alert);
  }

  async sendSlackAlert(alert) {
    // Slack implementation would go here
    logger.debug(`Slack alert sent: ${alert.title}`);
    this.emit('slack-sent', alert);
  }

  async sendPushNotification(alert) {
    // Push notification implementation would go here
    logger.debug(`Push notification sent: ${alert.title}`);
    this.emit('push-sent', alert);
  }

  analyzeSystemPatterns() {
    // Analyze patterns for anomaly detection
    const patterns = {
      failedAuthenticationSpikes: this.detectAuthenticationSpikes(),
      unusualResourceAccess: this.detectUnusualResourceAccess(),
      timeBasedAnomalies: this.detectTimeBasedAnomalies()
    };

    if (Object.values(patterns).some(Boolean)) {
      this.emit('system-pattern-detected', patterns);
    }
  }

  checkForAnomalies() {
    // Check for system-wide anomalies
    const currentHour = new Date().getHours();
    const warningsThisHour = Array.from(this.activeWarnings.values())
      .filter(w => new Date(w.timestamp).getHours() === currentHour).length;

    if (warningsThisHour > this.options.maxAlertsPerHour) {
      logger.warn(`High number of warnings this hour: ${warningsThisHour}`);
      this.emit('warning-spike', { count: warningsThisHour, hour: currentHour });
    }
  }

  detectAuthenticationSpikes() {
    const recentFailures = Array.from(this.failedAttempts.values())
      .flat()
      .filter(attempt => Date.now() - attempt.timestamp < 3600000);

    return recentFailures.length > this.options.maxFailedAttempts * 5;
  }

  detectUnusualResourceAccess() {
    // Simplified detection logic
    return false;
  }

  detectTimeBasedAnomalies() {
    const currentHour = new Date().getHours();
    return currentHour < 6 || currentHour > 22;
  }

  // Public API methods
  getActiveWarnings(userId = null, level = null) {
    let warnings = Array.from(this.activeWarnings.values());

    if (userId) {
      warnings = warnings.filter(w => w.userId === userId);
    }

    if (level) {
      warnings = warnings.filter(w => w.level === level);
    }

    return warnings.sort((a, b) => b.timestamp - a.timestamp);
  }

  getWarningDetails(warningId) {
    return this.activeWarnings.get(warningId);
  }

  getWarningStats() {
    const stats = {
      total: this.activeWarnings.size,
      byLevel: { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 },
      byStatus: { active: 0, acknowledged: 0, resolved: 0, false_positive: 0 }
    };

    for (const warning of this.activeWarnings.values()) {
      stats.byLevel[warning.level]++;
      stats.byStatus[warning.status]++;
    }

    return stats;
  }

  getAdminNotifications() {
    return this.adminNotifications.slice(-50); // Last 50 notifications
  }

  getMetrics() {
    return {
      ...this.metrics,
      activeWarnings: this.activeWarnings.size,
      pendingAlerts: this.alertQueue.length,
      trackedUsers: this.userSessions.size,
      escalatedWarnings: this.escalatedWarnings.size
    };
  }

  async cleanup() {
    this.activeWarnings.clear();
    this.userWarnings.clear();
    this.warningHistory.clear();
    this.alertQueue = [];
    this.suppressedAlerts.clear();
    this.userSessions.clear();
    this.accessPatterns.clear();
    this.failedAttempts.clear();
    this.suspiciousActivities.clear();
    this.systemEvents = [];
    this.escalatedWarnings.clear();
    this.adminNotifications = [];

    this.removeAllListeners();
    logger.info('Permission Warning System cleaned up');
  }
}

module.exports = PermissionWarningSystem;