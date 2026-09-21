import { Plugin, PluginManifest, PluginContext, TriggerEvent, TriggerResult, api_endpoint, trigger_handler } from '@activelog/plugin-sdk';
import axios from 'axios';
import * as cron from 'node-cron';

interface WeatherData {
  location: string;
  temperature: number;
  humidity: number;
  pressure: number;
  windSpeed: number;
  windDirection: number;
  description: string;
  timestamp: Date;
}

interface Location {
  name: string;
  lat: number;
  lng: number;
}

interface WeatherAlert {
  type: 'high_temp' | 'low_temp' | 'high_wind';
  location: string;
  value: number;
  threshold: number;
  message: string;
}

/**
 * Weather Data Plugin for ActiveLog
 * 
 * Fetches weather data from external APIs and provides real-time weather monitoring
 * with customizable alerts and data storage.
 */
export default class WeatherPlugin extends Plugin {
  private cronJob?: cron.ScheduledTask;
  private weatherCache = new Map<string, WeatherData>();

  getManifest(): PluginManifest {
    return require('./manifest.json');
  }

  /**
   * Initialize the plugin and start scheduled weather updates
   */
  async onLoad(context: PluginContext): Promise<void> {
    await super.onLoad(context);
    this.log('info', 'Weather plugin loaded');
  }

  /**
   * Activate the plugin and start monitoring
   */
  async onActivate(context: PluginContext): Promise<void> {
    await super.onActivate(context);
    this.log('info', 'Weather plugin activated');
    
    // Start scheduled monitoring
    await this.startScheduledUpdates();
    
    // Initial data fetch
    await this.updateAllLocations();
  }

  /**
   * Deactivate the plugin and stop monitoring
   */
  async onDeactivate(context: PluginContext): Promise<void> {
    await super.onDeactivate(context);
    
    if (this.cronJob) {
      this.cronJob.stop();
      this.cronJob = undefined;
    }
    
    this.log('info', 'Weather plugin deactivated');
  }

