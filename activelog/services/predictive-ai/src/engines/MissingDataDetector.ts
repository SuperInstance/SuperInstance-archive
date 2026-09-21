import { UserAction, AnomalyAlert } from '../types';
import { BehaviorPredictionEngine } from '../core/BehaviorPredictionEngine';
import { TimelineReconstructionEngine } from './TimelineReconstructionEngine';
import { v4 as uuidv4 } from 'uuid';
import { 
  differenceInMinutes, 
  differenceInHours, 
  differenceInDays,
  startOfDay,
  endOfDay,
  isWithinInterval,
  addDays
} from 'date-fns';
import { groupBy, orderBy } from 'lodash';

export class MissingDataDetector {
  private behaviorEngine: BehaviorPredictionEngine;
  private timelineEngine: TimelineReconstructionEngine;
  private expectedPatterns: Map<string, ExpectedPattern[]> = new Map();
  private missingDataAlerts: Map<string, MissingDataAlert[]> = new Map();

  constructor(
    behaviorEngine: BehaviorPredictionEngine,
    timelineEngine: TimelineReconstructionEngine
  ) {
    this.behaviorEngine = behaviorEngine;
    this.timelineEngine = timelineEngine;
  }

  async detectMissingData(userId: string, actions: UserAction[]): Promise<MissingDataAlert[]> {
    const alerts: MissingDataAlert[] = [];
    
    // Detect missing data patterns
    alerts.push(...await this.detectMissingHabits(userId, actions));
    alerts.push(...await this.detectMissingDocumentation(userId, actions));
    alerts.push(...await this.detectMissingBackups(userId, actions));
    alerts.push(...await this.detectMissingTags(userId, actions));
    alerts.push(...await this.detectMissingPhotographs(userId, actions));
    alerts.push(...await this.detectMissingReceipts(userId, actions));
    alerts.push(...await this.detectIncompleteProjects(userId, actions));
    alerts.push(...await this.detectMissingFollowUps(userId, actions));
    
    // Store alerts
    this.missingDataAlerts.set(userId, alerts);
    
    return orderBy(alerts, ['severity', 'confidence'], ['desc', 'desc']);
  }

  async predictMissingData(userId: string, context?: any): Promise<PredictedMissing[]> {
    const predictions: PredictedMissing[] = [];
    const now = new Date();
    
    // Predict based on typical user patterns
    predictions.push(...await this.predictMissingReceiptPhotos(userId, now));
    predictions.push(...await this.predictMissingMeetingNotes(userId, now));
    predictions.push(...await this.predictMissingProjectDocs(userId, now));
    predictions.push(...await this.predictMissingBackupActions(userId, now));
    predictions.push(...await this.predictMissingTagging(userId, now));
    
    return orderBy(predictions, 'probability', 'desc');
  }

  async learnExpectedPatterns(userId: string, actions: UserAction[]): Promise<void> {
    if (!this.expectedPatterns.has(userId)) {
      this.expectedPatterns.set(userId, []);
    }
    
    const patterns = this.expectedPatterns.get(userId)!;
    
    // Learn receipt photography patterns
    const receiptPattern = this.extractReceiptPhotographyPattern(actions);
    if (receiptPattern) {
      this.updateOrAddPattern(patterns, receiptPattern);
    }
    
    // Learn documentation patterns
    const docPattern = this.extractDocumentationPattern(actions);
    if (docPattern) {
      this.updateOrAddPattern(patterns, docPattern);
    }
    
    // Learn tagging patterns
    const tagPattern = this.extractTaggingPattern(actions);
    if (tagPattern) {
      this.updateOrAddPattern(patterns, tagPattern);
    }
    
    // Learn backup patterns
    const backupPattern = this.extractBackupPattern(actions);
    if (backupPattern) {
      this.updateOrAddPattern(patterns, backupPattern);
    }
  }

  async getMissingDataSummary(userId: string): Promise<MissingDataSummary> {
    const alerts = this.missingDataAlerts.get(userId) || [];
    
    return {
      totalAlerts: alerts.length,
      highPriorityAlerts: alerts.filter(a => a.severity === 'high').length,
      categories: this.categorizeMissingData(alerts),
      suggestions: this.generateSuggestions(alerts),
      completionScore: this.calculateCompletionScore(userId, alerts)
    };
  }

