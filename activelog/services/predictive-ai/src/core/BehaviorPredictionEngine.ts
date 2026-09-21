import { UserAction, UserPattern, Prediction } from '../types';
import { PatternExtractor } from './PatternExtractor';
import { MLPredictor } from './MLPredictor';
import { ContextAnalyzer } from './ContextAnalyzer';

export class BehaviorPredictionEngine {
  private patternExtractor: PatternExtractor;
  private mlPredictor: MLPredictor;
  private contextAnalyzer: ContextAnalyzer;
  private userPatterns: Map<string, UserPattern[]> = new Map();
  private recentActions: Map<string, UserAction[]> = new Map();

  constructor() {
    this.patternExtractor = new PatternExtractor();
    this.mlPredictor = new MLPredictor();
    this.contextAnalyzer = new ContextAnalyzer();
  }

  async initialize(): Promise<void> {
    await this.mlPredictor.initialize();
  }

  async learnFromAction(action: UserAction): Promise<void> {
    const userId = action.userId;
    
    if (!this.recentActions.has(userId)) {
      this.recentActions.set(userId, []);
    }
    
    const userActions = this.recentActions.get(userId)!;
    userActions.push(action);
    
    if (userActions.length > 1000) {
      userActions.shift();
    }
    
    await this.extractPatterns(userId, userActions);
    await this.mlPredictor.trainOnAction(action);
  }

