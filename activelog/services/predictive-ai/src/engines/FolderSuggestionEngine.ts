import { UserAction, UserPattern, Prediction } from '../types';
import { BehaviorPredictionEngine } from '../core/BehaviorPredictionEngine';
import { v4 as uuidv4 } from 'uuid';
import { groupBy, countBy, orderBy } from 'lodash';

export class FolderSuggestionEngine {
  private behaviorEngine: BehaviorPredictionEngine;
  private userFolderHierarchies: Map<string, FolderHierarchy> = new Map();

  constructor(behaviorEngine: BehaviorPredictionEngine) {
    this.behaviorEngine = behaviorEngine;
  }

  async suggestFolders(userId: string, currentPath: string, context?: any): Promise<string[]> {
    const hierarchy = this.getUserHierarchy(userId);
    const predictions = await this.behaviorEngine.getFolderSuggestions(userId, currentPath);
    
    const contextualSuggestions = this.getContextualSuggestions(userId, currentPath, context);
    const patternBasedSuggestions = this.getPatternBasedSuggestions(userId, currentPath);
    const semanticSuggestions = this.getSemanticSuggestions(currentPath, hierarchy);
    
    const allSuggestions = [
      ...predictions,
      ...contextualSuggestions,
      ...patternBasedSuggestions,
      ...semanticSuggestions
    ];
    
    return this.rankAndDedupeSuggestions(allSuggestions, userId, currentPath);
  }

  async suggestFolderName(userId: string, parentPath: string, context?: any): Promise<string[]> {
    const hierarchy = this.getUserHierarchy(userId);
    const parentNode = hierarchy.getNode(parentPath);
    
    if (!parentNode) {
      return this.getDefaultSuggestions(context);
    }
    
    const siblingNames = parentNode.children.map(c => c.name);
    const namingPatterns = this.extractNamingPatterns(siblingNames);
    
    const suggestions: string[] = [];
    
    suggestions.push(...this.generateFromPatterns(namingPatterns, context));
    suggestions.push(...this.generateFromContext(context));
    suggestions.push(...this.generateFromSiblings(siblingNames));
    suggestions.push(...this.generateSeasonalSuggestions(context));
    
    return suggestions.slice(0, 5);
  }

  async predictivelyCreateFolder(userId: string, triggerPath: string): Promise<string | null> {
    const patterns = await this.findCreationPatterns(userId, triggerPath);
    
    if (patterns.length === 0) return null;
    
    const bestPattern = patterns[0];
    if (bestPattern.confidence < 0.7) return null;
    
    const suggestedPath = this.generatePathFromPattern(bestPattern, triggerPath);
    
    if (suggestedPath && !this.pathExists(suggestedPath)) {
      return suggestedPath;
    }
    
    return null;
  }

  learnFromFolderCreation(action: UserAction): void {
    if (action.actionType !== 'folder_create') return;
    
    const hierarchy = this.getUserHierarchy(action.userId);
    hierarchy.addPath(action.resourcePath, action.timestamp);
    
    this.updateCreationPatterns(action);
  }

  private getUserHierarchy(userId: string): FolderHierarchy {
    if (!this.userFolderHierarchies.has(userId)) {
      this.userFolderHierarchies.set(userId, new FolderHierarchy());
    }
    return this.userFolderHierarchies.get(userId)!;
  }

  private getContextualSuggestions(userId: string, currentPath: string, context: any): string[] {
    const suggestions: string[] = [];
    
    if (!context) return suggestions;
    
    if (context.workMode === 'work') {
      suggestions.push(
        `${currentPath}/projects`,
        `${currentPath}/meetings`,
        `${currentPath}/documents`,
        `${currentPath}/reports`
      );
    }
    
    if (context.workMode === 'personal') {
      suggestions.push(
        `${currentPath}/photos`,
        `${currentPath}/personal`,
        `${currentPath}/hobbies`,
        `${currentPath}/finances`
      );
    }
    
    if (context.season === 'winter' && context.month === 11) {
      suggestions.push(`${currentPath}/holiday`, `${currentPath}/taxes-prep`);
    }
    
    if (context.month === 2) {
      suggestions.push(`${currentPath}/taxes`, `${currentPath}/receipts-2024`);
    }
    
    return suggestions.filter(s => !this.pathExists(s));
  }

