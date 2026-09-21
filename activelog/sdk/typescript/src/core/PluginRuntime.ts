/**
 * ActiveLog Plugin SDK - Plugin Runtime
 */

import { EventEmitter } from 'eventemitter3';
import {
  PluginContext,
  PluginManifest,
  PluginInterface,
  PluginLogger,
  PluginStorage,
  PluginHTTP,
  PluginDatabase,
  PluginServices,
  PluginEvents,
  UserContext,
  OrganizationContext,
  PluginError,
  PermissionError,
  ResourceLimitError
} from '../types';

/**
 * Plugin Runtime - Manages plugin execution and provides sandboxed environment
 */
export class PluginRuntime {
  private plugins: Map<string, LoadedPlugin> = new Map();
  private globalEvents: EventEmitter = new EventEmitter();
  private resourceMonitor: ResourceMonitor;

  constructor(
    private services: PluginServices,
    private storageProvider: StorageProvider,
    private httpProvider: HTTPProvider,
    private databaseProvider: DatabaseProvider,
    private logger: PluginLogger
  ) {
    this.resourceMonitor = new ResourceMonitor();
  }

  /**
   * Load a plugin
   */
  async loadPlugin(
    pluginId: string,
    pluginCode: string,
    manifest: PluginManifest,
    userConfig: Record<string, any> = {},
    userContext: UserContext,
    orgContext: OrganizationContext
  ): Promise<void> {
    try {
      this.logger.info(`Loading plugin: ${pluginId}`);

      // Validate manifest
      this.validateManifest(manifest);

      // Check permissions
      await this.checkPermissions(manifest, userContext, orgContext);

      // Create sandbox environment
      const sandbox = this.createSandbox(manifest);

      // Execute plugin code in sandbox
      const PluginClass = await this.executePluginCode(pluginCode, sandbox, manifest);

      // Create plugin instance
      const pluginInstance: PluginInterface = new PluginClass();

      // Create plugin context
      const context = this.createPluginContext(
        manifest,
        userConfig,
        userContext,
        orgContext,
        pluginId
      );

      // Set context on plugin
      if (typeof pluginInstance._setContext === 'function') {
        pluginInstance._setContext(context);
      }

      // Store loaded plugin
      const loadedPlugin: LoadedPlugin = {
        id: pluginId,
        instance: pluginInstance,
        manifest,
        context,
        sandbox,
        isActive: false,
        loadedAt: new Date(),
        resourceUsage: this.resourceMonitor.createTracker(pluginId, manifest.resources)
      };

      this.plugins.set(pluginId, loadedPlugin);

      // Call plugin onLoad
      if (pluginInstance.onLoad) {
        await this.executeWithResourceMonitoring(
          pluginId,
          () => pluginInstance.onLoad!(context)
        );
      }

      this.logger.info(`Plugin loaded successfully: ${pluginId}`);
    } catch (error) {
      this.logger.error(`Failed to load plugin: ${pluginId}`, error as Error);
      throw error;
    }
  }

  /**
   * Activate a plugin
   */
  async activatePlugin(pluginId: string): Promise<void> {
    const plugin = this.getPlugin(pluginId);
    
    if (plugin.isActive) {
      return;
    }

    try {
      this.logger.info(`Activating plugin: ${pluginId}`);

      if (plugin.instance.onActivate) {
        await this.executeWithResourceMonitoring(
          pluginId,
          () => plugin.instance.onActivate!(plugin.context)
        );
      }

      plugin.isActive = true;
      plugin.activatedAt = new Date();

      this.logger.info(`Plugin activated successfully: ${pluginId}`);
    } catch (error) {
      this.logger.error(`Failed to activate plugin: ${pluginId}`, error as Error);
      throw error;
    }
  }

  /**
   * Deactivate a plugin
   */
  async deactivatePlugin(pluginId: string): Promise<void> {
    const plugin = this.getPlugin(pluginId);
    
    if (!plugin.isActive) {
      return;
    }

    try {
      this.logger.info(`Deactivating plugin: ${pluginId}`);

      if (plugin.instance.onDeactivate) {
        await this.executeWithResourceMonitoring(
          pluginId,
          () => plugin.instance.onDeactivate!(plugin.context)
        );
      }

      plugin.isActive = false;
      delete plugin.activatedAt;

      this.logger.info(`Plugin deactivated successfully: ${pluginId}`);
    } catch (error) {
      this.logger.error(`Failed to deactivate plugin: ${pluginId}`, error as Error);
      throw error;
    }
  }

