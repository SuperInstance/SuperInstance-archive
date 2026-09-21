import sharp from 'sharp';
import { promises as fs } from 'fs';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';
import Redis from 'ioredis';
import { Logger } from '@/utils/logger';

export interface ImageVariant {
  name: string;
  width: number;
  height: number;
  quality: number;
  format: 'jpeg' | 'png' | 'webp' | 'avif';
  crop?: boolean;
  blur?: number;
  watermark?: boolean;
}

export interface ImageOptimizationConfig {
  outputDirectory: string;
  cacheDirectory: string;
  cdnBaseUrl: string;
  defaultVariants: ImageVariant[];
  maxFileSize: number;
  allowedFormats: string[];
  redis: {
    host: string;
    port: number;
    password?: string;
  };
}

export interface OptimizationResult {
  originalSize: number;
  variants: Array<{
    name: string;
    url: string;
    size: number;
    width: number;
    height: number;
    format: string;
    compressionRatio: number;
  }>;
  totalSavings: number;
  processingTime: number;
}

export class ImageOptimizationService {
  private redis: Redis;
  private logger: Logger;
  private config: ImageOptimizationConfig;

  // Default mobile-optimized variants
  private static readonly MOBILE_VARIANTS: ImageVariant[] = [
    { name: 'thumbnail', width: 150, height: 150, quality: 80, format: 'jpeg', crop: true },
    { name: 'small', width: 320, height: 240, quality: 85, format: 'jpeg' },
    { name: 'medium', width: 640, height: 480, quality: 85, format: 'jpeg' },
    { name: 'large', width: 1024, height: 768, quality: 90, format: 'jpeg' },
    { name: 'thumbnail_webp', width: 150, height: 150, quality: 80, format: 'webp', crop: true },
    { name: 'small_webp', width: 320, height: 240, quality: 85, format: 'webp' },
    { name: 'medium_webp', width: 640, height: 480, quality: 85, format: 'webp' },
    { name: 'large_webp', width: 1024, height: 768, quality: 90, format: 'webp' },
    { name: 'avatar', width: 128, height: 128, quality: 85, format: 'jpeg', crop: true },
    { name: 'avatar_webp', width: 128, height: 128, quality: 85, format: 'webp', crop: true },
    { name: 'banner', width: 800, height: 200, quality: 85, format: 'jpeg', crop: true },
    { name: 'banner_webp', width: 800, height: 200, quality: 85, format: 'webp', crop: true }
  ];

  constructor(config: ImageOptimizationConfig) {
    this.config = {
      ...config,
      defaultVariants: config.defaultVariants || ImageOptimizationService.MOBILE_VARIANTS
    };
    
    this.logger = new Logger('ImageOptimizationService');
    this.redis = new Redis({
      host: config.redis.host,
      port: config.redis.port,
      password: config.redis.password,
      retryDelayOnFailover: 100,
      enableReadyCheck: false,
      maxRetriesPerRequest: null
    });

    this.ensureDirectories();
  }

  private async ensureDirectories(): Promise<void> {
    try {
      await fs.mkdir(this.config.outputDirectory, { recursive: true });
      await fs.mkdir(this.config.cacheDirectory, { recursive: true });
    } catch (error) {
      this.logger.error('Failed to create directories', error);
    }
  }

  async optimizeImage(
    inputPath: string, 
    options: {
      variants?: ImageVariant[];
      userId?: string;
      generateProgressive?: boolean;
      enableCache?: boolean;
    } = {}
  ): Promise<OptimizationResult> {
    const startTime = Date.now();
    
    try {
      // Validate input file
      await this.validateImageFile(inputPath);
      
      // Get image metadata
      const metadata = await sharp(inputPath).metadata();
      const originalSize = metadata.size || 0;
      
      this.logger.info(`Optimizing image: ${inputPath} (${metadata.width}x${metadata.height}, ${originalSize} bytes)`);

      // Use provided variants or default ones
      const variants = options.variants || this.config.defaultVariants;
      
      // Check cache if enabled
      if (options.enableCache) {
        const cached = await this.getCachedResult(inputPath, variants);
        if (cached) {
          this.logger.info('Using cached optimization result');
          return cached;
        }
      }

      // Generate variants
      const results = await Promise.all(
        variants.map(variant => this.generateVariant(inputPath, variant, metadata, options))
      );

      // Calculate total savings
      const totalVariantSize = results.reduce((sum, result) => sum + result.size, 0);
      const totalSavings = Math.max(0, originalSize - totalVariantSize);

      const optimizationResult: OptimizationResult = {
        originalSize,
        variants: results,
        totalSavings,
        processingTime: Date.now() - startTime
      };

      // Cache result if enabled
      if (options.enableCache) {
        await this.cacheResult(inputPath, variants, optimizationResult);
      }

      // Record optimization metrics
      await this.recordOptimizationMetrics(optimizationResult, options.userId);

      this.logger.info(`Image optimization completed: ${results.length} variants generated, ${totalSavings} bytes saved`);
      
      return optimizationResult;

    } catch (error) {
      this.logger.error('Image optimization failed', error);
      throw error;
    }
  }