  private async detectMissingHabits(userId: string, actions: UserAction[]): Promise<MissingDataAlert[]> {
    const alerts: MissingDataAlert[] = [];
    const expectedPatterns = this.expectedPatterns.get(userId) || [];
    
    for (const pattern of expectedPatterns) {
      if (pattern.type === 'habit') {
        const recentActions = actions.filter(a => 
          differenceInDays(new Date(), new Date(a.timestamp)) <= 7
        );
        
        const matchingActions = recentActions.filter(a => 
          this.matchesPattern(a, pattern)
        );
        
        if (matchingActions.length < pattern.expectedFrequency * 0.5) {
          alerts.push({
            id: uuidv4(),
            userId,
            type: 'missing_habit',
            severity: this.calculateHabitSeverity(pattern, matchingActions.length),
            confidence: pattern.confidence,
            title: `Missing ${pattern.description}`,
            description: `You typically ${pattern.description} but haven't recently`,
            suggestedActions: [
              `Resume ${pattern.description}`,
              'Set reminder for regular activity',
              'Review if this habit is still relevant'
            ],
            affectedAreas: [pattern.category],
            detectedAt: new Date(),
            expectedAction: pattern.expectedAction,
            lastOccurrence: this.findLastOccurrence(actions, pattern)
          });
        }
      }
    }
    
    return alerts;
  }

  private async detectMissingDocumentation(userId: string, actions: UserAction[]): Promise<MissingDataAlert[]> {
    const alerts: MissingDataAlert[] = [];
    
    // Find project actions without corresponding documentation
    const projectActions = actions.filter(a => 
      a.resourcePath.toLowerCase().includes('project') ||
      a.actionType === 'folder_create'
    );
    
    const projectGroups = groupBy(projectActions, a => 
      this.extractProjectPath(a.resourcePath)
    );
    
    for (const [projectPath, projectActionsList] of Object.entries(projectGroups)) {
      if (projectActionsList.length >= 5) { // Significant project activity
        const hasDocumentation = projectActionsList.some(a => 
          a.resourcePath.toLowerCase().includes('readme') ||
          a.resourcePath.toLowerCase().includes('doc') ||
          a.resourcePath.toLowerCase().includes('note')
        );
        
        if (!hasDocumentation) {
          alerts.push({
            id: uuidv4(),
            userId,
            type: 'missing_documentation',
            severity: 'medium',
            confidence: 0.7,
            title: 'Missing project documentation',
            description: `Project ${projectPath} has significant activity but no documentation`,
            suggestedActions: [
              'Create README file',
              'Document project goals and setup',
              'Add notes about key decisions'
            ],
            affectedAreas: ['documentation', 'project_management'],
            detectedAt: new Date(),
            expectedAction: 'Create documentation files',
            context: { projectPath, activityCount: projectActionsList.length }
          });
        }
      }
    }
    
    return alerts;
  }

  private async detectMissingBackups(userId: string, actions: UserAction[]): Promise<MissingDataAlert[]> {
    const alerts: MissingDataAlert[] = [];
    
    // Check for important files without recent backups
    const importantFileActions = actions.filter(a => 
      a.actionType === 'file_access' &&
      (a.resourcePath.toLowerCase().includes('important') ||
       a.resourcePath.toLowerCase().includes('critical') ||
       a.metadata?.tags?.includes('important'))
    );
    
    const backupActions = actions.filter(a => 
      a.resourcePath.toLowerCase().includes('backup') ||
      a.actionType === 'move' && a.metadata?.destination?.includes('backup')
    );
    
    if (importantFileActions.length > 0 && backupActions.length === 0) {
      alerts.push({
        id: uuidv4(),
        userId,
        type: 'missing_backup',
        severity: 'high',
        confidence: 0.8,
        title: 'Missing backups for important files',
        description: `${importantFileActions.length} important files accessed without recent backup activity`,
        suggestedActions: [
          'Create backup of important files',
          'Set up automated backup system',
          'Review backup strategy'
        ],
        affectedAreas: ['data_safety', 'backup'],
        detectedAt: new Date(),
        expectedAction: 'Create backups',
        context: { importantFileCount: importantFileActions.length }
      });
    }
    
    return alerts;
  }

