import nodemailer from 'nodemailer';
import { v4 as uuidv4 } from 'uuid';

export interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  htmlContent: string;
  textContent: string;
  type: 'transactional' | 'marketing' | 'system';
  category: 'welcome' | 'onboarding' | 'retention' | 'reactivation' | 'promotional' | 'notification';
  
  // Template variables
  variables: string[];
  
  // Personalization
  personalizationRules: {
    segmentBased?: Record<string, Partial<EmailTemplate>>;
    appVariantBased?: Record<string, Partial<EmailTemplate>>;
    behaviorBased?: Record<string, Partial<EmailTemplate>>;
  };
  
  // A/B testing
  variants?: Array<{
    id: string;
    name: string;
    weight: number;
    changes: Partial<Pick<EmailTemplate, 'subject' | 'htmlContent' | 'textContent'>>;
  }>;
  
  // Metadata
  createdAt: Date;
  updatedAt: Date;
  isActive: boolean;
  tags: string[];
}

export interface EmailCampaign {
  id: string;
  name: string;
  description: string;
  templateId: string;
  
  // Audience targeting
  audienceRules: {
    userSegments?: string[];
    appVariants?: string[];
    userStates?: ('active' | 'inactive' | 'new' | 'churned' | 'premium')[];
    geographicFilters?: string[];
    behaviorFilters?: {
      hasCompletedAction?: string[];
      hasNotCompletedAction?: string[];
      lastActiveWithin?: number; // days
      joinedWithin?: number; // days
    };
    customFilters?: Record<string, any>;
  };
  
  // Scheduling
  scheduling: {
    type: 'immediate' | 'scheduled' | 'triggered';
    scheduledAt?: Date;
    triggerEvent?: string;
    triggerDelay?: number; // minutes
    timezone: string;
    respectQuietHours: boolean;
    quietHours?: { start: string; end: string };
  };
  
  // Delivery settings
  deliverySettings: {
    sendingDomain: string;
    fromName: string;
    fromEmail: string;
    replyToEmail?: string;
    trackOpens: boolean;
    trackClicks: boolean;
    unsubscribeLink: boolean;
    customHeaders?: Record<string, string>;
  };
  
  // Campaign lifecycle
  status: 'draft' | 'scheduled' | 'sending' | 'sent' | 'paused' | 'cancelled';
  createdAt: Date;
  scheduledAt?: Date;
  sentAt?: Date;
  pausedAt?: Date;
  
  // Performance tracking
  metrics?: {
    totalRecipients: number;
    delivered: number;
    opened: number;
    clicked: number;
    unsubscribed: number;
    bounced: number;
    complained: number;
    
    // Rates
    deliveryRate: number;
    openRate: number;
    clickRate: number;
    unsubscribeRate: number;
    bounceRate: number;
    complaintRate: number;
    
    // Revenue tracking
    conversions: number;
    revenue: number;
  };
}

export interface EmailAutomation {
  id: string;
  name: string;
  description: string;
  type: 'drip' | 'behavioral' | 'lifecycle' | 'abandoned_cart' | 'winback';
  
  // Trigger conditions
  trigger: {
    event: string;
    conditions?: Record<string, any>;
    delay?: number; // minutes
  };
  
  // Email sequence
  emails: Array<{
    id: string;
    templateId: string;
    delay: number; // minutes from previous email or trigger
    conditions?: Record<string, any>; // conditions to send this email
  }>;
  
  // Audience and targeting (same as campaign)
  audienceRules: EmailCampaign['audienceRules'];
  
  // Settings
  settings: {
    maxEmailsPerDay?: number;
    respectUnsubscribes: boolean;
    respectQuietHours: boolean;
    quietHours?: { start: string; end: string };
    timezone: string;
    exitOnGoalAchieved?: string; // event that stops the automation
  };
  
  // Status and metadata
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
  
  // Performance metrics
  metrics?: {
    totalEnrolled: number;
    completed: number;
    avgCompletionRate: number;
    totalRevenue: number;
    avgRevenuePerUser: number;
  };
}

export interface EmailUser {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  appVariant?: string;
  userSegment?: string;
  
  // Subscription status
  subscriptionStatus: 'subscribed' | 'unsubscribed' | 'bounced' | 'complained';
  subscriptionSource: string;
  subscribedAt: Date;
  unsubscribedAt?: Date;
  
  // Preferences
  preferences: {
    frequency: 'daily' | 'weekly' | 'monthly' | 'never';
    categories: string[]; // which email categories they want
    timezone: string;
    quietHours?: { start: string; end: string };
  };
  
