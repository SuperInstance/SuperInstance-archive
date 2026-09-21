import { UserAction, UserPattern, Prediction } from '../types';
import { BehaviorPredictionEngine } from '../core/BehaviorPredictionEngine';
import { FutureNeedsPredictor } from './FutureNeedsPredictor';
import { v4 as uuidv4 } from 'uuid';
import { differenceInMinutes, addMinutes, isAfter } from 'date-fns';
import { orderBy } from 'lodash';

export class SmartPreCachingEngine {
  private behaviorEngine: BehaviorPredictionEngine;
  private futureNeedsPredictor: FutureNeedsPredictor;
  private cacheQueue: Map<string, CacheEntry[]> = new Map();
  private cacheStats: Map<string, CacheStats> = new Map();
  private accessPatterns: Map<string, AccessPattern[]> = new Map();
  private maxCacheSize: number = 1000; // Max files to pre-cache per user

  constructor(
    behaviorEngine: BehaviorPredictionEngine,
    futureNeedsPredictor: FutureNeedsPredictor
  ) {
    this.behaviorEngine = behaviorEngine;
    this.futureNeedsPredictor = futureNeedsPredictor;
  }

  async generateCacheRecommendations(userId: string): Promise<CacheRecommendation[]> {
    const recommendations: CacheRecommendation[] = [];
    
    recommendations.push(...await this.predictImmediateNeeds(userId));
    recommendations.push(...await this.predictSequentialAccess(userId));
    recommendations.push(...await this.predictContextualNeeds(userId));
    recommendations.push(...await this.predictSeasonalNeeds(userId));
    
    return this.rankAndOptimizeCacheRecommendations(userId, recommendations);
  }

  async shouldPreCache(userId: string, filePath: string): Promise<boolean> {
    const predictions = await this.behaviorEngine.predictNextActions(userId);
    const fileAccessPredictions = predictions.filter(p => 
      p.predictionType === 'file_access' && 
      p.payload.predictedPath === filePath
    );
    
    if (fileAccessPredictions.length === 0) {
      return false;
    }
    
    const highestConfidence = Math.max(...fileAccessPredictions.map(p => p.confidence));
    const cacheStats = this.getCacheStats(userId);
    
    // Consider caching if confidence is high and we have cache space
    return highestConfidence > 0.6 && cacheStats.currentSize < this.maxCacheSize;
  }

  async updateAccessPattern(userId: string, action: UserAction): Promise<void> {
    if (!this.accessPatterns.has(userId)) {
      this.accessPatterns.set(userId, []);
    }
    
    const patterns = this.accessPatterns.get(userId)!;
    const now = new Date();
    
    // Create new access pattern entry
    const newPattern: AccessPattern = {
      id: uuidv4(),
      filePath: action.resourcePath,
      timestamp: action.timestamp,
      actionType: action.actionType,
      context: action.context,
      precedingActions: this.getRecentActions(userId, 5)
    };
    
    patterns.push(newPattern);
    
    // Keep only recent patterns (last 1000)
    if (patterns.length > 1000) {
      patterns.splice(0, patterns.length - 1000);
    }
    
    // Update cache recommendations based on new pattern
    await this.updateCacheQueue(userId, action);
  }

  async getCacheHitPrediction(userId: string, filePath: string): Promise<number> {
    const patterns = this.accessPatterns.get(userId) || [];
    const filePatterns = patterns.filter(p => p.filePath === filePath);
    
    if (filePatterns.length === 0) {
      return 0;
    }
    
    const recentAccess = filePatterns[filePatterns.length - 1];
    const timeSinceAccess = differenceInMinutes(new Date(), new Date(recentAccess.timestamp));
    
    // Higher probability if accessed recently
    if (timeSinceAccess < 60) return 0.8;
    if (timeSinceAccess < 240) return 0.6;
    if (timeSinceAccess < 1440) return 0.4;
    
    // Check for recurring patterns
    const recurringScore = this.calculateRecurringScore(filePatterns);
    
    return Math.max(0.1, recurringScore);
  }

  async optimizeCacheSize(userId: string): Promise<void> {
    const stats = this.getCacheStats(userId);
    const queue = this.cacheQueue.get(userId) || [];
    
    if (stats.currentSize > this.maxCacheSize) {
      // Remove least likely to be accessed files
      const sortedQueue = orderBy(queue, 'priority', 'desc');
      const toRemove = sortedQueue.slice(this.maxCacheSize);
      
      for (const entry of toRemove) {
        await this.removeCacheEntry(userId, entry);
      }
    }
  }

  private async predictImmediateNeeds(userId: string): Promise<CacheRecommendation[]> {
    const recommendations: CacheRecommendation[] = [];
    const predictions = await this.behaviorEngine.predictNextActions(userId);
    
    for (const prediction of predictions.slice(0, 10)) {
      if (prediction.confidence > 0.5 && prediction.payload.predictedPath) {
        recommendations.push({
          id: uuidv4(),
          userId,
          filePath: prediction.payload.predictedPath,
          reason: 'immediate_prediction',
          confidence: prediction.confidence,
          priority: prediction.confidence * 100,
          estimatedAccessTime: addMinutes(new Date(), 30), // Expect access within 30 minutes
          size: await this.estimateFileSize(prediction.payload.predictedPath),
          metadata: {
            predictionId: prediction.id,
            reasoning: prediction.payload.reasoning
          }
        });
      }
    }
    
    return recommendations;
  }

