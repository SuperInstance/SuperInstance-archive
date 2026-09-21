import { useState, useEffect, useCallback, useRef } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import { AppReviewService, ReviewPromptTrigger } from '../services/app-review';
import { AnalyticsService } from '../services/analytics';
import { ABTestingService } from '../services/ab-testing';

export interface UseAppRatingConfig {
  appVariant?: string;
  enableAutoPrompt?: boolean;
  enableSessionTracking?: boolean;
  enableActionTracking?: boolean;
  debugMode?: boolean;
}

export interface AppRatingState {
  isPromptVisible: boolean;
  promptVariant: 'standard' | 'contextual' | 'gamified';
  promptContext?: {
    trigger: string;
    achievement?: string;
    feature?: string;
  };
  canShowPrompt: boolean;
  userHistory: any;
  sessionMetrics: {
    sessionCount: number;
    actionCount: number;
    daysSinceInstall: number;
  };
}

export interface AppRatingActions {
  showPrompt: (trigger?: ReviewPromptTrigger) => Promise<void>;
  hidePrompt: () => void;
  trackAction: (actionType: string, context?: Record<string, any>) => Promise<void>;
  trackMilestone: (milestoneType: string, details?: Record<string, any>) => Promise<void>;
  trackFeatureSuccess: (featureName: string, successMetric?: Record<string, any>) => Promise<void>;
  forcePrompt: () => Promise<void>;
  resetRatingState: () => Promise<void>;
  checkEligibility: () => Promise<boolean>;
}

