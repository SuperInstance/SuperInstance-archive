import * as Sentry from '@sentry/react-native';
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Application from 'expo-application';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface CrashContext {
  userId?: string;
  sessionId?: string;
  userAgent?: string;
  buildId?: string;
  releaseChannel?: string;
  [key: string]: any;
}

export interface BreadcrumbData {
  message: string;
  category?: string;
  level?: 'info' | 'warning' | 'error' | 'debug';
  data?: Record<string, any>;
}

export interface PerformanceMetrics {
  name: string;
  duration: number;
  tags?: Record<string, string>;
  data?: Record<string, any>;
}

class CrashReportingServiceClass {
  private isInitialized = false;
  private context: CrashContext = {};
  private performanceTransactions: Map<string, any> = new Map();

  public async initialize(): Promise<void> {
    try {
      const sentryDsn = Constants.expoConfig?.extra?.sentryDsn;
      
      if (!sentryDsn) {
        console.warn('Sentry DSN not found, crash reporting will be disabled');
        return;
      }

      // Initialize Sentry with comprehensive configuration
      Sentry.init({
        dsn: sentryDsn,
        debug: __DEV__,
        enableAutoSessionTracking: true,
        sessionTrackingIntervalMillis: 30000,
        enableNative: true,
        enableNativeCrashHandling: true,
        enableAutoPerformanceTracing: true,
        enableOutOfMemoryTracking: true,
        attachStacktrace: true,
        autoSessionTracking: true,
        enableCaptureFailedRequests: true,
        
        // Release and environment configuration
        release: `${Constants.expoConfig?.version}-${Application.nativeBuildVersion}`,
        environment: __DEV__ ? 'development' : 'production',
        dist: Application.nativeBuildVersion || '1',

        // Before send hook to filter and enhance events
        beforeSend: (event, hint) => {
          // Don't send events in development unless explicitly enabled
          if (__DEV__ && !this.shouldSendInDevelopment()) {
            return null;
          }

          // Add custom context
          if (this.context) {
            event.contexts = {
              ...event.contexts,
              app_context: this.context,
            };
          }

          // Filter out known non-critical errors
          if (this.isKnownNonCriticalError(event, hint)) {
            return null;
          }

          return event;
        },

        // Performance monitoring
        tracesSampleRate: __DEV__ ? 1.0 : 0.2, // 20% sampling in production
        
        // Integrations
        integrations: [
          new Sentry.ReactNativeTracing({
            enableStallTracking: true,
            enableAppStartTracking: true,
            enableNativeFramesTracking: true,
            enableUserInteractionTracing: true,
          }),
        ],
      });

      // Set initial context
      await this.setInitialContext();

      this.isInitialized = true;

      console.log('💥 Crash reporting initialized successfully');
    } catch (error) {
      console.error('Failed to initialize crash reporting:', error);
    }
  }

  public setUser(userId: string, email?: string, username?: string, additionalData?: Record<string, any>): void {
    if (!this.isInitialized) return;

    try {
      Sentry.setUser({
        id: userId,
        email,
        username,
        ...additionalData,
      });

      this.context.userId = userId;
      
      console.log('👤 User context set for crash reporting:', userId);
    } catch (error) {
      console.error('Failed to set user context:', error);
    }
  }

  public setContext(key: string, context: Record<string, any>): void {
    if (!this.isInitialized) return;

    try {
      Sentry.setContext(key, context);
      this.context[key] = context;
      
      console.log(`🏷️ Context set: ${key}`);
    } catch (error) {
      console.error('Failed to set context:', error);
    }
  }

  public addBreadcrumb(breadcrumb: BreadcrumbData): void {
    if (!this.isInitialized) return;

    try {
      Sentry.addBreadcrumb({
        message: breadcrumb.message,
        category: breadcrumb.category || 'default',
        level: breadcrumb.level || 'info',
        data: breadcrumb.data,
        timestamp: Date.now() / 1000,
      });

      if (__DEV__) {
        console.log('🍞 Breadcrumb added:', breadcrumb.message);
      }
    } catch (error) {
      console.error('Failed to add breadcrumb:', error);
    }
  }

