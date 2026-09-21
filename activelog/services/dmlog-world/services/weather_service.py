"""
Weather and climate simulation service with gameplay effects.
"""

import random
import math
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
import logging

from ..models.weather import (
    WeatherType, WeatherSeverity, WindDirection, SeasonType, WeatherEventType,
    WeatherConditions, WeatherForecast, GameplayWeatherEffects, WeatherEventSchema,
    ClimateZoneSchema, WeatherGenerationRequest, WeatherQueryRequest, WeatherResponse,
    WeatherEventRequest, AstronomicalData, WeatherAlert, SeasonalWeatherPattern,
    MicroclimateModifier, WeatherTransition
)
from ..models.base import BiomeType, ClimateType, Coordinate
from ..config import Config

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.config = Config()
        self.climate_zones = self._initialize_climate_zones()
        self.weather_transitions = self._initialize_weather_transitions()
        self.seasonal_patterns = self._initialize_seasonal_patterns()
        self.gameplay_effects = self._initialize_gameplay_effects()
        
    def _initialize_climate_zones(self) -> Dict[ClimateType, ClimateZoneSchema]:
        """Initialize climate zone definitions."""
        
        zones = {}
        
        # Temperate climate zone
        zones[ClimateType.TEMPERATE] = ClimateZoneSchema(
            id="temperate_zone",
            name="Temperate Zone",
            climate_type=ClimateType.TEMPERATE,
            biome=BiomeType.TEMPERATE_FOREST,
            bounds={"type": "latitude_band", "min_lat": 30, "max_lat": 60},
            seasonal_params={
                SeasonType.SPRING: {
                    "temperature_range": (5, 20),
                    "humidity_range": (0.4, 0.8),
                    "precipitation_days": 10
                },
                SeasonType.SUMMER: {
                    "temperature_range": (15, 30),
                    "humidity_range": (0.3, 0.7),
                    "precipitation_days": 8
                },
                SeasonType.AUTUMN: {
                    "temperature_range": (5, 20),
                    "humidity_range": (0.5, 0.8),
                    "precipitation_days": 12
                },
                SeasonType.WINTER: {
                    "temperature_range": (-5, 10),
                    "humidity_range": (0.6, 0.9),
                    "precipitation_days": 15
                }
            },
            weather_probabilities={
                SeasonType.SPRING: {
                    WeatherType.CLEAR: 0.3,
                    WeatherType.PARTLY_CLOUDY: 0.25,
                    WeatherType.CLOUDY: 0.2,
                    WeatherType.RAIN: 0.2,
                    WeatherType.THUNDERSTORM: 0.05
                },
                SeasonType.SUMMER: {
                    WeatherType.CLEAR: 0.4,
                    WeatherType.PARTLY_CLOUDY: 0.3,
                    WeatherType.CLOUDY: 0.15,
                    WeatherType.RAIN: 0.1,
                    WeatherType.THUNDERSTORM: 0.05
                },
                SeasonType.AUTUMN: {
                    WeatherType.CLOUDY: 0.3,
                    WeatherType.RAIN: 0.25,
                    WeatherType.PARTLY_CLOUDY: 0.2,
                    WeatherType.CLEAR: 0.15,
                    WeatherType.FOG: 0.1
                },
                SeasonType.WINTER: {
                    WeatherType.CLOUDY: 0.3,
                    WeatherType.SNOW: 0.25,
                    WeatherType.OVERCAST: 0.2,
                    WeatherType.CLEAR: 0.15,
                    WeatherType.FOG: 0.1
                }
            }
        )
        
        # Desert climate zone
        zones[ClimateType.DESERT] = ClimateZoneSchema(
            id="desert_zone",
            name="Desert Zone",
            climate_type=ClimateType.DESERT,
            biome=BiomeType.DESERT,
            bounds={"type": "latitude_band", "min_lat": 15, "max_lat": 35},
            seasonal_params={
                SeasonType.SPRING: {
                    "temperature_range": (15, 35),
                    "humidity_range": (0.1, 0.3),
                    "precipitation_days": 2
                },
                SeasonType.SUMMER: {
                    "temperature_range": (25, 50),
                    "humidity_range": (0.05, 0.2),
                    "precipitation_days": 1
                },
                SeasonType.AUTUMN: {
                    "temperature_range": (15, 35),
                    "humidity_range": (0.1, 0.3),
                    "precipitation_days": 2
                },
                SeasonType.WINTER: {
                    "temperature_range": (5, 25),
                    "humidity_range": (0.15, 0.4),
                    "precipitation_days": 3
                }
            },
            weather_probabilities={
                SeasonType.SPRING: {
                    WeatherType.CLEAR: 0.7,
                    WeatherType.PARTLY_CLOUDY: 0.2,
                    WeatherType.CLOUDY: 0.08,
                    WeatherType.RAIN: 0.02
                },
                SeasonType.SUMMER: {
                    WeatherType.CLEAR: 0.8,
                    WeatherType.PARTLY_CLOUDY: 0.15,
                    WeatherType.CLOUDY: 0.04,
                    WeatherType.RAIN: 0.01
                },
                SeasonType.AUTUMN: {
                    WeatherType.CLEAR: 0.65,
                    WeatherType.PARTLY_CLOUDY: 0.25,
                    WeatherType.CLOUDY: 0.08,
                    WeatherType.RAIN: 0.02
                },
                SeasonType.WINTER: {
                    WeatherType.CLEAR: 0.6,
                    WeatherType.PARTLY_CLOUDY: 0.25,
                    WeatherType.CLOUDY: 0.12,
                    WeatherType.RAIN: 0.03
                }
            }
        )
        
        # Arctic climate zone
        zones[ClimateType.ARCTIC] = ClimateZoneSchema(
            id="arctic_zone",
            name="Arctic Zone", 
            climate_type=ClimateType.ARCTIC,
            biome=BiomeType.ARCTIC,
            bounds={"type": "latitude_band", "min_lat": 60, "max_lat": 90},
            seasonal_params={
                SeasonType.SPRING: {
                    "temperature_range": (-10, 5),
                    "humidity_range": (0.5, 0.8),
                    "precipitation_days": 8
                },
                SeasonType.SUMMER: {
                    "temperature_range": (0, 15),
                    "humidity_range": (0.4, 0.7),
                    "precipitation_days": 6
                },
                SeasonType.AUTUMN: {
                    "temperature_range": (-10, 5),
                    "humidity_range": (0.5, 0.8),
                    "precipitation_days": 10
                },
                SeasonType.WINTER: {
                    "temperature_range": (-30, -5),
                    "humidity_range": (0.7, 0.9),
                    "precipitation_days": 20
                }
            },
            weather_probabilities={
                SeasonType.SPRING: {
                    WeatherType.SNOW: 0.3,
                    WeatherType.CLOUDY: 0.25,
                    WeatherType.OVERCAST: 0.2,
                    WeatherType.CLEAR: 0.15,
                    WeatherType.BLIZZARD: 0.1
                },
                SeasonType.SUMMER: {
                    WeatherType.CLOUDY: 0.3,
                    WeatherType.PARTLY_CLOUDY: 0.25,
                    WeatherType.CLEAR: 0.2,
                    WeatherType.RAIN: 0.15,
                    WeatherType.FOG: 0.1
                },
                SeasonType.AUTUMN: {
                    WeatherType.SNOW: 0.35,
                    WeatherType.CLOUDY: 0.3,
                    WeatherType.OVERCAST: 0.2,
                    WeatherType.CLEAR: 0.1,
                    WeatherType.BLIZZARD: 0.05
                },
                SeasonType.WINTER: {
                    WeatherType.BLIZZARD: 0.25,
                    WeatherType.SNOW: 0.3,
                    WeatherType.OVERCAST: 0.25,
                    WeatherType.CLOUDY: 0.15,
                    WeatherType.CLEAR: 0.05
                }
            }
        )
        
        return zones

    def _initialize_weather_transitions(self) -> List[WeatherTransition]:
        """Initialize weather transition probabilities."""
        
        transitions = []
        
        # Clear weather transitions
        transitions.extend([
            WeatherTransition(
                from_weather=WeatherType.CLEAR,
                to_weather=WeatherType.PARTLY_CLOUDY,
                transition_time=2.0,
                probability=0.4
            ),
            WeatherTransition(
                from_weather=WeatherType.CLEAR,
                to_weather=WeatherType.CLOUDY,
                transition_time=4.0,
                probability=0.2
            )
        ])
        
        # Cloudy weather transitions
        transitions.extend([
            WeatherTransition(
                from_weather=WeatherType.CLOUDY,
                to_weather=WeatherType.RAIN,
                transition_time=1.5,
                probability=0.3
            ),
            WeatherTransition(
                from_weather=WeatherType.CLOUDY,
                to_weather=WeatherType.PARTLY_CLOUDY,
                transition_time=3.0,
                probability=0.4
            )
        ])
        
        # Rain transitions
        transitions.extend([
            WeatherTransition(
                from_weather=WeatherType.RAIN,
                to_weather=WeatherType.CLOUDY,
                transition_time=2.0,
                probability=0.5
            ),
            WeatherTransition(
                from_weather=WeatherType.RAIN,
                to_weather=WeatherType.THUNDERSTORM,
                transition_time=0.5,
                probability=0.1,
                seasonal_modifier={SeasonType.SUMMER: 2.0}
            )
        ])
        
        return transitions

    def _initialize_seasonal_patterns(self) -> Dict[SeasonType, SeasonalWeatherPattern]:
        """Initialize seasonal weather patterns."""
        
        return {
            SeasonType.SPRING: SeasonalWeatherPattern(
                season=SeasonType.SPRING,
                temperature_range=(5, 25),
                humidity_range=(0.4, 0.8),
                precipitation_frequency=10.0,
                common_weather=[WeatherType.RAIN, WeatherType.CLOUDY, WeatherType.PARTLY_CLOUDY],
                rare_weather=[WeatherType.THUNDERSTORM, WeatherType.HAIL]
            ),
            SeasonType.SUMMER: SeasonalWeatherPattern(
                season=SeasonType.SUMMER,
                temperature_range=(15, 35),
                humidity_range=(0.3, 0.7),
                precipitation_frequency=8.0,
                common_weather=[WeatherType.CLEAR, WeatherType.PARTLY_CLOUDY, WeatherType.THUNDERSTORM],
                rare_weather=[WeatherType.HEAVY_RAIN, WeatherType.HAIL]
            ),
            SeasonType.AUTUMN: SeasonalWeatherPattern(
                season=SeasonType.AUTUMN,
                temperature_range=(0, 20),
                humidity_range=(0.5, 0.8),
                precipitation_frequency=12.0,
                common_weather=[WeatherType.RAIN, WeatherType.CLOUDY, WeatherType.FOG],
                rare_weather=[WeatherType.THUNDERSTORM, WeatherType.HEAVY_RAIN]
            ),
            SeasonType.WINTER: SeasonalWeatherPattern(
                season=SeasonType.WINTER,
                temperature_range=(-10, 10),
                humidity_range=(0.6, 0.9),
                precipitation_frequency=15.0,
                common_weather=[WeatherType.SNOW, WeatherType.OVERCAST, WeatherType.CLOUDY],
                rare_weather=[WeatherType.BLIZZARD, WeatherType.HEAVY_SNOW]
            )
        }

    def _initialize_gameplay_effects(self) -> Dict[WeatherType, GameplayWeatherEffects]:
        """Initialize gameplay effects for different weather types."""
        
        effects = {}
        
        # Clear weather - baseline
        effects[WeatherType.CLEAR] = GameplayWeatherEffects()
        
        # Rain effects
        effects[WeatherType.RAIN] = GameplayWeatherEffects(
            movement_speed_modifier=0.8,
            terrain_difficulty_modifier=1.2,
            vision_range_modifier=0.7,
            stealth_modifier=1.3,
            ranged_accuracy_modifier=0.8,
            fire_damage_modifier=0.5,
            exposure_damage=1.0,
            certain_spell_modifiers={"water": 1.5, "fire": 0.5}
        )
        
        effects[WeatherType.HEAVY_RAIN] = GameplayWeatherEffects(
            movement_speed_modifier=0.6,
            terrain_difficulty_modifier=1.5,
            vision_range_modifier=0.4,
            stealth_modifier=1.5,
            ranged_accuracy_modifier=0.6,
            fire_damage_modifier=0.2,
            exposure_damage=2.0,
            certain_spell_modifiers={"water": 2.0, "fire": 0.3}
        )
        
        # Snow effects
        effects[WeatherType.SNOW] = GameplayWeatherEffects(
            movement_speed_modifier=0.7,
            terrain_difficulty_modifier=1.3,
            vision_range_modifier=0.6,
            stealth_modifier=1.2,
            ranged_accuracy_modifier=0.9,
            cold_damage_modifier=1.3,
            exposure_damage=2.0,
            certain_spell_modifiers={"ice": 1.5, "fire": 0.8}
        )
        
        effects[WeatherType.BLIZZARD] = GameplayWeatherEffects(
            movement_speed_modifier=0.3,
            terrain_difficulty_modifier=2.0,
            vision_range_modifier=0.2,
            stealth_modifier=2.0,
            ranged_accuracy_modifier=0.4,
            cold_damage_modifier=2.0,
            exposure_damage=5.0,
            rest_quality_modifier=0.3,
            certain_spell_modifiers={"ice": 2.5, "fire": 0.5}
        )
        
        # Fog effects
        effects[WeatherType.FOG] = GameplayWeatherEffects(
            vision_range_modifier=0.3,
            stealth_modifier=1.8,
            ranged_accuracy_modifier=0.5,
            certain_spell_modifiers={"illusion": 1.5}
        )
        
        # Thunderstorm effects
        effects[WeatherType.THUNDERSTORM] = GameplayWeatherEffects(
            movement_speed_modifier=0.7,
            terrain_difficulty_modifier=1.4,
            vision_range_modifier=0.5,
            stealth_modifier=0.7,  # Thunder masks sound but lightning reveals
            ranged_accuracy_modifier=0.6,
            fire_damage_modifier=0.3,
            exposure_damage=2.5,
            certain_spell_modifiers={"lightning": 2.0, "fire": 0.3, "water": 1.5}
        )
        
        return effects

    async def generate_weather(
        self,
        request: WeatherGenerationRequest,
        db_session: Optional[Session] = None
    ) -> WeatherResponse:
        """Generate weather conditions for a location."""
        
        start_time = datetime.utcnow()
        
        try:
            # Set random seed if provided
            if request.seed:
                random.seed(request.seed)
            
            # Determine climate zone
            climate_zone = await self._determine_climate_zone(request.biome)
            
            # Get current time
            current_time = request.current_time or datetime.utcnow()
            
            # Generate current conditions
            current_conditions = await self._generate_current_conditions(
                climate_zone, request.season, current_time, request.location
            )
            
            # Generate forecast
            forecast = None
            if request.forecast_duration_hours > 0:
                forecast = await self._generate_forecast(
                    current_conditions, climate_zone, request.season,
                    current_time, request.forecast_duration_hours,
                    request.weather_variability
                )
            
            # Check for extreme weather events
            active_events = []
            if request.include_extreme_weather:
                active_events = await self._check_extreme_weather(
                    request.location, current_time, climate_zone
                )
            
            # Calculate gameplay effects
            gameplay_effects = await self._calculate_gameplay_effects(
                current_conditions, active_events
            )
            
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            return WeatherResponse(
                success=True,
                current_conditions=current_conditions,
                forecast=forecast,
                active_events=active_events,
                gameplay_effects=gameplay_effects,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"Error generating weather: {e}")
            return WeatherResponse(
                success=False,
                message=f"Failed to generate weather: {str(e)}",
                errors=[str(e)]
            )

    async def _determine_climate_zone(self, biome: Optional[BiomeType]) -> ClimateZoneSchema:
        """Determine appropriate climate zone for biome."""
        
        biome_to_climate = {
            BiomeType.ARCTIC: ClimateType.ARCTIC,
            BiomeType.TUNDRA: ClimateType.SUBARCTIC,
            BiomeType.TEMPERATE_FOREST: ClimateType.TEMPERATE,
            BiomeType.TROPICAL_FOREST: ClimateType.TROPICAL,
            BiomeType.GRASSLAND: ClimateType.TEMPERATE,
            BiomeType.DESERT: ClimateType.DESERT,
            BiomeType.SWAMP: ClimateType.SUBTROPICAL,
            BiomeType.MOUNTAINS: ClimateType.TEMPERATE,
            BiomeType.HILLS: ClimateType.TEMPERATE
        }
        
        climate_type = biome_to_climate.get(biome, ClimateType.TEMPERATE)
        return self.climate_zones.get(climate_type, self.climate_zones[ClimateType.TEMPERATE])

    async def _generate_current_conditions(
        self,
        climate_zone: ClimateZoneSchema,
        season: SeasonType,
        current_time: datetime,
        location: Optional[Coordinate]
    ) -> WeatherConditions:
        """Generate current weather conditions."""
        
        # Get seasonal parameters
        seasonal_params = climate_zone.seasonal_params.get(season, {})
        temp_range = seasonal_params.get("temperature_range", (10, 25))
        humidity_range = seasonal_params.get("humidity_range", (0.3, 0.7))
        
        # Select weather type based on probabilities
        weather_probs = climate_zone.weather_probabilities.get(season, {})
        weather_type = self._weighted_choice(weather_probs) or WeatherType.CLEAR
        
        # Generate base conditions
        temperature = random.uniform(*temp_range)
        humidity = random.uniform(*humidity_range)
        
        # Adjust for specific weather type
        temperature, humidity = await self._adjust_for_weather_type(
            weather_type, temperature, humidity
        )
        
        # Calculate feels-like temperature
        feels_like = await self._calculate_feels_like_temperature(
            temperature, humidity, 5.0  # assume 5 m/s wind
        )
        
        # Generate other atmospheric conditions
        pressure = random.uniform(990, 1020)  # hPa
        visibility = await self._calculate_visibility(weather_type)
        
        # Wind conditions
        wind_speed, wind_direction = await self._generate_wind_conditions(weather_type)
        
        # Precipitation
        precip_rate, precip_type = await self._generate_precipitation(weather_type, temperature)
        
        # Cloud cover and UV
        cloud_cover = await self._calculate_cloud_cover(weather_type)
        uv_index = await self._calculate_uv_index(current_time, cloud_cover, season)
        
        return WeatherConditions(
            weather_type=weather_type,
            severity=WeatherSeverity.MODERATE,
            temperature=temperature,
            feels_like=feels_like,
            humidity=humidity,
            pressure=pressure,
            visibility=visibility,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            precipitation_rate=precip_rate,
            precipitation_type=precip_type,
            uv_index=uv_index,
            cloud_cover=cloud_cover
        )

    def _weighted_choice(self, choices: Dict[Any, float]) -> Any:
        """Make a weighted random choice from a dictionary."""
        
        if not choices:
            return None
            
        items = list(choices.keys())
        weights = list(choices.values())
        
        return random.choices(items, weights=weights, k=1)[0]

    async def _adjust_for_weather_type(
        self,
        weather_type: WeatherType,
        temperature: float,
        humidity: float
    ) -> Tuple[float, float]:
        """Adjust temperature and humidity for specific weather type."""
        
        adjustments = {
            WeatherType.RAIN: {"temp_offset": -2, "humidity_mult": 1.2},
            WeatherType.HEAVY_RAIN: {"temp_offset": -4, "humidity_mult": 1.4},
            WeatherType.SNOW: {"temp_offset": -5, "humidity_mult": 1.1},
            WeatherType.BLIZZARD: {"temp_offset": -10, "humidity_mult": 1.3},
            WeatherType.CLEAR: {"temp_offset": 2, "humidity_mult": 0.8},
            WeatherType.FOG: {"temp_offset": -1, "humidity_mult": 1.5},
            WeatherType.THUNDERSTORM: {"temp_offset": -3, "humidity_mult": 1.3}
        }
        
        adj = adjustments.get(weather_type, {"temp_offset": 0, "humidity_mult": 1.0})
        
        new_temp = temperature + adj["temp_offset"]
        new_humidity = min(1.0, humidity * adj["humidity_mult"])
        
        return new_temp, new_humidity

    async def _calculate_feels_like_temperature(
        self,
        temperature: float,
        humidity: float,
        wind_speed: float
    ) -> float:
        """Calculate feels-like temperature with wind chill and heat index."""
        
        if temperature < 10:  # Wind chill for cold temps
            # Simplified wind chill formula
            wind_chill = 13.12 + 0.6215 * temperature - 11.37 * (wind_speed ** 0.16) + 0.3965 * temperature * (wind_speed ** 0.16)
            return min(temperature, wind_chill)
        
        elif temperature > 26 and humidity > 0.4:  # Heat index for hot, humid conditions
            # Simplified heat index formula
            heat_index = temperature + 0.5 * (humidity * 100 - 40) * (temperature - 26) / 15
            return max(temperature, heat_index)
        
        else:
            return temperature

    async def _calculate_visibility(self, weather_type: WeatherType) -> float:
        """Calculate visibility in kilometers."""
        
        visibility_map = {
            WeatherType.CLEAR: random.uniform(15, 25),
            WeatherType.PARTLY_CLOUDY: random.uniform(12, 20),
            WeatherType.CLOUDY: random.uniform(8, 15),
            WeatherType.OVERCAST: random.uniform(5, 12),
            WeatherType.FOG: random.uniform(0.1, 1.0),
            WeatherType.MIST: random.uniform(1, 5),
            WeatherType.DRIZZLE: random.uniform(3, 8),
            WeatherType.RAIN: random.uniform(2, 6),
            WeatherType.HEAVY_RAIN: random.uniform(0.5, 3),
            WeatherType.SNOW: random.uniform(1, 5),
            WeatherType.HEAVY_SNOW: random.uniform(0.2, 2),
            WeatherType.BLIZZARD: random.uniform(0.1, 0.5),
            WeatherType.THUNDERSTORM: random.uniform(1, 4)
        }
        
        return visibility_map.get(weather_type, 10.0)

    async def _generate_wind_conditions(self, weather_type: WeatherType) -> Tuple[float, WindDirection]:
        """Generate wind speed and direction."""
        
        # Wind speeds by weather type (m/s)
        wind_ranges = {
            WeatherType.CLEAR: (0, 5),
            WeatherType.PARTLY_CLOUDY: (2, 8),
            WeatherType.CLOUDY: (3, 10),
            WeatherType.RAIN: (5, 15),
            WeatherType.HEAVY_RAIN: (10, 20),
            WeatherType.THUNDERSTORM: (15, 30),
            WeatherType.BLIZZARD: (20, 40),
            WeatherType.FOG: (0, 2)
        }
        
        wind_range = wind_ranges.get(weather_type, (2, 8))
        wind_speed = random.uniform(*wind_range)
        
        # Wind direction - more variable in storms
        if weather_type in [WeatherType.THUNDERSTORM, WeatherType.BLIZZARD]:
            wind_direction = WindDirection.VARIABLE
        elif wind_speed < 1:
            wind_direction = WindDirection.CALM
        else:
            directions = [d for d in WindDirection if d not in [WindDirection.CALM, WindDirection.VARIABLE]]
            wind_direction = random.choice(directions)
        
        return wind_speed, wind_direction

    async def _generate_precipitation(self, weather_type: WeatherType, temperature: float) -> Tuple[float, Optional[str]]:
        """Generate precipitation rate and type."""
        
        # Precipitation rates (mm/hour)
        precip_rates = {
            WeatherType.DRIZZLE: random.uniform(0.1, 0.5),
            WeatherType.LIGHT_RAIN: random.uniform(0.5, 2.5),
            WeatherType.RAIN: random.uniform(2.5, 10),
            WeatherType.HEAVY_RAIN: random.uniform(10, 50),
            WeatherType.LIGHT_SNOW: random.uniform(0.5, 2),
            WeatherType.SNOW: random.uniform(2, 10),
            WeatherType.HEAVY_SNOW: random.uniform(10, 25),
            WeatherType.BLIZZARD: random.uniform(15, 40),
            WeatherType.THUNDERSTORM: random.uniform(10, 30),
            WeatherType.HAIL: random.uniform(5, 20),
            WeatherType.SLEET: random.uniform(2, 8)
        }
        
        rate = precip_rates.get(weather_type, 0.0)
        
        # Determine precipitation type
        if rate == 0:
            return 0.0, None
        
        if temperature < -2:
            precip_type = "snow"
        elif temperature < 2:
            precip_type = "sleet" if random.random() < 0.3 else "snow"
        elif weather_type == WeatherType.HAIL:
            precip_type = "hail"
        else:
            precip_type = "rain"
        
        return rate, precip_type

    async def _calculate_cloud_cover(self, weather_type: WeatherType) -> float:
        """Calculate cloud cover as a fraction (0-1)."""
        
        cloud_cover_map = {
            WeatherType.CLEAR: random.uniform(0, 0.1),
            WeatherType.PARTLY_CLOUDY: random.uniform(0.25, 0.75),
            WeatherType.CLOUDY: random.uniform(0.75, 0.95),
            WeatherType.OVERCAST: random.uniform(0.95, 1.0),
            WeatherType.FOG: random.uniform(0.8, 1.0),
            WeatherType.RAIN: random.uniform(0.8, 1.0),
            WeatherType.SNOW: random.uniform(0.9, 1.0),
            WeatherType.THUNDERSTORM: random.uniform(0.95, 1.0)
        }
        
        return cloud_cover_map.get(weather_type, 0.5)

    async def _calculate_uv_index(
        self,
        current_time: datetime,
        cloud_cover: float,
        season: SeasonType
    ) -> float:
        """Calculate UV index based on time, clouds, and season."""
        
        # Base UV by season (simplified)
        seasonal_base = {
            SeasonType.WINTER: 2.0,
            SeasonType.SPRING: 6.0,
            SeasonType.SUMMER: 9.0,
            SeasonType.AUTUMN: 4.0
        }
        
        base_uv = seasonal_base.get(season, 5.0)
        
        # Time of day modifier (assuming peak UV at noon)
        hour = current_time.hour
        if 6 <= hour <= 18:  # Daylight hours
            time_modifier = math.sin(math.pi * (hour - 6) / 12)
        else:
            time_modifier = 0
        
        # Cloud cover reduces UV
        cloud_modifier = 1.0 - (cloud_cover * 0.8)
        
        uv_index = base_uv * time_modifier * cloud_modifier
        return max(0, min(11, uv_index))

    async def _generate_forecast(
        self,
        current_conditions: WeatherConditions,
        climate_zone: ClimateZoneSchema,
        season: SeasonType,
        start_time: datetime,
        duration_hours: int,
        variability: float
    ) -> WeatherForecast:
        """Generate weather forecast for the specified duration."""
        
        forecast_periods = []
        current_weather = current_conditions.weather_type
        
        # Generate hourly forecasts
        for hour in range(duration_hours):
            forecast_time = start_time + timedelta(hours=hour)
            
            # Check for weather transitions
            if random.random() < variability * 0.1:  # 10% chance per hour at max variability
                current_weather = await self._transition_weather(current_weather, season)
            
            # Generate conditions for this hour
            period_conditions = await self._generate_forecast_period(
                current_weather, climate_zone, season, forecast_time
            )
            
            forecast_periods.append(period_conditions)
        
        # Calculate confidence (decreases over time)
        confidence = max(0.3, 0.95 - (duration_hours * 0.02))
        
        return WeatherForecast(
            forecast_start=start_time,
            forecast_periods=forecast_periods,
            confidence=confidence
        )

    async def _transition_weather(self, current_weather: WeatherType, season: SeasonType) -> WeatherType:
        """Determine if weather should transition and to what."""
        
        # Find applicable transitions
        applicable_transitions = [
            t for t in self.weather_transitions
            if t.from_weather == current_weather
        ]
        
        if not applicable_transitions:
            return current_weather
        
        # Apply seasonal modifiers and select transition
        for transition in applicable_transitions:
            base_prob = transition.probability
            seasonal_mod = transition.seasonal_modifier.get(season, 1.0)
            final_prob = base_prob * seasonal_mod
            
            if random.random() < final_prob:
                return transition.to_weather
        
        return current_weather

    async def _generate_forecast_period(
        self,
        weather_type: WeatherType,
        climate_zone: ClimateZoneSchema,
        season: SeasonType,
        forecast_time: datetime
    ) -> WeatherConditions:
        """Generate conditions for a single forecast period."""
        
        # Similar to current conditions generation but with some variation
        seasonal_params = climate_zone.seasonal_params.get(season, {})
        temp_range = seasonal_params.get("temperature_range", (10, 25))
        humidity_range = seasonal_params.get("humidity_range", (0.3, 0.7))
        
        # Add some random variation
        temp_var = random.uniform(-2, 2)
        humidity_var = random.uniform(-0.1, 0.1)
        
        temperature = random.uniform(*temp_range) + temp_var
        humidity = max(0.0, min(1.0, random.uniform(*humidity_range) + humidity_var))
        
        # Adjust for weather type
        temperature, humidity = await self._adjust_for_weather_type(
            weather_type, temperature, humidity
        )
        
        # Generate other conditions
        feels_like = await self._calculate_feels_like_temperature(temperature, humidity, 5.0)
        pressure = random.uniform(990, 1020)
        visibility = await self._calculate_visibility(weather_type)
        wind_speed, wind_direction = await self._generate_wind_conditions(weather_type)
        precip_rate, precip_type = await self._generate_precipitation(weather_type, temperature)
        cloud_cover = await self._calculate_cloud_cover(weather_type)
        uv_index = await self._calculate_uv_index(forecast_time, cloud_cover, season)
        
        return WeatherConditions(
            weather_type=weather_type,
            severity=WeatherSeverity.MODERATE,
            temperature=temperature,
            feels_like=feels_like,
            humidity=humidity,
            pressure=pressure,
            visibility=visibility,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            precipitation_rate=precip_rate,
            precipitation_type=precip_type,
            uv_index=uv_index,
            cloud_cover=cloud_cover
        )

    async def _check_extreme_weather(
        self,
        location: Optional[Coordinate],
        current_time: datetime,
        climate_zone: ClimateZoneSchema
    ) -> List[WeatherEventSchema]:
        """Check for and generate extreme weather events."""
        
        events = []
        
        # Base chance for extreme weather
        extreme_chance = climate_zone.extreme_weather_chance
        
        if random.random() < extreme_chance:
            event = await self._generate_weather_event(location, current_time, climate_zone)
            if event:
                events.append(event)
        
        return events

    async def _generate_weather_event(
        self,
        location: Optional[Coordinate],
        start_time: datetime,
        climate_zone: ClimateZoneSchema
    ) -> Optional[WeatherEventSchema]:
        """Generate a random weather event."""
        
        # Event types by climate
        climate_events = {
            ClimateType.TEMPERATE: [WeatherEventType.STORM, WeatherEventType.FLOOD],
            ClimateType.DESERT: [WeatherEventType.DROUGHT, WeatherEventType.HEATWAVE],
            ClimateType.ARCTIC: [WeatherEventType.BLIZZARD, WeatherEventType.COLD_SNAP],
            ClimateType.TROPICAL: [WeatherEventType.HURRICANE, WeatherEventType.STORM]
        }
        
        possible_events = climate_events.get(climate_zone.climate_type, [WeatherEventType.STORM])
        event_type = random.choice(possible_events)
        
        # Generate event details
        center = location or Coordinate(x=0, y=0)
        radius = random.uniform(10, 100)  # km
        duration = random.uniform(2, 48)  # hours
        severity = random.choice(list(WeatherSeverity))
        
        # Create weather conditions for the event
        event_weather = await self._create_event_weather(event_type, severity)
        
        # Create gameplay effects
        gameplay_effects = await self._create_event_gameplay_effects(event_type, severity)
        
        return WeatherEventSchema(
            event_type=event_type,
            severity=severity,
            center=center,
            radius=radius,
            start_time=start_time,
            duration_hours=duration,
            weather_changes=event_weather,
            gameplay_effects=gameplay_effects,
            name=f"{severity.value.title()} {event_type.value.title()}",
            description=await self._generate_event_description(event_type, severity),
            warning_message=await self._generate_warning_message(event_type, severity)
        )

    async def _create_event_weather(self, event_type: WeatherEventType, severity: WeatherSeverity) -> WeatherConditions:
        """Create weather conditions for a specific event."""
        
        base_conditions = WeatherConditions(
            weather_type=WeatherType.CLEAR,
            temperature=20.0,
            humidity=0.5,
            pressure=1013.25,
            visibility=10.0
        )
        
        # Modify based on event type
        if event_type == WeatherEventType.STORM:
            base_conditions.weather_type = WeatherType.THUNDERSTORM
            base_conditions.wind_speed = 15 + (severity.value == "severe") * 10
            base_conditions.precipitation_rate = 10 + (severity.value == "severe") * 20
            base_conditions.visibility = 2.0
            
        elif event_type == WeatherEventType.BLIZZARD:
            base_conditions.weather_type = WeatherType.BLIZZARD
            base_conditions.temperature = -10 - (severity.value == "severe") * 15
            base_conditions.wind_speed = 25 + (severity.value == "severe") * 15
            base_conditions.visibility = 0.5
            base_conditions.precipitation_rate = 15
            base_conditions.precipitation_type = "snow"
            
        elif event_type == WeatherEventType.HEATWAVE:
            base_conditions.weather_type = WeatherType.CLEAR
            base_conditions.temperature = 35 + (severity.value == "severe") * 10
            base_conditions.humidity = 0.2
            
        return base_conditions

    async def _create_event_gameplay_effects(
        self,
        event_type: WeatherEventType,
        severity: WeatherSeverity
    ) -> GameplayWeatherEffects:
        """Create gameplay effects for weather events."""
        
        severity_multiplier = {
            WeatherSeverity.LIGHT: 0.5,
            WeatherSeverity.MODERATE: 1.0,
            WeatherSeverity.HEAVY: 1.5,
            WeatherSeverity.SEVERE: 2.0,
            WeatherSeverity.EXTREME: 3.0
        }.get(severity, 1.0)
        
        if event_type == WeatherEventType.BLIZZARD:
            return GameplayWeatherEffects(
                movement_speed_modifier=max(0.1, 0.5 / severity_multiplier),
                terrain_difficulty_modifier=1.5 * severity_multiplier,
                vision_range_modifier=max(0.1, 0.3 / severity_multiplier),
                exposure_damage=3.0 * severity_multiplier,
                rest_quality_modifier=max(0.2, 0.5 / severity_multiplier)
            )
        
        elif event_type == WeatherEventType.STORM:
            return GameplayWeatherEffects(
                movement_speed_modifier=max(0.3, 0.7 / severity_multiplier),
                vision_range_modifier=max(0.2, 0.5 / severity_multiplier),
                ranged_accuracy_modifier=max(0.2, 0.6 / severity_multiplier),
                exposure_damage=2.0 * severity_multiplier,
                certain_spell_modifiers={"lightning": 2.0 * severity_multiplier}
            )
        
        else:
            return GameplayWeatherEffects()

    async def _generate_event_description(self, event_type: WeatherEventType, severity: WeatherSeverity) -> str:
        """Generate description for weather event."""
        
        descriptions = {
            WeatherEventType.STORM: f"A {severity.value} thunderstorm brings heavy rain, strong winds, and frequent lightning strikes.",
            WeatherEventType.BLIZZARD: f"A {severity.value} blizzard creates whiteout conditions with heavy snow and fierce winds.",
            WeatherEventType.HEATWAVE: f"A {severity.value} heatwave brings dangerously high temperatures and oppressive conditions.",
            WeatherEventType.DROUGHT: f"A {severity.value} drought has left the land parched and water sources depleted.",
            WeatherEventType.FLOOD: f"Heavy rains have caused {severity.value} flooding in low-lying areas."
        }
        
        return descriptions.get(event_type, f"A {severity.value} weather event affects the area.")

    async def _generate_warning_message(self, event_type: WeatherEventType, severity: WeatherSeverity) -> str:
        """Generate warning message for weather event."""
        
        if severity in [WeatherSeverity.SEVERE, WeatherSeverity.EXTREME]:
            return f"DANGER: {severity.value.upper()} {event_type.value.upper()} - Seek shelter immediately!"
        elif severity == WeatherSeverity.HEAVY:
            return f"Warning: Heavy {event_type.value} conditions. Travel not recommended."
        else:
            return f"Advisory: {event_type.value.title()} conditions expected. Exercise caution."

    async def _calculate_gameplay_effects(
        self,
        conditions: WeatherConditions,
        events: List[WeatherEventSchema]
    ) -> GameplayWeatherEffects:
        """Calculate combined gameplay effects from weather and events."""
        
        # Start with base weather effects
        base_effects = self.gameplay_effects.get(conditions.weather_type, GameplayWeatherEffects())
        
        # Apply event effects
        combined_effects = base_effects
        
        for event in events:
            if event.active:
                # Combine effects (multiplicative for most, additive for damage)
                event_effects = event.gameplay_effects
                
                combined_effects.movement_speed_modifier *= event_effects.movement_speed_modifier
                combined_effects.terrain_difficulty_modifier *= event_effects.terrain_difficulty_modifier
                combined_effects.vision_range_modifier *= event_effects.vision_range_modifier
                combined_effects.ranged_accuracy_modifier *= event_effects.ranged_accuracy_modifier
                combined_effects.exposure_damage += event_effects.exposure_damage
                combined_effects.rest_quality_modifier *= event_effects.rest_quality_modifier
        
        return combined_effects

    async def create_weather_event(
        self,
        request: WeatherEventRequest,
        db_session: Optional[Session] = None
    ) -> WeatherResponse:
        """Create a custom weather event."""
        
        try:
            start_time = request.start_time or datetime.utcnow()
            
            # Create event weather conditions
            event_weather = await self._create_event_weather(request.event_type, request.severity)
            
            # Create or use custom gameplay effects
            gameplay_effects = request.custom_effects or await self._create_event_gameplay_effects(
                request.event_type, request.severity
            )
            
            # Create the weather event
            event = WeatherEventSchema(
                event_type=request.event_type,
                severity=request.severity,
                center=request.center,
                radius=request.radius,
                start_time=start_time,
                duration_hours=request.duration_hours,
                end_time=start_time + timedelta(hours=request.duration_hours),
                weather_changes=event_weather,
                gameplay_effects=gameplay_effects,
                name=f"{request.severity.value.title()} {request.event_type.value.title()}",
                description=request.description_override or await self._generate_event_description(
                    request.event_type, request.severity
                )
            )
            
            return WeatherResponse(
                success=True,
                message="Weather event created successfully",
                active_events=[event],
                gameplay_effects=gameplay_effects
            )
            
        except Exception as e:
            logger.error(f"Error creating weather event: {e}")
            return WeatherResponse(
                success=False,
                message=f"Failed to create weather event: {str(e)}",
                errors=[str(e)]
            )

    async def get_astronomical_data(self, date: datetime, location: Optional[Coordinate] = None) -> AstronomicalData:
        """Get astronomical data for date and location."""
        
        # Simplified astronomical calculations
        day_of_year = date.timetuple().tm_yday
        
        # Determine season based on day of year (Northern hemisphere)
        if 80 <= day_of_year <= 172:  # Mar 21 - Jun 21
            season = SeasonType.SPRING
            days_into_season = day_of_year - 80
        elif 173 <= day_of_year <= 266:  # Jun 22 - Sep 22  
            season = SeasonType.SUMMER
            days_into_season = day_of_year - 173
        elif 267 <= day_of_year <= 354:  # Sep 23 - Dec 21
            season = SeasonType.AUTUMN
            days_into_season = day_of_year - 267
        else:  # Dec 22 - Mar 20
            season = SeasonType.WINTER
            days_into_season = day_of_year if day_of_year <= 79 else day_of_year - 354
        
        # Simplified daylight calculation (varies by latitude)
        latitude = location.y if location else 45.0  # Default to 45°N
        daylight_variation = 4 * math.sin(2 * math.pi * day_of_year / 365.25)
        base_daylight = 12 + (latitude / 90) * daylight_variation
        daylight_hours = max(4, min(20, base_daylight))
        
        # Calculate sunrise/sunset
        sunrise_hour = 12 - daylight_hours / 2
        sunset_hour = 12 + daylight_hours / 2
        
        sunrise = datetime.combine(date.date(), datetime.min.time().replace(
            hour=int(sunrise_hour), 
            minute=int((sunrise_hour % 1) * 60)
        ))
        sunset = datetime.combine(date.date(), datetime.min.time().replace(
            hour=int(sunset_hour), 
            minute=int((sunset_hour % 1) * 60)
        ))
        
        # Moon phase (simplified)
        moon_cycle_days = 29.53
        days_since_new_moon = (day_of_year % moon_cycle_days) / moon_cycle_days
        
        # Solar elevation at noon (simplified)
        solar_elevation = 90 - abs(latitude) + 23.5 * math.sin(2 * math.pi * day_of_year / 365.25)
        
        # UV intensity based on solar elevation
        uv_intensity = max(0, min(11, solar_elevation / 10))
        
        return AstronomicalData(
            date=date,
            sunrise=sunrise,
            sunset=sunset,
            daylight_hours=daylight_hours,
            moon_phase=days_since_new_moon,
            season=season,
            days_into_season=days_into_season,
            solar_elevation_noon=solar_elevation,
            uv_intensity=uv_intensity
        )