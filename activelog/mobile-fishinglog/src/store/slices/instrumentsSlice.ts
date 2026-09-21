import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { InstrumentData, WeatherData, Position } from '@/types';

interface InstrumentsState {
  current: InstrumentData | null;
  weather: WeatherData | null;
  position: Position | null;
  isConnected: boolean;
  lastUpdate: string | null;
  history: InstrumentData[];
}

const initialState: InstrumentsState = {
  current: null,
  weather: null,
  position: null,
  isConnected: false,
  lastUpdate: null,
  history: [],
};

const instrumentsSlice = createSlice({
  name: 'instruments',
  initialState,
  reducers: {
    updateInstrumentData: (state, action: PayloadAction<InstrumentData>) => {
      state.current = action.payload;
      state.lastUpdate = new Date().toISOString();
      state.isConnected = true;
      
      // Keep last 100 readings for history
      state.history.push(action.payload);
      if (state.history.length > 100) {
        state.history.shift();
      }
    },
    
    updateWeatherData: (state, action: PayloadAction<WeatherData>) => {
      state.weather = action.payload;
    },
    
    updatePosition: (state, action: PayloadAction<Position>) => {
      state.position = action.payload;
    },
    
    setConnectionStatus: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
      if (!action.payload) {
        state.lastUpdate = null;
      }
    },
    
    clearHistory: (state) => {
      state.history = [];
    },
  },
});

export const {
  updateInstrumentData,
  updateWeatherData,
  updatePosition,
  setConnectionStatus,
  clearHistory,
} = instrumentsSlice.actions;

export default instrumentsSlice.reducer;