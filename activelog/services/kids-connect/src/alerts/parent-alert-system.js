const EventEmitter = require('events');
const nodemailer = require('nodemailer');
const twilio = require('twilio');
const crypto = require('crypto');

class ParentAlertSystem extends EventEmitter {
    constructor() {
        super();
        this.alertQueue = [];
        this.parentContacts = new Map();
        this.alertHistory = new Map();
        this.alertTemplates = new Map();
        this.deliveryChannels = new Map();
        this.emergencyEscalation = new Map();
        this.alertPreferences = new Map();
        this.rateLimiting = new Map();
        this.alertMetrics = new Map();
        
        this.initializeAlertSystem();
        this.setupDeliveryChannels();
        this.initializeAlertTemplates();
    }

    initializeAlertSystem() {
        this.severityLevels = {
            critical: {
                priority: 1,
                deliveryMethods: ['sms', 'phone-call', 'email', 'app-push'],
                maxDelay: 60, // 1 minute
                escalationTime: 300, // 5 minutes if not acknowledged
                requireAcknowledgment: true,
                multipleAttempts: true,
                emergencyContacts: true
            },
            high: {
                priority: 2,
                deliveryMethods: ['email', 'sms', 'app-push'],
                maxDelay: 300, // 5 minutes
                escalationTime: 1800, // 30 minutes
                requireAcknowledgment: true,
                multipleAttempts: false,
                emergencyContacts: false
            },
            medium: {
                priority: 3,
                deliveryMethods: ['email', 'app-push'],
                maxDelay: 900, // 15 minutes
                escalationTime: 3600, // 1 hour
                requireAcknowledgment: false,
                multipleAttempts: false,
                emergencyContacts: false
            },
            low: {
                priority: 4,
                deliveryMethods: ['app-push', 'email'],
                maxDelay: 3600, // 1 hour
                escalationTime: null,
                requireAcknowledgment: false,
                multipleAttempts: false,
                emergencyContacts: false
            },
            info: {
                priority: 5,
                deliveryMethods: ['app-push'],
                maxDelay: 7200, // 2 hours
                escalationTime: null,
                requireAcknowledgment: false,
                multipleAttempts: false,
                emergencyContacts: false
            }
        };

        this.alertTypes = {
            safety: {
                inappropriateContent: { severity: 'high', category: 'content-safety' },
                predatoryBehavior: { severity: 'critical', category: 'child-safety' },
                cyberbullying: { severity: 'high', category: 'social-safety' },
                personalInfoShared: { severity: 'critical', category: 'privacy-safety' },
                offPlatformCommunication: { severity: 'critical', category: 'safety-protocol' },
                meetingRequest: { severity: 'critical', category: 'physical-safety' },
                selfHarmExpression: { severity: 'critical', category: 'mental-health' }
            },
            behavior: {
                excessiveUsage: { severity: 'medium', category: 'digital-wellbeing' },
                timeViolation: { severity: 'medium', category: 'time-management' },
                behaviorChange: { severity: 'medium', category: 'behavioral-patterns' },
                socialWithdrawal: { severity: 'medium', category: 'social-wellbeing' }
            },
            connection: {
                newConnection: { severity: 'info', category: 'social-activity' },
                connectionBlocked: { severity: 'high', category: 'safety-action' },
                suspiciousContact: { severity: 'critical', category: 'safety-warning' }
            },
            achievement: {
                milestone: { severity: 'info', category: 'positive-news' },
                improvement: { severity: 'info', category: 'progress-update' },
                concern: { severity: 'medium', category: 'academic-concern' }
            },
            system: {
                accountSuspended: { severity: 'critical', category: 'account-status' },
                policyViolation: { severity: 'high', category: 'platform-policy' },
                technicalIssue: { severity: 'low', category: 'technical-support' }
            }
        };

        // Rate limiting to prevent alert fatigue
        this.rateLimits = {
            critical: { maxPerHour: 10, maxPerDay: 50 },
            high: { maxPerHour: 5, maxPerDay: 20 },
            medium: { maxPerHour: 3, maxPerDay: 10 },
            low: { maxPerHour: 2, maxPerDay: 5 },
            info: { maxPerHour: 1, maxPerDay: 3 }
        };
    }