  public recordError(error: Error, context?: Record<string, any>, level: 'error' | 'warning' | 'info' = 'error'): void {
    if (!this.isInitialized) return;

    try {
      Sentry.withScope((scope) => {
        scope.setLevel(level);
        
        if (context) {
          Object.entries(context).forEach(([key, value]) => {
            scope.setTag(key, String(value));
          });
          scope.setContext('error_context', context);
        }

        Sentry.captureException(error);
      });

      if (__DEV__) {
        console.error('💥 Error recorded:', error);
      }
    } catch (recordingError) {
      console.error('Failed to record error:', recordingError);
    }
  }

  public recordMessage(message: string, level: 'error' | 'warning' | 'info' | 'debug' = 'info', context?: Record<string, any>): void {
    if (!this.isInitialized) return;

    try {
      Sentry.withScope((scope) => {
        scope.setLevel(level);
        
        if (context) {
          Object.entries(context).forEach(([key, value]) => {
            scope.setTag(key, String(value));
          });
          scope.setContext('message_context', context);
        }

        Sentry.captureMessage(message);
      });

      if (__DEV__) {
        console.log(`📝 Message recorded [${level}]:`, message);
      }
    } catch (error) {
      console.error('Failed to record message:', error);
    }
  }

  public startTransaction(name: string, op: string = 'custom', tags?: Record<string, string>): string {
    if (!this.isInitialized) return '';

    try {
      const transaction = Sentry.startTransaction({
        name,
        op,
        tags,
      });

      const transactionId = `${name}_${Date.now()}`;
      this.performanceTransactions.set(transactionId, transaction);

      if (__DEV__) {
        console.log(`⏱️ Transaction started: ${name}`);
      }

      return transactionId;
    } catch (error) {
      console.error('Failed to start transaction:', error);
      return '';
    }
  }

  public finishTransaction(transactionId: string, status?: string): void {
    if (!this.isInitialized || !transactionId) return;

    try {
      const transaction = this.performanceTransactions.get(transactionId);
      if (transaction) {
        if (status) {
          transaction.setStatus(status);
        }
        transaction.finish();
        this.performanceTransactions.delete(transactionId);

        if (__DEV__) {
          console.log(`✅ Transaction finished: ${transactionId}`);
        }
      }
    } catch (error) {
      console.error('Failed to finish transaction:', error);
    }
  }

  public recordPerformanceMetrics(metrics: PerformanceMetrics): void {
    if (!this.isInitialized) return;

    try {
      const transaction = Sentry.startTransaction({
        name: metrics.name,
        op: 'performance',
        tags: metrics.tags,
      });

      // Add custom measurements
      if (metrics.data) {
        Object.entries(metrics.data).forEach(([key, value]) => {
          if (typeof value === 'number') {
            transaction.setMeasurement(key, value);
          }
        });
      }

      // Simulate the duration
      setTimeout(() => {
        transaction.finish();
      }, metrics.duration);

      if (__DEV__) {
        console.log(`📊 Performance metrics recorded: ${metrics.name} (${metrics.duration}ms)`);
      }
    } catch (error) {
      console.error('Failed to record performance metrics:', error);
    }
  }

  public setTag(key: string, value: string): void {
    if (!this.isInitialized) return;

    try {
      Sentry.setTag(key, value);
      
      if (__DEV__) {
        console.log(`🏷️ Tag set: ${key} = ${value}`);
      }
    } catch (error) {
      console.error('Failed to set tag:', error);
    }
  }

  public setExtra(key: string, extra: any): void {
    if (!this.isInitialized) return;

    try {
      Sentry.setExtra(key, extra);
      
      if (__DEV__) {
        console.log(`📎 Extra set: ${key}`);
      }
    } catch (error) {
      console.error('Failed to set extra:', error);
    }
  }

