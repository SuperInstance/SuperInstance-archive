import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { AppSettings } from '@/types';

const initialState: AppSettings = {
  theme: 'dark',
  units: {
    distance: 'nm',
    speed: 'kts',
    depth: 'ft',
    temperature: 'f',
    volume: 'gal',
  },
  notifications: {
    anchor_watch: true,
    maintenance_due: true,
    tank_levels: true,
    weather_alerts: true,
    emergency: true,
  },
  voice: {
    enabled: false,
    wake_word: 'Hey Captain',
    language: 'en-US',
    sensitivity: 0.7,
  },
  remote_desktop: {
    auto_connect: false,
    default_quality: 'medium',
    keep_alive: true,
  },
};

const settingsSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {
    updateSettings: (state, action: PayloadAction<Partial<AppSettings>>) => {
      return { ...state, ...action.payload };
    },
    
    updateUnits: (state, action: PayloadAction<Partial<AppSettings['units']>>) => {
      state.units = { ...state.units, ...action.payload };
    },
    
    updateNotifications: (state, action: PayloadAction<Partial<AppSettings['notifications']>>) => {
      state.notifications = { ...state.notifications, ...action.payload };
    },
    
    updateVoiceSettings: (state, action: PayloadAction<Partial<AppSettings['voice']>>) => {
      state.voice = { ...state.voice, ...action.payload };
    },
    
    updateRemoteDesktopSettings: (state, action: PayloadAction<Partial<AppSettings['remote_desktop']>>) => {
      state.remote_desktop = { ...state.remote_desktop, ...action.payload };
    },
    
    resetSettings: () => initialState,
  },
});

export const {
  updateSettings,
  updateUnits,
  updateNotifications,
  updateVoiceSettings,
  updateRemoteDesktopSettings,
  resetSettings,
} = settingsSlice.actions;

export default settingsSlice.reducer;