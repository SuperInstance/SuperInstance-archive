import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { MaintenanceItem } from '@/types';

interface MaintenanceState {
  items: MaintenanceItem[];
  systems: string[];
  components: { [system: string]: string[] };
}

const initialState: MaintenanceState = {
  items: [],
  systems: [
    'Engine',
    'Electrical',
    'Plumbing',
    'Safety',
    'Navigation',
    'Communication',
    'Hull',
    'Rigging',
    'HVAC'
  ],
  components: {
    Engine: ['Oil Filter', 'Fuel Filter', 'Water Pump', 'Spark Plugs', 'Belts', 'Hoses'],
    Electrical: ['Battery', 'Alternator', 'Wiring', 'Lights', 'Fuses', 'Shore Power'],
    Plumbing: ['Through Hull', 'Seacocks', 'Pumps', 'Hoses', 'Fittings', 'Holding Tank'],
    Safety: ['Fire Extinguisher', 'Life Jackets', 'Flares', 'EPIRB', 'Life Raft', 'Horn'],
    Navigation: ['GPS', 'Compass', 'Charts', 'Radar', 'Sonar', 'AIS'],
    Communication: ['VHF Radio', 'SSB Radio', 'Sat Phone', 'WiFi', 'Cell Booster'],
    Hull: ['Bottom Paint', 'Zincs', 'Propeller', 'Rudder', 'Keel', 'Windows'],
    Rigging: ['Standing Rigging', 'Running Rigging', 'Sails', 'Winches', 'Blocks'],
    HVAC: ['Air Conditioning', 'Heating', 'Ventilation', 'Fans', 'Filters']
  },
};

const maintenanceSlice = createSlice({
  name: 'maintenance',
  initialState,
  reducers: {
    addMaintenanceItem: (state, action: PayloadAction<Omit<MaintenanceItem, 'id'>>) => {
      const item: MaintenanceItem = {
        id: `maintenance_${Date.now()}`,
        ...action.payload,
      };
      
      // Calculate status based on next service date
      const now = new Date();
      const nextService = new Date(item.next_service);
      const daysUntilService = Math.ceil((nextService.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
      
      if (daysUntilService < 0) {
        item.status = 'overdue';
      } else if (daysUntilService <= 7) {
        item.status = 'due';
      } else {
        item.status = 'current';
      }
      
      state.items.push(item);
    },
    
    updateMaintenanceItem: (state, action: PayloadAction<{ id: string; updates: Partial<MaintenanceItem> }>) => {
      const { id, updates } = action.payload;
      const itemIndex = state.items.findIndex(i => i.id === id);
      if (itemIndex !== -1) {
        state.items[itemIndex] = { ...state.items[itemIndex], ...updates };
        
        // Recalculate status if next_service date changed
        if (updates.next_service) {
          const now = new Date();
          const nextService = new Date(updates.next_service);
          const daysUntilService = Math.ceil((nextService.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
          
          if (daysUntilService < 0) {
            state.items[itemIndex].status = 'overdue';
          } else if (daysUntilService <= 7) {
            state.items[itemIndex].status = 'due';
          } else {
            state.items[itemIndex].status = 'current';
          }
        }
      }
    },
    
    completeMaintenanceItem: (state, action: PayloadAction<{ id: string; cost?: number; notes?: string }>) => {
      const { id, cost, notes } = action.payload;
      const itemIndex = state.items.findIndex(i => i.id === id);
      if (itemIndex !== -1) {
        const item = state.items[itemIndex];
        const now = new Date();
        
        // Update last service date
        item.last_service = now;
        
        // Calculate next service date
        let nextServiceDate = new Date(now);
        if (item.interval_days) {
          nextServiceDate.setDate(nextServiceDate.getDate() + item.interval_days);
        } else if (item.interval_hours) {
          // For simplicity, assuming 8 hours of operation per day
          nextServiceDate.setDate(nextServiceDate.getDate() + Math.ceil(item.interval_hours / 8));
        }
        
        item.next_service = nextServiceDate;
        item.status = 'current';
        
        if (cost !== undefined) {
          item.cost = cost;
        }
        
        if (notes) {
          item.notes = notes;
        }
      }
    },
    
    deleteMaintenanceItem: (state, action: PayloadAction<string>) => {
      state.items = state.items.filter(i => i.id !== action.payload);
    },
    
    addSystem: (state, action: PayloadAction<string>) => {
      if (!state.systems.includes(action.payload)) {
        state.systems.push(action.payload);
        state.systems.sort();
        state.components[action.payload] = [];
      }
    },
    
    addComponent: (state, action: PayloadAction<{ system: string; component: string }>) => {
      const { system, component } = action.payload;
      if (state.components[system] && !state.components[system].includes(component)) {
        state.components[system].push(component);
        state.components[system].sort();
      }
    },
    
    updateMaintenanceStatuses: (state) => {
      const now = new Date();
      
      state.items.forEach(item => {
        const nextService = new Date(item.next_service);
        const daysUntilService = Math.ceil((nextService.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
        
        if (daysUntilService < 0) {
          item.status = 'overdue';
          item.priority = 'critical';
        } else if (daysUntilService <= 7) {
          item.status = 'due';
          if (item.priority === 'low') {
            item.priority = 'medium';
          }
        } else {
          item.status = 'current';
        }
      });
    },
    
    snoozeMaintenanceItem: (state, action: PayloadAction<{ id: string; days: number }>) => {
      const { id, days } = action.payload;
      const itemIndex = state.items.findIndex(i => i.id === id);
      if (itemIndex !== -1) {
        const nextService = new Date(state.items[itemIndex].next_service);
        nextService.setDate(nextService.getDate() + days);
        state.items[itemIndex].next_service = nextService;
        
        // Update status
        const now = new Date();
        const daysUntilService = Math.ceil((nextService.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
        
        if (daysUntilService < 0) {
          state.items[itemIndex].status = 'overdue';
        } else if (daysUntilService <= 7) {
          state.items[itemIndex].status = 'due';
        } else {
          state.items[itemIndex].status = 'current';
        }
      }
    },
  },
});

export const {
  addMaintenanceItem,
  updateMaintenanceItem,
  completeMaintenanceItem,
  deleteMaintenanceItem,
  addSystem,
  addComponent,
  updateMaintenanceStatuses,
  snoozeMaintenanceItem,
} = maintenanceSlice.actions;

export default maintenanceSlice.reducer;