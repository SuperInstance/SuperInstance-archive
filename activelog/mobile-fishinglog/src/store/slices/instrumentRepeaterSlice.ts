import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { InstrumentDisplay, CustomInstrument, DisplayLayout } from '@/types';

interface InstrumentRepeaterState {
  displays: InstrumentDisplay[];
  customInstruments: CustomInstrument[];
  layout: DisplayLayout;
  liveData: Record<string, number>;
  isSimulating: boolean;
  alertsEnabled: boolean;
  activeAlerts: Array<{
    id: string;
    display_id: string;
    type: 'warning' | 'critical';
    message: string;
    timestamp: Date;
  }>;
}

const initialState: InstrumentRepeaterState = {
  displays: [
    {
      id: 'depth_main',
      name: 'Depth',
      dataSource: 'depth',
      position: { x: 0, y: 0, width: 2, height: 2 },
      displayType: 'digital',
      enabled: true,
      units: 'm',
      precision: 1,
      ranges: {
        min: 0,
        max: 100,
        warning: 5,
        critical: 2,
      },
      appearance: {
        fontSize: 32,
        color: '#00FF88',
        backgroundColor: '#001122',
        showBorder: true,
        showLabel: true,
      },
    },
    {
      id: 'speed_main',
      name: 'Speed',
      dataSource: 'speed',
      position: { x: 2, y: 0, width: 2, height: 2 },
      displayType: 'analog',
      enabled: true,
      units: 'kts',
      precision: 1,
      ranges: {
        min: 0,
        max: 25,
        warning: 20,
        critical: 23,
      },
      appearance: {
        fontSize: 28,
        color: '#00AAFF',
        backgroundColor: '#001122',
        showBorder: true,
        showLabel: true,
      },
    },
    {
      id: 'heading_main',
      name: 'Heading',
      dataSource: 'heading',
      position: { x: 0, y: 2, width: 2, height: 2 },
      displayType: 'compass',
      enabled: true,
      units: '°',
      precision: 0,
      ranges: {
        min: 0,
        max: 360,
        warning: 350,
        critical: 355,
      },
      appearance: {
        fontSize: 24,
        color: '#FFAA00',
        backgroundColor: '#001122',
        showBorder: true,
        showLabel: true,
      },
    },
    {
      id: 'wind_speed',
      name: 'Wind Speed',
      dataSource: 'wind_speed',
      position: { x: 2, y: 2, width: 2, height: 2 },
      displayType: 'linear',
      enabled: true,
      units: 'kts',
      precision: 1,
      ranges: {
        min: 0,
        max: 40,
        warning: 25,
        critical: 35,
      },
      appearance: {
        fontSize: 20,
        color: '#FF8800',
        backgroundColor: '#001122',
        showBorder: true,
        showLabel: true,
      },
    },
  ],
  customInstruments: [],
  layout: {
    columns: 4,
    rows: 6,
    gridSize: 1,
    fullscreen: false,
  },
  liveData: {
    depth: 15.3,
    speed: 8.2,
    heading: 245,
    wind_speed: 12.5,
    wind_direction: 180,
    water_temp: 18.5,
    air_temp: 22.1,
    barometric: 1013.2,
    voltage: 12.4,
    engine_rpm: 1850,
    fuel_flow: 18.5,
    trim: 0,
  },
  isSimulating: true,
  alertsEnabled: true,
  activeAlerts: [],
};

