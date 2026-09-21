/**
 * Advanced API Response Compression System
 * Automatic compression middleware with multiple algorithms and smart selection
 */

import { Request, Response, NextFunction } from 'express';
import { createGzip, createBrotliCompress, createDeflate } from 'zlib';
import { Transform } from 'stream';

interface CompressionConfig {
  threshold: number;
  level: number;
  chunkSize: number;
  memLevel: number;
  windowBits: number;
  strategy: number;
}

interface CompressionStats {
  originalSize: number;
  compressedSize: number;
  ratio: number;
  algorithm: string;
  processingTime: number;
}

type CompressionAlgorithm = 'gzip' | 'br' | 'deflate' | 'none';

class ResponseCompressor {
  private config: Map<CompressionAlgorithm, CompressionConfig>;
  private stats: Map<string, CompressionStats[]> = new Map();
  private compressionCache: Map<string, Buffer> = new Map();
  private cacheMaxSize: number = 100 * 1024 * 1024; // 100MB
  private currentCacheSize: number = 0;

  constructor() {
    this.config = new Map([
      ['gzip', {
        threshold: 1024,
        level: 6,
        chunkSize: 16384,
        memLevel: 8,
        windowBits: 15,
        strategy: 0
      }],
      ['br', {
        threshold: 1024,
        level: 4,
        chunkSize: 16384,
        memLevel: 0,
        windowBits: 0,
        strategy: 0
      }],
      ['deflate', {
        threshold: 1024,
        level: 6,
        chunkSize: 16384,
        memLevel: 8,
        windowBits: 15,
        strategy: 0
      }]
    ]);
  }

  /**
   * Express middleware for automatic response compression
   */
  middleware() {
    return (req: Request, res: Response, next: NextFunction) => {
      const originalSend = res.send.bind(res);
      const originalJson = res.json.bind(res);
      const originalEnd = res.end.bind(res);

      // Override res.send
      res.send = (body: any) => {
        return this.compressResponse(req, res, body, originalSend);
      };

      // Override res.json
      res.json = (obj: any) => {
        const jsonString = JSON.stringify(obj);
        return this.compressResponse(req, res, jsonString, originalSend);
      };

      // Override res.end
      res.end = (chunk?: any, encoding?: BufferEncoding) => {
        if (chunk && typeof chunk === 'string') {
          return this.compressResponse(req, res, chunk, originalEnd);
        }
        return originalEnd(chunk, encoding);
      };

      next();
    };
  }

  /**
   * Compress response based on best algorithm selection
   */
  private compressResponse(
    req: Request, 
    res: Response, 
    body: any, 
    originalMethod: Function
  ): Response {
    // Skip compression for already compressed content
    if (res.getHeader('content-encoding')) {
      return originalMethod(body);
    }

    const bodyString = typeof body === 'string' ? body : JSON.stringify(body);
    const bodyBuffer = Buffer.from(bodyString, 'utf8');

    // Skip compression for small responses
    if (bodyBuffer.length < this.getThreshold(req)) {
      return originalMethod(body);
    }

    // Determine best compression algorithm
    const algorithm = this.selectCompressionAlgorithm(req, bodyBuffer);
    
    if (algorithm === 'none') {
      return originalMethod(body);
    }

    // Check cache first
    const cacheKey = this.getCacheKey(req.path, bodyString, algorithm);
    const cached = this.compressionCache.get(cacheKey);
    
    if (cached) {
      res.setHeader('content-encoding', algorithm);
      res.setHeader('content-length', cached.length);
      res.setHeader('x-compression-cache', 'hit');
      return originalMethod(cached);
    }

    // Compress response
    const startTime = Date.now();
    
    try {
      const compressedBuffer = this.compressBuffer(bodyBuffer, algorithm);
      const processingTime = Date.now() - startTime;

      // Update stats
      this.updateStats(req.path, {
        originalSize: bodyBuffer.length,
        compressedSize: compressedBuffer.length,
        ratio: compressedBuffer.length / bodyBuffer.length,
        algorithm,
        processingTime
      });

      // Cache compressed response
      this.cacheCompressedResponse(cacheKey, compressedBuffer);

      // Set headers
      res.setHeader('content-encoding', algorithm);
      res.setHeader('content-length', compressedBuffer.length);
      res.setHeader('x-compression-ratio', 
        (compressedBuffer.length / bodyBuffer.length).toFixed(3));
      res.setHeader('x-compression-time', `${processingTime}ms`);
      res.setHeader('x-compression-cache', 'miss');

      return originalMethod(compressedBuffer);
    } catch (error) {
      console.error('Compression failed:', error);
      return originalMethod(body);
    }
  }

