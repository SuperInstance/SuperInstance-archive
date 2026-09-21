import { EventEmitter } from 'events';
import axios from 'axios';
import FormData from 'form-data';
import sharp from 'sharp';
import ffmpeg from 'fluent-ffmpeg';
import crypto from 'crypto';
import fs from 'fs/promises';
import path from 'path';

class CrossPlatformPosting extends EventEmitter {
    constructor(config = {}) {
        super();
        this.postQueue = new Map();
        this.postHistory = new Map();
        this.activelogIntegration = new Map();
        this.mediaProcessor = new Map();
        this.platformAdapters = new Map();
        this.crossPostRules = new Map();
        this.contentOptimizer = new Map();
        this.postTemplates = new Map();

        // ActiveLog service connections
        this.activelogEndpoints = {
            content_feed: config.activelog_endpoints?.content_feed || 'http://localhost:8080/api/content/feed',
            project_updates: config.activelog_endpoints?.project_updates || 'http://localhost:8080/api/projects/updates',
            user_activity: config.activelog_endpoints?.user_activity || 'http://localhost:8080/api/users/activity',
            analytics: config.activelog_endpoints?.analytics || 'http://localhost:8080/api/analytics'
        };

        this.initializeSystem();
    }

    initializeSystem() {
        this.initializePlatformAdapters();
        this.initializeCrossPostRules();
        this.initializePostTemplates();
        this.initializeActiveLogIntegration();
        
        // Start monitoring ActiveLog feeds
        this.startActiveLogMonitoring();
        
        this.emit('cross_posting_system_initialized');
    }

    initializePlatformAdapters() {
        const adapters = [
            {
                platform: 'twitter',
                character_limit: 280,
                media_limit: 4,
                video_length_limit: 140, // seconds
                supported_media: ['jpg', 'jpeg', 'png', 'gif', 'mp4'],
                hashtag_strategy: 'integrated',
                optimal_posting_times: ['09:00', '12:00', '15:00', '18:00'],
                engagement_window: 2 // hours
            },
            {
                platform: 'linkedin',
                character_limit: 3000,
                media_limit: 9,
                video_length_limit: 600, // seconds
                supported_media: ['jpg', 'jpeg', 'png', 'mp4', 'pdf'],
                hashtag_strategy: 'end_of_post',
                optimal_posting_times: ['08:00', '12:00', '17:00'],
                engagement_window: 24 // hours
            },
            {
                platform: 'facebook',
                character_limit: 63206,
                media_limit: 10,
                video_length_limit: 7200, // seconds
                supported_media: ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov'],
                hashtag_strategy: 'minimal',
                optimal_posting_times: ['09:00', '13:00', '15:00', '19:00'],
                engagement_window: 6 // hours
            },
            {
                platform: 'instagram',
                character_limit: 2200,
                media_limit: 10,
                video_length_limit: 60, // seconds for reels
                supported_media: ['jpg', 'jpeg', 'png', 'mp4'],
                hashtag_strategy: 'abundant',
                optimal_posting_times: ['11:00', '14:00', '17:00', '20:00'],
                engagement_window: 4 // hours
            },
            {
                platform: 'youtube',
                character_limit: 5000, // description
                media_limit: 1,
                video_length_limit: 43200, // seconds (12 hours)
                supported_media: ['mp4', 'mov', 'avi', 'wmv', 'flv', 'webm'],
                hashtag_strategy: 'description_tags',
                optimal_posting_times: ['14:00', '16:00', '20:00'],
                engagement_window: 48 // hours
            },
            {
                platform: 'tiktok',
                character_limit: 150,
                media_limit: 1,
                video_length_limit: 180, // seconds
                supported_media: ['mp4', 'mov'],
                hashtag_strategy: 'trending_focused',
                optimal_posting_times: ['06:00', '10:00', '19:00', '22:00'],
                engagement_window: 3 // hours
            }
        ];

        adapters.forEach(adapter => {
            this.platformAdapters.set(adapter.platform, adapter);
        });
    }

