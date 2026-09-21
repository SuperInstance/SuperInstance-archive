// Core streaming types
export interface StreamSession {
  id: string;
  campaignId: string;
  title: string;
  description?: string;
  startTime: Date;
  endTime?: Date;
  status: 'scheduled' | 'live' | 'ended' | 'cancelled';
  platform: 'twitch' | 'youtube' | 'both';
  streamKey?: string;
  viewerCount: number;
  chatMessages: number;
  highlights: StreamHighlight[];
  chapters: StreamChapter[];
  settings: StreamSettings;
}

export interface StreamSettings {
  overlays: OverlaySettings;
  automation: AutomationSettings;
  interaction: InteractionSettings;
  recording: RecordingSettings;
}

export interface OverlaySettings {
  enabled: boolean;
  layout: 'standard' | 'minimal' | 'cinematic' | 'combat';
  theme: 'dark' | 'light' | 'custom';
  opacity: number;
  fadeTransitions: boolean;
  showViewerCount: boolean;
  showDonations: boolean;
  showDiceRolls: boolean;
  characterShowcase: boolean;
  campaignProgress: boolean;
}

export interface AutomationSettings {
  cameraSwitching: {
    enabled: boolean;
    mode: 'manual' | 'scene-based' | 'ai-assisted';
    scenes: CameraScene[];
  };
  socialPosting: {
    enabled: boolean;
    platforms: ('twitter' | 'discord' | 'instagram')[];
    templates: SocialTemplate[];
  };
  vodProcessing: {
    enabled: boolean;
    autoChapters: boolean;
    highlightDetection: boolean;
    uploadToYoutube: boolean;
  };
}

export interface InteractionSettings {
  viewerDice: {
    enabled: boolean;
    cooldown: number;
    maxRolls: number;
    allowedDice: string[];
  };
  polls: {
    enabled: boolean;
    duration: number;
    showResults: boolean;
    requireSubscription: boolean;
  };
  donations: {
    enabled: boolean;
    effects: DonationEffect[];
    minimumAmount: number;
    showDonorName: boolean;
  };
}

export interface RecordingSettings {
  enabled: boolean;
  quality: 'low' | 'medium' | 'high' | 'source';
  format: 'mp4' | 'mkv' | 'flv';
  separateAudioTracks: boolean;
  autoUpload: boolean;
}

// OBS Integration
export interface OBSScene {
  name: string;
  sources: OBSSource[];
  transitions: SceneTransition[];
}

export interface OBSSource {
  id: string;
  name: string;
  type: 'browser' | 'image' | 'video' | 'camera' | 'audio' | 'text';
  url?: string;
  file?: string;
  settings: Record<string, any>;
  transform: SourceTransform;
  filters: SourceFilter[];
}

export interface SourceTransform {
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  opacity: number;
  visible: boolean;
}

export interface SourceFilter {
  name: string;
  type: string;
  enabled: boolean;
  settings: Record<string, any>;
}

export interface SceneTransition {
  name: string;
  type: 'cut' | 'fade' | 'swipe' | 'slide' | 'zoom';
  duration: number;
  trigger: 'manual' | 'timer' | 'event';
}

export interface CameraScene {
  id: string;
  name: string;
  description: string;
  obsSceneName: string;
  triggers: SceneTrigger[];
  duration?: number;
}

export interface SceneTrigger {
  type: 'combat' | 'roleplay' | 'exploration' | 'dice_roll' | 'donation' | 'manual';
  condition?: string;
  priority: number;
}

// Overlay System
export interface OverlayElement {
  id: string;
  type: 'dice' | 'character' | 'chat' | 'donation' | 'poll' | 'progress' | 'timer' | 'image' | 'text';
  position: Position;
  size: Size;
  style: ElementStyle;
  data: Record<string, any>;
  visible: boolean;
  animation?: Animation;
}

export interface Position {
  x: number;
  y: number;
  anchor: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';
}

export interface Size {
  width: number;
  height: number;
  scale: number;
}

