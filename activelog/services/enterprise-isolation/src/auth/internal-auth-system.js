const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const speakeasy = require('speakeasy');
const qrcode = require('qrcode');
const crypto = require('crypto');
const argon2 = require('argon2');
const EventEmitter = require('events');
const passport = require('passport');
const LocalStrategy = require('passport-local').Strategy;
const LdapStrategy = require('passport-ldapauth');
const SamlStrategy = require('passport-saml').Strategy;

class InternalAuthSystem extends EventEmitter {
    constructor() {
        super();
        this.users = new Map();
        this.sessions = new Map();
        this.loginAttempts = new Map();
        this.roleHierarchy = new Map();
        this.permissions = new Map();
        this.authProviders = new Map();
        this.securityPolicies = new Map();
        this.mfaDevices = new Map();
        this.auditLog = [];
        
        this.initializeSecurityPolicies();
        this.initializeRoleHierarchy();
        this.initializeDefaultUsers();
        this.setupPassportStrategies();
    }

    initializeSecurityPolicies() {
        this.securityPolicies.set('password', {
            minLength: 16,
            requireUppercase: true,
            requireLowercase: true, 
            requireNumbers: true,
            requireSpecialChars: true,
            maxAge: 90 * 24 * 60 * 60 * 1000, // 90 days
            historyCheck: 12, // Cannot reuse last 12 passwords
            complexityScore: 4, // Minimum complexity score
            dictionaryCheck: true,
            compromisedPasswordCheck: true
        });

        this.securityPolicies.set('authentication', {
            maxLoginAttempts: 3,
            lockoutDuration: 30 * 60 * 1000, // 30 minutes
            sessionTimeout: 8 * 60 * 60 * 1000, // 8 hours
            mfaRequired: true,
            mfaGracePeriod: 5 * 60 * 1000, // 5 minutes
            tokenLifetime: 15 * 60 * 1000, // 15 minutes
            refreshTokenLifetime: 24 * 60 * 60 * 1000, // 24 hours
            concurrentSessions: 1, // Only one session per user
            forcePasswordChangeOnFirstLogin: true,
            minimumRoleForSystemAccess: 'user'
        });

        this.securityPolicies.set('authorization', {
            principleOfLeastPrivilege: true,
            roleBasedAccess: true,
            temporaryElevation: true,
            elevationTimeout: 60 * 60 * 1000, // 1 hour
            auditAllAccess: true,
            denyByDefault: true,
            administrativeApprovalRequired: ['system_admin', 'security_admin'],
            emergencyAccessProcedures: true
        });

        this.securityPolicies.set('compliance', {
            auditAllAuthEvents: true,
            retainAuditLogs: 7 * 365 * 24 * 60 * 60 * 1000, // 7 years
            encryptSensitiveData: true,
            regularAccessReviews: true,
            accessReviewInterval: 90 * 24 * 60 * 60 * 1000, // 90 days
            segregationOfDuties: true,
            approvalWorkflows: true
        });
    }

    initializeRoleHierarchy() {
        // Define role hierarchy from least to most privileged
        this.roles = {
            'guest': {
                level: 0,
                permissions: ['read_public'],
                description: 'Guest access with minimal permissions',
                temporary: true
            },
            'user': {
                level: 1,
                permissions: ['read_own', 'write_own', 'read_public'],
                description: 'Standard user with basic access rights',
                inherits: ['guest']
            },
            'operator': {
                level: 2,
                permissions: ['read_own', 'write_own', 'read_shared', 'write_shared', 'view_basic_monitoring'],
                description: 'Operational user with limited system monitoring',
                inherits: ['user']
            },
            'supervisor': {
                level: 3,
                permissions: ['read_team', 'write_team', 'view_team_monitoring', 'approve_basic_requests'],
                description: 'Team supervisor with management capabilities',
                inherits: ['operator']
            },
            'manager': {
                level: 4,
                permissions: ['read_department', 'write_department', 'view_department_monitoring', 'approve_department_requests'],
                description: 'Department manager with broader access',
                inherits: ['supervisor']
            },
            'admin': {
                level: 5,
                permissions: ['read_all', 'write_configuration', 'view_system_monitoring', 'manage_users'],
                description: 'System administrator with full operational access',
                inherits: ['manager']
            },
            'security_admin': {
                level: 6,
                permissions: ['read_all', 'write_all', 'manage_security', 'view_audit_logs', 'manage_compliance'],
                description: 'Security administrator with security-focused privileges',
                inherits: ['admin']
            },
            'system_admin': {
                level: 7,
                permissions: ['read_all', 'write_all', 'system_configuration', 'emergency_access', 'manage_infrastructure'],
                description: 'System administrator with full system access',
                inherits: ['security_admin']
            }
        };

        // Build role hierarchy map
        Object.entries(this.roles).forEach(([role, config]) => {
            this.roleHierarchy.set(role, config);
        });

        // Build complete permission sets including inherited permissions
        this.buildInheritedPermissions();
    }

