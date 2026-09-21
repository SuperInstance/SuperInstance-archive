import { Request, Response } from 'express';
import { Logger } from '@/utils/logger';
import { AppConfigService, AppConfigOptions } from '@/services/AppConfigService';

const logger = new Logger('ConfigController');

interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    role: string;
  };
}

export const configController = {
  async getAppConfig(req: Request, res: Response) {
    const startTime = Date.now();
    
    try {
      const appConfigService = req.app.locals.services.appConfigService as AppConfigService;
      
      // Extract client information from headers
      const platform = (req.headers['x-platform'] as string) || 'unknown';
      const appVersion = (req.headers['x-app-version'] as string) || '1.0.0';
      const osVersion = (req.headers['x-os-version'] as string) || 'unknown';
      const deviceType = (req.headers['x-device-type'] as string) || 'unknown';
      const userId = (req as AuthenticatedRequest).user?.id;
      const region = (req.headers['x-region'] as string) || req.headers['cf-ipcountry'] as string;
      const language = (req.headers['accept-language'] as string)?.split(',')[0];

      const options: AppConfigOptions = {
        platform: platform === 'ios' || platform === 'android' ? platform : 'android',
        appVersion,
        osVersion,
        deviceType,
        userId,
        region,
        language
      };

      const config = await appConfigService.getAppConfig(options);
      const responseTime = Date.now() - startTime;

      // Record analytics
      await appConfigService.recordConfigRequest(options, responseTime);

      // Set cache headers
      const cacheMaxAge = userId ? 300 : 600; // 5 min for users, 10 min for anonymous
      res.set({
        'Cache-Control': `public, max-age=${cacheMaxAge}`,
        'ETag': `"config-${config.version}-${config.updatedAt.getTime()}"`,
        'X-Response-Time': `${responseTime}ms`
      });

      // Check if client has latest version
      if (req.headers['if-none-match'] === `"config-${config.version}-${config.updatedAt.getTime()}"`) {
        return res.status(304).send();
      }

      // Convert Maps to objects for JSON serialization
      const serializedConfig = {
        ...config,
        features: {
          flags: Object.fromEntries(config.features.flags),
          experiments: config.features.experiments
        },
        endpoints: {
          ...config.endpoints,
          serviceUrls: Object.fromEntries(config.endpoints.serviceUrls)
        }
      };

      res.json(serializedConfig);

    } catch (error) {
      logger.error('Failed to get app config', error);
      res.status(500).json({ error: 'Failed to load configuration' });
    }
  },

  async updateFeatureFlag(req: AuthenticatedRequest, res: Response) {
    try {
      const appConfigService = req.app.locals.services.appConfigService as AppConfigService;
      const { flagName, enabled, scope } = req.body;

      if (!flagName || typeof enabled !== 'boolean') {
        return res.status(400).json({ error: 'Flag name and enabled status required' });
      }

      // Check if user has permission to update feature flags
      if (req.user?.role !== 'admin' && req.user?.role !== 'super_admin') {
        return res.status(403).json({ error: 'Insufficient permissions' });
      }

      await appConfigService.updateFeatureFlag(flagName, enabled, scope);

      logger.info(`Feature flag ${flagName} updated to ${enabled} by ${req.user?.id}`);

      res.json({
        success: true,
        message: `Feature flag ${flagName} updated successfully`
      });

    } catch (error) {
      logger.error('Failed to update feature flag', error);
      res.status(500).json({ error: 'Failed to update feature flag' });
    }
  },

  async getAnalytics(req: AuthenticatedRequest, res: Response) {
    try {
      const appConfigService = req.app.locals.services.appConfigService as AppConfigService;

      // Check if user has permission to view analytics
      if (req.user?.role !== 'admin' && req.user?.role !== 'super_admin') {
        return res.status(403).json({ error: 'Insufficient permissions' });
      }

      const analytics = await appConfigService.getConfigAnalytics();

      res.json(analytics);

    } catch (error) {
      logger.error('Failed to get config analytics', error);
      res.status(500).json({ error: 'Failed to get analytics' });
    }
  }
};