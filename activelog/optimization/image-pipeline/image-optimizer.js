const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const EventEmitter = require('events');

class ImageOptimizer extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      // Output quality settings
      jpegQuality: config.jpegQuality || 80,
      pngQuality: config.pngQuality || 80,
      webpQuality: config.webpQuality || 80,
      avifQuality: config.avifQuality || 50,
      
      // Resize settings
      maxWidth: config.maxWidth || 2048,
      maxHeight: config.maxHeight || 2048,
      enableResponsiveImages: config.enableResponsiveImages ?? true,
      responsiveSizes: config.responsiveSizes || [320, 640, 1024, 1920],
      
      // Format settings
      enableWebP: config.enableWebP ?? true,
      enableAVIF: config.enableAVIF ?? false,
      autoFormat: config.autoFormat ?? true,
      
      // Optimization settings
      enableProgressive: config.enableProgressive ?? true,
      stripMetadata: config.stripMetadata ?? true,
      enableLossless: config.enableLossless ?? false,
      
      // Processing settings
      outputDir: config.outputDir || './optimized',
      cacheDir: config.cacheDir || './cache',
      enableCaching: config.enableCaching ?? true,
      concurrency: config.concurrency || 4,
      
      ...config
    };
    
    this.processingQueue = [];
    this.activeProcesses = 0;
    this.cache = new Map();
    this.stats = {
      processed: 0,
      totalSizeReduction: 0,
      avgCompressionRatio: 0,
      errors: 0
    };

    this.ensureDirectories();
    this.loadCache();
  }

  // Ensure output and cache directories exist
  ensureDirectories() {
    [this.config.outputDir, this.config.cacheDir].forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });
  }

  // Load cache from disk
  loadCache() {
    const cacheFile = path.join(this.config.cacheDir, 'image-cache.json');
    if (fs.existsSync(cacheFile)) {
      try {
        const cacheData = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
        this.cache = new Map(cacheData);
      } catch (error) {
        console.warn('Failed to load image cache:', error.message);
      }
    }
  }

  // Save cache to disk
  saveCache() {
    const cacheFile = path.join(this.config.cacheDir, 'image-cache.json');
    try {
      fs.writeFileSync(cacheFile, JSON.stringify([...this.cache.entries()]));
    } catch (error) {
      console.warn('Failed to save image cache:', error.message);
    }
  }

  // Generate cache key for image
  generateCacheKey(inputPath, options) {
    const hash = crypto.createHash('md5');
    hash.update(inputPath);
    hash.update(JSON.stringify(options));
    
    // Include file modification time for cache invalidation
    const stats = fs.statSync(inputPath);
    hash.update(stats.mtime.toISOString());
    
    return hash.digest('hex');
  }

  // Check if image is already optimized in cache
  isInCache(cacheKey) {
    if (!this.config.enableCaching) return false;
    
    const cacheEntry = this.cache.get(cacheKey);
    if (!cacheEntry) return false;
    
    // Verify cached files still exist
    const allExist = cacheEntry.outputs.every(output => 
      fs.existsSync(output.path)
    );
    
    if (!allExist) {
      this.cache.delete(cacheKey);
      return false;
    }
    
    return true;
  }

  // Get image metadata and analyze
  async analyzeImage(inputPath) {
    try {
      // This would typically use a library like sharp, jimp, or imagemagick
      // For demonstration, we'll simulate the analysis
      const stats = fs.statSync(inputPath);
      const ext = path.extname(inputPath).toLowerCase();
      
      // Simulate getting image dimensions and format
      const analysis = {
        path: inputPath,
        size: stats.size,
        format: ext.substring(1),
        width: 1920, // Would be actual width from image library
        height: 1080, // Would be actual height from image library
        hasAlpha: ext === '.png',
        isAnimated: ext === '.gif',
        colorProfile: 'sRGB',
        metadata: {
          created: stats.birthtime,
          modified: stats.mtime
        }
      };
      
      return analysis;
    } catch (error) {
      throw new Error(`Failed to analyze image ${inputPath}: ${error.message}`);
    }
  }

  // Determine optimal formats for image
  determineOptimalFormats(analysis) {
    const formats = [];
    
    // Always include original format (optimized)
    formats.push({
      format: analysis.format,
      quality: this.getQualityForFormat(analysis.format),
      suffix: 'optimized'
    });
    
    // Add modern formats if enabled
    if (this.config.enableWebP && analysis.format !== 'webp') {
      formats.push({
        format: 'webp',
        quality: this.config.webpQuality,
        suffix: 'webp'
      });
    }
    
    if (this.config.enableAVIF && analysis.format !== 'avif') {
      formats.push({
        format: 'avif',
        quality: this.config.avifQuality,
        suffix: 'avif'
      });
    }
    
    return formats;
  }

  // Get quality setting for format
  getQualityForFormat(format) {
    switch (format) {
      case 'jpg':
      case 'jpeg':
        return this.config.jpegQuality;
      case 'png':
        return this.config.pngQuality;
      case 'webp':
        return this.config.webpQuality;
      case 'avif':
        return this.config.avifQuality;
      default:
        return 80;
    }
  }

  // Calculate responsive sizes needed
  calculateResponsiveSizes(originalWidth) {
    if (!this.config.enableResponsiveImages) {
      return [originalWidth];
    }
    
    return this.config.responsiveSizes.filter(size => size <= originalWidth);
  }

  // Optimize single image
  async optimizeImage(inputPath, options = {}) {
    const cacheKey = this.generateCacheKey(inputPath, options);
    
    // Check cache first
    if (this.isInCache(cacheKey)) {
      const cachedResult = this.cache.get(cacheKey);
      this.emit('cached', { inputPath, result: cachedResult });
      return cachedResult;
    }

    try {
      // Analyze input image
      const analysis = await this.analyzeImage(inputPath);
      this.emit('analyzing', { inputPath, analysis });
      
      // Determine optimization strategy
      const formats = this.determineOptimalFormats(analysis);
      const sizes = this.calculateResponsiveSizes(analysis.width);
      
      const outputs = [];
      let totalOriginalSize = analysis.size * formats.length * sizes.length;
      let totalOptimizedSize = 0;
      
      // Process each format and size combination
      for (const format of formats) {
        for (const size of sizes) {
          const output = await this.processImageVariant(
            inputPath,
            analysis,
            format,
            size,
            options
          );
          
          outputs.push(output);
          totalOptimizedSize += output.size;
        }
      }
      
      // Calculate compression statistics
      const compressionRatio = (totalOriginalSize - totalOptimizedSize) / totalOriginalSize;
      const result = {
        inputPath,
        originalSize: analysis.size,
        outputs,
        totalOptimizedSize,
        compressionRatio,
        sizeSaved: totalOriginalSize - totalOptimizedSize,
        processedAt: new Date().toISOString()
      };
      
      // Update statistics
      this.updateStats(result);
      
      // Cache the result
      if (this.config.enableCaching) {
        this.cache.set(cacheKey, result);
        this.saveCache();
      }
      
      this.emit('optimized', result);
      return result;
      
    } catch (error) {
      this.stats.errors++;
      this.emit('error', { inputPath, error });
      throw error;
    }
  }

  // Process individual image variant (format/size combination)
  async processImageVariant(inputPath, analysis, formatConfig, targetSize, options) {
    const inputBasename = path.basename(inputPath, path.extname(inputPath));
    const outputFilename = `${inputBasename}_${targetSize}w.${formatConfig.suffix}.${formatConfig.format}`;
    const outputPath = path.join(this.config.outputDir, outputFilename);
    
    // Simulate image processing (would use actual image library)
    const processedImage = await this.simulateImageProcessing(
      inputPath,
      formatConfig,
      targetSize,
      options
    );
    
    // Write processed image to disk
    fs.writeFileSync(outputPath, processedImage.buffer);
    
    return {
      path: outputPath,
      format: formatConfig.format,
      width: processedImage.width,
      height: processedImage.height,
      size: processedImage.buffer.length,
      quality: formatConfig.quality
    };
  }

  // Simulate image processing (replace with actual library)
  async simulateImageProcessing(inputPath, formatConfig, targetSize, options) {
    // This would be replaced with actual image processing using sharp, jimp, etc.
    const inputBuffer = fs.readFileSync(inputPath);
    
    // Simulate optimization by reducing file size by compression ratio
    const compressionFactor = formatConfig.format === 'avif' ? 0.6 : 
                            formatConfig.format === 'webp' ? 0.7 : 0.8;
    
    const optimizedSize = Math.floor(inputBuffer.length * compressionFactor);
    const outputBuffer = Buffer.alloc(optimizedSize);
    
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 100));
    
    return {
      buffer: outputBuffer,
      width: targetSize,
      height: Math.floor(targetSize * 0.75), // Simulate aspect ratio
      format: formatConfig.format
    };
  }

  // Update optimization statistics
  updateStats(result) {
    this.stats.processed++;
    this.stats.totalSizeReduction += result.sizeSaved;
    
    const totalProcessed = this.stats.processed;
    this.stats.avgCompressionRatio = (
      (this.stats.avgCompressionRatio * (totalProcessed - 1) + result.compressionRatio) / 
      totalProcessed
    );
  }

  // Process multiple images with concurrency control
  async optimizeBatch(inputPaths, options = {}) {
    const results = [];
    const errors = [];
    
    this.emit('batchStarted', { count: inputPaths.length });
    
    // Process images with concurrency control
    const processingPromises = inputPaths.map(async (inputPath) => {
      try {
        const result = await this.optimizeImage(inputPath, options);
        results.push(result);
      } catch (error) {
        errors.push({ inputPath, error });
      }
    });
    
    // Wait for all images to process
    await Promise.all(processingPromises);
    
    const batchResult = {
      processed: results.length,
      errors: errors.length,
      results,
      errors: errors,
      totalSizeSaved: results.reduce((sum, r) => sum + r.sizeSaved, 0),
      avgCompressionRatio: results.reduce((sum, r) => sum + r.compressionRatio, 0) / results.length
    };
    
    this.emit('batchCompleted', batchResult);
    return batchResult;
  }

  // Watch directory for new images and auto-optimize
  watchDirectory(directoryPath, options = {}) {
    const chokidar = require('chokidar');
    
    const watcher = chokidar.watch(directoryPath, {
      ignored: /(^|[\/\\])\../, // Ignore hidden files
      persistent: true
    });
    
    watcher.on('add', async (filePath) => {
      if (this.isImageFile(filePath)) {
        try {
          await this.optimizeImage(filePath, options);
          this.emit('autoOptimized', { filePath });
        } catch (error) {
          this.emit('autoOptimizationError', { filePath, error });
        }
      }
    });
    
    return watcher;
  }

  // Check if file is an image
  isImageFile(filePath) {
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.webp', '.avif', '.gif', '.bmp', '.tiff'];
    const ext = path.extname(filePath).toLowerCase();
    return imageExtensions.includes(ext);
  }

  // Generate responsive image HTML
  generateResponsiveHTML(result, alt = '', className = '') {
    const outputs = result.outputs;
    const webpOutputs = outputs.filter(o => o.format === 'webp');
    const avifOutputs = outputs.filter(o => o.format === 'avif');
    const fallbackOutputs = outputs.filter(o => o.format !== 'webp' && o.format !== 'avif');
    
    let html = '<picture>\n';
    
    // Add AVIF sources
    if (avifOutputs.length > 0) {
      const srcset = avifOutputs.map(o => `${o.path} ${o.width}w`).join(', ');
      html += `  <source srcset="${srcset}" type="image/avif">\n`;
    }
    
    // Add WebP sources
    if (webpOutputs.length > 0) {
      const srcset = webpOutputs.map(o => `${o.path} ${o.width}w`).join(', ');
      html += `  <source srcset="${srcset}" type="image/webp">\n`;
    }
    
    // Add fallback
    const fallback = fallbackOutputs[0] || outputs[0];
    const fallbackSrcset = fallbackOutputs.map(o => `${o.path} ${o.width}w`).join(', ');
    
    html += `  <img src="${fallback.path}" srcset="${fallbackSrcset}" `;
    html += `alt="${alt}" class="${className}" loading="lazy">\n`;
    html += '</picture>';
    
    return html;
  }

  // Generate optimization report
  generateReport() {
    return {
      stats: { ...this.stats },
      config: {
        formats: {
          webpEnabled: this.config.enableWebP,
          avifEnabled: this.config.enableAVIF
        },
        quality: {
          jpeg: this.config.jpegQuality,
          png: this.config.pngQuality,
          webp: this.config.webpQuality,
          avif: this.config.avifQuality
        },
        responsive: {
          enabled: this.config.enableResponsiveImages,
          sizes: this.config.responsiveSizes
        }
      },
      cacheSize: this.cache.size,
      recommendations: this.generateRecommendations()
    };
  }

  // Generate optimization recommendations
  generateRecommendations() {
    const recommendations = [];
    
    if (this.stats.avgCompressionRatio < 0.2) {
      recommendations.push({
        type: 'quality_adjustment',
        message: 'Consider reducing quality settings for better compression',
        impact: 'medium'
      });
    }
    
    if (!this.config.enableWebP) {
      recommendations.push({
        type: 'format_upgrade',
        message: 'Enable WebP format for better compression and browser support',
        impact: 'high'
      });
    }
    
    if (!this.config.enableResponsiveImages) {
      recommendations.push({
        type: 'responsive_images',
        message: 'Enable responsive images to reduce bandwidth on mobile devices',
        impact: 'high'
      });
    }
    
    return recommendations;
  }

  // Clean up cache and temporary files
  cleanup() {
    this.saveCache();
    
    // Clean old cache entries (older than 30 days)
    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
    for (const [key, value] of this.cache.entries()) {
      if (new Date(value.processedAt).getTime() < thirtyDaysAgo) {
        this.cache.delete(key);
      }
    }
  }

  // Get optimization statistics
  getStats() {
    return {
      ...this.stats,
      cacheHitRate: this.cache.size / Math.max(this.stats.processed, 1),
      avgSizeSavedPerImage: this.stats.totalSizeReduction / Math.max(this.stats.processed, 1)
    };
  }
}

// Utility functions for integration with web frameworks

// Express middleware for automatic image optimization
function createImageOptimizationMiddleware(optimizer, options = {}) {
  return async (req, res, next) => {
    const originalSend = res.sendFile;
    
    res.sendFile = async function(filePath, options, callback) {
      if (optimizer.isImageFile(filePath)) {
        try {
          const result = await optimizer.optimizeImage(filePath);
          // Serve the best optimized version based on Accept header
          const acceptHeader = req.headers.accept || '';
          
          let bestOutput = result.outputs[0];
          if (acceptHeader.includes('image/avif')) {
            bestOutput = result.outputs.find(o => o.format === 'avif') || bestOutput;
          } else if (acceptHeader.includes('image/webp')) {
            bestOutput = result.outputs.find(o => o.format === 'webp') || bestOutput;
          }
          
          return originalSend.call(this, bestOutput.path, options, callback);
        } catch (error) {
          console.warn('Image optimization failed, serving original:', error.message);
        }
      }
      
      return originalSend.call(this, filePath, options, callback);
    };
    
    next();
  };
}

module.exports = {
  ImageOptimizer,
  createImageOptimizationMiddleware
};