    initializeCrossPostRules() {
        const rules = [
            {
                id: 'new_project_announcement',
                trigger: 'project_created',
                platforms: ['twitter', 'linkedin', 'facebook'],
                content_strategy: 'announcement',
                delay_between_posts: 30, // minutes
                customization_level: 'high'
            },
            {
                id: 'project_milestone',
                trigger: 'project_milestone',
                platforms: ['twitter', 'linkedin'],
                content_strategy: 'celebration',
                delay_between_posts: 15,
                customization_level: 'medium'
            },
            {
                id: 'daily_highlights',
                trigger: 'daily_summary',
                platforms: ['twitter', 'instagram', 'facebook'],
                content_strategy: 'digest',
                delay_between_posts: 60,
                customization_level: 'high'
            },
            {
                id: 'product_showcase',
                trigger: 'product_featured',
                platforms: ['all'],
                content_strategy: 'showcase',
                delay_between_posts: 45,
                customization_level: 'very_high'
            },
            {
                id: 'user_achievement',
                trigger: 'user_milestone',
                platforms: ['twitter', 'linkedin'],
                content_strategy: 'recognition',
                delay_between_posts: 20,
                customization_level: 'medium'
            },
            {
                id: 'technical_update',
                trigger: 'system_update',
                platforms: ['twitter', 'linkedin'],
                content_strategy: 'informative',
                delay_between_posts: 10,
                customization_level: 'low'
            }
        ];

        rules.forEach(rule => {
            this.crossPostRules.set(rule.id, rule);
        });
    }

