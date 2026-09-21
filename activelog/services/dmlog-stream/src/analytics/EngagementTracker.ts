import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import { ViewerEngagement, ViewerDiceRoll, ViewerPoll, Donation, StreamAnalytics, StreamSession } from '../types';

export interface EngagementEvent {
  userId: string;
  username: string;
  type: 'chat' | 'dice_roll' | 'poll_vote' | 'donation' | 'follow' | 'subscribe' | 'raid' | 'host';
  timestamp: Date;
  data?: any;
  value?: number; // Engagement value weight
}

export interface EngagementStats {
  totalViewers: number;
  activeViewers: number;
  newViewers: number;
  returningViewers: number;
  topChatters: Array<{username: string; messageCount: number}>;
  topDiceRollers: Array<{username: string; rollCount: number}>;
  engagementRate: number;
  retentionRate: number;
  averageSessionTime: number;
  peakEngagement: {timestamp: Date; count: number};
}

export class EngagementTracker extends EventEmitter {
  private session: StreamSession | null = null;
  private viewers: Map<string, ViewerEngagement> = new Map();
  private events: EngagementEvent[] = [];
  private sessionStartTime: Date | null = null;
  private dataPath: string;
  private saveInterval: NodeJS.Timeout | null = null;
  private engagementHistory: Map<string, number[]> = new Map(); // Track engagement over time
  private currentViewerCount: number = 0;
  private peakViewerCount: number = 0;

  constructor(dataPath: string) {
    super();
    this.dataPath = dataPath;
  }

  public async initialize(): Promise<void> {
    try {
      await fs.mkdir(this.dataPath, { recursive: true });
      
      // Start periodic data saving
      this.saveInterval = setInterval(() => {
        this.saveEngagementData();
      }, 30000); // Save every 30 seconds
      
      console.log('📊 Viewer engagement tracker initialized');
      this.emit('initialized');
    } catch (error) {
      console.error('Error initializing engagement tracker:', error);
      throw error;
    }
  }

  public startSession(session: StreamSession): void {
    this.session = session;
    this.sessionStartTime = new Date();
    this.viewers.clear();
    this.events = [];
    this.engagementHistory.clear();
    this.currentViewerCount = 0;
    this.peakViewerCount = 0;
    
    console.log(`📊 Started tracking engagement for: ${session.title}`);
    this.emit('session-started', session);
  }

  public async endSession(): Promise<EngagementStats> {
    if (!this.session) {
      throw new Error('No active session to end');
    }

    const stats = this.generateStats();
    await this.saveSessionData(stats);
    
    console.log('📊 Ended engagement tracking session');
    this.emit('session-ended', stats);
    
    return stats;
  }

  // Viewer lifecycle tracking
  public addViewer(userId: string, username: string, metadata?: any): ViewerEngagement {
    const existingViewer = this.viewers.get(userId);
    
    if (existingViewer) {
      // Returning viewer
      existingViewer.totalTime = this.calculateTotalTime(existingViewer.joinTime);
      return existingViewer;
    }

    // New viewer
    const viewer: ViewerEngagement = {
      userId,
      username,
      joinTime: new Date(),
      totalTime: 0,
      messageCount: 0,
      diceRolls: 0,
      pollVotes: 0,
      donations: 0,
      subscribed: metadata?.subscribed || false,
      follower: metadata?.follower || false,
      moderator: metadata?.moderator || false,
      badges: metadata?.badges || []
    };

    this.viewers.set(userId, viewer);
    this.updateViewerCount(this.viewers.size);
    
    this.trackEvent({
      userId,
      username,
      type: 'follow',
      timestamp: new Date(),
      value: 1
    });

    console.log(`👋 New viewer: ${username}`);
    this.emit('viewer-joined', viewer);
    
    return viewer;
  }

  public removeViewer(userId: string): void {
    const viewer = this.viewers.get(userId);
    if (viewer) {
      viewer.totalTime = this.calculateTotalTime(viewer.joinTime);
      this.updateViewerCount(this.viewers.size - 1);
      
      console.log(`👋 Viewer left: ${viewer.username} (${Math.round(viewer.totalTime / 60000)}m)`);
      this.emit('viewer-left', viewer);
    }
  }

  private updateViewerCount(count: number): void {
    this.currentViewerCount = count;
    this.peakViewerCount = Math.max(this.peakViewerCount, count);
    
    // Track engagement over time (every minute)
    const minute = Math.floor(Date.now() / 60000);
    if (!this.engagementHistory.has(minute.toString())) {
      this.engagementHistory.set(minute.toString(), [count, 0, 0, 0]); // [viewers, messages, dice, polls]
    }
  }

