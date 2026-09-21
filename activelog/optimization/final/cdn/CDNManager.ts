/**
 * CDN Asset Delivery Configuration System
 * Manages multiple CDN providers with intelligent failover and optimization
 */

interface CDNProvider {
  name: string;
  baseUrl: string;
  regions: string[];
  priority: number;
  healthCheck: string;
  apiKey?: string;
  features: {
    imageOptimization: boolean;
    videoStreaming: boolean;
    compression: boolean;
    caching: boolean;
    analytics: boolean;
  };
}

interface AssetConfig {
  type: 'image' | 'video' | 'audio' | 'document' | 'font' | 'css' | 'js';
  path: string;
  optimizations: {
    resize?: { width?: number; height?: number; quality?: number };
    format?: 'webp' | 'avif' | 'jpg' | 'png';
    lazy?: boolean;
    preload?: boolean;
    responsive?: boolean;
  };
  cacheControl: {
    maxAge: number;
    public: boolean;
    immutable?: boolean;
  };
}

interface CDNAnalytics {
  provider: string;
  requests: number;
  bandwidth: number;
  hitRate: number;
  avgResponseTime: number;
  errors: number;
  lastUpdated: Date;
}

class CDNManager {
  private providers: Map<string, CDNProvider> = new Map();
  private analytics: Map<string, CDNAnalytics> = new Map();
  private healthStatus: Map<string, boolean> = new Map();
  private assetConfigs: Map<string, AssetConfig> = new Map();
  private fallbackOrder: string[] = [];

  constructor() {
    this.initializeProviders();
    this.startHealthMonitoring();
  }

  /**
   * Initialize CDN providers configuration
   */
  private initializeProviders(): void {
    // CloudFront configuration
    this.providers.set('cloudfront', {
      name: 'Amazon CloudFront',
      baseUrl: 'https://d1234567890.cloudfront.net',
      regions: ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'],
      priority: 1,
      healthCheck: '/health',
      features: {
        imageOptimization: true,
        videoStreaming: true,
        compression: true,
        caching: true,
        analytics: true
      }
    });

    // Cloudflare configuration
    this.providers.set('cloudflare', {
      name: 'Cloudflare',
      baseUrl: 'https://activelog.cdn.cloudflare.net',
      regions: ['global'],
      priority: 2,
      healthCheck: '/health',
      features: {
        imageOptimization: true,
        videoStreaming: true,
        compression: true,
        caching: true,
        analytics: true
      }
    });

    // Fastly configuration
    this.providers.set('fastly', {
      name: 'Fastly',
      baseUrl: 'https://activelog.global.ssl.fastly.net',
      regions: ['global'],
      priority: 3,
      healthCheck: '/health',
      features: {
        imageOptimization: true,
        videoStreaming: false,
        compression: true,
        caching: true,
        analytics: true
      }
    });

    this.fallbackOrder = ['cloudfront', 'cloudflare', 'fastly'];
  }

  /**
   * Generate optimized asset URL with CDN
   */
  getAssetUrl(
    path: string,
    options: {
      type?: AssetConfig['type'];
      width?: number;
      height?: number;
      quality?: number;
      format?: string;
      provider?: string;
    } = {}
  ): string {
    const provider = this.selectProvider(options.provider);
    if (!provider) {
      return path; // Fallback to original path
    }

    let url = `${provider.baseUrl}${path}`;
    const params = new URLSearchParams();

    // Image optimization parameters
    if (options.type === 'image' && provider.features.imageOptimization) {
      if (options.width) params.set('w', options.width.toString());
      if (options.height) params.set('h', options.height.toString());
      if (options.quality) params.set('q', options.quality.toString());
      if (options.format) params.set('f', options.format);
    }

    if (params.toString()) {
      url += '?' + params.toString();
    }

    return url;
  }

  /**
   * Generate responsive image srcSet
   */
  getResponsiveImageSrcSet(
    path: string,
    breakpoints: number[] = [320, 640, 768, 1024, 1280, 1920],
    options: {
      quality?: number;
      format?: string;
      provider?: string;
    } = {}
  ): string {
    const srcSet = breakpoints.map(width => {
      const url = this.getAssetUrl(path, {
        type: 'image',
        width,
        quality: options.quality || 85,
        format: options.format || 'webp',
        provider: options.provider
      });
      return `${url} ${width}w`;
    });

    return srcSet.join(', ');
  }

