import * as admin from 'firebase-admin';
import * as apn from 'apn';
import { EventEmitter } from 'events';
import Redis from 'ioredis';
import { PushNotification, PushPlatform, PushStatus, DeviceRegistration, PushCampaign, CampaignStatus } from '@/types/push';
import { Logger } from '@/utils/logger';

export interface PushConfig {
  fcm: {
    serviceAccountPath: string;
    projectId: string;
  };
  apns: {
    keyPath: string;
    keyId: string;
    teamId: string;
    production: boolean;
  };
  redis: {
    host: string;
    port: number;
    password?: string;
  };
}

export class PushNotificationService extends EventEmitter {
  private fcmApp: admin.app.App | null = null;
  private apnProvider: apn.Provider | null = null;
  private redis: Redis;
  private logger: Logger;
  private config: PushConfig;
  private isInitialized = false;

  constructor(config: PushConfig) {
    super();
    this.config = config;
    this.logger = new Logger('PushNotificationService');
    this.redis = new Redis({
      host: config.redis.host,
      port: config.redis.port,
      password: config.redis.password,
      retryDelayOnFailover: 100,
      enableReadyCheck: false,
      maxRetriesPerRequest: null
    });
  }

  async initialize(): Promise<void> {
    try {
      // Initialize FCM
      await this.initializeFCM();
      
      // Initialize APNS
      await this.initializeAPNS();
      
      this.isInitialized = true;
      this.logger.info('Push notification service initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize push notification service', error);
      throw error;
    }
  }

  private async initializeFCM(): Promise<void> {
    try {
      const serviceAccount = require(this.config.fcm.serviceAccountPath);
      
      this.fcmApp = admin.initializeApp({
        credential: admin.credential.cert(serviceAccount),
        projectId: this.config.fcm.projectId
      }, 'mobile-push');
      
      this.logger.info('FCM initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize FCM', error);
      throw error;
    }
  }

  private async initializeAPNS(): Promise<void> {
    try {
      this.apnProvider = new apn.Provider({
        token: {
          key: this.config.apns.keyPath,
          keyId: this.config.apns.keyId,
          teamId: this.config.apns.teamId
        },
        production: this.config.apns.production
      });
      
      this.logger.info('APNS initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize APNS', error);
      throw error;
    }
  }

  async sendNotification(notification: PushNotification): Promise<boolean> {
    if (!this.isInitialized) {
      throw new Error('Push notification service not initialized');
    }

    try {
      let success = false;
      
      switch (notification.platform) {
        case PushPlatform.ANDROID:
          success = await this.sendFCMNotification(notification);
          break;
        case PushPlatform.IOS:
          success = await this.sendAPNSNotification(notification);
          break;
        case PushPlatform.WEB:
          success = await this.sendWebPushNotification(notification);
          break;
        default:
          throw new Error(`Unsupported platform: ${notification.platform}`);
      }

      // Update notification status
      await this.updateNotificationStatus(notification.id, success ? PushStatus.SENT : PushStatus.FAILED);
      
      // Emit event
      this.emit('notification_sent', { notification, success });
      
      return success;
    } catch (error) {
      this.logger.error(`Failed to send notification ${notification.id}`, error);
      await this.updateNotificationStatus(notification.id, PushStatus.FAILED, error.message);
      return false;
    }
  }

