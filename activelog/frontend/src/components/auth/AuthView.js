/**
 * Authentication View Component
 */

import { AuthManager } from '../../utils/auth.js';
import { NotificationManager } from '../../utils/notifications.js';

export class AuthView {
    constructor(mode = 'login') {
        this.mode = mode; // 'login' or 'register'
        this.isLoading = false;
    }

    async render(container) {
        container.innerHTML = `
            <div class="auth-container">
                <div class="auth-card">
                    <div class="auth-header">
                        <h1 class="auth-title">
                            <span class="logo">🚀</span>
                            ActiveLog.ai
                        </h1>
                        <p class="auth-subtitle">
                            ${this.mode === 'login' ? 'Welcome back!' : 'Create your account'}
                        </p>
                    </div>
                    
                    <form id="auth-form" class="auth-form">
                        ${this.mode === 'register' ? `
                            <div class="form-group">
                                <label for="name">Full Name</label>
                                <input type="text" id="name" name="name" required 
                                       placeholder="Enter your full name">
                            </div>
                        ` : ''}
                        
                        <div class="form-group">
                            <label for="email">Email Address</label>
                            <input type="email" id="email" name="email" required 
                                   placeholder="Enter your email">
                        </div>
                        
                        <div class="form-group">
                            <label for="password">Password</label>
                            <input type="password" id="password" name="password" required 
                                   placeholder="Enter your password">
                        </div>
                        
                        ${this.mode === 'register' ? `
                            <div class="form-group">
                                <label for="confirmPassword">Confirm Password</label>
                                <input type="password" id="confirmPassword" name="confirmPassword" required 
                                       placeholder="Confirm your password">
                            </div>
                        ` : ''}
                        
                        <button type="submit" class="auth-button" id="auth-submit">
                            <span class="button-text">
                                ${this.mode === 'login' ? 'Sign In' : 'Create Account'}
                            </span>
                            <span class="button-spinner" style="display: none;">
                                <div class="spinner"></div>
                            </span>
                        </button>
                        
                        ${this.mode === 'login' ? `
                            <div class="form-footer">
                                <a href="#" id="forgot-password">Forgot password?</a>
                            </div>
                        ` : ''}
                    </form>
                    
                    <div class="auth-switch">
                        ${this.mode === 'login' ? `
                            <p>Don't have an account? 
                               <a href="#" id="switch-to-register">Create one</a>
                            </p>
                        ` : `
                            <p>Already have an account? 
                               <a href="#" id="switch-to-login">Sign in</a>
                            </p>
                        `}
                    </div>
                </div>
                
                <div class="auth-background">
                    <div class="bg-animation"></div>
                </div>
            </div>
        `;

        this.attachEventListeners();
    }

    attachEventListeners() {
        const form = document.getElementById('auth-form');
        const switchToRegister = document.getElementById('switch-to-register');
        const switchToLogin = document.getElementById('switch-to-login');
        const forgotPassword = document.getElementById('forgot-password');

        form?.addEventListener('submit', (e) => this.handleSubmit(e));
        switchToRegister?.addEventListener('click', (e) => this.switchMode(e, 'register'));
        switchToLogin?.addEventListener('click', (e) => this.switchMode(e, 'login'));
        forgotPassword?.addEventListener('click', (e) => this.handleForgotPassword(e));
    }

    async handleSubmit(event) {
        event.preventDefault();
        
        if (this.isLoading) return;
        
        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData.entries());
        
        // Validation
        if (!this.validateForm(data)) return;
        
        this.setLoading(true);
        
        try {
            if (this.mode === 'login') {
                await this.handleLogin(data);
            } else {
                await this.handleRegister(data);
            }
        } catch (error) {
            console.error('Auth error:', error);
            NotificationManager.error(error.message || 'Authentication failed');
        } finally {
            this.setLoading(false);
        }
    }

    async handleLogin(data) {
        const result = await AuthManager.login(data.email, data.password);
        
        if (result.success) {
            NotificationManager.success('Login successful!');
            // AuthManager will emit 'login' event which App.js handles
        } else {
            throw new Error(result.error || 'Login failed');
        }
    }

    async handleRegister(data) {
        const result = await AuthManager.register({
            name: data.name,
            email: data.email,
            password: data.password
        });
        
        if (result.success) {
            NotificationManager.success('Account created successfully!');
            // Auto-login after registration
            await this.handleLogin(data);
        } else {
            throw new Error(result.error || 'Registration failed');
        }
    }

    validateForm(data) {
        if (this.mode === 'register') {
            if (!data.name?.trim()) {
                NotificationManager.error('Please enter your full name');
                return false;
            }
            
            if (data.password !== data.confirmPassword) {
                NotificationManager.error('Passwords do not match');
                return false;
            }
            
            if (data.password.length < 6) {
                NotificationManager.error('Password must be at least 6 characters');
                return false;
            }
        }
        
        if (!data.email?.trim() || !this.isValidEmail(data.email)) {
            NotificationManager.error('Please enter a valid email address');
            return false;
        }
        
        if (!data.password?.trim()) {
            NotificationManager.error('Please enter your password');
            return false;
        }
        
        return true;
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    setLoading(loading) {
        this.isLoading = loading;
        const submitButton = document.getElementById('auth-submit');
        const buttonText = submitButton?.querySelector('.button-text');
        const buttonSpinner = submitButton?.querySelector('.button-spinner');
        
        if (loading) {
            submitButton?.setAttribute('disabled', 'true');
            buttonText && (buttonText.style.display = 'none');
            buttonSpinner && (buttonSpinner.style.display = 'inline-flex');
        } else {
            submitButton?.removeAttribute('disabled');
            buttonText && (buttonText.style.display = 'inline');
            buttonSpinner && (buttonSpinner.style.display = 'none');
        }
    }

    switchMode(event, newMode) {
        event.preventDefault();
        this.mode = newMode;
        this.render(document.querySelector('.auth-container').parentElement);
    }

    handleForgotPassword(event) {
        event.preventDefault();
        NotificationManager.info('Password reset functionality coming soon!');
    }
}