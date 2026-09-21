const { v4: uuidv4 } = require('uuid');
const nodemailer = require('nodemailer');
const twilio = require('twilio');
const logger = require('../config/logger');
const redis = require('../config/redis');
const EventEmitter = require('events');

class NotificationManager extends EventEmitter {
    constructor(socketIO) {
        super();
        this.io = socketIO;
        this.redis = redis.client;
        this.emailTransporter = null;
        this.twilioClient = null;
        this.notificationQueue = [];
        this.notificationHistory = new Map();
        this.userPreferences = new Map();
        this.notificationTemplates = new Map();

        this.initializeProviders();
        this.setupNotificationTemplates();
        this.startNotificationProcessor();
    }

    async initializeProviders() {
        try {
            // Initialize email provider
            if (process.env.SMTP_HOST) {
                this.emailTransporter = nodemailer.createTransporter({
                    host: process.env.SMTP_HOST,
                    port: parseInt(process.env.SMTP_PORT, 10) || 587,
                    secure: process.env.SMTP_SECURE === 'true',
                    auth: {
                        user: process.env.SMTP_USER,
                        pass: process.env.SMTP_PASSWORD
                    }
                });

                // Verify email connection
                await this.emailTransporter.verify();
                logger.info('Email provider initialized successfully');
            } else {
                logger.warn('SMTP configuration not found, email notifications disabled');
            }

            // Initialize SMS provider
            if (process.env.TWILIO_ACCOUNT_SID && process.env.TWILIO_AUTH_TOKEN) {
                this.twilioClient = twilio(
                    process.env.TWILIO_ACCOUNT_SID,
                    process.env.TWILIO_AUTH_TOKEN
                );
                logger.info('SMS provider initialized successfully');
            } else {
                logger.warn('Twilio configuration not found, SMS notifications disabled');
            }

        } catch (error) {
            logger.error('Failed to initialize notification providers', { error: error.message });
        }
    }

