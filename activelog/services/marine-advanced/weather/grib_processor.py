"""
ActiveLog Marine Advanced Suite - GRIB Weather File Processing and Routing

Advanced weather file analysis, processing, and optimal routing calculations
for marine navigation with storm avoidance and performance optimization.
"""

import asyncio
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import struct
import gzip
import math
from scipy import interpolate, optimize
from scipy.spatial.distance import haversine
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from geopy.distance import geodesic
import warnings
warnings.filterwarnings('ignore')


class WeatherModel(Enum):
    GFS = "gfs"
    ECMWF = "ecmwf"
    NAM = "nam"
    HRRR = "hrrr"
    WAVE_WATCH_III = "ww3"
    CUSTOM = "custom"


class ParameterType(Enum):
    WIND_U = "wind_u"           # U-component of wind (m/s)
    WIND_V = "wind_v"           # V-component of wind (m/s)
    WIND_SPEED = "wind_speed"   # Wind speed (m/s)
    WIND_DIRECTION = "wind_dir" # Wind direction (degrees)
    PRESSURE = "pressure"       # Sea level pressure (Pa)
    TEMPERATURE = "temperature" # Temperature (K)
    HUMIDITY = "humidity"       # Relative humidity (%)
    WAVE_HEIGHT = "wave_height" # Significant wave height (m)
    WAVE_PERIOD = "wave_period" # Wave period (s)
    WAVE_DIRECTION = "wave_dir" # Wave direction (degrees)
    PRECIPITATION = "precip"    # Precipitation rate (kg/m²/s)
    VISIBILITY = "visibility"   # Visibility (m)
    GUST_SPEED = "gust_speed"   # Wind gust speed (m/s)


class RoutingCriteria(Enum):
    FASTEST = "fastest"         # Minimize time
    MOST_COMFORTABLE = "comfort" # Minimize motion/discomfort
    FUEL_EFFICIENT = "fuel"     # Minimize fuel consumption
    WEATHER_AVOIDANCE = "avoid"  # Avoid severe weather
    BALANCED = "balanced"       # Balance all factors


@dataclass
class WeatherDataPoint:
    lat: float
    lon: float
    timestamp: datetime
    parameters: Dict[ParameterType, float]
    forecast_hour: int
    model: WeatherModel


@dataclass
class GriddedWeatherData:
    model: WeatherModel
    init_time: datetime
    forecast_hours: List[int]
    lat_range: Tuple[float, float]
    lon_range: Tuple[float, float]
    lat_resolution: float
    lon_resolution: float
    parameters: Dict[ParameterType, np.ndarray]  # 4D arrays: [time, lat, lon, level]
    metadata: Dict[str, Any]


@dataclass
class WeatherForecast:
    location: Tuple[float, float]
    forecast_time: datetime
    valid_time: datetime
    wind_speed: float
    wind_direction: float
    wave_height: float
    wave_period: float
    pressure: float
    temperature: float
    visibility: float
    weather_severity: float  # 0-1 scale


@dataclass
class RoutePoint:
    lat: float
    lon: float
    timestamp: datetime
    course: float
    speed: float
    weather_conditions: WeatherForecast
    fuel_consumption: float
    comfort_index: float


@dataclass
class WeatherRoute:
    route_id: str
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]
    start_time: datetime
    total_distance: float
    total_time: timedelta
    route_points: List[RoutePoint]
    criteria: RoutingCriteria
    weather_model: WeatherModel
    average_speed: float
    fuel_consumption: float
    max_weather_severity: float
    comfort_rating: float


