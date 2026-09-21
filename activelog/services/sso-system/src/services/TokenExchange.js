const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const { EventEmitter } = require('events');

class TokenExchange extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      jwtSecret: options.jwtSecret || process.env.JWT_SECRET || 'sso-secret-key',
      issuer: options.issuer || 'https://sso.activelog.com',
      defaultTokenLifetime: options.defaultTokenLifetime || 3600, // 1 hour
      maxTokenLifetime: options.maxTokenLifetime || 86400, // 24 hours
      allowedAudiences: options.allowedAudiences || [],
      trustedIssuers: options.trustedIssuers || [],
      ...options
    };
    
    this.exchangeRules = new Map();
    this.exchangeHistory = [];
    this.serviceKeys = new Map();
    this.trustedServices = new Map();
    
    this.setupDefaultRules();
  }

  // Token Exchange (RFC 8693) Implementation
  async exchangeToken(request) {
    const {
      grant_type,
      subject_token,
      subject_token_type,
      actor_token,
      actor_token_type,
      resource,
      audience,
      scope,
      requested_token_type
    } = request;
    
    // Validate grant type
    if (grant_type !== 'urn:ietf:params:oauth:grant-type:token-exchange') {
      throw new Error('Invalid grant type');
    }
    
    // Validate subject token
    const subjectTokenInfo = await this.validateToken(subject_token, subject_token_type);
    if (!subjectTokenInfo.valid) {
      throw new Error(`Invalid subject token: ${subjectTokenInfo.reason}`);
    }
    
    // Validate actor token if present
    let actorTokenInfo = null;
    if (actor_token) {
      actorTokenInfo = await this.validateToken(actor_token, actor_token_type);
      if (!actorTokenInfo.valid) {
        throw new Error(`Invalid actor token: ${actorTokenInfo.reason}`);
      }
    }
    
    // Check exchange rules
    const canExchange = await this.checkExchangeRules({
      subjectToken: subjectTokenInfo,
      actorToken: actorTokenInfo,
      targetAudience: audience,
      targetResource: resource,
      requestedScopes: scope ? scope.split(' ') : []
    });
    
    if (!canExchange.allowed) {
      throw new Error(`Token exchange not allowed: ${canExchange.reason}`);
    }
    
    // Generate new token
    const newToken = await this.generateExchangedToken({
      subjectToken: subjectTokenInfo,
      actorToken: actorTokenInfo,
      targetAudience: audience,
      targetResource: resource,
      requestedScopes: scope ? scope.split(' ') : [],
      requestedTokenType: requested_token_type
    });
    
    // Log the exchange
    await this.logTokenExchange({
      subjectToken: subjectTokenInfo.payload.jti || 'unknown',
      actorToken: actorTokenInfo?.payload.jti || null,
      newTokenId: newToken.jti,
      audience,
      resource,
      scope,
      timestamp: new Date(),
      clientId: request.client_id
    });
    
    this.emit('tokenExchanged', {
      subjectToken: subjectTokenInfo.payload.sub,
      newToken: newToken.jti,
      audience,
      scope
    });
    
    return {
      access_token: newToken.token,
      issued_token_type: requested_token_type || 'urn:ietf:params:oauth:token-type:access_token',
      token_type: 'Bearer',
      expires_in: newToken.expiresIn,
      scope: newToken.scope,
      resource: resource
    };
  }

  // Service-to-Service Token Exchange
  async exchangeForService(sourceToken, targetService, options = {}) {
    const sourceTokenInfo = await this.validateToken(sourceToken);
    if (!sourceTokenInfo.valid) {
      throw new Error('Invalid source token');
    }
    
    const targetServiceInfo = this.trustedServices.get(targetService);
    if (!targetServiceInfo) {
      throw new Error('Unknown target service');
    }
    
    // Check if exchange is allowed
    const canExchange = await this.canExchangeForService(
      sourceTokenInfo.payload,
      targetService,
      options.requestedScopes || []
    );
    
    if (!canExchange) {
      throw new Error('Service token exchange not allowed');
    }
    
    // Generate service token
    const serviceToken = await this.generateServiceToken({
      sourceToken: sourceTokenInfo.payload,
      targetService: targetServiceInfo,
      scopes: options.requestedScopes || [],
      lifetime: options.lifetime || this.options.defaultTokenLifetime
    });
    
    this.emit('serviceTokenExchanged', {
      sourceUser: sourceTokenInfo.payload.sub,
      targetService,
      tokenId: serviceToken.jti
    });
    
    return serviceToken;
  }

  // Impersonation Token Exchange
  async impersonateUser(actorToken, targetUserId, options = {}) {
    const actorTokenInfo = await this.validateToken(actorToken);
    if (!actorTokenInfo.valid) {
      throw new Error('Invalid actor token');
    }
    
    // Check if actor has impersonation rights
    const canImpersonate = await this.canImpersonate(
      actorTokenInfo.payload,
      targetUserId,
      options.scopes || []
    );
    
    if (!canImpersonate.allowed) {
      throw new Error(`Impersonation not allowed: ${canImpersonate.reason}`);
    }
    
    // Get target user info (this would typically come from a user service)
    const targetUser = await this.getUserInfo(targetUserId);
    if (!targetUser) {
      throw new Error('Target user not found');
    }
    
    // Generate impersonation token
    const impersonationToken = await this.generateImpersonationToken({
      actor: actorTokenInfo.payload,
      targetUser,
      scopes: options.scopes || [],
      lifetime: options.lifetime || this.options.defaultTokenLifetime,
      audience: options.audience
    });
    
    // Log impersonation
    await this.logImpersonation({
      actorId: actorTokenInfo.payload.sub,
      targetUserId,
      tokenId: impersonationToken.jti,
      timestamp: new Date(),
      reason: options.reason
    });
    
    this.emit('userImpersonated', {
      actor: actorTokenInfo.payload.sub,
      target: targetUserId,
      tokenId: impersonationToken.jti
    });
    
    return impersonationToken;
  }

  // Cross-Domain Token Exchange
  async exchangeForDomain(sourceToken, targetDomain, options = {}) {
    const sourceTokenInfo = await this.validateToken(sourceToken);
    if (!sourceTokenInfo.valid) {
      throw new Error('Invalid source token');
    }
    
    // Check if domain exchange is allowed
    const canExchange = await this.canExchangeForDomain(
      sourceTokenInfo.payload,
      targetDomain
    );
    
    if (!canExchange) {
      throw new Error('Cross-domain exchange not allowed');
    }
    
    // Generate domain-specific token
    const domainToken = await this.generateDomainToken({
      sourceToken: sourceTokenInfo.payload,
      targetDomain,
      scopes: options.scopes || sourceTokenInfo.payload.scope?.split(' ') || [],
      lifetime: options.lifetime || 300 // Short-lived for security
    });
    
    this.emit('domainTokenExchanged', {
      sourceUser: sourceTokenInfo.payload.sub,
      targetDomain,
      tokenId: domainToken.jti
    });
    
    return domainToken;
  }

  // Token Validation
  async validateToken(token, tokenType = 'urn:ietf:params:oauth:token-type:access_token') {
    try {
      let payload;
      
      switch (tokenType) {
        case 'urn:ietf:params:oauth:token-type:access_token':
        case 'urn:ietf:params:oauth:token-type:jwt':
          payload = jwt.verify(token, this.options.jwtSecret, { algorithms: ['HS256'] });
          break;
          
        case 'urn:ietf:params:oauth:token-type:refresh_token':
          // Handle refresh token validation
          payload = await this.validateRefreshToken(token);
          break;
          
        case 'urn:ietf:params:oauth:token-type:id_token':
          payload = jwt.verify(token, this.options.jwtSecret, { algorithms: ['HS256'] });
          // Additional ID token validation
          if (!payload.aud || !payload.iss || !payload.sub) {
            throw new Error('Invalid ID token structure');
          }
          break;
          
        case 'urn:ietf:params:oauth:token-type:saml2':
          return await this.validateSAMLToken(token);
          
        default:
          throw new Error(`Unsupported token type: ${tokenType}`);
      }
      
      // Check token expiration
      if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) {
        return { valid: false, reason: 'Token expired' };
      }
      
      // Check issuer
      if (payload.iss && !this.isTrustedIssuer(payload.iss)) {
        return { valid: false, reason: 'Untrusted issuer' };
      }
      
      // Check audience
      if (payload.aud && !this.isAllowedAudience(payload.aud)) {
        return { valid: false, reason: 'Invalid audience' };
      }
      
      return { valid: true, payload, tokenType };
      
    } catch (error) {
      return { valid: false, reason: error.message };
    }
  }

  // Token Generation
  async generateExchangedToken(params) {
    const {
      subjectToken,
      actorToken,
      targetAudience,
      targetResource,
      requestedScopes,
      requestedTokenType
    } = params;
    
    const now = Math.floor(Date.now() / 1000);
    const tokenId = this.generateTokenId();
    const expiresIn = this.calculateTokenLifetime(requestedScopes);
    
    const payload = {
      iss: this.options.issuer,
      sub: subjectToken.payload.sub,
      aud: targetAudience || subjectToken.payload.aud,
      exp: now + expiresIn,
      iat: now,
      jti: tokenId,
      
      // Subject token claims
      email: subjectToken.payload.email,
      username: subjectToken.payload.username,
      roles: subjectToken.payload.roles || [],
      permissions: subjectToken.payload.permissions || [],
      
      // Exchange metadata
      token_exchange: {
        subject_token_type: subjectToken.tokenType,
        subject_issuer: subjectToken.payload.iss,
        actor_present: !!actorToken,
        exchange_time: now
      }
    };
    
    // Add actor information if present
    if (actorToken) {
      payload.act = {
        sub: actorToken.payload.sub,
        iss: actorToken.payload.iss
      };
    }
    
    // Add resource if specified
    if (targetResource) {
      payload.resource = targetResource;
    }
    
    // Add scopes
    if (requestedScopes.length > 0) {
      payload.scope = requestedScopes.join(' ');
    }
    
    const token = jwt.sign(payload, this.options.jwtSecret, { algorithm: 'HS256' });
    
    return {
      token,
      jti: tokenId,
      expiresIn,
      scope: payload.scope
    };
  }

  async generateServiceToken(params) {
    const { sourceToken, targetService, scopes, lifetime } = params;
    
    const now = Math.floor(Date.now() / 1000);
    const tokenId = this.generateTokenId();
    
    const payload = {
      iss: this.options.issuer,
      sub: sourceToken.sub,
      aud: targetService.clientId,
      exp: now + lifetime,
      iat: now,
      jti: tokenId,
      
      // User context
      email: sourceToken.email,
      username: sourceToken.username,
      roles: sourceToken.roles || [],
      
      // Service-specific claims
      scope: scopes.join(' '),
      service: targetService.name,
      
      // Token metadata
      token_type: 'service_access',
      original_token: sourceToken.jti || 'unknown'
    };
    
    const token = jwt.sign(payload, this.options.jwtSecret, { algorithm: 'HS256' });
    
    return {
      token,
      jti: tokenId,
      expiresIn: lifetime,
      scope: payload.scope,
      service: targetService.name
    };
  }

  async generateImpersonationToken(params) {
    const { actor, targetUser, scopes, lifetime, audience } = params;
    
    const now = Math.floor(Date.now() / 1000);
    const tokenId = this.generateTokenId();
    
    const payload = {
      iss: this.options.issuer,
      sub: targetUser.id.toString(),
      aud: audience || actor.aud,
      exp: now + lifetime,
      iat: now,
      jti: tokenId,
      
      // Target user claims
      email: targetUser.email,
      username: targetUser.username,
      roles: targetUser.roles || [],
      permissions: targetUser.permissions || [],
      
      // Impersonation metadata
      act: {
        sub: actor.sub,
        iss: actor.iss,
        impersonation_time: now
      },
      
      scope: scopes.join(' '),
      token_type: 'impersonation',
      
      // Mark as impersonation token
      imp: true
    };
    
    const token = jwt.sign(payload, this.options.jwtSecret, { algorithm: 'HS256' });
    
    return {
      token,
      jti: tokenId,
      expiresIn: lifetime,
      scope: payload.scope,
      impersonatedUser: targetUser.id
    };
  }

  async generateDomainToken(params) {
    const { sourceToken, targetDomain, scopes, lifetime } = params;
    
    const now = Math.floor(Date.now() / 1000);
    const tokenId = this.generateTokenId();
    
    const payload = {
      iss: this.options.issuer,
      sub: sourceToken.sub,
      aud: targetDomain,
      exp: now + lifetime,
      iat: now,
      jti: tokenId,
      
      // Minimal user claims for cross-domain
      email: sourceToken.email,
      username: sourceToken.username,
      roles: this.filterRolesForDomain(sourceToken.roles || [], targetDomain),
      
      scope: scopes.join(' '),
      token_type: 'domain_access',
      domain: targetDomain,
      
      // Original token reference
      original_domain: sourceToken.aud
    };
    
    const token = jwt.sign(payload, this.options.jwtSecret, { algorithm: 'HS256' });
    
    return {
      token,
      jti: tokenId,
      expiresIn: lifetime,
      scope: payload.scope,
      domain: targetDomain
    };
  }

  // Exchange Rules Management
  addExchangeRule(rule) {
    const ruleId = rule.id || this.generateRuleId();
    
    const exchangeRule = {
      id: ruleId,
      name: rule.name,
      description: rule.description,
      
      // Source criteria
      sourceAudience: rule.sourceAudience,
      sourceIssuer: rule.sourceIssuer,
      sourceScopes: rule.sourceScopes || [],
      sourceRoles: rule.sourceRoles || [],
      
      // Target criteria
      targetAudience: rule.targetAudience,
      targetResource: rule.targetResource,
      targetScopes: rule.targetScopes || [],
      
      // Conditions
      conditions: rule.conditions || [],
      
      // Actions
      allow: rule.allow !== false,
      transformClaims: rule.transformClaims || {},
      addClaims: rule.addClaims || {},
      removeClaims: rule.removeClaims || [],
      
      // Metadata
      createdAt: new Date(),
      enabled: rule.enabled !== false,
      priority: rule.priority || 0
    };
    
    this.exchangeRules.set(ruleId, exchangeRule);
    this.emit('exchangeRuleAdded', exchangeRule);
    return exchangeRule;
  }

  updateExchangeRule(ruleId, updates) {
    const rule = this.exchangeRules.get(ruleId);
    if (!rule) {
      throw new Error(`Exchange rule ${ruleId} not found`);
    }
    
    const updatedRule = { ...rule, ...updates, updatedAt: new Date() };
    this.exchangeRules.set(ruleId, updatedRule);
    this.emit('exchangeRuleUpdated', updatedRule);
    return updatedRule;
  }

  deleteExchangeRule(ruleId) {
    const rule = this.exchangeRules.get(ruleId);
    if (!rule) {
      throw new Error(`Exchange rule ${ruleId} not found`);
    }
    
    this.exchangeRules.delete(ruleId);
    this.emit('exchangeRuleDeleted', rule);
    return true;
  }

  // Service Registration
  registerTrustedService(service) {
    const serviceInfo = {
      id: service.id || this.generateServiceId(),
      name: service.name,
      clientId: service.clientId,
      description: service.description,
      
      // Service capabilities
      allowTokenExchange: service.allowTokenExchange !== false,
      allowImpersonation: service.allowImpersonation || false,
      allowedScopes: service.allowedScopes || [],
      
      // Security settings
      publicKey: service.publicKey,
      secretHash: service.secretHash,
      
      // Metadata
      registeredAt: new Date(),
      isActive: true
    };
    
    this.trustedServices.set(service.clientId, serviceInfo);
    this.emit('serviceRegistered', serviceInfo);
    return serviceInfo;
  }

  // Exchange Rules Evaluation
  async checkExchangeRules(context) {
    const applicableRules = Array.from(this.exchangeRules.values())
      .filter(rule => rule.enabled)
      .filter(rule => this.ruleMatches(rule, context))
      .sort((a, b) => b.priority - a.priority);
    
    if (applicableRules.length === 0) {
      return { allowed: false, reason: 'No matching exchange rules found' };
    }
    
    const rule = applicableRules[0]; // Highest priority rule
    
    if (!rule.allow) {
      return { allowed: false, reason: 'Exchange explicitly denied by rule', rule: rule.id };
    }
    
    // Check conditions
    for (const condition of rule.conditions) {
      const conditionResult = await this.evaluateCondition(condition, context);
      if (!conditionResult) {
        return { 
          allowed: false, 
          reason: `Condition not met: ${condition.type}`, 
          rule: rule.id 
        };
      }
    }
    
    return { allowed: true, rule: rule.id, appliedRule: rule };
  }

  ruleMatches(rule, context) {
    const { subjectToken, targetAudience, targetResource } = context;
    
    // Check source audience
    if (rule.sourceAudience && subjectToken.payload.aud !== rule.sourceAudience) {
      return false;
    }
    
    // Check source issuer
    if (rule.sourceIssuer && subjectToken.payload.iss !== rule.sourceIssuer) {
      return false;
    }
    
    // Check target audience
    if (rule.targetAudience && targetAudience !== rule.targetAudience) {
      return false;
    }
    
    // Check target resource
    if (rule.targetResource && targetResource !== rule.targetResource) {
      return false;
    }
    
    // Check source scopes
    if (rule.sourceScopes.length > 0) {
      const tokenScopes = subjectToken.payload.scope?.split(' ') || [];
      if (!rule.sourceScopes.some(scope => tokenScopes.includes(scope))) {
        return false;
      }
    }
    
    // Check source roles
    if (rule.sourceRoles.length > 0) {
      const tokenRoles = subjectToken.payload.roles || [];
      if (!rule.sourceRoles.some(role => tokenRoles.includes(role))) {
        return false;
      }
    }
    
    return true;
  }

  async evaluateCondition(condition, context) {
    switch (condition.type) {
      case 'time_range':
        return this.isWithinTimeRange(condition.start, condition.end);
        
      case 'ip_range':
        return this.isWithinIPRange(context.clientIP, condition.ranges);
        
      case 'user_attribute':
        return this.checkUserAttribute(
          context.subjectToken.payload,
          condition.attribute,
          condition.value,
          condition.operator
        );
        
      case 'custom_claim':
        return this.checkCustomClaim(
          context.subjectToken.payload,
          condition.claim,
          condition.value,
          condition.operator
        );
        
      default:
        return true;
    }
  }

  // Service Permission Checks
  async canExchangeForService(sourceToken, targetService, requestedScopes) {
    const service = this.trustedServices.get(targetService);
    if (!service || !service.isActive) {
      return false;
    }
    
    if (!service.allowTokenExchange) {
      return false;
    }
    
    // Check if requested scopes are allowed
    if (requestedScopes.length > 0) {
      const allowedScopes = service.allowedScopes;
      if (!requestedScopes.every(scope => allowedScopes.includes(scope))) {
        return false;
      }
    }
    
    return true;
  }

  async canImpersonate(actorToken, targetUserId, scopes) {
    // Check if actor has impersonation permission
    const actorRoles = actorToken.roles || [];
    const actorPermissions = actorToken.permissions || [];
    
    if (!actorRoles.includes('admin') && 
        !actorPermissions.includes('user:impersonate')) {
      return { allowed: false, reason: 'Actor lacks impersonation permission' };
    }
    
    // Additional checks could include:
    // - Organization boundaries
    // - Scope limitations
    // - Time restrictions
    
    return { allowed: true };
  }

  async canExchangeForDomain(sourceToken, targetDomain) {
    // Check if cross-domain exchange is allowed
    const allowedDomains = this.options.allowedCrossDomains || [];
    return allowedDomains.includes(targetDomain);
  }

  // Utility Methods
  generateTokenId() {
    return crypto.randomBytes(16).toString('hex');
  }

  generateRuleId() {
    return `rule_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  generateServiceId() {
    return `service_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  calculateTokenLifetime(scopes) {
    // Different scopes might have different lifetime requirements
    if (scopes.includes('offline_access')) {
      return this.options.maxTokenLifetime;
    }
    
    return this.options.defaultTokenLifetime;
  }

  isTrustedIssuer(issuer) {
    return this.options.trustedIssuers.length === 0 || 
           this.options.trustedIssuers.includes(issuer) ||
           issuer === this.options.issuer;
  }

  isAllowedAudience(audience) {
    return this.options.allowedAudiences.length === 0 || 
           this.options.allowedAudiences.includes(audience);
  }

  filterRolesForDomain(roles, domain) {
    // Filter roles based on domain-specific policies
    // This is a simplified implementation
    return roles.filter(role => !role.startsWith('admin:'));
  }

  async getUserInfo(userId) {
    // This would typically call a user service
    // Simplified implementation
    return {
      id: userId,
      email: `user${userId}@activelog.com`,
      username: `user${userId}`,
      roles: ['user'],
      permissions: []
    };
  }

  // Logging and Audit
  async logTokenExchange(exchangeData) {
    this.exchangeHistory.push({
      ...exchangeData,
      id: this.generateTokenId()
    });
    
    // Keep only last 10000 exchanges
    if (this.exchangeHistory.length > 10000) {
      this.exchangeHistory.shift();
    }
    
    this.emit('tokenExchangeLogged', exchangeData);
  }

  async logImpersonation(impersonationData) {
    this.impersonationHistory = this.impersonationHistory || [];
    this.impersonationHistory.push({
      ...impersonationData,
      id: this.generateTokenId()
    });
    
    this.emit('impersonationLogged', impersonationData);
  }

  // Default Rules Setup
  setupDefaultRules() {
    // Allow internal service exchanges
    this.addExchangeRule({
      id: 'internal-service-exchange',
      name: 'Internal Service Exchange',
      description: 'Allow token exchange between internal ActiveLog services',
      sourceAudience: 'activelog-web-client',
      targetAudience: /^activelog-.*-service$/,
      allow: true,
      conditions: []
    });
    
    // Allow admin impersonation
    this.addExchangeRule({
      id: 'admin-impersonation',
      name: 'Admin Impersonation',
      description: 'Allow administrators to impersonate other users',
      sourceRoles: ['admin', 'super_admin'],
      allow: true,
      conditions: [
        {
          type: 'user_attribute',
          attribute: 'roles',
          operator: 'contains',
          value: 'admin'
        }
      ]
    });
  }

  // Helper methods for condition evaluation
  isWithinTimeRange(start, end) {
    const now = new Date().getHours();
    return now >= start && now <= end;
  }

  isWithinIPRange(clientIP, ranges) {
    // Simplified IP range check
    return ranges.some(range => clientIP.startsWith(range));
  }

  checkUserAttribute(tokenPayload, attribute, value, operator = 'equals') {
    const attributeValue = tokenPayload[attribute];
    
    switch (operator) {
      case 'equals':
        return attributeValue === value;
      case 'contains':
        return Array.isArray(attributeValue) ? attributeValue.includes(value) : false;
      case 'not_equals':
        return attributeValue !== value;
      default:
        return false;
    }
  }

  checkCustomClaim(tokenPayload, claim, value, operator = 'equals') {
    return this.checkUserAttribute(tokenPayload, claim, value, operator);
  }

  // Statistics and Monitoring
  getExchangeStats() {
    return {
      totalExchanges: this.exchangeHistory.length,
      activeRules: Array.from(this.exchangeRules.values()).filter(r => r.enabled).length,
      trustedServices: this.trustedServices.size,
      recentExchanges: this.exchangeHistory.slice(-10)
    };
  }

  getExchangeRules() {
    return Array.from(this.exchangeRules.values());
  }

  getTrustedServices() {
    return Array.from(this.trustedServices.values());
  }

  reset() {
    this.exchangeRules.clear();
    this.trustedServices.clear();
    this.exchangeHistory = [];
    this.impersonationHistory = [];
    this.setupDefaultRules();
  }
}

module.exports = TokenExchange;