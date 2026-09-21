"""
ActiveLog Marine Advanced Suite - Sail Trim Optimization Using Wind Sensors

Advanced sail trim optimization system with real-time wind sensor analysis,
performance calculations, and AI-driven recommendations for optimal sailing configuration.
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
from scipy import optimize, interpolate
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


class SailType(Enum):
    MAINSAIL = "mainsail"
    JIB = "jib"
    GENOA = "genoa"
    SPINNAKER = "spinnaker"
    STAYSAIL = "staysail"
    MIZZEN = "mizzen"
    TOPSAIL = "topsail"
    CODE_ZERO = "code_zero"
    STORM_JIB = "storm_jib"
    TRYSAIL = "trysail"


class TrimParameter(Enum):
    MAIN_SHEET = "main_sheet"
    JIB_SHEET = "jib_sheet"
    HALYARD_TENSION = "halyard_tension"
    OUTHAUL = "outhaul"
    CUNNINGHAM = "cunningham"
    BACKSTAY = "backstay"
    FORESTAY = "forestay"
    BOOM_VANG = "boom_vang"
    TRAVELER = "traveler"
    POLE_POSITION = "pole_position"
    TWIST = "twist"
    DRAFT_POSITION = "draft_position"


class WindCondition(Enum):
    LIGHT = "light"         # 0-8 knots
    MODERATE = "moderate"   # 8-15 knots
    FRESH = "fresh"         # 15-25 knots
    STRONG = "strong"       # 25-35 knots
    GALE = "gale"          # 35+ knots


class SailConfiguration(Enum):
    LIGHT_AIR = "light_air"
    UPWIND = "upwind"
    REACHING = "reaching"
    RUNNING = "running"
    HEAVY_WEATHER = "heavy_weather"
    RACING = "racing"
    CRUISING = "cruising"


@dataclass
class WindSensorData:
    timestamp: datetime
    apparent_wind_speed: float      # knots
    apparent_wind_angle: float      # degrees from bow
    true_wind_speed: float          # knots
    true_wind_angle: float          # degrees from bow
    wind_direction: float           # degrees magnetic
    wind_gust_speed: float          # knots
    wind_shift_rate: float          # degrees per minute
    sensor_height: float            # meters above water
    sensor_location: str            # "masthead", "deck", "bow"
    quality_score: float            # 0-1 sensor reliability


@dataclass
class VesselMotion:
    timestamp: datetime
    boat_speed: float               # knots
    course_over_ground: float       # degrees
    speed_over_ground: float        # knots
    heel_angle: float               # degrees
    pitch_angle: float              # degrees
    roll_rate: float                # degrees per second
    acceleration: Tuple[float, float, float]  # x, y, z in m/s²
    heading_change_rate: float      # degrees per minute


@dataclass
class SailTrimState:
    timestamp: datetime
    sail_type: SailType
    sheet_position: float           # 0-100% (0=tight, 100=loose)
    halyard_tension: float          # 0-100%
    outhaul_position: float         # 0-100%
    cunningham_tension: float       # 0-100%
    backstay_tension: float         # 0-100%
    forestay_tension: float         # 0-100%
    boom_vang_tension: float        # 0-100%
    traveler_position: float        # -100 to +100 (port to starboard)
    twist_angle: float              # degrees
    draft_position: float           # 0-100% (0=forward, 100=aft)
    reef_points: int                # number of reef points set


@dataclass
class PerformanceMetrics:
    timestamp: datetime
    velocity_made_good: float       # VMG in knots
    speed_efficiency: float         # actual speed / polar speed (0-1)
    heel_efficiency: float          # performance factor based on heel angle
    motion_comfort: float           # comfort index (0-1)
    sail_power: float               # estimated power in sail plan
    pointing_angle: float           # degrees off wind for upwind sailing
    polar_performance: float        # percentage of theoretical max speed
    fuel_savings: float             # estimated fuel saved vs motoring


@dataclass
class TrimRecommendation:
    timestamp: datetime
    sail_type: SailType
    parameter: TrimParameter
    current_value: float
    recommended_value: float
    adjustment_magnitude: float     # how big the change should be (0-1)
    confidence: float               # AI model confidence (0-1)
    priority: int                   # 1=highest priority, 5=lowest
    reason: str                     # explanation of recommendation
    expected_improvement: float     # expected performance gain


@dataclass
class SailInventory:
    vessel_name: str
    sails: Dict[SailType, Dict[str, Any]]  # sail specifications
    rigging_config: Dict[str, Any]
    mast_height: float              # meters
    boom_length: float              # meters
    sail_areas: Dict[SailType, float]  # square meters
    working_sail_combinations: List[List[SailType]]


class WindSensorManager:
    """Manages multiple wind sensors and data fusion"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.sensors: Dict[str, Dict[str, Any]] = {}
        self.wind_history: List[WindSensorData] = []
        self.history_limit = 1000
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize wind sensor database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wind_sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                sensor_id TEXT,
                apparent_wind_speed REAL,
                apparent_wind_angle REAL,
                true_wind_speed REAL,
                true_wind_angle REAL,
                wind_direction REAL,
                wind_gust_speed REAL,
                wind_shift_rate REAL,
                sensor_height REAL,
                sensor_location TEXT,
                quality_score REAL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_wind_sensor_time 
            ON wind_sensor_data (timestamp, sensor_id)
        """)
        
        conn.commit()
        conn.close()
    
    def register_sensor(self, sensor_id: str, sensor_config: Dict[str, Any]):
        """Register a wind sensor"""
        self.sensors[sensor_id] = sensor_config
        print(f"Wind sensor registered: {sensor_id} at {sensor_config.get('location', 'unknown')}")
    
    async def process_wind_data(self, sensor_id: str, raw_data: Dict[str, Any]) -> WindSensorData:
        """Process raw wind sensor data"""
        if sensor_id not in self.sensors:
            raise ValueError(f"Unknown sensor: {sensor_id}")
        
        sensor_config = self.sensors[sensor_id]
        
        # Calculate true wind from apparent wind (requires vessel motion data)
        boat_speed = raw_data.get('boat_speed', 0.0)
        boat_heading = raw_data.get('boat_heading', 0.0)
        
        apparent_wind_speed = raw_data.get('apparent_wind_speed', 0.0)
        apparent_wind_angle = raw_data.get('apparent_wind_angle', 0.0)
        
        true_wind_speed, true_wind_angle = self._calculate_true_wind(
            apparent_wind_speed, apparent_wind_angle, boat_speed, boat_heading
        )
        
        # Calculate wind shift rate
        wind_shift_rate = 0.0
        if len(self.wind_history) > 0:
            last_reading = self.wind_history[-1]
            time_diff = (datetime.utcnow() - last_reading.timestamp).total_seconds() / 60  # minutes
            if time_diff > 0:
                angle_diff = true_wind_angle - last_reading.true_wind_angle
                # Handle angle wrap-around
                if angle_diff > 180:
                    angle_diff -= 360
                elif angle_diff < -180:
                    angle_diff += 360
                wind_shift_rate = angle_diff / time_diff
        
        # Calculate quality score based on sensor characteristics and conditions
        quality_score = self._calculate_sensor_quality(sensor_config, raw_data)
        
        wind_data = WindSensorData(
            timestamp=datetime.utcnow(),
            apparent_wind_speed=apparent_wind_speed,
            apparent_wind_angle=apparent_wind_angle,
            true_wind_speed=true_wind_speed,
            true_wind_angle=true_wind_angle,
            wind_direction=raw_data.get('wind_direction', 0.0),
            wind_gust_speed=raw_data.get('wind_gust_speed', apparent_wind_speed),
            wind_shift_rate=wind_shift_rate,
            sensor_height=sensor_config.get('height', 10.0),
            sensor_location=sensor_config.get('location', 'masthead'),
            quality_score=quality_score
        )
        
        # Store in history
        self.wind_history.append(wind_data)
        if len(self.wind_history) > self.history_limit:
            self.wind_history = self.wind_history[-self.history_limit:]
        
        # Store in database
        await self._store_wind_data(sensor_id, wind_data)
        
        return wind_data
    
    def _calculate_true_wind(self, apparent_speed: float, apparent_angle: float,
                           boat_speed: float, boat_heading: float) -> Tuple[float, float]:
        """Calculate true wind from apparent wind and vessel motion"""
        # Convert apparent wind to components
        awa_rad = math.radians(apparent_angle)
        aws_x = apparent_speed * math.sin(awa_rad)  # Cross-boat component
        aws_y = apparent_speed * math.cos(awa_rad)  # Fore-aft component
        
        # Remove boat speed vector
        tws_x = aws_x
        tws_y = aws_y - boat_speed
        
        # Calculate true wind speed and angle
        true_wind_speed = math.sqrt(tws_x**2 + tws_y**2)
        
        if true_wind_speed > 0:
            true_wind_angle = math.degrees(math.atan2(tws_x, tws_y))
            if true_wind_angle < 0:
                true_wind_angle += 360
        else:
            true_wind_angle = 0
        
        return true_wind_speed, true_wind_angle
    
    def _calculate_sensor_quality(self, sensor_config: Dict[str, Any], 
                                raw_data: Dict[str, Any]) -> float:
        """Calculate sensor data quality score"""
        quality = 1.0
        
        # Reduce quality for low wind speeds (sensor less accurate)
        wind_speed = raw_data.get('apparent_wind_speed', 0.0)
        if wind_speed < 3.0:
            quality *= 0.7
        elif wind_speed < 1.0:
            quality *= 0.4
        
        # Sensor-specific factors
        sensor_type = sensor_config.get('type', 'unknown')
        if sensor_type == 'ultrasonic':
            quality *= 1.0  # High quality
        elif sensor_type == 'mechanical':
            quality *= 0.8  # Good quality but has inertia
        elif sensor_type == 'electronic':
            quality *= 0.9  # Very good quality
        
        # Environmental factors
        if raw_data.get('heel_angle', 0) > 20:
            quality *= 0.9  # Heel affects sensor accuracy
        
        if raw_data.get('boat_speed', 0) < 2:
            quality *= 0.8  # Low boat speed makes calculations less accurate
        
        return max(0.1, quality)  # Minimum quality threshold
    
    async def get_fused_wind_data(self) -> Optional[WindSensorData]:
        """Get sensor-fused wind data from multiple sensors"""
        if not self.wind_history:
            return None
        
        # For simplicity, return the most recent high-quality reading
        # In production, implement proper sensor fusion algorithms
        recent_data = [d for d in self.wind_history[-10:] if d.quality_score > 0.7]
        
        if not recent_data:
            return self.wind_history[-1]  # Return last reading even if low quality
        
        # Return highest quality recent reading
        return max(recent_data, key=lambda d: d.quality_score)
    
    async def _store_wind_data(self, sensor_id: str, wind_data: WindSensorData):
        """Store wind data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO wind_sensor_data 
            (timestamp, sensor_id, apparent_wind_speed, apparent_wind_angle,
             true_wind_speed, true_wind_angle, wind_direction, wind_gust_speed,
             wind_shift_rate, sensor_height, sensor_location, quality_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            wind_data.timestamp, sensor_id, wind_data.apparent_wind_speed,
            wind_data.apparent_wind_angle, wind_data.true_wind_speed,
            wind_data.true_wind_angle, wind_data.wind_direction,
            wind_data.wind_gust_speed, wind_data.wind_shift_rate,
            wind_data.sensor_height, wind_data.sensor_location,
            wind_data.quality_score
        ))
        
        conn.commit()
        conn.close()


