const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');

class CreativeGrowthMetrics extends EventEmitter {
    constructor() {
        super();
        this.assessments = new Map();
        this.profiles = new Map();
        this.creativityDomains = this.initializeCreativityDomains();
        this.developmentalMilestones = this.initializeDevelopmentalMilestones();
        this.assessmentBatteries = this.initializeAssessmentBatteries();
        this.interventionStrategies = this.initializeInterventionStrategies();
    }

    initializeCreativityDomains() {
        return {
            artistic_expression: {
                subdomains: {
                    visual_arts: {
                        skills: [
                            'Drawing and sketching',
                            'Painting and color exploration',
                            'Sculpture and 3D creation',
                            'Digital art creation',
                            'Mixed media exploration',
                            'Art appreciation and critique'
                        ],
                        assessments: [
                            'Drawing complexity analysis',
                            'Color usage creativity',
                            'Spatial composition skills',
                            'Artistic storytelling ability',
                            'Innovation in technique'
                        ]
                    },
                    performing_arts: {
                        skills: [
                            'Musical expression and rhythm',
                            'Dance and movement creativity',
                            'Dramatic play and acting',
                            'Storytelling and narration',
                            'Improvisation skills',
                            'Performance confidence'
                        ],
                        assessments: [
                            'Musical creativity tasks',
                            'Movement improvisation',
                            'Dramatic interpretation',
                            'Story creation and telling',
                            'Audience engagement skills'
                        ]
                    },
                    creative_writing: {
                        skills: [
                            'Imaginative story creation',
                            'Poetry and verse writing',
                            'Character development',
                            'Plot construction',
                            'Descriptive language use',
                            'Genre exploration'
                        ],
                        assessments: [
                            'Story originality scoring',
                            'Language creativity metrics',
                            'Narrative structure analysis',
                            'Character depth evaluation',
                            'Emotional expression in writing'
                        ]
                    }
                }
            },
            innovative_thinking: {
                subdomains: {
                    divergent_thinking: {
                        skills: [
                            'Alternative use generation',
                            'Fluency in idea production',
                            'Flexibility in thinking',
                            'Originality of responses',
                            'Elaboration of concepts',
                            'Abstract thinking ability'
                        ],
                        assessments: [
                            'Torrance Tests of Creative Thinking',
                            'Alternative Uses Task',
                            'Circles Task completion',
                            'Remote Associates Test',
                            'Unusual Uses creativity test'
                        ]
                    },
                    convergent_thinking: {
                        skills: [
                            'Solution synthesis',
                            'Idea refinement',
                            'Creative problem resolution',
                            'Innovation implementation',
                            'Design optimization',
                            'Creative constraints handling'
                        ],
                        assessments: [
                            'Creative problem-solving scenarios',
                            'Innovation implementation tasks',
                            'Design challenge completions',
                            'Constraint creativity tests',
                            'Solution effectiveness evaluation'
                        ]
                    },
                    systems_thinking: {
                        skills: [
                            'Pattern recognition',
                            'Connection identification',
                            'Systems analysis',
                            'Holistic perspective',
                            'Interdisciplinary thinking',
                            'Complex problem decomposition'
                        ],
                        assessments: [
                            'Systems mapping exercises',
                            'Pattern completion tasks',
                            'Connection finding challenges',
                            'Holistic problem analysis',
                            'Cross-domain thinking tests'
                        ]
                    }
                }
            },
            design_thinking: {
                subdomains: {
                    human_centered_design: {
                        skills: [
                            'Empathy and user understanding',
                            'Need identification',
                            'User research methods',
                            'Persona development',
                            'Journey mapping',
                            'Accessibility consideration'
                        ],
                        assessments: [
                            'Empathy mapping exercises',
                            'User story creation',
                            'Interview skill evaluation',
                            'Observation accuracy tests',
                            'Need prioritization tasks'
                        ]
                    },
                    prototyping_skills: {
                        skills: [
                            'Rapid prototyping',
                            'Iterative design',
                            'Material exploration',
                            'Low-fidelity mockups',
                            'Testing methodology',
                            'Feedback incorporation'
                        ],
                        assessments: [
                            'Prototype quality evaluation',
                            'Iteration effectiveness',
                            'Material usage creativity',
                            'Testing thoroughness',
                            'Feedback integration ability'
                        ]
                    },
                    design_process: {
                        skills: [
                            'Design thinking methodology',
                            'Ideation facilitation',
                            'Concept development',
                            'Solution evaluation',
                            'Implementation planning',
                            'Reflection and learning'
                        ],
                        assessments: [
                            'Process adherence evaluation',
                            'Ideation session effectiveness',
                            'Concept clarity assessment',
                            'Evaluation criteria development',
                            'Learning reflection quality'
                        ]
                    }
                }
            },
            creative_collaboration: {
                subdomains: {
                    co_creation: {
                        skills: [
                            'Collaborative ideation',
                            'Shared vision development',
                            'Group creative process',
                            'Collective decision making',
                            'Shared ownership',
                            'Creative conflict resolution'
                        ],
                        assessments: [
                            'Group project contributions',
                            'Collaboration effectiveness',
                            'Shared vision alignment',
                            'Conflict resolution skills',
                            'Collective output quality'
                        ]
                    },
                    creative_leadership: {
                        skills: [
                            'Creative vision articulation',
                            'Team inspiration',
                            'Creative risk taking',
                            'Innovation championing',
                            'Creative culture building',
                            'Failure reframing'
                        ],
                        assessments: [
                            'Vision communication clarity',
                            'Team motivation impact',
                            'Risk assessment skills',
                            'Innovation advocacy',
                            'Culture influence measurement'
                        ]
                    },
                    feedback_integration: {
                        skills: [
                            'Constructive feedback giving',
                            'Feedback reception',
                            'Critique analysis',
                            'Improvement integration',
                            'Iterative refinement',
                            'Growth mindset application'
                        ],
                        assessments: [
                            'Feedback quality evaluation',
                            'Reception responsiveness',
                            'Critique utilization',
                            'Improvement implementation',
                            'Growth demonstration'
                        ]
                    }
                }
            },
            technological_creativity: {
                subdomains: {
                    digital_creation: {
                        skills: [
                            'Digital tool mastery',
                            'Technology integration',
                            'Digital storytelling',
                            'Interactive media creation',
                            'Virtual reality exploration',
                            'Augmented reality design'
                        ],
                        assessments: [
                            'Digital portfolio quality',
                            'Tool usage innovation',
                            'Technology integration creativity',
                            'Interactive design effectiveness',
                            'Immersive experience creation'
                        ]
                    },
                    computational_thinking: {
                        skills: [
                            'Algorithm design creativity',
                            'Pattern abstraction',
                            'Decomposition strategies',
                            'Creative coding',
                            'Data visualization',
                            'Automation innovation'
                        ],
                        assessments: [
                            'Algorithm creativity evaluation',
                            'Abstraction quality assessment',
                            'Problem decomposition skills',
                            'Code creativity metrics',
                            'Visualization innovation'
                        ]
                    },
                    maker_skills: {
                        skills: [
                            'Physical computing',
                            'Fabrication techniques',
                            'Maker tool usage',
                            'DIY innovation',
                            'Sustainable making',
                            'Community sharing'
                        ],
                        assessments: [
                            'Making project complexity',
                            'Tool usage creativity',
                            'Innovation in fabrication',
                            'Sustainability consideration',
                            'Community contribution'
                        ]
                    }
                }
            }
        };
    }

