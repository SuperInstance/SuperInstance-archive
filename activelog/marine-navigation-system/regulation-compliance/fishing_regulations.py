"""
Fishing Regulation Compliance Checker
Comprehensive system for checking fishing regulations, seasons, limits, and marine protected areas
"""

import asyncio
import aiohttp
import json
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
import math
from pathlib import Path
import requests
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RegulationType(Enum):
    SIZE_LIMIT = "size_limit"
    BAG_LIMIT = "bag_limit"
    SEASON_CLOSURE = "season_closure"
    AREA_CLOSURE = "area_closure"
    GEAR_RESTRICTION = "gear_restriction"
    LICENSE_REQUIREMENT = "license_requirement"
    MARINE_PROTECTED_AREA = "marine_protected_area"
    SPAWNING_CLOSURE = "spawning_closure"
    QUOTA_LIMIT = "quota_limit"

class ViolationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"

class WaterType(Enum):
    FEDERAL_WATERS = "federal"
    STATE_WATERS = "state"
    INLAND_WATERS = "inland"
    INTERNATIONAL = "international"

@dataclass
class FishingRegulation:
    regulation_id: str
    species_name: str
    scientific_name: str
    regulation_type: RegulationType
    jurisdiction: str  # State, Federal, International
    water_type: WaterType
    area_name: str
    area_coordinates: Optional[List[Tuple[float, float]]] = None
    
    # Size limits
    minimum_size_cm: Optional[float] = None
    maximum_size_cm: Optional[float] = None
    slot_limit_min_cm: Optional[float] = None
    slot_limit_max_cm: Optional[float] = None
    
    # Bag limits
    daily_bag_limit: Optional[int] = None
    possession_limit: Optional[int] = None
    annual_limit: Optional[int] = None
    
    # Season information
    season_start: Optional[date] = None
    season_end: Optional[date] = None
    closed_months: List[int] = field(default_factory=list)  # Month numbers
    
    # Gear restrictions
    allowed_gear: List[str] = field(default_factory=list)
    prohibited_gear: List[str] = field(default_factory=list)
    hook_restrictions: Optional[str] = None
    
    # License requirements
    license_required: bool = True
    special_permit_required: bool = False
    permit_types: List[str] = field(default_factory=list)
    
    # Additional information
    description: str = ""
    penalties: str = ""
    contact_info: str = ""
    last_updated: datetime = field(default_factory=datetime.now)
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None

@dataclass
class MarineProtectedArea:
    area_id: str
    name: str
    designation: str  # National Marine Sanctuary, Marine Reserve, etc.
    jurisdiction: str
    coordinates: List[Tuple[float, float]]
    restrictions: Dict[str, Any] = field(default_factory=dict)
    allowed_activities: List[str] = field(default_factory=list)
    prohibited_activities: List[str] = field(default_factory=list)
    seasonal_restrictions: Dict[str, Any] = field(default_factory=dict)
    contact_info: str = ""
    website: str = ""

@dataclass
class ComplianceViolation:
    violation_id: str
    regulation: FishingRegulation
    violation_type: str
    severity: ViolationSeverity
    description: str
    recommendation: str
    penalty_range: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ComplianceCheck:
    location: Tuple[float, float]
    target_species: List[str]
    fishing_date: date
    gear_types: List[str]
    violations: List[ComplianceViolation] = field(default_factory=list)
    applicable_regulations: List[FishingRegulation] = field(default_factory=list)
    marine_protected_areas: List[MarineProtectedArea] = field(default_factory=list)
    license_requirements: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

