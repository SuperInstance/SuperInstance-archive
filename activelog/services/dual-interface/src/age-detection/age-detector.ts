import { EventEmitter } from 'events';

export interface UserProfile {
  id: string;
  birthDate?: Date;
  ageVerified?: boolean;
  parentalConsentGiven?: boolean;
  accountCreatedAt: Date;
  behavioralData?: BehavioralData;
  deviceInfo?: DeviceInfo;
  parentAccountId?: string;
  educationLevel?: EducationLevel;
  languagePreference?: string;
}

export interface BehavioralData {
  avgSessionDuration: number; // minutes
  clickPatterns: {
    averageClickSpeed: number; // clicks per second
    precisionScore: number; // 0-1, how accurately they click targets
    multitaskingBehavior: number; // 0-1, tendency to switch between tasks
  };
  vocabularyLevel: {
    averageWordLength: number;
    complexityScore: number; // 0-1
    grammarAccuracy: number; // 0-1
  };
  contentPreferences: {
    visualContent: number; // 0-1 preference for visual vs text
    interactiveElements: number; // 0-1 preference for interactive content
    gamificationElements: number; // 0-1 preference for game-like features
  };
  timePatterns: {
    mostActiveHours: number[]; // hours of day (0-23)
    weekdayUsage: number; // 0-1, weekday vs weekend usage ratio
    attentionSpan: number; // average minutes on single task
  };
}

export interface DeviceInfo {
  screenSize: { width: number; height: number };
  inputMethod: 'touch' | 'mouse' | 'keyboard' | 'mixed';
  operatingSystem: string;
  browserInfo: string;
  accessibilityFeatures: string[];
}

export enum AgeGroup {
  TODDLER = 'toddler', // 2-4
  PRESCHOOL = 'preschool', // 5-6
  EARLY_ELEMENTARY = 'early_elementary', // 7-9
  LATE_ELEMENTARY = 'late_elementary', // 10-12
  MIDDLE_SCHOOL = 'middle_school', // 13-15
  HIGH_SCHOOL = 'high_school', // 16-17
  YOUNG_ADULT = 'young_adult', // 18-25
  ADULT = 'adult', // 26-64
  SENIOR = 'senior' // 65+
}

export enum EducationLevel {
  PRESCHOOL = 'preschool',
  ELEMENTARY = 'elementary',
  MIDDLE_SCHOOL = 'middle_school',
  HIGH_SCHOOL = 'high_school',
  COLLEGE = 'college',
  GRADUATE = 'graduate',
  UNKNOWN = 'unknown'
}

export interface AgeDetectionResult {
  estimatedAge: number;
  ageGroup: AgeGroup;
  confidenceLevel: number; // 0-1
  detectionMethod: DetectionMethod[];
  recommendations: {
    interfaceComplexity: number; // 0-1
    vocabularyLevel: number; // 0-1
    requiresParentalSupervision: boolean;
    suggestedTheme: string;
    contentFiltering: ContentFilterLevel;
  };
  lastUpdated: Date;
}

export enum DetectionMethod {
  BIRTH_DATE = 'birth_date',
  BEHAVIORAL_ANALYSIS = 'behavioral_analysis',
  VOCABULARY_ANALYSIS = 'vocabulary_analysis',
  DEVICE_PATTERNS = 'device_patterns',
  PARENTAL_ACCOUNT = 'parental_account',
  CONTENT_PREFERENCES = 'content_preferences',
  INTERACTION_PATTERNS = 'interaction_patterns'
}

export enum ContentFilterLevel {
  UNRESTRICTED = 'unrestricted',
  LIGHT_FILTERING = 'light_filtering',
  MODERATE_FILTERING = 'moderate_filtering',
  HEAVY_FILTERING = 'heavy_filtering',
  STRICT_FILTERING = 'strict_filtering'
}

export class AgeDetector extends EventEmitter {
  private userProfiles: Map<string, UserProfile> = new Map();
  private ageResults: Map<string, AgeDetectionResult> = new Map();
  private behavioralAnalyzer: BehavioralAnalyzer;
  private vocabularyAnalyzer: VocabularyAnalyzer;

