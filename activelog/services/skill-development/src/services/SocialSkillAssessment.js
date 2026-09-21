const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');

class SocialSkillAssessment extends EventEmitter {
    constructor() {
        super();
        this.studentProfiles = new Map();
        this.socialSkillDomains = this.initializeSocialSkillDomains();
        this.developmentalMilestones = this.initializeDevelopmentalMilestones();
        this.assessmentTools = this.initializeAssessmentTools();
        this.interventionPrograms = this.initializeInterventionPrograms();
        this.socialContexts = this.initializeSocialContexts();
        this.culturalConsiderations = this.initializeCulturalConsiderations();
    }

    initializeSocialSkillDomains() {
        return {
            communication_skills: {
                id: 'communication_skills',
                name: 'Communication Skills',
                description: 'Verbal and non-verbal communication abilities',
                subdomains: {
                    verbal_communication: {
                        name: 'Verbal Communication',
                        skills: [
                            'Initiating conversations',
                            'Maintaining conversations',
                            'Taking turns in conversation',
                            'Asking appropriate questions',
                            'Responding to questions',
                            'Expressing needs and wants',
                            'Sharing experiences and ideas',
                            'Using appropriate volume and tone'
                        ],
                        assessment_methods: ['conversation_samples', 'structured_observations', 'peer_interactions']
                    },
                    nonverbal_communication: {
                        name: 'Non-verbal Communication',
                        skills: [
                            'Making appropriate eye contact',
                            'Reading facial expressions',
                            'Using appropriate gestures',
                            'Understanding body language',
                            'Maintaining appropriate personal space',
                            'Recognizing social cues',
                            'Using appropriate posture',
                            'Matching non-verbal to verbal messages'
                        ],
                        assessment_methods: ['video_analysis', 'social_cue_recognition_tasks', 'interaction_coding']
                    },
                    pragmatic_language: {
                        name: 'Pragmatic Language',
                        skills: [
                            'Using context-appropriate language',
                            'Understanding humor and sarcasm',
                            'Following conversation rules',
                            'Staying on topic',
                            'Requesting clarification',
                            'Providing appropriate detail',
                            'Using politeness markers',
                            'Code-switching for different audiences'
                        ],
                        assessment_methods: ['pragmatic_language_assessments', 'discourse_analysis', 'context_adaptation_tasks']
                    }
                }
            },
            social_interaction: {
                id: 'social_interaction',
                name: 'Social Interaction Skills',
                description: 'Ability to engage successfully with peers and adults',
                subdomains: {
                    peer_relationships: {
                        name: 'Peer Relationships',
                        skills: [
                            'Making friends',
                            'Maintaining friendships',
                            'Joining group activities',
                            'Sharing and taking turns',
                            'Showing empathy to peers',
                            'Resolving conflicts with peers',
                            'Cooperating in group tasks',
                            'Including others in activities'
                        ],
                        assessment_methods: ['peer_sociometrics', 'playground_observations', 'friendship_interviews']
                    },
                    adult_relationships: {
                        name: 'Adult Relationships',
                        skills: [
                            'Showing respect to adults',
                            'Following adult directions',
                            'Asking adults for help appropriately',
                            'Greeting adults appropriately',
                            'Responding to adult feedback',
                            'Showing appropriate affection',
                            'Understanding authority relationships',
                            'Communicating with unfamiliar adults'
                        ],
                        assessment_methods: ['teacher_ratings', 'adult_interaction_observations', 'structured_interviews']
                    },
                    group_dynamics: {
                        name: 'Group Dynamics',
                        skills: [
                            'Understanding group roles',
                            'Contributing to group discussions',
                            'Following group rules',
                            'Compromising in group decisions',
                            'Supporting group goals',
                            'Managing group conflicts',
                            'Leading group activities',
                            'Being a good group member'
                        ],
                        assessment_methods: ['group_work_observations', 'leadership_assessments', 'team_building_activities']
                    }
                }
            },
            emotional_regulation: {
                id: 'emotional_regulation',
                name: 'Emotional Regulation',
                description: 'Managing emotions in social contexts',
                subdomains: {
                    emotion_recognition: {
                        name: 'Emotion Recognition',
                        skills: [
                            'Identifying own emotions',
                            'Recognizing others\' emotions',
                            'Understanding emotion triggers',
                            'Reading emotional expressions',
                            'Understanding emotional intensity',
                            'Recognizing mixed emotions',
                            'Understanding emotional contexts',
                            'Predicting emotional responses'
                        ],
                        assessment_methods: ['emotion_identification_tasks', 'facial_expression_recognition', 'emotion_scenarios']
                    },
                    emotion_expression: {
                        name: 'Emotion Expression',
                        skills: [
                            'Expressing emotions appropriately',
                            'Using emotion words accurately',
                            'Matching expression to situation',
                            'Controlling emotional intensity',
                            'Expressing emotions safely',
                            'Seeking emotional support',
                            'Showing emotional restraint',
                            'Using emotions for communication'
                        ],
                        assessment_methods: ['emotional_expression_tasks', 'situation_response_assessments', 'emotional_vocabulary_tests']
                    },
                    self_regulation: {
                        name: 'Self-Regulation',
                        skills: [
                            'Managing anger appropriately',
                            'Calming down when upset',
                            'Waiting patiently',
                            'Controlling impulses',
                            'Adapting to changes',
                            'Managing frustration',
                            'Self-soothing strategies',
                            'Seeking help when overwhelmed'
                        ],
                        assessment_methods: ['self_regulation_tasks', 'behavioral_observations', 'coping_strategy_assessments']
                    }
                }
            },
            social_cognition: {
                id: 'social_cognition',
                name: 'Social Cognition',
                description: 'Understanding social situations and relationships',
                subdomains: {
                    perspective_taking: {
                        name: 'Perspective Taking',
                        skills: [
                            'Understanding others\' viewpoints',
                            'Considering multiple perspectives',
                            'Predicting others\' thoughts',
                            'Understanding others\' feelings',
                            'Recognizing different knowledge states',
                            'Understanding false beliefs',
                            'Considering others\' intentions',
                            'Understanding others\' motivations'
                        ],
                        assessment_methods: ['theory_of_mind_tasks', 'perspective_taking_scenarios', 'false_belief_tasks']
                    },
                    social_problem_solving: {
                        name: 'Social Problem Solving',
                        skills: [
                            'Identifying social problems',
                            'Generating multiple solutions',
                            'Evaluating solution consequences',
                            'Choosing appropriate solutions',
                            'Implementing solutions effectively',
                            'Monitoring solution outcomes',
                            'Adjusting strategies as needed',
                            'Learning from social mistakes'
                        ],
                        assessment_methods: ['social_problem_solving_scenarios', 'solution_generation_tasks', 'decision_making_assessments']
                    },
                    social_knowledge: {
                        name: 'Social Knowledge',
                        skills: [
                            'Understanding social rules',
                            'Knowing social conventions',
                            'Understanding role expectations',
                            'Recognizing social hierarchies',
                            'Understanding cultural norms',
                            'Knowing appropriate behaviors',
                            'Understanding social consequences',
                            'Recognizing social contexts'
                        ],
                        assessment_methods: ['social_knowledge_interviews', 'social_rules_assessments', 'cultural_competence_evaluations']
                    }
                }
            },
            behavioral_regulation: {
                id: 'behavioral_regulation',
                name: 'Behavioral Regulation',
                description: 'Managing behavior in social situations',
                subdomains: {
                    impulse_control: {
                        name: 'Impulse Control',
                        skills: [
                            'Thinking before acting',
                            'Resisting immediate impulses',
                            'Waiting for appropriate times',
                            'Controlling physical impulses',
                            'Managing verbal impulses',
                            'Delaying gratification',
                            'Following multi-step instructions',
                            'Stopping inappropriate behaviors'
                        ],
                        assessment_methods: ['impulse_control_tasks', 'delay_of_gratification_tests', 'behavioral_inhibition_measures']
                    },
                    attention_regulation: {
                        name: 'Attention Regulation',
                        skills: [
                            'Focusing on social cues',
                            'Attending to conversation partners',
                            'Monitoring social situations',
                            'Switching attention appropriately',
                            'Maintaining social attention',
                            'Filtering social distractions',
                            'Noticing social changes',
                            'Attending to multiple social inputs'
                        ],
                        assessment_methods: ['social_attention_tasks', 'distraction_resistance_tests', 'attention_switching_assessments']
                    },
                    behavioral_flexibility: {
                        name: 'Behavioral Flexibility',
                        skills: [
                            'Adapting to new social situations',
                            'Changing behavior when needed',
                            'Trying new social strategies',
                            'Adjusting to others\' styles',
                            'Recovering from social mistakes',
                            'Learning new social skills',
                            'Generalizing across contexts',
                            'Being open to feedback'
                        ],
                        assessment_methods: ['behavioral_adaptation_tasks', 'flexibility_scenarios', 'change_adaptation_assessments']
                    }
                }
            }
        };
    }

