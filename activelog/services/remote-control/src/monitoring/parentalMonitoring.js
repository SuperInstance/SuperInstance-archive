const EventEmitter = require('events');
const logger = require('../core/logger');
const path = require('path');
const fs = require('fs').promises;

class ParentalMonitoring extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      // Replay settings
      replayDuration: options.replayDuration || 30000, // 30 seconds
      maxReplaySize: options.maxReplaySize || 100 * 1024 * 1024, // 100MB
      frameRate: options.frameRate || 2, // 2 FPS for replay
      
      // Activity detection
      activityThreshold: options.activityThreshold || 0.3,
      inactivityTimeout: options.inactivityTimeout || 300000, // 5 minutes
      
      // Content filtering
      enableContentFilter: options.enableContentFilter !== false,
      blockedKeywords: options.blockedKeywords || ['inappropriate', 'blocked'],
      suspiciousPatterns: options.suspiciousPatterns || [
        /password/i,
        /credit.*card/i,
        /social.*security/i
      ],
      
      // Monitoring policies
      allowedTimeWindows: options.allowedTimeWindows || [
        { start: '08:00', end: '22:00', days: [1,2,3,4,5] }, // Weekdays
        { start: '09:00', end: '21:00', days: [0,6] } // Weekends
      ],
      
      maxDailyUsage: options.maxDailyUsage || 480, // 8 hours in minutes
      breakReminders: options.breakReminders !== false,
      breakInterval: options.breakInterval || 60, // minutes
      
      // Storage
      storageDir: options.storageDir || './data/parental-monitoring',
      retentionDays: options.retentionDays || 7,
      
      ...options
    };

    // Monitoring state
    this.isActive = false;
    this.currentSession = null;
    this.replayBuffer = [];
    this.dailyUsage = new Map(); // date -> minutes
    this.lastActivity = null;
    this.suspiciousEvents = [];
    
    // Activity tracking
    this.screenCaptures = [];
    this.keywordDetections = [];
    this.applicationUsage = new Map();
    this.websiteVisits = [];
    
    // Alerts and notifications
    this.alertQueue = [];
    this.parentNotifications = [];
    
    // Metrics
    this.metrics = {
      totalMonitoringTime: 0,
      screenshotsCaptured: 0,
      alertsGenerated: 0,
      replayRequests: 0,
      contentBlocked: 0
    };
  }

  async initialize() {
    logger.info('Initializing Parental Monitoring system...');
    
    try {
      // Create storage directory
      await fs.mkdir(this.options.storageDir, { recursive: true });
      
      // Setup replay buffer management
      this.setupReplayBuffer();
      
      // Start activity monitoring
      this.startActivityMonitoring();
      
      // Setup daily usage tracking
      this.setupUsageTracking();
      
      // Load existing data
      await this.loadMonitoringData();
      
      logger.info('Parental Monitoring system initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Parental Monitoring:', error);
      throw error;
    }
  }

  async startMonitoring(childProfile) {
    if (this.isActive) {
      logger.warn('Parental monitoring already active');
      return;
    }

    // Validate time windows
    if (!this.isAllowedTime()) {
      const nextAllowed = this.getNextAllowedTime();
      this.emit('time-restriction', {
        message: 'Computer usage not allowed at this time',
        nextAllowed
      });
      return { success: false, error: 'Usage not allowed at this time' };
    }

    // Check daily usage limits
    const todayUsage = this.getTodayUsage();
    if (todayUsage >= this.options.maxDailyUsage) {
      this.emit('usage-limit-exceeded', {
        todayUsage,
        limit: this.options.maxDailyUsage
      });
      return { success: false, error: 'Daily usage limit exceeded' };
    }

    this.isActive = true;
    this.currentSession = {
      childId: childProfile.id,
      childName: childProfile.name,
      startTime: Date.now(),
      lastActivity: Date.now(),
      screenCaptures: 0,
      alerts: 0
    };

    // Clear replay buffer
    this.replayBuffer = [];
    
    // Start capturing
    this.startReplayCapture();
    
    logger.info(`Parental monitoring started for ${childProfile.name}`, {
      childId: childProfile.id
    });
    
    this.emit('monitoring-started', {
      session: this.currentSession,
      todayUsage
    });

    return { success: true, session: this.currentSession };
  }

  async stopMonitoring() {
    if (!this.isActive) return;

    const endTime = Date.now();
    const sessionDuration = endTime - this.currentSession.startTime;
    
    // Update daily usage
    this.updateDailyUsage(sessionDuration);
    
    // Save session data
    await this.saveSessionData({
      ...this.currentSession,
      endTime,
      duration: sessionDuration,
      finalReplayBuffer: this.replayBuffer.length
    });

    this.isActive = false;
    const session = this.currentSession;
    this.currentSession = null;

    logger.info(`Parental monitoring stopped for ${session.childName}`, {
      duration: sessionDuration,
      screenCaptures: session.screenCaptures
    });

    this.emit('monitoring-stopped', { session, duration: sessionDuration });
  }

  setupReplayBuffer() {
    // Maintain rolling buffer of last 30 seconds
    setInterval(() => {
      if (this.isActive) {
        this.captureReplayFrame();
      }
      this.cleanupReplayBuffer();
    }, 1000 / this.options.frameRate); // Based on frame rate
  }

  async captureReplayFrame() {
    if (!this.isActive) return;

    try {
      // In a real implementation, this would capture actual screen
      const frameData = {
        timestamp: Date.now(),
        windowTitle: await this.getCurrentWindowTitle(),
        screenshot: 'base64_screenshot_data', // Simulated
        activities: await this.detectCurrentActivities(),
        size: 50000 // Simulated frame size
      };

      // Add to replay buffer
      this.replayBuffer.push(frameData);
      this.currentSession.screenCaptures++;
      this.metrics.screenshotsCaptured++;

      // Check for suspicious content
      await this.analyzeFrameContent(frameData);

    } catch (error) {
      logger.error('Replay frame capture error:', error);
    }
  }

  cleanupReplayBuffer() {
    const cutoffTime = Date.now() - this.options.replayDuration;
    
    // Remove old frames
    this.replayBuffer = this.replayBuffer.filter(frame => 
      frame.timestamp > cutoffTime
    );

    // Check buffer size
    const totalSize = this.replayBuffer.reduce((sum, frame) => sum + frame.size, 0);
    if (totalSize > this.options.maxReplaySize) {
      // Remove oldest frames to stay under limit
      while (this.replayBuffer.length > 0) {
        const currentSize = this.replayBuffer.reduce((sum, frame) => sum + frame.size, 0);
        if (currentSize <= this.options.maxReplaySize * 0.8) break;
        this.replayBuffer.shift();
      }
    }
  }

  async analyzeFrameContent(frameData) {
    try {
      const windowTitle = frameData.windowTitle.toLowerCase();
      
      // Check blocked keywords
      for (const keyword of this.options.blockedKeywords) {
        if (windowTitle.includes(keyword.toLowerCase())) {
          await this.handleContentViolation('blocked_keyword', {
            keyword,
            windowTitle: frameData.windowTitle,
            frame: frameData
          });
          return;
        }
      }

      // Check suspicious patterns
      for (const pattern of this.options.suspiciousPatterns) {
        if (pattern.test(windowTitle)) {
          await this.handleSuspiciousActivity('pattern_match', {
            pattern: pattern.toString(),
            windowTitle: frameData.windowTitle,
            frame: frameData
          });
        }
      }

      // Analyze activities for inappropriate content
      if (frameData.activities) {
        for (const activity of frameData.activities) {
          if (activity.risk && activity.risk > 0.7) {
            await this.handleContentViolation('high_risk_activity', {
              activity,
              frame: frameData
            });
          }
        }
      }

    } catch (error) {
      logger.error('Content analysis error:', error);
    }
  }

  async handleContentViolation(type, data) {
    const violation = {
      id: `violation_${Date.now()}`,
      type,
      timestamp: Date.now(),
      severity: 'high',
      data,
      childId: this.currentSession?.childId,
      action: 'logged'
    };

    this.suspiciousEvents.push(violation);
    this.metrics.contentBlocked++;

    // Create parent alert
    const alert = {
      id: `alert_${Date.now()}`,
      type: 'content_violation',
      title: 'Inappropriate Content Detected',
      message: `${type.replace('_', ' ')} detected in ${data.windowTitle}`,
      timestamp: Date.now(),
      severity: 'high',
      childId: this.currentSession.childId,
      replayAvailable: true
    };

    this.alertQueue.push(alert);
    this.parentNotifications.push(alert);
    this.currentSession.alerts++;
    this.metrics.alertsGenerated++;

    logger.warn(`Content violation detected: ${type}`, {
      childId: this.currentSession.childId,
      windowTitle: data.windowTitle
    });

    this.emit('content-violation', violation);
    this.emit('parent-alert', alert);
  }

  async handleSuspiciousActivity(type, data) {
    const event = {
      id: `suspicious_${Date.now()}`,
      type,
      timestamp: Date.now(),
      data,
      childId: this.currentSession?.childId
    };

    this.suspiciousEvents.push(event);

    // Create lower priority alert
    const alert = {
      id: `alert_${Date.now()}`,
      type: 'suspicious_activity',
      title: 'Suspicious Activity Detected',
      message: `${type.replace('_', ' ')} in ${data.windowTitle}`,
      timestamp: Date.now(),
      severity: 'medium',
      childId: this.currentSession.childId,
      replayAvailable: true
    };

    this.alertQueue.push(alert);

    logger.info(`Suspicious activity detected: ${type}`, {
      childId: this.currentSession.childId
    });

    this.emit('suspicious-activity', event);
  }

  async getReplayData(startTime, endTime) {
    this.metrics.replayRequests++;

    if (!startTime) {
      startTime = Date.now() - this.options.replayDuration;
    }
    if (!endTime) {
      endTime = Date.now();
    }

    // Filter replay buffer for requested time range
    const replayFrames = this.replayBuffer.filter(frame => 
      frame.timestamp >= startTime && frame.timestamp <= endTime
    );

    // Include additional context
    const replayData = {
      id: `replay_${Date.now()}`,
      startTime,
      endTime,
      duration: endTime - startTime,
      frameCount: replayFrames.length,
      frames: replayFrames,
      events: this.suspiciousEvents.filter(event =>
        event.timestamp >= startTime && event.timestamp <= endTime
      ),
      childId: this.currentSession?.childId,
      generatedAt: Date.now()
    };

    logger.info(`Replay data generated`, {
      startTime,
      endTime,
      frameCount: replayFrames.length
    });

    return replayData;
  }

  startActivityMonitoring() {
    setInterval(() => {
      if (this.isActive) {
        this.checkActivityLevel();
        this.checkBreakReminders();
      }
    }, 30000); // Check every 30 seconds
  }

  checkActivityLevel() {
    // Simulate activity detection
    const now = Date.now();
    const timeSinceLastActivity = this.lastActivity ? now - this.lastActivity : 0;
    
    if (timeSinceLastActivity > this.options.inactivityTimeout) {
      this.emit('child-inactive', {
        inactiveFor: timeSinceLastActivity,
        childId: this.currentSession?.childId
      });
    }
  }

  checkBreakReminders() {
    if (!this.options.breakReminders || !this.currentSession) return;

    const sessionDuration = Date.now() - this.currentSession.startTime;
    const breakIntervalMs = this.options.breakInterval * 60 * 1000;

    if (sessionDuration % breakIntervalMs < 30000) { // Within 30 seconds of break time
      this.emit('break-reminder', {
        sessionDuration,
        recommendedBreak: 10 // minutes
      });
    }
  }

  setupUsageTracking() {
    // Track daily usage
    setInterval(() => {
      if (this.isActive) {
        const today = new Date().toDateString();
        const current = this.dailyUsage.get(today) || 0;
        this.dailyUsage.set(today, current + 1); // Add 1 minute
      }
    }, 60000); // Every minute
  }

  isAllowedTime() {
    const now = new Date();
    const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    const dayOfWeek = now.getDay();

    return this.options.allowedTimeWindows.some(window => {
      if (!window.days.includes(dayOfWeek)) return false;
      return currentTime >= window.start && currentTime <= window.end;
    });
  }

  getTodayUsage() {
    const today = new Date().toDateString();
    return this.dailyUsage.get(today) || 0;
  }

  updateDailyUsage(sessionDuration) {
    const today = new Date().toDateString();
    const minutes = Math.round(sessionDuration / 60000);
    const current = this.dailyUsage.get(today) || 0;
    this.dailyUsage.set(today, current + minutes);
  }

  async getCurrentWindowTitle() {
    // In a real implementation, this would get the actual active window
    const simulatedTitles = [
      'Educational Website - Mathematics',
      'Google Classroom',
      'Minecraft',
      'YouTube - Science Videos',
      'Khan Academy',
      'Discord',
      'Social Media Platform'
    ];
    return simulatedTitles[Math.floor(Math.random() * simulatedTitles.length)];
  }

  async detectCurrentActivities() {
    // Simulate activity detection
    return [
      {
        type: 'application_usage',
        application: 'web_browser',
        risk: Math.random(),
        duration: Math.floor(Math.random() * 300000) // 0-5 minutes
      },
      {
        type: 'keyboard_activity',
        keystrokesPerMinute: Math.floor(Math.random() * 100),
        risk: Math.random() * 0.3
      }
    ];
  }

  // Public API methods
  getMonitoringStatus() {
    return {
      isActive: this.isActive,
      currentSession: this.currentSession,
      todayUsage: this.getTodayUsage(),
      replayBufferSize: this.replayBuffer.length,
      pendingAlerts: this.alertQueue.length
    };
  }

  getAlerts() {
    const alerts = [...this.alertQueue];
    this.alertQueue = []; // Clear after reading
    return alerts;
  }

  getParentNotifications() {
    return this.parentNotifications.slice(-50); // Last 50 notifications
  }

  async generateParentReport(date = null) {
    const targetDate = date ? new Date(date) : new Date();
    const dateString = targetDate.toDateString();
    
    const report = {
      date: dateString,
      childId: this.currentSession?.childId,
      totalUsageMinutes: this.dailyUsage.get(dateString) || 0,
      violations: this.suspiciousEvents.filter(event => {
        const eventDate = new Date(event.timestamp).toDateString();
        return eventDate === dateString;
      }),
      applicationUsage: this.getApplicationUsage(dateString),
      activitySummary: {
        screenCaptures: this.metrics.screenshotsCaptured,
        alertsGenerated: this.metrics.alertsGenerated,
        contentBlocked: this.metrics.contentBlocked
      },
      generatedAt: Date.now()
    };

    return report;
  }

  getApplicationUsage(date) {
    // In a real implementation, this would track actual application usage
    return [
      { name: 'Educational Software', duration: 120, category: 'education' },
      { name: 'Web Browser', duration: 90, category: 'web' },
      { name: 'Games', duration: 60, category: 'entertainment' },
      { name: 'Communication', duration: 30, category: 'social' }
    ];
  }

  async saveSessionData(sessionData) {
    try {
      const filename = `session_${sessionData.childId}_${Date.now()}.json`;
      const filepath = path.join(this.options.storageDir, filename);
      
      await fs.writeFile(filepath, JSON.stringify(sessionData, null, 2));
      logger.debug(`Session data saved: ${filename}`);
    } catch (error) {
      logger.error('Failed to save session data:', error);
    }
  }

  async loadMonitoringData() {
    try {
      // Load existing daily usage data
      const files = await fs.readdir(this.options.storageDir);
      const dataFiles = files.filter(file => file.startsWith('daily_usage_'));
      
      for (const file of dataFiles) {
        const filepath = path.join(this.options.storageDir, file);
        const data = JSON.parse(await fs.readFile(filepath, 'utf8'));
        
        for (const [date, usage] of Object.entries(data)) {
          this.dailyUsage.set(date, usage);
        }
      }
    } catch (error) {
      logger.debug('No existing monitoring data found');
    }
  }

  getMetrics() {
    return {
      ...this.metrics,
      isActive: this.isActive,
      replayBufferFrames: this.replayBuffer.length,
      suspiciousEvents: this.suspiciousEvents.length,
      todayUsage: this.getTodayUsage()
    };
  }

  async cleanup() {
    if (this.isActive) {
      await this.stopMonitoring();
    }
    
    this.replayBuffer = [];
    this.suspiciousEvents = [];
    this.alertQueue = [];
    this.parentNotifications = [];
    this.dailyUsage.clear();
    this.applicationUsage.clear();
    
    this.removeAllListeners();
    logger.info('Parental Monitoring system cleaned up');
  }
}

module.exports = ParentalMonitoring;