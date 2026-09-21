import { NextRequest } from 'next/server';

export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  component: string;
  order: number;
  required: boolean;
  completed: boolean;
  data?: any;
  validationRules?: string[];
}

export interface OnboardingFlow {
  id: string;
  name: string;
  description: string;
  targetAudience: string;
  appVariant: 'PersonalLog' | 'BusinessLog' | 'FamilyLog' | 'FitnessLog' | 'TravelLog' | 'EducationLog';
  steps: OnboardingStep[];
  completionRate: number;
  averageTimeToComplete: number;
  isActive: boolean;
}

export interface OnboardingSession {
  id: string;
  userId: string;
  flowId: string;
  currentStepId: string;
  completedSteps: string[];
  startedAt: Date;
  completedAt?: Date;
  abandonedAt?: Date;
  progress: number;
  userData: Record<string, any>;
}

export interface OnboardingAnalytics {
  totalSessions: number;
  completionRate: number;
  averageTimeToComplete: number;
  dropOffPoints: { stepId: string; stepTitle: string; dropOffRate: number }[];
  conversionByStep: { stepId: string; conversionRate: number }[];
}

export class OnboardingFlowSystem {
  private flows: Map<string, OnboardingFlow> = new Map();
  private sessions: Map<string, OnboardingSession> = new Map();

  constructor() {
    this.initializeDefaultFlows();
  }

  private initializeDefaultFlows(): void {
    const personalLogFlow: OnboardingFlow = {
      id: 'personal-log-flow',
      name: 'Personal Logging Setup',
      description: 'Get started with PersonalLog',
      targetAudience: 'Individual users',
      appVariant: 'PersonalLog',
      completionRate: 0,
      averageTimeToComplete: 0,
      isActive: true,
      steps: [
        {
          id: 'welcome',
          title: 'Welcome to PersonalLog',
          description: 'Learn what PersonalLog can do for you',
          component: 'WelcomeStep',
          order: 1,
          required: true,
          completed: false
        },
        {
          id: 'profile-setup',
          title: 'Set Up Your Profile',
          description: 'Tell us about yourself',
          component: 'ProfileSetupStep',
          order: 2,
          required: true,
          completed: false,
          validationRules: ['name_required', 'timezone_required']
        },
        {
          id: 'first-entry',
          title: 'Create Your First Entry',
          description: 'Start logging your thoughts and experiences',
          component: 'FirstEntryStep',
          order: 3,
          required: true,
          completed: false
        },
        {
          id: 'categories-setup',
          title: 'Organize with Categories',
          description: 'Set up categories for your entries',
          component: 'CategoriesStep',
          order: 4,
          required: false,
          completed: false
        },
        {
          id: 'notifications',
          title: 'Enable Notifications',
          description: 'Get reminders to log regularly',
          component: 'NotificationsStep',
          order: 5,
          required: false,
          completed: false
        }
      ]
    };

    const businessLogFlow: OnboardingFlow = {
      id: 'business-log-flow',
      name: 'Business Logging Setup',
      description: 'Get started with BusinessLog',
      targetAudience: 'Business professionals',
      appVariant: 'BusinessLog',
      completionRate: 0,
      averageTimeToComplete: 0,
      isActive: true,
      steps: [
        {
          id: 'welcome',
          title: 'Welcome to BusinessLog',
          description: 'Streamline your business documentation',
          component: 'WelcomeStep',
          order: 1,
          required: true,
          completed: false
        },
        {
          id: 'company-setup',
          title: 'Company Information',
          description: 'Set up your company profile',
          component: 'CompanySetupStep',
          order: 2,
          required: true,
          completed: false,
          validationRules: ['company_name_required', 'industry_required']
        },
        {
          id: 'team-setup',
          title: 'Invite Team Members',
          description: 'Add your team to collaborate',
          component: 'TeamSetupStep',
          order: 3,
          required: false,
          completed: false
        },
        {
          id: 'first-log',
          title: 'Create First Business Log',
          description: 'Document your first business activity',
          component: 'FirstLogStep',
          order: 4,
          required: true,
          completed: false
        },
        {
          id: 'integrations',
          title: 'Connect Tools',
          description: 'Integrate with your existing tools',
          component: 'IntegrationsStep',
          order: 5,
          required: false,
          completed: false
        }
      ]
    };

    const fitnessLogFlow: OnboardingFlow = {
      id: 'fitness-log-flow',
      name: 'Fitness Tracking Setup',
      description: 'Get started with FitnessLog',
      targetAudience: 'Fitness enthusiasts',
      appVariant: 'FitnessLog',
      completionRate: 0,
      averageTimeToComplete: 0,
      isActive: true,
      steps: [
        {
          id: 'welcome',
          title: 'Welcome to FitnessLog',
          description: 'Track your fitness journey',
          component: 'WelcomeStep',
          order: 1,
          required: true,
          completed: false
        },
        {
          id: 'fitness-goals',
          title: 'Set Your Goals',
          description: 'Define what you want to achieve',
          component: 'GoalsSetupStep',
          order: 2,
          required: true,
          completed: false,
          validationRules: ['goal_type_required', 'target_date_required']
        },
        {
          id: 'body-metrics',
          title: 'Initial Measurements',
          description: 'Record your starting metrics',
          component: 'MetricsStep',
          order: 3,
          required: true,
          completed: false
        },
        {
          id: 'first-workout',
          title: 'Log Your First Workout',
          description: 'Start tracking your exercises',
          component: 'FirstWorkoutStep',
          order: 4,
          required: true,
          completed: false
        },
        {
          id: 'wearable-sync',
          title: 'Connect Devices',
          description: 'Sync with fitness trackers',
          component: 'WearableSyncStep',
          order: 5,
          required: false,
          completed: false
        }
      ]
    };

    this.flows.set(personalLogFlow.id, personalLogFlow);
    this.flows.set(businessLogFlow.id, businessLogFlow);
    this.flows.set(fitnessLogFlow.id, fitnessLogFlow);
  }