export const useAppRating = (config: UseAppRatingConfig = {}): [AppRatingState, AppRatingActions] => {
  const {
    appVariant,
    enableAutoPrompt = true,
    enableSessionTracking = true,
    enableActionTracking = true,
    debugMode = false
  } = config;

  const [state, setState] = useState<AppRatingState>({
    isPromptVisible: false,
    promptVariant: 'standard',
    canShowPrompt: false,
    userHistory: null,
    sessionMetrics: {
      sessionCount: 0,
      actionCount: 0,
      daysSinceInstall: 0
    }
  });

  const appStateRef = useRef<AppStateStatus>(AppState.currentState);
  const sessionStartTime = useRef<Date>(new Date());
  const isInitialized = useRef(false);

  // Initialize the hook
  useEffect(() => {
    if (!isInitialized.current) {
      initializeRatingService();
      isInitialized.current = true;
    }
  }, []);

  // Set up app state listeners for session tracking
  useEffect(() => {
    if (!enableSessionTracking) return;

    const handleAppStateChange = (nextAppState: AppStateStatus) => {
      if (appStateRef.current.match(/inactive|background/) && nextAppState === 'active') {
        // App came to foreground
        handleSessionStart();
      } else if (appStateRef.current === 'active' && nextAppState.match(/inactive|background/)) {
        // App went to background
        handleSessionEnd();
      }
      appStateRef.current = nextAppState;
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    
    return () => {
      subscription?.remove();
    };
  }, [enableSessionTracking]);

  const initializeRatingService = useCallback(async () => {
    try {
      await AppReviewService.initialize(appVariant);
      
      // Get A/B test variant for rating prompt
      const abTestVariant = await ABTestingService.getVariant('rating_prompt_variant', 'standard');
      const promptVariant = typeof abTestVariant === 'string' ? abTestVariant : 'standard';
      
      // Load initial state
      const canShow = await AppReviewService.isEligibleForReview();
      const history = AppReviewService.getUserHistory();
      
      setState(prev => ({
        ...prev,
        promptVariant: promptVariant as 'standard' | 'contextual' | 'gamified',
        canShowPrompt: canShow,
        userHistory: history
      }));

      if (debugMode) {
        console.log('🎭 App Rating Hook initialized:', {
          appVariant,
          promptVariant,
          canShowPrompt: canShow,
          userHistory: history
        });
      }
    } catch (error) {
      console.error('Failed to initialize app rating service:', error);
    }
  }, [appVariant, debugMode]);

  const handleSessionStart = useCallback(async () => {
    try {
      sessionStartTime.current = new Date();
      await AppReviewService.incrementSessionCount();
      
      // Update session metrics
      await updateSessionMetrics();
      
      if (debugMode) {
        console.log('📱 New session started');
      }
    } catch (error) {
      console.error('Error handling session start:', error);
    }
  }, [debugMode]);

  const handleSessionEnd = useCallback(async () => {
    try {
      const sessionDuration = new Date().getTime() - sessionStartTime.current.getTime();
      
      AnalyticsService.track('session_ended', {
        duration_ms: sessionDuration,
        duration_minutes: Math.floor(sessionDuration / (1000 * 60))
      });

      if (debugMode) {
        console.log('📱 Session ended, duration:', sessionDuration, 'ms');
      }
    } catch (error) {
      console.error('Error handling session end:', error);
    }
  }, [debugMode]);

  const updateSessionMetrics = useCallback(async () => {
    try {
      // This would typically come from AppReviewService methods
      // For now, we'll simulate the data
      setState(prev => ({
        ...prev,
        sessionMetrics: {
          ...prev.sessionMetrics,
          sessionCount: prev.sessionMetrics.sessionCount + 1
        }
      }));
    } catch (error) {
      console.error('Error updating session metrics:', error);
    }
  }, []);

  const showPrompt = useCallback(async (trigger?: ReviewPromptTrigger) => {
    try {
      if (!enableAutoPrompt && !trigger) {
        if (debugMode) {
          console.log('⏸️ Auto-prompt disabled, ignoring request');
        }
        return;
      }

      const canShow = await AppReviewService.isEligibleForReview();
      if (!canShow) {
        if (debugMode) {
          console.log('🚫 User not eligible for rating prompt');
        }
        return;
      }

      const defaultTrigger: ReviewPromptTrigger = {
        eventType: 'manual',
        timestamp: new Date(),
        context: trigger?.context || {}
      };

      const finalTrigger = trigger || defaultTrigger;
      
      // Request review through service
      const success = await AppReviewService.requestReview(finalTrigger);
      
      if (success) {
        setState(prev => ({
          ...prev,
          isPromptVisible: true,
          promptContext: {
            trigger: finalTrigger.eventType,
            achievement: finalTrigger.context?.achievement,
            feature: finalTrigger.context?.feature
          }
        }));

        if (debugMode) {
          console.log('✨ Rating prompt shown:', finalTrigger);
        }
      } else {
        if (debugMode) {
          console.log('❌ Rating prompt request failed');
        }
      }
    } catch (error) {
      console.error('Error showing rating prompt:', error);
    }
  }, [enableAutoPrompt, debugMode]);

  const hidePrompt = useCallback(() => {
    setState(prev => ({
      ...prev,
      isPromptVisible: false,
      promptContext: undefined
    }));

    if (debugMode) {
      console.log('👻 Rating prompt hidden');
    }
  }, [debugMode]);

  const trackAction = useCallback(async (actionType: string, context?: Record<string, any>) => {
    if (!enableActionTracking) return;

    try {
      await AppReviewService.trackUserAction(actionType, context);
      
      setState(prev => ({
        ...prev,
        sessionMetrics: {
          ...prev.sessionMetrics,
          actionCount: prev.sessionMetrics.actionCount + 1
        }
      }));

      if (debugMode) {
        console.log('🎬 Action tracked:', actionType, context);
      }
    } catch (error) {
      console.error('Error tracking action:', error);
    }
  }, [enableActionTracking, debugMode]);

  const trackMilestone = useCallback(async (milestoneType: string, details?: Record<string, any>) => {
    if (!enableActionTracking) return;

    try {
      await AppReviewService.trackMilestone(milestoneType, details);

      if (debugMode) {
        console.log('🏆 Milestone tracked:', milestoneType, details);
      }
    } catch (error) {
      console.error('Error tracking milestone:', error);
    }
  }, [enableActionTracking, debugMode]);

  const trackFeatureSuccess = useCallback(async (featureName: string, successMetric?: Record<string, any>) => {
    if (!enableActionTracking) return;

    try {
      await AppReviewService.trackFeatureSuccess(featureName, successMetric);

      if (debugMode) {
        console.log('🚀 Feature success tracked:', featureName, successMetric);
      }
    } catch (error) {
      console.error('Error tracking feature success:', error);
    }
  }, [enableActionTracking, debugMode]);

  const forcePrompt = useCallback(async () => {
    const trigger: ReviewPromptTrigger = {
      eventType: 'manual',
      timestamp: new Date(),
      context: { forced: true }
    };
    
    await showPrompt(trigger);
    
    if (debugMode) {
      console.log('🔧 Force prompt triggered');
    }
  }, [showPrompt, debugMode]);

  const resetRatingState = useCallback(async () => {
    try {
      // This would reset the user's rating history
      // Implementation depends on AppReviewService having a reset method
      
      setState(prev => ({
        ...prev,
        isPromptVisible: false,
        promptContext: undefined,
        canShowPrompt: true,
        userHistory: null,
        sessionMetrics: {
          sessionCount: 0,
          actionCount: 0,
          daysSinceInstall: 0
        }
      }));

      if (debugMode) {
        console.log('🔄 Rating state reset');
      }
    } catch (error) {
      console.error('Error resetting rating state:', error);
    }
  }, [debugMode]);

  const checkEligibility = useCallback(async (): Promise<boolean> => {
    try {
      const eligible = await AppReviewService.isEligibleForReview();
      
      setState(prev => ({
        ...prev,
        canShowPrompt: eligible
      }));

      if (debugMode) {
        console.log('✅ Eligibility check:', eligible);
      }

      return eligible;
    } catch (error) {
      console.error('Error checking eligibility:', error);
      return false;
    }
  }, [debugMode]);

  // Convenience methods for common actions
  const trackCommonActions = {
    goalCompleted: (goalType: string, details?: Record<string, any>) =>
      trackAction('goal_completed', { goalType, ...details }),
    
    streakMaintained: (streakCount: number, streakType: string) =>
      trackAction('streak_maintained', { streakCount, streakType }),
    
    featureMastered: (featureName: string, level?: string) =>
      trackAction('feature_mastered', { featureName, level }),
    
    dataExported: (exportType: string, itemCount?: number) =>
      trackAction('data_exported', { exportType, itemCount }),
    
    contentShared: (contentType: string, platform?: string) =>
      trackAction('content_shared', { contentType, platform }),
    
    premiumFeatureUsed: (featureName: string, usage?: Record<string, any>) =>
      trackAction('premium_feature_used', { featureName, ...usage }),
  };

  const actions: AppRatingActions = {
    showPrompt,
    hidePrompt,
    trackAction,
    trackMilestone,
    trackFeatureSuccess,
    forcePrompt,
    resetRatingState,
    checkEligibility,
    
    // Add convenience methods
    ...trackCommonActions
  };

  return [state, actions];
};

// Helper hook for simpler usage when you just need basic tracking
export const useSimpleRating = (appVariant?: string) => {
  const [state, actions] = useAppRating({ appVariant });
  
  return {
    isVisible: state.isPromptVisible,
    variant: state.promptVariant,
    context: state.promptContext,
    show: actions.showPrompt,
    hide: actions.hidePrompt,
    track: actions.trackAction
  };
};

// Hook for milestone tracking with common milestones
export const useMilestoneRating = (appVariant?: string) => {
  const [, actions] = useAppRating({ appVariant });
  
  const trackCommonMilestones = {
    firstGoalCompleted: () => actions.trackMilestone('first_goal_completed'),
    weekStreak: () => actions.trackMilestone('7_day_streak'),
    monthStreak: () => actions.trackMilestone('30_day_streak'),
    hundredItems: () => actions.trackMilestone('100_items_created'),
    powerUser: () => actions.trackMilestone('power_user_unlocked'),
    yearAnniversary: () => actions.trackMilestone('1_year_anniversary')
  };
  
  return trackCommonMilestones;
};

export default useAppRating;