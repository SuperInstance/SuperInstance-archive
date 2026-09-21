import { EventEmitter } from 'events';
import { AgeGroup } from '../age-detection/age-detector';

export interface IconConfiguration {
  userId: string;
  ageGroup: AgeGroup;
  style: IconStyle;
  size: IconSize;
  colorScheme: ColorScheme;
  animationLevel: AnimationLevel;
  accessibility: IconAccessibilityOptions;
  culturalContext: CulturalContext;
  cognitiveLevel: number; // 0-1
}

export enum IconStyle {
  OUTLINE = 'outline',
  FILLED = 'filled',
  COLORFUL = 'colorful',
  ILLUSTRATED = 'illustrated',
  PHOTOGRAPHIC = 'photographic',
  MINIMAL = 'minimal',
  PLAYFUL = 'playful',
  PROFESSIONAL = 'professional'
}

export enum IconSize {
  TINY = 'tiny', // 12px
  SMALL = 'small', // 16px
  MEDIUM = 'medium', // 24px
  LARGE = 'large', // 32px
  EXTRA_LARGE = 'extra_large', // 48px
  HUGE = 'huge' // 64px+
}

export enum AnimationLevel {
  NONE = 'none',
  SUBTLE = 'subtle',
  MODERATE = 'moderate',
  PROMINENT = 'prominent',
  PLAYFUL = 'playful'
}

export enum ColorScheme {
  MONOCHROME = 'monochrome',
  MINIMAL_COLOR = 'minimal_color',
  FULL_COLOR = 'full_color',
  HIGH_CONTRAST = 'high_contrast',
  RAINBOW = 'rainbow'
}

export interface IconAccessibilityOptions {
  highContrast: boolean;
  altTextRequired: boolean;
  soundEffects: boolean;
  hoverDescriptions: boolean;
  largeClickTargets: boolean;
  reducedMotion: boolean;
  colorBlindFriendly: boolean;
}

export enum CulturalContext {
  WESTERN = 'western',
  EASTERN = 'eastern',
  UNIVERSAL = 'universal',
  LOCAL = 'local'
}

export interface IconDefinition {
  id: string;
  name: string;
  category: IconCategory;
  variants: IconVariant[];
  semanticMeaning: string;
  ageAppropriate: {
    [key in AgeGroup]?: IconVariant;
  };
  culturalVariants: {
    [key in CulturalContext]?: IconVariant;
  };
  accessibility: {
    altText: string;
    description: string;
    soundCue?: string;
  };
  cognitiveLoad: number; // 0-1, how complex the icon is to understand
  recognitionRate: {
    [key in AgeGroup]?: number; // 0-1, how well this age group recognizes the icon
  };
}

export enum IconCategory {
  NAVIGATION = 'navigation',
  ACTIONS = 'actions',
  OBJECTS = 'objects',
  PEOPLE = 'people',
  EMOTIONS = 'emotions',
  EDUCATION = 'education',
  ENTERTAINMENT = 'entertainment',
  COMMUNICATION = 'communication',
  SYSTEM = 'system',
  ABSTRACT = 'abstract'
}

export interface IconVariant {
  style: IconStyle;
  svgPath: string;
  colorPalette?: string[];
  animationData?: AnimationData;
  size: { width: number; height: number };
  strokeWidth?: number;
  complexity: number; // 0-1
}

export interface AnimationData {
  type: AnimationType;
  duration: number;
  easing: string;
  loop: boolean;
  keyframes?: AnimationKeyframe[];
}

export enum AnimationType {
  NONE = 'none',
  SCALE = 'scale',
  ROTATE = 'rotate',
  BOUNCE = 'bounce',
  PULSE = 'pulse',
  WIGGLE = 'wiggle',
  GLOW = 'glow',
  MORPHING = 'morphing'
}

export interface AnimationKeyframe {
  at: number; // 0-1
  transform: string;
  opacity?: number;
  color?: string;
}

export interface IconRequest {
  concept: string;
  context?: string;
  importance: 'low' | 'medium' | 'high' | 'critical';
  fallbackText?: string;
}

