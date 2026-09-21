import { Dimensions } from 'react-native';

const { width, height } = Dimensions.get('window');

export const MarineTheme = {
  colors: {
    // Primary marine palette
    navy: '#001f3f',
    deepBlue: '#003366',
    oceanBlue: '#0066cc',
    cyan: '#00b4db',
    seafoam: '#b3e0ff',
    
    // Status colors
    success: '#22c55e',
    warning: '#f59e0b',
    danger: '#ef4444',
    critical: '#dc2626',
    
    // Grays for dark theme
    gray900: '#0f172a',
    gray800: '#1e293b',
    gray700: '#334155',
    gray600: '#475569',
    gray500: '#64748b',
    gray400: '#94a3b8',
    gray300: '#cbd5e1',
    gray200: '#e2e8f0',
    gray100: '#f1f5f9',
    
    // Text colors
    textPrimary: '#f8fafc',
    textSecondary: '#cbd5e1',
    textMuted: '#94a3b8',
    
    // Background colors
    background: '#0f172a',
    surface: '#1e293b',
    surfaceElevated: '#334155',
    
    // Accent colors
    accent: '#3b82f6',
    accentSecondary: '#06b6d4',
    
    // Transparent overlays
    overlay: 'rgba(0, 0, 0, 0.7)',
    overlayLight: 'rgba(0, 0, 0, 0.5)',
    overlayHeavy: 'rgba(0, 0, 0, 0.9)',
    
    // Emergency colors
    mayday: '#dc2626',
    pan: '#f59e0b',
    securite: '#22c55e',
  },
  
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  
  typography: {
    heading1: {
      fontSize: 32,
      fontWeight: '700',
      lineHeight: 40,
    },
    heading2: {
      fontSize: 24,
      fontWeight: '600',
      lineHeight: 32,
    },
    heading3: {
      fontSize: 20,
      fontWeight: '600',
      lineHeight: 28,
    },
    heading4: {
      fontSize: 18,
      fontWeight: '600',
      lineHeight: 24,
    },
    body1: {
      fontSize: 16,
      fontWeight: '400',
      lineHeight: 24,
    },
    body2: {
      fontSize: 14,
      fontWeight: '400',
      lineHeight: 20,
    },
    caption: {
      fontSize: 12,
      fontWeight: '500',
      lineHeight: 16,
    },
    button: {
      fontSize: 16,
      fontWeight: '600',
      lineHeight: 20,
    },
    instrument: {
      fontSize: 28,
      fontWeight: '700',
      lineHeight: 32,
    },
  },
  
  borderRadius: {
    sm: 4,
    md: 8,
    lg: 12,
    xl: 16,
    full: 999,
  },
  
  shadows: {
    sm: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.2,
      shadowRadius: 2,
      elevation: 2,
    },
    md: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.25,
      shadowRadius: 4,
      elevation: 4,
    },
    lg: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.3,
      shadowRadius: 8,
      elevation: 8,
    },
  },
  
  layout: {
    screenWidth: width,
    screenHeight: height,
    isSmallScreen: width < 375,
    isMediumScreen: width >= 375 && width < 768,
    isLargeScreen: width >= 768,
    
    // Touch targets
    minTouchTarget: 44,
    touchTargetLarge: 56,
    touchTargetXL: 72,
    
    // Common measurements
    headerHeight: 56,
    tabBarHeight: 60,
    buttonHeight: 48,
    buttonHeightLarge: 56,
  },
  
  animation: {
    timing: {
      fast: 150,
      normal: 300,
      slow: 500,
    },
    easing: {
      easeInOut: 'ease-in-out',
      easeOut: 'ease-out',
      easeIn: 'ease-in',
    },
  },
  
  // Marine-specific styling
  marine: {
    instrumentBorder: '2px solid rgba(59, 130, 246, 0.3)',
    glowEffect: {
      textShadowColor: '#3b82f6',
      textShadowOffset: { width: 0, height: 0 },
      textShadowRadius: 8,
    },
    emergencyGlow: {
      textShadowColor: '#dc2626',
      textShadowOffset: { width: 0, height: 0 },
      textShadowRadius: 12,
    },
    compassColors: {
      north: '#dc2626',
      east: '#22c55e',
      south: '#3b82f6',
      west: '#f59e0b',
    },
  },
} as const;

export type ThemeType = typeof MarineTheme;