    buildInheritedPermissions() {
        const getInheritedPermissions = (role, visited = new Set()) => {
            if (visited.has(role)) {
                throw new Error(`Circular inheritance detected for role: ${role}`);
            }
            visited.add(role);

            const roleConfig = this.roleHierarchy.get(role);
            if (!roleConfig) return [];

            let permissions = [...roleConfig.permissions];
            
            if (roleConfig.inherits) {
                roleConfig.inherits.forEach(inheritedRole => {
                    permissions.push(...getInheritedPermissions(inheritedRole, visited));
                });
            }

            return [...new Set(permissions)]; // Remove duplicates
        };

        // Update each role with complete permission set
        this.roleHierarchy.forEach((config, role) => {
            config.allPermissions = getInheritedPermissions(role);
        });
    }

    async initializeDefaultUsers() {
        // Create emergency access account (must be changed on first login)
        const emergencyPassword = crypto.randomBytes(32).toString('hex');
        const emergencyUser = await this.createUser({
            username: 'emergency',
            email: 'emergency@localhost',
            password: emergencyPassword,
            role: 'system_admin',
            forcePasswordChange: true,
            isEmergencyAccount: true,
            created: new Date(),
            lastLogin: null,
            loginCount: 0,
            status: 'active'
        });

        // Log emergency account creation with password (this should be securely communicated)
        console.log(`EMERGENCY ACCOUNT CREATED - Username: emergency, Password: ${emergencyPassword}`);
        console.log('CHANGE THIS PASSWORD IMMEDIATELY AFTER FIRST LOGIN');

        // Create default system service account
        const systemServiceKey = crypto.randomBytes(64).toString('hex');
        await this.createUser({
            username: 'system_service',
            email: 'system@localhost',
            password: systemServiceKey,
            role: 'admin',
            isServiceAccount: true,
            created: new Date(),
            status: 'active'
        });

        this.emit('defaultUsersInitialized', {
            emergencyUser: emergencyUser.username,
            serviceAccount: 'system_service'
        });
    }

    setupPassportStrategies() {
        // Local authentication strategy
        passport.use('local', new LocalStrategy({
            usernameField: 'username',
            passwordField: 'password',
            passReqToCallback: true
        }, async (req, username, password, done) => {
            try {
                const result = await this.authenticateUser(username, password, {
                    ip: req.ip,
                    userAgent: req.get('user-agent'),
                    sessionId: req.sessionID
                });

                if (result.success) {
                    return done(null, result.user);
                } else {
                    return done(null, false, { message: result.error });
                }
            } catch (error) {
                return done(error);
            }
        }));

        // LDAP authentication strategy (for enterprise integration)
        if (process.env.LDAP_URL) {
            passport.use('ldap', new LdapStrategy({
                server: {
                    url: process.env.LDAP_URL,
                    bindDN: process.env.LDAP_BIND_DN,
                    bindCredentials: process.env.LDAP_BIND_PASSWORD,
                    searchBase: process.env.LDAP_SEARCH_BASE,
                    searchFilter: '(uid={{username}})'
                }
            }, async (profile, done) => {
                try {
                    const user = await this.syncLdapUser(profile);
                    return done(null, user);
                } catch (error) {
                    return done(error);
                }
            }));
        }

        // SAML authentication strategy (for SSO integration)
        if (process.env.SAML_ENTRY_POINT) {
            passport.use('saml', new SamlStrategy({
                entryPoint: process.env.SAML_ENTRY_POINT,
                issuer: process.env.SAML_ISSUER,
                callbackUrl: process.env.SAML_CALLBACK_URL,
                cert: process.env.SAML_CERT
            }, async (profile, done) => {
                try {
                    const user = await this.syncSamlUser(profile);
                    return done(null, user);
                } catch (error) {
                    return done(error);
                }
            }));
        }

        passport.serializeUser((user, done) => {
            done(null, user.id);
        });

        passport.deserializeUser(async (id, done) => {
            try {
                const user = this.users.get(id);
                if (user && user.status === 'active') {
                    done(null, user);
                } else {
                    done(null, false);
                }
            } catch (error) {
                done(error);
            }
        });
    }

