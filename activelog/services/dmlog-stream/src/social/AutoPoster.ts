import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import { 
  StreamSession, 
  StreamHighlight, 
  SocialTemplate, 
  SocialPost, 
  AutomationSettings,
  SessionEvent,
  ProgressMilestone
} from '../types';

export interface TwitterAPI {
  postTweet(content: string, media?: string[]): Promise<string>;
  uploadMedia(filePath: string): Promise<string>;
}

export interface DiscordAPI {
  postMessage(content: string, channelId: string, embeds?: any[]): Promise<string>;
  uploadFile(filePath: string, channelId: string): Promise<string>;
}

export class AutoPoster extends EventEmitter {
  private settings: AutomationSettings;
  private templates: Map<string, SocialTemplate> = new Map();
  private postHistory: SocialPost[] = [];
  private dataPath: string;
  private twitterAPI?: TwitterAPI;
  private discordAPI?: DiscordAPI;
  private currentSession: StreamSession | null = null;
  private scheduledPosts: Map<string, NodeJS.Timeout> = new Map();

  constructor(
    settings: AutomationSettings,
    dataPath: string,
    twitterAPI?: TwitterAPI,
    discordAPI?: DiscordAPI
  ) {
    super();
    this.settings = settings;
    this.dataPath = dataPath;
    this.twitterAPI = twitterAPI;
    this.discordAPI = discordAPI;
    this.setupDefaultTemplates();
  }

  public async initialize(): Promise<void> {
    try {
      await fs.mkdir(this.dataPath, { recursive: true });
      await this.loadPostHistory();
      
      console.log('📱 Social media auto-posting initialized');
      this.emit('initialized');
    } catch (error) {
      console.error('Error initializing auto-poster:', error);
      throw error;
    }
  }

