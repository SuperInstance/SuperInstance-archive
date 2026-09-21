import { UserAction, UserPattern } from '../types';
import { v4 as uuidv4 } from 'uuid';
import { differenceInMinutes, differenceInHours, isSameDay, getDay, getHours } from 'date-fns';
import { groupBy, countBy, orderBy } from 'lodash';

export class PatternExtractor {
  
  async extractPatterns(actions: UserAction[]): Promise<UserPattern[]> {
    const patterns: UserPattern[] = [];
    
    if (actions.length < 5) return patterns;
    
    patterns.push(...await this.extractTemporalPatterns(actions));
    patterns.push(...await this.extractSequentialPatterns(actions));
    patterns.push(...await this.extractCategoricalPatterns(actions));
    patterns.push(...await this.extractContextualPatterns(actions));
    
    return patterns.filter(p => p.confidence > 0.2);
  }

  private async extractTemporalPatterns(actions: UserAction[]): Promise<UserPattern[]> {
    const patterns: UserPattern[] = [];
    
    const hourlyGroups = groupBy(actions, a => getHours(new Date(a.timestamp)));
    for (const [hour, hourActions] of Object.entries(hourlyGroups)) {
      if (hourActions.length >= 3) {
        const actionTypes = countBy(hourActions, 'actionType');
        const dominantAction = Object.keys(actionTypes).reduce((a, b) => 
          actionTypes[a] > actionTypes[b] ? a : b
        );
        
        patterns.push({
          id: uuidv4(),
          userId: hourActions[0].userId,
          patternType: 'temporal',
          confidence: Math.min(hourActions.length / 10, 0.9),
          frequency: hourActions.length,
          lastSeen: new Date(),
          pattern: {
            timeOfDay: parseInt(hour),
            actionType: dominantAction,
            avgActions: hourActions.length / 7 // Assuming weekly pattern
          }
        });
      }
    }
    
    const dayOfWeekGroups = groupBy(actions, a => getDay(new Date(a.timestamp)));
    for (const [day, dayActions] of Object.entries(dayOfWeekGroups)) {
      if (dayActions.length >= 5) {
        const resourcePaths = countBy(dayActions, 'resourcePath');
        const commonPath = Object.keys(resourcePaths).reduce((a, b) => 
          resourcePaths[a] > resourcePaths[b] ? a : b
        );
        
        patterns.push({
          id: uuidv4(),
          userId: dayActions[0].userId,
          patternType: 'temporal',
          confidence: Math.min(dayActions.length / 20, 0.8),
          frequency: dayActions.length,
          lastSeen: new Date(),
          pattern: {
            dayOfWeek: parseInt(day),
            commonPath,
            actionTypes: Object.keys(countBy(dayActions, 'actionType'))
          }
        });
      }
    }
    
    const monthlyPatterns = this.extractMonthlyPatterns(actions);
    patterns.push(...monthlyPatterns);
    
    return patterns;
  }

  private extractMonthlyPatterns(actions: UserAction[]): UserPattern[] {
    const patterns: UserPattern[] = [];
    
    const monthlyGroups = groupBy(actions, a => new Date(a.timestamp).getMonth());
    
    for (const [month, monthActions] of Object.entries(monthlyGroups)) {
      if (monthActions.length >= 10) {
        const pathKeywords = this.extractPathKeywords(monthActions);
        const seasonalKeywords = ['tax', 'receipt', 'holiday', 'vacation', 'budget'];
        
        const hasSeasonalActivity = seasonalKeywords.some(keyword => 
          pathKeywords.some(path => path.toLowerCase().includes(keyword))
        );
        
        if (hasSeasonalActivity) {
          patterns.push({
            id: uuidv4(),
            userId: monthActions[0].userId,
            patternType: 'temporal',
            confidence: Math.min(monthActions.length / 50, 0.95),
            frequency: monthActions.length,
            lastSeen: new Date(),
            pattern: {
              month: parseInt(month),
              seasonalActivity: true,
              keywords: pathKeywords.slice(0, 5),
              actionTypes: Object.keys(countBy(monthActions, 'actionType'))
            }
          });
        }
      }
    }
    
    return patterns;
  }