class GRIBProcessor:
    """GRIB weather file processor with advanced parsing capabilities"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.supported_models = {
            WeatherModel.GFS: {"grid_resolution": 0.25, "forecast_hours": 384},
            WeatherModel.ECMWF: {"grid_resolution": 0.1, "forecast_hours": 240},
            WeatherModel.NAM: {"grid_resolution": 0.11, "forecast_hours": 84},
            WeatherModel.HRRR: {"grid_resolution": 0.03, "forecast_hours": 18}
        }
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize weather database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_files (
                file_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                model TEXT NOT NULL,
                init_time TIMESTAMP NOT NULL,
                processed_time TIMESTAMP,
                lat_min REAL, lat_max REAL,
                lon_min REAL, lon_max REAL,
                forecast_hours TEXT,
                parameters TEXT,
                file_size INTEGER,
                checksum TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT,
                lat REAL, lon REAL,
                forecast_time TIMESTAMP,
                valid_time TIMESTAMP,
                parameter_type TEXT,
                value REAL,
                level REAL,
                FOREIGN KEY (file_id) REFERENCES weather_files (file_id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_weather_spatial 
            ON weather_data (lat, lon, forecast_time, parameter_type)
        """)
        
        conn.commit()
        conn.close()
    
    async def load_grib_file(self, file_path: str, model: WeatherModel = WeatherModel.GFS) -> GriddedWeatherData:
        """Load and parse GRIB file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"GRIB file not found: {file_path}")
        
        # Determine if file is compressed
        if file_path.suffix == '.gz':
            with gzip.open(file_path, 'rb') as f:
                grib_data = f.read()
        else:
            with open(file_path, 'rb') as f:
                grib_data = f.read()
        
        # Parse GRIB messages
        weather_data = await self._parse_grib_data(grib_data, model)
        
        # Store in database
        file_id = await self._store_weather_file(file_path, weather_data)
        weather_data.metadata['file_id'] = file_id
        
        return weather_data
    
    async def _parse_grib_data(self, grib_data: bytes, model: WeatherModel) -> GriddedWeatherData:
        """Parse GRIB binary data"""
        # This is a simplified GRIB parser - in production use pygrib or similar
        
        # GRIB message structure parsing
        messages = await self._extract_grib_messages(grib_data)
        
        if not messages:
            raise ValueError("No valid GRIB messages found")
        
        # Initialize data structure
        init_time = datetime.utcnow()
        forecast_hours = []
        parameters = {}
        lat_range = (-90, 90)
        lon_range = (-180, 180)
        lat_resolution = 0.25
        lon_resolution = 0.25
        
        # Process each message
        for message in messages:
            param_type, forecast_hour, data_array, grid_info = await self._parse_grib_message(message)
            
            if forecast_hour not in forecast_hours:
                forecast_hours.append(forecast_hour)
            
            if param_type not in parameters:
                # Initialize 4D array [time, lat, lon, level]
                grid_shape = (len(forecast_hours), grid_info['nlat'], grid_info['nlon'], 1)
                parameters[param_type] = np.zeros(grid_shape)
            
            # Store data in appropriate array position
            time_idx = forecast_hours.index(forecast_hour)
            parameters[param_type][time_idx, :, :, 0] = data_array
            
            # Update grid information
            lat_range = (grid_info['lat_min'], grid_info['lat_max'])
            lon_range = (grid_info['lon_min'], grid_info['lon_max'])
            lat_resolution = grid_info['lat_res']
            lon_resolution = grid_info['lon_res']
        
        # Sort forecast hours
        forecast_hours.sort()
        
        return GriddedWeatherData(
            model=model,
            init_time=init_time,
            forecast_hours=forecast_hours,
            lat_range=lat_range,
            lon_range=lon_range,
            lat_resolution=lat_resolution,
            lon_resolution=lon_resolution,
            parameters=parameters,
            metadata={
                'total_messages': len(messages),
                'grid_points': grid_info['nlat'] * grid_info['nlon'],
                'parameter_count': len(parameters)
            }
        )
    
    async def _extract_grib_messages(self, grib_data: bytes) -> List[bytes]:
        """Extract individual GRIB messages from file"""
        messages = []
        offset = 0
        
        while offset < len(grib_data):
            # Look for GRIB header "GRIB"
            grib_start = grib_data.find(b'GRIB', offset)
            if grib_start == -1:
                break
            
            # Check GRIB version and read message length
            if grib_start + 16 < len(grib_data):
                # GRIB2 format
                if grib_data[grib_start + 7] == 2:
                    # Read message length (bytes 8-15)
                    msg_length = struct.unpack('>Q', grib_data[grib_start + 8:grib_start + 16])[0]
                else:
                    # GRIB1 format - length in bytes 4-7
                    msg_length = struct.unpack('>I', b'\x00' + grib_data[grib_start + 4:grib_start + 7])[0]
                
                # Extract complete message
                if grib_start + msg_length <= len(grib_data):
                    message = grib_data[grib_start:grib_start + msg_length]
                    messages.append(message)
                    offset = grib_start + msg_length
                else:
                    break
            else:
                break
        
        return messages
    
    async def _parse_grib_message(self, message: bytes) -> Tuple[ParameterType, int, np.ndarray, Dict[str, Any]]:
        """Parse individual GRIB message"""
        # Simplified GRIB message parsing
        # In production, use proper GRIB2 decoder like eccodes or pygrib
        
        # Extract parameter information from GRIB sections
        param_code = struct.unpack('>H', message[20:22])[0] if len(message) > 22 else 0
        forecast_hour = struct.unpack('>H', message[30:32])[0] if len(message) > 32 else 0
        
        # Map parameter codes to types
        param_mapping = {
            2: ParameterType.WIND_U,
            3: ParameterType.WIND_V,
            1: ParameterType.PRESSURE,
            11: ParameterType.TEMPERATURE,
            33: ParameterType.WIND_SPEED,
            34: ParameterType.WIND_DIRECTION
        }
        
        param_type = param_mapping.get(param_code, ParameterType.WIND_SPEED)
        
        # Generate sample data for demonstration
        # In production, decode actual GRIB data values
        nlat, nlon = 181, 361  # Global 0.5 degree grid
        lat_min, lat_max = -90, 90
        lon_min, lon_max = 0, 360
        
        # Create sample weather data
        if param_type == ParameterType.WIND_U:
            data = np.random.normal(0, 5, (nlat, nlon))  # U-component
        elif param_type == ParameterType.WIND_V:
            data = np.random.normal(0, 5, (nlat, nlon))  # V-component
        elif param_type == ParameterType.PRESSURE:
            data = np.random.normal(101325, 1000, (nlat, nlon))  # Pressure in Pa
        elif param_type == ParameterType.TEMPERATURE:
            data = np.random.normal(288, 10, (nlat, nlon))  # Temperature in K
        else:
            data = np.random.exponential(8, (nlat, nlon))  # Wind speed
        
        grid_info = {
            'nlat': nlat,
            'nlon': nlon,
            'lat_min': lat_min,
            'lat_max': lat_max,
            'lon_min': lon_min,
            'lon_max': lon_max,
            'lat_res': (lat_max - lat_min) / (nlat - 1),
            'lon_res': (lon_max - lon_min) / (nlon - 1)
        }
        
        return param_type, forecast_hour, data, grid_info
    
    async def _store_weather_file(self, file_path: Path, weather_data: GriddedWeatherData) -> str:
        """Store weather file metadata in database"""
        file_id = f"grib_{weather_data.model.value}_{weather_data.init_time.strftime('%Y%m%d_%H%M%S')}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO weather_files 
            (file_id, file_path, model, init_time, processed_time,
             lat_min, lat_max, lon_min, lon_max, forecast_hours, parameters, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id, str(file_path), weather_data.model.value, weather_data.init_time,
            datetime.utcnow(), weather_data.lat_range[0], weather_data.lat_range[1],
            weather_data.lon_range[0], weather_data.lon_range[1],
            json.dumps(weather_data.forecast_hours),
            json.dumps([p.value for p in weather_data.parameters.keys()]),
            file_path.stat().st_size if file_path.exists() else 0
        ))
        
        conn.commit()
        conn.close()
        
        return file_id
    
    async def interpolate_weather(self, weather_data: GriddedWeatherData, 
                                lat: float, lon: float, 
                                forecast_time: datetime) -> WeatherForecast:
        """Interpolate weather data at specific location and time"""
        # Find nearest time indices
        forecast_hours = weather_data.forecast_hours
        target_hour = (forecast_time - weather_data.init_time).total_seconds() / 3600
        
        # Interpolate in time
        if target_hour <= forecast_hours[0]:
            time_idx = 0
            time_weight = 0
        elif target_hour >= forecast_hours[-1]:
            time_idx = len(forecast_hours) - 1
            time_weight = 0
        else:
            # Find surrounding time indices
            for i in range(len(forecast_hours) - 1):
                if forecast_hours[i] <= target_hour <= forecast_hours[i + 1]:
                    time_idx = i
                    time_weight = (target_hour - forecast_hours[i]) / (forecast_hours[i + 1] - forecast_hours[i])
                    break
        
        # Normalize longitude to grid range
        grid_lon = lon
        if lon < 0:
            grid_lon += 360
        
        # Find spatial indices
        lat_idx = (lat - weather_data.lat_range[0]) / weather_data.lat_resolution
        lon_idx = (grid_lon - weather_data.lon_range[0]) / weather_data.lon_resolution
        
        # Interpolate each parameter
        interpolated_params = {}
        
        for param_type, data_array in weather_data.parameters.items():
            # Bilinear spatial interpolation
            if 0 <= lat_idx < data_array.shape[1] - 1 and 0 <= lon_idx < data_array.shape[2] - 1:
                lat_i, lon_i = int(lat_idx), int(lon_idx)
                lat_frac = lat_idx - lat_i
                lon_frac = lon_idx - lon_i
                
                # Get surrounding grid points
                v00 = data_array[time_idx, lat_i, lon_i, 0]
                v01 = data_array[time_idx, lat_i, lon_i + 1, 0]
                v10 = data_array[time_idx, lat_i + 1, lon_i, 0]
                v11 = data_array[time_idx, lat_i + 1, lon_i + 1, 0]
                
                # Bilinear interpolation
                v0 = v00 * (1 - lon_frac) + v01 * lon_frac
                v1 = v10 * (1 - lon_frac) + v11 * lon_frac
                interpolated_value = v0 * (1 - lat_frac) + v1 * lat_frac
                
                # Time interpolation if needed
                if time_weight > 0 and time_idx < len(forecast_hours) - 1:
                    v00_next = data_array[time_idx + 1, lat_i, lon_i, 0]
                    v01_next = data_array[time_idx + 1, lat_i, lon_i + 1, 0]
                    v10_next = data_array[time_idx + 1, lat_i + 1, lon_i, 0]
                    v11_next = data_array[time_idx + 1, lat_i + 1, lon_i + 1, 0]
                    
                    v0_next = v00_next * (1 - lon_frac) + v01_next * lon_frac
                    v1_next = v10_next * (1 - lon_frac) + v11_next * lon_frac
                    interpolated_value_next = v0_next * (1 - lat_frac) + v1_next * lat_frac
                    
                    interpolated_value = interpolated_value * (1 - time_weight) + interpolated_value_next * time_weight
                
                interpolated_params[param_type] = interpolated_value
            else:
                # Outside grid bounds - use nearest neighbor
                interpolated_params[param_type] = 0.0
        
        # Calculate derived parameters
        wind_speed = self._calculate_wind_speed(interpolated_params)
        wind_direction = self._calculate_wind_direction(interpolated_params)
        weather_severity = self._calculate_weather_severity(interpolated_params)
        
        return WeatherForecast(
            location=(lat, lon),
            forecast_time=weather_data.init_time,
            valid_time=forecast_time,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            wave_height=interpolated_params.get(ParameterType.WAVE_HEIGHT, 1.0),
            wave_period=interpolated_params.get(ParameterType.WAVE_PERIOD, 6.0),
            pressure=interpolated_params.get(ParameterType.PRESSURE, 101325.0),
            temperature=interpolated_params.get(ParameterType.TEMPERATURE, 288.0),
            visibility=interpolated_params.get(ParameterType.VISIBILITY, 10000.0),
            weather_severity=weather_severity
        )
    
    def _calculate_wind_speed(self, params: Dict[ParameterType, float]) -> float:
        """Calculate wind speed from U/V components"""
        if ParameterType.WIND_SPEED in params:
            return params[ParameterType.WIND_SPEED]
        elif ParameterType.WIND_U in params and ParameterType.WIND_V in params:
            u = params[ParameterType.WIND_U]
            v = params[ParameterType.WIND_V]
            return math.sqrt(u * u + v * v)
        else:
            return 0.0
    
    def _calculate_wind_direction(self, params: Dict[ParameterType, float]) -> float:
        """Calculate wind direction from U/V components"""
        if ParameterType.WIND_DIRECTION in params:
            return params[ParameterType.WIND_DIRECTION]
        elif ParameterType.WIND_U in params and ParameterType.WIND_V in params:
            u = params[ParameterType.WIND_U]
            v = params[ParameterType.WIND_V]
            direction = math.atan2(-u, -v) * 180 / math.pi
            return (direction + 360) % 360  # Convert to 0-360 degrees
        else:
            return 0.0
    
    def _calculate_weather_severity(self, params: Dict[ParameterType, float]) -> float:
        """Calculate overall weather severity (0-1 scale)"""
        severity = 0.0
        
        # Wind severity
        wind_speed = self._calculate_wind_speed(params)
        if wind_speed > 25:  # Gale force
            severity = max(severity, 0.8)
        elif wind_speed > 15:  # Strong breeze
            severity = max(severity, 0.5)
        elif wind_speed > 10:  # Moderate breeze
            severity = max(severity, 0.3)
        
        # Wave severity
        wave_height = params.get(ParameterType.WAVE_HEIGHT, 0)
        if wave_height > 4:
            severity = max(severity, 0.7)
        elif wave_height > 2:
            severity = max(severity, 0.4)
        
        # Visibility severity
        visibility = params.get(ParameterType.VISIBILITY, 10000)
        if visibility < 1000:  # Poor visibility
            severity = max(severity, 0.6)
        elif visibility < 5000:
            severity = max(severity, 0.3)
        
        return min(1.0, severity)


class WeatherRouter:
    """Advanced weather routing system with multiple optimization criteria"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.grib_processor = GRIBProcessor(db_path)
        
        # Vessel performance defaults
        self.default_polar = {
            'max_speed': 12.0,  # knots
            'optimal_wind_angle': 45,  # degrees
            'min_wind_speed': 3,  # knots
            'max_wind_speed': 35,  # knots
            'fuel_consumption_rate': 2.5  # gallons per hour
        }
    
    async def calculate_route(self, start_lat: float, start_lon: float,
                            end_lat: float, end_lon: float,
                            start_time: datetime,
                            weather_data: GriddedWeatherData,
                            criteria: RoutingCriteria = RoutingCriteria.FASTEST,
                            vessel_polar: Optional[Dict[str, float]] = None) -> WeatherRoute:
        """Calculate optimal route using weather data"""
        
        if vessel_polar is None:
            vessel_polar = self.default_polar
        
        # Calculate great circle distance and bearing
        total_distance = self._calculate_distance(start_lat, start_lon, end_lat, end_lon)
        initial_bearing = self._calculate_bearing(start_lat, start_lon, end_lat, end_lon)
        
        # Generate route using isochrone method
        route_points = await self._generate_isochrone_route(
            start_lat, start_lon, end_lat, end_lon, start_time,
            weather_data, criteria, vessel_polar
        )
        
        # Calculate route metrics
        total_time = route_points[-1].timestamp - route_points[0].timestamp
        average_speed = total_distance / (total_time.total_seconds() / 3600)  # knots
        total_fuel = sum(point.fuel_consumption for point in route_points)
        max_severity = max(point.weather_conditions.weather_severity for point in route_points)
        comfort_rating = 1.0 - (sum(1 - point.comfort_index for point in route_points) / len(route_points))
        
        route_id = f"route_{start_time.strftime('%Y%m%d_%H%M%S')}_{criteria.value}"
        
        return WeatherRoute(
            route_id=route_id,
            start_point=(start_lat, start_lon),
            end_point=(end_lat, end_lon),
            start_time=start_time,
            total_distance=total_distance,
            total_time=total_time,
            route_points=route_points,
            criteria=criteria,
            weather_model=weather_data.model,
            average_speed=average_speed,
            fuel_consumption=total_fuel,
            max_weather_severity=max_severity,
            comfort_rating=comfort_rating
        )
    
    async def _generate_isochrone_route(self, start_lat: float, start_lon: float,
                                      end_lat: float, end_lon: float,
                                      start_time: datetime,
                                      weather_data: GriddedWeatherData,
                                      criteria: RoutingCriteria,
                                      vessel_polar: Dict[str, float]) -> List[RoutePoint]:
        """Generate route using isochrone method"""
        
        route_points = []
        current_lat, current_lon = start_lat, start_lon
        current_time = start_time
        
        # Time step for route calculation (1 hour)
        time_step = timedelta(hours=1)
        max_iterations = 100  # Prevent infinite loops
        
        for iteration in range(max_iterations):
            # Calculate bearing and distance to destination
            bearing = self._calculate_bearing(current_lat, current_lon, end_lat, end_lon)
            distance_remaining = self._calculate_distance(current_lat, current_lon, end_lat, end_lon)
            
            # Check if we've reached the destination
            if distance_remaining < 5:  # Within 5 nautical miles
                break
            
            # Get weather conditions at current position and time
            weather = await self.grib_processor.interpolate_weather(
                weather_data, current_lat, current_lon, current_time
            )
            
            # Calculate optimal course and speed based on criteria
            optimal_course, optimal_speed = self._optimize_course_and_speed(
                bearing, weather, criteria, vessel_polar
            )
            
            # Calculate fuel consumption and comfort metrics
            fuel_consumption = self._calculate_fuel_consumption(
                optimal_speed, weather, vessel_polar, time_step
            )
            comfort_index = self._calculate_comfort_index(weather, optimal_speed)
            
            # Create route point
            route_point = RoutePoint(
                lat=current_lat,
                lon=current_lon,
                timestamp=current_time,
                course=optimal_course,
                speed=optimal_speed,
                weather_conditions=weather,
                fuel_consumption=fuel_consumption,
                comfort_index=comfort_index
            )
            
            route_points.append(route_point)
            
            # Calculate next position
            distance_traveled = optimal_speed * (time_step.total_seconds() / 3600)  # nautical miles
            next_lat, next_lon = self._calculate_destination_point(
                current_lat, current_lon, optimal_course, distance_traveled
            )
            
            # Update position and time
            current_lat, current_lon = next_lat, next_lon
            current_time += time_step
        
        return route_points
    
    def _optimize_course_and_speed(self, target_bearing: float, weather: WeatherForecast,
                                 criteria: RoutingCriteria, vessel_polar: Dict[str, float]) -> Tuple[float, float]:
        """Optimize course and speed based on routing criteria"""
        
        # Calculate relative wind angle
        apparent_wind_angle = (weather.wind_direction - target_bearing + 360) % 360
        if apparent_wind_angle > 180:
            apparent_wind_angle = 360 - apparent_wind_angle
        
        # Base speed calculation from polar performance
        base_speed = self._calculate_polar_speed(weather.wind_speed, apparent_wind_angle, vessel_polar)
        
        # Adjust course and speed based on criteria
        if criteria == RoutingCriteria.FASTEST:
            # Minimize time - use optimal VMG (Velocity Made Good)
            course_adjustment = 0
            if apparent_wind_angle < 45:  # Too close to wind
                course_adjustment = 45 - apparent_wind_angle
            speed = base_speed
        
        elif criteria == RoutingCriteria.WEATHER_AVOIDANCE:
            # Avoid severe weather
            course_adjustment = 0
            if weather.weather_severity > 0.6:
                # Deviate around severe weather
                course_adjustment = 30 if weather.wind_direction > target_bearing else -30
            speed = base_speed * (1 - weather.weather_severity * 0.5)
        
        elif criteria == RoutingCriteria.FUEL_EFFICIENT:
            # Optimize for fuel efficiency
            course_adjustment = 0
            # Reduce speed in adverse conditions
            if weather.weather_severity > 0.4:
                speed = base_speed * 0.8
            else:
                speed = base_speed * 0.9  # Slightly reduced for efficiency
        
        elif criteria == RoutingCriteria.MOST_COMFORTABLE:
            # Minimize motion and discomfort
            course_adjustment = 0
            if weather.wave_height > 2.0:
                # Adjust course to reduce wave impact
                course_adjustment = 20
            speed = base_speed * (1 - weather.weather_severity * 0.3)
        
        else:  # BALANCED
            # Balance all factors
            course_adjustment = weather.weather_severity * 15
            speed = base_speed * (1 - weather.weather_severity * 0.2)
        
        optimal_course = (target_bearing + course_adjustment + 360) % 360
        optimal_speed = max(2.0, min(vessel_polar['max_speed'], speed))
        
        return optimal_course, optimal_speed
    
    def _calculate_polar_speed(self, wind_speed: float, wind_angle: float,
                             vessel_polar: Dict[str, float]) -> float:
        """Calculate vessel speed from polar performance curve"""
        
        if wind_speed < vessel_polar['min_wind_speed']:
            return 2.0  # Minimum speed under engine
        
        if wind_speed > vessel_polar['max_wind_speed']:
            return vessel_polar['max_speed'] * 0.6  # Reduced speed in high winds
        
        # Simplified polar calculation
        # In production, use actual polar data tables
        optimal_angle = vessel_polar['optimal_wind_angle']
        max_speed = vessel_polar['max_speed']
        
        # Speed factor based on wind angle
        if wind_angle < 30:  # Too close to wind
            angle_factor = 0.3
        elif wind_angle < 60:
            angle_factor = 0.8 + (wind_angle - 30) * 0.02
        elif wind_angle < 120:
            angle_factor = 1.0
        elif wind_angle < 150:
            angle_factor = 0.9
        else:  # Running downwind
            angle_factor = 0.7
        
        # Speed factor based on wind strength
        wind_factor = min(1.0, wind_speed / 15.0)
        
        return max_speed * angle_factor * wind_factor
    
    def _calculate_fuel_consumption(self, speed: float, weather: WeatherForecast,
                                  vessel_polar: Dict[str, float], time_step: timedelta) -> float:
        """Calculate fuel consumption for route segment"""
        
        base_consumption = vessel_polar['fuel_consumption_rate']  # gallons per hour
        hours = time_step.total_seconds() / 3600
        
        # Adjust for speed (quadratic relationship)
        speed_factor = (speed / 10.0) ** 2
        
        # Adjust for weather conditions
        weather_factor = 1.0 + weather.weather_severity * 0.5
        
        # Adjust for wave height (increased resistance)
        wave_factor = 1.0 + weather.wave_height * 0.1
        
        total_consumption = base_consumption * speed_factor * weather_factor * wave_factor * hours
        
        return max(0.1, total_consumption)  # Minimum consumption
    
    def _calculate_comfort_index(self, weather: WeatherForecast, speed: float) -> float:
        """Calculate comfort index (0-1 scale, 1 = most comfortable)"""
        
        comfort = 1.0
        
        # Wind comfort
        if weather.wind_speed > 20:
            comfort -= 0.3
        elif weather.wind_speed > 15:
            comfort -= 0.1
        
        # Wave comfort
        if weather.wave_height > 3:
            comfort -= 0.4
        elif weather.wave_height > 1.5:
            comfort -= 0.2
        
        # Speed comfort (higher speeds in rough conditions reduce comfort)
        if weather.weather_severity > 0.5 and speed > 8:
            comfort -= 0.2
        
        # Overall weather severity impact
        comfort -= weather.weather_severity * 0.3
        
        return max(0.0, comfort)
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great circle distance in nautical miles"""
        distance_km = geodesic((lat1, lon1), (lat2, lon2)).kilometers
        return distance_km * 0.539957  # Convert to nautical miles
    
    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate initial bearing from point 1 to point 2"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        
        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        return (bearing_deg + 360) % 360
    
    def _calculate_destination_point(self, lat: float, lon: float, 
                                   bearing: float, distance: float) -> Tuple[float, float]:
        """Calculate destination point given start point, bearing, and distance"""
        R = 3440.065  # Earth radius in nautical miles
        
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        bearing_rad = math.radians(bearing)
        
        lat2_rad = math.asin(math.sin(lat_rad) * math.cos(distance / R) +
                            math.cos(lat_rad) * math.sin(distance / R) * math.cos(bearing_rad))
        
        lon2_rad = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance / R) * math.cos(lat_rad),
            math.cos(distance / R) - math.sin(lat_rad) * math.sin(lat2_rad)
        )
        
        lat2 = math.degrees(lat2_rad)
        lon2 = math.degrees(lon2_rad)
        
        # Normalize longitude
        lon2 = (lon2 + 540) % 360 - 180
        
        return lat2, lon2


async def main():
    """Example usage of GRIB weather processing and routing"""
    
    # Initialize weather processor
    weather_processor = GRIBProcessor("weather.db")
    weather_router = WeatherRouter("weather.db")
    
    # Simulate loading a GRIB file (in production, use actual GRIB data)
    print("Loading sample weather data...")
    
    # Create sample weather data
    sample_weather = GriddedWeatherData(
        model=WeatherModel.GFS,
        init_time=datetime.utcnow(),
        forecast_hours=[0, 6, 12, 18, 24, 30, 36, 42, 48],
        lat_range=(-90, 90),
        lon_range=(0, 360),
        lat_resolution=0.5,
        lon_resolution=0.5,
        parameters={
            ParameterType.WIND_U: np.random.normal(0, 5, (9, 181, 361, 1)),
            ParameterType.WIND_V: np.random.normal(0, 5, (9, 181, 361, 1)),
            ParameterType.PRESSURE: np.random.normal(101325, 1000, (9, 181, 361, 1)),
            ParameterType.WAVE_HEIGHT: np.random.exponential(1.5, (9, 181, 361, 1))
        },
        metadata={'source': 'sample_data'}
    )
    
    print(f"Weather data loaded: {sample_weather.model.value}")
    print(f"Forecast hours: {sample_weather.forecast_hours}")
    print(f"Parameters: {list(sample_weather.parameters.keys())}")
    
    # Test weather interpolation
    test_lat, test_lon = 37.7749, -122.4194  # San Francisco
    test_time = datetime.utcnow() + timedelta(hours=12)
    
    weather_forecast = await weather_processor.interpolate_weather(
        sample_weather, test_lat, test_lon, test_time
    )
    
    print(f"\nWeather forecast for {test_lat:.2f}°N, {test_lon:.2f}°W:")
    print(f"Wind: {weather_forecast.wind_speed:.1f} kts from {weather_forecast.wind_direction:.0f}°")
    print(f"Waves: {weather_forecast.wave_height:.1f}m")
    print(f"Pressure: {weather_forecast.pressure:.0f} Pa")
    print(f"Weather severity: {weather_forecast.weather_severity:.2f}")
    
    # Calculate weather route
    print("\nCalculating optimal route...")
    
    start_lat, start_lon = 37.7749, -122.4194  # San Francisco
    end_lat, end_lon = 21.3099, -157.8581      # Honolulu
    start_time = datetime.utcnow()
    
    route = await weather_router.calculate_route(
        start_lat, start_lon, end_lat, end_lon, start_time,
        sample_weather, RoutingCriteria.FASTEST
    )
    
    print(f"\nRoute calculated: {route.route_id}")
    print(f"Total distance: {route.total_distance:.0f} nautical miles")
    print(f"Total time: {route.total_time}")
    print(f"Average speed: {route.average_speed:.1f} knots")
    print(f"Fuel consumption: {route.fuel_consumption:.1f} gallons")
    print(f"Max weather severity: {route.max_weather_severity:.2f}")
    print(f"Comfort rating: {route.comfort_rating:.2f}")
    print(f"Route points: {len(route.route_points)}")
    
    # Display first few route points
    print("\nFirst 5 route points:")
    for i, point in enumerate(route.route_points[:5]):
        print(f"  {i+1}: {point.lat:.2f}°N, {point.lon:.2f}°W")
        print(f"     Course: {point.course:.0f}°, Speed: {point.speed:.1f} kts")
        print(f"     Wind: {point.weather_conditions.wind_speed:.1f} kts")
        print(f"     Time: {point.timestamp}")


if __name__ == "__main__":
    asyncio.run(main())