  async startOnboardingFlow(userId: string, appVariant: string): Promise<OnboardingSession | null> {
    const flow = this.getFlowByAppVariant(appVariant as any);
    if (!flow || !flow.isActive) return null;

    const session: OnboardingSession = {
      id: `session_${userId}_${Date.now()}`,
      userId,
      flowId: flow.id,
      currentStepId: flow.steps[0].id,
      completedSteps: [],
      startedAt: new Date(),
      progress: 0,
      userData: {}
    };

    this.sessions.set(session.id, session);
    return session;
  }

  async completeStep(sessionId: string, stepId: string, stepData?: any): Promise<{ success: boolean; nextStep?: OnboardingStep }> {
    const session = this.sessions.get(sessionId);
    if (!session) return { success: false };

    const flow = this.flows.get(session.flowId);
    if (!flow) return { success: false };

    const step = flow.steps.find(s => s.id === stepId);
    if (!step) return { success: false };

    if (stepData && !this.validateStepData(step, stepData)) {
      return { success: false };
    }

    session.completedSteps.push(stepId);
    if (stepData) {
      session.userData[stepId] = stepData;
    }

    const nextStepIndex = flow.steps.findIndex(s => s.id === stepId) + 1;
    if (nextStepIndex < flow.steps.length) {
      session.currentStepId = flow.steps[nextStepIndex].id;
      session.progress = (session.completedSteps.length / flow.steps.length) * 100;
      return { success: true, nextStep: flow.steps[nextStepIndex] };
    } else {
      session.completedAt = new Date();
      session.progress = 100;
      return { success: true };
    }
  }

  async skipStep(sessionId: string, stepId: string): Promise<{ success: boolean; nextStep?: OnboardingStep }> {
    const session = this.sessions.get(sessionId);
    if (!session) return { success: false };

    const flow = this.flows.get(session.flowId);
    if (!flow) return { success: false };

    const step = flow.steps.find(s => s.id === stepId);
    if (!step || step.required) return { success: false };

    return this.completeStep(sessionId, stepId);
  }

  async abandonSession(sessionId: string): Promise<boolean> {
    const session = this.sessions.get(sessionId);
    if (!session) return false;

    session.abandonedAt = new Date();
    return true;
  }

