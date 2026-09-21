// import { InstagramApi } from 'instagram-private-api';
// import { TwitterApi } from 'twitter-api-v2';
// import axios from 'axios';
// import puppeteer from 'puppeteer';
// import sharp from 'sharp';
// import ffmpeg from 'fluent-ffmpeg';
import cron from 'node-cron';
import logger from '../lib/logger.js';
import config from '../config/config.js';

class SocialMediaService {
  constructor(redis) {
    this.redis = redis;
    this.platforms = new Map();
    this.scheduledPosts = new Map();
    this.automationRules = new Map();
    this.crossPostingEnabled = true;
    this.contentQueue = [];
    this.postHistory = [];
    this.analytics = {
      totalPosts: 0,
      successfulPosts: 0,
      failedPosts: 0,
      engagement: {}
    };
  }

  async initialize() {
    try {
      // Initialize platform connections
      await this.initializePlatforms();
      
      // Start scheduled posting service
      this.startScheduledPosting();
      
      // Start cross-platform synchronization
      this.startCrossPlatformSync();
      
      logger.info('Social Media Service initialized');
    } catch (error) {
      logger.error('Failed to initialize Social Media Service:', error);
      throw error;
    }
  }

  async initializePlatforms() {
    // Instagram
    if (config.socialMedia.instagram.clientId) {
      try {
        const instagram = new InstagramApi();
        this.platforms.set('instagram', {
          api: instagram,
          connected: false,
          rateLimits: { posts: 25, stories: 100, reels: 25 }, // per day
          features: ['posts', 'stories', 'reels', 'igtv', 'shopping']
        });
      } catch (error) {
        logger.warn('Instagram initialization failed:', error.message);
      }
    }

    // Twitter
    if (config.socialMedia && config.socialMedia.twitter && config.socialMedia.twitter.apiKey) {
      try {
        // const twitter = new TwitterApi({
        //   appKey: config.socialMedia.twitter.apiKey,
        //   appSecret: config.socialMedia.twitter.apiSecret,
        //   accessToken: config.socialMedia.twitter.accessToken,
        //   accessSecret: config.socialMedia.twitter.accessTokenSecret
        // });
        const twitter = null; // Mock for now
        
        this.platforms.set('twitter', {
          api: twitter,
          connected: true,
          rateLimits: { tweets: 300, retweets: 300, likes: 1000 }, // per 15 min
          features: ['tweets', 'threads', 'spaces', 'fleets']
        });
      } catch (error) {
        logger.warn('Twitter initialization failed:', error.message);
      }
    }

    // Facebook
    if (config.socialMedia.facebook.appId) {
      this.platforms.set('facebook', {
        api: null, // Will use Graph API directly
        connected: true,
        rateLimits: { posts: 25, pages: 200 }, // per hour
        features: ['posts', 'stories', 'reels', 'live', 'events']
      });
    }

    // YouTube
    if (config.socialMedia.youtube.apiKey) {
      this.platforms.set('youtube', {
        api: null, // Will use YouTube Data API
        connected: true,
        rateLimits: { uploads: 6, comments: 100 }, // per day/hour
        features: ['videos', 'shorts', 'live', 'community']
      });
    }

    // TikTok
    if (config.socialMedia.tiktok.clientId) {
      this.platforms.set('tiktok', {
        api: null, // Will use TikTok API
        connected: true,
        rateLimits: { videos: 10, comments: 100 }, // per day
        features: ['videos', 'effects', 'sounds']
      });
    }

    // LinkedIn
    if (config.socialMedia.linkedin.clientId) {
      this.platforms.set('linkedin', {
        api: null, // Will use LinkedIn API
        connected: true,
        rateLimits: { posts: 150, shares: 150 }, // per day
        features: ['posts', 'articles', 'newsletters', 'events']
      });
    }

    // Pinterest
    if (config.socialMedia.pinterest.clientId) {
      this.platforms.set('pinterest', {
        api: null, // Will use Pinterest API
        connected: true,
        rateLimits: { pins: 1000, boards: 10 }, // per day
        features: ['pins', 'boards', 'stories', 'shopping']
      });
    }

    // Twitch
    if (config.socialMedia.twitch.clientId) {
      this.platforms.set('twitch', {
        api: null, // Will use Twitch API
        connected: true,
        rateLimits: { clips: 100, streams: 1 }, // per day
        features: ['streams', 'clips', 'chat', 'raids']
      });
    }

    // Discord
    if (config.socialMedia.discord.token) {
      const { Client, GatewayIntentBits } = await import('discord.js');
      const discord = new Client({ 
        intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages] 
      });
      
      this.platforms.set('discord', {
        api: discord,
        connected: false,
        rateLimits: { messages: 50, embeds: 10 }, // per second
        features: ['messages', 'embeds', 'threads', 'voice']
      });
    }