export interface IconResult {
  iconId: string;
  variant: IconVariant;
  renderedSVG: string;
  accessibility: {
    altText: string;
    ariaLabel: string;
    role: string;
  };
  metadata: {
    confidence: number; // How well this icon matches the request
    appropriateness: number; // How age-appropriate this icon is
    recognitionLikelihood: number; // How likely user will understand
  };
}

export class IconSystem extends EventEmitter {
  private configurations: Map<string, IconConfiguration> = new Map();
  private iconLibrary: Map<string, IconDefinition> = new Map();
  private conceptMappings: Map<string, string[]> = new Map(); // concept -> icon IDs
  private cache: Map<string, IconResult> = new Map();

  constructor() {
    super();
    this.initializeIconLibrary();
    this.initializeConceptMappings();
  }

  public createConfiguration(
    userId: string,
    ageGroup: AgeGroup,
    preferences?: Partial<IconConfiguration>
  ): IconConfiguration {
    const config: IconConfiguration = {
      userId,
      ageGroup,
      style: this.getDefaultStyle(ageGroup),
      size: this.getDefaultSize(ageGroup),
      colorScheme: this.getDefaultColorScheme(ageGroup),
      animationLevel: this.getDefaultAnimationLevel(ageGroup),
      accessibility: this.getDefaultAccessibilityOptions(ageGroup),
      culturalContext: CulturalContext.UNIVERSAL,
      cognitiveLevel: this.getDefaultCognitiveLevel(ageGroup),
      ...preferences
    };

    this.configurations.set(userId, config);
    this.emit('configurationCreated', { userId, config });

    return config;
  }

  public async getIcon(userId: string, request: IconRequest): Promise<IconResult> {
    const config = this.configurations.get(userId);
    if (!config) {
      throw new Error(`No icon configuration found for user: ${userId}`);
    }

    const cacheKey = this.generateCacheKey(userId, request);
    const cached = this.cache.get(cacheKey);
    if (cached) return cached;

    const result = await this.selectAndRenderIcon(request, config);
    this.cache.set(cacheKey, result);

    this.emit('iconRequested', { userId, request, result });
    return result;
  }

  public generateIconGrid(userId: string, category: IconCategory): IconResult[] {
    const config = this.configurations.get(userId);
    if (!config) return [];

    const categoryIcons = Array.from(this.iconLibrary.values())
      .filter(icon => icon.category === category)
      .filter(icon => this.isAgeAppropriate(icon, config.ageGroup))
      .slice(0, 12); // Limit to 12 icons for grid

    return categoryIcons.map(icon => ({
      iconId: icon.id,
      variant: this.selectVariant(icon, config),
      renderedSVG: this.renderSVG(icon, config),
      accessibility: {
        altText: icon.accessibility.altText,
        ariaLabel: icon.accessibility.description,
        role: 'img'
      },
      metadata: {
        confidence: 1.0,
        appropriateness: this.calculateAppropriateness(icon, config),
        recognitionLikelihood: icon.recognitionRate[config.ageGroup] || 0.5
      }
    }));
  }

  public suggestIcons(userId: string, concept: string): IconResult[] {
    const config = this.configurations.get(userId);
    if (!config) return [];

    const relatedIconIds = this.conceptMappings.get(concept.toLowerCase()) || [];
    const suggestions: IconResult[] = [];

    for (const iconId of relatedIconIds.slice(0, 5)) {
      const icon = this.iconLibrary.get(iconId);
      if (icon && this.isAgeAppropriate(icon, config.ageGroup)) {
        suggestions.push({
          iconId: icon.id,
          variant: this.selectVariant(icon, config),
          renderedSVG: this.renderSVG(icon, config),
          accessibility: {
            altText: icon.accessibility.altText,
            ariaLabel: icon.accessibility.description,
            role: 'img'
          },
          metadata: {
            confidence: this.calculateConceptMatch(concept, icon),
            appropriateness: this.calculateAppropriateness(icon, config),
            recognitionLikelihood: icon.recognitionRate[config.ageGroup] || 0.5
          }
        });
      }
    }

    return suggestions.sort((a, b) => b.metadata.confidence - a.metadata.confidence);
  }

