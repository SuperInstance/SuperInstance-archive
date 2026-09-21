"""
Weather Impact Modeling Module

This module provides comprehensive weather impact simulation for various systems and operations.
Includes meteorological modeling, impact analysis, and predictive capabilities for weather-related
disruptions and optimization opportunities.

Key Features:
- Real-time weather simulation
- Impact assessment on operations, infrastructure, and resources
- Seasonal and climate pattern modeling
- Weather-driven scenario planning
- Multi-scale modeling (local, regional, global)
- Extreme weather event simulation
- Agricultural and environmental impact analysis
- Energy consumption modeling
- Transportation disruption analysis
- Supply chain weather risk assessment
"""

import asyncio
import logging
import random
import time
import json
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from enum import Enum
from collections import defaultdict, deque
import math


class WeatherType(Enum):
    """Weather condition types"""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    FOG = "fog"
    STORM = "storm"
    HURRICANE = "hurricane"
    TORNADO = "tornado"
    HAIL = "hail"
    ICE = "ice"
    BLIZZARD = "blizzard"
    DROUGHT = "drought"
    HEAT_WAVE = "heat_wave"
    COLD_SNAP = "cold_snap"


class ImpactSeverity(Enum):
    """Impact severity levels"""
    MINIMAL = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3
    SEVERE = 4
    CRITICAL = 5


class SeasonType(Enum):
    """Season types for modeling"""
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"


@dataclass
class WeatherCondition:
    """Represents current weather conditions"""
    weather_type: WeatherType
    temperature: float  # Celsius
    humidity: float  # Percentage
    wind_speed: float  # km/h
    precipitation: float  # mm/h
    pressure: float  # hPa
    visibility: float  # km
    uv_index: float
    timestamp: datetime = field(default_factory=datetime.now)
    location: str = "default"
    forecast_confidence: float = 1.0


@dataclass
class WeatherForecast:
    """Weather forecast data"""
    conditions: List[WeatherCondition]
    forecast_horizon: int  # hours
    accuracy_score: float
    last_updated: datetime = field(default_factory=datetime.now)
    source: str = "simulation"


@dataclass
class ImpactAssessment:
    """Impact assessment results"""
    sector: str
    impact_type: str
    severity: ImpactSeverity
    probability: float
    estimated_loss: float
    duration_hours: int
    mitigation_strategies: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


class WeatherPattern(ABC):
    """Abstract base class for weather patterns"""
    
    @abstractmethod
    def generate_conditions(self, hours: int) -> List[WeatherCondition]:
        """Generate weather conditions for specified hours"""
        pass
    
    @abstractmethod
    def get_transition_probability(self, current: WeatherType, next_type: WeatherType) -> float:
        """Get probability of transitioning between weather types"""
        pass


