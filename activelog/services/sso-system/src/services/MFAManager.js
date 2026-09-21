const speakeasy = require('speakeasy');
const QRCode = require('qrcode');
const crypto = require('crypto');
const { EventEmitter } = require('events');

class MFAManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      issuer: options.issuer || 'ActiveLog SSO',
      totpWindow: options.totpWindow || 2,
      backupCodesCount: options.backupCodesCount || 10,
      smsCodeLength: options.smsCodeLength || 6,
      emailCodeLength: options.emailCodeLength || 6,
      codeExpiration: options.codeExpiration || 300000, // 5 minutes
      maxAttempts: options.maxAttempts || 5,
      lockoutDuration: options.lockoutDuration || 900000, // 15 minutes
      enableWebAuthn: options.enableWebAuthn !== false,
      enableSMS: options.enableSMS !== false,
      enableEmail: options.enableEmail !== false,
      ...options
    };
    
    this.userMFASettings = new Map();
    this.pendingCodes = new Map();
    this.failedAttempts = new Map();
    this.backupCodes = new Map();
    this.webAuthnCredentials = new Map();
    
    this.setupCleanupInterval();
  }

  // TOTP (Time-based One-Time Password) Management
  async setupTOTP(userId, options = {}) {
    const userSettings = this.getUserMFASettings(userId);
    
    if (userSettings.totp && userSettings.totp.enabled) {
      throw new Error('TOTP is already enabled for this user');
    }
    
    const secret = speakeasy.generateSecret({
      name: options.accountName || `ActiveLog:${userId}`,
      issuer: this.options.issuer,
      length: 32
    });
    
    const totpSetup = {
      secret: secret.base32,
      qrCodeUrl: secret.otpauth_url,
      backupUrl: secret.otpauth_url,
      enabled: false,
      setupAt: new Date(),
      confirmed: false
    };
    
    userSettings.totp = totpSetup;
    this.userMFASettings.set(userId, userSettings);
    
    // Generate QR code
    const qrCodeData = await QRCode.toDataURL(secret.otpauth_url);
    
    this.emit('totpSetupInitiated', { userId, qrCodeUrl: secret.otpauth_url });
    
    return {
      secret: secret.base32,
      qrCode: qrCodeData,
      manualEntryKey: secret.base32,
      backupUrl: secret.otpauth_url
    };
  }

  async verifyTOTPSetup(userId, token) {
    const userSettings = this.getUserMFASettings(userId);
    
    if (!userSettings.totp || userSettings.totp.confirmed) {
      throw new Error('TOTP setup not found or already confirmed');
    }
    
    const verified = speakeasy.totp.verify({
      secret: userSettings.totp.secret,
      encoding: 'base32',
      token,
      window: this.options.totpWindow
    });
    
    if (!verified) {
      this.recordFailedAttempt(userId, 'totp_setup');
      throw new Error('Invalid TOTP code');
    }
    
    // Enable TOTP and generate backup codes
    userSettings.totp.enabled = true;
    userSettings.totp.confirmed = true;
    userSettings.totp.confirmedAt = new Date();
    
    const backupCodes = this.generateBackupCodes(userId);
    
    userSettings.mfaEnabled = true;
    userSettings.enabledMethods.add('totp');
    userSettings.updatedAt = new Date();
    
    this.userMFASettings.set(userId, userSettings);
    
    this.emit('totpEnabled', { userId, backupCodesGenerated: backupCodes.length });
    
    return {
      success: true,
      backupCodes
    };
  }

  async verifyTOTP(userId, token) {
    const userSettings = this.getUserMFASettings(userId);
    
    if (!userSettings.totp || !userSettings.totp.enabled) {
      throw new Error('TOTP is not enabled for this user');
    }
    
    if (this.isUserLockedOut(userId)) {
      const lockout = this.failedAttempts.get(userId);
      throw new Error(`Account locked due to too many failed attempts. Try again after ${new Date(lockout.lockedUntil)}`);
    }
    
    const verified = speakeasy.totp.verify({
      secret: userSettings.totp.secret,
      encoding: 'base32',
      token,
      window: this.options.totpWindow
    });
    
    if (!verified) {
      this.recordFailedAttempt(userId, 'totp');
      throw new Error('Invalid TOTP code');
    }
    
    this.clearFailedAttempts(userId);
    userSettings.totp.lastUsedAt = new Date();
    this.userMFASettings.set(userId, userSettings);
    
    this.emit('totpVerified', { userId, timestamp: new Date() });
    
    return { success: true, method: 'totp' };
  }

  async disableTOTP(userId) {
    const userSettings = this.getUserMFASettings(userId);
    
    if (!userSettings.totp || !userSettings.totp.enabled) {
      throw new Error('TOTP is not enabled for this user');
    }
    
    userSettings.totp.enabled = false;
    userSettings.totp.disabledAt = new Date();
    userSettings.enabledMethods.delete('totp');
    
    // Check if MFA should be disabled entirely
    if (userSettings.enabledMethods.size === 0) {
      userSettings.mfaEnabled = false;
    }
    
    this.userMFASettings.set(userId, userSettings);
    
    this.emit('totpDisabled', { userId });
    
    return { success: true };
  }

  // SMS MFA
  async setupSMS(userId, phoneNumber) {
    if (!this.options.enableSMS) {
      throw new Error('SMS MFA is not enabled');
    }
    
    const userSettings = this.getUserMFASettings(userId);
    
    userSettings.sms = {
      phoneNumber,
      enabled: true,
      setupAt: new Date(),
      verified: false
    };
    
    // Send verification code
    const verificationCode = await this.sendSMSVerificationCode(userId, phoneNumber);
    
    userSettings.sms.pendingVerification = true;
    this.userMFASettings.set(userId, userSettings);
    
    this.emit('smsSetupInitiated', { userId, phoneNumber });
    
    return {
      success: true,
      message: 'Verification code sent to phone number',
      maskedPhone: this.maskPhoneNumber(phoneNumber)
    };
  }

  async verifySMSSetup(userId, code) {
    const userSettings = this.getUserMFASettings(userId);
    
    if (!userSettings.sms || !userSettings.sms.pendingVerification) {
      throw new Error('SMS setup not found or not pending verification');
    }
    
    const verified = await this.verifySMSCode(userId, code);
    
    if (!verified) {
      throw new Error('Invalid SMS code');
    }
    
    userSettings.sms.verified = true;
    userSettings.sms.verifiedAt = new Date();
    userSettings.sms.pendingVerification = false;
    userSettings.mfaEnabled = true;
    userSettings.enabledMethods.add('sms');
    
    this.userMFASettings.set(userId, userSettings);
    
    this.emit('smsEnabled', { userId, phoneNumber: userSettings.sms.phoneNumber });
    
    return { success: true };
  }

  async sendSMSCode(userId) {
    const userSettings = this.getUserMFASettings(userId);
    
    if (!userSettings.sms || !userSettings.sms.enabled || !userSettings.sms.verified) {
      throw new Error('SMS MFA is not enabled for this user');
    }
    
    const code = this.generateSMSCode();
    const expiresAt = new Date(Date.now() + this.options.codeExpiration);
    
    this.pendingCodes.set(`sms:${userId}`, {
      code,
      expiresAt,
      method: 'sms',
      attempts: 0
    });
    
    // In a real implementation, you would integrate with an SMS service
    await this.sendSMSMessage(userSettings.sms.phoneNumber, `Your ActiveLog verification code is: ${code}`);
    
    this.emit('smsCodeSent', { userId, phoneNumber: userSettings.sms.phoneNumber });
    
    return {
      success: true,
      message: 'SMS code sent',
      expiresIn: this.options.codeExpiration / 1000
    };
  }

  async verifySMSCode(userId, code) {
    const pendingCode = this.pendingCodes.get(`sms:${userId}`);
    
    if (!pendingCode) {
      return false;
    }
    
    if (pendingCode.expiresAt < new Date()) {
      this.pendingCodes.delete(`sms:${userId}`);
      return false;
    }
    
    if (pendingCode.code !== code) {
      pendingCode.attempts++;
      if (pendingCode.attempts >= this.options.maxAttempts) {
        this.pendingCodes.delete(`sms:${userId}`);
        this.recordFailedAttempt(userId, 'sms');
      }
      return false;
    }
    
    this.pendingCodes.delete(`sms:${userId}`);
    this.clearFailedAttempts(userId);
    
    const userSettings = this.getUserMFASettings(userId);
    if (userSettings.sms) {
      userSettings.sms.lastUsedAt = new Date();
      this.userMFASettings.set(userId, userSettings);
    }
    
    this.emit('smsCodeVerified', { userId });
    
    return true;
  }

  // Email MFA
  async setupEmail(userId, email) {
    if (!this.options.enableEmail) {
      throw new Error('Email MFA is not enabled');
    }
    
    const userSettings = this.getUserMFASettings(userId);
    
    userSettings.email = {
      email,
      enabled: true,
      setupAt: new Date(),
      verified: false
    };
    
    const verificationCode = await this.sendEmailVerificationCode(userId, email);
    
    userSettings.email.pendingVerification = true;
    this.userMFASettings.set(userId, userSettings);
    
    this.emit('emailSetupInitiated', { userId, email });
    
    return {
      success: true,
      message: 'Verification code sent to email address',
      maskedEmail: this.maskEmail(email)
    };
  }

  async verifyEmailSetup(userId, code) {
    const userSettings = this.getUserMFASettings(userId);
    
    if (!userSettings.email || !userSettings.email.pendingVerification) {
      throw new Error('Email setup not found or not pending verification');
    }
    
    const verified = await this.verifyEmailCode(userId, code);
    
    if (!verified) {
      throw new Error('Invalid email code');
    }
    
    userSettings.email.verified = true;
    userSettings.email.verifiedAt = new Date();
    userSettings.email.pendingVerification = false;
    userSettings.mfaEnabled = true;
    userSettings.enabledMethods.add('email');
    
    this.userMFASettings.set(userId, userSettings);
    
    this.emit('emailEnabled', { userId, email: userSettings.email.email });
    
    return { success: true };
  }

  async sendEmailCode(userId) {
    const userSettings = this.getUserMFASettings(userId);
    
    if (!userSettings.email || !userSettings.email.enabled || !userSettings.email.verified) {
      throw new Error('Email MFA is not enabled for this user');
    }
    
    const code = this.generateEmailCode();
    const expiresAt = new Date(Date.now() + this.options.codeExpiration);
    
    this.pendingCodes.set(`email:${userId}`, {
      code,
      expiresAt,
      method: 'email',
      attempts: 0
    });
    
    await this.sendEmailMessage(userSettings.email.email, 'ActiveLog Verification Code', 
      `Your verification code is: ${code}. This code expires in 5 minutes.`);
    
    this.emit('emailCodeSent', { userId, email: userSettings.email.email });
    
    return {
      success: true,
      message: 'Email code sent',
      expiresIn: this.options.codeExpiration / 1000
    };
  }

  async verifyEmailCode(userId, code) {
    const pendingCode = this.pendingCodes.get(`email:${userId}`);
    
    if (!pendingCode) {
      return false;
    }
    
    if (pendingCode.expiresAt < new Date()) {
      this.pendingCodes.delete(`email:${userId}`);
      return false;
    }
    
    if (pendingCode.code !== code) {
      pendingCode.attempts++;
      if (pendingCode.attempts >= this.options.maxAttempts) {
        this.pendingCodes.delete(`email:${userId}`);
        this.recordFailedAttempt(userId, 'email');
      }
      return false;
    }
    
    this.pendingCodes.delete(`email:${userId}`);
    this.clearFailedAttempts(userId);
    
    const userSettings = this.getUserMFASettings(userId);
    if (userSettings.email) {
      userSettings.email.lastUsedAt = new Date();
      this.userMFASettings.set(userId, userSettings);
    }
    
    this.emit('emailCodeVerified', { userId });
    
    return true;
  }

  // WebAuthn Support
  async setupWebAuthn(userId, credentialData) {
    if (!this.options.enableWebAuthn) {
      throw new Error('WebAuthn is not enabled');
    }
    
    const userSettings = this.getUserMFASettings(userId);
    
    const credentialId = this.generateCredentialId();
    const credential = {
      id: credentialId,
      credentialId: credentialData.credentialId,
      publicKey: credentialData.publicKey,
      counter: credentialData.counter || 0,
      name: credentialData.name || 'Security Key',
      createdAt: new Date(),
      lastUsedAt: null
    };
    
    if (!userSettings.webauthn) {
      userSettings.webauthn = {
        enabled: true,
        credentials: []
      };
    }
    
    userSettings.webauthn.credentials.push(credential);
    userSettings.mfaEnabled = true;
    userSettings.enabledMethods.add('webauthn');
    
    this.userMFASettings.set(userId, userSettings);
    this.webAuthnCredentials.set(credentialId, { userId, ...credential });
    
    this.emit('webAuthnCredentialAdded', { userId, credentialId, name: credential.name });
    
    return {
      success: true,
      credentialId,
      name: credential.name
    };
  }

  async verifyWebAuthn(userId, credentialId, signature, challengeData) {
    const userSettings = this.getUserMFASettings(userId);
    
    if (!userSettings.webauthn || !userSettings.webauthn.enabled) {
      throw new Error('WebAuthn is not enabled for this user');
    }
    
    const credential = userSettings.webauthn.credentials.find(c => c.id === credentialId);
    if (!credential) {
      throw new Error('Credential not found');
    }
    
    // In a real implementation, you would verify the WebAuthn signature
    const verified = await this.verifyWebAuthnSignature(credential, signature, challengeData);
    
    if (!verified) {
      this.recordFailedAttempt(userId, 'webauthn');
      throw new Error('WebAuthn verification failed');
    }
    
    // Update counter and last used time
    credential.counter++;
    credential.lastUsedAt = new Date();
    this.userMFASettings.set(userId, userSettings);
    
    this.clearFailedAttempts(userId);
    
    this.emit('webAuthnVerified', { userId, credentialId });
    
    return { success: true, method: 'webauthn' };
  }

  // Backup Codes
  generateBackupCodes(userId) {
    const codes = [];
    
    for (let i = 0; i < this.options.backupCodesCount; i++) {
      codes.push(this.generateBackupCode());
    }
    
    this.backupCodes.set(userId, {
      codes: new Set(codes),
      createdAt: new Date(),
      usedCodes: new Set()
    });
    
    return codes;
  }

  async verifyBackupCode(userId, code) {
    const backupData = this.backupCodes.get(userId);
    
    if (!backupData) {
      throw new Error('No backup codes found for user');
    }
    
    if (!backupData.codes.has(code)) {
      this.recordFailedAttempt(userId, 'backup_code');
      throw new Error('Invalid backup code');
    }
    
    // Use the backup code (single use)
    backupData.codes.delete(code);
    backupData.usedCodes.add(code);
    backupData.lastUsedAt = new Date();
    
    this.backupCodes.set(userId, backupData);
    this.clearFailedAttempts(userId);
    
    this.emit('backupCodeUsed', { 
      userId, 
      remainingCodes: backupData.codes.size,
      usedCode: code 
    });
    
    // Generate new backup codes if running low
    if (backupData.codes.size <= 2) {
      const newCodes = this.generateBackupCodes(userId);
      this.emit('backupCodesRegenerationRequired', { userId, newCodes });
    }
    
    return { 
      success: true, 
      method: 'backup_code',
      remainingCodes: backupData.codes.size
    };
  }

  getBackupCodes(userId) {
    const backupData = this.backupCodes.get(userId);
    
    if (!backupData) {
      return null;
    }
    
    return {
      totalCodes: this.options.backupCodesCount,
      remainingCodes: backupData.codes.size,
      usedCodes: backupData.usedCodes.size,
      createdAt: backupData.createdAt,
      lastUsedAt: backupData.lastUsedAt
    };
  }

  // MFA Management
  async enableMFA(userId, method, setupData) {
    switch (method) {
      case 'totp':
        return await this.setupTOTP(userId, setupData);
      case 'sms':
        return await this.setupSMS(userId, setupData.phoneNumber);
      case 'email':
        return await this.setupEmail(userId, setupData.email);
      case 'webauthn':
        return await this.setupWebAuthn(userId, setupData);
      default:
        throw new Error(`Unsupported MFA method: ${method}`);
    }
  }

  async disableMFA(userId, method) {
    const userSettings = this.getUserMFASettings(userId);
    
    switch (method) {
      case 'totp':
        return await this.disableTOTP(userId);
      case 'sms':
        if (userSettings.sms) {
          userSettings.sms.enabled = false;
          userSettings.enabledMethods.delete('sms');
        }
        break;
      case 'email':
        if (userSettings.email) {
          userSettings.email.enabled = false;
          userSettings.enabledMethods.delete('email');
        }
        break;
      case 'webauthn':
        if (userSettings.webauthn) {
          userSettings.webauthn.enabled = false;
          userSettings.enabledMethods.delete('webauthn');
        }
        break;
    }
    
    // Check if MFA should be disabled entirely
    if (userSettings.enabledMethods.size === 0) {
      userSettings.mfaEnabled = false;
    }
    
    this.userMFASettings.set(userId, userSettings);
    
    this.emit('mfaMethodDisabled', { userId, method });
    
    return { success: true };
  }

  async verifyMFA(userId, method, code, additionalData = {}) {
    const userSettings = this.getUserMFASettings(userId);
    
    if (!userSettings.mfaEnabled) {
      throw new Error('MFA is not enabled for this user');
    }
    
    if (!userSettings.enabledMethods.has(method)) {
      throw new Error(`MFA method ${method} is not enabled for this user`);
    }
    
    switch (method) {
      case 'totp':
        return await this.verifyTOTP(userId, code);
      case 'sms':
        const smsVerified = await this.verifySMSCode(userId, code);
        return smsVerified ? { success: true, method: 'sms' } : { success: false };
      case 'email':
        const emailVerified = await this.verifyEmailCode(userId, code);
        return emailVerified ? { success: true, method: 'email' } : { success: false };
      case 'webauthn':
        return await this.verifyWebAuthn(userId, additionalData.credentialId, code, additionalData);
      case 'backup_code':
        return await this.verifyBackupCode(userId, code);
      default:
        throw new Error(`Unsupported MFA method: ${method}`);
    }
  }

  // User MFA Status
  getUserMFAStatus(userId) {
    const userSettings = this.getUserMFASettings(userId);
    
    return {
      mfaEnabled: userSettings.mfaEnabled,
      enabledMethods: Array.from(userSettings.enabledMethods),
      availableMethods: this.getAvailableMethods(),
      
      // Method-specific status
      totp: userSettings.totp ? {
        enabled: userSettings.totp.enabled,
        confirmed: userSettings.totp.confirmed,
        setupAt: userSettings.totp.setupAt,
        lastUsedAt: userSettings.totp.lastUsedAt
      } : null,
      
      sms: userSettings.sms ? {
        enabled: userSettings.sms.enabled,
        verified: userSettings.sms.verified,
        phoneNumber: this.maskPhoneNumber(userSettings.sms.phoneNumber),
        setupAt: userSettings.sms.setupAt,
        lastUsedAt: userSettings.sms.lastUsedAt
      } : null,
      
      email: userSettings.email ? {
        enabled: userSettings.email.enabled,
        verified: userSettings.email.verified,
        email: this.maskEmail(userSettings.email.email),
        setupAt: userSettings.email.setupAt,
        lastUsedAt: userSettings.email.lastUsedAt
      } : null,
      
      webauthn: userSettings.webauthn ? {
        enabled: userSettings.webauthn.enabled,
        credentialsCount: userSettings.webauthn.credentials.length,
        credentials: userSettings.webauthn.credentials.map(c => ({
          id: c.id,
          name: c.name,
          createdAt: c.createdAt,
          lastUsedAt: c.lastUsedAt
        }))
      } : null,
      
      backupCodes: this.getBackupCodes(userId),
      
      // Security info
      isLockedOut: this.isUserLockedOut(userId),
      failedAttempts: this.getFailedAttemptsCount(userId)
    };
  }

  getUserMFASettings(userId) {
    if (!this.userMFASettings.has(userId)) {
      this.userMFASettings.set(userId, {
        mfaEnabled: false,
        enabledMethods: new Set(),
        createdAt: new Date(),
        updatedAt: new Date()
      });
    }
    
    return this.userMFASettings.get(userId);
  }

  getAvailableMethods() {
    const methods = ['totp', 'backup_code'];
    
    if (this.options.enableSMS) methods.push('sms');
    if (this.options.enableEmail) methods.push('email');
    if (this.options.enableWebAuthn) methods.push('webauthn');
    
    return methods;
  }

  // Failed Attempts and Lockout
  recordFailedAttempt(userId, method) {
    const key = `${userId}:${method}`;
    
    if (!this.failedAttempts.has(key)) {
      this.failedAttempts.set(key, {
        count: 0,
        firstAttempt: new Date(),
        lastAttempt: new Date(),
        lockedUntil: null
      });
    }
    
    const attempts = this.failedAttempts.get(key);
    attempts.count++;
    attempts.lastAttempt = new Date();
    
    if (attempts.count >= this.options.maxAttempts) {
      attempts.lockedUntil = new Date(Date.now() + this.options.lockoutDuration);
      this.emit('userLockedOut', { userId, method, lockedUntil: attempts.lockedUntil });
    }
    
    this.failedAttempts.set(key, attempts);
    
    this.emit('mfaFailedAttempt', { userId, method, attemptCount: attempts.count });
  }

  clearFailedAttempts(userId, method = null) {
    if (method) {
      this.failedAttempts.delete(`${userId}:${method}`);
    } else {
      // Clear all methods for user
      for (const [key] of this.failedAttempts) {
        if (key.startsWith(`${userId}:`)) {
          this.failedAttempts.delete(key);
        }
      }
    }
  }

  isUserLockedOut(userId) {
    const now = new Date();
    
    for (const [key, attempts] of this.failedAttempts) {
      if (key.startsWith(`${userId}:`) && attempts.lockedUntil && attempts.lockedUntil > now) {
        return true;
      }
    }
    
    return false;
  }

  getFailedAttemptsCount(userId) {
    let totalAttempts = 0;
    
    for (const [key, attempts] of this.failedAttempts) {
      if (key.startsWith(`${userId}:`)) {
        totalAttempts += attempts.count;
      }
    }
    
    return totalAttempts;
  }

  // Utility Methods
  generateSMSCode() {
    return crypto.randomInt(100000, 999999).toString().padStart(this.options.smsCodeLength, '0');
  }

  generateEmailCode() {
    return crypto.randomInt(100000, 999999).toString().padStart(this.options.emailCodeLength, '0');
  }

  generateBackupCode() {
    return crypto.randomBytes(4).toString('hex').toUpperCase();
  }

  generateCredentialId() {
    return crypto.randomBytes(16).toString('hex');
  }

  maskPhoneNumber(phone) {
    if (!phone || phone.length < 4) return phone;
    return phone.slice(0, -4).replace(/\d/g, '*') + phone.slice(-4);
  }

  maskEmail(email) {
    const [username, domain] = email.split('@');
    if (username.length <= 2) return email;
    return username[0] + '*'.repeat(username.length - 2) + username.slice(-1) + '@' + domain;
  }

  // Integration Methods (to be implemented with actual services)
  async sendSMSMessage(phoneNumber, message) {
    // Integration with SMS service (Twilio, AWS SNS, etc.)
    console.log(`SMS to ${phoneNumber}: ${message}`);
    return true;
  }

  async sendEmailMessage(email, subject, message) {
    // Integration with email service (SendGrid, AWS SES, etc.)
    console.log(`Email to ${email} - ${subject}: ${message}`);
    return true;
  }

  async sendSMSVerificationCode(userId, phoneNumber) {
    const code = this.generateSMSCode();
    const expiresAt = new Date(Date.now() + this.options.codeExpiration);
    
    this.pendingCodes.set(`sms:${userId}`, {
      code,
      expiresAt,
      method: 'sms_setup',
      attempts: 0
    });
    
    await this.sendSMSMessage(phoneNumber, `Your ActiveLog verification code is: ${code}`);
    return code;
  }

  async sendEmailVerificationCode(userId, email) {
    const code = this.generateEmailCode();
    const expiresAt = new Date(Date.now() + this.options.codeExpiration);
    
    this.pendingCodes.set(`email:${userId}`, {
      code,
      expiresAt,
      method: 'email_setup',
      attempts: 0
    });
    
    await this.sendEmailMessage(email, 'ActiveLog Verification Code', 
      `Your verification code is: ${code}. This code expires in 5 minutes.`);
    return code;
  }

  async verifyWebAuthnSignature(credential, signature, challengeData) {
    // WebAuthn signature verification would be implemented here
    // This is a complex process involving cryptographic verification
    return true; // Simplified for this example
  }

  // Cleanup and Maintenance
  setupCleanupInterval() {
    // Clean up expired codes and old failed attempts every 5 minutes
    setInterval(() => {
      this.cleanupExpiredData();
    }, 5 * 60 * 1000);
  }

  cleanupExpiredData() {
    const now = new Date();
    
    // Clean up expired pending codes
    for (const [key, codeData] of this.pendingCodes) {
      if (codeData.expiresAt < now) {
        this.pendingCodes.delete(key);
      }
    }
    
    // Clean up old failed attempts
    for (const [key, attempts] of this.failedAttempts) {
      if (attempts.lockedUntil && attempts.lockedUntil < now) {
        this.failedAttempts.delete(key);
      }
    }
  }

  // Statistics and Monitoring
  getStats() {
    let totalUsers = 0;
    let usersWithMFA = 0;
    let methodCounts = {};
    
    for (const settings of this.userMFASettings.values()) {
      totalUsers++;
      
      if (settings.mfaEnabled) {
        usersWithMFA++;
        
        for (const method of settings.enabledMethods) {
          methodCounts[method] = (methodCounts[method] || 0) + 1;
        }
      }
    }
    
    return {
      totalUsers,
      usersWithMFA,
      mfaAdoptionRate: totalUsers > 0 ? (usersWithMFA / totalUsers) * 100 : 0,
      methodCounts,
      pendingCodes: this.pendingCodes.size,
      failedAttempts: this.failedAttempts.size,
      lockedOutUsers: Array.from(this.failedAttempts.values())
        .filter(attempts => attempts.lockedUntil && attempts.lockedUntil > new Date()).length
    };
  }

  reset() {
    this.userMFASettings.clear();
    this.pendingCodes.clear();
    this.failedAttempts.clear();
    this.backupCodes.clear();
    this.webAuthnCredentials.clear();
  }
}

module.exports = MFAManager;