/**
 * ActiveLog Plugin SDK - Main Export
 */

// Core classes
export { Plugin, APIEndpoint, TriggerHandler, ValidateParams } from './core/Plugin';
export { PluginRuntime } from './core/PluginRuntime';

// Types
export * from './types';

// Utilities
export * from './utils';

// Version
export const SDK_VERSION = '1.0.0';