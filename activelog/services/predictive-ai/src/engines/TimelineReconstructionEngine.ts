import { UserAction, TemporalCluster } from '../types';
import { RelationshipMappingEngine } from './RelationshipMappingEngine';
import { v4 as uuidv4 } from 'uuid';
import { 
  differenceInMinutes, 
  differenceInHours, 
  differenceInDays,
  startOfDay,
  endOfDay,
  format,
  parseISO,
  isWithinInterval
} from 'date-fns';
import { groupBy, orderBy, sortBy } from 'lodash';

export class TimelineReconstructionEngine {
  private relationshipEngine: RelationshipMappingEngine;
  private userTimelines: Map<string, Timeline> = new Map();
  private eventSignatureCache: Map<string, EventSignature[]> = new Map();

  constructor(relationshipEngine: RelationshipMappingEngine) {
    this.relationshipEngine = relationshipEngine;
  }

  async reconstructTimeline(
    userId: string,
    actions: UserAction[],
    timeRange?: { start: Date; end: Date }
  ): Promise<Timeline> {
    // Filter actions by time range if provided
    let filteredActions = actions;
    if (timeRange) {
      filteredActions = actions.filter(action =>
        isWithinInterval(new Date(action.timestamp), timeRange)
      );
    }
    
    // Sort actions chronologically
    const sortedActions = orderBy(filteredActions, 'timestamp');
    
    // Identify significant events and sessions
    const events = await this.identifySignificantEvents(userId, sortedActions);
    const sessions = await this.identifyWorkSessions(userId, sortedActions);
    const patterns = await this.identifyTemporalPatterns(userId, sortedActions);
    const gaps = await this.identifyDataGaps(userId, sortedActions);
    
    // Build narrative structure
    const narrative = await this.buildNarrative(userId, events, sessions);
    
    const timeline: Timeline = {
      id: uuidv4(),
      userId,
      startTime: sortedActions[0]?.timestamp || new Date(),
      endTime: sortedActions[sortedActions.length - 1]?.timestamp || new Date(),
      events,
      sessions,
      patterns,
      gaps,
      narrative,
      confidence: this.calculateTimelineConfidence(events, sessions, gaps)
    };
    
    this.userTimelines.set(userId, timeline);
    return timeline;
  }

  async identifyWorkSessions(userId: string, actions: UserAction[]): Promise<WorkSession[]> {
    if (actions.length === 0) return [];
    
    const sessions: WorkSession[] = [];
    let currentSession: Partial<WorkSession> = {};
    const sessionGapMinutes = 30; // Break sessions if no activity for 30 minutes
    
    for (let i = 0; i < actions.length; i++) {
      const action = actions[i];
      const actionTime = new Date(action.timestamp);
      
      // Start new session if no current session or large time gap
      if (!currentSession.startTime || 
          differenceInMinutes(actionTime, new Date(currentSession.endTime!)) > sessionGapMinutes) {
        
        // Save previous session if exists
        if (currentSession.startTime) {
          sessions.push(this.finalizeSession(currentSession as WorkSession));
        }
        
        // Start new session
        currentSession = {
          id: uuidv4(),
          userId,
          startTime: action.timestamp,
          endTime: action.timestamp,
          actions: [action],
          primaryActivity: action.actionType,
          focusAreas: [this.extractFocusArea(action.resourcePath)],
          productivity: 0,
          context: action.context
        };
      } else {
        // Extend current session
        currentSession.endTime = action.timestamp;
        currentSession.actions!.push(action);
        
        const focusArea = this.extractFocusArea(action.resourcePath);
        if (!currentSession.focusAreas!.includes(focusArea)) {
          currentSession.focusAreas!.push(focusArea);
        }
      }
    }
    
    // Finalize last session
    if (currentSession.startTime) {
      sessions.push(this.finalizeSession(currentSession as WorkSession));
    }
    
    return sessions.filter(s => s.duration >= 5); // Filter out very short sessions
  }

  async identifySignificantEvents(userId: string, actions: UserAction[]): Promise<TimelineEvent[]> {
    const events: TimelineEvent[] = [];
    
    // Project start/completion events
    events.push(...await this.identifyProjectEvents(userId, actions));
    
    // Collaboration events
    events.push(...await this.identifyCollaborationEvents(userId, actions));
    
    // Major file operations
    events.push(...await this.identifyMajorFileEvents(userId, actions));
    
    // Context changes (location, device changes)
    events.push(...await this.identifyContextChangeEvents(userId, actions));
    
    // Milestone achievements
    events.push(...await this.identifyMilestoneEvents(userId, actions));
    
    return orderBy(events, 'timestamp');
  }