  private setupDefaultTemplates(): void {
    // Session start templates
    this.templates.set('session_start_twitter', {
      id: 'session_start_twitter',
      platform: 'twitter',
      trigger: 'session_start',
      template: `🎲 LIVE NOW: {{sessionTitle}}\n\nJoin us for {{campaignName}} as we continue our adventure! \n\n{{description}}\n\n#DnD #TTRPG #LiveStream #{{campaignHashtag}}`,
      hashtags: ['DnD', 'TTRPG', 'LiveStream'],
      mentions: [],
      includeMedia: true,
      enabled: true
    });

    this.templates.set('session_start_discord', {
      id: 'session_start_discord',
      platform: 'discord',
      trigger: 'session_start',
      template: `🎯 **{{campaignName}} is LIVE!**\n\n📖 **Session:** {{sessionTitle}}\n🎬 **Stream:** {{streamUrl}}\n\n{{description}}\n\n@everyone Come watch the adventure unfold!`,
      hashtags: [],
      mentions: ['@everyone'],
      includeMedia: false,
      enabled: true
    });

    // Session end templates
    this.templates.set('session_end_twitter', {
      id: 'session_end_twitter',
      platform: 'twitter',
      trigger: 'session_end',
      template: `📚 Session {{sessionNumber}} of {{campaignName}} is complete!\n\n✨ {{highlightText}}\n\nThanks to everyone who joined us! VOD will be available soon.\n\n#DnD #TTRPG #{{campaignHashtag}}`,
      hashtags: ['DnD', 'TTRPG', 'SessionComplete'],
      mentions: [],
      includeMedia: true,
      enabled: true
    });

    this.templates.set('session_end_discord', {
      id: 'session_end_discord',
      platform: 'discord',
      trigger: 'session_end',
      template: `📋 **Session {{sessionNumber}} Complete!**\n\n🎭 **Duration:** {{duration}} minutes\n⚔️ **Highlights:** {{highlightCount}} epic moments\n👥 **Peak Viewers:** {{peakViewers}}\n\n{{sessionSummary}}\n\nThanks for watching! 🙏`,
      hashtags: [],
      mentions: [],
      includeMedia: false,
      enabled: true
    });

    // Highlight templates
    this.templates.set('highlight_twitter', {
      id: 'highlight_twitter',
      platform: 'twitter',
      trigger: 'highlight',
      template: `🔥 EPIC MOMENT: {{highlightTitle}}\n\n{{highlightDescription}}\n\nFrom today's {{campaignName}} session!\n\n#DnD #TTRPG #EpicMoments #{{campaignHashtag}}`,
      hashtags: ['DnD', 'TTRPG', 'EpicMoments'],
      mentions: [],
      includeMedia: true,
      enabled: true
    });

    // Milestone templates
    this.templates.set('milestone_twitter', {
      id: 'milestone_twitter',
      platform: 'twitter',
      trigger: 'milestone',
      template: `🏆 MILESTONE ACHIEVED!\n\n{{milestoneTitle}}\n{{milestoneDescription}}\n\n{{campaignName}} continues to amaze! 🎲\n\n#DnD #TTRPG #Milestone #{{campaignHashtag}}`,
      hashtags: ['DnD', 'TTRPG', 'Milestone'],
      mentions: [],
      includeMedia: false,
      enabled: true
    });

    this.templates.set('milestone_discord', {
      id: 'milestone_discord',
      platform: 'discord',
      trigger: 'milestone',
      template: `🎉 **MILESTONE ACHIEVED!** 🎉\n\n🏆 **{{milestoneTitle}}**\n📝 {{milestoneDescription}}\n\nThe adventure continues to reach new heights! Keep watching for more epic moments!`,
      hashtags: [],
      mentions: [],
      includeMedia: false,
      enabled: true
    });

    // Custom event templates
    this.templates.set('character_death_twitter', {
      id: 'character_death_twitter',
      platform: 'twitter',
      trigger: 'custom',
      template: `💀 RIP {{characterName}}\n\nA moment of silence for our fallen hero in {{campaignName}}...\n\nWill they return? Tune in to find out! 🎲\n\n#DnD #TTRPG #CharacterDeath #Drama`,
      hashtags: ['DnD', 'TTRPG', 'CharacterDeath', 'Drama'],
      mentions: [],
      includeMedia: false,
      enabled: false // Disabled by default - sensitive content
    });

    this.templates.set('critical_hit_twitter', {
      id: 'critical_hit_twitter',
      platform: 'twitter',
      trigger: 'custom',
      template: `🎯 NATURAL 20! 🎯\n\n{{characterName}} just rolled a critical hit!\n{{description}}\n\nThe dice gods smile upon {{campaignName}}! 🎲\n\n#DnD #TTRPG #Crit #Natural20`,
      hashtags: ['DnD', 'TTRPG', 'Crit', 'Natural20'],
      mentions: [],
      includeMedia: false,
      enabled: true
    });
  }

  private async loadPostHistory(): Promise<void> {
    try {
      const historyFile = path.join(this.dataPath, 'post_history.json');
      const data = await fs.readFile(historyFile, 'utf-8');
      this.postHistory = JSON.parse(data);
      console.log(`📱 Loaded ${this.postHistory.length} previous posts`);
    } catch (error) {
      console.log('📱 Starting with fresh post history');
      this.postHistory = [];
    }
  }

  private async savePostHistory(): Promise<void> {
    try {
      const historyFile = path.join(this.dataPath, 'post_history.json');
      await fs.writeFile(historyFile, JSON.stringify(this.postHistory, null, 2));
    } catch (error) {
      console.error('Error saving post history:', error);
    }
  }

  // Event handlers
  public async onSessionStart(session: StreamSession): Promise<void> {
    if (!this.settings.socialPosting.enabled) return;

    this.currentSession = session;
    
    const context = {
      sessionTitle: session.title,
      sessionNumber: this.getSessionNumber(session),
      campaignName: this.getCampaignName(session),
      campaignHashtag: this.generateCampaignHashtag(session),
      description: session.description || 'Join us for an epic adventure!',
      streamUrl: this.getStreamUrl(session)
    };

    await this.processTemplateTrigger('session_start', context);
    
    console.log(`📱 Posted session start for: ${session.title}`);
    this.emit('session-start-posted', session);
  }

