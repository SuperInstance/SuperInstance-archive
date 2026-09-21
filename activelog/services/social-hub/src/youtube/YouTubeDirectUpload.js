import { EventEmitter } from 'events';
import { google } from 'googleapis';
import fs from 'fs/promises';
import path from 'path';
import ffmpeg from 'fluent-ffmpeg';
import sharp from 'sharp';
import crypto from 'crypto';
import axios from 'axios';

class YouTubeDirectUpload extends EventEmitter {
    constructor(config = {}) {
        super();
        this.uploadQueue = new Map();
        this.uploadHistory = new Map();
        this.videoTemplates = new Map();
        this.thumbnailGenerator = new Map();
        this.videoProcessor = new Map();
        this.channelSettings = new Map();
        this.uploadPresets = new Map();
        this.analytics = new Map();

        // YouTube API configuration
        this.credentials = {
            client_id: config.client_id || process.env.YOUTUBE_CLIENT_ID,
            client_secret: config.client_secret || process.env.YOUTUBE_CLIENT_SECRET,
            redirect_uri: config.redirect_uri || 'http://localhost:8383/auth/youtube/callback',
            refresh_token: config.refresh_token || process.env.YOUTUBE_REFRESH_TOKEN
        };

        this.initializeSystem();
    }

    async initializeSystem() {
        try {
            await this.initializeYouTubeAPI();
            this.initializeVideoTemplates();
            this.initializeUploadPresets();
            this.initializeThumbnailTemplates();
            
            this.emit('youtube_upload_system_initialized');
        } catch (error) {
            this.emit('youtube_initialization_error', error);
        }
    }

    async initializeYouTubeAPI() {
        this.oauth2Client = new google.auth.OAuth2(
            this.credentials.client_id,
            this.credentials.client_secret,
            this.credentials.redirect_uri
        );

        if (this.credentials.refresh_token) {
            this.oauth2Client.setCredentials({
                refresh_token: this.credentials.refresh_token
            });

            try {
                // Test the connection
                const youtube = google.youtube({
                    version: 'v3',
                    auth: this.oauth2Client
                });

                const channelResponse = await youtube.channels.list({
                    part: 'snippet,statistics,contentDetails,brandingSettings',
                    mine: true
                });

                if (channelResponse.data.items.length > 0) {
                    this.channelInfo = channelResponse.data.items[0];
                    this.channelId = this.channelInfo.id;
                    
                    this.emit('youtube_authenticated', {
                        channel_id: this.channelId,
                        channel_name: this.channelInfo.snippet.title
                    });
                }

            } catch (error) {
                this.emit('youtube_auth_error', error);
                throw error;
            }
        }

        this.youtube = google.youtube({
            version: 'v3',
            auth: this.oauth2Client
        });
    }