  // Engagement tracking
  engagement: {
    totalEmailsSent: number;
    totalOpens: number;
    totalClicks: number;
    lastOpenedAt?: Date;
    lastClickedAt?: Date;
    engagementScore: number; // 0-100
  };
  
  // Custom properties
  customProperties: Record<string, any>;
}

export interface EmailEvent {
  id: string;
  campaignId?: string;
  automationId?: string;
  templateId: string;
  userId: string;
  email: string;
  
  // Event details
  eventType: 'sent' | 'delivered' | 'opened' | 'clicked' | 'bounced' | 'unsubscribed' | 'complained';
  timestamp: Date;
  
  // Additional data
  metadata?: {
    messageId?: string;
    clickedUrl?: string;
    bounceType?: 'hard' | 'soft';
    bounceReason?: string;
    userAgent?: string;
    ipAddress?: string;
    location?: {
      country: string;
      city: string;
    };
  };
}

class EmailAutomationSystem {
  private templates: Map<string, EmailTemplate> = new Map();
  private campaigns: Map<string, EmailCampaign> = new Map();
  private automations: Map<string, EmailAutomation> = new Map();
  private users: Map<string, EmailUser> = new Map();
  private events: Map<string, EmailEvent> = new Map();
  private transporter: nodemailer.Transporter;

  constructor(smtpConfig: {
    host: string;
    port: number;
    secure: boolean;
    auth: {
      user: string;
      pass: string;
    };
  }) {
    this.transporter = nodemailer.createTransporter(smtpConfig);
    this.initializeDefaultTemplates();
    this.initializeDefaultAutomations();
  }

