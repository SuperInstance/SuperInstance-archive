/**
 * Authentication Manager
 */

import { ApiClient } from './api.js';
import { EventEmitter } from './events.js';

class AuthManagerClass extends EventEmitter {
    constructor() {
        super();
        this.user = null;
        this.token = null;
        this.refreshToken = null;
    }

    async init() {
        // Try to restore session from localStorage
        this.token = localStorage.getItem('auth_token');
        this.refreshToken = localStorage.getItem('refresh_token');
        
        if (this.token) {
            try {
                // Validate token and get user info
                const userInfo = await this.getCurrentUser();
                if (userInfo) {
                    this.user = userInfo;
                    this.emit('login', this.user);
                } else {
                    // Token is invalid, clear it
                    this.clearTokens();
                }
            } catch (error) {
                console.warn('Failed to validate stored token:', error);
                this.clearTokens();
            }
        }
    }

    async login(email, password) {
        try {
            const response = await ApiClient.post('/auth/login', {
                email,
                password
            });

            if (response.access_token) {
                this.token = response.access_token;
                this.refreshToken = response.refresh_token;
                this.user = response.user;
                
                // Store tokens
                localStorage.setItem('auth_token', this.token);
                if (this.refreshToken) {
                    localStorage.setItem('refresh_token', this.refreshToken);
                }
                
                // Update API client default headers
                ApiClient.setAuthToken(this.token);
                
                this.emit('login', this.user);
                
                return { success: true, user: this.user };
            } else {
                return { success: false, error: 'Invalid response from server' };
            }
        } catch (error) {
            console.error('Login error:', error);
            return { 
                success: false, 
                error: error.message || 'Login failed'
            };
        }
    }

    async register(userData) {
        try {
            const response = await ApiClient.post('/auth/register', userData);
            
            return { success: true, user: response.user };
        } catch (error) {
            console.error('Registration error:', error);
            return { 
                success: false, 
                error: error.message || 'Registration failed'
            };
        }
    }

    async logout() {
        try {
            // Call logout endpoint if token exists
            if (this.token) {
                await ApiClient.post('/auth/logout');
            }
        } catch (error) {
            console.warn('Logout API call failed:', error);
        } finally {
            this.clearSession();
            this.emit('logout');
        }
    }

    async refreshAccessToken() {
        if (!this.refreshToken) {
            throw new Error('No refresh token available');
        }

        try {
            const response = await ApiClient.post('/auth/refresh', {
                refresh_token: this.refreshToken
            });

            this.token = response.access_token;
            localStorage.setItem('auth_token', this.token);
            ApiClient.setAuthToken(this.token);

            return this.token;
        } catch (error) {
            console.error('Token refresh failed:', error);
            this.clearSession();
            this.emit('logout');
            throw error;
        }
    }

    async getCurrentUser() {
        if (!this.token) {
            return null;
        }

        try {
            const response = await ApiClient.get('/auth/me');
            return response;
        } catch (error) {
            console.error('Get current user failed:', error);
            return null;
        }
    }

    clearSession() {
        this.user = null;
        this.token = null;
        this.refreshToken = null;
        this.clearTokens();
        ApiClient.setAuthToken(null);
    }

    clearTokens() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
    }

    isAuthenticated() {
        return !!this.token && !!this.user;
    }

    getUser() {
        return this.user;
    }

    getToken() {
        return this.token;
    }

    hasRole(role) {
        return this.user?.role === role || this.user?.roles?.includes(role);
    }

    hasPermission(permission) {
        return this.user?.permissions?.includes(permission);
    }
}

export const AuthManager = new AuthManagerClass();