    initializeVideoTemplates() {
        const templates = [
            {
                id: 'product_showcase',
                name: 'Product Showcase',
                description_template: `{product_name} - Complete Overview & Demo

🚀 In this video, we'll explore {product_name}, an innovative {product_category} that's changing how we approach {use_case}.

📋 What you'll learn:
• Product overview and key features
• Live demonstration
• Real-world applications
• Setup and configuration
• Performance insights

🔗 Links:
• Product page: {product_url}
• Documentation: {docs_url}
• ActiveLog: https://activelog.com

⏰ Timestamps:
0:00 Introduction
{timestamps}

💡 About {product_name}:
{detailed_description}

🎯 Perfect for:
{target_audience}

❓ Questions? Drop them in the comments below!

👍 Like this video if you found it helpful
🔔 Subscribe for more tech reviews and demos
📢 Share with fellow makers and developers

#{product_category} #TechReview #Innovation #ActiveLog #OpenSource`,
                thumbnail_style: 'product_focus',
                default_tags: ['tech', 'innovation', 'product review', 'demo', 'activelog'],
                category_id: '28', // Science & Technology
                default_privacy: 'public',
                variables: ['product_name', 'product_category', 'use_case', 'product_url', 'docs_url', 'detailed_description', 'target_audience', 'timestamps']
            },
            {
                id: 'tutorial',
                name: 'Tutorial/How-to',
                description_template: `How to {tutorial_topic} - Step by Step Guide

📚 Complete tutorial covering {tutorial_topic} from beginner to advanced level.

🎯 What you'll master:
{learning_objectives}

🛠️ Requirements:
{requirements}

📁 Resources:
• Code/files: {resources_url}
• Documentation: {docs_url}
• ActiveLog: https://activelog.com

⏰ Chapters:
{timestamps}

🔧 Step-by-step process:
{steps_overview}

💡 Pro tips and best practices included throughout!

🤔 Stuck? Check the comments - I respond to every question!

👍 Smash that like button if this helped you
🔔 Subscribe for weekly tutorials
📤 Share with your developer friends

#Tutorial #HowTo #Programming #Development #ActiveLog #TechEducation`,
                thumbnail_style: 'tutorial_steps',
                default_tags: ['tutorial', 'how-to', 'programming', 'development', 'education'],
                category_id: '27', // Education
                default_privacy: 'public',
                variables: ['tutorial_topic', 'learning_objectives', 'requirements', 'resources_url', 'docs_url', 'timestamps', 'steps_overview']
            },
            {
                id: 'project_walkthrough',
                name: 'Project Walkthrough',
                description_template: `{project_name} - Full Project Breakdown & Code Review

🏗️ Deep dive into {project_name}, a {project_type} built with {tech_stack}.

🎯 Project Overview:
{project_description}

✨ Key Features:
{key_features}

🔧 Tech Stack:
{tech_stack_details}

📂 Project Structure:
{project_structure}

⏰ Timeline:
{timestamps}

💻 Code Highlights:
{code_highlights}

🚀 Deployment & Live Demo:
{deployment_info}

📚 What I learned:
{lessons_learned}

🔗 Resources:
• GitHub: {github_url}
• Live Demo: {demo_url}
• Blog Post: {blog_url}
• ActiveLog: https://activelog.com

💭 What would you build differently? Let me know in the comments!

👍 Like if you enjoyed this project breakdown
🔔 Subscribe for more project walkthroughs
⭐ Star the repo if you found it useful

#ProjectWalkthrough #CodeReview #Development #Programming #ActiveLog #OpenSource`,
                thumbnail_style: 'project_showcase',
                default_tags: ['project', 'code review', 'development', 'programming', 'walkthrough'],
                category_id: '28', // Science & Technology
                default_privacy: 'public',
                variables: ['project_name', 'project_type', 'tech_stack', 'project_description', 'key_features', 'tech_stack_details', 'project_structure', 'timestamps', 'code_highlights', 'deployment_info', 'lessons_learned', 'github_url', 'demo_url', 'blog_url']
            },
            {
                id: 'livestream_archive',
                name: 'Livestream Archive',
                description_template: `🔴 LIVESTREAM ARCHIVE: {stream_title}

📅 Originally streamed: {stream_date}
⏰ Duration: {duration}

🎯 In this stream:
{stream_highlights}

⏰ Key Moments:
{timestamps}

💬 Chat Highlights:
{chat_highlights}

🔗 Mentioned Resources:
{resources_mentioned}

📱 Follow for live streams:
• Twitch: {twitch_url}
• YouTube Live: {youtube_live_url}
• Twitter: {twitter_url}

🗓️ Next stream: {next_stream}

👥 Thanks to everyone who joined live!

🔔 Turn on notifications to catch future streams
💬 Join our Discord: {discord_url}
🌟 Support on Patreon: {patreon_url}

#Livestream #Programming #Development #Coding #ActiveLog #TechStream`,
                thumbnail_style: 'livestream_archive',
                default_tags: ['livestream', 'programming', 'development', 'coding', 'stream'],
                category_id: '20', // Gaming (closest for livestreams)
                default_privacy: 'public',
                variables: ['stream_title', 'stream_date', 'duration', 'stream_highlights', 'timestamps', 'chat_highlights', 'resources_mentioned', 'twitch_url', 'youtube_live_url', 'twitter_url', 'next_stream', 'discord_url', 'patreon_url']
            },
            {
                id: 'community_highlight',
                name: 'Community Highlight',
                description_template: `Community Spotlight: {creator_name} - {project_title}

👨‍💻 Featuring amazing work by {creator_name} from our ActiveLog community!

🚀 Project: {project_title}
📋 Category: {project_category}

✨ What makes this special:
{project_highlights}

🔧 Technical Details:
{technical_details}

💡 Creative Solutions:
{creative_solutions}

🎯 Impact:
{project_impact}

👨‍💻 About the Creator:
{creator_bio}

🔗 Check it out:
• Project: {project_url}
• Creator's Profile: {creator_profile}
• GitHub: {github_url}

💬 Leave some love for {creator_name} in the comments!

🌟 Want to be featured?
• Share your projects on ActiveLog
• Tag us in your posts
• Join our community challenges

#CommunitySpotlight #MakerCommunity #Innovation #ActiveLog #Featured #OpenSource`,
                thumbnail_style: 'community_feature',
                default_tags: ['community', 'spotlight', 'maker', 'innovation', 'featured'],
                category_id: '28', // Science & Technology
                default_privacy: 'public',
                variables: ['creator_name', 'project_title', 'project_category', 'project_highlights', 'technical_details', 'creative_solutions', 'project_impact', 'creator_bio', 'project_url', 'creator_profile', 'github_url']
            }
        ];

        templates.forEach(template => {
            this.videoTemplates.set(template.id, template);
        });
    }