  constructor() {
    super();
    this.behavioralAnalyzer = new BehavioralAnalyzer();
    this.vocabularyAnalyzer = new VocabularyAnalyzer();
  }

  public async detectAge(userId: string, profile: UserProfile): Promise<AgeDetectionResult> {
    this.userProfiles.set(userId, profile);

    const detectionMethods: DetectionMethod[] = [];
    let estimatedAge = 25; // default adult age
    let confidenceLevel = 0.1; // very low initial confidence

    // Method 1: Birth date (most reliable)
    if (profile.birthDate && profile.ageVerified) {
      estimatedAge = this.calculateAgeFromBirthDate(profile.birthDate);
      confidenceLevel = 0.95;
      detectionMethods.push(DetectionMethod.BIRTH_DATE);
    }

    // Method 2: Parental account linkage
    else if (profile.parentAccountId) {
      const parentProfile = this.userProfiles.get(profile.parentAccountId);
      if (parentProfile?.birthDate) {
        const parentAge = this.calculateAgeFromBirthDate(parentProfile.birthDate);
        estimatedAge = Math.max(5, parentAge - 25); // Assume parent had child around 25
        confidenceLevel = 0.7;
        detectionMethods.push(DetectionMethod.PARENTAL_ACCOUNT);
      }
    }

    // Method 3: Behavioral analysis
    if (profile.behavioralData) {
      const behavioralAge = await this.behavioralAnalyzer.analyzeAge(profile.behavioralData);
      if (detectionMethods.length === 0) {
        estimatedAge = behavioralAge.estimatedAge;
        confidenceLevel = behavioralAge.confidence;
      } else {
        // Weighted average with existing estimate
        const weight = behavioralAge.confidence * 0.3;
        estimatedAge = (estimatedAge * (1 - weight)) + (behavioralAge.estimatedAge * weight);
        confidenceLevel = Math.min(0.9, confidenceLevel + (behavioralAge.confidence * 0.1));
      }
      detectionMethods.push(DetectionMethod.BEHAVIORAL_ANALYSIS);
    }

    // Method 4: Device and interaction patterns
    if (profile.deviceInfo) {
      const deviceAge = this.analyzeDevicePatterns(profile.deviceInfo);
      if (detectionMethods.length <= 1) {
        estimatedAge = (estimatedAge + deviceAge.estimatedAge) / 2;
        confidenceLevel = Math.max(confidenceLevel, deviceAge.confidence * 0.6);
      }
      detectionMethods.push(DetectionMethod.DEVICE_PATTERNS);
    }

    const ageGroup = this.determineAgeGroup(estimatedAge);
    const recommendations = this.generateRecommendations(estimatedAge, ageGroup, profile);

    const result: AgeDetectionResult = {
      estimatedAge: Math.round(estimatedAge),
      ageGroup,
      confidenceLevel: Math.min(1, confidenceLevel),
      detectionMethod: detectionMethods,
      recommendations,
      lastUpdated: new Date()
    };

    this.ageResults.set(userId, result);
    this.emit('ageDetected', { userId, result });

    return result;
  }

  public async updateBehavioralData(userId: string, behavioralData: Partial<BehavioralData>): Promise<void> {
    const profile = this.userProfiles.get(userId);
    if (!profile) return;

    profile.behavioralData = {
      ...profile.behavioralData,
      ...behavioralData
    } as BehavioralData;

    this.userProfiles.set(userId, profile);

    // Re-analyze age with updated behavioral data
    await this.detectAge(userId, profile);
  }

  public getAgeResult(userId: string): AgeDetectionResult | null {
    return this.ageResults.get(userId) || null;
  }

  public isMinor(userId: string): boolean {
    const result = this.ageResults.get(userId);
    return result ? result.estimatedAge < 18 : false;
  }

  public requiresParentalConsent(userId: string): boolean {
    const result = this.ageResults.get(userId);
    return result ? result.estimatedAge < 13 : false;
  }

  public getRecommendedComplexity(userId: string): number {
    const result = this.ageResults.get(userId);
    return result?.recommendations.interfaceComplexity || 0.7;
  }

  public getContentFilterLevel(userId: string): ContentFilterLevel {
    const result = this.ageResults.get(userId);
    return result?.recommendations.contentFiltering || ContentFilterLevel.MODERATE_FILTERING;
  }