    initializeDevelopmentalMilestones() {
        return {
            'ages_2_3': {
                communication_skills: [
                    'Uses 2-3 word phrases to communicate needs',
                    'Makes eye contact during interactions',
                    'Responds to simple questions',
                    'Shows objects to share interest',
                    'Imitates simple gestures'
                ],
                social_interaction: [
                    'Shows interest in other children',
                    'Engages in parallel play',
                    'Shows affection to familiar people',
                    'Seeks comfort when distressed',
                    'Follows simple social routines'
                ],
                emotional_regulation: [
                    'Shows basic emotions clearly',
                    'Seeks comfort when upset',
                    'Shows empathy to crying children',
                    'Expresses frustration appropriately',
                    'Calms with adult support'
                ]
            },
            'ages_3_4': {
                communication_skills: [
                    'Uses longer sentences (4-5 words)',
                    'Asks many questions',
                    'Follows 2-step instructions',
                    'Tells simple stories',
                    'Uses polite words (please, thank you)'
                ],
                social_interaction: [
                    'Plays with other children briefly',
                    'Takes turns with assistance',
                    'Shows preference for certain friends',
                    'Includes others in play sometimes',
                    'Follows simple group rules'
                ],
                emotional_regulation: [
                    'Names basic emotions',
                    'Shows empathy to others',
                    'Uses words for feelings sometimes',
                    'Calms down with strategies',
                    'Seeks adult help when needed'
                ]
            },
            'ages_4_5': {
                communication_skills: [
                    'Maintains conversations for several turns',
                    'Asks for clarification when confused',
                    'Adjusts communication for different listeners',
                    'Understands most social cues',
                    'Uses appropriate volume and tone'
                ],
                social_interaction: [
                    'Engages in cooperative play',
                    'Shows concern for friends',
                    'Resolves conflicts with help',
                    'Follows group rules consistently',
                    'Shows leadership in familiar activities'
                ],
                emotional_regulation: [
                    'Identifies emotions in self and others',
                    'Uses coping strategies independently',
                    'Expresses emotions appropriately',
                    'Shows emotional self-control',
                    'Comforts others who are upset'
                ]
            },
            'ages_5_6': {
                communication_skills: [
                    'Engages in complex conversations',
                    'Understands humor and jokes',
                    'Follows conversation rules',
                    'Communicates effectively with adults',
                    'Uses advanced vocabulary appropriately'
                ],
                social_interaction: [
                    'Forms close friendships',
                    'Cooperates well in groups',
                    'Shows good sportsmanship',
                    'Includes others naturally',
                    'Resolves conflicts independently'
                ],
                emotional_regulation: [
                    'Manages emotions in challenging situations',
                    'Shows empathy and compassion',
                    'Uses multiple coping strategies',
                    'Helps others regulate emotions',
                    'Shows emotional maturity'
                ]
            },
            'ages_6_8': {
                communication_skills: [
                    'Maintains topic across conversations',
                    'Uses appropriate language for context',
                    'Understands implied meanings',
                    'Gives clear explanations',
                    'Adapts communication style for audience'
                ],
                social_interaction: [
                    'Maintains stable friendships',
                    'Works effectively in teams',
                    'Shows good citizenship',
                    'Demonstrates fairness',
                    'Takes on leadership roles'
                ],
                emotional_regulation: [
                    'Shows sophisticated emotional understanding',
                    'Manages complex emotions',
                    'Provides emotional support to others',
                    'Shows emotional resilience',
                    'Demonstrates emotional intelligence'
                ]
            }
        };
    }

    initializeAssessmentTools() {
        return {
            ssis: {
                name: 'Social Skills Improvement System',
                age_range: '3-18 years',
                informants: ['teachers', 'parents', 'students'],
                domains: ['Communication', 'Cooperation', 'Assertion', 'Responsibility', 'Empathy', 'Engagement', 'Self-Control'],
                administration_time: '15-25 minutes per form',
                scoring: 'Standard scores and percentile ranks'
            },
            pkbs2: {
                name: 'Preschool and Kindergarten Behavior Scales - Second Edition',
                age_range: '3-6 years',
                informants: ['teachers', 'parents'],
                domains: ['Social Cooperation', 'Social Independence', 'Social Interaction'],
                administration_time: '10-15 minutes',
                scoring: 'Standard scores and percentile ranks'
            },
            basc3: {
                name: 'Behavior Assessment System for Children - Third Edition',
                age_range: '2-21 years',
                informants: ['teachers', 'parents', 'students'],
                domains: ['Adaptability', 'Social Skills', 'Leadership', 'Functional Communication'],
                administration_time: '10-20 minutes per form',
                scoring: 'T-scores and percentile ranks'
            },
            walker_mccconnell: {
                name: 'Walker-McConnell Scale of Social Competence',
                age_range: '5-18 years',
                informants: ['teachers'],
                domains: ['Teacher-Preferred Social Behavior', 'Peer-Preferred Social Behavior', 'School Adjustment'],
                administration_time: '10-15 minutes',
                scoring: 'Percentile ranks and standard scores'
            },
            sps: {
                name: 'Social Performance Survey Schedule',
                age_range: '4-17 years',
                informants: ['teachers', 'parents'],
                domains: ['Positive Social Behaviors', 'Problematic Social Behaviors'],
                administration_time: '10-20 minutes',
                scoring: 'Raw scores and normative comparisons'
            },
            observation_protocols: {
                name: 'Systematic Observation Protocols',
                contexts: ['classroom', 'playground', 'cafeteria', 'structured_activities'],
                measures: ['social_initiations', 'responses_to_peers', 'cooperative_behaviors', 'conflict_resolution'],
                duration: '15-30 minutes per observation',
                coding: 'Frequency counts and duration measures'
            }
        };
    }