    async initialize() {
        this.emit('authSystemInitialized');
    }

    async createUser(userData) {
        const userId = crypto.randomBytes(16).toString('hex');
        
        // Validate required fields
        if (!userData.username || !userData.password || !userData.role) {
            throw new Error('Username, password, and role are required');
        }

        // Check if username already exists
        const existingUser = Array.from(this.users.values()).find(u => u.username === userData.username);
        if (existingUser) {
            throw new Error('Username already exists');
        }

        // Validate role
        if (!this.roleHierarchy.has(userData.role)) {
            throw new Error(`Invalid role: ${userData.role}`);
        }

        // Validate password policy
        await this.validatePasswordPolicy(userData.password);

        // Hash password using Argon2 (more secure than bcrypt)
        const hashedPassword = await argon2.hash(userData.password, {
            type: argon2.argon2id,
            memoryCost: 65536, // 64 MB
            timeCost: 3,
            parallelism: 4,
            hashLength: 32
        });

        const user = {
            id: userId,
            username: userData.username,
            email: userData.email,
            passwordHash: hashedPassword,
            role: userData.role,
            permissions: this.roleHierarchy.get(userData.role).allPermissions,
            
            // Account status
            status: userData.status || 'active',
            forcePasswordChange: userData.forcePasswordChange || false,
            isServiceAccount: userData.isServiceAccount || false,
            isEmergencyAccount: userData.isEmergencyAccount || false,
            
            // Security tracking
            created: userData.created || new Date(),
            lastLogin: null,
            loginCount: 0,
            failedLoginAttempts: 0,
            lastFailedLogin: null,
            passwordChanged: new Date(),
            passwordHistory: [],
            
            // MFA settings
            mfaEnabled: false,
            mfaSecret: null,
            mfaBackupCodes: [],
            mfaDevices: [],
            
            // Session management
            activeSessions: [],
            maxSessions: this.securityPolicies.get('authentication').concurrentSessions,
            
            // Compliance
            accessReviewDate: new Date(Date.now() + this.securityPolicies.get('compliance').accessReviewInterval),
            lastAccessReview: new Date(),
            
            // Metadata
            metadata: userData.metadata || {}
        };

        this.users.set(userId, user);

        // Audit log
        this.auditLog.push({
            timestamp: new Date(),
            action: 'user_created',
            userId: userId,
            username: userData.username,
            role: userData.role,
            createdBy: userData.createdBy || 'system'
        });

        this.emit('userCreated', { userId, username: userData.username, role: userData.role });

        return {
            id: userId,
            username: userData.username,
            role: userData.role,
            created: user.created
        };
    }

