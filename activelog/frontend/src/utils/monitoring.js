/**
 * Comprehensive Error Logging and Monitoring System
 */

import { ServiceStatusManager } from './serviceStatus.js';
import { EventEmitter } from './events.js';

class MonitoringManagerClass extends EventEmitter {
    constructor() {
        super();
        this.isInitialized = false;
        this.sessionId = this.generateSessionId();
        this.userId = null;
        this.logs = [];
        this.metrics = {
            pageViews: 0,
            errors: 0,
            apiCalls: 0,
            loadTime: 0,
            interactions: 0
        };
        this.performanceObserver = null;
        this.config = {
            maxLogs: 1000,
            batchSize: 10,
            flushInterval: 30000, // 30 seconds
            enablePerformanceMonitoring: true,
            enableErrorReporting: true,
            enableUserInteractionTracking: true,
            logLevel: 'info' // debug, info, warn, error
        };
    }

    init(options = {}) {
        if (this.isInitialized) return;

        this.config = { ...this.config, ...options };
        this.setupGlobalErrorHandlers();
        this.setupPerformanceMonitoring();
        this.setupUserInteractionTracking();
        this.startLogFlushing();
        
        this.isInitialized = true;
        this.log('info', 'Monitoring system initialized', { sessionId: this.sessionId });
        
        // Track page load time
        if (document.readyState === 'complete') {
            this.trackPageLoad();
        } else {
            window.addEventListener('load', () => this.trackPageLoad());
        }
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    setUserId(userId) {
        this.userId = userId;
        this.log('info', 'User identified', { userId });
    }

    setupGlobalErrorHandlers() {
        // JavaScript errors
        window.addEventListener('error', (event) => {
            this.handleError({
                type: 'javascript_error',
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                stack: event.error?.stack,
                timestamp: new Date().toISOString(),
                url: window.location.href,
                userAgent: navigator.userAgent
            });
        });

        // Unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError({
                type: 'unhandled_promise_rejection',
                message: event.reason?.message || 'Unhandled promise rejection',
                stack: event.reason?.stack,
                timestamp: new Date().toISOString(),
                url: window.location.href,
                userAgent: navigator.userAgent
            });
        });

        // Resource loading errors
        window.addEventListener('error', (event) => {
            if (event.target !== window) {
                this.handleError({
                    type: 'resource_error',
                    message: `Failed to load resource: ${event.target.src || event.target.href}`,
                    element: event.target.tagName,
                    source: event.target.src || event.target.href,
                    timestamp: new Date().toISOString(),
                    url: window.location.href
                });
            }
        }, true);
    }

    setupPerformanceMonitoring() {
        if (!this.config.enablePerformanceMonitoring) return;

        // Performance Observer for detailed metrics
        if ('PerformanceObserver' in window) {
            try {
                this.performanceObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        this.handlePerformanceEntry(entry);
                    }
                });

                this.performanceObserver.observe({ 
                    entryTypes: ['navigation', 'resource', 'measure', 'paint'] 
                });
            } catch (e) {
                this.log('warn', 'Performance Observer not supported', { error: e.message });
            }
        }

        // Memory monitoring
        if ('memory' in performance) {
            setInterval(() => {
                this.trackMemoryUsage();
            }, 60000); // Every minute
        }

        // Connection monitoring
        if ('connection' in navigator) {
            this.trackNetworkInformation();
            navigator.connection.addEventListener('change', () => {
                this.trackNetworkInformation();
            });
        }
    }

    setupUserInteractionTracking() {
        if (!this.config.enableUserInteractionTracking) return;

        const trackInteraction = (type, target) => {
            this.metrics.interactions++;
            this.log('debug', 'User interaction', {
                type,
                element: target?.tagName?.toLowerCase(),
                className: target?.className,
                id: target?.id,
                timestamp: Date.now()
            });
        };

        // Click tracking
        document.addEventListener('click', (e) => {
            trackInteraction('click', e.target);
        });

        // Form submissions
        document.addEventListener('submit', (e) => {
            trackInteraction('form_submit', e.target);
        });

        // Input focus/blur for form analytics
        document.addEventListener('focus', (e) => {
            if (['input', 'textarea', 'select'].includes(e.target.tagName?.toLowerCase())) {
                trackInteraction('input_focus', e.target);
            }
        }, true);

        // Page visibility changes
        document.addEventListener('visibilitychange', () => {
            this.log('info', 'Page visibility changed', {
                hidden: document.hidden,
                visibilityState: document.visibilityState
            });
        });
    }

    handleError(error) {
        if (!this.config.enableErrorReporting) return;

        this.metrics.errors++;
        this.log('error', error.message || 'Unknown error', {
            ...error,
            sessionId: this.sessionId,
            userId: this.userId,
            timestamp: new Date().toISOString(),
            context: this.getContextInfo()
        });

        // Emit error event for other components to handle
        this.emit('error', error);

        // Send critical errors immediately
        if (error.type === 'javascript_error' && error.message?.toLowerCase().includes('critical')) {
            this.flushLogs(true);
        }
    }

    handlePerformanceEntry(entry) {
        const perfData = {
            name: entry.name,
            type: entry.entryType,
            startTime: entry.startTime,
            duration: entry.duration,
            timestamp: Date.now()
        };

        switch (entry.entryType) {
            case 'navigation':
                this.trackNavigationTiming(entry);
                break;
            case 'resource':
                this.trackResourceTiming(entry);
                break;
            case 'paint':
                this.trackPaintTiming(entry);
                break;
            case 'measure':
                this.log('debug', 'Performance measure', perfData);
                break;
        }
    }

    trackNavigationTiming(entry) {
        this.log('info', 'Navigation timing', {
            dns: entry.domainLookupEnd - entry.domainLookupStart,
            connection: entry.connectEnd - entry.connectStart,
            request: entry.responseStart - entry.requestStart,
            response: entry.responseEnd - entry.responseStart,
            domProcessing: entry.domContentLoadedEventEnd - entry.responseEnd,
            total: entry.loadEventEnd - entry.navigationStart,
            type: entry.type
        });
    }

    trackResourceTiming(entry) {
        // Only log slow resources or errors
        if (entry.duration > 1000 || entry.transferSize === 0) {
            this.log('warn', 'Slow or failed resource', {
                name: entry.name,
                duration: entry.duration,
                size: entry.transferSize,
                type: this.getResourceType(entry.name)
            });
        }
    }

    trackPaintTiming(entry) {
        this.log('info', 'Paint timing', {
            name: entry.name,
            startTime: entry.startTime
        });
    }

    trackPageLoad() {
        const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
        this.metrics.loadTime = loadTime;
        this.metrics.pageViews++;
        
        this.log('info', 'Page loaded', {
            loadTime,
            url: window.location.href,
            referrer: document.referrer
        });
    }

    trackMemoryUsage() {
        if ('memory' in performance) {
            const memory = performance.memory;
            this.log('debug', 'Memory usage', {
                used: Math.round(memory.usedJSHeapSize / 1024 / 1024),
                total: Math.round(memory.totalJSHeapSize / 1024 / 1024),
                limit: Math.round(memory.jsHeapSizeLimit / 1024 / 1024)
            });

            // Warn if memory usage is high
            const usagePercent = (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100;
            if (usagePercent > 80) {
                this.log('warn', 'High memory usage', {
                    usagePercent: Math.round(usagePercent),
                    used: Math.round(memory.usedJSHeapSize / 1024 / 1024)
                });
            }
        }
    }

    trackNetworkInformation() {
        if ('connection' in navigator) {
            const conn = navigator.connection;
            this.log('info', 'Network information', {
                effectiveType: conn.effectiveType,
                downlink: conn.downlink,
                rtt: conn.rtt,
                saveData: conn.saveData
            });
        }
    }

    trackAPICall(method, url, duration, status, error = null) {
        this.metrics.apiCalls++;
        
        const logLevel = status >= 400 ? 'error' : status >= 300 ? 'warn' : 'debug';
        this.log(logLevel, 'API call', {
            method,
            url,
            duration,
            status,
            error: error?.message,
            timestamp: Date.now()
        });
    }

    trackCustomEvent(name, data = {}) {
        this.log('info', `Custom event: ${name}`, {
            ...data,
            timestamp: Date.now()
        });
    }

    log(level, message, data = {}) {
        if (this.shouldLog(level)) {
            const logEntry = {
                level,
                message,
                data,
                timestamp: new Date().toISOString(),
                sessionId: this.sessionId,
                userId: this.userId,
                url: window.location.href,
                userAgent: navigator.userAgent
            };

            this.logs.push(logEntry);

            // Console output for development
            if (window.location.hostname === 'localhost') {
                const style = this.getConsoleStyle(level);
                console.log(`%c[${level.toUpperCase()}] ${message}`, style, data);
            }

            // Trim logs if too many
            if (this.logs.length > this.config.maxLogs) {
                this.logs = this.logs.slice(-this.config.maxLogs);
            }

            this.emit('log', logEntry);
        }
    }

    shouldLog(level) {
        const levels = { debug: 0, info: 1, warn: 2, error: 3 };
        return levels[level] >= levels[this.config.logLevel];
    }

    getConsoleStyle(level) {
        const styles = {
            debug: 'color: #718096; font-size: 12px',
            info: 'color: #2b6cb0; font-weight: bold',
            warn: 'color: #d69e2e; font-weight: bold',
            error: 'color: #e53e3e; font-weight: bold; background: #fed7d7; padding: 2px 4px; border-radius: 2px'
        };
        return styles[level] || styles.info;
    }

    getContextInfo() {
        return {
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            screen: {
                width: screen.width,
                height: screen.height,
                colorDepth: screen.colorDepth
            },
            connection: navigator.connection ? {
                effectiveType: navigator.connection.effectiveType,
                downlink: navigator.connection.downlink
            } : null,
            language: navigator.language,
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine
        };
    }

    getResourceType(url) {
        const extension = url.split('.').pop()?.toLowerCase();
        const typeMap = {
            'js': 'script',
            'css': 'stylesheet',
            'png': 'image',
            'jpg': 'image',
            'jpeg': 'image',
            'gif': 'image',
            'svg': 'image',
            'woff': 'font',
            'woff2': 'font',
            'ttf': 'font'
        };
        return typeMap[extension] || 'other';
    }

    startLogFlushing() {
        setInterval(() => {
            this.flushLogs();
        }, this.config.flushInterval);

        // Flush logs when page is about to unload
        window.addEventListener('beforeunload', () => {
            this.flushLogs(true);
        });

        // Flush logs when page becomes hidden
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.flushLogs();
            }
        });
    }

    async flushLogs(force = false) {
        if (!force && this.logs.length < this.config.batchSize) {
            return;
        }

        const logsToSend = this.logs.splice(0, this.config.batchSize);
        if (logsToSend.length === 0) return;

        try {
            // Try to send to backend
            await this.sendLogsToBackend(logsToSend);
        } catch (error) {
            // If backend is unavailable, store locally
            this.storeLogsLocally(logsToSend);
        }
    }

    async sendLogsToBackend(logs) {
        if (ServiceStatusManager.isMockMode()) {
            // In mock mode, just store locally
            this.storeLogsLocally(logs);
            return;
        }

        const response = await fetch('/api/monitoring/logs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                logs,
                metrics: this.metrics,
                sessionId: this.sessionId,
                timestamp: new Date().toISOString()
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to send logs: ${response.status}`);
        }
    }

    storeLogsLocally(logs) {
        try {
            const existingLogs = JSON.parse(localStorage.getItem('monitoring_logs') || '[]');
            const allLogs = [...existingLogs, ...logs];
            
            // Keep only the most recent logs
            const trimmedLogs = allLogs.slice(-500);
            localStorage.setItem('monitoring_logs', JSON.stringify(trimmedLogs));
        } catch (error) {
            console.warn('Failed to store logs locally:', error);
        }
    }

    getStoredLogs() {
        try {
            return JSON.parse(localStorage.getItem('monitoring_logs') || '[]');
        } catch (error) {
            return [];
        }
    }

    clearStoredLogs() {
        localStorage.removeItem('monitoring_logs');
    }

    // Performance measurement helpers
    startMeasure(name) {
        performance.mark(`${name}-start`);
    }

    endMeasure(name) {
        try {
            performance.mark(`${name}-end`);
            performance.measure(name, `${name}-start`, `${name}-end`);
        } catch (error) {
            this.log('warn', 'Performance measurement failed', { name, error: error.message });
        }
    }

    // Export data for debugging
    exportData() {
        return {
            sessionId: this.sessionId,
            userId: this.userId,
            metrics: this.metrics,
            logs: this.logs,
            storedLogs: this.getStoredLogs(),
            context: this.getContextInfo(),
            config: this.config
        };
    }

    // Generate performance report
    generatePerformanceReport() {
        const navigation = performance.getEntriesByType('navigation')[0];
        const resources = performance.getEntriesByType('resource');
        
        return {
            navigation: navigation ? {
                loadTime: navigation.loadEventEnd - navigation.navigationStart,
                domContentLoaded: navigation.domContentLoadedEventEnd - navigation.navigationStart,
                firstByte: navigation.responseStart - navigation.navigationStart,
                domComplete: navigation.domComplete - navigation.navigationStart
            } : null,
            resources: {
                total: resources.length,
                slow: resources.filter(r => r.duration > 1000).length,
                failed: resources.filter(r => r.transferSize === 0).length,
                totalSize: resources.reduce((sum, r) => sum + r.transferSize, 0)
            },
            metrics: this.metrics
        };
    }
}

export const MonitoringManager = new MonitoringManagerClass();

// Auto-initialize if not in test environment
if (typeof window !== 'undefined' && !window.location.href.includes('test')) {
    document.addEventListener('DOMContentLoaded', () => {
        MonitoringManager.init();
    });
}