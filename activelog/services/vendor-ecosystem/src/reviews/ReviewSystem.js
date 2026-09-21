import { EventEmitter } from 'events';
import { createHash } from 'crypto';

class ReviewSystem extends EventEmitter {
    constructor() {
        super();
        this.reviews = new Map();
        this.reviewCriteria = new Map();
        this.moderationQueue = [];
        this.reviewMetrics = {
            total_reviews: 0,
            average_rating: 0,
            verified_reviews: 0,
            flagged_reviews: 0
        };
        this.reviewTemplates = new Map();
        this.sentimentAnalysis = new Map();
        this.reviewIncentives = new Map();
        this.initializeReviewCriteria();
        this.initializeReviewTemplates();
    }

    initializeReviewCriteria() {
        const criteria = [
            {
                category: 'product_quality',
                weight: 0.3,
                aspects: ['durability', 'performance', 'design', 'materials']
            },
            {
                category: 'vendor_service',
                weight: 0.25,
                aspects: ['communication', 'delivery_speed', 'packaging', 'support']
            },
            {
                category: 'value_for_money',
                weight: 0.2,
                aspects: ['price_competitiveness', 'quality_ratio', 'warranty_value']
            },
            {
                category: 'compatibility',
                weight: 0.15,
                aspects: ['fit_accuracy', 'specification_match', 'integration_ease']
            },
            {
                category: 'documentation',
                weight: 0.1,
                aspects: ['instruction_clarity', 'technical_specs', 'installation_guides']
            }
        ];

        criteria.forEach(criterion => {
            this.reviewCriteria.set(criterion.category, criterion);
        });
    }

    initializeReviewTemplates() {
        const templates = [
            {
                type: 'product_review',
                sections: ['overall_rating', 'quality_assessment', 'pros_cons', 'recommendation'],
                required_fields: ['overall_rating', 'product_id', 'reviewer_id']
            },
            {
                type: 'vendor_review',
                sections: ['service_rating', 'communication', 'delivery', 'support_quality'],
                required_fields: ['service_rating', 'vendor_id', 'reviewer_id']
            },
            {
                type: 'assembly_review',
                sections: ['difficulty_rating', 'time_taken', 'instruction_quality', 'result_satisfaction'],
                required_fields: ['difficulty_rating', 'assembly_id', 'reviewer_id']
            },
            {
                type: 'design_review',
                sections: ['design_rating', 'functionality', 'aesthetics', 'innovation'],
                required_fields: ['design_rating', 'design_id', 'reviewer_id']
            }
        ];

        templates.forEach(template => {
            this.reviewTemplates.set(template.type, template);
        });
    }

    async submitReview(reviewData) {
        try {
            const validation = await this.validateReviewSubmission(reviewData);
            if (!validation.valid) {
                throw new Error(`Review validation failed: ${validation.errors.join(', ')}`);
            }

            const review = {
                id: this.generateReviewId(),
                ...reviewData,
                submission_date: new Date(),
                status: 'pending_moderation',
                verification_status: 'unverified',
                helpfulness_score: 0,
                flags: [],
                moderation_notes: [],
                sentiment_score: await this.analyzeSentiment(reviewData.content),
                authenticity_score: await this.calculateAuthenticityScore(reviewData)
            };

            review.structured_rating = await this.calculateStructuredRating(review);
            review.review_hash = this.generateReviewHash(review);

            this.reviews.set(review.id, review);
            this.moderationQueue.push(review.id);

            await this.triggerAutoModeration(review);
            this.emit('reviewSubmitted', review);

            return {
                success: true,
                review_id: review.id,
                status: review.status,
                estimated_review_time: '24-48 hours'
            };
        } catch (error) {
            this.emit('reviewError', { error: error.message, reviewData });
            throw error;
        }
    }

