const cv = require('opencv4nodejs');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const logger = require('./utils/logger');

class KeyframeExtractor {
  constructor(options = {}) {
    this.threshold = options.threshold || 0.3;
    this.minFrameDistance = options.minFrameDistance || 30;
    this.maxKeyframes = options.maxKeyframes || 50;
    this.outputDir = options.outputDir || './output/keyframes';
  }

  async ensureOutputDir() {
    try {
      await fs.mkdir(this.outputDir, { recursive: true });
    } catch (error) {
      logger.error('Failed to create output directory:', error);
      throw error;
    }
  }

  calculateHistogramDifference(hist1, hist2) {
    if (!hist1 || !hist2) return 1.0;
    
    try {
      const correlation = cv.compareHist(hist1, hist2, cv.HISTCMP_CORREL);
      return 1.0 - correlation;
    } catch (error) {
      logger.warn('Failed to calculate histogram difference:', error);
      return 1.0;
    }
  }

  computeHistogram(frame) {
    try {
      const grayFrame = frame.cvtColor(cv.COLOR_BGR2GRAY);
      const hist = cv.calcHist([grayFrame], [0], new cv.Mat(), [256], [0, 256]);
      return hist;
    } catch (error) {
      logger.warn('Failed to compute histogram:', error);
      return null;
    }
  }

  async extractKeyframes(videoPath, outputOptions = {}) {
    const sessionId = uuidv4();
    logger.info(`Starting keyframe extraction for ${videoPath} (session: ${sessionId})`);

    try {
      await this.ensureOutputDir();
      
      const cap = new cv.VideoCapture(videoPath);
      const totalFrames = cap.get(cv.CAP_PROP_FRAME_COUNT);
      const fps = cap.get(cv.CAP_PROP_FPS);
      
      if (totalFrames <= 0 || fps <= 0) {
        throw new Error('Invalid video file or unable to read video properties');
      }

      logger.info(`Video info: ${totalFrames} frames, ${fps} FPS`);

      const keyframes = [];
      let previousHist = null;
      let frameNumber = 0;
      let lastKeyframeIndex = -this.minFrameDistance;

      while (true) {
        const frame = cap.read();
        if (frame.empty) break;

        const currentHist = this.computeHistogram(frame);
        
        if (previousHist && currentHist) {
          const difference = this.calculateHistogramDifference(previousHist, currentHist);
          
          const shouldExtract = difference > this.threshold && 
                               (frameNumber - lastKeyframeIndex) >= this.minFrameDistance &&
                               keyframes.length < this.maxKeyframes;

          if (shouldExtract) {
            const timestamp = frameNumber / fps;
            const filename = `keyframe_${sessionId}_${frameNumber}_${timestamp.toFixed(2)}s.jpg`;
            const outputPath = path.join(this.outputDir, filename);

            try {
              cv.imwrite(outputPath, frame);
              
              keyframes.push({
                frameNumber,
                timestamp,
                filename,
                path: outputPath,
                difference: difference.toFixed(4)
              });

              lastKeyframeIndex = frameNumber;
              logger.debug(`Extracted keyframe at frame ${frameNumber} (${timestamp.toFixed(2)}s)`);
            } catch (writeError) {
              logger.warn(`Failed to save keyframe ${filename}:`, writeError);
            }
          }
        }

        previousHist = currentHist;
        frameNumber++;

        if (outputOptions.onProgress) {
          const progress = (frameNumber / totalFrames) * 100;
          outputOptions.onProgress(progress, frameNumber, totalFrames);
        }
      }

      cap.release();

      const result = {
        sessionId,
        videoPath,
        totalFrames,
        fps,
        keyframes,
        processingTime: Date.now()
      };

      logger.info(`Keyframe extraction completed. Found ${keyframes.length} keyframes (session: ${sessionId})`);
      return result;

    } catch (error) {
      logger.error(`Keyframe extraction failed for ${videoPath}:`, error);
      throw error;
    }
  }

  async extractUniformKeyframes(videoPath, count = 10) {
    const sessionId = uuidv4();
    logger.info(`Extracting ${count} uniform keyframes for ${videoPath} (session: ${sessionId})`);

    try {
      await this.ensureOutputDir();
      
      const cap = new cv.VideoCapture(videoPath);
      const totalFrames = cap.get(cv.CAP_PROP_FRAME_COUNT);
      const fps = cap.get(cv.CAP_PROP_FPS);
      
      if (totalFrames <= 0 || fps <= 0) {
        throw new Error('Invalid video file');
      }

      const interval = Math.floor(totalFrames / (count + 1));
      const keyframes = [];

      for (let i = 1; i <= count; i++) {
        const frameNumber = i * interval;
        cap.set(cv.CAP_PROP_POS_FRAMES, frameNumber);
        
        const frame = cap.read();
        if (!frame.empty) {
          const timestamp = frameNumber / fps;
          const filename = `uniform_keyframe_${sessionId}_${i}_${frameNumber}_${timestamp.toFixed(2)}s.jpg`;
          const outputPath = path.join(this.outputDir, filename);

          try {
            cv.imwrite(outputPath, frame);
            
            keyframes.push({
              frameNumber,
              timestamp,
              filename,
              path: outputPath,
              index: i
            });
          } catch (writeError) {
            logger.warn(`Failed to save uniform keyframe ${filename}:`, writeError);
          }
        }
      }

      cap.release();

      logger.info(`Extracted ${keyframes.length} uniform keyframes (session: ${sessionId})`);
      return {
        sessionId,
        videoPath,
        totalFrames,
        fps,
        keyframes,
        method: 'uniform'
      };

    } catch (error) {
      logger.error(`Uniform keyframe extraction failed for ${videoPath}:`, error);
      throw error;
    }
  }

  async getVideoInfo(videoPath) {
    try {
      const cap = new cv.VideoCapture(videoPath);
      const info = {
        totalFrames: cap.get(cv.CAP_PROP_FRAME_COUNT),
        fps: cap.get(cv.CAP_PROP_FPS),
        width: cap.get(cv.CAP_PROP_FRAME_WIDTH),
        height: cap.get(cv.CAP_PROP_FRAME_HEIGHT),
        duration: cap.get(cv.CAP_PROP_FRAME_COUNT) / cap.get(cv.CAP_PROP_FPS)
      };
      cap.release();
      return info;
    } catch (error) {
      logger.error(`Failed to get video info for ${videoPath}:`, error);
      throw error;
    }
  }
}

module.exports = KeyframeExtractor;