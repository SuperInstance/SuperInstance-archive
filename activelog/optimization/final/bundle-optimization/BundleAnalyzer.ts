/**
 * Advanced Bundle Size Analysis and Optimization System
 * Comprehensive bundle analysis with automated optimization recommendations
 */

interface BundleAnalysis {
  totalSize: number;
  gzippedSize: number;
  modules: ModuleAnalysis[];
  chunks: ChunkAnalysis[];
  duplicates: DuplicateModule[];
  treeshaking: TreeshakingAnalysis;
  recommendations: OptimizationRecommendation[];
}

interface ModuleAnalysis {
  name: string;
  size: number;
  gzippedSize: number;
  path: string;
  imports: string[];
  exports: string[];
  usedExports: string[];
  unusedExports: string[];
  isNodeModule: boolean;
  treeshakeable: boolean;
  sideEffects: boolean;
}

interface ChunkAnalysis {
  name: string;
  size: number;
  gzippedSize: number;
  modules: string[];
  isEntry: boolean;
  isAsync: boolean;
  parents: string[];
  children: string[];
  loadPriority: 'high' | 'medium' | 'low';
}

interface DuplicateModule {
  name: string;
  paths: string[];
  totalSize: number;
  potentialSavings: number;
  versions: string[];
}

interface TreeshakingAnalysis {
  totalDeadCode: number;
  moduleDeadCode: Record<string, number>;
  shakingEfficiency: number;
  improvementPotential: number;
}

interface OptimizationRecommendation {
  type: 'split-vendor' | 'lazy-load' | 'tree-shake' | 'dedupe' | 'replace-library' | 'bundle-splitting';
  priority: 'high' | 'medium' | 'low';
  description: string;
  potentialSavings: number;
  effort: 'low' | 'medium' | 'high';
  action: string;
  affectedModules: string[];
}

interface BundleBudget {
  maxSize: number;
  warningThreshold: number;
  errorThreshold: number;
  budgetType: 'initial' | 'all' | 'any';
}

class BundleAnalyzer {
  private budgets: Map<string, BundleBudget> = new Map();
  private analysisHistory: BundleAnalysis[] = [];
  private optimizationTargets: Map<string, number> = new Map();

  constructor() {
    this.initializeDefaultBudgets();
  }

  /**
   * Initialize default bundle budgets
   */
  private initializeDefaultBudgets(): void {
    this.budgets.set('main', {
      maxSize: 250 * 1024, // 250KB
      warningThreshold: 200 * 1024, // 200KB
      errorThreshold: 300 * 1024, // 300KB
      budgetType: 'initial'
    });

    this.budgets.set('vendor', {
      maxSize: 500 * 1024, // 500KB
      warningThreshold: 400 * 1024, // 400KB
      errorThreshold: 600 * 1024, // 600KB
      budgetType: 'initial'
    });

    this.budgets.set('async-chunks', {
      maxSize: 100 * 1024, // 100KB per chunk
      warningThreshold: 80 * 1024, // 80KB
      errorThreshold: 150 * 1024, // 150KB
      budgetType: 'any'
    });
  }

  /**
   * Analyze webpack bundle statistics
   */
  analyzeBundleStats(stats: any): BundleAnalysis {
    const modules = this.analyzeModules(stats.modules || []);
    const chunks = this.analyzeChunks(stats.chunks || [], modules);
    const duplicates = this.findDuplicateModules(modules);
    const treeshaking = this.analyzeTreeshaking(modules);
    
    const totalSize = chunks.reduce((sum, chunk) => sum + chunk.size, 0);
    const gzippedSize = chunks.reduce((sum, chunk) => sum + chunk.gzippedSize, 0);

    const analysis: BundleAnalysis = {
      totalSize,
      gzippedSize,
      modules,
      chunks,
      duplicates,
      treeshaking,
      recommendations: this.generateRecommendations(modules, chunks, duplicates, treeshaking)
    };

    this.analysisHistory.push(analysis);
    this.checkBudgets(analysis);

    return analysis;
  }