    initializePostTemplates() {
        const templates = [
            {
                id: 'project_announcement',
                category: 'announcement',
                variations: {
                    twitter: '🚀 New project alert! "{project_name}" by {creator} is now live on ActiveLog!\n\n{brief_description}\n\n🔗 Check it out: {link}\n\n#{category} #ActiveLog #Innovation',
                    linkedin: '🚀 Exciting Project Launch!\n\nWe\'re thrilled to share "{project_name}" by {creator} - now available on ActiveLog!\n\n📋 Project Details:\n{detailed_description}\n\n🎯 Key Features:\n{key_features}\n\n💡 This project demonstrates the incredible innovation happening in our community.\n\n🔗 Explore the project: {link}\n\n#{category} #ActiveLog #Innovation #TechCommunity',
                    facebook: '🚀 Amazing New Project Alert! 🚀\n\nCheck out "{project_name}" by our talented community member {creator}!\n\n{detailed_description}\n\n✨ What makes this special:\n{highlights}\n\n👥 Join thousands of makers, developers, and innovators on ActiveLog!\n\n🔗 See the full project: {link}\n\nWhat do you think? Drop a comment below! 👇',
                    instagram: 'New project spotlight! ✨\n\n"{project_name}" by {creator}\n\n{brief_description}\n\nSwipe to see the amazing details! 👉\n\nLink in bio to explore more 🔗\n\n#{category} #ActiveLog #Innovation #TechProject #MakerCommunity',
                    youtube: '{project_name} - Project Showcase\n\n{detailed_description}\n\n🔗 Project Link: {link}\n📱 ActiveLog: https://activelog.com\n\nTimestamps:\n0:00 Introduction\n1:30 Project Overview\n3:00 Key Features\n5:00 Community Impact\n\n#{category} #ActiveLog #ProjectShowcase'
                },
                variables: ['project_name', 'creator', 'brief_description', 'detailed_description', 'key_features', 'highlights', 'link', 'category']
            },
            {
                id: 'milestone_celebration',
                category: 'celebration',
                variations: {
                    twitter: '🎉 Milestone achieved! {milestone_description}\n\n{stats}\n\nThank you to our amazing community! 🙏\n\n#ActiveLog #Milestone #Community',
                    linkedin: '🎉 Celebrating a Major Milestone!\n\n{milestone_description}\n\n📊 By the numbers:\n{detailed_stats}\n\n🙏 This achievement wouldn\'t be possible without our incredible community of makers, innovators, and supporters.\n\n💪 Here\'s to the next milestone!\n\n#ActiveLog #Milestone #Innovation #Community',
                    facebook: '🎉 MILESTONE CELEBRATION! 🎉\n\n{milestone_description}\n\n{detailed_stats}\n\n🙏 HUGE thanks to everyone who\'s been part of this journey!\n\n✨ Every project shared, every collaboration, every innovation contributes to this success.\n\n💪 Ready for what\'s next? Join us at ActiveLog!\n\n#ActiveLog #Community #Innovation',
                    instagram: 'Milestone unlocked! 🎉✨\n\n{milestone_description}\n\n{stats}\n\nCelebrating with our amazing community! 🙌\n\nThank you for being part of the journey! ❤️\n\n#ActiveLog #Milestone #Community #Grateful #Innovation'
                },
                variables: ['milestone_description', 'stats', 'detailed_stats']
            },
            {
                id: 'daily_highlights',
                category: 'digest',
                variations: {
                    twitter: '📅 Today on ActiveLog:\n\n{highlights}\n\n🔗 Discover more: {link}\n\n#ActiveLog #DailyHighlights #Innovation',
                    instagram: 'Daily dose of innovation! ⚡\n\n{highlights}\n\nWhat caught your attention today? 💭\n\nStories highlight for more! 👆\n\n#ActiveLog #Daily #Innovation #Tech #Community',
                    facebook: '📅 Your Daily ActiveLog Highlights!\n\n{detailed_highlights}\n\n💡 Missed something? Catch up on all the latest projects, updates, and community achievements!\n\n🔗 Visit ActiveLog: {link}\n\n#ActiveLog #Community #Innovation'
                },
                variables: ['highlights', 'detailed_highlights', 'link']
            },
            {
                id: 'product_showcase',
                category: 'showcase',
                variations: {
                    twitter: '🌟 Product Spotlight: {product_name}\n\n{key_benefit}\n\n💡 Perfect for: {use_cases}\n\n🔗 Learn more: {link}\n\n#{product_category} #ActiveLog #Innovation',
                    linkedin: '🌟 Product Spotlight: {product_name}\n\n{detailed_description}\n\n🎯 Key Benefits:\n{benefits_list}\n\n💼 Use Cases:\n{use_cases_detailed}\n\n📈 Why it matters:\n{market_impact}\n\n🔗 Explore: {link}\n\n#{product_category} #ProductSpotlight #Innovation #Technology',
                    facebook: '🌟 Featured Product: {product_name}! 🌟\n\n{detailed_description}\n\n✨ What makes it special:\n{benefits_list}\n\n🎯 Perfect for:\n{use_cases_detailed}\n\n🗣️ Customer feedback:\n{testimonial}\n\n🔗 Check it out: {link}\n\nWhat questions do you have? Ask below! 👇',
                    instagram: 'Product spotlight! ✨\n\n{product_name}\n\n{brief_description}\n\nSwipe for details! 👉\n\n{key_benefit}\n\nLink in bio! 🔗\n\n#{product_category} #ProductSpotlight #Innovation #ActiveLog #Tech',
                    youtube: '{product_name} - Complete Product Overview\n\n{detailed_description}\n\n🔗 Product Page: {link}\n📱 ActiveLog: https://activelog.com\n\nIn this video:\n0:00 Product Introduction\n2:00 Key Features\n4:30 Use Cases & Applications\n7:00 Customer Reviews\n9:00 Getting Started\n\n#{product_category} #ProductReview #Innovation #ActiveLog',
                    tiktok: '{product_name} in action! ⚡\n\n{brief_description}\n\n{key_benefit}\n\n#ActiveLog #{product_category} #Innovation #Tech #Product'
                },
                variables: ['product_name', 'key_benefit', 'use_cases', 'detailed_description', 'benefits_list', 'use_cases_detailed', 'market_impact', 'testimonial', 'brief_description', 'product_category', 'link']
            }
        ];

        templates.forEach(template => {
            this.postTemplates.set(template.id, template);
        });
    }

