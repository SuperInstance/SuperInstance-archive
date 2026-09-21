"""
Weather Windows for Fishing
Advanced weather analysis and optimal fishing window prediction
"""

import asyncio
import json
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class WeatherCondition(Enum):
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    LIGHT_RAIN = "light_rain"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORMS = "thunderstorms"
    FOG = "fog"
    MIST = "mist"

class SeaState(Enum):
    CALM = "calm"              # 0-0.1m waves
    SMOOTH = "smooth"          # 0.1-0.5m waves  
    SLIGHT = "slight"          # 0.5-1.25m waves
    MODERATE = "moderate"      # 1.25-2.5m waves
    ROUGH = "rough"            # 2.5-4m waves
    VERY_ROUGH = "very_rough"  # 4-6m waves
    HIGH = "high"              # 6-9m waves
    VERY_HIGH = "very_high"    # 9m+ waves

class FishingConditionRating(Enum):
    EXCELLENT = "excellent"
    GOOD = "good" 
    FAIR = "fair"
    POOR = "poor"
    DANGEROUS = "dangerous"

@dataclass
class WeatherData:
    timestamp: datetime
    latitude: float
    longitude: float
    temperature: float  # Celsius
    feels_like: float   # Celsius
    humidity: float     # percentage
    pressure: float     # hPa
    wind_speed: float   # m/s
    wind_direction: float  # degrees
    wind_gust: Optional[float] = None  # m/s
    visibility: Optional[float] = None  # km
    uv_index: Optional[float] = None
    cloud_cover: Optional[float] = None  # percentage
    condition: Optional[WeatherCondition] = None
    precipitation: Optional[float] = None  # mm/hr
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        if result.get('condition'):
            result['condition'] = result['condition'].value
        return result

@dataclass
class MarineWeatherData:
    timestamp: datetime
    latitude: float
    longitude: float
    wave_height: float      # meters
    wave_period: float      # seconds
    wave_direction: float   # degrees
    swell_height: Optional[float] = None    # meters
    swell_period: Optional[float] = None    # seconds
    swell_direction: Optional[float] = None # degrees
    water_temperature: Optional[float] = None  # Celsius
    sea_state: Optional[SeaState] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        if result.get('sea_state'):
            result['sea_state'] = result['sea_state'].value
        return result

@dataclass
class FishingWindow:
    start_time: datetime
    end_time: datetime
    location: Tuple[float, float]  # (lat, lon)
    rating: FishingConditionRating
    score: float  # 0-100
    weather: WeatherData
    marine_weather: Optional[MarineWeatherData] = None
    reasons: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'location': self.location,
            'rating': self.rating.value,
            'score': self.score,
            'weather': self.weather.to_dict(),
            'marine_weather': self.marine_weather.to_dict() if self.marine_weather else None,
            'reasons': self.reasons,
            'warnings': self.warnings
        }

