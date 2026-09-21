const crypto = require('crypto');
const UAParser = require('ua-parser-js');
const geoip = require('geoip-lite');
const { EventEmitter } = require('events');

class DeviceFingerprinting extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      fingerprintAlgorithm: options.fingerprintAlgorithm || 'sha256',
      enableLocationTracking: options.enableLocationTracking !== false,
      enableBehavioralAnalysis: options.enableBehavioralAnalysis !== false,
      deviceTrustThreshold: options.deviceTrustThreshold || 0.8,
      suspiciousThreshold: options.suspiciousThreshold || 0.6,
      fingerprintTTL: options.fingerprintTTL || 86400000, // 24 hours
      maxDevicesPerUser: options.maxDevicesPerUser || 20,
      riskFactors: options.riskFactors || this.getDefaultRiskFactors(),
      ...options
    };
    
    this.deviceFingerprints = new Map();
    this.userDevices = new Map();
    this.deviceSessions = new Map();
    this.behavioralProfiles = new Map();
    this.riskAssessments = new Map();
    this.deviceReports = new Map();
    
    this.setupCleanupInterval();
  }

  // Device Fingerprint Generation
  async generateFingerprint(requestData) {
    const {
      userAgent,
      ip,
      acceptLanguage,
      acceptEncoding,
      dnt,
      connection,
      headers,
      screenResolution,
      colorDepth,
      timezone,
      plugins,
      fonts,
      canvas,
      webgl,
      audio,
      cookies,
      localStorage,
      sessionStorage
    } = requestData;
    
    // Parse User Agent
    const uaParser = new UAParser(userAgent);
    const browser = uaParser.getBrowser();
    const os = uaParser.getOS();
    const device = uaParser.getDevice();
    const engine = uaParser.getEngine();
    
    // Generate location data
    const locationData = this.options.enableLocationTracking 
      ? this.getLocationFromIP(ip) 
      : null;
    
    // Create fingerprint components
    const fingerprintComponents = {
      // Browser fingerprint
      userAgent,
      browser: {
        name: browser.name,
        version: browser.version,
        major: browser.major
      },
      os: {
        name: os.name,
        version: os.version
      },
      device: {
        vendor: device.vendor,
        model: device.model,
        type: device.type
      },
      engine: {
        name: engine.name,
        version: engine.version
      },
      
      // HTTP headers fingerprint
      acceptLanguage,
      acceptEncoding,
      dnt: dnt || '0',
      connection: connection || 'keep-alive',
      
      // Screen and hardware
      screenResolution: screenResolution || 'unknown',
      colorDepth: colorDepth || 24,
      timezone: timezone || 'UTC',
      
      // Plugins and capabilities
      plugins: plugins || [],
      fonts: fonts || [],
      
      // Canvas and WebGL fingerprinting
      canvas: canvas ? this.hashData(canvas) : null,
      webgl: webgl ? this.hashData(JSON.stringify(webgl)) : null,
      audio: audio ? this.hashData(audio) : null,
      
      // Storage capabilities
      cookies: cookies || false,
      localStorage: localStorage || false,
      sessionStorage: sessionStorage || false,
      
      // Network information
      ip,
      location: locationData,
      
      // Additional headers for entropy
      customHeaders: this.extractCustomHeaders(headers)
    };
    
    // Generate stable fingerprint hash
    const stableFingerprint = this.generateStableFingerprint(fingerprintComponents);
    
    // Generate detailed fingerprint with more entropy
    const detailedFingerprint = this.generateDetailedFingerprint(fingerprintComponents);
    
    const fingerprint = {
      id: this.generateFingerprintId(),
      stableId: stableFingerprint,
      detailedId: detailedFingerprint,
      
      components: fingerprintComponents,
      
      // Metadata
      createdAt: new Date(),
      lastSeenAt: new Date(),
      useCount: 1,
      
      // Risk assessment
      riskScore: 0,
      trustScore: 0,
      suspiciousFlags: []
    };
    
    // Perform risk assessment
    await this.assessDeviceRisk(fingerprint);
    
    this.deviceFingerprints.set(fingerprint.id, fingerprint);
    
    this.emit('fingerprintGenerated', {
      fingerprintId: fingerprint.id,
      stableId: fingerprint.stableId,
      riskScore: fingerprint.riskScore,
      trustScore: fingerprint.trustScore
    });
    
    return fingerprint;
  }

  generateStableFingerprint(components) {
    // Use only stable components that don't change frequently
    const stableComponents = {
      browser: components.browser.name,
      browserMajor: components.browser.major,
      os: components.os.name,
      osVersion: components.os.version,
      screenResolution: components.screenResolution,
      colorDepth: components.colorDepth,
      timezone: components.timezone,
      acceptLanguage: components.acceptLanguage,
      dnt: components.dnt,
      plugins: components.plugins.sort(),
      fonts: components.fonts.sort(),
      canvas: components.canvas,
      webgl: components.webgl
    };
    
    const stableString = JSON.stringify(stableComponents);
    return this.hashData(stableString);
  }

  generateDetailedFingerprint(components) {
    // Use all available components for maximum uniqueness
    const detailedString = JSON.stringify(components);
    return this.hashData(detailedString);
  }

  // Device Recognition and Tracking
  async recognizeDevice(requestData, userId = null) {
    const currentFingerprint = await this.generateFingerprint(requestData);
    
    // Look for existing similar fingerprints
    const matchingDevices = this.findMatchingDevices(currentFingerprint);
    
    let deviceRecord = null;
    
    if (matchingDevices.length > 0) {
      // Use the best matching device
      deviceRecord = matchingDevices[0];
      
      // Update device record
      await this.updateDeviceRecord(deviceRecord.id, {
        lastFingerprint: currentFingerprint,
        lastSeenAt: new Date(),
        useCount: deviceRecord.useCount + 1,
        updatedAt: new Date()
      });
      
      this.emit('deviceRecognized', {
        deviceId: deviceRecord.id,
        fingerprintId: currentFingerprint.id,
        userId,
        matchScore: deviceRecord.matchScore
      });
    } else {
      // Create new device record
      deviceRecord = await this.createDeviceRecord(currentFingerprint, userId);
      
      this.emit('newDeviceDetected', {
        deviceId: deviceRecord.id,
        fingerprintId: currentFingerprint.id,
        userId,
        riskScore: currentFingerprint.riskScore
      });
    }
    
    // Associate device with user if provided
    if (userId) {
      await this.associateDeviceWithUser(deviceRecord.id, userId);
    }
    
    // Track device session
    await this.trackDeviceSession(deviceRecord.id, requestData);
    
    return {
      deviceId: deviceRecord.id,
      fingerprint: currentFingerprint,
      isKnownDevice: matchingDevices.length > 0,
      riskScore: currentFingerprint.riskScore,
      trustScore: currentFingerprint.trustScore,
      suspiciousFlags: currentFingerprint.suspiciousFlags
    };
  }

  findMatchingDevices(fingerprint) {
    const matches = [];
    const threshold = this.options.deviceTrustThreshold;
    
    for (const existingFingerprint of this.deviceFingerprints.values()) {
      // Skip if too old
      if (Date.now() - existingFingerprint.createdAt.getTime() > this.options.fingerprintTTL) {
        continue;
      }
      
      const similarity = this.calculateFingerprintSimilarity(fingerprint, existingFingerprint);
      
      if (similarity >= threshold) {
        const deviceRecord = this.findDeviceByFingerprint(existingFingerprint.id);
        if (deviceRecord) {
          matches.push({
            ...deviceRecord,
            similarity,
            matchScore: similarity
          });
        }
      }
    }
    
    // Sort by similarity (best match first)
    return matches.sort((a, b) => b.similarity - a.similarity);
  }

  calculateFingerprintSimilarity(fp1, fp2) {
    let totalWeight = 0;
    let matchedWeight = 0;
    
    const weights = {
      stableId: 0.4,
      browser: 0.15,
      os: 0.15,
      screenResolution: 0.1,
      timezone: 0.05,
      acceptLanguage: 0.05,
      plugins: 0.05,
      canvas: 0.03,
      webgl: 0.02
    };
    
    // Compare stable fingerprint (most important)
    totalWeight += weights.stableId;
    if (fp1.stableId === fp2.stableId) {
      matchedWeight += weights.stableId;
    }
    
    // Compare browser
    totalWeight += weights.browser;
    if (fp1.components.browser.name === fp2.components.browser.name &&
        fp1.components.browser.major === fp2.components.browser.major) {
      matchedWeight += weights.browser;
    }
    
    // Compare OS
    totalWeight += weights.os;
    if (fp1.components.os.name === fp2.components.os.name) {
      matchedWeight += weights.os;
    }
    
    // Compare screen resolution
    totalWeight += weights.screenResolution;
    if (fp1.components.screenResolution === fp2.components.screenResolution) {
      matchedWeight += weights.screenResolution;
    }
    
    // Compare timezone
    totalWeight += weights.timezone;
    if (fp1.components.timezone === fp2.components.timezone) {
      matchedWeight += weights.timezone;
    }
    
    // Compare accept language
    totalWeight += weights.acceptLanguage;
    if (fp1.components.acceptLanguage === fp2.components.acceptLanguage) {
      matchedWeight += weights.acceptLanguage;
    }
    
    // Compare plugins (partial match)
    totalWeight += weights.plugins;
    const pluginSimilarity = this.calculateArraySimilarity(
      fp1.components.plugins,
      fp2.components.plugins
    );
    matchedWeight += weights.plugins * pluginSimilarity;
    
    // Compare canvas
    totalWeight += weights.canvas;
    if (fp1.components.canvas && fp2.components.canvas && 
        fp1.components.canvas === fp2.components.canvas) {
      matchedWeight += weights.canvas;
    }
    
    // Compare WebGL
    totalWeight += weights.webgl;
    if (fp1.components.webgl && fp2.components.webgl && 
        fp1.components.webgl === fp2.components.webgl) {
      matchedWeight += weights.webgl;
    }
    
    return totalWeight > 0 ? matchedWeight / totalWeight : 0;
  }

  calculateArraySimilarity(arr1, arr2) {
    if (!arr1 || !arr2 || arr1.length === 0 || arr2.length === 0) {
      return 0;
    }
    
    const set1 = new Set(arr1);
    const set2 = new Set(arr2);
    const intersection = new Set([...set1].filter(x => set2.has(x)));
    const union = new Set([...set1, ...set2]);
    
    return intersection.size / union.size;
  }

  // Device Records Management
  async createDeviceRecord(fingerprint, userId = null) {
    const deviceId = this.generateDeviceId();
    
    const device = {
      id: deviceId,
      userId,
      
      // Fingerprint data
      currentFingerprint: fingerprint,
      fingerprintHistory: [fingerprint.id],
      
      // Device information
      browser: fingerprint.components.browser,
      os: fingerprint.components.os,
      device: fingerprint.components.device,
      
      // Location and network
      lastLocation: fingerprint.components.location,
      lastIP: fingerprint.components.ip,
      
      // Trust and risk
      trustScore: fingerprint.trustScore,
      riskScore: fingerprint.riskScore,
      isVerified: false,
      isTrusted: false,
      isBlocked: false,
      
      // Usage statistics
      useCount: 1,
      sessionCount: 0,
      
      // Timestamps
      firstSeenAt: new Date(),
      lastSeenAt: new Date(),
      createdAt: new Date(),
      updatedAt: new Date(),
      
      // Metadata
      name: this.generateDeviceName(fingerprint.components),
      tags: []
    };
    
    // Store device record (in production, this would go to a database)
    this.deviceRecords = this.deviceRecords || new Map();
    this.deviceRecords.set(deviceId, device);
    
    this.emit('deviceRecordCreated', {
      deviceId,
      userId,
      fingerprint: fingerprint.id
    });
    
    return device;
  }

  async updateDeviceRecord(deviceId, updates) {
    if (!this.deviceRecords) {
      return null;
    }
    
    const device = this.deviceRecords.get(deviceId);
    if (!device) {
      throw new Error(`Device record ${deviceId} not found`);
    }
    
    const updatedDevice = {
      ...device,
      ...updates,
      updatedAt: new Date()
    };
    
    this.deviceRecords.set(deviceId, updatedDevice);
    
    this.emit('deviceRecordUpdated', {
      deviceId,
      userId: device.userId,
      updates: Object.keys(updates)
    });
    
    return updatedDevice;
  }

  findDeviceByFingerprint(fingerprintId) {
    if (!this.deviceRecords) {
      return null;
    }
    
    for (const device of this.deviceRecords.values()) {
      if (device.fingerprintHistory.includes(fingerprintId)) {
        return device;
      }
    }
    
    return null;
  }

  // User-Device Association
  async associateDeviceWithUser(deviceId, userId) {
    // Update device record
    await this.updateDeviceRecord(deviceId, { userId });
    
    // Track user devices
    if (!this.userDevices.has(userId)) {
      this.userDevices.set(userId, new Set());
    }
    
    const userDeviceSet = this.userDevices.get(userId);
    userDeviceSet.add(deviceId);
    
    // Enforce device limit
    if (userDeviceSet.size > this.options.maxDevicesPerUser) {
      await this.enforceDeviceLimit(userId);
    }
    
    this.emit('deviceAssociated', { deviceId, userId });
  }

  async enforceDeviceLimit(userId) {
    const userDeviceSet = this.userDevices.get(userId);
    if (!userDeviceSet || userDeviceSet.size <= this.options.maxDevicesPerUser) {
      return;
    }
    
    // Get all user devices with timestamps
    const devices = [];
    for (const deviceId of userDeviceSet) {
      const device = this.deviceRecords?.get(deviceId);
      if (device) {
        devices.push(device);
      }
    }
    
    // Sort by last seen time (oldest first)
    devices.sort((a, b) => a.lastSeenAt.getTime() - b.lastSeenAt.getTime());
    
    // Remove oldest devices
    const devicesToRemove = devices.slice(0, devices.length - this.options.maxDevicesPerUser);
    
    for (const device of devicesToRemove) {
      userDeviceSet.delete(device.id);
      this.deviceRecords?.delete(device.id);
      
      this.emit('deviceLimitEnforced', {
        userId,
        removedDeviceId: device.id,
        reason: 'device_limit_exceeded'
      });
    }
  }

  // Risk Assessment
  async assessDeviceRisk(fingerprint) {
    const riskFactors = this.options.riskFactors;
    let riskScore = 0;
    const suspiciousFlags = [];
    
    // Check for suspicious user agents
    if (this.isSuspiciousUserAgent(fingerprint.components.userAgent)) {
      riskScore += riskFactors.suspiciousUserAgent;
      suspiciousFlags.push('suspicious_user_agent');
    }
    
    // Check for automation tools
    if (this.hasAutomationIndicators(fingerprint.components)) {
      riskScore += riskFactors.automationTools;
      suspiciousFlags.push('automation_tools');
    }
    
    // Check for VPN/Proxy usage
    if (this.isVPNorProxy(fingerprint.components.ip)) {
      riskScore += riskFactors.vpnProxy;
      suspiciousFlags.push('vpn_proxy');
    }
    
    // Check for unusual location
    if (this.isUnusualLocation(fingerprint.components.location)) {
      riskScore += riskFactors.unusualLocation;
      suspiciousFlags.push('unusual_location');
    }
    
    // Check for missing standard features
    if (this.hasMissingStandardFeatures(fingerprint.components)) {
      riskScore += riskFactors.missingFeatures;
      suspiciousFlags.push('missing_features');
    }
    
    // Check for inconsistent data
    if (this.hasInconsistentData(fingerprint.components)) {
      riskScore += riskFactors.inconsistentData;
      suspiciousFlags.push('inconsistent_data');
    }
    
    // Calculate trust score (inverse of risk)
    const trustScore = Math.max(0, 1 - riskScore);
    
    fingerprint.riskScore = Math.min(1, riskScore);
    fingerprint.trustScore = trustScore;
    fingerprint.suspiciousFlags = suspiciousFlags;
    
    if (riskScore >= this.options.suspiciousThreshold) {
      this.emit('suspiciousDeviceDetected', {
        fingerprintId: fingerprint.id,
        riskScore,
        suspiciousFlags
      });
    }
  }

  isSuspiciousUserAgent(userAgent) {
    const suspiciousPatterns = [
      /bot/i,
      /crawler/i,
      /spider/i,
      /scraper/i,
      /curl/i,
      /wget/i,
      /python/i,
      /java/i,
      /ruby/i,
      /php/i
    ];
    
    return suspiciousPatterns.some(pattern => pattern.test(userAgent));
  }

  hasAutomationIndicators(components) {
    // Check for headless browser indicators
    if (components.userAgent.includes('HeadlessChrome') ||
        components.userAgent.includes('PhantomJS') ||
        components.userAgent.includes('Selenium')) {
      return true;
    }
    
    // Check for missing plugins that most browsers have
    if (!components.plugins || components.plugins.length === 0) {
      return true;
    }
    
    // Check for suspicious canvas or WebGL data
    if (!components.canvas || !components.webgl) {
      return true;
    }
    
    return false;
  }

  isVPNorProxy(ip) {
    // This would integrate with VPN/proxy detection services
    // For now, just basic checks
    if (!ip) return false;
    
    // Check for common VPN/proxy IP ranges (simplified)
    const suspiciousRanges = [
      '10.', '172.16.', '192.168.', // Private ranges often used by proxies
      '127.', // Localhost
      '0.0.0.0' // Invalid IP
    ];
    
    return suspiciousRanges.some(range => ip.startsWith(range));
  }

  isUnusualLocation(location) {
    if (!location) return false;
    
    // Check for high-risk countries (this would be configurable)
    const highRiskCountries = ['TOR', 'XX']; // TOR and unknown countries
    
    return highRiskCountries.includes(location.country);
  }

  hasMissingStandardFeatures(components) {
    // Check for features that most modern browsers should have
    const requiredFeatures = [
      'localStorage',
      'sessionStorage',
      'cookies'
    ];
    
    return requiredFeatures.some(feature => !components[feature]);
  }

  hasInconsistentData(components) {
    // Check for inconsistencies in the fingerprint data
    
    // Mobile device with desktop screen resolution
    if (components.device.type === 'mobile' && components.screenResolution) {
      const [width, height] = components.screenResolution.split('x').map(Number);
      if (width > 1920 || height > 1080) {
        return true;
      }
    }
    
    // Very old browser version with modern features
    if (components.browser.version && parseInt(components.browser.version) < 50) {
      if (components.webgl || components.audio) {
        return true;
      }
    }
    
    return false;
  }

  // Session Tracking
  async trackDeviceSession(deviceId, requestData) {
    const sessionId = this.generateSessionId();
    
    const session = {
      id: sessionId,
      deviceId,
      
      // Session data
      ip: requestData.ip,
      userAgent: requestData.userAgent,
      referer: requestData.referer,
      
      // Location
      location: this.getLocationFromIP(requestData.ip),
      
      // Timing
      startedAt: new Date(),
      lastActivityAt: new Date(),
      endedAt: null,
      duration: 0,
      
      // Activity counters
      requestCount: 1,
      pageViews: 0,
      
      // Risk assessment
      riskEvents: [],
      anomalies: []
    };
    
    this.deviceSessions.set(sessionId, session);
    
    // Update device session count
    if (this.deviceRecords) {
      const device = this.deviceRecords.get(deviceId);
      if (device) {
        await this.updateDeviceRecord(deviceId, {
          sessionCount: device.sessionCount + 1
        });
      }
    }
    
    this.emit('sessionStarted', {
      sessionId,
      deviceId,
      ip: requestData.ip
    });
    
    return session;
  }

  async updateDeviceSession(sessionId, activity) {
    const session = this.deviceSessions.get(sessionId);
    if (!session) {
      return null;
    }
    
    session.lastActivityAt = new Date();
    session.requestCount++;
    
    if (activity.pageView) {
      session.pageViews++;
    }
    
    if (activity.riskEvent) {
      session.riskEvents.push({
        type: activity.riskEvent.type,
        description: activity.riskEvent.description,
        timestamp: new Date()
      });
    }
    
    this.deviceSessions.set(sessionId, session);
    
    return session;
  }

  async endDeviceSession(sessionId) {
    const session = this.deviceSessions.get(sessionId);
    if (!session) {
      return null;
    }
    
    session.endedAt = new Date();
    session.duration = session.endedAt.getTime() - session.startedAt.getTime();
    
    this.deviceSessions.set(sessionId, session);
    
    this.emit('sessionEnded', {
      sessionId,
      deviceId: session.deviceId,
      duration: session.duration,
      requestCount: session.requestCount
    });
    
    return session;
  }

  // Behavioral Analysis
  async analyzeBehavior(deviceId, activities) {
    if (!this.options.enableBehavioralAnalysis) {
      return null;
    }
    
    let profile = this.behavioralProfiles.get(deviceId);
    
    if (!profile) {
      profile = this.createBehavioralProfile(deviceId);
    }
    
    // Update profile with new activities
    for (const activity of activities) {
      this.updateBehavioralProfile(profile, activity);
    }
    
    // Detect anomalies
    const anomalies = this.detectBehavioralAnomalies(profile, activities);
    
    if (anomalies.length > 0) {
      this.emit('behavioralAnomalies', {
        deviceId,
        anomalies,
        riskScore: this.calculateBehavioralRisk(anomalies)
      });
    }
    
    this.behavioralProfiles.set(deviceId, profile);
    
    return {
      profile,
      anomalies,
      riskScore: this.calculateBehavioralRisk(anomalies)
    };
  }

  createBehavioralProfile(deviceId) {
    return {
      deviceId,
      
      // Activity patterns
      typingPatterns: {
        averageSpeed: 0,
        keyPressIntervals: [],
        commonMistakes: []
      },
      
      mouseMov
ements: {
        speed: 0,
        patterns: [],
        clickFrequency: 0
      },
      
      navigationPatterns: {
        commonPaths: [],
        timeSpentOnPages: {},
        scrollBehavior: {}
      },
      
      timePatterns: {
        activeHours: new Array(24).fill(0),
        activeDays: new Array(7).fill(0),
        sessionDurations: []
      },
      
      deviceUsage: {
        operatingSystems: new Map(),
        browsers: new Map(),
        locations: new Map()
      },
      
      // Metadata
      createdAt: new Date(),
      updatedAt: new Date(),
      activityCount: 0
    };
  }

  updateBehavioralProfile(profile, activity) {
    profile.updatedAt = new Date();
    profile.activityCount++;
    
    // Update typing patterns
    if (activity.typing) {
      profile.typingPatterns.keyPressIntervals.push(...activity.typing.intervals);
      profile.typingPatterns.averageSpeed = this.calculateAverageTypingSpeed(
        profile.typingPatterns.keyPressIntervals
      );
    }
    
    // Update mouse movements
    if (activity.mouse) {
      profile.mouseMovements.patterns.push(activity.mouse);
      profile.mouseMovements.speed = this.calculateAverageMouseSpeed(
        profile.mouseMovements.patterns
      );
    }
    
    // Update navigation patterns
    if (activity.navigation) {
      profile.navigationPatterns.commonPaths.push(activity.navigation.path);
      profile.navigationPatterns.timeSpentOnPages[activity.navigation.page] = 
        (profile.navigationPatterns.timeSpentOnPages[activity.navigation.page] || 0) + 
        activity.navigation.duration;
    }
    
    // Update time patterns
    if (activity.timestamp) {
      const hour = new Date(activity.timestamp).getHours();
      const day = new Date(activity.timestamp).getDay();
      profile.timePatterns.activeHours[hour]++;
      profile.timePatterns.activeDays[day]++;
    }
  }

  detectBehavioralAnomalies(profile, activities) {
    const anomalies = [];
    
    for (const activity of activities) {
      // Detect typing anomalies
      if (activity.typing) {
        const currentSpeed = this.calculateTypingSpeed(activity.typing.intervals);
        const expectedSpeed = profile.typingPatterns.averageSpeed;
        
        if (Math.abs(currentSpeed - expectedSpeed) > expectedSpeed * 0.5) {
          anomalies.push({
            type: 'typing_speed_anomaly',
            description: 'Typing speed significantly different from profile',
            severity: 'medium',
            details: { currentSpeed, expectedSpeed }
          });
        }
      }
      
      // Detect unusual time activity
      if (activity.timestamp) {
        const hour = new Date(activity.timestamp).getHours();
        const expectedActivity = profile.timePatterns.activeHours[hour];
        
        if (expectedActivity === 0 && profile.activityCount > 100) {
          anomalies.push({
            type: 'unusual_time_activity',
            description: 'Activity at unusual time',
            severity: 'low',
            details: { hour, expectedActivity }
          });
        }
      }
      
      // Detect location anomalies
      if (activity.location) {
        const knownLocations = Array.from(profile.deviceUsage.locations.keys());
        const isKnownLocation = knownLocations.some(location => 
          this.calculateLocationDistance(location, activity.location) < 100 // 100km
        );
        
        if (!isKnownLocation && knownLocations.length > 0) {
          anomalies.push({
            type: 'location_anomaly',
            description: 'Activity from unusual location',
            severity: 'high',
            details: { location: activity.location, knownLocations }
          });
        }
      }
    }
    
    return anomalies;
  }

  calculateBehavioralRisk(anomalies) {
    let riskScore = 0;
    
    for (const anomaly of anomalies) {
      switch (anomaly.severity) {
        case 'low':
          riskScore += 0.1;
          break;
        case 'medium':
          riskScore += 0.3;
          break;
        case 'high':
          riskScore += 0.5;
          break;
      }
    }
    
    return Math.min(1, riskScore);
  }

  // Device Management
  async verifyDevice(deviceId, userId) {
    if (!this.deviceRecords) {
      throw new Error('Device records not available');
    }
    
    const device = this.deviceRecords.get(deviceId);
    if (!device) {
      throw new Error(`Device ${deviceId} not found`);
    }
    
    if (device.userId !== userId) {
      throw new Error('Device does not belong to user');
    }
    
    await this.updateDeviceRecord(deviceId, {
      isVerified: true,
      isTrusted: true,
      verifiedAt: new Date()
    });
    
    this.emit('deviceVerified', { deviceId, userId });
    
    return true;
  }

  async blockDevice(deviceId, reason = 'Manual block') {
    if (!this.deviceRecords) {
      throw new Error('Device records not available');
    }
    
    const device = this.deviceRecords.get(deviceId);
    if (!device) {
      throw new Error(`Device ${deviceId} not found`);
    }
    
    await this.updateDeviceRecord(deviceId, {
      isBlocked: true,
      blockedAt: new Date(),
      blockReason: reason
    });
    
    this.emit('deviceBlocked', { deviceId, userId: device.userId, reason });
    
    return true;
  }

  async unblockDevice(deviceId) {
    if (!this.deviceRecords) {
      throw new Error('Device records not available');
    }
    
    const device = this.deviceRecords.get(deviceId);
    if (!device) {
      throw new Error(`Device ${deviceId} not found`);
    }
    
    await this.updateDeviceRecord(deviceId, {
      isBlocked: false,
      unblockedAt: new Date(),
      blockReason: null
    });
    
    this.emit('deviceUnblocked', { deviceId, userId: device.userId });
    
    return true;
  }

  // Utility Methods
  getLocationFromIP(ip) {
    if (!this.options.enableLocationTracking || !ip) {
      return null;
    }
    
    const geo = geoip.lookup(ip);
    
    if (!geo) {
      return null;
    }
    
    return {
      country: geo.country,
      region: geo.region,
      city: geo.city,
      timezone: geo.timezone,
      coordinates: {
        latitude: geo.ll[0],
        longitude: geo.ll[1]
      }
    };
  }

  extractCustomHeaders(headers) {
    if (!headers) return {};
    
    const customHeaders = {};
    const standardHeaders = [
      'user-agent', 'accept', 'accept-language', 'accept-encoding',
      'connection', 'host', 'referer', 'cookie', 'authorization'
    ];
    
    for (const [key, value] of Object.entries(headers)) {
      if (!standardHeaders.includes(key.toLowerCase())) {
        customHeaders[key] = value;
      }
    }
    
    return customHeaders;
  }

  hashData(data) {
    return crypto.createHash(this.options.fingerprintAlgorithm)
      .update(data)
      .digest('hex');
  }

  generateFingerprintId() {
    return `fp_${Date.now()}_${crypto.randomBytes(8).toString('hex')}`;
  }

  generateDeviceId() {
    return `dev_${Date.now()}_${crypto.randomBytes(8).toString('hex')}`;
  }

  generateSessionId() {
    return `sess_${Date.now()}_${crypto.randomBytes(8).toString('hex')}`;
  }

  generateDeviceName(components) {
    const os = components.os.name || 'Unknown';
    const browser = components.browser.name || 'Unknown';
    const device = components.device.type || 'desktop';
    
    return `${os} ${browser} (${device})`;
  }

  calculateAverageTypingSpeed(intervals) {
    if (intervals.length === 0) return 0;
    
    const totalTime = intervals.reduce((sum, interval) => sum + interval, 0);
    return intervals.length / (totalTime / 1000) * 60; // WPM
  }

  calculateTypingSpeed(intervals) {
    if (intervals.length === 0) return 0;
    
    const totalTime = intervals.reduce((sum, interval) => sum + interval, 0);
    return intervals.length / (totalTime / 1000) * 60; // WPM
  }

  calculateAverageMouseSpeed(patterns) {
    if (patterns.length === 0) return 0;
    
    const speeds = patterns.map(pattern => pattern.speed || 0);
    return speeds.reduce((sum, speed) => sum + speed, 0) / speeds.length;
  }

  calculateLocationDistance(loc1, loc2) {
    // Simplified distance calculation (would use proper geolocation libraries)
    if (!loc1.coordinates || !loc2.coordinates) return 0;
    
    const lat1 = loc1.coordinates.latitude;
    const lon1 = loc1.coordinates.longitude;
    const lat2 = loc2.coordinates.latitude;
    const lon2 = loc2.coordinates.longitude;
    
    const R = 6371; // Earth's radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    
    return R * c;
  }

  getDefaultRiskFactors() {
    return {
      suspiciousUserAgent: 0.4,
      automationTools: 0.5,
      vpnProxy: 0.3,
      unusualLocation: 0.2,
      missingFeatures: 0.3,
      inconsistentData: 0.4
    };
  }

  // Query Methods
  getUserDevices(userId) {
    if (!this.deviceRecords) {
      return [];
    }
    
    const userDeviceIds = this.userDevices.get(userId) || new Set();
    const devices = [];
    
    for (const deviceId of userDeviceIds) {
      const device = this.deviceRecords.get(deviceId);
      if (device) {
        devices.push({
          id: device.id,
          name: device.name,
          browser: device.browser,
          os: device.os,
          device: device.device,
          lastLocation: device.lastLocation,
          trustScore: device.trustScore,
          riskScore: device.riskScore,
          isVerified: device.isVerified,
          isTrusted: device.isTrusted,
          isBlocked: device.isBlocked,
          lastSeenAt: device.lastSeenAt,
          useCount: device.useCount
        });
      }
    }
    
    return devices.sort((a, b) => b.lastSeenAt.getTime() - a.lastSeenAt.getTime());
  }

  getDeviceFingerprint(fingerprintId) {
    return this.deviceFingerprints.get(fingerprintId);
  }

  getDeviceSessions(deviceId) {
    return Array.from(this.deviceSessions.values())
      .filter(session => session.deviceId === deviceId)
      .sort((a, b) => b.startedAt.getTime() - a.startedAt.getTime());
  }

  // Cleanup
  setupCleanupInterval() {
    // Clean up old fingerprints and sessions every hour
    setInterval(() => {
      this.cleanupOldData();
    }, 3600000);
  }

  cleanupOldData() {
    const now = Date.now();
    const ttl = this.options.fingerprintTTL;
    
    // Clean up old fingerprints
    for (const [id, fingerprint] of this.deviceFingerprints) {
      if (now - fingerprint.createdAt.getTime() > ttl) {
        this.deviceFingerprints.delete(id);
      }
    }
    
    // Clean up old sessions
    for (const [id, session] of this.deviceSessions) {
      if (session.endedAt && now - session.endedAt.getTime() > ttl) {
        this.deviceSessions.delete(id);
      }
    }
  }

  // Statistics and Monitoring
  getStats() {
    const stats = {
      totalFingerprints: this.deviceFingerprints.size,
      totalDevices: this.deviceRecords ? this.deviceRecords.size : 0,
      totalUsers: this.userDevices.size,
      activeSessions: Array.from(this.deviceSessions.values())
        .filter(s => !s.endedAt).length,
      behavioralProfiles: this.behavioralProfiles.size,
      
      // Risk distribution
      riskDistribution: {
        low: 0,
        medium: 0,
        high: 0
      },
      
      // Browser distribution
      browsers: {},
      
      // OS distribution
      operatingSystems: {},
      
      // Location distribution
      countries: {}
    };
    
    // Calculate risk distribution
    for (const fingerprint of this.deviceFingerprints.values()) {
      if (fingerprint.riskScore < 0.3) {
        stats.riskDistribution.low++;
      } else if (fingerprint.riskScore < 0.7) {
        stats.riskDistribution.medium++;
      } else {
        stats.riskDistribution.high++;
      }
      
      // Count browsers
      const browserName = fingerprint.components.browser.name;
      stats.browsers[browserName] = (stats.browsers[browserName] || 0) + 1;
      
      // Count OS
      const osName = fingerprint.components.os.name;
      stats.operatingSystems[osName] = (stats.operatingSystems[osName] || 0) + 1;
      
      // Count countries
      if (fingerprint.components.location) {
        const country = fingerprint.components.location.country;
        stats.countries[country] = (stats.countries[country] || 0) + 1;
      }
    }
    
    return stats;
  }

  reset() {
    this.deviceFingerprints.clear();
    this.userDevices.clear();
    this.deviceSessions.clear();
    this.behavioralProfiles.clear();
    this.riskAssessments.clear();
    this.deviceReports.clear();
    
    if (this.deviceRecords) {
      this.deviceRecords.clear();
    }
  }
}

module.exports = DeviceFingerprinting;