    initializeUploadPresets() {
        const presets = [
            {
                id: 'high_quality',
                name: 'High Quality Upload',
                video_settings: {
                    resolution: '1080p',
                    framerate: 30,
                    bitrate: '5000k',
                    audio_bitrate: '192k',
                    codec: 'h264'
                },
                processing_options: {
                    stabilization: true,
                    noise_reduction: true,
                    color_correction: 'auto',
                    audio_enhancement: true
                },
                upload_options: {
                    privacy_status: 'public',
                    notify_subscribers: true,
                    made_for_kids: false,
                    category_id: '28'
                }
            },
            {
                id: 'quick_upload',
                name: 'Quick Upload',
                video_settings: {
                    resolution: '720p',
                    framerate: 30,
                    bitrate: '2500k',
                    audio_bitrate: '128k',
                    codec: 'h264'
                },
                processing_options: {
                    stabilization: false,
                    noise_reduction: false,
                    color_correction: 'none',
                    audio_enhancement: false
                },
                upload_options: {
                    privacy_status: 'unlisted',
                    notify_subscribers: false,
                    made_for_kids: false,
                    category_id: '28'
                }
            },
            {
                id: 'livestream_archive',
                name: 'Livestream Archive',
                video_settings: {
                    resolution: '1080p',
                    framerate: 30,
                    bitrate: '4000k',
                    audio_bitrate: '192k',
                    codec: 'h264'
                },
                processing_options: {
                    stabilization: false,
                    noise_reduction: true,
                    color_correction: 'auto',
                    audio_enhancement: true
                },
                upload_options: {
                    privacy_status: 'public',
                    notify_subscribers: false,
                    made_for_kids: false,
                    category_id: '20',
                    enable_premiere: false
                }
            }
        ];

        presets.forEach(preset => {
            this.uploadPresets.set(preset.id, preset);
        });
    }

