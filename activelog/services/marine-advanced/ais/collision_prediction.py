"""
ActiveLog Marine Advanced Suite - AIS Collision Prediction System

Advanced collision risk assessment using machine learning, real-time AIS data processing,
CPA/TCPA calculations, and intelligent alert management for maritime safety.
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
from scipy import optimize
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
from geopy.distance import geodesic
import warnings
warnings.filterwarnings('ignore')


class VesselType(Enum):
    UNKNOWN = 0
    FISHING = 30
    TOWING = 31
    DREDGING = 33
    DIVING_OPS = 34
    MILITARY = 35
    SAILING = 36
    PLEASURE_CRAFT = 37
    HIGH_SPEED_CRAFT = 40
    PILOT = 50
    SEARCH_RESCUE = 51
    TUG = 52
    PORT_TENDER = 53
    ANTI_POLLUTION = 54
    LAW_ENFORCEMENT = 55
    MEDICAL = 58
    PASSENGER = 60
    CARGO = 70
    TANKER = 80
    OTHER = 90


class NavigationStatus(Enum):
    UNDER_WAY_USING_ENGINE = 0
    AT_ANCHOR = 1
    NOT_UNDER_COMMAND = 2
    RESTRICTED_MANOEUVRABILITY = 3
    CONSTRAINED_BY_DRAUGHT = 4
    MOORED = 5
    AGROUND = 6
    FISHING = 7
    UNDER_WAY_SAILING = 8
    RESERVED_HSC = 9
    RESERVED_WIG = 10
    POWER_DRIVEN_VESSEL_TOWING_ASTERN = 11
    POWER_DRIVEN_VESSEL_PUSHING_AHEAD = 12
    RESERVED = 13
    AIS_SART = 14
    DEFAULT = 15


class RiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    IMMINENT = "imminent"


class AlertType(Enum):
    CPA_VIOLATION = "cpa_violation"
    TCPA_WARNING = "tcpa_warning"
    CROSSING_SITUATION = "crossing_situation"
    OVERTAKING = "overtaking"
    HEAD_ON = "head_on"
    FISHING_VESSEL_PRIORITY = "fishing_priority"
    RESTRICTED_MANEUVERABILITY = "restricted_maneuverability"
    ANCHOR_DRAG_RISK = "anchor_drag_risk"


@dataclass
class VesselPosition:
    mmsi: str
    timestamp: datetime
    lat: float
    lon: float
    course_over_ground: float  # degrees
    speed_over_ground: float   # knots
    heading: float             # degrees
    rate_of_turn: Optional[float]  # degrees per minute
    position_accuracy: bool
    raim: bool
    navigation_status: NavigationStatus


@dataclass
class VesselStatic:
    mmsi: str
    vessel_name: str
    call_sign: str
    imo: Optional[str]
    vessel_type: VesselType
    dimensions: Tuple[int, int, int, int]  # to_bow, to_stern, to_port, to_starboard
    draught: Optional[float]  # meters
    destination: str
    eta: Optional[datetime]
    ais_version: int


@dataclass
class VesselTrack:
    mmsi: str
    positions: List[VesselPosition]
    static_data: Optional[VesselStatic]
    predicted_positions: List[VesselPosition]
    last_update: datetime


@dataclass
class CollisionRiskAssessment:
    own_vessel_mmsi: str
    target_vessel_mmsi: str
    assessment_time: datetime
    cpa_distance: float           # Closest Point of Approach distance (nautical miles)
    tcpa_time: float             # Time to Closest Point of Approach (minutes)
    cpa_position: Tuple[float, float]  # Lat, Lon of CPA
    risk_level: RiskLevel
    risk_score: float            # 0-1 probability of collision
    encounter_type: AlertType
    relative_bearing: float      # degrees
    relative_speed: float        # knots
    action_required: bool
    recommended_action: str
    confidence: float            # ML model confidence


@dataclass
class CollisionAlert:
    alert_id: str
    risk_assessment: CollisionRiskAssessment
    created_at: datetime
    acknowledged: bool
    resolved: bool
    escalation_level: int
    time_to_action: float        # minutes until action required
    colregs_rule: Optional[str]  # Applicable COLREGS rule


class AISDataProcessor:
    """AIS data processing and vessel tracking system"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.vessel_tracks: Dict[str, VesselTrack] = {}
        self.position_history_limit = 100  # Keep last 100 positions per vessel
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize AIS database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Vessel positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vessel_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mmsi TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                course_over_ground REAL,
                speed_over_ground REAL,
                heading REAL,
                rate_of_turn REAL,
                navigation_status INTEGER,
                position_accuracy BOOLEAN,
                raim BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Vessel static data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vessel_static (
                mmsi TEXT PRIMARY KEY,
                vessel_name TEXT,
                call_sign TEXT,
                imo TEXT,
                vessel_type INTEGER,
                to_bow INTEGER,
                to_stern INTEGER,
                to_port INTEGER,
                to_starboard INTEGER,
                draught REAL,
                destination TEXT,
                eta TIMESTAMP,
                ais_version INTEGER,
                last_updated TIMESTAMP
            )
        """)
        
        # Collision assessments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collision_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assessment_id TEXT UNIQUE,
                own_vessel_mmsi TEXT,
                target_vessel_mmsi TEXT,
                assessment_time TIMESTAMP,
                cpa_distance REAL,
                tcpa_time REAL,
                cpa_lat REAL,
                cpa_lon REAL,
                risk_level TEXT,
                risk_score REAL,
                encounter_type TEXT,
                relative_bearing REAL,
                relative_speed REAL,
                action_required BOOLEAN,
                recommended_action TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Collision alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collision_alerts (
                alert_id TEXT PRIMARY KEY,
                assessment_id TEXT,
                created_at TIMESTAMP,
                acknowledged BOOLEAN DEFAULT FALSE,
                resolved BOOLEAN DEFAULT FALSE,
                escalation_level INTEGER DEFAULT 1,
                time_to_action REAL,
                colregs_rule TEXT,
                FOREIGN KEY (assessment_id) REFERENCES collision_assessments (assessment_id)
            )
        """)
        
        # Create spatial indices
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vessel_positions_spatial 
            ON vessel_positions (lat, lon, timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vessel_positions_mmsi 
            ON vessel_positions (mmsi, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    async def process_ais_message(self, ais_message: Dict[str, Any]) -> Optional[VesselPosition]:
        """Process incoming AIS message"""
        try:
            mmsi = str(ais_message.get('mmsi', ''))
            if not mmsi:
                return None
            
            # Parse position report
            if ais_message.get('msg_type') in [1, 2, 3]:  # Position reports
                position = VesselPosition(
                    mmsi=mmsi,
                    timestamp=datetime.utcnow(),
                    lat=float(ais_message.get('lat', 0.0)),
                    lon=float(ais_message.get('lon', 0.0)),
                    course_over_ground=float(ais_message.get('cog', 0.0)),
                    speed_over_ground=float(ais_message.get('sog', 0.0)),
                    heading=float(ais_message.get('heading', 0.0)),
                    rate_of_turn=ais_message.get('rot'),
                    position_accuracy=bool(ais_message.get('accuracy', False)),
                    raim=bool(ais_message.get('raim', False)),
                    navigation_status=NavigationStatus(ais_message.get('nav_status', 15))
                )
                
                # Update vessel track
                await self._update_vessel_track(position)
                
                # Store in database
                await self._store_position(position)
                
                return position
            
            # Parse static data
            elif ais_message.get('msg_type') == 5:  # Static and voyage data
                static_data = VesselStatic(
                    mmsi=mmsi,
                    vessel_name=ais_message.get('vessel_name', '').strip(),
                    call_sign=ais_message.get('call_sign', '').strip(),
                    imo=ais_message.get('imo'),
                    vessel_type=VesselType(ais_message.get('ship_type', 0)),
                    dimensions=(
                        ais_message.get('to_bow', 0),
                        ais_message.get('to_stern', 0),
                        ais_message.get('to_port', 0),
                        ais_message.get('to_starboard', 0)
                    ),
                    draught=ais_message.get('draught'),
                    destination=ais_message.get('destination', '').strip(),
                    eta=self._parse_eta(ais_message.get('eta')),
                    ais_version=ais_message.get('ais_version', 0)
                )
                
                # Update vessel track static data
                if mmsi in self.vessel_tracks:
                    self.vessel_tracks[mmsi].static_data = static_data
                
                # Store in database
                await self._store_static_data(static_data)
        
        except Exception as e:
            print(f"Error processing AIS message: {e}")
            return None
        
        return None
    
    async def _update_vessel_track(self, position: VesselPosition):
        """Update vessel track with new position"""
        mmsi = position.mmsi
        
        if mmsi not in self.vessel_tracks:
            self.vessel_tracks[mmsi] = VesselTrack(
                mmsi=mmsi,
                positions=[],
                static_data=None,
                predicted_positions=[],
                last_update=datetime.utcnow()
            )
        
        track = self.vessel_tracks[mmsi]
        track.positions.append(position)
        track.last_update = datetime.utcnow()
        
        # Limit position history
        if len(track.positions) > self.position_history_limit:
            track.positions = track.positions[-self.position_history_limit:]
        
        # Generate predicted positions
        track.predicted_positions = await self._predict_vessel_positions(track)
    
    async def _predict_vessel_positions(self, track: VesselTrack, 
                                      prediction_minutes: int = 30) -> List[VesselPosition]:
        """Predict future vessel positions"""
        if len(track.positions) < 2:
            return []
        
        latest_position = track.positions[-1]
        
        # Simple linear prediction based on current course and speed
        # In production, use more sophisticated prediction models
        
        predicted_positions = []
        current_time = latest_position.timestamp
        
        for minutes in range(1, prediction_minutes + 1, 2):  # Every 2 minutes
            prediction_time = current_time + timedelta(minutes=minutes)
            
            # Calculate distance traveled
            distance_nm = latest_position.speed_over_ground * (minutes / 60.0)
            
            # Calculate new position
            new_lat, new_lon = self._calculate_destination_point(
                latest_position.lat, latest_position.lon,
                latest_position.course_over_ground, distance_nm
            )
            
            predicted_pos = VesselPosition(
                mmsi=track.mmsi,
                timestamp=prediction_time,
                lat=new_lat,
                lon=new_lon,
                course_over_ground=latest_position.course_over_ground,
                speed_over_ground=latest_position.speed_over_ground,
                heading=latest_position.heading,
                rate_of_turn=latest_position.rate_of_turn,
                position_accuracy=False,  # Predicted position
                raim=False,
                navigation_status=latest_position.navigation_status
            )
            
            predicted_positions.append(predicted_pos)
        
        return predicted_positions
    
    def _parse_eta(self, eta_data: Optional[Dict]) -> Optional[datetime]:
        """Parse ETA data from AIS message"""
        if not eta_data:
            return None
        
        try:
            month = eta_data.get('month', 0)
            day = eta_data.get('day', 0)
            hour = eta_data.get('hour', 24)
            minute = eta_data.get('minute', 60)
            
            if month == 0 or day == 0 or hour == 24 or minute == 60:
                return None  # Invalid ETA
            
            current_year = datetime.utcnow().year
            return datetime(current_year, month, day, hour, minute)
        
        except (ValueError, TypeError):
            return None
    
    async def _store_position(self, position: VesselPosition):
        """Store vessel position in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO vessel_positions 
            (mmsi, timestamp, lat, lon, course_over_ground, speed_over_ground,
             heading, rate_of_turn, navigation_status, position_accuracy, raim)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            position.mmsi, position.timestamp, position.lat, position.lon,
            position.course_over_ground, position.speed_over_ground,
            position.heading, position.rate_of_turn, position.navigation_status.value,
            position.position_accuracy, position.raim
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_static_data(self, static_data: VesselStatic):
        """Store vessel static data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO vessel_static 
            (mmsi, vessel_name, call_sign, imo, vessel_type,
             to_bow, to_stern, to_port, to_starboard, draught,
             destination, eta, ais_version, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            static_data.mmsi, static_data.vessel_name, static_data.call_sign,
            static_data.imo, static_data.vessel_type.value,
            static_data.dimensions[0], static_data.dimensions[1],
            static_data.dimensions[2], static_data.dimensions[3],
            static_data.draught, static_data.destination, static_data.eta,
            static_data.ais_version, datetime.utcnow()
        ))
        
        conn.commit()
        conn.close()
    
    def get_vessels_in_area(self, center_lat: float, center_lon: float, 
                           radius_nm: float) -> List[VesselTrack]:
        """Get all vessels within specified radius"""
        nearby_vessels = []
        
        for track in self.vessel_tracks.values():
            if track.positions:
                latest_pos = track.positions[-1]
                distance = self._calculate_distance(
                    center_lat, center_lon, latest_pos.lat, latest_pos.lon
                )
                
                if distance <= radius_nm:
                    nearby_vessels.append(track)
        
        return nearby_vessels
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in nautical miles"""
        distance_km = geodesic((lat1, lon1), (lat2, lon2)).kilometers
        return distance_km * 0.539957  # Convert to nautical miles
    
    def _calculate_destination_point(self, lat: float, lon: float, 
                                   bearing: float, distance: float) -> Tuple[float, float]:
        """Calculate destination point given start, bearing, and distance"""
        R = 3440.065  # Earth radius in nautical miles
        
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        bearing_rad = math.radians(bearing)
        
        lat2_rad = math.asin(
            math.sin(lat_rad) * math.cos(distance / R) +
            math.cos(lat_rad) * math.sin(distance / R) * math.cos(bearing_rad)
        )
        
        lon2_rad = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance / R) * math.cos(lat_rad),
            math.cos(distance / R) - math.sin(lat_rad) * math.sin(lat2_rad)
        )
        
        lat2 = math.degrees(lat2_rad)
        lon2 = math.degrees(lon2_rad)
        
        # Normalize longitude
        lon2 = (lon2 + 540) % 360 - 180
        
        return lat2, lon2


class CollisionPredictor:
    """Machine learning-based collision risk prediction system"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.ais_processor = AISDataProcessor(db_path)
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = [
            'cpa_distance', 'tcpa_time', 'relative_speed', 'relative_bearing',
            'own_speed', 'target_speed', 'speed_ratio', 'bearing_rate',
            'distance_rate', 'encounter_angle', 'own_vessel_length',
            'target_vessel_length', 'visibility_factor', 'traffic_density'
        ]
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize collision prediction model"""
        # In production, load pre-trained model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        # Generate synthetic training data for demonstration
        self._train_with_synthetic_data()
    
    def _train_with_synthetic_data(self):
        """Train model with synthetic data (for demonstration)"""
        # Generate synthetic training data
        n_samples = 10000
        
        # Features: CPA distance, TCPA time, relative speed, etc.
        X = np.random.rand(n_samples, len(self.feature_columns))
        
        # Scale features to realistic ranges
        X[:, 0] *= 5.0  # CPA distance (0-5 nm)
        X[:, 1] = X[:, 1] * 60 - 10  # TCPA time (-10 to 50 minutes)
        X[:, 2] *= 30  # Relative speed (0-30 knots)
        X[:, 3] *= 360  # Relative bearing (0-360 degrees)
        X[:, 4] *= 25  # Own speed (0-25 knots)
        X[:, 5] *= 25  # Target speed (0-25 knots)
        
        # Generate labels based on collision risk rules
        y = np.zeros(n_samples)
        
        # High risk: Close CPA and short TCPA
        high_risk = (X[:, 0] < 0.5) & (X[:, 1] > 0) & (X[:, 1] < 10) & (X[:, 2] > 5)
        y[high_risk] = 1
        
        # Medium risk: Moderate CPA and TCPA
        medium_risk = (X[:, 0] < 1.0) & (X[:, 1] > 0) & (X[:, 1] < 20) & (X[:, 2] > 3)
        y[medium_risk] = 1
        
        # Train model
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
    
    async def assess_collision_risk(self, own_vessel_pos: VesselPosition,
                                  target_vessel_track: VesselTrack) -> CollisionRiskAssessment:
        """Assess collision risk between own vessel and target vessel"""
        
        if not target_vessel_track.positions:
            return None
        
        target_pos = target_vessel_track.positions[-1]
        
        # Calculate CPA (Closest Point of Approach) and TCPA (Time to CPA)
        cpa_info = self._calculate_cpa_tcpa(own_vessel_pos, target_pos)
        
        if cpa_info is None:
            return None
        
        cpa_distance, tcpa_time, cpa_position = cpa_info
        
        # Calculate relative motion parameters
        relative_bearing = self._calculate_relative_bearing(own_vessel_pos, target_pos)
        relative_speed = self._calculate_relative_speed(own_vessel_pos, target_pos)
        
        # Determine encounter type
        encounter_type = self._classify_encounter(own_vessel_pos, target_pos, relative_bearing)
        
        # Extract features for ML prediction
        features = self._extract_features(
            own_vessel_pos, target_pos, target_vessel_track,
            cpa_distance, tcpa_time, relative_bearing, relative_speed
        )
        
        # Predict collision risk
        risk_score = 0.0
        confidence = 0.5
        
        if self.model and len(features) == len(self.feature_columns):
            features_scaled = self.scaler.transform([features])
            risk_proba = self.model.predict_proba(features_scaled)[0]
            risk_score = risk_proba[1] if len(risk_proba) > 1 else 0.0
            confidence = max(risk_proba)
        
        # Determine risk level
        risk_level = self._determine_risk_level(cpa_distance, tcpa_time, risk_score)
        
        # Generate recommended action
        action_required = risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.IMMINENT]
        recommended_action = self._generate_recommendation(
            encounter_type, risk_level, cpa_distance, tcpa_time, relative_bearing
        )
        
        assessment_id = f"risk_{own_vessel_pos.mmsi}_{target_pos.mmsi}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        assessment = CollisionRiskAssessment(
            own_vessel_mmsi=own_vessel_pos.mmsi,
            target_vessel_mmsi=target_pos.mmsi,
            assessment_time=datetime.utcnow(),
            cpa_distance=cpa_distance,
            tcpa_time=tcpa_time,
            cpa_position=cpa_position,
            risk_level=risk_level,
            risk_score=risk_score,
            encounter_type=encounter_type,
            relative_bearing=relative_bearing,
            relative_speed=relative_speed,
            action_required=action_required,
            recommended_action=recommended_action,
            confidence=confidence
        )
        
        # Store assessment
        await self._store_risk_assessment(assessment)
        
        return assessment
    
    def _calculate_cpa_tcpa(self, own_pos: VesselPosition, 
                          target_pos: VesselPosition) -> Optional[Tuple[float, float, Tuple[float, float]]]:
        """Calculate Closest Point of Approach (CPA) and Time to CPA (TCPA)"""
        
        # Convert to Cartesian coordinates (approximate for small distances)
        own_x = own_pos.lon * math.cos(math.radians(own_pos.lat))
        own_y = own_pos.lat
        target_x = target_pos.lon * math.cos(math.radians(target_pos.lat))
        target_y = target_pos.lat
        
        # Convert speeds and courses to velocity vectors
        own_vx = own_pos.speed_over_ground * math.sin(math.radians(own_pos.course_over_ground))
        own_vy = own_pos.speed_over_ground * math.cos(math.radians(own_pos.course_over_ground))
        target_vx = target_pos.speed_over_ground * math.sin(math.radians(target_pos.course_over_ground))
        target_vy = target_pos.speed_over_ground * math.cos(math.radians(target_pos.course_over_ground))
        
        # Relative velocity
        rel_vx = target_vx - own_vx
        rel_vy = target_vy - own_vy
        
        # Relative position
        rel_x = target_x - own_x
        rel_y = target_y - own_y
        
        # Calculate TCPA
        rel_speed_squared = rel_vx * rel_vx + rel_vy * rel_vy
        
        if rel_speed_squared < 0.01:  # Vessels moving at same speed and direction
            # Calculate current distance as CPA
            cpa_distance_deg = math.sqrt(rel_x * rel_x + rel_y * rel_y)
            cpa_distance_nm = cpa_distance_deg * 60  # Convert degrees to nautical miles
            return cpa_distance_nm, float('inf'), (target_pos.lat, target_pos.lon)
        
        tcpa_hours = -(rel_x * rel_vx + rel_y * rel_vy) / rel_speed_squared
        tcpa_minutes = tcpa_hours * 60
        
        # Calculate CPA position and distance
        cpa_own_x = own_x + own_vx * tcpa_hours
        cpa_own_y = own_y + own_vy * tcpa_hours
        cpa_target_x = target_x + target_vx * tcpa_hours
        cpa_target_y = target_y + target_vy * tcpa_hours
        
        cpa_distance_deg = math.sqrt((cpa_target_x - cpa_own_x) ** 2 + (cpa_target_y - cpa_own_y) ** 2)
        cpa_distance_nm = cpa_distance_deg * 60  # Convert degrees to nautical miles
        
        # CPA position (midpoint)
        cpa_lat = (cpa_own_y + cpa_target_y) / 2
        cpa_lon = (cpa_own_x + cpa_target_x) / 2 / math.cos(math.radians(cpa_lat))
        
        return cpa_distance_nm, tcpa_minutes, (cpa_lat, cpa_lon)
    
    def _calculate_relative_bearing(self, own_pos: VesselPosition, target_pos: VesselPosition) -> float:
        """Calculate relative bearing from own vessel to target vessel"""
        lat1_rad = math.radians(own_pos.lat)
        lat2_rad = math.radians(target_pos.lat)
        dlon_rad = math.radians(target_pos.lon - own_pos.lon)
        
        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        # Convert to relative bearing (relative to own vessel's heading)
        relative_bearing = (bearing_deg - own_pos.heading + 360) % 360
        
        return relative_bearing
    
    def _calculate_relative_speed(self, own_pos: VesselPosition, target_pos: VesselPosition) -> float:
        """Calculate relative speed between vessels"""
        # Vector calculation of relative velocity
        own_vx = own_pos.speed_over_ground * math.sin(math.radians(own_pos.course_over_ground))
        own_vy = own_pos.speed_over_ground * math.cos(math.radians(own_pos.course_over_ground))
        target_vx = target_pos.speed_over_ground * math.sin(math.radians(target_pos.course_over_ground))
        target_vy = target_pos.speed_over_ground * math.cos(math.radians(target_pos.course_over_ground))
        
        rel_vx = target_vx - own_vx
        rel_vy = target_vy - own_vy
        
        return math.sqrt(rel_vx * rel_vx + rel_vy * rel_vy)
    
    def _classify_encounter(self, own_pos: VesselPosition, target_pos: VesselPosition,
                          relative_bearing: float) -> AlertType:
        """Classify the type of encounter based on COLREGS rules"""
        
        # Calculate relative course difference
        course_diff = abs(own_pos.course_over_ground - target_pos.course_over_ground)
        if course_diff > 180:
            course_diff = 360 - course_diff
        
        # Head-on situation
        if course_diff > 150 and 345 <= relative_bearing <= 15:
            return AlertType.HEAD_ON
        
        # Crossing situations
        if 15 < relative_bearing < 112.5:  # Target on starboard bow
            return AlertType.CROSSING_SITUATION
        elif 247.5 < relative_bearing < 345:  # Target on port bow
            return AlertType.CROSSING_SITUATION
        
        # Overtaking situation
        if 112.5 <= relative_bearing <= 247.5:
            return AlertType.OVERTAKING
        
        # Check for special vessel priorities
        if target_pos.navigation_status == NavigationStatus.FISHING:
            return AlertType.FISHING_VESSEL_PRIORITY
        elif target_pos.navigation_status in [NavigationStatus.NOT_UNDER_COMMAND,
                                            NavigationStatus.RESTRICTED_MANOEUVRABILITY]:
            return AlertType.RESTRICTED_MANEUVERABILITY
        elif target_pos.navigation_status == NavigationStatus.AT_ANCHOR:
            return AlertType.ANCHOR_DRAG_RISK
        
        return AlertType.CPA_VIOLATION
    
    def _extract_features(self, own_pos: VesselPosition, target_pos: VesselPosition,
                         target_track: VesselTrack, cpa_distance: float, tcpa_time: float,
                         relative_bearing: float, relative_speed: float) -> List[float]:
        """Extract features for ML model"""
        
        # Calculate additional features
        speed_ratio = own_pos.speed_over_ground / max(target_pos.speed_over_ground, 0.1)
        
        # Rate of bearing change (requires historical data)
        bearing_rate = 0.0
        if len(target_track.positions) >= 2:
            prev_pos = target_track.positions[-2]
            time_diff = (target_pos.timestamp - prev_pos.timestamp).total_seconds() / 60  # minutes
            if time_diff > 0:
                prev_bearing = self._calculate_relative_bearing(own_pos, prev_pos)
                bearing_rate = (relative_bearing - prev_bearing) / time_diff
        
        # Distance rate of change
        distance_rate = 0.0
        if len(target_track.positions) >= 2:
            prev_pos = target_track.positions[-2]
            time_diff = (target_pos.timestamp - prev_pos.timestamp).total_seconds() / 60
            if time_diff > 0:
                current_distance = self.ais_processor._calculate_distance(
                    own_pos.lat, own_pos.lon, target_pos.lat, target_pos.lon
                )
                prev_distance = self.ais_processor._calculate_distance(
                    own_pos.lat, own_pos.lon, prev_pos.lat, prev_pos.lon
                )
                distance_rate = (current_distance - prev_distance) / time_diff
        
        # Encounter angle
        course_diff = abs(own_pos.course_over_ground - target_pos.course_over_ground)
        encounter_angle = min(course_diff, 360 - course_diff)
        
        # Vessel dimensions (simplified)
        own_length = 100  # Default length in meters
        target_length = 100
        if target_track.static_data:
            dims = target_track.static_data.dimensions
            target_length = dims[0] + dims[1] if dims[0] + dims[1] > 0 else 100
        
        # Environmental factors
        visibility_factor = 1.0  # Good visibility (would come from weather data)
        traffic_density = min(10.0, len(self.ais_processor.vessel_tracks))  # Simplified
        
        return [
            cpa_distance, tcpa_time, relative_speed, relative_bearing,
            own_pos.speed_over_ground, target_pos.speed_over_ground, speed_ratio,
            bearing_rate, distance_rate, encounter_angle, own_length, target_length,
            visibility_factor, traffic_density
        ]
    
    def _determine_risk_level(self, cpa_distance: float, tcpa_time: float, risk_score: float) -> RiskLevel:
        """Determine risk level based on CPA, TCPA, and ML score"""
        
        # TCPA-based risk (negative TCPA means vessels are diverging)
        if tcpa_time < 0:
            return RiskLevel.LOW
        
        # Imminent collision
        if cpa_distance < 0.1 and tcpa_time < 2:
            return RiskLevel.IMMINENT
        
        # Critical risk
        if cpa_distance < 0.25 and tcpa_time < 5:
            return RiskLevel.CRITICAL
        
        # High risk
        if (cpa_distance < 0.5 and tcpa_time < 10) or risk_score > 0.8:
            return RiskLevel.HIGH
        
        # Moderate risk
        if (cpa_distance < 1.0 and tcpa_time < 20) or risk_score > 0.5:
            return RiskLevel.MODERATE
        
        return RiskLevel.LOW
    
    def _generate_recommendation(self, encounter_type: AlertType, risk_level: RiskLevel,
                               cpa_distance: float, tcpa_time: float, 
                               relative_bearing: float) -> str:
        """Generate recommended action based on encounter analysis"""
        
        if risk_level == RiskLevel.LOW:
            return "Continue on current course. Monitor target vessel."
        
        recommendations = {
            AlertType.HEAD_ON: "Head-on situation: Both vessels should alter course to starboard.",
            AlertType.CROSSING_SITUATION: "Crossing situation: Give way if target is on starboard side, maintain course if on port side.",
            AlertType.OVERTAKING: "Overtaking situation: Keep clear of overtaken vessel.",
            AlertType.FISHING_VESSEL_PRIORITY: "Keep clear of fishing vessel engaged in fishing.",
            AlertType.RESTRICTED_MANEUVERABILITY: "Keep clear of vessel restricted in maneuverability.",
            AlertType.ANCHOR_DRAG_RISK: "Monitor anchored vessel for potential anchor drag."
        }
        
        base_recommendation = recommendations.get(encounter_type, "Take appropriate action to avoid collision.")
        
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.IMMINENT]:
            if tcpa_time < 5:
                return f"IMMEDIATE ACTION REQUIRED: {base_recommendation} Sound danger signal."
            else:
                return f"URGENT: {base_recommendation} Prepare for emergency maneuver."
        elif risk_level == RiskLevel.HIGH:
            return f"HIGH RISK: {base_recommendation} Take early action."
        else:
            return base_recommendation
    
    async def _store_risk_assessment(self, assessment: CollisionRiskAssessment):
        """Store collision risk assessment in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        assessment_id = f"assess_{assessment.own_vessel_mmsi}_{assessment.target_vessel_mmsi}_{assessment.assessment_time.strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO collision_assessments 
            (assessment_id, own_vessel_mmsi, target_vessel_mmsi, assessment_time,
             cpa_distance, tcpa_time, cpa_lat, cpa_lon, risk_level, risk_score,
             encounter_type, relative_bearing, relative_speed, action_required,
             recommended_action, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            assessment_id, assessment.own_vessel_mmsi, assessment.target_vessel_mmsi,
            assessment.assessment_time, assessment.cpa_distance, assessment.tcpa_time,
            assessment.cpa_position[0], assessment.cpa_position[1], assessment.risk_level.value,
            assessment.risk_score, assessment.encounter_type.value, assessment.relative_bearing,
            assessment.relative_speed, assessment.action_required, assessment.recommended_action,
            assessment.confidence
        ))
        
        conn.commit()
        conn.close()
    
    async def monitor_collision_risks(self, own_vessel_mmsi: str, 
                                    monitoring_radius_nm: float = 12) -> List[CollisionRiskAssessment]:
        """Monitor collision risks for own vessel"""
        
        # Get own vessel position
        if own_vessel_mmsi not in self.ais_processor.vessel_tracks:
            return []
        
        own_track = self.ais_processor.vessel_tracks[own_vessel_mmsi]
        if not own_track.positions:
            return []
        
        own_position = own_track.positions[-1]
        
        # Get nearby vessels
        nearby_vessels = self.ais_processor.get_vessels_in_area(
            own_position.lat, own_position.lon, monitoring_radius_nm
        )
        
        risk_assessments = []
        
        for vessel_track in nearby_vessels:
            if vessel_track.mmsi == own_vessel_mmsi:
                continue  # Skip own vessel
            
            # Assess collision risk
            risk_assessment = await self.assess_collision_risk(own_position, vessel_track)
            if risk_assessment and risk_assessment.risk_level != RiskLevel.LOW:
                risk_assessments.append(risk_assessment)
        
        # Sort by risk level and TCPA
        risk_assessments.sort(key=lambda x: (
            5 - ['low', 'moderate', 'high', 'critical', 'imminent'].index(x.risk_level.value),
            x.tcpa_time if x.tcpa_time > 0 else float('inf')
        ))
        
        return risk_assessments