  public createCustomIcon(
    userId: string,
    concept: string,
    svgPath: string,
    options?: Partial<IconDefinition>
  ): string {
    const config = this.configurations.get(userId);
    if (!config) throw new Error('User configuration not found');

    const iconId = `custom_${Date.now()}`;
    const customIcon: IconDefinition = {
      id: iconId,
      name: concept,
      category: IconCategory.OBJECTS,
      variants: [{
        style: config.style,
        svgPath,
        size: { width: 24, height: 24 },
        complexity: 0.5
      }],
      semanticMeaning: concept,
      ageAppropriate: {},
      culturalVariants: {},
      accessibility: {
        altText: concept,
        description: `Custom icon representing ${concept}`
      },
      cognitiveLoad: 0.5,
      recognitionRate: {},
      ...options
    };

    this.iconLibrary.set(iconId, customIcon);
    this.emit('customIconCreated', { userId, iconId, concept });

    return iconId;
  }

  private async selectAndRenderIcon(request: IconRequest, config: IconConfiguration): Promise<IconResult> {
    // Find best matching icon
    const candidates = this.findCandidateIcons(request, config);
    const bestIcon = this.selectBestIcon(candidates, request, config);

    if (!bestIcon) {
      // Generate fallback icon
      return this.generateFallbackIcon(request, config);
    }

    const variant = this.selectVariant(bestIcon, config);
    const renderedSVG = this.renderSVG(bestIcon, config, variant);

    return {
      iconId: bestIcon.id,
      variant,
      renderedSVG,
      accessibility: {
        altText: request.fallbackText || bestIcon.accessibility.altText,
        ariaLabel: bestIcon.accessibility.description,
        role: 'img'
      },
      metadata: {
        confidence: this.calculateConceptMatch(request.concept, bestIcon),
        appropriateness: this.calculateAppropriateness(bestIcon, config),
        recognitionLikelihood: bestIcon.recognitionRate[config.ageGroup] || 0.5
      }
    };
  }

  private findCandidateIcons(request: IconRequest, config: IconConfiguration): IconDefinition[] {
    const conceptIds = this.conceptMappings.get(request.concept.toLowerCase()) || [];
    const candidates: IconDefinition[] = [];

    // Exact concept matches
    for (const iconId of conceptIds) {
      const icon = this.iconLibrary.get(iconId);
      if (icon && this.isAgeAppropriate(icon, config.ageGroup)) {
        candidates.push(icon);
      }
    }

    // Semantic similarity matches
    if (candidates.length < 3) {
      const similarConcepts = this.findSimilarConcepts(request.concept);
      for (const concept of similarConcepts) {
        const ids = this.conceptMappings.get(concept) || [];
        for (const iconId of ids) {
          const icon = this.iconLibrary.get(iconId);
          if (icon && !candidates.includes(icon) && this.isAgeAppropriate(icon, config.ageGroup)) {
            candidates.push(icon);
          }
        }
      }
    }

    return candidates;
  }

  private selectBestIcon(
    candidates: IconDefinition[],
    request: IconRequest,
    config: IconConfiguration
  ): IconDefinition | null {
    if (candidates.length === 0) return null;

    let bestIcon = candidates[0];
    let bestScore = this.scoreIcon(bestIcon, request, config);

    for (const candidate of candidates.slice(1)) {
      const score = this.scoreIcon(candidate, request, config);
      if (score > bestScore) {
        bestIcon = candidate;
        bestScore = score;
      }
    }

    return bestIcon;
  }

  private scoreIcon(icon: IconDefinition, request: IconRequest, config: IconConfiguration): number {
    let score = 0;

    // Concept match
    score += this.calculateConceptMatch(request.concept, icon) * 0.4;

    // Age appropriateness
    score += this.calculateAppropriateness(icon, config) * 0.3;

    // Recognition likelihood
    score += (icon.recognitionRate[config.ageGroup] || 0.5) * 0.2;

    // Complexity appropriateness
    const complexityScore = 1 - Math.abs(icon.cognitiveLoad - config.cognitiveLevel);
    score += complexityScore * 0.1;

    return score;
  }

