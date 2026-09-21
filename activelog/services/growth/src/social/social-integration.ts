import { TwitterApi } from 'twitter-api-v2';
import axios from 'axios';

export interface SocialPlatformConfig {
  platform: 'twitter' | 'facebook' | 'instagram' | 'linkedin' | 'tiktok' | 'youtube' | 'pinterest';
  enabled: boolean;
  credentials: {
    apiKey?: string;
    apiSecret?: string;
    accessToken?: string;
    accessTokenSecret?: string;
    appId?: string;
    appSecret?: string;
    pageId?: string;
    businessAccountId?: string;
  };
  autoPost: boolean;
  hashtagStrategy: 'automatic' | 'manual' | 'trending';
  contentTypes: ('text' | 'image' | 'video' | 'carousel' | 'story')[];
}

export interface SocialPost {
  id: string;
  platform: string;
  content: string;
  media?: {
    type: 'image' | 'video' | 'gif';
    url: string;
    alt?: string;
  }[];
  hashtags: string[];
  mentions: string[];
  scheduledAt?: Date;
  publishedAt?: Date;
  status: 'draft' | 'scheduled' | 'published' | 'failed';
  metrics?: {
    impressions?: number;
    engagements?: number;
    likes?: number;
    shares?: number;
    comments?: number;
    clicks?: number;
    saves?: number;
  };
  campaignId?: string;
  appVariant?: string;
}

export interface ContentTemplate {
  id: string;
  name: string;
  type: 'announcement' | 'feature' | 'tip' | 'testimonial' | 'promotion' | 'educational';
  platforms: string[];
  template: string;
  variables: string[];
  hashtags: string[];
  schedulingRules?: {
    daysOfWeek: number[];
    timeSlots: string[];
    frequency: 'daily' | 'weekly' | 'biweekly' | 'monthly';
  };
}

export interface SocialMetrics {
  platform: string;
  period: 'day' | 'week' | 'month' | 'quarter';
  followers: number;
  followersGrowth: number;
  impressions: number;
  engagements: number;
  engagementRate: number;
  clicks: number;
  conversions: number;
  topPosts: SocialPost[];
  demographics: {
    ageGroups: Record<string, number>;
    genders: Record<string, number>;
    locations: Record<string, number>;
  };
}

class SocialIntegrationManager {
  private platforms: Map<string, SocialPlatformConfig> = new Map();
  private contentTemplates: Map<string, ContentTemplate> = new Map();
  private postQueue: SocialPost[] = [];
  private publishedPosts: Map<string, SocialPost> = new Map();

  constructor() {
    this.initializeDefaultTemplates();
  }

  public configurePlatform(config: SocialPlatformConfig): void {
    this.platforms.set(config.platform, config);
  }

  public async publishPost(post: Omit<SocialPost, 'id' | 'status'>): Promise<SocialPost> {
    const socialPost: SocialPost = {
      ...post,
      id: this.generateId(),
      status: 'draft',
    };

    try {
      if (post.scheduledAt && post.scheduledAt > new Date()) {
        socialPost.status = 'scheduled';
        this.postQueue.push(socialPost);
        this.schedulePost(socialPost);
      } else {
        await this.publishToplatform(socialPost);
        socialPost.status = 'published';
        socialPost.publishedAt = new Date();
        this.publishedPosts.set(socialPost.id, socialPost);
      }

      return socialPost;
    } catch (error) {
      console.error(`Failed to publish post to ${post.platform}:`, error);
      socialPost.status = 'failed';
      return socialPost;
    }
  }

  public async publishToTwitter(post: SocialPost): Promise<void> {
    const config = this.platforms.get('twitter');
    if (!config?.enabled || !config.credentials.accessToken) {
      throw new Error('Twitter not configured');
    }

    const client = new TwitterApi({
      appKey: config.credentials.apiKey!,
      appSecret: config.credentials.apiSecret!,
      accessToken: config.credentials.accessToken!,
      accessSecret: config.credentials.accessTokenSecret!,
    });

    let mediaIds: string[] = [];
    
    // Upload media if present
    if (post.media && post.media.length > 0) {
      for (const media of post.media) {
        if (media.type === 'image') {
          const mediaId = await client.v1.uploadMedia(media.url, {
            mimeType: 'image/jpeg',
            additionalOwners: [],
          });
          mediaIds.push(mediaId);
        }
      }
    }

    // Create tweet content with hashtags
    const content = this.formatContentForPlatform(post.content, post.hashtags, 'twitter');

    const tweet = await client.v2.tweet({
      text: content,
      media: mediaIds.length > 0 ? { media_ids: mediaIds } : undefined,
    });

    console.log('Tweet published:', tweet.data.id);
  }