    async authenticateUser(username, password, context = {}) {
        const user = Array.from(this.users.values()).find(u => u.username === username);
        
        // Check if user exists
        if (!user) {
            await this.recordFailedLogin(username, 'user_not_found', context);
            return { success: false, error: 'Invalid credentials' };
        }

        // Check account status
        if (user.status !== 'active') {
            await this.recordFailedLogin(username, 'account_inactive', context);
            return { success: false, error: 'Account is not active' };
        }

        // Check if account is locked
        if (await this.isAccountLocked(user.id)) {
            await this.recordFailedLogin(username, 'account_locked', context);
            return { success: false, error: 'Account is temporarily locked' };
        }

        // Verify password
        const passwordValid = await argon2.verify(user.passwordHash, password);
        if (!passwordValid) {
            await this.recordFailedLogin(username, 'invalid_password', context);
            user.failedLoginAttempts++;
            user.lastFailedLogin = new Date();
            return { success: false, error: 'Invalid credentials' };
        }

        // Check if password change is required
        if (user.forcePasswordChange) {
            return { success: false, error: 'Password change required', requirePasswordChange: true };
        }

        // Check password age
        const passwordAge = Date.now() - user.passwordChanged.getTime();
        const maxPasswordAge = this.securityPolicies.get('password').maxAge;
        if (passwordAge > maxPasswordAge) {
            return { success: false, error: 'Password has expired', requirePasswordChange: true };
        }

        // Check MFA requirement
        if (this.securityPolicies.get('authentication').mfaRequired && !user.mfaEnabled) {
            return { success: false, error: 'MFA setup required', requireMfaSetup: true };
        }

        // Reset failed login attempts on successful authentication
        user.failedLoginAttempts = 0;
        user.lastFailedLogin = null;

        // Update login tracking
        user.lastLogin = new Date();
        user.loginCount++;

        // Audit successful login
        this.auditLog.push({
            timestamp: new Date(),
            action: 'user_login_success',
            userId: user.id,
            username: user.username,
            context: context
        });

        this.emit('userAuthenticated', { 
            userId: user.id, 
            username: user.username, 
            role: user.role,
            context 
        });

        return { 
            success: true, 
            user: {
                id: user.id,
                username: user.username,
                role: user.role,
                permissions: user.permissions,
                requireMfa: user.mfaEnabled
            }
        };
    }

    async validateMFA(userId, token, deviceId = null) {
        const user = this.users.get(userId);
        if (!user) {
            throw new Error('User not found');
        }

        if (!user.mfaEnabled || !user.mfaSecret) {
            throw new Error('MFA not enabled for user');
        }

        // Verify TOTP token
        const verified = speakeasy.totp.verify({
            secret: user.mfaSecret,
            encoding: 'base32',
            token: token,
            window: 2 // Allow 2 time steps (60 seconds) variance
        });

        if (!verified) {
            // Check backup codes
            const backupCodeIndex = user.mfaBackupCodes.findIndex(
                code => code.code === token && !code.used
            );
            
            if (backupCodeIndex === -1) {
                this.auditLog.push({
                    timestamp: new Date(),
                    action: 'mfa_failed',
                    userId: userId,
                    deviceId: deviceId
                });
                return { success: false, error: 'Invalid MFA token' };
            }

            // Mark backup code as used
            user.mfaBackupCodes[backupCodeIndex].used = true;
            user.mfaBackupCodes[backupCodeIndex].usedAt = new Date();
        }

        this.auditLog.push({
            timestamp: new Date(),
            action: 'mfa_success',
            userId: userId,
            deviceId: deviceId,
            method: verified ? 'totp' : 'backup_code'
        });

        return { success: true };
    }

    async setupMFA(userId) {
        const user = this.users.get(userId);
        if (!user) {
            throw new Error('User not found');
        }

        // Generate secret
        const secret = speakeasy.generateSecret({
            name: `ActiveLog Enterprise (${user.username})`,
            issuer: 'ActiveLog Enterprise'
        });

        // Generate backup codes
        const backupCodes = Array.from({ length: 10 }, () => ({
            code: crypto.randomBytes(4).toString('hex').toUpperCase(),
            used: false,
            usedAt: null
        }));

        // Generate QR code
        const qrCodeUrl = await qrcode.toDataURL(secret.otpauth_url);

        // Store MFA configuration (not yet enabled)
        user.mfaTempSecret = secret.base32;
        user.mfaTempBackupCodes = backupCodes;

        this.emit('mfaSetupInitiated', { userId, username: user.username });

        return {
            secret: secret.base32,
            qrCode: qrCodeUrl,
            backupCodes: backupCodes.map(bc => bc.code)
        };
    }