  /**
   * Unload a plugin
   */
  async unloadPlugin(pluginId: string): Promise<void> {
    const plugin = this.getPlugin(pluginId);

    try {
      this.logger.info(`Unloading plugin: ${pluginId}`);

      // Deactivate if active
      if (plugin.isActive) {
        await this.deactivatePlugin(pluginId);
      }

      // Call plugin onUnload
      if (plugin.instance.onUnload) {
        await this.executeWithResourceMonitoring(
          pluginId,
          () => plugin.instance.onUnload!(plugin.context)
        );
      }

      // Cleanup resources
      this.resourceMonitor.cleanup(pluginId);

      // Remove from loaded plugins
      this.plugins.delete(pluginId);

      this.logger.info(`Plugin unloaded successfully: ${pluginId}`);
    } catch (error) {
      this.logger.error(`Failed to unload plugin: ${pluginId}`, error as Error);
      throw error;
    }
  }

  /**
   * Execute plugin trigger
   */
  async executeTrigger(pluginId: string, event: any): Promise<any> {
    const plugin = this.getPlugin(pluginId);

    if (!plugin.isActive) {
      throw new PluginError(`Plugin not active: ${pluginId}`);
    }

    if (!plugin.instance.onTrigger) {
      throw new PluginError(`Plugin does not handle triggers: ${pluginId}`);
    }

    return await this.executeWithResourceMonitoring(
      pluginId,
      () => plugin.instance.onTrigger!(event, plugin.context)
    );
  }

  /**
   * Execute plugin API handler
   */
  async executeAPI(pluginId: string, path: string, method: string, data: any): Promise<any> {
    const plugin = this.getPlugin(pluginId);

    if (!plugin.isActive) {
      throw new PluginError(`Plugin not active: ${pluginId}`);
    }

    if (!plugin.instance.handleAPI) {
      throw new PluginError(`Plugin does not handle API requests: ${pluginId}`);
    }

    return await this.executeWithResourceMonitoring(
      pluginId,
      () => plugin.instance.handleAPI!(path, method, data, plugin.context)
    );
  }

  /**
   * Update plugin configuration
   */
  async updatePluginConfig(pluginId: string, newConfig: Record<string, any>): Promise<void> {
    const plugin = this.getPlugin(pluginId);

    // Update context config
    plugin.context = {
      ...plugin.context,
      config: { ...plugin.context.config, ...newConfig }
    };

    // Notify plugin of config change
    if (plugin.instance.onConfigChange) {
      await this.executeWithResourceMonitoring(
        pluginId,
        () => plugin.instance.onConfigChange!(newConfig, plugin.context)
      );
    }
  }

  /**
   * Get plugin status
   */
  getPluginStatus(pluginId: string) {
    if (!this.plugins.has(pluginId)) {
      return { status: 'not-loaded' };
    }

    const plugin = this.plugins.get(pluginId)!;
    const resourceUsage = this.resourceMonitor.getUsage(pluginId);

    return {
      status: plugin.isActive ? 'active' : 'loaded',
      manifest: plugin.manifest,
      loadedAt: plugin.loadedAt,
      activatedAt: plugin.activatedAt,
      resourceUsage
    };
  }

  /**
   * List all plugins
   */
  listPlugins() {
    return Array.from(this.plugins.keys()).map(id => this.getPluginStatus(id));
  }

  private getPlugin(pluginId: string): LoadedPlugin {
    const plugin = this.plugins.get(pluginId);
    if (!plugin) {
      throw new PluginError(`Plugin not found: ${pluginId}`);
    }
    return plugin;
  }

  private validateManifest(manifest: PluginManifest): void {
    // Basic manifest validation
    if (!manifest.name || !manifest.version || !manifest.main) {
      throw new PluginError('Invalid manifest: missing required fields');
    }

    // Validate version format
    if (!/^\d+\.\d+\.\d+/.test(manifest.version)) {
      throw new PluginError('Invalid version format');
    }
  }

