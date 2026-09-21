import { useCallback, useRef } from 'react';
import { HapticPattern, HapticType } from '@/types';

// Navigator interface extension for haptic feedback
interface NavigatorWithVibrate {
  vibrate?: (pattern: number | number[]) => boolean;
}

export interface HapticConfig {
  enabled: boolean;
  intensity: number; // 0-1
  respectSystemSettings: boolean;
}

const defaultConfig: HapticConfig = {
  enabled: true,
  intensity: 1,
  respectSystemSettings: true,
};

// Predefined haptic patterns
const hapticPatterns: Record<HapticType, HapticPattern> = {
  light: { type: 'light', duration: 10, intensity: 0.3 },
  medium: { type: 'medium', duration: 20, intensity: 0.6 },
  heavy: { type: 'heavy', duration: 30, intensity: 1.0 },
  selection: { type: 'selection', duration: 5, intensity: 0.2 },
  impact: { type: 'impact', duration: 15, intensity: 0.8 },
  notification: { type: 'notification', duration: 25, intensity: 0.7 },
};

export const useHapticFeedback = (config: Partial<HapticConfig> = {}) => {
  const finalConfig = { ...defaultConfig, ...config };
  const lastFeedbackRef = useRef<number>(0);

  // Check if haptic feedback is supported
  const isSupported = useCallback(() => {
    const nav = navigator as NavigatorWithVibrate;
    return (
      'vibrate' in nav ||
      'webkitVibrate' in nav ||
      (window as any).DeviceMotionEvent !== undefined
    );
  }, []);

  // Check if user prefers reduced motion
  const shouldRespectMotionPreferences = useCallback(() => {
    if (!finalConfig.respectSystemSettings) return false;
    
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    return mediaQuery.matches;
  }, [finalConfig.respectSystemSettings]);

  // Throttle feedback to prevent excessive vibration
  const shouldThrottle = useCallback((minInterval: number = 50) => {
    const now = Date.now();
    if (now - lastFeedbackRef.current < minInterval) {
      return true;
    }
    lastFeedbackRef.current = now;
    return false;
  }, []);

  // Core haptic feedback function
  const triggerHaptic = useCallback((pattern: HapticPattern) => {
    if (!finalConfig.enabled || !isSupported()) return false;
    
    if (shouldRespectMotionPreferences() || shouldThrottle()) return false;

    const nav = navigator as NavigatorWithVibrate;
    const intensity = Math.min(1, pattern.intensity * finalConfig.intensity);
    const duration = Math.round(pattern.duration * intensity);

    try {
      if (nav.vibrate) {
        return nav.vibrate(duration);
      }
      
      // Fallback for older browsers
      if ((nav as any).webkitVibrate) {
        return (nav as any).webkitVibrate(duration);
      }

      // Web API fallback (experimental)
      if ('vibrate' in navigator) {
        return navigator.vibrate(duration);
      }

      return false;
    } catch (error) {
      console.warn('Haptic feedback failed:', error);
      return false;
    }
  }, [finalConfig.enabled, finalConfig.intensity, isSupported, shouldRespectMotionPreferences, shouldThrottle]);

  // Convenient methods for different types of feedback
  const light = useCallback(() => triggerHaptic(hapticPatterns.light), [triggerHaptic]);
  const medium = useCallback(() => triggerHaptic(hapticPatterns.medium), [triggerHaptic]);
  const heavy = useCallback(() => triggerHaptic(hapticPatterns.heavy), [triggerHaptic]);
  const selection = useCallback(() => triggerHaptic(hapticPatterns.selection), [triggerHaptic]);
  const impact = useCallback(() => triggerHaptic(hapticPatterns.impact), [triggerHaptic]);
  const notification = useCallback(() => triggerHaptic(hapticPatterns.notification), [triggerHaptic]);

  // Custom pattern
  const custom = useCallback((pattern: Partial<HapticPattern>) => {
    const fullPattern: HapticPattern = {
      type: 'medium',
      duration: 20,
      intensity: 0.6,
      ...pattern,
    };
    return triggerHaptic(fullPattern);
  }, [triggerHaptic]);

  // Success/error patterns
  const success = useCallback(() => {
    if (!finalConfig.enabled) return false;
    
    // Double tap pattern for success
    const successPattern = [10, 30, 15];
    const nav = navigator as NavigatorWithVibrate;
    
    try {
      if (nav.vibrate) {
        return nav.vibrate(successPattern);
      }
      return false;
    } catch (error) {
      console.warn('Success haptic failed:', error);
      return false;
    }
  }, [finalConfig.enabled]);

  const error = useCallback(() => {
    if (!finalConfig.enabled) return false;
    
    // Triple tap pattern for error
    const errorPattern = [20, 20, 20, 20, 20];
    const nav = navigator as NavigatorWithVibrate;
    
    try {
      if (nav.vibrate) {
        return nav.vibrate(errorPattern);
      }
      return false;
    } catch (error) {
      console.warn('Error haptic failed:', error);
      return false;
    }
  }, [finalConfig.enabled]);

  // Stop any ongoing vibration
  const stop = useCallback(() => {
    const nav = navigator as NavigatorWithVibrate;
    
    try {
      if (nav.vibrate) {
        return nav.vibrate(0);
      }
      return false;
    } catch (error) {
      console.warn('Stop haptic failed:', error);
      return false;
    }
  }, []);

  return {
    // Basic feedback types
    light,
    medium,
    heavy,
    selection,
    impact,
    notification,
    
    // Semantic feedback
    success,
    error,
    
    // Custom and control
    custom,
    stop,
    
    // Utility
    isSupported: isSupported(),
    isEnabled: finalConfig.enabled,
  };
};

export default useHapticFeedback;