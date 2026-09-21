/**
 * Edge Cache Optimization System
 * Advanced caching strategies for CDN edge locations with intelligent purging
 */

interface CacheRule {
  pattern: string | RegExp;
  ttl: number;
  tags: string[];
  conditions?: {
    headers?: Record<string, string | RegExp>;
    query?: Record<string, string | RegExp>;
    method?: string[];
  };
  behavior: {
    cacheByDevice?: boolean;
    cacheByGeo?: boolean;
    cacheByUser?: boolean;
    respectOriginHeaders?: boolean;
    staleWhileRevalidate?: number;
    staleIfError?: number;
  };
}

interface CacheStats {
  hitRate: number;
  missRate: number;
  requests: number;
  bandwidth: number;
  origin_requests: number;
  edge_requests: number;
  regions: Record<string, {
    hits: number;
    misses: number;
    bandwidth: number;
  }>;
}

interface PurgeStrategy {
  type: 'immediate' | 'scheduled' | 'conditional';
  conditions?: {
    minAge?: number;
    maxRequests?: number;
    errorRate?: number;
  };
  schedule?: {
    cron: string;
    timezone: string;
  };
}

class EdgeCacheOptimizer {
  private cacheRules: CacheRule[] = [];
  private purgeStrategies: Map<string, PurgeStrategy> = new Map();
  private cacheStats: Map<string, CacheStats> = new Map();
  private warmupQueue: Set<string> = new Set();
  private invalidationHistory: Array<{
    timestamp: Date;
    paths: string[];
    reason: string;
    success: boolean;
  }> = [];

  constructor() {
    this.initializeDefaultRules();
    this.setupPurgeStrategies();
  }

  /**
   * Initialize default cache rules for different content types
   */
  private initializeDefaultRules(): void {
    // Static assets - long cache
    this.addCacheRule({
      pattern: /\.(js|css|woff2?|ttf|otf)(\?.*)?$/,
      ttl: 31536000, // 1 year
      tags: ['static', 'assets'],
      behavior: {
        respectOriginHeaders: false,
        staleWhileRevalidate: 86400, // 1 day
        staleIfError: 604800 // 1 week
      }
    });

    // Images - medium cache
    this.addCacheRule({
      pattern: /\.(png|jpg|jpeg|gif|webp|avif|svg)(\?.*)?$/,
      ttl: 2592000, // 30 days
      tags: ['images'],
      behavior: {
        cacheByDevice: true,
        respectOriginHeaders: true,
        staleWhileRevalidate: 3600, // 1 hour
        staleIfError: 86400 // 1 day
      }
    });

    // API responses - short cache with conditions
    this.addCacheRule({
      pattern: /^\/api\//,
      ttl: 300, // 5 minutes
      tags: ['api'],
      conditions: {
        method: ['GET'],
        headers: {
          'authorization': /^(?!Bearer)/i // Don't cache authenticated requests
        }
      },
      behavior: {
        cacheByUser: false,
        respectOriginHeaders: true,
        staleWhileRevalidate: 60,
        staleIfError: 300
      }
    });

    // HTML pages - short cache
    this.addCacheRule({
      pattern: /\.html?(\?.*)?$/,
      ttl: 3600, // 1 hour
      tags: ['html', 'pages'],
      behavior: {
        cacheByDevice: true,
        cacheByGeo: false,
        respectOriginHeaders: true,
        staleWhileRevalidate: 300,
        staleIfError: 3600
      }
    });

    // Fonts - very long cache
    this.addCacheRule({
      pattern: /\.(woff2?|ttf|otf|eot)(\?.*)?$/,
      ttl: 63072000, // 2 years
      tags: ['fonts'],
      behavior: {
        respectOriginHeaders: false,
        staleIfError: 2592000 // 30 days
      }
    });

    // Videos - long cache
    this.addCacheRule({
      pattern: /\.(mp4|webm|ogg|avi|mov)(\?.*)?$/,
      ttl: 7776000, // 90 days
      tags: ['video'],
      behavior: {
        cacheByDevice: true,
        respectOriginHeaders: true,
        staleWhileRevalidate: 86400,
        staleIfError: 604800
      }
    });
  }