class WeatherAPI:
    """Weather API integration (simulated)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    def get_weather_forecast(self, lat: float, lon: float, hours_ahead: int = 72) -> List[WeatherData]:
        """Get weather forecast for location"""
        # In real implementation, would call weather API like OpenWeatherMap, NOAA, etc.
        return self._simulate_weather_forecast(lat, lon, hours_ahead)
    
    def get_marine_forecast(self, lat: float, lon: float, hours_ahead: int = 72) -> List[MarineWeatherData]:
        """Get marine weather forecast"""
        return self._simulate_marine_forecast(lat, lon, hours_ahead)
    
    def _simulate_weather_forecast(self, lat: float, lon: float, hours_ahead: int) -> List[WeatherData]:
        """Simulate weather forecast data"""
        import random
        
        forecast = []
        current_time = datetime.now(timezone.utc)
        
        # Base conditions that vary by season and location
        base_temp = 20.0 + random.uniform(-5, 5)  # Base temperature
        base_pressure = 1013.25 + random.uniform(-20, 20)
        
        for hour in range(0, hours_ahead, 3):  # Every 3 hours
            forecast_time = current_time + timedelta(hours=hour)
            
            # Simulate daily temperature cycle
            hour_of_day = forecast_time.hour
            temp_variation = 5 * math.sin(2 * math.pi * (hour_of_day - 6) / 24)
            temperature = base_temp + temp_variation + random.uniform(-2, 2)
            
            # Simulate weather patterns
            pressure = base_pressure + random.uniform(-5, 5)
            humidity = random.uniform(40, 90)
            wind_speed = random.uniform(0, 15)  # m/s
            wind_direction = random.uniform(0, 360)
            wind_gust = wind_speed + random.uniform(0, 5) if wind_speed > 5 else None
            
            # Simulate conditions based on pressure and other factors
            if pressure < 1000:
                condition = random.choice([WeatherCondition.RAIN, WeatherCondition.CLOUDY, WeatherCondition.OVERCAST])
                precipitation = random.uniform(0.5, 5.0) if condition == WeatherCondition.RAIN else None
            elif pressure > 1025:
                condition = random.choice([WeatherCondition.CLEAR, WeatherCondition.PARTLY_CLOUDY])
                precipitation = None
            else:
                condition = random.choice([WeatherCondition.PARTLY_CLOUDY, WeatherCondition.CLOUDY])
                precipitation = random.uniform(0, 1.0) if random.random() < 0.2 else None
            
            weather_data = WeatherData(
                timestamp=forecast_time,
                latitude=lat,
                longitude=lon,
                temperature=temperature,
                feels_like=temperature - (wind_speed * 0.5),  # Simple wind chill
                humidity=humidity,
                pressure=pressure,
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                wind_gust=wind_gust,
                visibility=random.uniform(5, 20),
                uv_index=random.uniform(1, 8) if 6 <= hour_of_day <= 18 else 0,
                cloud_cover=random.uniform(0, 100),
                condition=condition,
                precipitation=precipitation
            )
            
            forecast.append(weather_data)
        
        return forecast
    
    def _simulate_marine_forecast(self, lat: float, lon: float, hours_ahead: int) -> List[MarineWeatherData]:
        """Simulate marine weather forecast"""
        import random
        
        forecast = []
        current_time = datetime.now(timezone.utc)
        
        for hour in range(0, hours_ahead, 6):  # Every 6 hours
            forecast_time = current_time + timedelta(hours=hour)
            
            # Simulate wave conditions
            wave_height = random.uniform(0.2, 3.0)
            wave_period = random.uniform(4, 12)
            wave_direction = random.uniform(0, 360)
            
            # Determine sea state based on wave height
            if wave_height <= 0.1:
                sea_state = SeaState.CALM
            elif wave_height <= 0.5:
                sea_state = SeaState.SMOOTH
            elif wave_height <= 1.25:
                sea_state = SeaState.SLIGHT
            elif wave_height <= 2.5:
                sea_state = SeaState.MODERATE
            elif wave_height <= 4.0:
                sea_state = SeaState.ROUGH
            else:
                sea_state = SeaState.VERY_ROUGH
            
            # Simulate swell (may be different from wind waves)
            swell_height = random.uniform(0.1, wave_height + 1.0)
            swell_period = random.uniform(8, 20)
            swell_direction = wave_direction + random.uniform(-45, 45)
            
            water_temp = random.uniform(15, 25)  # Seasonal water temperature
            
            marine_data = MarineWeatherData(
                timestamp=forecast_time,
                latitude=lat,
                longitude=lon,
                wave_height=wave_height,
                wave_period=wave_period,
                wave_direction=wave_direction,
                swell_height=swell_height,
                swell_period=swell_period,
                swell_direction=swell_direction % 360,
                water_temperature=water_temp,
                sea_state=sea_state
            )
            
            forecast.append(marine_data)
        
        return forecast

class FishingWeatherAnalyzer:
    """Analyze weather conditions for fishing suitability"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Configurable thresholds for fishing conditions
        self.wind_thresholds = self.config.get('wind_thresholds', {
            'excellent': 5.0,    # m/s (11 mph)
            'good': 8.0,         # m/s (18 mph)
            'fair': 12.0,        # m/s (27 mph)
            'poor': 15.0         # m/s (34 mph)
        })
        
        self.wave_thresholds = self.config.get('wave_thresholds', {
            'excellent': 0.5,    # meters
            'good': 1.25,        # meters
            'fair': 2.0,         # meters
            'poor': 3.0          # meters
        })
        
        self.pressure_thresholds = self.config.get('pressure_thresholds', {
            'stable_min': 1010,  # hPa
            'stable_max': 1025   # hPa
        })
    
    def analyze_weather_conditions(self, weather: WeatherData, 
                                 marine_weather: Optional[MarineWeatherData] = None) -> Tuple[FishingConditionRating, float, List[str], List[str]]:
        """Analyze weather conditions and return rating, score, reasons, and warnings"""
        score = 100.0
        reasons = []
        warnings = []
        
        # Analyze wind conditions
        wind_score, wind_reasons, wind_warnings = self._analyze_wind(weather)
        score = min(score, wind_score)
        reasons.extend(wind_reasons)
        warnings.extend(wind_warnings)
        
        # Analyze precipitation
        precip_score, precip_reasons, precip_warnings = self._analyze_precipitation(weather)
        score = min(score, precip_score)
        reasons.extend(precip_reasons)
        warnings.extend(precip_warnings)
        
        # Analyze pressure trends (would need historical data for real trends)
        pressure_score, pressure_reasons = self._analyze_pressure(weather)
        score = min(score, pressure_score)
        reasons.extend(pressure_reasons)
        
        # Analyze visibility
        if weather.visibility and weather.visibility < 2.0:
            score *= 0.7
            warnings.append(f"Poor visibility: {weather.visibility:.1f} km")
        
        # Analyze marine conditions if available
        if marine_weather:
            marine_score, marine_reasons, marine_warnings = self._analyze_marine_conditions(marine_weather)
            score = min(score, marine_score)
            reasons.extend(marine_reasons)
            warnings.extend(marine_warnings)
        
        # Analyze dangerous conditions
        if self._is_dangerous(weather, marine_weather):
            return FishingConditionRating.DANGEROUS, 0.0, reasons, warnings + ["Dangerous conditions - do not fish"]
        
        # Determine overall rating
        if score >= 80:
            rating = FishingConditionRating.EXCELLENT
        elif score >= 65:
            rating = FishingConditionRating.GOOD
        elif score >= 45:
            rating = FishingConditionRating.FAIR
        else:
            rating = FishingConditionRating.POOR
        
        return rating, score, reasons, warnings
    
    def _analyze_wind(self, weather: WeatherData) -> Tuple[float, List[str], List[str]]:
        """Analyze wind conditions"""
        wind_speed = weather.wind_speed
        reasons = []
        warnings = []
        
        if wind_speed <= self.wind_thresholds['excellent']:
            score = 100.0
            reasons.append(f"Light winds ({wind_speed:.1f} m/s)")
        elif wind_speed <= self.wind_thresholds['good']:
            score = 85.0
            reasons.append(f"Moderate winds ({wind_speed:.1f} m/s)")
        elif wind_speed <= self.wind_thresholds['fair']:
            score = 65.0
            reasons.append(f"Fresh winds ({wind_speed:.1f} m/s)")
            warnings.append("Choppy conditions expected")
        elif wind_speed <= self.wind_thresholds['poor']:
            score = 40.0
            reasons.append(f"Strong winds ({wind_speed:.1f} m/s)")
            warnings.append("Rough conditions")
        else:
            score = 20.0
            reasons.append(f"Very strong winds ({wind_speed:.1f} m/s)")
            warnings.append("Very rough conditions - experienced anglers only")
        
        # Factor in wind gusts
        if weather.wind_gust and weather.wind_gust > wind_speed * 1.5:
            score *= 0.85
            warnings.append(f"Strong gusts up to {weather.wind_gust:.1f} m/s")
        
        return score, reasons, warnings
    
    def _analyze_precipitation(self, weather: WeatherData) -> Tuple[float, List[str], List[str]]:
        """Analyze precipitation conditions"""
        reasons = []
        warnings = []
        
        if weather.condition == WeatherCondition.THUNDERSTORMS:
            return 0.0, [], ["Thunderstorms - unsafe conditions"]
        
        if not weather.precipitation or weather.precipitation < 0.5:
            return 100.0, ["Dry conditions"], []
        elif weather.precipitation < 2.0:
            return 80.0, [], ["Light precipitation"]
        elif weather.precipitation < 5.0:
            return 60.0, [], ["Moderate rain - dress appropriately"]
        else:
            return 30.0, [], ["Heavy rain - poor fishing conditions"]
    
    def _analyze_pressure(self, weather: WeatherData) -> Tuple[float, List[str]]:
        """Analyze barometric pressure"""
        pressure = weather.pressure
        reasons = []
        
        if self.pressure_thresholds['stable_min'] <= pressure <= self.pressure_thresholds['stable_max']:
            score = 100.0
            reasons.append("Stable barometric pressure")
        elif pressure > self.pressure_thresholds['stable_max']:
            score = 90.0
            reasons.append("High pressure system")
        elif pressure > 1000:
            score = 75.0
            reasons.append("Falling pressure")
        else:
            score = 60.0
            reasons.append("Low pressure system")
        
        return score, reasons
    
    def _analyze_marine_conditions(self, marine_weather: MarineWeatherData) -> Tuple[float, List[str], List[str]]:
        """Analyze marine/wave conditions"""
        wave_height = marine_weather.wave_height
        reasons = []
        warnings = []
        
        if wave_height <= self.wave_thresholds['excellent']:
            score = 100.0
            reasons.append(f"Calm seas ({wave_height:.1f}m waves)")
        elif wave_height <= self.wave_thresholds['good']:
            score = 85.0
            reasons.append(f"Slight seas ({wave_height:.1f}m waves)")
        elif wave_height <= self.wave_thresholds['fair']:
            score = 65.0
            reasons.append(f"Moderate seas ({wave_height:.1f}m waves)")
            warnings.append("Boat handling skills required")
        elif wave_height <= self.wave_thresholds['poor']:
            score = 40.0
            reasons.append(f"Rough seas ({wave_height:.1f}m waves)")
            warnings.append("Experienced boaters only")
        else:
            score = 20.0
            reasons.append(f"Very rough seas ({wave_height:.1f}m waves)")
            warnings.append("Dangerous conditions for small boats")
        
        # Analyze sea state
        if marine_weather.sea_state:
            if marine_weather.sea_state in [SeaState.ROUGH, SeaState.VERY_ROUGH]:
                warnings.append(f"Sea state: {marine_weather.sea_state.value}")
        
        return score, reasons, warnings
    
    def _is_dangerous(self, weather: WeatherData, marine_weather: Optional[MarineWeatherData] = None) -> bool:
        """Check for dangerous conditions"""
        # Thunderstorms
        if weather.condition == WeatherCondition.THUNDERSTORMS:
            return True
        
        # Extreme winds
        if weather.wind_speed > 20 or (weather.wind_gust and weather.wind_gust > 25):
            return True
        
        # Very poor visibility
        if weather.visibility and weather.visibility < 0.5:
            return True
        
        # Extreme marine conditions
        if marine_weather and marine_weather.wave_height > 4.0:
            return True
        
        return False

