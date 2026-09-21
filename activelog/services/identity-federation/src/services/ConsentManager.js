const EventEmitter = require('events');
const crypto = require('crypto');
const User = require('../models/User');
const Organization = require('../models/Organization');
const ConsentRecord = require('../models/ConsentRecord');
const ConsentTemplate = require('../models/ConsentTemplate');
const AuditLogger = require('./AuditLogger');

class ConsentManager extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      defaultConsentExpiry: config.defaultConsentExpiry || 365, // days
      reminderDaysBeforeExpiry: config.reminderDaysBeforeExpiry || 30,
      requireExplicitConsent: config.requireExplicitConsent !== false,
      allowImpliedConsent: config.allowImpliedConsent === true,
      granularConsent: config.granularConsent !== false,
      consentWithdrawalGracePeriod: config.consentWithdrawalGracePeriod || 24, // hours
      minAge: config.minAge || 13,
      parentalConsentAge: config.parentalConsentAge || 16,
      ...config
    };
    
    this.auditLogger = new AuditLogger();
    this.consentTypes = {
      'data_processing': 'Data Processing',
      'marketing_communications': 'Marketing Communications',
      'analytics': 'Analytics and Performance',
      'personalization': 'Personalization',
      'third_party_sharing': 'Third Party Data Sharing',
      'cookies': 'Cookie Usage',
      'location_tracking': 'Location Tracking',
      'biometric_data': 'Biometric Data Processing',
      'automated_decision_making': 'Automated Decision Making',
      'research': 'Research and Development'
    };
    
    this.consentMechanisms = {
      'opt_in': 'Explicit Opt-in',
      'opt_out': 'Opt-out',
      'implied': 'Implied Consent',
      'granular': 'Granular Consent',
      'dynamic': 'Dynamic Consent'
    };
    
    this.initializeDefaultTemplates();
  }

  async initializeDefaultTemplates() {
    const defaultTemplates = [
      {
        type: 'data_processing',
        name: 'Essential Data Processing',
        description: 'Processing of personal data necessary for service functionality',
        purpose: 'Service provision and account management',
        legalBasis: 'contract',
        required: true,
        canWithdraw: false,
        dataCategories: ['personal_info', 'contact_info', 'technical_info'],
        retentionPeriod: 365,
        template: {
          title: 'Essential Data Processing',
          content: 'We process your personal data to provide our services and manage your account.',
          language: 'en',
          version: '1.0'
        }
      },
      {
        type: 'marketing_communications',
        name: 'Marketing Communications',
        description: 'Sending marketing emails and promotional content',
        purpose: 'Marketing and promotional communications',
        legalBasis: 'consent',
        required: false,
        canWithdraw: true,
        dataCategories: ['contact_info', 'preferences', 'behavioral_info'],
        retentionPeriod: 730,
        template: {
          title: 'Marketing Communications',
          content: 'We would like to send you information about our products, services, and special offers.',
          language: 'en',
          version: '1.0'
        }
      },
      {
        type: 'analytics',
        name: 'Analytics and Performance',
        description: 'Collecting data to improve our services and user experience',
        purpose: 'Service improvement and analytics',
        legalBasis: 'legitimate_interests',
        required: false,
        canWithdraw: true,
        dataCategories: ['technical_info', 'behavioral_info'],
        retentionPeriod: 90,
        template: {
          title: 'Analytics and Performance',
          content: 'We collect usage data to understand how you use our service and improve your experience.',
          language: 'en',
          version: '1.0'
        }
      }
    ];

    for (const templateData of defaultTemplates) {
      try {
        await ConsentTemplate.findOneAndUpdate(
          { type: templateData.type, isDefault: true },
          { ...templateData, isDefault: true, createdAt: new Date() },
          { upsert: true, new: true }
        );
      } catch (error) {
        console.error(`Error creating default consent template ${templateData.type}:`, error);
      }
    }
  }

  async requestConsent(userId, consentRequest, context = {}) {
    try {
      const user = await User.findById(userId);
      if (!user) {
        throw new Error('User not found');
      }

      // Check age requirements
      const ageCheck = await this.checkAgeRequirements(user, consentRequest.type);
      if (!ageCheck.canConsent) {
        return {
          canConsent: false,
          reason: ageCheck.reason,
          requiresParentalConsent: ageCheck.requiresParentalConsent
        };
      }

      const consentId = crypto.randomUUID();
      const template = await ConsentTemplate.findOne({
        type: consentRequest.type,
        isActive: true
      }) || await ConsentTemplate.findOne({
        type: consentRequest.type,
        isDefault: true
      });

      if (!template) {
        throw new Error(`No consent template found for type: ${consentRequest.type}`);
      }

      const consent = new ConsentRecord({
        consentId,
        userId,
        organizationId: consentRequest.organizationId,
        type: consentRequest.type,
        status: 'requested',
        templateId: template._id,
        purpose: consentRequest.purpose || template.purpose,
        legalBasis: template.legalBasis,
        dataCategories: consentRequest.dataCategories || template.dataCategories,
        retentionPeriod: consentRequest.retentionPeriod || template.retentionPeriod,
        mechanism: consentRequest.mechanism || 'opt_in',
        required: template.required,
        canWithdraw: template.canWithdraw,
        requestedAt: new Date(),
        expiresAt: consentRequest.expiresAt || new Date(Date.now() + this.config.defaultConsentExpiry * 24 * 60 * 60 * 1000),
        context: {
          ipAddress: context.ipAddress,
          userAgent: context.userAgent,
          source: context.source,
          referrer: context.referrer
        },
        metadata: consentRequest.metadata || {}
      });

      await consent.save();

      await this.auditLogger.log('consent_requested', 'success', {
        userId,
        consentId,
        type: consentRequest.type,
        organizationId: consentRequest.organizationId,
        context
      });

      this.emit('consent_requested', {
        userId,
        consent,
        template
      });

      return {
        consentId,
        template: template.template,
        mechanism: consent.mechanism,
        required: consent.required,
        canWithdraw: consent.canWithdraw,
        expiresAt: consent.expiresAt
      };
    } catch (error) {
      await this.auditLogger.log('consent_requested', 'failed', {
        userId,
        consentRequest,
        error: error.message
      });
      throw error;
    }
  }

  async grantConsent(userId, consentId, consentData = {}, context = {}) {
    try {
      const consent = await ConsentRecord.findOne({ consentId, userId });
      if (!consent) {
        throw new Error('Consent record not found');
      }

      if (consent.status !== 'requested') {
        throw new Error(`Cannot grant consent with status: ${consent.status}`);
      }

      // Validate consent data for granular consent
      if (consent.mechanism === 'granular' && consentData.granularChoices) {
        await this.validateGranularConsent(consent, consentData.granularChoices);
      }

      consent.status = 'granted';
      consent.grantedAt = new Date();
      consent.consentEvidence = {
        method: consentData.method || 'explicit',
        timestamp: new Date(),
        ipAddress: context.ipAddress,
        userAgent: context.userAgent,
        evidence: consentData.evidence,
        granularChoices: consentData.granularChoices
      };
      consent.version = consentData.version || '1.0';

      // Set expiry if not already set
      if (!consent.expiresAt) {
        consent.expiresAt = new Date(Date.now() + this.config.defaultConsentExpiry * 24 * 60 * 60 * 1000);
      }

      await consent.save();

      // Update user's consent preferences
      await this.updateUserConsentPreferences(userId, consent);

      // Schedule expiry reminder
      await this.scheduleExpiryReminder(consent);

      await this.auditLogger.log('consent_granted', 'success', {
        userId,
        consentId,
        type: consent.type,
        method: consentData.method,
        context
      });

      this.emit('consent_granted', {
        userId,
        consent,
        context
      });

      return {
        consentId,
        status: 'granted',
        grantedAt: consent.grantedAt,
        expiresAt: consent.expiresAt
      };
    } catch (error) {
      await this.auditLogger.log('consent_granted', 'failed', {
        userId,
        consentId,
        error: error.message
      });
      throw error;
    }
  }

  async withdrawConsent(userId, consentId, withdrawalData = {}, context = {}) {
    try {
      const consent = await ConsentRecord.findOne({ consentId, userId });
      if (!consent) {
        throw new Error('Consent record not found');
      }

      if (!consent.canWithdraw) {
        throw new Error('This consent cannot be withdrawn');
      }

      if (consent.status !== 'granted') {
        throw new Error(`Cannot withdraw consent with status: ${consent.status}`);
      }

      // Grace period check
      const gracePeriodEnd = new Date(consent.grantedAt.getTime() + this.config.consentWithdrawalGracePeriod * 60 * 60 * 1000);
      const isInGracePeriod = new Date() <= gracePeriodEnd;

      consent.status = 'withdrawn';
      consent.withdrawnAt = new Date();
      consent.withdrawalReason = withdrawalData.reason;
      consent.withdrawalEvidence = {
        method: withdrawalData.method || 'explicit',
        timestamp: new Date(),
        ipAddress: context.ipAddress,
        userAgent: context.userAgent,
        reason: withdrawalData.reason,
        gracePeriod: isInGracePeriod
      };

      await consent.save();

      // Update user's consent preferences
      await this.updateUserConsentPreferences(userId, consent);

      // Trigger data cleanup if necessary
      if (!isInGracePeriod) {
        await this.handleConsentWithdrawal(consent);
      } else {
        // Schedule cleanup after grace period
        setTimeout(async () => {
          await this.handleConsentWithdrawal(consent);
        }, this.config.consentWithdrawalGracePeriod * 60 * 60 * 1000);
      }

      await this.auditLogger.log('consent_withdrawn', 'success', {
        userId,
        consentId,
        type: consent.type,
        reason: withdrawalData.reason,
        gracePeriod: isInGracePeriod,
        context
      });

      this.emit('consent_withdrawn', {
        userId,
        consent,
        gracePeriod: isInGracePeriod,
        context
      });

      return {
        consentId,
        status: 'withdrawn',
        withdrawnAt: consent.withdrawnAt,
        gracePeriod: isInGracePeriod,
        cleanupScheduled: !isInGracePeriod
      };
    } catch (error) {
      await this.auditLogger.log('consent_withdrawn', 'failed', {
        userId,
        consentId,
        error: error.message
      });
      throw error;
    }
  }

  async checkConsent(userId, consentType, organizationId = null) {
    try {
      const query = {
        userId,
        type: consentType,
        status: 'granted'
      };

      if (organizationId) {
        query.organizationId = organizationId;
      }

      const consent = await ConsentRecord.findOne(query)
        .sort({ grantedAt: -1 });

      if (!consent) {
        return {
          hasConsent: false,
          reason: 'no_consent_found'
        };
      }

      // Check if consent has expired
      if (consent.expiresAt && consent.expiresAt < new Date()) {
        consent.status = 'expired';
        consent.expiredAt = new Date();
        await consent.save();

        return {
          hasConsent: false,
          reason: 'consent_expired',
          expiredAt: consent.expiredAt
        };
      }

      return {
        hasConsent: true,
        consent: {
          consentId: consent.consentId,
          type: consent.type,
          grantedAt: consent.grantedAt,
          expiresAt: consent.expiresAt,
          purpose: consent.purpose,
          legalBasis: consent.legalBasis
        }
      };
    } catch (error) {
      await this.auditLogger.log('consent_check', 'failed', {
        userId,
        consentType,
        organizationId,
        error: error.message
      });
      throw error;
    }
  }

  async getUserConsents(userId, filters = {}) {
    try {
      const query = { userId };
      
      if (filters.organizationId) {
        query.organizationId = filters.organizationId;
      }
      
      if (filters.type) {
        query.type = filters.type;
      }
      
      if (filters.status) {
        query.status = filters.status;
      }

      const consents = await ConsentRecord.find(query)
        .populate('templateId')
        .sort({ grantedAt: -1, requestedAt: -1 });

      const processedConsents = consents.map(consent => ({
        consentId: consent.consentId,
        type: consent.type,
        status: consent.status,
        purpose: consent.purpose,
        legalBasis: consent.legalBasis,
        required: consent.required,
        canWithdraw: consent.canWithdraw,
        requestedAt: consent.requestedAt,
        grantedAt: consent.grantedAt,
        withdrawnAt: consent.withdrawnAt,
        expiresAt: consent.expiresAt,
        dataCategories: consent.dataCategories,
        mechanism: consent.mechanism,
        template: consent.templateId?.template
      }));

      return {
        consents: processedConsents,
        summary: this.generateConsentSummary(processedConsents)
      };
    } catch (error) {
      await this.auditLogger.log('get_user_consents', 'failed', {
        userId,
        filters,
        error: error.message
      });
      throw error;
    }
  }

  async updateConsentTemplate(templateId, templateData, updatedBy) {
    try {
      const template = await ConsentTemplate.findById(templateId);
      if (!template) {
        throw new Error('Template not found');
      }

      // Create new version
      template.version = (parseFloat(template.version) + 0.1).toFixed(1);
      template.template = { ...template.template, ...templateData.template };
      template.description = templateData.description || template.description;
      template.purpose = templateData.purpose || template.purpose;
      template.dataCategories = templateData.dataCategories || template.dataCategories;
      template.retentionPeriod = templateData.retentionPeriod || template.retentionPeriod;
      template.updatedAt = new Date();
      template.updatedBy = updatedBy;

      await template.save();

      // Mark existing active consents for re-consent if significant changes
      if (templateData.requiresReConsent) {
        await this.markConsentsForReConsent(template._id, template.version);
      }

      await this.auditLogger.log('consent_template_updated', 'success', {
        templateId,
        type: template.type,
        version: template.version,
        updatedBy,
        requiresReConsent: templateData.requiresReConsent
      });

      this.emit('consent_template_updated', {
        template,
        requiresReConsent: templateData.requiresReConsent
      });

      return template;
    } catch (error) {
      await this.auditLogger.log('consent_template_updated', 'failed', {
        templateId,
        error: error.message
      });
      throw error;
    }
  }

  async createDynamicConsent(userId, consentData, context = {}) {
    try {
      const user = await User.findById(userId);
      if (!user) {
        throw new Error('User not found');
      }

      const consentId = crypto.randomUUID();
      const consent = new ConsentRecord({
        consentId,
        userId,
        organizationId: consentData.organizationId,
        type: 'dynamic',
        status: 'active',
        purpose: consentData.purpose,
        legalBasis: consentData.legalBasis || 'consent',
        dataCategories: consentData.dataCategories,
        mechanism: 'dynamic',
        dynamicRules: consentData.rules,
        conditions: consentData.conditions,
        triggers: consentData.triggers,
        grantedAt: new Date(),
        context: {
          ipAddress: context.ipAddress,
          userAgent: context.userAgent,
          source: context.source
        }
      });

      await consent.save();

      // Set up dynamic consent monitoring
      await this.setupDynamicConsentMonitoring(consent);

      await this.auditLogger.log('dynamic_consent_created', 'success', {
        userId,
        consentId,
        purpose: consentData.purpose,
        rules: consentData.rules
      });

      this.emit('dynamic_consent_created', {
        userId,
        consent
      });

      return {
        consentId,
        status: 'active',
        rules: consent.dynamicRules,
        conditions: consent.conditions
      };
    } catch (error) {
      await this.auditLogger.log('dynamic_consent_created', 'failed', {
        userId,
        error: error.message
      });
      throw error;
    }
  }

  // Helper methods

  async checkAgeRequirements(user, consentType) {
    // Simplified age check - in production, would need proper age verification
    const userAge = this.calculateAge(user.dateOfBirth);
    
    if (userAge < this.config.minAge) {
      return {
        canConsent: false,
        reason: 'below_minimum_age',
        requiresParentalConsent: true
      };
    }

    if (userAge < this.config.parentalConsentAge && ['biometric_data', 'location_tracking'].includes(consentType)) {
      return {
        canConsent: false,
        reason: 'requires_parental_consent',
        requiresParentalConsent: true
      };
    }

    return { canConsent: true };
  }

  calculateAge(dateOfBirth) {
    if (!dateOfBirth) return 18; // Default to adult age if no birth date
    
    const today = new Date();
    const birth = new Date(dateOfBirth);
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    
    return age;
  }

  async validateGranularConsent(consent, granularChoices) {
    // Validate that all required choices are present
    const requiredCategories = consent.dataCategories.filter(cat => 
      consent.metadata?.requiredCategories?.includes(cat)
    );

    for (const category of requiredCategories) {
      if (!granularChoices[category] || granularChoices[category] !== true) {
        throw new Error(`Consent required for data category: ${category}`);
      }
    }
  }

  async updateUserConsentPreferences(userId, consent) {
    const user = await User.findById(userId);
    if (!user.consentPreferences) {
      user.consentPreferences = {};
    }

    user.consentPreferences[consent.type] = {
      status: consent.status,
      grantedAt: consent.grantedAt,
      withdrawnAt: consent.withdrawnAt,
      lastUpdated: new Date()
    };

    await user.save();
  }

  async scheduleExpiryReminder(consent) {
    const reminderDate = new Date(consent.expiresAt.getTime() - this.config.reminderDaysBeforeExpiry * 24 * 60 * 60 * 1000);
    
    if (reminderDate > new Date()) {
      // In production, use a job queue
      setTimeout(async () => {
        await this.sendExpiryReminder(consent);
      }, reminderDate.getTime() - Date.now());
    }
  }

  async sendExpiryReminder(consent) {
    this.emit('consent_expiry_reminder', {
      userId: consent.userId,
      consentId: consent.consentId,
      type: consent.type,
      expiresAt: consent.expiresAt
    });
  }

  async handleConsentWithdrawal(consent) {
    // Clean up data based on withdrawn consent
    this.emit('consent_data_cleanup', {
      userId: consent.userId,
      consentType: consent.type,
      dataCategories: consent.dataCategories
    });
  }

  async markConsentsForReConsent(templateId, newVersion) {
    await ConsentRecord.updateMany(
      { templateId, status: 'granted' },
      {
        requiresReConsent: true,
        newTemplateVersion: newVersion,
        reConsentRequiredAt: new Date()
      }
    );
  }

  async setupDynamicConsentMonitoring(consent) {
    // Set up monitoring for dynamic consent conditions
    this.emit('dynamic_consent_monitor_setup', {
      consentId: consent.consentId,
      conditions: consent.conditions,
      triggers: consent.triggers
    });
  }

  generateConsentSummary(consents) {
    const summary = {
      total: consents.length,
      granted: 0,
      withdrawn: 0,
      expired: 0,
      pending: 0,
      byType: {},
      expiringSoon: 0
    };

    const thirtyDaysFromNow = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);

    consents.forEach(consent => {
      summary[consent.status]++;
      
      if (!summary.byType[consent.type]) {
        summary.byType[consent.type] = 0;
      }
      summary.byType[consent.type]++;

      if (consent.expiresAt && new Date(consent.expiresAt) <= thirtyDaysFromNow) {
        summary.expiringSoon++;
      }
    });

    return summary;
  }
}

module.exports = ConsentManager;