/**
 * SuperInstance Mobile UI Backend Integration System
 * Connects the mobile UI to all 9 SuperInstance backend services
 * Provides unified API calls, authentication, and real-time updates
 */

class SuperInstanceMobileIntegration {
    constructor(options = {}) {
        this.services = {
            auth: 'http://localhost:8001',
            apiGateway: 'http://localhost:8088',
            userManagement: 'http://localhost:8092',
            activelogAI: 'http://localhost:8090',
            personallogAI: 'http://localhost:8095',
            fishinglogAI: 'http://localhost:8096',
            dmlogAI: 'http://localhost:8097',
            businesslogAI: 'http://localhost:8098',
            fitnessData: 'http://localhost:8099'
        };

        this.authToken = null;
        this.userId = null;
        this.currentDomain = 'activelog';
        this.isOnline = navigator.onLine;
        this.socketConnections = new Map();
        this.cache = new Map();
        this.pendingRequests = new Map();
        
        this.setupNetworkListeners();
        this.initializeCache();
    }

    /**
     * Initialize the mobile integration system
     */
    async initialize() {
        try {
            // Check service health
            const healthStatus = await this.checkServicesHealth();
            console.log('🏥 Services Health:', healthStatus);

            // Initialize authentication
            await this.initializeAuth();

            // Set up real-time connections
            await this.setupRealtimeConnections();

            // Initialize cross-domain AI correlations
            await this.initializeCrossDomainAI();

            console.log('🚀 SuperInstance Mobile Integration initialized successfully');
            return true;
        } catch (error) {
            console.error('❌ Mobile integration initialization failed:', error);
            return false;
        }
    }

    /**
     * Check health status of all SuperInstance services
     */
    async checkServicesHealth() {
        const healthChecks = Object.entries(this.services).map(async ([name, url]) => {
            try {
                const healthPath = name === 'auth' ? '/api/health' : '/health';
                const response = await this.makeRequest(`${url}${healthPath}`, {
                    method: 'GET',
                    timeout: 3000
                });
                return {
                    service: name,
                    status: response.ok ? 'healthy' : 'degraded',
                    responseTime: response.responseTime || 0
                };
            } catch (error) {
                return {
                    service: name,
                    status: 'unhealthy',
                    error: error.message
                };
            }
        });

        return await Promise.allSettled(healthChecks);
    }

    /**
     * Initialize authentication with all services
     */
    async initializeAuth() {
        try {
            // Check for existing token
            this.authToken = localStorage.getItem('superinstance_token');
            this.userId = localStorage.getItem('superinstance_user_id');

            if (this.authToken) {
                const isValid = await this.validateToken();
                if (isValid) {
                    await this.setServiceAuthentication();
                    return true;
                }
            }

            // If no valid token, return false to trigger login
            return false;
        } catch (error) {
            console.error('Auth initialization error:', error);
            return false;
        }
    }

