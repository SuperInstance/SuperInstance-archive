import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { VoiceCommand, VoiceSession } from '@/types';

interface VoiceState {
  commands: VoiceCommand[];
  currentSession: VoiceSession | null;
  isListening: boolean;
  isEnabled: boolean;
  lastRecognizedText: string | null;
  sessionHistory: VoiceSession[];
}

const initialState: VoiceState = {
  commands: [
    {
      id: 'mark_position',
      phrase: 'mark position',
      action: 'MARK_POSITION',
      enabled: true,
    },
    {
      id: 'start_anchor_watch',
      phrase: 'start anchor watch',
      action: 'START_ANCHOR_WATCH',
      enabled: true,
    },
    {
      id: 'stop_anchor_watch',
      phrase: 'stop anchor watch',
      action: 'STOP_ANCHOR_WATCH',
      enabled: true,
    },
    {
      id: 'emergency_mayday',
      phrase: 'mayday mayday',
      action: 'EMERGENCY_MAYDAY',
      enabled: true,
    },
    {
      id: 'emergency_pan',
      phrase: 'pan pan',
      action: 'EMERGENCY_PAN',
      enabled: true,
    },
    {
      id: 'log_fish',
      phrase: 'log fish',
      action: 'LOG_FISH',
      enabled: true,
    },
    {
      id: 'take_photo',
      phrase: 'take photo',
      action: 'TAKE_PHOTO',
      enabled: true,
    },
    {
      id: 'start_trip',
      phrase: 'start fishing trip',
      action: 'START_TRIP',
      enabled: true,
    },
    {
      id: 'end_trip',
      phrase: 'end fishing trip',
      action: 'END_TRIP',
      enabled: true,
    },
    {
      id: 'check_weather',
      phrase: 'check weather',
      action: 'CHECK_WEATHER',
      enabled: true,
    },
    {
      id: 'check_fuel',
      phrase: 'check fuel',
      action: 'CHECK_FUEL',
      enabled: true,
    },
    {
      id: 'navigate_home',
      phrase: 'navigate home',
      action: 'NAVIGATE_HOME',
      enabled: true,
    },
  ],
  currentSession: null,
  isListening: false,
  isEnabled: false,
  lastRecognizedText: null,
  sessionHistory: [],
};

const voiceSlice = createSlice({
  name: 'voice',
  initialState,
  reducers: {
    enableVoice: (state) => {
      state.isEnabled = true;
    },
    
    disableVoice: (state) => {
      state.isEnabled = false;
      state.isListening = false;
      if (state.currentSession) {
        state.currentSession.end_time = new Date();
        state.sessionHistory.unshift(state.currentSession);
        state.currentSession = null;
      }
    },
    
    startListening: (state) => {
      if (state.isEnabled) {
        state.isListening = true;
        
        if (!state.currentSession) {
          state.currentSession = {
            id: `session_${Date.now()}`,
            start_time: new Date(),
            commands_processed: 0,
            errors: 0,
          };
        }
      }
    },
    
    stopListening: (state) => {
      state.isListening = false;
    },
    
    voiceRecognized: (state, action: PayloadAction<string>) => {
      state.lastRecognizedText = action.payload;
      
      // Check if recognized text matches any command
      const matchedCommand = state.commands.find(cmd => 
        cmd.enabled && 
        action.payload.toLowerCase().includes(cmd.phrase.toLowerCase())
      );
      
      if (matchedCommand && state.currentSession) {
        state.currentSession.commands_processed += 1;
      } else if (state.currentSession) {
        state.currentSession.errors += 1;
      }
    },
    
    addVoiceCommand: (state, action: PayloadAction<Omit<VoiceCommand, 'id'>>) => {
      const command: VoiceCommand = {
        id: `cmd_${Date.now()}`,
        ...action.payload,
      };
      state.commands.push(command);
    },
    
    updateVoiceCommand: (state, action: PayloadAction<{ id: string; updates: Partial<VoiceCommand> }>) => {
      const { id, updates } = action.payload;
      const commandIndex = state.commands.findIndex(c => c.id === id);
      if (commandIndex !== -1) {
        state.commands[commandIndex] = { ...state.commands[commandIndex], ...updates };
      }
    },
    
    deleteVoiceCommand: (state, action: PayloadAction<string>) => {
      state.commands = state.commands.filter(c => c.id !== action.payload);
    },
    
    toggleCommandEnabled: (state, action: PayloadAction<string>) => {
      const commandIndex = state.commands.findIndex(c => c.id === action.payload);
      if (commandIndex !== -1) {
        state.commands[commandIndex].enabled = !state.commands[commandIndex].enabled;
      }
    },
    
    endVoiceSession: (state) => {
      if (state.currentSession) {
        state.currentSession.end_time = new Date();
        state.sessionHistory.unshift(state.currentSession);
        state.currentSession = null;
        
        // Keep only last 50 sessions
        if (state.sessionHistory.length > 50) {
          state.sessionHistory = state.sessionHistory.slice(0, 50);
        }
      }
      state.isListening = false;
    },
    
    clearLastRecognizedText: (state) => {
      state.lastRecognizedText = null;
    },
    
    clearSessionHistory: (state) => {
      state.sessionHistory = [];
    },
    
    processVoiceCommand: (state, action: PayloadAction<{ commandId: string; parameters?: any }>) => {
      if (state.currentSession) {
        state.currentSession.commands_processed += 1;
      }
      
      // The actual command processing would be handled by middleware or effects
      console.log('Processing voice command:', action.payload);
    },
    
    voiceError: (state, action: PayloadAction<string>) => {
      if (state.currentSession) {
        state.currentSession.errors += 1;
      }
      
      console.error('Voice recognition error:', action.payload);
    },
    
    trainVoiceCommand: (state, action: PayloadAction<{ commandId: string; audioData: string }>) => {
      // In a real implementation, this would train the voice recognition model
      const commandIndex = state.commands.findIndex(c => c.id === action.payload.commandId);
      if (commandIndex !== -1) {
        // Store training data or update recognition parameters
        console.log('Training voice command:', state.commands[commandIndex].phrase);
      }
    },
  },
});

export const {
  enableVoice,
  disableVoice,
  startListening,
  stopListening,
  voiceRecognized,
  addVoiceCommand,
  updateVoiceCommand,
  deleteVoiceCommand,
  toggleCommandEnabled,
  endVoiceSession,
  clearLastRecognizedText,
  clearSessionHistory,
  processVoiceCommand,
  voiceError,
  trainVoiceCommand,
} = voiceSlice.actions;

export default voiceSlice.reducer;