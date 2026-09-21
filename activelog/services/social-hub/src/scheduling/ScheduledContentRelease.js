import { EventEmitter } from 'events';
import cron from 'node-cron';
import crypto from 'crypto';
import OpenAI from 'openai';

class ScheduledContentRelease extends EventEmitter {
    constructor(config = {}) {
        super();
        this.schedules = new Map();
        this.contentQueue = new Map();
        this.campaigns = new Map();
        this.templates = new Map();
        this.automationRules = new Map();
        this.timezones = new Map();
        this.contentCalendar = new Map();
        this.recurrentSchedules = new Map();
        this.activeJobs = new Map();

        this.openai = new OpenAI({
            apiKey: config.openai_api_key || process.env.OPENAI_API_KEY
        });

        this.initializeSystem();
    }

    initializeSystem() {
        this.initializeScheduleTemplates();
        this.initializeAutomationRules();
        this.initializeTimezoneSettings();
        this.initializeRecurrentPatterns();
        this.startScheduleProcessor();
        
        this.emit('scheduler_initialized');
    }

    initializeScheduleTemplates() {
        const templates = [
            {
                id: 'daily_highlights',
                name: 'Daily Highlights',
                description: 'Daily content highlighting community activities',
                frequency: 'daily',
                time: '09:00',
                timezone: 'UTC',
                platforms: ['twitter', 'linkedin', 'facebook'],
                content_type: 'auto_generated',
                content_strategy: {
                    source: 'community_activity',
                    max_items: 3,
                    include_stats: true,
                    tone: 'engaging'
                },
                active: true
            },
            {
                id: 'weekly_roundup',
                name: 'Weekly Roundup',
                description: 'Weekly summary of top projects and achievements',
                frequency: 'weekly',
                day: 'friday',
                time: '14:00',
                timezone: 'UTC',
                platforms: ['linkedin', 'facebook', 'youtube'],
                content_type: 'curated_digest',
                content_strategy: {
                    source: 'top_projects',
                    period: '7d',
                    min_engagement: 50,
                    include_metrics: true
                },
                active: true
            },
            {
                id: 'product_spotlight',
                name: 'Product Spotlight',
                description: 'Bi-weekly product or feature highlights',
                frequency: 'bi_weekly',
                day: 'tuesday',
                time: '11:00',
                timezone: 'UTC',
                platforms: ['all'],
                content_type: 'product_showcase',
                content_strategy: {
                    source: 'featured_products',
                    rotation_strategy: 'balanced',
                    include_testimonials: true
                },
                active: true
            },
            {
                id: 'community_milestones',
                name: 'Community Milestones',
                description: 'Celebrate community achievements and milestones',
                frequency: 'event_triggered',
                trigger_condition: 'milestone_reached',
                platforms: ['all'],
                content_type: 'celebration',
                content_strategy: {
                    source: 'milestone_data',
                    personalization: 'high',
                    call_to_action: true
                },
                active: true
            },
            {
                id: 'tech_tips_tuesday',
                name: 'Tech Tips Tuesday',
                description: 'Weekly technical tips and tutorials',
                frequency: 'weekly',
                day: 'tuesday',
                time: '10:00',
                timezone: 'UTC',
                platforms: ['twitter', 'linkedin', 'instagram'],
                content_type: 'educational',
                content_strategy: {
                    source: 'tip_database',
                    difficulty_level: 'mixed',
                    include_visuals: true
                },
                active: true
            },
            {
                id: 'motivational_monday',
                name: 'Motivational Monday',
                description: 'Inspirational content to start the week',
                frequency: 'weekly',
                day: 'monday',
                time: '08:00',
                timezone: 'UTC',
                platforms: ['instagram', 'facebook', 'twitter'],
                content_type: 'inspirational',
                content_strategy: {
                    source: 'quote_database',
                    include_community_stories: true,
                    visual_style: 'motivational'
                },
                active: true
            }
        ];

        templates.forEach(template => {
            this.templates.set(template.id, template);
        });
    }