    setupDeliveryChannels() {
        // Email setup
        this.emailTransporter = nodemailer.createTransporter({
            service: process.env.EMAIL_SERVICE || 'smtp.gmail.com',
            auth: {
                user: process.env.EMAIL_USER,
                pass: process.env.EMAIL_PASS
            },
            secure: true
        });

        // SMS setup (Twilio)
        if (process.env.TWILIO_SID && process.env.TWILIO_TOKEN) {
            this.twilioClient = twilio(
                process.env.TWILIO_SID,
                process.env.TWILIO_TOKEN
            );
        }

        // App push notifications would be integrated with Firebase/APNs
        this.pushNotificationService = {
            send: async (token, notification) => {
                // Implementation for push notifications
                this.emit('pushNotificationSent', { token, notification });
            }
        };

        // Phone call service for critical alerts
        this.phoneCallService = {
            call: async (phoneNumber, message) => {
                if (this.twilioClient) {
                    try {
                        const call = await this.twilioClient.calls.create({
                            twiml: `<Response><Say>${message}</Say></Response>`,
                            to: phoneNumber,
                            from: process.env.TWILIO_PHONE_NUMBER
                        });
                        return { success: true, callSid: call.sid };
                    } catch (error) {
                        return { success: false, error: error.message };
                    }
                }
                return { success: false, error: 'Phone service not configured' };
            }
        };
    }

