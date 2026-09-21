import { UserAction, UserPattern, Prediction, TemporalCluster } from '../types';
import { BehaviorPredictionEngine } from '../core/BehaviorPredictionEngine';
import { v4 as uuidv4 } from 'uuid';
import { addDays, addWeeks, addMonths, isAfter, isBefore, differenceInDays } from 'date-fns';
import { groupBy, orderBy } from 'lodash';

export class FutureNeedsPredictor {
  private behaviorEngine: BehaviorPredictionEngine;
  private seasonalPatterns: Map<string, SeasonalPattern[]> = new Map();
  private lifecycleEvents: Map<string, LifecycleEvent[]> = new Map();

  constructor(behaviorEngine: BehaviorPredictionEngine) {
    this.behaviorEngine = behaviorEngine;
  }

  async predictFutureNeeds(
    userId: string,
    timeHorizon: 'day' | 'week' | 'month' | 'quarter' | 'year'
  ): Promise<Prediction[]> {
    const predictions: Prediction[] = [];
    const now = new Date();

    predictions.push(...await this.predictSeasonalNeeds(userId, timeHorizon, now));
    predictions.push(...await this.predictRecurringNeeds(userId, timeHorizon, now));
    predictions.push(...await this.predictLifecycleNeeds(userId, timeHorizon, now));
    predictions.push(...await this.predictContextualNeeds(userId, timeHorizon, now));
    predictions.push(...await this.predictTrendBasedNeeds(userId, timeHorizon, now));

    return predictions
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 20);
  }

  async predictTaxSeasonNeeds(userId: string): Promise<Prediction[]> {
    const now = new Date();
    const taxSeason = now.getMonth() >= 0 && now.getMonth() <= 3; // Jan-Apr
    
    if (!taxSeason && now.getMonth() !== 11) { // Not tax season and not December prep
      return [];
    }

    const predictions: Prediction[] = [];
    const confidence = taxSeason ? 0.9 : 0.6;
    const baseId = uuidv4();

    const taxPredictions = [
      {
        type: 'document_access',
        description: 'You will likely need tax documents (W-2s, 1099s, receipts)',
        suggestedActions: [
          'Gather W-2 and 1099 forms',
          'Collect receipts for deductions',
          'Review last year\'s tax return',
          'Update tax software'
        ],
        urgency: taxSeason ? 'high' : 'medium'
      },
      {
        type: 'folder_organization',
        description: 'Tax document organization will be needed',
        suggestedActions: [
          'Create taxes-2024 folder',
          'Organize receipts by category',
          'Scan physical documents',
          'Backup tax files'
        ],
        urgency: 'medium'
      }
    ];

    for (const pred of taxPredictions) {
      predictions.push({
        id: `${baseId}_${pred.type}`,
        userId,
        predictionType: 'future_need',
        confidence,
        timestamp: now,
        expiresAt: addMonths(now, 4),
        payload: {
          category: 'tax_season',
          ...pred
        },
        context: { season: 'tax', timeHorizon: 'month' }
      });
    }

    return predictions;
  }

  async predictHolidayNeeds(userId: string): Promise<Prediction[]> {
    const now = new Date();
    const isHolidaySeason = now.getMonth() >= 10; // Nov-Dec
    
    if (!isHolidaySeason && now.getMonth() !== 9) { // Not holiday season and not October prep
      return [];
    }

    const predictions: Prediction[] = [];
    const baseId = uuidv4();

    const holidayPredictions = [
      {
        description: 'Holiday photo organization will be needed',
        suggestedActions: [
          'Create holiday-2024 photo folder',
          'Plan family photo sessions',
          'Backup holiday photos',
          'Create photo albums'
        ]
      },
      {
        description: 'Gift planning and tracking',
        suggestedActions: [
          'Create gift-ideas folder',
          'Track gift purchases',
          'Store receipts for returns',
          'Plan holiday budget'
        ]
      }
    ];

    for (const pred of holidayPredictions) {
      predictions.push({
        id: `${baseId}_holiday`,
        userId,
        predictionType: 'future_need',
        confidence: 0.7,
        timestamp: now,
        expiresAt: addMonths(now, 2),
        payload: {
          category: 'holidays',
          ...pred
        },
        context: { season: 'holiday', timeHorizon: 'month' }
      });
    }

    return predictions;
  }

  async predictBirthdayNeeds(userId: string, upcomingBirthdays: Date[]): Promise<Prediction[]> {
    const predictions: Prediction[] = [];
    const now = new Date();

    for (const birthday of upcomingBirthdays) {
      const daysUntilBirthday = differenceInDays(birthday, now);
      
      if (daysUntilBirthday > 0 && daysUntilBirthday <= 30) {
        predictions.push({
          id: uuidv4(),
          userId,
          predictionType: 'future_need',
          confidence: 0.8,
          timestamp: now,
          expiresAt: birthday,
          payload: {
            category: 'birthday',
            description: `Birthday preparation needed in ${daysUntilBirthday} days`,
            suggestedActions: [
              'Plan birthday celebration',
              'Purchase gift',
              'Send invitations',
              'Organize photos from past birthdays'
            ],
            daysUntil: daysUntilBirthday
          },
          context: { event: 'birthday', timeHorizon: 'week' }
        });
      }
    }

    return predictions;
  }

  learnFromSeasonalActivity(userId: string, actions: UserAction[]): void {
    const seasonalGroups = this.groupActionsBySeason(actions);
    
    for (const [season, seasonActions] of seasonalGroups.entries()) {
      this.updateSeasonalPatterns(userId, season, seasonActions);
    }
  }

  private async predictSeasonalNeeds(
    userId: string,
    timeHorizon: string,
    now: Date
  ): Promise<Prediction[]> {
    const predictions: Prediction[] = [];
    const currentSeason = this.getSeason(now.getMonth());
    const nextSeason = this.getNextSeason(currentSeason);
    
    const seasonalPatterns = this.seasonalPatterns.get(userId) || [];
    
    for (const pattern of seasonalPatterns) {
      if (pattern.season === nextSeason || 
          (pattern.season === currentSeason && pattern.isRecurring)) {
        
        const prediction = this.createSeasonalPrediction(userId, pattern, now);
        if (prediction) {
          predictions.push(prediction);
        }
      }
    }

    // Add hardcoded seasonal predictions
    predictions.push(...await this.predictTaxSeasonNeeds(userId));
    predictions.push(...await this.predictHolidayNeeds(userId));

    return predictions;
  }

  private async predictRecurringNeeds(
    userId: string,
    timeHorizon: string,
    now: Date
  ): Promise<Prediction[]> {
    const predictions: Prediction[] = [];
    
    // Weekly recurring needs
    if (timeHorizon === 'week' || timeHorizon === 'day') {
      if (now.getDay() === 0) { // Sunday
        predictions.push({
          id: uuidv4(),
          userId,
          predictionType: 'future_need',
          confidence: 0.6,
          timestamp: now,
          expiresAt: addDays(now, 7),
          payload: {
            category: 'weekly_organization',
            description: 'Weekly file organization typically happens on Sundays',
            suggestedActions: [
              'Clean up desktop',
              'Organize downloads folder',
              'Archive completed projects',
              'Review and tag recent files'
            ]
          },
          context: { pattern: 'weekly', timeHorizon }
        });
      }
    }

    // Monthly recurring needs
    if (timeHorizon === 'month' && now.getDate() === 1) {
      predictions.push({
        id: uuidv4(),
        userId,
        predictionType: 'future_need',
        confidence: 0.7,
        timestamp: now,
        expiresAt: addMonths(now, 1),
        payload: {
          category: 'monthly_review',
          description: 'Monthly file backup and organization',
          suggestedActions: [
            'Backup important files',
            'Review storage usage',
            'Clean up temporary files',
            'Update folder structures'
          ]
        },
        context: { pattern: 'monthly', timeHorizon }
      });
    }

    return predictions;
  }

  private async predictLifecycleNeeds(
    userId: string,
    timeHorizon: string,
    now: Date
  ): Promise<Prediction[]> {
    const predictions: Prediction[] = [];
    const lifecycleEvents = this.lifecycleEvents.get(userId) || [];

    for (const event of lifecycleEvents) {
      if (this.isEventUpcoming(event, now, timeHorizon)) {
        const prediction = this.createLifecyclePrediction(userId, event, now);
        if (prediction) {
          predictions.push(prediction);
        }
      }
    }

    return predictions;
  }

  private async predictContextualNeeds(
    userId: string,
    timeHorizon: string,
    now: Date
  ): Promise<Prediction[]> {
    const predictions: Prediction[] = [];
    
    // Back to school season
    if (now.getMonth() === 7 || now.getMonth() === 8) { // Aug-Sep
      predictions.push({
        id: uuidv4(),
        userId,
        predictionType: 'future_need',
        confidence: 0.5,
        timestamp: now,
        expiresAt: addMonths(now, 2),
        payload: {
          category: 'back_to_school',
          description: 'Back to school organization may be needed',
          suggestedActions: [
            'Organize school documents',
            'Create academic year folders',
            'Backup summer projects',
            'Prepare study materials'
          ]
        },
        context: { season: 'back_to_school', timeHorizon }
      });
    }

    // Year-end activities
    if (now.getMonth() === 11) { // December
      predictions.push({
        id: uuidv4(),
        userId,
        predictionType: 'future_need',
        confidence: 0.8,
        timestamp: now,
        expiresAt: addMonths(now, 1),
        payload: {
          category: 'year_end',
          description: 'Year-end file organization and backup',
          suggestedActions: [
            'Archive 2024 files',
            'Backup important documents',
            'Organize tax documents for next season',
            'Clean up old files'
          ]
        },
        context: { season: 'year_end', timeHorizon }
      });
    }

    return predictions;
  }

  private async predictTrendBasedNeeds(
    userId: string,
    timeHorizon: string,
    now: Date
  ): Promise<Prediction[]> {
    const predictions: Prediction[] = [];
    
    // Storage cleanup prediction
    predictions.push({
      id: uuidv4(),
      userId,
      predictionType: 'future_need',
      confidence: 0.4,
      timestamp: now,
      expiresAt: addWeeks(now, 2),
      payload: {
        category: 'storage_management',
        description: 'Storage cleanup may be needed based on typical usage patterns',
        suggestedActions: [
          'Review large files',
          'Clean temporary folders',
          'Archive old projects',
          'Optimize storage usage'
        ]
      },
      context: { trend: 'storage_growth', timeHorizon }
    });

    return predictions;
  }

  private getSeason(month: number): string {
    if (month >= 2 && month <= 4) return 'spring';
    if (month >= 5 && month <= 7) return 'summer';
    if (month >= 8 && month <= 10) return 'fall';
    return 'winter';
  }

  private getNextSeason(currentSeason: string): string {
    const seasons = ['winter', 'spring', 'summer', 'fall'];
    const currentIndex = seasons.indexOf(currentSeason);
    return seasons[(currentIndex + 1) % seasons.length];
  }

  private groupActionsBySeason(actions: UserAction[]): Map<string, UserAction[]> {
    const groups = new Map<string, UserAction[]>();
    
    for (const action of actions) {
      const month = new Date(action.timestamp).getMonth();
      const season = this.getSeason(month);
      
      if (!groups.has(season)) {
        groups.set(season, []);
      }
      groups.get(season)!.push(action);
    }
    
    return groups;
  }

  private updateSeasonalPatterns(userId: string, season: string, actions: UserAction[]): void {
    if (!this.seasonalPatterns.has(userId)) {
      this.seasonalPatterns.set(userId, []);
    }

    const patterns = this.seasonalPatterns.get(userId)!;
    const existingPattern = patterns.find(p => p.season === season);

    if (existingPattern) {
      existingPattern.actions.push(...actions);
      existingPattern.frequency++;
      existingPattern.lastSeen = new Date();
    } else {
      patterns.push({
        id: uuidv4(),
        season,
        actions: [...actions],
        frequency: 1,
        confidence: 0.5,
        lastSeen: new Date(),
        isRecurring: false
      });
    }

    // Mark as recurring if seen multiple times
    const pattern = patterns.find(p => p.season === season)!;
    if (pattern.frequency >= 2) {
      pattern.isRecurring = true;
      pattern.confidence = Math.min(pattern.frequency * 0.2, 0.9);
    }
  }

  private createSeasonalPrediction(
    userId: string,
    pattern: SeasonalPattern,
    now: Date
  ): Prediction | null {
    return {
      id: uuidv4(),
      userId,
      predictionType: 'future_need',
      confidence: pattern.confidence,
      timestamp: now,
      expiresAt: addMonths(now, 3),
      payload: {
        category: 'seasonal',
        season: pattern.season,
        description: `Seasonal activity pattern for ${pattern.season}`,
        suggestedActions: this.generateSeasonalActions(pattern.season),
        frequency: pattern.frequency
      },
      context: { season: pattern.season, timeHorizon: 'season' }
    };
  }

  private createLifecyclePrediction(
    userId: string,
    event: LifecycleEvent,
    now: Date
  ): Prediction | null {
    return {
      id: uuidv4(),
      userId,
      predictionType: 'future_need',
      confidence: event.confidence,
      timestamp: now,
      expiresAt: event.expectedDate,
      payload: {
        category: 'lifecycle',
        event: event.type,
        description: `Upcoming lifecycle event: ${event.type}`,
        suggestedActions: event.suggestedActions,
        daysUntil: differenceInDays(event.expectedDate, now)
      },
      context: { event: event.type, timeHorizon: 'lifecycle' }
    };
  }

  private isEventUpcoming(event: LifecycleEvent, now: Date, timeHorizon: string): boolean {
    const daysDifference = differenceInDays(event.expectedDate, now);
    
    switch (timeHorizon) {
      case 'day': return daysDifference >= 0 && daysDifference <= 1;
      case 'week': return daysDifference >= 0 && daysDifference <= 7;
      case 'month': return daysDifference >= 0 && daysDifference <= 30;
      case 'quarter': return daysDifference >= 0 && daysDifference <= 90;
      case 'year': return daysDifference >= 0 && daysDifference <= 365;
      default: return false;
    }
  }

  private generateSeasonalActions(season: string): string[] {
    const seasonalActions: Record<string, string[]> = {
      'winter': ['Organize holiday photos', 'Prepare tax documents', 'Plan year-end backup'],
      'spring': ['Spring cleaning of files', 'Organize outdoor activity photos', 'Review financial documents'],
      'summer': ['Organize vacation photos', 'Backup travel documents', 'Plan summer project folders'],
      'fall': ['Back to school organization', 'Archive summer activities', 'Prepare holiday planning']
    };

    return seasonalActions[season] || ['Seasonal file organization'];
  }
}

interface SeasonalPattern {
  id: string;
  season: string;
  actions: UserAction[];
  frequency: number;
  confidence: number;
  lastSeen: Date;
  isRecurring: boolean;
}

interface LifecycleEvent {
  id: string;
  type: 'birthday' | 'anniversary' | 'graduation' | 'job_change' | 'move' | 'vacation';
  expectedDate: Date;
  confidence: number;
  suggestedActions: string[];
}