class SeasonalPattern(WeatherPattern):
    """Seasonal weather pattern modeling"""
    
    def __init__(self, season: SeasonType, location: str = "default"):
        self.season = season
        self.location = location
        self.base_temperature = self._get_base_temperature()
        self.weather_probabilities = self._get_weather_probabilities()
    
    def _get_base_temperature(self) -> float:
        """Get base temperature for season"""
        temps = {
            SeasonType.SPRING: 15,
            SeasonType.SUMMER: 25,
            SeasonType.FALL: 10,
            SeasonType.WINTER: -5
        }
        return temps[self.season]
    
    def _get_weather_probabilities(self) -> Dict[WeatherType, float]:
        """Get weather type probabilities for season"""
        if self.season == SeasonType.SUMMER:
            return {
                WeatherType.CLEAR: 0.6,
                WeatherType.CLOUDY: 0.25,
                WeatherType.RAIN: 0.1,
                WeatherType.STORM: 0.05
            }
        elif self.season == SeasonType.WINTER:
            return {
                WeatherType.CLOUDY: 0.4,
                WeatherType.SNOW: 0.3,
                WeatherType.CLEAR: 0.2,
                WeatherType.ICE: 0.1
            }
        elif self.season == SeasonType.SPRING:
            return {
                WeatherType.CLOUDY: 0.35,
                WeatherType.RAIN: 0.3,
                WeatherType.CLEAR: 0.25,
                WeatherType.STORM: 0.1
            }
        else:  # FALL
            return {
                WeatherType.CLOUDY: 0.45,
                WeatherType.CLEAR: 0.3,
                WeatherType.RAIN: 0.2,
                WeatherType.FOG: 0.05
            }
    
    def generate_conditions(self, hours: int) -> List[WeatherCondition]:
        """Generate seasonal weather conditions"""
        conditions = []
        current_weather = self._select_weather_type()
        
        for hour in range(hours):
            temp_variation = random.gauss(0, 3)
            temp = self.base_temperature + temp_variation
            
            condition = WeatherCondition(
                weather_type=current_weather,
                temperature=temp,
                humidity=self._generate_humidity(current_weather),
                wind_speed=self._generate_wind_speed(current_weather),
                precipitation=self._generate_precipitation(current_weather),
                pressure=self._generate_pressure(current_weather),
                visibility=self._generate_visibility(current_weather),
                uv_index=self._generate_uv_index(current_weather, temp),
                timestamp=datetime.now() + timedelta(hours=hour),
                location=self.location
            )
            conditions.append(condition)
            
            # Possibly change weather type
            if random.random() < 0.1:  # 10% chance of change per hour
                current_weather = self._select_weather_type()
        
        return conditions
    
    def _select_weather_type(self) -> WeatherType:
        """Select weather type based on probabilities"""
        weather_types = list(self.weather_probabilities.keys())
        probabilities = list(self.weather_probabilities.values())
        return np.random.choice(weather_types, p=probabilities)
    
    def _generate_humidity(self, weather_type: WeatherType) -> float:
        """Generate humidity based on weather type"""
        base_humidity = {
            WeatherType.CLEAR: 45,
            WeatherType.CLOUDY: 65,
            WeatherType.RAIN: 85,
            WeatherType.SNOW: 75,
            WeatherType.FOG: 95,
            WeatherType.STORM: 80
        }
        base = base_humidity.get(weather_type, 60)
        return max(0, min(100, base + random.gauss(0, 10)))
    
    def _generate_wind_speed(self, weather_type: WeatherType) -> float:
        """Generate wind speed based on weather type"""
        base_wind = {
            WeatherType.CLEAR: 5,
            WeatherType.CLOUDY: 8,
            WeatherType.RAIN: 15,
            WeatherType.SNOW: 12,
            WeatherType.FOG: 3,
            WeatherType.STORM: 45,
            WeatherType.HURRICANE: 120,
            WeatherType.TORNADO: 200
        }
        base = base_wind.get(weather_type, 10)
        return max(0, base + random.gauss(0, base * 0.3))
    
    def _generate_precipitation(self, weather_type: WeatherType) -> float:
        """Generate precipitation rate"""
        if weather_type in [WeatherType.RAIN, WeatherType.STORM]:
            return max(0, random.exponential(2))
        elif weather_type == WeatherType.SNOW:
            return max(0, random.exponential(1))
        return 0
    
    def _generate_pressure(self, weather_type: WeatherType) -> float:
        """Generate atmospheric pressure"""
        base_pressure = 1013.25  # Standard atmosphere
        if weather_type == WeatherType.STORM:
            base_pressure -= 20
        elif weather_type == WeatherType.CLEAR:
            base_pressure += 5
        return base_pressure + random.gauss(0, 5)
    
    def _generate_visibility(self, weather_type: WeatherType) -> float:
        """Generate visibility distance"""
        if weather_type == WeatherType.FOG:
            return random.uniform(0.1, 1)
        elif weather_type in [WeatherType.RAIN, WeatherType.SNOW]:
            return random.uniform(2, 8)
        elif weather_type == WeatherType.STORM:
            return random.uniform(1, 5)
        return random.uniform(10, 50)  # Clear conditions
    
    def _generate_uv_index(self, weather_type: WeatherType, temperature: float) -> float:
        """Generate UV index"""
        if weather_type == WeatherType.CLEAR and temperature > 20:
            return random.uniform(6, 11)
        elif weather_type == WeatherType.CLOUDY:
            return random.uniform(2, 6)
        return random.uniform(0, 3)
    
    def get_transition_probability(self, current: WeatherType, next_type: WeatherType) -> float:
        """Get weather transition probability"""
        # Simplified transition matrix
        if current == next_type:
            return 0.7  # Tendency to persist
        elif (current == WeatherType.CLEAR and next_type == WeatherType.CLOUDY) or \
             (current == WeatherType.CLOUDY and next_type == WeatherType.RAIN):
            return 0.2
        else:
            return 0.1


