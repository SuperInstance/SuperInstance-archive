/**
 * Real-time Notification Center with WebSocket Support
 */

import { WebSocketManager } from '../../utils/websocket.js';
import { NotificationManager } from '../../utils/notifications.js';
import { API } from '../../utils/api.js';

export class NotificationCenter {
    constructor(options = {}) {
        this.container = null;
        this.isOpen = false;
        this.notifications = [];
        this.unreadCount = 0;
        
        this.maxNotifications = options.maxNotifications || 100;
        this.autoMarkRead = options.autoMarkRead !== false;
        this.groupSimilar = options.groupSimilar !== false;
        this.enableSound = options.enableSound !== false;
        
        this.filters = {
            types: [],
            sources: [],
            priority: 'all'
        };
        
        this.sortBy = 'timestamp';
        this.sortOrder = 'desc';
        
        this.onNotificationClick = options.onNotificationClick || (() => {});
        this.onNotificationAction = options.onNotificationAction || (() => {});
        
        this.setupWebSocketListeners();
    }
    
    async render(container) {
        this.container = container;
        
        container.innerHTML = `
            <div class="notification-center">
                <div class="notification-trigger">
                    <button class="notification-bell" title="Notifications">
                        <i data-lucide="bell"></i>
                        <span class="notification-badge ${this.unreadCount > 0 ? 'visible' : ''}" 
                              id="notification-badge">${this.unreadCount}</span>
                    </button>
                </div>
                
                <div class="notification-panel ${this.isOpen ? 'open' : ''}" id="notification-panel">
                    <div class="notification-header">
                        <div class="header-title">
                            <h3>Notifications</h3>
                            <span class="notification-count">${this.notifications.length} total</span>
                        </div>
                        
                        <div class="header-actions">
                            <button class="btn-icon mark-all-read" title="Mark all as read">
                                <i data-lucide="check"></i>
                            </button>
                            <button class="btn-icon clear-all" title="Clear all">
                                <i data-lucide="trash-2"></i>
                            </button>
                            <button class="btn-icon notification-settings" title="Settings">
                                <i data-lucide="settings"></i>
                            </button>
                            <button class="btn-icon close-panel" title="Close">
                                <i data-lucide="x"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div class="notification-filters">
                        <div class="filter-group">
                            <select class="filter-type">
                                <option value="all">All Types</option>
                                <option value="upload">Uploads</option>
                                <option value="processing">Processing</option>
                                <option value="error">Errors</option>
                                <option value="system">System</option>
                                <option value="sharing">Sharing</option>
                            </select>
                            
                            <select class="filter-priority">
                                <option value="all">All Priority</option>
                                <option value="high">High</option>
                                <option value="medium">Medium</option>
                                <option value="low">Low</option>
                            </select>
                            
                            <button class="btn-icon filter-clear" title="Clear filters">
                                <i data-lucide="filter-x"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div class="notification-list" id="notification-list">
                        <div class="loading-notifications">
                            <i data-lucide="loader" class="spin"></i>
                            <span>Loading notifications...</span>
                        </div>
                    </div>
                    
                    <div class="notification-footer">
                        <div class="footer-actions">
                            <button class="load-more-btn" style="display: none;">
                                Load More
                            </button>
                            <div class="notification-status">
                                <span class="status-text">All caught up!</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="notification-overlay" id="notification-overlay"></div>
            </div>
        `;
        
        this.setupEventListeners();
        await this.loadNotifications();
    }
    
