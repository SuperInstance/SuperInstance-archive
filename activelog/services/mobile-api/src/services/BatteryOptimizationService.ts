import { EventEmitter } from 'events';
import Redis from 'ioredis';
import * as cron from 'cron';
import { Logger } from '@/utils/logger';
import { ConnectionState, BatteryOptimization, SyncRequest } from '@/types/sync';

export interface BatteryConfig {
  redis: {
    host: string;
    port: number;
    password?: string;
  };
  lowBatteryThreshold: number;
  criticalBatteryThreshold: number;
  syncIntervals: {
    normal: number;        // minutes
    lowBattery: number;    // minutes
    critical: number;      // minutes
    charging: number;      // minutes
  };
  networkOptimization: {
    wifiPriority: number;
    cellularPriority: number;
    lowBandwidthThreshold: number; // kbps
  };
}

export interface SyncStrategy {
  syncInterval: number;
  batchSize: number;
  maxConcurrentOperations: number;
  enableCompression: boolean;
  prioritizeOperations: boolean;
  deferNonCriticalUpdates: boolean;
  useBackgroundSync: boolean;
  networkConditions: 'any' | 'wifi-only' | 'high-bandwidth';
}

export class BatteryOptimizationService extends EventEmitter {
  private redis: Redis;
  private logger: Logger;
  private config: BatteryConfig;
  private syncScheduler: Map<string, cron.CronJob> = new Map();
  private deviceStates: Map<string, ConnectionState> = new Map();

  // Predefined strategies for different battery/network conditions
  private strategies: { [key: string]: SyncStrategy } = {
    optimal: {
      syncInterval: 5,
      batchSize: 100,
      maxConcurrentOperations: 5,
      enableCompression: true,
      prioritizeOperations: true,
      deferNonCriticalUpdates: false,
      useBackgroundSync: true,
      networkConditions: 'any'
    },
    
    batteryEfficient: {
      syncInterval: 15,
      batchSize: 50,
      maxConcurrentOperations: 2,
      enableCompression: true,
      prioritizeOperations: true,
      deferNonCriticalUpdates: true,
      useBackgroundSync: false,
      networkConditions: 'wifi-only'
    },
    
    critical: {
      syncInterval: 60,
      batchSize: 20,
      maxConcurrentOperations: 1,
      enableCompression: true,
      prioritizeOperations: true,
      deferNonCriticalUpdates: true,
      useBackgroundSync: false,
      networkConditions: 'wifi-only'
    },
    
    charging: {
      syncInterval: 2,
      batchSize: 200,
      maxConcurrentOperations: 10,
      enableCompression: false, // Trade battery for speed when charging
      prioritizeOperations: false,
      deferNonCriticalUpdates: false,
      useBackgroundSync: true,
      networkConditions: 'any'
    },
    
    offline: {
      syncInterval: 0, // No sync
      batchSize: 0,
      maxConcurrentOperations: 0,
      enableCompression: true,
      prioritizeOperations: true,
      deferNonCriticalUpdates: true,
      useBackgroundSync: false,
      networkConditions: 'any'
    }
  };

  constructor(config: BatteryConfig) {
    super();
    this.config = config;
    this.logger = new Logger('BatteryOptimizationService');
    this.redis = new Redis({
      host: config.redis.host,
      port: config.redis.port,
      password: config.redis.password,
      retryDelayOnFailover: 100,
      enableReadyCheck: false,
      maxRetriesPerRequest: null
    });
  }

  async updateDeviceState(deviceId: string, state: ConnectionState): Promise<void> {
    this.deviceStates.set(deviceId, state);
    
    // Store in Redis for persistence
    await this.redis.hset(`device_state:${deviceId}`, {
      online: state.online ? '1' : '0',
      connectionType: state.connectionType.toString(),
      bandwidthKbps: state.bandwidthKbps.toString(),
      latencyMs: state.latencyMs.toString(),
      meteredConnection: state.meteredConnection ? '1' : '0',
      batteryLevel: state.batteryLevel.toString(),
      lowPowerMode: state.lowPowerMode ? '1' : '0',
      lastUpdated: Date.now().toString()
    });

    // Determine optimal sync strategy
    const strategy = this.calculateOptimalStrategy(state);
    await this.updateSyncStrategy(deviceId, strategy);
    
    // Emit strategy change event
    this.emit('strategy_changed', { deviceId, state, strategy });
    
    this.logger.info(`Updated device state for ${deviceId}: Battery ${state.batteryLevel}%, ${state.connectionType}, Strategy: ${this.getStrategyName(strategy)}`);
  }

