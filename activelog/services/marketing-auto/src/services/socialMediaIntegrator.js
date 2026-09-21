const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');
const axios = require('axios');

class SocialMediaIntegrator extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.accounts = new Map();
        this.posts = new Map();
        this.campaigns = new Map();
        this.contentLibrary = new Map();
        this.scheduledPosts = new Map();
        this.analytics = new Map();
        
        this.setupEventHandlers();
        this.initializePlatformAPIs();
        this.startSchedulingEngine();
        this.startAnalyticsEngine();
    }

    setupEventHandlers() {
        this.on('account_connected', this.handleAccountConnected.bind(this));
        this.on('post_scheduled', this.handlePostScheduled.bind(this));
        this.on('post_published', this.handlePostPublished.bind(this));
        this.on('engagement_received', this.handleEngagementReceived.bind(this));
        this.on('campaign_completed', this.handleCampaignCompleted.bind(this));
    }

    initializePlatformAPIs() {
        this.platformAPIs = {
            facebook: {
                name: 'Facebook',
                baseUrl: 'https://graph.facebook.com/v18.0',
                scopes: ['pages_manage_posts', 'pages_read_engagement', 'pages_show_list'],
                mediaTypes: ['image', 'video', 'carousel', 'link'],
                characterLimit: 63206,
                hashtagLimit: 30,
                features: ['scheduling', 'analytics', 'stories', 'reels']
            },
            instagram: {
                name: 'Instagram',
                baseUrl: 'https://graph.facebook.com/v18.0',
                scopes: ['instagram_basic', 'instagram_content_publish'],
                mediaTypes: ['image', 'video', 'carousel', 'story', 'reel'],
                characterLimit: 2200,
                hashtagLimit: 30,
                features: ['scheduling', 'analytics', 'stories', 'reels']
            },
            twitter: {
                name: 'Twitter/X',
                baseUrl: 'https://api.twitter.com/2',
                scopes: ['tweet.read', 'tweet.write', 'users.read'],
                mediaTypes: ['text', 'image', 'video', 'poll'],
                characterLimit: 280,
                hashtagLimit: 10,
                features: ['scheduling', 'analytics', 'threads']
            },
            linkedin: {
                name: 'LinkedIn',
                baseUrl: 'https://api.linkedin.com/v2',
                scopes: ['w_member_social', 'r_liteprofile', 'r_emailaddress'],
                mediaTypes: ['text', 'image', 'video', 'document', 'article'],
                characterLimit: 3000,
                hashtagLimit: 3,
                features: ['scheduling', 'analytics', 'targeting']
            },
            youtube: {
                name: 'YouTube',
                baseUrl: 'https://www.googleapis.com/youtube/v3',
                scopes: ['youtube.upload', 'youtube.readonly'],
                mediaTypes: ['video', 'shorts'],
                characterLimit: 5000, // Description
                hashtagLimit: 15,
                features: ['scheduling', 'analytics', 'community_posts']
            },
            tiktok: {
                name: 'TikTok',
                baseUrl: 'https://open-api.tiktok.com/v1.3',
                scopes: ['user.info.basic', 'video.list', 'video.upload'],
                mediaTypes: ['video'],
                characterLimit: 150,
                hashtagLimit: 100,
                features: ['analytics', 'trends']
            },
            pinterest: {
                name: 'Pinterest',
                baseUrl: 'https://api.pinterest.com/v5',
                scopes: ['boards:read', 'pins:read', 'pins:write'],
                mediaTypes: ['image', 'video'],
                characterLimit: 500,
                hashtagLimit: 20,
                features: ['scheduling', 'analytics', 'rich_pins']
            }
        };
    }

    async connectAccount(connectionData) {
        try {
            const accountId = uuidv4();
            const platform = connectionData.platform.toLowerCase();
            
            if (!this.platformAPIs[platform]) {
                throw new Error(`Unsupported platform: ${connectionData.platform}`);
            }
            
            // Verify credentials with platform API
            const verification = await this.verifyCredentials(platform, connectionData.credentials);
            
            if (!verification.valid) {
                throw new Error(`Failed to verify credentials: ${verification.error}`);
            }
            
            const account = {
                id: accountId,
                platform,
                platformAccountId: verification.accountId,
                username: verification.username,
                displayName: verification.displayName,
                profileImage: verification.profileImage,
                credentials: this.encryptCredentials(connectionData.credentials),
                permissions: verification.permissions,
                settings: {
                    autoPosting: connectionData.settings?.autoPosting || false,
                    defaultHashtags: connectionData.settings?.defaultHashtags || [],
                    contentApproval: connectionData.settings?.contentApproval !== false,
                    brandSafety: connectionData.settings?.brandSafety !== false,
                    timezone: connectionData.settings?.timezone || 'UTC',
                    postingHours: connectionData.settings?.postingHours || { start: 9, end: 17 }
                },
                status: 'active', // active, paused, disconnected, error
                connectedAt: new Date(),
                connectedBy: connectionData.connectedBy,
                lastSync: null,
                analytics: {
                    followers: verification.followers || 0,
                    posts: 0,
                    engagement: 0,
                    reach: 0,
                    impressions: 0
                },
                rateLimits: {
                    postsPerDay: this.getPlatformRateLimit(platform, 'posts'),
                    apiCallsPerHour: this.getPlatformRateLimit(platform, 'api'),
                    lastReset: new Date()
                }
            };

            this.accounts.set(accountId, account);
            await this.redis.hset('social_accounts', accountId, JSON.stringify(account));
            
            // Sync initial data
            await this.syncAccountData(accountId);
            
            this.logger.info('Social media account connected', { 
                accountId, 
                platform,
                username: account.username 
            });
            
            this.io.emit('social_account_connected', {
                accountId,
                platform,
                username: account.username,
                followers: account.analytics.followers
            });
            
            this.emit('account_connected', account);
            
            return { success: true, accountId, account: this.sanitizeAccountData(account) };
        } catch (error) {
            this.logger.error('Failed to connect social media account', { 
                error: error.message, 
                platform: connectionData.platform 
            });
            throw new Error(`Social media connection failed: ${error.message}`);
        }
    }

    async schedulePost(postData) {
        try {
            const postId = uuidv4();
            const scheduledDate = new Date(postData.scheduledDate);
            
            if (scheduledDate <= new Date()) {
                throw new Error('Scheduled date must be in the future');
            }
            
            // Validate accounts
            const accounts = [];
            for (const accountId of postData.accounts) {
                const account = this.accounts.get(accountId) || 
                    JSON.parse(await this.redis.hget('social_accounts', accountId));
                if (!account) {
                    throw new Error(`Account ${accountId} not found`);
                }
                accounts.push(account);
            }
            
            // Optimize content for each platform
            const platformContent = await this.optimizeContentForPlatforms(postData.content, accounts);
            
            const post = {
                id: postId,
                type: postData.type || 'post', // post, story, reel, video, carousel
                accounts: postData.accounts,
                content: platformContent,
                originalContent: postData.content,
                media: postData.media || [],
                scheduling: {
                    scheduledDate,
                    timezone: postData.timezone || 'UTC',
                    frequency: postData.frequency || 'once', // once, daily, weekly, monthly
                    endDate: postData.endDate || null,
                    optimalTiming: postData.optimalTiming || false
                },
                targeting: {
                    demographics: postData.targeting?.demographics || {},
                    interests: postData.targeting?.interests || [],
                    locations: postData.targeting?.locations || [],
                    customAudiences: postData.targeting?.customAudiences || []
                },
                campaign: {
                    campaignId: postData.campaignId || null,
                    objective: postData.objective || 'engagement',
                    budget: postData.budget || 0,
                    duration: postData.duration || 0
                },
                settings: {
                    crossPost: postData.settings?.crossPost !== false,
                    trackPerformance: postData.settings?.trackPerformance !== false,
                    moderationEnabled: postData.settings?.moderationEnabled !== false,
                    boostPost: postData.settings?.boostPost || false
                },
                status: 'scheduled',
                createdAt: new Date(),
                createdBy: postData.createdBy,
                approvalStatus: 'pending', // pending, approved, rejected
                publishResults: {},
                analytics: {
                    reach: 0,
                    impressions: 0,
                    engagement: 0,
                    clicks: 0,
                    shares: 0,
                    comments: 0,
                    likes: 0
                }
            };

            // Auto-optimize timing if requested
            if (post.scheduling.optimalTiming) {
                const optimalTime = await this.calculateOptimalPostTime(accounts);
                post.scheduling.scheduledDate = optimalTime;
            }
            
            this.scheduledPosts.set(postId, post);
            await this.redis.hset('scheduled_posts', postId, JSON.stringify(post));
            
            // Add to scheduling queue
            await this.addToSchedulingQueue(post);
            
            this.logger.info('Social media post scheduled', { 
                postId, 
                scheduledDate,
                accounts: post.accounts.length,
                platforms: accounts.map(a => a.platform)
            });
            
            this.io.emit('post_scheduled', {
                postId,
                scheduledDate,
                platforms: accounts.map(a => a.platform),
                accounts: post.accounts.length
            });
            
            this.emit('post_scheduled', post);
            
            return { success: true, postId, post: this.sanitizePostData(post) };
        } catch (error) {
            this.logger.error('Failed to schedule social media post', { 
                error: error.message, 
                postData 
            });
            throw new Error(`Post scheduling failed: ${error.message}`);
        }
    }

    async publishPost(postData) {
        try {
            const publishResults = {};
            
            for (const accountId of postData.accounts) {
                const account = this.accounts.get(accountId);
                if (!account) {
                    publishResults[accountId] = { success: false, error: 'Account not found' };
                    continue;
                }
                
                try {
                    const platformContent = postData.content[account.platform] || postData.content.default;
                    const result = await this.publishToPlatform(account, platformContent, postData.media);
                    
                    publishResults[accountId] = {
                        success: true,
                        platformPostId: result.id,
                        url: result.url,
                        publishedAt: new Date()
                    };
                    
                    // Update account analytics
                    account.analytics.posts++;
                    await this.redis.hset('social_accounts', accountId, JSON.stringify(account));
                    
                } catch (error) {
                    publishResults[accountId] = {
                        success: false,
                        error: error.message
                    };
                    
                    this.logger.error('Failed to publish to platform', {
                        accountId,
                        platform: account.platform,
                        error: error.message
                    });
                }
            }
            
            const successCount = Object.values(publishResults).filter(r => r.success).length;
            const totalCount = postData.accounts.length;
            
            this.logger.info('Post publishing completed', {
                postId: postData.id,
                successful: successCount,
                total: totalCount
            });
            
            this.io.emit('post_published', {
                postId: postData.id,
                results: publishResults,
                successRate: successCount / totalCount
            });
            
            this.emit('post_published', {
                post: postData,
                results: publishResults
            });
            
            return { success: true, results: publishResults };
        } catch (error) {
            this.logger.error('Failed to publish post', { error: error.message });
            throw error;
        }
    }

    async optimizeContentForPlatforms(content, accounts) {
        const optimizedContent = {};
        
        for (const account of accounts) {
            const platform = account.platform;
            const platformAPI = this.platformAPIs[platform];
            
            let optimizedText = content.text || '';
            let hashtags = content.hashtags || [];
            
            // Platform-specific optimizations
            switch (platform) {
                case 'twitter':
                    // Trim to character limit
                    if (optimizedText.length > platformAPI.characterLimit) {
                        optimizedText = optimizedText.substring(0, platformAPI.characterLimit - 3) + '...';
                    }
                    // Limit hashtags
                    hashtags = hashtags.slice(0, platformAPI.hashtagLimit);
                    break;
                    
                case 'instagram':
                    // Instagram works best with hashtags in comments or at the end
                    if (hashtags.length > 0) {
                        optimizedText += '\n\n' + hashtags.map(tag => `#${tag}`).join(' ');
                    }
                    break;
                    
                case 'linkedin':
                    // LinkedIn prefers professional tone and fewer hashtags
                    hashtags = hashtags.slice(0, platformAPI.hashtagLimit);
                    if (hashtags.length > 0) {
                        optimizedText += '\n\n' + hashtags.map(tag => `#${tag}`).join(' ');
                    }
                    break;
                    
                case 'facebook':
                    // Facebook allows longer content
                    if (hashtags.length > 0) {
                        optimizedText += '\n\n' + hashtags.map(tag => `#${tag}`).join(' ');
                    }
                    break;
            }
            
            optimizedContent[platform] = {
                text: optimizedText,
                hashtags,
                mentions: content.mentions || [],
                cta: this.optimizeCTAForPlatform(content.cta, platform),
                tone: this.adjustToneForPlatform(content.tone, platform)
            };
        }
        
        return optimizedContent;
    }

    async publishToPlatform(account, content, media) {
        const platform = account.platform;
        const credentials = this.decryptCredentials(account.credentials);
        
        switch (platform) {
            case 'facebook':
                return await this.publishToFacebook(account, credentials, content, media);
            case 'instagram':
                return await this.publishToInstagram(account, credentials, content, media);
            case 'twitter':
                return await this.publishToTwitter(account, credentials, content, media);
            case 'linkedin':
                return await this.publishToLinkedIn(account, credentials, content, media);
            case 'youtube':
                return await this.publishToYouTube(account, credentials, content, media);
            default:
                throw new Error(`Publishing to ${platform} not implemented`);
        }
    }

    async publishToFacebook(account, credentials, content, media) {
        const pageId = credentials.pageId;
        const accessToken = credentials.accessToken;
        
        let postData = {
            message: content.text,
            access_token: accessToken
        };
        
        // Handle media
        if (media && media.length > 0) {
            if (media.length === 1) {
                // Single media post
                const mediaItem = media[0];
                if (mediaItem.type === 'image') {
                    postData.url = mediaItem.url;
                } else if (mediaItem.type === 'video') {
                    postData.source = mediaItem.url;
                }
            } else {
                // Multiple media - create carousel/album
                postData.attached_media = media.map((item, index) => ({
                    media_fbid: `media_${index}`
                }));
            }
        }
        
        const response = await axios.post(
            `${this.platformAPIs.facebook.baseUrl}/${pageId}/feed`,
            postData
        );
        
        return {
            id: response.data.id,
            url: `https://facebook.com/${response.data.id}`,
            platformResponse: response.data
        };
    }

    async publishToInstagram(account, credentials, content, media) {
        const instagramAccountId = credentials.instagramAccountId;
        const accessToken = credentials.accessToken;
        
        if (!media || media.length === 0) {
            throw new Error('Instagram posts require media');
        }
        
        // Create media container
        const mediaContainer = await axios.post(
            `${this.platformAPIs.instagram.baseUrl}/${instagramAccountId}/media`,
            {
                image_url: media[0].url,
                caption: content.text,
                access_token: accessToken
            }
        );
        
        // Publish media
        const publishResponse = await axios.post(
            `${this.platformAPIs.instagram.baseUrl}/${instagramAccountId}/media_publish`,
            {
                creation_id: mediaContainer.data.id,
                access_token: accessToken
            }
        );
        
        return {
            id: publishResponse.data.id,
            url: `https://instagram.com/p/${publishResponse.data.id}`,
            platformResponse: publishResponse.data
        };
    }

    async publishToTwitter(account, credentials, content, media) {
        const apiKey = credentials.apiKey;
        const apiSecret = credentials.apiSecret;
        const accessToken = credentials.accessToken;
        const accessTokenSecret = credentials.accessTokenSecret;
        
        // Twitter API v2 implementation would go here
        // For now, returning mock response
        return {
            id: `tweet_${Date.now()}`,
            url: `https://twitter.com/${account.username}/status/123456789`,
            platformResponse: { id: '123456789' }
        };
    }

    async publishToLinkedIn(account, credentials, content, media) {
        const accessToken = credentials.accessToken;
        const authorId = credentials.authorId;
        
        const postData = {
            author: `urn:li:person:${authorId}`,
            lifecycleState: 'PUBLISHED',
            specificContent: {
                'com.linkedin.ugc.ShareContent': {
                    shareCommentary: {
                        text: content.text
                    },
                    shareMediaCategory: media && media.length > 0 ? 'IMAGE' : 'NONE'
                }
            },
            visibility: {
                'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
            }
        };
        
        if (media && media.length > 0) {
            postData.specificContent['com.linkedin.ugc.ShareContent'].media = media.map(item => ({
                status: 'READY',
                description: {
                    text: item.description || ''
                },
                media: item.url
            }));
        }
        
        const response = await axios.post(
            `${this.platformAPIs.linkedin.baseUrl}/ugcPosts`,
            postData,
            {
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                }
            }
        );
        
        return {
            id: response.data.id,
            url: `https://linkedin.com/feed/update/${response.data.id}`,
            platformResponse: response.data
        };
    }

    async getAnalytics(accountId, timeframe = '30d') {
        try {
            const account = this.accounts.get(accountId) || 
                JSON.parse(await this.redis.hget('social_accounts', accountId));
            
            if (!account) {
                throw new Error(`Account ${accountId} not found`);
            }
            
            // Get analytics from platform API
            const platformAnalytics = await this.fetchPlatformAnalytics(account, timeframe);
            
            // Get post performance data
            const posts = await this.getAccountPosts(accountId, timeframe);
            const postAnalytics = this.calculatePostAnalytics(posts);
            
            // Calculate engagement rates and trends
            const engagementMetrics = this.calculateEngagementMetrics(platformAnalytics, postAnalytics);
            
            const analytics = {
                account: {
                    id: account.id,
                    platform: account.platform,
                    username: account.username,
                    followers: platformAnalytics.followers
                },
                timeframe,
                overview: {
                    followers: platformAnalytics.followers,
                    followersGrowth: platformAnalytics.followersGrowth,
                    posts: postAnalytics.totalPosts,
                    reach: platformAnalytics.reach,
                    impressions: platformAnalytics.impressions,
                    engagement: platformAnalytics.engagement,
                    engagementRate: engagementMetrics.overallEngagementRate
                },
                engagement: {
                    likes: postAnalytics.totalLikes,
                    comments: postAnalytics.totalComments,
                    shares: postAnalytics.totalShares,
                    saves: postAnalytics.totalSaves,
                    clicks: postAnalytics.totalClicks
                },
                topPosts: postAnalytics.topPosts,
                demographics: platformAnalytics.demographics,
                bestTimes: platformAnalytics.bestTimes,
                hashtagPerformance: postAnalytics.hashtagPerformance,
                contentTypes: postAnalytics.contentTypePerformance,
                trends: this.calculateTrends(platformAnalytics, timeframe)
            };
            
            // Cache analytics
            await this.redis.setex(
                `analytics:${accountId}:${timeframe}`,
                3600, // 1 hour cache
                JSON.stringify(analytics)
            );
            
            return analytics;
        } catch (error) {
            this.logger.error('Failed to get analytics', { error: error.message, accountId });
            throw error;
        }
    }

    async createSocialCampaign(campaignData) {
        try {
            const campaignId = uuidv4();
            const campaign = {
                id: campaignId,
                name: campaignData.name,
                description: campaignData.description || '',
                objective: campaignData.objective || 'engagement',
                platforms: campaignData.platforms || [],
                accounts: campaignData.accounts || [],
                budget: {
                    total: campaignData.budget?.total || 0,
                    daily: campaignData.budget?.daily || 0,
                    currency: campaignData.budget?.currency || 'USD',
                    spent: 0
                },
                targeting: {
                    demographics: campaignData.targeting?.demographics || {},
                    interests: campaignData.targeting?.interests || [],
                    behaviors: campaignData.targeting?.behaviors || [],
                    locations: campaignData.targeting?.locations || [],
                    customAudiences: campaignData.targeting?.customAudiences || []
                },
                content: {
                    posts: campaignData.content?.posts || [],
                    creatives: campaignData.content?.creatives || [],
                    hashtags: campaignData.content?.hashtags || [],
                    mentions: campaignData.content?.mentions || []
                },
                schedule: {
                    startDate: new Date(campaignData.schedule?.startDate || Date.now()),
                    endDate: campaignData.schedule?.endDate ? new Date(campaignData.schedule.endDate) : null,
                    frequency: campaignData.schedule?.frequency || 'daily',
                    optimalTiming: campaignData.schedule?.optimalTiming || true
                },
                status: 'draft',
                createdAt: new Date(),
                createdBy: campaignData.createdBy,
                analytics: {
                    reach: 0,
                    impressions: 0,
                    engagement: 0,
                    clicks: 0,
                    conversions: 0,
                    cost: 0,
                    cpm: 0,
                    cpc: 0,
                    ctr: 0
                }
            };

            this.campaigns.set(campaignId, campaign);
            await this.redis.hset('social_campaigns', campaignId, JSON.stringify(campaign));
            
            this.logger.info('Social media campaign created', { 
                campaignId, 
                name: campaign.name,
                platforms: campaign.platforms,
                objective: campaign.objective
            });
            
            return { success: true, campaignId, campaign };
        } catch (error) {
            this.logger.error('Failed to create social campaign', { error: error.message, campaignData });
            throw error;
        }
    }

    async calculateOptimalPostTime(accounts) {
        // Analyze historical performance to determine optimal posting time
        const performanceData = [];
        
        for (const account of accounts) {
            const analytics = await this.fetchPlatformAnalytics(account, '30d');
            if (analytics.bestTimes) {
                performanceData.push(analytics.bestTimes);
            }
        }
        
        if (performanceData.length === 0) {
            // Default optimal times by platform
            const defaultTimes = {
                facebook: { hour: 15, day: 'tuesday' }, // 3 PM Tuesday
                instagram: { hour: 11, day: 'wednesday' }, // 11 AM Wednesday
                twitter: { hour: 12, day: 'wednesday' }, // 12 PM Wednesday
                linkedin: { hour: 10, day: 'tuesday' }, // 10 AM Tuesday
                youtube: { hour: 14, day: 'saturday' } // 2 PM Saturday
            };
            
            // Use most common platform's default
            const primaryPlatform = accounts[0].platform;
            const optimalTime = defaultTimes[primaryPlatform] || defaultTimes.facebook;
            
            return moment().day(optimalTime.day).hour(optimalTime.hour).minute(0).second(0).toDate();
        }
        
        // Calculate weighted average of optimal times
        const avgHour = Math.round(
            performanceData.reduce((sum, data) => sum + data.hour, 0) / performanceData.length
        );
        
        return moment().add(1, 'day').hour(avgHour).minute(0).second(0).toDate();
    }

    async verifyCredentials(platform, credentials) {
        try {
            switch (platform) {
                case 'facebook':
                    return await this.verifyFacebookCredentials(credentials);
                case 'instagram':
                    return await this.verifyInstagramCredentials(credentials);
                case 'twitter':
                    return await this.verifyTwitterCredentials(credentials);
                case 'linkedin':
                    return await this.verifyLinkedInCredentials(credentials);
                default:
                    throw new Error(`Verification for ${platform} not implemented`);
            }
        } catch (error) {
            return { valid: false, error: error.message };
        }
    }

    async verifyFacebookCredentials(credentials) {
        const response = await axios.get(
            `${this.platformAPIs.facebook.baseUrl}/me/accounts`,
            {
                params: {
                    access_token: credentials.accessToken,
                    fields: 'id,name,username,picture,followers_count'
                }
            }
        );
        
        return {
            valid: true,
            accountId: response.data.data[0]?.id,
            username: response.data.data[0]?.username,
            displayName: response.data.data[0]?.name,
            profileImage: response.data.data[0]?.picture?.data?.url,
            followers: response.data.data[0]?.followers_count,
            permissions: ['manage_pages', 'publish_pages']
        };
    }

    async verifyLinkedInCredentials(credentials) {
        const response = await axios.get(
            `${this.platformAPIs.linkedin.baseUrl}/people/~`,
            {
                headers: {
                    'Authorization': `Bearer ${credentials.accessToken}`
                }
            }
        );
        
        return {
            valid: true,
            accountId: response.data.id,
            username: response.data.vanityName,
            displayName: `${response.data.firstName} ${response.data.lastName}`,
            profileImage: response.data.pictureUrl,
            followers: 0, // LinkedIn doesn't provide this in basic profile
            permissions: ['w_member_social']
        };
    }

    // Helper methods
    encryptCredentials(credentials) {
        // In production, use proper encryption
        return Buffer.from(JSON.stringify(credentials)).toString('base64');
    }

    decryptCredentials(encryptedCredentials) {
        // In production, use proper decryption
        return JSON.parse(Buffer.from(encryptedCredentials, 'base64').toString());
    }

    getPlatformRateLimit(platform, type) {
        const limits = {
            facebook: { posts: 25, api: 200 },
            instagram: { posts: 25, api: 200 },
            twitter: { posts: 100, api: 300 },
            linkedin: { posts: 20, api: 100 },
            youtube: { posts: 6, api: 10000 }
        };
        
        return limits[platform]?.[type] || 10;
    }

    optimizeCTAForPlatform(cta, platform) {
        if (!cta) return null;
        
        const platformCTAs = {
            facebook: 'Learn More',
            instagram: 'Link in Bio',
            twitter: 'See Thread',
            linkedin: 'Read Full Article',
            youtube: 'Watch Now'
        };
        
        return cta.text || platformCTAs[platform] || 'Click Here';
    }

    adjustToneForPlatform(tone, platform) {
        const platformTones = {
            facebook: 'conversational',
            instagram: 'visual',
            twitter: 'concise',
            linkedin: 'professional',
            youtube: 'entertaining'
        };
        
        return tone || platformTones[platform] || 'neutral';
    }

    startSchedulingEngine() {
        // Check for posts to publish every minute
        setInterval(async () => {
            try {
                await this.processScheduledPosts();
            } catch (error) {
                this.logger.error('Scheduling engine error', { error: error.message });
            }
        }, 60 * 1000);
    }

    startAnalyticsEngine() {
        // Update analytics every hour
        setInterval(async () => {
            try {
                await this.updateAnalytics();
            } catch (error) {
                this.logger.error('Analytics engine error', { error: error.message });
            }
        }, 60 * 60 * 1000);
    }

    async getOverallStats() {
        const totalAccounts = this.accounts.size;
        const activeAccounts = Array.from(this.accounts.values()).filter(a => a.status === 'active').length;
        const totalCampaigns = this.campaigns.size;
        const scheduledPosts = this.scheduledPosts.size;
        
        let totalFollowers = 0;
        let totalPosts = 0;
        let totalEngagement = 0;
        
        for (const account of this.accounts.values()) {
            totalFollowers += account.analytics.followers;
            totalPosts += account.analytics.posts;
            totalEngagement += account.analytics.engagement;
        }
        
        return {
            totalAccounts,
            activeAccounts,
            totalCampaigns,
            scheduledPosts,
            totalFollowers,
            totalPosts,
            totalEngagement,
            averageEngagement: totalPosts > 0 ? totalEngagement / totalPosts : 0
        };
    }

    // Event handlers
    handleAccountConnected(account) {
        this.logger.info('Social media account connected successfully', {
            accountId: account.id,
            platform: account.platform,
            username: account.username
        });
    }

    handlePostScheduled(post) {
        this.logger.info('Social media post scheduled', {
            postId: post.id,
            scheduledDate: post.scheduling.scheduledDate,
            platforms: post.accounts.length
        });
    }

    handlePostPublished(data) {
        this.logger.info('Social media post published', {
            postId: data.post.id,
            successfulPlatforms: Object.values(data.results).filter(r => r.success).length
        });
    }

    handleEngagementReceived(engagement) {
        this.logger.info('Social media engagement received', {
            type: engagement.type,
            platform: engagement.platform,
            postId: engagement.postId
        });
    }

    handleCampaignCompleted(campaign) {
        this.logger.info('Social media campaign completed', {
            campaignId: campaign.id,
            name: campaign.name,
            performance: campaign.analytics
        });
    }

    // Data sanitization
    sanitizeAccountData(account) {
        const { credentials, ...sanitized } = account;
        return sanitized;
    }

    sanitizePostData(post) {
        return post;
    }
}

module.exports = SocialMediaIntegrator;