    initializeInterventionPrograms() {
        return {
            communication_interventions: {
                verbal_communication: [
                    'Conversation skills training',
                    'Social scripts practice',
                    'Turn-taking games',
                    'Question-asking activities',
                    'Story-telling practice'
                ],
                nonverbal_communication: [
                    'Eye contact exercises',
                    'Body language recognition',
                    'Personal space training',
                    'Facial expression practice',
                    'Gesture recognition activities'
                ],
                pragmatic_language: [
                    'Context-appropriate language practice',
                    'Social language groups',
                    'Humor understanding activities',
                    'Conversation repair strategies',
                    'Code-switching practice'
                ]
            },
            social_interaction_interventions: {
                peer_relationships: [
                    'Friendship skills training',
                    'Peer mediation programs',
                    'Social circles activities',
                    'Conflict resolution training',
                    'Empathy building exercises'
                ],
                group_dynamics: [
                    'Cooperative learning activities',
                    'Team building exercises',
                    'Leadership development programs',
                    'Group problem-solving tasks',
                    'Role-playing activities'
                ]
            },
            emotional_regulation_interventions: [
                'Emotion identification activities',
                'Feeling thermometer exercises',
                'Mindfulness training',
                'Self-regulation strategies',
                'Coping skills training',
                'Emotional vocabulary building',
                'Stress management techniques',
                'Relaxation training'
            ],
            behavioral_regulation_interventions: [
                'Impulse control training',
                'Self-monitoring programs',
                'Behavioral flexibility exercises',
                'Attention regulation activities',
                'Social problem-solving training',
                'Self-instruction training',
                'Behavioral rehearsal',
                'Social skills generalization'
            ],
            comprehensive_programs: {
                strong_kids: {
                    name: 'Strong Kids Social-Emotional Learning Curriculum',
                    age_groups: ['PreK-K', 'Grades 3-5', 'Grades 6-8'],
                    components: ['Emotional knowledge', 'Emotional management', 'Social awareness', 'Relationship skills'],
                    delivery: 'Classroom-based lessons'
                },
                second_step: {
                    name: 'Second Step Social-Emotional Learning',
                    age_groups: ['PreK-Grade 8'],
                    components: ['Skills for learning', 'Empathy', 'Emotion management', 'Problem solving'],
                    delivery: 'Structured lessons with practice activities'
                },
                paths: {
                    name: 'Promoting Alternative Thinking Strategies',
                    age_groups: ['PreK-Grade 6'],
                    components: ['Self-control', 'Emotional understanding', 'Interpersonal problem solving', 'Friendship skills'],
                    delivery: 'Daily lessons and generalization activities'
                }
            }
        };
    }

    initializeSocialContexts() {
        return {
            school_contexts: {
                classroom: {
                    typical_interactions: ['teacher_student', 'peer_peer', 'group_work', 'class_discussions'],
                    social_demands: ['following_instructions', 'participating_appropriately', 'helping_others', 'asking_for_help'],
                    common_challenges: ['attention_difficulties', 'peer_conflicts', 'authority_issues', 'participation_problems']
                },
                playground: {
                    typical_interactions: ['unstructured_play', 'game_participation', 'conflict_resolution', 'inclusion_exclusion'],
                    social_demands: ['joining_games', 'following_rules', 'sharing_equipment', 'resolving_conflicts'],
                    common_challenges: ['social_rejection', 'aggressive_behavior', 'withdrawal', 'rule_violations']
                },
                cafeteria: {
                    typical_interactions: ['peer_conversations', 'sharing_food', 'table_manners', 'social_groupings'],
                    social_demands: ['appropriate_eating_behavior', 'conversation_skills', 'inclusion_behaviors'],
                    common_challenges: ['social_isolation', 'inappropriate_behavior', 'peer_rejection']
                },
                hallways: {
                    typical_interactions: ['brief_greetings', 'walking_with_peers', 'respectful_behavior'],
                    social_demands: ['appropriate_movement', 'brief_social_exchanges', 'following_procedures'],
                    common_challenges: ['disruptive_behavior', 'peer_conflicts', 'inappropriate_interactions']
                }
            },
            home_contexts: {
                family_interactions: {
                    typical_interactions: ['parent_child', 'sibling_relationships', 'extended_family'],
                    social_demands: ['following_family_rules', 'showing_respect', 'contributing_to_household'],
                    assessment_considerations: ['family_dynamics', 'cultural_values', 'parenting_styles']
                },
                neighborhood: {
                    typical_interactions: ['peer_play', 'neighbor_interactions', 'community_activities'],
                    social_demands: ['appropriate_outdoor_behavior', 'respecting_property', 'safety_awareness'],
                    assessment_considerations: ['community_resources', 'safety_concerns', 'cultural_factors']
                }
            },
            community_contexts: {
                recreational_activities: {
                    typical_interactions: ['team_sports', 'clubs', 'community_events', 'structured_activities'],
                    social_demands: ['following_activity_rules', 'cooperating_with_peers', 'respecting_leaders'],
                    assessment_opportunities: ['naturalistic_observations', 'coach_teacher_reports', 'peer_interactions']
                }
            }
        };
    }

    initializeCulturalConsiderations() {
        return {
            communication_styles: {
                high_context: ['Indirect communication', 'Nonverbal emphasis', 'Implicit understanding', 'Relationship focus'],
                low_context: ['Direct communication', 'Explicit messages', 'Individual focus', 'Task orientation'],
                considerations: ['Family communication patterns', 'Cultural communication norms', 'Language proficiency', 'Code-switching abilities']
            },
            social_values: {
                individualistic: ['Personal achievement', 'Independence', 'Self-expression', 'Individual rights'],
                collectivistic: ['Group harmony', 'Family loyalty', 'Cooperation', 'Respect for authority'],
                considerations: ['Family values', 'Community expectations', 'Role definitions', 'Conflict resolution styles']
            },
            behavioral_expectations: {
                authority_relationships: ['Respect for elders', 'Teacher-student dynamics', 'Parent-child interactions', 'Formal vs informal address'],
                peer_relationships: ['Gender role expectations', 'Age-based hierarchies', 'Friendship definitions', 'Social boundaries'],
                emotional_expression: ['Acceptable emotions', 'Expression contexts', 'Gender differences', 'Cultural taboos']
            },
            assessment_adaptations: [
                'Use culturally relevant examples',
                'Consider language proficiency',
                'Adapt social scenarios',
                'Include cultural informants',
                'Use multiple assessment methods',
                'Consider cultural bias in measures',
                'Interpret results in cultural context',
                'Involve cultural mediators'
            ]
        };
    }

    createSocialProfile(studentId, studentInfo) {
        const profile = {
            id: studentId,
            personalInfo: {
                name: studentInfo.name,
                dateOfBirth: studentInfo.dateOfBirth,
                age: this.calculateAge(studentInfo.dateOfBirth),
                grade: studentInfo.grade,
                culturalBackground: studentInfo.culturalBackground || {},
                languageBackground: studentInfo.languageBackground || [],
                familyStructure: studentInfo.familyStructure || {}
            },
            socialSkillProfile: this.initializeSocialSkillProfile(),
            assessmentHistory: [],
            contextualPerformance: this.initializeContextualPerformance(),
            interventionHistory: [],
            developmentalMilestones: this.setDevelopmentalMilestones(this.calculateAge(studentInfo.dateOfBirth)),
            strengthsNeeds: {
                strengths: [],
                needs: [],
                emerging_skills: []
            },
            socialGoals: [],
            progressTracking: new Map(),
            culturalConsiderations: this.assessCulturalFactors(studentInfo),
            createdAt: new Date(),
            updatedAt: new Date()
        };

        this.studentProfiles.set(studentId, profile);
        
        this.emit('socialProfileCreated', {
            studentId,
            profile: this.getPublicSocialProfile(profile)
        });

        return profile;
    }

