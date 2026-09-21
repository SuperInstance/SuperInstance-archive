const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { EventEmitter } = require('events');

class CDNManager extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      // CDN Provider settings
      providers: config.providers || ['cloudflare', 'aws-cloudfront', 'azure-cdn'],
      primaryProvider: config.primaryProvider || 'cloudflare',
      fallbackProviders: config.fallbackProviders || ['aws-cloudfront'],
      
      // Cache settings
      defaultTTL: config.defaultTTL || 86400, // 24 hours
      maxAge: config.maxAge || 31536000, // 1 year for static assets
      cacheBusting: config.cacheBusting ?? true,
      
      // Asset optimization
      enableCompression: config.enableCompression ?? true,
      enableMinification: config.enableMinification ?? true,
      enableImageOptimization: config.enableImageOptimization ?? true,
      
      // Performance
      enableHTTP2Push: config.enableHTTP2Push ?? true,
      enablePrefetch: config.enablePrefetch ?? true,
      enablePreload: config.enablePreload ?? true,
      
      // Security
      enableSRI: config.enableSRI ?? true, // Subresource Integrity
      enableCSP: config.enableCSP ?? true, // Content Security Policy
      
      // Monitoring
      enableAnalytics: config.enableAnalytics ?? true,
      enablePerformanceTracking: config.enablePerformanceTracking ?? true,
      
      ...config
    };

    this.providers = new Map();
    this.assetCache = new Map();
    this.performanceMetrics = new Map();
    this.purgeQueue = new Set();
    this.stats = {
      totalRequests: 0,
      cacheHits: 0,
      cacheMisses: 0,
      totalBandwidth: 0,
      avgResponseTime: 0
    };

    this.initializeProviders();
  }

  // Initialize CDN providers
  initializeProviders() {
    // Cloudflare provider
    this.providers.set('cloudflare', new CloudflareProvider({
      apiToken: this.config.cloudflare?.apiToken,
      zoneId: this.config.cloudflare?.zoneId,
      baseUrl: this.config.cloudflare?.baseUrl
    }));

    // AWS CloudFront provider
    this.providers.set('aws-cloudfront', new AWSCloudFrontProvider({
      accessKeyId: this.config.aws?.accessKeyId,
      secretAccessKey: this.config.aws?.secretAccessKey,
      distributionId: this.config.aws?.distributionId,
      baseUrl: this.config.aws?.baseUrl
    }));

    // Azure CDN provider
    this.providers.set('azure-cdn', new AzureCDNProvider({
      subscriptionId: this.config.azure?.subscriptionId,
      resourceGroupName: this.config.azure?.resourceGroupName,
      profileName: this.config.azure?.profileName,
      endpointName: this.config.azure?.endpointName
    }));
  }

  // Upload asset to CDN
  async uploadAsset(assetPath, options = {}) {
    try {
      const asset = await this.prepareAsset(assetPath, options);
      const provider = this.getProvider(options.provider);
      
      const uploadResult = await provider.uploadAsset(asset);
      
      // Update cache and metrics
      this.assetCache.set(asset.key, {
        ...uploadResult,
        uploadedAt: new Date(),
        size: asset.size,
        hash: asset.hash
      });

      this.emit('assetUploaded', uploadResult);
      return uploadResult;
      
    } catch (error) {
      this.emit('uploadError', { assetPath, error });
      throw error;
    }
  }

  // Prepare asset for CDN upload
  async prepareAsset(assetPath, options = {}) {
    const absolutePath = path.resolve(assetPath);
    const content = fs.readFileSync(absolutePath);
    const stats = fs.statSync(absolutePath);
    
    let processedContent = content;
    const contentType = this.getContentType(absolutePath);
    
    // Apply optimizations
    if (this.config.enableMinification && this.isMinifiable(contentType)) {
      processedContent = await this.minifyAsset(processedContent, contentType);
    }

    if (this.config.enableCompression) {
      processedContent = await this.compressAsset(processedContent);
    }

    // Generate hash for cache busting
    const hash = crypto.createHash('sha256').update(processedContent).digest('hex').substring(0, 8);
    const key = this.generateAssetKey(assetPath, hash);

    return {
      key,
      path: assetPath,
      content: processedContent,
      originalSize: content.length,
      size: processedContent.length,
      contentType,
      hash,
      cacheControl: this.getCacheControl(contentType),
      lastModified: stats.mtime,
      ...options
    };
  }

  // Generate asset key with cache busting
  generateAssetKey(assetPath, hash) {
    const parsedPath = path.parse(assetPath);
    
    if (this.config.cacheBusting) {
      return `${parsedPath.dir}/${parsedPath.name}.${hash}${parsedPath.ext}`;
    }
    
    return assetPath;
  }

  // Get appropriate cache control headers
  getCacheControl(contentType) {
    const staticAssets = ['image', 'font', 'application/javascript', 'text/css'];
    const isStatic = staticAssets.some(type => contentType.includes(type));
    
    if (isStatic) {
      return `public, max-age=${this.config.maxAge}, immutable`;
    }
    
    return `public, max-age=${this.config.defaultTTL}`;
  }

  // Minify asset based on content type
  async minifyAsset(content, contentType) {
    try {
      switch (true) {
        case contentType.includes('javascript'):
          return await this.minifyJavaScript(content);
        case contentType.includes('css'):
          return await this.minifyCSS(content);
        case contentType.includes('html'):
          return await this.minifyHTML(content);
        default:
          return content;
      }
    } catch (error) {
      console.warn('Minification failed, using original content:', error.message);
      return content;
    }
  }

  // Minify JavaScript
  async minifyJavaScript(content) {
    const { minify } = require('terser');
    const result = await minify(content.toString(), {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.warn']
      },
      mangle: true
    });
    
    return Buffer.from(result.code);
  }

  // Minify CSS
  async minifyCSS(content) {
    const CleanCSS = require('clean-css');
    const result = new CleanCSS({
      level: 2,
      returnPromise: true
    }).minify(content.toString());
    
    return Buffer.from((await result).styles);
  }

  // Minify HTML
  async minifyHTML(content) {
    const { minify } = require('html-minifier-terser');
    const result = await minify(content.toString(), {
      removeComments: true,
      collapseWhitespace: true,
      removeRedundantAttributes: true,
      useShortDoctype: true,
      removeEmptyAttributes: true,
      removeStyleLinkTypeAttributes: true,
      keepClosingSlash: true,
      minifyJS: true,
      minifyCSS: true,
      minifyURLs: true
    });
    
    return Buffer.from(result);
  }

  // Compress asset
  async compressAsset(content) {
    const zlib = require('zlib');
    return zlib.gzipSync(content, { level: 9 });
  }

  // Check if content type is minifiable
  isMinifiable(contentType) {
    const minifiableTypes = [
      'application/javascript',
      'text/javascript',
      'text/css',
      'text/html',
      'application/json'
    ];
    
    return minifiableTypes.some(type => contentType.includes(type));
  }

  // Get content type from file path
  getContentType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const contentTypes = {
      '.js': 'application/javascript',
      '.css': 'text/css',
      '.html': 'text/html',
      '.json': 'application/json',
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.gif': 'image/gif',
      '.svg': 'image/svg+xml',
      '.webp': 'image/webp',
      '.woff': 'font/woff',
      '.woff2': 'font/woff2',
      '.ttf': 'font/ttf',
      '.eot': 'application/vnd.ms-fontobject'
    };
    
    return contentTypes[ext] || 'application/octet-stream';
  }

  // Get CDN provider
  getProvider(providerName) {
    const name = providerName || this.config.primaryProvider;
    const provider = this.providers.get(name);
    
    if (!provider) {
      throw new Error(`CDN provider '${name}' not found`);
    }
    
    return provider;
  }

  // Purge asset from CDN cache
  async purgeAsset(assetKey, provider) {
    try {
      const cdnProvider = this.getProvider(provider);
      await cdnProvider.purgeAsset(assetKey);
      
      this.assetCache.delete(assetKey);
      this.emit('assetPurged', { assetKey, provider });
      
    } catch (error) {
      this.emit('purgeError', { assetKey, provider, error });
      throw error;
    }
  }

  // Batch purge multiple assets
  async purgeAssets(assetKeys, provider) {
    const cdnProvider = this.getProvider(provider);
    const results = [];
    
    for (const key of assetKeys) {
      try {
        await cdnProvider.purgeAsset(key);
        this.assetCache.delete(key);
        results.push({ key, success: true });
      } catch (error) {
        results.push({ key, success: false, error });
      }
    }
    
    this.emit('batchPurgeCompleted', { results, provider });
    return results;
  }

  // Generate preload headers
  generatePreloadHeaders(assets) {
    return assets.map(asset => {
      const { url, type, crossorigin } = asset;
      let header = `<${url}>; rel=preload; as=${type}`;
      
      if (crossorigin) {
        header += '; crossorigin';
      }
      
      return header;
    }).join(', ');
  }

  // Generate prefetch headers
  generatePrefetchHeaders(assets) {
    return assets.map(asset => `<${asset.url}>; rel=prefetch`).join(', ');
  }

  // Generate Subresource Integrity hash
  generateSRIHash(content) {
    const hash = crypto.createHash('sha384').update(content).digest('base64');
    return `sha384-${hash}`;
  }

  // Generate Content Security Policy
  generateCSP(options = {}) {
    const directives = {
      'default-src': ["'self'"],
      'script-src': ["'self'", "'unsafe-inline'", ...this.getCDNDomains()],
      'style-src': ["'self'", "'unsafe-inline'", ...this.getCDNDomains()],
      'img-src': ["'self'", 'data:', ...this.getCDNDomains()],
      'font-src': ["'self'", ...this.getCDNDomains()],
      'connect-src': ["'self'"],
      'frame-src': ["'none'"],
      'object-src': ["'none'"],
      ...options
    };

    return Object.entries(directives)
      .map(([key, values]) => `${key} ${values.join(' ')}`)
      .join('; ');
  }

  // Get CDN domains for CSP
  getCDNDomains() {
    const domains = [];
    
    for (const [name, provider] of this.providers) {
      if (provider.getDomain) {
        domains.push(provider.getDomain());
      }
    }
    
    return domains;
  }

  // Deploy assets to CDN
  async deployAssets(assetsDir, options = {}) {
    const results = [];
    const files = this.getAssetFiles(assetsDir, options.extensions);
    
    console.log(`Deploying ${files.length} assets to CDN...`);
    
    for (const file of files) {
      try {
        const result = await this.uploadAsset(file, options);
        results.push({ file, success: true, result });
        console.log(`✓ Uploaded: ${file}`);
      } catch (error) {
        results.push({ file, success: false, error });
        console.error(`✗ Failed: ${file}`, error.message);
      }
    }
    
    const successful = results.filter(r => r.success).length;
    console.log(`Deployment completed: ${successful}/${files.length} successful`);
    
    return results;
  }

  // Get asset files from directory
  getAssetFiles(dir, extensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2']) {
    const files = [];
    
    function scanDirectory(directory) {
      const items = fs.readdirSync(directory);
      
      for (const item of items) {
        const fullPath = path.join(directory, item);
        const stats = fs.statSync(fullPath);
        
        if (stats.isDirectory()) {
          scanDirectory(fullPath);
        } else if (extensions.includes(path.extname(item).toLowerCase())) {
          files.push(fullPath);
        }
      }
    }
    
    scanDirectory(dir);
    return files;
  }

  // Get performance analytics
  getAnalytics() {
    const cacheHitRate = this.stats.totalRequests > 0 
      ? (this.stats.cacheHits / this.stats.totalRequests * 100).toFixed(2) 
      : 0;

    return {
      ...this.stats,
      cacheHitRate: `${cacheHitRate}%`,
      totalAssets: this.assetCache.size,
      bandwidthSaved: this.calculateBandwidthSaved(),
      performanceGain: this.calculatePerformanceGain()
    };
  }

  // Calculate bandwidth saved through CDN
  calculateBandwidthSaved() {
    let saved = 0;
    
    for (const [, asset] of this.assetCache) {
      const compressionRatio = (asset.originalSize - asset.size) / asset.originalSize;
      saved += asset.originalSize * compressionRatio;
    }
    
    return this.formatBytes(saved);
  }

  // Calculate performance gain
  calculatePerformanceGain() {
    // Simplified calculation based on average response time improvement
    const baselineResponseTime = 500; // ms
    const improvement = (baselineResponseTime - this.stats.avgResponseTime) / baselineResponseTime;
    return `${(improvement * 100).toFixed(1)}%`;
  }

  // Format bytes for display
  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}

