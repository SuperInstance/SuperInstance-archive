import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { User, JournalEntry, TimelineEvent, InsightData, FocusSession, UserPreferences, ThemeMode } from '@/types';

// Theme Store
interface ThemeState {
  mode: ThemeMode;
  isDark: boolean;
  toggleTheme: () => void;
  setTheme: (mode: ThemeMode) => void;
  colors: {
    primary: string;
    secondary: string;
    background: string;
    surface: string;
    text: string;
    textSecondary: string;
    accent: string;
    success: string;
    warning: string;
    error: string;
  };
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      mode: 'auto',
      isDark: window.matchMedia('(prefers-color-scheme: dark)').matches,
      toggleTheme: () => {
        const currentMode = get().mode;
        const newMode = currentMode === 'light' ? 'dark' : 'light';
        set({ mode: newMode, isDark: newMode === 'dark' });
      },
      setTheme: (mode: ThemeMode) => {
        const isDark = mode === 'auto' 
          ? window.matchMedia('(prefers-color-scheme: dark)').matches 
          : mode === 'dark';
        set({ mode, isDark });
      },
      colors: {
        primary: '#6366f1',
        secondary: '#8b5cf6',
        background: '#ffffff',
        surface: '#f8fafc',
        text: '#1e293b',
        textSecondary: '#64748b',
        accent: '#f59e0b',
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444',
      },
    }),
    {
      name: 'theme-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// User Store
interface UserState {
  user: User | null;
  preferences: UserPreferences;
  setUser: (user: User) => void;
  updatePreferences: (preferences: Partial<UserPreferences>) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set, get) => ({
      user: null,
      preferences: {
        theme: 'auto',
        fontSize: 'medium',
        focusMode: false,
        hapticFeedback: true,
        voiceJournal: true,
        smartSuggestions: true,
        ambientMode: false,
        magazineLayout: false,
      },
      setUser: (user: User) => set({ user }),
      updatePreferences: (newPreferences: Partial<UserPreferences>) =>
        set((state) => ({
          preferences: { ...state.preferences, ...newPreferences },
        })),
      logout: () => set({ user: null }),
    }),
    {
      name: 'user-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// Journal Store
interface JournalState {
  entries: JournalEntry[];
  currentEntry: JournalEntry | null;
  isLoading: boolean;
  searchQuery: string;
  filteredEntries: JournalEntry[];
  addEntry: (entry: Omit<JournalEntry, 'id' | 'createdAt' | 'updatedAt'>) => void;
  updateEntry: (id: string, updates: Partial<JournalEntry>) => void;
  deleteEntry: (id: string) => void;
  setCurrentEntry: (entry: JournalEntry | null) => void;
  searchEntries: (query: string) => void;
  setLoading: (loading: boolean) => void;
}

export const useJournalStore = create<JournalState>((set, get) => ({
  entries: [],
  currentEntry: null,
  isLoading: false,
  searchQuery: '',
  filteredEntries: [],
  
  addEntry: (entryData) => {
    const entry: JournalEntry = {
      ...entryData,
      id: crypto.randomUUID(),
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    set((state) => ({ 
      entries: [entry, ...state.entries],
      filteredEntries: [entry, ...state.filteredEntries]
    }));
  },
  
  updateEntry: (id, updates) => {
    set((state) => ({
      entries: state.entries.map((entry) =>
        entry.id === id ? { ...entry, ...updates, updatedAt: new Date() } : entry
      ),
      filteredEntries: state.filteredEntries.map((entry) =>
        entry.id === id ? { ...entry, ...updates, updatedAt: new Date() } : entry
      ),
    }));
  },
  
  deleteEntry: (id) => {
    set((state) => ({
      entries: state.entries.filter((entry) => entry.id !== id),
      filteredEntries: state.filteredEntries.filter((entry) => entry.id !== id),
      currentEntry: state.currentEntry?.id === id ? null : state.currentEntry,
    }));
  },
  
  setCurrentEntry: (entry) => set({ currentEntry: entry }),
  
  searchEntries: (query) => {
    set({ searchQuery: query });
    if (!query.trim()) {
      set((state) => ({ filteredEntries: state.entries }));
      return;
    }
    
    const filtered = get().entries.filter((entry) =>
      entry.title.toLowerCase().includes(query.toLowerCase()) ||
      entry.content.toLowerCase().includes(query.toLowerCase()) ||
      entry.tags.some(tag => tag.toLowerCase().includes(query.toLowerCase()))
    );
    set({ filteredEntries: filtered });
  },
  
  setLoading: (loading) => set({ isLoading: loading }),
}));

// Timeline Store
interface TimelineState {
  events: TimelineEvent[];
  selectedEvent: TimelineEvent | null;
  setEvents: (events: TimelineEvent[]) => void;
  setSelectedEvent: (event: TimelineEvent | null) => void;
  addEvent: (event: Omit<TimelineEvent, 'id'>) => void;
}

export const useTimelineStore = create<TimelineState>((set) => ({
  events: [],
  selectedEvent: null,
  setEvents: (events) => set({ events }),
  setSelectedEvent: (event) => set({ selectedEvent: event }),
  addEvent: (eventData) => {
    const event: TimelineEvent = {
      ...eventData,
      id: crypto.randomUUID(),
    };
    set((state) => ({ events: [...state.events, event] }));
  },
}));

// Focus Mode Store
interface FocusState {
  isActive: boolean;
  currentSession: FocusSession | null;
  sessions: FocusSession[];
  startSession: (mode: FocusSession['mode'], targetDuration: number) => void;
  endSession: () => void;
  updateSession: (updates: Partial<FocusSession>) => void;
}

export const useFocusStore = create<FocusState>((set, get) => ({
  isActive: false,
  currentSession: null,
  sessions: [],
  
  startSession: (mode, targetDuration) => {
    const session: FocusSession = {
      id: crypto.randomUUID(),
      startTime: new Date(),
      targetDuration,
      wordsWritten: 0,
      distractionCount: 0,
      mode,
    };
    set({ isActive: true, currentSession: session });
  },
  
  endSession: () => {
    const { currentSession } = get();
    if (currentSession) {
      const completedSession: FocusSession = {
        ...currentSession,
        endTime: new Date(),
      };
      set((state) => ({
        isActive: false,
        currentSession: null,
        sessions: [...state.sessions, completedSession],
      }));
    }
  },
  
  updateSession: (updates) => {
    set((state) => ({
      currentSession: state.currentSession
        ? { ...state.currentSession, ...updates }
        : null,
    }));
  },
}));

// Voice Store
interface VoiceState {
  isListening: boolean;
  transcript: string;
  isSupported: boolean;
  startListening: () => void;
  stopListening: () => void;
  clearTranscript: () => void;
}

export const useVoiceStore = create<VoiceState>((set) => ({
  isListening: false,
  transcript: '',
  isSupported: 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window,
  
  startListening: () => set({ isListening: true }),
  stopListening: () => set({ isListening: false }),
  clearTranscript: () => set({ transcript: '' }),
}));

// UI Store
interface UIState {
  sidebarOpen: boolean;
  focusModeActive: boolean;
  ambientModeActive: boolean;
  magazineLayoutActive: boolean;
  showTimeline: boolean;
  showInsights: boolean;
  toggleSidebar: () => void;
  setFocusMode: (active: boolean) => void;
  setAmbientMode: (active: boolean) => void;
  setMagazineLayout: (active: boolean) => void;
  setShowTimeline: (show: boolean) => void;
  setShowInsights: (show: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  focusModeActive: false,
  ambientModeActive: false,
  magazineLayoutActive: false,
  showTimeline: false,
  showInsights: false,
  
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setFocusMode: (active) => set({ focusModeActive: active }),
  setAmbientMode: (active) => set({ ambientModeActive: active }),
  setMagazineLayout: (active) => set({ magazineLayoutActive: active }),
  setShowTimeline: (show) => set({ showTimeline: show }),
  setShowInsights: (show) => set({ showInsights: show }),
}));