  private async checkPermissions(
    manifest: PluginManifest,
    userContext: UserContext,
    orgContext: OrganizationContext
  ): Promise<void> {
    // Check organization plan limits
    const requiredServices = manifest.permissions.services || [];
    const availableServices = orgContext.features;

    for (const service of requiredServices) {
      if (!availableServices.includes(service)) {
        throw new PermissionError(`Service not available in current plan: ${service}`);
      }
    }

    // Check user permissions
    if (manifest.permissions.database?.write) {
      if (!userContext.permissions.includes('plugin:database:write')) {
        throw new PermissionError('database:write');
      }
    }

    // Check resource limits
    const resources = manifest.resources;
    if (resources) {
      if (resources.cpu && resources.cpu > orgContext.limits.maxPluginCpu) {
        throw new ResourceLimitError('cpu', `${resources.cpu} > ${orgContext.limits.maxPluginCpu}`);
      }
      
      if (resources.memory) {
        const memoryMB = this.parseMemoryLimit(resources.memory);
        if (memoryMB > orgContext.limits.maxPluginMemoryMB) {
          throw new ResourceLimitError('memory', `${memoryMB}MB > ${orgContext.limits.maxPluginMemoryMB}MB`);
        }
      }
    }
  }

  private createSandbox(manifest: PluginManifest): PluginSandbox {
    const allowedModules = new Set(['crypto', 'util', 'path']);
    
    // Add allowed NPM modules from manifest
    if (manifest.dependencies?.npm) {
      Object.keys(manifest.dependencies.npm).forEach(module => {
        allowedModules.add(module);
      });
    }

    return {
      console: {
        log: (...args) => this.logger.info('Plugin console:', ...args),
        error: (...args) => this.logger.error('Plugin console:', undefined, ...args),
        warn: (...args) => this.logger.warn('Plugin console:', ...args)
      },
      setTimeout,
      setInterval,
      clearTimeout,
      clearInterval,
      require: (module: string) => {
        if (!allowedModules.has(module)) {
          throw new PluginError(`Module not allowed: ${module}`);
        }
        return require(module);
      },
      Buffer,
      process: {
        env: {}, // Empty env for security
        version: process.version,
        platform: process.platform
      }
    };
  }

  private async executePluginCode(
    code: string,
    sandbox: PluginSandbox,
    manifest: PluginManifest
  ): Promise<any> {
    // In a real implementation, this would use a proper sandbox like vm2 or isolated-vm
    const vm = require('vm');
    const context = vm.createContext(sandbox);

    try {
      const script = new vm.Script(`
        ${code}
        module.exports;
      `);

      const result = script.runInContext(context, {
        timeout: 10000, // 10 second timeout for loading
        filename: manifest.main
      });

      return result.default || result;
    } catch (error) {
      throw new PluginError(`Failed to execute plugin code: ${(error as Error).message}`);
    }
  }

  private createPluginContext(
    manifest: PluginManifest,
    config: Record<string, any>,
    userContext: UserContext,
    orgContext: OrganizationContext,
    pluginId: string
  ): PluginContext {
    return {
      manifest,
      config: { ...manifest.config?.defaults, ...config },
      logger: this.createPluginLogger(pluginId),
      storage: this.createPluginStorage(pluginId),
      http: this.createPluginHTTP(pluginId, manifest),
      database: this.createPluginDatabase(pluginId, manifest),
      services: this.services,
      events: this.createPluginEvents(pluginId),
      user: userContext,
      organization: orgContext
    };
  }

  private createPluginLogger(pluginId: string): PluginLogger {
    return {
      debug: (message, ...args) => this.logger.debug(`[${pluginId}] ${message}`, ...args),
      info: (message, ...args) => this.logger.info(`[${pluginId}] ${message}`, ...args),
      warn: (message, ...args) => this.logger.warn(`[${pluginId}] ${message}`, ...args),
      error: (message, error, ...args) => this.logger.error(`[${pluginId}] ${message}`, error, ...args)
    };
  }

  private createPluginStorage(pluginId: string): PluginStorage {
    return this.storageProvider.createPluginStorage(pluginId);
  }

  private createPluginHTTP(pluginId: string, manifest: PluginManifest): PluginHTTP {
    return this.httpProvider.createPluginHTTP(pluginId, manifest.permissions.network);
  }

  private createPluginDatabase(pluginId: string, manifest: PluginManifest): PluginDatabase {
    return this.databaseProvider.createPluginDatabase(pluginId, manifest.permissions.database);
  }

