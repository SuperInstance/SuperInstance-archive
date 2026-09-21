import { EventEmitter } from 'events';
import OpenAI from 'openai';
import fs from 'fs/promises';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

class SegmentRegenerator extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            openai_api_key: config.openai_api_key || process.env.OPENAI_API_KEY,
            model: config.model || 'gpt-4',
            regeneration_history_directory: config.regeneration_history_directory || './data/regeneration_history',
            max_regeneration_attempts: config.max_regeneration_attempts || 5,
            quality_threshold: config.quality_threshold || 0.7,
            ...config
        };

        this.openai = new OpenAI({
            apiKey: this.config.openai_api_key
        });

        this.regenerationTasks = new Map();
        this.regenerationHistory = new Map();
        this.qualityMetrics = new Map();
        this.regenerationStrategies = new Map();

        this.initializeRegenerationStrategies();
        this.ensureDirectories();
    }

    async ensureDirectories() {
        try {
            await fs.mkdir(this.config.regeneration_history_directory, { recursive: true });
        } catch (error) {
            this.emit('error', { type: 'directory-creation', error });
        }
    }

    initializeRegenerationStrategies() {
        // Different strategies for regenerating segments based on issues
        this.regenerationStrategies.set('improve_clarity', {
            name: 'Improve Clarity',
            description: 'Make the segment clearer and easier to understand',
            prompts: {
                system: 'Rewrite this podcast segment to be clearer and easier to understand. Focus on simplifying complex ideas without losing important information.',
                user_template: 'Original segment: {original_text}\n\nMake this clearer and more accessible while maintaining the speaker\'s voice and style.'
            },
            parameters: {
                temperature: 0.6,
                focus_areas: ['simplification', 'clarity', 'accessibility']
            }
        });

        this.regenerationStrategies.set('enhance_engagement', {
            name: 'Enhance Engagement',
            description: 'Make the segment more engaging and interesting',
            prompts: {
                system: 'Rewrite this podcast segment to be more engaging and captivating. Add energy, interesting examples, or compelling storytelling elements.',
                user_template: 'Original segment: {original_text}\n\nMake this more engaging and interesting while preserving the core message and information.'
            },
            parameters: {
                temperature: 0.8,
                focus_areas: ['engagement', 'storytelling', 'energy']
            }
        });

        this.regenerationStrategies.set('fix_accuracy', {
            name: 'Fix Accuracy Issues',
            description: 'Correct factual errors or improve accuracy',
            prompts: {
                system: 'Review and correct this podcast segment for factual accuracy. Fix any errors while maintaining the conversational tone.',
                user_template: 'Original segment: {original_text}\n\nCorrect any factual errors and improve accuracy. If corrections are made, explain what was changed.'
            },
            parameters: {
                temperature: 0.3,
                focus_areas: ['accuracy', 'fact_checking', 'precision']
            }
        });

        this.regenerationStrategies.set('adjust_tone', {
            name: 'Adjust Tone',
            description: 'Change the tone to better match the desired style',
            prompts: {
                system: 'Adjust the tone of this podcast segment to match the specified style and mood.',
                user_template: 'Original segment: {original_text}\n\nTarget tone: {target_tone}\n\nRewrite to match this tone while preserving the information.'
            },
            parameters: {
                temperature: 0.7,
                focus_areas: ['tone', 'style', 'mood']
            }
        });

        this.regenerationStrategies.set('improve_flow', {
            name: 'Improve Flow',
            description: 'Better integrate with surrounding segments',
            prompts: {
                system: 'Improve the flow and transitions in this podcast segment to better connect with the surrounding content.',
                user_template: 'Previous segment: {previous_segment}\n\nCurrent segment: {original_text}\n\nNext segment: {next_segment}\n\nRewrite the current segment to flow better with its context.'
            },
            parameters: {
                temperature: 0.6,
                focus_areas: ['flow', 'transitions', 'continuity']
            }
        });

        this.regenerationStrategies.set('add_personality', {
            name: 'Add Personality',
            description: 'Inject more personality and character voice',
            prompts: {
                system: 'Rewrite this podcast segment to better reflect the speaker\'s personality and unique voice characteristics.',
                user_template: 'Speaker: {speaker_name}\nPersonality traits: {personality_traits}\nSpeaking style: {speaking_style}\n\nOriginal segment: {original_text}\n\nRewrite to better reflect this speaker\'s personality.'
            },
            parameters: {
                temperature: 0.8,
                focus_areas: ['personality', 'voice', 'character']
            }
        });

        this.regenerationStrategies.set('expand_detail', {
            name: 'Expand Detail',
            description: 'Add more detail and depth to the content',
            prompts: {
                system: 'Expand this podcast segment with more detail, examples, and depth while maintaining conversational flow.',
                user_template: 'Original segment: {original_text}\n\nExpand with more detail, examples, or explanations. Focus on: {focus_areas}'
            },
            parameters: {
                temperature: 0.7,
                focus_areas: ['detail', 'examples', 'depth']
            }
        });

        this.regenerationStrategies.set('condense_content', {
            name: 'Condense Content',
            description: 'Make the segment more concise while preserving key points',
            prompts: {
                system: 'Condense this podcast segment to be more concise while preserving all key information and maintaining natural flow.',
                user_template: 'Original segment: {original_text}\n\nMake this more concise while keeping all important information.'
            },
            parameters: {
                temperature: 0.5,
                focus_areas: ['conciseness', 'efficiency', 'key_points']
            }
        });

        this.regenerationStrategies.set('fix_dialogue', {
            name: 'Fix Dialogue Issues',
            description: 'Improve dialogue naturalness and authenticity',
            prompts: {
                system: 'Improve the dialogue in this podcast segment to sound more natural and authentic for the speakers involved.',
                user_template: 'Speakers: {speakers}\nOriginal segment: {original_text}\n\nMake the dialogue sound more natural and authentic for these speakers.'
            },
            parameters: {
                temperature: 0.7,
                focus_areas: ['dialogue', 'naturalness', 'authenticity']
            }
        });

        this.regenerationStrategies.set('creative_rewrite', {
            name: 'Creative Rewrite',
            description: 'Completely reimagine the segment with creative approaches',
            prompts: {
                system: 'Creatively rewrite this podcast segment using innovative approaches while preserving the core message.',
                user_template: 'Original segment: {original_text}\n\nCore message to preserve: {core_message}\n\nCreatively rewrite this segment with a fresh approach.'
            },
            parameters: {
                temperature: 0.9,
                focus_areas: ['creativity', 'innovation', 'fresh_perspective']
            }
        });
    }

    async regenerateSegment(script, segmentIndex, regenerationRequest) {
        const taskId = uuidv4();
        
        try {
            this.emit('regeneration-started', { taskId, segmentIndex });

            const {
                strategy,
                custom_instructions,
                target_tone,
                focus_areas,
                preserve_elements,
                quality_criteria
            } = regenerationRequest;

            if (segmentIndex < 0 || segmentIndex >= script.segments.length) {
                throw new Error(`Invalid segment index: ${segmentIndex}`);
            }

            const originalSegment = script.segments[segmentIndex];
            const regenerationStrategy = this.regenerationStrategies.get(strategy);

            if (!regenerationStrategy) {
                throw new Error(`Unknown regeneration strategy: ${strategy}`);
            }

            // Create regeneration task
            const regenerationTask = {
                id: taskId,
                script_id: script.metadata?.id || 'unknown',
                segment_index: segmentIndex,
                original_segment: { ...originalSegment },
                strategy: strategy,
                custom_instructions: custom_instructions,
                target_tone: target_tone,
                focus_areas: focus_areas || regenerationStrategy.parameters.focus_areas,
                preserve_elements: preserve_elements || [],
                quality_criteria: quality_criteria || {},
                started_at: new Date().toISOString(),
                status: 'processing',
                attempts: [],
                current_attempt: 0
            };

            this.regenerationTasks.set(taskId, regenerationTask);

            // Generate context for better regeneration
            const context = await this.buildRegenerationContext(script, segmentIndex, regenerationRequest);

            // Attempt regeneration with quality validation
            const result = await this.performRegenerationWithQualityCheck(
                regenerationTask,
                regenerationStrategy,
                context
            );

            // Update the script with the new segment
            script.segments[segmentIndex] = {
                ...originalSegment,
                ...result.final_segment,
                regenerated: true,
                regeneration_info: {
                    task_id: taskId,
                    strategy: strategy,
                    regenerated_at: new Date().toISOString(),
                    attempts: result.attempts_made,
                    quality_score: result.quality_score
                }
            };

            // Save regeneration history
            await this.saveRegenerationHistory(taskId, regenerationTask, result);

            regenerationTask.status = 'completed';
            regenerationTask.completed_at = new Date().toISOString();
            regenerationTask.result = result;

            this.emit('regeneration-completed', {
                taskId,
                segmentIndex,
                strategy,
                qualityScore: result.quality_score,
                attemptsUsed: result.attempts_made
            });

            return {
                task_id: taskId,
                regenerated_segment: script.segments[segmentIndex],
                quality_score: result.quality_score,
                attempts_made: result.attempts_made,
                improvements: result.improvements
            };

        } catch (error) {
            const task = this.regenerationTasks.get(taskId);
            if (task) {
                task.status = 'failed';
                task.error = error.message;
            }
            
            this.emit('regeneration-failed', { taskId, segmentIndex, error });
            throw error;
        }
    }

    async buildRegenerationContext(script, segmentIndex, regenerationRequest) {
        const segments = script.segments;
        const targetSegment = segments[segmentIndex];

        const context = {
            podcast_metadata: script.metadata || {},
            target_segment: targetSegment,
            segment_index: segmentIndex,
            total_segments: segments.length
        };

        // Add surrounding context
        if (segmentIndex > 0) {
            context.previous_segment = segments[segmentIndex - 1];
        }
        
        if (segmentIndex < segments.length - 1) {
            context.next_segment = segments[segmentIndex + 1];
        }

        // Add speaker context
        if (script.participants && targetSegment.speaker) {
            context.speaker_info = script.participants[targetSegment.speaker];
        }

        // Add conversation flow context
        const speakerSegments = segments.filter(s => s.speaker === targetSegment.speaker);
        context.speaker_conversation_flow = speakerSegments.slice(
            Math.max(0, speakerSegments.indexOf(targetSegment) - 2),
            speakerSegments.indexOf(targetSegment) + 3
        );

        // Add thematic context
        context.podcast_themes = await this.extractPodcastThemes(script);
        context.segment_themes = await this.extractSegmentThemes(targetSegment);

        return context;
    }

    async extractPodcastThemes(script) {
        const allText = script.segments.map(s => s.text).join(' ');
        
        try {
            const completion = await this.openai.chat.completions.create({
                model: 'gpt-3.5-turbo',
                messages: [
                    {
                        role: 'system',
                        content: 'Extract the main themes and topics from this podcast script. Return a JSON array of theme strings.'
                    },
                    {
                        role: 'user',
                        content: allText.substring(0, 2000) // Limit for efficiency
                    }
                ],
                temperature: 0.3,
                max_tokens: 200
            });

            return JSON.parse(completion.choices[0].message.content);
        } catch (error) {
            return ['general discussion'];
        }
    }

    async extractSegmentThemes(segment) {
        try {
            const completion = await this.openai.chat.completions.create({
                model: 'gpt-3.5-turbo',
                messages: [
                    {
                        role: 'system',
                        content: 'Extract the main topics and themes from this podcast segment. Return a JSON array of theme strings.'
                    },
                    {
                        role: 'user',
                        content: segment.text
                    }
                ],
                temperature: 0.3,
                max_tokens: 100
            });

            return JSON.parse(completion.choices[0].message.content);
        } catch (error) {
            return ['discussion'];
        }
    }

    async performRegenerationWithQualityCheck(regenerationTask, strategy, context) {
        let bestAttempt = null;
        let bestQualityScore = 0;
        const maxAttempts = this.config.max_regeneration_attempts;

        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            regenerationTask.current_attempt = attempt;
            
            this.emit('regeneration-attempt', {
                taskId: regenerationTask.id,
                attempt: attempt,
                maxAttempts: maxAttempts
            });

            try {
                // Generate new segment content
                const newSegment = await this.generateSegmentContent(
                    regenerationTask,
                    strategy,
                    context,
                    attempt
                );

                // Evaluate quality
                const qualityScore = await this.evaluateRegeneratedSegment(
                    regenerationTask.original_segment,
                    newSegment,
                    regenerationTask,
                    context
                );

                const attemptRecord = {
                    attempt: attempt,
                    generated_segment: newSegment,
                    quality_score: qualityScore,
                    generated_at: new Date().toISOString()
                };

                regenerationTask.attempts.push(attemptRecord);

                // Check if this is the best attempt so far
                if (qualityScore > bestQualityScore) {
                    bestQualityScore = qualityScore;
                    bestAttempt = attemptRecord;
                }

                // Check if quality threshold is met
                if (qualityScore >= this.config.quality_threshold) {
                    break;
                }

            } catch (error) {
                regenerationTask.attempts.push({
                    attempt: attempt,
                    error: error.message,
                    generated_at: new Date().toISOString()
                });

                this.emit('regeneration-attempt-failed', {
                    taskId: regenerationTask.id,
                    attempt: attempt,
                    error
                });
            }
        }

        if (!bestAttempt) {
            throw new Error('All regeneration attempts failed');
        }

        // Analyze improvements made
        const improvements = await this.analyzeImprovements(
            regenerationTask.original_segment,
            bestAttempt.generated_segment,
            regenerationTask.strategy
        );

        return {
            final_segment: bestAttempt.generated_segment,
            quality_score: bestQualityScore,
            attempts_made: regenerationTask.attempts.length,
            improvements: improvements
        };
    }

    async generateSegmentContent(regenerationTask, strategy, context, attemptNumber) {
        const promptData = this.buildPromptData(regenerationTask, context, attemptNumber);
        const systemPrompt = strategy.prompts.system;
        const userPrompt = this.populatePromptTemplate(strategy.prompts.user_template, promptData);

        // Add custom instructions if provided
        const enhancedUserPrompt = regenerationTask.custom_instructions 
            ? `${userPrompt}\n\nAdditional instructions: ${regenerationTask.custom_instructions}`
            : userPrompt;

        // Adjust temperature based on attempt number (get more creative with each attempt)
        const temperature = Math.min(0.9, strategy.parameters.temperature + (attemptNumber - 1) * 0.1);

        const completion = await this.openai.chat.completions.create({
            model: this.config.model,
            messages: [
                { role: 'system', content: systemPrompt },
                { role: 'user', content: enhancedUserPrompt }
            ],
            temperature: temperature,
            max_tokens: 1000
        });

        const generatedText = completion.choices[0].message.content.trim();

        return {
            speaker: regenerationTask.original_segment.speaker,
            text: generatedText,
            segment_type: regenerationTask.original_segment.segment_type || 'dialogue',
            regeneration_attempt: attemptNumber,
            generation_temperature: temperature
        };
    }

    buildPromptData(regenerationTask, context, attemptNumber) {
        const data = {
            original_text: regenerationTask.original_segment.text,
            speaker_name: regenerationTask.original_segment.speaker || 'Speaker',
            target_tone: regenerationTask.target_tone || 'conversational',
            focus_areas: regenerationTask.focus_areas.join(', '),
            core_message: context.segment_themes.join(', ')
        };

        // Add context segments if available
        if (context.previous_segment) {
            data.previous_segment = context.previous_segment.text.substring(0, 200) + '...';
        }
        
        if (context.next_segment) {
            data.next_segment = context.next_segment.text.substring(0, 200) + '...';
        }

        // Add speaker information
        if (context.speaker_info) {
            data.personality_traits = context.speaker_info.personality || 'conversational';
            data.speaking_style = context.speaker_info.speaking_pattern || 'natural';
        }

        // Add speakers list for dialogue strategies
        if (context.podcast_metadata.participants) {
            data.speakers = Object.keys(context.podcast_metadata.participants).join(', ');
        }

        // Add attempt-specific guidance
        if (attemptNumber > 1) {
            const previousAttempts = regenerationTask.attempts.slice(0, attemptNumber - 1);
            const avgScore = previousAttempts.reduce((sum, att) => sum + (att.quality_score || 0), 0) / previousAttempts.length;
            
            if (avgScore < 0.5) {
                data.additional_guidance = 'Previous attempts were not satisfactory. Try a more creative or different approach.';
            } else {
                data.additional_guidance = 'Previous attempts were decent but can be improved. Refine the approach.';
            }
        }

        return data;
    }

    populatePromptTemplate(template, data) {
        let populatedTemplate = template;
        
        Object.keys(data).forEach(key => {
            const placeholder = `{${key}}`;
            populatedTemplate = populatedTemplate.replace(
                new RegExp(placeholder, 'g'), 
                data[key] || ''
            );
        });
        
        return populatedTemplate;
    }

    async evaluateRegeneratedSegment(originalSegment, newSegment, regenerationTask, context) {
        try {
            const completion = await this.openai.chat.completions.create({
                model: 'gpt-3.5-turbo',
                messages: [
                    {
                        role: 'system',
                        content: `Evaluate the quality of a regenerated podcast segment. Rate on a scale of 0.0 to 1.0 based on:
- Improvement over original
- Clarity and engagement
- Consistency with speaker voice
- Achievement of regeneration goals
- Natural flow and dialogue

Strategy used: ${regenerationTask.strategy}
Goals: ${regenerationTask.focus_areas.join(', ')}

Return only a number between 0.0 and 1.0.`
                    },
                    {
                        role: 'user',
                        content: `Original segment: "${originalSegment.text}"

Regenerated segment: "${newSegment.text}"

Rate the quality of the regeneration (0.0 to 1.0):`
                    }
                ],
                temperature: 0.1,
                max_tokens: 10
            });

            const scoreText = completion.choices[0].message.content.trim();
            const score = parseFloat(scoreText);
            
            return isNaN(score) ? 0.5 : Math.max(0, Math.min(1, score));
        } catch (error) {
            // Fallback scoring based on simple metrics
            return this.calculateFallbackQualityScore(originalSegment, newSegment);
        }
    }

    calculateFallbackQualityScore(originalSegment, newSegment) {
        let score = 0.5; // Base score
        
        // Check if text length is reasonable (not too short or too long compared to original)
        const originalLength = originalSegment.text.length;
        const newLength = newSegment.text.length;
        const lengthRatio = newLength / originalLength;
        
        if (lengthRatio >= 0.7 && lengthRatio <= 1.5) {
            score += 0.2;
        } else if (lengthRatio >= 0.5 && lengthRatio <= 2.0) {
            score += 0.1;
        }

        // Check for basic dialogue markers (questions, responses, etc.)
        if (newSegment.text.includes('?') || newSegment.text.includes('!')) {
            score += 0.1;
        }

        // Check for conversation connectors
        const connectors = ['well', 'so', 'now', 'but', 'and', 'actually', 'really'];
        if (connectors.some(connector => newSegment.text.toLowerCase().includes(connector))) {
            score += 0.1;
        }

        return Math.min(1, score);
    }

    async analyzeImprovements(originalSegment, regeneratedSegment, strategy) {
        try {
            const completion = await this.openai.chat.completions.create({
                model: 'gpt-3.5-turbo',
                messages: [
                    {
                        role: 'system',
                        content: `Analyze the improvements made in regenerating a podcast segment. List specific improvements achieved.

Strategy used: ${strategy}

Return a JSON array of improvement descriptions.`
                    },
                    {
                        role: 'user',
                        content: `Original: "${originalSegment.text}"

Regenerated: "${regeneratedSegment.text}"

What specific improvements were made?`
                    }
                ],
                temperature: 0.3,
                max_tokens: 300
            });

            return JSON.parse(completion.choices[0].message.content);
        } catch (error) {
            return [`Applied ${strategy} strategy to improve segment quality`];
        }
    }

    async regenerateMultipleSegments(script, segmentIndices, regenerationRequest) {
        const results = [];
        
        for (const segmentIndex of segmentIndices) {
            try {
                const result = await this.regenerateSegment(script, segmentIndex, regenerationRequest);
                results.push(result);
                
                this.emit('multi-regeneration-progress', {
                    completed: results.length,
                    total: segmentIndices.length,
                    currentSegment: segmentIndex
                });
                
            } catch (error) {
                results.push({
                    segment_index: segmentIndex,
                    error: error.message,
                    success: false
                });
            }
        }

        return results;
    }

    async batchRegenerateByCondition(script, condition, regenerationRequest) {
        const targetSegments = this.findSegmentsByCondition(script, condition);
        return await this.regenerateMultipleSegments(script, targetSegments, regenerationRequest);
    }

    findSegmentsByCondition(script, condition) {
        const segments = [];
        
        script.segments.forEach((segment, index) => {
            switch (condition.type) {
                case 'speaker':
                    if (segment.speaker === condition.value) segments.push(index);
                    break;
                case 'length':
                    const wordCount = segment.text.split(/\s+/).length;
                    if (condition.operator === 'less_than' && wordCount < condition.value) {
                        segments.push(index);
                    } else if (condition.operator === 'greater_than' && wordCount > condition.value) {
                        segments.push(index);
                    }
                    break;
                case 'contains_text':
                    if (segment.text.toLowerCase().includes(condition.value.toLowerCase())) {
                        segments.push(index);
                    }
                    break;
                case 'segment_type':
                    if (segment.segment_type === condition.value) segments.push(index);
                    break;
                case 'quality_score':
                    // This would require pre-calculated quality scores
                    break;
            }
        });
        
        return segments;
    }

    async saveRegenerationHistory(taskId, regenerationTask, result) {
        const historyRecord = {
            task_id: taskId,
            script_id: regenerationTask.script_id,
            segment_index: regenerationTask.segment_index,
            original_segment: regenerationTask.original_segment,
            final_segment: result.final_segment,
            strategy: regenerationTask.strategy,
            attempts: regenerationTask.attempts,
            quality_score: result.quality_score,
            improvements: result.improvements,
            timestamp: new Date().toISOString()
        };

        const historyPath = path.join(
            this.config.regeneration_history_directory,
            `${taskId}.json`
        );

        await fs.writeFile(historyPath, JSON.stringify(historyRecord, null, 2));
        
        this.regenerationHistory.set(taskId, historyRecord);
        this.emit('history-saved', { taskId, historyPath });
        
        return historyPath;
    }

    getRegenerationStrategies() {
        return Array.from(this.regenerationStrategies.entries()).map(([id, strategy]) => ({
            id,
            name: strategy.name,
            description: strategy.description,
            focus_areas: strategy.parameters.focus_areas
        }));
    }

    getRegenerationTask(taskId) {
        return this.regenerationTasks.get(taskId);
    }

    getRegenerationHistory(taskId) {
        return this.regenerationHistory.get(taskId);
    }

    async loadRegenerationHistory() {
        try {
            const files = await fs.readdir(this.config.regeneration_history_directory);
            const jsonFiles = files.filter(file => file.endsWith('.json'));

            for (const file of jsonFiles) {
                const filePath = path.join(this.config.regeneration_history_directory, file);
                const content = await fs.readFile(filePath, 'utf8');
                const historyRecord = JSON.parse(content);
                this.regenerationHistory.set(historyRecord.task_id, historyRecord);
            }

            this.emit('history-loaded', { count: jsonFiles.length });
        } catch (error) {
            this.emit('history-load-failed', { error });
        }
    }

    calculateRegenerationStats(scriptId) {
        const taskRecords = Array.from(this.regenerationTasks.values())
            .filter(task => task.script_id === scriptId);
            
        const historyRecords = Array.from(this.regenerationHistory.values())
            .filter(record => record.script_id === scriptId);

        const allRecords = [...taskRecords, ...historyRecords];

        return {
            total_regenerations: allRecords.length,
            strategies_used: [...new Set(allRecords.map(r => r.strategy))],
            average_quality_improvement: this.calculateAverageImprovement(allRecords),
            most_common_strategy: this.getMostCommonStrategy(allRecords),
            success_rate: allRecords.filter(r => r.result?.quality_score >= this.config.quality_threshold).length / allRecords.length
        };
    }

    calculateAverageImprovement(records) {
        const improvements = records
            .filter(r => r.result?.quality_score)
            .map(r => r.result.quality_score);
            
        return improvements.length > 0 
            ? improvements.reduce((sum, score) => sum + score, 0) / improvements.length
            : 0;
    }

    getMostCommonStrategy(records) {
        const strategyCounts = {};
        records.forEach(record => {
            const strategy = record.strategy;
            strategyCounts[strategy] = (strategyCounts[strategy] || 0) + 1;
        });
        
        return Object.keys(strategyCounts).reduce((a, b) => 
            strategyCounts[a] > strategyCounts[b] ? a : b, 
            Object.keys(strategyCounts)[0]
        );
    }

    async suggestRegenerationsForScript(script) {
        const suggestions = [];
        
        for (let i = 0; i < script.segments.length; i++) {
            const segment = script.segments[i];
            const issues = await this.identifySegmentIssues(segment, script, i);
            
            if (issues.length > 0) {
                suggestions.push({
                    segment_index: i,
                    issues: issues,
                    recommended_strategies: this.recommendStrategiesForIssues(issues),
                    priority: this.calculateRegenerationPriority(issues)
                });
            }
        }
        
        return suggestions.sort((a, b) => b.priority - a.priority);
    }

    async identifySegmentIssues(segment, script, segmentIndex) {
        const issues = [];
        
        // Check for common issues
        const wordCount = segment.text.split(/\s+/).length;
        
        if (wordCount < 10) {
            issues.push({ type: 'too_short', severity: 'medium' });
        }
        
        if (wordCount > 200) {
            issues.push({ type: 'too_long', severity: 'low' });
        }
        
        if (!segment.text.includes('?') && !segment.text.includes('!') && segment.text.length > 100) {
            issues.push({ type: 'monotone', severity: 'medium' });
        }
        
        // Check for repetitive content
        const words = segment.text.toLowerCase().split(/\s+/);
        const uniqueWords = new Set(words);
        if (uniqueWords.size / words.length < 0.5 && words.length > 20) {
            issues.push({ type: 'repetitive', severity: 'high' });
        }
        
        return issues;
    }

    recommendStrategiesForIssues(issues) {
        const recommendations = new Set();
        
        issues.forEach(issue => {
            switch (issue.type) {
                case 'too_short':
                    recommendations.add('expand_detail');
                    break;
                case 'too_long':
                    recommendations.add('condense_content');
                    break;
                case 'monotone':
                    recommendations.add('enhance_engagement');
                    recommendations.add('add_personality');
                    break;
                case 'repetitive':
                    recommendations.add('improve_clarity');
                    recommendations.add('creative_rewrite');
                    break;
                case 'unclear':
                    recommendations.add('improve_clarity');
                    break;
                case 'poor_flow':
                    recommendations.add('improve_flow');
                    break;
            }
        });
        
        return Array.from(recommendations);
    }

    calculateRegenerationPriority(issues) {
        const severityWeights = { high: 3, medium: 2, low: 1 };
        return issues.reduce((total, issue) => total + severityWeights[issue.severity], 0);
    }
}

export default SegmentRegenerator;