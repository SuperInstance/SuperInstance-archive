import { EventEmitter } from 'events';
import { AgeGroup } from '../age-detection/age-detector';

export interface VocabularyProfile {
  userId: string;
  ageGroup: AgeGroup;
  readingLevel: number; // 1-16 (grade level)
  complexityPreference: number; // 0-1
  languagePreference: string;
  specialNeeds: SpecialNeedsOptions;
  learningStyle: LearningStyle;
  domainKnowledge: DomainKnowledge;
}

export interface SpecialNeedsOptions {
  dyslexia: boolean;
  autism: boolean;
  adhd: boolean;
  visualImpairment: boolean;
  cognitiveDelay: boolean;
  englishAsSecondLanguage: boolean;
}

export enum LearningStyle {
  VISUAL = 'visual',
  AUDITORY = 'auditory',
  KINESTHETIC = 'kinesthetic',
  MIXED = 'mixed'
}

export interface DomainKnowledge {
  technology: number; // 0-1
  education: number; // 0-1
  science: number; // 0-1
  arts: number; // 0-1
  sports: number; // 0-1
  general: number; // 0-1
}

export interface VocabularyEntry {
  simple: string;
  intermediate: string;
  advanced: string;
  professional: string;
  explanation?: string;
  examples?: string[];
  synonyms?: string[];
  domain?: string;
  ageAppropriate: {
    [key in AgeGroup]?: string;
  };
}

export interface TextAdaptation {
  originalText: string;
  adaptedText: string;
  adaptationLevel: AdaptationLevel;
  changes: TextChange[];
  readabilityScore: {
    original: number;
    adapted: number;
  };
  estimatedReadingTime: {
    original: number; // seconds
    adapted: number; // seconds
  };
}

export enum AdaptationLevel {
  NONE = 'none',
  SIMPLE = 'simple',
  MODERATE = 'moderate',
  EXTENSIVE = 'extensive',
  COMPLETE = 'complete'
}

export interface TextChange {
  type: ChangeType;
  original: string;
  replacement: string;
  position: { start: number; end: number };
  reason: string;
}

export enum ChangeType {
  WORD_SUBSTITUTION = 'word_substitution',
  SENTENCE_SIMPLIFICATION = 'sentence_simplification',
  CONCEPT_EXPLANATION = 'concept_explanation',
  STRUCTURE_REORGANIZATION = 'structure_reorganization',
  TECHNICAL_TERM_EXPLANATION = 'technical_term_explanation',
  EXAMPLE_ADDITION = 'example_addition',
  SUMMARY_ADDITION = 'summary_addition'
}

export class VocabularyAdapter extends EventEmitter {
  private profiles: Map<string, VocabularyProfile> = new Map();
  private vocabularyDatabase: Map<string, VocabularyEntry> = new Map();
  private adaptationRules: AdaptationRule[] = [];
  private cache: Map<string, TextAdaptation> = new Map();

  constructor() {
    super();
    this.initializeVocabularyDatabase();
    this.initializeAdaptationRules();
  }

  public createProfile(
    userId: string,
    ageGroup: AgeGroup,
    options: Partial<VocabularyProfile> = {}
  ): VocabularyProfile {
    const profile: VocabularyProfile = {
      userId,
      ageGroup,
      readingLevel: this.getDefaultReadingLevel(ageGroup),
      complexityPreference: this.getDefaultComplexity(ageGroup),
      languagePreference: 'en',
      specialNeeds: {
        dyslexia: false,
        autism: false,
        adhd: false,
        visualImpairment: false,
        cognitiveDelay: false,
        englishAsSecondLanguage: false,
        ...options.specialNeeds
      },
      learningStyle: LearningStyle.MIXED,
      domainKnowledge: {
        technology: 0.5,
        education: 0.5,
        science: 0.5,
        arts: 0.5,
        sports: 0.5,
        general: 0.5,
        ...options.domainKnowledge
      },
      ...options
    };

    this.profiles.set(userId, profile);
    this.emit('profileCreated', { userId, profile });

    return profile;
  }

