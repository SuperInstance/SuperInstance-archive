import { NextRequest } from 'next/server';

export interface TourStep {
  id: string;
  title: string;
  content: string;
  target: string;
  placement: 'top' | 'bottom' | 'left' | 'right' | 'center';
  order: number;
  type: 'tooltip' | 'modal' | 'highlight' | 'spotlight';
  optional: boolean;
  actionRequired?: {
    type: 'click' | 'input' | 'scroll' | 'wait';
    element?: string;
    value?: string;
    timeout?: number;
  };
  conditions?: {
    showIf?: string;
    hideIf?: string;
    requiredFeature?: string;
  };
}

export interface ProductTour {
  id: string;
  name: string;
  description: string;
  appVariant: 'PersonalLog' | 'BusinessLog' | 'FamilyLog' | 'FitnessLog' | 'TravelLog' | 'EducationLog';
  category: 'onboarding' | 'feature-discovery' | 'advanced' | 'troubleshooting';
  targetAudience: string[];
  triggers: {
    manual: boolean;
    onFirstVisit: boolean;
    onFeatureAccess: boolean;
    onUserSegment?: string;
    afterDays?: number;
  };
  steps: TourStep[];
  completionRate: number;
  averageTimeToComplete: number;
  userRating: number;
  isActive: boolean;
  version: string;
}

export interface TourSession {
  id: string;
  userId: string;
  tourId: string;
  currentStepIndex: number;
  completedSteps: string[];
  startedAt: Date;
  completedAt?: Date;
  abandonedAt?: Date;
  skippedSteps: string[];
  progress: number;
  userFeedback?: {
    rating: number;
    helpful: boolean;
    comments?: string;
  };
}

export interface TourAnalytics {
  totalSessions: number;
  completionRate: number;
  averageRating: number;
  stepAnalytics: {
    stepId: string;
    title: string;
    viewCount: number;
    completionRate: number;
    averageTimeSpent: number;
    skipRate: number;
  }[];
  userSegmentPerformance: {
    segment: string;
    completionRate: number;
    averageRating: number;
  }[];
}

export class ProductTourSystem {
  private tours: Map<string, ProductTour> = new Map();
  private sessions: Map<string, TourSession> = new Map();

  constructor() {
    this.initializeDefaultTours();
  }