class ExtremeWeatherPattern(WeatherPattern):
    """Extreme weather event modeling"""
    
    def __init__(self, extreme_type: WeatherType, intensity: float = 1.0):
        self.extreme_type = extreme_type
        self.intensity = intensity
        self.duration_hours = self._get_typical_duration()
    
    def _get_typical_duration(self) -> int:
        """Get typical duration for extreme weather type"""
        durations = {
            WeatherType.STORM: 3,
            WeatherType.HURRICANE: 12,
            WeatherType.TORNADO: 1,
            WeatherType.BLIZZARD: 18,
            WeatherType.HEAT_WAVE: 120,
            WeatherType.DROUGHT: 720,  # 30 days
            WeatherType.COLD_SNAP: 72
        }
        return durations.get(self.extreme_type, 6)
    
    def generate_conditions(self, hours: int) -> List[WeatherCondition]:
        """Generate extreme weather conditions"""
        conditions = []
        peak_hour = hours // 2
        
        for hour in range(min(hours, self.duration_hours)):
            # Intensity curve (builds up, peaks, then declines)
            if hour <= peak_hour:
                current_intensity = (hour / peak_hour) * self.intensity
            else:
                remaining = self.duration_hours - peak_hour
                current_intensity = ((remaining - (hour - peak_hour)) / remaining) * self.intensity
            
            condition = self._generate_extreme_condition(current_intensity, hour)
            conditions.append(condition)
        
        return conditions
    
    def _generate_extreme_condition(self, intensity: float, hour: int) -> WeatherCondition:
        """Generate specific extreme weather condition"""
        timestamp = datetime.now() + timedelta(hours=hour)
        
        if self.extreme_type == WeatherType.HURRICANE:
            return WeatherCondition(
                weather_type=WeatherType.HURRICANE,
                temperature=22 + random.gauss(0, 2),
                humidity=85 + intensity * 10,
                wind_speed=80 + intensity * 100,
                precipitation=20 + intensity * 30,
                pressure=950 + intensity * (-50),
                visibility=1 + (1 - intensity) * 4,
                uv_index=0,
                timestamp=timestamp
            )
        elif self.extreme_type == WeatherType.BLIZZARD:
            return WeatherCondition(
                weather_type=WeatherType.BLIZZARD,
                temperature=-15 - intensity * 10,
                humidity=80 + intensity * 15,
                wind_speed=40 + intensity * 60,
                precipitation=15 + intensity * 25,
                pressure=1000 - intensity * 15,
                visibility=0.2 + (1 - intensity) * 0.8,
                uv_index=0,
                timestamp=timestamp
            )
        elif self.extreme_type == WeatherType.HEAT_WAVE:
            return WeatherCondition(
                weather_type=WeatherType.HEAT_WAVE,
                temperature=35 + intensity * 15,
                humidity=30 - intensity * 15,
                wind_speed=5 + intensity * 10,
                precipitation=0,
                pressure=1020 + intensity * 10,
                visibility=15 - intensity * 10,  # Heat haze
                uv_index=9 + intensity * 2,
                timestamp=timestamp
            )
        else:
            # Default extreme condition
            return WeatherCondition(
                weather_type=self.extreme_type,
                temperature=20,
                humidity=70,
                wind_speed=30 + intensity * 50,
                precipitation=10 + intensity * 20,
                pressure=1000,
                visibility=5,
                uv_index=2,
                timestamp=timestamp
            )
    
    def get_transition_probability(self, current: WeatherType, next_type: WeatherType) -> float:
        """Get extreme weather transition probability"""
        if current == self.extreme_type and next_type == self.extreme_type:
            return 0.9  # Extreme weather tends to persist
        elif current == self.extreme_type:
            return 0.05  # Low chance of immediate change
        elif next_type == self.extreme_type:
            return 0.01  # Rare transition to extreme
        return 0.1


