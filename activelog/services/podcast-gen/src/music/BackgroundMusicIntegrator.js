import { EventEmitter } from 'events';
import fs from 'fs/promises';
import path from 'path';
import ffmpeg from 'fluent-ffmpeg';
import ffmpegStatic from 'ffmpeg-static';
import { v4 as uuidv4 } from 'uuid';

// Set ffmpeg path
ffmpeg.setFfmpegPath(ffmpegStatic);

class BackgroundMusicIntegrator extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            music_library_directory: config.music_library_directory || './assets/music',
            output_directory: config.output_directory || './output/with_music',
            temp_directory: config.temp_directory || './temp/music_processing',
            default_fade_in: config.default_fade_in || 3.0,
            default_fade_out: config.default_fade_out || 3.0,
            default_background_volume: config.default_background_volume || 0.15,
            default_intro_volume: config.default_intro_volume || 0.8,
            ...config
        };

        this.musicLibrary = new Map();
        this.musicProfiles = new Map();
        this.integrationTasks = new Map();
        this.musicSegments = new Map();

        this.initializeMusicProfiles();
        this.ensureDirectories();
        this.loadMusicLibrary();
    }

    async ensureDirectories() {
        try {
            await fs.mkdir(this.config.music_library_directory, { recursive: true });
            await fs.mkdir(this.config.output_directory, { recursive: true });
            await fs.mkdir(this.config.temp_directory, { recursive: true });
        } catch (error) {
            this.emit('error', { type: 'directory-creation', error });
        }
    }

    initializeMusicProfiles() {
        // Define music profiles for different podcast styles and moods
        this.musicProfiles.set('corporate_professional', {
            id: 'corporate_professional',
            name: 'Corporate Professional',
            description: 'Clean, professional background music for business podcasts',
            characteristics: {
                tempo: 'moderate',
                energy: 'low_to_medium',
                instrumentation: ['piano', 'strings', 'light_percussion'],
                mood: 'confident_and_stable',
                genre: 'ambient_corporate'
            },
            usage_guidelines: {
                intro_volume: 0.8,
                background_volume: 0.12,
                fade_in_duration: 3.0,
                fade_out_duration: 4.0,
                suitable_for: ['business', 'educational', 'professional_interview']
            },
            timing: {
                intro_duration: 15,
                outro_duration: 12,
                background_segments: 'throughout'
            }
        });

        this.musicProfiles.set('upbeat_energetic', {
            id: 'upbeat_energetic',
            name: 'Upbeat Energetic',
            description: 'High-energy music for engaging, dynamic content',
            characteristics: {
                tempo: 'fast',
                energy: 'high',
                instrumentation: ['electric_guitar', 'drums', 'synthesizer'],
                mood: 'exciting_and_motivating',
                genre: 'upbeat_electronic'
            },
            usage_guidelines: {
                intro_volume: 0.9,
                background_volume: 0.18,
                fade_in_duration: 2.0,
                fade_out_duration: 3.0,
                suitable_for: ['comedy', 'entertainment', 'motivational']
            },
            timing: {
                intro_duration: 12,
                outro_duration: 10,
                background_segments: 'selective'
            }
        });

        this.musicProfiles.set('ambient_calm', {
            id: 'ambient_calm',
            name: 'Ambient Calm',
            description: 'Peaceful, meditative background for thoughtful content',
            characteristics: {
                tempo: 'slow',
                energy: 'low',
                instrumentation: ['ambient_pads', 'nature_sounds', 'soft_piano'],
                mood: 'peaceful_and_contemplative',
                genre: 'ambient_meditation'
            },
            usage_guidelines: {
                intro_volume: 0.6,
                background_volume: 0.08,
                fade_in_duration: 5.0,
                fade_out_duration: 6.0,
                suitable_for: ['wellness', 'philosophy', 'storytelling']
            },
            timing: {
                intro_duration: 20,
                outro_duration: 18,
                background_segments: 'continuous_low'
            }
        });

        this.musicProfiles.set('cinematic_dramatic', {
            id: 'cinematic_dramatic',
            name: 'Cinematic Dramatic',
            description: 'Dramatic orchestral music for narrative podcasts',
            characteristics: {
                tempo: 'variable',
                energy: 'medium_to_high',
                instrumentation: ['full_orchestra', 'dramatic_percussion'],
                mood: 'suspenseful_and_epic',
                genre: 'cinematic_score'
            },
            usage_guidelines: {
                intro_volume: 0.85,
                background_volume: 0.15,
                fade_in_duration: 4.0,
                fade_out_duration: 5.0,
                suitable_for: ['storytelling', 'documentary', 'mystery']
            },
            timing: {
                intro_duration: 18,
                outro_duration: 15,
                background_segments: 'dramatic_moments'
            }
        });

        this.musicProfiles.set('tech_modern', {
            id: 'tech_modern',
            name: 'Tech Modern',
            description: 'Electronic, futuristic sounds for technology content',
            characteristics: {
                tempo: 'moderate_to_fast',
                energy: 'medium',
                instrumentation: ['synthesizer', 'electronic_beats', 'digital_fx'],
                mood: 'innovative_and_forward_thinking',
                genre: 'electronic_tech'
            },
            usage_guidelines: {
                intro_volume: 0.75,
                background_volume: 0.14,
                fade_in_duration: 2.5,
                fade_out_duration: 3.5,
                suitable_for: ['technology', 'science', 'innovation']
            },
            timing: {
                intro_duration: 14,
                outro_duration: 11,
                background_segments: 'tech_discussions'
            }
        });

        this.musicProfiles.set('acoustic_warm', {
            id: 'acoustic_warm',
            name: 'Acoustic Warm',
            description: 'Warm acoustic instruments for personal, intimate conversations',
            characteristics: {
                tempo: 'moderate',
                energy: 'medium',
                instrumentation: ['acoustic_guitar', 'strings', 'light_percussion'],
                mood: 'warm_and_inviting',
                genre: 'acoustic_folk'
            },
            usage_guidelines: {
                intro_volume: 0.7,
                background_volume: 0.11,
                fade_in_duration: 3.5,
                fade_out_duration: 4.5,
                suitable_for: ['personal_stories', 'interviews', 'casual_conversation']
            },
            timing: {
                intro_duration: 16,
                outro_duration: 14,
                background_segments: 'emotional_moments'
            }
        });
    }

    async loadMusicLibrary() {
        try {
            const musicFiles = await fs.readdir(this.config.music_library_directory, { withFileTypes: true });
            
            for (const file of musicFiles) {
                if (file.isFile() && this.isAudioFile(file.name)) {
                    const filePath = path.join(this.config.music_library_directory, file.name);
                    const musicInfo = await this.analyzeMusicFile(filePath);
                    this.musicLibrary.set(file.name, musicInfo);
                }
            }

            this.emit('music-library-loaded', { count: this.musicLibrary.size });
        } catch (error) {
            this.emit('music-library-load-failed', { error });
        }
    }

    isAudioFile(filename) {
        const audioExtensions = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'];
        return audioExtensions.some(ext => filename.toLowerCase().endsWith(ext));
    }

    async analyzeMusicFile(filePath) {
        return new Promise((resolve, reject) => {
            ffmpeg.ffprobe(filePath, (err, metadata) => {
                if (err) {
                    reject(err);
                } else {
                    resolve({
                        path: filePath,
                        duration: metadata.format.duration,
                        bitrate: metadata.format.bit_rate,
                        sample_rate: metadata.streams[0].sample_rate,
                        channels: metadata.streams[0].channels,
                        format: metadata.format.format_name,
                        analyzed_at: new Date().toISOString()
                    });
                }
            });
        });
    }

    async integrateBackgroundMusic(podcastAudioPath, musicIntegrationRequest) {
        const taskId = uuidv4();
        
        try {
            this.emit('music-integration-started', { taskId, podcastAudioPath });

            const {
                music_profile_id,
                custom_music_path,
                integration_style,
                volume_settings,
                timing_adjustments,
                segments_to_enhance
            } = musicIntegrationRequest;

            // Create integration task
            const integrationTask = {
                id: taskId,
                podcast_audio_path: podcastAudioPath,
                music_profile_id: music_profile_id,
                custom_music_path: custom_music_path,
                integration_style: integration_style || 'background_throughout',
                status: 'processing',
                started_at: new Date().toISOString(),
                steps: []
            };

            this.integrationTasks.set(taskId, integrationTask);

            // Get podcast duration
            const podcastDuration = await this.getAudioDuration(podcastAudioPath);
            integrationTask.podcast_duration = podcastDuration;

            // Select or validate music
            const musicPath = await this.selectMusic(music_profile_id, custom_music_path, podcastDuration);
            integrationTask.selected_music_path = musicPath;

            // Generate integration plan
            const integrationPlan = await this.createIntegrationPlan(
                podcastDuration,
                music_profile_id,
                integration_style,
                volume_settings,
                timing_adjustments,
                segments_to_enhance
            );
            integrationTask.integration_plan = integrationPlan;

            // Execute integration
            const outputPath = await this.executeIntegration(
                taskId,
                podcastAudioPath,
                musicPath,
                integrationPlan
            );

            integrationTask.status = 'completed';
            integrationTask.output_path = outputPath;
            integrationTask.completed_at = new Date().toISOString();

            this.emit('music-integration-completed', {
                taskId,
                outputPath,
                processingTime: Date.now() - new Date(integrationTask.started_at).getTime()
            });

            return {
                task_id: taskId,
                output_path: outputPath,
                integration_plan: integrationPlan,
                music_used: musicPath
            };

        } catch (error) {
            const task = this.integrationTasks.get(taskId);
            if (task) {
                task.status = 'failed';
                task.error = error.message;
            }
            
            this.emit('music-integration-failed', { taskId, error });
            throw error;
        }
    }

    async selectMusic(musicProfileId, customMusicPath, podcastDuration) {
        if (customMusicPath) {
            // Validate custom music file
            try {
                await fs.access(customMusicPath);
                const musicInfo = await this.analyzeMusicFile(customMusicPath);
                
                if (musicInfo.duration < podcastDuration) {
                    // Music is shorter than podcast, we'll need to loop it
                    return await this.prepareLoopedMusic(customMusicPath, podcastDuration);
                }
                
                return customMusicPath;
            } catch (error) {
                throw new Error(`Custom music file not accessible: ${customMusicPath}`);
            }
        }

        // Select from library based on profile
        const musicProfile = this.musicProfiles.get(musicProfileId);
        if (!musicProfile) {
            throw new Error(`Music profile not found: ${musicProfileId}`);
        }

        // Find suitable music from library
        const suitableMusic = Array.from(this.musicLibrary.values()).find(music => 
            music.duration >= podcastDuration * 0.8 // At least 80% of podcast duration
        );

        if (suitableMusic) {
            return suitableMusic.path;
        }

        // Generate or use default music
        return await this.generateDefaultMusic(musicProfile, podcastDuration);
    }

    async prepareLoopedMusic(musicPath, targetDuration) {
        const loopedMusicPath = path.join(
            this.config.temp_directory,
            `looped_${Date.now()}_${path.basename(musicPath)}`
        );

        return new Promise((resolve, reject) => {
            ffmpeg(musicPath)
                .inputOptions(['-stream_loop', '-1']) // Loop indefinitely
                .duration(targetDuration + 10) // Add 10 seconds padding
                .output(loopedMusicPath)
                .on('end', () => resolve(loopedMusicPath))
                .on('error', reject)
                .run();
        });
    }

    async generateDefaultMusic(musicProfile, duration) {
        // This would integrate with music generation services
        // For now, return a placeholder path that would be created
        const defaultMusicPath = path.join(
            this.config.music_library_directory,
            `generated_${musicProfile.id}_${duration}s.mp3`
        );

        // Placeholder - would implement actual music generation
        // Could integrate with services like AIVA, Amper Music, or others
        
        return defaultMusicPath;
    }

    async createIntegrationPlan(duration, musicProfileId, integrationStyle, volumeSettings, timingAdjustments, segmentsToEnhance) {
        const musicProfile = this.musicProfiles.get(musicProfileId) || this.musicProfiles.get('corporate_professional');
        
        const plan = {
            total_duration: duration,
            music_profile: musicProfile,
            integration_style: integrationStyle,
            segments: []
        };

        // Default volume settings from profile
        const volumes = {
            intro_volume: volumeSettings?.intro_volume || musicProfile.usage_guidelines.intro_volume,
            background_volume: volumeSettings?.background_volume || musicProfile.usage_guidelines.background_volume,
            outro_volume: volumeSettings?.outro_volume || musicProfile.usage_guidelines.intro_volume,
            transition_volume: volumeSettings?.transition_volume || 0.3
        };

        // Default timing from profile
        const timing = {
            fade_in: timingAdjustments?.fade_in || musicProfile.usage_guidelines.fade_in_duration,
            fade_out: timingAdjustments?.fade_out || musicProfile.usage_guidelines.fade_out_duration,
            intro_duration: timingAdjustments?.intro_duration || musicProfile.timing.intro_duration,
            outro_duration: timingAdjustments?.outro_duration || musicProfile.timing.outro_duration
        };

        switch (integrationStyle) {
            case 'intro_outro_only':
                plan.segments = this.createIntroOutroOnlyPlan(duration, volumes, timing);
                break;
            case 'background_throughout':
                plan.segments = this.createBackgroundThroughoutPlan(duration, volumes, timing);
                break;
            case 'dynamic_segments':
                plan.segments = this.createDynamicSegmentsPlan(duration, volumes, timing, segmentsToEnhance);
                break;
            case 'music_breaks':
                plan.segments = this.createMusicBreaksPlan(duration, volumes, timing);
                break;
            default:
                plan.segments = this.createBackgroundThroughoutPlan(duration, volumes, timing);
        }

        return plan;
    }

    createIntroOutroOnlyPlan(duration, volumes, timing) {
        return [
            {
                type: 'intro_music',
                start_time: 0,
                end_time: timing.intro_duration,
                volume: volumes.intro_volume,
                fade_in: timing.fade_in,
                fade_out: 2.0,
                description: 'Full volume intro music'
            },
            {
                type: 'silence',
                start_time: timing.intro_duration,
                end_time: duration - timing.outro_duration,
                volume: 0,
                description: 'No music during main content'
            },
            {
                type: 'outro_music',
                start_time: duration - timing.outro_duration,
                end_time: duration,
                volume: volumes.outro_volume,
                fade_in: 2.0,
                fade_out: timing.fade_out,
                description: 'Full volume outro music'
            }
        ];
    }

    createBackgroundThroughoutPlan(duration, volumes, timing) {
        return [
            {
                type: 'intro_music',
                start_time: 0,
                end_time: timing.intro_duration,
                volume: volumes.intro_volume,
                fade_in: timing.fade_in,
                fade_out: 3.0,
                description: 'Full volume intro, fade to background'
            },
            {
                type: 'background_music',
                start_time: timing.intro_duration,
                end_time: duration - timing.outro_duration,
                volume: volumes.background_volume,
                fade_in: 0,
                fade_out: 0,
                description: 'Continuous low-volume background'
            },
            {
                type: 'outro_music',
                start_time: duration - timing.outro_duration,
                end_time: duration,
                volume: volumes.outro_volume,
                fade_in: 3.0,
                fade_out: timing.fade_out,
                description: 'Fade up to full volume outro'
            }
        ];
    }

    createDynamicSegmentsPlan(duration, volumes, timing, segmentsToEnhance) {
        const segments = [];
        
        // Start with intro
        segments.push({
            type: 'intro_music',
            start_time: 0,
            end_time: timing.intro_duration,
            volume: volumes.intro_volume,
            fade_in: timing.fade_in,
            fade_out: 2.0
        });

        // Add enhanced segments
        if (segmentsToEnhance && segmentsToEnhance.length > 0) {
            segmentsToEnhance.forEach(segment => {
                segments.push({
                    type: 'enhanced_segment',
                    start_time: segment.start_time,
                    end_time: segment.end_time,
                    volume: segment.volume || 0.25,
                    fade_in: 1.0,
                    fade_out: 1.0,
                    description: segment.description || 'Enhanced segment'
                });
            });
        }

        // Fill gaps with low background music
        segments.push({
            type: 'background_music',
            start_time: timing.intro_duration,
            end_time: duration - timing.outro_duration,
            volume: volumes.background_volume,
            fade_in: 0,
            fade_out: 0,
            priority: 'low' // Will be overridden by enhanced segments
        });

        // Add outro
        segments.push({
            type: 'outro_music',
            start_time: duration - timing.outro_duration,
            end_time: duration,
            volume: volumes.outro_volume,
            fade_in: 2.0,
            fade_out: timing.fade_out
        });

        return segments.sort((a, b) => a.start_time - b.start_time);
    }

    createMusicBreaksPlan(duration, volumes, timing) {
        const segments = [];
        const breakDuration = 3; // 3-second music breaks
        const breakInterval = 300; // Every 5 minutes
        
        // Intro
        segments.push({
            type: 'intro_music',
            start_time: 0,
            end_time: timing.intro_duration,
            volume: volumes.intro_volume,
            fade_in: timing.fade_in,
            fade_out: 2.0
        });

        // Music breaks throughout
        for (let time = breakInterval; time < duration - timing.outro_duration - breakDuration; time += breakInterval) {
            segments.push({
                type: 'music_break',
                start_time: time,
                end_time: time + breakDuration,
                volume: volumes.transition_volume,
                fade_in: 1.0,
                fade_out: 1.0,
                description: 'Transitional music break'
            });
        }

        // Outro
        segments.push({
            type: 'outro_music',
            start_time: duration - timing.outro_duration,
            end_time: duration,
            volume: volumes.outro_volume,
            fade_in: 2.0,
            fade_out: timing.fade_out
        });

        return segments;
    }

    async executeIntegration(taskId, podcastPath, musicPath, integrationPlan) {
        const outputPath = path.join(
            this.config.output_directory,
            `with_music_${taskId}.mp3`
        );

        this.emit('integration-execution-started', { taskId, outputPath });

        return new Promise((resolve, reject) => {
            const command = ffmpeg()
                .input(podcastPath)
                .input(musicPath);

            // Build complex filter for music integration
            const filterComplex = this.buildMusicFilterComplex(integrationPlan);
            
            command
                .complexFilter(filterComplex)
                .outputOptions([
                    '-map', '[final_output]',
                    '-c:a', 'libmp3lame',
                    '-b:a', '192k',
                    '-ar', '44100',
                    '-ac', '2'
                ])
                .output(outputPath)
                .on('start', (commandLine) => {
                    this.emit('ffmpeg-started', { taskId, commandLine });
                })
                .on('progress', (progress) => {
                    this.emit('integration-progress', { taskId, progress });
                })
                .on('end', () => {
                    this.emit('integration-execution-completed', { taskId, outputPath });
                    resolve(outputPath);
                })
                .on('error', (error) => {
                    this.emit('integration-execution-failed', { taskId, error });
                    reject(error);
                })
                .run();
        });
    }

    buildMusicFilterComplex(integrationPlan) {
        const filters = [];
        let outputLabel = '[podcast]';
        let musicOutputLabel = '[music_processed]';
        
        // Label inputs
        filters.push('[0:a]anull[podcast]');
        filters.push('[1:a]anull[music_raw]');

        // Process music according to plan
        const musicProcessingSteps = this.buildMusicProcessingSteps(integrationPlan);
        filters.push(...musicProcessingSteps);

        // Final mix
        filters.push(`${outputLabel}${musicOutputLabel}amix=inputs=2:duration=first:weights=1 0.8[final_output]`);

        return filters;
    }

    buildMusicProcessingSteps(integrationPlan) {
        const steps = [];
        const segments = integrationPlan.segments;
        
        // Create volume automation for each segment
        let volumeFilter = '[music_raw]';
        
        segments.forEach((segment, index) => {
            if (segment.type !== 'silence') {
                const volumeChange = `volume=${segment.volume}:enable='between(t,${segment.start_time},${segment.end_time})'`;
                
                if (segment.fade_in && segment.fade_in > 0) {
                    const fadeInFilter = `afade=t=in:ss=${segment.start_time}:d=${segment.fade_in}`;
                    volumeFilter += `[temp${index}a]; [temp${index}a]${fadeInFilter}`;
                }
                
                if (segment.fade_out && segment.fade_out > 0) {
                    const fadeOutEnd = segment.end_time;
                    const fadeOutStart = fadeOutEnd - segment.fade_out;
                    const fadeOutFilter = `afade=t=out:st=${fadeOutStart}:d=${segment.fade_out}`;
                    volumeFilter += `[temp${index}b]; [temp${index}b]${fadeOutFilter}`;
                }
                
                volumeFilter += `[temp${index}]; [temp${index}]${volumeChange}`;
            }
        });
        
        volumeFilter += '[music_processed]';
        steps.push(volumeFilter);
        
        return steps;
    }

    async getAudioDuration(audioPath) {
        return new Promise((resolve, reject) => {
            ffmpeg.ffprobe(audioPath, (err, metadata) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(metadata.format.duration);
                }
            });
        });
    }

    getMusicProfiles() {
        return Array.from(this.musicProfiles.values()).map(profile => ({
            id: profile.id,
            name: profile.name,
            description: profile.description,
            characteristics: profile.characteristics,
            suitable_for: profile.usage_guidelines.suitable_for
        }));
    }

    getMusicLibrary() {
        return Array.from(this.musicLibrary.entries()).map(([filename, info]) => ({
            filename,
            duration: info.duration,
            format: info.format,
            sample_rate: info.sample_rate
        }));
    }

    getIntegrationTask(taskId) {
        return this.integrationTasks.get(taskId);
    }

    async addMusicToLibrary(musicFilePath, metadata = {}) {
        try {
            const filename = path.basename(musicFilePath);
            const destinationPath = path.join(this.config.music_library_directory, filename);
            
            // Copy file to library
            await fs.copyFile(musicFilePath, destinationPath);
            
            // Analyze the music file
            const musicInfo = await this.analyzeMusicFile(destinationPath);
            musicInfo.metadata = metadata;
            
            this.musicLibrary.set(filename, musicInfo);
            
            this.emit('music-added-to-library', { filename, musicInfo });
            
            return {
                filename,
                path: destinationPath,
                info: musicInfo
            };
        } catch (error) {
            this.emit('music-library-add-failed', { musicFilePath, error });
            throw error;
        }
    }

    async createMusicProfile(profileData) {
        const {
            id,
            name,
            description,
            characteristics,
            usage_guidelines,
            timing
        } = profileData;

        const profile = {
            id,
            name,
            description,
            characteristics: characteristics || {},
            usage_guidelines: usage_guidelines || {},
            timing: timing || {},
            created_at: new Date().toISOString(),
            custom: true
        };

        this.musicProfiles.set(id, profile);
        
        this.emit('music-profile-created', { profileId: id, profile });
        
        return profile;
    }

    async analyzeAudioForMusicSuitability(audioPath) {
        // Analyze audio characteristics to suggest suitable music profiles
        try {
            const audioInfo = await this.analyzeMusicFile(audioPath);
            
            const analysis = {
                duration: audioInfo.duration,
                suggested_profiles: [],
                integration_recommendations: {}
            };

            // Simple heuristics for profile suggestions
            if (audioInfo.duration > 1800) { // 30+ minutes
                analysis.suggested_profiles.push('ambient_calm');
                analysis.integration_recommendations.style = 'background_throughout';
            } else if (audioInfo.duration < 600) { // Under 10 minutes
                analysis.suggested_profiles.push('upbeat_energetic');
                analysis.integration_recommendations.style = 'intro_outro_only';
            } else {
                analysis.suggested_profiles.push('corporate_professional');
                analysis.integration_recommendations.style = 'dynamic_segments';
            }

            return analysis;
        } catch (error) {
            throw new Error(`Failed to analyze audio: ${error.message}`);
        }
    }

    async removeBackgroundMusic(audioWithMusicPath, outputPath) {
        // Attempt to remove background music using spectral subtraction
        // This is a complex process and results may vary
        return new Promise((resolve, reject) => {
            ffmpeg(audioWithMusicPath)
                .audioFilters([
                    'highpass=f=300',
                    'lowpass=f=3000',
                    'compand=attacks=0.3:decays=0.8:points=-70/-90|-24/-12|0/-6|20/20'
                ])
                .output(outputPath)
                .on('end', () => resolve(outputPath))
                .on('error', reject)
                .run();
        });
    }
}

export default BackgroundMusicIntegrator;