import { EventEmitter } from 'events';
import OpenAI from 'openai';
import fs from 'fs/promises';
import path from 'path';
import ffmpeg from 'fluent-ffmpeg';
import ffmpegStatic from 'ffmpeg-static';
import { v4 as uuidv4 } from 'uuid';

// Set ffmpeg path
ffmpeg.setFfmpegPath(ffmpegStatic);

class IntroOutroAutomator extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            openai_api_key: config.openai_api_key || process.env.OPENAI_API_KEY,
            model: config.model || 'gpt-4',
            templates_directory: config.templates_directory || './data/intro_outro_templates',
            audio_assets_directory: config.audio_assets_directory || './assets/audio',
            output_directory: config.output_directory || './output/intro_outro',
            default_music_path: config.default_music_path || './assets/audio/default_intro_music.mp3',
            default_voice_profile: config.default_voice_profile || 'host_male_professional',
            ...config
        };

        this.openai = new OpenAI({
            apiKey: this.config.openai_api_key
        });

        this.introTemplates = new Map();
        this.outroTemplates = new Map();
        this.brandingElements = new Map();
        this.generatedIntros = new Map();
        this.generatedOutros = new Map();

        this.initializeTemplates();
        this.initializeBrandingElements();
        this.ensureDirectories();
    }

    async ensureDirectories() {
        try {
            await fs.mkdir(this.config.templates_directory, { recursive: true });
            await fs.mkdir(this.config.audio_assets_directory, { recursive: true });
            await fs.mkdir(this.config.output_directory, { recursive: true });
        } catch (error) {
            this.emit('error', { type: 'directory-creation', error });
        }
    }

    initializeTemplates() {
        // Professional Intro Templates
        this.introTemplates.set('professional_standard', {
            id: 'professional_standard',
            name: 'Professional Standard',
            category: 'professional',
            structure: {
                opening_hook: 'attention_grabber',
                podcast_branding: 'title_and_tagline',
                episode_introduction: 'episode_preview',
                host_introduction: 'host_credentials',
                content_preview: 'episode_outline'
            },
            duration_target: 45, // seconds
            tone: 'professional',
            energy_level: 'moderate',
            template_text: `{opening_hook}

Welcome to {podcast_title} - {podcast_tagline}.

I'm your host, {host_name}, {host_credentials}.

In today's episode, "{episode_title}", we'll be {episode_preview}.

{content_preview}

Let's dive in.`,
            voice_direction: {
                pace: 'moderate',
                emphasis_points: ['podcast_title', 'episode_title'],
                tone_progression: 'welcoming_to_informative'
            }
        });

        this.introTemplates.set('conversational_friendly', {
            id: 'conversational_friendly',
            name: 'Conversational Friendly',
            category: 'casual',
            structure: {
                greeting: 'warm_welcome',
                personal_connection: 'host_check_in',
                episode_excitement: 'enthusiasm_builder',
                content_tease: 'curiosity_hook'
            },
            duration_target: 30,
            tone: 'friendly',
            energy_level: 'high',
            template_text: `Hey there, and welcome back to {podcast_title}! 

{personal_greeting} I'm {host_name}, and I am so excited to share today's episode with you.

We're talking about {episode_topic}, and trust me, {enthusiasm_hook}.

{content_tease}

So grab your coffee, get comfortable, and let's get into it!`,
            voice_direction: {
                pace: 'energetic',
                emphasis_points: ['episode_topic', 'enthusiasm_hook'],
                tone_progression: 'excited_throughout'
            }
        });

        this.introTemplates.set('educational_expert', {
            id: 'educational_expert',
            name: 'Educational Expert',
            category: 'educational',
            structure: {
                authority_establishment: 'credentials_highlight',
                learning_objective: 'episode_goals',
                context_setting: 'background_info',
                methodology_preview: 'approach_explanation'
            },
            duration_target: 60,
            tone: 'authoritative',
            energy_level: 'moderate',
            template_text: `This is {podcast_title}, the podcast where {podcast_mission}.

I'm {host_name}, {host_expertise}.

Today's episode focuses on {learning_objective}. We'll explore {key_concepts}, examine {case_studies}, and by the end, you'll {expected_outcome}.

{methodology_preview}

Let's begin with the fundamentals.`,
            voice_direction: {
                pace: 'measured',
                emphasis_points: ['learning_objective', 'expected_outcome'],
                tone_progression: 'authoritative_to_engaging'
            }
        });

        this.introTemplates.set('storytelling_narrative', {
            id: 'storytelling_narrative',
            name: 'Storytelling Narrative',
            category: 'narrative',
            structure: {
                scene_setting: 'atmospheric_opening',
                intrigue_builder: 'mystery_hook',
                story_preview: 'narrative_tease',
                guide_introduction: 'storyteller_role'
            },
            duration_target: 50,
            tone: 'mysterious',
            energy_level: 'variable',
            template_text: `{atmospheric_opening}

{mystery_hook}

Welcome to {podcast_title}, where {podcast_concept}.

I'm {host_name}, your guide through {story_world}.

Today's story: {episode_title}. {narrative_tease}

{story_preview}

Our story begins...`,
            voice_direction: {
                pace: 'dramatic',
                emphasis_points: ['mystery_hook', 'episode_title'],
                tone_progression: 'mysterious_to_engaging'
            }
        });

        this.introTemplates.set('news_format', {
            id: 'news_format',
            name: 'News Format',
            category: 'informational',
            structure: {
                headline: 'breaking_news_style',
                date_location: 'timestamp',
                key_stories: 'episode_agenda',
                credibility: 'source_information'
            },
            duration_target: 35,
            tone: 'professional',
            energy_level: 'moderate',
            template_text: `Good {time_of_day}, I'm {host_name}, and this is {podcast_title}.

Today is {current_date}, and here's what we're covering:

{headline_stories}

{source_credibility}

Let's start with our top story.`,
            voice_direction: {
                pace: 'news_anchor',
                emphasis_points: ['headline_stories', 'current_date'],
                tone_progression: 'authoritative_consistent'
            }
        });

        this.introTemplates.set('comedy_entertainment', {
            id: 'comedy_entertainment',
            name: 'Comedy Entertainment',
            category: 'entertainment',
            structure: {
                comedy_hook: 'opening_joke',
                self_deprecation: 'host_humor',
                audience_connection: 'shared_experience',
                episode_tease: 'funny_preview'
            },
            duration_target: 40,
            tone: 'humorous',
            energy_level: 'high',
            template_text: `{opening_joke}

What's up everyone, and welcome to {podcast_title}! I'm {host_name}, {self_deprecating_intro}.

{audience_connection}

Today we're diving into {episode_topic}, and {funny_preview}.

{comedy_setup}

Alright, let's get weird!`,
            voice_direction: {
                pace: 'comedic_timing',
                emphasis_points: ['opening_joke', 'funny_preview'],
                tone_progression: 'playful_throughout'
            }
        });

        // Outro Templates
        this.outroTemplates.set('professional_standard', {
            id: 'professional_standard',
            name: 'Professional Standard',
            category: 'professional',
            structure: {
                episode_recap: 'key_takeaways',
                call_to_action: 'next_steps',
                engagement_request: 'social_media',
                next_episode_tease: 'upcoming_preview',
                closing: 'professional_goodbye'
            },
            duration_target: 50,
            template_text: `That wraps up today's episode on {episode_topic}.

To recap: {key_takeaways}.

{call_to_action}

If you found this valuable, please subscribe and share with others who might benefit. Connect with us at {social_handles}.

Next week: {next_episode_preview}.

Until then, I'm {host_name}. Thanks for listening to {podcast_title}.`,
            voice_direction: {
                pace: 'concluding',
                emphasis_points: ['key_takeaways', 'call_to_action'],
                tone_progression: 'grateful_to_professional'
            }
        });

        this.outroTemplates.set('conversational_friendly', {
            id: 'conversational_friendly',
            name: 'Conversational Friendly',
            category: 'casual',
            structure: {
                personal_reflection: 'host_thoughts',
                community_building: 'listener_connection',
                gratitude: 'appreciation',
                casual_goodbye: 'friendly_farewell'
            },
            duration_target: 35,
            template_text: `Wow, {personal_reflection}.

{community_message}

Seriously though, thank you so much for spending time with me today. {gratitude_message}.

Don't forget to {engagement_reminder}, and I'll catch you in the next episode!

Until then, keep being awesome. This has been {host_name}, and you've been listening to {podcast_title}.

Bye for now!`,
            voice_direction: {
                pace: 'warm',
                emphasis_points: ['gratitude_message', 'engagement_reminder'],
                tone_progression: 'appreciative_to_warm'
            }
        });

        this.outroTemplates.set('educational_summary', {
            id: 'educational_summary',
            name: 'Educational Summary',
            category: 'educational',
            structure: {
                learning_reinforcement: 'concept_review',
                practical_application: 'homework_assignment',
                additional_resources: 'further_reading',
                next_lesson: 'course_progression'
            },
            duration_target: 65,
            template_text: `Let's review what we covered today: {concept_summary}.

Your action items: {practical_steps}.

For additional resources, including {supplementary_materials}, visit {website_url}.

In our next episode: {next_lesson_preview}.

Thank you for learning with {podcast_title}. I'm {host_name}, and I'll see you next time.`,
            voice_direction: {
                pace: 'instructional',
                emphasis_points: ['concept_summary', 'practical_steps'],
                tone_progression: 'educational_to_encouraging'
            }
        });

        this.outroTemplates.set('storytelling_conclusion', {
            id: 'storytelling_conclusion',
            name: 'Storytelling Conclusion',
            category: 'narrative',
            structure: {
                story_moral: 'lesson_learned',
                reflection: 'deeper_meaning',
                connection_to_audience: 'universal_theme',
                series_continuation: 'story_world_expansion'
            },
            duration_target: 55,
            template_text: `And that's where our story ends... for now.

{story_moral}

{philosophical_reflection}

{audience_connection}

If you want to explore more stories from {story_world}, {series_information}.

Thank you for joining me in {podcast_title}. I'm {host_name}, your storyteller and guide.

Until our next adventure...`,
            voice_direction: {
                pace: 'reflective',
                emphasis_points: ['story_moral', 'philosophical_reflection'],
                tone_progression: 'conclusive_to_mysterious'
            }
        });
    }

    initializeBrandingElements() {
        // Standard branding elements that can be customized
        this.brandingElements.set('default_podcast', {
            podcast_title: '{PODCAST_TITLE}',
            podcast_tagline: '{PODCAST_TAGLINE}',
            host_name: '{HOST_NAME}',
            podcast_concept: '{PODCAST_CONCEPT}',
            social_handles: '{SOCIAL_MEDIA}',
            website_url: '{WEBSITE}',
            sponsor_mentions: '{SPONSORS}',
            music_style: 'corporate_upbeat',
            sound_effects: ['whoosh', 'notification_chime'],
            brand_voice: 'professional_friendly'
        });

        this.brandingElements.set('tech_podcast', {
            music_style: 'electronic_modern',
            sound_effects: ['digital_beep', 'tech_transition'],
            brand_voice: 'expert_accessible',
            terminology: 'tech_savvy'
        });

        this.brandingElements.set('wellness_podcast', {
            music_style: 'ambient_peaceful',
            sound_effects: ['nature_sounds', 'meditation_bell'],
            brand_voice: 'calm_encouraging',
            terminology: 'mindfulness_focused'
        });

        this.brandingElements.set('business_podcast', {
            music_style: 'corporate_dynamic',
            sound_effects: ['success_chime', 'impact_sound'],
            brand_voice: 'authoritative_motivational',
            terminology: 'business_focused'
        });
    }

    async generateIntro(podcast_metadata, episode_metadata, customization_options = {}) {
        const introId = uuidv4();
        
        try {
            this.emit('intro-generation-started', { introId });

            // Select appropriate template
            const templateId = customization_options.template_id || 
                              this.selectBestIntroTemplate(podcast_metadata, episode_metadata);
            
            const template = this.introTemplates.get(templateId);
            if (!template) {
                throw new Error(`Intro template not found: ${templateId}`);
            }

            // Generate content based on metadata
            const introContent = await this.generateIntroContent(
                template,
                podcast_metadata,
                episode_metadata,
                customization_options
            );

            // Apply branding elements
            const brandedContent = this.applyBranding(
                introContent,
                podcast_metadata,
                customization_options.branding_style || 'default_podcast'
            );

            // Generate voice script with timing cues
            const voiceScript = this.createVoiceScript(
                brandedContent,
                template.voice_direction,
                customization_options.voice_customization || {}
            );

            const generatedIntro = {
                id: introId,
                template_id: templateId,
                content: brandedContent,
                voice_script: voiceScript,
                metadata: {
                    podcast_title: podcast_metadata.title,
                    episode_title: episode_metadata.title,
                    duration_estimate: template.duration_target,
                    created_at: new Date().toISOString()
                },
                customization_applied: customization_options
            };

            this.generatedIntros.set(introId, generatedIntro);

            this.emit('intro-generated', {
                introId,
                templateUsed: templateId,
                estimatedDuration: template.duration_target
            });

            return generatedIntro;

        } catch (error) {
            this.emit('intro-generation-failed', { introId, error });
            throw error;
        }
    }

    async generateOutro(podcast_metadata, episode_metadata, episode_summary, customization_options = {}) {
        const outroId = uuidv4();
        
        try {
            this.emit('outro-generation-started', { outroId });

            // Select appropriate template
            const templateId = customization_options.template_id || 
                              this.selectBestOutroTemplate(podcast_metadata, episode_metadata);
            
            const template = this.outroTemplates.get(templateId);
            if (!template) {
                throw new Error(`Outro template not found: ${templateId}`);
            }

            // Generate content based on episode summary
            const outroContent = await this.generateOutroContent(
                template,
                podcast_metadata,
                episode_metadata,
                episode_summary,
                customization_options
            );

            // Apply branding elements
            const brandedContent = this.applyBranding(
                outroContent,
                podcast_metadata,
                customization_options.branding_style || 'default_podcast'
            );

            // Generate voice script with timing cues
            const voiceScript = this.createVoiceScript(
                brandedContent,
                template.voice_direction,
                customization_options.voice_customization || {}
            );

            const generatedOutro = {
                id: outroId,
                template_id: templateId,
                content: brandedContent,
                voice_script: voiceScript,
                metadata: {
                    podcast_title: podcast_metadata.title,
                    episode_title: episode_metadata.title,
                    duration_estimate: template.duration_target,
                    created_at: new Date().toISOString()
                },
                customization_applied: customization_options
            };

            this.generatedOutros.set(outroId, generatedOutro);

            this.emit('outro-generated', {
                outroId,
                templateUsed: templateId,
                estimatedDuration: template.duration_target
            });

            return generatedOutro;

        } catch (error) {
            this.emit('outro-generation-failed', { outroId, error });
            throw error;
        }
    }

    selectBestIntroTemplate(podcast_metadata, episode_metadata) {
        // Analyze podcast characteristics to select best template
        const category = podcast_metadata.category?.toLowerCase();
        const tone = podcast_metadata.tone?.toLowerCase();
        
        if (category === 'education' || tone === 'educational') {
            return 'educational_expert';
        } else if (category === 'comedy' || tone === 'humorous') {
            return 'comedy_entertainment';
        } else if (category === 'news' || tone === 'informational') {
            return 'news_format';
        } else if (category === 'storytelling' || tone === 'narrative') {
            return 'storytelling_narrative';
        } else if (tone === 'casual' || tone === 'friendly') {
            return 'conversational_friendly';
        } else {
            return 'professional_standard';
        }
    }

    selectBestOutroTemplate(podcast_metadata, episode_metadata) {
        const category = podcast_metadata.category?.toLowerCase();
        const tone = podcast_metadata.tone?.toLowerCase();
        
        if (category === 'education' || tone === 'educational') {
            return 'educational_summary';
        } else if (category === 'storytelling' || tone === 'narrative') {
            return 'storytelling_conclusion';
        } else if (tone === 'casual' || tone === 'friendly') {
            return 'conversational_friendly';
        } else {
            return 'professional_standard';
        }
    }

    async generateIntroContent(template, podcast_metadata, episode_metadata, customization_options) {
        const completion = await this.openai.chat.completions.create({
            model: this.config.model,
            messages: [
                {
                    role: 'system',
                    content: `Generate personalized content for a podcast intro based on the provided template and metadata.

Template: ${template.name}
Category: ${template.category}
Target Duration: ${template.duration_target} seconds
Tone: ${template.tone}

Fill in the template with engaging, specific content based on the podcast and episode information.`
                },
                {
                    role: 'user',
                    content: `Template: ${template.template_text}

Podcast Information:
- Title: ${podcast_metadata.title}
- Description: ${podcast_metadata.description || ''}
- Host: ${podcast_metadata.host || 'Host'}
- Category: ${podcast_metadata.category || ''}

Episode Information:
- Title: ${episode_metadata.title}
- Topic: ${episode_metadata.topic || episode_metadata.title}
- Description: ${episode_metadata.description || ''}

Customization Notes: ${customization_options.content_notes || 'None'}

Generate the personalized intro content by filling in the template placeholders with specific, engaging content.`
                }
            ],
            temperature: 0.7,
            max_tokens: 800
        });

        return completion.choices[0].message.content.trim();
    }

    async generateOutroContent(template, podcast_metadata, episode_metadata, episode_summary, customization_options) {
        const completion = await this.openai.chat.completions.create({
            model: this.config.model,
            messages: [
                {
                    role: 'system',
                    content: `Generate personalized content for a podcast outro based on the provided template, metadata, and episode summary.

Template: ${template.name}
Category: ${template.category}
Target Duration: ${template.duration_target} seconds

Create a compelling outro that summarizes the episode and encourages listener engagement.`
                },
                {
                    role: 'user',
                    content: `Template: ${template.template_text}

Podcast Information:
- Title: ${podcast_metadata.title}
- Host: ${podcast_metadata.host || 'Host'}
- Website: ${podcast_metadata.website || ''}
- Social Media: ${podcast_metadata.social_media || ''}

Episode Information:
- Title: ${episode_metadata.title}
- Topic: ${episode_metadata.topic || episode_metadata.title}

Episode Summary:
${episode_summary || 'Episode content covered various interesting topics.'}

Next Episode: ${customization_options.next_episode_preview || 'Stay tuned for more great content!'}

Generate the personalized outro content that effectively concludes the episode and encourages engagement.`
                }
            ],
            temperature: 0.6,
            max_tokens: 800
        });

        return completion.choices[0].message.content.trim();
    }

    applyBranding(content, podcast_metadata, branding_style) {
        const branding = this.brandingElements.get(branding_style) || this.brandingElements.get('default_podcast');
        
        let brandedContent = content;

        // Replace branding placeholders
        const replacements = {
            '{PODCAST_TITLE}': podcast_metadata.title || 'Your Podcast',
            '{PODCAST_TAGLINE}': podcast_metadata.tagline || '',
            '{HOST_NAME}': podcast_metadata.host || 'Your Host',
            '{PODCAST_CONCEPT}': podcast_metadata.concept || 'we explore interesting topics',
            '{SOCIAL_MEDIA}': podcast_metadata.social_media || 'your social handles',
            '{WEBSITE}': podcast_metadata.website || 'your website',
            '{SPONSORS}': podcast_metadata.sponsors ? `Thanks to our sponsors: ${podcast_metadata.sponsors.join(', ')}.` : ''
        };

        Object.entries(replacements).forEach(([placeholder, value]) => {
            brandedContent = brandedContent.replace(new RegExp(placeholder, 'g'), value);
        });

        return brandedContent;
    }

    createVoiceScript(content, voice_direction, voice_customization) {
        // Add voice direction cues to the content
        const script = {
            content: content,
            voice_cues: {
                overall_pace: voice_direction.pace || 'moderate',
                tone_progression: voice_direction.tone_progression || 'consistent',
                emphasis_points: voice_direction.emphasis_points || [],
                pause_points: this.identifyPausePoints(content),
                volume_changes: this.identifyVolumeChanges(content, voice_direction),
                emotion_cues: this.identifyEmotionCues(content, voice_direction)
            },
            timing_estimates: this.estimateTimingBreakdown(content),
            pronunciation_guide: voice_customization.pronunciation_guide || {},
            custom_voice_settings: {
                speed: voice_customization.speed || 1.0,
                pitch: voice_customization.pitch || 0,
                emphasis_strength: voice_customization.emphasis_strength || 'medium'
            }
        };

        return script;
    }

    identifyPausePoints(content) {
        const pausePoints = [];
        const sentences = content.split(/[.!?]+/);
        let currentPosition = 0;
        
        sentences.forEach((sentence, index) => {
            currentPosition += sentence.length;
            if (index < sentences.length - 1) {
                pausePoints.push({
                    position: currentPosition,
                    duration: 'short',
                    reason: 'sentence_break'
                });
            }
            currentPosition += 1; // for punctuation
        });

        // Add paragraph breaks
        const paragraphs = content.split('\n\n');
        currentPosition = 0;
        paragraphs.forEach((paragraph, index) => {
            currentPosition += paragraph.length;
            if (index < paragraphs.length - 1) {
                pausePoints.push({
                    position: currentPosition,
                    duration: 'medium',
                    reason: 'paragraph_break'
                });
            }
            currentPosition += 2; // for double newline
        });

        return pausePoints;
    }

    identifyVolumeChanges(content, voice_direction) {
        const volumeChanges = [];
        
        // Look for emphasis points
        if (voice_direction.emphasis_points) {
            voice_direction.emphasis_points.forEach(emphasisPoint => {
                const regex = new RegExp(emphasisPoint, 'gi');
                let match;
                while ((match = regex.exec(content)) !== null) {
                    volumeChanges.push({
                        start_position: match.index,
                        end_position: match.index + match[0].length,
                        volume_change: '+10%',
                        reason: 'emphasis'
                    });
                }
            });
        }

        return volumeChanges;
    }

    identifyEmotionCues(content, voice_direction) {
        const emotionCues = [];
        
        // Identify emotional content
        const emotionalMarkers = {
            excitement: ['excited', 'amazing', 'incredible', 'wow'],
            gratitude: ['thank you', 'grateful', 'appreciate'],
            emphasis: ['important', 'key', 'crucial', 'remember'],
            warmth: ['welcome', 'hello', 'glad', 'happy']
        };

        Object.entries(emotionalMarkers).forEach(([emotion, markers]) => {
            markers.forEach(marker => {
                const regex = new RegExp(`\\b${marker}\\b`, 'gi');
                let match;
                while ((match = regex.exec(content)) !== null) {
                    emotionCues.push({
                        start_position: match.index,
                        end_position: match.index + match[0].length,
                        emotion: emotion,
                        intensity: 'moderate'
                    });
                }
            });
        });

        return emotionCues;
    }

    estimateTimingBreakdown(content) {
        const words = content.split(/\s+/).length;
        const averageWordsPerMinute = 150; // Standard speaking pace
        const totalMinutes = words / averageWordsPerMinute;
        
        return {
            total_words: words,
            estimated_duration_minutes: totalMinutes,
            estimated_duration_seconds: Math.round(totalMinutes * 60),
            words_per_minute: averageWordsPerMinute
        };
    }

    async createCompleteIntroOutroPackage(podcast_metadata, episode_metadata, episode_summary, options = {}) {
        try {
            // Generate both intro and outro
            const intro = await this.generateIntro(
                podcast_metadata,
                episode_metadata,
                options.intro_options || {}
            );

            const outro = await this.generateOutro(
                podcast_metadata,
                episode_metadata,
                episode_summary,
                options.outro_options || {}
            );

            // Create package metadata
            const packageId = uuidv4();
            const package_info = {
                id: packageId,
                intro_id: intro.id,
                outro_id: outro.id,
                podcast_metadata: podcast_metadata,
                episode_metadata: episode_metadata,
                created_at: new Date().toISOString(),
                estimated_total_duration: intro.metadata.duration_estimate + outro.metadata.duration_estimate
            };

            this.emit('intro-outro-package-created', {
                packageId: packageId,
                introId: intro.id,
                outroId: outro.id
            });

            return {
                package_info: package_info,
                intro: intro,
                outro: outro
            };

        } catch (error) {
            this.emit('package-creation-failed', { error });
            throw error;
        }
    }

    async generateMusicAndEffects(introOrOutro, music_options = {}) {
        const audioId = uuidv4();
        
        try {
            // This would integrate with music generation/selection services
            const music_config = {
                style: music_options.style || 'corporate_upbeat',
                duration: introOrOutro.metadata.duration_estimate + 5, // Extra padding
                fade_in: music_options.fade_in || 2,
                fade_out: music_options.fade_out || 3,
                volume_during_speech: music_options.background_volume || 0.2,
                volume_solo: music_options.solo_volume || 0.8
            };

            // Placeholder for music generation - would integrate with actual music service
            const musicPath = await this.selectOrGenerateMusic(music_config);
            
            this.emit('music-generated', { audioId, musicPath });

            return {
                audio_id: audioId,
                music_path: musicPath,
                config: music_config
            };

        } catch (error) {
            this.emit('music-generation-failed', { audioId, error });
            throw error;
        }
    }

    async selectOrGenerateMusic(music_config) {
        // This would implement actual music selection/generation logic
        // For now, return a placeholder path
        return this.config.default_music_path;
    }

    getIntroTemplates() {
        return Array.from(this.introTemplates.values()).map(template => ({
            id: template.id,
            name: template.name,
            category: template.category,
            duration_target: template.duration_target,
            tone: template.tone,
            energy_level: template.energy_level
        }));
    }

    getOutroTemplates() {
        return Array.from(this.outroTemplates.values()).map(template => ({
            id: template.id,
            name: template.name,
            category: template.category,
            duration_target: template.duration_target
        }));
    }

    getBrandingStyles() {
        return Array.from(this.brandingElements.keys());
    }

    getGeneratedIntro(introId) {
        return this.generatedIntros.get(introId);
    }

    getGeneratedOutro(outroId) {
        return this.generatedOutros.get(outroId);
    }

    async saveTemplate(templateData) {
        const templatePath = path.join(
            this.config.templates_directory,
            `${templateData.id}.json`
        );

        await fs.writeFile(templatePath, JSON.stringify(templateData, null, 2));
        
        if (templateData.type === 'intro') {
            this.introTemplates.set(templateData.id, templateData);
        } else if (templateData.type === 'outro') {
            this.outroTemplates.set(templateData.id, templateData);
        }

        this.emit('template-saved', { templateId: templateData.id, templatePath });
        return templatePath;
    }

    async loadCustomTemplates() {
        try {
            const files = await fs.readdir(this.config.templates_directory);
            const jsonFiles = files.filter(file => file.endsWith('.json'));

            for (const file of jsonFiles) {
                const filePath = path.join(this.config.templates_directory, file);
                const content = await fs.readFile(filePath, 'utf8');
                const template = JSON.parse(content);

                if (template.type === 'intro') {
                    this.introTemplates.set(template.id, template);
                } else if (template.type === 'outro') {
                    this.outroTemplates.set(template.id, template);
                }
            }

            this.emit('custom-templates-loaded', { count: jsonFiles.length });
        } catch (error) {
            this.emit('template-load-failed', { error });
        }
    }

    async customizeTemplate(templateId, customizations, newTemplateId) {
        const originalTemplate = this.introTemplates.get(templateId) || this.outroTemplates.get(templateId);
        
        if (!originalTemplate) {
            throw new Error(`Template not found: ${templateId}`);
        }

        const customizedTemplate = {
            ...originalTemplate,
            id: newTemplateId,
            name: customizations.name || `${originalTemplate.name} (Custom)`,
            based_on: templateId,
            customizations_applied: customizations,
            created_at: new Date().toISOString()
        };

        // Apply customizations
        if (customizations.template_text) {
            customizedTemplate.template_text = customizations.template_text;
        }
        
        if (customizations.voice_direction) {
            customizedTemplate.voice_direction = {
                ...customizedTemplate.voice_direction,
                ...customizations.voice_direction
            };
        }

        if (customizations.duration_target) {
            customizedTemplate.duration_target = customizations.duration_target;
        }

        // Save the customized template
        await this.saveTemplate(customizedTemplate);

        return customizedTemplate;
    }
}

export default IntroOutroAutomator;