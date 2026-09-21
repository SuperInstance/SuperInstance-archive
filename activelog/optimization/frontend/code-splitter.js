const fs = require('fs');
const path = require('path');
const babel = require('@babel/core');
const parser = require('@babel/parser');
const traverse = require('@babel/traverse').default;
const generator = require('@babel/generator').default;
const crypto = require('crypto');

class CodeSplitter {
  constructor(config = {}) {
    this.config = {
      outputDir: config.outputDir || './dist',
      chunkSize: config.chunkSize || 244 * 1024, // 244KB default chunk size
      enableAsyncChunks: config.enableAsyncChunks ?? true,
      enableVendorChunks: config.enableVendorChunks ?? true,
      enableRouteChunks: config.enableRouteChunks ?? true,
      enableComponentChunks: config.enableComponentChunks ?? true,
      chunkPrefix: config.chunkPrefix || 'chunk',
      vendorChunkName: config.vendorChunkName || 'vendor',
      commonChunkName: config.commonChunkName || 'common',
      entryPoint: config.entryPoint || './src/index.js',
      minChunkSize: config.minChunkSize || 20 * 1024, // 20KB minimum
      maxChunks: config.maxChunks || 10,
      ...config
    };

    this.dependencies = new Map();
    this.chunks = new Map();
    this.moduleGraph = new Map();
    this.stats = {
      originalSize: 0,
      optimizedSize: 0,
      chunksCreated: 0,
      bundlingSaved: 0
    };
  }

  // Main entry point for code splitting
  async split(entryFiles) {
    console.log('Starting code splitting optimization...');
    
    const files = Array.isArray(entryFiles) ? entryFiles : [entryFiles || this.config.entryPoint];
    
    // Analyze dependencies and build module graph
    for (const file of files) {
      await this.analyzeDependencies(file);
    }

    // Create chunks based on analysis
    await this.createChunks();

    // Generate optimized bundles
    await this.generateBundles();

    // Generate manifest and loader
    await this.generateManifest();
    await this.generateChunkLoader();

    console.log('Code splitting optimization completed');
    return this.getOptimizationReport();
  }

  // Analyze file dependencies and build module graph
  async analyzeDependencies(filePath, visited = new Set()) {
    const resolvedPath = path.resolve(filePath);
    
    if (visited.has(resolvedPath) || !fs.existsSync(resolvedPath)) {
      return;
    }

    visited.add(resolvedPath);

    try {
      const code = fs.readFileSync(resolvedPath, 'utf8');
      this.stats.originalSize += code.length;

      const ast = parser.parse(code, {
        sourceType: 'module',
        plugins: ['jsx', 'typescript', 'decorators-legacy', 'classProperties']
      });

      const dependencies = [];
      const dynamicImports = [];
      let isRouteComponent = false;
      let isVendorModule = false;

      traverse(ast, {
        // Static imports
        ImportDeclaration(nodePath) {
          const source = nodePath.node.source.value;
          dependencies.push({
            type: 'static',
            source,
            specifiers: nodePath.node.specifiers.map(spec => ({
              type: spec.type,
              local: spec.local?.name,
              imported: spec.imported?.name,
              exported: spec.exported?.name
            }))
          });
        },

        // Dynamic imports
        CallExpression(nodePath) {
          if (nodePath.node.callee.type === 'Import') {
            const source = nodePath.node.arguments[0]?.value;
            if (source) {
              dynamicImports.push({
                type: 'dynamic',
                source,
                line: nodePath.node.loc?.start?.line
              });
            }
          }
        },

        // React Router route detection
        JSXElement(nodePath) {
          const elementName = nodePath.node.openingElement.name.name;
          if (elementName === 'Route' || elementName === 'AsyncRoute') {
            isRouteComponent = true;
          }
        },

        // Component detection
        ExportDefaultDeclaration(nodePath) {
          if (nodePath.node.declaration.type === 'FunctionDeclaration' ||
              nodePath.node.declaration.type === 'ArrowFunctionExpression') {
            // Mark as potential component chunk
          }
        }
      });

      // Check if this is a vendor module (node_modules)
      isVendorModule = resolvedPath.includes('node_modules');

      this.moduleGraph.set(resolvedPath, {
        path: resolvedPath,
        size: code.length,
        dependencies,
        dynamicImports,
        isRouteComponent,
        isVendorModule,
        hash: this.generateFileHash(code)
      });

      // Recursively analyze dependencies
      for (const dep of dependencies) {
        const depPath = this.resolveDependency(dep.source, path.dirname(resolvedPath));
        if (depPath) {
          await this.analyzeDependencies(depPath, visited);
        }
      }

    } catch (error) {
      console.warn(`Failed to analyze ${filePath}:`, error.message);
    }
  }