    calculateAge(dateOfBirth) {
        return moment().diff(moment(dateOfBirth), 'years', true);
    }

    initializeSocialSkillProfile() {
        const profile = {};
        
        Object.entries(this.socialSkillDomains).forEach(([domainId, domain]) => {
            profile[domainId] = {};
            Object.entries(domain.subdomains).forEach(([subdomainId, subdomain]) => {
                profile[domainId][subdomainId] = {
                    overallRating: null,
                    skillRatings: new Map(),
                    percentileRank: null,
                    descriptiveLevel: 'not_assessed',
                    assessmentHistory: [],
                    contextualVariation: new Map(),
                    lastAssessed: null
                };
            });
        });

        return profile;
    }

    initializeContextualPerformance() {
        const contexts = {};
        
        Object.entries(this.socialContexts).forEach(([contextType, contextInfo]) => {
            contexts[contextType] = {};
            Object.entries(contextInfo).forEach(([specificContext, details]) => {
                contexts[contextType][specificContext] = {
                    performanceLevel: null,
                    specificChallenges: [],
                    strengths: [],
                    supportNeeds: [],
                    observationHistory: []
                };
            });
        });

        return contexts;
    }

    setDevelopmentalMilestones(age) {
        let ageGroup;
        if (age < 3) ageGroup = 'ages_2_3';
        else if (age < 4) ageGroup = 'ages_3_4';
        else if (age < 5) ageGroup = 'ages_4_5';
        else if (age < 6) ageGroup = 'ages_5_6';
        else ageGroup = 'ages_6_8';

        const milestones = this.developmentalMilestones[ageGroup] || {};
        const milestoneMap = new Map();

        Object.entries(milestones).forEach(([domain, skills]) => {
            skills.forEach(skill => {
                milestoneMap.set(skill, {
                    domain,
                    achieved: false,
                    dateAchieved: null,
                    evidenceSource: null,
                    confidence: null
                });
            });
        });

        return milestoneMap;
    }

    assessCulturalFactors(studentInfo) {
        const culturalInfo = studentInfo.culturalBackground || {};
        const languageInfo = studentInfo.languageBackground || [];
        
        return {
            primaryLanguage: languageInfo[0] || 'english',
            languageProficiency: culturalInfo.languageProficiency || 'native',
            culturalOrientation: culturalInfo.culturalOrientation || 'mixed',
            communicationStyle: culturalInfo.communicationStyle || 'direct',
            familyValues: culturalInfo.familyValues || [],
            assessmentConsiderations: this.generateCulturalAssessmentConsiderations(culturalInfo),
            interventionAdaptations: this.generateCulturalInterventionAdaptations(culturalInfo)
        };
    }

    generateCulturalAssessmentConsiderations(culturalInfo) {
        const considerations = [];
        
        if (culturalInfo.primaryLanguage !== 'english') {
            considerations.push('Consider language proficiency in assessment interpretation');
            considerations.push('Use culturally adapted assessment tools when available');
        }
        
        if (culturalInfo.communicationStyle === 'indirect') {
            considerations.push('Expect less direct verbal communication');
            considerations.push('Pay attention to nonverbal communication patterns');
        }
        
        if (culturalInfo.culturalOrientation === 'collectivistic') {
            considerations.push('Consider group-oriented behaviors as strengths');
            considerations.push('Assess cooperation and harmony-seeking behaviors');
        }
        
        return considerations;
    }

    generateCulturalInterventionAdaptations(culturalInfo) {
        const adaptations = [];
        
        adaptations.push('Involve family in intervention planning');
        adaptations.push('Consider cultural values in goal setting');
        adaptations.push('Use culturally relevant examples and activities');
        adaptations.push('Respect cultural communication patterns');
        
        return adaptations;
    }

    conductSocialAssessment(studentId, assessmentData) {
        const profile = this.studentProfiles.get(studentId);
        if (!profile) {
            throw new Error('Student profile not found');
        }

        const assessment = {
            id: uuidv4(),
            date: new Date(),
            assessor: assessmentData.assessor,
            tool: assessmentData.tool,
            informants: assessmentData.informants,
            contexts: assessmentData.contexts,
            results: assessmentData.results,
            observations: assessmentData.observations,
            culturalConsiderations: assessmentData.culturalConsiderations,
            recommendations: assessmentData.recommendations
        };

        profile.assessmentHistory.push(assessment);
        
        // Update social skill profile
        this.updateSocialSkillProfile(profile, assessment);
        
        // Update contextual performance
        this.updateContextualPerformance(profile, assessment);
        
        // Analyze social patterns
        const socialAnalysis = this.analyzeSocialPatterns(profile);
        
        // Update strengths and needs
        this.updateSocialStrengthsNeeds(profile, socialAnalysis);
        
        // Update milestone progress
        this.updateMilestoneProgress(profile, assessment);
        
        profile.updatedAt = new Date();

        this.emit('socialAssessmentCompleted', {
            studentId,
            assessmentId: assessment.id,
            results: assessment.results,
            socialAnalysis
        });

        return {
            assessment,
            socialAnalysis,
            updatedProfile: profile.socialSkillProfile
        };
    }

    updateSocialSkillProfile(profile, assessment) {
        Object.entries(assessment.results).forEach(([domainId, domainResults]) => {
            if (profile.socialSkillProfile[domainId]) {
                Object.entries(domainResults).forEach(([subdomainId, result]) => {
                    if (profile.socialSkillProfile[domainId][subdomainId]) {
                        const subdomain = profile.socialSkillProfile[domainId][subdomainId];
                        
                        // Add to assessment history
                        subdomain.assessmentHistory.push({
                            date: assessment.date,
                            tool: assessment.tool,
                            overallRating: result.overallRating,
                            percentileRank: result.percentileRank,
                            descriptiveLevel: result.descriptiveLevel
                        });

                        // Update current values
                        subdomain.overallRating = result.overallRating;
                        subdomain.percentileRank = result.percentileRank;
                        subdomain.descriptiveLevel = result.descriptiveLevel;
                        subdomain.lastAssessed = assessment.date;
                        
                        // Update skill ratings if available
                        if (result.skillRatings) {
                            Object.entries(result.skillRatings).forEach(([skill, rating]) => {
                                subdomain.skillRatings.set(skill, rating);
                            });
                        }
                        
                        // Update contextual variation if available
                        if (result.contextualRatings) {
                            Object.entries(result.contextualRatings).forEach(([context, rating]) => {
                                subdomain.contextualVariation.set(context, rating);
                            });
                        }
                    }
                });
            }
        });
    }

    updateContextualPerformance(profile, assessment) {
        if (assessment.contexts) {
            assessment.contexts.forEach(context => {
                const [contextType, specificContext] = context.split('.');
                if (profile.contextualPerformance[contextType] && 
                    profile.contextualPerformance[contextType][specificContext]) {
                    
                    const contextData = profile.contextualPerformance[contextType][specificContext];
                    contextData.observationHistory.push({
                        date: assessment.date,
                        assessor: assessment.assessor,
                        observations: assessment.observations[context] || [],
                        challenges: assessment.results.contextualChallenges?.[context] || [],
                        strengths: assessment.results.contextualStrengths?.[context] || []
                    });
                    
                    // Update current performance
                    if (assessment.results.contextualPerformance?.[context]) {
                        contextData.performanceLevel = assessment.results.contextualPerformance[context].level;
                        contextData.specificChallenges = assessment.results.contextualPerformance[context].challenges;
                        contextData.strengths = assessment.results.contextualPerformance[context].strengths;
                    }
                }
            });
        }
    }