    setupEventListeners() {
        // Notification bell toggle
        this.container.querySelector('.notification-bell').addEventListener('click', () => {
            this.togglePanel();
        });
        
        // Close panel
        this.container.querySelector('.close-panel').addEventListener('click', () => {
            this.closePanel();
        });
        
        // Overlay click to close
        this.container.querySelector('#notification-overlay').addEventListener('click', () => {
            this.closePanel();
        });
        
        // Header actions
        this.container.querySelector('.mark-all-read').addEventListener('click', () => {
            this.markAllAsRead();
        });
        
        this.container.querySelector('.clear-all').addEventListener('click', () => {
            this.clearAllNotifications();
        });
        
        this.container.querySelector('.notification-settings').addEventListener('click', () => {
            this.showSettings();
        });
        
        // Filters
        this.container.querySelector('.filter-type').addEventListener('change', (e) => {
            this.updateFilter('type', e.target.value);
        });
        
        this.container.querySelector('.filter-priority').addEventListener('change', (e) => {
            this.updateFilter('priority', e.target.value);
        });
        
        this.container.querySelector('.filter-clear').addEventListener('click', () => {
            this.clearFilters();
        });
        
        // Load more
        this.container.querySelector('.load-more-btn').addEventListener('click', () => {
            this.loadMoreNotifications();
        });
        
        // Notification list events
        this.container.querySelector('#notification-list').addEventListener('click', (e) => {
            this.handleNotificationClick(e);
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closePanel();
            }
        });
    }
    
    setupWebSocketListeners() {
        // Listen for real-time notifications
        WebSocketManager.on('notification', (data) => {
            this.handleIncomingNotification(data);
        });
        
        WebSocketManager.on('notification_read', (data) => {
            this.markNotificationAsRead(data.id, false);
        });
        
        WebSocketManager.on('notification_dismissed', (data) => {
            this.removeNotification(data.id, false);
        });
        
        // Connection status updates
        WebSocketManager.on('connected', () => {
            this.updateConnectionStatus(true);
        });
        
        WebSocketManager.on('disconnected', () => {
            this.updateConnectionStatus(false);
        });
    }
    
    async loadNotifications() {
        try {
            const response = await API.get('/notifications', {
                limit: 50,
                offset: 0,
                filters: this.filters
            });
            
            this.notifications = response.notifications || [];
            this.updateUnreadCount();
            this.renderNotifications();
            
        } catch (error) {
            console.error('Failed to load notifications:', error);
            this.renderErrorState();
        }
    }
    
    async loadMoreNotifications() {
        try {
            const response = await API.get('/notifications', {
                limit: 50,
                offset: this.notifications.length,
                filters: this.filters
            });
            
            const newNotifications = response.notifications || [];
            this.notifications.push(...newNotifications);
            this.renderNotifications();
            
            // Hide load more button if no more notifications
            if (newNotifications.length < 50) {
                this.container.querySelector('.load-more-btn').style.display = 'none';
            }
            
        } catch (error) {
            console.error('Failed to load more notifications:', error);
            NotificationManager.error('Failed to load more notifications');
        }
    }
    
    handleIncomingNotification(notificationData) {
        const notification = {
            id: notificationData.id || Date.now().toString(),
            type: notificationData.type || 'info',
            title: notificationData.title || 'New Notification',
            message: notificationData.message || '',
            timestamp: notificationData.timestamp || new Date().toISOString(),
            read: false,
            priority: notificationData.priority || 'medium',
            source: notificationData.source || 'system',
            actions: notificationData.actions || [],
            data: notificationData.data || {}
        };
        
        // Add to beginning of list
        this.notifications.unshift(notification);
        
        // Limit total notifications
        if (this.notifications.length > this.maxNotifications) {
            this.notifications = this.notifications.slice(0, this.maxNotifications);
        }
        
        this.updateUnreadCount();
        this.renderNotifications();
        this.showToastNotification(notification);
        
        if (this.enableSound) {
            this.playNotificationSound(notification.priority);
        }
    }
    
    showToastNotification(notification) {
        const toast = document.createElement('div');
        toast.className = `notification-toast ${notification.type} ${notification.priority}`;
        toast.innerHTML = `
            <div class="toast-icon">
                <i data-lucide="${this.getNotificationIcon(notification.type)}"></i>
            </div>
            <div class="toast-content">
                <div class="toast-title">${notification.title}</div>
                <div class="toast-message">${notification.message}</div>
            </div>
            <button class="toast-close">
                <i data-lucide="x"></i>
            </button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto dismiss after delay
        const dismissDelay = this.getToastDismissDelay(notification.priority);
        setTimeout(() => {
            this.dismissToast(toast);
        }, dismissDelay);
        
        // Manual dismiss
        toast.querySelector('.toast-close').addEventListener('click', () => {
            this.dismissToast(toast);
        });
        
        // Click to view
        toast.addEventListener('click', () => {
            this.openPanel();
            this.highlightNotification(notification.id);
            this.dismissToast(toast);
        });
        
        // Animate in
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
    }
    
    dismissToast(toast) {
        toast.classList.add('hide');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }
    
    renderNotifications() {
        const listContainer = this.container.querySelector('#notification-list');
        
        if (this.notifications.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-notifications">
                    <div class="empty-icon">
                        <i data-lucide="bell-off"></i>
                    </div>
                    <div class="empty-text">No notifications</div>
                </div>
            `;
            return;
        }
        
        const filteredNotifications = this.getFilteredNotifications();
        const groupedNotifications = this.groupSimilar ? 
            this.groupSimilarNotifications(filteredNotifications) : 
            filteredNotifications;
        
        const html = groupedNotifications.map(item => {
            if (item.group) {
                return this.renderNotificationGroup(item);
            } else {
                return this.renderNotificationItem(item);
            }
        }).join('');
        
        listContainer.innerHTML = html;
        
        // Update counters
        this.updateCounters();
    }
    
    renderNotificationItem(notification) {
        const timeAgo = this.getTimeAgo(notification.timestamp);
        const icon = this.getNotificationIcon(notification.type);
        
        return `
            <div class="notification-item ${notification.read ? 'read' : 'unread'} ${notification.priority}" 
                 data-id="${notification.id}"
                 data-type="${notification.type}">
                <div class="notification-icon">
                    <i data-lucide="${icon}"></i>
                </div>
                
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-meta">
                        <span class="notification-time">${timeAgo}</span>
                        <span class="notification-source">${notification.source}</span>
                        ${notification.priority !== 'medium' ? 
                            `<span class="notification-priority ${notification.priority}">${notification.priority}</span>` : 
                            ''}
                    </div>
                    
                    ${notification.actions && notification.actions.length > 0 ? `
                        <div class="notification-actions">
                            ${notification.actions.map(action => `
                                <button class="notification-action" 
                                        data-action="${action.type}" 
                                        data-notification-id="${notification.id}">
                                    ${action.label}
                                </button>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
                
                <div class="notification-controls">
                    <button class="btn-icon mark-read" title="${notification.read ? 'Mark as unread' : 'Mark as read'}">
                        <i data-lucide="${notification.read ? 'mail' : 'mail-open'}"></i>
                    </button>
                    <button class="btn-icon dismiss" title="Dismiss">
                        <i data-lucide="x"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    renderNotificationGroup(group) {
        const latestNotification = group.notifications[0];
        const count = group.notifications.length;
        const icon = this.getNotificationIcon(group.type);
        
        return `
            <div class="notification-group" data-type="${group.type}">
                <div class="group-header">
                    <div class="group-icon">
                        <i data-lucide="${icon}"></i>
                    </div>
                    <div class="group-title">${group.title}</div>
                    <div class="group-count">${count} notifications</div>
                    <button class="group-toggle" data-expanded="false">
                        <i data-lucide="chevron-down"></i>
                    </button>
                </div>
                
                <div class="group-preview">
                    ${latestNotification.message}
                </div>
                
                <div class="group-notifications" style="display: none;">
                    ${group.notifications.map(notification => 
                        this.renderNotificationItem(notification)
                    ).join('')}
                </div>
            </div>
        `;
    }
    
    groupSimilarNotifications(notifications) {
        const groups = new Map();
        const ungrouped = [];
        
        notifications.forEach(notification => {
            const groupKey = `${notification.type}-${notification.source}`;
            
            if (groups.has(groupKey)) {
                groups.get(groupKey).notifications.push(notification);
            } else if (this.shouldGroup(notification)) {
                groups.set(groupKey, {
                    group: true,
                    type: notification.type,
                    title: this.getGroupTitle(notification.type, notification.source),
                    notifications: [notification]
                });
            } else {
                ungrouped.push(notification);
            }
        });
        
        // Only return groups with multiple notifications
        const validGroups = Array.from(groups.values()).filter(group => 
            group.notifications.length > 1
        );
        
        // Add single notifications from invalid groups to ungrouped
        Array.from(groups.values()).forEach(group => {
            if (group.notifications.length === 1) {
                ungrouped.push(group.notifications[0]);
            }
        });
        
        return [...validGroups, ...ungrouped];
    }
    
    shouldGroup(notification) {
        const groupableTypes = ['upload', 'processing', 'download'];
        return groupableTypes.includes(notification.type);
    }
    
    getGroupTitle(type, source) {
        const titles = {
            upload: 'File Uploads',
            processing: 'File Processing',
            download: 'Downloads',
            error: 'Errors',
            system: 'System Updates'
        };
        
        return titles[type] || 'Notifications';
    }
    
    getFilteredNotifications() {
        return this.notifications.filter(notification => {
            // Type filter
            if (this.filters.types.length > 0 && !this.filters.types.includes(notification.type)) {
                return false;
            }
            
            // Source filter
            if (this.filters.sources.length > 0 && !this.filters.sources.includes(notification.source)) {
                return false;
            }
            
            // Priority filter
            if (this.filters.priority !== 'all' && notification.priority !== this.filters.priority) {
                return false;
            }
            
            return true;
        });
    }
    
    handleNotificationClick(e) {
        const notificationItem = e.target.closest('.notification-item');
        const groupToggle = e.target.closest('.group-toggle');
        const markReadBtn = e.target.closest('.mark-read');
        const dismissBtn = e.target.closest('.dismiss');
        const actionBtn = e.target.closest('.notification-action');
        
        if (groupToggle) {
            this.toggleNotificationGroup(groupToggle);
        } else if (markReadBtn) {
            const notificationId = notificationItem.dataset.id;
            this.toggleNotificationRead(notificationId);
        } else if (dismissBtn) {
            const notificationId = notificationItem.dataset.id;
            this.dismissNotification(notificationId);
        } else if (actionBtn) {
            const notificationId = actionBtn.dataset.notificationId;
            const actionType = actionBtn.dataset.action;
            this.handleNotificationAction(notificationId, actionType);
        } else if (notificationItem) {
            const notificationId = notificationItem.dataset.id;
            this.openNotification(notificationId);
        }
    }
    
    toggleNotificationGroup(toggle) {
        const group = toggle.closest('.notification-group');
        const notifications = group.querySelector('.group-notifications');
        const isExpanded = toggle.dataset.expanded === 'true';
        
        if (isExpanded) {
            notifications.style.display = 'none';
            toggle.dataset.expanded = 'false';
            toggle.querySelector('i').setAttribute('data-lucide', 'chevron-down');
        } else {
            notifications.style.display = 'block';
            toggle.dataset.expanded = 'true';
            toggle.querySelector('i').setAttribute('data-lucide', 'chevron-up');
        }
    }
    
    async toggleNotificationRead(notificationId) {
        const notification = this.notifications.find(n => n.id === notificationId);
        if (!notification) return;
        
        try {
            await API.post(`/notifications/${notificationId}/read`, {
                read: !notification.read
            });
            
            this.markNotificationAsRead(notificationId, !notification.read);
            
        } catch (error) {
            console.error('Failed to update notification read status:', error);
            NotificationManager.error('Failed to update notification');
        }
    }
    
    async dismissNotification(notificationId) {
        try {
            await API.delete(`/notifications/${notificationId}`);
            this.removeNotification(notificationId);
            
        } catch (error) {
            console.error('Failed to dismiss notification:', error);
            NotificationManager.error('Failed to dismiss notification');
        }
    }
    
    openNotification(notificationId) {
        const notification = this.notifications.find(n => n.id === notificationId);
        if (!notification) return;
        
        // Mark as read if auto-mark is enabled
        if (this.autoMarkRead && !notification.read) {
            this.toggleNotificationRead(notificationId);
        }
        
        this.onNotificationClick(notification);
    }
    
    handleNotificationAction(notificationId, actionType) {
        const notification = this.notifications.find(n => n.id === notificationId);
        if (!notification) return;
        
        this.onNotificationAction(notification, actionType);
    }
    
    markNotificationAsRead(notificationId, read = true, updateServer = true) {
        const notification = this.notifications.find(n => n.id === notificationId);
        if (!notification) return;
        
        notification.read = read;
        this.updateUnreadCount();
        this.renderNotifications();
        
        if (updateServer) {
            API.post(`/notifications/${notificationId}/read`, { read })
                .catch(error => console.error('Failed to sync read status:', error));
        }
    }
    
    removeNotification(notificationId, updateServer = true) {
        this.notifications = this.notifications.filter(n => n.id !== notificationId);
        this.updateUnreadCount();
        this.renderNotifications();
        
        if (updateServer) {
            API.delete(`/notifications/${notificationId}`)
                .catch(error => console.error('Failed to sync notification removal:', error));
        }
    }
    
    async markAllAsRead() {
        try {
            await API.post('/notifications/read-all');
            
            this.notifications.forEach(notification => {
                notification.read = true;
            });
            
            this.updateUnreadCount();
            this.renderNotifications();
            
            NotificationManager.success('All notifications marked as read');
            
        } catch (error) {
            console.error('Failed to mark all as read:', error);
            NotificationManager.error('Failed to mark all as read');
        }
    }
    
    async clearAllNotifications() {
        const confirmed = confirm('Are you sure you want to clear all notifications?');
        if (!confirmed) return;
        
        try {
            await API.delete('/notifications/all');
            
            this.notifications = [];
            this.updateUnreadCount();
            this.renderNotifications();
            
            NotificationManager.success('All notifications cleared');
            
        } catch (error) {
            console.error('Failed to clear all notifications:', error);
            NotificationManager.error('Failed to clear notifications');
        }
    }
    
    updateFilter(type, value) {
        switch (type) {
            case 'type':
                this.filters.types = value === 'all' ? [] : [value];
                break;
            case 'priority':
                this.filters.priority = value;
                break;
        }
        
        this.renderNotifications();
    }
    
    clearFilters() {
        this.filters = {
            types: [],
            sources: [],
            priority: 'all'
        };
        
        this.container.querySelector('.filter-type').value = 'all';
        this.container.querySelector('.filter-priority').value = 'all';
        
        this.renderNotifications();
    }
    
    updateUnreadCount() {
        this.unreadCount = this.notifications.filter(n => !n.read).length;
        
        const badge = this.container.querySelector('#notification-badge');
        badge.textContent = this.unreadCount;
        badge.classList.toggle('visible', this.unreadCount > 0);
    }
    
    updateCounters() {
        const countElement = this.container.querySelector('.notification-count');
        countElement.textContent = `${this.notifications.length} total`;
    }
    
    updateConnectionStatus(connected) {
        const statusElement = this.container.querySelector('.status-text');
        if (statusElement) {
            statusElement.textContent = connected ? 'Connected' : 'Disconnected';
            statusElement.className = `status-text ${connected ? 'connected' : 'disconnected'}`;
        }
    }
    
    togglePanel() {
        if (this.isOpen) {
            this.closePanel();
        } else {
            this.openPanel();
        }
    }
    
    openPanel() {
        this.isOpen = true;
        this.container.querySelector('#notification-panel').classList.add('open');
        this.container.querySelector('#notification-overlay').classList.add('visible');
        
        // Mark notifications as read when panel is opened
        if (this.autoMarkRead) {
            setTimeout(() => {
                this.markVisibleNotificationsAsRead();
            }, 1000);
        }
    }
    
    closePanel() {
        this.isOpen = false;
        this.container.querySelector('#notification-panel').classList.remove('open');
        this.container.querySelector('#notification-overlay').classList.remove('visible');
    }
    
    markVisibleNotificationsAsRead() {
        // Mark unread notifications as read after viewing
        this.notifications.forEach(notification => {
            if (!notification.read) {
                this.markNotificationAsRead(notification.id);
            }
        });
    }
    
    highlightNotification(notificationId) {
        const element = this.container.querySelector(`[data-id="${notificationId}"]`);
        if (element) {
            element.classList.add('highlighted');
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            setTimeout(() => {
                element.classList.remove('highlighted');
            }, 2000);
        }
    }
    
    showSettings() {
        // Implementation for notification settings modal
        NotificationManager.info('Notification settings coming soon');
    }
    
    renderErrorState() {
        const listContainer = this.container.querySelector('#notification-list');
        listContainer.innerHTML = `
            <div class="error-state">
                <div class="error-icon">
                    <i data-lucide="alert-circle"></i>
                </div>
                <div class="error-text">Failed to load notifications</div>
                <button class="retry-btn">Retry</button>
            </div>
        `;
        
        listContainer.querySelector('.retry-btn').addEventListener('click', () => {
            this.loadNotifications();
        });
    }
    
    getNotificationIcon(type) {
        const icons = {
            upload: 'upload',
            download: 'download',
            processing: 'loader',
            error: 'alert-circle',
            warning: 'alert-triangle',
            success: 'check-circle',
            info: 'info',
            system: 'settings',
            sharing: 'share',
            security: 'shield'
        };
        
        return icons[type] || 'bell';
    }
    
    getTimeAgo(timestamp) {
        const now = new Date();
        const date = new Date(timestamp);
        const diffMs = now - date;
        
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffMinutes < 1) return 'Just now';
        if (diffMinutes < 60) return `${diffMinutes}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }
    
    getToastDismissDelay(priority) {
        const delays = {
            high: 8000,
            medium: 5000,
            low: 3000
        };
        
        return delays[priority] || 5000;
    }
    
    playNotificationSound(priority) {
        // Implementation for notification sounds
        const audio = new Audio();
        
        const soundFiles = {
            high: '/sounds/notification-high.mp3',
            medium: '/sounds/notification-medium.mp3',
            low: '/sounds/notification-low.mp3'
        };
        
        audio.src = soundFiles[priority] || soundFiles.medium;
        audio.volume = 0.3;
        audio.play().catch(() => {
            // Ignore audio play errors (browser restrictions)
        });
    }
    
    getUnreadCount() {
        return this.unreadCount;
    }
    
    getNotifications() {
        return [...this.notifications];
    }
    
    addNotification(notification) {
        this.handleIncomingNotification(notification);
    }
}