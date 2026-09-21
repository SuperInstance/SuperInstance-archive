"""
ActiveLog Marine Advanced Suite - Fuel Consumption Prediction

Advanced fuel consumption prediction system with machine learning models,
environmental factor analysis, and optimization recommendations for marine vessels.
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
import math
from scipy import optimize, stats
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


class VesselType(Enum):
    SAILBOAT = "sailboat"
    MOTOR_YACHT = "motor_yacht"
    TRAWLER = "trawler"
    SPORTFISH = "sportfish"
    CATAMARAN = "catamaran"
    COMMERCIAL = "commercial"
    WORKBOAT = "workboat"


class EngineType(Enum):
    DIESEL_INBOARD = "diesel_inboard"
    GASOLINE_INBOARD = "gasoline_inboard"
    DIESEL_OUTBOARD = "diesel_outboard"
    GASOLINE_OUTBOARD = "gasoline_outboard"
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    TURBINE = "turbine"


class OperatingMode(Enum):
    IDLE = "idle"
    SLOW_CRUISE = "slow_cruise"
    CRUISE = "cruise"
    FAST_CRUISE = "fast_cruise"
    MAXIMUM = "maximum"
    TROLLING = "trolling"
    HARBOR_MANEUVERING = "harbor_maneuvering"


class SeaState(Enum):
    CALM = 0        # 0-0.1m waves
    SMOOTH = 1      # 0.1-0.5m waves
    SLIGHT = 2      # 0.5-1.25m waves
    MODERATE = 3    # 1.25-2.5m waves
    ROUGH = 4       # 2.5-4m waves
    VERY_ROUGH = 5  # 4-6m waves
    HIGH = 6        # 6-9m waves
    VERY_HIGH = 7   # 9-14m waves


@dataclass
class EngineSpecifications:
    engine_id: str
    manufacturer: str
    model: str
    engine_type: EngineType
    max_power: float            # kW or HP
    displacement: float         # liters
    cylinders: int
    fuel_type: str             # "diesel", "gasoline", "electric"
    specific_fuel_consumption: float  # g/kWh or gallons/HP-hour
    idle_consumption: float     # liters/hour at idle
    optimal_rpm: int           # most efficient RPM
    max_rpm: int
    installation_date: datetime


@dataclass
class VesselSpecifications:
    vessel_id: str
    vessel_name: str
    vessel_type: VesselType
    length_overall: float      # meters
    beam: float               # meters
    draft: float              # meters
    displacement: float       # tonnes
    wetted_surface: float     # square meters
    engines: List[EngineSpecifications]
    fuel_capacity: float      # liters
    cruising_speed: float     # knots
    maximum_speed: float      # knots
    hull_type: str           # "displacement", "planing", "catamaran"


@dataclass
class EnvironmentalConditions:
    timestamp: datetime
    wind_speed: float          # knots
    wind_direction: float      # degrees relative to vessel heading
    wave_height: float         # meters
    wave_period: float         # seconds
    wave_direction: float      # degrees relative to vessel heading
    current_speed: float       # knots
    current_direction: float   # degrees relative to vessel heading
    sea_state: SeaState
    water_temperature: float   # Celsius
    air_temperature: float     # Celsius
    barometric_pressure: float # millibars
    visibility: float          # nautical miles


@dataclass
class VesselOperatingData:
    timestamp: datetime
    vessel_id: str
    speed_over_ground: float   # knots
    speed_through_water: float # knots
    engine_rpm: Dict[str, int] # RPM for each engine
    engine_load: Dict[str, float] # Load percentage for each engine
    fuel_flow_rate: Dict[str, float] # liters/hour for each engine
    operating_mode: OperatingMode
    heading: float             # degrees
    course: float             # degrees
    distance_traveled: float   # nautical miles since last reading
    engine_temperature: Dict[str, float] # Celsius for each engine
    engine_hours: Dict[str, float] # Operating hours for each engine


@dataclass
class FuelConsumptionPrediction:
    timestamp: datetime
    vessel_id: str
    prediction_horizon: int    # hours
    route_distance: float      # nautical miles
    estimated_consumption: float # liters
    consumption_rate: float    # liters/hour
    consumption_per_mile: float # liters/nautical mile
    confidence_interval: Tuple[float, float] # 95% confidence interval
    environmental_impact: float # additional consumption due to conditions
    optimization_potential: float # potential savings with optimization
    recommendations: List[str]
    model_confidence: float    # 0-1 ML model confidence


@dataclass
class FuelOptimizationRecommendation:
    timestamp: datetime
    vessel_id: str
    current_consumption: float # liters/hour
    optimized_consumption: float # liters/hour
    potential_savings: float   # liters/hour
    recommended_rpm: Dict[str, int]
    recommended_speed: float   # knots
    route_adjustments: List[str]
    operational_changes: List[str]
    environmental_considerations: List[str]
    payback_period: Optional[float] # hours to recover efficiency investment


class FuelConsumptionPredictor:
    """Advanced fuel consumption prediction and optimization system"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.vessel_specs: Dict[str, VesselSpecifications] = {}
        self.consumption_history: Dict[str, List[VesselOperatingData]] = {}
        self.environmental_history: Dict[str, List[EnvironmentalConditions]] = {}
        
        # Machine learning models
        self.consumption_model = None
        self.optimization_model = None
        self.scaler = StandardScaler()
        
        # Model features
        self.feature_columns = [
            'speed_over_ground', 'speed_through_water', 'avg_engine_rpm', 'avg_engine_load',
            'wind_speed', 'wave_height', 'current_speed', 'sea_state_numeric',
            'vessel_length', 'vessel_displacement', 'total_engine_power',
            'wind_relative_angle', 'wave_relative_angle', 'current_relative_angle',
            'hull_speed_ratio', 'displacement_speed_ratio'
        ]
        
        self.history_limit = 2000
        self._initialize_database()
        self._initialize_models()
    
    def _initialize_database(self):
        """Initialize fuel consumption database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Vessel specifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vessel_specifications (
                vessel_id TEXT PRIMARY KEY,
                vessel_name TEXT,
                vessel_type TEXT,
                length_overall REAL,
                beam REAL,
                draft REAL,
                displacement REAL,
                wetted_surface REAL,
                fuel_capacity REAL,
                cruising_speed REAL,
                maximum_speed REAL,
                hull_type TEXT,
                engine_specs TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Operating data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vessel_operating_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                vessel_id TEXT,
                speed_over_ground REAL,
                speed_through_water REAL,
                engine_rpm TEXT,  -- JSON
                engine_load TEXT, -- JSON
                fuel_flow_rate TEXT, -- JSON
                operating_mode TEXT,
                heading REAL,
                course REAL,
                distance_traveled REAL,
                engine_temperature TEXT, -- JSON
                engine_hours TEXT, -- JSON
                FOREIGN KEY (vessel_id) REFERENCES vessel_specifications (vessel_id)
            )
        """)
        
        # Environmental conditions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environmental_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                vessel_id TEXT,
                wind_speed REAL,
                wind_direction REAL,
                wave_height REAL,
                wave_period REAL,
                wave_direction REAL,
                current_speed REAL,
                current_direction REAL,
                sea_state INTEGER,
                water_temperature REAL,
                air_temperature REAL,
                barometric_pressure REAL,
                visibility REAL,
                FOREIGN KEY (vessel_id) REFERENCES vessel_specifications (vessel_id)
            )
        """)
        
        # Fuel predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fuel_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                vessel_id TEXT,
                prediction_horizon INTEGER,
                route_distance REAL,
                estimated_consumption REAL,
                consumption_rate REAL,
                consumption_per_mile REAL,
                confidence_lower REAL,
                confidence_upper REAL,
                environmental_impact REAL,
                optimization_potential REAL,
                model_confidence REAL,
                FOREIGN KEY (vessel_id) REFERENCES vessel_specifications (vessel_id)
            )
        """)
        
        # Optimization recommendations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                vessel_id TEXT,
                current_consumption REAL,
                optimized_consumption REAL,
                potential_savings REAL,
                recommended_rpm TEXT, -- JSON
                recommended_speed REAL,
                route_adjustments TEXT, -- JSON
                operational_changes TEXT, -- JSON
                payback_period REAL,
                FOREIGN KEY (vessel_id) REFERENCES vessel_specifications (vessel_id)
            )
        """)
        
        # Create indices
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_operating_data_vessel_time 
            ON vessel_operating_data (vessel_id, timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_environmental_vessel_time 
            ON environmental_conditions (vessel_id, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def _initialize_models(self):
        """Initialize machine learning models"""
        # Consumption prediction model
        self.consumption_model = RandomForestRegressor(
            n_estimators=150,
            max_depth=12,
            random_state=42,
            n_jobs=-1
        )
        
        # Optimization model
        self.optimization_model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=8,
            random_state=42
        )
        
        # Train with synthetic data for demonstration
        self._train_with_synthetic_data()
    
    def _train_with_synthetic_data(self):
        """Train models with synthetic fuel consumption data"""
        n_samples = 10000
        
        # Generate synthetic training data
        features = []
        consumption_targets = []
        optimization_targets = []
        
        for _ in range(n_samples):
            # Vessel characteristics
            length = np.random.uniform(8, 50)  # meters
            displacement = length ** 2.5 * np.random.uniform(0.1, 0.3)  # tonnes
            engine_power = length * np.random.uniform(15, 25)  # kW
            
            # Operating conditions
            speed_sog = np.random.uniform(3, 25)  # knots
            speed_stw = speed_sog + np.random.normal(0, 0.5)
            engine_rpm = np.random.uniform(800, 3000)
            engine_load = np.random.uniform(20, 95)  # percent
            
            # Environmental conditions
            wind_speed = np.random.exponential(8) + 1
            wave_height = np.random.exponential(1.5)
            current_speed = np.random.exponential(1)
            sea_state = min(7, int(wave_height))
            
            # Relative angles (0-180 degrees)
            wind_angle = np.random.uniform(0, 180)
            wave_angle = np.random.uniform(0, 180)
            current_angle = np.random.uniform(0, 180)
            
            # Speed ratios
            hull_speed = 1.34 * math.sqrt(length)  # Theoretical hull speed
            hull_speed_ratio = speed_sog / hull_speed
            displacement_speed_ratio = speed_sog / (displacement ** (1/3))
            
            features.append([
                speed_sog, speed_stw, engine_rpm, engine_load,
                wind_speed, wave_height, current_speed, sea_state,
                length, displacement, engine_power,
                wind_angle, wave_angle, current_angle,
                hull_speed_ratio, displacement_speed_ratio
            ])
            
            # Calculate synthetic fuel consumption based on realistic factors
            # Base consumption from engine load and RPM
            base_consumption = (engine_power * engine_load / 100) * 0.25  # L/hr baseline
            
            # Speed factor (higher speeds = exponentially more fuel)
            speed_factor = 1 + (hull_speed_ratio - 1) ** 2
            
            # Environmental factors
            wind_factor = 1 + (wind_speed / 30) * (1 - math.cos(math.radians(wind_angle)))
            wave_factor = 1 + (wave_height / 4) * (1 - math.cos(math.radians(wave_angle)))
            current_factor = 1 + (current_speed / 5) * (1 - math.cos(math.radians(current_angle + 180)))
            
            # Total consumption
            total_consumption = base_consumption * speed_factor * wind_factor * wave_factor * current_factor
            consumption_targets.append(max(1, total_consumption))
            
            # Optimization target (potential improvement)
            optimization_potential = total_consumption * np.random.uniform(0.05, 0.25)  # 5-25% potential savings
            optimization_targets.append(optimization_potential)
        
        # Train models
        X = np.array(features)
        y_consumption = np.array(consumption_targets)
        y_optimization = np.array(optimization_targets)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train consumption model
        self.consumption_model.fit(X_scaled, y_consumption)
        
        # Train optimization model
        self.optimization_model.fit(X_scaled, y_optimization)
        
        print(f"Models trained on {n_samples} synthetic data points")
    
    async def register_vessel(self, vessel_specs: VesselSpecifications):
        """Register a vessel with its specifications"""
        self.vessel_specs[vessel_specs.vessel_id] = vessel_specs
        self.consumption_history[vessel_specs.vessel_id] = []
        self.environmental_history[vessel_specs.vessel_id] = []
        
        # Store in database
        await self._store_vessel_specs(vessel_specs)
        
        print(f"Vessel registered: {vessel_specs.vessel_name} ({vessel_specs.vessel_id})")
        print(f"Type: {vessel_specs.vessel_type.value}, Length: {vessel_specs.length_overall}m")
        print(f"Engines: {len(vessel_specs.engines)}, Max Speed: {vessel_specs.maximum_speed} knots")
    
    async def update_operating_data(self, operating_data: VesselOperatingData):
        """Update vessel operating data"""
        vessel_id = operating_data.vessel_id
        
        if vessel_id not in self.vessel_specs:
            raise ValueError(f"Vessel not registered: {vessel_id}")
        
        # Add to history
        self.consumption_history[vessel_id].append(operating_data)
        if len(self.consumption_history[vessel_id]) > self.history_limit:
            self.consumption_history[vessel_id] = self.consumption_history[vessel_id][-self.history_limit:]
        
        # Store in database
        await self._store_operating_data(operating_data)
    
    async def update_environmental_conditions(self, vessel_id: str, conditions: EnvironmentalConditions):
        """Update environmental conditions for vessel"""
        if vessel_id not in self.vessel_specs:
            raise ValueError(f"Vessel not registered: {vessel_id}")
        
        # Add to history
        self.environmental_history[vessel_id].append(conditions)
        if len(self.environmental_history[vessel_id]) > 200:
            self.environmental_history[vessel_id] = self.environmental_history[vessel_id][-200:]
        
        # Store in database
        await self._store_environmental_conditions(vessel_id, conditions)
    
    async def predict_fuel_consumption(self, vessel_id: str, route_distance: float,
                                     prediction_horizon: int = 8,
                                     target_speed: Optional[float] = None) -> FuelConsumptionPrediction:
        """Predict fuel consumption for route"""
        if vessel_id not in self.vessel_specs:
            raise ValueError(f"Vessel not registered: {vessel_id}")
        
        vessel_specs = self.vessel_specs[vessel_id]
        
        # Get latest operating and environmental data
        latest_operating = None
        latest_environmental = None
        
        if self.consumption_history[vessel_id]:
            latest_operating = self.consumption_history[vessel_id][-1]
        
        if self.environmental_history[vessel_id]:
            latest_environmental = self.environmental_history[vessel_id][-1]
        
        # Use default values if no historical data
        if not latest_operating:
            latest_operating = self._create_default_operating_data(vessel_id, target_speed)
        
        if not latest_environmental:
            latest_environmental = self._create_default_environmental_conditions()
        
        # Extract features for prediction
        features = self._extract_prediction_features(
            vessel_specs, latest_operating, latest_environmental, target_speed
        )
        
        # Make prediction
        features_scaled = self.scaler.transform([features])
        predicted_rate = self.consumption_model.predict(features_scaled)[0]
        
        # Calculate route consumption
        if target_speed:
            travel_time = route_distance / target_speed
        else:
            travel_time = route_distance / vessel_specs.cruising_speed
        
        total_consumption = predicted_rate * travel_time
        consumption_per_mile = total_consumption / max(route_distance, 0.1)
        
        # Calculate confidence interval (simplified)
        prediction_std = predicted_rate * 0.15  # Assume 15% standard deviation
        confidence_lower = max(0, total_consumption - 1.96 * prediction_std * travel_time)
        confidence_upper = total_consumption + 1.96 * prediction_std * travel_time
        
        # Calculate environmental impact
        environmental_impact = self._calculate_environmental_impact(latest_environmental, predicted_rate)
        
        # Calculate optimization potential
        optimization_features_scaled = features_scaled
        optimization_potential = self.optimization_model.predict(optimization_features_scaled)[0] * travel_time
        
        # Generate recommendations
        recommendations = self._generate_consumption_recommendations(
            vessel_specs, latest_operating, latest_environmental, predicted_rate
        )
        
        # Model confidence based on data quality and history
        model_confidence = self._calculate_model_confidence(vessel_id, features)
        
        prediction = FuelConsumptionPrediction(
            timestamp=datetime.utcnow(),
            vessel_id=vessel_id,
            prediction_horizon=prediction_horizon,
            route_distance=route_distance,
            estimated_consumption=total_consumption,
            consumption_rate=predicted_rate,
            consumption_per_mile=consumption_per_mile,
            confidence_interval=(confidence_lower, confidence_upper),
            environmental_impact=environmental_impact,
            optimization_potential=optimization_potential,
            recommendations=recommendations,
            model_confidence=model_confidence
        )
        
        # Store prediction
        await self._store_prediction(prediction)
        
        return prediction
    
    async def generate_optimization_recommendations(self, vessel_id: str,
                                                  target_distance: float = 100,
                                                  target_time: Optional[float] = None) -> FuelOptimizationRecommendation:
        """Generate fuel optimization recommendations"""
        if vessel_id not in self.vessel_specs:
            raise ValueError(f"Vessel not registered: {vessel_id}")
        
        vessel_specs = self.vessel_specs[vessel_id]
        
        # Get current operating state
        if not self.consumption_history[vessel_id]:
            raise ValueError(f"No operating data available for vessel: {vessel_id}")
        
        current_operating = self.consumption_history[vessel_id][-1]
        current_environmental = (self.environmental_history[vessel_id][-1] 
                               if self.environmental_history[vessel_id] 
                               else self._create_default_environmental_conditions())
        
        # Calculate current consumption rate
        current_consumption = sum(current_operating.fuel_flow_rate.values())
        
        # Optimize operating parameters
        optimized_params = await self._optimize_operating_parameters(
            vessel_specs, current_operating, current_environmental, target_distance, target_time
        )
        
        # Calculate potential savings
        optimized_consumption = optimized_params['fuel_consumption']
        potential_savings = current_consumption - optimized_consumption
        
        # Generate recommendations
        route_adjustments = []
        operational_changes = []
        environmental_considerations = []
        
        # Route recommendations
        if current_environmental.wind_speed > 15:
            route_adjustments.append("Consider route adjustment to reduce headwind exposure")
        
        if current_environmental.wave_height > 2:
            route_adjustments.append("Route through calmer waters if possible")
        
        if current_environmental.current_speed > 1:
            if current_environmental.current_direction < 90 or current_environmental.current_direction > 270:
                route_adjustments.append("Take advantage of favorable current")
            else:
                route_adjustments.append("Minimize time against adverse current")
        
        # Operational recommendations
        if optimized_params['recommended_speed'] != current_operating.speed_over_ground:
            if optimized_params['recommended_speed'] < current_operating.speed_over_ground:
                operational_changes.append(f"Reduce speed to {optimized_params['recommended_speed']:.1f} knots for fuel efficiency")
            else:
                operational_changes.append(f"Increase speed to {optimized_params['recommended_speed']:.1f} knots for optimal efficiency")
        
        for engine_id, rpm in optimized_params['recommended_rpm'].items():
            current_rpm = current_operating.engine_rpm.get(engine_id, 0)
            if abs(rpm - current_rpm) > 50:
                operational_changes.append(f"Adjust {engine_id} RPM from {current_rpm} to {rpm}")
        
        # Environmental considerations
        if current_environmental.sea_state.value > 3:
            environmental_considerations.append("Rough seas - prioritize safety over fuel efficiency")
        
        if current_environmental.visibility < 2:
            environmental_considerations.append("Poor visibility - maintain safe speed regardless of fuel efficiency")
        
        # Calculate payback period for efficiency investments
        payback_period = None
        if potential_savings > 0:
            # Assume investment in efficiency monitoring/optimization
            investment_cost = 1000  # Hypothetical cost in fuel units
            payback_period = investment_cost / (potential_savings * 24)  # Days
        
        recommendation = FuelOptimizationRecommendation(
            timestamp=datetime.utcnow(),
            vessel_id=vessel_id,
            current_consumption=current_consumption,
            optimized_consumption=optimized_consumption,
            potential_savings=potential_savings,
            recommended_rpm=optimized_params['recommended_rpm'],
            recommended_speed=optimized_params['recommended_speed'],
            route_adjustments=route_adjustments,
            operational_changes=operational_changes,
            environmental_considerations=environmental_considerations,
            payback_period=payback_period
        )
        
        # Store recommendation
        await self._store_optimization_recommendation(recommendation)
        
        return recommendation
    
    async def _optimize_operating_parameters(self, vessel_specs: VesselSpecifications,
                                           current_operating: VesselOperatingData,
                                           environmental: EnvironmentalConditions,
                                           target_distance: float,
                                           target_time: Optional[float]) -> Dict[str, Any]:
        """Optimize operating parameters for fuel efficiency"""
        
        # Define optimization bounds
        speed_bounds = (vessel_specs.cruising_speed * 0.6, vessel_specs.maximum_speed * 0.9)
        
        # If target time is specified, calculate required speed
        if target_time:
            required_speed = target_distance / target_time
            speed_bounds = (required_speed * 0.95, required_speed * 1.05)
        
        # Optimize speed for fuel efficiency
        def fuel_consumption_objective(speed):
            # Create temporary operating data with new speed
            temp_features = self._extract_prediction_features(
                vessel_specs, current_operating, environmental, speed
            )
            features_scaled = self.scaler.transform([temp_features])
            return self.consumption_model.predict(features_scaled)[0]
        
        # Find optimal speed
        result = optimize.minimize_scalar(
            fuel_consumption_objective,
            bounds=speed_bounds,
            method='bounded'
        )
        
        optimal_speed = result.x
        optimal_consumption = result.fun
        
        # Calculate optimal RPM for engines
        optimal_rpm = {}
        for engine in vessel_specs.engines:
            # Simple RPM calculation based on speed and engine characteristics
            load_factor = min(0.85, optimal_speed / vessel_specs.maximum_speed)
            optimal_rpm[engine.engine_id] = int(engine.optimal_rpm * load_factor)
        
        return {
            'recommended_speed': optimal_speed,
            'fuel_consumption': optimal_consumption,
            'recommended_rpm': optimal_rpm
        }
    
    def _extract_prediction_features(self, vessel_specs: VesselSpecifications,
                                   operating_data: VesselOperatingData,
                                   environmental: EnvironmentalConditions,
                                   target_speed: Optional[float] = None) -> List[float]:
        """Extract features for ML prediction"""
        
        # Use target speed if provided, otherwise use current speed
        speed_sog = target_speed if target_speed else operating_data.speed_over_ground
        speed_stw = speed_sog  # Assume same for simplification
        
        # Engine parameters (average if multiple engines)
        avg_rpm = np.mean(list(operating_data.engine_rpm.values())) if operating_data.engine_rpm else 1500
        avg_load = np.mean(list(operating_data.engine_load.values())) if operating_data.engine_load else 50
        
        # Environmental conditions
        wind_speed = environmental.wind_speed
        wave_height = environmental.wave_height
        current_speed = environmental.current_speed
        sea_state_numeric = environmental.sea_state.value
        
        # Vessel characteristics
        vessel_length = vessel_specs.length_overall
        vessel_displacement = vessel_specs.displacement
        total_engine_power = sum(engine.max_power for engine in vessel_specs.engines)
        
        # Relative angles (wind, wave, current relative to vessel heading)
        wind_relative_angle = abs(environmental.wind_direction)
        wave_relative_angle = abs(environmental.wave_direction)
        current_relative_angle = abs(environmental.current_direction)
        
        # Speed ratios
        hull_speed = 1.34 * math.sqrt(vessel_length)  # Theoretical hull speed in knots
        hull_speed_ratio = speed_sog / hull_speed
        displacement_speed_ratio = speed_sog / (vessel_displacement ** (1/3))
        
        return [
            speed_sog, speed_stw, avg_rpm, avg_load,
            wind_speed, wave_height, current_speed, sea_state_numeric,
            vessel_length, vessel_displacement, total_engine_power,
            wind_relative_angle, wave_relative_angle, current_relative_angle,
            hull_speed_ratio, displacement_speed_ratio
        ]
    
    def _create_default_operating_data(self, vessel_id: str, target_speed: Optional[float] = None) -> VesselOperatingData:
        """Create default operating data for vessel"""
        vessel_specs = self.vessel_specs[vessel_id]
        speed = target_speed if target_speed else vessel_specs.cruising_speed
        
        # Default engine parameters
        engine_rpm = {}
        engine_load = {}
        fuel_flow_rate = {}
        engine_temp = {}
        engine_hours = {}
        
        for engine in vessel_specs.engines:
            load_factor = min(0.75, speed / vessel_specs.maximum_speed)
            engine_rpm[engine.engine_id] = int(engine.optimal_rpm * load_factor)
            engine_load[engine.engine_id] = load_factor * 100
            fuel_flow_rate[engine.engine_id] = engine.max_power * load_factor * 0.25  # Simplified
            engine_temp[engine.engine_id] = 85.0  # Normal operating temperature
            engine_hours[engine.engine_id] = 1000.0  # Default hours
        
        return VesselOperatingData(
            timestamp=datetime.utcnow(),
            vessel_id=vessel_id,
            speed_over_ground=speed,
            speed_through_water=speed,
            engine_rpm=engine_rpm,
            engine_load=engine_load,
            fuel_flow_rate=fuel_flow_rate,
            operating_mode=OperatingMode.CRUISE,
            heading=180.0,
            course=180.0,
            distance_traveled=0.0,
            engine_temperature=engine_temp,
            engine_hours=engine_hours
        )
    
    def _create_default_environmental_conditions(self) -> EnvironmentalConditions:
        """Create default environmental conditions"""
        return EnvironmentalConditions(
            timestamp=datetime.utcnow(),
            wind_speed=8.0,
            wind_direction=45.0,
            wave_height=1.0,
            wave_period=6.0,
            wave_direction=45.0,
            current_speed=0.5,
            current_direction=90.0,
            sea_state=SeaState.SLIGHT,
            water_temperature=20.0,
            air_temperature=22.0,
            barometric_pressure=1013.25,
            visibility=10.0
        )
    
    def _calculate_environmental_impact(self, environmental: EnvironmentalConditions, 
                                      base_consumption: float) -> float:
        """Calculate additional fuel consumption due to environmental conditions"""
        impact = 0.0
        
        # Wind impact
        if environmental.wind_speed > 10:
            wind_factor = (environmental.wind_speed - 10) / 20  # 0 to 1 scale
            # Headwind has more impact than tailwind
            angle_factor = 1 - math.cos(math.radians(environmental.wind_direction))
            impact += base_consumption * wind_factor * angle_factor * 0.1
        
        # Wave impact
        if environmental.wave_height > 1:
            wave_factor = (environmental.wave_height - 1) / 3  # 0 to 1 scale
            angle_factor = 1 - math.cos(math.radians(environmental.wave_direction))
            impact += base_consumption * wave_factor * angle_factor * 0.15
        
        # Current impact (negative current reduces consumption)
        current_factor = environmental.current_speed / 5  # 0 to 1+ scale
        if environmental.current_direction > 90 and environmental.current_direction < 270:
            # Adverse current
            impact += base_consumption * current_factor * 0.1
        else:
            # Favorable current
            impact -= base_consumption * current_factor * 0.05
        
        return impact
    
    def _generate_consumption_recommendations(self, vessel_specs: VesselSpecifications,
                                            operating: VesselOperatingData,
                                            environmental: EnvironmentalConditions,
                                            predicted_rate: float) -> List[str]:
        """Generate fuel consumption recommendations"""
        recommendations = []
        
        # Speed recommendations
        hull_speed = 1.34 * math.sqrt(vessel_specs.length_overall)
        if operating.speed_over_ground > hull_speed * 1.2:
            recommendations.append(f"Consider reducing speed below {hull_speed:.1f} knots for better fuel efficiency")
        
        # Engine load recommendations
        avg_load = np.mean(list(operating.engine_load.values()))
        if avg_load > 85:
            recommendations.append("High engine load detected - consider reducing power for efficiency")
        elif avg_load < 40:
            recommendations.append("Low engine load - consider optimizing speed for better efficiency")
        
        # Environmental recommendations
        if environmental.wind_speed > 15 and abs(environmental.wind_direction) < 45:
            recommendations.append("Strong headwind - consider course adjustment or speed reduction")
        
        if environmental.wave_height > 2 and abs(environmental.wave_direction) < 45:
            recommendations.append("Head seas causing increased consumption - consider alternative routing")
        
        if environmental.current_speed > 1:
            if environmental.current_direction > 90 and environmental.current_direction < 270:
                recommendations.append("Adverse current detected - optimize timing or route to minimize impact")
            else:
                recommendations.append("Favorable current available - consider maximizing benefit")
        
        # Operating mode recommendations
        if operating.operating_mode == OperatingMode.MAXIMUM:
            recommendations.append("Maximum power operation is fuel intensive - use only when necessary")
        
        return recommendations
    
    def _calculate_model_confidence(self, vessel_id: str, features: List[float]) -> float:
        """Calculate model prediction confidence"""
        confidence = 1.0
        
        # Reduce confidence if vessel has limited history
        history_length = len(self.consumption_history.get(vessel_id, []))
        if history_length < 10:
            confidence *= 0.6
        elif history_length < 50:
            confidence *= 0.8
        
        # Reduce confidence for extreme operating conditions
        speed_sog = features[0]
        if speed_sog > 25 or speed_sog < 2:
            confidence *= 0.7
        
        wind_speed = features[4]
        if wind_speed > 30:
            confidence *= 0.8
        
        wave_height = features[5]
        if wave_height > 4:
            confidence *= 0.7
        
        return max(0.3, confidence)  # Minimum confidence threshold
    
    async def _store_vessel_specs(self, vessel_specs: VesselSpecifications):
        """Store vessel specifications in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO vessel_specifications 
            (vessel_id, vessel_name, vessel_type, length_overall, beam, draft,
             displacement, wetted_surface, fuel_capacity, cruising_speed, maximum_speed,
             hull_type, engine_specs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vessel_specs.vessel_id, vessel_specs.vessel_name, vessel_specs.vessel_type.value,
            vessel_specs.length_overall, vessel_specs.beam, vessel_specs.draft,
            vessel_specs.displacement, vessel_specs.wetted_surface, vessel_specs.fuel_capacity,
            vessel_specs.cruising_speed, vessel_specs.maximum_speed, vessel_specs.hull_type,
            json.dumps([asdict(engine) for engine in vessel_specs.engines])
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_operating_data(self, operating_data: VesselOperatingData):
        """Store operating data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO vessel_operating_data 
            (timestamp, vessel_id, speed_over_ground, speed_through_water, engine_rpm,
             engine_load, fuel_flow_rate, operating_mode, heading, course,
             distance_traveled, engine_temperature, engine_hours)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            operating_data.timestamp, operating_data.vessel_id, operating_data.speed_over_ground,
            operating_data.speed_through_water, json.dumps(operating_data.engine_rpm),
            json.dumps(operating_data.engine_load), json.dumps(operating_data.fuel_flow_rate),
            operating_data.operating_mode.value, operating_data.heading, operating_data.course,
            operating_data.distance_traveled, json.dumps(operating_data.engine_temperature),
            json.dumps(operating_data.engine_hours)
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_environmental_conditions(self, vessel_id: str, conditions: EnvironmentalConditions):
        """Store environmental conditions in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO environmental_conditions 
            (timestamp, vessel_id, wind_speed, wind_direction, wave_height, wave_period,
             wave_direction, current_speed, current_direction, sea_state, water_temperature,
             air_temperature, barometric_pressure, visibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conditions.timestamp, vessel_id, conditions.wind_speed, conditions.wind_direction,
            conditions.wave_height, conditions.wave_period, conditions.wave_direction,
            conditions.current_speed, conditions.current_direction, conditions.sea_state.value,
            conditions.water_temperature, conditions.air_temperature, conditions.barometric_pressure,
            conditions.visibility
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_prediction(self, prediction: FuelConsumptionPrediction):
        """Store fuel prediction in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO fuel_predictions 
            (timestamp, vessel_id, prediction_horizon, route_distance, estimated_consumption,
             consumption_rate, consumption_per_mile, confidence_lower, confidence_upper,
             environmental_impact, optimization_potential, model_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction.timestamp, prediction.vessel_id, prediction.prediction_horizon,
            prediction.route_distance, prediction.estimated_consumption, prediction.consumption_rate,
            prediction.consumption_per_mile, prediction.confidence_interval[0], prediction.confidence_interval[1],
            prediction.environmental_impact, prediction.optimization_potential, prediction.model_confidence
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_optimization_recommendation(self, recommendation: FuelOptimizationRecommendation):
        """Store optimization recommendation in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO optimization_recommendations 
            (timestamp, vessel_id, current_consumption, optimized_consumption, potential_savings,
             recommended_rpm, recommended_speed, route_adjustments, operational_changes, payback_period)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recommendation.timestamp, recommendation.vessel_id, recommendation.current_consumption,
            recommendation.optimized_consumption, recommendation.potential_savings,
            json.dumps(recommendation.recommended_rpm), recommendation.recommended_speed,
            json.dumps(recommendation.route_adjustments), json.dumps(recommendation.operational_changes),
            recommendation.payback_period
        ))
        
        conn.commit()
        conn.close()