    initializeAutomationRules() {
        const rules = [
            {
                id: 'optimal_timing',
                name: 'Optimal Timing Adjustment',
                description: 'Automatically adjust posting times based on engagement data',
                enabled: true,
                conditions: {
                    min_data_points: 10,
                    engagement_threshold_improvement: 15
                },
                actions: ['adjust_timing', 'notify_team']
            },
            {
                id: 'content_gap_filler',
                name: 'Content Gap Filler',
                description: 'Automatically generate content when gaps are detected',
                enabled: true,
                conditions: {
                    max_gap_hours: 24,
                    exclude_weekends: true
                },
                actions: ['generate_fill_content', 'schedule_post']
            },
            {
                id: 'holiday_awareness',
                name: 'Holiday Content Adjustment',
                description: 'Adjust content strategy for holidays and special events',
                enabled: true,
                conditions: {
                    holiday_calendar: 'global',
                    adjustment_days_before: 3
                },
                actions: ['pause_regular_content', 'activate_holiday_content']
            },
            {
                id: 'trending_boost',
                name: 'Trending Topic Boost',
                description: 'Increase posting frequency when trending',
                enabled: true,
                conditions: {
                    trend_score_threshold: 7.0,
                    trend_duration_hours: 4
                },
                actions: ['increase_frequency', 'prioritize_trending_content']
            }
        ];

        rules.forEach(rule => {
            this.automationRules.set(rule.id, rule);
        });
    }

    initializeTimezoneSettings() {
        const timezones = [
            {
                id: 'primary',
                timezone: 'America/New_York',
                weight: 0.4,
                peak_hours: ['09:00', '12:00', '15:00', '18:00'],
                description: 'Primary US audience'
            },
            {
                id: 'secondary',
                timezone: 'Europe/London',
                weight: 0.3,
                peak_hours: ['08:00', '12:00', '17:00'],
                description: 'European audience'
            },
            {
                id: 'tertiary',
                timezone: 'Asia/Tokyo',
                weight: 0.2,
                peak_hours: ['09:00', '12:00', '19:00'],
                description: 'Asian Pacific audience'
            },
            {
                id: 'global',
                timezone: 'UTC',
                weight: 0.1,
                peak_hours: ['12:00', '18:00'],
                description: 'Global coordination'
            }
        ];

        timezones.forEach(tz => {
            this.timezones.set(tz.id, tz);
        });
    }

    initializeRecurrentPatterns() {
        const patterns = [
            {
                id: 'business_days',
                name: 'Business Days Only',
                pattern: '0 9-17 * * 1-5',
                description: 'Weekdays 9AM-5PM'
            },
            {
                id: 'peak_engagement',
                name: 'Peak Engagement Times',
                pattern: '0 9,12,15,18 * * *',
                description: 'Daily at peak hours'
            },
            {
                id: 'weekend_light',
                name: 'Weekend Light Schedule',
                pattern: '0 10,14 * * 6,0',
                description: 'Reduced weekend posting'
            },
            {
                id: 'weekly_summary',
                name: 'Weekly Summary',
                pattern: '0 14 * * 5',
                description: 'Every Friday at 2PM'
            }
        ];

        patterns.forEach(pattern => {
            this.recurrentSchedules.set(pattern.id, pattern);
        });
    }

