// import axios from 'axios';
// import { TwitterApi } from 'twitter-api-v2';
// import puppeteer from 'puppeteer';
// import natural from 'natural';
// import Sentiment from 'sentiment';
import cron from 'node-cron';
import logger from '../lib/logger.js';
import config from '../config/config.js';

class CommentManagementService {
  constructor(redis) {
    this.redis = redis;
    this.platforms = new Map();
    this.commentFilters = new Map();
    this.moderationRules = new Map();
    this.sentiment = { analyze: (text) => ({ score: 0, comparative: 0 }) }; // Mock sentiment
    this.commentQueue = [];
    this.blockedUsers = new Set();
    this.spamDetector = { addDocument: () => {}, train: () => {}, classify: () => 'legitimate' }; // Mock
    this.toxicityDetector = { addDocument: () => {}, train: () => {}, classify: () => 'clean' }; // Mock
    
    this.analytics = {
      totalComments: 0,
      moderatedComments: 0,
      spamFiltered: 0,
      toxicityFiltered: 0,
      sentimentBreakdown: { positive: 0, negative: 0, neutral: 0 }
    };
    
    this.initializeAIModels();
  }

  async initialize() {
    try {
      await this.initializePlatformAPIs();
      this.startCommentMonitoring();
      this.startBulkModeration();
      await this.loadModerationRules();
      
      logger.info('Comment Management Service initialized');
    } catch (error) {
      logger.error('Failed to initialize Comment Management Service:', error);
      throw error;
    }
  }

  async initializePlatformAPIs() {
    // Instagram
    if (config.socialMedia.instagram.clientId) {
      this.platforms.set('instagram', {
        type: 'instagram',
        rateLimits: { comments: 200, replies: 60 }, // per hour
        features: ['read', 'reply', 'moderate', 'like', 'hide']
      });
    }

    // Twitter
    if (config.socialMedia.twitter.apiKey) {
      const twitter = new TwitterApi({
        appKey: config.socialMedia.twitter.apiKey,
        appSecret: config.socialMedia.twitter.apiSecret,
        accessToken: config.socialMedia.twitter.accessToken,
        accessSecret: config.socialMedia.twitter.accessTokenSecret
      });
      
      this.platforms.set('twitter', {
        api: twitter,
        type: 'twitter',
        rateLimits: { comments: 300, replies: 300 }, // per 15 min
        features: ['read', 'reply', 'retweet', 'like', 'block', 'mute']
      });
    }

    // Facebook/Meta
    if (config.socialMedia.facebook.appId) {
      this.platforms.set('facebook', {
        type: 'facebook',
        rateLimits: { comments: 200, replies: 100 }, // per hour
        features: ['read', 'reply', 'moderate', 'like', 'hide', 'ban']
      });
    }

    // YouTube
    if (config.socialMedia.youtube.apiKey) {
      this.platforms.set('youtube', {
        type: 'youtube',
        rateLimits: { comments: 10000, replies: 1000 }, // per day
        features: ['read', 'reply', 'moderate', 'like', 'report', 'ban']
      });
    }

    // TikTok
    if (config.socialMedia.tiktok.clientId) {
      this.platforms.set('tiktok', {
        type: 'tiktok',
        rateLimits: { comments: 100, replies: 50 }, // per day
        features: ['read', 'reply', 'like', 'report']
      });
    }

    // LinkedIn
    if (config.socialMedia.linkedin.clientId) {
      this.platforms.set('linkedin', {
        type: 'linkedin',
        rateLimits: { comments: 100, replies: 100 }, // per day
        features: ['read', 'reply', 'like', 'moderate']
      });
    }

    // Discord
    if (config.socialMedia.discord.token) {
      this.platforms.set('discord', {
        type: 'discord',
        rateLimits: { messages: 50, reactions: 20 }, // per second
        features: ['read', 'reply', 'moderate', 'react', 'delete', 'ban', 'timeout']
      });
    }

    // Reddit
    if (config.socialMedia.reddit.clientId) {
      this.platforms.set('reddit', {
        type: 'reddit',
        rateLimits: { comments: 100, votes: 300 }, // per hour
        features: ['read', 'reply', 'moderate', 'upvote', 'downvote', 'report']
      });
    }
  }

