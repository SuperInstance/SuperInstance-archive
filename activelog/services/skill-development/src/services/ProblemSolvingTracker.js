const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');

class ProblemSolvingTracker extends EventEmitter {
    constructor() {
        super();
        this.assessments = new Map();
        this.profiles = new Map();
        this.problemSolvingFrameworks = this.initializeProblemSolvingFrameworks();
        this.developmentalStages = this.initializeDevelopmentalStages();
        this.assessmentProtocols = this.initializeAssessmentProtocols();
        this.interventionStrategies = this.initializeInterventionStrategies();
        this.problemTypes = this.initializeProblemTypes();
    }

    initializeProblemSolvingFrameworks() {
        return {
            polya_framework: {
                description: "George Polya's four-step problem-solving process",
                steps: [
                    {
                        name: 'understand_problem',
                        description: 'Understand what the problem is asking',
                        skills: [
                            'Reading comprehension',
                            'Information identification',
                            'Constraint recognition',
                            'Goal clarification',
                            'Question analysis'
                        ],
                        assessments: [
                            'Problem restatement accuracy',
                            'Key information extraction',
                            'Constraint identification',
                            'Goal articulation clarity'
                        ]
                    },
                    {
                        name: 'devise_plan',
                        description: 'Develop a strategy to solve the problem',
                        skills: [
                            'Strategy selection',
                            'Pattern recognition',
                            'Analogical reasoning',
                            'Resource identification',
                            'Step sequencing'
                        ],
                        assessments: [
                            'Strategy appropriateness',
                            'Plan completeness',
                            'Resource utilization',
                            'Step logical sequence'
                        ]
                    },
                    {
                        name: 'carry_out_plan',
                        description: 'Execute the chosen strategy',
                        skills: [
                            'Plan execution',
                            'Monitoring progress',
                            'Persistence through obstacles',
                            'Strategy adjustment',
                            'Accurate computation'
                        ],
                        assessments: [
                            'Execution accuracy',
                            'Progress monitoring',
                            'Obstacle handling',
                            'Strategy flexibility'
                        ]
                    },
                    {
                        name: 'look_back',
                        description: 'Check and reflect on the solution',
                        skills: [
                            'Solution verification',
                            'Alternative method consideration',
                            'Process reflection',
                            'Generalization ability',
                            'Error identification'
                        ],
                        assessments: [
                            'Verification thoroughness',
                            'Alternative consideration',
                            'Reflection depth',
                            'Learning extraction'
                        ]
                    }
                ]
            },
            systems_thinking: {
                description: "Systems approach to complex problem solving",
                components: [
                    {
                        name: 'system_identification',
                        description: 'Recognize the system and its boundaries',
                        skills: [
                            'Boundary setting',
                            'Component identification',
                            'Relationship mapping',
                            'Scale consideration',
                            'Context awareness'
                        ]
                    },
                    {
                        name: 'pattern_analysis',
                        description: 'Identify patterns and feedback loops',
                        skills: [
                            'Pattern recognition',
                            'Cause-effect relationships',
                            'Feedback loop identification',
                            'Delay recognition',
                            'Leverage point identification'
                        ]
                    },
                    {
                        name: 'mental_modeling',
                        description: 'Develop mental models of the system',
                        skills: [
                            'Model construction',
                            'Model testing',
                            'Model refinement',
                            'Scenario planning',
                            'Prediction ability'
                        ]
                    },
                    {
                        name: 'intervention_design',
                        description: 'Design effective interventions',
                        skills: [
                            'Intervention planning',
                            'Unintended consequence consideration',
                            'Multiple solution generation',
                            'Implementation planning',
                            'Monitoring design'
                        ]
                    }
                ]
            },
            design_thinking_problem_solving: {
                description: "Human-centered approach to problem solving",
                phases: [
                    {
                        name: 'empathize',
                        description: 'Understand the human needs involved',
                        skills: [
                            'Perspective taking',
                            'Stakeholder analysis',
                            'Need identification',
                            'Context understanding',
                            'Human-centered focus'
                        ]
                    },
                    {
                        name: 'define',
                        description: 'Frame the problem from human perspective',
                        skills: [
                            'Problem framing',
                            'Point-of-view development',
                            'Need statement crafting',
                            'Criteria establishment',
                            'Scope definition'
                        ]
                    },
                    {
                        name: 'ideate',
                        description: 'Generate creative solution ideas',
                        skills: [
                            'Brainstorming',
                            'Creative thinking',
                            'Idea generation',
                            'Solution diversity',
                            'Innovation thinking'
                        ]
                    },
                    {
                        name: 'prototype',
                        description: 'Build quick testable versions',
                        skills: [
                            'Rapid prototyping',
                            'Concept visualization',
                            'Testing preparation',
                            'Iteration mindset',
                            'Resource efficiency'
                        ]
                    },
                    {
                        name: 'test',
                        description: 'Test solutions with real users',
                        skills: [
                            'Testing methodology',
                            'Feedback collection',
                            'Iteration based on learning',
                            'Solution refinement',
                            'Impact measurement'
                        ]
                    }
                ]
            },
            computational_thinking: {
                description: "Breaking down complex problems systematically",
                elements: [
                    {
                        name: 'decomposition',
                        description: 'Break complex problems into smaller parts',
                        skills: [
                            'Problem breakdown',
                            'Subtask identification',
                            'Hierarchy creation',
                            'Dependency mapping',
                            'Modular thinking'
                        ]
                    },
                    {
                        name: 'pattern_recognition',
                        description: 'Find similarities and patterns',
                        skills: [
                            'Pattern identification',
                            'Similarity recognition',
                            'Template matching',
                            'Generalization',
                            'Classification ability'
                        ]
                    },
                    {
                        name: 'abstraction',
                        description: 'Focus on essential features',
                        skills: [
                            'Essential feature identification',
                            'Detail filtering',
                            'Model creation',
                            'Concept generalization',
                            'Simplification ability'
                        ]
                    },
                    {
                        name: 'algorithm_design',
                        description: 'Create step-by-step solutions',
                        skills: [
                            'Step sequencing',
                            'Logic flow design',
                            'Instruction clarity',
                            'Efficiency consideration',
                            'Error handling'
                        ]
                    }
                ]
            }
        };
    }