  private getPatternBasedSuggestions(userId: string, currentPath: string): string[] {
    const hierarchy = this.getUserHierarchy(userId);
    const currentNode = hierarchy.getNode(currentPath);
    
    if (!currentNode) return [];
    
    const suggestions: string[] = [];
    const siblingPaths = currentNode.parent?.children.map(c => c.fullPath) || [];
    
    const patterns = this.findCommonPatterns(siblingPaths);
    
    for (const pattern of patterns) {
      const newPath = this.applyPattern(pattern, currentPath);
      if (newPath && !this.pathExists(newPath)) {
        suggestions.push(newPath);
      }
    }
    
    return suggestions.slice(0, 3);
  }

  private getSemanticSuggestions(currentPath: string, hierarchy: FolderHierarchy): string[] {
    const suggestions: string[] = [];
    const pathParts = currentPath.split('/').filter(p => p);
    const lastPart = pathParts[pathParts.length - 1]?.toLowerCase() || '';
    
    const semanticMaps: Record<string, string[]> = {
      'project': ['src', 'docs', 'tests', 'assets', 'config'],
      'work': ['projects', 'meetings', 'reports', 'templates'],
      'photo': ['2024', 'raw', 'edited', 'family', 'travel'],
      'document': ['drafts', 'final', 'archive', 'templates'],
      'finance': ['receipts', 'taxes', 'banking', 'investments']
    };
    
    for (const [key, values] of Object.entries(semanticMaps)) {
      if (lastPart.includes(key)) {
        for (const value of values) {
          const suggestionPath = `${currentPath}/${value}`;
          if (!this.pathExists(suggestionPath)) {
            suggestions.push(suggestionPath);
          }
        }
        break;
      }
    }
    
    return suggestions.slice(0, 3);
  }

  private rankAndDedupeSuggestions(suggestions: string[], userId: string, currentPath: string): string[] {
    const uniqueSuggestions = [...new Set(suggestions)];
    const hierarchy = this.getUserHierarchy(userId);
    
    return uniqueSuggestions
      .map(suggestion => ({
        path: suggestion,
        score: this.calculateSuggestionScore(suggestion, userId, currentPath, hierarchy)
      }))
      .sort((a, b) => b.score - a.score)
      .map(s => s.path)
      .slice(0, 5);
  }

  private calculateSuggestionScore(suggestion: string, userId: string, currentPath: string, hierarchy: FolderHierarchy): number {
    let score = 0;
    
    const depth = suggestion.split('/').length - currentPath.split('/').length;
    score += Math.max(0, 5 - depth);
    
    const parentNode = hierarchy.getNode(currentPath);
    if (parentNode) {
      const siblingCount = parentNode.children.length;
      score += Math.max(0, 3 - siblingCount);
    }
    
    const lastPart = suggestion.split('/').pop()?.toLowerCase() || '';
    const commonWords = ['documents', 'photos', 'projects', 'work', 'personal'];
    if (commonWords.includes(lastPart)) {
      score += 2;
    }
    
    if (/\d{4}/.test(lastPart)) {
      score += 1;
    }
    
    return score;
  }

  private extractNamingPatterns(names: string[]): NamingPattern[] {
    const patterns: NamingPattern[] = [];
    
    if (names.length < 2) return patterns;
    
    const hasDatePattern = names.some(n => /\d{4}-\d{2}-\d{2}/.test(n));
    if (hasDatePattern) {
      patterns.push({ type: 'date', format: 'YYYY-MM-DD', confidence: 0.8 });
    }
    
    const hasNumberedPattern = names.some(n => /\d+$/.test(n));
    if (hasNumberedPattern) {
      patterns.push({ type: 'numbered', format: 'name-###', confidence: 0.7 });
    }
    
    const hasProjectPattern = names.some(n => n.toLowerCase().includes('project'));
    if (hasProjectPattern) {
      patterns.push({ type: 'project', format: 'project-name', confidence: 0.6 });
    }
    
    return patterns;
  }