    setupNotificationTemplates() {
        // Stock alert templates
        this.notificationTemplates.set('low_stock_alert', {
            email: {
                subject: 'Low Stock Alert - {itemName}',
                text: `Item "{itemName}" (SKU: {sku}) at location "{locationName}" is running low.
                
Current Stock: {currentStock}
Threshold: {threshold}
Location: {locationName}
Time: {timestamp}

Please restock as soon as possible.`,
                html: `
                <h2>Low Stock Alert</h2>
                <p><strong>Item:</strong> {itemName} (SKU: {sku})</p>
                <p><strong>Location:</strong> {locationName}</p>
                <p><strong>Current Stock:</strong> {currentStock}</p>
                <p><strong>Threshold:</strong> {threshold}</p>
                <p><strong>Time:</strong> {timestamp}</p>
                <p style="color: orange;">Please restock as soon as possible.</p>`
            },
            sms: 'LOW STOCK: {itemName} at {locationName} - {currentStock} left (threshold: {threshold}). Please restock.',
            push: {
                title: 'Low Stock Alert',
                body: '{itemName} at {locationName} is running low ({currentStock} left)',
                data: { type: 'low_stock', itemId: '{itemId}', locationId: '{locationId}' }
            }
        });

        this.notificationTemplates.set('out_of_stock_alert', {
            email: {
                subject: 'OUT OF STOCK - {itemName}',
                text: `URGENT: Item "{itemName}" (SKU: {sku}) at location "{locationName}" is OUT OF STOCK.

Location: {locationName}
Time: {timestamp}

Immediate restocking required!`,
                html: `
                <h2 style="color: red;">OUT OF STOCK ALERT</h2>
                <p><strong>Item:</strong> {itemName} (SKU: {sku})</p>
                <p><strong>Location:</strong> {locationName}</p>
                <p><strong>Time:</strong> {timestamp}</p>
                <p style="color: red; font-weight: bold;">Immediate restocking required!</p>`
            },
            sms: 'URGENT: {itemName} at {locationName} is OUT OF STOCK. Immediate restocking required!',
            push: {
                title: 'OUT OF STOCK',
                body: '{itemName} at {locationName} is out of stock',
                data: { type: 'out_of_stock', itemId: '{itemId}', locationId: '{locationId}', priority: 'critical' }
            }
        });

        // Reservation templates
        this.notificationTemplates.set('reservation_created', {
            email: {
                subject: 'Reservation Confirmed - #{reservationId}',
                text: `Your reservation has been confirmed!

Reservation ID: {reservationId}
Customer: {customerName}
Items: {itemCount} items
Total Value: ${totalValue}
Expires: {expiresAt}

Please pick up your items before the expiration time.`,
                html: `
                <h2>Reservation Confirmed</h2>
                <p><strong>Reservation ID:</strong> {reservationId}</p>
                <p><strong>Customer:</strong> {customerName}</p>
                <p><strong>Items:</strong> {itemCount} items</p>
                <p><strong>Total Value:</strong> ${totalValue}</p>
                <p><strong>Expires:</strong> {expiresAt}</p>
                <p>Please pick up your items before the expiration time.</p>`
            },
            sms: 'Reservation {reservationId} confirmed! {itemCount} items reserved. Expires: {expiresAt}. Pick up before expiration.',
            push: {
                title: 'Reservation Confirmed',
                body: '{itemCount} items reserved. Expires {expiresAt}',
                data: { type: 'reservation', reservationId: '{reservationId}' }
            }
        });

        this.notificationTemplates.set('reservation_expiring', {
            email: {
                subject: 'Reservation Expiring Soon - #{reservationId}',
                text: `Your reservation is expiring soon!

Reservation ID: {reservationId}
Expires: {expiresAt}
Items: {itemCount} items

Please pick up your items as soon as possible to avoid cancellation.`,
                html: `
                <h2 style="color: orange;">Reservation Expiring Soon</h2>
                <p><strong>Reservation ID:</strong> {reservationId}</p>
                <p><strong>Expires:</strong> {expiresAt}</p>
                <p><strong>Items:</strong> {itemCount} items</p>
                <p style="color: orange;">Please pick up your items as soon as possible to avoid cancellation.</p>`
            },
            sms: 'REMINDER: Reservation {reservationId} expires at {expiresAt}. Please pick up your {itemCount} items soon!',
            push: {
                title: 'Reservation Expiring Soon',
                body: 'Your reservation expires at {expiresAt}',
                data: { type: 'reservation_expiring', reservationId: '{reservationId}', priority: 'high' }
            }
        });

        // Pickup templates
        this.notificationTemplates.set('pickup_scheduled', {
            email: {
                subject: 'Pickup Scheduled - {pickupDate} at {pickupTime}',
                text: `Your pickup has been scheduled!

Pickup ID: {pickupId}
Date: {pickupDate}
Time: {pickupTime}
Location: {locationName}
Items: {itemCount} items

Please arrive at the scheduled time for quick service.`,
                html: `
                <h2>Pickup Scheduled</h2>
                <p><strong>Pickup ID:</strong> {pickupId}</p>
                <p><strong>Date:</strong> {pickupDate}</p>
                <p><strong>Time:</strong> {pickupTime}</p>
                <p><strong>Location:</strong> {locationName}</p>
                <p><strong>Items:</strong> {itemCount} items</p>
                <p>Please arrive at the scheduled time for quick service.</p>`
            },
            sms: 'Pickup scheduled for {pickupDate} at {pickupTime} at {locationName}. Pickup ID: {pickupId}',
            push: {
                title: 'Pickup Scheduled',
                body: '{pickupDate} at {pickupTime} - {locationName}',
                data: { type: 'pickup_scheduled', pickupId: '{pickupId}' }
            }
        });

        this.notificationTemplates.set('pickup_reminder', {
            email: {
                subject: 'Pickup Reminder - Today at {pickupTime}',
                text: `Reminder: You have a pickup scheduled today!

Pickup ID: {pickupId}
Time: {pickupTime}
Location: {locationName}
Items: {itemCount} items

Please arrive on time. Call {locationPhone} if you need to reschedule.`,
                html: `
                <h2>Pickup Reminder</h2>
                <p><strong>Today at {pickupTime}</strong></p>
                <p><strong>Pickup ID:</strong> {pickupId}</p>
                <p><strong>Location:</strong> {locationName}</p>
                <p><strong>Items:</strong> {itemCount} items</p>
                <p>Please arrive on time. Call {locationPhone} if you need to reschedule.</p>`
            },
            sms: 'Pickup reminder: Today at {pickupTime} at {locationName}. Pickup ID: {pickupId}. {itemCount} items ready.',
            push: {
                title: 'Pickup Today',
                body: 'Today at {pickupTime} - {locationName}',
                data: { type: 'pickup_reminder', pickupId: '{pickupId}', priority: 'high' }
            }
        });

        // Transfer templates
        this.notificationTemplates.set('transfer_requested', {
            email: {
                subject: 'Inventory Transfer Request - {itemName}',
                text: `New inventory transfer request:

Transfer ID: {transferId}
Item: {itemName} (SKU: {sku})
From: {fromLocationName}
To: {toLocationName}
Quantity: {quantity}
Requested by: {requestedBy}
Priority: {priority}

Please review and approve if appropriate.`,
                html: `
                <h2>Inventory Transfer Request</h2>
                <p><strong>Transfer ID:</strong> {transferId}</p>
                <p><strong>Item:</strong> {itemName} (SKU: {sku})</p>
                <p><strong>From:</strong> {fromLocationName}</p>
                <p><strong>To:</strong> {toLocationName}</p>
                <p><strong>Quantity:</strong> {quantity}</p>
                <p><strong>Requested by:</strong> {requestedBy}</p>
                <p><strong>Priority:</strong> {priority}</p>
                <p>Please review and approve if appropriate.</p>`
            },
            sms: 'Transfer request: {quantity} {itemName} from {fromLocationName} to {toLocationName}. ID: {transferId}',
            push: {
                title: 'Transfer Request',
                body: '{quantity} {itemName} - {fromLocationName} → {toLocationName}',
                data: { type: 'transfer_requested', transferId: '{transferId}' }
            }
        });

        logger.info('Notification templates initialized', {
            templateCount: this.notificationTemplates.size
        });
    }