    initializeDevelopmentalMilestones() {
        return {
            ages_2_3: {
                artistic_expression: [
                    'Scribbles with intention',
                    'Shows color preferences',
                    'Engages in pretend play',
                    'Moves to music rhythmically',
                    'Creates simple vocal expressions'
                ],
                innovative_thinking: [
                    'Uses objects in unconventional ways',
                    'Shows curiosity about how things work',
                    'Generates multiple solutions to simple problems',
                    'Demonstrates flexibility in play',
                    'Shows persistence in exploration'
                ],
                design_thinking: [
                    'Builds with blocks creatively',
                    'Shows awareness of others needs',
                    'Attempts to fix broken toys',
                    'Experiments with materials',
                    'Shows trial and error learning'
                ],
                creative_collaboration: [
                    'Engages in parallel creative play',
                    'Shares creative materials',
                    'Shows interest in others creations',
                    'Mimics creative behaviors',
                    'Responds to creative prompts'
                ],
                technological_creativity: [
                    'Shows interest in cause and effect',
                    'Explores interactive toys',
                    'Shows pattern recognition',
                    'Demonstrates basic tool use',
                    'Shows interest in moving parts'
                ]
            },
            ages_4_5: {
                artistic_expression: [
                    'Draws recognizable figures',
                    'Uses multiple colors purposefully',
                    'Creates stories with characters',
                    'Sings simple songs',
                    'Engages in dramatic role play'
                ],
                innovative_thinking: [
                    'Generates creative solutions',
                    'Shows originality in responses',
                    'Demonstrates mental flexibility',
                    'Creates elaborate imaginary scenarios',
                    'Shows persistence in creative tasks'
                ],
                design_thinking: [
                    'Plans before building',
                    'Shows empathy for characters',
                    'Tests and modifies creations',
                    'Uses available materials creatively',
                    'Explains design choices'
                ],
                creative_collaboration: [
                    'Participates in group creative activities',
                    'Builds on others ideas',
                    'Takes turns in creative play',
                    'Shares creative leadership',
                    'Gives simple creative feedback'
                ],
                technological_creativity: [
                    'Uses simple digital tools',
                    'Shows understanding of sequences',
                    'Creates with building systems',
                    'Shows interest in how things are made',
                    'Demonstrates basic programming concepts'
                ]
            },
            ages_6_7: {
                artistic_expression: [
                    'Shows personal artistic style',
                    'Creates detailed artwork',
                    'Writes original stories',
                    'Performs for audiences',
                    'Shows art appreciation'
                ],
                innovative_thinking: [
                    'Demonstrates fluent idea generation',
                    'Shows flexible thinking patterns',
                    'Creates original combinations',
                    'Elaborates on basic ideas',
                    'Shows abstract thinking emergence'
                ],
                design_thinking: [
                    'Identifies user needs',
                    'Creates simple prototypes',
                    'Tests and iterates designs',
                    'Considers multiple perspectives',
                    'Reflects on design process'
                ],
                creative_collaboration: [
                    'Leads creative group projects',
                    'Integrates diverse ideas',
                    'Resolves creative conflicts',
                    'Provides constructive feedback',
                    'Builds on collaborative work'
                ],
                technological_creativity: [
                    'Creates digital content',
                    'Uses technology to solve problems',
                    'Shows computational thinking',
                    'Builds interactive projects',
                    'Demonstrates maker skills'
                ]
            },
            ages_8_plus: {
                artistic_expression: [
                    'Develops artistic expertise areas',
                    'Shows sophisticated technique',
                    'Creates complex narratives',
                    'Demonstrates performance mastery',
                    'Critiques artwork thoughtfully'
                ],
                innovative_thinking: [
                    'Shows advanced divergent thinking',
                    'Integrates ideas across domains',
                    'Demonstrates systems thinking',
                    'Shows creative problem-solving mastery',
                    'Exhibits creative confidence'
                ],
                design_thinking: [
                    'Uses complete design process',
                    'Conducts user research',
                    'Creates sophisticated prototypes',
                    'Evaluates design effectiveness',
                    'Shows design thinking mastery'
                ],
                creative_collaboration: [
                    'Facilitates creative processes',
                    'Builds creative communities',
                    'Mentors others creativity',
                    'Manages creative projects',
                    'Demonstrates creative leadership'
                ],
                technological_creativity: [
                    'Creates complex digital projects',
                    'Shows programming creativity',
                    'Builds maker inventions',
                    'Integrates multiple technologies',
                    'Shows innovation in tech use'
                ]
            }
        };
    }

