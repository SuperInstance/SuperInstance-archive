import AsyncStorage from '@react-native-async-storage/async-storage';
import * as StoreReview from 'expo-store-review';
import { Platform } from 'react-native';
import { AnalyticsService } from './analytics';
import { CrashReportingService } from './crash-reporting';

export interface ReviewPromptConfig {
  // Timing configurations
  minUsageDays: number;
  minSessionCount: number;
  minActionCount: number;
  
  // Behavioral triggers
  significantActions: string[];
  positiveEvents: string[];
  
  // Display rules
  maxPromptsPerVersion: number;
  daysBetweenPrompts: number;
  cooldownAfterNegative: number;
  
  // A/B testing
  promptVariant?: 'standard' | 'contextual' | 'gamified';
  
  // Custom messaging
  customPrompts?: {
    title: string;
    message: string;
    positiveButton: string;
    neutralButton: string;
    negativeButton: string;
  };
}

export interface ReviewPromptTrigger {
  eventType: 'session_milestone' | 'feature_success' | 'achievement_unlocked' | 'positive_outcome' | 'manual';
  context?: Record<string, any>;
  timestamp: Date;
  sessionId?: string;
}

export interface UserReviewHistory {
  hasRatedApp: boolean;
  hasDeclinedReview: boolean;
  promptCount: number;
  lastPromptDate: Date | null;
  lastPositiveInteraction: Date | null;
  lastNegativeResponse: Date | null;
  currentVersion: string;
  reviewPromptVersion: number;
}

export interface ReviewMetrics {
  totalPrompts: number;
  promptsAccepted: number;
  promptsDeclined: number;
  promptsDeferred: number;
  conversionRate: number;
  averageTimeToReview: number;
  userSatisfactionScore?: number;
}

class AppReviewServiceClass {
  private config: ReviewPromptConfig;
  private isInitialized = false;
  private userHistory: UserReviewHistory | null = null;
  private sessionStartTime: Date = new Date();
  private sessionActionCount = 0;
  private recentPositiveEvents: string[] = [];
  
  constructor() {
    // Default configuration - can be customized per app variant
    this.config = {
      minUsageDays: 3,
      minSessionCount: 5,
      minActionCount: 10,
      
      significantActions: [
        'item_created',
        'goal_completed',
        'milestone_reached',
        'feature_mastered',
        'data_exported',
        'sharing_completed'
      ],
      
      positiveEvents: [
        'task_completed',
        'goal_achieved',
        'streak_maintained',
        'level_unlocked',
        'positive_outcome',
        'success_celebration'
      ],
      
      maxPromptsPerVersion: 3,
      daysBetweenPrompts: 14,
      cooldownAfterNegative: 30,
      
      promptVariant: 'standard'
    };
  }