  initializeAIModels() {
    // Train spam detection model with common spam patterns
    const spamExamples = [
      { input: 'click here for free money', output: 'spam' },
      { input: 'buy followers cheap', output: 'spam' },
      { input: 'check my profile for nudes', output: 'spam' },
      { input: 'dm me for business', output: 'spam' },
      { input: 'great post love it', output: 'legitimate' },
      { input: 'thanks for sharing this', output: 'legitimate' },
      { input: 'interesting perspective', output: 'legitimate' }
    ];

    spamExamples.forEach(example => {
      this.spamDetector.addDocument(example.input, example.output);
    });

    this.spamDetector.train();

    // Train toxicity detection model
    const toxicityExamples = [
      { input: 'you are stupid', output: 'toxic' },
      { input: 'this is garbage content', output: 'toxic' },
      { input: 'kill yourself', output: 'toxic' },
      { input: 'great work keep it up', output: 'clean' },
      { input: 'i disagree but respect your opinion', output: 'clean' },
      { input: 'nice content', output: 'clean' }
    ];

    toxicityExamples.forEach(example => {
      this.toxicityDetector.addDocument(example.input, example.output);
    });

    this.toxicityDetector.train();
  }

  async loadModerationRules() {
    // Default moderation rules
    this.moderationRules.set('spam_threshold', 0.8);
    this.moderationRules.set('toxicity_threshold', 0.7);
    this.moderationRules.set('auto_hide_toxic', true);
    this.moderationRules.set('auto_block_spam', true);
    this.moderationRules.set('max_comment_length', 1000);
    this.moderationRules.set('min_account_age_days', 7);
    this.moderationRules.set('blocked_keywords', [
      'spam', 'scam', 'porn', 'nude', 'sex', 'bitcoin', 'crypto scam',
      'follow back', 'sub4sub', 'like4like', 'dm me', 'check bio'
    ]);

    // Load custom rules from Redis
    try {
      const customRules = await this.redis.get('moderation_rules');
      if (customRules) {
        const rules = JSON.parse(customRules);
        Object.entries(rules).forEach(([key, value]) => {
          this.moderationRules.set(key, value);
        });
      }
    } catch (error) {
      logger.warn('Failed to load custom moderation rules:', error.message);
    }
  }

  async fetchComments(platform, postId, options = {}) {
    try {
      const platformConfig = this.platforms.get(platform);
      if (!platformConfig) {
        throw new Error(`Platform ${platform} not supported`);
      }

      await this.checkRateLimits(platform, 'comments');

      let comments = [];

      switch (platform) {
        case 'instagram':
          comments = await this.fetchInstagramComments(postId, options);
          break;
        case 'twitter':
          comments = await this.fetchTwitterComments(postId, options);
          break;
        case 'facebook':
          comments = await this.fetchFacebookComments(postId, options);
          break;
        case 'youtube':
          comments = await this.fetchYouTubeComments(postId, options);
          break;
        case 'tiktok':
          comments = await this.fetchTikTokComments(postId, options);
          break;
        case 'linkedin':
          comments = await this.fetchLinkedInComments(postId, options);
          break;
        case 'discord':
          comments = await this.fetchDiscordMessages(postId, options);
          break;
        case 'reddit':
          comments = await this.fetchRedditComments(postId, options);
          break;
        default:
          throw new Error(`Platform ${platform} not implemented`);
      }

      // Process and analyze comments
      const processedComments = [];
      for (const comment of comments) {
        const processed = await this.processComment(comment, platform);
        processedComments.push(processed);
      }

      this.analytics.totalComments += comments.length;
      
      logger.info(`Fetched ${comments.length} comments from ${platform}`);
      return processedComments;

    } catch (error) {
      logger.error(`Failed to fetch comments from ${platform}:`, error);
      throw error;
    }
  }

