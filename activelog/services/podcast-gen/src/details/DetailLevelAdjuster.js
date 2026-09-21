import { EventEmitter } from 'events';
import OpenAI from 'openai';
import natural from 'natural';
// Note: reading-level package might not be available, using fallback calculation
import fs from 'fs/promises';
import path from 'path';

class DetailLevelAdjuster extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            openai_api_key: config.openai_api_key || process.env.OPENAI_API_KEY,
            model: config.model || 'gpt-4',
            detail_profiles_directory: config.detail_profiles_directory || './data/detail_profiles',
            adjustments_directory: config.adjustments_directory || './data/detail_adjustments',
            ...config
        };

        this.openai = new OpenAI({
            apiKey: this.config.openai_api_key
        });

        this.detailLevels = new Map();
        this.adjustmentProfiles = new Map();
        this.activeAdjustments = new Map();
        this.complexityAnalyzer = new natural.WordTokenizer();

        this.initializeDetailLevels();
        this.initializeAdjustmentProfiles();
        this.ensureDirectories();
    }

    async ensureDirectories() {
        try {
            await fs.mkdir(this.config.detail_profiles_directory, { recursive: true });
            await fs.mkdir(this.config.adjustments_directory, { recursive: true });
        } catch (error) {
            this.emit('error', { type: 'directory-creation', error });
        }
    }

    initializeDetailLevels() {
        // Define different levels of detail with specific characteristics
        this.detailLevels.set('minimal', {
            id: 'minimal',
            name: 'Minimal Detail',
            description: 'Basic information only, high-level overview',
            characteristics: {
                reading_level: 'elementary',
                sentence_length: 'short',
                vocabulary: 'simple',
                examples: 'few',
                explanations: 'basic',
                jargon: 'minimal',
                depth: 'surface'
            },
            target_metrics: {
                flesch_score: [80, 100],
                avg_sentence_length: [8, 12],
                syllables_per_word: [1.2, 1.4],
                technical_terms_ratio: 0.02
            },
            content_rules: {
                max_concepts_per_segment: 1,
                explanation_style: 'simple_analogy',
                detail_reduction: 'aggressive',
                focus: 'key_takeaways_only'
            }
        });

        this.detailLevels.set('basic', {
            id: 'basic',
            name: 'Basic Detail',
            description: 'Essential information with some context',
            characteristics: {
                reading_level: 'middle_school',
                sentence_length: 'moderate',
                vocabulary: 'accessible',
                examples: 'some',
                explanations: 'clear',
                jargon: 'explained',
                depth: 'moderate'
            },
            target_metrics: {
                flesch_score: [70, 85],
                avg_sentence_length: [12, 16],
                syllables_per_word: [1.4, 1.6],
                technical_terms_ratio: 0.05
            },
            content_rules: {
                max_concepts_per_segment: 2,
                explanation_style: 'clear_with_examples',
                detail_reduction: 'moderate',
                focus: 'main_points_with_context'
            }
        });

        this.detailLevels.set('standard', {
            id: 'standard',
            name: 'Standard Detail',
            description: 'Balanced coverage with good explanations',
            characteristics: {
                reading_level: 'high_school',
                sentence_length: 'varied',
                vocabulary: 'general',
                examples: 'adequate',
                explanations: 'thorough',
                jargon: 'contextual',
                depth: 'comprehensive'
            },
            target_metrics: {
                flesch_score: [60, 75],
                avg_sentence_length: [15, 20],
                syllables_per_word: [1.5, 1.8],
                technical_terms_ratio: 0.08
            },
            content_rules: {
                max_concepts_per_segment: 3,
                explanation_style: 'balanced_detail',
                detail_reduction: 'selective',
                focus: 'complete_understanding'
            }
        });

        this.detailLevels.set('comprehensive', {
            id: 'comprehensive',
            name: 'Comprehensive Detail',
            description: 'In-depth coverage with extensive explanations',
            characteristics: {
                reading_level: 'college',
                sentence_length: 'complex',
                vocabulary: 'advanced',
                examples: 'multiple',
                explanations: 'detailed',
                jargon: 'acceptable',
                depth: 'thorough'
            },
            target_metrics: {
                flesch_score: [50, 65],
                avg_sentence_length: [18, 25],
                syllables_per_word: [1.7, 2.0],
                technical_terms_ratio: 0.12
            },
            content_rules: {
                max_concepts_per_segment: 4,
                explanation_style: 'detailed_analysis',
                detail_reduction: 'minimal',
                focus: 'deep_understanding'
            }
        });

        this.detailLevels.set('expert', {
            id: 'expert',
            name: 'Expert Detail',
            description: 'Technical depth for specialized audience',
            characteristics: {
                reading_level: 'graduate',
                sentence_length: 'complex',
                vocabulary: 'technical',
                examples: 'sophisticated',
                explanations: 'precise',
                jargon: 'expected',
                depth: 'exhaustive'
            },
            target_metrics: {
                flesch_score: [30, 55],
                avg_sentence_length: [20, 30],
                syllables_per_word: [1.8, 2.2],
                technical_terms_ratio: 0.15
            },
            content_rules: {
                max_concepts_per_segment: 5,
                explanation_style: 'technical_precision',
                detail_reduction: 'none',
                focus: 'comprehensive_mastery'
            }
        });
    }

    initializeAdjustmentProfiles() {
        // Different adjustment strategies for various content types
        this.adjustmentProfiles.set('educational', {
            id: 'educational',
            name: 'Educational Content',
            strategies: {
                increase_detail: ['add_examples', 'elaborate_concepts', 'include_background', 'add_practice_questions'],
                decrease_detail: ['remove_tangents', 'simplify_examples', 'consolidate_points', 'focus_core_concepts'],
                maintain_clarity: ['define_terms', 'use_analogies', 'progressive_disclosure']
            },
            preservation_priorities: ['learning_objectives', 'key_concepts', 'actionable_items']
        });

        this.adjustmentProfiles.set('technical', {
            id: 'technical',
            name: 'Technical Documentation',
            strategies: {
                increase_detail: ['add_implementation_details', 'include_code_examples', 'explain_edge_cases', 'add_troubleshooting'],
                decrease_detail: ['remove_verbose_explanations', 'consolidate_similar_concepts', 'focus_on_essentials'],
                maintain_clarity: ['use_precise_terminology', 'provide_context', 'logical_progression']
            },
            preservation_priorities: ['technical_accuracy', 'implementation_steps', 'requirements']
        });

        this.adjustmentProfiles.set('narrative', {
            id: 'narrative',
            name: 'Story/Narrative Content',
            strategies: {
                increase_detail: ['expand_character_development', 'add_scene_details', 'include_backstory', 'elaborate_conflicts'],
                decrease_detail: ['streamline_plot', 'reduce_descriptions', 'focus_main_storyline'],
                maintain_clarity: ['clear_timeline', 'consistent_characters', 'logical_flow']
            },
            preservation_priorities: ['plot_points', 'character_arcs', 'emotional_impact']
        });

        this.adjustmentProfiles.set('business', {
            id: 'business',
            name: 'Business Content',
            strategies: {
                increase_detail: ['add_market_analysis', 'include_case_studies', 'expand_on_implications', 'add_financial_details'],
                decrease_detail: ['focus_on_outcomes', 'summarize_data', 'highlight_key_metrics'],
                maintain_clarity: ['use_business_language', 'focus_on_roi', 'actionable_insights']
            },
            preservation_priorities: ['strategic_objectives', 'key_metrics', 'action_items']
        });

        this.adjustmentProfiles.set('conversational', {
            id: 'conversational',
            name: 'Conversational/Interview Style',
            strategies: {
                increase_detail: ['add_follow_up_questions', 'expand_on_answers', 'include_personal_anecdotes', 'add_context'],
                decrease_detail: ['keep_responses_concise', 'avoid_tangents', 'focus_on_key_points'],
                maintain_clarity: ['natural_dialogue_flow', 'clear_questions', 'smooth_transitions']
            },
            preservation_priorities: ['dialogue_authenticity', 'key_insights', 'conversational_flow']
        });
    }

    async adjustDetailLevel(script, targetDetailLevel, options = {}) {
        try {
            const adjustmentId = `adj_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            this.emit('adjustment-started', { adjustmentId, targetDetailLevel });

            // Analyze current detail level
            const currentAnalysis = await this.analyzeCurrentDetailLevel(script);
            
            // Determine adjustment strategy
            const adjustmentPlan = this.createAdjustmentPlan(
                currentAnalysis,
                targetDetailLevel,
                options
            );

            // Execute adjustments
            const adjustedScript = await this.executeAdjustmentPlan(
                script,
                adjustmentPlan,
                adjustmentId
            );

            // Verify adjustment success
            const finalAnalysis = await this.analyzeCurrentDetailLevel(adjustedScript);

            const adjustmentRecord = {
                id: adjustmentId,
                original_script: script,
                adjusted_script: adjustedScript,
                current_analysis: currentAnalysis,
                target_detail_level: targetDetailLevel,
                adjustment_plan: adjustmentPlan,
                final_analysis: finalAnalysis,
                options: options,
                timestamp: new Date().toISOString()
            };

            this.activeAdjustments.set(adjustmentId, adjustmentRecord);

            this.emit('adjustment-completed', {
                adjustmentId,
                currentLevel: currentAnalysis.detected_level,
                targetLevel: targetDetailLevel,
                finalLevel: finalAnalysis.detected_level,
                success: this.verifyAdjustmentSuccess(targetDetailLevel, finalAnalysis)
            });

            return {
                adjustment_id: adjustmentId,
                adjusted_script: adjustedScript,
                adjustment_summary: {
                    original_level: currentAnalysis.detected_level,
                    target_level: targetDetailLevel,
                    achieved_level: finalAnalysis.detected_level,
                    changes_made: adjustmentPlan.changes.length,
                    success: this.verifyAdjustmentSuccess(targetDetailLevel, finalAnalysis)
                }
            };

        } catch (error) {
            this.emit('adjustment-failed', { targetDetailLevel, error });
            throw error;
        }
    }

    async analyzeCurrentDetailLevel(script) {
        try {
            const segments = script.segments || [];
            const fullText = segments.map(s => s.text).join(' ');

            // Calculate readability metrics
            const tokens = this.complexityAnalyzer.tokenize(fullText);
            const sentences = fullText.split(/[.!?]+/).filter(s => s.trim().length > 0);
            const words = tokens.filter(token => /^[a-zA-Z]+$/.test(token));
            
            const metrics = {
                total_words: words.length,
                total_sentences: sentences.length,
                avg_sentence_length: words.length / sentences.length,
                avg_word_length: words.reduce((sum, word) => sum + word.length, 0) / words.length,
                syllables_per_word: await this.calculateAverageSyllables(words),
                flesch_score: this.calculateFleschScore(fullText),
                technical_terms_ratio: await this.calculateTechnicalTermsRatio(words),
                complexity_indicators: await this.identifyComplexityIndicators(fullText)
            };

            // Determine current detail level
            const detectedLevel = this.determineDetailLevel(metrics);

            // Analyze content structure
            const structureAnalysis = await this.analyzeContentStructure(segments);

            return {
                detected_level: detectedLevel,
                confidence: this.calculateDetectionConfidence(metrics, detectedLevel),
                metrics: metrics,
                structure_analysis: structureAnalysis,
                segments_analysis: await this.analyzeSegmentDetails(segments)
            };

        } catch (error) {
            this.emit('analysis-failed', { error });
            throw error;
        }
    }

    calculateFleschScore(text) {
        // Fallback calculation
        const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
        const words = text.split(/\s+/).filter(w => w.length > 0);
        
        if (sentences.length === 0 || words.length === 0) return 0;
        
        const syllables = words.reduce((count, word) => count + this.countSyllables(word), 0);
        
        const avgWordsPerSentence = words.length / sentences.length;
        const avgSyllablesPerWord = syllables / words.length;
        
        return 206.835 - (1.015 * avgWordsPerSentence) - (84.6 * avgSyllablesPerWord);
    }

    countSyllables(word) {
        const vowels = 'aeiouy';
        let count = 0;
        let previousWasVowel = false;
        
        word.toLowerCase().split('').forEach(char => {
            const isVowel = vowels.includes(char);
            if (isVowel && !previousWasVowel) count++;
            previousWasVowel = isVowel;
        });
        
        return Math.max(1, count);
    }

    async calculateAverageSyllables(words) {
        const totalSyllables = words.reduce((sum, word) => sum + this.countSyllables(word), 0);
        return totalSyllables / words.length;
    }

    async calculateTechnicalTermsRatio(words) {
        // This is a simplified version - in practice, you'd use a technical terms dictionary
        const technicalPatterns = [
            /.*tion$/, /.*sion$/, /.*ment$/, /.*ness$/, /.*ity$/,
            /^micro.*/, /^macro.*/, /.*system.*/, /.*process.*/, /.*analysis.*/
        ];
        
        const technicalWords = words.filter(word => 
            word.length > 6 && technicalPatterns.some(pattern => pattern.test(word.toLowerCase()))
        );
        
        return technicalWords.length / words.length;
    }

    async identifyComplexityIndicators(text) {
        const indicators = {
            passive_voice: (text.match(/\b(was|were|is|are|been|being)\s+\w+ed\b/gi) || []).length,
            subordinate_clauses: (text.match(/\b(although|because|since|while|whereas|if|unless|until)\b/gi) || []).length,
            long_sentences: text.split(/[.!?]+/).filter(s => s.trim().split(/\s+/).length > 20).length,
            technical_connectors: (text.match(/\b(therefore|furthermore|consequently|moreover|nevertheless|however)\b/gi) || []).length,
            quantitative_references: (text.match(/\b(\d+%|\d+\.\d+|\$\d+|approximately|roughly|about \d+)\b/gi) || []).length
        };
        
        return indicators;
    }

    determineDetailLevel(metrics) {
        const levels = Array.from(this.detailLevels.values());
        let bestMatch = levels[0];
        let bestScore = 0;

        for (const level of levels) {
            let score = 0;
            const targets = level.target_metrics;

            // Check Flesch score match
            const fleschRange = targets.flesch_score;
            const fleschMin = Array.isArray(fleschRange) ? fleschRange[0] : 60;
            const fleschMax = Array.isArray(fleschRange) ? fleschRange[1] : 75;
            
            if (metrics.flesch_score >= fleschMin && metrics.flesch_score <= fleschMax) {
                score += 3;
            } else {
                const distance = Math.min(
                    Math.abs(metrics.flesch_score - fleschMin),
                    Math.abs(metrics.flesch_score - fleschMax)
                );
                score += Math.max(0, 3 - (distance / 10));
            }

            // Check sentence length match
            const sentenceLengthRange = targets.avg_sentence_length;
            const sentenceLengthMin = Array.isArray(sentenceLengthRange) ? sentenceLengthRange[0] : 15;
            const sentenceLengthMax = Array.isArray(sentenceLengthRange) ? sentenceLengthRange[1] : 20;
            const sentenceLengthTarget = (sentenceLengthMin + sentenceLengthMax) / 2;
            const sentenceLengthDistance = Math.abs(metrics.avg_sentence_length - sentenceLengthTarget);
            score += Math.max(0, 2 - (sentenceLengthDistance / 5));

            // Check technical terms ratio
            const techTermsDistance = Math.abs(metrics.technical_terms_ratio - targets.technical_terms_ratio);
            score += Math.max(0, 1 - (techTermsDistance * 10));

            if (score > bestScore) {
                bestScore = score;
                bestMatch = level;
            }
        }

        return bestMatch.id;
    }

    calculateDetectionConfidence(metrics, detectedLevel) {
        const levelConfig = this.detailLevels.get(detectedLevel);
        if (!levelConfig) return 0.5;

        // Calculate confidence based on how well metrics match the detected level
        const targets = levelConfig.target_metrics;
        let totalMatch = 0;
        let totalChecks = 0;

        // Flesch score confidence
        const fleschRange = targets.flesch_score;
        const fleschTarget = Array.isArray(fleschRange) ? (fleschRange[0] + fleschRange[1]) / 2 : 60;
        const fleschMatch = Math.max(0, 1 - Math.abs(metrics.flesch_score - fleschTarget) / 25);
        totalMatch += fleschMatch;
        totalChecks++;

        // Sentence length confidence
        const sentLengthRange = targets.avg_sentence_length;
        const sentLengthTarget = Array.isArray(sentLengthRange) ? (sentLengthRange[0] + sentLengthRange[1]) / 2 : 15;
        const sentLengthMatch = Math.max(0, 1 - Math.abs(metrics.avg_sentence_length - sentLengthTarget) / 10);
        totalMatch += sentLengthMatch;
        totalChecks++;

        // Technical terms confidence
        const techTermsMatch = Math.max(0, 1 - Math.abs(metrics.technical_terms_ratio - targets.technical_terms_ratio) * 20);
        totalMatch += techTermsMatch;
        totalChecks++;

        return totalMatch / totalChecks;
    }

    async analyzeContentStructure(segments) {
        const structure = {
            total_segments: segments.length,
            avg_segment_length: 0,
            segment_types: {},
            dialogue_distribution: {},
            content_density: {}
        };

        let totalWords = 0;
        
        for (const segment of segments) {
            const words = segment.text.split(/\s+/).length;
            totalWords += words;
            
            // Count segment types
            const type = segment.segment_type || 'dialogue';
            structure.segment_types[type] = (structure.segment_types[type] || 0) + 1;
            
            // Count speakers
            const speaker = segment.speaker || 'unknown';
            structure.dialogue_distribution[speaker] = (structure.dialogue_distribution[speaker] || 0) + words;
        }

        structure.avg_segment_length = totalWords / segments.length;
        
        return structure;
    }

    async analyzeSegmentDetails(segments) {
        const analysis = [];
        
        for (let i = 0; i < segments.length; i++) {
            const segment = segments[i];
            const words = segment.text.split(/\s+/).filter(w => w.length > 0);
            const sentences = segment.text.split(/[.!?]+/).filter(s => s.trim().length > 0);
            
            analysis.push({
                index: i,
                speaker: segment.speaker,
                word_count: words.length,
                sentence_count: sentences.length,
                avg_sentence_length: words.length / Math.max(1, sentences.length),
                complexity_score: this.calculateSegmentComplexity(segment.text),
                detail_indicators: await this.identifyDetailIndicators(segment.text)
            });
        }
        
        return analysis;
    }

    calculateSegmentComplexity(text) {
        const words = text.split(/\s+/).length;
        const longWords = text.split(/\s+/).filter(word => word.length > 6).length;
        const complexSentences = text.split(/[.!?]+/).filter(sentence => 
            sentence.includes(',') || sentence.includes(';') || sentence.includes(':')
        ).length;
        
        return (longWords / words) + (complexSentences / Math.max(1, text.split(/[.!?]+/).length));
    }

    async identifyDetailIndicators(text) {
        return {
            examples: (text.match(/\b(for example|such as|like|including|specifically|instance)\b/gi) || []).length,
            explanations: (text.match(/\b(because|since|due to|as a result|therefore|thus)\b/gi) || []).length,
            qualifiers: (text.match(/\b(might|could|may|perhaps|possibly|likely|typically|generally)\b/gi) || []).length,
            specificity: (text.match(/\b(\d+|\$|%|exactly|precisely|specifically|particularly)\b/gi) || []).length,
            elaborations: (text.match(/\b(furthermore|additionally|moreover|in addition|also|further)\b/gi) || []).length
        };
    }

    createAdjustmentPlan(currentAnalysis, targetDetailLevel, options) {
        const targetConfig = this.detailLevels.get(targetDetailLevel);
        const adjustmentProfile = this.adjustmentProfiles.get(options.content_type || 'educational');
        
        const plan = {
            target_level: targetDetailLevel,
            current_level: currentAnalysis.detected_level,
            direction: this.determineAdjustmentDirection(currentAnalysis.detected_level, targetDetailLevel),
            changes: [],
            preservation_rules: adjustmentProfile?.preservation_priorities || [],
            strategies: []
        };

        // Determine specific adjustments needed
        if (plan.direction === 'increase') {
            plan.strategies = adjustmentProfile?.strategies.increase_detail || ['add_examples', 'elaborate_concepts'];
            plan.changes = this.planDetailIncreases(currentAnalysis, targetConfig, options);
        } else if (plan.direction === 'decrease') {
            plan.strategies = adjustmentProfile?.strategies.decrease_detail || ['simplify_examples', 'focus_core_concepts'];
            plan.changes = this.planDetailReductions(currentAnalysis, targetConfig, options);
        } else {
            plan.strategies = adjustmentProfile?.strategies.maintain_clarity || ['improve_clarity'];
            plan.changes = this.planClarityImprovements(currentAnalysis, targetConfig, options);
        }

        return plan;
    }

    determineAdjustmentDirection(currentLevel, targetLevel) {
        const levels = ['minimal', 'basic', 'standard', 'comprehensive', 'expert'];
        const currentIndex = levels.indexOf(currentLevel);
        const targetIndex = levels.indexOf(targetLevel);
        
        if (targetIndex > currentIndex) return 'increase';
        if (targetIndex < currentIndex) return 'decrease';
        return 'maintain';
    }

    planDetailIncreases(currentAnalysis, targetConfig, options) {
        const changes = [];
        
        // Add more examples if needed
        if (currentAnalysis.segments_analysis.some(s => s.detail_indicators.examples < 1)) {
            changes.push({
                type: 'add_examples',
                priority: 'high',
                target_segments: currentAnalysis.segments_analysis
                    .filter(s => s.detail_indicators.examples < 1)
                    .map(s => s.index),
                instructions: 'Add concrete examples to illustrate key points'
            });
        }

        // Expand explanations
        changes.push({
            type: 'expand_explanations',
            priority: 'medium',
            target_segments: 'all',
            instructions: 'Provide more detailed explanations of concepts and processes'
        });

        // Add background context
        changes.push({
            type: 'add_context',
            priority: 'medium',
            target_segments: 'introduction',
            instructions: 'Include more background information and context setting'
        });

        return changes;
    }

    planDetailReductions(currentAnalysis, targetConfig, options) {
        const changes = [];
        
        // Simplify complex sentences
        const complexSegments = currentAnalysis.segments_analysis
            .filter(s => s.avg_sentence_length > 20)
            .map(s => s.index);
            
        if (complexSegments.length > 0) {
            changes.push({
                type: 'simplify_sentences',
                priority: 'high',
                target_segments: complexSegments,
                instructions: 'Break down complex sentences into simpler ones'
            });
        }

        // Remove excessive detail
        changes.push({
            type: 'reduce_detail',
            priority: 'medium',
            target_segments: 'all',
            instructions: 'Focus on core concepts and remove tangential information'
        });

        // Consolidate examples
        changes.push({
            type: 'consolidate_examples',
            priority: 'low',
            target_segments: 'all',
            instructions: 'Use fewer, more impactful examples'
        });

        return changes;
    }

    planClarityImprovements(currentAnalysis, targetConfig, options) {
        const changes = [];
        
        // Improve terminology consistency
        changes.push({
            type: 'improve_terminology',
            priority: 'medium',
            target_segments: 'all',
            instructions: 'Ensure consistent use of terminology throughout'
        });

        // Add transitions
        changes.push({
            type: 'add_transitions',
            priority: 'medium',
            target_segments: 'between_segments',
            instructions: 'Add smooth transitions between topics'
        });

        return changes;
    }

    async executeAdjustmentPlan(script, plan, adjustmentId) {
        const adjustedScript = { ...script, segments: [...script.segments] };
        
        for (const change of plan.changes) {
            try {
                this.emit('change-processing', { adjustmentId, change: change.type });
                
                await this.applyChange(adjustedScript, change, plan);
                
                this.emit('change-applied', { adjustmentId, change: change.type });
            } catch (error) {
                this.emit('change-failed', { adjustmentId, change: change.type, error });
                // Continue with other changes even if one fails
            }
        }
        
        return adjustedScript;
    }

    async applyChange(script, change, plan) {
        const targetSegments = this.resolveTargetSegments(script, change.target_segments);
        
        switch (change.type) {
            case 'add_examples':
                await this.addExamples(script, targetSegments, change.instructions);
                break;
            case 'expand_explanations':
                await this.expandExplanations(script, targetSegments, change.instructions);
                break;
            case 'simplify_sentences':
                await this.simplifySentences(script, targetSegments, change.instructions);
                break;
            case 'reduce_detail':
                await this.reduceDetail(script, targetSegments, change.instructions, plan.preservation_rules);
                break;
            case 'add_context':
                await this.addContext(script, targetSegments, change.instructions);
                break;
            case 'improve_terminology':
                await this.improveTerminology(script, targetSegments, change.instructions);
                break;
            case 'add_transitions':
                await this.addTransitions(script, change.instructions);
                break;
            default:
                console.warn(`Unknown change type: ${change.type}`);
        }
    }

    resolveTargetSegments(script, target) {
        if (target === 'all') {
            return script.segments.map((_, index) => index);
        } else if (target === 'introduction') {
            return [0];
        } else if (Array.isArray(target)) {
            return target;
        } else if (typeof target === 'number') {
            return [target];
        }
        return [];
    }

    async addExamples(script, targetSegments, instructions) {
        for (const segmentIndex of targetSegments) {
            const segment = script.segments[segmentIndex];
            
            const completion = await this.openai.chat.completions.create({
                model: this.config.model,
                messages: [
                    {
                        role: 'system',
                        content: `Add concrete examples to this podcast segment. ${instructions}

Original segment: ${segment.text}

Add 1-2 relevant examples that illustrate the key points. Maintain the speaker's voice and style.`
                    }
                ],
                temperature: 0.7,
                max_tokens: 1000
            });

            script.segments[segmentIndex].text = completion.choices[0].message.content.trim();
        }
    }

    async expandExplanations(script, targetSegments, instructions) {
        for (const segmentIndex of targetSegments) {
            const segment = script.segments[segmentIndex];
            
            const completion = await this.openai.chat.completions.create({
                model: this.config.model,
                messages: [
                    {
                        role: 'system',
                        content: `Expand the explanations in this podcast segment. ${instructions}

Original segment: ${segment.text}

Provide more detailed explanations while maintaining clarity and the speaker's voice.`
                    }
                ],
                temperature: 0.6,
                max_tokens: 1200
            });

            script.segments[segmentIndex].text = completion.choices[0].message.content.trim();
        }
    }

    async simplifySentences(script, targetSegments, instructions) {
        for (const segmentIndex of targetSegments) {
            const segment = script.segments[segmentIndex];
            
            const completion = await this.openai.chat.completions.create({
                model: this.config.model,
                messages: [
                    {
                        role: 'system',
                        content: `Simplify the sentences in this podcast segment. ${instructions}

Original segment: ${segment.text}

Break down complex sentences into simpler ones while preserving all important information.`
                    }
                ],
                temperature: 0.5,
                max_tokens: 800
            });

            script.segments[segmentIndex].text = completion.choices[0].message.content.trim();
        }
    }

    async reduceDetail(script, targetSegments, instructions, preservationRules) {
        for (const segmentIndex of targetSegments) {
            const segment = script.segments[segmentIndex];
            
            const completion = await this.openai.chat.completions.create({
                model: this.config.model,
                messages: [
                    {
                        role: 'system',
                        content: `Reduce the detail level in this podcast segment. ${instructions}

Preservation rules: Always preserve ${preservationRules.join(', ')}

Original segment: ${segment.text}

Focus on core concepts and remove excessive detail while preserving essential information.`
                    }
                ],
                temperature: 0.4,
                max_tokens: 600
            });

            script.segments[segmentIndex].text = completion.choices[0].message.content.trim();
        }
    }

    async addContext(script, targetSegments, instructions) {
        for (const segmentIndex of targetSegments) {
            const segment = script.segments[segmentIndex];
            
            const completion = await this.openai.chat.completions.create({
                model: this.config.model,
                messages: [
                    {
                        role: 'system',
                        content: `Add more context to this podcast segment. ${instructions}

Original segment: ${segment.text}

Provide background information and context to help listeners better understand the content.`
                    }
                ],
                temperature: 0.7,
                max_tokens: 1000
            });

            script.segments[segmentIndex].text = completion.choices[0].message.content.trim();
        }
    }

    async improveTerminology(script, targetSegments, instructions) {
        // First pass: identify terminology used across segments
        const terminology = new Map();
        
        for (const segmentIndex of targetSegments) {
            const segment = script.segments[segmentIndex];
            // Extract potential technical terms (simplified approach)
            const words = segment.text.split(/\s+/);
            words.forEach(word => {
                if (word.length > 6) {
                    const normalized = word.toLowerCase().replace(/[^\w]/g, '');
                    terminology.set(normalized, (terminology.get(normalized) || 0) + 1);
                }
            });
        }

        // Second pass: ensure consistent usage
        for (const segmentIndex of targetSegments) {
            const segment = script.segments[segmentIndex];
            
            const completion = await this.openai.chat.completions.create({
                model: this.config.model,
                messages: [
                    {
                        role: 'system',
                        content: `Improve terminology consistency in this podcast segment. ${instructions}

Original segment: ${segment.text}

Ensure technical terms are used consistently and defined when first introduced.`
                    }
                ],
                temperature: 0.4,
                max_tokens: 800
            });

            script.segments[segmentIndex].text = completion.choices[0].message.content.trim();
        }
    }

    async addTransitions(script, instructions) {
        // Add transitions between segments where needed
        for (let i = 0; i < script.segments.length - 1; i++) {
            const currentSegment = script.segments[i];
            const nextSegment = script.segments[i + 1];
            
            // Check if transition is needed (different topics or speakers)
            if (currentSegment.speaker !== nextSegment.speaker || 
                this.topicsAreDifferent(currentSegment.text, nextSegment.text)) {
                
                const completion = await this.openai.chat.completions.create({
                    model: this.config.model,
                    messages: [
                        {
                            role: 'system',
                            content: `Create a smooth transition between these podcast segments. ${instructions}

Current segment (${currentSegment.speaker}): ${currentSegment.text}
Next segment (${nextSegment.speaker}): ${nextSegment.text}

Add a brief transition that connects these topics naturally. Return only the transition text.`
                        }
                    ],
                    temperature: 0.6,
                    max_tokens: 200
                });

                const transitionText = completion.choices[0].message.content.trim();
                
                // Add transition to current segment or create new transition segment
                script.segments[i].text += ` ${transitionText}`;
            }
        }
    }

    topicsAreDifferent(text1, text2) {
        // Simplified topic difference detection
        const words1 = new Set(text1.toLowerCase().split(/\s+/).filter(w => w.length > 4));
        const words2 = new Set(text2.toLowerCase().split(/\s+/).filter(w => w.length > 4));
        
        const intersection = new Set([...words1].filter(w => words2.has(w)));
        const union = new Set([...words1, ...words2]);
        
        const similarity = intersection.size / union.size;
        return similarity < 0.3; // Consider different if less than 30% word overlap
    }

    verifyAdjustmentSuccess(targetLevel, finalAnalysis) {
        return finalAnalysis.detected_level === targetLevel && finalAnalysis.confidence > 0.7;
    }

    getDetailLevels() {
        return Array.from(this.detailLevels.values()).map(level => ({
            id: level.id,
            name: level.name,
            description: level.description,
            characteristics: level.characteristics
        }));
    }

    getAdjustmentProfiles() {
        return Array.from(this.adjustmentProfiles.values()).map(profile => ({
            id: profile.id,
            name: profile.name,
            strategies: Object.keys(profile.strategies)
        }));
    }

    getAdjustmentRecord(adjustmentId) {
        return this.activeAdjustments.get(adjustmentId);
    }

    async saveAdjustment(adjustmentId) {
        const adjustment = this.activeAdjustments.get(adjustmentId);
        if (!adjustment) {
            throw new Error(`Adjustment not found: ${adjustmentId}`);
        }

        const savePath = path.join(
            this.config.adjustments_directory,
            `${adjustmentId}.json`
        );

        await fs.writeFile(savePath, JSON.stringify(adjustment, null, 2));
        this.emit('adjustment-saved', { adjustmentId, savePath });
        
        return savePath;
    }
}

export default DetailLevelAdjuster;