  public async initialize(appVariant?: string): Promise<void> {
    try {
      // Customize config based on app variant
      this.customizeConfigForVariant(appVariant);
      
      // Load user review history
      await this.loadUserHistory();
      
      // Initialize session tracking
      this.sessionStartTime = new Date();
      this.sessionActionCount = 0;
      this.recentPositiveEvents = [];
      
      this.isInitialized = true;
      
      console.log('⭐ App Review Service initialized');
    } catch (error) {
      console.error('Failed to initialize app review service:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'app_review',
        action: 'initialize'
      });
    }
  }

  public async trackUserAction(actionType: string, context?: Record<string, any>): Promise<void> {
    if (!this.isInitialized) return;

    try {
      this.sessionActionCount++;
      
      // Track significant actions
      if (this.config.significantActions.includes(actionType)) {
        await this.recordSignificantAction(actionType, context);
      }
      
      // Track positive events
      if (this.config.positiveEvents.includes(actionType)) {
        this.recentPositiveEvents.push(actionType);
        await this.recordPositiveEvent(actionType, context);
        
        // Check if we should trigger a review prompt
        await this.evaluateReviewPromptTrigger({
          eventType: 'positive_outcome',
          context: { actionType, ...context },
          timestamp: new Date()
        });
      }
      
      // Track analytics
      AnalyticsService.track('user_action_tracked', {
        action_type: actionType,
        session_action_count: this.sessionActionCount,
        context
      });
      
    } catch (error) {
      console.error('Failed to track user action:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'app_review',
        action: 'track_user_action',
        actionType
      });
    }
  }

  public async trackMilestone(milestoneType: string, details?: Record<string, any>): Promise<void> {
    if (!this.isInitialized) return;

    try {
      // Record milestone achievement
      await this.recordMilestone(milestoneType, details);
      
      // Evaluate if this milestone warrants a review prompt
      await this.evaluateReviewPromptTrigger({
        eventType: 'achievement_unlocked',
        context: { milestoneType, ...details },
        timestamp: new Date()
      });
      
      AnalyticsService.track('milestone_achieved', {
        milestone_type: milestoneType,
        details
      });
      
    } catch (error) {
      console.error('Failed to track milestone:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'app_review',
        action: 'track_milestone',
        milestoneType
      });
    }
  }

  public async trackFeatureSuccess(featureName: string, successMetric?: Record<string, any>): Promise<void> {
    if (!this.isInitialized) return;

    try {
      await this.evaluateReviewPromptTrigger({
        eventType: 'feature_success',
        context: { featureName, ...successMetric },
        timestamp: new Date()
      });
      
      AnalyticsService.track('feature_success', {
        feature_name: featureName,
        success_metric: successMetric
      });
      
    } catch (error) {
      console.error('Failed to track feature success:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'app_review',
        action: 'track_feature_success',
        featureName
      });
    }
  }

  public async requestReview(trigger: ReviewPromptTrigger): Promise<boolean> {
    if (!this.isInitialized || !this.userHistory) return false;

    try {
      // Check if review request is appropriate
      if (!await this.shouldRequestReview()) {
        console.log('Review request blocked by eligibility rules');
        return false;
      }
      
      // Track review request attempt
      AnalyticsService.track('review_prompt_triggered', {
        trigger_type: trigger.eventType,
        context: trigger.context,
        user_session_count: await this.getUserSessionCount(),
        days_since_install: await this.getDaysSinceInstall()
      });
      
      // Show appropriate review prompt based on variant
      const success = await this.showReviewPrompt(trigger);
      
      if (success) {
        // Update user history
        this.userHistory.promptCount++;
        this.userHistory.lastPromptDate = new Date();
        await this.saveUserHistory();
        
        AnalyticsService.track('review_prompt_shown', {
          prompt_variant: this.config.promptVariant,
          prompt_count: this.userHistory.promptCount
        });
      }
      
      return success;
    } catch (error) {
      console.error('Failed to request review:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'app_review',
        action: 'request_review',
        trigger: trigger.eventType
      });
      return false;
    }
  }

  public async handleReviewResponse(response: 'accepted' | 'declined' | 'deferred', context?: Record<string, any>): Promise<void> {
    if (!this.isInitialized || !this.userHistory) return;

    try {
      const now = new Date();
      
      switch (response) {
        case 'accepted':
          this.userHistory.hasRatedApp = true;
          this.userHistory.lastPositiveInteraction = now;
          break;
          
        case 'declined':
          this.userHistory.hasDeclinedReview = true;
          this.userHistory.lastNegativeResponse = now;
          break;
          
        case 'deferred':
          // User chose "maybe later" - don't mark as declined
          break;
      }
      
      await this.saveUserHistory();
      
      // Track response analytics
      AnalyticsService.track('review_response', {
        response,
        prompt_variant: this.config.promptVariant,
        context,
        session_duration: new Date().getTime() - this.sessionStartTime.getTime()
      });
      
      // If user accepted, trigger native review flow
      if (response === 'accepted') {
        await this.triggerNativeReview();
      }
      
    } catch (error) {
      console.error('Failed to handle review response:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'app_review',
        action: 'handle_review_response',
        response
      });
    }
  }

  public async getReviewMetrics(): Promise<ReviewMetrics> {
    try {
      const history = await this.loadUserHistory();
      const totalPrompts = history?.promptCount || 0;
      
      // This would typically come from analytics aggregation
      const metrics: ReviewMetrics = {
        totalPrompts,
        promptsAccepted: history?.hasRatedApp ? 1 : 0,
        promptsDeclined: history?.hasDeclinedReview ? 1 : 0,
        promptsDeferred: Math.max(0, totalPrompts - (history?.hasRatedApp ? 1 : 0) - (history?.hasDeclinedReview ? 1 : 0)),
        conversionRate: totalPrompts > 0 ? (history?.hasRatedApp ? 1 : 0) / totalPrompts : 0,
        averageTimeToReview: 0 // Would need to track this separately
      };
      
      return metrics;
    } catch (error) {
      console.error('Failed to get review metrics:', error);
      return {
        totalPrompts: 0,
        promptsAccepted: 0,
        promptsDeclined: 0,
        promptsDeferred: 0,
        conversionRate: 0,
        averageTimeToReview: 0
      };
    }
  }

  private async evaluateReviewPromptTrigger(trigger: ReviewPromptTrigger): Promise<void> {
    if (!this.userHistory) return;

    try {
      // Check basic eligibility
      if (!await this.shouldRequestReview()) return;
      
      // Evaluate trigger-specific conditions
      let shouldTrigger = false;
      
      switch (trigger.eventType) {
        case 'session_milestone':
          shouldTrigger = await this.evaluateSessionMilestone();
          break;
          
        case 'feature_success':
          shouldTrigger = await this.evaluateFeatureSuccess(trigger);
          break;
          
        case 'achievement_unlocked':
          shouldTrigger = await this.evaluateAchievement(trigger);
          break;
          
        case 'positive_outcome':
          shouldTrigger = await this.evaluatePositiveOutcome(trigger);
          break;
          
        case 'manual':
          shouldTrigger = true; // Manual triggers bypass automatic evaluation
          break;
      }
      
      if (shouldTrigger) {
        // Add small delay for better UX
        setTimeout(async () => {
          await this.requestReview(trigger);
        }, 1000);
      }
      
    } catch (error) {
      console.error('Failed to evaluate review prompt trigger:', error);
    }
  }

  private async shouldRequestReview(): Promise<boolean> {
    if (!this.userHistory) return false;
    
    try {
      // Don't prompt if already rated
      if (this.userHistory.hasRatedApp) return false;
      
      // Check if we've hit the maximum prompts for this version
      if (this.userHistory.promptCount >= this.config.maxPromptsPerVersion) return false;
      
      // Check minimum usage requirements
      const daysSinceInstall = await this.getDaysSinceInstall();
      if (daysSinceInstall < this.config.minUsageDays) return false;
      
      const sessionCount = await this.getUserSessionCount();
      if (sessionCount < this.config.minSessionCount) return false;
      
      const actionCount = await this.getUserActionCount();
      if (actionCount < this.config.minActionCount) return false;
      
      // Check cooldown periods
      if (this.userHistory.lastPromptDate) {
        const daysSinceLastPrompt = Math.floor((new Date().getTime() - this.userHistory.lastPromptDate.getTime()) / (1000 * 60 * 60 * 24));
        if (daysSinceLastPrompt < this.config.daysBetweenPrompts) return false;
      }
      
      // Check negative response cooldown
      if (this.userHistory.lastNegativeResponse) {
        const daysSinceNegative = Math.floor((new Date().getTime() - this.userHistory.lastNegativeResponse.getTime()) / (1000 * 60 * 60 * 24));
        if (daysSinceNegative < this.config.cooldownAfterNegative) return false;
      }
      
      // Check if native review is available
      if (!await StoreReview.hasAction()) return false;
      
      return true;
    } catch (error) {
      console.error('Failed to check review eligibility:', error);
      return false;
    }
  }

  private async evaluateSessionMilestone(): Promise<boolean> {
    const sessionCount = await this.getUserSessionCount();
    const milestones = [5, 10, 25, 50, 100];
    return milestones.includes(sessionCount);
  }

  private async evaluateFeatureSuccess(trigger: ReviewPromptTrigger): Promise<boolean> {
    // Trigger after user successfully completes a complex feature
    const featureName = trigger.context?.featureName;
    const complexFeatures = ['data_export', 'advanced_analytics', 'collaboration_setup', 'automation_created'];
    return complexFeatures.includes(featureName);
  }

  private async evaluateAchievement(trigger: ReviewPromptTrigger): Promise<boolean> {
    // Trigger on significant achievements
    const milestoneType = trigger.context?.milestoneType;
    const significantMilestones = ['first_goal_completed', '7_day_streak', '30_day_streak', 'power_user_unlocked'];
    return significantMilestones.includes(milestoneType);
  }

  private async evaluatePositiveOutcome(trigger: ReviewPromptTrigger): Promise<boolean> {
    // Trigger after multiple recent positive events
    return this.recentPositiveEvents.length >= 3;
  }

  private async showReviewPrompt(trigger: ReviewPromptTrigger): Promise<boolean> {
    try {
      // For now, we'll use the native review prompt directly
      // In a real implementation, you might show a custom dialog first
      
      if (this.config.promptVariant === 'contextual') {
        // Show contextual prompt based on trigger
        return await this.showContextualPrompt(trigger);
      } else if (this.config.promptVariant === 'gamified') {
        // Show gamified prompt with rewards
        return await this.showGamifiedPrompt(trigger);
      } else {
        // Standard prompt
        return await this.showStandardPrompt();
      }
    } catch (error) {
      console.error('Failed to show review prompt:', error);
      return false;
    }
  }

  private async showStandardPrompt(): Promise<boolean> {
    try {
      // Use native store review
      await StoreReview.requestReview();
      return true;
    } catch (error) {
      console.error('Failed to show standard review prompt:', error);
      return false;
    }
  }

  private async showContextualPrompt(trigger: ReviewPromptTrigger): Promise<boolean> {
    // This would show a custom dialog with contextual messaging
    // For now, fall back to standard prompt
    return await this.showStandardPrompt();
  }

  private async showGamifiedPrompt(trigger: ReviewPromptTrigger): Promise<boolean> {
    // This would show a gamified dialog with rewards/incentives
    // For now, fall back to standard prompt
    return await this.showStandardPrompt();
  }

  private async triggerNativeReview(): Promise<void> {
    try {
      if (await StoreReview.hasAction()) {
        await StoreReview.requestReview();
      }
    } catch (error) {
      console.error('Failed to trigger native review:', error);
    }
  }

  private customizeConfigForVariant(appVariant?: string): void {
    // Customize configuration based on app variant
    switch (appVariant) {
      case 'personal-log':
        this.config.significantActions.push('journal_entry_created', 'mood_tracked', 'reflection_completed');
        this.config.positiveEvents.push('writing_streak', 'mood_improved', 'insight_discovered');
        break;
        
      case 'business-log':
        this.config.significantActions.push('project_created', 'task_delegated', 'report_generated');
        this.config.positiveEvents.push('deadline_met', 'productivity_increased', 'team_goal_achieved');
        break;
        
      case 'fitness-log':
        this.config.significantActions.push('workout_logged', 'goal_set', 'progress_photo_added');
        this.config.positiveEvents.push('personal_record', 'streak_achieved', 'target_weight_reached');
        break;
        
      case 'family-log':
        this.config.significantActions.push('memory_shared', 'event_planned', 'photo_uploaded');
        this.config.positiveEvents.push('family_moment_captured', 'milestone_celebrated', 'connection_strengthened');
        break;
        
      case 'travel-log':
        this.config.significantActions.push('trip_planned', 'location_tracked', 'expense_logged');
        this.config.positiveEvents.push('trip_completed', 'budget_met', 'memory_documented');
        break;
        
      case 'education-log':
        this.config.significantActions.push('course_added', 'assignment_tracked', 'study_session_logged');
        this.config.positiveEvents.push('grade_improved', 'assignment_completed', 'learning_goal_achieved');
        break;
    }
  }

  private async loadUserHistory(): Promise<UserReviewHistory> {
    try {
      const stored = await AsyncStorage.getItem('app_review_history');
      if (stored) {
        const parsed = JSON.parse(stored);
        // Convert date strings back to Date objects
        if (parsed.lastPromptDate) parsed.lastPromptDate = new Date(parsed.lastPromptDate);
        if (parsed.lastPositiveInteraction) parsed.lastPositiveInteraction = new Date(parsed.lastPositiveInteraction);
        if (parsed.lastNegativeResponse) parsed.lastNegativeResponse = new Date(parsed.lastNegativeResponse);
        
        this.userHistory = parsed;
        return parsed;
      }
    } catch (error) {
      console.error('Failed to load user review history:', error);
    }
    
    // Create new history
    const newHistory: UserReviewHistory = {
      hasRatedApp: false,
      hasDeclinedReview: false,
      promptCount: 0,
      lastPromptDate: null,
      lastPositiveInteraction: null,
      lastNegativeResponse: null,
      currentVersion: '1.0.0', // Should get from app config
      reviewPromptVersion: 1
    };
    
    this.userHistory = newHistory;
    await this.saveUserHistory();
    return newHistory;
  }

  private async saveUserHistory(): Promise<void> {
    if (!this.userHistory) return;
    
    try {
      await AsyncStorage.setItem('app_review_history', JSON.stringify(this.userHistory));
    } catch (error) {
      console.error('Failed to save user review history:', error);
    }
  }

  private async recordSignificantAction(actionType: string, context?: Record<string, any>): Promise<void> {
    try {
      const key = 'significant_actions_count';
      const currentCount = parseInt(await AsyncStorage.getItem(key) || '0');
      await AsyncStorage.setItem(key, (currentCount + 1).toString());
    } catch (error) {
      console.error('Failed to record significant action:', error);
    }
  }

  private async recordPositiveEvent(eventType: string, context?: Record<string, any>): Promise<void> {
    try {
      if (this.userHistory) {
        this.userHistory.lastPositiveInteraction = new Date();
        await this.saveUserHistory();
      }
    } catch (error) {
      console.error('Failed to record positive event:', error);
    }
  }

  private async recordMilestone(milestoneType: string, details?: Record<string, any>): Promise<void> {
    try {
      const key = `milestone_${milestoneType}`;
      await AsyncStorage.setItem(key, JSON.stringify({
        achieved: true,
        timestamp: new Date().toISOString(),
        details
      }));
    } catch (error) {
      console.error('Failed to record milestone:', error);
    }
  }

  private async getDaysSinceInstall(): Promise<number> {
    try {
      const installDate = await AsyncStorage.getItem('app_install_date');
      if (installDate) {
        const install = new Date(installDate);
        return Math.floor((new Date().getTime() - install.getTime()) / (1000 * 60 * 60 * 24));
      }
      
      // Set install date if not exists
      await AsyncStorage.setItem('app_install_date', new Date().toISOString());
      return 0;
    } catch (error) {
      console.error('Failed to get days since install:', error);
      return 0;
    }
  }

  private async getUserSessionCount(): Promise<number> {
    try {
      const count = await AsyncStorage.getItem('user_session_count');
      return parseInt(count || '0');
    } catch (error) {
      console.error('Failed to get user session count:', error);
      return 0;
    }
  }

  private async getUserActionCount(): Promise<number> {
    try {
      const count = await AsyncStorage.getItem('significant_actions_count');
      return parseInt(count || '0');
    } catch (error) {
      console.error('Failed to get user action count:', error);
      return 0;
    }
  }

  public async incrementSessionCount(): Promise<void> {
    try {
      const currentCount = await this.getUserSessionCount();
      await AsyncStorage.setItem('user_session_count', (currentCount + 1).toString());
      
      // Check session milestone
      await this.evaluateReviewPromptTrigger({
        eventType: 'session_milestone',
        timestamp: new Date()
      });
    } catch (error) {
      console.error('Failed to increment session count:', error);
    }
  }

  public getConfig(): ReviewPromptConfig {
    return { ...this.config };
  }

  public updateConfig(updates: Partial<ReviewPromptConfig>): void {
    this.config = { ...this.config, ...updates };
  }

  public getUserHistory(): UserReviewHistory | null {
    return this.userHistory ? { ...this.userHistory } : null;
  }

  public isEligibleForReview(): Promise<boolean> {
    return this.shouldRequestReview();
  }
}

export const AppReviewService = new AppReviewServiceClass();