/**
 * ActiveLog Plugin SDK - Core Plugin Class
 */

import { EventEmitter } from 'eventemitter3';
import {
  PluginInterface,
  PluginContext,
  PluginManifest,
  TriggerEvent,
  TriggerResult,
  PluginError
} from '../types';

/**
 * Base Plugin class that all plugins should extend
 */
export abstract class Plugin implements PluginInterface {
  protected context!: PluginContext;
  protected events: EventEmitter;
  protected isActive = false;
  protected isLoaded = false;

  constructor() {
    this.events = new EventEmitter();
  }

  /**
   * Get the plugin manifest
   */
  abstract getManifest(): PluginManifest;

  /**
   * Internal method to set the plugin context
   * Called by the runtime when the plugin is loaded
   */
  public _setContext(context: PluginContext): void {
    this.context = context;
  }

  /**
   * Get the current plugin context
   */
  protected getContext(): PluginContext {
    if (!this.context) {
      throw new PluginError('Plugin context not available. Plugin may not be loaded.');
    }
    return this.context;
  }

  /**
   * Check if the plugin is currently active
   */
  public isPluginActive(): boolean {
    return this.isActive;
  }

  /**
   * Check if the plugin is currently loaded
   */
  public isPluginLoaded(): boolean {
    return this.isLoaded;
  }

  /**
   * Plugin lifecycle methods - override as needed
   */

  /**
   * Called when the plugin is first loaded
   */
  public async onLoad?(context: PluginContext): Promise<void> {
    this.context = context;
    this.isLoaded = true;
    this.log('info', 'Plugin loaded');
  }

  /**
   * Called when the plugin is activated
   */
  public async onActivate?(context: PluginContext): Promise<void> {
    this.isActive = true;
    this.log('info', 'Plugin activated');
  }

  /**
   * Called when the plugin is deactivated
   */
  public async onDeactivate?(context: PluginContext): Promise<void> {
    this.isActive = false;
    this.log('info', 'Plugin deactivated');
  }

  /**
   * Called when the plugin is unloaded
   */
  public async onUnload?(context: PluginContext): Promise<void> {
    this.isLoaded = false;
    this.isActive = false;
    this.events.removeAllListeners();
    this.log('info', 'Plugin unloaded');
  }

  /**
   * Called when configuration changes
   */
  public async onConfigChange?(
    config: Record<string, any>,
    context: PluginContext
  ): Promise<void> {
    this.log('info', 'Configuration changed', { config });
  }

  /**
   * Called when a trigger event occurs
   */
  public async onTrigger?(
    event: TriggerEvent,
    context: PluginContext
  ): Promise<TriggerResult> {
    this.log('info', 'Trigger event received', { event });
    return { success: true };
  }

  /**
   * Called for API endpoint handlers
   */
  public async handleAPI?(
    path: string,
    method: string,
    data: any,
    context: PluginContext
  ): Promise<any> {
    throw new PluginError(`API endpoint not implemented: ${method} ${path}`);
  }

  /**
   * Utility methods for plugin developers
   */

  /**
   * Log a message using the plugin logger
   */
  protected log(level: 'debug' | 'info' | 'warn' | 'error', message: string, data?: any): void {
    const context = this.getContext();
    const logger = context.logger;

    switch (level) {
      case 'debug':
        logger.debug(message, data);
        break;
      case 'info':
        logger.info(message, data);
        break;
      case 'warn':
        logger.warn(message, data);
        break;
      case 'error':
        logger.error(message, data);
        break;
    }
  }

  /**
   * Get plugin configuration
   */
  protected getConfig<T = any>(key?: string): T {
    const context = this.getContext();
    if (key) {
      return context.config[key] as T;
    }
    return context.config as T;
  }

  /**
   * Store data in plugin storage
   */
  protected async setStorage(key: string, value: any, ttl?: number): Promise<void> {
    const context = this.getContext();
    await context.storage.set(key, value, ttl);
  }

  /**
   * Retrieve data from plugin storage
   */
  protected async getStorage<T = any>(key: string): Promise<T | null> {
    const context = this.getContext();
    return await context.storage.get(key);
  }

  /**
   * Delete data from plugin storage
   */
  protected async deleteStorage(key: string): Promise<void> {
    const context = this.getContext();
    await context.storage.delete(key);
  }

  /**
   * Make an HTTP request
   */
  protected async httpRequest(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
    url: string,
    data?: any,
    options?: { headers?: Record<string, string>; timeout?: number }
  ) {
    const context = this.getContext();
    const http = context.http;

    switch (method) {
      case 'GET':
        return await http.get(url, options);
      case 'POST':
        return await http.post(url, data, options);
      case 'PUT':
        return await http.put(url, data, options);
      case 'DELETE':
        return await http.delete(url, options);
      case 'PATCH':
        return await http.patch(url, data, options);
      default:
        throw new PluginError(`Unsupported HTTP method: ${method}`);
    }
  }