    analyzeSocialPatterns(profile) {
        const analysis = {
            overallProfile: this.generateOverallSocialProfile(profile),
            domainStrengths: [],
            domainNeeds: [],
            contextualPatterns: this.analyzeContextualPatterns(profile),
            developmentalAlignment: this.analyzeDevelopmentalAlignment(profile),
            socialRiskFactors: [],
            protectiveFactors: [],
            interventionPriorities: []
        };

        // Analyze each domain
        Object.entries(profile.socialSkillProfile).forEach(([domainId, domain]) => {
            const domainAnalysis = this.analyzeDomain(domainId, domain);
            
            if (domainAnalysis.averagePercentile >= 75) {
                analysis.domainStrengths.push({
                    domain: domainId,
                    averagePercentile: domainAnalysis.averagePercentile,
                    description: this.socialSkillDomains[domainId].name,
                    implications: this.getDomainStrengthImplications(domainId)
                });
            } else if (domainAnalysis.averagePercentile <= 25) {
                analysis.domainNeeds.push({
                    domain: domainId,
                    averagePercentile: domainAnalysis.averagePercentile,
                    description: this.socialSkillDomains[domainId].name,
                    implications: this.getDomainNeedImplications(domainId)
                });
                analysis.interventionPriorities.push(domainId);
            }
        });

        // Identify risk and protective factors
        analysis.socialRiskFactors = this.identifyRiskFactors(profile, analysis);
        analysis.protectiveFactors = this.identifyProtectiveFactors(profile, analysis);

        return analysis;
    }

    generateOverallSocialProfile(profile) {
        const allPercentiles = [];
        let assessedDomains = 0;

        Object.entries(profile.socialSkillProfile).forEach(([domainId, domain]) => {
            const domainPercentiles = Object.values(domain)
                .filter(subdomain => subdomain.percentileRank !== null)
                .map(subdomain => subdomain.percentileRank);
            
            if (domainPercentiles.length > 0) {
                const avgPercentile = domainPercentiles.reduce((sum, p) => sum + p, 0) / domainPercentiles.length;
                allPercentiles.push(avgPercentile);
                assessedDomains++;
            }
        });

        if (allPercentiles.length === 0) {
            return {
                overallLevel: 'not_assessed',
                profilePattern: 'unknown',
                averagePercentile: null,
                variability: null
            };
        }

        const avgPercentile = allPercentiles.reduce((sum, p) => sum + p, 0) / allPercentiles.length;
        const variance = allPercentiles.reduce((sum, p) => sum + Math.pow(p - avgPercentile, 2), 0) / allPercentiles.length;
        const standardDeviation = Math.sqrt(variance);

        let overallLevel = 'average';
        if (avgPercentile >= 75) overallLevel = 'above_average';
        else if (avgPercentile <= 25) overallLevel = 'below_average';

        let profilePattern = 'consistent';
        if (standardDeviation >= 20) profilePattern = 'variable';
        else if (Math.max(...allPercentiles) - Math.min(...allPercentiles) >= 30) profilePattern = 'scattered';

        return {
            overallLevel,
            profilePattern,
            averagePercentile: Math.round(avgPercentile),
            variability: Math.round(standardDeviation),
            assessedDomains
        };
    }

    analyzeDomain(domainId, domain) {
        const subdomainPercentiles = Object.values(domain)
            .filter(subdomain => subdomain.percentileRank !== null)
            .map(subdomain => subdomain.percentileRank);

        if (subdomainPercentiles.length === 0) {
            return {
                averagePercentile: null,
                consistency: null,
                trend: 'no_data'
            };
        }

        const avgPercentile = subdomainPercentiles.reduce((sum, p) => sum + p, 0) / subdomainPercentiles.length;
        const consistency = this.calculateConsistency(subdomainPercentiles);

        // Analyze trend if there are multiple assessments
        let trend = 'stable';
        Object.values(domain).forEach(subdomain => {
            if (subdomain.assessmentHistory.length >= 2) {
                const recent = subdomain.assessmentHistory.slice(-2);
                const change = recent[1].percentileRank - recent[0].percentileRank;
                if (Math.abs(change) > 10) {
                    trend = change > 0 ? 'improving' : 'declining';
                }
            }
        });

        return {
            averagePercentile: Math.round(avgPercentile),
            consistency,
            trend
        };
    }

    calculateConsistency(percentiles) {
        if (percentiles.length < 2) return 100;
        
        const mean = percentiles.reduce((sum, p) => sum + p, 0) / percentiles.length;
        const variance = percentiles.reduce((sum, p) => sum + Math.pow(p - mean, 2), 0) / percentiles.length;
        const standardDeviation = Math.sqrt(variance);
        
        // Convert to consistency score (higher = more consistent)
        return Math.max(0, 100 - standardDeviation);
    }

    analyzeContextualPatterns(profile) {
        const patterns = {
            bestContexts: [],
            challengingContexts: [],
            contextualVariability: 'low'
        };

        const contextPerformance = new Map();

        // Collect performance data across contexts
        Object.entries(profile.contextualPerformance).forEach(([contextType, contexts]) => {
            Object.entries(contexts).forEach(([contextName, data]) => {
                if (data.performanceLevel !== null) {
                    contextPerformance.set(`${contextType}.${contextName}`, data.performanceLevel);
                }
            });
        });

        if (contextPerformance.size === 0) {
            return patterns;
        }

        const performances = Array.from(contextPerformance.values());
        const avgPerformance = performances.reduce((sum, p) => sum + p, 0) / performances.length;
        const maxPerformance = Math.max(...performances);
        const minPerformance = Math.min(...performances);

        // Identify best and challenging contexts
        contextPerformance.forEach((performance, context) => {
            if (performance >= avgPerformance + 10) {
                patterns.bestContexts.push({ context, performance });
            } else if (performance <= avgPerformance - 10) {
                patterns.challengingContexts.push({ context, performance });
            }
        });

        // Determine variability
        if (maxPerformance - minPerformance > 30) {
            patterns.contextualVariability = 'high';
        } else if (maxPerformance - minPerformance > 15) {
            patterns.contextualVariability = 'moderate';
        }

        return patterns;
    }

    analyzeDevelopmentalAlignment(profile) {
        const milestones = Array.from(profile.developmentalMilestones.entries());
        const achieved = milestones.filter(([_, milestone]) => milestone.achieved).length;
        const total = milestones.length;
        
        const alignment = {
            achievementRate: total > 0 ? (achieved / total) * 100 : 0,
            expectedForAge: total > 0 ? 75 : 0, // Expected 75% achievement
            developmentalStatus: 'on_track',
            delayedMilestones: [],
            advancedMilestones: []
        };

        if (alignment.achievementRate < 50) {
            alignment.developmentalStatus = 'delayed';
        } else if (alignment.achievementRate > 90) {
            alignment.developmentalStatus = 'advanced';
        }

        // Identify specific delayed milestones
        milestones.filter(([_, milestone]) => !milestone.achieved)
            .forEach(([skill, milestone]) => {
                alignment.delayedMilestones.push({
                    skill,
                    domain: milestone.domain,
                    expectedAge: this.getExpectedAgeForSkill(skill)
                });
            });

        return alignment;
    }

