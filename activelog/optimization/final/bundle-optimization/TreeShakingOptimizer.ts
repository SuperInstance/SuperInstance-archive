/**
 * Advanced Tree Shaking Optimization System
 * Automated dead code elimination and import optimization
 */

import * as fs from 'fs';
import * as path from 'path';
import * as typescript from 'typescript';

interface UnusedExport {
  file: string;
  export: string;
  line: number;
  type: 'function' | 'class' | 'variable' | 'type' | 'interface';
  references: number;
}

interface ImportAnalysis {
  file: string;
  imports: Array<{
    module: string;
    imports: string[];
    isDefault: boolean;
    isNamespace: boolean;
    line: number;
    used: string[];
    unused: string[];
  }>;
}

interface SideEffectAnalysis {
  file: string;
  hasSideEffects: boolean;
  sideEffects: Array<{
    type: 'console' | 'global' | 'mutation' | 'unknown';
    line: number;
    description: string;
  }>;
}

interface OptimizationResult {
  filesAnalyzed: number;
  unusedExports: UnusedExport[];
  unusedImports: ImportAnalysis[];
  sideEffects: SideEffectAnalysis[];
  potentialSavings: number;
  recommendations: Array<{
    type: 'remove-export' | 'remove-import' | 'mark-side-effect-free' | 'split-module';
    file: string;
    description: string;
    impact: 'high' | 'medium' | 'low';
    automated: boolean;
  }>;
}

class TreeShakingOptimizer {
  private program: typescript.Program | null = null;
  private checker: typescript.TypeChecker | null = null;
  private sourceFiles: Map<string, typescript.SourceFile> = new Map();
  private exportUsage: Map<string, Set<string>> = new Map();
  private importUsage: Map<string, Set<string>> = new Map();

  constructor(private projectRoot: string) {}

  /**
   * Analyze project for tree shaking opportunities
   */
  async analyzeProject(): Promise<OptimizationResult> {
    console.log('🔍 Starting tree shaking analysis...');

    // Initialize TypeScript program
    this.initializeProgram();

    const sourceFiles = this.program!.getSourceFiles()
      .filter(sf => !sf.isDeclarationFile && sf.fileName.includes(this.projectRoot));

    console.log(`📁 Analyzing ${sourceFiles.length} files...`);

    // Analyze exports and imports
    const unusedExports = this.findUnusedExports(sourceFiles);
    const unusedImports = this.findUnusedImports(sourceFiles);
    const sideEffects = this.analyzeSideEffects(sourceFiles);

    // Calculate potential savings
    const potentialSavings = this.calculatePotentialSavings(unusedExports, unusedImports);

    // Generate recommendations
    const recommendations = this.generateRecommendations(unusedExports, unusedImports, sideEffects);

    return {
      filesAnalyzed: sourceFiles.length,
      unusedExports,
      unusedImports,
      sideEffects,
      potentialSavings,
      recommendations
    };
  }

  /**
   * Initialize TypeScript program
   */
  private initializeProgram(): void {
    const configPath = typescript.findConfigFile(this.projectRoot, typescript.sys.fileExists, 'tsconfig.json');
    
    if (!configPath) {
      throw new Error('Could not find tsconfig.json');
    }

    const configFile = typescript.readConfigFile(configPath, typescript.sys.readFile);
    const parsedConfig = typescript.parseJsonConfigFileContent(
      configFile.config,
      typescript.sys,
      path.dirname(configPath)
    );

    this.program = typescript.createProgram({
      rootNames: parsedConfig.fileNames,
      options: parsedConfig.options
    });

    this.checker = this.program.getTypeChecker();

    // Cache source files
    this.program.getSourceFiles().forEach(sf => {
      this.sourceFiles.set(sf.fileName, sf);
    });
  }

