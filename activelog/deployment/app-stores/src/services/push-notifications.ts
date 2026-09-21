import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface NotificationConfig {
  sound?: boolean | string;
  badge?: boolean;
  priority?: 'min' | 'low' | 'default' | 'high' | 'max';
  vibrate?: boolean | number[];
  color?: string;
  categoryId?: string;
  data?: Record<string, any>;
}

export interface ScheduledNotification {
  id: string;
  title: string;
  body: string;
  trigger: Date | number;
  config?: NotificationConfig;
  repeats?: boolean;
}

export interface NotificationCategory {
  identifier: string;
  actions: NotificationAction[];
  options?: {
    hiddenPreviewsBodyPlaceholder?: string;
    customDismissAction?: boolean;
    allowInCarPlay?: boolean;
    showTitle?: boolean;
    showSubtitle?: boolean;
  };
}

export interface NotificationAction {
  identifier: string;
  buttonTitle: string;
  options?: {
    isDestructive?: boolean;
    isAuthenticationRequired?: boolean;
    opensAppToForeground?: boolean;
  };
}

export interface PushToken {
  data: string;
  type: 'ios' | 'android';
  projectId?: string;
}

export interface NotificationPermissions {
  status: 'granted' | 'denied' | 'undetermined';
  canAskAgain: boolean;
  granted: boolean;
  ios?: {
    allowsAlert: boolean;
    allowsBadge: boolean;
    allowsSound: boolean;
    allowsCriticalAlerts: boolean;
    allowsAnnouncements: boolean;
    allowsDisplayInNotificationCenter: boolean;
    allowsDisplayInCarPlay: boolean;
    allowsDisplayOnLockScreen: boolean;
  };
  android?: {
    importance: number;
    interruptionFilter: number;
  };
}

class PushNotificationServiceClass {
  private isInitialized = false;
  private pushToken: PushToken | null = null;
  private notificationListener: any = null;
  private responseListener: any = null;
  private categories: NotificationCategory[] = [];
  private scheduledNotifications: Map<string, string> = new Map(); // id -> expo notification id

  public async initialize(): Promise<void> {
    try {
      // Set notification handler
      Notifications.setNotificationHandler({
        handleNotification: async (notification) => {
          const shouldShow = await this.shouldShowNotification(notification);
          const shouldPlaySound = await this.shouldPlaySound(notification);
          const shouldSetBadge = await this.shouldSetBadge(notification);

          return {
            shouldShowAlert: shouldShow,
            shouldPlaySound: shouldPlaySound,
            shouldSetBadge: shouldSetBadge,
          };
        },
        handleSuccess: (notificationId) => {
          console.log('📱 Notification handled successfully:', notificationId);
        },
        handleError: (error) => {
          console.error('📱 Notification handling error:', error);
        },
      });

      // Register for push notifications
      await this.registerForPushNotifications();

      // Set up notification categories
      await this.setupNotificationCategories();

      // Set up listeners
      this.setupNotificationListeners();

      // Restore scheduled notifications
      await this.restoreScheduledNotifications();

      this.isInitialized = true;
      console.log('📱 Push notification service initialized');
    } catch (error) {
      console.error('Failed to initialize push notifications:', error);
    }
  }

  public async registerForPushNotifications(): Promise<PushToken | null> {
    try {
      if (!Device.isDevice) {
        console.warn('Push notifications require a physical device');
        return null;
      }

      // Check existing permissions
      const { status: existingStatus } = await Notifications.getPermissionsAsync();
      let finalStatus = existingStatus;

      // Request permissions if not already granted
      if (existingStatus !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync({
          ios: {
            allowAlert: true,
            allowBadge: true,
            allowSound: true,
            allowAnnouncements: true,
            allowCriticalAlerts: false,
          },
          android: {
            allowAlert: true,
            allowBadge: true,
            allowSound: true,
          },
        });
        finalStatus = status;
      }

      if (finalStatus !== 'granted') {
        console.warn('Push notification permissions not granted');
        return null;
      }

      // Get push token
      const tokenData = await Notifications.getExpoPushTokenAsync({
        projectId: Constants.expoConfig?.extra?.eas?.projectId,
      });

      this.pushToken = {
        data: tokenData.data,
        type: Platform.OS as 'ios' | 'android',
        projectId: Constants.expoConfig?.extra?.eas?.projectId,
      };

      // Store token locally
      await AsyncStorage.setItem('push_token', JSON.stringify(this.pushToken));

      console.log('📱 Push token obtained:', this.pushToken.data);
      return this.pushToken;
    } catch (error) {
      console.error('Failed to register for push notifications:', error);
      return null;
    }
  }

