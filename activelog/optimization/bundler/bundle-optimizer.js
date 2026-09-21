const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { EventEmitter } = require('events');

class BundleOptimizer extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.config = {
      // Bundle size limits
      maxBundleSize: config.maxBundleSize || 250 * 1024, // 250KB
      maxChunkSize: config.maxChunkSize || 50 * 1024, // 50KB
      targetBundleSize: config.targetBundleSize || 100 * 1024, // 100KB
      
      // Tree shaking
      enableTreeShaking: config.enableTreeShaking ?? true,
      unusedExportsThreshold: config.unusedExportsThreshold || 0, // Remove any unused exports
      
      // Code splitting
      enableCodeSplitting: config.enableCodeSplitting ?? true,
      splitThreshold: config.splitThreshold || 20 * 1024, // 20KB
      maxChunks: config.maxChunks || 10,
      
      // Minification
      enableMinification: config.enableMinification ?? true,
      minificationLevel: config.minificationLevel || 'aggressive', // conservative, standard, aggressive
      
      // Compression
      enableCompression: config.enableCompression ?? true,
      compressionLevel: config.compressionLevel || 6,
      
      // Analysis
      enableDuplicateDetection: config.enableDuplicateDetection ?? true,
      enableDependencyAnalysis: config.enableDependencyAnalysis ?? true,
      enableUnusedCodeDetection: config.enableUnusedCodeDetection ?? true,
      
      // Output
      outputDir: config.outputDir || './dist',
      generateReport: config.generateReport ?? true,
      generateSourceMaps: config.generateSourceMaps ?? true,
      
