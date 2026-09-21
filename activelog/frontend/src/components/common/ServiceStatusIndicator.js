/**
 * Service Status Indicator Component
 */

import { ServiceStatusManager } from '../../utils/serviceStatus.js';

export class ServiceStatusIndicator {
    constructor() {
        this.element = null;
        this.isExpanded = false;
        this.init();
    }

    init() {
        this.createElement();
        this.attachEventListeners();
        this.updateDisplay();
    }

    createElement() {
        this.element = document.createElement('div');
        this.element.className = 'service-status-indicator';
        this.element.innerHTML = `
            <div class="status-badge" id="status-badge">
                <span class="status-icon" id="status-icon">🔄</span>
                <span class="status-text" id="status-text">Checking...</span>
                <span class="expand-arrow" id="expand-arrow">▼</span>
            </div>
            <div class="status-details" id="status-details" style="display: none;">
                <div class="status-header">
                    <h4>Service Status</h4>
                    <button class="refresh-btn" id="refresh-btn" title="Refresh Status">🔄</button>
                </div>
                <div class="services-list" id="services-list">
                    <!-- Services will be populated here -->
                </div>
                <div class="status-actions">
                    <button class="mock-mode-toggle" id="mock-mode-toggle">
                        <span id="mock-mode-text">Enable Demo Mode</span>
                    </button>
                </div>
                <div class="status-footer">
                    <small>Last updated: <span id="last-updated">Never</span></small>
                </div>
            </div>
            ${this.getStyles()}
        `;
    }