    async validateReviewSubmission(reviewData) {
        const errors = [];
        
        if (!reviewData.reviewer_id) errors.push('Reviewer ID required');
        if (!reviewData.type) errors.push('Review type required');
        if (!this.reviewTemplates.has(reviewData.type)) {
            errors.push('Invalid review type');
        } else {
            const template = this.reviewTemplates.get(reviewData.type);
            template.required_fields.forEach(field => {
                if (!reviewData[field]) {
                    errors.push(`Required field missing: ${field}`);
                }
            });
        }

        if (reviewData.overall_rating && (reviewData.overall_rating < 1 || reviewData.overall_rating > 5)) {
            errors.push('Rating must be between 1 and 5');
        }

        if (reviewData.content && reviewData.content.length < 10) {
            errors.push('Review content too short (minimum 10 characters)');
        }

        const duplicateCheck = await this.checkForDuplicateReviews(reviewData);
        if (duplicateCheck.isDuplicate) {
            errors.push('Similar review already exists');
        }

        const spamCheck = await this.checkForSpam(reviewData);
        if (spamCheck.isSpam) {
            errors.push('Review flagged as potential spam');
        }

        return {
            valid: errors.length === 0,
            errors
        };
    }

    async triggerAutoModeration(review) {
        const moderationChecks = await Promise.all([
            this.checkProfanityFilter(review),
            this.checkSentimentExtreme(review),
            this.checkReviewerHistory(review),
            this.checkContentAuthenticity(review)
        ]);

        const flaggedChecks = moderationChecks.filter(check => check.flagged);
        
        if (flaggedChecks.length === 0 && review.authenticity_score > 0.8) {
            review.status = 'approved';
            review.verification_status = 'auto_verified';
            this.publishReview(review);
        } else if (flaggedChecks.length > 2 || review.authenticity_score < 0.3) {
            review.status = 'rejected';
            review.rejection_reason = flaggedChecks.map(check => check.reason).join(', ');
        } else {
            review.status = 'manual_review_required';
            review.moderation_notes = flaggedChecks.map(check => check.reason);
        }

        this.reviews.set(review.id, review);
    }

    async calculateStructuredRating(review) {
        const structured = {};
        
        this.reviewCriteria.forEach((criterion, category) => {
            if (review.ratings && review.ratings[category]) {
                structured[category] = {
                    rating: review.ratings[category],
                    weight: criterion.weight,
                    weighted_score: review.ratings[category] * criterion.weight
                };
            }
        });

        const totalWeightedScore = Object.values(structured)
            .reduce((sum, rating) => sum + rating.weighted_score, 0);
        const totalWeight = Object.values(structured)
            .reduce((sum, rating) => sum + rating.weight, 0);

        structured.composite_score = totalWeight > 0 ? totalWeightedScore / totalWeight : 0;
        return structured;
    }

    async moderateReview(reviewId, moderatorId, action, notes = '') {
        const review = this.reviews.get(reviewId);
        if (!review) {
            throw new Error('Review not found');
        }

        const moderation = {
            moderator_id: moderatorId,
            action,
            notes,
            moderation_date: new Date()
        };

        review.moderation_history = review.moderation_history || [];
        review.moderation_history.push(moderation);

        switch (action) {
            case 'approve':
                review.status = 'approved';
                review.verification_status = 'manually_verified';
                await this.publishReview(review);
                break;
            case 'reject':
                review.status = 'rejected';
                review.rejection_reason = notes;
                break;
            case 'flag':
                review.flags.push({
                    flag_type: 'moderator_flag',
                    reason: notes,
                    date: new Date()
                });
                break;
            case 'edit':
                review.status = 'edited';
                review.moderation_notes.push(notes);
                break;
        }

        this.reviews.set(reviewId, review);
        this.emit('reviewModerated', { review, moderation });

        return {
            success: true,
            review_id: reviewId,
            new_status: review.status
        };
    }

    async publishReview(review) {
        review.publication_date = new Date();
        review.status = 'published';
        
        await this.updateReviewMetrics();
        await this.updateTargetRatings(review);
        await this.triggerReviewNotifications(review);
        
        this.emit('reviewPublished', review);
    }

