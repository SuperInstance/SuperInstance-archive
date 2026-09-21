import { EventEmitter } from 'events';
import { AgeGroup } from '../age-detection/age-detector';

export interface ComplexityConfiguration {
  userId: string;
  ageGroup: AgeGroup;
  globalComplexity: number; // 0-1 master complexity level
  featureComplexities: Map<string, number>; // feature-specific overrides
  userPreferences: ComplexityPreferences;
  autoAdjustment: AutoAdjustmentSettings;
  contextualAdaptation: ContextualSettings;
}

export interface ComplexityPreferences {
  allowComplexityIncrease: boolean;
  maxComplexityJump: number; // Maximum single adjustment (0-1)
  learningMode: boolean; // Gradually increase complexity over time
  expertMode: boolean; // Override age-based restrictions
  accessibilityMode: boolean; // Force simpler interfaces
  parentalOverride: boolean; // Parent can force complexity limits
}

export interface AutoAdjustmentSettings {
  enabled: boolean;
  basedOnSuccess: boolean; // Increase complexity on successful interactions
  basedOnTime: boolean; // Increase complexity over time
  basedOnErrors: boolean; // Decrease complexity on errors
  adjustmentSensitivity: number; // 0-1 how quickly to adjust
  cooldownPeriod: number; // Minutes between adjustments
}

export interface ContextualSettings {
  taskBasedAdjustment: boolean; // Adjust based on current task
  timeOfDayAdjustment: boolean; // Simpler interface during tired times
  stressModeAdjustment: boolean; // Simplify when user seems stressed
  focusModeAdjustment: boolean; // Adapt for focused work sessions
}

export interface FeatureDefinition {
  id: string;
  name: string;
  category: FeatureCategory;
  description: string;
  complexityLevels: ComplexityLevel[];
  dependencies: string[]; // Other features this depends on
  prerequisites: FeaturePrerequisites;
  cognitiveLoad: number; // 0-1 mental effort required
  learningCurve: number; // 0-1 how hard to learn
  safetyLevel: SafetyLevel; // Content safety classification
}

export enum FeatureCategory {
  CORE = 'core', // Essential features
  PRODUCTIVITY = 'productivity',
  CREATIVE = 'creative',
  COMMUNICATION = 'communication',
  ENTERTAINMENT = 'entertainment',
  EDUCATIONAL = 'educational',
  ADVANCED = 'advanced',
  EXPERIMENTAL = 'experimental'
}

export interface ComplexityLevel {
  level: number; // 0-10
  name: string; // "Beginner", "Intermediate", "Advanced", etc.
  description: string;
  uiElements: UIComplexity;
  functionality: FunctionalityComplexity;
  content: ContentComplexity;
  interactions: InteractionComplexity;
  requirements: LevelRequirements;
}

export interface UIComplexity {
  controlCount: number; // Number of visible controls
  menuDepth: number; // Maximum menu nesting
  optionsVisible: number; // Number of options shown simultaneously
  shortcuts: boolean; // Show keyboard shortcuts
  customization: boolean; // Allow UI customization
  advancedPanels: boolean; // Show advanced configuration panels
}

export interface FunctionalityComplexity {
  autoMode: boolean; // Automatic vs manual control
  batchOperations: boolean; // Allow bulk actions
  conditionalLogic: boolean; // If/then functionality
  scripting: boolean; // User scripting/automation
  integrations: boolean; // Third-party integrations
  apiAccess: boolean; // Direct API access
}

export interface ContentComplexity {
  detailLevel: 'basic' | 'standard' | 'detailed' | 'comprehensive';
  technicalTerms: boolean; // Use technical vocabulary
  assumptions: boolean; // Assume prior knowledge
  contextualHelp: 'none' | 'tooltips' | 'guided' | 'comprehensive';
  examples: boolean; // Show usage examples
  warnings: boolean; // Show advanced warnings
}