  // Event tracking methods
  public trackChatMessage(userId: string, username: string, message: string, metadata?: any): void {
    let viewer = this.viewers.get(userId);
    if (!viewer) {
      viewer = this.addViewer(userId, username, metadata);
    }

    viewer.messageCount++;
    viewer.totalTime = this.calculateTotalTime(viewer.joinTime);
    
    this.trackEvent({
      userId,
      username,
      type: 'chat',
      timestamp: new Date(),
      data: { message, length: message.length },
      value: this.calculateChatValue(message)
    });

    // Update minute tracking
    this.updateMinuteEngagement('messages', 1);
    
    this.emit('chat-message', { viewer, message });
  }

  private calculateChatValue(message: string): number {
    let value = 1;
    
    // Longer messages are more valuable
    if (message.length > 50) value += 1;
    if (message.length > 100) value += 1;
    
    // Questions and interactions are valuable
    if (message.includes('?')) value += 1;
    if (message.toLowerCase().includes('@')) value += 1;
    
    // Emotes reduce value slightly (spam)
    const emoteCount = (message.match(/:\w+:/g) || []).length;
    value = Math.max(1, value - emoteCount * 0.5);
    
    return value;
  }

  public trackDiceRoll(roll: ViewerDiceRoll): void {
    let viewer = this.viewers.get(roll.userId);
    if (!viewer) {
      viewer = this.addViewer(roll.userId, roll.username);
    }

    viewer.diceRolls++;
    viewer.totalTime = this.calculateTotalTime(viewer.joinTime);
    
    let value = 2; // Base value for dice rolls
    if (roll.result.critical) value += 3;
    if (roll.result.fumble) value += 2;
    
    this.trackEvent({
      userId: roll.userId,
      username: roll.username,
      type: 'dice_roll',
      timestamp: new Date(),
      data: roll,
      value
    });

    this.updateMinuteEngagement('dice', 1);
    
    this.emit('dice-roll', { viewer, roll });
  }

  public trackPollVote(userId: string, username: string, pollId: string, optionIndex: number): void {
    let viewer = this.viewers.get(userId);
    if (!viewer) {
      viewer = this.addViewer(userId, username);
    }

    viewer.pollVotes++;
    viewer.totalTime = this.calculateTotalTime(viewer.joinTime);
    
    this.trackEvent({
      userId,
      username,
      type: 'poll_vote',
      timestamp: new Date(),
      data: { pollId, optionIndex },
      value: 3 // Poll votes are high engagement
    });

    this.updateMinuteEngagement('polls', 1);
    
    this.emit('poll-vote', { viewer, pollId, optionIndex });
  }

  public trackDonation(donation: Donation): void {
    let viewer = this.viewers.get(donation.userId);
    if (!viewer) {
      viewer = this.addViewer(donation.userId, donation.username);
    }

    viewer.donations += donation.amount;
    viewer.totalTime = this.calculateTotalTime(viewer.joinTime);
    
    const value = Math.min(10, Math.floor(donation.amount / 5)); // Cap at 10 points
    
    this.trackEvent({
      userId: donation.userId,
      username: donation.username,
      type: 'donation',
      timestamp: new Date(),
      data: donation,
      value
    });

    console.log(`💰 Donation tracked: ${donation.username} - $${donation.amount}`);
    this.emit('donation', { viewer, donation });
  }

  public trackSubscription(userId: string, username: string, tier: number = 1, isGift: boolean = false): void {
    let viewer = this.viewers.get(userId);
    if (!viewer) {
      viewer = this.addViewer(userId, username);
    }

    viewer.subscribed = true;
    viewer.totalTime = this.calculateTotalTime(viewer.joinTime);
    
    this.trackEvent({
      userId,
      username,
      type: 'subscribe',
      timestamp: new Date(),
      data: { tier, isGift },
      value: tier * (isGift ? 3 : 5) // Gift subs are less valuable for individual engagement
    });

    console.log(`🌟 Subscription: ${username} (Tier ${tier}${isGift ? ' - Gift' : ''})`);
    this.emit('subscription', { viewer, tier, isGift });
  }

  public trackRaid(fromChannel: string, viewerCount: number): void {
    this.trackEvent({
      userId: 'system',
      username: 'system',
      type: 'raid',
      timestamp: new Date(),
      data: { fromChannel, viewerCount },
      value: Math.min(20, viewerCount / 10) // Scale raid value
    });

    this.updateViewerCount(this.currentViewerCount + viewerCount);
    
    console.log(`🔥 Raid from ${fromChannel}: +${viewerCount} viewers`);
    this.emit('raid', { fromChannel, viewerCount });
  }

