import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { FishCatch, FishingTrip } from '@/types';

interface FishLogState {
  currentTrip: FishingTrip | null;
  trips: FishingTrip[];
  catches: FishCatch[];
  species: string[];
  baits: string[];
  lures: string[];
}

const initialState: FishLogState = {
  currentTrip: null,
  trips: [],
  catches: [],
  species: [
    'Bass', 'Trout', 'Salmon', 'Tuna', 'Marlin', 'Snapper', 'Grouper', 
    'Mahi-mahi', 'Wahoo', 'Kingfish', 'Amberjack', 'Tarpon', 'Permit'
  ],
  baits: [
    'Live Bait', 'Shrimp', 'Squid', 'Sardines', 'Mackerel', 'Ballyhoo',
    'Pilchards', 'Mullet', 'Pinfish', 'Grunt', 'Cut Bait'
  ],
  lures: [
    'Jig', 'Spoon', 'Spinner', 'Plug', 'Soft Plastic', 'Trolling Lure',
    'Poppers', 'Swimbaits', 'Bucktail', 'Feather Jig', 'Cedar Plug'
  ],
};

const fishLogSlice = createSlice({
  name: 'fishLog',
  initialState,
  reducers: {
    startTrip: (state, action: PayloadAction<Omit<FishingTrip, 'catches' | 'locations' | 'weather'>>) => {
      state.currentTrip = {
        ...action.payload,
        catches: [],
        locations: [],
        weather: [],
      };
    },
    
    endTrip: (state) => {
      if (state.currentTrip) {
        state.currentTrip.endTime = new Date();
        state.trips.push(state.currentTrip);
        state.currentTrip = null;
      }
    },
    
    addCatch: (state, action: PayloadAction<FishCatch>) => {
      state.catches.push(action.payload);
      if (state.currentTrip) {
        state.currentTrip.catches.push(action.payload);
      }
    },
    
    updateCatch: (state, action: PayloadAction<{ id: string; updates: Partial<FishCatch> }>) => {
      const { id, updates } = action.payload;
      
      const catchIndex = state.catches.findIndex(c => c.id === id);
      if (catchIndex !== -1) {
        state.catches[catchIndex] = { ...state.catches[catchIndex], ...updates };
      }
      
      if (state.currentTrip) {
        const tripCatchIndex = state.currentTrip.catches.findIndex(c => c.id === id);
        if (tripCatchIndex !== -1) {
          state.currentTrip.catches[tripCatchIndex] = {
            ...state.currentTrip.catches[tripCatchIndex],
            ...updates
          };
        }
      }
    },
    
    deleteCatch: (state, action: PayloadAction<string>) => {
      const catchId = action.payload;
      state.catches = state.catches.filter(c => c.id !== catchId);
      
      if (state.currentTrip) {
        state.currentTrip.catches = state.currentTrip.catches.filter(c => c.id !== catchId);
      }
    },
    
    addSpecies: (state, action: PayloadAction<string>) => {
      if (!state.species.includes(action.payload)) {
        state.species.push(action.payload);
        state.species.sort();
      }
    },
    
    addBait: (state, action: PayloadAction<string>) => {
      if (!state.baits.includes(action.payload)) {
        state.baits.push(action.payload);
        state.baits.sort();
      }
    },
    
    addLure: (state, action: PayloadAction<string>) => {
      if (!state.lures.includes(action.payload)) {
        state.lures.push(action.payload);
        state.lures.sort();
      }
    },
  },
});

export const {
  startTrip,
  endTrip,
  addCatch,
  updateCatch,
  deleteCatch,
  addSpecies,
  addBait,
  addLure,
} = fishLogSlice.actions;

export default fishLogSlice.reducer;