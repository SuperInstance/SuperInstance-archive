"""
GPS-enabled Catch Logging System
Comprehensive catch logging with precise GPS location and environmental data
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import threading
import time
import logging

logger = logging.getLogger(__name__)

class CatchMethod(Enum):
    TROLLING = "trolling"
    JIGGING = "jigging"
    BOTTOM_FISHING = "bottom_fishing"
    FLY_FISHING = "fly_fishing"
    NET_FISHING = "net_fishing"
    SPEARING = "spearing"
    CRABBING = "crabbing"
    LOBSTERING = "lobstering"

class FishCondition(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    RELEASED_ALIVE = "released_alive"
    RELEASED_DEAD = "released_dead"

class WeatherCondition(Enum):
    CALM = "calm"
    LIGHT_BREEZE = "light_breeze"
    MODERATE_BREEZE = "moderate_breeze"
    FRESH_BREEZE = "fresh_breeze"
    STRONG_BREEZE = "strong_breeze"
    ROUGH = "rough"
    STORMY = "stormy"

@dataclass
class GPSCoordinate:
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'accuracy': self.accuracy,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

@dataclass
class EnvironmentalData:
    water_temperature: Optional[float] = None  # Celsius
    air_temperature: Optional[float] = None    # Celsius
    barometric_pressure: Optional[float] = None # hPa
    wind_speed: Optional[float] = None         # knots
    wind_direction: Optional[float] = None     # degrees
    wave_height: Optional[float] = None        # meters
    current_speed: Optional[float] = None      # knots
    current_direction: Optional[float] = None  # degrees
    visibility: Optional[float] = None         # nautical miles
    weather_condition: Optional[WeatherCondition] = None
    tide_stage: Optional[str] = None           # high, low, rising, falling
    tide_height: Optional[float] = None        # meters
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if result.get('weather_condition'):
            result['weather_condition'] = result['weather_condition'].value
        return result

@dataclass
class CatchEntry:
    catch_id: str
    timestamp: datetime
    gps_location: GPSCoordinate
    species: str
    weight: Optional[float] = None           # kg
    length: Optional[float] = None          # cm
    catch_method: Optional[CatchMethod] = None
    gear_used: Optional[str] = None
    depth_caught: Optional[float] = None    # meters
    condition: Optional[FishCondition] = None
    quantity: int = 1
    kept: bool = True
    environmental_data: Optional[EnvironmentalData] = None
    notes: Optional[str] = None
    photos: Optional[List[str]] = None      # photo file paths
    crew_member: Optional[str] = None
    trip_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.catch_id:
            self.catch_id = str(uuid.uuid4())
        if self.photos is None:
            self.photos = []
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['gps_location'] = self.gps_location.to_dict()
        if result.get('catch_method'):
            result['catch_method'] = result['catch_method'].value
        if result.get('condition'):
            result['condition'] = result['condition'].value
        if result.get('environmental_data'):
            result['environmental_data'] = self.environmental_data.to_dict()
        return result

class GPSService:
    """GPS service for obtaining current coordinates"""
    
    def __init__(self, simulation_mode: bool = True):
        self.simulation_mode = simulation_mode
        self.last_position: Optional[GPSCoordinate] = None
        self._lock = threading.Lock()
        
        # Simulation parameters
        self._sim_lat = 40.7128  # Starting at NYC harbor
        self._sim_lon = -74.0060
        self._sim_drift_rate = 0.0001  # Small random drift
        
    def get_current_position(self) -> Optional[GPSCoordinate]:
        """Get current GPS position"""
        if self.simulation_mode:
            return self._simulate_position()
        else:
            # In real implementation, would interface with GPS hardware
            # Using NMEA sentences or GPS libraries like gpsd
            return self._get_real_gps_position()
    
    def _simulate_position(self) -> GPSCoordinate:
        """Simulate GPS position with small random drift"""
        import random
        
        if self.last_position is None:
            lat = self._sim_lat
            lon = self._sim_lon
        else:
            # Small random drift
            lat = self.last_position.latitude + random.uniform(-self._sim_drift_rate, self._sim_drift_rate)
            lon = self.last_position.longitude + random.uniform(-self._sim_drift_rate, self._sim_drift_rate)
        
        position = GPSCoordinate(
            latitude=lat,
            longitude=lon,
            altitude=random.uniform(0, 5),  # Sea level +/- tide
            accuracy=random.uniform(1, 5)   # GPS accuracy in meters
        )
        
        with self._lock:
            self.last_position = position
        
        return position
    
    def _get_real_gps_position(self) -> Optional[GPSCoordinate]:
        """Get position from real GPS hardware"""
        # Real implementation would use:
        # - gpsd client
        # - NMEA sentence parsing
        # - GPS module libraries
        logger.warning("Real GPS not implemented, using simulation")
        return self._simulate_position()

class EnvironmentalSensorService:
    """Service for collecting environmental data"""
    
    def __init__(self, simulation_mode: bool = True):
        self.simulation_mode = simulation_mode
    
    def get_current_conditions(self) -> EnvironmentalData:
        """Get current environmental conditions"""
        if self.simulation_mode:
            return self._simulate_conditions()
        else:
            return self._get_real_conditions()
    
    def _simulate_conditions(self) -> EnvironmentalData:
        """Simulate environmental conditions"""
        import random
        
        return EnvironmentalData(
            water_temperature=random.uniform(10, 25),
            air_temperature=random.uniform(15, 30),
            barometric_pressure=random.uniform(1000, 1030),
            wind_speed=random.uniform(0, 25),
            wind_direction=random.uniform(0, 360),
            wave_height=random.uniform(0, 3),
            current_speed=random.uniform(0, 3),
            current_direction=random.uniform(0, 360),
            visibility=random.uniform(1, 20),
            weather_condition=random.choice(list(WeatherCondition)),
            tide_stage=random.choice(["high", "low", "rising", "falling"]),
            tide_height=random.uniform(-2, 2)
        )
    
    def _get_real_conditions(self) -> EnvironmentalData:
        """Get conditions from real sensors"""
        # Real implementation would interface with:
        # - Weather stations
        # - Water temperature sensors
        # - Barometric pressure sensors
        # - Wind sensors
        logger.warning("Real environmental sensors not implemented, using simulation")
        return self._simulate_conditions()

class CatchDatabase:
    """SQLite database for storing catch data"""
    
    def __init__(self, db_path: str = "fishing_pro.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS catches (
                    catch_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    altitude REAL,
                    gps_accuracy REAL,
                    species TEXT NOT NULL,
                    weight REAL,
                    length REAL,
                    catch_method TEXT,
                    gear_used TEXT,
                    depth_caught REAL,
                    condition TEXT,
                    quantity INTEGER DEFAULT 1,
                    kept BOOLEAN DEFAULT 1,
                    notes TEXT,
                    photos TEXT,
                    crew_member TEXT,
                    trip_id TEXT,
                    environmental_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_catches_timestamp 
                ON catches(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_catches_species 
                ON catches(species)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_catches_location 
                ON catches(latitude, longitude)
            """)
    
    def save_catch(self, catch_entry: CatchEntry) -> bool:
        """Save catch entry to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO catches (
                        catch_id, timestamp, latitude, longitude, altitude, gps_accuracy,
                        species, weight, length, catch_method, gear_used, depth_caught,
                        condition, quantity, kept, notes, photos, crew_member, trip_id,
                        environmental_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    catch_entry.catch_id,
                    catch_entry.timestamp.isoformat(),
                    catch_entry.gps_location.latitude,
                    catch_entry.gps_location.longitude,
                    catch_entry.gps_location.altitude,
                    catch_entry.gps_location.accuracy,
                    catch_entry.species,
                    catch_entry.weight,
                    catch_entry.length,
                    catch_entry.catch_method.value if catch_entry.catch_method else None,
                    catch_entry.gear_used,
                    catch_entry.depth_caught,
                    catch_entry.condition.value if catch_entry.condition else None,
                    catch_entry.quantity,
                    catch_entry.kept,
                    catch_entry.notes,
                    json.dumps(catch_entry.photos) if catch_entry.photos else None,
                    catch_entry.crew_member,
                    catch_entry.trip_id,
                    json.dumps(catch_entry.environmental_data.to_dict()) if catch_entry.environmental_data else None
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to save catch: {e}")
            return False
    
    def get_catches(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get catch entries from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM catches 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_catches_by_species(self, species: str) -> List[Dict[str, Any]]:
        """Get catches filtered by species"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM catches 
                WHERE species = ?
                ORDER BY timestamp DESC
            """, (species,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_catches_in_area(self, center_lat: float, center_lon: float, radius_km: float) -> List[Dict[str, Any]]:
        """Get catches within specified area"""
        # Simple bounding box calculation (not exact but sufficient)
        lat_delta = radius_km / 111.0  # Approximate km per degree latitude
        lon_delta = radius_km / (111.0 * abs(center_lat))  # Adjust for latitude
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM catches 
                WHERE latitude BETWEEN ? AND ?
                  AND longitude BETWEEN ? AND ?
                ORDER BY timestamp DESC
            """, (
                center_lat - lat_delta, center_lat + lat_delta,
                center_lon - lon_delta, center_lon + lon_delta
            ))
            
            return [dict(row) for row in cursor.fetchall()]