    initializeActiveLogIntegration() {
        // Set up webhooks and polling for ActiveLog events
        this.activelogIntegration.set('polling_interval', 60000); // 1 minute
        this.activelogIntegration.set('webhook_secret', crypto.randomBytes(32).toString('hex'));
        this.activelogIntegration.set('last_sync', new Date());
    }

    async startActiveLogMonitoring() {
        // Start polling ActiveLog for new content
        setInterval(async () => {
            await this.pollActiveLogFeed();
        }, this.activelogIntegration.get('polling_interval'));

        this.emit('activelog_monitoring_started');
    }

    async pollActiveLogFeed() {
        try {
            const lastSync = this.activelogIntegration.get('last_sync');
            
            // Poll different ActiveLog endpoints
            const [contentFeed, projectUpdates, userActivity] = await Promise.all([
                this.fetchActiveLogContent('content_feed', lastSync),
                this.fetchActiveLogContent('project_updates', lastSync),
                this.fetchActiveLogContent('user_activity', lastSync)
            ]);

            // Process each type of content
            if (contentFeed.length > 0) {
                await this.processContentFeedUpdates(contentFeed);
            }

            if (projectUpdates.length > 0) {
                await this.processProjectUpdates(projectUpdates);
            }

            if (userActivity.length > 0) {
                await this.processUserActivity(userActivity);
            }

            // Update last sync time
            this.activelogIntegration.set('last_sync', new Date());

        } catch (error) {
            this.emit('activelog_polling_error', error);
        }
    }

    async fetchActiveLogContent(endpoint, since) {
        try {
            const url = this.activelogEndpoints[endpoint];
            const response = await axios.get(url, {
                params: {
                    since: since.toISOString(),
                    limit: 50
                },
                timeout: 10000
            });

            return response.data.items || [];

        } catch (error) {
            if (error.code === 'ECONNREFUSED') {
                // ActiveLog service not available, return empty array
                return [];
            }
            throw error;
        }
    }

    async processContentFeedUpdates(updates) {
        for (const update of updates) {
            try {
                // Determine if this update should trigger cross-posting
                const crossPostRule = this.shouldCrossPost(update);
                
                if (crossPostRule) {
                    await this.schedulecrossPost(update, crossPostRule);
                }

            } catch (error) {
                this.emit('content_processing_error', { update, error });
            }
        }
    }

    async processProjectUpdates(updates) {
        for (const update of updates) {
            try {
                const eventType = update.event_type;
                const projectData = update.project_data;

                switch (eventType) {
                    case 'project_created':
                        await this.handleProjectCreated(projectData);
                        break;
                    case 'project_milestone':
                        await this.handleProjectMilestone(projectData, update.milestone_data);
                        break;
                    case 'project_featured':
                        await this.handleProjectFeatured(projectData);
                        break;
                    case 'project_completed':
                        await this.handleProjectCompleted(projectData);
                        break;
                }

            } catch (error) {
                this.emit('project_processing_error', { update, error });
            }
        }
    }

    async processUserActivity(activities) {
        for (const activity of activities) {
            try {
                if (activity.type === 'user_milestone' && activity.data.milestone_type === 'major') {
                    await this.handleUserMilestone(activity);
                }

            } catch (error) {
                this.emit('user_activity_processing_error', { activity, error });
            }
        }
    }

    shouldCrossPost(update) {
        // Determine if an update should trigger cross-posting
        const rules = Array.from(this.crossPostRules.values());
        
        for (const rule of rules) {
            if (this.evaluateRule(rule, update)) {
                return rule;
            }
        }
        
        return null;
    }