  private selectVariant(icon: IconDefinition, config: IconConfiguration): IconVariant {
    // Check for age-specific variant first
    const ageVariant = icon.ageAppropriate[config.ageGroup];
    if (ageVariant) return ageVariant;

    // Check for cultural variant
    const culturalVariant = icon.culturalVariants[config.culturalContext];
    if (culturalVariant) return culturalVariant;

    // Find best matching variant by style
    const styleMatch = icon.variants.find(v => v.style === config.style);
    if (styleMatch) return styleMatch;

    // Fallback to first variant
    return icon.variants[0];
  }

  private renderSVG(
    icon: IconDefinition,
    config: IconConfiguration,
    variant?: IconVariant
  ): string {
    const selectedVariant = variant || this.selectVariant(icon, config);
    const sizeMap = {
      [IconSize.TINY]: 12,
      [IconSize.SMALL]: 16,
      [IconSize.MEDIUM]: 24,
      [IconSize.LARGE]: 32,
      [IconSize.EXTRA_LARGE]: 48,
      [IconSize.HUGE]: 64
    };

    const size = sizeMap[config.size];
    const colors = this.getColorPalette(config.colorScheme);
    
    let svg = `<svg width="${size}" height="${size}" viewBox="0 0 ${selectedVariant.size.width} ${selectedVariant.size.height}" xmlns="http://www.w3.org/2000/svg">`;
    
    // Apply accessibility attributes
    if (config.accessibility.altTextRequired) {
      svg += `<title>${icon.accessibility.altText}</title>`;
      svg += `<desc>${icon.accessibility.description}</desc>`;
    }

    // Apply colors and styles
    let styledPath = selectedVariant.svgPath;
    if (colors.primary) {
      styledPath = styledPath.replace(/fill="[^"]*"/g, `fill="${colors.primary}"`);
      styledPath = styledPath.replace(/stroke="[^"]*"/g, `stroke="${colors.secondary || colors.primary}"`);
    }

    svg += styledPath;

    // Add animations
    if (config.animationLevel !== AnimationLevel.NONE && selectedVariant.animationData) {
      svg += this.generateAnimation(selectedVariant.animationData, config.animationLevel);
    }

    svg += '</svg>';

    return svg;
  }

  private generateAnimation(animationData: AnimationData, level: AnimationLevel): string {
    if (level === AnimationLevel.NONE || animationData.type === AnimationType.NONE) {
      return '';
    }

    const intensity = {
      [AnimationLevel.SUBTLE]: 0.3,
      [AnimationLevel.MODERATE]: 0.6,
      [AnimationLevel.PROMINENT]: 0.9,
      [AnimationLevel.PLAYFUL]: 1.2
    }[level] || 0.6;

    switch (animationData.type) {
      case AnimationType.PULSE:
        return `<animate attributeName="opacity" values="1;0.5;1" dur="${animationData.duration}ms" repeatCount="${animationData.loop ? 'indefinite' : '1'}"/>`;
      
      case AnimationType.SCALE:
        return `<animateTransform attributeName="transform" type="scale" values="1;${1 + intensity * 0.2};1" dur="${animationData.duration}ms" repeatCount="${animationData.loop ? 'indefinite' : '1'}"/>`;
      
      case AnimationType.BOUNCE:
        return `<animateTransform attributeName="transform" type="translate" values="0,0;0,-${intensity * 5};0,0" dur="${animationData.duration}ms" repeatCount="${animationData.loop ? 'indefinite' : '1'}"/>`;
      
      default:
        return '';
    }
  }