  public async onSessionEnd(
    session: StreamSession,
    summary: {
      duration: number;
      highlightCount: number;
      peakViewers: number;
      sessionSummary: string;
      highlights: StreamHighlight[];
    }
  ): Promise<void> {
    if (!this.settings.socialPosting.enabled) return;

    const context = {
      sessionTitle: session.title,
      sessionNumber: this.getSessionNumber(session),
      campaignName: this.getCampaignName(session),
      campaignHashtag: this.generateCampaignHashtag(session),
      duration: Math.round(summary.duration),
      highlightCount: summary.highlightCount,
      peakViewers: summary.peakViewers,
      sessionSummary: summary.sessionSummary,
      highlightText: this.generateHighlightText(summary.highlights)
    };

    await this.processTemplateTrigger('session_end', context);
    
    // Schedule highlight posts
    await this.scheduleHighlightPosts(summary.highlights);
    
    console.log(`📱 Posted session end for: ${session.title}`);
    this.emit('session-end-posted', session, summary);
  }

  public async onMilestoneAchieved(milestone: ProgressMilestone, campaignName: string): Promise<void> {
    if (!this.settings.socialPosting.enabled) return;

    const context = {
      milestoneTitle: milestone.title,
      milestoneDescription: milestone.description,
      campaignName,
      campaignHashtag: this.generateCampaignHashtag({ title: campaignName } as any),
      milestoneType: milestone.type,
      milestoneIcon: milestone.icon || '🏆'
    };

    await this.processTemplateTrigger('milestone', context);
    
    console.log(`📱 Posted milestone achievement: ${milestone.title}`);
    this.emit('milestone-posted', milestone);
  }

  public async onHighlightCreated(highlight: StreamHighlight, campaignName: string): Promise<void> {
    if (!this.settings.socialPosting.enabled) return;
    
    // Don't post every highlight immediately - use scheduling
    await this.scheduleHighlightPost(highlight, campaignName);
  }

  private async scheduleHighlightPosts(highlights: StreamHighlight[]): Promise<void> {
    // Post highlights over the next few hours after session ends
    const topHighlights = highlights
      .filter(h => h.score >= 0.8)
      .sort((a, b) => b.score - a.score)
      .slice(0, 3);

    topHighlights.forEach((highlight, index) => {
      const delay = (index + 1) * 60 * 60 * 1000; // 1 hour apart
      this.scheduleHighlightPost(highlight, this.getCampaignName(this.currentSession), delay);
    });
  }

  private async scheduleHighlightPost(
    highlight: StreamHighlight,
    campaignName: string,
    delay: number = 0
  ): Promise<void> {
    const postId = `highlight_${highlight.id}`;
    
    const timer = setTimeout(async () => {
      try {
        const context = {
          highlightTitle: highlight.title,
          highlightDescription: highlight.description || 'An epic moment from the stream!',
          campaignName,
          campaignHashtag: this.generateCampaignHashtag({ title: campaignName } as any),
          highlightType: highlight.type,
          participants: highlight.participants.join(', ')
        };

        await this.processTemplateTrigger('highlight', context, highlight);
        console.log(`📱 Posted scheduled highlight: ${highlight.title}`);
      } catch (error) {
        console.error(`Error posting scheduled highlight:`, error);
      } finally {
        this.scheduledPosts.delete(postId);
      }
    }, delay);

    this.scheduledPosts.set(postId, timer);
  }

  // Custom event posting
  public async postCharacterDeath(characterName: string, campaignName: string): Promise<void> {
    if (!this.settings.socialPosting.enabled) return;

    const template = this.templates.get('character_death_twitter');
    if (!template?.enabled) return;

    const context = {
      characterName,
      campaignName,
      campaignHashtag: this.generateCampaignHashtag({ title: campaignName } as any)
    };

    await this.createAndPostSocial(template, context);
  }

