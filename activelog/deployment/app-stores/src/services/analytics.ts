import { Mixpanel } from 'mixpanel-react-native';
import { Amplitude, Identify } from '@amplitude/react-native';
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Application from 'expo-application';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface AnalyticsEvent {
  name: string;
  properties?: Record<string, any>;
  timestamp?: Date;
  userId?: string;
  sessionId?: string;
}

export interface UserProfile {
  userId: string;
  email?: string;
  name?: string;
  appVariant: string;
  subscriptionTier?: 'free' | 'premium' | 'business';
  signupDate?: Date;
  lastActiveDate?: Date;
  totalSessions?: number;
  customProperties?: Record<string, any>;
}

export interface AnalyticsConfig {
  mixpanelToken?: string;
  amplitudeApiKey?: string;
  enableMixpanel: boolean;
  enableAmplitude: boolean;
  enableDebugLogging: boolean;
  flushInterval: number;
  maxBatchSize: number;
}

class AnalyticsServiceClass {
  private mixpanel: Mixpanel | null = null;
  private amplitude: Amplitude | null = null;
  private config: AnalyticsConfig;
  private isInitialized = false;
  private eventQueue: AnalyticsEvent[] = [];
  private sessionId: string | null = null;
  private sessionStartTime: Date | null = null;
  private userId: string | null = null;
  private userProfile: UserProfile | null = null;

  constructor() {
    this.config = {
      enableMixpanel: true,
      enableAmplitude: true,
      enableDebugLogging: __DEV__,
      flushInterval: 30000, // 30 seconds
      maxBatchSize: 50,
    };
  }

  public async initialize(appVariant: string): Promise<void> {
    try {
      this.config.mixpanelToken = Constants.expoConfig?.extra?.mixpanelToken;
      this.config.amplitudeApiKey = Constants.expoConfig?.extra?.amplitudeApiKey;

      // Initialize Mixpanel
      if (this.config.enableMixpanel && this.config.mixpanelToken) {
        this.mixpanel = new Mixpanel(this.config.mixpanelToken, false);
        await this.mixpanel.init();
        
        if (this.config.enableDebugLogging) {
          console.log('🔍 Mixpanel initialized successfully');
        }
      }

      // Initialize Amplitude
      if (this.config.enableAmplitude && this.config.amplitudeApiKey) {
        this.amplitude = Amplitude.getInstance();
        this.amplitude.init(this.config.amplitudeApiKey);
        
        if (this.config.enableDebugLogging) {
          console.log('🔍 Amplitude initialized successfully');
        }
      }

      // Set up device properties
      await this.setDeviceProperties(appVariant);

      // Start session
      await this.startSession();

      // Set up flush interval
      this.setupFlushInterval();

      this.isInitialized = true;

      if (this.config.enableDebugLogging) {
        console.log('📊 Analytics service initialized');
      }
    } catch (error) {
      console.error('Failed to initialize analytics:', error);
    }
  }

  public async identify(userId: string, userProfile?: Partial<UserProfile>): Promise<void> {
    if (!this.isInitialized) {
      console.warn('Analytics not initialized');
      return;
    }

    try {
      this.userId = userId;
      
      // Store user profile
      const profile: UserProfile = {
        userId,
        appVariant: userProfile?.appVariant || 'unknown',
        signupDate: new Date(),
        lastActiveDate: new Date(),
        totalSessions: 1,
        ...userProfile,
      };
      this.userProfile = profile;

      // Identify in Mixpanel
      if (this.mixpanel) {
        this.mixpanel.identify(userId);
        this.mixpanel.getPeople().set({
          '$email': profile.email,
          '$name': profile.name,
          'app_variant': profile.appVariant,
          'subscription_tier': profile.subscriptionTier,
          'signup_date': profile.signupDate?.toISOString(),
          'last_active': profile.lastActiveDate?.toISOString(),
          ...profile.customProperties,
        });
      }

      // Identify in Amplitude
      if (this.amplitude) {
        this.amplitude.setUserId(userId);
        
        const identify = new Identify();
        if (profile.email) identify.set('email', profile.email);
        if (profile.name) identify.set('name', profile.name);
        identify.set('app_variant', profile.appVariant);
        if (profile.subscriptionTier) identify.set('subscription_tier', profile.subscriptionTier);
        if (profile.signupDate) identify.set('signup_date', profile.signupDate.toISOString());
        identify.set('last_active', profile.lastActiveDate?.toISOString());
        
        if (profile.customProperties) {
          Object.entries(profile.customProperties).forEach(([key, value]) => {
            identify.set(key, value);
          });
        }
        
        this.amplitude.identify(identify);
      }

      // Store user info locally
      await AsyncStorage.setItem('analytics_user_id', userId);
      await AsyncStorage.setItem('analytics_user_profile', JSON.stringify(profile));

      if (this.config.enableDebugLogging) {
        console.log('👤 User identified:', userId);
      }
    } catch (error) {
      console.error('Failed to identify user:', error);
    }
  }

