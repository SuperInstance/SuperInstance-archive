import Redis from 'ioredis';
import { Logger } from '@/utils/logger';
import { AppConfig, FeatureFlags, ApiEndpoints, ImageOptimization, SyncConfiguration, SecuritySettings, ExperimentFlag } from '@/types/config';

export interface AppConfigOptions {
  platform: 'ios' | 'android';
  appVersion: string;
  osVersion: string;
  deviceType: string;
  userId?: string;
  region?: string;
  language?: string;
}

export class AppConfigService {
  private redis: Redis;
  private logger: Logger;
  private baseConfig: AppConfig;
  private configCache: Map<string, AppConfig> = new Map();
  private cacheExpiryTime = 5 * 60 * 1000; // 5 minutes

  constructor(redisConfig: { host: string; port: number; password?: string }) {
    this.logger = new Logger('AppConfigService');
    this.redis = new Redis({
      host: redisConfig.host,
      port: redisConfig.port,
      password: redisConfig.password,
      retryDelayOnFailover: 100,
      enableReadyCheck: false,
      maxRetriesPerRequest: null
    });

    this.initializeBaseConfig();
  }

  private initializeBaseConfig(): void {
    this.baseConfig = {
      version: '1.0.0',
      minVersionCode: 1,
      forceUpdate: false,
      updateUrl: '',
      features: this.getDefaultFeatureFlags(),
      endpoints: this.getDefaultEndpoints(),
      imageOptimization: this.getDefaultImageOptimization(),
      syncConfig: this.getDefaultSyncConfiguration(),
      security: this.getDefaultSecuritySettings(),
      updatedAt: new Date()
    };
  }

  private getDefaultFeatureFlags(): FeatureFlags {
    return {
      flags: new Map([
        ['push_notifications', true],
        ['offline_mode', true],
        ['image_compression', true],
        ['video_streaming', true],
        ['biometric_auth', true],
        ['dark_mode', true],
        ['analytics', true],
        ['crash_reporting', true],
        ['file_sharing', true],
        ['background_sync', true],
        ['battery_optimization', true],
        ['smart_sync', true],
        ['progressive_image_loading', true],
        ['adaptive_quality', true],
        ['collaborative_editing', false],
        ['ai_suggestions', false],
        ['advanced_search', true],
        ['cloud_backup', true],
        ['multi_account', false],
        ['premium_features', false]
      ]),
      experiments: [
        {
          name: 'new_ui_design',
          enabled: false,
          rolloutPercentage: 0.1,
          targetGroups: ['beta_testers']
        },
        {
          name: 'improved_compression',
          enabled: true,
          rolloutPercentage: 0.5,
          targetGroups: []
        },
        {
          name: 'ml_recommendations',
          enabled: false,
          rolloutPercentage: 0.05,
          targetGroups: ['premium_users']
        }
      ]
    };
  }

  private getDefaultEndpoints(): ApiEndpoints {
    const baseUrl = process.env.API_BASE_URL || 'https://api.activelog.com';
    
    return {
      baseUrl,
      graphqlUrl: `${baseUrl}/graphql`,
      uploadUrl: `${baseUrl}/upload`,
      cdnUrl: process.env.CDN_URL || 'https://cdn.activelog.com',
      wsUrl: process.env.WS_URL || 'wss://ws.activelog.com',
      serviceUrls: new Map([
        ['mobile-api', 'https://mobile-api.activelog.com'],
        ['file-service', 'https://files.activelog.com'],
        ['video-service', 'https://video.activelog.com'],
        ['analytics-service', 'https://analytics.activelog.com'],
        ['auth-service', 'https://auth.activelog.com']
      ])
    };
  }

  private getDefaultImageOptimization(): ImageOptimization {
    return {
      sizes: [
        { name: 'thumbnail', width: 150, height: 150, crop: true },
        { name: 'small', width: 320, height: 240, crop: false },
        { name: 'medium', width: 640, height: 480, crop: false },
        { name: 'large', width: 1024, height: 768, crop: false }
      ],
      formats: ['jpeg', 'webp'],
      quality: 85,
      progressive: true,
      webpEnabled: true
    };
  }