  /**
   * Select optimal compression algorithm based on client support and content
   */
  private selectCompressionAlgorithm(req: Request, buffer: Buffer): CompressionAlgorithm {
    const acceptEncoding = req.headers['accept-encoding'] || '';
    const contentType = req.headers['content-type'] || '';

    // Check client support
    const supportsBrotli = acceptEncoding.includes('br');
    const supportsGzip = acceptEncoding.includes('gzip');
    const supportsDeflate = acceptEncoding.includes('deflate');

    // Content-based algorithm selection
    if (contentType.includes('application/json') || contentType.includes('text/')) {
      if (supportsBrotli && buffer.length > 10000) {
        return 'br'; // Brotli is best for text/JSON
      }
      if (supportsGzip) {
        return 'gzip'; // Good general purpose
      }
      if (supportsDeflate) {
        return 'deflate'; // Fallback
      }
    }

    // For binary content, prefer gzip
    if (supportsGzip) {
      return 'gzip';
    }

    if (supportsDeflate) {
      return 'deflate';
    }

    return 'none';
  }

  /**
   * Compress buffer using specified algorithm
   */
  private compressBuffer(buffer: Buffer, algorithm: CompressionAlgorithm): Buffer {
    const config = this.config.get(algorithm);
    if (!config) {
      throw new Error(`Unknown compression algorithm: ${algorithm}`);
    }

    switch (algorithm) {
      case 'gzip':
        return this.gzipCompress(buffer, config);
      case 'br':
        return this.brotliCompress(buffer, config);
      case 'deflate':
        return this.deflateCompress(buffer, config);
      default:
        throw new Error(`Compression not implemented for: ${algorithm}`);
    }
  }

  /**
   * Gzip compression with optimized settings
   */
  private gzipCompress(buffer: Buffer, config: CompressionConfig): Buffer {
    const { createGzip } = require('zlib');
    const gzip = createGzip({
      level: config.level,
      chunkSize: config.chunkSize,
      memLevel: config.memLevel,
      windowBits: config.windowBits,
      strategy: config.strategy
    });

    return this.syncCompress(gzip, buffer);
  }

  /**
   * Brotli compression with quality settings
   */
  private brotliCompress(buffer: Buffer, config: CompressionConfig): Buffer {
    const { createBrotliCompress, constants } = require('zlib');
    const brotli = createBrotliCompress({
      params: {
        [constants.BROTLI_PARAM_QUALITY]: config.level,
        [constants.BROTLI_PARAM_SIZE_HINT]: buffer.length
      }
    });

    return this.syncCompress(brotli, buffer);
  }

  /**
   * Deflate compression
   */
  private deflateCompress(buffer: Buffer, config: CompressionConfig): Buffer {
    const { createDeflate } = require('zlib');
    const deflate = createDeflate({
      level: config.level,
      chunkSize: config.chunkSize,
      memLevel: config.memLevel,
      windowBits: config.windowBits,
      strategy: config.strategy
    });

    return this.syncCompress(deflate, buffer);
  }

  /**
   * Synchronous compression helper
   */
  private syncCompress(compressor: Transform, buffer: Buffer): Buffer {
    const chunks: Buffer[] = [];
    
    compressor.on('data', (chunk: Buffer) => {
      chunks.push(chunk);
    });

    compressor.write(buffer);
    compressor.end();

    return Buffer.concat(chunks);
  }

  /**
   * Get compression threshold for request
   */
  private getThreshold(req: Request): number {
    const userAgent = req.headers['user-agent'] || '';
    
    // Lower threshold for mobile devices
    if (userAgent.includes('Mobile')) {
      return 512;
    }

    return 1024;
  }

  /**
   * Generate cache key for compressed responses
   */
  private getCacheKey(path: string, content: string, algorithm: string): string {
    const crypto = require('crypto');
    const hash = crypto.createHash('md5');
    hash.update(`${path}:${content}:${algorithm}`);
    return hash.digest('hex');
  }

  /**
   * Cache compressed response with LRU eviction
   */
  private cacheCompressedResponse(key: string, buffer: Buffer): void {
    // Check cache size limit
    if (this.currentCacheSize + buffer.length > this.cacheMaxSize) {
      this.evictOldestEntries(buffer.length);
    }

    this.compressionCache.set(key, buffer);
    this.currentCacheSize += buffer.length;
  }

