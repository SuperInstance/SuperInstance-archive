"""
ARPA Radar Overlay System
Professional radar target tracking with ARPA calculations and overlay management
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
# import cv2
# from scipy import ndimage
# from scipy.spatial.distance import euclidean
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge

logger = logging.getLogger(__name__)

class RadarMode(Enum):
    STANDBY = "standby"
    TRANSMIT = "transmit"
    RECEIVE = "receive"
    ARPA = "arpa"
    MARPA = "marpa"  # Manual ARPA

class RadarRange(Enum):
    RANGE_0_125 = 0.125
    RANGE_0_25 = 0.25
    RANGE_0_5 = 0.5
    RANGE_0_75 = 0.75
    RANGE_1_5 = 1.5
    RANGE_3 = 3.0
    RANGE_6 = 6.0
    RANGE_12 = 12.0
    RANGE_24 = 24.0
    RANGE_48 = 48.0
    RANGE_96 = 96.0

class TargetType(Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    REFERENCE = "reference"
    DANGEROUS = "dangerous"
    LOST = "lost"

class TargetStatus(Enum):
    ACQUIRING = "acquiring"
    TRACKING = "tracking"
    COASTING = "coasting"
    LOST = "lost"

@dataclass
class RadarEcho:
    azimuth: float  # degrees
    range_nm: float  # nautical miles
    strength: float  # signal strength 0-1
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class RadarTarget:
    target_id: int
    target_type: TargetType
    status: TargetStatus
    
    # Current position (polar coordinates)
    bearing: float = 0.0  # degrees true
    range_nm: float = 0.0  # nautical miles
    
    # Cartesian position relative to own vessel
    x_position: float = 0.0  # nautical miles
    y_position: float = 0.0  # nautical miles
    
    # Motion vectors
    speed: float = 0.0  # knots
    course: float = 0.0  # degrees true
    heading: float = 0.0  # degrees true
    
    # ARPA calculations
    cpa_distance: Optional[float] = None  # nautical miles
    tcpa_time: Optional[float] = None     # minutes
    bcr: Optional[float] = None           # bearing change rate
    
    # Target history
    position_history: deque = field(default_factory=lambda: deque(maxlen=50))
    echo_history: deque = field(default_factory=lambda: deque(maxlen=10))
    
    # Tracking quality
    track_quality: float = 0.0  # 0-1, quality of track
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acquisition_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Display properties
    selected: bool = False
    symbol_type: str = "triangle"
    trail_length: int = 10

@dataclass
class RadarConfig:
    antenna_height: float = 10.0  # meters above sea level
    antenna_gain: float = 28.0    # dB
    transmit_power: float = 25.0  # kW
    pulse_length: float = 0.08    # microseconds
    frequency: float = 9.4        # GHz (X-band)
    horizontal_beamwidth: float = 1.2  # degrees
    
    # Processing parameters
    sea_clutter_level: float = 0.5
    rain_clutter_level: float = 0.3
    interference_rejection: bool = True
    fast_time_constant: float = 0.5
    
    # ARPA parameters
    min_target_size: float = 50   # square meters RCS
    acquisition_threshold: float = 0.6
    tracking_threshold: float = 0.4
    lost_target_timeout: int = 30  # seconds

class ARPARadar:
    """
    Professional ARPA radar system with target tracking and collision prediction
    Implements IMO ARPA performance standards
    """
    
    def __init__(self):
        self.config = RadarConfig()
        self.mode = RadarMode.STANDBY
        self.current_range = RadarRange.RANGE_6
        
        # Radar data
        self.sweep_data = {}  # azimuth -> echo data
        self.targets: Dict[int, RadarTarget] = {}
        self.next_target_id = 1
        
        # Own vessel data
        self.own_position = {"lat": 0.0, "lon": 0.0, "heading": 0.0, "speed": 0.0}
        self.stabilization_mode = "head_up"  # head_up, north_up, course_up
        
        # Radar receiver
        self.radar_lock = threading.RLock()
        self.radar_thread = None
        self.receiving_radar = False
        self.radar_port = 2102
        self.radar_host = "localhost"
        
        # Performance tracking
        self.sweep_count = 0
        self.target_count = 0
        self.last_sweep_time = None
        self.rpm = 24  # antenna RPM
        
        # Processing parameters
        self.correlation_threshold = 0.8
        self.max_targets = 100
        self.track_initiation_threshold = 3  # number of plots needed
        
        self._start_radar_receiver()
        logger.info("ARPA Radar system initialized")
    
    def _start_radar_receiver(self):
        """Start radar data receiver thread"""
        self.receiving_radar = True
        self.radar_thread = threading.Thread(target=self._radar_receiver_loop, daemon=True)
        self.radar_thread.start()
    
    def _radar_receiver_loop(self):
        """Main radar data receiver loop"""
        while self.receiving_radar:
            try:
                # Simulate radar data reception
                # In production this would connect to actual radar hardware
                self._simulate_radar_sweep()
                
                # Process received data
                self._process_radar_data()
                
                # Update ARPA tracks
                self._update_arpa_tracks()
                
                time.sleep(2.5)  # 24 RPM = 2.5 seconds per revolution
                
            except Exception as e:
                logger.error(f"Radar receiver error: {e}")
                time.sleep(5)
    
    def _simulate_radar_sweep(self):
        """Simulate radar sweep data (for demonstration)"""
        # This would be replaced with actual radar hardware interface
        current_time = datetime.now(timezone.utc)
        
        # Generate simulated echoes
        simulated_echoes = []
        
        # Add some random targets
        for _ in range(np.random.randint(3, 8)):
            azimuth = np.random.uniform(0, 360)
            range_nm = np.random.uniform(0.5, float(self.current_range.value))
            strength = np.random.uniform(0.3, 1.0)
            
            echo = RadarEcho(
                azimuth=azimuth,
                range_nm=range_nm,
                strength=strength,
                timestamp=current_time
            )
            simulated_echoes.append(echo)
        
        # Store sweep data
        with self.radar_lock:
            self.sweep_data[current_time] = simulated_echoes
            self.sweep_count += 1
            self.last_sweep_time = current_time
    
    def _process_radar_data(self):
        """Process radar sweep data and extract targets"""
        if not self.sweep_data:
            return
        
        try:
            latest_time = max(self.sweep_data.keys())
            echoes = self.sweep_data[latest_time]
            
            # Plot extraction and correlation
            for echo in echoes:
                if echo.strength > self.config.acquisition_threshold:
                    self._correlate_echo_with_tracks(echo)
            
            # Clean up old sweep data (keep last 10 sweeps)
            if len(self.sweep_data) > 10:
                oldest_times = sorted(self.sweep_data.keys())[:-10]
                for old_time in oldest_times:
                    del self.sweep_data[old_time]
                    
        except Exception as e:
            logger.error(f"Radar processing error: {e}")
    
    def _correlate_echo_with_tracks(self, echo: RadarEcho):
        """Correlate radar echo with existing tracks"""
        # Convert echo to Cartesian coordinates
        echo_x = echo.range_nm * math.sin(math.radians(echo.azimuth))
        echo_y = echo.range_nm * math.cos(math.radians(echo.azimuth))
        
        best_target = None
        best_distance = float('inf')
        correlation_gate = 0.1  # nautical miles
        
        # Find closest existing target
        with self.radar_lock:
            for target in self.targets.values():
                if target.status == TargetStatus.LOST:
                    continue
                
                # Predict target position based on last known motion
                time_diff = (echo.timestamp - target.last_update).total_seconds() / 3600  # hours
                
                predicted_x = target.x_position + (target.speed * math.sin(math.radians(target.course)) * time_diff)
                predicted_y = target.y_position + (target.speed * math.cos(math.radians(target.course)) * time_diff)
                
                distance = math.sqrt((echo_x - predicted_x)**2 + (echo_y - predicted_y)**2)
                
                if distance < correlation_gate and distance < best_distance:
                    best_target = target
                    best_distance = distance
            
            if best_target:
                # Update existing target
                self._update_target_with_echo(best_target, echo, echo_x, echo_y)
            else:
                # Create new target track
                self._initiate_new_track(echo, echo_x, echo_y)
    
    def _update_target_with_echo(self, target: RadarTarget, echo: RadarEcho, 
                                echo_x: float, echo_y: float):
        """Update existing target with new echo"""
        # Add old position to history
        target.position_history.append({
            'timestamp': target.last_update,
            'x': target.x_position,
            'y': target.y_position,
            'bearing': target.bearing,
            'range': target.range_nm
        })
        
        # Update current position
        target.x_position = echo_x
        target.y_position = echo_y
        target.bearing = echo.azimuth
        target.range_nm = echo.range_nm
        target.last_update = echo.timestamp
        
        # Add echo to history
        target.echo_history.append(echo)
        
        # Calculate motion vectors if we have enough history
        if len(target.position_history) >= 2:
            self._calculate_target_motion(target)
        
        # Update tracking quality
        target.track_quality = min(1.0, target.track_quality + 0.1)
        
        # Update status
        if target.status == TargetStatus.ACQUIRING:
            if len(target.echo_history) >= self.track_initiation_threshold:
                target.status = TargetStatus.TRACKING
        elif target.status == TargetStatus.COASTING:
            target.status = TargetStatus.TRACKING
    
    def _initiate_new_track(self, echo: RadarEcho, echo_x: float, echo_y: float):
        """Initiate new target track"""
        if len(self.targets) >= self.max_targets:
            return
        
        target_id = self.next_target_id
        self.next_target_id += 1
        
        target = RadarTarget(
            target_id=target_id,
            target_type=TargetType.AUTOMATIC,
            status=TargetStatus.ACQUIRING,
            bearing=echo.azimuth,
            range_nm=echo.range_nm,
            x_position=echo_x,
            y_position=echo_y
        )
        
        target.echo_history.append(echo)
        
        with self.radar_lock:
            self.targets[target_id] = target
        
        logger.info(f"New radar target initiated: {target_id}")
    
    def _calculate_target_motion(self, target: RadarTarget):
        """Calculate target speed and course from position history"""
        if len(target.position_history) < 2:
            return
        
        try:
            # Get last two positions
            pos1 = target.position_history[-2]
            pos2 = target.position_history[-1]
            
            # Calculate time difference in hours
            time_diff = (pos2['timestamp'] - pos1['timestamp']).total_seconds() / 3600
            if time_diff <= 0:
                return
            
            # Calculate distance moved
            dx = pos2['x'] - pos1['x']
            dy = pos2['y'] - pos1['y']
            distance = math.sqrt(dx**2 + dy**2)
            
            # Calculate speed (knots)
            target.speed = distance / time_diff
            
            # Calculate course (degrees)
            if distance > 0.01:  # Minimum movement threshold
                target.course = math.degrees(math.atan2(dx, dy)) % 360
            
            # Smooth motion parameters if we have more history
            if len(target.position_history) >= 5:
                self._smooth_target_motion(target)
                
        except Exception as e:
            logger.debug(f"Motion calculation error for target {target.target_id}: {e}")
    
    def _smooth_target_motion(self, target: RadarTarget):
        """Apply smoothing to target motion parameters"""
        if len(target.position_history) < 3:
            return
        
        # Get recent positions
        recent_positions = list(target.position_history)[-5:]
        
        # Calculate smoothed speed
        speeds = []
        for i in range(len(recent_positions) - 1):
            pos1 = recent_positions[i]
            pos2 = recent_positions[i + 1]
            
            time_diff = (pos2['timestamp'] - pos1['timestamp']).total_seconds() / 3600
            if time_diff > 0:
                dx = pos2['x'] - pos1['x']
                dy = pos2['y'] - pos1['y']
                distance = math.sqrt(dx**2 + dy**2)
                speed = distance / time_diff
                speeds.append(speed)
        
        if speeds:
            target.speed = sum(speeds) / len(speeds)
        
        # Calculate smoothed course
        courses = []
        for i in range(len(recent_positions) - 1):
            pos1 = recent_positions[i]
            pos2 = recent_positions[i + 1]
            
            dx = pos2['x'] - pos1['x']
            dy = pos2['y'] - pos1['y']
            
            if abs(dx) > 0.01 or abs(dy) > 0.01:
                course = math.degrees(math.atan2(dx, dy)) % 360
                courses.append(course)
        
        if courses:
            # Average courses (accounting for circular nature)
            x_avg = sum(math.cos(math.radians(c)) for c in courses)
            y_avg = sum(math.sin(math.radians(c)) for c in courses)
            target.course = math.degrees(math.atan2(y_avg, x_avg)) % 360
    
    def _update_arpa_tracks(self):
        """Update all ARPA track calculations"""
        current_time = datetime.now(timezone.utc)
        
        with self.radar_lock:
            targets_to_remove = []
            
            for target_id, target in self.targets.items():
                # Check if target is lost
                time_since_update = (current_time - target.last_update).total_seconds()
                
                if time_since_update > self.config.lost_target_timeout:
                    if target.status != TargetStatus.LOST:
                        target.status = TargetStatus.LOST
                        target.track_quality = max(0.0, target.track_quality - 0.2)
                        logger.info(f"Target {target_id} lost")
                
                # Remove very old lost targets
                if (target.status == TargetStatus.LOST and 
                    time_since_update > self.config.lost_target_timeout * 3):
                    targets_to_remove.append(target_id)
                    continue
                
                # Update CPA/TCPA calculations
                if target.status == TargetStatus.TRACKING:
                    self._calculate_target_cpa_tcpa(target)
            
            # Remove old targets
            for target_id in targets_to_remove:
                del self.targets[target_id]
    
    def _calculate_target_cpa_tcpa(self, target: RadarTarget):
        """Calculate CPA and TCPA for ARPA target"""
        if target.speed < 0.1:  # Target not moving
            target.cpa_distance = target.range_nm
            target.tcpa_time = float('inf')
            return
        
        try:
            own_speed = self.own_position.get('speed', 0.0)
            own_course = self.own_position.get('heading', 0.0)
            
            # Own vessel velocity components
            own_vx = own_speed * math.sin(math.radians(own_course))
            own_vy = own_speed * math.cos(math.radians(own_course))
            
            # Target velocity components
            target_vx = target.speed * math.sin(math.radians(target.course))
            target_vy = target.speed * math.cos(math.radians(target.course))
            
            # Relative velocity
            rel_vx = target_vx - own_vx
            rel_vy = target_vy - own_vy
            rel_speed = math.sqrt(rel_vx**2 + rel_vy**2)
            
            if rel_speed < 0.1:  # No relative motion
                target.cpa_distance = target.range_nm
                target.tcpa_time = float('inf')
                return
            
            # Current relative position
            rel_x = target.x_position
            rel_y = target.y_position
            
            # Time to CPA
            tcpa_hours = -(rel_x * rel_vx + rel_y * rel_vy) / (rel_speed**2)
            target.tcpa_time = tcpa_hours * 60  # Convert to minutes
            
            # CPA distance
            if tcpa_hours < 0:
                # CPA in the past
                target.cpa_distance = target.range_nm
            else:
                # Calculate CPA position
                cpa_x = rel_x + rel_vx * tcpa_hours
                cpa_y = rel_y + rel_vy * tcpa_hours
                target.cpa_distance = math.sqrt(cpa_x**2 + cpa_y**2)
            
            # Bearing change rate
            if len(target.position_history) >= 2:
                recent_bearings = [p['bearing'] for p in list(target.position_history)[-5:]]
                recent_times = [p['timestamp'] for p in list(target.position_history)[-5:]]
                
                if len(recent_bearings) >= 2:
                    bearing_changes = []
                    for i in range(len(recent_bearings) - 1):
                        db = recent_bearings[i+1] - recent_bearings[i]
                        # Handle bearing wrap-around
                        if db > 180:
                            db -= 360
                        elif db < -180:
                            db += 360
                        
                        dt = (recent_times[i+1] - recent_times[i]).total_seconds() / 60  # minutes
                        if dt > 0:
                            bearing_changes.append(db / dt)
                    
                    if bearing_changes:
                        target.bcr = sum(bearing_changes) / len(bearing_changes)
                        
        except Exception as e:
            logger.debug(f"CPA/TCPA calculation error for target {target.target_id}: {e}")
    
    def set_own_vessel_data(self, lat: float, lon: float, heading: float, speed: float):
        """Update own vessel position and motion"""
        self.own_position = {
            'lat': lat,
            'lon': lon,
            'heading': heading,
            'speed': speed
        }
    
    def set_range(self, range_nm: float):
        """Set radar range"""
        for radar_range in RadarRange:
            if radar_range.value == range_nm:
                self.current_range = radar_range
                logger.info(f"Radar range set to {range_nm} nm")
                return True
        
        logger.warning(f"Invalid radar range: {range_nm}")
        return False
    
    def set_mode(self, mode: str):
        """Set radar operating mode"""
        try:
            self.mode = RadarMode(mode)
            logger.info(f"Radar mode set to {mode}")
            return True
        except ValueError:
            logger.warning(f"Invalid radar mode: {mode}")
            return False
    
    def acquire_target(self, bearing: float, range_nm: float) -> Optional[int]:
        """Manually acquire target at specified position"""
        # Convert to Cartesian coordinates
        x = range_nm * math.sin(math.radians(bearing))
        y = range_nm * math.cos(math.radians(bearing))
        
        target_id = self.next_target_id
        self.next_target_id += 1
        
        target = RadarTarget(
            target_id=target_id,
            target_type=TargetType.MANUAL,
            status=TargetStatus.ACQUIRING,
            bearing=bearing,
            range_nm=range_nm,
            x_position=x,
            y_position=y
        )
        
        with self.radar_lock:
            self.targets[target_id] = target
        
        logger.info(f"Manual target acquisition: {target_id} at {bearing}° / {range_nm}nm")
        return target_id
    
    def drop_target(self, target_id: int) -> bool:
        """Drop/delete target track"""
        with self.radar_lock:
            if target_id in self.targets:
                del self.targets[target_id]
                logger.info(f"Target dropped: {target_id}")
                return True
        
        return False
    
    def select_target(self, target_id: int) -> bool:
        """Select target for detailed display"""
        with self.radar_lock:
            if target_id in self.targets:
                # Deselect all other targets
                for target in self.targets.values():
                    target.selected = False
                
                # Select specified target
                self.targets[target_id].selected = True
                return True
        
        return False
    
    def get_processed_data(self) -> Dict[str, Any]:
        """Get processed radar data for display"""
        with self.radar_lock:
            targets_data = []
            
            for target in self.targets.values():
                if target.status == TargetStatus.LOST:
                    continue
                
                targets_data.append({
                    'id': target.target_id,
                    'type': target.target_type.value,
                    'status': target.status.value,
                    'bearing': target.bearing,
                    'range': target.range_nm,
                    'x': target.x_position,
                    'y': target.y_position,
                    'speed': target.speed,
                    'course': target.course,
                    'cpa_distance': target.cpa_distance,
                    'tcpa_time': target.tcpa_time,
                    'track_quality': target.track_quality,
                    'selected': target.selected,
                    'last_update': target.last_update.isoformat()
                })
            
            return {
                'mode': self.mode.value,
                'range': self.current_range.value,
                'targets': targets_data,
                'sweep_count': self.sweep_count,
                'target_count': len([t for t in self.targets.values() 
                                   if t.status != TargetStatus.LOST]),
                'last_sweep': self.last_sweep_time.isoformat() if self.last_sweep_time else None,
                'antenna_rpm': self.rpm
            }
    
    def process_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process radar control command"""
        try:
            if command == "set_range":
                range_nm = params.get('range')
                success = self.set_range(range_nm)
                return {"status": "success" if success else "error", "range": range_nm}
            
            elif command == "set_mode":
                mode = params.get('mode')
                success = self.set_mode(mode)
                return {"status": "success" if success else "error", "mode": mode}
            
            elif command == "acquire_target":
                bearing = params.get('bearing')
                range_nm = params.get('range')
                target_id = self.acquire_target(bearing, range_nm)
                return {"status": "success", "target_id": target_id}
            
            elif command == "drop_target":
                target_id = params.get('target_id')
                success = self.drop_target(target_id)
                return {"status": "success" if success else "error"}
            
            elif command == "select_target":
                target_id = params.get('target_id')
                success = self.select_target(target_id)
                return {"status": "success" if success else "error"}
            
            elif command == "set_sea_clutter":
                level = params.get('level', 0.5)
                self.config.sea_clutter_level = max(0.0, min(1.0, level))
                return {"status": "success", "sea_clutter": self.config.sea_clutter_level}
            
            elif command == "set_rain_clutter":
                level = params.get('level', 0.3)
                self.config.rain_clutter_level = max(0.0, min(1.0, level))
                return {"status": "success", "rain_clutter": self.config.rain_clutter_level}
            
            else:
                return {"status": "error", "message": f"Unknown command: {command}"}
                
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_target_details(self, target_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information for specific target"""
        with self.radar_lock:
            if target_id not in self.targets:
                return None
            
            target = self.targets[target_id]
            
            return {
                'id': target.target_id,
                'type': target.target_type.value,
                'status': target.status.value,
                'position': {
                    'bearing': target.bearing,
                    'range': target.range_nm,
                    'x': target.x_position,
                    'y': target.y_position
                },
                'motion': {
                    'speed': target.speed,
                    'course': target.course,
                    'heading': target.heading
                },
                'arpa': {
                    'cpa_distance': target.cpa_distance,
                    'tcpa_time': target.tcpa_time,
                    'bcr': target.bcr
                },
                'tracking': {
                    'quality': target.track_quality,
                    'acquisition_time': target.acquisition_time.isoformat(),
                    'last_update': target.last_update.isoformat(),
                    'echo_count': len(target.echo_history),
                    'position_history_count': len(target.position_history)
                },
                'display': {
                    'selected': target.selected,
                    'symbol': target.symbol_type,
                    'trail_length': target.trail_length
                }
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get radar system statistics"""
        with self.radar_lock:
            status_counts = {
                'acquiring': sum(1 for t in self.targets.values() 
                               if t.status == TargetStatus.ACQUIRING),
                'tracking': sum(1 for t in self.targets.values() 
                              if t.status == TargetStatus.TRACKING),
                'coasting': sum(1 for t in self.targets.values() 
                              if t.status == TargetStatus.COASTING),
                'lost': sum(1 for t in self.targets.values() 
                          if t.status == TargetStatus.LOST)
            }
            
            type_counts = {
                'automatic': sum(1 for t in self.targets.values() 
                               if t.target_type == TargetType.AUTOMATIC),
                'manual': sum(1 for t in self.targets.values() 
                            if t.target_type == TargetType.MANUAL)
            }
        
        return {
            'mode': self.mode.value,
            'range': self.current_range.value,
            'total_targets': len(self.targets),
            'active_targets': len(self.targets) - status_counts['lost'],
            'status_counts': status_counts,
            'type_counts': type_counts,
            'sweep_count': self.sweep_count,
            'antenna_rpm': self.rpm,
            'last_sweep': self.last_sweep_time.isoformat() if self.last_sweep_time else None,
            'receiving': self.receiving_radar,
            'config': {
                'max_targets': self.max_targets,
                'lost_timeout': self.config.lost_target_timeout,
                'sea_clutter': self.config.sea_clutter_level,
                'rain_clutter': self.config.rain_clutter_level
            }
        }