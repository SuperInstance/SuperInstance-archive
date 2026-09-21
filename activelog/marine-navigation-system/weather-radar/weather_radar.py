"""
Weather Radar Overlay System
Real-time weather radar integration for marine navigation
"""

import asyncio
import aiohttp
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance
import io
import json
import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import base64
import gzip
import math
import colorsys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeatherDataSource(Enum):
    NOAA_NEXRAD = "noaa_nexrad"
    OPENWEATHER = "openweather"
    WEATHERAPI = "weatherapi"
    MARINE_WEATHER = "marine_weather"

class RadarType(Enum):
    PRECIPITATION = "precipitation"
    REFLECTIVITY = "reflectivity"
    VELOCITY = "velocity"
    STORM_RELATIVE = "storm_relative"

@dataclass
class WeatherRadarConfig:
    data_source: WeatherDataSource = WeatherDataSource.NOAA_NEXRAD
    api_key: Optional[str] = None
    update_interval: int = 300  # seconds
    radar_range: float = 100.0  # nautical miles
    opacity: float = 0.7
    color_scheme: str = "precipitation"
    show_lightning: bool = True
    show_wind_barbs: bool = True
    show_pressure_contours: bool = True

@dataclass
class RadarDataPoint:
    latitude: float
    longitude: float
    intensity: float  # dBZ or mm/hr
    timestamp: datetime
    radar_type: RadarType = RadarType.PRECIPITATION

@dataclass
class WeatherAlert:
    alert_id: str
    alert_type: str  # STORM, LIGHTNING, WIND, PRECIPITATION
    severity: str    # LOW, MODERATE, HIGH, SEVERE
    title: str
    description: str
    area_coordinates: List[Tuple[float, float]]
    start_time: datetime
    end_time: Optional[datetime]
    marine_zones: List[str] = field(default_factory=list)

@dataclass
class LightningStrike:
    latitude: float
    longitude: float
    timestamp: datetime
    intensity: float  # peak current in kA
    cloud_to_ground: bool = True

@dataclass
class WindBarb:
    latitude: float
    longitude: float
    wind_speed: float  # knots
    wind_direction: float  # degrees
    timestamp: datetime

@dataclass
class PressureContour:
    coordinates: List[Tuple[float, float]]
    pressure: float  # millibars
    contour_type: str  # HIGH, LOW, FRONT

@dataclass
class WeatherRadarData:
    radar_points: List[RadarDataPoint] = field(default_factory=list)
    lightning_strikes: List[LightningStrike] = field(default_factory=list)
    wind_barbs: List[WindBarb] = field(default_factory=list)
    pressure_contours: List[PressureContour] = field(default_factory=list)
    weather_alerts: List[WeatherAlert] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    coverage_area: Tuple[float, float, float, float] = (0, 0, 0, 0)  # lat_min, lat_max, lon_min, lon_max

