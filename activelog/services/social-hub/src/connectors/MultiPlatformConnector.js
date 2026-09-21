import { EventEmitter } from 'events';
import { TwitterApi } from 'twitter-api-v2';
import { FacebookAdsApi, Page, User } from 'facebook-nodejs-business-sdk';
import { google } from 'googleapis';
import axios from 'axios';
import crypto from 'crypto';

class MultiPlatformConnector extends EventEmitter {
    constructor(config = {}) {
        super();
        this.platforms = new Map();
        this.connections = new Map();
        this.rateLimits = new Map();
        this.uploadQueues = new Map();
        this.webhooks = new Map();
        
        // Initialize platform configurations
        this.config = {
            twitter: {
                consumer_key: config.twitter?.consumer_key || process.env.TWITTER_API_KEY,
                consumer_secret: config.twitter?.consumer_secret || process.env.TWITTER_API_SECRET,
                access_token: config.twitter?.access_token || process.env.TWITTER_ACCESS_TOKEN,
                access_token_secret: config.twitter?.access_token_secret || process.env.TWITTER_ACCESS_SECRET,
                bearer_token: config.twitter?.bearer_token || process.env.TWITTER_BEARER_TOKEN
            },
            facebook: {
                app_id: config.facebook?.app_id || process.env.FACEBOOK_APP_ID,
                app_secret: config.facebook?.app_secret || process.env.FACEBOOK_APP_SECRET,
                access_token: config.facebook?.access_token || process.env.FACEBOOK_ACCESS_TOKEN,
                page_id: config.facebook?.page_id || process.env.FACEBOOK_PAGE_ID
            },
            instagram: {
                client_id: config.instagram?.client_id || process.env.INSTAGRAM_CLIENT_ID,
                client_secret: config.instagram?.client_secret || process.env.INSTAGRAM_CLIENT_SECRET,
                access_token: config.instagram?.access_token || process.env.INSTAGRAM_ACCESS_TOKEN,
                business_account_id: config.instagram?.business_account_id || process.env.INSTAGRAM_BUSINESS_ID
            },
            youtube: {
                client_id: config.youtube?.client_id || process.env.YOUTUBE_CLIENT_ID,
                client_secret: config.youtube?.client_secret || process.env.YOUTUBE_CLIENT_SECRET,
                refresh_token: config.youtube?.refresh_token || process.env.YOUTUBE_REFRESH_TOKEN,
                channel_id: config.youtube?.channel_id || process.env.YOUTUBE_CHANNEL_ID
            },
            tiktok: {
                client_key: config.tiktok?.client_key || process.env.TIKTOK_CLIENT_KEY,
                client_secret: config.tiktok?.client_secret || process.env.TIKTOK_CLIENT_SECRET,
                access_token: config.tiktok?.access_token || process.env.TIKTOK_ACCESS_TOKEN
            }
        };

        this.initializePlatforms();
    }

    async initializePlatforms() {
        try {
            // Initialize Twitter
            if (this.config.twitter.consumer_key) {
                await this.initializeTwitter();
            }

            // Initialize Facebook
            if (this.config.facebook.app_id) {
                await this.initializeFacebook();
            }

            // Initialize Instagram
            if (this.config.instagram.client_id) {
                await this.initializeInstagram();
            }

            // Initialize YouTube
            if (this.config.youtube.client_id) {
                await this.initializeYouTube();
            }

            // Initialize TikTok
            if (this.config.tiktok.client_key) {
                await this.initializeTikTok();
            }

            this.emit('platforms_initialized', Array.from(this.platforms.keys()));
        } catch (error) {
            this.emit('initialization_error', error);
        }
    }

    async initializeTwitter() {
        try {
            const twitterClient = new TwitterApi({
                appKey: this.config.twitter.consumer_key,
                appSecret: this.config.twitter.consumer_secret,
                accessToken: this.config.twitter.access_token,
                accessSecret: this.config.twitter.access_token_secret
            });

            // Test connection
            const user = await twitterClient.v2.me();
            
            this.platforms.set('twitter', {
                client: twitterClient,
                api_version: 'v2',
                user_info: user.data,
                rate_limits: {
                    tweets: { limit: 300, window: 15 * 60 * 1000, used: 0, reset: Date.now() },
                    media_upload: { limit: 300, window: 15 * 60 * 1000, used: 0, reset: Date.now() }
                },
                features: ['text', 'images', 'videos', 'threads', 'spaces'],
                max_text_length: 280,
                max_media_size: 512 * 1024 * 1024, // 512MB
                supported_formats: ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov']
            });

            this.emit('twitter_connected', user.data);
        } catch (error) {
            this.emit('twitter_error', error);
        }
    }

