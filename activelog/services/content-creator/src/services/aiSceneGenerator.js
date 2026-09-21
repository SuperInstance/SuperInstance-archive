const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const OpenAI = require('openai');
const fs = require('fs').promises;
const path = require('path');

class AISceneGenerator extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        this.openai = new OpenAI({
            apiKey: process.env.OPENAI_API_KEY || 'demo-key'
        });
        
        this.sceneTypes = {
            GAMEPLAY: 'gameplay',
            TUTORIAL: 'tutorial',
            CINEMATIC: 'cinematic',
            REVIEW: 'review',
            COMMENTARY: 'commentary',
            SHOWCASE: 'showcase',
            TRAILER: 'trailer',
            MONTAGE: 'montage'
        };
        
        this.scriptFormats = {
            STANDARD: 'standard',
            YOUTUBE: 'youtube',
            TIKTOK: 'tiktok',
            INSTAGRAM: 'instagram',
            TWITCH: 'twitch'
        };
        
        this.contentStyles = {
            ENERGETIC: 'energetic',
            INFORMATIVE: 'informative',
            CASUAL: 'casual',
            PROFESSIONAL: 'professional',
            HUMOROUS: 'humorous',
            DRAMATIC: 'dramatic'
        };
        
        this.setupEventListeners();
        this.logger.info('AI Scene Generator service initialized');
    }
    
    setupEventListeners() {
        this.on('scene_generated', (data) => {
            this.io.emit('scene_generated', data);
        });
        
        this.on('script_generated', (data) => {
            this.io.emit('script_generated', data);
        });
        
        this.on('generation_progress', (data) => {
            this.io.emit('ai_generation_progress', data);
        });
    }
    
    async generateScene(sceneData) {
        try {
            const sessionId = uuidv4();
            const {
                type,
                gameTitle,
                description,
                duration,
                style,
                targetPlatform,
                keyElements,
                mood,
                difficulty
            } = sceneData;
            
            this.emit('generation_progress', { sessionId, progress: 10, status: 'Analyzing requirements' });
            
            const scenePrompt = this.buildScenePrompt(sceneData);
            
            this.emit('generation_progress', { sessionId, progress: 30, status: 'Generating scene structure' });
            
            const sceneStructure = await this.generateSceneStructure(scenePrompt);
            
            this.emit('generation_progress', { sessionId, progress: 50, status: 'Creating shot breakdown' });
            
            const shotBreakdown = await this.generateShotBreakdown(sceneStructure, sceneData);
            
            this.emit('generation_progress', { sessionId, progress: 70, status: 'Generating camera directions' });
            
            const cameraDirections = await this.generateCameraDirections(shotBreakdown);
            
            this.emit('generation_progress', { sessionId, progress: 90, status: 'Finalizing scene' });
            
            const scene = {
                id: sessionId,
                type: type || this.sceneTypes.GAMEPLAY,
                gameTitle: gameTitle || 'Unknown Game',
                title: sceneStructure.title,
                description: description,
                duration: duration || 60,
                style: style || this.contentStyles.ENERGETIC,
                targetPlatform: targetPlatform || 'youtube',
                structure: sceneStructure,
                shots: shotBreakdown,
                cameraWork: cameraDirections,
                metadata: {
                    created: new Date(),
                    aiModel: 'gpt-4',
                    complexity: this.calculateComplexity(shotBreakdown),
                    estimatedRenderTime: this.estimateRenderTime(shotBreakdown)
                },
                assets: {
                    required: this.extractRequiredAssets(shotBreakdown),
                    optional: this.extractOptionalAssets(shotBreakdown)
                }
            };
            
            await this.redis.setEx(`ai_scene:${sessionId}`, 3600, JSON.stringify(scene));
            
            this.emit('generation_progress', { sessionId, progress: 100, status: 'Scene generation complete' });
            this.emit('scene_generated', { sessionId, scene });
            
            this.logger.info(`AI scene generated: ${sessionId} for ${gameTitle}`);
            
            return { success: true, sessionId, scene };
        } catch (error) {
            this.logger.error('Generate scene error:', error);
            throw error;
        }
    }
    
    buildScenePrompt(sceneData) {
        const {
            type,
            gameTitle,
            description,
            duration,
            style,
            targetPlatform,
            keyElements,
            mood
        } = sceneData;
        
        return `Create a ${type} scene for ${gameTitle} content creation:
        
        Context:
        - Game: ${gameTitle}
        - Scene Type: ${type}
        - Duration: ${duration} seconds
        - Style: ${style}
        - Target Platform: ${targetPlatform}
        - Mood: ${mood || 'engaging'}
        - Description: ${description || 'No specific description provided'}
        
        Key Elements to Include:
        ${keyElements ? keyElements.map(element => `- ${element}`).join('\n') : '- Dynamic gameplay moments\n- Clear visual storytelling'}
        
        Requirements:
        - Create compelling visual narrative
        - Optimize for ${targetPlatform} audience
        - Maintain ${style} tone throughout
        - Include specific camera angles and movements
        - Suggest timing and pacing
        - Consider audio/music cues
        
        Please provide a structured scene breakdown with:
        1. Overall concept and hook
        2. Three-act structure (setup, action, resolution)
        3. Key moments and transitions
        4. Visual style guidelines
        5. Platform-specific optimizations`;
    }
    
    async generateSceneStructure(prompt) {
        try {
            const completion = await this.openai.chat.completions.create({
                model: 'gpt-4',
                messages: [
                    {
                        role: 'system',
                        content: 'You are an expert video content creator and cinematographer specializing in gaming content. Provide detailed, actionable scene structures optimized for social media platforms.'
                    },
                    {
                        role: 'user',
                        content: prompt
                    }
                ],
                max_tokens: 1500,
                temperature: 0.8
            });
            
            const response = completion.choices[0].message.content;
            
            // Parse the AI response into structured data
            return {
                title: this.extractTitle(response),
                concept: this.extractConcept(response),
                structure: {
                    setup: this.extractSection(response, 'setup'),
                    action: this.extractSection(response, 'action'),
                    resolution: this.extractSection(response, 'resolution')
                },
                keyMoments: this.extractKeyMoments(response),
                visualStyle: this.extractVisualStyle(response),
                platformOptimizations: this.extractPlatformOptimizations(response)
            };
        } catch (error) {
            this.logger.error('Generate scene structure error:', error);
            
            // Fallback structure
            return {
                title: 'AI-Generated Scene',
                concept: 'Dynamic gaming content with engaging visuals',
                structure: {
                    setup: 'Introduction and context establishment',
                    action: 'Main gameplay or content showcase',
                    resolution: 'Conclusion and call-to-action'
                },
                keyMoments: ['Opening hook', 'Climax moment', 'Resolution'],
                visualStyle: 'Dynamic and engaging',
                platformOptimizations: ['Vertical format ready', 'Quick pacing', 'Clear visuals']
            };
        }
    }
    
    async generateShotBreakdown(sceneStructure, sceneData) {
        try {
            const shotPrompt = `Based on this scene structure, create a detailed shot-by-shot breakdown:
            
            Title: ${sceneStructure.title}
            Concept: ${sceneStructure.concept}
            Duration: ${sceneData.duration} seconds
            Platform: ${sceneData.targetPlatform}
            
            Structure:
            - Setup: ${sceneStructure.structure.setup}
            - Action: ${sceneStructure.structure.action}
            - Resolution: ${sceneStructure.structure.resolution}
            
            Create 6-12 shots with:
            - Shot number and duration
            - Camera angle and movement
            - Action description
            - Audio/music notes
            - Transition type
            - Any special effects or editing notes`;
            
            const completion = await this.openai.chat.completions.create({
                model: 'gpt-4',
                messages: [
                    {
                        role: 'system',
                        content: 'You are a professional video editor creating shot lists for gaming content. Provide specific, technical shot breakdowns that editors can follow.'
                    },
                    {
                        role: 'user',
                        content: shotPrompt
                    }
                ],
                max_tokens: 2000,
                temperature: 0.7
            });
            
            return this.parseShotBreakdown(completion.choices[0].message.content, sceneData.duration);
        } catch (error) {
            this.logger.error('Generate shot breakdown error:', error);
            
            // Fallback shot breakdown
            return this.createFallbackShotBreakdown(sceneData.duration);
        }
    }
    
    async generateCameraDirections(shotBreakdown) {
        try {
            const cameraPrompt = `Create detailed camera directions for these shots:
            
            ${shotBreakdown.map((shot, i) => `Shot ${i + 1}: ${shot.description} (${shot.duration}s)`).join('\n')}
            
            For each shot, provide:
            - Specific camera position and angle
            - Movement type and speed
            - Focus points and depth of field
            - Lighting considerations
            - Game engine camera settings if applicable`;
            
            const completion = await this.openai.chat.completions.create({
                model: 'gpt-4',
                messages: [
                    {
                        role: 'system',
                        content: 'You are a professional cinematographer specializing in virtual camera work and game engine cinematography. Provide technical, actionable camera directions.'
                    },
                    {
                        role: 'user',
                        content: cameraPrompt
                    }
                ],
                max_tokens: 1500,
                temperature: 0.6
            });
            
            return this.parseCameraDirections(completion.choices[0].message.content);
        } catch (error) {
            this.logger.error('Generate camera directions error:', error);
            
            // Fallback camera directions
            return shotBreakdown.map((_, i) => ({
                shotNumber: i + 1,
                position: 'Medium shot',
                movement: 'Static',
                focusPoint: 'Subject center',
                settings: 'Standard game camera'
            }));
        }
    }
    
    async generateScript(scriptData) {
        try {
            const sessionId = uuidv4();
            const {
                format,
                duration,
                topic,
                style,
                targetAudience,
                keyPoints,
                callToAction
            } = scriptData;
            
            const scriptPrompt = `Write a ${format} script for gaming content:
            
            Topic: ${topic}
            Duration: ${duration} seconds
            Style: ${style}
            Target Audience: ${targetAudience}
            Format: ${format}
            
            Key Points to Cover:
            ${keyPoints ? keyPoints.map(point => `- ${point}`).join('\n') : '- Main gameplay features\n- Tips and strategies'}
            
            Call to Action: ${callToAction || 'Like and subscribe for more content'}
            
            Requirements:
            - Engaging hook in first 5 seconds
            - Clear, conversational tone
            - Platform-optimized pacing
            - Natural transitions
            - Strong ending with CTA
            
            Format as:
            [TIMESTAMP] SPEAKER: Dialogue
            [TIMESTAMP] ACTION: Stage direction
            [TIMESTAMP] VISUAL: Visual cue`;
            
            const completion = await this.openai.chat.completions.create({
                model: 'gpt-4',
                messages: [
                    {
                        role: 'system',
                        content: 'You are an expert script writer for gaming content creators. Write engaging, platform-optimized scripts that drive viewer engagement.'
                    },
                    {
                        role: 'user',
                        content: scriptPrompt
                    }
                ],
                max_tokens: 2000,
                temperature: 0.8
            });
            
            const script = {
                id: sessionId,
                format: format || this.scriptFormats.YOUTUBE,
                topic: topic,
                duration: duration || 60,
                style: style || this.contentStyles.ENERGETIC,
                content: completion.choices[0].message.content,
                metadata: {
                    created: new Date(),
                    wordCount: this.countWords(completion.choices[0].message.content),
                    estimatedReadingTime: this.estimateReadingTime(completion.choices[0].message.content)
                },
                segments: this.parseScriptSegments(completion.choices[0].message.content),
                cues: this.extractScriptCues(completion.choices[0].message.content)
            };
            
            await this.redis.setEx(`ai_script:${sessionId}`, 3600, JSON.stringify(script));
            
            this.emit('script_generated', { sessionId, script });
            this.logger.info(`AI script generated: ${sessionId} for ${topic}`);
            
            return { success: true, sessionId, script };
        } catch (error) {
            this.logger.error('Generate script error:', error);
            throw error;
        }
    }
    
    // Utility methods for parsing AI responses
    extractTitle(response) {
        const titleMatch = response.match(/title:?\s*([^\n]+)/i);
        return titleMatch ? titleMatch[1].trim() : 'AI-Generated Scene';
    }
    
    extractConcept(response) {
        const conceptMatch = response.match(/concept:?\s*([^\n]+)/i);
        return conceptMatch ? conceptMatch[1].trim() : 'Engaging gaming content';
    }
    
    extractSection(response, section) {
        const regex = new RegExp(`${section}:?\\s*([^\\n]+)`, 'i');
        const match = response.match(regex);
        return match ? match[1].trim() : `${section} section`;
    }
    
    extractKeyMoments(response) {
        const moments = [];
        const lines = response.split('\n');
        for (const line of lines) {
            if (line.includes('moment') || line.includes('key') || line.includes('highlight')) {
                moments.push(line.replace(/[^\w\s]/g, '').trim());
            }
        }
        return moments.slice(0, 5);
    }
    
    extractVisualStyle(response) {
        const styleMatch = response.match(/visual\s+style:?\s*([^\n]+)/i);
        return styleMatch ? styleMatch[1].trim() : 'Dynamic and cinematic';
    }
    
    extractPlatformOptimizations(response) {
        const optimizations = [];
        const lines = response.split('\n');
        for (const line of lines) {
            if (line.includes('platform') || line.includes('optimization') || line.includes('format')) {
                optimizations.push(line.replace(/[^\w\s]/g, '').trim());
            }
        }
        return optimizations.slice(0, 3);
    }
    
    parseShotBreakdown(content, totalDuration) {
        const shots = [];
        const lines = content.split('\n');
        let currentShot = null;
        let shotDuration = Math.floor(totalDuration / 8); // Default shot length
        
        for (const line of lines) {
            if (line.match(/shot\s+\d+/i)) {
                if (currentShot) shots.push(currentShot);
                
                currentShot = {
                    id: uuidv4(),
                    number: shots.length + 1,
                    duration: shotDuration,
                    description: line.trim(),
                    cameraAngle: 'Medium shot',
                    movement: 'Static',
                    transition: 'Cut',
                    audio: 'Game audio',
                    effects: []
                };
            } else if (currentShot && line.trim()) {
                if (line.includes('camera') || line.includes('angle')) {
                    currentShot.cameraAngle = line.trim();
                } else if (line.includes('movement') || line.includes('pan') || line.includes('zoom')) {
                    currentShot.movement = line.trim();
                } else if (line.includes('transition') || line.includes('cut') || line.includes('fade')) {
                    currentShot.transition = line.trim();
                } else if (line.includes('audio') || line.includes('music') || line.includes('sound')) {
                    currentShot.audio = line.trim();
                }
            }
        }
        
        if (currentShot) shots.push(currentShot);
        
        // Ensure shots total the correct duration
        const actualTotal = shots.reduce((sum, shot) => sum + shot.duration, 0);
        if (actualTotal !== totalDuration) {
            const adjustment = (totalDuration - actualTotal) / shots.length;
            shots.forEach(shot => shot.duration += adjustment);
        }
        
        return shots.length > 0 ? shots : this.createFallbackShotBreakdown(totalDuration);
    }
    
    createFallbackShotBreakdown(duration) {
        const shotCount = Math.max(3, Math.min(8, Math.floor(duration / 10)));
        const shotDuration = duration / shotCount;
        
        return Array.from({ length: shotCount }, (_, i) => ({
            id: uuidv4(),
            number: i + 1,
            duration: shotDuration,
            description: `Shot ${i + 1}: Dynamic gameplay moment`,
            cameraAngle: ['Wide shot', 'Medium shot', 'Close-up'][i % 3],
            movement: ['Static', 'Pan left', 'Zoom in'][i % 3],
            transition: 'Cut',
            audio: 'Game audio with background music',
            effects: []
        }));
    }
    
    parseCameraDirections(content) {
        const directions = [];
        const lines = content.split('\n');
        let currentDirection = null;
        
        for (const line of lines) {
            if (line.match(/shot\s+\d+/i)) {
                if (currentDirection) directions.push(currentDirection);
                
                currentDirection = {
                    shotNumber: directions.length + 1,
                    position: 'Medium shot',
                    movement: 'Static',
                    focusPoint: 'Center',
                    settings: 'Standard'
                };
            } else if (currentDirection && line.trim()) {
                if (line.includes('position') || line.includes('angle')) {
                    currentDirection.position = line.trim();
                } else if (line.includes('movement') || line.includes('pan') || line.includes('track')) {
                    currentDirection.movement = line.trim();
                } else if (line.includes('focus') || line.includes('depth')) {
                    currentDirection.focusPoint = line.trim();
                } else if (line.includes('settings') || line.includes('camera')) {
                    currentDirection.settings = line.trim();
                }
            }
        }
        
        if (currentDirection) directions.push(currentDirection);
        
        return directions;
    }
    
    parseScriptSegments(content) {
        const segments = [];
        const lines = content.split('\n');
        
        for (const line of lines) {
            const timestampMatch = line.match(/\[(\d+:\d+|\d+)\]/);
            if (timestampMatch) {
                const timeStr = timestampMatch[1];
                const time = timeStr.includes(':') ? 
                    parseInt(timeStr.split(':')[0]) * 60 + parseInt(timeStr.split(':')[1]) :
                    parseInt(timeStr);
                
                segments.push({
                    timestamp: time,
                    content: line.replace(/\[\d+:?\d*\]/, '').trim()
                });
            }
        }
        
        return segments;
    }
    
    extractScriptCues(content) {
        const cues = {
            visual: [],
            audio: [],
            action: []
        };
        
        const lines = content.split('\n');
        for (const line of lines) {
            if (line.includes('VISUAL:')) {
                cues.visual.push(line.replace('VISUAL:', '').trim());
            } else if (line.includes('ACTION:')) {
                cues.action.push(line.replace('ACTION:', '').trim());
            } else if (line.includes('AUDIO:') || line.includes('MUSIC:')) {
                cues.audio.push(line.replace(/AUDIO:|MUSIC:/, '').trim());
            }
        }
        
        return cues;
    }
    
    calculateComplexity(shots) {
        let complexity = 0;
        for (const shot of shots) {
            if (shot.movement !== 'Static') complexity += 1;
            if (shot.effects && shot.effects.length > 0) complexity += shot.effects.length;
            if (shot.transition !== 'Cut') complexity += 1;
        }
        return complexity > 10 ? 'High' : complexity > 5 ? 'Medium' : 'Low';
    }
    
    estimateRenderTime(shots) {
        const baseTime = shots.length * 2; // 2 minutes per shot base
        const complexityMultiplier = shots.reduce((mult, shot) => {
            let shotMult = 1;
            if (shot.movement !== 'Static') shotMult *= 1.5;
            if (shot.effects && shot.effects.length > 0) shotMult *= (1 + shot.effects.length * 0.3);
            return mult + shotMult;
        }, 0) / shots.length;
        
        return Math.round(baseTime * complexityMultiplier);
    }
    
    extractRequiredAssets(shots) {
        const assets = new Set();
        for (const shot of shots) {
            if (shot.description.includes('gameplay')) assets.add('gameplay_footage');
            if (shot.description.includes('UI') || shot.description.includes('interface')) assets.add('ui_elements');
            if (shot.description.includes('character')) assets.add('character_models');
            if (shot.description.includes('environment')) assets.add('environment_assets');
        }
        return Array.from(assets);
    }
    
    extractOptionalAssets(shots) {
        const assets = new Set();
        for (const shot of shots) {
            if (shot.description.includes('effect')) assets.add('visual_effects');
            if (shot.description.includes('particle')) assets.add('particle_systems');
            if (shot.description.includes('animation')) assets.add('custom_animations');
            if (shot.description.includes('overlay')) assets.add('overlay_graphics');
        }
        return Array.from(assets);
    }
    
    countWords(text) {
        return text.split(/\s+/).filter(word => word.length > 0).length;
    }
    
    estimateReadingTime(text) {
        const wordsPerMinute = 150;
        const wordCount = this.countWords(text);
        return Math.ceil(wordCount / wordsPerMinute);
    }
    
    async getStats() {
        try {
            const stats = {
                sceneTypes: this.sceneTypes,
                scriptFormats: this.scriptFormats,
                contentStyles: this.contentStyles,
                totalScenesGenerated: await this.getTotalGenerated('ai_scene'),
                totalScriptsGenerated: await this.getTotalGenerated('ai_script'),
                timestamp: new Date()
            };
            
            return stats;
        } catch (error) {
            this.logger.error('Get stats error:', error);
            throw error;
        }
    }
    
    async getTotalGenerated(prefix) {
        try {
            const keys = await this.redis.keys(`${prefix}:*`);
            return keys.length;
        } catch (error) {
            return 0;
        }
    }
}

module.exports = AISceneGenerator;