  private getDefaultSyncConfiguration(): SyncConfiguration {
    return {
      batchSize: 100,
      retryAttempts: 3,
      retryDelayMs: 1000,
      timeoutMs: 30000,
      compressionEnabled: true,
      maxQueueSize: 1000
    };
  }

  private getDefaultSecuritySettings(): SecuritySettings {
    return {
      certificatePinning: true,
      sessionTimeoutMinutes: 60,
      biometricAuth: true,
      maxLoginAttempts: 5,
      lockoutDurationMinutes: 15
    };
  }

  async getAppConfig(options: AppConfigOptions): Promise<AppConfig> {
    try {
      // Generate cache key
      const cacheKey = this.generateCacheKey(options);
      
      // Check cache first
      const cached = this.configCache.get(cacheKey);
      if (cached) {
        this.logger.info(`Returning cached config for ${options.platform} v${options.appVersion}`);
        return cached;
      }

      // Build customized config
      let config = { ...this.baseConfig };
      
      // Apply platform-specific configurations
      config = await this.applyPlatformConfig(config, options);
      
      // Apply version-specific configurations
      config = await this.applyVersionConfig(config, options);
      
      // Apply user-specific configurations
      if (options.userId) {
        config = await this.applyUserConfig(config, options);
      }
      
      // Apply regional configurations
      if (options.region) {
        config = await this.applyRegionalConfig(config, options);
      }
      
      // Apply A/B testing experiments
      config = await this.applyExperiments(config, options);
      
      // Cache the result
      this.configCache.set(cacheKey, config);
      setTimeout(() => {
        this.configCache.delete(cacheKey);
      }, this.cacheExpiryTime);
      
      this.logger.info(`Generated config for ${options.platform} v${options.appVersion} (user: ${options.userId || 'anonymous'})`);
      
      return config;

    } catch (error) {
      this.logger.error('Failed to get app config', error);
      return this.baseConfig;
    }
  }

  private generateCacheKey(options: AppConfigOptions): string {
    return `${options.platform}-${options.appVersion}-${options.userId || 'anon'}-${options.region || 'default'}`;
  }

  private async applyPlatformConfig(config: AppConfig, options: AppConfigOptions): Promise<AppConfig> {
    // Get platform-specific overrides from Redis
    const platformOverrides = await this.redis.hgetall(`config:platform:${options.platform}`);
    
    if (Object.keys(platformOverrides).length > 0) {
      // Apply platform-specific feature flags
      if (platformOverrides.features) {
        const platformFeatures = JSON.parse(platformOverrides.features);
        Object.entries(platformFeatures).forEach(([key, value]) => {
          config.features.flags.set(key, value as boolean);
        });
      }
      
      // Apply platform-specific sync configuration
      if (platformOverrides.syncConfig) {
        const platformSyncConfig = JSON.parse(platformOverrides.syncConfig);
        config.syncConfig = { ...config.syncConfig, ...platformSyncConfig };
      }
      
      // iOS specific configurations
      if (options.platform === 'ios') {
        config.features.flags.set('background_app_refresh', true);
        config.features.flags.set('app_store_review', true);
        config.security.biometricAuth = true; // Face ID / Touch ID
      }
      
      // Android specific configurations
      if (options.platform === 'android') {
        config.features.flags.set('adaptive_icon', true);
        config.features.flags.set('android_shortcuts', true);
        config.features.flags.set('notification_channels', true);
      }
    }
    
    return config;
  }