  public async adaptText(userId: string, text: string, domain?: string): Promise<TextAdaptation> {
    const profile = this.profiles.get(userId);
    if (!profile) {
      throw new Error(`No vocabulary profile found for user: ${userId}`);
    }

    const cacheKey = this.generateCacheKey(userId, text, domain);
    const cached = this.cache.get(cacheKey);
    if (cached) return cached;

    const adaptation = await this.performTextAdaptation(text, profile, domain);
    this.cache.set(cacheKey, adaptation);
    
    this.emit('textAdapted', { userId, adaptation });
    return adaptation;
  }

  public adaptWord(userId: string, word: string, context?: string): string {
    const profile = this.profiles.get(userId);
    if (!profile) return word;

    const entry = this.vocabularyDatabase.get(word.toLowerCase());
    if (!entry) return word;

    // Age-specific adaptation
    const ageSpecific = entry.ageAppropriate[profile.ageGroup];
    if (ageSpecific) return ageSpecific;

    // Complexity-based adaptation
    if (profile.complexityPreference < 0.25) return entry.simple;
    if (profile.complexityPreference < 0.5) return entry.intermediate;
    if (profile.complexityPreference < 0.75) return entry.advanced;
    return entry.professional;
  }

  public generateExplanation(userId: string, concept: string): string | null {
    const profile = this.profiles.get(userId);
    if (!profile) return null;

    const entry = this.vocabularyDatabase.get(concept.toLowerCase());
    if (!entry || !entry.explanation) return null;

    return this.adaptExplanationToProfile(entry.explanation, profile);
  }

  public suggestSimplifications(text: string): SimplificationSuggestion[] {
    const words = this.tokenizeText(text);
    const suggestions: SimplificationSuggestion[] = [];

    for (const word of words) {
      const entry = this.vocabularyDatabase.get(word.toLowerCase());
      if (entry && entry.simple !== word) {
        suggestions.push({
          original: word,
          suggestion: entry.simple,
          reason: 'Simpler alternative available',
          confidence: 0.8
        });
      }
    }

    return suggestions;
  }

  public assessReadability(text: string): ReadabilityAssessment {
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
    const words = this.tokenizeText(text);
    const syllables = words.reduce((sum, word) => sum + this.countSyllables(word), 0);

    const averageWordsPerSentence = words.length / sentences.length;
    const averageSyllablesPerWord = syllables / words.length;

    // Flesch Reading Ease
    const fleschScore = 206.835 - (1.015 * averageWordsPerSentence) - (84.6 * averageSyllablesPerWord);
    
    // Flesch-Kincaid Grade Level
    const gradeLevel = 0.39 * averageWordsPerSentence + 11.8 * averageSyllablesPerWord - 15.59;

    // Complexity assessment
    const complexWords = words.filter(word => this.isComplexWord(word)).length;
    const complexityRatio = complexWords / words.length;

    return {
      fleschReadingEase: Math.max(0, Math.min(100, fleschScore)),
      gradeLevel: Math.max(1, Math.min(16, gradeLevel)),
      averageWordsPerSentence,
      averageSyllablesPerWord,
      complexityRatio,
      wordCount: words.length,
      sentenceCount: sentences.length,
      recommendedAge: this.gradeToAge(gradeLevel),
      difficulty: this.assessDifficulty(fleschScore)
    };
  }

  private async performTextAdaptation(
    text: string,
    profile: VocabularyProfile,
    domain?: string
  ): Promise<TextAdaptation> {
    const originalReadability = this.assessReadability(text);
    const targetReadingLevel = profile.readingLevel;
    const adaptationLevel = this.determineAdaptationLevel(originalReadability.gradeLevel, targetReadingLevel);

    let adaptedText = text;
    const changes: TextChange[] = [];

    if (adaptationLevel !== AdaptationLevel.NONE) {
      // Apply adaptation rules in order
      for (const rule of this.adaptationRules) {
        if (rule.shouldApply(adaptationLevel, profile, originalReadability)) {
          const result = await rule.apply(adaptedText, profile, domain);
          adaptedText = result.text;
          changes.push(...result.changes);
        }
      }
    }

    const adaptedReadability = this.assessReadability(adaptedText);

    return {
      originalText: text,
      adaptedText,
      adaptationLevel,
      changes,
      readabilityScore: {
        original: originalReadability.fleschReadingEase,
        adapted: adaptedReadability.fleschReadingEase
      },
      estimatedReadingTime: {
        original: this.estimateReadingTime(text, profile),
        adapted: this.estimateReadingTime(adaptedText, profile)
      }
    };
  }