      ...config
    };

    this.bundleStats = new Map();
    this.dependencyGraph = new Map();
    this.duplicateModules = new Set();
    this.unusedExports = new Map();
    this.compressionStats = new Map();
    
    this.stats = {
      totalFiles: 0,
      totalSize: 0,
      optimizedSize: 0,
      compressionRatio: 0,
      duplicatesRemoved: 0,
      unusedCodeRemoved: 0,
      chunksCreated: 0
    };
  }

  // Main optimization entry point
  async optimize(entryPoints, options = {}) {
    console.log('Starting bundle optimization...');
    
    this.emit('optimizationStarted', { entryPoints });
    
    try {
      // Analyze dependencies
      await this.analyzeDependencies(entryPoints);
      
      // Detect duplicates and unused code
      await this.detectDuplicates();
      await this.detectUnusedCode();
      
      // Perform optimizations
      const bundles = await this.createOptimizedBundles(entryPoints, options);
      
      // Generate output files
      const outputFiles = await this.generateOutput(bundles);
      
      // Create optimization report
      const report = await this.generateOptimizationReport(outputFiles);
      
      this.emit('optimizationCompleted', { bundles, outputFiles, report });
      
      return {
        bundles,
        outputFiles,
        report,
        stats: this.getOptimizationStats()
      };
      
    } catch (error) {
      this.emit('optimizationError', error);
      throw error;
    }
  }

  // Analyze dependency graph
  async analyzeDependencies(entryPoints) {
    console.log('Analyzing dependencies...');
    
    for (const entryPoint of entryPoints) {
      await this.walkDependencyTree(entryPoint, new Set());
    }
    
    this.stats.totalFiles = this.dependencyGraph.size;
    this.stats.totalSize = Array.from(this.dependencyGraph.values())
      .reduce((sum, module) => sum + module.size, 0);
  }

  // Walk dependency tree recursively
  async walkDependencyTree(filePath, visited) {
    const resolvedPath = path.resolve(filePath);
    
    if (visited.has(resolvedPath) || !fs.existsSync(resolvedPath)) {
      return;
    }
    
    visited.add(resolvedPath);
    
    const content = fs.readFileSync(resolvedPath, 'utf8');
    const module = await this.analyzeModule(resolvedPath, content);
    
    this.dependencyGraph.set(resolvedPath, module);
    
    // Recursively analyze dependencies
    for (const dependency of module.dependencies) {
      const depPath = this.resolveDependency(dependency, path.dirname(resolvedPath));
      if (depPath) {
        await this.walkDependencyTree(depPath, visited);
      }
    }
  }

  // Analyze individual module
  async analyzeModule(filePath, content) {
    const module = {
      path: filePath,
      originalContent: content,
      size: content.length,
      dependencies: this.extractDependencies(content),
      exports: this.extractExports(content),
      imports: this.extractImports(content),
      type: this.getModuleType(filePath),
      hash: crypto.createHash('md5').update(content).digest('hex')
    };

    // Analyze for optimization opportunities
    module.optimizationInfo = {
      hasUnusedImports: this.hasUnusedImports(content),
      hasDuplicateCode: await this.checkForDuplicateCode(content),
      isTreeShakeable: this.isTreeShakeable(module),
      compressionPotential: this.estimateCompressionPotential(content)
    };

    return module;
  }

  // Extract dependencies from module
  extractDependencies(content) {
    const dependencies = new Set();
    
    // ES6 imports
    const importMatches = content.match(/import\s+.*?\s+from\s+['"]([^'"]+)['"]/g);
    if (importMatches) {
      importMatches.forEach(match => {
        const dep = match.match(/from\s+['"]([^'"]+)['"]/)[1];
        dependencies.add(dep);
      });
    }
    
    // CommonJS requires
    const requireMatches = content.match(/require\s*\(\s*['"]([^'"]+)['"]\s*\)/g);
    if (requireMatches) {
      requireMatches.forEach(match => {
        const dep = match.match(/['"]([^'"]+)['"]/)[1];
        dependencies.add(dep);
      });
    }
    
    // Dynamic imports
    const dynamicImports = content.match(/import\s*\(\s*['"]([^'"]+)['"]\s*\)/g);
    if (dynamicImports) {
      dynamicImports.forEach(match => {
        const dep = match.match(/['"]([^'"]+)['"]/)[1];
        dependencies.add(dep);
      });
    }
    
    return Array.from(dependencies);
  }

  // Extract exports from module
  extractExports(content) {
    const exports = new Set();
    
    // Named exports
    const namedExports = content.match(/export\s+(?:const|let|var|function|class)\s+(\w+)/g);
    if (namedExports) {
      namedExports.forEach(match => {
        const name = match.match(/\s+(\w+)$/)[1];
        exports.add(name);
      });
    }
    
    // Export statements
    const exportStatements = content.match(/export\s*\{\s*([^}]+)\s*\}/g);
    if (exportStatements) {
      exportStatements.forEach(match => {
        const names = match.match(/\{\s*([^}]+)\s*\}/)[1];
        names.split(',').forEach(name => {
          exports.add(name.trim().split(/\s+as\s+/)[0]);
        });
      });
    }
    
    // Default export
    if (content.includes('export default')) {
      exports.add('default');
    }
    
    return Array.from(exports);
  }

  // Extract imports from module
  extractImports(content) {
    const imports = new Set();
    
    // Named imports
    const namedImports = content.match(/import\s*\{\s*([^}]+)\s*\}\s*from/g);
    if (namedImports) {
      namedImports.forEach(match => {
        const names = match.match(/\{\s*([^}]+)\s*\}/)[1];
        names.split(',').forEach(name => {
          imports.add(name.trim().split(/\s+as\s+/)[0]);
        });
      });
    }
    
    // Default imports
    const defaultImports = content.match(/import\s+(\w+)\s+from/g);
    if (defaultImports) {
      defaultImports.forEach(match => {
        const name = match.match(/import\s+(\w+)/)[1];
        imports.add(name);
      });
    }
    
    return Array.from(imports);
  }

  // Get module type
  getModuleType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const typeMap = {
      '.js': 'javascript',
      '.jsx': 'javascript',
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.css': 'stylesheet',
      '.scss': 'stylesheet',
      '.less': 'stylesheet',
      '.json': 'data',
      '.svg': 'asset',
      '.png': 'asset',
      '.jpg': 'asset',
      '.jpeg': 'asset',
      '.gif': 'asset',
      '.woff': 'font',
      '.woff2': 'font',
      '.ttf': 'font',
      '.eot': 'font'
    };
    
    return typeMap[ext] || 'unknown';
  }

  // Check if module has unused imports
  hasUnusedImports(content) {
    // Simplified check - in practice would use AST analysis
    const importedNames = this.extractImports(content);
    return importedNames.some(name => {
      const regex = new RegExp(`\\b${name}\\b`, 'g');
      const matches = content.match(regex);
      return !matches || matches.length <= 1; // Only the import statement
    });
  }

  // Check for duplicate code
  async checkForDuplicateCode(content) {
    const hash = crypto.createHash('md5').update(content).digest('hex');
    
    for (const [, module] of this.dependencyGraph) {
      if (module.hash === hash) {
        return true;
      }
    }
    
    return false;
  }

  // Check if module is tree-shakeable
  isTreeShakeable(module) {
    // Module is tree-shakeable if it has named exports and uses ES6 modules
    return module.exports.length > 0 && 
           !module.exports.includes('default') &&
           module.originalContent.includes('export');
  }

  // Estimate compression potential
  estimateCompressionPotential(content) {
    // Quick heuristic based on repetitive patterns
    const uniqueChars = new Set(content).size;
    const totalChars = content.length;
    const entropy = uniqueChars / totalChars;
    
    // Lower entropy = better compression potential
    return Math.max(0, (1 - entropy) * 100);
  }

  // Detect duplicate modules
  async detectDuplicates() {
    const hashMap = new Map();
    
    for (const [filePath, module] of this.dependencyGraph) {
      if (hashMap.has(module.hash)) {
        const duplicates = hashMap.get(module.hash);
        duplicates.push(filePath);
        this.duplicateModules.add(module.hash);
      } else {
        hashMap.set(module.hash, [filePath]);
      }
    }
    
    this.stats.duplicatesRemoved = this.duplicateModules.size;
  }

  // Detect unused code
  async detectUnusedCode() {
    const allExports = new Map();
    const allImports = new Map();
    
    // Collect all exports and imports
    for (const [filePath, module] of this.dependencyGraph) {
      allExports.set(filePath, new Set(module.exports));
      allImports.set(filePath, new Set(module.imports));
    }
    
    // Find unused exports
    for (const [filePath, exports] of allExports) {
      const unusedInModule = new Set();
      
      for (const exportName of exports) {
        let isUsed = false;
        
        // Check if this export is imported anywhere
        for (const [, imports] of allImports) {
          if (imports.has(exportName)) {
            isUsed = true;
            break;
          }
        }
        
        if (!isUsed && exportName !== 'default') {
          unusedInModule.add(exportName);
        }
      }
      
      if (unusedInModule.size > 0) {
        this.unusedExports.set(filePath, unusedInModule);
      }
    }
  }

  // Create optimized bundles
  async createOptimizedBundles(entryPoints, options = {}) {
    const bundles = [];
    
    for (const entryPoint of entryPoints) {
      const bundle = await this.createBundle(entryPoint, options);
      bundles.push(bundle);
    }
    
    // Optimize chunk distribution
    const optimizedBundles = await this.optimizeChunkDistribution(bundles);
    
    return optimizedBundles;
  }

  // Create individual bundle
  async createBundle(entryPoint, options = {}) {
    const bundleId = path.basename(entryPoint, path.extname(entryPoint));
    const modules = await this.collectBundleModules(entryPoint);
    
    let bundleContent = '';
    let bundleSize = 0;
    const includedModules = [];
    
    for (const modulePath of modules) {
      const module = this.dependencyGraph.get(modulePath);
      if (!module) continue;
      
      // Apply optimizations
      let optimizedContent = module.originalContent;
      
      if (this.config.enableTreeShaking) {
        optimizedContent = await this.treeShakeModule(optimizedContent, modulePath);
      }
      
      if (this.config.enableMinification) {
        optimizedContent = await this.minifyContent(optimizedContent, module.type);
      }
      
      // Wrap module
      const wrappedContent = this.wrapModule(optimizedContent, modulePath);
      bundleContent += wrappedContent + '\n';
      bundleSize += wrappedContent.length;
      
      includedModules.push({
        path: modulePath,
        originalSize: module.size,
        optimizedSize: wrappedContent.length,
        type: module.type
      });
    }
    
    // Add bundle wrapper
    bundleContent = this.wrapBundle(bundleContent, bundleId);
    
    const bundle = {
      id: bundleId,
      entryPoint,
      content: bundleContent,
      size: bundleContent.length,
      modules: includedModules,
      chunks: []
    };
    
    // Split into chunks if too large
    if (bundle.size > this.config.maxBundleSize && this.config.enableCodeSplitting) {
      bundle.chunks = await this.splitBundle(bundle);
    }
    
    return bundle;
  }

  // Collect all modules for a bundle
  async collectBundleModules(entryPoint) {
    const modules = new Set();
    const visited = new Set();
    
    const walk = (filePath) => {
      const resolvedPath = path.resolve(filePath);
      
      if (visited.has(resolvedPath)) return;
      visited.add(resolvedPath);
      
      const module = this.dependencyGraph.get(resolvedPath);
      if (!module) return;
      
      modules.add(resolvedPath);
      
      // Recursively add dependencies
      for (const dependency of module.dependencies) {
        const depPath = this.resolveDependency(dependency, path.dirname(resolvedPath));
        if (depPath) {
          walk(depPath);
        }
      }
    };
    
    walk(entryPoint);
    return Array.from(modules);
  }

  // Tree shake module
  async treeShakeModule(content, modulePath) {
    if (!this.config.enableTreeShaking) return content;
    
    const unusedExports = this.unusedExports.get(modulePath);
    if (!unusedExports || unusedExports.size === 0) return content;
    
    let optimizedContent = content;
    
    // Remove unused exports (simplified implementation)
    for (const unusedExport of unusedExports) {
      const exportRegex = new RegExp(`export\\s+(?:const|let|var|function|class)\\s+${unusedExport}\\b[^;]*;?`, 'g');
      optimizedContent = optimizedContent.replace(exportRegex, '');
      
      const namedExportRegex = new RegExp(`\\b${unusedExport}\\b,?\\s*`, 'g');
      optimizedContent = optimizedContent.replace(namedExportRegex, '');
    }
    
    return optimizedContent;
  }

  // Minify content
  async minifyContent(content, moduleType) {
    if (!this.config.enableMinification) return content;
    
    try {
      switch (moduleType) {
        case 'javascript':
        case 'typescript':
          return await this.minifyJavaScript(content);
        case 'stylesheet':
          return await this.minifyCSS(content);
        default:
          return content;
      }
    } catch (error) {
      console.warn(`Minification failed for ${moduleType}:`, error.message);
      return content;
    }
  }

  // Minify JavaScript
  async minifyJavaScript(content) {
    const { minify } = require('terser');
    
    const minifyOptions = {
      compress: {
        drop_console: this.config.minificationLevel === 'aggressive',
        drop_debugger: true,
        pure_funcs: this.config.minificationLevel === 'aggressive' ? 
          ['console.log', 'console.warn', 'console.info'] : []
      },
      mangle: this.config.minificationLevel !== 'conservative',
      format: {
        comments: this.config.minificationLevel === 'conservative'
      }
    };
    
    const result = await minify(content, minifyOptions);
    return result.code || content;
  }

  // Minify CSS
  async minifyCSS(content) {
    const CleanCSS = require('clean-css');
    
    const minifyOptions = {
      level: this.config.minificationLevel === 'aggressive' ? 2 : 1,
      returnPromise: true
    };
    
    const result = await new CleanCSS(minifyOptions).minify(content);
    return result.styles || content;
  }

  // Wrap module in function
  wrapModule(content, modulePath) {
    const moduleId = this.generateModuleId(modulePath);
    
    return `
__modules["${moduleId}"] = function(exports, require, module, __filename, __dirname) {
${content}
};`;
  }

  // Wrap bundle with loader
  wrapBundle(content, bundleId) {
    return `
(function() {
  var __modules = {};
  var __cache = {};
  
  function __require(moduleId) {
    if (__cache[moduleId]) return __cache[moduleId].exports;
    
    var module = __cache[moduleId] = { exports: {} };
    var exports = module.exports;
    
    __modules[moduleId].call(exports, exports, __require, module, '', '');
    return module.exports;
  }
  
  ${content}
  
  // Execute entry point
  if (typeof window !== 'undefined') {
    window.__bundle_${bundleId} = __require;
  }
})();`;
  }

  // Split bundle into chunks
  async splitBundle(bundle) {
    const chunks = [];
    const modules = bundle.modules.slice();
    let currentChunk = [];
    let currentSize = 0;
    
    for (const module of modules) {
      if (currentSize + module.optimizedSize > this.config.maxChunkSize && currentChunk.length > 0) {
        chunks.push(await this.createChunk(currentChunk, chunks.length));
        currentChunk = [];
        currentSize = 0;
      }
      
      currentChunk.push(module);
      currentSize += module.optimizedSize;
    }
    
    // Add final chunk
    if (currentChunk.length > 0) {
      chunks.push(await this.createChunk(currentChunk, chunks.length));
    }
    
    this.stats.chunksCreated += chunks.length;
    return chunks;
  }

  // Create individual chunk
  async createChunk(modules, chunkIndex) {
    let chunkContent = '';
    let chunkSize = 0;
    
    for (const module of modules) {
      const moduleContent = this.dependencyGraph.get(module.path).originalContent;
      const wrappedContent = this.wrapModule(moduleContent, module.path);
      chunkContent += wrappedContent + '\n';
      chunkSize += wrappedContent.length;
    }
    
    return {
      index: chunkIndex,
      content: chunkContent,
      size: chunkSize,
      modules: modules.length
    };
  }

  // Optimize chunk distribution
  async optimizeChunkDistribution(bundles) {
    // Find common modules across bundles
    const moduleUsage = new Map();
    
    for (const bundle of bundles) {
      for (const module of bundle.modules) {
        const count = moduleUsage.get(module.path) || 0;
        moduleUsage.set(module.path, count + 1);
      }
    }
    
    // Extract common modules into shared chunks
    const commonModules = Array.from(moduleUsage.entries())
      .filter(([, count]) => count > 1)
      .map(([path]) => path);
    
    if (commonModules.length > 0) {
      const sharedChunk = await this.createSharedChunk(commonModules);
      
      // Update bundles to remove common modules
      for (const bundle of bundles) {
        bundle.modules = bundle.modules.filter(m => !commonModules.includes(m.path));
        bundle.sharedChunk = sharedChunk;
      }
    }
    
    return bundles;
  }

  // Create shared chunk for common modules
  async createSharedChunk(modulePaths) {
    const modules = modulePaths.map(path => {
      const module = this.dependencyGraph.get(path);
      return {
        path,
        originalSize: module.size,
        optimizedSize: module.size, // Would apply optimizations here
        type: module.type
      };
    });
    
    return await this.createChunk(modules, 'shared');
  }

  // Generate output files
  async generateOutput(bundles) {
    this.ensureOutputDirectory();
    const outputFiles = [];
    
    for (const bundle of bundles) {
      // Generate main bundle file
      const bundleFile = await this.writeBundleFile(bundle);
      outputFiles.push(bundleFile);
      
      // Generate chunk files
      for (const chunk of bundle.chunks) {
        const chunkFile = await this.writeChunkFile(bundle.id, chunk);
        outputFiles.push(chunkFile);
      }
      
      // Generate shared chunk if exists
      if (bundle.sharedChunk) {
        const sharedFile = await this.writeChunkFile('shared', bundle.sharedChunk);
        outputFiles.push(sharedFile);
      }
    }
    
    // Generate source maps if enabled
    if (this.config.generateSourceMaps) {
      for (const bundle of bundles) {
        const sourceMapFile = await this.generateSourceMap(bundle);
        outputFiles.push(sourceMapFile);
      }
    }
    
    return outputFiles;
  }

  // Write bundle file
  async writeBundleFile(bundle) {
    let content = bundle.content;
    
    // Apply compression if enabled
    if (this.config.enableCompression) {
      content = await this.compressContent(content);
    }
    
    const filename = `${bundle.id}.bundle.js`;
    const filepath = path.join(this.config.outputDir, filename);
    
    fs.writeFileSync(filepath, content);
    
    this.stats.optimizedSize += content.length;
    
    return {
      type: 'bundle',
      filename,
      filepath,
      size: content.length,
      originalSize: bundle.size,
      compressionRatio: content.length / bundle.size
    };
  }

  // Write chunk file
  async writeChunkFile(bundleId, chunk) {
    let content = chunk.content;
    
    if (this.config.enableCompression) {
      content = await this.compressContent(content);
    }
    
    const filename = `${bundleId}.chunk.${chunk.index}.js`;
    const filepath = path.join(this.config.outputDir, filename);
    
    fs.writeFileSync(filepath, content);
    
    return {
      type: 'chunk',
      filename,
      filepath,
      size: content.length,
      originalSize: chunk.size,
      modules: chunk.modules
    };
  }

  // Compress content
  async compressContent(content) {
    const zlib = require('zlib');
    const compressed = zlib.gzipSync(content, { level: this.config.compressionLevel });
    return compressed;
  }

  // Generate source map
  async generateSourceMap(bundle) {
    // Simplified source map generation
    const sourceMap = {
      version: 3,
      sources: bundle.modules.map(m => m.path),
      names: [],
      mappings: '',
      sourcesContent: bundle.modules.map(m => 
        this.dependencyGraph.get(m.path).originalContent
      )
    };
    
    const filename = `${bundle.id}.bundle.js.map`;
    const filepath = path.join(this.config.outputDir, filename);
    
    fs.writeFileSync(filepath, JSON.stringify(sourceMap, null, 2));
    
    return {
      type: 'sourcemap',
      filename,
      filepath,
      size: JSON.stringify(sourceMap).length
    };
  }

  // Generate optimization report
  async generateOptimizationReport(outputFiles) {
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalInputSize: this.formatBytes(this.stats.totalSize),
        totalOutputSize: this.formatBytes(this.stats.optimizedSize),
        sizeSaved: this.formatBytes(this.stats.totalSize - this.stats.optimizedSize),
        compressionRatio: `${((1 - this.stats.optimizedSize / this.stats.totalSize) * 100).toFixed(2)}%`,
        filesProcessed: this.stats.totalFiles,
        duplicatesRemoved: this.stats.duplicatesRemoved,
        chunksCreated: this.stats.chunksCreated
      },
      optimizations: {
        treeShaking: {
          enabled: this.config.enableTreeShaking,
          unusedExportsRemoved: this.unusedExports.size
        },
        minification: {
          enabled: this.config.enableMinification,
          level: this.config.minificationLevel
        },
        compression: {
          enabled: this.config.enableCompression,
          level: this.config.compressionLevel
        },
        codeSplitting: {
          enabled: this.config.enableCodeSplitting,
          chunksCreated: this.stats.chunksCreated
        }
      },
      outputFiles: outputFiles.map(file => ({
        filename: file.filename,
        type: file.type,
        size: this.formatBytes(file.size),
        compressionRatio: file.compressionRatio ? 
          `${((1 - file.compressionRatio) * 100).toFixed(2)}%` : 'N/A'
      })),
      recommendations: this.generateRecommendations()
    };
    
    if (this.config.generateReport) {
      const reportPath = path.join(this.config.outputDir, 'optimization-report.json');
      fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    }
    
    return report;
  }

  // Generate optimization recommendations
  generateRecommendations() {
    const recommendations = [];
    
    // Check bundle sizes
    const avgBundleSize = this.stats.optimizedSize / (this.stats.chunksCreated || 1);
    if (avgBundleSize > this.config.targetBundleSize) {
      recommendations.push({
        type: 'bundle_size',
        message: 'Consider more aggressive code splitting to reduce bundle sizes',
        current: this.formatBytes(avgBundleSize),
        target: this.formatBytes(this.config.targetBundleSize)
      });
    }
    
    // Check compression ratio
    const compressionRatio = 1 - (this.stats.optimizedSize / this.stats.totalSize);
    if (compressionRatio < 0.3) {
      recommendations.push({
        type: 'compression',
        message: 'Low compression ratio detected. Consider enabling more aggressive minification',
        current: `${(compressionRatio * 100).toFixed(2)}%`,
        suggestion: 'Enable aggressive minification and tree shaking'
      });
    }
    
    // Check for unused exports
    if (this.unusedExports.size > 0) {
      recommendations.push({
        type: 'unused_code',
        message: 'Unused exports detected that could be removed',
        count: this.unusedExports.size,
        suggestion: 'Enable tree shaking or manually remove unused exports'
      });
    }
    
    // Check for duplicates
    if (this.duplicateModules.size > 0) {
      recommendations.push({
        type: 'duplicates',
        message: 'Duplicate modules detected',
        count: this.duplicateModules.size,
        suggestion: 'Consider creating shared chunks for common dependencies'
      });
    }
    
    return recommendations;
  }

  // Utility methods
  resolveDependency(dependency, basePath) {
    if (dependency.startsWith('./') || dependency.startsWith('../')) {
      const extensions = ['.js', '.jsx', '.ts', '.tsx', '.json'];
      const baseName = path.resolve(basePath, dependency);
      
      for (const ext of extensions) {
        const fullPath = baseName + ext;
        if (fs.existsSync(fullPath)) {
          return fullPath;
        }
      }
    }
    
    return null; // Node modules handling would go here
  }

  generateModuleId(modulePath) {
    const relativePath = path.relative(process.cwd(), modulePath);
    return crypto.createHash('md5').update(relativePath).digest('hex').substring(0, 8);
  }

  ensureOutputDirectory() {
    if (!fs.existsSync(this.config.outputDir)) {
      fs.mkdirSync(this.config.outputDir, { recursive: true });
    }
  }

  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  getOptimizationStats() {
    return {
      ...this.stats,
      compressionRatio: `${((1 - this.stats.optimizedSize / this.stats.totalSize) * 100).toFixed(2)}%`,
      sizeSaved: this.formatBytes(this.stats.totalSize - this.stats.optimizedSize)
    };
  }

  // Health check
  async healthCheck() {
    return {
      healthy: true,
      stats: this.getOptimizationStats(),
      config: {
        treeShaking: this.config.enableTreeShaking,
        minification: this.config.enableMinification,
        compression: this.config.enableCompression,
        codeSplitting: this.config.enableCodeSplitting
      }
    };
  }
}

// Webpack plugin integration
function createWebpackOptimizerPlugin(options = {}) {
  return {
    apply(compiler) {
      compiler.hooks.afterEmit.tapAsync('BundleOptimizerPlugin', (compilation, callback) => {
        const optimizer = new BundleOptimizer(options);
        
        const entryFiles = Object.values(compilation.options.entry).flat();
        
        optimizer.optimize(entryFiles).then(() => {
          console.log('Bundle optimization completed via Webpack plugin');
          callback();
        }).catch(callback);
      });
    }
  };
}

module.exports = {
  BundleOptimizer,
  createWebpackOptimizerPlugin
};