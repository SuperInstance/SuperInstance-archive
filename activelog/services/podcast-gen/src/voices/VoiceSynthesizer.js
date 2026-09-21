import { EventEmitter } from 'events';
import OpenAI from 'openai';
import fs from 'fs/promises';
import path from 'path';
import ffmpeg from 'fluent-ffmpeg';
import ffmpegStatic from 'ffmpeg-static';
import { GoogleAuth } from 'google-auth-library';
import textToSpeech from '@google-cloud/text-to-speech';
import AWS from 'aws-sdk';
import { v4 as uuidv4 } from 'uuid';

// Set ffmpeg path
ffmpeg.setFfmpegPath(ffmpegStatic);

class VoiceSynthesizer extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            openai_api_key: config.openai_api_key || process.env.OPENAI_API_KEY,
            google_credentials: config.google_credentials || process.env.GOOGLE_APPLICATION_CREDENTIALS,
            aws_access_key: config.aws_access_key || process.env.AWS_ACCESS_KEY_ID,
            aws_secret_key: config.aws_secret_key || process.env.AWS_SECRET_ACCESS_KEY,
            aws_region: config.aws_region || process.env.AWS_REGION || 'us-east-1',
            output_directory: config.output_directory || './output/audio',
            temp_directory: config.temp_directory || './temp/audio',
            default_provider: config.default_provider || 'openai', // openai, google, aws
            quality: config.quality || 'standard', // standard, hd
            audio_format: config.audio_format || 'mp3',
            sample_rate: config.sample_rate || 22050,
            ...config
        };

        this.synthesisTasks = new Map();
        this.voiceProfiles = new Map();
        this.audioCache = new Map();

        // Initialize TTS providers
        this.initializeProviders();
        this.setupVoiceProfiles();
        this.ensureDirectories();
    }

    async initializeProviders() {
        try {
            // OpenAI
            if (this.config.openai_api_key) {
                this.openai = new OpenAI({
                    apiKey: this.config.openai_api_key
                });
            }

            // Google Cloud TTS
            if (this.config.google_credentials) {
                this.googleTTS = new textToSpeech.TextToSpeechClient({
                    keyFilename: this.config.google_credentials
                });
            }

            // AWS Polly
            if (this.config.aws_access_key && this.config.aws_secret_key) {
                AWS.config.update({
                    accessKeyId: this.config.aws_access_key,
                    secretAccessKey: this.config.aws_secret_key,
                    region: this.config.aws_region
                });
                this.polly = new AWS.Polly();
            }

            this.emit('providers-initialized');
        } catch (error) {
            this.emit('error', { type: 'provider-initialization', error });
            throw error;
        }
    }

    setupVoiceProfiles() {
        // Define voice profiles for different roles and characteristics
        this.voiceProfiles.set('host_male_professional', {
            provider: 'openai',
            voice: 'nova',
            characteristics: {
                gender: 'male',
                age: 'adult',
                tone: 'professional',
                accent: 'american',
                pace: 'moderate',
                pitch: 'medium'
            },
            settings: {
                speed: 1.0,
                stability: 0.8,
                clarity: 0.9
            }
        });

        this.voiceProfiles.set('host_female_warm', {
            provider: 'openai',
            voice: 'alloy',
            characteristics: {
                gender: 'female',
                age: 'adult',
                tone: 'warm',
                accent: 'american',
                pace: 'moderate',
                pitch: 'medium'
            },
            settings: {
                speed: 1.0,
                stability: 0.8,
                clarity: 0.9
            }
        });

        this.voiceProfiles.set('expert_male_authoritative', {
            provider: 'google',
            voice: 'en-US-Neural2-J',
            characteristics: {
                gender: 'male',
                age: 'mature',
                tone: 'authoritative',
                accent: 'american',
                pace: 'slow',
                pitch: 'low'
            },
            settings: {
                speed: 0.9,
                pitch: -2.0,
                volumeGainDb: 2.0
            }
        });

        this.voiceProfiles.set('expert_female_confident', {
            provider: 'google',
            voice: 'en-US-Neural2-F',
            characteristics: {
                gender: 'female',
                age: 'adult',
                tone: 'confident',
                accent: 'american',
                pace: 'moderate',
                pitch: 'medium'
            },
            settings: {
                speed: 1.0,
                pitch: 0.0,
                volumeGainDb: 1.0
            }
        });

        this.voiceProfiles.set('narrator_neutral', {
            provider: 'aws',
            voice: 'Matthew',
            characteristics: {
                gender: 'male',
                age: 'adult',
                tone: 'neutral',
                accent: 'american',
                pace: 'moderate',
                pitch: 'medium'
            },
            settings: {
                rate: 'medium',
                volume: 'medium',
                pitch: 'medium'
            }
        });

        this.voiceProfiles.set('comedian_male_energetic', {
            provider: 'openai',
            voice: 'onyx',
            characteristics: {
                gender: 'male',
                age: 'young_adult',
                tone: 'energetic',
                accent: 'american',
                pace: 'fast',
                pitch: 'high'
            },
            settings: {
                speed: 1.1,
                stability: 0.6,
                clarity: 0.8
            }
        });

        this.voiceProfiles.set('comedian_female_playful', {
            provider: 'openai',
            voice: 'shimmer',
            characteristics: {
                gender: 'female',
                age: 'young_adult',
                tone: 'playful',
                accent: 'american',
                pace: 'fast',
                pitch: 'high'
            },
            settings: {
                speed: 1.1,
                stability: 0.6,
                clarity: 0.8
            }
        });

        this.voiceProfiles.set('interviewer_professional', {
            provider: 'google',
            voice: 'en-US-Neural2-D',
            characteristics: {
                gender: 'male',
                age: 'adult',
                tone: 'professional',
                accent: 'american',
                pace: 'moderate',
                pitch: 'medium'
            },
            settings: {
                speed: 1.0,
                pitch: 0.0,
                volumeGainDb: 0.0
            }
        });

        this.voiceProfiles.set('advocate_passionate', {
            provider: 'aws',
            voice: 'Joanna',
            characteristics: {
                gender: 'female',
                age: 'adult',
                tone: 'passionate',
                accent: 'american',
                pace: 'fast',
                pitch: 'medium_high'
            },
            settings: {
                rate: 'fast',
                volume: 'loud',
                pitch: 'high'
            }
        });

        this.voiceProfiles.set('skeptic_analytical', {
            provider: 'aws',
            voice: 'Brian',
            characteristics: {
                gender: 'male',
                age: 'mature',
                tone: 'analytical',
                accent: 'british',
                pace: 'slow',
                pitch: 'low'
            },
            settings: {
                rate: 'slow',
                volume: 'medium',
                pitch: 'low'
            }
        });
    }

    async ensureDirectories() {
        try {
            await fs.mkdir(this.config.output_directory, { recursive: true });
            await fs.mkdir(this.config.temp_directory, { recursive: true });
        } catch (error) {
            this.emit('error', { type: 'directory-creation', error });
        }
    }

    async synthesizePodcast(dialogueScript, voiceAssignments, options = {}) {
        const taskId = uuidv4();
        
        try {
            this.emit('synthesis-started', { taskId, totalSegments: dialogueScript.segments.length });
            
            const synthesisTask = {
                id: taskId,
                status: 'processing',
                segments: [],
                audioFiles: [],
                startTime: Date.now(),
                progress: 0,
                totalSegments: dialogueScript.segments.length
            };
            
            this.synthesisTasks.set(taskId, synthesisTask);

            // Process each dialogue segment
            for (let i = 0; i < dialogueScript.segments.length; i++) {
                const segment = dialogueScript.segments[i];
                
                this.emit('segment-processing', {
                    taskId,
                    segmentIndex: i,
                    speaker: segment.speaker,
                    text: segment.text.substring(0, 100) + '...'
                });

                const audioFile = await this.synthesizeSegment(
                    segment,
                    voiceAssignments[segment.speaker],
                    { taskId, segmentIndex: i, ...options }
                );

                synthesisTask.segments.push({
                    index: i,
                    speaker: segment.speaker,
                    text: segment.text,
                    audioFile: audioFile,
                    duration: await this.getAudioDuration(audioFile)
                });

                synthesisTask.audioFiles.push(audioFile);
                synthesisTask.progress = ((i + 1) / dialogueScript.segments.length) * 100;
                
                this.emit('segment-completed', {
                    taskId,
                    segmentIndex: i,
                    progress: synthesisTask.progress
                });
            }

            // Combine all audio segments into final podcast
            const finalAudioPath = await this.combineAudioSegments(
                synthesisTask.audioFiles,
                taskId,
                options
            );

            synthesisTask.status = 'completed';
            synthesisTask.finalAudioPath = finalAudioPath;
            synthesisTask.completedAt = Date.now();
            synthesisTask.processingTime = synthesisTask.completedAt - synthesisTask.startTime;

            this.emit('synthesis-completed', {
                taskId,
                finalAudioPath,
                processingTime: synthesisTask.processingTime
            });

            return {
                taskId,
                finalAudioPath,
                segments: synthesisTask.segments,
                processingTime: synthesisTask.processingTime
            };

        } catch (error) {
            const task = this.synthesisTasks.get(taskId);
            if (task) {
                task.status = 'failed';
                task.error = error.message;
            }
            
            this.emit('synthesis-failed', { taskId, error });
            throw error;
        }
    }

    async synthesizeSegment(segment, voiceProfileId, options = {}) {
        const cacheKey = this.generateCacheKey(segment.text, voiceProfileId);
        
        // Check cache first
        if (this.audioCache.has(cacheKey) && !options.forceRegenerate) {
            this.emit('cache-hit', { cacheKey, voiceProfileId });
            return this.audioCache.get(cacheKey);
        }

        const voiceProfile = this.voiceProfiles.get(voiceProfileId);
        if (!voiceProfile) {
            throw new Error(`Voice profile not found: ${voiceProfileId}`);
        }

        let audioFilePath;

        try {
            switch (voiceProfile.provider) {
                case 'openai':
                    audioFilePath = await this.synthesizeWithOpenAI(segment.text, voiceProfile, options);
                    break;
                case 'google':
                    audioFilePath = await this.synthesizeWithGoogle(segment.text, voiceProfile, options);
                    break;
                case 'aws':
                    audioFilePath = await this.synthesizeWithAWS(segment.text, voiceProfile, options);
                    break;
                default:
                    throw new Error(`Unsupported TTS provider: ${voiceProfile.provider}`);
            }

            // Cache the result
            this.audioCache.set(cacheKey, audioFilePath);
            
            this.emit('segment-synthesized', {
                taskId: options.taskId,
                segmentIndex: options.segmentIndex,
                voiceProfile: voiceProfileId,
                audioFile: audioFilePath
            });

            return audioFilePath;

        } catch (error) {
            this.emit('segment-synthesis-failed', {
                taskId: options.taskId,
                segmentIndex: options.segmentIndex,
                voiceProfile: voiceProfileId,
                error
            });
            throw error;
        }
    }

    async synthesizeWithOpenAI(text, voiceProfile, options = {}) {
        const filename = `openai_${Date.now()}_${Math.random().toString(36).substr(2, 9)}.mp3`;
        const outputPath = path.join(this.config.temp_directory, filename);

        const mp3 = await this.openai.audio.speech.create({
            model: this.config.quality === 'hd' ? 'tts-1-hd' : 'tts-1',
            voice: voiceProfile.voice,
            input: text,
            speed: voiceProfile.settings.speed || 1.0,
            response_format: 'mp3'
        });

        const buffer = Buffer.from(await mp3.arrayBuffer());
        await fs.writeFile(outputPath, buffer);

        return outputPath;
    }

    async synthesizeWithGoogle(text, voiceProfile, options = {}) {
        const filename = `google_${Date.now()}_${Math.random().toString(36).substr(2, 9)}.mp3`;
        const outputPath = path.join(this.config.temp_directory, filename);

        const request = {
            input: { text: text },
            voice: {
                languageCode: 'en-US',
                name: voiceProfile.voice
            },
            audioConfig: {
                audioEncoding: 'MP3',
                speakingRate: voiceProfile.settings.speed || 1.0,
                pitch: voiceProfile.settings.pitch || 0.0,
                volumeGainDb: voiceProfile.settings.volumeGainDb || 0.0,
                sampleRateHertz: this.config.sample_rate
            }
        };

        const [response] = await this.googleTTS.synthesizeSpeech(request);
        await fs.writeFile(outputPath, response.audioContent, 'binary');

        return outputPath;
    }

    async synthesizeWithAWS(text, voiceProfile, options = {}) {
        const filename = `aws_${Date.now()}_${Math.random().toString(36).substr(2, 9)}.mp3`;
        const outputPath = path.join(this.config.temp_directory, filename);

        const params = {
            Text: text,
            OutputFormat: 'mp3',
            VoiceId: voiceProfile.voice,
            SampleRate: this.config.sample_rate.toString(),
            TextType: 'text'
        };

        // Add SSML markup for advanced voice settings
        if (voiceProfile.settings.rate || voiceProfile.settings.volume || voiceProfile.settings.pitch) {
            let ssmlText = '<speak>';
            
            const prosodyAttrs = [];
            if (voiceProfile.settings.rate) prosodyAttrs.push(`rate="${voiceProfile.settings.rate}"`);
            if (voiceProfile.settings.volume) prosodyAttrs.push(`volume="${voiceProfile.settings.volume}"`);
            if (voiceProfile.settings.pitch) prosodyAttrs.push(`pitch="${voiceProfile.settings.pitch}"`);
            
            if (prosodyAttrs.length > 0) {
                ssmlText += `<prosody ${prosodyAttrs.join(' ')}>${text}</prosody>`;
            } else {
                ssmlText += text;
            }
            
            ssmlText += '</speak>';
            
            params.Text = ssmlText;
            params.TextType = 'ssml';
        }

        const result = await this.polly.synthesizeSpeech(params).promise();
        await fs.writeFile(outputPath, result.AudioStream);

        return outputPath;
    }

    async combineAudioSegments(audioFiles, taskId, options = {}) {
        const outputFilename = `podcast_${taskId}.${this.config.audio_format}`;
        const outputPath = path.join(this.config.output_directory, outputFilename);

        return new Promise((resolve, reject) => {
            let command = ffmpeg();

            // Add all audio files as inputs
            audioFiles.forEach(file => {
                command = command.input(file);
            });

            // Configure output
            command
                .complexFilter([
                    // Create silent gaps between segments
                    ...audioFiles.map((_, i) => `[${i}:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=stereo[a${i}]`),
                    // Add 0.5 second silence between segments
                    audioFiles.map((_, i) => i === 0 ? `[a0]` : `[silence][a${i}]concat=n=2:v=0:a=1`)
                        .join('[temp]; ') + '[final]'
                ])
                .outputOptions([
                    '-map', '[final]',
                    '-c:a', 'libmp3lame',
                    '-b:a', options.bitrate || '128k',
                    '-ar', this.config.sample_rate.toString(),
                    '-ac', '2'
                ])
                .output(outputPath)
                .on('start', (commandLine) => {
                    this.emit('audio-combining-started', { taskId, commandLine });
                })
                .on('progress', (progress) => {
                    this.emit('audio-combining-progress', { taskId, progress });
                })
                .on('end', () => {
                    this.emit('audio-combining-completed', { taskId, outputPath });
                    resolve(outputPath);
                })
                .on('error', (error) => {
                    this.emit('audio-combining-failed', { taskId, error });
                    reject(error);
                })
                .run();
        });
    }

    async addBackgroundMusic(podcastPath, musicPath, options = {}) {
        const outputPath = path.join(
            this.config.output_directory,
            `with_music_${path.basename(podcastPath)}`
        );

        const musicVolume = options.musicVolume || 0.1;
        const fadeIn = options.fadeIn || 3.0;
        const fadeOut = options.fadeOut || 3.0;

        return new Promise((resolve, reject) => {
            ffmpeg()
                .input(podcastPath)
                .input(musicPath)
                .complexFilter([
                    `[1:a]volume=${musicVolume}[music]`,
                    `[music]afade=t=in:ss=0:d=${fadeIn}[music_in]`,
                    `[music_in]afade=t=out:st=${options.duration - fadeOut}:d=${fadeOut}[music_final]`,
                    `[0:a][music_final]amix=inputs=2:duration=first[final]`
                ])
                .outputOptions([
                    '-map', '[final]',
                    '-c:a', 'libmp3lame',
                    '-b:a', '192k'
                ])
                .output(outputPath)
                .on('end', () => resolve(outputPath))
                .on('error', reject)
                .run();
        });
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

    generateCacheKey(text, voiceProfileId) {
        return `${voiceProfileId}_${Buffer.from(text).toString('base64').substring(0, 32)}`;
    }

    getVoiceProfiles() {
        return Array.from(this.voiceProfiles.keys()).map(key => ({
            id: key,
            ...this.voiceProfiles.get(key)
        }));
    }

    getSynthesisTask(taskId) {
        return this.synthesisTasks.get(taskId);
    }

    async cleanupTempFiles(taskId) {
        const task = this.synthesisTasks.get(taskId);
        if (!task) return;

        try {
            for (const audioFile of task.audioFiles) {
                if (audioFile.includes(this.config.temp_directory)) {
                    await fs.unlink(audioFile);
                }
            }
            this.emit('temp-files-cleaned', { taskId });
        } catch (error) {
            this.emit('cleanup-error', { taskId, error });
        }
    }

    async createVoiceClone(sampleAudioPath, voiceId, characteristics) {
        // Placeholder for voice cloning functionality
        // This would integrate with services like ElevenLabs or similar
        this.emit('voice-clone-requested', { sampleAudioPath, voiceId, characteristics });
        
        // For now, create a custom voice profile
        this.voiceProfiles.set(voiceId, {
            provider: 'custom',
            voice: voiceId,
            characteristics,
            samplePath: sampleAudioPath,
            settings: {
                speed: 1.0,
                stability: 0.8,
                clarity: 0.9
            }
        });
        
        return voiceId;
    }
}

export default VoiceSynthesizer;