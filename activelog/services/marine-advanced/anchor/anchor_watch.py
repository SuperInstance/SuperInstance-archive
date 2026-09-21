"""
ActiveLog Marine Advanced Suite - Anchor Watch with Drift Alerts

Advanced anchor monitoring system with intelligent drift detection, environmental analysis,
customizable alert zones, and predictive anchor drag assessment.
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
from scipy import stats
from scipy.spatial.distance import euclidean
from geopy.distance import geodesic
from shapely.geometry import Point, Polygon, Circle
from shapely.ops import transform
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


class AnchorAlertType(Enum):
    DRIFT_WARNING = "drift_warning"
    DRAG_DETECTED = "drag_detected"
    ZONE_BREACH = "zone_breach"
    ANCHOR_WATCH_FAILURE = "anchor_watch_failure"
    ENVIRONMENTAL_WARNING = "environmental_warning"
    DEPTH_CHANGE = "depth_change"
    SWING_RADIUS_EXCEEDED = "swing_radius_exceeded"


class AlertSeverity(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnchorStatus(Enum):
    SETTING = "setting"
    SET = "set"
    DRAGGING = "dragging"
    WEIGHING = "weighing"
    UNKNOWN = "unknown"


class SeabedType(Enum):
    SAND = "sand"
    MUD = "mud"
    CLAY = "clay"
    ROCK = "rock"
    CORAL = "coral"
    GRAVEL = "gravel"
    WEED = "weed"
    UNKNOWN = "unknown"


@dataclass
class AnchorPosition:
    timestamp: datetime
    lat: float
    lon: float
    heading: float
    depth: float
    position_accuracy: float  # meters
    gps_quality: int         # 0-9 GPS fix quality
    satellite_count: int


@dataclass
class EnvironmentalConditions:
    timestamp: datetime
    wind_speed: float        # knots
    wind_direction: float    # degrees
    current_speed: float     # knots
    current_direction: float # degrees
    wave_height: float       # meters
    wave_period: float       # seconds
    tide_height: float       # meters from chart datum
    tide_rate: float         # meters per hour
    barometric_pressure: float  # millibars


@dataclass
class AnchorDeployment:
    deployment_id: str
    vessel_name: str
    anchor_type: str
    chain_length: float      # meters
    rope_length: float       # meters
    anchor_weight: float     # kg
    deployment_time: datetime
    initial_position: AnchorPosition
    water_depth: float       # meters
    seabed_type: SeabedType
    scope_ratio: float       # total rode length / water depth
    notes: str


@dataclass
class AlertZone:
    zone_id: str
    zone_name: str
    zone_type: str          # "circle", "polygon", "depth_contour"
    geometry: Any           # Shapely geometry object
    alert_threshold: float  # meters for buffer zones
    is_active: bool
    created_at: datetime


@dataclass
class DriftAnalysis:
    analysis_time: datetime
    current_position: AnchorPosition
    reference_position: AnchorPosition  # Original anchor position
    drift_distance: float    # meters from reference
    drift_bearing: float     # degrees
    drift_rate: float        # meters per hour
    max_swing_radius: float  # meters
    position_variance: float # position stability measure
    confidence_score: float  # 0-1, confidence in position accuracy


@dataclass
class AnchorAlert:
    alert_id: str
    deployment_id: str
    alert_type: AnchorAlertType
    severity: AlertSeverity
    timestamp: datetime
    current_position: AnchorPosition
    drift_analysis: DriftAnalysis
    environmental_conditions: EnvironmentalConditions
    message: str
    recommended_action: str
    acknowledged: bool
    resolved: bool


class AnchorWatchSystem:
    """Advanced anchor watch monitoring system"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.position_history_limit = 1000
        self.alert_zones: Dict[str, AlertZone] = {}
        self.active_deployments: Dict[str, AnchorDeployment] = {}
        self.position_histories: Dict[str, List[AnchorPosition]] = {}
        self.environmental_history: Dict[str, List[EnvironmentalConditions]] = {}
        
        # Configurable thresholds
        self.drift_warning_threshold = 15.0    # meters
        self.drag_detection_threshold = 30.0   # meters
        self.swing_radius_multiplier = 1.5     # factor of expected swing radius
        self.position_update_interval = 60     # seconds
        self.environmental_update_interval = 300  # seconds
        
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize anchor watch database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Anchor deployments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anchor_deployments (
                deployment_id TEXT PRIMARY KEY,
                vessel_name TEXT NOT NULL,
                anchor_type TEXT,
                chain_length REAL,
                rope_length REAL,
                anchor_weight REAL,
                deployment_time TIMESTAMP,
                initial_lat REAL,
                initial_lon REAL,
                initial_depth REAL,
                water_depth REAL,
                seabed_type TEXT,
                scope_ratio REAL,
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Position history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anchor_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT,
                timestamp TIMESTAMP,
                lat REAL,
                lon REAL,
                heading REAL,
                depth REAL,
                position_accuracy REAL,
                gps_quality INTEGER,
                satellite_count INTEGER,
                FOREIGN KEY (deployment_id) REFERENCES anchor_deployments (deployment_id)
            )
        """)
        
        # Environmental conditions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environmental_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT,
                timestamp TIMESTAMP,
                wind_speed REAL,
                wind_direction REAL,
                current_speed REAL,
                current_direction REAL,
                wave_height REAL,
                wave_period REAL,
                tide_height REAL,
                tide_rate REAL,
                barometric_pressure REAL,
                FOREIGN KEY (deployment_id) REFERENCES anchor_deployments (deployment_id)
            )
        """)
        
        # Alert zones table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_zones (
                zone_id TEXT PRIMARY KEY,
                zone_name TEXT,
                zone_type TEXT,
                geometry_wkt TEXT,
                alert_threshold REAL,
                is_active BOOLEAN,
                created_at TIMESTAMP
            )
        """)
        
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anchor_alerts (
                alert_id TEXT PRIMARY KEY,
                deployment_id TEXT,
                alert_type TEXT,
                severity TEXT,
                timestamp TIMESTAMP,
                current_lat REAL,
                current_lon REAL,
                drift_distance REAL,
                drift_bearing REAL,
                message TEXT,
                recommended_action TEXT,
                acknowledged BOOLEAN DEFAULT FALSE,
                resolved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (deployment_id) REFERENCES anchor_deployments (deployment_id)
            )
        """)
        
        # Create indices for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_anchor_positions_deployment 
            ON anchor_positions (deployment_id, timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_environmental_deployment 
            ON environmental_conditions (deployment_id, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    async def deploy_anchor(self, deployment: AnchorDeployment) -> str:
        """Register new anchor deployment"""
        self.active_deployments[deployment.deployment_id] = deployment
        self.position_histories[deployment.deployment_id] = [deployment.initial_position]
        self.environmental_history[deployment.deployment_id] = []
        
        # Store in database
        await self._store_deployment(deployment)
        await self._store_position(deployment.deployment_id, deployment.initial_position)
        
        print(f"Anchor deployed: {deployment.vessel_name} at {deployment.initial_position.lat:.6f}, {deployment.initial_position.lon:.6f}")
        print(f"Water depth: {deployment.water_depth}m, Scope ratio: {deployment.scope_ratio:.1f}:1")
        
        return deployment.deployment_id
    
    async def update_position(self, deployment_id: str, position: AnchorPosition):
        """Update vessel position and perform drift analysis"""
        if deployment_id not in self.active_deployments:
            raise ValueError(f"No active deployment found: {deployment_id}")
        
        # Add position to history
        if deployment_id not in self.position_histories:
            self.position_histories[deployment_id] = []
        
        self.position_histories[deployment_id].append(position)
        
        # Limit history size
        if len(self.position_histories[deployment_id]) > self.position_history_limit:
            self.position_histories[deployment_id] = self.position_histories[deployment_id][-self.position_history_limit:]
        
        # Store in database
        await self._store_position(deployment_id, position)
        
        # Perform drift analysis
        drift_analysis = await self._analyze_drift(deployment_id)
        
        # Check for alerts
        await self._check_drift_alerts(deployment_id, position, drift_analysis)
        
        return drift_analysis
    
    async def update_environmental_conditions(self, deployment_id: str, conditions: EnvironmentalConditions):
        """Update environmental conditions"""
        if deployment_id not in self.active_deployments:
            return
        
        # Add to history
        if deployment_id not in self.environmental_history:
            self.environmental_history[deployment_id] = []
        
        self.environmental_history[deployment_id].append(conditions)
        
        # Limit history size
        if len(self.environmental_history[deployment_id]) > 200:  # Keep last 200 readings
            self.environmental_history[deployment_id] = self.environmental_history[deployment_id][-200:]
        
        # Store in database
        await self._store_environmental_conditions(deployment_id, conditions)
        
        # Check for environmental alerts
        await self._check_environmental_alerts(deployment_id, conditions)
    
    async def _analyze_drift(self, deployment_id: str) -> DriftAnalysis:
        """Analyze vessel drift from anchor position"""
        deployment = self.active_deployments[deployment_id]
        positions = self.position_histories[deployment_id]
        
        if len(positions) < 2:
            # Not enough data for analysis
            return DriftAnalysis(
                analysis_time=datetime.utcnow(),
                current_position=positions[-1],
                reference_position=deployment.initial_position,
                drift_distance=0.0,
                drift_bearing=0.0,
                drift_rate=0.0,
                max_swing_radius=0.0,
                position_variance=0.0,
                confidence_score=0.5
            )
        
        current_position = positions[-1]
        reference_position = deployment.initial_position
        
        # Calculate drift distance from original anchor position
        drift_distance = geodesic(
            (reference_position.lat, reference_position.lon),
            (current_position.lat, current_position.lon)
        ).meters
        
        # Calculate drift bearing
        drift_bearing = self._calculate_bearing(
            reference_position.lat, reference_position.lon,
            current_position.lat, current_position.lon
        )
        
        # Calculate drift rate (recent movement)
        drift_rate = 0.0
        if len(positions) >= 2:
            time_diff = (current_position.timestamp - positions[-2].timestamp).total_seconds() / 3600  # hours
            if time_diff > 0:
                distance_moved = geodesic(
                    (positions[-2].lat, positions[-2].lon),
                    (current_position.lat, current_position.lon)
                ).meters
                drift_rate = distance_moved / time_diff  # meters per hour
        
        # Calculate maximum swing radius
        max_swing_radius = 0.0
        for pos in positions[-20:]:  # Check last 20 positions
            distance = geodesic(
                (reference_position.lat, reference_position.lon),
                (pos.lat, pos.lon)
            ).meters
            max_swing_radius = max(max_swing_radius, distance)
        
        # Calculate position variance (stability measure)
        if len(positions) >= 10:
            recent_positions = positions[-10:]
            lats = [p.lat for p in recent_positions]
            lons = [p.lon for p in recent_positions]
            position_variance = (np.var(lats) + np.var(lons)) * 111000  # Rough conversion to meters
        else:
            position_variance = 0.0
        
        # Calculate confidence score based on GPS quality and position accuracy
        gps_quality_score = min(1.0, current_position.gps_quality / 9.0)
        accuracy_score = min(1.0, 10.0 / max(current_position.position_accuracy, 1.0))
        satellite_score = min(1.0, current_position.satellite_count / 12.0)
        confidence_score = (gps_quality_score + accuracy_score + satellite_score) / 3.0
        
        return DriftAnalysis(
            analysis_time=datetime.utcnow(),
            current_position=current_position,
            reference_position=reference_position,
            drift_distance=drift_distance,
            drift_bearing=drift_bearing,
            drift_rate=drift_rate,
            max_swing_radius=max_swing_radius,
            position_variance=position_variance,
            confidence_score=confidence_score
        )
    
    async def _check_drift_alerts(self, deployment_id: str, current_position: AnchorPosition, 
                                drift_analysis: DriftAnalysis):
        """Check for drift-related alerts"""
        deployment = self.active_deployments[deployment_id]
        
        # Calculate expected swing radius
        total_rode = deployment.chain_length + deployment.rope_length
        expected_swing_radius = total_rode * 0.7  # Conservative estimate
        
        alerts = []
        
        # Check drift warning threshold
        if drift_analysis.drift_distance > self.drift_warning_threshold:
            alert = await self._create_alert(
                deployment_id, AnchorAlertType.DRIFT_WARNING, AlertSeverity.MEDIUM,
                current_position, drift_analysis,
                f"Vessel has drifted {drift_analysis.drift_distance:.1f}m from anchor position",
                "Monitor position closely. Check anchor holding."
            )
            alerts.append(alert)
        
        # Check drag detection threshold
        if drift_analysis.drift_distance > self.drag_detection_threshold:
            # Additional analysis for drag detection
            if await self._confirm_anchor_drag(deployment_id, drift_analysis):
                alert = await self._create_alert(
                    deployment_id, AnchorAlertType.DRAG_DETECTED, AlertSeverity.HIGH,
                    current_position, drift_analysis,
                    f"ANCHOR DRAG DETECTED! Vessel dragged {drift_analysis.drift_distance:.1f}m",
                    "IMMEDIATE ACTION REQUIRED: Reset anchor or find alternative anchorage."
                )
                alerts.append(alert)
        
        # Check swing radius
        if drift_analysis.max_swing_radius > expected_swing_radius * self.swing_radius_multiplier:
            alert = await self._create_alert(
                deployment_id, AnchorAlertType.SWING_RADIUS_EXCEEDED, AlertSeverity.MEDIUM,
                current_position, drift_analysis,
                f"Maximum swing radius exceeded: {drift_analysis.max_swing_radius:.1f}m",
                "Check rode length and scope. Consider reducing scope if safe."
            )
            alerts.append(alert)
        
        # Check zone breaches
        for zone_id, zone in self.alert_zones.items():
            if zone.is_active and await self._check_zone_breach(current_position, zone):
                alert = await self._create_alert(
                    deployment_id, AnchorAlertType.ZONE_BREACH, AlertSeverity.HIGH,
                    current_position, drift_analysis,
                    f"Alert zone breached: {zone.zone_name}",
                    "Vessel has entered restricted area. Take immediate corrective action."
                )
                alerts.append(alert)
        
        # Store alerts
        for alert in alerts:
            await self._store_alert(alert)
    
    async def _confirm_anchor_drag(self, deployment_id: str, drift_analysis: DriftAnalysis) -> bool:
        """Confirm anchor drag using multiple indicators"""
        positions = self.position_histories[deployment_id]
        
        if len(positions) < 5:
            return False
        
        # Check for consistent movement in one direction
        recent_positions = positions[-5:]
        bearings = []
        
        for i in range(1, len(recent_positions)):
            bearing = self._calculate_bearing(
                recent_positions[i-1].lat, recent_positions[i-1].lon,
                recent_positions[i].lat, recent_positions[i].lon
            )
            bearings.append(bearing)
        
        # Check bearing consistency (drag typically shows consistent direction)
        if len(bearings) >= 3:
            bearing_variance = np.var(bearings)
            consistent_movement = bearing_variance < 900  # Less than 30 degrees variance
        else:
            consistent_movement = False
        
        # Check drift rate (dragging typically shows increasing rate)
        drift_rate_increasing = drift_analysis.drift_rate > 5.0  # 5 meters per hour
        
        # Check position accuracy (low accuracy might indicate false drag)
        good_gps_accuracy = drift_analysis.confidence_score > 0.7
        
        # Confirm drag if multiple indicators present
        return consistent_movement and drift_rate_increasing and good_gps_accuracy
    
    async def _check_environmental_alerts(self, deployment_id: str, conditions: EnvironmentalConditions):
        """Check for environmental condition alerts"""
        # Check for severe weather conditions that might affect anchoring
        alerts = []
        
        current_position = self.position_histories[deployment_id][-1] if self.position_histories[deployment_id] else None
        if not current_position:
            return
        
        drift_analysis = await self._analyze_drift(deployment_id)
        
        # High wind warning
        if conditions.wind_speed > 25:  # 25 knots
            severity = AlertSeverity.HIGH if conditions.wind_speed > 35 else AlertSeverity.MEDIUM
            alert = await self._create_alert(
                deployment_id, AnchorAlertType.ENVIRONMENTAL_WARNING, severity,
                current_position, drift_analysis,
                f"High wind warning: {conditions.wind_speed:.1f} knots from {conditions.wind_direction:.0f}°",
                "Monitor anchor holding. Consider additional anchoring measures."
            )
            alerts.append(alert)
        
        # Large waves warning
        if conditions.wave_height > 2.0:
            alert = await self._create_alert(
                deployment_id, AnchorAlertType.ENVIRONMENTAL_WARNING, AlertSeverity.MEDIUM,
                current_position, drift_analysis,
                f"Large waves: {conditions.wave_height:.1f}m waves",
                "Monitor vessel motion and anchor holding in rough seas."
            )
            alerts.append(alert)
        
        # Strong current warning
        if conditions.current_speed > 1.5:  # 1.5 knots
            alert = await self._create_alert(
                deployment_id, AnchorAlertType.ENVIRONMENTAL_WARNING, AlertSeverity.MEDIUM,
                current_position, drift_analysis,
                f"Strong current: {conditions.current_speed:.1f} knots from {conditions.current_direction:.0f}°",
                "Strong current may affect anchor holding and vessel position."
            )
            alerts.append(alert)
        
        # Rapid pressure change (weather system approaching)
        if deployment_id in self.environmental_history and len(self.environmental_history[deployment_id]) >= 2:
            prev_conditions = self.environmental_history[deployment_id][-2]
            time_diff = (conditions.timestamp - prev_conditions.timestamp).total_seconds() / 3600  # hours
            if time_diff > 0:
                pressure_rate = (conditions.barometric_pressure - prev_conditions.barometric_pressure) / time_diff
                if abs(pressure_rate) > 3.0:  # 3 mb/hour change
                    alert = await self._create_alert(
                        deployment_id, AnchorAlertType.ENVIRONMENTAL_WARNING, AlertSeverity.MEDIUM,
                        current_position, drift_analysis,
                        f"Rapid barometric pressure change: {pressure_rate:+.1f} mb/hr",
                        "Weather system approaching. Monitor conditions closely."
                    )
                    alerts.append(alert)
        
        # Store alerts
        for alert in alerts:
            await self._store_alert(alert)
    
    async def _create_alert(self, deployment_id: str, alert_type: AnchorAlertType, 
                          severity: AlertSeverity, current_position: AnchorPosition,
                          drift_analysis: DriftAnalysis, message: str, 
                          recommended_action: str) -> AnchorAlert:
        """Create anchor alert"""
        
        # Get current environmental conditions
        env_conditions = None
        if (deployment_id in self.environmental_history and 
            self.environmental_history[deployment_id]):
            env_conditions = self.environmental_history[deployment_id][-1]
        
        if not env_conditions:
            # Create default environmental conditions
            env_conditions = EnvironmentalConditions(
                timestamp=datetime.utcnow(),
                wind_speed=0.0, wind_direction=0.0,
                current_speed=0.0, current_direction=0.0,
                wave_height=0.0, wave_period=0.0,
                tide_height=0.0, tide_rate=0.0,
                barometric_pressure=1013.25
            )
        
        alert_id = f"alert_{deployment_id}_{alert_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return AnchorAlert(
            alert_id=alert_id,
            deployment_id=deployment_id,
            alert_type=alert_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            current_position=current_position,
            drift_analysis=drift_analysis,
            environmental_conditions=env_conditions,
            message=message,
            recommended_action=recommended_action,
            acknowledged=False,
            resolved=False
        )
    
    async def _check_zone_breach(self, position: AnchorPosition, zone: AlertZone) -> bool:
        """Check if current position breaches alert zone"""
        point = Point(position.lon, position.lat)
        
        if zone.zone_type == "circle":
            return not zone.geometry.contains(point)
        elif zone.zone_type == "polygon":
            return not zone.geometry.contains(point)
        else:
            return False
    
    def create_circular_zone(self, center_lat: float, center_lon: float, 
                           radius_meters: float, zone_name: str) -> str:
        """Create circular alert zone"""
        zone_id = f"zone_circle_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Convert radius to degrees (approximate)
        radius_deg = radius_meters / 111000.0  # Rough conversion
        
        # Create circular geometry
        center_point = Point(center_lon, center_lat)
        circle = center_point.buffer(radius_deg)
        
        zone = AlertZone(
            zone_id=zone_id,
            zone_name=zone_name,
            zone_type="circle",
            geometry=circle,
            alert_threshold=radius_meters,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.alert_zones[zone_id] = zone
        return zone_id
    
    def create_polygon_zone(self, coordinates: List[Tuple[float, float]], 
                          zone_name: str) -> str:
        """Create polygonal alert zone"""
        zone_id = f"zone_polygon_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Create polygon geometry (coordinates as lon, lat)
        polygon_coords = [(lon, lat) for lat, lon in coordinates]
        polygon = Polygon(polygon_coords)
        
        zone = AlertZone(
            zone_id=zone_id,
            zone_name=zone_name,
            zone_type="polygon",
            geometry=polygon,
            alert_threshold=0.0,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.alert_zones[zone_id] = zone
        return zone_id
    
    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing from point 1 to point 2"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        
        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        return (bearing_deg + 360) % 360
    
    async def _store_deployment(self, deployment: AnchorDeployment):
        """Store anchor deployment in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO anchor_deployments 
            (deployment_id, vessel_name, anchor_type, chain_length, rope_length,
             anchor_weight, deployment_time, initial_lat, initial_lon, initial_depth,
             water_depth, seabed_type, scope_ratio, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            deployment.deployment_id, deployment.vessel_name, deployment.anchor_type,
            deployment.chain_length, deployment.rope_length, deployment.anchor_weight,
            deployment.deployment_time, deployment.initial_position.lat,
            deployment.initial_position.lon, deployment.initial_position.depth,
            deployment.water_depth, deployment.seabed_type.value,
            deployment.scope_ratio, deployment.notes
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_position(self, deployment_id: str, position: AnchorPosition):
        """Store position update in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO anchor_positions 
            (deployment_id, timestamp, lat, lon, heading, depth, position_accuracy,
             gps_quality, satellite_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            deployment_id, position.timestamp, position.lat, position.lon,
            position.heading, position.depth, position.accuracy,
            position.gps_quality, position.satellite_count
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_environmental_conditions(self, deployment_id: str, conditions: EnvironmentalConditions):
        """Store environmental conditions in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO environmental_conditions 
            (deployment_id, timestamp, wind_speed, wind_direction, current_speed,
             current_direction, wave_height, wave_period, tide_height, tide_rate,
             barometric_pressure)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            deployment_id, conditions.timestamp, conditions.wind_speed,
            conditions.wind_direction, conditions.current_speed,
            conditions.current_direction, conditions.wave_height,
            conditions.wave_period, conditions.tide_height,
            conditions.tide_rate, conditions.barometric_pressure
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_alert(self, alert: AnchorAlert):
        """Store alert in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO anchor_alerts 
            (alert_id, deployment_id, alert_type, severity, timestamp,
             current_lat, current_lon, drift_distance, drift_bearing,
             message, recommended_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.alert_id, alert.deployment_id, alert.alert_type.value,
            alert.severity.value, alert.timestamp, alert.current_position.lat,
            alert.current_position.lon, alert.drift_analysis.drift_distance,
            alert.drift_analysis.drift_bearing, alert.message, alert.recommended_action
        ))
        
        conn.commit()
        conn.close()
        
        # Print alert to console
        severity_emoji = {"info": "ℹ️", "low": "⚠️", "medium": "⚠️", "high": "🚨", "critical": "🚨"}
        print(f"\n{severity_emoji.get(alert.severity.value, '⚠️')} ANCHOR WATCH ALERT")
        print(f"Deployment: {alert.deployment_id}")
        print(f"Type: {alert.alert_type.value.replace('_', ' ').title()}")
        print(f"Severity: {alert.severity.value.upper()}")
        print(f"Message: {alert.message}")
        print(f"Action: {alert.recommended_action}")
        print(f"Time: {alert.timestamp}")
        print("=" * 50)
    
    async def get_active_alerts(self, deployment_id: Optional[str] = None) -> List[AnchorAlert]:
        """Get active alerts for deployment(s)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if deployment_id:
            cursor.execute("""
                SELECT * FROM anchor_alerts 
                WHERE deployment_id = ? AND resolved = FALSE
                ORDER BY severity DESC, timestamp DESC
            """, (deployment_id,))
        else:
            cursor.execute("""
                SELECT * FROM anchor_alerts 
                WHERE resolved = FALSE
                ORDER BY severity DESC, timestamp DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to AnchorAlert objects (simplified)
        alerts = []
        for row in rows:
            # This is a simplified conversion - in production, reconstruct full objects
            print(f"Alert: {row[2]} - {row[8]} ({row[3]})")
        
        return alerts
    
    async def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE anchor_alerts 
            SET acknowledged = TRUE 
            WHERE alert_id = ?
        """, (alert_id,))
        
        conn.commit()
        conn.close()
    
    async def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE anchor_alerts 
            SET resolved = TRUE, acknowledged = TRUE 
            WHERE alert_id = ?
        """, (alert_id,))
        
        conn.commit()
        conn.close()
    
    async def weigh_anchor(self, deployment_id: str):
        """End anchor watch session"""
        if deployment_id in self.active_deployments:
            del self.active_deployments[deployment_id]
        
        # Mark deployment as inactive
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE anchor_deployments 
            SET is_active = FALSE 
            WHERE deployment_id = ?
        """, (deployment_id,))
        
        conn.commit()
        conn.close()
        
        print(f"Anchor watch ended for deployment: {deployment_id}")
    
    def get_deployment_summary(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of anchor deployment"""
        if deployment_id not in self.active_deployments:
            return None
        
        deployment = self.active_deployments[deployment_id]
        positions = self.position_histories.get(deployment_id, [])
        
        if not positions:
            return None
        
        latest_position = positions[-1]
        
        # Calculate total drift
        total_drift = geodesic(
            (deployment.initial_position.lat, deployment.initial_position.lon),
            (latest_position.lat, latest_position.lon)
        ).meters
        
        # Calculate watch duration
        watch_duration = latest_position.timestamp - deployment.deployment_time
        
        return {
            'deployment_id': deployment_id,
            'vessel_name': deployment.vessel_name,
            'anchor_type': deployment.anchor_type,
            'deployment_time': deployment.deployment_time,
            'watch_duration': watch_duration,
            'current_position': (latest_position.lat, latest_position.lon),
            'initial_position': (deployment.initial_position.lat, deployment.initial_position.lon),
            'total_drift': total_drift,
            'scope_ratio': deployment.scope_ratio,
            'water_depth': deployment.water_depth,
            'position_count': len(positions),
            'active_zones': len([z for z in self.alert_zones.values() if z.is_active])
        }


async def main():
    """Example usage of anchor watch system"""
    
    # Initialize anchor watch system
    anchor_watch = AnchorWatchSystem("anchor_watch.db")
    
    print("ActiveLog Marine Advanced - Anchor Watch System Demo")
    print("=" * 55)
    
    # Create anchor deployment
    deployment = AnchorDeployment(
        deployment_id="deploy_001",
        vessel_name="SV SERENDIPITY",
        anchor_type="CQR 35lb",
        chain_length=50.0,   # 50 meters of chain
        rope_length=100.0,   # 100 meters of rode
        anchor_weight=16.0,  # 35 lbs = ~16 kg
        deployment_time=datetime.utcnow(),
        initial_position=AnchorPosition(
            timestamp=datetime.utcnow(),
            lat=37.7749,
            lon=-122.4194,
            heading=180.0,
            depth=12.0,
            position_accuracy=3.0,
            gps_quality=8,
            satellite_count=12
        ),
        water_depth=15.0,
        seabed_type=SeabedType.SAND,
        scope_ratio=10.0,  # 150m rode / 15m depth = 10:1 scope
        notes="Good holding in sand bottom, protected anchorage"
    )
    
    # Deploy anchor
    deployment_id = await anchor_watch.deploy_anchor(deployment)
    
    # Create safety zones
    zone_id = anchor_watch.create_circular_zone(
        center_lat=37.7749, 
        center_lon=-122.4194,
        radius_meters=200.0,
        zone_name="Swing Circle"
    )
    print(f"Created safety zone: {zone_id}")
    
    # Create danger zone (shipping channel)
    danger_zone = anchor_watch.create_polygon_zone(
        coordinates=[
            (37.7800, -122.4100),
            (37.7850, -122.4100),
            (37.7850, -122.4150),
            (37.7800, -122.4150)
        ],
        zone_name="Shipping Channel - No Anchor"
    )
    print(f"Created danger zone: {danger_zone}")
    
    print("\n" + "=" * 50)
    print("SIMULATING ANCHOR WATCH MONITORING")
    print("=" * 50)
    
    # Simulate position updates over time
    base_lat = 37.7749
    base_lon = -122.4194
    
    for hour in range(1, 13):  # 12 hours of monitoring
        # Simulate gradual drift
        drift_factor = hour * 0.00005  # Gradual increase in drift
        wind_factor = 0.00001 * (2 + math.sin(hour * 0.5))  # Variable wind
        
        new_lat = base_lat + drift_factor + wind_factor
        new_lon = base_lon + drift_factor * 0.5
        
        # Add some random variation
        new_lat += np.random.normal(0, 0.000005)
        new_lon += np.random.normal(0, 0.000005)
        
        position = AnchorPosition(
            timestamp=datetime.utcnow() + timedelta(hours=hour),
            lat=new_lat,
            lon=new_lon,
            heading=180.0 + np.random.normal(0, 10),
            depth=12.0 + np.random.normal(0, 0.5),
            position_accuracy=3.0 + np.random.normal(0, 1),
            gps_quality=8 + int(np.random.normal(0, 1)),
            satellite_count=12 + int(np.random.normal(0, 2))
        )
        
        # Update position
        drift_analysis = await anchor_watch.update_position(deployment_id, position)
        
        # Update environmental conditions
        conditions = EnvironmentalConditions(
            timestamp=position.timestamp,
            wind_speed=10 + 5 * math.sin(hour * 0.3) + np.random.normal(0, 2),
            wind_direction=225 + np.random.normal(0, 15),
            current_speed=0.5 + 0.3 * math.sin(hour * 0.2),
            current_direction=180 + np.random.normal(0, 20),
            wave_height=1.0 + 0.5 * math.sin(hour * 0.4),
            wave_period=6.0 + np.random.normal(0, 1),
            tide_height=2.0 + 1.5 * math.sin(hour * 0.52),  # ~12-hour tide cycle
            tide_rate=0.3 * math.cos(hour * 0.52),
            barometric_pressure=1015 + np.random.normal(0, 3)
        )
        
        await anchor_watch.update_environmental_conditions(deployment_id, conditions)
        
        # Print status update
        print(f"\nHour {hour:2d}: Position {position.lat:.6f}, {position.lon:.6f}")
        print(f"         Drift: {drift_analysis.drift_distance:.1f}m @ {drift_analysis.drift_bearing:.0f}°")
        print(f"         Rate: {drift_analysis.drift_rate:.1f} m/hr")
        print(f"         Max swing: {drift_analysis.max_swing_radius:.1f}m")
        print(f"         Wind: {conditions.wind_speed:.1f} kts @ {conditions.wind_direction:.0f}°")
        print(f"         Confidence: {drift_analysis.confidence_score:.3f}")
        
        # Simulate anchor drag at hour 8
        if hour == 8:
            print("\n🚨 SIMULATING ANCHOR DRAG EVENT...")
            drag_lat = base_lat + 0.0008  # Significant position change
            drag_lon = base_lon + 0.0005
            
            drag_position = AnchorPosition(
                timestamp=datetime.utcnow() + timedelta(hours=hour, minutes=30),
                lat=drag_lat,
                lon=drag_lon,
                heading=190.0,
                depth=18.0,  # Deeper water
                position_accuracy=2.0,
                gps_quality=9,
                satellite_count=13
            )
            
            await anchor_watch.update_position(deployment_id, drag_position)
    
    print("\n" + "=" * 50)
    print("ANCHOR WATCH SESSION SUMMARY")
    print("=" * 50)
    
    # Get deployment summary
    summary = anchor_watch.get_deployment_summary(deployment_id)
    if summary:
        print(f"Vessel: {summary['vessel_name']}")
        print(f"Anchor Type: {summary['anchor_type']}")
        print(f"Watch Duration: {summary['watch_duration']}")
        print(f"Total Drift: {summary['total_drift']:.1f} meters")
        print(f"Scope Ratio: {summary['scope_ratio']:.1f}:1")
        print(f"Water Depth: {summary['water_depth']}m")
        print(f"Position Updates: {summary['position_count']}")
        print(f"Active Alert Zones: {summary['active_zones']}")
    
    # Show active alerts
    print(f"\nActive Alerts:")
    await anchor_watch.get_active_alerts(deployment_id)
    
    # End anchor watch
    print(f"\nEnding anchor watch session...")
    await anchor_watch.weigh_anchor(deployment_id)


if __name__ == "__main__":
    asyncio.run(main())