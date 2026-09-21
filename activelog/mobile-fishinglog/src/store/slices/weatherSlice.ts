import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { WeatherData, WeatherForecast, WeatherAlert } from '@/types';

interface WeatherState {
  current: WeatherData;
  forecast: WeatherForecast;
  alerts: WeatherAlert[];
  isLoading: boolean;
  lastUpdated: Date;
  settings: {
    location: {
      latitude: number;
      longitude: number;
      name: string;
    };
    units: 'metric' | 'imperial';
    alerts_enabled: boolean;
    auto_refresh: boolean;
    refresh_interval: number;
  };
}

const initialState: WeatherState = {
  current: {
    temperature: 22.5,
    feels_like: 24.8,
    humidity: 68,
    pressure: 1013.2,
    pressure_trend: 'stable',
    wind_speed: 12.3,
    wind_direction: 225,
    wind_gust: 16.8,
    visibility: 15.2,
    uv_index: 6,
    condition: 'partly_cloudy',
    wave_height: 1.2,
    swell_height: 0.8,
    swell_period: 8,
    tides: [
      {
        type: 'high',
        time: '06:45',
        height: 3.2,
      },
      {
        type: 'low',
        time: '12:30',
        height: 0.8,
      },
      {
        type: 'high',
        time: '18:15',
        height: 3.4,
      },
      {
        type: 'low',
        time: '00:45',
        height: 0.6,
      },
    ],
  },
  forecast: {
    hourly: Array.from({ length: 24 }, (_, i) => ({
      time: new Date(Date.now() + i * 60 * 60 * 1000).toISOString(),
      temperature: 22.5 + Math.sin(i / 4) * 3 + Math.random() * 2,
      condition: ['clear', 'partly_cloudy', 'cloudy', 'rain'][Math.floor(Math.random() * 4)] as any,
      wind_speed: 8 + Math.random() * 8,
      wind_direction: 200 + Math.random() * 90,
      precipitation_probability: Math.random() * 100,
    })),
    daily: Array.from({ length: 7 }, (_, i) => ({
      date: new Date(Date.now() + i * 24 * 60 * 60 * 1000).toISOString(),
      high_temp: 25 + Math.random() * 5,
      low_temp: 18 + Math.random() * 4,
      condition: ['clear', 'partly_cloudy', 'cloudy', 'rain'][Math.floor(Math.random() * 4)] as any,
      wind_speed: 10 + Math.random() * 10,
      wind_direction: 180 + Math.random() * 180,
      precipitation_probability: Math.random() * 100,
      sunrise: '06:30',
      sunset: '19:45',
    })),
  },
  alerts: [
    {
      id: 'alert_wind',
      title: 'High Wind Warning',
      description: 'Winds expected to reach 25-30 knots from southwest. Small craft advisory in effect.',
      severity: 'moderate',
      start_time: new Date(),
      end_time: new Date(Date.now() + 8 * 60 * 60 * 1000),
      acknowledged: false,
    },
  ],
  isLoading: false,
  lastUpdated: new Date(),
  settings: {
    location: {
      latitude: 37.8199,
      longitude: -122.4783,
      name: 'San Francisco Bay',
    },
    units: 'metric',
    alerts_enabled: true,
    auto_refresh: true,
    refresh_interval: 30, // minutes
  },
};