    async sendNotification(notificationData) {
        const notificationId = uuidv4();
        const timestamp = new Date();

        try {
            const {
                type,
                recipients,
                templateData = {},
                priority = 'normal',
                channels = ['email', 'push'], // email, sms, push, websocket
                scheduleAt = null,
                expiresAt = null,
                metadata = {}
            } = notificationData;

            // Create notification record
            const notification = {
                notificationId,
                type,
                recipients: Array.isArray(recipients) ? recipients : [recipients],
                templateData,
                priority,
                channels,
                status: scheduleAt ? 'scheduled' : 'pending',
                createdAt: timestamp.toISOString(),
                updatedAt: timestamp.toISOString(),
                scheduleAt: scheduleAt?.toISOString(),
                expiresAt: expiresAt?.toISOString(),
                attempts: 0,
                maxAttempts: 3,
                results: {},
                metadata
            };

            // Store notification
            await this.storeNotification(notification);

            // Add to queue or schedule
            if (scheduleAt) {
                await this.scheduleNotification(notification);
            } else {
                this.queueNotification(notification);
            }

            logger.logInventoryEvent('notification_created', 'system', 'system', {
                notificationId,
                type,
                recipientCount: notification.recipients.length,
                channels,
                priority
            });

            return {
                notificationId,
                status: notification.status,
                recipients: notification.recipients.length,
                channels
            };

        } catch (error) {
            logger.error('Failed to send notification', {
                notificationData,
                error: error.message,
                stack: error.stack
            });
            throw error;
        }
    }

