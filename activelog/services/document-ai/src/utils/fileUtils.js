const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const config = require('../config/config');
const logger = require('./logger');

class FileUtils {
  static ensureDirectoryExists(dirPath) {
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
      logger.info(`Created directory: ${dirPath}`);
    }
  }

  static generateUniqueFilename(originalName) {
    const ext = path.extname(originalName);
    const name = path.basename(originalName, ext);
    const timestamp = Date.now();
    const hash = crypto.randomBytes(8).toString('hex');
    return `${name}_${timestamp}_${hash}${ext}`;
  }

  static getFileExtension(filename) {
    return path.extname(filename).toLowerCase().slice(1);
  }

  static isValidFileFormat(filename) {
    const ext = this.getFileExtension(filename);
    return config.processing.supportedFormats.includes(ext);
  }

  static async saveUploadedFile(file, directory = config.processing.tempDir) {
    this.ensureDirectoryExists(directory);
    
    const filename = this.generateUniqueFilename(file.originalname);
    const filepath = path.join(directory, filename);
    
    await fs.promises.writeFile(filepath, file.buffer);
    logger.info(`Saved file: ${filepath}`);
    
    return {
      filename,
      filepath,
      originalName: file.originalname,
      size: file.size,
      mimetype: file.mimetype
    };
  }

  static async deleteFile(filepath) {
    try {
      if (fs.existsSync(filepath)) {
        await fs.promises.unlink(filepath);
        logger.info(`Deleted file: ${filepath}`);
      }
    } catch (error) {
      logger.error(`Error deleting file ${filepath}:`, error);
    }
  }

  static async cleanupTempFiles(maxAge = 24 * 60 * 60 * 1000) { // 24 hours
    const tempDir = config.processing.tempDir;
    
    if (!fs.existsSync(tempDir)) {
      return;
    }

    const files = await fs.promises.readdir(tempDir);
    const now = Date.now();

    for (const file of files) {
      const filepath = path.join(tempDir, file);
      const stats = await fs.promises.stat(filepath);
      
      if (now - stats.mtime.getTime() > maxAge) {
        await this.deleteFile(filepath);
      }
    }
  }

  static getFileSizeInMB(size) {
    return (size / (1024 * 1024)).toFixed(2);
  }

  static validateFileSize(size, maxSizeMB = 50) {
    const sizeInMB = this.getFileSizeInMB(size);
    return parseFloat(sizeInMB) <= maxSizeMB;
  }

  static async readFileAsBuffer(filepath) {
    return await fs.promises.readFile(filepath);
  }

  static async saveProcessingResult(result, outputDir = config.processing.outputDir) {
    this.ensureDirectoryExists(outputDir);
    
    const filename = `result_${Date.now()}_${crypto.randomBytes(4).toString('hex')}.json`;
    const filepath = path.join(outputDir, filename);
    
    await fs.promises.writeFile(filepath, JSON.stringify(result, null, 2));
    logger.info(`Saved processing result: ${filepath}`);
    
    return { filename, filepath };
  }
}

module.exports = FileUtils;