  private trackEvent(event: EngagementEvent): void {
    this.events.push(event);
    
    // Limit event history to prevent memory issues
    if (this.events.length > 10000) {
      this.events = this.events.slice(-5000); // Keep latest 5000
    }
  }

  private updateMinuteEngagement(type: 'messages' | 'dice' | 'polls', count: number): void {
    const minute = Math.floor(Date.now() / 60000).toString();
    const current = this.engagementHistory.get(minute) || [this.currentViewerCount, 0, 0, 0];
    
    switch (type) {
      case 'messages': current[1] += count; break;
      case 'dice': current[2] += count; break;
      case 'polls': current[3] += count; break;
    }
    
    this.engagementHistory.set(minute, current);
  }

  private calculateTotalTime(joinTime: Date): number {
    return Date.now() - joinTime.getTime();
  }

  // Analytics and reporting
  public generateStats(): EngagementStats {
    const now = new Date();
    const sessionDuration = this.sessionStartTime ? 
      (now.getTime() - this.sessionStartTime.getTime()) / 1000 : 0;

    const activeViewers = Array.from(this.viewers.values());
    const totalViewers = activeViewers.length;
    
    // Calculate engagement metrics
    const totalEngagementEvents = this.events.filter(e => 
      ['chat', 'dice_roll', 'poll_vote'].includes(e.type)
    ).length;
    
    const engagementRate = totalViewers > 0 ? 
      (totalEngagementEvents / totalViewers) * 100 : 0;

    // Calculate retention (viewers who stayed > 5 minutes)
    const retainedViewers = activeViewers.filter(v => 
      this.calculateTotalTime(v.joinTime) > 300000
    ).length;
    const retentionRate = totalViewers > 0 ? 
      (retainedViewers / totalViewers) * 100 : 0;

    // Average session time
    const totalTime = activeViewers.reduce((sum, v) => 
      sum + this.calculateTotalTime(v.joinTime), 0
    );
    const averageSessionTime = totalViewers > 0 ? totalTime / totalViewers : 0;

    // Top chatters
    const topChatters = activeViewers
      .filter(v => v.messageCount > 0)
      .sort((a, b) => b.messageCount - a.messageCount)
      .slice(0, 10)
      .map(v => ({ username: v.username, messageCount: v.messageCount }));

    // Top dice rollers
    const topDiceRollers = activeViewers
      .filter(v => v.diceRolls > 0)
      .sort((a, b) => b.diceRolls - a.diceRolls)
      .slice(0, 10)
      .map(v => ({ username: v.username, rollCount: v.diceRolls }));

    // Peak engagement
    let peakEngagement = { timestamp: now, count: 0 };
    for (const [minute, data] of this.engagementHistory) {
      const totalActivity = data[1] + data[2] + data[3]; // messages + dice + polls
      if (totalActivity > peakEngagement.count) {
        peakEngagement = {
          timestamp: new Date(parseInt(minute) * 60000),
          count: totalActivity
        };
      }
    }

    // Identify new vs returning viewers (simplified)
    const newViewers = activeViewers.filter(v => 
      this.calculateTotalTime(v.joinTime) === sessionDuration * 1000
    ).length;
    const returningViewers = totalViewers - newViewers;

    return {
      totalViewers,
      activeViewers: this.currentViewerCount,
      newViewers,
      returningViewers,
      topChatters,
      topDiceRollers,
      engagementRate,
      retentionRate,
      averageSessionTime: averageSessionTime / 1000, // Convert to seconds
      peakEngagement
    };
  }

  public getEngagementTimeline(intervalMinutes: number = 5): Array<{
    timestamp: Date;
    viewers: number;
    messages: number;
    diceRolls: number;
    pollVotes: number;
    totalActivity: number;
  }> {
    const timeline: Array<any> = [];
    const intervalMs = intervalMinutes * 60000;
    
    if (!this.sessionStartTime) return timeline;
    
    const startTime = this.sessionStartTime.getTime();
    const endTime = Date.now();
    
    for (let time = startTime; time <= endTime; time += intervalMs) {
      const intervalEnd = time + intervalMs;
      const eventsInInterval = this.events.filter(e => 
        e.timestamp.getTime() >= time && e.timestamp.getTime() < intervalEnd
      );

      const viewers = this.currentViewerCount; // Simplified - would need better tracking
      const messages = eventsInInterval.filter(e => e.type === 'chat').length;
      const diceRolls = eventsInInterval.filter(e => e.type === 'dice_roll').length;
      const pollVotes = eventsInInterval.filter(e => e.type === 'poll_vote').length;

      timeline.push({
        timestamp: new Date(time),
        viewers,
        messages,
        diceRolls,
        pollVotes,
        totalActivity: messages + diceRolls + pollVotes
      });
    }

    return timeline;
  }