    evaluateRule(rule, update) {
        // Simple rule evaluation - in production this would be more sophisticated
        switch (rule.trigger) {
            case 'project_created':
                return update.event_type === 'project_created';
            case 'project_milestone':
                return update.event_type === 'project_milestone';
            case 'daily_summary':
                return update.event_type === 'daily_digest';
            case 'product_featured':
                return update.event_type === 'product_featured';
            case 'user_milestone':
                return update.event_type === 'user_milestone';
            case 'system_update':
                return update.event_type === 'system_update';
            default:
                return false;
        }
    }

    async scheduleACCrossPost(activelogData, rule) {
        try {
            const postId = crypto.randomBytes(16).toString('hex');
            const platforms = rule.platforms.includes('all') ? 
                Array.from(this.platformAdapters.keys()) : 
                rule.platforms;

            // Generate content for each platform
            const platformPosts = await this.generatePlatformContent(activelogData, rule, platforms);

            // Schedule posts with delays
            let delay = 0;
            for (const platform of platforms) {
                const scheduledTime = new Date(Date.now() + delay * 60 * 1000);
                
                const postData = {
                    id: `${postId}_${platform}`,
                    platform: platform,
                    content: platformPosts[platform],
                    scheduled_time: scheduledTime,
                    status: 'scheduled',
                    rule_id: rule.id,
                    source_data: activelogData,
                    created_at: new Date()
                };

                this.postQueue.set(postData.id, postData);
                delay += rule.delay_between_posts;
            }

            this.emit('cross_post_scheduled', {
                post_id: postId,
                platforms: platforms,
                rule: rule.id
            });

            return { success: true, post_id: postId, platforms: platforms.length };

        } catch (error) {
            this.emit('cross_post_scheduling_error', { activelogData, rule, error });
            return { success: false, error: error.message };
        }
    }

    async generatePlatformContent(sourceData, rule, platforms) {
        const platformPosts = {};
        const template = this.postTemplates.get(rule.content_strategy) || 
                        this.postTemplates.get('project_announcement');

        for (const platform of platforms) {
            try {
                const platformTemplate = template.variations[platform];
                if (platformTemplate) {
                    // Extract variables from source data
                    const variables = this.extractVariables(sourceData, template.variables);
                    
                    // Optimize content for platform
                    const optimizedContent = await this.optimizeContentForPlatform(
                        platformTemplate, 
                        variables, 
                        platform
                    );

                    platformPosts[platform] = optimizedContent;
                }

            } catch (error) {
                this.emit('content_generation_error', { platform, sourceData, error });
                // Use fallback content
                platformPosts[platform] = this.generateFallbackContent(sourceData, platform);
            }
        }

        return platformPosts;
    }

    extractVariables(sourceData, variableNames) {
        const variables = {};

        variableNames.forEach(varName => {
            switch (varName) {
                case 'project_name':
                    variables[varName] = sourceData.project?.name || sourceData.title || 'New Project';
                    break;
                case 'creator':
                    variables[varName] = sourceData.creator?.username || sourceData.author || 'ActiveLog User';
                    break;
                case 'brief_description':
                    variables[varName] = this.truncateText(sourceData.description || '', 100);
                    break;
                case 'detailed_description':
                    variables[varName] = sourceData.description || '';
                    break;
                case 'link':
                    variables[varName] = sourceData.url || 'https://activelog.com';
                    break;
                case 'category':
                    variables[varName] = sourceData.category || 'Innovation';
                    break;
                case 'key_features':
                    variables[varName] = this.formatList(sourceData.features || []);
                    break;
                case 'highlights':
                    variables[varName] = this.formatHighlights(sourceData.highlights || []);
                    break;
                case 'stats':
                    variables[varName] = this.formatStats(sourceData.stats || {});
                    break;
                case 'milestone_description':
                    variables[varName] = sourceData.milestone?.description || '';
                    break;
                case 'product_name':
                    variables[varName] = sourceData.product?.name || sourceData.title || '';
                    break;
                case 'key_benefit':
                    variables[varName] = sourceData.product?.key_benefit || '';
                    break;
                case 'use_cases':
                    variables[varName] = this.formatUseCases(sourceData.product?.use_cases || []);
                    break;
                default:
                    variables[varName] = sourceData[varName] || '';
            }
        });

        return variables;
    }

