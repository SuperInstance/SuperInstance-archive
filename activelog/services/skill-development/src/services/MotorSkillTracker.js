const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');

class MotorSkillTracker extends EventEmitter {
    constructor() {
        super();
        this.studentProfiles = new Map();
        this.skillCategories = this.initializeSkillCategories();
        this.developmentMilestones = this.initializeDevelopmentMilestones();
        this.assessmentTools = this.initializeAssessmentTools();
        this.interventionStrategies = this.initializeInterventionStrategies();
    }

    initializeSkillCategories() {
        return {
            gross_motor: {
                id: 'gross_motor',
                name: 'Gross Motor Skills',
                description: 'Large muscle movements and coordination',
                skills: {
                    balance: {
                        name: 'Balance and Stability',
                        components: ['static_balance', 'dynamic_balance', 'postural_control'],
                        assessment_methods: ['single_leg_stand', 'balance_beam', 'stability_challenges']
                    },
                    locomotion: {
                        name: 'Locomotor Skills',
                        components: ['walking', 'running', 'jumping', 'hopping', 'skipping', 'galloping'],
                        assessment_methods: ['movement_patterns', 'speed_tests', 'coordination_tasks']
                    },
                    object_control: {
                        name: 'Object Control Skills',
                        components: ['throwing', 'catching', 'kicking', 'striking', 'dribbling'],
                        assessment_methods: ['ball_skills', 'target_accuracy', 'manipulation_tasks']
                    },
                    body_awareness: {
                        name: 'Body Awareness',
                        components: ['spatial_awareness', 'body_schema', 'proprioception'],
                        assessment_methods: ['body_part_identification', 'spatial_tasks', 'movement_copying']
                    }
                }
            },
            fine_motor: {
                id: 'fine_motor',
                name: 'Fine Motor Skills',
                description: 'Small muscle movements and precision',
                skills: {
                    hand_dexterity: {
                        name: 'Hand and Finger Dexterity',
                        components: ['finger_isolation', 'in_hand_manipulation', 'bilateral_coordination'],
                        assessment_methods: ['pegboard_test', 'bead_threading', 'finger_tapping']
                    },
                    writing_skills: {
                        name: 'Pre-writing and Writing Skills',
                        components: ['pencil_grip', 'letter_formation', 'line_drawing', 'pressure_control'],
                        assessment_methods: ['handwriting_samples', 'drawing_tasks', 'tracing_activities']
                    },
                    cutting_skills: {
                        name: 'Cutting and Manipulation',
                        components: ['scissor_skills', 'tool_use', 'craft_activities'],
                        assessment_methods: ['cutting_tests', 'construction_tasks', 'tool_manipulation']
                    },
                    visual_motor: {
                        name: 'Visual-Motor Integration',
                        components: ['hand_eye_coordination', 'copying_skills', 'drawing_accuracy'],
                        assessment_methods: ['copying_tests', 'dot_to_dot', 'maze_completion']
                    }
                }
            },
            oral_motor: {
                id: 'oral_motor',
                name: 'Oral Motor Skills',
                description: 'Mouth and speech-related motor skills',
                skills: {
                    articulation: {
                        name: 'Speech Articulation',
                        components: ['sound_production', 'speech_clarity', 'pronunciation'],
                        assessment_methods: ['speech_samples', 'articulation_tests', 'phoneme_production']
                    },
                    feeding_skills: {
                        name: 'Eating and Drinking',
                        components: ['chewing', 'swallowing', 'utensil_use', 'cup_drinking'],
                        assessment_methods: ['feeding_observation', 'texture_tolerance', 'self_feeding']
                    },
                    oral_awareness: {
                        name: 'Oral Awareness',
                        components: ['lip_closure', 'tongue_movement', 'jaw_control'],
                        assessment_methods: ['oral_motor_exercises', 'imitation_tasks', 'awareness_activities']
                    }
                }
            }
        };
    }