const instrumentRepeaterSlice = createSlice({
  name: 'instrumentRepeater',
  initialState,
  reducers: {
    addInstrumentDisplay: (state, action: PayloadAction<Omit<InstrumentDisplay, 'id' | 'enabled'>>) => {
      const display: InstrumentDisplay = {
        id: `display_${Date.now()}`,
        enabled: true,
        ...action.payload,
      };
      state.displays.push(display);
    },

    updateInstrumentDisplay: (state, action: PayloadAction<{ id: string; updates: Partial<InstrumentDisplay> }>) => {
      const { id, updates } = action.payload;
      const displayIndex = state.displays.findIndex(d => d.id === id);
      if (displayIndex !== -1) {
        state.displays[displayIndex] = { ...state.displays[displayIndex], ...updates };
      }
    },

    deleteInstrumentDisplay: (state, action: PayloadAction<string>) => {
      state.displays = state.displays.filter(d => d.id !== action.payload);
      
      // Clean up related alerts
      state.activeAlerts = state.activeAlerts.filter(a => a.display_id !== action.payload);
    },

    toggleInstrumentDisplay: (state, action: PayloadAction<string>) => {
      const displayIndex = state.displays.findIndex(d => d.id === action.payload);
      if (displayIndex !== -1) {
        state.displays[displayIndex].enabled = !state.displays[displayIndex].enabled;
      }
    },

    updateInstrumentLayout: (state, action: PayloadAction<Partial<DisplayLayout>>) => {
      state.layout = { ...state.layout, ...action.payload };
    },

    moveInstrumentDisplay: (state, action: PayloadAction<{ id: string; position: { x: number; y: number; width: number; height: number } }>) => {
      const { id, position } = action.payload;
      const displayIndex = state.displays.findIndex(d => d.id === id);
      if (displayIndex !== -1) {
        state.displays[displayIndex].position = position;
      }
    },

    addCustomInstrument: (state, action: PayloadAction<Omit<CustomInstrument, 'id'>>) => {
      const instrument: CustomInstrument = {
        id: `custom_${Date.now()}`,
        ...action.payload,
      };
      state.customInstruments.push(instrument);
    },

    updateCustomInstrument: (state, action: PayloadAction<{ id: string; updates: Partial<CustomInstrument> }>) => {
      const { id, updates } = action.payload;
      const instrumentIndex = state.customInstruments.findIndex(i => i.id === id);
      if (instrumentIndex !== -1) {
        state.customInstruments[instrumentIndex] = { ...state.customInstruments[instrumentIndex], ...updates };
      }
    },

    deleteCustomInstrument: (state, action: PayloadAction<string>) => {
      state.customInstruments = state.customInstruments.filter(i => i.id !== action.payload);
    },

    updateInstrumentValue: (state, action: PayloadAction<{ dataSource: string; value: number }>) => {
      const { dataSource, value } = action.payload;
      state.liveData[dataSource] = value;

      // Check for alerts if enabled
      if (state.alertsEnabled) {
        state.displays.forEach(display => {
          if (display.dataSource === dataSource && display.enabled) {
            const existingAlert = state.activeAlerts.find(a => a.display_id === display.id);
            
            // Check for critical alert
            if (value >= display.ranges.critical) {
              if (!existingAlert || existingAlert.type !== 'critical') {
                // Remove existing warning if upgrading to critical
                if (existingAlert) {
                  state.activeAlerts = state.activeAlerts.filter(a => a.id !== existingAlert.id);
                }
                
                state.activeAlerts.push({
                  id: `alert_${Date.now()}`,
                  display_id: display.id,
                  type: 'critical',
                  message: `${display.name} critical: ${value.toFixed(display.precision)}${display.units}`,
                  timestamp: new Date(),
                });
              }
            }
            // Check for warning alert
            else if (value >= display.ranges.warning) {
              if (!existingAlert) {
                state.activeAlerts.push({
                  id: `alert_${Date.now()}`,
                  display_id: display.id,
                  type: 'warning',
                  message: `${display.name} warning: ${value.toFixed(display.precision)}${display.units}`,
                  timestamp: new Date(),
                });
              }
            }
            // Clear alerts if value is back to normal
            else if (existingAlert) {
              state.activeAlerts = state.activeAlerts.filter(a => a.id !== existingAlert.id);
            }
          }
        });
      }
    },

    bulkUpdateInstrumentValues: (state, action: PayloadAction<Record<string, number>>) => {
      Object.entries(action.payload).forEach(([dataSource, value]) => {
        state.liveData[dataSource] = value;
      });
    },

    toggleSimulation: (state) => {
      state.isSimulating = !state.isSimulating;
    },

    startSimulation: (state) => {
      state.isSimulating = true;
    },

    stopSimulation: (state) => {
      state.isSimulating = false;
    },

    toggleAlerts: (state) => {
      state.alertsEnabled = !state.alertsEnabled;
      if (!state.alertsEnabled) {
        state.activeAlerts = [];
      }
    },

    dismissAlert: (state, action: PayloadAction<string>) => {
      state.activeAlerts = state.activeAlerts.filter(a => a.id !== action.payload);
    },

    resetInstrumentAlerts: (state) => {
      state.activeAlerts = [];
    },

    calibrateInstrument: (state, action: PayloadAction<{ displayId: string; offset: number; multiplier: number }>) => {
      const { displayId, offset, multiplier } = action.payload;
      const displayIndex = state.displays.findIndex(d => d.id === displayId);
      if (displayIndex !== -1) {
        // Store calibration data for future use
        state.displays[displayIndex] = {
          ...state.displays[displayIndex],
          calibration: { offset, multiplier }
        };
      }
    },

    resetInstrumentCalibration: (state, action: PayloadAction<string>) => {
      const displayIndex = state.displays.findIndex(d => d.id === action.payload);
      if (displayIndex !== -1) {
        const { calibration, ...display } = state.displays[displayIndex];
        state.displays[displayIndex] = display;
      }
    },

    setDisplayFullscreen: (state, action: PayloadAction<string | null>) => {
      state.layout.fullscreenDisplay = action.payload;
      state.layout.fullscreen = action.payload !== null;
    },

    exportDisplayConfiguration: (state) => {
      // This would trigger an export action handled by middleware
      console.log('Exporting display configuration:', {
        displays: state.displays,
        layout: state.layout,
        customInstruments: state.customInstruments,
      });
    },

    importDisplayConfiguration: (state, action: PayloadAction<{
      displays: InstrumentDisplay[];
      layout: DisplayLayout;
      customInstruments: CustomInstrument[];
    }>) => {
      const { displays, layout, customInstruments } = action.payload;
      state.displays = displays;
      state.layout = layout;
      state.customInstruments = customInstruments;
      state.activeAlerts = []; // Reset alerts after import
    },

    duplicateInstrumentDisplay: (state, action: PayloadAction<string>) => {
      const originalDisplay = state.displays.find(d => d.id === action.payload);
      if (originalDisplay) {
        const duplicatedDisplay: InstrumentDisplay = {
          ...originalDisplay,
          id: `display_${Date.now()}`,
          name: `${originalDisplay.name} Copy`,
          position: {
            ...originalDisplay.position,
            x: originalDisplay.position.x + originalDisplay.position.width,
          },
        };
        state.displays.push(duplicatedDisplay);
      }
    },
  },
});

export const {
  addInstrumentDisplay,
  updateInstrumentDisplay,
  deleteInstrumentDisplay,
  toggleInstrumentDisplay,
  updateInstrumentLayout,
  moveInstrumentDisplay,
  addCustomInstrument,
  updateCustomInstrument,
  deleteCustomInstrument,
  updateInstrumentValue,
  bulkUpdateInstrumentValues,
  toggleSimulation,
  startSimulation,
  stopSimulation,
  toggleAlerts,
  dismissAlert,
  resetInstrumentAlerts,
  calibrateInstrument,
  resetInstrumentCalibration,
  setDisplayFullscreen,
  exportDisplayConfiguration,
  importDisplayConfiguration,
  duplicateInstrumentDisplay,
} = instrumentRepeaterSlice.actions;

export default instrumentRepeaterSlice.reducer;