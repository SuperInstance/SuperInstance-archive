import { ThemeMode } from '@/types';

export interface AdaptiveThemeConfig {
  autoAdjustBrightness: boolean;
  timeBasedThemes: boolean;
  locationBasedThemes: boolean;
  moodBasedThemes: boolean;
  seasonalThemes: boolean;
  weatherBasedThemes: boolean;
}

export interface ThemeColors {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  surface: string;
  text: string;
  textSecondary: string;
  border: string;
  success: string;
  warning: string;
  error: string;
  info: string;
}

export interface AdaptiveTheme {
  name: string;
  mode: 'light' | 'dark';
  colors: ThemeColors;
  gradients: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  conditions?: {
    timeRange?: [number, number]; // Hours in 24h format
    season?: 'spring' | 'summer' | 'autumn' | 'winter';
    weather?: 'sunny' | 'cloudy' | 'rainy' | 'snowy';
    mood?: 'happy' | 'calm' | 'focused' | 'melancholy';
  };
}

// Predefined themes
export const adaptiveThemes: AdaptiveTheme[] = [
  {
    name: 'Dawn',
    mode: 'light',
    colors: {
      primary: '#ff6b6b',
      secondary: '#feca57',
      accent: '#ff9ff3',
      background: '#fff5f5',
      surface: '#fef5e7',
      text: '#2d3436',
      textSecondary: '#636e72',
      border: '#e17055',
      success: '#00b894',
      warning: '#fdcb6e',
      error: '#e84393',
      info: '#74b9ff',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #ff6b6b 0%, #feca57 100%)',
      secondary: 'linear-gradient(135deg, #feca57 0%, #ff9ff3 100%)',
      accent: 'linear-gradient(135deg, #ff9ff3 0%, #ff6b6b 100%)',
      background: 'linear-gradient(135deg, #fff5f5 0%, #fef5e7 100%)',
    },
    shadows: {
      sm: '0 1px 3px rgba(255, 107, 107, 0.12)',
      md: '0 4px 6px rgba(255, 107, 107, 0.16)',
      lg: '0 10px 15px rgba(255, 107, 107, 0.20)',
      xl: '0 20px 25px rgba(255, 107, 107, 0.25)',
    },
    conditions: {
      timeRange: [5, 8],
      season: 'spring',
    },
  },
  {
    name: 'Daylight',
    mode: 'light',
    colors: {
      primary: '#0984e3',
      secondary: '#00b894',
      accent: '#6c5ce7',
      background: '#ffffff',
      surface: '#f8f9fa',
      text: '#2d3436',
      textSecondary: '#636e72',
      border: '#ddd',
      success: '#00b894',
      warning: '#fdcb6e',
      error: '#e84393',
      info: '#74b9ff',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #0984e3 0%, #00b894 100%)',
      secondary: 'linear-gradient(135deg, #00b894 0%, #6c5ce7 100%)',
      accent: 'linear-gradient(135deg, #6c5ce7 0%, #0984e3 100%)',
      background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)',
    },
    shadows: {
      sm: '0 1px 3px rgba(9, 132, 227, 0.12)',
      md: '0 4px 6px rgba(9, 132, 227, 0.16)',
      lg: '0 10px 15px rgba(9, 132, 227, 0.20)',
      xl: '0 20px 25px rgba(9, 132, 227, 0.25)',
    },
    conditions: {
      timeRange: [8, 18],
      weather: 'sunny',
    },
  },
  {
    name: 'Sunset',
    mode: 'light',
    colors: {
      primary: '#e17055',
      secondary: '#fdcb6e',
      accent: '#fd79a8',
      background: '#ffeaa7',
      surface: '#fab1a0',
      text: '#2d3436',
      textSecondary: '#636e72',
      border: '#e17055',
      success: '#00b894',
      warning: '#fdcb6e',
      error: '#e84393',
      info: '#74b9ff',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #e17055 0%, #fdcb6e 100%)',
      secondary: 'linear-gradient(135deg, #fdcb6e 0%, #fd79a8 100%)',
      accent: 'linear-gradient(135deg, #fd79a8 0%, #e17055 100%)',
      background: 'linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%)',
    },
    shadows: {
      sm: '0 1px 3px rgba(225, 112, 85, 0.12)',
      md: '0 4px 6px rgba(225, 112, 85, 0.16)',
      lg: '0 10px 15px rgba(225, 112, 85, 0.20)',
      xl: '0 20px 25px rgba(225, 112, 85, 0.25)',
    },
    conditions: {
      timeRange: [18, 20],
      season: 'summer',
    },
  },
  {
    name: 'Twilight',
    mode: 'dark',
    colors: {
      primary: '#74b9ff',
      secondary: '#a29bfe',
      accent: '#fd79a8',
      background: '#2d3436',
      surface: '#636e72',
      text: '#ddd',
      textSecondary: '#b2bec3',
      border: '#636e72',
      success: '#00b894',
      warning: '#fdcb6e',
      error: '#e84393',
      info: '#74b9ff',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #74b9ff 0%, #a29bfe 100%)',
      secondary: 'linear-gradient(135deg, #a29bfe 0%, #fd79a8 100%)',
      accent: 'linear-gradient(135deg, #fd79a8 0%, #74b9ff 100%)',
      background: 'linear-gradient(135deg, #2d3436 0%, #636e72 100%)',
    },
    shadows: {
      sm: '0 1px 3px rgba(0, 0, 0, 0.3)',
      md: '0 4px 6px rgba(0, 0, 0, 0.4)',
      lg: '0 10px 15px rgba(0, 0, 0, 0.5)',
      xl: '0 20px 25px rgba(0, 0, 0, 0.6)',
    },
    conditions: {
      timeRange: [20, 22],
    },
  },
  {
    name: 'Midnight',
    mode: 'dark',
    colors: {
      primary: '#6c5ce7',
      secondary: '#a29bfe',
      accent: '#fd79a8',
      background: '#0f0f23',
      surface: '#1a1a2e',
      text: '#eee',
      textSecondary: '#b2bec3',
      border: '#16213e',
      success: '#00b894',
      warning: '#fdcb6e',
      error: '#e84393',
      info: '#74b9ff',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%)',
      secondary: 'linear-gradient(135deg, #a29bfe 0%, #fd79a8 100%)',
      accent: 'linear-gradient(135deg, #fd79a8 0%, #6c5ce7 100%)',
      background: 'linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%)',
    },
    shadows: {
      sm: '0 1px 3px rgba(0, 0, 0, 0.5)',
      md: '0 4px 6px rgba(0, 0, 0, 0.6)',
      lg: '0 10px 15px rgba(0, 0, 0, 0.7)',
      xl: '0 20px 25px rgba(0, 0, 0, 0.8)',
    },
    conditions: {
      timeRange: [22, 5],
    },
  },
  {
    name: 'Forest',
    mode: 'light',
    colors: {
      primary: '#00b894',
      secondary: '#55a3ff',
      accent: '#fdcb6e',
      background: '#f1f2f6',
      surface: '#ecf0f1',
      text: '#2d3436',
      textSecondary: '#636e72',
      border: '#00b894',
      success: '#00b894',
      warning: '#fdcb6e',
      error: '#e84393',
      info: '#74b9ff',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #00b894 0%, #55a3ff 100%)',
      secondary: 'linear-gradient(135deg, #55a3ff 0%, #fdcb6e 100%)',
      accent: 'linear-gradient(135deg, #fdcb6e 0%, #00b894 100%)',
      background: 'linear-gradient(135deg, #f1f2f6 0%, #ecf0f1 100%)',
    },
    shadows: {
      sm: '0 1px 3px rgba(0, 184, 148, 0.12)',
      md: '0 4px 6px rgba(0, 184, 148, 0.16)',
      lg: '0 10px 15px rgba(0, 184, 148, 0.20)',
      xl: '0 20px 25px rgba(0, 184, 148, 0.25)',
    },
    conditions: {
      mood: 'calm',
      season: 'spring',
    },
  },
];

