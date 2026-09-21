"""
AIS Target Tracking and Collision Prediction System
Professional ARPA-style target tracking with CPA/TCPA calculations
"""

import logging
import json
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
import threading
import time
import math
import socket
import struct
from collections import deque
import pynmea2
from geopy.distance import geodesic
from geopy import distance

logger = logging.getLogger(__name__)

class AISMessageType(Enum):
    POSITION_REPORT_A = 1
    POSITION_REPORT_B = 2  
    POSITION_REPORT_C = 3
    BASE_STATION_REPORT = 4
    STATIC_VOYAGE_DATA = 5
    BINARY_ADDRESSED = 6
    BINARY_ACKNOWLEDGMENT = 7
    BINARY_BROADCAST = 8
    UTC_DATE_INQUIRY = 9
    UTC_DATE_RESPONSE = 10
    ADDRESSED_SAFETY = 12
    SAFETY_ACKNOWLEDGMENT = 13
    BROADCAST_SAFETY = 14
    INTERROGATION = 15
    ASSIGNMENT_MODE = 16
    DGNSS_BROADCAST = 17
    STANDARD_CLASS_B = 18
    EXTENDED_CLASS_B = 19
    DATA_LINK_MANAGEMENT = 20
    AID_TO_NAVIGATION = 21
    CHANNEL_MANAGEMENT = 22
    GROUP_ASSIGNMENT = 23
    STATIC_DATA_REPORT = 24
    SINGLE_SLOT_BINARY = 25
    MULTIPLE_SLOT_BINARY = 26
    LONG_RANGE_AIS = 27

class VesselType(Enum):
    UNKNOWN = 0
    FISHING = 30
    TOWING = 31
    DREDGING = 33
    DIVING = 34
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
    RESTRICTED_MANEUVERABILITY = 3
    CONSTRAINED_BY_DRAUGHT = 4
    MOORED = 5
    AGROUND = 6
    ENGAGED_IN_FISHING = 7
    UNDER_WAY_SAILING = 8
    AIS_SART = 14
    UNDEFINED = 15

@dataclass
class AISTarget:
    mmsi: int
    call_sign: str = ""
    vessel_name: str = ""
    vessel_type: VesselType = VesselType.UNKNOWN
    
    # Position data
    latitude: float = 0.0
    longitude: float = 0.0
    position_accuracy: bool = False
    
    # Motion data
    sog: float = 0.0  # Speed over ground (knots)
    cog: float = 0.0  # Course over ground (degrees)
    true_heading: float = 0.0  # True heading (degrees)
    rate_of_turn: float = 0.0  # Rate of turn (degrees/minute)
    
    # Status
    nav_status: NavigationStatus = NavigationStatus.UNDEFINED
    maneuver_indicator: int = 0
    
    # Vessel dimensions
    to_bow: int = 0
    to_stern: int = 0
    to_port: int = 0
    to_starboard: int = 0
    
    # Timestamps
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Tracking data
    position_history: deque = field(default_factory=lambda: deque(maxlen=100))
    speed_history: deque = field(default_factory=lambda: deque(maxlen=50))
    course_history: deque = field(default_factory=lambda: deque(maxlen=50))
    
    # ARPA calculations
    cpa_distance: Optional[float] = None  # Closest Point of Approach (nautical miles)
    tcpa_time: Optional[float] = None     # Time to CPA (minutes)
    bcr: Optional[float] = None           # Bearing Change Rate (degrees/minute)
    bcpa: Optional[float] = None          # Bearing at CPA (degrees)
    
    # Risk assessment
    collision_risk: str = "safe"  # safe, caution, warning, danger
    risk_score: float = 0.0       # 0.0 to 1.0
    
    # Display properties
    selected: bool = False
    tracked: bool = False
    lost: bool = False

@dataclass
class CollisionRisk:
    target_mmsi: int
    risk_level: str  # safe, caution, warning, danger
    risk_score: float
    cpa_distance: float
    tcpa_time: float
    recommended_action: str
    description: str

