export class TokenManager {
    constructor(config = {}) {
        this.config = {
            sessionDuration: '30d',
            rememberDevice: true,
            crossAppSupport: true,
            tokenKey: 'activelog_auth_token',
            refreshThreshold: 5 * 60 * 1000, // 5 minutes
            ...config
        };
        
        this.storage = null;
        this.currentToken = null;
        this.refreshTimer = null;
    }

    async init() {
        this.storage = this.config.rememberDevice ? localStorage : sessionStorage;
        this.currentToken = this.getStoredToken();
        
        if (this.currentToken) {
            this.scheduleRefresh();
        }
    }

    async storeToken(token, user) {
        const tokenData = {
            token,
            user,
            issuedAt: Date.now(),
            expiresAt: this.calculateExpiration(),
            apps: this.generateAppTokens(user.apps || [])
        };

        this.currentToken = tokenData;
        this.storage.setItem(this.config.tokenKey, JSON.stringify(tokenData));
        
        if (this.config.crossAppSupport) {
            this.storeCrossAppToken(tokenData);
        }
        
        this.scheduleRefresh();
        console.log('Token stored successfully');
    }

    getStoredToken() {
        try {
            const stored = this.storage.getItem(this.config.tokenKey);
            if (!stored) return null;
            
            const tokenData = JSON.parse(stored);
            
            if (this.isTokenExpired(tokenData)) {
                this.clearToken();
                return null;
            }
            
            return tokenData;
        } catch (error) {
            console.error('Error reading stored token:', error);
            this.clearToken();
            return null;
        }
    }

    async getValidToken() {
        if (!this.currentToken) {
            this.currentToken = this.getStoredToken();
        }

        if (!this.currentToken) return null;

        if (this.isTokenExpired(this.currentToken)) {
            try {
                await this.refreshToken();
            } catch (error) {
                console.error('Token refresh failed:', error);
                this.clearToken();
                return null;
            }
        }

        return this.currentToken.token;
    }

    async getAppToken(appDomain) {
        if (!this.currentToken) {
            throw new Error('No authentication token available');
        }

        const appTokens = this.currentToken.apps || {};
        let appToken = appTokens[appDomain];

        if (!appToken || this.isTokenExpired({ expiresAt: appToken.expiresAt })) {
            appToken = await this.generateAppToken(appDomain);
            
            this.currentToken.apps = this.currentToken.apps || {};
            this.currentToken.apps[appDomain] = appToken;
            
            this.storage.setItem(this.config.tokenKey, JSON.stringify(this.currentToken));
        }

        return appToken.token;
    }

    async generateAppToken(appDomain) {
        try {
            const response = await fetch('/api/auth/app-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.currentToken.token}`
                },
                body: JSON.stringify({ appDomain })
            });

            if (!response.ok) {
                throw new Error('Failed to generate app token');
            }

            const result = await response.json();
            return {
                token: result.token,
                expiresAt: result.expiresAt
            };

        } catch (error) {
            console.error('Error generating app token:', error);
            throw error;
        }
    }

    generateAppTokens(apps) {
        const appTokens = {};
        apps.forEach(app => {
            appTokens[app] = {
                token: `${this.currentToken?.token}.${app}`,
                expiresAt: this.calculateExpiration()
            };
        });
        return appTokens;
    }

    async refreshToken() {
        if (!this.currentToken) {
            throw new Error('No token to refresh');
        }

        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.currentToken.token}`
                }
            });

            if (!response.ok) {
                throw new Error('Token refresh failed');
            }

            const result = await response.json();
            
            const newTokenData = {
                ...this.currentToken,
                token: result.token,
                issuedAt: Date.now(),
                expiresAt: this.calculateExpiration()
            };

            this.currentToken = newTokenData;
            this.storage.setItem(this.config.tokenKey, JSON.stringify(newTokenData));
            
            if (this.config.crossAppSupport) {
                this.storeCrossAppToken(newTokenData);
            }
            
            this.scheduleRefresh();
            console.log('Token refreshed successfully');
            
            return result.token;

        } catch (error) {
            console.error('Token refresh error:', error);
            throw error;
        }
    }

    storeCrossAppToken(tokenData) {
        try {
            const crossAppData = {
                token: tokenData.token,
                user: {
                    id: tokenData.user.id,
                    email: tokenData.user.email,
                    name: tokenData.user.name,
                    apps: tokenData.user.apps
                },
                expiresAt: tokenData.expiresAt
            };
            
            localStorage.setItem('activelog_cross_app_token', JSON.stringify(crossAppData));
        } catch (error) {
            console.warn('Failed to store cross-app token:', error);
        }
    }

    getCrossAppToken() {
        try {
            const stored = localStorage.getItem('activelog_cross_app_token');
            if (!stored) return null;
            
            const tokenData = JSON.parse(stored);
            
            if (this.isTokenExpired(tokenData)) {
                localStorage.removeItem('activelog_cross_app_token');
                return null;
            }
            
            return tokenData;
        } catch (error) {
            console.error('Error reading cross-app token:', error);
            localStorage.removeItem('activelog_cross_app_token');
            return null;
        }
    }

    clearToken() {
        this.currentToken = null;
        this.storage.removeItem(this.config.tokenKey);
        
        if (this.config.crossAppSupport) {
            localStorage.removeItem('activelog_cross_app_token');
        }
        
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
            this.refreshTimer = null;
        }
        
        console.log('Token cleared');
    }

    scheduleRefresh() {
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
        }

        if (!this.currentToken) return;

        const timeUntilExpiry = this.currentToken.expiresAt - Date.now();
        const timeUntilRefresh = timeUntilExpiry - this.config.refreshThreshold;

        if (timeUntilRefresh > 0) {
            this.refreshTimer = setTimeout(async () => {
                try {
                    await this.refreshToken();
                } catch (error) {
                    console.error('Scheduled token refresh failed:', error);
                }
            }, timeUntilRefresh);
        }
    }

    calculateExpiration() {
        const duration = this.parseDuration(this.config.sessionDuration);
        return Date.now() + duration;
    }

    parseDuration(duration) {
        const units = {
            's': 1000,
            'm': 60 * 1000,
            'h': 60 * 60 * 1000,
            'd': 24 * 60 * 60 * 1000
        };

        const match = duration.match(/^(\d+)([smhd])$/);
        if (!match) {
            console.warn('Invalid duration format, defaulting to 30 days');
            return 30 * units.d;
        }

        const value = parseInt(match[1]);
        const unit = match[2];
        
        return value * units[unit];
    }

    isTokenExpired(tokenData) {
        if (!tokenData || !tokenData.expiresAt) return true;
        return Date.now() >= tokenData.expiresAt;
    }

    getTokenInfo() {
        if (!this.currentToken) return null;
        
        return {
            issuedAt: new Date(this.currentToken.issuedAt),
            expiresAt: new Date(this.currentToken.expiresAt),
            timeUntilExpiry: this.currentToken.expiresAt - Date.now(),
            user: this.currentToken.user,
            apps: Object.keys(this.currentToken.apps || {})
        };
    }

    destroy() {
        this.clearToken();
        this.currentToken = null;
        this.storage = null;
    }
}