    // Additional platforms...
    this.initializeAdditionalPlatforms();
  }

  async initializeAdditionalPlatforms() {
    // Telegram
    if (config.socialMedia.telegram.botToken) {
      this.platforms.set('telegram', {
        api: null,
        connected: true,
        rateLimits: { messages: 30, media: 20 }, // per second
        features: ['messages', 'media', 'polls', 'stickers']
      });
    }

    // Snapchat
    if (config.socialMedia.snapchat.clientId) {
      this.platforms.set('snapchat', {
        api: null,
        connected: true,
        rateLimits: { stories: 10, ads: 100 }, // per day
        features: ['stories', 'lenses', 'ads']
      });
    }

    // Reddit
    if (config.socialMedia.reddit.clientId) {
      this.platforms.set('reddit', {
        api: null,
        connected: true,
        rateLimits: { posts: 5, comments: 100 }, // per hour
        features: ['posts', 'comments', 'awards', 'communities']
      });
    }
  }

  // Post content across multiple platforms
  async postContent(content, platforms = [], scheduledTime = null) {
    try {
      const postId = `post_${Date.now()}`;
      const results = [];

      // Validate content
      const validatedContent = await this.validateContent(content);
      
      // Process media if present
      if (content.media) {
        validatedContent.processedMedia = await this.processMedia(content.media);
      }

      // If scheduled, add to queue
      if (scheduledTime) {
        return await this.schedulePost(validatedContent, platforms, scheduledTime);
      }

      // Post immediately to selected platforms
      for (const platformName of platforms) {
        if (this.platforms.has(platformName)) {
          try {
            const result = await this.postToPlatform(platformName, validatedContent);
            results.push({ platform: platformName, success: true, data: result });
            this.analytics.successfulPosts++;
          } catch (error) {
            logger.error(`Failed to post to ${platformName}:`, error);
            results.push({ platform: platformName, success: false, error: error.message });
            this.analytics.failedPosts++;
          }
        }
      }

      // Store post history
      this.postHistory.push({
        id: postId,
        content: validatedContent,
        platforms,
        timestamp: new Date(),
        results
      });

      // Update analytics
      this.analytics.totalPosts++;
      
      logger.social('Content posted across platforms', platforms.join(','), {
        postId,
        platforms,
        results: results.length
      });

      return {
        postId,
        results,
        success: results.some(r => r.success)
      };

    } catch (error) {
      logger.error('Failed to post content:', error);
      throw error;
    }
  }

  async postToPlatform(platform, content) {
    const platformConfig = this.platforms.get(platform);
    if (!platformConfig || !platformConfig.connected) {
      throw new Error(`Platform ${platform} not connected`);
    }

    // Check rate limits
    await this.checkRateLimits(platform);

    switch (platform) {
      case 'instagram':
        return await this.postToInstagram(content);
      case 'twitter':
        return await this.postToTwitter(content);
      case 'facebook':
        return await this.postToFacebook(content);
      case 'youtube':
        return await this.postToYouTube(content);
      case 'tiktok':
        return await this.postToTikTok(content);
      case 'linkedin':
        return await this.postToLinkedIn(content);
      case 'pinterest':
        return await this.postToPinterest(content);
      case 'twitch':
        return await this.postToTwitch(content);
      case 'discord':
        return await this.postToDiscord(content);
      case 'telegram':
        return await this.postToTelegram(content);
      case 'snapchat':
        return await this.postToSnapchat(content);
      case 'reddit':
        return await this.postToReddit(content);
      default:
        throw new Error(`Platform ${platform} not supported`);
    }
  }

  async postToInstagram(content) {
    const instagram = this.platforms.get('instagram').api;
    
    if (content.type === 'story') {
      return await instagram.publish.story({
        file: content.processedMedia.path,
        caption: content.text
      });
    } else if (content.type === 'reel') {
      return await instagram.publish.video({
        video: content.processedMedia.path,
        caption: content.text,
        isReel: true
      });
    } else {
      // Regular post
      if (content.processedMedia) {
        if (content.processedMedia.type === 'image') {
          return await instagram.publish.photo({
            file: content.processedMedia.path,
            caption: content.text
          });
        } else if (content.processedMedia.type === 'video') {
          return await instagram.publish.video({
            video: content.processedMedia.path,
            caption: content.text
          });
        }
      } else {
        // Text-only not supported on Instagram directly
        throw new Error('Instagram requires media content');
      }
    }
  }

  async postToTwitter(content) {
    const twitter = this.platforms.get('twitter').api;
    
    if (content.type === 'thread') {
      // Post as thread
      const tweets = content.text.split('\n\n').filter(t => t.trim());
      let previousTweetId = null;
      const tweetIds = [];

      for (const tweet of tweets) {
        const tweetData = {
          text: tweet,
          ...(previousTweetId && { reply: { in_reply_to_tweet_id: previousTweetId } })
        };

        const response = await twitter.v2.tweet(tweetData);
        previousTweetId = response.data.id;
        tweetIds.push(previousTweetId);
      }

      return { threadIds: tweetIds };
    } else {
      // Regular tweet
      const tweetData = { text: content.text };
      
      if (content.processedMedia) {
        const mediaId = await twitter.v1.uploadMedia(content.processedMedia.path);
        tweetData.media = { media_ids: [mediaId] };
      }

      return await twitter.v2.tweet(tweetData);
    }
  }

  async postToFacebook(content) {
    const accessToken = config.socialMedia.facebook.accessToken;
    const pageId = content.pageId || 'me';
    
    const params = {
      message: content.text,
      access_token: accessToken
    };

    if (content.processedMedia) {
      if (content.processedMedia.type === 'image') {
        params.url = content.processedMedia.url;
      } else if (content.processedMedia.type === 'video') {
        params.source = content.processedMedia.url;
      }
    }

    const response = await axios.post(
      `https://graph.facebook.com/v18.0/${pageId}/feed`,
      params
    );

    return response.data;
  }

  async postToYouTube(content) {
    if (content.type !== 'video') {
      throw new Error('YouTube only supports video content');
    }

    // YouTube video upload requires OAuth 2.0 flow
    const response = await axios.post('https://www.googleapis.com/upload/youtube/v3/videos', {
      part: 'snippet,status',
      snippet: {
        title: content.title || 'Untitled Video',
        description: content.text,
        tags: content.tags || [],
        categoryId: content.categoryId || '22'
      },
      status: {
        privacyStatus: content.privacy || 'public'
      }
    }, {
      headers: {
        'Authorization': `Bearer ${config.socialMedia.youtube.accessToken}`,
        'Content-Type': 'application/json'
      }
    });

    return response.data;
  }

  async postToTikTok(content) {
    if (content.type !== 'video') {
      throw new Error('TikTok only supports video content');
    }

    // TikTok API implementation
    const response = await axios.post('https://open-api.tiktok.com/share/video/upload/', {
      video_url: content.processedMedia.url,
      description: content.text,
      privacy_level: content.privacy || 'PUBLIC_TO_EVERYONE'
    }, {
      headers: {
        'Authorization': `Bearer ${config.socialMedia.tiktok.accessToken}`,
        'Content-Type': 'application/json'
      }
    });

    return response.data;
  }

  async postToLinkedIn(content) {
    const response = await axios.post('https://api.linkedin.com/v2/ugcPosts', {
      author: `urn:li:person:${content.authorId}`,
      lifecycleState: 'PUBLISHED',
      specificContent: {
        'com.linkedin.ugc.ShareContent': {
          shareCommentary: {
            text: content.text
          },
          shareMediaCategory: content.processedMedia ? 'IMAGE' : 'NONE',
          ...(content.processedMedia && {
            media: [{
              status: 'READY',
              description: {
                text: content.text
              },
              media: content.processedMedia.url,
              title: {
                text: content.title || 'Post'
              }
            }]
          })
        }
      },
      visibility: {
        'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
      }
    }, {
      headers: {
        'Authorization': `Bearer ${config.socialMedia.linkedin.accessToken}`,
        'Content-Type': 'application/json'
      }
    });

    return response.data;
  }

  async postToPinterest(content) {
    if (!content.processedMedia || content.processedMedia.type !== 'image') {
      throw new Error('Pinterest requires image content');
    }

    const response = await axios.post('https://api.pinterest.com/v5/pins', {
      link: content.link || '',
      title: content.title || content.text.substring(0, 100),
      description: content.text,
      dominant_color: content.dominantColor || '#000000',
      alt_text: content.altText || content.text,
      board_id: content.boardId,
      media_source: {
        source_type: 'image_url',
        url: content.processedMedia.url
      }
    }, {
      headers: {
        'Authorization': `Bearer ${config.socialMedia.pinterest.accessToken}`,
        'Content-Type': 'application/json'
      }
    });

    return response.data;
  }

  async postToDiscord(content) {
    const discord = this.platforms.get('discord').api;
    const channel = discord.channels.cache.get(content.channelId);
    
    if (!channel) {
      throw new Error('Discord channel not found');
    }

    const messageOptions = {
      content: content.text
    };

    if (content.processedMedia) {
      messageOptions.files = [content.processedMedia.path];
    }

    if (content.embed) {
      messageOptions.embeds = [content.embed];
    }

    return await channel.send(messageOptions);
  }

  async postToTelegram(content) {
    const botToken = config.socialMedia.telegram.botToken;
    const chatId = content.chatId;

    if (content.processedMedia) {
      let method = 'sendPhoto';
      if (content.processedMedia.type === 'video') {
        method = 'sendVideo';
      }

      const response = await axios.post(`https://api.telegram.org/bot${botToken}/${method}`, {
        chat_id: chatId,
        [content.processedMedia.type]: content.processedMedia.url,
        caption: content.text
      });

      return response.data;
    } else {
      const response = await axios.post(`https://api.telegram.org/bot${botToken}/sendMessage`, {
        chat_id: chatId,
        text: content.text,
        parse_mode: 'HTML'
      });

      return response.data;
    }
  }

  async postToReddit(content) {
    // Reddit API implementation
    const response = await axios.post('https://oauth.reddit.com/api/submit', {
      api_type: 'json',
      kind: content.processedMedia ? 'link' : 'self',
      sr: content.subreddit,
      title: content.title,
      text: content.processedMedia ? undefined : content.text,
      url: content.processedMedia ? content.processedMedia.url : undefined
    }, {
      headers: {
        'Authorization': `Bearer ${config.socialMedia.reddit.accessToken}`,
        'User-Agent': 'RealLogPro/1.0.0'
      }
    });

    return response.data;
  }

  // Content validation and processing
  async validateContent(content) {
    // Validate required fields
    if (!content.text && !content.media) {
      throw new Error('Content must include text or media');
    }

    // Platform-specific validation
    const validated = { ...content };

    // Text length validation
    if (validated.text) {
      validated.text = validated.text.trim();
      if (validated.text.length === 0 && !validated.media) {
        throw new Error('Content cannot be empty');
      }
    }

    // Add hashtags and mentions processing
    validated.hashtags = this.extractHashtags(validated.text || '');
    validated.mentions = this.extractMentions(validated.text || '');

    return validated;
  }

  async processMedia(media) {
    try {
      const processed = { ...media };

      if (media.type === 'image') {
        // Optimize image for different platforms
        processed.optimized = await this.optimizeImage(media);
      } else if (media.type === 'video') {
        // Process video for different platforms
        processed.optimized = await this.processVideo(media);
      }

      return processed;
    } catch (error) {
      logger.error('Media processing failed:', error);
      throw error;
    }
  }

  async optimizeImage(image) {
    const optimizations = {};

    // Instagram optimization (1080x1080 for square, 1080x1350 for portrait)
    optimizations.instagram = await sharp(image.path)
      .resize(1080, 1080, { fit: 'cover' })
      .jpeg({ quality: 90 })
      .toBuffer();

    // Twitter optimization (1200x675)
    optimizations.twitter = await sharp(image.path)
      .resize(1200, 675, { fit: 'cover' })
      .jpeg({ quality: 85 })
      .toBuffer();

    // Facebook optimization (1200x630)
    optimizations.facebook = await sharp(image.path)
      .resize(1200, 630, { fit: 'cover' })
      .jpeg({ quality: 85 })
      .toBuffer();

    // Pinterest optimization (1000x1500)
    optimizations.pinterest = await sharp(image.path)
      .resize(1000, 1500, { fit: 'cover' })
      .jpeg({ quality: 90 })
      .toBuffer();

    return optimizations;
  }

  async processVideo(video) {
    const processed = {};

    return new Promise((resolve, reject) => {
      // Instagram Reels (9:16 aspect ratio, max 90 seconds)
      ffmpeg(video.path)
        .aspect('9:16')
        .duration(90)
        .videoCodec('libx264')
        .audioCodec('aac')
        .save(video.path.replace(/\.[^/.]+$/, '_instagram.mp4'))
        .on('end', () => {
          processed.instagram = video.path.replace(/\.[^/.]+$/, '_instagram.mp4');
          
          // TikTok (9:16, max 10 minutes)
          ffmpeg(video.path)
            .aspect('9:16')
            .duration(600)
            .videoCodec('libx264')
            .audioCodec('aac')
            .save(video.path.replace(/\.[^/.]+$/, '_tiktok.mp4'))
            .on('end', () => {
              processed.tiktok = video.path.replace(/\.[^/.]+$/, '_tiktok.mp4');
              
              // YouTube Shorts (9:16, max 60 seconds)
              ffmpeg(video.path)
                .aspect('9:16')
                .duration(60)
                .videoCodec('libx264')
                .audioCodec('aac')
                .save(video.path.replace(/\.[^/.]+$/, '_youtube_shorts.mp4'))
                .on('end', () => {
                  processed.youtubeShorts = video.path.replace(/\.[^/.]+$/, '_youtube_shorts.mp4');
                  resolve(processed);
                })
                .on('error', reject);
            })
            .on('error', reject);
        })
        .on('error', reject);
    });
  }

  // Scheduling and automation
  async schedulePost(content, platforms, scheduledTime) {
    const scheduleId = `schedule_${Date.now()}`;
    
    const scheduledPost = {
      id: scheduleId,
      content,
      platforms,
      scheduledTime: new Date(scheduledTime),
      status: 'scheduled',
      createdAt: new Date()
    };

    this.scheduledPosts.set(scheduleId, scheduledPost);
    
    // Store in Redis for persistence
    await this.redis.set(
      `scheduled_post:${scheduleId}`, 
      JSON.stringify(scheduledPost),
      'EX',
      60 * 60 * 24 * 30 // 30 days
    );

    logger.social('Post scheduled', platforms.join(','), {
      scheduleId,
      scheduledTime,
      platforms
    });

    return { scheduleId, scheduledTime: scheduledPost.scheduledTime };
  }

  startScheduledPosting() {
    // Check for scheduled posts every minute
    cron.schedule('* * * * *', async () => {
      const now = new Date();
      
      for (const [scheduleId, post] of this.scheduledPosts) {
        if (post.scheduledTime <= now && post.status === 'scheduled') {
          try {
            post.status = 'posting';
            const result = await this.postContent(post.content, post.platforms);
            
            post.status = 'completed';
            post.result = result;
            post.completedAt = new Date();
            
            // Remove from scheduled posts
            this.scheduledPosts.delete(scheduleId);
            await this.redis.del(`scheduled_post:${scheduleId}`);
            
            logger.social('Scheduled post completed', post.platforms.join(','), {
              scheduleId,
              result: result.success
            });
          } catch (error) {
            post.status = 'failed';
            post.error = error.message;
            post.failedAt = new Date();
            
            logger.error(`Scheduled post failed: ${scheduleId}`, error);
          }
        }
      }
    });
  }

  startCrossPlatformSync() {
    // Sync content across platforms with platform-specific optimizations
    cron.schedule('0 */6 * * *', async () => { // Every 6 hours
      try {
        await this.syncCrossPlatformContent();
        logger.info('Cross-platform sync completed');
      } catch (error) {
        logger.error('Cross-platform sync failed:', error);
      }
    });
  }

  async syncCrossPlatformContent() {
    // Fetch analytics from each platform
    const platformAnalytics = new Map();
    
    for (const [platformName] of this.platforms) {
      try {
        const analytics = await this.getPlatformAnalytics(platformName);
        platformAnalytics.set(platformName, analytics);
      } catch (error) {
        logger.warn(`Failed to fetch analytics for ${platformName}:`, error.message);
      }
    }

    // Identify top-performing content for cross-posting
    const topContent = this.identifyTopPerformingContent(platformAnalytics);
    
    // Cross-post high-performing content to other platforms
    for (const content of topContent) {
      await this.crossPostContent(content);
    }
  }

  // Utility methods
  extractHashtags(text) {
    const hashtagRegex = /#[a-zA-Z0-9_]+/g;
    return text.match(hashtagRegex) || [];
  }

  extractMentions(text) {
    const mentionRegex = /@[a-zA-Z0-9_]+/g;
    return text.match(mentionRegex) || [];
  }

  async checkRateLimits(platform) {
    const key = `rate_limit:${platform}`;
    const current = await this.redis.get(key);
    const limits = this.platforms.get(platform).rateLimits;
    
    // Simple rate limiting implementation
    if (current && parseInt(current) >= limits.posts) {
      throw new Error(`Rate limit exceeded for ${platform}`);
    }
    
    await this.redis.incr(key);
    await this.redis.expire(key, 3600); // 1 hour window
  }

  async getPlatformAnalytics(platform) {
    // Platform-specific analytics fetching
    // Implementation varies by platform API
    return {};
  }

  identifyTopPerformingContent(analytics) {
    // Analyze content performance and identify top posts
    return [];
  }

  async crossPostContent(content) {
    // Cross-post content to other platforms with optimizations
  }

  async getScheduledPosts() {
    return Array.from(this.scheduledPosts.values());
  }

  async cancelScheduledPost(scheduleId) {
    if (this.scheduledPosts.has(scheduleId)) {
      this.scheduledPosts.delete(scheduleId);
      await this.redis.del(`scheduled_post:${scheduleId}`);
      return true;
    }
    return false;
  }

  getAnalytics() {
    return {
      ...this.analytics,
      platforms: Array.from(this.platforms.keys()),
      scheduledPosts: this.scheduledPosts.size,
      postHistory: this.postHistory.length
    };
  }
}

export default SocialMediaService;