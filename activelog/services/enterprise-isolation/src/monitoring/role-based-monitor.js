const winston = require('winston');
const EventEmitter = require('events');

class RoleBasedMonitor extends EventEmitter {
    constructor(options = {}) {
        super();

        this.config = {
            monitoringLevels: {
                'guest': {
                    allowedMetrics: ['system_status', 'public_stats'],
                    refreshInterval: 30000, // 30 seconds
                    dataRetention: 3600000, // 1 hour
                    alertThresholds: {}
                },
                'user': {
                    allowedMetrics: ['system_status', 'public_stats', 'user_activity', 'performance'],
                    refreshInterval: 15000, // 15 seconds
                    dataRetention: 86400000, // 24 hours
                    alertThresholds: {
                        'response_time': 5000,
                        'error_rate': 5
                    }
                },
                'operator': {
                    allowedMetrics: ['system_status', 'public_stats', 'user_activity', 'performance', 'security_events', 'resource_usage'],
                    refreshInterval: 5000, // 5 seconds
                    dataRetention: 604800000, // 7 days
                    alertThresholds: {
                        'response_time': 3000,
                        'error_rate': 2,
                        'cpu_usage': 80,
                        'memory_usage': 85,
                        'disk_usage': 90
                    }
                },
                'admin': {
                    allowedMetrics: ['*'], // All metrics
                    refreshInterval: 1000, // 1 second
                    dataRetention: 2592000000, // 30 days
                    alertThresholds: {
                        'response_time': 2000,
                        'error_rate': 1,
                        'cpu_usage': 70,
                        'memory_usage': 80,
                        'disk_usage': 85,
                        'security_violations': 1,
                        'failed_logins': 3
                    }
                },
                'security_officer': {
                    allowedMetrics: ['security_events', 'audit_logs', 'compliance_status', 'threat_intelligence', 'user_activity'],
                    refreshInterval: 2000, // 2 seconds
                    dataRetention: 7776000000, // 90 days
                    alertThresholds: {
                        'security_violations': 1,
                        'failed_logins': 2,
                        'suspicious_activity': 1,
                        'privilege_escalations': 1,
                        'data_exfiltration_risk': 1
                    }
                }
            },
            metricCollectors: new Map(),
            activeMonitors: new Map(),
            alertChannels: options.alertChannels || ['log', 'email'],
            realTimeMetrics: new Map()
        };

        this.logger = winston.createLogger({
            level: 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json()
            ),
            defaultMeta: { service: 'role-based-monitor' },
            transports: [
                new winston.transports.File({
                    filename: 'logs/monitoring-error.log',
                    level: 'error'
                }),
                new winston.transports.File({
                    filename: 'logs/monitoring.log'
                })
            ]
        });