    initializeDevelopmentMilestones() {
        return {
            age_2_3: {
                gross_motor: [
                    'Walks steadily without falling',
                    'Runs with improved coordination',
                    'Jumps with both feet together',
                    'Kicks a ball forward',
                    'Throws ball overhand'
                ],
                fine_motor: [
                    'Stacks 6-8 blocks',
                    'Turns pages in a book',
                    'Scribbles with purpose',
                    'Uses spoon and fork',
                    'Removes clothing independently'
                ]
            },
            age_3_4: {
                gross_motor: [
                    'Pedals tricycle',
                    'Walks up stairs alternating feet',
                    'Hops on one foot briefly',
                    'Catches large ball with arms',
                    'Balances on one foot for 2-3 seconds'
                ],
                fine_motor: [
                    'Cuts with scissors following lines',
                    'Copies simple shapes',
                    'Draws person with 3-4 body parts',
                    'Strings large beads',
                    'Uses toilet independently'
                ]
            },
            age_4_5: {
                gross_motor: [
                    'Skips smoothly',
                    'Throws ball with accuracy',
                    'Catches bounced ball',
                    'Walks on balance beam',
                    'Performs somersaults'
                ],
                fine_motor: [
                    'Cuts complex shapes',
                    'Writes some letters',
                    'Ties shoes with help',
                    'Uses knife to spread',
                    'Copies triangle and square'
                ]
            },
            age_5_6: {
                gross_motor: [
                    'Rides bicycle with training wheels',
                    'Jumps rope',
                    'Performs heel-to-toe walk',
                    'Throws and catches with control',
                    'Demonstrates rhythm in movement'
                ],
                fine_motor: [
                    'Writes name clearly',
                    'Cuts on lines accurately',
                    'Ties shoes independently',
                    'Uses mature pencil grip',
                    'Draws detailed pictures'
                ]
            },
            age_6_8: {
                gross_motor: [
                    'Rides bicycle without training wheels',
                    'Performs coordinated sports movements',
                    'Demonstrates mature throwing pattern',
                    'Shows good balance in activities',
                    'Performs complex movement sequences'
                ],
                fine_motor: [
                    'Writes legibly in correct size',
                    'Uses tools with precision',
                    'Performs detailed crafts',
                    'Shows good hand-eye coordination',
                    'Manipulates small objects skillfully'
                ]
            }
        };
    }

    initializeAssessmentTools() {
        return {
            movement_abc: {
                name: 'Movement Assessment Battery for Children',
                age_range: '3-16 years',
                domains: ['manual_dexterity', 'ball_skills', 'static_dynamic_balance'],
                scoring: 'percentile_ranks',
                administration_time: '20-40 minutes'
            },
            peabody_pdms: {
                name: 'Peabody Developmental Motor Scales',
                age_range: '0-6 years',
                domains: ['reflexes', 'stationary', 'locomotion', 'object_manipulation', 'grasping', 'visual_motor'],
                scoring: 'standard_scores',
                administration_time: '45-60 minutes'
            },
            tgmd: {
                name: 'Test of Gross Motor Development',
                age_range: '3-10 years',
                domains: ['locomotor_skills', 'object_control_skills'],
                scoring: 'standard_scores_percentiles',
                administration_time: '15-20 minutes'
            },
            bot2: {
                name: 'Bruininks-Oseretsky Test of Motor Proficiency',
                age_range: '4-21 years',
                domains: ['fine_manual_control', 'manual_coordination', 'body_coordination', 'strength_agility'],
                scoring: 'standard_scores',
                administration_time: '45-60 minutes'
            },
            custom_observations: {
                name: 'Classroom Observation Tool',
                age_range: 'All ages',
                domains: ['daily_living_skills', 'academic_tasks', 'play_skills', 'social_participation'],
                scoring: 'qualitative_ratings',
                administration_time: 'Ongoing'
            }
        };
    }

