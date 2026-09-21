const cv = require('opencv4nodejs');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const logger = require('./utils/logger');

class SceneDetector {
  constructor(options = {}) {
    this.threshold = options.threshold || 0.4;
    this.minSceneDuration = options.minSceneDuration || 2;
    this.outputDir = options.outputDir || './output/scenes';
    this.histogramMethod = options.histogramMethod || 'correlation';
    this.adaptiveThreshold = options.adaptiveThreshold || false;
  }

  async ensureOutputDir() {
    try {
      await fs.mkdir(this.outputDir, { recursive: true });
    } catch (error) {
      logger.error('Failed to create output directory:', error);
      throw error;
    }
  }

  calculateFrameDifference(hist1, hist2, method = 'correlation') {
    if (!hist1 || !hist2) return 1.0;
    
    try {
      let difference;
      switch (method) {
        case 'correlation':
          const correlation = cv.compareHist(hist1, hist2, cv.HISTCMP_CORREL);
          difference = 1.0 - correlation;
          break;
        case 'chi_square':
          difference = cv.compareHist(hist1, hist2, cv.HISTCMP_CHISQR);
          break;
        case 'intersection':
          const intersection = cv.compareHist(hist1, hist2, cv.HISTCMP_INTERSECT);
          difference = 1.0 - (intersection / Math.max(cv.norm(hist1), cv.norm(hist2)));
          break;
        case 'bhattacharyya':
          difference = cv.compareHist(hist1, hist2, cv.HISTCMP_BHATTACHARYYA);
          break;
        default:
          difference = 1.0 - cv.compareHist(hist1, hist2, cv.HISTCMP_CORREL);
      }
      return Math.max(0, Math.min(1, difference));
    } catch (error) {
      logger.warn('Failed to calculate frame difference:', error);
      return 1.0;
    }
  }

  computeColorHistogram(frame) {
    try {
      const bgrChannels = frame.split();
      const histSize = [50];
      const ranges = [0, 256];
      
      const histB = cv.calcHist([bgrChannels[0]], [0], new cv.Mat(), histSize, ranges);
      const histG = cv.calcHist([bgrChannels[1]], [0], new cv.Mat(), histSize, ranges);
      const histR = cv.calcHist([bgrChannels[2]], [0], new cv.Mat(), histSize, ranges);
      
      const combinedHist = new cv.Mat(150, 1, cv.CV_32F);
      histB.copyTo(combinedHist.getRegion(new cv.Rect(0, 0, 1, 50)));
      histG.copyTo(combinedHist.getRegion(new cv.Rect(0, 50, 1, 50)));
      histR.copyTo(combinedHist.getRegion(new cv.Rect(0, 100, 1, 50)));
      
      return cv.normalize(combinedHist, new cv.Mat(), 0, 1, cv.NORM_MINMAX);
    } catch (error) {
      logger.warn('Failed to compute color histogram:', error);
      return null;
    }
  }

  computeAdaptiveThreshold(differences, windowSize = 10) {
    const adaptiveThresholds = [];
    
    for (let i = 0; i < differences.length; i++) {
      const start = Math.max(0, i - windowSize);
      const end = Math.min(differences.length, i + windowSize + 1);
      const window = differences.slice(start, end);
      
      const mean = window.reduce((sum, val) => sum + val, 0) / window.length;
      const variance = window.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / window.length;
      const stdDev = Math.sqrt(variance);
      
      const adaptiveThreshold = mean + (2 * stdDev);
      adaptiveThresholds.push(Math.max(this.threshold, adaptiveThreshold));
    }
    
    return adaptiveThresholds;
  }

