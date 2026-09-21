const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const logger = require('./logger');

class FileUtils {
  static async ensureDirectory(dirPath) {
    try {
      await fs.mkdir(dirPath, { recursive: true });
      return true;
    } catch (error) {
      logger.error(`Failed to create directory ${dirPath}:`, error);
      return false;
    }
  }

  static async fileExists(filePath) {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  static async getFileSize(filePath) {
    try {
      const stats = await fs.stat(filePath);
      return stats.size;
    } catch (error) {
      logger.warn(`Failed to get file size for ${filePath}:`, error);
      return 0;
    }
  }

  static async getFileMimeType(filePath) {
    const extension = path.extname(filePath).toLowerCase();
    const mimeTypes = {
      '.mp4': 'video/mp4',
      '.avi': 'video/avi',
      '.mkv': 'video/x-matroska',
      '.mov': 'video/quicktime',
      '.wmv': 'video/x-ms-wmv',
      '.flv': 'video/x-flv',
      '.webm': 'video/webm',
      '.m4v': 'video/mp4',
      '.3gp': 'video/3gpp',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.png': 'image/png',
      '.gif': 'image/gif',
      '.bmp': 'image/bmp',
      '.tiff': 'image/tiff',
      '.srt': 'text/srt',
      '.vtt': 'text/vtt',
      '.ass': 'text/ass',
      '.ssa': 'text/ssa',
      '.json': 'application/json',
      '.txt': 'text/plain'
    };

    return mimeTypes[extension] || 'application/octet-stream';
  }

  static async calculateFileHash(filePath, algorithm = 'md5') {
    try {
      const hash = crypto.createHash(algorithm);
      const stream = require('fs').createReadStream(filePath);
      
      return new Promise((resolve, reject) => {
        stream.on('data', data => hash.update(data));
        stream.on('end', () => resolve(hash.digest('hex')));
        stream.on('error', reject);
      });
    } catch (error) {
      logger.error(`Failed to calculate hash for ${filePath}:`, error);
      throw error;
    }
  }

  static async copyFile(source, destination) {
    try {
      await FileUtils.ensureDirectory(path.dirname(destination));
      await fs.copyFile(source, destination);
      return true;
    } catch (error) {
      logger.error(`Failed to copy file from ${source} to ${destination}:`, error);
      return false;
    }
  }

  static async moveFile(source, destination) {
    try {
      await FileUtils.ensureDirectory(path.dirname(destination));
      await fs.rename(source, destination);
      return true;
    } catch (error) {
      logger.error(`Failed to move file from ${source} to ${destination}:`, error);
      return false;
    }
  }

  static async deleteFile(filePath) {
    try {
      if (await FileUtils.fileExists(filePath)) {
        await fs.unlink(filePath);
        return true;
      }
      return false;
    } catch (error) {
      logger.error(`Failed to delete file ${filePath}:`, error);
      return false;
    }
  }

  static async deleteDirectory(dirPath, recursive = false) {
    try {
      if (recursive) {
        await fs.rmdir(dirPath, { recursive: true });
      } else {
        await fs.rmdir(dirPath);
      }
      return true;
    } catch (error) {
      logger.error(`Failed to delete directory ${dirPath}:`, error);
      return false;
    }
  }

  static async listFiles(dirPath, pattern = null) {
    try {
      const files = await fs.readdir(dirPath);
      
      if (pattern) {
        const regex = new RegExp(pattern);
        return files.filter(file => regex.test(file));
      }
      
      return files;
    } catch (error) {
      logger.error(`Failed to list files in ${dirPath}:`, error);
      return [];
    }
  }

  static async getFileStats(filePath) {
    try {
      const stats = await fs.stat(filePath);
      return {
        size: stats.size,
        created: stats.birthtime,
        modified: stats.mtime,
        accessed: stats.atime,
        isFile: stats.isFile(),
        isDirectory: stats.isDirectory()
      };
    } catch (error) {
      logger.error(`Failed to get file stats for ${filePath}:`, error);
      return null;
    }
  }

  static formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  static getFileExtension(filePath) {
    return path.extname(filePath).toLowerCase();
  }

  static getFileName(filePath, includeExtension = true) {
    if (includeExtension) {
      return path.basename(filePath);
    }
    return path.basename(filePath, path.extname(filePath));
  }

  static generateUniqueFileName(originalName, directory) {
    const extension = path.extname(originalName);
    const baseName = path.basename(originalName, extension);
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    
    return path.join(directory, `${baseName}_${timestamp}_${random}${extension}`);
  }

  static async isWritable(dirPath) {
    try {
      await fs.access(dirPath, fs.constants.W_OK);
      return true;
    } catch {
      return false;
    }
  }

  static async getDiskSpace(dirPath) {
    try {
      const stats = await fs.statvfs ? fs.statvfs(dirPath) : null;
      if (stats) {
        return {
          free: stats.bavail * stats.frsize,
          total: stats.blocks * stats.frsize,
          used: (stats.blocks - stats.bavail) * stats.frsize
        };
      }
      return null;
    } catch (error) {
      logger.warn(`Failed to get disk space for ${dirPath}:`, error);
      return null;
    }
  }

  static async cleanupOldFiles(dirPath, maxAge = 86400000, pattern = null) {
    try {
      const files = await FileUtils.listFiles(dirPath, pattern);
      const now = Date.now();
      let deletedCount = 0;

      for (const file of files) {
        const filePath = path.join(dirPath, file);
        const stats = await FileUtils.getFileStats(filePath);
        
        if (stats && (now - stats.modified.getTime()) > maxAge) {
          if (await FileUtils.deleteFile(filePath)) {
            deletedCount++;
          }
        }
      }

      logger.info(`Cleaned up ${deletedCount} old files in ${dirPath}`);
      return deletedCount;
    } catch (error) {
      logger.error(`Failed to cleanup old files in ${dirPath}:`, error);
      return 0;
    }
  }

  static async validateVideoFile(filePath) {
    try {
      const stats = await FileUtils.getFileStats(filePath);
      if (!stats || !stats.isFile) {
        return { valid: false, error: 'File does not exist or is not a file' };
      }

      if (stats.size === 0) {
        return { valid: false, error: 'File is empty' };
      }

      const mimeType = await FileUtils.getFileMimeType(filePath);
      if (!mimeType.startsWith('video/')) {
        return { valid: false, error: 'File is not a video file' };
      }

      return { valid: true, mimeType, size: stats.size };
    } catch (error) {
      logger.error(`Failed to validate video file ${filePath}:`, error);
      return { valid: false, error: error.message };
    }
  }

  static async createTempFile(content, extension = '.tmp', directory = './temp') {
    try {
      await FileUtils.ensureDirectory(directory);
      const fileName = `temp_${Date.now()}_${Math.random().toString(36).substring(2)}${extension}`;
      const filePath = path.join(directory, fileName);
      
      await fs.writeFile(filePath, content);
      return filePath;
    } catch (error) {
      logger.error('Failed to create temp file:', error);
      throw error;
    }
  }

  static async readFileChunks(filePath, chunkSize = 1024 * 1024) {
    try {
      const stats = await fs.stat(filePath);
      const fileSize = stats.size;
      const chunks = [];
      
      const fileHandle = await fs.open(filePath, 'r');
      
      for (let position = 0; position < fileSize; position += chunkSize) {
        const buffer = Buffer.alloc(Math.min(chunkSize, fileSize - position));
        await fileHandle.read(buffer, 0, buffer.length, position);
        chunks.push(buffer);
      }
      
      await fileHandle.close();
      return chunks;
    } catch (error) {
      logger.error(`Failed to read file chunks from ${filePath}:`, error);
      throw error;
    }
  }
}

module.exports = FileUtils;