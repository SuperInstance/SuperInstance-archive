import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Device from 'expo-device';
import * as Application from 'expo-application';
import { Platform } from 'react-native';
import { AnalyticsService } from './analytics';
import { CrashReportingService } from './crash-reporting';

export interface ABTestConfig {
  testId: string;
  testName: string;
  description: string;
  status: 'draft' | 'active' | 'paused' | 'completed';
  
  // Targeting
  targetPercentage: number; // 0-100, percentage of users to include
  targetPlatforms?: ('ios' | 'android')[];
  targetVersions?: string[];
  targetCountries?: string[];
  targetUserSegments?: string[];
  
  // Variants
  controlVariant: ABTestVariant;
  testVariants: ABTestVariant[];
  
  // Test duration and timing
  startDate: Date;
  endDate?: Date;
  duration?: number; // days
  
  // Success metrics
  primaryMetric: string;
  secondaryMetrics?: string[];
  conversionGoal?: string;
  
  // Statistical settings
  minimumSampleSize: number;
  confidenceLevel: number; // 90, 95, or 99
  minimumDetectableEffect: number; // percentage
  
  // Advanced settings
  stickyAssignment: boolean; // Once assigned, user stays in same variant
  enabledForNewUsersOnly?: boolean;
  excludeExistingTests?: string[]; // Test IDs to exclude from
  
  // Custom properties
  customProperties?: Record<string, any>;
}

export interface ABTestVariant {
  variantId: string;
  variantName: string;
  description?: string;
  weight: number; // 0-100, relative weight for allocation
  configuration: Record<string, any>;
  
  // Variant-specific tracking
  isControl?: boolean;
  expectedLift?: number; // expected improvement percentage
}

export interface ABTestAssignment {
  testId: string;
  variantId: string;
  assignmentDate: Date;
  userId?: string;
  deviceId: string;
  sessionId?: string;
  userSegment?: string;
  assignmentReason: 'random' | 'override' | 'sticky' | 'excluded';
}

export interface ABTestEvent {
  testId: string;
  variantId: string;
  eventName: string;
  eventValue?: number;
  eventProperties?: Record<string, any>;
  timestamp: Date;
  userId?: string;
  sessionId?: string;
}

export interface ABTestResults {
  testId: string;
  status: 'running' | 'completed' | 'inconclusive';
  
  // Participation
  totalUsers: number;
  participationRate: number;
  
  // Variant performance
  variants: {
    variantId: string;
    variantName: string;
    users: number;
    conversionRate: number;
    conversionCount: number;
    averageValue?: number;
    
    // Statistical significance
    confidenceInterval?: [number, number];
    pValue?: number;
    isSignificant?: boolean;
    lift?: number; // vs control
  }[];
  
  // Test insights
  winningVariant?: string;
  recommendedAction: 'continue_testing' | 'roll_out_winner' | 'roll_back' | 'inconclusive';
  confidence: number;
  
  // Timeline data
  dailyMetrics?: Array<{
    date: string;
    variantId: string;
    users: number;
    conversions: number;
    conversionRate: number;
  }>;
}

export interface ABTestOverride {
  userId?: string;
  deviceId?: string;
  testId: string;
  variantId: string;
  reason: string;
  expiresAt?: Date;
}

class ABTestingServiceClass {
  private isInitialized = false;
  private activeTests: Map<string, ABTestConfig> = new Map();
  private userAssignments: Map<string, ABTestAssignment> = new Map();
  private deviceId: string = '';
  private userId?: string;
  private userSegment?: string;
  private overrides: Map<string, ABTestOverride> = new Map();
  
