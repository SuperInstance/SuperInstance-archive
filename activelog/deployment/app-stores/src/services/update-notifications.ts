import * as Updates from 'expo-updates';
import * as Device from 'expo-device';
import * as Application from 'expo-application';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { AnalyticsService } from './analytics';
import { CrashReportingService } from './crash-reporting';
import { PushNotificationService } from './push-notifications';

export interface UpdateConfig {
  // Check frequency
  checkFrequency: 'startup' | 'foreground' | 'manual' | 'interval';
  checkIntervalMinutes?: number;
  
  // Update behavior
  autoDownload: boolean;
  autoInstall: boolean;
  promptBeforeDownload: boolean;
  promptBeforeInstall: boolean;
  
  // Rollout controls
  enableGradualRollout: boolean;
  rolloutPercentage: number; // 0-100
  rolloutSegments?: string[]; // User segments for staged rollout
  
  // Fallback and recovery
  enableFallback: boolean;
  maxFailedAttempts: number;
  rollbackOnError: boolean;
  
  // User communication
  showUpdateBadge: boolean;
  pushNotificationOnUpdate: boolean;
  inAppNotificationStyle: 'banner' | 'modal' | 'badge' | 'none';
  
  // Feature flags and A/B testing
  enableFeatureFlags: boolean;
  featureFlagSource?: 'remote' | 'local';
}

export interface UpdateInfo {
  isAvailable: boolean;
  isDownloaded: boolean;
  manifest?: any;
  
  // Update details
  version: string;
  buildNumber: string;
  releaseNotes?: string;
  updateSize?: number;
  releaseDate?: Date;
  priority: 'low' | 'medium' | 'high' | 'critical';
  
  // Rollout information
  rolloutPercentage: number;
  targetSegments: string[];
  
  // Feature changes
  newFeatures?: string[];
  improvements?: string[];
  bugFixes?: string[];
  breakingChanges?: boolean;
}

export interface UpdateProgress {
  stage: 'checking' | 'downloading' | 'installing' | 'complete' | 'error';
  progress: number; // 0-100
  bytesDownloaded?: number;
  totalBytes?: number;
  error?: Error;
  timeRemaining?: number; // seconds
}

export interface UpdateNotification {
  id: string;
  type: 'update_available' | 'update_downloaded' | 'update_failed' | 'update_required';
  title: string;
  message: string;
  actionButtons?: {
    primary?: { text: string; action: () => void };
    secondary?: { text: string; action: () => void };
  };
  priority: 'low' | 'high';
  persistent: boolean;
  autoHide?: number; // milliseconds
}

export interface RolloutSegment {
  id: string;
  name: string;
  criteria: {
    userType?: 'new' | 'existing' | 'premium';
    appVersion?: string[];
    platform?: ('ios' | 'android')[];
    country?: string[];
    deviceModel?: string[];
    customProperties?: Record<string, any>;
  };
  percentage: number;
}

class UpdateNotificationServiceClass {
  private config: UpdateConfig;
  private isInitialized = false;
  private lastCheckTime: Date | null = null;
  private currentUpdateInfo: UpdateInfo | null = null;
  private updateProgressCallbacks: ((progress: UpdateProgress) => void)[] = [];
  private checkInterval: NodeJS.Timeout | null = null;
  private failedAttempts = 0;
  
  constructor() {
    this.config = {
      checkFrequency: 'startup',
      checkIntervalMinutes: 60,
      autoDownload: false,
      autoInstall: false,
      promptBeforeDownload: true,
      promptBeforeInstall: true,
      enableGradualRollout: true,
      rolloutPercentage: 100,
      enableFallback: true,
      maxFailedAttempts: 3,
      rollbackOnError: false,
      showUpdateBadge: true,
      pushNotificationOnUpdate: true,
      inAppNotificationStyle: 'banner',
      enableFeatureFlags: true,
      featureFlagSource: 'remote'
    };
  }

