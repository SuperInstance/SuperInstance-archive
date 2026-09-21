/**
 * Enhanced Authentication View with Modern UI
 */

import { ModernButton, ModernCard, ModernToast, ModernProgress } from '../ui/ModernComponents.js';
import { AuthManager } from '../../utils/auth.js';
import { ServiceStatusManager } from '../../utils/serviceStatus.js';

export class EnhancedAuthView {
    constructor(mode = 'login') {
        this.mode = mode;
        this.isLoading = false;
        this.rememberMe = false;
        this.showPassword = false;
        this.element = null;
    }

    async render(container) {
        container.innerHTML = this.getHTML();
        this.element = container;
        this.attachEventListeners();
        this.initializeAnimations();
        
        // Check if we're in demo mode
        if (ServiceStatusManager.isMockMode()) {
            this.showDemoModeNotice();
        }
    }

    getHTML() {
        return `
            <div class="enhanced-auth">
                <div class="enhanced-auth__background">
                    <div class="enhanced-auth__shapes">
                        <div class="shape shape--1"></div>
                        <div class="shape shape--2"></div>
                        <div class="shape shape--3"></div>
                    </div>
                </div>
                
                <div class="enhanced-auth__container">
                    <div class="enhanced-auth__card">
                        <div class="enhanced-auth__header">
                            <div class="enhanced-auth__logo">
                                <span class="logo-icon">📊</span>
                                <h1 class="logo-text">ActiveLog.ai</h1>
                            </div>
                            <p class="enhanced-auth__subtitle">
                                ${this.mode === 'login' ? 'Welcome back! Sign in to continue.' : 'Create your account to get started.'}
                            </p>
                        </div>

                        <div class="enhanced-auth__form-container">
                            <div class="enhanced-auth__tabs">
                                <button class="auth-tab ${this.mode === 'login' ? 'auth-tab--active' : ''}" 
                                        data-mode="login">Sign In</button>
                                <button class="auth-tab ${this.mode === 'register' ? 'auth-tab--active' : ''}" 
                                        data-mode="register">Sign Up</button>
                            </div>

                            <form class="enhanced-auth__form" id="auth-form">
                                ${this.mode === 'register' ? this.getRegisterFields() : this.getLoginFields()}
                                
                                <div class="form-actions">
                                    <div class="form-options">
                                        ${this.mode === 'login' ? `
                                            <label class="checkbox-label">
                                                <input type="checkbox" id="remember-me" ${this.rememberMe ? 'checked' : ''}>
                                                <span class="checkmark"></span>
                                                Remember me
                                            </label>
                                        ` : ''}
                                    </div>
                                    
                                    <button type="submit" class="auth-submit-btn" id="auth-submit" ${this.isLoading ? 'disabled' : ''}>
                                        <span class="btn-content">
                                            ${this.isLoading ? '<div class="spinner"></div>' : ''}
                                            <span class="btn-text">
                                                ${this.mode === 'login' ? 'Sign In' : 'Create Account'}
                                            </span>
                                        </span>
                                    </button>
                                </div>
                                
                                ${this.mode === 'login' ? `
                                    <div class="auth-links">
                                        <a href="#" class="forgot-password">Forgot password?</a>
                                    </div>
                                ` : ''}
                            </form>
                        </div>

                        <div class="enhanced-auth__footer">
                            <div class="demo-credentials" id="demo-credentials">
                                <h4>🧪 Demo Credentials</h4>
                                <p><strong>Username:</strong> admin</p>
                                <p><strong>Password:</strong> admin123</p>
                                <button class="demo-fill-btn" id="demo-fill">Use Demo Credentials</button>
                            </div>
                            
                            <div class="service-status-mini" id="service-status-mini">
                                <div class="status-indicator">
                                    <span class="status-dot" id="status-dot"></span>
                                    <span class="status-text" id="status-text">Checking services...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="progress-overlay" id="progress-overlay" style="display: none;">
                    <div class="progress-content">
                        <div class="progress-icon">🔐</div>
                        <h3 id="progress-title">Authenticating...</h3>
                        <div class="progress-bar-container">
                            <div class="progress-bar" id="progress-bar"></div>
                        </div>
                        <p id="progress-message">Verifying credentials...</p>
                    </div>
                </div>
            </div>
            ${this.getStyles()}
        `;
    }