class NOAANexradProvider:
    """NOAA NEXRAD weather radar data provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.weather.gov"
        self.nexrad_base = "https://nomads.ncep.noaa.gov"
        self.session = None
        
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def get_radar_data(self, center_lat: float, center_lon: float, 
                           radius_nm: float) -> WeatherRadarData:
        """Get NEXRAD radar data for specified area"""
        try:
            # Get radar stations in area
            stations = await self._get_nearby_radar_stations(center_lat, center_lon, radius_nm)
            
            radar_data = WeatherRadarData()
            
            for station in stations:
                # Get latest radar data for station
                station_data = await self._get_station_radar_data(station)
                radar_data.radar_points.extend(station_data.radar_points)
            
            # Get weather alerts
            alerts = await self._get_weather_alerts(center_lat, center_lon, radius_nm)
            radar_data.weather_alerts = alerts
            
            # Get lightning data
            lightning = await self._get_lightning_data(center_lat, center_lon, radius_nm)
            radar_data.lightning_strikes = lightning
            
            return radar_data
            
        except Exception as e:
            logger.error(f"Error getting NEXRAD data: {e}")
            return WeatherRadarData()
    
    async def _get_nearby_radar_stations(self, lat: float, lon: float, 
                                       radius_nm: float) -> List[str]:
        """Find NEXRAD stations within radius"""
        # NEXRAD station locations (simplified list)
        nexrad_stations = {
            'KABR': (45.456, -98.413),
            'KAMA': (35.233, -101.709),
            'KBGM': (42.200, -75.985),
            'KBIS': (46.771, -100.760),
            'KBMX': (33.172, -86.770),
            'KBOX': (41.956, -71.137),
            'KBRO': (25.916, -97.419),
            'KBUF': (42.949, -78.737),
            # Add more stations as needed
        }
        
        nearby_stations = []
        radius_deg = radius_nm / 60.0  # Convert nautical miles to degrees (approximate)
        
        for station_id, (station_lat, station_lon) in nexrad_stations.items():
            distance = math.sqrt((lat - station_lat)**2 + (lon - station_lon)**2)
            if distance <= radius_deg:
                nearby_stations.append(station_id)
        
        return nearby_stations[:3]  # Limit to 3 closest stations
    
    async def _get_station_radar_data(self, station_id: str) -> WeatherRadarData:
        """Get radar data for specific station"""
        try:
            url = f"{self.nexrad_base}/pub/data/nccf/com/radar/{station_id.lower()}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    # Parse NEXRAD Level II data (simplified)
                    data = await response.read()
                    return self._parse_nexrad_data(data, station_id)
                else:
                    logger.warning(f"Failed to get data for station {station_id}: {response.status}")
                    return WeatherRadarData()
                    
        except Exception as e:
            logger.error(f"Error getting station data for {station_id}: {e}")
            return WeatherRadarData()
    
    def _parse_nexrad_data(self, data: bytes, station_id: str) -> WeatherRadarData:
        """Parse NEXRAD Level II data (simplified implementation)"""
        # This is a simplified parser - actual NEXRAD data requires complex parsing
        radar_data = WeatherRadarData()
        
        try:
            # Simulate radar data points in a grid around the station
            # In reality, this would parse the actual NEXRAD data format
            station_coords = self._get_station_coordinates(station_id)
            if station_coords:
                lat, lon = station_coords
                
                # Generate sample radar points in a grid
                for i in range(-20, 21, 2):
                    for j in range(-20, 21, 2):
                        point_lat = lat + i * 0.01
                        point_lon = lon + j * 0.01
                        
                        # Simulate reflectivity based on distance from center
                        distance = math.sqrt(i**2 + j**2)
                        if distance < 20:
                            intensity = max(0, 50 - distance * 2.5 + np.random.normal(0, 5))
                            
                            radar_data.radar_points.append(RadarDataPoint(
                                latitude=point_lat,
                                longitude=point_lon,
                                intensity=intensity,
                                timestamp=datetime.now(),
                                radar_type=RadarType.REFLECTIVITY
                            ))
            
        except Exception as e:
            logger.error(f"Error parsing NEXRAD data: {e}")
        
        return radar_data
    
    def _get_station_coordinates(self, station_id: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for NEXRAD station"""
        stations = {
            'KABR': (45.456, -98.413),
            'KAMA': (35.233, -101.709),
            'KBGM': (42.200, -75.985),
            'KBIS': (46.771, -100.760),
            'KBMX': (33.172, -86.770),
            'KBOX': (41.956, -71.137),
            'KBRO': (25.916, -97.419),
            'KBUF': (42.949, -78.737),
        }
        return stations.get(station_id)
    
    async def _get_weather_alerts(self, lat: float, lon: float, 
                                radius_nm: float) -> List[WeatherAlert]:
        """Get weather alerts for area"""
        try:
            # Get alerts from NWS API
            url = f"{self.base_url}/alerts/active"
            params = {
                'point': f"{lat},{lon}",
                'status': 'actual'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_weather_alerts(data)
                    
        except Exception as e:
            logger.error(f"Error getting weather alerts: {e}")
        
        return []
    
    def _parse_weather_alerts(self, data: Dict[str, Any]) -> List[WeatherAlert]:
        """Parse NWS weather alerts"""
        alerts = []
        
        try:
            features = data.get('features', [])
            
            for feature in features:
                properties = feature.get('properties', {})
                
                alert = WeatherAlert(
                    alert_id=properties.get('id', ''),
                    alert_type=properties.get('event', 'UNKNOWN'),
                    severity=properties.get('severity', 'UNKNOWN'),
                    title=properties.get('headline', ''),
                    description=properties.get('description', ''),
                    area_coordinates=[],  # Would need to parse geometry
                    start_time=self._parse_alert_time(properties.get('onset')),
                    end_time=self._parse_alert_time(properties.get('ends')),
                    marine_zones=properties.get('geocode', {}).get('UGC', [])
                )
                
                alerts.append(alert)
                
        except Exception as e:
            logger.error(f"Error parsing weather alerts: {e}")
        
        return alerts
    
    def _parse_alert_time(self, time_str: Optional[str]) -> Optional[datetime]:
        """Parse alert timestamp"""
        if not time_str:
            return None
        
        try:
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except:
            return None
    
    async def _get_lightning_data(self, lat: float, lon: float, 
                                radius_nm: float) -> List[LightningStrike]:
        """Get lightning data (simulated - would need real lightning network)"""
        # Simulate some lightning strikes
        lightning = []
        
        # Generate random lightning strikes in the area
        for _ in range(np.random.poisson(5)):  # Average of 5 strikes
            strike_lat = lat + np.random.uniform(-0.5, 0.5)
            strike_lon = lon + np.random.uniform(-0.5, 0.5)
            
            lightning.append(LightningStrike(
                latitude=strike_lat,
                longitude=strike_lon,
                timestamp=datetime.now() - timedelta(minutes=np.random.randint(0, 30)),
                intensity=np.random.uniform(10, 100),
                cloud_to_ground=np.random.choice([True, False], p=[0.7, 0.3])
            ))
        
        return lightning
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

class OpenWeatherProvider:
    """OpenWeatherMap weather radar provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.session = None
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def get_radar_data(self, center_lat: float, center_lon: float, 
                           radius_nm: float) -> WeatherRadarData:
        """Get weather radar data from OpenWeatherMap"""
        try:
            radar_data = WeatherRadarData()
            
            # Get precipitation data
            precip_data = await self._get_precipitation_data(center_lat, center_lon)
            radar_data.radar_points.extend(precip_data)
            
            # Get current weather alerts
            alerts = await self._get_current_weather_alerts(center_lat, center_lon)
            radar_data.weather_alerts = alerts
            
            return radar_data
            
        except Exception as e:
            logger.error(f"Error getting OpenWeather data: {e}")
            return WeatherRadarData()
    
    async def _get_precipitation_data(self, lat: float, lon: float) -> List[RadarDataPoint]:
        """Get precipitation radar data"""
        try:
            url = f"{self.base_url}/onecall"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'exclude': 'minutely,daily,alerts'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_precipitation_data(data, lat, lon)
                    
        except Exception as e:
            logger.error(f"Error getting precipitation data: {e}")
        
        return []
    
    def _parse_precipitation_data(self, data: Dict[str, Any], center_lat: float, 
                                center_lon: float) -> List[RadarDataPoint]:
        """Parse precipitation data from OpenWeather"""
        radar_points = []
        
        try:
            current = data.get('current', {})
            precipitation = current.get('rain', {}).get('1h', 0)
            
            if precipitation > 0:
                # Create radar points in a grid around the location
                for i in range(-5, 6):
                    for j in range(-5, 6):
                        point_lat = center_lat + i * 0.01
                        point_lon = center_lon + j * 0.01
                        
                        # Simulate intensity variation
                        distance = math.sqrt(i**2 + j**2)
                        intensity = precipitation * (1 - distance * 0.1) * np.random.uniform(0.5, 1.5)
                        
                        if intensity > 0:
                            radar_points.append(RadarDataPoint(
                                latitude=point_lat,
                                longitude=point_lon,
                                intensity=intensity,
                                timestamp=datetime.now(),
                                radar_type=RadarType.PRECIPITATION
                            ))
                            
        except Exception as e:
            logger.error(f"Error parsing precipitation data: {e}")
        
        return radar_points
    
    async def _get_current_weather_alerts(self, lat: float, lon: float) -> List[WeatherAlert]:
        """Get current weather alerts"""
        # OpenWeatherMap doesn't provide detailed alerts in the free tier
        # This would be implemented with their alerts API
        return []
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

class WeatherRadarRenderer:
    """Weather radar overlay renderer"""
    
    def __init__(self, config: WeatherRadarConfig):
        self.config = config
        self.color_schemes = {
            'precipitation': self._get_precipitation_colors(),
            'reflectivity': self._get_reflectivity_colors(),
            'velocity': self._get_velocity_colors()
        }
    
    def render_overlay(self, radar_data: WeatherRadarData, 
                      map_bounds: Tuple[float, float, float, float],
                      image_size: Tuple[int, int]) -> Image.Image:
        """Render weather radar overlay image"""
        try:
            width, height = image_size
            lat_min, lat_max, lon_min, lon_max = map_bounds
            
            # Create transparent overlay
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Render radar points
            self._render_radar_points(draw, radar_data.radar_points, 
                                    map_bounds, image_size)
            
            # Render lightning strikes
            if self.config.show_lightning:
                self._render_lightning(draw, radar_data.lightning_strikes, 
                                     map_bounds, image_size)
            
            # Render wind barbs
            if self.config.show_wind_barbs:
                self._render_wind_barbs(draw, radar_data.wind_barbs, 
                                      map_bounds, image_size)
            
            # Render pressure contours
            if self.config.show_pressure_contours:
                self._render_pressure_contours(draw, radar_data.pressure_contours, 
                                             map_bounds, image_size)
            
            # Apply opacity
            if self.config.opacity < 1.0:
                overlay = self._apply_opacity(overlay, self.config.opacity)
            
            return overlay
            
        except Exception as e:
            logger.error(f"Error rendering weather overlay: {e}")
            return Image.new('RGBA', image_size, (0, 0, 0, 0))
    
    def _render_radar_points(self, draw: ImageDraw.Draw, 
                           radar_points: List[RadarDataPoint],
                           map_bounds: Tuple[float, float, float, float],
                           image_size: Tuple[int, int]):
        """Render radar precipitation/reflectivity points"""
        lat_min, lat_max, lon_min, lon_max = map_bounds
        width, height = image_size
        
        color_scheme = self.color_schemes.get(self.config.color_scheme, 
                                            self.color_schemes['precipitation'])
        
        for point in radar_points:
            if (lat_min <= point.latitude <= lat_max and 
                lon_min <= point.longitude <= lon_max):
                
                # Convert to pixel coordinates
                x = int((point.longitude - lon_min) / (lon_max - lon_min) * width)
                y = int((lat_max - point.latitude) / (lat_max - lat_min) * height)
                
                # Get color based on intensity
                color = self._get_intensity_color(point.intensity, color_scheme)
                
                # Draw radar point (small filled circle)
                radius = 2
                draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                           fill=color, outline=color)
    
    def _render_lightning(self, draw: ImageDraw.Draw, 
                         lightning_strikes: List[LightningStrike],
                         map_bounds: Tuple[float, float, float, float],
                         image_size: Tuple[int, int]):
        """Render lightning strikes"""
        lat_min, lat_max, lon_min, lon_max = map_bounds
        width, height = image_size
        
        current_time = datetime.now()
        
        for strike in lightning_strikes:
            if (lat_min <= strike.latitude <= lat_max and 
                lon_min <= strike.longitude <= lon_max):
                
                # Age of strike in minutes
                age_minutes = (current_time - strike.timestamp).total_seconds() / 60
                
                # Skip old strikes
                if age_minutes > 30:
                    continue
                
                # Convert to pixel coordinates
                x = int((strike.longitude - lon_min) / (lon_max - lon_min) * width)
                y = int((lat_max - strike.latitude) / (lat_max - lat_min) * height)
                
                # Color based on age (brighter for newer strikes)
                alpha = max(0, 255 - int(age_minutes * 8))
                
                if strike.cloud_to_ground:
                    color = (255, 255, 0, alpha)  # Yellow for cloud-to-ground
                else:
                    color = (255, 200, 255, alpha)  # Pink for cloud-to-cloud
                
                # Draw lightning symbol
                self._draw_lightning_symbol(draw, x, y, color)
    
    def _render_wind_barbs(self, draw: ImageDraw.Draw, 
                          wind_barbs: List[WindBarb],
                          map_bounds: Tuple[float, float, float, float],
                          image_size: Tuple[int, int]):
        """Render wind barbs"""
        lat_min, lat_max, lon_min, lon_max = map_bounds
        width, height = image_size
        
        for barb in wind_barbs:
            if (lat_min <= barb.latitude <= lat_max and 
                lon_min <= barb.longitude <= lon_max):
                
                # Convert to pixel coordinates
                x = int((barb.longitude - lon_min) / (lon_max - lon_min) * width)
                y = int((lat_max - barb.latitude) / (lat_max - lat_min) * height)
                
                # Draw wind barb
                self._draw_wind_barb(draw, x, y, barb.wind_speed, barb.wind_direction)
    
    def _render_pressure_contours(self, draw: ImageDraw.Draw, 
                                pressure_contours: List[PressureContour],
                                map_bounds: Tuple[float, float, float, float],
                                image_size: Tuple[int, int]):
        """Render pressure contours"""
        lat_min, lat_max, lon_min, lon_max = map_bounds
        width, height = image_size
        
        for contour in pressure_contours:
            # Convert coordinates to pixels
            pixel_coords = []
            for lat, lon in contour.coordinates:
                if (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
                    x = int((lon - lon_min) / (lon_max - lon_min) * width)
                    y = int((lat_max - lat) / (lat_max - lat_min) * height)
                    pixel_coords.append((x, y))
            
            if len(pixel_coords) > 1:
                # Color based on contour type
                if contour.contour_type == 'HIGH':
                    color = (0, 0, 255, 128)  # Blue for high pressure
                elif contour.contour_type == 'LOW':
                    color = (255, 0, 0, 128)  # Red for low pressure
                else:
                    color = (128, 128, 128, 128)  # Gray for fronts
                
                # Draw contour line
                for i in range(len(pixel_coords) - 1):
                    draw.line([pixel_coords[i], pixel_coords[i+1]], 
                             fill=color, width=2)
    
    def _get_precipitation_colors(self) -> List[Tuple[float, Tuple[int, int, int, int]]]:
        """Get precipitation color scheme"""
        return [
            (0.0, (0, 0, 0, 0)),          # No precipitation - transparent
            (0.1, (0, 255, 0, 64)),       # Light rain - light green
            (0.5, (255, 255, 0, 128)),    # Moderate rain - yellow
            (1.0, (255, 165, 0, 192)),    # Heavy rain - orange
            (2.0, (255, 0, 0, 255)),      # Very heavy rain - red
            (5.0, (255, 0, 255, 255)),    # Extreme rain - magenta
        ]
    
    def _get_reflectivity_colors(self) -> List[Tuple[float, Tuple[int, int, int, int]]]:
        """Get reflectivity color scheme (dBZ)"""
        return [
            (0, (0, 0, 0, 0)),            # No echo - transparent
            (5, (0, 255, 255, 64)),       # Light blue
            (10, (0, 200, 0, 96)),        # Green
            (20, (255, 255, 0, 128)),     # Yellow
            (35, (255, 165, 0, 192)),     # Orange
            (50, (255, 0, 0, 255)),       # Red
            (65, (255, 0, 255, 255)),     # Magenta
        ]
    
    def _get_velocity_colors(self) -> List[Tuple[float, Tuple[int, int, int, int]]]:
        """Get velocity color scheme"""
        return [
            (-50, (0, 255, 0, 255)),      # Inbound - green
            (-20, (0, 200, 100, 192)),    
            (0, (128, 128, 128, 64)),     # No motion - gray
            (20, (255, 200, 100, 192)),   
            (50, (255, 0, 0, 255)),       # Outbound - red
        ]
    
    def _get_intensity_color(self, intensity: float, 
                           color_scheme: List[Tuple[float, Tuple[int, int, int, int]]]) -> Tuple[int, int, int, int]:
        """Get color for given intensity value"""
        for i, (threshold, color) in enumerate(color_scheme):
            if intensity <= threshold:
                if i == 0:
                    return color
                
                # Interpolate between colors
                prev_threshold, prev_color = color_scheme[i-1]
                factor = (intensity - prev_threshold) / (threshold - prev_threshold)
                
                r = int(prev_color[0] + (color[0] - prev_color[0]) * factor)
                g = int(prev_color[1] + (color[1] - prev_color[1]) * factor)
                b = int(prev_color[2] + (color[2] - prev_color[2]) * factor)
                a = int(prev_color[3] + (color[3] - prev_color[3]) * factor)
                
                return (r, g, b, a)
        
        # Return highest intensity color if above all thresholds
        return color_scheme[-1][1]
    
    def _draw_lightning_symbol(self, draw: ImageDraw.Draw, x: int, y: int, 
                              color: Tuple[int, int, int, int]):
        """Draw lightning bolt symbol"""
        # Lightning bolt shape
        points = [
            (x-3, y-6), (x+1, y-2), (x-1, y-2),
            (x+3, y+6), (x-1, y+2), (x+1, y+2)
        ]
        draw.polygon(points, fill=color)
    
    def _draw_wind_barb(self, draw: ImageDraw.Draw, x: int, y: int, 
                       speed: float, direction: float):
        """Draw wind barb symbol"""
        # Convert direction to radians
        angle = math.radians(direction)
        
        # Wind barb length
        length = 15
        
        # Calculate end point
        end_x = x + int(length * math.sin(angle))
        end_y = y - int(length * math.cos(angle))
        
        # Draw main shaft
        draw.line([(x, y), (end_x, end_y)], fill=(255, 255, 255, 255), width=2)
        
        # Draw speed indicators (barbs)
        barb_count = int(speed / 10)  # One barb per 10 knots
        
        for i in range(barb_count):
            barb_pos = 0.7 - i * 0.15  # Position along shaft
            if barb_pos < 0.2:
                break
            
            barb_x = x + int(length * barb_pos * math.sin(angle))
            barb_y = y - int(length * barb_pos * math.cos(angle))
            
            # Perpendicular barb
            perp_x = barb_x + int(5 * math.cos(angle))
            perp_y = barb_y + int(5 * math.sin(angle))
            
            draw.line([(barb_x, barb_y), (perp_x, perp_y)], 
                     fill=(255, 255, 255, 255), width=1)
    
    def _apply_opacity(self, image: Image.Image, opacity: float) -> Image.Image:
        """Apply opacity to entire image"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Create alpha mask
        alpha = image.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        image.putalpha(alpha)
        
        return image

class WeatherRadarManager:
    """Main weather radar overlay manager"""
    
    def __init__(self, config: WeatherRadarConfig):
        self.config = config
        self.provider = None
        self.renderer = WeatherRadarRenderer(config)
        self.latest_data: Optional[WeatherRadarData] = None
        self.update_task: Optional[asyncio.Task] = None
        self.data_callbacks = []
        
        # Initialize provider based on config
        if config.data_source == WeatherDataSource.NOAA_NEXRAD:
            self.provider = NOAANexradProvider(config.api_key)
        elif config.data_source == WeatherDataSource.OPENWEATHER:
            self.provider = OpenWeatherProvider(config.api_key)
        else:
            raise ValueError(f"Unsupported weather data source: {config.data_source}")
    
    async def initialize(self):
        """Initialize the weather radar manager"""
        if self.provider:
            await self.provider.initialize()
        
        logger.info("Weather radar manager initialized")
    
    async def start_updates(self, center_lat: float, center_lon: float, 
                          radius_nm: float):
        """Start automatic weather data updates"""
        if self.update_task:
            self.update_task.cancel()
        
        self.update_task = asyncio.create_task(
            self._update_loop(center_lat, center_lon, radius_nm)
        )
        
        logger.info(f"Started weather updates for {center_lat:.4f}, {center_lon:.4f}")
    
    async def _update_loop(self, center_lat: float, center_lon: float, 
                          radius_nm: float):
        """Background update loop"""
        while True:
            try:
                # Get latest weather data
                weather_data = await self.provider.get_radar_data(
                    center_lat, center_lon, radius_nm
                )
                
                self.latest_data = weather_data
                
                # Notify callbacks
                for callback in self.data_callbacks:
                    try:
                        callback(weather_data)
                    except Exception as e:
                        logger.error(f"Error in weather data callback: {e}")
                
                # Wait for next update
                await asyncio.sleep(self.config.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in weather update loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def stop_updates(self):
        """Stop automatic updates"""
        if self.update_task:
            self.update_task.cancel()
            self.update_task = None
        
        logger.info("Stopped weather updates")
    
    def get_radar_overlay(self, map_bounds: Tuple[float, float, float, float],
                         image_size: Tuple[int, int]) -> Optional[Image.Image]:
        """Get weather radar overlay image"""
        if not self.latest_data:
            return None
        
        return self.renderer.render_overlay(
            self.latest_data, map_bounds, image_size
        )
    
    def get_latest_data(self) -> Optional[WeatherRadarData]:
        """Get latest weather radar data"""
        return self.latest_data
    
    def get_weather_alerts(self) -> List[WeatherAlert]:
        """Get current weather alerts"""
        if self.latest_data:
            return self.latest_data.weather_alerts
        return []
    
    def add_data_callback(self, callback):
        """Add callback for weather data updates"""
        self.data_callbacks.append(callback)
    
    async def cleanup(self):
        """Cleanup resources"""
        self.stop_updates()
        
        if self.provider:
            await self.provider.cleanup()
        
        logger.info("Weather radar manager cleanup completed")

# Example usage
async def example_usage():
    """Example of using the weather radar system"""
    
    # Configuration
    config = WeatherRadarConfig(
        data_source=WeatherDataSource.NOAA_NEXRAD,
        api_key="your_api_key_here",
        update_interval=300,
        radar_range=50.0,
        opacity=0.7,
        show_lightning=True
    )
    
    # Create weather radar manager
    weather_manager = WeatherRadarManager(config)
    
    # Data callback
    def on_weather_data(data: WeatherRadarData):
        print(f"Weather update: {len(data.radar_points)} radar points")
        print(f"Alerts: {len(data.weather_alerts)}")
        print(f"Lightning: {len(data.lightning_strikes)} strikes")
    
    weather_manager.add_data_callback(on_weather_data)
    
    try:
        # Initialize
        await weather_manager.initialize()
        
        # Start updates for Miami area
        await weather_manager.start_updates(25.7617, -80.1918, 50.0)
        
        # Generate overlay example
        await asyncio.sleep(5)  # Wait for first data
        
        # Map bounds (lat_min, lat_max, lon_min, lon_max)
        map_bounds = (25.0, 26.5, -81.0, -79.5)
        overlay = weather_manager.get_radar_overlay(map_bounds, (800, 600))
        
        if overlay:
            overlay.save('/tmp/weather_overlay.png')
            print("Weather overlay saved to /tmp/weather_overlay.png")
        
        # Run for 30 seconds
        await asyncio.sleep(30)
        
    finally:
        await weather_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(example_usage())