  async identifyTemporalPatterns(userId: string, actions: UserAction[]): Promise<TemporalPattern[]> {
    const patterns: TemporalPattern[] = [];
    
    // Daily patterns
    patterns.push(...this.identifyDailyPatterns(actions));
    
    // Weekly patterns
    patterns.push(...this.identifyWeeklyPatterns(actions));
    
    // Seasonal patterns
    patterns.push(...this.identifySeasonalPatterns(actions));
    
    // Recurring events
    patterns.push(...this.identifyRecurringPatterns(actions));
    
    return patterns.filter(p => p.confidence > 0.3);
  }

  async identifyDataGaps(userId: string, actions: UserAction[]): Promise<DataGap[]> {
    const gaps: DataGap[] = [];
    const sortedActions = orderBy(actions, 'timestamp');
    
    for (let i = 1; i < sortedActions.length; i++) {
      const previousAction = sortedActions[i - 1];
      const currentAction = sortedActions[i];
      
      const gapMinutes = differenceInMinutes(
        new Date(currentAction.timestamp),
        new Date(previousAction.timestamp)
      );
      
      // Identify significant gaps (more than 2 hours during business hours)
      const isBusinessHour = (time: Date) => {
        const hour = time.getHours();
        const day = time.getDay();
        return day >= 1 && day <= 5 && hour >= 9 && hour <= 17;
      };
      
      const shouldBeActive = isBusinessHour(new Date(previousAction.timestamp)) ||
                            isBusinessHour(new Date(currentAction.timestamp));
      
      if (gapMinutes > (shouldBeActive ? 120 : 480)) { // 2 hours or 8 hours
        gaps.push({
          id: uuidv4(),
          startTime: previousAction.timestamp,
          endTime: currentAction.timestamp,
          duration: gapMinutes,
          type: this.classifyGapType(gapMinutes, previousAction, currentAction),
          confidence: this.calculateGapConfidence(gapMinutes, shouldBeActive),
          possibleReasons: this.inferGapReasons(gapMinutes, previousAction, currentAction),
          contextBefore: previousAction.context,
          contextAfter: currentAction.context
        });
      }
    }
    
    return gaps;
  }

  async buildNarrative(
    userId: string,
    events: TimelineEvent[],
    sessions: WorkSession[]
  ): Promise<TimelineNarrative> {
    const sortedEvents = orderBy(events, 'timestamp');
    const chapters: NarrativeChapter[] = [];
    
    // Group events into logical chapters (by day or major event clusters)
    const eventsByDay = groupBy(sortedEvents, event => 
      format(new Date(event.timestamp), 'yyyy-MM-dd')
    );
    
    for (const [date, dayEvents] of Object.entries(eventsByDay)) {
      const daySessions = sessions.filter(session =>
        format(new Date(session.startTime), 'yyyy-MM-dd') === date
      );
      
      const chapter: NarrativeChapter = {
        id: uuidv4(),
        title: this.generateChapterTitle(date, dayEvents),
        date: parseISO(date),
        summary: this.generateDaySummary(dayEvents, daySessions),
        keyEvents: dayEvents.slice(0, 5), // Top 5 events
        sessions: daySessions,
        themes: this.extractDayThemes(dayEvents, daySessions),
        mood: this.inferDayMood(dayEvents, daySessions)
      };
      
      chapters.push(chapter);
    }
    
    return {
      id: uuidv4(),
      userId,
      title: this.generateTimelineTitle(events, sessions),
      overview: this.generateTimelineOverview(events, sessions),
      chapters: orderBy(chapters, 'date'),
      keyInsights: this.extractKeyInsights(events, sessions),
      emotionalArc: this.buildEmotionalArc(chapters)
    };
  }

  async getTimelineForPeriod(
    userId: string,
    start: Date,
    end: Date
  ): Promise<Timeline | null> {
    const existingTimeline = this.userTimelines.get(userId);
    
    if (existingTimeline && 
        new Date(existingTimeline.startTime) <= start &&
        new Date(existingTimeline.endTime) >= end) {
      
      // Filter existing timeline to requested period
      return this.filterTimelineToPeriod(existingTimeline, start, end);
    }
    
    return null; // Would need to reconstruct from actions
  }