  // Resolve dependency path
  resolveDependency(source, basePath) {
    // Handle relative imports
    if (source.startsWith('./') || source.startsWith('../')) {
      const extensions = ['.js', '.jsx', '.ts', '.tsx', '.json'];
      const baseName = path.resolve(basePath, source);
      
      for (const ext of extensions) {
        const fullPath = baseName + ext;
        if (fs.existsSync(fullPath)) {
          return fullPath;
        }
      }
      
      // Check for index files
      for (const ext of extensions) {
        const indexPath = path.join(baseName, 'index' + ext);
        if (fs.existsSync(indexPath)) {
          return indexPath;
        }
      }
    }

    // Handle node_modules
    if (!source.startsWith('.')) {
      try {
        return require.resolve(source, { paths: [basePath] });
      } catch (e) {
        return null;
      }
    }

    return null;
  }

  // Create chunks based on analysis
  async createChunks() {
    const vendorModules = [];
    const routeModules = [];
    const componentModules = [];
    const commonModules = [];

    // Categorize modules
    for (const [filePath, module] of this.moduleGraph) {
      if (module.isVendorModule && this.config.enableVendorChunks) {
        vendorModules.push(module);
      } else if (module.isRouteComponent && this.config.enableRouteChunks) {
        routeModules.push(module);
      } else if (this.config.enableComponentChunks && this.isReusableComponent(module)) {
        componentModules.push(module);
      } else {
        commonModules.push(module);
      }
    }

    // Create vendor chunk
    if (vendorModules.length > 0) {
      this.chunks.set(this.config.vendorChunkName, {
        name: this.config.vendorChunkName,
        modules: vendorModules,
        type: 'vendor',
        size: vendorModules.reduce((sum, m) => sum + m.size, 0),
        priority: 1
      });
    }

    // Create route chunks
    if (this.config.enableRouteChunks) {
      routeModules.forEach((module, index) => {
        const chunkName = `route-${index}`;
        this.chunks.set(chunkName, {
          name: chunkName,
          modules: [module],
          type: 'route',
          size: module.size,
          priority: 2
        });
      });
    }

    // Create component chunks
    if (this.config.enableComponentChunks) {
      componentModules.forEach((module, index) => {
        const chunkName = `component-${index}`;
        this.chunks.set(chunkName, {
          name: chunkName,
          modules: [module],
          type: 'component',
          size: module.size,
          priority: 3
        });
      });
    }

    // Split common modules into optimally sized chunks
    this.splitCommonModules(commonModules);

    console.log(`Created ${this.chunks.size} chunks`);
    this.stats.chunksCreated = this.chunks.size;
  }

  // Split common modules into optimally sized chunks
  splitCommonModules(modules) {
    let currentChunk = [];
    let currentSize = 0;
    let chunkIndex = 0;

    for (const module of modules) {
      // Start new chunk if current exceeds size limit
      if (currentSize + module.size > this.config.chunkSize && currentChunk.length > 0) {
        this.finalizeCommonChunk(currentChunk, chunkIndex++);
        currentChunk = [];
        currentSize = 0;
      }

      currentChunk.push(module);
      currentSize += module.size;
    }

    // Finalize last chunk
    if (currentChunk.length > 0) {
      this.finalizeCommonChunk(currentChunk, chunkIndex);
    }
  }

  // Finalize a common chunk
  finalizeCommonChunk(modules, index) {
    const chunkName = `${this.config.chunkPrefix}-${index}`;
    this.chunks.set(chunkName, {
      name: chunkName,
      modules,
      type: 'common',
      size: modules.reduce((sum, m) => sum + m.size, 0),
      priority: 4
    });
  }

  // Check if module is a reusable component
  isReusableComponent(module) {
    // Simple heuristic: check if it's imported by multiple files
    let importCount = 0;
    for (const [, otherModule] of this.moduleGraph) {
      if (otherModule.dependencies.some(dep => 
        this.resolveDependency(dep.source, path.dirname(otherModule.path)) === module.path
      )) {
        importCount++;
      }
    }
    return importCount > 1;
  }

  // Generate optimized bundles
  async generateBundles() {
    this.ensureOutputDirectory();

    for (const [chunkName, chunk] of this.chunks) {
      await this.generateChunkBundle(chunk);
    }
  }