  /**
   * Generate optimized video streaming URLs
   */
  getVideoStreamingUrls(
    path: string,
    qualities: Array<{ resolution: string; bitrate: number }> = [
      { resolution: '720p', bitrate: 2500 },
      { resolution: '1080p', bitrate: 5000 },
      { resolution: '4K', bitrate: 15000 }
    ],
    options: {
      provider?: string;
      format?: 'mp4' | 'webm' | 'hls';
    } = {}
  ): Record<string, string> {
    const provider = this.selectProvider(options.provider);
    if (!provider?.features.videoStreaming) {
      return { default: path };
    }

    const urls: Record<string, string> = {};
    
    qualities.forEach(({ resolution, bitrate }) => {
      const params = new URLSearchParams();
      params.set('resolution', resolution);
      params.set('bitrate', bitrate.toString());
      if (options.format) params.set('format', options.format);

      urls[resolution] = `${provider.baseUrl}${path}?${params.toString()}`;
    });

    return urls;
  }

  /**
   * Select best available CDN provider
   */
  private selectProvider(preferredProvider?: string): CDNProvider | null {
    // Use preferred provider if specified and healthy
    if (preferredProvider && this.healthStatus.get(preferredProvider)) {
      return this.providers.get(preferredProvider) || null;
    }

    // Find first healthy provider by priority
    for (const providerName of this.fallbackOrder) {
      if (this.healthStatus.get(providerName)) {
        return this.providers.get(providerName) || null;
      }
    }

    return null;
  }

  /**
   * Configure asset-specific settings
   */
  configureAsset(path: string, config: AssetConfig): void {
    this.assetConfigs.set(path, config);
  }

  /**
   * Get preload links for critical assets
   */
  getPreloadLinks(criticalAssets: Array<{ path: string; type: AssetConfig['type']; priority?: 'high' | 'low' }>): string[] {
    const links: string[] = [];

    criticalAssets.forEach(asset => {
      const config = this.assetConfigs.get(asset.path);
      if (config?.optimizations.preload) {
        const url = this.getAssetUrl(asset.path, { type: asset.type });
        const linkType = this.getLinkType(asset.type);
        const priority = asset.priority || 'high';
        
        links.push(`<${url}>; rel=preload; as=${linkType}; fetchpriority=${priority}`);
      }
    });

    return links;
  }

  private getLinkType(assetType: AssetConfig['type']): string {
    const typeMap: Record<AssetConfig['type'], string> = {
      'image': 'image',
      'video': 'video',
      'audio': 'audio',
      'font': 'font',
      'css': 'style',
      'js': 'script',
      'document': 'document'
    };
    return typeMap[assetType] || 'fetch';
  }

  /**
   * Generate cache headers for assets
   */
  getCacheHeaders(path: string): Record<string, string> {
    const config = this.assetConfigs.get(path);
    if (!config) {
      return {
        'Cache-Control': 'public, max-age=3600'
      };
    }

    const cacheControl = [
      config.cacheControl.public ? 'public' : 'private',
      `max-age=${config.cacheControl.maxAge}`,
    ];

    if (config.cacheControl.immutable) {
      cacheControl.push('immutable');
    }

    return {
      'Cache-Control': cacheControl.join(', '),
      'Expires': new Date(Date.now() + config.cacheControl.maxAge * 1000).toUTCString()
    };
  }

  /**
   * Start health monitoring for CDN providers
   */
  private startHealthMonitoring(): void {
    const checkInterval = 60000; // 1 minute

    const checkHealth = async () => {
      for (const [name, provider] of this.providers.entries()) {
        try {
          const response = await fetch(`${provider.baseUrl}${provider.healthCheck}`, {
            method: 'HEAD',
            timeout: 5000
          });
          
          this.healthStatus.set(name, response.ok);
          
          // Update analytics
          this.updateAnalytics(name, {
            avgResponseTime: response.ok ? Date.now() - performance.now() : 0,
            errors: response.ok ? 0 : 1
          });

        } catch (error) {
          this.healthStatus.set(name, false);
          this.updateAnalytics(name, { errors: 1 });
        }
      }
    };

    // Initial health check
    checkHealth();

    // Periodic health checks
    setInterval(checkHealth, checkInterval);
  }

  /**
   * Update provider analytics
   */
  private updateAnalytics(provider: string, metrics: Partial<CDNAnalytics>): void {
    const existing = this.analytics.get(provider) || {
      provider,
      requests: 0,
      bandwidth: 0,
      hitRate: 0,
      avgResponseTime: 0,
      errors: 0,
      lastUpdated: new Date()
    };

    this.analytics.set(provider, {
      ...existing,
      ...metrics,
      lastUpdated: new Date()
    });
  }

  /**
   * Get CDN performance analytics
   */
  getAnalytics(): CDNAnalytics[] {
    return Array.from(this.analytics.values());
  }

  /**
   * Get CDN health status
   */
  getHealthStatus(): Record<string, boolean> {
    return Object.fromEntries(this.healthStatus.entries());
  }