async def main():
    """Demonstration of fuel consumption prediction system"""
    
    # Initialize fuel consumption predictor
    predictor = FuelConsumptionPredictor("fuel_consumption.db")
    
    print("ActiveLog Marine Advanced - Fuel Consumption Prediction Demo")
    print("=" * 63)
    
    # Create sample engine specifications
    main_engine = EngineSpecifications(
        engine_id="main_engine_001",
        manufacturer="Caterpillar",
        model="C18 ACERT",
        engine_type=EngineType.DIESEL_INBOARD,
        max_power=425.0,  # kW
        displacement=18.1,  # liters
        cylinders=6,
        fuel_type="diesel",
        specific_fuel_consumption=205.0,  # g/kWh
        idle_consumption=8.0,  # liters/hour
        optimal_rpm=1800,
        max_rpm=2300,
        installation_date=datetime(2020, 1, 1)
    )
    
    # Create sample vessel specifications
    test_vessel = VesselSpecifications(
        vessel_id="mv_seafarer_001",
        vessel_name="MV SEAFARER",
        vessel_type=VesselType.MOTOR_YACHT,
        length_overall=18.3,  # meters
        beam=5.2,  # meters
        draft=1.8,  # meters
        displacement=22.5,  # tonnes
        wetted_surface=85.0,  # square meters
        engines=[main_engine],
        fuel_capacity=2000.0,  # liters
        cruising_speed=12.0,  # knots
        maximum_speed=18.0,  # knots
        hull_type="planing"
    )
    
    # Register vessel
    await predictor.register_vessel(test_vessel)
    
    print("\n" + "="*50)
    print("SIMULATING OPERATING CONDITIONS")
    print("="*50)
    
    # Simulate different operating scenarios
    scenarios = [
        {"name": "Calm Weather Cruising", "wind": 5, "waves": 0.5, "speed": 12},
        {"name": "Moderate Conditions", "wind": 15, "waves": 1.5, "speed": 10},
        {"name": "Rough Weather", "wind": 25, "waves": 3.0, "speed": 8},
        {"name": "High Speed Run", "wind": 10, "waves": 1.0, "speed": 16},
        {"name": "Economy Cruise", "wind": 8, "waves": 1.2, "speed": 9}
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i}: {scenario['name']} ---")
        
        # Create environmental conditions
        conditions = EnvironmentalConditions(
            timestamp=datetime.utcnow(),
            wind_speed=scenario['wind'],
            wind_direction=45.0 + np.random.uniform(-30, 30),
            wave_height=scenario['waves'],
            wave_period=6.0 + np.random.uniform(-2, 2),
            wave_direction=60.0 + np.random.uniform(-30, 30),
            current_speed=np.random.uniform(0, 1.5),
            current_direction=np.random.uniform(0, 360),
            sea_state=SeaState(min(7, int(scenario['waves']))),
            water_temperature=20.0 + np.random.uniform(-5, 5),
            air_temperature=22.0 + np.random.uniform(-5, 5),
            barometric_pressure=1013.25 + np.random.uniform(-10, 10),
            visibility=10.0 - scenario['waves']
        )
        
        # Create operating data
        speed = scenario['speed']
        engine_load = min(95, (speed / test_vessel.maximum_speed) * 100 + np.random.uniform(-10, 10))
        engine_rpm = int(main_engine.optimal_rpm * (speed / test_vessel.cruising_speed))
        fuel_flow = main_engine.max_power * (engine_load / 100) * 0.25  # Simplified calculation
        
        operating_data = VesselOperatingData(
            timestamp=datetime.utcnow(),
            vessel_id=test_vessel.vessel_id,
            speed_over_ground=speed,
            speed_through_water=speed + np.random.uniform(-0.5, 0.5),
            engine_rpm={main_engine.engine_id: engine_rpm},
            engine_load={main_engine.engine_id: engine_load},
            fuel_flow_rate={main_engine.engine_id: fuel_flow},
            operating_mode=OperatingMode.CRUISE,
            heading=180.0,
            course=180.0,
            distance_traveled=speed,  # Assume 1 hour intervals
            engine_temperature={main_engine.engine_id: 85.0 + np.random.uniform(-5, 10)},
            engine_hours={main_engine.engine_id: 1000.0 + i * 10}
        )
        
        # Update system with data
        await predictor.update_operating_data(operating_data)
        await predictor.update_environmental_conditions(test_vessel.vessel_id, conditions)
        
        # Generate fuel consumption prediction for 100 nautical mile route
        prediction = await predictor.predict_fuel_consumption(
            test_vessel.vessel_id, 
            route_distance=100.0,
            prediction_horizon=12,
            target_speed=speed
        )
        
        # Generate optimization recommendations
        optimization = await predictor.generate_optimization_recommendations(
            test_vessel.vessel_id,
            target_distance=100.0
        )
        
        # Display results
        print(f"Operating Conditions:")
        print(f"  Speed: {speed:.1f} knots, RPM: {engine_rpm}, Load: {engine_load:.0f}%")
        print(f"  Wind: {conditions.wind_speed:.1f} kts @ {conditions.wind_direction:.0f}°")
        print(f"  Waves: {conditions.wave_height:.1f}m, Current: {conditions.current_speed:.1f} kts")
        
        print(f"\nFuel Prediction (100 nm route):")
        print(f"  Estimated Consumption: {prediction.estimated_consumption:.1f} liters")
        print(f"  Consumption Rate: {prediction.consumption_rate:.1f} L/hr")
        print(f"  Consumption per Mile: {prediction.consumption_per_mile:.2f} L/nm")
        print(f"  Confidence Interval: {prediction.confidence_interval[0]:.1f} - {prediction.confidence_interval[1]:.1f} L")
        print(f"  Environmental Impact: {prediction.environmental_impact:+.1f} L/hr")
        print(f"  Optimization Potential: {prediction.optimization_potential:.1f} L")
        print(f"  Model Confidence: {prediction.model_confidence:.1%}")
        
        print(f"\nOptimization Recommendations:")
        print(f"  Current Consumption: {optimization.current_consumption:.1f} L/hr")
        print(f"  Optimized Consumption: {optimization.optimized_consumption:.1f} L/hr")
        print(f"  Potential Savings: {optimization.potential_savings:.1f} L/hr ({optimization.potential_savings/optimization.current_consumption:.1%})")
        print(f"  Recommended Speed: {optimization.recommended_speed:.1f} knots")
        
        if optimization.operational_changes:
            print(f"  Operational Changes:")
            for change in optimization.operational_changes[:3]:
                print(f"    • {change}")
        
        if optimization.route_adjustments:
            print(f"  Route Adjustments:")
            for adjustment in optimization.route_adjustments[:2]:
                print(f"    • {adjustment}")
        
        if prediction.recommendations:
            print(f"  Additional Recommendations:")
            for rec in prediction.recommendations[:3]:
                print(f"    • {rec}")
    
    print("\n" + "="*50)
    print("FUEL CONSUMPTION ANALYSIS SUMMARY")
    print("="*50)
    
    # Analyze consumption history
    vessel_history = predictor.consumption_history[test_vessel.vessel_id]
    if vessel_history:
        speeds = [data.speed_over_ground for data in vessel_history]
        fuel_rates = [sum(data.fuel_flow_rate.values()) for data in vessel_history]
        engine_loads = [np.mean(list(data.engine_load.values())) for data in vessel_history]
        
        print(f"Operating Statistics ({len(vessel_history)} data points):")
        print(f"  Speed Range: {min(speeds):.1f} - {max(speeds):.1f} knots (avg: {np.mean(speeds):.1f})")
        print(f"  Fuel Rate Range: {min(fuel_rates):.1f} - {max(fuel_rates):.1f} L/hr (avg: {np.mean(fuel_rates):.1f})")
        print(f"  Engine Load Range: {min(engine_loads):.0f} - {max(engine_loads):.0f}% (avg: {np.mean(engine_loads):.0f}%)")
        
        # Calculate efficiency metrics
        fuel_efficiency = [speeds[i] / fuel_rates[i] for i in range(len(speeds)) if fuel_rates[i] > 0]
        if fuel_efficiency:
            print(f"  Fuel Efficiency: {np.mean(fuel_efficiency):.2f} nm/L (avg)")
            print(f"  Best Efficiency: {max(fuel_efficiency):.2f} nm/L")
    
    # Environmental impact analysis
    env_history = predictor.environmental_history[test_vessel.vessel_id]
    if env_history:
        wind_speeds = [env.wind_speed for env in env_history]
        wave_heights = [env.wave_height for env in env_history]
        
        print(f"\nEnvironmental Conditions Encountered:")
        print(f"  Wind: {min(wind_speeds):.1f} - {max(wind_speeds):.1f} knots")
        print(f"  Waves: {min(wave_heights):.1f} - {max(wave_heights):.1f} meters")
        
        # Correlation analysis (simplified)
        if len(wind_speeds) == len(fuel_rates):
            wind_fuel_corr = np.corrcoef(wind_speeds, fuel_rates)[0, 1]
            wave_fuel_corr = np.corrcoef(wave_heights, fuel_rates)[0, 1]
            print(f"  Wind-Fuel Correlation: {wind_fuel_corr:.2f}")
            print(f"  Wave-Fuel Correlation: {wave_fuel_corr:.2f}")
    
    print(f"\nVessel Specifications:")
    print(f"  {test_vessel.vessel_name} - {test_vessel.vessel_type.value.title()}")
    print(f"  Length: {test_vessel.length_overall}m, Displacement: {test_vessel.displacement}t")
    print(f"  Engine: {main_engine.manufacturer} {main_engine.model} ({main_engine.max_power} kW)")
    print(f"  Fuel Capacity: {test_vessel.fuel_capacity} L")
    print(f"  Cruising Speed: {test_vessel.cruising_speed} knots")
    
    print("\n⛽ Fuel consumption prediction and optimization system demo completed!")
    print("Use predictions and recommendations to optimize fuel efficiency and reduce operating costs.")


if __name__ == "__main__":
    asyncio.run(main())