  public async getPermissions(): Promise<NotificationPermissions> {
    try {
      const permissions = await Notifications.getPermissionsAsync();
      
      return {
        status: permissions.status,
        canAskAgain: permissions.canAskAgain,
        granted: permissions.granted,
        ios: permissions.ios,
        android: permissions.android,
      };
    } catch (error) {
      console.error('Failed to get notification permissions:', error);
      return {
        status: 'undetermined',
        canAskAgain: true,
        granted: false,
      };
    }
  }

  public async requestPermissions(): Promise<NotificationPermissions> {
    try {
      const permissions = await Notifications.requestPermissionsAsync({
        ios: {
          allowAlert: true,
          allowBadge: true,
          allowSound: true,
          allowAnnouncements: true,
          allowCriticalAlerts: false,
          allowDisplayInNotificationCenter: true,
          allowDisplayOnLockScreen: true,
          allowDisplayInCarPlay: false,
        },
        android: {
          allowAlert: true,
          allowBadge: true,
          allowSound: true,
        },
      });

      return {
        status: permissions.status,
        canAskAgain: permissions.canAskAgain,
        granted: permissions.granted,
        ios: permissions.ios,
        android: permissions.android,
      };
    } catch (error) {
      console.error('Failed to request notification permissions:', error);
      return {
        status: 'denied',
        canAskAgain: false,
        granted: false,
      };
    }
  }

  public async scheduleNotification(notification: ScheduledNotification): Promise<string | null> {
    if (!this.isInitialized) {
      console.warn('Push notification service not initialized');
      return null;
    }

    try {
      let trigger: any;

      if (notification.trigger instanceof Date) {
        trigger = notification.trigger;
      } else if (typeof notification.trigger === 'number') {
        trigger = { seconds: notification.trigger };
      }

      if (notification.repeats) {
        trigger = {
          ...trigger,
          repeats: true,
        };
      }

      const notificationId = await Notifications.scheduleNotificationAsync({
        content: {
          title: notification.title,
          body: notification.body,
          sound: notification.config?.sound ?? true,
          priority: this.mapPriority(notification.config?.priority),
          vibrate: notification.config?.vibrate,
          color: notification.config?.color,
          categoryIdentifier: notification.config?.categoryId,
          data: {
            ...notification.config?.data,
            notificationId: notification.id,
          },
          badge: notification.config?.badge ? 1 : undefined,
        },
        trigger,
      });

      // Store the mapping
      this.scheduledNotifications.set(notification.id, notificationId);
      await this.saveScheduledNotifications();

      console.log('📅 Notification scheduled:', notification.id);
      return notificationId;
    } catch (error) {
      console.error('Failed to schedule notification:', error);
      return null;
    }
  }

  public async cancelScheduledNotification(notificationId: string): Promise<boolean> {
    try {
      const expoNotificationId = this.scheduledNotifications.get(notificationId);
      
      if (expoNotificationId) {
        await Notifications.cancelScheduledNotificationAsync(expoNotificationId);
        this.scheduledNotifications.delete(notificationId);
        await this.saveScheduledNotifications();
        
        console.log('❌ Notification cancelled:', notificationId);
        return true;
      }

      return false;
    } catch (error) {
      console.error('Failed to cancel notification:', error);
      return false;
    }
  }

  public async cancelAllScheduledNotifications(): Promise<void> {
    try {
      await Notifications.cancelAllScheduledNotificationsAsync();
      this.scheduledNotifications.clear();
      await this.saveScheduledNotifications();
      
      console.log('❌ All notifications cancelled');
    } catch (error) {
      console.error('Failed to cancel all notifications:', error);
    }
  }

  public async getScheduledNotifications(): Promise<Notifications.NotificationRequest[]> {
    try {
      return await Notifications.getAllScheduledNotificationsAsync();
    } catch (error) {
      console.error('Failed to get scheduled notifications:', error);
      return [];
    }
  }

  public async presentNotification(title: string, body: string, config?: NotificationConfig): Promise<string | null> {
    if (!this.isInitialized) {
      console.warn('Push notification service not initialized');
      return null;
    }

    try {
      const notificationId = await Notifications.scheduleNotificationAsync({
        content: {
          title,
          body,
          sound: config?.sound ?? true,
          priority: this.mapPriority(config?.priority),
          vibrate: config?.vibrate,
          color: config?.color,
          categoryIdentifier: config?.categoryId,
          data: config?.data,
          badge: config?.badge ? 1 : undefined,
        },
        trigger: null, // Present immediately
      });

      console.log('📱 Notification presented:', notificationId);
      return notificationId;
    } catch (error) {
      console.error('Failed to present notification:', error);
      return null;
    }
  }

