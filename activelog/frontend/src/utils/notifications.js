/**
 * Notification Manager for showing toast notifications
 */

class NotificationManagerClass {
    constructor() {
        this.container = null;
        this.notifications = new Map();
        this.nextId = 1;
    }

    init(container) {
        this.container = container;
        if (!this.container) {
            console.warn('Notification container not found');
        }
    }

    show(message, type = 'info', duration = 5000, options = {}) {
        if (!this.container) {
            console.warn('Notification container not initialized');
            return null;
        }

        const id = this.nextId++;
        const notification = this.createNotification(id, message, type, duration, options);
        
        this.container.appendChild(notification);
        this.notifications.set(id, notification);

        // Trigger entrance animation
        requestAnimationFrame(() => {
            notification.classList.add('show');
        });

        // Auto-dismiss
        if (duration > 0) {
            setTimeout(() => {
                this.dismiss(id);
            }, duration);
        }

        return id;
    }

    createNotification(id, message, type, duration, options) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.dataset.id = id;

        const icon = this.getIcon(type);
        const showClose = options.showClose !== false;
        const showProgress = duration > 0 && options.showProgress !== false;

        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-icon">${icon}</div>
                <div class="notification-message">${message}</div>
                ${showClose ? '<button class="notification-close" aria-label="Close">&times;</button>' : ''}
            </div>
            ${showProgress ? '<div class="notification-progress"><div class="notification-progress-bar"></div></div>' : ''}
        `;

        // Add event listeners
        if (showClose) {
            const closeBtn = notification.querySelector('.notification-close');
            closeBtn.addEventListener('click', () => this.dismiss(id));
        }

        // Progress bar animation
        if (showProgress) {
            const progressBar = notification.querySelector('.notification-progress-bar');
            progressBar.style.animationDuration = `${duration}ms`;
        }

        // Allow clicking the notification to dismiss it
        notification.addEventListener('click', (e) => {
            if (!e.target.classList.contains('notification-close')) {
                this.dismiss(id);
            }
        });

        return notification;
    }

    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ⓘ'
        };
        return icons[type] || icons.info;
    }

    dismiss(id) {
        const notification = this.notifications.get(id);
        if (!notification) return;

        notification.classList.add('dismiss');
        
        // Remove from DOM after animation
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            this.notifications.delete(id);
        }, 300);
    }

    dismissAll() {
        this.notifications.forEach((notification, id) => {
            this.dismiss(id);
        });
    }

    // Convenience methods
    success(message, duration = 5000, options = {}) {
        return this.show(message, 'success', duration, options);
    }

    error(message, duration = 8000, options = {}) {
        return this.show(message, 'error', duration, options);
    }

    warning(message, duration = 6000, options = {}) {
        return this.show(message, 'warning', duration, options);
    }

    info(message, duration = 5000, options = {}) {
        return this.show(message, 'info', duration, options);
    }

    // Persistent notifications (no auto-dismiss)
    persistent(message, type = 'info', options = {}) {
        return this.show(message, type, 0, { ...options, showClose: true });
    }
}

export const NotificationManager = new NotificationManagerClass();