  /**
   * Find unused exports across the project
   */
  private findUnusedExports(sourceFiles: typescript.SourceFile[]): UnusedExport[] {
    console.log('🔍 Finding unused exports...');
    const unusedExports: UnusedExport[] = [];

    // First pass: collect all exports
    const allExports = new Map<string, Set<string>>();
    sourceFiles.forEach(sourceFile => {
      const exports = new Set<string>();
      this.visitNode(sourceFile, node => {
        this.collectExports(node, exports, sourceFile);
      });
      allExports.set(sourceFile.fileName, exports);
    });

    // Second pass: find usage of exports
    const usageMap = new Map<string, Map<string, number>>();
    sourceFiles.forEach(sourceFile => {
      this.visitNode(sourceFile, node => {
        this.collectImportUsage(node, usageMap, sourceFile);
      });
    });

    // Third pass: identify unused exports
    allExports.forEach((exports, fileName) => {
      const fileUsage = usageMap.get(fileName) || new Map();
      
      exports.forEach(exportName => {
        const usageCount = fileUsage.get(exportName) || 0;
        if (usageCount === 0 && !this.isEntryPoint(fileName)) {
          const sourceFile = this.sourceFiles.get(fileName)!;
          const exportInfo = this.getExportInfo(sourceFile, exportName);
          
          if (exportInfo) {
            unusedExports.push({
              file: fileName,
              export: exportName,
              line: exportInfo.line,
              type: exportInfo.type,
              references: usageCount
            });
          }
        }
      });
    });

    return unusedExports.sort((a, b) => b.references - a.references);
  }

  /**
   * Find unused imports in files
   */
  private findUnusedImports(sourceFiles: typescript.SourceFile[]): ImportAnalysis[] {
    console.log('🔍 Finding unused imports...');
    const analyses: ImportAnalysis[] = [];

    sourceFiles.forEach(sourceFile => {
      const imports: ImportAnalysis['imports'] = [];
      
      this.visitNode(sourceFile, node => {
        if (typescript.isImportDeclaration(node)) {
          const analysis = this.analyzeImportDeclaration(node, sourceFile);
          if (analysis) {
            imports.push(analysis);
          }
        }
      });

      if (imports.length > 0) {
        analyses.push({
          file: sourceFile.fileName,
          imports
        });
      }
    });

    return analyses.filter(analysis => 
      analysis.imports.some(imp => imp.unused.length > 0)
    );
  }

  /**
   * Analyze side effects in modules
   */
  private analyzeSideEffects(sourceFiles: typescript.SourceFile[]): SideEffectAnalysis[] {
    console.log('🔍 Analyzing side effects...');
    const analyses: SideEffectAnalysis[] = [];

    sourceFiles.forEach(sourceFile => {
      const sideEffects: SideEffectAnalysis['sideEffects'] = [];
      
      this.visitNode(sourceFile, node => {
        const effect = this.detectSideEffect(node, sourceFile);
        if (effect) {
          sideEffects.push(effect);
        }
      });

      analyses.push({
        file: sourceFile.fileName,
        hasSideEffects: sideEffects.length > 0,
        sideEffects
      });
    });

    return analyses.filter(analysis => analysis.hasSideEffects);
  }

  /**
   * Visit AST nodes recursively
   */
  private visitNode(node: typescript.Node, callback: (node: typescript.Node) => void): void {
    callback(node);
    typescript.forEachChild(node, child => this.visitNode(child, callback));
  }

  /**
   * Collect exports from a node
   */
  private collectExports(node: typescript.Node, exports: Set<string>, sourceFile: typescript.SourceFile): void {
    if (typescript.isExportDeclaration(node)) {
      if (node.exportClause && typescript.isNamedExports(node.exportClause)) {
        node.exportClause.elements.forEach(element => {
          exports.add(element.name.text);
        });
      }
    } else if (typescript.isFunctionDeclaration(node) && this.hasExportModifier(node)) {
      if (node.name) {
        exports.add(node.name.text);
      }
    } else if (typescript.isClassDeclaration(node) && this.hasExportModifier(node)) {
      if (node.name) {
        exports.add(node.name.text);
      }
    } else if (typescript.isVariableStatement(node) && this.hasExportModifier(node)) {
      node.declarationList.declarations.forEach(decl => {
        if (typescript.isIdentifier(decl.name)) {
          exports.add(decl.name.text);
        }
      });
    } else if (typescript.isInterfaceDeclaration(node) && this.hasExportModifier(node)) {
      exports.add(node.name.text);
    } else if (typescript.isTypeAliasDeclaration(node) && this.hasExportModifier(node)) {
      exports.add(node.name.text);
    }
  }