    initializeAssessmentBatteries() {
        return {
            torrance_creative_thinking: {
                description: 'Comprehensive creativity assessment',
                age_range: '5-18',
                domains: ['fluency', 'flexibility', 'originality', 'elaboration'],
                administration_time: '90 minutes',
                scoring_method: 'standardized_percentiles'
            },
            creative_personality_scale: {
                description: 'Creative personality traits assessment',
                age_range: '8-18',
                domains: ['openness', 'risk_taking', 'complexity', 'imagination'],
                administration_time: '30 minutes',
                scoring_method: 'likert_scale'
            },
            artistic_development_portfolio: {
                description: 'Portfolio-based artistic growth assessment',
                age_range: '4-18',
                domains: ['technique', 'creativity', 'expression', 'growth'],
                administration_time: 'ongoing',
                scoring_method: 'rubric_based'
            },
            creative_problem_solving_scenarios: {
                description: 'Real-world creative problem solving',
                age_range: '6-18',
                domains: ['problem_identification', 'solution_generation', 'implementation'],
                administration_time: '60 minutes',
                scoring_method: 'performance_based'
            },
            design_thinking_challenges: {
                description: 'Design process assessment',
                age_range: '7-18',
                domains: ['empathy', 'ideation', 'prototyping', 'testing'],
                administration_time: '120 minutes',
                scoring_method: 'process_evaluation'
            },
            collaborative_creativity_tasks: {
                description: 'Group creativity assessment',
                age_range: '5-18',
                domains: ['collaboration', 'idea_building', 'group_dynamics'],
                administration_time: '45 minutes',
                scoring_method: 'group_performance'
            }
        };
    }