    initializeThumbnailTemplates() {
        const thumbnailTemplates = [
            {
                id: 'product_focus',
                name: 'Product Focus',
                layout: 'centered_product',
                elements: {
                    background: 'gradient_tech',
                    title_position: 'bottom_third',
                    logo_position: 'top_right',
                    accent_color: '#FF6B35',
                    font_family: 'Roboto Bold'
                }
            },
            {
                id: 'tutorial_steps',
                name: 'Tutorial Steps',
                layout: 'step_by_step',
                elements: {
                    background: 'code_pattern',
                    title_position: 'left_side',
                    step_indicators: 'numbered_circles',
                    accent_color: '#4ECDC4',
                    font_family: 'Open Sans Bold'
                }
            },
            {
                id: 'project_showcase',
                name: 'Project Showcase',
                layout: 'split_screen',
                elements: {
                    background: 'dark_tech',
                    title_position: 'center_top',
                    code_preview: 'right_side',
                    accent_color: '#45B7D1',
                    font_family: 'Montserrat Bold'
                }
            },
            {
                id: 'community_feature',
                name: 'Community Feature',
                layout: 'creator_spotlight',
                elements: {
                    background: 'community_gradient',
                    creator_photo: 'left_circle',
                    title_position: 'center_bottom',
                    accent_color: '#96CEB4',
                    font_family: 'Poppins Bold'
                }
            }
        ];

        thumbnailTemplates.forEach(template => {
            this.thumbnailGenerator.set(template.id, template);
        });
    }

    // Main upload methods
    async uploadVideo(videoData) {
        try {
            const uploadId = crypto.randomBytes(16).toString('hex');
            
            // Add to queue
            const queueItem = {
                id: uploadId,
                status: 'preparing',
                created_at: new Date(),
                video_data: videoData,
                processing_steps: [],
                upload_progress: 0
            };
            
            this.uploadQueue.set(uploadId, queueItem);
            this.emit('upload_queued', { upload_id: uploadId });

            // Process the upload
            const result = await this.processVideoUpload(uploadId);
            return result;

        } catch (error) {
            this.emit('upload_error', { videoData, error });
            return { success: false, error: error.message };
        }
    }

    async processVideoUpload(uploadId) {
        const queueItem = this.uploadQueue.get(uploadId);
        if (!queueItem) {
            return { success: false, error: 'Upload not found in queue' };
        }

        try {
            // Step 1: Validate and prepare video
            queueItem.status = 'validating';
            this.updateQueueItem(uploadId, queueItem);
            
            const validation = await this.validateVideoFile(queueItem.video_data);
            if (!validation.valid) {
                throw new Error(`Video validation failed: ${validation.error}`);
            }

            // Step 2: Process video if needed
            queueItem.status = 'processing';
            this.updateQueueItem(uploadId, queueItem);
            
            const processedVideo = await this.processVideo(queueItem.video_data, uploadId);

            // Step 3: Generate thumbnail
            queueItem.status = 'generating_thumbnail';
            this.updateQueueItem(uploadId, queueItem);
            
            const thumbnail = await this.generateThumbnail(processedVideo, queueItem.video_data);

            // Step 4: Prepare metadata
            const metadata = await this.prepareMetadata(queueItem.video_data);

            // Step 5: Upload to YouTube
            queueItem.status = 'uploading';
            this.updateQueueItem(uploadId, queueItem);
            
            const uploadResult = await this.uploadToYouTube(processedVideo, metadata, thumbnail, uploadId);

            if (uploadResult.success) {
                queueItem.status = 'completed';
                queueItem.youtube_video_id = uploadResult.video_id;
                queueItem.youtube_url = `https://www.youtube.com/watch?v=${uploadResult.video_id}`;
                queueItem.completed_at = new Date();
            } else {
                queueItem.status = 'failed';
                queueItem.error = uploadResult.error;
            }

            this.updateQueueItem(uploadId, queueItem);
            
            // Move to history
            this.uploadHistory.set(uploadId, { ...queueItem });
            this.uploadQueue.delete(uploadId);

            this.emit('upload_completed', {
                upload_id: uploadId,
                success: uploadResult.success,
                video_id: uploadResult.video_id,
                url: queueItem.youtube_url
            });

            return {
                success: uploadResult.success,
                upload_id: uploadId,
                video_id: uploadResult.video_id,
                url: queueItem.youtube_url,
                error: uploadResult.error
            };

        } catch (error) {
            queueItem.status = 'failed';
            queueItem.error = error.message;
            this.updateQueueItem(uploadId, queueItem);
            
            this.emit('upload_failed', { upload_id: uploadId, error });
            return { success: false, error: error.message };
        }
    }