  private async generateVariant(
    inputPath: string,
    variant: ImageVariant,
    originalMetadata: sharp.Metadata,
    options: any
  ): Promise<any> {
    try {
      const outputId = uuidv4();
      const outputFilename = `${outputId}_${variant.name}.${variant.format}`;
      const outputPath = path.join(this.config.outputDirectory, outputFilename);

      let pipeline = sharp(inputPath);

      // Apply resizing
      if (variant.crop) {
        pipeline = pipeline.resize(variant.width, variant.height, {
          fit: 'cover',
          position: 'center'
        });
      } else {
        pipeline = pipeline.resize(variant.width, variant.height, {
          fit: 'inside',
          withoutEnlargement: true
        });
      }

      // Apply blur if specified
      if (variant.blur && variant.blur > 0) {
        pipeline = pipeline.blur(variant.blur);
      }

      // Apply format-specific optimizations
      switch (variant.format) {
        case 'jpeg':
          pipeline = pipeline.jpeg({
            quality: variant.quality,
            progressive: options.generateProgressive || false,
            mozjpeg: true // Use mozjpeg encoder for better compression
          });
          break;
          
        case 'webp':
          pipeline = pipeline.webp({
            quality: variant.quality,
            effort: 6, // Higher effort for better compression
            nearLossless: false
          });
          break;
          
        case 'avif':
          pipeline = pipeline.avif({
            quality: variant.quality,
            effort: 9 // Maximum effort for AVIF
          });
          break;
          
        case 'png':
          pipeline = pipeline.png({
            quality: variant.quality,
            compressionLevel: 9,
            progressive: options.generateProgressive || false
          });
          break;
      }

      // Apply watermark if specified
      if (variant.watermark) {
        pipeline = await this.applyWatermark(pipeline);
      }

      // Save optimized image
      const info = await pipeline.toFile(outputPath);
      
      // Calculate compression ratio
      const compressionRatio = originalMetadata.size 
        ? Math.round(((originalMetadata.size - info.size) / originalMetadata.size) * 100)
        : 0;

      const url = `${this.config.cdnBaseUrl}/${outputFilename}`;

      return {
        name: variant.name,
        url,
        size: info.size,
        width: info.width,
        height: info.height,
        format: variant.format,
        compressionRatio
      };

    } catch (error) {
      this.logger.error(`Failed to generate variant ${variant.name}`, error);
      throw error;
    }
  }

  private async applyWatermark(pipeline: sharp.Sharp): Promise<sharp.Sharp> {
    // This would apply a watermark to the image
    // For now, just return the pipeline unchanged
    return pipeline;
  }

  private async validateImageFile(inputPath: string): Promise<void> {
    try {
      // Check if file exists
      const stats = await fs.stat(inputPath);
      
      // Check file size
      if (stats.size > this.config.maxFileSize) {
        throw new Error(`Image file too large: ${stats.size} bytes (max: ${this.config.maxFileSize})`);
      }

      // Check if it's a valid image
      const metadata = await sharp(inputPath).metadata();
      
      if (!metadata.format || !this.config.allowedFormats.includes(metadata.format)) {
        throw new Error(`Unsupported image format: ${metadata.format}`);
      }

    } catch (error) {
      throw new Error(`Invalid image file: ${error.message}`);
    }
  }

  async generateResponsiveImageSet(
    inputPath: string,
    breakpoints: number[] = [320, 640, 768, 1024, 1200],
    options: {
      format?: 'jpeg' | 'webp' | 'avif';
      quality?: number;
      userId?: string;
    } = {}
  ): Promise<{
    srcSet: string;
    sizes: string;
    variants: any[];
  }> {
    const format = options.format || 'jpeg';
    const quality = options.quality || 85;

    // Create variants for each breakpoint
    const variants: ImageVariant[] = breakpoints.map((width, index) => ({
      name: `responsive_${width}`,
      width,
      height: Math.round(width * 0.75), // 4:3 aspect ratio
      quality,
      format,
      crop: false
    }));

    const result = await this.optimizeImage(inputPath, {
      variants,
      userId: options.userId,
      enableCache: true
    });

    // Generate srcSet string
    const srcSet = result.variants
      .map(variant => `${variant.url} ${variant.width}w`)
      .join(', ');

    // Generate sizes string (responsive design)
    const sizes = [
      '(max-width: 320px) 280px',
      '(max-width: 640px) 600px',
      '(max-width: 768px) 720px',
      '(max-width: 1024px) 960px',
      '1200px'
    ].join(', ');

    return {
      srcSet,
      sizes,
      variants: result.variants
    };
  }