    async getReviewsForTarget(targetType, targetId, filters = {}) {
        const targetReviews = Array.from(this.reviews.values()).filter(review => {
            if (review[`${targetType}_id`] !== targetId) return false;
            if (review.status !== 'published') return false;
            
            if (filters.rating_min && review.overall_rating < filters.rating_min) return false;
            if (filters.rating_max && review.overall_rating > filters.rating_max) return false;
            if (filters.verified_only && review.verification_status === 'unverified') return false;
            if (filters.date_from && new Date(review.publication_date) < new Date(filters.date_from)) return false;
            if (filters.date_to && new Date(review.publication_date) > new Date(filters.date_to)) return false;
            
            return true;
        });

        const sortBy = filters.sort_by || 'helpful';
        targetReviews.sort((a, b) => {
            switch (sortBy) {
                case 'newest': return new Date(b.publication_date) - new Date(a.publication_date);
                case 'oldest': return new Date(a.publication_date) - new Date(b.publication_date);
                case 'rating_high': return b.overall_rating - a.overall_rating;
                case 'rating_low': return a.overall_rating - b.overall_rating;
                case 'helpful':
                default: return b.helpfulness_score - a.helpfulness_score;
            }
        });

        const page = filters.page || 1;
        const limit = filters.limit || 20;
        const start = (page - 1) * limit;
        const end = start + limit;

        return {
            reviews: targetReviews.slice(start, end),
            pagination: {
                current_page: page,
                total_pages: Math.ceil(targetReviews.length / limit),
                total_reviews: targetReviews.length,
                has_next: end < targetReviews.length,
                has_prev: page > 1
            },
            summary: await this.calculateReviewSummary(targetReviews)
        };
    }

    async calculateReviewSummary(reviews) {
        if (reviews.length === 0) {
            return {
                average_rating: 0,
                total_reviews: 0,
                rating_distribution: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 }
            };
        }

        const ratings = reviews.map(r => r.overall_rating);
        const average_rating = ratings.reduce((sum, rating) => sum + rating, 0) / ratings.length;
        
        const rating_distribution = ratings.reduce((dist, rating) => {
            dist[rating] = (dist[rating] || 0) + 1;
            return dist;
        }, {});

        const sentiment_distribution = reviews.reduce((dist, review) => {
            const sentiment = review.sentiment_score > 0.1 ? 'positive' : 
                            review.sentiment_score < -0.1 ? 'negative' : 'neutral';
            dist[sentiment] = (dist[sentiment] || 0) + 1;
            return dist;
        }, { positive: 0, neutral: 0, negative: 0 });

