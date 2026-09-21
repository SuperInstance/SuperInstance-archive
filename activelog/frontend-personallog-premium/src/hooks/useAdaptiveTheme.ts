import { useState, useEffect, useCallback } from 'react';
import { themeManager, AdaptiveTheme, AdaptiveThemeConfig } from '@/utils/themeUtils';
import { useThemeStore } from '@/stores';

export const useAdaptiveTheme = (config?: Partial<AdaptiveThemeConfig>) => {
  const [adaptiveTheme, setAdaptiveTheme] = useState<AdaptiveTheme>(themeManager.getCurrentTheme());
  const [isAutoMode, setIsAutoMode] = useState(false);
  const { mode, setTheme } = useThemeStore();

  // Update theme manager configuration
  useEffect(() => {
    if (config) {
      // Create new theme manager with updated config
      const newManager = new (themeManager.constructor as any)(config);
      Object.setPrototypeOf(themeManager, newManager);
    }
  }, [config]);

  // Listen to theme changes from the adaptive theme manager
  useEffect(() => {
    const handleThemeChange = (theme: AdaptiveTheme) => {
      setAdaptiveTheme(theme);
      
      // Auto-apply theme if in auto mode
      if (isAutoMode) {
        setTheme(theme.mode);
        applyThemeToDocument(theme);
      }
    };

    themeManager.addThemeChangeCallback(handleThemeChange);
    
    return () => {
      themeManager.removeThemeChangeCallback(handleThemeChange);
    };
  }, [isAutoMode, setTheme]);

  // Apply theme colors to CSS custom properties
  const applyThemeToDocument = useCallback((theme: AdaptiveTheme) => {
    const root = document.documentElement;
    
    // Apply colors
    Object.entries(theme.colors).forEach(([key, value]) => {
      root.style.setProperty(`--adaptive-${key}`, value);
    });
    
    // Apply gradients
    Object.entries(theme.gradients).forEach(([key, value]) => {
      root.style.setProperty(`--adaptive-gradient-${key}`, value);
    });
    
    // Apply shadows
    Object.entries(theme.shadows).forEach(([key, value]) => {
      root.style.setProperty(`--adaptive-shadow-${key}`, value);
    });

    // Apply theme name as data attribute
    root.setAttribute('data-adaptive-theme', theme.name.toLowerCase());
  }, []);

  // Enable/disable auto theme mode
  const setAutoMode = useCallback((enabled: boolean) => {
    setIsAutoMode(enabled);
    if (enabled) {
      const currentTheme = themeManager.getCurrentTheme();
      setTheme(currentTheme.mode);
      applyThemeToDocument(currentTheme);
    }
  }, [setTheme, applyThemeToDocument]);

  // Manually set a specific adaptive theme
  const setAdaptiveThemeManual = useCallback((theme: AdaptiveTheme) => {
    themeManager.setTheme(theme);
    setAdaptiveTheme(theme);
    setTheme(theme.mode);
    applyThemeToDocument(theme);
    setIsAutoMode(false);
  }, [setTheme, applyThemeToDocument]);

  // Get theme for specific mood
  const getThemeForMood = useCallback((mood: 'happy' | 'calm' | 'focused' | 'melancholy') => {
    return themeManager.getThemeForMood(mood);
  }, []);

  // Adjust theme based on ambient light (if supported)
  const adjustForAmbientLight = useCallback(async () => {
    if ('AmbientLightSensor' in window) {
      try {
        const sensor = new (window as any).AmbientLightSensor();
        sensor.addEventListener('reading', () => {
          const lightLevel = Math.min(1, Math.max(0, sensor.illuminance / 1000));
          const adjustedTheme = themeManager.adjustBrightnessForAmbientLight(lightLevel);
          setAdaptiveTheme(adjustedTheme);
          applyThemeToDocument(adjustedTheme);
        });
        sensor.start();
        return sensor;
      } catch (error) {
        console.warn('Ambient light sensor not available:', error);
        return null;
      }
    }
    return null;
  }, [applyThemeToDocument]);

  // Get current time-based theme
  const getCurrentTimeTheme = useCallback(() => {
    const hour = new Date().getHours();
    let themeName = 'Daylight';
    
    if (hour >= 5 && hour < 8) themeName = 'Dawn';
    else if (hour >= 8 && hour < 18) themeName = 'Daylight';
    else if (hour >= 18 && hour < 20) themeName = 'Sunset';
    else if (hour >= 20 && hour < 22) themeName = 'Twilight';
    else themeName = 'Midnight';
    
    return themeName;
  }, []);

  // Get theme preview (without applying)
  const previewTheme = useCallback((theme: AdaptiveTheme, duration: number = 3000) => {
    const originalTheme = adaptiveTheme;
    
    // Apply preview theme
    applyThemeToDocument(theme);
    setAdaptiveTheme(theme);
    
    // Revert after duration
    setTimeout(() => {
      applyThemeToDocument(originalTheme);
      setAdaptiveTheme(originalTheme);
    }, duration);
  }, [adaptiveTheme, applyThemeToDocument]);

  // Create custom theme
  const createCustomTheme = useCallback((
    name: string,
    baseTheme: AdaptiveTheme,
    customizations: Partial<AdaptiveTheme['colors']>
  ) => {
    return themeManager.createCustomTheme(name, baseTheme, customizations);
  }, []);

  // Initialize theme on first load
  useEffect(() => {
    applyThemeToDocument(adaptiveTheme);
  }, []);

  return {
    // Current state
    adaptiveTheme,
    isAutoMode,
    currentTimeTheme: getCurrentTimeTheme(),
    
    // Controls
    setAutoMode,
    setAdaptiveTheme: setAdaptiveThemeManual,
    previewTheme,
    
    // Utilities
    getThemeForMood,
    createCustomTheme,
    adjustForAmbientLight,
    
    // Theme application
    applyThemeToDocument,
  };
};

export default useAdaptiveTheme;