  private initializeDefaultTours(): void {
    const personalLogBasicTour: ProductTour = {
      id: 'personal-log-basics',
      name: 'PersonalLog Basics',
      description: 'Learn the essential features of PersonalLog',
      appVariant: 'PersonalLog',
      category: 'onboarding',
      targetAudience: ['new-users', 'beginners'],
      triggers: {
        manual: true,
        onFirstVisit: true,
        onFeatureAccess: false
      },
      completionRate: 0,
      averageTimeToComplete: 0,
      userRating: 0,
      isActive: true,
      version: '1.0',
      steps: [
        {
          id: 'welcome',
          title: 'Welcome to PersonalLog!',
          content: 'Let\'s take a quick tour to help you get started with logging your thoughts and experiences.',
          target: 'body',
          placement: 'center',
          order: 1,
          type: 'modal',
          optional: false
        },
        {
          id: 'new-entry-button',
          title: 'Create Your First Entry',
          content: 'Click this button to start writing your first log entry. This is where your journey begins!',
          target: '[data-tour="new-entry-button"]',
          placement: 'bottom',
          order: 2,
          type: 'tooltip',
          optional: false,
          actionRequired: {
            type: 'click',
            element: '[data-tour="new-entry-button"]'
          }
        },
        {
          id: 'editor',
          title: 'Rich Text Editor',
          content: 'Use this editor to write your thoughts. You can format text, add images, and create lists.',
          target: '[data-tour="editor"]',
          placement: 'top',
          order: 3,
          type: 'spotlight',
          optional: false
        },
        {
          id: 'categories',
          title: 'Organize with Categories',
          content: 'Tag your entries with categories to keep them organized and easy to find later.',
          target: '[data-tour="categories"]',
          placement: 'right',
          order: 4,
          type: 'tooltip',
          optional: true
        },
        {
          id: 'save-entry',
          title: 'Save Your Entry',
          content: 'Don\'t forget to save your entry when you\'re done writing!',
          target: '[data-tour="save-button"]',
          placement: 'left',
          order: 5,
          type: 'highlight',
          optional: false
        }
      ]
    };

    const businessLogAdvancedTour: ProductTour = {
      id: 'business-log-advanced',
      name: 'Advanced BusinessLog Features',
      description: 'Discover powerful features for business documentation',
      appVariant: 'BusinessLog',
      category: 'feature-discovery',
      targetAudience: ['experienced-users', 'business-professionals'],
      triggers: {
        manual: true,
        onFirstVisit: false,
        onFeatureAccess: true,
        afterDays: 7
      },
      completionRate: 0,
      averageTimeToComplete: 0,
      userRating: 0,
      isActive: true,
      version: '1.0',
      steps: [
        {
          id: 'collaboration',
          title: 'Team Collaboration',
          content: 'Share logs with your team members and collaborate in real-time.',
          target: '[data-tour="collaboration-panel"]',
          placement: 'right',
          order: 1,
          type: 'tooltip',
          optional: false
        },
        {
          id: 'templates',
          title: 'Business Templates',
          content: 'Use pre-built templates for meeting notes, project updates, and reports.',
          target: '[data-tour="templates"]',
          placement: 'bottom',
          order: 2,
          type: 'spotlight',
          optional: false
        },
        {
          id: 'analytics',
          title: 'Business Analytics',
          content: 'Track your team\'s productivity and logging patterns with detailed analytics.',
          target: '[data-tour="analytics"]',
          placement: 'top',
          order: 3,
          type: 'tooltip',
          optional: true
        },
        {
          id: 'integrations',
          title: 'Tool Integrations',
          content: 'Connect with Slack, Microsoft Teams, and other business tools.',
          target: '[data-tour="integrations"]',
          placement: 'left',
          order: 4,
          type: 'highlight',
          optional: true
        }
      ]
    };

    const fitnessLogWorkoutTour: ProductTour = {
      id: 'fitness-log-workouts',
      name: 'Workout Tracking Guide',
      description: 'Learn how to track your workouts effectively',
      appVariant: 'FitnessLog',
      category: 'onboarding',
      targetAudience: ['fitness-beginners', 'new-users'],
      triggers: {
        manual: true,
        onFirstVisit: true,
        onFeatureAccess: false
      },
      completionRate: 0,
      averageTimeToComplete: 0,
      userRating: 0,
      isActive: true,
      version: '1.0',
      steps: [
        {
          id: 'workout-creation',
          title: 'Start a New Workout',
          content: 'Begin tracking your workout by clicking the "New Workout" button.',
          target: '[data-tour="new-workout"]',
          placement: 'bottom',
          order: 1,
          type: 'tooltip',
          optional: false,
          actionRequired: {
            type: 'click',
            element: '[data-tour="new-workout"]'
          }
        },
        {
          id: 'exercise-selection',
          title: 'Add Exercises',
          content: 'Choose from our extensive exercise database or create custom exercises.',
          target: '[data-tour="exercise-selector"]',
          placement: 'right',
          order: 2,
          type: 'spotlight',
          optional: false
        },
        {
          id: 'sets-tracking',
          title: 'Track Sets and Reps',
          content: 'Log each set with weight, reps, and rest time for detailed tracking.',
          target: '[data-tour="sets-tracker"]',
          placement: 'top',
          order: 3,
          type: 'tooltip',
          optional: false
        },
        {
          id: 'progress-photos',
          title: 'Add Progress Photos',
          content: 'Document your transformation with progress photos.',
          target: '[data-tour="photo-upload"]',
          placement: 'left',
          order: 4,
          type: 'highlight',
          optional: true
        }
      ]
    };

    this.tours.set(personalLogBasicTour.id, personalLogBasicTour);
    this.tours.set(businessLogAdvancedTour.id, businessLogAdvancedTour);
    this.tours.set(fitnessLogWorkoutTour.id, fitnessLogWorkoutTour);
  }

  async startTour(userId: string, tourId: string): Promise<TourSession | null> {
    const tour = this.tours.get(tourId);
    if (!tour || !tour.isActive) return null;

    const session: TourSession = {
      id: `tour_${userId}_${tourId}_${Date.now()}`,
      userId,
      tourId,
      currentStepIndex: 0,
      completedSteps: [],
      startedAt: new Date(),
      skippedSteps: [],
      progress: 0
    };

    this.sessions.set(session.id, session);
    return session;
  }