class AISTracker:
    """
    Professional AIS target tracking system with collision prediction
    Implements ARPA-style calculations and risk assessment
    """
    
    def __init__(self):
        self.targets: Dict[int, AISTarget] = {}
        self.own_vessel: Optional[Dict[str, float]] = None
        self.tracking_lock = threading.RLock()
        
        # Tracking parameters
        self.max_target_age = 300  # 5 minutes
        self.position_smoothing = True
        self.speed_smoothing = True
        self.course_smoothing = True
        
        # Risk assessment parameters
        self.safe_distance = 2.0        # nautical miles
        self.caution_distance = 1.0     # nautical miles  
        self.warning_distance = 0.5     # nautical miles
        self.danger_distance = 0.2      # nautical miles
        
        self.safe_time = 30.0          # minutes
        self.caution_time = 15.0       # minutes
        self.warning_time = 5.0        # minutes
        self.danger_time = 2.0         # minutes
        
        # AIS receiver
        self.ais_receiver_thread = None
        self.ais_port = 2101
        self.ais_host = "localhost"
        self.receiving_ais = False
        
        # Performance tracking
        self.message_count = 0
        self.error_count = 0
        self.last_message_time = None
        
        self._start_ais_receiver()
        logger.info("AIS Tracker initialized")
    
    def _start_ais_receiver(self):
        """Start AIS message receiver thread"""
        self.receiving_ais = True
        self.ais_receiver_thread = threading.Thread(target=self._ais_receiver_loop, daemon=True)
        self.ais_receiver_thread.start()
    
    def _ais_receiver_loop(self):
        """Main AIS message receiver loop"""
        while self.receiving_ais:
            try:
                # Try to connect to AIS data source
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((self.ais_host, self.ais_port))
                
                logger.info(f"Connected to AIS source: {self.ais_host}:{self.ais_port}")
                
                buffer = b""
                while self.receiving_ais:
                    try:
                        data = sock.recv(4096)
                        if not data:
                            break
                        
                        buffer += data
                        
                        # Process complete NMEA sentences
                        while b'\r\n' in buffer:
                            line, buffer = buffer.split(b'\r\n', 1)
                            try:
                                sentence = line.decode('ascii', errors='ignore')
                                if sentence.startswith('!AIVDM') or sentence.startswith('!AIVDO'):
                                    self._process_ais_sentence(sentence)
                            except Exception as e:
                                self.error_count += 1
                                logger.debug(f"AIS sentence error: {e}")
                    
                    except socket.timeout:
                        continue
                    except Exception as e:
                        logger.error(f"AIS receiver error: {e}")
                        break
                
                sock.close()
                
            except Exception as e:
                logger.warning(f"AIS connection failed: {e}")
                time.sleep(10)  # Wait before retry
    
    def _process_ais_sentence(self, sentence: str):
        """Process NMEA AIS sentence"""
        try:
            msg = pynmea2.parse(sentence)
            if hasattr(msg, 'payload'):
                decoded = self._decode_ais_payload(msg.payload, msg.fill_bits)
                if decoded:
                    self._update_target_from_ais(decoded)
                    self.message_count += 1
                    self.last_message_time = datetime.now(timezone.utc)
                    
        except Exception as e:
            self.error_count += 1
            logger.debug(f"AIS processing error: {e}")
    
    def _decode_ais_payload(self, payload: str, fill_bits: int) -> Optional[Dict[str, Any]]:
        """Decode AIS binary payload"""
        try:
            # Convert 6-bit ASCII to binary
            binary_data = self._ais_6bit_to_binary(payload)
            if not binary_data:
                return None
            
            # Extract message type
            msg_type = int(binary_data[0:6], 2)
            
            if msg_type in [1, 2, 3]:
                return self._decode_position_report(binary_data)
            elif msg_type == 5:
                return self._decode_static_voyage_data(binary_data)
            elif msg_type == 18:
                return self._decode_class_b_position(binary_data)
            elif msg_type == 19:
                return self._decode_extended_class_b(binary_data)
            elif msg_type == 21:
                return self._decode_aid_to_navigation(binary_data)
            
            return None
            
        except Exception as e:
            logger.debug(f"AIS decode error: {e}")
            return None
    
    def _ais_6bit_to_binary(self, payload: str) -> str:
        """Convert AIS 6-bit encoded string to binary"""
        binary = ""
        for char in payload:
            # AIS uses 6-bit encoding with offset
            val = ord(char) - 48
            if val > 40:
                val -= 8
            binary += format(val, '06b')
        return binary
    
    def _decode_position_report(self, binary_data: str) -> Dict[str, Any]:
        """Decode AIS position report (messages 1, 2, 3)"""
        try:
            return {
                'msg_type': int(binary_data[0:6], 2),
                'mmsi': int(binary_data[8:38], 2),
                'nav_status': int(binary_data[38:42], 2),
                'rot': self._decode_rot(int(binary_data[42:50], 2)),
                'sog': int(binary_data[50:60], 2) / 10.0,
                'position_accuracy': bool(int(binary_data[60:61], 2)),
                'longitude': self._decode_longitude(int(binary_data[61:89], 2)),
                'latitude': self._decode_latitude(int(binary_data[89:116], 2)),
                'cog': int(binary_data[116:128], 2) / 10.0,
                'true_heading': int(binary_data[128:137], 2),
                'timestamp': int(binary_data[137:143], 2),
                'maneuver': int(binary_data[143:145], 2)
            }
        except Exception as e:
            logger.debug(f"Position decode error: {e}")
            return None
    
    def _decode_static_voyage_data(self, binary_data: str) -> Dict[str, Any]:
        """Decode AIS static and voyage data (message 5)"""
        try:
            return {
                'msg_type': 5,
                'mmsi': int(binary_data[8:38], 2),
                'imo': int(binary_data[40:70], 2),
                'call_sign': self._decode_ais_string(binary_data[70:112]),
                'vessel_name': self._decode_ais_string(binary_data[112:232]),
                'vessel_type': int(binary_data[232:240], 2),
                'to_bow': int(binary_data[240:249], 2),
                'to_stern': int(binary_data[249:258], 2),
                'to_port': int(binary_data[258:264], 2),
                'to_starboard': int(binary_data[264:270], 2),
                'draught': int(binary_data[294:302], 2) / 10.0
            }
        except Exception as e:
            logger.debug(f"Static data decode error: {e}")
            return None
    
    def _decode_class_b_position(self, binary_data: str) -> Dict[str, Any]:
        """Decode Class B position report (message 18)"""
        try:
            return {
                'msg_type': 18,
                'mmsi': int(binary_data[8:38], 2),
                'sog': int(binary_data[46:56], 2) / 10.0,
                'position_accuracy': bool(int(binary_data[56:57], 2)),
                'longitude': self._decode_longitude(int(binary_data[57:85], 2)),
                'latitude': self._decode_latitude(int(binary_data[85:112], 2)),
                'cog': int(binary_data[112:124], 2) / 10.0,
                'true_heading': int(binary_data[124:133], 2)
            }
        except Exception as e:
            logger.debug(f"Class B decode error: {e}")
            return None
    
    def _decode_rot(self, rot_raw: int) -> float:
        """Decode rate of turn"""
        if rot_raw == 128:  # Not available
            return 0.0
        elif rot_raw == 127:  # Turning right at more than 5°/30s
            return 127.0
        elif rot_raw == 129:  # Turning left at more than 5°/30s
            return -127.0
        else:
            # Convert to degrees per minute
            return (rot_raw / 4.733) ** 2 * (1 if rot_raw > 0 else -1)
    
    def _decode_longitude(self, lon_raw: int) -> float:
        """Decode longitude from AIS format"""
        if lon_raw == 0x6791AC0:  # Not available
            return 0.0
        
        # Convert from 1/600000 minute precision
        if lon_raw & 0x8000000:  # Negative
            lon_raw = lon_raw - 0x10000000
        
        return lon_raw / 600000.0
    
    def _decode_latitude(self, lat_raw: int) -> float:
        """Decode latitude from AIS format"""
        if lat_raw == 0x3412140:  # Not available
            return 0.0
        
        # Convert from 1/600000 minute precision
        if lat_raw & 0x4000000:  # Negative
            lat_raw = lat_raw - 0x8000000
        
        return lat_raw / 600000.0
    
    def _decode_ais_string(self, binary_data: str) -> str:
        """Decode AIS text string"""
        text = ""
        for i in range(0, len(binary_data), 6):
            if i + 6 <= len(binary_data):
                char_val = int(binary_data[i:i+6], 2)
                if char_val == 0:  # End of string
                    break
                if char_val < 32:
                    char_val += 64
                text += chr(char_val)
        
        return text.rstrip()
    
    def _update_target_from_ais(self, ais_data: Dict[str, Any]):
        """Update target from decoded AIS data"""
        mmsi = ais_data.get('mmsi')
        if not mmsi:
            return
        
        with self.tracking_lock:
            # Get or create target
            if mmsi not in self.targets:
                self.targets[mmsi] = AISTarget(mmsi=mmsi)
                logger.info(f"New AIS target: {mmsi}")
            
            target = self.targets[mmsi]
            
            # Update position data
            if 'latitude' in ais_data and 'longitude' in ais_data:
                old_lat, old_lon = target.latitude, target.longitude
                target.latitude = ais_data['latitude']
                target.longitude = ais_data['longitude']
                target.position_accuracy = ais_data.get('position_accuracy', False)
                
                # Add to position history
                if old_lat != 0 or old_lon != 0:  # Not first position
                    target.position_history.append({
                        'timestamp': target.last_update,
                        'lat': old_lat,
                        'lon': old_lon
                    })
            
            # Update motion data
            if 'sog' in ais_data:
                target.speed_history.append({
                    'timestamp': target.last_update,
                    'speed': target.sog
                })
                target.sog = ais_data['sog']
            
            if 'cog' in ais_data:
                target.course_history.append({
                    'timestamp': target.last_update,
                    'course': target.cog
                })
                target.cog = ais_data['cog']
            
            if 'true_heading' in ais_data:
                target.true_heading = ais_data['true_heading']
            
            if 'rot' in ais_data:
                target.rate_of_turn = ais_data['rot']
            
            # Update status
            if 'nav_status' in ais_data:
                try:
                    target.nav_status = NavigationStatus(ais_data['nav_status'])
                except ValueError:
                    target.nav_status = NavigationStatus.UNDEFINED
            
            # Update static data
            if 'vessel_name' in ais_data:
                target.vessel_name = ais_data['vessel_name']
            
            if 'call_sign' in ais_data:
                target.call_sign = ais_data['call_sign']
            
            if 'vessel_type' in ais_data:
                try:
                    target.vessel_type = VesselType(ais_data['vessel_type'])
                except ValueError:
                    target.vessel_type = VesselType.UNKNOWN
            
            # Update dimensions
            for dim in ['to_bow', 'to_stern', 'to_port', 'to_starboard']:
                if dim in ais_data:
                    setattr(target, dim, ais_data[dim])
            
            target.last_update = datetime.now(timezone.utc)
            target.lost = False
            
            # Perform tracking calculations
            self._calculate_target_motion(target)
    
    def _calculate_target_motion(self, target: AISTarget):
        """Calculate smoothed motion parameters and predictions"""
        if len(target.position_history) < 2:
            return
        
        try:
            # Calculate smoothed speed and course
            if self.speed_smoothing and len(target.speed_history) >= 3:
                recent_speeds = [s['speed'] for s in list(target.speed_history)[-3:]]
                target.sog = sum(recent_speeds) / len(recent_speeds)
            
            if self.course_smoothing and len(target.course_history) >= 3:
                recent_courses = [c['course'] for c in list(target.course_history)[-3:]]
                target.cog = self._average_courses(recent_courses)
            
        except Exception as e:
            logger.debug(f"Motion calculation error for {target.mmsi}: {e}")
    
    def _average_courses(self, courses: List[float]) -> float:
        """Average courses accounting for circular nature"""
        if not courses:
            return 0.0
        
        # Convert to radians and calculate average
        x = sum(math.cos(math.radians(c)) for c in courses)
        y = sum(math.sin(math.radians(c)) for c in courses)
        
        avg_radians = math.atan2(y, x)
        avg_degrees = math.degrees(avg_radians)
        
        return avg_degrees % 360
    
    def set_own_vessel(self, lat: float, lon: float, sog: float, cog: float, heading: float = None):
        """Update own vessel position and motion"""
        self.own_vessel = {
            'lat': lat,
            'lon': lon,
            'sog': sog,
            'cog': cog,
            'heading': heading or cog,
            'timestamp': datetime.now(timezone.utc)
        }
        
        # Calculate collision risks for all targets
        self._calculate_all_collision_risks()
    
    def _calculate_all_collision_risks(self):
        """Calculate collision risks for all active targets"""
        if not self.own_vessel:
            return
        
        with self.tracking_lock:
            for target in self.targets.values():
                if target.lost or target.latitude == 0:
                    continue
                
                self._calculate_cpa_tcpa(target)
                self._assess_collision_risk(target)
    
    def _calculate_cpa_tcpa(self, target: AISTarget):
        """Calculate Closest Point of Approach and Time to CPA"""
        if not self.own_vessel:
            return
        
        try:
            own_lat = self.own_vessel['lat']
            own_lon = self.own_vessel['lon']
            own_sog = self.own_vessel['sog']
            own_cog = self.own_vessel['cog']
            
            target_lat = target.latitude
            target_lon = target.longitude
            target_sog = target.sog
            target_cog = target.cog
            
            # Calculate relative motion vectors
            own_vel_x = own_sog * math.sin(math.radians(own_cog))
            own_vel_y = own_sog * math.cos(math.radians(own_cog))
            
            target_vel_x = target_sog * math.sin(math.radians(target_cog))
            target_vel_y = target_sog * math.cos(math.radians(target_cog))
            
            # Relative velocity
            rel_vel_x = target_vel_x - own_vel_x
            rel_vel_y = target_vel_y - own_vel_y
            rel_speed = math.sqrt(rel_vel_x**2 + rel_vel_y**2)
            
            if rel_speed < 0.1:  # Essentially same course and speed
                target.cpa_distance = geodesic(
                    (own_lat, own_lon), 
                    (target_lat, target_lon)
                ).nautical
                target.tcpa_time = float('inf')
                return
            
            # Current range and bearing
            current_range = geodesic(
                (own_lat, own_lon),
                (target_lat, target_lon)
            ).nautical
            
            current_bearing = distance.bearing((own_lat, own_lon), (target_lat, target_lon))
            
            # Relative position components
            range_x = current_range * math.sin(math.radians(current_bearing))
            range_y = current_range * math.cos(math.radians(current_bearing))
            
            # Time to CPA
            tcpa_hours = -(range_x * rel_vel_x + range_y * rel_vel_y) / (rel_speed**2)
            target.tcpa_time = tcpa_hours * 60  # Convert to minutes
            
            # CPA distance
            if tcpa_hours < 0:
                # CPA is in the past
                target.cpa_distance = current_range
            else:
                # Future CPA position
                cpa_x = range_x + rel_vel_x * tcpa_hours
                cpa_y = range_y + rel_vel_y * tcpa_hours
                target.cpa_distance = math.sqrt(cpa_x**2 + cpa_y**2)
            
            # Bearing at CPA
            if target.cpa_distance > 0:
                target.bcpa = math.degrees(math.atan2(cpa_x, cpa_y)) % 360
            
        except Exception as e:
            logger.debug(f"CPA/TCPA calculation error for {target.mmsi}: {e}")
            target.cpa_distance = None
            target.tcpa_time = None
    
    def _assess_collision_risk(self, target: AISTarget):
        """Assess collision risk level for target"""
        if target.cpa_distance is None or target.tcpa_time is None:
            target.collision_risk = "safe"
            target.risk_score = 0.0
            return
        
        # Distance risk factor
        if target.cpa_distance <= self.danger_distance:
            distance_risk = 1.0
        elif target.cpa_distance <= self.warning_distance:
            distance_risk = 0.8
        elif target.cpa_distance <= self.caution_distance:
            distance_risk = 0.5
        elif target.cpa_distance <= self.safe_distance:
            distance_risk = 0.3
        else:
            distance_risk = 0.1
        
        # Time risk factor
        if 0 < target.tcpa_time <= self.danger_time:
            time_risk = 1.0
        elif target.tcpa_time <= self.warning_time:
            time_risk = 0.8
        elif target.tcpa_time <= self.caution_time:
            time_risk = 0.5
        elif target.tcpa_time <= self.safe_time:
            time_risk = 0.3
        else:
            time_risk = 0.1
        
        # Combined risk score
        target.risk_score = max(distance_risk, time_risk)
        
        # Determine risk level
        if target.risk_score >= 0.8:
            target.collision_risk = "danger"
        elif target.risk_score >= 0.6:
            target.collision_risk = "warning"
        elif target.risk_score >= 0.4:
            target.collision_risk = "caution"
        else:
            target.collision_risk = "safe"
    
    def get_active_targets(self, max_age_seconds: int = None) -> List[Dict[str, Any]]:
        """Get list of active AIS targets"""
        if max_age_seconds is None:
            max_age_seconds = self.max_target_age
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
        active_targets = []
        
        with self.tracking_lock:
            for target in self.targets.values():
                if target.last_update < cutoff_time:
                    target.lost = True
                    continue
                
                active_targets.append({
                    'mmsi': target.mmsi,
                    'call_sign': target.call_sign,
                    'vessel_name': target.vessel_name,
                    'vessel_type': target.vessel_type.value,
                    'lat': target.latitude,
                    'lon': target.longitude,
                    'sog': target.sog,
                    'cog': target.cog,
                    'heading': target.true_heading,
                    'nav_status': target.nav_status.value,
                    'last_update': target.last_update.isoformat(),
                    'collision_risk': target.collision_risk,
                    'risk_score': target.risk_score,
                    'cpa_distance': target.cpa_distance,
                    'tcpa_time': target.tcpa_time
                })
        
        return active_targets
    
    def calculate_collision_risks(self, own_vessel_pos: Dict[str, float]) -> List[CollisionRisk]:
        """Calculate collision risks for current situation"""
        if own_vessel_pos:
            self.set_own_vessel(
                own_vessel_pos['lat'],
                own_vessel_pos['lon'],
                own_vessel_pos.get('speed', 0.0),
                own_vessel_pos.get('heading', 0.0)
            )
        
        risks = []
        
        with self.tracking_lock:
            for target in self.targets.values():
                if (target.lost or target.collision_risk == "safe" or 
                    target.cpa_distance is None):
                    continue
                
                # Generate recommended action
                action = self._generate_collision_avoidance_action(target)
                
                risks.append(CollisionRisk(
                    target_mmsi=target.mmsi,
                    risk_level=target.collision_risk,
                    risk_score=target.risk_score,
                    cpa_distance=target.cpa_distance,
                    tcpa_time=target.tcpa_time,
                    recommended_action=action,
                    description=f"Target {target.vessel_name or target.mmsi}: "
                              f"CPA {target.cpa_distance:.2f}nm in {target.tcpa_time:.1f}min"
                ))
        
        # Sort by risk level
        risk_order = {"danger": 4, "warning": 3, "caution": 2, "safe": 1}
        risks.sort(key=lambda r: risk_order.get(r.risk_level, 0), reverse=True)
        
        return risks
    
    def _generate_collision_avoidance_action(self, target: AISTarget) -> str:
        """Generate collision avoidance recommendation"""
        if not self.own_vessel or target.cpa_distance is None:
            return "Monitor target"
        
        if target.collision_risk == "danger":
            # Immediate action required
            if target.cpa_distance < 0.1:
                return "IMMEDIATE EVASIVE ACTION - Turn hard to starboard"
            else:
                return "Alter course to starboard and reduce speed"
        
        elif target.collision_risk == "warning":
            return "Alter course or speed to increase CPA"
        
        elif target.collision_risk == "caution":
            return "Monitor closely and prepare to maneuver"
        
        return "Continue monitoring"
    
    def get_target_details(self, mmsi: int) -> Optional[Dict[str, Any]]:
        """Get detailed information for specific target"""
        if mmsi not in self.targets:
            return None
        
        target = self.targets[mmsi]
        
        return {
            'mmsi': target.mmsi,
            'call_sign': target.call_sign,
            'vessel_name': target.vessel_name,
            'vessel_type': target.vessel_type.name,
            'position': {'lat': target.latitude, 'lon': target.longitude},
            'motion': {
                'sog': target.sog,
                'cog': target.cog,
                'heading': target.true_heading,
                'rot': target.rate_of_turn
            },
            'dimensions': {
                'to_bow': target.to_bow,
                'to_stern': target.to_stern,
                'to_port': target.to_port,
                'to_starboard': target.to_starboard
            },
            'nav_status': target.nav_status.name,
            'collision_data': {
                'risk_level': target.collision_risk,
                'risk_score': target.risk_score,
                'cpa_distance': target.cpa_distance,
                'tcpa_time': target.tcpa_time,
                'bcpa': target.bcpa
            },
            'timestamps': {
                'first_seen': target.first_seen.isoformat(),
                'last_update': target.last_update.isoformat()
            },
            'tracking': {
                'selected': target.selected,
                'tracked': target.tracked,
                'lost': target.lost
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get AIS tracker statistics"""
        with self.tracking_lock:
            active_count = sum(1 for t in self.targets.values() if not t.lost)
            
            risk_counts = {
                'danger': sum(1 for t in self.targets.values() 
                            if t.collision_risk == 'danger' and not t.lost),
                'warning': sum(1 for t in self.targets.values() 
                             if t.collision_risk == 'warning' and not t.lost),
                'caution': sum(1 for t in self.targets.values() 
                             if t.collision_risk == 'caution' and not t.lost),
                'safe': sum(1 for t in self.targets.values() 
                          if t.collision_risk == 'safe' and not t.lost)
            }
        
        return {
            'total_targets': len(self.targets),
            'active_targets': active_count,
            'lost_targets': len(self.targets) - active_count,
            'risk_counts': risk_counts,
            'message_count': self.message_count,
            'error_count': self.error_count,
            'last_message': self.last_message_time.isoformat() if self.last_message_time else None,
            'receiving_ais': self.receiving_ais
        }