    getExpectedAgeForSkill(skill) {
        // This would be implemented based on developmental literature
        // For now, return a placeholder
        return 'age_appropriate';
    }

    getDomainStrengthImplications(domainId) {
        const implications = {
            communication_skills: 'Strong communication abilities support academic and social success',
            social_interaction: 'Good social interaction skills facilitate positive relationships',
            emotional_regulation: 'Strong emotional regulation supports overall well-being and learning',
            social_cognition: 'Good social understanding facilitates successful navigation of social situations',
            behavioral_regulation: 'Strong behavioral control supports classroom and social success'
        };
        return implications[domainId] || 'Strength in this social skill area';
    }

    getDomainNeedImplications(domainId) {
        const implications = {
            communication_skills: 'Communication challenges may impact academic and social participation',
            social_interaction: 'Social interaction difficulties may affect peer relationships and inclusion',
            emotional_regulation: 'Emotional regulation challenges may impact behavior and learning',
            social_cognition: 'Social understanding difficulties may lead to social misunderstandings',
            behavioral_regulation: 'Behavioral regulation challenges may impact classroom and social success'
        };
        return implications[domainId] || 'Need for support in this social skill area';
    }

    identifyRiskFactors(profile, analysis) {
        const riskFactors = [];

        // Low overall social skills
        if (analysis.overallProfile.averagePercentile <= 15) {
            riskFactors.push({
                type: 'severe_social_deficits',
                description: 'Significantly below average social skills across domains',
                impact: 'high',
                recommendations: ['Intensive social skills intervention', 'Comprehensive assessment', 'Multi-disciplinary support']
            });
        }

        // Multiple domain needs
        if (analysis.domainNeeds.length >= 3) {
            riskFactors.push({
                type: 'pervasive_social_challenges',
                description: 'Challenges across multiple social skill domains',
                impact: 'high',
                recommendations: ['Comprehensive intervention program', 'Environmental modifications', 'Family support']
            });
        }

        // Contextual challenges
        if (analysis.contextualPatterns.challengingContexts.length > analysis.contextualPatterns.bestContexts.length) {
            riskFactors.push({
                type: 'contextual_difficulties',
                description: 'Challenges in multiple social contexts',
                impact: 'moderate',
                recommendations: ['Context-specific interventions', 'Environmental supports', 'Generalization training']
            });
        }

        // Developmental delays
        if (analysis.developmentalAlignment.achievementRate < 50) {
            riskFactors.push({
                type: 'developmental_delays',
                description: 'Below expected developmental milestones',
                impact: 'high',
                recommendations: ['Early intervention', 'Developmental monitoring', 'Family education']
            });
        }

        return riskFactors;
    }

    identifyProtectiveFactors(profile, analysis) {
        const protectiveFactors = [];

        // Domain strengths
        analysis.domainStrengths.forEach(strength => {
            protectiveFactors.push({
                type: 'social_skill_strength',
                description: `Strength in ${strength.description}`,
                domain: strength.domain,
                implications: strength.implications
            });
        });

        // Contextual strengths
        if (analysis.contextualPatterns.bestContexts.length > 0) {
            protectiveFactors.push({
                type: 'contextual_strengths',
                description: 'Performs well in some social contexts',
                contexts: analysis.contextualPatterns.bestContexts,
                implications: 'Can use successful contexts as models for intervention'
            });
        }

        // Cultural resources
        if (profile.culturalConsiderations.familyValues.includes('cooperation') ||
            profile.culturalConsiderations.familyValues.includes('respect')) {
            protectiveFactors.push({
                type: 'cultural_values',
                description: 'Cultural values support positive social development',
                implications: 'Family values can be leveraged in intervention'
            });
        }

        return protectiveFactors;
    }

    updateSocialStrengthsNeeds(profile, analysis) {
        profile.strengthsNeeds = {
            strengths: analysis.domainStrengths.map(s => ({
                domain: s.domain,
                description: s.description,
                percentile: s.averagePercentile,
                implications: s.implications,
                contexts: this.getStrengthContexts(profile, s.domain)
            })),
            needs: analysis.domainNeeds.map(n => ({
                domain: n.domain,
                description: n.description,
                percentile: n.averagePercentile,
                implications: n.implications,
                priority: n.averagePercentile <= 15 ? 'high' : 'moderate',
                contexts: this.getNeedContexts(profile, n.domain)
            })),
            emerging_skills: this.identifyEmergingSkills(profile)
        };
    }

    getStrengthContexts(profile, domain) {
        // Identify contexts where this domain strength is most evident
        const strengthContexts = [];
        
        Object.entries(profile.contextualPerformance).forEach(([contextType, contexts]) => {
            Object.entries(contexts).forEach(([contextName, data]) => {
                if (data.strengths.some(strength => strength.includes(domain))) {
                    strengthContexts.push(`${contextType}.${contextName}`);
                }
            });
        });
        
        return strengthContexts;
    }

    getNeedContexts(profile, domain) {
        // Identify contexts where this domain need is most evident
        const needContexts = [];
        
        Object.entries(profile.contextualPerformance).forEach(([contextType, contexts]) => {
            Object.entries(contexts).forEach(([contextName, data]) => {
                if (data.specificChallenges.some(challenge => challenge.includes(domain))) {
                    needContexts.push(`${contextType}.${contextName}`);
                }
            });
        });
        
        return needContexts;
    }

    identifyEmergingSkills(profile) {
        const emergingSkills = [];
        const age = profile.personalInfo.age;
        
        // Check milestones that are partially achieved or just above age level
        Array.from(profile.developmentalMilestones.entries()).forEach(([skill, milestone]) => {
            if (!milestone.achieved && milestone.confidence && milestone.confidence > 0.5) {
                emergingSkills.push({
                    skill,
                    domain: milestone.domain,
                    confidence: milestone.confidence,
                    supportNeeded: this.getSkillSupport(skill, milestone.domain)
                });
            }
        });
        
        return emergingSkills.slice(0, 5); // Top 5 emerging skills
    }

    getSkillSupport(skill, domain) {
        // Return recommended support strategies for emerging skills
        const supports = {
            communication_skills: ['Practice opportunities', 'Modeling', 'Social scripts'],
            social_interaction: ['Peer interaction opportunities', 'Guided practice', 'Social coaching'],
            emotional_regulation: ['Emotion coaching', 'Coping strategy practice', 'Mindfulness activities'],
            social_cognition: ['Perspective-taking activities', 'Social stories', 'Problem-solving practice'],
            behavioral_regulation: ['Self-monitoring strategies', 'Environmental supports', 'Positive reinforcement']
        };
        
        return supports[domain] || ['General skill practice', 'Positive reinforcement', 'Modeling'];
    }

    updateMilestoneProgress(profile, assessment) {
        // Update milestone achievements based on assessment results
        if (assessment.results.milestoneAchievements) {
            assessment.results.milestoneAchievements.forEach(achievement => {
                const milestone = profile.developmentalMilestones.get(achievement.skill);
                if (milestone) {
                    milestone.achieved = true;
                    milestone.dateAchieved = assessment.date;
                    milestone.evidenceSource = assessment.tool;
                    milestone.confidence = achievement.confidence || 1.0;
                }
            });
        }
    }