    // Core scheduling methods
    async createSchedule(scheduleData) {
        try {
            const scheduleId = crypto.randomBytes(16).toString('hex');
            
            const schedule = {
                id: scheduleId,
                name: scheduleData.name,
                description: scheduleData.description,
                content_template: scheduleData.content_template || 'auto_generate',
                platforms: scheduleData.platforms || ['twitter'],
                frequency: scheduleData.frequency,
                timing: this.parseTimingConfig(scheduleData.timing),
                content_strategy: scheduleData.content_strategy || {},
                status: 'active',
                created_at: new Date(),
                next_execution: null,
                last_execution: null,
                execution_count: 0,
                success_rate: 1.0,
                engagement_metrics: {
                    average_engagement: 0,
                    best_performing_time: null,
                    platform_performance: {}
                }
            };

            // Calculate next execution time
            schedule.next_execution = this.calculateNextExecution(schedule);

            this.schedules.set(scheduleId, schedule);
            
            // Set up cron job
            await this.setupCronJob(schedule);

            this.emit('schedule_created', { schedule_id: scheduleId, schedule });
            
            return {
                success: true,
                schedule_id: scheduleId,
                next_execution: schedule.next_execution
            };

        } catch (error) {
            this.emit('schedule_creation_error', { scheduleData, error });
            return { success: false, error: error.message };
        }
    }

    parseTimingConfig(timing) {
        if (typeof timing === 'string') {
            // Simple time string like "09:00"
            return {
                type: 'fixed',
                time: timing,
                timezone: 'UTC'
            };
        } else if (timing.type === 'optimal') {
            // AI-optimized timing
            return {
                type: 'optimal',
                target_audience: timing.target_audience || 'global',
                optimization_metric: timing.optimization_metric || 'engagement'
            };
        } else if (timing.type === 'interval') {
            // Interval-based scheduling
            return {
                type: 'interval',
                interval_hours: timing.interval_hours || 24,
                start_time: timing.start_time || '09:00'
            };
        } else {
            return timing;
        }
    }

    calculateNextExecution(schedule) {
        const now = new Date();
        const timing = schedule.timing;

        switch (schedule.frequency) {
            case 'daily':
                return this.calculateDailyExecution(timing, now);
            case 'weekly':
                return this.calculateWeeklyExecution(timing, now);
            case 'bi_weekly':
                return this.calculateBiWeeklyExecution(timing, now);
            case 'monthly':
                return this.calculateMonthlyExecution(timing, now);
            case 'interval':
                return this.calculateIntervalExecution(timing, now);
            default:
                return new Date(now.getTime() + 24 * 60 * 60 * 1000); // Default to 24 hours
        }
    }

    calculateDailyExecution(timing, from) {
        if (timing.type === 'optimal') {
            return this.calculateOptimalTime(timing, from, 'daily');
        }

        const [hours, minutes] = timing.time.split(':').map(Number);
        const nextExecution = new Date(from);
        nextExecution.setHours(hours, minutes, 0, 0);

        // If time has passed today, schedule for tomorrow
        if (nextExecution <= from) {
            nextExecution.setDate(nextExecution.getDate() + 1);
        }

        return nextExecution;
    }

    calculateWeeklyExecution(timing, from) {
        if (timing.type === 'optimal') {
            return this.calculateOptimalTime(timing, from, 'weekly');
        }

        const targetDay = this.getDayNumber(timing.day || 'monday');
        const [hours, minutes] = timing.time.split(':').map(Number);
        
        const nextExecution = new Date(from);
        const currentDay = nextExecution.getDay();
        const daysToAdd = (targetDay - currentDay + 7) % 7;
        
        if (daysToAdd === 0 && nextExecution.getHours() >= hours) {
            // If it's the same day but time has passed, schedule for next week
            nextExecution.setDate(nextExecution.getDate() + 7);
        } else {
            nextExecution.setDate(nextExecution.getDate() + daysToAdd);
        }
        
        nextExecution.setHours(hours, minutes, 0, 0);
        return nextExecution;
    }