  /**
   * Collect import usage
   */
  private collectImportUsage(
    node: typescript.Node, 
    usageMap: Map<string, Map<string, number>>, 
    sourceFile: typescript.SourceFile
  ): void {
    if (typescript.isImportDeclaration(node)) {
      const moduleSpecifier = (node.moduleSpecifier as typescript.StringLiteral).text;
      const resolvedModule = this.resolveModule(moduleSpecifier, sourceFile.fileName);
      
      if (resolvedModule && node.importClause) {
        if (!usageMap.has(resolvedModule)) {
          usageMap.set(resolvedModule, new Map());
        }
        
        const fileUsage = usageMap.get(resolvedModule)!;
        
        // Default import
        if (node.importClause.name) {
          const defaultImportName = node.importClause.name.text;
          const usageCount = this.countIdentifierUsage(sourceFile, defaultImportName);
          fileUsage.set('default', (fileUsage.get('default') || 0) + usageCount);
        }
        
        // Named imports
        if (node.importClause.namedBindings && typescript.isNamedImports(node.importClause.namedBindings)) {
          node.importClause.namedBindings.elements.forEach(element => {
            const importName = element.name.text;
            const usageCount = this.countIdentifierUsage(sourceFile, importName);
            fileUsage.set(importName, (fileUsage.get(importName) || 0) + usageCount);
          });
        }
        
        // Namespace import
        if (node.importClause.namedBindings && typescript.isNamespaceImport(node.importClause.namedBindings)) {
          const namespaceName = node.importClause.namedBindings.name.text;
          const usageCount = this.countIdentifierUsage(sourceFile, namespaceName);
          fileUsage.set(namespaceName, (fileUsage.get(namespaceName) || 0) + usageCount);
        }
      }
    }
  }

  /**
   * Analyze import declaration for unused imports
   */
  private analyzeImportDeclaration(
    node: typescript.ImportDeclaration, 
    sourceFile: typescript.SourceFile
  ): ImportAnalysis['imports'][0] | null {
    const moduleSpecifier = (node.moduleSpecifier as typescript.StringLiteral).text;
    
    if (!node.importClause) return null;

    const importInfo = {
      module: moduleSpecifier,
      imports: [] as string[],
      isDefault: false,
      isNamespace: false,
      line: sourceFile.getLineAndCharacterOfPosition(node.pos).line + 1,
      used: [] as string[],
      unused: [] as string[]
    };

    // Default import
    if (node.importClause.name) {
      const importName = node.importClause.name.text;
      importInfo.imports.push(importName);
      importInfo.isDefault = true;
      
      const usageCount = this.countIdentifierUsage(sourceFile, importName);
      if (usageCount > 0) {
        importInfo.used.push(importName);
      } else {
        importInfo.unused.push(importName);
      }
    }

    // Named imports
    if (node.importClause.namedBindings && typescript.isNamedImports(node.importClause.namedBindings)) {
      node.importClause.namedBindings.elements.forEach(element => {
        const importName = element.name.text;
        importInfo.imports.push(importName);
        
        const usageCount = this.countIdentifierUsage(sourceFile, importName);
        if (usageCount > 0) {
          importInfo.used.push(importName);
        } else {
          importInfo.unused.push(importName);
        }
      });
    }

    // Namespace import
    if (node.importClause.namedBindings && typescript.isNamespaceImport(node.importClause.namedBindings)) {
      const importName = node.importClause.namedBindings.name.text;
      importInfo.imports.push(importName);
      importInfo.isNamespace = true;
      
      const usageCount = this.countIdentifierUsage(sourceFile, importName);
      if (usageCount > 0) {
        importInfo.used.push(importName);
      } else {
        importInfo.unused.push(importName);
      }
    }

    return importInfo;
  }