    setSocialGoals(studentId, goals) {
        const profile = this.studentProfiles.get(studentId);
        if (!profile) {
            throw new Error('Student profile not found');
        }

        const processedGoals = goals.map(goal => ({
            id: uuidv4(),
            ...goal,
            createdAt: new Date(),
            targetDate: new Date(goal.targetDate),
            progress: 0,
            status: 'active',
            measurements: goal.measurements || [],
            contexts: goal.contexts || [],
            supportStrategies: goal.supportStrategies || []
        }));

        profile.socialGoals.push(...processedGoals);
        profile.updatedAt = new Date();

        this.emit('socialGoalsSet', {
            studentId,
            goals: processedGoals
        });

        return processedGoals;
    }

    trackSocialProgress(studentId, progressData) {
        const profile = this.studentProfiles.get(studentId);
        if (!profile) {
            throw new Error('Student profile not found');
        }

        const progressEntry = {
            date: new Date(),
            domain: progressData.domain,
            subdomain: progressData.subdomain,
            skill: progressData.skill,
            context: progressData.context,
            measurement: progressData.measurement,
            value: progressData.value,
            observer: progressData.observer,
            notes: progressData.notes
        };

        // Add to progress tracking
        const trackingKey = `${progressData.domain}_${progressData.subdomain}`;
        if (!profile.progressTracking.has(trackingKey)) {
            profile.progressTracking.set(trackingKey, []);
        }
        profile.progressTracking.get(trackingKey).push(progressEntry);

        // Analyze progress trend
        const progressTrend = this.analyzeSocialProgressTrend(
            profile.progressTracking.get(trackingKey)
        );

        profile.updatedAt = new Date();

        this.emit('socialProgressTracked', {
            studentId,
            progressEntry,
            progressTrend
        });

        return { progressEntry, progressTrend };
    }

    analyzeSocialProgressTrend(progressData) {
        if (progressData.length < 2) {
            return { trend: 'insufficient_data', slope: 0, consistency: 0 };
        }

        // Calculate linear trend
        const values = progressData.map((entry, index) => ({ x: index, y: entry.value }));
        const n = values.length;
        const sumX = values.reduce((sum, point) => sum + point.x, 0);
        const sumY = values.reduce((sum, point) => sum + point.y, 0);
        const sumXY = values.reduce((sum, point) => sum + point.x * point.y, 0);
        const sumX2 = values.reduce((sum, point) => sum + point.x * point.x, 0);

        const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        
        let trend = 'stable';
        if (slope > 0.3) trend = 'improving';
        else if (slope < -0.3) trend = 'declining';

        // Calculate consistency
        const yMean = sumY / n;
        const totalVariation = values.reduce((sum, point) => sum + Math.pow(point.y - yMean, 2), 0);
        const residualVariation = values.reduce((sum, point, index) => {
            const predicted = (slope * index) + (sumY - slope * sumX) / n;
            return sum + Math.pow(point.y - predicted, 2);
        }, 0);
        
        const consistency = totalVariation > 0 ? 1 - (residualVariation / totalVariation) : 0;

        return {
            trend,
            slope: Math.round(slope * 100) / 100,
            consistency: Math.round(consistency * 100) / 100,
            dataPoints: progressData.length,
            timeSpan: moment().diff(moment(progressData[0].date), 'days'),
            latestValue: progressData[progressData.length - 1].value
        };
    }

    generateSocialSkillsReport(studentId, reportType = 'comprehensive') {
        const profile = this.studentProfiles.get(studentId);
        if (!profile) {
            throw new Error('Student profile not found');
        }

        const report = {
            studentInfo: profile.personalInfo,
            socialSkillProfile: profile.socialSkillProfile,
            assessmentSummary: this.summarizeSocialAssessments(profile),
            strengthsNeeds: profile.strengthsNeeds,
            contextualPerformance: this.summarizeContextualPerformance(profile),
            developmentalProgress: this.summarizeDevelopmentalProgress(profile),
            culturalConsiderations: profile.culturalConsiderations,
            interventionRecommendations: this.generateSocialInterventionRecommendations(profile),
            progressSummary: this.summarizeSocialProgress(profile),
            goalStatus: this.summarizeGoalStatus(profile),
            nextSteps: this.generateSocialNextSteps(profile),
            generatedAt: new Date(),
            reportType
        };

        this.emit('socialSkillsReportGenerated', {
            studentId,
            reportType,
            report
        });

        return report;
    }

    summarizeSocialAssessments(profile) {
        const assessments = profile.assessmentHistory;
        if (assessments.length === 0) {
            return { totalAssessments: 0, message: 'No social skills assessments completed' };
        }

        const latest = assessments[assessments.length - 1];
        const tools = [...new Set(assessments.map(a => a.tool))];
        const informants = [...new Set(assessments.flatMap(a => a.informants))];
        
        return {
            totalAssessments: assessments.length,
            latestAssessment: {
                date: latest.date,
                tool: latest.tool,
                assessor: latest.assessor
            },
            toolsUsed: tools,
            informants: informants,
            assessmentSpan: assessments.length > 1 ? 
                moment().diff(moment(assessments[0].date), 'months') : 0
        };
    }

    summarizeContextualPerformance(profile) {
        const summary = {
            bestPerformingContexts: [],
            challengingContexts: [],
            contextualConsistency: 'consistent'
        };

        const contextScores = [];

        Object.entries(profile.contextualPerformance).forEach(([contextType, contexts]) => {
            Object.entries(contexts).forEach(([contextName, data]) => {
                if (data.performanceLevel !== null) {
                    const fullContextName = `${contextType}.${contextName}`;
                    contextScores.push({ context: fullContextName, score: data.performanceLevel });
                    
                    if (data.performanceLevel >= 75) {
                        summary.bestPerformingContexts.push({
                            context: fullContextName,
                            score: data.performanceLevel,
                            strengths: data.strengths
                        });
                    } else if (data.performanceLevel <= 25) {
                        summary.challengingContexts.push({
                            context: fullContextName,
                            score: data.performanceLevel,
                            challenges: data.specificChallenges
                        });
                    }
                }
            });
        });

        // Determine consistency
        if (contextScores.length > 1) {
            const scores = contextScores.map(c => c.score);
            const range = Math.max(...scores) - Math.min(...scores);
            if (range > 40) summary.contextualConsistency = 'variable';
            else if (range > 20) summary.contextualConsistency = 'somewhat_variable';
        }

        return summary;
    }

    summarizeDevelopmentalProgress(profile) {
        const milestones = Array.from(profile.developmentalMilestones.entries());
        const achieved = milestones.filter(([_, milestone]) => milestone.achieved).length;
        const total = milestones.length;
        
        const recentAchievements = milestones
            .filter(([_, milestone]) => 
                milestone.achieved && 
                milestone.dateAchieved &&
                moment(milestone.dateAchieved).isAfter(moment().subtract(3, 'months'))
            )
            .map(([skill, milestone]) => ({
                skill,
                domain: milestone.domain,
                dateAchieved: milestone.dateAchieved
            }));

        return {
            achievementRate: total > 0 ? Math.round((achieved / total) * 100) : 0,
            totalMilestones: total,
            achievedMilestones: achieved,
            recentAchievements,
            developmentalStatus: this.getDevelopmentalStatus(achieved, total)
        };
    }

    getDevelopmentalStatus(achieved, total) {
        const rate = total > 0 ? (achieved / total) * 100 : 0;
        if (rate >= 80) return 'on_track';
        if (rate >= 60) return 'some_concerns';
        return 'significant_concerns';
    }

