import { Theme } from '@/types';

export const theme: Theme = {
  colors: {
    primary: '#ffd700',
    secondary: '#8b5a3c',
    accent: '#2a2a3e',
    background: '#1a1a2e',
    surface: '#16213e',
    text: '#ffffff',
    textSecondary: '#b0b0b0',
    border: '#3a3a4e',
    error: '#ef4444',
    warning: '#f59e0b',
    success: '#10b981',
    info: '#3b82f6',
    
    // Ability scores
    strength: '#dc2626',
    dexterity: '#16a34a',
    constitution: '#ca8a04',
    intelligence: '#2563eb',
    wisdom: '#7c3aed',
    charisma: '#db2777',
    
    // Item rarities
    common: '#9ca3af',
    uncommon: '#22c55e',
    rare: '#3b82f6',
    veryRare: '#a855f7',
    legendary: '#f59e0b',
    artifact: '#ef4444'
  },
  fonts: {
    regular: 'System',
    medium: 'System',
    bold: 'System',
    sizes: {
      xs: 12,
      sm: 14,
      md: 16,
      lg: 18,
      xl: 20,
      xxl: 24
    }
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32
  },
  borderRadius: {
    sm: 4,
    md: 8,
    lg: 16,
    full: 9999
  }
};

// Utility functions for theme
export const getAbilityColor = (ability: string): string => {
  switch (ability.toLowerCase()) {
    case 'strength': return theme.colors.strength;
    case 'dexterity': return theme.colors.dexterity;
    case 'constitution': return theme.colors.constitution;
    case 'intelligence': return theme.colors.intelligence;
    case 'wisdom': return theme.colors.wisdom;
    case 'charisma': return theme.colors.charisma;
    default: return theme.colors.text;
  }
};

export const getRarityColor = (rarity: string): string => {
  switch (rarity.toLowerCase()) {
    case 'common': return theme.colors.common;
    case 'uncommon': return theme.colors.uncommon;
    case 'rare': return theme.colors.rare;
    case 'very-rare': case 'very rare': return theme.colors.veryRare;
    case 'legendary': return theme.colors.legendary;
    case 'artifact': return theme.colors.artifact;
    default: return theme.colors.common;
  }
};

export const getClassColor = (className: string): string => {
  const classColors: Record<string, string> = {
    'barbarian': '#dc2626',
    'bard': '#db2777',
    'cleric': '#f59e0b',
    'druid': '#16a34a',
    'fighter': '#8b5a3c',
    'monk': '#0891b2',
    'paladin': '#facc15',
    'ranger': '#22c55e',
    'rogue': '#6b7280',
    'sorcerer': '#dc2626',
    'warlock': '#7c3aed',
    'wizard': '#3b82f6'
  };
  
  return classColors[className.toLowerCase()] || theme.colors.primary;
};

export const shadows = {
  small: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 1.41,
    elevation: 2
  },
  medium: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5
  },
  large: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4.65,
    elevation: 8
  }
};