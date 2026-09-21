const EventEmitter = require('events');
const crypto = require('crypto');

class ParentMonitoringSystem extends EventEmitter {
    constructor() {
        super();
        this.childActivities = new Map();
        this.parentDashboards = new Map();
        this.activityLogs = new Map();
        this.connectionMonitoring = new Map();
        this.contentLogs = new Map();
        this.alertThresholds = new Map();
        this.realTimeMonitoring = new Map();
        this.privacyExceptions = new Map();
        this.reportingSchedules = new Map();
        this.emergencyProtocols = new Map();
        this.initializeDefaultSettings();
    }

    initializeDefaultSettings() {
        this.defaultMonitoringSettings = {
            activityTracking: {
                loginTimes: true,
                sessionDuration: true,
                connectionsUsed: true,
                messagesExchanged: true,
                contentShared: true,
                programsParticipated: true,
                achievementsEarned: true,
                flaggedIncidents: true
            },
            contentMonitoring: {
                allMessages: true, // Except diary entries
                sharedFiles: true,
                videoCallSummaries: true,
                publicPosts: true,
                groupDiscussions: true,
                privateMessagesExceptions: ['diary'], // Only diary is private
                contentFlags: true,
                moderationActions: true
            },
            realTimeAlerts: {
                inappropriateContent: 'immediate',
                newConnections: 'immediate',
                excessiveUsage: '2-hours',
                suspiciousActivity: 'immediate',
                locationSharing: 'immediate',
                personalInfoShared: 'immediate',
                offPlatformCommunication: 'immediate'
            },
            reportingFrequency: {
                daily: ['summary', 'alerts'],
                weekly: ['detailed', 'trends', 'connections'],
                monthly: ['comprehensive', 'development', 'safety']
            },
            privacyControls: {
                childCanSeeMonitoring: true, // Transparency
                childCanRequestPrivacy: false, // Except for diary
                parentCanOverride: true,
                emergencyAccess: true,
                dataRetention: '365-days'
            }
        };

        this.alertSeverityLevels = {
            critical: {
                color: 'red',
                notification: ['email', 'sms', 'app-push'],
                escalation: 'immediate',
                actions: ['alert-parent', 'alert-school', 'log-incident', 'possible-suspension']
            },
            high: {
                color: 'orange',
                notification: ['email', 'app-push'],
                escalation: '15-minutes',
                actions: ['alert-parent', 'log-incident', 'review-required']
            },
            medium: {
                color: 'yellow',
                notification: ['app-push'],
                escalation: '1-hour',
                actions: ['log-incident', 'parent-notification']
            },
            low: {
                color: 'blue',
                notification: ['dashboard-update'],
                escalation: '24-hours',
                actions: ['log-activity', 'weekly-report']
            }
        };
    }

    async registerChildForMonitoring(childId, parentIds, monitoringPreferences = {}) {
        const monitoring = {
            childId,
            parentIds,
            settings: {
                ...this.defaultMonitoringSettings,
                ...monitoringPreferences
            },
            activeSince: new Date(),
            lastReportSent: null,
            totalActivities: 0,
            currentSession: null,
            dailyLimits: monitoringPreferences.dailyLimits || {
                sessionTime: 180, // 3 hours default
                connectionTime: 120, // 2 hours
                newConnections: 3,
                messagesPerDay: 50
            },
            exceptions: {
                diaryEntries: true, // Always private
                educationalContent: monitoringPreferences.educationalContentPrivate || false,
                teacherSupervised: monitoringPreferences.teacherSupervisedPrivate || false
            }
        };

        this.childActivities.set(childId, monitoring);

        // Create parent dashboards
        for (const parentId of parentIds) {
            await this.createParentDashboard(parentId, childId);
        }

        this.emit('childMonitoringRegistered', { childId, parentIds });

        return {
            childId,
            monitoringActive: true,
            dashboardUrls: parentIds.map(parentId => 
                `${process.env.PARENT_PORTAL_URL}/dashboard/${parentId}/child/${childId}`
            ),
            privacyExceptions: monitoring.exceptions
        };
    }