  private calculateAgeFromBirthDate(birthDate: Date): number {
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    
    return age;
  }

  private determineAgeGroup(age: number): AgeGroup {
    if (age >= 2 && age <= 4) return AgeGroup.TODDLER;
    if (age >= 5 && age <= 6) return AgeGroup.PRESCHOOL;
    if (age >= 7 && age <= 9) return AgeGroup.EARLY_ELEMENTARY;
    if (age >= 10 && age <= 12) return AgeGroup.LATE_ELEMENTARY;
    if (age >= 13 && age <= 15) return AgeGroup.MIDDLE_SCHOOL;
    if (age >= 16 && age <= 17) return AgeGroup.HIGH_SCHOOL;
    if (age >= 18 && age <= 25) return AgeGroup.YOUNG_ADULT;
    if (age >= 26 && age <= 64) return AgeGroup.ADULT;
    return AgeGroup.SENIOR;
  }

  private analyzeDevicePatterns(deviceInfo: DeviceInfo): { estimatedAge: number; confidence: number } {
    let ageIndicators: number[] = [];
    let confidence = 0.3;

    // Touch vs mouse usage patterns
    if (deviceInfo.inputMethod === 'touch') {
      ageIndicators.push(15); // Younger users more likely to use touch
      confidence += 0.1;
    } else if (deviceInfo.inputMethod === 'mouse') {
      ageIndicators.push(35); // Older users more comfortable with traditional input
      confidence += 0.1;
    }

    // Screen size preferences
    if (deviceInfo.screenSize.width < 800) {
      ageIndicators.push(20); // Mobile-first users tend to be younger
      confidence += 0.1;
    } else if (deviceInfo.screenSize.width > 1920) {
      ageIndicators.push(30); // Large screens often used by professionals
      confidence += 0.05;
    }

    // Accessibility features usage
    if (deviceInfo.accessibilityFeatures.length > 0) {
      ageIndicators.push(45); // More common in older users
      confidence += 0.15;
    }

    const estimatedAge = ageIndicators.length > 0 
      ? ageIndicators.reduce((sum, age) => sum + age, 0) / ageIndicators.length
      : 25;

    return { estimatedAge, confidence: Math.min(0.5, confidence) };
  }

  private generateRecommendations(
    estimatedAge: number, 
    ageGroup: AgeGroup, 
    profile: UserProfile
  ): AgeDetectionResult['recommendations'] {
    const isChild = estimatedAge < 13;
    const isTeen = estimatedAge >= 13 && estimatedAge < 18;
    const isYoung = estimatedAge >= 18 && estimatedAge < 26;
    const isSenior = estimatedAge >= 65;

    // Interface complexity (0 = very simple, 1 = very complex)
    let interfaceComplexity = 0.7;
    if (estimatedAge < 7) interfaceComplexity = 0.1;
    else if (estimatedAge < 13) interfaceComplexity = 0.3;
    else if (estimatedAge < 18) interfaceComplexity = 0.6;
    else if (estimatedAge > 65) interfaceComplexity = 0.5;

    // Vocabulary level (0 = very simple, 1 = professional)
    let vocabularyLevel = 0.7;
    if (estimatedAge < 7) vocabularyLevel = 0.1;
    else if (estimatedAge < 13) vocabularyLevel = 0.3;
    else if (estimatedAge < 18) vocabularyLevel = 0.5;

    // Content filtering
    let contentFiltering = ContentFilterLevel.LIGHT_FILTERING;
    if (isChild) contentFiltering = ContentFilterLevel.STRICT_FILTERING;
    else if (isTeen) contentFiltering = ContentFilterLevel.MODERATE_FILTERING;
    else if (isYoung) contentFiltering = ContentFilterLevel.LIGHT_FILTERING;
    else contentFiltering = ContentFilterLevel.UNRESTRICTED;

    // Theme suggestions
    let suggestedTheme = 'professional';
    if (estimatedAge < 7) suggestedTheme = 'playful';
    else if (estimatedAge < 13) suggestedTheme = 'colorful';
    else if (estimatedAge < 18) suggestedTheme = 'modern';
    else if (isSenior) suggestedTheme = 'high-contrast';

    return {
      interfaceComplexity,
      vocabularyLevel,
      requiresParentalSupervision: isChild,
      suggestedTheme,
      contentFiltering
    };
  }
}