  private async identifyProjectEvents(userId: string, actions: UserAction[]): Promise<TimelineEvent[]> {
    const events: TimelineEvent[] = [];
    const projectActions = actions.filter(a => 
      a.resourcePath.toLowerCase().includes('project') ||
      a.actionType === 'folder_create' && a.resourcePath.split('/').length <= 3
    );
    
    // Group by project path
    const projectGroups = groupBy(projectActions, a => 
      a.resourcePath.split('/').slice(0, 3).join('/')
    );
    
    for (const [projectPath, projectActionsList] of Object.entries(projectGroups)) {
      const sortedProjectActions = orderBy(projectActionsList, 'timestamp');
      const firstAction = sortedProjectActions[0];
      const lastAction = sortedProjectActions[sortedProjectActions.length - 1];
      
      // Project start event
      if (firstAction.actionType === 'folder_create') {
        events.push({
          id: uuidv4(),
          timestamp: firstAction.timestamp,
          type: 'project_start',
          title: `Started project: ${this.extractProjectName(projectPath)}`,
          description: `Initiated new project with folder creation`,
          importance: 0.8,
          relatedActions: [firstAction.id],
          tags: ['project', 'start'],
          context: firstAction.context
        });
      }
      
      // Check for project completion indicators
      const hasCompleteIndicators = projectActionsList.some(a =>
        a.resourcePath.toLowerCase().includes('final') ||
        a.resourcePath.toLowerCase().includes('complete') ||
        a.resourcePath.toLowerCase().includes('done')
      );
      
      if (hasCompleteIndicators) {
        events.push({
          id: uuidv4(),
          timestamp: lastAction.timestamp,
          type: 'project_completion',
          title: `Completed project: ${this.extractProjectName(projectPath)}`,
          description: `Project appears to have reached completion`,
          importance: 0.9,
          relatedActions: projectActionsList.map(a => a.id).slice(-5),
          tags: ['project', 'completion'],
          context: lastAction.context
        });
      }
    }
    
    return events;
  }

  private async identifyCollaborationEvents(userId: string, actions: UserAction[]): Promise<TimelineEvent[]> {
    const events: TimelineEvent[] = [];
    const collaborationActions = actions.filter(a => 
      a.metadata?.collaborators || 
      a.actionType === 'share' ||
      a.resourcePath.toLowerCase().includes('shared')
    );
    
    for (const action of collaborationActions) {
      events.push({
        id: uuidv4(),
        timestamp: action.timestamp,
        type: 'collaboration',
        title: 'Collaboration activity',
        description: `${action.actionType} involving ${action.metadata?.collaborators?.join(', ') || 'others'}`,
        importance: 0.6,
        relatedActions: [action.id],
        tags: ['collaboration', 'social'],
        context: action.context
      });
    }
    
    return events;
  }

  private async identifyMajorFileEvents(userId: string, actions: UserAction[]): Promise<TimelineEvent[]> {
    const events: TimelineEvent[] = [];
    
    // Large operations or significant file movements
    const majorActions = actions.filter(a => {
      const isLargeOperation = (a.metadata?.fileCount && a.metadata.fileCount > 10) ||
                              (a.metadata?.size && a.metadata.size > 100 * 1024 * 1024); // 100MB
      
      const isSignificantPath = a.resourcePath.toLowerCase().includes('backup') ||
                               a.resourcePath.toLowerCase().includes('archive') ||
                               a.resourcePath.toLowerCase().includes('important');
      
      return isLargeOperation || isSignificantPath || a.actionType === 'delete';
    });
    
    for (const action of majorActions) {
      events.push({
        id: uuidv4(),
        timestamp: action.timestamp,
        type: 'major_operation',
        title: `Major ${action.actionType} operation`,
        description: this.generateOperationDescription(action),
        importance: 0.7,
        relatedActions: [action.id],
        tags: ['operation', action.actionType],
        context: action.context
      });
    }
    
    return events;
  }

  private async identifyContextChangeEvents(userId: string, actions: UserAction[]): Promise<TimelineEvent[]> {
    const events: TimelineEvent[] = [];
    
    for (let i = 1; i < actions.length; i++) {
      const prevAction = actions[i - 1];
      const currentAction = actions[i];
      
      if (this.hasSignificantContextChange(prevAction.context, currentAction.context)) {
        events.push({
          id: uuidv4(),
          timestamp: currentAction.timestamp,
          type: 'context_change',
          title: 'Context change detected',
          description: this.describeContextChange(prevAction.context, currentAction.context),
          importance: 0.4,
          relatedActions: [currentAction.id],
          tags: ['context', 'environment'],
          context: currentAction.context
        });
      }
    }
    
    return events;
  }

