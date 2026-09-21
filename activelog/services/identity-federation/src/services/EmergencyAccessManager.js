const EventEmitter = require('events');
const crypto = require('crypto');
const User = require('../models/User');
const Organization = require('../models/Organization');
const EmergencyAccess = require('../models/EmergencyAccess');
const AuditLogger = require('./AuditLogger');

class EmergencyAccessManager extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      enabled: config.enabled !== false,
      masterKeyRequired: config.masterKeyRequired !== false,
      multiAuthRequired: config.multiAuthRequired !== false,
      auditRequired: config.auditRequired !== false,
      accessDuration: config.accessDuration || 24 * 60 * 60 * 1000, // 24 hours
      cooldownPeriod: config.cooldownPeriod || 7 * 24 * 60 * 60 * 1000, // 7 days
      requiredApprovals: config.requiredApprovals || 2,
      ...config
    };
    
    this.auditLogger = new AuditLogger();
    this.emergencyRoles = {
      'system_admin': 'Full system access for critical incidents',
      'security_officer': 'Security-related emergency access',
      'compliance_officer': 'Compliance and legal emergency access',
      'recovery_agent': 'Account recovery assistance'
    };
    
    this.emergencyScenarios = {
      'account_lockout': 'User locked out of critical account',
      'security_breach': 'Security incident requiring immediate access',
      'system_failure': 'System failure requiring emergency intervention',
      'legal_compliance': 'Legal or regulatory compliance requirement',
      'data_recovery': 'Critical data recovery situation',
      'key_recovery': 'Lost encryption keys or credentials'
    };
  }

  async requestEmergencyAccess(requestData) {
    try {
      if (!this.config.enabled) {
        throw new Error('Emergency access is disabled');
      }

      const requestId = crypto.randomUUID();
      const request = new EmergencyAccess({
        requestId,
        requestedBy: requestData.requestedBy,
        targetUserId: requestData.targetUserId,
        organizationId: requestData.organizationId,
        scenario: requestData.scenario,
        justification: requestData.justification,
        requestedPermissions: requestData.permissions || [],
        urgencyLevel: requestData.urgencyLevel || 'high',
        status: 'pending',
        requestedAt: new Date(),
        expiresAt: new Date(Date.now() + this.config.accessDuration),
        metadata: {
          ipAddress: requestData.ipAddress,
          userAgent: requestData.userAgent,
          location: requestData.location,
          contactInfo: requestData.contactInfo
        },
        approvals: [],
        accessLog: []
      });

      await request.save();

      // Immediate approval for critical scenarios with proper authentication
      if (requestData.urgencyLevel === 'critical' && await this.validateCriticalAccess(requestData)) {
        await this.autoApproveEmergencyAccess(requestId, 'system_automated');
      } else {
        // Notify approvers
        await this.notifyApprovers(request);
      }

      await this.auditLogger.log('emergency_access_requested', 'success', {
        requestId,
        requestedBy: requestData.requestedBy,
        targetUserId: requestData.targetUserId,
        scenario: requestData.scenario,
        urgencyLevel: requestData.urgencyLevel
      });

      this.emit('emergency_access_requested', {
        requestId,
        request,
        urgencyLevel: requestData.urgencyLevel
      });

      return {
        requestId,
        status: request.status,
        estimatedApprovalTime: this.calculateApprovalTime(requestData.urgencyLevel),
        requiredApprovals: this.config.requiredApprovals,
        currentApprovals: request.approvals.length
      };
    } catch (error) {
      await this.auditLogger.log('emergency_access_requested', 'failed', {
        requestData,
        error: error.message
      });
      throw error;
    }
  }

  async approveEmergencyAccess(requestId, approverUserId, approvalData = {}) {
    try {
      const request = await EmergencyAccess.findOne({ requestId });
      if (!request) {
        throw new Error('Emergency access request not found');
      }

      if (request.status !== 'pending') {
        throw new Error(`Cannot approve request with status: ${request.status}`);
      }

      // Verify approver authority
      const canApprove = await this.verifyApproverAuthority(approverUserId, request);
      if (!canApprove) {
        throw new Error('Insufficient authority to approve emergency access');
      }

      // Check for duplicate approval
      const existingApproval = request.approvals.find(a => a.approvedBy === approverUserId);
      if (existingApproval) {
        throw new Error('User has already approved this request');
      }

      // Add approval
      request.approvals.push({
        approvedBy: approverUserId,
        approvedAt: new Date(),
        method: approvalData.method || 'manual',
        justification: approvalData.justification,
        conditions: approvalData.conditions || []
      });

      // Check if sufficient approvals received
      if (request.approvals.length >= this.config.requiredApprovals) {
        request.status = 'approved';
        request.approvedAt = new Date();
        request.accessToken = await this.generateEmergencyAccessToken(request);
        
        // Set actual expiration based on urgency
        const actualDuration = this.getAccessDurationForUrgency(request.urgencyLevel);
        request.expiresAt = new Date(Date.now() + actualDuration);
      }

      await request.save();

      await this.auditLogger.log('emergency_access_approved', 'success', {
        requestId,
        approvedBy: approverUserId,
        totalApprovals: request.approvals.length,
        status: request.status,
        method: approvalData.method
      });

      this.emit('emergency_access_approved', {
        requestId,
        request,
        approvedBy: approverUserId,
        isFullyApproved: request.status === 'approved'
      });

      if (request.status === 'approved') {
        // Notify requester and start monitoring
        await this.notifyAccessGranted(request);
        await this.startAccessMonitoring(request);
      }

      return {
        requestId,
        status: request.status,
        approvals: request.approvals.length,
        accessToken: request.accessToken,
        expiresAt: request.expiresAt
      };
    } catch (error) {
      await this.auditLogger.log('emergency_access_approved', 'failed', {
        requestId,
        approverUserId,
        error: error.message
      });
      throw error;
    }
  }

  async denyEmergencyAccess(requestId, denierUserId, denialReason) {
    try {
      const request = await EmergencyAccess.findOne({ requestId });
      if (!request) {
        throw new Error('Emergency access request not found');
      }

      request.status = 'denied';
      request.deniedAt = new Date();
      request.deniedBy = denierUserId;
      request.denialReason = denialReason;

      await request.save();

      await this.auditLogger.log('emergency_access_denied', 'success', {
        requestId,
        deniedBy: denierUserId,
        reason: denialReason
      });

      this.emit('emergency_access_denied', {
        requestId,
        request,
        deniedBy: denierUserId,
        reason: denialReason
      });

      // Notify requester
      await this.notifyAccessDenied(request, denialReason);

      return { requestId, status: 'denied' };
    } catch (error) {
      await this.auditLogger.log('emergency_access_denied', 'failed', {
        requestId,
        denierUserId,
        error: error.message
      });
      throw error;
    }
  }

  async activateEmergencyAccess(accessToken, activationData = {}) {
    try {
      const request = await EmergencyAccess.findOne({ accessToken, status: 'approved' });
      if (!request) {
        throw new Error('Invalid or expired emergency access token');
      }

      if (request.expiresAt < new Date()) {
        request.status = 'expired';
        await request.save();
        throw new Error('Emergency access has expired');
      }

      // Activate access
      request.status = 'active';
      request.activatedAt = new Date();
      request.activatedBy = activationData.activatedBy || request.requestedBy;
      request.activationContext = {
        ipAddress: activationData.ipAddress,
        userAgent: activationData.userAgent,
        location: activationData.location,
        deviceFingerprint: activationData.deviceFingerprint
      };

      // Log initial access
      request.accessLog.push({
        action: 'access_activated',
        timestamp: new Date(),
        details: activationData
      });

      await request.save();

      // Create temporary elevated permissions
      const emergencySession = await this.createEmergencySession(request);

      await this.auditLogger.log('emergency_access_activated', 'success', {
        requestId: request.requestId,
        activatedBy: request.activatedBy,
        targetUserId: request.targetUserId,
        permissions: request.requestedPermissions
      });

      this.emit('emergency_access_activated', {
        request,
        emergencySession,
        activatedBy: request.activatedBy
      });

      return {
        requestId: request.requestId,
        sessionId: emergencySession.sessionId,
        permissions: request.requestedPermissions,
        expiresAt: request.expiresAt,
        monitoringEnabled: true
      };
    } catch (error) {
      await this.auditLogger.log('emergency_access_activated', 'failed', {
        accessToken: accessToken?.substring(0, 10) + '...',
        error: error.message
      });
      throw error;
    }
  }

  async revokeEmergencyAccess(requestId, revokedBy, reason = 'manual_revocation') {
    try {
      const request = await EmergencyAccess.findOne({ requestId });
      if (!request) {
        throw new Error('Emergency access request not found');
      }

      const wasActive = request.status === 'active';
      
      request.status = 'revoked';
      request.revokedAt = new Date();
      request.revokedBy = revokedBy;
      request.revocationReason = reason;

      // Log revocation
      request.accessLog.push({
        action: 'access_revoked',
        timestamp: new Date(),
        revokedBy,
        reason
      });

      await request.save();

      // Terminate any active emergency sessions
      if (wasActive) {
        await this.terminateEmergencySessions(requestId);
      }

      await this.auditLogger.log('emergency_access_revoked', 'success', {
        requestId,
        revokedBy,
        reason,
        wasActive
      });

      this.emit('emergency_access_revoked', {
        requestId,
        request,
        revokedBy,
        reason
      });

      return { requestId, status: 'revoked' };
    } catch (error) {
      await this.auditLogger.log('emergency_access_revoked', 'failed', {
        requestId,
        revokedBy,
        error: error.message
      });
      throw error;
    }
  }

  async logEmergencyAction(requestId, actionData) {
    try {
      const request = await EmergencyAccess.findOne({ requestId, status: 'active' });
      if (!request) {
        throw new Error('No active emergency access found');
      }

      const logEntry = {
        action: actionData.action,
        timestamp: new Date(),
        resource: actionData.resource,
        resourceId: actionData.resourceId,
        details: actionData.details,
        outcome: actionData.outcome
      };

      request.accessLog.push(logEntry);
      await request.save();

      await this.auditLogger.log('emergency_action_logged', 'success', {
        requestId,
        action: actionData.action,
        resource: actionData.resource,
        outcome: actionData.outcome
      });

      this.emit('emergency_action_logged', {
        requestId,
        logEntry
      });

      return logEntry;
    } catch (error) {
      await this.auditLogger.log('emergency_action_logged', 'failed', {
        requestId,
        error: error.message
      });
      throw error;
    }
  }

  async getEmergencyAccessHistory(filters = {}) {
    try {
      const query = {};
      
      if (filters.requestedBy) {
        query.requestedBy = filters.requestedBy;
      }
      
      if (filters.targetUserId) {
        query.targetUserId = filters.targetUserId;
      }
      
      if (filters.organizationId) {
        query.organizationId = filters.organizationId;
      }
      
      if (filters.scenario) {
        query.scenario = filters.scenario;
      }
      
      if (filters.status) {
        query.status = filters.status;
      }
      
      if (filters.startDate || filters.endDate) {
        query.requestedAt = {};
        if (filters.startDate) {
          query.requestedAt.$gte = new Date(filters.startDate);
        }
        if (filters.endDate) {
          query.requestedAt.$lte = new Date(filters.endDate);
        }
      }

      const requests = await EmergencyAccess.find(query)
        .populate('requestedBy', 'email firstName lastName')
        .populate('targetUserId', 'email firstName lastName')
        .sort({ requestedAt: -1 })
        .limit(filters.limit || 100);

      return requests.map(request => ({
        requestId: request.requestId,
        requestedBy: request.requestedBy,
        targetUser: request.targetUserId,
        scenario: request.scenario,
        status: request.status,
        urgencyLevel: request.urgencyLevel,
        requestedAt: request.requestedAt,
        approvedAt: request.approvedAt,
        activatedAt: request.activatedAt,
        revokedAt: request.revokedAt,
        expiresAt: request.expiresAt,
        approvals: request.approvals.length,
        actionCount: request.accessLog.length
      }));
    } catch (error) {
      console.error('Error retrieving emergency access history:', error);
      return [];
    }
  }

  // Helper methods

  async validateCriticalAccess(requestData) {
    // Validate master key if required
    if (this.config.masterKeyRequired) {
      const isValidMasterKey = await this.verifyMasterKey(requestData.masterKey);
      if (!isValidMasterKey) {
        return false;
      }
    }

    // Validate multi-factor authentication if required
    if (this.config.multiAuthRequired) {
      const isValidMFA = await this.verifyEmergencyMFA(requestData.requestedBy, requestData.mfaCode);
      if (!isValidMFA) {
        return false;
      }
    }

    return true;
  }

  async autoApproveEmergencyAccess(requestId, approvedBy) {
    const request = await EmergencyAccess.findOne({ requestId });
    if (!request) return;

    request.status = 'approved';
    request.approvedAt = new Date();
    request.accessToken = await this.generateEmergencyAccessToken(request);
    request.approvals.push({
      approvedBy,
      approvedAt: new Date(),
      method: 'automated_critical',
      justification: 'Critical emergency auto-approval'
    });

    await request.save();
  }

  async verifyApproverAuthority(approverUserId, request) {
    const approver = await User.findById(approverUserId);
    if (!approver) return false;

    // Check if user has emergency approval permissions
    const hasEmergencyRole = approver.permissions?.includes('emergency:approve') ||
                           approver.roles?.some(role => this.emergencyRoles[role]);
    
    return hasEmergencyRole;
  }

  async generateEmergencyAccessToken(request) {
    const tokenData = {
      requestId: request.requestId,
      targetUserId: request.targetUserId,
      permissions: request.requestedPermissions,
      scenario: request.scenario,
      isEmergencyAccess: true,
      generatedAt: new Date()
    };

    return crypto.createHash('sha256')
      .update(JSON.stringify(tokenData) + process.env.EMERGENCY_MASTER_KEY)
      .digest('hex');
  }

  async createEmergencySession(request) {
    const sessionId = crypto.randomUUID();
    const session = {
      sessionId,
      requestId: request.requestId,
      userId: request.targetUserId,
      type: 'emergency_access',
      permissions: request.requestedPermissions,
      createdAt: new Date(),
      expiresAt: request.expiresAt,
      isActive: true
    };

    // In production, this would integrate with session management
    return session;
  }

  async startAccessMonitoring(request) {
    // Set up real-time monitoring for emergency access usage
    this.emit('emergency_monitoring_started', {
      requestId: request.requestId,
      targetUserId: request.targetUserId,
      permissions: request.requestedPermissions
    });
  }

  async terminateEmergencySessions(requestId) {
    // Terminate all active sessions for this emergency access
    this.emit('emergency_sessions_terminated', { requestId });
  }

  async notifyApprovers(request) {
    this.emit('emergency_approval_required', {
      requestId: request.requestId,
      scenario: request.scenario,
      urgencyLevel: request.urgencyLevel,
      justification: request.justification
    });
  }

  async notifyAccessGranted(request) {
    this.emit('emergency_access_granted', {
      requestId: request.requestId,
      requestedBy: request.requestedBy,
      accessToken: request.accessToken,
      expiresAt: request.expiresAt
    });
  }

  async notifyAccessDenied(request, reason) {
    this.emit('emergency_access_denied_notification', {
      requestId: request.requestId,
      requestedBy: request.requestedBy,
      reason
    });
  }

  calculateApprovalTime(urgencyLevel) {
    const times = {
      'critical': new Date(Date.now() + 15 * 60 * 1000), // 15 minutes
      'high': new Date(Date.now() + 60 * 60 * 1000), // 1 hour
      'medium': new Date(Date.now() + 4 * 60 * 60 * 1000), // 4 hours
      'low': new Date(Date.now() + 24 * 60 * 60 * 1000) // 24 hours
    };

    return times[urgencyLevel] || times['medium'];
  }

  getAccessDurationForUrgency(urgencyLevel) {
    const durations = {
      'critical': 4 * 60 * 60 * 1000, // 4 hours
      'high': 8 * 60 * 60 * 1000, // 8 hours
      'medium': 24 * 60 * 60 * 1000, // 24 hours
      'low': 48 * 60 * 60 * 1000 // 48 hours
    };

    return durations[urgencyLevel] || durations['medium'];
  }

  async verifyMasterKey(providedKey) {
    const masterKey = process.env.EMERGENCY_MASTER_KEY;
    return masterKey && providedKey === masterKey;
  }

  async verifyEmergencyMFA(userId, mfaCode) {
    // Implementation would verify MFA code for emergency access
    return true; // Simplified for example
  }
}

module.exports = EmergencyAccessManager;