    async createParentDashboard(parentId, childId) {
        const dashboardId = this.generateSecureId();
        const dashboard = {
            id: dashboardId,
            parentId,
            childId,
            createdAt: new Date(),
            lastViewed: null,
            widgets: {
                activitySummary: { enabled: true, position: 1 },
                currentSession: { enabled: true, position: 2 },
                recentConnections: { enabled: true, position: 3 },
                safetyAlerts: { enabled: true, position: 4 },
                learningProgress: { enabled: true, position: 5 },
                timeUsage: { enabled: true, position: 6 },
                contentSummary: { enabled: true, position: 7 },
                weeklyTrends: { enabled: true, position: 8 }
            },
            notifications: {
                email: true,
                sms: true,
                push: true,
                frequency: 'real-time-alerts-only'
            },
            accessLevel: 'full', // full, limited, emergency-only
            customFilters: [],
            exportOptions: ['pdf', 'csv', 'json']
        };

        this.parentDashboards.set(`${parentId}-${childId}`, dashboard);
        return dashboard;
    }

    async logActivity(childId, activity) {
        const monitoring = this.childActivities.get(childId);
        if (!monitoring) {
            throw new Error('Child not registered for monitoring');
        }

        // Check if this activity should be logged (privacy exceptions)
        if (this.isPrivacyException(activity, monitoring.exceptions)) {
            this.logPrivateActivity(childId, activity);
            return;
        }

        const logEntry = {
            id: this.generateSecureId(),
            childId,
            timestamp: new Date(),
            activity: {
                type: activity.type,
                details: activity.details || {},
                duration: activity.duration || null,
                participants: activity.participants || [],
                location: activity.location || 'platform',
                contentType: activity.contentType || null,
                safetyRating: activity.safetyRating || 'safe'
            },
            session: monitoring.currentSession,
            flagged: false,
            parentNotified: false,
            alertLevel: this.determineAlertLevel(activity),
            metadata: {
                userAgent: activity.userAgent || null,
                ipAddress: activity.ipAddress || null,
                deviceInfo: activity.deviceInfo || null
            }
        };

        // Store activity log
        if (!this.activityLogs.has(childId)) {
            this.activityLogs.set(childId, []);
        }
        this.activityLogs.get(childId).push(logEntry);

        // Update monitoring statistics
        monitoring.totalActivities++;
        monitoring.lastActivity = new Date();

        // Check for alert conditions
        await this.checkAlertConditions(childId, logEntry);

        // Real-time updates to parent dashboards
        await this.updateParentDashboards(childId, logEntry);

        this.emit('activityLogged', { childId, activity: logEntry });

        return logEntry;
    }

    logPrivateActivity(childId, activity) {
        // For privacy exceptions (like diary), log minimal metadata only
        const privateLog = {
            childId,
            timestamp: new Date(),
            activityType: activity.type,
            duration: activity.duration || null,
            safetyFlags: activity.automaticSafetyFlags || [], // Only security flags
            session: this.childActivities.get(childId)?.currentSession
        };

        // Store in separate private log (only accessible in emergencies)
        if (!this.privacyExceptions.has(childId)) {
            this.privacyExceptions.set(childId, []);
        }
        this.privacyExceptions.get(childId).push(privateLog);

        // Note: Parents are NOT notified of private activities unless flagged for safety
        if (activity.automaticSafetyFlags && activity.automaticSafetyFlags.length > 0) {
            this.emit('safetyFlagInPrivateContent', {
                childId,
                flags: activity.automaticSafetyFlags,
                timestamp: new Date()
            });
        }
    }

    isPrivacyException(activity, exceptions) {
        // Check if activity qualifies for privacy exception
        if (activity.type === 'diary-entry' && exceptions.diaryEntries) {
            return true;
        }
        
        if (activity.educationalContext && exceptions.educationalContent) {
            return true;
        }
        
        if (activity.teacherSupervised && exceptions.teacherSupervised) {
            return true;
        }
        
        return false;
    }