    async optimizeContentForPlatform(template, variables, platform) {
        // Fill template with variables
        let content = this.fillTemplate(template, variables);
        
        const platformAdapter = this.platformAdapters.get(platform);
        if (!platformAdapter) return content;

        // Truncate to character limit
        if (content.length > platformAdapter.character_limit) {
            content = this.truncateText(content, platformAdapter.character_limit - 10) + '... (more)';
        }

        // Optimize hashtags based on platform strategy
        content = this.optimizeHashtags(content, platform, platformAdapter.hashtag_strategy);

        // Add platform-specific optimizations
        content = this.addPlatformSpecificElements(content, platform);

        return content;
    }

    fillTemplate(template, variables) {
        let filled = template;
        
        Object.entries(variables).forEach(([key, value]) => {
            const regex = new RegExp(`{${key}}`, 'g');
            filled = filled.replace(regex, value || '');
        });

        return filled.trim();
    }

    optimizeHashtags(content, platform, strategy) {
        switch (strategy) {
            case 'integrated':
                // Keep hashtags as-is (Twitter)
                return content;
                
            case 'end_of_post':
                // Move hashtags to end (LinkedIn)
                const hashtagRegex = /#\w+/g;
                const hashtags = content.match(hashtagRegex) || [];
                const contentWithoutHashtags = content.replace(hashtagRegex, '').trim();
                return hashtags.length > 0 ? 
                    `${contentWithoutHashtags}\n\n${hashtags.join(' ')}` : 
                    contentWithoutHashtags;
                    
            case 'minimal':
                // Reduce hashtags (Facebook)
                const minimalHashtags = (content.match(/#\w+/g) || []).slice(0, 3);
                return content.replace(/#\w+/g, '').trim() + 
                       (minimalHashtags.length > 0 ? `\n\n${minimalHashtags.join(' ')}` : '');
                       
            case 'abundant':
                // Expand hashtags (Instagram)
                return this.expandHashtags(content);
                
            case 'trending_focused':
                // Use trending hashtags (TikTok)
                return this.addTrendingHashtags(content);
                
            default:
                return content;
        }
    }

    expandHashtags(content) {
        // Add more relevant hashtags for Instagram
        const additionalHashtags = [
            '#tech', '#innovation', '#maker', '#diy', '#electronics', 
            '#iot', '#programming', '#opensource', '#community', '#build'
        ];
        
        const existingHashtags = content.match(/#\w+/g) || [];
        const needed = Math.max(0, 10 - existingHashtags.length);
        const toAdd = additionalHashtags.slice(0, needed);
        
        return toAdd.length > 0 ? `${content}\n\n${toAdd.join(' ')}` : content;
    }

    addTrendingHashtags(content) {
        // Add trending TikTok hashtags
        const trendingHashtags = ['#fyp', '#foryou', '#viral', '#trending', '#tech'];
        return `${content}\n\n${trendingHashtags.join(' ')}`;
    }

    addPlatformSpecificElements(content, platform) {
        switch (platform) {
            case 'twitter':
                // Add thread indicator if content is long
                if (content.length > 250) {
                    return content + '\n\n🧵 Thread below ⬇️';
                }
                break;
                
            case 'linkedin':
                // Add professional call-to-action
                return content + '\n\n💭 What are your thoughts on this? Share in the comments!';
                
            case 'instagram':
                // Add engagement prompts
                return content + '\n\n💾 Save this post for later!\n👆 Follow for more updates!';
                
            case 'youtube':
                // Add video-specific CTAs
                return content + '\n\n👍 Like this video if you found it helpful!\n🔔 Subscribe for more content!';
                
            case 'tiktok':
                // Add TikTok-specific elements
                return content + '\n\n✨ Follow for more tech content!';
        }
        
        return content;
    }

    // Utility methods
    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        
        const truncated = text.substring(0, maxLength);
        const lastSpace = truncated.lastIndexOf(' ');
        
        return lastSpace > maxLength * 0.8 ? 
            truncated.substring(0, lastSpace) : 
            truncated;
    }

    formatList(items) {
        if (!Array.isArray(items) || items.length === 0) return '';
        return items.map(item => `• ${item}`).join('\n');
    }

    formatHighlights(highlights) {
        if (!Array.isArray(highlights) || highlights.length === 0) return '';
        return highlights.map((highlight, index) => `${index + 1}. ${highlight}`).join('\n');
    }

    formatStats(stats) {
        if (!stats || Object.keys(stats).length === 0) return '';
        return Object.entries(stats)
            .map(([key, value]) => `${key}: ${value}`)
            .join(' | ');
    }

    formatUseCases(useCases) {
        if (!Array.isArray(useCases) || useCases.length === 0) return '';
        return useCases.slice(0, 3).join(', ');
    }

    generateFallbackContent(sourceData, platform) {
        const platformAdapter = this.platformAdapters.get(platform);
        const maxLength = platformAdapter ? platformAdapter.character_limit - 50 : 200;
        
        const title = sourceData.title || sourceData.project?.name || 'New Update';
        const description = sourceData.description || 'Check out this update from ActiveLog!';
        
        let content = `${title}\n\n${this.truncateText(description, maxLength - title.length - 10)}`;
        
        if (sourceData.url) {
            content += `\n\n🔗 ${sourceData.url}`;
        }
        
        return content;
    }

    // Event handlers for different ActiveLog events
    async handleProjectCreated(projectData) {
        const rule = this.crossPostRules.get('new_project_announcement');
        if (rule) {
            await this.scheduleCrossPost(projectData, rule);
        }
    }

    async handleProjectMilestone(projectData, milestoneData) {
        const rule = this.crossPostRules.get('project_milestone');
        if (rule) {
            const combinedData = { ...projectData, milestone: milestoneData };
            await this.scheduleCrossPost(combinedData, rule);
        }
    }

    async handleProjectFeatured(projectData) {
        const rule = this.crossPostRules.get('product_showcase');
        if (rule) {
            await this.scheduleCrossPost(projectData, rule);
        }
    }

    async handleProjectCompleted(projectData) {
        // Custom logic for completed projects
        const customRule = {
            id: 'project_completed',
            platforms: ['twitter', 'linkedin'],
            content_strategy: 'celebration',
            delay_between_posts: 30
        };
        
        await this.scheduleCrossPost(projectData, customRule);
    }

    async handleUserMilestone(activityData) {
        const rule = this.crossPostRules.get('user_achievement');
        if (rule) {
            await this.scheduleCrossPost(activityData, rule);
        }
    }

    // Manual posting methods
    async createManualCrossPost(content, platforms, options = {}) {
        try {
            const postId = crypto.randomBytes(16).toString('hex');
            const targetPlatforms = platforms.includes('all') ? 
                Array.from(this.platformAdapters.keys()) : 
                platforms;

            const platformPosts = {};
            
            for (const platform of targetPlatforms) {
                // Optimize content for each platform
                const optimizedContent = await this.optimizeContentForPlatform(
                    content.text || content, 
                    content.variables || {}, 
                    platform
                );

                const scheduledTime = options.scheduled_time ? 
                    new Date(options.scheduled_time) : 
                    new Date();

                const postData = {
                    id: `${postId}_${platform}`,
                    platform: platform,
                    content: {
                        text: optimizedContent,
                        media: content.media || [],
                        link: content.link || null
                    },
                    scheduled_time: scheduledTime,
                    status: 'scheduled',
                    is_manual: true,
                    created_at: new Date()
                };

                this.postQueue.set(postData.id, postData);
                platformPosts[platform] = optimizedContent;
            }

            this.emit('manual_cross_post_created', {
                post_id: postId,
                platforms: targetPlatforms,
                content: platformPosts
            });

            return {
                success: true,
                post_id: postId,
                platforms: targetPlatforms,
                scheduled_posts: Object.keys(platformPosts).length
            };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // Queue management
    async processPostQueue() {
        const now = new Date();
        const readyPosts = Array.from(this.postQueue.values())
            .filter(post => post.status === 'scheduled' && post.scheduled_time <= now)
            .sort((a, b) => a.scheduled_time - b.scheduled_time);

        for (const post of readyPosts) {
            try {
                // Update status
                post.status = 'posting';
                this.postQueue.set(post.id, post);

                // Execute the post
                const result = await this.executePost(post);
                
                if (result.success) {
                    post.status = 'completed';
                    post.posted_at = new Date();
                    post.platform_response = result.response;
                } else {
                    post.status = 'failed';
                    post.error = result.error;
                    post.retry_count = (post.retry_count || 0) + 1;
                }

                this.postQueue.set(post.id, post);
                
                // Move to history
                this.postHistory.set(post.id, { ...post });
                
                // Remove from queue if completed or failed too many times
                if (post.status === 'completed' || post.retry_count >= 3) {
                    this.postQueue.delete(post.id);
                }

                this.emit('post_processed', { post_id: post.id, status: post.status });

            } catch (error) {
                this.emit('post_processing_error', { post_id: post.id, error });
            }
        }
    }

    async executePost(postData) {
        try {
            // This would integrate with the MultiPlatformConnector
            this.emit('execute_post', postData);
            
            // Mock successful execution
            return {
                success: true,
                response: {
                    platform: postData.platform,
                    post_id: crypto.randomBytes(16).toString('hex'),
                    timestamp: new Date()
                }
            };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // Analytics and reporting
    getCrossPostingStats(timeframe = '7d') {
        const now = new Date();
        const cutoff = new Date(now.getTime() - (timeframe === '7d' ? 7 : 30) * 24 * 60 * 60 * 1000);
        
        const recentPosts = Array.from(this.postHistory.values())
            .filter(post => post.created_at >= cutoff);

        const stats = {
            total_posts: recentPosts.length,
            successful_posts: recentPosts.filter(p => p.status === 'completed').length,
            failed_posts: recentPosts.filter(p => p.status === 'failed').length,
            platform_breakdown: {},
            rule_breakdown: {},
            average_delay_minutes: 0,
            pending_posts: this.postQueue.size
        };

        recentPosts.forEach(post => {
            // Platform breakdown
            stats.platform_breakdown[post.platform] = 
                (stats.platform_breakdown[post.platform] || 0) + 1;

            // Rule breakdown
            if (post.rule_id) {
                stats.rule_breakdown[post.rule_id] = 
                    (stats.rule_breakdown[post.rule_id] || 0) + 1;
            }
        });

        return stats;
    }

    getQueueStatus() {
        const queueArray = Array.from(this.postQueue.values());
        
        return {
            total_queued: queueArray.length,
            scheduled: queueArray.filter(p => p.status === 'scheduled').length,
            posting: queueArray.filter(p => p.status === 'posting').length,
            failed: queueArray.filter(p => p.status === 'failed').length,
            next_post: queueArray
                .filter(p => p.status === 'scheduled')
                .sort((a, b) => a.scheduled_time - b.scheduled_time)[0]?.scheduled_time
        };
    }

    // Configuration management
    updateCrossPostRule(ruleId, updates) {
        if (this.crossPostRules.has(ruleId)) {
            const currentRule = this.crossPostRules.get(ruleId);
            const updatedRule = { ...currentRule, ...updates };
            this.crossPostRules.set(ruleId, updatedRule);
            
            this.emit('rule_updated', { rule_id: ruleId, updates });
            return { success: true };
        }
        
        return { success: false, error: 'Rule not found' };
    }

    addPostTemplate(template) {
        const templateId = template.id || crypto.randomBytes(16).toString('hex');
        this.postTemplates.set(templateId, { ...template, id: templateId });
        
        this.emit('template_added', templateId);
        return { success: true, template_id: templateId };
    }
}

export default CrossPlatformPosting;