  private initializeIconLibrary(): void {
    // Home icon
    this.iconLibrary.set('home', {
      id: 'home',
      name: 'Home',
      category: IconCategory.NAVIGATION,
      variants: [
        {
          style: IconStyle.OUTLINE,
          svgPath: '<path d="M3 9L12 2L21 9V20C21 21.1 20.1 22 19 22H5C3.9 22 3 21.1 3 20V9Z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round" stroke-linecap="round"/>',
          size: { width: 24, height: 24 },
          complexity: 0.2
        },
        {
          style: IconStyle.PLAYFUL,
          svgPath: '<path d="M12 2L2 10V20C2 21.1 2.9 22 4 22H20C21.1 22 22 21.1 22 20V10L12 2Z" fill="#FF6B6B"/><circle cx="12" cy="16" r="2" fill="#FFF"/>',
          size: { width: 24, height: 24 },
          complexity: 0.3,
          colorPalette: ['#FF6B6B', '#FFF']
        }
      ],
      semanticMeaning: 'Home, house, main page, start location',
      ageAppropriate: {
        [AgeGroup.TODDLER]: {
          style: IconStyle.COLORFUL,
          svgPath: '<path d="M12 2L2 10V20C2 21.1 2.9 22 4 22H20C21.1 22 22 21.1 22 20V10L12 2Z" fill="#FF6B6B" stroke="#000" stroke-width="3"/><rect x="10" y="14" width="4" height="6" fill="#8B4513"/><rect x="6" y="12" width="3" height="3" fill="#87CEEB"/>',
          size: { width: 32, height: 32 },
          complexity: 0.1,
          colorPalette: ['#FF6B6B', '#8B4513', '#87CEEB']
        }
      },
      culturalVariants: {},
      accessibility: {
        altText: 'Home',
        description: 'Home icon to return to main page',
        soundCue: 'home'
      },
      cognitiveLoad: 0.1,
      recognitionRate: {
        [AgeGroup.TODDLER]: 0.9,
        [AgeGroup.PRESCHOOL]: 0.95,
        [AgeGroup.EARLY_ELEMENTARY]: 0.98,
        [AgeGroup.LATE_ELEMENTARY]: 0.99,
        [AgeGroup.MIDDLE_SCHOOL]: 1.0,
        [AgeGroup.HIGH_SCHOOL]: 1.0,
        [AgeGroup.YOUNG_ADULT]: 1.0,
        [AgeGroup.ADULT]: 1.0,
        [AgeGroup.SENIOR]: 0.95
      }
    });

    // Add more icons...
    this.addMoreIcons();
  }

  private addMoreIcons(): void {
    const icons = [
      {
        id: 'play',
        name: 'Play',
        category: IconCategory.ACTIONS,
        semanticMeaning: 'Play, start, begin, video play',
        simpleVariant: '<polygon points="8,5 8,19 19,12" fill="currentColor"/>',
        playfulVariant: '<polygon points="8,5 8,19 19,12" fill="#4ECDC4"/><circle cx="12" cy="12" r="11" stroke="#4ECDC4" stroke-width="2" fill="none"/>',
        recognitionRate: { [AgeGroup.TODDLER]: 0.7, [AgeGroup.ADULT]: 0.95 }
      },
      {
        id: 'search',
        name: 'Search',
        category: IconCategory.ACTIONS,
        semanticMeaning: 'Search, find, look for, magnifying glass',
        simpleVariant: '<circle cx="11" cy="11" r="8" stroke="currentColor" stroke-width="2" fill="none"/><path d="m21 21-4.35-4.35" stroke="currentColor" stroke-width="2"/>',
        playfulVariant: '<circle cx="11" cy="11" r="8" stroke="#45B7D1" stroke-width="3" fill="#E3F2FD"/><path d="m21 21-4.35-4.35" stroke="#45B7D1" stroke-width="3"/>',
        recognitionRate: { [AgeGroup.EARLY_ELEMENTARY]: 0.8, [AgeGroup.ADULT]: 0.98 }
      }
    ];

    icons.forEach(iconData => {
      this.iconLibrary.set(iconData.id, {
        id: iconData.id,
        name: iconData.name,
        category: iconData.category,
        variants: [
          {
            style: IconStyle.OUTLINE,
            svgPath: iconData.simpleVariant,
            size: { width: 24, height: 24 },
            complexity: 0.3
          },
          {
            style: IconStyle.PLAYFUL,
            svgPath: iconData.playfulVariant,
            size: { width: 24, height: 24 },
            complexity: 0.4
          }
        ],
        semanticMeaning: iconData.semanticMeaning,
        ageAppropriate: {},
        culturalVariants: {},
        accessibility: {
          altText: iconData.name,
          description: `${iconData.name} icon`
        },
        cognitiveLoad: 0.3,
        recognitionRate: iconData.recognitionRate
      });
    });
  }