  private async extractSequentialPatterns(actions: UserAction[]): Promise<UserPattern[]> {
    const patterns: UserPattern[] = [];
    const sortedActions = orderBy(actions, 'timestamp');
    
    for (let i = 0; i < sortedActions.length - 2; i++) {
      const sequence = sortedActions.slice(i, i + 3);
      
      if (this.isValidSequence(sequence)) {
        const sequenceKey = sequence.map(a => a.actionType).join('->');
        
        const existingPattern = patterns.find(p => 
          p.pattern.sequence === sequenceKey && 
          p.userId === sequence[0].userId
        );
        
        if (existingPattern) {
          existingPattern.frequency++;
          existingPattern.confidence = Math.min(existingPattern.frequency / 10, 0.9);
        } else {
          patterns.push({
            id: uuidv4(),
            userId: sequence[0].userId,
            patternType: 'sequential',
            confidence: 0.3,
            frequency: 1,
            lastSeen: new Date(),
            pattern: {
              sequence: sequenceKey,
              avgTimeBetween: this.calculateAvgTimeBetween(sequence),
              triggerConditions: this.extractTriggerConditions(sequence)
            },
            triggers: [sequence[0].actionType],
            outcomes: [sequence[2].actionType]
          });
        }
      }
    }
    
    return patterns.filter(p => p.frequency >= 3);
  }

  private async extractCategoricalPatterns(actions: UserAction[]): Promise<UserPattern[]> {
    const patterns: UserPattern[] = [];
    
    const folderActions = actions.filter(a => a.actionType === 'folder_create');
    if (folderActions.length >= 5) {
      const folderNames = folderActions.map(a => this.extractFolderName(a.resourcePath));
      const categories = this.categorizeNames(folderNames);
      
      for (const [category, names] of Object.entries(categories)) {
        if (names.length >= 3) {
          patterns.push({
            id: uuidv4(),
            userId: folderActions[0].userId,
            patternType: 'categorical',
            confidence: Math.min(names.length / 10, 0.8),
            frequency: names.length,
            lastSeen: new Date(),
            pattern: {
              category,
              commonNames: names.slice(0, 5),
              namingConvention: this.detectNamingConvention(names)
            }
          });
        }
      }
    }
    
    const tagPatterns = this.extractTagPatterns(actions);
    patterns.push(...tagPatterns);
    
    return patterns;
  }

  private async extractContextualPatterns(actions: UserAction[]): Promise<UserPattern[]> {
    const patterns: UserPattern[] = [];
    
    const contextGroups = groupBy(actions.filter(a => a.context), a => {
      const ctx = a.context!;
      return `${ctx.deviceType || 'unknown'}_${ctx.location || 'unknown'}`;
    });
    
    for (const [contextKey, contextActions] of Object.entries(contextGroups)) {
      if (contextActions.length >= 5) {
        const [deviceType, location] = contextKey.split('_');
        
        patterns.push({
          id: uuidv4(),
          userId: contextActions[0].userId,
          patternType: 'contextual',
          confidence: Math.min(contextActions.length / 15, 0.7),
          frequency: contextActions.length,
          lastSeen: new Date(),
          pattern: {
            deviceType: deviceType !== 'unknown' ? deviceType : undefined,
            location: location !== 'unknown' ? location : undefined,
            preferredActions: Object.keys(countBy(contextActions, 'actionType')),
            commonPaths: this.extractCommonPaths(contextActions)
          }
        });
      }
    }
    
    return patterns;
  }

  private isValidSequence(sequence: UserAction[]): boolean {
    if (sequence.length !== 3) return false;
    
    const timeDiffs = [];
    for (let i = 1; i < sequence.length; i++) {
      const diff = differenceInMinutes(
        new Date(sequence[i].timestamp),
        new Date(sequence[i-1].timestamp)
      );
      timeDiffs.push(diff);
    }
    
    return timeDiffs.every(diff => diff > 0 && diff < 60);
  }