export interface ElementStyle {
  background?: string;
  border?: string;
  borderRadius?: number;
  color?: string;
  fontSize?: number;
  fontFamily?: string;
  opacity?: number;
  shadow?: string;
}

export interface Animation {
  type: 'fade' | 'slide' | 'bounce' | 'pulse' | 'shake' | 'rotate';
  duration: number;
  easing: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
  loop?: boolean;
}

// Viewer Interaction
export interface ViewerDiceRoll {
  id: string;
  userId: string;
  username: string;
  notation: string;
  result: DiceResult;
  timestamp: Date;
  context?: string;
}

export interface DiceResult {
  total: number;
  rolls: number[];
  modifiers: number[];
  breakdown: string;
  critical?: boolean;
  fumble?: boolean;
}

export interface ViewerPoll {
  id: string;
  question: string;
  options: PollOption[];
  duration: number;
  startTime: Date;
  endTime?: Date;
  status: 'active' | 'ended';
  totalVotes: number;
  allowMultiple: boolean;
  requireSubscription: boolean;
  createdBy: string;
}

export interface PollOption {
  id: string;
  text: string;
  votes: number;
  voters: string[];
}

export interface ViewerEngagement {
  userId: string;
  username: string;
  joinTime: Date;
  totalTime: number;
  messageCount: number;
  diceRolls: number;
  pollVotes: number;
  donations: number;
  subscribed: boolean;
  follower: boolean;
  moderator: boolean;
  badges: string[];
}

// Donations & Effects
export interface Donation {
  id: string;
  userId: string;
  username: string;
  amount: number;
  currency: string;
  message?: string;
  timestamp: Date;
  effects: DonationEffect[];
  processed: boolean;
}

export interface DonationEffect {
  type: 'sound' | 'overlay' | 'scene_change' | 'dice_roll' | 'character_action' | 'light_effect';
  trigger: {
    minAmount?: number;
    keywords?: string[];
  };
  settings: Record<string, any>;
  duration?: number;
}

// Character System
export interface Character {
  id: string;
  name: string;
  class: string;
  level: number;
  race: string;
  background: string;
  stats: CharacterStats;
  equipment: InventoryItem[];
  spells: Spell[];
  avatar?: string;
  portrait?: string;
  token?: string;
  backstory: string;
  notes: string[];
}

export interface CharacterStats {
  hitPoints: { current: number; maximum: number };
  armorClass: number;
  speed: number;
  abilities: {
    strength: number;
    dexterity: number;
    constitution: number;
    intelligence: number;
    wisdom: number;
    charisma: number;
  };
  savingThrows: Record<string, number>;
  skills: Record<string, number>;
  conditions: string[];
}

export interface InventoryItem {
  id: string;
  name: string;
  type: string;
  rarity: string;
  description: string;
  quantity: number;
  equipped: boolean;
  magical: boolean;
  image?: string;
}

export interface Spell {
  id: string;
  name: string;
  level: number;
  school: string;
  castingTime: string;
  range: string;
  duration: string;
  description: string;
  prepared: boolean;
  components: {
    verbal: boolean;
    somatic: boolean;
    material: boolean;
  };
}

// Campaign System
export interface Campaign {
  id: string;
  name: string;
  description: string;
  dmId: string;
  players: string[];
  characters: Character[];
  sessions: Session[];
  currentSession?: string;
  settings: CampaignSettings;
  status: 'planning' | 'active' | 'paused' | 'completed';
  createdAt: Date;
  updatedAt: Date;
}

export interface Session {
  id: string;
  campaignId: string;
  sessionNumber: number;
  title: string;
  summary: string;
  startTime: Date;
  endTime?: Date;
  events: SessionEvent[];
  highlights: string[];
  notes: string[];
  experience: number;
  treasure: InventoryItem[];
}

export interface SessionEvent {
  id: string;
  timestamp: Date;
  type: 'combat' | 'roleplay' | 'exploration' | 'puzzle' | 'social' | 'discovery';
  title: string;
  description: string;
  participants: string[];
  outcome?: string;
  experience?: number;
  treasure?: InventoryItem[];
}

