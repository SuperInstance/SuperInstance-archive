const EventEmitter = require('events');
const crypto = require('crypto');
const User = require('../models/User');
const Organization = require('../models/Organization');
const PrivacyRequest = require('../models/PrivacyRequest');
const DataProcessingRecord = require('../models/DataProcessingRecord');
const AuditLogger = require('./AuditLogger');

class PrivacyControlManager extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      gdprCompliance: config.gdprCompliance !== false,
      ccpaCompliance: config.ccpaCompliance !== false,
      dataRetentionDays: config.dataRetentionDays || 365,
      anonymizationDelay: config.anonymizationDelay || 30, // days after deletion request
      encryptionAlgorithm: 'aes-256-gcm',
      minAge: config.minAge || 13,
      parentalConsentAge: config.parentalConsentAge || 16,
      ...config
    };
    
    this.auditLogger = new AuditLogger();
    this.dataCategories = {
      'personal_info': 'Personal Information',
      'contact_info': 'Contact Information',
      'financial_info': 'Financial Information',
      'health_info': 'Health Information',
      'biometric_info': 'Biometric Information',
      'location_info': 'Location Information',
      'behavioral_info': 'Behavioral Information',
      'technical_info': 'Technical Information',
      'communication_info': 'Communication Information',
      'preferences': 'User Preferences'
    };
    
    this.processingPurposes = {
      'essential_service': 'Essential service functionality',
      'performance_analytics': 'Performance and analytics',
      'marketing': 'Marketing communications',
      'personalization': 'Content personalization',
      'security': 'Security and fraud prevention',
      'legal_compliance': 'Legal compliance',
      'customer_support': 'Customer support',
      'research': 'Research and development'
    };
    
    this.legalBases = {
      'consent': 'User consent',
      'contract': 'Contract performance',
      'legal_obligation': 'Legal obligation',
      'vital_interests': 'Vital interests',
      'public_task': 'Public task',
      'legitimate_interests': 'Legitimate interests'
    };
  }

  async createPrivacyProfile(userId, profileData = {}) {
    try {
      const user = await User.findById(userId);
      if (!user) {
        throw new Error('User not found');
      }

      const privacyProfile = {
        userId,
        preferences: {
          dataMinimization: profileData.dataMinimization !== false,
          allowAnalytics: profileData.allowAnalytics === true,
          allowMarketing: profileData.allowMarketing === true,
          allowPersonalization: profileData.allowPersonalization !== false,
          allowThirdPartySharing: profileData.allowThirdPartySharing === true,
          cookieConsent: profileData.cookieConsent || 'essential_only',
          dataRetentionPeriod: profileData.dataRetentionPeriod || this.config.dataRetentionDays,
          rightToPortability: profileData.rightToPortability !== false,
          rightToRectification: profileData.rightToRectification !== false,
          rightToErasure: profileData.rightToErasure !== false
        },
        consentHistory: [{
          timestamp: new Date(),
          action: 'profile_created',
          preferences: profileData
        }],
        dataProcessingConsents: {},
        createdAt: new Date(),
        lastUpdated: new Date()
      };

      // Initialize consent for each processing purpose
      Object.keys(this.processingPurposes).forEach(purpose => {
        privacyProfile.dataProcessingConsents[purpose] = {
          granted: profileData[purpose] === true || purpose === 'essential_service',
          timestamp: new Date(),
          legalBasis: purpose === 'essential_service' ? 'contract' : 'consent',
          dataCategories: this.getDataCategoriesForPurpose(purpose)
        };
      });

      // Store privacy profile
      user.privacyProfile = privacyProfile;
      await user.save();

      await this.auditLogger.log('privacy_profile_created', 'success', {
        userId,
        preferences: privacyProfile.preferences
      });

      this.emit('privacy_profile_created', {
        userId,
        privacyProfile
      });

      return privacyProfile;
    } catch (error) {
      await this.auditLogger.log('privacy_profile_created', 'failed', {
        userId,
        error: error.message
      });
      throw error;
    }
  }

  async updatePrivacyPreferences(userId, preferences, context = {}) {
    try {
      const user = await User.findById(userId);
      if (!user || !user.privacyProfile) {
        throw new Error('User or privacy profile not found');
      }

      const oldPreferences = { ...user.privacyProfile.preferences };
      
      // Update preferences
      Object.assign(user.privacyProfile.preferences, preferences);
      
      // Update consent history
      user.privacyProfile.consentHistory.push({
        timestamp: new Date(),
        action: 'preferences_updated',
        changes: preferences,
        context: {
          ipAddress: context.ipAddress,
          userAgent: context.userAgent,
          source: context.source
        }
      });

      user.privacyProfile.lastUpdated = new Date();
      await user.save();

      // Check if consent changes require action
      await this.handleConsentChanges(userId, oldPreferences, preferences);

      await this.auditLogger.log('privacy_preferences_updated', 'success', {
        userId,
        oldPreferences,
        newPreferences: preferences,
        context
      });

      this.emit('privacy_preferences_updated', {
        userId,
        oldPreferences,
        newPreferences: preferences
      });

      return user.privacyProfile.preferences;
    } catch (error) {
      await this.auditLogger.log('privacy_preferences_updated', 'failed', {
        userId,
        preferences,
        error: error.message
      });
      throw error;
    }
  }

  async grantProcessingConsent(userId, purpose, dataCategories = [], legalBasis = 'consent') {
    try {
      const user = await User.findById(userId);
      if (!user || !user.privacyProfile) {
        throw new Error('User or privacy profile not found');
      }

      if (!this.processingPurposes[purpose]) {
        throw new Error(`Invalid processing purpose: ${purpose}`);
      }

      user.privacyProfile.dataProcessingConsents[purpose] = {
        granted: true,
        timestamp: new Date(),
        legalBasis,
        dataCategories: dataCategories.length > 0 ? dataCategories : this.getDataCategoriesForPurpose(purpose),
        expiresAt: legalBasis === 'consent' ? new Date(Date.now() + 365 * 24 * 60 * 60 * 1000) : null // 1 year
      };

      user.privacyProfile.consentHistory.push({
        timestamp: new Date(),
        action: 'consent_granted',
        purpose,
        legalBasis,
        dataCategories
      });

      user.privacyProfile.lastUpdated = new Date();
      await user.save();

      // Create data processing record
      await this.createDataProcessingRecord(userId, purpose, 'consent_granted', {
        legalBasis,
        dataCategories
      });

      await this.auditLogger.log('processing_consent_granted', 'success', {
        userId,
        purpose,
        legalBasis,
        dataCategories
      });

      this.emit('consent_granted', {
        userId,
        purpose,
        legalBasis,
        dataCategories
      });

      return true;
    } catch (error) {
      await this.auditLogger.log('processing_consent_granted', 'failed', {
        userId,
        purpose,
        error: error.message
      });
      throw error;
    }
  }

  async revokeProcessingConsent(userId, purpose) {
    try {
      const user = await User.findById(userId);
      if (!user || !user.privacyProfile) {
        throw new Error('User or privacy profile not found');
      }

      if (purpose === 'essential_service') {
        throw new Error('Cannot revoke consent for essential service functionality');
      }

      if (!user.privacyProfile.dataProcessingConsents[purpose]) {
        throw new Error('Consent not found for this purpose');
      }

      const previousConsent = user.privacyProfile.dataProcessingConsents[purpose];
      user.privacyProfile.dataProcessingConsents[purpose] = {
        granted: false,
        timestamp: new Date(),
        revokedAt: new Date(),
        previousConsent
      };

      user.privacyProfile.consentHistory.push({
        timestamp: new Date(),
        action: 'consent_revoked',
        purpose
      });

      user.privacyProfile.lastUpdated = new Date();
      await user.save();

      // Create data processing record
      await this.createDataProcessingRecord(userId, purpose, 'consent_revoked');

      // Trigger data cleanup if necessary
      await this.handleConsentRevocation(userId, purpose);

      await this.auditLogger.log('processing_consent_revoked', 'success', {
        userId,
        purpose
      });

      this.emit('consent_revoked', {
        userId,
        purpose
      });

      return true;
    } catch (error) {
      await this.auditLogger.log('processing_consent_revoked', 'failed', {
        userId,
        purpose,
        error: error.message
      });
      throw error;
    }
  }

  async submitDataSubjectRequest(userId, requestType, details = {}) {
    try {
      const user = await User.findById(userId);
      if (!user) {
        throw new Error('User not found');
      }

      const validRequestTypes = [
        'access', 'rectification', 'erasure', 'portability', 
        'restriction', 'objection', 'opt_out'
      ];

      if (!validRequestTypes.includes(requestType)) {
        throw new Error(`Invalid request type: ${requestType}`);
      }

      const request = new PrivacyRequest({
        userId,
        requestType,
        status: 'pending',
        submittedAt: new Date(),
        details: {
          reason: details.reason,
          specificData: details.specificData,
          additionalInfo: details.additionalInfo,
          urgency: details.urgency || 'normal'
        },
        metadata: {
          ipAddress: details.ipAddress,
          userAgent: details.userAgent,
          source: details.source
        }
      });

      await request.save();

      // Auto-process certain types of requests
      if (requestType === 'access' || requestType === 'portability') {
        await this.processDataSubjectRequest(request._id);
      }

      await this.auditLogger.log('data_subject_request_submitted', 'success', {
        userId,
        requestId: request._id,
        requestType,
        details
      });

      this.emit('data_subject_request_submitted', {
        userId,
        request
      });

      return {
        requestId: request._id,
        status: request.status,
        estimatedCompletionTime: this.calculateEstimatedCompletion(requestType)
      };
    } catch (error) {
      await this.auditLogger.log('data_subject_request_submitted', 'failed', {
        userId,
        requestType,
        error: error.message
      });
      throw error;
    }
  }

  async processDataSubjectRequest(requestId) {
    try {
      const request = await PrivacyRequest.findById(requestId).populate('userId');
      if (!request) {
        throw new Error('Request not found');
      }

      request.status = 'processing';
      request.processedAt = new Date();
      await request.save();

      let result = {};

      switch (request.requestType) {
        case 'access':
          result = await this.processAccessRequest(request);
          break;
        case 'rectification':
          result = await this.processRectificationRequest(request);
          break;
        case 'erasure':
          result = await this.processErasureRequest(request);
          break;
        case 'portability':
          result = await this.processPortabilityRequest(request);
          break;
        case 'restriction':
          result = await this.processRestrictionRequest(request);
          break;
        case 'objection':
          result = await this.processObjectionRequest(request);
          break;
        case 'opt_out':
          result = await this.processOptOutRequest(request);
          break;
        default:
          throw new Error(`Unsupported request type: ${request.requestType}`);
      }

      request.status = 'completed';
      request.completedAt = new Date();
      request.result = result;
      await request.save();

      await this.auditLogger.log('data_subject_request_processed', 'success', {
        requestId,
        userId: request.userId._id,
        requestType: request.requestType,
        result
      });

      this.emit('data_subject_request_processed', {
        request,
        result
      });

      return result;
    } catch (error) {
      const request = await PrivacyRequest.findById(requestId);
      if (request) {
        request.status = 'failed';
        request.error = error.message;
        request.failedAt = new Date();
        await request.save();
      }

      await this.auditLogger.log('data_subject_request_processed', 'failed', {
        requestId,
        error: error.message
      });
      throw error;
    }
  }

  async processAccessRequest(request) {
    const userId = request.userId._id;
    const user = await User.findById(userId).populate('organizations');
    
    const accessData = {
      personalData: {
        id: user._id,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        avatar: user.avatar,
        createdAt: user.createdAt,
        lastLoginAt: user.lastLoginAt,
        preferences: user.preferences,
        privacyProfile: user.privacyProfile
      },
      organizations: user.organizations.map(org => ({
        id: org._id,
        name: org.name,
        role: org.members.find(m => m.user.toString() === userId)?.role
      })),
      dataProcessingActivities: await this.getDataProcessingActivities(userId),
      thirdPartySharing: await this.getThirdPartySharing(userId),
      retentionPeriods: await this.getDataRetentionInfo(userId)
    };

    return {
      type: 'data_access',
      data: accessData,
      exportFormat: 'json',
      generatedAt: new Date()
    };
  }

  async processErasureRequest(request) {
    const userId = request.userId._id;
    
    // Check if erasure is possible
    const canErase = await this.checkErasureEligibility(userId);
    if (!canErase.eligible) {
      throw new Error(`Cannot erase data: ${canErase.reason}`);
    }

    // Start anonymization process
    const anonymizationId = await this.scheduleDataAnonymization(userId, {
      delay: this.config.anonymizationDelay,
      reason: 'user_request',
      requestId: request._id
    });

    return {
      type: 'data_erasure',
      status: 'scheduled',
      anonymizationId,
      scheduledDate: new Date(Date.now() + this.config.anonymizationDelay * 24 * 60 * 60 * 1000),
      canCancel: true,
      cancellationDeadline: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) // 7 days
    };
  }

  async createDataProcessingRecord(userId, purpose, action, metadata = {}) {
    const record = new DataProcessingRecord({
      userId,
      purpose,
      action,
      timestamp: new Date(),
      legalBasis: metadata.legalBasis,
      dataCategories: metadata.dataCategories || [],
      retentionPeriod: metadata.retentionPeriod,
      thirdParties: metadata.thirdParties || [],
      metadata
    });

    await record.save();
    return record;
  }

  async anonymizeUserData(userId, options = {}) {
    try {
      const user = await User.findById(userId);
      if (!user) {
        throw new Error('User not found');
      }

      const anonymizationId = crypto.randomUUID();
      const anonymizedData = {
        originalUserId: userId,
        anonymizationId,
        anonymizedAt: new Date(),
        retainedData: {},
        method: options.method || 'k_anonymity'
      };

      // Anonymize personal identifiers
      user.email = `anonymized_${anonymizationId}@deleted.local`;
      user.firstName = 'Deleted';
      user.lastName = 'User';
      user.avatar = null;
      user.isActive = false;
      user.isAnonymized = true;
      user.anonymizedAt = new Date();

      // Remove or anonymize sensitive data based on retention policies
      if (!options.retainPreferences) {
        user.preferences = {};
      }
      
      if (!options.retainSettings) {
        user.settings = {};
      }

      // Clear authentication providers
      user.providers = {};
      user.password = null;
      user.mfaSecret = null;

      await user.save();

      await this.auditLogger.log('user_data_anonymized', 'success', {
        originalUserId: userId,
        anonymizationId,
        method: options.method,
        retainedFields: Object.keys(anonymizedData.retainedData)
      });

      this.emit('user_data_anonymized', {
        originalUserId: userId,
        anonymizationId,
        anonymizedData
      });

      return {
        anonymizationId,
        anonymizedAt: new Date(),
        retainedData: anonymizedData.retainedData
      };
    } catch (error) {
      await this.auditLogger.log('user_data_anonymized', 'failed', {
        userId,
        error: error.message
      });
      throw error;
    }
  }

  async scheduleDataAnonymization(userId, options = {}) {
    const anonymizationId = crypto.randomUUID();
    const scheduledDate = new Date(Date.now() + (options.delay || 30) * 24 * 60 * 60 * 1000);

    // In production, this would use a job queue
    setTimeout(async () => {
      try {
        await this.anonymizeUserData(userId, options);
      } catch (error) {
        console.error('Scheduled anonymization failed:', error);
      }
    }, (options.delay || 30) * 24 * 60 * 60 * 1000);

    await this.auditLogger.log('data_anonymization_scheduled', 'success', {
      userId,
      anonymizationId,
      scheduledDate,
      delay: options.delay
    });

    return anonymizationId;
  }

  // Helper methods

  getDataCategoriesForPurpose(purpose) {
    const categoryMappings = {
      'essential_service': ['personal_info', 'contact_info', 'technical_info'],
      'performance_analytics': ['technical_info', 'behavioral_info'],
      'marketing': ['contact_info', 'preferences', 'behavioral_info'],
      'personalization': ['preferences', 'behavioral_info'],
      'security': ['technical_info', 'location_info'],
      'legal_compliance': ['personal_info', 'contact_info'],
      'customer_support': ['personal_info', 'contact_info', 'communication_info'],
      'research': ['behavioral_info', 'technical_info']
    };

    return categoryMappings[purpose] || [];
  }

  async handleConsentChanges(userId, oldPreferences, newPreferences) {
    // Handle specific consent changes that require immediate action
    if (oldPreferences.allowAnalytics && !newPreferences.allowAnalytics) {
      await this.revokeProcessingConsent(userId, 'performance_analytics');
    }

    if (oldPreferences.allowMarketing && !newPreferences.allowMarketing) {
      await this.revokeProcessingConsent(userId, 'marketing');
    }
  }

  async handleConsentRevocation(userId, purpose) {
    // Clean up data based on revoked consent
    switch (purpose) {
      case 'marketing':
        await this.removeMarketingData(userId);
        break;
      case 'performance_analytics':
        await this.removeAnalyticsData(userId);
        break;
      case 'personalization':
        await this.resetPersonalizationData(userId);
        break;
    }
  }

  calculateEstimatedCompletion(requestType) {
    const completionTimes = {
      'access': new Date(Date.now() + 24 * 60 * 60 * 1000), // 1 day
      'rectification': new Date(Date.now() + 3 * 24 * 60 * 60 * 1000), // 3 days
      'erasure': new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days
      'portability': new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
      'restriction': new Date(Date.now() + 3 * 24 * 60 * 60 * 1000), // 3 days
      'objection': new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
      'opt_out': new Date(Date.now() + 1 * 60 * 60 * 1000) // 1 hour
    };

    return completionTimes[requestType] || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
  }

  async checkErasureEligibility(userId) {
    const user = await User.findById(userId);
    if (!user) {
      return { eligible: false, reason: 'User not found' };
    }

    // Check for legal holds or ongoing processes
    const activeRequests = await PrivacyRequest.find({
      userId,
      status: { $in: ['pending', 'processing'] },
      requestType: { $ne: 'erasure' }
    });

    if (activeRequests.length > 0) {
      return { eligible: false, reason: 'Active privacy requests pending' };
    }

    return { eligible: true };
  }

  async getDataProcessingActivities(userId) {
    return await DataProcessingRecord.find({ userId })
      .sort({ timestamp: -1 })
      .limit(100);
  }

  async getThirdPartySharing(userId) {
    // Return list of third parties data is shared with
    return [];
  }

  async getDataRetentionInfo(userId) {
    const user = await User.findById(userId);
    return {
      defaultRetention: this.config.dataRetentionDays,
      userPreference: user.privacyProfile?.preferences?.dataRetentionPeriod,
      categorySpecific: {
        'personal_info': this.config.dataRetentionDays,
        'behavioral_info': 90,
        'technical_info': 30
      }
    };
  }

  // Placeholder methods for data cleanup
  async removeMarketingData(userId) {
    // Remove marketing-related data
  }

  async removeAnalyticsData(userId) {
    // Remove analytics data
  }

  async resetPersonalizationData(userId) {
    // Reset personalization preferences
  }

  // Additional request processing methods
  async processRectificationRequest(request) {
    return { type: 'rectification', status: 'manual_review_required' };
  }

  async processPortabilityRequest(request) {
    return { type: 'portability', status: 'export_generated', exportId: crypto.randomUUID() };
  }

  async processRestrictionRequest(request) {
    return { type: 'restriction', status: 'processing_restricted' };
  }

  async processObjectionRequest(request) {
    return { type: 'objection', status: 'processing_stopped' };
  }

  async processOptOutRequest(request) {
    return { type: 'opt_out', status: 'opted_out' };
  }
}

module.exports = PrivacyControlManager;