  /**
   * Query the database
   */
  protected async dbQuery(sql: string, params?: any[]) {
    const context = this.getContext();
    return await context.database.query(sql, params);
  }

  /**
   * Get current user
   */
  protected getCurrentUser() {
    const context = this.getContext();
    return context.user;
  }

  /**
   * Get organization context
   */
  protected getOrganization() {
    const context = this.getContext();
    return context.organization;
  }

  /**
   * Emit an event
   */
  protected emitEvent(event: string, ...args: any[]): void {
    const context = this.getContext();
    context.events.emit(event, ...args);
    this.events.emit(event, ...args);
  }

  /**
   * Listen to an event
   */
  protected onEvent(event: string, listener: (...args: any[]) => void): void {
    const context = this.getContext();
    context.events.on(event, listener);
  }

  /**
   * Remove event listener
   */
  protected offEvent(event: string, listener: (...args: any[]) => void): void {
    const context = this.getContext();
    context.events.off(event, listener);
  }

  /**
   * Send a notification
   */
  protected async sendNotification(
    type: 'email' | 'push' | 'in-app',
    recipient: string,
    title: string,
    message: string,
    data?: Record<string, any>
  ) {
    const context = this.getContext();
    return await context.services.notifications.send({
      type,
      recipient,
      title,
      message,
      data
    });
  }

  /**
   * Track an analytics event
   */
  protected async trackEvent(event: string, properties?: Record<string, any>): Promise<void> {
    const context = this.getContext();
    await context.services.analytics.track(event, properties);
  }

  /**
   * Search files and metadata
   */
  protected async searchFiles(query: string, filters?: Record<string, any>) {
    const context = this.getContext();
    return await context.services.metadata.search(query, filters);
  }

  /**
   * Watch for file changes
   */
  protected async watchFiles(
    path: string,
    callback: (event: { type: string; path: string; metadata?: any }) => void
  ): Promise<string> {
    const context = this.getContext();
    return await context.services.fileSync.watch(path, callback);
  }

  /**
   * Stop watching files
   */
  protected async unwatchFiles(watchId: string): Promise<void> {
    const context = this.getContext();
    await context.services.fileSync.unwatch(watchId);
  }

  /**
   * Validate plugin configuration against schema
   */
  protected validateConfig(config: any): boolean {
    const manifest = this.getManifest();
    if (!manifest.config?.schema) {
      return true;
    }

    // Basic validation - in a real implementation, use a JSON Schema validator
    // like Ajv or Joi
    try {
      // Placeholder for actual validation logic
      return true;
    } catch (error) {
      this.log('error', 'Configuration validation failed', { error });
      return false;
    }
  }

  /**
   * Schedule a recurring task
   */
  protected scheduleTask(
    name: string,
    schedule: string,
    task: () => Promise<void>
  ): void {
    // This would integrate with the plugin runtime's scheduler
    this.log('info', `Scheduling task: ${name} with schedule: ${schedule}`);
  }

  /**
   * Cancel a scheduled task
   */
  protected cancelTask(name: string): void {
    this.log('info', `Canceling task: ${name}`);
  }

  /**
   * Get plugin metadata
   */
  protected getPluginInfo() {
    const context = this.getContext();
    const manifest = this.getManifest();
    
    return {
      name: manifest.name,
      version: manifest.version,
      displayName: manifest.displayName,
      description: manifest.description,
      author: manifest.author,
      isActive: this.isActive,
      isLoaded: this.isLoaded,
      config: context.config
    };
  }
}

/**
 * Decorator for marking methods as API endpoints
 */
export function APIEndpoint(path: string, method: string = 'POST') {
  return function (target: any, propertyName: string, descriptor: PropertyDescriptor) {
    if (!target.constructor._apiEndpoints) {
      target.constructor._apiEndpoints = [];
    }
    
    target.constructor._apiEndpoints.push({
      path,
      method: method.toUpperCase(),
      handler: propertyName
    });
  };
}

/**
 * Decorator for marking methods as trigger handlers
 */
export function TriggerHandler(triggerType: string) {
  return function (target: any, propertyName: string, descriptor: PropertyDescriptor) {
    if (!target.constructor._triggerHandlers) {
      target.constructor._triggerHandlers = {};
    }
    
    target.constructor._triggerHandlers[triggerType] = propertyName;
  };
}

/**
 * Decorator for validating method parameters
 */
export function ValidateParams(schema: Record<string, any>) {
  return function (target: any, propertyName: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;
    
    descriptor.value = function (...args: any[]) {
      // Validate parameters against schema
      // This would integrate with a validation library
      return originalMethod.apply(this, args);
    };
  };
}

export default Plugin;