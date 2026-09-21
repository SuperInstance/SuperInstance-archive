const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');

class AIDMPersonalityGenerator extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        this.personalityTemplates = {
            narrative_styles: {
                'theatrical': {
                    name: 'Theatrical Storyteller',
                    description: 'Dramatic, over-the-top descriptions with theatrical flair',
                    traits: ['dramatic_descriptions', 'character_voices', 'epic_moments'],
                    speech_patterns: ['grand gestures', 'dramatic pauses', 'vivid imagery']
                },
                'mysterious': {
                    name: 'Mysterious Guide',
                    description: 'Subtle hints, cryptic clues, and atmospheric tension',
                    traits: ['cryptic_hints', 'atmospheric_descriptions', 'subtle_foreshadowing'],
                    speech_patterns: ['whispered secrets', 'meaningful glances', 'pregnant pauses']
                },
                'tactical': {
                    name: 'Strategic Commander',
                    description: 'Focus on combat tactics, positioning, and strategic thinking',
                    traits: ['combat_focused', 'tactical_advice', 'strategic_thinking'],
                    speech_patterns: ['military terminology', 'precise descriptions', 'tactical analysis']
                },
                'whimsical': {
                    name: 'Whimsical Storyteller',
                    description: 'Light-hearted, fun, with unexpected twists and humor',
                    traits: ['comedic_timing', 'unexpected_twists', 'playful_descriptions'],
                    speech_patterns: ['dad jokes', 'silly voices', 'absurd situations']
                },
                'gritty': {
                    name: 'Gritty Realist',
                    description: 'Dark, realistic consequences with moral complexity',
                    traits: ['realistic_consequences', 'moral_dilemmas', 'harsh_realities'],
                    speech_patterns: ['blunt honesty', 'serious tone', 'consequence focus']
                },
                'scholarly': {
                    name: 'Scholarly Lorekeeper',
                    description: 'Rich world-building, detailed lore, and educational moments',
                    traits: ['detailed_lore', 'historical_context', 'educational_moments'],
                    speech_patterns: ['encyclopedia knowledge', 'historical references', 'detailed explanations']
                }
            },
            
            rule_interpretations: {
                'strict_rules': {
                    name: 'Rules as Written',
                    description: 'Follows RAW strictly, minimal house rules',
                    flexibility: 0.2,
                    house_rules: ['minimal_modifications', 'strict_spell_components', 'exact_measurements']
                },
                'flexible_narrative': {
                    name: 'Narrative First',
                    description: 'Rules serve the story, flexible interpretations',
                    flexibility: 0.8,
                    house_rules: ['rule_of_cool', 'narrative_advantage', 'creative_solutions']
                },
                'balanced_approach': {
                    name: 'Balanced Arbiter',
                    description: 'Balance between rules and narrative flow',
                    flexibility: 0.5,
                    house_rules: ['contextual_rulings', 'consistent_precedents', 'player_agency']
                },
                'experimental': {
                    name: 'Experimental Innovator',
                    description: 'Loves trying new mechanics and homebrew content',
                    flexibility: 0.9,
                    house_rules: ['homebrew_mechanics', 'experimental_rules', 'creative_interpretations']
                }
            },
            
            interaction_patterns: {
                'collaborative': {
                    name: 'Collaborative Partner',
                    description: 'Works with players to build the story together',
                    player_agency: 0.8,
                    traits: ['shared_narrative', 'player_input', 'collaborative_worldbuilding']
                },
                'guiding_mentor': {
                    name: 'Guiding Mentor',
                    description: 'Provides gentle guidance and teaching moments',
                    player_agency: 0.6,
                    traits: ['helpful_hints', 'teaching_moments', 'encouraging_feedback']
                },
                'challenging_adversary': {
                    name: 'Challenging Adversary',
                    description: 'Creates tough but fair challenges for growth',
                    player_agency: 0.4,
                    traits: ['strategic_challenges', 'growth_opportunities', 'earned_victories']
                },
                'neutral_arbiter': {
                    name: 'Neutral Arbiter',
                    description: 'Impartial judge who lets the dice decide',
                    player_agency: 0.5,
                    traits: ['impartial_rulings', 'dice_respect', 'fair_consequences']
                }
            },
            