    attachEventListeners() {
        // Toggle expanded view
        const statusBadge = this.element.querySelector('#status-badge');
        statusBadge.addEventListener('click', () => this.toggleExpanded());

        // Refresh button
        const refreshBtn = this.element.querySelector('#refresh-btn');
        refreshBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            ServiceStatusManager.checkAllServices();
        });

        // Mock mode toggle
        const mockModeToggle = this.element.querySelector('#mock-mode-toggle');
        mockModeToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleMockMode();
        });

        // Listen to service status updates
        ServiceStatusManager.on('statusUpdate', (status) => {
            this.updateDisplay(status);
        });

        ServiceStatusManager.on('serviceStatusChanged', (change) => {
            this.showNotification(change);
        });

        ServiceStatusManager.on('mockModeEnabled', () => {
            this.updateMockModeButton(true);
        });

        ServiceStatusManager.on('mockModeDisabled', () => {
            this.updateMockModeButton(false);
        });

        // Close when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.element.contains(e.target) && this.isExpanded) {
                this.collapse();
            }
        });
    }

    updateDisplay(status = null) {
        if (!status) {
            status = ServiceStatusManager.getStatus();
        }

        this.updateBadge(status);
        this.updateServicesList(status);
        this.updateLastUpdated();
        this.updateMockModeButton(status.mockMode);
    }

    updateBadge(status) {
        const statusIcon = this.element.querySelector('#status-icon');
        const statusText = this.element.querySelector('#status-text');
        const statusBadge = this.element.querySelector('#status-badge');

        let icon = '🔄';
        let text = 'Checking...';
        let className = 'checking';

        switch (status.overall) {
            case 'healthy':
                icon = '🟢';
                text = 'All Systems Operational';
                className = 'healthy';
                break;
            case 'degraded':
                icon = '🟡';
                text = 'Some Services Offline';
                className = 'degraded';
                break;
            case 'unknown':
                icon = '🔄';
                text = 'Checking Services...';
                className = 'checking';
                break;
        }

        if (status.mockMode) {
            icon = '🧪';
            text = 'Demo Mode Active';
            className = 'mock';
        }

        statusIcon.textContent = icon;
        statusText.textContent = text;
        statusBadge.className = `status-badge ${className}`;
    }

    updateServicesList(status) {
        const servicesList = this.element.querySelector('#services-list');
        const services = status.services || {};

        let servicesHtml = '';
        Object.entries(services).forEach(([name, service]) => {
            let statusClass = 'unknown';
            let statusIcon = '🔄';
            let statusText = 'Unknown';

            switch (service.status) {
                case 'online':
                    statusClass = 'online';
                    statusIcon = '🟢';
                    statusText = 'Online';
                    break;
                case 'offline':
                    statusClass = 'offline';
                    statusIcon = '🔴';
                    statusText = 'Offline';
                    break;
                case 'error':
                    statusClass = 'error';
                    statusIcon = '🟡';
                    statusText = 'Error';
                    break;
            }

            const isRequired = service.required ? ' (Required)' : '';
            const lastChecked = service.lastChecked ? 
                new Date(service.lastChecked).toLocaleTimeString() : 'Never';

            servicesHtml += `
                <div class="service-item ${statusClass}">
                    <div class="service-info">
                        <span class="service-icon">${statusIcon}</span>
                        <span class="service-name">${name}${isRequired}</span>
                        <span class="service-status">${statusText}</span>
                    </div>
                    <div class="service-details">
                        <small>Last checked: ${lastChecked}</small>
                    </div>
                </div>
            `;
        });

        // Add critical services summary
        const critical = status.critical || {};
        servicesHtml = `
            <div class="critical-summary">
                <strong>Critical Services: ${critical.online || 0}/${critical.total || 0} Online</strong>
            </div>
            ${servicesHtml}
        `;

        servicesList.innerHTML = servicesHtml;
    }

    updateLastUpdated() {
        const lastUpdatedEl = this.element.querySelector('#last-updated');
        lastUpdatedEl.textContent = new Date().toLocaleTimeString();
    }

    updateMockModeButton(isMockMode) {
        const mockModeToggle = this.element.querySelector('#mock-mode-toggle');
        const mockModeText = this.element.querySelector('#mock-mode-text');

        if (isMockMode) {
            mockModeToggle.classList.add('active');
            mockModeText.textContent = 'Disable Demo Mode';
        } else {
            mockModeToggle.classList.remove('active');
            mockModeText.textContent = 'Enable Demo Mode';
        }
    }

    toggleExpanded() {
        if (this.isExpanded) {
            this.collapse();
        } else {
            this.expand();
        }
    }

    expand() {
        const statusDetails = this.element.querySelector('#status-details');
        const expandArrow = this.element.querySelector('#expand-arrow');
        
        statusDetails.style.display = 'block';
        expandArrow.textContent = '▲';
        this.isExpanded = true;
        
        // Refresh data when expanding
        ServiceStatusManager.checkAllServices();
    }

    collapse() {
        const statusDetails = this.element.querySelector('#status-details');
        const expandArrow = this.element.querySelector('#expand-arrow');
        
        statusDetails.style.display = 'none';
        expandArrow.textContent = '▼';
        this.isExpanded = false;
    }

    toggleMockMode() {
        if (ServiceStatusManager.isMockMode()) {
            ServiceStatusManager.disableMockMode();
        } else {
            ServiceStatusManager.enableMockMode();
        }
    }

    showNotification(change) {
        // Create a temporary notification
        const notification = document.createElement('div');
        notification.className = 'service-notification';
        notification.innerHTML = `
            <strong>${change.service}</strong> is now <strong>${change.status}</strong>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }

    render(container) {
        if (container) {
            container.appendChild(this.element);
        }
        return this.element;
    }

    getStyles() {
        return `
            <style>
                .service-status-indicator {
                    position: relative;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                    font-size: 14px;
                }

                .status-badge {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px 12px;
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 20px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    user-select: none;
                }

                .status-badge:hover {
                    background: #e9ecef;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }

                .status-badge.healthy {
                    background: #d4edda;
                    border-color: #c3e6cb;
                }

                .status-badge.degraded {
                    background: #fff3cd;
                    border-color: #ffeaa7;
                }

                .status-badge.checking {
                    background: #e2e3e5;
                    border-color: #c6c8ca;
                }

                .status-badge.mock {
                    background: #e7f3ff;
                    border-color: #bee5eb;
                }

                .status-icon {
                    font-size: 16px;
                }

                .status-text {
                    font-weight: 500;
                    white-space: nowrap;
                }

                .expand-arrow {
                    font-size: 10px;
                    opacity: 0.6;
                    transition: transform 0.2s ease;
                }

                .status-details {
                    position: absolute;
                    top: 100%;
                    right: 0;
                    width: 350px;
                    background: white;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    z-index: 1000;
                    margin-top: 5px;
                    animation: slideDown 0.2s ease;
                }

                @keyframes slideDown {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                .status-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 12px 16px;
                    border-bottom: 1px solid #dee2e6;
                }

                .status-header h4 {
                    margin: 0;
                    font-size: 16px;
                    font-weight: 600;
                }

                .refresh-btn {
                    background: none;
                    border: none;
                    cursor: pointer;
                    padding: 4px;
                    border-radius: 4px;
                    transition: background 0.2s ease;
                }

                .refresh-btn:hover {
                    background: #f8f9fa;
                }

                .critical-summary {
                    padding: 12px 16px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #dee2e6;
                    font-size: 13px;
                }

                .services-list {
                    max-height: 250px;
                    overflow-y: auto;
                }

                .service-item {
                    padding: 10px 16px;
                    border-bottom: 1px solid #f1f3f4;
                }

                .service-item:last-child {
                    border-bottom: none;
                }

                .service-info {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .service-icon {
                    font-size: 14px;
                }

                .service-name {
                    flex: 1;
                    font-weight: 500;
                }

                .service-status {
                    font-size: 12px;
                    opacity: 0.8;
                }

                .service-details {
                    margin-top: 4px;
                    font-size: 11px;
                    opacity: 0.6;
                }

                .status-actions {
                    padding: 12px 16px;
                    border-top: 1px solid #dee2e6;
                    border-bottom: 1px solid #dee2e6;
                }

                .mock-mode-toggle {
                    width: 100%;
                    padding: 8px 12px;
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: 13px;
                }

                .mock-mode-toggle:hover {
                    background: #e9ecef;
                }

                .mock-mode-toggle.active {
                    background: #007bff;
                    color: white;
                    border-color: #007bff;
                }

                .status-footer {
                    padding: 8px 16px;
                    text-align: center;
                    font-size: 11px;
                    opacity: 0.6;
                }

                .service-notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #fff;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 12px 16px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    z-index: 10000;
                    font-size: 14px;
                    animation: slideIn 0.3s ease;
                }

                @keyframes slideIn {
                    from { opacity: 0; transform: translateX(100%); }
                    to { opacity: 1; transform: translateX(0); }
                }

                /* Mobile responsiveness */
                @media (max-width: 768px) {
                    .status-details {
                        width: 300px;
                        right: 0;
                        left: auto;
                    }
                    
                    .status-text {
                        display: none;
                    }
                }

                @media (max-width: 400px) {
                    .status-details {
                        width: calc(100vw - 40px);
                        left: 20px;
                        right: 20px;
                    }
                }
            </style>
        `;
    }
}