  public async postCriticalHit(
    characterName: string,
    description: string,
    campaignName: string
  ): Promise<void> {
    if (!this.settings.socialPosting.enabled) return;

    const template = this.templates.get('critical_hit_twitter');
    if (!template?.enabled) return;

    const context = {
      characterName,
      description,
      campaignName,
      campaignHashtag: this.generateCampaignHashtag({ title: campaignName } as any)
    };

    await this.createAndPostSocial(template, context);
  }

  // Core posting logic
  private async processTemplateTrigger(
    trigger: SocialTemplate['trigger'],
    context: Record<string, any>,
    mediaSource?: StreamHighlight
  ): Promise<void> {
    const matchingTemplates = Array.from(this.templates.values())
      .filter(template => template.trigger === trigger && template.enabled);

    for (const template of matchingTemplates) {
      try {
        await this.createAndPostSocial(template, context, mediaSource);
      } catch (error) {
        console.error(`Error posting to ${template.platform}:`, error);
        this.emit('post-error', { template, error });
      }
    }
  }

  private async createAndPostSocial(
    template: SocialTemplate,
    context: Record<string, any>,
    mediaSource?: StreamHighlight
  ): Promise<SocialPost> {
    const content = this.processTemplate(template.template, context);
    const hashtags = [...template.hashtags];
    const mentions = [...template.mentions];

    // Add dynamic hashtags based on context
    if (context.highlightType) {
      hashtags.push(this.formatHashtag(context.highlightType));
    }

    const post: SocialPost = {
      id: this.generatePostId(),
      platform: template.platform,
      content,
      hashtags,
      mentions,
      postedAt: new Date(),
      status: 'draft'
    };

    // Add media if specified
    let media: string[] = [];
    if (template.includeMedia && mediaSource) {
      media = await this.prepareMedia(mediaSource);
      post.media = media;
    }

    // Post to platform
    try {
      const platformPostId = await this.postToPlatform(post);
      post.status = 'posted';
      
      // Add engagement tracking ID
      if (platformPostId) {
        post.id = platformPostId;
      }

      console.log(`✅ Posted to ${template.platform}: ${content.substring(0, 50)}...`);
    } catch (error) {
      post.status = 'failed';
      console.error(`❌ Failed to post to ${template.platform}:`, error);
      throw error;
    }

    // Save to history
    this.postHistory.push(post);
    if (this.postHistory.length > 1000) {
      this.postHistory = this.postHistory.slice(-500); // Keep latest 500
    }
    
    await this.savePostHistory();
    this.emit('post-created', post);
    
    return post;
  }

  private async postToPlatform(post: SocialPost): Promise<string | null> {
    switch (post.platform) {
      case 'twitter':
        if (this.twitterAPI) {
          return await this.twitterAPI.postTweet(post.content, post.media);
        }
        break;
        
      case 'discord':
        if (this.discordAPI) {
          const channelId = this.getDiscordChannelId();
          return await this.discordAPI.postMessage(post.content, channelId, 
            this.createDiscordEmbeds(post));
        }
        break;
    }

    throw new Error(`No API configured for platform: ${post.platform}`);
  }

  private async prepareMedia(source: StreamHighlight): Promise<string[]> {
    const media: string[] = [];
    
    if (source.thumbnail) {
      try {
        await fs.access(source.thumbnail);
        media.push(source.thumbnail);
      } catch {} // File doesn't exist
    }

    if (source.clipUrl && source.clipUrl.endsWith('.mp4')) {
      try {
        await fs.access(source.clipUrl);
        // For video clips, we might want to create a GIF or additional thumbnail
        media.push(source.clipUrl);
      } catch {} // File doesn't exist
    }

    return media;
  }

  private createDiscordEmbeds(post: SocialPost): any[] {
    if (post.platform !== 'discord') return [];

    return [{
      color: 0x7289da,
      timestamp: post.postedAt?.toISOString(),
      footer: {
        text: 'DMLog Stream Bot'
      }
    }];
  }

  // Template processing
  private processTemplate(template: string, context: Record<string, any>): string {
    let processed = template;
    
    // Replace template variables
    for (const [key, value] of Object.entries(context)) {
      const placeholder = `{{${key}}}`;
      processed = processed.replace(new RegExp(placeholder, 'g'), String(value));
    }
    
    return processed;
  }