  async fetchInstagramComments(postId, options) {
    const browser = await puppeteer.launch({ headless: true });
    try {
      const page = await browser.newPage();
      await page.goto(`https://www.instagram.com/p/${postId}/`);
      
      // Wait for comments to load
      await page.waitForSelector('[data-testid="comment"]', { timeout: 10000 });
      
      // Scrape comments
      const comments = await page.evaluate(() => {
        const commentElements = document.querySelectorAll('[data-testid="comment"]');
        return Array.from(commentElements).map(el => ({
          id: el.getAttribute('data-comment-id') || Math.random().toString(),
          text: el.querySelector('[data-testid="comment-text"]')?.textContent || '',
          author: el.querySelector('[data-testid="comment-author"]')?.textContent || '',
          timestamp: el.querySelector('time')?.getAttribute('datetime') || new Date().toISOString(),
          likes: parseInt(el.querySelector('[data-testid="comment-likes"]')?.textContent || '0'),
          replies: []
        }));
      });

      return comments;
    } finally {
      await browser.close();
    }
  }

  async fetchTwitterComments(postId, options) {
    const twitter = this.platforms.get('twitter').api;
    
    const responses = await twitter.v2.replies(postId, {
      max_results: options.limit || 100,
      'tweet.fields': ['created_at', 'author_id', 'public_metrics', 'context_annotations'],
      'user.fields': ['username', 'verified', 'public_metrics'],
      expansions: ['author_id']
    });

    return responses.data?.map(tweet => ({
      id: tweet.id,
      text: tweet.text,
      author: responses.includes?.users?.find(u => u.id === tweet.author_id)?.username || '',
      authorId: tweet.author_id,
      timestamp: tweet.created_at,
      likes: tweet.public_metrics?.like_count || 0,
      retweets: tweet.public_metrics?.retweet_count || 0,
      replies: []
    })) || [];
  }

  async fetchFacebookComments(postId, options) {
    const accessToken = config.socialMedia.facebook.accessToken;
    
    const response = await axios.get(`https://graph.facebook.com/v18.0/${postId}/comments`, {
      params: {
        access_token: accessToken,
        fields: 'id,message,from,created_time,like_count,comment_count',
        limit: options.limit || 100
      }
    });

    return response.data.data.map(comment => ({
      id: comment.id,
      text: comment.message,
      author: comment.from.name,
      authorId: comment.from.id,
      timestamp: comment.created_time,
      likes: comment.like_count,
      replies: []
    }));
  }

  async fetchYouTubeComments(videoId, options) {
    const response = await axios.get('https://www.googleapis.com/youtube/v3/commentThreads', {
      params: {
        part: 'snippet,replies',
        videoId: videoId,
        key: config.socialMedia.youtube.apiKey,
        maxResults: options.limit || 100,
        order: 'time'
      }
    });

    return response.data.items.map(item => {
      const comment = item.snippet.topLevelComment.snippet;
      return {
        id: item.id,
        text: comment.textDisplay,
        author: comment.authorDisplayName,
        authorId: comment.authorChannelId?.value || '',
        timestamp: comment.publishedAt,
        likes: comment.likeCount,
        replies: item.replies?.comments?.map(reply => ({
          id: reply.id,
          text: reply.snippet.textDisplay,
          author: reply.snippet.authorDisplayName,
          timestamp: reply.snippet.publishedAt,
          likes: reply.snippet.likeCount
        })) || []
      };
    });
  }