async def main():
    """Example usage of AIS collision prediction system"""
    
    # Initialize systems
    ais_processor = AISDataProcessor("ais_collision.db")
    collision_predictor = CollisionPredictor("ais_collision.db")
    
    print("AIS Collision Prediction System Demo")
    print("====================================")
    
    # Simulate AIS messages
    print("\nSimulating AIS messages...")
    
    # Own vessel AIS message (position report)
    own_vessel_ais = {
        'msg_type': 1,
        'mmsi': '123456789',
        'lat': 37.7749,
        'lon': -122.4194,
        'cog': 90.0,  # Course Over Ground (degrees)
        'sog': 12.0,  # Speed Over Ground (knots)
        'heading': 90.0,
        'nav_status': 0,  # Under way using engine
        'accuracy': True,
        'raim': True
    }
    
    # Target vessel AIS messages
    target_vessels = [
        {
            'msg_type': 1,
            'mmsi': '987654321',
            'lat': 37.7749,
            'lon': -122.3194,  # About 6nm east, head-on course
            'cog': 270.0,  # Westbound
            'sog': 10.0,
            'heading': 270.0,
            'nav_status': 0,
            'accuracy': True,
            'raim': True
        },
        {
            'msg_type': 1,
            'mmsi': '555666777',
            'lat': 37.7649,
            'lon': -122.4094,  # Crossing from south
            'cog': 45.0,  # Northeast
            'sog': 8.0,
            'heading': 45.0,
            'nav_status': 0,
            'accuracy': True,
            'raim': True
        }
    ]
    
    # Process own vessel position
    own_position = await ais_processor.process_ais_message(own_vessel_ais)
    print(f"Own vessel position: {own_position.lat:.4f}°N, {own_position.lon:.4f}°W")
    print(f"Course: {own_position.course_over_ground:.0f}°, Speed: {own_position.speed_over_ground:.1f} kts")
    
    # Process target vessel positions
    target_positions = []
    for target_ais in target_vessels:
        position = await ais_processor.process_ais_message(target_ais)
        target_positions.append(position)
        print(f"Target {position.mmsi}: {position.lat:.4f}°N, {position.lon:.4f}°W")
        print(f"  Course: {position.course_over_ground:.0f}°, Speed: {position.speed_over_ground:.1f} kts")
    
    # Add static data for target vessels
    static_data = {
        'msg_type': 5,
        'mmsi': '987654321',
        'vessel_name': 'CARGO SHIP ALPHA',
        'call_sign': 'ABCD',
        'ship_type': 70,  # Cargo ship
        'to_bow': 100,
        'to_stern': 50,
        'to_port': 15,
        'to_starboard': 15,
        'destination': 'SAN FRANCISCO',
        'eta': {'month': 12, 'day': 25, 'hour': 14, 'minute': 30}
    }
    
    await ais_processor.process_ais_message(static_data)
    
    print("\n" + "="*50)
    print("COLLISION RISK ASSESSMENT")
    print("="*50)
    
    # Monitor collision risks
    risk_assessments = await collision_predictor.monitor_collision_risks('123456789', 20)
    
    if not risk_assessments:
        print("No collision risks detected.")
    else:
        for i, assessment in enumerate(risk_assessments, 1):
            print(f"\nRISK ASSESSMENT #{i}")
            print(f"Target Vessel: {assessment.target_vessel_mmsi}")
            print(f"Risk Level: {assessment.risk_level.value.upper()}")
            print(f"Risk Score: {assessment.risk_score:.3f}")
            print(f"CPA Distance: {assessment.cpa_distance:.2f} nm")
            print(f"TCPA: {assessment.tcpa_time:.1f} minutes")
            print(f"Encounter Type: {assessment.encounter_type.value.replace('_', ' ').title()}")
            print(f"Relative Bearing: {assessment.relative_bearing:.0f}°")
            print(f"Relative Speed: {assessment.relative_speed:.1f} kts")
            print(f"Action Required: {'YES' if assessment.action_required else 'NO'}")
            print(f"Recommendation: {assessment.recommended_action}")
            print(f"Confidence: {assessment.confidence:.3f}")
            
            if assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.IMMINENT]:
                print(f"⚠️  HIGH PRIORITY ALERT - IMMEDIATE ATTENTION REQUIRED")
    
    # Display vessel tracking summary
    print(f"\n" + "="*50)
    print("VESSEL TRACKING SUMMARY")
    print("="*50)
    print(f"Total vessels tracked: {len(ais_processor.vessel_tracks)}")
    
    for mmsi, track in ais_processor.vessel_tracks.items():
        print(f"\nVessel {mmsi}:")
        print(f"  Position history: {len(track.positions)} points")
        print(f"  Predicted positions: {len(track.predicted_positions)} points")
        print(f"  Last update: {track.last_update}")
        if track.static_data:
            print(f"  Name: {track.static_data.vessel_name}")
            print(f"  Type: {track.static_data.vessel_type.name}")
            print(f"  Destination: {track.static_data.destination}")


if __name__ == "__main__":
    asyncio.run(main())