  // Generate individual chunk bundle
  async generateChunkBundle(chunk) {
    try {
      let bundleCode = '';
      const moduleExports = {};

      // Generate module wrapper for each file in chunk
      for (const module of chunk.modules) {
        const moduleCode = fs.readFileSync(module.path, 'utf8');
        const moduleId = this.generateModuleId(module.path);
        
        // Transform with Babel if needed
        const transformed = await this.transformModule(moduleCode, module.path);
        
        // Wrap module in function
        bundleCode += `
__modules["${moduleId}"] = function(exports, require, module, __filename, __dirname) {
${transformed}
};
`;
        
        moduleExports[moduleId] = module.path;
      }

      // Add chunk metadata and loader
      const chunkWrapper = `
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
  
  ${bundleCode}
  
  // Chunk metadata
  window.__chunkRegistry = window.__chunkRegistry || {};
  window.__chunkRegistry["${chunk.name}"] = {
    modules: ${JSON.stringify(moduleExports)},
    require: __require,
    loaded: true
  };
  
  // Execute entry point if this is main chunk
  ${chunk.type === 'common' && chunk.name.includes('0') ? 
    'if (window.__chunkLoader) window.__chunkLoader.onChunkLoaded("' + chunk.name + '");' : 
    ''}
})();
`;

      const outputPath = path.join(this.config.outputDir, `${chunk.name}.js`);
      fs.writeFileSync(outputPath, chunkWrapper);

      this.stats.optimizedSize += chunkWrapper.length;
      console.log(`Generated chunk: ${chunk.name} (${this.formatBytes(chunkWrapper.length)})`);

    } catch (error) {
      console.error(`Failed to generate chunk ${chunk.name}:`, error.message);
    }
  }

  // Transform module with Babel
  async transformModule(code, filePath) {
    try {
      const result = await babel.transformAsync(code, {
        filename: filePath,
        presets: [
          ['@babel/preset-env', { 
            targets: { browsers: ['> 1%', 'last 2 versions'] },
            modules: false
          }],
          '@babel/preset-react'
        ],
        plugins: [
          '@babel/plugin-proposal-class-properties',
          '@babel/plugin-proposal-object-rest-spread',
          '@babel/plugin-syntax-dynamic-import'
        ]
      });
      
      return result.code;
    } catch (error) {
      console.warn(`Babel transform failed for ${filePath}, using original code`);
      return code;
    }
  }

  // Generate chunk manifest
  async generateManifest() {
    const manifest = {
      chunks: {},
      entryPoints: {},
      dependencies: {}
    };

    // Build chunk manifest
    for (const [chunkName, chunk] of this.chunks) {
      manifest.chunks[chunkName] = {
        files: [`${chunkName}.js`],
        size: chunk.size,
        type: chunk.type,
        priority: chunk.priority,
        modules: chunk.modules.map(m => this.generateModuleId(m.path))
      };
    }

    // Build dependency graph for chunk loading
    for (const [chunkName, chunk] of this.chunks) {
      const dependencies = new Set();
      
      for (const module of chunk.modules) {
        for (const dep of module.dependencies) {
          const depPath = this.resolveDependency(dep.source, path.dirname(module.path));
          if (depPath) {
            const depChunk = this.findChunkByModule(depPath);
            if (depChunk && depChunk !== chunkName) {
              dependencies.add(depChunk);
            }
          }
        }
      }
      
      manifest.dependencies[chunkName] = Array.from(dependencies);
    }

    const manifestPath = path.join(this.config.outputDir, 'chunk-manifest.json');
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    
    console.log('Generated chunk manifest');
  }

