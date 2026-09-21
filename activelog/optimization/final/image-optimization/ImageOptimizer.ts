/**
 * Advanced Image Optimization System
 * Handles image compression, format conversion, and responsive optimization
 */

interface OptimizationOptions {
  quality?: number;
  format?: 'webp' | 'avif' | 'jpeg' | 'png' | 'auto';
  width?: number;
  height?: number;
  fit?: 'cover' | 'contain' | 'fill' | 'inside' | 'outside';
  blur?: number;
  sharpen?: boolean;
  progressive?: boolean;
  lossless?: boolean;
}

interface ResponsiveBreakpoint {
  width: number;
  quality?: number;
  format?: string;
}

class ImageOptimizer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private worker: Worker | null = null;

  constructor() {
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d')!;
    this.initializeWorker();
  }

  /**
   * Initialize Web Worker for heavy image processing
   */
  private initializeWorker(): void {
    try {
      const workerCode = `
        self.onmessage = function(e) {
          const { imageData, operation, options } = e.data;
          
          let result;
          switch (operation) {
            case 'resize':
              result = resizeImageData(imageData, options);
              break;
            case 'compress':
              result = compressImageData(imageData, options);
              break;
            case 'blur':
              result = blurImageData(imageData, options);
              break;
            default:
              result = imageData;
          }
          
          self.postMessage({ result });
        };

        function resizeImageData(imageData, { width, height }) {
          // Implement bicubic interpolation for better quality
          const srcWidth = imageData.width;
          const srcHeight = imageData.height;
          const srcData = imageData.data;
          
          const newImageData = new ImageData(width, height);
          const destData = newImageData.data;
          
          const xRatio = srcWidth / width;
          const yRatio = srcHeight / height;
          
          for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
              const srcX = x * xRatio;
              const srcY = y * yRatio;
              
              const pixel = bicubicInterpolation(srcData, srcWidth, srcHeight, srcX, srcY);
              const destIndex = (y * width + x) * 4;
              
              destData[destIndex] = pixel.r;
              destData[destIndex + 1] = pixel.g;
              destData[destIndex + 2] = pixel.b;
              destData[destIndex + 3] = pixel.a;
            }
          }
          
          return newImageData;
        }

        function bicubicInterpolation(data, width, height, x, y) {
          const x1 = Math.floor(x);
          const y1 = Math.floor(y);
          const x2 = Math.min(x1 + 1, width - 1);
          const y2 = Math.min(y1 + 1, height - 1);
          
          const getPixel = (px, py) => {
            const idx = (py * width + px) * 4;
            return {
              r: data[idx] || 0,
              g: data[idx + 1] || 0,
              b: data[idx + 2] || 0,
              a: data[idx + 3] || 0
            };
          };
          
          // Simple bilinear interpolation for now
          const p1 = getPixel(x1, y1);
          const p2 = getPixel(x2, y1);
          const p3 = getPixel(x1, y2);
          const p4 = getPixel(x2, y2);
          
          const fx = x - x1;
          const fy = y - y1;
          
          return {
            r: Math.round(p1.r * (1 - fx) * (1 - fy) + p2.r * fx * (1 - fy) + p3.r * (1 - fx) * fy + p4.r * fx * fy),
            g: Math.round(p1.g * (1 - fx) * (1 - fy) + p2.g * fx * (1 - fy) + p3.g * (1 - fx) * fy + p4.g * fx * fy),
            b: Math.round(p1.b * (1 - fx) * (1 - fy) + p2.b * fx * (1 - fy) + p3.b * (1 - fx) * fy + p4.b * fx * fy),
            a: Math.round(p1.a * (1 - fx) * (1 - fy) + p2.a * fx * (1 - fy) + p3.a * (1 - fx) * fy + p4.a * fx * fy)
          };
        }

        function compressImageData(imageData, { quality }) {
          // Apply compression algorithms
          return imageData; // Placeholder
        }

        function blurImageData(imageData, { radius }) {
          // Apply Gaussian blur
          return imageData; // Placeholder
        }
      `;

      const blob = new Blob([workerCode], { type: 'application/javascript' });
      this.worker = new Worker(URL.createObjectURL(blob));
    } catch (error) {
      console.warn('Failed to initialize image optimization worker:', error);
    }
  }

  /**
   * Optimize a single image with specified options
   */
  async optimizeImage(
    source: string | File | Blob,
    options: OptimizationOptions = {}
  ): Promise<{ blob: Blob; url: string; size: number; dimensions: { width: number; height: number } }> {
    const {
      quality = 80,
      format = 'auto',
      width,
      height,
      fit = 'cover',
      blur,
      sharpen,
      progressive = true,
      lossless = false
    } = options;

    // Load image
    const img = await this.loadImage(source);
    const originalWidth = img.naturalWidth || img.width;
    const originalHeight = img.naturalHeight || img.height;

    // Calculate dimensions
    const dimensions = this.calculateDimensions(originalWidth, originalHeight, width, height, fit);
    
    // Setup canvas
    this.canvas.width = dimensions.width;
    this.canvas.height = dimensions.height;

    // Draw and optimize
    this.ctx.imageSmoothingEnabled = true;
    this.ctx.imageSmoothingQuality = 'high';
    this.ctx.drawImage(img, 0, 0, dimensions.width, dimensions.height);

    // Apply effects
    if (blur && blur > 0) {
      this.ctx.filter = `blur(${blur}px)`;
    }

    if (sharpen) {
      await this.applySharpenFilter();
    }

    // Determine optimal format
    const optimalFormat = this.determineOptimalFormat(format, source);
    
    // Convert to blob
    const blob = await this.canvasToBlob(optimalFormat, quality, progressive, lossless);
    const url = URL.createObjectURL(blob);

    return {
      blob,
      url,
      size: blob.size,
      dimensions
    };
  }

  /**
   * Generate responsive images for different breakpoints
   */
  async generateResponsiveImages(
    source: string | File | Blob,
    breakpoints: ResponsiveBreakpoint[],
    baseOptions: OptimizationOptions = {}
  ): Promise<Array<{
    width: number;
    blob: Blob;
    url: string;
    size: number;
    format: string;
  }>> {
    const results = [];

    for (const breakpoint of breakpoints) {
      const options: OptimizationOptions = {
        ...baseOptions,
        width: breakpoint.width,
        quality: breakpoint.quality || baseOptions.quality,
        format: (breakpoint.format as any) || baseOptions.format,
      };

      try {
        const optimized = await this.optimizeImage(source, options);
        results.push({
          width: breakpoint.width,
          blob: optimized.blob,
          url: optimized.url,
          size: optimized.size,
          format: options.format || 'auto',
        });
      } catch (error) {
        console.error(`Failed to generate responsive image for width ${breakpoint.width}:`, error);
      }
    }

    return results;
  }

  /**
   * Create blur placeholder for progressive loading
   */
  async createBlurPlaceholder(
    source: string | File | Blob,
    size: number = 20
  ): Promise<string> {
    const placeholder = await this.optimizeImage(source, {
      width: size,
      height: size,
      quality: 50,
      blur: 1,
      format: 'jpeg'
    });

    // Convert to base64 data URL for inline embedding
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.readAsDataURL(placeholder.blob);
    });
  }

  /**
   * Batch optimize multiple images
   */
  async batchOptimize(
    images: Array<{ source: string | File | Blob; options?: OptimizationOptions }>,
    concurrency: number = 3
  ): Promise<Array<{ success: boolean; result?: any; error?: Error }>> {
    const results = [];
    const batches = this.createBatches(images, concurrency);

    for (const batch of batches) {
      const batchPromises = batch.map(async ({ source, options }) => {
        try {
          const result = await this.optimizeImage(source, options);
          return { success: true, result };
        } catch (error) {
          return { success: false, error: error as Error };
        }
      });

      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults);
    }

    return results;
  }

  /**
   * Analyze image and suggest optimizations
   */
  async analyzeImage(source: string | File | Blob): Promise<{
    originalSize: number;
    dimensions: { width: number; height: number };
    format: string;
    recommendations: Array<{
      optimization: string;
      potentialSaving: number;
      description: string;
    }>;
  }> {
    const img = await this.loadImage(source);
    const originalSize = source instanceof Blob ? source.size : 0;
    const dimensions = {
      width: img.naturalWidth || img.width,
      height: img.naturalHeight || img.height
    };

    // Analyze format
    const format = this.detectImageFormat(source);
    const recommendations = [];

    // Check if image is too large
    const pixelCount = dimensions.width * dimensions.height;
    if (pixelCount > 2073600) { // > 1920x1080
      recommendations.push({
        optimization: 'resize',
        potentialSaving: 0.6,
        description: 'Image resolution is higher than necessary for web display'
      });
    }

    // Check format optimization
    if (format === 'png' && this.hasTransparency(img)) {
      recommendations.push({
        optimization: 'format',
        potentialSaving: 0.4,
        description: 'Convert to WebP for better compression while maintaining transparency'
      });
    } else if (format === 'png' && !this.hasTransparency(img)) {
      recommendations.push({
        optimization: 'format',
        potentialSaving: 0.7,
        description: 'Convert to JPEG or WebP for significantly better compression'
      });
    }

    // Check quality
    if (originalSize > 500000) { // > 500KB
      recommendations.push({
        optimization: 'quality',
        potentialSaving: 0.3,
        description: 'Reduce quality to 80-85% for minimal visual impact'
      });
    }

    return {
      originalSize,
      dimensions,
      format,
      recommendations
    };
  }

  /**
   * Load image from various sources
   */
  private loadImage(source: string | File | Blob): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;

      if (typeof source === 'string') {
        img.src = source;
      } else {
        img.src = URL.createObjectURL(source);
      }
    });
  }

  /**
   * Calculate optimal dimensions based on constraints
   */
  private calculateDimensions(
    originalWidth: number,
    originalHeight: number,
    targetWidth?: number,
    targetHeight?: number,
    fit: string = 'cover'
  ): { width: number; height: number } {
    if (!targetWidth && !targetHeight) {
      return { width: originalWidth, height: originalHeight };
    }

    const aspectRatio = originalWidth / originalHeight;

    if (targetWidth && !targetHeight) {
      return { width: targetWidth, height: Math.round(targetWidth / aspectRatio) };
    }

    if (!targetWidth && targetHeight) {
      return { width: Math.round(targetHeight * aspectRatio), height: targetHeight };
    }

    // Both dimensions specified
    if (fit === 'cover') {
      const scale = Math.max(targetWidth! / originalWidth, targetHeight! / originalHeight);
      return {
        width: Math.round(originalWidth * scale),
        height: Math.round(originalHeight * scale)
      };
    } else if (fit === 'contain') {
      const scale = Math.min(targetWidth! / originalWidth, targetHeight! / originalHeight);
      return {
        width: Math.round(originalWidth * scale),
        height: Math.round(originalHeight * scale)
      };
    }

    return { width: targetWidth!, height: targetHeight! };
  }

  /**
   * Determine optimal image format
   */
  private determineOptimalFormat(
    requestedFormat: string,
    source: string | File | Blob
  ): string {
    if (requestedFormat !== 'auto') {
      return requestedFormat;
    }

    // Check browser support
    const supportsWebP = this.supportsFormat('webp');
    const supportsAVIF = this.supportsFormat('avif');

    if (supportsAVIF) return 'avif';
    if (supportsWebP) return 'webp';
    
    // Fallback based on source
    const originalFormat = this.detectImageFormat(source);
    return originalFormat === 'png' ? 'png' : 'jpeg';
  }

  /**
   * Check browser format support
   */
  private supportsFormat(format: string): boolean {
    const canvas = document.createElement('canvas');
    canvas.width = 1;
    canvas.height = 1;
    
    try {
      const dataUrl = canvas.toDataURL(`image/${format}`);
      return dataUrl.indexOf(`image/${format}`) === 5;
    } catch {
      return false;
    }
  }

  /**
   * Detect image format from source
   */
  private detectImageFormat(source: string | File | Blob): string {
    if (typeof source === 'string') {
      const ext = source.split('.').pop()?.toLowerCase();
      return ext || 'jpeg';
    } else if (source instanceof File) {
      return source.type.split('/')[1] || 'jpeg';
    }
    return 'jpeg';
  }

  /**
   * Check if image has transparency
   */
  private hasTransparency(img: HTMLImageElement): boolean {
    // This is a simplified check - in reality, you'd analyze the image data
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d')!;
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0);
    
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;
    
    for (let i = 3; i < data.length; i += 4) {
      if (data[i] < 255) return true;
    }
    
    return false;
  }

  /**
   * Convert canvas to optimized blob
   */
  private canvasToBlob(
    format: string,
    quality: number,
    progressive: boolean,
    lossless: boolean
  ): Promise<Blob> {
    return new Promise((resolve) => {
      const mimeType = `image/${format}`;
      const qualityValue = format === 'png' ? undefined : quality / 100;
      
      this.canvas.toBlob(
        (blob) => resolve(blob!),
        mimeType,
        qualityValue
      );
    });
  }

  /**
   * Apply sharpen filter using convolution
   */
  private async applySharpenFilter(): Promise<void> {
    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    const data = imageData.data;
    const width = imageData.width;
    const height = imageData.height;
    
    // Sharpen kernel
    const kernel = [
      [0, -1, 0],
      [-1, 5, -1],
      [0, -1, 0]
    ];
    
    const newData = new Uint8ClampedArray(data.length);
    
    for (let y = 1; y < height - 1; y++) {
      for (let x = 1; x < width - 1; x++) {
        for (let c = 0; c < 3; c++) { // RGB channels only
          let sum = 0;
          for (let ky = -1; ky <= 1; ky++) {
            for (let kx = -1; kx <= 1; kx++) {
              const idx = ((y + ky) * width + (x + kx)) * 4 + c;
              sum += data[idx] * kernel[ky + 1][kx + 1];
            }
          }
          const idx = (y * width + x) * 4 + c;
          newData[idx] = Math.max(0, Math.min(255, sum));
        }
        // Copy alpha channel
        const alphaIdx = (y * width + x) * 4 + 3;
        newData[alphaIdx] = data[alphaIdx];
      }
    }
    
    const newImageData = new ImageData(newData, width, height);
    this.ctx.putImageData(newImageData, 0, 0);
  }

  /**
   * Create batches for concurrent processing
   */
  private createBatches<T>(items: T[], size: number): T[][] {
    const batches: T[][] = [];
    for (let i = 0; i < items.length; i += size) {
      batches.push(items.slice(i, i + size));
    }
    return batches;
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
    }
  }
}

// Create singleton instance
export const imageOptimizer = new ImageOptimizer();
export default ImageOptimizer;