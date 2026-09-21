/**
 * Advanced Notification System with Real-time Updates
 */

import { ModernToast } from '../ui/ModernComponents.js';
import { WebSocketManager } from '../../utils/websocket.js';
import { ServiceStatusManager } from '../../utils/serviceStatus.js';
import { EventEmitter } from '../../utils/events.js';

export class NotificationSystem extends EventEmitter {
    constructor() {
        super();
        this.notifications = new Map();
        this.isInitialized = false;
        this.notificationQueue = [];
        this.permission = 'default';
        this.config = {
            maxNotifications: 50,
            defaultDuration: 5000,
            enableSound: true,
            enableDesktop: true,
            enableGrouping: true,
            position: 'top-right', // top-right, top-left, bottom-right, bottom-left
            categories: {
                success: { color: '#48bb78', icon: '✅', sound: 'success.mp3' },
                error: { color: '#f56565', icon: '❌', sound: 'error.mp3' },
                warning: { color: '#ed8936', icon: '⚠️', sound: 'warning.mp3' },
                info: { color: '#4299e1', icon: 'ℹ️', sound: 'info.mp3' },
                system: { color: '#805ad5', icon: '🔔', sound: 'system.mp3' },
                update: { color: '#38b2ac', icon: '🔄', sound: 'update.mp3' }
            }
        };
        this.sounds = new Map();
        this.container = null;
    }

    async init(options = {}) {
        if (this.isInitialized) return;

        this.config = { ...this.config, ...options };
        this.createContainer();
        this.requestNotificationPermission();
        this.loadSounds();
        this.setupWebSocketListeners();
        this.setupServiceStatusListeners();
        this.setupGlobalErrorListeners();
        
        this.isInitialized = true;
        this.show('system', 'Notification System Ready', { 
            message: 'Real-time notifications are now active',
            duration: 3000 
        });
    }

    createContainer() {
        if (this.container) return;

        this.container = document.createElement('div');
        this.container.id = 'notification-system';
        this.container.className = `notification-system notification-system--${this.config.position}`;
        
        // Add styles
        const styles = this.getStyles();
        if (!document.querySelector('#notification-system-styles')) {
            const styleSheet = document.createElement('style');
            styleSheet.id = 'notification-system-styles';
            styleSheet.textContent = styles;
            document.head.appendChild(styleSheet);
        }

        document.body.appendChild(this.container);
    }

    async requestNotificationPermission() {
        if ('Notification' in window) {
            this.permission = await Notification.requestPermission();
            if (this.permission === 'granted') {
                this.show('success', 'Desktop Notifications Enabled', {
                    message: 'You will receive desktop notifications when the tab is not active',
                    duration: 4000
                });
            }
        }
    }

    loadSounds() {
        if (!this.config.enableSound) return;

        // In a real implementation, you would load actual sound files
        // For demo purposes, we'll simulate sound loading
        Object.entries(this.config.categories).forEach(([category, config]) => {
            if (config.sound) {
                // Simulate loading sound
                this.sounds.set(category, {
                    loaded: true,
                    play: () => {
                        // In real implementation: audio.play()
                        console.log(`🔊 Playing ${category} notification sound`);
                    }
                });
            }
        });
    }

    setupWebSocketListeners() {
        WebSocketManager.on('connected', () => {
            this.show('success', 'Connected to Server', {
                message: 'Real-time updates are active',
                duration: 3000
            });
        });

        WebSocketManager.on('disconnected', () => {
            this.show('warning', 'Connection Lost', {
                message: 'Attempting to reconnect...',
                duration: 5000,
                persistent: true
            });
        });

        WebSocketManager.on('connectionFailed', () => {
            this.show('error', 'Connection Failed', {
                message: 'Unable to establish real-time connection',
                duration: 8000,
                actions: [
                    {
                        text: 'Retry',
                        action: () => WebSocketManager.connect()
                    }
                ]
            });
        });

        // Listen for server-sent notifications
        WebSocketManager.on('systemNotification', (payload) => {
            this.show(payload.type || 'system', payload.title, {
                message: payload.message,
                duration: payload.duration || this.config.defaultDuration,
                actions: payload.actions || []
            });
        });

        WebSocketManager.on('fileChange', (payload) => {
            this.show('update', 'File Updated', {
                message: `${payload.filename} has been modified`,
                duration: 4000,
                icon: '📄'
            });
        });

        WebSocketManager.on('syncStatus', (payload) => {
            if (payload.status === 'syncing') {
                this.show('info', 'Syncing Files...', {
                    message: `Syncing ${payload.count} files`,
                    duration: 2000,
                    id: 'sync-status'
                });
            } else if (payload.status === 'complete') {
                this.update('sync-status', 'success', 'Sync Complete', {
                    message: `${payload.count} files synchronized`,
                    duration: 3000
                });
            }
        });
    }

