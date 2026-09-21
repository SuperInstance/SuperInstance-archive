const EventEmitter = require('events');
const logger = require('../core/logger');
const crypto = require('crypto');
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs').promises;

class AuditTrail extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      // Storage settings
      storageDir: options.storageDir || './data/audit-trail',
      maxFileSize: options.maxFileSize || 50 * 1024 * 1024, // 50MB
      retentionDays: options.retentionDays || 365, // 1 year
      compressionEnabled: options.compressionEnabled !== false,
      
      // Audit levels
      auditLevels: options.auditLevels || {
        MINIMAL: ['authentication', 'permission_changes'],
        STANDARD: ['authentication', 'permission_changes', 'data_access', 'configuration_changes'],
        COMPREHENSIVE: ['authentication', 'permission_changes', 'data_access', 'configuration_changes', 'user_actions', 'system_events'],
        FORENSIC: ['*'] // Everything
      },
      
      currentLevel: options.currentLevel || 'STANDARD',
      
      // Event categories to audit
      auditCategories: options.auditCategories || [
        'authentication',
        'authorization',
        'data_access',
        'data_modification',
        'configuration_changes',
        'user_management',
        'system_events',
        'security_events',
        'admin_actions',
        'api_calls'
      ],
      
      // Security features
      tamperProtection: options.tamperProtection !== false,
      digitalSignatures: options.digitalSignatures !== false,
      encryptAuditLogs: options.encryptAuditLogs !== false,
      
      // Real-time monitoring
      realTimeAlerts: options.realTimeAlerts !== false,
      suspiciousActivityThreshold: options.suspiciousActivityThreshold || 10,
      
      // Integration
      syslogIntegration: options.syslogIntegration || false,
      siemIntegration: options.siemIntegration || false,
      webhookUrl: options.webhookUrl,
      
      // Performance
      batchSize: options.batchSize || 100,
      flushInterval: options.flushInterval || 5000, // 5 seconds
      indexingEnabled: options.indexingEnabled !== false,
      
      ...options
    };

    // Audit trail state
    this.auditEntries = [];
    this.entryBuffer = [];
    this.currentLogFile = null;
    this.logFileRotationCount = 0;
    
    // Indexing for fast searches
    this.userIndex = new Map(); // userId -> entry IDs
    this.resourceIndex = new Map(); // resource -> entry IDs
    this.timestampIndex = new Map(); // date -> entry IDs
    this.eventTypeIndex = new Map(); // event type -> entry IDs
    
    // Security
    this.encryptionKey = null;
    this.signatureKey = null;
    this.integrityHashes = new Map();
    
    // Real-time monitoring
    this.activityTracking = new Map(); // userId -> recent activities
    this.suspiciousPatterns = new Set();
    
    // Metrics
    this.metrics = {
      totalEntries: 0,
      entriesPerCategory: new Map(),
      filesCreated: 0,
      queriesPerformed: 0,
      integrityChecks: 0,
      tamperAttempts: 0
    };
  }

  async initialize() {
    logger.info('Initializing Audit Trail system...');
    
    try {
      // Create storage directory
      await fs.mkdir(this.options.storageDir, { recursive: true });
      
      // Initialize security keys
      if (this.options.tamperProtection || this.options.digitalSignatures) {
        await this.initializeSecurity();
      }
      
      // Start log file rotation
      await this.initializeLogFile();
      
      // Start periodic flushing
      this.startPeriodicFlush();
      
      // Start integrity monitoring
      if (this.options.tamperProtection) {
        this.startIntegrityMonitoring();
      }
      
      // Load existing indexes
      await this.loadIndexes();
      
      logger.info('Audit Trail system initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Audit Trail system:', error);
      throw error;
    }
  }

  async initializeSecurity() {
    // Generate encryption key if needed
    if (this.options.encryptAuditLogs && !this.encryptionKey) {
      this.encryptionKey = crypto.randomBytes(32);
    }

    // Generate signature key for tamper protection
    if (this.options.digitalSignatures && !this.signatureKey) {
      this.signatureKey = crypto.randomBytes(32);
    }
  }

  async auditEvent(eventData) {
    try {
      // Check if this event type should be audited
      if (!this.shouldAuditEvent(eventData.category, eventData.eventType)) {
        return null;
      }

      const auditEntry = this.createAuditEntry(eventData);
      
      // Add to buffer
      this.entryBuffer.push(auditEntry);
      
      // Update indexes
      if (this.options.indexingEnabled) {
        this.updateIndexes(auditEntry);
      }
      
      // Track for real-time monitoring
      if (this.options.realTimeAlerts) {
        await this.trackUserActivity(auditEntry);
      }
      
      // Flush if buffer is full
      if (this.entryBuffer.length >= this.options.batchSize) {
        await this.flushBuffer();
      }

      this.metrics.totalEntries++;
      this.updateCategoryMetrics(eventData.category);

      this.emit('audit-entry-created', auditEntry);
      
      return auditEntry;
    } catch (error) {
      logger.error('Failed to create audit entry:', error);
      throw error;
    }
  }

  createAuditEntry(eventData) {
    const entryId = uuidv4();
    const timestamp = Date.now();
    
    const baseEntry = {
      id: entryId,
      timestamp,
      dateTime: new Date(timestamp).toISOString(),
      
      // Event classification
      category: eventData.category,
      eventType: eventData.eventType,
      severity: eventData.severity || 'info', // info, warning, error, critical
      
      // Actor information
      userId: eventData.userId,
      userEmail: eventData.userEmail,
      userRole: eventData.userRole,
      sessionId: eventData.sessionId,
      
      // Target information
      targetResource: eventData.targetResource,
      targetId: eventData.targetId,
      targetType: eventData.targetType,
      
      // Action details
      action: eventData.action,
      description: eventData.description,
      result: eventData.result, // success, failure, partial
      
      // Technical details
      ipAddress: eventData.ipAddress,
      userAgent: eventData.userAgent,
      requestId: eventData.requestId,
      
      // Context
      context: eventData.context || {},
      metadata: eventData.metadata || {},
      
      // Security
      checksum: null,
      signature: null,
      
      // Before/after state for data changes
      beforeState: eventData.beforeState,
      afterState: eventData.afterState,
      
      // Compliance fields
      complianceFlags: eventData.complianceFlags || [],
      retentionCategory: this.getRetentionCategory(eventData),
      
      // System information
      systemVersion: eventData.systemVersion,
      component: eventData.component || 'remote-control'
    };

    // Add digital signature for tamper protection
    if (this.options.digitalSignatures) {
      baseEntry.signature = this.createSignature(baseEntry);
    }

    // Calculate checksum for integrity
    if (this.options.tamperProtection) {
      baseEntry.checksum = this.calculateChecksum(baseEntry);
    }

    return baseEntry;
  }

  shouldAuditEvent(category, eventType) {
    const currentLevelEvents = this.options.auditLevels[this.options.currentLevel];
    
    // Check if we audit everything
    if (currentLevelEvents.includes('*')) {
      return true;
    }
    
    // Check if category is included
    if (currentLevelEvents.includes(category)) {
      return true;
    }
    
    // Check specific event types
    return currentLevelEvents.includes(eventType);
  }

  getRetentionCategory(eventData) {
    // Determine retention requirements based on event type
    const criticalEvents = ['authentication', 'permission_changes', 'data_deletion'];
    const complianceEvents = ['data_access', 'user_management'];
    
    if (criticalEvents.includes(eventData.category)) {
      return 'critical'; // Longer retention
    } else if (complianceEvents.includes(eventData.category)) {
      return 'compliance'; // Standard retention
    }
    
    return 'standard';
  }

  createSignature(entry) {
    if (!this.signatureKey) return null;
    
    const data = JSON.stringify({
      id: entry.id,
      timestamp: entry.timestamp,
      userId: entry.userId,
      action: entry.action,
      targetResource: entry.targetResource
    });
    
    return crypto.createHmac('sha256', this.signatureKey).update(data).digest('hex');
  }

  calculateChecksum(entry) {
    const data = JSON.stringify(entry, Object.keys(entry).sort());
    return crypto.createHash('sha256').update(data).digest('hex');
  }

  updateIndexes(entry) {
    // User index
    if (entry.userId) {
      const userEntries = this.userIndex.get(entry.userId) || [];
      userEntries.push(entry.id);
      this.userIndex.set(entry.userId, userEntries);
    }

    // Resource index
    if (entry.targetResource) {
      const resourceEntries = this.resourceIndex.get(entry.targetResource) || [];
      resourceEntries.push(entry.id);
      this.resourceIndex.set(entry.targetResource, resourceEntries);
    }

    // Timestamp index (by day)
    const dateKey = new Date(entry.timestamp).toDateString();
    const dateEntries = this.timestampIndex.get(dateKey) || [];
    dateEntries.push(entry.id);
    this.timestampIndex.set(dateKey, dateEntries);

    // Event type index
    const eventKey = `${entry.category}:${entry.eventType}`;
    const eventEntries = this.eventTypeIndex.get(eventKey) || [];
    eventEntries.push(entry.id);
    this.eventTypeIndex.set(eventKey, eventEntries);
  }

  async trackUserActivity(entry) {
    if (!entry.userId) return;

    const userActivities = this.activityTracking.get(entry.userId) || [];
    userActivities.push({
      timestamp: entry.timestamp,
      action: entry.action,
      resource: entry.targetResource,
      result: entry.result
    });

    // Keep only recent activities (last hour)
    const oneHourAgo = Date.now() - 3600000;
    const recentActivities = userActivities.filter(a => a.timestamp > oneHourAgo);
    this.activityTracking.set(entry.userId, recentActivities);

    // Check for suspicious patterns
    await this.checkSuspiciousActivity(entry.userId, recentActivities);
  }

  async checkSuspiciousActivity(userId, activities) {
    // Check for rapid actions
    if (activities.length > this.options.suspiciousActivityThreshold) {
      await this.createSuspiciousActivityAlert(userId, 'rapid_actions', {
        activityCount: activities.length,
        timeWindow: '1 hour'
      });
    }

    // Check for failed actions pattern
    const failedActions = activities.filter(a => a.result === 'failure');
    if (failedActions.length > 5) {
      await this.createSuspiciousActivityAlert(userId, 'multiple_failures', {
        failedCount: failedActions.length,
        totalActions: activities.length
      });
    }

    // Check for privilege escalation attempts
    const privilegeActions = activities.filter(a => 
      a.action.includes('permission') || a.action.includes('role') || a.action.includes('admin')
    );
    if (privilegeActions.length > 0) {
      await this.createSuspiciousActivityAlert(userId, 'privilege_escalation_attempt', {
        privilegeActions: privilegeActions.length
      });
    }
  }

  async createSuspiciousActivityAlert(userId, type, details) {
    const alertData = {
      category: 'security_events',
      eventType: 'suspicious_activity_detected',
      severity: 'warning',
      userId,
      action: 'suspicious_activity_alert',
      description: `Suspicious activity detected: ${type}`,
      targetResource: 'system',
      result: 'success',
      context: { alertType: type, ...details }
    };

    // Create audit entry for the alert itself
    await this.auditEvent(alertData);

    // Emit for real-time processing
    this.emit('suspicious-activity-detected', {
      userId,
      type,
      details,
      timestamp: Date.now()
    });

    logger.warn(`Suspicious activity detected: ${type}`, { userId, ...details });
  }

  async flushBuffer() {
    if (this.entryBuffer.length === 0) return;

    try {
      const entries = [...this.entryBuffer];
      this.entryBuffer = [];

      await this.writeEntriesToFile(entries);
      
      // Update integrity tracking
      if (this.options.tamperProtection) {
        await this.updateIntegrityTracking(entries);
      }

      logger.debug(`Flushed ${entries.length} audit entries to disk`);
    } catch (error) {
      logger.error('Failed to flush audit buffer:', error);
      // Put entries back in buffer for retry
      this.entryBuffer.unshift(...entries);
      throw error;
    }
  }

  async writeEntriesToFile(entries) {
    if (!this.currentLogFile) {
      await this.rotateLogFile();
    }

    for (const entry of entries) {
      let logLine = JSON.stringify(entry) + '\n';
      
      // Encrypt if enabled
      if (this.options.encryptAuditLogs && this.encryptionKey) {
        logLine = this.encryptLogLine(logLine);
      }

      await fs.appendFile(this.currentLogFile, logLine);
    }

    // Check if file size exceeds limit
    const stats = await fs.stat(this.currentLogFile);
    if (stats.size > this.options.maxFileSize) {
      await this.rotateLogFile();
    }
  }

  encryptLogLine(logLine) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipher('aes-256-cbc', this.encryptionKey);
    cipher.setAutoPadding(true);
    
    let encrypted = cipher.update(logLine, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    return iv.toString('hex') + ':' + encrypted + '\n';
  }

  decryptLogLine(encryptedLine) {
    const [ivHex, encryptedData] = encryptedLine.trim().split(':');
    const iv = Buffer.from(ivHex, 'hex');
    
    const decipher = crypto.createDecipher('aes-256-cbc', this.encryptionKey);
    let decrypted = decipher.update(encryptedData, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return decrypted;
  }

  async rotateLogFile() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `audit-${timestamp}-${this.logFileRotationCount}.log`;
    this.currentLogFile = path.join(this.options.storageDir, filename);
    this.logFileRotationCount++;
    
    this.metrics.filesCreated++;
    
    logger.info(`Rotated audit log file: ${filename}`);
  }

  async initializeLogFile() {
    await this.rotateLogFile();
  }

  startPeriodicFlush() {
    setInterval(async () => {
      if (this.entryBuffer.length > 0) {
        await this.flushBuffer();
      }
    }, this.options.flushInterval);
  }

  startIntegrityMonitoring() {
    // Check integrity every hour
    setInterval(async () => {
      await this.performIntegrityCheck();
    }, 3600000);
  }

  async updateIntegrityTracking(entries) {
    for (const entry of entries) {
      const hash = crypto.createHash('sha256').update(JSON.stringify(entry)).digest('hex');
      this.integrityHashes.set(entry.id, hash);
    }
  }

  async performIntegrityCheck() {
    this.metrics.integrityChecks++;
    
    // This would check file integrity against stored hashes
    // Simplified for demo
    const suspiciousSamples = Math.random() < 0.01; // 1% chance of finding issues
    
    if (suspiciousSamples) {
      this.metrics.tamperAttempts++;
      
      await this.auditEvent({
        category: 'security_events',
        eventType: 'integrity_check_failed',
        severity: 'critical',
        userId: 'system',
        action: 'integrity_check',
        description: 'Potential tampering detected in audit logs',
        targetResource: 'audit_logs',
        result: 'failure'
      });

      this.emit('integrity-violation-detected', {
        timestamp: Date.now(),
        details: 'Audit log integrity check failed'
      });
    }
  }

  async queryAuditTrail(query) {
    this.metrics.queriesPerformed++;
    
    try {
      const results = await this.performQuery(query);
      
      // Audit the query itself
      await this.auditEvent({
        category: 'system_events',
        eventType: 'audit_query',
        severity: 'info',
        userId: query.requestedBy,
        action: 'query_audit_trail',
        description: 'Audit trail queried',
        targetResource: 'audit_logs',
        result: 'success',
        context: {
          queryType: query.type,
          resultCount: results.length,
          timeRange: query.timeRange
        }
      });

      return results;
    } catch (error) {
      await this.auditEvent({
        category: 'system_events',
        eventType: 'audit_query_failed',
        severity: 'error',
        userId: query.requestedBy,
        action: 'query_audit_trail',
        description: 'Audit trail query failed',
        targetResource: 'audit_logs',
        result: 'failure',
        context: { error: error.message }
      });
      
      throw error;
    }
  }

  async performQuery(query) {
    const results = [];
    
    // Use indexes for efficient querying
    let candidateIds = new Set();
    
    // Filter by user
    if (query.userId) {
      const userIds = this.userIndex.get(query.userId) || [];
      if (candidateIds.size === 0) {
        candidateIds = new Set(userIds);
      } else {
        candidateIds = new Set(userIds.filter(id => candidateIds.has(id)));
      }
    }

    // Filter by time range
    if (query.startTime || query.endTime) {
      const timeFilteredIds = this.filterByTimeRange(query.startTime, query.endTime);
      if (candidateIds.size === 0) {
        candidateIds = timeFilteredIds;
      } else {
        candidateIds = new Set(Array.from(timeFilteredIds).filter(id => candidateIds.has(id)));
      }
    }

    // Filter by resource
    if (query.resource) {
      const resourceIds = this.resourceIndex.get(query.resource) || [];
      if (candidateIds.size === 0) {
        candidateIds = new Set(resourceIds);
      } else {
        candidateIds = new Set(resourceIds.filter(id => candidateIds.has(id)));
      }
    }

    // Filter by event type
    if (query.category || query.eventType) {
      const eventKey = `${query.category || '*'}:${query.eventType || '*'}`;
      const eventIds = this.eventTypeIndex.get(eventKey) || [];
      if (candidateIds.size === 0) {
        candidateIds = new Set(eventIds);
      } else {
        candidateIds = new Set(eventIds.filter(id => candidateIds.has(id)));
      }
    }

    // Load matching entries (this would read from files in a real implementation)
    for (const entryId of candidateIds) {
      const entry = await this.loadAuditEntry(entryId);
      if (entry && this.matchesQuery(entry, query)) {
        results.push(entry);
      }
    }

    // Sort by timestamp (newest first)
    results.sort((a, b) => b.timestamp - a.timestamp);

    // Apply limit
    if (query.limit) {
      return results.slice(0, query.limit);
    }

    return results;
  }

  filterByTimeRange(startTime, endTime) {
    const start = startTime || 0;
    const end = endTime || Date.now();
    const matchingIds = new Set();

    for (const [dateString, ids] of this.timestampIndex) {
      const date = new Date(dateString).getTime();
      if (date >= start && date <= end) {
        ids.forEach(id => matchingIds.add(id));
      }
    }

    return matchingIds;
  }

  async loadAuditEntry(entryId) {
    // In a real implementation, this would read from the appropriate log file
    // For demo, we'll return a simulated entry
    return {
      id: entryId,
      timestamp: Date.now(),
      category: 'system_events',
      eventType: 'simulated',
      userId: 'user123',
      action: 'load_entry',
      description: 'Simulated audit entry'
    };
  }

  matchesQuery(entry, query) {
    // Apply additional filters that weren't handled by indexes
    if (query.severity && entry.severity !== query.severity) {
      return false;
    }

    if (query.result && entry.result !== query.result) {
      return false;
    }

    if (query.ipAddress && entry.ipAddress !== query.ipAddress) {
      return false;
    }

    if (query.searchText) {
      const searchText = query.searchText.toLowerCase();
      const entryText = JSON.stringify(entry).toLowerCase();
      if (!entryText.includes(searchText)) {
        return false;
      }
    }

    return true;
  }

  updateCategoryMetrics(category) {
    const current = this.metrics.entriesPerCategory.get(category) || 0;
    this.metrics.entriesPerCategory.set(category, current + 1);
  }

  async loadIndexes() {
    // In a real implementation, this would load indexes from persistent storage
    logger.debug('Audit trail indexes loaded');
  }

  async saveIndexes() {
    // In a real implementation, this would save indexes to persistent storage
    logger.debug('Audit trail indexes saved');
  }

  // Convenience methods for common audit events
  async auditAuthentication(userId, action, result, details = {}) {
    return await this.auditEvent({
      category: 'authentication',
      eventType: 'user_authentication',
      userId,
      action,
      result,
      description: `User ${action} attempt`,
      targetResource: 'authentication_system',
      ...details
    });
  }

  async auditPermissionChange(userId, targetUserId, oldPermissions, newPermissions, details = {}) {
    return await this.auditEvent({
      category: 'authorization',
      eventType: 'permission_change',
      userId,
      action: 'modify_permissions',
      result: 'success',
      description: `Permissions modified for user ${targetUserId}`,
      targetResource: 'user_permissions',
      targetId: targetUserId,
      beforeState: oldPermissions,
      afterState: newPermissions,
      ...details
    });
  }

  async auditDataAccess(userId, resource, action, result, details = {}) {
    return await this.auditEvent({
      category: 'data_access',
      eventType: 'data_access',
      userId,
      action,
      result,
      description: `Data ${action} on ${resource}`,
      targetResource: resource,
      ...details
    });
  }

  async auditConfigurationChange(userId, configItem, oldValue, newValue, details = {}) {
    return await this.auditEvent({
      category: 'configuration_changes',
      eventType: 'config_change',
      userId,
      action: 'modify_configuration',
      result: 'success',
      description: `Configuration changed: ${configItem}`,
      targetResource: configItem,
      beforeState: oldValue,
      afterState: newValue,
      ...details
    });
  }

  async auditSystemEvent(eventType, description, details = {}) {
    return await this.auditEvent({
      category: 'system_events',
      eventType,
      userId: 'system',
      action: eventType,
      result: 'success',
      description,
      targetResource: 'system',
      ...details
    });
  }

  // Public API methods
  async getAuditSummary(timeRange = '24h') {
    const endTime = Date.now();
    const startTime = endTime - this.parseTimeRange(timeRange);
    
    const query = {
      startTime,
      endTime,
      requestedBy: 'system'
    };

    const entries = await this.queryAuditTrail(query);
    
    const summary = {
      totalEntries: entries.length,
      timeRange: { start: new Date(startTime), end: new Date(endTime) },
      byCategory: {},
      bySeverity: {},
      byResult: {},
      topUsers: {},
      topResources: {}
    };

    // Analyze entries
    entries.forEach(entry => {
      // By category
      summary.byCategory[entry.category] = (summary.byCategory[entry.category] || 0) + 1;
      
      // By severity
      summary.bySeverity[entry.severity] = (summary.bySeverity[entry.severity] || 0) + 1;
      
      // By result
      summary.byResult[entry.result] = (summary.byResult[entry.result] || 0) + 1;
      
      // Top users
      if (entry.userId) {
        summary.topUsers[entry.userId] = (summary.topUsers[entry.userId] || 0) + 1;
      }
      
      // Top resources
      if (entry.targetResource) {
        summary.topResources[entry.targetResource] = (summary.topResources[entry.targetResource] || 0) + 1;
      }
    });

    return summary;
  }

  parseTimeRange(range) {
    const units = {
      'h': 3600000,      // hours
      'd': 86400000,     // days
      'w': 604800000,    // weeks
      'm': 2592000000    // months (30 days)
    };

    const match = range.match(/^(\d+)([hdwm])$/);
    if (!match) {
      throw new Error('Invalid time range format. Use format like "24h", "7d", "1w", "1m"');
    }

    const [, amount, unit] = match;
    return parseInt(amount) * units[unit];
  }

  getMetrics() {
    return {
      ...this.metrics,
      bufferSize: this.entryBuffer.length,
      indexSizes: {
        users: this.userIndex.size,
        resources: this.resourceIndex.size,
        timestamps: this.timestampIndex.size,
        eventTypes: this.eventTypeIndex.size
      },
      activeUserTracking: this.activityTracking.size
    };
  }

  async generateComplianceReport(startDate, endDate, complianceStandard = 'SOX') {
    // Generate compliance reports for standards like SOX, GDPR, HIPAA, etc.
    const query = {
      startTime: new Date(startDate).getTime(),
      endTime: new Date(endDate).getTime(),
      requestedBy: 'compliance_system'
    };

    const entries = await this.queryAuditTrail(query);
    
    // Filter for compliance-relevant events
    const complianceEvents = entries.filter(entry => 
      entry.complianceFlags.includes(complianceStandard.toLowerCase()) ||
      this.isComplianceRelevant(entry, complianceStandard)
    );

    const report = {
      standard: complianceStandard,
      period: { start: startDate, end: endDate },
      totalEvents: complianceEvents.length,
      criticalEvents: complianceEvents.filter(e => e.severity === 'critical').length,
      categories: {},
      integrityVerification: await this.verifyIntegrity(complianceEvents),
      generatedAt: new Date().toISOString()
    };

    return report;
  }

  isComplianceRelevant(entry, standard) {
    const complianceCategories = {
      'SOX': ['authentication', 'authorization', 'data_modification', 'configuration_changes'],
      'GDPR': ['data_access', 'data_modification', 'user_management'],
      'HIPAA': ['data_access', 'authentication', 'authorization']
    };

    return complianceCategories[standard]?.includes(entry.category) || false;
  }

  async verifyIntegrity(entries) {
    // Verify integrity of entries
    let verified = 0;
    let failed = 0;

    for (const entry of entries) {
      if (this.verifyEntryIntegrity(entry)) {
        verified++;
      } else {
        failed++;
      }
    }

    return { verified, failed, total: entries.length };
  }

  verifyEntryIntegrity(entry) {
    if (!entry.checksum && !entry.signature) return true; // No integrity protection

    // Verify checksum
    if (entry.checksum) {
      const calculatedChecksum = this.calculateChecksum(entry);
      if (calculatedChecksum !== entry.checksum) return false;
    }

    // Verify signature
    if (entry.signature) {
      const calculatedSignature = this.createSignature(entry);
      if (calculatedSignature !== entry.signature) return false;
    }

    return true;
  }

  async cleanup() {
    // Flush any remaining entries
    if (this.entryBuffer.length > 0) {
      await this.flushBuffer();
    }

    // Save indexes
    await this.saveIndexes();

    // Clear memory
    this.entryBuffer = [];
    this.userIndex.clear();
    this.resourceIndex.clear();
    this.timestampIndex.clear();
    this.eventTypeIndex.clear();
    this.activityTracking.clear();
    this.integrityHashes.clear();

    this.removeAllListeners();
    logger.info('Audit Trail system cleaned up');
  }
}

module.exports = AuditTrail;