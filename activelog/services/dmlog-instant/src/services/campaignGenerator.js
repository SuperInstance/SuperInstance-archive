const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');

class CampaignGenerator extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        // Campaign templates and structures
        this.campaignTemplates = {
            'classic_heroic': {
                name: 'Classic Heroic Adventure',
                description: 'Traditional fantasy adventure with clear heroes and villains',
                structure: 'three_act',
                themes: ['good vs evil', 'heroism', 'friendship', 'sacrifice'],
                tone: 'heroic and inspiring',
                estimated_sessions: '8-12',
                character_levels: '1-10',
                
                act_structure: {
                    act1: {
                        name: 'The Call to Adventure',
                        description: 'Heroes meet and receive their quest',
                        sessions: 3,
                        key_elements: ['meeting', 'inciting_incident', 'departure']
                    },
                    act2: {
                        name: 'Trials and Challenges',
                        description: 'Heroes face obstacles and grow stronger',
                        sessions: 6,
                        key_elements: ['challenges', 'allies', 'setbacks', 'revelation']
                    },
                    act3: {
                        name: 'Climax and Resolution',
                        description: 'Final confrontation and resolution',
                        sessions: 3,
                        key_elements: ['final_battle', 'sacrifice', 'victory', 'epilogue']
                    }
                }
            },
            
            'mystery_investigation': {
                name: 'Mystery Investigation',
                description: 'Detective-style campaign focused on solving mysteries',
                structure: 'episodic',
                themes: ['truth vs deception', 'justice', 'knowledge', 'corruption'],
                tone: 'suspenseful and methodical',
                estimated_sessions: '6-10',
                character_levels: '1-8',
                
                episode_structure: {
                    introduction: 'Present the mystery',
                    investigation: 'Gather clues and interview witnesses',
                    complications: 'Red herrings and new developments',
                    revelation: 'Uncover the truth',
                    resolution: 'Confront the perpetrator'
                }
            },
            
            'political_intrigue': {
                name: 'Political Intrigue',
                description: 'Complex political maneuvering and court politics',
                structure: 'layered_plots',
                themes: ['power', 'loyalty', 'betrayal', 'ambition'],
                tone: 'sophisticated and tense',
                estimated_sessions: '10-15',
                character_levels: '3-12',
                
                plot_layers: {
                    surface: 'Obvious political conflicts',
                    hidden: 'Secret alliances and schemes',
                    deep: 'Ancient conspiracies and hidden agendas'
                }
            },
            
            'exploration_discovery': {
                name: 'Exploration & Discovery',
                description: 'Exploring unknown lands and discovering secrets',
                structure: 'open_world',
                themes: ['discovery', 'wonder', 'danger', 'civilization vs wilderness'],
                tone: 'adventurous and wondrous',
                estimated_sessions: '12-20',
                character_levels: '1-15',
                
                exploration_phases: {
                    preparation: 'Gathering supplies and information',
                    journey: 'Travel to unknown regions',
                    discovery: 'Uncover ancient secrets',
                    consequences: 'Deal with what was found'
                }
            },
            
            'survival_horror': {
                name: 'Survival Horror',
                description: 'Atmospheric horror with survival elements',
                structure: 'escalating_tension',
                themes: ['survival', 'fear', 'human nature', 'isolation'],
                tone: 'tense and atmospheric',
                estimated_sessions: '6-8',
                character_levels: '1-6',
                
                tension_phases: {
                    normalcy: 'Establish normal world',
                    incursion: 'Something wrong appears',
                    escalation: 'Threat grows and spreads',
                    climax: 'Final confrontation or escape'
                }
            },
            
            'epic_campaign': {
                name: 'Epic World-Spanning Campaign',
                description: 'Grand campaign affecting entire world or multiverse',
                structure: 'multi_tier',
                themes: ['destiny', 'cosmic forces', 'ultimate good vs evil', 'sacrifice'],
                tone: 'epic and mythic',
                estimated_sessions: '20-50',
                character_levels: '1-20',
                
                tier_structure: {
                    local: 'Local heroes (levels 1-5)',
                    regional: 'Regional champions (levels 6-10)',
                    national: 'National heroes (levels 11-15)',
                    cosmic: 'Cosmic champions (levels 16-20)'
                }
            }
        };
        
        // Story element libraries
        this.storyElements = {
            inciting_incidents: [
                'Ancient evil awakens from long slumber',
                'Mysterious plague spreads across the land',
                'Royal heir disappears on eve of coronation',
                'Portal to another plane opens unexpectedly',
                'Dragons return after centuries of absence',
                'Civil war erupts between noble houses',
                'Cult seeks to summon dark deity',
                'Natural disasters suggest magical cause',
                'Merchant guild conspiracy uncovered',
                'Time itself begins to unravel'
            ],
            
            major_villains: [
                'Fallen paladin seeking redemption through conquest',
                'Ancient dragon manipulating from shadows',
                'Mad wizard experimenting with forbidden magic',
                'Corrupt noble using position for dark purposes',
                'Cultist leader prophesying world\'s end',
                'Undead king risen to reclaim lost kingdom',
                'Demon lord seeking entrance to material plane',
                'Rival adventuring party with opposing goals',
                'Elemental being wreaking havoc on civilization',
                'Time traveler attempting to change history'
            ],
            
            plot_twists: [
                'Trusted ally revealed as secret villain',
                'Heroes\' actions accidentally aid the enemy',
                'Villain\'s goals are actually noble but methods evil',
                'The real threat was hidden behind obvious enemy',
                'Heroes are fulfilling ancient prophecy unknowingly',
                'Timeline has been altered by unseen forces',
                'The quest item is actually a trap or curse',
                'Heroes are not who they think they are',
                'The kingdom they serve is the true evil',
                'Multiple timelines are converging'
            ],
            
            quest_objectives: [
                'Retrieve ancient artifact before villains',
                'Escort important person through dangerous territory',
                'Infiltrate enemy stronghold to gather intelligence',
                'Negotiate peace between warring factions',
                'Solve mysterious deaths in remote village',
                'Close dangerous portal before invasion begins',
                'Protect sacred site from desecration',
                'Hunt down dangerous escaped criminal',
                'Discover cure for magical plague',
                'Unite scattered tribes against common threat'
            ],
            
            locations: [
                'Ancient ruined city with dark secrets',
                'Floating island accessible only by magic',
                'Underground dwarven stronghold',
                'Haunted forest where time moves differently',
                'Bustling port city with criminal underworld',
                'Mountain monastery of warrior monks',
                'Desert oasis hiding ancient temple',
                'Frozen wasteland with surviving settlements',
                'Magical academy with dangerous experiments',
                'Planar nexus connecting multiple worlds'
            ],
            
            complications: [
                'Rival group seeks same objective',
                'Trusted ally has hidden agenda',
                'Time limit becomes more urgent',
                'Innocent people caught in crossfire',
                'Heroes\' reputations become tarnished',
                'Critical resource becomes unavailable',
                'Enemy adapts to heroes\' tactics',
                'Political situation changes suddenly',
                'Natural disaster complicates plans',
                'Magic begins behaving unpredictably'
            ]
        };
        
        // NPC relationship templates
        this.npcRelationships = {
            mentor: {
                role: 'Guide and teacher',
                personality: ['wise', 'patient', 'mysterious'],
                relationship_arc: ['initial_guidance', 'deepening_trust', 'ultimate_sacrifice_or_departure']
            },
            ally: {
                role: 'Trusted companion',
                personality: ['loyal', 'capable', 'dedicated'],
                relationship_arc: ['meeting', 'proving_worth', 'strong_alliance']
            },
            rival: {
                role: 'Competing for same goals',
                personality: ['ambitious', 'skilled', 'honorable'],
                relationship_arc: ['initial_conflict', 'grudging_respect', 'potential_alliance']
            },
            love_interest: {
                role: 'Romantic subplot',
                personality: ['attractive', 'independent', 'complex'],
                relationship_arc: ['attraction', 'obstacles', 'resolution']
            },
            comic_relief: {
                role: 'Lighthearted companion',
                personality: ['funny', 'loyal', 'optimistic'],
                relationship_arc: ['comic_introduction', 'unexpected_depth', 'heroic_moment']
            }
        };
    }

    async generateCampaign(options = {}) {
        try {
            const campaignId = uuidv4();
            
            // Determine campaign template
            const template = this._selectCampaignTemplate(options);
            
            // Generate core campaign structure
            const campaign = {
                id: campaignId,
                name: options.name || this._generateCampaignName(template),
                template: template,
                created_at: new Date(),
                
                // Campaign overview
                overview: {
                    description: this._generateCampaignDescription(template, options),
                    themes: template.themes,
                    tone: template.tone,
                    estimated_duration: template.estimated_sessions,
                    level_range: template.character_levels,
                    player_count: options.player_count || 4
                },
                
                // Story structure
                story_structure: await this._generateStoryStructure(template, options),
                
                // Key NPCs
                npcs: await this._generateKeyNPCs(template, options),
                
                // Major locations
                locations: await this._generateMajorLocations(template, options),
                
                // Session outlines
                session_outlines: await this._generateSessionOutlines(template, options),
                
                // Campaign resources
                resources: {
                    handouts: this._generateHandouts(template),
                    maps: this._generateMapRequirements(template),
                    props: this._generateProps(template),
                    music_suggestions: this._generateMusicSuggestions(template)
                },
                
                // DM notes and guidance
                dm_guidance: {
                    running_notes: this._generateRunningNotes(template),
                    common_challenges: this._generateCommonChallenges(template),
                    adaptation_suggestions: this._generateAdaptationSuggestions(template)
                },
                
                // Player handouts
                player_information: {
                    campaign_primer: this._generatePlayerPrimer(template),
                    character_creation_guidelines: this._generateCharacterGuidelines(template),
                    session_zero_questions: this._generateSessionZeroQuestions(template)
                }
            };
            
            // Integrate with other services if requested
            if (options.integrate_services) {
                campaign.integrated_content = await this._integrateServices(campaign, options);
            }
            
            // Cache the campaign
            await this.redis.setex(
                `campaign:${campaignId}`,
                86400 * 30, // 30 days
                JSON.stringify(campaign)
            );
            
            this.logger.info(`Generated campaign: ${campaign.name} (${campaignId})`);
            this.io.emit('campaign_generated', { 
                campaignId, 
                name: campaign.name,
                template: template.name 
            });
            
            return campaign;
            
        } catch (error) {
            this.logger.error('Error generating campaign:', error);
            throw error;
        }
    }

    async getCampaign(campaignId) {
        try {
            const cached = await this.redis.get(`campaign:${campaignId}`);
            if (cached) {
                return JSON.parse(cached);
            }
            
            throw new Error('Campaign not found');
            
        } catch (error) {
            this.logger.error('Error retrieving campaign:', error);
            throw error;
        }
    }

    _selectCampaignTemplate(options) {
        if (options.template && this.campaignTemplates[options.template]) {
            return this.campaignTemplates[options.template];
        }
        
        // Auto-select based on preferences
        if (options.preferences) {
            if (options.preferences.includes('mystery')) return this.campaignTemplates['mystery_investigation'];
            if (options.preferences.includes('political')) return this.campaignTemplates['political_intrigue'];
            if (options.preferences.includes('exploration')) return this.campaignTemplates['exploration_discovery'];
            if (options.preferences.includes('horror')) return this.campaignTemplates['survival_horror'];
            if (options.preferences.includes('epic')) return this.campaignTemplates['epic_campaign'];
        }
        
        // Default to classic heroic
        return this.campaignTemplates['classic_heroic'];
    }

    _generateCampaignName(template) {
        const nameTemplates = {
            'classic_heroic': [
                'The Legend of the Crystal Sword',
                'Heroes of the Forgotten Realm',
                'The Dragon\'s Legacy',
                'Quest for the Sacred Crown',
                'Chronicles of the Light Bearers'
            ],
            'mystery_investigation': [
                'Secrets of Shadowport',
                'The Vanishing Noble',
                'Mystery at Moonfall Manor',
                'The Clockwork Conspiracy',
                'Whispers in the Dark'
            ],
            'political_intrigue': [
                'Crown of Thorns',
                'The Gilded Conspiracy',
                'Shadows of the Throne',
                'The Noble Game',
                'Web of Allegiances'
            ],
            'exploration_discovery': [
                'Beyond the Mist Veil',
                'Expedition to the Unknown',
                'Secrets of the Lost World',
                'The Cartographer\'s Dream',
                'Into the Wilds'
            ],
            'survival_horror': [
                'The Cursed Village',
                'Night of the Hollow Moon',
                'The Whispering Woods',
                'Shadows Over Millhaven',
                'The Last Sanctuary'
            ],
            'epic_campaign': [
                'The Sundering of Worlds',
                'Twilight of the Gods',
                'The Cosmic Convergence',
                'Fate of the Multiverse',
                'The Final Prophecy'
            ]
        };
        
        const names = nameTemplates[template.name] || nameTemplates['classic_heroic'];
        return this._randomChoice(names);
    }

    _generateCampaignDescription(template, options) {
        const descriptions = {
            'classic_heroic': `A classic fantasy adventure where heroes rise to face an ancient evil threatening the realm. Through courage, friendship, and sacrifice, they must save the world from darkness.`,
            
            'mystery_investigation': `A detective-style campaign where the heroes must unravel complex mysteries using wit, investigation, and careful deduction. Every clue matters, and every suspect has secrets.`,
            
            'political_intrigue': `Navigate the dangerous waters of court politics, where every word matters and trust is a luxury. Heroes must use diplomacy, espionage, and strategic thinking to achieve their goals.`,
            
            'exploration_discovery': `Venture into uncharted territories and discover ancient secrets. This campaign emphasizes exploration, wonder, and the thrill of discovering the unknown.`,
            
            'survival_horror': `A tense, atmospheric campaign where heroes must survive against overwhelming odds. Resources are scarce, danger lurks everywhere, and not everyone will make it out alive.`,
            
            'epic_campaign': `An epic journey spanning multiple planes of existence. Heroes grow from local adventurers to cosmic champions, facing threats that could destroy reality itself.`
        };
        
        return descriptions[template.name] || descriptions['classic_heroic'];
    }

    async _generateStoryStructure(template, options) {
        const structure = {
            template_type: template.structure,
            main_plot: this._generateMainPlot(template),
            subplots: this._generateSubplots(template),
            major_beats: this._generateMajorBeats(template),
            pacing_guide: this._generatePacingGuide(template)
        };
        
        // Add template-specific structure
        if (template.act_structure) {
            structure.acts = template.act_structure;
        } else if (template.episode_structure) {
            structure.episodes = template.episode_structure;
        } else if (template.plot_layers) {
            structure.layers = template.plot_layers;
        }
        
        return structure;
    }

    _generateMainPlot(template) {
        const incitingIncident = this._randomChoice(this.storyElements.inciting_incidents);
        const majorVillain = this._randomChoice(this.storyElements.major_villains);
        const questObjective = this._randomChoice(this.storyElements.quest_objectives);
        const plotTwist = this._randomChoice(this.storyElements.plot_twists);
        
        return {
            inciting_incident: incitingIncident,
            main_antagonist: majorVillain,
            primary_objective: questObjective,
            major_twist: plotTwist,
            resolution_type: this._generateResolutionType(template)
        };
    }

    _generateSubplots(template) {
        const numSubplots = Math.floor(Math.random() * 3) + 2; // 2-4 subplots
        const subplots = [];
        
        for (let i = 0; i < numSubplots; i++) {
            subplots.push({
                name: this._generateSubplotName(),
                description: this._generateSubplotDescription(),
                complexity: this._randomChoice(['simple', 'moderate', 'complex']),
                connection_to_main: this._generateMainPlotConnection(),
                resolution_session: Math.floor(Math.random() * 8) + 3 // Sessions 3-10
            });
        }
        
        return subplots;
    }

    _generateMajorBeats(template) {
        return [
            { name: 'Opening Hook', session: 1, description: 'Introduce heroes and inciting incident' },
            { name: 'Call to Action', session: 2, description: 'Heroes accept the quest' },
            { name: 'First Challenge', session: 3, description: 'Initial obstacle tests the heroes' },
            { name: 'Revelation', session: Math.floor(template.estimated_sessions.split('-')[0] / 2), description: 'Major plot information revealed' },
            { name: 'Midpoint Crisis', session: Math.floor(template.estimated_sessions.split('-')[1] * 0.6), description: 'Everything seems lost' },
            { name: 'Final Preparation', session: template.estimated_sessions.split('-')[1] - 2, description: 'Heroes prepare for final confrontation' },
            { name: 'Climax', session: template.estimated_sessions.split('-')[1] - 1, description: 'Final battle or confrontation' },
            { name: 'Resolution', session: template.estimated_sessions.split('-')[1], description: 'Wrap up loose ends and epilogue' }
        ];
    }

    async _generateKeyNPCs(template, options) {
        const npcs = [];
        const requiredRoles = ['mentor', 'ally', 'rival', 'love_interest', 'comic_relief'];
        
        for (const role of requiredRoles) {
            const npc = {
                id: uuidv4(),
                name: this._generateNPCName(),
                role: role,
                relationship_template: this.npcRelationships[role],
                description: this._generateNPCDescription(role, template),
                personality_traits: this._generateNPCPersonality(role),
                background: this._generateNPCBackground(role, template),
                stats: this._generateNPCStats(role, template),
                plot_significance: this._generatePlotSignificance(role, template),
                character_arc: this._generateCharacterArc(role, template)
            };
            
            npcs.push(npc);
        }
        
        // Add template-specific NPCs
        const additionalNPCs = this._generateAdditionalNPCs(template);
        npcs.push(...additionalNPCs);
        
        return npcs;
    }

    async _generateMajorLocations(template, options) {
        const locations = [];
        const numLocations = Math.floor(Math.random() * 4) + 4; // 4-7 locations
        
        for (let i = 0; i < numLocations; i++) {
            const location = {
                id: uuidv4(),
                name: this._generateLocationName(),
                type: this._randomChoice(['city', 'dungeon', 'wilderness', 'stronghold', 'magical_site']),
                description: this._generateLocationDescription(),
                key_features: this._generateLocationFeatures(),
                inhabitants: this._generateLocationInhabitants(),
                plot_connections: this._generateLocationPlotConnections(),
                encounters: this._generateLocationEncounters(),
                secrets: this._generateLocationSecrets(),
                resources: this._generateLocationResources()
            };
            
            locations.push(location);
        }
        
        return locations;
    }

    async _generateSessionOutlines(template, options) {
        const outlines = [];
        const sessionCount = parseInt(template.estimated_sessions.split('-')[1]);
        
        for (let i = 1; i <= sessionCount; i++) {
            const outline = {
                session_number: i,
                title: this._generateSessionTitle(i, template),
                overview: this._generateSessionOverview(i, template),
                objectives: this._generateSessionObjectives(i, template),
                encounters: this._generateSessionEncounters(i, template),
                roleplay_scenes: this._generateRoleplayScenes(i, template),
                treasure_rewards: this._generateSessionRewards(i, template),
                dm_notes: this._generateSessionDMNotes(i, template),
                transitions: this._generateSessionTransitions(i, template)
            };
            
            outlines.push(outline);
        }
        
        return outlines;
    }

    async _integrateServices(campaign, options) {
        const integrated = {};
        
        try {
            // Integrate with game randomizer for additional content
            if (options.integrate_randomizer) {
                integrated.randomized_elements = await this._integrateGameRandomizer(campaign);
            }
            
            // Integrate with AI DM personality
            if (options.integrate_dm_personality) {
                integrated.dm_personality = await this._integrateDMPersonality(campaign);
            }
            
            // Integrate with player bots
            if (options.integrate_player_bots) {
                integrated.ai_players = await this._integratePlayerBots(campaign);
            }
            
            // Integrate with style selector
            if (options.integrate_style) {
                integrated.visual_style = await this._integrateStyleSelector(campaign, options);
            }
            
        } catch (error) {
            this.logger.warn('Error integrating services:', error);
        }
        
        return integrated;
    }

    // Helper methods for generation
    _generateResolutionType(template) {
        const resolutions = {
            'classic_heroic': 'heroic_victory',
            'mystery_investigation': 'truth_revealed',
            'political_intrigue': 'power_balance_shift',
            'exploration_discovery': 'world_changed',
            'survival_horror': 'escape_or_sacrifice',
            'epic_campaign': 'cosmic_transformation'
        };
        
        return resolutions[template.name] || 'heroic_victory';
    }

    _generateSubplotName() {
        const names = [
            'The Missing Heir', 'Secret of the Guild', 'The Rival\'s Challenge',
            'Love Lost and Found', 'The Mentor\'s Past', 'Betrayal in the Ranks',
            'The Cursed Item', 'Political Complications', 'Family Secrets',
            'The Mysterious Benefactor'
        ];
        
        return this._randomChoice(names);
    }

    _generateSubplotDescription() {
        const descriptions = [
            'A personal quest that tests character loyalty',
            'A political complication that affects the main mission',
            'A romantic entanglement that complicates relationships',
            'A moral dilemma that challenges character beliefs',
            'A mystery from the past that resurfaces',
            'A rival group with competing interests',
            'A cursed or magical item with unintended consequences',
            'A family connection that brings obligations'
        ];
        
        return this._randomChoice(descriptions);
    }

    _generateMainPlotConnection() {
        const connections = [
            'Directly impacts main quest success',
            'Provides crucial information for main plot',
            'Creates complications for main objective',
            'Offers alternative solution to main problem',
            'Tests character growth needed for finale',
            'Reveals hidden aspect of main antagonist'
        ];
        
        return this._randomChoice(connections);
    }

    _generatePacingGuide(template) {
        return {
            opening: 'Start with immediate action or compelling mystery',
            early_sessions: 'Establish characters and world, build momentum',
            middle_sessions: 'Escalate stakes, introduce complications',
            climax_approach: 'Increase tension, converge plot threads',
            resolution: 'Satisfying conclusion, tie up loose ends'
        };
    }

    _generateNPCName() {
        const names = [
            'Aldric Stormwind', 'Seraphina Nightshade', 'Thorin Ironforge',
            'Luna Silverleaf', 'Marcus Blackthorn', 'Aria Goldenheart',
            'Darius Shadowbane', 'Lyra Moonwhisper', 'Gareth Strongarm',
            'Isabella Ravenwood'
        ];
        
        return this._randomChoice(names);
    }

    _generateNPCDescription(role, template) {
        const descriptions = {
            'mentor': 'A wise and experienced figure who guides the heroes on their journey',
            'ally': 'A trusted companion who aids the heroes in their quest',
            'rival': 'A capable individual with goals that sometimes conflict with the heroes',
            'love_interest': 'An attractive and complex person who captures a hero\'s heart',
            'comic_relief': 'A cheerful character who brings levity to tense situations'
        };
        
        return descriptions[role] || 'An important figure in the campaign';
    }

    _generateNPCPersonality(role) {
        const personalities = {
            'mentor': ['wise', 'patient', 'mysterious', 'caring'],
            'ally': ['loyal', 'brave', 'dependable', 'skilled'],
            'rival': ['ambitious', 'honorable', 'competitive', 'proud'],
            'love_interest': ['charming', 'independent', 'complex', 'attractive'],
            'comic_relief': ['funny', 'optimistic', 'loyal', 'energetic']
        };
        
        return personalities[role] || ['friendly', 'helpful', 'trustworthy'];
    }

    _generateNPCBackground(role, template) {
        return `A ${role} with deep connections to the campaign's central themes and conflicts.`;
    }

    _generateNPCStats(role, template) {
        const levels = {
            'mentor': Math.floor(Math.random() * 10) + 10, // Level 10-19
            'ally': Math.floor(Math.random() * 5) + 3, // Level 3-7
            'rival': Math.floor(Math.random() * 6) + 2, // Level 2-7
            'love_interest': Math.floor(Math.random() * 4) + 1, // Level 1-4
            'comic_relief': Math.floor(Math.random() * 3) + 1 // Level 1-3
        };
        
        return {
            level: levels[role] || 1,
            class: this._generateNPCClass(role),
            notable_abilities: this._generateNotableAbilities(role)
        };
    }

    _generateNPCClass(role) {
        const classes = {
            'mentor': ['wizard', 'cleric', 'druid', 'paladin'],
            'ally': ['fighter', 'ranger', 'rogue', 'bard'],
            'rival': ['fighter', 'rogue', 'wizard', 'paladin'],
            'love_interest': ['bard', 'sorcerer', 'ranger', 'cleric'],
            'comic_relief': ['bard', 'rogue', 'barbarian', 'sorcerer']
        };
        
        return this._randomChoice(classes[role] || ['fighter']);
    }

    _generateNotableAbilities(role) {
        const abilities = {
            'mentor': ['Powerful spellcasting', 'Ancient knowledge', 'Prophetic visions'],
            'ally': ['Expert combatant', 'Useful skills', 'Local connections'],
            'rival': ['Matching capabilities', 'Different approach', 'Hidden talents'],
            'love_interest': ['Charming personality', 'Unique skills', 'Emotional depth'],
            'comic_relief': ['Comic timing', 'Unexpected competence', 'Loyalty']
        };
        
        return abilities[role] || ['Generic abilities'];
    }

    _generatePlotSignificance(role, template) {
        return `Critical ${role} who significantly impacts the campaign's direction and outcome.`;
    }

    _generateCharacterArc(role, template) {
        return this.npcRelationships[role]?.relationship_arc || ['introduction', 'development', 'resolution'];
    }

    _generateAdditionalNPCs(template) {
        // Template-specific NPCs would be generated here
        return [];
    }

    _generateLocationName() {
        const names = [
            'Shadowmere Keep', 'The Whispering Woods', 'Goldenhaven',
            'Dragonspine Mountains', 'The Sunken City', 'Moonfall Tower',
            'The Crystal Caverns', 'Thornwall Village', 'The Floating Isle',
            'Emberdale'
        ];
        
        return this._randomChoice(names);
    }

    _generateLocationDescription() {
        return 'A significant location that plays an important role in the campaign narrative.';
    }

    _generateLocationFeatures() {
        return ['Notable architecture', 'Unique atmosphere', 'Strategic importance'];
    }

    _generateLocationInhabitants() {
        return ['Local population', 'Notable NPCs', 'Potential enemies'];
    }

    _generateLocationPlotConnections() {
        return ['Connects to main plot', 'Subplot location', 'Information source'];
    }

    _generateLocationEncounters() {
        return ['Combat encounters', 'Social challenges', 'Environmental obstacles'];
    }

    _generateLocationSecrets() {
        return ['Hidden passages', 'Buried history', 'Concealed treasures'];
    }

    _generateLocationResources() {
        return ['Equipment', 'Information', 'Allies', 'Rest and recovery'];
    }

    // Session outline generation methods
    _generateSessionTitle(sessionNum, template) {
        return `Session ${sessionNum}: ${this._generateGenericSessionTitle(sessionNum)}`;
    }

    _generateGenericSessionTitle(sessionNum) {
        const titles = [
            'The Adventure Begins', 'First Steps', 'Gathering Clues',
            'Into Danger', 'Unexpected Allies', 'The Plot Thickens',
            'Rising Stakes', 'Dark Revelations', 'The Final Push',
            'Victory and Resolution'
        ];
        
        const index = Math.min(sessionNum - 1, titles.length - 1);
        return titles[index];
    }

    _generateSessionOverview(sessionNum, template) {
        return `Overview for session ${sessionNum} following the ${template.name} template.`;
    }

    _generateSessionObjectives(sessionNum, template) {
        return ['Primary objective', 'Secondary objective', 'Character development goal'];
    }

    _generateSessionEncounters(sessionNum, template) {
        return ['Main encounter', 'Optional encounter', 'Social challenge'];
    }

    _generateRoleplayScenes(sessionNum, template) {
        return ['Character interaction scene', 'NPC dialogue', 'Moral choice moment'];
    }

    _generateSessionRewards(sessionNum, template) {
        return ['Experience points', 'Treasure or items', 'Story advancement'];
    }

    _generateSessionDMNotes(sessionNum, template) {
        return ['Key points to remember', 'Flexibility notes', 'Backup plans'];
    }

    _generateSessionTransitions(sessionNum, template) {
        return 'How this session connects to the next session.';
    }

    // Resource generation methods
    _generateHandouts(template) {
        return ['Campaign primer', 'Important letters', 'Maps', 'Prophecies'];
    }

    _generateMapRequirements(template) {
        return ['World map', 'Local area maps', 'Battle maps', 'Building layouts'];
    }

    _generateProps(template) {
        return ['Important items', 'Clue tokens', 'Character portraits', 'Reference sheets'];
    }

    _generateMusicSuggestions(template) {
        const suggestions = {
            'classic_heroic': ['Epic orchestral', 'Adventure themes', 'Battle music'],
            'mystery_investigation': ['Suspenseful ambience', 'Investigation themes', 'Revelation stings'],
            'political_intrigue': ['Court music', 'Tense atmosphere', 'Sophisticated themes'],
            'exploration_discovery': ['Wonder themes', 'Travel music', 'Discovery fanfares'],
            'survival_horror': ['Atmospheric dread', 'Tension music', 'Horror stings'],
            'epic_campaign': ['Cosmic themes', 'Divine music', 'Apocalyptic scores']
        };
        
        return suggestions[template.name] || suggestions['classic_heroic'];
    }

    // DM guidance methods
    _generateRunningNotes(template) {
        return [
            'Keep track of NPC relationships',
            'Note player character development',
            'Adjust difficulty as needed',
            'Encourage player agency'
        ];
    }

    _generateCommonChallenges(template) {
        return [
            'Players going off expected path',
            'Balancing different character motivations',
            'Managing pacing across sessions',
            'Keeping all players engaged'
        ];
    }

    _generateAdaptationSuggestions(template) {
        return [
            'Scale encounters to party size',
            'Adjust story for player interests',
            'Modify NPCs based on player reactions',
            'Be flexible with timeline'
        ];
    }

    // Player information methods
    _generatePlayerPrimer(template) {
        return `Welcome to ${template.name}! This campaign focuses on ${template.themes.join(', ')} with a ${template.tone} tone.`;
    }

    _generateCharacterGuidelines(template) {
        return [
            'Create characters that fit the campaign themes',
            'Consider your character\'s motivations',
            'Think about relationships with other PCs',
            'Discuss any concerns with the DM'
        ];
    }

    _generateSessionZeroQuestions(template) {
        return [
            'What draws your character to adventure?',
            'What are your character\'s goals?',
            'How does your character know the other PCs?',
            'What are you most excited about in this campaign?'
        ];
    }

    // Integration methods (simplified)
    async _integrateGameRandomizer(campaign) {
        return { status: 'Game randomizer integration planned' };
    }

    async _integrateDMPersonality(campaign) {
        return { status: 'DM personality integration planned' };
    }

    async _integratePlayerBots(campaign) {
        return { status: 'Player bots integration planned' };
    }

    async _integrateStyleSelector(campaign, options) {
        return { status: 'Style selector integration planned' };
    }

    async getStats() {
        try {
            const keys = await this.redis.keys('campaign:*');
            const totalCampaigns = keys.length;
            
            let templateDistribution = {};
            let avgSessionCount = 0;
            
            for (const key of keys.slice(0, 100)) {
                const data = await this.redis.get(key);
                if (data) {
                    const campaign = JSON.parse(data);
                    const templateName = campaign.template.name;
                    templateDistribution[templateName] = (templateDistribution[templateName] || 0) + 1;
                    
                    // Calculate average sessions (simplified)
                    const sessions = parseInt(campaign.template.estimated_sessions.split('-')[0]);
                    avgSessionCount += sessions;
                }
            }
            
            return {
                total_campaigns: totalCampaigns,
                popular_templates: templateDistribution,
                average_session_count: totalCampaigns > 0 ? avgSessionCount / totalCampaigns : 0,
                generated_today: 0 // Could implement daily tracking
            };
            
        } catch (error) {
            this.logger.error('Error getting campaign stats:', error);
            return {
                total_campaigns: 0,
                popular_templates: {},
                average_session_count: 0,
                generated_today: 0
            };
        }
    }

    _randomChoice(array) {
        return array[Math.floor(Math.random() * array.length)];
    }
}

module.exports = CampaignGenerator;