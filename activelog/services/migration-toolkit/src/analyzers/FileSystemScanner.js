import fs from 'fs-extra';
import path from 'path';
import logger from '../lib/logger.js';

/**
 * Advanced file system scanner for migration analysis
 */
export class FileSystemScanner {
  constructor(options = {}) {
    this.options = {
      scanDepth: 10,
      includeNodeModules: false,
      includeHidden: false,
      ignorePatterns: [
        'node_modules',
        '.git',
        '.svn',
        '.hg',
        'coverage',
        '.nyc_output',
        '.DS_Store',
        'Thumbs.db',
        '*.log',
        '.env.local',
        '.env.production'
      ],
      ...options
    };
  }

  /**
   * Scan directory and return detailed file structure
   */
  async scanDirectory(dirPath, currentDepth = 0) {
    const structure = {
      path: dirPath,
      name: path.basename(dirPath),
      type: 'directory',
      size: 0,
      files: [],
      directories: [],
      totalFiles: 0,
      totalDirectories: 0,
      fileTypes: {},
      largestFiles: [],
      configFiles: [],
      buildFiles: [],
      testFiles: [],
      documentationFiles: [],
      staticAssets: []
    };

    if (currentDepth >= this.options.scanDepth) {
      return structure;
    }

    try {
      const items = await fs.readdir(dirPath, { withFileTypes: true });

      for (const item of items) {
        const itemPath = path.join(dirPath, item.name);

        // Skip ignored patterns
        if (this.shouldIgnoreItem(item.name)) {
          continue;
        }

        if (item.isDirectory()) {
          structure.directories.push(item.name);
          structure.totalDirectories++;

          // Recursively scan subdirectories
          const subStructure = await this.scanDirectory(itemPath, currentDepth + 1);
          structure.totalFiles += subStructure.totalFiles;
          structure.totalDirectories += subStructure.totalDirectories;
          structure.size += subStructure.size;
        } else if (item.isFile()) {
          const stats = await fs.stat(itemPath);
          const fileInfo = {
            name: item.name,
            path: itemPath,
            size: stats.size,
            extension: path.extname(item.name).toLowerCase(),
            modified: stats.mtime,
            created: stats.birthtime
          };

          structure.files.push(item.name);
          structure.totalFiles++;
          structure.size += stats.size;

          // Categorize file types
          const ext = fileInfo.extension;
          structure.fileTypes[ext] = (structure.fileTypes[ext] || 0) + 1;

          // Track largest files
          structure.largestFiles.push(fileInfo);
          structure.largestFiles.sort((a, b) => b.size - a.size);
          structure.largestFiles = structure.largestFiles.slice(0, 20);

          // Categorize files by purpose
          this.categorizeFile(fileInfo, structure);
        }
      }

    } catch (error) {
      logger.warn(`Error scanning directory ${dirPath}:`, error);
    }

    return structure;
  }

  /**
   * Check if item should be ignored
   */
  shouldIgnoreItem(itemName) {
    if (!this.options.includeHidden && itemName.startsWith('.')) {
      return true;
    }

    if (!this.options.includeNodeModules && itemName === 'node_modules') {
      return true;
    }

    return this.options.ignorePatterns.some(pattern => {
      if (pattern.includes('*')) {
        const regex = new RegExp(pattern.replace(/\*/g, '.*'));
        return regex.test(itemName);
      }
      return itemName === pattern;
    });
  }

  /**
   * Categorize files by their purpose
   */
  categorizeFile(fileInfo, structure) {
    const fileName = fileInfo.name.toLowerCase();
    const ext = fileInfo.extension;

    // Configuration files
    if (this.isConfigFile(fileName)) {
      structure.configFiles.push(fileInfo.name);
    }

    // Build files
    if (this.isBuildFile(fileName, ext)) {
      structure.buildFiles.push(fileInfo.name);
    }

    // Test files
    if (this.isTestFile(fileName, ext)) {
      structure.testFiles.push(fileInfo.name);
    }

    // Documentation files
    if (this.isDocumentationFile(fileName, ext)) {
      structure.documentationFiles.push(fileInfo.name);
    }

    // Static assets
    if (this.isStaticAsset(ext)) {
      structure.staticAssets.push(fileInfo.name);
    }
  }

  /**
   * Check if file is a configuration file
   */
  isConfigFile(fileName) {
    const configPatterns = [
      'package.json',
      'package-lock.json',
      'yarn.lock',
      'pnpm-lock.yaml',
      'composer.json',
      'composer.lock',
      'requirements.txt',
      'pipfile',
      'gemfile',
      'gemfile.lock',
      'pom.xml',
      'build.gradle',
      'cargo.toml',
      'dockerfile',
      'docker-compose.yml',
      'docker-compose.yaml',
      '.gitignore',
      '.gitattributes',
      '.eslintrc',
      '.prettierrc',
      'tsconfig.json',
      'jsconfig.json',
      'webpack.config.js',
      'vite.config.js',
      'rollup.config.js',
      'babel.config.js',
      '.babelrc',
      'jest.config.js',
      'cypress.json',
      'tailwind.config.js',
      'postcss.config.js',
      '.env',
      '.env.example',
      '.env.local',
      '.env.production',
      '.env.development',
      'next.config.js',
      'nuxt.config.js',
      'vue.config.js',
      'angular.json',
      '.angular-cli.json'
    ];

    return configPatterns.some(pattern => fileName.includes(pattern));
  }