    async initializeFacebook() {
        try {
            FacebookAdsApi.init(this.config.facebook.access_token);
            
            // Test connection and get page info
            const response = await axios.get(`https://graph.facebook.com/v18.0/${this.config.facebook.page_id}`, {
                params: {
                    access_token: this.config.facebook.access_token,
                    fields: 'id,name,username,followers_count,fan_count'
                }
            });

            this.platforms.set('facebook', {
                api: FacebookAdsApi,
                page_id: this.config.facebook.page_id,
                access_token: this.config.facebook.access_token,
                page_info: response.data,
                rate_limits: {
                    posts: { limit: 200, window: 60 * 60 * 1000, used: 0, reset: Date.now() },
                    media_upload: { limit: 100, window: 60 * 60 * 1000, used: 0, reset: Date.now() }
                },
                features: ['text', 'images', 'videos', 'links', 'events', 'stories'],
                max_text_length: 63206,
                max_media_size: 4 * 1024 * 1024 * 1024, // 4GB
                supported_formats: ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi']
            });

            this.emit('facebook_connected', response.data);
        } catch (error) {
            this.emit('facebook_error', error);
        }
    }

    async initializeInstagram() {
        try {
            // Test Instagram Business API connection
            const response = await axios.get(`https://graph.facebook.com/v18.0/${this.config.instagram.business_account_id}`, {
                params: {
                    access_token: this.config.instagram.access_token,
                    fields: 'id,username,followers_count,follows_count,media_count'
                }
            });

            this.platforms.set('instagram', {
                business_account_id: this.config.instagram.business_account_id,
                access_token: this.config.instagram.access_token,
                account_info: response.data,
                rate_limits: {
                    posts: { limit: 25, window: 24 * 60 * 60 * 1000, used: 0, reset: Date.now() },
                    stories: { limit: 100, window: 24 * 60 * 60 * 1000, used: 0, reset: Date.now() }
                },
                features: ['images', 'videos', 'stories', 'reels', 'igtv', 'carousel'],
                max_text_length: 2200,
                max_media_size: 100 * 1024 * 1024, // 100MB
                supported_formats: ['jpg', 'jpeg', 'png', 'mp4', 'mov'],
                aspect_ratios: {
                    square: '1:1',
                    portrait: '4:5',
                    landscape: '1.91:1',
                    stories: '9:16'
                }
            });

            this.emit('instagram_connected', response.data);
        } catch (error) {
            this.emit('instagram_error', error);
        }
    }

    async initializeYouTube() {
        try {
            const oauth2Client = new google.auth.OAuth2(
                this.config.youtube.client_id,
                this.config.youtube.client_secret,
                'http://localhost:8383/auth/youtube/callback'
            );

            oauth2Client.setCredentials({
                refresh_token: this.config.youtube.refresh_token
            });

            const youtube = google.youtube({
                version: 'v3',
                auth: oauth2Client
            });

            // Test connection
            const channel = await youtube.channels.list({
                part: 'snippet,statistics,contentDetails',
                id: this.config.youtube.channel_id
            });

            this.platforms.set('youtube', {
                client: youtube,
                oauth2: oauth2Client,
                channel_id: this.config.youtube.channel_id,
                channel_info: channel.data.items[0],
                rate_limits: {
                    uploads: { limit: 6, window: 24 * 60 * 60 * 1000, used: 0, reset: Date.now() },
                    api_calls: { limit: 10000, window: 24 * 60 * 60 * 1000, used: 0, reset: Date.now() }
                },
                features: ['videos', 'shorts', 'livestreams', 'premieres', 'playlists'],
                max_video_size: 256 * 1024 * 1024 * 1024, // 256GB
                max_video_length: 12 * 60 * 60, // 12 hours
                supported_formats: ['mp4', 'mov', 'avi', 'wmv', 'flv', 'webm']
            });

            this.emit('youtube_connected', channel.data.items[0]);
        } catch (error) {
            this.emit('youtube_error', error);
        }
    }