  private initializeVocabularyDatabase(): void {
    // Technology terms
    this.vocabularyDatabase.set('algorithm', {
      simple: 'recipe',
      intermediate: 'step-by-step process',
      advanced: 'algorithm',
      professional: 'algorithmic procedure',
      explanation: 'A set of rules or steps to solve a problem',
      examples: ['Making a sandwich follows an algorithm', 'GPS uses algorithms to find routes'],
      ageAppropriate: {
        [AgeGroup.TODDLER]: 'steps',
        [AgeGroup.PRESCHOOL]: 'recipe',
        [AgeGroup.EARLY_ELEMENTARY]: 'step-by-step way',
        [AgeGroup.LATE_ELEMENTARY]: 'computer steps',
        [AgeGroup.MIDDLE_SCHOOL]: 'algorithm',
        [AgeGroup.HIGH_SCHOOL]: 'algorithm',
        [AgeGroup.YOUNG_ADULT]: 'algorithm',
        [AgeGroup.ADULT]: 'algorithm',
        [AgeGroup.SENIOR]: 'computer process'
      }
    });

    this.vocabularyDatabase.set('database', {
      simple: 'list',
      intermediate: 'organized information',
      advanced: 'database',
      professional: 'relational database system',
      explanation: 'A place where information is stored and organized',
      examples: ['A phone book is like a database', 'Libraries organize books like databases'],
      ageAppropriate: {
        [AgeGroup.TODDLER]: 'box',
        [AgeGroup.PRESCHOOL]: 'big list',
        [AgeGroup.EARLY_ELEMENTARY]: 'computer list',
        [AgeGroup.LATE_ELEMENTARY]: 'information storage',
        [AgeGroup.MIDDLE_SCHOOL]: 'database',
        [AgeGroup.HIGH_SCHOOL]: 'database',
        [AgeGroup.YOUNG_ADULT]: 'database',
        [AgeGroup.ADULT]: 'database',
        [AgeGroup.SENIOR]: 'computer filing system'
      }
    });

    // Add more vocabulary entries...
    this.addCommonVocabulary();
  }

  private addCommonVocabulary(): void {
    const entries = [
      { word: 'analyze', simple: 'look at', intermediate: 'study carefully', advanced: 'analyze', professional: 'conduct analysis' },
      { word: 'implement', simple: 'do', intermediate: 'put into action', advanced: 'implement', professional: 'execute implementation' },
      { word: 'optimize', simple: 'make better', intermediate: 'improve', advanced: 'optimize', professional: 'optimize performance' },
      { word: 'integrate', simple: 'connect', intermediate: 'combine', advanced: 'integrate', professional: 'integrate systems' },
      { word: 'authenticate', simple: 'check who you are', intermediate: 'verify identity', advanced: 'authenticate', professional: 'authenticate credentials' },
      { word: 'configure', simple: 'set up', intermediate: 'arrange settings', advanced: 'configure', professional: 'configure parameters' }
    ];

    entries.forEach(({ word, simple, intermediate, advanced, professional }) => {
      this.vocabularyDatabase.set(word, {
        simple,
        intermediate,
        advanced,
        professional,
        explanation: `${simple} in a specific way`,
        ageAppropriate: {
          [AgeGroup.TODDLER]: simple,
          [AgeGroup.PRESCHOOL]: simple,
          [AgeGroup.EARLY_ELEMENTARY]: simple,
          [AgeGroup.LATE_ELEMENTARY]: intermediate,
          [AgeGroup.MIDDLE_SCHOOL]: intermediate,
          [AgeGroup.HIGH_SCHOOL]: advanced,
          [AgeGroup.YOUNG_ADULT]: advanced,
          [AgeGroup.ADULT]: professional,
          [AgeGroup.SENIOR]: intermediate
        }
      });
    });
  }