    async processNotification(notification) {
        try {
            notification.attempts += 1;
            notification.status = 'processing';
            notification.updatedAt = new Date().toISOString();

            const template = this.notificationTemplates.get(notification.type);
            if (!template) {
                throw new Error(`No template found for notification type: ${notification.type}`);
            }

            const results = {};

            // Process each channel
            for (const channel of notification.channels) {
                try {
                    switch (channel) {
                        case 'email':
                            results.email = await this.sendEmailNotification(notification, template);
                            break;
                        
                        case 'sms':
                            results.sms = await this.sendSMSNotification(notification, template);
                            break;
                        
                        case 'push':
                            results.push = await this.sendPushNotification(notification, template);
                            break;
                        
                        case 'websocket':
                            results.websocket = await this.sendWebSocketNotification(notification, template);
                            break;
                        
                        default:
                            results[channel] = { success: false, error: 'Unknown channel' };
                    }
                } catch (channelError) {
                    results[channel] = { 
                        success: false, 
                        error: channelError.message,
                        timestamp: new Date().toISOString()
                    };
                }
            }

            // Determine overall status
            const hasSuccess = Object.values(results).some(result => result.success);
            const allFailed = Object.values(results).every(result => !result.success);

            if (hasSuccess) {
                notification.status = 'sent';
                notification.sentAt = new Date().toISOString();
            } else if (allFailed && notification.attempts >= notification.maxAttempts) {
                notification.status = 'failed';
                notification.failedAt = new Date().toISOString();
            } else {
                notification.status = 'retry';
                notification.nextRetryAt = new Date(Date.now() + (notification.attempts * 60000)).toISOString();
            }

            notification.results = results;
            notification.updatedAt = new Date().toISOString();

            // Store updated notification
            await this.storeNotification(notification);

            // Schedule retry if needed
            if (notification.status === 'retry') {
                setTimeout(() => {
                    this.queueNotification(notification);
                }, notification.attempts * 60000); // Exponential backoff
            }

            logger.logInventoryEvent('notification_processed', 'system', 'system', {
                notificationId: notification.notificationId,
                type: notification.type,
                status: notification.status,
                attempts: notification.attempts,
                channels: Object.keys(results),
                success: hasSuccess
            });

            return results;

        } catch (error) {
            notification.status = 'error';
            notification.error = error.message;
            notification.updatedAt = new Date().toISOString();
            
            await this.storeNotification(notification);

            logger.error('Failed to process notification', {
                notificationId: notification.notificationId,
                type: notification.type,
                error: error.message
            });

            throw error;
        }
    }

