/**
 * Header Component
 */

import { AuthManager } from '../../utils/auth.js';
import { WebSocketManager } from '../../utils/websocket.js';
import { GlobalEvents } from '../../utils/events.js';

export class Header {
    constructor() {
        this.user = null;
        this.connectionStatus = 'disconnected';
    }

    async render(container) {
        this.user = AuthManager.getUser();
        
        container.innerHTML = `
            <header class="app-header">
                <div class="header-left">
                    <div class="app-logo">
                        <span class="logo-icon">🚀</span>
                        <span class="logo-text">ActiveLog.ai</span>
                    </div>
                    
                    <div class="connection-status" id="connection-status">
                        <div class="status-indicator ${this.connectionStatus}"></div>
                        <span class="status-text">${this.getConnectionText()}</span>
                    </div>
                </div>
                
                <div class="header-center">
                    <div class="global-search">
                        <input type="text" id="global-search" placeholder="Search files, tags, content..." />
                        <button class="search-button" id="search-button">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"/>
                                <path d="m21 21-4.35-4.35"/>
                            </svg>
                        </button>
                    </div>
                </div>
                
                <div class="header-right">
                    <div class="sync-status" id="sync-status">
                        <div class="sync-indicator">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
                                <path d="M21 3v5h-5"/>
                                <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
                                <path d="M3 21v-5h5"/>
                            </svg>
                        </div>
                        <span class="sync-text">Synced</span>
                    </div>
                    
                    <div class="notifications" id="notifications-button">
                        <button class="notification-button">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>
                                <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                            </svg>
                            <span class="notification-badge" id="notification-badge" style="display: none;">0</span>
                        </button>
                    </div>
                    
                    <div class="user-menu" id="user-menu">
                        <button class="user-button" id="user-button">
                            <div class="user-avatar">
                                ${this.getUserInitials()}
                            </div>
                            <span class="user-name">${this.user?.name || 'User'}</span>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="6,9 12,15 18,9"/>
                            </svg>
                        </button>
                        
                        <div class="user-dropdown" id="user-dropdown" style="display: none;">
                            <div class="dropdown-header">
                                <div class="user-info">
                                    <div class="user-name">${this.user?.name || 'User'}</div>
                                    <div class="user-email">${this.user?.email || ''}</div>
                                </div>
                            </div>
                            <div class="dropdown-divider"></div>
                            <a href="/settings" class="dropdown-item">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="3"/>
                                    <path d="M12 1v6m0 6v6"/>
                                    <path d="m12 1 4 4-4 4-4-4 4-4z"/>
                                </svg>
                                Settings
                            </a>
                            <a href="#" class="dropdown-item" id="help-link">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"/>
                                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                                    <circle cx="12" cy="17" r="1"/>
                                </svg>
                                Help
                            </a>
                            <div class="dropdown-divider"></div>
                            <a href="#" class="dropdown-item" id="logout-button">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                                    <polyline points="16,17 21,12 16,7"/>
                                    <line x1="21" y1="12" x2="9" y2="12"/>
                                </svg>
                                Logout
                            </a>
                        </div>
                    </div>
                </div>
            </header>
        `;

        this.attachEventListeners();
        this.setupWebSocketListeners();
    }

    attachEventListeners() {
        // User menu toggle
        const userButton = document.getElementById('user-button');
        const userDropdown = document.getElementById('user-dropdown');
        
        userButton?.addEventListener('click', (e) => {
            e.stopPropagation();
            const isVisible = userDropdown.style.display !== 'none';
            userDropdown.style.display = isVisible ? 'none' : 'block';
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
            if (userDropdown) {
                userDropdown.style.display = 'none';
            }
        });

        // Logout
        const logoutButton = document.getElementById('logout-button');
        logoutButton?.addEventListener('click', async (e) => {
            e.preventDefault();
            await AuthManager.logout();
        });

        // Global search
        const searchInput = document.getElementById('global-search');
        const searchButton = document.getElementById('search-button');
        
        const handleSearch = () => {
            const query = searchInput.value.trim();
            if (query) {
                GlobalEvents.emit('globalSearch', query);
                // Navigate to search page with query
                window.location.hash = `/search?q=${encodeURIComponent(query)}`;
            }
        };

        searchButton?.addEventListener('click', handleSearch);
        searchInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleSearch();
            }
        });

        // Notifications
        const notificationButton = document.getElementById('notifications-button');
        notificationButton?.addEventListener('click', () => {
            GlobalEvents.emit('showNotifications');
        });
    }

    setupWebSocketListeners() {
        // Connection status updates
        WebSocketManager.on('connected', () => {
            this.updateConnectionStatus('connected');
        });

        WebSocketManager.on('disconnected', () => {
            this.updateConnectionStatus('disconnected');
        });

        WebSocketManager.on('connectionFailed', () => {
            this.updateConnectionStatus('error');
        });

        // Sync status updates
        WebSocketManager.on('syncStatus', (status) => {
            this.updateSyncStatus(status);
        });

        // Notification updates
        WebSocketManager.on('systemNotification', (notification) => {
            this.updateNotificationBadge();
        });
    }

    updateConnectionStatus(status) {
        this.connectionStatus = status;
        const statusElement = document.getElementById('connection-status');
        
        if (statusElement) {
            const indicator = statusElement.querySelector('.status-indicator');
            const text = statusElement.querySelector('.status-text');
            
            indicator.className = `status-indicator ${status}`;
            text.textContent = this.getConnectionText();
        }
    }

    getConnectionText() {
        const statusTexts = {
            connected: 'Online',
            disconnected: 'Offline',
            error: 'Connection Error'
        };
        return statusTexts[this.connectionStatus] || 'Unknown';
    }

    updateSyncStatus(status) {
        const syncElement = document.getElementById('sync-status');
        if (!syncElement) return;

        const indicator = syncElement.querySelector('.sync-indicator');
        const text = syncElement.querySelector('.sync-text');

        // Update based on sync status
        switch (status.state) {
            case 'syncing':
                indicator.classList.add('syncing');
                text.textContent = 'Syncing...';
                break;
            case 'synced':
                indicator.classList.remove('syncing');
                text.textContent = 'Synced';
                break;
            case 'error':
                indicator.classList.add('error');
                text.textContent = 'Sync Error';
                break;
            default:
                text.textContent = 'Unknown';
        }
    }

    updateNotificationBadge() {
        // This would typically get the actual notification count from a service
        const badge = document.getElementById('notification-badge');
        if (badge) {
            // For now, just show a simple indicator
            badge.style.display = 'block';
            badge.textContent = '•';
        }
    }

    getUserInitials() {
        const name = this.user?.name || 'User';
        return name.split(' ')
            .map(word => word.charAt(0))
            .join('')
            .toUpperCase()
            .substring(0, 2);
    }
}