import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Tank, TankReading } from '@/types';

interface TanksState {
  tanks: Tank[];
  readings: TankReading[];
  alertThresholds: {
    low_warning: number;
    critical_warning: number;
  };
}

const initialState: TanksState = {
  tanks: [
    {
      id: 'fuel_main',
      name: 'Main Fuel Tank',
      type: 'fuel',
      capacity: 200,
      current_level: 150,
      unit: 'gallons',
      low_warning: 25,
      critical_warning: 10,
      last_updated: new Date(),
    },
    {
      id: 'water_fresh',
      name: 'Fresh Water Tank',
      type: 'water',
      capacity: 100,
      current_level: 75,
      unit: 'gallons',
      low_warning: 15,
      critical_warning: 5,
      last_updated: new Date(),
    },
  ],
  readings: [],
  alertThresholds: {
    low_warning: 25,
    critical_warning: 10,
  },
};

const tanksSlice = createSlice({
  name: 'tanks',
  initialState,
  reducers: {
    addTank: (state, action: PayloadAction<Omit<Tank, 'id' | 'last_updated'>>) => {
      const tank: Tank = {
        id: `tank_${Date.now()}`,
        last_updated: new Date(),
        ...action.payload,
      };
      state.tanks.push(tank);
    },
    
    updateTank: (state, action: PayloadAction<{ id: string; updates: Partial<Tank> }>) => {
      const { id, updates } = action.payload;
      const tankIndex = state.tanks.findIndex(t => t.id === id);
      if (tankIndex !== -1) {
        state.tanks[tankIndex] = {
          ...state.tanks[tankIndex],
          ...updates,
          last_updated: new Date(),
        };
      }
    },
    
    updateTankLevel: (state, action: PayloadAction<{ tankId: string; level: number; notes?: string }>) => {
      const { tankId, level, notes } = action.payload;
      const tankIndex = state.tanks.findIndex(t => t.id === tankId);
      
      if (tankIndex !== -1) {
        // Update tank level
        state.tanks[tankIndex].current_level = level;
        state.tanks[tankIndex].last_updated = new Date();
        
        // Add reading to history
        const reading: TankReading = {
          id: `reading_${Date.now()}`,
          tank_id: tankId,
          level: level,
          timestamp: new Date(),
          notes,
        };
        
        state.readings.unshift(reading);
        
        // Keep only last 1000 readings
        if (state.readings.length > 1000) {
          state.readings = state.readings.slice(0, 1000);
        }
      }
    },
    
    consumeFuel: (state, action: PayloadAction<{ tankId: string; amount: number }>) => {
      const { tankId, amount } = action.payload;
      const tankIndex = state.tanks.findIndex(t => t.id === tankId && t.type === 'fuel');
      
      if (tankIndex !== -1) {
        const newLevel = Math.max(0, state.tanks[tankIndex].current_level - amount);
        state.tanks[tankIndex].current_level = newLevel;
        state.tanks[tankIndex].last_updated = new Date();
        
        // Add consumption reading
        const reading: TankReading = {
          id: `reading_${Date.now()}`,
          tank_id: tankId,
          level: newLevel,
          timestamp: new Date(),
          notes: `Consumed ${amount} ${state.tanks[tankIndex].unit}`,
        };
        
        state.readings.unshift(reading);
      }
    },
    
    fillTank: (state, action: PayloadAction<{ tankId: string; amount?: number }>) => {
      const { tankId, amount } = action.payload;
      const tankIndex = state.tanks.findIndex(t => t.id === tankId);
      
      if (tankIndex !== -1) {
        const tank = state.tanks[tankIndex];
        const newLevel = amount ? 
          Math.min(tank.capacity, tank.current_level + amount) : 
          tank.capacity;
        
        tank.current_level = newLevel;
        tank.last_updated = new Date();
        
        // Add fill reading
        const reading: TankReading = {
          id: `reading_${Date.now()}`,
          tank_id: tankId,
          level: newLevel,
          timestamp: new Date(),
          notes: amount ? 
            `Added ${amount} ${tank.unit}` : 
            `Filled to capacity (${tank.capacity} ${tank.unit})`,
        };
        
        state.readings.unshift(reading);
      }
    },
    
    deleteTank: (state, action: PayloadAction<string>) => {
      const tankId = action.payload;
      state.tanks = state.tanks.filter(t => t.id !== tankId);
      state.readings = state.readings.filter(r => r.tank_id !== tankId);
    },
    
    updateAlertThresholds: (state, action: PayloadAction<Partial<TanksState['alertThresholds']>>) => {
      state.alertThresholds = { ...state.alertThresholds, ...action.payload };
      
      // Update all tank thresholds
      state.tanks.forEach(tank => {
        if (action.payload.low_warning !== undefined) {
          tank.low_warning = action.payload.low_warning;
        }
        if (action.payload.critical_warning !== undefined) {
          tank.critical_warning = action.payload.critical_warning;
        }
      });
    },
    
    getTankAlerts: (state) => {
      // This would be used by a selector to get tanks that need attention
      return state.tanks.filter(tank => 
        tank.current_level <= tank.critical_warning ||
        tank.current_level <= tank.low_warning
      );
    },
    
    addCustomReading: (state, action: PayloadAction<Omit<TankReading, 'id' | 'timestamp'>>) => {
      const reading: TankReading = {
        id: `reading_${Date.now()}`,
        timestamp: new Date(),
        ...action.payload,
      };
      
      state.readings.unshift(reading);
      
      // Update tank level
      const tankIndex = state.tanks.findIndex(t => t.id === reading.tank_id);
      if (tankIndex !== -1) {
        state.tanks[tankIndex].current_level = reading.level;
        state.tanks[tankIndex].last_updated = new Date();
      }
    },
    
    clearReadingHistory: (state, action: PayloadAction<string>) => {
      const tankId = action.payload;
      state.readings = state.readings.filter(r => r.tank_id !== tankId);
    },
  },
});

export const {
  addTank,
  updateTank,
  updateTankLevel,
  consumeFuel,
  fillTank,
  deleteTank,
  updateAlertThresholds,
  getTankAlerts,
  addCustomReading,
  clearReadingHistory,
} = tanksSlice.actions;

export default tanksSlice.reducer;