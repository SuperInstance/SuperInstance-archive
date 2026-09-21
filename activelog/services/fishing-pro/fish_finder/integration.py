#!/usr/bin/env python3

import asyncio
import time
import json
import struct
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import numpy as np

logger = logging.getLogger(__name__)

class SonarFrequency(Enum):
    """Sonar frequency bands"""
    LOW_50KHZ = "50kHz"
    MID_83KHZ = "83kHz"
    HIGH_200KHZ = "200kHz"
    CHIRP = "chirp"

class FishSize(Enum):
    """Fish size categories"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"

class BottomType(Enum):
    """Bottom composition types"""
    SOFT_MUD = "soft_mud"
    HARD_SAND = "hard_sand"
    ROCK = "rock"
    GRAVEL = "gravel"
    MIXED = "mixed"
    UNKNOWN = "unknown"

@dataclass
class SonarReading:
    """Individual sonar ping data"""
    timestamp: float
    depth: float  # meters
    water_temperature: Optional[float] = None  # celsius
    frequency: SonarFrequency = SonarFrequency.HIGH_200KHZ
    signal_strength: float = 0.0  # dB
    bottom_hardness: float = 0.0  # 0-100 scale
    bottom_type: BottomType = BottomType.UNKNOWN
    noise_level: float = 0.0  # dB

@dataclass
class FishTarget:
    """Detected fish target"""
    target_id: str
    timestamp: float
    latitude: float
    longitude: float
    depth: float  # meters from surface
    size: FishSize
    strength: float  # signal return strength
    length: Optional[float] = None  # estimated length in cm
    school_size: Optional[int] = None  # number of fish if school
    species_hint: Optional[str] = None  # AI species identification

@dataclass
class DepthContour:
    """Depth contour data"""
    latitude: float
    longitude: float
    depth: float
    timestamp: float

@dataclass
class FishFinderData:
    """Complete fish finder data package"""
    timestamp: float
    position: Dict[str, float]  # lat, lon
    sonar_reading: SonarReading
    fish_targets: List[FishTarget]
    depth_contours: List[DepthContour]
    water_column_data: Dict[str, Any]

class FishFinderParser:
    """Parses fish finder data from various formats"""
    
    def __init__(self):
        self.supported_formats = {
            'simrad': self._parse_simrad,
            'raymarine': self._parse_raymarine,
            'garmin': self._parse_garmin,
            'lowrance': self._parse_lowrance,
            'humminbird': self._parse_humminbird,
            'nmea': self._parse_nmea
        }
    
    def parse_data(self, data: bytes, format_type: str) -> Optional[FishFinderData]:
        """Parse fish finder data based on format"""
        try:
            if format_type in self.supported_formats:
                parser = self.supported_formats[format_type]
                return parser(data)
            else:
                logger.error(f"Unsupported format: {format_type}")
                return None
        except Exception as e:
            logger.error(f"Error parsing fish finder data: {e}")
            return None
    
    def _parse_simrad(self, data: bytes) -> Optional[FishFinderData]:
        """Parse Simrad EK/ES format data"""
        try:
            # Simrad RAW format parsing (simplified)
            if len(data) < 20:
                return None
            
            timestamp = time.time()
            
            # Extract basic ping data
            depth = struct.unpack('<f', data[0:4])[0]
            temperature = struct.unpack('<f', data[4:8])[0] if len(data) > 8 else None
            signal_strength = struct.unpack('<f', data[8:12])[0] if len(data) > 12 else 0.0
            
            sonar_reading = SonarReading(
                timestamp=timestamp,
                depth=depth,
                water_temperature=temperature,
                frequency=SonarFrequency.HIGH_200KHZ,
                signal_strength=signal_strength
            )
            
            # Detect fish targets (simplified algorithm)
            fish_targets = self._detect_fish_targets(data[12:], depth)
            
            return FishFinderData(
                timestamp=timestamp,
                position={'latitude': 0.0, 'longitude': 0.0},  # Would be filled by GPS
                sonar_reading=sonar_reading,
                fish_targets=fish_targets,
                depth_contours=[],
                water_column_data={}
            )
            
        except Exception as e:
            logger.error(f"Error parsing Simrad data: {e}")
            return None
    
    def _parse_raymarine(self, data: bytes) -> Optional[FishFinderData]:
        """Parse Raymarine format data"""
        try:
            # Raymarine SeaTalk format
            timestamp = time.time()
            
            # Basic depth and temperature extraction
            depth = struct.unpack('>H', data[0:2])[0] * 0.3048  # feet to meters
            
            sonar_reading = SonarReading(
                timestamp=timestamp,
                depth=depth,
                frequency=SonarFrequency.HIGH_200KHZ
            )
            
            return FishFinderData(
                timestamp=timestamp,
                position={'latitude': 0.0, 'longitude': 0.0},
                sonar_reading=sonar_reading,
                fish_targets=[],
                depth_contours=[],
                water_column_data={}
            )
            
        except Exception as e:
            logger.error(f"Error parsing Raymarine data: {e}")
            return None
    
    def _parse_garmin(self, data: bytes) -> Optional[FishFinderData]:
        """Parse Garmin format data"""
        try:
            # Garmin proprietary format
            timestamp = time.time()
            
            if len(data) < 8:
                return None
            
            depth = struct.unpack('<f', data[0:4])[0]
            temperature = struct.unpack('<f', data[4:8])[0] if len(data) > 8 else None
            
            sonar_reading = SonarReading(
                timestamp=timestamp,
                depth=depth,
                water_temperature=temperature,
                frequency=SonarFrequency.CHIRP
            )
            
            return FishFinderData(
                timestamp=timestamp,
                position={'latitude': 0.0, 'longitude': 0.0},
                sonar_reading=sonar_reading,
                fish_targets=[],
                depth_contours=[],
                water_column_data={}
            )
            
        except Exception as e:
            logger.error(f"Error parsing Garmin data: {e}")
            return None
    
    def _parse_lowrance(self, data: bytes) -> Optional[FishFinderData]:
        """Parse Lowrance format data"""
        return self._parse_garmin(data)  # Similar format
    
    def _parse_humminbird(self, data: bytes) -> Optional[FishFinderData]:
        """Parse Humminbird format data"""
        try:
            timestamp = time.time()
            
            if len(data) < 6:
                return None
            
            depth = struct.unpack('<H', data[0:2])[0] / 10.0  # decimeters to meters
            temperature = struct.unpack('<h', data[2:4])[0] / 10.0 if len(data) > 4 else None
            
            sonar_reading = SonarReading(
                timestamp=timestamp,
                depth=depth,
                water_temperature=temperature,
                frequency=SonarFrequency.HIGH_200KHZ
            )
            
            return FishFinderData(
                timestamp=timestamp,
                position={'latitude': 0.0, 'longitude': 0.0},
                sonar_reading=sonar_reading,
                fish_targets=[],
                depth_contours=[],
                water_column_data={}
            )
            
        except Exception as e:
            logger.error(f"Error parsing Humminbird data: {e}")
            return None
    
    def _parse_nmea(self, data: bytes) -> Optional[FishFinderData]:
        """Parse NMEA 0183/2000 sonar data"""
        try:
            # Parse NMEA sentences like $SDDBT, $SDDPT, $SDMTW
            sentence = data.decode('ascii').strip()
            
            if not sentence.startswith('$'):
                return None
            
            parts = sentence.split(',')
            sentence_type = parts[0][3:6]  # Extract sentence type
            
            timestamp = time.time()
            depth = 0.0
            temperature = None
            
            if sentence_type == 'DBT':  # Depth Below Transducer
                if len(parts) > 3 and parts[3]:
                    depth = float(parts[3])  # meters
            elif sentence_type == 'DPT':  # Depth
                if len(parts) > 1 and parts[1]:
                    depth = float(parts[1])  # meters
            elif sentence_type == 'MTW':  # Water Temperature
                if len(parts) > 1 and parts[1]:
                    temperature = float(parts[1])  # celsius
            
            sonar_reading = SonarReading(
                timestamp=timestamp,
                depth=depth,
                water_temperature=temperature,
                frequency=SonarFrequency.HIGH_200KHZ
            )
            
            return FishFinderData(
                timestamp=timestamp,
                position={'latitude': 0.0, 'longitude': 0.0},
                sonar_reading=sonar_reading,
                fish_targets=[],
                depth_contours=[],
                water_column_data={}
            )
            
        except Exception as e:
            logger.error(f"Error parsing NMEA data: {e}")
            return None
    
    def _detect_fish_targets(self, echo_data: bytes, depth: float) -> List[FishTarget]:
        """Detect fish targets from echo sounder data"""
        targets = []
        
        try:
            if len(echo_data) < 4:
                return targets
            
            # Simplified fish detection algorithm
            # In a real system, this would use sophisticated DSP
            
            # Convert bytes to signal strength values
            signal_data = np.frombuffer(echo_data[:100], dtype=np.uint8)
            
            # Find peaks that might indicate fish
            threshold = np.mean(signal_data) + 2 * np.std(signal_data)
            peaks = np.where(signal_data > threshold)[0]
            
            for i, peak_idx in enumerate(peaks[:5]):  # Limit to 5 targets
                signal_strength = float(signal_data[peak_idx])
                target_depth = depth * (peak_idx / len(signal_data))
                
                # Estimate fish size based on signal strength
                if signal_strength > threshold * 1.5:
                    size = FishSize.LARGE
                    estimated_length = 40 + (signal_strength - threshold) * 2
                elif signal_strength > threshold * 1.2:
                    size = FishSize.MEDIUM  
                    estimated_length = 20 + (signal_strength - threshold) * 1.5
                else:
                    size = FishSize.SMALL
                    estimated_length = 10 + (signal_strength - threshold)
                
                target = FishTarget(
                    target_id=f"target_{int(time.time())}_{i}",
                    timestamp=time.time(),
                    latitude=0.0,  # Will be filled by GPS
                    longitude=0.0,
                    depth=target_depth,
                    size=size,
                    strength=signal_strength,
                    length=min(estimated_length, 200.0)  # Cap at 2m
                )
                
                targets.append(target)
            
        except Exception as e:
            logger.error(f"Error detecting fish targets: {e}")
        
        return targets

class FishSpeciesIdentifier:
    """AI-powered fish species identification"""
    
    def __init__(self):
        self.species_database = {
            # Size and depth-based species hints
            'cod': {'min_length': 30, 'max_length': 120, 'depth_range': (10, 200), 'strength_range': (15, 40)},
            'haddock': {'min_length': 25, 'max_length': 75, 'depth_range': (40, 300), 'strength_range': (10, 30)},
            'pollock': {'min_length': 35, 'max_length': 130, 'depth_range': (20, 400), 'strength_range': (20, 45)},
            'mackerel': {'min_length': 20, 'max_length': 60, 'depth_range': (0, 50), 'strength_range': (5, 20)},
            'herring': {'min_length': 15, 'max_length': 40, 'depth_range': (0, 200), 'strength_range': (3, 15)},
            'tuna': {'min_length': 50, 'max_length': 300, 'depth_range': (0, 500), 'strength_range': (30, 80)},
            'salmon': {'min_length': 40, 'max_length': 150, 'depth_range': (0, 100), 'strength_range': (20, 50)},
            'bass': {'min_length': 25, 'max_length': 100, 'depth_range': (5, 150), 'strength_range': (15, 35)},
        }
        
        # Load location-specific species data
        self.location_species = {}
    
    def identify_species(self, fish_target: FishTarget, location: Dict[str, float], 
                        season: Optional[str] = None, water_temp: Optional[float] = None) -> List[Dict[str, Any]]:
        """Identify possible species based on target characteristics"""
        
        candidates = []
        
        try:
            for species, characteristics in self.species_database.items():
                confidence = self._calculate_species_confidence(
                    fish_target, characteristics, location, season, water_temp
                )
                
                if confidence > 0.3:  # Minimum confidence threshold
                    candidates.append({
                        'species': species,
                        'confidence': confidence,
                        'reason': self._get_identification_reason(fish_target, characteristics)
                    })
            
            # Sort by confidence
            candidates.sort(key=lambda x: x['confidence'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error identifying species: {e}")
        
        return candidates[:3]  # Return top 3 candidates
    
    def _calculate_species_confidence(self, target: FishTarget, characteristics: Dict[str, Any],
                                    location: Dict[str, float], season: Optional[str], 
                                    water_temp: Optional[float]) -> float:
        """Calculate confidence score for species match"""
        
        confidence = 0.0
        
        try:
            # Size match
            if target.length:
                min_len = characteristics['min_length']
                max_len = characteristics['max_length']
                
                if min_len <= target.length <= max_len:
                    confidence += 0.4
                elif target.length < min_len:
                    confidence += max(0, 0.4 - (min_len - target.length) / min_len)
                else:
                    confidence += max(0, 0.4 - (target.length - max_len) / max_len)
            
            # Depth match
            depth_range = characteristics['depth_range']
            if depth_range[0] <= target.depth <= depth_range[1]:
                confidence += 0.3
            else:
                # Reduce confidence based on depth difference
                if target.depth < depth_range[0]:
                    diff = depth_range[0] - target.depth
                elif target.depth > depth_range[1]:
                    diff = target.depth - depth_range[1]
                else:
                    diff = 0
                
                confidence += max(0, 0.3 - diff / 100)
            
            # Signal strength match
            strength_range = characteristics['strength_range']
            if strength_range[0] <= target.strength <= strength_range[1]:
                confidence += 0.2
            
            # Location-based adjustment (simplified)
            # In a real system, this would use detailed habitat data
            latitude = location.get('latitude', 0)
            
            # Rough latitude-based species distribution
            if 'cod' in characteristics and 40 <= latitude <= 70:
                confidence += 0.1
            elif 'tuna' in characteristics and 20 <= latitude <= 50:
                confidence += 0.1
            elif 'mackerel' in characteristics and 30 <= latitude <= 60:
                confidence += 0.1
            
        except Exception as e:
            logger.error(f"Error calculating species confidence: {e}")
        
        return min(confidence, 1.0)
    
    def _get_identification_reason(self, target: FishTarget, characteristics: Dict[str, Any]) -> str:
        """Generate human-readable identification reason"""
        
        reasons = []
        
        if target.length:
            min_len = characteristics['min_length']
            max_len = characteristics['max_length']
            if min_len <= target.length <= max_len:
                reasons.append(f"size match ({target.length:.0f}cm)")
        
        depth_range = characteristics['depth_range']
        if depth_range[0] <= target.depth <= depth_range[1]:
            reasons.append(f"depth match ({target.depth:.0f}m)")
        
        return ', '.join(reasons) if reasons else 'general characteristics'

class FishFinderIntegration:
    """Main fish finder integration system"""
    
    def __init__(self):
        self.parser = FishFinderParser()
        self.species_identifier = FishSpeciesIdentifier()
        self.running = False
        self.data_callbacks: List[Callable] = []
        self.fish_callbacks: List[Callable] = []
        
        # Connection settings
        self.connections = {}
        self.data_sources = []
        
        # Data storage
        self.recent_data: List[FishFinderData] = []
        self.max_recent_data = 1000
        
        # Current position from GPS
        self.current_position = {'latitude': 0.0, 'longitude': 0.0}
        
        # Environmental data
        self.water_temperature: Optional[float] = None
        self.current_season = "spring"
        
    async def start(self):
        """Start fish finder integration"""
        self.running = True
        logger.info("Fish finder integration started")
        await self._monitoring_loop()
    
    async def stop(self):
        """Stop fish finder integration"""
        self.running = False
        logger.info("Fish finder integration stopped")
    
    def add_data_source(self, source_config: Dict[str, Any]):
        """Add a fish finder data source"""
        
        source = {
            'id': source_config.get('id', f'source_{len(self.data_sources)}'),
            'type': source_config.get('type', 'nmea'),  # nmea, serial, tcp, udp
            'format': source_config.get('format', 'nmea'),
            'connection': source_config.get('connection', {}),
            'enabled': source_config.get('enabled', True)
        }
        
        self.data_sources.append(source)
        logger.info(f"Added fish finder data source: {source['id']}")
    
    async def process_data(self, data: bytes, format_type: str, source_id: str):
        """Process incoming fish finder data"""
        
        try:
            # Parse the data
            parsed_data = self.parser.parse_data(data, format_type)
            
            if parsed_data:
                # Update with current GPS position
                parsed_data.position = self.current_position.copy()
                
                # Identify species for fish targets
                for target in parsed_data.fish_targets:
                    target.latitude = self.current_position['latitude']
                    target.longitude = self.current_position['longitude']
                    
                    # Run species identification
                    species_candidates = self.species_identifier.identify_species(
                        target, self.current_position, self.current_season, self.water_temperature
                    )
                    
                    if species_candidates:
                        target.species_hint = species_candidates[0]['species']
                
                # Store recent data
                self.recent_data.append(parsed_data)
                if len(self.recent_data) > self.max_recent_data:
                    self.recent_data.pop(0)
                
                # Notify callbacks
                await self._notify_data_callbacks(parsed_data)
                
                if parsed_data.fish_targets:
                    await self._notify_fish_callbacks(parsed_data.fish_targets)
        
        except Exception as e:
            logger.error(f"Error processing fish finder data: {e}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for data sources"""
        while self.running:
            try:
                # In a real implementation, this would:
                # - Connect to serial ports
                # - Listen on TCP/UDP sockets
                # - Read from file sources
                # - Process NMEA streams
                
                # For now, simulate with periodic data generation
                await self._simulate_fish_finder_data()
                
                await asyncio.sleep(1.0)  # 1 second update interval
                
            except Exception as e:
                logger.error(f"Error in fish finder monitoring loop: {e}")
                await asyncio.sleep(5.0)
    
    async def _simulate_fish_finder_data(self):
        """Simulate fish finder data for testing"""
        try:
            import random
            
            timestamp = time.time()
            
            # Simulate sonar reading
            depth = 15 + random.uniform(-5, 25)  # 10-40m depth
            temperature = 12 + random.uniform(-3, 8)  # 9-20°C
            
            sonar_reading = SonarReading(
                timestamp=timestamp,
                depth=depth,
                water_temperature=temperature,
                frequency=SonarFrequency.HIGH_200KHZ,
                signal_strength=20 + random.uniform(-10, 20)
            )
            
            # Occasionally simulate fish targets
            fish_targets = []
            if random.random() < 0.3:  # 30% chance of fish
                num_targets = random.randint(1, 3)
                
                for i in range(num_targets):
                    target_depth = random.uniform(5, depth - 2)
                    signal_strength = 15 + random.uniform(0, 25)
                    
                    if signal_strength > 30:
                        size = FishSize.LARGE
                        length = random.uniform(50, 120)
                    elif signal_strength > 20:
                        size = FishSize.MEDIUM
                        length = random.uniform(25, 60)
                    else:
                        size = FishSize.SMALL
                        length = random.uniform(10, 30)
                    
                    target = FishTarget(
                        target_id=f"sim_target_{int(timestamp)}_{i}",
                        timestamp=timestamp,
                        latitude=self.current_position['latitude'],
                        longitude=self.current_position['longitude'],
                        depth=target_depth,
                        size=size,
                        strength=signal_strength,
                        length=length
                    )
                    
                    fish_targets.append(target)
            
            # Create fish finder data package
            fish_data = FishFinderData(
                timestamp=timestamp,
                position=self.current_position.copy(),
                sonar_reading=sonar_reading,
                fish_targets=fish_targets,
                depth_contours=[],
                water_column_data={'thermocline_depth': depth * 0.6}
            )
            
            # Process the simulated data
            await self.process_data(b'simulated', 'simulation', 'simulator')
            
        except Exception as e:
            logger.error(f"Error in fish finder simulation: {e}")
    
    async def _notify_data_callbacks(self, data: FishFinderData):
        """Notify data callbacks"""
        for callback in self.data_callbacks:
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"Error in fish finder data callback: {e}")
    
    async def _notify_fish_callbacks(self, fish_targets: List[FishTarget]):
        """Notify fish detection callbacks"""
        for callback in self.fish_callbacks:
            try:
                await callback(fish_targets)
            except Exception as e:
                logger.error(f"Error in fish detection callback: {e}")
    
    def update_position(self, latitude: float, longitude: float):
        """Update current GPS position"""
        self.current_position = {'latitude': latitude, 'longitude': longitude}
    
    def update_water_temperature(self, temperature: float):
        """Update water temperature"""
        self.water_temperature = temperature
    
    def add_data_callback(self, callback: Callable):
        """Add callback for all fish finder data"""
        self.data_callbacks.append(callback)
    
    def add_fish_callback(self, callback: Callable):
        """Add callback for fish detections"""
        self.fish_callbacks.append(callback)
    
    def get_recent_data(self, minutes: int = 10) -> List[FishFinderData]:
        """Get recent fish finder data"""
        cutoff_time = time.time() - (minutes * 60)
        return [data for data in self.recent_data if data.timestamp > cutoff_time]
    
    def get_fish_targets_in_area(self, center_lat: float, center_lon: float, 
                                radius_meters: float = 1000) -> List[FishTarget]:
        """Get fish targets in specified area"""
        targets = []
        
        for data in self.recent_data:
            for target in data.fish_targets:
                # Simple distance calculation
                lat_diff = target.latitude - center_lat
                lon_diff = target.longitude - center_lon
                distance = ((lat_diff * 111111) ** 2 + (lon_diff * 111111 * 
                           np.cos(np.radians(center_lat))) ** 2) ** 0.5
                
                if distance <= radius_meters:
                    targets.append(target)
        
        return targets
    
    def get_depth_profile(self, minutes: int = 30) -> Dict[str, Any]:
        """Get depth profile over time"""
        cutoff_time = time.time() - (minutes * 60)
        recent_data = [data for data in self.recent_data if data.timestamp > cutoff_time]
        
        if not recent_data:
            return {}
        
        depths = [data.sonar_reading.depth for data in recent_data]
        timestamps = [data.timestamp for data in recent_data]
        
        return {
            'timestamps': timestamps,
            'depths': depths,
            'min_depth': min(depths),
            'max_depth': max(depths),
            'avg_depth': sum(depths) / len(depths),
            'data_points': len(depths)
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get fish finder system status"""
        return {
            'running': self.running,
            'data_sources': len(self.data_sources),
            'recent_data_points': len(self.recent_data),
            'current_position': self.current_position,
            'water_temperature': self.water_temperature,
            'last_update': self.recent_data[-1].timestamp if self.recent_data else None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Export system state as dictionary"""
        return {
            'status': self.get_system_status(),
            'recent_fish_targets': [
                asdict(target) for data in self.recent_data[-10:] 
                for target in data.fish_targets
            ],
            'depth_profile': self.get_depth_profile(10)
        }