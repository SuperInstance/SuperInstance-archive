const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');

class TutorialEngine extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        // Tutorial campaign templates
        this.tutorialCampaigns = {
            'first_time_adventurer': {
                name: 'Your First Adventure',
                description: 'A gentle introduction to D&D for complete beginners',
                target_audience: 'brand_new_players',
                duration: '3-4 sessions',
                character_levels: '1-3',
                player_count: '3-5',
                
                learning_objectives: [
                    'Understand basic dice rolling',
                    'Learn character abilities and stats',
                    'Practice roleplay basics',
                    'Experience combat fundamentals',
                    'Learn teamwork and party dynamics'
                ],
                
                tutorial_structure: {
                    session1: {
                        name: 'Character Creation & Basics',
                        focus: 'character_creation_and_mechanics',
                        duration: '3-4 hours'
                    },
                    session2: {
                        name: 'The Village of Beginnings',
                        focus: 'roleplay_and_social_interaction',
                        duration: '3-4 hours'
                    },
                    session3: {
                        name: 'Your First Dungeon',
                        focus: 'exploration_and_combat',
                        duration: '3-4 hours'
                    },
                    session4: {
                        name: 'Heroes of the Village',
                        focus: 'teamwork_and_celebration',
                        duration: '2-3 hours'
                    }
                }
            },
            
            'rules_refresher': {
                name: 'Rules Refresher Adventure',
                description: 'For players returning to D&D after a long break',
                target_audience: 'returning_players',
                duration: '2-3 sessions',
                character_levels: '3-5',
                player_count: '3-6',
                
                learning_objectives: [
                    'Refresh core mechanics',
                    'Practice advanced combat options',
                    'Review spellcasting rules',
                    'Explore social encounters',
                    'Re-familiarize with D&D flow'
                ],
                
                tutorial_structure: {
                    session1: {
                        name: 'Getting Back in the Saddle',
                        focus: 'mechanics_review',
                        duration: '3-4 hours'
                    },
                    session2: {
                        name: 'Advanced Tactics',
                        focus: 'complex_encounters',
                        duration: '3-4 hours'
                    },
                    session3: {
                        name: 'The Full Experience',
                        focus: 'integrated_gameplay',
                        duration: '4 hours'
                    }
                }
            },
            
            'dm_training': {
                name: 'Your First Time as DM',
                description: 'Learn to be a Dungeon Master with guided practice',
                target_audience: 'aspiring_dms',
                duration: '4-5 sessions',
                character_levels: '1-4',
                player_count: '3-4',
                
                learning_objectives: [
                    'Learn DM fundamentals',
                    'Practice running encounters',
                    'Master NPC roleplay',
                    'Handle player creativity',
                    'Build confidence as DM'
                ],
                
                tutorial_structure: {
                    session0: {
                        name: 'DM Preparation Workshop',
                        focus: 'dm_preparation',
                        duration: '2 hours'
                    },
                    session1: {
                        name: 'Running Your First Session',
                        focus: 'basic_dm_skills',
                        duration: '3 hours'
                    },
                    session2: {
                        name: 'Combat and Challenge',
                        focus: 'encounter_management',
                        duration: '3 hours'
                    },
                    session3: {
                        name: 'NPCs and Roleplay',
                        focus: 'narrative_skills',
                        duration: '3 hours'
                    },
                    session4: {
                        name: 'Your Own Style',
                        focus: 'dm_confidence',
                        duration: '3-4 hours'
                    }
                }
            },
            
            'kids_first_adventure': {
                name: 'Adventure for Young Heroes',
                description: 'Child-friendly introduction to D&D',
                target_audience: 'children_8_to_12',
                duration: '2-3 sessions',
                character_levels: '1-2',
                player_count: '2-4',
                
                learning_objectives: [
                    'Have fun with imagination',
                    'Learn basic cooperation',
                    'Simple math with dice',
                    'Creative storytelling',
                    'Problem-solving skills'
                ],
                
                tutorial_structure: {
                    session1: {
                        name: 'Meet Your Hero',
                        focus: 'character_and_imagination',
                        duration: '1.5-2 hours'
                    },
                    session2: {
                        name: 'The Friendly Village',
                        focus: 'roleplay_and_helping',
                        duration: '1.5-2 hours'
                    },
                    session3: {
                        name: 'Big Heroes Save the Day',
                        focus: 'teamwork_and_success',
                        duration: '2 hours'
                    }
                }
            },
            
            'online_play_basics': {
                name: 'Digital D&D Fundamentals',
                description: 'Learn to play D&D online with virtual tabletops',
                target_audience: 'online_beginners',
                duration: '2 sessions',
                character_levels: '2-4',
                player_count: '3-5',
                
                learning_objectives: [
                    'Master virtual tabletop tools',
                    'Learn online etiquette',
                    'Practice digital dice rolling',
                    'Use voice chat effectively',
                    'Navigate technical challenges'
                ],
                
                tutorial_structure: {
                    session1: {
                        name: 'Virtual Tabletop Training',
                        focus: 'technical_skills',
                        duration: '2-3 hours'
                    },
                    session2: {
                        name: 'Online Adventure',
                        focus: 'digital_gameplay',
                        duration: '3-4 hours'
                    }
                }
            }
        };
        
        // Progressive learning modules
        this.learningModules = {
            character_creation: {
                name: 'Creating Your Character',
                concepts: ['ability_scores', 'races', 'classes', 'backgrounds', 'equipment'],
                exercises: [
                    'Roll ability scores with explanation',
                    'Choose race and understand bonuses',
                    'Select class and learn key features',
                    'Pick background for personality',
                    'Equip character with starting gear'
                ],
                assessment: 'Character sheet completion check'
            },
            
            basic_mechanics: {
                name: 'How D&D Works',
                concepts: ['d20_system', 'ability_checks', 'saving_throws', 'advantage_disadvantage'],
                exercises: [
                    'Practice d20 + modifier rolls',
                    'Try different types of ability checks',
                    'Experience advantage/disadvantage',
                    'Make saving throws with consequences'
                ],
                assessment: 'Mechanics quiz through play'
            },
            
            combat_basics: {
                name: 'Your First Fight',
                concepts: ['initiative', 'actions', 'movement', 'armor_class', 'hit_points'],
                exercises: [
                    'Roll initiative and understand turn order',
                    'Take different action types',
                    'Move tactically in combat',
                    'Attack rolls and damage',
                    'Take damage and track hit points'
                ],
                assessment: 'Successfully complete combat encounter'
            },
            
            roleplay_fundamentals: {
                name: 'Becoming Your Character',
                concepts: ['character_voice', 'motivations', 'interactions', 'decision_making'],
                exercises: [
                    'Speak in character voice',
                    'Make decisions based on character',
                    'Interact with NPCs meaningfully',
                    'Work with party members'
                ],
                assessment: 'Demonstrate character consistency'
            },
            
            spellcasting_101: {
                name: 'Magic for Beginners',
                concepts: ['spell_slots', 'components', 'concentration', 'spell_attacks'],
                exercises: [
                    'Cast cantrips and leveled spells',
                    'Understand spell slot usage',
                    'Practice concentration checks',
                    'Learn spell attack vs save spells'
                ],
                assessment: 'Cast spells effectively in encounters'
            },
            
            exploration_skills: {
                name: 'Exploring the World',
                concepts: ['investigation', 'perception', 'survival', 'environmental_hazards'],
                exercises: [
                    'Search rooms thoroughly',
                    'Notice hidden details',
                    'Navigate wilderness',
                    'Handle environmental challenges'
                ],
                assessment: 'Successfully explore complex area'
            },
            
            social_encounters: {
                name: 'Talking Your Way Through',
                concepts: ['persuasion', 'deception', 'intimidation', 'insight', 'npc_motivations'],
                exercises: [
                    'Negotiate with NPCs',
                    'Gather information socially',
                    'Read NPC motivations',
                    'Resolve conflicts without combat'
                ],
                assessment: 'Successfully resolve social challenge'
            }
        };
        
        // Interactive teaching tools
        this.teachingTools = {
            guided_examples: {
                'dice_rolling': {
                    name: 'Interactive Dice Tutorial',
                    description: 'Step-by-step dice rolling with immediate feedback'
                },
                'character_sheet': {
                    name: 'Character Sheet Walkthrough',
                    description: 'Guided tour of character sheet sections'
                },
                'combat_tracker': {
                    name: 'Combat Round Simulator',
                    description: 'Practice combat rounds with guidance'
                }
            },
            
            practice_scenarios: {
                'tavern_conversation': {
                    name: 'The Friendly Tavern',
                    description: 'Safe roleplay practice environment'
                },
                'simple_puzzle': {
                    name: 'The Locked Door',
                    description: 'Basic problem-solving scenario'
                },
                'goblin_encounter': {
                    name: 'Goblin Ambush',
                    description: 'Introductory combat encounter'
                }
            },
            
            help_systems: {
                'rule_lookup': {
                    name: 'Quick Rule Reference',
                    description: 'Context-sensitive rule explanations'
                },
                'decision_helper': {
                    name: 'What Can I Do?',
                    description: 'Suggests actions based on situation'
                },
                'mentor_ai': {
                    name: 'Virtual Mentor',
                    description: 'AI assistant for new players'
                }
            }
        };
    }

    async getTutorialCampaigns(options = {}) {
        try {
            const audience = options.target_audience;
            const experience_level = options.experience_level;
            
            let campaigns = Object.keys(this.tutorialCampaigns).map(key => ({
                id: key,
                ...this.tutorialCampaigns[key]
            }));
            
            // Filter by audience if specified
            if (audience) {
                campaigns = campaigns.filter(campaign => 
                    campaign.target_audience === audience
                );
            }
            
            // Add recommendation scores
            campaigns = campaigns.map(campaign => ({
                ...campaign,
                recommendation_score: this._calculateRecommendationScore(campaign, options)
            }));
            
            // Sort by recommendation score
            campaigns.sort((a, b) => b.recommendation_score - a.recommendation_score);
            
            return {
                campaigns: campaigns,
                learning_modules: Object.keys(this.learningModules).map(key => ({
                    id: key,
                    ...this.learningModules[key]
                })),
                teaching_tools: this.teachingTools
            };
            
        } catch (error) {
            this.logger.error('Error getting tutorial campaigns:', error);
            throw error;
        }
    }

    async startTutorial(options = {}) {
        try {
            const tutorialId = uuidv4();
            const campaignType = options.campaign_type || 'first_time_adventurer';
            const template = this.tutorialCampaigns[campaignType];
            
            if (!template) {
                throw new Error('Invalid tutorial campaign type');
            }
            
            const tutorial = {
                id: tutorialId,
                campaign_type: campaignType,
                template: template,
                started_at: new Date(),
                
                // Participant information
                participants: options.participants || [],
                dm_experience: options.dm_experience || 'beginner',
                player_experience: options.player_experience || 'beginner',
                
                // Progress tracking
                progress: {
                    current_session: 1,
                    completed_modules: [],
                    learning_objectives_met: [],
                    skill_assessments: {},
                    notes: []
                },
                
                // Customizations
                customizations: {
                    pacing: options.pacing || 'normal',
                    focus_areas: options.focus_areas || [],
                    special_needs: options.special_needs || [],
                    time_constraints: options.time_constraints || 'normal'
                },
                
                // Generated content
                session_plans: await this._generateTutorialSessions(template, options),
                character_pregens: await this._generatePregenCharacters(template, options),
                teaching_materials: await this._generateTeachingMaterials(template, options),
                
                // Support resources
                dm_guides: await this._generateDMGuides(template, options),
                player_handouts: await this._generatePlayerHandouts(template, options),
                safety_tools: this._generateSafetyTools(template, options)
            };
            
            // Cache the tutorial
            await this.redis.setex(
                `tutorial:${tutorialId}`,
                86400 * 30, // 30 days
                JSON.stringify(tutorial)
            );
            
            this.logger.info(`Started tutorial: ${template.name} (${tutorialId})`);
            this.io.emit('tutorial_started', { 
                tutorialId, 
                campaignType,
                participantCount: tutorial.participants.length 
            });
            
            return tutorial;
            
        } catch (error) {
            this.logger.error('Error starting tutorial:', error);
            throw error;
        }
    }

    async updateTutorialProgress(tutorialId, progressData) {
        try {
            const tutorial = await this.getTutorial(tutorialId);
            
            // Update progress
            if (progressData.session_completed) {
                tutorial.progress.current_session++;
            }
            
            if (progressData.modules_completed) {
                tutorial.progress.completed_modules.push(...progressData.modules_completed);
            }
            
            if (progressData.objectives_met) {
                tutorial.progress.learning_objectives_met.push(...progressData.objectives_met);
            }
            
            if (progressData.skill_assessment) {
                Object.assign(tutorial.progress.skill_assessments, progressData.skill_assessment);
            }
            
            if (progressData.notes) {
                tutorial.progress.notes.push({
                    timestamp: new Date(),
                    content: progressData.notes,
                    author: progressData.author || 'system'
                });
            }
            
            // Generate recommendations based on progress
            tutorial.recommendations = this._generateProgressRecommendations(tutorial);
            
            // Update cache
            await this.redis.setex(
                `tutorial:${tutorialId}`,
                86400 * 30,
                JSON.stringify(tutorial)
            );
            
            this.logger.info(`Updated tutorial progress: ${tutorialId}`);
            this.io.emit('tutorial_progress_updated', { 
                tutorialId, 
                progress: tutorial.progress 
            });
            
            return tutorial;
            
        } catch (error) {
            this.logger.error('Error updating tutorial progress:', error);
            throw error;
        }
    }

    async getTutorial(tutorialId) {
        try {
            const cached = await this.redis.get(`tutorial:${tutorialId}`);
            if (cached) {
                return JSON.parse(cached);
            }
            
            throw new Error('Tutorial not found');
            
        } catch (error) {
            this.logger.error('Error retrieving tutorial:', error);
            throw error;
        }
    }

    async generateCustomTutorial(requirements) {
        try {
            const customId = uuidv4();
            
            const customTutorial = {
                id: customId,
                type: 'custom',
                name: requirements.name || 'Custom Tutorial Campaign',
                created_at: new Date(),
                
                // Requirements analysis
                target_skills: requirements.target_skills || [],
                participant_profiles: requirements.participants || [],
                time_available: requirements.time_budget || 'flexible',
                learning_goals: requirements.learning_goals || [],
                
                // Generated structure
                session_structure: this._generateCustomSessionStructure(requirements),
                learning_path: this._generateLearningPath(requirements),
                assessment_plan: this._generateAssessmentPlan(requirements),
                
                // Adaptive elements
                difficulty_scaling: this._generateDifficultyScaling(requirements),
                alternative_paths: this._generateAlternativePaths(requirements),
                
                // Support materials
                custom_handouts: this._generateCustomHandouts(requirements),
                tailored_examples: this._generateTailoredExamples(requirements)
            };
            
            // Cache custom tutorial
            await this.redis.setex(
                `custom_tutorial:${customId}`,
                86400 * 7, // 7 days
                JSON.stringify(customTutorial)
            );
            
            return customTutorial;
            
        } catch (error) {
            this.logger.error('Error generating custom tutorial:', error);
            throw error;
        }
    }

    _calculateRecommendationScore(campaign, options) {
        let score = 0.5; // Base score
        
        // Match target audience
        if (options.target_audience === campaign.target_audience) {
            score += 0.3;
        }
        
        // Consider time constraints
        if (options.time_available) {
            const campaignSessions = parseInt(campaign.duration.split('-')[0]);
            const availableSessions = options.time_available;
            if (campaignSessions <= availableSessions) {
                score += 0.2;
            }
        }
        
        // Consider group size
        if (options.group_size) {
            const [min, max] = campaign.player_count.split('-').map(n => parseInt(n));
            if (options.group_size >= min && options.group_size <= max) {
                score += 0.1;
            }
        }
        
        return Math.min(score, 1.0);
    }

    async _generateTutorialSessions(template, options) {
        const sessions = [];
        
        for (const [sessionKey, sessionData] of Object.entries(template.tutorial_structure)) {
            const session = {
                session_id: sessionKey,
                name: sessionData.name,
                focus: sessionData.focus,
                duration: sessionData.duration,
                
                // Learning objectives for this session
                objectives: this._getSessionObjectives(sessionData.focus),
                
                // Step-by-step guide
                step_by_step: await this._generateSessionSteps(sessionData, template),
                
                // Teaching materials
                materials_needed: this._getSessionMaterials(sessionData.focus),
                
                // Assessment and feedback
                assessment_methods: this._getSessionAssessment(sessionData.focus),
                
                // Troubleshooting
                common_issues: this._getCommonIssues(sessionData.focus),
                solutions: this._getSolutions(sessionData.focus)
            };
            
            sessions.push(session);
        }
        
        return sessions;
    }

    _getSessionObjectives(focus) {
        const objectiveMap = {
            'character_creation_and_mechanics': [
                'Complete character creation process',
                'Understand ability scores and modifiers',
                'Learn basic dice mechanics',
                'Practice using character sheet'
            ],
            'roleplay_and_social_interaction': [
                'Develop character personality',
                'Practice speaking in character',
                'Learn social interaction mechanics',
                'Experience consequence-free roleplay'
            ],
            'exploration_and_combat': [
                'Navigate dungeon environment',
                'Learn combat turn structure',
                'Practice teamwork in challenges',
                'Experience risk and reward'
            ],
            'teamwork_and_celebration': [
                'Reflect on learning experience',
                'Plan future adventures',
                'Celebrate achievements',
                'Provide feedback on tutorial'
            ]
        };
        
        return objectiveMap[focus] || ['General learning objectives'];
    }

    async _generateSessionSteps(sessionData, template) {
        const focus = sessionData.focus;
        
        const stepMap = {
            'character_creation_and_mechanics': [
                '1. Welcome and introductions (15 min)',
                '2. Explain D&D basics with examples (20 min)',
                '3. Guided character creation (90 min)',
                '4. Practice basic mechanics (30 min)',
                '5. Q&A and wrap-up (15 min)'
            ],
            'roleplay_and_social_interaction': [
                '1. Recap and character introductions (15 min)',
                '2. Roleplay fundamentals (20 min)',
                '3. Practice conversations with NPCs (60 min)',
                '4. Group decision-making scenario (45 min)',
                '5. Reflection and feedback (10 min)'
            ],
            'exploration_and_combat': [
                '1. Set the scene and review characters (10 min)',
                '2. Exploration mechanics tutorial (20 min)',
                '3. Navigate first rooms with guidance (45 min)',
                '4. First combat with coaching (60 min)',
                '5. Treasure and advancement (15 min)'
            ]
        };
        
        return stepMap[focus] || ['Generic session steps'];
    }

    _getSessionMaterials(focus) {
        const materialMap = {
            'character_creation_and_mechanics': [
                'Character sheets (pre-printed)',
                'Pencils and erasers',
                'Full set of dice for each player',
                'Basic rules summary',
                'Character creation flowchart'
            ],
            'roleplay_and_social_interaction': [
                'Character sheets from session 1',
                'NPC portraits or tokens',
                'Situation prompt cards',
                'Voice and mannerism examples',
                'Roleplay comfort cards'
            ],
            'exploration_and_combat': [
                'Simple dungeon map',
                'Miniatures or tokens',
                'Initiative tracker',
                'Combat reference sheet',
                'Dice for damage rolls'
            ]
        };
        
        return materialMap[focus] || ['Basic game materials'];
    }

    _getSessionAssessment(focus) {
        const assessmentMap = {
            'character_creation_and_mechanics': [
                'Character sheet completion check',
                'Basic mechanic demonstration',
                'Comfort level self-assessment',
                'Questions answered accurately'
            ],
            'roleplay_and_social_interaction': [
                'Consistent character voice',
                'Meaningful NPC interactions',
                'Group collaboration evidence',
                'Comfort with roleplay'
            ],
            'exploration_and_combat': [
                'Successful combat participation',
                'Problem-solving demonstration',
                'Teamwork in challenges',
                'Rule application accuracy'
            ]
        };
        
        return assessmentMap[focus] || ['General assessment methods'];
    }

    _getCommonIssues(focus) {
        const issueMap = {
            'character_creation_and_mechanics': [
                'Analysis paralysis in character creation',
                'Difficulty understanding modifiers',
                'Confusion about dice types',
                'Overwhelmed by options'
            ],
            'roleplay_and_social_interaction': [
                'Shyness about speaking in character',
                'Uncertainty about character motivations',
                'Difficulty with improvisation',
                'Fear of doing it wrong'
            ],
            'exploration_and_combat': [
                'Forgetting combat order',
                'Confusion about action types',
                'Difficulty with spatial reasoning',
                'Overwhelmed by tactical options'
            ]
        };
        
        return issueMap[focus] || ['General learning challenges'];
    }

    _getSolutions(focus) {
        const solutionMap = {
            'character_creation_and_mechanics': [
                'Offer pre-generated characters as backup',
                'Use visual aids for modifier explanations',
                'Provide dice reference cards',
                'Break choices into smaller decisions'
            ],
            'roleplay_and_social_interaction': [
                'Start with simple character descriptions',
                'Provide example character motivations',
                'Use "yes, and..." encouragement',
                'Emphasize that there are no wrong answers'
            ],
            'exploration_and_combat': [
                'Use visual initiative tracker',
                'Provide action options on cards',
                'Use grid maps for spatial clarity',
                'Limit choices to prevent overwhelm'
            ]
        };
        
        return solutionMap[focus] || ['General solutions'];
    }

    async _generatePregenCharacters(template, options) {
        const pregens = [];
        const characterCount = Math.max(options.participants?.length || 4, 4);
        
        const classOptions = ['fighter', 'rogue', 'wizard', 'cleric', 'ranger'];
        
        for (let i = 0; i < characterCount; i++) {
            const character = {
                id: uuidv4(),
                name: this._generateCharacterName(),
                class: classOptions[i % classOptions.length],
                race: this._generateRace(),
                level: 1,
                
                // Simplified stats for beginners
                stats: this._generateBeginnerStats(),
                
                // Clear personality
                personality: this._generateSimplePersonality(),
                
                // Beginner-friendly equipment
                equipment: this._generateBeginnerEquipment(classOptions[i % classOptions.length]),
                
                // Tutorial notes
                tutorial_notes: {
                    key_abilities: this._getClassKeyAbilities(classOptions[i % classOptions.length]),
                    roleplay_suggestions: this._getClassRoleplaySuggestions(classOptions[i % classOptions.length]),
                    beginner_tips: this._getClassBeginnerTips(classOptions[i % classOptions.length])
                }
            };
            
            pregens.push(character);
        }
        
        return pregens;
    }

    _generateCharacterName() {
        const names = [
            'Alex Brightblade', 'Sam Swiftarrow', 'Morgan Spellweaver', 
            'Jordan Lightbringer', 'Casey Shadowstep', 'Riley Ironshield',
            'Avery Windwalker', 'Quinn Stargazer'
        ];
        
        return this._randomChoice(names);
    }

    _generateRace() {
        const beginnerFriendlyRaces = ['human', 'elf', 'dwarf', 'halfling'];
        return this._randomChoice(beginnerFriendlyRaces);
    }

    _generateBeginnerStats() {
        // Simplified stats that are good but not overwhelming
        return {
            strength: 14,
            dexterity: 13,
            constitution: 15,
            intelligence: 12,
            wisdom: 13,
            charisma: 11
        };
    }

    _generateSimplePersonality() {
        const personalities = [
            'Brave and helpful hero who protects others',
            'Clever and curious explorer who loves mysteries',
            'Wise and kind healer who cares for everyone',
            'Sneaky but loyal friend who solves problems',
            'Strong and honest warrior who fights fairly'
        ];
        
        return this._randomChoice(personalities);
    }

    _generateBeginnerEquipment(characterClass) {
        const equipment = {
            'fighter': ['longsword', 'shield', 'chain mail', 'backpack', 'rope', 'torch'],
            'rogue': ['shortsword', 'shortbow', 'leather armor', 'thieves tools', 'backpack', 'rope'],
            'wizard': ['quarterstaff', 'spellbook', 'robes', 'component pouch', 'backpack', 'lantern'],
            'cleric': ['mace', 'shield', 'chain mail', 'holy symbol', 'backpack', 'healing kit'],
            'ranger': ['longbow', 'shortsword', 'leather armor', 'explorer\'s pack', 'rope', 'survival kit']
        };
        
        return equipment[characterClass] || equipment['fighter'];
    }

    _getClassKeyAbilities(characterClass) {
        const abilities = {
            'fighter': ['Attack with weapons', 'Wear heavy armor', 'Protect allies', 'Action Surge ability'],
            'rogue': ['Sneak attack damage', 'Pick locks and find traps', 'Hide and move quietly', 'Lots of skills'],
            'wizard': ['Cast many different spells', 'Ritual casting', 'Spellbook contains spells', 'High intelligence'],
            'cleric': ['Heal allies', 'Cast divine spells', 'Turn undead', 'Channel divinity'],
            'ranger': ['Track and survive in nature', 'Fight with bow or melee', 'Animal companion (variant)', 'Favored enemy bonus']
        };
        
        return abilities[characterClass] || abilities['fighter'];
    }

    _getClassRoleplaySuggestions(characterClass) {
        const suggestions = {
            'fighter': ['Take charge in dangerous situations', 'Protect weaker party members', 'Be brave and direct'],
            'rogue': ['Notice details others miss', 'Suggest sneaky solutions', 'Be a bit mischievous but loyal'],
            'wizard': ['Offer knowledge about magical things', 'Plan before acting', 'Be curious about mysteries'],
            'cleric': ['Help and heal others', 'Provide moral guidance', 'Call on divine power in need'],
            'ranger': ['Guide the party in wilderness', 'Track enemies and creatures', 'Be practical and prepared']
        };
        
        return suggestions[characterClass] || suggestions['fighter'];
    }

    _getClassBeginnerTips(characterClass) {
        const tips = {
            'fighter': ['You have the most hit points - you can take hits for the team', 'Your Action Surge lets you attack twice in one turn'],
            'rogue': ['You deal extra damage when you have advantage', 'Use stealth to get advantage on attacks'],
            'wizard': ['You have lots of spells but few spell slots - choose wisely', 'Cantrips don\'t use spell slots'],
            'cleric': ['You can heal AND fight - you\'re very versatile', 'Your Channel Divinity is very powerful'],
            'ranger': ['You\'re good at both ranged and close combat', 'Your survival skills help outside of combat']
        };
        
        return tips[characterClass] || tips['fighter'];
    }

    async _generateTeachingMaterials(template, options) {
        return {
            visual_aids: [
                'Dice identification chart',
                'Character sheet guide',
                'Combat flow diagram',
                'Spell slot tracker'
            ],
            
            reference_sheets: [
                'Basic actions in combat',
                'Common ability checks',
                'Spell save DC explanation',
                'Movement and positioning'
            ],
            
            interactive_tools: [
                'Digital dice roller with explanations',
                'Character builder with guidance',
                'Combat simulator',
                'Rule lookup tool'
            ],
            
            practice_exercises: [
                'Dice rolling drills',
                'Character voice practice',
                'Simple tactical puzzles',
                'Roleplay scenario cards'
            ]
        };
    }

    async _generateDMGuides(template, options) {
        return {
            preparation_guides: [
                'How to prepare your first tutorial session',
                'Managing new player expectations',
                'Adapting on the fly for different learning speeds',
                'Creating a safe learning environment'
            ],
            
            teaching_strategies: [
                'Explaining rules without overwhelming',
                'Encouraging roleplay in shy players',
                'Managing combat pacing for beginners',
                'When to let mistakes slide vs correct them'
            ],
            
            troubleshooting: [
                'Player is confused about basic mechanics',
                'Someone is dominating the conversation',
                'Group is moving too slowly through content',
                'Player wants to do something not in the rules'
            ],
            
            encouragement_techniques: [
                'Celebrating small successes',
                'Reframing "mistakes" as learning',
                'Building confidence through agency',
                'Creating memorable positive moments'
            ]
        };
    }

    async _generatePlayerHandouts(template, options) {
        return {
            welcome_packet: [
                'What is D&D? Simple explanation',
                'What to expect in your first sessions',
                'Basic etiquette and expectations',
                'How to ask for help during the game'
            ],
            
            reference_cards: [
                'Your character\'s key abilities',
                'Common actions you can take',
                'Basic dice and when to use them',
                'Roleplay tips and examples'
            ],
            
            between_session_materials: [
                'Character development worksheet',
                'Questions to think about for next session',
                'Optional reading about D&D',
                'Practice scenarios to imagine'
            ],
            
            advancement_guides: [
                'What happens when you level up',
                'Choosing new spells or abilities',
                'How your character grows over time',
                'Setting personal goals for your character'
            ]
        };
    }

    _generateSafetyTools(template, options) {
        return {
            session_zero_topics: [
                'Comfort levels with different content',
                'Communication preferences',
                'What everyone wants from the game',
                'Boundaries and limits'
            ],
            
            ongoing_tools: [
                'X-Card for uncomfortable content',
                'Open Door policy for breaks',
                'Check-ins after intense scenes',
                'Enthusiastic consent for character interactions'
            ],
            
            inclusive_practices: [
                'Use inclusive language',
                'Respect pronouns and identity',
                'Make space for all personality types',
                'Accommodate different learning styles'
            ]
        };
    }

    _generateProgressRecommendations(tutorial) {
        const recommendations = [];
        
        // Check learning objective completion
        const template = tutorial.template;
        const completedObjectives = tutorial.progress.learning_objectives_met;
        const totalObjectives = template.learning_objectives.length;
        
        if (completedObjectives.length < totalObjectives * 0.5) {
            recommendations.push({
                type: 'pacing',
                priority: 'high',
                message: 'Consider slowing down to ensure core concepts are mastered',
                suggestions: ['Repeat key exercises', 'Add extra practice time', 'Check individual understanding']
            });
        }
        
        // Check session progress vs expectations
        const currentSession = tutorial.progress.current_session;
        const expectedSession = Math.floor((Date.now() - new Date(tutorial.started_at)) / (7 * 24 * 60 * 60 * 1000)) + 1;
        
        if (currentSession < expectedSession) {
            recommendations.push({
                type: 'scheduling',
                priority: 'medium',
                message: 'Tutorial is behind expected schedule',
                suggestions: ['Schedule catch-up session', 'Combine lighter content', 'Focus on essentials']
            });
        }
        
        return recommendations;
    }

    // Custom tutorial generation methods
    _generateCustomSessionStructure(requirements) {
        const sessions = [];
        const targetSkills = requirements.target_skills || [];
        const timeAvailable = requirements.time_budget || 'flexible';
        
        // Create sessions based on required skills
        let sessionCount = 1;
        for (const skill of targetSkills) {
            sessions.push({
                session_number: sessionCount++,
                focus_skill: skill,
                duration: this._calculateSessionDuration(skill, timeAvailable),
                objectives: this._getSkillObjectives(skill),
                activities: this._getSkillActivities(skill)
            });
        }
        
        return sessions;
    }

    _generateLearningPath(requirements) {
        const skills = requirements.target_skills || [];
        const prerequisites = this._getSkillPrerequisites(skills);
        
        return {
            prerequisite_check: prerequisites,
            skill_progression: this._orderSkillsByDependency(skills),
            milestone_assessments: this._generateMilestoneAssessments(skills)
        };
    }

    _generateAssessmentPlan(requirements) {
        return {
            formative_assessments: 'Ongoing observation and feedback',
            summative_assessments: 'End-of-tutorial demonstration',
            self_assessments: 'Player confidence and understanding checks'
        };
    }

    // Helper methods for custom generation
    _calculateSessionDuration(skill, timeAvailable) {
        const baseDurations = {
            'character_creation': '2-3 hours',
            'basic_mechanics': '1-2 hours',
            'combat_basics': '2-3 hours',
            'roleplay_fundamentals': '2-3 hours',
            'spellcasting_101': '2-3 hours'
        };
        
        return baseDurations[skill] || '2 hours';
    }

    _getSkillObjectives(skill) {
        return this.learningModules[skill]?.concepts || ['Basic understanding of ' + skill];
    }

    _getSkillActivities(skill) {
        return this.learningModules[skill]?.exercises || ['Practice ' + skill];
    }

    _getSkillPrerequisites(skills) {
        const prerequisites = {
            'spellcasting_101': ['basic_mechanics', 'character_creation'],
            'combat_basics': ['basic_mechanics'],
            'roleplay_fundamentals': ['character_creation']
        };
        
        return prerequisites;
    }

    _orderSkillsByDependency(skills) {
        // Simplified dependency ordering
        const order = ['character_creation', 'basic_mechanics', 'roleplay_fundamentals', 'combat_basics', 'spellcasting_101'];
        return skills.sort((a, b) => order.indexOf(a) - order.indexOf(b));
    }

    _generateMilestoneAssessments(skills) {
        return skills.map(skill => ({
            skill: skill,
            assessment: `Demonstrate competency in ${skill}`,
            criteria: ['Understanding', 'Application', 'Confidence']
        }));
    }

    // Additional helper methods
    _generateDifficultyScaling(requirements) {
        return {
            adaptive_pacing: 'Adjust based on group understanding',
            alternative_explanations: 'Multiple ways to explain concepts',
            skip_advanced: 'Options to skip complex topics if needed'
        };
    }

    _generateAlternativePaths(requirements) {
        return {
            fast_track: 'For experienced players needing specific skills',
            deep_dive: 'For players wanting thorough understanding',
            practical_focus: 'Emphasize hands-on play over theory'
        };
    }

    _generateCustomHandouts(requirements) {
        return ['Customized reference materials', 'Targeted practice exercises'];
    }

    _generateTailoredExamples(requirements) {
        return ['Examples relevant to participant interests', 'Scenarios matching group preferences'];
    }

    async getStats() {
        try {
            const tutorialKeys = await this.redis.keys('tutorial:*');
            const customKeys = await this.redis.keys('custom_tutorial:*');
            
            let completionRates = {};
            let popularCampaigns = {};
            let avgProgress = 0;
            
            for (const key of tutorialKeys.slice(0, 100)) {
                const data = await this.redis.get(key);
                if (data) {
                    const tutorial = JSON.parse(data);
                    const campaignType = tutorial.campaign_type;
                    popularCampaigns[campaignType] = (popularCampaigns[campaignType] || 0) + 1;
                    
                    const progress = tutorial.progress.completed_modules.length;
                    avgProgress += progress;
                }
            }
            
            return {
                total_tutorials: tutorialKeys.length,
                custom_tutorials: customKeys.length,
                popular_campaigns: popularCampaigns,
                average_progress: tutorialKeys.length > 0 ? avgProgress / tutorialKeys.length : 0,
                active_tutorials: 0 // Could implement active tracking
            };
            
        } catch (error) {
            this.logger.error('Error getting tutorial stats:', error);
            return {
                total_tutorials: 0,
                custom_tutorials: 0,
                popular_campaigns: {},
                average_progress: 0,
                active_tutorials: 0
            };
        }
    }

    _randomChoice(array) {
        return array[Math.floor(Math.random() * array.length)];
    }
}

module.exports = TutorialEngine;