class FishingWeatherService:
    """Main fishing weather service"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.weather_api = WeatherAPI(self.config.get('weather_api_key'))
        self.analyzer = FishingWeatherAnalyzer(self.config.get('analyzer_config', {}))
        
        # Default forecast period
        self.default_forecast_hours = self.config.get('forecast_hours', 72)
    
    def get_current_conditions(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Get current weather conditions for fishing"""
        weather_forecast = self.weather_api.get_weather_forecast(lat, lon, hours_ahead=3)
        marine_forecast = self.weather_api.get_marine_forecast(lat, lon, hours_ahead=6)
        
        if not weather_forecast:
            return None
        
        current_weather = weather_forecast[0]
        current_marine = marine_forecast[0] if marine_forecast else None
        
        rating, score, reasons, warnings = self.analyzer.analyze_weather_conditions(
            current_weather, current_marine
        )
        
        return {
            'timestamp': current_weather.timestamp.isoformat(),
            'location': (lat, lon),
            'rating': rating.value,
            'score': score,
            'weather': current_weather.to_dict(),
            'marine_weather': current_marine.to_dict() if current_marine else None,
            'reasons': reasons,
            'warnings': warnings
        }
    
    def get_fishing_windows(self, lat: float, lon: float, hours_ahead: int = None) -> List[FishingWindow]:
        """Get optimal fishing windows based on weather forecast"""
        if hours_ahead is None:
            hours_ahead = self.default_forecast_hours
        
        weather_forecast = self.weather_api.get_weather_forecast(lat, lon, hours_ahead)
        marine_forecast = self.weather_api.get_marine_forecast(lat, lon, hours_ahead)
        
        # Create marine weather lookup
        marine_lookup = {m.timestamp: m for m in marine_forecast}
        
        windows = []
        
        for weather in weather_forecast:
            # Find closest marine forecast
            marine_weather = None
            closest_time = None
            min_time_diff = timedelta.max
            
            for marine_time in marine_lookup.keys():
                time_diff = abs(weather.timestamp - marine_time)
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_time = marine_time
            
            if closest_time and min_time_diff < timedelta(hours=6):
                marine_weather = marine_lookup[closest_time]
            
            # Analyze conditions
            rating, score, reasons, warnings = self.analyzer.analyze_weather_conditions(
                weather, marine_weather
            )
            
            # Only include windows with fair or better conditions
            if rating != FishingConditionRating.DANGEROUS and score >= 40:
                # Create 4-hour fishing window
                window = FishingWindow(
                    start_time=weather.timestamp,
                    end_time=weather.timestamp + timedelta(hours=4),
                    location=(lat, lon),
                    rating=rating,
                    score=score,
                    weather=weather,
                    marine_weather=marine_weather,
                    reasons=reasons,
                    warnings=warnings
                )
                
                windows.append(window)
        
        # Consolidate overlapping windows
        return self._consolidate_windows(windows)
    
    def _consolidate_windows(self, windows: List[FishingWindow]) -> List[FishingWindow]:
        """Consolidate overlapping fishing windows"""
        if not windows:
            return []
        
        # Sort by start time
        sorted_windows = sorted(windows, key=lambda x: x.start_time)
        consolidated = []
        
        current_window = sorted_windows[0]
        
        for next_window in sorted_windows[1:]:
            # Check if windows overlap or are adjacent
            if next_window.start_time <= current_window.end_time:
                # Merge windows - use better conditions
                if next_window.score > current_window.score:
                    current_window = FishingWindow(
                        start_time=current_window.start_time,
                        end_time=max(current_window.end_time, next_window.end_time),
                        location=next_window.location,
                        rating=next_window.rating,
                        score=next_window.score,
                        weather=next_window.weather,
                        marine_weather=next_window.marine_weather,
                        reasons=next_window.reasons,
                        warnings=next_window.warnings
                    )
                else:
                    current_window.end_time = max(current_window.end_time, next_window.end_time)
            else:
                # No overlap, add current and start new one
                consolidated.append(current_window)
                current_window = next_window
        
        # Add the last window
        consolidated.append(current_window)
        
        # Sort by score and limit results
        return sorted(consolidated, key=lambda x: x.score, reverse=True)[:20]
    
    def get_extended_forecast(self, lat: float, lon: float, days: int = 7) -> Dict[str, Any]:
        """Get extended weather forecast for fishing planning"""
        hours_ahead = days * 24
        weather_forecast = self.weather_api.get_weather_forecast(lat, lon, hours_ahead)
        marine_forecast = self.weather_api.get_marine_forecast(lat, lon, hours_ahead)
        
        # Group by day
        daily_forecasts = {}
        
        for weather in weather_forecast:
            day_key = weather.timestamp.date().isoformat()
            
            if day_key not in daily_forecasts:
                daily_forecasts[day_key] = {
                    'date': day_key,
                    'weather_periods': [],
                    'best_conditions': None,
                    'avg_score': 0,
                    'warnings': []
                }
            
            # Find corresponding marine data
            marine_weather = None
            for marine in marine_forecast:
                if abs(weather.timestamp - marine.timestamp) < timedelta(hours=3):
                    marine_weather = marine
                    break
            
            # Analyze conditions
            rating, score, reasons, warnings = self.analyzer.analyze_weather_conditions(
                weather, marine_weather
            )
            
            period_data = {
                'time': weather.timestamp.isoformat(),
                'rating': rating.value,
                'score': score,
                'weather': weather.to_dict(),
                'marine_weather': marine_weather.to_dict() if marine_weather else None,
                'reasons': reasons,
                'warnings': warnings
            }
            
            daily_forecasts[day_key]['weather_periods'].append(period_data)
            
            # Update best conditions for the day
            if (daily_forecasts[day_key]['best_conditions'] is None or 
                score > daily_forecasts[day_key]['best_conditions']['score']):
                daily_forecasts[day_key]['best_conditions'] = period_data
            
            # Collect unique warnings
            for warning in warnings:
                if warning not in daily_forecasts[day_key]['warnings']:
                    daily_forecasts[day_key]['warnings'].append(warning)
        
        # Calculate average scores
        for day_data in daily_forecasts.values():
            if day_data['weather_periods']:
                scores = [p['score'] for p in day_data['weather_periods']]
                day_data['avg_score'] = sum(scores) / len(scores)
        
        return {
            'location': (lat, lon),
            'forecast_days': days,
            'daily_forecasts': list(daily_forecasts.values()),
            'best_fishing_windows': self.get_fishing_windows(lat, lon, hours_ahead)[:10]
        }
    
    def get_spot_weather_summary(self, lat: float, lon: float) -> Dict[str, Any]:
        """Get comprehensive weather summary for a fishing spot"""
        current = self.get_current_conditions(lat, lon)
        windows = self.get_fishing_windows(lat, lon, hours_ahead=48)
        extended = self.get_extended_forecast(lat, lon, days=3)
        
        return {
            'current_conditions': current,
            'next_48h_windows': windows,
            'extended_forecast': extended,
            'summary': {
                'current_rating': current['rating'] if current else 'unknown',
                'windows_count': len(windows),
                'best_window': windows[0].to_dict() if windows else None,
                'forecast_days': len(extended['daily_forecasts']) if extended else 0
            }
        }