  public async publishToFacebook(post: SocialPost): Promise<void> {
    const config = this.platforms.get('facebook');
    if (!config?.enabled || !config.credentials.accessToken || !config.credentials.pageId) {
      throw new Error('Facebook not configured');
    }

    const endpoint = `https://graph.facebook.com/v18.0/${config.credentials.pageId}/posts`;
    const content = this.formatContentForPlatform(post.content, post.hashtags, 'facebook');

    const payload: any = {
      message: content,
      access_token: config.credentials.accessToken,
    };

    // Add media if present
    if (post.media && post.media.length > 0) {
      const media = post.media[0]; // Facebook posts typically use one main image
      if (media.type === 'image') {
        payload.link = media.url;
      }
    }

    const response = await axios.post(endpoint, payload);
    console.log('Facebook post published:', response.data.id);
  }

  public async publishToLinkedIn(post: SocialPost): Promise<void> {
    const config = this.platforms.get('linkedin');
    if (!config?.enabled || !config.credentials.accessToken) {
      throw new Error('LinkedIn not configured');
    }

    const endpoint = 'https://api.linkedin.com/v2/ugcPosts';
    const content = this.formatContentForPlatform(post.content, post.hashtags, 'linkedin');

    const payload = {
      author: `urn:li:person:${config.credentials.businessAccountId}`,
      lifecycleState: 'PUBLISHED',
      specificContent: {
        'com.linkedin.ugc.ShareContent': {
          shareCommentary: {
            text: content,
          },
          shareMediaCategory: 'NONE',
        },
      },
      visibility: {
        'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC',
      },
    };

    // Add media if present
    if (post.media && post.media.length > 0) {
      const media = post.media[0];
      payload.specificContent['com.linkedin.ugc.ShareContent'].shareMediaCategory = 'IMAGE';
      // Note: LinkedIn media upload is more complex and requires separate API calls
    }

    const response = await axios.post(endpoint, payload, {
      headers: {
        'Authorization': `Bearer ${config.credentials.accessToken}`,
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0',
      },
    });

    console.log('LinkedIn post published:', response.data.id);
  }

  public async scheduleContentSeries(
    templateId: string,
    variables: Record<string, string>,
    startDate: Date,
    platforms: string[]
  ): Promise<SocialPost[]> {
    const template = this.contentTemplates.get(templateId);
    if (!template) {
      throw new Error(`Template ${templateId} not found`);
    }

    const posts: SocialPost[] = [];
    let currentDate = new Date(startDate);

    // Generate posts based on template scheduling rules
    for (let i = 0; i < 30; i++) { // Generate for next 30 intervals
      if (template.schedulingRules) {
        const dayOfWeek = currentDate.getDay();
        if (!template.schedulingRules.daysOfWeek.includes(dayOfWeek)) {
          currentDate = this.getNextScheduleDate(currentDate, template.schedulingRules.frequency);
          continue;
        }
      }

      for (const platform of platforms.filter(p => template.platforms.includes(p))) {
        const content = this.processTemplate(template.template, variables);
        const post: SocialPost = {
          id: this.generateId(),
          platform,
          content,
          hashtags: template.hashtags,
          mentions: [],
          scheduledAt: new Date(currentDate),
          status: 'scheduled',
          campaignId: `series_${templateId}_${Date.now()}`,
        };

        posts.push(post);
        await this.publishPost(post);
      }

      currentDate = this.getNextScheduleDate(currentDate, template.schedulingRules?.frequency || 'weekly');
    }

    return posts;
  }

  public async getMetrics(platform: string, period: 'day' | 'week' | 'month' = 'week'): Promise<SocialMetrics> {
    const config = this.platforms.get(platform);
    if (!config?.enabled) {
      throw new Error(`Platform ${platform} not configured`);
    }

    switch (platform) {
      case 'twitter':
        return await this.getTwitterMetrics(period);
      case 'facebook':
        return await this.getFacebookMetrics(period);
      case 'linkedin':
        return await this.getLinkedInMetrics(period);
      default:
        throw new Error(`Metrics not implemented for ${platform}`);
    }
  }