// Base CDN Provider class
class BaseCDNProvider {
  constructor(config) {
    this.config = config;
  }

  async uploadAsset(asset) {
    throw new Error('uploadAsset method must be implemented');
  }

  async purgeAsset(key) {
    throw new Error('purgeAsset method must be implemented');
  }

  getDomain() {
    return this.config.baseUrl;
  }
}

// Cloudflare CDN Provider
class CloudflareProvider extends BaseCDNProvider {
  async uploadAsset(asset) {
    // Simulate Cloudflare API call
    const url = `${this.config.baseUrl}/${asset.key}`;
    
    // In real implementation, this would make actual API calls
    console.log(`Uploading to Cloudflare: ${asset.key}`);
    
    return {
      provider: 'cloudflare',
      url,
      key: asset.key,
      size: asset.size,
      contentType: asset.contentType
    };
  }

  async purgeAsset(key) {
    console.log(`Purging from Cloudflare: ${key}`);
    // Make actual purge API call
  }
}

// AWS CloudFront Provider
class AWSCloudFrontProvider extends BaseCDNProvider {
  async uploadAsset(asset) {
    const url = `${this.config.baseUrl}/${asset.key}`;
    
    console.log(`Uploading to CloudFront: ${asset.key}`);
    
    return {
      provider: 'aws-cloudfront',
      url,
      key: asset.key,
      size: asset.size,
      contentType: asset.contentType
    };
  }

