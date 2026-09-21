const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');

class ProgressiveComplexitySystem extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        // Player skill assessment framework
        this.skillCategories = {
            'rules_mastery': {
                name: 'Rules Knowledge',
                description: 'Understanding of D&D mechanics and rules',
                indicators: [
                    'applies_modifiers_correctly',
                    'knows_action_types',
                    'understands_advantage_disadvantage',
                    'uses_spell_slots_appropriately',
                    'calculates_damage_accurately'
                ],
                complexity_factors: ['rule_complexity', 'mechanical_depth', 'exception_handling']
            },
            
            'tactical_thinking': {
                name: 'Tactical Combat',
                description: 'Strategic thinking in combat situations',
                indicators: [
                    'uses_positioning_strategically',
                    'coordinates_with_team',
                    'adapts_tactics_to_enemies',
                    'manages_resources_effectively',
                    'thinks_several_turns_ahead'
                ],
                complexity_factors: ['encounter_complexity', 'tactical_options', 'resource_management']
            },
            
            'roleplay_engagement': {
                name: 'Roleplay Skills',
                description: 'Character portrayal and narrative engagement',
                indicators: [
                    'consistent_character_voice',
                    'makes_character_driven_decisions',
                    'engages_with_npcs_meaningfully',
                    'contributes_to_group_storytelling',
                    'handles_character_conflicts'
                ],
                complexity_factors: ['narrative_complexity', 'character_depth', 'social_challenges']
            },
            
            'problem_solving': {
                name: 'Creative Problem Solving',
                description: 'Innovative thinking and adaptability',
                indicators: [
                    'thinks_outside_established_solutions',
                    'combines_abilities_creatively',
                    'adapts_to_unexpected_situations',
                    'proposes_innovative_approaches',
                    'learns_from_failed_attempts'
                ],
                complexity_factors: ['puzzle_complexity', 'open_ended_challenges', 'creative_requirements']
            },
            
            'system_mastery': {
                name: 'System Expertise',
                description: 'Deep understanding of D&D systems',
                indicators: [
                    'optimizes_character_builds',
                    'understands_action_economy',
                    'exploits_mechanical_synergies',
                    'handles_complex_interactions',
                    'teaches_other_players'
                ],
                complexity_factors: ['system_depth', 'optimization_opportunities', 'mechanical_interactions']
            },
            
            'narrative_contribution': {
                name: 'Story Contribution',
                description: 'Active participation in collaborative storytelling',
                indicators: [
                    'adds_details_to_world',
                    'creates_character_backstory_hooks',
                    'builds_on_others_ideas',
                    'drives_narrative_forward',
                    'handles_dramatic_moments'
                ],
                complexity_factors: ['narrative_agency', 'story_complexity', 'character_development']
            }
        };
        
        // Complexity scaling mechanisms
        this.complexityScaling = {
            encounters: {
                beginner: {
                    enemy_count: 'Single enemy or small groups',
                    enemy_complexity: 'Simple stat blocks, basic abilities',
                    terrain: 'Open areas, minimal complications',
                    objectives: 'Defeat all enemies',
                    tactics: 'Straightforward attack patterns'
                },
                intermediate: {
                    enemy_count: 'Varied group sizes, multiple enemy types',
                    enemy_complexity: 'Some special abilities, tactical awareness',
                    terrain: 'Moderate terrain features, cover options',
                    objectives: 'Multiple win conditions available',
                    tactics: 'Enemies use formations and basic tactics'
                },
                advanced: {
                    enemy_count: 'Large groups, reinforcement waves',
                    enemy_complexity: 'Complex abilities, legendary actions',
                    terrain: 'Dynamic environments, hazards, verticality',
                    objectives: 'Time pressure, protection missions, puzzles',
                    tactics: 'Sophisticated enemy coordination and adaptation'
                },
                expert: {
                    enemy_count: 'Massive encounters, multiple fronts',
                    enemy_complexity: 'Unique mechanics, adaptive abilities',
                    terrain: 'Shifting battlefields, environmental storytelling',
                    objectives: 'Moral dilemmas, cascading consequences',
                    tactics: 'Enemies learn and counter player strategies'
                }
            },
            
            social_encounters: {
                beginner: {
                    npc_motivations: 'Clear and straightforward',
                    consequences: 'Obvious and immediate',
                    information_gathering: 'Direct questions yield answers',
                    relationship_tracking: 'Simple friend/enemy dynamics'
                },
                intermediate: {
                    npc_motivations: 'Some hidden agendas and complexity',
                    consequences: 'Short-term and some long-term effects',
                    information_gathering: 'Requires some investigation',
                    relationship_tracking: 'Multiple relationship levels'
                },
                advanced: {
                    npc_motivations: 'Complex, conflicting interests',
                    consequences: 'Far-reaching, unintended effects',
                    information_gathering: 'Multi-source verification needed',
                    relationship_tracking: 'Dynamic, changing allegiances'
                },
                expert: {
                    npc_motivations: 'Layered, philosophical differences',
                    consequences: 'Systemic changes, moral implications',
                    information_gathering: 'Unreliable narrators, deception',
                    relationship_tracking: 'Network effects, reputation systems'
                }
            },
            
            exploration: {
                beginner: {
                    navigation: 'Linear paths, obvious routes',
                    discovery: 'Clearly marked secrets, simple clues',
                    environmental_challenges: 'Basic obstacles with clear solutions',
                    resource_management: 'Abundant resources, clear consequences'
                },
                intermediate: {
                    navigation: 'Multiple paths, some backtracking',
                    discovery: 'Hidden areas require investigation',
                    environmental_challenges: 'Moderate puzzles and hazards',
                    resource_management: 'Strategic resource allocation needed'
                },
                advanced: {
                    navigation: 'Complex layouts, puzzle-locked areas',
                    discovery: 'Layered secrets, cryptic clues',
                    environmental_challenges: 'Multi-step puzzles, dangerous hazards',
                    resource_management: 'Scarcity creates meaningful choices'
                },
                expert: {
                    navigation: 'Non-linear, interconnected regions',
                    discovery: 'Narrative secrets, player-driven reveals',
                    environmental_challenges: 'Physics-based puzzles, moral dilemmas',
                    resource_management: 'Complex economy, long-term planning'
                }
            }
        };
        
        // Assessment methods and triggers
        this.assessmentTriggers = {
            session_end: {
                frequency: 'after_each_session',
                methods: ['performance_analysis', 'self_assessment', 'peer_feedback'],
                weight: 0.3
            },
            critical_moments: {
                frequency: 'when_triggered',
                methods: ['decision_analysis', 'skill_demonstration', 'creative_solutions'],
                weight: 0.4
            },
            milestone_achievements: {
                frequency: 'level_up_or_major_events',
                methods: ['comprehensive_review', 'skill_portfolio', 'growth_tracking'],
                weight: 0.3
            }
        };
        
        // Adaptive difficulty adjustment algorithms
        this.adaptationAlgorithms = {
            gradual_scaling: {
                name: 'Gradual Progression',
                description: 'Slowly increase complexity over time',
                parameters: {
                    base_increase_rate: 0.1, // 10% complexity increase per session
                    skill_multiplier: 1.2,   // Faster scaling for skilled players
                    failure_adjustment: -0.2, // Reduce complexity after failures
                    success_boost: 0.05      // Small boost after successes
                }
            },
            
            performance_based: {
                name: 'Performance Adaptation',
                description: 'Adjust based on player performance metrics',
                parameters: {
                    target_success_rate: 0.7, // Aim for 70% success rate
                    adjustment_sensitivity: 0.15,
                    measurement_window: 5,    // Last 5 encounters
                    min_complexity_change: 0.05
                }
            },
            
            engagement_focused: {
                name: 'Engagement Optimization',
                description: 'Prioritize player engagement and flow state',
                parameters: {
                    engagement_threshold: 0.8, // Target 80% engagement
                    boredom_penalty: -0.3,     // Reduce complexity if bored
                    frustration_penalty: -0.4, // Reduce complexity if frustrated
                    flow_bonus: 0.1            // Maintain complexity in flow state
                }
            }
        };
    }

    async assessPlayer(playerId, options = {}) {
        try {
            const assessmentId = uuidv4();
            
            // Get player's historical data
            const playerHistory = await this._getPlayerHistory(playerId);
            
            // Perform comprehensive assessment
            const assessment = {
                id: assessmentId,
                player_id: playerId,
                assessed_at: new Date(),
                
                // Skill category scores
                skill_scores: await this._assessSkillCategories(playerId, playerHistory, options),
                
                // Overall complexity level
                current_complexity_level: this._calculateComplexityLevel(playerHistory),
                
                // Performance metrics
                performance_metrics: await this._analyzePerformanceMetrics(playerId, playerHistory),
                
                // Learning trajectory
                learning_trajectory: this._analyzeLearningTrajectory(playerHistory),
                
                // Recommended adjustments
                recommendations: await this._generateRecommendations(playerId, playerHistory),
                
                // Confidence scores
                assessment_confidence: this._calculateAssessmentConfidence(playerHistory),
                
                // Next assessment timing
                next_assessment_due: this._calculateNextAssessmentDate(playerHistory)
            };
            
            // Cache assessment results
            await this.redis.setex(
                `player_assessment:${playerId}`,
                86400 * 7, // 7 days
                JSON.stringify(assessment)
            );
            
            // Update player profile with new assessment
            await this._updatePlayerProfile(playerId, assessment);
            
            this.logger.info(`Assessed player: ${playerId} (${assessmentId})`);
            this.io.emit('player_assessed', { 
                playerId, 
                assessmentId,
                complexityLevel: assessment.current_complexity_level 
            });
            
            return assessment;
            
        } catch (error) {
            this.logger.error('Error assessing player:', error);
            throw error;
        }
    }

    async adjustComplexity(options = {}) {
        try {
            const adjustmentId = uuidv4();
            const players = options.players || [];
            const currentSession = options.session_data || {};
            
            // Analyze group composition and individual needs
            const groupAnalysis = await this._analyzeGroupComplexity(players, currentSession);
            
            // Calculate optimal complexity adjustments
            const adjustments = {
                id: adjustmentId,
                adjusted_at: new Date(),
                session_id: currentSession.id,
                players: players,
                
                // Group-level adjustments
                group_complexity_level: groupAnalysis.recommended_level,
                group_skill_distribution: groupAnalysis.skill_distribution,
                
                // Individual player adjustments
                individual_adjustments: await this._calculateIndividualAdjustments(players, groupAnalysis),
                
                // Specific game element modifications
                encounter_adjustments: this._generateEncounterAdjustments(groupAnalysis),
                social_adjustments: this._generateSocialAdjustments(groupAnalysis),
                exploration_adjustments: this._generateExplorationAdjustments(groupAnalysis),
                
                // Implementation guidance
                dm_guidance: this._generateDMGuidance(groupAnalysis),
                real_time_suggestions: this._generateRealTimeSuggestions(groupAnalysis),
                
                // Monitoring instructions
                success_indicators: this._defineSuccessIndicators(groupAnalysis),
                adjustment_triggers: this._defineAdjustmentTriggers(groupAnalysis)
            };
            
            // Apply adjustments to current session
            if (options.apply_immediately) {
                await this._applyAdjustments(adjustments, currentSession);
            }
            
            // Cache adjustment plan
            await this.redis.setex(
                `complexity_adjustment:${adjustmentId}`,
                86400, // 24 hours
                JSON.stringify(adjustments)
            );
            
            this.logger.info(`Generated complexity adjustments: ${adjustmentId}`);
            this.io.emit('complexity_adjusted', { 
                adjustmentId, 
                groupLevel: adjustments.group_complexity_level,
                playerCount: players.length 
            });
            
            return adjustments;
            
        } catch (error) {
            this.logger.error('Error adjusting complexity:', error);
            throw error;
        }
    }

    async trackPerformance(playerId, performanceData) {
        try {
            const trackingEntry = {
                player_id: playerId,
                timestamp: new Date(),
                session_id: performanceData.session_id,
                
                // Performance indicators
                success_rate: performanceData.success_rate || 0,
                engagement_score: performanceData.engagement_score || 0,
                creativity_demonstrated: performanceData.creativity_demonstrated || false,
                rules_accuracy: performanceData.rules_accuracy || 0,
                teamwork_rating: performanceData.teamwork_rating || 0,
                
                // Specific achievements
                achievements: performanceData.achievements || [],
                skills_demonstrated: performanceData.skills_demonstrated || [],
                areas_for_improvement: performanceData.areas_for_improvement || [],
                
                // Context information
                encounter_type: performanceData.encounter_type,
                complexity_level: performanceData.complexity_level,
                group_composition: performanceData.group_composition || []
            };
            
            // Store in player's performance history
            const historyKey = `player_performance:${playerId}`;
            const existingHistory = await this.redis.get(historyKey);
            const history = existingHistory ? JSON.parse(existingHistory) : [];
            
            history.push(trackingEntry);
            
            // Keep only recent entries (last 50)
            if (history.length > 50) {
                history.splice(0, history.length - 50);
            }
            
            await this.redis.setex(historyKey, 86400 * 30, JSON.stringify(history)); // 30 days
            
            // Trigger assessment if conditions are met
            if (this._shouldTriggerAssessment(playerId, trackingEntry, history)) {
                this.assessPlayer(playerId, { triggered_by: 'performance_tracking' });
            }
            
            this.logger.info(`Tracked performance for player: ${playerId}`);
            this.io.emit('performance_tracked', { playerId, sessionId: performanceData.session_id });
            
            return trackingEntry;
            
        } catch (error) {
            this.logger.error('Error tracking performance:', error);
            throw error;
        }
    }

    async _getPlayerHistory(playerId) {
        try {
            const performanceKey = `player_performance:${playerId}`;
            const assessmentKey = `player_assessment:${playerId}`;
            
            const [performanceData, assessmentData] = await Promise.all([
                this.redis.get(performanceKey),
                this.redis.get(assessmentKey)
            ]);
            
            return {
                performance_history: performanceData ? JSON.parse(performanceData) : [],
                last_assessment: assessmentData ? JSON.parse(assessmentData) : null,
                first_session: this._findFirstSession(performanceData ? JSON.parse(performanceData) : []),
                total_sessions: performanceData ? JSON.parse(performanceData).length : 0
            };
            
        } catch (error) {
            this.logger.error('Error getting player history:', error);
            return { performance_history: [], last_assessment: null, first_session: null, total_sessions: 0 };
        }
    }

    async _assessSkillCategories(playerId, playerHistory, options) {
        const skillScores = {};
        
        for (const [categoryId, category] of Object.entries(this.skillCategories)) {
            const indicators = category.indicators;
            let categoryScore = 0;
            let evidenceCount = 0;
            
            // Analyze performance history for indicators
            for (const performance of playerHistory.performance_history) {
                for (const indicator of indicators) {
                    if (performance.skills_demonstrated.includes(indicator)) {
                        categoryScore += this._getIndicatorWeight(indicator, performance);
                        evidenceCount++;
                    }
                }
            }
            
            // Calculate normalized score
            const normalizedScore = evidenceCount > 0 ? categoryScore / evidenceCount : 0.5; // Default to middle
            
            skillScores[categoryId] = {
                category_name: category.name,
                score: Math.max(0, Math.min(1, normalizedScore)), // Clamp to 0-1
                evidence_count: evidenceCount,
                confidence: this._calculateCategoryConfidence(evidenceCount, playerHistory.total_sessions),
                trend: this._calculateSkillTrend(categoryId, playerHistory.performance_history),
                next_growth_opportunities: this._identifyGrowthOpportunities(categoryId, normalizedScore)
            };
        }
        
        return skillScores;
    }

    _calculateComplexityLevel(playerHistory) {
        if (!playerHistory.performance_history.length) {
            return 'beginner';
        }
        
        // Calculate weighted average of recent performance
        const recentHistory = playerHistory.performance_history.slice(-10); // Last 10 sessions
        let weightedScore = 0;
        let totalWeight = 0;
        
        recentHistory.forEach((performance, index) => {
            const weight = (index + 1) / recentHistory.length; // More weight to recent sessions
            const performanceScore = (
                performance.success_rate +
                performance.engagement_score +
                performance.rules_accuracy +
                performance.teamwork_rating
            ) / 4;
            
            weightedScore += performanceScore * weight;
            totalWeight += weight;
        });
        
        const averagePerformance = totalWeight > 0 ? weightedScore / totalWeight : 0.5;
        
        // Map to complexity levels
        if (averagePerformance < 0.3) return 'beginner';
        if (averagePerformance < 0.6) return 'intermediate';
        if (averagePerformance < 0.8) return 'advanced';
        return 'expert';
    }

    async _analyzePerformanceMetrics(playerId, playerHistory) {
        const history = playerHistory.performance_history;
        
        if (history.length === 0) {
            return {
                average_success_rate: 0.5,
                engagement_trend: 'stable',
                skill_progression: 'unknown',
                consistency_score: 0.5
            };
        }
        
        // Calculate metrics
        const avgSuccessRate = history.reduce((sum, p) => sum + p.success_rate, 0) / history.length;
        const avgEngagement = history.reduce((sum, p) => sum + p.engagement_score, 0) / history.length;
        
        // Analyze trends
        const engagementTrend = this._calculateTrend(history.map(p => p.engagement_score));
        const skillProgression = this._calculateSkillProgression(history);
        const consistencyScore = this._calculateConsistency(history);
        
        return {
            average_success_rate: avgSuccessRate,
            average_engagement: avgEngagement,
            engagement_trend: engagementTrend,
            skill_progression: skillProgression,
            consistency_score: consistencyScore,
            session_count: history.length
        };
    }

    _analyzeLearningTrajectory(playerHistory) {
        const history = playerHistory.performance_history;
        
        if (history.length < 3) {
            return { trajectory: 'insufficient_data', confidence: 0.1 };
        }
        
        // Analyze improvement rate over time
        const earlyPerformance = history.slice(0, Math.floor(history.length / 3));
        const recentPerformance = history.slice(-Math.floor(history.length / 3));
        
        const earlyAvg = this._calculateAveragePerformance(earlyPerformance);
        const recentAvg = this._calculateAveragePerformance(recentPerformance);
        
        const improvement = recentAvg - earlyAvg;
        
        let trajectory;
        if (improvement > 0.2) trajectory = 'rapid_improvement';
        else if (improvement > 0.05) trajectory = 'steady_improvement';
        else if (improvement > -0.05) trajectory = 'stable';
        else if (improvement > -0.2) trajectory = 'slight_decline';
        else trajectory = 'significant_decline';
        
        return {
            trajectory: trajectory,
            improvement_rate: improvement,
            confidence: Math.min(history.length / 10, 1.0), // More confident with more data
            projected_complexity: this._projectComplexityProgression(trajectory, improvement)
        };
    }

    async _generateRecommendations(playerId, playerHistory) {
        const recommendations = [];
        
        // Analyze current performance
        const recentPerformance = playerHistory.performance_history.slice(-5);
        const avgPerformance = this._calculateAveragePerformance(recentPerformance);
        
        // Performance-based recommendations
        if (avgPerformance < 0.4) {
            recommendations.push({
                type: 'difficulty_reduction',
                priority: 'high',
                description: 'Reduce encounter complexity to build confidence',
                specific_actions: [
                    'Use simpler enemy stat blocks',
                    'Provide more obvious solutions to problems',
                    'Increase success opportunities',
                    'Offer more guidance and hints'
                ]
            });
        } else if (avgPerformance > 0.8) {
            recommendations.push({
                type: 'difficulty_increase',
                priority: 'medium',
                description: 'Increase challenge to maintain engagement',
                specific_actions: [
                    'Add tactical complexity to encounters',
                    'Introduce multi-layered problems',
                    'Reduce obvious solution paths',
                    'Add time pressure or resource constraints'
                ]
            });
        }
        
        // Engagement-based recommendations
        const engagementTrend = this._calculateTrend(recentPerformance.map(p => p.engagement_score));
        if (engagementTrend < -0.1) {
            recommendations.push({
                type: 'engagement_boost',
                priority: 'high',
                description: 'Address declining engagement',
                specific_actions: [
                    'Incorporate player character backgrounds',
                    'Offer more player agency in story direction',
                    'Vary encounter types and challenges',
                    'Create memorable NPC interactions'
                ]
            });
        }
        
        return recommendations;
    }

    async _analyzeGroupComplexity(players, currentSession) {
        const playerAssessments = [];
        
        // Get assessments for all players
        for (const playerId of players) {
            try {
                const assessmentData = await this.redis.get(`player_assessment:${playerId}`);
                if (assessmentData) {
                    playerAssessments.push(JSON.parse(assessmentData));
                }
            } catch (error) {
                this.logger.warn(`Could not get assessment for player ${playerId}`);
            }
        }
        
        if (playerAssessments.length === 0) {
            return {
                recommended_level: 'intermediate',
                skill_distribution: 'unknown',
                group_dynamics: 'balanced'
            };
        }
        
        // Analyze group composition
        const complexityLevels = playerAssessments.map(a => a.current_complexity_level);
        const skillVariance = this._calculateSkillVariance(playerAssessments);
        
        // Determine recommended group level
        const groupLevel = this._calculateGroupComplexityLevel(complexityLevels, skillVariance);
        
        return {
            recommended_level: groupLevel,
            skill_distribution: this._categorizeSkillDistribution(skillVariance),
            group_dynamics: this._analyzeGroupDynamics(playerAssessments),
            individual_needs: this._identifyIndividualNeeds(playerAssessments, groupLevel),
            balancing_strategies: this._generateBalancingStrategies(playerAssessments, groupLevel)
        };
    }

    async _calculateIndividualAdjustments(players, groupAnalysis) {
        const adjustments = {};
        
        for (const playerId of players) {
            const assessment = await this.redis.get(`player_assessment:${playerId}`);
            if (assessment) {
                const playerData = JSON.parse(assessment);
                
                adjustments[playerId] = {
                    complexity_offset: this._calculateComplexityOffset(playerData, groupAnalysis),
                    focus_areas: this._identifyFocusAreas(playerData),
                    support_level: this._calculateSupportLevel(playerData, groupAnalysis),
                    growth_targets: this._setGrowthTargets(playerData)
                };
            }
        }
        
        return adjustments;
    }

    _generateEncounterAdjustments(groupAnalysis) {
        const level = groupAnalysis.recommended_level;
        const scaling = this.complexityScaling.encounters[level];
        
        return {
            enemy_scaling: {
                count_modifier: this._getCountModifier(level),
                complexity_rating: scaling.enemy_complexity,
                tactical_sophistication: scaling.tactics
            },
            environmental_factors: {
                terrain_complexity: scaling.terrain,
                objective_variety: scaling.objectives
            },
            adaptation_guidelines: this._generateEncounterAdaptationGuidelines(level)
        };
    }

    _generateSocialAdjustments(groupAnalysis) {
        const level = groupAnalysis.recommended_level;
        const scaling = this.complexityScaling.social_encounters[level];
        
        return {
            npc_complexity: scaling.npc_motivations,
            consequence_depth: scaling.consequences,
            information_accessibility: scaling.information_gathering,
            relationship_mechanics: scaling.relationship_tracking
        };
    }

    _generateExplorationAdjustments(groupAnalysis) {
        const level = groupAnalysis.recommended_level;
        const scaling = this.complexityScaling.exploration[level];
        
        return {
            navigation_complexity: scaling.navigation,
            discovery_difficulty: scaling.discovery,
            environmental_challenges: scaling.environmental_challenges,
            resource_management: scaling.resource_management
        };
    }

    _generateDMGuidance(groupAnalysis) {
        return {
            pacing_advice: this._generatePacingAdvice(groupAnalysis),
            player_management: this._generatePlayerManagementAdvice(groupAnalysis),
            difficulty_indicators: this._generateDifficultyIndicators(groupAnalysis),
            real_time_adjustments: this._generateRealTimeAdjustmentGuidance(groupAnalysis)
        };
    }

    // Helper methods for calculations and analysis
    _getIndicatorWeight(indicator, performance) {
        // More recent performances have higher weight
        const recencyBonus = 1.0;
        const baseWeight = 1.0;
        
        // High-engagement sessions provide better evidence
        const engagementBonus = performance.engagement_score * 0.5;
        
        return baseWeight + engagementBonus + recencyBonus;
    }

    _calculateCategoryConfidence(evidenceCount, totalSessions) {
        if (totalSessions === 0) return 0.1;
        
        const evidenceRatio = evidenceCount / totalSessions;
        return Math.min(evidenceRatio * 2, 1.0); // Cap at 100%
    }

    _calculateSkillTrend(categoryId, performanceHistory) {
        // Simplified trend calculation
        if (performanceHistory.length < 3) return 'stable';
        
        const recent = performanceHistory.slice(-3);
        const earlier = performanceHistory.slice(0, 3);
        
        const recentScore = recent.filter(p => 
            p.skills_demonstrated.some(skill => 
                this.skillCategories[categoryId].indicators.includes(skill)
            )
        ).length;
        
        const earlierScore = earlier.filter(p => 
            p.skills_demonstrated.some(skill => 
                this.skillCategories[categoryId].indicators.includes(skill)
            )
        ).length;
        
        if (recentScore > earlierScore) return 'improving';
        if (recentScore < earlierScore) return 'declining';
        return 'stable';
    }

    _identifyGrowthOpportunities(categoryId, currentScore) {
        const category = this.skillCategories[categoryId];
        const opportunities = [];
        
        if (currentScore < 0.7) {
            opportunities.push(`Focus on ${category.complexity_factors[0]}`);
        }
        
        if (currentScore < 0.5) {
            opportunities.push(`Practice ${category.indicators[0]}`);
        }
        
        return opportunities;
    }

    _calculateTrend(values) {
        if (values.length < 2) return 0;
        
        let trend = 0;
        for (let i = 1; i < values.length; i++) {
            trend += values[i] - values[i-1];
        }
        
        return trend / (values.length - 1);
    }

    _calculateSkillProgression(history) {
        // Simplified skill progression calculation
        const totalSkillsDemonstrated = history.reduce((sum, p) => sum + p.skills_demonstrated.length, 0);
        const averageSkillsPerSession = totalSkillsDemonstrated / history.length;
        
        if (averageSkillsPerSession > 3) return 'rapid';
        if (averageSkillsPerSession > 2) return 'steady';
        if (averageSkillsPerSession > 1) return 'gradual';
        return 'slow';
    }

    _calculateConsistency(history) {
        if (history.length < 2) return 0.5;
        
        const scores = history.map(p => (p.success_rate + p.engagement_score + p.rules_accuracy) / 3);
        const mean = scores.reduce((sum, score) => sum + score, 0) / scores.length;
        const variance = scores.reduce((sum, score) => sum + Math.pow(score - mean, 2), 0) / scores.length;
        
        // Lower variance = higher consistency
        return Math.max(0, 1 - variance);
    }

    _calculateAveragePerformance(performances) {
        if (performances.length === 0) return 0.5;
        
        const totalScore = performances.reduce((sum, p) => {
            return sum + (p.success_rate + p.engagement_score + p.rules_accuracy + p.teamwork_rating) / 4;
        }, 0);
        
        return totalScore / performances.length;
    }

    _projectComplexityProgression(trajectory, improvementRate) {
        const projectionMap = {
            'rapid_improvement': 'advanced',
            'steady_improvement': 'intermediate_to_advanced',
            'stable': 'maintain_current',
            'slight_decline': 'reduce_slightly',
            'significant_decline': 'reduce_significantly'
        };
        
        return projectionMap[trajectory] || 'maintain_current';
    }

    _shouldTriggerAssessment(playerId, trackingEntry, history) {
        // Trigger assessment every 5 sessions
        if (history.length % 5 === 0) return true;
        
        // Trigger if performance significantly changes
        if (history.length >= 3) {
            const recent = history.slice(-3);
            const avgRecentPerformance = this._calculateAveragePerformance(recent);
            const currentPerformance = (trackingEntry.success_rate + trackingEntry.engagement_score) / 2;
            
            if (Math.abs(avgRecentPerformance - currentPerformance) > 0.3) return true;
        }
        
        return false;
    }

    _calculateAssessmentConfidence(playerHistory) {
        const sessionCount = playerHistory.total_sessions;
        
        if (sessionCount < 3) return 0.3;
        if (sessionCount < 10) return 0.6;
        if (sessionCount < 20) return 0.8;
        return 0.95;
    }

    _calculateNextAssessmentDate(playerHistory) {
        const now = new Date();
        const daysToAdd = Math.min(14, Math.max(3, playerHistory.total_sessions)); // 3-14 days based on experience
        
        return new Date(now.getTime() + (daysToAdd * 24 * 60 * 60 * 1000));
    }

    async _updatePlayerProfile(playerId, assessment) {
        const profile = {
            player_id: playerId,
            last_updated: new Date(),
            complexity_level: assessment.current_complexity_level,
            skill_scores: assessment.skill_scores,
            learning_trajectory: assessment.learning_trajectory,
            next_assessment_due: assessment.next_assessment_due
        };
        
        await this.redis.setex(
            `player_profile:${playerId}`,
            86400 * 30, // 30 days
            JSON.stringify(profile)
        );
    }

    // Additional helper methods would be implemented here...
    _findFirstSession(performanceHistory) {
        return performanceHistory.length > 0 ? performanceHistory[0].timestamp : null;
    }

    _calculateSkillVariance(playerAssessments) {
        // Simplified variance calculation
        return playerAssessments.length > 1 ? 'varied' : 'uniform';
    }

    _categorizeSkillDistribution(variance) {
        return variance === 'varied' ? 'mixed_skill_levels' : 'similar_skill_levels';
    }

    _calculateGroupComplexityLevel(complexityLevels, skillVariance) {
        const levelMap = { beginner: 1, intermediate: 2, advanced: 3, expert: 4 };
        const numericLevels = complexityLevels.map(level => levelMap[level] || 2);
        const avgLevel = numericLevels.reduce((sum, level) => sum + level, 0) / numericLevels.length;
        
        if (avgLevel < 1.5) return 'beginner';
        if (avgLevel < 2.5) return 'intermediate';
        if (avgLevel < 3.5) return 'advanced';
        return 'expert';
    }

    async getStats() {
        try {
            const assessmentKeys = await this.redis.keys('player_assessment:*');
            const adjustmentKeys = await this.redis.keys('complexity_adjustment:*');
            
            let complexityDistribution = {};
            let avgAssessmentScore = 0;
            
            for (const key of assessmentKeys.slice(0, 100)) {
                const data = await this.redis.get(key);
                if (data) {
                    const assessment = JSON.parse(data);
                    const level = assessment.current_complexity_level;
                    complexityDistribution[level] = (complexityDistribution[level] || 0) + 1;
                    
                    // Calculate average skill score
                    const skillScores = Object.values(assessment.skill_scores);
                    if (skillScores.length > 0) {
                        const avgSkillScore = skillScores.reduce((sum, skill) => sum + skill.score, 0) / skillScores.length;
                        avgAssessmentScore += avgSkillScore;
                    }
                }
            }
            
            return {
                total_assessments: assessmentKeys.length,
                total_adjustments: adjustmentKeys.length,
                complexity_distribution: complexityDistribution,
                average_skill_score: assessmentKeys.length > 0 ? avgAssessmentScore / assessmentKeys.length : 0,
                active_tracking: 0 // Could implement active session tracking
            };
            
        } catch (error) {
            this.logger.error('Error getting complexity system stats:', error);
            return {
                total_assessments: 0,
                total_adjustments: 0,
                complexity_distribution: {},
                average_skill_score: 0,
                active_tracking: 0
            };
        }
    }

    // Stub methods for remaining functionality
    _analyzeGroupDynamics(assessments) { return 'collaborative'; }
    _identifyIndividualNeeds(assessments, groupLevel) { return []; }
    _generateBalancingStrategies(assessments, groupLevel) { return []; }
    _calculateComplexityOffset(playerData, groupAnalysis) { return 0; }
    _identifyFocusAreas(playerData) { return []; }
    _calculateSupportLevel(playerData, groupAnalysis) { return 'standard'; }
    _setGrowthTargets(playerData) { return []; }
    _getCountModifier(level) { return 1.0; }
    _generateEncounterAdaptationGuidelines(level) { return []; }
    _generatePacingAdvice(groupAnalysis) { return 'Standard pacing recommended'; }
    _generatePlayerManagementAdvice(groupAnalysis) { return []; }
    _generateDifficultyIndicators(groupAnalysis) { return []; }
    _generateRealTimeAdjustmentGuidance(groupAnalysis) { return []; }
    _generateRealTimeSuggestions(groupAnalysis) { return []; }
    _defineSuccessIndicators(groupAnalysis) { return []; }
    _defineAdjustmentTriggers(groupAnalysis) { return []; }
    async _applyAdjustments(adjustments, currentSession) { return; }
}

module.exports = ProgressiveComplexitySystem;