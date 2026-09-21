/**
 * WebAssembly Image Processor Interface
 * High-performance image processing using WASM for compute-intensive operations
 */

interface ImageProcessorModule {
  ready: Promise<void>;
  resize_image(src_data: number, src_width: number, src_height: number, dst_data: number, dst_width: number, dst_height: number): void;
  gaussian_blur(data: number, width: number, height: number, radius: number): void;
  sharpen_image(data: number, width: number, height: number, amount: number): void;
  adjust_brightness_contrast(data: number, width: number, height: number, brightness: number, contrast: number): void;
  adjust_color_temperature(data: number, width: number, height: number, temperature: number): void;
  edge_detection(src_data: number, dst_data: number, width: number, height: number, threshold: number): void;
  adjust_hsv(data: number, width: number, height: number, hue_shift: number, saturation_mult: number, value_mult: number): void;
  allocate_memory(size: number): number;
  free_memory(ptr: number): void;
  HEAPU8: Uint8Array;
  _malloc(size: number): number;
  _free(ptr: number): void;
}

type ImageProcessorFactory = () => Promise<ImageProcessorModule>;

interface ProcessingOptions {
  useWorker?: boolean;
  maxConcurrency?: number;
  enableProfiling?: boolean;
}

interface ProcessingResult {
  success: boolean;
  processingTime: number;
  memoryUsed: number;
  error?: string;
}

class WASMImageProcessor {
  private module: ImageProcessorModule | null = null;
  private worker: Worker | null = null;
  private isInitialized = false;
  private processingQueue: Array<() => Promise<any>> = [];
  private activeOperations = 0;
  private maxConcurrency: number;
  private enableProfiling: boolean;

  constructor(options: ProcessingOptions = {}) {
    this.maxConcurrency = options.maxConcurrency || 1;
    this.enableProfiling = options.enableProfiling || false;
    
    if (options.useWorker) {
      this.initializeWorker();
    }
  }

  /**
   * Initialize the WASM module
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Dynamic import to avoid bundling issues
      const { default: ImageProcessor } = await import('./build/wasm/image-processor.js');
      this.module = await ImageProcessor();
      this.isInitialized = true;
      
      console.log('✅ WASM Image Processor initialized');
    } catch (error) {
      console.error('❌ Failed to initialize WASM Image Processor:', error);
      throw new Error('Failed to initialize WASM module');
    }
  }

  /**
   * Initialize Web Worker for background processing
   */
  private initializeWorker(): void {
    const workerCode = `
      let wasmModule = null;
      
      self.onmessage = async function(e) {
        const { operation, data, options, id } = e.data;
        
        try {
          if (!wasmModule) {
            const { default: ImageProcessor } = await import('./build/wasm/image-processor.js');
            wasmModule = await ImageProcessor();
          }
          
          const startTime = performance.now();
          let result;
          
          switch (operation) {
            case 'resize':
              result = await processResize(data, options);
              break;
            case 'blur':
              result = await processBlur(data, options);
              break;
            case 'sharpen':
              result = await processSharpen(data, options);
              break;
            case 'adjustBrightness':
              result = await processBrightnessContrast(data, options);
              break;
            case 'adjustTemperature':
              result = await processColorTemperature(data, options);
              break;
            case 'detectEdges':
              result = await processEdgeDetection(data, options);
              break;
            case 'adjustHSV':
              result = await processHSV(data, options);
              break;
            default:
              throw new Error('Unknown operation: ' + operation);
          }
          
          const processingTime = performance.now() - startTime;
          
          self.postMessage({
            id,
            success: true,
            result,
            processingTime
          });
          
        } catch (error) {
          self.postMessage({
            id,
            success: false,
            error: error.message
          });
        }
      };
      
      async function processResize(imageData, options) {
        const { width: srcWidth, height: srcHeight, data: srcData } = imageData;
        const { width: dstWidth, height: dstHeight } = options;
        
        const srcSize = srcWidth * srcHeight * 4;
        const dstSize = dstWidth * dstHeight * 4;
        
        const srcPtr = wasmModule.allocate_memory(srcSize);
        const dstPtr = wasmModule.allocate_memory(dstSize);
        
        wasmModule.HEAPU8.set(srcData, srcPtr);
        
        wasmModule.resize_image(srcPtr, srcWidth, srcHeight, dstPtr, dstWidth, dstHeight);
        
        const resultData = new Uint8ClampedArray(wasmModule.HEAPU8.buffer, dstPtr, dstSize);
        const result = new ImageData(new Uint8ClampedArray(resultData), dstWidth, dstHeight);
        
        wasmModule.free_memory(srcPtr);
        wasmModule.free_memory(dstPtr);
        
        return result;
      }
      
      // Additional processing functions would be implemented similarly...
    `;

    const blob = new Blob([workerCode], { type: 'application/javascript' });
    this.worker = new Worker(URL.createObjectURL(blob));
  }

