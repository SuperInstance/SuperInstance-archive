import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { EmergencyContact, Position } from '@/types';

interface EmergencyState {
  contacts: EmergencyContact[];
  isDistressActive: boolean;
  lastDistressSignal: {
    type: 'mayday' | 'pan_pan' | 'securite';
    timestamp: Date;
    location: Position;
    description: string;
  } | null;
  emergencyHistory: Array<{
    id: string;
    type: string;
    description: string;
    timestamp: Date;
    resolved?: boolean;
  }>;
  settings: {
    auto_send_location: boolean;
    emergency_contact_priority: boolean;
    sound_signals: boolean;
    vibration_alerts: boolean;
  };
  systemStatus: {
    gps: 'operational' | 'warning' | 'error';
    radio: 'operational' | 'warning' | 'error';
    emergency_beacon: 'operational' | 'warning' | 'error';
    backup_power: 'operational' | 'warning' | 'error';
  };
}

const initialState: EmergencyState = {
  contacts: [
    {
      id: 'uscg',
      name: 'US Coast Guard',
      organization: 'United States Coast Guard',
      phone: '*CG',
      vhf_channel: '16',
      priority: 'critical',
      notes: 'Primary emergency contact for all maritime emergencies',
    },
    {
      id: 'towboat',
      name: 'TowBoatUS',
      organization: 'BoatUS',
      phone: '1-800-888-4869',
      vhf_channel: '24',
      priority: 'high',
      notes: 'Marine assistance and towing services',
    },
    {
      id: 'sea_tow',
      name: 'Sea Tow',
      organization: 'Sea Tow Services International',
      phone: '1-800-473-2869',
      vhf_channel: '26',
      priority: 'high',
      notes: 'Professional marine assistance',
    },
  ],
  isDistressActive: false,
  lastDistressSignal: null,
  emergencyHistory: [],
  settings: {
    auto_send_location: true,
    emergency_contact_priority: true,
    sound_signals: true,
    vibration_alerts: true,
  },
  systemStatus: {
    gps: 'operational',
    radio: 'operational',
    emergency_beacon: 'operational',
    backup_power: 'operational',
  },
};

const emergencySlice = createSlice({
  name: 'emergency',
  initialState,
  reducers: {
    addEmergencyContact: (state, action: PayloadAction<Omit<EmergencyContact, 'id'>>) => {
      const contact: EmergencyContact = {
        id: `contact_${Date.now()}`,
        ...action.payload,
      };
      state.contacts.push(contact);
    },

    updateEmergencyContact: (state, action: PayloadAction<{ id: string; updates: Partial<EmergencyContact> }>) => {
      const { id, updates } = action.payload;
      const contactIndex = state.contacts.findIndex(c => c.id === id);
      if (contactIndex !== -1) {
        state.contacts[contactIndex] = { ...state.contacts[contactIndex], ...updates };
      }
    },

    deleteEmergencyContact: (state, action: PayloadAction<string>) => {
      state.contacts = state.contacts.filter(c => c.id !== action.payload);
    },

    logEmergencyEvent: (state, action: PayloadAction<{ type: string; description: string }>) => {
      const { type, description } = action.payload;
      const event = {
        id: `event_${Date.now()}`,
        type,
        description,
        timestamp: new Date(),
      };
      
      state.emergencyHistory.unshift(event);
      
      // Keep only last 100 events
      if (state.emergencyHistory.length > 100) {
        state.emergencyHistory = state.emergencyHistory.slice(0, 100);
      }
    },

    sendMaydaySignal: (state, action: PayloadAction<{ location: Position; description: string }>) => {
      const { location, description } = action.payload;
      
      state.isDistressActive = true;
      state.lastDistressSignal = {
        type: 'mayday',
        timestamp: new Date(),
        location,
        description,
      };
      
      // Log the mayday event
      state.emergencyHistory.unshift({
        id: `mayday_${Date.now()}`,
        type: 'mayday',
        description: `MAYDAY signal sent - ${description}`,
        timestamp: new Date(),
      });
    },

    sendPanPanSignal: (state, action: PayloadAction<{ location: Position; description: string }>) => {
      const { location, description } = action.payload;
      
      state.lastDistressSignal = {
        type: 'pan_pan',
        timestamp: new Date(),
        location,
        description,
      };
      
      // Log the pan-pan event
      state.emergencyHistory.unshift({
        id: `panpan_${Date.now()}`,
        type: 'pan_pan',
        description: `PAN-PAN signal sent - ${description}`,
        timestamp: new Date(),
      });
    },

    cancelDistressSignal: (state) => {
      if (state.lastDistressSignal) {
        state.emergencyHistory.unshift({
          id: `cancel_${Date.now()}`,
          type: 'cancel_distress',
          description: `${state.lastDistressSignal.type.toUpperCase()} signal cancelled`,
          timestamp: new Date(),
        });
      }
      
      state.isDistressActive = false;
      state.lastDistressSignal = null;
    },

    updateEmergencySettings: (state, action: PayloadAction<Partial<EmergencyState['settings']>>) => {
      state.settings = { ...state.settings, ...action.payload };
    },

    updateSystemStatus: (state, action: PayloadAction<Partial<EmergencyState['systemStatus']>>) => {
      state.systemStatus = { ...state.systemStatus, ...action.payload };
    },

    testEmergencySystem: (state) => {
      // Simulate a system test
      state.emergencyHistory.unshift({
        id: `test_${Date.now()}`,
        type: 'system_test',
        description: 'Emergency system test completed - all systems operational',
        timestamp: new Date(),
      });
    },

    clearEmergencyHistory: (state) => {
      state.emergencyHistory = [];
    },

    resolveEmergencyEvent: (state, action: PayloadAction<string>) => {
      const eventIndex = state.emergencyHistory.findIndex(e => e.id === action.payload);
      if (eventIndex !== -1) {
        state.emergencyHistory[eventIndex].resolved = true;
      }
    },
  },
});

export const {
  addEmergencyContact,
  updateEmergencyContact,
  deleteEmergencyContact,
  logEmergencyEvent,
  sendMaydaySignal,
  sendPanPanSignal,
  cancelDistressSignal,
  updateEmergencySettings,
  updateSystemStatus,
  testEmergencySystem,
  clearEmergencyHistory,
  resolveEmergencyEvent,
} = emergencySlice.actions;

export default emergencySlice.reducer;