  async optimizeForMobile(
    inputPath: string,
    deviceType: 'phone' | 'tablet' | 'desktop' = 'phone',
    networkType: 'slow' | 'fast' = 'slow',
    options: {
      userId?: string;
      generateWebP?: boolean;
    } = {}
  ): Promise<OptimizationResult> {
    let variants: ImageVariant[];

    // Choose variants based on device and network
    if (deviceType === 'phone' && networkType === 'slow') {
      variants = [
        { name: 'thumbnail', width: 100, height: 100, quality: 75, format: 'jpeg', crop: true },
        { name: 'small', width: 240, height: 180, quality: 80, format: 'jpeg' },
        { name: 'medium', width: 320, height: 240, quality: 80, format: 'jpeg' }
      ];
    } else if (deviceType === 'phone' && networkType === 'fast') {
      variants = [
        { name: 'thumbnail', width: 150, height: 150, quality: 85, format: 'jpeg', crop: true },
        { name: 'small', width: 320, height: 240, quality: 85, format: 'jpeg' },
        { name: 'medium', width: 480, height: 360, quality: 85, format: 'jpeg' },
        { name: 'large', width: 640, height: 480, quality: 90, format: 'jpeg' }
      ];
    } else {
      variants = this.config.defaultVariants;
    }

    // Add WebP variants if requested
    if (options.generateWebP) {
      const webpVariants = variants.map(variant => ({
        ...variant,
        name: `${variant.name}_webp`,
        format: 'webp' as const,
        quality: Math.max(75, variant.quality - 5) // WebP can achieve same quality with lower setting
      }));
      variants = [...variants, ...webpVariants];
    }

    return this.optimizeImage(inputPath, {
      variants,
      userId: options.userId,
      enableCache: true,
      generateProgressive: networkType === 'slow'
    });
  }

  async generateBlurredPlaceholder(inputPath: string): Promise<string> {
    try {
      const outputId = uuidv4();
      const outputFilename = `${outputId}_placeholder.jpg`;
      const outputPath = path.join(this.config.outputDirectory, outputFilename);

      // Generate a tiny, heavily blurred version for placeholder
      await sharp(inputPath)
        .resize(20, 15) // Very small
        .blur(2)
        .jpeg({ quality: 50 })
        .toFile(outputPath);

      return `${this.config.cdnBaseUrl}/${outputFilename}`;

    } catch (error) {
      this.logger.error('Failed to generate blurred placeholder', error);
      throw error;
    }
  }

  private async getCachedResult(
    inputPath: string,
    variants: ImageVariant[]
  ): Promise<OptimizationResult | null> {
    try {
      const cacheKey = this.generateCacheKey(inputPath, variants);
      const cached = await this.redis.get(`image_cache:${cacheKey}`);
      
      if (cached) {
        return JSON.parse(cached);
      }
      
      return null;
    } catch (error) {
      this.logger.warn('Failed to get cached result', error);
      return null;
    }
  }

  private async cacheResult(
    inputPath: string,
    variants: ImageVariant[],
    result: OptimizationResult
  ): Promise<void> {
    try {
      const cacheKey = this.generateCacheKey(inputPath, variants);
      
      await this.redis.setex(
        `image_cache:${cacheKey}`,
        3600, // 1 hour cache
        JSON.stringify(result)
      );
    } catch (error) {
      this.logger.warn('Failed to cache result', error);
    }
  }

  private generateCacheKey(inputPath: string, variants: ImageVariant[]): string {
    const variantHash = variants
      .map(v => `${v.name}-${v.width}x${v.height}-${v.quality}-${v.format}`)
      .join('|');
    
    return Buffer.from(`${inputPath}:${variantHash}`).toString('base64');
  }

  private async recordOptimizationMetrics(result: OptimizationResult, userId?: string): Promise<void> {
    try {
      const metrics = {
        timestamp: Date.now(),
        originalSize: result.originalSize,
        totalSavings: result.totalSavings,
        processingTime: result.processingTime,
        variantCount: result.variants.length,
        userId: userId || 'anonymous'
      };

      await this.redis.lpush('optimization_metrics', JSON.stringify(metrics));
      await this.redis.ltrim('optimization_metrics', 0, 999); // Keep last 1000 entries

    } catch (error) {
      this.logger.warn('Failed to record optimization metrics', error);
    }
  }

  async getOptimizationStats(): Promise<{
    totalOptimizations: number;
    totalBytesSaved: number;
    averageProcessingTime: number;
    averageCompressionRatio: number;
  }> {
    try {
      const metrics = await this.redis.lrange('optimization_metrics', 0, -1);
      const parsedMetrics = metrics.map(m => JSON.parse(m));

      const totalOptimizations = parsedMetrics.length;
      const totalBytesSaved = parsedMetrics.reduce((sum, m) => sum + m.totalSavings, 0);
      const averageProcessingTime = parsedMetrics.reduce((sum, m) => sum + m.processingTime, 0) / totalOptimizations;
      const averageCompressionRatio = parsedMetrics.reduce((sum, m) => {
        return sum + (m.totalSavings / m.originalSize * 100);
      }, 0) / totalOptimizations;

      return {
        totalOptimizations,
        totalBytesSaved,
        averageProcessingTime,
        averageCompressionRatio
      };
    } catch (error) {
      this.logger.error('Failed to get optimization stats', error);
      return {
        totalOptimizations: 0,
        totalBytesSaved: 0,
        averageProcessingTime: 0,
        averageCompressionRatio: 0
      };
    }
  }

  async cleanup(): Promise<void> {
    await this.redis.quit();
    this.logger.info('Image optimization service cleanup completed');
  }
}