    setupServiceStatusListeners() {
        ServiceStatusManager.on('serviceStatusChanged', (change) => {
            const { service, status, previousStatus } = change;
            
            if (status === 'online' && previousStatus !== 'online') {
                this.show('success', `${service} Online`, {
                    message: `${service} service is now available`,
                    duration: 4000
                });
            } else if (status === 'offline' && previousStatus === 'online') {
                this.show('error', `${service} Offline`, {
                    message: `${service} service is currently unavailable`,
                    duration: 8000,
                    persistent: true
                });
            }
        });

        ServiceStatusManager.on('mockModeEnabled', () => {
            this.show('warning', 'Demo Mode Active', {
                message: 'Using mock data due to service unavailability',
                duration: 6000,
                persistent: true
            });
        });
    }

    setupGlobalErrorListeners() {
        window.addEventListener('online', () => {
            this.show('success', 'Back Online', {
                message: 'Internet connection restored',
                duration: 3000
            });
        });

        window.addEventListener('offline', () => {
            this.show('warning', 'Connection Lost', {
                message: 'You are now offline',
                duration: 5000,
                persistent: true
            });
        });

        // Listen to monitoring system errors
        if (window.MonitoringManager) {
            window.MonitoringManager.on('error', (error) => {
                if (error.type === 'javascript_error') {
                    this.show('error', 'Application Error', {
                        message: 'An error occurred in the application',
                        duration: 8000,
                        details: error.message
                    });
                }
            });
        }
    }

    show(type, title, options = {}) {
        const id = options.id || this.generateId();
        const category = this.config.categories[type] || this.config.categories.info;
        
        const notification = {
            id,
            type,
            title,
            message: options.message || '',
            icon: options.icon || category.icon,
            color: category.color,
            duration: options.duration || this.config.defaultDuration,
            persistent: options.persistent || false,
            timestamp: new Date(),
            actions: options.actions || [],
            details: options.details || null,
            group: options.group || null
        };

        // Group similar notifications if enabled
        if (this.config.enableGrouping && notification.group) {
            const existing = Array.from(this.notifications.values())
                .find(n => n.group === notification.group);
            
            if (existing) {
                this.update(existing.id, type, title, options);
                return existing.id;
            }
        }

        // Store notification
        this.notifications.set(id, notification);
        
        // Create and show visual notification
        this.createNotificationElement(notification);
        
        // Play sound
        this.playSound(type);
        
        // Show desktop notification if tab is not active
        this.showDesktopNotification(notification);
        
        // Auto-remove if not persistent
        if (!notification.persistent && notification.duration > 0) {
            setTimeout(() => {
                this.remove(id);
            }, notification.duration);
        }

        // Emit event
        this.emit('notificationShown', notification);
        
        return id;
    }

    update(id, type, title, options = {}) {
        const existing = this.notifications.get(id);
        if (!existing) {
            return this.show(type, title, { ...options, id });
        }

        const category = this.config.categories[type] || this.config.categories.info;
        
        // Update notification data
        const updated = {
            ...existing,
            type,
            title,
            message: options.message || existing.message,
            icon: options.icon || category.icon,
            color: category.color,
            timestamp: new Date(),
            actions: options.actions || existing.actions
        };

        this.notifications.set(id, updated);
        
        // Update visual element
        const element = document.querySelector(`[data-notification-id="${id}"]`);
        if (element) {
            this.updateNotificationElement(element, updated);
        }

        this.emit('notificationUpdated', updated);
        return id;
    }

