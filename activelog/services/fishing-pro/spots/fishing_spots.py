"""
Fishing Spot Database and Management System
Comprehensive fishing spot database with GPS coordinates, conditions, and analytics
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import threading
import logging
import math

logger = logging.getLogger(__name__)

class SpotType(Enum):
    STRUCTURE = "structure"           # Reefs, wrecks, drop-offs
    WEED_LINE = "weed_line"          # Sargassum, kelp lines
    TEMPERATURE_BREAK = "temperature_break"  # Thermoclines
    CURRENT_BREAK = "current_break"   # Current edges
    UPWELLING = "upwelling"          # Nutrient upwelling areas
    SHALLOW_WATER = "shallow_water"   # Flats, shallows
    DEEP_WATER = "deep_water"        # Deep sea spots
    INLET = "inlet"                  # Harbor mouths, inlets
    BRIDGE = "bridge"                # Bridge structures
    PIER = "pier"                    # Pier/dock fishing
    SHORE = "shore"                  # Shore/surf fishing
    ARTIFICIAL_REEF = "artificial_reef"  # Man-made reefs

class BottomType(Enum):
    SAND = "sand"
    MUD = "mud"
    ROCK = "rock"
    REEF = "reef"
    GRAVEL = "gravel"
    SHELL = "shell"
    WEED = "weed"
    MIXED = "mixed"

class WaterType(Enum):
    SALTWATER = "saltwater"
    FRESHWATER = "freshwater"
    BRACKISH = "brackish"

@dataclass
class GPSCoordinate:
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    
    def distance_to(self, other: 'GPSCoordinate') -> float:
        """Calculate distance in nautical miles using haversine formula"""
        R = 3440.065  # Earth radius in nautical miles
        
        lat1_rad = math.radians(self.latitude)
        lat2_rad = math.radians(other.latitude)
        delta_lat = math.radians(other.latitude - self.latitude)
        delta_lon = math.radians(other.longitude - self.longitude)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def bearing_to(self, other: 'GPSCoordinate') -> float:
        """Calculate bearing in degrees"""
        lat1_rad = math.radians(self.latitude)
        lat2_rad = math.radians(other.latitude)
        delta_lon = math.radians(other.longitude - self.longitude)
        
        x = math.sin(delta_lon) * math.cos(lat2_rad)
        y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))
        
        bearing_rad = math.atan2(x, y)
        bearing_deg = (math.degrees(bearing_rad) + 360) % 360
        
        return bearing_deg

@dataclass
class FishingConditions:
    best_tide_stages: List[str]       # high, low, rising, falling
    best_wind_directions: List[str]   # N, NE, E, SE, S, SW, W, NW
    min_depth: Optional[float] = None # meters
    max_depth: Optional[float] = None # meters
    best_seasons: Optional[List[str]] = None  # spring, summer, fall, winter
    best_months: Optional[List[int]] = None   # 1-12
    best_times: Optional[List[str]] = None    # dawn, morning, midday, afternoon, dusk, night
    water_temperature_range: Optional[Tuple[float, float]] = None  # (min, max) Celsius
    current_preferred: Optional[bool] = None  # True for moving water, False for slack
    structure_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if result.get('water_temperature_range'):
            result['water_temperature_range'] = list(result['water_temperature_range'])
        return result

@dataclass
class FishingSpot:
    spot_id: str
    name: str
    location: GPSCoordinate
    spot_type: SpotType
    water_type: WaterType
    description: Optional[str] = None
    depth_range: Optional[Tuple[float, float]] = None  # (min, max) meters
    bottom_type: Optional[BottomType] = None
    target_species: Optional[List[str]] = None
    conditions: Optional[FishingConditions] = None
    access_info: Optional[str] = None
    facilities: Optional[List[str]] = None  # parking, restrooms, launch ramp, etc.
    regulations: Optional[str] = None
    safety_notes: Optional[str] = None
    private_spot: bool = False
    creator: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    rating: Optional[float] = None  # 1-5 stars
    visit_count: int = 0
    success_rate: Optional[float] = None  # percentage of successful trips
    last_fished: Optional[datetime] = None
    notes: Optional[str] = None
    photos: Optional[List[str]] = None
    
    def __post_init__(self):
        if not self.spot_id:
            self.spot_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.last_updated is None:
            self.last_updated = self.created_at
        if self.target_species is None:
            self.target_species = []
        if self.facilities is None:
            self.facilities = []
        if self.photos is None:
            self.photos = []
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['location'] = asdict(self.location)
        result['spot_type'] = self.spot_type.value
        result['water_type'] = self.water_type.value
        if result.get('bottom_type'):
            result['bottom_type'] = result['bottom_type'].value
        if result.get('conditions'):
            result['conditions'] = self.conditions.to_dict()
        if result.get('depth_range'):
            result['depth_range'] = list(result['depth_range'])
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()
        if result.get('last_updated'):
            result['last_updated'] = result['last_updated'].isoformat()
        if result.get('last_fished'):
            result['last_fished'] = result['last_fished'].isoformat()
        return result

@dataclass
class SpotVisit:
    visit_id: str
    spot_id: str
    visit_date: datetime
    catches: List[str]  # catch_ids
    conditions_observed: Optional[Dict[str, Any]] = None
    success: bool = False
    notes: Optional[str] = None
    weather_conditions: Optional[str] = None
    tide_stage: Optional[str] = None
    fishing_duration: Optional[float] = None  # hours
    
    def __post_init__(self):
        if not self.visit_id:
            self.visit_id = str(uuid.uuid4())
        if self.catches is None:
            self.catches = []

class FishingSpotDatabase:
    """SQLite database for fishing spots"""
    
    def __init__(self, db_path: str = "fishing_spots.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Fishing spots table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fishing_spots (
                    spot_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    location_accuracy REAL,
                    spot_type TEXT NOT NULL,
                    water_type TEXT NOT NULL,
                    description TEXT,
                    min_depth REAL,
                    max_depth REAL,
                    bottom_type TEXT,
                    target_species TEXT,
                    conditions TEXT,
                    access_info TEXT,
                    facilities TEXT,
                    regulations TEXT,
                    safety_notes TEXT,
                    private_spot BOOLEAN DEFAULT 0,
                    creator TEXT,
                    created_at TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    rating REAL,
                    visit_count INTEGER DEFAULT 0,
                    success_rate REAL,
                    last_fished TEXT,
                    notes TEXT,
                    photos TEXT
                )
            """)
            
            # Spot visits table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spot_visits (
                    visit_id TEXT PRIMARY KEY,
                    spot_id TEXT NOT NULL,
                    visit_date TEXT NOT NULL,
                    catches TEXT,
                    conditions_observed TEXT,
                    success BOOLEAN DEFAULT 0,
                    notes TEXT,
                    weather_conditions TEXT,
                    tide_stage TEXT,
                    fishing_duration REAL,
                    FOREIGN KEY (spot_id) REFERENCES fishing_spots (spot_id)
                )
            """)
            
            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_spots_location 
                ON fishing_spots(latitude, longitude)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_spots_type 
                ON fishing_spots(spot_type)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_spots_species 
                ON fishing_spots(target_species)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_visits_spot 
                ON spot_visits(spot_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_visits_date 
                ON spot_visits(visit_date)
            """)
    
    def save_spot(self, spot: FishingSpot) -> bool:
        """Save fishing spot to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO fishing_spots (
                        spot_id, name, latitude, longitude, location_accuracy,
                        spot_type, water_type, description, min_depth, max_depth,
                        bottom_type, target_species, conditions, access_info, facilities,
                        regulations, safety_notes, private_spot, creator, created_at,
                        last_updated, rating, visit_count, success_rate, last_fished,
                        notes, photos
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    spot.spot_id, spot.name,
                    spot.location.latitude, spot.location.longitude, spot.location.accuracy,
                    spot.spot_type.value, spot.water_type.value, spot.description,
                    spot.depth_range[0] if spot.depth_range else None,
                    spot.depth_range[1] if spot.depth_range else None,
                    spot.bottom_type.value if spot.bottom_type else None,
                    json.dumps(spot.target_species) if spot.target_species else None,
                    json.dumps(spot.conditions.to_dict()) if spot.conditions else None,
                    spot.access_info,
                    json.dumps(spot.facilities) if spot.facilities else None,
                    spot.regulations, spot.safety_notes, spot.private_spot, spot.creator,
                    spot.created_at.isoformat(), spot.last_updated.isoformat(),
                    spot.rating, spot.visit_count, spot.success_rate,
                    spot.last_fished.isoformat() if spot.last_fished else None,
                    spot.notes,
                    json.dumps(spot.photos) if spot.photos else None
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to save fishing spot: {e}")
            return False
    
    def get_spot(self, spot_id: str) -> Optional[Dict[str, Any]]:
        """Get fishing spot by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM fishing_spots WHERE spot_id = ?
            """, (spot_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_spots_near_location(self, lat: float, lon: float, radius_nm: float = 10.0) -> List[Dict[str, Any]]:
        """Get spots within radius (nautical miles) of location"""
        # Simple bounding box calculation
        lat_delta = radius_nm / 60.0  # 1 degree ≈ 60 nautical miles
        lon_delta = radius_nm / (60.0 * math.cos(math.radians(lat)))
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM fishing_spots 
                WHERE latitude BETWEEN ? AND ?
                  AND longitude BETWEEN ? AND ?
                ORDER BY 
                    ((latitude - ?) * (latitude - ?) + 
                     (longitude - ?) * (longitude - ?)) ASC
            """, (
                lat - lat_delta, lat + lat_delta,
                lon - lon_delta, lon + lon_delta,
                lat, lat, lon, lon
            ))
            
            spots = [dict(row) for row in cursor.fetchall()]
            
            # Filter by exact distance and sort
            center = GPSCoordinate(lat, lon)
            filtered_spots = []
            
            for spot_data in spots:
                spot_coord = GPSCoordinate(spot_data['latitude'], spot_data['longitude'])
                distance = center.distance_to(spot_coord)
                if distance <= radius_nm:
                    spot_data['distance_nm'] = distance
                    spot_data['bearing'] = center.bearing_to(spot_coord)
                    filtered_spots.append(spot_data)
            
            return sorted(filtered_spots, key=lambda x: x['distance_nm'])
    
    def get_spots_by_type(self, spot_type: SpotType) -> List[Dict[str, Any]]:
        """Get spots by type"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM fishing_spots WHERE spot_type = ?
                ORDER BY rating DESC, visit_count DESC
            """, (spot_type.value,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_spots_by_species(self, species: str) -> List[Dict[str, Any]]:
        """Get spots that target specific species"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM fishing_spots 
                WHERE target_species LIKE ?
                ORDER BY success_rate DESC, rating DESC
            """, (f'%{species}%',))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def search_spots(self, query: str) -> List[Dict[str, Any]]:
        """Search spots by name, description, or notes"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM fishing_spots 
                WHERE name LIKE ? OR description LIKE ? OR notes LIKE ?
                ORDER BY rating DESC, visit_count DESC
            """, (f'%{query}%', f'%{query}%', f'%{query}%'))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def record_visit(self, visit: SpotVisit) -> bool:
        """Record a spot visit"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Insert visit record
                conn.execute("""
                    INSERT INTO spot_visits (
                        visit_id, spot_id, visit_date, catches, conditions_observed,
                        success, notes, weather_conditions, tide_stage, fishing_duration
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    visit.visit_id, visit.spot_id, visit.visit_date.isoformat(),
                    json.dumps(visit.catches), 
                    json.dumps(visit.conditions_observed) if visit.conditions_observed else None,
                    visit.success, visit.notes, visit.weather_conditions,
                    visit.tide_stage, visit.fishing_duration
                ))
                
                # Update spot statistics
                conn.execute("""
                    UPDATE fishing_spots 
                    SET visit_count = visit_count + 1,
                        last_fished = ?,
                        last_updated = ?
                    WHERE spot_id = ?
                """, (visit.visit_date.isoformat(), datetime.now(timezone.utc).isoformat(), visit.spot_id))
                
                # Update success rate
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_visits,
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_visits
                    FROM spot_visits WHERE spot_id = ?
                """, (visit.spot_id,))
                
                stats = cursor.fetchone()
                if stats and stats[0] > 0:
                    success_rate = (stats[1] / stats[0]) * 100
                    conn.execute("""
                        UPDATE fishing_spots 
                        SET success_rate = ?
                        WHERE spot_id = ?
                    """, (success_rate, visit.spot_id))
                
            return True
        except Exception as e:
            logger.error(f"Failed to record spot visit: {e}")
            return False
    
    def get_spot_visits(self, spot_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get visit history for a spot"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM spot_visits 
                WHERE spot_id = ?
                ORDER BY visit_date DESC
                LIMIT ?
            """, (spot_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_spot_statistics(self, spot_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a spot"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Basic stats
            cursor = conn.execute("""
                SELECT COUNT(*) as total_visits,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_visits,
                       AVG(fishing_duration) as avg_duration,
                       MAX(visit_date) as last_visit
                FROM spot_visits WHERE spot_id = ?
            """, (spot_id,))
            
            stats = cursor.fetchone()
            if not stats:
                return {}
            
            # Get spot info
            spot_cursor = conn.execute("""
                SELECT rating, target_species FROM fishing_spots WHERE spot_id = ?
            """, (spot_id,))
            
            spot_info = spot_cursor.fetchone()
            
            result = dict(stats) if stats else {}
            if spot_info:
                result['rating'] = spot_info['rating']
                result['target_species'] = json.loads(spot_info['target_species']) if spot_info['target_species'] else []
            
            # Calculate success rate
            if result.get('total_visits', 0) > 0:
                result['success_rate'] = (result.get('successful_visits', 0) / result['total_visits']) * 100
            else:
                result['success_rate'] = 0
            
            return result

class FishingSpotManager:
    """Main fishing spot management service"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.database = FishingSpotDatabase(self.config.get('database_path', 'fishing_spots.db'))
        
        # Default user for spot creation
        self.default_user = self.config.get('default_user', 'user')
    
    def create_spot(self, 
                   name: str,
                   location: GPSCoordinate,
                   spot_type: SpotType,
                   water_type: WaterType,
                   description: Optional[str] = None,
                   depth_range: Optional[Tuple[float, float]] = None,
                   bottom_type: Optional[BottomType] = None,
                   target_species: Optional[List[str]] = None,
                   conditions: Optional[FishingConditions] = None,
                   **kwargs) -> FishingSpot:
        """Create a new fishing spot"""
        
        spot = FishingSpot(
            spot_id=str(uuid.uuid4()),
            name=name,
            location=location,
            spot_type=spot_type,
            water_type=water_type,
            description=description,
            depth_range=depth_range,
            bottom_type=bottom_type,
            target_species=target_species or [],
            conditions=conditions,
            creator=self.default_user,
            **kwargs
        )
        
        success = self.database.save_spot(spot)
        if success:
            logger.info(f"Created fishing spot: {name} ({spot.spot_id})")
        else:
            logger.error(f"Failed to create fishing spot: {name}")
        
        return spot
    
    def find_spots_near(self, lat: float, lon: float, radius_nm: float = 10.0) -> List[Dict[str, Any]]:
        """Find spots near a location"""
        return self.database.get_spots_near_location(lat, lon, radius_nm)
    
    def find_spots_for_species(self, species: str) -> List[Dict[str, Any]]:
        """Find spots that target specific species"""
        return self.database.get_spots_by_species(species)
    
    def search_spots(self, query: str) -> List[Dict[str, Any]]:
        """Search spots by name or description"""
        return self.database.search_spots(query)
    
    def record_fishing_trip(self, spot_id: str, catches: List[str], success: bool = True, **kwargs) -> bool:
        """Record a fishing trip to a spot"""
        visit = SpotVisit(
            visit_id=str(uuid.uuid4()),
            spot_id=spot_id,
            visit_date=datetime.now(timezone.utc),
            catches=catches,
            success=success,
            **kwargs
        )
        
        return self.database.record_visit(visit)
    
    def get_spot_info(self, spot_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed spot information"""
        spot_data = self.database.get_spot(spot_id)
        if not spot_data:
            return None
        
        # Add statistics
        stats = self.database.get_spot_statistics(spot_id)
        spot_data.update(stats)
        
        return spot_data
    
    def get_recommended_spots(self, user_location: GPSCoordinate, target_species: Optional[str] = None, 
                            max_distance: float = 50.0) -> List[Dict[str, Any]]:
        """Get recommended spots based on location and preferences"""
        # Find nearby spots
        spots = self.database.get_spots_near_location(
            user_location.latitude, user_location.longitude, max_distance
        )
        
        # Filter by species if specified
        if target_species:
            species_spots = []
            for spot in spots:
                target_species_list = json.loads(spot.get('target_species', '[]'))
                if target_species.lower() in [s.lower() for s in target_species_list]:
                    species_spots.append(spot)
            spots = species_spots
        
        # Sort by rating and success rate
        def sort_key(spot):
            rating = spot.get('rating', 0) or 0
            success_rate = spot.get('success_rate', 0) or 0
            visit_count = spot.get('visit_count', 0) or 0
            
            # Weighted score: rating * 0.4 + success_rate * 0.4 + visit_count * 0.2
            return rating * 0.4 + success_rate * 0.004 + min(visit_count * 0.2, 10)
        
        return sorted(spots, key=sort_key, reverse=True)[:20]  # Top 20 recommendations
    
    def update_spot_rating(self, spot_id: str, rating: float, user: Optional[str] = None) -> bool:
        """Update spot rating"""
        if rating < 1 or rating > 5:
            return False
        
        try:
            with sqlite3.connect(self.database.db_path) as conn:
                conn.execute("""
                    UPDATE fishing_spots 
                    SET rating = ?, last_updated = ?
                    WHERE spot_id = ?
                """, (rating, datetime.now(timezone.utc).isoformat(), spot_id))
            
            logger.info(f"Updated rating for spot {spot_id}: {rating} stars")
            return True
        except Exception as e:
            logger.error(f"Failed to update spot rating: {e}")
            return False
    
    def export_spots(self, format_type: str = "json") -> str:
        """Export all spots in specified format"""
        with sqlite3.connect(self.database.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM fishing_spots ORDER BY name")
            spots = [dict(row) for row in cursor.fetchall()]
        
        if format_type.lower() == "json":
            return json.dumps(spots, indent=2, default=str)
        elif format_type.lower() == "csv":
            import csv
            import io
            
            if not spots:
                return ""
            
            output = io.StringIO()
            fieldnames = spots[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(spots)
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

async def main():
    """Example usage of the fishing spot system"""
    
    # Initialize spot manager
    spot_manager = FishingSpotManager({
        'database_path': 'fishing_spots.db',
        'default_user': 'captain_fisher'
    })
    
    # Create some example spots
    
    # Structure spot
    reef_spot = spot_manager.create_spot(
        name="Montauk Reef",
        location=GPSCoordinate(41.0488, -71.8558),
        spot_type=SpotType.STRUCTURE,
        water_type=WaterType.SALTWATER,
        description="Productive reef structure with good striped bass fishing",
        depth_range=(20.0, 45.0),
        bottom_type=BottomType.ROCK,
        target_species=["Striped Bass", "Black Sea Bass", "Fluke"],
        conditions=FishingConditions(
            best_tide_stages=["rising", "high"],
            best_wind_directions=["W", "NW", "N"],
            best_times=["dawn", "dusk"],
            current_preferred=True
        ),
        access_info="Accessible by boat only",
        safety_notes="Watch for strong currents during tide changes"
    )
    
    print(f"Created spot: {reef_spot.name} ({reef_spot.spot_id})")
    
    # Inlet spot
    inlet_spot = spot_manager.create_spot(
        name="Jones Inlet",
        location=GPSCoordinate(40.5915, -73.5669),
        spot_type=SpotType.INLET,
        water_type=WaterType.SALTWATER,
        description="Productive inlet with good fluke and striped bass",
        depth_range=(3.0, 15.0),
        bottom_type=BottomType.SAND,
        target_species=["Fluke", "Striped Bass", "Weakfish"],
        conditions=FishingConditions(
            best_tide_stages=["rising", "falling"],
            best_wind_directions=["S", "SW", "W"],
            best_times=["morning", "afternoon"],
            current_preferred=True
        ),
        access_info="Accessible by boat or shore",
        facilities=["launch_ramp", "parking", "bait_shop"]
    )
    
    print(f"Created spot: {inlet_spot.name} ({inlet_spot.spot_id})")
    
    # Find spots near a location
    user_location = GPSCoordinate(40.7128, -73.9060)  # NYC area
    nearby_spots = spot_manager.find_spots_near(
        user_location.latitude, user_location.longitude, radius_nm=25.0
    )
    
    print(f"\nFound {len(nearby_spots)} spots within 25 nm of NYC:")
    for spot in nearby_spots:
        print(f"- {spot['name']}: {spot['distance_nm']:.1f} nm away at bearing {spot['bearing']:.0f}°")
    
    # Find spots for specific species
    bass_spots = spot_manager.find_spots_for_species("Striped Bass")
    print(f"\nFound {len(bass_spots)} spots for Striped Bass")
    
    # Get recommendations
    recommendations = spot_manager.get_recommended_spots(user_location, "Striped Bass")
    print(f"\nTop recommendations for Striped Bass:")
    for spot in recommendations[:3]:
        print(f"- {spot['name']}: Rating {spot.get('rating', 'N/A')}, {spot.get('distance_nm', 0):.1f} nm away")
    
    # Record a fishing trip
    success = spot_manager.record_fishing_trip(
        spot_id=reef_spot.spot_id,
        catches=["catch_1", "catch_2"],
        success=True,
        weather_conditions="Light winds, calm seas",
        tide_stage="rising",
        fishing_duration=4.5,
        notes="Great morning bite on live eels"
    )
    
    if success:
        print(f"\nRecorded successful trip to {reef_spot.name}")
    
    # Get spot info with statistics
    spot_info = spot_manager.get_spot_info(reef_spot.spot_id)
    if spot_info:
        print(f"\nSpot statistics for {spot_info['name']}:")
        print(f"- Total visits: {spot_info.get('total_visits', 0)}")
        print(f"- Success rate: {spot_info.get('success_rate', 0):.1f}%")

if __name__ == "__main__":
    asyncio.run(main())