    calculateOptimalTime(timing, from, frequency) {
        // For now, return a simple calculation
        // In production, this would analyze engagement data
        const baseHours = [9, 12, 15, 18]; // Peak engagement hours
        const randomHour = baseHours[Math.floor(Math.random() * baseHours.length)];
        
        const nextExecution = new Date(from);
        
        if (frequency === 'daily') {
            nextExecution.setHours(randomHour, 0, 0, 0);
            if (nextExecution <= from) {
                nextExecution.setDate(nextExecution.getDate() + 1);
            }
        } else if (frequency === 'weekly') {
            const targetDay = 1 + Math.floor(Math.random() * 5); // Monday to Friday
            const currentDay = nextExecution.getDay();
            const daysToAdd = (targetDay - currentDay + 7) % 7;
            
            nextExecution.setDate(nextExecution.getDate() + daysToAdd);
            nextExecution.setHours(randomHour, 0, 0, 0);
        }
        
        return nextExecution;
    }

    getDayNumber(dayName) {
        const days = {
            'sunday': 0, 'monday': 1, 'tuesday': 2, 'wednesday': 3,
            'thursday': 4, 'friday': 5, 'saturday': 6
        };
        return days[dayName.toLowerCase()] || 1;
    }

    async setupCronJob(schedule) {
        try {
            const cronExpression = this.generateCronExpression(schedule);
            
            const job = cron.schedule(cronExpression, async () => {
                await this.executeSchedule(schedule.id);
            }, {
                scheduled: true,
                timezone: schedule.timing.timezone || 'UTC'
            });

            this.activeJobs.set(schedule.id, job);

        } catch (error) {
            this.emit('cron_setup_error', { schedule, error });
        }
    }

    generateCronExpression(schedule) {
        const timing = schedule.timing;
        
        switch (schedule.frequency) {
            case 'daily':
                if (timing.time) {
                    const [hours, minutes] = timing.time.split(':').map(Number);
                    return `${minutes} ${hours} * * *`;
                }
                return '0 9 * * *'; // Default 9 AM daily
                
            case 'weekly':
                const [hours, minutes] = timing.time.split(':').map(Number);
                const dayNum = this.getDayNumber(timing.day || 'monday');
                return `${minutes} ${hours} * * ${dayNum}`;
                
            case 'interval':
                // For intervals, we'll use a frequent check and handle logic internally
                return '*/15 * * * *'; // Check every 15 minutes
                
            default:
                return '0 9 * * *';
        }
    }

    // Content generation and scheduling
    async executeSchedule(scheduleId) {
        try {
            const schedule = this.schedules.get(scheduleId);
            if (!schedule || schedule.status !== 'active') {
                return;
            }

            this.emit('schedule_execution_started', { schedule_id: scheduleId });

            // Generate content based on strategy
            const content = await this.generateScheduledContent(schedule);
            
            if (content.success) {
                // Queue content for posting
                const queuedPosts = await this.queueContentForPosting(content.posts, schedule);
                
                // Update schedule metrics
                schedule.execution_count += 1;
                schedule.last_execution = new Date();
                schedule.next_execution = this.calculateNextExecution(schedule);
                
                this.schedules.set(scheduleId, schedule);

                this.emit('schedule_executed', {
                    schedule_id: scheduleId,
                    posts_queued: queuedPosts.length,
                    next_execution: schedule.next_execution
                });

                return {
                    success: true,
                    posts_queued: queuedPosts.length,
                    content_preview: content.preview
                };
            } else {
                this.emit('schedule_execution_failed', {
                    schedule_id: scheduleId,
                    error: content.error
                });

                return { success: false, error: content.error };
            }

        } catch (error) {
            this.emit('schedule_execution_error', { schedule_id: scheduleId, error });
            return { success: false, error: error.message };
        }
    }