    initializeDevelopmentalStages() {
        return {
            ages_4_5: {
                cognitive_abilities: [
                    'Concrete operational thinking emerging',
                    'Simple cause-effect understanding',
                    'Basic categorization skills',
                    'Sequential thinking development',
                    'Simple pattern recognition'
                ],
                problem_solving_characteristics: [
                    'Trial-and-error approach dominant',
                    'Concrete problem preference',
                    'Single-step solutions',
                    'Immediate feedback needs',
                    'Visual representation helpful'
                ],
                typical_strategies: [
                    'Hands-on manipulation',
                    'Visual exploration',
                    'Simple elimination',
                    'Imitation of successful approaches',
                    'Adult guidance seeking'
                ],
                assessment_focus: [
                    'Problem recognition',
                    'Simple strategy application',
                    'Persistence measurement',
                    'Help-seeking behavior',
                    'Solution communication'
                ]
            },
            ages_6_7: {
                cognitive_abilities: [
                    'Concrete operations established',
                    'Logical thinking in familiar contexts',
                    'Classification and seriation',
                    'Basic conservation understanding',
                    'Rule-based thinking'
                ],
                problem_solving_characteristics: [
                    'More systematic approaches',
                    'Multi-step problem handling',
                    'Strategy comparison beginning',
                    'Planning ahead emerging',
                    'Error correction improving'
                ],
                typical_strategies: [
                    'Systematic trial-and-error',
                    'Simple planning',
                    'Pattern-based solutions',
                    'Rule application',
                    'Strategy modification'
                ],
                assessment_focus: [
                    'Strategy selection',
                    'Plan execution',
                    'Error monitoring',
                    'Strategy flexibility',
                    'Solution explanation'
                ]
            },
            ages_8_10: {
                cognitive_abilities: [
                    'Concrete operations mastered',
                    'Logical reasoning in concrete domains',
                    'Multiple classification',
                    'Reversible thinking',
                    'Conservation across domains'
                ],
                problem_solving_characteristics: [
                    'Strategic thinking development',
                    'Multiple solution generation',
                    'Planning and monitoring',
                    'Strategy evaluation',
                    'Transfer beginning'
                ],
                typical_strategies: [
                    'Means-ends analysis',
                    'Working backwards',
                    'Analogy application',
                    'Systematic testing',
                    'Strategy combination'
                ],
                assessment_focus: [
                    'Strategy sophistication',
                    'Planning quality',
                    'Monitoring effectiveness',
                    'Transfer ability',
                    'Reflection depth'
                ]
            },
            ages_11_plus: {
                cognitive_abilities: [
                    'Formal operations emerging',
                    'Abstract thinking development',
                    'Hypothetical reasoning',
                    'Systematic experimentation',
                    'Metacognitive awareness'
                ],
                problem_solving_characteristics: [
                    'Abstract problem handling',
                    'Hypothesis generation',
                    'Systematic testing',
                    'Strategy optimization',
                    'Transfer across domains'
                ],
                typical_strategies: [
                    'Hypothesis testing',
                    'Abstract reasoning',
                    'Systematic variation',
                    'Strategy integration',
                    'Meta-strategy use'
                ],
                assessment_focus: [
                    'Abstract reasoning',
                    'Hypothesis quality',
                    'Systematic approach',
                    'Strategy integration',
                    'Metacognitive reflection'
                ]
            }
        };
    }