  public async setBadgeCount(count: number): Promise<boolean> {
    try {
      await Notifications.setBadgeCountAsync(count);
      console.log('🔢 Badge count set:', count);
      return true;
    } catch (error) {
      console.error('Failed to set badge count:', error);
      return false;
    }
  }

  public async getBadgeCount(): Promise<number> {
    try {
      return await Notifications.getBadgeCountAsync();
    } catch (error) {
      console.error('Failed to get badge count:', error);
      return 0;
    }
  }

  public async clearBadge(): Promise<boolean> {
    return await this.setBadgeCount(0);
  }

  public addNotificationReceivedListener(listener: (notification: Notifications.Notification) => void): Notifications.Subscription {
    return Notifications.addNotificationReceivedListener(listener);
  }

  public addNotificationResponseReceivedListener(listener: (response: Notifications.NotificationResponse) => void): Notifications.Subscription {
    return Notifications.addNotificationResponseReceivedListener(listener);
  }

  public getPushToken(): PushToken | null {
    return this.pushToken;
  }

  public async refreshPushToken(): Promise<PushToken | null> {
    try {
      const tokenData = await Notifications.getExpoPushTokenAsync({
        projectId: Constants.expoConfig?.extra?.eas?.projectId,
      });

      this.pushToken = {
        data: tokenData.data,
        type: Platform.OS as 'ios' | 'android',
        projectId: Constants.expoConfig?.extra?.eas?.projectId,
      };

      await AsyncStorage.setItem('push_token', JSON.stringify(this.pushToken));
      
      console.log('🔄 Push token refreshed');
      return this.pushToken;
    } catch (error) {
      console.error('Failed to refresh push token:', error);
      return null;
    }
  }

  public async registerNotificationCategories(categories: NotificationCategory[]): Promise<void> {
    try {
      this.categories = categories;

      if (Platform.OS === 'ios') {
        await Notifications.setNotificationCategoryAsync(
          ...categories.map(category => ({
            identifier: category.identifier,
            actions: category.actions.map(action => ({
              identifier: action.identifier,
              buttonTitle: action.buttonTitle,
              options: action.options,
            })),
            options: category.options,
          }))
        );
      }

      console.log('📋 Notification categories registered:', categories.length);
    } catch (error) {
      console.error('Failed to register notification categories:', error);
    }
  }

  // Utility methods for common notification scenarios
  public async scheduleReminderNotification(
    title: string,
    body: string,
    triggerDate: Date,
    data?: Record<string, any>
  ): Promise<string | null> {
    return this.scheduleNotification({
      id: `reminder_${Date.now()}`,
      title,
      body,
      trigger: triggerDate,
      config: {
        sound: true,
        badge: true,
        priority: 'default',
        categoryId: 'reminder',
        data,
      },
    });
  }

  public async scheduleRepeatingNotification(
    title: string,
    body: string,
    intervalSeconds: number,
    data?: Record<string, any>
  ): Promise<string | null> {
    return this.scheduleNotification({
      id: `repeating_${Date.now()}`,
      title,
      body,
      trigger: intervalSeconds,
      repeats: true,
      config: {
        sound: true,
        badge: false,
        priority: 'low',
        data,
      },
    });
  }

  public async sendSilentNotification(data: Record<string, any>): Promise<string | null> {
    return this.presentNotification('', '', {
      sound: false,
      badge: false,
      priority: 'min',
      data,
    });
  }

  private async setupNotificationCategories(): Promise<void> {
    const defaultCategories: NotificationCategory[] = [
      {
        identifier: 'reminder',
        actions: [
          {
            identifier: 'mark_done',
            buttonTitle: 'Mark Done',
            options: { opensAppToForeground: false },
          },
          {
            identifier: 'snooze',
            buttonTitle: 'Snooze',
            options: { opensAppToForeground: false },
          },
        ],
      },
      {
        identifier: 'message',
        actions: [
          {
            identifier: 'reply',
            buttonTitle: 'Reply',
            options: { opensAppToForeground: true },
          },
          {
            identifier: 'view',
            buttonTitle: 'View',
            options: { opensAppToForeground: true },
          },
        ],
      },
      {
        identifier: 'update',
        actions: [
          {
            identifier: 'update_now',
            buttonTitle: 'Update Now',
            options: { opensAppToForeground: true },
          },
          {
            identifier: 'later',
            buttonTitle: 'Later',
            options: { opensAppToForeground: false },
          },
        ],
      },
    ];

    await this.registerNotificationCategories(defaultCategories);
  }