  private createPluginEvents(pluginId: string): PluginEvents {
    const pluginEvents = new EventEmitter();
    
    return {
      on: (event, listener) => {
        pluginEvents.on(event, listener);
        this.globalEvents.on(`plugin:${pluginId}:${event}`, listener);
      },
      off: (event, listener) => {
        pluginEvents.off(event, listener);
        this.globalEvents.off(`plugin:${pluginId}:${event}`, listener);
      },
      emit: (event, ...args) => {
        pluginEvents.emit(event, ...args);
        this.globalEvents.emit(`plugin:${pluginId}:${event}`, ...args);
      },
      once: (event, listener) => {
        pluginEvents.once(event, listener);
        this.globalEvents.once(`plugin:${pluginId}:${event}`, listener);
      }
    };
  }

  private async executeWithResourceMonitoring<T>(
    pluginId: string,
    fn: () => Promise<T>
  ): Promise<T> {
    const plugin = this.getPlugin(pluginId);
    const tracker = plugin.resourceUsage;

    tracker.startExecution();

    try {
      const result = await Promise.race([
        fn(),
        this.createTimeoutPromise(plugin.manifest.resources?.timeout || 60)
      ]);

      tracker.endExecution(true);
      return result as T;
    } catch (error) {
      tracker.endExecution(false);
      throw error;
    }
  }

  private createTimeoutPromise(timeoutSeconds: number): Promise<never> {
    return new Promise((_, reject) => {
      setTimeout(() => {
        reject(new ResourceLimitError('execution_time', `${timeoutSeconds}s`));
      }, timeoutSeconds * 1000);
    });
  }

  private parseMemoryLimit(limit: string): number {
    const match = limit.match(/^(\d+)([KMGT]?)B$/);
    if (!match) return 0;

    const value = parseInt(match[1]);
    const unit = match[2];

    switch (unit) {
      case 'K': return value / 1024;
      case 'M': return value;
      case 'G': return value * 1024;
      case 'T': return value * 1024 * 1024;
      default: return value / (1024 * 1024); // bytes to MB
    }
  }
}

interface LoadedPlugin {
  id: string;
  instance: PluginInterface;
  manifest: PluginManifest;
  context: PluginContext;
  sandbox: PluginSandbox;
  isActive: boolean;
  loadedAt: Date;
  activatedAt?: Date;
  resourceUsage: ResourceTracker;
}

interface PluginSandbox {
  console: {
    log: (...args: any[]) => void;
    error: (...args: any[]) => void;
    warn: (...args: any[]) => void;
  };
  setTimeout: typeof setTimeout;
  setInterval: typeof setInterval;
  clearTimeout: typeof clearTimeout;
  clearInterval: typeof clearInterval;
  require: (module: string) => any;
  Buffer: typeof Buffer;
  process: {
    env: Record<string, string>;
    version: string;
    platform: string;
  };
}

class ResourceMonitor {
  private trackers: Map<string, ResourceTracker> = new Map();

  createTracker(pluginId: string, limits?: any): ResourceTracker {
    const tracker = new ResourceTracker(pluginId, limits);
    this.trackers.set(pluginId, tracker);
    return tracker;
  }

  getUsage(pluginId: string) {
    return this.trackers.get(pluginId)?.getUsage();
  }

  cleanup(pluginId: string) {
    this.trackers.delete(pluginId);
  }
}

class ResourceTracker {
  private startTime?: Date;
  private totalExecutionTime = 0;
  private executionCount = 0;
  private errorCount = 0;

  constructor(
    private pluginId: string,
    private limits?: any
  ) {}

  startExecution() {
    this.startTime = new Date();
  }

  endExecution(success: boolean) {
    if (!this.startTime) return;

    const duration = Date.now() - this.startTime.getTime();
    this.totalExecutionTime += duration;
    this.executionCount++;

    if (!success) {
      this.errorCount++;
    }

    this.startTime = undefined;
  }

  getUsage() {
    return {
      totalExecutionTime: this.totalExecutionTime,
      executionCount: this.executionCount,
      errorCount: this.errorCount,
      averageExecutionTime: this.executionCount > 0 ? this.totalExecutionTime / this.executionCount : 0,
      successRate: this.executionCount > 0 ? (this.executionCount - this.errorCount) / this.executionCount : 0
    };
  }
}

// Provider interfaces that would be implemented by the actual runtime
export interface StorageProvider {
  createPluginStorage(pluginId: string): PluginStorage;
}

export interface HTTPProvider {
  createPluginHTTP(pluginId: string, permissions?: any): PluginHTTP;
}

export interface DatabaseProvider {
  createPluginDatabase(pluginId: string, permissions?: any): PluginDatabase;
}

export { PluginRuntime };