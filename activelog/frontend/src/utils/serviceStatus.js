/**
 * Service Status Manager
 * Monitors backend service availability and provides fallback modes
 */

import { EventEmitter } from './events.js';

class ServiceStatusManagerClass extends EventEmitter {
    constructor() {
        super();
        this.services = {
            'auth': { status: 'unknown', url: '/api/auth', required: true },
            'file-sync': { status: 'unknown', url: '/api/file-sync', required: false },
            'ai-orchestrator': { status: 'unknown', url: '/api/ai-orchestrator', required: false },
            'metadata': { status: 'unknown', url: '/api/metadata', required: false }
        };
        this.overallStatus = 'unknown';
        this.checkInterval = null;
        this.mockMode = false;
    }

    async init() {
        await this.checkAllServices();
        this.startPeriodicChecks();
        
        // Check if we should enable mock mode
        const criticalServices = this.getCriticalServicesStatus();
        if (criticalServices.offline > 0) {
            console.warn('Critical services offline, enabling mock mode');
            this.enableMockMode();
        }
    }

    async checkAllServices() {
        const checkPromises = Object.entries(this.services).map(async ([name, service]) => {
            try {
                const response = await fetch(`${service.url}/health`, {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' },
                    timeout: 5000
                });
                
                if (response.ok) {
                    this.updateServiceStatus(name, 'online');
                } else {
                    this.updateServiceStatus(name, 'error');
                }
            } catch (error) {
                this.updateServiceStatus(name, 'offline');
            }
        });

        await Promise.allSettled(checkPromises);
        this.updateOverallStatus();
        this.emit('statusUpdate', this.getStatus());
    }

    updateServiceStatus(serviceName, status) {
        const previousStatus = this.services[serviceName].status;
        this.services[serviceName].status = status;
        this.services[serviceName].lastChecked = new Date().toISOString();

        if (previousStatus !== status) {
            this.emit('serviceStatusChanged', { service: serviceName, status, previousStatus });
        }
    }

    updateOverallStatus() {
        const statuses = Object.values(this.services).map(s => s.status);
        
        if (statuses.includes('offline') || statuses.includes('error')) {
            this.overallStatus = 'degraded';
        } else if (statuses.includes('unknown')) {
            this.overallStatus = 'unknown';
        } else {
            this.overallStatus = 'healthy';
        }
    }

    getCriticalServicesStatus() {
        const criticalServices = Object.entries(this.services)
            .filter(([name, service]) => service.required);
        
        return {
            total: criticalServices.length,
            online: criticalServices.filter(([name, service]) => service.status === 'online').length,
            offline: criticalServices.filter(([name, service]) => 
                service.status === 'offline' || service.status === 'error').length
        };
    }

    enableMockMode() {
        this.mockMode = true;
        this.emit('mockModeEnabled');
        console.log('Mock mode enabled - using fallback data');
    }

    disableMockMode() {
        this.mockMode = false;
        this.emit('mockModeDisabled');
        console.log('Mock mode disabled - using live services');
    }

    isMockMode() {
        return this.mockMode;
    }

    isServiceAvailable(serviceName) {
        return this.services[serviceName]?.status === 'online';
    }

    getStatus() {
        return {
            overall: this.overallStatus,
            services: { ...this.services },
            mockMode: this.mockMode,
            critical: this.getCriticalServicesStatus(),
            lastChecked: new Date().toISOString()
        };
    }

    startPeriodicChecks() {
        // Check every 30 seconds
        this.checkInterval = setInterval(() => {
            this.checkAllServices();
        }, 30000);
    }

    stopPeriodicChecks() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }

    // Mock data generators for offline mode
    getMockUserData() {
        return {
            id: 'mock-user-1',
            username: 'demo@activelog.ai',
            email: 'demo@activelog.ai',
            role: 'user',
            is_active: true,
            created_at: new Date().toISOString()
        };
    }

    getMockAuthResponse() {
        return {
            access_token: 'mock-jwt-token-demo-mode',
            refresh_token: 'mock-refresh-token',
            user: this.getMockUserData(),
            expires_in: 3600
        };
    }

    getMockFiles() {
        return [
            {
                id: 'mock-file-1',
                name: 'demo-document.pdf',
                path: '/documents/demo-document.pdf',
                size: 245760,
                type: 'application/pdf',
                created_at: new Date(Date.now() - 86400000).toISOString(),
                modified_at: new Date(Date.now() - 3600000).toISOString()
            },
            {
                id: 'mock-file-2',
                name: 'sample-image.jpg',
                path: '/images/sample-image.jpg',
                size: 524288,
                type: 'image/jpeg',
                created_at: new Date(Date.now() - 172800000).toISOString(),
                modified_at: new Date(Date.now() - 172800000).toISOString()
            }
        ];
    }

    async getMockResponse(endpoint, method = 'GET', data = null) {
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 100 + Math.random() * 400));

        // Return mock data based on endpoint
        if (endpoint.includes('/auth/login')) {
            return this.getMockAuthResponse();
        }
        
        if (endpoint.includes('/auth/me')) {
            return this.getMockUserData();
        }
        
        if (endpoint.includes('/file-sync/files')) {
            return { files: this.getMockFiles() };
        }
        
        if (endpoint.includes('/health')) {
            return { status: 'mock', service: 'demo-mode' };
        }

        // Default mock response
        return { 
            message: 'Mock response - services unavailable',
            mock_mode: true,
            endpoint: endpoint,
            method: method
        };
    }
}

export const ServiceStatusManager = new ServiceStatusManagerClass();