  public createTemplate(template: Omit<EmailTemplate, 'id' | 'createdAt' | 'updatedAt'>): EmailTemplate {
    const newTemplate: EmailTemplate = {
      ...template,
      id: uuidv4(),
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    this.templates.set(newTemplate.id, newTemplate);
    return newTemplate;
  }

  public createCampaign(campaign: Omit<EmailCampaign, 'id' | 'createdAt' | 'status'>): EmailCampaign {
    const newCampaign: EmailCampaign = {
      ...campaign,
      id: uuidv4(),
      status: 'draft',
      createdAt: new Date(),
    };

    this.campaigns.set(newCampaign.id, newCampaign);
    return newCampaign;
  }

  public createAutomation(automation: Omit<EmailAutomation, 'id' | 'createdAt' | 'updatedAt'>): EmailAutomation {
    const newAutomation: EmailAutomation = {
      ...automation,
      id: uuidv4(),
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    this.automations.set(newAutomation.id, newAutomation);
    return newAutomation;
  }

  public async sendCampaign(campaignId: string): Promise<void> {
    const campaign = this.campaigns.get(campaignId);
    if (!campaign) {
      throw new Error(`Campaign ${campaignId} not found`);
    }

    if (campaign.status !== 'draft' && campaign.status !== 'scheduled') {
      throw new Error(`Campaign ${campaignId} cannot be sent from status: ${campaign.status}`);
    }

    campaign.status = 'sending';
    campaign.sentAt = new Date();

    try {
      // Get target audience
      const audience = this.getAudience(campaign.audienceRules);
      
      // Send emails
      const sendPromises = audience.map(user => this.sendEmailToUser(campaign, user));
      await Promise.allSettled(sendPromises);

      campaign.status = 'sent';
      this.campaigns.set(campaignId, campaign);

      // Update campaign metrics
      await this.updateCampaignMetrics(campaignId);

    } catch (error) {
      campaign.status = 'draft'; // Reset to draft on error
      this.campaigns.set(campaignId, campaign);
      throw error;
    }
  }

  public async triggerAutomation(
    automationId: string,
    userId: string,
    triggerData?: Record<string, any>
  ): Promise<void> {
    const automation = this.automations.get(automationId);
    if (!automation || !automation.isActive) {
      return;
    }

    const user = this.users.get(userId);
    if (!user || user.subscriptionStatus !== 'subscribed') {
      return;
    }

    // Check if user matches audience rules
    if (!this.userMatchesAudience(user, automation.audienceRules)) {
      return;
    }

    // Schedule all emails in the automation
    for (const email of automation.emails) {
      setTimeout(async () => {
        // Check conditions before sending
        if (email.conditions && !this.checkConditions(user, email.conditions)) {
          return;
        }

        const template = this.templates.get(email.templateId);
        if (!template) return;

        await this.sendTemplateToUser(template, user, {
          automationId,
          ...triggerData,
        });
      }, email.delay * 60 * 1000);
    }
  }

  public async subscribeUser(
    email: string,
    userData: Partial<EmailUser> = {},
    source: string = 'api'
  ): Promise<EmailUser> {
    const existingUser = Array.from(this.users.values()).find(u => u.email === email);
    
    if (existingUser) {
      if (existingUser.subscriptionStatus === 'unsubscribed') {
        existingUser.subscriptionStatus = 'subscribed';
        existingUser.subscribedAt = new Date();
        existingUser.subscriptionSource = source;
        this.users.set(existingUser.id, existingUser);
      }
      return existingUser;
    }

    const newUser: EmailUser = {
      id: uuidv4(),
      email,
      firstName: userData.firstName,
      lastName: userData.lastName,
      appVariant: userData.appVariant,
      userSegment: userData.userSegment,
      subscriptionStatus: 'subscribed',
      subscriptionSource: source,
      subscribedAt: new Date(),
      preferences: {
        frequency: 'weekly',
        categories: ['onboarding', 'promotional', 'notification'],
        timezone: 'UTC',
        ...userData.preferences,
      },
      engagement: {
        totalEmailsSent: 0,
        totalOpens: 0,
        totalClicks: 0,
        engagementScore: 50,
      },
      customProperties: userData.customProperties || {},
    };

    this.users.set(newUser.id, newUser);

    // Trigger welcome automation
    setTimeout(() => {
      this.triggerAutomationByType('welcome', newUser.id);
    }, 1000);

    return newUser;
  }

  public unsubscribeUser(email: string): void {
    const user = Array.from(this.users.values()).find(u => u.email === email);
    if (user) {
      user.subscriptionStatus = 'unsubscribed';
      user.unsubscribedAt = new Date();
      this.users.set(user.id, user);
    }
  }

  public segmentUsers(segmentRules: {
    appVariant?: string[];
    userStates?: string[];
    engagementScore?: { min?: number; max?: number };
    lastActiveWithin?: number;
    customProperties?: Record<string, any>;
  }): EmailUser[] {
    return Array.from(this.users.values()).filter(user => {
      if (user.subscriptionStatus !== 'subscribed') return false;

      if (segmentRules.appVariant && !segmentRules.appVariant.includes(user.appVariant || '')) {
        return false;
      }

      if (segmentRules.engagementScore) {
        if (segmentRules.engagementScore.min && user.engagement.engagementScore < segmentRules.engagementScore.min) {
          return false;
        }
        if (segmentRules.engagementScore.max && user.engagement.engagementScore > segmentRules.engagementScore.max) {
          return false;
        }
      }

      // Add more segmentation logic here...

      return true;
    });
  }

  public getEmailAnalytics(
    entityId: string,
    entityType: 'campaign' | 'automation' | 'template',
    timeframe: { start: Date; end: Date }
  ): any {
    const events = Array.from(this.events.values()).filter(event => {
      const isInTimeframe = event.timestamp >= timeframe.start && event.timestamp <= timeframe.end;
      
      switch (entityType) {
        case 'campaign':
          return event.campaignId === entityId && isInTimeframe;
        case 'automation':
          return event.automationId === entityId && isInTimeframe;
        case 'template':
          return event.templateId === entityId && isInTimeframe;
        default:
          return false;
      }
    });

    const sent = events.filter(e => e.eventType === 'sent').length;
    const delivered = events.filter(e => e.eventType === 'delivered').length;
    const opened = events.filter(e => e.eventType === 'opened').length;
    const clicked = events.filter(e => e.eventType === 'clicked').length;
    const unsubscribed = events.filter(e => e.eventType === 'unsubscribed').length;
    const bounced = events.filter(e => e.eventType === 'bounced').length;

    return {
      sent,
      delivered,
      opened,
      clicked,
      unsubscribed,
      bounced,
      deliveryRate: sent > 0 ? (delivered / sent) * 100 : 0,
      openRate: delivered > 0 ? (opened / delivered) * 100 : 0,
      clickRate: delivered > 0 ? (clicked / delivered) * 100 : 0,
      unsubscribeRate: delivered > 0 ? (unsubscribed / delivered) * 100 : 0,
      bounceRate: sent > 0 ? (bounced / sent) * 100 : 0,
    };
  }

  private async sendEmailToUser(campaign: EmailCampaign, user: EmailUser): Promise<void> {
    const template = this.templates.get(campaign.templateId);
    if (!template) return;

    await this.sendTemplateToUser(template, user, { campaignId: campaign.id });
  }

  private async sendTemplateToUser(
    template: EmailTemplate,
    user: EmailUser,
    context: { campaignId?: string; automationId?: string; [key: string]: any } = {}
  ): Promise<void> {
    try {
      // Personalize content
      const personalizedContent = this.personalizeTemplate(template, user, context);
      
      // Create tracking links
      const trackingData = this.createTrackingData(template.id, user.id, context);
      const htmlWithTracking = this.addTrackingToContent(personalizedContent.htmlContent, trackingData);

      // Send email
      const info = await this.transporter.sendMail({
        from: `"ActiveLog" <noreply@activelog.com>`,
        to: user.email,
        subject: personalizedContent.subject,
        text: personalizedContent.textContent,
        html: htmlWithTracking,
        headers: {
          'X-Campaign-ID': context.campaignId || '',
          'X-Automation-ID': context.automationId || '',
          'X-Template-ID': template.id,
          'X-User-ID': user.id,
        },
      });

      // Record sent event
      this.recordEvent({
        campaignId: context.campaignId,
        automationId: context.automationId,
        templateId: template.id,
        userId: user.id,
        email: user.email,
        eventType: 'sent',
        timestamp: new Date(),
        metadata: { messageId: info.messageId },
      });

      // Update user engagement
      user.engagement.totalEmailsSent++;
      this.users.set(user.id, user);

    } catch (error) {
      console.error('Failed to send email:', error);
      
      // Record bounce if it's a delivery error
      this.recordEvent({
        campaignId: context.campaignId,
        automationId: context.automationId,
        templateId: template.id,
        userId: user.id,
        email: user.email,
        eventType: 'bounced',
        timestamp: new Date(),
        metadata: { bounceReason: error instanceof Error ? error.message : 'Unknown error' },
      });
    }
  }

  private personalizeTemplate(
    template: EmailTemplate,
    user: EmailUser,
    context: Record<string, any>
  ): Pick<EmailTemplate, 'subject' | 'htmlContent' | 'textContent'> {
    const variables = {
      firstName: user.firstName || 'there',
      lastName: user.lastName || '',
      email: user.email,
      appVariant: user.appVariant || 'ActiveLog',
      ...context,
    };

    const replaceVariables = (content: string) => {
      return content.replace(/\{\{(\w+)\}\}/g, (match, key) => {
        return variables[key] || match;
      });
    };

    return {
      subject: replaceVariables(template.subject),
      htmlContent: replaceVariables(template.htmlContent),
      textContent: replaceVariables(template.textContent),
    };
  }

  private createTrackingData(templateId: string, userId: string, context: Record<string, any>) {
    return {
      templateId,
      userId,
      campaignId: context.campaignId,
      automationId: context.automationId,
      trackingId: uuidv4(),
    };
  }

  private addTrackingToContent(htmlContent: string, trackingData: any): string {
    // Add open tracking pixel
    const trackingPixel = `<img src="https://track.activelog.com/open?t=${trackingData.trackingId}" width="1" height="1" style="display:none" alt="" />`;
    
    // Add click tracking to links
    const htmlWithClickTracking = htmlContent.replace(
      /<a\s+href="([^"]+)"/g,
      `<a href="https://track.activelog.com/click?url=$1&t=${trackingData.trackingId}"`
    );

    return htmlWithClickTracking + trackingPixel;
  }