  private async applyVersionConfig(config: AppConfig, options: AppConfigOptions): Promise<AppConfig> {
    // Get version-specific configuration
    const versionConfig = await this.redis.hgetall(`config:version:${options.appVersion}`);
    
    if (Object.keys(versionConfig).length > 0) {
      // Check if force update is required
      if (versionConfig.minVersionCode) {
        const minVersion = parseInt(versionConfig.minVersionCode);
        const currentVersion = this.parseVersionCode(options.appVersion);
        
        if (currentVersion < minVersion) {
          config.forceUpdate = true;
          config.updateUrl = versionConfig.updateUrl || config.updateUrl;
        }
      }
      
      // Apply version-specific feature flags
      if (versionConfig.deprecatedFeatures) {
        const deprecated = JSON.parse(versionConfig.deprecatedFeatures);
        deprecated.forEach((feature: string) => {
          config.features.flags.set(feature, false);
        });
      }
      
      // Apply new features for this version
      if (versionConfig.newFeatures) {
        const newFeatures = JSON.parse(versionConfig.newFeatures);
        Object.entries(newFeatures).forEach(([key, value]) => {
          config.features.flags.set(key, value as boolean);
        });
      }
    }
    
    return config;
  }

  private async applyUserConfig(config: AppConfig, options: AppConfigOptions): Promise<AppConfig> {
    if (!options.userId) return config;
    
    try {
      // Get user-specific preferences
      const userPrefs = await this.redis.hgetall(`user_prefs:${options.userId}`);
      
      if (Object.keys(userPrefs).length > 0) {
        // Apply user preferences
        if (userPrefs.darkMode !== undefined) {
          config.features.flags.set('dark_mode', userPrefs.darkMode === '1');
        }
        
        if (userPrefs.pushNotifications !== undefined) {
          config.features.flags.set('push_notifications', userPrefs.pushNotifications === '1');
        }
        
        if (userPrefs.backgroundSync !== undefined) {
          config.features.flags.set('background_sync', userPrefs.backgroundSync === '1');
        }
        
        // Apply custom sync configuration
        if (userPrefs.syncConfig) {
          const userSyncConfig = JSON.parse(userPrefs.syncConfig);
          config.syncConfig = { ...config.syncConfig, ...userSyncConfig };
        }
      }
      
      // Check user subscription/plan for premium features
      const userPlan = await this.redis.get(`user_plan:${options.userId}`);
      if (userPlan === 'premium' || userPlan === 'pro') {
        config.features.flags.set('premium_features', true);
        config.features.flags.set('advanced_analytics', true);
        config.features.flags.set('priority_sync', true);
        config.features.flags.set('unlimited_storage', true);
      }
      
    } catch (error) {
      this.logger.warn(`Failed to apply user config for ${options.userId}`, error);
    }
    
    return config;
  }

  private async applyRegionalConfig(config: AppConfig, options: AppConfigOptions): Promise<AppConfig> {
    if (!options.region) return config;
    
    try {
      const regionalConfig = await this.redis.hgetall(`config:region:${options.region}`);
      
      if (Object.keys(regionalConfig).length > 0) {
        // Apply regional endpoints
        if (regionalConfig.endpoints) {
          const regionalEndpoints = JSON.parse(regionalConfig.endpoints);
          Object.entries(regionalEndpoints).forEach(([key, value]) => {
            if (key === 'serviceUrls') {
              Object.entries(value as any).forEach(([service, url]) => {
                config.endpoints.serviceUrls.set(service, url as string);
              });
            } else {
              (config.endpoints as any)[key] = value;
            }
          });
        }
        
        // Apply regional feature flags (e.g., compliance requirements)
        if (regionalConfig.features) {
          const regionalFeatures = JSON.parse(regionalConfig.features);
          Object.entries(regionalFeatures).forEach(([key, value]) => {
            config.features.flags.set(key, value as boolean);
          });
        }
        
        // Apply regional security settings
        if (regionalConfig.security) {
          const regionalSecurity = JSON.parse(regionalConfig.security);
          config.security = { ...config.security, ...regionalSecurity };
        }
      }
    } catch (error) {
      this.logger.warn(`Failed to apply regional config for ${options.region}`, error);
    }
    
    return config;
  }