    getLoginFields() {
        return `
            <div class="form-group">
                <label for="username" class="form-label">Username or Email</label>
                <div class="input-container">
                    <input type="text" id="username" class="form-input" 
                           placeholder="Enter your username or email" 
                           autocomplete="username" required>
                    <span class="input-icon">👤</span>
                </div>
            </div>

            <div class="form-group">
                <label for="password" class="form-label">Password</label>
                <div class="input-container">
                    <input type="${this.showPassword ? 'text' : 'password'}" id="password" 
                           class="form-input" placeholder="Enter your password" 
                           autocomplete="current-password" required>
                    <button type="button" class="password-toggle" id="password-toggle">
                        ${this.showPassword ? '🙈' : '👁️'}
                    </button>
                </div>
            </div>
        `;
    }

    getRegisterFields() {
        return `
            <div class="form-group">
                <label for="username" class="form-label">Username</label>
                <div class="input-container">
                    <input type="text" id="username" class="form-input" 
                           placeholder="Choose a username" 
                           autocomplete="username" required>
                    <span class="input-icon">👤</span>
                </div>
            </div>

            <div class="form-group">
                <label for="email" class="form-label">Email</label>
                <div class="input-container">
                    <input type="email" id="email" class="form-input" 
                           placeholder="Enter your email address" 
                           autocomplete="email" required>
                    <span class="input-icon">📧</span>
                </div>
            </div>

            <div class="form-group">
                <label for="password" class="form-label">Password</label>
                <div class="input-container">
                    <input type="${this.showPassword ? 'text' : 'password'}" id="password" 
                           class="form-input" placeholder="Create a strong password" 
                           autocomplete="new-password" required>
                    <button type="button" class="password-toggle" id="password-toggle">
                        ${this.showPassword ? '🙈' : '👁️'}
                    </button>
                </div>
                <div class="password-strength" id="password-strength">
                    <div class="strength-bar">
                        <div class="strength-fill" id="strength-fill"></div>
                    </div>
                    <span class="strength-text" id="strength-text">Password strength</span>
                </div>
            </div>

            <div class="form-group">
                <label for="confirm-password" class="form-label">Confirm Password</label>
                <div class="input-container">
                    <input type="${this.showPassword ? 'text' : 'password'}" id="confirm-password" 
                           class="form-input" placeholder="Confirm your password" 
                           autocomplete="new-password" required>
                    <span class="input-icon">🔒</span>
                </div>
            </div>
        `;
    }