class CatchLogger:
    """Main catch logging service"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.gps_service = GPSService(simulation_mode=self.config.get('simulation_mode', True))
        self.env_service = EnvironmentalSensorService(simulation_mode=self.config.get('simulation_mode', True))
        self.database = CatchDatabase(self.config.get('database_path', 'fishing_pro.db'))
        
        # Auto-logging settings
        self.auto_log_environmental = self.config.get('auto_log_environmental', True)
        self.auto_save = self.config.get('auto_save', True)
        
        # Current trip tracking
        self.current_trip_id: Optional[str] = None
        
    def start_trip(self, trip_name: Optional[str] = None) -> str:
        """Start a new fishing trip"""
        self.current_trip_id = str(uuid.uuid4())
        logger.info(f"Started new fishing trip: {self.current_trip_id}")
        return self.current_trip_id
    
    def end_trip(self):
        """End current fishing trip"""
        if self.current_trip_id:
            logger.info(f"Ended fishing trip: {self.current_trip_id}")
            self.current_trip_id = None
    
    def log_catch(self,
                  species: str,
                  weight: Optional[float] = None,
                  length: Optional[float] = None,
                  catch_method: Optional[CatchMethod] = None,
                  gear_used: Optional[str] = None,
                  depth_caught: Optional[float] = None,
                  condition: Optional[FishCondition] = None,
                  quantity: int = 1,
                  kept: bool = True,
                  notes: Optional[str] = None,
                  crew_member: Optional[str] = None,
                  photos: Optional[List[str]] = None) -> Optional[CatchEntry]:
        """Log a catch with current GPS and environmental data"""
        
        # Get current GPS position
        gps_location = self.gps_service.get_current_position()
        if not gps_location:
            logger.error("Could not obtain GPS position for catch")
            return None
        
        # Get environmental data if enabled
        environmental_data = None
        if self.auto_log_environmental:
            environmental_data = self.env_service.get_current_conditions()
        
        # Create catch entry
        catch_entry = CatchEntry(
            catch_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            gps_location=gps_location,
            species=species,
            weight=weight,
            length=length,
            catch_method=catch_method,
            gear_used=gear_used,
            depth_caught=depth_caught,
            condition=condition,
            quantity=quantity,
            kept=kept,
            environmental_data=environmental_data,
            notes=notes,
            photos=photos or [],
            crew_member=crew_member,
            trip_id=self.current_trip_id
        )
        
        # Save to database if auto-save is enabled
        if self.auto_save:
            success = self.database.save_catch(catch_entry)
            if success:
                logger.info(f"Logged catch: {species} at {gps_location.latitude:.6f}, {gps_location.longitude:.6f}")
            else:
                logger.error("Failed to save catch to database")
                return None
        
        return catch_entry
    
    def quick_log(self, species: str, kept: bool = True, notes: Optional[str] = None) -> Optional[CatchEntry]:
        """Quick catch logging with minimal data"""
        return self.log_catch(
            species=species,
            kept=kept,
            notes=notes,
            condition=FishCondition.GOOD if kept else FishCondition.RELEASED_ALIVE
        )
    
    def get_trip_catches(self, trip_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get catches for current or specified trip"""
        if trip_id is None:
            trip_id = self.current_trip_id
        
        if not trip_id:
            return []
        
        with sqlite3.connect(self.database.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM catches 
                WHERE trip_id = ?
                ORDER BY timestamp DESC
            """, (trip_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trip_summary(self, trip_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for a trip"""
        catches = self.get_trip_catches(trip_id)
        
        if not catches:
            return {"total_catches": 0, "species_count": 0, "total_weight": 0, "kept_count": 0}
        
        species_set = set()
        total_weight = 0
        kept_count = 0
        
        for catch in catches:
            if catch['species']:
                species_set.add(catch['species'])
            if catch['weight']:
                total_weight += catch['weight']
            if catch['kept']:
                kept_count += catch['quantity'] or 1
        
        return {
            "total_catches": len(catches),
            "species_count": len(species_set),
            "total_weight": total_weight,
            "kept_count": kept_count,
            "released_count": len(catches) - kept_count,
            "species_list": list(species_set)
        }
    
    def export_catches(self, format_type: str = "json", trip_id: Optional[str] = None) -> str:
        """Export catch data in specified format"""
        catches = self.get_trip_catches(trip_id) if trip_id else self.database.get_catches()
        
        if format_type.lower() == "json":
            return json.dumps(catches, indent=2, default=str)
        elif format_type.lower() == "csv":
            import csv
            import io
            
            if not catches:
                return ""
            
            output = io.StringIO()
            fieldnames = catches[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(catches)
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

async def main():
    """Example usage of the catch logging system"""
    
    # Initialize catch logger
    logger_config = {
        'simulation_mode': True,
        'auto_log_environmental': True,
        'auto_save': True,
        'database_path': 'fishing_pro.db'
    }
    
    catch_logger = CatchLogger(logger_config)
    
    # Start a fishing trip
    trip_id = catch_logger.start_trip("Morning Fishing")
    print(f"Started trip: {trip_id}")
    
    # Log some catches
    catch1 = catch_logger.log_catch(
        species="Striped Bass",
        weight=2.5,
        length=45.0,
        catch_method=CatchMethod.TROLLING,
        gear_used="Trolling rod, spoon lure",
        depth_caught=15.0,
        condition=FishCondition.EXCELLENT,
        kept=True,
        notes="Beautiful fish, fought hard"
    )
    
    if catch1:
        print(f"Logged catch: {catch1.species} at {catch1.gps_location.latitude:.6f}, {catch1.gps_location.longitude:.6f}")
    
    # Quick log
    catch2 = catch_logger.quick_log("Flounder", kept=False, notes="Too small, released")
    if catch2:
        print(f"Quick logged: {catch2.species}")
    
    # Get trip summary
    summary = catch_logger.get_trip_summary()
    print(f"Trip summary: {summary}")
    
    # End trip
    catch_logger.end_trip()

if __name__ == "__main__":
    asyncio.run(main())