import { Request, Response } from 'express';
import { Logger } from '@/utils/logger';
import { PushNotificationService } from '@/services/PushNotificationService';
import { DeviceRegistration, PushNotification, PushCampaign } from '@/types/push';

const logger = new Logger('PushController');

interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    role: string;
  };
}

export const pushController = {
  async registerDevice(req: AuthenticatedRequest, res: Response) {
    try {
      const pushService = req.app.locals.services.pushService as PushNotificationService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      const registration: DeviceRegistration = {
        ...req.body,
        userId,
        registeredAt: new Date(),
        lastActiveAt: new Date()
      };

      if (!registration.deviceToken || !registration.platform) {
        return res.status(400).json({ error: 'Device token and platform required' });
      }

      await pushService.registerDevice(registration);

      logger.info(`Device registered for user ${userId}: ${registration.deviceToken}`);

      res.json({
        success: true,
        message: 'Device registered successfully'
      });

    } catch (error) {
      logger.error('Device registration failed', error);
      res.status(500).json({ error: 'Failed to register device' });
    }
  },

  async unregisterDevice(req: AuthenticatedRequest, res: Response) {
    try {
      const pushService = req.app.locals.services.pushService as PushNotificationService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      const { deviceToken } = req.body;

      if (!deviceToken) {
        return res.status(400).json({ error: 'Device token required' });
      }

      await pushService.unregisterDevice(userId, deviceToken);

      logger.info(`Device unregistered for user ${userId}: ${deviceToken}`);

      res.json({
        success: true,
        message: 'Device unregistered successfully'
      });

    } catch (error) {
      logger.error('Device unregistration failed', error);
      res.status(500).json({ error: 'Failed to unregister device' });
    }
  },

  async sendNotification(req: AuthenticatedRequest, res: Response) {
    try {
      const pushService = req.app.locals.services.pushService as PushNotificationService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      const { targetUserId, notification } = req.body;

      if (!targetUserId || !notification) {
        return res.status(400).json({ error: 'Target user ID and notification required' });
      }

      // Check if user has permission to send notifications
      if (req.user?.role !== 'admin' && req.user?.role !== 'super_admin' && userId !== targetUserId) {
        return res.status(403).json({ error: 'Insufficient permissions' });
      }

      await pushService.sendToUser(targetUserId, notification);

      res.json({
        success: true,
        message: 'Notification sent successfully'
      });

    } catch (error) {
      logger.error('Failed to send notification', error);
      res.status(500).json({ error: 'Failed to send notification' });
    }
  },

  async sendCampaign(req: AuthenticatedRequest, res: Response) {
    try {
      const pushService = req.app.locals.services.pushService as PushNotificationService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      // Check if user has permission to send campaigns
      if (req.user?.role !== 'admin' && req.user?.role !== 'super_admin') {
        return res.status(403).json({ error: 'Insufficient permissions' });
      }

      const campaign: PushCampaign = req.body;

      if (!campaign.name || !campaign.payload) {
        return res.status(400).json({ error: 'Campaign name and payload required' });
      }

      await pushService.sendCampaign(campaign);

      res.json({
        success: true,
        message: 'Campaign sent successfully'
      });

    } catch (error) {
      logger.error('Failed to send campaign', error);
      res.status(500).json({ error: 'Failed to send campaign' });
    }
  },

  async getAnalytics(req: AuthenticatedRequest, res: Response) {
    try {
      const pushService = req.app.locals.services.pushService as PushNotificationService;
      
      // Check if user has permission to view analytics
      if (req.user?.role !== 'admin' && req.user?.role !== 'super_admin') {
        return res.status(403).json({ error: 'Insufficient permissions' });
      }

      const { start, end } = req.query;
      
      const timeframe = {
        start: start ? new Date(start as string) : new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
        end: end ? new Date(end as string) : new Date()
      };

      const analytics = await pushService.getNotificationAnalytics(timeframe);

      res.json(analytics);

    } catch (error) {
      logger.error('Failed to get push analytics', error);
      res.status(500).json({ error: 'Failed to get analytics' });
    }
  }
};