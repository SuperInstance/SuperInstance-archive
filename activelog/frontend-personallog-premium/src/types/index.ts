// Core Types
export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  preferences: UserPreferences;
  subscription: SubscriptionTier;
}

export interface UserPreferences {
  theme: ThemeMode;
  fontSize: FontSize;
  focusMode: boolean;
  hapticFeedback: boolean;
  voiceJournal: boolean;
  smartSuggestions: boolean;
  ambientMode: boolean;
  magazineLayout: boolean;
}

export type ThemeMode = 'light' | 'dark' | 'auto';
export type FontSize = 'small' | 'medium' | 'large';
export type SubscriptionTier = 'free' | 'premium' | 'pro';

// Journal Entry Types
export interface JournalEntry {
  id: string;
  title: string;
  content: string;
  mood?: MoodType;
  weather?: WeatherType;
  location?: Location;
  photos: Photo[];
  tags: string[];
  createdAt: Date;
  updatedAt: Date;
  wordCount: number;
  readingTime: number;
  isPrivate: boolean;
  voiceNote?: VoiceNote;
  metadata: EntryMetadata;
}

export interface VoiceNote {
  id: string;
  audioUrl: string;
  transcript: string;
  duration: number;
  createdAt: Date;
}

export interface Photo {
  id: string;
  url: string;
  thumbnail: string;
  caption?: string;
  metadata: PhotoMetadata;
}

export interface PhotoMetadata {
  width: number;
  height: number;
  size: number;
  format: string;
  exif?: any;
}

export interface EntryMetadata {
  version: number;
  source: 'manual' | 'voice' | 'import';
  sentiment?: SentimentAnalysis;
  keywords: string[];
  readabilityScore: number;
}

export interface SentimentAnalysis {
  score: number; // -1 to 1
  label: 'negative' | 'neutral' | 'positive';
  confidence: number;
}

export type MoodType = 'excited' | 'happy' | 'content' | 'neutral' | 'tired' | 'sad' | 'anxious' | 'angry';
export type WeatherType = 'sunny' | 'cloudy' | 'rainy' | 'snowy' | 'stormy' | 'foggy';

export interface Location {
  latitude: number;
  longitude: number;
  address: string;
  city: string;
  country: string;
}

// Timeline Types
export interface TimelineEvent {
  id: string;
  date: Date;
  title: string;
  description: string;
  type: TimelineEventType;
  entries: JournalEntry[];
  photos: Photo[];
  milestone?: Milestone;
}

export type TimelineEventType = 'entry' | 'milestone' | 'memory' | 'achievement';

export interface Milestone {
  id: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  achievements: string[];
}

// Visualization Types
export interface InsightData {
  id: string;
  type: InsightType;
  title: string;
  description: string;
  data: any;
  chartType: ChartType;
  timeframe: TimeFrame;
  createdAt: Date;
}

export type InsightType = 'mood_trend' | 'writing_frequency' | 'word_count' | 'topics' | 'memories';
export type ChartType = 'line' | 'bar' | 'pie' | 'area' | 'scatter' | 'heatmap';
export type TimeFrame = 'week' | 'month' | 'quarter' | 'year' | 'all';

// Animation Types
export interface AnimationConfig {
  duration: number;
  easing: string;
  delay?: number;
  repeat?: number;
  yoyo?: boolean;
}

export interface GestureConfig {
  swipeThreshold: number;
  longPressDelay: number;
  doubleTapInterval: number;
  pinchSensitivity: number;
}

// Search Types
export interface SearchResult {
  id: string;
  type: 'entry' | 'photo' | 'voice';
  title: string;
  excerpt: string;
  highlights: string[];
  relevanceScore: number;
  date: Date;
}

export interface SearchFilters {
  dateRange?: [Date, Date];
  mood?: MoodType[];
  tags?: string[];
  hasPhotos?: boolean;
  hasVoice?: boolean;
  minWordCount?: number;
}

// AI Types
export interface SmartSuggestion {
  id: string;
  type: SuggestionType;
  content: string;
  confidence: number;
  context: string;
}

export type SuggestionType = 'prompt' | 'completion' | 'tag' | 'mood' | 'title';

// Focus Mode Types
export interface FocusSession {
  id: string;
  startTime: Date;
  endTime?: Date;
  targetDuration: number;
  wordsWritten: number;
  distractionCount: number;
  mode: FocusMode;
}

export type FocusMode = 'minimal' | 'typewriter' | 'zen' | 'pomodoro';

// Magazine Layout Types
export interface LayoutConfig {
  columns: number;
  gap: number;
  aspectRatio: number;
  flowDirection: 'vertical' | 'horizontal';
  gridTemplate: GridTemplate;
}

export type GridTemplate = 'masonry' | 'grid' | 'magazine' | 'timeline';

// Voice Recognition Types
export interface VoiceCommand {
  command: string;
  action: VoiceAction;
  parameters?: any;
}

export type VoiceAction = 'new_entry' | 'save_entry' | 'search' | 'navigate' | 'focus_mode' | 'change_theme';

// Haptic Feedback Types
export interface HapticPattern {
  type: HapticType;
  duration: number;
  intensity: number;
}

export type HapticType = 'light' | 'medium' | 'heavy' | 'selection' | 'impact' | 'notification';

// Export/Import Types
export interface ExportOptions {
  format: ExportFormat;
  dateRange?: [Date, Date];
  includePhotos: boolean;
  includeMetadata: boolean;
  template?: ExportTemplate;
}

export type ExportFormat = 'pdf' | 'docx' | 'html' | 'markdown' | 'json';
export type ExportTemplate = 'minimal' | 'detailed' | 'magazine' | 'timeline' | 'book';

// API Response Types
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  pagination?: PaginationInfo;
}

export interface PaginationInfo {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

// Error Types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: Date;
}

// Component Props Types
export interface BaseComponentProps {
  className?: string;
  children?: React.ReactNode;
}

export interface AnimatedComponentProps extends BaseComponentProps {
  animation?: AnimationConfig;
  gestureEnabled?: boolean;
}