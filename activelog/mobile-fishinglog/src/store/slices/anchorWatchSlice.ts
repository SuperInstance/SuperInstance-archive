import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { AnchorPosition, Position, Alert } from '@/types';

interface AnchorWatchState {
  isWatching: boolean;
  anchorPositions: AnchorPosition[];
  currentPosition: Position | null;
  watchRadius: number;
  isAlarming: boolean;
  alerts: Alert[];
  settings: {
    anchor_alarm_enabled: boolean;
    alert_sound_enabled: boolean;
    vibration_enabled: boolean;
    check_interval: number;
    drift_threshold: number;
  };
  driftHistory: Array<{
    timestamp: Date;
    distance: number;
    position: Position;
  }>;
  watchSession: {
    start_time: Date | null;
    anchor_id: string | null;
    max_drift: number;
    alerts_triggered: number;
  };
}

const initialState: AnchorWatchState = {
  isWatching: false,
  anchorPositions: [
    {
      id: 'anchor_home',
      name: 'Home Bay',
      latitude: 37.8199,
      longitude: -122.4783,
      depth: 12.5,
      anchor_type: 'fortress',
      scope_ratio: 7,
      chain_length: 60,
      notes: 'Good holding ground, protected from west winds',
    },
    {
      id: 'anchor_lunch',
      name: 'Lunch Spot',
      latitude: 37.8156,
      longitude: -122.4694,
      depth: 8.2,
      anchor_type: 'cqr',
      scope_ratio: 5,
      chain_length: 40,
      notes: 'Sandy bottom, good for short stops',
    },
  ],
  currentPosition: {
    latitude: 37.8199,
    longitude: -122.4783,
    timestamp: new Date(),
  },
  watchRadius: 50,
  isAlarming: false,
  alerts: [],
  settings: {
    anchor_alarm_enabled: true,
    alert_sound_enabled: true,
    vibration_enabled: true,
    check_interval: 30,
    drift_threshold: 0.8,
  },
  driftHistory: [],
  watchSession: {
    start_time: null,
    anchor_id: null,
    max_drift: 0,
    alerts_triggered: 0,
  },
};

const anchorWatchSlice = createSlice({
  name: 'anchorWatch',
  initialState,
  reducers: {
    startAnchorWatch: (state, action: PayloadAction<string>) => {
      const anchorId = action.payload;
      const anchor = state.anchorPositions.find(a => a.id === anchorId);
      
      if (anchor) {
        state.isWatching = true;
        state.watchSession = {
          start_time: new Date(),
          anchor_id: anchorId,
          max_drift: 0,
          alerts_triggered: 0,
        };
        
        state.alerts = [];
        state.isAlarming = false;
        state.driftHistory = [];
        
        if (state.currentPosition) {
          state.driftHistory.push({
            timestamp: new Date(),
            distance: 0,
            position: state.currentPosition,
          });
        }
      }
    },

    stopAnchorWatch: (state) => {
      state.isWatching = false;
      state.isAlarming = false;
      state.alerts = [];
      state.watchSession = {
        start_time: null,
        anchor_id: null,
        max_drift: 0,
        alerts_triggered: 0,
      };
    },

    addAnchorPosition: (state, action: PayloadAction<Omit<AnchorPosition, 'id'>>) => {
      const position: AnchorPosition = {
        id: `anchor_${Date.now()}`,
        ...action.payload,
      };
      state.anchorPositions.push(position);
    },

    updateAnchorPosition: (state, action: PayloadAction<{ id: string; updates: Partial<AnchorPosition> }>) => {
      const { id, updates } = action.payload;
      const anchorIndex = state.anchorPositions.findIndex(a => a.id === id);
      if (anchorIndex !== -1) {
        state.anchorPositions[anchorIndex] = { ...state.anchorPositions[anchorIndex], ...updates };
      }
    },

    deleteAnchorPosition: (state, action: PayloadAction<string>) => {
      const anchorId = action.payload;
      state.anchorPositions = state.anchorPositions.filter(a => a.id !== anchorId);
      
      if (state.watchSession.anchor_id === anchorId) {
        state.isWatching = false;
        state.isAlarming = false;
        state.alerts = [];
        state.watchSession = {
          start_time: null,
          anchor_id: null,
          max_drift: 0,
          alerts_triggered: 0,
        };
      }
    },

    updateCurrentPosition: (state, action: PayloadAction<Position>) => {
      state.currentPosition = action.payload;
    },

    setWatchRadius: (state, action: PayloadAction<number>) => {
      state.watchRadius = Math.max(10, Math.min(500, action.payload));
    },

    acknowledgeAlert: (state, action: PayloadAction<string>) => {
      const alertIndex = state.alerts.findIndex(a => a.id === action.payload);
      if (alertIndex !== -1) {
        state.alerts[alertIndex].acknowledged = true;
        
        const unacknowledgedAlerts = state.alerts.filter(a => !a.acknowledged);
        if (unacknowledgedAlerts.length === 0) {
          state.isAlarming = false;
        }
      }
    },

    toggleAnchorAlarm: (state) => {
      state.settings.anchor_alarm_enabled = !state.settings.anchor_alarm_enabled;
    },
  },
});

export const {
  startAnchorWatch,
  stopAnchorWatch,
  addAnchorPosition,
  updateAnchorPosition,
  deleteAnchorPosition,
  updateCurrentPosition,
  setWatchRadius,
  acknowledgeAlert,
  toggleAnchorAlarm,
} = anchorWatchSlice.actions;

export default anchorWatchSlice.reducer;