    async confirmMfaSetup(userId, token) {
        const user = this.users.get(userId);
        if (!user || !user.mfaTempSecret) {
            throw new Error('MFA setup not initiated');
        }

        // Verify the token
        const verified = speakeasy.totp.verify({
            secret: user.mfaTempSecret,
            encoding: 'base32',
            token: token,
            window: 2
        });

        if (!verified) {
            return { success: false, error: 'Invalid token' };
        }

        // Enable MFA
        user.mfaEnabled = true;
        user.mfaSecret = user.mfaTempSecret;
        user.mfaBackupCodes = user.mfaTempBackupCodes;
        
        // Clean up temporary data
        delete user.mfaTempSecret;
        delete user.mfaTempBackupCodes;

        this.auditLog.push({
            timestamp: new Date(),
            action: 'mfa_enabled',
            userId: userId,
            username: user.username
        });

        this.emit('mfaEnabled', { userId, username: user.username });

        return { success: true };
    }

    async createSession(userId, context = {}) {
        const user = this.users.get(userId);
        if (!user) {
            throw new Error('User not found');
        }

        // Check concurrent session limit
        if (user.activeSessions.length >= user.maxSessions) {
            // Terminate oldest session
            const oldestSession = user.activeSessions.shift();
            this.sessions.delete(oldestSession.id);
        }

        const sessionId = crypto.randomBytes(32).toString('hex');
        const session = {
            id: sessionId,
            userId: userId,
            created: new Date(),
            lastAccessed: new Date(),
            expiresAt: new Date(Date.now() + this.securityPolicies.get('authentication').sessionTimeout),
            context: context,
            permissions: user.permissions,
            role: user.role,
            status: 'active'
        };

        this.sessions.set(sessionId, session);
        user.activeSessions.push({ id: sessionId, created: session.created });

        // Generate JWT token
        const token = jwt.sign(
            {
                userId: userId,
                sessionId: sessionId,
                role: user.role,
                permissions: user.permissions
            },
            process.env.JWT_SECRET || 'default-secret-change-in-production',
            {
                expiresIn: '15m',
                issuer: 'activelog-enterprise',
                subject: userId,
                jwtid: sessionId
            }
        );

        this.auditLog.push({
            timestamp: new Date(),
            action: 'session_created',
            userId: userId,
            sessionId: sessionId,
            context: context
        });

        this.emit('sessionCreated', { userId, sessionId, context });

        return {
            sessionId,
            token,
            expiresAt: session.expiresAt,
            user: {
                id: userId,
                username: user.username,
                role: user.role,
                permissions: user.permissions
            }
        };
    }

    async validateSession(sessionId) {
        const session = this.sessions.get(sessionId);
        if (!session) {
            return { valid: false, error: 'Session not found' };
        }

        if (session.status !== 'active') {
            return { valid: false, error: 'Session is not active' };
        }

        if (Date.now() > session.expiresAt.getTime()) {
            session.status = 'expired';
            return { valid: false, error: 'Session expired' };
        }

        // Update last accessed
        session.lastAccessed = new Date();

        const user = this.users.get(session.userId);
        if (!user || user.status !== 'active') {
            return { valid: false, error: 'User account not active' };
        }

        return {
            valid: true,
            session: {
                id: session.id,
                userId: session.userId,
                role: session.role,
                permissions: session.permissions,
                expiresAt: session.expiresAt
            },
            user: {
                id: user.id,
                username: user.username,
                role: user.role,
                permissions: user.permissions
            }
        };
    }

    async hasPermission(userId, permission, resource = null) {
        const user = this.users.get(userId);
        if (!user || user.status !== 'active') {
            return false;
        }

        // Check direct permission
        if (user.permissions.includes(permission)) {
            return true;
        }

        // Check wildcard permissions
        if (user.permissions.includes('*') || user.permissions.includes('all')) {
            return true;
        }

        // Check role-based permissions with resource context
        if (resource) {
            return await this.checkResourcePermission(user, permission, resource);
        }

        return false;
    }