export interface InteractionComplexity {
  gestureSupport: boolean; // Advanced gestures
  multiStep: boolean; // Multi-step workflows
  dragDrop: boolean; // Drag and drop operations
  contextMenus: boolean; // Right-click menus
  modalDialogs: boolean; // Complex dialog boxes
  realTimeUpdates: boolean; // Live data updates
}

export interface LevelRequirements {
  minimumAge: number;
  parentalConsent: boolean;
  completedTutorial: boolean;
  prerequisiteFeatures: string[];
  usageTime: number; // Minimum hours of usage
  successRate: number; // Minimum success rate with previous level
}

export enum SafetyLevel {
  SAFE = 'safe', // Always safe for all ages
  SUPERVISED = 'supervised', // Safe with supervision
  RESTRICTED = 'restricted', // Age restrictions apply
  ADULT_ONLY = 'adult_only' // Adults only
}

export interface FeaturePrerequisites {
  minimumAge: number;
  parentalApproval: boolean;
  completedFeatures: string[];
  skillLevel: number; // 0-1 required skill level
  safetyTraining: boolean;
}

export interface ComplexityAdjustment {
  featureId: string;
  previousLevel: number;
  newLevel: number;
  reason: AdjustmentReason;
  timestamp: Date;
  automatic: boolean;
  confidence: number; // 0-1 confidence in this adjustment
}

export enum AdjustmentReason {
  USER_REQUEST = 'user_request',
  SUCCESS_RATE = 'success_rate',
  ERROR_RATE = 'error_rate',
  TIME_BASED = 'time_based',
  SKILL_PROGRESSION = 'skill_progression',
  SAFETY_CONCERN = 'safety_concern',
  PARENTAL_OVERRIDE = 'parental_override',
  CONTEXT_CHANGE = 'context_change'
}

export interface FeatureAvailability {
  featureId: string;
  available: boolean;
  currentLevel: number;
  maxAllowedLevel: number;
  reason?: string;
  unlockConditions?: string[];
  estimatedUnlockTime?: Date;
}

export class ComplexityManager extends EventEmitter {
  private configurations: Map<string, ComplexityConfiguration> = new Map();
  private featureLibrary: Map<string, FeatureDefinition> = new Map();
  private adjustmentHistory: Map<string, ComplexityAdjustment[]> = new Map();
  private userMetrics: Map<string, UserComplexityMetrics> = new Map();

  constructor() {
    super();
    this.initializeFeatureLibrary();
    this.setupAutoAdjustment();
  }

  public createConfiguration(
    userId: string,
    ageGroup: AgeGroup,
    preferences?: Partial<ComplexityPreferences>
  ): ComplexityConfiguration {
    const config: ComplexityConfiguration = {
      userId,
      ageGroup,
      globalComplexity: this.getDefaultComplexity(ageGroup),
      featureComplexities: new Map(),
      userPreferences: {
        allowComplexityIncrease: ageGroup !== AgeGroup.TODDLER && ageGroup !== AgeGroup.PRESCHOOL,
        maxComplexityJump: 0.2,
        learningMode: ageGroup === AgeGroup.EARLY_ELEMENTARY || ageGroup === AgeGroup.LATE_ELEMENTARY,
        expertMode: false,
        accessibilityMode: false,
        parentalOverride: this.requiresParentalConsent(ageGroup),
        ...preferences
      },
      autoAdjustment: {
        enabled: true,
        basedOnSuccess: true,
        basedOnTime: true,
        basedOnErrors: true,
        adjustmentSensitivity: 0.1,
        cooldownPeriod: 30
      },
      contextualAdaptation: {
        taskBasedAdjustment: true,
        timeOfDayAdjustment: true,
        stressModeAdjustment: true,
        focusModeAdjustment: false
      }
    };

    this.configurations.set(userId, config);
    this.userMetrics.set(userId, new UserComplexityMetrics());
    this.emit('configurationCreated', { userId, config });

    return config;
  }