  private initializeConceptMappings(): void {
    this.conceptMappings.set('home', ['home']);
    this.conceptMappings.set('house', ['home']);
    this.conceptMappings.set('main', ['home']);
    this.conceptMappings.set('start', ['home', 'play']);
    this.conceptMappings.set('play', ['play']);
    this.conceptMappings.set('video', ['play']);
    this.conceptMappings.set('begin', ['play']);
    this.conceptMappings.set('search', ['search']);
    this.conceptMappings.set('find', ['search']);
    this.conceptMappings.set('look', ['search']);
  }

  private getDefaultStyle(ageGroup: AgeGroup): IconStyle {
    switch (ageGroup) {
      case AgeGroup.TODDLER:
      case AgeGroup.PRESCHOOL:
        return IconStyle.COLORFUL;
      case AgeGroup.EARLY_ELEMENTARY:
      case AgeGroup.LATE_ELEMENTARY:
        return IconStyle.PLAYFUL;
      case AgeGroup.MIDDLE_SCHOOL:
        return IconStyle.FILLED;
      case AgeGroup.HIGH_SCHOOL:
      case AgeGroup.YOUNG_ADULT:
        return IconStyle.OUTLINE;
      case AgeGroup.ADULT:
        return IconStyle.PROFESSIONAL;
      case AgeGroup.SENIOR:
        return IconStyle.FILLED;
      default:
        return IconStyle.OUTLINE;
    }
  }

  private getDefaultSize(ageGroup: AgeGroup): IconSize {
    switch (ageGroup) {
      case AgeGroup.TODDLER:
      case AgeGroup.PRESCHOOL:
        return IconSize.HUGE;
      case AgeGroup.EARLY_ELEMENTARY:
        return IconSize.EXTRA_LARGE;
      case AgeGroup.LATE_ELEMENTARY:
      case AgeGroup.MIDDLE_SCHOOL:
        return IconSize.LARGE;
      case AgeGroup.SENIOR:
        return IconSize.LARGE;
      default:
        return IconSize.MEDIUM;
    }
  }

  private getDefaultColorScheme(ageGroup: AgeGroup): ColorScheme {
    switch (ageGroup) {
      case AgeGroup.TODDLER:
      case AgeGroup.PRESCHOOL:
        return ColorScheme.RAINBOW;
      case AgeGroup.EARLY_ELEMENTARY:
      case AgeGroup.LATE_ELEMENTARY:
        return ColorScheme.FULL_COLOR;
      case AgeGroup.SENIOR:
        return ColorScheme.HIGH_CONTRAST;
      default:
        return ColorScheme.MINIMAL_COLOR;
    }
  }

  private getDefaultAnimationLevel(ageGroup: AgeGroup): AnimationLevel {
    switch (ageGroup) {
      case AgeGroup.TODDLER:
      case AgeGroup.PRESCHOOL:
        return AnimationLevel.PLAYFUL;
      case AgeGroup.EARLY_ELEMENTARY:
        return AnimationLevel.PROMINENT;
      case AgeGroup.LATE_ELEMENTARY:
      case AgeGroup.MIDDLE_SCHOOL:
        return AnimationLevel.MODERATE;
      case AgeGroup.SENIOR:
        return AnimationLevel.NONE;
      default:
        return AnimationLevel.SUBTLE;
    }
  }

  private getDefaultAccessibilityOptions(ageGroup: AgeGroup): IconAccessibilityOptions {
    return {
      highContrast: ageGroup === AgeGroup.SENIOR,
      altTextRequired: true,
      soundEffects: [AgeGroup.TODDLER, AgeGroup.PRESCHOOL].includes(ageGroup),
      hoverDescriptions: ageGroup !== AgeGroup.TODDLER && ageGroup !== AgeGroup.PRESCHOOL,
      largeClickTargets: [AgeGroup.TODDLER, AgeGroup.PRESCHOOL, AgeGroup.SENIOR].includes(ageGroup),
      reducedMotion: ageGroup === AgeGroup.SENIOR,
      colorBlindFriendly: true
    };
  }

