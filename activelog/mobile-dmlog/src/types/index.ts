// Core character types
export interface Character {
  id: string;
  name: string;
  class: string;
  level: number;
  race: string;
  background: string;
  avatar?: string;
  
  // Ability scores
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
  
  // Derived stats
  proficiencyBonus: number;
  armorClass: number;
  hitPoints: {
    current: number;
    maximum: number;
    temporary: number;
  };
  hitDice: {
    current: number;
    maximum: number;
    type: string; // d6, d8, d10, d12
  };
  
  // Skills and proficiencies
  skills: Record<string, { proficient: boolean; expertise: boolean }>;
  savingThrows: Record<string, boolean>;
  languages: string[];
  proficiencies: string[];
  
  // Combat stats
  initiative: number;
  speed: number;
  conditions: string[];
  
  // Resources
  spellSlots: Record<number, { current: number; maximum: number }>;
  resources: Array<{
    name: string;
    current: number;
    maximum: number;
    resetOn: 'short' | 'long' | 'none';
  }>;
  
  // Equipment
  equipment: InventoryItem[];
  currency: {
    copper: number;
    silver: number;
    electrum: number;
    gold: number;
    platinum: number;
  };
  
  // Spells and abilities
  spells: Spell[];
  features: Feature[];
  
  // Roleplay
  personality: {
    traits: string[];
    ideals: string[];
    bonds: string[];
    flaws: string[];
  };
  backstory: string;
  notes: string[];
  
  // Meta
  createdAt: Date;
  updatedAt: Date;
  lastSyncAt?: Date;
}

// Spell system
export interface Spell {
  id: string;
  name: string;
  level: number;
  school: string;
  castingTime: string;
  range: string;
  components: {
    verbal: boolean;
    somatic: boolean;
    material: boolean;
    materialComponents?: string;
  };
  duration: string;
  description: string;
  atHigherLevels?: string;
  ritual: boolean;
  concentration: boolean;
  damage?: {
    type: string;
    dice: string;
  };
  prepared: boolean;
  alwaysPrepared: boolean;
  source: string;
}

// Features and abilities
export interface Feature {
  id: string;
  name: string;
  source: string; // Class, Race, Background, Feat, etc.
  description: string;
  usage?: {
    type: 'per-short-rest' | 'per-long-rest' | 'per-day' | 'charges' | 'unlimited';
    maximum: number;
    current: number;
  };
  level?: number; // Level when acquired
}

// Inventory system
export interface InventoryItem {
  id: string;
  name: string;
  description: string;
  type: 'weapon' | 'armor' | 'shield' | 'tool' | 'consumable' | 'treasure' | 'misc';
  rarity: 'common' | 'uncommon' | 'rare' | 'very-rare' | 'legendary' | 'artifact';
  quantity: number;
  weight: number;
  value: number; // in gold pieces
  equipped: boolean;
  attuned?: boolean;
  requiresAttunement?: boolean;
  image?: string;
  
  // Weapon specific
  damage?: {
    dice: string;
    type: string;
  };
  properties?: string[];
  
  // Armor specific
  armorClass?: {
    base: number;
    dexBonus: boolean;
    maxDexBonus?: number;
  };
  
  // Magical properties
  magical: boolean;
  spells?: string[];
  effects?: string[];
}

// Chat and communication
export interface ChatMessage {
  id: string;
  playerId: string;
  characterName: string;
  content: string;
  type: 'ic' | 'ooc' | 'roll';
  timestamp: Date;
  rollResult?: {
    notation: string;
    total: number;
    breakdown: string;
    rolls: Array<{
      sides: number;
      result: number;
    }>;
  };
  private?: boolean;
  recipients?: string[]; // For private messages
}

// Dice system
export interface DiceRoll {
  id: string;
  notation: string; // "1d20+5"
  results: number[];
  modifiers: number[];
  total: number;
  type: 'ability' | 'attack' | 'damage' | 'saving-throw' | 'skill' | 'custom';
  advantage?: boolean;
  disadvantage?: boolean;
  critical?: boolean;
  timestamp: Date;
}