  /**
   * Handle trigger events (scheduled updates, webhooks)
   */
  @trigger_handler('schedule', 'Handle scheduled weather updates')
  async onTrigger(event: TriggerEvent, context: PluginContext): Promise<TriggerResult> {
    try {
      switch (event.type) {
        case 'schedule':
          await this.updateAllLocations();
          return { success: true, data: { updated: true } };
        
        case 'webhook':
          return await this.handleWebhook(event.data);
        
        default:
          return { success: false, error: 'Unsupported trigger type' };
      }
    } catch (error) {
      this.log('error', 'Trigger execution failed', error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Get current weather for a specific location
   */
  @api_endpoint('/current/:location', 'GET', 'Get current weather for a location')
  async getCurrentWeather(location: string): Promise<WeatherData | null> {
    try {
      // Check cache first
      if (this.weatherCache.has(location)) {
        const cached = this.weatherCache.get(location)!;
        const age = Date.now() - cached.timestamp.getTime();
        
        // Return cached data if less than 30 minutes old
        if (age < 30 * 60 * 1000) {
          return cached;
        }
      }

      // Fetch fresh data
      const weatherData = await this.fetchWeatherData(location);
      
      if (weatherData) {
        this.weatherCache.set(location, weatherData);
        
        // Store in database
        await this.storeWeatherData(weatherData);
        
        // Check for alerts
        await this.checkAlerts(weatherData);
      }

      return weatherData;

    } catch (error) {
      this.log('error', `Failed to get weather for ${location}`, error);
      return null;
    }
  }

  /**
   * Get weather forecast for a location
   */
  @api_endpoint('/forecast/:location', 'GET', 'Get weather forecast for a location')
  async getWeatherForecast(location: string): Promise<WeatherData[]> {
    try {
      const config = this.getConfig();
      const provider = config.provider || 'openweathermap';
      
      let forecastData: WeatherData[] = [];
      
      if (provider === 'openweathermap') {
        forecastData = await this.fetchOpenWeatherMapForecast(location);
      } else if (provider === 'weatherapi') {
        forecastData = await this.fetchWeatherApiForecast(location);
      }

      // Track analytics
      await this.trackEvent('weather_forecast_requested', {
        location,
        provider,
        forecast_days: forecastData.length
      });

      return forecastData;

    } catch (error) {
      this.log('error', `Failed to get forecast for ${location}`, error);
      return [];
    }
  }

  /**
   * List all monitored locations
   */
  @api_endpoint('/locations', 'GET', 'List all monitored locations')
  async getLocations(): Promise<Location[]> {
    const config = this.getConfig();
    return config.locations || [];
  }

  /**
   * Add a new location to monitor
   */
  @api_endpoint('/locations', 'POST', 'Add a new location to monitor')
  async addLocation(locationData: Location): Promise<{ success: boolean; message: string }> {
    try {
      const config = this.getConfig();
      const locations = config.locations || [];
      
      // Check if location already exists
      const exists = locations.some((loc: Location) => 
        loc.name.toLowerCase() === locationData.name.toLowerCase()
      );
      
      if (exists) {
        return { success: false, message: 'Location already exists' };
      }

      // Validate location by fetching weather data
      const weatherData = await this.fetchWeatherData(locationData.name);
      if (!weatherData) {
        return { success: false, message: 'Invalid location or weather data unavailable' };
      }

      // Add to configuration
      locations.push(locationData);
      
      // Update configuration (this would typically update the plugin config)
      await this.updateConfig({ locations });

      this.log('info', `Added new location: ${locationData.name}`);
      
      return { success: true, message: 'Location added successfully' };

    } catch (error) {
      this.log('error', 'Failed to add location', error);
      return { success: false, message: (error as Error).message };
    }
  }

  /**
   * Start scheduled weather updates
   */
  private async startScheduledUpdates(): Promise<void> {
    const trigger = this.getManifest().triggers?.find(t => t.type === 'schedule');
    const cronSchedule = trigger?.config?.cron || '0 */6 * * *';

    this.cronJob = cron.schedule(cronSchedule, async () => {
      this.log('info', 'Starting scheduled weather update');
      await this.updateAllLocations();
    }, {
      scheduled: false
    });

    this.cronJob.start();
    this.log('info', `Scheduled updates started with cron: ${cronSchedule}`);
  }

  /**
   * Update weather data for all configured locations
   */
  private async updateAllLocations(): Promise<void> {
    const config = this.getConfig();
    const locations = config.locations || [];

    this.log('info', `Updating weather for ${locations.length} locations`);

    const results = await this.batchProcess(
      locations,
      async (location: Location) => {
        const weatherData = await this.fetchWeatherData(location.name);
        if (weatherData) {
          this.weatherCache.set(location.name, weatherData);
          await this.storeWeatherData(weatherData);
          await this.checkAlerts(weatherData);
          return { location: location.name, success: true };
        }
        return { location: location.name, success: false };
      },
      3, // batch size
      2  // max concurrent
    );

    const successful = results.filter(r => r.success).length;
    this.log('info', `Updated weather data for ${successful}/${locations.length} locations`);

    // Track analytics
    await this.trackEvent('weather_batch_update', {
      total_locations: locations.length,
      successful_updates: successful,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Fetch weather data from the configured provider
   */
  private async fetchWeatherData(location: string): Promise<WeatherData | null> {
    const config = this.getConfig();
    const provider = config.provider || 'openweathermap';

    try {
      if (provider === 'openweathermap') {
        return await this.fetchOpenWeatherMap(location);
      } else if (provider === 'weatherapi') {
        return await this.fetchWeatherApi(location);
      }
      
      throw new Error(`Unknown weather provider: ${provider}`);
      
    } catch (error) {
      this.log('error', `Failed to fetch weather data for ${location}`, error);
      return null;
    }
  }

  /**
   * Fetch weather data from OpenWeatherMap API
   */
  private async fetchOpenWeatherMap(location: string): Promise<WeatherData | null> {
    const config = this.getConfig();
    const apiKey = config.api_key;
    const units = config.units || 'metric';

    const url = `https://api.openweathermap.org/data/2.5/weather`;
    const params = {
      q: location,
      appid: apiKey,
      units: units
    };

    const response = await this.httpRequest('GET', url, null, null, 30000);
    
    if (response.status !== 200) {
      throw new Error(`OpenWeatherMap API error: ${response.status}`);
    }

    const data = response.data;

    return {
      location: data.name,
      temperature: data.main.temp,
      humidity: data.main.humidity,
      pressure: data.main.pressure,
      windSpeed: data.wind?.speed || 0,
      windDirection: data.wind?.deg || 0,
      description: data.weather[0]?.description || 'Unknown',
      timestamp: new Date()
    };
  }

  /**
   * Fetch weather data from WeatherAPI
   */
  private async fetchWeatherApi(location: string): Promise<WeatherData | null> {
    const config = this.getConfig();
    const apiKey = config.api_key;

    const url = `https://api.weatherapi.com/v1/current.json`;
    const params = {
      key: apiKey,
      q: location,
      aqi: 'no'
    };

    const response = await this.httpRequest('GET', url, params);
    
    if (response.status !== 200) {
      throw new Error(`WeatherAPI error: ${response.status}`);
    }

    const data = response.data;
    const current = data.current;
    const location_data = data.location;

    return {
      location: location_data.name,
      temperature: current.temp_c,
      humidity: current.humidity,
      pressure: current.pressure_mb,
      windSpeed: current.wind_kph,
      windDirection: current.wind_degree,
      description: current.condition.text,
      timestamp: new Date()
    };
  }

  /**
   * Fetch forecast data from OpenWeatherMap
   */
  private async fetchOpenWeatherMapForecast(location: string): Promise<WeatherData[]> {
    const config = this.getConfig();
    const apiKey = config.api_key;
    const units = config.units || 'metric';

    const url = `https://api.openweathermap.org/data/2.5/forecast`;
    const params = {
      q: location,
      appid: apiKey,
      units: units
    };

    const response = await this.httpRequest('GET', url, params);
    const data = response.data;

    return data.list.map((item: any) => ({
      location: data.city.name,
      temperature: item.main.temp,
      humidity: item.main.humidity,
      pressure: item.main.pressure,
      windSpeed: item.wind?.speed || 0,
      windDirection: item.wind?.deg || 0,
      description: item.weather[0]?.description || 'Unknown',
      timestamp: new Date(item.dt * 1000)
    }));
  }

  /**
   * Fetch forecast data from WeatherAPI
   */
  private async fetchWeatherApiForecast(location: string): Promise<WeatherData[]> {
    const config = this.getConfig();
    const apiKey = config.api_key;

    const url = `https://api.weatherapi.com/v1/forecast.json`;
    const params = {
      key: apiKey,
      q: location,
      days: 5,
      aqi: 'no'
    };

    const response = await this.httpRequest('GET', url, params);
    const data = response.data;

    const forecast: WeatherData[] = [];
    
    for (const day of data.forecast.forecastday) {
      for (const hour of day.hour) {
        forecast.push({
          location: data.location.name,
          temperature: hour.temp_c,
          humidity: hour.humidity,
          pressure: hour.pressure_mb,
          windSpeed: hour.wind_kph,
          windDirection: hour.wind_degree,
          description: hour.condition.text,
          timestamp: new Date(hour.time)
        });
      }
    }

    return forecast;
  }

  /**
   * Store weather data in the database
   */
  private async storeWeatherData(data: WeatherData): Promise<void> {
    try {
      const sql = `
        INSERT INTO weather_data (location, temperature, humidity, pressure, 
                                wind_speed, wind_direction, description, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `;
      
      await this.dbQuery(sql, [
        data.location,
        data.temperature,
        data.humidity,
        data.pressure,
        data.windSpeed,
        data.windDirection,
        data.description,
        data.timestamp.toISOString()
      ]);
      
    } catch (error) {
      this.log('error', 'Failed to store weather data', error);
    }
  }

  /**
   * Check for weather alerts based on thresholds
   */
  private async checkAlerts(data: WeatherData): Promise<void> {
    const config = this.getConfig();
    const thresholds = config.alert_thresholds || {};

    const alerts: WeatherAlert[] = [];

    // Check temperature alerts
    if (thresholds.high_temp && data.temperature > thresholds.high_temp) {
      alerts.push({
        type: 'high_temp',
        location: data.location,
        value: data.temperature,
        threshold: thresholds.high_temp,
        message: `High temperature alert: ${data.temperature}°C in ${data.location}`
      });
    }

    if (thresholds.low_temp && data.temperature < thresholds.low_temp) {
      alerts.push({
        type: 'low_temp',
        location: data.location,
        value: data.temperature,
        threshold: thresholds.low_temp,
        message: `Low temperature alert: ${data.temperature}°C in ${data.location}`
      });
    }

    // Check wind alerts
    if (thresholds.high_wind && data.windSpeed > thresholds.high_wind) {
      alerts.push({
        type: 'high_wind',
        location: data.location,
        value: data.windSpeed,
        threshold: thresholds.high_wind,
        message: `High wind alert: ${data.windSpeed} km/h in ${data.location}`
      });
    }

    // Send alerts
    for (const alert of alerts) {
      await this.sendAlert(alert);
    }
  }

  /**
   * Send weather alert notification
   */
  private async sendAlert(alert: WeatherAlert): Promise<void> {
    try {
      const user = this.getCurrentUser();
      
      await this.sendNotification(
        'email',
        user.email,
        `Weather Alert: ${alert.location}`,
        alert.message,
        {
          alert_type: alert.type,
          location: alert.location,
          value: alert.value,
          threshold: alert.threshold
        }
      );

      this.log('info', `Weather alert sent: ${alert.message}`);

      // Track alert in analytics
      await this.trackEvent('weather_alert_sent', {
        alert_type: alert.type,
        location: alert.location,
        value: alert.value,
        threshold: alert.threshold
      });

    } catch (error) {
      this.log('error', 'Failed to send weather alert', error);
    }
  }

  /**
   * Handle webhook requests
   */
  private async handleWebhook(data: any): Promise<TriggerResult> {
    try {
      if (data.action === 'update_location') {
        const location = data.location;
        if (location) {
          const weatherData = await this.fetchWeatherData(location);
          if (weatherData) {
            this.weatherCache.set(location, weatherData);
            await this.storeWeatherData(weatherData);
            return { 
              success: true, 
              data: { 
                location,
                weather: weatherData,
                updated_at: new Date().toISOString()
              } 
            };
          }
        }
      }

      return { success: false, error: 'Invalid webhook action or missing location' };

    } catch (error) {
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Update plugin configuration
   */
  private async updateConfig(updates: any): Promise<void> {
    // In a real implementation, this would update the plugin's configuration
    // For now, we'll just log the update
    this.log('info', 'Configuration update requested', updates);
  }
}