  /**
   * Setup intelligent purge strategies
   */
  private setupPurgeStrategies(): void {
    // Immediate purge for critical content
    this.purgeStrategies.set('critical', {
      type: 'immediate',
      conditions: {
        minAge: 0,
        maxRequests: 0
      }
    });

    // Scheduled purge for regular maintenance
    this.purgeStrategies.set('maintenance', {
      type: 'scheduled',
      schedule: {
        cron: '0 2 * * *', // Daily at 2 AM
        timezone: 'UTC'
      }
    });

    // Conditional purge based on performance
    this.purgeStrategies.set('performance', {
      type: 'conditional',
      conditions: {
        minAge: 3600, // 1 hour
        errorRate: 0.05 // 5% error rate
      }
    });
  }

  /**
   * Add cache rule for specific content patterns
   */
  addCacheRule(rule: CacheRule): void {
    this.cacheRules.push(rule);
    
    // Sort rules by specificity (more specific patterns first)
    this.cacheRules.sort((a, b) => {
      const aSpecific = typeof a.pattern === 'string' ? a.pattern.length : 0;
      const bSpecific = typeof b.pattern === 'string' ? b.pattern.length : 0;
      return bSpecific - aSpecific;
    });
  }

  /**
   * Get cache configuration for a given request
   */
  getCacheConfig(
    url: string,
    method: string = 'GET',
    headers: Record<string, string> = {},
    query: Record<string, string> = {}
  ): {
    shouldCache: boolean;
    ttl: number;
    tags: string[];
    behavior: CacheRule['behavior'];
  } {
    const defaultConfig = {
      shouldCache: false,
      ttl: 0,
      tags: [],
      behavior: {}
    };

    for (const rule of this.cacheRules) {
      const patternMatch = typeof rule.pattern === 'string' 
        ? url.includes(rule.pattern)
        : rule.pattern.test(url);

      if (!patternMatch) continue;

      // Check conditions
      if (rule.conditions) {
        // Method check
        if (rule.conditions.method && !rule.conditions.method.includes(method)) {
          continue;
        }

        // Header checks
        if (rule.conditions.headers) {
          const headerMatch = Object.entries(rule.conditions.headers).every(([key, pattern]) => {
            const headerValue = headers[key.toLowerCase()];
            if (!headerValue) return false;
            
            return typeof pattern === 'string' 
              ? headerValue === pattern
              : pattern.test(headerValue);
          });
          if (!headerMatch) continue;
        }

        // Query parameter checks
        if (rule.conditions.query) {
          const queryMatch = Object.entries(rule.conditions.query).every(([key, pattern]) => {
            const queryValue = query[key];
            if (!queryValue) return false;
            
            return typeof pattern === 'string'
              ? queryValue === pattern
              : pattern.test(queryValue);
          });
          if (!queryMatch) continue;
        }
      }

      // Rule matches, return configuration
      return {
        shouldCache: true,
        ttl: rule.ttl,
        tags: rule.tags,
        behavior: rule.behavior
      };
    }

    return defaultConfig;
  }

  /**
   * Generate cache headers for response
   */
  generateCacheHeaders(
    url: string,
    method: string = 'GET',
    headers: Record<string, string> = {},
    query: Record<string, string> = {}
  ): Record<string, string> {
    const config = this.getCacheConfig(url, method, headers, query);
    
    if (!config.shouldCache) {
      return {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      };
    }

    const cacheControlDirectives = ['public'];
    cacheControlDirectives.push(`max-age=${config.ttl}`);

    if (config.behavior.staleWhileRevalidate) {
      cacheControlDirectives.push(`stale-while-revalidate=${config.behavior.staleWhileRevalidate}`);
    }

    if (config.behavior.staleIfError) {
      cacheControlDirectives.push(`stale-if-error=${config.behavior.staleIfError}`);
    }

    const headers_output: Record<string, string> = {
      'Cache-Control': cacheControlDirectives.join(', '),
      'Expires': new Date(Date.now() + config.ttl * 1000).toUTCString()
    };

    if (config.tags.length > 0) {
      headers_output['Cache-Tag'] = config.tags.join(',');
    }

    // Add Vary headers based on behavior
    const varyHeaders: string[] = [];
    if (config.behavior.cacheByDevice) varyHeaders.push('User-Agent');
    if (config.behavior.cacheByGeo) varyHeaders.push('CloudFront-Viewer-Country');
    if (config.behavior.cacheByUser) varyHeaders.push('Authorization');
    
    if (varyHeaders.length > 0) {
      headers_output['Vary'] = varyHeaders.join(', ');
    }

    return headers_output;
  }