  async detectScenes(videoPath, outputOptions = {}) {
    const sessionId = uuidv4();
    logger.info(`Starting scene detection for ${videoPath} (session: ${sessionId})`);

    try {
      await this.ensureOutputDir();
      
      const cap = new cv.VideoCapture(videoPath);
      const totalFrames = cap.get(cv.CAP_PROP_FRAME_COUNT);
      const fps = cap.get(cv.CAP_PROP_FPS);
      
      if (totalFrames <= 0 || fps <= 0) {
        throw new Error('Invalid video file or unable to read video properties');
      }

      const minFrameDistance = Math.floor(this.minSceneDuration * fps);
      
      logger.info(`Video info: ${totalFrames} frames, ${fps} FPS, min scene duration: ${this.minSceneDuration}s`);

      const sceneCuts = [];
      const frameDifferences = [];
      let previousHist = null;
      let frameNumber = 0;

      while (true) {
        const frame = cap.read();
        if (frame.empty) break;

        const currentHist = this.computeColorHistogram(frame);
        
        if (previousHist && currentHist) {
          const difference = this.calculateFrameDifference(previousHist, currentHist, this.histogramMethod);
          frameDifferences.push(difference);
        }

        previousHist = currentHist;
        frameNumber++;

        if (outputOptions.onProgress && frameNumber % 100 === 0) {
          const progress = (frameNumber / totalFrames) * 50;
          outputOptions.onProgress(progress, frameNumber, totalFrames, 'analyzing');
        }
      }

      cap.release();

      const thresholds = this.adaptiveThreshold ? 
        this.computeAdaptiveThreshold(frameDifferences) : 
        new Array(frameDifferences.length).fill(this.threshold);

      let lastCutFrame = 0;
      for (let i = 0; i < frameDifferences.length; i++) {
        const difference = frameDifferences[i];
        const threshold = thresholds[i];
        const currentFrame = i + 1;

        if (difference > threshold && (currentFrame - lastCutFrame) >= minFrameDistance) {
          const timestamp = currentFrame / fps;
          sceneCuts.push({
            frameNumber: currentFrame,
            timestamp,
            difference: difference.toFixed(4),
            threshold: threshold.toFixed(4)
          });
          lastCutFrame = currentFrame;
        }
      }

      const scenes = await this.generateSceneSegments(videoPath, sceneCuts, fps, totalFrames, outputOptions);

      const result = {
        sessionId,
        videoPath,
        totalFrames,
        fps,
        sceneCuts,
        scenes,
        statistics: {
          totalScenes: scenes.length,
          averageSceneDuration: scenes.reduce((sum, scene) => sum + scene.duration, 0) / scenes.length,
          minSceneDuration: Math.min(...scenes.map(scene => scene.duration)),
          maxSceneDuration: Math.max(...scenes.map(scene => scene.duration)),
          detectionMethod: this.histogramMethod,
          adaptiveThreshold: this.adaptiveThreshold
        }
      };

      logger.info(`Scene detection completed. Found ${scenes.length} scenes (session: ${sessionId})`);
      return result;

    } catch (error) {
      logger.error(`Scene detection failed for ${videoPath}:`, error);
      throw error;
    }
  }

  async generateSceneSegments(videoPath, sceneCuts, fps, totalFrames, outputOptions = {}) {
    const scenes = [];
    
    const cutFrames = [0, ...sceneCuts.map(cut => cut.frameNumber), totalFrames];
    
    for (let i = 0; i < cutFrames.length - 1; i++) {
      const startFrame = cutFrames[i];
      const endFrame = cutFrames[i + 1];
      const startTime = startFrame / fps;
      const endTime = endFrame / fps;
      const duration = endTime - startTime;

      const scene = {
        id: i,
        startFrame,
        endFrame,
        startTime: parseFloat(startTime.toFixed(2)),
        endTime: parseFloat(endTime.toFixed(2)),
        duration: parseFloat(duration.toFixed(2)),
        frameCount: endFrame - startFrame
      };

      if (outputOptions.extractThumbnails) {
        const middleFrame = Math.floor((startFrame + endFrame) / 2);
        const middleTime = middleFrame / fps;
        
        try {
          const thumbnailPath = await this.extractSceneThumbnail(videoPath, middleTime, i);
          scene.thumbnail = thumbnailPath;
        } catch (error) {
          logger.warn(`Failed to extract thumbnail for scene ${i}:`, error);
        }
      }

      scenes.push(scene);

      if (outputOptions.onProgress) {
        const progress = 50 + ((i + 1) / (cutFrames.length - 1)) * 50;
        outputOptions.onProgress(progress, i + 1, cutFrames.length - 1, 'generating_segments');
      }
    }

    return scenes;
  }

  async extractSceneThumbnail(videoPath, timestamp, sceneId) {
    try {
      const cap = new cv.VideoCapture(videoPath);
      cap.set(cv.CAP_PROP_POS_MSEC, timestamp * 1000);
      
      const frame = cap.read();
      if (!frame.empty) {
        const filename = `scene_${sceneId}_thumbnail_${timestamp.toFixed(2)}s.jpg`;
        const outputPath = path.join(this.outputDir, filename);
        cv.imwrite(outputPath, frame);
        cap.release();
        return outputPath;
      }
      
      cap.release();
      return null;
    } catch (error) {
      logger.warn(`Failed to extract scene thumbnail:`, error);
      return null;
    }
  }