export interface CampaignSettings {
  theme: string;
  world: string;
  rules: string[];
  houseRules: string[];
  xpSystem: 'standard' | 'milestone' | 'custom';
  encumbranceRules: boolean;
  inspiration: boolean;
}

// Streaming Analytics
export interface StreamAnalytics {
  sessionId: string;
  viewMetrics: ViewMetrics;
  engagementMetrics: EngagementMetrics;
  contentMetrics: ContentMetrics;
  technicalMetrics: TechnicalMetrics;
}

export interface ViewMetrics {
  peakViewers: number;
  averageViewers: number;
  uniqueViewers: number;
  viewerRetention: number;
  chatActivity: number;
  newFollowers: number;
  newSubscribers: number;
}

export interface EngagementMetrics {
  totalMessages: number;
  uniqueChatters: number;
  diceRolls: number;
  pollParticipation: number;
  donations: {
    count: number;
    total: number;
  };
}

export interface ContentMetrics {
  combatTime: number;
  roleplayTime: number;
  explorationTime: number;
  characterShowcaseTime: number;
  totalDiceRolls: number;
  criticalHits: number;
  criticalMisses: number;
}

export interface TechnicalMetrics {
  streamHealth: number;
  droppedFrames: number;
  bitrate: number;
  encoding: string;
  resolution: string;
  fps: number;
  uptime: number;
}

// Highlights & Clips
export interface StreamHighlight {
  id: string;
  sessionId: string;
  startTime: number;
  endTime: number;
  title: string;
  description?: string;
  type: 'combat' | 'roleplay' | 'dice' | 'reaction' | 'donation' | 'custom';
  participants: string[];
  tags: string[];
  thumbnail?: string;
  clipUrl?: string;
  score: number;
  createdBy: 'auto' | 'manual' | 'viewer';
  status: 'pending' | 'processing' | 'ready' | 'uploaded';
}

export interface StreamChapter {
  id: string;
  sessionId: string;
  startTime: number;
  endTime?: number;
  title: string;
  description?: string;
  type: 'intro' | 'recap' | 'roleplay' | 'combat' | 'exploration' | 'outro';
  thumbnail?: string;
}

// Social Media
export interface SocialTemplate {
  id: string;
  platform: 'twitter' | 'discord' | 'instagram';
  trigger: 'session_start' | 'session_end' | 'highlight' | 'milestone' | 'custom';
  template: string;
  hashtags: string[];
  mentions: string[];
  includeMedia: boolean;
  enabled: boolean;
}

export interface SocialPost {
  id: string;
  platform: 'twitter' | 'discord' | 'instagram';
  content: string;
  media?: string[];
  hashtags: string[];
  mentions: string[];
  scheduledFor?: Date;
  postedAt?: Date;
  status: 'draft' | 'scheduled' | 'posted' | 'failed';
  engagement?: {
    likes: number;
    shares: number;
    comments: number;
  };
}

// WebSocket Events
export interface SocketEvent {
  type: string;
  data: any;
  timestamp: Date;
  source: 'server' | 'client' | 'obs' | 'twitch' | 'youtube';
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: Date;
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

// Configuration
export interface StreamConfig {
  server: {
    port: number;
    host: string;
    cors: {
      origins: string[];
    };
  };
  obs: {
    host: string;
    port: number;
    password: string;
    reconnectDelay: number;
  };
  twitch: {
    clientId: string;
    clientSecret: string;
    redirectUri: string;
    scopes: string[];
  };
  youtube: {
    apiKey: string;
    clientId: string;
    clientSecret: string;
  };
  database: {
    type: 'sqlite' | 'postgres' | 'mysql';
    host?: string;
    port?: number;
    database: string;
    username?: string;
    password?: string;
  };
  storage: {
    type: 'local' | 's3' | 'gcp' | 'azure';
    path: string;
    bucket?: string;
    region?: string;
  };
  ffmpeg: {
    path: string;
    outputPath: string;
    quality: 'low' | 'medium' | 'high';
  };
}