  private async detectMissingTags(userId: string, actions: UserAction[]): Promise<MissingDataAlert[]> {
    const alerts: MissingDataAlert[] = [];
    
    // Find files that should be tagged but aren't
    const fileActions = actions.filter(a => a.actionType === 'file_access');
    const tagActions = actions.filter(a => a.actionType === 'tag_add');
    
    const taggedFiles = new Set(tagActions.map(a => a.resourcePath));
    const untaggedImportantFiles = fileActions.filter(a => 
      !taggedFiles.has(a.resourcePath) &&
      (a.resourcePath.toLowerCase().includes('important') ||
       a.resourcePath.toLowerCase().includes('project') ||
       differenceInDays(new Date(), new Date(a.timestamp)) <= 30) // Recent files
    );
    
    if (untaggedImportantFiles.length > 10) {
      alerts.push({
        id: uuidv4(),
        userId,
        type: 'missing_tags',
        severity: 'low',
        confidence: 0.6,
        title: 'Many files lack organization tags',
        description: `${untaggedImportantFiles.length} important or recent files could benefit from tagging`,
        suggestedActions: [
          'Add descriptive tags to recent files',
          'Create tagging system',
          'Review and tag important documents'
        ],
        affectedAreas: ['organization', 'searchability'],
        detectedAt: new Date(),
        expectedAction: 'Add tags to files',
        context: { untaggedFileCount: untaggedImportantFiles.length }
      });
    }
    
    return alerts;
  }

  private async detectMissingPhotographs(userId: string, actions: UserAction[]): Promise<MissingDataAlert[]> {
    const alerts: MissingDataAlert[] = [];
    
    // Check if user typically photographs receipts but hasn't recently
    const receiptPattern = this.expectedPatterns.get(userId)?.find(p => 
      p.type === 'receipt_photography'
    );
    
    if (receiptPattern) {
      const recentReceiptPhotos = actions.filter(a => 
        a.resourcePath.toLowerCase().includes('receipt') &&
        a.resourcePath.toLowerCase().includes('photo') &&
        differenceInDays(new Date(), new Date(a.timestamp)) <= 14
      );
      
      const recentExpenseActivity = actions.filter(a => 
        a.resourcePath.toLowerCase().includes('expense') ||
        a.resourcePath.toLowerCase().includes('receipt') ||
        a.metadata?.tags?.includes('expense')
      );
      
      if (recentExpenseActivity.length > 0 && recentReceiptPhotos.length === 0) {
        alerts.push({
          id: uuidv4(),
          userId,
          type: 'missing_photographs',
          severity: 'medium',
          confidence: receiptPattern.confidence,
          title: 'Missing receipt photographs',
          description: 'You typically photograph receipts but haven\'t recently despite expense activity',
          suggestedActions: [
            'Photograph recent receipts',
            'Set reminder to photograph receipts immediately',
            'Review expense documentation process'
          ],
          affectedAreas: ['expense_tracking', 'documentation'],
          detectedAt: new Date(),
          expectedAction: 'Photograph receipts',
          context: { 
            expenseActivityCount: recentExpenseActivity.length,
            expectedFrequency: receiptPattern.expectedFrequency
          }
        });
      }
    }
    
    return alerts;
  }