            campaign_themes: {
                'heroic_fantasy': {
                    name: 'Heroic Fantasy',
                    description: 'Classic good vs evil with heroic protagonists',
                    tone: 'uplifting',
                    elements: ['noble_quests', 'clear_morality', 'heroic_moments']
                },
                'political_intrigue': {
                    name: 'Political Intrigue',
                    description: 'Complex politics, schemes, and moral ambiguity',
                    tone: 'complex',
                    elements: ['political_maneuvering', 'moral_ambiguity', 'social_dynamics']
                },
                'survival_horror': {
                    name: 'Survival Horror',
                    description: 'Resource management, fear, and psychological tension',
                    tone: 'tense',
                    elements: ['resource_scarcity', 'psychological_horror', 'survival_mechanics']
                },
                'exploration_discovery': {
                    name: 'Exploration & Discovery',
                    description: 'Unknown lands, ancient mysteries, and wonder',
                    tone: 'wonder',
                    elements: ['uncharted_territories', 'ancient_mysteries', 'discovery_moments']
                },
                'urban_adventure': {
                    name: 'Urban Adventure',
                    description: 'City-based adventures with social complexity',
                    tone: 'dynamic',
                    elements: ['city_politics', 'social_encounters', 'urban_exploration']
                }
            }
        };
        
        this.voicePatterns = {
            'authoritative': ['commands attention', 'speaks with certainty', 'uses declarative statements'],
            'friendly': ['warm tone', 'encouraging words', 'inclusive language'],
            'mysterious': ['speaks in riddles', 'leaves things unsaid', 'uses metaphors'],
            'energetic': ['exclamation points', 'rapid pace', 'enthusiasm'],
            'calm': ['measured speech', 'thoughtful pauses', 'soothing tone'],
            'scholarly': ['precise vocabulary', 'references sources', 'explains thoroughly']
        };
    }

    async generatePersonality(options = {}) {
        try {
            const personalityId = uuidv4();
            
            const personality = {
                id: personalityId,
                name: options.name || this._generatePersonalityName(),
                created_at: new Date(),
                
                narrative_style: this._selectNarrativeStyle(options.narrative_preference),
                rule_interpretation: this._selectRuleInterpretation(options.rule_preference),
                interaction_pattern: this._selectInteractionPattern(options.interaction_preference),
                campaign_theme: this._selectCampaignTheme(options.theme_preference),
                
                voice_characteristics: this._generateVoiceCharacteristics(),
                personality_quirks: this._generatePersonalityQuirks(),
                favorite_elements: this._generateFavoriteElements(),
                
                difficulty_preference: options.difficulty || this._randomChoice(['easy', 'moderate', 'hard', 'deadly']),
                roleplay_emphasis: Math.random() * 0.4 + 0.3, // 30-70%
                combat_emphasis: Math.random() * 0.4 + 0.3,   // 30-70%
                exploration_emphasis: Math.random() * 0.4 + 0.3, // 30-70%
                
                backstory: this._generateDMBackstory(),
                catch_phrases: this._generateCatchPhrases(),
                decision_making_style: this._generateDecisionMakingStyle(),
                
                stats: {
                    campaigns_run: 0,
                    player_satisfaction: 0,
                    memorable_moments: 0,
                    adaptability_score: Math.random()
                }
            };
            
            // Normalize emphasis values
            this._normalizeEmphasisValues(personality);
            
            await this.redis.setex(
                `dm_personality:${personalityId}`,
                86400 * 30, // 30 days
                JSON.stringify(personality)
            );
            
            this.logger.info(`Generated DM personality: ${personality.name} (${personalityId})`);
            this.io.emit('dm_personality_generated', { personalityId, name: personality.name });
            
            return personality;
            
        } catch (error) {
            this.logger.error('Error generating DM personality:', error);
            throw error;
        }
    }

    async getPersonality(personalityId) {
        try {
            const cached = await this.redis.get(`dm_personality:${personalityId}`);
            if (cached) {
                return JSON.parse(cached);
            }
            
            throw new Error('Personality not found');
            
        } catch (error) {
            this.logger.error('Error retrieving DM personality:', error);
            throw error;
        }
    }

    async updatePersonalityStats(personalityId, sessionData) {
        try {
            const personality = await this.getPersonality(personalityId);
            
            personality.stats.campaigns_run += 1;
            personality.stats.player_satisfaction = this._calculateSatisfaction(
                personality.stats.player_satisfaction,
                sessionData.satisfaction_score
            );
            
            if (sessionData.memorable_moments) {
                personality.stats.memorable_moments += sessionData.memorable_moments;
            }
            
            personality.stats.adaptability_score = this._updateAdaptability(
                personality.stats.adaptability_score,
                sessionData.adaptability_events
            );
            
            await this.redis.setex(
                `dm_personality:${personalityId}`,
                86400 * 30,
                JSON.stringify(personality)
            );
            
            this.logger.info(`Updated personality stats for ${personalityId}`);
            return personality.stats;
            
        } catch (error) {
            this.logger.error('Error updating personality stats:', error);
            throw error;
        }
    }

    async generatePersonalityResponse(personalityId, situation, context = {}) {
        try {
            const personality = await this.getPersonality(personalityId);
            const response = {
                response_text: this._generateContextualResponse(personality, situation, context),
                tone: this._determineResponseTone(personality, situation),
                suggestions: this._generateSuggestions(personality, situation),
                rule_guidance: this._generateRuleGuidance(personality, situation)
            };
            
            return response;
            
        } catch (error) {
            this.logger.error('Error generating personality response:', error);
            throw error;
        }
    }

    _selectNarrativeStyle(preference) {
        if (preference && this.personalityTemplates.narrative_styles[preference]) {
            return this.personalityTemplates.narrative_styles[preference];
        }
        
        const styles = Object.keys(this.personalityTemplates.narrative_styles);
        const selected = this._randomChoice(styles);
        return this.personalityTemplates.narrative_styles[selected];
    }

    _selectRuleInterpretation(preference) {
        if (preference && this.personalityTemplates.rule_interpretations[preference]) {
            return this.personalityTemplates.rule_interpretations[preference];
        }
        
        const interpretations = Object.keys(this.personalityTemplates.rule_interpretations);
        const selected = this._randomChoice(interpretations);
        return this.personalityTemplates.rule_interpretations[selected];
    }

    _selectInteractionPattern(preference) {
        if (preference && this.personalityTemplates.interaction_patterns[preference]) {
            return this.personalityTemplates.interaction_patterns[preference];
        }
        
        const patterns = Object.keys(this.personalityTemplates.interaction_patterns);
        const selected = this._randomChoice(patterns);
        return this.personalityTemplates.interaction_patterns[selected];
    }

    _selectCampaignTheme(preference) {
        if (preference && this.personalityTemplates.campaign_themes[preference]) {
            return this.personalityTemplates.campaign_themes[preference];
        }
        
        const themes = Object.keys(this.personalityTemplates.campaign_themes);
        const selected = this._randomChoice(themes);
        return this.personalityTemplates.campaign_themes[selected];
    }

    _generatePersonalityName() {
        const prefixes = ['The', 'Master', 'Keeper', 'Sage', 'Guardian', 'Weaver'];
        const descriptors = ['Mystical', 'Ancient', 'Wise', 'Cunning', 'Noble', 'Shadow'];
        const titles = ['Storyteller', 'Chronicler', 'Loremaster', 'Guide', 'Architect', 'Dreamweaver'];
        
        return `${this._randomChoice(prefixes)} ${this._randomChoice(descriptors)} ${this._randomChoice(titles)}`;
    }

    _generateVoiceCharacteristics() {
        const patterns = Object.keys(this.voicePatterns);
        const primary = this._randomChoice(patterns);
        const secondary = this._randomChoice(patterns.filter(p => p !== primary));
        
        return {
            primary_pattern: primary,
            secondary_pattern: secondary,
            speech_quirks: this.voicePatterns[primary].concat(this.voicePatterns[secondary].slice(0, 1)),
            volume: this._randomChoice(['quiet', 'normal', 'loud']),
            pace: this._randomChoice(['slow', 'normal', 'fast']),
            formality: Math.random()
        };
    }

    _generatePersonalityQuirks() {
        const quirks = [
            'Always references obscure lore',
            'Makes sound effects during combat',
            'Insists on authentic accents for NPCs',
            'Uses elaborate hand gestures',
            'Frequently checks rulebooks',
            'Creates detailed maps on the fly',
            'Speaks in character voices',
            'Uses props and miniatures extensively',
            'Keeps detailed campaign notes',
            'Loves unexpected plot twists'
        ];
        
        const numQuirks = Math.floor(Math.random() * 3) + 1;
        return this._randomChoices(quirks, numQuirks);
    }

    _generateFavoriteElements() {
        return {
            encounters: this._randomChoices(['dragons', 'puzzles', 'social_encounters', 'dungeon_crawls', 'wilderness_survival'], 2),
            mechanics: this._randomChoices(['skill_challenges', 'mass_combat', 'chase_scenes', 'investigation', 'politics'], 2),
            themes: this._randomChoices(['redemption', 'sacrifice', 'discovery', 'friendship', 'revenge'], 2),
            settings: this._randomChoices(['ancient_ruins', 'bustling_cities', 'mysterious_forests', 'underground_complexes', 'magical_academies'], 2)
        };
    }

    _generateDMBackstory() {
        const backgrounds = [
            'Former adventurer turned storyteller',
            'Scholarly researcher of ancient lore',
            'Tavern keeper who collected stories',
            'Court bard with a flair for drama',
            'Retired military strategist',
            'Wandering sage seeking wisdom'
        ];
        
        const motivations = [
            'loves seeing players succeed',
            'enjoys crafting memorable moments',
            'wants to share epic stories',
            'seeks to challenge player creativity',
            'aims to teach through adventure',
            'desires to build lasting friendships'
        ];
        
        return {
            background: this._randomChoice(backgrounds),
            motivation: this._randomChoice(motivations),
            experience: `${Math.floor(Math.random() * 15) + 1} years of storytelling`
        };
    }

    _generateCatchPhrases() {
        const phrases = [
            'Roll for initiative!',
            'What do you do?',
            'The dice have spoken',
            'Make it interesting',
            'Trust the process',
            'Every choice has consequences'
        ];
        
        return this._randomChoices(phrases, 2);
    }

    _generateDecisionMakingStyle() {
        const styles = {
            'consensus_builder': 'Seeks group agreement before major decisions',
            'quick_decider': 'Makes fast rulings to maintain game flow',
            'deliberative': 'Takes time to consider all angles',
            'intuitive': 'Relies on gut feelings and story needs',
            'analytical': 'Breaks down problems systematically'
        };
        
        const selected = this._randomChoice(Object.keys(styles));
        return {
            style: selected,
            description: styles[selected],
            confidence_level: Math.random() * 0.5 + 0.5 // 50-100%
        };
    }

    _normalizeEmphasisValues(personality) {
        const total = personality.roleplay_emphasis + 
                     personality.combat_emphasis + 
                     personality.exploration_emphasis;
        
        personality.roleplay_emphasis /= total;
        personality.combat_emphasis /= total;
        personality.exploration_emphasis /= total;
    }

    _generateContextualResponse(personality, situation, context) {
        const style = personality.narrative_style;
        const baseResponse = this._getBaseResponse(situation);
        
        switch (style.name) {
            case 'Theatrical Storyteller':
                return this._makeTheatrical(baseResponse);
            case 'Mysterious Guide':
                return this._makeMysterious(baseResponse);
            case 'Strategic Commander':
                return this._makeTactical(baseResponse);
            case 'Whimsical Storyteller':
                return this._makeWhimsical(baseResponse);
            case 'Gritty Realist':
                return this._makeGritty(baseResponse);
            case 'Scholarly Lorekeeper':
                return this._makeScholarly(baseResponse);
            default:
                return baseResponse;
        }
    }

    _getBaseResponse(situation) {
        const responses = {
            'combat_start': 'The battle begins! Everyone roll for initiative.',
            'skill_check': 'This seems like a good time for a skill check.',
            'roleplay_moment': 'What does your character say or do?',
            'rules_question': 'Let me check how this works in the rules.',
            'player_creativity': 'That\'s an interesting approach! Let\'s see how it plays out.'
        };
        
        return responses[situation] || 'What happens next is up to you.';
    }

    _makeTheatrical(response) {
        return `*dramatic gesture* ${response} *eyes gleaming with excitement*`;
    }

    _makeMysterious(response) {
        return `*leans forward with a knowing smile* ${response} *cryptic glance*`;
    }

    _makeTactical(response) {
        return `*studying the battlefield* ${response} Consider your positioning carefully.`;
    }

    _makeWhimsical(response) {
        return `*chuckling* ${response} This should be fun! *mischievous grin*`;
    }

    _makeGritty(response) {
        return `*serious expression* ${response} Remember, actions have consequences.`;
    }

    _makeScholarly(response) {
        return `*adjusting spectacles* ${response} As the ancient texts suggest...`;
    }

    _determineResponseTone(personality, situation) {
        const base_tone = personality.campaign_theme.tone;
        const voice_influence = personality.voice_characteristics.primary_pattern;
        
        return {
            base: base_tone,
            modifier: voice_influence,
            intensity: Math.random() * 0.5 + 0.5
        };
    }

    _generateSuggestions(personality, situation) {
        return [
            'Consider multiple approaches to this challenge',
            'Think about your character\'s motivations',
            'Remember your party\'s strengths and resources'
        ];
    }

    _generateRuleGuidance(personality, situation) {
        const flexibility = personality.rule_interpretation.flexibility;
        
        if (flexibility > 0.7) {
            return 'I\'m flexible on the rules here - let\'s focus on what makes the best story.';
        } else if (flexibility < 0.3) {
            return 'Let me check the exact wording in the rulebook to make sure we get this right.';
        } else {
            return 'I\'ll make a fair ruling that keeps the game moving while respecting the rules.';
        }
    }

    _calculateSatisfaction(currentSatisfaction, newScore) {
        return (currentSatisfaction * 0.8) + (newScore * 0.2);
    }

    _updateAdaptability(currentScore, events) {
        if (!events || events.length === 0) return currentScore;
        
        const adaptabilityBoost = events.length * 0.1;
        return Math.min(1.0, currentScore + adaptabilityBoost);
    }

    async getStats() {
        try {
            const keys = await this.redis.keys('dm_personality:*');
            const totalPersonalities = keys.length;
            
            let totalSatisfaction = 0;
            let totalCampaigns = 0;
            
            for (const key of keys.slice(0, 100)) { // Sample first 100
                const data = await this.redis.get(key);
                if (data) {
                    const personality = JSON.parse(data);
                    totalSatisfaction += personality.stats.player_satisfaction || 0;
                    totalCampaigns += personality.stats.campaigns_run || 0;
                }
            }
            
            return {
                total_personalities: totalPersonalities,
                average_satisfaction: totalPersonalities > 0 ? totalSatisfaction / totalPersonalities : 0,
                total_campaigns: totalCampaigns,
                generated_today: 0 // Could implement daily tracking
            };
            
        } catch (error) {
            this.logger.error('Error getting DM personality stats:', error);
            return {
                total_personalities: 0,
                average_satisfaction: 0,
                total_campaigns: 0,
                generated_today: 0
            };
        }
    }

    _randomChoice(array) {
        return array[Math.floor(Math.random() * array.length)];
    }

    _randomChoices(array, count) {
        const shuffled = [...array].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, count);
    }
}

module.exports = AIDMPersonalityGenerator;