export class AdaptiveThemeManager {
  private config: AdaptiveThemeConfig;
  private currentTheme: AdaptiveTheme;
  private callbacks: Array<(theme: AdaptiveTheme) => void> = [];

  constructor(config: Partial<AdaptiveThemeConfig> = {}) {
    this.config = {
      autoAdjustBrightness: true,
      timeBasedThemes: true,
      locationBasedThemes: false,
      moodBasedThemes: false,
      seasonalThemes: true,
      weatherBasedThemes: false,
      ...config,
    };
    
    this.currentTheme = adaptiveThemes[1]; // Default to Daylight
    this.startAdaptiveUpdates();
  }

  public getCurrentTheme(): AdaptiveTheme {
    return this.currentTheme;
  }

  public setTheme(theme: AdaptiveTheme): void {
    this.currentTheme = theme;
    this.notifyCallbacks();
  }

  public addThemeChangeCallback(callback: (theme: AdaptiveTheme) => void): void {
    this.callbacks.push(callback);
  }

  public removeThemeChangeCallback(callback: (theme: AdaptiveTheme) => void): void {
    this.callbacks = this.callbacks.filter(cb => cb !== callback);
  }

  private notifyCallbacks(): void {
    this.callbacks.forEach(callback => callback(this.currentTheme));
  }