  private async detectMissingReceipts(userId: string, actions: UserAction[]): Promise<MissingDataAlert[]> {
    const alerts: MissingDataAlert[] = [];
    
    // Detect if user is in tax season but missing receipt organization
    const now = new Date();
    const isTaxSeason = now.getMonth() >= 0 && now.getMonth() <= 3; // Jan-Apr
    
    if (isTaxSeason) {
      const receiptActions = actions.filter(a => 
        a.resourcePath.toLowerCase().includes('receipt') ||
        a.resourcePath.toLowerCase().includes('tax')
      );
      
      const businessExpenseActions = actions.filter(a => 
        a.resourcePath.toLowerCase().includes('business') ||
        a.resourcePath.toLowerCase().includes('expense') ||
        a.metadata?.tags?.includes('deductible')
      );
      
      if (businessExpenseActions.length > 0 && receiptActions.length === 0) {
        alerts.push({
          id: uuidv4(),
          userId,
          type: 'missing_receipts',
          severity: 'high',
          confidence: 0.9,
          title: 'Missing receipt collection for tax season',
          description: 'Tax season activity detected but no receipt organization',
          suggestedActions: [
            'Gather business receipts for tax deductions',
            'Organize receipts by category',
            'Scan physical receipts',
            'Create tax documents folder'
          ],
          affectedAreas: ['tax_preparation', 'financial_records'],
          detectedAt: new Date(),
          expectedAction: 'Organize receipts for taxes',
          context: { 
            businessExpenseCount: businessExpenseActions.length,
            taxSeason: true
          }
        });
      }
    }
    
    return alerts;
  }

  private async detectIncompleteProjects(userId: string, actions: UserAction[]): Promise<MissingDataAlert[]> {
    const alerts: MissingDataAlert[] = [];
    
    const projectGroups = groupBy(
      actions.filter(a => a.resourcePath.toLowerCase().includes('project')),
      a => this.extractProjectPath(a.resourcePath)
    );
    
    for (const [projectPath, projectActionsList] of Object.entries(projectGroups)) {
      const lastActivity = Math.max(...projectActionsList.map(a => 
        new Date(a.timestamp).getTime()
      ));
      
      const daysSinceActivity = differenceInDays(new Date(), new Date(lastActivity));
      
      // Project with recent activity but no completion markers
      if (daysSinceActivity <= 30 && daysSinceActivity >= 7) {
        const hasCompletionMarkers = projectActionsList.some(a => 
          a.resourcePath.toLowerCase().includes('complete') ||
          a.resourcePath.toLowerCase().includes('final') ||
          a.resourcePath.toLowerCase().includes('done') ||
          a.actionType === 'move' && a.metadata?.destination?.includes('archive')
        );
        
        if (!hasCompletionMarkers && projectActionsList.length >= 10) {
          alerts.push({
            id: uuidv4(),
            userId,
            type: 'incomplete_project',
            severity: 'medium',
            confidence: 0.6,
            title: `Project may be incomplete: ${this.extractProjectName(projectPath)}`,
            description: `Project has ${daysSinceActivity} days of inactivity without completion markers`,
            suggestedActions: [
              'Review project status',
              'Complete remaining tasks',
              'Archive if finished',
              'Document current progress'
            ],
            affectedAreas: ['project_management', 'completion'],
            detectedAt: new Date(),
            expectedAction: 'Complete or archive project',
            context: { 
              projectPath,
              daysSinceActivity,
              activityCount: projectActionsList.length
            }
          });
        }
      }
    }
    
    return alerts;
  }

  private async detectMissingFollowUps(userId: string, actions: UserAction[]): Promise<MissingDataAlert[]> {
    const alerts: MissingDataAlert[] = [];
    
    // Find sharing actions without follow-up
    const shareActions = actions.filter(a => a.actionType === 'share');
    
    for (const shareAction of shareActions) {
      const daysSinceShare = differenceInDays(new Date(), new Date(shareAction.timestamp));
      
      if (daysSinceShare >= 3 && daysSinceShare <= 14) {
        // Look for follow-up actions on the same resource
        const followUpActions = actions.filter(a => 
          a.resourcePath === shareAction.resourcePath &&
          new Date(a.timestamp) > new Date(shareAction.timestamp)
        );
        
        if (followUpActions.length === 0) {
          alerts.push({
            id: uuidv4(),
            userId,
            type: 'missing_followup',
            severity: 'low',
            confidence: 0.5,
            title: 'Missing follow-up on shared item',
            description: `Shared ${shareAction.resourcePath} ${daysSinceShare} days ago without follow-up`,
            suggestedActions: [
              'Check if feedback was received',
              'Follow up with collaborators',
              'Update shared document based on feedback'
            ],
            affectedAreas: ['collaboration', 'communication'],
            detectedAt: new Date(),
            expectedAction: 'Follow up on shared item',
            context: { 
              sharedResource: shareAction.resourcePath,
              daysSinceShare,
              collaborators: shareAction.metadata?.collaborators
            }
          });
        }
      }
    }
    
    return alerts;
  }