    initializeAlertTemplates() {
        this.alertTemplates.set('inappropriateContent', {
            subject: '🚨 Safety Alert: Inappropriate Content Detected',
            sms: 'URGENT: Inappropriate content detected in {childName}\'s activity. Please check your email for details.',
            email: {
                html: `
                    <h2 style="color: #d32f2f;">Safety Alert: Inappropriate Content</h2>
                    <p>Dear {parentName},</p>
                    <p>We detected inappropriate content in {childName}'s interactions on Kids Connect.</p>
                    <p><strong>What happened:</strong> {description}</p>
                    <p><strong>Time:</strong> {timestamp}</p>
                    <p><strong>Our response:</strong> {systemResponse}</p>
                    <p><strong>Recommended actions:</strong></p>
                    <ul>
                        <li>Talk to {childName} about appropriate online behavior</li>
                        <li>Review their recent activity in the parent dashboard</li>
                        <li>Consider adjusting their privacy settings</li>
                    </ul>
                    <p><a href="{dashboardLink}" style="background: #1976d2; color: white; padding: 10px 20px; text-decoration: none;">View Full Report</a></p>
                    <p>If you have concerns, please contact our support team immediately.</p>
                `,
                text: `Safety Alert: Inappropriate content detected in {childName}'s activity. Time: {timestamp}. Please check your parent dashboard for full details.`
            },
            push: {
                title: 'Safety Alert',
                body: 'Inappropriate content detected for {childName}',
                data: { type: 'safety', severity: 'high' }
            }
        });

        this.alertTemplates.set('predatoryBehavior', {
            subject: '🆘 CRITICAL SAFETY ALERT: Potential Predatory Behavior',
            sms: 'CRITICAL ALERT: Potential predatory behavior detected. We have taken immediate safety measures. Please call us NOW at {supportPhone}.',
            email: {
                html: `
                    <h2 style="color: #b71c1c; font-weight: bold;">🆘 CRITICAL SAFETY ALERT</h2>
                    <p style="color: #b71c1c; font-weight: bold;">POTENTIAL PREDATORY BEHAVIOR DETECTED</p>
                    <p>Dear {parentName},</p>
                    <p><strong>We have detected potential predatory behavior targeting {childName} and have taken immediate action to protect them.</strong></p>
                    <p><strong>Immediate actions taken:</strong></p>
                    <ul>
                        <li>✓ {childName} has been immediately disconnected from all sessions</li>
                        <li>✓ The suspicious account has been blocked and reported</li>
                        <li>✓ All communication logs have been preserved as evidence</li>
                        <li>✓ Appropriate authorities have been notified</li>
                    </ul>
                    <p><strong>What you need to do RIGHT NOW:</strong></p>
                    <ol>
                        <li><strong>Talk to {childName}</strong> - Ask if anyone has made them feel uncomfortable</li>
                        <li><strong>Contact us immediately</strong> - Call {supportPhone}</li>
                        <li><strong>Consider involving local authorities</strong> if appropriate</li>
                    </ol>
                    <p style="background: #ffebee; padding: 15px; border-left: 4px solid #f44336;">
                        <strong>Time is critical:</strong> Please call us within the next hour at {supportPhone}. 
                        Our child safety team is standing by to assist you.
                    </p>
                    <p><strong>Support resources:</strong></p>
                    <ul>
                        <li>National Center for Missing & Exploited Children: 1-800-THE-LOST</li>
                        <li>Crisis Text Line: Text HOME to 741741</li>
                        <li>Local Emergency Services: 911</li>
                    </ul>
                `,
                text: `CRITICAL SAFETY ALERT: Potential predatory behavior detected targeting {childName}. We have taken immediate protective action. Please call {supportPhone} immediately.`
            },
            push: {
                title: '🆘 CRITICAL SAFETY ALERT',
                body: 'Immediate action required for {childName}\'s safety',
                data: { type: 'critical-safety', severity: 'critical', requiresImmediate: true }
            }
        });

        this.alertTemplates.set('newConnection', {
            subject: 'New Connection: {childName} connected with a new friend',
            email: {
                html: `
                    <h2 style="color: #1976d2;">New Connection Notification</h2>
                    <p>Hi {parentName},</p>
                    <p>{childName} has made a new connection on Kids Connect!</p>
                    <p><strong>New connection details:</strong></p>
                    <ul>
                        <li>Name: {connectionName}</li>
                        <li>Age: {connectionAge}</li>
                        <li>School: {connectionSchool}</li>
                        <li>Connection type: {connectionType}</li>
                        <li>Time: {timestamp}</li>
                    </ul>
                    <p>This connection was approved through our safety verification process.</p>
                    <p><a href="{dashboardLink}">View connection details in your dashboard</a></p>
                `,
                text: `{childName} made a new connection with {connectionName} ({connectionAge}) from {connectionSchool}. View details in your parent dashboard.`
            },
            push: {
                title: 'New Connection',
                body: '{childName} connected with {connectionName}',
                data: { type: 'social', severity: 'info' }
            }
        });

        this.alertTemplates.set('excessiveUsage', {
            subject: 'Screen Time Alert: {childName} approaching daily limit',
            email: {
                html: `
                    <h2 style="color: #f57c00;">Screen Time Alert</h2>
                    <p>Hi {parentName},</p>
                    <p>{childName} has been using Kids Connect for {currentUsage} today and is approaching their daily limit of {dailyLimit}.</p>
                    <p><strong>Today's activity:</strong></p>
                    <ul>
                        <li>Learning time: {learningTime}</li>
                        <li>Social time: {socialTime}</li>
                        <li>Creative time: {creativeTime}</li>
                    </ul>
                    <p>Consider encouraging offline activities or family time.</p>
                    <p><a href="{dashboardLink}">Adjust time limits in settings</a></p>
                `,
                text: `{childName} has used {currentUsage} of their {dailyLimit} daily screen time limit. Consider encouraging offline activities.`
            },
            push: {
                title: 'Screen Time Alert',
                body: '{childName} approaching daily usage limit',
                data: { type: 'time-management', severity: 'medium' }
            }
        });
    }

    async sendUrgentAlert(alertData) {
        const alert = {
            id: this.generateAlertId(),
            type: alertData.type,
            severity: 'critical',
            childId: alertData.userId || alertData.childId,
            timestamp: new Date(),
            data: alertData,
            status: 'pending',
            attempts: [],
            acknowledgments: []
        };

        return await this.processAlert(alert);
    }