  private calculateOptimalStrategy(state: ConnectionState): SyncStrategy {
    // If device is offline, use offline strategy
    if (!state.online) {
      return this.strategies.offline;
    }

    // If device is charging, use aggressive strategy
    if (this.isCharging(state)) {
      return this.strategies.charging;
    }

    // If battery is critical, use minimal strategy
    if (state.batteryLevel <= this.config.criticalBatteryThreshold) {
      return this.strategies.critical;
    }

    // If battery is low or in low power mode, use efficient strategy
    if (state.batteryLevel <= this.config.lowBatteryThreshold || state.lowPowerMode) {
      return this.strategies.batteryEfficient;
    }

    // Consider network conditions
    if (state.meteredConnection || state.bandwidthKbps < this.config.networkOptimization.lowBandwidthThreshold) {
      // Use battery efficient strategy for poor network conditions
      const strategy = { ...this.strategies.batteryEfficient };
      strategy.networkConditions = 'wifi-only';
      return strategy;
    }

    // Use optimal strategy for good conditions
    return this.strategies.optimal;
  }

  private isCharging(state: ConnectionState): boolean {
    // In a real implementation, this would check if the device is charging
    // For now, assume charging if battery level is increasing or at 100%
    return state.batteryLevel === 100;
  }

  private getStrategyName(strategy: SyncStrategy): string {
    for (const [name, strat] of Object.entries(this.strategies)) {
      if (JSON.stringify(strat) === JSON.stringify(strategy)) {
        return name;
      }
    }
    return 'custom';
  }

  async updateSyncStrategy(deviceId: string, strategy: SyncStrategy): Promise<void> {
    // Store strategy in Redis
    await this.redis.hset(`sync_strategy:${deviceId}`, {
      syncInterval: strategy.syncInterval.toString(),
      batchSize: strategy.batchSize.toString(),
      maxConcurrentOperations: strategy.maxConcurrentOperations.toString(),
      enableCompression: strategy.enableCompression ? '1' : '0',
      prioritizeOperations: strategy.prioritizeOperations ? '1' : '0',
      deferNonCriticalUpdates: strategy.deferNonCriticalUpdates ? '1' : '0',
      useBackgroundSync: strategy.useBackgroundSync ? '1' : '0',
      networkConditions: strategy.networkConditions,
      updatedAt: Date.now().toString()
    });

    // Update sync scheduler
    await this.updateSyncScheduler(deviceId, strategy);
  }

  private async updateSyncScheduler(deviceId: string, strategy: SyncStrategy): Promise<void> {
    // Cancel existing scheduler
    const existingJob = this.syncScheduler.get(deviceId);
    if (existingJob) {
      existingJob.stop();
      existingJob.destroy();
      this.syncScheduler.delete(deviceId);
    }

    // Don't schedule if sync interval is 0 (offline strategy)
    if (strategy.syncInterval === 0) {
      return;
    }

    // Create new cron job for sync
    const cronPattern = this.createCronPattern(strategy.syncInterval);
    const job = new cron.CronJob(cronPattern, async () => {
      try {
        await this.performOptimizedSync(deviceId, strategy);
      } catch (error) {
        this.logger.error(`Scheduled sync failed for device ${deviceId}`, error);
      }
    });

    job.start();
    this.syncScheduler.set(deviceId, job);
    
    this.logger.info(`Updated sync scheduler for ${deviceId}: every ${strategy.syncInterval} minutes`);
  }