  public adjustGlobalComplexity(userId: string, newLevel: number, reason: AdjustmentReason): boolean {
    const config = this.configurations.get(userId);
    if (!config) return false;

    const clampedLevel = Math.max(0, Math.min(1, newLevel));
    
    // Check if adjustment is allowed
    if (!this.canAdjustComplexity(userId, clampedLevel, reason)) {
      this.emit('adjustmentDenied', { userId, requestedLevel: clampedLevel, reason });
      return false;
    }

    const previousLevel = config.globalComplexity;
    config.globalComplexity = clampedLevel;

    // Update feature-specific complexities proportionally
    for (const [featureId, currentLevel] of config.featureComplexities) {
      const proportion = currentLevel / previousLevel;
      config.featureComplexities.set(featureId, clampedLevel * proportion);
    }

    this.recordAdjustment(userId, 'global', previousLevel, clampedLevel, reason, false);
    this.configurations.set(userId, config);
    
    this.emit('complexityAdjusted', {
      userId,
      type: 'global',
      previousLevel,
      newLevel: clampedLevel,
      reason
    });

    return true;
  }

  public adjustFeatureComplexity(
    userId: string,
    featureId: string,
    newLevel: number,
    reason: AdjustmentReason
  ): boolean {
    const config = this.configurations.get(userId);
    const feature = this.featureLibrary.get(featureId);
    
    if (!config || !feature) return false;

    const clampedLevel = Math.max(0, Math.min(1, newLevel));
    
    // Check if adjustment is allowed
    if (!this.canAdjustFeatureComplexity(userId, featureId, clampedLevel, reason)) {
      return false;
    }

    const previousLevel = config.featureComplexities.get(featureId) || config.globalComplexity;
    config.featureComplexities.set(featureId, clampedLevel);

    this.recordAdjustment(userId, featureId, previousLevel, clampedLevel, reason, false);
    this.configurations.set(userId, config);

    this.emit('featureComplexityAdjusted', {
      userId,
      featureId,
      previousLevel,
      newLevel: clampedLevel,
      reason
    });

    return true;
  }

  public getFeatureComplexity(userId: string, featureId: string): number {
    const config = this.configurations.get(userId);
    if (!config) return 0.5;

    return config.featureComplexities.get(featureId) || config.globalComplexity;
  }

  public getAvailableFeatures(userId: string): FeatureAvailability[] {
    const config = this.configurations.get(userId);
    if (!config) return [];

    const availability: FeatureAvailability[] = [];

    for (const [featureId, feature] of this.featureLibrary) {
      const currentComplexity = this.getFeatureComplexity(userId, featureId);
      const maxAllowed = this.getMaxAllowedComplexity(userId, featureId);
      const canUse = this.canUseFeature(userId, featureId, currentComplexity);

      availability.push({
        featureId,
        available: canUse,
        currentLevel: Math.floor(currentComplexity * 10),
        maxAllowedLevel: Math.floor(maxAllowed * 10),
        reason: canUse ? undefined : this.getUnavailabilityReason(userId, featureId),
        unlockConditions: canUse ? undefined : this.getUnlockConditions(userId, featureId),
        estimatedUnlockTime: this.estimateUnlockTime(userId, featureId)
      });
    }

    return availability;
  }

  public getComplexityLevel(userId: string, featureId: string): ComplexityLevel | null {
    const feature = this.featureLibrary.get(featureId);
    if (!feature) return null;

    const complexity = this.getFeatureComplexity(userId, featureId);
    const levelIndex = Math.floor(complexity * (feature.complexityLevels.length - 1));
    
    return feature.complexityLevels[levelIndex] || null;
  }

