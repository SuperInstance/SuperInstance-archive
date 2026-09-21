const EventEmitter = require('events');
const crypto = require('crypto');
const UAParser = require('ua-parser-js');
const Device = require('../models/Device');
const DeviceTrustScore = require('../models/DeviceTrustScore');
const AuditLogger = require('./AuditLogger');

class DeviceManager extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      trustDuration: config.trustDuration || 30 * 24 * 60 * 60 * 1000, // 30 days
      maxDevicesPerUser: config.maxDevicesPerUser || 10,
      requireVerification: config.requireVerification !== false,
      automaticTrust: config.automaticTrust === true,
      riskThreshold: config.riskThreshold || 0.7,
      ...config
    };
    
    this.auditLogger = new AuditLogger();
    this.deviceCache = new Map();
    this.riskFactors = {
      'new_device': 0.3,
      'new_location': 0.2,
      'suspicious_timing': 0.2,
      'unusual_behavior': 0.3,
      'tor_usage': 0.4,
      'vpn_usage': 0.1,
      'outdated_browser': 0.1
    };
  }

  async registerDevice(userId, deviceInfo, context = {}) {
    try {
      const deviceFingerprint = this.generateDeviceFingerprint(deviceInfo);
      
      // Check if device already exists
      let device = await Device.findOne({ 
        userId, 
        fingerprint: deviceFingerprint 
      });
      
      if (device) {
        // Update last seen
        device.lastSeenAt = new Date();
        device.lastIpAddress = context.ipAddress;
        device.accessCount = (device.accessCount || 0) + 1;
        await device.save();
        
        return {
          deviceId: device.deviceId,
          isNew: false,
          trustLevel: device.trustLevel,
          requiresVerification: false
        };
      }
      
      // Check device limits
      await this.enforceDeviceLimits(userId);
      
      // Create new device
      const deviceId = crypto.randomUUID();
      const parsedUA = new UAParser(deviceInfo.userAgent);
      
      device = new Device({
        deviceId,
        userId,
        fingerprint: deviceFingerprint,
        name: this.generateDeviceName(parsedUA),
        type: this.detectDeviceType(deviceInfo),
        userAgent: deviceInfo.userAgent,
        browser: {
          name: parsedUA.getBrowser().name,
          version: parsedUA.getBrowser().version
        },
        os: {
          name: parsedUA.getOS().name,
          version: parsedUA.getOS().version
        },
        screen: deviceInfo.screen,
        timezone: deviceInfo.timezone,
        language: deviceInfo.language,
        firstSeenAt: new Date(),
        lastSeenAt: new Date(),
        lastIpAddress: context.ipAddress,
        location: context.location,
        trustLevel: 'unverified',
        isActive: true,
        accessCount: 1,
        metadata: {
          registrationContext: context,
          capabilities: deviceInfo.capabilities || {}
        }
      });
      
      await device.save();
      
      // Calculate initial trust score
      const trustScore = await this.calculateTrustScore(device, context);
      await this.updateDeviceTrustScore(deviceId, trustScore);
      
      // Check if verification is required
      const requiresVerification = this.shouldRequireVerification(device, trustScore, context);
      
      if (!requiresVerification && this.config.automaticTrust) {
        device.trustLevel = 'trusted';
        device.trustedAt = new Date();
        await device.save();
      }
      
      await this.auditLogger.log('device_registered', 'success', {
        userId,
        deviceId,
        deviceType: device.type,
        trustScore: trustScore.score,
        requiresVerification,
        ipAddress: context.ipAddress
      });
      
      this.emit('device_registered', {
        device,
        trustScore,
        requiresVerification
      });
      
      return {
        deviceId,
        isNew: true,
        trustLevel: device.trustLevel,
        requiresVerification,
        trustScore: trustScore.score
      };
    } catch (error) {
      await this.auditLogger.log('device_registered', 'failed', {
        userId,
        error: error.message,
        ipAddress: context.ipAddress
      });
      throw error;
    }
  }

  async verifyDevice(userId, deviceId, verificationMethod, verificationData) {
    try {
      const device = await Device.findOne({ userId, deviceId });
      if (!device) {
        throw new Error('Device not found');
      }
      
      if (device.trustLevel === 'trusted') {
        return { verified: true, alreadyTrusted: true };
      }
      
      let verified = false;
      
      switch (verificationMethod) {
        case 'email':
          verified = await this.verifyEmailCode(userId, verificationData.code);
          break;
        case 'sms':
          verified = await this.verifySMSCode(userId, verificationData.code);
          break;
        case 'totp':
          verified = await this.verifyTOTPCode(userId, verificationData.code);
          break;
        case 'push':
          verified = await this.verifyPushNotification(userId, verificationData.token);
          break;
        case 'biometric':
          verified = await this.verifyBiometric(deviceId, verificationData);
          break;
        default:
          throw new Error(`Unsupported verification method: ${verificationMethod}`);
      }
      
      if (verified) {
        device.trustLevel = 'trusted';
        device.trustedAt = new Date();
        device.verificationMethod = verificationMethod;
        device.verifiedAt = new Date();
        await device.save();
        
        // Update trust score
        const trustScore = await this.calculateTrustScore(device);
        trustScore.verified = true;
        trustScore.verificationMethod = verificationMethod;
        await this.updateDeviceTrustScore(deviceId, trustScore);
        
        await this.auditLogger.log('device_verified', 'success', {
          userId,
          deviceId,
          verificationMethod,
          trustScore: trustScore.score
        });
        
        this.emit('device_verified', { device, verificationMethod });
      }
      
      return { verified, trustLevel: device.trustLevel };
    } catch (error) {
      await this.auditLogger.log('device_verified', 'failed', {
        userId,
        deviceId,
        verificationMethod,
        error: error.message
      });
      throw error;
    }
  }

  async revokeDevice(userId, deviceId, reason = 'user_request') {
    try {
      const device = await Device.findOne({ userId, deviceId });
      if (!device) {
        throw new Error('Device not found');
      }
      
      device.trustLevel = 'revoked';
      device.revokedAt = new Date();
      device.revocationReason = reason;
      device.isActive = false;
      await device.save();
      
      // Remove from cache
      this.deviceCache.delete(deviceId);
      
      await this.auditLogger.log('device_revoked', 'success', {
        userId,
        deviceId,
        reason,
        deviceType: device.type
      });
      
      this.emit('device_revoked', { device, reason });
      
      return true;
    } catch (error) {
      await this.auditLogger.log('device_revoked', 'failed', {
        userId,
        deviceId,
        error: error.message
      });
      throw error;
    }
  }

  async getUserDevices(userId, options = {}) {
    try {
      const query = { userId };
      
      if (options.activeOnly !== false) {
        query.isActive = true;
      }
      
      if (options.trustLevel) {
        query.trustLevel = options.trustLevel;
      }
      
      const devices = await Device.find(query)
        .sort({ lastSeenAt: -1 })
        .limit(options.limit || 50);
      
      const deviceList = await Promise.all(devices.map(async (device) => {
        const trustScore = await DeviceTrustScore.findOne({ deviceId: device.deviceId });
        
        return {
          deviceId: device.deviceId,
          name: device.name,
          type: device.type,
          browser: device.browser,
          os: device.os,
          trustLevel: device.trustLevel,
          trustScore: trustScore?.score || 0,
          firstSeenAt: device.firstSeenAt,
          lastSeenAt: device.lastSeenAt,
          lastIpAddress: device.lastIpAddress,
          location: device.location,
          accessCount: device.accessCount,
          isCurrentDevice: options.currentDeviceId === device.deviceId
        };
      }));
      
      return deviceList;
    } catch (error) {
      console.error('Error retrieving user devices:', error);
      return [];
    }
  }

  async calculateTrustScore(device, context = {}) {
    try {
      let score = 0.5; // Base score
      const factors = [];
      
      // Device age factor
      const deviceAge = Date.now() - device.firstSeenAt.getTime();
      const ageDays = deviceAge / (24 * 60 * 60 * 1000);
      if (ageDays > 30) {
        score += 0.2;
        factors.push('mature_device');
      } else if (ageDays < 1) {
        score -= 0.2;
        factors.push('new_device');
      }
      
      // Usage frequency
      const accessesPerDay = device.accessCount / Math.max(ageDays, 1);
      if (accessesPerDay > 3) {
        score += 0.1;
        factors.push('frequent_use');
      }
      
      // Location consistency
      if (device.location && context.location) {
        const distance = this.calculateDistance(device.location, context.location);
        if (distance > 1000) {
          score -= 0.15;
          factors.push('location_change');
        } else if (distance < 50) {
          score += 0.1;
          factors.push('consistent_location');
        }
      }
      
      // Browser and OS factors
      if (device.browser.name && device.os.name) {
        const commonCombos = ['Chrome-Windows', 'Safari-macOS', 'Safari-iOS', 'Chrome-Android'];
        const combo = `${device.browser.name}-${device.os.name}`;
        if (commonCombos.includes(combo)) {
          score += 0.05;
          factors.push('common_platform');
        }
      }
      
      // Time-based patterns
      if (context.timestamp) {
        const hour = new Date(context.timestamp).getHours();
        if (hour < 6 || hour > 23) {
          score -= 0.1;
          factors.push('unusual_timing');
        }
      }
      
      // Security indicators
      if (context.isVPN) {
        score -= this.riskFactors.vpn_usage;
        factors.push('vpn_usage');
      }
      
      if (context.isTor) {
        score -= this.riskFactors.tor_usage;
        factors.push('tor_usage');
      }
      
      // Browser version check
      if (this.isOutdatedBrowser(device.browser)) {
        score -= this.riskFactors.outdated_browser;
        factors.push('outdated_browser');
      }
      
      // Normalize score between 0 and 1
      score = Math.max(0, Math.min(1, score));
      
      const trustScore = {
        score,
        factors,
        calculatedAt: new Date(),
        riskLevel: this.calculateRiskLevel(score),
        recommendations: this.generateRecommendations(score, factors)
      };
      
      return trustScore;
    } catch (error) {
      console.error('Error calculating trust score:', error);
      return { score: 0.3, factors: ['calculation_error'], calculatedAt: new Date() };
    }
  }

  async updateDeviceTrustScore(deviceId, trustScore) {
    try {
      await DeviceTrustScore.findOneAndUpdate(
        { deviceId },
        { ...trustScore, updatedAt: new Date() },
        { upsert: true, new: true }
      );
    } catch (error) {
      console.error('Error updating device trust score:', error);
    }
  }

  async detectAnomalousActivity(deviceId, activityData) {
    try {
      const device = await Device.findOne({ deviceId });
      if (!device) return false;
      
      const anomalies = [];
      
      // Check for device fingerprint changes
      const currentFingerprint = this.generateDeviceFingerprint(activityData.deviceInfo);
      if (device.fingerprint !== currentFingerprint) {
        anomalies.push('fingerprint_change');
      }
      
      // Check for rapid location changes
      if (device.location && activityData.location) {
        const distance = this.calculateDistance(device.location, activityData.location);
        const timeDiff = new Date() - device.lastSeenAt;
        const speedKmh = distance / (timeDiff / (60 * 60 * 1000));
        
        if (speedKmh > 1000) { // Faster than commercial aircraft
          anomalies.push('impossible_travel');
        }
      }
      
      // Check for unusual usage patterns
      const typicalAccessHour = this.getTypicalAccessTime(device);
      const currentHour = new Date().getHours();
      if (Math.abs(currentHour - typicalAccessHour) > 6) {
        anomalies.push('unusual_timing');
      }
      
      if (anomalies.length > 0) {
        await this.auditLogger.log('anomalous_device_activity', 'warning', {
          deviceId,
          userId: device.userId,
          anomalies,
          activityData
        });
        
        this.emit('anomalous_activity', {
          device,
          anomalies,
          activityData
        });
        
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Error detecting anomalous activity:', error);
      return false;
    }
  }

  generateDeviceFingerprint(deviceInfo) {
    const fingerprint = {
      userAgent: deviceInfo.userAgent,
      screen: deviceInfo.screen,
      timezone: deviceInfo.timezone,
      language: deviceInfo.language,
      platform: deviceInfo.platform,
      canvas: deviceInfo.canvas,
      webgl: deviceInfo.webgl,
      fonts: deviceInfo.fonts
    };
    
    return crypto
      .createHash('sha256')
      .update(JSON.stringify(fingerprint))
      .digest('hex');
  }

  generateDeviceName(parsedUA) {
    const browser = parsedUA.getBrowser();
    const os = parsedUA.getOS();
    const device = parsedUA.getDevice();
    
    if (device.model && device.vendor) {
      return `${device.vendor} ${device.model}`;
    }
    
    return `${browser.name || 'Unknown Browser'} on ${os.name || 'Unknown OS'}`;
  }

  detectDeviceType(deviceInfo) {
    const ua = deviceInfo.userAgent.toLowerCase();
    
    if (ua.includes('mobile') || ua.includes('android') || ua.includes('iphone')) {
      return 'mobile';
    }
    
    if (ua.includes('tablet') || ua.includes('ipad')) {
      return 'tablet';
    }
    
    return 'desktop';
  }

  shouldRequireVerification(device, trustScore, context) {
    if (!this.config.requireVerification) {
      return false;
    }
    
    // Always require verification for low trust scores
    if (trustScore.score < this.config.riskThreshold) {
      return true;
    }
    
    // Require verification for certain risk factors
    const highRiskFactors = ['new_device', 'tor_usage', 'impossible_travel'];
    if (trustScore.factors.some(factor => highRiskFactors.includes(factor))) {
      return true;
    }
    
    return false;
  }

  calculateRiskLevel(score) {
    if (score >= 0.8) return 'low';
    if (score >= 0.6) return 'medium';
    if (score >= 0.4) return 'high';
    return 'critical';
  }

  generateRecommendations(score, factors) {
    const recommendations = [];
    
    if (score < 0.3) {
      recommendations.push('Consider blocking or requiring additional verification');
    }
    
    if (factors.includes('new_device')) {
      recommendations.push('Verify device through email or SMS');
    }
    
    if (factors.includes('tor_usage')) {
      recommendations.push('Review for suspicious activity');
    }
    
    if (factors.includes('unusual_timing')) {
      recommendations.push('Monitor for account compromise');
    }
    
    return recommendations;
  }

  isOutdatedBrowser(browser) {
    const minVersions = {
      'Chrome': 90,
      'Firefox': 88,
      'Safari': 14,
      'Edge': 90
    };
    
    const minVersion = minVersions[browser.name];
    if (!minVersion) return false;
    
    const version = parseInt(browser.version);
    return version < minVersion;
  }

  getTypicalAccessTime(device) {
    // Simplified - in production, would analyze historical access patterns
    return 10; // 10 AM as default typical time
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

  async enforceDeviceLimits(userId) {
    const deviceCount = await Device.countDocuments({ userId, isActive: true });
    
    if (deviceCount >= this.config.maxDevicesPerUser) {
      const oldestDevices = await Device.find({ userId, isActive: true })
        .sort({ lastSeenAt: 1 })
        .limit(deviceCount - this.config.maxDevicesPerUser + 1);
      
      for (const device of oldestDevices) {
        await this.revokeDevice(userId, device.deviceId, 'device_limit_exceeded');
      }
    }
  }

  // Verification method implementations (simplified)
  async verifyEmailCode(userId, code) {
    // Implementation would verify email code
    return true;
  }

  async verifySMSCode(userId, code) {
    // Implementation would verify SMS code
    return true;
  }

  async verifyTOTPCode(userId, code) {
    // Implementation would verify TOTP code
    return true;
  }

  async verifyPushNotification(userId, token) {
    // Implementation would verify push notification
    return true;
  }

  async verifyBiometric(deviceId, biometricData) {
    // Implementation would verify biometric data
    return true;
  }
}

module.exports = DeviceManager;