    async logMessage(message) {
        // Skip if it's a diary entry (privacy exception)
        if (message.type === 'diary') {
            this.logPrivateActivity(message.senderId, {
                type: 'diary-entry',
                duration: null,
                automaticSafetyFlags: message.safetyFlags || []
            });
            return;
        }

        const activity = {
            type: 'message-sent',
            details: {
                recipientId: message.recipientId,
                messageLength: message.content.length,
                contentType: message.type || 'text',
                hasAttachments: message.attachments && message.attachments.length > 0,
                safetyFiltered: message.wasFiltered || false,
                educational: message.educational || false
            },
            participants: [message.senderId, message.recipientId],
            contentType: message.type,
            safetyRating: message.safetyRating || 'safe'
        };

        await this.logActivity(message.senderId, activity);

        // Also log as received message for recipient
        const recipientActivity = {
            type: 'message-received',
            details: {
                senderId: message.senderId,
                messageLength: message.content.length,
                contentType: message.type || 'text',
                hasAttachments: message.attachments && message.attachments.length > 0
            },
            participants: [message.senderId, message.recipientId],
            contentType: message.type,
            safetyRating: message.safetyRating || 'safe'
        };

        await this.logActivity(message.recipientId, recipientActivity);
    }

    async startSessionMonitoring(childId, sessionInfo) {
        const monitoring = this.childActivities.get(childId);
        if (!monitoring) {
            throw new Error('Child not registered for monitoring');
        }

        const session = {
            id: this.generateSecureId(),
            childId,
            startTime: new Date(),
            endTime: null,
            duration: null,
            activities: [],
            connections: [],
            contentFlags: [],
            totalMessages: 0,
            safetyScore: 100,
            deviceInfo: sessionInfo.deviceInfo || {},
            ipAddress: sessionInfo.ipAddress,
            location: sessionInfo.location || 'unknown'
        };

        monitoring.currentSession = session;
        
        // Set up real-time monitoring
        this.realTimeMonitoring.set(childId, {
            sessionId: session.id,
            startTime: session.startTime,
            lastPing: new Date(),
            alertsTriggered: 0,
            warningsSent: 0
        });

        await this.logActivity(childId, {
            type: 'session-started',
            details: {
                deviceType: sessionInfo.deviceInfo?.type || 'unknown',
                location: sessionInfo.location
            }
        });

        this.emit('sessionStarted', { childId, session });

        return session;
    }

    async endSessionMonitoring(childId) {
        const monitoring = this.childActivities.get(childId);
        if (!monitoring || !monitoring.currentSession) {
            return;
        }

        const session = monitoring.currentSession;
        session.endTime = new Date();
        session.duration = session.endTime - session.startTime;

        // Calculate session statistics
        const sessionStats = {
            duration: session.duration,
            activitiesCount: session.activities.length,
            connectionsUsed: session.connections.length,
            messagesExchanged: session.totalMessages,
            safetyIncidents: session.contentFlags.length,
            finalSafetyScore: session.safetyScore
        };

        await this.logActivity(childId, {
            type: 'session-ended',
            details: sessionStats,
            duration: session.duration
        });

        // Clear current session
        monitoring.currentSession = null;
        this.realTimeMonitoring.delete(childId);

        // Generate session summary for parents
        await this.generateSessionSummary(childId, session);

        this.emit('sessionEnded', { childId, session, stats: sessionStats });

        return sessionStats;
    }

    async addSocketMonitoring(socket) {
        const childId = socket.userId;
        const monitoring = this.childActivities.get(childId);
        
        if (!monitoring) {
            return;
        }

        // Start session if not already started
        if (!monitoring.currentSession) {
            await this.startSessionMonitoring(childId, {
                deviceInfo: { type: 'web', userAgent: socket.handshake.headers['user-agent'] },
                ipAddress: socket.handshake.address,
                location: 'web-platform'
            });
        }

        // Set up socket-specific monitoring
        socket.on('disconnect', async () => {
            await this.endSessionMonitoring(childId);
        });

        // Monitor socket events
        const originalEmit = socket.emit;
        socket.emit = function(event, ...args) {
            if (monitoring.currentSession) {
                monitoring.currentSession.activities.push({
                    type: 'socket-event',
                    event: event,
                    timestamp: new Date(),
                    data: args
                });
            }
            return originalEmit.apply(socket, arguments);
        };
    }

