const User = require('../models/User');
const config = require('../config/config');
const { v4: uuidv4 } = require('uuid');

class ReviewController {
  constructor() {
    this.config = config.reviewSystem;
  }

  // Submit Review for CCC Rewards
  async submitReview(req, res) {
    try {
      const { userId } = req.params;
      const { 
        targetId, 
        targetType, 
        rating, 
        reviewText, 
        photos = [], 
        videoUrl = null 
      } = req.body;

      const user = await User.findByUserId(userId);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // Validate review eligibility
      const eligibility = await this.checkReviewEligibility(user, targetId);
      if (!eligibility.eligible) {
        return res.status(400).json({ 
          error: 'Review not eligible', 
          reason: eligibility.reason 
        });
      }

      // Determine review type and base reward
      const reviewType = this.determineReviewType(reviewText, photos, videoUrl);
      const baseReward = this.config.reviewRewards[reviewType];
      
      // Calculate reputation multiplier
      const reputationMultiplier = this.getReputationMultiplier(user.reviews.given.reputation);
      
      // Calculate quality score
      const qualityScore = this.calculateQualityScore(reviewText, photos, videoUrl, rating);
      
      // Apply quality bonus/penalty
      const qualityMultiplier = this.getQualityMultiplier(qualityScore);
      
      // Final reward calculation
      const finalReward = Math.round(baseReward * reputationMultiplier * qualityMultiplier);

      // Create review record
      const reviewRecord = {
        targetId,
        targetType,
        rating,
        review: reviewText || '',
        photos,
        videoUrl,
        helpful: 0,
        timestamp: new Date(),
        reward: finalReward
      };

      // Update user review stats
      user.reviews.given.count += 1;
      user.reviews.given.totalRating += rating;
      user.reviews.given.lastReview = new Date();
      user.reviews.given.reviews.push(reviewRecord);

      // Update quality score (running average)
      const currentQuality = user.reviews.given.qualityScore || 0;
      const reviewCount = user.reviews.given.count;
      user.reviews.given.qualityScore = ((currentQuality * (reviewCount - 1)) + qualityScore) / reviewCount;

      // Update reputation tier
      user.reviews.given.reputation = this.calculateReputationTier(user.reviews.given.count);

      // Award CCC
      await user.addCredits(
        finalReward, 
        'review', 
        `${reviewType} review for ${targetType}`,
        {
          targetId,
          targetType,
          reviewType,
          baseReward,
          reputationMultiplier,
          qualityMultiplier,
          qualityScore
        }
      );

      await user.save();

      res.json({
        success: true,
        reviewId: reviewRecord._id,
        reviewType,
        qualityScore,
        rewards: {
          base: baseReward,
          reputationMultiplier,
          qualityMultiplier,
          final: finalReward
        },
        userStats: {
          newBalance: user.credits.balance,
          reviewCount: user.reviews.given.count,
          reputation: user.reviews.given.reputation,
          qualityScore: user.reviews.given.qualityScore
        }
      });

    } catch (error) {
      console.error('Error submitting review:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Get Review Opportunities
  async getReviewOpportunities(req, res) {
    try {
      const { userId } = req.params;
      const { category, location, limit = 10 } = req.query;

      const user = await User.findByUserId(userId);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // Check eligibility for more reviews today
      const eligibility = this.checkDailyReviewEligibility(user);
      if (!eligibility.canReview) {
        return res.json({
          opportunities: [],
          reason: eligibility.reason,
          nextAvailable: eligibility.nextAvailable,
          dailyStats: {
            reviewsToday: eligibility.reviewsToday,
            maxDaily: this.config.qualityThresholds.maxDaily
          }
        });
      }

      // Generate mock opportunities (in real app, this would query a database)
      const opportunities = this.generateReviewOpportunities(user, category, location, limit);

      res.json({
        opportunities,
        userStats: {
          reputation: user.reviews.given.reputation,
          reviewCount: user.reviews.given.count,
          qualityScore: user.reviews.given.qualityScore,
          potentialEarnings: this.calculatePotentialEarnings(user, opportunities.length)
        },
        dailyStats: {
          reviewsToday: eligibility.reviewsToday,
          remainingToday: this.config.qualityThresholds.maxDaily - eligibility.reviewsToday
        }
      });

    } catch (error) {
      console.error('Error getting review opportunities:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Get User Review Stats
  async getReviewStats(req, res) {
    try {
      const { userId } = req.params;
      const user = await User.findByUserId(userId);

      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      const stats = {
        given: {
          count: user.reviews.given.count,
          reputation: user.reviews.given.reputation,
          qualityScore: user.reviews.given.qualityScore,
          averageRating: user.reviews.given.count > 0 
            ? user.reviews.given.totalRating / user.reviews.given.count 
            : 0,
          totalEarned: user.reviews.given.reviews.reduce((sum, r) => sum + r.reward, 0),
          lastReview: user.reviews.given.lastReview
        },
        received: {
          count: user.reviews.received.count,
          averageRating: user.reviews.received.averageRating,
          totalRating: user.reviews.received.totalRating
        },
        progression: {
          currentTier: user.reviews.given.reputation,
          nextTier: this.getNextReputationTier(user.reviews.given.reputation),
          progressToNext: this.getProgressToNextTier(user.reviews.given.count),
          multiplier: this.getReputationMultiplier(user.reviews.given.reputation)
        },
        opportunities: {
          canReviewToday: this.checkDailyReviewEligibility(user).canReview,
          remainingToday: Math.max(0, this.config.qualityThresholds.maxDaily - this.getTodayReviewCount(user))
        }
      };

      res.json(stats);

    } catch (error) {
      console.error('Error getting review stats:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Mark Review as Helpful
  async markReviewHelpful(req, res) {
    try {
      const { userId, reviewId } = req.params;
      const { helpful = true } = req.body;

      const user = await User.findByUserId(userId);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      const review = user.reviews.given.reviews.id(reviewId);
      if (!review) {
        return res.status(404).json({ error: 'Review not found' });
      }

      // Update helpful count
      review.helpful += helpful ? 1 : -1;
      review.helpful = Math.max(0, review.helpful);

      // Award bonus credits for helpful reviews (milestone-based)
      const helpfulMilestones = [5, 10, 25, 50, 100];
      if (helpfulMilestones.includes(review.helpful)) {
        const bonusReward = Math.floor(review.helpful / 5) * 2;
        await user.addCredits(
          bonusReward,
          'review_helpful',
          `Review reached ${review.helpful} helpful votes`,
          { reviewId, helpfulCount: review.helpful }
        );
      }

      await user.save();

      res.json({
        success: true,
        reviewId,
        newHelpfulCount: review.helpful,
        bonusAwarded: helpfulMilestones.includes(review.helpful)
      });

    } catch (error) {
      console.error('Error marking review as helpful:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Helper Methods
  async checkReviewEligibility(user, targetId) {
    // Check if user already reviewed this target
    const existingReview = user.reviews.given.reviews.find(r => r.targetId === targetId);
    if (existingReview) {
      return { eligible: false, reason: 'Already reviewed this item' };
    }

    // Check daily review limit
    const dailyCheck = this.checkDailyReviewEligibility(user);
    if (!dailyCheck.canReview) {
      return { eligible: false, reason: dailyCheck.reason };
    }

    // Check cooldown period
    if (user.reviews.given.lastReview) {
      const cooldownMs = this.config.qualityThresholds.cooldown * 1000;
      const timeSinceLastReview = Date.now() - user.reviews.given.lastReview.getTime();
      if (timeSinceLastReview < cooldownMs) {
        const remainingMinutes = Math.ceil((cooldownMs - timeSinceLastReview) / 1000 / 60);
        return { 
          eligible: false, 
          reason: `Cooldown active. Try again in ${remainingMinutes} minutes.` 
        };
      }
    }

    return { eligible: true };
  }

  checkDailyReviewEligibility(user) {
    const today = new Date().toDateString();
    const reviewsToday = this.getTodayReviewCount(user);
    const maxDaily = this.config.qualityThresholds.maxDaily;

    if (reviewsToday >= maxDaily) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      tomorrow.setHours(0, 0, 0, 0);

      return {
        canReview: false,
        reason: 'Daily review limit reached',
        reviewsToday,
        nextAvailable: tomorrow
      };
    }

    return {
      canReview: true,
      reviewsToday
    };
  }

  getTodayReviewCount(user) {
    const today = new Date().toDateString();
    return user.reviews.given.reviews.filter(r => 
      r.timestamp.toDateString() === today
    ).length;
  }

  determineReviewType(reviewText, photos, videoUrl) {
    if (videoUrl) return 'video';
    if (photos && photos.length > 0) return 'photo';
    if (reviewText && reviewText.length >= this.config.qualityThresholds.minLength) return 'detailed';
    return 'basic';
  }

  calculateQualityScore(reviewText, photos, videoUrl, rating) {
    let score = 50; // Base score

    // Text quality
    if (reviewText) {
      const wordCount = reviewText.split(' ').length;
      if (wordCount >= 10) score += 10;
      if (wordCount >= 25) score += 10;
      if (wordCount >= 50) score += 10;

      // Check for helpful keywords
      const helpfulWords = ['quality', 'recommend', 'experience', 'value', 'service'];
      const foundWords = helpfulWords.filter(word => 
        reviewText.toLowerCase().includes(word)
      ).length;
      score += foundWords * 2;
    }

    // Visual content
    if (photos && photos.length > 0) {
      score += Math.min(photos.length * 5, 15);
    }
    if (videoUrl) {
      score += 20;
    }

    // Rating reasonableness (extreme ratings get slight penalty unless justified)
    if ((rating === 1 || rating === 5) && (!reviewText || reviewText.length < 50)) {
      score -= 5;
    }

    return Math.min(Math.max(score, 0), 100);
  }

  getQualityMultiplier(qualityScore) {
    if (qualityScore >= 90) return 1.5;
    if (qualityScore >= 80) return 1.3;
    if (qualityScore >= 70) return 1.1;
    if (qualityScore >= 60) return 1.0;
    if (qualityScore >= 40) return 0.8;
    return 0.6;
  }

  getReputationMultiplier(reputation) {
    return this.config.reputationMultipliers[reputation] || 1.0;
  }

  calculateReputationTier(reviewCount) {
    if (reviewCount >= 200) return 'master';
    if (reviewCount >= 51) return 'expert';
    if (reviewCount >= 11) return 'contributor';
    return 'newcomer';
  }

  getNextReputationTier(currentTier) {
    const tiers = ['newcomer', 'contributor', 'expert', 'master'];
    const currentIndex = tiers.indexOf(currentTier);
    return currentIndex < tiers.length - 1 ? tiers[currentIndex + 1] : 'master';
  }

  getProgressToNextTier(reviewCount) {
    if (reviewCount < 11) return { current: reviewCount, needed: 11, progress: reviewCount / 11 };
    if (reviewCount < 51) return { current: reviewCount, needed: 51, progress: reviewCount / 51 };
    if (reviewCount < 200) return { current: reviewCount, needed: 200, progress: reviewCount / 200 };
    return { current: reviewCount, needed: 200, progress: 1.0 };
  }

  calculatePotentialEarnings(user, opportunityCount) {
    const baseReward = this.config.reviewRewards.detailed;
    const multiplier = this.getReputationMultiplier(user.reviews.given.reputation);
    const avgQualityMultiplier = 1.1; // Assume average quality
    
    return Math.round(baseReward * multiplier * avgQualityMultiplier * opportunityCount);
  }

  generateReviewOpportunities(user, category, location, limit) {
    // Mock opportunities - in real app, this would query actual products/services
    const mockOpportunities = [
      {
        id: 'prod_001',
        type: 'product',
        name: 'ActiveLog Pro Subscription',
        category: 'software',
        description: 'Premium productivity software subscription',
        potentialReward: this.calculateReviewReward(user, 'detailed'),
        estimatedTime: 10,
        difficulty: 'easy'
      },
      {
        id: 'service_001',
        type: 'service',
        name: 'CloudCompute API',
        category: 'cloud-services',
        description: 'Cloud computing API service',
        potentialReward: this.calculateReviewReward(user, 'detailed'),
        estimatedTime: 15,
        difficulty: 'medium'
      },
      {
        id: 'app_001',
        type: 'app',
        name: 'TaskManager Mobile',
        category: 'mobile-app',
        description: 'Mobile task management application',
        potentialReward: this.calculateReviewReward(user, 'photo'),
        estimatedTime: 12,
        difficulty: 'easy'
      },
      {
        id: 'course_001',
        type: 'course',
        name: 'AI Development Fundamentals',
        category: 'education',
        description: 'Online course on AI development basics',
        potentialReward: this.calculateReviewReward(user, 'video'),
        estimatedTime: 20,
        difficulty: 'hard'
      }
    ];

    // Filter by category if specified
    let filtered = mockOpportunities;
    if (category) {
      filtered = filtered.filter(opp => opp.category === category);
    }

    // Shuffle and limit
    const shuffled = filtered.sort(() => 0.5 - Math.random());
    return shuffled.slice(0, Math.min(limit, shuffled.length));
  }

  calculateReviewReward(user, reviewType) {
    const baseReward = this.config.reviewRewards[reviewType] || this.config.reviewRewards.basic;
    const reputationMultiplier = this.getReputationMultiplier(user.reviews.given.reputation);
    const avgQualityMultiplier = 1.1;
    
    return Math.round(baseReward * reputationMultiplier * avgQualityMultiplier);
  }
}

module.exports = ReviewController;