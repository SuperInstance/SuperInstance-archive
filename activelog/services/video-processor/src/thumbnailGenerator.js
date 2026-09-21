const ffmpeg = require('fluent-ffmpeg');
const sharp = require('sharp');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const logger = require('./utils/logger');

class ThumbnailGenerator {
  constructor(options = {}) {
    this.outputDir = options.outputDir || './output/thumbnails';
    this.previewDir = options.previewDir || './output/previews';
    this.thumbnailSizes = options.thumbnailSizes || [
      { width: 160, height: 90, suffix: 'small' },
      { width: 320, height: 180, suffix: 'medium' },
      { width: 640, height: 360, suffix: 'large' }
    ];
    this.previewDuration = options.previewDuration || 10;
    this.previewFramerate = options.previewFramerate || 15;
  }

  async ensureOutputDirs() {
    try {
      await fs.mkdir(this.outputDir, { recursive: true });
      await fs.mkdir(this.previewDir, { recursive: true });
    } catch (error) {
      logger.error('Failed to create output directories:', error);
      throw error;
    }
  }

  async generateThumbnail(videoPath, timestamp = null, outputOptions = {}) {
    const sessionId = uuidv4();
    logger.info(`Generating thumbnail for ${videoPath} (session: ${sessionId})`);

    try {
      await this.ensureOutputDirs();

      const videoInfo = await this.getVideoInfo(videoPath);
      const targetTimestamp = timestamp || videoInfo.duration / 2;

      const baseName = `thumbnail_${sessionId}_${targetTimestamp.toFixed(2)}s`;
      const tempPath = path.join(this.outputDir, `${baseName}_temp.jpg`);

      await new Promise((resolve, reject) => {
        ffmpeg(videoPath)
          .seekInput(targetTimestamp)
          .frames(1)
          .output(tempPath)
          .on('end', resolve)
          .on('error', reject)
          .run();
      });

      const thumbnails = [];

      for (const size of this.thumbnailSizes) {
        const filename = `${baseName}_${size.suffix}.jpg`;
        const outputPath = path.join(this.outputDir, filename);

        await sharp(tempPath)
          .resize(size.width, size.height, {
            fit: 'cover',
            position: 'center'
          })
          .jpeg({ quality: 85 })
          .toFile(outputPath);

        thumbnails.push({
          size: size.suffix,
          width: size.width,
          height: size.height,
          filename,
          path: outputPath,
          timestamp: targetTimestamp
        });
      }

      await fs.unlink(tempPath);

      const result = {
        sessionId,
        videoPath,
        timestamp: targetTimestamp,
        thumbnails,
        videoInfo
      };

      logger.info(`Generated ${thumbnails.length} thumbnails (session: ${sessionId})`);
      return result;

    } catch (error) {
      logger.error(`Thumbnail generation failed for ${videoPath}:`, error);
      throw error;
    }
  }

  async generateMultipleThumbnails(videoPath, timestamps = [], outputOptions = {}) {
    const sessionId = uuidv4();
    logger.info(`Generating multiple thumbnails for ${videoPath} (session: ${sessionId})`);

    try {
      const videoInfo = await this.getVideoInfo(videoPath);
      const targetTimestamps = timestamps.length > 0 ? timestamps : 
        this.generateUniformTimestamps(videoInfo.duration, 5);

      const allThumbnails = [];

      for (let i = 0; i < targetTimestamps.length; i++) {
        const timestamp = targetTimestamps[i];
        
        try {
          const result = await this.generateThumbnail(videoPath, timestamp, outputOptions);
          allThumbnails.push({
            index: i,
            timestamp,
            thumbnails: result.thumbnails
          });

          if (outputOptions.onProgress) {
            const progress = ((i + 1) / targetTimestamps.length) * 100;
            outputOptions.onProgress(progress, i + 1, targetTimestamps.length);
          }
        } catch (error) {
          logger.warn(`Failed to generate thumbnail at ${timestamp}s:`, error);
        }
      }

      logger.info(`Generated thumbnails for ${allThumbnails.length} timestamps (session: ${sessionId})`);
      return {
        sessionId,
        videoPath,
        timestamps: targetTimestamps,
        thumbnails: allThumbnails,
        videoInfo
      };

    } catch (error) {
      logger.error(`Multiple thumbnail generation failed for ${videoPath}:`, error);
      throw error;
    }
  }