  /**
   * Invalidate CDN cache for specific paths
   */
  async invalidateCache(paths: string[], provider?: string): Promise<void> {
    const providers = provider 
      ? [this.providers.get(provider)!].filter(Boolean)
      : Array.from(this.providers.values());

    const invalidationPromises = providers.map(async (p) => {
      // CloudFront invalidation
      if (p.name === 'Amazon CloudFront' && p.apiKey) {
        return this.invalidateCloudFront(paths, p);
      }
      
      // Cloudflare cache purge
      if (p.name === 'Cloudflare' && p.apiKey) {
        return this.invalidateCloudflare(paths, p);
      }

      // Generic cache invalidation
      return this.invalidateGeneric(paths, p);
    });

    await Promise.allSettled(invalidationPromises);
  }

  private async invalidateCloudFront(paths: string[], provider: CDNProvider): Promise<void> {
    // CloudFront invalidation API call
    const aws = await import('aws-sdk');
    const cloudfront = new aws.CloudFront();

    await cloudfront.createInvalidation({
      DistributionId: provider.apiKey!, // Distribution ID
      InvalidationBatch: {
        CallerReference: Date.now().toString(),
        Paths: {
          Quantity: paths.length,
          Items: paths
        }
      }
    }).promise();
  }

  private async invalidateCloudflare(paths: string[], provider: CDNProvider): Promise<void> {
    // Cloudflare cache purge API
    const response = await fetch('https://api.cloudflare.com/client/v4/zones/zone_id/purge_cache', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${provider.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        files: paths.map(path => `${provider.baseUrl}${path}`)
      })
    });

    if (!response.ok) {
      throw new Error(`Cloudflare cache invalidation failed: ${response.statusText}`);
    }
  }

  private async invalidateGeneric(paths: string[], provider: CDNProvider): Promise<void> {
    // Generic cache invalidation (PURGE method)
    const purgePromises = paths.map(path =>
      fetch(`${provider.baseUrl}${path}`, {
        method: 'PURGE',
        headers: provider.apiKey ? {
          'Authorization': `Bearer ${provider.apiKey}`
        } : {}
      })
    );

    await Promise.allSettled(purgePromises);
  }

  /**
   * Configure CDN provider
   */
  addProvider(name: string, config: CDNProvider): void {
    this.providers.set(name, config);
    this.healthStatus.set(name, true); // Assume healthy initially
    
    // Update fallback order based on priority
    this.fallbackOrder = Array.from(this.providers.entries())
      .sort(([,a], [,b]) => a.priority - b.priority)
      .map(([name]) => name);
  }

  /**
   * Remove CDN provider
   */
  removeProvider(name: string): void {
    this.providers.delete(name);
    this.healthStatus.delete(name);
    this.analytics.delete(name);
    this.fallbackOrder = this.fallbackOrder.filter(p => p !== name);
  }

  /**
   * Get comprehensive CDN status
   */
  getStatus(): {
    providers: Array<{
      name: string;
      healthy: boolean;
      priority: number;
      features: CDNProvider['features'];
    }>;
    totalRequests: number;
    totalBandwidth: number;
    avgHitRate: number;
  } {
    const providers = Array.from(this.providers.entries()).map(([name, config]) => ({
      name: config.name,
      healthy: this.healthStatus.get(name) || false,
      priority: config.priority,
      features: config.features
    }));

    const analytics = Array.from(this.analytics.values());
    const totalRequests = analytics.reduce((sum, a) => sum + a.requests, 0);
    const totalBandwidth = analytics.reduce((sum, a) => sum + a.bandwidth, 0);
    const avgHitRate = analytics.length > 0 
      ? analytics.reduce((sum, a) => sum + a.hitRate, 0) / analytics.length 
      : 0;

    return {
      providers,
      totalRequests,
      totalBandwidth,
      avgHitRate
    };
  }
}

// Singleton instance
export const cdnManager = new CDNManager();

// React hook for CDN asset URLs
export const useCDNAsset = (path: string, options: Parameters<CDNManager['getAssetUrl']>[1] = {}) => {
  const [url, setUrl] = React.useState(path);

  React.useEffect(() => {
    const cdnUrl = cdnManager.getAssetUrl(path, options);
    setUrl(cdnUrl);
  }, [path, JSON.stringify(options)]);

  return url;
};

// React hook for responsive images
export const useResponsiveImage = (
  path: string, 
  breakpoints?: number[], 
  options?: Parameters<CDNManager['getResponsiveImageSrcSet']>[2]
) => {
  const [srcSet, setSrcSet] = React.useState('');

  React.useEffect(() => {
    const responsiveSrcSet = cdnManager.getResponsiveImageSrcSet(path, breakpoints, options);
    setSrcSet(responsiveSrcSet);
  }, [path, JSON.stringify(breakpoints), JSON.stringify(options)]);

  return {
    src: cdnManager.getAssetUrl(path, { type: 'image', ...options }),
    srcSet
  };
};

export default CDNManager;