    initializeProblemTypes() {
        return {
            mathematical_problems: {
                subcategories: [
                    'arithmetic_word_problems',
                    'geometry_spatial_problems',
                    'algebraic_relationships',
                    'statistical_reasoning',
                    'mathematical_modeling'
                ],
                cognitive_demands: [
                    'quantitative reasoning',
                    'spatial visualization',
                    'logical deduction',
                    'pattern recognition',
                    'symbolic manipulation'
                ]
            },
            scientific_problems: {
                subcategories: [
                    'hypothesis_testing',
                    'experimental_design',
                    'data_interpretation',
                    'scientific_modeling',
                    'cause_effect_analysis'
                ],
                cognitive_demands: [
                    'scientific_reasoning',
                    'evidence_evaluation',
                    'hypothesis_generation',
                    'experimental_thinking',
                    'data_analysis'
                ]
            },
            social_problems: {
                subcategories: [
                    'interpersonal_conflicts',
                    'group_decision_making',
                    'resource_allocation',
                    'negotiation_scenarios',
                    'ethical_dilemmas'
                ],
                cognitive_demands: [
                    'perspective_taking',
                    'social_reasoning',
                    'moral_reasoning',
                    'negotiation_skills',
                    'empathy_application'
                ]
            },
            creative_problems: {
                subcategories: [
                    'open_ended_challenges',
                    'design_problems',
                    'invention_tasks',
                    'artistic_challenges',
                    'innovation_scenarios'
                ],
                cognitive_demands: [
                    'divergent_thinking',
                    'creative_synthesis',
                    'aesthetic_reasoning',
                    'originality',
                    'elaboration_skills'
                ]
            },
            practical_problems: {
                subcategories: [
                    'everyday_life_challenges',
                    'resource_management',
                    'time_management',
                    'tool_usage_problems',
                    'efficiency_optimization'
                ],
                cognitive_demands: [
                    'practical_reasoning',
                    'resource_optimization',
                    'efficiency_thinking',
                    'tool_selection',
                    'constraint_management'
                ]
            },
            technology_problems: {
                subcategories: [
                    'debugging_challenges',
                    'system_optimization',
                    'user_interface_design',
                    'data_processing',
                    'automation_design'
                ],
                cognitive_demands: [
                    'logical_debugging',
                    'systems_thinking',
                    'user_experience_reasoning',
                    'algorithmic_thinking',
                    'efficiency_optimization'
                ]
            }
        };
    }

    initializeAssessmentProtocols() {
        return {
            think_aloud_protocol: {
                description: 'Verbal protocol analysis during problem solving',
                age_range: '6-18',
                duration: '30-45 minutes',
                data_collected: [
                    'Problem understanding verbalizations',
                    'Strategy selection reasoning',
                    'Monitoring comments',
                    'Self-correction instances',
                    'Reflection statements'
                ],
                analysis_methods: [
                    'Cognitive process identification',
                    'Strategy categorization',
                    'Metacognitive awareness assessment',
                    'Problem-solving phase analysis',
                    'Error pattern identification'
                ]
            },
            problem_solving_observation: {
                description: 'Structured observation of problem-solving behavior',
                age_range: '4-18',
                duration: '20-60 minutes',
                data_collected: [
                    'Initial problem approach',
                    'Strategy changes',
                    'Persistence behaviors',
                    'Help-seeking patterns',
                    'Solution verification actions'
                ],
                analysis_methods: [
                    'Behavioral coding',
                    'Strategy effectiveness evaluation',
                    'Persistence measurement',
                    'Self-regulation assessment',
                    'Social problem-solving evaluation'
                ]
            },
            problem_solving_interview: {
                description: 'Semi-structured interview about problem-solving approach',
                age_range: '6-18',
                duration: '15-30 minutes',
                data_collected: [
                    'Strategy awareness',
                    'Problem-solving beliefs',
                    'Self-efficacy perceptions',
                    'Transfer understanding',
                    'Metacognitive knowledge'
                ],
                analysis_methods: [
                    'Thematic analysis',
                    'Metacognitive knowledge assessment',
                    'Belief system evaluation',
                    'Self-efficacy measurement',
                    'Transfer potential estimation'
                ]
            },
            performance_based_assessment: {
                description: 'Direct assessment through problem-solving tasks',
                age_range: '4-18',
                duration: '45-90 minutes',
                data_collected: [
                    'Solution accuracy',
                    'Strategy efficiency',
                    'Time to solution',
                    'Error patterns',
                    'Transfer performance'
                ],
                analysis_methods: [
                    'Accuracy scoring',
                    'Efficiency calculation',
                    'Strategy sophistication rating',
                    'Error analysis',
                    'Transfer measurement'
                ]
            },
            portfolio_assessment: {
                description: 'Collection of problem-solving work over time',
                age_range: '5-18',
                duration: 'ongoing',
                data_collected: [
                    'Problem-solving artifacts',
                    'Reflection documents',
                    'Strategy evolution evidence',
                    'Peer collaboration products',
                    'Self-assessment records'
                ],
                analysis_methods: [
                    'Growth documentation',
                    'Strategy development tracking',
                    'Reflection quality evaluation',
                    'Collaboration skills assessment',
                    'Self-awareness measurement'
                ]
            }
        };
    }