  async fetchTikTokComments(videoId, options) {
    // TikTok API implementation (requires special access)
    const response = await axios.get(`https://open-api.tiktok.com/video/comment/list/`, {
      params: {
        video_id: videoId,
        count: options.limit || 50
      },
      headers: {
        'Authorization': `Bearer ${config.socialMedia.tiktok.accessToken}`
      }
    });

    return response.data.comments?.map(comment => ({
      id: comment.cid,
      text: comment.text,
      author: comment.user.display_name,
      authorId: comment.user.uid,
      timestamp: new Date(comment.create_time * 1000).toISOString(),
      likes: comment.digg_count,
      replies: []
    })) || [];
  }

  async fetchLinkedInComments(postId, options) {
    const response = await axios.get(`https://api.linkedin.com/v2/socialActions/${postId}/comments`, {
      headers: {
        'Authorization': `Bearer ${config.socialMedia.linkedin.accessToken}`
      },
      params: {
        count: options.limit || 100
      }
    });

    return response.data.elements?.map(comment => ({
      id: comment.id,
      text: comment.message?.text || '',
      author: comment.actor || '',
      timestamp: new Date(comment.created?.time || 0).toISOString(),
      likes: 0,
      replies: []
    })) || [];
  }

  async fetchDiscordMessages(channelId, options) {
    const discord = this.platforms.get('discord').api;
    const channel = discord.channels.cache.get(channelId);
    
    if (!channel) {
      throw new Error('Discord channel not found');
    }

    const messages = await channel.messages.fetch({ limit: options.limit || 100 });
    
    return messages.map(message => ({
      id: message.id,
      text: message.content,
      author: message.author.username,
      authorId: message.author.id,
      timestamp: message.createdAt.toISOString(),
      likes: message.reactions.cache.size,
      replies: []
    }));
  }

  async fetchRedditComments(postId, options) {
    const response = await axios.get(`https://oauth.reddit.com/comments/${postId}`, {
      headers: {
        'Authorization': `Bearer ${config.socialMedia.reddit.accessToken}`,
        'User-Agent': 'RealLogPro/1.0.0'
      },
      params: {
        limit: options.limit || 100,
        sort: 'new'
      }
    });

    const comments = [];
    const commentListing = response.data[1];
    
    function extractComments(children) {
      children.forEach(child => {
        if (child.kind === 't1' && child.data.body) {
          comments.push({
            id: child.data.id,
            text: child.data.body,
            author: child.data.author,
            timestamp: new Date(child.data.created_utc * 1000).toISOString(),
            likes: child.data.ups - child.data.downs,
            replies: []
          });
          
          if (child.data.replies && child.data.replies.data) {
            extractComments(child.data.replies.data.children);
          }
        }
      });
    }

    if (commentListing && commentListing.data) {
      extractComments(commentListing.data.children);
    }

    return comments;
  }

  async processComment(comment, platform) {
    try {
      // Analyze sentiment
      const sentimentResult = this.sentiment.analyze(comment.text);
      comment.sentiment = {
        score: sentimentResult.score,
        comparative: sentimentResult.comparative,
        classification: this.classifySentiment(sentimentResult.score)
      };

      // Update sentiment analytics
      this.analytics.sentimentBreakdown[comment.sentiment.classification]++;

      // Detect spam
      const spamProbability = this.spamDetector.classify(comment.text);
      comment.isSpam = spamProbability === 'spam';
      comment.spamScore = this.spamDetector.getClassifications(comment.text)[0]?.value || 0;

      // Detect toxicity
      const toxicityProbability = this.toxicityDetector.classify(comment.text);
      comment.isToxic = toxicityProbability === 'toxic';
      comment.toxicityScore = this.toxicityDetector.getClassifications(comment.text)[0]?.value || 0;

      // Check against blocked keywords
      comment.hasBlockedKeywords = this.checkBlockedKeywords(comment.text);

      // Overall moderation score
      comment.moderationScore = this.calculateModerationScore(comment);
      comment.requiresModeration = comment.moderationScore > 0.5;

      // Platform-specific processing
      comment.platform = platform;
      comment.processedAt = new Date();

      // Store in Redis for quick access
      await this.redis.setex(
        `comment:${platform}:${comment.id}`,
        3600 * 24, // 24 hours
        JSON.stringify(comment)
      );

      return comment;
    } catch (error) {
      logger.error('Comment processing failed:', error);
      return comment;
    }
  }

