import { EventEmitter } from 'events';
import { AgeGroup, AgeDetectionResult } from '../age-detection/age-detector';

export interface UIConfiguration {
  userId: string;
  ageGroup: AgeGroup;
  complexityLevel: number; // 0-1
  vocabularyLevel: number; // 0-1
  theme: string;
  accessibility: AccessibilityOptions;
  layout: LayoutConfiguration;
  interactions: InteractionConfiguration;
  content: ContentConfiguration;
  navigation: NavigationConfiguration;
}

export interface AccessibilityOptions {
  fontSize: number; // 12-24px
  highContrast: boolean;
  reducedMotion: boolean;
  screenReader: boolean;
  colorBlindSupport: boolean;
  dyslexiaSupport: boolean;
  focusIndicators: 'subtle' | 'prominent' | 'high-visibility';
  soundEffects: boolean;
  hapticFeedback: boolean;
}

export interface LayoutConfiguration {
  density: 'compact' | 'comfortable' | 'spacious';
  gridSystem: 'simple' | 'standard' | 'advanced';
  sidebars: boolean;
  headerStyle: 'minimal' | 'standard' | 'full';
  footerVisible: boolean;
  panelLayout: 'single' | 'dual' | 'multi';
  responsiveBreakpoints: ResponsiveConfig;
}

export interface InteractionConfiguration {
  clickTargetSize: 'small' | 'medium' | 'large' | 'extra-large';
  hoverEffects: 'none' | 'subtle' | 'prominent';
  animationDuration: number; // milliseconds
  feedbackStyle: 'minimal' | 'standard' | 'rich';
  gestureSupport: boolean;
  dragAndDrop: boolean;
  contextMenus: boolean;
  shortcuts: boolean;
  tooltips: 'none' | 'basic' | 'detailed';
}

export interface ContentConfiguration {
  textDensity: 'sparse' | 'normal' | 'dense';
  imageSize: 'small' | 'medium' | 'large';
  iconStyle: 'outline' | 'filled' | 'colorful' | 'animated';
  contentFiltering: boolean;
  readingAssistance: boolean;
  translationSupport: boolean;
  summaryGeneration: boolean;
}

export interface NavigationConfiguration {
  style: 'breadcrumb' | 'tabs' | 'sidebar' | 'floating' | 'wizard';
  depth: number; // max navigation levels
  backButton: boolean;
  homeButton: boolean;
  searchIntegration: boolean;
  favourites: boolean;
  recentItems: boolean;
}

export interface ResponsiveConfig {
  mobile: number;
  tablet: number;
  desktop: number;
  ultrawide: number;
}

export interface TransformationRule {
  condition: (config: UIConfiguration) => boolean;
  transform: (element: UIElement) => UIElement;
  priority: number;
  description: string;
}

export interface UIElement {
  id: string;
  type: ElementType;
  props: Record<string, any>;
  children?: UIElement[];
  styles?: CSSProperties;
  metadata?: ElementMetadata;
}

export enum ElementType {
  BUTTON = 'button',
  INPUT = 'input',
  TEXT = 'text',
  IMAGE = 'image',
  CONTAINER = 'container',
  NAVIGATION = 'navigation',
  FORM = 'form',
  LIST = 'list',
  CARD = 'card',
  MODAL = 'modal',
  DROPDOWN = 'dropdown',
  SLIDER = 'slider',
  CHECKBOX = 'checkbox',
  RADIO = 'radio',
  TOGGLE = 'toggle',
  TAB = 'tab',
  ACCORDION = 'accordion',
  TOOLTIP = 'tooltip',
  NOTIFICATION = 'notification',
  CHART = 'chart',
  TABLE = 'table'
}

export interface ElementMetadata {
  importance: 'low' | 'medium' | 'high' | 'critical';
  complexity: number; // 0-1
  userGroup: AgeGroup[];
  accessibilityLevel: number; // 0-1
  cognitiveLoad: number; // 0-1
}

export interface CSSProperties {
  [key: string]: string | number;
}