    async generateScheduledContent(schedule) {
        try {
            const strategy = schedule.content_strategy;
            let contentData;

            switch (strategy.source) {
                case 'community_activity':
                    contentData = await this.fetchCommunityActivity(strategy);
                    break;
                case 'top_projects':
                    contentData = await this.fetchTopProjects(strategy);
                    break;
                case 'featured_products':
                    contentData = await this.fetchFeaturedProducts(strategy);
                    break;
                case 'tip_database':
                    contentData = await this.fetchTechTips(strategy);
                    break;
                case 'quote_database':
                    contentData = await this.fetchInspirationalContent(strategy);
                    break;
                default:
                    contentData = await this.generateGenericContent(strategy);
            }

            if (!contentData || contentData.length === 0) {
                throw new Error('No content data available');
            }

            // Generate posts for each platform
            const posts = {};
            for (const platform of schedule.platforms) {
                posts[platform] = await this.generatePlatformContent(
                    contentData,
                    platform,
                    strategy,
                    schedule.content_template
                );
            }

            return {
                success: true,
                posts: posts,
                preview: this.generateContentPreview(posts)
            };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async fetchCommunityActivity(strategy) {
        // Mock community activity data
        return [
            {
                type: 'project_created',
                project_name: 'Smart Fish Counter v2.0',
                creator: 'TechMaker2024',
                description: 'Enhanced AI-powered fish counting system',
                engagement_score: 85,
                created_at: new Date()
            },
            {
                type: 'collaboration',
                participants: ['OpenSourceBuilder', 'FishingTechGuru'],
                project: 'Marine Sensor Network',
                milestone: 'First deployment successful',
                engagement_score: 72
            },
            {
                type: 'achievement',
                user: 'InnovativeDesigner',
                achievement: '10th successful project',
                community_impact: 'High',
                engagement_score: 91
            }
        ];
    }

    async fetchTopProjects(strategy) {
        // Mock top projects data
        return [
            {
                name: 'Solar-Powered Weather Station',
                creator: 'WeatherTech',
                category: 'Environmental Monitoring',
                engagement_metrics: { views: 1250, likes: 89, shares: 34 },
                description: 'Complete weather monitoring solution with solar power',
                technical_highlights: ['ESP32 controller', 'Multiple sensors', 'Cloud connectivity']
            },
            {
                name: 'IoT Plant Care System',
                creator: 'GreenThumb',
                category: 'Agriculture Tech',
                engagement_metrics: { views: 980, likes: 76, shares: 28 },
                description: 'Automated plant monitoring and care system',
                technical_highlights: ['Moisture sensors', 'Automated watering', 'Mobile app']
            }
        ];
    }

    async generatePlatformContent(contentData, platform, strategy, template) {
        try {
            const platformContent = this.adaptContentForPlatform(contentData, platform, strategy);
            
            // Use AI to generate engaging content
            if (this.openai.apiKey) {
                return await this.generateAIContent(platformContent, platform, strategy);
            } else {
                return this.generateTemplateContent(platformContent, platform, template);
            }

        } catch (error) {
            // Fallback to template-based generation
            return this.generateTemplateContent(contentData, platform, template);
        }
    }

    async generateAIContent(contentData, platform, strategy) {
        try {
            const prompt = this.buildAIPrompt(contentData, platform, strategy);
            
            const completion = await this.openai.chat.completions.create({
                model: "gpt-3.5-turbo",
                messages: [{ role: "user", content: prompt }],
                temperature: 0.7,
                max_tokens: this.getPlatformTokenLimit(platform)
            });

            const generatedContent = completion.choices[0].message.content.trim();
            
            return {
                text: generatedContent,
                generated_by: 'ai',
                source_data: contentData,
                platform: platform
            };

        } catch (error) {
            throw new Error(`AI content generation failed: ${error.message}`);
        }
    }

    buildAIPrompt(contentData, platform, strategy) {
        const platformSpecs = this.getPlatformSpecs(platform);
        const tone = strategy.tone || 'engaging';
        
        return `Create ${tone} social media content for ${platform} based on this data:

${JSON.stringify(contentData, null, 2)}

Platform requirements:
- Character limit: ${platformSpecs.character_limit}
- Hashtag style: ${platformSpecs.hashtag_style}
- Audience: ${platformSpecs.audience}

Content should be:
- ${tone} and ${platformSpecs.style}
- Include relevant hashtags
- Encourage engagement
- Represent ActiveLog brand voice
- ${strategy.include_stats ? 'Include metrics/stats' : 'Focus on storytelling'}

Generate only the post content, no explanations.`;
    }

    getPlatformSpecs(platform) {
        const specs = {
            twitter: {
                character_limit: 280,
                hashtag_style: 'integrated',
                audience: 'tech-savvy professionals',
                style: 'concise and punchy'
            },
            linkedin: {
                character_limit: 1300,
                hashtag_style: 'end of post',
                audience: 'professionals and businesses',
                style: 'professional yet approachable'
            },
            facebook: {
                character_limit: 400,
                hashtag_style: 'minimal',
                audience: 'general tech enthusiasts',
                style: 'conversational and community-focused'
            },
            instagram: {
                character_limit: 300,
                hashtag_style: 'abundant',
                audience: 'visual-focused creators',
                style: 'visual and inspirational'
            }
        };
        
        return specs[platform] || specs.twitter;
    }

    getPlatformTokenLimit(platform) {
        const limits = {
            twitter: 80,
            linkedin: 300,
            facebook: 150,
            instagram: 100
        };
        
        return limits[platform] || 150;
    }

    generateTemplateContent(contentData, platform, template) {
        // Fallback template-based content generation
        const templates = {
            daily_highlights: `🌟 Today's ActiveLog highlights:\n\n{highlights}\n\n💡 What's your current project? Share below!\n\n#ActiveLog #Innovation #Community`,
            weekly_roundup: `📅 Week in Review:\n\n{weekly_summary}\n\n🚀 Amazing work by our community!\n\n#WeeklyRoundup #ActiveLog #Projects`,
            product_spotlight: `🔥 Product Spotlight: {product_name}\n\n{description}\n\n💪 Built with innovation in mind!\n\n{link}\n\n#ProductSpotlight #Innovation`
        };

        const templateText = templates[template] || templates.daily_highlights;
        return {
            text: this.fillContentTemplate(templateText, contentData),
            generated_by: 'template',
            source_data: contentData,
            platform: platform
        };
    }

    fillContentTemplate(template, data) {
        let filled = template;
        
        // Basic template filling logic
        if (Array.isArray(data)) {
            const highlights = data.slice(0, 3).map((item, index) => 
                `${index + 1}. ${item.project_name || item.name || item.title || 'New update'}`
            ).join('\n');
            filled = filled.replace('{highlights}', highlights);
            filled = filled.replace('{weekly_summary}', highlights);
        }

        // Replace other placeholders
        filled = filled.replace('{product_name}', data.name || 'Featured Product');
        filled = filled.replace('{description}', data.description || 'Check out this amazing innovation!');
        filled = filled.replace('{link}', 'https://activelog.com');

        return filled;
    }

    adaptContentForPlatform(contentData, platform, strategy) {
        // Adapt content structure and emphasis for each platform
        switch (platform) {
            case 'twitter':
                return {
                    ...contentData,
                    focus: 'brevity',
                    include_hashtags: true,
                    call_to_action: 'retweet'
                };
            case 'linkedin':
                return {
                    ...contentData,
                    focus: 'professional_value',
                    include_hashtags: true,
                    call_to_action: 'connect'
                };
            case 'instagram':
                return {
                    ...contentData,
                    focus: 'visual_appeal',
                    include_hashtags: true,
                    call_to_action: 'save'
                };
            case 'facebook':
                return {
                    ...contentData,
                    focus: 'community',
                    include_hashtags: false,
                    call_to_action: 'share'
                };
            default:
                return contentData;
        }
    }

    async queueContentForPosting(posts, schedule) {
        const queuedPosts = [];
        let delay = 0;

        for (const [platform, content] of Object.entries(posts)) {
            const postId = crypto.randomBytes(16).toString('hex');
            const scheduledTime = new Date(Date.now() + delay * 60 * 1000); // Delay in minutes

            const queuedPost = {
                id: postId,
                schedule_id: schedule.id,
                platform: platform,
                content: content,
                scheduled_time: scheduledTime,
                status: 'queued',
                created_at: new Date(),
                attempts: 0
            };

            this.contentQueue.set(postId, queuedPost);
            queuedPosts.push(queuedPost);

            delay += 15; // 15 minute delay between posts
        }

        this.emit('content_queued', {
            schedule_id: schedule.id,
            posts_queued: queuedPosts.length
        });

        return queuedPosts;
    }

    generateContentPreview(posts) {
        const preview = {};
        
        Object.entries(posts).forEach(([platform, content]) => {
            preview[platform] = {
                text_preview: content.text?.substring(0, 100) + (content.text?.length > 100 ? '...' : ''),
                character_count: content.text?.length || 0,
                has_media: Boolean(content.media),
                hashtag_count: (content.text?.match(/#\w+/g) || []).length
            };
        });

        return preview;
    }

    // Campaign management
    async createCampaign(campaignData) {
        try {
            const campaignId = crypto.randomBytes(16).toString('hex');
            
            const campaign = {
                id: campaignId,
                name: campaignData.name,
                description: campaignData.description,
                start_date: new Date(campaignData.start_date),
                end_date: new Date(campaignData.end_date),
                schedules: campaignData.schedules || [],
                content_themes: campaignData.content_themes || [],
                target_metrics: campaignData.target_metrics || {},
                status: 'active',
                created_at: new Date()
            };

            this.campaigns.set(campaignId, campaign);

            // Create schedules for campaign
            const createdSchedules = [];
            for (const scheduleConfig of campaignData.schedules) {
                const schedule = await this.createSchedule({
                    ...scheduleConfig,
                    campaign_id: campaignId
                });
                
                if (schedule.success) {
                    createdSchedules.push(schedule.schedule_id);
                }
            }

            campaign.created_schedules = createdSchedules;
            this.campaigns.set(campaignId, campaign);

            this.emit('campaign_created', { campaign_id: campaignId, schedules: createdSchedules.length });

            return {
                success: true,
                campaign_id: campaignId,
                schedules_created: createdSchedules.length
            };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // Queue processing
    startScheduleProcessor() {
        // Process content queue every minute
        setInterval(async () => {
            await this.processContentQueue();
        }, 60 * 1000);

        // Optimize schedules every hour
        setInterval(async () => {
            await this.optimizeSchedules();
        }, 60 * 60 * 1000);
    }

    async processContentQueue() {
        const now = new Date();
        const readyPosts = Array.from(this.contentQueue.values())
            .filter(post => post.status === 'queued' && post.scheduled_time <= now)
            .sort((a, b) => a.scheduled_time - b.scheduled_time);

        for (const post of readyPosts) {
            try {
                post.status = 'posting';
                post.attempts += 1;
                this.contentQueue.set(post.id, post);

                // Execute the post via cross-platform posting system
                this.emit('execute_scheduled_post', post);

                post.status = 'completed';
                post.posted_at = new Date();

                this.contentQueue.set(post.id, post);
                
                // Remove from queue after successful posting
                setTimeout(() => {
                    this.contentQueue.delete(post.id);
                }, 60000); // Keep for 1 minute for debugging

            } catch (error) {
                post.status = 'failed';
                post.error = error.message;
                post.retry_at = new Date(Date.now() + 30 * 60 * 1000); // Retry in 30 minutes

                if (post.attempts >= 3) {
                    post.status = 'permanently_failed';
                    this.emit('post_permanently_failed', post);
                }

                this.contentQueue.set(post.id, post);
            }
        }
    }

    async optimizeSchedules() {
        // Placeholder for schedule optimization logic
        for (const [scheduleId, schedule] of this.schedules) {
            if (schedule.status === 'active') {
                // Analyze performance and adjust if needed
                await this.analyzeSchedulePerformance(scheduleId);
            }
        }
    }

    async analyzeSchedulePerformance(scheduleId) {
        // Placeholder for performance analysis
        // Would analyze engagement metrics and adjust timing
        const schedule = this.schedules.get(scheduleId);
        
        if (schedule && schedule.execution_count >= 10) {
            // Enough data to start optimizing
            this.emit('schedule_optimization_candidate', { schedule_id: scheduleId });
        }
    }

    // Management and analytics
    getScheduleStats() {
        const schedules = Array.from(this.schedules.values());
        const activeSchedules = schedules.filter(s => s.status === 'active');
        const queuedPosts = Array.from(this.contentQueue.values());

        return {
            total_schedules: schedules.length,
            active_schedules: activeSchedules.length,
            total_executions: schedules.reduce((sum, s) => sum + s.execution_count, 0),
            queued_posts: queuedPosts.length,
            pending_posts: queuedPosts.filter(p => p.status === 'queued').length,
            failed_posts: queuedPosts.filter(p => p.status === 'failed').length,
            next_scheduled_post: queuedPosts
                .filter(p => p.status === 'queued')
                .sort((a, b) => a.scheduled_time - b.scheduled_time)[0]?.scheduled_time
        };
    }

    async pauseSchedule(scheduleId) {
        const schedule = this.schedules.get(scheduleId);
        if (schedule) {
            schedule.status = 'paused';
            this.schedules.set(scheduleId, schedule);
            
            // Stop cron job
            const job = this.activeJobs.get(scheduleId);
            if (job) {
                job.stop();
            }

            this.emit('schedule_paused', { schedule_id: scheduleId });
            return { success: true };
        }
        
        return { success: false, error: 'Schedule not found' };
    }

    async resumeSchedule(scheduleId) {
        const schedule = this.schedules.get(scheduleId);
        if (schedule) {
            schedule.status = 'active';
            schedule.next_execution = this.calculateNextExecution(schedule);
            this.schedules.set(scheduleId, schedule);
            
            // Restart cron job
            await this.setupCronJob(schedule);

            this.emit('schedule_resumed', { schedule_id: scheduleId });
            return { success: true };
        }
        
        return { success: false, error: 'Schedule not found' };
    }

    async updateSchedule(scheduleId, updates) {
        const schedule = this.schedules.get(scheduleId);
        if (schedule) {
            // Stop current job
            const job = this.activeJobs.get(scheduleId);
            if (job) {
                job.stop();
                this.activeJobs.delete(scheduleId);
            }

            // Update schedule
            Object.assign(schedule, updates);
            schedule.next_execution = this.calculateNextExecution(schedule);
            this.schedules.set(scheduleId, schedule);

            // Setup new job
            if (schedule.status === 'active') {
                await this.setupCronJob(schedule);
            }

            this.emit('schedule_updated', { schedule_id: scheduleId });
            return { success: true };
        }
        
        return { success: false, error: 'Schedule not found' };
    }

    getContentCalendar(startDate, endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        const calendar = [];

        // Get all scheduled executions in date range
        for (const [scheduleId, schedule] of this.schedules) {
            if (schedule.status === 'active') {
                let nextExecution = new Date(schedule.next_execution);
                
                while (nextExecution <= end) {
                    if (nextExecution >= start) {
                        calendar.push({
                            date: new Date(nextExecution),
                            schedule_id: scheduleId,
                            schedule_name: schedule.name,
                            platforms: schedule.platforms,
                            content_type: schedule.content_strategy.source
                        });
                    }

                    // Calculate next occurrence
                    const tempSchedule = { ...schedule, next_execution: nextExecution };
                    nextExecution = this.calculateNextExecution(tempSchedule);
                    
                    // Prevent infinite loops
                    if (nextExecution <= tempSchedule.next_execution) {
                        break;
                    }
                }
            }
        }

        return calendar.sort((a, b) => a.date - b.date);
    }
}

export default ScheduledContentRelease;