  // Generate chunk loader
  async generateChunkLoader() {
    const loaderCode = `
class ChunkLoader {
  constructor() {
    this.loadedChunks = new Set();
    this.loadingPromises = new Map();
    this.manifest = null;
    this.baseUrl = '';
  }

  async initialize(manifestUrl) {
    try {
      const response = await fetch(manifestUrl);
      this.manifest = await response.json();
      this.baseUrl = manifestUrl.replace('/chunk-manifest.json', '/');
    } catch (error) {
      console.error('Failed to load chunk manifest:', error);
    }
  }

  async loadChunk(chunkName) {
    if (this.loadedChunks.has(chunkName)) {
      return Promise.resolve();
    }

    if (this.loadingPromises.has(chunkName)) {
      return this.loadingPromises.get(chunkName);
    }

    const promise = this._loadChunkWithDependencies(chunkName);
    this.loadingPromises.set(chunkName, promise);
    
    return promise;
  }

  async _loadChunkWithDependencies(chunkName) {
    const chunk = this.manifest.chunks[chunkName];
    if (!chunk) {
      throw new Error(\`Chunk \${chunkName} not found in manifest\`);
    }

    // Load dependencies first
    const dependencies = this.manifest.dependencies[chunkName] || [];
    await Promise.all(dependencies.map(dep => this.loadChunk(dep)));

    // Load the chunk itself
    if (!this.loadedChunks.has(chunkName)) {
      await this._loadChunkScript(chunkName);
      this.loadedChunks.add(chunkName);
    }
  }

  _loadChunkScript(chunkName) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = this.baseUrl + chunkName + '.js';
      script.async = true;
      
      script.onload = () => {
        resolve();
      };
      
      script.onerror = () => {
        reject(new Error(\`Failed to load chunk: \${chunkName}\`));
      };

      document.head.appendChild(script);
    });
  }

  onChunkLoaded(chunkName) {
    this.loadedChunks.add(chunkName);
  }

  // Preload chunks based on route or component usage
  preloadChunk(chunkName) {
    if (!this.loadedChunks.has(chunkName) && !this.loadingPromises.has(chunkName)) {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.as = 'script';
      link.href = this.baseUrl + chunkName + '.js';
      document.head.appendChild(link);
    }
  }

  // Get loading statistics
  getStats() {
    return {
      totalChunks: Object.keys(this.manifest?.chunks || {}).length,
      loadedChunks: this.loadedChunks.size,
      loadingChunks: this.loadingPromises.size
    };
  }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ChunkLoader;
}

// Global instance
window.__chunkLoader = new ChunkLoader();

// Auto-initialize if manifest is available
if (document.currentScript) {
  const script = document.currentScript;
  const manifestUrl = script.dataset.manifest || './chunk-manifest.json';
  window.__chunkLoader.initialize(manifestUrl);
}
`;

    const loaderPath = path.join(this.config.outputDir, 'chunk-loader.js');
    fs.writeFileSync(loaderPath, loaderCode);
    
    console.log('Generated chunk loader');
  }

  // Generate module ID from file path
  generateModuleId(filePath) {
    const relativePath = path.relative(process.cwd(), filePath);
    return crypto.createHash('md5').update(relativePath).digest('hex').substring(0, 8);
  }

  // Generate file hash for cache invalidation
  generateFileHash(content) {
    return crypto.createHash('md5').update(content).digest('hex');
  }

  // Find chunk containing a specific module
  findChunkByModule(modulePath) {
    for (const [chunkName, chunk] of this.chunks) {
      if (chunk.modules.some(m => m.path === modulePath)) {
        return chunkName;
      }
    }
    return null;
  }

  // Ensure output directory exists
  ensureOutputDirectory() {
    if (!fs.existsSync(this.config.outputDir)) {
      fs.mkdirSync(this.config.outputDir, { recursive: true });
    }
  }

  // Generate optimization report
  getOptimizationReport() {
    const sizeSaved = this.stats.originalSize - this.stats.optimizedSize;
    const compressionRatio = sizeSaved / this.stats.originalSize;

    return {
      originalSize: this.formatBytes(this.stats.originalSize),
      optimizedSize: this.formatBytes(this.stats.optimizedSize),
      sizeSaved: this.formatBytes(sizeSaved),
      compressionRatio: `${(compressionRatio * 100).toFixed(1)}%`,
      chunksCreated: this.stats.chunksCreated,
      chunks: Array.from(this.chunks.entries()).map(([name, chunk]) => ({
        name,
        size: this.formatBytes(chunk.size),
        type: chunk.type,
        modules: chunk.modules.length
      }))
    };
  }

  // Format bytes for human-readable output
  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}

// Webpack integration helper
function createWebpackPlugin(options = {}) {
  return {
    apply(compiler) {
      compiler.hooks.afterEmit.tapAsync('CodeSplitterPlugin', (compilation, callback) => {
        const splitter = new CodeSplitter(options);
        
        // Extract entry points from Webpack
        const entryFiles = Object.values(compilation.options.entry).flat();
        
        splitter.split(entryFiles).then(() => {
          console.log('Code splitting completed via Webpack plugin');
          callback();
        }).catch(callback);
      });
    }
  };
}

// CLI utility
function createCLI() {
  const args = process.argv.slice(2);
  const config = {};
  
  // Parse CLI arguments
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace('--', '');
    const value = args[i + 1];
    
    if (value && !value.startsWith('--')) {
      config[key] = value;
    }
  }

  const splitter = new CodeSplitter(config);
  const entryFile = config.entry || './src/index.js';
  
  splitter.split(entryFile).then(report => {
    console.log('\nCode Splitting Report:');
    console.log('======================');
    console.log(\`Original Size: \${report.originalSize}\`);
    console.log(\`Optimized Size: \${report.optimizedSize}\`);
    console.log(\`Size Saved: \${report.sizeSaved}\`);
    console.log(\`Compression: \${report.compressionRatio}\`);
    console.log(\`Chunks Created: \${report.chunksCreated}\`);
  }).catch(console.error);
}

// Run CLI if called directly
if (require.main === module) {
  createCLI();
}

module.exports = {
  CodeSplitter,
  createWebpackPlugin
};