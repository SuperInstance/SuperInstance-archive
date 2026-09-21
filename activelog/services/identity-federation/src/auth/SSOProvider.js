const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20').Strategy;
const MicrosoftStrategy = require('passport-microsoft').Strategy;
const GitHubStrategy = require('passport-github2').Strategy;
const SamlStrategy = require('passport-saml').Strategy;
const LocalStrategy = require('passport-local').Strategy;
const OAuth2Strategy = require('passport-oauth2').Strategy;
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const EventEmitter = require('events');
const User = require('../models/User');
const Organization = require('../models/Organization');
const SessionManager = require('../services/SessionManager');
const AuditLogger = require('../services/AuditLogger');

class SSOProvider extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      jwtSecret: process.env.JWT_SECRET,
      jwtRefreshSecret: process.env.JWT_REFRESH_SECRET,
      accessTokenExpiry: process.env.JWT_ACCESS_EXPIRY || '15m',
      refreshTokenExpiry: process.env.JWT_REFRESH_EXPIRY || '7d',
      ...config
    };

    this.sessionManager = new SessionManager();
    this.auditLogger = new AuditLogger();
    this.initializeStrategies();
  }

  initializeStrategies() {
    // Local Strategy for username/password
    passport.use(new LocalStrategy({
      usernameField: 'email',
      passwordField: 'password',
      passReqToCallback: true
    }, async (req, email, password, done) => {
      try {
        const user = await User.findOne({ 
          email: email.toLowerCase(),
          isActive: true 
        }).populate('organizations');

        if (!user) {
          await this.auditLogger.log('authentication', 'failed', {
            email,
            reason: 'user_not_found',
            ip: req.ip,
            userAgent: req.get('User-Agent')
          });
          return done(null, false, { message: 'Invalid credentials' });
        }

        const isValidPassword = await bcrypt.compare(password, user.password);
        if (!isValidPassword) {
          await this.auditLogger.log('authentication', 'failed', {
            userId: user._id,
            email,
            reason: 'invalid_password',
            ip: req.ip,
            userAgent: req.get('User-Agent')
          });
          return done(null, false, { message: 'Invalid credentials' });
        }

        // Check if MFA is required
        if (user.mfaEnabled && !req.body.mfaCode) {
          return done(null, false, { 
            message: 'MFA required',
            requiresMFA: true,
            userId: user._id
          });
        }

        if (user.mfaEnabled && req.body.mfaCode) {
          const isValidMFA = await this.verifyMFA(user, req.body.mfaCode);
          if (!isValidMFA) {
            await this.auditLogger.log('authentication', 'failed', {
              userId: user._id,
              email,
              reason: 'invalid_mfa',
              ip: req.ip,
              userAgent: req.get('User-Agent')
            });
            return done(null, false, { message: 'Invalid MFA code' });
          }
        }

        await this.auditLogger.log('authentication', 'success', {
          userId: user._id,
          email,
          provider: 'local',
          ip: req.ip,
          userAgent: req.get('User-Agent')
        });

        return done(null, user);
      } catch (error) {
        return done(error);
      }
    }));

    // Google OAuth Strategy
    if (process.env.GOOGLE_CLIENT_ID) {
      passport.use(new GoogleStrategy({
        clientID: process.env.GOOGLE_CLIENT_ID,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET,
        callbackURL: process.env.GOOGLE_CALLBACK_URL,
        passReqToCallback: true
      }, async (req, accessToken, refreshToken, profile, done) => {
        try {
          const result = await this.handleOAuthUser(req, {
            provider: 'google',
            providerId: profile.id,
            email: profile.emails[0].value,
            firstName: profile.name.givenName,
            lastName: profile.name.familyName,
            avatar: profile.photos[0]?.value,
            accessToken,
            refreshToken
          });
          return done(null, result.user);
        } catch (error) {
          return done(error);
        }
      }));
    }

    // Microsoft OAuth Strategy
    if (process.env.MICROSOFT_CLIENT_ID) {
      passport.use(new MicrosoftStrategy({
        clientID: process.env.MICROSOFT_CLIENT_ID,
        clientSecret: process.env.MICROSOFT_CLIENT_SECRET,
        callbackURL: process.env.MICROSOFT_CALLBACK_URL,
        passReqToCallback: true
      }, async (req, accessToken, refreshToken, profile, done) => {
        try {
          const result = await this.handleOAuthUser(req, {
            provider: 'microsoft',
            providerId: profile.id,
            email: profile.emails[0].value,
            firstName: profile.name.givenName,
            lastName: profile.name.familyName,
            avatar: profile.photos[0]?.value,
            accessToken,
            refreshToken
          });
          return done(null, result.user);
        } catch (error) {
          return done(error);
        }
      }));
    }

    // GitHub OAuth Strategy
    if (process.env.GITHUB_CLIENT_ID) {
      passport.use(new GitHubStrategy({
        clientID: process.env.GITHUB_CLIENT_ID,
        clientSecret: process.env.GITHUB_CLIENT_SECRET,
        callbackURL: process.env.GITHUB_CALLBACK_URL,
        passReqToCallback: true
      }, async (req, accessToken, refreshToken, profile, done) => {
        try {
          const result = await this.handleOAuthUser(req, {
            provider: 'github',
            providerId: profile.id,
            email: profile.emails[0]?.value || `${profile.username}@github.local`,
            firstName: profile.displayName?.split(' ')[0] || profile.username,
            lastName: profile.displayName?.split(' ').slice(1).join(' ') || '',
            avatar: profile.photos[0]?.value,
            username: profile.username,
            accessToken,
            refreshToken
          });
          return done(null, result.user);
        } catch (error) {
          return done(error);
        }
      }));
    }

    // SAML Strategy
    if (process.env.SAML_ENTRY_POINT) {
      passport.use(new SamlStrategy({
        entryPoint: process.env.SAML_ENTRY_POINT,
        issuer: process.env.SAML_ISSUER,
        callbackUrl: `${process.env.BASE_URL}/auth/saml/callback`,
        cert: process.env.SAML_CERT,
        passReqToCallback: true
      }, async (req, profile, done) => {
        try {
          const result = await this.handleSAMLUser(req, profile);
          return done(null, result.user);
        } catch (error) {
          return done(error);
        }
      }));
    }

    // Generic OAuth2 Strategy for custom providers
    passport.use('custom-oauth2', new OAuth2Strategy({
      authorizationURL: process.env.OAUTH2_AUTH_URL,
      tokenURL: process.env.OAUTH2_TOKEN_URL,
      clientID: process.env.OAUTH2_CLIENT_ID,
      clientSecret: process.env.OAUTH2_CLIENT_SECRET,
      callbackURL: process.env.OAUTH2_CALLBACK_URL,
      passReqToCallback: true
    }, async (req, accessToken, refreshToken, profile, done) => {
      try {
        const userInfo = await this.fetchCustomOAuthUserInfo(accessToken);
        const result = await this.handleOAuthUser(req, {
          provider: 'custom-oauth2',
          providerId: userInfo.id,
          email: userInfo.email,
          firstName: userInfo.firstName,
          lastName: userInfo.lastName,
          avatar: userInfo.avatar,
          accessToken,
          refreshToken
        });
        return done(null, result.user);
      } catch (error) {
        return done(error);
      }
    }));

    passport.serializeUser((user, done) => {
      done(null, user._id);
    });

    passport.deserializeUser(async (id, done) => {
      try {
        const user = await User.findById(id).populate('organizations');
        done(null, user);
      } catch (error) {
        done(error);
      }
    });
  }

  async handleOAuthUser(req, providerData) {
    const { provider, providerId, email, firstName, lastName, avatar, accessToken, refreshToken } = providerData;
    
    try {
      // Check if user exists by provider ID
      let user = await User.findOne({
        [`providers.${provider}.id`]: providerId
      }).populate('organizations');

      if (!user) {
        // Check if user exists by email
        user = await User.findOne({ email: email.toLowerCase() }).populate('organizations');
        
        if (user) {
          // Link existing account with new provider
          user.providers = user.providers || {};
          user.providers[provider] = {
            id: providerId,
            accessToken: this.encryptToken(accessToken),
            refreshToken: refreshToken ? this.encryptToken(refreshToken) : null,
            lastLogin: new Date()
          };
          await user.save();
        } else {
          // Create new user
          user = new User({
            email: email.toLowerCase(),
            firstName,
            lastName,
            avatar,
            isActive: true,
            emailVerified: true, // OAuth users are pre-verified
            providers: {
              [provider]: {
                id: providerId,
                accessToken: this.encryptToken(accessToken),
                refreshToken: refreshToken ? this.encryptToken(refreshToken) : null,
                lastLogin: new Date()
              }
            }
          });
          await user.save();
        }
      } else {
        // Update existing OAuth user
        user.providers[provider].accessToken = this.encryptToken(accessToken);
        if (refreshToken) {
          user.providers[provider].refreshToken = this.encryptToken(refreshToken);
        }
        user.providers[provider].lastLogin = new Date();
        user.lastLoginAt = new Date();
        await user.save();
      }

      await this.auditLogger.log('authentication', 'success', {
        userId: user._id,
        email,
        provider,
        ip: req.ip,
        userAgent: req.get('User-Agent')
      });

      this.emit('user_authenticated', { user, provider, req });
      
      return { user, isNewUser: !user.lastLoginAt };
    } catch (error) {
      await this.auditLogger.log('authentication', 'failed', {
        email,
        provider,
        reason: error.message,
        ip: req.ip,
        userAgent: req.get('User-Agent')
      });
      throw error;
    }
  }

  async handleSAMLUser(req, profile) {
    const email = profile.email || profile.nameID;
    const attributes = profile.attributes || {};
    
    try {
      let user = await User.findOne({
        'providers.saml.nameID': profile.nameID
      }).populate('organizations');

      if (!user) {
        user = await User.findOne({ email: email.toLowerCase() }).populate('organizations');
        
        if (user) {
          // Link SAML to existing account
          user.providers = user.providers || {};
          user.providers.saml = {
            nameID: profile.nameID,
            sessionIndex: profile.sessionIndex,
            attributes,
            lastLogin: new Date()
          };
          await user.save();
        } else {
          // Create new SAML user
          user = new User({
            email: email.toLowerCase(),
            firstName: attributes.firstName || attributes.givenName || '',
            lastName: attributes.lastName || attributes.surname || '',
            isActive: true,
            emailVerified: true,
            providers: {
              saml: {
                nameID: profile.nameID,
                sessionIndex: profile.sessionIndex,
                attributes,
                lastLogin: new Date()
              }
            }
          });
          await user.save();
        }
      } else {
        // Update SAML user
        user.providers.saml.sessionIndex = profile.sessionIndex;
        user.providers.saml.attributes = attributes;
        user.providers.saml.lastLogin = new Date();
        user.lastLoginAt = new Date();
        await user.save();
      }

      await this.auditLogger.log('authentication', 'success', {
        userId: user._id,
        email,
        provider: 'saml',
        ip: req.ip,
        userAgent: req.get('User-Agent')
      });

      return { user, isNewUser: !user.lastLoginAt };
    } catch (error) {
      await this.auditLogger.log('authentication', 'failed', {
        email,
        provider: 'saml',
        reason: error.message,
        ip: req.ip,
        userAgent: req.get('User-Agent')
      });
      throw error;
    }
  }

  async generateTokenPair(user, context = {}) {
    const accessTokenPayload = {
      userId: user._id,
      email: user.email,
      role: user.role,
      organizations: user.organizations.map(org => ({
        id: org._id,
        name: org.name,
        role: org.members.find(m => m.user.toString() === user._id.toString())?.role
      })),
      permissions: await this.getUserPermissions(user),
      context: context.organizationId ? { organizationId: context.organizationId } : {}
    };

    const refreshTokenPayload = {
      userId: user._id,
      tokenVersion: user.tokenVersion || 0
    };

    const accessToken = jwt.sign(accessTokenPayload, this.config.jwtSecret, {
      expiresIn: this.config.accessTokenExpiry
    });

    const refreshToken = jwt.sign(refreshTokenPayload, this.config.jwtRefreshSecret, {
      expiresIn: this.config.refreshTokenExpiry
    });

    return { accessToken, refreshToken };
  }

  async verifyToken(token, type = 'access') {
    try {
      const secret = type === 'access' ? this.config.jwtSecret : this.config.jwtRefreshSecret;
      const decoded = jwt.verify(token, secret);
      
      if (type === 'refresh') {
        const user = await User.findById(decoded.userId);
        if (!user || user.tokenVersion !== decoded.tokenVersion) {
          throw new Error('Token revoked');
        }
      }
      
      return decoded;
    } catch (error) {
      throw new Error('Invalid token');
    }
  }

  async refreshAccessToken(refreshToken) {
    try {
      const decoded = await this.verifyToken(refreshToken, 'refresh');
      const user = await User.findById(decoded.userId).populate('organizations');
      
      if (!user || !user.isActive) {
        throw new Error('User not found or inactive');
      }

      const { accessToken: newAccessToken } = await this.generateTokenPair(user);
      return { accessToken: newAccessToken };
    } catch (error) {
      throw new Error('Token refresh failed');
    }
  }

  async revokeUserTokens(userId) {
    const user = await User.findById(userId);
    if (user) {
      user.tokenVersion = (user.tokenVersion || 0) + 1;
      await user.save();
      await this.sessionManager.revokeUserSessions(userId);
    }
  }

  async getUserPermissions(user) {
    const permissions = new Set();
    
    // Add user-level permissions
    if (user.permissions) {
      user.permissions.forEach(perm => permissions.add(perm));
    }
    
    // Add organization-level permissions
    for (const org of user.organizations) {
      const member = org.members.find(m => m.user.toString() === user._id.toString());
      if (member && member.permissions) {
        member.permissions.forEach(perm => permissions.add(`${org._id}:${perm}`));
      }
    }
    
    return Array.from(permissions);
  }

  async verifyMFA(user, code) {
    const speakeasy = require('speakeasy');
    
    if (!user.mfaSecret) {
      return false;
    }
    
    return speakeasy.totp.verify({
      secret: user.mfaSecret,
      encoding: 'ascii',
      token: code,
      window: 2
    });
  }

  encryptToken(token) {
    const crypto = require('crypto');
    const algorithm = 'aes-256-gcm';
    const key = Buffer.from(process.env.ENCRYPTION_KEY, 'hex');
    
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipher(algorithm, key);
    cipher.setAAD(Buffer.from('token'));
    
    let encrypted = cipher.update(token, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    const authTag = cipher.getAuthTag();
    
    return `${iv.toString('hex')}:${encrypted}:${authTag.toString('hex')}`;
  }

  decryptToken(encryptedToken) {
    const crypto = require('crypto');
    const algorithm = 'aes-256-gcm';
    const key = Buffer.from(process.env.ENCRYPTION_KEY, 'hex');
    
    const [ivHex, encrypted, authTagHex] = encryptedToken.split(':');
    const iv = Buffer.from(ivHex, 'hex');
    const authTag = Buffer.from(authTagHex, 'hex');
    
    const decipher = crypto.createDecipher(algorithm, key);
    decipher.setAAD(Buffer.from('token'));
    decipher.setAuthTag(authTag);
    
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return decrypted;
  }

  async fetchCustomOAuthUserInfo(accessToken) {
    const axios = require('axios');
    const response = await axios.get(process.env.OAUTH2_USER_INFO_URL, {
      headers: { Authorization: `Bearer ${accessToken}` }
    });
    return response.data;
  }

  async federateUser(fromProvider, toProvider, userId, options = {}) {
    const user = await User.findById(userId).populate('organizations');
    
    if (!user) {
      throw new Error('User not found');
    }

    // Create federation record
    const federationData = {
      fromProvider,
      toProvider,
      userId: user._id,
      email: user.email,
      createdAt: new Date(),
      ...options
    };

    await this.auditLogger.log('federation', 'created', federationData);
    this.emit('user_federated', federationData);
    
    return federationData;
  }
}

module.exports = SSOProvider;