    initializeInterventionStrategies() {
        return {
            gross_motor_interventions: {
                balance_activities: [
                    'Balance board exercises',
                    'Single-leg standing games',
                    'Walking on different surfaces',
                    'Yoga poses for children',
                    'Balance beam activities'
                ],
                coordination_activities: [
                    'Obstacle courses',
                    'Dance and movement games',
                    'Ball throwing and catching',
                    'Jumping rope progressions',
                    'Bilateral coordination tasks'
                ],
                strength_activities: [
                    'Playground activities',
                    'Carrying heavy objects',
                    'Push and pull games',
                    'Climbing activities',
                    'Resistance exercises'
                ]
            },
            fine_motor_interventions: {
                hand_strengthening: [
                    'Playdough activities',
                    'Squeeze toys and stress balls',
                    'Clothespin games',
                    'Tweezers and tong activities',
                    'Hand exercise programs'
                ],
                dexterity_activities: [
                    'Pegboard activities',
                    'Bead stringing',
                    'Lacing cards',
                    'Button and zipper practice',
                    'Finger isolation exercises'
                ],
                writing_preparation: [
                    'Pre-writing shapes',
                    'Pencil grip activities',
                    'Letter formation practice',
                    'Tracing activities',
                    'Drawing progressions'
                ]
            },
            sensory_motor_interventions: {
                proprioceptive_activities: [
                    'Heavy work activities',
                    'Joint compression exercises',
                    'Push and pull tasks',
                    'Weighted activities',
                    'Resistance band exercises'
                ],
                vestibular_activities: [
                    'Swinging activities',
                    'Spinning games',
                    'Balance challenges',
                    'Movement songs',
                    'Rocking activities'
                ],
                tactile_activities: [
                    'Sensory bins',
                    'Texture exploration',
                    'Finger painting',
                    'Massage activities',
                    'Tactile discrimination games'
                ]
            }
        };
    }

    createStudentProfile(studentId, studentInfo) {
        const profile = {
            id: studentId,
            personalInfo: {
                name: studentInfo.name,
                dateOfBirth: studentInfo.dateOfBirth,
                age: this.calculateAge(studentInfo.dateOfBirth),
                grade: studentInfo.grade,
                medicalHistory: studentInfo.medicalHistory || [],
                currentConcerns: studentInfo.currentConcerns || []
            },
            assessmentHistory: [],
            currentSkillLevels: this.initializeSkillLevels(),
            progressTracking: {
                goals: [],
                interventions: [],
                milestoneProgress: new Map()
            },
            riskFactors: [],
            strengths: [],
            recommendations: [],
            createdAt: new Date(),
            updatedAt: new Date()
        };

        this.studentProfiles.set(studentId, profile);
        
        // Initialize with age-appropriate milestones
        this.setAgeMilestones(profile);
        
        this.emit('profileCreated', {
            studentId,
            profile: this.getPublicProfile(profile)
        });

        return profile;
    }

    calculateAge(dateOfBirth) {
        return moment().diff(moment(dateOfBirth), 'years', true);
    }

    initializeSkillLevels() {
        const skills = {};
        
        Object.entries(this.skillCategories).forEach(([categoryId, category]) => {
            skills[categoryId] = {};
            Object.entries(category.skills).forEach(([skillId, skill]) => {
                skills[categoryId][skillId] = {
                    level: 'not_assessed',
                    score: null,
                    percentile: null,
                    lastAssessed: null,
                    progression: [],
                    notes: []
                };
            });
        });

        return skills;
    }

    setAgeMilestones(profile) {
        const age = profile.personalInfo.age;
        let milestoneKey;

        if (age < 3) milestoneKey = 'age_2_3';
        else if (age < 4) milestoneKey = 'age_3_4';
        else if (age < 5) milestoneKey = 'age_4_5';
        else if (age < 6) milestoneKey = 'age_5_6';
        else milestoneKey = 'age_6_8';

        const milestones = this.developmentMilestones[milestoneKey];
        if (milestones) {
            Object.entries(milestones).forEach(([category, skills]) => {
                skills.forEach(skill => {
                    profile.progressTracking.milestoneProgress.set(skill, {
                        achieved: false,
                        dateAchieved: null,
                        category: category,
                        difficulty: this.getMilestoneDifficulty(skill, age)
                    });
                });
            });
        }
    }

    getMilestoneDifficulty(skill, age) {
        // Simple heuristic for milestone difficulty
        if (age < 3) return 'emerging';
        if (age < 5) return 'developing';
        return 'advanced';
    }

    conductAssessment(studentId, assessmentData) {
        const profile = this.studentProfiles.get(studentId);
        if (!profile) {
            throw new Error('Student profile not found');
        }

        const assessment = {
            id: uuidv4(),
            date: new Date(),
            assessor: assessmentData.assessor,
            tool: assessmentData.tool,
            environment: assessmentData.environment,
            results: assessmentData.results,
            observations: assessmentData.observations,
            recommendations: assessmentData.recommendations
        };

        profile.assessmentHistory.push(assessment);
        
        // Update skill levels based on assessment
        this.updateSkillLevels(profile, assessment);
        
        // Analyze progress
        const progressAnalysis = this.analyzeProgress(profile);
        
        // Update recommendations
        this.updateRecommendations(profile, progressAnalysis);
        
        profile.updatedAt = new Date();

        this.emit('assessmentCompleted', {
            studentId,
            assessmentId: assessment.id,
            results: assessment.results,
            progressAnalysis
        });

        return {
            assessment,
            progressAnalysis,
            updatedSkills: profile.currentSkillLevels
        };
    }