  classifySentiment(score) {
    if (score > 0) return 'positive';
    if (score < 0) return 'negative';
    return 'neutral';
  }

  checkBlockedKeywords(text) {
    const blockedKeywords = this.moderationRules.get('blocked_keywords') || [];
    const lowerText = text.toLowerCase();
    
    return blockedKeywords.some(keyword => 
      lowerText.includes(keyword.toLowerCase())
    );
  }

  calculateModerationScore(comment) {
    let score = 0;

    // Spam detection weight
    if (comment.isSpam) score += 0.4;

    // Toxicity detection weight
    if (comment.isToxic) score += 0.4;

    // Blocked keywords weight
    if (comment.hasBlockedKeywords) score += 0.3;

    // Negative sentiment weight
    if (comment.sentiment.score < -5) score += 0.2;

    // Account age (if available)
    // Implementation depends on platform data availability

    return Math.min(score, 1.0);
  }

  async moderateComment(comment, action) {
    try {
      await this.checkRateLimits(comment.platform, 'moderate');

      let result;
      switch (action) {
        case 'hide':
          result = await this.hideComment(comment);
          break;
        case 'delete':
          result = await this.deleteComment(comment);
          break;
        case 'reply':
          result = await this.replyToComment(comment, action.message);
          break;
        case 'like':
          result = await this.likeComment(comment);
          break;
        case 'block_user':
          result = await this.blockUser(comment);
          break;
        case 'report':
          result = await this.reportComment(comment);
          break;
        default:
          throw new Error(`Unknown moderation action: ${action}`);
      }

      this.analytics.moderatedComments++;
      
      logger.info(`Comment moderated: ${action}`, {
        platform: comment.platform,
        commentId: comment.id,
        action
      });

      return result;
    } catch (error) {
      logger.error('Comment moderation failed:', error);
      throw error;
    }
  }

  async hideComment(comment) {
    switch (comment.platform) {
      case 'instagram':
        return await this.hideInstagramComment(comment);
      case 'facebook':
        return await this.hideFacebookComment(comment);
      case 'youtube':
        return await this.hideYouTubeComment(comment);
      default:
        throw new Error(`Hide not supported for ${comment.platform}`);
    }
  }

  async deleteComment(comment) {
    switch (comment.platform) {
      case 'discord':
        return await this.deleteDiscordMessage(comment);
      case 'reddit':
        return await this.deleteRedditComment(comment);
      default:
        throw new Error(`Delete not supported for ${comment.platform}`);
    }
  }

  async replyToComment(comment, message) {
    switch (comment.platform) {
      case 'twitter':
        return await this.replyToTweet(comment, message);
      case 'instagram':
        return await this.replyToInstagramComment(comment, message);
      case 'facebook':
        return await this.replyToFacebookComment(comment, message);
      case 'youtube':
        return await this.replyToYouTubeComment(comment, message);
      case 'discord':
        return await this.replyToDiscordMessage(comment, message);
      default:
        throw new Error(`Reply not supported for ${comment.platform}`);
    }
  }

  async bulkModeration(comments, rules) {
    const results = [];
    
    for (const comment of comments) {
      try {
        // Apply automatic moderation rules
        if (rules.autoHideToxic && comment.isToxic) {
          const result = await this.moderateComment(comment, 'hide');
          results.push({ comment: comment.id, action: 'hide', result });
        }
        
        if (rules.autoBlockSpam && comment.isSpam) {
          const result = await this.moderateComment(comment, 'block_user');
          results.push({ comment: comment.id, action: 'block_user', result });
        }

        if (rules.autoReportToxic && comment.toxicityScore > 0.8) {
          const result = await this.moderateComment(comment, 'report');
          results.push({ comment: comment.id, action: 'report', result });
        }

        // Custom rule processing
        for (const [ruleName, ruleConfig] of Object.entries(rules.customRules || {})) {
          if (this.evaluateCustomRule(comment, ruleConfig)) {
            const result = await this.moderateComment(comment, ruleConfig.action);
            results.push({ comment: comment.id, action: ruleConfig.action, result });
          }
        }
      } catch (error) {
        logger.error(`Bulk moderation failed for comment ${comment.id}:`, error);
        results.push({ comment: comment.id, error: error.message });
      }
    }

    return results;
  }