  /**
   * Detect side effects in code
   */
  private detectSideEffect(
    node: typescript.Node, 
    sourceFile: typescript.SourceFile
  ): SideEffectAnalysis['sideEffects'][0] | null {
    const line = sourceFile.getLineAndCharacterOfPosition(node.pos).line + 1;

    // Console statements
    if (typescript.isCallExpression(node)) {
      if (typescript.isPropertyAccessExpression(node.expression)) {
        if (typescript.isIdentifier(node.expression.expression) && 
            node.expression.expression.text === 'console') {
          return {
            type: 'console',
            line,
            description: `Console.${node.expression.name.text}() call`
          };
        }
      }
    }

    // Global variable assignments
    if (typescript.isBinaryExpression(node) && node.operatorToken.kind === typescript.SyntaxKind.EqualsToken) {
      if (typescript.isPropertyAccessExpression(node.left)) {
        if (typescript.isIdentifier(node.left.expression)) {
          const objectName = node.left.expression.text;
          if (['window', 'global', 'globalThis'].includes(objectName)) {
            return {
              type: 'global',
              line,
              description: `Assignment to ${objectName}.${node.left.name.text}`
            };
          }
        }
      }
    }

    // DOM mutations
    if (typescript.isCallExpression(node)) {
      if (typescript.isPropertyAccessExpression(node.expression)) {
        const methodName = node.expression.name.text;
        const domMethods = ['appendChild', 'removeChild', 'setAttribute', 'innerHTML', 'textContent'];
        if (domMethods.includes(methodName)) {
          return {
            type: 'mutation',
            line,
            description: `DOM mutation: ${methodName}`
          };
        }
      }
    }

    return null;
  }

  /**
   * Helper methods
   */
  private hasExportModifier(node: typescript.Node): boolean {
    return node.modifiers?.some(modifier => 
      modifier.kind === typescript.SyntaxKind.ExportKeyword
    ) || false;
  }

  private isEntryPoint(fileName: string): boolean {
    const entryPoints = ['index.ts', 'index.tsx', 'main.ts', 'main.tsx', 'app.ts', 'app.tsx'];
    return entryPoints.some(entry => fileName.endsWith(entry));
  }

  private getExportInfo(sourceFile: typescript.SourceFile, exportName: string): { line: number; type: UnusedExport['type'] } | null {
    let result: { line: number; type: UnusedExport['type'] } | null = null;

    this.visitNode(sourceFile, node => {
      if (typescript.isFunctionDeclaration(node) && 
          node.name?.text === exportName && 
          this.hasExportModifier(node)) {
        result = {
          line: sourceFile.getLineAndCharacterOfPosition(node.pos).line + 1,
          type: 'function'
        };
      } else if (typescript.isClassDeclaration(node) && 
                 node.name?.text === exportName && 
                 this.hasExportModifier(node)) {
        result = {
          line: sourceFile.getLineAndCharacterOfPosition(node.pos).line + 1,
          type: 'class'
        };
      }
      // Add more export type checks...
    });

    return result;
  }

  private resolveModule(moduleSpecifier: string, fromFile: string): string | null {
    // Simplified module resolution - in practice, use TypeScript's module resolution
    if (moduleSpecifier.startsWith('./') || moduleSpecifier.startsWith('../')) {
      return path.resolve(path.dirname(fromFile), moduleSpecifier);
    }
    return null;
  }

  private countIdentifierUsage(sourceFile: typescript.SourceFile, identifier: string): number {
    let count = 0;
    
    this.visitNode(sourceFile, node => {
      if (typescript.isIdentifier(node) && node.text === identifier) {
        count++;
      }
    });
    
    return Math.max(0, count - 1); // Subtract 1 for the declaration itself
  }

  private calculatePotentialSavings(unusedExports: UnusedExport[], unusedImports: ImportAnalysis[]): number {
    // Rough estimation based on average code size per export/import
    const avgExportSize = 500; // bytes
    const avgImportSize = 100; // bytes

    const exportSavings = unusedExports.length * avgExportSize;
    const importSavings = unusedImports.reduce((sum, analysis) => {
      return sum + analysis.imports.reduce((importSum, imp) => {
        return importSum + (imp.unused.length * avgImportSize);
      }, 0);
    }, 0);

    return exportSavings + importSavings;
  }