// Game session
export interface GameSession {
  id: string;
  name: string;
  dmId: string;
  players: string[];
  characters: Character[];
  active: boolean;
  currentTurn?: string; // character ID
  round: number;
  initiative: Array<{
    characterId: string;
    initiative: number;
    hasActed: boolean;
  }>;
  createdAt: Date;
  scheduledFor?: Date;
}

// Synchronization
export interface SyncOperation {
  id: string;
  type: 'create' | 'update' | 'delete';
  entityType: 'character' | 'spell' | 'item' | 'chat' | 'session';
  entityId: string;
  data: any;
  timestamp: Date;
  synced: boolean;
  userId: string;
}

// Notifications
export interface GameNotification {
  id: string;
  title: string;
  body: string;
  type: 'session-start' | 'turn-reminder' | 'chat-mention' | 'level-up' | 'custom';
  data?: any;
  scheduledFor?: Date;
  sent: boolean;
  userId: string;
}

// AR and camera
export interface MiniatureData {
  id: string;
  characterId: string;
  position: { x: number; y: number };
  scale: number;
  rotation: number;
  model?: string; // 3D model path
  image: string; // 2D representation
}

// Navigation types
export type RootStackParamList = {
  CharacterSheet: { characterId: string };
  DiceRoller: undefined;
  SpellCards: { characterId: string };
  Inventory: { characterId: string };
  Chat: { sessionId: string };
  Initiative: { sessionId: string };
  Rules: undefined;
  AR: { sessionId: string };
  Notes: { characterId: string };
  Settings: undefined;
  CharacterSelect: undefined;
  Backup: undefined;
};

export type TabParamList = {
  Character: undefined;
  Dice: undefined;
  Spells: undefined;
  Inventory: undefined;
  Chat: undefined;
  More: undefined;
};

// Hook return types
export interface UseCharacterReturn {
  character: Character | null;
  loading: boolean;
  error: string | null;
  updateCharacter: (updates: Partial<Character>) => Promise<void>;
  refreshCharacter: () => Promise<void>;
}

export interface UseDiceReturn {
  rollHistory: DiceRoll[];
  rollDice: (notation: string, type?: DiceRoll['type'], options?: { advantage?: boolean; disadvantage?: boolean }) => Promise<DiceRoll>;
  clearHistory: () => void;
  getLastRoll: () => DiceRoll | null;
}

export interface UseInventoryReturn {
  items: InventoryItem[];
  equippedItems: InventoryItem[];
  totalWeight: number;
  addItem: (item: Omit<InventoryItem, 'id'>) => Promise<void>;
  updateItem: (id: string, updates: Partial<InventoryItem>) => Promise<void>;
  removeItem: (id: string) => Promise<void>;
  equipItem: (id: string) => Promise<void>;
  unequipItem: (id: string) => Promise<void>;
}

// Theme types
export interface Theme {
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    surface: string;
    text: string;
    textSecondary: string;
    border: string;
    error: string;
    warning: string;
    success: string;
    info: string;
    
    // D&D specific
    strength: string;
    dexterity: string;
    constitution: string;
    intelligence: string;
    wisdom: string;
    charisma: string;
    
    // Rarity colors
    common: string;
    uncommon: string;
    rare: string;
    veryRare: string;
    legendary: string;
    artifact: string;
  };
  fonts: {
    regular: string;
    medium: string;
    bold: string;
    sizes: {
      xs: number;
      sm: number;
      md: number;
      lg: number;
      xl: number;
      xxl: number;
    };
  };
  spacing: {
    xs: number;
    sm: number;
    md: number;
    lg: number;
    xl: number;
  };
  borderRadius: {
    sm: number;
    md: number;
    lg: number;
    full: number;
  };
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}