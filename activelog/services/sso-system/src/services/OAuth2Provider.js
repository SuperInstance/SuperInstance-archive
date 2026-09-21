const OAuth2Server = require('node-oauth2-server');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const { EventEmitter } = require('events');

class OAuth2Provider extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      accessTokenLifetime: options.accessTokenLifetime || 3600, // 1 hour
      refreshTokenLifetime: options.refreshTokenLifetime || 1209600, // 2 weeks
      authorizationCodeLifetime: options.authorizationCodeLifetime || 300, // 5 minutes
      jwtSecret: options.jwtSecret || process.env.JWT_SECRET || 'sso-secret-key',
      issuer: options.issuer || 'https://sso.activelog.com',
      ...options
    };
    
    this.clients = new Map();
    this.tokens = new Map();
    this.authCodes = new Map();
    this.refreshTokens = new Map();
    
    this.server = new OAuth2Server({
      model: this,
      accessTokenLifetime: this.options.accessTokenLifetime,
      refreshTokenLifetime: this.options.refreshTokenLifetime,
      authorizationCodeLifetime: this.options.authorizationCodeLifetime,
      allowBearerTokensInQueryString: true,
      allowEmptyState: false,
      allowExtendedTokenAttributes: true
    });
    
    this.setupDefaultClients();
    this.setupCleanupInterval();
  }

  // OAuth2 Model Implementation
  async getClient(clientId, clientSecret) {
    const client = this.clients.get(clientId);
    
    if (!client) {
      return null;
    }
    
    // If clientSecret is provided, verify it
    if (clientSecret && client.clientSecret !== clientSecret) {
      return null;
    }
    
    return {
      id: client.id,
      clientId: client.clientId,
      clientSecret: client.clientSecret,
      redirectUris: client.redirectUris,
      grants: client.grants,
      accessTokenLifetime: client.accessTokenLifetime || this.options.accessTokenLifetime,
      refreshTokenLifetime: client.refreshTokenLifetime || this.options.refreshTokenLifetime
    };
  }

  async saveToken(token, client, user) {
    const tokenData = {
      accessToken: token.accessToken,
      refreshToken: token.refreshToken,
      accessTokenExpiresAt: token.accessTokenExpiresAt,
      refreshTokenExpiresAt: token.refreshTokenExpiresAt,
      scope: token.scope,
      client: {
        id: client.id,
        clientId: client.clientId
      },
      user: {
        id: user.id,
        username: user.username,
        email: user.email
      }
    };
    
    this.tokens.set(token.accessToken, tokenData);
    
    if (token.refreshToken) {
      this.refreshTokens.set(token.refreshToken, tokenData);
    }
    
    this.emit('tokenCreated', tokenData);
    return tokenData;
  }

  async getAccessToken(accessToken) {
    const token = this.tokens.get(accessToken);
    
    if (!token) {
      return null;
    }
    
    if (token.accessTokenExpiresAt < new Date()) {
      this.tokens.delete(accessToken);
      return null;
    }
    
    return token;
  }

  async getRefreshToken(refreshToken) {
    const token = this.refreshTokens.get(refreshToken);
    
    if (!token) {
      return null;
    }
    
    if (token.refreshTokenExpiresAt < new Date()) {
      this.refreshTokens.delete(refreshToken);
      return null;
    }
    
    return token;
  }

  async revokeToken(token) {
    const deleted = this.refreshTokens.delete(token.refreshToken);
    this.emit('tokenRevoked', token);
    return deleted;
  }

  async saveAuthorizationCode(code, client, user) {
    const authCode = {
      authorizationCode: code.authorizationCode,
      expiresAt: code.expiresAt,
      redirectUri: code.redirectUri,
      scope: code.scope,
      client: {
        id: client.id,
        clientId: client.clientId
      },
      user: {
        id: user.id,
        username: user.username,
        email: user.email
      }
    };
    
    this.authCodes.set(code.authorizationCode, authCode);
    this.emit('authCodeCreated', authCode);
    return authCode;
  }

  async getAuthorizationCode(authorizationCode) {
    const code = this.authCodes.get(authorizationCode);
    
    if (!code) {
      return null;
    }
    
    if (code.expiresAt < new Date()) {
      this.authCodes.delete(authorizationCode);
      return null;
    }
    
    return code;
  }

  async revokeAuthorizationCode(code) {
    const deleted = this.authCodes.delete(code.authorizationCode);
    this.emit('authCodeRevoked', code);
    return deleted;
  }

  async verifyScope(token, scope) {
    if (!token.scope) {
      return false;
    }
    
    const tokenScopes = token.scope.split(' ');
    const requiredScopes = scope.split(' ');
    
    return requiredScopes.every(s => tokenScopes.includes(s));
  }

  // Client Management
  async registerClient(clientData) {
    const client = {
      id: this.generateClientId(),
      clientId: clientData.clientId || this.generateClientId(),
      clientSecret: clientData.clientSecret || this.generateClientSecret(),
      name: clientData.name,
      description: clientData.description,
      redirectUris: clientData.redirectUris || [],
      grants: clientData.grants || ['authorization_code', 'refresh_token'],
      scopes: clientData.scopes || ['openid', 'profile', 'email'],
      responseTypes: clientData.responseTypes || ['code'],
      tokenEndpointAuthMethod: clientData.tokenEndpointAuthMethod || 'client_secret_basic',
      
      // OIDC specific
      applicationType: clientData.applicationType || 'web',
      contacts: clientData.contacts || [],
      logoUri: clientData.logoUri,
      clientUri: clientData.clientUri,
      policyUri: clientData.policyUri,
      tosUri: clientData.tosUri,
      
      // Timeouts
      accessTokenLifetime: clientData.accessTokenLifetime,
      refreshTokenLifetime: clientData.refreshTokenLifetime,
      
      // Metadata
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true
    };
    
    this.clients.set(client.clientId, client);
    this.emit('clientRegistered', client);
    return client;
  }

  async updateClient(clientId, updates) {
    const client = this.clients.get(clientId);
    if (!client) {
      throw new Error(`Client ${clientId} not found`);
    }
    
    const updatedClient = {
      ...client,
      ...updates,
      updatedAt: new Date()
    };
    
    this.clients.set(clientId, updatedClient);
    this.emit('clientUpdated', updatedClient);
    return updatedClient;
  }

  async deleteClient(clientId) {
    const client = this.clients.get(clientId);
    if (!client) {
      throw new Error(`Client ${clientId} not found`);
    }
    
    // Revoke all tokens for this client
    for (const [token, tokenData] of this.tokens) {
      if (tokenData.client.clientId === clientId) {
        this.tokens.delete(token);
      }
    }
    
    for (const [refreshToken, tokenData] of this.refreshTokens) {
      if (tokenData.client.clientId === clientId) {
        this.refreshTokens.delete(refreshToken);
      }
    }
    
    this.clients.delete(clientId);
    this.emit('clientDeleted', client);
    return true;
  }

  getClient(clientId) {
    return this.clients.get(clientId);
  }

  getClients() {
    return Array.from(this.clients.values());
  }

  // OIDC Implementation
  async generateIdToken(user, client, nonce = null) {
    const now = Math.floor(Date.now() / 1000);
    
    const payload = {
      iss: this.options.issuer,
      sub: user.id.toString(),
      aud: client.clientId,
      exp: now + this.options.accessTokenLifetime,
      iat: now,
      auth_time: user.lastLoginAt ? Math.floor(user.lastLoginAt.getTime() / 1000) : now,
      
      // Standard claims
      name: user.name || `${user.firstName} ${user.lastName}`.trim(),
      given_name: user.firstName,
      family_name: user.lastName,
      middle_name: user.middleName,
      nickname: user.nickname,
      preferred_username: user.username,
      email: user.email,
      email_verified: user.emailVerified || false,
      phone_number: user.phoneNumber,
      phone_number_verified: user.phoneVerified || false,
      picture: user.avatar,
      profile: user.profileUrl,
      website: user.website,
      gender: user.gender,
      birthdate: user.birthdate,
      zoneinfo: user.timezone,
      locale: user.locale,
      updated_at: user.updatedAt ? Math.floor(user.updatedAt.getTime() / 1000) : now
    };
    
    if (nonce) {
      payload.nonce = nonce;
    }
    
    // Add custom claims
    if (user.roles && user.roles.length > 0) {
      payload.roles = user.roles;
    }
    
    if (user.permissions && user.permissions.length > 0) {
      payload.permissions = user.permissions;
    }
    
    if (user.organization) {
      payload.org = user.organization;
    }
    
    return jwt.sign(payload, this.options.jwtSecret, { algorithm: 'HS256' });
  }

  async generateJWTToken(user, client, scopes = []) {
    const now = Math.floor(Date.now() / 1000);
    
    const payload = {
      iss: this.options.issuer,
      sub: user.id.toString(),
      aud: client.clientId,
      exp: now + this.options.accessTokenLifetime,
      iat: now,
      scope: scopes.join(' '),
      
      // User info
      username: user.username,
      email: user.email,
      roles: user.roles || [],
      permissions: user.permissions || [],
      
      // Token metadata
      token_type: 'Bearer',
      client_id: client.clientId
    };
    
    return jwt.sign(payload, this.options.jwtSecret, { algorithm: 'HS256' });
  }

  async verifyJWTToken(token) {
    try {
      return jwt.verify(token, this.options.jwtSecret, { algorithm: 'HS256' });
    } catch (error) {
      return null;
    }
  }

  // OIDC Discovery
  getWellKnownConfiguration() {
    return {
      issuer: this.options.issuer,
      authorization_endpoint: `${this.options.issuer}/oauth/authorize`,
      token_endpoint: `${this.options.issuer}/oauth/token`,
      userinfo_endpoint: `${this.options.issuer}/oauth/userinfo`,
      jwks_uri: `${this.options.issuer}/.well-known/jwks.json`,
      end_session_endpoint: `${this.options.issuer}/oauth/logout`,
      
      scopes_supported: [
        'openid',
        'profile',
        'email',
        'phone',
        'address',
        'offline_access'
      ],
      
      response_types_supported: [
        'code',
        'id_token',
        'token id_token',
        'code id_token',
        'code token',
        'code token id_token'
      ],
      
      response_modes_supported: [
        'query',
        'fragment',
        'form_post'
      ],
      
      grant_types_supported: [
        'authorization_code',
        'refresh_token',
        'client_credentials',
        'implicit'
      ],
      
      subject_types_supported: ['public'],
      
      id_token_signing_alg_values_supported: ['HS256'],
      
      token_endpoint_auth_methods_supported: [
        'client_secret_basic',
        'client_secret_post'
      ],
      
      claims_supported: [
        'iss',
        'sub',
        'aud',
        'exp',
        'iat',
        'name',
        'given_name',
        'family_name',
        'nickname',
        'email',
        'email_verified',
        'picture',
        'roles',
        'permissions'
      ],
      
      code_challenge_methods_supported: ['S256'],
      
      request_parameter_supported: false,
      request_uri_parameter_supported: false
    };
  }

  // JWKS (JSON Web Key Set)
  getJWKS() {
    // For simplicity, returning empty set since we're using HMAC
    // In production, you'd want to use RSA/ECDSA keys
    return {
      keys: []
    };
  }

  // Token Introspection (RFC 7662)
  async introspectToken(token) {
    const tokenData = await this.getAccessToken(token);
    
    if (!tokenData) {
      return { active: false };
    }
    
    return {
      active: true,
      scope: tokenData.scope,
      client_id: tokenData.client.clientId,
      username: tokenData.user.username,
      exp: Math.floor(tokenData.accessTokenExpiresAt.getTime() / 1000),
      iat: Math.floor((tokenData.accessTokenExpiresAt.getTime() - (this.options.accessTokenLifetime * 1000)) / 1000),
      sub: tokenData.user.id.toString(),
      aud: tokenData.client.clientId,
      iss: this.options.issuer,
      token_type: 'Bearer'
    };
  }

  // Token Exchange (RFC 8693)
  async exchangeToken(subjectToken, subjectTokenType, targetAudience, scopes = []) {
    // Verify the subject token
    let payload;
    try {
      payload = await this.verifyJWTToken(subjectToken);
    } catch (error) {
      throw new Error('Invalid subject token');
    }
    
    // Create new token with different audience
    const now = Math.floor(Date.now() / 1000);
    const newPayload = {
      ...payload,
      aud: targetAudience,
      exp: now + this.options.accessTokenLifetime,
      iat: now,
      scope: scopes.join(' ') || payload.scope
    };
    
    const exchangedToken = jwt.sign(newPayload, this.options.jwtSecret, { algorithm: 'HS256' });
    
    this.emit('tokenExchanged', {
      originalToken: subjectToken,
      exchangedToken,
      targetAudience,
      user: payload.sub
    });
    
    return {
      access_token: exchangedToken,
      issued_token_type: 'urn:ietf:params:oauth:token-type:access_token',
      token_type: 'Bearer',
      expires_in: this.options.accessTokenLifetime,
      scope: newPayload.scope
    };
  }

  // Device Authorization Flow (RFC 8628)
  async initiateDeviceAuthorization(clientId, scopes = []) {
    const client = await this.getClient(clientId);
    if (!client) {
      throw new Error('Invalid client');
    }
    
    const deviceCode = this.generateDeviceCode();
    const userCode = this.generateUserCode();
    const verificationUri = `${this.options.issuer}/device`;
    const verificationUriComplete = `${verificationUri}?user_code=${userCode}`;
    const expiresIn = 600; // 10 minutes
    
    const deviceData = {
      deviceCode,
      userCode,
      clientId,
      scopes,
      expiresAt: new Date(Date.now() + expiresIn * 1000),
      status: 'pending',
      createdAt: new Date()
    };
    
    // Store device authorization (in real implementation, use persistent storage)
    this.deviceAuthorizations = this.deviceAuthorizations || new Map();
    this.deviceAuthorizations.set(deviceCode, deviceData);
    this.deviceAuthByUserCode = this.deviceAuthByUserCode || new Map();
    this.deviceAuthByUserCode.set(userCode, deviceData);
    
    return {
      device_code: deviceCode,
      user_code: userCode,
      verification_uri: verificationUri,
      verification_uri_complete: verificationUriComplete,
      expires_in: expiresIn,
      interval: 5
    };
  }

  async pollDeviceAuthorization(deviceCode, clientId) {
    const deviceData = this.deviceAuthorizations?.get(deviceCode);
    
    if (!deviceData || deviceData.clientId !== clientId) {
      throw new Error('Invalid device code');
    }
    
    if (deviceData.expiresAt < new Date()) {
      this.deviceAuthorizations.delete(deviceCode);
      throw new Error('Device code expired');
    }
    
    if (deviceData.status === 'pending') {
      throw new Error('Authorization pending');
    }
    
    if (deviceData.status === 'denied') {
      throw new Error('Authorization denied');
    }
    
    if (deviceData.status === 'authorized' && deviceData.user) {
      // Generate tokens
      const client = await this.getClient(clientId);
      const accessToken = await this.generateJWTToken(deviceData.user, client, deviceData.scopes);
      const refreshToken = this.generateRefreshToken();
      
      const tokenData = {
        accessToken,
        refreshToken,
        accessTokenExpiresAt: new Date(Date.now() + this.options.accessTokenLifetime * 1000),
        refreshTokenExpiresAt: new Date(Date.now() + this.options.refreshTokenLifetime * 1000),
        scope: deviceData.scopes.join(' '),
        client: { id: client.id, clientId: client.clientId },
        user: deviceData.user
      };
      
      await this.saveToken(tokenData, client, deviceData.user);
      
      // Clean up device authorization
      this.deviceAuthorizations.delete(deviceCode);
      this.deviceAuthByUserCode.delete(deviceData.userCode);
      
      return {
        access_token: accessToken,
        refresh_token: refreshToken,
        token_type: 'Bearer',
        expires_in: this.options.accessTokenLifetime,
        scope: tokenData.scope
      };
    }
    
    throw new Error('Invalid device authorization state');
  }

  // Utility Methods
  generateClientId() {
    return crypto.randomBytes(16).toString('hex');
  }

  generateClientSecret() {
    return crypto.randomBytes(32).toString('hex');
  }

  generateDeviceCode() {
    return crypto.randomBytes(32).toString('hex');
  }

  generateUserCode() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let result = '';
    for (let i = 0; i < 8; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  generateRefreshToken() {
    return crypto.randomBytes(32).toString('hex');
  }

  setupDefaultClients() {
    // Register default clients for ActiveLog services
    const defaultClients = [
      {
        clientId: 'activelog-web-client',
        name: 'ActiveLog Web Application',
        redirectUris: ['http://localhost:3000/auth/callback', 'https://app.activelog.com/auth/callback'],
        grants: ['authorization_code', 'refresh_token'],
        scopes: ['openid', 'profile', 'email', 'offline_access']
      },
      {
        clientId: 'activelog-mobile-client',
        name: 'ActiveLog Mobile Application',
        redirectUris: ['activelog://auth/callback'],
        grants: ['authorization_code', 'refresh_token'],
        scopes: ['openid', 'profile', 'email', 'offline_access']
      },
      {
        clientId: 'activelog-api-client',
        name: 'ActiveLog API Service',
        grants: ['client_credentials'],
        scopes: ['api:read', 'api:write']
      }
    ];
    
    defaultClients.forEach(client => {
      this.registerClient(client);
    });
  }

  setupCleanupInterval() {
    // Clean up expired tokens and codes every 5 minutes
    setInterval(() => {
      this.cleanupExpiredTokens();
    }, 5 * 60 * 1000);
  }

  cleanupExpiredTokens() {
    const now = new Date();
    
    // Clean up access tokens
    for (const [token, tokenData] of this.tokens) {
      if (tokenData.accessTokenExpiresAt < now) {
        this.tokens.delete(token);
      }
    }
    
    // Clean up refresh tokens
    for (const [token, tokenData] of this.refreshTokens) {
      if (tokenData.refreshTokenExpiresAt < now) {
        this.refreshTokens.delete(token);
      }
    }
    
    // Clean up authorization codes
    for (const [code, codeData] of this.authCodes) {
      if (codeData.expiresAt < now) {
        this.authCodes.delete(code);
      }
    }
    
    // Clean up device authorizations
    if (this.deviceAuthorizations) {
      for (const [code, deviceData] of this.deviceAuthorizations) {
        if (deviceData.expiresAt < now) {
          this.deviceAuthorizations.delete(code);
          this.deviceAuthByUserCode?.delete(deviceData.userCode);
        }
      }
    }
  }

  // Statistics and Monitoring
  getStats() {
    return {
      clients: this.clients.size,
      activeTokens: this.tokens.size,
      refreshTokens: this.refreshTokens.size,
      authorizationCodes: this.authCodes.size,
      deviceAuthorizations: this.deviceAuthorizations?.size || 0
    };
  }

  reset() {
    this.clients.clear();
    this.tokens.clear();
    this.authCodes.clear();
    this.refreshTokens.clear();
    if (this.deviceAuthorizations) {
      this.deviceAuthorizations.clear();
      this.deviceAuthByUserCode.clear();
    }
    this.setupDefaultClients();
  }
}

module.exports = OAuth2Provider;