  public async initialize(): Promise<void> {
    try {
      // Only initialize on device, not in Expo Go
      if (!Device.isDevice || __DEV__) {
        console.log('🔄 Update service disabled in development/Expo Go');
        return;
      }
      
      // Set up update event listeners
      this.setupUpdateListeners();
      
      // Load previous update state
      await this.loadUpdateState();
      
      // Start update checking based on config
      this.startUpdateChecking();
      
      this.isInitialized = true;
      
      console.log('🔄 Update Notification Service initialized');
      
      AnalyticsService.track('update_service_initialized', {
        check_frequency: this.config.checkFrequency,
        auto_download: this.config.autoDownload,
        auto_install: this.config.autoInstall
      });
      
    } catch (error) {
      console.error('Failed to initialize update service:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'update_notifications',
        action: 'initialize'
      });
    }
  }

  public async checkForUpdates(manual: boolean = false): Promise<UpdateInfo | null> {
    if (!this.isInitialized) {
      console.warn('Update service not initialized');
      return null;
    }

    try {
      this.notifyProgress({ stage: 'checking', progress: 0 });
      
      const updateCheck = await Updates.checkForUpdateAsync();
      this.lastCheckTime = new Date();
      
      if (updateCheck.isAvailable) {
        const updateInfo = await this.buildUpdateInfo(updateCheck);
        
        // Check if user is eligible for this update
        if (!await this.isEligibleForUpdate(updateInfo)) {
          console.log('User not eligible for this update rollout');
          return null;
        }
        
        this.currentUpdateInfo = updateInfo;
        await this.saveUpdateState();
        
        // Track update availability
        AnalyticsService.track('update_available', {
          version: updateInfo.version,
          priority: updateInfo.priority,
          manual_check: manual,
          rollout_percentage: updateInfo.rolloutPercentage
        });
        
        // Show notification if configured
        await this.showUpdateAvailableNotification(updateInfo);
        
        // Auto-download if enabled
        if (this.config.autoDownload && !this.config.promptBeforeDownload) {
          await this.downloadUpdate();
        }
        
        return updateInfo;
      } else {
        console.log('No updates available');
        this.notifyProgress({ stage: 'complete', progress: 100 });
        
        AnalyticsService.track('update_check_completed', {
          update_available: false,
          manual_check: manual
        });
        
        return null;
      }
    } catch (error) {
      console.error('Error checking for updates:', error);
      this.failedAttempts++;
      
      this.notifyProgress({ 
        stage: 'error', 
        progress: 0, 
        error: error as Error 
      });
      
      CrashReportingService.recordError(error as Error, {
        service: 'update_notifications',
        action: 'check_for_updates',
        failed_attempts: this.failedAttempts
      });
      
      AnalyticsService.track('update_check_failed', {
        error: (error as Error).message,
        failed_attempts: this.failedAttempts,
        manual_check: manual
      });
      
      return null;
    }
  }

  public async downloadUpdate(): Promise<boolean> {
    if (!this.currentUpdateInfo?.isAvailable) {
      console.warn('No update available to download');
      return false;
    }

    try {
      this.notifyProgress({ stage: 'downloading', progress: 0 });
      
      // If configured to prompt, show download confirmation
      if (this.config.promptBeforeDownload) {
        const userConsent = await this.showDownloadPrompt(this.currentUpdateInfo);
        if (!userConsent) {
          console.log('User declined update download');
          return false;
        }
      }
      
      const downloadResult = await Updates.fetchUpdateAsync();
      
      if (downloadResult.isNew) {
        this.currentUpdateInfo.isDownloaded = true;
        await this.saveUpdateState();
        
        this.notifyProgress({ stage: 'complete', progress: 100 });
        
        AnalyticsService.track('update_downloaded', {
          version: this.currentUpdateInfo.version,
          priority: this.currentUpdateInfo.priority
        });
        
        // Show download complete notification
        await this.showUpdateDownloadedNotification(this.currentUpdateInfo);
        
        // Auto-install if enabled
        if (this.config.autoInstall && !this.config.promptBeforeInstall) {
          await this.installUpdate();
        }
        
        return true;
      } else {
        console.log('Update download failed or no new update');
        return false;
      }
    } catch (error) {
      console.error('Error downloading update:', error);
      this.failedAttempts++;
      
      this.notifyProgress({ 
        stage: 'error', 
        progress: 0, 
        error: error as Error 
      });
      
      CrashReportingService.recordError(error as Error, {
        service: 'update_notifications',
        action: 'download_update',
        failed_attempts: this.failedAttempts
      });
      
      AnalyticsService.track('update_download_failed', {
        error: (error as Error).message,
        version: this.currentUpdateInfo?.version,
        failed_attempts: this.failedAttempts
      });
      
      return false;
    }
  }

  public async installUpdate(): Promise<boolean> {
    if (!this.currentUpdateInfo?.isDownloaded) {
      console.warn('No update downloaded to install');
      return false;
    }

    try {
      // If configured to prompt, show install confirmation
      if (this.config.promptBeforeInstall) {
        const userConsent = await this.showInstallPrompt(this.currentUpdateInfo);
        if (!userConsent) {
          console.log('User declined update installation');
          return false;
        }
      }
      
      this.notifyProgress({ stage: 'installing', progress: 50 });
      
      AnalyticsService.track('update_installing', {
        version: this.currentUpdateInfo.version,
        priority: this.currentUpdateInfo.priority
      });
      
      // Clear update state before restart
      await this.clearUpdateState();
      
      // Reload the app with the new update
      await Updates.reloadAsync();
      
      return true;
    } catch (error) {
      console.error('Error installing update:', error);
      this.failedAttempts++;
      
      this.notifyProgress({ 
        stage: 'error', 
        progress: 0, 
        error: error as Error 
      });
      
      CrashReportingService.recordError(error as Error, {
        service: 'update_notifications',
        action: 'install_update',
        failed_attempts: this.failedAttempts
      });
      
      AnalyticsService.track('update_install_failed', {
        error: (error as Error).message,
        version: this.currentUpdateInfo?.version,
        failed_attempts: this.failedAttempts
      });
      
      return false;
    }
  }

  public onUpdateProgress(callback: (progress: UpdateProgress) => void): () => void {
    this.updateProgressCallbacks.push(callback);
    
    // Return unsubscribe function
    return () => {
      const index = this.updateProgressCallbacks.indexOf(callback);
      if (index > -1) {
        this.updateProgressCallbacks.splice(index, 1);
      }
    };
  }

  public getCurrentUpdateInfo(): UpdateInfo | null {
    return this.currentUpdateInfo;
  }

  public getLastCheckTime(): Date | null {
    return this.lastCheckTime;
  }

  public async dismissUpdate(): Promise<void> {
    this.currentUpdateInfo = null;
    await this.clearUpdateState();
    
    AnalyticsService.track('update_dismissed', {
      timestamp: new Date().toISOString()
    });
  }

  public updateConfig(newConfig: Partial<UpdateConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    // Restart checking with new config
    if (this.isInitialized) {
      this.stopUpdateChecking();
      this.startUpdateChecking();
    }
  }

  public getConfig(): UpdateConfig {
    return { ...this.config };
  }

  private async buildUpdateInfo(updateCheck: any): Promise<UpdateInfo> {
    // Get current app version for comparison
    const currentVersion = Application.nativeApplicationVersion || '1.0.0';
    const currentBuildNumber = Application.nativeBuildVersion || '1';
    
    // Extract update information (this would come from your update manifest)
    const updateInfo: UpdateInfo = {
      isAvailable: updateCheck.isAvailable,
      isDownloaded: false,
      manifest: updateCheck.manifest,
      version: updateCheck.manifest?.version || currentVersion,
      buildNumber: updateCheck.manifest?.buildNumber || currentBuildNumber,
      releaseNotes: updateCheck.manifest?.releaseNotes,
      releaseDate: updateCheck.manifest?.releaseDate ? new Date(updateCheck.manifest.releaseDate) : new Date(),
      priority: updateCheck.manifest?.priority || 'medium',
      rolloutPercentage: updateCheck.manifest?.rolloutPercentage || 100,
      targetSegments: updateCheck.manifest?.targetSegments || [],
      newFeatures: updateCheck.manifest?.newFeatures || [],
      improvements: updateCheck.manifest?.improvements || [],
      bugFixes: updateCheck.manifest?.bugFixes || [],
      breakingChanges: updateCheck.manifest?.breakingChanges || false
    };
    
    return updateInfo;
  }

  private async isEligibleForUpdate(updateInfo: UpdateInfo): Promise<boolean> {
    try {
      // Check rollout percentage
      if (this.config.enableGradualRollout) {
        const userId = await AsyncStorage.getItem('user_id');
        const deviceId = await AsyncStorage.getItem('device_id');
        const identifier = userId || deviceId || Device.modelId || 'unknown';
        
        // Use consistent hashing to determine if user is in rollout
        const hash = this.hashString(identifier);
        const userPercentile = (hash % 10000) / 100; // 0-99.99
        
        if (userPercentile >= updateInfo.rolloutPercentage) {
          return false;
        }
      }
      
      // Check target segments
      if (updateInfo.targetSegments.length > 0) {
        const userSegment = await AsyncStorage.getItem('user_segment');
        if (!userSegment || !updateInfo.targetSegments.includes(userSegment)) {
          return false;
        }
      }
      
      return true;
    } catch (error) {
      console.error('Error checking update eligibility:', error);
      return true; // Default to eligible if check fails
    }
  }

  private async showUpdateAvailableNotification(updateInfo: UpdateInfo): Promise<void> {
    const notification: UpdateNotification = {
      id: `update_available_${updateInfo.version}`,
      type: 'update_available',
      title: 'Update Available',
      message: `Version ${updateInfo.version} is now available with new features and improvements.`,
      priority: updateInfo.priority === 'critical' ? 'high' : 'low',
      persistent: updateInfo.priority === 'critical',
      actionButtons: {
        primary: {
          text: 'Download',
          action: () => this.downloadUpdate()
        },
        secondary: {
          text: 'Later',
          action: () => this.dismissUpdate()
        }
      }
    };
    
    await this.showNotification(notification);
    
    // Send push notification if enabled
    if (this.config.pushNotificationOnUpdate) {
      await PushNotificationService.scheduleLocalNotification({
        title: notification.title,
        body: notification.message,
        data: {
          type: 'update_available',
          version: updateInfo.version
        },
        trigger: { type: 'time', seconds: 1 }
      });
    }
  }

  private async showUpdateDownloadedNotification(updateInfo: UpdateInfo): Promise<void> {
    const notification: UpdateNotification = {
      id: `update_downloaded_${updateInfo.version}`,
      type: 'update_downloaded',
      title: 'Update Ready',
      message: `Version ${updateInfo.version} has been downloaded and is ready to install.`,
      priority: updateInfo.priority === 'critical' ? 'high' : 'low',
      persistent: true,
      actionButtons: {
        primary: {
          text: 'Install Now',
          action: () => this.installUpdate()
        },
        secondary: {
          text: 'Install Later',
          action: () => console.log('Install deferred')
        }
      }
    };
    
    await this.showNotification(notification);
  }

  private async showNotification(notification: UpdateNotification): Promise<void> {
    // This would integrate with your app's notification system
    console.log('📢 Update notification:', notification);
    
    AnalyticsService.track('update_notification_shown', {
      notification_id: notification.id,
      notification_type: notification.type,
      priority: notification.priority
    });
  }

  private async showDownloadPrompt(updateInfo: UpdateInfo): Promise<boolean> {
    // This would show a modal/dialog to the user
    // For now, we'll simulate user consent based on update priority
    const shouldAutoConsent = updateInfo.priority === 'critical';
    
    AnalyticsService.track('update_download_prompt_shown', {
      version: updateInfo.version,
      priority: updateInfo.priority,
      auto_consent: shouldAutoConsent
    });
    
    return shouldAutoConsent;
  }

  private async showInstallPrompt(updateInfo: UpdateInfo): Promise<boolean> {
    // This would show a modal/dialog to the user
    // For now, we'll simulate user consent based on update priority
    const shouldAutoConsent = updateInfo.priority === 'critical';
    
    AnalyticsService.track('update_install_prompt_shown', {
      version: updateInfo.version,
      priority: updateInfo.priority,
      auto_consent: shouldAutoConsent
    });
    
    return shouldAutoConsent;
  }

  private setupUpdateListeners(): void {
    // Listen for update events from Expo Updates
    Updates.addListener((event) => {
      switch (event.type) {
        case Updates.UpdateEventType.ERROR:
          this.handleUpdateError(event);
          break;
        case Updates.UpdateEventType.NO_UPDATE_AVAILABLE:
          this.handleNoUpdateAvailable();
          break;
        case Updates.UpdateEventType.UPDATE_AVAILABLE:
          this.handleUpdateAvailable();
          break;
      }
    });
  }

  private handleUpdateError(event: any): void {
    console.error('Update error:', event);
    this.failedAttempts++;
    
    this.notifyProgress({ 
      stage: 'error', 
      progress: 0, 
      error: new Error(event.message || 'Update failed') 
    });
    
    CrashReportingService.recordError(new Error(event.message), {
      service: 'update_notifications',
      action: 'update_error',
      event_type: event.type
    });
  }

  private handleNoUpdateAvailable(): void {
    this.notifyProgress({ stage: 'complete', progress: 100 });
  }

  private handleUpdateAvailable(): void {
    console.log('Update available event received');
  }

  private notifyProgress(progress: UpdateProgress): void {
    this.updateProgressCallbacks.forEach(callback => {
      try {
        callback(progress);
      } catch (error) {
        console.error('Error in update progress callback:', error);
      }
    });
  }

  private startUpdateChecking(): void {
    if (this.config.checkFrequency === 'startup') {
      // Check on startup
      setTimeout(() => this.checkForUpdates(), 5000); // Delay to let app initialize
    } else if (this.config.checkFrequency === 'interval' && this.config.checkIntervalMinutes) {
      // Set up interval checking
      this.checkInterval = setInterval(() => {
        this.checkForUpdates();
      }, this.config.checkIntervalMinutes * 60 * 1000);
    }
    // 'foreground' and 'manual' don't need automatic setup
  }

  private stopUpdateChecking(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }

  private async loadUpdateState(): Promise<void> {
    try {
      const stored = await AsyncStorage.getItem('update_notification_state');
      if (stored) {
        const state = JSON.parse(stored);
        if (state.currentUpdateInfo) {
          this.currentUpdateInfo = {
            ...state.currentUpdateInfo,
            releaseDate: state.currentUpdateInfo.releaseDate ? new Date(state.currentUpdateInfo.releaseDate) : undefined
          };
        }
        this.lastCheckTime = state.lastCheckTime ? new Date(state.lastCheckTime) : null;
        this.failedAttempts = state.failedAttempts || 0;
      }
    } catch (error) {
      console.error('Error loading update state:', error);
    }
  }

  private async saveUpdateState(): Promise<void> {
    try {
      const state = {
        currentUpdateInfo: this.currentUpdateInfo,
        lastCheckTime: this.lastCheckTime,
        failedAttempts: this.failedAttempts
      };
      await AsyncStorage.setItem('update_notification_state', JSON.stringify(state));
    } catch (error) {
      console.error('Error saving update state:', error);
    }
  }

  private async clearUpdateState(): Promise<void> {
    try {
      await AsyncStorage.removeItem('update_notification_state');
      this.currentUpdateInfo = null;
      this.failedAttempts = 0;
    } catch (error) {
      console.error('Error clearing update state:', error);
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

  public async getDebugInfo(): Promise<any> {
    return {
      isInitialized: this.isInitialized,
      config: this.config,
      currentUpdateInfo: this.currentUpdateInfo,
      lastCheckTime: this.lastCheckTime,
      failedAttempts: this.failedAttempts,
      updatesEnabled: Updates.isEnabled,
      updateId: await Updates.readUpdateInfoAsync(),
      isEmbedded: Updates.isEmbeddedLaunch
    };
  }
}

export const UpdateNotificationService = new UpdateNotificationServiceClass();