class ImpactAnalyzer:
    """Analyzes weather impact on various sectors"""
    
    def __init__(self):
        self.sector_analyzers = {
            'transportation': self._analyze_transportation_impact,
            'agriculture': self._analyze_agriculture_impact,
            'energy': self._analyze_energy_impact,
            'construction': self._analyze_construction_impact,
            'retail': self._analyze_retail_impact,
            'supply_chain': self._analyze_supply_chain_impact,
            'aviation': self._analyze_aviation_impact,
            'marine': self._analyze_marine_impact,
            'tourism': self._analyze_tourism_impact,
            'healthcare': self._analyze_healthcare_impact
        }
    
    def analyze_impact(self, condition: WeatherCondition, sector: str) -> ImpactAssessment:
        """Analyze weather impact on specific sector"""
        if sector not in self.sector_analyzers:
            raise ValueError(f"Unknown sector: {sector}")
        
        return self.sector_analyzers[sector](condition)
    
    def analyze_all_sectors(self, condition: WeatherCondition) -> List[ImpactAssessment]:
        """Analyze weather impact across all sectors"""
        return [self.analyze_impact(condition, sector) for sector in self.sector_analyzers.keys()]
    
    def _analyze_transportation_impact(self, condition: WeatherCondition) -> ImpactAssessment:
        """Analyze transportation impact"""
        severity = ImpactSeverity.MINIMAL
        probability = 0.1
        estimated_loss = 0
        duration = 1
        strategies = []
        
        if condition.weather_type in [WeatherType.SNOW, WeatherType.ICE, WeatherType.BLIZZARD]:
            severity = ImpactSeverity.HIGH
            probability = 0.9
            estimated_loss = 50000 * (condition.wind_speed / 10)
            duration = 6
            strategies = ["Deploy snow plows", "Apply road salt", "Issue travel advisories"]
        elif condition.weather_type in [WeatherType.FOG, WeatherType.RAIN]:
            if condition.visibility < 1:
                severity = ImpactSeverity.SEVERE
                probability = 0.95
                estimated_loss = 75000
                duration = 4
                strategies = ["Reduce speed limits", "Increase following distance", "Use fog lights"]
            elif condition.precipitation > 10:
                severity = ImpactSeverity.MODERATE
                probability = 0.7
                estimated_loss = 20000
                duration = 3
                strategies = ["Monitor road conditions", "Clear drainage", "Traffic management"]
        elif condition.weather_type in [WeatherType.STORM, WeatherType.HURRICANE]:
            severity = ImpactSeverity.CRITICAL
            probability = 0.99
            estimated_loss = 200000 + condition.wind_speed * 1000
            duration = 12
            strategies = ["Close roads", "Emergency services standby", "Evacuate if necessary"]
        
        return ImpactAssessment(
            sector="transportation",
            impact_type="traffic_disruption",
            severity=severity,
            probability=probability,
            estimated_loss=estimated_loss,
            duration_hours=duration,
            mitigation_strategies=strategies
        )
    
    def _analyze_agriculture_impact(self, condition: WeatherCondition) -> ImpactAssessment:
        """Analyze agriculture impact"""
        severity = ImpactSeverity.MINIMAL
        probability = 0.2
        estimated_loss = 0
        duration = 1
        strategies = []
        
        if condition.weather_type == WeatherType.DROUGHT:
            severity = ImpactSeverity.SEVERE
            probability = 0.95
            estimated_loss = 100000
            duration = 168  # 7 days
            strategies = ["Implement irrigation", "Drought-resistant crops", "Water conservation"]
        elif condition.weather_type == WeatherType.HAIL:
            severity = ImpactSeverity.HIGH
            probability = 0.8
            estimated_loss = 75000
            duration = 24
            strategies = ["Crop insurance claims", "Hail nets", "Replanting damaged crops"]
        elif condition.weather_type == WeatherType.HEAT_WAVE:
            if condition.temperature > 40:
                severity = ImpactSeverity.HIGH
                probability = 0.85
                estimated_loss = 60000
                duration = 48
                strategies = ["Shade structures", "Increased watering", "Heat-resistant varieties"]
        elif condition.weather_type in [WeatherType.RAIN, WeatherType.STORM]:
            if condition.precipitation > 15:
                severity = ImpactSeverity.MODERATE
                probability = 0.6
                estimated_loss = 30000
                duration = 12
                strategies = ["Improve drainage", "Harvest early", "Fungicide application"]
        
        return ImpactAssessment(
            sector="agriculture",
            impact_type="crop_damage",
            severity=severity,
            probability=probability,
            estimated_loss=estimated_loss,
            duration_hours=duration,
            mitigation_strategies=strategies
        )
    
    def _analyze_energy_impact(self, condition: WeatherCondition) -> ImpactAssessment:
        """Analyze energy sector impact"""
        severity = ImpactSeverity.MINIMAL
        probability = 0.1
        estimated_loss = 0
        duration = 1
        strategies = []
        
        if condition.weather_type == WeatherType.HEAT_WAVE:
            severity = ImpactSeverity.HIGH
            probability = 0.9
            estimated_loss = 150000  # Increased cooling demand
            duration = 24
            strategies = ["Load balancing", "Demand response", "Peak shaving"]
        elif condition.weather_type == WeatherType.COLD_SNAP:
            severity = ImpactSeverity.HIGH
            probability = 0.85
            estimated_loss = 120000  # Increased heating demand
            duration = 18
            strategies = ["Gas supply monitoring", "Grid stability", "Energy efficiency"]
        elif condition.weather_type in [WeatherType.STORM, WeatherType.HURRICANE]:
            severity = ImpactSeverity.CRITICAL
            probability = 0.95
            estimated_loss = 300000 + condition.wind_speed * 2000
            duration = 24
            strategies = ["Power line inspection", "Grid hardening", "Backup generation"]
        elif condition.wind_speed > 80:
            severity = ImpactSeverity.SEVERE
            probability = 0.8
            estimated_loss = 200000
            duration = 12
            strategies = ["Wind turbine shutdown", "Line monitoring", "Emergency repairs"]
        
        return ImpactAssessment(
            sector="energy",
            impact_type="supply_disruption",
            severity=severity,
            probability=probability,
            estimated_loss=estimated_loss,
            duration_hours=duration,
            mitigation_strategies=strategies
        )
    
    def _analyze_construction_impact(self, condition: WeatherCondition) -> ImpactAssessment:
        """Analyze construction impact"""
        severity = ImpactSeverity.MINIMAL
        probability = 0.15
        estimated_loss = 0
        duration = 4
        strategies = []
        
        if condition.temperature < 0:
            severity = ImpactSeverity.MODERATE
            probability = 0.7
            estimated_loss = 25000
            duration = 8
            strategies = ["Heated enclosures", "Concrete additives", "Schedule adjustment"]
        elif condition.weather_type in [WeatherType.RAIN, WeatherType.STORM]:
            if condition.precipitation > 5:
                severity = ImpactSeverity.MODERATE
                probability = 0.8
                estimated_loss = 15000
                duration = 6
                strategies = ["Weatherproofing", "Equipment protection", "Drainage systems"]
        elif condition.wind_speed > 50:
            severity = ImpactSeverity.HIGH
            probability = 0.9
            estimated_loss = 40000
            duration = 8
            strategies = ["Crane operations halt", "Safety protocols", "Secure materials"]
        
        return ImpactAssessment(
            sector="construction",
            impact_type="work_delays",
            severity=severity,
            probability=probability,
            estimated_loss=estimated_loss,
            duration_hours=duration,
            mitigation_strategies=strategies
        )
    
    def _analyze_retail_impact(self, condition: WeatherCondition) -> ImpactAssessment:
        """Analyze retail impact"""
        severity = ImpactSeverity.MINIMAL
        probability = 0.2
        estimated_loss = 0
        duration = 4
        strategies = []
        
        if condition.weather_type in [WeatherType.STORM, WeatherType.BLIZZARD, WeatherType.HURRICANE]:
            severity = ImpactSeverity.MODERATE
            probability = 0.75
            estimated_loss = 30000  # Lost sales
            duration = 12
            strategies = ["Online sales push", "Delivery alternatives", "Emergency supplies"]
        elif condition.weather_type == WeatherType.HEAT_WAVE:
            severity = ImpactSeverity.LOW
            probability = 0.5
            estimated_loss = -10000  # Increased cooling products sales
            duration = 24
            strategies = ["Stock cooling products", "Extended hours", "Promotions"]
        
        return ImpactAssessment(
            sector="retail",
            impact_type="customer_traffic",
            severity=severity,
            probability=probability,
            estimated_loss=estimated_loss,
            duration_hours=duration,
            mitigation_strategies=strategies
        )
    
    def _analyze_supply_chain_impact(self, condition: WeatherCondition) -> ImpactAssessment:
        """Analyze supply chain impact"""
        severity = ImpactSeverity.MINIMAL
        probability = 0.25
        estimated_loss = 0
        duration = 8
        strategies = []
        
        if condition.weather_type in [WeatherType.HURRICANE, WeatherType.BLIZZARD]:
            severity = ImpactSeverity.SEVERE
            probability = 0.9
            estimated_loss = 150000
            duration = 48
            strategies = ["Route diversification", "Inventory buffers", "Supplier alternatives"]
        elif condition.weather_type in [WeatherType.STORM, WeatherType.ICE]:
            severity = ImpactSeverity.MODERATE
            probability = 0.7
            estimated_loss = 50000
            duration = 24
            strategies = ["Weather tracking", "Flexible scheduling", "Safety protocols"]
        
        return ImpactAssessment(
            sector="supply_chain",
            impact_type="logistics_disruption",
            severity=severity,
            probability=probability,
            estimated_loss=estimated_loss,
            duration_hours=duration,
            mitigation_strategies=strategies
        )
    
    def _analyze_aviation_impact(self, condition: WeatherCondition) -> ImpactAssessment:
        """Analyze aviation impact"""
        severity = ImpactSeverity.MINIMAL
        probability = 0.1
        estimated_loss = 0
        duration = 2
        strategies = []
        
        if condition.visibility < 1 or condition.weather_type == WeatherType.FOG:
            severity = ImpactSeverity.HIGH
            probability = 0.95
            estimated_loss = 100000
            duration = 6
            strategies = ["ILS approaches", "Ground stops", "Divert flights"]
        elif condition.wind_speed > 60:
            severity = ImpactSeverity.SEVERE
            probability = 0.9
            estimated_loss = 200000
            duration = 8
            strategies = ["Flight cancellations", "Airport closure", "Safety inspections"]
        elif condition.weather_type in [WeatherType.STORM, WeatherType.HURRICANE]:
            severity = ImpactSeverity.CRITICAL
            probability = 0.99
            estimated_loss = 500000
            duration = 24
            strategies = ["Airport evacuation", "Aircraft hangar", "Passenger accommodation"]
        
        return ImpactAssessment(
            sector="aviation",
            impact_type="flight_disruption",
            severity=severity,
            probability=probability,
            estimated_loss=estimated_loss,
            duration_hours=duration,
            mitigation_strategies=strategies
        )
    
    def _analyze_marine_impact(self, condition: WeatherCondition) -> ImpactAssessment:
        """Analyze marine sector impact"""
        severity = ImpactSeverity.MINIMAL
        probability = 0.2
        estimated_loss = 0
        duration = 6
        strategies = []
        
        if condition.wind_speed > 40:
            severity = ImpactSeverity.MODERATE
            probability = 0.8
            estimated_loss = 75000
            duration = 12
            strategies = ["Port closure", "Vessel rerouting", "Harbor safety"]
        elif condition.weather_type in [WeatherType.HURRICANE, WeatherType.STORM]:
            severity = ImpactSeverity.CRITICAL
            probability = 0.95
            estimated_loss = 300000
            duration = 24
            strategies = ["Emergency anchorage", "Port evacuation", "Vessel tracking"]
        
        return ImpactAssessment(
            sector="marine",
            impact_type="shipping_disruption",
            severity=severity,
            probability=probability,
            estimated_loss=estimated_loss,
            duration_hours=duration,
            mitigation_strategies=strategies
        )
    
    def _analyze_tourism_impact(self, condition: WeatherCondition) -> ImpactAssessment:
        """Analyze tourism impact"""
        severity = ImpactSeverity.MINIMAL
        probability = 0.3
        estimated_loss = 0
        duration = 24
        strategies = []
        
        if condition.weather_type in [WeatherType.STORM, WeatherType.HURRICANE]:
            severity = ImpactSeverity.HIGH
            probability = 0.9
            estimated_loss = 100000
            duration = 48
            strategies = ["Indoor activities", "Refund policies", "Safety measures"]
        elif condition.weather_type == WeatherType.HEAT_WAVE and condition.temperature > 45:
            severity = ImpactSeverity.MODERATE
            probability = 0.6
            estimated_loss = 25000
            duration = 24
            strategies = ["Cooling centers", "Activity rescheduling", "Health warnings"]
        
        return ImpactAssessment(
            sector="tourism",
            impact_type="visitor_experience",
            severity=severity,
            probability=probability,
            estimated_loss=estimated_loss,
            duration_hours=duration,
            mitigation_strategies=strategies
        )
    
    def _analyze_healthcare_impact(self, condition: WeatherCondition) -> ImpactAssessment:
        """Analyze healthcare impact"""
        severity = ImpactSeverity.MINIMAL
        probability = 0.15
        estimated_loss = 0
        duration = 12
        strategies = []
        
        if condition.weather_type == WeatherType.HEAT_WAVE:
            severity = ImpactSeverity.HIGH
            probability = 0.85
            estimated_loss = 50000  # Increased emergency visits
            duration = 48
            strategies = ["Heat illness protocols", "Cooling stations", "Vulnerable population checks"]
        elif condition.weather_type == WeatherType.COLD_SNAP:
            severity = ImpactSeverity.MODERATE
            probability = 0.7
            estimated_loss = 30000
            duration = 36
            strategies = ["Hypothermia treatment", "Shelter services", "Elder care checks"]
        elif condition.weather_type in [WeatherType.STORM, WeatherType.HURRICANE]:
            severity = ImpactSeverity.SEVERE
            probability = 0.9
            estimated_loss = 100000
            duration = 24
            strategies = ["Emergency preparedness", "Evacuation plans", "Medical supply stockpiling"]
        
        return ImpactAssessment(
            sector="healthcare",
            impact_type="service_demand",
            severity=severity,
            probability=probability,
            estimated_loss=estimated_loss,
            duration_hours=duration,
            mitigation_strategies=strategies
        )


