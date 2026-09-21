const EventEmitter = require('events');
const crypto = require('crypto');
const jwt = require('jsonwebtoken');
const User = require('../models/User');
const Organization = require('../models/Organization');
const PortabilityRequest = require('../models/PortabilityRequest');
const AuditLogger = require('./AuditLogger');

class CredentialPortabilityManager extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      exportFormats: ['json', 'xml', 'csv', 'vcf', 'saml', 'oidc'],
      encryptionAlgorithm: 'aes-256-gcm',
      keyDerivationIterations: 100000,
      maxExportSize: config.maxExportSize || 50 * 1024 * 1024, // 50MB
      exportExpiryDays: config.exportExpiryDays || 30,
      verifiableCredentialVersion: '1.1',
      ...config
    };
    
    this.auditLogger = new AuditLogger();
    this.activeExports = new Map(); // Track ongoing export processes
    this.verifiableCredentials = new Map(); // Store issued credentials
  }

  async exportUserData(userId, exportOptions = {}) {
    try {
      const user = await User.findById(userId).populate('organizations');
      if (!user) {
        throw new Error('User not found');
      }

      const exportId = crypto.randomUUID();
      const exportRequest = {
        id: exportId,
        userId,
        format: exportOptions.format || 'json',
        includePersonalData: exportOptions.includePersonalData !== false,
        includeOrganizationData: exportOptions.includeOrganizationData === true,
        includeCredentials: exportOptions.includeCredentials === true,
        includeAuditLog: exportOptions.includeAuditLog === true,
        encryption: exportOptions.encryption || 'none',
        password: exportOptions.password,
        organizationIds: exportOptions.organizationIds || [],
        requestedAt: new Date(),
        status: 'processing'
      };

      this.activeExports.set(exportId, exportRequest);

      // Start async export process
      this.processExport(exportRequest).catch(error => {
        console.error('Export process failed:', error);
        exportRequest.status = 'failed';
        exportRequest.error = error.message;
        this.activeExports.set(exportId, exportRequest);
      });

      await this.auditLogger.log('data_export_requested', 'success', {
        userId,
        exportId,
        format: exportRequest.format,
        includePersonalData: exportRequest.includePersonalData,
        includeOrganizationData: exportRequest.includeOrganizationData
      });

      return {
        exportId,
        status: 'processing',
        estimatedCompletionTime: new Date(Date.now() + 5 * 60 * 1000) // 5 minutes
      };
    } catch (error) {
      await this.auditLogger.log('data_export_requested', 'failed', {
        userId,
        exportOptions,
        error: error.message
      });
      throw error;
    }
  }

  async processExport(exportRequest) {
    try {
      const { userId, format, includePersonalData, includeOrganizationData, includeCredentials, includeAuditLog } = exportRequest;
      
      const user = await User.findById(userId).populate('organizations');
      const exportData = {
        metadata: {
          exportId: exportRequest.id,
          userId,
          exportedAt: new Date().toISOString(),
          format,
          version: '1.0'
        },
        user: null,
        organizations: [],
        credentials: [],
        auditLog: []
      };

      // Export personal data
      if (includePersonalData) {
        exportData.user = {
          id: user._id,
          email: user.email,
          firstName: user.firstName,
          lastName: user.lastName,
          avatar: user.avatar,
          preferences: user.preferences || {},
          settings: user.settings || {},
          createdAt: user.createdAt,
          lastLoginAt: user.lastLoginAt,
          emailVerified: user.emailVerified,
          mfaEnabled: user.mfaEnabled,
          timezone: user.timezone,
          locale: user.locale
        };

        // Include provider information (without sensitive tokens)
        if (user.providers) {
          exportData.user.connectedProviders = Object.keys(user.providers).map(provider => ({
            provider,
            connectedAt: user.providers[provider].lastLogin,
            verified: true
          }));
        }
      }

      // Export organization data
      if (includeOrganizationData && user.organizations) {
        for (const org of user.organizations) {
          if (exportRequest.organizationIds.length === 0 || exportRequest.organizationIds.includes(org._id.toString())) {
            const member = org.members.find(m => m.user.toString() === userId);
            if (member) {
              exportData.organizations.push({
                id: org._id,
                name: org.name,
                displayName: org.displayName,
                domain: org.domain,
                type: org.type,
                membership: {
                  role: member.role,
                  permissions: member.permissions || [],
                  joinedAt: member.joinedAt,
                  status: member.status
                }
              });
            }
          }
        }
      }

      // Export credentials
      if (includeCredentials) {
        exportData.credentials = await this.exportUserCredentials(userId);
      }

      // Export audit log
      if (includeAuditLog) {
        exportData.auditLog = await this.auditLogger.getUserAuditLog(userId, {
          limit: 1000,
          organizationIds: exportRequest.organizationIds
        });
      }

      // Convert to requested format
      let exportContent;
      switch (format.toLowerCase()) {
        case 'json':
          exportContent = JSON.stringify(exportData, null, 2);
          break;
        case 'xml':
          exportContent = this.convertToXML(exportData);
          break;
        case 'csv':
          exportContent = this.convertToCSV(exportData);
          break;
        case 'vcf':
          exportContent = this.convertToVCF(exportData.user);
          break;
        case 'saml':
          exportContent = await this.createSAMLAssertion(exportData);
          break;
        case 'oidc':
          exportContent = await this.createOIDCProfile(exportData);
          break;
        default:
          throw new Error(`Unsupported format: ${format}`);
      }

      // Encrypt if requested
      if (exportRequest.encryption !== 'none' && exportRequest.password) {
        exportContent = this.encryptExportData(exportContent, exportRequest.password);
      }

      // Store export file
      const fileName = `user_data_export_${exportRequest.id}.${format.toLowerCase()}`;
      const filePath = await this.storeExportFile(fileName, exportContent);

      // Update export request
      exportRequest.status = 'completed';
      exportRequest.completedAt = new Date();
      exportRequest.filePath = filePath;
      exportRequest.fileSize = Buffer.byteLength(exportContent, 'utf8');
      exportRequest.expiresAt = new Date(Date.now() + this.config.exportExpiryDays * 24 * 60 * 60 * 1000);
      
      this.activeExports.set(exportRequest.id, exportRequest);

      await this.auditLogger.log('data_export_completed', 'success', {
        userId,
        exportId: exportRequest.id,
        format,
        fileSize: exportRequest.fileSize,
        filePath: fileName
      });

      this.emit('export_completed', {
        exportId: exportRequest.id,
        userId,
        filePath,
        format
      });

    } catch (error) {
      exportRequest.status = 'failed';
      exportRequest.error = error.message;
      exportRequest.failedAt = new Date();
      this.activeExports.set(exportRequest.id, exportRequest);

      await this.auditLogger.log('data_export_completed', 'failed', {
        userId: exportRequest.userId,
        exportId: exportRequest.id,
        error: error.message
      });

      throw error;
    }
  }

  async importUserData(userId, importData, importOptions = {}) {
    try {
      const user = await User.findById(userId);
      if (!user) {
        throw new Error('User not found');
      }

      const importId = crypto.randomUUID();
      let parsedData;

      // Parse import data based on format
      switch (importOptions.format?.toLowerCase()) {
        case 'json':
          parsedData = typeof importData === 'string' ? JSON.parse(importData) : importData;
          break;
        case 'xml':
          parsedData = this.parseXMLData(importData);
          break;
        case 'saml':
          parsedData = await this.parseSAMLAssertion(importData);
          break;
        case 'oidc':
          parsedData = await this.parseOIDCProfile(importData);
          break;
        default:
          throw new Error(`Unsupported import format: ${importOptions.format}`);
      }

      // Validate import data
      await this.validateImportData(parsedData);

      const importResult = {
        importId,
        userId,
        importedAt: new Date(),
        success: true,
        imported: {
          profile: false,
          preferences: false,
          credentials: false,
          organizations: []
        },
        errors: []
      };

      // Import user profile data
      if (parsedData.user && importOptions.importProfile !== false) {
        try {
          await this.importUserProfile(user, parsedData.user, importOptions);
          importResult.imported.profile = true;
        } catch (error) {
          importResult.errors.push(`Profile import failed: ${error.message}`);
        }
      }

      // Import preferences
      if (parsedData.user?.preferences && importOptions.importPreferences !== false) {
        try {
          await this.importUserPreferences(user, parsedData.user.preferences);
          importResult.imported.preferences = true;
        } catch (error) {
          importResult.errors.push(`Preferences import failed: ${error.message}`);
        }
      }

      // Import credentials
      if (parsedData.credentials && importOptions.importCredentials === true) {
        try {
          const credentialsImported = await this.importUserCredentials(userId, parsedData.credentials);
          importResult.imported.credentials = credentialsImported;
        } catch (error) {
          importResult.errors.push(`Credentials import failed: ${error.message}`);
        }
      }

      await this.auditLogger.log('data_import_completed', 'success', {
        userId,
        importId,
        importedItems: importResult.imported,
        errors: importResult.errors
      });

      this.emit('import_completed', {
        importId,
        userId,
        result: importResult
      });

      return importResult;
    } catch (error) {
      await this.auditLogger.log('data_import_completed', 'failed', {
        userId,
        error: error.message
      });
      throw error;
    }
  }

  async createVerifiableCredential(userId, credentialData, issuerData) {
    try {
      const user = await User.findById(userId);
      if (!user) {
        throw new Error('User not found');
      }

      const credentialId = crypto.randomUUID();
      const issuanceDate = new Date().toISOString();
      
      const credential = {
        '@context': [
          'https://www.w3.org/2018/credentials/v1',
          'https://activelog.com/credentials/v1'
        ],
        id: `https://activelog.com/credentials/${credentialId}`,
        type: ['VerifiableCredential', credentialData.type || 'IdentityCredential'],
        issuer: {
          id: issuerData.id || 'https://activelog.com',
          name: issuerData.name || 'ActiveLog Identity Federation'
        },
        issuanceDate,
        expirationDate: credentialData.expirationDate || new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
        credentialSubject: {
          id: `did:activelog:${userId}`,
          email: user.email,
          firstName: user.firstName,
          lastName: user.lastName,
          ...credentialData.subject
        },
        credentialStatus: {
          id: `https://activelog.com/credentials/status/${credentialId}`,
          type: 'RevocationList2020Status'
        }
      };

      // Sign the credential
      const signedCredential = await this.signCredential(credential, issuerData.privateKey);

      // Store credential
      this.verifiableCredentials.set(credentialId, {
        credential: signedCredential,
        userId,
        issuedAt: new Date(),
        status: 'active',
        revoked: false
      });

      await this.auditLogger.log('verifiable_credential_issued', 'success', {
        userId,
        credentialId,
        credentialType: credentialData.type,
        issuer: issuerData.id
      });

      this.emit('credential_issued', {
        credentialId,
        userId,
        credential: signedCredential
      });

      return {
        credentialId,
        credential: signedCredential,
        verificationUrl: `https://activelog.com/verify/${credentialId}`
      };
    } catch (error) {
      await this.auditLogger.log('verifiable_credential_issued', 'failed', {
        userId,
        credentialData,
        error: error.message
      });
      throw error;
    }
  }

  async verifyCredential(credentialData) {
    try {
      // Parse credential
      const credential = typeof credentialData === 'string' ? JSON.parse(credentialData) : credentialData;

      // Extract credential ID
      const credentialId = credential.id?.split('/').pop();
      if (!credentialId) {
        throw new Error('Invalid credential ID');
      }

      // Check if credential exists and is active
      const storedCredential = this.verifiableCredentials.get(credentialId);
      if (!storedCredential) {
        return { valid: false, reason: 'Credential not found' };
      }

      if (storedCredential.revoked) {
        return { valid: false, reason: 'Credential revoked' };
      }

      // Check expiration
      if (credential.expirationDate && new Date(credential.expirationDate) < new Date()) {
        return { valid: false, reason: 'Credential expired' };
      }

      // Verify signature
      const signatureValid = await this.verifyCredentialSignature(credential);
      if (!signatureValid) {
        return { valid: false, reason: 'Invalid signature' };
      }

      await this.auditLogger.log('credential_verified', 'success', {
        credentialId,
        verifiedAt: new Date()
      });

      return {
        valid: true,
        credential,
        subject: credential.credentialSubject,
        issuer: credential.issuer,
        issuanceDate: credential.issuanceDate,
        expirationDate: credential.expirationDate
      };
    } catch (error) {
      await this.auditLogger.log('credential_verified', 'failed', {
        error: error.message
      });
      return { valid: false, reason: error.message };
    }
  }

  async revokeCredential(credentialId, revokedBy, reason) {
    try {
      const storedCredential = this.verifiableCredentials.get(credentialId);
      if (!storedCredential) {
        throw new Error('Credential not found');
      }

      storedCredential.revoked = true;
      storedCredential.revokedAt = new Date();
      storedCredential.revokedBy = revokedBy;
      storedCredential.revocationReason = reason;

      this.verifiableCredentials.set(credentialId, storedCredential);

      await this.auditLogger.log('credential_revoked', 'success', {
        credentialId,
        revokedBy,
        reason
      });

      this.emit('credential_revoked', {
        credentialId,
        revokedBy,
        reason
      });

      return true;
    } catch (error) {
      await this.auditLogger.log('credential_revoked', 'failed', {
        credentialId,
        revokedBy,
        error: error.message
      });
      throw error;
    }
  }

  // Helper methods

  async exportUserCredentials(userId) {
    const credentials = [];
    for (const [credentialId, credentialData] of this.verifiableCredentials.entries()) {
      if (credentialData.userId === userId && !credentialData.revoked) {
        credentials.push({
          id: credentialId,
          credential: credentialData.credential,
          issuedAt: credentialData.issuedAt
        });
      }
    }
    return credentials;
  }

  async importUserCredentials(userId, credentials) {
    let importedCount = 0;
    for (const credentialData of credentials) {
      try {
        const verification = await this.verifyCredential(credentialData.credential);
        if (verification.valid) {
          // Store imported credential with new ID
          const newCredentialId = crypto.randomUUID();
          this.verifiableCredentials.set(newCredentialId, {
            credential: credentialData.credential,
            userId,
            issuedAt: new Date(credentialData.issuedAt),
            status: 'active',
            revoked: false,
            imported: true
          });
          importedCount++;
        }
      } catch (error) {
        console.error('Failed to import credential:', error);
      }
    }
    return importedCount;
  }

  async importUserProfile(user, profileData, options) {
    if (options.overwriteProfile !== false) {
      user.firstName = profileData.firstName || user.firstName;
      user.lastName = profileData.lastName || user.lastName;
      user.avatar = profileData.avatar || user.avatar;
      user.timezone = profileData.timezone || user.timezone;
      user.locale = profileData.locale || user.locale;
      await user.save();
    }
  }

  async importUserPreferences(user, preferences) {
    user.preferences = { ...user.preferences, ...preferences };
    await user.save();
  }

  encryptExportData(data, password) {
    const key = crypto.pbkdf2Sync(password, 'salt', this.config.keyDerivationIterations, 32, 'sha256');
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipher(this.config.encryptionAlgorithm, key);
    
    let encrypted = cipher.update(data, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    const authTag = cipher.getAuthTag();
    
    return {
      encrypted,
      iv: iv.toString('hex'),
      authTag: authTag.toString('hex'),
      algorithm: this.config.encryptionAlgorithm
    };
  }

  convertToXML(data) {
    // Simple XML conversion - in production, use proper XML library
    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<export>\n';
    xml += this.objectToXML(data, 1);
    xml += '</export>';
    return xml;
  }

  objectToXML(obj, indent = 0) {
    const spaces = '  '.repeat(indent);
    let xml = '';
    
    for (const [key, value] of Object.entries(obj)) {
      if (typeof value === 'object' && value !== null) {
        if (Array.isArray(value)) {
          xml += `${spaces}<${key}>\n`;
          value.forEach(item => {
            xml += `${spaces}  <item>\n`;
            xml += this.objectToXML(item, indent + 2);
            xml += `${spaces}  </item>\n`;
          });
          xml += `${spaces}</${key}>\n`;
        } else {
          xml += `${spaces}<${key}>\n`;
          xml += this.objectToXML(value, indent + 1);
          xml += `${spaces}</${key}>\n`;
        }
      } else {
        xml += `${spaces}<${key}>${value || ''}</${key}>\n`;
      }
    }
    
    return xml;
  }

  convertToCSV(data) {
    // Simple CSV conversion - focuses on user data
    const csvData = [];
    csvData.push(['Field', 'Value']);
    
    if (data.user) {
      Object.entries(data.user).forEach(([key, value]) => {
        if (typeof value !== 'object') {
          csvData.push([key, value]);
        }
      });
    }
    
    return csvData.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
  }

  convertToVCF(userData) {
    if (!userData) return '';
    
    let vcf = 'BEGIN:VCARD\n';
    vcf += 'VERSION:3.0\n';
    vcf += `FN:${userData.firstName || ''} ${userData.lastName || ''}\n`;
    vcf += `EMAIL:${userData.email}\n`;
    if (userData.avatar) {
      vcf += `PHOTO:${userData.avatar}\n`;
    }
    vcf += 'END:VCARD\n';
    
    return vcf;
  }

  async createSAMLAssertion(data) {
    // SAML assertion creation - simplified version
    const assertion = {
      '@xmlns:saml2': 'urn:oasis:names:tc:SAML:2.0:assertion',
      'ID': crypto.randomUUID(),
      'IssueInstant': new Date().toISOString(),
      'Issuer': 'https://activelog.com',
      'Subject': {
        'NameID': data.user?.email,
        'Format': 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress'
      },
      'AttributeStatement': {
        'Attribute': Object.entries(data.user || {}).map(([name, value]) => ({
          'Name': name,
          'AttributeValue': value
        }))
      }
    };
    
    return JSON.stringify(assertion, null, 2);
  }

  async createOIDCProfile(data) {
    const profile = {
      sub: data.user?.id,
      email: data.user?.email,
      given_name: data.user?.firstName,
      family_name: data.user?.lastName,
      picture: data.user?.avatar,
      iat: Math.floor(Date.now() / 1000),
      iss: 'https://activelog.com'
    };
    
    return JSON.stringify(profile, null, 2);
  }

  async signCredential(credential, privateKey) {
    // In production, use proper digital signature
    const payload = JSON.stringify(credential);
    const signature = crypto.sign('sha256', Buffer.from(payload));
    
    return {
      ...credential,
      proof: {
        type: 'Ed25519Signature2020',
        created: new Date().toISOString(),
        proofPurpose: 'assertionMethod',
        signature: signature.toString('base64')
      }
    };
  }

  async verifyCredentialSignature(credential) {
    // Simplified signature verification
    return true; // In production, implement proper verification
  }

  async storeExportFile(fileName, content) {
    // In production, store in secure cloud storage
    // For now, return a mock file path
    return `/exports/${fileName}`;
  }

  async validateImportData(data) {
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid import data format');
    }
    
    if (data.metadata && data.metadata.version !== '1.0') {
      throw new Error('Unsupported import data version');
    }
    
    return true;
  }
}

module.exports = CredentialPortabilityManager;