  // Utility methods
  private getSessionNumber(session: StreamSession): string {
    // Extract session number from title or generate based on campaign
    const match = session.title.match(/session\s*(\d+)/i);
    return match ? match[1] : '1';
  }

  private getCampaignName(session: StreamSession | null): string {
    if (!session) return 'D&D Campaign';
    
    // Extract campaign name from title or description
    const title = session.title;
    const parts = title.split(/[-–:]/);
    return parts.length > 1 ? parts[0].trim() : 'D&D Campaign';
  }

  private generateCampaignHashtag(session: StreamSession): string {
    const name = this.getCampaignName(session);
    return name
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, '')
      .substring(0, 20);
  }

  private getStreamUrl(session: StreamSession): string {
    // This would be configured based on your streaming platform
    return `https://twitch.tv/yourchannel`;
  }

  private generateHighlightText(highlights: StreamHighlight[]): string {
    if (highlights.length === 0) return 'Epic moments throughout!';
    
    const topHighlight = highlights
      .sort((a, b) => b.score - a.score)[0];
      
    return topHighlight.title || 'Amazing moments captured!';
  }

  private formatHashtag(text: string): string {
    return text
      .replace(/[^a-zA-Z0-9]/g, '')
      .toLowerCase();
  }

  private getDiscordChannelId(): string {
    // This would be configured
    return process.env.DISCORD_CHANNEL_ID || '';
  }

  private generatePostId(): string {
    return `post_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Template management
  public addTemplate(template: SocialTemplate): void {
    this.templates.set(template.id, template);
    console.log(`➕ Added social media template: ${template.id}`);
  }

  public removeTemplate(templateId: string): void {
    this.templates.delete(templateId);
    console.log(`➖ Removed social media template: ${templateId}`);
  }

  public updateTemplate(template: SocialTemplate): void {
    this.templates.set(template.id, template);
    console.log(`🔄 Updated social media template: ${template.id}`);
  }

  public getTemplates(): SocialTemplate[] {
    return Array.from(this.templates.values());
  }

  public toggleTemplate(templateId: string, enabled: boolean): void {
    const template = this.templates.get(templateId);
    if (template) {
      template.enabled = enabled;
      console.log(`${enabled ? '✅' : '❌'} Template ${templateId}: ${enabled ? 'enabled' : 'disabled'}`);
    }
  }

  // Analytics
  public getPostAnalytics(): any {
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    const recentPosts = this.postHistory.filter(p => 
      p.postedAt && p.postedAt > thirtyDaysAgo
    );

    const platformStats = recentPosts.reduce((acc, post) => {
      acc[post.platform] = (acc[post.platform] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const statusStats = recentPosts.reduce((acc, post) => {
      acc[post.status] = (acc[post.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      totalPosts: this.postHistory.length,
      recentPosts: recentPosts.length,
      platformBreakdown: platformStats,
      statusBreakdown: statusStats,
      averagePostsPerDay: recentPosts.length / 30,
      successRate: recentPosts.length > 0 ? 
        (statusStats.posted || 0) / recentPosts.length : 0
    };
  }

  public getRecentPosts(limit: number = 20): SocialPost[] {
    return this.postHistory
      .sort((a, b) => (b.postedAt?.getTime() || 0) - (a.postedAt?.getTime() || 0))
      .slice(0, limit);
  }

  // Configuration
  public updateSettings(newSettings: AutomationSettings): void {
    this.settings = newSettings;
    console.log('🔄 Updated social media settings');
    this.emit('settings-updated', newSettings);
  }

  // Cleanup
  public async shutdown(): Promise<void> {
    // Cancel scheduled posts
    for (const [postId, timer] of this.scheduledPosts) {
      clearTimeout(timer);
    }
    this.scheduledPosts.clear();
    
    await this.savePostHistory();
    console.log('📱 Social media auto-posting shut down');
  }
}