  public generateContentFromTemplate(
    type: 'feature_announcement' | 'tip_of_the_day' | 'user_testimonial' | 'product_update',
    appVariant: string,
    customData?: Record<string, any>
  ): string {
    const templates = {
      feature_announcement: {
        'personal-log': "🎉 New in PersonalLog: {feature}! {description} Perfect for {target_audience}. #PersonalLog #DigitalJournal #Mindfulness",
        'business-log': "🚀 BusinessLog Update: {feature} is here! {description} Boost your team's productivity. #BusinessLog #Productivity #TeamWork",
        'fitness-log': "💪 FitnessLog Enhancement: {feature}! {description} Take your fitness journey to the next level. #FitnessLog #Health #Fitness",
        'family-log': "👨‍👩‍👧‍👦 FamilyLog Feature: {feature}! {description} Bringing families closer together. #FamilyLog #Family #Memories",
        'travel-log': "✈️ TravelLog Addition: {feature}! {description} Make every journey memorable. #TravelLog #Travel #Adventure",
        'education-log': "📚 EducationLog Update: {feature}! {description} Enhance your learning experience. #EducationLog #Education #Learning",
      },
      tip_of_the_day: {
        'personal-log': "💡 PersonalLog Tip: {tip} Try this today and see the difference! #PersonalGrowth #Journaling #Mindfulness",
        'business-log': "🎯 BusinessLog Pro Tip: {tip} Small changes, big results! #ProductivityTip #Business #Efficiency",
        'fitness-log': "🏋️ Fitness Tip: {tip} Your body will thank you! #FitnessTip #Health #Wellness",
        'family-log': "🏠 Family Tip: {tip} Strengthen your family bonds! #FamilyTip #Parenting #FamilyTime",
        'travel-log': "🗺️ Travel Tip: {tip} Make your next trip unforgettable! #TravelTip #Travel #Adventure",
        'education-log': "🎓 Study Tip: {tip} Boost your academic success! #StudyTip #Education #Learning",
      },
      user_testimonial: {
        'personal-log': "💝 '{testimonial}' - {user_name} Thank you for sharing your PersonalLog journey! #UserLove #Testimonial #PersonalGrowth",
        'business-log': "🙌 '{testimonial}' - {user_name}, {company} Success stories like this fuel our passion! #CustomerSuccess #Business #Productivity",
        'fitness-log': "🏆 '{testimonial}' - {user_name} Incredible transformation! Keep crushing those goals! #FitnessSuccess #Transformation #Motivation",
        'family-log': "❤️ '{testimonial}' - {user_name} Family connections matter! #FamilySuccess #Love #Connection",
        'travel-log': "🌟 '{testimonial}' - {user_name} Adventures made better with TravelLog! #TravelSuccess #Memories #Adventure",
        'education-log': "📈 '{testimonial}' - {user_name} Academic success unlocked! #StudentSuccess #Education #Achievement",
      },
      product_update: {
        'personal-log': "🔄 PersonalLog v{version} is live! {changes} Download now and continue your mindfulness journey. #Update #PersonalLog",
        'business-log': "📊 BusinessLog v{version} released! {changes} Keep your team ahead of the curve. #Update #Business #Productivity",
        'fitness-log': "⚡ FitnessLog v{version} drops today! {changes} Your fitness goals just got easier. #Update #Fitness #Health",
        'family-log': "🎈 FamilyLog v{version} is here! {changes} More ways to stay connected with loved ones. #Update #Family",
        'travel-log': "🎒 TravelLog v{version} launched! {changes} Adventure planning made simple. #Update #Travel",
        'education-log': "🎯 EducationLog v{version} available now! {changes} Study smarter, not harder. #Update #Education",
      },
    };

    const template = templates[type][appVariant as keyof typeof templates[typeof type]];
    return this.processTemplate(template, customData || {});
  }

  private async publishToplatform(post: SocialPost): Promise<void> {
    switch (post.platform) {
      case 'twitter':
        await this.publishToTwitter(post);
        break;
      case 'facebook':
        await this.publishToFacebook(post);
        break;
      case 'linkedin':
        await this.publishToLinkedIn(post);
        break;
      default:
        throw new Error(`Publishing to ${post.platform} not implemented`);
    }
  }

  private formatContentForPlatform(content: string, hashtags: string[], platform: string): string {
    let formattedContent = content;
    let hashtagString = hashtags.map(tag => tag.startsWith('#') ? tag : `#${tag}`).join(' ');

    switch (platform) {
      case 'twitter':
        // Twitter has character limits
        const maxLength = 280;
        const availableLength = maxLength - hashtagString.length - 1;
        if (formattedContent.length > availableLength) {
          formattedContent = formattedContent.substring(0, availableLength - 3) + '...';
        }
        return `${formattedContent} ${hashtagString}`;

      case 'linkedin':
        // LinkedIn allows longer content and hashtags work better at the end
        return `${formattedContent}\n\n${hashtagString}`;

      case 'facebook':
        // Facebook integrates hashtags more naturally
        return `${formattedContent} ${hashtagString}`;

      default:
        return `${formattedContent} ${hashtagString}`;
    }
  }

  private schedulePost(post: SocialPost): void {
    if (!post.scheduledAt) return;

    const delay = post.scheduledAt.getTime() - new Date().getTime();
    if (delay > 0) {
      setTimeout(async () => {
        try {
          await this.publishToplatform(post);
          post.status = 'published';
          post.publishedAt = new Date();
          this.publishedPosts.set(post.id, post);
          
          // Remove from queue
          const index = this.postQueue.findIndex(p => p.id === post.id);
          if (index > -1) {
            this.postQueue.splice(index, 1);
          }
        } catch (error) {
          console.error('Failed to publish scheduled post:', error);
          post.status = 'failed';
        }
      }, delay);
    }
  }