  async nextStep(sessionId: string): Promise<{ success: boolean; step?: TourStep; completed?: boolean }> {
    const session = this.sessions.get(sessionId);
    if (!session) return { success: false };

    const tour = this.tours.get(session.tourId);
    if (!tour) return { success: false };

    if (session.currentStepIndex < tour.steps.length) {
      const currentStep = tour.steps[session.currentStepIndex];
      session.completedSteps.push(currentStep.id);
      session.currentStepIndex++;
      session.progress = (session.currentStepIndex / tour.steps.length) * 100;

      if (session.currentStepIndex >= tour.steps.length) {
        session.completedAt = new Date();
        return { success: true, completed: true };
      }

      const nextStep = tour.steps[session.currentStepIndex];
      if (this.shouldShowStep(nextStep, session)) {
        return { success: true, step: nextStep };
      } else {
        return this.nextStep(sessionId);
      }
    }

    return { success: false };
  }

  async skipStep(sessionId: string): Promise<{ success: boolean; nextStep?: TourStep }> {
    const session = this.sessions.get(sessionId);
    if (!session) return { success: false };

    const tour = this.tours.get(session.tourId);
    if (!tour) return { success: false };

    const currentStep = tour.steps[session.currentStepIndex];
    if (currentStep && currentStep.optional) {
      session.skippedSteps.push(currentStep.id);
      const result = await this.nextStep(sessionId);
      return { success: result.success, nextStep: result.step };
    }

    return { success: false };
  }

  async completeTour(sessionId: string, feedback?: { rating: number; helpful: boolean; comments?: string }): Promise<boolean> {
    const session = this.sessions.get(sessionId);
    if (!session) return false;

    session.completedAt = new Date();
    session.progress = 100;
    
    if (feedback) {
      session.userFeedback = feedback;
    }

    return true;
  }

  async abandonTour(sessionId: string): Promise<boolean> {
    const session = this.sessions.get(sessionId);
    if (!session) return false;

    session.abandonedAt = new Date();
    return true;
  }

  async getTourProgress(sessionId: string): Promise<any> {
    const session = this.sessions.get(sessionId);
    if (!session) return null;

    const tour = this.tours.get(session.tourId);
    if (!tour) return null;

    const currentStep = tour.steps[session.currentStepIndex];
    const totalSteps = tour.steps.length;
    const completedSteps = session.completedSteps.length;

    return {
      session,
      tour: {
        id: tour.id,
        name: tour.name,
        description: tour.description,
        category: tour.category
      },
      currentStep,
      progress: {
        percentage: Math.round(session.progress),
        completed: completedSteps,
        total: totalSteps,
        remaining: totalSteps - completedSteps
      },
      timeElapsed: session.startedAt ? Date.now() - session.startedAt.getTime() : 0
    };
  }

  async getAvailableTours(userId: string, appVariant: string, userSegment?: string): Promise<ProductTour[]> {
    return Array.from(this.tours.values())
      .filter(tour => {
        if (!tour.isActive) return false;
        if (tour.appVariant !== appVariant) return false;
        if (userSegment && tour.targetAudience.length > 0 && !tour.targetAudience.includes(userSegment)) return false;
        return true;
      })
      .sort((a, b) => {
        if (a.category === 'onboarding' && b.category !== 'onboarding') return -1;
        if (b.category === 'onboarding' && a.category !== 'onboarding') return 1;
        return a.name.localeCompare(b.name);
      });
  }

  async getTourAnalytics(tourId?: string): Promise<TourAnalytics> {
    let sessions = Array.from(this.sessions.values());
    
    if (tourId) {
      sessions = sessions.filter(s => s.tourId === tourId);
    }

    const totalSessions = sessions.length;
    const completedSessions = sessions.filter(s => s.completedAt).length;
    const completionRate = totalSessions > 0 ? (completedSessions / totalSessions) * 100 : 0;

    const ratings = sessions
      .filter(s => s.userFeedback?.rating)
      .map(s => s.userFeedback!.rating);
    const averageRating = ratings.length > 0 ? ratings.reduce((sum, r) => sum + r, 0) / ratings.length : 0;

    const stepAnalytics = this.calculateStepAnalytics(sessions);
    const userSegmentPerformance = this.calculateSegmentPerformance(sessions);

    return {
      totalSessions,
      completionRate: Math.round(completionRate * 100) / 100,
      averageRating: Math.round(averageRating * 100) / 100,
      stepAnalytics,
      userSegmentPerformance
    };
  }

