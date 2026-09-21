"""
ActiveLog Marine Advanced Suite - Automatic Logbook Generation

Intelligent automatic logbook system with AI-powered entry generation, regulatory compliance,
voyage documentation, and comprehensive maritime record keeping.
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
import uuid
from jinja2 import Template
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import base64
import warnings
warnings.filterwarnings('ignore')


class LogEntryType(Enum):
    NAVIGATION = "navigation"
    WEATHER = "weather"
    ENGINE = "engine"
    MAINTENANCE = "maintenance"
    CREW = "crew"
    SAFETY = "safety"
    COMMUNICATION = "communication"
    CARGO = "cargo"
    FUEL = "fuel"
    CUSTOMS = "customs"
    INCIDENT = "incident"
    ARRIVAL = "arrival"
    DEPARTURE = "departure"
    WAYPOINT = "waypoint"


class LogEntryPriority(Enum):
    ROUTINE = "routine"
    IMPORTANT = "important"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class WeatherObservation(Enum):
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    FOG = "fog"
    RAIN = "rain"
    DRIZZLE = "drizzle"
    SQUALLS = "squalls"
    THUNDERSTORMS = "thunderstorms"


class SeaCondition(Enum):
    CALM = "calm"
    SMOOTH = "smooth"
    SLIGHT = "slight"
    MODERATE = "moderate"
    ROUGH = "rough"
    VERY_ROUGH = "very_rough"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class VesselPosition:
    timestamp: datetime
    latitude: float
    longitude: float
    course_over_ground: float
    speed_over_ground: float
    heading: float
    distance_run: float           # nautical miles since last entry
    position_source: str          # "GPS", "DGPS", "ECDIS", "DR"
    position_accuracy: float      # meters


@dataclass
class WeatherData:
    timestamp: datetime
    wind_direction: float         # degrees true
    wind_speed: float            # knots
    wind_force: int              # Beaufort scale
    barometric_pressure: float   # millibars
    air_temperature: float       # Celsius
    sea_temperature: float       # Celsius
    visibility: float            # nautical miles
    cloud_cover: int             # oktas (0-8)
    weather_observation: WeatherObservation
    sea_condition: SeaCondition
    wave_height: float           # meters
    wave_period: float           # seconds
    swell_direction: Optional[float]  # degrees true
    swell_height: Optional[float]     # meters


@dataclass
class EngineData:
    timestamp: datetime
    engine_id: str
    engine_hours: float
    rpm: int
    engine_temperature: float    # Celsius
    oil_pressure: float          # bar
    fuel_consumption: float      # liters/hour
    engine_load: float           # percentage
    coolant_temperature: float   # Celsius
    exhaust_temperature: float   # Celsius
    status: str                  # "running", "stopped", "maintenance"
    alarms: List[str]


@dataclass
class CrewEntry:
    timestamp: datetime
    crew_member_id: str
    name: str
    rank: str
    watch_duty: Optional[str]
    action: str                  # "sign_on", "sign_off", "watch_change", "rest"
    notes: Optional[str]


@dataclass
class SafetyEntry:
    timestamp: datetime
    safety_check_type: str       # "fire_drill", "boat_drill", "safety_round"
    personnel_involved: List[str]
    equipment_tested: List[str]
    results: str
    deficiencies: List[str]
    corrective_actions: List[str]


@dataclass
class MaintenanceEntry:
    timestamp: datetime
    equipment_id: str
    equipment_name: str
    maintenance_type: str        # "routine", "corrective", "preventive"
    work_performed: str
    parts_used: List[str]
    personnel: str
    next_service_date: Optional[datetime]
    status: str                  # "completed", "in_progress", "scheduled"


@dataclass
class LogEntry:
    entry_id: str
    timestamp: datetime
    entry_type: LogEntryType
    priority: LogEntryPriority
    watch_officer: str
    summary: str
    details: str
    position_data: Optional[VesselPosition]
    weather_data: Optional[WeatherData]
    engine_data: Optional[List[EngineData]]
    crew_data: Optional[CrewEntry]
    safety_data: Optional[SafetyEntry]
    maintenance_data: Optional[MaintenanceEntry]
    attachments: List[str]       # File references
    auto_generated: bool
    verified: bool
    compliance_flags: List[str]  # Regulatory compliance markers


@dataclass
class VoyageLog:
    voyage_id: str
    vessel_name: str
    vessel_imo: str
    voyage_number: str
    departure_port: str
    departure_date: datetime
    destination_port: str
    estimated_arrival: datetime
    actual_arrival: Optional[datetime]
    master_name: str
    chief_officer: str
    entries: List[LogEntry]
    total_distance: float        # nautical miles
    fuel_consumed: float         # liters
    avg_speed: float            # knots
    max_speed: float            # knots
    compliance_status: Dict[str, bool]


class AutomaticLogbookSystem:
    """Intelligent automatic logbook generation system"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.active_voyages: Dict[str, VoyageLog] = {}
        self.log_entries: Dict[str, List[LogEntry]] = {}
        self.auto_logging_enabled = True
        self.entry_interval = 3600  # seconds (1 hour default)
        self.last_position: Optional[VesselPosition] = None
        self.last_weather: Optional[WeatherData] = None
        self.last_engine_data: Dict[str, EngineData] = {}
        
        # Regulatory compliance templates
        self.compliance_templates = {
            'SOLAS': ['safety_equipment', 'fire_drill', 'boat_drill', 'navigation_watch'],
            'MARPOL': ['oil_record', 'garbage_record', 'ballast_water'],
            'STCW': ['watch_keeping', 'rest_hours', 'training_records'],
            'MLC': ['crew_welfare', 'working_hours', 'accommodation']
        }
        
        # Natural language templates for entry generation
        self.entry_templates = self._initialize_templates()
        
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize logbook database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Voyages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voyages (
                voyage_id TEXT PRIMARY KEY,
                vessel_name TEXT,
                vessel_imo TEXT,
                voyage_number TEXT,
                departure_port TEXT,
                departure_date TIMESTAMP,
                destination_port TEXT,
                estimated_arrival TIMESTAMP,
                actual_arrival TIMESTAMP,
                master_name TEXT,
                chief_officer TEXT,
                total_distance REAL,
                fuel_consumed REAL,
                avg_speed REAL,
                max_speed REAL,
                compliance_status TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Log entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_entries (
                entry_id TEXT PRIMARY KEY,
                voyage_id TEXT,
                timestamp TIMESTAMP,
                entry_type TEXT,
                priority TEXT,
                watch_officer TEXT,
                summary TEXT,
                details TEXT,
                position_data TEXT,  -- JSON
                weather_data TEXT,   -- JSON
                engine_data TEXT,    -- JSON
                crew_data TEXT,      -- JSON
                safety_data TEXT,    -- JSON
                maintenance_data TEXT, -- JSON
                attachments TEXT,    -- JSON
                auto_generated BOOLEAN,
                verified BOOLEAN,
                compliance_flags TEXT, -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (voyage_id) REFERENCES voyages (voyage_id)
            )
        """)
        
        # Position history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS position_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voyage_id TEXT,
                timestamp TIMESTAMP,
                latitude REAL,
                longitude REAL,
                course_over_ground REAL,
                speed_over_ground REAL,
                heading REAL,
                distance_run REAL,
                position_source TEXT,
                position_accuracy REAL,
                FOREIGN KEY (voyage_id) REFERENCES voyages (voyage_id)
            )
        """)
        
        # Weather observations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voyage_id TEXT,
                timestamp TIMESTAMP,
                wind_direction REAL,
                wind_speed REAL,
                wind_force INTEGER,
                barometric_pressure REAL,
                air_temperature REAL,
                sea_temperature REAL,
                visibility REAL,
                cloud_cover INTEGER,
                weather_observation TEXT,
                sea_condition TEXT,
                wave_height REAL,
                wave_period REAL,
                swell_direction REAL,
                swell_height REAL,
                FOREIGN KEY (voyage_id) REFERENCES voyages (voyage_id)
            )
        """)
        
        # Engine logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS engine_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voyage_id TEXT,
                timestamp TIMESTAMP,
                engine_id TEXT,
                engine_hours REAL,
                rpm INTEGER,
                engine_temperature REAL,
                oil_pressure REAL,
                fuel_consumption REAL,
                engine_load REAL,
                coolant_temperature REAL,
                exhaust_temperature REAL,
                status TEXT,
                alarms TEXT,  -- JSON
                FOREIGN KEY (voyage_id) REFERENCES voyages (voyage_id)
            )
        """)
        
        # Create indices
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_log_entries_voyage_time 
            ON log_entries (voyage_id, timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_position_history_voyage_time 
            ON position_history (voyage_id, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def _initialize_templates(self) -> Dict[str, str]:
        """Initialize natural language templates for log entries"""
        return {
            'navigation': """{{ timestamp.strftime('%H:%M') }} - Position: {{ "%.4f"|format(position.latitude) }}°N {{ "%.4f"|format(position.longitude|abs) }}°W, 
Course: {{ position.course_over_ground|round(0) }}°T, Speed: {{ position.speed_over_ground|round(1) }} knots, 
Distance run: {{ position.distance_run|round(1) }} nm. {% if position.position_source == 'GPS' %}GPS fix good.{% endif %}""",
            
            'weather': """{{ timestamp.strftime('%H:%M') }} - Weather: {{ weather.weather_observation.value|title }}, 
Wind: {{ weather.wind_direction|round(0) }}°T {{ weather.wind_speed|round(0) }} knots (Force {{ weather.wind_force }}), 
Barometer: {{ weather.barometric_pressure|round(1) }} mb, Air temp: {{ weather.air_temperature|round(0) }}°C, 
Sea: {{ weather.sea_condition.value|title }} {{ weather.wave_height|round(1) }}m, Visibility: {{ weather.visibility|round(0) }} nm.""",
            
            'engine': """{{ timestamp.strftime('%H:%M') }} - Engine {{ engine.engine_id }}: Running {{ engine.engine_hours|round(1) }} hours, 
{{ engine.rpm }} RPM, Load {{ engine.engine_load|round(0) }}%, Temp {{ engine.engine_temperature|round(0) }}°C, 
Oil pressure {{ engine.oil_pressure|round(1) }} bar, Fuel consumption {{ engine.fuel_consumption|round(1) }} L/hr.
{% if engine.alarms %}Alarms: {{ engine.alarms|join(', ') }}.{% endif %}""",
            
            'departure': """{{ timestamp.strftime('%H:%M') }} - Departed {{ port_name }}. All fast, proceeding to sea. 
Pilot dropped {{ pilot_time }}. All systems operational. Crew complete. Safety briefing conducted.""",
            
            'arrival': """{{ timestamp.strftime('%H:%M') }} - Arrived {{ port_name }}. Pilot embarked {{ pilot_time }}. 
All fast alongside berth {{ berth_number }}. Engines stopped {{ engine_stop_time }}. Voyage completed safely.""",
            
            'watch_change': """{{ timestamp.strftime('%H:%M') }} - Watch relief: {{ relieving_officer }} relieved {{ relieved_officer }}. 
Course {{ course }}°T, Speed {{ speed }} knots, Weather {{ weather_summary }}. All in order.""",
            
            'safety_drill': """{{ timestamp.strftime('%H:%M') }} - {{ drill_type|title }} conducted. Personnel: {{ personnel_count }}. 
Equipment tested: {{ equipment_list }}. Duration: {{ duration }} minutes. 
{% if deficiencies %}Deficiencies noted: {{ deficiencies|join(', ') }}.{% else %}No deficiencies.{% endif %}""",
            
            'maintenance': """{{ timestamp.strftime('%H:%M') }} - Maintenance on {{ equipment_name }}: {{ work_description }}. 
{% if parts_used %}Parts used: {{ parts_used|join(', ') }}.{% endif %} 
Work completed by {{ personnel }}. {% if next_service %}Next service: {{ next_service.strftime('%d/%m/%Y') }}.{% endif %}"""
        }
    
    async def start_voyage(self, voyage_log: VoyageLog) -> str:
        """Start a new voyage and initialize logbook"""
        voyage_id = voyage_log.voyage_id
        self.active_voyages[voyage_id] = voyage_log
        self.log_entries[voyage_id] = []
        
        # Store voyage in database
        await self._store_voyage(voyage_log)
        
        # Generate departure entry
        departure_entry = await self._generate_departure_entry(voyage_log)
        await self.add_log_entry(voyage_id, departure_entry)
        
        print(f"Voyage started: {voyage_log.voyage_number} - {voyage_log.vessel_name}")
        print(f"From: {voyage_log.departure_port} to {voyage_log.destination_port}")
        
        return voyage_id
    
    async def update_position(self, voyage_id: str, position: VesselPosition):
        """Update vessel position and generate navigation entries"""
        if voyage_id not in self.active_voyages:
            return
        
        # Store position in history
        await self._store_position(voyage_id, position)
        
        # Check if automatic navigation entry is due
        if await self._should_generate_navigation_entry(voyage_id, position):
            nav_entry = await self._generate_navigation_entry(voyage_id, position)
            await self.add_log_entry(voyage_id, nav_entry)
        
        self.last_position = position
    
    async def update_weather(self, voyage_id: str, weather: WeatherData):
        """Update weather data and generate weather entries"""
        if voyage_id not in self.active_voyages:
            return
        
        # Store weather observation
        await self._store_weather(voyage_id, weather)
        
        # Generate weather entry if conditions changed significantly
        if await self._should_generate_weather_entry(voyage_id, weather):
            weather_entry = await self._generate_weather_entry(voyage_id, weather)
            await self.add_log_entry(voyage_id, weather_entry)
        
        self.last_weather = weather
    
    async def update_engine_data(self, voyage_id: str, engine_data: List[EngineData]):
        """Update engine data and generate engine entries"""
        if voyage_id not in self.active_voyages:
            return
        
        for engine in engine_data:
            # Store engine data
            await self._store_engine_data(voyage_id, engine)
            
            # Check for alarms or significant changes
            if engine.alarms or await self._should_generate_engine_entry(voyage_id, engine):
                engine_entry = await self._generate_engine_entry(voyage_id, engine)
                await self.add_log_entry(voyage_id, engine_entry)
            
            self.last_engine_data[engine.engine_id] = engine
    
    async def add_log_entry(self, voyage_id: str, entry: LogEntry) -> str:
        """Add a log entry to the voyage"""
        if voyage_id not in self.active_voyages:
            raise ValueError(f"Voyage not found: {voyage_id}")
        
        # Add to memory
        self.log_entries[voyage_id].append(entry)
        
        # Store in database
        await self._store_log_entry(voyage_id, entry)
        
        # Check compliance requirements
        await self._check_compliance(voyage_id, entry)
        
        return entry.entry_id
    
    async def add_manual_entry(self, voyage_id: str, entry_type: LogEntryType,
                             summary: str, details: str, watch_officer: str,
                             priority: LogEntryPriority = LogEntryPriority.ROUTINE) -> str:
        """Add a manual log entry"""
        entry_id = str(uuid.uuid4())
        
        entry = LogEntry(
            entry_id=entry_id,
            timestamp=datetime.utcnow(),
            entry_type=entry_type,
            priority=priority,
            watch_officer=watch_officer,
            summary=summary,
            details=details,
            position_data=self.last_position,
            weather_data=self.last_weather,
            engine_data=list(self.last_engine_data.values()),
            crew_data=None,
            safety_data=None,
            maintenance_data=None,
            attachments=[],
            auto_generated=False,
            verified=False,
            compliance_flags=[]
        )
        
        await self.add_log_entry(voyage_id, entry)
        return entry_id
    
    async def add_safety_drill_entry(self, voyage_id: str, safety_entry: SafetyEntry,
                                   watch_officer: str) -> str:
        """Add a safety drill entry"""
        entry_id = str(uuid.uuid4())
        
        # Generate natural language description
        template = Template(self.entry_templates['safety_drill'])
        summary = template.render(
            timestamp=safety_entry.timestamp,
            drill_type=safety_entry.safety_check_type,
            personnel_count=len(safety_entry.personnel_involved),
            equipment_list=', '.join(safety_entry.equipment_tested),
            duration=15,  # Default drill duration
            deficiencies=safety_entry.deficiencies
        )
        
        entry = LogEntry(
            entry_id=entry_id,
            timestamp=safety_entry.timestamp,
            entry_type=LogEntryType.SAFETY,
            priority=LogEntryPriority.IMPORTANT,
            watch_officer=watch_officer,
            summary=summary,
            details=f"Safety drill details: {safety_entry.results}",
            position_data=self.last_position,
            weather_data=self.last_weather,
            engine_data=list(self.last_engine_data.values()),
            crew_data=None,
            safety_data=safety_entry,
            maintenance_data=None,
            attachments=[],
            auto_generated=True,
            verified=False,
            compliance_flags=['SOLAS']
        )
        
        await self.add_log_entry(voyage_id, entry)
        return entry_id
    
    async def add_maintenance_entry(self, voyage_id: str, maintenance_entry: MaintenanceEntry,
                                  watch_officer: str) -> str:
        """Add a maintenance entry"""
        entry_id = str(uuid.uuid4())
        
        # Generate natural language description
        template = Template(self.entry_templates['maintenance'])
        summary = template.render(
            timestamp=maintenance_entry.timestamp,
            equipment_name=maintenance_entry.equipment_name,
            work_description=maintenance_entry.work_performed,
            parts_used=maintenance_entry.parts_used,
            personnel=maintenance_entry.personnel,
            next_service=maintenance_entry.next_service_date
        )
        
        entry = LogEntry(
            entry_id=entry_id,
            timestamp=maintenance_entry.timestamp,
            entry_type=LogEntryType.MAINTENANCE,
            priority=LogEntryPriority.ROUTINE,
            watch_officer=watch_officer,
            summary=summary,
            details=f"Maintenance work: {maintenance_entry.work_performed}",
            position_data=self.last_position,
            weather_data=self.last_weather,
            engine_data=list(self.last_engine_data.values()),
            crew_data=None,
            safety_data=None,
            maintenance_data=maintenance_entry,
            attachments=[],
            auto_generated=True,
            verified=False,
            compliance_flags=[]
        )
        
        await self.add_log_entry(voyage_id, entry)
        return entry_id
    
    async def generate_watch_change_entry(self, voyage_id: str, relieving_officer: str,
                                        relieved_officer: str) -> str:
        """Generate watch change entry"""
        entry_id = str(uuid.uuid4())
        
        template = Template(self.entry_templates['watch_change'])
        summary = template.render(
            timestamp=datetime.utcnow(),
            relieving_officer=relieving_officer,
            relieved_officer=relieved_officer,
            course=self.last_position.course_over_ground if self.last_position else 0,
            speed=self.last_position.speed_over_ground if self.last_position else 0,
            weather_summary=f"{self.last_weather.weather_observation.value}" if self.last_weather else "Unknown"
        )
        
        entry = LogEntry(
            entry_id=entry_id,
            timestamp=datetime.utcnow(),
            entry_type=LogEntryType.CREW,
            priority=LogEntryPriority.ROUTINE,
            watch_officer=relieving_officer,
            summary=summary,
            details="Watch change conducted. All systems reviewed and operational.",
            position_data=self.last_position,
            weather_data=self.last_weather,
            engine_data=list(self.last_engine_data.values()),
            crew_data=None,
            safety_data=None,
            maintenance_data=None,
            attachments=[],
            auto_generated=True,
            verified=False,
            compliance_flags=['STCW']
        )
        
        await self.add_log_entry(voyage_id, entry)
        return entry_id
    
    async def complete_voyage(self, voyage_id: str, arrival_port: str) -> Dict[str, Any]:
        """Complete voyage and generate summary report"""
        if voyage_id not in self.active_voyages:
            raise ValueError(f"Voyage not found: {voyage_id}")
        
        voyage = self.active_voyages[voyage_id]
        voyage.actual_arrival = datetime.utcnow()
        
        # Generate arrival entry
        arrival_entry = await self._generate_arrival_entry(voyage_id, arrival_port)
        await self.add_log_entry(voyage_id, arrival_entry)
        
        # Calculate voyage statistics
        voyage_stats = await self._calculate_voyage_statistics(voyage_id)
        
        # Update voyage record
        voyage.total_distance = voyage_stats['total_distance']
        voyage.fuel_consumed = voyage_stats['fuel_consumed']
        voyage.avg_speed = voyage_stats['avg_speed']
        voyage.max_speed = voyage_stats['max_speed']
        
        # Generate compliance report
        compliance_report = await self._generate_compliance_report(voyage_id)
        voyage.compliance_status = compliance_report
        
        # Update database
        await self._update_voyage(voyage)
        
        # Generate voyage summary report
        summary_report = await self._generate_voyage_summary(voyage_id)
        
        print(f"Voyage completed: {voyage.voyage_number}")
        print(f"Total entries: {len(self.log_entries[voyage_id])}")
        print(f"Distance: {voyage.total_distance:.1f} nm")
        print(f"Average speed: {voyage.avg_speed:.1f} knots")
        
        return summary_report
    
    async def _generate_departure_entry(self, voyage_log: VoyageLog) -> LogEntry:
        """Generate departure log entry"""
        entry_id = str(uuid.uuid4())
        
        template = Template(self.entry_templates['departure'])
        summary = template.render(
            timestamp=voyage_log.departure_date,
            port_name=voyage_log.departure_port,
            pilot_time=voyage_log.departure_date.strftime('%H:%M'),
            engine_start_time=voyage_log.departure_date.strftime('%H:%M')
        )
        
        return LogEntry(
            entry_id=entry_id,
            timestamp=voyage_log.departure_date,
            entry_type=LogEntryType.DEPARTURE,
            priority=LogEntryPriority.IMPORTANT,
            watch_officer=voyage_log.chief_officer,
            summary=summary,
            details=f"Departed {voyage_log.departure_port} bound for {voyage_log.destination_port}",
            position_data=None,
            weather_data=None,
            engine_data=None,
            crew_data=None,
            safety_data=None,
            maintenance_data=None,
            attachments=[],
            auto_generated=True,
            verified=False,
            compliance_flags=['SOLAS', 'STCW']
        )
    
    async def _generate_navigation_entry(self, voyage_id: str, position: VesselPosition) -> LogEntry:
        """Generate navigation log entry"""
        entry_id = str(uuid.uuid4())
        
        template = Template(self.entry_templates['navigation'])
        summary = template.render(
            timestamp=position.timestamp,
            position=position
        )
        
        return LogEntry(
            entry_id=entry_id,
            timestamp=position.timestamp,
            entry_type=LogEntryType.NAVIGATION,
            priority=LogEntryPriority.ROUTINE,
            watch_officer="Auto",
            summary=summary,
            details="Automatic navigation entry based on GPS position",
            position_data=position,
            weather_data=self.last_weather,
            engine_data=list(self.last_engine_data.values()),
            crew_data=None,
            safety_data=None,
            maintenance_data=None,
            attachments=[],
            auto_generated=True,
            verified=False,
            compliance_flags=['SOLAS']
        )
    
    async def _generate_weather_entry(self, voyage_id: str, weather: WeatherData) -> LogEntry:
        """Generate weather observation entry"""
        entry_id = str(uuid.uuid4())
        
        template = Template(self.entry_templates['weather'])
        summary = template.render(
            timestamp=weather.timestamp,
            weather=weather
        )
        
        return LogEntry(
            entry_id=entry_id,
            timestamp=weather.timestamp,
            entry_type=LogEntryType.WEATHER,
            priority=LogEntryPriority.ROUTINE,
            watch_officer="Auto",
            summary=summary,
            details="Automatic weather observation entry",
            position_data=self.last_position,
            weather_data=weather,
            engine_data=list(self.last_engine_data.values()),
            crew_data=None,
            safety_data=None,
            maintenance_data=None,
            attachments=[],
            auto_generated=True,
            verified=False,
            compliance_flags=[]
        )
    
    async def _generate_engine_entry(self, voyage_id: str, engine: EngineData) -> LogEntry:
        """Generate engine log entry"""
        entry_id = str(uuid.uuid4())
        
        template = Template(self.entry_templates['engine'])
        summary = template.render(
            timestamp=engine.timestamp,
            engine=engine
        )
        
        priority = LogEntryPriority.CRITICAL if engine.alarms else LogEntryPriority.ROUTINE
        
        return LogEntry(
            entry_id=entry_id,
            timestamp=engine.timestamp,
            entry_type=LogEntryType.ENGINE,
            priority=priority,
            watch_officer="Auto",
            summary=summary,
            details="Automatic engine monitoring entry",
            position_data=self.last_position,
            weather_data=self.last_weather,
            engine_data=[engine],
            crew_data=None,
            safety_data=None,
            maintenance_data=None,
            attachments=[],
            auto_generated=True,
            verified=False,
            compliance_flags=['MARPOL'] if engine.alarms else []
        )
    
    async def _generate_arrival_entry(self, voyage_id: str, port_name: str) -> LogEntry:
        """Generate arrival log entry"""
        entry_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        template = Template(self.entry_templates['arrival'])
        summary = template.render(
            timestamp=now,
            port_name=port_name,
            pilot_time=now.strftime('%H:%M'),
            berth_number="TBD",
            engine_stop_time=now.strftime('%H:%M')
        )
        
        return LogEntry(
            entry_id=entry_id,
            timestamp=now,
            entry_type=LogEntryType.ARRIVAL,
            priority=LogEntryPriority.IMPORTANT,
            watch_officer="Master",
            summary=summary,
            details=f"Arrived {port_name}. Voyage completed successfully.",
            position_data=self.last_position,
            weather_data=self.last_weather,
            engine_data=list(self.last_engine_data.values()),
            crew_data=None,
            safety_data=None,
            maintenance_data=None,
            attachments=[],
            auto_generated=True,
            verified=False,
            compliance_flags=['SOLAS', 'STCW']
        )
    
    async def _should_generate_navigation_entry(self, voyage_id: str, position: VesselPosition) -> bool:
        """Determine if navigation entry should be generated"""
        if not self.auto_logging_enabled:
            return False
        
        # Get last navigation entry
        entries = self.log_entries.get(voyage_id, [])
        nav_entries = [e for e in entries if e.entry_type == LogEntryType.NAVIGATION]
        
        if not nav_entries:
            return True
        
        last_nav_entry = nav_entries[-1]
        time_diff = (position.timestamp - last_nav_entry.timestamp).total_seconds()
        
        # Generate entry if interval has passed or significant position change
        if time_diff >= self.entry_interval:
            return True
        
        if self.last_position:
            distance_moved = self._calculate_distance(
                self.last_position.latitude, self.last_position.longitude,
                position.latitude, position.longitude
            )
            if distance_moved > 10:  # 10 nm threshold
                return True
        
        return False
    
    async def _should_generate_weather_entry(self, voyage_id: str, weather: WeatherData) -> bool:
        """Determine if weather entry should be generated"""
        if not self.last_weather:
            return True
        
        # Check for significant weather changes
        wind_change = abs(weather.wind_speed - self.last_weather.wind_speed)
        pressure_change = abs(weather.barometric_pressure - self.last_weather.barometric_pressure)
        visibility_change = abs(weather.visibility - self.last_weather.visibility)
        
        if wind_change > 10 or pressure_change > 5 or visibility_change > 3:
            return True
        
        if weather.weather_observation != self.last_weather.weather_observation:
            return True
        
        return False
    
    async def _should_generate_engine_entry(self, voyage_id: str, engine: EngineData) -> bool:
        """Determine if engine entry should be generated"""
        if engine.alarms:
            return True
        
        if engine.engine_id not in self.last_engine_data:
            return True
        
        last_engine = self.last_engine_data[engine.engine_id]
        
        # Check for significant parameter changes
        temp_change = abs(engine.engine_temperature - last_engine.engine_temperature)
        load_change = abs(engine.engine_load - last_engine.engine_load)
        pressure_change = abs(engine.oil_pressure - last_engine.oil_pressure)
        
        if temp_change > 10 or load_change > 20 or pressure_change > 0.5:
            return True
        
        if engine.status != last_engine.status:
            return True
        
        return False
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in nautical miles"""
        # Haversine formula
        R = 3440.065  # Earth's radius in nautical miles
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    async def _calculate_voyage_statistics(self, voyage_id: str) -> Dict[str, float]:
        """Calculate voyage statistics"""
        # Get position history
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM position_history WHERE voyage_id = ? ORDER BY timestamp
        """, (voyage_id,))
        positions = cursor.fetchall()
        
        # Calculate total distance
        total_distance = sum(pos[8] for pos in positions if pos[8])  # distance_run column
        
        # Calculate average and max speed
        speeds = [pos[5] for pos in positions if pos[5]]  # speed_over_ground column
        avg_speed = np.mean(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0
        
        # Get fuel consumption data
        cursor.execute("""
            SELECT SUM(fuel_consumption) FROM engine_logs WHERE voyage_id = ?
        """, (voyage_id,))
        fuel_result = cursor.fetchone()
        fuel_consumed = fuel_result[0] if fuel_result[0] else 0
        
        conn.close()
        
        return {
            'total_distance': total_distance,
            'avg_speed': avg_speed,
            'max_speed': max_speed,
            'fuel_consumed': fuel_consumed
        }
    
    async def _check_compliance(self, voyage_id: str, entry: LogEntry):
        """Check regulatory compliance for log entry"""
        compliance_flags = []
        
        # SOLAS compliance checks
        if entry.entry_type in [LogEntryType.SAFETY, LogEntryType.NAVIGATION, LogEntryType.DEPARTURE, LogEntryType.ARRIVAL]:
            compliance_flags.append('SOLAS')
        
        # STCW compliance checks (watch keeping)
        if entry.entry_type == LogEntryType.CREW or "watch" in entry.summary.lower():
            compliance_flags.append('STCW')
        
        # MARPOL compliance checks
        if entry.entry_type in [LogEntryType.FUEL, LogEntryType.ENGINE] or entry.engine_data:
            compliance_flags.append('MARPOL')
        
        entry.compliance_flags.extend(compliance_flags)
    
    async def _generate_compliance_report(self, voyage_id: str) -> Dict[str, bool]:
        """Generate compliance status report"""
        entries = self.log_entries.get(voyage_id, [])
        
        compliance_status = {}
        
        for regulation in self.compliance_templates:
            required_entries = self.compliance_templates[regulation]
            compliance_met = True
            
            for requirement in required_entries:
                # Check if requirement is covered in log entries
                requirement_met = any(
                    requirement in entry.summary.lower() or 
                    requirement in [flag.lower() for flag in entry.compliance_flags]
                    for entry in entries
                )
                if not requirement_met:
                    compliance_met = False
                    break
            
            compliance_status[regulation] = compliance_met
        
        return compliance_status
    
    async def _generate_voyage_summary(self, voyage_id: str) -> Dict[str, Any]:
        """Generate comprehensive voyage summary report"""
        voyage = self.active_voyages[voyage_id]
        entries = self.log_entries.get(voyage_id, [])
        
        # Entry statistics
        entry_stats = {}
        for entry_type in LogEntryType:
            count = len([e for e in entries if e.entry_type == entry_type])
            entry_stats[entry_type.value] = count
        
        # Priority distribution
        priority_stats = {}
        for priority in LogEntryPriority:
            count = len([e for e in entries if e.priority == priority])
            priority_stats[priority.value] = count
        
        # Auto-generated vs manual entries
        auto_generated_count = len([e for e in entries if e.auto_generated])
        manual_count = len(entries) - auto_generated_count
        
        summary = {
            'voyage_info': {
                'voyage_id': voyage_id,
                'vessel_name': voyage.vessel_name,
                'voyage_number': voyage.voyage_number,
                'departure_port': voyage.departure_port,
                'arrival_port': voyage.destination_port,
                'departure_date': voyage.departure_date.isoformat(),
                'arrival_date': voyage.actual_arrival.isoformat() if voyage.actual_arrival else None,
                'duration_hours': (voyage.actual_arrival - voyage.departure_date).total_seconds() / 3600 if voyage.actual_arrival else None
            },
            'statistics': {
                'total_entries': len(entries),
                'auto_generated_entries': auto_generated_count,
                'manual_entries': manual_count,
                'total_distance': voyage.total_distance,
                'average_speed': voyage.avg_speed,
                'max_speed': voyage.max_speed,
                'fuel_consumed': voyage.fuel_consumed
            },
            'entry_distribution': entry_stats,
            'priority_distribution': priority_stats,
            'compliance_status': voyage.compliance_status
        }
        
        return summary
    
    async def export_logbook(self, voyage_id: str, format: str = "html") -> str:
        """Export logbook in specified format"""
        if voyage_id not in self.active_voyages:
            raise ValueError(f"Voyage not found: {voyage_id}")
        
        voyage = self.active_voyages[voyage_id]
        entries = self.log_entries.get(voyage_id, [])
        
        if format == "html":
            return await self._export_html_logbook(voyage, entries)
        elif format == "pdf":
            return await self._export_pdf_logbook(voyage, entries)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def _export_html_logbook(self, voyage: VoyageLog, entries: List[LogEntry]) -> str:
        """Export logbook as HTML"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ voyage.vessel_name }} - Voyage {{ voyage.voyage_number }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
                .entry { margin-bottom: 15px; padding: 10px; border-left: 3px solid #007acc; }
                .entry-header { font-weight: bold; color: #007acc; }
                .entry-details { margin-top: 5px; color: #666; }
                .priority-critical { border-left-color: #ff4444; }
                .priority-important { border-left-color: #ff8800; }
                .auto-generated { background-color: #f9f9f9; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{{ voyage.vessel_name }} - Voyage {{ voyage.voyage_number }}</h1>
                <p><strong>From:</strong> {{ voyage.departure_port }} <strong>To:</strong> {{ voyage.destination_port }}</p>
                <p><strong>Departure:</strong> {{ voyage.departure_date.strftime('%d/%m/%Y %H:%M') }}</p>
                {% if voyage.actual_arrival %}
                <p><strong>Arrival:</strong> {{ voyage.actual_arrival.strftime('%d/%m/%Y %H:%M') }}</p>
                {% endif %}
                <p><strong>Master:</strong> {{ voyage.master_name }}</p>
            </div>
            
            {% for entry in entries %}
            <div class="entry {% if entry.auto_generated %}auto-generated{% endif %} priority-{{ entry.priority.value }}">
                <div class="entry-header">
                    {{ entry.timestamp.strftime('%d/%m/%Y %H:%M') }} - {{ entry.entry_type.value.title() }}
                    {% if entry.priority != 'routine' %}({{ entry.priority.value.title() }}){% endif %}
                </div>
                <div>{{ entry.summary }}</div>
                {% if entry.details != entry.summary %}
                <div class="entry-details">{{ entry.details }}</div>
                {% endif %}
                <div class="entry-details">
                    Officer: {{ entry.watch_officer }}
                    {% if entry.auto_generated %}| Auto-generated{% endif %}
                    {% if entry.compliance_flags %}| Compliance: {{ entry.compliance_flags|join(', ') }}{% endif %}
                </div>
            </div>
            {% endfor %}
        </body>
        </html>
        """
        
        template = Template(html_template)
        return template.render(voyage=voyage, entries=entries)
    
    async def _store_voyage(self, voyage: VoyageLog):
        """Store voyage in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO voyages 
            (voyage_id, vessel_name, vessel_imo, voyage_number, departure_port,
             departure_date, destination_port, estimated_arrival, actual_arrival,
             master_name, chief_officer, total_distance, fuel_consumed,
             avg_speed, max_speed, compliance_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            voyage.voyage_id, voyage.vessel_name, voyage.vessel_imo,
            voyage.voyage_number, voyage.departure_port, voyage.departure_date,
            voyage.destination_port, voyage.estimated_arrival, voyage.actual_arrival,
            voyage.master_name, voyage.chief_officer, voyage.total_distance,
            voyage.fuel_consumed, voyage.avg_speed, voyage.max_speed,
            json.dumps(voyage.compliance_status)
        ))
        
        conn.commit()
        conn.close()
    
    async def _update_voyage(self, voyage: VoyageLog):
        """Update voyage in database"""
        await self._store_voyage(voyage)  # Same as store with REPLACE
    
    async def _store_log_entry(self, voyage_id: str, entry: LogEntry):
        """Store log entry in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO log_entries 
            (entry_id, voyage_id, timestamp, entry_type, priority, watch_officer,
             summary, details, position_data, weather_data, engine_data,
             crew_data, safety_data, maintenance_data, attachments,
             auto_generated, verified, compliance_flags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.entry_id, voyage_id, entry.timestamp, entry.entry_type.value,
            entry.priority.value, entry.watch_officer, entry.summary, entry.details,
            json.dumps(asdict(entry.position_data)) if entry.position_data else None,
            json.dumps(asdict(entry.weather_data)) if entry.weather_data else None,
            json.dumps([asdict(e) for e in entry.engine_data]) if entry.engine_data else None,
            json.dumps(asdict(entry.crew_data)) if entry.crew_data else None,
            json.dumps(asdict(entry.safety_data)) if entry.safety_data else None,
            json.dumps(asdict(entry.maintenance_data)) if entry.maintenance_data else None,
            json.dumps(entry.attachments), entry.auto_generated, entry.verified,
            json.dumps(entry.compliance_flags)
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_position(self, voyage_id: str, position: VesselPosition):
        """Store position in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO position_history 
            (voyage_id, timestamp, latitude, longitude, course_over_ground,
             speed_over_ground, heading, distance_run, position_source, position_accuracy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            voyage_id, position.timestamp, position.latitude, position.longitude,
            position.course_over_ground, position.speed_over_ground, position.heading,
            position.distance_run, position.position_source, position.position_accuracy
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_weather(self, voyage_id: str, weather: WeatherData):
        """Store weather observation in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO weather_observations 
            (voyage_id, timestamp, wind_direction, wind_speed, wind_force,
             barometric_pressure, air_temperature, sea_temperature, visibility,
             cloud_cover, weather_observation, sea_condition, wave_height,
             wave_period, swell_direction, swell_height)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            voyage_id, weather.timestamp, weather.wind_direction, weather.wind_speed,
            weather.wind_force, weather.barometric_pressure, weather.air_temperature,
            weather.sea_temperature, weather.visibility, weather.cloud_cover,
            weather.weather_observation.value, weather.sea_condition.value,
            weather.wave_height, weather.wave_period, weather.swell_direction,
            weather.swell_height
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_engine_data(self, voyage_id: str, engine: EngineData):
        """Store engine data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO engine_logs 
            (voyage_id, timestamp, engine_id, engine_hours, rpm, engine_temperature,
             oil_pressure, fuel_consumption, engine_load, coolant_temperature,
             exhaust_temperature, status, alarms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            voyage_id, engine.timestamp, engine.engine_id, engine.engine_hours,
            engine.rpm, engine.engine_temperature, engine.oil_pressure,
            engine.fuel_consumption, engine.engine_load, engine.coolant_temperature,
            engine.exhaust_temperature, engine.status, json.dumps(engine.alarms)
        ))
        
        conn.commit()
        conn.close()


async def main():
    """Demonstration of automatic logbook system"""
    
    # Initialize automatic logbook system
    logbook = AutomaticLogbookSystem("logbook.db")
    
    print("ActiveLog Marine Advanced - Automatic Logbook Demo")
    print("=" * 54)
    
    # Create sample voyage
    voyage = VoyageLog(
        voyage_id="VOY_2024_001",
        vessel_name="MV PACIFIC EXPLORER",
        vessel_imo="IMO1234567",
        voyage_number="PE-2024-15",
        departure_port="Los Angeles",
        departure_date=datetime.utcnow() - timedelta(days=3),
        destination_port="Honolulu",
        estimated_arrival=datetime.utcnow() + timedelta(hours=6),
        actual_arrival=None,
        master_name="Captain James Morrison",
        chief_officer="Chief Officer Sarah Chen",
        entries=[],
        total_distance=0.0,
        fuel_consumed=0.0,
        avg_speed=0.0,
        max_speed=0.0,
        compliance_status={}
    )
    
    # Start voyage
    voyage_id = await logbook.start_voyage(voyage)
    
    print(f"\nVoyage started: {voyage.voyage_number}")
    print(f"Vessel: {voyage.vessel_name}")
    print(f"Route: {voyage.departure_port} → {voyage.destination_port}")
    
    print("\n" + "="*50)
    print("SIMULATING VOYAGE PROGRESS")
    print("="*50)
    
    # Simulate voyage data over 3 days
    start_time = voyage.departure_date
    
    for hour in range(0, 72, 6):  # Every 6 hours for 3 days
        current_time = start_time + timedelta(hours=hour)
        
        print(f"\n--- Hour {hour}: {current_time.strftime('%d/%m/%Y %H:%M')} ---")
        
        # Simulate position update
        # Moving from LA (34.05°N, 118.24°W) towards Honolulu (21.31°N, 157.86°W)
        progress = hour / 72.0  # 0 to 1
        lat = 34.05 + (21.31 - 34.05) * progress
        lon = -118.24 + (-157.86 - (-118.24)) * progress
        
        position = VesselPosition(
            timestamp=current_time,
            latitude=lat,
            longitude=lon,
            course_over_ground=240 + np.random.uniform(-10, 10),
            speed_over_ground=14 + np.random.uniform(-2, 2),
            heading=240 + np.random.uniform(-5, 5),
            distance_run=14 * 6,  # 6-hour interval
            position_source="GPS",
            position_accuracy=3.0
        )
        
        await logbook.update_position(voyage_id, position)
        
        # Simulate weather update
        weather = WeatherData(
            timestamp=current_time,
            wind_direction=220 + np.random.uniform(-30, 30),
            wind_speed=15 + np.random.uniform(-8, 8),
            wind_force=int(min(12, max(0, (15 + np.random.uniform(-8, 8)) / 3))),
            barometric_pressure=1015 + np.random.uniform(-10, 10),
            air_temperature=24 + np.random.uniform(-5, 5),
            sea_temperature=22 + np.random.uniform(-3, 3),
            visibility=10 + np.random.uniform(-5, 5),
            cloud_cover=int(np.random.uniform(0, 8)),
            weather_observation=WeatherObservation.CLEAR if np.random.random() > 0.3 else WeatherObservation.PARTLY_CLOUDY,
            sea_condition=SeaCondition.MODERATE,
            wave_height=2 + np.random.uniform(-1, 1),
            wave_period=6 + np.random.uniform(-2, 2),
            swell_direction=210.0,
            swell_height=1.5
        )
        
        await logbook.update_weather(voyage_id, weather)
        
        # Simulate engine data
        engine_data = [EngineData(
            timestamp=current_time,
            engine_id="MAIN_001",
            engine_hours=2500 + hour,
            rpm=1800 + int(np.random.uniform(-100, 100)),
            engine_temperature=85 + np.random.uniform(-5, 10),
            oil_pressure=4.2 + np.random.uniform(-0.5, 0.3),
            fuel_consumption=45 + np.random.uniform(-5, 5),
            engine_load=75 + np.random.uniform(-15, 15),
            coolant_temperature=78 + np.random.uniform(-5, 8),
            exhaust_temperature=420 + np.random.uniform(-20, 30),
            status="running",
            alarms=["high_temp"] if np.random.random() < 0.05 else []
        )]
        
        await logbook.update_engine_data(voyage_id, engine_data)
        
        # Add some special events
        if hour == 24:  # After 1 day
            await logbook.generate_watch_change_entry(
                voyage_id, "Second Officer Mike Roberts", "Chief Officer Sarah Chen"
            )
            
        if hour == 36:  # After 1.5 days
            safety_drill = SafetyEntry(
                timestamp=current_time,
                safety_check_type="fire_drill",
                personnel_involved=["crew_001", "crew_002", "crew_003", "crew_004"],
                equipment_tested=["fire_hoses", "fire_pumps", "breathing_apparatus"],
                results="Drill completed successfully. All equipment operational.",
                deficiencies=[],
                corrective_actions=[]
            )
            await logbook.add_safety_drill_entry(voyage_id, safety_drill, "Chief Officer Sarah Chen")
            
        if hour == 48:  # After 2 days
            maintenance = MaintenanceEntry(
                timestamp=current_time,
                equipment_id="PUMP_002",
                equipment_name="Fresh Water Pump #2",
                maintenance_type="routine",
                work_performed="Replaced impeller and checked seals",
                parts_used=["impeller_kit_A24", "seal_set_B12"],
                personnel="Engineer Tom Wilson",
                next_service_date=current_time + timedelta(days=90),
                status="completed"
            )
            await logbook.add_maintenance_entry(voyage_id, maintenance, "Chief Engineer")
        
        # Add manual entry occasionally
        if hour % 18 == 0 and hour > 0:  # Every 18 hours
            await logbook.add_manual_entry(
                voyage_id,
                LogEntryType.NAVIGATION,
                f"Waypoint passed - {hour//18}",
                f"Passed planned waypoint #{hour//18}. Course and speed maintained. ETA unchanged.",
                "Officer on Watch",
                LogEntryPriority.ROUTINE
            )
        
        print(f"Position: {lat:.2f}°N, {lon:.2f}°W")
        print(f"Course: {position.course_over_ground:.0f}°, Speed: {position.speed_over_ground:.1f} kts")
        print(f"Weather: {weather.weather_observation.value}, Wind: {weather.wind_speed:.0f} kts")
        print(f"Engine: {engine_data[0].rpm} RPM, {engine_data[0].engine_load:.0f}% load")
    
    print(f"\n" + "="*50)
    print("VOYAGE COMPLETION")
    print("="*50)
    
    # Complete voyage
    summary_report = await logbook.complete_voyage(voyage_id, "Honolulu")
    
    print(f"\nVoyage Summary:")
    print(f"Duration: {summary_report['voyage_info']['duration_hours']:.1f} hours")
    print(f"Total Entries: {summary_report['statistics']['total_entries']}")
    print(f"Auto-generated: {summary_report['statistics']['auto_generated_entries']}")
    print(f"Manual Entries: {summary_report['statistics']['manual_entries']}")
    print(f"Distance: {summary_report['statistics']['total_distance']:.0f} nm")
    print(f"Average Speed: {summary_report['statistics']['average_speed']:.1f} kts")
    print(f"Fuel Consumed: {summary_report['statistics']['fuel_consumed']:.0f} L")
    
    print(f"\nEntry Distribution:")
    for entry_type, count in summary_report['entry_distribution'].items():
        if count > 0:
            print(f"  {entry_type.title()}: {count}")
    
    print(f"\nCompliance Status:")
    for regulation, status in summary_report['compliance_status'].items():
        status_symbol = "✅" if status else "❌"
        print(f"  {regulation}: {status_symbol}")
    
    # Export logbook
    print(f"\n" + "="*50)
    print("LOGBOOK EXPORT")
    print("="*50)
    
    html_export = await logbook.export_logbook(voyage_id, "html")
    
    # Save to file
    export_file = f"logbook_{voyage.voyage_number}_{datetime.now().strftime('%Y%m%d')}.html"
    with open(export_file, 'w', encoding='utf-8') as f:
        f.write(html_export)
    
    print(f"Logbook exported to: {export_file}")
    print(f"Export size: {len(html_export)} characters")
    
    # Show sample log entries
    print(f"\nSample Log Entries:")
    entries = logbook.log_entries[voyage_id]
    for i, entry in enumerate(entries[-5:], 1):  # Show last 5 entries
        priority_symbol = "🔴" if entry.priority == LogEntryPriority.CRITICAL else "🟡" if entry.priority == LogEntryPriority.IMPORTANT else "🔵"
        auto_symbol = "🤖" if entry.auto_generated else "✋"
        print(f"  {i}. {priority_symbol} {auto_symbol} [{entry.timestamp.strftime('%d/%m %H:%M')}] {entry.entry_type.value.title()}")
        print(f"     {entry.summary[:80]}{'...' if len(entry.summary) > 80 else ''}")
        if entry.compliance_flags:
            print(f"     Compliance: {', '.join(entry.compliance_flags)}")
    
    print("\n📚 Automatic logbook generation demo completed successfully!")
    print("Logbook entries automatically generated with regulatory compliance tracking.")


if __name__ == "__main__":
    asyncio.run(main())