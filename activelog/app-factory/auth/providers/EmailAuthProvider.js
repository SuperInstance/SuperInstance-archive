export class EmailAuthProvider {
    constructor(config) {
        this.config = config;
        this.name = 'email';
    }

    async signIn(credentials) {
        const { email, password } = credentials;
        
        if (!email || !password) {
            throw new Error('Email and password are required');
        }

        try {
            const response = await fetch('/api/auth/signin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Sign in failed');
            }

            const result = await response.json();
            
            return {
                user: result.user,
                token: result.token,
                provider: this.name,
                emailVerified: result.user.emailVerified,
                twoFactorVerified: result.twoFactorVerified || false
            };

        } catch (error) {
            console.error('Email sign in error:', error);
            throw error;
        }
    }

    async signUp(credentials) {
        const { email, password, name } = credentials;
        
        if (!email || !password) {
            throw new Error('Email and password are required');
        }

        try {
            const response = await fetch('/api/auth/signup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    email, 
                    password, 
                    name: name || email.split('@')[0]
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Sign up failed');
            }

            const result = await response.json();
            
            return {
                user: result.user,
                token: result.token,
                provider: this.name,
                emailVerified: result.user.emailVerified || false
            };

        } catch (error) {
            console.error('Email sign up error:', error);
            throw error;
        }
    }

    async signOut() {
        try {
            await fetch('/api/auth/signout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        } catch (error) {
            console.warn('Sign out request failed:', error);
        }
    }

    async resetPassword(email) {
        try {
            const response = await fetch('/api/auth/reset-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Password reset failed');
            }

            return { success: true };

        } catch (error) {
            console.error('Password reset error:', error);
            throw error;
        }
    }

    async changePassword(currentPassword, newPassword) {
        try {
            const response = await fetch('/api/auth/change-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ currentPassword, newPassword })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Password change failed');
            }

            return { success: true };

        } catch (error) {
            console.error('Password change error:', error);
            throw error;
        }
    }

    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    validatePassword(password) {
        return password && password.length >= 8;
    }
}