export class UITransformer extends EventEmitter {
  private configurations: Map<string, UIConfiguration> = new Map();
  private transformationRules: TransformationRule[] = [];
  private themeLibrary: Map<string, ThemeDefinition> = new Map();

  constructor() {
    super();
    this.initializeDefaultRules();
    this.initializeThemes();
  }

  public createConfiguration(
    userId: string,
    ageResult: AgeDetectionResult,
    preferences?: Partial<UIConfiguration>
  ): UIConfiguration {
    const baseConfig = this.generateBaseConfiguration(ageResult);
    const config: UIConfiguration = {
      ...baseConfig,
      userId,
      ...preferences
    };

    this.configurations.set(userId, config);
    this.emit('configurationCreated', { userId, config });

    return config;
  }

  public updateConfiguration(
    userId: string,
    updates: Partial<UIConfiguration>
  ): UIConfiguration | null {
    const existing = this.configurations.get(userId);
    if (!existing) return null;

    const updated: UIConfiguration = { ...existing, ...updates };
    this.configurations.set(userId, updated);
    this.emit('configurationUpdated', { userId, config: updated });

    return updated;
  }

  public transformElement(userId: string, element: UIElement): UIElement {
    const config = this.configurations.get(userId);
    if (!config) return element;

    let transformed = { ...element };

    // Apply transformation rules in priority order
    const applicableRules = this.transformationRules
      .filter(rule => rule.condition(config))
      .sort((a, b) => b.priority - a.priority);

    for (const rule of applicableRules) {
      transformed = rule.transform(transformed);
    }

    // Apply theme-specific transformations
    transformed = this.applyThemeTransformation(transformed, config);

    // Apply accessibility transformations
    transformed = this.applyAccessibilityTransformation(transformed, config);

    return transformed;
  }

  public transformPage(userId: string, page: UIElement[]): UIElement[] {
    return page.map(element => this.transformElement(userId, element));
  }

  public generateCSS(userId: string): string {
    const config = this.configurations.get(userId);
    if (!config) return '';

    const theme = this.themeLibrary.get(config.theme);
    if (!theme) return '';

    return this.compileCSSFromTheme(theme, config);
  }

  public async transitionToConfiguration(
    userId: string,
    newConfig: Partial<UIConfiguration>,
    duration: number = 300
  ): Promise<void> {
    const currentConfig = this.configurations.get(userId);
    if (!currentConfig) return;

    const targetConfig = { ...currentConfig, ...newConfig };
    
    // Create transition steps
    const steps = this.generateTransitionSteps(currentConfig, targetConfig, duration);
    
    this.emit('transitionStart', { userId, from: currentConfig, to: targetConfig });

    // Execute transition
    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      this.configurations.set(userId, step);
      this.emit('transitionStep', { userId, step: i, config: step });
      
      await this.delay(duration / steps.length);
    }