  public async initialize(): Promise<void> {
    try {
      // Get device identifier
      this.deviceId = await this.getDeviceId();
      
      // Load active tests
      await this.loadActiveTests();
      
      // Load user assignments
      await this.loadUserAssignments();
      
      // Load overrides
      await this.loadOverrides();
      
      this.isInitialized = true;
      
      console.log('🧪 A/B Testing Service initialized');
      
      AnalyticsService.track('ab_testing_initialized', {
        device_id: this.deviceId,
        active_tests_count: this.activeTests.size
      });
      
    } catch (error) {
      console.error('Failed to initialize A/B testing service:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'ab_testing',
        action: 'initialize'
      });
    }
  }

  public setUser(userId: string, userSegment?: string): void {
    this.userId = userId;
    this.userSegment = userSegment;
    
    // Re-evaluate test assignments for the user
    this.refreshUserAssignments();
  }

  public async getVariant(testId: string, defaultValue?: any): Promise<any> {
    if (!this.isInitialized) {
      console.warn('A/B Testing service not initialized, returning default value');
      return defaultValue;
    }

    try {
      const test = this.activeTests.get(testId);
      if (!test) {
        console.warn(`Test ${testId} not found, returning default value`);
        return defaultValue;
      }
      
      // Check if user should be excluded
      if (!this.shouldIncludeInTest(test)) {
        return defaultValue;
      }
      
      // Get or create assignment
      let assignment = this.userAssignments.get(testId);
      if (!assignment) {
        assignment = await this.assignUserToVariant(test);
        if (!assignment) {
          return defaultValue;
        }
      }
      
      // Find variant configuration
      const variant = [test.controlVariant, ...test.testVariants]
        .find(v => v.variantId === assignment!.variantId);
      
      if (!variant) {
        console.error(`Variant ${assignment.variantId} not found for test ${testId}`);
        return defaultValue;
      }
      
      // Track variant exposure
      this.trackEvent(testId, assignment.variantId, 'variant_exposed');
      
      // Return variant configuration
      return variant.configuration;
      
    } catch (error) {
      console.error(`Error getting variant for test ${testId}:`, error);
      CrashReportingService.recordError(error as Error, {
        service: 'ab_testing',
        action: 'get_variant',
        testId
      });
      return defaultValue;
    }
  }

  public async trackConversion(testId: string, conversionValue?: number, properties?: Record<string, any>): Promise<void> {
    if (!this.isInitialized) return;

    try {
      const assignment = this.userAssignments.get(testId);
      if (!assignment) {
        console.warn(`No assignment found for test ${testId}, cannot track conversion`);
        return;
      }
      
      this.trackEvent(testId, assignment.variantId, 'conversion', conversionValue, properties);
      
    } catch (error) {
      console.error(`Error tracking conversion for test ${testId}:`, error);
      CrashReportingService.recordError(error as Error, {
        service: 'ab_testing',
        action: 'track_conversion',
        testId
      });
    }
  }

  public async trackCustomEvent(testId: string, eventName: string, eventValue?: number, properties?: Record<string, any>): Promise<void> {
    if (!this.isInitialized) return;

    try {
      const assignment = this.userAssignments.get(testId);
      if (!assignment) {
        console.warn(`No assignment found for test ${testId}, cannot track event ${eventName}`);
        return;
      }
      
      this.trackEvent(testId, assignment.variantId, eventName, eventValue, properties);
      
    } catch (error) {
      console.error(`Error tracking custom event ${eventName} for test ${testId}:`, error);
      CrashReportingService.recordError(error as Error, {
        service: 'ab_testing',
        action: 'track_custom_event',
        testId,
        eventName
      });
    }
  }

  public getActiveTests(): ABTestConfig[] {
    return Array.from(this.activeTests.values());
  }

  public getUserAssignments(): ABTestAssignment[] {
    return Array.from(this.userAssignments.values());
  }

  public async addOverride(override: ABTestOverride): Promise<void> {
    const key = `${override.testId}_${override.userId || override.deviceId}`;
    this.overrides.set(key, override);
    
    // Force re-assignment for this test
    if (this.userAssignments.has(override.testId)) {
      this.userAssignments.delete(override.testId);
    }
    
    await this.saveOverrides();
    
    // Re-assign with override
    const test = this.activeTests.get(override.testId);
    if (test) {
      await this.assignUserToVariant(test);
    }
  }

  public async removeOverride(testId: string, userId?: string, deviceId?: string): Promise<void> {
    const key = `${testId}_${userId || deviceId || this.deviceId}`;
    this.overrides.delete(key);
    await this.saveOverrides();
    
    // Force re-assignment
    if (this.userAssignments.has(testId)) {
      this.userAssignments.delete(testId);
    }
  }

  public async refreshTests(): Promise<void> {
    // In a real implementation, this would fetch from a remote config service
    console.log('Refreshing A/B tests configuration...');
    // await this.loadActiveTests();
    // this.refreshUserAssignments();
  }

  private async assignUserToVariant(test: ABTestConfig): Promise<ABTestAssignment | null> {
    try {
      // Check for overrides first
      const overrideKey = `${test.testId}_${this.userId || this.deviceId}`;
      const override = this.overrides.get(overrideKey);
      
      if (override) {
        const assignment: ABTestAssignment = {
          testId: test.testId,
          variantId: override.variantId,
          assignmentDate: new Date(),
          userId: this.userId,
          deviceId: this.deviceId,
          userSegment: this.userSegment,
          assignmentReason: 'override'
        };
        
        this.userAssignments.set(test.testId, assignment);
        await this.saveUserAssignments();
        
        AnalyticsService.track('ab_test_assignment_override', {
          test_id: test.testId,
          variant_id: assignment.variantId,
          user_id: this.userId,
          device_id: this.deviceId
        });
        
        return assignment;
      }
      
      // Check if user should participate in test
      if (!this.shouldParticipateInTest(test)) {
        return null;
      }
      
      // Determine variant using consistent hashing
      const variants = [test.controlVariant, ...test.testVariants];
      const variantId = this.selectVariant(test.testId, variants);
      
      const assignment: ABTestAssignment = {
        testId: test.testId,
        variantId,
        assignmentDate: new Date(),
        userId: this.userId,
        deviceId: this.deviceId,
        userSegment: this.userSegment,
        assignmentReason: 'random'
      };
      
      this.userAssignments.set(test.testId, assignment);
      await this.saveUserAssignments();
      
      AnalyticsService.track('ab_test_assignment', {
        test_id: test.testId,
        variant_id: assignment.variantId,
        user_id: this.userId,
        device_id: this.deviceId,
        user_segment: this.userSegment
      });
      
      return assignment;
      
    } catch (error) {
      console.error(`Error assigning user to variant for test ${test.testId}:`, error);
      return null;
    }
  }

  private shouldIncludeInTest(test: ABTestConfig): boolean {
    // Check test status
    if (test.status !== 'active') return false;
    
    // Check date range
    const now = new Date();
    if (now < test.startDate) return false;
    if (test.endDate && now > test.endDate) return false;
    
    // Check platform
    if (test.targetPlatforms && !test.targetPlatforms.includes(Platform.OS as 'ios' | 'android')) {
      return false;
    }
    
    // Check user segment
    if (test.targetUserSegments && this.userSegment && !test.targetUserSegments.includes(this.userSegment)) {
      return false;
    }
    
    return true;
  }

  private shouldParticipateInTest(test: ABTestConfig): boolean {
    // Check basic inclusion criteria
    if (!this.shouldIncludeInTest(test)) return false;
    
    // Check if user is in target percentage using consistent hashing
    const hash = this.hashString(this.deviceId + test.testId);
    const userPercentile = (hash % 10000) / 100; // 0-99.99
    
    return userPercentile < test.targetPercentage;
  }

  private selectVariant(testId: string, variants: ABTestVariant[]): string {
    // Use consistent hashing for variant selection
    const seed = this.deviceId + testId + 'variant';
    const hash = this.hashString(seed);
    const random = (hash % 10000) / 10000; // 0-0.9999
    
    // Calculate cumulative weights
    const totalWeight = variants.reduce((sum, v) => sum + v.weight, 0);
    let cumulativeWeight = 0;
    const normalizedRandom = random * totalWeight;
    
    for (const variant of variants) {
      cumulativeWeight += variant.weight;
      if (normalizedRandom <= cumulativeWeight) {
        return variant.variantId;
      }
    }
    
    // Fallback to control
    return variants[0].variantId;
  }

  private trackEvent(testId: string, variantId: string, eventName: string, eventValue?: number, properties?: Record<string, any>): void {
    const event: ABTestEvent = {
      testId,
      variantId,
      eventName,
      eventValue,
      eventProperties: properties,
      timestamp: new Date(),
      userId: this.userId
    };
    
    // Track in analytics
    AnalyticsService.track('ab_test_event', {
      test_id: testId,
      variant_id: variantId,
      event_name: eventName,
      event_value: eventValue,
      event_properties: properties,
      user_id: this.userId,
      device_id: this.deviceId
    });
    
    // Store locally for offline support (optional)
    this.storeEventLocally(event);
  }

  private async refreshUserAssignments(): Promise<void> {
    // Re-evaluate all active tests for current user
    for (const test of this.activeTests.values()) {
      if (this.shouldIncludeInTest(test)) {
        // Only refresh if not sticky assignment or no existing assignment
        const existingAssignment = this.userAssignments.get(test.testId);
        if (!test.stickyAssignment || !existingAssignment) {
          await this.assignUserToVariant(test);
        }
      }
    }
  }

  private async loadActiveTests(): Promise<void> {
    try {
      // In a real implementation, this would load from remote config or local storage
      // For now, we'll load some example tests
      await this.loadExampleTests();
    } catch (error) {
      console.error('Failed to load active tests:', error);
    }
  }

  private async loadExampleTests(): Promise<void> {
    // Example A/B tests for different scenarios
    const exampleTests: ABTestConfig[] = [
      {
        testId: 'onboarding_flow_v2',
        testName: 'New Onboarding Flow',
        description: 'Test new streamlined onboarding vs current flow',
        status: 'active',
        targetPercentage: 50,
        controlVariant: {
          variantId: 'current_onboarding',
          variantName: 'Current Onboarding',
          weight: 50,
          configuration: {
            onboardingSteps: 5,
            showTutorial: true,
            skipOption: false
          },
          isControl: true
        },
        testVariants: [{
          variantId: 'streamlined_onboarding',
          variantName: 'Streamlined Onboarding',
          weight: 50,
          configuration: {
            onboardingSteps: 3,
            showTutorial: false,
            skipOption: true
          },
          expectedLift: 15
        }],
        startDate: new Date('2024-01-01'),
        endDate: new Date('2024-03-01'),
        primaryMetric: 'onboarding_completion_rate',
        secondaryMetrics: ['time_to_first_action', 'retention_day_7'],
        minimumSampleSize: 1000,
        confidenceLevel: 95,
        minimumDetectableEffect: 10,
        stickyAssignment: true
      },
      {
        testId: 'premium_pricing_test',
        testName: 'Premium Pricing Options',
        description: 'Test different pricing models for premium features',
        status: 'active',
        targetPercentage: 30,
        controlVariant: {
          variantId: 'current_pricing',
          variantName: 'Current Pricing',
          weight: 34,
          configuration: {
            monthlyPrice: 4.99,
            annualPrice: 49.99,
            freeTrialDays: 7
          },
          isControl: true
        },
        testVariants: [
          {
            variantId: 'higher_pricing',
            variantName: 'Higher Pricing',
            weight: 33,
            configuration: {
              monthlyPrice: 6.99,
              annualPrice: 59.99,
              freeTrialDays: 7
            },
            expectedLift: -10
          },
          {
            variantId: 'longer_trial',
            variantName: 'Longer Trial',
            weight: 33,
            configuration: {
              monthlyPrice: 4.99,
              annualPrice: 49.99,
              freeTrialDays: 14
            },
            expectedLift: 20
          }
        ],
        startDate: new Date('2024-01-15'),
        endDate: new Date('2024-04-15'),
        primaryMetric: 'premium_conversion_rate',
        secondaryMetrics: ['trial_to_paid_rate', 'revenue_per_user'],
        minimumSampleSize: 2000,
        confidenceLevel: 95,
        minimumDetectableEffect: 5,
        stickyAssignment: true,
        targetUserSegments: ['free_user']
      }
    ];
    
    // Load tests into memory
    for (const test of exampleTests) {
      this.activeTests.set(test.testId, test);
    }
  }

  private async loadUserAssignments(): Promise<void> {
    try {
      const stored = await AsyncStorage.getItem('ab_test_assignments');
      if (stored) {
        const assignments: ABTestAssignment[] = JSON.parse(stored);
        for (const assignment of assignments) {
          assignment.assignmentDate = new Date(assignment.assignmentDate);
          this.userAssignments.set(assignment.testId, assignment);
        }
      }
    } catch (error) {
      console.error('Failed to load user assignments:', error);
    }
  }

  private async saveUserAssignments(): Promise<void> {
    try {
      const assignments = Array.from(this.userAssignments.values());
      await AsyncStorage.setItem('ab_test_assignments', JSON.stringify(assignments));
    } catch (error) {
      console.error('Failed to save user assignments:', error);
    }
  }

  private async loadOverrides(): Promise<void> {
    try {
      const stored = await AsyncStorage.getItem('ab_test_overrides');
      if (stored) {
        const overrides: ABTestOverride[] = JSON.parse(stored);
        for (const override of overrides) {
          if (override.expiresAt) {
            override.expiresAt = new Date(override.expiresAt);
            // Skip expired overrides
            if (override.expiresAt < new Date()) continue;
          }
          const key = `${override.testId}_${override.userId || override.deviceId}`;
          this.overrides.set(key, override);
        }
      }
    } catch (error) {
      console.error('Failed to load overrides:', error);
    }
  }

  private async saveOverrides(): Promise<void> {
    try {
      const overrides = Array.from(this.overrides.values());
      await AsyncStorage.setItem('ab_test_overrides', JSON.stringify(overrides));
    } catch (error) {
      console.error('Failed to save overrides:', error);
    }
  }

  private async getDeviceId(): Promise<string> {
    try {
      // Try to get a consistent device identifier
      let deviceId = await AsyncStorage.getItem('ab_device_id');
      
      if (!deviceId) {
        // Generate new device ID
        deviceId = `${Platform.OS}_${Date.now()}_${Math.random().toString(36).substring(7)}`;
        
        // Try to make it more stable with device info
        if (Device.modelId) {
          deviceId = `${Platform.OS}_${Device.modelId}_${Application.nativeBuildVersion || '1'}_${Date.now()}`;
        }
        
        await AsyncStorage.setItem('ab_device_id', deviceId);
      }
      
      return deviceId;
    } catch (error) {
      console.error('Failed to get device ID:', error);
      return `fallback_${Date.now()}`;
    }
  }

  private hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash);
  }

  private async storeEventLocally(event: ABTestEvent): Promise<void> {
    try {
      // Store for offline support and local analytics
      const key = 'ab_test_events';
      const stored = await AsyncStorage.getItem(key);
      const events: ABTestEvent[] = stored ? JSON.parse(stored) : [];
      
      events.push(event);
      
      // Keep only recent events (last 1000)
      if (events.length > 1000) {
        events.splice(0, events.length - 1000);
      }
      
      await AsyncStorage.setItem(key, JSON.stringify(events));
    } catch (error) {
      console.error('Failed to store event locally:', error);
    }
  }

  public async getLocalEvents(): Promise<ABTestEvent[]> {
    try {
      const stored = await AsyncStorage.getItem('ab_test_events');
      if (stored) {
        const events: ABTestEvent[] = JSON.parse(stored);
        return events.map(event => ({
          ...event,
          timestamp: new Date(event.timestamp)
        }));
      }
    } catch (error) {
      console.error('Failed to get local events:', error);
    }
    return [];
  }

  public async clearLocalData(): Promise<void> {
    try {
      await AsyncStorage.multiRemove([
        'ab_test_assignments',
        'ab_test_overrides',
        'ab_test_events',
        'ab_device_id'
      ]);
      
      this.userAssignments.clear();
      this.overrides.clear();
      this.deviceId = '';
      
      // Re-initialize
      await this.initialize();
    } catch (error) {
      console.error('Failed to clear A/B testing data:', error);
    }
  }

  public getDebugInfo(): any {
    return {
      isInitialized: this.isInitialized,
      deviceId: this.deviceId,
      userId: this.userId,
      userSegment: this.userSegment,
      activeTestsCount: this.activeTests.size,
      userAssignmentsCount: this.userAssignments.size,
      overridesCount: this.overrides.size,
      activeTests: Array.from(this.activeTests.keys()),
      userAssignments: Array.from(this.userAssignments.entries()).map(([testId, assignment]) => ({
        testId,
        variantId: assignment.variantId,
        assignmentReason: assignment.assignmentReason
      })),
      overrides: Array.from(this.overrides.entries()).map(([key, override]) => ({
        key,
        testId: override.testId,
        variantId: override.variantId,
        reason: override.reason
      }))
    };
  }
}

export const ABTestingService = new ABTestingServiceClass();