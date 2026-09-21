export class AuthManager {
    constructor() {
        this.currentUser = null;
        this.authConfig = {};
        this.providers = new Map();
        this.tokenManager = null;
        this.initialized = false;
    }

    static instance = null;

    static getInstance() {
        if (!AuthManager.instance) {
            AuthManager.instance = new AuthManager();
        }
        return AuthManager.instance;
    }

    async init(config = {}) {
        if (this.initialized) return;

        this.authConfig = {
            providers: ['email'],
            requireEmailVerification: false,
            enableTwoFactor: false,
            sessionDuration: '30d',
            rememberDevice: true,
            crossAppAuth: true,
            ...config
        };

        await this.initializeProviders();
        await this.initializeTokenManager();
        await this.checkExistingSession();

        this.initialized = true;
        console.log('AuthManager initialized with providers:', this.authConfig.providers);
    }

    async initializeProviders() {
        for (const providerName of this.authConfig.providers) {
            try {
                const provider = await this.loadProvider(providerName);
                this.providers.set(providerName, provider);
                console.log(`Loaded auth provider: ${providerName}`);
            } catch (error) {
                console.warn(`Failed to load auth provider ${providerName}:`, error);
            }
        }
    }

    async loadProvider(providerName) {
        switch (providerName) {
            case 'email':
                const { EmailAuthProvider } = await import('./providers/EmailAuthProvider.js');
                return new EmailAuthProvider(this.authConfig);
                
            case 'google':
                const { GoogleAuthProvider } = await import('./providers/GoogleAuthProvider.js');
                return new GoogleAuthProvider(this.authConfig);
                
            case 'facebook':
                const { FacebookAuthProvider } = await import('./providers/FacebookAuthProvider.js');
                return new FacebookAuthProvider(this.authConfig);
                
            case 'apple':
                const { AppleAuthProvider } = await import('./providers/AppleAuthProvider.js');
                return new AppleAuthProvider(this.authConfig);
                
            case 'microsoft':
                const { MicrosoftAuthProvider } = await import('./providers/MicrosoftAuthProvider.js');
                return new MicrosoftAuthProvider(this.authConfig);
                
            case 'discord':
                const { DiscordAuthProvider } = await import('./providers/DiscordAuthProvider.js');
                return new DiscordAuthProvider(this.authConfig);
                
            case 'steam':
                const { SteamAuthProvider } = await import('./providers/SteamAuthProvider.js');
                return new SteamAuthProvider(this.authConfig);
                
            case 'sso':
            case 'okta':
            case 'active-directory':
            case 'ldap':
            case 'saml':
                const { EnterpriseAuthProvider } = await import('./providers/EnterpriseAuthProvider.js');
                return new EnterpriseAuthProvider(this.authConfig, providerName);
                
            default:
                throw new Error(`Unknown auth provider: ${providerName}`);
        }
    }

    async initializeTokenManager() {
        const { TokenManager } = await import('./TokenManager.js');
        this.tokenManager = new TokenManager({
            sessionDuration: this.authConfig.sessionDuration,
            rememberDevice: this.authConfig.rememberDevice,
            crossAppSupport: this.authConfig.crossAppAuth
        });
        await this.tokenManager.init();
    }

    async checkExistingSession() {
        const token = await this.tokenManager.getValidToken();
        if (token) {
            try {
                this.currentUser = await this.validateToken(token);
                this.emitAuthEvent('session-restored', this.currentUser);
                console.log('Session restored for user:', this.currentUser.email);
            } catch (error) {
                console.warn('Invalid existing session, clearing token');
                await this.tokenManager.clearToken();
            }
        }
    }

    async signIn(providerName, credentials = {}) {
        const provider = this.providers.get(providerName);
        if (!provider) {
            throw new Error(`Auth provider ${providerName} not available`);
        }

        try {
            const authResult = await provider.signIn(credentials);
            
            if (this.authConfig.requireEmailVerification && !authResult.emailVerified) {
                await this.sendEmailVerification(authResult.user);
                throw new Error('Email verification required');
            }

            if (this.authConfig.enableTwoFactor && !authResult.twoFactorVerified) {
                return { requiresTwoFactor: true, user: authResult.user };
            }

            await this.completeSignIn(authResult);
            return { success: true, user: this.currentUser };

        } catch (error) {
            this.emitAuthEvent('sign-in-error', { provider: providerName, error });
            throw error;
        }
    }

    async signUp(providerName, credentials = {}) {
        const provider = this.providers.get(providerName);
        if (!provider) {
            throw new Error(`Auth provider ${providerName} not available`);
        }

        try {
            const authResult = await provider.signUp(credentials);
            
            if (this.authConfig.requireEmailVerification) {
                await this.sendEmailVerification(authResult.user);
                return { success: true, requiresEmailVerification: true, user: authResult.user };
            }

            await this.completeSignIn(authResult);
            return { success: true, user: this.currentUser };

        } catch (error) {
            this.emitAuthEvent('sign-up-error', { provider: providerName, error });
            throw error;
        }
    }

    async signOut() {
        if (!this.currentUser) return;

        try {
            const provider = this.providers.get(this.currentUser.provider);
            if (provider && provider.signOut) {
                await provider.signOut();
            }

            await this.tokenManager.clearToken();
            
            const user = this.currentUser;
            this.currentUser = null;
            
            this.emitAuthEvent('sign-out', user);
            console.log('User signed out successfully');

        } catch (error) {
            console.error('Error during sign out:', error);
            throw error;
        }
    }

    async completeSignIn(authResult) {
        this.currentUser = {
            id: authResult.user.id,
            email: authResult.user.email,
            name: authResult.user.name,
            provider: authResult.provider,
            roles: authResult.user.roles || [],
            permissions: authResult.user.permissions || [],
            apps: authResult.user.apps || [],
            lastSignIn: new Date(),
            ...authResult.user
        };

        await this.tokenManager.storeToken(authResult.token, this.currentUser);
        this.emitAuthEvent('sign-in', this.currentUser);
        
        console.log('User signed in successfully:', this.currentUser.email);
    }

    async validateToken(token) {
        try {
            const response = await fetch('/api/auth/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Token validation failed');
            }

            const result = await response.json();
            return result.user;

        } catch (error) {
            throw new Error('Token validation failed');
        }
    }

    async sendEmailVerification(user) {
        try {
            const response = await fetch('/api/auth/send-verification', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: user.email })
            });

            if (!response.ok) {
                throw new Error('Failed to send verification email');
            }

            console.log('Verification email sent to:', user.email);
        } catch (error) {
            console.error('Error sending verification email:', error);
            throw error;
        }
    }

    async verifyTwoFactor(code) {
        if (!this.currentUser) {
            throw new Error('No user context for two-factor verification');
        }

        try {
            const response = await fetch('/api/auth/verify-2fa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    userId: this.currentUser.id, 
                    code 
                })
            });

            if (!response.ok) {
                throw new Error('Two-factor verification failed');
            }

            const result = await response.json();
            await this.completeSignIn(result);
            
            return { success: true, user: this.currentUser };

        } catch (error) {
            this.emitAuthEvent('2fa-error', error);
            throw error;
        }
    }

    async switchApp(appDomain) {
        if (!this.currentUser) {
            throw new Error('No authenticated user');
        }

        if (!this.currentUser.apps.includes(appDomain)) {
            throw new Error('User not authorized for this app');
        }

        try {
            const appToken = await this.tokenManager.getAppToken(appDomain);
            this.emitAuthEvent('app-switch', { user: this.currentUser, app: appDomain });
            
            return appToken;

        } catch (error) {
            console.error('Error switching app:', error);
            throw error;
        }
    }

    async refreshToken() {
        if (!this.currentUser) return null;

        try {
            const newToken = await this.tokenManager.refreshToken();
            this.emitAuthEvent('token-refreshed', this.currentUser);
            return newToken;
            
        } catch (error) {
            console.error('Token refresh failed:', error);
            await this.signOut();
            throw error;
        }
    }

    getCurrentUser() {
        return this.currentUser;
    }

    isAuthenticated() {
        return !!this.currentUser;
    }

    hasPermission(permission) {
        if (!this.currentUser) return false;
        return this.currentUser.permissions.includes(permission);
    }

    hasRole(role) {
        if (!this.currentUser) return false;
        return this.currentUser.roles.includes(role);
    }

    hasAppAccess(appDomain) {
        if (!this.currentUser) return false;
        return this.currentUser.apps.includes(appDomain);
    }

    emitAuthEvent(eventName, data) {
        const event = new CustomEvent(`auth:${eventName}`, { 
            detail: data 
        });
        document.dispatchEvent(event);
    }

    onAuthEvent(eventName, callback) {
        document.addEventListener(`auth:${eventName}`, callback);
    }

    offAuthEvent(eventName, callback) {
        document.removeEventListener(`auth:${eventName}`, callback);
    }

    destroy() {
        this.currentUser = null;
        this.providers.clear();
        this.tokenManager = null;
        this.initialized = false;
    }
}

export default AuthManager.getInstance();