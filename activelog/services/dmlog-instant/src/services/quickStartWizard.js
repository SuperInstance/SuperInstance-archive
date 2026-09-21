const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');

class QuickStartWizard extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        // Wizard flow definitions
        this.wizardFlows = {
            'complete_beginner': {
                name: 'Complete Beginner Setup',
                description: 'For people who have never played D&D before',
                target_audience: 'never_played',
                estimated_time: '20-30 minutes',
                
                steps: [
                    {
                        id: 'welcome',
                        title: 'Welcome to D&D!',
                        type: 'introduction',
                        content: 'introduction_to_dnd',
                        required: true,
                        estimated_minutes: 3
                    },
                    {
                        id: 'group_setup',
                        title: 'Who\'s Playing?',
                        type: 'group_configuration',
                        content: 'player_count_and_roles',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'character_creation',
                        title: 'Create Your Characters',
                        type: 'character_setup',
                        content: 'guided_character_creation',
                        required: true,
                        estimated_minutes: 15
                    },
                    {
                        id: 'first_adventure',
                        title: 'Choose Your First Adventure',
                        type: 'adventure_selection',
                        content: 'beginner_adventure_options',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'game_setup',
                        title: 'Set Up Your Game',
                        type: 'technical_setup',
                        content: 'dice_and_materials',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'launch',
                        title: 'Start Playing!',
                        type: 'completion',
                        content: 'launch_first_session',
                        required: true,
                        estimated_minutes: 2
                    }
                ]
            },
            
            'experienced_quick_start': {
                name: 'Quick Campaign Setup',
                description: 'For experienced players starting a new campaign',
                target_audience: 'experienced_players',
                estimated_time: '10-15 minutes',
                
                steps: [
                    {
                        id: 'campaign_type',
                        title: 'Campaign Style',
                        type: 'campaign_selection',
                        content: 'campaign_type_selection',
                        required: true,
                        estimated_minutes: 3
                    },
                    {
                        id: 'customization',
                        title: 'Customize Your Game',
                        type: 'customization',
                        content: 'advanced_customization_options',
                        required: false,
                        estimated_minutes: 5
                    },
                    {
                        id: 'character_import',
                        title: 'Characters',
                        type: 'character_setup',
                        content: 'import_or_generate_characters',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'integration',
                        title: 'Integrate Services',
                        type: 'service_integration',
                        content: 'optional_service_integration',
                        required: false,
                        estimated_minutes: 3
                    },
                    {
                        id: 'launch',
                        title: 'Ready to Play',
                        type: 'completion',
                        content: 'launch_configured_session',
                        required: true,
                        estimated_minutes: 1
                    }
                ]
            },
            
            'dm_first_time': {
                name: 'First-Time DM Setup',
                description: 'Special guidance for new Dungeon Masters',
                target_audience: 'new_dm',
                estimated_time: '25-35 minutes',
                
                steps: [
                    {
                        id: 'dm_introduction',
                        title: 'Welcome, Dungeon Master!',
                        type: 'introduction',
                        content: 'dm_role_explanation',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'dm_personality',
                        title: 'Your DM Style',
                        type: 'personality_setup',
                        content: 'dm_personality_selection',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'player_setup',
                        title: 'Set Up Players',
                        type: 'group_configuration',
                        content: 'player_experience_assessment',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'adventure_prep',
                        title: 'Choose and Prep Adventure',
                        type: 'adventure_preparation',
                        content: 'dm_adventure_selection_and_prep',
                        required: true,
                        estimated_minutes: 10
                    },
                    {
                        id: 'dm_tools',
                        title: 'DM Tools and Resources',
                        type: 'tool_setup',
                        content: 'dm_tool_configuration',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'session_zero',
                        title: 'Session Zero Guide',
                        type: 'guidance',
                        content: 'session_zero_checklist',
                        required: true,
                        estimated_minutes: 3
                    },
                    {
                        id: 'launch',
                        title: 'Start Your First Session!',
                        type: 'completion',
                        content: 'launch_dm_session',
                        required: true,
                        estimated_minutes: 2
                    }
                ]
            },
            
            'one_shot_setup': {
                name: 'One-Shot Adventure Setup',
                description: 'Quick setup for single-session adventures',
                target_audience: 'one_shot_players',
                estimated_time: '10-15 minutes',
                
                steps: [
                    {
                        id: 'one_shot_selection',
                        title: 'Choose Your Adventure',
                        type: 'adventure_selection',
                        content: 'one_shot_adventure_catalog',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'quick_characters',
                        title: 'Instant Characters',
                        type: 'character_setup',
                        content: 'pregenerated_character_selection',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'style_selection',
                        title: 'Adventure Style',
                        type: 'style_setup',
                        content: 'visual_and_narrative_style',
                        required: false,
                        estimated_minutes: 3
                    },
                    {
                        id: 'launch',
                        title: 'Jump In!',
                        type: 'completion',
                        content: 'launch_one_shot',
                        required: true,
                        estimated_minutes: 2
                    }
                ]
            },
            
            'custom_setup': {
                name: 'Custom Game Setup',
                description: 'Flexible setup for specific requirements',
                target_audience: 'custom_needs',
                estimated_time: '15-30 minutes',
                
                steps: [
                    {
                        id: 'requirements_gathering',
                        title: 'Tell Us About Your Game',
                        type: 'requirements_gathering',
                        content: 'custom_requirements_form',
                        required: true,
                        estimated_minutes: 8
                    },
                    {
                        id: 'solution_recommendation',
                        title: 'Recommended Setup',
                        type: 'recommendation',
                        content: 'ai_generated_recommendations',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'customization',
                        title: 'Fine-Tune Your Setup',
                        type: 'customization',
                        content: 'detailed_customization_options',
                        required: false,
                        estimated_minutes: 10
                    },
                    {
                        id: 'validation',
                        title: 'Review Your Setup',
                        type: 'validation',
                        content: 'setup_review_and_validation',
                        required: true,
                        estimated_minutes: 5
                    },
                    {
                        id: 'launch',
                        title: 'Launch Custom Game',
                        type: 'completion',
                        content: 'launch_custom_session',
                        required: true,
                        estimated_minutes: 2
                    }
                ]
            }
        };
        
        // Step content definitions
        this.stepContent = {
            // Introduction content
            introduction_to_dnd: {
                title: 'What is Dungeons & Dragons?',
                explanation: 'D&D is a cooperative storytelling game where you create characters and go on adventures together. One person is the Dungeon Master (DM) who describes the world and plays supporting characters, while the others play the heroes of the story.',
                key_concepts: [
                    'You tell a story together with friends',
                    'Dice add excitement and unpredictability',
                    'Your character has abilities and personality',
                    'The DM describes the world and situations',
                    'Players decide what their characters do'
                ],
                next_steps: 'Let\'s set up your first game!'
            },
            
            dm_role_explanation: {
                title: 'Welcome to Being a Dungeon Master!',
                explanation: 'As the DM, you\'re the narrator, referee, and world-builder. Don\'t worry - you don\'t need to be perfect! The most important thing is to help everyone have fun.',
                key_responsibilities: [
                    'Describe the world and situations',
                    'Play NPCs (non-player characters)',
                    'Make rulings when questions arise',
                    'Help guide the story forward',
                    'Ensure everyone gets spotlight time'
                ],
                encouragement: 'Remember: You\'re not playing against the players, you\'re all working together to create an amazing story!'
            },
            
            // Selection options
            campaign_type_options: [
                {
                    id: 'heroic_fantasy',
                    name: 'Heroic Fantasy',
                    description: 'Classic good vs evil with brave heroes',
                    suitable_for: ['all_experience_levels'],
                    themes: ['heroism', 'friendship', 'good_vs_evil']
                },
                {
                    id: 'mystery_investigation',
                    name: 'Mystery & Investigation',
                    description: 'Solve crimes and uncover secrets',
                    suitable_for: ['intermediate', 'experienced'],
                    themes: ['mystery', 'investigation', 'puzzles']
                },
                {
                    id: 'exploration_adventure',
                    name: 'Exploration & Discovery',
                    description: 'Explore unknown lands and discover wonders',
                    suitable_for: ['all_experience_levels'],
                    themes: ['exploration', 'discovery', 'wonder']
                },
                {
                    id: 'political_intrigue',
                    name: 'Political Intrigue',
                    description: 'Navigate court politics and schemes',
                    suitable_for: ['experienced'],
                    themes: ['politics', 'intrigue', 'social']
                }
            ],
            
            beginner_adventure_options: [
                {
                    id: 'lost_mine',
                    name: 'The Lost Mine of Phandelver',
                    description: 'A classic beginner adventure with goblins, magic, and treasure',
                    duration: '4-6 sessions',
                    difficulty: 'beginner_friendly',
                    themes: ['exploration', 'combat', 'mystery']
                },
                {
                    id: 'village_trouble',
                    name: 'Trouble in Willowbrook',
                    description: 'Help a small village with mysterious problems',
                    duration: '2-3 sessions',
                    difficulty: 'very_beginner_friendly',
                    themes: ['helping_others', 'simple_mystery', 'community']
                },
                {
                    id: 'first_dungeon',
                    name: 'Your First Dungeon',
                    description: 'A simple dungeon crawl perfect for learning',
                    duration: '1-2 sessions',
                    difficulty: 'tutorial',
                    themes: ['exploration', 'treasure', 'monsters']
                }
            ]
        };
        
        // Wizard state management
        this.wizardStates = {
            'not_started': 'Wizard not yet begun',
            'in_progress': 'Currently working through steps',
            'paused': 'Temporarily paused, can be resumed',
            'completed': 'Successfully finished setup',
            'abandoned': 'User left without completing',
            'error': 'Encountered error during setup'
        };
        
        // Integration with other services
        this.serviceIntegrations = {
            game_randomizer: {
                name: 'Game Content Generator',
                description: 'Automatically generate NPCs, encounters, and treasures',
                suitable_for: ['all_flows'],
                setup_complexity: 'simple'
            },
            ai_dm_personality: {
                name: 'AI DM Assistant',
                description: 'Get an AI DM personality to help guide your game',
                suitable_for: ['dm_first_time', 'experienced_quick_start'],
                setup_complexity: 'moderate'
            },
            player_bots: {
                name: 'AI Players',
                description: 'Add AI-controlled characters to fill out your party',
                suitable_for: ['all_flows'],
                setup_complexity: 'simple'
            },
            style_selector: {
                name: 'Visual Style',
                description: 'Choose how your game looks and feels',
                suitable_for: ['all_flows'],
                setup_complexity: 'simple'
            },
            tutorial_system: {
                name: 'Learning Support',
                description: 'Extra help and tutorials for new players',
                suitable_for: ['complete_beginner', 'dm_first_time'],
                setup_complexity: 'simple'
            }
        };
    }

    async beginWizard(options = {}) {
        try {
            const wizardId = uuidv4();
            
            // Determine which wizard flow to use
            const flowType = this._selectWizardFlow(options);
            const flow = this.wizardFlows[flowType];
            
            if (!flow) {
                throw new Error(`Invalid wizard flow: ${flowType}`);
            }
            
            // Initialize wizard session
            const wizard = {
                id: wizardId,
                flow_type: flowType,
                flow_config: flow,
                
                // Session info
                started_at: new Date(),
                updated_at: new Date(),
                state: 'in_progress',
                
                // User information
                user_info: {
                    experience_level: options.experience_level || 'unknown',
                    group_size: options.group_size || 4,
                    time_available: options.time_available || 'flexible',
                    preferences: options.preferences || [],
                    special_requirements: options.special_requirements || []
                },
                
                // Progress tracking
                current_step_index: 0,
                completed_steps: [],
                step_data: {},
                
                // Generated configuration
                game_configuration: {
                    players: [],
                    characters: [],
                    adventure: null,
                    settings: {},
                    integrations: []
                },
                
                // Wizard metadata
                estimated_completion_time: this._calculateEstimatedTime(flow),
                personalized_recommendations: [],
                encountered_issues: []
            };
            
            // Generate initial recommendations
            wizard.personalized_recommendations = await this._generateInitialRecommendations(wizard);
            
            // Cache wizard session
            await this.redis.setex(
                `wizard:${wizardId}`,
                3600 * 24, // 24 hours
                JSON.stringify(wizard)
            );
            
            this.logger.info(`Started wizard: ${flow.name} (${wizardId})`);
            this.io.emit('wizard_started', { 
                wizardId, 
                flowType,
                estimatedTime: wizard.estimated_completion_time 
            });
            
            return {
                wizard_id: wizardId,
                current_step: this._getCurrentStepInfo(wizard),
                estimated_time: wizard.estimated_completion_time,
                flow_info: flow
            };
            
        } catch (error) {
            this.logger.error('Error beginning wizard:', error);
            throw error;
        }
    }

    async processStep(wizardId, stepData) {
        try {
            // Load wizard session
            const wizard = await this._getWizardSession(wizardId);
            
            if (!wizard) {
                throw new Error('Wizard session not found');
            }
            
            if (wizard.state !== 'in_progress') {
                throw new Error(`Cannot process step: wizard state is ${wizard.state}`);
            }
            
            const currentStep = wizard.flow_config.steps[wizard.current_step_index];
            
            if (!currentStep) {
                throw new Error('No current step found');
            }
            
            // Validate step data
            const validation = await this._validateStepData(currentStep, stepData, wizard);
            if (!validation.valid) {
                return {
                    success: false,
                    errors: validation.errors,
                    current_step: this._getCurrentStepInfo(wizard)
                };
            }
            
            // Process the step data
            await this._processStepData(wizard, currentStep, stepData);
            
            // Mark step as completed
            wizard.completed_steps.push(currentStep.id);
            wizard.step_data[currentStep.id] = stepData;
            wizard.updated_at = new Date();
            
            // Advance to next step or complete wizard
            const nextStepResult = await this._advanceToNextStep(wizard);
            
            // Update cache
            await this.redis.setex(
                `wizard:${wizardId}`,
                3600 * 24,
                JSON.stringify(wizard)
            );
            
            this.logger.info(`Processed wizard step: ${currentStep.title} (${wizardId})`);
            this.io.emit('wizard_step_completed', { 
                wizardId, 
                completedStep: currentStep.id,
                nextStep: nextStepResult.next_step?.id 
            });
            
            return {
                success: true,
                completed_step: currentStep,
                next_step: nextStepResult.next_step,
                wizard_complete: nextStepResult.wizard_complete,
                game_configuration: nextStepResult.wizard_complete ? wizard.game_configuration : null
            };
            
        } catch (error) {
            this.logger.error('Error processing wizard step:', error);
            throw error;
        }
    }

    async getWizardStatus(wizardId) {
        try {
            const wizard = await this._getWizardSession(wizardId);
            
            if (!wizard) {
                throw new Error('Wizard session not found');
            }
            
            const currentStep = wizard.current_step_index < wizard.flow_config.steps.length ?
                wizard.flow_config.steps[wizard.current_step_index] : null;
            
            return {
                wizard_id: wizardId,
                state: wizard.state,
                flow_type: wizard.flow_type,
                current_step: currentStep,
                progress: {
                    completed_steps: wizard.completed_steps.length,
                    total_steps: wizard.flow_config.steps.length,
                    percentage: (wizard.completed_steps.length / wizard.flow_config.steps.length) * 100
                },
                estimated_time_remaining: this._calculateRemainingTime(wizard),
                game_configuration: wizard.game_configuration
            };
            
        } catch (error) {
            this.logger.error('Error getting wizard status:', error);
            throw error;
        }
    }

    async pauseWizard(wizardId) {
        try {
            const wizard = await this._getWizardSession(wizardId);
            
            if (!wizard) {
                throw new Error('Wizard session not found');
            }
            
            wizard.state = 'paused';
            wizard.paused_at = new Date();
            wizard.updated_at = new Date();
            
            await this.redis.setex(
                `wizard:${wizardId}`,
                3600 * 24,
                JSON.stringify(wizard)
            );
            
            this.logger.info(`Paused wizard: ${wizardId}`);
            this.io.emit('wizard_paused', { wizardId });
            
            return { success: true, state: 'paused' };
            
        } catch (error) {
            this.logger.error('Error pausing wizard:', error);
            throw error;
        }
    }

    async resumeWizard(wizardId) {
        try {
            const wizard = await this._getWizardSession(wizardId);
            
            if (!wizard) {
                throw new Error('Wizard session not found');
            }
            
            if (wizard.state !== 'paused') {
                throw new Error(`Cannot resume: wizard state is ${wizard.state}`);
            }
            
            wizard.state = 'in_progress';
            wizard.resumed_at = new Date();
            wizard.updated_at = new Date();
            
            await this.redis.setex(
                `wizard:${wizardId}`,
                3600 * 24,
                JSON.stringify(wizard)
            );
            
            this.logger.info(`Resumed wizard: ${wizardId}`);
            this.io.emit('wizard_resumed', { wizardId });
            
            return {
                success: true,
                state: 'in_progress',
                current_step: this._getCurrentStepInfo(wizard)
            };
            
        } catch (error) {
            this.logger.error('Error resuming wizard:', error);
            throw error;
        }
    }

    async getAvailableFlows(userProfile = {}) {
        try {
            const flows = Object.keys(this.wizardFlows).map(key => {
                const flow = this.wizardFlows[key];
                return {
                    id: key,
                    name: flow.name,
                    description: flow.description,
                    target_audience: flow.target_audience,
                    estimated_time: flow.estimated_time,
                    step_count: flow.steps.length,
                    suitability_score: this._calculateSuitabilityScore(flow, userProfile)
                };
            });
            
            // Sort by suitability score
            flows.sort((a, b) => b.suitability_score - a.suitability_score);
            
            return {
                flows: flows,
                recommended_flow: flows[0],
                user_profile_factors: this._getProfileFactors(userProfile)
            };
            
        } catch (error) {
            this.logger.error('Error getting available flows:', error);
            throw error;
        }
    }

    // Private helper methods
    _selectWizardFlow(options) {
        // Auto-select based on user profile
        if (options.flow_type) {
            return options.flow_type;
        }
        
        const experience = options.experience_level;
        const role = options.primary_role;
        const sessionType = options.session_type;
        
        if (experience === 'never_played') {
            return 'complete_beginner';
        }
        
        if (role === 'dm' && (experience === 'beginner' || options.first_time_dm)) {
            return 'dm_first_time';
        }
        
        if (sessionType === 'one_shot') {
            return 'one_shot_setup';
        }
        
        if (options.has_specific_requirements) {
            return 'custom_setup';
        }
        
        // Default for experienced players
        return 'experienced_quick_start';
    }

    _calculateEstimatedTime(flow) {
        const totalMinutes = flow.steps.reduce((sum, step) => sum + step.estimated_minutes, 0);
        return `${Math.floor(totalMinutes / 60)}h ${totalMinutes % 60}m`;
    }

    async _generateInitialRecommendations(wizard) {
        const recommendations = [];
        const userInfo = wizard.user_info;
        
        // Experience-based recommendations
        if (userInfo.experience_level === 'beginner') {
            recommendations.push({
                type: 'tutorial',
                priority: 'high',
                message: 'We recommend using our tutorial system to help learn the basics',
                action: 'enable_tutorial_mode'
            });
        }
        
        // Group size recommendations
        if (userInfo.group_size < 3) {
            recommendations.push({
                type: 'ai_players',
                priority: 'medium',
                message: 'Consider adding AI players to fill out your party',
                action: 'suggest_ai_players'
            });
        }
        
        // Time-based recommendations
        if (userInfo.time_available === 'limited') {
            recommendations.push({
                type: 'one_shot',
                priority: 'medium',
                message: 'One-shot adventures might be perfect for your schedule',
                action: 'suggest_one_shot_adventures'
            });
        }
        
        return recommendations;
    }

    _getCurrentStepInfo(wizard) {
        const currentIndex = wizard.current_step_index;
        const steps = wizard.flow_config.steps;
        
        if (currentIndex >= steps.length) {
            return null; // Wizard complete
        }
        
        const currentStep = steps[currentIndex];
        
        return {
            step_id: currentStep.id,
            title: currentStep.title,
            type: currentStep.type,
            content: this._getStepContent(currentStep),
            required: currentStep.required,
            estimated_minutes: currentStep.estimated_minutes,
            step_number: currentIndex + 1,
            total_steps: steps.length
        };
    }

    _getStepContent(step) {
        const contentKey = step.content;
        const content = this.stepContent[contentKey];
        
        if (!content) {
            return {
                title: step.title,
                description: `Content for ${step.type} step`,
                instructions: 'Please complete this step to continue.'
            };
        }
        
        return content;
    }

    async _getWizardSession(wizardId) {
        try {
            const cached = await this.redis.get(`wizard:${wizardId}`);
            return cached ? JSON.parse(cached) : null;
        } catch (error) {
            this.logger.error('Error getting wizard session:', error);
            return null;
        }
    }

    async _validateStepData(step, stepData, wizard) {
        const errors = [];
        
        // Check required fields based on step type
        switch (step.type) {
            case 'group_configuration':
                if (!stepData.player_count || stepData.player_count < 1) {
                    errors.push('Player count is required and must be at least 1');
                }
                if (stepData.player_count > 8) {
                    errors.push('Maximum 8 players supported');
                }
                break;
                
            case 'character_setup':
                if (!stepData.characters || stepData.characters.length === 0) {
                    errors.push('At least one character is required');
                }
                break;
                
            case 'adventure_selection':
                if (!stepData.selected_adventure) {
                    errors.push('Adventure selection is required');
                }
                break;
                
            case 'campaign_selection':
                if (!stepData.campaign_type) {
                    errors.push('Campaign type selection is required');
                }
                break;
        }
        
        return {
            valid: errors.length === 0,
            errors: errors
        };
    }

    async _processStepData(wizard, step, stepData) {
        // Update game configuration based on step data
        switch (step.type) {
            case 'group_configuration':
                wizard.game_configuration.players = stepData.players || [];
                wizard.game_configuration.settings.player_count = stepData.player_count;
                wizard.game_configuration.settings.dm_experience = stepData.dm_experience;
                break;
                
            case 'character_setup':
                wizard.game_configuration.characters = stepData.characters || [];
                break;
                
            case 'adventure_selection':
                wizard.game_configuration.adventure = stepData.selected_adventure;
                break;
                
            case 'campaign_selection':
                wizard.game_configuration.settings.campaign_type = stepData.campaign_type;
                wizard.game_configuration.settings.themes = stepData.themes;
                break;
                
            case 'customization':
                wizard.game_configuration.settings = {
                    ...wizard.game_configuration.settings,
                    ...stepData.customizations
                };
                break;
                
            case 'service_integration':
                wizard.game_configuration.integrations = stepData.selected_integrations || [];
                break;
                
            case 'personality_setup':
                wizard.game_configuration.settings.dm_personality = stepData.personality_selection;
                break;
        }
        
        // Generate additional content based on step completion
        await this._generateStepContent(wizard, step, stepData);
    }

    async _generateStepContent(wizard, step, stepData) {
        // Generate content specific to completed steps
        switch (step.id) {
            case 'character_creation':
                if (stepData.generate_additional_npcs) {
                    // Integration with game randomizer would happen here
                    wizard.game_configuration.generated_npcs = await this._generateNPCs(wizard);
                }
                break;
                
            case 'adventure_prep':
                if (stepData.need_prep_materials) {
                    wizard.game_configuration.dm_materials = await this._generateDMMaterials(wizard);
                }
                break;
                
            case 'customization':
                if (stepData.apply_style) {
                    // Integration with style selector would happen here
                    wizard.game_configuration.visual_style = stepData.selected_style;
                }
                break;
        }
    }

    async _advanceToNextStep(wizard) {
        wizard.current_step_index++;
        
        // Check if wizard is complete
        if (wizard.current_step_index >= wizard.flow_config.steps.length) {
            wizard.state = 'completed';
            wizard.completed_at = new Date();
            
            // Finalize game configuration
            await this._finalizeGameConfiguration(wizard);
            
            return {
                wizard_complete: true,
                next_step: null
            };
        }
        
        // Get next step
        const nextStep = wizard.flow_config.steps[wizard.current_step_index];
        
        return {
            wizard_complete: false,
            next_step: this._getCurrentStepInfo(wizard)
        };
    }

    async _finalizeGameConfiguration(wizard) {
        const config = wizard.game_configuration;
        
        // Generate final game session data
        config.session_data = {
            session_id: uuidv4(),
            created_at: new Date(),
            ready_to_start: true,
            setup_method: 'quick_start_wizard',
            wizard_flow: wizard.flow_type
        };
        
        // Create any missing required elements
        if (config.characters.length === 0 && config.settings.player_count > 0) {
            config.characters = await this._generateDefaultCharacters(config.settings.player_count);
        }
        
        if (!config.adventure && wizard.flow_type !== 'custom_setup') {
            config.adventure = await this._selectDefaultAdventure(wizard);
        }
        
        // Set up integration connections
        for (const integration of config.integrations) {
            await this._setupIntegration(integration, config);
        }
    }

    _calculateRemainingTime(wizard) {
        const remainingSteps = wizard.flow_config.steps.slice(wizard.current_step_index);
        const remainingMinutes = remainingSteps.reduce((sum, step) => sum + step.estimated_minutes, 0);
        
        if (remainingMinutes === 0) {
            return 'Complete';
        }
        
        return `${Math.floor(remainingMinutes / 60)}h ${remainingMinutes % 60}m`;
    }

    _calculateSuitabilityScore(flow, userProfile) {
        let score = 0.5; // Base score
        
        // Match target audience
        const targetAudience = flow.target_audience;
        const userExperience = userProfile.experience_level;
        
        if (targetAudience === 'never_played' && userExperience === 'never_played') {
            score += 0.4;
        } else if (targetAudience === 'experienced_players' && userExperience === 'experienced') {
            score += 0.3;
        } else if (targetAudience === 'new_dm' && userProfile.role === 'dm' && userExperience === 'beginner') {
            score += 0.4;
        }
        
        // Consider time constraints
        if (userProfile.time_available === 'limited' && flow.estimated_time.includes('10-15')) {
            score += 0.2;
        }
        
        return Math.min(score, 1.0);
    }

    _getProfileFactors(userProfile) {
        return {
            experience_considered: !!userProfile.experience_level,
            role_considered: !!userProfile.role,
            time_considered: !!userProfile.time_available,
            group_size_considered: !!userProfile.group_size
        };
    }

    // Integration helper methods (simplified)
    async _generateNPCs(wizard) {
        return [{ name: 'Generated NPC', role: 'shopkeeper' }];
    }

    async _generateDMMaterials(wizard) {
        return { handouts: [], maps: [], reference_sheets: [] };
    }

    async _generateDefaultCharacters(count) {
        const characters = [];
        const classes = ['fighter', 'rogue', 'wizard', 'cleric'];
        
        for (let i = 0; i < count; i++) {
            characters.push({
                name: `Hero ${i + 1}`,
                class: classes[i % classes.length],
                level: 1,
                generated: true
            });
        }
        
        return characters;
    }

    async _selectDefaultAdventure(wizard) {
        return {
            name: 'Default Adventure',
            type: 'beginner_friendly',
            description: 'A simple adventure perfect for getting started'
        };
    }

    async _setupIntegration(integration, config) {
        // Set up connections with other services
        this.logger.info(`Setting up integration: ${integration}`);
    }

    async getStats() {
        try {
            const wizardKeys = await this.redis.keys('wizard:*');
            const totalWizards = wizardKeys.length;
            
            let completionRates = {};
            let flowDistribution = {};
            let avgStepsCompleted = 0;
            
            for (const key of wizardKeys.slice(0, 100)) {
                try {
                    const data = await this.redis.get(key);
                    if (data) {
                        const wizard = JSON.parse(data);
                        
                        const flowType = wizard.flow_type;
                        flowDistribution[flowType] = (flowDistribution[flowType] || 0) + 1;
                        
                        const completionRate = wizard.completed_steps.length / wizard.flow_config.steps.length;
                        const completionCategory = completionRate === 1 ? 'completed' : 
                                                completionRate > 0.5 ? 'partial' : 'abandoned';
                        completionRates[completionCategory] = (completionRates[completionCategory] || 0) + 1;
                        
                        avgStepsCompleted += wizard.completed_steps.length;
                    }
                } catch (error) {
                    // Skip invalid wizard data
                }
            }
            
            return {
                total_wizards: totalWizards,
                completion_rates: completionRates,
                flow_distribution: flowDistribution,
                average_steps_completed: totalWizards > 0 ? avgStepsCompleted / totalWizards : 0,
                active_wizards: 0 // Could implement active session tracking
            };
            
        } catch (error) {
            this.logger.error('Error getting wizard stats:', error);
            return {
                total_wizards: 0,
                completion_rates: {},
                flow_distribution: {},
                average_steps_completed: 0,
                active_wizards: 0
            };
        }
    }
}

module.exports = QuickStartWizard;