    removeSocketMonitoring(socket) {
        // Clean up monitoring when socket disconnects
        const childId = socket.userId;
        if (childId) {
            this.endSessionMonitoring(childId);
        }
    }

    async checkAlertConditions(childId, logEntry) {
        const monitoring = this.childActivities.get(childId);
        const alerts = [];

        // Check time-based alerts
        const timeAlerts = await this.checkTimeBasedAlerts(childId, monitoring);
        alerts.push(...timeAlerts);

        // Check content-based alerts
        const contentAlerts = await this.checkContentBasedAlerts(logEntry);
        alerts.push(...contentAlerts);

        // Check behavioral alerts
        const behaviorAlerts = await this.checkBehavioralAlerts(childId, logEntry);
        alerts.push(...behaviorAlerts);

        // Check safety alerts
        const safetyAlerts = await this.checkSafetyAlerts(logEntry);
        alerts.push(...safetyAlerts);

        // Process alerts
        for (const alert of alerts) {
            await this.processAlert(childId, alert);
        }

        return alerts;
    }

    async checkTimeBasedAlerts(childId, monitoring) {
        const alerts = [];
        const now = new Date();

        if (!monitoring.currentSession) return alerts;

        const sessionDuration = now - monitoring.currentSession.startTime;
        const dailyLimits = monitoring.dailyLimits;

        // Session time limit
        if (sessionDuration > dailyLimits.sessionTime * 60 * 1000) {
            alerts.push({
                type: 'time-limit-exceeded',
                severity: 'high',
                message: 'Session time limit exceeded',
                data: { 
                    duration: sessionDuration, 
                    limit: dailyLimits.sessionTime * 60 * 1000 
                }
            });
        }

        // Daily connection limit
        const todayConnections = await this.getTodayConnectionCount(childId);
        if (todayConnections >= dailyLimits.newConnections) {
            alerts.push({
                type: 'daily-connection-limit',
                severity: 'medium',
                message: 'Daily connection limit reached',
                data: { 
                    connections: todayConnections, 
                    limit: dailyLimits.newConnections 
                }
            });
        }

        return alerts;
    }

    async checkContentBasedAlerts(logEntry) {
        const alerts = [];

        // Check for flagged content
        if (logEntry.activity.safetyRating === 'flagged') {
            alerts.push({
                type: 'content-flagged',
                severity: 'high',
                message: 'Inappropriate content detected',
                data: logEntry.activity.details
            });
        }

        // Check for personal information sharing
        if (logEntry.activity.type === 'personal-info-shared') {
            alerts.push({
                type: 'personal-info-sharing',
                severity: 'critical',
                message: 'Personal information may have been shared',
                data: logEntry.activity.details
            });
        }

        return alerts;
    }

    async checkBehavioralAlerts(childId, logEntry) {
        const alerts = [];
        const recentActivities = await this.getRecentActivities(childId, '1-hour');

        // Check for excessive messaging
        const messageCount = recentActivities.filter(a => 
            a.activity.type === 'message-sent'
        ).length;

        if (messageCount > 20) { // 20 messages in 1 hour
            alerts.push({
                type: 'excessive-messaging',
                severity: 'medium',
                message: 'High message frequency detected',
                data: { messageCount, timeframe: '1-hour' }
            });
        }

        // Check for pattern changes
        const patterns = await this.analyzeActivityPatterns(childId);
        if (patterns.significantChange) {
            alerts.push({
                type: 'behavior-pattern-change',
                severity: 'low',
                message: 'Unusual activity pattern detected',
                data: patterns
            });
        }

        return alerts;
    }

    async checkSafetyAlerts(logEntry) {
        const alerts = [];

        // Check for off-platform communication attempts
        if (logEntry.activity.type === 'off-platform-request') {
            alerts.push({
                type: 'off-platform-communication',
                severity: 'critical',
                message: 'Attempt to move communication off-platform',
                data: logEntry.activity.details
            });
        }

        // Check for meeting requests
        if (logEntry.activity.type === 'meeting-request') {
            alerts.push({
                type: 'meeting-request',
                severity: 'critical',
                message: 'In-person meeting requested',
                data: logEntry.activity.details
            });
        }

        return alerts;
    }