  private generateFromPatterns(patterns: NamingPattern[], context?: any): string[] {
    const suggestions: string[] = [];
    
    for (const pattern of patterns) {
      switch (pattern.type) {
        case 'date':
          const today = new Date();
          suggestions.push(today.toISOString().split('T')[0]);
          break;
        case 'numbered':
          suggestions.push('item-001', 'document-001');
          break;
        case 'project':
          suggestions.push('project-new', 'project-draft');
          break;
      }
    }
    
    return suggestions;
  }

  private generateFromContext(context?: any): string[] {
    if (!context) return [];
    
    const suggestions: string[] = [];
    const now = new Date();
    
    suggestions.push(now.getFullYear().toString());
    suggestions.push(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`);
    
    if (context.workMode === 'work') {
      suggestions.push('meeting-notes', 'project-docs', 'resources');
    }
    
    return suggestions;
  }

  private generateFromSiblings(siblingNames: string[]): string[] {
    const suggestions: string[] = [];
    
    const lastNumber = this.extractLastNumber(siblingNames);
    if (lastNumber !== null) {
      suggestions.push(`item-${String(lastNumber + 1).padStart(3, '0')}`);
    }
    
    return suggestions;
  }

  private generateSeasonalSuggestions(context?: any): string[] {
    if (!context) return [];
    
    const suggestions: string[] = [];
    const month = context.month || new Date().getMonth();
    
    const seasonalSuggestions: Record<number, string[]> = {
      11: ['holiday-2024', 'gift-ideas', 'year-end'],
      0: ['new-year', 'resolutions', 'planning'],
      2: ['taxes-2024', 'receipts', 'tax-docs'],
      5: ['summer-plans', 'vacation', 'outdoor'],
      8: ['back-to-school', 'autumn', 'planning']
    };
    
    return seasonalSuggestions[month] || [];
  }

  private async findCreationPatterns(userId: string, triggerPath: string): Promise<UserPattern[]> {
    return [];
  }

  private generatePathFromPattern(pattern: UserPattern, triggerPath: string): string | null {
    return null;
  }

  private updateCreationPatterns(action: UserAction): void {
  }

  private pathExists(path: string): boolean {
    return false;
  }

  private findCommonPatterns(paths: string[]): string[] {
    return [];
  }

  private applyPattern(pattern: string, currentPath: string): string | null {
    return null;
  }

  private extractLastNumber(names: string[]): number | null {
    const numbers = names
      .map(name => {
        const match = name.match(/(\d+)$/);
        return match ? parseInt(match[1], 10) : null;
      })
      .filter(n => n !== null) as number[];
    
    return numbers.length > 0 ? Math.max(...numbers) : null;
  }

  private getDefaultSuggestions(context?: any): string[] {
    return ['documents', 'images', 'projects', 'archive', 'temp'];
  }
}

interface NamingPattern {
  type: 'date' | 'numbered' | 'project' | 'category';
  format: string;
  confidence: number;
}

class FolderHierarchy {
  private root: FolderNode;
  private pathMap: Map<string, FolderNode> = new Map();

  constructor() {
    this.root = new FolderNode('/', null);
    this.pathMap.set('/', this.root);
  }

  addPath(fullPath: string, timestamp: Date): FolderNode {
    const parts = fullPath.split('/').filter(p => p);
    let currentNode = this.root;
    let currentPath = '';

    for (const part of parts) {
      currentPath += `/${part}`;
      
      let childNode = this.pathMap.get(currentPath);
      if (!childNode) {
        childNode = new FolderNode(part, currentNode);
        currentNode.children.push(childNode);
        this.pathMap.set(currentPath, childNode);
      }
      
      childNode.lastAccessed = timestamp;
      currentNode = childNode;
    }

    return currentNode;
  }

  getNode(path: string): FolderNode | null {
    return this.pathMap.get(path) || null;
  }
}

class FolderNode {
  public fullPath: string;
  public children: FolderNode[] = [];
  public lastAccessed: Date = new Date();
  public accessCount: number = 0;

  constructor(
    public name: string,
    public parent: FolderNode | null
  ) {
    this.fullPath = parent ? `${parent.fullPath}/${name}`.replace(/\/+/g, '/') : name;
  }
}