  /**
   * Intelligent cache invalidation by tags
   */
  async invalidateByTags(
    tags: string[], 
    strategy: string = 'immediate',
    reason: string = 'Manual invalidation'
  ): Promise<void> {
    const purgeStrategy = this.purgeStrategies.get(strategy);
    if (!purgeStrategy) {
      throw new Error(`Unknown purge strategy: ${strategy}`);
    }

    const affectedPaths = this.findPathsByTags(tags);
    
    try {
      switch (purgeStrategy.type) {
        case 'immediate':
          await this.executeImmediatePurge(affectedPaths);
          break;
        case 'scheduled':
          this.scheduleDelayedPurge(affectedPaths, purgeStrategy);
          break;
        case 'conditional':
          await this.executeConditionalPurge(affectedPaths, purgeStrategy);
          break;
      }

      this.recordInvalidation(affectedPaths, reason, true);
    } catch (error) {
      this.recordInvalidation(affectedPaths, reason, false);
      throw error;
    }
  }

  /**
   * Find cached paths by tags
   */
  private findPathsByTags(tags: string[]): string[] {
    const paths: Set<string> = new Set();
    
    for (const rule of this.cacheRules) {
      const hasMatchingTag = rule.tags.some(tag => tags.includes(tag));
      if (hasMatchingTag && typeof rule.pattern === 'string') {
        paths.add(rule.pattern);
      }
    }

    return Array.from(paths);
  }

  /**
   * Execute immediate cache purge
   */
  private async executeImmediatePurge(paths: string[]): Promise<void> {
    // Implementation would depend on CDN provider API
    const purgePromises = paths.map(async (path) => {
      // Example: CloudFlare API call
      // await this.purgeCloudflareCache([path]);
      
      // Example: CloudFront invalidation
      // await this.invalidateCloudFrontCache([path]);
      
      console.log(`Purging cache for: ${path}`);
    });

    await Promise.all(purgePromises);
  }

  /**
   * Schedule delayed purge
   */
  private scheduleDelayedPurge(paths: string[], strategy: PurgeStrategy): void {
    if (!strategy.schedule) return;

    // Implementation would use cron job scheduler
    console.log(`Scheduled purge for ${paths.length} paths at ${strategy.schedule.cron}`);
  }

  /**
   * Execute conditional purge based on performance metrics
   */
  private async executeConditionalPurge(paths: string[], strategy: PurgeStrategy): Promise<void> {
    if (!strategy.conditions) return;

    const shouldPurge = await this.evaluatePurgeConditions(paths, strategy.conditions);
    
    if (shouldPurge) {
      await this.executeImmediatePurge(paths);
    }
  }

  /**
   * Evaluate purge conditions
   */
  private async evaluatePurgeConditions(
    paths: string[], 
    conditions: NonNullable<PurgeStrategy['conditions']>
  ): Promise<boolean> {
    // Check minimum age
    if (conditions.minAge) {
      const oldestCacheAge = await this.getOldestCacheAge(paths);
      if (oldestCacheAge < conditions.minAge) {
        return false;
      }
    }

    // Check error rate
    if (conditions.errorRate) {
      const currentErrorRate = await this.getCurrentErrorRate(paths);
      if (currentErrorRate < conditions.errorRate) {
        return false;
      }
    }

    return true;
  }

  /**
   * Get oldest cache age for paths
   */
  private async getOldestCacheAge(paths: string[]): Promise<number> {
    // Mock implementation - would query CDN cache metadata
    return Math.random() * 7200; // Random age up to 2 hours
  }

  /**
   * Get current error rate for paths
   */
  private async getCurrentErrorRate(paths: string[]): Promise<number> {
    // Mock implementation - would query CDN analytics
    return Math.random() * 0.1; // Random error rate up to 10%
  }