  private initializeAdaptationRules(): void {
    // Word substitution rule
    this.adaptationRules.push(new WordSubstitutionRule(this.vocabularyDatabase));
    
    // Sentence simplification rule
    this.adaptationRules.push(new SentenceSimplificationRule());
    
    // Concept explanation rule
    this.adaptationRules.push(new ConceptExplanationRule(this.vocabularyDatabase));
    
    // Example addition rule
    this.adaptationRules.push(new ExampleAdditionRule());
  }

  private getDefaultReadingLevel(ageGroup: AgeGroup): number {
    switch (ageGroup) {
      case AgeGroup.TODDLER: return 1;
      case AgeGroup.PRESCHOOL: return 1;
      case AgeGroup.EARLY_ELEMENTARY: return 3;
      case AgeGroup.LATE_ELEMENTARY: return 5;
      case AgeGroup.MIDDLE_SCHOOL: return 8;
      case AgeGroup.HIGH_SCHOOL: return 12;
      case AgeGroup.YOUNG_ADULT: return 14;
      case AgeGroup.ADULT: return 16;
      case AgeGroup.SENIOR: return 12;
      default: return 8;
    }
  }

  private getDefaultComplexity(ageGroup: AgeGroup): number {
    switch (ageGroup) {
      case AgeGroup.TODDLER: return 0.1;
      case AgeGroup.PRESCHOOL: return 0.15;
      case AgeGroup.EARLY_ELEMENTARY: return 0.25;
      case AgeGroup.LATE_ELEMENTARY: return 0.4;
      case AgeGroup.MIDDLE_SCHOOL: return 0.6;
      case AgeGroup.HIGH_SCHOOL: return 0.75;
      case AgeGroup.YOUNG_ADULT: return 0.85;
      case AgeGroup.ADULT: return 0.9;
      case AgeGroup.SENIOR: return 0.6;
      default: return 0.5;
    }
  }

  private determineAdaptationLevel(currentLevel: number, targetLevel: number): AdaptationLevel {
    const difference = currentLevel - targetLevel;
    
    if (difference <= 1) return AdaptationLevel.NONE;
    if (difference <= 3) return AdaptationLevel.SIMPLE;
    if (difference <= 5) return AdaptationLevel.MODERATE;
    if (difference <= 8) return AdaptationLevel.EXTENSIVE;
    return AdaptationLevel.COMPLETE;
  }

  private adaptExplanationToProfile(explanation: string, profile: VocabularyProfile): string {
    // Simplify explanation based on profile
    if (profile.readingLevel < 5) {
      return this.simplifyForYoungReaders(explanation);
    }
    if (profile.specialNeeds.englishAsSecondLanguage) {
      return this.simplifyForESL(explanation);
    }
    return explanation;
  }

  private simplifyForYoungReaders(text: string): string {
    return text
      .replace(/\b(utilize|utilizes|utilizing)\b/gi, 'use')
      .replace(/\b(demonstrate|demonstrates)\b/gi, 'show')
      .replace(/\b(approximately)\b/gi, 'about')
      .replace(/\b(sufficient)\b/gi, 'enough')
      .replace(/\b(acquire|acquires)\b/gi, 'get');
  }

  private simplifyForESL(text: string): string {
    return text
      .replace(/\b(commence|commences)\b/gi, 'start')
      .replace(/\b(terminate|terminates)\b/gi, 'end')
      .replace(/\b(facilitate|facilitates)\b/gi, 'help')
      .replace(/\b(obtain|obtains)\b/gi, 'get')
      .replace(/\b(endeavor|endeavors)\b/gi, 'try');
  }

  private tokenizeText(text: string): string[] {
    return text.toLowerCase().match(/\b\w+\b/g) || [];
  }