    initializeInterventionStrategies() {
        return {
            strategy_instruction: {
                description: 'Explicit teaching of problem-solving strategies',
                components: [
                    'Strategy demonstration',
                    'Guided practice',
                    'Independent application',
                    'Strategy comparison',
                    'Metacognitive reflection'
                ],
                age_adaptations: {
                    'ages_4_5': [
                        'Visual strategy representations',
                        'Simple step-by-step guides',
                        'Concrete problem examples',
                        'Immediate feedback provision',
                        'Success celebration'
                    ],
                    'ages_6_7': [
                        'Strategy choice explanations',
                        'Multiple strategy exposure',
                        'Strategy effectiveness discussions',
                        'Peer strategy sharing',
                        'Strategy transfer practice'
                    ],
                    'ages_8_10': [
                        'Strategy condition learning',
                        'Strategy combination instruction',
                        'Cross-domain transfer practice',
                        'Strategy evaluation training',
                        'Personal strategy development'
                    ],
                    'ages_11_plus': [
                        'Abstract strategy principles',
                        'Strategy optimization techniques',
                        'Domain-general principles',
                        'Strategy creation guidance',
                        'Metacognitive strategy use'
                    ]
                }
            },
            metacognitive_training: {
                description: 'Development of thinking about thinking skills',
                components: [
                    'Self-questioning techniques',
                    'Planning instruction',
                    'Monitoring training',
                    'Evaluation skills',
                    'Reflection practices'
                ],
                techniques: [
                    'Think-aloud modeling',
                    'Self-monitoring checklists',
                    'Reflection journals',
                    'Peer coaching',
                    'Strategy evaluation rubrics'
                ]
            },
            collaborative_problem_solving: {
                description: 'Group-based problem-solving development',
                components: [
                    'Group formation strategies',
                    'Communication skill development',
                    'Collaborative strategy instruction',
                    'Conflict resolution training',
                    'Group reflection practices'
                ],
                benefits: [
                    'Multiple perspective exposure',
                    'Strategy sharing',
                    'Peer scaffolding',
                    'Communication development',
                    'Social problem-solving'
                ]
            },
            authentic_problem_experiences: {
                description: 'Real-world problem-solving opportunities',
                components: [
                    'Community problem identification',
                    'Stakeholder engagement',
                    'Solution implementation',
                    'Impact evaluation',
                    'Learning reflection'
                ],
                examples: [
                    'School improvement projects',
                    'Environmental challenges',
                    'Community service problems',
                    'Technology solution development',
                    'Social issue addressing'
                ]
            },
            scaffolded_practice: {
                description: 'Graduated support for problem-solving development',
                levels: [
                    'Full modeling and guidance',
                    'Partial guidance with hints',
                    'Minimal prompting',
                    'Independent practice',
                    'Teaching others'
                ],
                scaffolding_techniques: [
                    'Questioning sequences',
                    'Visual organizers',
                    'Strategy reminders',
                    'Peer partnerships',
                    'Technology supports'
                ]
            }
        };
    }

    createProfile(studentId, age, currentProblemSolvingLevel = 'developing') {
        const profile = {
            id: uuidv4(),
            studentId,
            age,
            currentLevel: currentProblemSolvingLevel,
            problemSolvingProfile: this.initializeProblemSolvingProfile(),
            assessmentHistory: [],
            interventionHistory: [],
            developmentalTrajectory: {},
            strengthAreas: [],
            challengeAreas: [],
            createdAt: moment().toISOString(),
            updatedAt: moment().toISOString()
        };

        this.profiles.set(profile.id, profile);
        this.emit('profileCreated', { profileId: profile.id, studentId });

        return profile.id;
    }

    initializeProblemSolvingProfile() {
        const profile = {};
        
        Object.keys(this.problemSolvingFrameworks).forEach(framework => {
            profile[framework] = {
                overallScore: 0,
                percentile: 0,
                componentScores: {},
                masteryLevel: 'emerging',
                strengthAreas: [],
                developmentNeeds: []
            };
        });

        Object.keys(this.problemTypes).forEach(problemType => {
            profile[problemType] = {
                performance: 0,
                engagement: 0,
                transferability: 0,
                preference: 0
            };
        });

        return profile;
    }