  /**
   * Record invalidation for audit trail
   */
  private recordInvalidation(paths: string[], reason: string, success: boolean): void {
    this.invalidationHistory.push({
      timestamp: new Date(),
      paths,
      reason,
      success
    });

    // Keep only last 1000 records
    if (this.invalidationHistory.length > 1000) {
      this.invalidationHistory = this.invalidationHistory.slice(-1000);
    }
  }

  /**
   * Cache warming for critical paths
   */
  async warmCache(paths: string[], priority: 'high' | 'medium' | 'low' = 'medium'): Promise<void> {
    const warmupRequests = paths.map(async (path) => {
      try {
        const response = await fetch(path, {
          method: 'HEAD',
          headers: {
            'X-Cache-Warmup': 'true',
            'X-Priority': priority
          }
        });

        if (response.ok) {
          console.log(`Cache warmed for: ${path}`);
        }
      } catch (error) {
        console.warn(`Failed to warm cache for: ${path}`, error);
      }
    });

    await Promise.allSettled(warmupRequests);
  }

  /**
   * Analyze cache performance
   */
  analyzeCachePerformance(): {
    overallHitRate: number;
    recommendations: Array<{
      type: 'increase_ttl' | 'decrease_ttl' | 'add_tags' | 'modify_behavior';
      rule: string;
      reason: string;
      impact: 'high' | 'medium' | 'low';
    }>;
    topMissedContent: Array<{ path: string; misses: number; potential_savings: number }>;
  } {
    // Mock analysis - would use real cache statistics
    const hitRates = Array.from(this.cacheStats.values()).map(s => s.hitRate);
    const overallHitRate = hitRates.length > 0 
      ? hitRates.reduce((a, b) => a + b, 0) / hitRates.length 
      : 0;

    const recommendations = [
      {
        type: 'increase_ttl' as const,
        rule: 'API responses',
        reason: 'Low cache hit rate detected for API endpoints',
        impact: 'high' as const
      },
      {
        type: 'add_tags' as const,
        rule: 'Image assets',
        reason: 'Missing cache tags for efficient invalidation',
        impact: 'medium' as const
      }
    ];

    const topMissedContent = [
      { path: '/api/user/profile', misses: 1250, potential_savings: 0.85 },
      { path: '/assets/images/hero.jpg', misses: 890, potential_savings: 0.92 }
    ];

    return {
      overallHitRate,
      recommendations,
      topMissedContent
    };
  }

  /**
   * Get cache rule statistics
   */
  getCacheRuleStats(): Array<{
    pattern: string;
    ttl: number;
    tags: string[];
    matchCount: number;
    hitRate: number;
  }> {
    return this.cacheRules.map(rule => ({
      pattern: rule.pattern.toString(),
      ttl: rule.ttl,
      tags: rule.tags,
      matchCount: Math.floor(Math.random() * 1000), // Mock data
      hitRate: Math.random()
    }));
  }

  /**
   * Export cache configuration
   */
  exportConfiguration(): {
    rules: CacheRule[];
    strategies: Record<string, PurgeStrategy>;
    version: string;
    timestamp: string;
  } {
    return {
      rules: this.cacheRules,
      strategies: Object.fromEntries(this.purgeStrategies.entries()),
      version: '1.0.0',
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Import cache configuration
   */
  importConfiguration(config: ReturnType<EdgeCacheOptimizer['exportConfiguration']>): void {
    this.cacheRules = config.rules;
    this.purgeStrategies = new Map(Object.entries(config.strategies));
  }

  /**
   * Get invalidation history
   */
  getInvalidationHistory(limit: number = 100): typeof this.invalidationHistory {
    return this.invalidationHistory.slice(-limit);
  }
}

// Singleton instance
export const edgeCacheOptimizer = new EdgeCacheOptimizer();

// Express middleware for automatic cache headers
export const cacheHeadersMiddleware = () => {
  return (req: any, res: any, next: any) => {
    const originalSend = res.send.bind(res);
    
    res.send = (body: any) => {
      // Generate cache headers
      const cacheHeaders = edgeCacheOptimizer.generateCacheHeaders(
        req.originalUrl,
        req.method,
        req.headers,
        req.query
      );

      // Set headers
      Object.entries(cacheHeaders).forEach(([key, value]) => {
        res.setHeader(key, value);
      });

      return originalSend(body);
    };

    next();
  };
};

export default EdgeCacheOptimizer;