  private async getTwitterMetrics(period: string): Promise<SocialMetrics> {
    // Implement Twitter Analytics API integration
    return {
      platform: 'twitter',
      period: period as any,
      followers: 0,
      followersGrowth: 0,
      impressions: 0,
      engagements: 0,
      engagementRate: 0,
      clicks: 0,
      conversions: 0,
      topPosts: [],
      demographics: {
        ageGroups: {},
        genders: {},
        locations: {},
      },
    };
  }

  private async getFacebookMetrics(period: string): Promise<SocialMetrics> {
    // Implement Facebook Graph API integration
    return {
      platform: 'facebook',
      period: period as any,
      followers: 0,
      followersGrowth: 0,
      impressions: 0,
      engagements: 0,
      engagementRate: 0,
      clicks: 0,
      conversions: 0,
      topPosts: [],
      demographics: {
        ageGroups: {},
        genders: {},
        locations: {},
      },
    };
  }

  private async getLinkedInMetrics(period: string): Promise<SocialMetrics> {
    // Implement LinkedIn Marketing API integration
    return {
      platform: 'linkedin',
      period: period as any,
      followers: 0,
      followersGrowth: 0,
      impressions: 0,
      engagements: 0,
      engagementRate: 0,
      clicks: 0,
      conversions: 0,
      topPosts: [],
      demographics: {
        ageGroups: {},
        genders: {},
        locations: {},
      },
    };
  }

  private processTemplate(template: string, variables: Record<string, any>): string {
    return template.replace(/{(\w+)}/g, (match, key) => {
      return variables[key] || match;
    });
  }

  private getNextScheduleDate(currentDate: Date, frequency: string): Date {
    const nextDate = new Date(currentDate);
    switch (frequency) {
      case 'daily':
        nextDate.setDate(nextDate.getDate() + 1);
        break;
      case 'weekly':
        nextDate.setDate(nextDate.getDate() + 7);
        break;
      case 'biweekly':
        nextDate.setDate(nextDate.getDate() + 14);
        break;
      case 'monthly':
        nextDate.setMonth(nextDate.getMonth() + 1);
        break;
    }
    return nextDate;
  }

  private generateId(): string {
    return `social_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private initializeDefaultTemplates(): void {
    const defaultTemplates: ContentTemplate[] = [
      {
        id: 'feature_announcement',
        name: 'Feature Announcement',
        type: 'announcement',
        platforms: ['twitter', 'facebook', 'linkedin'],
        template: '🎉 New Feature: {feature_name}! {description} Try it now: {link} #NewFeature #{app_variant}',
        variables: ['feature_name', 'description', 'link', 'app_variant'],
        hashtags: ['NewFeature', 'ProductUpdate'],
        schedulingRules: {
          daysOfWeek: [1, 2, 3, 4, 5], // Monday to Friday
          timeSlots: ['09:00', '14:00'],
          frequency: 'weekly',
        },
      },
      {
        id: 'daily_tip',
        name: 'Daily Tip',
        type: 'tip',
        platforms: ['twitter', 'facebook'],
        template: '💡 Tip of the day: {tip_content} What\'s your favorite productivity hack? #TipOfTheDay #Productivity',
        variables: ['tip_content'],
        hashtags: ['TipOfTheDay', 'Productivity'],
        schedulingRules: {
          daysOfWeek: [1, 2, 3, 4, 5, 6, 7], // Every day
          timeSlots: ['08:00'],
          frequency: 'daily',
        },
      },
      {
        id: 'user_testimonial',
        name: 'User Testimonial',
        type: 'testimonial',
        platforms: ['twitter', 'facebook', 'linkedin'],
        template: '💝 "{testimonial}" - {user_name} Thank you for sharing your experience! #CustomerLove #Testimonial',
        variables: ['testimonial', 'user_name'],
        hashtags: ['CustomerLove', 'Testimonial'],
        schedulingRules: {
          daysOfWeek: [2, 4], // Tuesday and Thursday
          timeSlots: ['11:00'],
          frequency: 'weekly',
        },
      },
    ];

    defaultTemplates.forEach(template => {
      this.contentTemplates.set(template.id, template);
    });
  }

  public getScheduledPosts(): SocialPost[] {
    return this.postQueue;
  }

  public getPublishedPosts(): SocialPost[] {
    return Array.from(this.publishedPosts.values());
  }

  public cancelScheduledPost(postId: string): boolean {
    const index = this.postQueue.findIndex(post => post.id === postId);
    if (index > -1) {
      this.postQueue.splice(index, 1);
      return true;
    }
    return false;
  }
}

export default SocialIntegrationManager;