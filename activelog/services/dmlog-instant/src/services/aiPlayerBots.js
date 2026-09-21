const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');

class AIPlayerBots extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        this.personalityArchetypes = {
            'brave_leader': {
                name: 'The Brave Leader',
                description: 'Natural leader who takes charge and protects others',
                traits: ['courageous', 'protective', 'decisive', 'inspiring'],
                preferred_actions: ['charge_into_combat', 'rally_allies', 'make_tactical_decisions'],
                speech_patterns: ['commanding', 'encouraging', 'direct'],
                roleplay_tendency: 0.7,
                combat_aggression: 0.8,
                risk_tolerance: 0.6
            },
            'clever_trickster': {
                name: 'The Clever Trickster',
                description: 'Witty and cunning, prefers creative solutions',
                traits: ['clever', 'mischievous', 'creative', 'observant'],
                preferred_actions: ['find_creative_solutions', 'use_environment', 'trick_enemies'],
                speech_patterns: ['witty', 'sarcastic', 'playful'],
                roleplay_tendency: 0.9,
                combat_aggression: 0.4,
                risk_tolerance: 0.7
            },
            'wise_mentor': {
                name: 'The Wise Mentor',
                description: 'Experienced advisor who guides the party with wisdom',
                traits: ['wise', 'patient', 'knowledgeable', 'calm'],
                preferred_actions: ['give_advice', 'analyze_situations', 'share_knowledge'],
                speech_patterns: ['thoughtful', 'measured', 'philosophical'],
                roleplay_tendency: 0.8,
                combat_aggression: 0.3,
                risk_tolerance: 0.2
            },
            'fierce_warrior': {
                name: 'The Fierce Warrior',
                description: 'Combat-focused fighter who lives for battle',
                traits: ['fierce', 'straightforward', 'honorable', 'competitive'],
                preferred_actions: ['engage_in_combat', 'challenge_strong_foes', 'train_skills'],
                speech_patterns: ['blunt', 'direct', 'battle_focused'],
                roleplay_tendency: 0.4,
                combat_aggression: 0.9,
                risk_tolerance: 0.8
            },
            'curious_scholar': {
                name: 'The Curious Scholar',
                description: 'Intellectual who seeks knowledge and understanding',
                traits: ['intelligent', 'curious', 'methodical', 'cautious'],
                preferred_actions: ['investigate_mysteries', 'research_lore', 'analyze_magic'],
                speech_patterns: ['academic', 'precise', 'questioning'],
                roleplay_tendency: 0.6,
                combat_aggression: 0.2,
                risk_tolerance: 0.3
            },
            'loyal_friend': {
                name: 'The Loyal Friend',
                description: 'Devoted companion who values friendship above all',
                traits: ['loyal', 'supportive', 'empathetic', 'selfless'],
                preferred_actions: ['help_allies', 'maintain_relationships', 'heal_others'],
                speech_patterns: ['warm', 'supportive', 'caring'],
                roleplay_tendency: 0.8,
                combat_aggression: 0.5,
                risk_tolerance: 0.4
            },
            'mysterious_loner': {
                name: 'The Mysterious Loner',
                description: 'Enigmatic figure with hidden depths and secrets',
                traits: ['secretive', 'independent', 'perceptive', 'complex'],
                preferred_actions: ['work_alone', 'gather_information', 'stay_in_shadows'],
                speech_patterns: ['cryptic', 'brief', 'meaningful'],
                roleplay_tendency: 0.7,
                combat_aggression: 0.6,
                risk_tolerance: 0.5
            },
            'optimistic_healer': {
                name: 'The Optimistic Healer',
                description: 'Positive spirit who believes in the good in everyone',
                traits: ['optimistic', 'compassionate', 'peaceful', 'hopeful'],
                preferred_actions: ['heal_injuries', 'resolve_conflicts', 'encourage_others'],
                speech_patterns: ['uplifting', 'gentle', 'positive'],
                roleplay_tendency: 0.9,
                combat_aggression: 0.1,
                risk_tolerance: 0.3
            }
        };
        
        this.classPreferences = {
            'brave_leader': ['paladin', 'fighter', 'warlord'],
            'clever_trickster': ['rogue', 'bard', 'artificer'],
            'wise_mentor': ['wizard', 'cleric', 'druid'],
            'fierce_warrior': ['barbarian', 'fighter', 'ranger'],
            'curious_scholar': ['wizard', 'artificer', 'warlock'],
            'loyal_friend': ['cleric', 'paladin', 'bard'],
            'mysterious_loner': ['rogue', 'ranger', 'warlock'],
            'optimistic_healer': ['cleric', 'druid', 'bard']
        };
        
        this.decisionFactors = {
            combat: {
                aggressive: ['charge_enemy', 'use_powerful_attack', 'take_risks'],
                defensive: ['protect_allies', 'use_defensive_abilities', 'position_carefully'],
                tactical: ['analyze_battlefield', 'coordinate_with_team', 'exploit_weaknesses'],
                supportive: ['heal_allies', 'buff_teammates', 'provide_assistance']
            },
            social: {
                charismatic: ['lead_conversation', 'persuade_npcs', 'make_friends'],
                diplomatic: ['negotiate_peace', 'find_compromise', 'mediate_conflicts'],
                intimidating: ['threaten_enemies', 'assert_dominance', 'use_fear'],
                deceptive: ['lie_convincingly', 'manipulate_information', 'create_distractions']
            },
            exploration: {
                cautious: ['check_for_traps', 'move_slowly', 'prepare_for_danger'],
                bold: ['lead_the_way', 'take_shortcuts', 'explore_everything'],
                methodical: ['map_areas', 'document_findings', 'systematic_search'],
                intuitive: ['follow_hunches', 'trust_instincts', 'notice_details']
            }
        };
    }

    async createPlayerBot(options = {}) {
        try {
            const botId = uuidv4();
            const archetype = this._selectArchetype(options.personality_preference);
            const characterClass = this._selectClass(archetype, options.class_preference);
            const character = this._generateCharacterStats(characterClass);
            
            const bot = {
                id: botId,
                name: options.name || this._generateBotName(archetype),
                archetype: archetype,
                character: character,
                personality: this._generateDetailedPersonality(archetype),
                relationships: {},
                memory: {
                    important_events: [],
                    npc_relationships: {},
                    learned_information: {},
                    personal_goals: this._generatePersonalGoals(archetype)
                },
                behavior_patterns: this._generateBehaviorPatterns(archetype),
                stats: {
                    sessions_played: 0,
                    memorable_moments: 0,
                    successful_actions: 0,
                    character_development: 0
                },
                created_at: new Date()
            };
            
            await this.redis.setex(
                `player_bot:${botId}`,
                86400 * 30, // 30 days
                JSON.stringify(bot)
            );
            
            this.logger.info(`Created player bot: ${bot.name} (${botId})`);
            this.io.emit('player_bot_created', { botId, name: bot.name, archetype: archetype.name });
            
            return bot;
            
        } catch (error) {
            this.logger.error('Error creating player bot:', error);
            throw error;
        }
    }

    async generateBotAction(botId, context) {
        try {
            const bot = await this.getPlayerBot(botId);
            const action = await this._decideAction(bot, context);
            
            // Update bot's memory with new context
            await this._updateBotMemory(bot, context, action);
            
            // Update bot stats
            bot.stats.successful_actions += action.success_probability > 0.6 ? 1 : 0;
            
            await this.redis.setex(
                `player_bot:${botId}`,
                86400 * 30,
                JSON.stringify(bot)
            );
            
            this.logger.info(`Bot ${bot.name} decided on action: ${action.type}`);
            this.io.emit('bot_action_generated', { botId, action });
            
            return action;
            
        } catch (error) {
            this.logger.error('Error generating bot action:', error);
            throw error;
        }
    }

    async getPlayerBot(botId) {
        try {
            const cached = await this.redis.get(`player_bot:${botId}`);
            if (cached) {
                return JSON.parse(cached);
            }
            
            throw new Error('Player bot not found');
            
        } catch (error) {
            this.logger.error('Error retrieving player bot:', error);
            throw error;
        }
    }

    async updateBotRelationships(botId, relationshipData) {
        try {
            const bot = await this.getPlayerBot(botId);
            
            for (const [entityId, relationship] of Object.entries(relationshipData)) {
                if (!bot.relationships[entityId]) {
                    bot.relationships[entityId] = {
                        type: relationship.type, // 'player', 'npc', 'faction'
                        name: relationship.name,
                        trust_level: 0.5,
                        affection: 0.5,
                        respect: 0.5,
                        history: []
                    };
                }
                
                // Update relationship based on recent interactions
                this._updateRelationshipValues(bot.relationships[entityId], relationship.interaction);
            }
            
            await this.redis.setex(
                `player_bot:${botId}`,
                86400 * 30,
                JSON.stringify(bot)
            );
            
            return bot.relationships;
            
        } catch (error) {
            this.logger.error('Error updating bot relationships:', error);
            throw error;
        }
    }

    async generateBotDialogue(botId, situation, targetId = null) {
        try {
            const bot = await this.getPlayerBot(botId);
            const dialogue = this._createDialogue(bot, situation, targetId);
            
            return {
                speaker: bot.name,
                text: dialogue.text,
                emotion: dialogue.emotion,
                intent: dialogue.intent,
                delivery_style: dialogue.delivery_style
            };
            
        } catch (error) {
            this.logger.error('Error generating bot dialogue:', error);
            throw error;
        }
    }

    _selectArchetype(preference) {
        if (preference && this.personalityArchetypes[preference]) {
            return this.personalityArchetypes[preference];
        }
        
        const archetypes = Object.keys(this.personalityArchetypes);
        const selected = this._randomChoice(archetypes);
        return this.personalityArchetypes[selected];
    }

    _selectClass(archetype, preference) {
        if (preference) {
            return preference.toLowerCase();
        }
        
        const archetypeKey = Object.keys(this.personalityArchetypes).find(
            key => this.personalityArchetypes[key] === archetype
        );
        
        const preferredClasses = this.classPreferences[archetypeKey] || ['fighter'];
        return this._randomChoice(preferredClasses);
    }

    _generateCharacterStats(characterClass) {
        const baseStats = {
            level: Math.floor(Math.random() * 10) + 1,
            class: characterClass,
            race: this._randomChoice(['human', 'elf', 'dwarf', 'halfling', 'dragonborn', 'tiefling']),
            attributes: {
                strength: this._rollStats(),
                dexterity: this._rollStats(),
                constitution: this._rollStats(),
                intelligence: this._rollStats(),
                wisdom: this._rollStats(),
                charisma: this._rollStats()
            },
            skills: this._generateSkills(characterClass),
            equipment: this._generateEquipment(characterClass),
            background: this._generateBackground()
        };
        
        // Adjust stats based on class
        this._adjustStatsForClass(baseStats, characterClass);
        
        return baseStats;
    }

    _rollStats() {
        // 4d6, drop lowest
        const rolls = Array.from({ length: 4 }, () => Math.floor(Math.random() * 6) + 1);
        rolls.sort((a, b) => b - a);
        return rolls.slice(0, 3).reduce((sum, val) => sum + val, 0);
    }

    _generateSkills(characterClass) {
        const classSkills = {
            fighter: ['Athletics', 'Intimidation', 'Survival'],
            rogue: ['Stealth', 'Sleight of Hand', 'Deception'],
            wizard: ['Arcana', 'History', 'Investigation'],
            cleric: ['Medicine', 'Religion', 'Insight'],
            ranger: ['Survival', 'Animal Handling', 'Nature'],
            bard: ['Performance', 'Persuasion', 'Deception'],
            barbarian: ['Athletics', 'Intimidation', 'Survival'],
            paladin: ['Athletics', 'Religion', 'Persuasion'],
            warlock: ['Deception', 'Intimidation', 'Arcana'],
            druid: ['Medicine', 'Nature', 'Animal Handling'],
            artificer: ['Arcana', 'Investigation', 'Medicine']
        };
        
        return classSkills[characterClass] || ['Athletics', 'Perception', 'Insight'];
    }

    _generateEquipment(characterClass) {
        const classEquipment = {
            fighter: ['Longsword', 'Shield', 'Chain Mail', 'Adventurer\'s Pack'],
            rogue: ['Shortsword', 'Shortbow', 'Leather Armor', 'Thieves\' Tools'],
            wizard: ['Quarterstaff', 'Spellbook', 'Robes', 'Component Pouch'],
            cleric: ['Mace', 'Shield', 'Scale Mail', 'Holy Symbol'],
            ranger: ['Longbow', 'Shortsword', 'Leather Armor', 'Explorer\'s Pack'],
            bard: ['Rapier', 'Lute', 'Leather Armor', 'Entertainer\'s Pack'],
            barbarian: ['Greataxe', 'Handaxe', 'Leather Armor', 'Explorer\'s Pack'],
            paladin: ['Longsword', 'Shield', 'Chain Mail', 'Holy Symbol'],
            warlock: ['Light Crossbow', 'Dagger', 'Leather Armor', 'Scholar\'s Pack'],
            druid: ['Scimitar', 'Shield', 'Leather Armor', 'Druidcraft Focus'],
            artificer: ['Light Crossbow', 'Dagger', 'Studded Leather', 'Tinker\'s Tools']
        };
        
        return classEquipment[characterClass] || ['Club', 'Leather Armor', 'Explorer\'s Pack'];
    }

    _generateBackground() {
        const backgrounds = [
            'Acolyte', 'Criminal', 'Folk Hero', 'Noble', 'Sage', 'Soldier',
            'Charlatan', 'Entertainer', 'Guild Artisan', 'Hermit', 'Outlander', 'Sailor'
        ];
        
        return this._randomChoice(backgrounds);
    }

    _adjustStatsForClass(stats, characterClass) {
        const classAdjustments = {
            fighter: { strength: 2, constitution: 1 },
            rogue: { dexterity: 2, intelligence: 1 },
            wizard: { intelligence: 2, wisdom: 1 },
            cleric: { wisdom: 2, strength: 1 },
            ranger: { dexterity: 1, wisdom: 2 },
            bard: { charisma: 2, dexterity: 1 },
            barbarian: { strength: 2, constitution: 1 },
            paladin: { strength: 1, charisma: 2 },
            warlock: { charisma: 2, constitution: 1 },
            druid: { wisdom: 2, constitution: 1 },
            artificer: { intelligence: 2, constitution: 1 }
        };
        
        const adjustments = classAdjustments[characterClass];
        if (adjustments) {
            for (const [attr, bonus] of Object.entries(adjustments)) {
                stats.attributes[attr] = Math.min(20, stats.attributes[attr] + bonus);
            }
        }
    }

    _generateDetailedPersonality(archetype) {
        return {
            core_traits: archetype.traits,
            speech_style: this._randomChoice(archetype.speech_patterns),
            quirks: this._generatePersonalityQuirks(),
            motivations: this._generateMotivations(archetype),
            fears: this._generateFears(),
            values: this._generateValues(archetype),
            emotional_range: {
                default_mood: this._randomChoice(['cheerful', 'serious', 'calm', 'energetic']),
                stress_response: this._randomChoice(['fight', 'flight', 'freeze', 'analyze']),
                social_energy: Math.random()
            }
        };
    }

    _generatePersonalityQuirks() {
        const quirks = [
            'Always checks equipment before entering new areas',
            'Collects interesting stones or trinkets',
            'Hums quietly when thinking',
            'Makes jokes to lighten tense situations',
            'Keeps a detailed journal of adventures',
            'Always sits facing the door',
            'Talks to animals as if they understand',
            'Never backs down from a challenge',
            'Quotes old sayings frequently',
            'Fidgets with equipment when nervous'
        ];
        
        return this._randomChoices(quirks, Math.floor(Math.random() * 3) + 1);
    }

    _generateMotivations(archetype) {
        const motivationSets = {
            'brave_leader': ['protect the innocent', 'build a better world', 'prove worthy of trust'],
            'clever_trickster': ['outsmart opponents', 'find creative solutions', 'uncover secrets'],
            'wise_mentor': ['share knowledge', 'guide others to wisdom', 'preserve traditions'],
            'fierce_warrior': ['test combat skills', 'earn glory in battle', 'protect homeland'],
            'curious_scholar': ['discover new knowledge', 'solve mysteries', 'understand magic'],
            'loyal_friend': ['support companions', 'maintain friendships', 'create harmony'],
            'mysterious_loner': ['maintain independence', 'protect secrets', 'find inner peace'],
            'optimistic_healer': ['reduce suffering', 'spread hope', 'heal the world']
        };
        
        const archetypeKey = Object.keys(this.personalityArchetypes).find(
            key => this.personalityArchetypes[key] === archetype
        );
        
        return motivationSets[archetypeKey] || ['seek adventure', 'help others', 'grow stronger'];
    }

    _generateFears() {
        const fears = [
            'losing close friends', 'being powerless to help', 'facing overwhelming darkness',
            'betraying trust', 'being forgotten', 'losing control', 'failing in duty',
            'being alone forever', 'causing harm to innocents', 'facing own mortality'
        ];
        
        return this._randomChoices(fears, Math.floor(Math.random() * 2) + 1);
    }

    _generateValues(archetype) {
        const valueSets = {
            'brave_leader': ['courage', 'justice', 'loyalty'],
            'clever_trickster': ['freedom', 'creativity', 'wit'],
            'wise_mentor': ['wisdom', 'patience', 'tradition'],
            'fierce_warrior': ['honor', 'strength', 'competition'],
            'curious_scholar': ['knowledge', 'truth', 'discovery'],
            'loyal_friend': ['friendship', 'trust', 'compassion'],
            'mysterious_loner': ['independence', 'mystery', 'self-reliance'],
            'optimistic_healer': ['hope', 'healing', 'peace']
        };
        
        const archetypeKey = Object.keys(this.personalityArchetypes).find(
            key => this.personalityArchetypes[key] === archetype
        );
        
        return valueSets[archetypeKey] || ['honor', 'friendship', 'adventure'];
    }

    _generatePersonalGoals(archetype) {
        const goals = [
            'Master a particular skill or ability',
            'Find a long-lost family member',
            'Establish a reputation in their field',
            'Create something lasting and meaningful',
            'Overcome a personal weakness or fear',
            'Build strong relationships with the party',
            'Discover the truth about their past',
            'Make amends for a past mistake'
        ];
        
        return this._randomChoices(goals, 2);
    }

    _generateBehaviorPatterns(archetype) {
        return {
            combat_preference: this._getCombatPreference(archetype),
            social_preference: this._getSocialPreference(archetype),
            exploration_preference: this._getExplorationPreference(archetype),
            decision_making_speed: Math.random(),
            group_vs_solo_preference: archetype.traits.includes('independent') ? 0.3 : 0.7,
            risk_assessment: archetype.risk_tolerance
        };
    }

    _getCombatPreference(archetype) {
        if (archetype.combat_aggression > 0.7) return 'aggressive';
        if (archetype.combat_aggression < 0.3) return 'defensive';
        if (archetype.traits.includes('clever')) return 'tactical';
        return 'supportive';
    }

    _getSocialPreference(archetype) {
        if (archetype.traits.includes('inspiring')) return 'charismatic';
        if (archetype.traits.includes('wise')) return 'diplomatic';
        if (archetype.traits.includes('fierce')) return 'intimidating';
        return 'diplomatic';
    }

    _getExplorationPreference(archetype) {
        if (archetype.traits.includes('cautious')) return 'cautious';
        if (archetype.traits.includes('courageous')) return 'bold';
        if (archetype.traits.includes('methodical')) return 'methodical';
        return 'intuitive';
    }

    async _decideAction(bot, context) {
        const situationType = context.situation_type; // 'combat', 'social', 'exploration'
        const availableActions = context.available_actions || [];
        
        let preferredActions = [];
        
        switch (situationType) {
            case 'combat':
                preferredActions = this._getCombatActions(bot, context);
                break;
            case 'social':
                preferredActions = this._getSocialActions(bot, context);
                break;
            case 'exploration':
                preferredActions = this._getExplorationActions(bot, context);
                break;
            default:
                preferredActions = availableActions;
        }
        
        const selectedAction = this._selectBestAction(bot, preferredActions, context);
        
        return {
            type: selectedAction.type,
            description: selectedAction.description,
            reasoning: this._generateReasoning(bot, selectedAction, context),
            confidence: selectedAction.confidence,
            success_probability: this._estimateSuccessProbability(bot, selectedAction, context),
            roleplay_flavor: this._addRoleplayFlavor(bot, selectedAction)
        };
    }

    _getCombatActions(bot, context) {
        const preference = bot.behavior_patterns.combat_preference;
        const factorActions = this.decisionFactors.combat[preference] || [];
        
        return factorActions.map(action => ({
            type: action,
            description: this._getActionDescription(action),
            confidence: this._calculateActionConfidence(bot, action, context)
        }));
    }

    _getSocialActions(bot, context) {
        const preference = bot.behavior_patterns.social_preference;
        const factorActions = this.decisionFactors.social[preference] || [];
        
        return factorActions.map(action => ({
            type: action,
            description: this._getActionDescription(action),
            confidence: this._calculateActionConfidence(bot, action, context)
        }));
    }

    _getExplorationActions(bot, context) {
        const preference = bot.behavior_patterns.exploration_preference;
        const factorActions = this.decisionFactors.exploration[preference] || [];
        
        return factorActions.map(action => ({
            type: action,
            description: this._getActionDescription(action),
            confidence: this._calculateActionConfidence(bot, action, context)
        }));
    }

    _getActionDescription(actionType) {
        const descriptions = {
            'charge_enemy': 'Charges directly at the nearest enemy',
            'protect_allies': 'Moves to defend vulnerable allies',
            'use_environment': 'Uses environmental features creatively',
            'lead_conversation': 'Takes charge of social interactions',
            'check_for_traps': 'Carefully examines the area for dangers',
            'rally_allies': 'Encourages and motivates the party'
        };
        
        return descriptions[actionType] || `Performs ${actionType.replace('_', ' ')}`;
    }

    _calculateActionConfidence(bot, action, context) {
        let confidence = 0.5; // Base confidence
        
        // Adjust based on bot's traits and preferences
        if (bot.archetype.preferred_actions.some(pa => action.includes(pa))) {
            confidence += 0.3;
        }
        
        // Adjust based on context
        if (context.party_needs && context.party_needs.includes(action)) {
            confidence += 0.2;
        }
        
        // Adjust based on past success
        if (bot.stats.successful_actions > 10) {
            confidence += 0.1;
        }
        
        return Math.min(1.0, confidence);
    }

    _selectBestAction(bot, actions, context) {
        if (actions.length === 0) {
            return {
                type: 'default_action',
                description: 'Takes a standard action',
                confidence: 0.5
            };
        }
        
        // Weight actions by confidence and personality fit
        const weightedActions = actions.map(action => ({
            ...action,
            weight: action.confidence * this._getPersonalityWeight(bot, action)
        }));
        
        // Sort by weight and add some randomness
        weightedActions.sort((a, b) => b.weight - a.weight);
        
        // Select from top 3 actions with some randomness
        const topActions = weightedActions.slice(0, 3);
        const randomIndex = Math.floor(Math.random() * topActions.length);
        
        return topActions[randomIndex];
    }

    _getPersonalityWeight(bot, action) {
        let weight = 1.0;
        
        // Increase weight for actions that align with personality
        if (bot.archetype.preferred_actions.some(pa => action.type.includes(pa))) {
            weight *= 1.5;
        }
        
        // Adjust based on roleplay tendency
        if (action.type.includes('roleplay') || action.type.includes('social')) {
            weight *= bot.archetype.roleplay_tendency;
        }
        
        return weight;
    }

    _generateReasoning(bot, action, context) {
        const reasoningTemplates = [
            `${bot.name} believes this action aligns with their values of ${bot.personality.values.join(' and ')}.`,
            `Given the situation, ${bot.name} thinks this is what a ${bot.archetype.name.toLowerCase()} would do.`,
            `${bot.name} remembers similar situations and feels this approach worked before.`,
            `This action fits ${bot.name}'s personality and should help the party.`
        ];
        
        return this._randomChoice(reasoningTemplates);
    }

    _estimateSuccessProbability(bot, action, context) {
        let probability = 0.5; // Base 50%
        
        // Adjust based on relevant attributes
        const relevantAttribute = this._getRelevantAttribute(action.type);
        if (relevantAttribute && bot.character.attributes[relevantAttribute]) {
            const attributeModifier = Math.floor((bot.character.attributes[relevantAttribute] - 10) / 2);
            probability += (attributeModifier / 20); // Convert modifier to probability adjustment
        }
        
        // Adjust based on context difficulty
        if (context.difficulty) {
            probability -= (context.difficulty - 0.5) * 0.3;
        }
        
        return Math.max(0.1, Math.min(0.9, probability));
    }

    _getRelevantAttribute(actionType) {
        const attributeMap = {
            'charge_enemy': 'strength',
            'use_environment': 'intelligence',
            'lead_conversation': 'charisma',
            'check_for_traps': 'wisdom',
            'protect_allies': 'constitution',
            'rally_allies': 'charisma'
        };
        
        return attributeMap[actionType] || 'wisdom';
    }

    _addRoleplayFlavor(bot, action) {
        const flavorTexts = [
            `"${this._generateQuote(bot, action.type)}" says ${bot.name}.`,
            `${bot.name} ${this._getCharacteristicAction(bot)} while ${action.type.replace('_', 'ing ')}.`,
            `With a ${bot.personality.emotional_range.default_mood} expression, ${bot.name} ${action.description.toLowerCase()}.`
        ];
        
        return this._randomChoice(flavorTexts);
    }

    _generateQuote(bot, actionType) {
        const quotes = {
            'charge_enemy': ['For glory!', 'Stand and fight!', 'I\'ll lead the charge!'],
            'protect_allies': ['I\'ve got your back!', 'Nobody gets past me!', 'Stay behind me!'],
            'use_environment': ['Let me try something...', 'I have an idea!', 'This might work...'],
            'lead_conversation': ['Let me handle this.', 'Allow me to speak.', 'I know what to say.']
        };
        
        const actionQuotes = quotes[actionType] || ['Let\'s do this!', 'Here goes nothing!', 'Worth a try!'];
        return this._randomChoice(actionQuotes);
    }

    _getCharacteristicAction(bot) {
        const actions = {
            'brave_leader': 'stands tall',
            'clever_trickster': 'grins mischievously',
            'wise_mentor': 'strokes their chin thoughtfully',
            'fierce_warrior': 'clenches their fists',
            'curious_scholar': 'adjusts their glasses',
            'loyal_friend': 'looks to their companions',
            'mysterious_loner': 'pulls their hood up',
            'optimistic_healer': 'smiles warmly'
        };
        
        const archetypeKey = Object.keys(this.personalityArchetypes).find(
            key => this.personalityArchetypes[key] === bot.archetype
        );
        
        return actions[archetypeKey] || 'prepares for action';
    }

    async _updateBotMemory(bot, context, action) {
        // Add important events to memory
        if (context.importance && context.importance > 0.7) {
            bot.memory.important_events.push({
                event: context.description || 'Important event occurred',
                action_taken: action.type,
                timestamp: new Date(),
                outcome: context.outcome || 'pending'
            });
            
            // Keep only recent important events
            if (bot.memory.important_events.length > 20) {
                bot.memory.important_events = bot.memory.important_events.slice(-20);
            }
        }
        
        // Update learned information
        if (context.new_information) {
            for (const [topic, info] of Object.entries(context.new_information)) {
                bot.memory.learned_information[topic] = info;
            }
        }
    }

    _updateRelationshipValues(relationship, interaction) {
        const adjustments = {
            'positive_interaction': { trust: 0.1, affection: 0.1, respect: 0.05 },
            'negative_interaction': { trust: -0.1, affection: -0.1, respect: -0.05 },
            'helpful_action': { trust: 0.15, respect: 0.1 },
            'betrayal': { trust: -0.3, affection: -0.2, respect: -0.1 },
            'heroic_moment': { respect: 0.2, affection: 0.1 }
        };
        
        const adjustment = adjustments[interaction.type] || {};
        
        for (const [attr, change] of Object.entries(adjustment)) {
            relationship[`${attr}_level`] = Math.max(0, Math.min(1, 
                relationship[`${attr}_level`] + change
            ));
        }
        
        relationship.history.push({
            interaction_type: interaction.type,
            description: interaction.description,
            timestamp: new Date()
        });
        
        // Keep only recent history
        if (relationship.history.length > 10) {
            relationship.history = relationship.history.slice(-10);
        }
    }

    _createDialogue(bot, situation, targetId) {
        const personality = bot.personality;
        const archetype = bot.archetype;
        
        let baseText = '';
        let emotion = personality.emotional_range.default_mood;
        let intent = 'general';
        
        switch (situation) {
            case 'greeting':
                baseText = this._generateGreeting(bot);
                emotion = 'friendly';
                intent = 'social_bonding';
                break;
            case 'combat_start':
                baseText = this._generateCombatDialogue(bot);
                emotion = archetype.combat_aggression > 0.6 ? 'excited' : 'focused';
                intent = 'motivation';
                break;
            case 'problem_solving':
                baseText = this._generateProblemSolvingDialogue(bot);
                emotion = 'thoughtful';
                intent = 'collaboration';
                break;
            case 'celebration':
                baseText = this._generateCelebrationDialogue(bot);
                emotion = 'joyful';
                intent = 'celebration';
                break;
        }
        
        return {
            text: baseText,
            emotion: emotion,
            intent: intent,
            delivery_style: personality.speech_style
        };
    }

    _generateGreeting(bot) {
        const greetings = {
            'commanding': ['Well met, companions!', 'Ready for adventure?', 'Let\'s make this count!'],
            'friendly': ['Hello there!', 'Good to see you all!', 'How is everyone doing?'],
            'mysterious': ['*nods silently*', 'The path ahead calls...', '*emerges from the shadows*']
        };
        
        const style = bot.personality.speech_style;
        const styleGreetings = greetings[style] || greetings['friendly'];
        return this._randomChoice(styleGreetings);
    }

    _generateCombatDialogue(bot) {
        const combatLines = {
            'aggressive': ['Time to fight!', 'Let\'s end this quickly!', 'No mercy!'],
            'protective': ['I\'ll keep you safe!', 'Watch each other\'s backs!', 'Form up!'],
            'tactical': ['Remember the plan!', 'Use your positioning!', 'Think before you act!']
        };
        
        const preference = bot.behavior_patterns.combat_preference;
        const lines = combatLines[preference] || combatLines['aggressive'];
        return this._randomChoice(lines);
    }

    _generateProblemSolvingDialogue(bot) {
        const problemLines = {
            'analytical': ['Let me think about this...', 'What are our options?', 'There must be a solution.'],
            'creative': ['What if we tried...?', 'I have an unusual idea...', 'Think outside the box!'],
            'collaborative': ['What does everyone think?', 'Let\'s work together on this.', 'Two heads are better than one.']
        };
        
        const approach = bot.archetype.traits.includes('clever') ? 'creative' : 
                        bot.archetype.traits.includes('wise') ? 'analytical' : 'collaborative';
        
        const lines = problemLines[approach];
        return this._randomChoice(lines);
    }

    _generateCelebrationDialogue(bot) {
        const celebrations = {
            'enthusiastic': ['We did it!', 'Fantastic work everyone!', 'That was amazing!'],
            'humble': ['Good job, team.', 'We worked well together.', 'A successful endeavor.'],
            'proud': ['As expected!', 'Well done!', 'Another victory for us!']
        };
        
        const style = bot.archetype.traits.includes('inspiring') ? 'enthusiastic' :
                      bot.archetype.traits.includes('wise') ? 'humble' : 'proud';
        
        const lines = celebrations[style];
        return this._randomChoice(lines);
    }

    _generateBotName(archetype) {
        const namesByArchetype = {
            'brave_leader': ['Valiant', 'Commander', 'Sterling', 'Beacon', 'Marshal'],
            'clever_trickster': ['Wit', 'Clever', 'Riddle', 'Jest', 'Quicksilver'],
            'wise_mentor': ['Sage', 'Elder', 'Wisdom', 'Oracle', 'Keeper'],
            'fierce_warrior': ['Blade', 'Storm', 'Iron', 'Thunder', 'Fury'],
            'curious_scholar': ['Quill', 'Lore', 'Scribe', 'Archive', 'Tome'],
            'loyal_friend': ['True', 'Bond', 'Heart', 'Loyal', 'Steady'],
            'mysterious_loner': ['Shadow', 'Whisper', 'Veil', 'Enigma', 'Shade'],
            'optimistic_healer': ['Hope', 'Light', 'Grace', 'Mercy', 'Dawn']
        };
        
        const archetypeKey = Object.keys(this.personalityArchetypes).find(
            key => this.personalityArchetypes[key] === archetype
        );
        
        const names = namesByArchetype[archetypeKey] || ['Adventure', 'Quest', 'Journey'];
        return this._randomChoice(names);
    }

    async getStats() {
        try {
            const keys = await this.redis.keys('player_bot:*');
            const totalBots = keys.length;
            
            let totalSessions = 0;
            let totalSuccesses = 0;
            
            for (const key of keys.slice(0, 100)) { // Sample first 100
                const data = await this.redis.get(key);
                if (data) {
                    const bot = JSON.parse(data);
                    totalSessions += bot.stats.sessions_played || 0;
                    totalSuccesses += bot.stats.successful_actions || 0;
                }
            }
            
            return {
                total_bots: totalBots,
                total_sessions: totalSessions,
                success_rate: totalSessions > 0 ? totalSuccesses / totalSessions : 0,
                active_today: 0 // Could implement daily tracking
            };
            
        } catch (error) {
            this.logger.error('Error getting player bot stats:', error);
            return {
                total_bots: 0,
                total_sessions: 0,
                success_rate: 0,
                active_today: 0
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

module.exports = AIPlayerBots;