    async checkResourcePermission(user, permission, resource) {
        // Resource-based permission checking logic
        // This would be expanded based on specific resource requirements
        
        if (resource.owner === user.id && permission.startsWith('read_own')) {
            return true;
        }

        if (resource.team === user.team && permission.startsWith('read_team')) {
            return true;
        }

        return false;
    }

    async validatePasswordPolicy(password) {
        const policy = this.securityPolicies.get('password');
        const errors = [];

        // Length check
        if (password.length < policy.minLength) {
            errors.push(`Password must be at least ${policy.minLength} characters`);
        }

        // Complexity checks
        if (policy.requireUppercase && !/[A-Z]/.test(password)) {
            errors.push('Password must contain at least one uppercase letter');
        }

        if (policy.requireLowercase && !/[a-z]/.test(password)) {
            errors.push('Password must contain at least one lowercase letter');
        }

        if (policy.requireNumbers && !/\d/.test(password)) {
            errors.push('Password must contain at least one number');
        }

        if (policy.requireSpecialChars && !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
            errors.push('Password must contain at least one special character');
        }

        // Calculate complexity score
        const complexityScore = this.calculatePasswordComplexity(password);
        if (complexityScore < policy.complexityScore) {
            errors.push(`Password complexity score too low (${complexityScore}/${policy.complexityScore})`);
        }

        if (errors.length > 0) {
            throw new Error(`Password policy violations: ${errors.join(', ')}`);
        }

        return true;
    }

    calculatePasswordComplexity(password) {
        let score = 0;
        
        // Length bonus
        score += Math.min(password.length / 4, 6);
        
        // Character variety bonus
        if (/[a-z]/.test(password)) score += 1;
        if (/[A-Z]/.test(password)) score += 1;
        if (/\d/.test(password)) score += 1;
        if (/[^a-zA-Z0-9]/.test(password)) score += 1;
        
        // Penalty for patterns
        if (/(.)\1{2,}/.test(password)) score -= 1; // Repeated characters
        if (/012|123|234|345|456|567|678|789|890/.test(password)) score -= 1; // Sequential numbers
        if (/abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz/.test(password.toLowerCase())) score -= 1; // Sequential letters

        return Math.max(0, score);
    }

    async recordFailedLogin(username, reason, context) {
        const key = `${context.ip || 'unknown'}_${username}`;
        const now = Date.now();
        
        if (!this.loginAttempts.has(key)) {
            this.loginAttempts.set(key, { count: 0, lastAttempt: now, locked: false });
        }

        const attempts = this.loginAttempts.get(key);
        attempts.count++;
        attempts.lastAttempt = now;

        // Check if should be locked
        const maxAttempts = this.securityPolicies.get('authentication').maxLoginAttempts;
        const lockoutDuration = this.securityPolicies.get('authentication').lockoutDuration;
        
        if (attempts.count >= maxAttempts) {
            attempts.locked = true;
            attempts.lockedUntil = now + lockoutDuration;
        }

        // Audit log
        this.auditLog.push({
            timestamp: new Date(),
            action: 'login_failed',
            username: username,
            reason: reason,
            context: context,
            attempts: attempts.count
        });

        this.emit('loginFailed', { username, reason, attempts: attempts.count, context });
    }

    async isAccountLocked(userId) {
        const user = this.users.get(userId);
        if (!user) return true;

        const maxAttempts = this.securityPolicies.get('authentication').maxLoginAttempts;
        const lockoutDuration = this.securityPolicies.get('authentication').lockoutDuration;

        if (user.failedLoginAttempts >= maxAttempts) {
            const lockoutExpiry = user.lastFailedLogin.getTime() + lockoutDuration;
            return Date.now() < lockoutExpiry;
        }

        return false;
    }