  private startAdaptiveUpdates(): void {
    // Update theme every minute
    setInterval(() => {
      const newTheme = this.determineOptimalTheme();
      if (newTheme.name !== this.currentTheme.name) {
        this.setTheme(newTheme);
      }
    }, 60000);

    // Initial theme determination
    const initialTheme = this.determineOptimalTheme();
    this.setTheme(initialTheme);
  }

  private determineOptimalTheme(): AdaptiveTheme {
    const currentHour = new Date().getHours();
    const currentSeason = this.getCurrentSeason();
    
    // Find themes that match current conditions
    const matchingThemes = adaptiveThemes.filter(theme => {
      if (!theme.conditions) return false;

      let matches = true;

      // Time-based matching
      if (this.config.timeBasedThemes && theme.conditions.timeRange) {
        const [start, end] = theme.conditions.timeRange;
        if (start <= end) {
          matches = matches && (currentHour >= start && currentHour < end);
        } else {
          // Handle overnight range (e.g., 22-5)
          matches = matches && (currentHour >= start || currentHour < end);
        }
      }

      // Season-based matching
      if (this.config.seasonalThemes && theme.conditions.season) {
        matches = matches && (theme.conditions.season === currentSeason);
      }

      return matches;
    });

    // If no specific themes match, fall back to time-based selection
    if (matchingThemes.length === 0) {
      if (currentHour >= 5 && currentHour < 8) return adaptiveThemes[0]; // Dawn
      if (currentHour >= 8 && currentHour < 18) return adaptiveThemes[1]; // Daylight
      if (currentHour >= 18 && currentHour < 20) return adaptiveThemes[2]; // Sunset
      if (currentHour >= 20 && currentHour < 22) return adaptiveThemes[3]; // Twilight
      return adaptiveThemes[4]; // Midnight
    }

    // Return the first matching theme
    return matchingThemes[0];
  }

  private getCurrentSeason(): 'spring' | 'summer' | 'autumn' | 'winter' {
    const month = new Date().getMonth() + 1; // 1-12
    
    if (month >= 3 && month <= 5) return 'spring';
    if (month >= 6 && month <= 8) return 'summer';
    if (month >= 9 && month <= 11) return 'autumn';
    return 'winter';
  }

  public adjustBrightnessForAmbientLight(lightLevel: number): AdaptiveTheme {
    // lightLevel: 0-1 (0 = dark, 1 = bright)
    const adjustedTheme = { ...this.currentTheme };
    
    if (this.config.autoAdjustBrightness) {
      const factor = 0.2 + (lightLevel * 0.8); // 20%-100% brightness
      
      // Adjust colors based on ambient light
      adjustedTheme.colors = {
        ...adjustedTheme.colors,
        background: this.adjustColorBrightness(adjustedTheme.colors.background, factor),
        surface: this.adjustColorBrightness(adjustedTheme.colors.surface, factor),
      };
    }
    
    return adjustedTheme;
  }

  private adjustColorBrightness(color: string, factor: number): string {
    // Simple brightness adjustment - in a real implementation, you'd use a proper color library
    const hex = color.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    
    const adjustedR = Math.round(r * factor);
    const adjustedG = Math.round(g * factor);
    const adjustedB = Math.round(b * factor);
    
    return `#${adjustedR.toString(16).padStart(2, '0')}${adjustedG.toString(16).padStart(2, '0')}${adjustedB.toString(16).padStart(2, '0')}`;
  }

  public getThemeForMood(mood: 'happy' | 'calm' | 'focused' | 'melancholy'): AdaptiveTheme {
    const moodThemes = adaptiveThemes.filter(theme => 
      theme.conditions?.mood === mood
    );
    
    return moodThemes.length > 0 ? moodThemes[0] : this.currentTheme;
  }

  public createCustomTheme(
    name: string,
    baseTheme: AdaptiveTheme,
    customizations: Partial<ThemeColors>
  ): AdaptiveTheme {
    return {
      ...baseTheme,
      name,
      colors: {
        ...baseTheme.colors,
        ...customizations,
      },
    };
  }
}

export const themeManager = new AdaptiveThemeManager();