    initializeInterventionStrategies() {
        return {
            artistic_expression: {
                skill_building: [
                    'Structured art instruction',
                    'Multi-media exploration',
                    'Artist study programs',
                    'Creative technique workshops',
                    'Portfolio development support'
                ],
                creativity_enhancement: [
                    'Open-ended art challenges',
                    'Cross-medium experimentation',
                    'Art-based storytelling',
                    'Collaborative art projects',
                    'Art critique and reflection'
                ],
                environmental_modifications: [
                    'Rich material availability',
                    'Inspiration displays',
                    'Flexible workspace design',
                    'Documentation systems',
                    'Exhibition opportunities'
                ]
            },
            innovative_thinking: {
                skill_building: [
                    'Brainstorming technique training',
                    'Lateral thinking exercises',
                    'Creative problem-solving strategies',
                    'Analogical thinking development',
                    'Innovation methodology learning'
                ],
                creativity_enhancement: [
                    'Open-ended challenges',
                    'Cross-domain connection making',
                    'What-if scenario exploration',
                    'Constraint-based creativity',
                    'Failure reframing exercises'
                ],
                environmental_modifications: [
                    'Innovation-rich environments',
                    'Diverse perspective exposure',
                    'Risk-taking encouragement',
                    'Idea documentation systems',
                    'Innovation celebration'
                ]
            },
            design_thinking: {
                skill_building: [
                    'Design process training',
                    'Empathy skill development',
                    'Prototyping workshops',
                    'User research methods',
                    'Testing and iteration training'
                ],
                creativity_enhancement: [
                    'Human-centered design challenges',
                    'Cross-cultural design exploration',
                    'Sustainable design projects',
                    'Community problem solving',
                    'Design impact reflection'
                ],
                environmental_modifications: [
                    'Maker space access',
                    'Material resource availability',
                    'Community connection opportunities',
                    'Real-world problem exposure',
                    'Design showcase platforms'
                ]
            },
            creative_collaboration: {
                skill_building: [
                    'Collaboration skill training',
                    'Leadership development',
                    'Feedback and critique skills',
                    'Conflict resolution methods',
                    'Group facilitation techniques'
                ],
                creativity_enhancement: [
                    'Group creative challenges',
                    'Cross-age collaboration',
                    'Cultural exchange projects',
                    'Community creative initiatives',
                    'Peer mentoring programs'
                ],
                environmental_modifications: [
                    'Collaborative spaces design',
                    'Group work structures',
                    'Peer support systems',
                    'Community partnerships',
                    'Celebration of group achievements'
                ]
            },
            technological_creativity: {
                skill_building: [
                    'Digital tool mastery',
                    'Programming creativity',
                    'Maker skill development',
                    'Technology integration training',
                    'Computational thinking development'
                ],
                creativity_enhancement: [
                    'Tech-for-good projects',
                    'Cross-platform creation',
                    'Innovation competitions',
                    'Technology art fusion',
                    'Future technology exploration'
                ],
                environmental_modifications: [
                    'Technology access provision',
                    'Maker space establishment',
                    'Expert mentorship programs',
                    'Innovation showcases',
                    'Technology ethics discussions'
                ]
            }
        };
    }

    createProfile(studentId, age, interests = []) {
        const profile = {
            id: uuidv4(),
            studentId,
            age,
            interests,
            creativityProfile: this.initializeCreativityProfile(),
            assessmentHistory: [],
            developmentalTrajectory: {},
            interventionPlan: {},
            createdAt: moment().toISOString(),
            updatedAt: moment().toISOString()
        };
        
        this.profiles.set(profile.id, profile);
        this.emit('profileCreated', { profileId: profile.id, studentId });
        
        return profile.id;
    }

    initializeCreativityProfile() {
        const profile = {};
        Object.keys(this.creativityDomains).forEach(domain => {
            profile[domain] = {
                overallScore: 0,
                percentile: 0,
                subdomainScores: {},
                strengthAreas: [],
                growthAreas: [],
                trajectory: 'developing'
            };
        });
        return profile;
    }

    conductAssessment(profileId, assessmentType, assessmentData) {
        const profile = this.profiles.get(profileId);
        if (!profile) {
            throw new Error('Profile not found');
        }

        const assessment = {
            id: uuidv4(),
            type: assessmentType,
            data: assessmentData,
            scores: this.calculateCreativityScores(assessmentType, assessmentData, profile.age),
            percentiles: {},
            interpretations: {},
            recommendations: [],
            timestamp: moment().toISOString()
        };

        assessment.percentiles = this.calculatePercentiles(assessment.scores, profile.age);
        assessment.interpretations = this.generateInterpretations(assessment.scores, assessment.percentiles, profile.age);
        assessment.recommendations = this.generateRecommendations(assessment.scores, assessment.interpretations, profile);

        profile.assessmentHistory.push(assessment);
        profile.creativityProfile = this.updateCreativityProfile(profile.creativityProfile, assessment);
        profile.updatedAt = moment().toISOString();

        this.assessments.set(assessment.id, assessment);
        this.emit('assessmentCompleted', { profileId, assessmentId: assessment.id });

        return assessment.id;
    }