        return {
            average_rating: Math.round(average_rating * 100) / 100,
            total_reviews: reviews.length,
            verified_reviews: reviews.filter(r => r.verification_status !== 'unverified').length,
            rating_distribution,
            sentiment_distribution,
            most_helpful: reviews.sort((a, b) => b.helpfulness_score - a.helpfulness_score)[0] || null
        };
    }

    async flagReview(reviewId, flagData) {
        const review = this.reviews.get(reviewId);
        if (!review) {
            throw new Error('Review not found');
        }

        const flag = {
            id: this.generateFlagId(),
            flag_type: flagData.type,
            reason: flagData.reason,
            reporter_id: flagData.reporter_id,
            date: new Date(),
            status: 'pending'
        };

        review.flags = review.flags || [];
        review.flags.push(flag);

        if (review.flags.length >= 3) {
            review.status = 'under_investigation';
            this.moderationQueue.unshift(reviewId);
        }

        this.reviews.set(reviewId, review);
        this.emit('reviewFlagged', { review, flag });

        return {
            success: true,
            flag_id: flag.id,
            review_status: review.status
        };
    }

    async voteOnReviewHelpfulness(reviewId, userId, helpful) {
        const review = this.reviews.get(reviewId);
        if (!review) {
            throw new Error('Review not found');
        }

        review.helpfulness_votes = review.helpfulness_votes || [];
        const existingVote = review.helpfulness_votes.find(vote => vote.user_id === userId);

        if (existingVote) {
            existingVote.helpful = helpful;
            existingVote.date = new Date();
        } else {
            review.helpfulness_votes.push({
                user_id: userId,
                helpful,
                date: new Date()
            });
        }

        review.helpfulness_score = review.helpfulness_votes.reduce((score, vote) => {
            return score + (vote.helpful ? 1 : -0.5);
        }, 0);

        this.reviews.set(reviewId, review);
        return {
            success: true,
            new_helpfulness_score: review.helpfulness_score
        };
    }

    async generateReviewInsights(targetType, targetId) {
        const reviews = await this.getReviewsForTarget(targetType, targetId);
        const reviewList = reviews.reviews;

        if (reviewList.length === 0) {
            return { message: 'No reviews available for analysis' };
        }

        const insights = {
            performance_trends: await this.analyzePerformanceTrends(reviewList),
            common_themes: await this.extractCommonThemes(reviewList),
            improvement_suggestions: await this.generateImprovementSuggestions(reviewList),
            competitor_comparison: await this.compareWithCompetitors(targetType, targetId),
            reviewer_demographics: await this.analyzeReviewerDemographics(reviewList),
            seasonal_patterns: await this.analyzeSeasonalPatterns(reviewList)
        };

        return insights;
    }

    async analyzePerformanceTrends(reviews) {
        const sortedReviews = reviews.sort((a, b) => new Date(a.publication_date) - new Date(b.publication_date));
        const monthlyAverages = {};

        sortedReviews.forEach(review => {
            const month = review.publication_date.toISOString().slice(0, 7);
            if (!monthlyAverages[month]) {
                monthlyAverages[month] = { total: 0, count: 0 };
            }
            monthlyAverages[month].total += review.overall_rating;
            monthlyAverages[month].count += 1;
        });

        const trends = Object.entries(monthlyAverages).map(([month, data]) => ({
            month,
            average_rating: data.total / data.count,
            review_count: data.count
        }));

        const currentAvg = trends[trends.length - 1]?.average_rating || 0;
        const previousAvg = trends[trends.length - 2]?.average_rating || 0;
        const trend_direction = currentAvg > previousAvg ? 'improving' : 
                              currentAvg < previousAvg ? 'declining' : 'stable';

        return {
            monthly_trends: trends,
            trend_direction,
            improvement_rate: Math.abs(currentAvg - previousAvg)
        };
    }

    async extractCommonThemes(reviews) {
        const themes = {};
        const positiveKeywords = ['excellent', 'great', 'amazing', 'perfect', 'outstanding'];
        const negativeKeywords = ['terrible', 'awful', 'horrible', 'worst', 'disappointing'];

        reviews.forEach(review => {
            if (!review.content) return;
            
            const words = review.content.toLowerCase().split(/\s+/);
            words.forEach(word => {
                if (word.length > 3) {
                    themes[word] = (themes[word] || 0) + 1;
                }
            });
        });

        const sortedThemes = Object.entries(themes)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 20)
            .map(([word, count]) => ({
                word,
                frequency: count,
                sentiment: positiveKeywords.includes(word) ? 'positive' :
                          negativeKeywords.includes(word) ? 'negative' : 'neutral'
            }));

        return sortedThemes;
    }

    async generateImprovementSuggestions(reviews) {
        const lowRatingReviews = reviews.filter(r => r.overall_rating <= 2);
        const suggestions = [];

        const commonIssues = {};
        lowRatingReviews.forEach(review => {
            if (review.content) {
                const issues = this.extractIssues(review.content);
                issues.forEach(issue => {
                    commonIssues[issue] = (commonIssues[issue] || 0) + 1;
                });
            }
        });

        Object.entries(commonIssues)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 5)
            .forEach(([issue, count]) => {
                suggestions.push({
                    issue,
                    frequency: count,
                    priority: count > 5 ? 'high' : count > 2 ? 'medium' : 'low',
                    suggested_action: this.getSuggestedAction(issue)
                });
            });

        return suggestions;
    }

    extractIssues(content) {
        const issuePatterns = [
            'shipping', 'delivery', 'packaging', 'quality', 'support',
            'installation', 'documentation', 'compatibility', 'price', 'value'
        ];
        
        return issuePatterns.filter(pattern => 
            content.toLowerCase().includes(pattern)
        );
    }

    getSuggestedAction(issue) {
        const actions = {
            'shipping': 'Review shipping partners and delivery processes',
            'delivery': 'Improve delivery tracking and communication',
            'packaging': 'Enhance packaging design and protection',
            'quality': 'Implement stricter quality control measures',
            'support': 'Expand customer support team and training',
            'installation': 'Create better installation guides and videos',
            'documentation': 'Improve product documentation and manuals',
            'compatibility': 'Better compatibility testing and information',
            'price': 'Review pricing strategy and value proposition',
            'value': 'Enhance product features or adjust pricing'
        };
        
        return actions[issue] || 'Investigate and address customer concerns';
    }

    async checkForDuplicateReviews(reviewData) {
        const similarReviews = Array.from(this.reviews.values()).filter(review => 
            review.reviewer_id === reviewData.reviewer_id &&
            review.product_id === reviewData.product_id &&
            review.status !== 'rejected'
        );

        return {
            isDuplicate: similarReviews.length > 0,
            similarReviews
        };
    }

    async checkForSpam(reviewData) {
        const spamIndicators = [
            reviewData.content && reviewData.content.includes('http'),
            reviewData.content && /(.)\1{4,}/.test(reviewData.content),
            reviewData.content && reviewData.content.split(' ').length < 3,
            reviewData.overall_rating === 5 && (!reviewData.content || reviewData.content.length < 20)
        ];

        const spamScore = spamIndicators.filter(Boolean).length / spamIndicators.length;
        
        return {
            isSpam: spamScore > 0.5,
            spamScore,
            indicators: spamIndicators.map((indicator, index) => ({
                type: ['external_links', 'repetitive_chars', 'too_short', 'suspicious_5_star'][index],
                flagged: indicator
            })).filter(i => i.flagged)
        };
    }

    async analyzeSentiment(content) {
        if (!content) return 0;

        const positiveWords = ['great', 'excellent', 'amazing', 'perfect', 'love', 'best', 'awesome', 'fantastic'];
        const negativeWords = ['terrible', 'awful', 'hate', 'worst', 'horrible', 'disappointing', 'bad', 'poor'];
        
        const words = content.toLowerCase().split(/\s+/);
        let positiveCount = 0;
        let negativeCount = 0;

        words.forEach(word => {
            if (positiveWords.includes(word)) positiveCount++;
            if (negativeWords.includes(word)) negativeCount++;
        });

        const totalSentimentWords = positiveCount + negativeCount;
        if (totalSentimentWords === 0) return 0;

        return (positiveCount - negativeCount) / Math.max(words.length, 10);
    }

    async calculateAuthenticityScore(reviewData) {
        let score = 0.5;

        if (reviewData.verified_purchase) score += 0.3;
        if (reviewData.content && reviewData.content.length > 50) score += 0.1;
        if (reviewData.content && reviewData.content.length > 200) score += 0.1;
        if (reviewData.photos && reviewData.photos.length > 0) score += 0.2;
        if (reviewData.detailed_ratings && Object.keys(reviewData.detailed_ratings).length > 3) score += 0.1;

        const recentReviewsFromUser = Array.from(this.reviews.values()).filter(review => 
            review.reviewer_id === reviewData.reviewer_id &&
            new Date() - new Date(review.submission_date) < 24 * 60 * 60 * 1000
        );

        if (recentReviewsFromUser.length > 5) score -= 0.3;

        return Math.max(0, Math.min(1, score));
    }

    generateReviewId() {
        return `review_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateFlagId() {
        return `flag_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateReviewHash(review) {
        const hashContent = `${review.reviewer_id}_${review.product_id}_${review.content}_${review.overall_rating}`;
        return createHash('sha256').update(hashContent).digest('hex').substr(0, 16);
    }

    async updateReviewMetrics() {
        const allReviews = Array.from(this.reviews.values());
        const publishedReviews = allReviews.filter(r => r.status === 'published');
        
        this.reviewMetrics.total_reviews = publishedReviews.length;
        this.reviewMetrics.verified_reviews = publishedReviews.filter(r => r.verification_status !== 'unverified').length;
        this.reviewMetrics.flagged_reviews = allReviews.filter(r => r.flags && r.flags.length > 0).length;
        
        if (publishedReviews.length > 0) {
            this.reviewMetrics.average_rating = publishedReviews.reduce((sum, r) => sum + r.overall_rating, 0) / publishedReviews.length;
        }
    }

    async updateTargetRatings(review) {
        this.emit('targetRatingUpdate', {
            target_type: review.type,
            target_id: review[`${review.type.split('_')[0]}_id`],
            new_review: review
        });
    }

    async triggerReviewNotifications(review) {
        this.emit('reviewNotification', {
            type: 'review_published',
            review,
            recipients: ['vendor', 'product_followers']
        });
    }

    async checkProfanityFilter(review) {
        const profanityWords = ['spam', 'fake', 'scam'];
        const content = (review.content || '').toLowerCase();
        const hasProfanity = profanityWords.some(word => content.includes(word));
        
        return {
            flagged: hasProfanity,
            reason: 'Contains potentially inappropriate content'
        };
    }

    async checkSentimentExtreme(review) {
        const extremeThreshold = 0.8;
        const isExtreme = Math.abs(review.sentiment_score) > extremeThreshold;
        
        return {
            flagged: isExtreme && review.content && review.content.length < 50,
            reason: 'Extreme sentiment with minimal content'
        };
    }

    async checkReviewerHistory(review) {
        const recentReviews = Array.from(this.reviews.values()).filter(r => 
            r.reviewer_id === review.reviewer_id &&
            new Date() - new Date(r.submission_date) < 7 * 24 * 60 * 60 * 1000
        );
        
        return {
            flagged: recentReviews.length > 10,
            reason: 'Unusually high review activity from user'
        };
    }

    async checkContentAuthenticity(review) {
        return {
            flagged: review.authenticity_score < 0.4,
            reason: 'Low authenticity score'
        };
    }

    async compareWithCompetitors(targetType, targetId) {
        return {
            message: 'Competitor comparison analysis would require external data integration',
            suggestion: 'Integrate with market research APIs for comprehensive competitor analysis'
        };
    }

    async analyzeReviewerDemographics(reviews) {
        return {
            total_unique_reviewers: new Set(reviews.map(r => r.reviewer_id)).size,
            verified_reviewers: reviews.filter(r => r.verification_status !== 'unverified').length,
            repeat_reviewers: reviews.length - new Set(reviews.map(r => r.reviewer_id)).size
        };
    }

    async analyzeSeasonalPatterns(reviews) {
        const seasonalData = {};
        
        reviews.forEach(review => {
            const month = new Date(review.publication_date).getMonth();
            const season = ['Winter', 'Winter', 'Spring', 'Spring', 'Spring', 'Summer', 
                          'Summer', 'Summer', 'Fall', 'Fall', 'Fall', 'Winter'][month];
            
            if (!seasonalData[season]) {
                seasonalData[season] = { count: 0, totalRating: 0 };
            }
            seasonalData[season].count++;
            seasonalData[season].totalRating += review.overall_rating;
        });

        return Object.entries(seasonalData).map(([season, data]) => ({
            season,
            review_count: data.count,
            average_rating: data.count > 0 ? data.totalRating / data.count : 0
        }));
    }

    getSystemStats() {
        return {
            total_reviews: this.reviews.size,
            pending_moderation: this.moderationQueue.length,
            review_metrics: this.reviewMetrics,
            system_uptime: process.uptime(),
            memory_usage: process.memoryUsage()
        };
    }
}

export default ReviewSystem;