    remove(id) {
        const notification = this.notifications.get(id);
        if (!notification) return;

        // Remove visual element
        const element = document.querySelector(`[data-notification-id="${id}"]`);
        if (element) {
            element.classList.add('notification--removing');
            setTimeout(() => {
                if (element.parentNode) {
                    element.parentNode.removeChild(element);
                }
            }, 200);
        }

        // Remove from storage
        this.notifications.delete(id);
        
        this.emit('notificationRemoved', notification);
    }

    clear(type = null) {
        const toRemove = type 
            ? Array.from(this.notifications.values()).filter(n => n.type === type)
            : Array.from(this.notifications.values());

        toRemove.forEach(notification => {
            this.remove(notification.id);
        });

        this.emit('notificationsCleared', { type, count: toRemove.length });
    }

    createNotificationElement(notification) {
        const element = document.createElement('div');
        element.className = 'notification';
        element.setAttribute('data-notification-id', notification.id);
        element.setAttribute('data-notification-type', notification.type);

        this.updateNotificationElement(element, notification);
        
        // Add to container
        this.container.appendChild(element);
        
        // Trigger animation
        requestAnimationFrame(() => {
            element.classList.add('notification--show');
        });

        // Add click handlers
        element.addEventListener('click', (e) => {
            if (e.target.classList.contains('notification__close')) {
                this.remove(notification.id);
            } else if (e.target.classList.contains('notification__action')) {
                const actionIndex = parseInt(e.target.dataset.actionIndex);
                const action = notification.actions[actionIndex];
                if (action && action.action) {
                    action.action();
                }
            }
        });
    }

    updateNotificationElement(element, notification) {
        element.innerHTML = `
            <div class="notification__icon" style="color: ${notification.color}">
                ${notification.icon}
            </div>
            <div class="notification__content">
                <div class="notification__title">${notification.title}</div>
                ${notification.message ? `<div class="notification__message">${notification.message}</div>` : ''}
                ${notification.details ? `<div class="notification__details">${notification.details}</div>` : ''}
                ${notification.actions.length > 0 ? `
                    <div class="notification__actions">
                        ${notification.actions.map((action, index) => `
                            <button class="notification__action" data-action-index="${index}">
                                ${action.text}
                            </button>
                        `).join('')}
                    </div>
                ` : ''}
                <div class="notification__timestamp">
                    ${this.formatTimestamp(notification.timestamp)}
                </div>
            </div>
            <button class="notification__close">×</button>
        `;
    }

    playSound(type) {
        if (!this.config.enableSound) return;
        
        const sound = this.sounds.get(type);
        if (sound && sound.loaded) {
            try {
                sound.play();
            } catch (e) {
                console.warn('Failed to play notification sound:', e);
            }
        }
    }

    showDesktopNotification(notification) {
        if (!this.config.enableDesktop || this.permission !== 'granted') return;
        if (document.hasFocus()) return; // Don't show if tab is active

        try {
            const desktopNotification = new Notification(notification.title, {
                body: notification.message,
                icon: '/favicon.ico', // Replace with your app icon
                badge: '/favicon.ico',
                tag: notification.id,
                requireInteraction: notification.persistent
            });

            desktopNotification.onclick = () => {
                window.focus();
                desktopNotification.close();
            };

            // Auto-close desktop notification
            if (!notification.persistent) {
                setTimeout(() => {
                    desktopNotification.close();
                }, notification.duration);
            }
        } catch (e) {
            console.warn('Failed to show desktop notification:', e);
        }
    }

    generateId() {
        return 'notif_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    formatTimestamp(timestamp) {
        const now = new Date();
        const diff = now - timestamp;
        
        if (diff < 60000) { // Less than 1 minute
            return 'Just now';
        } else if (diff < 3600000) { // Less than 1 hour
            const minutes = Math.floor(diff / 60000);
            return `${minutes}m ago`;
        } else {
            return timestamp.toLocaleTimeString();
        }
    }

    getNotifications(type = null) {
        const notifications = Array.from(this.notifications.values());
        return type ? notifications.filter(n => n.type === type) : notifications;
    }