  private async sendFCMNotification(notification: PushNotification): Promise<boolean> {
    if (!this.fcmApp) {
      throw new Error('FCM not initialized');
    }

    const messaging = admin.messaging(this.fcmApp);
    
    const message: admin.messaging.Message = {
      token: notification.deviceToken,
      notification: {
        title: notification.payload.title,
        body: notification.payload.body,
        imageUrl: notification.payload.image
      },
      data: notification.payload.data || {},
      android: {
        priority: notification.payload.android?.priority === 1 ? 'high' : 'normal',
        ttl: notification.payload.android?.ttl ? notification.payload.android.ttl * 1000 : 3600000,
        notification: {
          icon: notification.payload.android?.notification?.icon,
          color: notification.payload.android?.notification?.color,
          sound: notification.payload.android?.notification?.sound,
          tag: notification.payload.android?.notification?.tag,
          clickAction: notification.payload.android?.notification?.clickAction,
          channelId: notification.payload.android?.notification?.channelId
        }
      },
      webpush: notification.platform === PushPlatform.WEB ? {
        notification: {
          title: notification.payload.title,
          body: notification.payload.body,
          icon: notification.payload.web?.icon,
          image: notification.payload.web?.image,
          badge: notification.payload.web?.badge,
          actions: notification.payload.web?.actions?.map(action => ({
            action: action.action,
            title: action.title,
            icon: action.icon
          })),
          requireInteraction: notification.payload.web?.requireInteraction,
          silent: notification.payload.web?.silent,
          timestamp: notification.payload.web?.timestamp,
          vibrate: notification.payload.web?.vibrate
        }
      } : undefined
    };

    try {
      const response = await messaging.send(message);
      this.logger.info(`FCM notification sent successfully: ${response}`);
      return true;
    } catch (error) {
      this.logger.error('FCM send failed', error);
      
      // Handle invalid token
      if (error.code === 'messaging/invalid-registration-token' ||
          error.code === 'messaging/registration-token-not-registered') {
        await this.markDeviceTokenInvalid(notification.deviceToken);
      }
      
      return false;
    }
  }

  private async sendAPNSNotification(notification: PushNotification): Promise<boolean> {
    if (!this.apnProvider) {
      throw new Error('APNS not initialized');
    }

    const apnNotification = new apn.Notification();
    
    // Set basic properties
    apnNotification.topic = process.env.APNS_BUNDLE_ID || 'com.activelog.mobile';
    apnNotification.badge = notification.payload.badge || 1;
    apnNotification.sound = notification.payload.ios?.sound || 'default';
    apnNotification.contentAvailable = notification.payload.ios?.contentAvailable || false;
    apnNotification.mutableContent = notification.payload.ios?.mutableContent || false;
    apnNotification.category = notification.payload.ios?.category;
    apnNotification.threadId = notification.payload.ios?.threadId;
    
    // Set alert
    if (notification.payload.ios?.alert) {
      apnNotification.alert = {
        title: notification.payload.ios.alert.title,
        subtitle: notification.payload.ios.alert.subtitle,
        body: notification.payload.ios.alert.body,
        'launch-image': notification.payload.ios.alert.launchImage,
        'title-loc-key': notification.payload.ios.alert.titleLocKey,
        'title-loc-args': notification.payload.ios.alert.titleLocArgs,
        'subtitle-loc-key': notification.payload.ios.alert.subtitleLocKey,
        'subtitle-loc-args': notification.payload.ios.alert.subtitleLocArgs,
        'loc-key': notification.payload.ios.alert.locKey,
        'loc-args': notification.payload.ios.alert.locArgs
      };
    } else {
      apnNotification.alert = {
        title: notification.payload.title,
        body: notification.payload.body
      };
    }
    
    // Set custom payload
    apnNotification.payload = notification.payload.data || {};
    
    // Set priority
    if (notification.payload.ios?.priority === 1) {
      apnNotification.priority = 10; // Send immediately
    } else {
      apnNotification.priority = 5; // Conserve power
    }
    
    try {
      const result = await this.apnProvider.send(apnNotification, notification.deviceToken);
      
      if (result.successful && result.successful.length > 0) {
        this.logger.info(`APNS notification sent successfully: ${result.successful[0].device}`);
        return true;
      } else if (result.failed && result.failed.length > 0) {
        const failure = result.failed[0];
        this.logger.error(`APNS notification failed: ${failure.error}`, failure);
        
        // Handle invalid token
        if (failure.status === '410' || failure.error === 'BadDeviceToken') {
          await this.markDeviceTokenInvalid(notification.deviceToken);
        }
        
        return false;
      }
      
      return false;
    } catch (error) {
      this.logger.error('APNS send failed', error);
      return false;
    }
  }