    // Middleware functions
    requireAuth() {
        return async (req, res, next) => {
            try {
                const token = req.headers.authorization?.replace('Bearer ', '');
                if (!token) {
                    return res.status(401).json({ error: 'Authentication required' });
                }

                const decoded = jwt.verify(token, process.env.JWT_SECRET || 'default-secret-change-in-production');
                const sessionValidation = await this.validateSession(decoded.sessionId);

                if (!sessionValidation.valid) {
                    return res.status(401).json({ error: sessionValidation.error });
                }

                req.user = sessionValidation.user;
                req.session = sessionValidation.session;
                next();
            } catch (error) {
                res.status(401).json({ error: 'Invalid authentication token' });
            }
        };
    }

    requireRole(roles) {
        return (req, res, next) => {
            if (!req.user) {
                return res.status(401).json({ error: 'Authentication required' });
            }

            const userRoles = Array.isArray(roles) ? roles : [roles];
            if (!userRoles.includes(req.user.role)) {
                return res.status(403).json({ error: 'Insufficient privileges' });
            }

            next();
        };
    }

    requirePermission(permission) {
        return async (req, res, next) => {
            if (!req.user) {
                return res.status(401).json({ error: 'Authentication required' });
            }

            const hasPermission = await this.hasPermission(req.user.id, permission);
            if (!hasPermission) {
                return res.status(403).json({ error: 'Insufficient permissions' });
            }

            next();
        };
    }

    getRoutes() {
        const router = require('express').Router();

        // Login endpoint
        router.post('/login', async (req, res) => {
            try {
                const { username, password, mfaToken } = req.body;
                
                const authResult = await this.authenticateUser(username, password, {
                    ip: req.ip,
                    userAgent: req.get('user-agent')
                });

                if (!authResult.success) {
                    return res.status(401).json(authResult);
                }

                // Check MFA if required
                if (authResult.user.requireMfa && !mfaToken) {
                    return res.status(200).json({ 
                        requireMfa: true, 
                        userId: authResult.user.id,
                        message: 'MFA token required' 
                    });
                }

                if (mfaToken) {
                    const mfaResult = await this.validateMFA(authResult.user.id, mfaToken);
                    if (!mfaResult.success) {
                        return res.status(401).json(mfaResult);
                    }
                }

                // Create session
                const session = await this.createSession(authResult.user.id, {
                    ip: req.ip,
                    userAgent: req.get('user-agent')
                });

                res.json({
                    success: true,
                    token: session.token,
                    expiresAt: session.expiresAt,
                    user: session.user
                });

            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        // MFA setup endpoints
        router.post('/mfa/setup', this.requireAuth(), async (req, res) => {
            try {
                const result = await this.setupMFA(req.user.id);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        router.post('/mfa/confirm', this.requireAuth(), async (req, res) => {
            try {
                const { token } = req.body;
                const result = await this.confirmMfaSetup(req.user.id, token);
                res.json(result);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        // User management endpoints
        router.post('/users', this.requireRole(['system_admin', 'security_admin']), async (req, res) => {
            try {
                const user = await this.createUser({
                    ...req.body,
                    createdBy: req.user.id
                });
                res.json(user);
            } catch (error) {
                res.status(400).json({ error: error.message });
            }
        });

        router.get('/users', this.requireRole(['admin', 'security_admin', 'system_admin']), (req, res) => {
            const users = Array.from(this.users.values()).map(user => ({
                id: user.id,
                username: user.username,
                email: user.email,
                role: user.role,
                status: user.status,
                created: user.created,
                lastLogin: user.lastLogin,
                mfaEnabled: user.mfaEnabled
            }));
            res.json(users);
        });

        // Session management
        router.delete('/sessions/:sessionId', this.requireAuth(), async (req, res) => {
            try {
                const { sessionId } = req.params;
                const session = this.sessions.get(sessionId);
                
                if (session && (session.userId === req.user.id || req.user.role === 'system_admin')) {
                    this.sessions.delete(sessionId);
                    res.json({ success: true });
                } else {
                    res.status(404).json({ error: 'Session not found' });
                }
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        return router;
    }

    // Placeholder implementations for external auth providers
    async syncLdapUser(profile) {
        // Implementation for LDAP user synchronization
        return profile;
    }

    async syncSamlUser(profile) {
        // Implementation for SAML user synchronization  
        return profile;
    }
}

module.exports = InternalAuthSystem;