  private async applyExperiments(config: AppConfig, options: AppConfigOptions): Promise<AppConfig> {
    try {
      const experiments = await this.redis.smembers('active_experiments');
      
      for (const experimentName of experiments) {
        const experiment = await this.redis.hgetall(`experiment:${experimentName}`);
        
        if (Object.keys(experiment).length === 0) continue;
        
        const rolloutPercentage = parseFloat(experiment.rolloutPercentage || '0');
        const targetGroups = experiment.targetGroups ? JSON.parse(experiment.targetGroups) : [];
        
        // Check if user is in target group
        let isInTargetGroup = targetGroups.length === 0; // If no target groups, everyone is eligible
        if (options.userId && targetGroups.length > 0) {
          const userGroups = await this.getUserGroups(options.userId);
          isInTargetGroup = targetGroups.some((group: string) => userGroups.includes(group));
        }
        
        // Apply experiment if user is in target group and passes rollout percentage
        if (isInTargetGroup && this.shouldApplyExperiment(options, rolloutPercentage)) {
          const experimentConfig = JSON.parse(experiment.config || '{}');
          
          // Apply experiment configuration
          if (experimentConfig.features) {
            Object.entries(experimentConfig.features).forEach(([key, value]) => {
              config.features.flags.set(key, value as boolean);
            });
          }
          
          // Mark experiment as applied
          const appliedExperiment: ExperimentFlag = {
            name: experimentName,
            enabled: true,
            rolloutPercentage,
            targetGroups
          };
          
          config.features.experiments.push(appliedExperiment);
          
          this.logger.info(`Applied experiment ${experimentName} for user ${options.userId || 'anonymous'}`);
        }
      }
    } catch (error) {
      this.logger.warn('Failed to apply experiments', error);
    }
    
    return config;
  }

  private async getUserGroups(userId: string): Promise<string[]> {
    try {
      const groups = await this.redis.smembers(`user_groups:${userId}`);
      return groups;
    } catch (error) {
      this.logger.warn(`Failed to get user groups for ${userId}`, error);
      return [];
    }
  }

  private shouldApplyExperiment(options: AppConfigOptions, rolloutPercentage: number): boolean {
    // Use consistent hashing based on user ID or device info
    const hashInput = options.userId || `${options.platform}-${options.deviceType}`;
    const hash = this.simpleHash(hashInput);
    const bucket = hash % 100;
    
    return bucket < (rolloutPercentage * 100);
  }