    updateSkillLevels(profile, assessment) {
        Object.entries(assessment.results).forEach(([categoryId, categoryResults]) => {
            if (profile.currentSkillLevels[categoryId]) {
                Object.entries(categoryResults).forEach(([skillId, result]) => {
                    if (profile.currentSkillLevels[categoryId][skillId]) {
                        const skill = profile.currentSkillLevels[categoryId][skillId];
                        
                        // Add to progression history
                        skill.progression.push({
                            date: assessment.date,
                            score: result.score,
                            level: result.level,
                            percentile: result.percentile,
                            assessmentTool: assessment.tool
                        });

                        // Update current values
                        skill.level = result.level;
                        skill.score = result.score;
                        skill.percentile = result.percentile;
                        skill.lastAssessed = assessment.date;
                        
                        if (result.notes) {
                            skill.notes.push({
                                date: assessment.date,
                                note: result.notes,
                                assessor: assessment.assessor
                            });
                        }
                    }
                });
            }
        });
    }

    analyzeProgress(profile) {
        const analysis = {
            overallTrend: 'stable',
            categoryTrends: {},
            strengths: [],
            areasForImprovement: [],
            milestoneProgress: this.analyzeMilestoneProgress(profile),
            riskFactors: [],
            interventionEffectiveness: {}
        };

        // Analyze trends for each category
        Object.entries(profile.currentSkillLevels).forEach(([categoryId, skills]) => {
            const categoryAnalysis = this.analyzeCategoryProgress(skills);
            analysis.categoryTrends[categoryId] = categoryAnalysis;
            
            // Identify strengths and areas for improvement
            if (categoryAnalysis.averagePercentile > 75) {
                analysis.strengths.push({
                    category: categoryId,
                    description: `Strong performance in ${this.skillCategories[categoryId].name}`,
                    percentile: categoryAnalysis.averagePercentile
                });
            } else if (categoryAnalysis.averagePercentile < 25) {
                analysis.areasForImprovement.push({
                    category: categoryId,
                    description: `Needs support in ${this.skillCategories[categoryId].name}`,
                    percentile: categoryAnalysis.averagePercentile
                });
            }
        });

        // Determine overall trend
        const allTrends = Object.values(analysis.categoryTrends).map(cat => cat.trend);
        if (allTrends.filter(t => t === 'improving').length > allTrends.length / 2) {
            analysis.overallTrend = 'improving';
        } else if (allTrends.filter(t => t === 'declining').length > allTrends.length / 3) {
            analysis.overallTrend = 'declining';
        }

        return analysis;
    }

    analyzeCategoryProgress(skills) {
        const skillEntries = Object.entries(skills);
        const assessedSkills = skillEntries.filter(([_, skill]) => skill.progression.length > 0);
        
        if (assessedSkills.length === 0) {
            return {
                trend: 'not_assessed',
                averagePercentile: null,
                progressRate: 0,
                consistencyScore: 0
            };
        }

        // Calculate average percentile
        const percentiles = assessedSkills
            .filter(([_, skill]) => skill.percentile !== null)
            .map(([_, skill]) => skill.percentile);
        
        const averagePercentile = percentiles.length > 0 
            ? percentiles.reduce((sum, p) => sum + p, 0) / percentiles.length 
            : null;

        // Calculate progress trend
        let trend = 'stable';
        let totalProgressRate = 0;
        let skillsWithTrend = 0;

        assessedSkills.forEach(([_, skill]) => {
            if (skill.progression.length >= 2) {
                const recent = skill.progression.slice(-2);
                const progressRate = recent[1].percentile - recent[0].percentile;
                totalProgressRate += progressRate;
                skillsWithTrend++;
            }
        });

        if (skillsWithTrend > 0) {
            const averageProgressRate = totalProgressRate / skillsWithTrend;
            if (averageProgressRate > 5) trend = 'improving';
            else if (averageProgressRate < -5) trend = 'declining';
        }

        return {
            trend,
            averagePercentile,
            progressRate: skillsWithTrend > 0 ? totalProgressRate / skillsWithTrend : 0,
            consistencyScore: this.calculateConsistency(assessedSkills)
        };
    }