  private async sendWebPushNotification(notification: PushNotification): Promise<boolean> {
    // Web push would be handled by FCM for web clients
    return this.sendFCMNotification(notification);
  }

  async sendBulkNotifications(notifications: PushNotification[]): Promise<{ successful: number; failed: number }> {
    const batchSize = 500;
    let successful = 0;
    let failed = 0;

    for (let i = 0; i < notifications.length; i += batchSize) {
      const batch = notifications.slice(i, i + batchSize);
      const promises = batch.map(notification => this.sendNotification(notification));
      
      const results = await Promise.allSettled(promises);
      
      results.forEach(result => {
        if (result.status === 'fulfilled' && result.value) {
          successful++;
        } else {
          failed++;
        }
      });
      
      // Add delay between batches to avoid rate limiting
      if (i + batchSize < notifications.length) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }

    this.logger.info(`Bulk notification results: ${successful} successful, ${failed} failed`);
    return { successful, failed };
  }

  async registerDevice(registration: DeviceRegistration): Promise<void> {
    const key = `device:${registration.userId}:${registration.deviceToken}`;
    
    await this.redis.hset(key, {
      userId: registration.userId,
      platform: registration.platform.toString(),
      appVersion: registration.appVersion || '',
      osVersion: registration.osVersion || '',
      deviceModel: registration.deviceModel || '',
      deviceName: registration.deviceName || '',
      notificationsEnabled: registration.notificationsEnabled ? '1' : '0',
      subscribedTopics: JSON.stringify(registration.subscribedTopics || []),
      metadata: JSON.stringify(registration.metadata || {}),
      registeredAt: registration.registeredAt?.toISOString() || new Date().toISOString(),
      lastActiveAt: registration.lastActiveAt?.toISOString() || new Date().toISOString()
    });

    // Add to user's device list
    await this.redis.sadd(`user_devices:${registration.userId}`, registration.deviceToken);
    
    this.logger.info(`Device registered: ${registration.deviceToken} for user ${registration.userId}`);
  }

  async unregisterDevice(userId: string, deviceToken: string): Promise<void> {
    const key = `device:${userId}:${deviceToken}`;
    
    await this.redis.del(key);
    await this.redis.srem(`user_devices:${userId}`, deviceToken);
    
    this.logger.info(`Device unregistered: ${deviceToken} for user ${userId}`);
  }

  async getUserDevices(userId: string): Promise<DeviceRegistration[]> {
    const deviceTokens = await this.redis.smembers(`user_devices:${userId}`);
    const devices: DeviceRegistration[] = [];
    
    for (const token of deviceTokens) {
      const deviceData = await this.redis.hgetall(`device:${userId}:${token}`);
      
      if (deviceData && Object.keys(deviceData).length > 0) {
        devices.push({
          userId: deviceData.userId,
          deviceToken: token,
          platform: parseInt(deviceData.platform) as PushPlatform,
          appVersion: deviceData.appVersion,
          osVersion: deviceData.osVersion,
          deviceModel: deviceData.deviceModel,
          deviceName: deviceData.deviceName,
          notificationsEnabled: deviceData.notificationsEnabled === '1',
          subscribedTopics: JSON.parse(deviceData.subscribedTopics || '[]'),
          metadata: JSON.parse(deviceData.metadata || '{}'),
          registeredAt: new Date(deviceData.registeredAt),
          lastActiveAt: new Date(deviceData.lastActiveAt)
        });
      }
    }
    
    return devices;
  }

  async sendToUser(userId: string, notification: Omit<PushNotification, 'deviceToken' | 'userId'>): Promise<void> {
    const devices = await this.getUserDevices(userId);
    
    if (devices.length === 0) {
      this.logger.warn(`No devices found for user ${userId}`);
      return;
    }

    const notifications = devices
      .filter(device => device.notificationsEnabled)
      .map(device => ({
        ...notification,
        userId,
        deviceToken: device.deviceToken,
        platform: device.platform
      } as PushNotification));

    await this.sendBulkNotifications(notifications);
  }