    getStyles() {
        return `
            .notification-system {
                position: fixed;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 12px;
                max-height: 100vh;
                overflow-y: auto;
                pointer-events: none;
            }

            .notification-system--top-right {
                top: 20px;
                right: 20px;
            }

            .notification-system--top-left {
                top: 20px;
                left: 20px;
            }

            .notification-system--bottom-right {
                bottom: 20px;
                right: 20px;
                flex-direction: column-reverse;
            }

            .notification-system--bottom-left {
                bottom: 20px;
                left: 20px;
                flex-direction: column-reverse;
            }

            .notification {
                display: flex;
                align-items: flex-start;
                gap: 12px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
                border: 1px solid rgba(0, 0, 0, 0.08);
                padding: 16px;
                min-width: 320px;
                max-width: 480px;
                transform: translateX(100%);
                opacity: 0;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                pointer-events: auto;
                backdrop-filter: blur(10px);
                position: relative;
                overflow: hidden;
            }

            .notification:before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: currentColor;
                opacity: 0.6;
            }

            .notification--show {
                transform: translateX(0);
                opacity: 1;
            }

            .notification--removing {
                transform: translateX(100%) scale(0.9);
                opacity: 0;
            }

            .notification-system--top-left .notification,
            .notification-system--bottom-left .notification {
                transform: translateX(-100%);
            }

            .notification-system--top-left .notification--show,
            .notification-system--bottom-left .notification--show {
                transform: translateX(0);
            }

            .notification-system--top-left .notification--removing,
            .notification-system--bottom-left .notification--removing {
                transform: translateX(-100%) scale(0.9);
            }

            .notification__icon {
                font-size: 24px;
                flex-shrink: 0;
                margin-top: 2px;
            }

            .notification__content {
                flex: 1;
                min-width: 0;
            }

            .notification__title {
                font-weight: 600;
                color: #1a202c;
                margin-bottom: 4px;
                font-size: 16px;
            }

            .notification__message {
                color: #4a5568;
                font-size: 14px;
                line-height: 1.4;
                margin-bottom: 4px;
            }

            .notification__details {
                color: #718096;
                font-size: 12px;
                font-family: monospace;
                background: #f7fafc;
                padding: 8px;
                border-radius: 4px;
                margin-top: 8px;
                word-break: break-all;
            }

            .notification__actions {
                display: flex;
                gap: 8px;
                margin-top: 12px;
            }

            .notification__action {
                background: #e2e8f0;
                color: #2d3748;
                border: none;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .notification__action:hover {
                background: #cbd5e0;
                transform: translateY(-1px);
            }

            .notification__timestamp {
                color: #a0aec0;
                font-size: 11px;
                margin-top: 8px;
            }

            .notification__close {
                position: absolute;
                top: 12px;
                right: 12px;
                background: none;
                border: none;
                color: #a0aec0;
                cursor: pointer;
                font-size: 18px;
                width: 24px;
                height: 24px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s ease;
            }

            .notification__close:hover {
                background: #f7fafc;
                color: #2d3748;
            }

            /* Animation variants */
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }

            @keyframes slideInLeft {
                from { transform: translateX(-100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }

            /* Mobile responsiveness */
            @media (max-width: 480px) {
                .notification-system {
                    left: 10px !important;
                    right: 10px !important;
                    top: 10px;
                }

                .notification {
                    min-width: auto;
                    max-width: none;
                    width: 100%;
                }

                .notification-system--bottom-right,
                .notification-system--bottom-left {
                    bottom: 10px;
                }
            }

            /* Dark mode support */
            @media (prefers-color-scheme: dark) {
                .notification {
                    background: #2d3748;
                    border-color: #4a5568;
                }

                .notification__title {
                    color: #f7fafc;
                }

                .notification__message {
                    color: #e2e8f0;
                }

                .notification__details {
                    background: #4a5568;
                    color: #e2e8f0;
                }

                .notification__timestamp {
                    color: #718096;
                }

                .notification__action {
                    background: #4a5568;
                    color: #f7fafc;
                }

                .notification__action:hover {
                    background: #718096;
                }

                .notification__close:hover {
                    background: #4a5568;
                    color: #f7fafc;
                }
            }
        `;
    }
}

// Create global instance
export const NotificationManager = new NotificationSystem();

// Auto-initialize
if (typeof window !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        NotificationManager.init();
    });
}