  /**
   * Process image resize with high performance
   */
  async resizeImage(
    imageData: ImageData,
    targetWidth: number,
    targetHeight: number
  ): Promise<{ result: ImageData; metrics: ProcessingResult }> {
    if (!this.isInitialized || !this.module) {
      throw new Error('WASM module not initialized');
    }

    const startTime = performance.now();
    const startMemory = this.getMemoryUsage();

    try {
      const srcSize = imageData.width * imageData.height * 4;
      const dstSize = targetWidth * targetHeight * 4;

      // Allocate memory in WASM heap
      const srcPtr = this.module.allocate_memory(srcSize);
      const dstPtr = this.module.allocate_memory(dstSize);

      // Copy image data to WASM memory
      this.module.HEAPU8.set(imageData.data, srcPtr);

      // Perform resize operation
      this.module.resize_image(
        srcPtr, imageData.width, imageData.height,
        dstPtr, targetWidth, targetHeight
      );

      // Copy result back to JavaScript
      const resultData = new Uint8ClampedArray(
        this.module.HEAPU8.buffer,
        dstPtr,
        dstSize
      );
      const result = new ImageData(
        new Uint8ClampedArray(resultData),
        targetWidth,
        targetHeight
      );

      // Free WASM memory
      this.module.free_memory(srcPtr);
      this.module.free_memory(dstPtr);

      const processingTime = performance.now() - startTime;
      const memoryUsed = this.getMemoryUsage() - startMemory;

      return {
        result,
        metrics: {
          success: true,
          processingTime,
          memoryUsed,
        }
      };
    } catch (error) {
      const processingTime = performance.now() - startTime;
      return {
        result: imageData, // Return original on error
        metrics: {
          success: false,
          processingTime,
          memoryUsed: 0,
          error: (error as Error).message,
        }
      };
    }
  }

  /**
   * Apply Gaussian blur with WebAssembly acceleration
   */
  async blurImage(
    imageData: ImageData,
    radius: number
  ): Promise<{ result: ImageData; metrics: ProcessingResult }> {
    if (!this.isInitialized || !this.module) {
      throw new Error('WASM module not initialized');
    }

    const startTime = performance.now();
    const startMemory = this.getMemoryUsage();

    try {
      const size = imageData.width * imageData.height * 4;
      const ptr = this.module.allocate_memory(size);

      this.module.HEAPU8.set(imageData.data, ptr);
      this.module.gaussian_blur(ptr, imageData.width, imageData.height, radius);

      const resultData = new Uint8ClampedArray(
        this.module.HEAPU8.buffer,
        ptr,
        size
      );
      const result = new ImageData(
        new Uint8ClampedArray(resultData),
        imageData.width,
        imageData.height
      );

      this.module.free_memory(ptr);

      const processingTime = performance.now() - startTime;
      const memoryUsed = this.getMemoryUsage() - startMemory;

      return {
        result,
        metrics: {
          success: true,
          processingTime,
          memoryUsed,
        }
      };
    } catch (error) {
      const processingTime = performance.now() - startTime;
      return {
        result: imageData,
        metrics: {
          success: false,
          processingTime,
          memoryUsed: 0,
          error: (error as Error).message,
        }
      };
    }
  }

  /**
   * Apply image sharpening
   */
  async sharpenImage(
    imageData: ImageData,
    amount: number = 0.5
  ): Promise<{ result: ImageData; metrics: ProcessingResult }> {
    if (!this.isInitialized || !this.module) {
      throw new Error('WASM module not initialized');
    }

    const startTime = performance.now();
    
    try {
      const size = imageData.width * imageData.height * 4;
      const ptr = this.module.allocate_memory(size);

      this.module.HEAPU8.set(imageData.data, ptr);
      this.module.sharpen_image(ptr, imageData.width, imageData.height, amount);

      const resultData = new Uint8ClampedArray(this.module.HEAPU8.buffer, ptr, size);
      const result = new ImageData(
        new Uint8ClampedArray(resultData),
        imageData.width,
        imageData.height
      );

      this.module.free_memory(ptr);

      return {
        result,
        metrics: {
          success: true,
          processingTime: performance.now() - startTime,
          memoryUsed: size,
        }
      };
    } catch (error) {
      return {
        result: imageData,
        metrics: {
          success: false,
          processingTime: performance.now() - startTime,
          memoryUsed: 0,
          error: (error as Error).message,
        }
      };
    }
  }