  private async predictSequentialAccess(userId: string): Promise<CacheRecommendation[]> {
    const recommendations: CacheRecommendation[] = [];
    const patterns = this.accessPatterns.get(userId) || [];
    
    // Look for sequential access patterns (file A -> file B -> file C)
    const sequentialGroups = this.findSequentialPatterns(patterns);
    
    for (const group of sequentialGroups) {
      if (group.confidence > 0.4) {
        for (const filePath of group.nextFiles) {
          recommendations.push({
            id: uuidv4(),
            userId,
            filePath,
            reason: 'sequential_pattern',
            confidence: group.confidence,
            priority: group.confidence * 80,
            estimatedAccessTime: addMinutes(new Date(), group.estimatedDelay),
            size: await this.estimateFileSize(filePath),
            metadata: {
              patternType: 'sequential',
              triggerFile: group.triggerFile
            }
          });
        }
      }
    }
    
    return recommendations;
  }

  private async predictContextualNeeds(userId: string): Promise<CacheRecommendation[]> {
    const recommendations: CacheRecommendation[] = [];
    const now = new Date();
    const currentHour = now.getHours();
    const currentDay = now.getDay();
    
    const patterns = this.accessPatterns.get(userId) || [];
    const contextualPatterns = patterns.filter(p => 
      p.context?.timeOfDay === currentHour || 
      p.context?.dayOfWeek === currentDay
    );
    
    const pathFrequency = new Map<string, number>();
    
    for (const pattern of contextualPatterns) {
      const count = pathFrequency.get(pattern.filePath) || 0;
      pathFrequency.set(pattern.filePath, count + 1);
    }
    
    for (const [filePath, frequency] of pathFrequency.entries()) {
      if (frequency >= 3) { // Seen at least 3 times in this context
        const confidence = Math.min(frequency / 10, 0.8);
        
        recommendations.push({
          id: uuidv4(),
          userId,
          filePath,
          reason: 'contextual_pattern',
          confidence,
          priority: confidence * 70,
          estimatedAccessTime: addMinutes(new Date(), 60),
          size: await this.estimateFileSize(filePath),
          metadata: {
            patternType: 'contextual',
            context: { hour: currentHour, day: currentDay },
            frequency
          }
        });
      }
    }
    
    return recommendations;
  }

  private async predictSeasonalNeeds(userId: string): Promise<CacheRecommendation[]> {
    const recommendations: CacheRecommendation[] = [];
    const futureNeeds = await this.futureNeedsPredictor.predictFutureNeeds(userId, 'week');
    
    for (const need of futureNeeds.slice(0, 5)) {
      if (need.confidence > 0.5 && need.payload.suggestedFiles) {
        for (const filePath of need.payload.suggestedFiles) {
          recommendations.push({
            id: uuidv4(),
            userId,
            filePath,
            reason: 'seasonal_prediction',
            confidence: need.confidence * 0.8, // Slightly lower confidence for seasonal
            priority: need.confidence * 60,
            estimatedAccessTime: addMinutes(new Date(), 24 * 60), // Within 24 hours
            size: await this.estimateFileSize(filePath),
            metadata: {
              patternType: 'seasonal',
              futureNeedId: need.id,
              category: need.payload.category
            }
          });
        }
      }
    }
    
    return recommendations;
  }

  private rankAndOptimizeCacheRecommendations(
    userId: string,
    recommendations: CacheRecommendation[]
  ): CacheRecommendation[] {
    const stats = this.getCacheStats(userId);
    
    // Remove duplicates
    const uniqueRecommendations = recommendations.reduce((acc, rec) => {
      const existing = acc.find(r => r.filePath === rec.filePath);
      if (!existing || existing.confidence < rec.confidence) {
        return [...acc.filter(r => r.filePath !== rec.filePath), rec];
      }
      return acc;
    }, [] as CacheRecommendation[]);
    
    // Sort by priority (confidence * urgency factor)
    const sorted = orderBy(uniqueRecommendations, [
      'priority',
      'confidence'
    ], ['desc', 'desc']);
    
    // Consider cache size constraints
    const availableSpace = this.maxCacheSize - stats.currentSize;
    let totalSize = 0;
    
    return sorted.filter(rec => {
      totalSize += rec.size;
      return totalSize <= availableSpace * 1024 * 1024; // Convert MB to bytes
    }).slice(0, 50); // Limit to top 50 recommendations
  }