  public track(eventName: string, properties?: Record<string, any>): void {
    if (!this.isInitialized) {
      // Queue event for later
      this.eventQueue.push({
        name: eventName,
        properties,
        timestamp: new Date(),
        userId: this.userId || undefined,
        sessionId: this.sessionId || undefined,
      });
      return;
    }

    try {
      const enrichedProperties = {
        ...properties,
        session_id: this.sessionId,
        user_id: this.userId,
        timestamp: new Date().toISOString(),
        platform: Platform.OS,
        app_version: Constants.expoConfig?.version,
        device_model: Device.modelName,
        os_version: Device.osVersion,
      };

      // Track in Mixpanel
      if (this.mixpanel) {
        this.mixpanel.track(eventName, enrichedProperties);
      }

      // Track in Amplitude
      if (this.amplitude) {
        this.amplitude.logEvent(eventName, enrichedProperties);
      }

      if (this.config.enableDebugLogging) {
        console.log('📈 Event tracked:', eventName, enrichedProperties);
      }
    } catch (error) {
      console.error('Failed to track event:', error);
    }
  }

  public trackUserAction(action: string, context?: Record<string, any>): void {
    this.track('user_action', {
      action,
      ...context,
    });
  }

  public trackScreenView(screenName: string, properties?: Record<string, any>): void {
    this.track('screen_view', {
      screen_name: screenName,
      ...properties,
    });
  }

  public trackError(error: Error, context?: Record<string, any>): void {
    this.track('error_occurred', {
      error_name: error.name,
      error_message: error.message,
      error_stack: error.stack,
      ...context,
    });
  }

  public trackPurchase(productId: string, price: number, currency: string, properties?: Record<string, any>): void {
    const purchaseProperties = {
      product_id: productId,
      price,
      currency,
      ...properties,
    };

    this.track('purchase_completed', purchaseProperties);

    // Track revenue in Mixpanel
    if (this.mixpanel) {
      this.mixpanel.getPeople().trackCharge(price, {
        product_id: productId,
        currency,
        ...properties,
      });
    }

    // Track revenue in Amplitude
    if (this.amplitude) {
      this.amplitude.logRevenue(productId, 1, price);
    }
  }

  public trackSubscription(planId: string, price: number, currency: string, isUpgrade: boolean = false): void {
    this.track('subscription_activated', {
      plan_id: planId,
      price,
      currency,
      is_upgrade: isUpgrade,
    });

    // Update user profile
    if (this.userProfile) {
      this.userProfile.subscriptionTier = this.getSubscriptionTier(planId);
      this.identify(this.userId!, this.userProfile);
    }
  }

  public trackSessionStart(): void {
    this.sessionStartTime = new Date();
    this.sessionId = this.generateSessionId();
    
    this.track('session_start', {
      session_id: this.sessionId,
    });
  }

  public trackSessionEnd(): void {
    if (this.sessionStartTime) {
      const duration = new Date().getTime() - this.sessionStartTime.getTime();
      
      this.track('session_end', {
        session_id: this.sessionId,
        duration_ms: duration,
        duration_seconds: Math.floor(duration / 1000),
      });

      this.sessionStartTime = null;
      this.sessionId = null;
    }
  }

  public incrementUserProperty(property: string, value: number = 1): void {
    try {
      if (this.mixpanel) {
        this.mixpanel.getPeople().increment(property, value);
      }

      if (this.amplitude) {
        const identify = new Identify();
        identify.add(property, value);
        this.amplitude.identify(identify);
      }

      if (this.config.enableDebugLogging) {
        console.log(`📊 Incremented user property: ${property} by ${value}`);
      }
    } catch (error) {
      console.error('Failed to increment user property:', error);
    }
  }

