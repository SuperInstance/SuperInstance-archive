const crypto = require('crypto');
const { EventEmitter } = require('events');

class APIKeyManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      keyLength: options.keyLength || 32,
      secretLength: options.secretLength || 64,
      defaultExpiration: options.defaultExpiration || 31536000000, // 1 year
      maxKeysPerUser: options.maxKeysPerUser || 50,
      maxKeysPerService: options.maxKeysPerService || 100,
      enableRotation: options.enableRotation !== false,
      rotationWarningDays: options.rotationWarningDays || 30,
      enableRateTracking: options.enableRateTracking !== false,
      ...options
    };
    
    this.apiKeys = new Map();
    this.keysByUser = new Map();
    this.keysByService = new Map();
    this.keyScopes = new Map();
    this.keyUsageStats = new Map();
    this.keyRotationSchedule = new Map();
    this.revokedKeys = new Map();
    
    this.setupRotationScheduler();
  }

  // API Key Creation
  async createAPIKey(keyData) {
    const {
      name,
      description,
      userId,
      serviceId,
      scopes = [],
      permissions = [],
      restrictions = {},
      expiresAt,
      metadata = {}
    } = keyData;
    
    // Validate limits
    await this.validateKeyLimits(userId, serviceId);
    
    const keyId = this.generateKeyId();
    const keyValue = this.generateKeyValue();
    const secretValue = this.generateSecretValue();
    
    const apiKey = {
      id: keyId,
      name,
      description,
      
      // Key credentials
      key: keyValue,
      secret: secretValue,
      keyHash: this.hashKey(keyValue),
      secretHash: this.hashSecret(secretValue),
      
      // Ownership
      userId,
      serviceId,
      
      // Permissions and scopes
      scopes: Array.isArray(scopes) ? scopes : [],
      permissions: Array.isArray(permissions) ? permissions : [],
      
      // Restrictions
      restrictions: {
        ipWhitelist: restrictions.ipWhitelist || [],
        refererWhitelist: restrictions.refererWhitelist || [],
        rateLimit: restrictions.rateLimit || { requests: 1000, window: 3600000 }, // 1000/hour
        allowedMethods: restrictions.allowedMethods || ['GET', 'POST', 'PUT', 'DELETE'],
        allowedEndpoints: restrictions.allowedEndpoints || [],
        ...restrictions
      },
      
      // Lifecycle
      createdAt: new Date(),
      updatedAt: new Date(),
      lastUsedAt: null,
      expiresAt: expiresAt || new Date(Date.now() + this.options.defaultExpiration),
      
      // Status
      isActive: true,
      isRevoked: false,
      revokedAt: null,
      revokedReason: null,
      
      // Metadata
      metadata,
      
      // Usage tracking
      usage: {
        totalRequests: 0,
        successfulRequests: 0,
        failedRequests: 0,
        lastRequestAt: null,
        dailyUsage: {},
        monthlyUsage: {}
      },
      
      // Security
      rotationSchedule: restrictions.autoRotate ? {
        enabled: true,
        intervalDays: restrictions.rotationIntervalDays || 90,
        nextRotationAt: new Date(Date.now() + (restrictions.rotationIntervalDays || 90) * 24 * 60 * 60 * 1000),
        notificationSent: false
      } : null
    };
    
    // Store the key
    this.apiKeys.set(keyId, apiKey);
    
    // Index by user and service
    this.indexKeyByUser(userId, keyId);
    this.indexKeyByService(serviceId, keyId);
    
    // Store scopes
    this.keyScopes.set(keyId, new Set(scopes));
    
    // Initialize usage stats
    if (this.options.enableRateTracking) {
      this.keyUsageStats.set(keyId, {
        currentWindow: {},
        windows: [],
        violations: []
      });
    }
    
    // Schedule rotation if enabled
    if (apiKey.rotationSchedule) {
      this.scheduleKeyRotation(keyId, apiKey.rotationSchedule.nextRotationAt);
    }
    
    this.emit('apiKeyCreated', {
      keyId,
      userId,
      serviceId,
      name,
      scopes: apiKey.scopes
    });
    
    // Return key with plain text credentials (only time they're visible)
    return {
      ...apiKey,
      key: keyValue,
      secret: secretValue,
      // Remove hashed versions from response
      keyHash: undefined,
      secretHash: undefined
    };
  }

  // API Key Validation
  async validateAPIKey(key, secret = null, context = {}) {
    const keyHash = this.hashKey(key);
    const apiKey = this.findKeyByHash(keyHash);
    
    if (!apiKey) {
      this.recordKeyAttempt(key, false, 'key_not_found', context);
      return { valid: false, reason: 'Invalid API key' };
    }
    
    // Check if key is revoked
    if (apiKey.isRevoked) {
      this.recordKeyAttempt(key, false, 'key_revoked', context);
      return { valid: false, reason: 'API key has been revoked' };
    }
    
    // Check if key is active
    if (!apiKey.isActive) {
      this.recordKeyAttempt(key, false, 'key_inactive', context);
      return { valid: false, reason: 'API key is not active' };
    }
    
    // Check expiration
    if (apiKey.expiresAt && apiKey.expiresAt < new Date()) {
      this.recordKeyAttempt(key, false, 'key_expired', context);
      return { valid: false, reason: 'API key has expired' };
    }
    
    // Validate secret if provided
    if (secret) {
      const secretHash = this.hashSecret(secret);
      if (apiKey.secretHash !== secretHash) {
        this.recordKeyAttempt(key, false, 'invalid_secret', context);
        return { valid: false, reason: 'Invalid API secret' };
      }
    }
    
    // Check IP restrictions
    if (context.ip && apiKey.restrictions.ipWhitelist.length > 0) {
      if (!this.isIPAllowed(context.ip, apiKey.restrictions.ipWhitelist)) {
        this.recordKeyAttempt(key, false, 'ip_not_allowed', context);
        return { valid: false, reason: 'IP address not allowed' };
      }
    }
    
    // Check referer restrictions
    if (context.referer && apiKey.restrictions.refererWhitelist.length > 0) {
      if (!this.isRefererAllowed(context.referer, apiKey.restrictions.refererWhitelist)) {
        this.recordKeyAttempt(key, false, 'referer_not_allowed', context);
        return { valid: false, reason: 'Referer not allowed' };
      }
    }
    
    // Check method restrictions
    if (context.method && apiKey.restrictions.allowedMethods.length > 0) {
      if (!apiKey.restrictions.allowedMethods.includes(context.method.toUpperCase())) {
        this.recordKeyAttempt(key, false, 'method_not_allowed', context);
        return { valid: false, reason: 'HTTP method not allowed' };
      }
    }
    
    // Check endpoint restrictions
    if (context.endpoint && apiKey.restrictions.allowedEndpoints.length > 0) {
      if (!this.isEndpointAllowed(context.endpoint, apiKey.restrictions.allowedEndpoints)) {
        this.recordKeyAttempt(key, false, 'endpoint_not_allowed', context);
        return { valid: false, reason: 'Endpoint not allowed' };
      }
    }
    
    // Check rate limits
    if (this.options.enableRateTracking) {
      const rateLimitResult = await this.checkRateLimit(apiKey.id, context);
      if (!rateLimitResult.allowed) {
        this.recordKeyAttempt(key, false, 'rate_limit_exceeded', context);
        return { 
          valid: false, 
          reason: 'Rate limit exceeded',
          retryAfter: rateLimitResult.retryAfter
        };
      }
    }
    
    // Update usage stats
    await this.updateKeyUsage(apiKey.id, context);
    
    this.recordKeyAttempt(key, true, 'success', context);
    
    return {
      valid: true,
      apiKey: {
        id: apiKey.id,
        name: apiKey.name,
        userId: apiKey.userId,
        serviceId: apiKey.serviceId,
        scopes: apiKey.scopes,
        permissions: apiKey.permissions,
        restrictions: apiKey.restrictions
      }
    };
  }

  // API Key Management
  async updateAPIKey(keyId, updates) {
    const apiKey = this.apiKeys.get(keyId);
    if (!apiKey) {
      throw new Error(`API key ${keyId} not found`);
    }
    
    if (apiKey.isRevoked) {
      throw new Error('Cannot update revoked API key');
    }
    
    const updatedKey = {
      ...apiKey,
      ...updates,
      updatedAt: new Date()
    };
    
    // Handle scope updates
    if (updates.scopes) {
      this.keyScopes.set(keyId, new Set(updates.scopes));
    }
    
    // Handle rotation schedule updates
    if (updates.rotationSchedule !== undefined) {
      if (updates.rotationSchedule) {
        this.scheduleKeyRotation(keyId, updates.rotationSchedule.nextRotationAt);
      } else {
        this.unscheduleKeyRotation(keyId);
      }
    }
    
    this.apiKeys.set(keyId, updatedKey);
    
    this.emit('apiKeyUpdated', {
      keyId,
      userId: updatedKey.userId,
      changes: Object.keys(updates)
    });
    
    return updatedKey;
  }

  async revokeAPIKey(keyId, reason = 'Manual revocation', userId = null) {
    const apiKey = this.apiKeys.get(keyId);
    if (!apiKey) {
      throw new Error(`API key ${keyId} not found`);
    }
    
    if (apiKey.isRevoked) {
      return apiKey; // Already revoked
    }
    
    const revokedKey = {
      ...apiKey,
      isActive: false,
      isRevoked: true,
      revokedAt: new Date(),
      revokedReason: reason,
      revokedBy: userId,
      updatedAt: new Date()
    };
    
    this.apiKeys.set(keyId, revokedKey);
    
    // Add to revoked keys index
    this.revokedKeys.set(keyId, revokedKey);
    
    // Unschedule rotation
    this.unscheduleKeyRotation(keyId);
    
    this.emit('apiKeyRevoked', {
      keyId,
      userId: revokedKey.userId,
      reason,
      revokedBy: userId
    });
    
    return revokedKey;
  }

  async deleteAPIKey(keyId, userId = null) {
    const apiKey = this.apiKeys.get(keyId);
    if (!apiKey) {
      throw new Error(`API key ${keyId} not found`);
    }
    
    // Remove from all indexes
    this.apiKeys.delete(keyId);
    this.keyScopes.delete(keyId);
    this.keyUsageStats.delete(keyId);
    
    // Remove from user index
    if (this.keysByUser.has(apiKey.userId)) {
      const userKeys = this.keysByUser.get(apiKey.userId);
      userKeys.delete(keyId);
      if (userKeys.size === 0) {
        this.keysByUser.delete(apiKey.userId);
      }
    }
    
    // Remove from service index
    if (apiKey.serviceId && this.keysByService.has(apiKey.serviceId)) {
      const serviceKeys = this.keysByService.get(apiKey.serviceId);
      serviceKeys.delete(keyId);
      if (serviceKeys.size === 0) {
        this.keysByService.delete(apiKey.serviceId);
      }
    }
    
    // Unschedule rotation
    this.unscheduleKeyRotation(keyId);
    
    this.emit('apiKeyDeleted', {
      keyId,
      userId: apiKey.userId,
      deletedBy: userId
    });
    
    return true;
  }

  // API Key Rotation
  async rotateAPIKey(keyId, keepOldKey = false) {
    const apiKey = this.apiKeys.get(keyId);
    if (!apiKey) {
      throw new Error(`API key ${keyId} not found`);
    }
    
    if (apiKey.isRevoked) {
      throw new Error('Cannot rotate revoked API key');
    }
    
    const newKeyValue = this.generateKeyValue();
    const newSecretValue = this.generateSecretValue();
    
    const rotatedKey = {
      ...apiKey,
      key: undefined, // Will be returned in response only
      secret: undefined, // Will be returned in response only
      keyHash: this.hashKey(newKeyValue),
      secretHash: this.hashSecret(newSecretValue),
      updatedAt: new Date(),
      lastRotatedAt: new Date(),
      rotationCount: (apiKey.rotationCount || 0) + 1
    };
    
    // Update rotation schedule if enabled
    if (rotatedKey.rotationSchedule) {
      rotatedKey.rotationSchedule.nextRotationAt = new Date(
        Date.now() + rotatedKey.rotationSchedule.intervalDays * 24 * 60 * 60 * 1000
      );
      rotatedKey.rotationSchedule.notificationSent = false;
      this.scheduleKeyRotation(keyId, rotatedKey.rotationSchedule.nextRotationAt);
    }
    
    // If keeping old key, create a deprecated version
    if (keepOldKey) {
      const deprecatedKeyId = `${keyId}_deprecated_${Date.now()}`;
      const deprecatedKey = {
        ...apiKey,
        id: deprecatedKeyId,
        name: `${apiKey.name} (Deprecated)`,
        isDeprecated: true,
        deprecatedAt: new Date(),
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days grace period
        parentKeyId: keyId
      };
      
      this.apiKeys.set(deprecatedKeyId, deprecatedKey);
    }
    
    this.apiKeys.set(keyId, rotatedKey);
    
    this.emit('apiKeyRotated', {
      keyId,
      userId: rotatedKey.userId,
      keepOldKey,
      rotationCount: rotatedKey.rotationCount
    });
    
    // Return new credentials
    return {
      ...rotatedKey,
      key: newKeyValue,
      secret: newSecretValue
    };
  }

  // Scope and Permission Management
  async addScope(keyId, scope) {
    const apiKey = this.apiKeys.get(keyId);
    if (!apiKey) {
      throw new Error(`API key ${keyId} not found`);
    }
    
    const scopes = this.keyScopes.get(keyId) || new Set();
    scopes.add(scope);
    this.keyScopes.set(keyId, scopes);
    
    const updatedKey = {
      ...apiKey,
      scopes: Array.from(scopes),
      updatedAt: new Date()
    };
    
    this.apiKeys.set(keyId, updatedKey);
    
    this.emit('apiKeyScopeAdded', { keyId, scope, userId: apiKey.userId });
    return updatedKey;
  }

  async removeScope(keyId, scope) {
    const apiKey = this.apiKeys.get(keyId);
    if (!apiKey) {
      throw new Error(`API key ${keyId} not found`);
    }
    
    const scopes = this.keyScopes.get(keyId) || new Set();
    scopes.delete(scope);
    this.keyScopes.set(keyId, scopes);
    
    const updatedKey = {
      ...apiKey,
      scopes: Array.from(scopes),
      updatedAt: new Date()
    };
    
    this.apiKeys.set(keyId, updatedKey);
    
    this.emit('apiKeyScopeRemoved', { keyId, scope, userId: apiKey.userId });
    return updatedKey;
  }

  async hasScope(keyId, scope) {
    const scopes = this.keyScopes.get(keyId);
    return scopes ? scopes.has(scope) : false;
  }

  async hasPermission(keyId, permission) {
    const apiKey = this.apiKeys.get(keyId);
    if (!apiKey) {
      return false;
    }
    
    return apiKey.permissions.includes(permission);
  }

  // Rate Limiting
  async checkRateLimit(keyId, context = {}) {
    const apiKey = this.apiKeys.get(keyId);
    if (!apiKey || !apiKey.restrictions.rateLimit) {
      return { allowed: true };
    }
    
    const rateLimit = apiKey.restrictions.rateLimit;
    const usageStats = this.keyUsageStats.get(keyId);
    
    if (!usageStats) {
      return { allowed: true };
    }
    
    const now = Date.now();
    const windowStart = now - rateLimit.window;
    
    // Count requests in current window
    let requestsInWindow = 0;
    for (const timestamp of usageStats.windows) {
      if (timestamp > windowStart) {
        requestsInWindow++;
      }
    }
    
    if (requestsInWindow >= rateLimit.requests) {
      // Find when the oldest request in current window will expire
      const oldestInWindow = Math.min(...usageStats.windows.filter(t => t > windowStart));
      const retryAfter = Math.ceil((oldestInWindow + rateLimit.window - now) / 1000);
      
      // Record rate limit violation
      usageStats.violations.push({
        timestamp: now,
        requestsInWindow,
        limit: rateLimit.requests,
        context
      });
      
      return {
        allowed: false,
        retryAfter,
        limit: rateLimit.requests,
        windowMs: rateLimit.window,
        requestsInWindow
      };
    }
    
    return { allowed: true };
  }

  async updateKeyUsage(keyId, context = {}) {
    const apiKey = this.apiKeys.get(keyId);
    if (!apiKey) {
      return;
    }
    
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    const month = now.toISOString().substring(0, 7);
    
    // Update API key usage stats
    apiKey.usage.totalRequests++;
    apiKey.usage.lastRequestAt = now;
    apiKey.lastUsedAt = now;
    
    if (context.success !== false) {
      apiKey.usage.successfulRequests++;
    } else {
      apiKey.usage.failedRequests++;
    }
    
    // Update daily usage
    apiKey.usage.dailyUsage[today] = (apiKey.usage.dailyUsage[today] || 0) + 1;
    
    // Update monthly usage
    apiKey.usage.monthlyUsage[month] = (apiKey.usage.monthlyUsage[month] || 0) + 1;
    
    // Update rate limiting stats
    if (this.options.enableRateTracking) {
      const usageStats = this.keyUsageStats.get(keyId);
      if (usageStats) {
        usageStats.windows.push(now.getTime());
        
        // Clean old timestamps
        const windowStart = now.getTime() - (apiKey.restrictions.rateLimit?.window || 3600000);
        usageStats.windows = usageStats.windows.filter(timestamp => timestamp > windowStart);
      }
    }
    
    this.apiKeys.set(keyId, apiKey);
    
    this.emit('apiKeyUsed', {
      keyId,
      userId: apiKey.userId,
      context,
      timestamp: now
    });
  }

  // Query and Retrieval
  getAPIKey(keyId) {
    const apiKey = this.apiKeys.get(keyId);
    if (!apiKey) {
      return null;
    }
    
    // Return without sensitive data
    return {
      ...apiKey,
      keyHash: undefined,
      secretHash: undefined
    };
  }

  getUserAPIKeys(userId, includeRevoked = false) {
    const userKeyIds = this.keysByUser.get(userId) || new Set();
    const keys = [];
    
    for (const keyId of userKeyIds) {
      const apiKey = this.apiKeys.get(keyId);
      if (apiKey && (includeRevoked || !apiKey.isRevoked)) {
        keys.push({
          ...apiKey,
          keyHash: undefined,
          secretHash: undefined
        });
      }
    }
    
    return keys.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
  }

  getServiceAPIKeys(serviceId, includeRevoked = false) {
    const serviceKeyIds = this.keysByService.get(serviceId) || new Set();
    const keys = [];
    
    for (const keyId of serviceKeyIds) {
      const apiKey = this.apiKeys.get(keyId);
      if (apiKey && (includeRevoked || !apiKey.isRevoked)) {
        keys.push({
          ...apiKey,
          keyHash: undefined,
          secretHash: undefined
        });
      }
    }
    
    return keys.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
  }

  getAllAPIKeys(filters = {}) {
    let keys = Array.from(this.apiKeys.values());
    
    if (filters.userId) {
      keys = keys.filter(key => key.userId === filters.userId);
    }
    
    if (filters.serviceId) {
      keys = keys.filter(key => key.serviceId === filters.serviceId);
    }
    
    if (filters.isActive !== undefined) {
      keys = keys.filter(key => key.isActive === filters.isActive);
    }
    
    if (filters.isRevoked !== undefined) {
      keys = keys.filter(key => key.isRevoked === filters.isRevoked);
    }
    
    if (filters.scope) {
      keys = keys.filter(key => key.scopes.includes(filters.scope));
    }
    
    if (filters.expiresAfter) {
      keys = keys.filter(key => !key.expiresAt || key.expiresAt > filters.expiresAfter);
    }
    
    if (filters.expiresBefore) {
      keys = keys.filter(key => key.expiresAt && key.expiresAt < filters.expiresBefore);
    }
    
    return keys.map(key => ({
      ...key,
      keyHash: undefined,
      secretHash: undefined
    }));
  }

  // Analytics and Reporting
  getKeyUsageAnalytics(keyId, timeRange = 30) {
    const apiKey = this.apiKeys.get(keyId);
    if (!apiKey) {
      throw new Error(`API key ${keyId} not found`);
    }
    
    const now = new Date();
    const startDate = new Date(now.getTime() - timeRange * 24 * 60 * 60 * 1000);
    
    const analytics = {
      keyId,
      timeRange,
      totalRequests: apiKey.usage.totalRequests,
      successfulRequests: apiKey.usage.successfulRequests,
      failedRequests: apiKey.usage.failedRequests,
      successRate: apiKey.usage.totalRequests > 0 
        ? (apiKey.usage.successfulRequests / apiKey.usage.totalRequests) * 100 
        : 0,
      
      // Daily breakdown
      dailyUsage: {},
      
      // Rate limit violations
      recentViolations: []
    };
    
    // Calculate daily usage for the time range
    for (let i = 0; i < timeRange; i++) {
      const date = new Date(startDate.getTime() + i * 24 * 60 * 60 * 1000);
      const dateStr = date.toISOString().split('T')[0];
      analytics.dailyUsage[dateStr] = apiKey.usage.dailyUsage[dateStr] || 0;
    }
    
    // Get recent rate limit violations
    const usageStats = this.keyUsageStats.get(keyId);
    if (usageStats) {
      const recentTime = now.getTime() - (timeRange * 24 * 60 * 60 * 1000);
      analytics.recentViolations = usageStats.violations
        .filter(v => v.timestamp > recentTime)
        .sort((a, b) => b.timestamp - a.timestamp);
    }
    
    return analytics;
  }

  getGlobalAnalytics() {
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    let totalKeys = 0;
    let activeKeys = 0;
    let revokedKeys = 0;
    let expiredKeys = 0;
    let totalRequests = 0;
    let recentlyUsedKeys = 0;
    
    for (const apiKey of this.apiKeys.values()) {
      totalKeys++;
      
      if (apiKey.isRevoked) {
        revokedKeys++;
      } else if (apiKey.expiresAt && apiKey.expiresAt < now) {
        expiredKeys++;
      } else if (apiKey.isActive) {
        activeKeys++;
      }
      
      totalRequests += apiKey.usage.totalRequests;
      
      if (apiKey.lastUsedAt && apiKey.lastUsedAt > thirtyDaysAgo) {
        recentlyUsedKeys++;
      }
    }
    
    return {
      totalKeys,
      activeKeys,
      revokedKeys,
      expiredKeys,
      totalRequests,
      recentlyUsedKeys,
      keysScheduledForRotation: this.keyRotationSchedule.size
    };
  }

  // Utility Methods
  findKeyByHash(keyHash) {
    for (const apiKey of this.apiKeys.values()) {
      if (apiKey.keyHash === keyHash) {
        return apiKey;
      }
    }
    return null;
  }

  async validateKeyLimits(userId, serviceId) {
    if (userId) {
      const userKeys = this.keysByUser.get(userId);
      if (userKeys && userKeys.size >= this.options.maxKeysPerUser) {
        throw new Error(`Maximum API keys limit reached for user (${this.options.maxKeysPerUser})`);
      }
    }
    
    if (serviceId) {
      const serviceKeys = this.keysByService.get(serviceId);
      if (serviceKeys && serviceKeys.size >= this.options.maxKeysPerService) {
        throw new Error(`Maximum API keys limit reached for service (${this.options.maxKeysPerService})`);
      }
    }
  }

  indexKeyByUser(userId, keyId) {
    if (!this.keysByUser.has(userId)) {
      this.keysByUser.set(userId, new Set());
    }
    this.keysByUser.get(userId).add(keyId);
  }

  indexKeyByService(serviceId, keyId) {
    if (!serviceId) return;
    
    if (!this.keysByService.has(serviceId)) {
      this.keysByService.set(serviceId, new Set());
    }
    this.keysByService.get(serviceId).add(keyId);
  }

  generateKeyId() {
    return `ak_${Date.now()}_${crypto.randomBytes(8).toString('hex')}`;
  }

  generateKeyValue() {
    return `ak_${crypto.randomBytes(this.options.keyLength).toString('hex')}`;
  }

  generateSecretValue() {
    return crypto.randomBytes(this.options.secretLength).toString('hex');
  }

  hashKey(key) {
    return crypto.createHash('sha256').update(key).digest('hex');
  }

  hashSecret(secret) {
    return crypto.createHash('sha256').update(secret).digest('hex');
  }

  isIPAllowed(ip, whitelist) {
    return whitelist.some(allowedIP => {
      if (allowedIP.includes('/')) {
        // CIDR notation
        return this.isIPInCIDR(ip, allowedIP);
      } else {
        // Exact match or wildcard
        return ip === allowedIP || allowedIP === '*';
      }
    });
  }

  isIPInCIDR(ip, cidr) {
    // Simplified CIDR check - in production use a proper library
    const [network, bits] = cidr.split('/');
    const networkParts = network.split('.').map(n => parseInt(n));
    const ipParts = ip.split('.').map(n => parseInt(n));
    const mask = ~(Math.pow(2, 32 - parseInt(bits)) - 1);
    
    const networkNum = (networkParts[0] << 24) + (networkParts[1] << 16) + (networkParts[2] << 8) + networkParts[3];
    const ipNum = (ipParts[0] << 24) + (ipParts[1] << 16) + (ipParts[2] << 8) + ipParts[3];
    
    return (networkNum & mask) === (ipNum & mask);
  }

  isRefererAllowed(referer, whitelist) {
    return whitelist.some(allowedReferer => {
      if (allowedReferer === '*') return true;
      if (allowedReferer.startsWith('*')) {
        return referer.endsWith(allowedReferer.substring(1));
      }
      return referer === allowedReferer;
    });
  }

  isEndpointAllowed(endpoint, whitelist) {
    return whitelist.some(allowedEndpoint => {
      if (allowedEndpoint === '*') return true;
      if (allowedEndpoint.includes('*')) {
        const regex = new RegExp(allowedEndpoint.replace(/\*/g, '.*'));
        return regex.test(endpoint);
      }
      return endpoint === allowedEndpoint;
    });
  }

  recordKeyAttempt(key, success, reason, context) {
    // This could be used for security monitoring
    this.emit('keyAttempt', {
      keyHash: this.hashKey(key),
      success,
      reason,
      context,
      timestamp: new Date()
    });
  }

  // Rotation Scheduling
  setupRotationScheduler() {
    if (!this.options.enableRotation) return;
    
    // Check for keys needing rotation every hour
    setInterval(() => {
      this.checkRotationSchedule();
    }, 60 * 60 * 1000);
    
    // Check for keys needing rotation warning every day
    setInterval(() => {
      this.checkRotationWarnings();
    }, 24 * 60 * 60 * 1000);
  }

  scheduleKeyRotation(keyId, nextRotationAt) {
    this.keyRotationSchedule.set(keyId, nextRotationAt);
  }

  unscheduleKeyRotation(keyId) {
    this.keyRotationSchedule.delete(keyId);
  }

  checkRotationSchedule() {
    const now = new Date();
    
    for (const [keyId, rotationTime] of this.keyRotationSchedule) {
      if (rotationTime <= now) {
        this.emit('keyRotationDue', { keyId, scheduledTime: rotationTime });
        
        // Auto-rotate if configured
        const apiKey = this.apiKeys.get(keyId);
        if (apiKey && apiKey.rotationSchedule && apiKey.rotationSchedule.enabled) {
          this.rotateAPIKey(keyId, true).catch(error => {
            this.emit('keyRotationError', { keyId, error: error.message });
          });
        }
      }
    }
  }

  checkRotationWarnings() {
    const now = new Date();
    const warningTime = new Date(now.getTime() + this.options.rotationWarningDays * 24 * 60 * 60 * 1000);
    
    for (const [keyId, rotationTime] of this.keyRotationSchedule) {
      if (rotationTime <= warningTime) {
        const apiKey = this.apiKeys.get(keyId);
        
        if (apiKey && apiKey.rotationSchedule && !apiKey.rotationSchedule.notificationSent) {
          this.emit('keyRotationWarning', {
            keyId,
            userId: apiKey.userId,
            scheduledTime: rotationTime,
            daysRemaining: Math.ceil((rotationTime.getTime() - now.getTime()) / (24 * 60 * 60 * 1000))
          });
          
          // Mark notification as sent
          apiKey.rotationSchedule.notificationSent = true;
          this.apiKeys.set(keyId, apiKey);
        }
      }
    }
  }

  // Statistics and Monitoring
  getStats() {
    return {
      totalKeys: this.apiKeys.size,
      keysByUser: this.keysByUser.size,
      keysByService: this.keysByService.size,
      revokedKeys: this.revokedKeys.size,
      scheduledRotations: this.keyRotationSchedule.size
    };
  }

  reset() {
    this.apiKeys.clear();
    this.keysByUser.clear();
    this.keysByService.clear();
    this.keyScopes.clear();
    this.keyUsageStats.clear();
    this.keyRotationSchedule.clear();
    this.revokedKeys.clear();
  }
}

module.exports = APIKeyManager;