  public suggestComplexityAdjustment(userId: string): ComplexityAdjustment[] {
    const metrics = this.userMetrics.get(userId);
    const config = this.configurations.get(userId);
    
    if (!metrics || !config) return [];

    const suggestions: ComplexityAdjustment[] = [];

    // Analyze success rates
    for (const [featureId, successRate] of metrics.successRates) {
      const currentComplexity = this.getFeatureComplexity(userId, featureId);
      
      if (successRate > 0.9 && currentComplexity < 0.9) {
        // High success rate - suggest increase
        suggestions.push({
          featureId,
          previousLevel: currentComplexity,
          newLevel: Math.min(1, currentComplexity + 0.1),
          reason: AdjustmentReason.SUCCESS_RATE,
          timestamp: new Date(),
          automatic: true,
          confidence: (successRate - 0.9) * 10
        });
      } else if (successRate < 0.6 && currentComplexity > 0.1) {
        // Low success rate - suggest decrease
        suggestions.push({
          featureId,
          previousLevel: currentComplexity,
          newLevel: Math.max(0.1, currentComplexity - 0.2),
          reason: AdjustmentReason.ERROR_RATE,
          timestamp: new Date(),
          automatic: true,
          confidence: (0.6 - successRate) * 5
        });
      }
    }

    return suggestions.sort((a, b) => b.confidence - a.confidence);
  }

  public recordInteraction(
    userId: string,
    featureId: string,
    success: boolean,
    duration: number,
    errorCount: number = 0
  ): void {
    const metrics = this.userMetrics.get(userId);
    if (!metrics) return;

    metrics.recordInteraction(featureId, success, duration, errorCount);
    
    // Check if auto-adjustment should trigger
    if (this.shouldTriggerAutoAdjustment(userId, featureId)) {
      this.performAutoAdjustment(userId, featureId);
    }
  }

  private initializeFeatureLibrary(): void {
    // Text Editor Feature
    this.featureLibrary.set('text-editor', {
      id: 'text-editor',
      name: 'Text Editor',
      category: FeatureCategory.CORE,
      description: 'Basic text editing functionality',
      complexityLevels: [
        {
          level: 0,
          name: 'Simple',
          description: 'Basic text input with large fonts',
          uiElements: {
            controlCount: 2, // Just type and clear
            menuDepth: 0,
            optionsVisible: 2,
            shortcuts: false,
            customization: false,
            advancedPanels: false
          },
          functionality: {
            autoMode: true,
            batchOperations: false,
            conditionalLogic: false,
            scripting: false,
            integrations: false,
            apiAccess: false
          },
          content: {
            detailLevel: 'basic',
            technicalTerms: false,
            assumptions: false,
            contextualHelp: 'comprehensive',
            examples: true,
            warnings: false
          },
          interactions: {
            gestureSupport: false,
            multiStep: false,
            dragDrop: false,
            contextMenus: false,
            modalDialogs: false,
            realTimeUpdates: false
          },
          requirements: {
            minimumAge: 4,
            parentalConsent: false,
            completedTutorial: false,
            prerequisiteFeatures: [],
            usageTime: 0,
            successRate: 0
          }
        },
        {
          level: 5,
          name: 'Standard',
          description: 'Full text editor with formatting',
          uiElements: {
            controlCount: 12,
            menuDepth: 2,
            optionsVisible: 8,
            shortcuts: true,
            customization: true,
            advancedPanels: false
          },
          functionality: {
            autoMode: false,
            batchOperations: true,
            conditionalLogic: false,
            scripting: false,
            integrations: true,
            apiAccess: false
          },
          content: {
            detailLevel: 'standard',
            technicalTerms: true,
            assumptions: true,
            contextualHelp: 'tooltips',
            examples: false,
            warnings: true
          },
          interactions: {
            gestureSupport: true,
            multiStep: true,
            dragDrop: true,
            contextMenus: true,
            modalDialogs: true,
            realTimeUpdates: true
          },
          requirements: {
            minimumAge: 12,
            parentalConsent: false,
            completedTutorial: true,
            prerequisiteFeatures: [],
            usageTime: 10,
            successRate: 0.7
          }
        }
      ],
      dependencies: [],
      prerequisites: {
        minimumAge: 4,
        parentalApproval: false,
        completedFeatures: [],
        skillLevel: 0,
        safetyTraining: false
      },
      cognitiveLoad: 0.3,
      learningCurve: 0.2,
      safetyLevel: SafetyLevel.SAFE
    });

    // Add more features
    this.addMoreFeatures();
  }