  private countSyllables(word: string): number {
    word = word.toLowerCase();
    if (word.length <= 3) return 1;
    
    const vowels = 'aeiouy';
    let count = 0;
    let previousWasVowel = false;
    
    for (let i = 0; i < word.length; i++) {
      const isVowel = vowels.includes(word[i]);
      if (isVowel && !previousWasVowel) {
        count++;
      }
      previousWasVowel = isVowel;
    }
    
    if (word.endsWith('e') && count > 1) {
      count--;
    }
    
    return Math.max(1, count);
  }

  private isComplexWord(word: string): boolean {
    return word.length > 6 || this.countSyllables(word) > 2;
  }

  private gradeToAge(grade: number): number {
    return Math.max(5, grade + 5);
  }

  private assessDifficulty(fleschScore: number): string {
    if (fleschScore >= 90) return 'Very Easy';
    if (fleschScore >= 80) return 'Easy';
    if (fleschScore >= 70) return 'Fairly Easy';
    if (fleschScore >= 60) return 'Standard';
    if (fleschScore >= 50) return 'Fairly Difficult';
    if (fleschScore >= 30) return 'Difficult';
    return 'Very Difficult';
  }

  private estimateReadingTime(text: string, profile: VocabularyProfile): number {
    const words = this.tokenizeText(text).length;
    let wordsPerMinute = 200; // adult average
    
    switch (profile.ageGroup) {
      case AgeGroup.EARLY_ELEMENTARY: wordsPerMinute = 80; break;
      case AgeGroup.LATE_ELEMENTARY: wordsPerMinute = 115; break;
      case AgeGroup.MIDDLE_SCHOOL: wordsPerMinute = 140; break;
      case AgeGroup.HIGH_SCHOOL: wordsPerMinute = 170; break;
      case AgeGroup.SENIOR: wordsPerMinute = 175; break;
    }

    if (profile.specialNeeds.dyslexia) wordsPerMinute *= 0.7;
    if (profile.specialNeeds.englishAsSecondLanguage) wordsPerMinute *= 0.8;

    return Math.ceil((words / wordsPerMinute) * 60); // seconds
  }

  private generateCacheKey(userId: string, text: string, domain?: string): string {
    const textHash = this.simpleHash(text);
    return `${userId}:${textHash}:${domain || 'general'}`;
  }

  private simpleHash(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return hash.toString(36);
  }
}

// Adaptation Rules
abstract class AdaptationRule {
  abstract shouldApply(
    level: AdaptationLevel,
    profile: VocabularyProfile,
    readability: ReadabilityAssessment
  ): boolean;

  abstract apply(
    text: string,
    profile: VocabularyProfile,
    domain?: string
  ): Promise<{ text: string; changes: TextChange[] }>;
}

class WordSubstitutionRule extends AdaptationRule {
  constructor(private vocabularyDb: Map<string, VocabularyEntry>) {
    super();
  }

  shouldApply(level: AdaptationLevel, profile: VocabularyProfile): boolean {
    return level !== AdaptationLevel.NONE;
  }

  async apply(text: string, profile: VocabularyProfile): Promise<{ text: string; changes: TextChange[] }> {
    const changes: TextChange[] = [];
    let adaptedText = text;
    
    const words = text.match(/\b\w+\b/g) || [];
    
    for (const word of words) {
      const entry = this.vocabularyDb.get(word.toLowerCase());
      if (entry) {
        let replacement = this.selectAppropriateWord(entry, profile);
        
        if (replacement !== word) {
          const regex = new RegExp(`\\b${word}\\b`, 'gi');
          adaptedText = adaptedText.replace(regex, replacement);
          
          changes.push({
            type: ChangeType.WORD_SUBSTITUTION,
            original: word,
            replacement,
            position: { start: 0, end: 0 }, // Would need proper tracking
            reason: 'Simplified vocabulary for target reading level'
          });
        }
      }
    }
    
    return { text: adaptedText, changes };
  }