  async generatePreview(videoPath, options = {}) {
    const sessionId = uuidv4();
    logger.info(`Generating preview for ${videoPath} (session: ${sessionId})`);

    try {
      await this.ensureOutputDirs();

      const videoInfo = await this.getVideoInfo(videoPath);
      const startTime = options.startTime || 0;
      const duration = Math.min(options.duration || this.previewDuration, videoInfo.duration);
      const framerate = options.framerate || this.previewFramerate;

      const filename = `preview_${sessionId}_${startTime}s_${duration}s.mp4`;
      const outputPath = path.join(this.previewDir, filename);

      await new Promise((resolve, reject) => {
        ffmpeg(videoPath)
          .seekInput(startTime)
          .duration(duration)
          .videoCodec('libx264')
          .audioCodec('aac')
          .size('640x360')
          .fps(framerate)
          .outputOptions([
            '-preset fast',
            '-crf 28',
            '-movflags +faststart'
          ])
          .output(outputPath)
          .on('progress', (progress) => {
            if (options.onProgress) {
              options.onProgress(progress.percent || 0);
            }
          })
          .on('end', resolve)
          .on('error', reject)
          .run();
      });

      const previewInfo = await this.getVideoInfo(outputPath);

      const result = {
        sessionId,
        originalVideo: videoPath,
        preview: {
          filename,
          path: outputPath,
          startTime,
          duration,
          framerate,
          size: await this.getFileSize(outputPath),
          info: previewInfo
        },
        originalVideoInfo: videoInfo
      };

      logger.info(`Generated preview: ${filename} (session: ${sessionId})`);
      return result;

    } catch (error) {
      logger.error(`Preview generation failed for ${videoPath}:`, error);
      throw error;
    }
  }

  async generateGif(videoPath, options = {}) {
    const sessionId = uuidv4();
    logger.info(`Generating GIF for ${videoPath} (session: ${sessionId})`);

    try {
      await this.ensureOutputDirs();

      const startTime = options.startTime || 0;
      const duration = Math.min(options.duration || 5, 10);
      const fps = options.fps || 10;
      const width = options.width || 320;

      const filename = `preview_${sessionId}_${startTime}s_${duration}s.gif`;
      const outputPath = path.join(this.previewDir, filename);

      await new Promise((resolve, reject) => {
        ffmpeg(videoPath)
          .seekInput(startTime)
          .duration(duration)
          .fps(fps)
          .size(`${width}x?`)
          .outputOptions([
            '-vf scale=' + width + ':-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
            '-loop 0'
          ])
          .output(outputPath)
          .on('progress', (progress) => {
            if (options.onProgress) {
              options.onProgress(progress.percent || 0);
            }
          })
          .on('end', resolve)
          .on('error', reject)
          .run();
      });

      const result = {
        sessionId,
        originalVideo: videoPath,
        gif: {
          filename,
          path: outputPath,
          startTime,
          duration,
          fps,
          width,
          size: await this.getFileSize(outputPath)
        }
      };

      logger.info(`Generated GIF: ${filename} (session: ${sessionId})`);
      return result;

    } catch (error) {
      logger.error(`GIF generation failed for ${videoPath}:`, error);
      throw error;
    }
  }

  generateUniformTimestamps(duration, count) {
    const timestamps = [];
    const interval = duration / (count + 1);
    
    for (let i = 1; i <= count; i++) {
      timestamps.push(i * interval);
    }
    
    return timestamps;
  }

  async getVideoInfo(videoPath) {
    return new Promise((resolve, reject) => {
      ffmpeg.ffprobe(videoPath, (err, metadata) => {
        if (err) {
          reject(err);
          return;
        }

        const videoStream = metadata.streams.find(stream => stream.codec_type === 'video');
        
        resolve({
          duration: metadata.format.duration,
          width: videoStream?.width || 0,
          height: videoStream?.height || 0,
          fps: videoStream?.r_frame_rate ? eval(videoStream.r_frame_rate) : 0,
          bitrate: metadata.format.bit_rate,
          size: metadata.format.size
        });
      });
    });
  }

  async getFileSize(filePath) {
    try {
      const stats = await fs.stat(filePath);
      return stats.size;
    } catch (error) {
      logger.warn(`Failed to get file size for ${filePath}:`, error);
      return 0;
    }
  }
}

module.exports = ThumbnailGenerator;