  private addMoreFeatures(): void {
    const features = [
      {
        id: 'web-browser',
        name: 'Web Browser',
        category: FeatureCategory.CORE,
        cognitiveLoad: 0.6,
        learningCurve: 0.4,
        safetyLevel: SafetyLevel.SUPERVISED,
        minimumAge: 8,
        parentalApproval: true
      },
      {
        id: 'file-manager',
        name: 'File Manager',
        category: FeatureCategory.PRODUCTIVITY,
        cognitiveLoad: 0.7,
        learningCurve: 0.6,
        safetyLevel: SafetyLevel.SAFE,
        minimumAge: 10,
        parentalApproval: false
      },
      {
        id: 'code-editor',
        name: 'Code Editor',
        category: FeatureCategory.ADVANCED,
        cognitiveLoad: 0.9,
        learningCurve: 0.8,
        safetyLevel: SafetyLevel.SAFE,
        minimumAge: 12,
        parentalApproval: false
      }
    ];

    // Simplified feature creation for brevity
    features.forEach(featureData => {
      this.featureLibrary.set(featureData.id, {
        id: featureData.id,
        name: featureData.name,
        category: featureData.category,
        description: `${featureData.name} with age-appropriate complexity levels`,
        complexityLevels: this.generateBasicComplexityLevels(featureData),
        dependencies: [],
        prerequisites: {
          minimumAge: featureData.minimumAge,
          parentalApproval: featureData.parentalApproval,
          completedFeatures: [],
          skillLevel: featureData.cognitiveLoad * 0.5,
          safetyTraining: featureData.safetyLevel !== SafetyLevel.SAFE
        },
        cognitiveLoad: featureData.cognitiveLoad,
        learningCurve: featureData.learningCurve,
        safetyLevel: featureData.safetyLevel
      });
    });
  }

  private generateBasicComplexityLevels(featureData: any): ComplexityLevel[] {
    return [
      {
        level: 0,
        name: 'Beginner',
        description: `Basic ${featureData.name.toLowerCase()} functionality`,
        uiElements: {
          controlCount: 3,
          menuDepth: 1,
          optionsVisible: 3,
          shortcuts: false,
          customization: false,
          advancedPanels: false
        },
        functionality: {
          autoMode: true,
          batchOperations: false,
          conditionalLogic: false,
          scripting: false,
          integrations: false,
          apiAccess: false
        },
        content: {
          detailLevel: 'basic',
          technicalTerms: false,
          assumptions: false,
          contextualHelp: 'comprehensive',
          examples: true,
          warnings: false
        },
        interactions: {
          gestureSupport: false,
          multiStep: false,
          dragDrop: false,
          contextMenus: false,
          modalDialogs: false,
          realTimeUpdates: false
        },
        requirements: {
          minimumAge: featureData.minimumAge,
          parentalConsent: featureData.parentalApproval,
          completedTutorial: true,
          prerequisiteFeatures: [],
          usageTime: 0,
          successRate: 0
        }
      },
      {
        level: 10,
        name: 'Expert',
        description: `Advanced ${featureData.name.toLowerCase()} with full capabilities`,
        uiElements: {
          controlCount: 20,
          menuDepth: 4,
          optionsVisible: 15,
          shortcuts: true,
          customization: true,
          advancedPanels: true
        },
        functionality: {
          autoMode: false,
          batchOperations: true,
          conditionalLogic: true,
          scripting: true,
          integrations: true,
          apiAccess: true
        },
        content: {
          detailLevel: 'comprehensive',
          technicalTerms: true,
          assumptions: true,
          contextualHelp: 'none',
          examples: false,
          warnings: true
        },
        interactions: {
          gestureSupport: true,
          multiStep: true,
          dragDrop: true,
          contextMenus: true,
          modalDialogs: true,
          realTimeUpdates: true
        },
        requirements: {
          minimumAge: Math.max(16, featureData.minimumAge + 4),
          parentalConsent: false,
          completedTutorial: true,
          prerequisiteFeatures: [],
          usageTime: 100,
          successRate: 0.8
        }
      }
    ];
  }