    async initializeTikTok() {
        try {
            // TikTok Business API integration
            const response = await axios.get('https://business-api.tiktok.com/open_api/v1.3/user/info/', {
                headers: {
                    'Access-Token': this.config.tiktok.access_token
                }
            });

            this.platforms.set('tiktok', {
                access_token: this.config.tiktok.access_token,
                client_key: this.config.tiktok.client_key,
                user_info: response.data.data,
                rate_limits: {
                    posts: { limit: 10, window: 24 * 60 * 60 * 1000, used: 0, reset: Date.now() },
                    api_calls: { limit: 1000, window: 60 * 60 * 1000, used: 0, reset: Date.now() }
                },
                features: ['videos', 'images', 'duets', 'stitches', 'effects'],
                max_video_length: 180, // 3 minutes
                max_video_size: 4 * 1024 * 1024 * 1024, // 4GB
                supported_formats: ['mp4', 'mov', 'avi'],
                aspect_ratios: ['9:16', '1:1', '16:9']
            });

            this.emit('tiktok_connected', response.data.data);
        } catch (error) {
            this.emit('tiktok_error', error);
        }
    }

    // Universal posting method
    async post(platform, content) {
        try {
            if (!this.platforms.has(platform)) {
                throw new Error(`Platform ${platform} not connected`);
            }

            // Check rate limits
            if (!this.checkRateLimit(platform, 'posts')) {
                throw new Error(`Rate limit exceeded for ${platform}`);
            }

            let result;
            
            switch (platform) {
                case 'twitter':
                    result = await this.postToTwitter(content);
                    break;
                case 'facebook':
                    result = await this.postToFacebook(content);
                    break;
                case 'instagram':
                    result = await this.postToInstagram(content);
                    break;
                case 'youtube':
                    result = await this.postToYouTube(content);
                    break;
                case 'tiktok':
                    result = await this.postToTikTok(content);
                    break;
                default:
                    throw new Error(`Unsupported platform: ${platform}`);
            }

            // Update rate limit
            this.updateRateLimit(platform, 'posts');
            
            this.emit('post_success', { platform, content, result });
            return { success: true, platform, result };

        } catch (error) {
            this.emit('post_error', { platform, content, error });
            return { success: false, platform, error: error.message };
        }
    }

    async postToTwitter(content) {
        const twitterData = this.platforms.get('twitter');
        const client = twitterData.client;

        if (content.media && content.media.length > 0) {
            // Upload media first
            const mediaIds = [];
            for (const mediaItem of content.media) {
                const mediaId = await client.v1.uploadMedia(mediaItem.buffer, {
                    type: mediaItem.type,
                    target: 'tweet'
                });
                mediaIds.push(mediaId);
            }

            return await client.v2.tweet({
                text: content.text || '',
                media: { media_ids: mediaIds }
            });
        } else {
            return await client.v2.tweet({ text: content.text });
        }
    }

    async postToFacebook(content) {
        const facebookData = this.platforms.get('facebook');
        
        const postData = {
            message: content.text || '',
            access_token: facebookData.access_token
        };

        if (content.media && content.media.length > 0) {
            // For single image/video
            if (content.media.length === 1) {
                const media = content.media[0];
                if (media.type === 'image') {
                    postData.source = media.buffer;
                } else if (media.type === 'video') {
                    postData.file_url = media.url;
                }
            }
        }

        if (content.link) {
            postData.link = content.link;
        }

        const response = await axios.post(
            `https://graph.facebook.com/v18.0/${facebookData.page_id}/feed`,
            postData
        );

        return response.data;
    }

    async postToInstagram(content) {
        const instagramData = this.platforms.get('instagram');
        
        if (!content.media || content.media.length === 0) {
            throw new Error('Instagram posts require media');
        }

        const media = content.media[0];
        let creationData = {
            access_token: instagramData.access_token
        };

        if (media.type === 'image') {
            creationData.image_url = media.url;
            creationData.media_type = 'IMAGE';
        } else if (media.type === 'video') {
            creationData.video_url = media.url;
            creationData.media_type = 'VIDEO';
        }

        if (content.text) {
            creationData.caption = content.text;
        }

        // Step 1: Create media container
        const containerResponse = await axios.post(
            `https://graph.facebook.com/v18.0/${instagramData.business_account_id}/media`,
            creationData
        );

        const creationId = containerResponse.data.id;

        // Step 2: Publish the media
        const publishResponse = await axios.post(
            `https://graph.facebook.com/v18.0/${instagramData.business_account_id}/media_publish`,
            {
                creation_id: creationId,
                access_token: instagramData.access_token
            }
        );

        return publishResponse.data;
    }

