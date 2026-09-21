import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { DesktopSession, RemoteControl } from '@/types';

interface RemoteDesktopState {
  sessions: DesktopSession[];
  currentSession: DesktopSession | null;
  isConnecting: boolean;
  lastError: string | null;
  connectionHistory: RemoteControl[];
}

const initialState: RemoteDesktopState = {
  sessions: [
    {
      id: 'desktop_main',
      name: 'Main Desktop',
      host: '192.168.1.100',
      port: 3389,
      status: 'disconnected',
      quality: 'medium',
    },
    {
      id: 'nav_station',
      name: 'Navigation Station',
      host: '192.168.1.101',
      port: 3389,
      status: 'disconnected',
      quality: 'high',
    },
  ],
  currentSession: null,
  isConnecting: false,
  lastError: null,
  connectionHistory: [],
};

const remoteDesktopSlice = createSlice({
  name: 'remoteDesktop',
  initialState,
  reducers: {
    addSession: (state, action: PayloadAction<Omit<DesktopSession, 'id' | 'status'>>) => {
      const session: DesktopSession = {
        id: `session_${Date.now()}`,
        status: 'disconnected',
        ...action.payload,
      };
      state.sessions.push(session);
    },
    
    updateSession: (state, action: PayloadAction<{ id: string; updates: Partial<DesktopSession> }>) => {
      const { id, updates } = action.payload;
      const sessionIndex = state.sessions.findIndex(s => s.id === id);
      if (sessionIndex !== -1) {
        state.sessions[sessionIndex] = { ...state.sessions[sessionIndex], ...updates };
        
        if (state.currentSession?.id === id) {
          state.currentSession = { ...state.currentSession, ...updates };
        }
      }
    },
    
    deleteSession: (state, action: PayloadAction<string>) => {
      const sessionId = action.payload;
      state.sessions = state.sessions.filter(s => s.id !== sessionId);
      
      if (state.currentSession?.id === sessionId) {
        state.currentSession = null;
      }
      
      // Clean up connection history
      state.connectionHistory = state.connectionHistory.filter(h => h.session_id !== sessionId);
    },
    
    startConnecting: (state, action: PayloadAction<string>) => {
      const sessionId = action.payload;
      const session = state.sessions.find(s => s.id === sessionId);
      
      if (session) {
        state.isConnecting = true;
        state.lastError = null;
        session.status = 'connecting';
        
        if (state.currentSession?.id === sessionId) {
          state.currentSession.status = 'connecting';
        }
      }
    },
    
    connectSuccess: (state, action: PayloadAction<string>) => {
      const sessionId = action.payload;
      const sessionIndex = state.sessions.findIndex(s => s.id === sessionId);
      
      if (sessionIndex !== -1) {
        state.sessions[sessionIndex].status = 'connected';
        state.sessions[sessionIndex].last_connected = new Date();
        state.currentSession = state.sessions[sessionIndex];
        state.isConnecting = false;
        state.lastError = null;
      }
    },
    
    connectError: (state, action: PayloadAction<{ sessionId: string; error: string }>) => {
      const { sessionId, error } = action.payload;
      const sessionIndex = state.sessions.findIndex(s => s.id === sessionId);
      
      if (sessionIndex !== -1) {
        state.sessions[sessionIndex].status = 'error';
        state.isConnecting = false;
        state.lastError = error;
        
        if (state.currentSession?.id === sessionId) {
          state.currentSession.status = 'error';
        }
      }
    },
    
    disconnect: (state, action: PayloadAction<string>) => {
      const sessionId = action.payload;
      const sessionIndex = state.sessions.findIndex(s => s.id === sessionId);
      
      if (sessionIndex !== -1) {
        state.sessions[sessionIndex].status = 'disconnected';
        
        if (state.currentSession?.id === sessionId) {
          state.currentSession = null;
        }
      }
      
      state.isConnecting = false;
    },
    
    sendRemoteControl: (state, action: PayloadAction<RemoteControl>) => {
      // Add to connection history for debugging/logging
      state.connectionHistory.unshift(action.payload);
      
      // Keep only last 100 actions
      if (state.connectionHistory.length > 100) {
        state.connectionHistory = state.connectionHistory.slice(0, 100);
      }
    },
    
    changeQuality: (state, action: PayloadAction<{ sessionId: string; quality: 'low' | 'medium' | 'high' | 'auto' }>) => {
      const { sessionId, quality } = action.payload;
      const sessionIndex = state.sessions.findIndex(s => s.id === sessionId);
      
      if (sessionIndex !== -1) {
        state.sessions[sessionIndex].quality = quality;
        
        if (state.currentSession?.id === sessionId) {
          state.currentSession.quality = quality;
        }
      }
    },
    
    clearConnectionHistory: (state) => {
      state.connectionHistory = [];
    },
    
    clearLastError: (state) => {
      state.lastError = null;
    },
    
    setCurrentSession: (state, action: PayloadAction<string | null>) => {
      const sessionId = action.payload;
      if (sessionId) {
        const session = state.sessions.find(s => s.id === sessionId);
        state.currentSession = session || null;
      } else {
        state.currentSession = null;
      }
    },
    
    updateConnectionStatus: (state, action: PayloadAction<{ sessionId: string; status: DesktopSession['status'] }>) => {
      const { sessionId, status } = action.payload;
      const sessionIndex = state.sessions.findIndex(s => s.id === sessionId);
      
      if (sessionIndex !== -1) {
        state.sessions[sessionIndex].status = status;
        
        if (state.currentSession?.id === sessionId) {
          state.currentSession.status = status;
        }
      }
    },
  },
});

export const {
  addSession,
  updateSession,
  deleteSession,
  startConnecting,
  connectSuccess,
  connectError,
  disconnect,
  sendRemoteControl,
  changeQuality,
  clearConnectionHistory,
  clearLastError,
  setCurrentSession,
  updateConnectionStatus,
} = remoteDesktopSlice.actions;

export default remoteDesktopSlice.reducer;