  async predictNextActions(userId: string, context?: any): Promise<Prediction[]> {
    const currentContext = await this.contextAnalyzer.getCurrentContext(context);
    const userPatterns = this.userPatterns.get(userId) || [];
    const recentActions = this.recentActions.get(userId) || [];
    
    const predictions: Prediction[] = [];
    
    for (const pattern of userPatterns) {
      if (this.shouldTriggerPattern(pattern, currentContext, recentActions)) {
        const prediction = await this.generatePredictionFromPattern(
          userId,
          pattern,
          currentContext
        );
        if (prediction) {
          predictions.push(prediction);
        }
      }
    }
    
    const mlPredictions = await this.mlPredictor.predict(userId, currentContext, recentActions);
    predictions.push(...mlPredictions);
    
    return predictions
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 10);
  }

  async getFolderSuggestions(userId: string, currentPath?: string): Promise<string[]> {
    const predictions = await this.predictNextActions(userId, { currentPath });
    
    return predictions
      .filter(p => p.predictionType === 'folder_suggestion')
      .map(p => p.payload.suggestedPath)
      .slice(0, 5);
  }

  async predictFutureNeeds(userId: string, timeHorizon: 'day' | 'week' | 'month' | 'year'): Promise<Prediction[]> {
    const currentDate = new Date();
    const context = {
      timeHorizon,
      currentDate,
      currentMonth: currentDate.getMonth(),
      currentDayOfWeek: currentDate.getDay()
    };
    
    const temporalPatterns = (this.userPatterns.get(userId) || [])
      .filter(p => p.patternType === 'temporal');
    
    const predictions: Prediction[] = [];
    
    for (const pattern of temporalPatterns) {
      if (this.isTemporalPatternRelevant(pattern, context)) {
        const prediction = await this.generateTemporalPrediction(userId, pattern, context);
        if (prediction) {
          predictions.push(prediction);
        }
      }
    }
    
    return predictions.sort((a, b) => b.confidence - a.confidence);
  }

  private async extractPatterns(userId: string, actions: UserAction[]): Promise<void> {
    const newPatterns = await this.patternExtractor.extractPatterns(actions);
    
    if (!this.userPatterns.has(userId)) {
      this.userPatterns.set(userId, []);
    }
    
    const existingPatterns = this.userPatterns.get(userId)!;
    
    for (const newPattern of newPatterns) {
      const existingIndex = existingPatterns.findIndex(
        p => this.patternsAreSimilar(p, newPattern)
      );
      
      if (existingIndex >= 0) {
        existingPatterns[existingIndex] = this.mergePatterns(
          existingPatterns[existingIndex],
          newPattern
        );
      } else {
        existingPatterns.push(newPattern);
      }
    }
    
    this.userPatterns.set(userId, existingPatterns.slice(-100));
  }

  private shouldTriggerPattern(
    pattern: UserPattern,
    context: any,
    recentActions: UserAction[]
  ): boolean {
    if (pattern.confidence < 0.3) return false;
    
    if (pattern.triggers) {
      const recentActionTypes = recentActions
        .slice(-5)
        .map(a => a.actionType);
      
      return pattern.triggers.some(trigger => 
        recentActionTypes.includes(trigger as any)
      );
    }
    
    if (pattern.patternType === 'temporal') {
      return this.isTemporalPatternActive(pattern, context);
    }
    
    return true;
  }

  private async generatePredictionFromPattern(
    userId: string,
    pattern: UserPattern,
    context: any
  ): Promise<Prediction | null> {
    const now = new Date();
    
    return {
      id: `pred_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      userId,
      predictionType: 'file_access',
      confidence: pattern.confidence,
      timestamp: now,
      expiresAt: new Date(now.getTime() + 24 * 60 * 60 * 1000), // 24 hours
      payload: {
        predictedAction: pattern.pattern,
        reasoning: `Based on ${pattern.patternType} pattern with ${(pattern.confidence * 100).toFixed(1)}% confidence`
      },
      context
    };
  }

  private isTemporalPatternRelevant(pattern: UserPattern, context: any): boolean {
    const patternData = pattern.pattern;
    
    if (context.timeHorizon === 'month' && patternData.month !== undefined) {
      return Math.abs(patternData.month - context.currentMonth) <= 1;
    }
    
    if (context.timeHorizon === 'week' && patternData.dayOfWeek !== undefined) {
      return true;
    }
    
    return false;
  }

  private async generateTemporalPrediction(
    userId: string,
    pattern: UserPattern,
    context: any
  ): Promise<Prediction | null> {
    const now = new Date();
    const patternData = pattern.pattern;
    
    let predictionText = '';
    if (patternData.month === 2 && patternData.actionType === 'file_access') {
      predictionText = 'You typically access tax documents in March';
    } else if (patternData.dayOfWeek === 1 && patternData.actionType === 'folder_create') {
      predictionText = 'You often organize files on Mondays';
    } else {
      predictionText = `Temporal pattern suggests ${patternData.actionType} activity`;
    }
    
    return {
      id: `future_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      userId,
      predictionType: 'future_need',
      confidence: pattern.confidence * 0.8, // Slightly lower confidence for future predictions
      timestamp: now,
      expiresAt: new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000), // 7 days
      payload: {
        prediction: predictionText,
        suggestedActions: [`Prepare for ${patternData.actionType}`, 'Review related files'],
        timeFrame: context.timeHorizon
      },
      context
    };
  }

  private isTemporalPatternActive(pattern: UserPattern, context: any): boolean {
    const now = new Date();
    const patternData = pattern.pattern;
    
    if (patternData.timeOfDay !== undefined) {
      const currentHour = now.getHours();
      return Math.abs(currentHour - patternData.timeOfDay) <= 2;
    }
    
    if (patternData.dayOfWeek !== undefined) {
      return now.getDay() === patternData.dayOfWeek;
    }
    
    return true;
  }

  private patternsAreSimilar(pattern1: UserPattern, pattern2: UserPattern): boolean {
    return pattern1.patternType === pattern2.patternType &&
           JSON.stringify(pattern1.pattern) === JSON.stringify(pattern2.pattern);
  }

  private mergePatterns(existing: UserPattern, newPattern: UserPattern): UserPattern {
    return {
      ...existing,
      confidence: (existing.confidence + newPattern.confidence) / 2,
      frequency: existing.frequency + 1,
      lastSeen: new Date()
    };
  }
}