    async postToYouTube(content) {
        const youtubeData = this.platforms.get('youtube');
        
        if (content.type !== 'video') {
            throw new Error('YouTube only supports video uploads');
        }

        const requestBody = {
            snippet: {
                title: content.title || 'ActiveLog Upload',
                description: content.text || '',
                tags: content.tags || [],
                categoryId: content.category || '28', // Science & Technology
                defaultLanguage: 'en'
            },
            status: {
                privacyStatus: content.privacy || 'public',
                selfDeclaredMadeForKids: false
            }
        };

        const response = await youtubeData.client.videos.insert({
            part: 'snippet,status',
            requestBody: requestBody,
            media: {
                body: content.media[0].stream
            }
        });

        return response.data;
    }

    async postToTikTok(content) {
        const tiktokData = this.platforms.get('tiktok');
        
        if (!content.media || content.media.length === 0 || content.media[0].type !== 'video') {
            throw new Error('TikTok posts require video content');
        }

        // TikTok posting flow is more complex and requires video upload first
        const postData = {
            video_url: content.media[0].url,
            text: content.text || '',
            privacy_level: content.privacy || 'PUBLIC_TO_EVERYONE',
            disable_duet: content.disable_duet || false,
            disable_comment: content.disable_comment || false,
            disable_stitch: content.disable_stitch || false,
            brand_content_toggle: content.brand_content || false
        };

        const response = await axios.post(
            'https://open.tiktokapis.com/v2/post/publish/video/init/',
            postData,
            {
                headers: {
                    'Authorization': `Bearer ${tiktokData.access_token}`,
                    'Content-Type': 'application/json'
                }
            }
        );

        return response.data;
    }

    // Rate limiting
    checkRateLimit(platform, operation) {
        const platformData = this.platforms.get(platform);
        if (!platformData) return false;

        const rateLimit = platformData.rate_limits[operation];
        if (!rateLimit) return true;

        const now = Date.now();
        
        // Reset counter if window has passed
        if (now > rateLimit.reset) {
            rateLimit.used = 0;
            rateLimit.reset = now + rateLimit.window;
        }

        return rateLimit.used < rateLimit.limit;
    }

    updateRateLimit(platform, operation) {
        const platformData = this.platforms.get(platform);
        if (!platformData) return;

        const rateLimit = platformData.rate_limits[operation];
        if (rateLimit) {
            rateLimit.used += 1;
        }
    }

    // Media upload utilities
    async uploadMedia(platform, mediaBuffer, mediaType) {
        try {
            switch (platform) {
                case 'twitter':
                    return await this.uploadToTwitterMedia(mediaBuffer, mediaType);
                case 'facebook':
                    return await this.uploadToFacebookMedia(mediaBuffer, mediaType);
                case 'instagram':
                    return await this.uploadToInstagramMedia(mediaBuffer, mediaType);
                case 'youtube':
                    return await this.uploadToYouTubeMedia(mediaBuffer, mediaType);
                case 'tiktok':
                    return await this.uploadToTikTokMedia(mediaBuffer, mediaType);
                default:
                    throw new Error(`Media upload not supported for ${platform}`);
            }
        } catch (error) {
            this.emit('media_upload_error', { platform, error });
            throw error;
        }
    }

    async uploadToTwitterMedia(mediaBuffer, mediaType) {
        const twitterData = this.platforms.get('twitter');
        return await twitterData.client.v1.uploadMedia(mediaBuffer, { type: mediaType });
    }

    async uploadToFacebookMedia(mediaBuffer, mediaType) {
        const facebookData = this.platforms.get('facebook');
        
        const formData = new FormData();
        formData.append('source', mediaBuffer);
        formData.append('access_token', facebookData.access_token);
        
        const response = await axios.post(
            `https://graph.facebook.com/v18.0/${facebookData.page_id}/photos`,
            formData,
            { headers: { 'Content-Type': 'multipart/form-data' } }
        );

        return response.data;
    }

    // Platform-specific methods
    async getTwitterUser(username) {
        const twitterData = this.platforms.get('twitter');
        if (!twitterData) throw new Error('Twitter not connected');

        return await twitterData.client.v2.userByUsername(username);
    }