  async sendCampaign(campaign: PushCampaign): Promise<void> {
    try {
      // Update campaign status
      campaign.status = CampaignStatus.SENDING;
      await this.updateCampaignStatus(campaign.id, CampaignStatus.SENDING);

      // Get target devices based on targeting options
      const targetDevices = await this.getTargetDevices(campaign.targeting);
      
      if (targetDevices.length === 0) {
        this.logger.warn(`No target devices found for campaign ${campaign.id}`);
        await this.updateCampaignStatus(campaign.id, CampaignStatus.COMPLETED);
        return;
      }

      // Create notifications for all target devices
      const notifications = targetDevices.map(device => ({
        id: `${campaign.id}_${device.deviceToken}`,
        userId: device.userId,
        deviceToken: device.deviceToken,
        platform: device.platform,
        payload: campaign.payload,
        options: campaign.options,
        status: PushStatus.PENDING,
        createdAt: new Date(),
        sentAt: null,
        deliveredAt: null,
        errorMessage: null,
        retryCount: 0
      } as PushNotification));

      // Send notifications
      const results = await this.sendBulkNotifications(notifications);
      
      // Update campaign statistics
      campaign.stats = {
        targetCount: targetDevices.length,
        sentCount: results.successful,
        deliveredCount: 0, // Will be updated by delivery receipts
        openedCount: 0,
        clickedCount: 0,
        failedCount: results.failed,
        deliveryRate: results.successful / targetDevices.length,
        openRate: 0,
        clickRate: 0
      };

      await this.updateCampaignStatus(campaign.id, CampaignStatus.SENT_CAMPAIGN);
      
      this.logger.info(`Campaign ${campaign.id} completed: ${results.successful}/${targetDevices.length} sent successfully`);
    } catch (error) {
      this.logger.error(`Campaign ${campaign.id} failed`, error);
      await this.updateCampaignStatus(campaign.id, CampaignStatus.CANCELLED_CAMPAIGN);
      throw error;
    }
  }

  private async getTargetDevices(targeting: any): Promise<DeviceRegistration[]> {
    // This would implement the targeting logic based on the targeting options
    // For now, return all devices for specified user IDs
    const devices: DeviceRegistration[] = [];
    
    if (targeting.userIds && targeting.userIds.length > 0) {
      for (const userId of targeting.userIds) {
        const userDevices = await this.getUserDevices(userId);
        devices.push(...userDevices);
      }
    }
    
    return devices;
  }

  private async updateNotificationStatus(notificationId: string, status: PushStatus, errorMessage?: string): Promise<void> {
    const key = `notification:${notificationId}`;
    const updates: any = { status: status.toString() };
    
    if (errorMessage) {
      updates.errorMessage = errorMessage;
    }
    
    if (status === PushStatus.SENT) {
      updates.sentAt = new Date().toISOString();
    }
    
    await this.redis.hset(key, updates);
  }

  private async updateCampaignStatus(campaignId: string, status: CampaignStatus): Promise<void> {
    const key = `campaign:${campaignId}`;
    await this.redis.hset(key, 'status', status.toString());
  }

  private async markDeviceTokenInvalid(deviceToken: string): Promise<void> {
    // Find and remove invalid device tokens
    const pattern = `device:*:${deviceToken}`;
    const keys = await this.redis.keys(pattern);
    
    for (const key of keys) {
      const userId = key.split(':')[1];
      await this.unregisterDevice(userId, deviceToken);
    }
    
    this.logger.info(`Marked device token as invalid and removed: ${deviceToken}`);
  }

  async getNotificationAnalytics(timeframe: { start: Date; end: Date }): Promise<any> {
    // Implementation would query analytics data
    return {
      totalSent: 0,
      totalDelivered: 0,
      totalOpened: 0,
      totalClicked: 0,
      deliveryRate: 0,
      openRate: 0,
      clickRate: 0
    };
  }

  async cleanup(): Promise<void> {
    if (this.apnProvider) {
      this.apnProvider.shutdown();
    }
    
    await this.redis.quit();
    this.logger.info('Push notification service cleanup completed');
  }
}