  private async identifyMilestoneEvents(userId: string, actions: UserAction[]): Promise<TimelineEvent[]> {
    const events: TimelineEvent[] = [];
    
    // Look for milestone indicators in paths and metadata
    const milestoneActions = actions.filter(a => {
      const path = a.resourcePath.toLowerCase();
      return path.includes('milestone') ||
             path.includes('release') ||
             path.includes('version') ||
             path.includes('launch') ||
             path.includes('delivery');
    });
    
    for (const action of milestoneActions) {
      events.push({
        id: uuidv4(),
        timestamp: action.timestamp,
        type: 'milestone',
        title: 'Milestone reached',
        description: `Milestone activity: ${action.actionType} on ${action.resourcePath}`,
        importance: 0.85,
        relatedActions: [action.id],
        tags: ['milestone', 'achievement'],
        context: action.context
      });
    }
    
    return events;
  }

  private identifyDailyPatterns(actions: UserAction[]): TemporalPattern[] {
    const patterns: TemporalPattern[] = [];
    
    // Group actions by hour of day
    const hourlyGroups = groupBy(actions, a => new Date(a.timestamp).getHours());
    
    for (const [hour, hourActions] of Object.entries(hourlyGroups)) {
      if (hourActions.length >= 3) { // At least 3 occurrences
        patterns.push({
          id: uuidv4(),
          type: 'daily',
          description: `Regular activity at ${hour}:00`,
          frequency: hourActions.length,
          confidence: Math.min(hourActions.length / 10, 0.9),
          timePattern: { hour: parseInt(hour) },
          commonActions: this.getCommonActionTypes(hourActions),
          strength: hourActions.length / actions.length
        });
      }
    }
    
    return patterns;
  }

  private identifyWeeklyPatterns(actions: UserAction[]): TemporalPattern[] {
    const patterns: TemporalPattern[] = [];
    
    const weekdayGroups = groupBy(actions, a => new Date(a.timestamp).getDay());
    
    for (const [day, dayActions] of Object.entries(weekdayGroups)) {
      if (dayActions.length >= 5) {
        patterns.push({
          id: uuidv4(),
          type: 'weekly',
          description: `Regular ${this.getDayName(parseInt(day))} activity`,
          frequency: dayActions.length,
          confidence: Math.min(dayActions.length / 20, 0.8),
          timePattern: { dayOfWeek: parseInt(day) },
          commonActions: this.getCommonActionTypes(dayActions),
          strength: dayActions.length / actions.length
        });
      }
    }
    
    return patterns;
  }

  private identifySeasonalPatterns(actions: UserAction[]): TemporalPattern[] {
    const patterns: TemporalPattern[] = [];
    
    const monthlyGroups = groupBy(actions, a => new Date(a.timestamp).getMonth());
    
    for (const [month, monthActions] of Object.entries(monthlyGroups)) {
      if (monthActions.length >= 10) {
        const hasSeasonalKeywords = monthActions.some(a =>
          a.resourcePath.toLowerCase().includes('holiday') ||
          a.resourcePath.toLowerCase().includes('tax') ||
          a.resourcePath.toLowerCase().includes('vacation')
        );
        
        if (hasSeasonalKeywords) {
          patterns.push({
            id: uuidv4(),
            type: 'seasonal',
            description: `Seasonal activity in ${this.getMonthName(parseInt(month))}`,
            frequency: monthActions.length,
            confidence: 0.7,
            timePattern: { month: parseInt(month) },
            commonActions: this.getCommonActionTypes(monthActions),
            strength: monthActions.length / actions.length
          });
        }
      }
    }
    
    return patterns;
  }