  async purgeAsset(key) {
    console.log(`Purging from CloudFront: ${key}`);
    // Make actual invalidation API call
  }
}

// Azure CDN Provider
class AzureCDNProvider extends BaseCDNProvider {
  async uploadAsset(asset) {
    const url = `${this.config.baseUrl}/${asset.key}`;
    
    console.log(`Uploading to Azure CDN: ${asset.key}`);
    
    return {
      provider: 'azure-cdn',
      url,
      key: asset.key,
      size: asset.size,
      contentType: asset.contentType
    };
  }

  async purgeAsset(key) {
    console.log(`Purging from Azure CDN: ${key}`);
    // Make actual purge API call
  }
}

// Express middleware for CDN integration
function createCDNMiddleware(cdnManager, options = {}) {
  return (req, res, next) => {
    // Add CDN helper methods to response
    res.cdnUrl = (assetPath) => {
      const asset = cdnManager.assetCache.get(assetPath);
      return asset ? asset.url : assetPath;
    };

    res.preload = (assets) => {
      const headers = cdnManager.generatePreloadHeaders(assets);
      res.set('Link', headers);
    };

    res.prefetch = (assets) => {
      const headers = cdnManager.generatePrefetchHeaders(assets);
      res.set('Link', headers);
    };

    res.setCSP = (options) => {
      const csp = cdnManager.generateCSP(options);
      res.set('Content-Security-Policy', csp);
    };

    next();
  };
}

module.exports = {
  CDNManager,
  createCDNMiddleware
};