  private getAudience(audienceRules: EmailCampaign['audienceRules']): EmailUser[] {
    return Array.from(this.users.values()).filter(user => 
      this.userMatchesAudience(user, audienceRules)
    );
  }

  private userMatchesAudience(user: EmailUser, rules: EmailCampaign['audienceRules']): boolean {
    if (user.subscriptionStatus !== 'subscribed') return false;

    if (rules.appVariants && !rules.appVariants.includes(user.appVariant || '')) {
      return false;
    }

    if (rules.userSegments && !rules.userSegments.includes(user.userSegment || '')) {
      return false;
    }

    // Add more audience matching logic...

    return true;
  }

  private checkConditions(user: EmailUser, conditions: Record<string, any>): boolean {
    // Implement condition checking logic
    return true;
  }

  private recordEvent(event: Omit<EmailEvent, 'id'>): void {
    const emailEvent: EmailEvent = {
      ...event,
      id: uuidv4(),
    };

    this.events.set(emailEvent.id, emailEvent);

    // Update user engagement based on event type
    const user = this.users.get(event.userId);
    if (user) {
      switch (event.eventType) {
        case 'opened':
          user.engagement.totalOpens++;
          user.engagement.lastOpenedAt = new Date();
          user.engagement.engagementScore = Math.min(100, user.engagement.engagementScore + 2);
          break;
        case 'clicked':
          user.engagement.totalClicks++;
          user.engagement.lastClickedAt = new Date();
          user.engagement.engagementScore = Math.min(100, user.engagement.engagementScore + 5);
          break;
        case 'bounced':
          user.subscriptionStatus = 'bounced';
          user.engagement.engagementScore = Math.max(0, user.engagement.engagementScore - 10);
          break;
        case 'unsubscribed':
          user.subscriptionStatus = 'unsubscribed';
          user.unsubscribedAt = new Date();
          break;
      }
      this.users.set(user.id, user);
    }
  }