  private generateRecommendations(
    unusedExports: UnusedExport[], 
    unusedImports: ImportAnalysis[], 
    sideEffects: SideEffectAnalysis[]
  ): OptimizationResult['recommendations'] {
    const recommendations: OptimizationResult['recommendations'] = [];

    // Unused exports recommendations
    unusedExports.slice(0, 10).forEach(exp => {
      recommendations.push({
        type: 'remove-export',
        file: exp.file,
        description: `Remove unused export '${exp.export}' from ${path.basename(exp.file)}`,
        impact: 'medium',
        automated: true
      });
    });

    // Unused imports recommendations
    unusedImports.slice(0, 10).forEach(analysis => {
      analysis.imports.forEach(imp => {
        if (imp.unused.length > 0) {
          recommendations.push({
            type: 'remove-import',
            file: analysis.file,
            description: `Remove unused imports: ${imp.unused.join(', ')} from '${imp.module}'`,
            impact: 'low',
            automated: true
          });
        }
      });
    });

    // Side effect recommendations
    const sideEffectFree = sideEffects.filter(analysis => 
      analysis.sideEffects.every(effect => effect.type === 'console')
    );

    sideEffectFree.slice(0, 5).forEach(analysis => {
      recommendations.push({
        type: 'mark-side-effect-free',
        file: analysis.file,
        description: `Mark ${path.basename(analysis.file)} as side-effect free in package.json`,
        impact: 'high',
        automated: false
      });
    });

    return recommendations.sort((a, b) => {
      const impactOrder = { 'high': 3, 'medium': 2, 'low': 1 };
      return impactOrder[b.impact] - impactOrder[a.impact];
    });
  }

  /**
   * Generate optimization report
   */
  generateReport(result: OptimizationResult): string {
    let report = '# Tree Shaking Optimization Report\n\n';

    // Summary
    report += '## Summary\n';
    report += `**Files Analyzed:** ${result.filesAnalyzed}\n`;
    report += `**Unused Exports:** ${result.unusedExports.length}\n`;
    report += `**Files with Unused Imports:** ${result.unusedImports.length}\n`;
    report += `**Files with Side Effects:** ${result.sideEffects.length}\n`;
    report += `**Potential Savings:** ${this.formatBytes(result.potentialSavings)}\n\n`;

    // Top unused exports
    if (result.unusedExports.length > 0) {
      report += '## Top Unused Exports\n';
      report += '| File | Export | Type | Line |\n';
      report += '|------|---------|------|------|\n';
      result.unusedExports.slice(0, 10).forEach(exp => {
        const fileName = path.basename(exp.file);
        report += `| ${fileName} | ${exp.export} | ${exp.type} | ${exp.line} |\n`;
      });
      report += '\n';
    }

    // Unused imports
    if (result.unusedImports.length > 0) {
      report += '## Files with Unused Imports\n';
      result.unusedImports.slice(0, 10).forEach(analysis => {
        const fileName = path.basename(analysis.file);
        report += `### ${fileName}\n`;
        analysis.imports.forEach(imp => {
          if (imp.unused.length > 0) {
            report += `- **${imp.module}**: Remove ${imp.unused.join(', ')}\n`;
          }
        });
        report += '\n';
      });
    }

    // Recommendations
    if (result.recommendations.length > 0) {
      report += '## Recommendations\n';
      result.recommendations.slice(0, 10).forEach((rec, i) => {
        const priority = rec.impact.toUpperCase();
        const automated = rec.automated ? '🤖 Automated' : '👤 Manual';
        report += `### ${i + 1}. ${rec.description}\n`;
        report += `**Priority:** ${priority} | **Type:** ${automated}\n`;
        report += `**File:** ${path.basename(rec.file)}\n\n`;
      });
    }

    return report;
  }

  private formatBytes(bytes: number): string {
    const sizes = ['B', 'KB', 'MB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  }
}

export default TreeShakingOptimizer;