    async validateVideoFile(videoData) {
        try {
            if (!videoData.file_path && !videoData.file_buffer) {
                return { valid: false, error: 'No video file provided' };
            }

            // Check file size (YouTube limit is 256GB, but we'll be more conservative)
            const maxSize = 50 * 1024 * 1024 * 1024; // 50GB
            if (videoData.file_size && videoData.file_size > maxSize) {
                return { valid: false, error: 'Video file too large (max 50GB)' };
            }

            // Check video format
            const supportedFormats = ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.webm', '.m4v'];
            const fileExtension = path.extname(videoData.file_path || videoData.filename || '').toLowerCase();
            
            if (!supportedFormats.includes(fileExtension)) {
                return { valid: false, error: `Unsupported format: ${fileExtension}` };
            }

            // If file path provided, check if file exists
            if (videoData.file_path) {
                try {
                    await fs.access(videoData.file_path);
                } catch {
                    return { valid: false, error: 'Video file not found' };
                }
            }

            return { valid: true };

        } catch (error) {
            return { valid: false, error: error.message };
        }
    }

    async processVideo(videoData, uploadId) {
        try {
            const preset = this.uploadPresets.get(videoData.upload_preset || 'high_quality');
            const inputPath = videoData.file_path;
            const outputPath = `/tmp/processed_${uploadId}.mp4`;

            await new Promise((resolve, reject) => {
                let command = ffmpeg(inputPath);

                // Apply video settings
                if (preset.video_settings.resolution) {
                    const height = preset.video_settings.resolution === '1080p' ? 1080 : 720;
                    command = command.size(`?x${height}`);
                }

                command = command
                    .videoBitrate(preset.video_settings.bitrate)
                    .audioBitrate(preset.video_settings.audio_bitrate)
                    .videoCodec('libx264')
                    .audioCodec('aac')
                    .format('mp4');

                // Apply processing options
                if (preset.processing_options.stabilization) {
                    command = command.videoFilters('deshake');
                }

                if (preset.processing_options.noise_reduction) {
                    command = command.audioFilters('afftdn');
                }

                command
                    .on('progress', (progress) => {
                        const queueItem = this.uploadQueue.get(uploadId);
                        queueItem.processing_progress = progress.percent;
                        this.updateQueueItem(uploadId, queueItem);
                    })
                    .on('end', () => resolve())
                    .on('error', (err) => reject(err))
                    .save(outputPath);
            });

            return {
                ...videoData,
                processed_file_path: outputPath,
                original_file_path: videoData.file_path
            };

        } catch (error) {
            // If processing fails, use original file
            return videoData;
        }
    }

    async generateThumbnail(videoData, originalData) {
        try {
            const thumbnailStyle = originalData.thumbnail_style || 'product_focus';
            const template = this.thumbnailGenerator.get(thumbnailStyle);
            
            if (!template) {
                // Generate simple thumbnail from video frame
                return await this.generateSimpleThumbnail(videoData);
            }

            // Generate custom thumbnail based on template
            return await this.generateCustomThumbnail(videoData, originalData, template);

        } catch (error) {
            this.emit('thumbnail_generation_error', { videoData, error });
            return null;
        }
    }

    async generateSimpleThumbnail(videoData) {
        return new Promise((resolve, reject) => {
            const inputPath = videoData.processed_file_path || videoData.file_path;
            const outputPath = `/tmp/thumbnail_${crypto.randomBytes(8).toString('hex')}.jpg`;

            ffmpeg(inputPath)
                .screenshots({
                    count: 1,
                    folder: '/tmp',
                    filename: path.basename(outputPath),
                    timemarks: ['50%'] // Take screenshot at 50% of video duration
                })
                .on('end', () => resolve(outputPath))
                .on('error', (err) => reject(err));
        });
    }