    async getFacebookPageInsights(pageId, metrics, period = 'day') {
        const facebookData = this.platforms.get('facebook');
        if (!facebookData) throw new Error('Facebook not connected');

        const response = await axios.get(
            `https://graph.facebook.com/v18.0/${pageId}/insights`,
            {
                params: {
                    metric: metrics.join(','),
                    period: period,
                    access_token: facebookData.access_token
                }
            }
        );

        return response.data;
    }

    async getInstagramMediaInsights(mediaId) {
        const instagramData = this.platforms.get('instagram');
        if (!instagramData) throw new Error('Instagram not connected');

        const response = await axios.get(
            `https://graph.facebook.com/v18.0/${mediaId}/insights`,
            {
                params: {
                    metric: 'impressions,reach,engagement',
                    access_token: instagramData.access_token
                }
            }
        );

        return response.data;
    }

    async getYouTubeAnalytics(channelId, metrics, startDate, endDate) {
        const youtubeData = this.platforms.get('youtube');
        if (!youtubeData) throw new Error('YouTube not connected');

        const analytics = google.youtubeAnalytics({
            version: 'v2',
            auth: youtubeData.oauth2
        });

        return await analytics.reports.query({
            ids: `channel==${channelId}`,
            startDate: startDate,
            endDate: endDate,
            metrics: metrics.join(','),
            dimensions: 'day'
        });
    }

    // Webhook management
    async setupWebhook(platform, webhookUrl, events = []) {
        try {
            switch (platform) {
                case 'facebook':
                    return await this.setupFacebookWebhook(webhookUrl, events);
                case 'instagram':
                    return await this.setupInstagramWebhook(webhookUrl, events);
                case 'youtube':
                    return await this.setupYouTubeWebhook(webhookUrl, events);
                default:
                    throw new Error(`Webhooks not supported for ${platform}`);
            }
        } catch (error) {
            this.emit('webhook_setup_error', { platform, error });
            throw error;
        }
    }

    async setupFacebookWebhook(webhookUrl, events) {
        const facebookData = this.platforms.get('facebook');
        
        const response = await axios.post(
            `https://graph.facebook.com/v18.0/${facebookData.app_id}/subscriptions`,
            {
                object: 'page',
                callback_url: webhookUrl,
                verify_token: crypto.randomBytes(32).toString('hex'),
                fields: events.join(','),
                access_token: facebookData.access_token
            }
        );

        return response.data;
    }

    // Connection status
    getPlatformStatus() {
        const status = {};
        
        for (const [platform, data] of this.platforms) {
            status[platform] = {
                connected: true,
                features: data.features,
                rate_limits: data.rate_limits,
                last_used: data.last_used || null,
                user_info: data.user_info || data.account_info || data.channel_info || data.page_info
            };
        }

        return status;
    }

    // Disconnect platform
    async disconnectPlatform(platform) {
        if (this.platforms.has(platform)) {
            this.platforms.delete(platform);
            this.emit('platform_disconnected', platform);
        }
    }

    // Cross-platform content optimization
    optimizeContentForPlatform(content, platform) {
        const platformData = this.platforms.get(platform);
        if (!platformData) return content;

        const optimized = { ...content };

        // Text length optimization
        if (optimized.text && optimized.text.length > platformData.max_text_length) {
            optimized.text = optimized.text.substring(0, platformData.max_text_length - 3) + '...';
        }

        // Platform-specific optimizations
        switch (platform) {
            case 'twitter':
                // Add hashtags strategically
                if (optimized.hashtags) {
                    const hashtagText = ' ' + optimized.hashtags.slice(0, 3).map(h => `#${h}`).join(' ');
                    if (optimized.text.length + hashtagText.length <= 280) {
                        optimized.text += hashtagText;
                    }
                }
                break;
                
            case 'instagram':
                // Instagram loves hashtags
                if (optimized.hashtags) {
                    optimized.text += '\n\n' + optimized.hashtags.slice(0, 30).map(h => `#${h}`).join(' ');
                }
                break;
                
            case 'linkedin':
                // Professional tone for LinkedIn
                if (optimized.text) {
                    optimized.text = this.makeProfessional(optimized.text);
                }
                break;
        }

        return optimized;
    }

    makeProfessional(text) {
        // Simple professional tone adjustment
        return text
            .replace(/awesome/gi, 'excellent')
            .replace(/cool/gi, 'innovative')
            .replace(/check it out/gi, 'please review');
    }
}

export default MultiPlatformConnector;