  private getDefaultComplexity(ageGroup: AgeGroup): number {
    switch (ageGroup) {
      case AgeGroup.TODDLER: return 0.05;
      case AgeGroup.PRESCHOOL: return 0.1;
      case AgeGroup.EARLY_ELEMENTARY: return 0.2;
      case AgeGroup.LATE_ELEMENTARY: return 0.35;
      case AgeGroup.MIDDLE_SCHOOL: return 0.5;
      case AgeGroup.HIGH_SCHOOL: return 0.7;
      case AgeGroup.YOUNG_ADULT: return 0.8;
      case AgeGroup.ADULT: return 0.9;
      case AgeGroup.SENIOR: return 0.6;
      default: return 0.5;
    }
  }

  private requiresParentalConsent(ageGroup: AgeGroup): boolean {
    return [
      AgeGroup.TODDLER,
      AgeGroup.PRESCHOOL,
      AgeGroup.EARLY_ELEMENTARY,
      AgeGroup.LATE_ELEMENTARY
    ].includes(ageGroup);
  }

  private canAdjustComplexity(userId: string, newLevel: number, reason: AdjustmentReason): boolean {
    const config = this.configurations.get(userId);
    if (!config) return false;

    // Check max jump size
    const currentLevel = config.globalComplexity;
    const jump = Math.abs(newLevel - currentLevel);
    if (jump > config.userPreferences.maxComplexityJump) return false;

    // Check if increases are allowed
    if (newLevel > currentLevel && !config.userPreferences.allowComplexityIncrease) return false;

    // Check parental override
    if (config.userPreferences.parentalOverride && reason !== AdjustmentReason.PARENTAL_OVERRIDE) {
      return false;
    }

    return true;
  }

  private canAdjustFeatureComplexity(
    userId: string,
    featureId: string,
    newLevel: number,
    reason: AdjustmentReason
  ): boolean {
    const config = this.configurations.get(userId);
    const feature = this.featureLibrary.get(featureId);
    
    if (!config || !feature) return false;

    const maxAllowed = this.getMaxAllowedComplexity(userId, featureId);
    return newLevel <= maxAllowed;
  }

  private getMaxAllowedComplexity(userId: string, featureId: string): number {
    const config = this.configurations.get(userId);
    const feature = this.featureLibrary.get(featureId);
    
    if (!config || !feature) return 0;

    // Base on age restrictions
    let maxComplexity = this.getDefaultComplexity(config.ageGroup);

    // Apply feature-specific restrictions
    if (feature.prerequisites.minimumAge > this.getAgeFromGroup(config.ageGroup)) {
      maxComplexity *= 0.5;
    }

    // Apply safety restrictions
    if (feature.safetyLevel === SafetyLevel.ADULT_ONLY && config.ageGroup !== AgeGroup.ADULT) {
      maxComplexity = 0;
    }

    return Math.min(1, maxComplexity);
  }

  private canUseFeature(userId: string, featureId: string, complexityLevel: number): boolean {
    const config = this.configurations.get(userId);
    const feature = this.featureLibrary.get(featureId);
    
    if (!config || !feature) return false;

    const userAge = this.getAgeFromGroup(config.ageGroup);
    const level = this.getComplexityLevel(userId, featureId);
    
    if (!level) return false;

    // Check age requirements
    if (userAge < level.requirements.minimumAge) return false;

    // Check parental consent
    if (level.requirements.parentalConsent && !config.userPreferences.parentalOverride) return false;

    // Check prerequisites
    const metrics = this.userMetrics.get(userId);
    if (metrics) {
      if (level.requirements.usageTime > metrics.totalUsageTime) return false;
      if (level.requirements.successRate > (metrics.overallSuccessRate || 0)) return false;
    }

    return true;
  }

