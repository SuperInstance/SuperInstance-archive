const archiver = require('archiver');
const tar = require('tar');
const fs = require('fs-extra');
const path = require('path');
const crypto = require('crypto');
const logger = require('../utils/logger');

class ArchiveExporter {
  constructor(options = {}) {
    this.options = {
      compressionLevel: options.compressionLevel || 6,
      includeMetadata: options.includeMetadata !== false,
      preservePermissions: options.preservePermissions !== false,
      generateChecksum: options.generateChecksum !== false,
      excludePatterns: options.excludePatterns || [],
      maxFileSize: options.maxFileSize || 1024 * 1024 * 1024, // 1GB
      ...options
    };
  }

  async createZipArchive(sources, outputPath, metadata = {}) {
    try {
      const output = fs.createWriteStream(outputPath);
      const archive = archiver('zip', {
        zlib: { level: this.options.compressionLevel }
      });

      archive.pipe(output);

      if (this.options.includeMetadata) {
        const metadataContent = this.generateMetadataFile(metadata, sources);
        archive.append(metadataContent, { name: 'export_metadata.json' });
      }

      await this.addSourcesToArchive(archive, sources);

      await archive.finalize();

      return new Promise((resolve, reject) => {
        output.on('close', async () => {
          const stats = fs.statSync(outputPath);
          const result = {
            success: true,
            outputPath,
            fileSize: stats.size,
            totalBytes: archive.pointer(),
            compressionRatio: (1 - stats.size / archive.pointer()) * 100
          };

          if (this.options.generateChecksum) {
            result.checksum = await this.generateChecksum(outputPath);
          }

          logger.info(`ZIP archive created: ${outputPath} (${this.formatBytes(stats.size)})`);
          resolve(result);
        });

        output.on('error', reject);
        archive.on('error', reject);
      });
    } catch (error) {
      logger.error('ZIP archive creation failed:', error);
      throw error;
    }
  }

  async createTarGzArchive(sources, outputPath, metadata = {}) {
    try {
      const tempDir = path.join(path.dirname(outputPath), 'temp_tar_' + Date.now());
      await fs.ensureDir(tempDir);

      const archiveDir = path.join(tempDir, 'export');
      await fs.ensureDir(archiveDir);

      if (this.options.includeMetadata) {
        const metadataContent = this.generateMetadataFile(metadata, sources);
        await fs.writeFile(
          path.join(archiveDir, 'export_metadata.json'),
          metadataContent
        );
      }

      await this.copySourcesToTempDir(sources, archiveDir);

      await tar.create(
        {
          gzip: true,
          file: outputPath,
          cwd: tempDir,
          portable: true,
          preservePaths: false
        },
        ['export']
      );

      await fs.remove(tempDir);

      const stats = fs.statSync(outputPath);
      const result = {
        success: true,
        outputPath,
        fileSize: stats.size
      };

      if (this.options.generateChecksum) {
        result.checksum = await this.generateChecksum(outputPath);
      }

      logger.info(`TAR.GZ archive created: ${outputPath} (${this.formatBytes(stats.size)})`);
      return result;
    } catch (error) {
      logger.error('TAR.GZ archive creation failed:', error);
      throw error;
    }
  }

  async addSourcesToArchive(archive, sources) {
    for (const source of sources) {
      if (this.shouldExclude(source.path)) {
        continue;
      }

      const stats = await fs.stat(source.path);

      if (stats.size > this.options.maxFileSize) {
        logger.warn(`Skipping large file: ${source.path} (${this.formatBytes(stats.size)})`);
        continue;
      }

      if (stats.isDirectory()) {
        archive.directory(source.path, source.name || path.basename(source.path));
      } else {
        const options = {
          name: source.name || path.basename(source.path)
        };

        if (this.options.preservePermissions) {
          options.mode = stats.mode;
        }

        if (source.metadata) {
          options.comment = JSON.stringify(source.metadata);
        }

        archive.file(source.path, options);
      }
    }
  }

  async copySourcesToTempDir(sources, targetDir) {
    for (const source of sources) {
      if (this.shouldExclude(source.path)) {
        continue;
      }

      const targetPath = path.join(targetDir, source.name || path.basename(source.path));
      
      const stats = await fs.stat(source.path);
      if (stats.size > this.options.maxFileSize) {
        logger.warn(`Skipping large file: ${source.path}`);
        continue;
      }

      if (stats.isDirectory()) {
        await fs.copy(source.path, targetPath, {
          preserveTimestamps: true,
          filter: (src) => !this.shouldExclude(src)
        });
      } else {
        await fs.copy(source.path, targetPath, {
          preserveTimestamps: true
        });
      }

      if (source.metadata && this.options.includeMetadata) {
        await fs.writeFile(
          targetPath + '.metadata.json',
          JSON.stringify(source.metadata, null, 2)
        );
      }
    }
  }

