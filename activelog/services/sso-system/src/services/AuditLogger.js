const winston = require('winston');
const { EventEmitter } = require('events');

class AuditLogger extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      logLevel: options.logLevel || 'info',
      logFormat: options.logFormat || 'json',
      logDir: options.logDir || './logs',
      maxFileSize: options.maxFileSize || 100 * 1024 * 1024, // 100MB
      maxFiles: options.maxFiles || 30,
      enableConsole: options.enableConsole !== false,
      enableFile: options.enableFile !== false,
      enableDatabase: options.enableDatabase || false,
      enableRealTime: options.enableRealTime !== false,
      retentionDays: options.retentionDays || 365,
      compressionEnabled: options.compressionEnabled !== false,
      ...options
    };
    
    this.auditLogs = new Map();
    this.logBuffer = [];
    this.realTimeSubscribers = new Map();
    this.alertRules = new Map();
    this.logStats = {
      totalLogs: 0,
      logsByLevel: new Map(),
      logsByCategory: new Map(),
      alertsTriggered: 0
    };
    
    this.setupWinstonLogger();
    this.setupBufferFlusher();
    this.setupCleanup();
  }

  setupWinstonLogger() {
    const transports = [];
    
    // Console transport
    if (this.options.enableConsole) {
      transports.push(new winston.transports.Console({
        level: this.options.logLevel,
        format: winston.format.combine(
          winston.format.timestamp(),
          winston.format.colorize(),
          winston.format.simple()
        )
      }));
    }
    
    // File transports
    if (this.options.enableFile) {
      // General audit log
      transports.push(new winston.transports.File({
        filename: `${this.options.logDir}/audit.log`,
        level: this.options.logLevel,
        maxsize: this.options.maxFileSize,
        maxFiles: this.options.maxFiles,
        format: winston.format.combine(
          winston.format.timestamp(),
          winston.format.json()
        )
      }));
      
      // Security-specific logs
      transports.push(new winston.transports.File({
        filename: `${this.options.logDir}/security.log`,
        level: 'warn',
        maxsize: this.options.maxFileSize,
        maxFiles: this.options.maxFiles,
        format: winston.format.combine(
          winston.format.timestamp(),
          winston.format.json()
        ),
        filter: (info) => info.category === 'security'
      }));
      
      // Error logs
      transports.push(new winston.transports.File({
        filename: `${this.options.logDir}/errors.log`,
        level: 'error',
        maxsize: this.options.maxFileSize,
        maxFiles: this.options.maxFiles,
        format: winston.format.combine(
          winston.format.timestamp(),
          winston.format.json()
        )
      }));
    }
    
    this.logger = winston.createLogger({
      level: this.options.logLevel,
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
      ),
      transports
    });
  }

  // Core Logging Methods
  async log(level, message, data = {}) {
    const logEntry = {
      id: this.generateLogId(),
      timestamp: new Date(),
      level,
      message,
      
      // Event details
      eventType: data.eventType || 'general',
      category: data.category || 'application',
      subcategory: data.subcategory,
      
      // User context
      userId: data.userId,
      username: data.username,
      email: data.email,
      sessionId: data.sessionId,
      
      // Request context
      ip: data.ip,
      userAgent: data.userAgent,
      requestId: data.requestId,
      method: data.method,
      url: data.url,
      
      // Authentication context
      authMethod: data.authMethod,
      tokenType: data.tokenType,
      clientId: data.clientId,
      scopes: data.scopes,
      
      // Device context
      deviceId: data.deviceId,
      deviceFingerprint: data.deviceFingerprint,
      location: data.location,
      
      // Security context
      riskScore: data.riskScore,
      threatLevel: data.threatLevel,
      securityFlags: data.securityFlags || [],
      
      // Operation details
      resource: data.resource,
      action: data.action,
      result: data.result,
      error: data.error,
      
      // Performance metrics
      duration: data.duration,
      responseSize: data.responseSize,
      
      // Custom fields
      metadata: data.metadata || {},
      tags: data.tags || [],
      
      // Compliance fields
      complianceCategory: data.complianceCategory,
      dataClassification: data.dataClassification,
      retentionPolicy: data.retentionPolicy
    };
    
    // Store in memory for querying
    this.auditLogs.set(logEntry.id, logEntry);
    
    // Add to buffer for batch processing
    this.logBuffer.push(logEntry);
    
    // Update statistics
    this.updateLogStats(logEntry);
    
    // Write to Winston logger
    this.logger.log(level, message, logEntry);
    
    // Check alert rules
    await this.checkAlertRules(logEntry);
    
    // Send to real-time subscribers
    if (this.options.enableRealTime) {
      this.broadcastRealTime(logEntry);
    }
    
    this.emit('logCreated', logEntry);
    
    return logEntry.id;
  }

  // Convenience methods for different log levels
  async info(message, data = {}) {
    return this.log('info', message, data);
  }

  async warn(message, data = {}) {
    return this.log('warn', message, data);
  }

  async error(message, data = {}) {
    return this.log('error', message, data);
  }

  async debug(message, data = {}) {
    return this.log('debug', message, data);
  }

  // Authentication Events
  async logLogin(userId, data = {}) {
    return this.log('info', `User login: ${userId}`, {
      ...data,
      eventType: 'login',
      category: 'authentication',
      userId,
      action: 'login',
      result: data.success ? 'success' : 'failure'
    });
  }

  async logLogout(userId, data = {}) {
    return this.log('info', `User logout: ${userId}`, {
      ...data,
      eventType: 'logout',
      category: 'authentication',
      userId,
      action: 'logout',
      result: 'success'
    });
  }

  async logFailedLogin(identifier, data = {}) {
    return this.log('warn', `Failed login attempt: ${identifier}`, {
      ...data,
      eventType: 'login_failed',
      category: 'security',
      subcategory: 'authentication',
      username: identifier,
      action: 'login',
      result: 'failure',
      threatLevel: data.threatLevel || 'medium'
    });
  }

  async logPasswordChange(userId, data = {}) {
    return this.log('info', `Password changed: ${userId}`, {
      ...data,
      eventType: 'password_change',
      category: 'security',
      subcategory: 'authentication',
      userId,
      action: 'password_change',
      result: 'success'
    });
  }

  async logMFAEvent(userId, mfaMethod, success, data = {}) {
    return this.log(success ? 'info' : 'warn', 
      `MFA ${mfaMethod} ${success ? 'success' : 'failure'}: ${userId}`, {
      ...data,
      eventType: 'mfa',
      category: 'authentication',
      subcategory: 'mfa',
      userId,
      action: `mfa_${mfaMethod}`,
      result: success ? 'success' : 'failure',
      authMethod: mfaMethod
    });
  }

  // Authorization Events
  async logPermissionCheck(userId, resource, action, allowed, data = {}) {
    return this.log('debug', 
      `Permission check: ${userId} ${action} on ${resource} - ${allowed ? 'allowed' : 'denied'}`, {
      ...data,
      eventType: 'permission_check',
      category: 'authorization',
      userId,
      resource,
      action,
      result: allowed ? 'allowed' : 'denied'
    });
  }

  async logRoleAssignment(targetUserId, roles, assignedBy, data = {}) {
    return this.log('info', `Roles assigned to ${targetUserId}: ${roles.join(', ')}`, {
      ...data,
      eventType: 'role_assignment',
      category: 'authorization',
      subcategory: 'role_management',
      userId: assignedBy,
      targetUserId,
      action: 'assign_roles',
      result: 'success',
      metadata: { roles }
    });
  }

  async logUnauthorizedAccess(userId, resource, action, data = {}) {
    return this.log('warn', 
      `Unauthorized access attempt: ${userId} tried to ${action} ${resource}`, {
      ...data,
      eventType: 'unauthorized_access',
      category: 'security',
      subcategory: 'authorization',
      userId,
      resource,
      action,
      result: 'denied',
      threatLevel: 'medium'
    });
  }

  // Token Events
  async logTokenIssued(userId, tokenType, clientId, data = {}) {
    return this.log('info', `Token issued: ${tokenType} for ${userId}`, {
      ...data,
      eventType: 'token_issued',
      category: 'authentication',
      subcategory: 'token_management',
      userId,
      tokenType,
      clientId,
      action: 'issue_token',
      result: 'success'
    });
  }

  async logTokenRevoked(userId, tokenType, reason, data = {}) {
    return this.log('info', `Token revoked: ${tokenType} for ${userId} - ${reason}`, {
      ...data,
      eventType: 'token_revoked',
      category: 'authentication',
      subcategory: 'token_management',
      userId,
      tokenType,
      action: 'revoke_token',
      result: 'success',
      metadata: { reason }
    });
  }

  async logTokenExchange(userId, fromTokenType, toTokenType, data = {}) {
    return this.log('info', 
      `Token exchange: ${userId} ${fromTokenType} -> ${toTokenType}`, {
      ...data,
      eventType: 'token_exchange',
      category: 'authentication',
      subcategory: 'token_management',
      userId,
      action: 'exchange_token',
      result: 'success',
      metadata: { fromTokenType, toTokenType }
    });
  }

  // API Key Events
  async logAPIKeyCreated(userId, keyName, data = {}) {
    return this.log('info', `API key created: ${keyName} by ${userId}`, {
      ...data,
      eventType: 'api_key_created',
      category: 'authentication',
      subcategory: 'api_key_management',
      userId,
      action: 'create_api_key',
      result: 'success',
      resource: keyName
    });
  }

  async logAPIKeyUsed(keyId, endpoint, success, data = {}) {
    return this.log('debug', `API key used: ${keyId} for ${endpoint}`, {
      ...data,
      eventType: 'api_key_used',
      category: 'authentication',
      subcategory: 'api_key_usage',
      action: 'use_api_key',
      result: success ? 'success' : 'failure',
      resource: endpoint,
      metadata: { keyId }
    });
  }

  async logAPIKeyRevoked(userId, keyId, reason, data = {}) {
    return this.log('warn', `API key revoked: ${keyId} by ${userId} - ${reason}`, {
      ...data,
      eventType: 'api_key_revoked',
      category: 'security',
      subcategory: 'api_key_management',
      userId,
      action: 'revoke_api_key',
      result: 'success',
      metadata: { keyId, reason }
    });
  }

  // Device Events
  async logDeviceRegistered(userId, deviceId, deviceInfo, data = {}) {
    return this.log('info', `Device registered: ${deviceId} for ${userId}`, {
      ...data,
      eventType: 'device_registered',
      category: 'device_management',
      userId,
      deviceId,
      action: 'register_device',
      result: 'success',
      metadata: deviceInfo
    });
  }

  async logSuspiciousDevice(userId, deviceId, riskScore, flags, data = {}) {
    return this.log('warn', 
      `Suspicious device detected: ${deviceId} for ${userId} (risk: ${riskScore})`, {
      ...data,
      eventType: 'suspicious_device',
      category: 'security',
      subcategory: 'device_security',
      userId,
      deviceId,
      riskScore,
      securityFlags: flags,
      threatLevel: 'medium'
    });
  }

  // Session Events
  async logSessionStarted(userId, sessionId, data = {}) {
    return this.log('debug', `Session started: ${sessionId} for ${userId}`, {
      ...data,
      eventType: 'session_started',
      category: 'session_management',
      userId,
      sessionId,
      action: 'start_session',
      result: 'success'
    });
  }

  async logSessionEnded(userId, sessionId, duration, data = {}) {
    return this.log('debug', `Session ended: ${sessionId} for ${userId}`, {
      ...data,
      eventType: 'session_ended',
      category: 'session_management',
      userId,
      sessionId,
      action: 'end_session',
      result: 'success',
      duration,
      metadata: { duration }
    });
  }

  // Enterprise SSO Events
  async logSAMLLogin(userId, providerId, success, data = {}) {
    return this.log(success ? 'info' : 'warn', 
      `SAML login ${success ? 'success' : 'failure'}: ${userId} via ${providerId}`, {
      ...data,
      eventType: 'saml_login',
      category: 'authentication',
      subcategory: 'enterprise_sso',
      userId,
      action: 'saml_login',
      result: success ? 'success' : 'failure',
      authMethod: 'saml',
      metadata: { providerId }
    });
  }

  async logLDAPAuth(username, success, data = {}) {
    return this.log(success ? 'info' : 'warn', 
      `LDAP authentication ${success ? 'success' : 'failure'}: ${username}`, {
      ...data,
      eventType: 'ldap_auth',
      category: 'authentication',
      subcategory: 'enterprise_sso',
      username,
      action: 'ldap_auth',
      result: success ? 'success' : 'failure',
      authMethod: 'ldap'
    });
  }

  // Security Events
  async logSecurityThreat(threatType, severity, details, data = {}) {
    return this.log('error', `Security threat detected: ${threatType}`, {
      ...data,
      eventType: 'security_threat',
      category: 'security',
      subcategory: 'threat_detection',
      action: 'threat_detected',
      threatLevel: severity,
      metadata: details
    });
  }

  async logRateLimitExceeded(identifier, endpoint, data = {}) {
    return this.log('warn', `Rate limit exceeded: ${identifier} on ${endpoint}`, {
      ...data,
      eventType: 'rate_limit_exceeded',
      category: 'security',
      subcategory: 'rate_limiting',
      action: 'rate_limit_check',
      result: 'exceeded',
      resource: endpoint,
      metadata: { identifier }
    });
  }

  // Data Events
  async logDataAccess(userId, resource, action, data = {}) {
    return this.log('info', `Data access: ${userId} ${action} ${resource}`, {
      ...data,
      eventType: 'data_access',
      category: 'data_management',
      userId,
      resource,
      action,
      result: 'success'
    });
  }

  async logDataModification(userId, resource, changes, data = {}) {
    return this.log('info', `Data modified: ${resource} by ${userId}`, {
      ...data,
      eventType: 'data_modification',
      category: 'data_management',
      userId,
      resource,
      action: 'modify',
      result: 'success',
      metadata: { changes }
    });
  }

  // Configuration Events
  async logConfigChange(userId, configType, changes, data = {}) {
    return this.log('warn', `Configuration changed: ${configType} by ${userId}`, {
      ...data,
      eventType: 'config_change',
      category: 'system_management',
      subcategory: 'configuration',
      userId,
      action: 'modify_config',
      result: 'success',
      resource: configType,
      metadata: { changes }
    });
  }

  // Alert Rules Management
  createAlertRule(ruleData) {
    const rule = {
      id: ruleData.id || this.generateRuleId(),
      name: ruleData.name,
      description: ruleData.description,
      
      // Rule conditions
      conditions: ruleData.conditions || [],
      
      // Alert settings
      severity: ruleData.severity || 'medium',
      threshold: ruleData.threshold || 1,
      timeWindow: ruleData.timeWindow || 300000, // 5 minutes
      
      // Notification settings
      notifications: ruleData.notifications || [],
      
      // Rule state
      enabled: ruleData.enabled !== false,
      triggeredCount: 0,
      lastTriggered: null,
      
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    this.alertRules.set(rule.id, rule);
    this.emit('alertRuleCreated', rule);
    return rule;
  }

  updateAlertRule(ruleId, updates) {
    const rule = this.alertRules.get(ruleId);
    if (!rule) {
      throw new Error(`Alert rule ${ruleId} not found`);
    }
    
    const updatedRule = {
      ...rule,
      ...updates,
      updatedAt: new Date()
    };
    
    this.alertRules.set(ruleId, updatedRule);
    this.emit('alertRuleUpdated', updatedRule);
    return updatedRule;
  }

  deleteAlertRule(ruleId) {
    const rule = this.alertRules.get(ruleId);
    if (!rule) {
      throw new Error(`Alert rule ${ruleId} not found`);
    }
    
    this.alertRules.delete(ruleId);
    this.emit('alertRuleDeleted', rule);
    return true;
  }

  async checkAlertRules(logEntry) {
    for (const [ruleId, rule] of this.alertRules) {
      if (!rule.enabled) {
        continue;
      }
      
      if (await this.ruleMatches(rule, logEntry)) {
        await this.triggerAlert(rule, logEntry);
      }
    }
  }

  async ruleMatches(rule, logEntry) {
    for (const condition of rule.conditions) {
      if (!this.evaluateCondition(condition, logEntry)) {
        return false;
      }
    }
    
    // Check threshold if rule has time window
    if (rule.timeWindow && rule.threshold > 1) {
      const matchingLogs = this.getRecentMatchingLogs(rule, rule.timeWindow);
      return matchingLogs.length >= rule.threshold;
    }
    
    return true;
  }

  evaluateCondition(condition, logEntry) {
    switch (condition.type) {
      case 'equals':
        return logEntry[condition.field] === condition.value;
        
      case 'contains':
        const fieldValue = logEntry[condition.field];
        return fieldValue && fieldValue.includes && fieldValue.includes(condition.value);
        
      case 'greater_than':
        return logEntry[condition.field] > condition.value;
        
      case 'less_than':
        return logEntry[condition.field] < condition.value;
        
      case 'in':
        return condition.values.includes(logEntry[condition.field]);
        
      case 'regex':
        const regex = new RegExp(condition.pattern);
        return regex.test(logEntry[condition.field]);
        
      default:
        return false;
    }
  }

  getRecentMatchingLogs(rule, timeWindow) {
    const cutoff = new Date(Date.now() - timeWindow);
    const matchingLogs = [];
    
    for (const logEntry of this.auditLogs.values()) {
      if (logEntry.timestamp >= cutoff) {
        let matches = true;
        for (const condition of rule.conditions) {
          if (!this.evaluateCondition(condition, logEntry)) {
            matches = false;
            break;
          }
        }
        if (matches) {
          matchingLogs.push(logEntry);
        }
      }
    }
    
    return matchingLogs;
  }

  async triggerAlert(rule, logEntry) {
    const alert = {
      id: this.generateAlertId(),
      ruleId: rule.id,
      ruleName: rule.name,
      severity: rule.severity,
      message: `Alert triggered: ${rule.name}`,
      triggeringLog: logEntry,
      timestamp: new Date()
    };
    
    // Update rule state
    rule.triggeredCount++;
    rule.lastTriggered = new Date();
    
    // Update statistics
    this.logStats.alertsTriggered++;
    
    // Send notifications
    for (const notification of rule.notifications) {
      await this.sendNotification(notification, alert);
    }
    
    this.emit('alertTriggered', alert);
    
    return alert;
  }

  async sendNotification(notification, alert) {
    // This would integrate with notification services
    console.log(`ALERT: ${alert.severity} - ${alert.message}`);
    
    switch (notification.type) {
      case 'email':
        await this.sendEmailNotification(notification.recipients, alert);
        break;
        
      case 'webhook':
        await this.sendWebhookNotification(notification.url, alert);
        break;
        
      case 'slack':
        await this.sendSlackNotification(notification.channel, alert);
        break;
    }
  }

  // Real-time Subscriptions
  subscribeRealTime(subscriberId, filters = {}) {
    this.realTimeSubscribers.set(subscriberId, {
      id: subscriberId,
      filters,
      createdAt: new Date()
    });
    
    return subscriberId;
  }

  unsubscribeRealTime(subscriberId) {
    return this.realTimeSubscribers.delete(subscriberId);
  }

  broadcastRealTime(logEntry) {
    for (const [subscriberId, subscriber] of this.realTimeSubscribers) {
      if (this.logMatchesFilters(logEntry, subscriber.filters)) {
        this.emit('realTimeLog', subscriberId, logEntry);
      }
    }
  }

  logMatchesFilters(logEntry, filters) {
    if (filters.level && logEntry.level !== filters.level) {
      return false;
    }
    
    if (filters.category && logEntry.category !== filters.category) {
      return false;
    }
    
    if (filters.userId && logEntry.userId !== filters.userId) {
      return false;
    }
    
    if (filters.eventType && logEntry.eventType !== filters.eventType) {
      return false;
    }
    
    return true;
  }

  // Query Methods
  queryLogs(filters = {}) {
    let logs = Array.from(this.auditLogs.values());
    
    // Apply filters
    if (filters.startDate) {
      logs = logs.filter(log => log.timestamp >= new Date(filters.startDate));
    }
    
    if (filters.endDate) {
      logs = logs.filter(log => log.timestamp <= new Date(filters.endDate));
    }
    
    if (filters.level) {
      logs = logs.filter(log => log.level === filters.level);
    }
    
    if (filters.category) {
      logs = logs.filter(log => log.category === filters.category);
    }
    
    if (filters.userId) {
      logs = logs.filter(log => log.userId === filters.userId);
    }
    
    if (filters.eventType) {
      logs = logs.filter(log => log.eventType === filters.eventType);
    }
    
    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      logs = logs.filter(log => 
        log.message.toLowerCase().includes(searchTerm) ||
        JSON.stringify(log.metadata).toLowerCase().includes(searchTerm)
      );
    }
    
    // Sort by timestamp (newest first)
    logs.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
    
    // Apply pagination
    if (filters.limit) {
      logs = logs.slice(0, filters.limit);
    }
    
    return logs;
  }

  getLogById(logId) {
    return this.auditLogs.get(logId);
  }

  getLogStats(timeRange = 24 * 60 * 60 * 1000) { // 24 hours
    const cutoff = new Date(Date.now() - timeRange);
    const recentLogs = Array.from(this.auditLogs.values())
      .filter(log => log.timestamp >= cutoff);
    
    const stats = {
      totalLogs: recentLogs.length,
      logsByLevel: {},
      logsByCategory: {},
      logsByEventType: {},
      logsByHour: new Array(24).fill(0),
      topUsers: {},
      topIPs: {},
      alertsTriggered: 0
    };
    
    // Calculate statistics
    recentLogs.forEach(log => {
      // By level
      stats.logsByLevel[log.level] = (stats.logsByLevel[log.level] || 0) + 1;
      
      // By category
      stats.logsByCategory[log.category] = (stats.logsByCategory[log.category] || 0) + 1;
      
      // By event type
      stats.logsByEventType[log.eventType] = (stats.logsByEventType[log.eventType] || 0) + 1;
      
      // By hour
      const hour = log.timestamp.getHours();
      stats.logsByHour[hour]++;
      
      // Top users
      if (log.userId) {
        stats.topUsers[log.userId] = (stats.topUsers[log.userId] || 0) + 1;
      }
      
      // Top IPs
      if (log.ip) {
        stats.topIPs[log.ip] = (stats.topIPs[log.ip] || 0) + 1;
      }
    });
    
    return stats;
  }

  // Utility Methods
  updateLogStats(logEntry) {
    this.logStats.totalLogs++;
    
    // Update level counts
    const currentCount = this.logStats.logsByLevel.get(logEntry.level) || 0;
    this.logStats.logsByLevel.set(logEntry.level, currentCount + 1);
    
    // Update category counts
    const categoryCount = this.logStats.logsByCategory.get(logEntry.category) || 0;
    this.logStats.logsByCategory.set(logEntry.category, categoryCount + 1);
  }

  setupBufferFlusher() {
    // Flush buffer every 5 seconds or when it reaches 100 entries
    setInterval(() => {
      if (this.logBuffer.length > 0) {
        this.flushBuffer();
      }
    }, 5000);
  }

  flushBuffer() {
    if (this.options.enableDatabase) {
      // In a real implementation, this would batch write to database
      this.emit('bufferFlushed', this.logBuffer.length);
    }
    
    this.logBuffer = [];
  }

  setupCleanup() {
    // Clean up old logs daily
    setInterval(() => {
      this.cleanupOldLogs();
    }, 24 * 60 * 60 * 1000);
  }

  cleanupOldLogs() {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - this.options.retentionDays);
    
    let deletedCount = 0;
    
    for (const [logId, log] of this.auditLogs) {
      if (log.timestamp < cutoff) {
        this.auditLogs.delete(logId);
        deletedCount++;
      }
    }
    
    if (deletedCount > 0) {
      this.emit('logsCleanedUp', deletedCount);
    }
  }

  generateLogId() {
    return `log_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  generateRuleId() {
    return `rule_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  generateAlertId() {
    return `alert_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Integration Methods (to be implemented with actual services)
  async sendEmailNotification(recipients, alert) {
    console.log(`Email notification sent to ${recipients.join(', ')}: ${alert.message}`);
  }

  async sendWebhookNotification(url, alert) {
    console.log(`Webhook notification sent to ${url}: ${alert.message}`);
  }

  async sendSlackNotification(channel, alert) {
    console.log(`Slack notification sent to ${channel}: ${alert.message}`);
  }

  // Statistics and Monitoring
  getStats() {
    return {
      totalLogs: this.auditLogs.size,
      logsByLevel: Object.fromEntries(this.logStats.logsByLevel),
      logsByCategory: Object.fromEntries(this.logStats.logsByCategory),
      alertRules: this.alertRules.size,
      alertsTriggered: this.logStats.alertsTriggered,
      realTimeSubscribers: this.realTimeSubscribers.size,
      bufferSize: this.logBuffer.length
    };
  }

  getAlertRules() {
    return Array.from(this.alertRules.values());
  }

  reset() {
    this.auditLogs.clear();
    this.logBuffer = [];
    this.realTimeSubscribers.clear();
    this.alertRules.clear();
    this.logStats = {
      totalLogs: 0,
      logsByLevel: new Map(),
      logsByCategory: new Map(),
      alertsTriggered: 0
    };
  }
}

module.exports = AuditLogger;