  /**
   * Analyze individual modules
   */
  private analyzeModules(statsModules: any[]): ModuleAnalysis[] {
    return statsModules.map(module => {
      const isNodeModule = module.name?.includes('node_modules') || false;
      const usedExports = module.usedExports || [];
      const providedExports = module.providedExports || [];
      const unusedExports = providedExports.filter((exp: string) => !usedExports.includes(exp));

      return {
        name: module.name || 'unknown',
        size: module.size || 0,
        gzippedSize: this.estimateGzippedSize(module.size || 0),
        path: module.name || '',
        imports: module.reasons?.map((r: any) => r.moduleName) || [],
        exports: providedExports,
        usedExports,
        unusedExports,
        isNodeModule,
        treeshakeable: !module.sideEffects && unusedExports.length > 0,
        sideEffects: module.sideEffects || false
      };
    });
  }

  /**
   * Analyze bundle chunks
   */
  private analyzeChunks(statsChunks: any[], modules: ModuleAnalysis[]): ChunkAnalysis[] {
    return statsChunks.map(chunk => {
      const chunkModules = chunk.modules?.map((m: any) => m.name) || [];
      const size = chunk.modules?.reduce((sum: number, m: any) => sum + (m.size || 0), 0) || 0;
      
      return {
        name: chunk.names?.[0] || `chunk-${chunk.id}`,
        size,
        gzippedSize: this.estimateGzippedSize(size),
        modules: chunkModules,
        isEntry: chunk.entry || false,
        isAsync: !chunk.entry && !chunk.initial,
        parents: chunk.parents || [],
        children: chunk.children || [],
        loadPriority: this.determineLoadPriority(chunk, chunkModules, modules)
      };
    });
  }

  /**
   * Determine chunk load priority
   */
  private determineLoadPriority(
    chunk: any, 
    chunkModules: string[], 
    modules: ModuleAnalysis[]
  ): 'high' | 'medium' | 'low' {
    if (chunk.entry || chunk.initial) return 'high';
    
    const hasFrameworkCode = chunkModules.some(mod => 
      mod.includes('react') || mod.includes('vue') || mod.includes('angular')
    );
    if (hasFrameworkCode) return 'high';

    const hasUIComponents = chunkModules.some(mod => 
      mod.includes('component') || mod.includes('ui') || mod.includes('layout')
    );
    if (hasUIComponents) return 'medium';

    return 'low';
  }

  /**
   * Find duplicate modules across chunks
   */
  private findDuplicateModules(modules: ModuleAnalysis[]): DuplicateModule[] {
    const moduleMap = new Map<string, ModuleAnalysis[]>();

    // Group modules by base name
    modules.forEach(module => {
      const baseName = this.getModuleBaseName(module.name);
      if (!moduleMap.has(baseName)) {
        moduleMap.set(baseName, []);
      }
      moduleMap.get(baseName)!.push(module);
    });

    const duplicates: DuplicateModule[] = [];

    moduleMap.forEach((moduleList, baseName) => {
      if (moduleList.length > 1) {
        const totalSize = moduleList.reduce((sum, mod) => sum + mod.size, 0);
        const versions = this.extractVersions(moduleList);
        
        duplicates.push({
          name: baseName,
          paths: moduleList.map(m => m.path),
          totalSize,
          potentialSavings: totalSize - moduleList[0].size, // Save all but one
          versions
        });
      }
    });

    return duplicates.sort((a, b) => b.potentialSavings - a.potentialSavings);
  }

  /**
   * Analyze tree shaking effectiveness
   */
  private analyzeTreeshaking(modules: ModuleAnalysis[]): TreeshakingAnalysis {
    const totalDeadCode = modules.reduce((sum, mod) => {
      const deadCodeRatio = mod.unusedExports.length / Math.max(mod.exports.length, 1);
      return sum + (mod.size * deadCodeRatio);
    }, 0);

    const moduleDeadCode: Record<string, number> = {};
    modules.forEach(mod => {
      if (mod.unusedExports.length > 0) {
        const deadCodeRatio = mod.unusedExports.length / mod.exports.length;
        moduleDeadCode[mod.name] = mod.size * deadCodeRatio;
      }
    });

    const totalSize = modules.reduce((sum, mod) => sum + mod.size, 0);
    const shakingEfficiency = 1 - (totalDeadCode / totalSize);
    const improvementPotential = totalDeadCode / totalSize;

    return {
      totalDeadCode,
      moduleDeadCode,
      shakingEfficiency,
      improvementPotential
    };
  }