    calculateCreativityScores(assessmentType, data, age) {
        const scores = {};
        
        switch (assessmentType) {
            case 'torrance_creative_thinking':
                scores.fluency = this.calculateFluencyScore(data.responses);
                scores.flexibility = this.calculateFlexibilityScore(data.responses);
                scores.originality = this.calculateOriginalityScore(data.responses, age);
                scores.elaboration = this.calculateElaborationScore(data.responses);
                break;
                
            case 'artistic_development_portfolio':
                scores.technical_skill = this.assessTechnicalSkill(data.portfolio, age);
                scores.creativity = this.assessArtisticCreativity(data.portfolio);
                scores.expression = this.assessArtisticExpression(data.portfolio);
                scores.growth = this.assessArtisticGrowth(data.portfolio);
                break;
                
            case 'creative_problem_solving_scenarios':
                scores.problem_identification = this.assessProblemIdentification(data.scenarios);
                scores.solution_generation = this.assessSolutionGeneration(data.scenarios);
                scores.implementation_planning = this.assessImplementationPlanning(data.scenarios);
                scores.solution_effectiveness = this.assessSolutionEffectiveness(data.scenarios);
                break;
                
            case 'design_thinking_challenges':
                scores.empathy = this.assessEmpathySkills(data.process);
                scores.ideation = this.assessIdeationSkills(data.process);
                scores.prototyping = this.assessPrototypingSkills(data.process);
                scores.testing = this.assessTestingSkills(data.process);
                break;
                
            case 'collaborative_creativity_tasks':
                scores.collaboration_quality = this.assessCollaborationQuality(data.group_work);
                scores.idea_building = this.assessIdeaBuilding(data.group_work);
                scores.leadership = this.assessCreativeLeadership(data.group_work);
                scores.group_dynamics = this.assessGroupDynamics(data.group_work);
                break;
                
            default:
                scores.overall = this.calculateGeneralCreativityScore(data, age);
        }
        
        return scores;
    }

    calculateFluencyScore(responses) {
        return responses.length * 2;
    }

    calculateFlexibilityScore(responses) {
        const categories = new Set(responses.map(r => r.category));
        return categories.size * 3;
    }

    calculateOriginalityScore(responses, age) {
        const ageNorms = this.getOriginalityNorms(age);
        let originalityScore = 0;
        
        responses.forEach(response => {
            const frequency = ageNorms[response.text] || 0;
            if (frequency < 0.02) originalityScore += 3;
            else if (frequency < 0.05) originalityScore += 2;
            else if (frequency < 0.1) originalityScore += 1;
        });
        
        return originalityScore;
    }

    calculateElaborationScore(responses) {
        const totalDetails = responses.reduce((sum, r) => sum + (r.details?.length || 0), 0);
        return Math.min(totalDetails * 2, 100);
    }

    assessTechnicalSkill(portfolio, age) {
        const ageExpectations = this.getTechnicalSkillExpectations(age);
        let score = 0;
        
        portfolio.forEach(piece => {
            score += this.evaluateTechnicalElements(piece, ageExpectations);
        });
        
        return Math.min(score / portfolio.length, 100);
    }

    assessArtisticCreativity(portfolio) {
        let creativityScore = 0;
        
        portfolio.forEach(piece => {
            creativityScore += this.evaluateOriginality(piece);
            creativityScore += this.evaluateConceptualThinking(piece);
            creativityScore += this.evaluateRiskTaking(piece);
        });
        
        return Math.min(creativityScore / portfolio.length, 100);
    }

    assessArtisticExpression(portfolio) {
        let expressionScore = 0;
        
        portfolio.forEach(piece => {
            expressionScore += this.evaluateEmotionalContent(piece);
            expressionScore += this.evaluatePersonalVoice(piece);
            expressionScore += this.evaluateCommunicationEffectiveness(piece);
        });
        
        return Math.min(expressionScore / portfolio.length, 100);
    }

    assessArtisticGrowth(portfolio) {
        if (portfolio.length < 2) return 0;
        
        const chronologicalPieces = portfolio.sort((a, b) => 
            moment(a.createdDate) - moment(b.createdDate)
        );
        
        let growthScore = 0;
        for (let i = 1; i < chronologicalPieces.length; i++) {
            growthScore += this.compareArtisticProgression(
                chronologicalPieces[i-1], 
                chronologicalPieces[i]
            );
        }
        
        return Math.min(growthScore / (chronologicalPieces.length - 1), 100);
    }

    calculatePercentiles(scores, age) {
        const percentiles = {};
        const norms = this.getCreativityNorms(age);
        
        Object.keys(scores).forEach(scoreType => {
            const score = scores[scoreType];
            const norm = norms[scoreType];
            
            if (norm) {
                percentiles[scoreType] = this.scoreToPercentile(score, norm.mean, norm.std);
            }
        });
        
        return percentiles;
    }