    generateSocialInterventionRecommendations(profile) {
        const recommendations = [];
        
        // Based on domain needs
        profile.strengthsNeeds.needs.forEach(need => {
            const domainInterventions = this.interventionPrograms[need.domain + '_interventions'];
            if (domainInterventions) {
                recommendations.push({
                    domain: need.domain,
                    priority: need.priority,
                    type: 'domain_specific',
                    interventions: Array.isArray(domainInterventions) ? 
                        domainInterventions : Object.values(domainInterventions).flat(),
                    rationale: `Address ${need.description} (${need.percentile}th percentile)`
                });
            }
        });

        // Based on contextual challenges
        const contextualPerformance = this.summarizeContextualPerformance(profile);
        contextualPerformance.challengingContexts.forEach(context => {
            recommendations.push({
                domain: 'contextual',
                priority: 'medium',
                type: 'context_specific',
                interventions: [`Targeted support for ${context.context}`, 'Environmental modifications', 'Context-specific skill practice'],
                rationale: `Address challenges in ${context.context}`
            });
        });

        // Cultural adaptations
        if (profile.culturalConsiderations.interventionAdaptations.length > 0) {
            recommendations.push({
                domain: 'cultural',
                priority: 'high',
                type: 'culturally_responsive',
                interventions: profile.culturalConsiderations.interventionAdaptations,
                rationale: 'Ensure culturally responsive intervention approach'
            });
        }

        return recommendations.sort((a, b) => {
            const priorityOrder = { high: 3, medium: 2, low: 1 };
            return priorityOrder[b.priority] - priorityOrder[a.priority];
        });
    }

    summarizeSocialProgress(profile) {
        const progressEntries = Array.from(profile.progressTracking.values()).flat();
        
        if (progressEntries.length === 0) {
            return { message: 'No progress data available' };
        }

        const recentProgress = progressEntries.filter(entry => 
            moment().diff(moment(entry.date), 'days') <= 30
        );

        const domains = [...new Set(progressEntries.map(entry => entry.domain))];
        const contexts = [...new Set(progressEntries.map(entry => entry.context))];

        return {
            totalDataPoints: progressEntries.length,
            recentDataPoints: recentProgress.length,
            domainsTracked: domains.length,
            contextsTracked: contexts.length,
            trackingSpan: progressEntries.length > 0 ? 
                moment().diff(moment(progressEntries[0].date), 'days') : 0,
            lastUpdate: progressEntries.length > 0 ? 
                progressEntries[progressEntries.length - 1].date : null
        };
    }

    summarizeGoalStatus(profile) {
        const goals = profile.socialGoals;
        
        if (goals.length === 0) {
            return { message: 'No social goals set' };
        }

        const active = goals.filter(g => g.status === 'active').length;
        const completed = goals.filter(g => g.status === 'completed').length;
        const overdue = goals.filter(g => 
            g.status === 'active' && moment().isAfter(moment(g.targetDate))
        ).length;

        return {
            totalGoals: goals.length,
            activeGoals: active,
            completedGoals: completed,
            overdueGoals: overdue,
            completionRate: goals.length > 0 ? Math.round((completed / goals.length) * 100) : 0,
            recentlyCompleted: goals.filter(g => 
                g.status === 'completed' && 
                moment().diff(moment(g.completedAt || g.updatedAt), 'days') <= 30
            ).length
        };
    }

    generateSocialNextSteps(profile) {
        const nextSteps = [];
        const analysis = this.analyzeSocialPatterns(profile);

        // Assessment recommendations
        const lastAssessment = profile.assessmentHistory[profile.assessmentHistory.length - 1];
        if (!lastAssessment || moment().diff(moment(lastAssessment.date), 'months') > 12) {
            nextSteps.push({
                category: 'assessment',
                priority: 'high',
                action: 'Conduct comprehensive social skills assessment',
                timeframe: 'Within 4 weeks',
                rationale: 'Current assessment data is outdated or missing'
            });
        }

        // Intervention recommendations
        if (analysis.domainNeeds.length > 0) {
            const highPriorityNeeds = analysis.domainNeeds.filter(need => need.averagePercentile <= 15);
            if (highPriorityNeeds.length > 0) {
                nextSteps.push({
                    category: 'intervention',
                    priority: 'high',
                    action: `Initiate intensive intervention for ${highPriorityNeeds[0].description}`,
                    timeframe: 'Within 2 weeks',
                    rationale: 'Significant social skill deficits require immediate attention'
                });
            }
        }

        // Goal setting recommendations
        if (profile.socialGoals.length === 0) {
            nextSteps.push({
                category: 'goal_setting',
                priority: 'medium',
                action: 'Establish specific, measurable social skill goals',
                timeframe: 'Within 2 weeks',
                rationale: 'Goals are needed to track progress and guide intervention'
            });
        }

        // Progress monitoring recommendations
        const progressSummary = this.summarizeSocialProgress(profile);
        if (progressSummary.recentDataPoints === 0) {
            nextSteps.push({
                category: 'progress_monitoring',
                priority: 'medium',
                action: 'Establish regular progress monitoring system',
                timeframe: 'Within 1 week',
                rationale: 'Ongoing data collection needed to track intervention effectiveness'
            });
        }

        return nextSteps.sort((a, b) => {
            const priorityOrder = { high: 3, medium: 2, low: 1 };
            return priorityOrder[b.priority] - priorityOrder[a.priority];
        });
    }

    getPublicSocialProfile(profile) {
        return {
            id: profile.id,
            personalInfo: {
                name: profile.personalInfo.name,
                age: profile.personalInfo.age,
                grade: profile.personalInfo.grade
            },
            socialSkillSummary: this.summarizeSocialSkillProfile(profile.socialSkillProfile),
            strengthsNeeds: profile.strengthsNeeds,
            lastAssessment: profile.assessmentHistory[profile.assessmentHistory.length - 1]?.date,
            activeGoals: profile.socialGoals.filter(g => g.status === 'active').length,
            developmentalProgress: this.summarizeDevelopmentalProgress(profile)
        };
    }

    summarizeSocialSkillProfile(socialSkillProfile) {
        const summary = {};
        Object.entries(socialSkillProfile).forEach(([domainId, domain]) => {
            const subdomainRatings = Object.values(domain)
                .filter(subdomain => subdomain.percentileRank !== null)
                .map(subdomain => subdomain.percentileRank);

            if (subdomainRatings.length > 0) {
                const avgPercentile = subdomainRatings.reduce((sum, p) => sum + p, 0) / subdomainRatings.length;
                summary[domainId] = {
                    averagePercentile: Math.round(avgPercentile),
                    subdomainsAssessed: subdomainRatings.length,
                    lastAssessed: Math.max(...Object.values(domain).map(s => s.lastAssessed || 0))
                };
            }
        });
        return summary;
    }

    getAllProfiles() {
        return Array.from(this.studentProfiles.values()).map(profile => 
            this.getPublicSocialProfile(profile)
        );
    }

    getProfile(studentId) {
        const profile = this.studentProfiles.get(studentId);
        return profile ? this.getPublicSocialProfile(profile) : null;
    }

    deleteProfile(studentId) {
        const deleted = this.studentProfiles.delete(studentId);
        if (deleted) {
            this.emit('socialProfileDeleted', { studentId });
        }
        return deleted;
    }
}

module.exports = SocialSkillAssessment;