  /**
   * Generate optimization recommendations
   */
  private generateRecommendations(
    modules: ModuleAnalysis[],
    chunks: ChunkAnalysis[],
    duplicates: DuplicateModule[],
    treeshaking: TreeshakingAnalysis
  ): OptimizationRecommendation[] {
    const recommendations: OptimizationRecommendation[] = [];

    // Vendor chunk splitting
    const largeNodeModules = modules
      .filter(m => m.isNodeModule && m.size > 50000) // > 50KB
      .sort((a, b) => b.size - a.size);

    if (largeNodeModules.length > 0) {
      recommendations.push({
        type: 'split-vendor',
        priority: 'high',
        description: 'Split large vendor libraries into separate chunks',
        potentialSavings: largeNodeModules.reduce((sum, mod) => sum + mod.size * 0.3, 0),
        effort: 'low',
        action: 'Configure webpack splitChunks for vendor libraries',
        affectedModules: largeNodeModules.slice(0, 5).map(m => m.name)
      });
    }

    // Lazy loading opportunities
    const asyncCandidates = chunks
      .filter(c => !c.isEntry && c.loadPriority === 'low' && c.size > 20000)
      .sort((a, b) => b.size - a.size);

    if (asyncCandidates.length > 0) {
      recommendations.push({
        type: 'lazy-load',
        priority: 'medium',
        description: 'Implement lazy loading for non-critical components',
        potentialSavings: asyncCandidates.reduce((sum, chunk) => sum + chunk.size * 0.8, 0),
        effort: 'medium',
        action: 'Add dynamic imports for route-based code splitting',
        affectedModules: asyncCandidates.slice(0, 3).map(c => c.name)
      });
    }

    // Tree shaking improvements
    if (treeshaking.improvementPotential > 0.1) { // > 10% dead code
      const worstOffenders = Object.entries(treeshaking.moduleDeadCode)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 5)
        .map(([name]) => name);

      recommendations.push({
        type: 'tree-shake',
        priority: 'high',
        description: `Remove unused code (${Math.round(treeshaking.improvementPotential * 100)}% dead code detected)`,
        potentialSavings: treeshaking.totalDeadCode,
        effort: 'medium',
        action: 'Review imports and mark packages as side-effect free',
        affectedModules: worstOffenders
      });
    }

    // Duplicate module deduplication
    const significantDuplicates = duplicates.filter(d => d.potentialSavings > 10000); // > 10KB savings

    if (significantDuplicates.length > 0) {
      recommendations.push({
        type: 'dedupe',
        priority: 'medium',
        description: 'Remove duplicate dependencies across bundles',
        potentialSavings: significantDuplicates.reduce((sum, dup) => sum + dup.potentialSavings, 0),
        effort: 'low',
        action: 'Configure webpack resolve.alias or use webpack-bundle-analyzer',
        affectedModules: significantDuplicates.slice(0, 5).map(d => d.name)
      });
    }

    // Library replacement suggestions
    const heavyLibraries = modules
      .filter(m => m.isNodeModule && m.size > 100000) // > 100KB
      .map(m => ({ name: this.getModuleBaseName(m.name), size: m.size }))
      .sort((a, b) => b.size - a.size);

    heavyLibraries.forEach(lib => {
      const alternative = this.suggestLighterAlternative(lib.name);
      if (alternative) {
        recommendations.push({
          type: 'replace-library',
          priority: 'low',
          description: `Replace ${lib.name} with lighter alternative: ${alternative.name}`,
          potentialSavings: lib.size - alternative.size,
          effort: 'high',
          action: `Replace ${lib.name} with ${alternative.name}`,
          affectedModules: [lib.name]
        });
      }
    });