    /**
     * Authenticate user with mobile credentials
     */
    async authenticate(credentials) {
        try {
            const response = await this.makeRequest(`${this.services.auth}/api/auth/login`, {
                method: 'POST',
                body: JSON.stringify(credentials),
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.authToken = data.token;
                this.userId = data.user_id;

                localStorage.setItem('superinstance_token', this.authToken);
                localStorage.setItem('superinstance_user_id', this.userId);

                await this.setServiceAuthentication();
                return { success: true, user: data.user };
            }

            return { success: false, error: 'Invalid credentials' };
        } catch (error) {
            console.error('Authentication error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Set authentication headers for all service requests
     */
    async setServiceAuthentication() {
        // Configure default headers for all services
        this.defaultHeaders = {
            'Authorization': `Bearer ${this.authToken}`,
            'Content-Type': 'application/json',
            'X-User-ID': this.userId,
            'X-Client-Type': 'mobile',
            'X-SuperInstance-Version': '1.0'
        };
    }

    /**
     * Validate authentication token
     */
    async validateToken() {
        try {
            const response = await this.makeRequest(`${this.services.auth}/api/auth/validate`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.authToken}`
                }
            });
            return response.ok;
        } catch (error) {
            console.error('Token validation error:', error);
            return false;
        }
    }

    /**
     * Set up real-time connections to all AI services
     */
    async setupRealtimeConnections() {
        const aiServices = ['activelogAI', 'personallogAI', 'fishinglogAI', 'dmlogAI', 'businesslogAI'];
        
        for (const service of aiServices) {
            try {
                const wsUrl = this.services[service].replace('http', 'ws') + '/ws';
                const socket = new WebSocket(wsUrl);
                
                socket.onopen = () => {
                    console.log(`🔌 Connected to ${service} websocket`);
                    this.socketConnections.set(service, socket);
                };
                
                socket.onmessage = (event) => {
                    this.handleRealtimeMessage(service, JSON.parse(event.data));
                };
                
                socket.onerror = (error) => {
                    console.error(`❌ WebSocket error for ${service}:`, error);
                };
                
                socket.onclose = () => {
                    console.log(`🔌 Disconnected from ${service} websocket`);
                    this.socketConnections.delete(service);
                    // Attempt reconnection after 3 seconds
                    setTimeout(() => this.setupRealtimeConnection(service), 3000);
                };
            } catch (error) {
                console.error(`Failed to connect to ${service} websocket:`, error);
            }
        }
    }

    /**
     * Initialize cross-domain AI correlation system
     */
    async initializeCrossDomainAI() {
        try {
            // Get user's cross-domain preferences
            const preferences = await this.getCrossDomainPreferences();
            
            // Set up AI correlation subscriptions
            if (preferences.enableCrossDomainInsights) {
                await this.subscribeToCrossDomainInsights();
            }
            
            console.log('🧠 Cross-domain AI system initialized');
        } catch (error) {
            console.error('Cross-domain AI initialization error:', error);
        }
    }

    // ====================================
    // MOBILE UI API METHODS
    // ====================================

    /**
     * Get unified dashboard data for mobile UI
     */
    async getMobileDashboardData() {
        try {
            const cacheKey = `mobile_dashboard_${this.userId}`;
            const cached = this.cache.get(cacheKey);
            
            if (cached && (Date.now() - cached.timestamp) < 300000) { // 5 minutes cache
                return cached.data;
            }

            // Parallel requests to all services for dashboard data
            const [
                activelogData,
                personallogData,
                fitnessData,
                userProfile,
                crossDomainInsights
            ] = await Promise.allSettled([
                this.getActiveLogData(),
                this.getPersonalLogData(),
                this.getFitnessData(),
                this.getUserProfile(),
                this.getCrossDomainInsights()
            ]);

            const dashboardData = {
                user: userProfile.value || {},
                activelog: activelogData.value || {},
                personallog: personallogData.value || {},
                fitness: fitnessData.value || {},
                insights: crossDomainInsights.value || {},
                lastUpdated: new Date().toISOString()
            };

            // Cache the result
            this.cache.set(cacheKey, {
                data: dashboardData,
                timestamp: Date.now()
            });

            return dashboardData;
        } catch (error) {
            console.error('Dashboard data error:', error);
            throw error;
        }
    }

    /**
     * Get ActiveLog fitness data for mobile UI
     */
    async getActiveLogData() {
        const [workouts, nutrition, goals] = await Promise.all([
            this.makeRequest(`${this.services.fitnessData}/workouts?limit=10`, { method: 'GET' }),
            this.makeRequest(`${this.services.fitnessData}/nutrition/recent?days=7`, { method: 'GET' }),
            this.makeRequest(`${this.services.fitnessData}/goals/active`, { method: 'GET' })
        ]);

        return {
            recentWorkouts: await workouts.json(),
            weeklyNutrition: await nutrition.json(),
            activeGoals: await goals.json()
        };
    }

    /**
     * Get PersonalLog productivity data
     */
    async getPersonalLogData() {
        const response = await this.makeRequest(`${this.services.personallogAI}/insights/productivity`, {
            method: 'GET'
        });
        return await response.json();
    }

    /**
     * Get fitness data from fitness API
     */
    async getFitnessData() {
        const response = await this.makeRequest(`${this.services.fitnessData}/dashboard`, {
            method: 'GET'
        });
        return await response.json();
    }

    /**
     * Get user profile data
     */
    async getUserProfile() {
        const response = await this.makeRequest(`${this.services.userManagement}/profile`, {
            method: 'GET'
        });
        return await response.json();
    }

    /**
     * Get cross-domain AI insights
     */
    async getCrossDomainInsights() {
        try {
            // Query multiple AI services for correlations
            const insights = await Promise.all([
                this.makeRequest(`${this.services.activelogAI}/insights/cross-domain`, { method: 'GET' }),
                this.makeRequest(`${this.services.personallogAI}/insights/correlations`, { method: 'GET' }),
                this.makeRequest(`${this.services.businesslogAI}/analytics/cross-domain`, { method: 'GET' })
            ]);

            return {
                fitness_productivity: await insights[0].json(),
                productivity_correlations: await insights[1].json(),
                business_insights: await insights[2].json()
            };
        } catch (error) {
            console.error('Cross-domain insights error:', error);
            return {};
        }
    }

    /**
     * Switch active domain context (ActiveLog, PersonalLog, etc.)
     */
    async switchDomain(domain) {
        this.currentDomain = domain;
        
        // Update UI context
        document.body.className = document.body.className.replace(/domain-\w+/g, '');
        document.body.classList.add(`domain-${domain}`);
        
        // Fetch domain-specific data
        const domainData = await this.getDomainData(domain);
        
        // Emit domain change event for UI components
        this.emitEvent('domainChanged', { domain, data: domainData });
        
        return domainData;
    }

    /**
     * Get domain-specific data based on current active domain
     */
    async getDomainData(domain) {
        const serviceMap = {
            'activelog': this.services.activelogAI,
            'personallog': this.services.personallogAI,
            'fishinglog': this.services.fishinglogAI,
            'dmlog': this.services.dmlogAI,
            'businesslog': this.services.businesslogAI
        };

        const serviceUrl = serviceMap[domain];
        if (!serviceUrl) {
            throw new Error(`Unknown domain: ${domain}`);
        }

        const response = await this.makeRequest(`${serviceUrl}/dashboard`, {
            method: 'GET'
        });
        
        return await response.json();
    }

    /**
     * Submit data across multiple domains
     */
    async submitCrossDomainData(data) {
        try {
            const submissions = [];
            
            // Route data to appropriate services
            if (data.fitness) {
                submissions.push(
                    this.makeRequest(`${this.services.fitnessData}/entries`, {
                        method: 'POST',
                        body: JSON.stringify(data.fitness)
                    })
                );
            }
            
            if (data.productivity) {
                submissions.push(
                    this.makeRequest(`${this.services.personallogAI}/entries`, {
                        method: 'POST',
                        body: JSON.stringify(data.productivity)
                    })
                );
            }
            
            // Wait for all submissions
            const results = await Promise.allSettled(submissions);
            
            // Trigger cross-domain correlation analysis
            await this.triggerCrossDomainAnalysis();
            
            return {
                success: true,
                results: results.map(r => r.status === 'fulfilled')
            };
        } catch (error) {
            console.error('Cross-domain submission error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Get AI insights for mobile optimization
     */
    async getMobileAIInsights(query) {
        try {
            // Route to appropriate AI service based on current domain
            const serviceUrl = this.services[`${this.currentDomain}AI`];
            
            const response = await this.makeRequest(`${serviceUrl}/mobile/insights`, {
                method: 'POST',
                body: JSON.stringify({ query, context: 'mobile' })
            });
            
            return await response.json();
        } catch (error) {
            console.error('Mobile AI insights error:', error);
            throw error;
        }
    }

    // ====================================
    // UTILITY METHODS
    // ====================================

    /**
     * Make authenticated HTTP request with mobile optimizations
     */
    async makeRequest(url, options = {}) {
        try {
            const startTime = Date.now();
            
            // Add default headers
            const headers = {
                ...this.defaultHeaders,
                ...options.headers
            };

            // Add request timeout for mobile
            const controller = new AbortController();
            const timeout = options.timeout || 10000;
            const timeoutId = setTimeout(() => controller.abort(), timeout);

            const requestOptions = {
                ...options,
                headers,
                signal: controller.signal
            };

            const response = await fetch(url, requestOptions);
            clearTimeout(timeoutId);
            
            // Add response time for monitoring
            response.responseTime = Date.now() - startTime;
            
            return response;
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }

    /**
     * Handle real-time messages from AI services
     */
    handleRealtimeMessage(service, message) {
        switch (message.type) {
            case 'insight':
                this.emitEvent('newInsight', { service, insight: message.data });
                break;
            case 'correlation':
                this.emitEvent('crossDomainCorrelation', { service, correlation: message.data });
                break;
            case 'notification':
                this.showMobileNotification(message.data);
                break;
            default:
                console.log('Unknown real-time message:', message);
        }
    }

    /**
     * Show mobile-optimized notification
     */
    showMobileNotification(notification) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(notification.title, {
                body: notification.message,
                icon: '/assets/icons/superinstance-icon.png',
                badge: '/assets/icons/badge.png',
                tag: notification.id
            });
        }
    }

    /**
     * Set up network status listeners
     */
    setupNetworkListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.emitEvent('networkStatusChanged', { online: true });
            this.syncPendingData();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.emitEvent('networkStatusChanged', { online: false });
        });
    }

    /**
     * Initialize local cache for offline support
     */
    initializeCache() {
        // Set up service worker for offline caching if available
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    console.log('Service Worker registered successfully');
                })
                .catch(error => {
                    console.log('Service Worker registration failed');
                });
        }
    }

    /**
     * Sync pending data when back online
     */
    async syncPendingData() {
        const pendingData = JSON.parse(localStorage.getItem('pending_sync_data') || '[]');
        
        for (const data of pendingData) {
            try {
                await this.submitCrossDomainData(data);
                // Remove from pending after successful sync
                const index = pendingData.indexOf(data);
                pendingData.splice(index, 1);
            } catch (error) {
                console.error('Sync failed for data:', data, error);
            }
        }
        
        localStorage.setItem('pending_sync_data', JSON.stringify(pendingData));
    }

    /**
     * Emit custom events for UI components
     */
    emitEvent(eventName, data) {
        const event = new CustomEvent(`superinstance:${eventName}`, {
            detail: data
        });
        document.dispatchEvent(event);
    }

    /**
     * Get cross-domain user preferences
     */
    async getCrossDomainPreferences() {
        try {
            const response = await this.makeRequest(`${this.services.userManagement}/preferences/cross-domain`, {
                method: 'GET'
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to get cross-domain preferences:', error);
            return { enableCrossDomainInsights: true }; // Default
        }
    }

    /**
     * Subscribe to cross-domain AI insights
     */
    async subscribeToCrossDomainInsights() {
        // Set up subscriptions with all AI services for cross-domain insights
        const aiServices = ['activelogAI', 'personallogAI', 'businesslogAI'];
        
        for (const service of aiServices) {
            try {
                await this.makeRequest(`${this.services[service]}/subscribe/cross-domain`, {
                    method: 'POST',
                    body: JSON.stringify({ userId: this.userId, platform: 'mobile' })
                });
            } catch (error) {
                console.error(`Failed to subscribe to ${service} cross-domain insights:`, error);
            }
        }
    }

    /**
     * Trigger cross-domain correlation analysis
     */
    async triggerCrossDomainAnalysis() {
        try {
            await this.makeRequest(`${this.services.apiGateway}/analyze/cross-domain`, {
                method: 'POST',
                body: JSON.stringify({ userId: this.userId, trigger: 'data_submission' })
            });
        } catch (error) {
            console.error('Failed to trigger cross-domain analysis:', error);
        }
    }

    // ====================================
    // PUBLIC API
    // ====================================

    /**
     * Get current integration status
     */
    getStatus() {
        return {
            authenticated: !!this.authToken,
            currentDomain: this.currentDomain,
            online: this.isOnline,
            servicesConnected: this.socketConnections.size,
            cacheSize: this.cache.size
        };
    }

    /**
     * Logout and cleanup
     */
    async logout() {
        // Close all WebSocket connections
        for (const [service, socket] of this.socketConnections) {
            socket.close();
        }
        this.socketConnections.clear();

        // Clear authentication
        this.authToken = null;
        this.userId = null;
        localStorage.removeItem('superinstance_token');
        localStorage.removeItem('superinstance_user_id');

        // Clear cache
        this.cache.clear();

        // Emit logout event
        this.emitEvent('userLoggedOut', {});
    }
}

// Export for use in mobile applications
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SuperInstanceMobileIntegration;
} else {
    window.SuperInstanceMobileIntegration = SuperInstanceMobileIntegration;
}