  private getUnavailabilityReason(userId: string, featureId: string): string {
    const config = this.configurations.get(userId);
    const feature = this.featureLibrary.get(featureId);
    
    if (!config || !feature) return 'Feature not found';

    const userAge = this.getAgeFromGroup(config.ageGroup);
    const level = this.getComplexityLevel(userId, featureId);
    
    if (!level) return 'No appropriate complexity level';
    
    if (userAge < level.requirements.minimumAge) {
      return `Requires minimum age of ${level.requirements.minimumAge}`;
    }

    if (level.requirements.parentalConsent && !config.userPreferences.parentalOverride) {
      return 'Requires parental consent';
    }

    return 'Prerequisites not met';
  }

  private getUnlockConditions(userId: string, featureId: string): string[] {
    const conditions: string[] = [];
    const config = this.configurations.get(userId);
    const feature = this.featureLibrary.get(featureId);
    const level = this.getComplexityLevel(userId, featureId);
    
    if (!config || !feature || !level) return conditions;

    const userAge = this.getAgeFromGroup(config.ageGroup);
    const metrics = this.userMetrics.get(userId);

    if (userAge < level.requirements.minimumAge) {
      conditions.push(`Reach age ${level.requirements.minimumAge}`);
    }

    if (level.requirements.parentalConsent && !config.userPreferences.parentalOverride) {
      conditions.push('Get parental consent');
    }

    if (metrics && level.requirements.usageTime > metrics.totalUsageTime) {
      const hoursNeeded = level.requirements.usageTime - metrics.totalUsageTime;
      conditions.push(`Use system for ${Math.ceil(hoursNeeded)} more hours`);
    }

    return conditions;
  }

  private estimateUnlockTime(userId: string, featureId: string): Date | undefined {
    // Simplified estimation - in real implementation would use ML models
    const metrics = this.userMetrics.get(userId);
    if (!metrics) return undefined;

    const avgHoursPerWeek = metrics.getAverageUsagePerWeek();
    if (avgHoursPerWeek === 0) return undefined;

    const level = this.getComplexityLevel(userId, featureId);
    if (!level) return undefined;

    const hoursNeeded = Math.max(0, level.requirements.usageTime - metrics.totalUsageTime);
    const weeksNeeded = hoursNeeded / avgHoursPerWeek;
    
    const unlockDate = new Date();
    unlockDate.setDate(unlockDate.getDate() + (weeksNeeded * 7));
    
    return unlockDate;
  }

  private shouldTriggerAutoAdjustment(userId: string, featureId: string): boolean {
    const config = this.configurations.get(userId);
    const metrics = this.userMetrics.get(userId);
    
    if (!config?.autoAdjustment.enabled || !metrics) return false;

    const lastAdjustment = this.getLastAdjustment(userId, featureId);
    if (lastAdjustment) {
      const timeSince = Date.now() - lastAdjustment.timestamp.getTime();
      const cooldown = config.autoAdjustment.cooldownPeriod * 60 * 1000;
      if (timeSince < cooldown) return false;
    }

    const interactions = metrics.getRecentInteractions(featureId, 10);
    return interactions.length >= 10; // Need minimum interactions for adjustment
  }

  private performAutoAdjustment(userId: string, featureId: string): void {
    const suggestions = this.suggestComplexityAdjustment(userId);
    const featureSuggestion = suggestions.find(s => s.featureId === featureId);
    
    if (featureSuggestion && featureSuggestion.confidence > 0.7) {
      this.adjustFeatureComplexity(
        userId,
        featureId,
        featureSuggestion.newLevel,
        featureSuggestion.reason
      );
    }
  }