  private createCronPattern(intervalMinutes: number): string {
    if (intervalMinutes < 60) {
      return `*/${intervalMinutes} * * * *`;
    } else {
      const hours = Math.floor(intervalMinutes / 60);
      return `0 */${hours} * * *`;
    }
  }

  private async performOptimizedSync(deviceId: string, strategy: SyncStrategy): Promise<void> {
    // Get current device state
    const state = this.deviceStates.get(deviceId);
    if (!state) {
      this.logger.warn(`No device state found for ${deviceId}, skipping sync`);
      return;
    }

    // Check if sync should proceed based on current conditions
    if (!this.shouldProceedWithSync(state, strategy)) {
      this.logger.info(`Skipping sync for ${deviceId} due to current conditions`);
      return;
    }

    // Emit sync event for the main sync service to handle
    this.emit('perform_sync', {
      deviceId,
      strategy,
      state,
      batteryOptimized: true
    });
  }

  private shouldProceedWithSync(state: ConnectionState, strategy: SyncStrategy): boolean {
    // Check network conditions
    switch (strategy.networkConditions) {
      case 'wifi-only':
        if (state.connectionType !== 1) { // 1 = WIFI in ConnectionType enum
          return false;
        }
        break;
        
      case 'high-bandwidth':
        if (state.bandwidthKbps < this.config.networkOptimization.lowBandwidthThreshold) {
          return false;
        }
        break;
    }

    // Check if device is in low power mode and strategy doesn't allow background sync
    if (state.lowPowerMode && !strategy.useBackgroundSync) {
      return false;
    }

    // Check battery level for critical operations
    if (state.batteryLevel <= this.config.criticalBatteryThreshold && !strategy.deferNonCriticalUpdates) {
      return false;
    }

    return true;
  }

  async optimizeSyncRequest(deviceId: string, request: SyncRequest): Promise<SyncRequest> {
    const strategy = await this.getSyncStrategy(deviceId);
    if (!strategy) {
      return request; // Return original request if no strategy found
    }

    // Apply strategy optimizations to the request
    const optimizedRequest = { ...request };
    
    // Update sync options based on strategy
    if (!optimizedRequest.options) {
      optimizedRequest.options = {};
    }

    optimizedRequest.options.batchSize = strategy.batchSize;
    optimizedRequest.options.compress = strategy.enableCompression;
    
    // Filter entity types if deferring non-critical updates
    if (strategy.deferNonCriticalUpdates) {
      optimizedRequest.entityTypes = this.filterCriticalEntityTypes(optimizedRequest.entityTypes);
    }

    // Set battery optimization options
    optimizedRequest.options.batteryOptimization = {
      enabled: true,
      syncIntervalMinutes: strategy.syncInterval,
      wifiOnly: strategy.networkConditions === 'wifi-only',
      lowPowerMode: strategy.useBackgroundSync,
      maxConcurrentOperations: strategy.maxConcurrentOperations
    };

    return optimizedRequest;
  }

  private filterCriticalEntityTypes(entityTypes: string[]): string[] {
    // Define critical entity types that should always sync
    const criticalTypes = ['user', 'notification', 'security'];
    
    return entityTypes.filter(type => 
      criticalTypes.includes(type.toLowerCase()) ||
      type.toLowerCase().includes('critical') ||
      type.toLowerCase().includes('urgent')
    );
  }

  async getSyncStrategy(deviceId: string): Promise<SyncStrategy | null> {
    try {
      const strategyData = await this.redis.hgetall(`sync_strategy:${deviceId}`);
      
      if (Object.keys(strategyData).length === 0) {
        return null;
      }

      return {
        syncInterval: parseInt(strategyData.syncInterval),
        batchSize: parseInt(strategyData.batchSize),
        maxConcurrentOperations: parseInt(strategyData.maxConcurrentOperations),
        enableCompression: strategyData.enableCompression === '1',
        prioritizeOperations: strategyData.prioritizeOperations === '1',
        deferNonCriticalUpdates: strategyData.deferNonCriticalUpdates === '1',
        useBackgroundSync: strategyData.useBackgroundSync === '1',
        networkConditions: strategyData.networkConditions as any
      };
    } catch (error) {
      this.logger.error(`Failed to get sync strategy for ${deviceId}`, error);
      return null;
    }
  }