  /**
   * Evict oldest cache entries to make space
   */
  private evictOldestEntries(neededSpace: number): void {
    const entries = Array.from(this.compressionCache.entries());
    let freedSpace = 0;

    for (const [key, buffer] of entries) {
      this.compressionCache.delete(key);
      this.currentCacheSize -= buffer.length;
      freedSpace += buffer.length;

      if (freedSpace >= neededSpace) {
        break;
      }
    }
  }

  /**
   * Update compression statistics
   */
  private updateStats(path: string, stats: CompressionStats): void {
    if (!this.stats.has(path)) {
      this.stats.set(path, []);
    }

    const pathStats = this.stats.get(path)!;
    pathStats.push(stats);

    // Keep only last 100 stats per path
    if (pathStats.length > 100) {
      pathStats.shift();
    }
  }

  /**
   * Get comprehensive compression statistics
   */
  getCompressionStats(): {
    totalRequests: number;
    avgCompressionRatio: number;
    avgProcessingTime: number;
    algorithmDistribution: Record<string, number>;
    topCompressedPaths: Array<{ path: string; avgRatio: number; requests: number }>;
    cacheStats: { size: number; hitRate: number };
  } {
    const allStats: CompressionStats[] = [];
    const algorithmCount: Record<string, number> = {};
    const pathStats: Record<string, { totalRatio: number; count: number }> = {};

    for (const [path, stats] of this.stats.entries()) {
      allStats.push(...stats);
      
      let totalRatio = 0;
      for (const stat of stats) {
        algorithmCount[stat.algorithm] = (algorithmCount[stat.algorithm] || 0) + 1;
        totalRatio += stat.ratio;
      }

      pathStats[path] = {
        totalRatio,
        count: stats.length
      };
    }

    const avgCompressionRatio = allStats.length > 0 
      ? allStats.reduce((sum, stat) => sum + stat.ratio, 0) / allStats.length 
      : 0;

    const avgProcessingTime = allStats.length > 0
      ? allStats.reduce((sum, stat) => sum + stat.processingTime, 0) / allStats.length
      : 0;

    const topCompressedPaths = Object.entries(pathStats)
      .map(([path, stats]) => ({
        path,
        avgRatio: stats.totalRatio / stats.count,
        requests: stats.count
      }))
      .sort((a, b) => a.avgRatio - b.avgRatio)
      .slice(0, 10);

    return {
      totalRequests: allStats.length,
      avgCompressionRatio,
      avgProcessingTime,
      algorithmDistribution: algorithmCount,
      topCompressedPaths,
      cacheStats: {
        size: this.currentCacheSize,
        hitRate: 0 // Would need to track hits/misses
      }
    };
  }

  /**
   * Configure compression settings
   */
  configure(algorithm: CompressionAlgorithm, config: Partial<CompressionConfig>): void {
    const currentConfig = this.config.get(algorithm);
    if (currentConfig) {
      this.config.set(algorithm, { ...currentConfig, ...config });
    }
  }

  /**
   * Clear compression cache
   */
  clearCache(): void {
    this.compressionCache.clear();
    this.currentCacheSize = 0;
  }

  /**
   * Get cache information
   */
  getCacheInfo(): {
    entries: number;
    size: number;
    maxSize: number;
    utilizationPercentage: number;
  } {
    return {
      entries: this.compressionCache.size,
      size: this.currentCacheSize,
      maxSize: this.cacheMaxSize,
      utilizationPercentage: (this.currentCacheSize / this.cacheMaxSize) * 100
    };
  }
}

// Singleton instance
export const responseCompressor = new ResponseCompressor();

// Express middleware factory
export const compressionMiddleware = (options?: {
  threshold?: number;
  algorithms?: CompressionAlgorithm[];
  cacheSize?: number;
}) => {
  if (options?.cacheSize) {
    responseCompressor['cacheMaxSize'] = options.cacheSize;
  }

  return responseCompressor.middleware();
};

// React hook for compression monitoring
export const useCompressionStats = () => {
  const [stats, setStats] = React.useState(responseCompressor.getCompressionStats());

  React.useEffect(() => {
    const interval = setInterval(() => {
      setStats(responseCompressor.getCompressionStats());
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return stats;
};

export default ResponseCompressor;