    attachEventListeners() {
        // Tab switching
        const tabs = this.element.querySelectorAll('.auth-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const mode = e.target.dataset.mode;
                if (mode !== this.mode) {
                    this.switchMode(mode);
                }
            });
        });

        // Form submission
        const form = this.element.querySelector('#auth-form');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });

        // Password toggle
        const passwordToggle = this.element.querySelector('#password-toggle');
        if (passwordToggle) {
            passwordToggle.addEventListener('click', () => {
                this.togglePasswordVisibility();
            });
        }

        // Remember me
        const rememberMe = this.element.querySelector('#remember-me');
        if (rememberMe) {
            rememberMe.addEventListener('change', (e) => {
                this.rememberMe = e.target.checked;
            });
        }

        // Demo credentials
        const demoFill = this.element.querySelector('#demo-fill');
        if (demoFill) {
            demoFill.addEventListener('click', () => {
                this.fillDemoCredentials();
            });
        }

        // Password strength (for register mode)
        if (this.mode === 'register') {
            const passwordInput = this.element.querySelector('#password');
            passwordInput.addEventListener('input', () => {
                this.updatePasswordStrength();
            });
        }

        // Service status updates
        ServiceStatusManager.on('statusUpdate', (status) => {
            this.updateServiceStatus(status);
        });

        // Input animations
        const inputs = this.element.querySelectorAll('.form-input');
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                input.parentNode.parentNode.classList.add('form-group--focused');
            });
            
            input.addEventListener('blur', () => {
                input.parentNode.parentNode.classList.remove('form-group--focused');
                if (input.value) {
                    input.parentNode.parentNode.classList.add('form-group--filled');
                } else {
                    input.parentNode.parentNode.classList.remove('form-group--filled');
                }
            });

            // Check initial state
            if (input.value) {
                input.parentNode.parentNode.classList.add('form-group--filled');
            }
        });
    }

    initializeAnimations() {
        // Animate card entrance
        const card = this.element.querySelector('.enhanced-auth__card');
        setTimeout(() => {
            card.classList.add('enhanced-auth__card--visible');
        }, 100);

        // Animate shapes
        const shapes = this.element.querySelectorAll('.shape');
        shapes.forEach((shape, index) => {
            setTimeout(() => {
                shape.classList.add('shape--animated');
            }, 200 * (index + 1));
        });

        // Update service status
        this.updateServiceStatus(ServiceStatusManager.getStatus());
    }

    switchMode(newMode) {
        this.mode = newMode;
        
        // Update tabs
        const tabs = this.element.querySelectorAll('.auth-tab');
        tabs.forEach(tab => {
            if (tab.dataset.mode === newMode) {
                tab.classList.add('auth-tab--active');
            } else {
                tab.classList.remove('auth-tab--active');
            }
        });

        // Update form
        const form = this.element.querySelector('#auth-form');
        form.innerHTML = `
            ${newMode === 'register' ? this.getRegisterFields() : this.getLoginFields()}
            <div class="form-actions">
                <div class="form-options">
                    ${newMode === 'login' ? `
                        <label class="checkbox-label">
                            <input type="checkbox" id="remember-me" ${this.rememberMe ? 'checked' : ''}>
                            <span class="checkmark"></span>
                            Remember me
                        </label>
                    ` : ''}
                </div>
                
                <button type="submit" class="auth-submit-btn" id="auth-submit">
                    <span class="btn-content">
                        <span class="btn-text">
                            ${newMode === 'login' ? 'Sign In' : 'Create Account'}
                        </span>
                    </span>
                </button>
            </div>
            
            ${newMode === 'login' ? `
                <div class="auth-links">
                    <a href="#" class="forgot-password">Forgot password?</a>
                </div>
            ` : ''}
        `;

        // Re-attach event listeners for new form
        this.attachEventListeners();
        
        // Update subtitle
        const subtitle = this.element.querySelector('.enhanced-auth__subtitle');
        subtitle.textContent = newMode === 'login' 
            ? 'Welcome back! Sign in to continue.' 
            : 'Create your account to get started.';
    }

    togglePasswordVisibility() {
        this.showPassword = !this.showPassword;
        const passwordInputs = this.element.querySelectorAll('input[type="password"], input[type="text"]');
        const toggleBtn = this.element.querySelector('#password-toggle');
        
        passwordInputs.forEach(input => {
            if (input.id.includes('password')) {
                input.type = this.showPassword ? 'text' : 'password';
            }
        });
        
        toggleBtn.textContent = this.showPassword ? '🙈' : '👁️';
    }

    fillDemoCredentials() {
        const usernameInput = this.element.querySelector('#username');
        const passwordInput = this.element.querySelector('#password');
        
        usernameInput.value = 'admin';
        passwordInput.value = 'admin123';
        
        // Trigger focus/blur to update styling
        usernameInput.dispatchEvent(new Event('blur'));
        passwordInput.dispatchEvent(new Event('blur'));
        
        ModernToast.info('Demo credentials filled!', { duration: 2000 });
    }

    updatePasswordStrength() {
        const passwordInput = this.element.querySelector('#password');
        const strengthFill = this.element.querySelector('#strength-fill');
        const strengthText = this.element.querySelector('#strength-text');
        
        if (!passwordInput || !strengthFill || !strengthText) return;
        
        const password = passwordInput.value;
        const strength = this.calculatePasswordStrength(password);
        
        strengthFill.style.width = `${strength.score * 25}%`;
        strengthFill.className = `strength-fill strength-fill--${strength.level}`;
        strengthText.textContent = strength.text;
    }

    calculatePasswordStrength(password) {
        let score = 0;
        let level = 'weak';
        let text = 'Weak';

        if (password.length >= 8) score++;
        if (/[a-z]/.test(password)) score++;
        if (/[A-Z]/.test(password)) score++;
        if (/\d/.test(password)) score++;
        if (/[^a-zA-Z\d]/.test(password)) score++;

        if (score >= 4) {
            level = 'strong';
            text = 'Strong';
        } else if (score >= 3) {
            level = 'medium';
            text = 'Medium';
        } else if (score >= 1) {
            level = 'weak';
            text = 'Weak';
        }

        return { score, level, text };
    }

    updateServiceStatus(status) {
        const statusDot = this.element.querySelector('#status-dot');
        const statusText = this.element.querySelector('#status-text');
        
        if (!statusDot || !statusText) return;
        
        let dotClass = 'status-dot--checking';
        let text = 'Checking services...';
        
        if (status.mockMode) {
            dotClass = 'status-dot--demo';
            text = 'Demo Mode Active';
        } else if (status.overall === 'healthy') {
            dotClass = 'status-dot--online';
            text = 'All Services Online';
        } else if (status.overall === 'degraded') {
            dotClass = 'status-dot--degraded';
            text = 'Some Services Offline';
        }
        
        statusDot.className = `status-dot ${dotClass}`;
        statusText.textContent = text;
    }

    showDemoModeNotice() {
        ModernToast.info('Running in Demo Mode', {
            title: '🧪 Demo Mode',
            message: 'Some features may be limited. Services will use mock data.',
            duration: 5000
        });
    }

    async handleSubmit() {
        if (this.isLoading) return;
        
        this.setLoading(true);
        
        try {
            const formData = this.getFormData();
            
            if (this.mode === 'register') {
                await this.handleRegister(formData);
            } else {
                await this.handleLogin(formData);
            }
        } catch (error) {
            ModernToast.error(error.message, {
                title: 'Authentication Error',
                duration: 5000
            });
        } finally {
            this.setLoading(false);
        }
    }

    getFormData() {
        const form = this.element.querySelector('#auth-form');
        const formData = new FormData(form);
        const data = {};
        
        // Get form values
        const username = this.element.querySelector('#username').value;
        const password = this.element.querySelector('#password').value;
        
        data.username = username;
        data.password = password;
        
        if (this.mode === 'register') {
            const email = this.element.querySelector('#email').value;
            const confirmPassword = this.element.querySelector('#confirm-password').value;
            
            data.email = email;
            
            if (password !== confirmPassword) {
                throw new Error('Passwords do not match');
            }
            
            if (password.length < 8) {
                throw new Error('Password must be at least 8 characters long');
            }
        }
        
        return data;
    }

    async handleLogin(formData) {
        this.updateProgress(25, 'Verifying credentials...');
        
        const result = await AuthManager.login(formData.username, formData.password);
        
        if (result.success) {
            this.updateProgress(75, 'Loading user profile...');
            
            setTimeout(() => {
                this.updateProgress(100, 'Authentication successful!');
                ModernToast.success('Welcome back!', {
                    title: 'Login Successful',
                    duration: 3000
                });
            }, 500);
        } else {
            throw new Error(result.error || 'Login failed');
        }
    }

    async handleRegister(formData) {
        this.updateProgress(25, 'Creating account...');
        
        const result = await AuthManager.register(formData);
        
        if (result.success) {
            this.updateProgress(75, 'Account created successfully...');
            
            setTimeout(() => {
                this.updateProgress(100, 'Registration complete!');
                ModernToast.success('Account created successfully!', {
                    title: 'Registration Successful',
                    message: 'You can now sign in with your credentials.',
                    duration: 5000
                });
                
                // Switch to login mode
                setTimeout(() => {
                    this.switchMode('login');
                }, 2000);
            }, 500);
        } else {
            throw new Error(result.error || 'Registration failed');
        }
    }

    setLoading(loading) {
        this.isLoading = loading;
        const submitBtn = this.element.querySelector('#auth-submit');
        const progressOverlay = this.element.querySelector('#progress-overlay');
        
        if (loading) {
            submitBtn.disabled = true;
            submitBtn.querySelector('.btn-content').innerHTML = `
                <div class="spinner"></div>
                <span class="btn-text">Processing...</span>
            `;
            progressOverlay.style.display = 'flex';
            this.updateProgress(0, 'Starting...');
        } else {
            submitBtn.disabled = false;
            submitBtn.querySelector('.btn-content').innerHTML = `
                <span class="btn-text">
                    ${this.mode === 'login' ? 'Sign In' : 'Create Account'}
                </span>
            `;
            
            setTimeout(() => {
                progressOverlay.style.display = 'none';
            }, 1000);
        }
    }

    updateProgress(percentage, message) {
        const progressBar = this.element.querySelector('#progress-bar');
        const progressMessage = this.element.querySelector('#progress-message');
        
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }
        
        if (progressMessage) {
            progressMessage.textContent = message;
        }
    }

    getStyles() {
        return `
            <style>
                .enhanced-auth {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                }

                .enhanced-auth__background {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    overflow: hidden;
                }

                .enhanced-auth__shapes {
                    position: relative;
                    width: 100%;
                    height: 100%;
                }

                .shape {
                    position: absolute;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    opacity: 0;
                    transition: all 1s ease-out;
                }

                .shape--1 {
                    width: 300px;
                    height: 300px;
                    top: -150px;
                    right: -150px;
                    animation: float 6s ease-in-out infinite;
                }

                .shape--2 {
                    width: 200px;
                    height: 200px;
                    bottom: -100px;
                    left: -100px;
                    animation: float 8s ease-in-out infinite reverse;
                }

                .shape--3 {
                    width: 150px;
                    height: 150px;
                    top: 50%;
                    left: -75px;
                    animation: float 7s ease-in-out infinite;
                }

                .shape--animated {
                    opacity: 1;
                }

                @keyframes float {
                    0%, 100% { transform: translateY(0) rotate(0deg); }
                    50% { transform: translateY(-20px) rotate(180deg); }
                }

                .enhanced-auth__container {
                    position: relative;
                    z-index: 1;
                    width: 100%;
                    max-width: 400px;
                    padding: 20px;
                }

                .enhanced-auth__card {
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 20px;
                    backdrop-filter: blur(20px);
                    box-shadow: 0 25px 45px rgba(0, 0, 0, 0.2);
                    overflow: hidden;
                    transform: translateY(20px);
                    opacity: 0;
                    transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
                }

                .enhanced-auth__card--visible {
                    transform: translateY(0);
                    opacity: 1;
                }

                .enhanced-auth__header {
                    padding: 40px 30px 20px;
                    text-align: center;
                }

                .enhanced-auth__logo {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 12px;
                    margin-bottom: 16px;
                }

                .logo-icon {
                    font-size: 2.5rem;
                    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
                }

                .logo-text {
                    font-size: 2rem;
                    font-weight: 700;
                    color: #1a202c;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }

                .enhanced-auth__subtitle {
                    color: #718096;
                    margin: 0;
                    font-size: 16px;
                }

                .enhanced-auth__form-container {
                    padding: 0 30px;
                }

                .enhanced-auth__tabs {
                    display: flex;
                    background: #f7fafc;
                    border-radius: 12px;
                    padding: 4px;
                    margin-bottom: 30px;
                }

                .auth-tab {
                    flex: 1;
                    background: none;
                    border: none;
                    padding: 12px 20px;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    color: #718096;
                }

                .auth-tab--active {
                    background: white;
                    color: #2d3748;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }

                .form-group {
                    margin-bottom: 24px;
                    position: relative;
                    transition: all 0.3s ease;
                }

                .form-group--focused {
                    transform: scale(1.02);
                }

                .form-label {
                    display: block;
                    margin-bottom: 8px;
                    font-weight: 600;
                    color: #4a5568;
                    font-size: 14px;
                }

                .input-container {
                    position: relative;
                }

                .form-input {
                    width: 100%;
                    padding: 16px 50px 16px 20px;
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    font-size: 16px;
                    transition: all 0.3s ease;
                    background: #fafafa;
                    box-sizing: border-box;
                }

                .form-input:focus {
                    outline: none;
                    border-color: #667eea;
                    background: white;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }

                .input-icon {
                    position: absolute;
                    right: 16px;
                    top: 50%;
                    transform: translateY(-50%);
                    font-size: 18px;
                    color: #a0aec0;
                    pointer-events: none;
                }

                .password-toggle {
                    position: absolute;
                    right: 16px;
                    top: 50%;
                    transform: translateY(-50%);
                    background: none;
                    border: none;
                    cursor: pointer;
                    font-size: 18px;
                    padding: 4px;
                    border-radius: 4px;
                    transition: all 0.2s ease;
                }

                .password-toggle:hover {
                    background: rgba(0,0,0,0.05);
                }

                .password-strength {
                    margin-top: 8px;
                }

                .strength-bar {
                    height: 4px;
                    background: #e2e8f0;
                    border-radius: 2px;
                    overflow: hidden;
                    margin-bottom: 4px;
                }

                .strength-fill {
                    height: 100%;
                    transition: all 0.3s ease;
                    border-radius: inherit;
                }

                .strength-fill--weak { background: #f56565; }
                .strength-fill--medium { background: #ed8936; }
                .strength-fill--strong { background: #48bb78; }

                .strength-text {
                    font-size: 12px;
                    color: #718096;
                }

                .form-actions {
                    margin: 30px 0;
                }

                .form-options {
                    margin-bottom: 20px;
                }

                .checkbox-label {
                    display: flex;
                    align-items: center;
                    cursor: pointer;
                    font-size: 14px;
                    color: #4a5568;
                }

                .checkbox-label input {
                    display: none;
                }

                .checkmark {
                    width: 20px;
                    height: 20px;
                    border: 2px solid #e2e8f0;
                    border-radius: 4px;
                    margin-right: 10px;
                    position: relative;
                    transition: all 0.2s ease;
                }

                .checkbox-label input:checked + .checkmark {
                    background: #667eea;
                    border-color: #667eea;
                }

                .checkbox-label input:checked + .checkmark:after {
                    content: '✓';
                    position: absolute;
                    color: white;
                    font-size: 14px;
                    top: -2px;
                    left: 3px;
                }

                .auth-submit-btn {
                    width: 100%;
                    padding: 16px 24px;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                }

                .auth-submit-btn:hover:not(:disabled) {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
                }

                .auth-submit-btn:active {
                    transform: translateY(0);
                }

                .auth-submit-btn:disabled {
                    opacity: 0.7;
                    cursor: not-allowed;
                    transform: none !important;
                }

                .btn-content {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                }

                .spinner {
                    width: 18px;
                    height: 18px;
                    border: 2px solid rgba(255,255,255,0.3);
                    border-top-color: white;
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                }

                @keyframes spin {
                    to { transform: rotate(360deg); }
                }

                .auth-links {
                    text-align: center;
                    margin-top: 20px;
                }

                .forgot-password {
                    color: #667eea;
                    text-decoration: none;
                    font-size: 14px;
                    font-weight: 500;
                }

                .forgot-password:hover {
                    text-decoration: underline;
                }

                .enhanced-auth__footer {
                    padding: 20px 30px 30px;
                }

                .demo-credentials {
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 20px;
                    text-align: center;
                }

                .demo-credentials h4 {
                    margin: 0 0 12px 0;
                    color: #856404;
                    font-size: 16px;
                }

                .demo-credentials p {
                    margin: 4px 0;
                    color: #856404;
                    font-size: 14px;
                }

                .demo-fill-btn {
                    background: #ffc107;
                    color: #212529;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                    margin-top: 10px;
                    transition: all 0.2s ease;
                }

                .demo-fill-btn:hover {
                    background: #e0a800;
                    transform: translateY(-1px);
                }

                .service-status-mini {
                    text-align: center;
                }

                .status-indicator {
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 14px;
                    color: #718096;
                }

                .status-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    display: inline-block;
                }

                .status-dot--online {
                    background: #48bb78;
                    animation: pulse 2s ease-in-out infinite;
                }

                .status-dot--degraded {
                    background: #ed8936;
                }

                .status-dot--demo {
                    background: #667eea;
                }

                .status-dot--checking {
                    background: #a0aec0;
                    animation: pulse 1.5s ease-in-out infinite;
                }

                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }

                .progress-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.8);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 10000;
                    backdrop-filter: blur(5px);
                }

                .progress-content {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    text-align: center;
                    max-width: 400px;
                    width: 90%;
                }

                .progress-icon {
                    font-size: 3rem;
                    margin-bottom: 20px;
                    animation: bounce 1s ease-in-out infinite;
                }

                @keyframes bounce {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-10px); }
                }

                .progress-content h3 {
                    margin: 0 0 20px 0;
                    color: #2d3748;
                }

                .progress-bar-container {
                    width: 100%;
                    height: 8px;
                    background: #e2e8f0;
                    border-radius: 4px;
                    overflow: hidden;
                    margin-bottom: 16px;
                }

                .progress-bar {
                    height: 100%;
                    background: linear-gradient(90deg, #667eea, #764ba2);
                    border-radius: inherit;
                    transition: width 0.5s ease;
                    width: 0%;
                }

                .progress-content p {
                    margin: 0;
                    color: #718096;
                    font-size: 14px;
                }

                /* Mobile Responsiveness */
                @media (max-width: 480px) {
                    .enhanced-auth__container {
                        padding: 10px;
                    }

                    .enhanced-auth__card {
                        border-radius: 16px;
                    }

                    .enhanced-auth__header,
                    .enhanced-auth__form-container,
                    .enhanced-auth__footer {
                        padding-left: 20px;
                        padding-right: 20px;
                    }

                    .logo-text {
                        font-size: 1.75rem;
                    }

                    .form-input {
                        font-size: 16px; /* Prevent zoom on iOS */
                    }

                    .progress-content {
                        padding: 30px 20px;
                    }
                }

                /* Dark mode support */
                @media (prefers-color-scheme: dark) {
                    .enhanced-auth__card {
                        background: rgba(26, 32, 44, 0.95);
                    }

                    .logo-text {
                        color: white;
                    }

                    .enhanced-auth__subtitle {
                        color: #a0aec0;
                    }

                    .form-input {
                        background: #2d3748;
                        border-color: #4a5568;
                        color: white;
                    }

                    .form-label {
                        color: #e2e8f0;
                    }

                    .auth-tab {
                        color: #a0aec0;
                    }

                    .auth-tab--active {
                        background: #4a5568;
                        color: white;
                    }

                    .progress-content {
                        background: #2d3748;
                        color: white;
                    }
                }
            </style>
        `;
    }
}