    this.configurations.set(userId, targetConfig);
    this.emit('transitionComplete', { userId, config: targetConfig });
  }

  private generateBaseConfiguration(ageResult: AgeDetectionResult): Omit<UIConfiguration, 'userId'> {
    const { ageGroup, recommendations } = ageResult;
    
    return {
      ageGroup,
      complexityLevel: recommendations.interfaceComplexity,
      vocabularyLevel: recommendations.vocabularyLevel,
      theme: recommendations.suggestedTheme,
      accessibility: this.generateAccessibilityOptions(ageGroup, ageResult.estimatedAge),
      layout: this.generateLayoutConfiguration(ageGroup, recommendations.interfaceComplexity),
      interactions: this.generateInteractionConfiguration(ageGroup, ageResult.estimatedAge),
      content: this.generateContentConfiguration(ageGroup, recommendations.vocabularyLevel),
      navigation: this.generateNavigationConfiguration(ageGroup, recommendations.interfaceComplexity)
    };
  }

  private generateAccessibilityOptions(ageGroup: AgeGroup, age: number): AccessibilityOptions {
    const isYoung = [AgeGroup.TODDLER, AgeGroup.PRESCHOOL, AgeGroup.EARLY_ELEMENTARY].includes(ageGroup);
    const isSenior = ageGroup === AgeGroup.SENIOR;

    return {
      fontSize: isYoung ? 18 : isSenior ? 20 : 16,
      highContrast: isSenior,
      reducedMotion: isSenior || age < 6,
      screenReader: false, // User preference
      colorBlindSupport: true,
      dyslexiaSupport: isYoung || age < 12,
      focusIndicators: isYoung ? 'high-visibility' : isSenior ? 'prominent' : 'subtle',
      soundEffects: isYoung,
      hapticFeedback: age < 25
    };
  }

  private generateLayoutConfiguration(ageGroup: AgeGroup, complexity: number): LayoutConfiguration {
    const isYoung = [AgeGroup.TODDLER, AgeGroup.PRESCHOOL, AgeGroup.EARLY_ELEMENTARY].includes(ageGroup);
    const isChild = [AgeGroup.LATE_ELEMENTARY, AgeGroup.MIDDLE_SCHOOL].includes(ageGroup);

    return {
      density: isYoung ? 'spacious' : complexity < 0.5 ? 'comfortable' : 'compact',
      gridSystem: complexity < 0.3 ? 'simple' : complexity < 0.7 ? 'standard' : 'advanced',
      sidebars: complexity > 0.6 && !isYoung,
      headerStyle: isYoung ? 'minimal' : complexity < 0.5 ? 'standard' : 'full',
      footerVisible: !isYoung,
      panelLayout: complexity < 0.3 ? 'single' : complexity < 0.7 ? 'dual' : 'multi',
      responsiveBreakpoints: {
        mobile: 768,
        tablet: 1024,
        desktop: 1440,
        ultrawide: 1920
      }
    };
  }

  private generateInteractionConfiguration(ageGroup: AgeGroup, age: number): InteractionConfiguration {
    const isVeryYoung = age < 7;
    const isYoung = age < 13;
    const isSenior = age >= 65;

    return {
      clickTargetSize: isVeryYoung ? 'extra-large' : isYoung || isSenior ? 'large' : 'medium',
      hoverEffects: isVeryYoung ? 'prominent' : age < 18 ? 'prominent' : 'subtle',
      animationDuration: isVeryYoung ? 600 : isSenior ? 400 : 300,
      feedbackStyle: isVeryYoung ? 'rich' : isYoung ? 'standard' : 'minimal',
      gestureSupport: age < 30,
      dragAndDrop: age >= 7 && age < 65,
      contextMenus: age >= 13,
      shortcuts: age >= 16,
      tooltips: isYoung ? 'detailed' : age >= 18 ? 'basic' : 'none'
    };
  }

  private generateContentConfiguration(ageGroup: AgeGroup, vocabularyLevel: number): ContentConfiguration {
    const isYoung = [AgeGroup.TODDLER, AgeGroup.PRESCHOOL, AgeGroup.EARLY_ELEMENTARY].includes(ageGroup);

    return {
      textDensity: vocabularyLevel < 0.3 ? 'sparse' : vocabularyLevel < 0.7 ? 'normal' : 'dense',
      imageSize: isYoung ? 'large' : 'medium',
      iconStyle: isYoung ? 'colorful' : vocabularyLevel < 0.5 ? 'filled' : 'outline',
      contentFiltering: [AgeGroup.TODDLER, AgeGroup.PRESCHOOL, AgeGroup.EARLY_ELEMENTARY, AgeGroup.LATE_ELEMENTARY].includes(ageGroup),
      readingAssistance: vocabularyLevel < 0.5,
      translationSupport: true,
      summaryGeneration: vocabularyLevel < 0.4
    };
  }

  private generateNavigationConfiguration(ageGroup: AgeGroup, complexity: number): NavigationConfiguration {
    const isVeryYoung = [AgeGroup.TODDLER, AgeGroup.PRESCHOOL].includes(ageGroup);
    const isYoung = [AgeGroup.EARLY_ELEMENTARY, AgeGroup.LATE_ELEMENTARY].includes(ageGroup);

    return {
      style: isVeryYoung ? 'floating' : isYoung ? 'tabs' : complexity < 0.5 ? 'breadcrumb' : 'sidebar',
      depth: isVeryYoung ? 1 : isYoung ? 2 : complexity < 0.7 ? 3 : 5,
      backButton: true,
      homeButton: isYoung || complexity < 0.5,
      searchIntegration: !isVeryYoung,
      favourites: complexity > 0.3,
      recentItems: complexity > 0.5
    };
  }

  private initializeDefaultRules(): void {
    // Button transformation rules
    this.transformationRules.push({
      condition: (config) => config.ageGroup === AgeGroup.TODDLER || config.ageGroup === AgeGroup.PRESCHOOL,
      transform: (element) => {
        if (element.type === ElementType.BUTTON) {
          return {
            ...element,
            styles: {
              ...element.styles,
              minHeight: '60px',
              minWidth: '120px',
              borderRadius: '15px',
              fontSize: '20px',
              fontWeight: 'bold',
              boxShadow: '0 4px 8px rgba(0,0,0,0.2)',
              transform: 'scale(1)',
              transition: 'transform 0.2s ease'
            },
            props: {
              ...element.props,
              onMouseEnter: () => { /* scale animation */ },
              onMouseLeave: () => { /* reset animation */ }
            }
          };
        }
        return element;
      },
      priority: 100,
      description: 'Large, colorful buttons for very young users'
    });

    // Text simplification rule
    this.transformationRules.push({
      condition: (config) => config.vocabularyLevel < 0.4,
      transform: (element) => {
        if (element.type === ElementType.TEXT) {
          return {
            ...element,
            styles: {
              ...element.styles,
              fontSize: '18px',
              lineHeight: '1.8',
              letterSpacing: '0.5px'
            }
          };
        }
        return element;
      },
      priority: 80,
      description: 'Simplified text for low vocabulary levels'
    });

    // Senior accessibility rule
    this.transformationRules.push({
      condition: (config) => config.ageGroup === AgeGroup.SENIOR,
      transform: (element) => {
        return {
          ...element,
          styles: {
            ...element.styles,
            fontSize: element.styles?.fontSize ? `calc(${element.styles.fontSize} * 1.2)` : '18px',
            contrast: 'high'
          }
        };
      },
      priority: 90,
      description: 'Enhanced readability for senior users'
    });
  }

  private initializeThemes(): void {
    // Playful theme for very young users
    this.themeLibrary.set('playful', {
      name: 'Playful',
      colors: {
        primary: '#FF6B6B',
        secondary: '#4ECDC4',
        accent: '#45B7D1',
        background: '#F8F9FA',
        surface: '#FFFFFF',
        text: '#2C3E50',
        textSecondary: '#7F8C8D'
      },
      typography: {
        fontFamily: 'Comic Sans MS, cursive',
        headingSize: '24px',
        bodySize: '18px',
        lineHeight: 1.6
      },
      spacing: {
        unit: 8,
        small: 16,
        medium: 24,
        large: 32
      },
      borderRadius: '15px',
      shadows: {
        small: '0 2px 4px rgba(0,0,0,0.1)',
        medium: '0 4px 8px rgba(0,0,0,0.15)',
        large: '0 8px 16px rgba(0,0,0,0.2)'
      }
    });

    // Professional theme for adults
    this.themeLibrary.set('professional', {
      name: 'Professional',
      colors: {
        primary: '#2563EB',
        secondary: '#64748B',
        accent: '#059669',
        background: '#F8FAFC',
        surface: '#FFFFFF',
        text: '#0F172A',
        textSecondary: '#475569'
      },
      typography: {
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
        headingSize: '20px',
        bodySize: '14px',
        lineHeight: 1.5
      },
      spacing: {
        unit: 4,
        small: 8,
        medium: 16,
        large: 24
      },
      borderRadius: '6px',
      shadows: {
        small: '0 1px 3px rgba(0,0,0,0.1)',
        medium: '0 4px 6px rgba(0,0,0,0.1)',
        large: '0 10px 15px rgba(0,0,0,0.1)'
      }
    });
  }

  private applyThemeTransformation(element: UIElement, config: UIConfiguration): UIElement {
    const theme = this.themeLibrary.get(config.theme);
    if (!theme) return element;

    return {
      ...element,
      styles: {
        ...element.styles,
        fontFamily: theme.typography.fontFamily,
        borderRadius: theme.borderRadius,
        // Apply theme-specific styles based on element type
      }
    };
  }

  private applyAccessibilityTransformation(element: UIElement, config: UIConfiguration): UIElement {
    let transformed = { ...element };

    if (config.accessibility.highContrast) {
      transformed.styles = {
        ...transformed.styles,
        filter: 'contrast(1.5)'
      };
    }

    if (config.accessibility.reducedMotion) {
      transformed.styles = {
        ...transformed.styles,
        animation: 'none',
        transition: 'none'
      };
    }

    return transformed;
  }

  private compileCSSFromTheme(theme: ThemeDefinition, config: UIConfiguration): string {
    return `
      :root {
        --primary-color: ${theme.colors.primary};
        --secondary-color: ${theme.colors.secondary};
        --accent-color: ${theme.colors.accent};
        --background-color: ${theme.colors.background};
        --surface-color: ${theme.colors.surface};
        --text-color: ${theme.colors.text};
        --text-secondary-color: ${theme.colors.textSecondary};
        --font-family: ${theme.typography.fontFamily};
        --heading-size: ${theme.typography.headingSize};
        --body-size: ${theme.typography.bodySize};
        --line-height: ${theme.typography.lineHeight};
        --border-radius: ${theme.borderRadius};
        --spacing-unit: ${theme.spacing.unit}px;
        --spacing-small: ${theme.spacing.small}px;
        --spacing-medium: ${theme.spacing.medium}px;
        --spacing-large: ${theme.spacing.large}px;
        --shadow-small: ${theme.shadows.small};
        --shadow-medium: ${theme.shadows.medium};
        --shadow-large: ${theme.shadows.large};
      }

      body {
        font-family: var(--font-family);
        font-size: var(--body-size);
        line-height: var(--line-height);
        color: var(--text-color);
        background-color: var(--background-color);
        ${config.accessibility.reducedMotion ? 'transition: none;' : ''}
        ${config.accessibility.highContrast ? 'filter: contrast(1.5);' : ''}
      }

      .ui-button {
        min-height: ${config.interactions.clickTargetSize === 'extra-large' ? '60px' : 
                     config.interactions.clickTargetSize === 'large' ? '48px' : 
                     config.interactions.clickTargetSize === 'medium' ? '40px' : '32px'};
        border-radius: var(--border-radius);
        transition: ${config.accessibility.reducedMotion ? 'none' : 'all 0.2s ease'};
      }

      .ui-text {
        font-size: ${config.accessibility.fontSize}px;
        ${config.accessibility.dyslexiaSupport ? 'font-family: OpenDyslexic, var(--font-family);' : ''}
      }
    `;
  }

  private generateTransitionSteps(
    from: UIConfiguration,
    to: UIConfiguration,
    duration: number
  ): UIConfiguration[] {
    const steps = 10;
    const result: UIConfiguration[] = [];

    for (let i = 1; i <= steps; i++) {
      const progress = i / steps;
      result.push({
        ...from,
        complexityLevel: this.lerp(from.complexityLevel, to.complexityLevel, progress),
        vocabularyLevel: this.lerp(from.vocabularyLevel, to.vocabularyLevel, progress),
        accessibility: {
          ...from.accessibility,
          fontSize: Math.round(this.lerp(from.accessibility.fontSize, to.accessibility.fontSize, progress))
        }
      });
    }

    return result;
  }

  private lerp(start: number, end: number, progress: number): number {
    return start + (end - start) * progress;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

interface ThemeDefinition {
  name: string;
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    surface: string;
    text: string;
    textSecondary: string;
  };
  typography: {
    fontFamily: string;
    headingSize: string;
    bodySize: string;
    lineHeight: number;
  };
  spacing: {
    unit: number;
    small: number;
    medium: number;
    large: number;
  };
  borderRadius: string;
  shadows: {
    small: string;
    medium: string;
    large: string;
  };
}

export const uiTransformer = new UITransformer();