  private calculateStepAnalytics(sessions: TourSession[]): TourAnalytics['stepAnalytics'] {
    const stepStats = new Map<string, {
      title: string;
      views: number;
      completions: number;
      skips: number;
      totalTime: number;
    }>();

    sessions.forEach(session => {
      const tour = this.tours.get(session.tourId);
      if (!tour) return;

      tour.steps.forEach((step, index) => {
        if (!stepStats.has(step.id)) {
          stepStats.set(step.id, {
            title: step.title,
            views: 0,
            completions: 0,
            skips: 0,
            totalTime: 0
          });
        }

        const stats = stepStats.get(step.id)!;
        
        if (session.currentStepIndex > index) {
          stats.views++;
          if (session.completedSteps.includes(step.id)) {
            stats.completions++;
          }
          if (session.skippedSteps.includes(step.id)) {
            stats.skips++;
          }
        }
      });
    });

    return Array.from(stepStats.entries()).map(([stepId, stats]) => ({
      stepId,
      title: stats.title,
      viewCount: stats.views,
      completionRate: stats.views > 0 ? Math.round((stats.completions / stats.views) * 100 * 100) / 100 : 0,
      averageTimeSpent: Math.round(stats.totalTime / Math.max(stats.views, 1)),
      skipRate: stats.views > 0 ? Math.round((stats.skips / stats.views) * 100 * 100) / 100 : 0
    }));
  }

  private calculateSegmentPerformance(sessions: TourSession[]): TourAnalytics['userSegmentPerformance'] {
    const segmentStats = new Map<string, { completed: number; total: number; ratings: number[] }>();

    sessions.forEach(session => {
      const segment = 'default';
      
      if (!segmentStats.has(segment)) {
        segmentStats.set(segment, { completed: 0, total: 0, ratings: [] });
      }

      const stats = segmentStats.get(segment)!;
      stats.total++;
      
      if (session.completedAt) {
        stats.completed++;
      }
      
      if (session.userFeedback?.rating) {
        stats.ratings.push(session.userFeedback.rating);
      }
    });

    return Array.from(segmentStats.entries()).map(([segment, stats]) => ({
      segment,
      completionRate: stats.total > 0 ? Math.round((stats.completed / stats.total) * 100 * 100) / 100 : 0,
      averageRating: stats.ratings.length > 0 ? Math.round((stats.ratings.reduce((sum, r) => sum + r, 0) / stats.ratings.length) * 100) / 100 : 0
    }));
  }

  private shouldShowStep(step: TourStep, session: TourSession): boolean {
    if (step.conditions?.hideIf) {
      return false;
    }
    
    if (step.conditions?.showIf) {
      return true;
    }

    return true;
  }

  getTour(tourId: string): ProductTour | undefined {
    return this.tours.get(tourId);
  }

  getAllTours(): ProductTour[] {
    return Array.from(this.tours.values());
  }

  getActiveTours(): ProductTour[] {
    return Array.from(this.tours.values()).filter(tour => tour.isActive);
  }

  getUserSessions(userId: string): TourSession[] {
    return Array.from(this.sessions.values()).filter(session => session.userId === userId);
  }

  async updateTour(tourId: string, updates: Partial<ProductTour>): Promise<boolean> {
    const tour = this.tours.get(tourId);
    if (!tour) return false;

    Object.assign(tour, updates);
    return true;
  }

  async createCustomTour(tourData: Omit<ProductTour, 'id' | 'completionRate' | 'averageTimeToComplete' | 'userRating'>): Promise<ProductTour> {
    const tour: ProductTour = {
      ...tourData,
      id: `custom_tour_${Date.now()}`,
      completionRate: 0,
      averageTimeToComplete: 0,
      userRating: 0
    };

    this.tours.set(tour.id, tour);
    return tour;
  }
}

export const productTours = new ProductTourSystem();