class SailTrimOptimizer:
    """AI-powered sail trim optimization system"""
    
    def __init__(self, db_path: str, sail_inventory: SailInventory):
        self.db_path = db_path
        self.sail_inventory = sail_inventory
        self.wind_sensor_manager = WindSensorManager(db_path)
        
        # Machine learning models
        self.performance_model = None
        self.trim_model = None
        self.scaler = StandardScaler()
        
        # Sailing performance data
        self.trim_history: List[SailTrimState] = []
        self.performance_history: List[PerformanceMetrics] = []
        self.motion_history: List[VesselMotion] = []
        
        # Polar performance data (simplified - in production use detailed polars)
        self.vessel_polars = self._initialize_polar_data()
        
        self._initialize_database()
        self._initialize_models()
    
    def _initialize_database(self):
        """Initialize sail trim database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sail trim states table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sail_trim_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                sail_type TEXT,
                sheet_position REAL,
                halyard_tension REAL,
                outhaul_position REAL,
                cunningham_tension REAL,
                backstay_tension REAL,
                forestay_tension REAL,
                boom_vang_tension REAL,
                traveler_position REAL,
                twist_angle REAL,
                draft_position REAL,
                reef_points INTEGER
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                velocity_made_good REAL,
                speed_efficiency REAL,
                heel_efficiency REAL,
                motion_comfort REAL,
                sail_power REAL,
                pointing_angle REAL,
                polar_performance REAL,
                fuel_savings REAL
            )
        """)
        
        # Trim recommendations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trim_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                sail_type TEXT,
                parameter TEXT,
                current_value REAL,
                recommended_value REAL,
                adjustment_magnitude REAL,
                confidence REAL,
                priority INTEGER,
                reason TEXT,
                expected_improvement REAL,
                implemented BOOLEAN DEFAULT FALSE
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _initialize_models(self):
        """Initialize machine learning models for performance prediction"""
        # Random Forest for performance prediction
        self.performance_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            random_state=42
        )
        
        # Generate synthetic training data for demonstration
        self._train_with_synthetic_data()
    
    def _train_with_synthetic_data(self):
        """Train models with synthetic sailing data"""
        n_samples = 5000
        
        # Features: wind speed, wind angle, heel, trim parameters
        features = []
        targets = []
        
        for _ in range(n_samples):
            # Wind conditions
            tws = np.random.exponential(12) + 2  # True wind speed 2-40 knots
            twa = np.random.uniform(30, 180)     # True wind angle
            
            # Vessel state
            heel = np.random.uniform(0, 25)      # Heel angle
            boat_speed = np.random.uniform(2, 12) # Boat speed
            
            # Trim parameters (normalized 0-1)
            main_sheet = np.random.uniform(0, 1)
            jib_sheet = np.random.uniform(0, 1)
            backstay = np.random.uniform(0, 1)
            outhaul = np.random.uniform(0, 1)
            
            # Calculate synthetic performance based on sailing principles
            # Upwind performance
            if twa < 60:
                vmg = boat_speed * math.cos(math.radians(twa)) * (1 - abs(main_sheet - 0.3) * 0.3)
            # Reaching
            elif twa < 120:
                vmg = boat_speed * 0.9 * (1 - abs(jib_sheet - 0.5) * 0.2)
            # Downwind
            else:
                vmg = boat_speed * math.cos(math.radians(180 - twa)) * (1 - abs(main_sheet - 0.7) * 0.2)
            
            # Add heel penalty
            heel_penalty = 1 - min(heel / 30, 0.3)
            vmg *= heel_penalty
            
            # Add wind strength factor
            wind_factor = min(1.0, tws / 15)
            vmg *= wind_factor
            
            features.append([tws, twa, heel, boat_speed, main_sheet, jib_sheet, backstay, outhaul])
            targets.append(max(0, vmg))
        
        # Train model
        X = np.array(features)
        y = np.array(targets)
        
        X_scaled = self.scaler.fit_transform(X)
        self.performance_model.fit(X_scaled, y)
    
    def _initialize_polar_data(self) -> Dict[str, Any]:
        """Initialize vessel polar performance data"""
        # Simplified polar data - in production use detailed polar tables
        return {
            'max_speed': 12.0,  # knots
            'optimal_twa_upwind': 45.0,  # degrees
            'optimal_twa_reaching': 90.0,
            'optimal_twa_downwind': 150.0,
            'pointing_ability': 35.0,  # minimum true wind angle
            'vmg_targets': {
                6: {'upwind': 4.5, 'downwind': 6.0},    # 6 knots true wind
                10: {'upwind': 6.0, 'downwind': 8.5},   # 10 knots true wind
                15: {'upwind': 7.5, 'downwind': 10.0},  # 15 knots true wind
                20: {'upwind': 8.0, 'downwind': 11.0},  # 20 knots true wind
            }
        }
    
    async def update_sail_trim(self, trim_state: SailTrimState):
        """Update current sail trim state"""
        self.trim_history.append(trim_state)
        if len(self.trim_history) > 500:
            self.trim_history = self.trim_history[-500:]
        
        await self._store_trim_state(trim_state)
    
    async def update_vessel_motion(self, motion: VesselMotion):
        """Update vessel motion data"""
        self.motion_history.append(motion)
        if len(self.motion_history) > 200:
            self.motion_history = self.motion_history[-200:]
    
    async def calculate_performance_metrics(self, wind_data: WindSensorData, 
                                          motion: VesselMotion) -> PerformanceMetrics:
        """Calculate current sailing performance metrics"""
        
        # Calculate VMG (Velocity Made Good)
        if wind_data.true_wind_angle < 90:  # Upwind
            vmg = motion.boat_speed * math.cos(math.radians(wind_data.true_wind_angle))
        else:  # Downwind
            vmg = motion.boat_speed * math.cos(math.radians(180 - wind_data.true_wind_angle))
        
        # Speed efficiency compared to polar
        polar_speed = self._get_polar_speed(wind_data.true_wind_speed, wind_data.true_wind_angle)
        speed_efficiency = motion.boat_speed / max(polar_speed, 0.1)
        
        # Heel efficiency (excessive heel reduces performance)
        heel_efficiency = 1.0 - min(abs(motion.heel_angle) / 30, 0.4)
        
        # Motion comfort index
        motion_comfort = self._calculate_motion_comfort(motion)
        
        # Sail power estimation
        sail_power = self._estimate_sail_power(wind_data)
        
        # Pointing angle for upwind sailing
        pointing_angle = wind_data.true_wind_angle if wind_data.true_wind_angle < 90 else 0
        
        # Polar performance percentage
        target_vmg = self._get_target_vmg(wind_data.true_wind_speed, wind_data.true_wind_angle)
        polar_performance = (vmg / max(target_vmg, 0.1)) * 100 if target_vmg > 0 else 0
        
        # Fuel savings (estimated savings vs motoring)
        fuel_savings = self._estimate_fuel_savings(motion.boat_speed, wind_data.true_wind_speed)
        
        performance = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            velocity_made_good=vmg,
            speed_efficiency=speed_efficiency,
            heel_efficiency=heel_efficiency,
            motion_comfort=motion_comfort,
            sail_power=sail_power,
            pointing_angle=pointing_angle,
            polar_performance=polar_performance,
            fuel_savings=fuel_savings
        )
        
        self.performance_history.append(performance)
        if len(self.performance_history) > 500:
            self.performance_history = self.performance_history[-500:]
        
        await self._store_performance_metrics(performance)
        
        return performance
    
    async def generate_trim_recommendations(self, wind_data: WindSensorData, 
                                          motion: VesselMotion) -> List[TrimRecommendation]:
        """Generate AI-powered sail trim recommendations"""
        recommendations = []
        
        if not self.trim_history:
            return recommendations
        
        current_trim = self.trim_history[-1]
        wind_condition = self._classify_wind_condition(wind_data.true_wind_speed)
        sail_config = self._determine_sail_configuration(wind_data, motion)
        
        # Generate recommendations for each sail and trim parameter
        for sail_type in [SailType.MAINSAIL, SailType.JIB]:
            if sail_type in self.sail_inventory.sails:
                sail_recommendations = await self._generate_sail_recommendations(
                    sail_type, current_trim, wind_data, motion, sail_config
                )
                recommendations.extend(sail_recommendations)
        
        # Sort by priority and expected improvement
        recommendations.sort(key=lambda r: (r.priority, -r.expected_improvement))
        
        # Store recommendations
        for rec in recommendations:
            await self._store_recommendation(rec)
        
        return recommendations[:5]  # Return top 5 recommendations
    
    async def _generate_sail_recommendations(self, sail_type: SailType, current_trim: SailTrimState,
                                           wind_data: WindSensorData, motion: VesselMotion,
                                           sail_config: SailConfiguration) -> List[TrimRecommendation]:
        """Generate recommendations for specific sail"""
        recommendations = []
        
        # Main sail recommendations
        if sail_type == SailType.MAINSAIL:
            # Sheet position
            optimal_sheet = self._calculate_optimal_main_sheet(wind_data, motion)
            if abs(current_trim.sheet_position - optimal_sheet) > 5:
                rec = TrimRecommendation(
                    timestamp=datetime.utcnow(),
                    sail_type=sail_type,
                    parameter=TrimParameter.MAIN_SHEET,
                    current_value=current_trim.sheet_position,
                    recommended_value=optimal_sheet,
                    adjustment_magnitude=abs(current_trim.sheet_position - optimal_sheet) / 100,
                    confidence=0.8,
                    priority=1 if abs(current_trim.sheet_position - optimal_sheet) > 15 else 2,
                    reason=f"Wind angle {wind_data.true_wind_angle:.0f}° requires different sheet tension",
                    expected_improvement=self._estimate_sheet_improvement(current_trim.sheet_position, optimal_sheet)
                )
                recommendations.append(rec)
            
            # Backstay tension
            optimal_backstay = self._calculate_optimal_backstay(wind_data)
            if abs(current_trim.backstay_tension - optimal_backstay) > 10:
                rec = TrimRecommendation(
                    timestamp=datetime.utcnow(),
                    sail_type=sail_type,
                    parameter=TrimParameter.BACKSTAY,
                    current_value=current_trim.backstay_tension,
                    recommended_value=optimal_backstay,
                    adjustment_magnitude=abs(current_trim.backstay_tension - optimal_backstay) / 100,
                    confidence=0.7,
                    priority=2,
                    reason=f"Wind speed {wind_data.true_wind_speed:.1f} kts requires backstay adjustment",
                    expected_improvement=0.05
                )
                recommendations.append(rec)
            
            # Outhaul position
            optimal_outhaul = self._calculate_optimal_outhaul(wind_data, sail_config)
            if abs(current_trim.outhaul_position - optimal_outhaul) > 8:
                rec = TrimRecommendation(
                    timestamp=datetime.utcnow(),
                    sail_type=sail_type,
                    parameter=TrimParameter.OUTHAUL,
                    current_value=current_trim.outhaul_position,
                    recommended_value=optimal_outhaul,
                    adjustment_magnitude=abs(current_trim.outhaul_position - optimal_outhaul) / 100,
                    confidence=0.6,
                    priority=3,
                    reason="Outhaul adjustment for sail shape optimization",
                    expected_improvement=0.03
                )
                recommendations.append(rec)
        
        # Jib recommendations
        elif sail_type == SailType.JIB:
            # Sheet position
            optimal_jib_sheet = self._calculate_optimal_jib_sheet(wind_data, motion)
            if abs(current_trim.sheet_position - optimal_jib_sheet) > 5:
                rec = TrimRecommendation(
                    timestamp=datetime.utcnow(),
                    sail_type=sail_type,
                    parameter=TrimParameter.JIB_SHEET,
                    current_value=current_trim.sheet_position,
                    recommended_value=optimal_jib_sheet,
                    adjustment_magnitude=abs(current_trim.sheet_position - optimal_jib_sheet) / 100,
                    confidence=0.8,
                    priority=1,
                    reason=f"Jib trim for wind angle {wind_data.true_wind_angle:.0f}°",
                    expected_improvement=self._estimate_jib_improvement(current_trim.sheet_position, optimal_jib_sheet)
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _calculate_optimal_main_sheet(self, wind_data: WindSensorData, motion: VesselMotion) -> float:
        """Calculate optimal mainsail sheet position"""
        twa = wind_data.true_wind_angle
        tws = wind_data.true_wind_speed
        
        if twa < 60:  # Upwind
            # Tight sheet for upwind work, adjusted for wind strength
            base_position = 15 + (tws - 10) * 0.5  # Tighter in more wind
            # Adjust for heel - ease if heeling too much
            if motion.heel_angle > 20:
                base_position += 5
        elif twa < 120:  # Reaching
            # Moderate sheet tension for reaching
            base_position = 40 + (twa - 90) * 0.3
        else:  # Running
            # Eased sheet for downwind
            base_position = 70 + (180 - twa) * 0.2
        
        return max(0, min(100, base_position))
    
    def _calculate_optimal_jib_sheet(self, wind_data: WindSensorData, motion: VesselMotion) -> float:
        """Calculate optimal jib sheet position"""
        twa = wind_data.true_wind_angle
        tws = wind_data.true_wind_speed
        
        if twa < 60:  # Upwind
            base_position = 20 + (tws - 10) * 0.3
            if motion.heel_angle > 15:
                base_position += 3  # Ease slightly if heeling
        elif twa < 100:  # Close reaching
            base_position = 35 + (twa - 60) * 0.4
        else:  # Broad reach and run
            base_position = 60  # Generally eased for reaching/running
        
        return max(0, min(100, base_position))
    
    def _calculate_optimal_backstay(self, wind_data: WindSensorData) -> float:
        """Calculate optimal backstay tension"""
        tws = wind_data.true_wind_speed
        
        if tws < 8:
            return 20  # Light tension in light air
        elif tws < 15:
            return 40 + (tws - 8) * 3  # Gradual increase
        elif tws < 25:
            return 60 + (tws - 15) * 2  # More tension in fresh wind
        else:
            return 80  # High tension in strong winds
    
    def _calculate_optimal_outhaul(self, wind_data: WindSensorData, 
                                 sail_config: SailConfiguration) -> float:
        """Calculate optimal outhaul position"""
        tws = wind_data.true_wind_speed
        twa = wind_data.true_wind_angle
        
        if sail_config == SailConfiguration.LIGHT_AIR:
            return 30  # Loose for power in light air
        elif twa < 80:  # Upwind
            return 60 + min(tws - 10, 20)  # Tighter for flatter sail upwind
        else:  # Reaching/running
            return 40  # Moderate tension for power
    
    def _get_polar_speed(self, tws: float, twa: float) -> float:
        """Get polar speed for given wind conditions"""
        # Simplified polar calculation
        if twa < 60:  # Upwind
            return min(self.vessel_polars['max_speed'], tws * 0.4)
        elif twa < 120:  # Reaching
            return min(self.vessel_polars['max_speed'], tws * 0.6)
        else:  # Running
            return min(self.vessel_polars['max_speed'], tws * 0.5)
    
    def _get_target_vmg(self, tws: float, twa: float) -> float:
        """Get target VMG for conditions"""
        # Find closest wind speed in polar data
        wind_speeds = sorted(self.vessel_polars['vmg_targets'].keys())
        closest_wind = min(wind_speeds, key=lambda x: abs(x - tws))
        
        targets = self.vessel_polars['vmg_targets'][closest_wind]
        
        if twa < 90:
            return targets['upwind']
        else:
            return targets['downwind']
    
    def _classify_wind_condition(self, tws: float) -> WindCondition:
        """Classify wind conditions"""
        if tws < 8:
            return WindCondition.LIGHT
        elif tws < 15:
            return WindCondition.MODERATE
        elif tws < 25:
            return WindCondition.FRESH
        elif tws < 35:
            return WindCondition.STRONG
        else:
            return WindCondition.GALE
    
    def _determine_sail_configuration(self, wind_data: WindSensorData, 
                                    motion: VesselMotion) -> SailConfiguration:
        """Determine optimal sail configuration"""
        tws = wind_data.true_wind_speed
        twa = wind_data.true_wind_angle
        
        if tws < 5:
            return SailConfiguration.LIGHT_AIR
        elif tws > 30:
            return SailConfiguration.HEAVY_WEATHER
        elif twa < 70:
            return SailConfiguration.UPWIND
        elif twa < 140:
            return SailConfiguration.REACHING
        else:
            return SailConfiguration.RUNNING
    
    def _calculate_motion_comfort(self, motion: VesselMotion) -> float:
        """Calculate motion comfort index"""
        comfort = 1.0
        
        # Heel comfort
        if motion.heel_angle > 15:
            comfort -= min((motion.heel_angle - 15) / 30, 0.4)
        
        # Pitch comfort
        if motion.pitch_angle > 5:
            comfort -= min((motion.pitch_angle - 5) / 15, 0.3)
        
        # Roll rate comfort
        if motion.roll_rate > 2:
            comfort -= min((motion.roll_rate - 2) / 8, 0.3)
        
        return max(0, comfort)
    
    def _estimate_sail_power(self, wind_data: WindSensorData) -> float:
        """Estimate power generated by sail plan"""
        # Simplified calculation based on wind speed and angle
        tws = wind_data.true_wind_speed
        twa = wind_data.true_wind_angle
        
        # Power varies with square of wind speed
        base_power = tws ** 2
        
        # Efficiency varies with wind angle
        if twa < 60:
            efficiency = 0.6  # Lower efficiency upwind
        elif twa < 120:
            efficiency = 0.9  # High efficiency reaching
        else:
            efficiency = 0.7  # Moderate efficiency running
        
        return base_power * efficiency
    
    def _estimate_fuel_savings(self, boat_speed: float, wind_speed: float) -> float:
        """Estimate fuel savings compared to motoring"""
        if boat_speed < 2:
            return 0
        
        # Estimate fuel consumption for equivalent motoring speed
        motor_fuel_rate = boat_speed * 0.3  # Rough estimate: 0.3 gal/hr per knot
        
        # Consider wind assistance
        wind_assist_factor = min(wind_speed / 15, 1.0)
        
        return motor_fuel_rate * wind_assist_factor
    
    def _estimate_sheet_improvement(self, current: float, optimal: float) -> float:
        """Estimate performance improvement from sheet adjustment"""
        adjustment = abs(current - optimal) / 100
        return min(adjustment * 0.1, 0.05)  # Up to 5% improvement
    
    def _estimate_jib_improvement(self, current: float, optimal: float) -> float:
        """Estimate performance improvement from jib adjustment"""
        adjustment = abs(current - optimal) / 100
        return min(adjustment * 0.08, 0.04)  # Up to 4% improvement
    
    async def _store_trim_state(self, trim_state: SailTrimState):
        """Store sail trim state in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sail_trim_states 
            (timestamp, sail_type, sheet_position, halyard_tension, outhaul_position,
             cunningham_tension, backstay_tension, forestay_tension, boom_vang_tension,
             traveler_position, twist_angle, draft_position, reef_points)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trim_state.timestamp, trim_state.sail_type.value, trim_state.sheet_position,
            trim_state.halyard_tension, trim_state.outhaul_position, trim_state.cunningham_tension,
            trim_state.backstay_tension, trim_state.forestay_tension, trim_state.boom_vang_tension,
            trim_state.traveler_position, trim_state.twist_angle, trim_state.draft_position,
            trim_state.reef_points
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_performance_metrics(self, performance: PerformanceMetrics):
        """Store performance metrics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO performance_metrics 
            (timestamp, velocity_made_good, speed_efficiency, heel_efficiency,
             motion_comfort, sail_power, pointing_angle, polar_performance, fuel_savings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            performance.timestamp, performance.velocity_made_good, performance.speed_efficiency,
            performance.heel_efficiency, performance.motion_comfort, performance.sail_power,
            performance.pointing_angle, performance.polar_performance, performance.fuel_savings
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_recommendation(self, recommendation: TrimRecommendation):
        """Store trim recommendation in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO trim_recommendations 
            (timestamp, sail_type, parameter, current_value, recommended_value,
             adjustment_magnitude, confidence, priority, reason, expected_improvement)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recommendation.timestamp, recommendation.sail_type.value, recommendation.parameter.value,
            recommendation.current_value, recommendation.recommended_value, recommendation.adjustment_magnitude,
            recommendation.confidence, recommendation.priority, recommendation.reason,
            recommendation.expected_improvement
        ))
        
        conn.commit()
        conn.close()


async def main():
    """Demonstration of sail trim optimization system"""
    
    # Create sail inventory
    sail_inventory = SailInventory(
        vessel_name="SV WINDSEEKER",
        sails={
            SailType.MAINSAIL: {"area": 45.0, "material": "dacron", "condition": "good"},
            SailType.JIB: {"area": 35.0, "material": "dacron", "condition": "excellent"},
            SailType.GENOA: {"area": 55.0, "material": "laminate", "condition": "good"},
            SailType.SPINNAKER: {"area": 85.0, "material": "nylon", "condition": "fair"}
        },
        rigging_config={
            "fractional_rig": True,
            "swept_spreaders": True,
            "adjustable_backstay": True
        },
        mast_height=16.5,  # meters
        boom_length=4.2,   # meters
        sail_areas={
            SailType.MAINSAIL: 45.0,
            SailType.JIB: 35.0,
            SailType.GENOA: 55.0,
            SailType.SPINNAKER: 85.0
        },
        working_sail_combinations=[
            [SailType.MAINSAIL, SailType.JIB],
            [SailType.MAINSAIL, SailType.GENOA],
            [SailType.MAINSAIL, SailType.SPINNAKER]
        ]
    )
    
    # Initialize sail trim optimizer
    optimizer = SailTrimOptimizer("sail_trim.db", sail_inventory)
    
    print("ActiveLog Marine Advanced - Sail Trim Optimization Demo")
    print("=" * 58)
    
    # Register wind sensors
    optimizer.wind_sensor_manager.register_sensor("masthead", {
        "type": "ultrasonic",
        "location": "masthead",
        "height": 16.0,
        "accuracy": 0.1
    })
    
    optimizer.wind_sensor_manager.register_sensor("deck", {
        "type": "mechanical",
        "location": "deck",
        "height": 2.0,
        "accuracy": 0.5
    })
    
    print("Wind sensors registered: masthead ultrasonic, deck mechanical")
    
    # Simulate sailing conditions
    print("\n" + "="*50)
    print("SIMULATING SAILING CONDITIONS")
    print("="*50)
    
    for scenario in range(5):
        print(f"\n--- Scenario {scenario + 1} ---")
        
        # Generate realistic wind conditions
        base_tws = 8 + scenario * 3  # Increasing wind
        base_twa = 45 + scenario * 30  # Varying angles
        
        # Simulate wind sensor data
        wind_raw_data = {
            "apparent_wind_speed": base_tws + np.random.normal(0, 1),
            "apparent_wind_angle": base_twa + np.random.normal(0, 5),
            "wind_direction": 225 + np.random.normal(0, 10),
            "wind_gust_speed": base_tws * 1.3,
            "boat_speed": 6 + scenario,
            "boat_heading": 180
        }
        
        # Process wind data
        wind_data = await optimizer.wind_sensor_manager.process_wind_data("masthead", wind_raw_data)
        
        # Simulate vessel motion
        vessel_motion = VesselMotion(
            timestamp=datetime.utcnow(),
            boat_speed=6 + scenario,
            course_over_ground=180 + np.random.normal(0, 5),
            speed_over_ground=6 + scenario + np.random.normal(0, 0.5),
            heel_angle=max(0, base_tws - 8) + np.random.normal(0, 2),
            pitch_angle=np.random.normal(0, 2),
            roll_rate=np.random.normal(0, 1),
            acceleration=(np.random.normal(0, 0.5), np.random.normal(0, 0.3), np.random.normal(0, 0.2)),
            heading_change_rate=np.random.normal(0, 1)
        )
        
        # Current sail trim state
        trim_state = SailTrimState(
            timestamp=datetime.utcnow(),
            sail_type=SailType.MAINSAIL,
            sheet_position=30 + np.random.normal(0, 10),
            halyard_tension=80 + np.random.normal(0, 5),
            outhaul_position=50 + np.random.normal(0, 10),
            cunningham_tension=20 + np.random.normal(0, 5),
            backstay_tension=40 + scenario * 10,
            forestay_tension=70,
            boom_vang_tension=30,
            traveler_position=0,
            twist_angle=10 + np.random.normal(0, 3),
            draft_position=45 + np.random.normal(0, 5),
            reef_points=0
        )
        
        # Update system with current state
        await optimizer.update_sail_trim(trim_state)
        await optimizer.update_vessel_motion(vessel_motion)
        
        # Calculate performance metrics
        performance = await optimizer.calculate_performance_metrics(wind_data, vessel_motion)
        
        # Generate recommendations
        recommendations = await optimizer.generate_trim_recommendations(wind_data, vessel_motion)
        
        # Display results
        print(f"Wind: {wind_data.true_wind_speed:.1f} kts @ {wind_data.true_wind_angle:.0f}° (apparent: {wind_data.apparent_wind_speed:.1f} kts)")
        print(f"Boat: {vessel_motion.boat_speed:.1f} kts, heel {vessel_motion.heel_angle:.1f}°")
        print(f"Performance: VMG {performance.velocity_made_good:.1f} kts, efficiency {performance.speed_efficiency:.1%}")
        print(f"Polar performance: {performance.polar_performance:.0f}%, comfort: {performance.motion_comfort:.1%}")
        
        if recommendations:
            print(f"Trim Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                priority_symbol = "🔴" if rec.priority == 1 else "🟡" if rec.priority == 2 else "🟢"
                print(f"  {priority_symbol} {i}. {rec.sail_type.value.title()} {rec.parameter.value.replace('_', ' ').title()}")
                print(f"     Current: {rec.current_value:.0f}%, Recommended: {rec.recommended_value:.0f}%")
                print(f"     Reason: {rec.reason}")
                print(f"     Expected improvement: {rec.expected_improvement:.1%}")
        else:
            print("No trim adjustments recommended - current setup is optimal")
        
        # Show fuel savings
        if performance.fuel_savings > 0:
            print(f"Estimated fuel savings: {performance.fuel_savings:.1f} gal/hr compared to motoring")
    
    print("\n" + "="*50)
    print("SAIL TRIM OPTIMIZATION SUMMARY")
    print("="*50)
    
    # Show overall performance trends
    if optimizer.performance_history:
        avg_vmg = np.mean([p.velocity_made_good for p in optimizer.performance_history])
        avg_efficiency = np.mean([p.speed_efficiency for p in optimizer.performance_history])
        avg_comfort = np.mean([p.motion_comfort for p in optimizer.performance_history])
        total_fuel_savings = sum([p.fuel_savings for p in optimizer.performance_history])
        
        print(f"Session Statistics:")
        print(f"- Average VMG: {avg_vmg:.1f} knots")
        print(f"- Average Speed Efficiency: {avg_efficiency:.1%}")
        print(f"- Average Motion Comfort: {avg_comfort:.1%}")
        print(f"- Total Estimated Fuel Savings: {total_fuel_savings:.1f} gallons")
        print(f"- Performance Samples: {len(optimizer.performance_history)}")
        print(f"- Trim Adjustments Tracked: {len(optimizer.trim_history)}")
    
    # Wind sensor summary
    print(f"\nWind Sensor Performance:")
    if optimizer.wind_sensor_manager.wind_history:
        avg_quality = np.mean([w.quality_score for w in optimizer.wind_sensor_manager.wind_history])
        print(f"- Average Data Quality: {avg_quality:.1%}")
        print(f"- Wind Samples: {len(optimizer.wind_sensor_manager.wind_history)}")
        
        # Show wind range encountered
        wind_speeds = [w.true_wind_speed for w in optimizer.wind_sensor_manager.wind_history]
        wind_angles = [w.true_wind_angle for w in optimizer.wind_sensor_manager.wind_history]
        print(f"- Wind Speed Range: {min(wind_speeds):.1f} - {max(wind_speeds):.1f} knots")
        print(f"- Wind Angle Range: {min(wind_angles):.0f}° - {max(wind_angles):.0f}°")
    
    print(f"\nSail Inventory:")
    print(f"- Vessel: {sail_inventory.vessel_name}")
    print(f"- Total Sails: {len(sail_inventory.sails)}")
    print(f"- Mast Height: {sail_inventory.mast_height}m")
    print(f"- Working Combinations: {len(sail_inventory.working_sail_combinations)}")
    
    print("\n🏆 Sail trim optimization session completed successfully!")
    print("Use recommendations to optimize sailing performance and comfort.")


if __name__ == "__main__":
    asyncio.run(main())