  private async updateCampaignMetrics(campaignId: string): Promise<void> {
    const campaign = this.campaigns.get(campaignId);
    if (!campaign) return;

    const analytics = this.getEmailAnalytics(campaignId, 'campaign', {
      start: campaign.createdAt,
      end: new Date(),
    });

    campaign.metrics = {
      totalRecipients: analytics.sent,
      delivered: analytics.delivered,
      opened: analytics.opened,
      clicked: analytics.clicked,
      unsubscribed: analytics.unsubscribed,
      bounced: analytics.bounced,
      complained: 0, // Would track from webhook
      deliveryRate: analytics.deliveryRate,
      openRate: analytics.openRate,
      clickRate: analytics.clickRate,
      unsubscribeRate: analytics.unsubscribeRate,
      bounceRate: analytics.bounceRate,
      complaintRate: 0,
      conversions: 0, // Would track from conversion events
      revenue: 0, // Would track from purchase events
    };

    this.campaigns.set(campaignId, campaign);
  }

  private triggerAutomationByType(type: string, userId: string): void {
    const automation = Array.from(this.automations.values())
      .find(a => a.type === type && a.isActive);
    
    if (automation) {
      this.triggerAutomation(automation.id, userId);
    }
  }

  private initializeDefaultTemplates(): void {
    const welcomeTemplate: EmailTemplate = {
      id: uuidv4(),
      name: 'Welcome Email',
      subject: 'Welcome to {{appVariant}}! 🎉',
      htmlContent: `
        <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
          <h1>Welcome to {{appVariant}}, {{firstName}}!</h1>
          <p>We're excited to have you on board. Here's what you can do next:</p>
          <ul>
            <li>Complete your profile setup</li>
            <li>Explore our key features</li>
            <li>Join our community</li>
          </ul>
          <a href="https://{{appVariant}}.com/getting-started" style="background: #007AFF; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">Get Started</a>
          <p>Need help? Just reply to this email!</p>
        </div>
      `,
      textContent: `Welcome to {{appVariant}}, {{firstName}}! We're excited to have you on board. Visit https://{{appVariant}}.com/getting-started to get started.`,
      type: 'transactional',
      category: 'welcome',
      variables: ['firstName', 'appVariant'],
      personalizationRules: {},
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true,
      tags: ['welcome', 'onboarding'],
    };

    this.templates.set(welcomeTemplate.id, welcomeTemplate);
  }

  private initializeDefaultAutomations(): void {
    // Create default welcome automation
    const welcomeTemplate = Array.from(this.templates.values())[0];
    
    if (welcomeTemplate) {
      const welcomeAutomation: EmailAutomation = {
        id: uuidv4(),
        name: 'Welcome Series',
        description: 'Welcome new users and guide them through onboarding',
        type: 'drip',
        trigger: {
          event: 'user_signup',
          delay: 0,
        },
        emails: [
          {
            id: uuidv4(),
            templateId: welcomeTemplate.id,
            delay: 0,
          },
        ],
        audienceRules: {},
        settings: {
          respectUnsubscribes: true,
          respectQuietHours: true,
          timezone: 'UTC',
        },
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      this.automations.set(welcomeAutomation.id, welcomeAutomation);
    }
  }

  // Public methods for accessing data (for testing/debugging)
  public getTemplates(): EmailTemplate[] {
    return Array.from(this.templates.values());
  }

  public getCampaigns(): EmailCampaign[] {
    return Array.from(this.campaigns.values());
  }

  public getAutomations(): EmailAutomation[] {
    return Array.from(this.automations.values());
  }

  public getUsers(): EmailUser[] {
    return Array.from(this.users.values());
  }

  public getEvents(): EmailEvent[] {
    return Array.from(this.events.values());
  }
}

export default EmailAutomationSystem;