    async processAlert(childId, alert) {
        const monitoring = this.childActivities.get(childId);
        const severityConfig = this.alertSeverityLevels[alert.severity];

        // Create alert record
        const alertRecord = {
            id: this.generateSecureId(),
            childId,
            timestamp: new Date(),
            type: alert.type,
            severity: alert.severity,
            message: alert.message,
            data: alert.data,
            acknowledged: false,
            resolved: false,
            actions: []
        };

        // Store alert
        if (!this.alertThresholds.has(childId)) {
            this.alertThresholds.set(childId, []);
        }
        this.alertThresholds.get(childId).push(alertRecord);

        // Execute configured actions
        for (const action of severityConfig.actions) {
            await this.executeAlertAction(childId, alertRecord, action);
        }

        // Send notifications to parents
        await this.notifyParentsOfAlert(childId, alertRecord, severityConfig);

        this.emit('alertProcessed', { childId, alert: alertRecord });

        return alertRecord;
    }

    async executeAlertAction(childId, alert, action) {
        switch (action) {
            case 'alert-parent':
                await this.sendImmediateParentAlert(childId, alert);
                break;
            case 'alert-school':
                await this.alertSchoolCoordinator(childId, alert);
                break;
            case 'log-incident':
                await this.logSecurityIncident(childId, alert);
                break;
            case 'possible-suspension':
                await this.initiateAccountReview(childId, alert);
                break;
            case 'review-required':
                await this.flagForManualReview(childId, alert);
                break;
        }

        alert.actions.push({
            action,
            executedAt: new Date(),
            status: 'completed'
        });
    }

    async updateParentDashboards(childId, activity) {
        const monitoring = this.childActivities.get(childId);
        
        for (const parentId of monitoring.parentIds) {
            const dashboardKey = `${parentId}-${childId}`;
            const dashboard = this.parentDashboards.get(dashboardKey);
            
            if (dashboard) {
                // Update real-time widgets
                await this.updateDashboardWidgets(dashboard, activity);
                
                // Send real-time update if parent is viewing
                this.emit('dashboardUpdate', {
                    parentId,
                    childId,
                    update: {
                        type: 'activity',
                        data: this.sanitizeActivityForParent(activity)
                    }
                });
            }
        }
    }

    async generateHourlyReports() {
        const reports = [];
        
        for (const [childId, monitoring] of this.childActivities.entries()) {
            const hourlyReport = {
                childId,
                reportType: 'hourly',
                timestamp: new Date(),
                period: {
                    start: new Date(Date.now() - 60 * 60 * 1000),
                    end: new Date()
                },
                summary: await this.generateHourlyActivitySummary(childId),
                alerts: await this.getRecentAlerts(childId, '1-hour'),
                safetyStatus: await this.getCurrentSafetyStatus(childId)
            };

            reports.push(hourlyReport);

            // Send to parents if configured
            if (monitoring.settings.reportingFrequency.hourly) {
                await this.sendReportToParents(childId, hourlyReport);
            }
        }

        this.emit('hourlyReportsGenerated', { count: reports.length, reports });
        return reports;
    }