  public getTopViewers(limit: number = 20): Array<ViewerEngagement & {engagementScore: number}> {
    return Array.from(this.viewers.values())
      .map(viewer => ({
        ...viewer,
        engagementScore: this.calculateEngagementScore(viewer)
      }))
      .sort((a, b) => b.engagementScore - a.engagementScore)
      .slice(0, limit);
  }

  private calculateEngagementScore(viewer: ViewerEngagement): number {
    let score = 0;
    
    // Base time bonus
    const timeHours = viewer.totalTime / (1000 * 60 * 60);
    score += timeHours * 10;
    
    // Activity bonuses
    score += viewer.messageCount * 1;
    score += viewer.diceRolls * 3;
    score += viewer.pollVotes * 2;
    score += viewer.donations * 5;
    
    // Special status bonuses
    if (viewer.subscribed) score += 20;
    if (viewer.moderator) score += 15;
    if (viewer.follower) score += 5;
    
    return Math.round(score);
  }

  // Data persistence
  private async saveEngagementData(): Promise<void> {
    if (!this.session) return;

    try {
      const data = {
        sessionId: this.session.id,
        timestamp: new Date(),
        viewers: Object.fromEntries(this.viewers),
        stats: this.generateStats(),
        eventCount: this.events.length
      };

      const filename = path.join(this.dataPath, `${this.session.id}_engagement.json`);
      await fs.writeFile(filename, JSON.stringify(data, null, 2));
      
    } catch (error) {
      console.error('Error saving engagement data:', error);
    }
  }

  private async saveSessionData(finalStats: EngagementStats): Promise<void> {
    if (!this.session) return;

    try {
      const data = {
        session: this.session,
        stats: finalStats,
        timeline: this.getEngagementTimeline(),
        topViewers: this.getTopViewers(),
        events: this.events,
        engagementHistory: Object.fromEntries(this.engagementHistory)
      };

      const filename = path.join(this.dataPath, `${this.session.id}_final.json`);
      await fs.writeFile(filename, JSON.stringify(data, null, 2));
      
      console.log(`💾 Saved session engagement data: ${filename}`);
    } catch (error) {
      console.error('Error saving session data:', error);
    }
  }

  // Real-time insights
  public getCurrentEngagement(): {
    activeViewers: number;
    recentActivity: number;
    engagementRate: number;
    trending: 'up' | 'down' | 'stable';
  } {
    const recentMinutes = 5;
    const cutoff = Date.now() - (recentMinutes * 60 * 1000);
    const recentEvents = this.events.filter(e => 
      e.timestamp.getTime() > cutoff && 
      ['chat', 'dice_roll', 'poll_vote'].includes(e.type)
    );

    const recentActivity = recentEvents.length;
    const engagementRate = this.currentViewerCount > 0 ? 
      (recentActivity / this.currentViewerCount) * 100 : 0;

    // Simple trending calculation
    const olderCutoff = cutoff - (recentMinutes * 60 * 1000);
    const olderEvents = this.events.filter(e => 
      e.timestamp.getTime() > olderCutoff && 
      e.timestamp.getTime() <= cutoff &&
      ['chat', 'dice_roll', 'poll_vote'].includes(e.type)
    );

    let trending: 'up' | 'down' | 'stable' = 'stable';
    if (recentActivity > olderEvents.length * 1.2) trending = 'up';
    else if (recentActivity < olderEvents.length * 0.8) trending = 'down';

    return {
      activeViewers: this.currentViewerCount,
      recentActivity,
      engagementRate,
      trending
    };
  }

  // Cleanup
  public async shutdown(): Promise<void> {
    if (this.saveInterval) {
      clearInterval(this.saveInterval);
      this.saveInterval = null;
    }
    
    await this.saveEngagementData();
    console.log('📊 Engagement tracker shut down');
  }

  // Getters
  public getSession(): StreamSession | null {
    return this.session;
  }

  public getViewers(): Map<string, ViewerEngagement> {
    return this.viewers;
  }

  public getEvents(): EngagementEvent[] {
    return this.events;
  }

  public getCurrentViewerCount(): number {
    return this.currentViewerCount;
  }

  public getPeakViewerCount(): number {
    return this.peakViewerCount;
  }
}