    conductAssessment(profileId, assessmentType, problemSet, observationData = {}) {
        const profile = this.profiles.get(profileId);
        if (!profile) {
            throw new Error('Profile not found');
        }

        const assessment = {
            id: uuidv4(),
            type: assessmentType,
            problemSet,
            observationData,
            responses: {},
            scores: {},
            analysis: {},
            recommendations: [],
            timestamp: moment().toISOString()
        };

        assessment.responses = this.collectResponses(problemSet, observationData);
        assessment.scores = this.scoreAssessment(assessment.responses, profile.age, assessmentType);
        assessment.analysis = this.analyzePerformance(assessment.scores, assessment.responses, profile);
        assessment.recommendations = this.generateRecommendations(assessment.analysis, profile);

        profile.assessmentHistory.push(assessment);
        profile.problemSolvingProfile = this.updateProblemSolvingProfile(
            profile.problemSolvingProfile, 
            assessment
        );
        profile.updatedAt = moment().toISOString();

        this.assessments.set(assessment.id, assessment);
        this.emit('assessmentCompleted', { 
            profileId, 
            assessmentId: assessment.id,
            scores: assessment.scores 
        });

        return assessment.id;
    }

    collectResponses(problemSet, observationData) {
        const responses = {
            problemSolutions: {},
            processObservations: observationData,
            timeData: {},
            strategyUsage: {},
            verbalizations: observationData.thinkAloud || [],
            errorPatterns: {},
            helpSeekingBehavior: observationData.helpSeeking || {}
        };

        problemSet.forEach(problem => {
            responses.problemSolutions[problem.id] = {
                solution: problem.studentSolution,
                correctness: problem.isCorrect,
                strategy: problem.strategyUsed,
                timeSpent: problem.timeSpent,
                attempts: problem.attempts,
                selfCorrections: problem.selfCorrections || 0
            };
        });

        return responses;
    }

    scoreAssessment(responses, age, assessmentType) {
        const scores = {
            overall: 0,
            frameworkScores: {},
            problemTypeScores: {},
            processScores: {},
            metacognitiveScores: {}
        };

        scores.frameworkScores = this.scoreByFramework(responses, age);
        scores.problemTypeScores = this.scoreByProblemType(responses);
        scores.processScores = this.scoreProcesses(responses, age);
        scores.metacognitiveScores = this.scoreMetacognition(responses, age);

        const allScores = [
            ...Object.values(scores.frameworkScores),
            ...Object.values(scores.problemTypeScores),
            ...Object.values(scores.processScores),
            ...Object.values(scores.metacognitiveScores)
        ].filter(score => typeof score === 'number' && !isNaN(score));

        scores.overall = allScores.length > 0 ? 
            allScores.reduce((sum, score) => sum + score, 0) / allScores.length : 0;

        return scores;
    }

    scoreByFramework(responses, age) {
        const frameworkScores = {};

        Object.keys(this.problemSolvingFrameworks).forEach(framework => {
            const frameworkData = this.problemSolvingFrameworks[framework];
            let frameworkScore = 0;

            if (framework === 'polya_framework') {
                frameworkScore = this.scorePolyaFramework(responses, age);
            } else if (framework === 'systems_thinking') {
                frameworkScore = this.scoreSystemsThinking(responses, age);
            } else if (framework === 'design_thinking_problem_solving') {
                frameworkScore = this.scoreDesignThinking(responses, age);
            } else if (framework === 'computational_thinking') {
                frameworkScore = this.scoreComputationalThinking(responses, age);
            }

            frameworkScores[framework] = frameworkScore;
        });

        return frameworkScores;
    }

    scorePolyaFramework(responses, age) {
        let totalScore = 0;
        let stepCount = 0;

        const understandingScore = this.evaluateProblemUnderstanding(responses);
        const planningScore = this.evaluatePlanning(responses);
        const executionScore = this.evaluateExecution(responses);
        const verificationScore = this.evaluateVerification(responses);

        totalScore = (understandingScore + planningScore + executionScore + verificationScore) / 4;
        
        return Math.min(Math.max(totalScore, 0), 100);
    }

    evaluateProblemUnderstanding(responses) {
        let score = 0;
        const solutions = responses.problemSolutions;
        const verbalizations = responses.verbalizations;

        Object.values(solutions).forEach(solution => {
            if (solution.strategy && solution.strategy !== 'random') score += 15;
            if (solution.attempts <= 3) score += 10;
        });

        if (verbalizations.some(v => v.includes('understand') || v.includes('means'))) {
            score += 20;
        }

        return Math.min(score, 100);
    }

