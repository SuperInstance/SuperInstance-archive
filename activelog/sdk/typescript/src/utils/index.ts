/**
 * ActiveLog Plugin SDK - Utilities
 */

import { PluginManifest, ValidationError } from '../types';

/**
 * Validate plugin manifest against schema
 */
export function validateManifest(manifest: any): PluginManifest {
  const errors: string[] = [];

  // Required fields
  if (!manifest.name) errors.push('name is required');
  if (!manifest.version) errors.push('version is required');
  if (!manifest.description) errors.push('description is required');
  if (!manifest.main) errors.push('main is required');
  if (!manifest.runtime) errors.push('runtime is required');
  if (!manifest.permissions) errors.push('permissions is required');

  // Validate name format
  if (manifest.name && !/^[a-z][a-z0-9-]*$/.test(manifest.name)) {
    errors.push('name must be lowercase with hyphens only');
  }

  // Validate version format
  if (manifest.version && !/^\d+\.\d+\.\d+/.test(manifest.version)) {
    errors.push('version must be in semver format (x.y.z)');
  }

  // Validate category
  const validCategories = [
    'data-import', 'data-export', 'analytics', 'automation',
    'integration', 'utility', 'visualization', 'ai-ml',
    'security', 'productivity'
  ];
  
  if (manifest.category && !validCategories.includes(manifest.category)) {
    errors.push(`category must be one of: ${validCategories.join(', ')}`);
  }

  if (errors.length > 0) {
    throw new ValidationError('manifest', errors.join('; '));
  }

  return manifest as PluginManifest;
}

/**
 * Generate plugin template
 */
export function generatePluginTemplate(options: {
  name: string;
  displayName?: string;
  description: string;
  author: string;
  category: string;
  runtime: 'typescript' | 'python';
}): { manifest: PluginManifest; code: string } {
  const manifest: PluginManifest = {
    name: options.name,
    version: '1.0.0',
    displayName: options.displayName || options.name,
    description: options.description,
    author: {
      name: options.author
    },
    category: options.category as any,
    main: options.runtime === 'typescript' ? 'index.js' : 'main.py',
    runtime: {
      type: options.runtime,
      environment: options.runtime === 'typescript' ? 'node' : 'python3'
    },
    permissions: {
      network: { enabled: false },
      filesystem: { temp: true },
      database: { read: false, write: false },
      services: []
    },
    resources: {
      cpu: 0.5,
      memory: '256MB',
      disk: '100MB',
      timeout: 60
    }
  };

  const code = options.runtime === 'typescript' 
    ? generateTypeScriptTemplate(manifest)
    : generatePythonTemplate(manifest);

  return { manifest, code };
}

function generateTypeScriptTemplate(manifest: PluginManifest): string {
  return `import { Plugin, PluginManifest, PluginContext, TriggerEvent, TriggerResult } from '@activelog/plugin-sdk';

export default class ${toPascalCase(manifest.name)}Plugin extends Plugin {
  getManifest(): PluginManifest {
    return ${JSON.stringify(manifest, null, 2)};
  }

  async onLoad(context: PluginContext): Promise<void> {
    super.onLoad?.(context);
    this.log('info', '${manifest.displayName} plugin loaded');
  }

  async onActivate(context: PluginContext): Promise<void> {
    super.onActivate?.(context);
    this.log('info', '${manifest.displayName} plugin activated');
    
    // Initialize your plugin here
  }

  async onTrigger(event: TriggerEvent, context: PluginContext): Promise<TriggerResult> {
    this.log('info', 'Trigger received', { type: event.type });
    
    try {
      // Handle trigger event
      switch (event.type) {
        case 'file-upload':
          return await this.handleFileUpload(event.data);
        case 'schedule':
          return await this.handleScheduledTask(event.data);
        default:
          return { success: false, error: 'Unsupported trigger type' };
      }
    } catch (error) {
      this.log('error', 'Trigger execution failed', error);
      return { success: false, error: (error as Error).message };
    }
  }

  private async handleFileUpload(data: any): Promise<TriggerResult> {
    // Implement file upload handling
    this.log('info', 'Handling file upload', data);
    return { success: true };
  }

  private async handleScheduledTask(data: any): Promise<TriggerResult> {
    // Implement scheduled task handling
    this.log('info', 'Handling scheduled task', data);
    return { success: true };
  }
}`;
}