    return recommendations.sort((a, b) => {
      const priorityOrder = { 'high': 3, 'medium': 2, 'low': 1 };
      return (priorityOrder[b.priority] - priorityOrder[a.priority]) ||
             (b.potentialSavings - a.potentialSavings);
    });
  }

  /**
   * Suggest lighter alternatives for heavy libraries
   */
  private suggestLighterAlternative(libraryName: string): { name: string; size: number } | null {
    const alternatives: Record<string, { name: string; size: number }> = {
      'lodash': { name: 'lodash-es (with tree shaking)', size: 20000 },
      'moment': { name: 'date-fns or dayjs', size: 15000 },
      'jquery': { name: 'vanilla JS or zepto', size: 5000 },
      'underscore': { name: 'lodash-es', size: 25000 },
      'axios': { name: 'fetch API or ky', size: 8000 },
      'babel-polyfill': { name: '@babel/preset-env with useBuiltIns', size: 30000 }
    };

    return alternatives[libraryName] || null;
  }

  /**
   * Check if bundles exceed configured budgets
   */
  private checkBudgets(analysis: BundleAnalysis): void {
    this.budgets.forEach((budget, name) => {
      let currentSize = 0;

      switch (budget.budgetType) {
        case 'initial':
          currentSize = analysis.chunks
            .filter(c => c.isEntry)
            .reduce((sum, c) => sum + c.size, 0);
          break;
        case 'all':
          currentSize = analysis.totalSize;
          break;
        case 'any':
          currentSize = Math.max(...analysis.chunks.map(c => c.size));
          break;
      }

      if (currentSize > budget.errorThreshold) {
        console.error(`❌ Bundle budget exceeded for ${name}: ${this.formatSize(currentSize)} > ${this.formatSize(budget.errorThreshold)}`);
      } else if (currentSize > budget.warningThreshold) {
        console.warn(`⚠️ Bundle budget warning for ${name}: ${this.formatSize(currentSize)} > ${this.formatSize(budget.warningThreshold)}`);
      } else {
        console.log(`✅ Bundle budget OK for ${name}: ${this.formatSize(currentSize)}`);
      }
    });
  }

  /**
   * Generate comprehensive bundle report
   */
  generateReport(analysis: BundleAnalysis): string {
    let report = '# Bundle Analysis Report\n\n';

    // Overview
    report += '## Overview\n';
    report += `**Total Bundle Size:** ${this.formatSize(analysis.totalSize)}\n`;
    report += `**Gzipped Size:** ${this.formatSize(analysis.gzippedSize)}\n`;
    report += `**Compression Ratio:** ${((1 - analysis.gzippedSize / analysis.totalSize) * 100).toFixed(1)}%\n`;
    report += `**Number of Modules:** ${analysis.modules.length}\n`;
    report += `**Number of Chunks:** ${analysis.chunks.length}\n\n`;

    // Chunks breakdown
    report += '## Chunk Analysis\n';
    report += '| Chunk | Size | Gzipped | Type | Priority |\n';
    report += '|-------|------|---------|------|---------|\n';
    analysis.chunks
      .sort((a, b) => b.size - a.size)
      .forEach(chunk => {
        const type = chunk.isEntry ? 'Entry' : chunk.isAsync ? 'Async' : 'Initial';
        report += `| ${chunk.name} | ${this.formatSize(chunk.size)} | ${this.formatSize(chunk.gzippedSize)} | ${type} | ${chunk.loadPriority} |\n`;
      });
    report += '\n';

    // Top modules
    report += '## Largest Modules\n';
    report += '| Module | Size | Gzipped | Tree-shakeable |\n';
    report += '|--------|------|---------|---------------|\n';
    analysis.modules
      .sort((a, b) => b.size - a.size)
      .slice(0, 10)
      .forEach(module => {
        const name = this.truncateModuleName(module.name);
        report += `| ${name} | ${this.formatSize(module.size)} | ${this.formatSize(module.gzippedSize)} | ${module.treeshakeable ? '✅' : '❌'} |\n`;
      });
    report += '\n';

    // Duplicates
    if (analysis.duplicates.length > 0) {
      report += '## Duplicate Modules\n';
      report += '| Module | Instances | Total Size | Potential Savings |\n';
      report += '|--------|-----------|------------|------------------|\n';
      analysis.duplicates
        .slice(0, 10)
        .forEach(dup => {
          report += `| ${dup.name} | ${dup.paths.length} | ${this.formatSize(dup.totalSize)} | ${this.formatSize(dup.potentialSavings)} |\n`;
        });
      report += '\n';
    }

    // Tree shaking analysis
    report += '## Tree Shaking Analysis\n';
    report += `**Shaking Efficiency:** ${(analysis.treeshaking.shakingEfficiency * 100).toFixed(1)}%\n`;
    report += `**Dead Code:** ${this.formatSize(analysis.treeshaking.totalDeadCode)}\n`;
    report += `**Improvement Potential:** ${(analysis.treeshaking.improvementPotential * 100).toFixed(1)}%\n\n`;

    // Recommendations
    report += '## Optimization Recommendations\n';
    analysis.recommendations.forEach((rec, i) => {
      report += `### ${i + 1}. ${rec.description}\n`;
      report += `**Priority:** ${rec.priority.toUpperCase()}\n`;
      report += `**Potential Savings:** ${this.formatSize(rec.potentialSavings)}\n`;
      report += `**Effort:** ${rec.effort}\n`;
      report += `**Action:** ${rec.action}\n`;
      if (rec.affectedModules.length > 0) {
        report += `**Affected Modules:** ${rec.affectedModules.join(', ')}\n`;
      }
      report += '\n';
    });

    return report;
  }

  /**
   * Compare two bundle analyses for regression detection
   */
  compareAnalyses(current: BundleAnalysis, previous: BundleAnalysis): {
    sizeChange: number;
    gzippedSizeChange: number;
    moduleChanges: {
      added: string[];
      removed: string[];
      sizeIncreases: Array<{ module: string; increase: number }>;
      sizeDecreases: Array<{ module: string; decrease: number }>;
    };
    recommendations: string[];
  } {
    const sizeChange = current.totalSize - previous.totalSize;
    const gzippedSizeChange = current.gzippedSize - previous.gzippedSize;

    const currentModuleMap = new Map(current.modules.map(m => [m.name, m]));
    const previousModuleMap = new Map(previous.modules.map(m => [m.name, m]));

    const added = current.modules
      .filter(m => !previousModuleMap.has(m.name))
      .map(m => m.name);

    const removed = previous.modules
      .filter(m => !currentModuleMap.has(m.name))
      .map(m => m.name);

    const sizeIncreases: Array<{ module: string; increase: number }> = [];
    const sizeDecreases: Array<{ module: string; decrease: number }> = [];

    current.modules.forEach(currentModule => {
      const previousModule = previousModuleMap.get(currentModule.name);
      if (previousModule) {
        const sizeDiff = currentModule.size - previousModule.size;
        if (sizeDiff > 1000) { // > 1KB increase
          sizeIncreases.push({ module: currentModule.name, increase: sizeDiff });
        } else if (sizeDiff < -1000) { // > 1KB decrease
          sizeDecreases.push({ module: currentModule.name, decrease: -sizeDiff });
        }
      }
    });

    const recommendations: string[] = [];
    if (sizeChange > 50000) { // > 50KB increase
      recommendations.push('Bundle size increased significantly. Review recent changes.');
    }
    if (added.length > 10) {
      recommendations.push('Many new modules added. Consider lazy loading or chunking.');
    }
    if (sizeIncreases.length > 5) {
      recommendations.push('Multiple modules increased in size. Check for unnecessary dependencies.');
    }

    return {
      sizeChange,
      gzippedSizeChange,
      moduleChanges: {
        added,
        removed,
        sizeIncreases: sizeIncreases.sort((a, b) => b.increase - a.increase),
        sizeDecreases: sizeDecreases.sort((a, b) => b.decrease - a.decrease)
      },
      recommendations
    };
  }

  /**
   * Helper methods
   */
  private estimateGzippedSize(size: number): number {
    // Rough estimation: text compresses to ~30% of original size
    return Math.round(size * 0.3);
  }

  private getModuleBaseName(fullName: string): string {
    // Extract base package name from full module path
    const match = fullName.match(/node_modules\/([^\/]+)/);
    if (match) return match[1];
    
    // For local modules, get the directory name
    const parts = fullName.split('/');
    return parts[parts.length - 2] || parts[parts.length - 1];
  }

  private extractVersions(modules: ModuleAnalysis[]): string[] {
    // Extract version numbers from module paths
    const versions = new Set<string>();
    modules.forEach(module => {
      const versionMatch = module.path.match(/node_modules\/[^\/]+\/([0-9]+\.[0-9]+\.[0-9]+)/);
      if (versionMatch) {
        versions.add(versionMatch[1]);
      }
    });
    return Array.from(versions);
  }

  private formatSize(bytes: number): string {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  }

  private truncateModuleName(name: string, maxLength: number = 50): string {
    if (name.length <= maxLength) return name;
    return `...${name.substring(name.length - maxLength + 3)}`;
  }

  /**
   * Public methods for configuration
   */
  setBudget(name: string, budget: BundleBudget): void {
    this.budgets.set(name, budget);
  }

  getBudgets(): Record<string, BundleBudget> {
    return Object.fromEntries(this.budgets.entries());
  }

  getAnalysisHistory(): BundleAnalysis[] {
    return this.analysisHistory.slice(-10); // Last 10 analyses
  }

  clearHistory(): void {
    this.analysisHistory = [];
  }
}

// Singleton instance
export const bundleAnalyzer = new BundleAnalyzer();

export default BundleAnalyzer;