  /**
   * Adjust brightness and contrast
   */
  async adjustBrightnessContrast(
    imageData: ImageData,
    brightness: number = 0,
    contrast: number = 0
  ): Promise<{ result: ImageData; metrics: ProcessingResult }> {
    if (!this.isInitialized || !this.module) {
      throw new Error('WASM module not initialized');
    }

    const startTime = performance.now();
    
    try {
      const size = imageData.width * imageData.height * 4;
      const ptr = this.module.allocate_memory(size);

      this.module.HEAPU8.set(imageData.data, ptr);
      this.module.adjust_brightness_contrast(
        ptr, imageData.width, imageData.height, brightness, contrast
      );

      const resultData = new Uint8ClampedArray(this.module.HEAPU8.buffer, ptr, size);
      const result = new ImageData(
        new Uint8ClampedArray(resultData),
        imageData.width,
        imageData.height
      );

      this.module.free_memory(ptr);

      return {
        result,
        metrics: {
          success: true,
          processingTime: performance.now() - startTime,
          memoryUsed: size,
        }
      };
    } catch (error) {
      return {
        result: imageData,
        metrics: {
          success: false,
          processingTime: performance.now() - startTime,
          memoryUsed: 0,
          error: (error as Error).message,
        }
      };
    }
  }

  /**
   * Batch process multiple operations on an image
   */
  async batchProcess(
    imageData: ImageData,
    operations: Array<{
      type: 'resize' | 'blur' | 'sharpen' | 'brightness' | 'temperature' | 'hsv';
      params: any;
    }>
  ): Promise<{ result: ImageData; metrics: ProcessingResult[] }> {
    const metrics: ProcessingResult[] = [];
    let currentImageData = imageData;

    for (const operation of operations) {
      let result;
      
      switch (operation.type) {
        case 'resize':
          result = await this.resizeImage(
            currentImageData,
            operation.params.width,
            operation.params.height
          );
          break;
        case 'blur':
          result = await this.blurImage(currentImageData, operation.params.radius);
          break;
        case 'sharpen':
          result = await this.sharpenImage(currentImageData, operation.params.amount);
          break;
        case 'brightness':
          result = await this.adjustBrightnessContrast(
            currentImageData,
            operation.params.brightness,
            operation.params.contrast
          );
          break;
        default:
          continue;
      }

      currentImageData = result.result;
      metrics.push(result.metrics);
    }

    return { result: currentImageData, metrics };
  }

  /**
   * Process image using Web Worker (non-blocking)
   */
  async processInWorker(
    operation: string,
    imageData: ImageData,
    options: any
  ): Promise<{ result: ImageData; metrics: ProcessingResult }> {
    if (!this.worker) {
      throw new Error('Worker not initialized');
    }

    return new Promise((resolve, reject) => {
      const id = Math.random().toString(36).substr(2, 9);
      
      const handleMessage = (event: MessageEvent) => {
        if (event.data.id === id) {
          this.worker!.removeEventListener('message', handleMessage);
          
          if (event.data.success) {
            resolve({
              result: event.data.result,
              metrics: {
                success: true,
                processingTime: event.data.processingTime,
                memoryUsed: 0,
              }
            });
          } else {
            reject(new Error(event.data.error));
          }
        }
      };

      this.worker.addEventListener('message', handleMessage);
      this.worker.postMessage({
        operation,
        data: imageData,
        options,
        id
      });
    });
  }

  /**
   * Get current memory usage for profiling
   */
  private getMemoryUsage(): number {
    if ('memory' in performance) {
      return (performance as any).memory.usedJSHeapSize;
    }
    return 0;
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
    }
    
    this.module = null;
    this.isInitialized = false;
    this.processingQueue = [];
  }

  /**
   * Get processing statistics
   */
  getStats(): {
    isInitialized: boolean;
    hasWorker: boolean;
    activeOperations: number;
    queueLength: number;
  } {
    return {
      isInitialized: this.isInitialized,
      hasWorker: !!this.worker,
      activeOperations: this.activeOperations,
      queueLength: this.processingQueue.length,
    };
  }
}

// Singleton instance with default configuration
export const wasmImageProcessor = new WASMImageProcessor({
  useWorker: true,
  maxConcurrency: 2,
  enableProfiling: process.env.NODE_ENV === 'development',
});

// React Hook for WASM image processing
export const useWASMImageProcessor = () => {
  const [isReady, setIsReady] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    wasmImageProcessor.initialize()
      .then(() => setIsReady(true))
      .catch((err) => setError(err.message));
  }, []);

  const processImage = React.useCallback(async (
    imageData: ImageData,
    operation: string,
    params: any
  ) => {
    if (!isReady) throw new Error('WASM processor not ready');

    switch (operation) {
      case 'resize':
        return wasmImageProcessor.resizeImage(imageData, params.width, params.height);
      case 'blur':
        return wasmImageProcessor.blurImage(imageData, params.radius);
      case 'sharpen':
        return wasmImageProcessor.sharpenImage(imageData, params.amount);
      case 'brightness':
        return wasmImageProcessor.adjustBrightnessContrast(
          imageData, params.brightness, params.contrast
        );
      default:
        throw new Error(`Unknown operation: ${operation}`);
    }
  }, [isReady]);

  return {
    isReady,
    error,
    processImage,
    processor: wasmImageProcessor,
  };
};

export default WASMImageProcessor;