class ClimateModel:
    """Climate and long-term weather modeling"""
    
    def __init__(self, location: str = "default"):
        self.location = location
        self.historical_data = []
        self.climate_trends = {}
        self.seasonal_patterns = {
            SeasonType.SPRING: SeasonalPattern(SeasonType.SPRING, location),
            SeasonType.SUMMER: SeasonalPattern(SeasonType.SUMMER, location),
            SeasonType.FALL: SeasonalPattern(SeasonType.FALL, location),
            SeasonType.WINTER: SeasonalPattern(SeasonType.WINTER, location)
        }
    
    def analyze_climate_trends(self, years: int = 10) -> Dict[str, Any]:
        """Analyze climate trends over specified years"""
        trends = {
            'temperature_trend': random.uniform(-0.5, 2.0),  # Degrees per decade
            'precipitation_trend': random.uniform(-10, 15),  # Percent change per decade
            'extreme_weather_frequency': random.uniform(0.8, 1.5),  # Frequency multiplier
            'sea_level_rise': random.uniform(1, 5),  # mm per year
            'growing_season_change': random.uniform(-5, 15),  # Days per decade
            'frost_date_shift': random.uniform(-3, 7)  # Days per decade
        }
        self.climate_trends = trends
        return trends
    
    def project_future_conditions(self, years_ahead: int) -> Dict[str, Any]:
        """Project future climate conditions"""
        if not self.climate_trends:
            self.analyze_climate_trends()
        
        projections = {}
        for trend, rate in self.climate_trends.items():
            change = rate * (years_ahead / 10)  # Scale to decades
            projections[f"{trend}_change"] = change
            projections[f"{trend}_confidence"] = max(0.3, 1.0 - years_ahead * 0.05)
        
        return projections
    
    def simulate_climate_scenario(self, scenario: str, years: int = 50) -> List[Dict[str, Any]]:
        """Simulate different climate scenarios"""
        scenarios = {
            'baseline': {'temp_increase': 0, 'precip_change': 0, 'extreme_multiplier': 1.0},
            'moderate_warming': {'temp_increase': 2, 'precip_change': 5, 'extreme_multiplier': 1.2},
            'high_warming': {'temp_increase': 4, 'precip_change': -5, 'extreme_multiplier': 1.8},
            'extreme_warming': {'temp_increase': 6, 'precip_change': -15, 'extreme_multiplier': 2.5}
        }
        
        if scenario not in scenarios:
            scenario = 'baseline'
        
        params = scenarios[scenario]
        yearly_data = []
        
        for year in range(years):
            progress = year / years
            temp_change = params['temp_increase'] * progress
            precip_change = params['precip_change'] * progress
            extreme_freq = params['extreme_multiplier'] * (1 + progress * 0.5)
            
            yearly_data.append({
                'year': year,
                'temperature_change': temp_change,
                'precipitation_change': precip_change,
                'extreme_weather_frequency': extreme_freq,
                'sea_level_rise': progress * 0.5,  # meters
                'ecosystem_stress': min(1.0, progress * 1.5)
            })
        
        return yearly_data


