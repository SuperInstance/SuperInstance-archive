const EventEmitter = require('events');
const logger = require('../core/logger');
const path = require('path');
const fs = require('fs').promises;

class ProductivityTracking extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      // Tracking settings
      trackingInterval: options.trackingInterval || 30000, // 30 seconds
      idleThreshold: options.idleThreshold || 300000, // 5 minutes
      screenshotInterval: options.screenshotInterval || 600000, // 10 minutes
      
      // Application categorization
      productiveApps: options.productiveApps || [
        'vscode', 'intellij', 'eclipse', 'sublime', 'atom',
        'excel', 'word', 'powerpoint', 'outlook',
        'photoshop', 'illustrator', 'figma', 'sketch',
        'slack', 'teams', 'zoom', 'calendar'
      ],
      
      unproductiveApps: options.unproductiveApps || [
        'facebook', 'instagram', 'twitter', 'tiktok',
        'youtube', 'netflix', 'spotify', 'games',
        'reddit', 'discord'
      ],
      
      // Website categorization
      productiveDomains: options.productiveDomains || [
        'github.com', 'stackoverflow.com', 'developer.mozilla.org',
        'docs.microsoft.com', 'aws.amazon.com', 'google.com/search'
      ],
      
      unproductiveDomains: options.unproductiveDomains || [
        'facebook.com', 'instagram.com', 'twitter.com',
        'youtube.com', 'netflix.com', 'twitch.tv'
      ],
      
      // Reporting
      generateReports: options.generateReports !== false,
      reportInterval: options.reportInterval || 86400000, // Daily
      alertThresholds: {
        lowProductivity: options.alertThresholds?.lowProductivity || 0.3,
        highIdle: options.alertThresholds?.highIdle || 0.4,
        excessiveNonWork: options.alertThresholds?.excessiveNonWork || 0.25
      },
      
      // Privacy settings
      blurScreenshots: options.blurScreenshots || false,
      excludePersonalTime: options.excludePersonalTime !== false,
      respectPrivacyHours: options.respectPrivacyHours || true,
      
      // Storage
      storageDir: options.storageDir || './data/productivity-tracking',
      retentionDays: options.retentionDays || 30,
      
      ...options
    };

    // Tracking state
    this.isTracking = false;
    this.currentEmployee = null;
    this.currentSession = null;
    this.lastActivity = Date.now();
    this.activityBuffer = [];
    
    // Productivity data
    this.dailyStats = new Map(); // date -> stats
    this.applicationTime = new Map(); // app -> time
    this.websiteTime = new Map(); // domain -> time
    this.keystrokeCounts = new Map(); // hour -> count
    this.mouseActivity = new Map(); // hour -> count
    
    // Behavioral patterns
    this.workPatterns = {
      peakHours: [],
      averageSessionLength: 0,
      breakPatterns: [],
      focusScore: 0
    };
    
    // Alert system
    this.alerts = [];
    this.dailyAlerts = new Map();
    
    // Metrics
    this.metrics = {
      totalTrackingTime: 0,
      productiveTime: 0,
      unproductiveTime: 0,
      idleTime: 0,
      screenshotsTaken: 0,
      alertsGenerated: 0,
      reportsGenerated: 0
    };
  }

  async initialize() {
    logger.info('Initializing Productivity Tracking system...');
    
    try {
      // Create storage directory
      await fs.mkdir(this.options.storageDir, { recursive: true });
      
      // Load existing data
      await this.loadTrackingData();
      
      // Setup periodic reporting
      if (this.options.generateReports) {
        this.setupPeriodicReporting();
      }
      
      // Setup data cleanup
      this.setupDataCleanup();
      
      logger.info('Productivity Tracking system initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Productivity Tracking:', error);
      throw error;
    }
  }

  async startTracking(employeeProfile) {
    if (this.isTracking) {
      logger.warn('Productivity tracking already active');
      return { success: false, error: 'Already tracking' };
    }

    this.isTracking = true;
    this.currentEmployee = employeeProfile;
    this.currentSession = {
      employeeId: employeeProfile.id,
      employeeName: employeeProfile.name,
      department: employeeProfile.department,
      startTime: Date.now(),
      activities: [],
      applications: new Map(),
      websites: new Map(),
      screenshots: [],
      keystrokes: 0,
      mouseClicks: 0,
      idleTime: 0,
      productiveTime: 0,
      unproductiveTime: 0
    };

    // Start activity monitoring
    this.startActivityMonitoring();
    
    // Start screenshot capture if enabled
    if (this.options.screenshotInterval > 0) {
      this.startScreenshotCapture();
    }

    logger.info(`Productivity tracking started for ${employeeProfile.name}`, {
      employeeId: employeeProfile.id,
      department: employeeProfile.department
    });

    this.emit('tracking-started', {
      employee: employeeProfile,
      session: this.currentSession
    });

    return { success: true, session: this.currentSession };
  }

  async stopTracking() {
    if (!this.isTracking) return;

    const endTime = Date.now();
    const sessionDuration = endTime - this.currentSession.startTime;
    
    // Finalize session data
    this.currentSession.endTime = endTime;
    this.currentSession.duration = sessionDuration;
    
    // Calculate final productivity scores
    await this.calculateProductivityScores();
    
    // Update daily statistics
    await this.updateDailyStats();
    
    // Save session data
    await this.saveSessionData(this.currentSession);
    
    // Generate alerts if needed
    await this.checkProductivityAlerts();

    const session = { ...this.currentSession };
    this.isTracking = false;
    this.currentEmployee = null;
    this.currentSession = null;

    logger.info(`Productivity tracking stopped for ${session.employeeName}`, {
      duration: sessionDuration,
      productiveTime: session.productiveTime,
      idleTime: session.idleTime
    });

    this.emit('tracking-stopped', { session });
    return session;
  }

  startActivityMonitoring() {
    this.activityInterval = setInterval(async () => {
      if (!this.isTracking) return;

      try {
        await this.recordCurrentActivity();
        await this.detectIdleState();
        await this.updateApplicationUsage();
        await this.trackWebsiteVisits();
        
      } catch (error) {
        logger.error('Activity monitoring error:', error);
      }
    }, this.options.trackingInterval);
  }

  async recordCurrentActivity() {
    const now = Date.now();
    const activity = {
      timestamp: now,
      activeApplication: await this.getCurrentApplication(),
      windowTitle: await this.getCurrentWindowTitle(),
      url: await this.getCurrentURL(),
      keystrokes: this.getRecentKeystrokes(),
      mouseActivity: this.getRecentMouseActivity(),
      category: null,
      productivityScore: 0
    };

    // Categorize activity
    activity.category = this.categorizeActivity(activity);
    activity.productivityScore = this.calculateActivityProductivity(activity);

    // Add to current session
    this.currentSession.activities.push(activity);
    this.activityBuffer.push(activity);

    // Update counters
    this.currentSession.keystrokes += activity.keystrokes;
    this.currentSession.mouseClicks += activity.mouseActivity;

    // Track time by category
    const timeSlice = this.options.trackingInterval;
    if (activity.category === 'productive') {
      this.currentSession.productiveTime += timeSlice;
      this.metrics.productiveTime += timeSlice;
    } else if (activity.category === 'unproductive') {
      this.currentSession.unproductiveTime += timeSlice;
      this.metrics.unproductiveTime += timeSlice;
    }

    this.lastActivity = now;
    
    // Keep buffer manageable
    if (this.activityBuffer.length > 1000) {
      this.activityBuffer = this.activityBuffer.slice(-500);
    }
  }

  categorizeActivity(activity) {
    const app = activity.activeApplication?.toLowerCase() || '';
    const title = activity.windowTitle?.toLowerCase() || '';
    const url = activity.url?.toLowerCase() || '';

    // Check productive applications
    if (this.options.productiveApps.some(productiveApp => 
        app.includes(productiveApp) || title.includes(productiveApp))) {
      return 'productive';
    }

    // Check unproductive applications
    if (this.options.unproductiveApps.some(unproductiveApp => 
        app.includes(unproductiveApp) || title.includes(unproductiveApp))) {
      return 'unproductive';
    }

    // Check website domains
    if (url) {
      if (this.options.productiveDomains.some(domain => url.includes(domain))) {
        return 'productive';
      }
      if (this.options.unproductiveDomains.some(domain => url.includes(domain))) {
        return 'unproductive';
      }
    }

    // Check for development/work indicators
    if (title.includes('code') || title.includes('development') || 
        title.includes('documentation') || title.includes('meeting')) {
      return 'productive';
    }

    // Default to neutral
    return 'neutral';
  }

  calculateActivityProductivity(activity) {
    let score = 0.5; // Neutral baseline

    switch (activity.category) {
      case 'productive':
        score = 0.8;
        break;
      case 'unproductive':
        score = 0.2;
        break;
      case 'neutral':
        score = 0.5;
        break;
    }

    // Boost score based on activity level
    const activityLevel = (activity.keystrokes + activity.mouseActivity) / 10;
    score += Math.min(activityLevel * 0.1, 0.2);

    // Cap at 1.0
    return Math.min(score, 1.0);
  }

  async detectIdleState() {
    const now = Date.now();
    const timeSinceActivity = now - this.lastActivity;

    if (timeSinceActivity > this.options.idleThreshold) {
      const idleTime = Math.min(timeSinceActivity, this.options.trackingInterval);
      this.currentSession.idleTime += idleTime;
      this.metrics.idleTime += idleTime;

      this.emit('employee-idle', {
        employeeId: this.currentEmployee.id,
        idleTime: timeSinceActivity
      });
    }
  }

  async updateApplicationUsage() {
    const currentApp = await this.getCurrentApplication();
    if (!currentApp) return;

    const timeSlice = this.options.trackingInterval;
    const currentUsage = this.currentSession.applications.get(currentApp) || 0;
    this.currentSession.applications.set(currentApp, currentUsage + timeSlice);

    // Update global application time
    const globalUsage = this.applicationTime.get(currentApp) || 0;
    this.applicationTime.set(currentApp, globalUsage + timeSlice);
  }

  async trackWebsiteVisits() {
    const url = await this.getCurrentURL();
    if (!url) return;

    try {
      const domain = new URL(url).hostname;
      const timeSlice = this.options.trackingInterval;
      
      const currentUsage = this.currentSession.websites.get(domain) || 0;
      this.currentSession.websites.set(domain, currentUsage + timeSlice);

      // Update global website time
      const globalUsage = this.websiteTime.get(domain) || 0;
      this.websiteTime.set(domain, globalUsage + timeSlice);
    } catch (error) {
      // Invalid URL, skip
    }
  }

  startScreenshotCapture() {
    this.screenshotInterval = setInterval(async () => {
      if (!this.isTracking) return;

      try {
        // Check if we should respect privacy hours
        if (this.options.respectPrivacyHours && !this.isWorkingHours()) {
          return;
        }

        const screenshot = await this.captureScreenshot();
        this.currentSession.screenshots.push({
          timestamp: Date.now(),
          data: screenshot,
          blurred: this.options.blurScreenshots
        });

        this.metrics.screenshotsTaken++;

      } catch (error) {
        logger.error('Screenshot capture error:', error);
      }
    }, this.options.screenshotInterval);
  }

  async calculateProductivityScores() {
    const totalTime = this.currentSession.duration;
    if (totalTime === 0) return;

    const session = this.currentSession;
    
    // Overall productivity percentage
    session.productivityPercentage = (session.productiveTime / totalTime) * 100;
    
    // Idle percentage
    session.idlePercentage = (session.idleTime / totalTime) * 100;
    
    // Focus score (based on app switching frequency)
    const appSwitches = session.activities.filter((activity, index) => {
      if (index === 0) return false;
      return activity.activeApplication !== session.activities[index - 1].activeApplication;
    }).length;
    
    session.focusScore = Math.max(0, 100 - (appSwitches / (totalTime / 60000)) * 10);
    
    // Activity score (keystrokes + mouse activity)
    const avgKeystrokesPerMinute = (session.keystrokes / (totalTime / 60000));
    session.activityScore = Math.min(100, avgKeystrokesPerMinute);

    logger.debug(`Productivity scores calculated`, {
      productivityPercentage: session.productivityPercentage.toFixed(1),
      idlePercentage: session.idlePercentage.toFixed(1),
      focusScore: session.focusScore.toFixed(1)
    });
  }

  async updateDailyStats() {
    const today = new Date().toDateString();
    const session = this.currentSession;
    
    const existing = this.dailyStats.get(today) || {
      date: today,
      totalTime: 0,
      productiveTime: 0,
      unproductiveTime: 0,
      idleTime: 0,
      sessions: 0,
      keystrokes: 0,
      mouseClicks: 0,
      applications: new Map(),
      websites: new Map(),
      averageProductivity: 0,
      averageFocus: 0
    };

    // Update with session data
    existing.totalTime += session.duration;
    existing.productiveTime += session.productiveTime;
    existing.unproductiveTime += session.unproductiveTime;
    existing.idleTime += session.idleTime;
    existing.sessions += 1;
    existing.keystrokes += session.keystrokes;
    existing.mouseClicks += session.mouseClicks;

    // Merge application usage
    for (const [app, time] of session.applications) {
      existing.applications.set(app, (existing.applications.get(app) || 0) + time);
    }

    // Merge website usage
    for (const [site, time] of session.websites) {
      existing.websites.set(site, (existing.websites.get(site) || 0) + time);
    }

    // Update averages
    existing.averageProductivity = ((existing.averageProductivity * (existing.sessions - 1)) + 
                                   session.productivityPercentage) / existing.sessions;
    existing.averageFocus = ((existing.averageFocus * (existing.sessions - 1)) + 
                            session.focusScore) / existing.sessions;

    this.dailyStats.set(today, existing);
  }

  async checkProductivityAlerts() {
    const session = this.currentSession;
    const alerts = [];

    // Low productivity alert
    if (session.productivityPercentage < this.options.alertThresholds.lowProductivity * 100) {
      alerts.push({
        type: 'low_productivity',
        severity: 'medium',
        message: `Low productivity detected: ${session.productivityPercentage.toFixed(1)}%`,
        employeeId: session.employeeId,
        timestamp: Date.now()
      });
    }

    // High idle time alert
    if (session.idlePercentage > this.options.alertThresholds.highIdle * 100) {
      alerts.push({
        type: 'high_idle',
        severity: 'low',
        message: `High idle time: ${session.idlePercentage.toFixed(1)}%`,
        employeeId: session.employeeId,
        timestamp: Date.now()
      });
    }

    // Excessive non-work activity
    const nonWorkPercentage = session.unproductiveTime / session.duration * 100;
    if (nonWorkPercentage > this.options.alertThresholds.excessiveNonWork * 100) {
      alerts.push({
        type: 'excessive_non_work',
        severity: 'high',
        message: `Excessive non-work activity: ${nonWorkPercentage.toFixed(1)}%`,
        employeeId: session.employeeId,
        timestamp: Date.now()
      });
    }

    // Save alerts
    for (const alert of alerts) {
      this.alerts.push(alert);
      this.metrics.alertsGenerated++;
      
      logger.warn(`Productivity alert: ${alert.type}`, {
        employeeId: session.employeeId,
        severity: alert.severity
      });

      this.emit('productivity-alert', alert);
    }
  }

  setupPeriodicReporting() {
    setInterval(async () => {
      try {
        await this.generateDailyReport();
      } catch (error) {
        logger.error('Report generation error:', error);
      }
    }, this.options.reportInterval);
  }

  async generateDailyReport(date = null) {
    const targetDate = date ? new Date(date) : new Date();
    const dateString = targetDate.toDateString();
    const stats = this.dailyStats.get(dateString);

    if (!stats) {
      return null;
    }

    const report = {
      date: dateString,
      employee: this.currentEmployee,
      summary: {
        totalTime: this.formatDuration(stats.totalTime),
        productiveTime: this.formatDuration(stats.productiveTime),
        unproductiveTime: this.formatDuration(stats.unproductiveTime),
        idleTime: this.formatDuration(stats.idleTime),
        productivityPercentage: stats.averageProductivity,
        focusScore: stats.averageFocus,
        sessionsCount: stats.sessions
      },
      topApplications: this.getTopItems(stats.applications, 10),
      topWebsites: this.getTopItems(stats.websites, 10),
      activityMetrics: {
        keystrokesPerHour: Math.round(stats.keystrokes / (stats.totalTime / 3600000)),
        mouseClicksPerHour: Math.round(stats.mouseClicks / (stats.totalTime / 3600000))
      },
      alerts: this.alerts.filter(alert => {
        const alertDate = new Date(alert.timestamp).toDateString();
        return alertDate === dateString;
      }),
      generatedAt: Date.now()
    };

    // Save report
    await this.saveReport(report);
    this.metrics.reportsGenerated++;

    logger.info(`Daily report generated for ${dateString}`, {
      employeeId: this.currentEmployee?.id,
      productivityPercentage: report.summary.productivityPercentage.toFixed(1)
    });

    this.emit('report-generated', report);
    return report;
  }

  // Helper methods for simulated data
  async getCurrentApplication() {
    const apps = [
      'Visual Studio Code', 'Google Chrome', 'Microsoft Teams',
      'Slack', 'Excel', 'PowerPoint', 'Outlook', 'Figma',
      'Terminal', 'Photoshop', 'Calculator', 'YouTube', 'Facebook'
    ];
    return apps[Math.floor(Math.random() * apps.length)];
  }

  async getCurrentWindowTitle() {
    const titles = [
      'Project Documentation - Google Docs',
      'Sprint Planning - Jira',
      'Team Meeting - Microsoft Teams',
      'Code Review - GitHub',
      'Database Design - draw.io',
      'Social Media - Facebook',
      'Video Platform - YouTube',
      'Email - Outlook'
    ];
    return titles[Math.floor(Math.random() * titles.length)];
  }

  async getCurrentURL() {
    const urls = [
      'https://github.com/company/project',
      'https://docs.company.com',
      'https://jira.company.com',
      'https://stackoverflow.com/questions',
      'https://youtube.com/watch',
      'https://facebook.com/feed',
      'https://twitter.com/home'
    ];
    return urls[Math.floor(Math.random() * urls.length)];
  }

  getRecentKeystrokes() {
    return Math.floor(Math.random() * 50); // Simulated
  }

  getRecentMouseActivity() {
    return Math.floor(Math.random() * 20); // Simulated
  }

  async captureScreenshot() {
    return 'data:image/jpeg;base64,/9j/4AAQSkZJRgABA...'; // Simulated base64
  }

  isWorkingHours() {
    const now = new Date();
    const hour = now.getHours();
    return hour >= 9 && hour <= 17; // 9 AM to 5 PM
  }

  formatDuration(ms) {
    const hours = Math.floor(ms / 3600000);
    const minutes = Math.floor((ms % 3600000) / 60000);
    return `${hours}h ${minutes}m`;
  }

  getTopItems(map, limit) {
    return Array.from(map.entries())
      .sort(([,a], [,b]) => b - a)
      .slice(0, limit)
      .map(([name, time]) => ({
        name,
        time: this.formatDuration(time),
        percentage: ((time / Array.from(map.values()).reduce((a, b) => a + b, 0)) * 100).toFixed(1)
      }));
  }

  setupDataCleanup() {
    setInterval(async () => {
      await this.cleanupOldData();
    }, 24 * 60 * 60 * 1000); // Daily cleanup
  }

  async cleanupOldData() {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - this.options.retentionDays);
    
    let cleaned = 0;
    for (const [dateString] of this.dailyStats) {
      if (new Date(dateString) < cutoffDate) {
        this.dailyStats.delete(dateString);
        cleaned++;
      }
    }

    if (cleaned > 0) {
      logger.info(`Cleaned up ${cleaned} days of old tracking data`);
    }
  }

  async saveSessionData(sessionData) {
    try {
      const filename = `session_${sessionData.employeeId}_${Date.now()}.json`;
      const filepath = path.join(this.options.storageDir, filename);
      
      // Remove screenshots from saved data to save space
      const sessionToSave = {
        ...sessionData,
        screenshots: sessionData.screenshots.map(s => ({
          timestamp: s.timestamp,
          blurred: s.blurred
          // Remove actual image data
        }))
      };
      
      await fs.writeFile(filepath, JSON.stringify(sessionToSave, null, 2));
    } catch (error) {
      logger.error('Failed to save session data:', error);
    }
  }

  async saveReport(report) {
    try {
      const filename = `report_${report.date.replace(/\s+/g, '_')}_${Date.now()}.json`;
      const filepath = path.join(this.options.storageDir, filename);
      await fs.writeFile(filepath, JSON.stringify(report, null, 2));
    } catch (error) {
      logger.error('Failed to save report:', error);
    }
  }

  async loadTrackingData() {
    try {
      // Load existing daily statistics
      const files = await fs.readdir(this.options.storageDir);
      const statsFiles = files.filter(file => file.startsWith('daily_stats_'));
      
      for (const file of statsFiles) {
        const filepath = path.join(this.options.storageDir, file);
        const stats = JSON.parse(await fs.readFile(filepath, 'utf8'));
        this.dailyStats.set(stats.date, stats);
      }
    } catch (error) {
      logger.debug('No existing tracking data found');
    }
  }

  // Public API methods
  getTrackingStatus() {
    return {
      isTracking: this.isTracking,
      currentEmployee: this.currentEmployee,
      currentSession: this.currentSession ? {
        ...this.currentSession,
        screenshots: undefined // Don't include screenshot data in status
      } : null
    };
  }

  getProductivitySummary(employeeId, days = 7) {
    const summaries = [];
    const endDate = new Date();
    
    for (let i = 0; i < days; i++) {
      const date = new Date(endDate);
      date.setDate(date.getDate() - i);
      const dateString = date.toDateString();
      
      const stats = this.dailyStats.get(dateString);
      if (stats) {
        summaries.push({
          date: dateString,
          productivityPercentage: stats.averageProductivity,
          focusScore: stats.averageFocus,
          totalTime: this.formatDuration(stats.totalTime),
          idlePercentage: (stats.idleTime / stats.totalTime * 100).toFixed(1)
        });
      }
    }

    return summaries.reverse(); // Chronological order
  }

  getAlerts(severity = null) {
    let filteredAlerts = [...this.alerts];
    
    if (severity) {
      filteredAlerts = filteredAlerts.filter(alert => alert.severity === severity);
    }

    return filteredAlerts.sort((a, b) => b.timestamp - a.timestamp);
  }

  getMetrics() {
    return {
      ...this.metrics,
      isTracking: this.isTracking,
      dailyStatsCount: this.dailyStats.size,
      pendingAlerts: this.alerts.length
    };
  }

  async cleanup() {
    if (this.isTracking) {
      await this.stopTracking();
    }

    if (this.activityInterval) {
      clearInterval(this.activityInterval);
    }

    if (this.screenshotInterval) {
      clearInterval(this.screenshotInterval);
    }

    this.activityBuffer = [];
    this.alerts = [];
    this.dailyStats.clear();
    this.applicationTime.clear();
    this.websiteTime.clear();

    this.removeAllListeners();
    logger.info('Productivity Tracking system cleaned up');
  }
}

module.exports = ProductivityTracking;