  public flush(timeout: number = 2000): Promise<boolean> {
    if (!this.isInitialized) {
      return Promise.resolve(false);
    }

    try {
      return Sentry.flush(timeout);
    } catch (error) {
      console.error('Failed to flush crash reports:', error);
      return Promise.resolve(false);
    }
  }

  public close(timeout: number = 2000): Promise<boolean> {
    if (!this.isInitialized) {
      return Promise.resolve(false);
    }

    try {
      return Sentry.close(timeout);
    } catch (error) {
      console.error('Failed to close crash reporting:', error);
      return Promise.resolve(false);
    }
  }

  // Utility methods for common scenarios
  public recordApiError(url: string, method: string, statusCode: number, error: Error): void {
    this.recordError(error, {
      api_url: url,
      api_method: method,
      api_status_code: statusCode,
      error_type: 'api_error',
    });
  }

  public recordNavigationError(screen: string, error: Error): void {
    this.recordError(error, {
      screen_name: screen,
      error_type: 'navigation_error',
    });
  }

  public recordRenderError(component: string, error: Error): void {
    this.recordError(error, {
      component_name: component,
      error_type: 'render_error',
    });
  }

  public recordDataError(operation: string, error: Error, data?: any): void {
    this.recordError(error, {
      data_operation: operation,
      error_type: 'data_error',
      data_snapshot: data ? JSON.stringify(data).substring(0, 1000) : undefined,
    });
  }

  private async setInitialContext(): Promise<void> {
    try {
      // Device information
      Sentry.setContext('device', {
        model: Device.modelName,
        brand: Device.brand,
        manufacturer: Device.manufacturer,
        modelId: Device.modelId,
        osName: Device.osName,
        osVersion: Device.osVersion,
        osBuildId: Device.osBuildId,
        deviceYearClass: Device.deviceYearClass,
        totalMemory: Device.totalMemory,
        platform: Platform.OS,
      });

      // App information
      Sentry.setContext('app', {
        name: Constants.expoConfig?.name,
        version: Constants.expoConfig?.version,
        buildVersion: Application.nativeBuildVersion,
        bundleId: Application.applicationId,
        buildId: Constants.expoConfig?.extra?.eas?.projectId,
        releaseChannel: Constants.expoConfig?.releaseChannel,
        sdkVersion: Constants.expoConfig?.sdkVersion,
      });

      // Runtime information
      Sentry.setContext('runtime', {
        platform: Platform.OS,
        version: Platform.Version,
        isDevice: Device.isDevice,
        isTablet: Device.deviceType === Device.DeviceType.TABLET,
      });

      // Store session info
      const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      this.context.sessionId = sessionId;
      
      await AsyncStorage.setItem('crash_session_id', sessionId);

      if (__DEV__) {
        console.log('🏷️ Initial crash reporting context set');
      }
    } catch (error) {
      console.error('Failed to set initial context:', error);
    }
  }

  private shouldSendInDevelopment(): boolean {
    // Only send crash reports in development if explicitly enabled
    return Constants.expoConfig?.extra?.enableCrashReportingInDev === true;
  }

  private isKnownNonCriticalError(event: any, hint?: any): boolean {
    const error = hint?.originalException || hint?.syntheticException;
    
    if (!error) return false;

    const nonCriticalPatterns = [
      /Network request failed/i,
      /Request timeout/i,
      /Connection lost/i,
      /User cancelled/i,
      /Aborted/i,
      /Task was cancelled/i,
      /The operation couldn't be completed/i,
    ];

    const errorMessage = error.message || '';
    
    return nonCriticalPatterns.some(pattern => pattern.test(errorMessage));
  }

  public getContext(): CrashContext {
    return { ...this.context };
  }

  public isInitialized(): boolean {
    return this.isInitialized;
  }
}

export const CrashReportingService = new CrashReportingServiceClass();