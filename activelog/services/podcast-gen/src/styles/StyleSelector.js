import { EventEmitter } from 'events';
import fs from 'fs/promises';
import path from 'path';

class StyleSelector extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            styles_directory: config.styles_directory || './data/styles',
            custom_styles_directory: config.custom_styles_directory || './data/custom_styles',
            default_style: config.default_style || 'conversational_explain',
            ...config
        };

        this.conversationStyles = new Map();
        this.customStyles = new Map();
        this.stylePresets = new Map();
        this.activeSelections = new Map();

        this.initializeStyles();
        this.ensureDirectories();
    }

    async ensureDirectories() {
        try {
            await fs.mkdir(this.config.styles_directory, { recursive: true });
            await fs.mkdir(this.config.custom_styles_directory, { recursive: true });
        } catch (error) {
            this.emit('error', { type: 'directory-creation', error });
        }
    }

    initializeStyles() {
        // Conversational Explain Style
        this.conversationStyles.set('conversational_explain', {
            id: 'conversational_explain',
            name: 'Conversational Explanation',
            description: 'Clear, friendly explanations with natural dialogue flow',
            category: 'educational',
            participants: {
                host: {
                    role: 'guide',
                    personality: 'friendly, knowledgeable, patient',
                    speaking_pattern: 'asks clarifying questions, summarizes key points',
                    voice_profile: 'host_female_warm'
                },
                expert: {
                    role: 'explainer',
                    personality: 'knowledgeable, approachable, detailed',
                    speaking_pattern: 'explains concepts step-by-step, uses analogies',
                    voice_profile: 'expert_male_authoritative'
                }
            },
            dialogue_structure: {
                opening: {
                    pattern: 'introduction_and_context',
                    elements: ['topic_introduction', 'guest_introduction', 'episode_outline']
                },
                body: {
                    pattern: 'question_and_answer',
                    elements: ['concept_explanation', 'practical_examples', 'clarifying_questions', 'key_takeaways']
                },
                closing: {
                    pattern: 'summary_and_next_steps',
                    elements: ['key_points_recap', 'actionable_advice', 'resources_mentioned']
                }
            },
            conversation_flow: {
                pacing: 'moderate',
                interruptions: 'minimal',
                back_and_forth: 'structured',
                tone_shifts: 'gradual'
            },
            content_adaptation: {
                complexity_handling: 'break_down_complex_topics',
                jargon_treatment: 'explain_technical_terms',
                examples: 'real_world_analogies',
                depth_level: 'comprehensive_but_accessible'
            }
        });

        // Debate Style
        this.conversationStyles.set('structured_debate', {
            id: 'structured_debate',
            name: 'Structured Debate',
            description: 'Balanced debate format with opposing viewpoints',
            category: 'discussion',
            participants: {
                moderator: {
                    role: 'facilitator',
                    personality: 'neutral, fair, organized',
                    speaking_pattern: 'introduces topics, manages time, asks probing questions',
                    voice_profile: 'interviewer_professional'
                },
                advocate: {
                    role: 'supporter',
                    personality: 'passionate, persuasive, well-researched',
                    speaking_pattern: 'presents arguments, counters objections, uses evidence',
                    voice_profile: 'advocate_passionate'
                },
                skeptic: {
                    role: 'critic',
                    personality: 'analytical, cautious, thorough',
                    speaking_pattern: 'questions assumptions, presents counterarguments, focuses on flaws',
                    voice_profile: 'skeptic_analytical'
                }
            },
            dialogue_structure: {
                opening: {
                    pattern: 'topic_setup_and_positions',
                    elements: ['debate_topic', 'participant_positions', 'ground_rules']
                },
                body: {
                    pattern: 'alternating_arguments',
                    elements: ['opening_statements', 'direct_rebuttals', 'evidence_presentation', 'cross_examination']
                },
                closing: {
                    pattern: 'final_statements_and_synthesis',
                    elements: ['closing_arguments', 'common_ground', 'moderator_summary']
                }
            },
            conversation_flow: {
                pacing: 'dynamic',
                interruptions: 'controlled',
                back_and_forth: 'adversarial_but_respectful',
                tone_shifts: 'rapid_between_agreement_and_disagreement'
            },
            content_adaptation: {
                complexity_handling: 'present_multiple_perspectives',
                jargon_treatment: 'define_when_first_used',
                examples: 'contrasting_case_studies',
                depth_level: 'thorough_analysis'
            }
        });

        // Comedy Roast Style
        this.conversationStyles.set('comedy_roast', {
            id: 'comedy_roast',
            name: 'Comedy Roast',
            description: 'Humorous take with playful criticism and jokes',
            category: 'entertainment',
            participants: {
                comedian_1: {
                    role: 'roaster',
                    personality: 'witty, sarcastic, observational',
                    speaking_pattern: 'makes jokes, delivers punchlines, builds on partner\'s jokes',
                    voice_profile: 'comedian_male_energetic'
                },
                comedian_2: {
                    role: 'straight_man',
                    personality: 'dry humor, reactive, timing-focused',
                    speaking_pattern: 'sets up jokes, reacts to absurdity, delivers deadpan lines',
                    voice_profile: 'comedian_female_playful'
                }
            },
            dialogue_structure: {
                opening: {
                    pattern: 'comedic_introduction',
                    elements: ['topic_setup_with_humor', 'comedian_introductions', 'disclaimer_about_humor']
                },
                body: {
                    pattern: 'roast_and_react',
                    elements: ['topic_roasting', 'comedic_observations', 'callback_jokes', 'audience_asides']
                },
                closing: {
                    pattern: 'wrap_up_with_love',
                    elements: ['final_roasts', 'sincere_appreciation', 'comedic_goodbye']
                }
            },
            conversation_flow: {
                pacing: 'fast',
                interruptions: 'frequent_for_comedy',
                back_and_forth: 'rapid_fire_jokes',
                tone_shifts: 'from_mean_to_loving'
            },
            content_adaptation: {
                complexity_handling: 'simplify_for_humor',
                jargon_treatment: 'make_fun_of_jargon',
                examples: 'absurd_hypotheticals',
                depth_level: 'surface_level_with_insight'
            }
        });

        // Interview Style
        this.conversationStyles.set('investigative_interview', {
            id: 'investigative_interview',
            name: 'Investigative Interview',
            description: 'In-depth interview with probing questions',
            category: 'journalistic',
            participants: {
                interviewer: {
                    role: 'questioner',
                    personality: 'curious, persistent, prepared',
                    speaking_pattern: 'asks follow-up questions, seeks clarity, challenges assumptions',
                    voice_profile: 'interviewer_professional'
                },
                subject: {
                    role: 'respondent',
                    personality: 'knowledgeable, reflective, sometimes defensive',
                    speaking_pattern: 'provides detailed answers, shares experiences, explains reasoning',
                    voice_profile: 'expert_female_confident'
                }
            },
            dialogue_structure: {
                opening: {
                    pattern: 'interview_setup',
                    elements: ['subject_introduction', 'context_setting', 'interview_scope']
                },
                body: {
                    pattern: 'progressive_questioning',
                    elements: ['background_questions', 'core_topic_exploration', 'challenging_questions', 'personal_insights']
                },
                closing: {
                    pattern: 'reflection_and_conclusion',
                    elements: ['key_revelations', 'subject_reflection', 'interviewer_analysis']
                }
            },
            conversation_flow: {
                pacing: 'thoughtful',
                interruptions: 'rare_but_strategic',
                back_and_forth: 'question_driven',
                tone_shifts: 'from_comfortable_to_challenging'
            },
            content_adaptation: {
                complexity_handling: 'ask_for_elaboration',
                jargon_treatment: 'ask_for_definitions',
                examples: 'request_specific_examples',
                depth_level: 'deep_dive_investigation'
            }
        });

        // Storytelling Narrative Style
        this.conversationStyles.set('narrative_storytelling', {
            id: 'narrative_storytelling',
            name: 'Narrative Storytelling',
            description: 'Story-driven format with dramatic elements',
            category: 'narrative',
            participants: {
                narrator: {
                    role: 'storyteller',
                    personality: 'engaging, dramatic, descriptive',
                    speaking_pattern: 'sets scenes, builds suspense, provides context',
                    voice_profile: 'narrator_neutral'
                },
                character_1: {
                    role: 'participant',
                    personality: 'varies_by_story',
                    speaking_pattern: 'dialogue_within_story',
                    voice_profile: 'expert_male_authoritative'
                },
                character_2: {
                    role: 'participant',
                    personality: 'varies_by_story',
                    speaking_pattern: 'dialogue_within_story',
                    voice_profile: 'expert_female_confident'
                }
            },
            dialogue_structure: {
                opening: {
                    pattern: 'story_setup',
                    elements: ['scene_setting', 'character_introduction', 'conflict_preview']
                },
                body: {
                    pattern: 'narrative_progression',
                    elements: ['story_development', 'character_dialogue', 'plot_advancement', 'dramatic_moments']
                },
                closing: {
                    pattern: 'resolution_and_meaning',
                    elements: ['story_conclusion', 'lessons_learned', 'broader_implications']
                }
            },
            conversation_flow: {
                pacing: 'variable',
                interruptions: 'part_of_narrative',
                back_and_forth: 'story_driven',
                tone_shifts: 'dramatic_arc'
            },
            content_adaptation: {
                complexity_handling: 'weave_into_narrative',
                jargon_treatment: 'explain_through_story',
                examples: 'story_scenarios',
                depth_level: 'comprehensive_through_narrative'
            }
        });

        // News Report Style
        this.conversationStyles.set('news_report', {
            id: 'news_report',
            name: 'News Report',
            description: 'Professional news-style reporting format',
            category: 'informational',
            participants: {
                anchor: {
                    role: 'news_presenter',
                    personality: 'professional, authoritative, clear',
                    speaking_pattern: 'introduces segments, provides transitions, summarizes',
                    voice_profile: 'host_male_professional'
                },
                correspondent: {
                    role: 'field_reporter',
                    personality: 'knowledgeable, direct, factual',
                    speaking_pattern: 'reports details, provides analysis, answers questions',
                    voice_profile: 'expert_female_confident'
                },
                expert: {
                    role: 'analyst',
                    personality: 'specialized, insightful, measured',
                    speaking_pattern: 'provides expert commentary, explains implications, offers predictions',
                    voice_profile: 'expert_male_authoritative'
                }
            },
            dialogue_structure: {
                opening: {
                    pattern: 'news_introduction',
                    elements: ['headline', 'story_overview', 'segment_preview']
                },
                body: {
                    pattern: 'layered_reporting',
                    elements: ['basic_facts', 'detailed_analysis', 'expert_commentary', 'broader_context']
                },
                closing: {
                    pattern: 'news_conclusion',
                    elements: ['key_takeaways', 'what_comes_next', 'sign_off']
                }
            },
            conversation_flow: {
                pacing: 'professional',
                interruptions: 'none',
                back_and_forth: 'structured_handoffs',
                tone_shifts: 'minimal'
            },
            content_adaptation: {
                complexity_handling: 'layer_information',
                jargon_treatment: 'define_immediately',
                examples: 'concrete_specifics',
                depth_level: 'comprehensive_factual'
            }
        });

        // Setup style presets for easy combinations
        this.setupStylePresets();
    }

    setupStylePresets() {
        this.stylePresets.set('educational_friendly', {
            base_style: 'conversational_explain',
            modifications: {
                pacing: 'slow',
                complexity_handling: 'extra_simple',
                examples: 'lots_of_analogies'
            },
            target_audience: 'beginners'
        });

        this.stylePresets.set('heated_debate', {
            base_style: 'structured_debate',
            modifications: {
                interruptions: 'frequent',
                tone_shifts: 'dramatic',
                back_and_forth: 'aggressive_but_civil'
            },
            target_audience: 'engaged_listeners'
        });

        this.stylePresets.set('light_comedy', {
            base_style: 'comedy_roast',
            modifications: {
                roast_intensity: 'gentle',
                sincerity_balance: 'high',
                joke_frequency: 'moderate'
            },
            target_audience: 'general_audience'
        });

        this.stylePresets.set('deep_dive_interview', {
            base_style: 'investigative_interview',
            modifications: {
                question_depth: 'maximum',
                follow_up_intensity: 'high',
                personal_questions: 'allowed'
            },
            target_audience: 'serious_listeners'
        });
    }

    getAvailableStyles() {
        return Array.from(this.conversationStyles.keys()).map(styleId => ({
            id: styleId,
            name: this.conversationStyles.get(styleId).name,
            description: this.conversationStyles.get(styleId).description,
            category: this.conversationStyles.get(styleId).category
        }));
    }

    getStyleDetails(styleId) {
        const style = this.conversationStyles.get(styleId);
        if (!style) {
            throw new Error(`Style not found: ${styleId}`);
        }
        return { ...style };
    }

    getStylePresets() {
        return Array.from(this.stylePresets.keys()).map(presetId => ({
            id: presetId,
            ...this.stylePresets.get(presetId)
        }));
    }

    selectStyle(selectionRequest) {
        const {
            document_id,
            preferred_style,
            target_audience,
            content_type,
            desired_length,
            tone_preference,
            expertise_level,
            custom_modifications
        } = selectionRequest;

        try {
            // Analyze content to suggest appropriate style
            const styleRecommendations = this.analyzeContentForStyle({
                content_type,
                target_audience,
                expertise_level,
                tone_preference
            });

            // Apply user preferences
            let selectedStyle = preferred_style || styleRecommendations.primary;
            
            // Get the base style
            let styleConfig = { ...this.conversationStyles.get(selectedStyle) };

            if (!styleConfig) {
                selectedStyle = this.config.default_style;
                styleConfig = { ...this.conversationStyles.get(selectedStyle) };
            }

            // Apply modifications based on context
            styleConfig = this.applyContextualModifications(styleConfig, {
                target_audience,
                content_type,
                desired_length,
                tone_preference,
                expertise_level
            });

            // Apply custom modifications if provided
            if (custom_modifications) {
                styleConfig = this.applyCustomModifications(styleConfig, custom_modifications);
            }

            // Store the selection
            const selectionId = `${document_id}_${Date.now()}`;
            this.activeSelections.set(selectionId, {
                id: selectionId,
                document_id,
                selected_style: selectedStyle,
                style_config: styleConfig,
                recommendations: styleRecommendations,
                created_at: new Date().toISOString(),
                parameters: selectionRequest
            });

            this.emit('style-selected', {
                selectionId,
                document_id,
                selectedStyle,
                styleConfig
            });

            return {
                selection_id: selectionId,
                selected_style: selectedStyle,
                style_config: styleConfig,
                recommendations: styleRecommendations
            };

        } catch (error) {
            this.emit('style-selection-failed', { document_id, error });
            throw error;
        }
    }

    analyzeContentForStyle({ content_type, target_audience, expertise_level, tone_preference }) {
        const recommendations = {
            primary: null,
            alternatives: [],
            reasoning: []
        };

        // Content type based recommendations
        if (content_type === 'technical_documentation') {
            recommendations.primary = 'conversational_explain';
            recommendations.alternatives = ['investigative_interview', 'news_report'];
            recommendations.reasoning.push('Technical content benefits from clear explanations');
        } else if (content_type === 'opinion_piece') {
            recommendations.primary = 'structured_debate';
            recommendations.alternatives = ['investigative_interview', 'comedy_roast'];
            recommendations.reasoning.push('Opinion pieces create natural debate opportunities');
        } else if (content_type === 'story' || content_type === 'case_study') {
            recommendations.primary = 'narrative_storytelling';
            recommendations.alternatives = ['investigative_interview', 'conversational_explain'];
            recommendations.reasoning.push('Stories work well in narrative format');
        } else if (content_type === 'news' || content_type === 'factual_report') {
            recommendations.primary = 'news_report';
            recommendations.alternatives = ['conversational_explain', 'investigative_interview'];
            recommendations.reasoning.push('Factual content suits news reporting style');
        }

        // Tone preference adjustments
        if (tone_preference === 'humorous' || tone_preference === 'casual') {
            recommendations.alternatives.unshift('comedy_roast');
            if (recommendations.primary === 'conversational_explain') {
                recommendations.primary = 'comedy_roast';
                recommendations.reasoning.push('Humor preference suggests comedy approach');
            }
        } else if (tone_preference === 'formal' || tone_preference === 'professional') {
            recommendations.primary = recommendations.primary === 'comedy_roast' ? 'news_report' : recommendations.primary;
            recommendations.reasoning.push('Formal tone requires professional approach');
        }

        // Target audience considerations
        if (target_audience === 'children' || target_audience === 'beginners') {
            if (recommendations.primary !== 'conversational_explain') {
                recommendations.alternatives.unshift(recommendations.primary);
                recommendations.primary = 'conversational_explain';
                recommendations.reasoning.push('Beginner audience needs clear explanations');
            }
        } else if (target_audience === 'experts' || target_audience === 'professionals') {
            if (recommendations.primary === 'conversational_explain') {
                recommendations.primary = 'investigative_interview';
                recommendations.reasoning.push('Expert audience can handle deeper analysis');
            }
        }

        // Default fallback
        if (!recommendations.primary) {
            recommendations.primary = this.config.default_style;
            recommendations.reasoning.push('Using default style due to unclear content characteristics');
        }

        return recommendations;
    }

    applyContextualModifications(styleConfig, context) {
        const modified = { ...styleConfig };

        // Adjust based on desired length
        if (context.desired_length === 'short') {
            modified.dialogue_structure.body.elements = modified.dialogue_structure.body.elements.slice(0, 2);
            modified.conversation_flow.pacing = 'fast';
        } else if (context.desired_length === 'long') {
            modified.dialogue_structure.body.elements.push('deep_dive_questions', 'multiple_examples');
            modified.conversation_flow.pacing = 'slow';
        }

        // Adjust based on expertise level
        if (context.expertise_level === 'beginner') {
            modified.content_adaptation.complexity_handling = 'extra_simple';
            modified.content_adaptation.jargon_treatment = 'avoid_or_explain_immediately';
            modified.content_adaptation.examples = 'basic_analogies';
        } else if (context.expertise_level === 'expert') {
            modified.content_adaptation.complexity_handling = 'full_complexity';
            modified.content_adaptation.jargon_treatment = 'use_freely';
            modified.content_adaptation.examples = 'technical_specifics';
        }

        // Adjust based on target audience
        if (context.target_audience === 'children') {
            modified.conversation_flow.pacing = 'slow';
            modified.content_adaptation.examples = 'fun_analogies';
            // Use more friendly voice profiles
            Object.keys(modified.participants).forEach(participant => {
                if (modified.participants[participant].voice_profile.includes('professional')) {
                    modified.participants[participant].voice_profile = 'host_female_warm';
                }
            });
        }

        return modified;
    }

    applyCustomModifications(styleConfig, modifications) {
        const modified = { ...styleConfig };

        // Apply conversation flow modifications
        if (modifications.conversation_flow) {
            modified.conversation_flow = {
                ...modified.conversation_flow,
                ...modifications.conversation_flow
            };
        }

        // Apply participant modifications
        if (modifications.participants) {
            Object.keys(modifications.participants).forEach(participantKey => {
                if (modified.participants[participantKey]) {
                    modified.participants[participantKey] = {
                        ...modified.participants[participantKey],
                        ...modifications.participants[participantKey]
                    };
                }
            });
        }

        // Apply dialogue structure modifications
        if (modifications.dialogue_structure) {
            Object.keys(modifications.dialogue_structure).forEach(section => {
                if (modified.dialogue_structure[section]) {
                    modified.dialogue_structure[section] = {
                        ...modified.dialogue_structure[section],
                        ...modifications.dialogue_structure[section]
                    };
                }
            });
        }

        // Apply content adaptation modifications
        if (modifications.content_adaptation) {
            modified.content_adaptation = {
                ...modified.content_adaptation,
                ...modifications.content_adaptation
            };
        }

        return modified;
    }

    async createCustomStyle(customStyleDefinition) {
        const {
            id,
            name,
            description,
            based_on,
            modifications,
            creator
        } = customStyleDefinition;

        try {
            let baseStyle = {};
            
            if (based_on) {
                const base = this.conversationStyles.get(based_on);
                if (!base) {
                    throw new Error(`Base style not found: ${based_on}`);
                }
                baseStyle = { ...base };
            }

            // Apply modifications to create custom style
            const customStyle = {
                id,
                name,
                description,
                category: 'custom',
                based_on,
                creator,
                created_at: new Date().toISOString(),
                ...baseStyle,
                ...modifications
            };

            // Store custom style
            this.customStyles.set(id, customStyle);

            // Save to file
            const customStylePath = path.join(
                this.config.custom_styles_directory,
                `${id}.json`
            );
            await fs.writeFile(customStylePath, JSON.stringify(customStyle, null, 2));

            this.emit('custom-style-created', { id, name });

            return customStyle;

        } catch (error) {
            this.emit('custom-style-creation-failed', { id, error });
            throw error;
        }
    }

    getSelection(selectionId) {
        return this.activeSelections.get(selectionId);
    }

    async loadCustomStyles() {
        try {
            const files = await fs.readdir(this.config.custom_styles_directory);
            const jsonFiles = files.filter(file => file.endsWith('.json'));

            for (const file of jsonFiles) {
                const filePath = path.join(this.config.custom_styles_directory, file);
                const content = await fs.readFile(filePath, 'utf8');
                const customStyle = JSON.parse(content);
                this.customStyles.set(customStyle.id, customStyle);
            }

            this.emit('custom-styles-loaded', { count: jsonFiles.length });
        } catch (error) {
            this.emit('custom-styles-load-failed', { error });
        }
    }

    getCustomStyles() {
        return Array.from(this.customStyles.values());
    }

    updateSelection(selectionId, updates) {
        const selection = this.activeSelections.get(selectionId);
        if (!selection) {
            throw new Error(`Selection not found: ${selectionId}`);
        }

        const updatedSelection = {
            ...selection,
            ...updates,
            updated_at: new Date().toISOString()
        };

        this.activeSelections.set(selectionId, updatedSelection);
        this.emit('selection-updated', { selectionId, updates });

        return updatedSelection;
    }
}

export default StyleSelector;