const { EventEmitter } = require('events');

class SessionAnalytics extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      retentionDays: options.retentionDays || 90,
      aggregationInterval: options.aggregationInterval || 3600000, // 1 hour
      enableRealTimeMetrics: options.enableRealTimeMetrics !== false,
      enableGeoAnalytics: options.enableGeoAnalytics !== false,
      enableDeviceAnalytics: options.enableDeviceAnalytics !== false,
      enableBehaviorAnalytics: options.enableBehaviorAnalytics !== false,
      maxEventsPerSession: options.maxEventsPerSession || 10000,
      ...options
    };
    
    this.sessions = new Map();
    this.events = new Map();
    this.userSessions = new Map();
    this.aggregatedMetrics = new Map();
    this.realTimeMetrics = new Map();
    this.cohortData = new Map();
    this.funnelData = new Map();
    
    this.setupAggregationInterval();
    this.setupRetentionCleanup();
  }

  // Session Tracking
  async startSession(sessionData) {
    const sessionId = sessionData.sessionId || this.generateSessionId();
    
    const session = {
      id: sessionId,
      userId: sessionData.userId,
      
      // Session metadata
      startTime: new Date(),
      endTime: null,
      duration: 0,
      isActive: true,
      
      // Device and location
      userAgent: sessionData.userAgent,
      ip: sessionData.ip,
      deviceFingerprint: sessionData.deviceFingerprint,
      device: sessionData.device || this.parseDevice(sessionData.userAgent),
      location: sessionData.location || this.parseLocation(sessionData.ip),
      
      // Authentication
      authMethod: sessionData.authMethod,
      mfaUsed: sessionData.mfaUsed || false,
      riskScore: sessionData.riskScore || 0,
      
      // Activity counters
      eventCount: 0,
      pageViews: 0,
      actions: 0,
      errors: 0,
      
      // User interaction
      mouseClicks: 0,
      keystrokes: 0,
      scrollDistance: 0,
      timeActive: 0,
      timeIdle: 0,
      
      // Navigation
      landingPage: sessionData.landingPage,
      exitPage: null,
      pagesVisited: new Set(),
      referrer: sessionData.referrer,
      
      // Performance
      loadTime: sessionData.loadTime || 0,
      
      // Custom attributes
      attributes: sessionData.attributes || {},
      
      // Events
      events: []
    };
    
    this.sessions.set(sessionId, session);
    
    // Track user sessions
    if (session.userId) {
      this.trackUserSession(session.userId, sessionId);
    }
    
    // Update real-time metrics
    if (this.options.enableRealTimeMetrics) {
      this.updateRealTimeMetrics('sessions_started', 1);
      this.updateRealTimeMetrics('active_sessions', 1);
    }
    
    this.emit('sessionStarted', session);
    
    return session;
  }

  async endSession(sessionId, endData = {}) {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    
    const endTime = new Date();
    session.endTime = endTime;
    session.duration = endTime.getTime() - session.startTime.getTime();
    session.isActive = false;
    session.exitPage = endData.exitPage || session.exitPage;
    
    // Calculate engagement metrics
    session.engagementScore = this.calculateEngagementScore(session);
    session.bounceRate = this.calculateBounceRate(session);
    
    this.sessions.set(sessionId, session);
    
    // Update real-time metrics
    if (this.options.enableRealTimeMetrics) {
      this.updateRealTimeMetrics('sessions_ended', 1);
      this.updateRealTimeMetrics('active_sessions', -1);
      this.updateRealTimeMetrics('avg_session_duration', session.duration);
    }
    
    this.emit('sessionEnded', session);
    
    return session;
  }

  async trackEvent(sessionId, eventData) {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    
    if (session.events.length >= this.options.maxEventsPerSession) {
      return null; // Prevent memory issues
    }
    
    const event = {
      id: this.generateEventId(),
      sessionId,
      userId: session.userId,
      
      // Event details
      type: eventData.type,
      category: eventData.category,
      action: eventData.action,
      label: eventData.label,
      value: eventData.value,
      
      // Context
      page: eventData.page,
      url: eventData.url,
      referrer: eventData.referrer,
      
      // User interaction
      mousePosition: eventData.mousePosition,
      clickTarget: eventData.clickTarget,
      keyPressed: eventData.keyPressed,
      
      // Timing
      timestamp: new Date(),
      timeInSession: Date.now() - session.startTime.getTime(),
      
      // Performance
      loadTime: eventData.loadTime,
      renderTime: eventData.renderTime,
      
      // Custom data
      properties: eventData.properties || {},
      
      // Technical details
      userAgent: session.userAgent,
      ip: session.ip,
      device: session.device,
      location: session.location
    };
    
    // Store event
    this.events.set(event.id, event);
    session.events.push(event.id);
    
    // Update session counters
    session.eventCount++;
    session.lastActivityAt = event.timestamp;
    
    if (eventData.type === 'page_view') {
      session.pageViews++;
      session.pagesVisited.add(eventData.page);
    } else if (eventData.type === 'action') {
      session.actions++;
    } else if (eventData.type === 'error') {
      session.errors++;
    }
    
    // Track user interactions
    if (eventData.type === 'click') {
      session.mouseClicks++;
    } else if (eventData.type === 'keypress') {
      session.keystrokes++;
    } else if (eventData.type === 'scroll') {
      session.scrollDistance += eventData.scrollDelta || 0;
    }
    
    this.sessions.set(sessionId, session);
    
    // Update real-time metrics
    if (this.options.enableRealTimeMetrics) {
      this.updateRealTimeMetrics('total_events', 1);
      this.updateRealTimeMetrics(`events_${eventData.type}`, 1);
    }
    
    this.emit('eventTracked', event);
    
    return event;
  }

  // User Analytics
  async trackUserActivity(userId, activityData) {
    let userMetrics = this.userSessions.get(userId);
    
    if (!userMetrics) {
      userMetrics = this.createUserMetrics(userId);
    }
    
    // Update user activity
    userMetrics.lastActivityAt = new Date();
    userMetrics.totalSessions = this.getUserSessionCount(userId);
    userMetrics.totalEvents = this.getUserEventCount(userId);
    
    // Track activity patterns
    const hour = new Date().getHours();
    const day = new Date().getDay();
    
    userMetrics.activityHours[hour]++;
    userMetrics.activityDays[day]++;
    
    // Update user attributes
    if (activityData.location) {
      userMetrics.locations.add(JSON.stringify(activityData.location));
    }
    
    if (activityData.device) {
      userMetrics.devices.add(JSON.stringify(activityData.device));
    }
    
    this.userSessions.set(userId, userMetrics);
    
    this.emit('userActivityTracked', { userId, activity: activityData });
    
    return userMetrics;
  }

  createUserMetrics(userId) {
    return {
      userId,
      
      // Session metrics
      totalSessions: 0,
      totalEvents: 0,
      avgSessionDuration: 0,
      avgEventsPerSession: 0,
      
      // Engagement
      totalTimeSpent: 0,
      bounceRate: 0,
      returnRate: 0,
      
      // Activity patterns
      activityHours: new Array(24).fill(0),
      activityDays: new Array(7).fill(0),
      
      // Device and location
      devices: new Set(),
      locations: new Set(),
      
      // Cohort data
      firstSeenAt: new Date(),
      lastActivityAt: new Date(),
      daysSinceFirstSeen: 0,
      
      // Custom metrics
      customEvents: new Map(),
      customProperties: new Map(),
      
      createdAt: new Date(),
      updatedAt: new Date()
    };
  }

  // Cohort Analysis
  async createCohort(cohortData) {
    const cohortId = cohortData.id || this.generateCohortId();
    
    const cohort = {
      id: cohortId,
      name: cohortData.name,
      description: cohortData.description,
      
      // Cohort definition
      criteria: cohortData.criteria,
      timeframe: cohortData.timeframe,
      
      // Users in cohort
      users: new Set(),
      userCount: 0,
      
      // Metrics
      retentionRates: {},
      churnRates: {},
      ltv: 0, // Lifetime value
      
      // Activity metrics
      avgSessionsPerUser: 0,
      avgEventsPerUser: 0,
      avgTimePerUser: 0,
      
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    // Populate cohort with users matching criteria
    await this.populateCohort(cohort);
    
    this.cohortData.set(cohortId, cohort);
    
    this.emit('cohortCreated', cohort);
    
    return cohort;
  }

  async populateCohort(cohort) {
    for (const [userId, userMetrics] of this.userSessions) {
      if (this.userMatchesCohortCriteria(userMetrics, cohort.criteria)) {
        cohort.users.add(userId);
      }
    }
    
    cohort.userCount = cohort.users.size;
    
    // Calculate cohort metrics
    await this.calculateCohortMetrics(cohort);
  }

  userMatchesCohortCriteria(userMetrics, criteria) {
    // Date range criteria
    if (criteria.dateRange) {
      const userDate = userMetrics.firstSeenAt;
      if (userDate < criteria.dateRange.start || userDate > criteria.dateRange.end) {
        return false;
      }
    }
    
    // Activity criteria
    if (criteria.minSessions && userMetrics.totalSessions < criteria.minSessions) {
      return false;
    }
    
    if (criteria.maxSessions && userMetrics.totalSessions > criteria.maxSessions) {
      return false;
    }
    
    // Device criteria
    if (criteria.deviceType) {
      const userDevices = Array.from(userMetrics.devices).map(d => JSON.parse(d));
      if (!userDevices.some(device => device.type === criteria.deviceType)) {
        return false;
      }
    }
    
    // Location criteria
    if (criteria.country) {
      const userLocations = Array.from(userMetrics.locations).map(l => JSON.parse(l));
      if (!userLocations.some(location => location.country === criteria.country)) {
        return false;
      }
    }
    
    return true;
  }

  async calculateCohortMetrics(cohort) {
    let totalSessions = 0;
    let totalEvents = 0;
    let totalTime = 0;
    
    for (const userId of cohort.users) {
      const userMetrics = this.userSessions.get(userId);
      if (userMetrics) {
        totalSessions += userMetrics.totalSessions;
        totalEvents += userMetrics.totalEvents;
        totalTime += userMetrics.totalTimeSpent;
      }
    }
    
    if (cohort.userCount > 0) {
      cohort.avgSessionsPerUser = totalSessions / cohort.userCount;
      cohort.avgEventsPerUser = totalEvents / cohort.userCount;
      cohort.avgTimePerUser = totalTime / cohort.userCount;
    }
    
    // Calculate retention rates
    await this.calculateRetentionRates(cohort);
  }

  async calculateRetentionRates(cohort) {
    const retentionPeriods = [1, 7, 14, 30, 60, 90]; // days
    
    for (const period of retentionPeriods) {
      const retainedUsers = this.getUsersActiveInPeriod(cohort.users, period);
      cohort.retentionRates[`day_${period}`] = 
        cohort.userCount > 0 ? retainedUsers / cohort.userCount : 0;
    }
  }

  getUsersActiveInPeriod(userIds, daysAgo) {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysAgo);
    
    let activeCount = 0;
    
    for (const userId of userIds) {
      const userMetrics = this.userSessions.get(userId);
      if (userMetrics && userMetrics.lastActivityAt >= cutoffDate) {
        activeCount++;
      }
    }
    
    return activeCount;
  }

  // Funnel Analysis
  async createFunnel(funnelData) {
    const funnelId = funnelData.id || this.generateFunnelId();
    
    const funnel = {
      id: funnelId,
      name: funnelData.name,
      description: funnelData.description,
      
      // Funnel steps
      steps: funnelData.steps, // Array of step definitions
      
      // Analysis results
      conversionRates: {},
      dropoffRates: {},
      averageTimeToConvert: {},
      
      // Segmentation
      segments: new Map(),
      
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    // Analyze funnel
    await this.analyzeFunnel(funnel);
    
    this.funnelData.set(funnelId, funnel);
    
    this.emit('funnelCreated', funnel);
    
    return funnel;
  }

  async analyzeFunnel(funnel) {
    const stepResults = [];
    
    for (let i = 0; i < funnel.steps.length; i++) {
      const step = funnel.steps[i];
      const users = this.getUsersCompletingStep(step);
      
      stepResults.push({
        step: i,
        name: step.name,
        users: users.size,
        userIds: users
      });
    }
    
    // Calculate conversion rates
    for (let i = 1; i < stepResults.length; i++) {
      const currentStep = stepResults[i];
      const previousStep = stepResults[i - 1];
      
      const conversionRate = previousStep.users > 0 
        ? currentStep.users / previousStep.users 
        : 0;
      
      funnel.conversionRates[`step_${i - 1}_to_${i}`] = conversionRate;
      funnel.dropoffRates[`step_${i - 1}_to_${i}`] = 1 - conversionRate;
    }
    
    // Calculate overall conversion rate
    if (stepResults.length > 1) {
      funnel.overallConversionRate = stepResults[0].users > 0 
        ? stepResults[stepResults.length - 1].users / stepResults[0].users 
        : 0;
    }
  }

  getUsersCompletingStep(stepDefinition) {
    const users = new Set();
    
    for (const [eventId, event] of this.events) {
      if (this.eventMatchesStep(event, stepDefinition)) {
        users.add(event.userId);
      }
    }
    
    return users;
  }

  eventMatchesStep(event, stepDefinition) {
    // Match by event type
    if (stepDefinition.eventType && event.type !== stepDefinition.eventType) {
      return false;
    }
    
    // Match by page
    if (stepDefinition.page && event.page !== stepDefinition.page) {
      return false;
    }
    
    // Match by action
    if (stepDefinition.action && event.action !== stepDefinition.action) {
      return false;
    }
    
    // Match by custom properties
    if (stepDefinition.properties) {
      for (const [key, value] of Object.entries(stepDefinition.properties)) {
        if (event.properties[key] !== value) {
          return false;
        }
      }
    }
    
    return true;
  }

  // Real-time Metrics
  updateRealTimeMetrics(metric, value) {
    if (!this.options.enableRealTimeMetrics) {
      return;
    }
    
    const now = Date.now();
    const windowSize = 60000; // 1 minute windows
    const windowKey = Math.floor(now / windowSize);
    
    if (!this.realTimeMetrics.has(metric)) {
      this.realTimeMetrics.set(metric, new Map());
    }
    
    const metricData = this.realTimeMetrics.get(metric);
    const currentValue = metricData.get(windowKey) || 0;
    
    if (metric.startsWith('avg_')) {
      // For averages, we need to track count and sum separately
      const countKey = `${windowKey}_count`;
      const sumKey = `${windowKey}_sum`;
      
      const count = metricData.get(countKey) || 0;
      const sum = metricData.get(sumKey) || 0;
      
      metricData.set(countKey, count + 1);
      metricData.set(sumKey, sum + value);
      metricData.set(windowKey, (sum + value) / (count + 1));
    } else {
      metricData.set(windowKey, currentValue + value);
    }
    
    // Clean up old windows (keep last hour)
    const cutoff = windowKey - 60; // 60 minutes ago
    for (const [key] of metricData) {
      if (typeof key === 'number' && key < cutoff) {
        metricData.delete(key);
      }
    }
  }

  getRealTimeMetrics(metric, minutes = 60) {
    if (!this.realTimeMetrics.has(metric)) {
      return [];
    }
    
    const metricData = this.realTimeMetrics.get(metric);
    const windowSize = 60000; // 1 minute
    const now = Date.now();
    const startWindow = Math.floor((now - minutes * 60000) / windowSize);
    const endWindow = Math.floor(now / windowSize);
    
    const results = [];
    
    for (let window = startWindow; window <= endWindow; window++) {
      results.push({
        timestamp: window * windowSize,
        value: metricData.get(window) || 0
      });
    }
    
    return results;
  }

  // Analytics Queries
  async getSessionAnalytics(filters = {}) {
    let sessions = Array.from(this.sessions.values());
    
    // Apply filters
    sessions = this.filterSessions(sessions, filters);
    
    if (sessions.length === 0) {
      return this.getEmptyAnalytics();
    }
    
    // Calculate metrics
    const totalSessions = sessions.length;
    const activeSessions = sessions.filter(s => s.isActive).length;
    const totalDuration = sessions.reduce((sum, s) => sum + s.duration, 0);
    const totalPageViews = sessions.reduce((sum, s) => sum + s.pageViews, 0);
    const totalEvents = sessions.reduce((sum, s) => sum + s.eventCount, 0);
    const bouncedSessions = sessions.filter(s => s.bounceRate === 1).length;
    
    const analytics = {
      totalSessions,
      activeSessions,
      avgSessionDuration: totalSessions > 0 ? totalDuration / totalSessions : 0,
      avgPageViewsPerSession: totalSessions > 0 ? totalPageViews / totalSessions : 0,
      avgEventsPerSession: totalSessions > 0 ? totalEvents / totalSessions : 0,
      bounceRate: totalSessions > 0 ? bouncedSessions / totalSessions : 0,
      
      // Device breakdown
      deviceAnalytics: this.options.enableDeviceAnalytics 
        ? this.analyzeDevices(sessions) 
        : null,
      
      // Geographic breakdown
      geoAnalytics: this.options.enableGeoAnalytics 
        ? this.analyzeGeography(sessions) 
        : null,
      
      // Time-based analysis
      timeAnalytics: this.analyzeTimePatterns(sessions),
      
      // Traffic sources
      trafficSources: this.analyzeTrafficSources(sessions),
      
      // Top pages
      topPages: this.analyzeTopPages(sessions)
    };
    
    return analytics;
  }

  filterSessions(sessions, filters) {
    if (filters.startDate) {
      sessions = sessions.filter(s => s.startTime >= new Date(filters.startDate));
    }
    
    if (filters.endDate) {
      sessions = sessions.filter(s => s.startTime <= new Date(filters.endDate));
    }
    
    if (filters.userId) {
      sessions = sessions.filter(s => s.userId === filters.userId);
    }
    
    if (filters.deviceType) {
      sessions = sessions.filter(s => s.device && s.device.type === filters.deviceType);
    }
    
    if (filters.country) {
      sessions = sessions.filter(s => s.location && s.location.country === filters.country);
    }
    
    if (filters.minDuration) {
      sessions = sessions.filter(s => s.duration >= filters.minDuration);
    }
    
    if (filters.maxDuration) {
      sessions = sessions.filter(s => s.duration <= filters.maxDuration);
    }
    
    return sessions;
  }

  analyzeDevices(sessions) {
    const devices = {};
    const browsers = {};
    const os = {};
    
    sessions.forEach(session => {
      if (session.device) {
        // Device types
        const deviceType = session.device.type || 'unknown';
        devices[deviceType] = (devices[deviceType] || 0) + 1;
        
        // Browsers
        const browser = session.device.browser || 'unknown';
        browsers[browser] = (browsers[browser] || 0) + 1;
        
        // Operating systems
        const osName = session.device.os || 'unknown';
        os[osName] = (os[osName] || 0) + 1;
      }
    });
    
    return { devices, browsers, os };
  }

  analyzeGeography(sessions) {
    const countries = {};
    const cities = {};
    const timezones = {};
    
    sessions.forEach(session => {
      if (session.location) {
        // Countries
        const country = session.location.country || 'unknown';
        countries[country] = (countries[country] || 0) + 1;
        
        // Cities
        const city = session.location.city || 'unknown';
        cities[city] = (cities[city] || 0) + 1;
        
        // Timezones
        const timezone = session.location.timezone || 'unknown';
        timezones[timezone] = (timezones[timezone] || 0) + 1;
      }
    });
    
    return { countries, cities, timezones };
  }

  analyzeTimePatterns(sessions) {
    const hourlyPattern = new Array(24).fill(0);
    const dailyPattern = new Array(7).fill(0);
    const monthlyPattern = new Array(12).fill(0);
    
    sessions.forEach(session => {
      const startTime = session.startTime;
      
      hourlyPattern[startTime.getHours()]++;
      dailyPattern[startTime.getDay()]++;
      monthlyPattern[startTime.getMonth()]++;
    });
    
    return {
      hourly: hourlyPattern,
      daily: dailyPattern,
      monthly: monthlyPattern
    };
  }

  analyzeTrafficSources(sessions) {
    const sources = {};
    const referrers = {};
    
    sessions.forEach(session => {
      // Traffic sources (derived from referrer)
      let source = 'direct';
      
      if (session.referrer) {
        if (session.referrer.includes('google')) {
          source = 'google';
        } else if (session.referrer.includes('facebook')) {
          source = 'facebook';
        } else if (session.referrer.includes('twitter')) {
          source = 'twitter';
        } else {
          source = 'referral';
        }
      }
      
      sources[source] = (sources[source] || 0) + 1;
      
      // Top referrers
      const referrer = session.referrer || 'direct';
      referrers[referrer] = (referrers[referrer] || 0) + 1;
    });
    
    return { sources, referrers };
  }

  analyzeTopPages(sessions) {
    const landingPages = {};
    const exitPages = {};
    const pagesVisited = {};
    
    sessions.forEach(session => {
      // Landing pages
      if (session.landingPage) {
        landingPages[session.landingPage] = (landingPages[session.landingPage] || 0) + 1;
      }
      
      // Exit pages
      if (session.exitPage) {
        exitPages[session.exitPage] = (exitPages[session.exitPage] || 0) + 1;
      }
      
      // All pages visited
      session.pagesVisited.forEach(page => {
        pagesVisited[page] = (pagesVisited[page] || 0) + 1;
      });
    });
    
    return {
      landing: this.sortAndLimit(landingPages, 10),
      exit: this.sortAndLimit(exitPages, 10),
      visited: this.sortAndLimit(pagesVisited, 10)
    };
  }

  // Engagement Metrics
  calculateEngagementScore(session) {
    let score = 0;
    
    // Duration score (up to 40 points)
    const durationMinutes = session.duration / 60000;
    score += Math.min(40, durationMinutes * 2);
    
    // Page views score (up to 30 points)
    score += Math.min(30, session.pageViews * 5);
    
    // Interactions score (up to 20 points)
    const totalInteractions = session.mouseClicks + session.keystrokes + session.actions;
    score += Math.min(20, totalInteractions * 0.5);
    
    // Return visit bonus (10 points)
    if (this.isReturnUser(session.userId)) {
      score += 10;
    }
    
    return Math.min(100, score);
  }

  calculateBounceRate(session) {
    // Single page visit with short duration is considered a bounce
    return session.pageViews <= 1 && session.duration < 30000 ? 1 : 0;
  }

  isReturnUser(userId) {
    if (!userId) return false;
    
    const userSessions = Array.from(this.sessions.values())
      .filter(s => s.userId === userId);
    
    return userSessions.length > 1;
  }

  // Utility Methods
  trackUserSession(userId, sessionId) {
    if (!this.userSessions.has(userId)) {
      this.createUserMetrics(userId);
    }
    
    const userMetrics = this.userSessions.get(userId);
    userMetrics.sessionIds = userMetrics.sessionIds || new Set();
    userMetrics.sessionIds.add(sessionId);
  }

  getUserSessionCount(userId) {
    return Array.from(this.sessions.values())
      .filter(s => s.userId === userId).length;
  }

  getUserEventCount(userId) {
    return Array.from(this.events.values())
      .filter(e => e.userId === userId).length;
  }

  parseDevice(userAgent) {
    // Simplified device parsing
    const device = {
      type: 'desktop',
      browser: 'unknown',
      os: 'unknown'
    };
    
    if (userAgent) {
      if (/Mobile|Android|iPhone|iPad/.test(userAgent)) {
        device.type = 'mobile';
      } else if (/Tablet|iPad/.test(userAgent)) {
        device.type = 'tablet';
      }
      
      if (/Chrome/.test(userAgent)) {
        device.browser = 'Chrome';
      } else if (/Firefox/.test(userAgent)) {
        device.browser = 'Firefox';
      } else if (/Safari/.test(userAgent)) {
        device.browser = 'Safari';
      } else if (/Edge/.test(userAgent)) {
        device.browser = 'Edge';
      }
      
      if (/Windows/.test(userAgent)) {
        device.os = 'Windows';
      } else if (/Mac/.test(userAgent)) {
        device.os = 'macOS';
      } else if (/Linux/.test(userAgent)) {
        device.os = 'Linux';
      } else if (/Android/.test(userAgent)) {
        device.os = 'Android';
      } else if (/iOS/.test(userAgent)) {
        device.os = 'iOS';
      }
    }
    
    return device;
  }

  parseLocation(ip) {
    // This would integrate with a geolocation service
    return {
      country: 'US',
      city: 'Unknown',
      timezone: 'UTC'
    };
  }

  generateSessionId() {
    return `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  generateEventId() {
    return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  generateCohortId() {
    return `cohort_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  generateFunnelId() {
    return `funnel_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  sortAndLimit(object, limit) {
    return Object.entries(object)
      .sort(([,a], [,b]) => b - a)
      .slice(0, limit)
      .reduce((acc, [key, value]) => {
        acc[key] = value;
        return acc;
      }, {});
  }

  getEmptyAnalytics() {
    return {
      totalSessions: 0,
      activeSessions: 0,
      avgSessionDuration: 0,
      avgPageViewsPerSession: 0,
      avgEventsPerSession: 0,
      bounceRate: 0,
      deviceAnalytics: null,
      geoAnalytics: null,
      timeAnalytics: {
        hourly: new Array(24).fill(0),
        daily: new Array(7).fill(0),
        monthly: new Array(12).fill(0)
      },
      trafficSources: { sources: {}, referrers: {} },
      topPages: { landing: {}, exit: {}, visited: {} }
    };
  }

  // Aggregation and Retention
  setupAggregationInterval() {
    setInterval(() => {
      this.aggregateMetrics();
    }, this.options.aggregationInterval);
  }

  setupRetentionCleanup() {
    setInterval(() => {
      this.cleanupOldData();
    }, 24 * 60 * 60 * 1000); // Daily cleanup
  }

  aggregateMetrics() {
    const now = new Date();
    const hourKey = `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}-${now.getHours()}`;
    
    const hourlyMetrics = {
      timestamp: now,
      totalSessions: this.sessions.size,
      activeSession s: Array.from(this.sessions.values()).filter(s => s.isActive).length,
      totalEvents: this.events.size,
      uniqueUsers: new Set(Array.from(this.sessions.values()).map(s => s.userId).filter(Boolean)).size
    };
    
    this.aggregatedMetrics.set(hourKey, hourlyMetrics);
  }

  cleanupOldData() {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - this.options.retentionDays);
    
    // Clean up old sessions
    for (const [sessionId, session] of this.sessions) {
      if (session.startTime < cutoff) {
        this.sessions.delete(sessionId);
      }
    }
    
    // Clean up old events
    for (const [eventId, event] of this.events) {
      if (event.timestamp < cutoff) {
        this.events.delete(eventId);
      }
    }
    
    // Clean up old aggregated metrics
    for (const [key, metrics] of this.aggregatedMetrics) {
      if (metrics.timestamp < cutoff) {
        this.aggregatedMetrics.delete(key);
      }
    }
  }

  // Statistics and Monitoring
  getStats() {
    return {
      totalSessions: this.sessions.size,
      totalEvents: this.events.size,
      totalUsers: this.userSessions.size,
      activeSessions: Array.from(this.sessions.values()).filter(s => s.isActive).length,
      cohorts: this.cohortData.size,
      funnels: this.funnelData.size,
      aggregatedMetrics: this.aggregatedMetrics.size
    };
  }

  reset() {
    this.sessions.clear();
    this.events.clear();
    this.userSessions.clear();
    this.aggregatedMetrics.clear();
    this.realTimeMetrics.clear();
    this.cohortData.clear();
    this.funnelData.clear();
  }
}

module.exports = SessionAnalytics;