    async generateCustomThumbnail(videoData, originalData, template) {
        try {
            // This would generate custom thumbnails using Canvas or Sharp
            // For now, returning a simple implementation
            const thumbnailPath = await this.generateSimpleThumbnail(videoData);
            
            // Apply template styling using Sharp
            const styledThumbnail = `/tmp/styled_thumbnail_${crypto.randomBytes(8).toString('hex')}.jpg`;
            
            await sharp(thumbnailPath)
                .resize(1280, 720)
                .jpeg({ quality: 95 })
                .toFile(styledThumbnail);

            return styledThumbnail;

        } catch (error) {
            return await this.generateSimpleThumbnail(videoData);
        }
    }

    async prepareMetadata(videoData) {
        try {
            const template = this.videoTemplates.get(videoData.template_id || 'product_showcase');
            
            let title = videoData.title;
            let description = videoData.description;

            // If template provided, fill it with data
            if (template && videoData.template_variables) {
                description = this.fillTemplate(template.description_template, videoData.template_variables);
                
                if (!title && videoData.template_variables.product_name) {
                    title = `${videoData.template_variables.product_name} - ${template.name}`;
                }
            }

            // Ensure title is within YouTube's limits
            if (title && title.length > 100) {
                title = title.substring(0, 97) + '...';
            }

            // Prepare tags
            let tags = videoData.tags || [];
            if (template && template.default_tags) {
                tags = [...new Set([...tags, ...template.default_tags])];
            }
            tags = tags.slice(0, 500).join(','); // YouTube limit

            const metadata = {
                snippet: {
                    title: title || 'Untitled Video',
                    description: description || '',
                    tags: tags ? tags.split(',') : [],
                    categoryId: videoData.category_id || template?.category_id || '28',
                    defaultLanguage: videoData.language || 'en',
                    defaultAudioLanguage: videoData.audio_language || 'en'
                },
                status: {
                    privacyStatus: videoData.privacy_status || template?.default_privacy || 'public',
                    selfDeclaredMadeForKids: videoData.made_for_kids || false,
                    embeddable: videoData.embeddable !== false,
                    publicStatsViewable: videoData.public_stats !== false
                }
            };

            // Add optional fields
            if (videoData.playlist_id) {
                metadata.snippet.playlistId = videoData.playlist_id;
            }

            if (videoData.scheduled_publish_time) {
                metadata.status.publishAt = new Date(videoData.scheduled_publish_time).toISOString();
                metadata.status.privacyStatus = 'private'; // Must be private for scheduled videos
            }

            if (videoData.notify_subscribers !== undefined) {
                metadata.status.notifySubscribers = videoData.notify_subscribers;
            }

            return metadata;

        } catch (error) {
            throw new Error(`Metadata preparation failed: ${error.message}`);
        }
    }

    async uploadToYouTube(videoData, metadata, thumbnailPath, uploadId) {
        try {
            const filePath = videoData.processed_file_path || videoData.file_path;
            const fileStats = await fs.stat(filePath);
            
            // Create the upload request
            const response = await this.youtube.videos.insert({
                part: 'snippet,status',
                requestBody: metadata,
                media: {
                    body: require('fs').createReadStream(filePath)
                }
            });

            const videoId = response.data.id;

            // Upload custom thumbnail if available
            if (thumbnailPath) {
                try {
                    await this.youtube.thumbnails.set({
                        videoId: videoId,
                        media: {
                            body: require('fs').createReadStream(thumbnailPath)
                        }
                    });
                } catch (thumbnailError) {
                    this.emit('thumbnail_upload_error', { videoId, error: thumbnailError });
                }
            }

            // Add to playlist if specified
            if (videoData.playlist_id) {
                try {
                    await this.youtube.playlistItems.insert({
                        part: 'snippet',
                        requestBody: {
                            snippet: {
                                playlistId: videoData.playlist_id,
                                resourceId: {
                                    kind: 'youtube#video',
                                    videoId: videoId
                                }
                            }
                        }
                    });
                } catch (playlistError) {
                    this.emit('playlist_add_error', { videoId, playlistId: videoData.playlist_id, error: playlistError });
                }
            }

            return {
                success: true,
                video_id: videoId,
                video_url: `https://www.youtube.com/watch?v=${videoId}`,
                upload_response: response.data
            };

        } catch (error) {
            return {
                success: false,
                error: error.message,
                youtube_error: error.response?.data
            };
        }
    }

