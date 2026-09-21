const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20').Strategy;
const FacebookStrategy = require('passport-facebook').Strategy;
const GitHubStrategy = require('passport-github2').Strategy;
const LinkedInStrategy = require('passport-linkedin-oauth2').Strategy;
const { EventEmitter } = require('events');
const crypto = require('crypto');

class SocialLoginManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      callbackUrl: options.callbackUrl || 'http://localhost:8201',
      sessionTimeout: options.sessionTimeout || 3600000, // 1 hour
      enableAccountLinking: options.enableAccountLinking !== false,
      requireEmailVerification: options.requireEmailVerification !== false,
      allowedDomains: options.allowedDomains || [],
      enableDomainRestriction: options.enableDomainRestriction || false,
      ...options
    };
    
    this.providers = new Map();
    this.socialAccounts = new Map();
    this.linkingTokens = new Map();
    this.pendingRegistrations = new Map();
    
    this.initializeProviders();
    this.setupCleanupInterval();
  }

  // Provider Configuration
  configureProvider(providerName, config) {
    const providerConfig = {
      name: providerName,
      enabled: config.enabled !== false,
      clientId: config.clientId,
      clientSecret: config.clientSecret,
      scopes: config.scopes || this.getDefaultScopes(providerName),
      callbackURL: `${this.options.callbackUrl}/auth/${providerName}/callback`,
      profileFields: config.profileFields || this.getDefaultProfileFields(providerName),
      
      // Provider-specific options
      ...config.options
    };
    
    this.providers.set(providerName, providerConfig);
    
    if (providerConfig.enabled) {
      this.setupPassportStrategy(providerName, providerConfig);
    }
    
    this.emit('providerConfigured', { provider: providerName, enabled: providerConfig.enabled });
    return providerConfig;
  }

  enableProvider(providerName) {
    const provider = this.providers.get(providerName);
    if (!provider) {
      throw new Error(`Provider ${providerName} not configured`);
    }
    
    provider.enabled = true;
    this.providers.set(providerName, provider);
    this.setupPassportStrategy(providerName, provider);
    
    this.emit('providerEnabled', { provider: providerName });
  }

  disableProvider(providerName) {
    const provider = this.providers.get(providerName);
    if (!provider) {
      throw new Error(`Provider ${providerName} not configured`);
    }
    
    provider.enabled = false;
    this.providers.set(providerName, provider);
    
    // Remove passport strategy
    passport.unuse(providerName);
    
    this.emit('providerDisabled', { provider: providerName });
  }

  // Passport Strategy Setup
  setupPassportStrategy(providerName, config) {
    switch (providerName) {
      case 'google':
        this.setupGoogleStrategy(config);
        break;
      case 'facebook':
        this.setupFacebookStrategy(config);
        break;
      case 'github':
        this.setupGitHubStrategy(config);
        break;
      case 'linkedin':
        this.setupLinkedInStrategy(config);
        break;
      default:
        throw new Error(`Unsupported provider: ${providerName}`);
    }
  }

  setupGoogleStrategy(config) {
    passport.use('google', new GoogleStrategy({
      clientID: config.clientId,
      clientSecret: config.clientSecret,
      callbackURL: config.callbackURL,
      scope: config.scopes
    }, async (accessToken, refreshToken, profile, done) => {
      try {
        const result = await this.handleSocialLogin('google', profile, {
          accessToken,
          refreshToken
        });
        done(null, result);
      } catch (error) {
        done(error, null);
      }
    }));
  }

  setupFacebookStrategy(config) {
    passport.use('facebook', new FacebookStrategy({
      clientID: config.clientId,
      clientSecret: config.clientSecret,
      callbackURL: config.callbackURL,
      profileFields: config.profileFields,
      scope: config.scopes
    }, async (accessToken, refreshToken, profile, done) => {
      try {
        const result = await this.handleSocialLogin('facebook', profile, {
          accessToken,
          refreshToken
        });
        done(null, result);
      } catch (error) {
        done(error, null);
      }
    }));
  }

  setupGitHubStrategy(config) {
    passport.use('github', new GitHubStrategy({
      clientID: config.clientId,
      clientSecret: config.clientSecret,
      callbackURL: config.callbackURL,
      scope: config.scopes
    }, async (accessToken, refreshToken, profile, done) => {
      try {
        const result = await this.handleSocialLogin('github', profile, {
          accessToken,
          refreshToken
        });
        done(null, result);
      } catch (error) {
        done(error, null);
      }
    }));
  }

  setupLinkedInStrategy(config) {
    passport.use('linkedin', new LinkedInStrategy({
      clientID: config.clientId,
      clientSecret: config.clientSecret,
      callbackURL: config.callbackURL,
      scope: config.scopes,
      state: true
    }, async (accessToken, refreshToken, profile, done) => {
      try {
        const result = await this.handleSocialLogin('linkedin', profile, {
          accessToken,
          refreshToken
        });
        done(null, result);
      } catch (error) {
        done(error, null);
      }
    }));
  }

  // Social Login Processing
  async handleSocialLogin(provider, profile, tokens) {
    const normalizedProfile = this.normalizeProfile(provider, profile);
    
    // Validate email domain if restriction is enabled
    if (this.options.enableDomainRestriction && normalizedProfile.email) {
      const isAllowedDomain = this.isEmailDomainAllowed(normalizedProfile.email);
      if (!isAllowedDomain) {
        throw new Error(`Email domain not allowed: ${normalizedProfile.email.split('@')[1]}`);
      }
    }
    
    // Check if social account already exists
    const existingSocialAccount = this.findSocialAccount(provider, normalizedProfile.id);
    
    if (existingSocialAccount) {
      // Update existing social account
      await this.updateSocialAccount(existingSocialAccount.id, {
        profile: normalizedProfile,
        tokens,
        lastLoginAt: new Date()
      });
      
      this.emit('socialLoginExisting', {
        provider,
        socialAccountId: existingSocialAccount.id,
        userId: existingSocialAccount.userId,
        email: normalizedProfile.email
      });
      
      return {
        success: true,
        userId: existingSocialAccount.userId,
        socialAccountId: existingSocialAccount.id,
        profile: normalizedProfile,
        isNewUser: false
      };
    }
    
    // Check if user exists with the same email
    const existingUser = await this.findUserByEmail(normalizedProfile.email);
    
    if (existingUser) {
      if (this.options.enableAccountLinking) {
        // Link social account to existing user
        const socialAccount = await this.linkSocialAccount(existingUser.id, provider, normalizedProfile, tokens);
        
        this.emit('socialAccountLinked', {
          provider,
          socialAccountId: socialAccount.id,
          userId: existingUser.id,
          email: normalizedProfile.email
        });
        
        return {
          success: true,
          userId: existingUser.id,
          socialAccountId: socialAccount.id,
          profile: normalizedProfile,
          isNewUser: false,
          linkedToExisting: true
        };
      } else {
        throw new Error('An account with this email already exists. Please sign in with your email and password.');
      }
    }
    
    // Create new user account
    const newUser = await this.createUserFromSocialProfile(provider, normalizedProfile, tokens);
    
    this.emit('socialLoginNewUser', {
      provider,
      socialAccountId: newUser.socialAccountId,
      userId: newUser.userId,
      email: normalizedProfile.email
    });
    
    return {
      success: true,
      userId: newUser.userId,
      socialAccountId: newUser.socialAccountId,
      profile: normalizedProfile,
      isNewUser: true
    };
  }

  // Profile Normalization
  normalizeProfile(provider, profile) {
    const normalized = {
      id: profile.id,
      provider,
      username: profile.username,
      displayName: profile.displayName,
      name: {
        first: null,
        last: null,
        middle: null
      },
      email: null,
      emailVerified: false,
      avatar: null,
      profileUrl: null,
      location: null,
      website: null,
      bio: null,
      createdAt: new Date(),
      rawProfile: profile._json || profile
    };
    
    switch (provider) {
      case 'google':
        normalized.email = profile.emails?.[0]?.value;
        normalized.emailVerified = profile.emails?.[0]?.verified || false;
        normalized.name.first = profile.name?.givenName;
        normalized.name.last = profile.name?.familyName;
        normalized.avatar = profile.photos?.[0]?.value;
        normalized.profileUrl = profile.profileUrl;
        break;
        
      case 'facebook':
        normalized.email = profile.emails?.[0]?.value;
        normalized.name.first = profile.name?.givenName;
        normalized.name.last = profile.name?.familyName;
        normalized.name.middle = profile.name?.middleName;
        normalized.avatar = profile.photos?.[0]?.value;
        normalized.profileUrl = profile.profileUrl;
        normalized.location = profile._json?.location?.name;
        normalized.website = profile._json?.website;
        break;
        
      case 'github':
        normalized.email = profile.emails?.[0]?.value;
        normalized.name.first = profile.displayName?.split(' ')[0];
        normalized.name.last = profile.displayName?.split(' ').slice(1).join(' ');
        normalized.avatar = profile.photos?.[0]?.value;
        normalized.profileUrl = profile.profileUrl;
        normalized.location = profile._json?.location;
        normalized.website = profile._json?.blog;
        normalized.bio = profile._json?.bio;
        break;
        
      case 'linkedin':
        normalized.email = profile.emails?.[0]?.value;
        normalized.name.first = profile.name?.givenName;
        normalized.name.last = profile.name?.familyName;
        normalized.avatar = profile.photos?.[0]?.value;
        normalized.profileUrl = profile._json?.publicProfileUrl;
        normalized.location = profile._json?.location?.name;
        break;
    }
    
    return normalized;
  }

  // Social Account Management
  async createSocialAccount(userId, provider, profile, tokens) {
    const socialAccountId = this.generateSocialAccountId();
    
    const socialAccount = {
      id: socialAccountId,
      userId,
      provider,
      providerId: profile.id,
      profile,
      tokens: {
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken,
        expiresAt: tokens.expiresAt ? new Date(tokens.expiresAt) : null
      },
      createdAt: new Date(),
      updatedAt: new Date(),
      lastLoginAt: new Date(),
      isActive: true
    };
    
    this.socialAccounts.set(socialAccountId, socialAccount);
    
    this.emit('socialAccountCreated', {
      socialAccountId,
      userId,
      provider,
      email: profile.email
    });
    
    return socialAccount;
  }

  async updateSocialAccount(socialAccountId, updates) {
    const socialAccount = this.socialAccounts.get(socialAccountId);
    if (!socialAccount) {
      throw new Error(`Social account ${socialAccountId} not found`);
    }
    
    const updatedAccount = {
      ...socialAccount,
      ...updates,
      updatedAt: new Date()
    };
    
    this.socialAccounts.set(socialAccountId, updatedAccount);
    
    this.emit('socialAccountUpdated', {
      socialAccountId,
      userId: socialAccount.userId,
      provider: socialAccount.provider
    });
    
    return updatedAccount;
  }

  async linkSocialAccount(userId, provider, profile, tokens) {
    // Check if this social account is already linked to another user
    const existingSocialAccount = this.findSocialAccount(provider, profile.id);
    if (existingSocialAccount && existingSocialAccount.userId !== userId) {
      throw new Error('This social account is already linked to another user');
    }
    
    if (existingSocialAccount && existingSocialAccount.userId === userId) {
      // Update existing link
      return await this.updateSocialAccount(existingSocialAccount.id, {
        profile,
        tokens,
        lastLoginAt: new Date()
      });
    }
    
    // Create new link
    return await this.createSocialAccount(userId, provider, profile, tokens);
  }

  async unlinkSocialAccount(userId, socialAccountId) {
    const socialAccount = this.socialAccounts.get(socialAccountId);
    if (!socialAccount) {
      throw new Error(`Social account ${socialAccountId} not found`);
    }
    
    if (socialAccount.userId !== userId) {
      throw new Error('Social account does not belong to this user');
    }
    
    // Check if user has other authentication methods
    const userSocialAccounts = this.getUserSocialAccounts(userId);
    if (userSocialAccounts.length === 1) {
      // Check if user has password or other auth methods
      const hasOtherAuthMethods = await this.userHasOtherAuthMethods(userId);
      if (!hasOtherAuthMethods) {
        throw new Error('Cannot unlink the only authentication method');
      }
    }
    
    this.socialAccounts.delete(socialAccountId);
    
    this.emit('socialAccountUnlinked', {
      socialAccountId,
      userId,
      provider: socialAccount.provider
    });
    
    return true;
  }

  // Account Linking with Verification
  async initiateLinking(userId, provider, linkingToken) {
    if (!linkingToken) {
      linkingToken = this.generateLinkingToken();
    }
    
    const linkingData = {
      token: linkingToken,
      userId,
      provider,
      createdAt: new Date(),
      expiresAt: new Date(Date.now() + 900000), // 15 minutes
      used: false
    };
    
    this.linkingTokens.set(linkingToken, linkingData);
    
    this.emit('linkingInitiated', { userId, provider, token: linkingToken });
    
    return {
      linkingToken,
      expiresIn: 900, // seconds
      linkingUrl: `${this.options.callbackUrl}/auth/${provider}?linking_token=${linkingToken}`
    };
  }

  async completeLinking(linkingToken, provider, profile, tokens) {
    const linkingData = this.linkingTokens.get(linkingToken);
    if (!linkingData) {
      throw new Error('Invalid linking token');
    }
    
    if (linkingData.expiresAt < new Date()) {
      this.linkingTokens.delete(linkingToken);
      throw new Error('Linking token expired');
    }
    
    if (linkingData.used) {
      throw new Error('Linking token already used');
    }
    
    if (linkingData.provider !== provider) {
      throw new Error('Provider mismatch');
    }
    
    // Mark token as used
    linkingData.used = true;
    linkingData.usedAt = new Date();
    this.linkingTokens.set(linkingToken, linkingData);
    
    // Link the account
    const socialAccount = await this.linkSocialAccount(linkingData.userId, provider, profile, tokens);
    
    this.emit('linkingCompleted', {
      userId: linkingData.userId,
      provider,
      socialAccountId: socialAccount.id
    });
    
    return socialAccount;
  }

  // User Creation from Social Profile
  async createUserFromSocialProfile(provider, profile, tokens) {
    // Check if email verification is required
    if (this.options.requireEmailVerification && !profile.emailVerified && profile.email) {
      // Store as pending registration
      const registrationToken = this.generateRegistrationToken();
      
      this.pendingRegistrations.set(registrationToken, {
        token: registrationToken,
        provider,
        profile,
        tokens,
        createdAt: new Date(),
        expiresAt: new Date(Date.now() + 3600000) // 1 hour
      });
      
      // Send verification email
      await this.sendEmailVerification(profile.email, registrationToken);
      
      throw new Error('Email verification required. Please check your email.');
    }
    
    // Create user account (this would integrate with your user management system)
    const userId = await this.createUser({
      email: profile.email,
      firstName: profile.name.first,
      lastName: profile.name.last,
      displayName: profile.displayName,
      avatar: profile.avatar,
      emailVerified: profile.emailVerified,
      registrationMethod: 'social',
      registrationProvider: provider
    });
    
    // Create social account link
    const socialAccount = await this.createSocialAccount(userId, provider, profile, tokens);
    
    return {
      userId,
      socialAccountId: socialAccount.id
    };
  }

  async completePendingRegistration(registrationToken, verificationCode) {
    const registration = this.pendingRegistrations.get(registrationToken);
    if (!registration) {
      throw new Error('Invalid registration token');
    }
    
    if (registration.expiresAt < new Date()) {
      this.pendingRegistrations.delete(registrationToken);
      throw new Error('Registration token expired');
    }
    
    // Verify email code (this would integrate with your email verification system)
    const isValidCode = await this.verifyEmailCode(registration.profile.email, verificationCode);
    if (!isValidCode) {
      throw new Error('Invalid verification code');
    }
    
    // Mark email as verified
    registration.profile.emailVerified = true;
    
    // Create user account
    const result = await this.createUserFromSocialProfile(
      registration.provider,
      registration.profile,
      registration.tokens
    );
    
    // Clean up pending registration
    this.pendingRegistrations.delete(registrationToken);
    
    this.emit('pendingRegistrationCompleted', {
      userId: result.userId,
      provider: registration.provider,
      email: registration.profile.email
    });
    
    return result;
  }

  // Query Methods
  getUserSocialAccounts(userId) {
    return Array.from(this.socialAccounts.values())
      .filter(account => account.userId === userId && account.isActive)
      .map(account => ({
        id: account.id,
        provider: account.provider,
        providerId: account.providerId,
        profile: {
          displayName: account.profile.displayName,
          email: account.profile.email,
          avatar: account.profile.avatar
        },
        createdAt: account.createdAt,
        lastLoginAt: account.lastLoginAt
      }));
  }

  findSocialAccount(provider, providerId) {
    return Array.from(this.socialAccounts.values())
      .find(account => account.provider === provider && account.providerId === providerId);
  }

  getSocialAccount(socialAccountId) {
    return this.socialAccounts.get(socialAccountId);
  }

  getProviders() {
    return Array.from(this.providers.values())
      .filter(provider => provider.enabled)
      .map(provider => ({
        name: provider.name,
        scopes: provider.scopes,
        authUrl: `${this.options.callbackUrl}/auth/${provider.name}`
      }));
  }

  // Token Refresh
  async refreshSocialToken(socialAccountId) {
    const socialAccount = this.socialAccounts.get(socialAccountId);
    if (!socialAccount) {
      throw new Error(`Social account ${socialAccountId} not found`);
    }
    
    if (!socialAccount.tokens.refreshToken) {
      throw new Error('No refresh token available');
    }
    
    try {
      const newTokens = await this.refreshProviderToken(
        socialAccount.provider,
        socialAccount.tokens.refreshToken
      );
      
      await this.updateSocialAccount(socialAccountId, {
        tokens: {
          ...socialAccount.tokens,
          ...newTokens,
          refreshedAt: new Date()
        }
      });
      
      this.emit('tokenRefreshed', {
        socialAccountId,
        provider: socialAccount.provider,
        userId: socialAccount.userId
      });
      
      return newTokens;
    } catch (error) {
      this.emit('tokenRefreshFailed', {
        socialAccountId,
        provider: socialAccount.provider,
        error: error.message
      });
      throw error;
    }
  }

  async refreshProviderToken(provider, refreshToken) {
    // This would implement token refresh for each provider
    // Each provider has different token refresh mechanisms
    switch (provider) {
      case 'google':
        return await this.refreshGoogleToken(refreshToken);
      case 'facebook':
        return await this.refreshFacebookToken(refreshToken);
      case 'github':
        // GitHub tokens don't expire, so this is a no-op
        return {};
      case 'linkedin':
        return await this.refreshLinkedInToken(refreshToken);
      default:
        throw new Error(`Token refresh not implemented for ${provider}`);
    }
  }

  // Utility Methods
  generateSocialAccountId() {
    return `social_${Date.now()}_${crypto.randomBytes(8).toString('hex')}`;
  }

  generateLinkingToken() {
    return crypto.randomBytes(32).toString('hex');
  }

  generateRegistrationToken() {
    return crypto.randomBytes(32).toString('hex');
  }

  isEmailDomainAllowed(email) {
    if (this.options.allowedDomains.length === 0) {
      return true;
    }
    
    const domain = email.split('@')[1];
    return this.options.allowedDomains.includes(domain);
  }

  getDefaultScopes(provider) {
    const defaultScopes = {
      google: ['profile', 'email'],
      facebook: ['email', 'public_profile'],
      github: ['user:email'],
      linkedin: ['r_liteprofile', 'r_emailaddress']
    };
    
    return defaultScopes[provider] || [];
  }

  getDefaultProfileFields(provider) {
    const defaultFields = {
      facebook: ['id', 'emails', 'name', 'picture.type(large)', 'location', 'website'],
      linkedin: ['id', 'first-name', 'last-name', 'email-address', 'picture-url']
    };
    
    return defaultFields[provider] || [];
  }

  // Integration Methods (to be implemented)
  async findUserByEmail(email) {
    // This would integrate with your user management system
    return null;
  }

  async createUser(userData) {
    // This would integrate with your user management system
    return `user_${Date.now()}_${crypto.randomBytes(8).toString('hex')}`;
  }

  async userHasOtherAuthMethods(userId) {
    // This would check if user has password or other authentication methods
    return true;
  }

  async sendEmailVerification(email, token) {
    // This would integrate with your email service
    console.log(`Send email verification to ${email} with token ${token}`);
  }

  async verifyEmailCode(email, code) {
    // This would verify the email verification code
    return true;
  }

  async refreshGoogleToken(refreshToken) {
    // Google token refresh implementation
    return {};
  }

  async refreshFacebookToken(refreshToken) {
    // Facebook token refresh implementation
    return {};
  }

  async refreshLinkedInToken(refreshToken) {
    // LinkedIn token refresh implementation
    return {};
  }

  // Default Providers Setup
  initializeProviders() {
    // Configure providers based on environment variables
    const providers = [
      {
        name: 'google',
        clientId: process.env.GOOGLE_CLIENT_ID,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET
      },
      {
        name: 'facebook',
        clientId: process.env.FACEBOOK_APP_ID,
        clientSecret: process.env.FACEBOOK_APP_SECRET,
        profileFields: ['id', 'emails', 'name', 'picture.type(large)']
      },
      {
        name: 'github',
        clientId: process.env.GITHUB_CLIENT_ID,
        clientSecret: process.env.GITHUB_CLIENT_SECRET
      },
      {
        name: 'linkedin',
        clientId: process.env.LINKEDIN_CLIENT_ID,
        clientSecret: process.env.LINKEDIN_CLIENT_SECRET
      }
    ];
    
    for (const provider of providers) {
      if (provider.clientId && provider.clientSecret) {
        this.configureProvider(provider.name, {
          clientId: provider.clientId,
          clientSecret: provider.clientSecret,
          enabled: true,
          ...provider
        });
      }
    }
  }

  // Cleanup
  setupCleanupInterval() {
    // Clean up expired tokens and registrations every hour
    setInterval(() => {
      this.cleanupExpiredData();
    }, 3600000);
  }

  cleanupExpiredData() {
    const now = new Date();
    
    // Clean up expired linking tokens
    for (const [token, data] of this.linkingTokens) {
      if (data.expiresAt < now) {
        this.linkingTokens.delete(token);
      }
    }
    
    // Clean up expired pending registrations
    for (const [token, data] of this.pendingRegistrations) {
      if (data.expiresAt < now) {
        this.pendingRegistrations.delete(token);
      }
    }
  }

  // Statistics and Monitoring
  getStats() {
    const providerStats = {};
    
    for (const account of this.socialAccounts.values()) {
      if (account.isActive) {
        providerStats[account.provider] = (providerStats[account.provider] || 0) + 1;
      }
    }
    
    return {
      enabledProviders: Array.from(this.providers.values()).filter(p => p.enabled).length,
      totalSocialAccounts: this.socialAccounts.size,
      providerStats,
      pendingLinkings: this.linkingTokens.size,
      pendingRegistrations: this.pendingRegistrations.size
    };
  }

  reset() {
    this.socialAccounts.clear();
    this.linkingTokens.clear();
    this.pendingRegistrations.clear();
  }
}

module.exports = SocialLoginManager;