    scoreToPercentile(score, mean, std) {
        const zScore = (score - mean) / std;
        return Math.round(this.normalCDF(zScore) * 100);
    }

    normalCDF(x) {
        return 0.5 * (1 + this.erf(x / Math.sqrt(2)));
    }

    erf(x) {
        const a1 = 0.254829592;
        const a2 = -0.284496736;
        const a3 = 1.421413741;
        const a4 = -1.453152027;
        const a5 = 1.061405429;
        const p = 0.3275911;
        
        const sign = x >= 0 ? 1 : -1;
        x = Math.abs(x);
        
        const t = 1.0 / (1.0 + p * x);
        const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
        
        return sign * y;
    }

    generateInterpretations(scores, percentiles, age) {
        const interpretations = {};
        const milestones = this.developmentalMilestones[this.getAgeCategory(age)];
        
        Object.keys(scores).forEach(scoreType => {
            const percentile = percentiles[scoreType];
            let level, description;
            
            if (percentile >= 90) {
                level = 'exceptional';
                description = 'Demonstrates exceptional creative abilities well above age expectations';
            } else if (percentile >= 75) {
                level = 'above_average';
                description = 'Shows above-average creative development';
            } else if (percentile >= 25) {
                level = 'average';
                description = 'Demonstrates typical creative development for age';
            } else if (percentile >= 10) {
                level = 'below_average';
                description = 'Shows creative development below age expectations';
            } else {
                level = 'concerning';
                description = 'May benefit from additional creative development support';
            }
            
            interpretations[scoreType] = {
                level,
                description,
                developmental_context: this.getDevelopmentalContext(scoreType, age, milestones)
            };
        });
        
        return interpretations;
    }

    generateRecommendations(scores, interpretations, profile) {
        const recommendations = [];
        const age = profile.age;
        const interests = profile.interests || [];
        
        Object.keys(interpretations).forEach(area => {
            const interpretation = interpretations[area];
            const domain = this.mapScoreToCreativityDomain(area);
            
            if (interpretation.level === 'exceptional') {
                recommendations.push({
                    type: 'enrichment',
                    area: domain,
                    priority: 'high',
                    strategies: this.getEnrichmentStrategies(domain, age, interests),
                    description: `Provide advanced challenges in ${domain} to maintain engagement`
                });
            } else if (interpretation.level === 'below_average' || interpretation.level === 'concerning') {
                recommendations.push({
                    type: 'intervention',
                    area: domain,
                    priority: interpretation.level === 'concerning' ? 'urgent' : 'medium',
                    strategies: this.getInterventionStrategies(domain, age, interests),
                    description: `Provide targeted support to develop ${domain} skills`
                });
            } else if (interpretation.level === 'above_average') {
                recommendations.push({
                    type: 'enhancement',
                    area: domain,
                    priority: 'medium',
                    strategies: this.getEnhancementStrategies(domain, age, interests),
                    description: `Build on existing strengths in ${domain}`
                });
            }
        });
        
        return recommendations;
    }

    trackProgressOverTime(profileId) {
        const profile = this.profiles.get(profileId);
        if (!profile || profile.assessmentHistory.length < 2) {
            return null;
        }
        
        const trajectory = {};
        const assessments = profile.assessmentHistory.sort((a, b) => 
            moment(a.timestamp) - moment(b.timestamp)
        );
        
        const domains = Object.keys(this.creativityDomains);
        domains.forEach(domain => {
            const domainScores = assessments.map(assessment => {
                const domainScore = this.extractDomainScore(assessment, domain);
                return {
                    score: domainScore,
                    timestamp: assessment.timestamp
                };
            }).filter(item => item.score !== null);
            
            if (domainScores.length >= 2) {
                trajectory[domain] = this.calculateTrajectory(domainScores);
            }
        });
        
        profile.developmentalTrajectory = trajectory;
        profile.updatedAt = moment().toISOString();
        
        this.emit('trajectoryUpdated', { profileId });
        return trajectory;
    }

