import { EventEmitter } from 'events';
import fs from 'fs/promises';
import path from 'path';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';

class DistributionAutomator extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            rss_output_directory: config.rss_output_directory || './output/rss',
            distribution_configs_directory: config.distribution_configs_directory || './data/distribution_configs',
            default_podcast_artwork: config.default_podcast_artwork || './assets/default_artwork.jpg',
            base_url: config.base_url || 'https://your-podcast-domain.com',
            ...config
        };

        this.distributionPlatforms = new Map();
        this.rssFeeds = new Map();
        this.distributionTasks = new Map();
        this.webhooks = new Map();

        this.initializeDistributionPlatforms();
        this.ensureDirectories();
    }

    async ensureDirectories() {
        try {
            await fs.mkdir(this.config.rss_output_directory, { recursive: true });
            await fs.mkdir(this.config.distribution_configs_directory, { recursive: true });
        } catch (error) {
            this.emit('error', { type: 'directory-creation', error });
        }
    }

    initializeDistributionPlatforms() {
        // Spotify for Podcasters (Anchor)
        this.distributionPlatforms.set('spotify', {
            id: 'spotify',
            name: 'Spotify for Podcasters',
            type: 'rss_feed',
            requires_approval: true,
            supports_analytics: true,
            supports_monetization: true,
            submission_method: 'rss_url',
            api_available: true,
            requirements: {
                min_episodes: 1,
                artwork_size: '1400x1400',
                audio_formats: ['mp3', 'm4a'],
                min_bitrate: '96kbps',
                required_fields: ['title', 'description', 'author', 'category', 'language']
            }
        });

        // Apple Podcasts
        this.distributionPlatforms.set('apple_podcasts', {
            id: 'apple_podcasts',
            name: 'Apple Podcasts',
            type: 'rss_feed',
            requires_approval: true,
            supports_analytics: true,
            supports_monetization: true,
            submission_method: 'rss_url',
            api_available: false,
            requirements: {
                min_episodes: 1,
                artwork_size: '1400x1400',
                audio_formats: ['mp3', 'm4a'],
                min_bitrate: '64kbps',
                required_fields: ['title', 'description', 'author', 'category', 'language', 'explicit']
            }
        });

        // Google Podcasts
        this.distributionPlatforms.set('google_podcasts', {
            id: 'google_podcasts',
            name: 'Google Podcasts',
            type: 'rss_feed',
            requires_approval: false,
            supports_analytics: true,
            supports_monetization: false,
            submission_method: 'rss_url',
            api_available: false,
            requirements: {
                min_episodes: 1,
                artwork_size: '1400x1400',
                audio_formats: ['mp3'],
                min_bitrate: '96kbps',
                required_fields: ['title', 'description', 'author']
            }
        });

        // Amazon Music/Audible
        this.distributionPlatforms.set('amazon_music', {
            id: 'amazon_music',
            name: 'Amazon Music',
            type: 'rss_feed',
            requires_approval: true,
            supports_analytics: true,
            supports_monetization: true,
            submission_method: 'rss_url',
            api_available: false,
            requirements: {
                min_episodes: 3,
                artwork_size: '1400x1400',
                audio_formats: ['mp3'],
                min_bitrate: '128kbps',
                required_fields: ['title', 'description', 'author', 'category', 'language']
            }
        });

        // Stitcher
        this.distributionPlatforms.set('stitcher', {
            id: 'stitcher',
            name: 'Stitcher',
            type: 'rss_feed',
            requires_approval: true,
            supports_analytics: true,
            supports_monetization: false,
            submission_method: 'rss_url',
            api_available: false,
            requirements: {
                min_episodes: 1,
                artwork_size: '1400x1400',
                audio_formats: ['mp3'],
                min_bitrate: '64kbps',
                required_fields: ['title', 'description', 'author', 'category']
            }
        });

        // YouTube
        this.distributionPlatforms.set('youtube', {
            id: 'youtube',
            name: 'YouTube',
            type: 'video_upload',
            requires_approval: false,
            supports_analytics: true,
            supports_monetization: true,
            submission_method: 'api_upload',
            api_available: true,
            requirements: {
                min_episodes: 1,
                artwork_size: '1280x720',
                video_formats: ['mp4'],
                audio_formats: ['mp3', 'm4a'],
                required_fields: ['title', 'description', 'tags', 'category']
            }
        });

        // Custom RSS
        this.distributionPlatforms.set('custom_rss', {
            id: 'custom_rss',
            name: 'Custom RSS Feed',
            type: 'rss_feed',
            requires_approval: false,
            supports_analytics: false,
            supports_monetization: false,
            submission_method: 'self_hosted',
            api_available: false,
            requirements: {
                min_episodes: 1,
                artwork_size: '1400x1400',
                audio_formats: ['mp3', 'm4a'],
                required_fields: ['title', 'description', 'author']
            }
        });
    }

    async createRSSFeed(podcastMetadata, episodes = []) {
        const feedId = uuidv4();
        
        try {
            this.emit('rss-creation-started', { feedId });

            const rssContent = await this.generateRSSContent(podcastMetadata, episodes);
            const feedFilename = `${podcastMetadata.slug || 'podcast'}.xml`;
            const feedPath = path.join(this.config.rss_output_directory, feedFilename);
            
            await fs.writeFile(feedPath, rssContent, 'utf8');

            const feedUrl = `${this.config.base_url}/rss/${feedFilename}`;
            
            const rssInfo = {
                id: feedId,
                podcast_metadata: podcastMetadata,
                episodes: episodes,
                feed_path: feedPath,
                feed_url: feedUrl,
                created_at: new Date().toISOString(),
                last_updated: new Date().toISOString()
            };

            this.rssFeeds.set(feedId, rssInfo);

            this.emit('rss-created', {
                feedId,
                feedUrl,
                episodeCount: episodes.length
            });

            return {
                feed_id: feedId,
                feed_url: feedUrl,
                feed_path: feedPath,
                episodes_count: episodes.length
            };

        } catch (error) {
            this.emit('rss-creation-failed', { feedId, error });
            throw error;
        }
    }

    async generateRSSContent(podcastMetadata, episodes) {
        const {
            title,
            description,
            author,
            email,
            website,
            language = 'en-US',
            category,
            subcategory,
            explicit = false,
            artwork_url,
            copyright,
            keywords
        } = podcastMetadata;

        const rssHeader = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:googleplay="http://www.google.com/schemas/play-podcasts/1.0"
     xmlns:atom="http://www.w3.org/2005/Atom">
<channel>`;

        const channelInfo = `
    <atom:link href="${this.config.base_url}/rss/${podcastMetadata.slug || 'podcast'}.xml" rel="self" type="application/rss+xml"/>
    <title><![CDATA[${title}]]></title>
    <description><![CDATA[${description}]]></description>
    <link>${website || this.config.base_url}</link>
    <language>${language}</language>
    <copyright><![CDATA[${copyright || `© ${new Date().getFullYear()} ${author}`}]]></copyright>
    <managingEditor>${email} (${author})</managingEditor>
    <webMaster>${email} (${author})</webMaster>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <pubDate>${new Date().toUTCString()}</pubDate>
    <generator>ActiveLog Podcast Generator 1.0</generator>
    
    <itunes:type>episodic</itunes:type>
    <itunes:author>${author}</itunes:author>
    <itunes:summary><![CDATA[${description}]]></itunes:summary>
    <itunes:owner>
        <itunes:name>${author}</itunes:name>
        <itunes:email>${email}</itunes:email>
    </itunes:owner>
    <itunes:image href="${artwork_url || this.config.default_podcast_artwork}"/>
    <itunes:category text="${category}">
        ${subcategory ? `<itunes:category text="${subcategory}"/>` : ''}
    </itunes:category>
    <itunes:explicit>${explicit ? 'true' : 'false'}</itunes:explicit>
    ${keywords ? `<itunes:keywords>${keywords}</itunes:keywords>` : ''}
    
    <googleplay:author>${author}</googleplay:author>
    <googleplay:description><![CDATA[${description}]]></googleplay:description>
    <googleplay:image href="${artwork_url || this.config.default_podcast_artwork}"/>
    <googleplay:category text="${category}"/>
    <googleplay:explicit>${explicit ? 'Yes' : 'No'}</googleplay:explicit>`;

        const episodeItems = episodes.map(episode => this.generateEpisodeRSSItem(episode, podcastMetadata)).join('\n');

        const rssFooter = `
</channel>
</rss>`;

        return rssHeader + channelInfo + episodeItems + rssFooter;
    }

    generateEpisodeRSSItem(episode, podcastMetadata) {
        const {
            title,
            description,
            audio_url,
            file_size,
            duration,
            episode_number,
            season_number,
            publish_date,
            explicit = false,
            episode_type = 'full',
            transcript_url,
            chapter_markers = []
        } = episode;

        return `
    <item>
        <title><![CDATA[${title}]]></title>
        <description><![CDATA[${description}]]></description>
        <link>${audio_url}</link>
        <guid isPermaLink="false">${episode.guid || uuidv4()}</guid>
        <pubDate>${new Date(publish_date).toUTCString()}</pubDate>
        <author>${podcastMetadata.email} (${podcastMetadata.author})</author>
        
        <enclosure url="${audio_url}" length="${file_size || 0}" type="audio/mpeg"/>
        
        <itunes:title><![CDATA[${title}]]></itunes:title>
        <itunes:summary><![CDATA[${description}]]></itunes:summary>
        <itunes:author>${podcastMetadata.author}</itunes:author>
        <itunes:duration>${this.formatDuration(duration)}</itunes:duration>
        <itunes:explicit>${explicit ? 'true' : 'false'}</itunes:explicit>
        <itunes:episodeType>${episode_type}</itunes:episodeType>
        ${episode_number ? `<itunes:episode>${episode_number}</itunes:episode>` : ''}
        ${season_number ? `<itunes:season>${season_number}</itunes:season>` : ''}
        ${transcript_url ? `<podcast:transcript url="${transcript_url}" type="text/html"/>` : ''}
        
        <googleplay:description><![CDATA[${description}]]></googleplay:description>
        <googleplay:explicit>${explicit ? 'Yes' : 'No'}</googleplay:explicit>
        
        ${chapter_markers.length > 0 ? this.generateChapterMarkers(chapter_markers) : ''}
    </item>`;
    }

    generateChapterMarkers(chapters) {
        const chaptersXML = chapters.map(chapter => `
        <podcast:chapter start="${this.formatDuration(chapter.start_time)}" title="${chapter.title}">
            ${chapter.url ? `<podcast:url>${chapter.url}</podcast:url>` : ''}
            ${chapter.image ? `<podcast:img src="${chapter.image}"/>` : ''}
        </podcast:chapter>`).join('');

        return `<podcast:chapters version="1.2.0">${chaptersXML}</podcast:chapters>`;
    }

    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }

    async distributeToMultiplePlatforms(distributionRequest) {
        const taskId = uuidv4();
        
        try {
            this.emit('multi-distribution-started', { taskId });

            const {
                podcast_metadata,
                episodes,
                platforms,
                distribution_config
            } = distributionRequest;

            const distributionTask = {
                id: taskId,
                podcast_metadata: podcast_metadata,
                episodes: episodes,
                platforms: platforms,
                status: 'processing',
                started_at: new Date().toISOString(),
                results: []
            };

            this.distributionTasks.set(taskId, distributionTask);

            // Create RSS feed first
            const rssResult = await this.createRSSFeed(podcast_metadata, episodes);
            distributionTask.rss_feed = rssResult;

            // Validate against platform requirements
            const validationResults = await this.validateForPlatforms(
                podcast_metadata, 
                episodes, 
                platforms
            );

            // Submit to each platform
            for (const platformId of platforms) {
                try {
                    const platformResult = await this.submitToPlatform(
                        platformId,
                        podcast_metadata,
                        episodes,
                        rssResult,
                        distribution_config
                    );

                    distributionTask.results.push({
                        platform: platformId,
                        status: 'success',
                        result: platformResult,
                        submitted_at: new Date().toISOString()
                    });

                    this.emit('platform-submission-success', {
                        taskId,
                        platform: platformId,
                        result: platformResult
                    });

                } catch (platformError) {
                    distributionTask.results.push({
                        platform: platformId,
                        status: 'failed',
                        error: platformError.message,
                        submitted_at: new Date().toISOString()
                    });

                    this.emit('platform-submission-failed', {
                        taskId,
                        platform: platformId,
                        error: platformError
                    });
                }
            }

            distributionTask.status = 'completed';
            distributionTask.completed_at = new Date().toISOString();

            this.emit('multi-distribution-completed', {
                taskId,
                successfulPlatforms: distributionTask.results.filter(r => r.status === 'success').length,
                failedPlatforms: distributionTask.results.filter(r => r.status === 'failed').length
            });

            return {
                task_id: taskId,
                rss_feed: rssResult,
                platform_results: distributionTask.results,
                validation_results: validationResults
            };

        } catch (error) {
            const task = this.distributionTasks.get(taskId);
            if (task) {
                task.status = 'failed';
                task.error = error.message;
            }
            
            this.emit('multi-distribution-failed', { taskId, error });
            throw error;
        }
    }

    async validateForPlatforms(podcastMetadata, episodes, platforms) {
        const validationResults = {};

        for (const platformId of platforms) {
            const platform = this.distributionPlatforms.get(platformId);
            if (!platform) {
                validationResults[platformId] = {
                    valid: false,
                    errors: [`Unknown platform: ${platformId}`]
                };
                continue;
            }

            const validation = await this.validateForPlatform(podcastMetadata, episodes, platform);
            validationResults[platformId] = validation;
        }

        return validationResults;
    }

    async validateForPlatform(podcastMetadata, episodes, platform) {
        const errors = [];
        const warnings = [];
        const requirements = platform.requirements;

        // Check minimum episodes
        if (episodes.length < requirements.min_episodes) {
            errors.push(`Minimum ${requirements.min_episodes} episodes required, found ${episodes.length}`);
        }

        // Check required fields
        for (const field of requirements.required_fields) {
            if (!podcastMetadata[field]) {
                errors.push(`Required field missing: ${field}`);
            }
        }

        // Check artwork dimensions (placeholder - would need actual image analysis)
        if (requirements.artwork_size && !podcastMetadata.artwork_url) {
            warnings.push(`Recommended artwork size: ${requirements.artwork_size}`);
        }

        // Check audio format and bitrate for episodes
        episodes.forEach((episode, index) => {
            if (episode.audio_format && !requirements.audio_formats.includes(episode.audio_format)) {
                warnings.push(`Episode ${index + 1}: Recommended audio formats: ${requirements.audio_formats.join(', ')}`);
            }
        });

        return {
            valid: errors.length === 0,
            errors: errors,
            warnings: warnings,
            requirements: requirements
        };
    }

    async submitToPlatform(platformId, podcastMetadata, episodes, rssResult, config) {
        const platform = this.distributionPlatforms.get(platformId);
        
        if (!platform) {
            throw new Error(`Unknown platform: ${platformId}`);
        }

        switch (platformId) {
            case 'spotify':
                return await this.submitToSpotify(podcastMetadata, episodes, rssResult, config);
            case 'youtube':
                return await this.submitToYouTube(podcastMetadata, episodes, rssResult, config);
            case 'custom_rss':
                return await this.publishCustomRSS(podcastMetadata, episodes, rssResult, config);
            default:
                return await this.createSubmissionInstructions(platformId, rssResult, platform);
        }
    }

    async submitToSpotify(podcastMetadata, episodes, rssResult, config) {
        // This would integrate with Spotify for Podcasters API
        // For now, return submission instructions
        return {
            submission_method: 'manual',
            instructions: [
                'Visit https://podcasters.spotify.com/',
                'Create an account or log in',
                'Click "Add your podcast"',
                `Enter your RSS feed URL: ${rssResult.feed_url}`,
                'Complete the verification process'
            ],
            rss_url: rssResult.feed_url,
            status: 'pending_manual_submission'
        };
    }

    async submitToYouTube(podcastMetadata, episodes, rssResult, config) {
        // This would integrate with YouTube Data API v3
        // For now, return upload instructions
        return {
            submission_method: 'api_upload',
            instructions: [
                'Set up YouTube Data API v3 credentials',
                'Convert audio episodes to video format with static artwork',
                'Upload each episode as a separate video',
                'Use consistent naming and descriptions'
            ],
            api_endpoint: 'https://www.googleapis.com/youtube/v3/videos',
            status: 'requires_api_integration'
        };
    }

    async publishCustomRSS(podcastMetadata, episodes, rssResult, config) {
        // Custom RSS is already created, just need to make it accessible
        return {
            submission_method: 'self_hosted',
            rss_url: rssResult.feed_url,
            feed_path: rssResult.feed_path,
            instructions: [
                'Ensure your web server serves the RSS file',
                'Configure proper CORS headers if needed',
                'Test the RSS feed URL in a podcast client',
                'Submit the RSS URL to desired podcast directories'
            ],
            status: 'ready'
        };
    }

    async createSubmissionInstructions(platformId, rssResult, platform) {
        const instructions = {
            platform: platform.name,
            submission_method: platform.submission_method,
            rss_url: rssResult.feed_url,
            requires_approval: platform.requires_approval,
            instructions: []
        };

        switch (platformId) {
            case 'apple_podcasts':
                instructions.instructions = [
                    'Visit https://podcastsconnect.apple.com/',
                    'Sign in with your Apple ID',
                    'Click the "+" button to add a show',
                    `Enter your RSS feed URL: ${rssResult.feed_url}`,
                    'Complete the submission form',
                    'Wait for Apple review (typically 2-5 business days)'
                ];
                break;
            
            case 'google_podcasts':
                instructions.instructions = [
                    'Ensure your RSS feed is publicly accessible',
                    'Submit to Google Search Console',
                    'Wait for Google to automatically discover your podcast',
                    'Or visit https://podcastsmanager.google.com/'
                ];
                break;
            
            case 'amazon_music':
                instructions.instructions = [
                    'Visit https://creators.music.amazon.com/',
                    'Create an Amazon Music for Creators account',
                    'Submit your podcast for review',
                    `Provide RSS feed URL: ${rssResult.feed_url}`,
                    'Wait for approval (typically 3-7 business days)'
                ];
                break;
            
            default:
                instructions.instructions = [
                    `Visit the ${platform.name} submission page`,
                    `Submit your RSS feed URL: ${rssResult.feed_url}`,
                    'Complete any required verification steps'
                ];
        }

        return instructions;
    }

    async updateRSSFeed(feedId, newEpisodes = [], updatedMetadata = null) {
        const rssInfo = this.rssFeeds.get(feedId);
        
        if (!rssInfo) {
            throw new Error(`RSS feed not found: ${feedId}`);
        }

        // Update episodes list
        const allEpisodes = [...rssInfo.episodes, ...newEpisodes];
        
        // Update metadata if provided
        const metadata = updatedMetadata || rssInfo.podcast_metadata;
        
        // Generate updated RSS content
        const updatedRSSContent = await this.generateRSSContent(metadata, allEpisodes);
        
        // Write updated RSS file
        await fs.writeFile(rssInfo.feed_path, updatedRSSContent, 'utf8');
        
        // Update stored info
        rssInfo.episodes = allEpisodes;
        rssInfo.podcast_metadata = metadata;
        rssInfo.last_updated = new Date().toISOString();
        
        // Notify platforms of update (if they support webhooks)
        await this.notifyPlatformsOfUpdate(feedId, newEpisodes);
        
        this.emit('rss-updated', {
            feedId,
            newEpisodesCount: newEpisodes.length,
            totalEpisodes: allEpisodes.length
        });

        return {
            feed_id: feedId,
            episodes_added: newEpisodes.length,
            total_episodes: allEpisodes.length,
            feed_url: rssInfo.feed_url
        };
    }

    async notifyPlatformsOfUpdate(feedId, newEpisodes) {
        const webhookPromises = [];
        
        for (const [webhookId, webhook] of this.webhooks) {
            if (webhook.feed_id === feedId && webhook.active) {
                webhookPromises.push(this.sendWebhookNotification(webhook, {
                    event: 'episodes_added',
                    feed_id: feedId,
                    new_episodes: newEpisodes,
                    timestamp: new Date().toISOString()
                }));
            }
        }
        
        await Promise.allSettled(webhookPromises);
    }

    async sendWebhookNotification(webhook, data) {
        try {
            await axios.post(webhook.url, data, {
                headers: {
                    'Content-Type': 'application/json',
                    'User-Agent': 'ActiveLog-Podcast-Generator/1.0',
                    ...(webhook.headers || {})
                },
                timeout: 10000
            });
            
            this.emit('webhook-sent', { webhookId: webhook.id, url: webhook.url });
        } catch (error) {
            this.emit('webhook-failed', { webhookId: webhook.id, url: webhook.url, error });
        }
    }

    async setupWebhook(webhookConfig) {
        const webhookId = uuidv4();
        
        const webhook = {
            id: webhookId,
            feed_id: webhookConfig.feed_id,
            url: webhookConfig.url,
            events: webhookConfig.events || ['episodes_added'],
            headers: webhookConfig.headers || {},
            active: true,
            created_at: new Date().toISOString()
        };
        
        this.webhooks.set(webhookId, webhook);
        
        this.emit('webhook-configured', { webhookId, url: webhook.url });
        
        return webhook;
    }

    async generateAnalyticsReport(feedId, dateRange) {
        // This would integrate with platform analytics APIs
        // For now, return a placeholder structure
        const rssInfo = this.rssFeeds.get(feedId);
        
        if (!rssInfo) {
            throw new Error(`RSS feed not found: ${feedId}`);
        }

        const report = {
            feed_id: feedId,
            podcast_title: rssInfo.podcast_metadata.title,
            reporting_period: dateRange,
            generated_at: new Date().toISOString(),
            metrics: {
                total_downloads: 0, // Would fetch from platform APIs
                unique_listeners: 0,
                average_completion_rate: 0,
                geographic_distribution: {},
                platform_breakdown: {},
                episode_performance: []
            },
            growth_metrics: {
                subscriber_growth: 0,
                download_growth: 0,
                retention_rate: 0
            }
        };

        return report;
    }

    getDistributionPlatforms() {
        return Array.from(this.distributionPlatforms.values()).map(platform => ({
            id: platform.id,
            name: platform.name,
            type: platform.type,
            requires_approval: platform.requires_approval,
            supports_analytics: platform.supports_analytics,
            supports_monetization: platform.supports_monetization,
            api_available: platform.api_available
        }));
    }

    getDistributionTask(taskId) {
        return this.distributionTasks.get(taskId);
    }

    getRSSFeed(feedId) {
        return this.rssFeeds.get(feedId);
    }

    async exportDistributionReport(taskId) {
        const task = this.distributionTasks.get(taskId);
        
        if (!task) {
            throw new Error(`Distribution task not found: ${taskId}`);
        }

        const report = {
            task_id: taskId,
            podcast_title: task.podcast_metadata.title,
            distribution_summary: {
                total_platforms: task.platforms.length,
                successful_submissions: task.results.filter(r => r.status === 'success').length,
                failed_submissions: task.results.filter(r => r.status === 'failed').length,
                processing_time: task.completed_at ? 
                    (new Date(task.completed_at) - new Date(task.started_at)) / 1000 : null
            },
            rss_feed: {
                url: task.rss_feed.feed_url,
                episodes_count: task.episodes.length
            },
            platform_results: task.results,
            next_steps: task.results
                .filter(r => r.status === 'success')
                .map(r => r.result.instructions || [])
                .flat(),
            generated_at: new Date().toISOString()
        };

        const reportPath = path.join(
            this.config.distribution_configs_directory,
            `distribution_report_${taskId}.json`
        );

        await fs.writeFile(reportPath, JSON.stringify(report, null, 2), 'utf8');

        return {
            report: report,
            report_path: reportPath
        };
    }
}

export default DistributionAutomator;