    evaluatePlanning(responses) {
        let score = 0;
        const solutions = responses.problemSolutions;
        const observations = responses.processObservations;

        if (observations.planningBehavior) {
            score += 30;
        }

        Object.values(solutions).forEach(solution => {
            if (solution.strategy && solution.strategy !== 'trial_and_error') {
                score += 15;
            }
        });

        return Math.min(score, 100);
    }

    evaluateExecution(responses) {
        let score = 0;
        const solutions = responses.problemSolutions;

        const correctSolutions = Object.values(solutions).filter(s => s.correctness).length;
        const totalSolutions = Object.values(solutions).length;
        
        score = (correctSolutions / totalSolutions) * 100;
        
        return score;
    }

    evaluateVerification(responses) {
        let score = 0;
        const solutions = responses.problemSolutions;
        const observations = responses.processObservations;

        if (observations.verificationBehavior) {
            score += 40;
        }

        const selfCorrectionCount = Object.values(solutions)
            .reduce((sum, s) => sum + (s.selfCorrections || 0), 0);
        
        score += Math.min(selfCorrectionCount * 10, 60);

        return Math.min(score, 100);
    }

    scoreSystemsThinking(responses, age) {
        let score = 0;
        const observations = responses.processObservations;

        if (observations.systemIdentification) score += 25;
        if (observations.patternRecognition) score += 25;
        if (observations.connectionMaking) score += 25;
        if (observations.holisticApproach) score += 25;

        return score;
    }

    scoreDesignThinking(responses, age) {
        let score = 0;
        const observations = responses.processObservations;

        if (observations.empathyBehavior) score += 20;
        if (observations.problemReframing) score += 20;
        if (observations.ideaGeneration) score += 20;
        if (observations.prototyping) score += 20;
        if (observations.testingBehavior) score += 20;

        return score;
    }

    scoreComputationalThinking(responses, age) {
        let score = 0;
        const solutions = responses.problemSolutions;
        const observations = responses.processObservations;

        if (observations.problemDecomposition) score += 25;
        if (observations.patternRecognition) score += 25;
        if (observations.abstraction) score += 25;
        
        const systematicSolutions = Object.values(solutions)
            .filter(s => s.strategy && s.strategy.includes('systematic')).length;
        score += Math.min(systematicSolutions * 5, 25);

        return score;
    }

    scoreByProblemType(responses) {
        const typeScores = {};
        const solutions = responses.problemSolutions;

        Object.keys(this.problemTypes).forEach(problemType => {
            const relevantSolutions = Object.values(solutions).filter(s => 
                s.problemType === problemType
            );
            
            if (relevantSolutions.length > 0) {
                const correctCount = relevantSolutions.filter(s => s.correctness).length;
                typeScores[problemType] = (correctCount / relevantSolutions.length) * 100;
            } else {
                typeScores[problemType] = 0;
            }
        });

        return typeScores;
    }

    scoreProcesses(responses, age) {
        const processScores = {};
        const ageStage = this.getAgeStage(age);
        const expectedProcesses = this.developmentalStages[ageStage];

        processScores.strategy_selection = this.evaluateStrategySelection(responses, expectedProcesses);
        processScores.monitoring = this.evaluateMonitoring(responses, age);
        processScores.persistence = this.evaluatePersistence(responses);
        processScores.flexibility = this.evaluateFlexibility(responses);
        processScores.transfer = this.evaluateTransfer(responses);

        return processScores;
    }

    evaluateStrategySelection(responses, expectedProcesses) {
        let score = 0;
        const solutions = responses.problemSolutions;
        const strategies = Object.values(solutions).map(s => s.strategy).filter(s => s);

        const uniqueStrategies = [...new Set(strategies)];
        score += Math.min(uniqueStrategies.length * 15, 60);

        const appropriateStrategies = strategies.filter(s => 
            expectedProcesses.typical_strategies.includes(s)
        ).length;
        score += Math.min(appropriateStrategies * 10, 40);

        return Math.min(score, 100);
    }

    evaluateMonitoring(responses, age) {
        let score = 0;
        const verbalizations = responses.verbalizations;
        const solutions = responses.problemSolutions;

        const monitoringVerbalizations = verbalizations.filter(v => 
            v.includes('check') || v.includes('think') || v.includes('wait')
        );
        score += Math.min(monitoringVerbalizations.length * 10, 50);

        const selfCorrectionTotal = Object.values(solutions)
            .reduce((sum, s) => sum + (s.selfCorrections || 0), 0);
        score += Math.min(selfCorrectionTotal * 12, 50);

        return Math.min(score, 100);
    }