  private getDefaultCognitiveLevel(ageGroup: AgeGroup): number {
    switch (ageGroup) {
      case AgeGroup.TODDLER: return 0.1;
      case AgeGroup.PRESCHOOL: return 0.2;
      case AgeGroup.EARLY_ELEMENTARY: return 0.3;
      case AgeGroup.LATE_ELEMENTARY: return 0.5;
      case AgeGroup.MIDDLE_SCHOOL: return 0.7;
      case AgeGroup.HIGH_SCHOOL: return 0.8;
      case AgeGroup.YOUNG_ADULT: return 0.9;
      case AgeGroup.ADULT: return 1.0;
      case AgeGroup.SENIOR: return 0.6;
      default: return 0.5;
    }
  }

  private isAgeAppropriate(icon: IconDefinition, ageGroup: AgeGroup): boolean {
    // Check if cognitive load is appropriate
    const cognitiveLevel = this.getDefaultCognitiveLevel(ageGroup);
    if (icon.cognitiveLoad > cognitiveLevel + 0.2) return false;

    // Check recognition rate
    const recognitionRate = icon.recognitionRate[ageGroup];
    if (recognitionRate && recognitionRate < 0.3) return false;

    return true;
  }

  private calculateAppropriateness(icon: IconDefinition, config: IconConfiguration): number {
    let score = 0;

    // Cognitive load appropriateness
    const cognitiveMatch = 1 - Math.abs(icon.cognitiveLoad - config.cognitiveLevel);
    score += cognitiveMatch * 0.4;

    // Recognition rate
    const recognitionRate = icon.recognitionRate[config.ageGroup] || 0.5;
    score += recognitionRate * 0.6;

    return Math.min(1, score);
  }

  private calculateConceptMatch(concept: string, icon: IconDefinition): number {
    const lowerConcept = concept.toLowerCase();
    const semanticWords = icon.semanticMeaning.toLowerCase().split(/[,\s]+/);
    
    if (semanticWords.includes(lowerConcept)) return 1.0;
    if (semanticWords.some(word => word.includes(lowerConcept) || lowerConcept.includes(word))) return 0.8;
    
    return 0.3; // Default partial match
  }

  private findSimilarConcepts(concept: string): string[] {
    // Simple similarity - in real implementation would use word embeddings
    const synonyms: Record<string, string[]> = {
      'home': ['house', 'main', 'start'],
      'play': ['start', 'begin', 'video'],
      'search': ['find', 'look', 'locate'],
      'save': ['store', 'keep', 'preserve'],
      'delete': ['remove', 'trash', 'destroy']
    };

    return synonyms[concept.toLowerCase()] || [];
  }

  private getColorPalette(scheme: ColorScheme): { primary: string; secondary?: string } {
    switch (scheme) {
      case ColorScheme.MONOCHROME:
        return { primary: '#000000' };
      case ColorScheme.HIGH_CONTRAST:
        return { primary: '#000000', secondary: '#FFFFFF' };
      case ColorScheme.FULL_COLOR:
        return { primary: '#4A90E2', secondary: '#7ED321' };
      case ColorScheme.RAINBOW:
        return { primary: '#FF6B6B', secondary: '#4ECDC4' };
      default:
        return { primary: '#666666' };
    }
  }

  private generateFallbackIcon(request: IconRequest, config: IconConfiguration): IconResult {
    // Generate a simple text-based fallback
    const letter = request.concept.charAt(0).toUpperCase();
    const size = 24;
    
    const fallbackSVG = `
      <svg width="${size}" height="${size}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/>
        <text x="12" y="16" text-anchor="middle" font-size="12" font-family="sans-serif" fill="currentColor">${letter}</text>
      </svg>
    `;

    return {
      iconId: 'fallback',
      variant: {
        style: IconStyle.OUTLINE,
        svgPath: fallbackSVG,
        size: { width: size, height: size },
        complexity: 0.1
      },
      renderedSVG: fallbackSVG,
      accessibility: {
        altText: request.fallbackText || request.concept,
        ariaLabel: `${request.concept} (fallback icon)`,
        role: 'img'
      },
      metadata: {
        confidence: 0.3,
        appropriateness: 0.8,
        recognitionLikelihood: 0.6
      }
    };
  }

  private generateCacheKey(userId: string, request: IconRequest): string {
    return `${userId}:${request.concept}:${request.context || ''}:${request.importance}`;
  }
}

export const iconSystem = new IconSystem();