    async sendEmailNotification(notification, template) {
        if (!this.emailTransporter) {
            throw new Error('Email provider not configured');
        }

        const emailTemplate = template.email;
        if (!emailTemplate) {
            throw new Error('No email template found');
        }

        const results = [];

        for (const recipient of notification.recipients) {
            try {
                // Get recipient preferences
                const preferences = await this.getUserPreferences(recipient.userId || recipient.email);
                
                if (!preferences.email) {
                    results.push({
                        recipient: recipient.email,
                        success: false,
                        error: 'Email notifications disabled'
                    });
                    continue;
                }

                // Render template
                const subject = this.renderTemplate(emailTemplate.subject, notification.templateData);
                const text = this.renderTemplate(emailTemplate.text, notification.templateData);
                const html = this.renderTemplate(emailTemplate.html, notification.templateData);

                // Send email
                const info = await this.emailTransporter.sendMail({
                    from: process.env.SMTP_FROM || 'noreply@inventory-sync.com',
                    to: recipient.email,
                    subject,
                    text,
                    html
                });

                results.push({
                    recipient: recipient.email,
                    success: true,
                    messageId: info.messageId,
                    timestamp: new Date().toISOString()
                });

            } catch (error) {
                results.push({
                    recipient: recipient.email,
                    success: false,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        }

        const successCount = results.filter(r => r.success).length;
        
        return {
            success: successCount > 0,
            successCount,
            totalCount: results.length,
            results
        };
    }

    async sendSMSNotification(notification, template) {
        if (!this.twilioClient) {
            throw new Error('SMS provider not configured');
        }

        const smsTemplate = template.sms;
        if (!smsTemplate) {
            throw new Error('No SMS template found');
        }

        const results = [];

        for (const recipient of notification.recipients) {
            try {
                if (!recipient.phone) {
                    results.push({
                        recipient: recipient.phone || 'unknown',
                        success: false,
                        error: 'No phone number provided'
                    });
                    continue;
                }

                // Get recipient preferences
                const preferences = await this.getUserPreferences(recipient.userId || recipient.phone);
                
                if (!preferences.sms) {
                    results.push({
                        recipient: recipient.phone,
                        success: false,
                        error: 'SMS notifications disabled'
                    });
                    continue;
                }

                // Render template
                const message = this.renderTemplate(smsTemplate, notification.templateData);

                // Send SMS
                const twilioMessage = await this.twilioClient.messages.create({
                    from: process.env.TWILIO_PHONE_NUMBER,
                    to: recipient.phone,
                    body: message
                });

                results.push({
                    recipient: recipient.phone,
                    success: true,
                    messageId: twilioMessage.sid,
                    timestamp: new Date().toISOString()
                });

            } catch (error) {
                results.push({
                    recipient: recipient.phone,
                    success: false,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        }

        const successCount = results.filter(r => r.success).length;
        
        return {
            success: successCount > 0,
            successCount,
            totalCount: results.length,
            results
        };
    }

    async sendPushNotification(notification, template) {
        const pushTemplate = template.push;
        if (!pushTemplate) {
            throw new Error('No push template found');
        }

        const results = [];

        for (const recipient of notification.recipients) {
            try {
                // Get recipient preferences
                const preferences = await this.getUserPreferences(recipient.userId);
                
                if (!preferences.push) {
                    results.push({
                        recipient: recipient.userId,
                        success: false,
                        error: 'Push notifications disabled'
                    });
                    continue;
                }

                // Render template
                const title = this.renderTemplate(pushTemplate.title, notification.templateData);
                const body = this.renderTemplate(pushTemplate.body, notification.templateData);
                const data = {};
                
                // Render data fields
                for (const [key, value] of Object.entries(pushTemplate.data || {})) {
                    data[key] = this.renderTemplate(value, notification.templateData);
                }

                const pushData = {
                    title,
                    body,
                    data,
                    priority: notification.priority,
                    timestamp: new Date().toISOString()
                };

                // Send via WebSocket to user's devices
                this.io.to(`user:${recipient.userId}`).emit('push_notification', pushData);

                results.push({
                    recipient: recipient.userId,
                    success: true,
                    timestamp: new Date().toISOString()
                });

            } catch (error) {
                results.push({
                    recipient: recipient.userId,
                    success: false,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        }

        const successCount = results.filter(r => r.success).length;
        
        return {
            success: successCount > 0,
            successCount,
            totalCount: results.length,
            results
        };
    }

    async sendWebSocketNotification(notification, template) {
        const results = [];

        for (const recipient of notification.recipients) {
            try {
                const notificationData = {
                    notificationId: notification.notificationId,
                    type: notification.type,
                    templateData: notification.templateData,
                    priority: notification.priority,
                    timestamp: new Date().toISOString()
                };

                // Send to user's active sessions
                this.io.to(`user:${recipient.userId}`).emit('notification', notificationData);

                // Send to location if specified
                if (notification.templateData.locationId) {
                    this.io.to(`location:${notification.templateData.locationId}`).emit('location_notification', notificationData);
                }

                results.push({
                    recipient: recipient.userId,
                    success: true,
                    timestamp: new Date().toISOString()
                });

            } catch (error) {
                results.push({
                    recipient: recipient.userId,
                    success: false,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        }

        const successCount = results.filter(r => r.success).length;
        
        return {
            success: successCount > 0,
            successCount,
            totalCount: results.length,
            results
        };
    }

    renderTemplate(template, data) {
        if (!template) return '';
        
        let rendered = template;
        
        // Replace template variables
        for (const [key, value] of Object.entries(data)) {
            const regex = new RegExp(`{${key}}`, 'g');
            rendered = rendered.replace(regex, String(value));
        }

        return rendered;
    }

    async getUserPreferences(userId) {
        if (this.userPreferences.has(userId)) {
            return this.userPreferences.get(userId);
        }

        // Load from Redis
        const prefsKey = `user_prefs:${userId}`;
        const prefsData = await this.redis.hgetall(prefsKey);

        const preferences = {
            email: prefsData.email !== 'false',
            sms: prefsData.sms !== 'false',
            push: prefsData.push !== 'false',
            websocket: prefsData.websocket !== 'false',
            lowStockAlerts: prefsData.lowStockAlerts !== 'false',
            reservationReminders: prefsData.reservationReminders !== 'false',
            pickupReminders: prefsData.pickupReminders !== 'false',
            transferAlerts: prefsData.transferAlerts !== 'false',
            ...prefsData
        };

        this.userPreferences.set(userId, preferences);
        return preferences;
    }

    async updateUserPreferences(userId, preferences) {
        try {
            const prefsKey = `user_prefs:${userId}`;
            
            // Update in Redis
            await this.redis.hmset(prefsKey, preferences);
            
            // Update cache
            const currentPrefs = await this.getUserPreferences(userId);
            const updatedPrefs = { ...currentPrefs, ...preferences };
            this.userPreferences.set(userId, updatedPrefs);

            logger.logInventoryEvent('user_preferences_updated', 'system', userId, {
                updatedFields: Object.keys(preferences)
            });

            return updatedPrefs;

        } catch (error) {
            logger.error('Failed to update user preferences', {
                userId,
                preferences,
                error: error.message
            });
            throw error;
        }
    }

    queueNotification(notification) {
        this.notificationQueue.push(notification);
    }

    async scheduleNotification(notification) {
        const delay = new Date(notification.scheduleAt).getTime() - Date.now();
        
        if (delay > 0) {
            setTimeout(() => {
                this.queueNotification(notification);
            }, delay);
            
            logger.debug('Notification scheduled', {
                notificationId: notification.notificationId,
                type: notification.type,
                scheduleAt: notification.scheduleAt,
                delay
            });
        } else {
            // Schedule time has passed, send immediately
            this.queueNotification(notification);
        }
    }

    async storeNotification(notification) {
        const notifKey = `notification:${notification.notificationId}`;
        
        await this.redis.hmset(notifKey, {
            notificationId: notification.notificationId,
            type: notification.type,
            recipients: JSON.stringify(notification.recipients),
            templateData: JSON.stringify(notification.templateData),
            priority: notification.priority,
            channels: JSON.stringify(notification.channels),
            status: notification.status,
            createdAt: notification.createdAt,
            updatedAt: notification.updatedAt,
            scheduleAt: notification.scheduleAt || '',
            expiresAt: notification.expiresAt || '',
            sentAt: notification.sentAt || '',
            failedAt: notification.failedAt || '',
            attempts: notification.attempts,
            maxAttempts: notification.maxAttempts,
            results: JSON.stringify(notification.results || {}),
            error: notification.error || '',
            metadata: JSON.stringify(notification.metadata || {})
        });

        // Set expiration (30 days)
        await this.redis.expire(notifKey, 86400 * 30);

        // Update history
        if (!this.notificationHistory.has(notification.type)) {
            this.notificationHistory.set(notification.type, []);
        }
        
        const history = this.notificationHistory.get(notification.type);
        history.push({
            notificationId: notification.notificationId,
            status: notification.status,
            timestamp: notification.updatedAt
        });

        // Keep only last 1000 notifications per type
        if (history.length > 1000) {
            this.notificationHistory.set(notification.type, history.slice(-1000));
        }
    }

    async getNotification(notificationId) {
        const notifKey = `notification:${notificationId}`;
        const notifData = await this.redis.hgetall(notifKey);

        if (Object.keys(notifData).length === 0) {
            return null;
        }

        return {
            ...notifData,
            recipients: JSON.parse(notifData.recipients || '[]'),
            templateData: JSON.parse(notifData.templateData || '{}'),
            channels: JSON.parse(notifData.channels || '[]'),
            results: JSON.parse(notifData.results || '{}'),
            metadata: JSON.parse(notifData.metadata || '{}'),
            attempts: parseInt(notifData.attempts, 10)
        };
    }

    startNotificationProcessor() {
        // Process notification queue every 5 seconds
        setInterval(async () => {
            if (this.notificationQueue.length > 0) {
                const notification = this.notificationQueue.shift();
                
                try {
                    await this.processNotification(notification);
                } catch (error) {
                    logger.error('Failed to process queued notification', {
                        notificationId: notification.notificationId,
                        error: error.message
                    });
                }
            }
        }, 5000);

        // Clean up expired notifications daily
        setInterval(async () => {
            await this.cleanupExpiredNotifications();
        }, 86400000); // 24 hours

        logger.info('Notification processor started');
    }

    async cleanupExpiredNotifications() {
        try {
            const pattern = 'notification:*';
            const keys = await this.redis.keys(pattern);
            
            let cleanedCount = 0;
            const now = new Date();

            for (const key of keys) {
                const notifData = await this.redis.hgetall(key);
                
                if (Object.keys(notifData).length > 0 && notifData.expiresAt) {
                    const expiresAt = new Date(notifData.expiresAt);
                    
                    if (expiresAt <= now) {
                        await this.redis.del(key);
                        cleanedCount++;
                    }
                }
            }

            if (cleanedCount > 0) {
                logger.info('Cleaned up expired notifications', { count: cleanedCount });
            }

        } catch (error) {
            logger.error('Failed to cleanup expired notifications', { error: error.message });
        }
    }

    // Convenience methods for common notification types
    async sendLowStockAlert(alertData) {
        return await this.sendNotification({
            type: 'low_stock_alert',
            recipients: alertData.recipients,
            templateData: {
                itemName: alertData.itemName,
                sku: alertData.sku,
                locationName: alertData.locationName,
                currentStock: alertData.currentStock,
                threshold: alertData.threshold,
                timestamp: new Date().toLocaleString(),
                itemId: alertData.itemId,
                locationId: alertData.locationId
            },
            priority: 'high',
            channels: ['email', 'push', 'websocket']
        });
    }

    async sendOutOfStockAlert(alertData) {
        return await this.sendNotification({
            type: 'out_of_stock_alert',
            recipients: alertData.recipients,
            templateData: {
                itemName: alertData.itemName,
                sku: alertData.sku,
                locationName: alertData.locationName,
                timestamp: new Date().toLocaleString(),
                itemId: alertData.itemId,
                locationId: alertData.locationId
            },
            priority: 'critical',
            channels: ['email', 'sms', 'push', 'websocket']
        });
    }

    async sendReservationNotification(reservationData, type = 'reservation_created') {
        return await this.sendNotification({
            type,
            recipients: [{
                userId: reservationData.customerId,
                email: reservationData.customerInfo?.email,
                phone: reservationData.customerInfo?.phone
            }],
            templateData: {
                reservationId: reservationData.reservationId,
                customerName: reservationData.customerInfo?.name || 'Customer',
                itemCount: reservationData.items?.length || 0,
                totalValue: reservationData.totalValue || 0,
                expiresAt: reservationData.expiresAt,
                locationName: reservationData.locationName
            },
            priority: type.includes('expiring') ? 'high' : 'normal',
            channels: reservationData.contactPreferences?.email !== false ? ['email', 'push'] : ['push']
        });
    }

    async sendPickupNotification(pickupData, type = 'pickup_scheduled') {
        return await this.sendNotification({
            type,
            recipients: [{
                userId: pickupData.customerId,
                email: pickupData.contactInfo?.email,
                phone: pickupData.contactInfo?.phone
            }],
            templateData: {
                pickupId: pickupData.pickupId,
                pickupDate: pickupData.scheduledDate,
                pickupTime: pickupData.timeSlot?.startTime,
                locationName: pickupData.locationName,
                itemCount: pickupData.items?.length || 0,
                locationPhone: pickupData.locationPhone
            },
            priority: type === 'pickup_reminder' ? 'high' : 'normal',
            channels: ['email', 'push']
        });
    }

    async sendTransferNotification(transferData, type = 'transfer_requested') {
        return await this.sendNotification({
            type,
            recipients: transferData.recipients,
            templateData: {
                transferId: transferData.transferId,
                itemName: transferData.itemName,
                sku: transferData.sku,
                fromLocationName: transferData.fromLocationName,
                toLocationName: transferData.toLocationName,
                quantity: transferData.quantity,
                requestedBy: transferData.requestedBy,
                priority: transferData.priority
            },
            priority: transferData.priority === 'urgent' ? 'high' : 'normal',
            channels: ['email', 'push', 'websocket']
        });
    }

    async getNotificationHistory(userId, options = {}) {
        const {
            type = null,
            status = null,
            limit = 50,
            offset = 0,
            startDate = null,
            endDate = null
        } = options;

        try {
            const pattern = 'notification:*';
            const keys = await this.redis.keys(pattern);
            
            const notifications = [];

            for (const key of keys) {
                const notifData = await this.redis.hgetall(key);
                
                if (Object.keys(notifData).length > 0) {
                    const notification = {
                        ...notifData,
                        recipients: JSON.parse(notifData.recipients || '[]'),
                        templateData: JSON.parse(notifData.templateData || '{}'),
                        channels: JSON.parse(notifData.channels || '[]'),
                        results: JSON.parse(notifData.results || '{}')
                    };

                    // Filter by user
                    const isForUser = notification.recipients.some(r => 
                        r.userId === userId || r.email === userId
                    );
                    
                    if (!isForUser) continue;

                    // Apply filters
                    if (type && notification.type !== type) continue;
                    if (status && notification.status !== status) continue;
                    
                    if (startDate) {
                        const createdAt = new Date(notification.createdAt);
                        if (createdAt < new Date(startDate)) continue;
                    }
                    
                    if (endDate) {
                        const createdAt = new Date(notification.createdAt);
                        if (createdAt > new Date(endDate)) continue;
                    }

                    notifications.push(notification);
                }
            }

            // Sort by creation time (most recent first)
            notifications.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

            // Apply pagination
            const paginatedResults = notifications.slice(offset, offset + limit);

            return {
                notifications: paginatedResults,
                total: notifications.length,
                limit,
                offset
            };

        } catch (error) {
            logger.error('Failed to get notification history', {
                userId,
                options,
                error: error.message
            });
            throw error;
        }
    }

    async getNotificationMetrics(options = {}) {
        const {
            startDate = new Date(Date.now() - 24 * 60 * 60 * 1000), // 24 hours ago
            endDate = new Date()
        } = options;

        const metrics = {
            totalNotifications: 0,
            sentNotifications: 0,
            failedNotifications: 0,
            pendingNotifications: 0,
            channelBreakdown: {},
            typeBreakdown: {},
            successRate: 0,
            averageProcessingTime: 0,
            timestamp: new Date().toISOString()
        };

        try {
            const pattern = 'notification:*';
            const keys = await this.redis.keys(pattern);

            for (const key of keys) {
                const notifData = await this.redis.hgetall(key);
                
                if (Object.keys(notifData).length > 0) {
                    const createdAt = new Date(notifData.createdAt);
                    
                    // Filter by date range
                    if (createdAt >= startDate && createdAt <= endDate) {
                        metrics.totalNotifications++;

                        switch (notifData.status) {
                            case 'sent':
                                metrics.sentNotifications++;
                                break;
                            case 'failed':
                                metrics.failedNotifications++;
                                break;
                            case 'pending':
                            case 'scheduled':
                            case 'retry':
                                metrics.pendingNotifications++;
                                break;
                        }

                        // Channel breakdown
                        const channels = JSON.parse(notifData.channels || '[]');
                        for (const channel of channels) {
                            if (!metrics.channelBreakdown[channel]) {
                                metrics.channelBreakdown[channel] = 0;
                            }
                            metrics.channelBreakdown[channel]++;
                        }

                        // Type breakdown
                        const type = notifData.type;
                        if (!metrics.typeBreakdown[type]) {
                            metrics.typeBreakdown[type] = { count: 0, sent: 0, failed: 0 };
                        }
                        metrics.typeBreakdown[type].count++;
                        
                        if (notifData.status === 'sent') {
                            metrics.typeBreakdown[type].sent++;
                        } else if (notifData.status === 'failed') {
                            metrics.typeBreakdown[type].failed++;
                        }
                    }
                }
            }

            // Calculate success rate
            if (metrics.totalNotifications > 0) {
                metrics.successRate = (metrics.sentNotifications / metrics.totalNotifications) * 100;
            }

            return metrics;

        } catch (error) {
            logger.error('Failed to get notification metrics', {
                options,
                error: error.message
            });
            throw error;
        }
    }
}

module.exports = NotificationManager;