class WeatherImpactSimulator:
    """Main weather impact simulation engine"""
    
    def __init__(self, location: str = "default"):
        self.location = location
        self.current_conditions = None
        self.forecast = None
        self.impact_analyzer = ImpactAnalyzer()
        self.climate_model = ClimateModel(location)
        self.active_patterns = []
        self.simulation_running = False
        self.event_log = deque(maxlen=1000)
        self.metrics = defaultdict(float)
        self.callbacks = []
        
        # Initialize with clear conditions
        self.current_conditions = WeatherCondition(
            weather_type=WeatherType.CLEAR,
            temperature=20,
            humidity=50,
            wind_speed=5,
            precipitation=0,
            pressure=1013.25,
            visibility=20,
            uv_index=5
        )
    
    def add_pattern(self, pattern: WeatherPattern):
        """Add a weather pattern to the simulation"""
        self.active_patterns.append(pattern)
        self._log_event("pattern_added", f"Added pattern: {type(pattern).__name__}")
    
    def remove_pattern(self, pattern: WeatherPattern):
        """Remove a weather pattern from simulation"""
        if pattern in self.active_patterns:
            self.active_patterns.remove(pattern)
            self._log_event("pattern_removed", f"Removed pattern: {type(pattern).__name__}")
    
    def generate_forecast(self, hours: int = 24) -> WeatherForecast:
        """Generate weather forecast"""
        if not self.active_patterns:
            # Default to seasonal pattern
            current_season = self._get_current_season()
            pattern = SeasonalPattern(current_season, self.location)
            self.active_patterns.append(pattern)
        
        # Use first active pattern for forecast
        primary_pattern = self.active_patterns[0]
        conditions = primary_pattern.generate_conditions(hours)
        
        # Add some uncertainty
        accuracy = random.uniform(0.7, 0.95)
        
        self.forecast = WeatherForecast(
            conditions=conditions,
            forecast_horizon=hours,
            accuracy_score=accuracy,
            source="weather_impact_simulator"
        )
        
        self._log_event("forecast_generated", f"Generated {hours}h forecast with {accuracy:.2f} accuracy")
        return self.forecast
    
    def update_conditions(self, conditions: WeatherCondition = None):
        """Update current weather conditions"""
        if conditions:
            self.current_conditions = conditions
        else:
            # Auto-update based on patterns
            if self.forecast and self.forecast.conditions:
                # Use next forecast condition
                self.current_conditions = self.forecast.conditions[0]
                self.forecast.conditions = self.forecast.conditions[1:]
        
        self._log_event("conditions_updated", f"Weather: {self.current_conditions.weather_type.value}")
        self._update_metrics()
    
    def analyze_current_impact(self, sectors: List[str] = None) -> Dict[str, ImpactAssessment]:
        """Analyze current weather impact"""
        if not self.current_conditions:
            raise ValueError("No current conditions available")
        
        if sectors is None:
            sectors = list(self.impact_analyzer.sector_analyzers.keys())
        
        impacts = {}
        for sector in sectors:
            impacts[sector] = self.impact_analyzer.analyze_impact(self.current_conditions, sector)
        
        self._log_event("impact_analyzed", f"Analyzed impact for {len(sectors)} sectors")
        return impacts
    
    def simulate_extreme_event(self, event_type: WeatherType, intensity: float = 1.0, 
                             duration: int = 6) -> List[ImpactAssessment]:
        """Simulate extreme weather event"""
        extreme_pattern = ExtremeWeatherPattern(event_type, intensity)
        conditions = extreme_pattern.generate_conditions(duration)
        
        all_impacts = []
        for condition in conditions:
            impacts = self.impact_analyzer.analyze_all_sectors(condition)
            all_impacts.extend(impacts)
        
        self._log_event("extreme_event", f"Simulated {event_type.value} for {duration}h at {intensity} intensity")
        return all_impacts
    
    async def run_continuous_simulation(self, hours: int = 24, update_interval: int = 1):
        """Run continuous weather simulation"""
        self.simulation_running = True
        self._log_event("simulation_started", f"Running for {hours}h with {update_interval}h intervals")
        
        try:
            for hour in range(0, hours, update_interval):
                if not self.simulation_running:
                    break
                
                # Update conditions
                self.update_conditions()
                
                # Analyze impacts
                impacts = self.analyze_current_impact()
                
                # Execute callbacks
                for callback in self.callbacks:
                    await callback(self.current_conditions, impacts)
                
                # Sleep for real-time simulation
                await asyncio.sleep(1)  # 1 second represents 1 hour
                
                self.metrics['simulation_hours'] += update_interval
        
        finally:
            self.simulation_running = False
            self._log_event("simulation_stopped", f"Completed simulation after {hour}h")
    
    def stop_simulation(self):
        """Stop continuous simulation"""
        self.simulation_running = False
    
    def add_callback(self, callback: Callable):
        """Add callback function for simulation events"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Remove callback function"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def get_simulation_metrics(self) -> Dict[str, Any]:
        """Get simulation performance metrics"""
        return dict(self.metrics)
    
    def get_event_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent simulation events"""
        return list(self.event_log)[-limit:]
    
    def export_simulation_data(self) -> Dict[str, Any]:
        """Export complete simulation data"""
        return {
            'location': self.location,
            'current_conditions': self.current_conditions.__dict__ if self.current_conditions else None,
            'forecast': {
                'conditions': [c.__dict__ for c in self.forecast.conditions],
                'forecast_horizon': self.forecast.forecast_horizon,
                'accuracy_score': self.forecast.accuracy_score,
                'last_updated': self.forecast.last_updated.isoformat(),
                'source': self.forecast.source
            } if self.forecast else None,
            'active_patterns': [type(p).__name__ for p in self.active_patterns],
            'metrics': self.get_simulation_metrics(),
            'event_log': self.get_event_log(),
            'climate_trends': self.climate_model.climate_trends
        }
    
    def import_simulation_data(self, data: Dict[str, Any]):
        """Import simulation data"""
        self.location = data.get('location', 'default')
        
        if data.get('current_conditions'):
            cond_data = data['current_conditions']
            self.current_conditions = WeatherCondition(**cond_data)
        
        if data.get('forecast'):
            forecast_data = data['forecast']
            conditions = [WeatherCondition(**c) for c in forecast_data['conditions']]
            self.forecast = WeatherForecast(
                conditions=conditions,
                forecast_horizon=forecast_data['forecast_horizon'],
                accuracy_score=forecast_data['accuracy_score'],
                last_updated=datetime.fromisoformat(forecast_data['last_updated']),
                source=forecast_data['source']
            )
        
        self.metrics.update(data.get('metrics', {}))
        self.climate_model.climate_trends = data.get('climate_trends', {})
        
        self._log_event("data_imported", "Simulation data imported successfully")
    
    def _get_current_season(self) -> SeasonType:
        """Determine current season"""
        month = datetime.now().month
        if 3 <= month <= 5:
            return SeasonType.SPRING
        elif 6 <= month <= 8:
            return SeasonType.SUMMER
        elif 9 <= month <= 11:
            return SeasonType.FALL
        else:
            return SeasonType.WINTER
    
    def _log_event(self, event_type: str, description: str):
        """Log simulation event"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'description': description
        }
        self.event_log.append(event)
    
    def _update_metrics(self):
        """Update simulation metrics"""
        if self.current_conditions:
            self.metrics['total_updates'] += 1
            self.metrics['avg_temperature'] = (
                (self.metrics['avg_temperature'] * (self.metrics['total_updates'] - 1) + 
                 self.current_conditions.temperature) / self.metrics['total_updates']
            )
            self.metrics['avg_humidity'] = (
                (self.metrics['avg_humidity'] * (self.metrics['total_updates'] - 1) + 
                 self.current_conditions.humidity) / self.metrics['total_updates']
            )
            self.metrics['max_wind_speed'] = max(
                self.metrics['max_wind_speed'], 
                self.current_conditions.wind_speed
            )


# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Create weather impact simulator
        simulator = WeatherImpactSimulator("New York")
        
        # Add seasonal pattern
        spring_pattern = SeasonalPattern(SeasonType.SPRING, "New York")
        simulator.add_pattern(spring_pattern)
        
        # Generate forecast
        forecast = simulator.generate_forecast(48)
        print(f"Generated forecast for {len(forecast.conditions)} hours")
        print(f"Forecast accuracy: {forecast.accuracy_score:.2f}")
        
        # Analyze current impact
        impacts = simulator.analyze_current_impact(['transportation', 'agriculture', 'energy'])
        for sector, impact in impacts.items():
            print(f"{sector}: {impact.severity.name} impact with ${impact.estimated_loss:,} potential loss")
        
        # Simulate extreme weather event
        hurricane_impacts = simulator.simulate_extreme_event(WeatherType.HURRICANE, 0.8, 12)
        print(f"Hurricane simulation generated {len(hurricane_impacts)} impact assessments")
        
        # Test climate modeling
        climate_trends = simulator.climate_model.analyze_climate_trends(20)
        print(f"Climate trends: {climate_trends}")
        
        # Test continuous simulation callback
        async def weather_callback(conditions, impacts):
            severe_impacts = [i for i in impacts.values() if i.severity.value >= 3]
            if severe_impacts:
                print(f"ALERT: {len(severe_impacts)} severe weather impacts detected!")
        
        simulator.add_callback(weather_callback)
        
        # Run short simulation
        print("Running 5-hour continuous simulation...")
        await simulator.run_continuous_simulation(5, 1)
        
        # Export simulation data
        export_data = simulator.export_simulation_data()
        print(f"Simulation generated {len(export_data['event_log'])} events")
        print(f"Simulation metrics: {simulator.get_simulation_metrics()}")
    
    # Run the example
    asyncio.run(main())