  async getSessionProgress(sessionId: string): Promise<any> {
    const session = this.sessions.get(sessionId);
    if (!session) return null;

    const flow = this.flows.get(session.flowId);
    if (!flow) return null;

    const currentStep = flow.steps.find(s => s.id === session.currentStepId);
    const totalSteps = flow.steps.length;
    const completedSteps = session.completedSteps.length;

    return {
      session,
      flow: {
        id: flow.id,
        name: flow.name,
        description: flow.description
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

  async getOnboardingAnalytics(flowId?: string): Promise<OnboardingAnalytics> {
    let sessions = Array.from(this.sessions.values());
    
    if (flowId) {
      sessions = sessions.filter(s => s.flowId === flowId);
    }

    const totalSessions = sessions.length;
    const completedSessions = sessions.filter(s => s.completedAt).length;
    const completionRate = totalSessions > 0 ? (completedSessions / totalSessions) * 100 : 0;

    const completedSessionTimes = sessions
      .filter(s => s.completedAt && s.startedAt)
      .map(s => s.completedAt!.getTime() - s.startedAt.getTime());
    
    const averageTimeToComplete = completedSessionTimes.length > 0
      ? completedSessionTimes.reduce((sum, time) => sum + time, 0) / completedSessionTimes.length
      : 0;

    const dropOffPoints = this.calculateDropOffPoints(sessions);
    const conversionByStep = this.calculateConversionRates(sessions);

    return {
      totalSessions,
      completionRate: Math.round(completionRate * 100) / 100,
      averageTimeToComplete: Math.round(averageTimeToComplete / 1000 / 60),
      dropOffPoints,
      conversionByStep
    };
  }

  private calculateDropOffPoints(sessions: OnboardingSession[]): { stepId: string; stepTitle: string; dropOffRate: number }[] {
    const stepDropOffs = new Map<string, { abandoned: number; reached: number; title: string }>();
    
    sessions.forEach(session => {
      const flow = this.flows.get(session.flowId);
      if (!flow) return;

      flow.steps.forEach(step => {
        if (!stepDropOffs.has(step.id)) {
          stepDropOffs.set(step.id, { abandoned: 0, reached: 0, title: step.title });
        }
        
        const stepIndex = flow.steps.findIndex(s => s.id === step.id);
        if (session.completedSteps.length > stepIndex) {
          stepDropOffs.get(step.id)!.reached++;
        } else if (session.abandonedAt && !session.completedAt) {
          stepDropOffs.get(step.id)!.abandoned++;
        }
      });
    });

    return Array.from(stepDropOffs.entries())
      .map(([stepId, data]) => ({
        stepId,
        stepTitle: data.title,
        dropOffRate: data.reached > 0 ? Math.round((data.abandoned / data.reached) * 100 * 100) / 100 : 0
      }))
      .sort((a, b) => b.dropOffRate - a.dropOffRate);
  }

  private calculateConversionRates(sessions: OnboardingSession[]): { stepId: string; conversionRate: number }[] {
    const stepConversions = new Map<string, { completed: number; started: number }>();
    
    sessions.forEach(session => {
      const flow = this.flows.get(session.flowId);
      if (!flow) return;

      flow.steps.forEach((step, index) => {
        if (!stepConversions.has(step.id)) {
          stepConversions.set(step.id, { completed: 0, started: 0 });
        }
        
        if (session.completedSteps.length > index) {
          stepConversions.get(step.id)!.started++;
          stepConversions.get(step.id)!.completed++;
        } else if (session.completedSteps.length === index) {
          stepConversions.get(step.id)!.started++;
        }
      });
    });

    return Array.from(stepConversions.entries())
      .map(([stepId, data]) => ({
        stepId,
        conversionRate: data.started > 0 ? Math.round((data.completed / data.started) * 100 * 100) / 100 : 0
      }));
  }

  private validateStepData(step: OnboardingStep, data: any): boolean {
    if (!step.validationRules) return true;

    for (const rule of step.validationRules) {
      switch (rule) {
        case 'name_required':
          if (!data.name || data.name.trim() === '') return false;
          break;
        case 'timezone_required':
          if (!data.timezone) return false;
          break;
        case 'company_name_required':
          if (!data.companyName || data.companyName.trim() === '') return false;
          break;
        case 'industry_required':
          if (!data.industry) return false;
          break;
        case 'goal_type_required':
          if (!data.goalType) return false;
          break;
        case 'target_date_required':
          if (!data.targetDate) return false;
          break;
      }
    }

    return true;
  }

  private getFlowByAppVariant(variant: OnboardingFlow['appVariant']): OnboardingFlow | undefined {
    return Array.from(this.flows.values()).find(flow => flow.appVariant === variant);
  }

  getFlow(flowId: string): OnboardingFlow | undefined {
    return this.flows.get(flowId);
  }

  getAllFlows(): OnboardingFlow[] {
    return Array.from(this.flows.values());
  }

  getActiveFlows(): OnboardingFlow[] {
    return Array.from(this.flows.values()).filter(flow => flow.isActive);
  }

  getUserSessions(userId: string): OnboardingSession[] {
    return Array.from(this.sessions.values()).filter(session => session.userId === userId);
  }

  async updateFlow(flowId: string, updates: Partial<OnboardingFlow>): Promise<boolean> {
    const flow = this.flows.get(flowId);
    if (!flow) return false;

    Object.assign(flow, updates);
    return true;
  }

  async createCustomFlow(flowData: Omit<OnboardingFlow, 'id' | 'completionRate' | 'averageTimeToComplete'>): Promise<OnboardingFlow> {
    const flow: OnboardingFlow = {
      ...flowData,
      id: `custom_flow_${Date.now()}`,
      completionRate: 0,
      averageTimeToComplete: 0
    };

    this.flows.set(flow.id, flow);
    return flow;
  }
}

export const onboardingFlows = new OnboardingFlowSystem();