  private identifyRecurringPatterns(actions: UserAction[]): TemporalPattern[] {
    const patterns: TemporalPattern[] = [];
    
    // Look for recurring file access patterns
    const pathGroups = groupBy(actions, 'resourcePath');
    
    for (const [path, pathActions] of Object.entries(pathGroups)) {
      if (pathActions.length >= 5) {
        const intervals = this.calculateIntervals(pathActions);
        const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
        const consistency = this.calculateIntervalConsistency(intervals);
        
        if (consistency > 0.6) { // High consistency
          patterns.push({
            id: uuidv4(),
            type: 'recurring',
            description: `Recurring access to ${path.split('/').pop()}`,
            frequency: pathActions.length,
            confidence: consistency,
            timePattern: { averageInterval: avgInterval },
            commonActions: [pathActions[0].actionType],
            strength: consistency
          });
        }
      }
    }
    
    return patterns;
  }

  // Helper methods
  private finalizeSession(session: WorkSession): WorkSession {
    const duration = differenceInMinutes(
      new Date(session.endTime),
      new Date(session.startTime)
    );
    
    session.duration = duration;
    session.productivity = this.calculateProductivity(session.actions);
    session.summary = this.generateSessionSummary(session);
    
    return session;
  }

  private extractFocusArea(resourcePath: string): string {
    const parts = resourcePath.split('/').filter(p => p);
    
    // Return the first meaningful directory or file type
    for (const part of parts) {
      if (part !== 'Documents' && part !== 'Files' && part.length > 0) {
        return part;
      }
    }
    
    const extension = resourcePath.split('.').pop();
    return extension || 'general';
  }

  private calculateProductivity(actions: UserAction[]): number {
    const productiveActions = ['file_access', 'folder_create', 'tag_add'];
    const productiveCount = actions.filter(a => 
      productiveActions.includes(a.actionType)
    ).length;
    
    return Math.min(productiveCount / Math.max(actions.length, 1), 1);
  }

  private generateSessionSummary(session: WorkSession): string {
    const duration = session.duration;
    const primaryFocus = session.focusAreas[0] || 'general tasks';
    const actionCount = session.actions.length;
    
    return `${duration} minute session focused on ${primaryFocus} (${actionCount} actions)`;
  }

  private classifyGapType(minutes: number, before: UserAction, after: UserAction): string {
    if (minutes > 480) return 'extended_break'; // 8+ hours
    if (minutes > 120) return 'break'; // 2+ hours
    if (minutes > 60) return 'pause'; // 1+ hour
    return 'short_gap';
  }

  private calculateGapConfidence(minutes: number, shouldBeActive: boolean): number {
    if (!shouldBeActive) return 0.3; // Lower confidence for non-business hours
    if (minutes > 240) return 0.9; // Very confident about 4+ hour gaps
    if (minutes > 120) return 0.7; // Confident about 2+ hour gaps
    return 0.5;
  }

  private inferGapReasons(minutes: number, before: UserAction, after: UserAction): string[] {
    const reasons: string[] = [];
    
    if (minutes > 480) {
      reasons.push('Sleep/overnight break', 'Weekend/holiday');
    } else if (minutes > 240) {
      reasons.push('Extended break', 'Meeting', 'Away from computer');
    } else if (minutes > 120) {
      reasons.push('Lunch break', 'Meeting', 'Other tasks');
    }
    
    // Context-based reasons
    if (before.context?.location !== after.context?.location) {
      reasons.push('Location change');
    }
    
    if (before.context?.deviceType !== after.context?.deviceType) {
      reasons.push('Device switch');
    }
    
    return reasons;
  }

  private calculateTimelineConfidence(
    events: TimelineEvent[],
    sessions: WorkSession[],
    gaps: DataGap[]
  ): number {
    let confidence = 0.8; // Base confidence
    
    // Reduce confidence based on data gaps
    const significantGaps = gaps.filter(g => g.confidence > 0.7).length;
    confidence -= significantGaps * 0.1;
    
    // Increase confidence based on rich event data
    const highImportanceEvents = events.filter(e => e.importance > 0.7).length;
    confidence += Math.min(highImportanceEvents * 0.05, 0.2);
    
    return Math.max(0.1, Math.min(confidence, 1.0));
  }

  private generateChapterTitle(date: string, events: TimelineEvent[]): string {
    const eventTypes = events.map(e => e.type);
    
    if (eventTypes.includes('project_start')) {
      return `Project Initiation - ${date}`;
    }
    if (eventTypes.includes('project_completion')) {
      return `Project Completion - ${date}`;
    }
    if (eventTypes.includes('milestone')) {
      return `Milestone Day - ${date}`;
    }
    
    return `Daily Activities - ${date}`;
  }