  async getDeviceState(deviceId: string): Promise<ConnectionState | null> {
    // Try memory cache first
    const cachedState = this.deviceStates.get(deviceId);
    if (cachedState) {
      return cachedState;
    }

    // Fall back to Redis
    try {
      const stateData = await this.redis.hgetall(`device_state:${deviceId}`);
      
      if (Object.keys(stateData).length === 0) {
        return null;
      }

      const state: ConnectionState = {
        online: stateData.online === '1',
        connectionType: parseInt(stateData.connectionType),
        bandwidthKbps: parseInt(stateData.bandwidthKbps),
        latencyMs: parseInt(stateData.latencyMs),
        meteredConnection: stateData.meteredConnection === '1',
        batteryLevel: parseInt(stateData.batteryLevel),
        lowPowerMode: stateData.lowPowerMode === '1'
      };

      // Update memory cache
      this.deviceStates.set(deviceId, state);
      
      return state;
    } catch (error) {
      this.logger.error(`Failed to get device state for ${deviceId}`, error);
      return null;
    }
  }

  async predictOptimalSyncWindow(deviceId: string): Promise<{
    nextSyncTime: Date;
    confidence: number;
    reason: string;
  } | null> {
    // Get historical sync patterns and device state
    const history = await this.getSyncHistory(deviceId);
    const currentState = await this.getDeviceState(deviceId);
    
    if (!currentState || history.length === 0) {
      return null;
    }

    // Simple prediction based on battery charging patterns
    let nextSyncTime: Date;
    let confidence = 0.5;
    let reason = 'Default scheduling';

    // If device is charging, predict next optimal window
    if (this.isCharging(currentState)) {
      nextSyncTime = new Date(Date.now() + (2 * 60 * 1000)); // 2 minutes
      confidence = 0.9;
      reason = 'Device is charging - optimal for sync';
    }
    // If battery is high and on WiFi
    else if (currentState.batteryLevel > 80 && currentState.connectionType === 1) {
      nextSyncTime = new Date(Date.now() + (5 * 60 * 1000)); // 5 minutes
      confidence = 0.8;
      reason = 'High battery and WiFi connection';
    }
    // If battery is low, wait for better conditions
    else if (currentState.batteryLevel < this.config.lowBatteryThreshold) {
      nextSyncTime = new Date(Date.now() + (30 * 60 * 1000)); // 30 minutes
      confidence = 0.6;
      reason = 'Low battery - waiting for better conditions';
    }
    // Default case
    else {
      const strategy = await this.getSyncStrategy(deviceId);
      const interval = strategy ? strategy.syncInterval : 15;
      nextSyncTime = new Date(Date.now() + (interval * 60 * 1000));
      confidence = 0.7;
      reason = `Scheduled based on current strategy (${interval}min)`;
    }

    return {
      nextSyncTime,
      confidence,
      reason
    };
  }

  private async getSyncHistory(deviceId: string): Promise<any[]> {
    try {
      const historyKey = `sync_history:${deviceId}`;
      const history = await this.redis.lrange(historyKey, 0, 99); // Last 100 syncs
      return history.map(h => JSON.parse(h));
    } catch (error) {
      this.logger.error(`Failed to get sync history for ${deviceId}`, error);
      return [];
    }
  }

  async recordSyncEvent(deviceId: string, event: {
    timestamp: number;
    batteryLevel: number;
    connectionType: number;
    syncDuration: number;
    bytesTransferred: number;
    success: boolean;
  }): Promise<void> {
    try {
      const historyKey = `sync_history:${deviceId}`;
      
      await this.redis.lpush(historyKey, JSON.stringify(event));
      await this.redis.ltrim(historyKey, 0, 99); // Keep last 100 events
      
      // Update battery usage analytics
      await this.updateBatteryUsageAnalytics(deviceId, event);
      
    } catch (error) {
      this.logger.error(`Failed to record sync event for ${deviceId}`, error);
    }
  }