    async sendContentAlert(incident) {
        const alert = {
            id: this.generateAlertId(),
            type: 'inappropriateContent',
            severity: this.determineSeverity(incident),
            childId: incident.userId,
            timestamp: new Date(),
            data: incident,
            status: 'pending',
            attempts: [],
            acknowledgments: []
        };

        return await this.processAlert(alert);
    }

    async sendConnectionAlert(connection) {
        const alert = {
            id: this.generateAlertId(),
            type: 'newConnection',
            severity: 'info',
            childId: connection.participants[0], // Assuming first participant is the child
            timestamp: new Date(),
            data: connection,
            status: 'pending',
            attempts: [],
            acknowledgments: []
        };

        return await this.processAlert(alert);
    }

    async sendTimeViolationAlert(violation) {
        const alert = {
            id: this.generateAlertId(),
            type: 'timeViolation',
            severity: 'medium',
            childId: violation.userId,
            timestamp: new Date(),
            data: violation,
            status: 'pending',
            attempts: [],
            acknowledgments: []
        };

        return await this.processAlert(alert);
    }

    async sendContentViolationAlert(violation) {
        const alert = {
            id: this.generateAlertId(),
            type: 'inappropriateContent',
            severity: this.mapSeverityToAlertSeverity(violation.severity),
            childId: violation.userId,
            timestamp: new Date(),
            data: violation,
            status: 'pending',
            attempts: [],
            acknowledgments: []
        };

        return await this.processAlert(alert);
    }

    async processAlert(alert) {
        try {
            // Check rate limiting
            if (!this.checkRateLimit(alert)) {
                this.emit('alertRateLimited', alert);
                return { success: false, reason: 'rate-limited' };
            }

            // Get parent contacts
            const parents = await this.getParentContacts(alert.childId);
            if (!parents || parents.length === 0) {
                throw new Error('No parent contacts found');
            }

            // Add to alert queue
            this.alertQueue.push(alert);

            // Process immediately for critical alerts
            if (alert.severity === 'critical') {
                await this.deliverAlert(alert, parents);
            } else {
                // Queue for batch delivery based on severity
                setTimeout(() => this.deliverAlert(alert, parents), 
                    this.severityLevels[alert.severity].maxDelay * 1000);
            }

            // Store in history
            this.storeAlertHistory(alert);

            // Set up escalation if required
            if (this.severityLevels[alert.severity].escalationTime) {
                this.setupEscalation(alert, parents);
            }

            this.emit('alertProcessed', alert);

            return { success: true, alertId: alert.id };

        } catch (error) {
            this.emit('alertProcessingError', { alert, error: error.message });
            return { success: false, error: error.message };
        }
    }

    async deliverAlert(alert, parents) {
        const template = this.alertTemplates.get(alert.type);
        if (!template) {
            throw new Error(`No template found for alert type: ${alert.type}`);
        }

        const deliveryMethods = this.severityLevels[alert.severity].deliveryMethods;

        for (const parent of parents) {
            const preferences = await this.getParentPreferences(parent.id);
            const enabledMethods = deliveryMethods.filter(method => 
                preferences[method] !== false
            );

            for (const method of enabledMethods) {
                try {
                    await this.deliverByMethod(alert, parent, template, method);
                    
                    alert.attempts.push({
                        parentId: parent.id,
                        method,
                        status: 'delivered',
                        timestamp: new Date()
                    });

                } catch (error) {
                    alert.attempts.push({
                        parentId: parent.id,
                        method,
                        status: 'failed',
                        error: error.message,
                        timestamp: new Date()
                    });
                }
            }
        }

        // Update alert status
        const successfulDeliveries = alert.attempts.filter(a => a.status === 'delivered').length;
        if (successfulDeliveries > 0) {
            alert.status = 'delivered';
        } else {
            alert.status = 'failed';
            await this.handleDeliveryFailure(alert, parents);
        }
    }

    async deliverByMethod(alert, parent, template, method) {
        const context = await this.buildTemplateContext(alert, parent);

        switch (method) {
            case 'email':
                await this.sendEmail(parent.email, template, context);
                break;
            case 'sms':
                await this.sendSMS(parent.phone, template, context);
                break;
            case 'app-push':
                await this.sendPushNotification(parent.deviceToken, template, context);
                break;
            case 'phone-call':
                await this.makePhoneCall(parent.phone, template, context);
                break;
            default:
                throw new Error(`Unsupported delivery method: ${method}`);
        }
    }