  private selectAppropriateWord(entry: VocabularyEntry, profile: VocabularyProfile): string {
    const ageSpecific = entry.ageAppropriate[profile.ageGroup];
    if (ageSpecific) return ageSpecific;

    if (profile.complexityPreference < 0.25) return entry.simple;
    if (profile.complexityPreference < 0.5) return entry.intermediate;
    if (profile.complexityPreference < 0.75) return entry.advanced;
    return entry.professional;
  }
}

class SentenceSimplificationRule extends AdaptationRule {
  shouldApply(level: AdaptationLevel, profile: VocabularyProfile): boolean {
    return level === AdaptationLevel.EXTENSIVE || level === AdaptationLevel.COMPLETE;
  }

  async apply(text: string, profile: VocabularyProfile): Promise<{ text: string; changes: TextChange[] }> {
    const changes: TextChange[] = [];
    const sentences = text.split(/(?<=[.!?])\s+/);
    let adaptedText = '';
    
    for (const sentence of sentences) {
      const simplified = this.simplifySentence(sentence, profile);
      adaptedText += simplified + ' ';
      
      if (simplified !== sentence) {
        changes.push({
          type: ChangeType.SENTENCE_SIMPLIFICATION,
          original: sentence,
          replacement: simplified,
          position: { start: 0, end: 0 },
          reason: 'Simplified sentence structure'
        });
      }
    }
    
    return { text: adaptedText.trim(), changes };
  }

  private simplifySentence(sentence: string, profile: VocabularyProfile): string {
    if (profile.readingLevel < 6) {
      // Break long sentences
      return sentence
        .replace(/;\s*/g, '. ')
        .replace(/,\s*and\s*/g, '. ')
        .replace(/,\s*but\s*/g, '. But ');
    }
    return sentence;
  }
}

class ConceptExplanationRule extends AdaptationRule {
  constructor(private vocabularyDb: Map<string, VocabularyEntry>) {
    super();
  }

  shouldApply(level: AdaptationLevel, profile: VocabularyProfile): boolean {
    return profile.readingLevel < 10;
  }

  async apply(text: string, profile: VocabularyProfile): Promise<{ text: string; changes: TextChange[] }> {
    const changes: TextChange[] = [];
    let adaptedText = text;
    
    // Find technical terms and add explanations
    const technicalTerms = this.findTechnicalTerms(text);
    
    for (const term of technicalTerms) {
      const entry = this.vocabularyDb.get(term.toLowerCase());
      if (entry?.explanation) {
        const explanation = ` (${entry.explanation})`;
        adaptedText = adaptedText.replace(
          new RegExp(`\\b${term}\\b`, 'i'),
          `${term}${explanation}`
        );
        
        changes.push({
          type: ChangeType.CONCEPT_EXPLANATION,
          original: term,
          replacement: `${term}${explanation}`,
          position: { start: 0, end: 0 },
          reason: 'Added explanation for technical term'
        });
      }
    }
    
    return { text: adaptedText, changes };
  }

  private findTechnicalTerms(text: string): string[] {
    const words = text.match(/\b\w+\b/g) || [];
    return words.filter(word => this.vocabularyDb.has(word.toLowerCase()));
  }
}

class ExampleAdditionRule extends AdaptationRule {
  shouldApply(level: AdaptationLevel, profile: VocabularyProfile): boolean {
    return profile.readingLevel < 8 && profile.learningStyle === LearningStyle.VISUAL;
  }

  async apply(text: string, profile: VocabularyProfile): Promise<{ text: string; changes: TextChange[] }> {
    // This would add examples to abstract concepts
    // Simplified implementation
    return { text, changes: [] };
  }
}

export interface SimplificationSuggestion {
  original: string;
  suggestion: string;
  reason: string;
  confidence: number;
}

export interface ReadabilityAssessment {
  fleschReadingEase: number;
  gradeLevel: number;
  averageWordsPerSentence: number;
  averageSyllablesPerWord: number;
  complexityRatio: number;
  wordCount: number;
  sentenceCount: number;
  recommendedAge: number;
  difficulty: string;
}

export const vocabularyAdapter = new VocabularyAdapter();