    fillTemplate(template, variables) {
        let filled = template;
        
        Object.entries(variables).forEach(([key, value]) => {
            const regex = new RegExp(`{${key}}`, 'g');
            filled = filled.replace(regex, value || '');
        });

        return filled.trim();
    }

    updateQueueItem(uploadId, queueItem) {
        this.uploadQueue.set(uploadId, queueItem);
        this.emit('upload_progress', {
            upload_id: uploadId,
            status: queueItem.status,
            progress: queueItem.upload_progress || 0
        });
    }

    // Batch upload methods
    async uploadVideoSeries(seriesData) {
        try {
            const seriesId = crypto.randomBytes(16).toString('hex');
            const uploads = [];

            // Create playlist for series if needed
            let playlistId = seriesData.playlist_id;
            if (!playlistId && seriesData.create_playlist) {
                playlistId = await this.createPlaylist(seriesData.playlist_info);
            }

            // Queue all videos in the series
            for (const videoData of seriesData.videos) {
                const uploadData = {
                    ...videoData,
                    playlist_id: playlistId,
                    series_id: seriesId,
                    notify_subscribers: videoData.notify_subscribers ?? (uploads.length === 0) // Only notify for first video
                };

                const result = await this.uploadVideo(uploadData);
                uploads.push(result);

                // Add delay between uploads to avoid rate limits
                if (uploads.length < seriesData.videos.length) {
                    await new Promise(resolve => setTimeout(resolve, 30000)); // 30 second delay
                }
            }

            return {
                success: true,
                series_id: seriesId,
                playlist_id: playlistId,
                uploads: uploads,
                successful_uploads: uploads.filter(u => u.success).length,
                total_videos: uploads.length
            };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async createPlaylist(playlistInfo) {
        try {
            const response = await this.youtube.playlists.insert({
                part: 'snippet,status',
                requestBody: {
                    snippet: {
                        title: playlistInfo.title,
                        description: playlistInfo.description || '',
                        defaultLanguage: playlistInfo.language || 'en'
                    },
                    status: {
                        privacyStatus: playlistInfo.privacy_status || 'public'
                    }
                }
            });

            return response.data.id;

        } catch (error) {
            this.emit('playlist_creation_error', error);
            return null;
        }
    }

    // Shorts-specific methods
    async uploadShort(shortData) {
        // YouTube Shorts are videos under 60 seconds in vertical format
        const shortsMetadata = {
            ...shortData,
            title: shortData.title + ' #Shorts',
            tags: [...(shortData.tags || []), 'shorts', 'youtubeshorts'],
            template_id: shortData.template_id || 'short_form'
        };

        return await this.uploadVideo(shortsMetadata);
    }

    // Live stream methods
    async createLiveStream(streamData) {
        try {
            // Create live stream
            const streamResponse = await this.youtube.liveStreams.insert({
                part: 'snippet,cdn,status',
                requestBody: {
                    snippet: {
                        title: streamData.stream_title || 'Live Stream'
                    },
                    cdn: {
                        format: '1080p',
                        ingestionType: 'rtmp'
                    },
                    status: {
                        streamStatus: 'created'
                    }
                }
            });

            // Create live broadcast
            const broadcastResponse = await this.youtube.liveBroadcasts.insert({
                part: 'snippet,status,contentDetails',
                requestBody: {
                    snippet: {
                        title: streamData.title,
                        description: streamData.description || '',
                        scheduledStartTime: streamData.scheduled_start_time
                    },
                    status: {
                        privacyStatus: streamData.privacy_status || 'public',
                        selfDeclaredMadeForKids: false
                    },
                    contentDetails: {
                        enableAutoStart: true,
                        enableAutoStop: true
                    }
                }
            });

            // Bind stream to broadcast
            await this.youtube.liveBroadcasts.bind({
                part: 'id',
                id: broadcastResponse.data.id,
                streamId: streamResponse.data.id
            });

            return {
                success: true,
                broadcast_id: broadcastResponse.data.id,
                stream_id: streamResponse.data.id,
                stream_key: streamResponse.data.cdn.ingestionInfo.streamName,
                rtmp_url: streamResponse.data.cdn.ingestionInfo.ingestionAddress,
                watch_url: `https://www.youtube.com/watch?v=${broadcastResponse.data.id}`
            };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // Analytics and management
    async getUploadStats(timeframe = '7d') {
        const now = new Date();
        const cutoff = new Date(now.getTime() - (timeframe === '7d' ? 7 : 30) * 24 * 60 * 60 * 1000);
        
        const recentUploads = Array.from(this.uploadHistory.values())
            .filter(upload => upload.created_at >= cutoff);

        return {
            total_uploads: recentUploads.length,
            successful_uploads: recentUploads.filter(u => u.status === 'completed').length,
            failed_uploads: recentUploads.filter(u => u.status === 'failed').length,
            total_duration: recentUploads.reduce((sum, u) => sum + (u.video_data.duration || 0), 0),
            average_processing_time: this.calculateAverageProcessingTime(recentUploads),
            template_usage: this.getTemplateUsageStats(recentUploads),
            pending_uploads: this.uploadQueue.size
        };
    }

    calculateAverageProcessingTime(uploads) {
        const completedUploads = uploads.filter(u => u.status === 'completed' && u.completed_at);
        if (completedUploads.length === 0) return 0;

        const totalTime = completedUploads.reduce((sum, u) => {
            return sum + (new Date(u.completed_at) - new Date(u.created_at));
        }, 0);

        return Math.round(totalTime / completedUploads.length / 1000 / 60); // Minutes
    }

    getTemplateUsageStats(uploads) {
        const usage = {};
        uploads.forEach(upload => {
            const templateId = upload.video_data.template_id || 'none';
            usage[templateId] = (usage[templateId] || 0) + 1;
        });
        return usage;
    }

    async getChannelAnalytics() {
        try {
            const analytics = google.youtubeAnalytics({
                version: 'v2',
                auth: this.oauth2Client
            });

            const endDate = new Date().toISOString().split('T')[0];
            const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

            const response = await analytics.reports.query({
                ids: `channel==${this.channelId}`,
                startDate: startDate,
                endDate: endDate,
                metrics: 'views,estimatedMinutesWatched,averageViewDuration,subscribersGained',
                dimensions: 'day'
            });

            return {
                success: true,
                data: response.data,
                period: { start: startDate, end: endDate }
            };

        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // Queue management
    getQueueStatus() {
        const queueArray = Array.from(this.uploadQueue.values());
        
        return {
            total_queued: queueArray.length,
            preparing: queueArray.filter(q => q.status === 'preparing').length,
            processing: queueArray.filter(q => q.status === 'processing').length,
            uploading: queueArray.filter(q => q.status === 'uploading').length,
            failed: queueArray.filter(q => q.status === 'failed').length,
            estimated_completion: this.estimateQueueCompletion()
        };
    }

    estimateQueueCompletion() {
        const queueArray = Array.from(this.uploadQueue.values());
        const processingTime = 5; // Average minutes per video
        
        return new Date(Date.now() + queueArray.length * processingTime * 60 * 1000);
    }

    // Configuration management
    addVideoTemplate(template) {
        const templateId = template.id || crypto.randomBytes(16).toString('hex');
        this.videoTemplates.set(templateId, { ...template, id: templateId });
        
        this.emit('template_added', templateId);
        return { success: true, template_id: templateId };
    }

    updateUploadPreset(presetId, updates) {
        if (this.uploadPresets.has(presetId)) {
            const currentPreset = this.uploadPresets.get(presetId);
            const updatedPreset = { ...currentPreset, ...updates };
            this.uploadPresets.set(presetId, updatedPreset);
            
            this.emit('preset_updated', presetId);
            return { success: true };
        }
        
        return { success: false, error: 'Preset not found' };
    }
}

export default YouTubeDirectUpload;