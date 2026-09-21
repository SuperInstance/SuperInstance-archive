const User = require('../models/User');
const config = require('../config/config');
const { v4: uuidv4 } = require('uuid');

class AdEngineController {
  constructor() {
    this.config = config.adEngine;
  }

  // Watch-Ad-to-Use System for Compute-Heavy Features
  async checkComputeEligibility(req, res) {
    try {
      const { userId } = req.params;
      const { operation, operationType = 'medium' } = req.body;
      
      const user = await User.findByUserId(userId);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      await user.resetDailyCounters();

      const cost = this.config.computeCosts[operationType] || this.config.computeCosts.medium;
      const hasCredits = user.credits.balance >= cost;
      const isAdFreeEligible = user.credits.balance >= this.config.adFreeThresholds.daily;

      // Check if user needs to watch ad to proceed
      const needsAd = !hasCredits && !isAdFreeEligible;
      const canShowAd = this.canShowAd(user);

      const response = {
        eligible: hasCredits || isAdFreeEligible,
        cost,
        currentBalance: user.credits.balance,
        needsAd,
        canShowAd,
        adFreeEligible: isAdFreeEligible,
        operation,
        operationType
      };

      // If needs ad but can't show one, provide alternatives
      if (needsAd && !canShowAd) {
        response.alternatives = {
          waitTime: this.getNextAdWaitTime(user),
          upgradeOption: true,
          earnCreditsOptions: [
            { type: 'review', reward: this.config.adRewards.banner },
            { type: 'education', reward: 5 },
            { type: 'referral', reward: 25 }
          ]
        };
      }

      res.json(response);
    } catch (error) {
      console.error('Error checking compute eligibility:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  async requestComputeAccess(req, res) {
    try {
      const { userId } = req.params;
      const { operation, operationType = 'medium', skipAd = false } = req.body;
      
      const user = await User.findByUserId(userId);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      const cost = this.config.computeCosts[operationType] || this.config.computeCosts.medium;
      
      // Check if user has sufficient credits
      if (user.credits.balance >= cost) {
        await user.spendCredits(cost, 'compute_usage', `${operationType} operation: ${operation}`);
        
        // Record usage
        user.usage.compute.today += cost;
        user.usage.compute.thisWeek += cost;
        user.usage.compute.thisMonth += cost;
        user.usage.compute.history.push({
          date: new Date(),
          operations: 1,
          cost,
          categories: [operationType]
        });
        
        await user.updateUsageTier();
        await user.save();

        return res.json({
          granted: true,
          method: 'credits',
          remainingBalance: user.credits.balance,
          cost
        });
      }

      // If ad-free eligible (high balance), grant access
      if (user.credits.balance >= this.config.adFreeThresholds.daily) {
        await user.spendCredits(cost, 'compute_usage', `${operationType} operation: ${operation} (ad-free)`);
        return res.json({
          granted: true,
          method: 'ad_free',
          remainingBalance: user.credits.balance,
          cost
        });
      }

      // Check if user can watch ad
      if (!this.canShowAd(user) || skipAd) {
        return res.status(403).json({
          granted: false,
          reason: 'insufficient_credits_no_ad',
          nextAdAvailable: user.ads.nextAdAllowed,
          alternatives: this.getAlternativeEarningMethods()
        });
      }

      // Generate ad request
      const adRequest = await this.generateAdForCompute(user, operationType, cost);
      
      res.json({
        granted: false,
        requiresAd: true,
        adRequest,
        reward: adRequest.reward,
        afterAdBalance: user.credits.balance + adRequest.reward
      });

    } catch (error) {
      console.error('Error requesting compute access:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Dynamic Ad Frequency Based on Usage
  async updateUserAdFrequency(req, res) {
    try {
      const { userId } = req.params;
      const user = await User.findByUserId(userId);
      
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // Analyze usage patterns
      const usageAnalysis = this.analyzeUsagePatterns(user);
      const newFrequency = this.calculateOptimalAdFrequency(usageAnalysis);
      
      // Update user's ad frequency settings
      user.ads.frequency = {
        current: newFrequency.tier,
        minInterval: newFrequency.minInterval,
        maxPerHour: newFrequency.maxPerHour
      };

      await user.save();

      res.json({
        userId,
        previousTier: user.usage.tier,
        newTier: newFrequency.tier,
        frequency: user.ads.frequency,
        usageAnalysis
      });

    } catch (error) {
      console.error('Error updating ad frequency:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Startup Ad with Clear Messaging
  async getStartupAd(req, res) {
    try {
      const { userId } = req.params;
      const user = await User.findByUserId(userId);
      
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // Check if startup ad should be shown
      const shouldShowStartup = this.shouldShowStartupAd(user);
      
      if (!shouldShowStartup.show) {
        return res.json({
          showAd: false,
          reason: shouldShowStartup.reason
        });
      }

      // Generate startup ad with clear messaging
      const startupAd = {
        id: uuidv4(),
        type: 'startup',
        message: this.config.startupAd.message,
        benefits: [
          `Earn ${this.config.startupAd.rewardAmount} CCC (Compute Credits)`,
          'Support ActiveLog development',
          'Unlock compute-heavy features',
          'Reduce future ad frequency'
        ],
        skipAfter: this.config.startupAd.skipAfter,
        reward: this.config.startupAd.rewardAmount,
        adContent: this.generateMockAd('startup'),
        timestamp: new Date()
      };

      res.json({
        showAd: true,
        adData: startupAd,
        userStats: {
          currentBalance: user.credits.balance,
          balanceAfterAd: user.credits.balance + startupAd.reward,
          adFreeStatus: user.credits.balance >= this.config.adFreeThresholds.daily
        }
      });

    } catch (error) {
      console.error('Error getting startup ad:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Double Banner Option for More Credits
  async getDoubleBannerOffer(req, res) {
    try {
      const { userId } = req.params;
      const user = await User.findByUserId(userId);
      
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // Check eligibility for double banner
      const eligibility = this.checkDoubleBannerEligibility(user);
      
      if (!eligibility.eligible) {
        return res.json({
          available: false,
          reason: eligibility.reason,
          nextAvailable: eligibility.nextAvailable
        });
      }

      const baseBannerReward = this.config.adRewards.banner;
      const doubleReward = baseBannerReward + this.config.doubleBanner.extraReward;

      const doubleBannerOffer = {
        id: uuidv4(),
        type: 'double_banner',
        baseReward: baseBannerReward,
        bonusReward: this.config.doubleBanner.extraReward,
        totalReward: doubleReward,
        description: 'Watch two banner ads back-to-back for bonus credits!',
        timeLimit: 300, // 5 minutes to complete both
        ads: [
          { ...this.generateMockAd('banner'), position: 1 },
          { ...this.generateMockAd('banner'), position: 2 }
        ]
      };

      res.json({
        available: true,
        offer: doubleBannerOffer,
        remainingToday: this.config.doubleBanner.maxPerDay - this.getDoubleBannersToday(user)
      });

    } catch (error) {
      console.error('Error getting double banner offer:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Ad-Free Compute Threshold Detection
  async checkAdFreeStatus(req, res) {
    try {
      const { userId } = req.params;
      const user = await User.findByUserId(userId);
      
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      const threshold = this.config.adFreeThresholds.daily;
      const buffer = this.config.adFreeThresholds.buffer;
      const currentBalance = user.credits.balance;

      const status = {
        isAdFree: currentBalance >= threshold,
        threshold,
        currentBalance,
        creditsToAdFree: Math.max(0, threshold - currentBalance),
        bufferRemaining: Math.max(0, currentBalance - buffer),
        willShowAdsAt: buffer,
        recommendations: []
      };

      // Provide recommendations based on balance
      if (currentBalance < threshold) {
        status.recommendations = this.getBalanceRecommendations(currentBalance, threshold);
      } else if (currentBalance < threshold + buffer) {
        status.recommendations.push({
          type: 'warning',
          message: 'Balance is low. Consider earning more credits to maintain ad-free experience.',
          actions: ['watch_ads', 'write_reviews', 'complete_education']
        });
      }

      res.json(status);

    } catch (error) {
      console.error('Error checking ad-free status:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Ad Break Scheduling for Heavy Users
  async scheduleAdBreak(req, res) {
    try {
      const { userId } = req.params;
      const { sessionDuration, operationsCount } = req.body;
      
      const user = await User.findByUserId(userId);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      const schedule = this.calculateAdBreakSchedule(user, sessionDuration, operationsCount);
      
      res.json({
        userId,
        userTier: user.usage.tier,
        sessionDuration,
        operationsCount,
        schedule: {
          breaks: schedule.breaks,
          nextBreak: schedule.nextBreak,
          adsPerBreak: schedule.adsPerBreak,
          totalReward: schedule.totalReward
        },
        reasoning: schedule.reasoning
      });

    } catch (error) {
      console.error('Error scheduling ad break:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // CCC Earning Through Ad Watching
  async processAdView(req, res) {
    try {
      const { userId } = req.params;
      const { adId, adType, completed = false, watchTime = 0, metadata = {} } = req.body;
      
      const user = await User.findByUserId(userId);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // Validate ad view
      const validation = this.validateAdView(user, adType, watchTime, completed);
      if (!validation.valid) {
        return res.status(400).json({ error: validation.reason });
      }

      // Calculate reward
      const baseReward = this.config.adRewards[adType] || 0;
      const bonusMultiplier = this.calculateBonusMultiplier(user, adType);
      const finalReward = Math.round(baseReward * bonusMultiplier);

      // Record ad view
      const adViewData = {
        adId,
        type: adType,
        provider: metadata.provider || 'mock',
        completed,
        reward: finalReward,
        metadata: {
          ...metadata,
          watchTime,
          bonusMultiplier,
          userTier: user.usage.tier
        }
      };

      await user.recordAdView(adViewData);

      // Update user stats
      await user.save();

      res.json({
        success: true,
        reward: finalReward,
        baseReward,
        bonusMultiplier,
        newBalance: user.credits.balance,
        adStats: {
          totalViewed: user.ads.totalViewed,
          todayCount: user.ads.viewedToday,
          nextAdAllowed: user.ads.nextAdAllowed
        }
      });

    } catch (error) {
      console.error('Error processing ad view:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Helper Methods
  canShowAd(user) {
    const now = new Date();
    const canShow = !user.ads.nextAdAllowed || now >= user.ads.nextAdAllowed;
    const notMaxedOut = user.ads.viewedToday < user.ads.preferences.maxAdsPerDay;
    return canShow && notMaxedOut;
  }

  getNextAdWaitTime(user) {
    if (!user.ads.nextAdAllowed) return 0;
    const now = new Date();
    return Math.max(0, Math.ceil((user.ads.nextAdAllowed - now) / 1000 / 60)); // minutes
  }

  async generateAdForCompute(user, operationType, cost) {
    const adType = operationType === 'extreme' ? 'video' : 'interstitial';
    const reward = this.config.adRewards[adType];
    
    return {
      id: uuidv4(),
      type: adType,
      reward,
      purpose: `Unlock ${operationType} compute operation`,
      cost,
      content: this.generateMockAd(adType),
      metadata: {
        operationType,
        computeCost: cost,
        userTier: user.usage.tier
      }
    };
  }

  analyzeUsagePatterns(user) {
    const now = new Date();
    const dayMs = 24 * 60 * 60 * 1000;
    const weekMs = 7 * dayMs;
    
    return {
      dailyCompute: user.usage.compute.today,
      weeklyCompute: user.usage.compute.thisWeek,
      averageSession: user.usage.sessions.average,
      lastActive: user.usage.sessions.lastActive,
      tier: user.usage.tier,
      creditBalance: user.credits.balance,
      adViewsToday: user.ads.viewedToday
    };
  }

  calculateOptimalAdFrequency(analysis) {
    let tier = 'light';
    let minInterval = 30;
    let maxPerHour = 2;

    if (analysis.dailyCompute >= 500) {
      tier = 'extreme';
      minInterval = 5;
      maxPerHour = 12;
    } else if (analysis.dailyCompute >= 200) {
      tier = 'heavy';
      minInterval = 10;
      maxPerHour = 6;
    } else if (analysis.dailyCompute >= 50) {
      tier = 'moderate';
      minInterval = 15;
      maxPerHour = 4;
    }

    return { tier, minInterval, maxPerHour };
  }

  shouldShowStartupAd(user) {
    const frequency = this.config.startupAd.frequency;
    const now = new Date();
    
    if (!this.config.startupAd.enabled) {
      return { show: false, reason: 'disabled' };
    }

    if (!user.profile.preferences.enableStartupAds) {
      return { show: false, reason: 'user_disabled' };
    }

    if (frequency === 'always') {
      return { show: true };
    }

    const lastLogin = user.lastLogin || user.createdAt;
    const timeSinceLastLogin = now - lastLogin;
    
    if (frequency === 'daily' && timeSinceLastLogin < 24 * 60 * 60 * 1000) {
      return { show: false, reason: 'already_shown_today' };
    }

    if (frequency === 'weekly' && timeSinceLastLogin < 7 * 24 * 60 * 60 * 1000) {
      return { show: false, reason: 'already_shown_this_week' };
    }

    return { show: true };
  }

  checkDoubleBannerEligibility(user) {
    const today = new Date().toDateString();
    const doubleBannersToday = this.getDoubleBannersToday(user);
    
    if (doubleBannersToday >= this.config.doubleBanner.maxPerDay) {
      return { 
        eligible: false, 
        reason: 'daily_limit_reached',
        nextAvailable: new Date(new Date().getTime() + 24 * 60 * 60 * 1000)
      };
    }

    if (!this.canShowAd(user)) {
      return {
        eligible: false,
        reason: 'ad_cooldown',
        nextAvailable: user.ads.nextAdAllowed
      };
    }

    return { eligible: true };
  }

  getDoubleBannersToday(user) {
    const today = new Date().toDateString();
    return user.ads.viewHistory.filter(ad => 
      ad.type === 'double_banner' && 
      ad.viewed.toDateString() === today
    ).length;
  }

  calculateAdBreakSchedule(user, sessionDuration, operationsCount) {
    const tier = user.usage.tier;
    const frequency = this.config.adFrequency[tier];
    
    // Calculate ad breaks based on session duration and operation intensity
    const breakIntervalMinutes = frequency.minInterval;
    const maxAdsPerHour = frequency.maxPerHour;
    
    const sessionHours = sessionDuration / 60;
    const maxAdsForSession = Math.floor(sessionHours * maxAdsPerHour);
    const breaksNeeded = Math.min(
      Math.floor(sessionDuration / breakIntervalMinutes),
      maxAdsForSession
    );

    const breaks = [];
    for (let i = 1; i <= breaksNeeded; i++) {
      const breakTime = (sessionDuration / (breaksNeeded + 1)) * i;
      breaks.push({
        timeMinutes: Math.round(breakTime),
        adsCount: tier === 'extreme' ? 2 : 1,
        type: tier === 'heavy' || tier === 'extreme' ? 'video' : 'banner',
        reward: this.config.adRewards[tier === 'heavy' || tier === 'extreme' ? 'video' : 'banner']
      });
    }

    return {
      breaks,
      nextBreak: breaks[0] || null,
      adsPerBreak: breaks.length > 0 ? breaks[0].adsCount : 0,
      totalReward: breaks.reduce((sum, b) => sum + b.reward * b.adsCount, 0),
      reasoning: `${tier} user: ${breaksNeeded} breaks over ${sessionDuration} minutes`
    };
  }

  validateAdView(user, adType, watchTime, completed) {
    if (!this.canShowAd(user)) {
      return { valid: false, reason: 'Ad cooldown active' };
    }

    const minimumTimes = {
      banner: 3,
      interstitial: 5,
      video: 15,
      rewarded: 30
    };

    const required = minimumTimes[adType] || 5;
    if (watchTime < required) {
      return { valid: false, reason: `Minimum watch time not met: ${required}s required` };
    }

    if (adType === 'video' || adType === 'rewarded') {
      if (!completed) {
        return { valid: false, reason: 'Ad must be completed for reward' };
      }
    }

    return { valid: true };
  }

  calculateBonusMultiplier(user, adType) {
    let multiplier = 1.0;

    // Tier-based bonus
    const tierBonuses = {
      light: 1.0,
      moderate: 1.1,
      heavy: 1.2,
      extreme: 1.3
    };
    multiplier *= tierBonuses[user.usage.tier] || 1.0;

    // First-time daily bonus
    if (user.ads.viewedToday === 0) {
      multiplier *= 1.2;
    }

    // Low balance bonus (encourage earning)
    if (user.credits.balance < 20) {
      multiplier *= 1.3;
    }

    return Math.round(multiplier * 100) / 100;
  }

  getAlternativeEarningMethods() {
    return [
      {
        method: 'reviews',
        description: 'Write product reviews',
        reward: '5-15 CCC per review',
        time: '5-10 minutes'
      },
      {
        method: 'education',
        description: 'Complete learning activities',
        reward: '3-8 CCC per activity',
        time: '10-30 minutes'
      },
      {
        method: 'referrals',
        description: 'Invite friends to ActiveLog',
        reward: '25 CCC per signup',
        time: 'Varies'
      }
    ];
  }

  getBalanceRecommendations(current, target) {
    const needed = target - current;
    const recommendations = [];

    if (needed <= 10) {
      recommendations.push({
        type: 'quick',
        message: 'Watch 2-3 ads to reach ad-free status',
        action: 'watch_ads',
        timeEstimate: '5 minutes'
      });
    } else if (needed <= 50) {
      recommendations.push({
        type: 'moderate',
        message: 'Complete a few reviews or educational activities',
        action: 'mixed_earning',
        timeEstimate: '20-30 minutes'
      });
    } else {
      recommendations.push({
        type: 'long_term',
        message: 'Consider upgrading or building credits over time',
        action: 'upgrade_plan',
        timeEstimate: 'Long term'
      });
    }

    return recommendations;
  }

  generateMockAd(type) {
    const mockAds = {
      banner: {
        title: 'ActiveLog Pro',
        description: 'Upgrade to unlock unlimited compute credits',
        imageUrl: '/api/ads/mock/banner.jpg',
        clickUrl: '/upgrade'
      },
      interstitial: {
        title: 'CloudCompute Services',
        description: 'Professional cloud computing for developers',
        imageUrl: '/api/ads/mock/interstitial.jpg',
        clickUrl: 'https://example.com/cloud'
      },
      video: {
        title: 'Learn AI Development',
        description: '30-day free course on machine learning',
        videoUrl: '/api/ads/mock/video.mp4',
        duration: 30,
        clickUrl: 'https://example.com/ai-course'
      },
      startup: {
        title: 'Welcome to ActiveLog!',
        description: 'Thank you for using our platform. Ads help keep ActiveLog free.',
        imageUrl: '/api/ads/mock/welcome.jpg'
      }
    };

    return mockAds[type] || mockAds.banner;
  }
}

module.exports = AdEngineController;