  evaluateCustomRule(comment, rule) {
    // Implement custom rule evaluation logic
    // This would allow users to create complex moderation rules
    return false;
  }

  startCommentMonitoring() {
    // Monitor comments every 5 minutes
    cron.schedule('*/5 * * * *', async () => {
      try {
        await this.monitorAllPlatforms();
      } catch (error) {
        logger.error('Comment monitoring failed:', error);
      }
    });
  }

  startBulkModeration() {
    // Run bulk moderation every hour
    cron.schedule('0 * * * *', async () => {
      try {
        const pendingComments = await this.getPendingModerationComments();
        if (pendingComments.length > 0) {
          const rules = {
            autoHideToxic: this.moderationRules.get('auto_hide_toxic'),
            autoBlockSpam: this.moderationRules.get('auto_block_spam'),
            autoReportToxic: true
          };
          
          await this.bulkModeration(pendingComments, rules);
          logger.info(`Bulk moderated ${pendingComments.length} comments`);
        }
      } catch (error) {
        logger.error('Bulk moderation failed:', error);
      }
    });
  }

  async monitorAllPlatforms() {
    // Implementation to monitor all connected platforms for new comments
    for (const [platformName] of this.platforms) {
      try {
        // Get recent posts for this platform
        // Fetch new comments
        // Process and queue for moderation if needed
      } catch (error) {
        logger.warn(`Failed to monitor ${platformName}:`, error.message);
      }
    }
  }

  async getPendingModerationComments() {
    // Get comments that require moderation from Redis
    const keys = await this.redis.keys('comment:*');
    const comments = [];

    for (const key of keys) {
      try {
        const commentData = await this.redis.get(key);
        if (commentData) {
          const comment = JSON.parse(commentData);
          if (comment.requiresModeration && !comment.moderated) {
            comments.push(comment);
          }
        }
      } catch (error) {
        logger.warn(`Failed to parse comment from ${key}:`, error.message);
      }
    }

    return comments;
  }

  async checkRateLimits(platform, action) {
    const key = `rate_limit:${platform}:${action}`;
    const current = await this.redis.get(key);
    const limits = this.platforms.get(platform).rateLimits;
    
    if (current && parseInt(current) >= limits[action]) {
      throw new Error(`Rate limit exceeded for ${platform} ${action}`);
    }
    
    await this.redis.incr(key);
    await this.redis.expire(key, 3600); // 1 hour window
  }

  // Platform-specific implementation methods would go here
  async hideInstagramComment(comment) {
    // Implementation for hiding Instagram comments
    return { success: true, hidden: true };
  }

  async replyToTweet(comment, message) {
    const twitter = this.platforms.get('twitter').api;
    return await twitter.v2.reply(message, comment.id);
  }

  // Additional platform-specific methods...

  async getAnalytics() {
    return {
      ...this.analytics,
      platforms: Array.from(this.platforms.keys()),
      moderationRules: Array.from(this.moderationRules.entries()),
      blockedUsers: this.blockedUsers.size
    };
  }

  async updateModerationRules(rules) {
    Object.entries(rules).forEach(([key, value]) => {
      this.moderationRules.set(key, value);
    });

    // Save to Redis
    await this.redis.set('moderation_rules', JSON.stringify(rules));
    logger.info('Moderation rules updated');
  }
}

export default CommentManagementService;