  private findSequentialPatterns(patterns: AccessPattern[]): SequentialGroup[] {
    const groups: SequentialGroup[] = [];
    const sequences = new Map<string, { next: string; delay: number; count: number }[]>();
    
    for (let i = 0; i < patterns.length - 1; i++) {
      const current = patterns[i];
      const next = patterns[i + 1];
      
      const delay = differenceInMinutes(
        new Date(next.timestamp),
        new Date(current.timestamp)
      );
      
      // Only consider sequences with reasonable delays (1-60 minutes)
      if (delay > 0 && delay < 60) {
        const key = current.filePath;
        
        if (!sequences.has(key)) {
          sequences.set(key, []);
        }
        
        const seq = sequences.get(key)!;
        const existing = seq.find(s => s.next === next.filePath);
        
        if (existing) {
          existing.count++;
          existing.delay = (existing.delay + delay) / 2; // Average delay
        } else {
          seq.push({ next: next.filePath, delay, count: 1 });
        }
      }
    }
    
    for (const [triggerFile, nextFiles] of sequences.entries()) {
      const frequentNext = nextFiles.filter(nf => nf.count >= 3);
      
      if (frequentNext.length > 0) {
        groups.push({
          triggerFile,
          nextFiles: frequentNext.map(nf => nf.next),
          confidence: Math.min(frequentNext[0].count / 10, 0.9),
          estimatedDelay: frequentNext[0].delay
        });
      }
    }
    
    return groups;
  }

  private calculateRecurringScore(patterns: AccessPattern[]): number {
    if (patterns.length < 3) return 0;
    
    const intervals = [];
    for (let i = 1; i < patterns.length; i++) {
      const interval = differenceInMinutes(
        new Date(patterns[i].timestamp),
        new Date(patterns[i - 1].timestamp)
      );
      intervals.push(interval);
    }
    
    // Calculate consistency of intervals
    const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    const variance = intervals.reduce((acc, interval) => 
      acc + Math.pow(interval - avgInterval, 2), 0) / intervals.length;
    
    const consistency = 1 / (1 + variance / (avgInterval * avgInterval));
    
    return Math.min(consistency * (patterns.length / 10), 0.9);
  }

  private getCacheStats(userId: string): CacheStats {
    if (!this.cacheStats.has(userId)) {
      this.cacheStats.set(userId, {
        currentSize: 0,
        hits: 0,
        misses: 0,
        totalRequests: 0,
        lastCleanup: new Date()
      });
    }
    return this.cacheStats.get(userId)!;
  }

  private getRecentActions(userId: string, count: number): string[] {
    const patterns = this.accessPatterns.get(userId) || [];
    return patterns.slice(-count).map(p => p.filePath);
  }

  private async updateCacheQueue(userId: string, action: UserAction): Promise<void> {
    if (!this.cacheQueue.has(userId)) {
      this.cacheQueue.set(userId, []);
    }
    
    const queue = this.cacheQueue.get(userId)!;
    
    // Update priority of related files
    for (const entry of queue) {
      if (this.areFilesRelated(entry.filePath, action.resourcePath)) {
        entry.priority += 10;
      }
    }
  }

  private areFilesRelated(path1: string, path2: string): boolean {
    const dir1 = path1.substring(0, path1.lastIndexOf('/'));
    const dir2 = path2.substring(0, path2.lastIndexOf('/'));
    
    return dir1 === dir2 || 
           path1.includes(path2.replace(/\.[^/.]+$/, '')) ||
           path2.includes(path1.replace(/\.[^/.]+$/, ''));
  }

  private async estimateFileSize(filePath: string): Promise<number> {
    // In a real implementation, this would get actual file size
    // For now, estimate based on file extension
    const extension = filePath.split('.').pop()?.toLowerCase() || '';
    
    const sizeMB: Record<string, number> = {
      'txt': 0.1,
      'doc': 0.5,
      'docx': 0.5,
      'pdf': 2,
      'jpg': 1.5,
      'jpeg': 1.5,
      'png': 2,
      'mp4': 50,
      'avi': 100,
      'zip': 10
    };
    
    return sizeMB[extension] || 1; // Default 1MB
  }

  private async removeCacheEntry(userId: string, entry: CacheEntry): Promise<void> {
    const queue = this.cacheQueue.get(userId);
    if (queue) {
      const index = queue.findIndex(e => e.id === entry.id);
      if (index >= 0) {
        queue.splice(index, 1);
      }
    }
    
    const stats = this.getCacheStats(userId);
    stats.currentSize -= entry.size;
  }
}

interface CacheRecommendation {
  id: string;
  userId: string;
  filePath: string;
  reason: 'immediate_prediction' | 'sequential_pattern' | 'contextual_pattern' | 'seasonal_prediction';
  confidence: number;
  priority: number;
  estimatedAccessTime: Date;
  size: number; // in MB
  metadata: Record<string, any>;
}

interface CacheEntry {
  id: string;
  filePath: string;
  cachedAt: Date;
  lastAccessed: Date;
  accessCount: number;
  size: number;
  priority: number;
}

interface AccessPattern {
  id: string;
  filePath: string;
  timestamp: Date;
  actionType: string;
  context?: any;
  precedingActions: string[];
}

interface CacheStats {
  currentSize: number;
  hits: number;
  misses: number;
  totalRequests: number;
  lastCleanup: Date;
}

interface SequentialGroup {
  triggerFile: string;
  nextFiles: string[];
  confidence: number;
  estimatedDelay: number;
}