  private simpleHash(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash);
  }

  private parseVersionCode(version: string): number {
    // Simple version parsing (assumes semver format)
    const parts = version.split('.');
    const major = parseInt(parts[0] || '0') * 10000;
    const minor = parseInt(parts[1] || '0') * 100;
    const patch = parseInt(parts[2] || '0');
    
    return major + minor + patch;
  }

  async updateFeatureFlag(flagName: string, enabled: boolean, scope?: {
    platform?: string;
    version?: string;
    region?: string;
    userGroup?: string;
  }): Promise<void> {
    try {
      if (scope) {
        // Update scoped feature flag
        const scopeKey = this.buildScopeKey(scope);
        const features = await this.redis.hget(`config:${scopeKey}`, 'features');
        const featureFlags = features ? JSON.parse(features) : {};
        
        featureFlags[flagName] = enabled;
        
        await this.redis.hset(`config:${scopeKey}`, 'features', JSON.stringify(featureFlags));
      } else {
        // Update global feature flag
        this.baseConfig.features.flags.set(flagName, enabled);
      }
      
      // Clear relevant caches
      this.clearRelatedCaches(scope);
      
      this.logger.info(`Updated feature flag ${flagName} to ${enabled} for scope: ${JSON.stringify(scope || 'global')}`);
      
    } catch (error) {
      this.logger.error(`Failed to update feature flag ${flagName}`, error);
      throw error;
    }
  }

  private buildScopeKey(scope: any): string {
    const parts = [];
    if (scope.platform) parts.push(`platform:${scope.platform}`);
    if (scope.version) parts.push(`version:${scope.version}`);
    if (scope.region) parts.push(`region:${scope.region}`);
    if (scope.userGroup) parts.push(`group:${scope.userGroup}`);
    
    return parts.join(':');
  }

  private clearRelatedCaches(scope?: any): void {
    if (!scope) {
      // Clear all caches
      this.configCache.clear();
      return;
    }
    
    // Clear specific caches based on scope
    const keysToDelete: string[] = [];
    
    for (const [key, config] of this.configCache) {
      const shouldDelete = 
        (scope.platform && key.includes(scope.platform)) ||
        (scope.version && key.includes(scope.version)) ||
        (scope.region && key.includes(scope.region));
        
      if (shouldDelete) {
        keysToDelete.push(key);
      }
    }
    
    keysToDelete.forEach(key => this.configCache.delete(key));
  }

  async createExperiment(experiment: {
    name: string;
    description: string;
    rolloutPercentage: number;
    targetGroups: string[];
    config: any;
    duration?: number; // in days
  }): Promise<void> {
    try {
      const experimentKey = `experiment:${experiment.name}`;
      
      await this.redis.hset(experimentKey, {
        description: experiment.description,
        rolloutPercentage: experiment.rolloutPercentage.toString(),
        targetGroups: JSON.stringify(experiment.targetGroups),
        config: JSON.stringify(experiment.config),
        createdAt: Date.now().toString(),
        expiresAt: experiment.duration ? (Date.now() + (experiment.duration * 24 * 60 * 60 * 1000)).toString() : '0'
      });
      
      await this.redis.sadd('active_experiments', experiment.name);
      
      // Set expiration if duration is specified
      if (experiment.duration) {
        await this.redis.expire(experimentKey, experiment.duration * 24 * 60 * 60);
      }
      
      this.logger.info(`Created experiment: ${experiment.name}`);
      
    } catch (error) {
      this.logger.error(`Failed to create experiment ${experiment.name}`, error);
      throw error;
    }
  }

  async getConfigAnalytics(): Promise<{
    totalConfigRequests: number;
    configsByPlatform: { [platform: string]: number };
    activeExperiments: number;
    featureFlagUsage: { [flag: string]: number };
    averageResponseTime: number;
  }> {
    try {
      const analytics = await this.redis.hgetall('config_analytics');
      const experiments = await this.redis.smembers('active_experiments');
      
      return {
        totalConfigRequests: parseInt(analytics.totalRequests || '0'),
        configsByPlatform: JSON.parse(analytics.platformBreakdown || '{}'),
        activeExperiments: experiments.length,
        featureFlagUsage: JSON.parse(analytics.featureUsage || '{}'),
        averageResponseTime: parseFloat(analytics.avgResponseTime || '0')
      };
    } catch (error) {
      this.logger.error('Failed to get config analytics', error);
      return {
        totalConfigRequests: 0,
        configsByPlatform: {},
        activeExperiments: 0,
        featureFlagUsage: {},
        averageResponseTime: 0
      };
    }
  }

  async recordConfigRequest(options: AppConfigOptions, responseTime: number): Promise<void> {
    try {
      const analytics = await this.redis.hgetall('config_analytics');
      
      const totalRequests = parseInt(analytics.totalRequests || '0') + 1;
      const platformBreakdown = JSON.parse(analytics.platformBreakdown || '{}');
      platformBreakdown[options.platform] = (platformBreakdown[options.platform] || 0) + 1;
      
      const avgResponseTime = parseFloat(analytics.avgResponseTime || '0');
      const newAvgResponseTime = (avgResponseTime * (totalRequests - 1) + responseTime) / totalRequests;
      
      await this.redis.hset('config_analytics', {
        totalRequests: totalRequests.toString(),
        platformBreakdown: JSON.stringify(platformBreakdown),
        avgResponseTime: newAvgResponseTime.toString(),
        lastRequest: Date.now().toString()
      });
      
    } catch (error) {
      this.logger.warn('Failed to record config request analytics', error);
    }
  }

  async cleanup(): Promise<void> {
    await this.redis.quit();
    this.logger.info('App config service cleanup completed');
  }
}