    calculateConsistency(assessedSkills) {
        if (assessedSkills.length === 0) return 0;

        const percentiles = assessedSkills
            .filter(([_, skill]) => skill.percentile !== null)
            .map(([_, skill]) => skill.percentile);

        if (percentiles.length < 2) return 0;

        const mean = percentiles.reduce((sum, p) => sum + p, 0) / percentiles.length;
        const variance = percentiles.reduce((sum, p) => sum + Math.pow(p - mean, 2), 0) / percentiles.length;
        const standardDeviation = Math.sqrt(variance);

        // Lower standard deviation = higher consistency
        return Math.max(0, 100 - standardDeviation);
    }

    analyzeMilestoneProgress(profile) {
        const milestones = Array.from(profile.progressTracking.milestoneProgress.entries());
        const achieved = milestones.filter(([_, milestone]) => milestone.achieved).length;
        const total = milestones.length;
        
        return {
            achievedCount: achieved,
            totalCount: total,
            percentageAchieved: total > 0 ? (achieved / total) * 100 : 0,
            recentAchievements: milestones
                .filter(([_, milestone]) => 
                    milestone.achieved && 
                    milestone.dateAchieved && 
                    moment(milestone.dateAchieved).isAfter(moment().subtract(30, 'days'))
                )
                .map(([skill, milestone]) => ({ skill, ...milestone }))
        };
    }

    updateRecommendations(profile, progressAnalysis) {
        const recommendations = [];

        // Add recommendations based on areas for improvement
        progressAnalysis.areasForImprovement.forEach(area => {
            const interventions = this.getInterventionRecommendations(area.category, area.percentile);
            recommendations.push({
                category: area.category,
                type: 'intervention',
                priority: area.percentile < 10 ? 'high' : 'medium',
                recommendations: interventions,
                rationale: `Low performance in ${area.category} (${area.percentile}th percentile)`
            });
        });

        // Add recommendations for strengths
        progressAnalysis.strengths.forEach(strength => {
            recommendations.push({
                category: strength.category,
                type: 'enrichment',
                priority: 'medium',
                recommendations: this.getEnrichmentRecommendations(strength.category),
                rationale: `Strong performance in ${strength.category} - opportunities for advanced challenges`
            });
        });

        // Add milestone-based recommendations
        const milestoneProgress = progressAnalysis.milestoneProgress;
        if (milestoneProgress.percentageAchieved < 60) {
            recommendations.push({
                category: 'developmental',
                type: 'milestone_focus',
                priority: 'high',
                recommendations: this.getMilestoneRecommendations(profile),
                rationale: 'Below expected milestone achievement rate'
            });
        }

        profile.recommendations = recommendations;
    }

    getInterventionRecommendations(category, percentile) {
        const intensity = percentile < 10 ? 'intensive' : percentile < 25 ? 'moderate' : 'light';
        const strategies = this.interventionStrategies;
        
        switch (category) {
            case 'gross_motor':
                return [
                    `${intensity} gross motor intervention program`,
                    'Daily movement breaks',
                    'Occupational therapy consultation',
                    'Structured physical activities',
                    'Home exercise program'
                ];
            case 'fine_motor':
                return [
                    `${intensity} fine motor skill practice`,
                    'Hand strengthening activities',
                    'Pre-writing skill development',
                    'Occupational therapy services',
                    'Adaptive tools assessment'
                ];
            case 'oral_motor':
                return [
                    `${intensity} oral motor exercises`,
                    'Speech therapy consultation',
                    'Feeding skills practice',
                    'Oral sensory activities',
                    'Family training on techniques'
                ];
            default:
                return ['General motor skill support', 'Professional consultation recommended'];
        }
    }

    getEnrichmentRecommendations(category) {
        switch (category) {
            case 'gross_motor':
                return [
                    'Advanced sports skills training',
                    'Dance or gymnastics classes',
                    'Leadership roles in physical activities',
                    'Peer tutoring opportunities',
                    'Complex movement challenges'
                ];
            case 'fine_motor':
                return [
                    'Advanced art and craft projects',
                    'Musical instrument learning',
                    'Complex construction activities',
                    'Detailed drawing and design work',
                    'Technology skills development'
                ];
            case 'oral_motor':
                return [
                    'Advanced speech activities',
                    'Public speaking opportunities',
                    'Drama and theater participation',
                    'Language learning programs',
                    'Peer communication roles'
                ];
            default:
                return ['Advanced skill development opportunities'];
        }
    }