class BehavioralAnalyzer {
  public async analyzeAge(data: BehavioralData): Promise<{ estimatedAge: number; confidence: number }> {
    const indicators: number[] = [];
    let confidence = 0;

    // Click patterns analysis
    if (data.clickPatterns.averageClickSpeed > 2) {
      indicators.push(15); // Fast clicking often indicates younger users
      confidence += 0.1;
    } else if (data.clickPatterns.averageClickSpeed < 0.5) {
      indicators.push(50); // Slow, deliberate clicking often indicates older users
      confidence += 0.1;
    }

    // Precision score
    if (data.clickPatterns.precisionScore < 0.6) {
      indicators.push(12); // Lower precision often indicates younger users
      confidence += 0.1;
    }

    // Session duration patterns
    if (data.avgSessionDuration < 15) {
      indicators.push(8); // Very short sessions often indicate very young users
      confidence += 0.15;
    } else if (data.avgSessionDuration > 120) {
      indicators.push(35); // Long sessions often indicate adult users
      confidence += 0.1;
    }

    // Attention span
    if (data.timePatterns.attentionSpan < 5) {
      indicators.push(6); // Very short attention span
      confidence += 0.2;
    } else if (data.timePatterns.attentionSpan > 30) {
      indicators.push(30); // Good attention span indicates maturity
      confidence += 0.1;
    }

    // Content preferences
    if (data.contentPreferences.gamificationElements > 0.8) {
      indicators.push(12); // High preference for gamification
      confidence += 0.1;
    }

    if (data.contentPreferences.visualContent > 0.8) {
      indicators.push(10); // High preference for visual content
      confidence += 0.05;
    }

    // Vocabulary analysis
    if (data.vocabularyLevel.complexityScore < 0.3) {
      indicators.push(8); // Simple vocabulary
      confidence += 0.15;
    } else if (data.vocabularyLevel.complexityScore > 0.8) {
      indicators.push(35); // Complex vocabulary indicates education/age
      confidence += 0.1;
    }

    const estimatedAge = indicators.length > 0
      ? indicators.reduce((sum, age) => sum + age, 0) / indicators.length
      : 25;

    return {
      estimatedAge: Math.max(3, Math.min(90, estimatedAge)),
      confidence: Math.min(0.8, confidence)
    };
  }
}

class VocabularyAnalyzer {
  public analyzeComplexity(text: string): { complexityScore: number; readingLevel: number } {
    const words = text.toLowerCase().split(/\s+/);
    const sentences = text.split(/[.!?]+/).length;
    
    // Calculate average word length
    const avgWordLength = words.reduce((sum, word) => sum + word.length, 0) / words.length;
    
    // Calculate syllable count (simplified)
    const avgSyllables = words.reduce((sum, word) => sum + this.countSyllables(word), 0) / words.length;
    
    // Flesch Reading Ease approximation
    const fleschScore = 206.835 - (1.015 * (words.length / sentences)) - (84.6 * avgSyllables);
    
    // Convert to 0-1 complexity score
    const complexityScore = Math.max(0, Math.min(1, (100 - fleschScore) / 100));
    
    // Estimate reading level (grade level)
    const readingLevel = Math.max(1, Math.min(16, 
      0.39 * (words.length / sentences) + 11.8 * avgSyllables - 15.59
    ));
    
    return { complexityScore, readingLevel };
  }

  private countSyllables(word: string): number {
    word = word.toLowerCase();
    if (word.length <= 3) return 1;
    
    const vowels = 'aeiouy';
    let syllableCount = 0;
    let previousWasVowel = false;
    
    for (let i = 0; i < word.length; i++) {
      const isVowel = vowels.includes(word[i]);
      if (isVowel && !previousWasVowel) {
        syllableCount++;
      }
      previousWasVowel = isVowel;
    }
    
    // Handle silent e
    if (word.endsWith('e') && syllableCount > 1) {
      syllableCount--;
    }
    
    return Math.max(1, syllableCount);
  }
}

export const ageDetector = new AgeDetector();