class RegulationDatabase:
    """Database manager for fishing regulations"""
    
    def __init__(self, db_path: str = "fishing_regulations.db"):
        self.db_path = db_path
        self._initialize_database()
        self._populate_default_regulations()
    
    def _initialize_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Regulations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regulations (
                regulation_id TEXT PRIMARY KEY,
                species_name TEXT NOT NULL,
                scientific_name TEXT,
                regulation_type TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                water_type TEXT,
                area_name TEXT,
                area_coordinates TEXT,
                minimum_size_cm REAL,
                maximum_size_cm REAL,
                slot_limit_min_cm REAL,
                slot_limit_max_cm REAL,
                daily_bag_limit INTEGER,
                possession_limit INTEGER,
                annual_limit INTEGER,
                season_start TEXT,
                season_end TEXT,
                closed_months TEXT,
                allowed_gear TEXT,
                prohibited_gear TEXT,
                hook_restrictions TEXT,
                license_required BOOLEAN,
                special_permit_required BOOLEAN,
                permit_types TEXT,
                description TEXT,
                penalties TEXT,
                contact_info TEXT,
                effective_date TEXT,
                expiration_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Marine Protected Areas table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS marine_protected_areas (
                area_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                designation TEXT,
                jurisdiction TEXT,
                coordinates TEXT,
                restrictions TEXT,
                allowed_activities TEXT,
                prohibited_activities TEXT,
                seasonal_restrictions TEXT,
                contact_info TEXT,
                website TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Compliance checks table (for history)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compliance_checks (
                check_id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_lat REAL,
                location_lon REAL,
                target_species TEXT,
                fishing_date TEXT,
                gear_types TEXT,
                violations_count INTEGER,
                violations_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _populate_default_regulations(self):
        """Populate database with common fishing regulations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if regulations already exist
        cursor.execute('SELECT COUNT(*) FROM regulations')
        count = cursor.fetchone()[0]
        
        if count == 0:
            default_regulations = self._get_default_regulations()
            for reg in default_regulations:
                self.add_regulation(reg)
            
            default_mpas = self._get_default_marine_protected_areas()
            for mpa in default_mpas:
                self.add_marine_protected_area(mpa)
        
        conn.close()
    
    def _get_default_regulations(self) -> List[FishingRegulation]:
        """Get default fishing regulations for common species"""
        regulations = [
            # Red Snapper - Federal Waters
            FishingRegulation(
                regulation_id="red_snapper_fed_2024",
                species_name="Red Snapper",
                scientific_name="Lutjanus campechanus",
                regulation_type=RegulationType.SIZE_LIMIT,
                jurisdiction="Federal",
                water_type=WaterType.FEDERAL_WATERS,
                area_name="Gulf of Mexico Federal Waters",
                minimum_size_cm=40.6,  # 16 inches
                daily_bag_limit=2,
                season_start=date(2024, 6, 1),
                season_end=date(2024, 7, 31),
                description="Federal red snapper regulations for recreational fishing",
                penalties="Up to $100,000 fine and/or 1 year imprisonment",
                contact_info="NOAA Fisheries: (727) 824-5301"
            ),
            
            # Red Snapper - State Waters (Florida)
            FishingRegulation(
                regulation_id="red_snapper_fl_2024",
                species_name="Red Snapper",
                scientific_name="Lutjanus campechanus",
                regulation_type=RegulationType.SIZE_LIMIT,
                jurisdiction="Florida",
                water_type=WaterType.STATE_WATERS,
                area_name="Florida State Waters",
                minimum_size_cm=50.8,  # 20 inches
                daily_bag_limit=1,
                season_start=date(2024, 6, 11),
                season_end=date(2024, 7, 24),
                description="Florida state waters red snapper regulations",
                contact_info="Florida Fish and Wildlife: (850) 488-4676"
            ),
            
            # Grouper - Size and Season
            FishingRegulation(
                regulation_id="grouper_fed_2024",
                species_name="Red Grouper",
                scientific_name="Epinephelus morio",
                regulation_type=RegulationType.SIZE_LIMIT,
                jurisdiction="Federal",
                water_type=WaterType.FEDERAL_WATERS,
                area_name="South Atlantic Federal Waters",
                minimum_size_cm=50.8,  # 20 inches
                daily_bag_limit=1,
                closed_months=[1, 2, 3, 4],  # Jan-Apr closure
                description="Red grouper size and bag limits",
                contact_info="NOAA Fisheries Southeast: (727) 824-5301"
            ),
            
            # Billfish - Prohibited
            FishingRegulation(
                regulation_id="billfish_atlantic_2024",
                species_name="Blue Marlin",
                scientific_name="Makaira nigricans",
                regulation_type=RegulationType.BAG_LIMIT,
                jurisdiction="Federal",
                water_type=WaterType.FEDERAL_WATERS,
                area_name="Atlantic Ocean",
                daily_bag_limit=0,  # Catch and release only
                description="Billfish must be released immediately",
                penalties="Up to $100,000 fine",
                contact_info="NOAA Fisheries: (727) 824-5301"
            ),
            
            # Striped Bass - Size Limits
            FishingRegulation(
                regulation_id="striped_bass_2024",
                species_name="Striped Bass",
                scientific_name="Morone saxatilis",
                regulation_type=RegulationType.SIZE_LIMIT,
                jurisdiction="Federal",
                water_type=WaterType.FEDERAL_WATERS,
                area_name="Atlantic Coast",
                slot_limit_min_cm=71.1,  # 28 inches
                slot_limit_max_cm=88.9,  # 35 inches
                daily_bag_limit=1,
                description="Striped bass slot limit - only fish 28-35 inches may be kept",
                contact_info="Atlantic States Marine Fisheries Commission"
            ),
            
            # Shark Regulations
            FishingRegulation(
                regulation_id="shark_prohibited_2024",
                species_name="Great White Shark",
                scientific_name="Carcharodon carcharias",
                regulation_type=RegulationType.BAG_LIMIT,
                jurisdiction="Federal",
                water_type=WaterType.FEDERAL_WATERS,
                area_name="All US Waters",
                daily_bag_limit=0,
                description="Prohibited species - must be released immediately",
                penalties="Up to $100,000 fine and/or 1 year imprisonment",
                special_permit_required=True
            )
        ]
        
        return regulations
    
    def _get_default_marine_protected_areas(self) -> List[MarineProtectedArea]:
        """Get default marine protected areas"""
        mpas = [
            MarineProtectedArea(
                area_id="florida_keys_nms",
                name="Florida Keys National Marine Sanctuary",
                designation="National Marine Sanctuary",
                jurisdiction="Federal",
                coordinates=[
                    (25.7617, -80.1918),
                    (24.3963, -81.8463),
                    (24.4469, -83.0937),
                    (25.6581, -80.0334)
                ],
                prohibited_activities=[
                    "spearfishing", "collecting", "anchoring on coral",
                    "discharge", "drilling", "dredging"
                ],
                allowed_activities=[
                    "hook_and_line_fishing", "diving", "snorkeling",
                    "boating", "research"
                ],
                restrictions={
                    "fishing": "Hook and line only in most areas",
                    "anchoring": "Mooring buoys required in sensitive areas",
                    "speed": "Idle speed zones in shallow areas"
                },
                contact_info="Florida Keys National Marine Sanctuary: (305) 809-4700",
                website="https://floridakeys.noaa.gov"
            ),
            
            MarineProtectedArea(
                area_id="dry_tortugas_np",
                name="Dry Tortugas National Park",
                designation="National Park",
                jurisdiction="Federal",
                coordinates=[
                    (24.6285, -82.8732),
                    (24.6285, -82.7732),
                    (24.5285, -82.7732),
                    (24.5285, -82.8732)
                ],
                prohibited_activities=[
                    "fishing", "collecting", "spearfishing", "anchoring",
                    "touching_coral", "feeding_wildlife"
                ],
                allowed_activities=[
                    "diving", "snorkeling", "photography", "research"
                ],
                restrictions={
                    "access": "Research Natural Area - no entry without permit",
                    "fishing": "Prohibited in Research Natural Area"
                },
                contact_info="Dry Tortugas National Park: (305) 242-7700"
            )
        ]
        
        return mpas
    
    def add_regulation(self, regulation: FishingRegulation):
        """Add regulation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert complex fields to JSON
        area_coords = json.dumps(regulation.area_coordinates) if regulation.area_coordinates else None
        closed_months = json.dumps(regulation.closed_months)
        allowed_gear = json.dumps(regulation.allowed_gear)
        prohibited_gear = json.dumps(regulation.prohibited_gear)
        permit_types = json.dumps(regulation.permit_types)
        
        cursor.execute('''
            INSERT OR REPLACE INTO regulations VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
            )
        ''', (
            regulation.regulation_id,
            regulation.species_name,
            regulation.scientific_name,
            regulation.regulation_type.value,
            regulation.jurisdiction,
            regulation.water_type.value,
            regulation.area_name,
            area_coords,
            regulation.minimum_size_cm,
            regulation.maximum_size_cm,
            regulation.slot_limit_min_cm,
            regulation.slot_limit_max_cm,
            regulation.daily_bag_limit,
            regulation.possession_limit,
            regulation.annual_limit,
            regulation.season_start.isoformat() if regulation.season_start else None,
            regulation.season_end.isoformat() if regulation.season_end else None,
            closed_months,
            allowed_gear,
            prohibited_gear,
            regulation.hook_restrictions,
            regulation.license_required,
            regulation.special_permit_required,
            permit_types,
            regulation.description,
            regulation.penalties,
            regulation.contact_info,
            regulation.effective_date.isoformat() if regulation.effective_date else None,
            regulation.expiration_date.isoformat() if regulation.expiration_date else None
        ))
        
        conn.commit()
        conn.close()
    
    def add_marine_protected_area(self, mpa: MarineProtectedArea):
        """Add marine protected area to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO marine_protected_areas VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
            )
        ''', (
            mpa.area_id,
            mpa.name,
            mpa.designation,
            mpa.jurisdiction,
            json.dumps(mpa.coordinates),
            json.dumps(mpa.restrictions),
            json.dumps(mpa.allowed_activities),
            json.dumps(mpa.prohibited_activities),
            json.dumps(mpa.seasonal_restrictions),
            mpa.contact_info,
            mpa.website
        ))
        
        conn.commit()
        conn.close()
    
    def get_regulations_for_species(self, species_name: str) -> List[FishingRegulation]:
        """Get all regulations for a species"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM regulations 
            WHERE species_name = ? OR scientific_name = ?
        ''', (species_name, species_name))
        
        regulations = []
        for row in cursor.fetchall():
            regulation = self._row_to_regulation(row)
            regulations.append(regulation)
        
        conn.close()
        return regulations
    
    def get_regulations_for_location(self, lat: float, lon: float) -> List[FishingRegulation]:
        """Get regulations applicable to a location"""
        # This is a simplified version - in practice, you'd do proper geographic queries
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM regulations')
        all_regulations = []
        
        for row in cursor.fetchall():
            regulation = self._row_to_regulation(row)
            
            # Check if location is in area (simplified check)
            if regulation.area_coordinates:
                if self._point_in_area(lat, lon, regulation.area_coordinates):
                    all_regulations.append(regulation)
            else:
                # If no specific coordinates, include regulation
                all_regulations.append(regulation)
        
        conn.close()
        return all_regulations
    
    def get_marine_protected_areas_for_location(self, lat: float, lon: float) -> List[MarineProtectedArea]:
        """Get MPAs that contain the specified location"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM marine_protected_areas')
        mpas = []
        
        for row in cursor.fetchall():
            mpa = self._row_to_mpa(row)
            
            if self._point_in_area(lat, lon, mpa.coordinates):
                mpas.append(mpa)
        
        conn.close()
        return mpas
    
    def _row_to_regulation(self, row) -> FishingRegulation:
        """Convert database row to FishingRegulation object"""
        return FishingRegulation(
            regulation_id=row[0],
            species_name=row[1],
            scientific_name=row[2] or "",
            regulation_type=RegulationType(row[3]),
            jurisdiction=row[4],
            water_type=WaterType(row[5]) if row[5] else WaterType.FEDERAL_WATERS,
            area_name=row[6] or "",
            area_coordinates=json.loads(row[7]) if row[7] else None,
            minimum_size_cm=row[8],
            maximum_size_cm=row[9],
            slot_limit_min_cm=row[10],
            slot_limit_max_cm=row[11],
            daily_bag_limit=row[12],
            possession_limit=row[13],
            annual_limit=row[14],
            season_start=date.fromisoformat(row[15]) if row[15] else None,
            season_end=date.fromisoformat(row[16]) if row[16] else None,
            closed_months=json.loads(row[17]) if row[17] else [],
            allowed_gear=json.loads(row[18]) if row[18] else [],
            prohibited_gear=json.loads(row[19]) if row[19] else [],
            hook_restrictions=row[20],
            license_required=bool(row[21]) if row[21] is not None else True,
            special_permit_required=bool(row[22]) if row[22] is not None else False,
            permit_types=json.loads(row[23]) if row[23] else [],
            description=row[24] or "",
            penalties=row[25] or "",
            contact_info=row[26] or "",
            effective_date=date.fromisoformat(row[27]) if row[27] else None,
            expiration_date=date.fromisoformat(row[28]) if row[28] else None
        )
    
    def _row_to_mpa(self, row) -> MarineProtectedArea:
        """Convert database row to MarineProtectedArea object"""
        return MarineProtectedArea(
            area_id=row[0],
            name=row[1],
            designation=row[2] or "",
            jurisdiction=row[3] or "",
            coordinates=json.loads(row[4]) if row[4] else [],
            restrictions=json.loads(row[5]) if row[5] else {},
            allowed_activities=json.loads(row[6]) if row[6] else [],
            prohibited_activities=json.loads(row[7]) if row[7] else [],
            seasonal_restrictions=json.loads(row[8]) if row[8] else {},
            contact_info=row[9] or "",
            website=row[10] or ""
        )
    
    def _point_in_area(self, lat: float, lon: float, coordinates: List[Tuple[float, float]]) -> bool:
        """Check if point is within area defined by coordinates"""
        try:
            if len(coordinates) < 3:
                return False
            
            # Use shapely for accurate point-in-polygon test
            point = Point(lon, lat)
            polygon = Polygon([(coord[1], coord[0]) for coord in coordinates])
            return polygon.contains(point)
            
        except Exception as e:
            logger.error(f"Error checking point in area: {e}")
            return False

class RegulationChecker:
    """Main regulation compliance checker"""
    
    def __init__(self):
        self.database = RegulationDatabase()
        self.current_date = date.today()
    
    async def check_compliance(self, location: Tuple[float, float],
                             target_species: List[str],
                             fishing_date: date = None,
                             gear_types: List[str] = None,
                             fish_sizes: Dict[str, float] = None,
                             catch_counts: Dict[str, int] = None) -> ComplianceCheck:
        """Perform comprehensive compliance check"""
        
        if fishing_date is None:
            fishing_date = self.current_date
        
        if gear_types is None:
            gear_types = []
        
        lat, lon = location
        
        # Get applicable regulations
        location_regulations = self.database.get_regulations_for_location(lat, lon)
        
        # Filter regulations by target species
        applicable_regulations = []
        for species in target_species:
            species_regulations = self.database.get_regulations_for_species(species)
            applicable_regulations.extend(species_regulations)
        
        # Remove duplicates
        applicable_regulations = list({reg.regulation_id: reg for reg in applicable_regulations}.values())
        
        # Get marine protected areas
        mpas = self.database.get_marine_protected_areas_for_location(lat, lon)
        
        # Check for violations
        violations = []
        recommendations = []
        license_requirements = []
        
        for regulation in applicable_regulations:
            # Check season closure
            if self._is_season_closed(regulation, fishing_date):
                violations.append(ComplianceViolation(
                    violation_id=f"season_{regulation.regulation_id}",
                    regulation=regulation,
                    violation_type="season_closure",
                    severity=ViolationSeverity.VIOLATION,
                    description=f"{regulation.species_name} season is closed on {fishing_date}",
                    recommendation=f"Season opens {regulation.season_start} to {regulation.season_end}",
                    penalty_range=regulation.penalties
                ))
            
            # Check size limits
            if fish_sizes and regulation.species_name in fish_sizes:
                size_cm = fish_sizes[regulation.species_name]
                size_violation = self._check_size_limit(regulation, size_cm)
                if size_violation:
                    violations.append(size_violation)
            
            # Check bag limits
            if catch_counts and regulation.species_name in catch_counts:
                count = catch_counts[regulation.species_name]
                bag_violation = self._check_bag_limit(regulation, count)
                if bag_violation:
                    violations.append(bag_violation)
            
            # Check gear restrictions
            if gear_types:
                gear_violations = self._check_gear_restrictions(regulation, gear_types)
                violations.extend(gear_violations)
            
            # Collect license requirements
            if regulation.license_required:
                license_requirements.append(f"{regulation.jurisdiction} fishing license required")
            
            if regulation.special_permit_required:
                for permit in regulation.permit_types:
                    license_requirements.append(f"Special permit required: {permit}")
        
        # Check marine protected area restrictions
        for mpa in mpas:
            mpa_violations = self._check_mpa_restrictions(mpa, gear_types, target_species)
            violations.extend(mpa_violations)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            applicable_regulations, violations, fishing_date, location
        )
        
        # Create compliance check result
        compliance_check = ComplianceCheck(
            location=location,
            target_species=target_species,
            fishing_date=fishing_date,
            gear_types=gear_types,
            violations=violations,
            applicable_regulations=applicable_regulations,
            marine_protected_areas=mpas,
            license_requirements=list(set(license_requirements)),
            recommendations=recommendations
        )
        
        # Save compliance check to database
        self._save_compliance_check(compliance_check)
        
        return compliance_check
    
    def _is_season_closed(self, regulation: FishingRegulation, check_date: date) -> bool:
        """Check if fishing season is closed for the species"""
        current_month = check_date.month
        
        # Check closed months
        if current_month in regulation.closed_months:
            return True
        
        # Check season dates
        if regulation.season_start and regulation.season_end:
            if not (regulation.season_start <= check_date <= regulation.season_end):
                return True
        
        return False
    
    def _check_size_limit(self, regulation: FishingRegulation, 
                         fish_size_cm: float) -> Optional[ComplianceViolation]:
        """Check size limit compliance"""
        
        # Minimum size limit
        if regulation.minimum_size_cm and fish_size_cm < regulation.minimum_size_cm:
            return ComplianceViolation(
                violation_id=f"size_min_{regulation.regulation_id}",
                regulation=regulation,
                violation_type="undersized",
                severity=ViolationSeverity.VIOLATION,
                description=f"{regulation.species_name} is undersized: {fish_size_cm:.1f}cm "
                           f"(minimum: {regulation.minimum_size_cm:.1f}cm)",
                recommendation="Release fish immediately",
                penalty_range=regulation.penalties
            )
        
        # Maximum size limit
        if regulation.maximum_size_cm and fish_size_cm > regulation.maximum_size_cm:
            return ComplianceViolation(
                violation_id=f"size_max_{regulation.regulation_id}",
                regulation=regulation,
                violation_type="oversized",
                severity=ViolationSeverity.VIOLATION,
                description=f"{regulation.species_name} is oversized: {fish_size_cm:.1f}cm "
                           f"(maximum: {regulation.maximum_size_cm:.1f}cm)",
                recommendation="Release fish immediately",
                penalty_range=regulation.penalties
            )
        
        # Slot limit
        if (regulation.slot_limit_min_cm and regulation.slot_limit_max_cm and
            not (regulation.slot_limit_min_cm <= fish_size_cm <= regulation.slot_limit_max_cm)):
            return ComplianceViolation(
                violation_id=f"slot_limit_{regulation.regulation_id}",
                regulation=regulation,
                violation_type="outside_slot_limit",
                severity=ViolationSeverity.VIOLATION,
                description=f"{regulation.species_name} outside slot limit: {fish_size_cm:.1f}cm "
                           f"(slot: {regulation.slot_limit_min_cm:.1f}-{regulation.slot_limit_max_cm:.1f}cm)",
                recommendation="Release fish immediately - only fish within slot limit may be kept",
                penalty_range=regulation.penalties
            )
        
        return None
    
    def _check_bag_limit(self, regulation: FishingRegulation, 
                        catch_count: int) -> Optional[ComplianceViolation]:
        """Check bag limit compliance"""
        
        # Daily bag limit
        if regulation.daily_bag_limit is not None and catch_count > regulation.daily_bag_limit:
            severity = ViolationSeverity.CRITICAL if regulation.daily_bag_limit == 0 else ViolationSeverity.VIOLATION
            
            return ComplianceViolation(
                violation_id=f"bag_limit_{regulation.regulation_id}",
                regulation=regulation,
                violation_type="over_bag_limit",
                severity=severity,
                description=f"Over daily bag limit for {regulation.species_name}: {catch_count} "
                           f"(limit: {regulation.daily_bag_limit})",
                recommendation="Release excess fish immediately" if regulation.daily_bag_limit > 0 
                              else "This species must be released - no retention allowed",
                penalty_range=regulation.penalties
            )
        
        return None
    
    def _check_gear_restrictions(self, regulation: FishingRegulation, 
                               gear_types: List[str]) -> List[ComplianceViolation]:
        """Check gear restriction compliance"""
        violations = []
        
        # Check prohibited gear
        for gear in gear_types:
            if gear in regulation.prohibited_gear:
                violations.append(ComplianceViolation(
                    violation_id=f"gear_prohibited_{regulation.regulation_id}_{gear}",
                    regulation=regulation,
                    violation_type="prohibited_gear",
                    severity=ViolationSeverity.VIOLATION,
                    description=f"Prohibited gear for {regulation.species_name}: {gear}",
                    recommendation=f"Use allowed gear: {', '.join(regulation.allowed_gear)}",
                    penalty_range=regulation.penalties
                ))
        
        # Check if using only allowed gear (if specified)
        if regulation.allowed_gear:
            for gear in gear_types:
                if gear not in regulation.allowed_gear:
                    violations.append(ComplianceViolation(
                        violation_id=f"gear_not_allowed_{regulation.regulation_id}_{gear}",
                        regulation=regulation,
                        violation_type="gear_not_allowed",
                        severity=ViolationSeverity.WARNING,
                        description=f"Gear not specifically allowed for {regulation.species_name}: {gear}",
                        recommendation=f"Verify gear is legal. Allowed gear: {', '.join(regulation.allowed_gear)}",
                        penalty_range=regulation.penalties
                    ))
        
        return violations
    
    def _check_mpa_restrictions(self, mpa: MarineProtectedArea, 
                              gear_types: List[str], 
                              target_species: List[str]) -> List[ComplianceViolation]:
        """Check marine protected area restrictions"""
        violations = []
        
        # Check prohibited activities
        for activity in ["fishing", "spearfishing", "collecting"]:
            if activity in mpa.prohibited_activities:
                if (activity == "fishing" or 
                    (activity == "spearfishing" and "spear" in " ".join(gear_types).lower()) or
                    (activity == "collecting" and any("collect" in species.lower() for species in target_species))):
                    
                    violations.append(ComplianceViolation(
                        violation_id=f"mpa_prohibited_{mpa.area_id}_{activity}",
                        regulation=FishingRegulation(
                            regulation_id=mpa.area_id,
                            species_name="All Species",
                            scientific_name="",
                            regulation_type=RegulationType.AREA_CLOSURE,
                            jurisdiction=mpa.jurisdiction,
                            water_type=WaterType.FEDERAL_WATERS,
                            area_name=mpa.name,
                            description=f"{activity} prohibited in {mpa.name}"
                        ),
                        violation_type="mpa_violation",
                        severity=ViolationSeverity.CRITICAL,
                        description=f"{activity.title()} is prohibited in {mpa.name}",
                        recommendation=f"Leave the area immediately. Contact: {mpa.contact_info}",
                        penalty_range="Up to $100,000 fine and/or imprisonment"
                    ))
        
        return violations
    
    def _generate_recommendations(self, regulations: List[FishingRegulation],
                                violations: List[ComplianceViolation],
                                fishing_date: date,
                                location: Tuple[float, float]) -> List[str]:
        """Generate helpful recommendations"""
        recommendations = []
        
        if violations:
            recommendations.append("⚠️ COMPLIANCE VIOLATIONS DETECTED - Review all violations before fishing")
        
        # Season recommendations
        for regulation in regulations:
            if regulation.season_start and regulation.season_end:
                days_until_open = (regulation.season_start - fishing_date).days
                days_until_closed = (regulation.season_end - fishing_date).days
                
                if days_until_open > 0:
                    recommendations.append(
                        f"📅 {regulation.species_name} season opens in {days_until_open} days "
                        f"({regulation.season_start})"
                    )
                elif 0 <= days_until_closed <= 7:
                    recommendations.append(
                        f"⏰ {regulation.species_name} season closes in {days_until_closed} days "
                        f"({regulation.season_end})"
                    )
        
        # Size limit reminders
        for regulation in regulations:
            if regulation.minimum_size_cm:
                recommendations.append(
                    f"📏 {regulation.species_name} minimum size: {regulation.minimum_size_cm:.1f}cm "
                    f"({regulation.minimum_size_cm/2.54:.1f} inches)"
                )
            
            if regulation.slot_limit_min_cm and regulation.slot_limit_max_cm:
                recommendations.append(
                    f"📏 {regulation.species_name} slot limit: "
                    f"{regulation.slot_limit_min_cm:.1f}-{regulation.slot_limit_max_cm:.1f}cm"
                )
        
        # General recommendations
        recommendations.extend([
            "🎣 Always carry proper identification and licenses",
            "📱 Keep regulations app updated with latest rules",
            "🐟 Practice catch and release for conservation",
            "📋 Record catches in fishing log for quota species"
        ])
        
        return recommendations[:10]  # Limit to 10 recommendations
    
    def _save_compliance_check(self, check: ComplianceCheck):
        """Save compliance check to database"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO compliance_checks (
                location_lat, location_lon, target_species, fishing_date,
                gear_types, violations_count, violations_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            check.location[0],
            check.location[1],
            json.dumps(check.target_species),
            check.fishing_date.isoformat(),
            json.dumps(check.gear_types),
            len(check.violations),
            json.dumps([{
                'violation_id': v.violation_id,
                'violation_type': v.violation_type,
                'severity': v.severity.value,
                'description': v.description
            } for v in check.violations])
        ))
        
        conn.commit()
        conn.close()
    
    def get_water_type(self, location: Tuple[float, float]) -> WaterType:
        """Determine water type based on location"""
        lat, lon = location
        
        # Simplified water type determination
        # In practice, this would use official boundary data
        
        # Very rough approximation for US waters
        if abs(lat) > 60:  # Arctic/Antarctic
            return WaterType.INTERNATIONAL
        
        # Rough US state waters boundary (3 nautical miles = ~0.05 degrees)
        us_coast_distance = self._distance_to_us_coast(lat, lon)
        
        if us_coast_distance < 5.56:  # ~3 nautical miles
            return WaterType.STATE_WATERS
        elif us_coast_distance < 370.4:  # ~200 nautical miles EEZ
            return WaterType.FEDERAL_WATERS
        else:
            return WaterType.INTERNATIONAL
    
    def _distance_to_us_coast(self, lat: float, lon: float) -> float:
        """Estimate distance to US coast (simplified)"""
        # Very simplified - in practice would use official coastline data
        us_coast_points = [
            (25.7617, -80.1918),  # Miami
            (30.3322, -81.6557),  # Jacksonville
            (32.0835, -81.0998),  # Savannah
            (36.8529, -75.9780),  # Norfolk
            (40.7589, -73.9851),  # New York
            (42.3601, -71.0589),  # Boston
        ]
        
        min_distance = float('inf')
        for coast_lat, coast_lon in us_coast_points:
            distance = math.sqrt((lat - coast_lat)**2 + (lon - coast_lon)**2) * 111.32  # Convert to km
            min_distance = min(min_distance, distance)
        
        return min_distance
    
    async def update_regulations_from_api(self):
        """Update regulations from official APIs (placeholder)"""
        logger.info("Updating regulations from official sources...")
        
        try:
            # Placeholder for API updates
            # In practice, would call NOAA, state fish & wildlife APIs
            await self._update_noaa_regulations()
            await self._update_state_regulations()
            
        except Exception as e:
            logger.error(f"Error updating regulations: {e}")
    
    async def _update_noaa_regulations(self):
        """Update federal regulations from NOAA"""
        # Placeholder - would implement actual NOAA API calls
        logger.info("Updated NOAA federal regulations")
    
    async def _update_state_regulations(self):
        """Update state regulations"""
        # Placeholder - would implement state API calls
        logger.info("Updated state regulations")

# Example usage and testing
async def example_usage():
    """Example of using the regulation compliance checker"""
    
    # Create regulation checker
    checker = RegulationChecker()
    
    # Example compliance check
    location = (25.7617, -80.1918)  # Miami, FL
    target_species = ["Red Snapper", "Red Grouper"]
    fishing_date = date(2024, 6, 15)
    gear_types = ["hook_and_line", "rod_and_reel"]
    
    # Fish sizes (in cm)
    fish_sizes = {
        "Red Snapper": 35.0,  # Undersized
        "Red Grouper": 55.0   # Legal size
    }
    
    # Catch counts
    catch_counts = {
        "Red Snapper": 3,  # Over limit
        "Red Grouper": 1   # Within limit
    }
    
    # Perform compliance check
    compliance_check = await checker.check_compliance(
        location=location,
        target_species=target_species,
        fishing_date=fishing_date,
        gear_types=gear_types,
        fish_sizes=fish_sizes,
        catch_counts=catch_counts
    )
    
    # Print results
    print("=== FISHING REGULATION COMPLIANCE CHECK ===")
    print(f"Location: {location}")
    print(f"Date: {fishing_date}")
    print(f"Target Species: {', '.join(target_species)}")
    print()
    
    print("VIOLATIONS:")
    if compliance_check.violations:
        for violation in compliance_check.violations:
            severity_emoji = {
                ViolationSeverity.INFO: "ℹ️",
                ViolationSeverity.WARNING: "⚠️",
                ViolationSeverity.VIOLATION: "🚫",
                ViolationSeverity.CRITICAL: "🔴"
            }
            print(f"{severity_emoji[violation.severity]} {violation.description}")
            print(f"   Recommendation: {violation.recommendation}")
            if violation.penalty_range:
                print(f"   Penalty: {violation.penalty_range}")
            print()
    else:
        print("✅ No violations detected")
    
    print("LICENSE REQUIREMENTS:")
    for requirement in compliance_check.license_requirements:
        print(f"📋 {requirement}")
    
    print("\nMARINE PROTECTED AREAS:")
    for mpa in compliance_check.marine_protected_areas:
        print(f"🏛️ {mpa.name} ({mpa.designation})")
        if mpa.prohibited_activities:
            print(f"   Prohibited: {', '.join(mpa.prohibited_activities)}")
    
    print("\nRECOMMENDATIONS:")
    for recommendation in compliance_check.recommendations:
        print(f"{recommendation}")
    
    print(f"\nApplicable Regulations: {len(compliance_check.applicable_regulations)}")
    for regulation in compliance_check.applicable_regulations[:3]:  # Show first 3
        print(f"• {regulation.species_name} - {regulation.jurisdiction} ({regulation.area_name})")

if __name__ == "__main__":
    asyncio.run(example_usage())