function generatePythonTemplate(manifest: PluginManifest): string {
  return `import asyncio
import logging
from typing import Any, Dict
from activelog_plugin_sdk import Plugin, PluginContext, TriggerEvent, TriggerResult

class ${toPascalCase(manifest.name)}Plugin(Plugin):
    def get_manifest(self) -> Dict[str, Any]:
        return ${JSON.stringify(manifest, null, 4).replace(/"/g, "'")}

    async def on_load(self, context: PluginContext) -> None:
        await super().on_load(context)
        self.log('info', '${manifest.displayName} plugin loaded')

    async def on_activate(self, context: PluginContext) -> None:
        await super().on_activate(context)
        self.log('info', '${manifest.displayName} plugin activated')
        
        # Initialize your plugin here

    async def on_trigger(self, event: TriggerEvent, context: PluginContext) -> TriggerResult:
        self.log('info', f'Trigger received: {event.type}')
        
        try:
            # Handle trigger event
            if event.type == 'file-upload':
                return await self.handle_file_upload(event.data)
            elif event.type == 'schedule':
                return await self.handle_scheduled_task(event.data)
            else:
                return TriggerResult(success=False, error='Unsupported trigger type')
        except Exception as error:
            self.log('error', f'Trigger execution failed: {str(error)}')
            return TriggerResult(success=False, error=str(error))

    async def handle_file_upload(self, data: Any) -> TriggerResult:
        # Implement file upload handling
        self.log('info', f'Handling file upload: {data}')
        return TriggerResult(success=True)

    async def handle_scheduled_task(self, data: Any) -> TriggerResult:
        # Implement scheduled task handling
        self.log('info', f'Handling scheduled task: {data}')
        return TriggerResult(success=True)

# Export plugin class
plugin_class = ${toPascalCase(manifest.name)}Plugin`;
}

/**
 * Convert kebab-case to PascalCase
 */
export function toPascalCase(str: string): string {
  return str
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join('');
}

/**
 * Convert PascalCase to kebab-case
 */
export function toKebabCase(str: string): string {
  return str
    .replace(/([A-Z])/g, '-$1')
    .toLowerCase()
    .replace(/^-/, '');
}

/**
 * Parse memory size to bytes
 */
export function parseMemorySize(size: string): number {
  const match = size.match(/^(\d+(?:\.\d+)?)\s*([KMGT]?)B?$/i);
  if (!match) {
    throw new ValidationError('memory', 'Invalid memory size format');
  }

  const value = parseFloat(match[1]);
  const unit = match[2].toUpperCase();

  const multipliers = {
    '': 1,
    'K': 1024,
    'M': 1024 * 1024,
    'G': 1024 * 1024 * 1024,
    'T': 1024 * 1024 * 1024 * 1024
  };

  return value * (multipliers[unit as keyof typeof multipliers] || 1);
}

/**
 * Format bytes to human readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Validate semantic version
 */
export function isValidSemver(version: string): boolean {
  const semverRegex = /^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$/;
  return semverRegex.test(version);
}

/**
 * Compare semantic versions
 */
export function compareSemver(version1: string, version2: string): number {
  const parts1 = version1.split('.').map(Number);
  const parts2 = version2.split('.').map(Number);

  for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
    const part1 = parts1[i] || 0;
    const part2 = parts2[i] || 0;

    if (part1 > part2) return 1;
    if (part1 < part2) return -1;
  }

  return 0;
}

/**
 * Check if version satisfies range
 */
export function satisfiesRange(version: string, range: string): boolean {
  // Simple implementation - in production use a proper semver library
  if (range.startsWith('^')) {
    const baseVersion = range.slice(1);
    return compareSemver(version, baseVersion) >= 0;
  }
  
  if (range.startsWith('~')) {
    const baseVersion = range.slice(1);
    return compareSemver(version, baseVersion) >= 0;
  }

  return version === range;
}

/**
 * Generate unique plugin ID
 */
export function generatePluginId(name: string, version: string): string {
  return `${name}@${version}`;
}

/**
 * Parse plugin ID
 */
export function parsePluginId(pluginId: string): { name: string; version: string } {
  const parts = pluginId.split('@');
  if (parts.length !== 2) {
    throw new ValidationError('pluginId', 'Invalid plugin ID format');
  }

  return {
    name: parts[0],
    version: parts[1]
  };
}

/**
 * Sanitize plugin name for use as identifier
 */
export function sanitizePluginName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

/**
 * Check if plugin has required permission
 */
export function hasPermission(manifest: PluginManifest, permission: string): boolean {
  const permissions = manifest.permissions;
  
  switch (permission) {
    case 'network':
      return permissions.network?.enabled === true;
    case 'database:read':
      return permissions.database?.read === true;
    case 'database:write':
      return permissions.database?.write === true;
    case 'filesystem:read':
      return Array.isArray(permissions.filesystem?.read);
    case 'filesystem:write':
      return Array.isArray(permissions.filesystem?.write);
    default:
      return false;
  }
}

/**
 * Calculate plugin resource requirements
 */
export function calculateResourceRequirements(manifest: PluginManifest) {
  const resources = manifest.resources || {};
  
  return {
    cpu: resources.cpu || 0.5,
    memoryBytes: parseMemorySize(resources.memory || '256MB'),
    diskBytes: parseMemorySize(resources.disk || '100MB'),
    networkBytes: parseMemorySize(resources.network || '10MB'),
    timeoutMs: (resources.timeout || 60) * 1000
  };
}