    calculateTrajectory(dataPoints) {
        if (dataPoints.length < 2) return null;
        
        const n = dataPoints.length;
        let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
        
        dataPoints.forEach((point, index) => {
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
        if (slope > 2) trend = 'rapid_improvement';
        else if (slope > 0.5) trend = 'steady_improvement';
        else if (slope > -0.5) trend = 'stable';
        else if (slope > -2) trend = 'declining';
        else trend = 'rapid_decline';
        
        return {
            slope,
            intercept,
            trend,
            r_squared: this.calculateRSquared(dataPoints, slope, intercept),
            recent_change: dataPoints[n-1].score - dataPoints[n-2].score,
            overall_change: dataPoints[n-1].score - dataPoints[0].score
        };
    }

    calculateRSquared(dataPoints, slope, intercept) {
        const meanY = dataPoints.reduce((sum, point) => sum + point.score, 0) / dataPoints.length;
        let ssRes = 0, ssTot = 0;
        
        dataPoints.forEach((point, index) => {
            const predicted = slope * index + intercept;
            ssRes += Math.pow(point.score - predicted, 2);
            ssTot += Math.pow(point.score - meanY, 2);
        });
        
        return 1 - (ssRes / ssTot);
    }

    identifyCreativeStrengths(profileId) {
        const profile = this.profiles.get(profileId);
        if (!profile) return null;
        
        const strengths = [];
        const creativityProfile = profile.creativityProfile;
        
        Object.keys(creativityProfile).forEach(domain => {
            const domainData = creativityProfile[domain];
            if (domainData.percentile >= 75) {
                strengths.push({
                    domain,
                    percentile: domainData.percentile,
                    level: domainData.percentile >= 90 ? 'exceptional' : 'strong',
                    specific_areas: domainData.strengthAreas,
                    recommendations: this.getStrengthDevelopmentRecommendations(domain, profile.age)
                });
            }
        });
        
        return strengths.sort((a, b) => b.percentile - a.percentile);
    }

    generateCreativityReport(profileId) {
        const profile = this.profiles.get(profileId);
        if (!profile) return null;
        
        const latestAssessment = profile.assessmentHistory[profile.assessmentHistory.length - 1];
        const trajectory = profile.developmentalTrajectory;
        const strengths = this.identifyCreativeStrengths(profileId);
        
        return {
            studentId: profile.studentId,
            assessmentDate: latestAssessment?.timestamp,
            creativityProfile: profile.creativityProfile,
            keyFindings: this.generateKeyFindings(profile),
            strengths,
            areasForGrowth: this.identifyGrowthAreas(profile),
            trajectory,
            developmentalMilestones: this.checkMilestoneProgress(profile),
            recommendations: this.generateComprehensiveRecommendations(profile),
            nextSteps: this.generateNextSteps(profile)
        };
    }

    getAgeCategory(age) {
        if (age <= 3) return 'ages_2_3';
        if (age <= 5) return 'ages_4_5';
        if (age <= 7) return 'ages_6_7';
        return 'ages_8_plus';
    }

    getCreativityNorms(age) {
        return {
            fluency: { mean: 10 + age * 2, std: 3 },
            flexibility: { mean: 8 + age * 1.5, std: 2.5 },
            originality: { mean: 12 + age * 1.8, std: 4 },
            elaboration: { mean: 15 + age * 2.2, std: 5 },
            technical_skill: { mean: 20 + age * 8, std: 12 },
            creativity: { mean: 45 + age * 3, std: 15 },
            expression: { mean: 40 + age * 3.5, std: 12 }
        };
    }

    getOriginalityNorms(age) {
        const baseNorms = {
            'car': 0.15, 'house': 0.12, 'tree': 0.18, 'flower': 0.10,
            'rocket': 0.05, 'robot': 0.03, 'unicorn': 0.02
        };
        
        Object.keys(baseNorms).forEach(key => {
            baseNorms[key] *= Math.max(0.5, 1 - (age - 6) * 0.1);
        });
        
        return baseNorms;
    }

    extractDomainScore(assessment, domain) {
        const domainMappings = {
            'artistic_expression': ['technical_skill', 'creativity', 'expression'],
            'innovative_thinking': ['fluency', 'flexibility', 'originality'],
            'design_thinking': ['empathy', 'ideation', 'prototyping'],
            'creative_collaboration': ['collaboration_quality', 'idea_building'],
            'technological_creativity': ['overall']
        };
        
        const relevantScores = domainMappings[domain] || ['overall'];
        const scores = relevantScores.map(scoreType => assessment.scores[scoreType]).filter(s => s != null);
        
        return scores.length > 0 ? scores.reduce((sum, score) => sum + score, 0) / scores.length : null;
    }

    mapScoreToCreativityDomain(scoreType) {
        const mappings = {
            'fluency': 'innovative_thinking',
            'flexibility': 'innovative_thinking',
            'originality': 'innovative_thinking',
            'elaboration': 'innovative_thinking',
            'technical_skill': 'artistic_expression',
            'creativity': 'artistic_expression',
            'expression': 'artistic_expression',
            'empathy': 'design_thinking',
            'ideation': 'design_thinking',
            'prototyping': 'design_thinking',
            'collaboration_quality': 'creative_collaboration',
            'idea_building': 'creative_collaboration'
        };
        
        return mappings[scoreType] || 'innovative_thinking';
    }

    generateKeyFindings(profile) {
        const findings = [];
        const creativityProfile = profile.creativityProfile;
        
        const overallCreativity = Object.values(creativityProfile)
            .reduce((sum, domain) => sum + domain.percentile, 0) / Object.keys(creativityProfile).length;
        
        if (overallCreativity >= 75) {
            findings.push('Student demonstrates strong overall creative abilities');
        } else if (overallCreativity <= 25) {
            findings.push('Student may benefit from additional creative development support');
        }
        
        const strongDomains = Object.keys(creativityProfile)
            .filter(domain => creativityProfile[domain].percentile >= 75);
        
        if (strongDomains.length > 0) {
            findings.push(`Particular strengths in: ${strongDomains.join(', ')}`);
        }
        
        return findings;
    }

    identifyGrowthAreas(profile) {
        const growthAreas = [];
        const creativityProfile = profile.creativityProfile;
        
        Object.keys(creativityProfile).forEach(domain => {
            if (creativityProfile[domain].percentile < 50) {
                growthAreas.push({
                    domain,
                    percentile: creativityProfile[domain].percentile,
                    specificAreas: creativityProfile[domain].growthAreas,
                    priority: creativityProfile[domain].percentile < 25 ? 'high' : 'medium'
                });
            }
        });
        
        return growthAreas.sort((a, b) => a.percentile - b.percentile);
    }

    checkMilestoneProgress(profile) {
        const ageCategory = this.getAgeCategory(profile.age);
        const milestones = this.developmentalMilestones[ageCategory];
        const progress = {};
        
        Object.keys(milestones).forEach(domain => {
            const domainPercentile = profile.creativityProfile[domain]?.percentile || 0;
            progress[domain] = {
                expected: milestones[domain],
                current_level: this.interpretPercentileForMilestones(domainPercentile),
                on_track: domainPercentile >= 25
            };
        });
        
        return progress;
    }

    interpretPercentileForMilestones(percentile) {
        if (percentile >= 75) return 'exceeding';
        if (percentile >= 50) return 'meeting';
        if (percentile >= 25) return 'approaching';
        return 'below';
    }

    generateComprehensiveRecommendations(profile) {
        const recommendations = [];
        const creativityProfile = profile.creativityProfile;
        const age = profile.age;
        const interests = profile.interests || [];
        
        Object.keys(creativityProfile).forEach(domain => {
            const domainData = creativityProfile[domain];
            const strategies = this.interventionStrategies[domain];
            
            if (strategies) {
                let recommendationType;
                if (domainData.percentile >= 75) {
                    recommendationType = 'enrichment';
                } else if (domainData.percentile < 25) {
                    recommendationType = 'intervention';
                } else {
                    recommendationType = 'enhancement';
                }
                
                recommendations.push({
                    domain,
                    type: recommendationType,
                    strategies: strategies[this.mapRecommendationType(recommendationType)],
                    priority: this.determinePriority(domainData.percentile, domain, interests),
                    timeline: '3-6 months',
                    success_metrics: this.defineSuccessMetrics(domain, recommendationType)
                });
            }
        });
        
        return recommendations;
    }

    mapRecommendationType(type) {
        const mappings = {
            'enrichment': 'creativity_enhancement',
            'intervention': 'skill_building',
            'enhancement': 'creativity_enhancement'
        };
        return mappings[type] || 'skill_building';
    }

    determinePriority(percentile, domain, interests) {
        if (percentile < 10) return 'urgent';
        if (percentile < 25) return 'high';
        if (interests.includes(domain)) return 'high';
        if (percentile > 75) return 'medium';
        return 'low';
    }

    defineSuccessMetrics(domain, type) {
        const baseMetrics = [
            'Increased engagement in creative activities',
            'Improved creative confidence',
            'Enhanced skill demonstration'
        ];
        
        const domainSpecificMetrics = {
            'artistic_expression': ['Portfolio quality improvement', 'Artistic technique advancement'],
            'innovative_thinking': ['Increased idea fluency', 'Enhanced solution originality'],
            'design_thinking': ['Better user empathy', 'Improved prototype quality'],
            'creative_collaboration': ['Enhanced group contribution', 'Improved peer feedback'],
            'technological_creativity': ['Digital creation skills', 'Technology integration ability']
        };
        
        return [...baseMetrics, ...(domainSpecificMetrics[domain] || [])];
    }

    generateNextSteps(profile) {
        return [
            'Schedule follow-up assessment in 3-6 months',
            'Implement priority recommendations',
            'Monitor progress through portfolio documentation',
            'Engage family in creative activities',
            'Connect with community creative resources',
            'Consider specialized programs for identified strengths'
        ];
    }
}

module.exports = CreativeGrowthMetrics;