    evaluatePersistence(responses) {
        let score = 0;
        const solutions = responses.problemSolutions;
        const observations = responses.processObservations;

        const averageAttempts = Object.values(solutions)
            .reduce((sum, s) => sum + (s.attempts || 1), 0) / Object.values(solutions).length;
        
        if (averageAttempts > 1) score += 30;
        if (averageAttempts > 2) score += 20;

        if (observations.persistenceBehavior) score += 50;

        return Math.min(score, 100);
    }

    evaluateFlexibility(responses) {
        let score = 0;
        const solutions = responses.problemSolutions;

        const strategyChanges = Object.values(solutions).filter(s => 
            s.attempts > 1 && s.strategy !== 'trial_and_error'
        ).length;

        score += Math.min(strategyChanges * 20, 100);

        return score;
    }

    evaluateTransfer(responses) {
        let score = 0;
        const solutions = responses.problemSolutions;

        const similarProblems = this.identifySimilarProblems(solutions);
        const consistentStrategies = this.checkStrategyConsistency(similarProblems);

        score += Math.min(consistentStrategies * 25, 100);

        return score;
    }

    scoreMetacognition(responses, age) {
        const metacognitiveScores = {};
        const verbalizations = responses.verbalizations;
        const observations = responses.processObservations;

        metacognitiveScores.self_awareness = this.evaluateSelfAwareness(verbalizations, observations);
        metacognitiveScores.strategy_knowledge = this.evaluateStrategyKnowledge(verbalizations, responses);
        metacognitiveScores.planning_monitoring = this.evaluatePlanningMonitoring(verbalizations, observations);
        metacognitiveScores.reflection = this.evaluateReflection(verbalizations, observations);

        return metacognitiveScores;
    }

    evaluateSelfAwareness(verbalizations, observations) {
        let score = 0;

        const selfAwarenessIndicators = verbalizations.filter(v =>
            v.includes('I think') || v.includes('I know') || v.includes('I\'m not sure')
        );
        score += Math.min(selfAwarenessIndicators.length * 15, 75);

        if (observations.accurateSelfAssessment) score += 25;

        return Math.min(score, 100);
    }

    evaluateStrategyKnowledge(verbalizations, responses) {
        let score = 0;
        const solutions = responses.problemSolutions;

        const strategyExplanations = verbalizations.filter(v =>
            v.includes('because') || v.includes('so I will') || v.includes('strategy')
        );
        score += Math.min(strategyExplanations.length * 20, 60);

        const appropriateStrategyUse = Object.values(solutions).filter(s =>
            s.strategy && s.strategy !== 'random' && s.correctness
        ).length;
        score += Math.min(appropriateStrategyUse * 10, 40);

        return Math.min(score, 100);
    }

    analyzePerformance(scores, responses, profile) {
        const analysis = {
            overallPerformance: this.categorizePerformance(scores.overall),
            frameworkStrengths: this.identifyFrameworkStrengths(scores.frameworkScores),
            frameworkWeaknesses: this.identifyFrameworkWeaknesses(scores.frameworkScores),
            problemTypePreferences: this.identifyProblemTypePreferences(scores.problemTypeScores),
            processStrengths: this.identifyProcessStrengths(scores.processScores),
            processWeaknesses: this.identifyProcessWeaknesses(scores.processScores),
            metacognitiveProfile: this.analyzeMetacognitiveProfile(scores.metacognitiveScores),
            developmentalAlignment: this.assessDevelopmentalAlignment(scores, profile.age),
            transferPotential: this.assessTransferPotential(responses, scores),
            motivationalFactors: this.analyzeMotivationalFactors(responses)
        };

        return analysis;
    }

    categorizePerformance(overallScore) {
        if (overallScore >= 85) return 'exceptional';
        if (overallScore >= 70) return 'proficient';
        if (overallScore >= 55) return 'developing';
        if (overallScore >= 40) return 'emerging';
        return 'needs_support';
    }

    identifyFrameworkStrengths(frameworkScores) {
        const threshold = 70;
        return Object.entries(frameworkScores)
            .filter(([framework, score]) => score >= threshold)
            .map(([framework, score]) => ({
                framework,
                score,
                level: score >= 85 ? 'strong' : 'moderate'
            }));
    }

    identifyFrameworkWeaknesses(frameworkScores) {
        const threshold = 50;
        return Object.entries(frameworkScores)
            .filter(([framework, score]) => score < threshold)
            .map(([framework, score]) => ({
                framework,
                score,
                priority: score < 30 ? 'high' : 'medium'
            }));
    }