  private async predictMissingReceiptPhotos(userId: string, currentTime: Date): Promise<PredictedMissing[]> {
    const predictions: PredictedMissing[] = [];
    const receiptPattern = this.expectedPatterns.get(userId)?.find(p => 
      p.type === 'receipt_photography'
    );
    
    if (receiptPattern && receiptPattern.confidence > 0.6) {
      // Predict based on typical shopping days/times
      const isShoppingTime = this.isTypicalShoppingTime(currentTime, receiptPattern);
      
      if (isShoppingTime) {
        predictions.push({
          id: uuidv4(),
          type: 'receipt_photo',
          description: 'You may need to photograph receipts soon',
          probability: receiptPattern.confidence * 0.7,
          timeFrame: 'within 2 hours',
          suggestedAction: 'Prepare to photograph any receipts from shopping',
          context: { pattern: receiptPattern.description }
        });
      }
    }
    
    return predictions;
  }

  private async predictMissingMeetingNotes(userId: string, currentTime: Date): Promise<PredictedMissing[]> {
    const predictions: PredictedMissing[] = [];
    
    // Check if it's typical meeting time
    const hour = currentTime.getHours();
    const isBusinessHours = hour >= 9 && hour <= 17;
    const isMeetingTime = [10, 14, 16].includes(hour); // Common meeting times
    
    if (isBusinessHours && isMeetingTime) {
      predictions.push({
        id: uuidv4(),
        type: 'meeting_notes',
        description: 'Meeting notes may be needed',
        probability: 0.4,
        timeFrame: 'within 1 hour',
        suggestedAction: 'Prepare note-taking system for potential meetings',
        context: { time: 'typical meeting hours' }
      });
    }
    
    return predictions;
  }

  private async predictMissingProjectDocs(userId: string, currentTime: Date): Promise<PredictedMissing[]> {
    const predictions: PredictedMissing[] = [];
    
    // Predict documentation needs for Friday afternoon (end of week)
    const dayOfWeek = currentTime.getDay();
    const hour = currentTime.getHours();
    
    if (dayOfWeek === 5 && hour >= 14) { // Friday afternoon
      predictions.push({
        id: uuidv4(),
        type: 'project_documentation',
        description: 'End-of-week project documentation may be needed',
        probability: 0.6,
        timeFrame: 'before end of day',
        suggestedAction: 'Review and document week\'s project progress',
        context: { time: 'end of week' }
      });
    }
    
    return predictions;
  }

  private async predictMissingBackupActions(userId: string, currentTime: Date): Promise<PredictedMissing[]> {
    const predictions: PredictedMissing[] = [];
    
    // Predict backup needs on Sunday evenings
    const dayOfWeek = currentTime.getDay();
    const hour = currentTime.getHours();
    
    if (dayOfWeek === 0 && hour >= 18) { // Sunday evening
      predictions.push({
        id: uuidv4(),
        type: 'backup_action',
        description: 'Weekly backup may be due',
        probability: 0.7,
        timeFrame: 'tonight',
        suggestedAction: 'Perform weekly backup of important files',
        context: { time: 'weekly backup time' }
      });
    }
    
    return predictions;
  }

  private async predictMissingTagging(userId: string, currentTime: Date): Promise<PredictedMissing[]> {
    const predictions: PredictedMissing[] = [];
    
    // Predict tagging needs during organization time (Sunday afternoon)
    const dayOfWeek = currentTime.getDay();
    const hour = currentTime.getHours();
    
    if (dayOfWeek === 0 && hour >= 14 && hour <= 17) { // Sunday afternoon
      predictions.push({
        id: uuidv4(),
        type: 'file_tagging',
        description: 'File organization and tagging may be needed',
        probability: 0.5,
        timeFrame: 'this afternoon',
        suggestedAction: 'Review and tag recently accessed files',
        context: { time: 'organization time' }
      });
    }
    
    return predictions;
  }