  private setupNotificationListeners(): void {
    // Notification received listener
    this.notificationListener = Notifications.addNotificationReceivedListener(
      this.handleNotificationReceived.bind(this)
    );

    // Notification response listener
    this.responseListener = Notifications.addNotificationResponseReceivedListener(
      this.handleNotificationResponse.bind(this)
    );
  }

  private async handleNotificationReceived(notification: Notifications.Notification): Promise<void> {
    console.log('📨 Notification received:', notification);
    
    // Track notification received
    if (this.isInitialized) {
      // You might want to integrate with analytics here
      console.log('Tracking notification received');
    }
  }

  private async handleNotificationResponse(response: Notifications.NotificationResponse): Promise<void> {
    console.log('👆 Notification response:', response);

    const { actionIdentifier, userText } = response;
    const { data } = response.notification.request.content;

    // Handle different action types
    switch (actionIdentifier) {
      case 'mark_done':
        await this.handleMarkDoneAction(data);
        break;
      case 'snooze':
        await this.handleSnoozeAction(data);
        break;
      case 'reply':
        await this.handleReplyAction(data, userText);
        break;
      case 'update_now':
        await this.handleUpdateAction(data);
        break;
      default:
        // Default tap action - open app
        console.log('Opening app from notification');
        break;
    }
  }

  private async handleMarkDoneAction(data: any): Promise<void> {
    console.log('✅ Mark done action:', data);
    // Implement mark done logic
  }

  private async handleSnoozeAction(data: any): Promise<void> {
    console.log('😴 Snooze action:', data);
    // Implement snooze logic - reschedule for later
  }

  private async handleReplyAction(data: any, userText?: string): Promise<void> {
    console.log('💬 Reply action:', data, userText);
    // Implement reply logic
  }

  private async handleUpdateAction(data: any): Promise<void> {
    console.log('🔄 Update action:', data);
    // Implement update logic
  }

  private async shouldShowNotification(notification: Notifications.Notification): Promise<boolean> {
    // Custom logic to determine if notification should be shown
    // For example, don't show if app is in foreground for certain types
    const { data } = notification.request.content;
    
    if (data?.silent === true) {
      return false;
    }

    return true;
  }

  private async shouldPlaySound(notification: Notifications.Notification): Promise<boolean> {
    // Custom logic for sound
    const { data } = notification.request.content;
    return data?.silent !== true;
  }

  private async shouldSetBadge(notification: Notifications.Notification): Promise<boolean> {
    // Custom logic for badge
    const { data } = notification.request.content;
    return data?.updateBadge !== false;
  }

  private mapPriority(priority?: string): Notifications.AndroidNotificationPriority {
    switch (priority) {
      case 'min':
        return Notifications.AndroidNotificationPriority.MIN;
      case 'low':
        return Notifications.AndroidNotificationPriority.LOW;
      case 'high':
        return Notifications.AndroidNotificationPriority.HIGH;
      case 'max':
        return Notifications.AndroidNotificationPriority.MAX;
      default:
        return Notifications.AndroidNotificationPriority.DEFAULT;
    }
  }

  private async saveScheduledNotifications(): Promise<void> {
    try {
      const data = JSON.stringify(Array.from(this.scheduledNotifications.entries()));
      await AsyncStorage.setItem('scheduled_notifications', data);
    } catch (error) {
      console.error('Failed to save scheduled notifications:', error);
    }
  }

  private async restoreScheduledNotifications(): Promise<void> {
    try {
      const data = await AsyncStorage.getItem('scheduled_notifications');
      if (data) {
        const entries = JSON.parse(data);
        this.scheduledNotifications = new Map(entries);
      }
    } catch (error) {
      console.error('Failed to restore scheduled notifications:', error);
    }
  }

  public cleanup(): void {
    if (this.notificationListener) {
      Notifications.removeNotificationSubscription(this.notificationListener);
    }
    if (this.responseListener) {
      Notifications.removeNotificationSubscription(this.responseListener);
    }
  }
}

export const PushNotificationService = new PushNotificationServiceClass();