  private recordAdjustment(
    userId: string,
    featureId: string,
    previousLevel: number,
    newLevel: number,
    reason: AdjustmentReason,
    automatic: boolean
  ): void {
    const history = this.adjustmentHistory.get(userId) || [];
    
    history.push({
      featureId,
      previousLevel,
      newLevel,
      reason,
      timestamp: new Date(),
      automatic,
      confidence: 1.0
    });

    this.adjustmentHistory.set(userId, history);
  }

  private getLastAdjustment(userId: string, featureId: string): ComplexityAdjustment | undefined {
    const history = this.adjustmentHistory.get(userId) || [];
    return history
      .filter(adj => adj.featureId === featureId)
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())[0];
  }

  private getAgeFromGroup(ageGroup: AgeGroup): number {
    switch (ageGroup) {
      case AgeGroup.TODDLER: return 4;
      case AgeGroup.PRESCHOOL: return 6;
      case AgeGroup.EARLY_ELEMENTARY: return 8;
      case AgeGroup.LATE_ELEMENTARY: return 11;
      case AgeGroup.MIDDLE_SCHOOL: return 14;
      case AgeGroup.HIGH_SCHOOL: return 17;
      case AgeGroup.YOUNG_ADULT: return 22;
      case AgeGroup.ADULT: return 35;
      case AgeGroup.SENIOR: return 70;
      default: return 25;
    }
  }

  private setupAutoAdjustment(): void {
    // Run auto-adjustment check every 5 minutes
    setInterval(() => {
      for (const [userId] of this.configurations) {
        const suggestions = this.suggestComplexityAdjustment(userId);
        suggestions.forEach(suggestion => {
          if (suggestion.confidence > 0.8) {
            this.adjustFeatureComplexity(
              userId,
              suggestion.featureId,
              suggestion.newLevel,
              suggestion.reason
            );
          }
        });
      }
    }, 5 * 60 * 1000);
  }
}

class UserComplexityMetrics {
  public totalUsageTime: number = 0; // hours
  public successRates: Map<string, number> = new Map();
  public errorCounts: Map<string, number> = new Map();
  public interactionHistory: InteractionRecord[] = [];
  public overallSuccessRate?: number;

  public recordInteraction(
    featureId: string,
    success: boolean,
    duration: number,
    errorCount: number
  ): void {
    this.interactionHistory.push({
      featureId,
      success,
      duration,
      errorCount,
      timestamp: new Date()
    });

    // Update totals
    this.totalUsageTime += duration / 3600; // convert to hours

    // Update success rate
    const recentInteractions = this.getRecentInteractions(featureId, 20);
    const successCount = recentInteractions.filter(i => i.success).length;
    this.successRates.set(featureId, successCount / recentInteractions.length);

    // Update error count
    this.errorCounts.set(featureId, (this.errorCounts.get(featureId) || 0) + errorCount);

    // Update overall success rate
    const allRecent = this.interactionHistory.slice(-100);
    this.overallSuccessRate = allRecent.filter(i => i.success).length / allRecent.length;
  }

  public getRecentInteractions(featureId: string, count: number): InteractionRecord[] {
    return this.interactionHistory
      .filter(i => i.featureId === featureId)
      .slice(-count);
  }

  public getAverageUsagePerWeek(): number {
    const weeksOfData = this.getWeeksOfData();
    return weeksOfData > 0 ? this.totalUsageTime / weeksOfData : 0;
  }

  private getWeeksOfData(): number {
    if (this.interactionHistory.length === 0) return 0;
    
    const oldest = this.interactionHistory[0].timestamp;
    const newest = this.interactionHistory[this.interactionHistory.length - 1].timestamp;
    const daysDiff = (newest.getTime() - oldest.getTime()) / (1000 * 60 * 60 * 24);
    
    return Math.max(1, daysDiff / 7);
  }
}

interface InteractionRecord {
  featureId: string;
  success: boolean;
  duration: number; // seconds
  errorCount: number;
  timestamp: Date;
}

export const complexityManager = new ComplexityManager();