  // Helper methods
  private extractReceiptPhotographyPattern(actions: UserAction[]): ExpectedPattern | null {
    const receiptPhotos = actions.filter(a => 
      a.resourcePath.toLowerCase().includes('receipt') &&
      (a.resourcePath.toLowerCase().includes('photo') || a.actionType === 'file_access')
    );
    
    if (receiptPhotos.length >= 5) {
      return {
        id: uuidv4(),
        type: 'receipt_photography',
        description: 'photograph receipts after shopping',
        category: 'expense_tracking',
        expectedFrequency: receiptPhotos.length / 4, // Per week estimate
        confidence: Math.min(receiptPhotos.length / 20, 0.9),
        expectedAction: 'Photograph receipt',
        triggers: ['shopping', 'expense'],
        lastUpdate: new Date()
      };
    }
    
    return null;
  }

  private extractDocumentationPattern(actions: UserAction[]): ExpectedPattern | null {
    const docActions = actions.filter(a => 
      a.resourcePath.toLowerCase().includes('readme') ||
      a.resourcePath.toLowerCase().includes('doc') ||
      a.resourcePath.toLowerCase().includes('note')
    );
    
    if (docActions.length >= 3) {
      return {
        id: uuidv4(),
        type: 'documentation',
        description: 'create documentation for projects',
        category: 'project_management',
        expectedFrequency: docActions.length / 8, // Per week estimate
        confidence: Math.min(docActions.length / 10, 0.8),
        expectedAction: 'Create documentation',
        triggers: ['project_start', 'significant_progress'],
        lastUpdate: new Date()
      };
    }
    
    return null;
  }

  private extractTaggingPattern(actions: UserAction[]): ExpectedPattern | null {
    const tagActions = actions.filter(a => a.actionType === 'tag_add');
    
    if (tagActions.length >= 5) {
      return {
        id: uuidv4(),
        type: 'tagging',
        description: 'add tags to organize files',
        category: 'organization',
        expectedFrequency: tagActions.length / 4,
        confidence: Math.min(tagActions.length / 15, 0.8),
        expectedAction: 'Add tags to files',
        triggers: ['file_creation', 'file_access'],
        lastUpdate: new Date()
      };
    }
    
    return null;
  }

  private extractBackupPattern(actions: UserAction[]): ExpectedPattern | null {
    const backupActions = actions.filter(a => 
      a.resourcePath.toLowerCase().includes('backup') ||
      (a.actionType === 'move' && a.metadata?.destination?.includes('backup'))
    );
    
    if (backupActions.length >= 3) {
      return {
        id: uuidv4(),
        type: 'backup',
        description: 'create backups of important files',
        category: 'data_safety',
        expectedFrequency: backupActions.length / 12, // Per week estimate
        confidence: Math.min(backupActions.length / 8, 0.9),
        expectedAction: 'Create backup',
        triggers: ['important_file_change', 'weekly_routine'],
        lastUpdate: new Date()
      };
    }
    
    return null;
  }

  private updateOrAddPattern(patterns: ExpectedPattern[], newPattern: ExpectedPattern): void {
    const existingIndex = patterns.findIndex(p => 
      p.type === newPattern.type && p.category === newPattern.category
    );
    
    if (existingIndex >= 0) {
      // Update existing pattern
      const existing = patterns[existingIndex];
      existing.expectedFrequency = (existing.expectedFrequency + newPattern.expectedFrequency) / 2;
      existing.confidence = Math.max(existing.confidence, newPattern.confidence);
      existing.lastUpdate = new Date();
    } else {
      // Add new pattern
      patterns.push(newPattern);
    }
  }

  private matchesPattern(action: UserAction, pattern: ExpectedPattern): boolean {
    if (pattern.type === 'receipt_photography') {
      return action.resourcePath.toLowerCase().includes('receipt');
    }
    
    if (pattern.type === 'documentation') {
      return action.resourcePath.toLowerCase().includes('doc') ||
             action.resourcePath.toLowerCase().includes('readme') ||
             action.resourcePath.toLowerCase().includes('note');
    }
    
    if (pattern.type === 'tagging') {
      return action.actionType === 'tag_add';
    }
    
    if (pattern.type === 'backup') {
      return action.resourcePath.toLowerCase().includes('backup');
    }
    
    return false;
  }