const weatherSlice = createSlice({
  name: 'weather',
  initialState,
  reducers: {
    updateCurrentWeather: (state, action: PayloadAction<Partial<WeatherData>>) => {
      state.current = { ...state.current, ...action.payload };
      state.lastUpdated = new Date();
    },

    updateForecast: (state, action: PayloadAction<Partial<WeatherForecast>>) => {
      state.forecast = { ...state.forecast, ...action.payload };
      state.lastUpdated = new Date();
    },

    addWeatherAlert: (state, action: PayloadAction<Omit<WeatherAlert, 'id'>>) => {
      const alert: WeatherAlert = {
        id: `alert_${Date.now()}`,
        ...action.payload,
      };
      state.alerts.unshift(alert);
      
      // Keep only last 20 alerts
      if (state.alerts.length > 20) {
        state.alerts = state.alerts.slice(0, 20);
      }
    },

    acknowledgeWeatherAlert: (state, action: PayloadAction<string>) => {
      const alertIndex = state.alerts.findIndex(a => a.id === action.payload);
      if (alertIndex !== -1) {
        state.alerts[alertIndex].acknowledged = true;
      }
    },

    removeWeatherAlert: (state, action: PayloadAction<string>) => {
      state.alerts = state.alerts.filter(a => a.id !== action.payload);
    },

    setWeatherLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },

    refreshWeatherData: (state) => {
      state.isLoading = true;
      // Simulate some data changes
      state.current.temperature += (Math.random() - 0.5) * 2;
      state.current.wind_speed += (Math.random() - 0.5) * 4;
      state.current.pressure += (Math.random() - 0.5) * 10;
      state.lastUpdated = new Date();
      state.isLoading = false;
    },

    updateWeatherSettings: (state, action: PayloadAction<Partial<WeatherState['settings']>>) => {
      state.settings = { ...state.settings, ...action.payload };
    },

    updateLocation: (state, action: PayloadAction<{ latitude: number; longitude: number; name?: string }>) => {
      const { latitude, longitude, name } = action.payload;
      state.settings.location = {
        latitude,
        longitude,
        name: name || `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`,
      };
    },

    toggleWeatherAlerts: (state) => {
      state.settings.alerts_enabled = !state.settings.alerts_enabled;
    },

    toggleAutoRefresh: (state) => {
      state.settings.auto_refresh = !state.settings.auto_refresh;
    },

    setRefreshInterval: (state, action: PayloadAction<number>) => {
      state.settings.refresh_interval = Math.max(5, Math.min(120, action.payload));
    },

    setWeatherUnits: (state, action: PayloadAction<'metric' | 'imperial'>) => {
      state.settings.units = action.payload;
    },

    clearWeatherAlerts: (state) => {
      state.alerts = [];
    },

    updateTideData: (state, action: PayloadAction<WeatherData['tides']>) => {
      state.current.tides = action.payload;
      state.lastUpdated = new Date();
    },

    simulateWeatherChange: (state) => {
      // Simulate realistic weather changes for demo purposes
      const conditions = ['clear', 'partly_cloudy', 'cloudy', 'overcast', 'rain'];
      const currentIndex = conditions.indexOf(state.current.condition as string);
      
      // Weather tends to change gradually
      const change = Math.random() < 0.7 ? 0 : Math.random() < 0.5 ? -1 : 1;
      const newIndex = Math.max(0, Math.min(conditions.length - 1, currentIndex + change));
      
      state.current.condition = conditions[newIndex] as any;
      state.current.temperature += (Math.random() - 0.5) * 3;
      state.current.wind_speed = Math.max(0, state.current.wind_speed + (Math.random() - 0.5) * 5);
      state.current.wind_direction = (state.current.wind_direction + (Math.random() - 0.5) * 30) % 360;
      
      // Update forecast to match current trends
      state.forecast.hourly.forEach((hour, index) => {
        if (index < 6) { // Update next 6 hours to be consistent
          hour.condition = state.current.condition;
          hour.temperature = state.current.temperature + (Math.random() - 0.5) * 2;
          hour.wind_speed = state.current.wind_speed + (Math.random() - 0.5) * 3;
        }
      });
      
      state.lastUpdated = new Date();
    },

    addCustomWeatherAlert: (state, action: PayloadAction<{
      title: string;
      description: string;
      threshold_type: 'wind' | 'pressure' | 'temperature' | 'wave';
      threshold_value: number;
      condition: 'above' | 'below';
    }>) => {
      const { title, description, threshold_type, threshold_value, condition } = action.payload;
      
      // Check if custom alert should trigger
      let shouldTrigger = false;
      let currentValue = 0;
      
      switch (threshold_type) {
        case 'wind':
          currentValue = state.current.wind_speed;
          break;
        case 'pressure':
          currentValue = state.current.pressure;
          break;
        case 'temperature':
          currentValue = state.current.temperature;
          break;
        case 'wave':
          currentValue = state.current.wave_height;
          break;
      }
      
      shouldTrigger = condition === 'above' ? 
        currentValue > threshold_value : 
        currentValue < threshold_value;
      
      if (shouldTrigger) {
        const alert: WeatherAlert = {
          id: `custom_alert_${Date.now()}`,
          title,
          description: `${description} Current: ${currentValue.toFixed(1)}`,
          severity: 'moderate',
          start_time: new Date(),
          end_time: new Date(Date.now() + 4 * 60 * 60 * 1000),
          acknowledged: false,
        };
        state.alerts.unshift(alert);
      }
    },
  },
});

export const {
  updateCurrentWeather,
  updateForecast,
  addWeatherAlert,
  acknowledgeWeatherAlert,
  removeWeatherAlert,
  setWeatherLoading,
  refreshWeatherData,
  updateWeatherSettings,
  updateLocation,
  toggleWeatherAlerts,
  toggleAutoRefresh,
  setRefreshInterval,
  setWeatherUnits,
  clearWeatherAlerts,
  updateTideData,
  simulateWeatherChange,
  addCustomWeatherAlert,
} = weatherSlice.actions;

export default weatherSlice.reducer;