async def main():
    """Example usage of fishing weather service"""
    
    # Initialize weather service
    weather_service = FishingWeatherService({
        'forecast_hours': 72,
        'weather_api_key': None,  # Would use real API key
        'analyzer_config': {
            'wind_thresholds': {
                'excellent': 5.0,
                'good': 8.0,
                'fair': 12.0,
                'poor': 15.0
            }
        }
    })
    
    # Example location (Montauk, NY)
    lat, lon = 41.0488, -71.8558
    
    print("=== Fishing Weather Analysis ===")
    
    # Get current conditions
    current = weather_service.get_current_conditions(lat, lon)
    if current:
        print(f"Current conditions at {lat:.4f}, {lon:.4f}:")
        print(f"- Rating: {current['rating']} (Score: {current['score']:.0f}/100)")
        print(f"- Wind: {current['weather']['wind_speed']:.1f} m/s from {current['weather']['wind_direction']:.0f}°")
        if current['marine_weather']:
            print(f"- Waves: {current['marine_weather']['wave_height']:.1f}m ({current['marine_weather']['sea_state']})")
        print(f"- Reasons: {', '.join(current['reasons'])}")
        if current['warnings']:
            print(f"- Warnings: {', '.join(current['warnings'])}")
    
    # Get fishing windows
    print(f"\nOptimal fishing windows (next 48 hours):")
    windows = weather_service.get_fishing_windows(lat, lon, hours_ahead=48)
    
    for i, window in enumerate(windows[:5], 1):  # Show top 5
        print(f"{i}. {window.start_time.strftime('%m/%d %H:%M')} - {window.end_time.strftime('%H:%M')} UTC")
        print(f"   Rating: {window.rating.value} (Score: {window.score:.0f}/100)")
        print(f"   Wind: {window.weather.wind_speed:.1f} m/s")
        if window.marine_weather:
            print(f"   Waves: {window.marine_weather.wave_height:.1f}m")
        if window.warnings:
            print(f"   Warnings: {', '.join(window.warnings)}")
    
    # Get extended forecast
    print(f"\nExtended forecast (3 days):")
    extended = weather_service.get_extended_forecast(lat, lon, days=3)
    
    for day_forecast in extended['daily_forecasts']:
        date_str = datetime.fromisoformat(day_forecast['date']).strftime('%A, %B %d')
        print(f"\n{date_str}:")
        print(f"  Average fishing score: {day_forecast['avg_score']:.0f}/100")
        
        if day_forecast['best_conditions']:
            best = day_forecast['best_conditions']
            best_time = datetime.fromisoformat(best['time']).strftime('%H:%M')
            print(f"  Best conditions: {best_time} UTC ({best['rating']}, {best['score']:.0f}/100)")
        
        if day_forecast['warnings']:
            print(f"  Warnings: {', '.join(day_forecast['warnings'][:2])}")  # Show first 2 warnings
    
    # Get comprehensive spot summary
    print(f"\nSpot weather summary:")
    summary = weather_service.get_spot_weather_summary(lat, lon)
    
    if summary['summary']['best_window']:
        best_window = summary['summary']['best_window']
        best_start = datetime.fromisoformat(best_window['start_time']).strftime('%m/%d %H:%M')
        print(f"Best upcoming window: {best_start} UTC ({best_window['rating']}, score {best_window['score']:.0f})")
    
    print(f"Total fishing windows found: {summary['summary']['windows_count']}")

if __name__ == "__main__":
    asyncio.run(main())