  /**
   * Check if file is a build file
   */
  isBuildFile(fileName, ext) {
    const buildExts = ['.map', '.min.js', '.min.css'];
    const buildPatterns = ['build', 'dist', 'bundle', 'compiled', '.cache'];

    return buildExts.includes(ext) || 
           buildPatterns.some(pattern => fileName.includes(pattern));
  }

  /**
   * Check if file is a test file
   */
  isTestFile(fileName, ext) {
    const testPatterns = [
      '.test.',
      '.spec.',
      '_test.',
      '_spec.',
      '.e2e.',
      'test/',
      'tests/',
      'spec/',
      'specs/',
      '__tests__/',
      'cypress/'
    ];

    return testPatterns.some(pattern => fileName.includes(pattern)) ||
           (ext === '.js' || ext === '.ts' || ext === '.jsx' || ext === '.tsx') && 
           (fileName.includes('test') || fileName.includes('spec'));
  }

  /**
   * Check if file is a documentation file
   */
  isDocumentationFile(fileName, ext) {
    const docExts = ['.md', '.txt', '.rst', '.adoc', '.pdf'];
    const docPatterns = ['readme', 'changelog', 'license', 'contributing', 'docs/', 'doc/'];

    return docExts.includes(ext) || 
           docPatterns.some(pattern => fileName.includes(pattern));
  }

  /**
   * Check if file is a static asset
   */
  isStaticAsset(ext) {
    const assetExts = [
      // Images
      '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.bmp',
      // Audio
      '.mp3', '.wav', '.ogg', '.m4a', '.aac',
      // Video
      '.mp4', '.webm', '.ogv', '.avi', '.mov',
      // Fonts
      '.woff', '.woff2', '.ttf', '.otf', '.eot',
      // Other assets
      '.pdf', '.zip', '.tar', '.gz', '.rar'
    ];

    return assetExts.includes(ext);
  }

  /**
   * Get file structure statistics
   */
  getStatistics(structure) {
    const stats = {
      totalFiles: structure.totalFiles,
      totalDirectories: structure.totalDirectories,
      totalSize: structure.size,
      fileTypeDistribution: structure.fileTypes,
      largestFiles: structure.largestFiles.slice(0, 10),
      configFilesCount: structure.configFiles.length,
      testFilesCount: structure.testFiles.length,
      buildFilesCount: structure.buildFiles.length,
      documentationFilesCount: structure.documentationFiles.length,
      staticAssetsCount: structure.staticAssets.length
    };

    return stats;
  }

  /**
   * Find files by pattern
   */
  async findFiles(dirPath, pattern, options = {}) {
    const results = [];
    const defaultOptions = {
      recursive: true,
      caseSensitive: false,
      includeStats: false,
      ...options
    };

    await this._findFilesRecursive(dirPath, pattern, results, defaultOptions);
    return results;
  }

  /**
   * Recursive file finder helper
   */
  async _findFilesRecursive(dirPath, pattern, results, options, currentDepth = 0) {
    if (currentDepth >= this.options.scanDepth) {
      return;
    }

    try {
      const items = await fs.readdir(dirPath, { withFileTypes: true });

      for (const item of items) {
        if (this.shouldIgnoreItem(item.name)) {
          continue;
        }

        const itemPath = path.join(dirPath, item.name);

        if (item.isDirectory() && options.recursive) {
          await this._findFilesRecursive(itemPath, pattern, results, options, currentDepth + 1);
        } else if (item.isFile()) {
          const fileName = options.caseSensitive ? item.name : item.name.toLowerCase();
          const searchPattern = options.caseSensitive ? pattern : pattern.toLowerCase();

          let matches = false;
          if (pattern instanceof RegExp) {
            matches = pattern.test(item.name);
          } else if (searchPattern.includes('*')) {
            const regexPattern = searchPattern.replace(/\*/g, '.*');
            matches = new RegExp(regexPattern).test(fileName);
          } else {
            matches = fileName.includes(searchPattern);
          }

          if (matches) {
            if (options.includeStats) {
              const stats = await fs.stat(itemPath);
              results.push({
                path: itemPath,
                name: item.name,
                size: stats.size,
                modified: stats.mtime,
                created: stats.birthtime
              });
            } else {
              results.push(itemPath);
            }
          }
        }
      }
    } catch (error) {
      logger.warn(`Error searching in directory ${dirPath}:`, error);
    }
  }
}