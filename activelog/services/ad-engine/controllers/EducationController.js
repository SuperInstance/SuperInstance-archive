const User = require('../models/User');
const config = require('../config/config');
const { v4: uuidv4 } = require('uuid');

class EducationController {
  constructor() {
    this.config = config.education;
  }

  // Complete Educational Activity
  async completeActivity(req, res) {
    try {
      const { userId } = req.params;
      const { 
        activityId, 
        activityType, 
        score = 0, 
        timeSpent = 0, 
        metadata = {} 
      } = req.body;

      const user = await User.findByUserId(userId);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // Validate activity completion
      const validation = this.validateActivityCompletion(user, activityType, score, timeSpent);
      if (!validation.valid) {
        return res.status(400).json({ error: validation.reason });
      }

      // Check if activity already completed
      const alreadyCompleted = user.education.completedActivities.find(
        activity => activity.activityId === activityId
      );

      if (alreadyCompleted) {
        return res.status(400).json({ error: 'Activity already completed' });
      }

      // Calculate base reward
      const baseReward = this.config.activityRewards[activityType] || 0;
      
      // Calculate score bonus
      const scoreBonus = this.calculateScoreBonus(score, activityType);
      
      // Calculate streak bonus
      const streakBonus = this.calculateStreakBonus(user);
      
      // Calculate final reward
      const finalReward = Math.round(baseReward + scoreBonus + streakBonus.bonus);

      // Create activity record
      const activityRecord = {
        activityId,
        type: activityType,
        score,
        completedAt: new Date(),
        timeSpent,
        reward: finalReward
      };

      // Update user education stats
      user.education.completedActivities.push(activityRecord);
      user.education.experience += this.calculateExperienceGain(activityType, score);
      
      // Update streak
      this.updateStreak(user);
      
      // Check for level up
      const levelUp = this.checkLevelUp(user);
      if (levelUp.leveled) {
        user.education.level = levelUp.newLevel;
        // Level up bonus
        const levelBonus = levelUp.newLevel * 5;
        await user.addCredits(levelBonus, 'level_up', `Reached level ${levelUp.newLevel}!`);
      }

      // Award credits
      await user.addCredits(
        finalReward,
        'education',
        `Completed ${activityType}: ${activityId}`,
        {
          activityId,
          activityType,
          score,
          timeSpent,
          baseReward,
          scoreBonus,
          streakBonus: streakBonus.bonus,
          streakCount: streakBonus.count
        }
      );

      await user.save();

      // Check for achievements
      const newAchievements = await this.checkAchievements(user);

      res.json({
        success: true,
        activityId,
        rewards: {
          base: baseReward,
          scoreBonus,
          streakBonus: streakBonus.bonus,
          total: finalReward
        },
        progress: {
          experience: user.education.experience,
          level: user.education.level,
          leveledUp: levelUp.leveled,
          streak: {
            current: user.education.streak.current,
            longest: user.education.streak.longest
          }
        },
        newBalance: user.credits.balance,
        achievements: newAchievements
      });

    } catch (error) {
      console.error('Error completing activity:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Get Available Educational Activities
  async getAvailableActivities(req, res) {
    try {
      const { userId } = req.params;
      const { category, difficulty, limit = 20 } = req.query;

      const user = await User.findByUserId(userId);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // Generate available activities based on user level and preferences
      const activities = this.generateAvailableActivities(user, category, difficulty, limit);

      // Calculate potential rewards for each activity
      const activitiesWithRewards = activities.map(activity => ({
        ...activity,
        potentialReward: this.calculatePotentialReward(user, activity.type, activity.difficulty),
        estimatedTime: this.getEstimatedTime(activity.type, activity.difficulty),
        prerequisitesMet: this.checkPrerequisites(user, activity.prerequisites || [])
      }));

      res.json({
        activities: activitiesWithRewards,
        userStats: {
          level: user.education.level,
          experience: user.education.experience,
          streak: user.education.streak.current,
          completedToday: this.getCompletedToday(user).length
        },
        recommendations: this.getPersonalizedRecommendations(user, activitiesWithRewards)
      });

    } catch (error) {
      console.error('Error getting available activities:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Get User Education Progress
  async getEducationProgress(req, res) {
    try {
      const { userId } = req.params;
      const user = await User.findByUserId(userId);

      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      const progress = {
        level: {
          current: user.education.level,
          experience: user.education.experience,
          experienceToNext: this.getExperienceToNextLevel(user.education.level, user.education.experience),
          progress: this.getLevelProgress(user.education.level, user.education.experience)
        },
        streak: {
          current: user.education.streak.current,
          longest: user.education.streak.longest,
          lastActivity: user.education.streak.lastActivity,
          bonusMultiplier: this.getStreakMultiplier(user.education.streak.current)
        },
        activities: {
          total: user.education.completedActivities.length,
          today: this.getCompletedToday(user).length,
          thisWeek: this.getCompletedThisWeek(user).length,
          byType: this.getActivitiesByType(user),
          averageScore: this.getAverageScore(user)
        },
        achievements: {
          unlocked: user.education.achievements.length,
          recent: user.education.achievements.slice(-5),
          next: this.getNextAchievements(user)
        },
        earnings: {
          total: this.getTotalEducationEarnings(user),
          today: this.getTodayEducationEarnings(user),
          thisWeek: this.getThisWeekEducationEarnings(user),
          average: this.getAverageEarningsPerActivity(user)
        }
      };

      res.json(progress);

    } catch (error) {
      console.error('Error getting education progress:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Unlock Achievement
  async unlockAchievement(req, res) {
    try {
      const { userId, achievementId } = req.params;

      const user = await User.findByUserId(userId);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // Check if achievement already unlocked
      const alreadyUnlocked = user.education.achievements.find(
        achievement => achievement.achievementId === achievementId
      );

      if (alreadyUnlocked) {
        return res.status(400).json({ error: 'Achievement already unlocked' });
      }

      // Get achievement details
      const achievement = this.getAchievementDetails(achievementId);
      if (!achievement) {
        return res.status(404).json({ error: 'Achievement not found' });
      }

      // Verify achievement requirements are met
      const meetsRequirements = this.verifyAchievementRequirements(user, achievement);
      if (!meetsRequirements.met) {
        return res.status(400).json({ 
          error: 'Achievement requirements not met',
          missing: meetsRequirements.missing
        });
      }

      // Unlock achievement
      const achievementRecord = {
        achievementId,
        name: achievement.name,
        description: achievement.description,
        unlockedAt: new Date(),
        reward: achievement.reward
      };

      user.education.achievements.push(achievementRecord);

      // Award credits
      await user.addCredits(
        achievement.reward,
        'achievement',
        `Unlocked achievement: ${achievement.name}`,
        { achievementId, category: achievement.category }
      );

      await user.save();

      res.json({
        success: true,
        achievement: achievementRecord,
        reward: achievement.reward,
        newBalance: user.credits.balance,
        totalAchievements: user.education.achievements.length
      });

    } catch (error) {
      console.error('Error unlocking achievement:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Get Learning Recommendations
  async getLearningRecommendations(req, res) {
    try {
      const { userId } = req.params;
      const user = await User.findByUserId(userId);

      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      const recommendations = {
        dailyGoal: this.getDailyGoal(user),
        streakMaintenance: this.getStreakRecommendations(user),
        skillGaps: this.identifySkillGaps(user),
        levelUpStrategy: this.getLevelUpStrategy(user),
        highValueActivities: this.getHighValueActivities(user),
        timeBasedSuggestions: this.getTimeBasedSuggestions(user)
      };

      res.json(recommendations);

    } catch (error) {
      console.error('Error getting learning recommendations:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Helper Methods
  validateActivityCompletion(user, activityType, score, timeSpent) {
    const validTypes = Object.keys(this.config.activityRewards);
    if (!validTypes.includes(activityType)) {
      return { valid: false, reason: 'Invalid activity type' };
    }

    const minimumTimes = {
      quiz: 2,      // 2 minutes minimum
      tutorial: 5,   // 5 minutes minimum
      lesson: 10,    // 10 minutes minimum
      course: 30     // 30 minutes minimum
    };

    const minTime = minimumTimes[activityType] || 5;
    if (timeSpent < minTime) {
      return { valid: false, reason: `Minimum time not met: ${minTime} minutes required` };
    }

    if (score < 0 || score > 100) {
      return { valid: false, reason: 'Score must be between 0 and 100' };
    }

    return { valid: true };
  }

  calculateScoreBonus(score, activityType) {
    if (score < 70) return 0; // No bonus for low scores
    
    const bonusRates = {
      quiz: 0.1,      // 10% of score above 70
      tutorial: 0.05,  // 5% of score above 70
      lesson: 0.08,    // 8% of score above 70
      course: 0.15     // 15% of score above 70
    };

    const rate = bonusRates[activityType] || 0.05;
    return Math.round((score - 70) * rate);
  }

  calculateStreakBonus(user) {
    const streak = user.education.streak.current;
    const bonuses = this.config.streakBonuses;
    
    let multiplier = 1.0;
    let bonus = 0;

    if (streak >= 90) {
      multiplier = bonuses.quarter;
      bonus = 10;
    } else if (streak >= 30) {
      multiplier = bonuses.month;
      bonus = 5;
    } else if (streak >= 7) {
      multiplier = bonuses.week;
      bonus = 2;
    }

    return {
      count: streak,
      multiplier,
      bonus: Math.round(bonus * (1 + streak / 100))
    };
  }

  calculateExperienceGain(activityType, score) {
    const baseXP = {
      quiz: 10,
      tutorial: 25,
      lesson: 50,
      course: 200
    };

    const base = baseXP[activityType] || 10;
    const scoreMultiplier = 1 + (score / 100);
    return Math.round(base * scoreMultiplier);
  }

  updateStreak(user) {
    const now = new Date();
    const lastActivity = user.education.streak.lastActivity;
    
    if (!lastActivity) {
      // First activity
      user.education.streak.current = 1;
      user.education.streak.longest = 1;
    } else {
      const daysDiff = Math.floor((now - lastActivity) / (1000 * 60 * 60 * 24));
      
      if (daysDiff === 0) {
        // Same day, streak continues
        // Don't increment streak counter for multiple activities on same day
      } else if (daysDiff === 1) {
        // Next day, increment streak
        user.education.streak.current += 1;
        if (user.education.streak.current > user.education.streak.longest) {
          user.education.streak.longest = user.education.streak.current;
        }
      } else {
        // Streak broken
        user.education.streak.current = 1;
      }
    }
    
    user.education.streak.lastActivity = now;
  }

  checkLevelUp(user) {
    const currentLevel = user.education.level;
    const experience = user.education.experience;
    const newLevel = this.calculateLevelFromExperience(experience);
    
    return {
      leveled: newLevel > currentLevel,
      newLevel: newLevel,
      experienceRequired: this.getExperienceForLevel(newLevel + 1)
    };
  }

  calculateLevelFromExperience(experience) {
    // Exponential leveling system
    return Math.floor(Math.sqrt(experience / 100)) + 1;
  }

  getExperienceForLevel(level) {
    return (level - 1) ** 2 * 100;
  }

  getExperienceToNextLevel(currentLevel, experience) {
    const nextLevelExp = this.getExperienceForLevel(currentLevel + 1);
    return Math.max(0, nextLevelExp - experience);
  }

  getLevelProgress(currentLevel, experience) {
    const currentLevelExp = this.getExperienceForLevel(currentLevel);
    const nextLevelExp = this.getExperienceForLevel(currentLevel + 1);
    const progress = (experience - currentLevelExp) / (nextLevelExp - currentLevelExp);
    return Math.min(Math.max(progress, 0), 1);
  }

  generateAvailableActivities(user, category, difficulty, limit) {
    // Mock activity generation - in real app, this would query a database
    const activityTypes = ['quiz', 'tutorial', 'lesson', 'course'];
    const categories = ['programming', 'data-science', 'design', 'business', 'math', 'science'];
    const difficulties = ['beginner', 'intermediate', 'advanced'];
    
    const activities = [];
    
    for (let i = 0; i < limit; i++) {
      const type = activityTypes[Math.floor(Math.random() * activityTypes.length)];
      const cat = category || categories[Math.floor(Math.random() * categories.length)];
      const diff = difficulty || difficulties[Math.floor(Math.random() * difficulties.length)];
      
      activities.push({
        id: `activity_${i + 1}`,
        type,
        category: cat,
        difficulty: diff,
        title: this.generateActivityTitle(type, cat, diff),
        description: this.generateActivityDescription(type, cat),
        estimatedDuration: this.getEstimatedTime(type, diff),
        prerequisites: this.getPrerequisites(type, diff)
      });
    }
    
    return activities;
  }

  calculatePotentialReward(user, activityType, difficulty) {
    const baseReward = this.config.activityRewards[activityType] || 0;
    const difficultyMultiplier = { beginner: 1.0, intermediate: 1.3, advanced: 1.6 };
    const streakBonus = this.calculateStreakBonus(user);
    
    const multiplier = difficultyMultiplier[difficulty] || 1.0;
    return Math.round(baseReward * multiplier * streakBonus.multiplier);
  }

  getEstimatedTime(activityType, difficulty) {
    const baseTimes = {
      quiz: { beginner: 5, intermediate: 8, advanced: 12 },
      tutorial: { beginner: 15, intermediate: 25, advanced: 40 },
      lesson: { beginner: 30, intermediate: 45, advanced: 60 },
      course: { beginner: 120, intermediate: 180, advanced: 300 }
    };
    
    return baseTimes[activityType]?.[difficulty] || 15;
  }

  checkPrerequisites(user, prerequisites) {
    if (!prerequisites || prerequisites.length === 0) return true;
    
    const completed = user.education.completedActivities.map(a => a.activityId);
    return prerequisites.every(prereq => completed.includes(prereq));
  }

  async checkAchievements(user) {
    const newAchievements = [];
    const possibleAchievements = this.getAllAchievements();
    const unlockedIds = user.education.achievements.map(a => a.achievementId);
    
    for (const achievement of possibleAchievements) {
      if (!unlockedIds.includes(achievement.id)) {
        const meetsRequirements = this.verifyAchievementRequirements(user, achievement);
        if (meetsRequirements.met) {
          const achievementRecord = {
            achievementId: achievement.id,
            name: achievement.name,
            description: achievement.description,
            unlockedAt: new Date(),
            reward: achievement.reward
          };
          
          user.education.achievements.push(achievementRecord);
          newAchievements.push(achievementRecord);
          
          await user.addCredits(
            achievement.reward,
            'achievement',
            `Unlocked achievement: ${achievement.name}`,
            { achievementId: achievement.id }
          );
        }
      }
    }
    
    return newAchievements;
  }

  // Mock data generation methods
  generateActivityTitle(type, category, difficulty) {
    const titles = {
      quiz: `${category.charAt(0).toUpperCase() + category.slice(1)} ${difficulty} Quiz`,
      tutorial: `Interactive ${category.charAt(0).toUpperCase() + category.slice(1)} Tutorial`,
      lesson: `${difficulty.charAt(0).toUpperCase() + difficulty.slice(1)} ${category} Lesson`,
      course: `Complete ${category.charAt(0).toUpperCase() + category.slice(1)} Course`
    };
    
    return titles[type] || `${category} Activity`;
  }

  generateActivityDescription(type, category) {
    return `Learn ${category} concepts through this interactive ${type}. Perfect for building your skills and earning credits!`;
  }

  getPrerequisites(type, difficulty) {
    if (difficulty === 'beginner') return [];
    if (difficulty === 'intermediate') return ['basic_' + type];
    return ['basic_' + type, 'intermediate_' + type];
  }

  // Statistics and analytics methods
  getCompletedToday(user) {
    const today = new Date().toDateString();
    return user.education.completedActivities.filter(activity =>
      activity.completedAt.toDateString() === today
    );
  }

  getCompletedThisWeek(user) {
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    return user.education.completedActivities.filter(activity =>
      activity.completedAt >= weekAgo
    );
  }

  getActivitiesByType(user) {
    const byType = {};
    user.education.completedActivities.forEach(activity => {
      byType[activity.type] = (byType[activity.type] || 0) + 1;
    });
    return byType;
  }

  getAverageScore(user) {
    const activities = user.education.completedActivities;
    if (activities.length === 0) return 0;
    
    const totalScore = activities.reduce((sum, activity) => sum + activity.score, 0);
    return Math.round(totalScore / activities.length);
  }

  getTotalEducationEarnings(user) {
    return user.credits.transactions
      .filter(tx => tx.source === 'education' || tx.source === 'achievement')
      .reduce((sum, tx) => sum + tx.amount, 0);
  }

  getTodayEducationEarnings(user) {
    const today = new Date().toDateString();
    return user.credits.transactions
      .filter(tx => 
        (tx.source === 'education' || tx.source === 'achievement') &&
        tx.timestamp.toDateString() === today
      )
      .reduce((sum, tx) => sum + tx.amount, 0);
  }

  getThisWeekEducationEarnings(user) {
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    return user.credits.transactions
      .filter(tx => 
        (tx.source === 'education' || tx.source === 'achievement') &&
        tx.timestamp >= weekAgo
      )
      .reduce((sum, tx) => sum + tx.amount, 0);
  }

  getAverageEarningsPerActivity(user) {
    const activities = user.education.completedActivities;
    if (activities.length === 0) return 0;
    
    const totalEarnings = activities.reduce((sum, activity) => sum + activity.reward, 0);
    return Math.round(totalEarnings / activities.length);
  }

  // Achievement system methods
  getAllAchievements() {
    return [
      {
        id: 'first_steps',
        name: 'First Steps',
        description: 'Complete your first educational activity',
        reward: 10,
        requirements: { activitiesCompleted: 1 }
      },
      {
        id: 'streak_week',
        name: 'Week Warrior',
        description: 'Maintain a 7-day learning streak',
        reward: 25,
        requirements: { streak: 7 }
      },
      {
        id: 'quiz_master',
        name: 'Quiz Master',
        description: 'Complete 10 quizzes',
        reward: 30,
        requirements: { quizzes: 10 }
      },
      {
        id: 'perfect_score',
        name: 'Perfect Score',
        description: 'Get 100% on any activity',
        reward: 20,
        requirements: { perfectScore: true }
      },
      {
        id: 'level_5',
        name: 'Knowledge Seeker',
        description: 'Reach level 5',
        reward: 50,
        requirements: { level: 5 }
      }
    ];
  }

  getAchievementDetails(achievementId) {
    return this.getAllAchievements().find(a => a.id === achievementId);
  }

  verifyAchievementRequirements(user, achievement) {
    const req = achievement.requirements;
    const missing = [];

    if (req.activitiesCompleted && user.education.completedActivities.length < req.activitiesCompleted) {
      missing.push(`Complete ${req.activitiesCompleted} activities`);
    }

    if (req.streak && user.education.streak.current < req.streak) {
      missing.push(`Maintain ${req.streak}-day streak`);
    }

    if (req.quizzes) {
      const quizCount = user.education.completedActivities.filter(a => a.type === 'quiz').length;
      if (quizCount < req.quizzes) {
        missing.push(`Complete ${req.quizzes} quizzes`);
      }
    }

    if (req.perfectScore) {
      const hasPerfectScore = user.education.completedActivities.some(a => a.score === 100);
      if (!hasPerfectScore) {
        missing.push('Get a perfect score (100%)');
      }
    }

    if (req.level && user.education.level < req.level) {
      missing.push(`Reach level ${req.level}`);
    }

    return {
      met: missing.length === 0,
      missing
    };
  }

  // Recommendation system methods
  getDailyGoal(user) {
    const completedToday = this.getCompletedToday(user).length;
    const recommendedDaily = Math.max(1, Math.floor(user.education.level / 2));
    
    return {
      recommended: recommendedDaily,
      completed: completedToday,
      remaining: Math.max(0, recommendedDaily - completedToday),
      progress: Math.min(completedToday / recommendedDaily, 1)
    };
  }

  getStreakRecommendations(user) {
    const streak = user.education.streak.current;
    const lastActivity = user.education.streak.lastActivity;
    
    if (!lastActivity) {
      return {
        message: 'Start your learning streak today!',
        urgency: 'low',
        suggestion: 'Complete any quiz or tutorial to begin'
      };
    }
    
    const hoursSinceLastActivity = (Date.now() - lastActivity.getTime()) / (1000 * 60 * 60);
    
    if (hoursSinceLastActivity > 20) {
      return {
        message: 'Your streak is at risk!',
        urgency: 'high',
        suggestion: 'Complete an activity soon to maintain your streak',
        hoursRemaining: Math.max(0, 24 - hoursSinceLastActivity)
      };
    }
    
    return {
      message: `Great ${streak}-day streak!`,
      urgency: 'low',
      suggestion: 'Keep it up tomorrow to continue growing your streak'
    };
  }

  identifySkillGaps(user) {
    const completed = user.education.completedActivities;
    const categories = {};
    
    completed.forEach(activity => {
      if (activity.metadata && activity.metadata.category) {
        categories[activity.metadata.category] = (categories[activity.metadata.category] || 0) + 1;
      }
    });
    
    const allCategories = ['programming', 'data-science', 'design', 'business', 'math', 'science'];
    const gaps = allCategories.filter(cat => !categories[cat] || categories[cat] < 3);
    
    return gaps.map(gap => ({
      category: gap,
      recommendation: `Try some ${gap} activities to broaden your skills`,
      potentialReward: this.config.activityRewards.lesson
    }));
  }

  getLevelUpStrategy(user) {
    const currentLevel = user.education.level;
    const experience = user.education.experience;
    const expToNext = this.getExperienceToNextLevel(currentLevel, experience);
    
    const strategies = [];
    
    // Calculate activities needed
    const avgExpPerActivity = 40; // Estimate
    const activitiesNeeded = Math.ceil(expToNext / avgExpPerActivity);
    
    strategies.push({
      type: 'activities',
      description: `Complete ~${activitiesNeeded} more activities to level up`,
      timeEstimate: `${activitiesNeeded * 20} minutes`
    });
    
    // High-value activities
    strategies.push({
      type: 'courses',
      description: 'Complete a course for maximum experience gain',
      timeEstimate: '2-3 hours',
      reward: 'Large XP boost'
    });
    
    return {
      currentLevel,
      nextLevel: currentLevel + 1,
      experienceNeeded: expToNext,
      strategies
    };
  }

  getHighValueActivities(user) {
    return [
      {
        type: 'course',
        reason: 'Highest CCC and XP reward',
        potentialReward: this.calculatePotentialReward(user, 'course', 'intermediate'),
        timeInvestment: 'High'
      },
      {
        type: 'lesson',
        reason: 'Good balance of time and reward',
        potentialReward: this.calculatePotentialReward(user, 'lesson', 'intermediate'),
        timeInvestment: 'Medium'
      }
    ];
  }

  getTimeBasedSuggestions(user) {
    const hour = new Date().getHours();
    
    if (hour < 12) {
      return {
        timeOfDay: 'morning',
        suggestion: 'Start your day with a quick quiz!',
        recommendedType: 'quiz',
        reason: 'Light activity to warm up your brain'
      };
    } else if (hour < 17) {
      return {
        timeOfDay: 'afternoon',
        suggestion: 'Perfect time for a tutorial or lesson',
        recommendedType: 'lesson',
        reason: 'Peak learning hours for focused content'
      };
    } else {
      return {
        timeOfDay: 'evening',
        suggestion: 'Wind down with an easy tutorial',
        recommendedType: 'tutorial',
        reason: 'Light learning before the day ends'
      };
    }
  }

  getPersonalizedRecommendations(user, activities) {
    const completed = user.education.completedActivities;
    const preferences = this.analyzeUserPreferences(completed);
    
    return activities
      .filter(activity => 
        !preferences.avoidedTypes.includes(activity.type) &&
        preferences.preferredCategories.includes(activity.category)
      )
      .sort((a, b) => b.potentialReward - a.potentialReward)
      .slice(0, 5)
      .map(activity => ({
        ...activity,
        recommendationReason: this.getRecommendationReason(activity, preferences)
      }));
  }

  analyzeUserPreferences(completedActivities) {
    const typeScores = {};
    const categoryScores = {};
    
    completedActivities.forEach(activity => {
      typeScores[activity.type] = (typeScores[activity.type] || 0) + activity.score;
      
      if (activity.metadata && activity.metadata.category) {
        categoryScores[activity.metadata.category] = 
          (categoryScores[activity.metadata.category] || 0) + activity.score;
      }
    });
    
    const preferredTypes = Object.entries(typeScores)
      .sort(([,a], [,b]) => b - a)
      .map(([type]) => type);
      
    const preferredCategories = Object.entries(categoryScores)
      .sort(([,a], [,b]) => b - a)
      .map(([category]) => category);
    
    return {
      preferredTypes: preferredTypes.slice(0, 2),
      avoidedTypes: preferredTypes.slice(-1),
      preferredCategories: preferredCategories.slice(0, 3)
    };
  }

  getRecommendationReason(activity, preferences) {
    if (preferences.preferredTypes.includes(activity.type)) {
      return `You perform well in ${activity.type}s`;
    }
    if (preferences.preferredCategories.includes(activity.category)) {
      return `Matches your interest in ${activity.category}`;
    }
    return 'High reward potential';
  }

  getStreakMultiplier(streakCount) {
    if (streakCount >= 90) return this.config.streakBonuses.quarter;
    if (streakCount >= 30) return this.config.streakBonuses.month;
    if (streakCount >= 7) return this.config.streakBonuses.week;
    return 1.0;
  }

  getNextAchievements(user) {
    const allAchievements = this.getAllAchievements();
    const unlockedIds = user.education.achievements.map(a => a.achievementId);
    
    return allAchievements
      .filter(achievement => !unlockedIds.includes(achievement.id))
      .map(achievement => {
        const requirements = this.verifyAchievementRequirements(user, achievement);
        return {
          ...achievement,
          progress: this.calculateAchievementProgress(user, achievement),
          missing: requirements.missing
        };
      })
      .sort((a, b) => b.progress - a.progress)
      .slice(0, 3);
  }

  calculateAchievementProgress(user, achievement) {
    const req = achievement.requirements;
    let progress = 0;
    let total = 0;

    if (req.activitiesCompleted) {
      progress += Math.min(user.education.completedActivities.length, req.activitiesCompleted);
      total += req.activitiesCompleted;
    }

    if (req.streak) {
      progress += Math.min(user.education.streak.current, req.streak);
      total += req.streak;
    }

    if (req.level) {
      progress += Math.min(user.education.level, req.level);
      total += req.level;
    }

    return total > 0 ? progress / total : 0;
  }
}

module.exports = EducationController;