    getMilestoneRecommendations(profile) {
        const unachievedMilestones = Array.from(profile.progressTracking.milestoneProgress.entries())
            .filter(([_, milestone]) => !milestone.achieved)
            .map(([skill, milestone]) => ({ skill, ...milestone }));

        return unachievedMilestones.slice(0, 5).map(milestone => 
            `Focus on: ${milestone.skill} (${milestone.category})`
        );
    }

    setGoals(studentId, goals) {
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
            milestones: goal.milestones || [],
            interventions: []
        }));

        profile.progressTracking.goals.push(...processedGoals);
        profile.updatedAt = new Date();

        this.emit('goalsSet', {
            studentId,
            goals: processedGoals
        });

        return processedGoals;
    }

    updateGoalProgress(studentId, goalId, progressUpdate) {
        const profile = this.studentProfiles.get(studentId);
        if (!profile) {
            throw new Error('Student profile not found');
        }

        const goal = profile.progressTracking.goals.find(g => g.id === goalId);
        if (!goal) {
            throw new Error('Goal not found');
        }

        goal.progress = progressUpdate.progress;
        goal.status = progressUpdate.status || goal.status;
        goal.notes = goal.notes || [];
        
        if (progressUpdate.note) {
            goal.notes.push({
                date: new Date(),
                note: progressUpdate.note,
                progress: progressUpdate.progress
            });
        }

        if (progressUpdate.progress >= 100) {
            goal.status = 'completed';
            goal.completedAt = new Date();
        }

        profile.updatedAt = new Date();

        this.emit('goalProgressUpdated', {
            studentId,
            goalId,
            goal,
            progressUpdate
        });

        return goal;
    }

    generateProgressReport(studentId, timeframe = '6months') {
        const profile = this.studentProfiles.get(studentId);
        if (!profile) {
            throw new Error('Student profile not found');
        }

        const endDate = moment();
        const startDate = moment().subtract(timeframe === '6months' ? 6 : 12, 'months');

        const report = {
            studentInfo: profile.personalInfo,
            reportPeriod: {
                start: startDate.toDate(),
                end: endDate.toDate(),
                duration: timeframe
            },
            skillProgressSummary: this.generateSkillProgressSummary(profile, startDate),
            milestoneAchievements: this.getMilestoneAchievements(profile, startDate),
            goalProgress: this.getGoalProgress(profile, startDate),
            assessmentSummary: this.getAssessmentSummary(profile, startDate),
            recommendations: profile.recommendations,
            nextSteps: this.generateNextSteps(profile),
            generatedAt: new Date()
        };

        this.emit('reportGenerated', {
            studentId,
            reportType: 'progress',
            timeframe,
            report
        });

        return report;
    }

    generateSkillProgressSummary(profile, startDate) {
        const summary = {};

        Object.entries(profile.currentSkillLevels).forEach(([categoryId, skills]) => {
            const categoryData = {
                categoryName: this.skillCategories[categoryId].name,
                skills: {},
                overallProgress: 0,
                trend: 'stable'
            };

            let totalProgress = 0;
            let skillCount = 0;

            Object.entries(skills).forEach(([skillId, skill]) => {
                const relevantProgress = skill.progression.filter(p => 
                    moment(p.date).isAfter(startDate)
                );

                if (relevantProgress.length > 0) {
                    const firstScore = relevantProgress[0].percentile || 0;
                    const lastScore = relevantProgress[relevantProgress.length - 1].percentile || 0;
                    const progress = lastScore - firstScore;

                    categoryData.skills[skillId] = {
                        name: this.skillCategories[categoryId].skills[skillId].name,
                        currentLevel: skill.level,
                        currentPercentile: skill.percentile,
                        progress: progress,
                        assessmentCount: relevantProgress.length
                    };

                    totalProgress += progress;
                    skillCount++;
                }
            });

            if (skillCount > 0) {
                categoryData.overallProgress = totalProgress / skillCount;
                if (categoryData.overallProgress > 5) categoryData.trend = 'improving';
                else if (categoryData.overallProgress < -5) categoryData.trend = 'declining';
            }

            summary[categoryId] = categoryData;
        });

        return summary;
    }

    getMilestoneAchievements(profile, startDate) {
        return Array.from(profile.progressTracking.milestoneProgress.entries())
            .filter(([_, milestone]) => 
                milestone.achieved && 
                milestone.dateAchieved &&
                moment(milestone.dateAchieved).isAfter(startDate)
            )
            .map(([skill, milestone]) => ({
                skill,
                category: milestone.category,
                dateAchieved: milestone.dateAchieved,
                difficulty: milestone.difficulty
            }));
    }

    getGoalProgress(profile, startDate) {
        return profile.progressTracking.goals
            .filter(goal => moment(goal.createdAt).isAfter(startDate) || goal.status === 'active')
            .map(goal => ({
                id: goal.id,
                description: goal.description,
                progress: goal.progress,
                status: goal.status,
                targetDate: goal.targetDate,
                category: goal.category,
                notes: goal.notes || []
            }));
    }

    getAssessmentSummary(profile, startDate) {
        const assessments = profile.assessmentHistory.filter(a => 
            moment(a.date).isAfter(startDate)
        );

        return {
            totalAssessments: assessments.length,
            assessmentTypes: [...new Set(assessments.map(a => a.tool))],
            assessors: [...new Set(assessments.map(a => a.assessor))],
            environments: [...new Set(assessments.map(a => a.environment))],
            recentAssessments: assessments.slice(-3).map(a => ({
                date: a.date,
                tool: a.tool,
                assessor: a.assessor,
                keyFindings: a.observations
            }))
        };
    }

    generateNextSteps(profile) {
        const steps = [];
        const analysis = this.analyzeProgress(profile);

        // Assessment recommendations
        const lastAssessment = profile.assessmentHistory[profile.assessmentHistory.length - 1];
        if (!lastAssessment || moment().diff(moment(lastAssessment.date), 'months') > 6) {
            steps.push({
                category: 'assessment',
                priority: 'high',
                action: 'Schedule comprehensive motor skills assessment',
                timeframe: 'Within 2 weeks'
            });
        }

        // Goal-based next steps
        const activeGoals = profile.progressTracking.goals.filter(g => g.status === 'active');
        activeGoals.forEach(goal => {
            if (goal.progress < 50 && moment().isAfter(moment(goal.targetDate).subtract(1, 'month'))) {
                steps.push({
                    category: 'goal_support',
                    priority: 'medium',
                    action: `Intensify interventions for goal: ${goal.description}`,
                    timeframe: 'Immediate'
                });
            }
        });

        // Category-specific recommendations
        Object.entries(analysis.categoryTrends).forEach(([categoryId, trend]) => {
            if (trend.trend === 'declining') {
                steps.push({
                    category: 'intervention',
                    priority: 'high',
                    action: `Address declining performance in ${this.skillCategories[categoryId].name}`,
                    timeframe: 'Within 1 week'
                });
            }
        });

        return steps.sort((a, b) => {
            const priorityOrder = { high: 3, medium: 2, low: 1 };
            return priorityOrder[b.priority] - priorityOrder[a.priority];
        });
    }

    getPublicProfile(profile) {
        return {
            id: profile.id,
            personalInfo: {
                name: profile.personalInfo.name,
                age: profile.personalInfo.age,
                grade: profile.personalInfo.grade
            },
            currentSkillLevels: profile.currentSkillLevels,
            strengths: profile.strengths,
            lastAssessment: profile.assessmentHistory[profile.assessmentHistory.length - 1]?.date,
            goalCount: profile.progressTracking.goals.filter(g => g.status === 'active').length,
            milestoneProgress: profile.progressTracking.milestoneProgress.size
        };
    }

    getAllProfiles() {
        return Array.from(this.studentProfiles.values()).map(profile => 
            this.getPublicProfile(profile)
        );
    }

    getProfile(studentId) {
        const profile = this.studentProfiles.get(studentId);
        return profile ? this.getPublicProfile(profile) : null;
    }

    deleteProfile(studentId) {
        const deleted = this.studentProfiles.delete(studentId);
        if (deleted) {
            this.emit('profileDeleted', { studentId });
        }
        return deleted;
    }
}

module.exports = MotorSkillTracker;