    async sendEmail(email, template, context) {
        const subject = this.processTemplate(template.subject, context);
        const html = this.processTemplate(template.email.html, context);
        const text = this.processTemplate(template.email.text, context);

        const mailOptions = {
            from: process.env.FROM_EMAIL || 'safety@kidsconnect.edu',
            to: email,
            subject: subject,
            html: html,
            text: text,
            priority: context.severity === 'critical' ? 'high' : 'normal'
        };

        const result = await this.emailTransporter.sendMail(mailOptions);
        return result;
    }

    async sendSMS(phone, template, context) {
        if (!this.twilioClient) {
            throw new Error('SMS service not configured');
        }

        const message = this.processTemplate(template.sms, context);

        const result = await this.twilioClient.messages.create({
            body: message,
            to: phone,
            from: process.env.TWILIO_PHONE_NUMBER
        });

        return result;
    }

    async sendPushNotification(deviceToken, template, context) {
        if (!deviceToken) {
            throw new Error('No device token available');
        }

        const notification = {
            title: this.processTemplate(template.push.title, context),
            body: this.processTemplate(template.push.body, context),
            data: template.push.data
        };

        return await this.pushNotificationService.send(deviceToken, notification);
    }

    async makePhoneCall(phone, template, context) {
        const message = `This is an urgent safety alert from Kids Connect regarding ${context.childName}. Please check your email immediately for important safety information. If this is a life-threatening emergency, please call 911.`;
        
        return await this.phoneCallService.call(phone, message);
    }

    processTemplate(template, context) {
        return template.replace(/\{(\w+)\}/g, (match, key) => {
            return context[key] || match;
        });
    }

    async buildTemplateContext(alert, parent) {
        const child = await this.getChildInfo(alert.childId);
        
        return {
            alertId: alert.id,
            parentName: parent.name,
            childName: child.name,
            severity: alert.severity,
            timestamp: alert.timestamp.toLocaleString(),
            dashboardLink: `${process.env.PARENT_PORTAL_URL}/dashboard/${parent.id}/child/${alert.childId}`,
            supportPhone: process.env.SUPPORT_PHONE || '1-800-KIDSSAFE',
            ...alert.data // Merge in alert-specific data
        };
    }

    setupEscalation(alert, parents) {
        const escalationTime = this.severityLevels[alert.severity].escalationTime * 1000;
        
        setTimeout(async () => {
            // Check if alert has been acknowledged
            if (alert.acknowledgments.length === 0) {
                await this.escalateAlert(alert, parents);
            }
        }, escalationTime);
    }

    async escalateAlert(alert, parents) {
        // Escalation strategies
        const escalationStrategies = {
            critical: async () => {
                // Call all emergency contacts
                await this.callEmergencyContacts(alert.childId);
                // Notify school authorities
                await this.notifySchoolAuthorities(alert.childId, alert);
                // Consider contacting child protective services
                await this.considerCPSContact(alert);
            },
            high: async () => {
                // Try alternative communication methods
                await this.tryAlternativeMethods(alert, parents);
                // Notify secondary contacts
                await this.notifySecondaryContacts(alert.childId);
            },
            medium: async () => {
                // Send follow-up reminder
                await this.sendFollowUpReminder(alert, parents);
            }
        };

        const strategy = escalationStrategies[alert.severity];
        if (strategy) {
            await strategy();
            this.emit('alertEscalated', { alert, escalationType: alert.severity });
        }
    }

    checkRateLimit(alert) {
        const key = `${alert.childId}-${alert.severity}`;
        const now = new Date();
        const hour = new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours());
        const day = new Date(now.getFullYear(), now.getMonth(), now.getDate());

        if (!this.rateLimiting.has(key)) {
            this.rateLimiting.set(key, { hourly: new Map(), daily: new Map() });
        }