    generateRecommendations(analysis, profile) {
        const recommendations = [];

        analysis.frameworkWeaknesses.forEach(weakness => {
            recommendations.push({
                type: 'framework_development',
                target: weakness.framework,
                priority: weakness.priority,
                strategies: this.getFrameworkStrategies(weakness.framework, profile.age),
                timeframe: '6-8 weeks'
            });
        });

        analysis.processWeaknesses.forEach(weakness => {
            recommendations.push({
                type: 'process_skill_development',
                target: weakness.process,
                priority: weakness.priority,
                strategies: this.getProcessStrategies(weakness.process, profile.age),
                timeframe: '4-6 weeks'
            });
        });

        if (analysis.metacognitiveProfile.overall < 60) {
            recommendations.push({
                type: 'metacognitive_development',
                target: 'metacognitive_awareness',
                priority: 'high',
                strategies: this.interventionStrategies.metacognitive_training.techniques,
                timeframe: '8-10 weeks'
            });
        }

        return recommendations;
    }

    trackDevelopmentalProgress(profileId) {
        const profile = this.profiles.get(profileId);
        if (!profile || profile.assessmentHistory.length < 2) {
            return null;
        }

        const progressData = {};
        const sortedAssessments = profile.assessmentHistory.sort((a, b) => 
            moment(a.timestamp) - moment(b.timestamp)
        );

        const frameworks = Object.keys(this.problemSolvingFrameworks);
        frameworks.forEach(framework => {
            const frameworkScores = sortedAssessments.map(assessment => ({
                score: assessment.scores.frameworkScores[framework] || 0,
                timestamp: assessment.timestamp
            }));

            progressData[framework] = this.calculateProgressTrajectory(frameworkScores);
        });

        profile.developmentalTrajectory = progressData;
        profile.updatedAt = moment().toISOString();

        this.emit('progressTracked', { profileId, trajectory: progressData });
        return progressData;
    }

    calculateProgressTrajectory(scoreData) {
        if (scoreData.length < 2) return null;

        const n = scoreData.length;
        let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;

        scoreData.forEach((point, index) => {
            const x = index;
            const y = point.score;
            sumX += x;
            sumY += y;
            sumXY += x * y;
            sumXX += x * x;
        });

        const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
        const intercept = (sumY - slope * sumX) / n;

        let trend;
        if (slope > 3) trend = 'rapid_improvement';
        else if (slope > 1) trend = 'steady_improvement';
        else if (slope > -1) trend = 'stable';
        else if (slope > -3) trend = 'declining';
        else trend = 'concerning_decline';

        return {
            slope,
            intercept,
            trend,
            improvement_rate: slope,
            recent_performance: scoreData[n-1].score,
            initial_performance: scoreData[0].score,
            total_improvement: scoreData[n-1].score - scoreData[0].score
        };
    }

    generateProblemSolvingReport(profileId) {
        const profile = this.profiles.get(profileId);
        if (!profile) return null;

        const latestAssessment = profile.assessmentHistory[profile.assessmentHistory.length - 1];
        const trajectory = profile.developmentalTrajectory;

        return {
            studentId: profile.studentId,
            age: profile.age,
            assessmentDate: latestAssessment?.timestamp,
            overallLevel: this.categorizePerformance(latestAssessment?.scores?.overall || 0),
            frameworkProfiles: this.generateFrameworkProfiles(profile),
            strengthAreas: this.identifyOverallStrengths(profile),
            developmentAreas: this.identifyDevelopmentAreas(profile),
            trajectory: trajectory,
            developmentalAlignment: this.assessOverallDevelopmentalAlignment(profile),
            recommendations: this.generateComprehensiveRecommendations(profile),
            nextAssessmentDate: moment().add(3, 'months').toISOString()
        };
    }

    getAgeStage(age) {
        if (age <= 5) return 'ages_4_5';
        if (age <= 7) return 'ages_6_7';
        if (age <= 10) return 'ages_8_10';
        return 'ages_11_plus';
    }

    identifySimilarProblems(solutions) {
        const grouped = {};
        Object.entries(solutions).forEach(([problemId, solution]) => {
            const type = solution.problemType || 'general';
            if (!grouped[type]) grouped[type] = [];
            grouped[type].push({ problemId, ...solution });
        });
        return grouped;
    }

    checkStrategyConsistency(similarProblems) {
        let consistentCount = 0;
        Object.values(similarProblems).forEach(problemGroup => {
            if (problemGroup.length > 1) {
                const strategies = problemGroup.map(p => p.strategy);
                const uniqueStrategies = [...new Set(strategies)];
                if (uniqueStrategies.length === 1 && uniqueStrategies[0] !== 'trial_and_error') {
                    consistentCount++;
                }
            }
        });
        return consistentCount;
    }

    getFrameworkStrategies(framework, age) {
        const ageStage = this.getAgeStage(age);
        const strategies = this.interventionStrategies.strategy_instruction.age_adaptations[ageStage] || [];
        return strategies;
    }

    getProcessStrategies(process, age) {
        const baseStrategies = this.interventionStrategies.scaffolded_practice.scaffolding_techniques;
        return baseStrategies;
    }
}

module.exports = ProblemSolvingTracker;