  private generateDaySummary(events: TimelineEvent[], sessions: WorkSession[]): string {
    const totalDuration = sessions.reduce((sum, s) => sum + s.duration, 0);
    const mainActivities = events.map(e => e.type).slice(0, 3);
    
    return `${Math.round(totalDuration / 60)} hours of activity with focus on ${mainActivities.join(', ')}`;
  }

  private extractDayThemes(events: TimelineEvent[], sessions: WorkSession[]): string[] {
    const themes = new Set<string>();
    
    events.forEach(e => e.tags.forEach(tag => themes.add(tag)));
    sessions.forEach(s => s.focusAreas.forEach(area => themes.add(area)));
    
    return Array.from(themes).slice(0, 5);
  }

  private inferDayMood(events: TimelineEvent[], sessions: WorkSession[]): string {
    const productivityScore = sessions.reduce((sum, s) => sum + s.productivity, 0) / sessions.length;
    const importanceScore = events.reduce((sum, e) => sum + e.importance, 0) / events.length;
    
    const overallScore = (productivityScore + importanceScore) / 2;
    
    if (overallScore > 0.8) return 'highly_productive';
    if (overallScore > 0.6) return 'productive';
    if (overallScore > 0.4) return 'moderate';
    if (overallScore > 0.2) return 'low_activity';
    return 'minimal';
  }

  private generateTimelineTitle(events: TimelineEvent[], sessions: WorkSession[]): string {
    const projectEvents = events.filter(e => e.type.includes('project'));
    
    if (projectEvents.length > 0) {
      return 'Project Development Timeline';
    }
    
    return 'Activity Timeline';
  }

  private generateTimelineOverview(events: TimelineEvent[], sessions: WorkSession[]): string {
    const totalSessions = sessions.length;
    const totalEvents = events.length;
    const avgProductivity = sessions.reduce((sum, s) => sum + s.productivity, 0) / sessions.length;
    
    return `Timeline contains ${totalSessions} work sessions and ${totalEvents} significant events with average productivity of ${(avgProductivity * 100).toFixed(0)}%`;
  }

  private extractKeyInsights(events: TimelineEvent[], sessions: WorkSession[]): string[] {
    const insights: string[] = [];
    
    // Productivity insights
    const highProductivitySessions = sessions.filter(s => s.productivity > 0.8);
    if (highProductivitySessions.length > sessions.length * 0.3) {
      insights.push('High productivity pattern identified');
    }
    
    // Collaboration insights
    const collaborationEvents = events.filter(e => e.type === 'collaboration');
    if (collaborationEvents.length > 5) {
      insights.push('Strong collaboration activity');
    }
    
    // Project progression insights
    const projectStarts = events.filter(e => e.type === 'project_start');
    const projectCompletions = events.filter(e => e.type === 'project_completion');
    
    if (projectCompletions.length >= projectStarts.length * 0.8) {
      insights.push('High project completion rate');
    }
    
    return insights;
  }

  private buildEmotionalArc(chapters: NarrativeChapter[]): EmotionalPoint[] {
    return chapters.map((chapter, index) => ({
      timestamp: chapter.date,
      mood: chapter.mood,
      intensity: this.calculateMoodIntensity(chapter),
      description: `${chapter.mood} phase with ${chapter.keyEvents.length} key events`
    }));
  }

  private calculateMoodIntensity(chapter: NarrativeChapter): number {
    const eventIntensity = chapter.keyEvents.reduce((sum, e) => sum + e.importance, 0) / chapter.keyEvents.length;
    const sessionIntensity = chapter.sessions.reduce((sum, s) => sum + s.productivity, 0) / chapter.sessions.length;
    
    return (eventIntensity + sessionIntensity) / 2;
  }

  private filterTimelineToPeriod(timeline: Timeline, start: Date, end: Date): Timeline {
    const filteredEvents = timeline.events.filter(e =>
      isWithinInterval(new Date(e.timestamp), { start, end })
    );
    
    const filteredSessions = timeline.sessions.filter(s =>
      isWithinInterval(new Date(s.startTime), { start, end })
    );
    
    return {
      ...timeline,
      id: uuidv4(),
      startTime: start,
      endTime: end,
      events: filteredEvents,
      sessions: filteredSessions,
      narrative: {
        ...timeline.narrative,
        chapters: timeline.narrative.chapters.filter(c =>
          isWithinInterval(c.date, { start, end })
        )
      }
    };
  }