        const limits = this.rateLimiting.get(key);
        const hourlyCount = limits.hourly.get(hour.getTime()) || 0;
        const dailyCount = limits.daily.get(day.getTime()) || 0;

        const rateLimit = this.rateLimits[alert.severity];

        if (hourlyCount >= rateLimit.maxPerHour || dailyCount >= rateLimit.maxPerDay) {
            return false; // Rate limited
        }

        // Increment counts
        limits.hourly.set(hour.getTime(), hourlyCount + 1);
        limits.daily.set(day.getTime(), dailyCount + 1);

        return true;
    }

    async acknowledgeAlert(alertId, parentId, acknowledgmentData = {}) {
        const alert = this.findAlert(alertId);
        if (!alert) {
            throw new Error('Alert not found');
        }

        const acknowledgment = {
            parentId,
            timestamp: new Date(),
            method: acknowledgmentData.method || 'manual',
            response: acknowledgmentData.response || 'acknowledged',
            followUpPlanned: acknowledgmentData.followUpPlanned || false
        };

        alert.acknowledgments.push(acknowledgment);
        alert.status = 'acknowledged';

        this.emit('alertAcknowledged', { alert, acknowledgment });

        return {
            success: true,
            alertId,
            acknowledgmentTime: acknowledgment.timestamp
        };
    }

    // Helper methods
    determineSeverity(incident) {
        if (incident.severity === 'high' || incident.type === 'predatory') {
            return 'critical';
        } else if (incident.severity === 'medium') {
            return 'high';
        } else {
            return 'medium';
        }
    }

    mapSeverityToAlertSeverity(incidentSeverity) {
        const mapping = {
            'critical': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low'
        };
        return mapping[incidentSeverity] || 'medium';
    }

    generateAlertId() {
        return 'alert_' + crypto.randomBytes(8).toString('hex');
    }

    storeAlertHistory(alert) {
        const childHistory = this.alertHistory.get(alert.childId) || [];
        childHistory.push({
            id: alert.id,
            type: alert.type,
            severity: alert.severity,
            timestamp: alert.timestamp,
            status: alert.status
        });
        this.alertHistory.set(alert.childId, childHistory);
    }

    findAlert(alertId) {
        return this.alertQueue.find(alert => alert.id === alertId);
    }

    // Placeholder implementations for external integrations
    async getParentContacts(childId) {
        // Implementation to retrieve parent contact information
        return [
            {
                id: 'parent1',
                name: 'Parent Name',
                email: 'parent@example.com',
                phone: '+1234567890',
                deviceToken: 'device-token'
            }
        ];
    }

    async getChildInfo(childId) {
        // Implementation to retrieve child information
        return {
            id: childId,
            name: 'Child Name',
            age: 12
        };
    }

    async getParentPreferences(parentId) {
        // Implementation to retrieve parent notification preferences
        return {
            email: true,
            sms: true,
            'app-push': true,
            'phone-call': true
        };
    }

    async handleDeliveryFailure(alert, parents) {
        // Implementation for handling delivery failures
        this.emit('alertDeliveryFailed', { alert, parents });
    }

    async callEmergencyContacts(childId) {
        // Implementation for calling emergency contacts
        this.emit('emergencyContactsCalled', { childId });
    }

    async notifySchoolAuthorities(childId, alert) {
        // Implementation for notifying school authorities
        this.emit('schoolAuthoritiesNotified', { childId, alert });
    }

    async considerCPSContact(alert) {
        // Implementation for considering child protective services contact
        this.emit('cpsContactConsidered', { alert });
    }

    async tryAlternativeMethods(alert, parents) {
        // Implementation for trying alternative communication methods
        this.emit('alternativeMethodsTried', { alert, parents });
    }

    async notifySecondaryContacts(childId) {
        // Implementation for notifying secondary contacts
        this.emit('secondaryContactsNotified', { childId });
    }

    async sendFollowUpReminder(alert, parents) {
        // Implementation for sending follow-up reminders
        this.emit('followUpReminderSent', { alert, parents });
    }
}

module.exports = ParentAlertSystem;