  generateMetadataFile(metadata, sources) {
    const exportMetadata = {
      exportDate: new Date().toISOString(),
      exportVersion: '1.0.0',
      sources: sources.map(source => ({
        originalPath: source.path,
        archivePath: source.name || path.basename(source.path),
        metadata: source.metadata || {}
      })),
      options: {
        compressionLevel: this.options.compressionLevel,
        preservePermissions: this.options.preservePermissions
      },
      ...metadata
    };

    return JSON.stringify(exportMetadata, null, 2);
  }

  shouldExclude(filePath) {
    for (const pattern of this.options.excludePatterns) {
      if (typeof pattern === 'string') {
        if (filePath.includes(pattern)) {
          return true;
        }
      } else if (pattern instanceof RegExp) {
        if (pattern.test(filePath)) {
          return true;
        }
      }
    }
    return false;
  }

  async generateChecksum(filePath, algorithm = 'sha256') {
    return new Promise((resolve, reject) => {
      const hash = crypto.createHash(algorithm);
      const stream = fs.createReadStream(filePath);

      stream.on('data', data => hash.update(data));
      stream.on('end', () => resolve(hash.digest('hex')));
      stream.on('error', reject);
    });
  }

  formatBytes(bytes) {
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  }

  async extractArchive(archivePath, extractDir, options = {}) {
    try {
      await fs.ensureDir(extractDir);

      const ext = path.extname(archivePath).toLowerCase();

      if (ext === '.zip') {
        return await this.extractZip(archivePath, extractDir, options);
      } else if (ext === '.gz' || ext === '.tar') {
        return await this.extractTarGz(archivePath, extractDir, options);
      } else {
        throw new Error(`Unsupported archive format: ${ext}`);
      }
    } catch (error) {
      logger.error('Archive extraction failed:', error);
      throw error;
    }
  }

  async extractZip(zipPath, extractDir, options) {
    const yauzl = require('yauzl');
    
    return new Promise((resolve, reject) => {
      yauzl.open(zipPath, { lazyEntries: true }, (err, zipfile) => {
        if (err) return reject(err);

        const extractedFiles = [];

        zipfile.readEntry();
        zipfile.on('entry', (entry) => {
          const entryPath = path.join(extractDir, entry.fileName);
          
          if (/\/$/.test(entry.fileName)) {
            fs.ensureDir(entryPath).then(() => zipfile.readEntry());
          } else {
            zipfile.openReadStream(entry, (err, readStream) => {
              if (err) return reject(err);

              fs.ensureDir(path.dirname(entryPath)).then(() => {
                const writeStream = fs.createWriteStream(entryPath);
                readStream.pipe(writeStream);
                
                writeStream.on('close', () => {
                  extractedFiles.push(entryPath);
                  zipfile.readEntry();
                });
              });
            });
          }
        });

        zipfile.on('end', () => {
          resolve({
            success: true,
            extractedFiles,
            extractDir
          });
        });
      });
    });
  }

  async extractTarGz(tarPath, extractDir, options) {
    await tar.extract({
      file: tarPath,
      cwd: extractDir,
      strict: true
    });

    const extractedFiles = await this.getExtractedFiles(extractDir);

    return {
      success: true,
      extractedFiles,
      extractDir
    };
  }

  async getExtractedFiles(dir, files = []) {
    const items = await fs.readdir(dir);
    
    for (const item of items) {
      const fullPath = path.join(dir, item);
      const stats = await fs.stat(fullPath);
      
      if (stats.isDirectory()) {
        await this.getExtractedFiles(fullPath, files);
      } else {
        files.push(fullPath);
      }
    }
    
    return files;
  }

  async createSplitArchive(sources, outputPath, maxSplitSize = 100 * 1024 * 1024) { // 100MB
    const tempDir = path.join(path.dirname(outputPath), 'temp_split_' + Date.now());
    await fs.ensureDir(tempDir);

    const splits = [];
    let currentSplit = [];
    let currentSize = 0;

    for (const source of sources) {
      const stats = await fs.stat(source.path);
      
      if (currentSize + stats.size > maxSplitSize && currentSplit.length > 0) {
        splits.push([...currentSplit]);
        currentSplit = [];
        currentSize = 0;
      }
      
      currentSplit.push(source);
      currentSize += stats.size;
    }

    if (currentSplit.length > 0) {
      splits.push(currentSplit);
    }

    const splitFiles = [];
    for (let i = 0; i < splits.length; i++) {
      const splitPath = outputPath.replace(/\.zip$/, `.part${i + 1}.zip`);
      const result = await this.createZipArchive(splits[i], splitPath);
      splitFiles.push(result);
    }

    await fs.remove(tempDir);

    return {
      success: true,
      splitFiles,
      totalParts: splits.length
    };
  }
}

module.exports = ArchiveExporter;