  // Utility methods
  private hasSignificantContextChange(context1: any, context2: any): boolean {
    if (!context1 || !context2) return false;
    
    return context1.location !== context2.location ||
           context1.deviceType !== context2.deviceType;
  }

  private describeContextChange(context1: any, context2: any): string {
    const changes: string[] = [];
    
    if (context1?.location !== context2?.location) {
      changes.push(`location: ${context1?.location || 'unknown'} → ${context2?.location || 'unknown'}`);
    }
    
    if (context1?.deviceType !== context2?.deviceType) {
      changes.push(`device: ${context1?.deviceType || 'unknown'} → ${context2?.deviceType || 'unknown'}`);
    }
    
    return changes.join(', ');
  }

  private extractProjectName(path: string): string {
    return path.split('/').pop() || 'Unknown Project';
  }

  private generateOperationDescription(action: UserAction): string {
    if (action.metadata?.fileCount) {
      return `${action.actionType} operation on ${action.metadata.fileCount} files`;
    }
    
    if (action.metadata?.size) {
      const sizeMB = Math.round(action.metadata.size / (1024 * 1024));
      return `${action.actionType} operation on ${sizeMB}MB of data`;
    }
    
    return `${action.actionType} operation on ${action.resourcePath}`;
  }

  private getCommonActionTypes(actions: UserAction[]): string[] {
    const actionCounts = groupBy(actions, 'actionType');
    return Object.entries(actionCounts)
      .sort(([,a], [,b]) => b.length - a.length)
      .slice(0, 3)
      .map(([actionType]) => actionType);
  }

  private getDayName(dayNumber: number): string {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return days[dayNumber] || 'Unknown';
  }

  private getMonthName(monthNumber: number): string {
    const months = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December'];
    return months[monthNumber] || 'Unknown';
  }

  private calculateIntervals(actions: UserAction[]): number[] {
    const intervals: number[] = [];
    const sortedActions = orderBy(actions, 'timestamp');
    
    for (let i = 1; i < sortedActions.length; i++) {
      const interval = differenceInMinutes(
        new Date(sortedActions[i].timestamp),
        new Date(sortedActions[i - 1].timestamp)
      );
      intervals.push(interval);
    }
    
    return intervals;
  }

  private calculateIntervalConsistency(intervals: number[]): number {
    if (intervals.length < 2) return 0;
    
    const average = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    const variance = intervals.reduce((acc, interval) => 
      acc + Math.pow(interval - average, 2), 0) / intervals.length;
    
    return 1 / (1 + Math.sqrt(variance) / average);
  }
}

// Interface definitions
interface Timeline {
  id: string;
  userId: string;
  startTime: Date;
  endTime: Date;
  events: TimelineEvent[];
  sessions: WorkSession[];
  patterns: TemporalPattern[];
  gaps: DataGap[];
  narrative: TimelineNarrative;
  confidence: number;
}

interface TimelineEvent {
  id: string;
  timestamp: Date;
  type: 'project_start' | 'project_completion' | 'collaboration' | 'major_operation' | 'context_change' | 'milestone';
  title: string;
  description: string;
  importance: number;
  relatedActions: string[];
  tags: string[];
  context?: any;
}

interface WorkSession {
  id: string;
  userId: string;
  startTime: Date;
  endTime: Date;
  duration: number;
  actions: UserAction[];
  primaryActivity: string;
  focusAreas: string[];
  productivity: number;
  summary: string;
  context?: any;
}

interface TemporalPattern {
  id: string;
  type: 'daily' | 'weekly' | 'seasonal' | 'recurring';
  description: string;
  frequency: number;
  confidence: number;
  timePattern: Record<string, any>;
  commonActions: string[];
  strength: number;
}

interface DataGap {
  id: string;
  startTime: Date;
  endTime: Date;
  duration: number;
  type: string;
  confidence: number;
  possibleReasons: string[];
  contextBefore?: any;
  contextAfter?: any;
}

interface TimelineNarrative {
  id: string;
  userId: string;
  title: string;
  overview: string;
  chapters: NarrativeChapter[];
  keyInsights: string[];
  emotionalArc: EmotionalPoint[];
}

interface NarrativeChapter {
  id: string;
  title: string;
  date: Date;
  summary: string;
  keyEvents: TimelineEvent[];
  sessions: WorkSession[];
  themes: string[];
  mood: string;
}

interface EmotionalPoint {
  timestamp: Date;
  mood: string;
  intensity: number;
  description: string;
}