        this.initializeMetricCollectors();
        this.startMonitoring();
    }

    initializeMetricCollectors() {
        // System status collector
        this.config.metricCollectors.set('system_status', {
            collect: async () => {
                const os = require('os');
                return {
                    uptime: process.uptime(),
                    load: os.loadavg(),
                    platform: os.platform(),
                    nodeVersion: process.version,
                    timestamp: Date.now()
                };
            },
            category: 'system'
        });

        // Performance metrics collector
        this.config.metricCollectors.set('performance', {
            collect: async () => {
                const used = process.memoryUsage();
                return {
                    memory: {
                        rss: used.rss,
                        heapTotal: used.heapTotal,
                        heapUsed: used.heapUsed,
                        external: used.external
                    },
                    cpu: process.cpuUsage(),
                    eventLoop: this.getEventLoopDelay(),
                    timestamp: Date.now()
                };
            },
            category: 'performance'
        });

        // Security events collector
        this.config.metricCollectors.set('security_events', {
            collect: async () => {
                return {
                    authenticationEvents: this.getAuthenticationMetrics(),
                    securityViolations: this.getSecurityViolations(),
                    threatLevel: this.getCurrentThreatLevel(),
                    activeThreats: this.getActiveThreats(),
                    timestamp: Date.now()
                };
            },
            category: 'security'
        });

        // User activity collector
        this.config.metricCollectors.set('user_activity', {
            collect: async () => {
                return {
                    activeUsers: this.getActiveUserCount(),
                    sessionMetrics: this.getSessionMetrics(),
                    activityByRole: this.getActivityByRole(),
                    recentActions: this.getRecentUserActions(),
                    timestamp: Date.now()
                };
            },
            category: 'activity'
        });

        // Resource usage collector
        this.config.metricCollectors.set('resource_usage', {
            collect: async () => {
                const os = require('os');
                return {
                    cpu: {
                        usage: this.getCPUUsage(),
                        cores: os.cpus().length
                    },
                    memory: {
                        total: os.totalmem(),
                        free: os.freemem(),
                        usage: ((os.totalmem() - os.freemem()) / os.totalmem()) * 100
                    },
                    disk: await this.getDiskUsage(),
                    network: await this.getNetworkStats(),
                    timestamp: Date.now()
                };
            },
            category: 'resources'
        });

        // Compliance status collector
        this.config.metricCollectors.set('compliance_status', {
            collect: async () => {
                return {
                    gdprCompliance: await this.checkGDPRCompliance(),
                    hipaaCompliance: await this.checkHIPAACompliance(),
                    soxCompliance: await this.checkSOXCompliance(),
                    dataRetentionCompliance: await this.checkDataRetention(),
                    auditTrailIntegrity: await this.checkAuditTrailIntegrity(),
                    timestamp: Date.now()
                };
            },
            category: 'compliance'
        });

        // Public stats collector
        this.config.metricCollectors.set('public_stats', {
            collect: async () => {
                return {
                    totalRequests: this.getTotalRequests(),
                    averageResponseTime: this.getAverageResponseTime(),
                    systemHealth: this.getSystemHealthScore(),
                    serviceAvailability: this.getServiceAvailability(),
                    timestamp: Date.now()
                };
            },
            category: 'public'
        });
    }

    async startUserMonitoring(userId, userRole, sessionId) {
        const roleConfig = this.config.monitoringLevels[userRole];
        if (!roleConfig) {
            this.logger.warn('Unknown user role for monitoring', { userId, userRole });
            return null;
        }

        const monitorId = `${userId}-${sessionId}`;
        const monitor = {
            userId,
            userRole,
            sessionId,
            startTime: Date.now(),
            config: roleConfig,
            lastUpdate: Date.now(),
            metrics: new Map(),
            alerts: []
        };

        this.config.activeMonitors.set(monitorId, monitor);

        // Start collecting metrics for this user's role
        const interval = setInterval(() => {
            this.collectMetricsForMonitor(monitorId);
        }, roleConfig.refreshInterval);

        monitor.interval = interval;

        this.logger.info('Started role-based monitoring', {
            userId,
            userRole,
            sessionId,
            refreshInterval: roleConfig.refreshInterval
        });

        return monitorId;
    }

    async collectMetricsForMonitor(monitorId) {
        const monitor = this.config.activeMonitors.get(monitorId);
        if (!monitor) return;

        const { config, userRole } = monitor;
        const currentTime = Date.now();

        try {
            for (const [metricName, collector] of this.config.metricCollectors) {
                // Check if user role has permission for this metric
                if (!this.hasMetricPermission(userRole, metricName)) {
                    continue;
                }

                const metricData = await collector.collect();
                
                // Store metric data with retention policy
                if (!monitor.metrics.has(metricName)) {
                    monitor.metrics.set(metricName, []);
                }

                const metricHistory = monitor.metrics.get(metricName);
                metricHistory.push(metricData);

                // Apply data retention policy
                const retentionCutoff = currentTime - config.dataRetention;
                monitor.metrics.set(
                    metricName,
                    metricHistory.filter(data => data.timestamp > retentionCutoff)
                );

                // Check alert thresholds
                await this.checkAlertThresholds(monitor, metricName, metricData);

                // Update real-time metrics for this metric type
                this.updateRealTimeMetric(metricName, metricData);
            }

            monitor.lastUpdate = currentTime;

        } catch (error) {
            this.logger.error('Error collecting metrics for monitor', {
                monitorId,
                error: error.message
            });
        }
    }

    hasMetricPermission(userRole, metricName) {
        const roleConfig = this.config.monitoringLevels[userRole];
        if (!roleConfig) return false;

        const allowedMetrics = roleConfig.allowedMetrics;
        return allowedMetrics.includes('*') || allowedMetrics.includes(metricName);
    }

    async checkAlertThresholds(monitor, metricName, metricData) {
        const thresholds = monitor.config.alertThresholds;
        if (!thresholds) return;

        const alerts = [];

        // Check various threshold types
        switch (metricName) {
            case 'performance':
                if (thresholds.response_time && metricData.responseTime > thresholds.response_time) {
                    alerts.push({
                        type: 'PERFORMANCE_DEGRADATION',
                        severity: 'WARNING',
                        message: `Response time ${metricData.responseTime}ms exceeds threshold ${thresholds.response_time}ms`,
                        value: metricData.responseTime,
                        threshold: thresholds.response_time
                    });
                }
                break;

            case 'resource_usage':
                if (thresholds.cpu_usage && metricData.cpu.usage > thresholds.cpu_usage) {
                    alerts.push({
                        type: 'HIGH_CPU_USAGE',
                        severity: 'WARNING',
                        message: `CPU usage ${metricData.cpu.usage.toFixed(1)}% exceeds threshold ${thresholds.cpu_usage}%`,
                        value: metricData.cpu.usage,
                        threshold: thresholds.cpu_usage
                    });
                }

                if (thresholds.memory_usage && metricData.memory.usage > thresholds.memory_usage) {
                    alerts.push({
                        type: 'HIGH_MEMORY_USAGE',
                        severity: 'WARNING',
                        message: `Memory usage ${metricData.memory.usage.toFixed(1)}% exceeds threshold ${thresholds.memory_usage}%`,
                        value: metricData.memory.usage,
                        threshold: thresholds.memory_usage
                    });
                }
                break;

            case 'security_events':
                if (thresholds.security_violations && metricData.securityViolations > thresholds.security_violations) {
                    alerts.push({
                        type: 'SECURITY_VIOLATIONS',
                        severity: 'CRITICAL',
                        message: `${metricData.securityViolations} security violations detected`,
                        value: metricData.securityViolations,
                        threshold: thresholds.security_violations
                    });
                }

                if (thresholds.failed_logins && metricData.authenticationEvents.failed > thresholds.failed_logins) {
                    alerts.push({
                        type: 'FAILED_LOGIN_ATTEMPTS',
                        severity: 'HIGH',
                        message: `${metricData.authenticationEvents.failed} failed login attempts`,
                        value: metricData.authenticationEvents.failed,
                        threshold: thresholds.failed_logins
                    });
                }
                break;
        }

        // Process alerts
        for (const alert of alerts) {
            await this.processAlert(monitor, alert);
        }
    }

    async processAlert(monitor, alert) {
        const alertData = {
            ...alert,
            monitorId: `${monitor.userId}-${monitor.sessionId}`,
            userId: monitor.userId,
            userRole: monitor.userRole,
            timestamp: Date.now()
        };

        monitor.alerts.push(alertData);

        // Emit alert event
        this.emit('alert', alertData);

        // Send notifications based on configured channels
        for (const channel of this.config.alertChannels) {
            await this.sendAlert(channel, alertData);
        }

        this.logger.warn('Alert triggered', alertData);
    }

    async sendAlert(channel, alert) {
        switch (channel) {
            case 'log':
                this.logger.error(`ALERT: ${alert.type}`, {
                    severity: alert.severity,
                    message: alert.message,
                    userId: alert.userId,
                    userRole: alert.userRole
                });
                break;

            case 'email':
                // Email notification would be implemented here
                // For now, just log the intent
                this.logger.info('Email alert would be sent', {
                    type: alert.type,
                    severity: alert.severity,
                    userId: alert.userId
                });
                break;

            case 'slack':
                // Slack notification would be implemented here
                this.logger.info('Slack alert would be sent', {
                    type: alert.type,
                    severity: alert.severity
                });
                break;
        }
    }

    async getMonitoringData(monitorId, metricNames = null, timeRange = null) {
        const monitor = this.config.activeMonitors.get(monitorId);
        if (!monitor) {
            throw new Error('Monitor not found');
        }

        const result = {
            monitorId,
            userId: monitor.userId,
            userRole: monitor.userRole,
            lastUpdate: monitor.lastUpdate,
            metrics: {},
            alerts: monitor.alerts
        };

        // Filter metrics based on requested names and user permissions
        const requestedMetrics = metricNames || Array.from(monitor.metrics.keys());
        
        for (const metricName of requestedMetrics) {
            if (!this.hasMetricPermission(monitor.userRole, metricName)) {
                continue;
            }

            if (monitor.metrics.has(metricName)) {
                let metricData = monitor.metrics.get(metricName);

                // Apply time range filter if specified
                if (timeRange) {
                    const { start, end } = timeRange;
                    metricData = metricData.filter(data => 
                        data.timestamp >= start && data.timestamp <= end
                    );
                }

                result.metrics[metricName] = metricData;
            }
        }

        return result;
    }

    async getRealTimeMetrics(userRole, metricNames = null) {
        const allowedMetrics = metricNames || 
            this.config.monitoringLevels[userRole]?.allowedMetrics || [];

        const result = {};

        for (const metricName of allowedMetrics) {
            if (metricName === '*') {
                // Return all real-time metrics
                for (const [name, data] of this.config.realTimeMetrics) {
                    result[name] = data;
                }
                break;
            } else if (this.hasMetricPermission(userRole, metricName)) {
                const metricData = this.config.realTimeMetrics.get(metricName);
                if (metricData) {
                    result[metricName] = metricData;
                }
            }
        }

        return result;
    }

    stopUserMonitoring(monitorId) {
        const monitor = this.config.activeMonitors.get(monitorId);
        if (monitor) {
            clearInterval(monitor.interval);
            this.config.activeMonitors.delete(monitorId);

            this.logger.info('Stopped role-based monitoring', {
                monitorId,
                userId: monitor.userId,
                userRole: monitor.userRole,
                duration: Date.now() - monitor.startTime
            });
        }
    }

    updateRealTimeMetric(metricName, data) {
        this.config.realTimeMetrics.set(metricName, {
            ...data,
            lastUpdated: Date.now()
        });
    }

    startMonitoring() {
        // Start background metric collection
        setInterval(() => {
            this.collectGlobalMetrics();
        }, 5000); // Collect global metrics every 5 seconds

        this.logger.info('Role-based monitoring system started');
    }

    async collectGlobalMetrics() {
        // Collect system-wide metrics that don't require user context
        try {
            const systemStatus = await this.config.metricCollectors.get('system_status').collect();
            this.updateRealTimeMetric('system_status', systemStatus);

            const performance = await this.config.metricCollectors.get('performance').collect();
            this.updateRealTimeMetric('performance', performance);

            const resourceUsage = await this.config.metricCollectors.get('resource_usage').collect();
            this.updateRealTimeMetric('resource_usage', resourceUsage);

        } catch (error) {
            this.logger.error('Error collecting global metrics', { error: error.message });
        }
    }

    // Helper methods for metric collection
    getEventLoopDelay() {
        // Simplified event loop delay measurement
        return Math.random() * 10; // Mock data
    }

    getAuthenticationMetrics() {
        return {
            total: 1250,
            successful: 1200,
            failed: 50,
            mfaUsed: 1180
        };
    }

    getSecurityViolations() {
        return Math.floor(Math.random() * 5);
    }

    getCurrentThreatLevel() {
        const levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
        return levels[Math.floor(Math.random() * levels.length)];
    }

    getActiveThreats() {
        return Math.floor(Math.random() * 10);
    }

    getActiveUserCount() {
        return Math.floor(Math.random() * 100) + 50;
    }

    getSessionMetrics() {
        return {
            active: Math.floor(Math.random() * 150) + 100,
            expired: Math.floor(Math.random() * 20),
            averageDuration: Math.floor(Math.random() * 7200) + 1800
        };
    }

    getActivityByRole() {
        return {
            admin: 5,
            operator: 15,
            user: 80,
            guest: 25
        };
    }

    getRecentUserActions() {
        return [
            { action: 'login', timestamp: Date.now() - 300000, userId: 'user123' },
            { action: 'file_access', timestamp: Date.now() - 180000, userId: 'user456' },
            { action: 'config_change', timestamp: Date.now() - 120000, userId: 'admin789' }
        ];
    }

    getCPUUsage() {
        return Math.random() * 100;
    }

    async getDiskUsage() {
        return {
            total: 1000000000000, // 1TB
            used: Math.floor(Math.random() * 500000000000), // Random usage up to 500GB
            available: 500000000000
        };
    }

    async getNetworkStats() {
        return {
            bytesIn: Math.floor(Math.random() * 1000000),
            bytesOut: Math.floor(Math.random() * 1000000),
            packetsIn: Math.floor(Math.random() * 10000),
            packetsOut: Math.floor(Math.random() * 10000)
        };
    }

    async checkGDPRCompliance() {
        return { compliant: true, lastCheck: Date.now() };
    }

    async checkHIPAACompliance() {
        return { compliant: true, lastCheck: Date.now() };
    }

    async checkSOXCompliance() {
        return { compliant: true, lastCheck: Date.now() };
    }

    async checkDataRetention() {
        return { compliant: true, lastCheck: Date.now() };
    }

    async checkAuditTrailIntegrity() {
        return { intact: true, lastCheck: Date.now() };
    }

    getTotalRequests() {
        return Math.floor(Math.random() * 10000) + 50000;
    }

    getAverageResponseTime() {
        return Math.floor(Math.random() * 500) + 100;
    }

    getSystemHealthScore() {
        return Math.floor(Math.random() * 20) + 80; // 80-100
    }

    getServiceAvailability() {
        return 99.95 + (Math.random() * 0.05);
    }

    getMonitoringStats() {
        return {
            activeMonitors: this.config.activeMonitors.size,
            totalMetrics: this.config.metricCollectors.size,
            realTimeMetrics: this.config.realTimeMetrics.size,
            supportedRoles: Object.keys(this.config.monitoringLevels)
        };
    }
}

module.exports = RoleBasedMonitor;