    async generateDailySummary(childId) {
        const monitoring = this.childActivities.get(childId);
        if (!monitoring) return null;

        const today = new Date();
        const todayActivities = await this.getTodayActivities(childId);

        const summary = {
            childId,
            date: today.toDateString(),
            generatedAt: new Date(),
            overview: {
                totalActivities: todayActivities.length,
                sessionCount: todayActivities.filter(a => a.activity.type === 'session-started').length,
                totalTimeSpent: await this.calculateTotalTimeSpent(todayActivities),
                connectionsUsed: await this.getUniqueConnections(todayActivities),
                messagesExchanged: todayActivities.filter(a => 
                    a.activity.type === 'message-sent' || a.activity.type === 'message-received'
                ).length
            },
            learning: {
                programsParticipated: await this.getParticipatedPrograms(todayActivities),
                achievementsEarned: await this.getTodayAchievements(childId),
                skillsPracticed: await this.getSkillsPracticed(todayActivities),
                culturalExchanges: await this.getCulturalExchanges(todayActivities)
            },
            safety: {
                alertsTriggered: await this.getTodayAlerts(childId),
                contentFlags: await this.getTodayContentFlags(childId),
                overallSafetyScore: await this.calculateDailySafetyScore(childId),
                parentInterventions: await this.getParentInterventions(childId)
            },
            social: {
                newConnections: await this.getTodayNewConnections(childId),
                activeConnections: await this.getTodayActiveConnections(childId),
                helpProvided: await this.getHelpProvidedToOthers(childId),
                collaborativeActivities: await this.getCollaborativeActivities(todayActivities)
            },
            insights: await this.generateDailyInsights(childId, todayActivities),
            recommendations: await this.generateDailyRecommendations(childId, todayActivities)
        };

        // Send to parents
        for (const parentId of monitoring.parentIds) {
            await this.sendDailySummaryToParent(parentId, summary);
        }

        this.emit('dailySummaryGenerated', { childId, summary });

        return summary;
    }

    async getParentDashboard(parentId, childId) {
        const dashboardKey = `${parentId}-${childId}`;
        const dashboard = this.parentDashboards.get(dashboardKey);
        
        if (!dashboard) {
            throw new Error('Dashboard not found');
        }

        // Get current activity data
        const currentData = {
            currentSession: await this.getCurrentSessionInfo(childId),
            todayActivities: await this.getTodayActivitySummary(childId),
            recentAlerts: await this.getRecentAlerts(childId, '24-hours'),
            safetyStatus: await this.getCurrentSafetyStatus(childId),
            connections: await this.getCurrentConnections(childId),
            learningProgress: await this.getLearningProgress(childId),
            weeklyTrends: await this.getWeeklyTrends(childId)
        };

        // Update last viewed
        dashboard.lastViewed = new Date();

        return {
            dashboard,
            data: currentData,
            lastUpdate: new Date()
        };
    }

    sanitizeActivityForParent(activity) {
        // Remove sensitive details but keep important safety information
        return {
            id: activity.id,
            timestamp: activity.timestamp,
            type: activity.activity.type,
            duration: activity.activity.duration,
            safetyRating: activity.activity.safetyRating,
            alertLevel: activity.alertLevel,
            participantsCount: activity.activity.participants?.length || 0,
            flagged: activity.flagged
        };
    }

    generateSecureId() {
        return crypto.randomBytes(16).toString('hex');
    }

    determineAlertLevel(activity) {
        if (activity.safetyRating === 'critical') return 'critical';
        if (activity.safetyRating === 'flagged') return 'high';
        if (activity.type === 'new-connection') return 'medium';
        if (activity.type === 'session-started') return 'low';
        return 'low';
    }

    // Additional helper methods would be implemented here...
    async getTodayConnectionCount(childId) { 
        // Implementation for getting today's connection count
        return 0; 
    }

    async getRecentActivities(childId, timeframe) { 
        // Implementation for getting recent activities
        return []; 
    }

    async analyzeActivityPatterns(childId) { 
        // Implementation for pattern analysis
        return { significantChange: false }; 
    }

    async sendImmediateParentAlert(childId, alert) { 
        // Implementation for sending immediate alerts
        this.emit('immediateParentAlert', { childId, alert });
    }

    async alertSchoolCoordinator(childId, alert) { 
        // Implementation for alerting school
        this.emit('schoolAlert', { childId, alert });
    }

    async logSecurityIncident(childId, alert) { 
        // Implementation for security incident logging
        this.emit('securityIncident', { childId, alert });
    }

    async initiateAccountReview(childId, alert) { 
        // Implementation for account review initiation
        this.emit('accountReview', { childId, alert });
    }

    async flagForManualReview(childId, alert) { 
        // Implementation for manual review flagging
        this.emit('manualReview', { childId, alert });
    }
}

module.exports = ParentMonitoringSystem;