  public setUserProperty(property: string, value: any): void {
    try {
      if (this.mixpanel) {
        this.mixpanel.getPeople().set({ [property]: value });
      }

      if (this.amplitude) {
        const identify = new Identify();
        identify.set(property, value);
        this.amplitude.identify(identify);
      }

      if (this.config.enableDebugLogging) {
        console.log(`👤 Set user property: ${property} = ${value}`);
      }
    } catch (error) {
      console.error('Failed to set user property:', error);
    }
  }

  public async flush(): Promise<void> {
    try {
      if (this.mixpanel) {
        await this.mixpanel.flush();
      }

      if (this.amplitude) {
        this.amplitude.uploadEvents();
      }

      if (this.config.enableDebugLogging) {
        console.log('📤 Analytics events flushed');
      }
    } catch (error) {
      console.error('Failed to flush analytics:', error);
    }
  }

  public reset(): void {
    try {
      this.userId = null;
      this.userProfile = null;
      this.sessionId = null;
      this.sessionStartTime = null;

      if (this.mixpanel) {
        this.mixpanel.reset();
      }

      if (this.amplitude) {
        this.amplitude.setUserId(null);
        this.amplitude.regenerateDeviceId();
      }

      // Clear stored data
      AsyncStorage.multiRemove(['analytics_user_id', 'analytics_user_profile']);

      if (this.config.enableDebugLogging) {
        console.log('🔄 Analytics reset');
      }
    } catch (error) {
      console.error('Failed to reset analytics:', error);
    }
  }

  private async setDeviceProperties(appVariant: string): Promise<void> {
    try {
      const deviceProperties = {
        app_variant: appVariant,
        platform: Platform.OS,
        device_model: Device.modelName,
        device_brand: Device.brand,
        os_version: Device.osVersion,
        app_version: Constants.expoConfig?.version,
        app_build_version: Application.nativeBuildVersion,
        expo_sdk_version: Constants.expoConfig?.sdkVersion,
        device_year_class: Device.deviceYearClass,
        total_memory: Device.totalMemory,
      };

      if (this.mixpanel) {
        this.mixpanel.registerSuperProperties(deviceProperties);
      }

      if (this.amplitude) {
        const identify = new Identify();
        Object.entries(deviceProperties).forEach(([key, value]) => {
          if (value !== undefined) {
            identify.setOnce(key, value);
          }
        });
        this.amplitude.identify(identify);
      }

      if (this.config.enableDebugLogging) {
        console.log('📱 Device properties set:', deviceProperties);
      }
    } catch (error) {
      console.error('Failed to set device properties:', error);
    }
  }

  private async startSession(): Promise<void> {
    try {
      // Try to restore user from storage
      const storedUserId = await AsyncStorage.getItem('analytics_user_id');
      const storedProfile = await AsyncStorage.getItem('analytics_user_profile');

      if (storedUserId) {
        this.userId = storedUserId;
        if (storedProfile) {
          this.userProfile = JSON.parse(storedProfile);
        }
      }

      this.trackSessionStart();
    } catch (error) {
      console.error('Failed to start session:', error);
    }
  }

  private setupFlushInterval(): void {
    setInterval(() => {
      this.flush();
    }, this.config.flushInterval);
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private getSubscriptionTier(planId: string): 'free' | 'premium' | 'business' {
    if (planId.includes('business')) return 'business';
    if (planId.includes('premium') || planId.includes('pro')) return 'premium';
    return 'free';
  }

  public getConfig(): AnalyticsConfig {
    return { ...this.config };
  }

  public updateConfig(updates: Partial<AnalyticsConfig>): void {
    this.config = { ...this.config, ...updates };
  }

  // A/B Testing Integration
  public trackExperiment(experimentName: string, variant: string, properties?: Record<string, any>): void {
    this.track('experiment_viewed', {
      experiment_name: experimentName,
      variant,
      ...properties,
    });
  }

  public trackConversion(experimentName: string, variant: string, conversionGoal: string, properties?: Record<string, any>): void {
    this.track('experiment_converted', {
      experiment_name: experimentName,
      variant,
      conversion_goal: conversionGoal,
      ...properties,
    });
  }
}

export const AnalyticsService = new AnalyticsServiceClass();