  async analyzeSceneContent(videoPath, scenes, options = {}) {
    const sessionId = uuidv4();
    logger.info(`Analyzing scene content for ${videoPath} (session: ${sessionId})`);

    try {
      const enhancedScenes = [];

      for (let i = 0; i < scenes.length; i++) {
        const scene = { ...scenes[i] };
        
        const analysis = await this.analyzeIndividualScene(videoPath, scene, options);
        scene.analysis = analysis;
        
        enhancedScenes.push(scene);

        if (options.onProgress) {
          const progress = ((i + 1) / scenes.length) * 100;
          options.onProgress(progress, i + 1, scenes.length);
        }
      }

      logger.info(`Scene content analysis completed for ${enhancedScenes.length} scenes (session: ${sessionId})`);
      return enhancedScenes;

    } catch (error) {
      logger.error(`Scene content analysis failed for ${videoPath}:`, error);
      throw error;
    }
  }

  async analyzeIndividualScene(videoPath, scene, options = {}) {
    try {
      const cap = new cv.VideoCapture(videoPath);
      cap.set(cv.CAP_PROP_POS_FRAMES, scene.startFrame);

      const sampleFrames = [];
      const sampleCount = Math.min(5, Math.floor(scene.frameCount / 10));
      const frameInterval = Math.floor(scene.frameCount / (sampleCount + 1));

      for (let i = 1; i <= sampleCount; i++) {
        const targetFrame = scene.startFrame + (i * frameInterval);
        cap.set(cv.CAP_PROP_POS_FRAMES, targetFrame);
        
        const frame = cap.read();
        if (!frame.empty) {
          sampleFrames.push(frame);
        }
      }

      cap.release();

      const analysis = {
        averageBrightness: this.calculateAverageBrightness(sampleFrames),
        colorDistribution: this.analyzeColorDistribution(sampleFrames),
        motionLevel: this.estimateMotionLevel(scene),
        complexity: this.calculateVisualComplexity(sampleFrames)
      };

      return analysis;

    } catch (error) {
      logger.warn(`Failed to analyze individual scene:`, error);
      return null;
    }
  }

  calculateAverageBrightness(frames) {
    if (frames.length === 0) return 0;

    let totalBrightness = 0;
    for (const frame of frames) {
      try {
        const gray = frame.cvtColor(cv.COLOR_BGR2GRAY);
        const mean = cv.mean(gray);
        totalBrightness += mean[0];
      } catch (error) {
        logger.warn('Failed to calculate brightness:', error);
      }
    }

    return totalBrightness / frames.length;
  }

  analyzeColorDistribution(frames) {
    if (frames.length === 0) return null;

    try {
      const combinedHist = { b: 0, g: 0, r: 0 };
      
      for (const frame of frames) {
        const channels = frame.split();
        const meanB = cv.mean(channels[0])[0];
        const meanG = cv.mean(channels[1])[0];
        const meanR = cv.mean(channels[2])[0];
        
        combinedHist.b += meanB;
        combinedHist.g += meanG;
        combinedHist.r += meanR;
      }

      const frameCount = frames.length;
      return {
        blue: combinedHist.b / frameCount,
        green: combinedHist.g / frameCount,
        red: combinedHist.r / frameCount
      };
    } catch (error) {
      logger.warn('Failed to analyze color distribution:', error);
      return null;
    }
  }

  estimateMotionLevel(scene) {
    const durationFactor = Math.min(scene.duration / 10, 1);
    const frameDensity = scene.frameCount / scene.duration;
    return (durationFactor * 0.7) + (frameDensity / 30 * 0.3);
  }

  calculateVisualComplexity(frames) {
    if (frames.length === 0) return 0;

    let totalComplexity = 0;
    for (const frame of frames) {
      try {
        const gray = frame.cvtColor(cv.COLOR_BGR2GRAY);
        const laplacian = gray.laplacian(cv.CV_64F);
        const variance = cv.mean(laplacian.mul(laplacian))[0];
        totalComplexity += variance;
      } catch (error) {
        logger.warn('Failed to calculate visual complexity:', error);
      }
    }

    return totalComplexity / frames.length;
  }
}

module.exports = SceneDetector;