  private async updateBatteryUsageAnalytics(deviceId: string, event: any): Promise<void> {
    const analyticsKey = `battery_analytics:${deviceId}`;
    const analytics = await this.redis.hgetall(analyticsKey);
    
    const totalSyncs = parseInt(analytics.totalSyncs || '0') + 1;
    const totalDuration = parseInt(analytics.totalDuration || '0') + event.syncDuration;
    const totalBytes = parseInt(analytics.totalBytes || '0') + event.bytesTransferred;
    const averageBatteryUsage = parseFloat(analytics.averageBatteryUsage || '0');
    
    // Estimate battery usage (simplified calculation)
    const estimatedBatteryUsage = this.estimateBatteryUsage(event);
    const newAverageBatteryUsage = (averageBatteryUsage * (totalSyncs - 1) + estimatedBatteryUsage) / totalSyncs;
    
    await this.redis.hset(analyticsKey, {
      totalSyncs: totalSyncs.toString(),
      totalDuration: totalDuration.toString(),
      totalBytes: totalBytes.toString(),
      averageBatteryUsage: newAverageBatteryUsage.toString(),
      lastSync: event.timestamp.toString()
    });
  }

  private estimateBatteryUsage(event: any): number {
    // Simplified battery usage estimation
    // In reality, this would use more sophisticated models
    const baseUsage = 0.1; // Base percentage per sync
    const networkMultiplier = event.connectionType === 1 ? 0.8 : 1.2; // WiFi vs Cellular
    const dataMultiplier = event.bytesTransferred / 1024 / 1024 * 0.05; // Per MB
    const durationMultiplier = event.syncDuration / 1000 * 0.01; // Per second
    
    return baseUsage * networkMultiplier + dataMultiplier + durationMultiplier;
  }

  async getBatteryUsageStats(deviceId: string): Promise<{
    totalSyncs: number;
    averageBatteryUsage: number;
    totalDuration: number;
    efficiency: number;
  }> {
    try {
      const analytics = await this.redis.hgetall(`battery_analytics:${deviceId}`);
      
      if (Object.keys(analytics).length === 0) {
        return {
          totalSyncs: 0,
          averageBatteryUsage: 0,
          totalDuration: 0,
          efficiency: 0
        };
      }

      const totalSyncs = parseInt(analytics.totalSyncs || '0');
      const averageBatteryUsage = parseFloat(analytics.averageBatteryUsage || '0');
      const totalDuration = parseInt(analytics.totalDuration || '0');
      const totalBytes = parseInt(analytics.totalBytes || '0');
      
      // Calculate efficiency (bytes per battery unit)
      const efficiency = averageBatteryUsage > 0 ? totalBytes / (averageBatteryUsage * totalSyncs) : 0;

      return {
        totalSyncs,
        averageBatteryUsage,
        totalDuration,
        efficiency
      };
    } catch (error) {
      this.logger.error(`Failed to get battery usage stats for ${deviceId}`, error);
      return {
        totalSyncs: 0,
        averageBatteryUsage: 0,
        totalDuration: 0,
        efficiency: 0
      };
    }
  }

  async pauseSync(deviceId: string, durationMinutes: number): Promise<void> {
    const job = this.syncScheduler.get(deviceId);
    if (job) {
      job.stop();
      
      // Resume after specified duration
      setTimeout(() => {
        job.start();
        this.logger.info(`Resumed sync for device ${deviceId}`);
      }, durationMinutes * 60 * 1000);
      
      this.logger.info(`Paused sync for device ${deviceId} for ${durationMinutes} minutes`);
    }
  }

  async cleanup(): Promise<void> {
    // Stop all scheduled jobs
    for (const [deviceId, job] of this.syncScheduler) {
      job.stop();
      job.destroy();
    }
    this.syncScheduler.clear();
    
    await this.redis.quit();
    this.logger.info('Battery optimization service cleanup completed');
  }
}