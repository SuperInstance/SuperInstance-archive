import EventEmitter from 'events';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default class ReputationSystem extends EventEmitter {
    constructor(logger) {
        super();
        this.logger = logger;
        this.reputationScores = new Map();
        this.transactionHistory = new Map();
        this.reviewSystem = new Map();
        this.performanceMetrics = new Map();
        this.trustFactors = new Map();
        this.penaltySystem = new Map();
        this.rewardSystem = new Map();
        this.verificationSystem = new Map();
        this.badgeSystem = new Map();
        this.communityFeedback = new Map();
        this.fraudDetection = new Map();
        
        this.initializeReputationSystem();
        this.initializeTrustFactors();
        this.initializeBadgeSystem();
        this.initializeFraudDetection();
    }

    async initializeReputationSystem() {
        try {
            // Load existing reputation data
            const reputationPath = path.join(__dirname, '../data/reputation-data.json');
            const reputationData = await fs.readFile(reputationPath, 'utf8');
            const data = JSON.parse(reputationData);
            
            for (const entity of data.entities) {
                this.reputationScores.set(entity.id, entity.reputation);
                this.performanceMetrics.set(entity.id, entity.metrics);
                this.transactionHistory.set(entity.id, entity.transactions || []);
            }
            
            this.logger.info(`Loaded reputation data for ${data.entities.length} entities`);
        } catch (error) {
            this.logger.warn('Could not load reputation data, initializing with defaults');
            this.initializeDefaultReputationData();
        }
    }

    initializeDefaultReputationData() {
        // Initialize with sample reputation data for vendors and assemblers
        const defaultEntities = [
            {
                id: 'techparts_direct',
                type: 'vendor',
                reputation: {
                    overall_score: 4.7,
                    trust_level: 'high',
                    transaction_count: 1250,
                    success_rate: 0.96,
                    response_time_avg: 2.3,
                    quality_score: 4.8,
                    reliability_score: 4.6,
                    communication_score: 4.7,
                    last_updated: new Date('2024-01-15')
                },
                metrics: {
                    on_time_delivery: 0.94,
                    order_accuracy: 0.98,
                    defect_rate: 0.02,
                    customer_satisfaction: 4.7,
                    return_rate: 0.03,
                    dispute_resolution: 0.89
                }
            },
            {
                id: 'assembler_001',
                type: 'assembler',
                reputation: {
                    overall_score: 4.8,
                    trust_level: 'high',
                    transaction_count: 845,
                    success_rate: 0.97,
                    response_time_avg: 1.8,
                    quality_score: 4.9,
                    reliability_score: 4.7,
                    communication_score: 4.8,
                    last_updated: new Date('2024-01-20')
                },
                metrics: {
                    project_completion_rate: 0.97,
                    quality_rating: 4.9,
                    timeline_adherence: 0.92,
                    customer_satisfaction: 4.8,
                    rework_rate: 0.05,
                    technical_expertise: 4.7
                }
            }
        ];

        defaultEntities.forEach(entity => {
            this.reputationScores.set(entity.id, entity.reputation);
            this.performanceMetrics.set(entity.id, entity.metrics);
            this.transactionHistory.set(entity.id, []);
        });
    }

    initializeTrustFactors() {
        // Define trust factors and their weights for reputation calculation
        this.trustFactors.set('transaction_success', {
            weight: 0.25,
            description: 'Successful completion of transactions',
            calculation: (metrics) => metrics.success_rate || 0.8
        });

        this.trustFactors.set('quality_consistency', {
            weight: 0.20,
            description: 'Consistent quality delivery',
            calculation: (metrics) => (metrics.quality_score || 4.0) / 5.0
        });

        this.trustFactors.set('reliability', {
            weight: 0.20,
            description: 'On-time delivery and promise keeping',
            calculation: (metrics) => metrics.on_time_delivery || metrics.timeline_adherence || 0.85
        });

        this.trustFactors.set('communication', {
            weight: 0.15,
            description: 'Response time and communication quality',
            calculation: (metrics) => {
                const responseScore = Math.max(0, 1 - ((metrics.response_time_avg || 24) / 48));
                return (responseScore + ((metrics.communication_score || 4.0) / 5.0)) / 2;
            }
        });

        this.trustFactors.set('customer_satisfaction', {
            weight: 0.15,
            description: 'Overall customer satisfaction ratings',
            calculation: (metrics) => (metrics.customer_satisfaction || 4.0) / 5.0
        });

        this.trustFactors.set('dispute_resolution', {
            weight: 0.05,
            description: 'Ability to resolve disputes fairly',
            calculation: (metrics) => metrics.dispute_resolution || 0.8
        });
    }

    initializeBadgeSystem() {
        const badges = [
            {
                id: 'trusted_vendor',
                name: 'Trusted Vendor',
                description: 'Consistently high performance and customer satisfaction',
                criteria: {
                    min_transactions: 100,
                    min_overall_score: 4.5,
                    min_success_rate: 0.95,
                    max_dispute_rate: 0.02
                },
                tier: 'gold',
                benefits: ['priority_listing', 'reduced_fees', 'trust_indicator']
            },
            {
                id: 'quality_specialist',
                name: 'Quality Specialist',
                description: 'Exceptional quality in products and services',
                criteria: {
                    min_quality_score: 4.7,
                    max_defect_rate: 0.01,
                    max_return_rate: 0.02,
                    min_transactions: 50
                },
                tier: 'gold',
                benefits: ['quality_badge', 'enhanced_visibility']
            },
            {
                id: 'fast_responder',
                name: 'Fast Responder',
                description: 'Quick response times and excellent communication',
                criteria: {
                    max_response_time: 2.0,
                    min_communication_score: 4.5,
                    min_transactions: 25
                },
                tier: 'silver',
                benefits: ['response_time_badge', 'communication_highlight']
            },
            {
                id: 'innovation_leader',
                name: 'Innovation Leader',
                description: 'Leading edge technology and innovative solutions',
                criteria: {
                    innovation_projects: 10,
                    technology_rating: 4.5,
                    custom_solutions: 0.3
                },
                tier: 'platinum',
                benefits: ['innovation_showcase', 'priority_matching']
            },
            {
                id: 'eco_friendly',
                name: 'Eco-Friendly Partner',
                description: 'Commitment to environmental sustainability',
                criteria: {
                    carbon_neutral: true,
                    recycling_program: true,
                    green_certifications: 2
                },
                tier: 'green',
                benefits: ['eco_badge', 'sustainability_highlighting']
            },
            {
                id: 'volume_expert',
                name: 'Volume Production Expert',
                description: 'Specialized in high-volume manufacturing',
                criteria: {
                    min_volume_capacity: 100000,
                    volume_projects: 20,
                    volume_quality_score: 4.6
                },
                tier: 'silver',
                benefits: ['volume_specialist_badge', 'bulk_order_priority']
            },
            {
                id: 'prototype_master',
                name: 'Prototype Master',
                description: 'Expert in rapid prototyping and development',
                criteria: {
                    prototype_projects: 50,
                    avg_prototype_time: 3,
                    prototype_success_rate: 0.95
                },
                tier: 'silver',
                benefits: ['prototype_badge', 'rapid_development_highlight']
            }
        ];

        badges.forEach(badge => {
            this.badgeSystem.set(badge.id, badge);
        });
    }

    initializeFraudDetection() {
        this.fraudDetection.set('behavioral_analysis', {
            enabled: true,
            patterns: [
                'rapid_score_changes',
                'review_manipulation',
                'fake_transactions',
                'identity_inconsistency'
            ],
            threshold: 0.7
        });

        this.fraudDetection.set('verification_checks', {
            enabled: true,
            checks: [
                'business_registration',
                'tax_id_verification',
                'address_verification',
                'phone_verification',
                'email_verification'
            ]
        });
    }

    async updateReputation(entityId, transactionData, reviewData = null) {
        try {
            // Record the transaction
            await this.recordTransaction(entityId, transactionData);

            // Update performance metrics
            await this.updatePerformanceMetrics(entityId, transactionData);

            // Process review if provided
            if (reviewData) {
                await this.processReview(entityId, reviewData);
            }

            // Recalculate reputation score
            const newReputation = await this.calculateReputationScore(entityId);

            // Update reputation data
            this.reputationScores.set(entityId, {
                ...this.reputationScores.get(entityId),
                ...newReputation,
                last_updated: new Date()
            });

            // Check for badge eligibility
            await this.evaluateBadgeEligibility(entityId);

            // Run fraud detection
            await this.runFraudDetection(entityId, transactionData);

            this.emit('reputation_updated', {
                entity_id: entityId,
                new_score: newReputation.overall_score,
                transaction_id: transactionData.transaction_id
            });

            this.logger.info(`Reputation updated for ${entityId}: ${newReputation.overall_score}`);

            return newReputation;

        } catch (error) {
            this.logger.error('Reputation update failed:', error);
            throw error;
        }
    }

    async recordTransaction(entityId, transactionData) {
        const history = this.transactionHistory.get(entityId) || [];
        
        const transactionRecord = {
            transaction_id: transactionData.transaction_id,
            timestamp: new Date(),
            type: transactionData.type, // 'sale', 'assembly', 'service'
            amount: transactionData.amount,
            success: transactionData.success,
            completion_time: transactionData.completion_time,
            quality_rating: transactionData.quality_rating,
            customer_id: transactionData.customer_id,
            product_category: transactionData.product_category,
            complexity: transactionData.complexity,
            issues: transactionData.issues || [],
            resolution_time: transactionData.resolution_time,
            customer_feedback: transactionData.customer_feedback
        };

        history.push(transactionRecord);

        // Keep only last 1000 transactions to prevent memory issues
        if (history.length > 1000) {
            history.splice(0, history.length - 1000);
        }

        this.transactionHistory.set(entityId, history);
    }

    async updatePerformanceMetrics(entityId, transactionData) {
        const currentMetrics = this.performanceMetrics.get(entityId) || {};
        const history = this.transactionHistory.get(entityId) || [];
        
        // Calculate updated metrics based on recent transaction history
        const recentTransactions = history.slice(-100); // Last 100 transactions
        
        const updatedMetrics = {
            ...currentMetrics,
            success_rate: this.calculateSuccessRate(recentTransactions),
            on_time_delivery: this.calculateOnTimeDelivery(recentTransactions),
            order_accuracy: this.calculateOrderAccuracy(recentTransactions),
            quality_score: this.calculateAverageQuality(recentTransactions),
            customer_satisfaction: this.calculateCustomerSatisfaction(recentTransactions),
            defect_rate: this.calculateDefectRate(recentTransactions),
            return_rate: this.calculateReturnRate(recentTransactions),
            response_time_avg: this.calculateAverageResponseTime(recentTransactions),
            dispute_resolution: this.calculateDisputeResolution(recentTransactions),
            last_calculated: new Date()
        };

        this.performanceMetrics.set(entityId, updatedMetrics);
        return updatedMetrics;
    }

    calculateSuccessRate(transactions) {
        if (transactions.length === 0) return 0.8;
        const successfulTransactions = transactions.filter(t => t.success).length;
        return successfulTransactions / transactions.length;
    }

    calculateOnTimeDelivery(transactions) {
        if (transactions.length === 0) return 0.85;
        const onTimeTransactions = transactions.filter(t => 
            t.completion_time && t.completion_time <= (t.promised_time || t.expected_time || Infinity)
        ).length;
        return onTimeTransactions / transactions.length;
    }

    calculateOrderAccuracy(transactions) {
        if (transactions.length === 0) return 0.95;
        const accurateOrders = transactions.filter(t => 
            !t.issues || !t.issues.includes('wrong_item') && !t.issues.includes('missing_item')
        ).length;
        return accurateOrders / transactions.length;
    }

    calculateAverageQuality(transactions) {
        if (transactions.length === 0) return 4.0;
        const qualityRatings = transactions
            .filter(t => t.quality_rating)
            .map(t => t.quality_rating);
        
        if (qualityRatings.length === 0) return 4.0;
        return qualityRatings.reduce((sum, rating) => sum + rating, 0) / qualityRatings.length;
    }

    calculateCustomerSatisfaction(transactions) {
        if (transactions.length === 0) return 4.0;
        const satisfactionRatings = transactions
            .filter(t => t.customer_feedback && t.customer_feedback.satisfaction_rating)
            .map(t => t.customer_feedback.satisfaction_rating);
        
        if (satisfactionRatings.length === 0) return 4.0;
        return satisfactionRatings.reduce((sum, rating) => sum + rating, 0) / satisfactionRatings.length;
    }

    calculateDefectRate(transactions) {
        if (transactions.length === 0) return 0.02;
        const defectiveTransactions = transactions.filter(t => 
            t.issues && (t.issues.includes('defective') || t.issues.includes('quality_issue'))
        ).length;
        return defectiveTransactions / transactions.length;
    }

    calculateReturnRate(transactions) {
        if (transactions.length === 0) return 0.03;
        const returnedTransactions = transactions.filter(t => 
            t.issues && t.issues.includes('returned')
        ).length;
        return returnedTransactions / transactions.length;
    }

    calculateAverageResponseTime(transactions) {
        if (transactions.length === 0) return 4.0;
        const responseTimes = transactions
            .filter(t => t.response_time)
            .map(t => t.response_time);
        
        if (responseTimes.length === 0) return 4.0;
        return responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length;
    }

    calculateDisputeResolution(transactions) {
        if (transactions.length === 0) return 0.85;
        const disputeTransactions = transactions.filter(t => 
            t.issues && t.issues.length > 0
        );
        
        if (disputeTransactions.length === 0) return 1.0;
        
        const resolvedDisputes = disputeTransactions.filter(t => 
            t.resolution_time && t.resolution_time < 72 // Resolved within 72 hours
        ).length;
        
        return resolvedDisputes / disputeTransactions.length;
    }

    async processReview(entityId, reviewData) {
        const reviews = this.reviewSystem.get(entityId) || [];
        
        // Validate review
        const validatedReview = await this.validateReview(reviewData);
        if (!validatedReview.valid) {
            this.logger.warn(`Invalid review for ${entityId}: ${validatedReview.reason}`);
            return;
        }

        const reviewRecord = {
            review_id: this.generateReviewId(),
            reviewer_id: reviewData.reviewer_id,
            timestamp: new Date(),
            rating: reviewData.rating,
            category_ratings: reviewData.category_ratings || {},
            comment: reviewData.comment,
            transaction_id: reviewData.transaction_id,
            verified_purchase: reviewData.verified_purchase || false,
            helpful_votes: 0,
            reported_count: 0,
            moderation_status: 'approved'
        };

        reviews.push(reviewRecord);

        // Keep only last 500 reviews
        if (reviews.length > 500) {
            reviews.splice(0, reviews.length - 500);
        }

        this.reviewSystem.set(entityId, reviews);

        // Update aggregated review metrics
        await this.updateReviewMetrics(entityId);
    }

    async validateReview(reviewData) {
        const validation = { valid: true, reason: null };

        // Check for required fields
        if (!reviewData.reviewer_id || !reviewData.rating || !reviewData.transaction_id) {
            validation.valid = false;
            validation.reason = 'Missing required fields';
            return validation;
        }

        // Check rating range
        if (reviewData.rating < 1 || reviewData.rating > 5) {
            validation.valid = false;
            validation.reason = 'Invalid rating range';
            return validation;
        }

        // Check for spam or inappropriate content
        if (await this.detectInappropriateContent(reviewData.comment)) {
            validation.valid = false;
            validation.reason = 'Inappropriate content detected';
            return validation;
        }

        // Check for review manipulation
        if (await this.detectReviewManipulation(reviewData)) {
            validation.valid = false;
            validation.reason = 'Potential review manipulation';
            return validation;
        }

        return validation;
    }

    async detectInappropriateContent(comment) {
        if (!comment) return false;
        
        // Simple keyword-based detection (in production, use ML-based content moderation)
        const inappropriateKeywords = [
            'spam', 'fake', 'scam', 'cheat', 'fraud'
        ];
        
        const lowerComment = comment.toLowerCase();
        return inappropriateKeywords.some(keyword => lowerComment.includes(keyword));
    }

    async detectReviewManipulation(reviewData) {
        // Check for patterns that might indicate manipulation
        const reviewerHistory = await this.getReviewerHistory(reviewData.reviewer_id);
        
        // Multiple reviews in short time period
        if (reviewerHistory.length > 5) {
            const recentReviews = reviewerHistory.filter(r => 
                (new Date() - new Date(r.timestamp)) < 24 * 60 * 60 * 1000 // Last 24 hours
            );
            if (recentReviews.length > 3) return true;
        }

        // Always same rating
        if (reviewerHistory.length > 3) {
            const allSameRating = reviewerHistory.every(r => r.rating === reviewerHistory[0].rating);
            if (allSameRating) return true;
        }

        return false;
    }

    async getReviewerHistory(reviewerId) {
        // Mock reviewer history - in production, query database
        return [
            { rating: 5, timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000) },
            { rating: 5, timestamp: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000) }
        ];
    }

    async updateReviewMetrics(entityId) {
        const reviews = this.reviewSystem.get(entityId) || [];
        if (reviews.length === 0) return;

        const metrics = {
            total_reviews: reviews.length,
            average_rating: reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length,
            rating_distribution: this.calculateRatingDistribution(reviews),
            recent_trend: this.calculateRecentTrend(reviews),
            verified_review_percentage: this.calculateVerifiedReviewPercentage(reviews),
            response_rate: this.calculateReviewResponseRate(entityId)
        };

        // Update reputation score with review metrics
        const currentReputation = this.reputationScores.get(entityId) || {};
        currentReputation.review_metrics = metrics;
        this.reputationScores.set(entityId, currentReputation);
    }

    calculateRatingDistribution(reviews) {
        const distribution = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
        reviews.forEach(review => {
            distribution[review.rating]++;
        });
        
        // Convert to percentages
        Object.keys(distribution).forEach(rating => {
            distribution[rating] = (distribution[rating] / reviews.length) * 100;
        });
        
        return distribution;
    }

    calculateRecentTrend(reviews) {
        const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        const recentReviews = reviews.filter(r => new Date(r.timestamp) > thirtyDaysAgo);
        const olderReviews = reviews.filter(r => new Date(r.timestamp) <= thirtyDaysAgo);
        
        if (recentReviews.length === 0 || olderReviews.length === 0) {
            return { trend: 'stable', change: 0 };
        }

        const recentAverage = recentReviews.reduce((sum, r) => sum + r.rating, 0) / recentReviews.length;
        const olderAverage = olderReviews.reduce((sum, r) => sum + r.rating, 0) / olderReviews.length;
        
        const change = recentAverage - olderAverage;
        
        return {
            trend: change > 0.1 ? 'improving' : change < -0.1 ? 'declining' : 'stable',
            change: parseFloat(change.toFixed(2))
        };
    }

    calculateVerifiedReviewPercentage(reviews) {
        const verifiedReviews = reviews.filter(r => r.verified_purchase).length;
        return (verifiedReviews / reviews.length) * 100;
    }

    calculateReviewResponseRate(entityId) {
        // Mock calculation - in production, track actual response rates
        return 0.75; // 75% response rate
    }

    async calculateReputationScore(entityId) {
        const currentReputation = this.reputationScores.get(entityId) || {};
        const metrics = this.performanceMetrics.get(entityId) || {};
        const reviews = this.reviewSystem.get(entityId) || [];

        let totalScore = 0;
        let totalWeight = 0;

        // Calculate score based on trust factors
        for (const [factorId, factor] of this.trustFactors) {
            const factorScore = factor.calculation(metrics);
            totalScore += factorScore * factor.weight;
            totalWeight += factor.weight;
        }

        // Normalize to 0-1 scale, then convert to 0-5 scale
        const baseScore = totalWeight > 0 ? (totalScore / totalWeight) * 5 : 2.5;

        // Apply review influence
        let reviewInfluence = 0;
        if (reviews.length > 0) {
            const avgReviewRating = reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length;
            const reviewWeight = Math.min(0.3, reviews.length / 100); // Max 30% influence, scales with review count
            reviewInfluence = avgReviewRating * reviewWeight;
        }

        // Apply penalties
        const penalties = await this.calculatePenalties(entityId);
        
        // Apply bonuses
        const bonuses = await this.calculateBonuses(entityId);

        // Calculate final score
        const finalScore = Math.max(0.1, Math.min(5.0, baseScore + reviewInfluence - penalties + bonuses));

        // Determine trust level
        const trustLevel = this.determineTrustLevel(finalScore, metrics);

        return {
            overall_score: parseFloat(finalScore.toFixed(2)),
            trust_level: trustLevel,
            quality_score: parseFloat((metrics.quality_score || 4.0).toFixed(2)),
            reliability_score: parseFloat(((metrics.on_time_delivery || 0.85) * 5).toFixed(2)),
            communication_score: parseFloat(((metrics.dispute_resolution || 0.8) * 5).toFixed(2)),
            transaction_count: currentReputation.transaction_count || 0,
            success_rate: parseFloat((metrics.success_rate || 0.8).toFixed(3)),
            response_time_avg: parseFloat((metrics.response_time_avg || 24).toFixed(1))
        };
    }

    determineTrustLevel(score, metrics) {
        const transactionCount = metrics.transaction_count || 0;
        
        if (score >= 4.5 && transactionCount >= 100) return 'excellent';
        if (score >= 4.0 && transactionCount >= 50) return 'high';
        if (score >= 3.5 && transactionCount >= 25) return 'good';
        if (score >= 3.0 && transactionCount >= 10) return 'fair';
        if (score >= 2.5) return 'developing';
        return 'poor';
    }

    async calculatePenalties(entityId) {
        let totalPenalties = 0;
        const history = this.transactionHistory.get(entityId) || [];
        const recentHistory = history.slice(-50); // Last 50 transactions

        // Late delivery penalty
        const lateDeliveries = recentHistory.filter(t => 
            t.completion_time > (t.promised_time || t.expected_time || Infinity)
        ).length;
        totalPenalties += (lateDeliveries / recentHistory.length) * 0.5;

        // Quality issue penalty
        const qualityIssues = recentHistory.filter(t => 
            t.issues && t.issues.includes('quality_issue')
        ).length;
        totalPenalties += (qualityIssues / recentHistory.length) * 0.7;

        // Dispute penalty
        const disputes = recentHistory.filter(t => 
            t.issues && t.issues.length > 0 && !t.resolution_time
        ).length;
        totalPenalties += (disputes / recentHistory.length) * 0.3;

        return Math.min(1.0, totalPenalties); // Cap at 1.0 point reduction
    }

    async calculateBonuses(entityId) {
        let totalBonuses = 0;
        const metrics = this.performanceMetrics.get(entityId) || {};

        // Excellence bonus for consistently high performance
        if (metrics.success_rate > 0.98 && metrics.quality_score > 4.8) {
            totalBonuses += 0.2;
        }

        // Fast response bonus
        if (metrics.response_time_avg < 2) {
            totalBonuses += 0.1;
        }

        // Customer loyalty bonus (repeat customers)
        const history = this.transactionHistory.get(entityId) || [];
        if (history.length > 0) {
            const uniqueCustomers = new Set(history.map(t => t.customer_id)).size;
            const repeatCustomerRate = 1 - (uniqueCustomers / history.length);
            if (repeatCustomerRate > 0.3) {
                totalBonuses += 0.15;
            }
        }

        return Math.min(0.5, totalBonuses); // Cap at 0.5 point increase
    }

    async evaluateBadgeEligibility(entityId) {
        const reputation = this.reputationScores.get(entityId);
        const metrics = this.performanceMetrics.get(entityId) || {};
        const history = this.transactionHistory.get(entityId) || [];
        const currentBadges = reputation?.badges || [];

        for (const [badgeId, badge] of this.badgeSystem) {
            // Skip if already has badge
            if (currentBadges.includes(badgeId)) continue;

            const eligible = await this.checkBadgeCriteria(badgeId, badge, reputation, metrics, history);
            
            if (eligible) {
                await this.awardBadge(entityId, badgeId);
            }
        }
    }

    async checkBadgeCriteria(badgeId, badge, reputation, metrics, history) {
        const criteria = badge.criteria;

        // Check transaction count
        if (criteria.min_transactions && history.length < criteria.min_transactions) {
            return false;
        }

        // Check overall score
        if (criteria.min_overall_score && reputation.overall_score < criteria.min_overall_score) {
            return false;
        }

        // Check success rate
        if (criteria.min_success_rate && metrics.success_rate < criteria.min_success_rate) {
            return false;
        }

        // Check quality score
        if (criteria.min_quality_score && metrics.quality_score < criteria.min_quality_score) {
            return false;
        }

        // Check defect rate
        if (criteria.max_defect_rate && metrics.defect_rate > criteria.max_defect_rate) {
            return false;
        }

        // Check return rate
        if (criteria.max_return_rate && metrics.return_rate > criteria.max_return_rate) {
            return false;
        }

        // Check response time
        if (criteria.max_response_time && metrics.response_time_avg > criteria.max_response_time) {
            return false;
        }

        // Check communication score
        if (criteria.min_communication_score && metrics.communication_score < criteria.min_communication_score) {
            return false;
        }

        // Check dispute rate
        if (criteria.max_dispute_rate) {
            const disputeRate = history.filter(t => t.issues && t.issues.length > 0).length / history.length;
            if (disputeRate > criteria.max_dispute_rate) {
                return false;
            }
        }

        // Additional criteria checks for specific badges
        return await this.checkSpecialBadgeCriteria(badgeId, criteria, metrics, history);
    }

    async checkSpecialBadgeCriteria(badgeId, criteria, metrics, history) {
        switch (badgeId) {
            case 'innovation_leader':
                // Mock innovation criteria check
                return criteria.innovation_projects <= 15 && 
                       criteria.technology_rating <= 4.5;

            case 'eco_friendly':
                // Mock eco-friendly criteria check
                return criteria.carbon_neutral && criteria.recycling_program;

            case 'volume_expert':
                // Check volume capacity and projects
                return metrics.volume_capacity >= criteria.min_volume_capacity;

            case 'prototype_master':
                // Check prototype-specific metrics
                return metrics.prototype_success_rate >= criteria.prototype_success_rate;

            default:
                return true;
        }
    }

    async awardBadge(entityId, badgeId) {
        const reputation = this.reputationScores.get(entityId);
        const currentBadges = reputation.badges || [];
        
        currentBadges.push({
            badge_id: badgeId,
            awarded_date: new Date(),
            status: 'active'
        });

        reputation.badges = currentBadges;
        this.reputationScores.set(entityId, reputation);

        this.emit('badge_awarded', {
            entity_id: entityId,
            badge_id: badgeId,
            badge_name: this.badgeSystem.get(badgeId).name
        });

        this.logger.info(`Badge awarded: ${badgeId} to ${entityId}`);
    }

    async runFraudDetection(entityId, transactionData) {
        const fraudScore = await this.calculateFraudScore(entityId, transactionData);
        
        if (fraudScore > 0.7) {
            await this.flagForReview(entityId, 'high_fraud_risk', {
                fraud_score: fraudScore,
                transaction_id: transactionData.transaction_id,
                detected_patterns: await this.getDetectedPatterns(entityId)
            });
        }

        return fraudScore;
    }

    async calculateFraudScore(entityId, transactionData) {
        let fraudScore = 0;
        const history = this.transactionHistory.get(entityId) || [];
        const reputation = this.reputationScores.get(entityId) || {};

        // Rapid reputation changes
        if (reputation.recent_score_changes && reputation.recent_score_changes > 1.0) {
            fraudScore += 0.3;
        }

        // Unusual transaction patterns
        const recentTransactions = history.slice(-20);
        if (recentTransactions.length > 15) {
            const avgTransactionTime = recentTransactions.reduce((sum, t) => 
                sum + (t.completion_time || 24), 0) / recentTransactions.length;
            
            if (avgTransactionTime < 1) { // Suspiciously fast
                fraudScore += 0.4;
            }
        }

        // Review manipulation indicators
        const reviews = this.reviewSystem.get(entityId) || [];
        if (reviews.length > 0) {
            const recentReviews = reviews.filter(r => 
                (new Date() - new Date(r.timestamp)) < 7 * 24 * 60 * 60 * 1000
            );
            
            if (recentReviews.length > 10) {
                fraudScore += 0.2;
            }

            // All 5-star reviews
            const allFiveStars = reviews.every(r => r.rating === 5);
            if (allFiveStars && reviews.length > 20) {
                fraudScore += 0.3;
            }
        }

        return Math.min(1.0, fraudScore);
    }

    async getDetectedPatterns(entityId) {
        const patterns = [];
        const history = this.transactionHistory.get(entityId) || [];
        const reviews = this.reviewSystem.get(entityId) || [];

        // Pattern detection logic
        if (history.length > 50) {
            const recentSuccess = history.slice(-10).every(t => t.success);
            const overallSuccess = this.calculateSuccessRate(history);
            
            if (recentSuccess && overallSuccess < 0.7) {
                patterns.push('sudden_improvement');
            }
        }

        if (reviews.length > 20) {
            const allHighRatings = reviews.every(r => r.rating >= 4);
            if (allHighRatings) {
                patterns.push('suspiciously_high_reviews');
            }
        }

        return patterns;
    }

    async flagForReview(entityId, reason, details) {
        const flag = {
            entity_id: entityId,
            reason,
            details,
            timestamp: new Date(),
            status: 'pending_review',
            reviewer_assigned: null,
            resolution: null
        };

        // Store flag for manual review
        const entityFlags = this.fraudDetection.get(entityId) || [];
        entityFlags.push(flag);
        this.fraudDetection.set(entityId, entityFlags);

        this.emit('entity_flagged', flag);
        
        this.logger.warn(`Entity flagged for review: ${entityId} - ${reason}`);
    }

    async getReputationSummary(entityId) {
        const reputation = this.reputationScores.get(entityId);
        const metrics = this.performanceMetrics.get(entityId);
        const reviews = this.reviewSystem.get(entityId) || [];
        const history = this.transactionHistory.get(entityId) || [];

        if (!reputation) {
            throw new Error(`No reputation data found for entity: ${entityId}`);
        }

        return {
            entity_id: entityId,
            reputation_score: reputation,
            performance_metrics: metrics,
            review_summary: {
                total_reviews: reviews.length,
                average_rating: reviews.length > 0 ? 
                    reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length : 0,
                recent_reviews: reviews.slice(-5).map(r => ({
                    rating: r.rating,
                    comment: r.comment,
                    timestamp: r.timestamp
                }))
            },
            transaction_summary: {
                total_transactions: history.length,
                recent_performance: this.getRecentPerformanceTrend(history),
                success_streak: this.calculateSuccessStreak(history)
            },
            badges: reputation.badges || [],
            trust_indicators: this.getTrustIndicators(reputation, metrics),
            improvement_suggestions: await this.generateImprovementSuggestions(entityId)
        };
    }

    getRecentPerformanceTrend(history) {
        const recentTransactions = history.slice(-20);
        const olderTransactions = history.slice(-40, -20);

        const recentSuccess = this.calculateSuccessRate(recentTransactions);
        const olderSuccess = this.calculateSuccessRate(olderTransactions);

        const trend = recentSuccess - olderSuccess;

        return {
            direction: trend > 0.05 ? 'improving' : trend < -0.05 ? 'declining' : 'stable',
            change: parseFloat(trend.toFixed(3)),
            recent_success_rate: recentSuccess,
            period_compared: `Last ${recentTransactions.length} vs previous ${olderTransactions.length} transactions`
        };
    }

    calculateSuccessStreak(history) {
        let currentStreak = 0;
        for (let i = history.length - 1; i >= 0; i--) {
            if (history[i].success) {
                currentStreak++;
            } else {
                break;
            }
        }
        return currentStreak;
    }

    getTrustIndicators(reputation, metrics) {
        const indicators = [];

        if (reputation.transaction_count >= 100) {
            indicators.push({ type: 'experience', description: 'Extensive transaction history' });
        }

        if (metrics.success_rate >= 0.95) {
            indicators.push({ type: 'reliability', description: 'High success rate' });
        }

        if (metrics.quality_score >= 4.5) {
            indicators.push({ type: 'quality', description: 'Consistently high quality' });
        }

        if (metrics.response_time_avg <= 4) {
            indicators.push({ type: 'responsiveness', description: 'Fast response times' });
        }

        return indicators;
    }

    async generateImprovementSuggestions(entityId) {
        const reputation = this.reputationScores.get(entityId);
        const metrics = this.performanceMetrics.get(entityId);
        const suggestions = [];

        // Quality improvement
        if (metrics.quality_score < 4.0) {
            suggestions.push({
                area: 'quality',
                priority: 'high',
                suggestion: 'Implement quality control measures to improve product/service quality',
                impact: 'Could increase reputation score by 0.5-1.0 points'
            });
        }

        // Delivery improvement
        if (metrics.on_time_delivery < 0.85) {
            suggestions.push({
                area: 'delivery',
                priority: 'high',
                suggestion: 'Improve delivery time management and scheduling',
                impact: 'Better on-time delivery boosts reliability scores'
            });
        }

        // Communication improvement
        if (metrics.response_time_avg > 8) {
            suggestions.push({
                area: 'communication',
                priority: 'medium',
                suggestion: 'Reduce response times to customer inquiries',
                impact: 'Faster responses improve customer satisfaction'
            });
        }

        // Review engagement
        const reviews = this.reviewSystem.get(entityId) || [];
        if (reviews.length < 20 && reputation.transaction_count > 50) {
            suggestions.push({
                area: 'reviews',
                priority: 'medium',
                suggestion: 'Encourage satisfied customers to leave reviews',
                impact: 'More reviews increase trust and visibility'
            });
        }

        return suggestions;
    }

    // Utility methods
    generateReviewId() {
        return `review_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    async exportReputationReport(entityId, format = 'json') {
        const summary = await this.getReputationSummary(entityId);
        
        switch (format) {
            case 'csv':
                return this.exportToCSV(summary);
            case 'pdf':
                return this.exportToPDF(summary);
            default:
                return JSON.stringify(summary, null, 2);
        }
    }

    exportToCSV(summary) {
        // Mock CSV export
        const csvData = [
            'Metric,Value',
            `Overall Score,${summary.reputation_score.overall_score}`,
            `Trust Level,${summary.reputation_score.trust_level}`,
            `Total Transactions,${summary.transaction_summary.total_transactions}`,
            `Success Rate,${summary.reputation_score.success_rate}`,
            `Quality Score,${summary.reputation_score.quality_score}`,
            `Total Reviews,${summary.review_summary.total_reviews}`,
            `Average Review Rating,${summary.review_summary.average_rating.toFixed(2)}`
        ].join('\n');

        return csvData;
    }

    exportToPDF(summary) {
        // Mock PDF export
        return {
            format: 'pdf',
            filename: `reputation_report_${summary.entity_id}_${Date.now()}.pdf`,
            content: 'Mock PDF content'
        };
    }
}