  private calculateHabitSeverity(pattern: ExpectedPattern, actualFrequency: number): 'low' | 'medium' | 'high' {
    const ratio = actualFrequency / pattern.expectedFrequency;
    
    if (ratio < 0.2) return 'high';
    if (ratio < 0.5) return 'medium';
    return 'low';
  }

  private findLastOccurrence(actions: UserAction[], pattern: ExpectedPattern): Date | null {
    const matchingActions = actions.filter(a => this.matchesPattern(a, pattern));
    
    if (matchingActions.length === 0) return null;
    
    return new Date(Math.max(...matchingActions.map(a => new Date(a.timestamp).getTime())));
  }

  private extractProjectPath(resourcePath: string): string {
    const parts = resourcePath.split('/');
    const projectIndex = parts.findIndex(part => 
      part.toLowerCase().includes('project')
    );
    
    if (projectIndex >= 0 && projectIndex < parts.length - 1) {
      return parts.slice(0, projectIndex + 2).join('/');
    }
    
    return parts.slice(0, 2).join('/');
  }

  private extractProjectName(projectPath: string): string {
    return projectPath.split('/').pop() || 'Unknown Project';
  }

  private isTypicalShoppingTime(currentTime: Date, pattern: ExpectedPattern): boolean {
    const hour = currentTime.getHours();
    const dayOfWeek = currentTime.getDay();
    
    // Weekend mornings and evenings are typical shopping times
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
    const isShoppingHour = (hour >= 9 && hour <= 12) || (hour >= 17 && hour <= 20);
    
    return isWeekend && isShoppingHour;
  }

  private categorizeMissingData(alerts: MissingDataAlert[]): Record<string, number> {
    const categories: Record<string, number> = {};
    
    for (const alert of alerts) {
      for (const area of alert.affectedAreas) {
        categories[area] = (categories[area] || 0) + 1;
      }
    }
    
    return categories;
  }

  private generateSuggestions(alerts: MissingDataAlert[]): string[] {
    const suggestions = new Set<string>();
    
    for (const alert of alerts) {
      for (const action of alert.suggestedActions) {
        suggestions.add(action);
      }
    }
    
    return Array.from(suggestions).slice(0, 10);
  }

  private calculateCompletionScore(userId: string, alerts: MissingDataAlert[]): number {
    const patterns = this.expectedPatterns.get(userId) || [];
    
    if (patterns.length === 0) return 1.0;
    
    const missedPatterns = alerts.filter(a => a.type === 'missing_habit').length;
    return Math.max(0, 1 - (missedPatterns / patterns.length));
  }
}

// Interface definitions
interface MissingDataAlert {
  id: string;
  userId: string;
  type: 'missing_habit' | 'missing_documentation' | 'missing_backup' | 'missing_tags' | 
        'missing_photographs' | 'missing_receipts' | 'incomplete_project' | 'missing_followup';
  severity: 'low' | 'medium' | 'high';
  confidence: number;
  title: string;
  description: string;
  suggestedActions: string[];
  affectedAreas: string[];
  detectedAt: Date;
  expectedAction: string;
  lastOccurrence?: Date | null;
  context?: Record<string, any>;
}

interface PredictedMissing {
  id: string;
  type: string;
  description: string;
  probability: number;
  timeFrame: string;
  suggestedAction: string;
  context: Record<string, any>;
}

interface ExpectedPattern {
  id: string;
  type: 'habit' | 'receipt_photography' | 'documentation' | 'tagging' | 'backup';
  description: string;
  category: string;
  expectedFrequency: number; // Per week
  confidence: number;
  expectedAction: string;
  triggers: string[];
  lastUpdate: Date;
}

interface MissingDataSummary {
  totalAlerts: number;
  highPriorityAlerts: number;
  categories: Record<string, number>;
  suggestions: string[];
  completionScore: number;
}