  private calculateAvgTimeBetween(sequence: UserAction[]): number {
    let totalMinutes = 0;
    for (let i = 1; i < sequence.length; i++) {
      totalMinutes += differenceInMinutes(
        new Date(sequence[i].timestamp),
        new Date(sequence[i-1].timestamp)
      );
    }
    return totalMinutes / (sequence.length - 1);
  }

  private extractTriggerConditions(sequence: UserAction[]): string[] {
    const conditions: string[] = [];
    
    const firstAction = sequence[0];
    if (firstAction.context) {
      if (firstAction.context.timeOfDay) {
        conditions.push(`time_${firstAction.context.timeOfDay}`);
      }
      if (firstAction.context.dayOfWeek) {
        conditions.push(`day_${firstAction.context.dayOfWeek}`);
      }
    }
    
    return conditions;
  }

  private extractFolderName(path: string): string {
    return path.split('/').pop() || '';
  }

  private categorizeNames(names: string[]): Record<string, string[]> {
    const categories: Record<string, string[]> = {};
    
    for (const name of names) {
      const lowerName = name.toLowerCase();
      
      if (lowerName.includes('project') || lowerName.includes('work')) {
        categories['work'] = categories['work'] || [];
        categories['work'].push(name);
      } else if (lowerName.includes('photo') || lowerName.includes('image')) {
        categories['media'] = categories['media'] || [];
        categories['media'].push(name);
      } else if (lowerName.includes('doc') || lowerName.includes('file')) {
        categories['documents'] = categories['documents'] || [];
        categories['documents'].push(name);
      } else if (/\d{4}/.test(name)) {
        categories['dated'] = categories['dated'] || [];
        categories['dated'].push(name);
      } else {
        categories['other'] = categories['other'] || [];
        categories['other'].push(name);
      }
    }
    
    return categories;
  }

  private detectNamingConvention(names: string[]): string {
    const hasUnderscores = names.some(n => n.includes('_'));
    const hasDashes = names.some(n => n.includes('-'));
    const hasSpaces = names.some(n => n.includes(' '));
    const hasDates = names.some(n => /\d{4}-\d{2}-\d{2}/.test(n));
    
    if (hasDates) return 'date_prefixed';
    if (hasUnderscores) return 'snake_case';
    if (hasDashes) return 'kebab-case';
    if (hasSpaces) return 'space_separated';
    
    return 'camelCase';
  }

  private extractTagPatterns(actions: UserAction[]): UserPattern[] {
    const patterns: UserPattern[] = [];
    const tagActions = actions.filter(a => a.actionType === 'tag_add');
    
    if (tagActions.length >= 5) {
      const tagFrequency = countBy(tagActions, a => a.metadata?.tag);
      const frequentTags = Object.entries(tagFrequency)
        .filter(([_, count]) => count >= 3)
        .map(([tag, count]) => ({ tag, count }));
      
      if (frequentTags.length > 0) {
        patterns.push({
          id: uuidv4(),
          userId: tagActions[0].userId,
          patternType: 'categorical',
          confidence: Math.min(frequentTags.length / 10, 0.8),
          frequency: frequentTags.reduce((sum, t) => sum + t.count, 0),
          lastSeen: new Date(),
          pattern: {
            category: 'tagging',
            frequentTags: frequentTags.map(t => t.tag),
            avgTagsPerAction: frequentTags.length / tagActions.length
          }
        });
      }
    }
    
    return patterns;
  }

  private extractPathKeywords(actions: UserAction[]): string[] {
    const allPaths = actions.map(a => a.resourcePath).join(' ');
    const words = allPaths.toLowerCase().split(/[\/\-_\s]+/);
    const wordCount = countBy(words.filter(w => w.length > 3));
    
    return Object.entries(wordCount)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .map(([word]) => word);
  }

  private extractCommonPaths(actions: UserAction[]): string[] {
    const pathCount = countBy(actions, 'resourcePath');
    return Object.entries(pathCount)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([path]) => path);
  }
}