#!/usr/bin/env python3
"""
ActiveLog.ai Distributed Manufacturing Coordination System

Multi-site production orchestration with real-time capacity planning and supply chain integration.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import uuid
import sqlite3
import requests
import websockets
from concurrent.futures import ThreadPoolExecutor

class FacilityType(Enum):
    MANUFACTURING = "manufacturing"
    ASSEMBLY = "assembly"
    TESTING = "testing"
    PACKAGING = "packaging"
    DISTRIBUTION = "distribution"
    RESEARCH = "research"

class ProductionStatus(Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"

class ResourceType(Enum):
    MACHINE = "machine"
    OPERATOR = "operator"
    TOOL = "tool"
    MATERIAL = "material"
    SPACE = "space"

class Priority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5

@dataclass
class Facility:
    """Manufacturing facility information"""
    facility_id: str
    name: str
    location: str
    facility_type: FacilityType
    capabilities: List[str]
    capacity: Dict[str, float]  # Resource type -> capacity
    current_utilization: Dict[str, float]  # Resource type -> current usage
    operating_hours: Dict[str, str]  # day -> "start-end"
    timezone: str
    contact_info: Dict[str, str]
    certifications: List[str] = None
    equipment: List[str] = None
    specializations: List[str] = None
    
    def __post_init__(self):
        if self.certifications is None:
            self.certifications = []
        if self.equipment is None:
            self.equipment = []
        if self.specializations is None:
            self.specializations = []

@dataclass
class ProductionJob:
    """Production job definition"""
    job_id: str
    product_id: str
    quantity: int
    priority: Priority
    requirements: Dict[str, Any]  # Resource requirements
    estimated_duration: float  # Hours
    deadline: Optional[str] = None
    dependencies: List[str] = None  # Other job IDs
    assigned_facility: Optional[str] = None
    status: ProductionStatus = ProductionStatus.PLANNED
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0
    notes: str = ""
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

@dataclass
class Resource:
    """Manufacturing resource"""
    resource_id: str
    resource_type: ResourceType
    name: str
    facility_id: str
    capacity: float
    current_allocation: float = 0.0
    availability_schedule: Dict[str, List[str]] = None  # date -> [time_slots]
    maintenance_schedule: List[str] = None  # maintenance dates
    specifications: Dict[str, Any] = None
    cost_per_hour: float = 0.0
    
    def __post_init__(self):
        if self.availability_schedule is None:
            self.availability_schedule = {}
        if self.maintenance_schedule is None:
            self.maintenance_schedule = []
        if self.specifications is None:
            self.specifications = {}

@dataclass
class ProductionSchedule:
    """Production schedule for a facility"""
    facility_id: str
    date: str
    scheduled_jobs: List[Dict[str, Any]]  # job_id, start_time, end_time, resources
    resource_utilization: Dict[str, float]
    total_capacity_used: float
    
    def __post_init__(self):
        if self.scheduled_jobs is None:
            self.scheduled_jobs = []

@dataclass
class SupplyChainEvent:
    """Supply chain event notification"""
    event_id: str
    event_type: str  # "material_shortage", "supplier_delay", etc.
    severity: str  # "low", "medium", "high", "critical"
    affected_jobs: List[str]
    description: str
    timestamp: str
    expected_resolution: Optional[str] = None
    mitigation_actions: List[str] = None
    
    def __post_init__(self):
        if self.mitigation_actions is None:
            self.mitigation_actions = []

class ManufacturingDatabase:
    """Database for manufacturing coordination"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Facilities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS facilities (
                facility_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                facility_type TEXT NOT NULL,
                capabilities TEXT,
                capacity TEXT,
                current_utilization TEXT,
                operating_hours TEXT,
                timezone TEXT,
                contact_info TEXT,
                certifications TEXT,
                equipment TEXT,
                specializations TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Production jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS production_jobs (
                job_id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                priority INTEGER NOT NULL,
                requirements TEXT,
                estimated_duration REAL NOT NULL,
                deadline TEXT,
                dependencies TEXT,
                assigned_facility TEXT,
                status TEXT DEFAULT 'planned',
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                progress REAL DEFAULT 0.0,
                notes TEXT,
                FOREIGN KEY (assigned_facility) REFERENCES facilities (facility_id)
            )
        ''')
        
        # Resources table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                resource_id TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                name TEXT NOT NULL,
                facility_id TEXT NOT NULL,
                capacity REAL NOT NULL,
                current_allocation REAL DEFAULT 0.0,
                availability_schedule TEXT,
                maintenance_schedule TEXT,
                specifications TEXT,
                cost_per_hour REAL DEFAULT 0.0,
                FOREIGN KEY (facility_id) REFERENCES facilities (facility_id)
            )
        ''')
        
        # Production schedules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS production_schedules (
                schedule_id TEXT PRIMARY KEY,
                facility_id TEXT NOT NULL,
                date TEXT NOT NULL,
                scheduled_jobs TEXT,
                resource_utilization TEXT,
                total_capacity_used REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (facility_id) REFERENCES facilities (facility_id),
                UNIQUE(facility_id, date)
            )
        ''')
        
        # Supply chain events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS supply_chain_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                affected_jobs TEXT,
                description TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                expected_resolution TEXT,
                mitigation_actions TEXT,
                resolved_at TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON production_jobs(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_facility ON production_jobs(assigned_facility)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_resources_facility ON resources(facility_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedules_date ON production_schedules(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON supply_chain_events(timestamp)')
        
        conn.commit()
        conn.close()

class CapacityPlanner:
    """Real-time capacity planning and resource allocation"""
    
    def __init__(self, database: ManufacturingDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
    
    def calculate_capacity_utilization(self, facility_id: str, date: str) -> Dict[str, float]:
        """Calculate capacity utilization for a facility on a specific date"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        # Get facility resources
        cursor.execute('SELECT resource_type, capacity, current_allocation FROM resources WHERE facility_id = ?',
                      (facility_id,))
        resources = cursor.fetchall()
        
        # Get scheduled jobs for the date
        cursor.execute('SELECT scheduled_jobs FROM production_schedules WHERE facility_id = ? AND date = ?',
                      (facility_id, date))
        schedule_result = cursor.fetchone()
        
        conn.close()
        
        # Calculate utilization by resource type
        utilization = {}
        for resource_type, capacity, current_allocation in resources:
            utilization[resource_type] = (current_allocation / capacity) * 100 if capacity > 0 else 0
        
        # Factor in scheduled jobs
        if schedule_result:
            scheduled_jobs = json.loads(schedule_result[0])
            for job in scheduled_jobs:
                if 'resources' in job:
                    for resource_type, required in job['resources'].items():
                        if resource_type in utilization:
                            # Add scheduled resource usage
                            total_capacity = sum(cap for rt, cap, _ in resources if rt == resource_type)
                            if total_capacity > 0:
                                utilization[resource_type] += (required / total_capacity) * 100
        
        return utilization
    
    def find_available_capacity(self, requirements: Dict[str, float], 
                               date: str, duration: float) -> List[Tuple[str, float]]:
        """Find facilities with available capacity for requirements"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        # Get all facilities
        cursor.execute('SELECT facility_id, name, capabilities FROM facilities')
        facilities = cursor.fetchall()
        
        available_facilities = []
        
        for facility_id, name, capabilities_json in facilities:
            capabilities = json.loads(capabilities_json) if capabilities_json else []
            
            # Check if facility has required capabilities
            required_capabilities = requirements.get('capabilities', [])
            if not all(cap in capabilities for cap in required_capabilities):
                continue
            
            # Calculate available capacity
            utilization = self.calculate_capacity_utilization(facility_id, date)
            
            # Check if facility can meet resource requirements
            can_meet_requirements = True
            capacity_score = 0
            
            for resource_type, required_amount in requirements.items():
                if resource_type == 'capabilities':
                    continue
                
                current_utilization = utilization.get(resource_type, 0)
                if current_utilization + (required_amount * 100) > 100:  # Over capacity
                    can_meet_requirements = False
                    break
                
                capacity_score += (100 - current_utilization) / 100
            
            if can_meet_requirements:
                available_facilities.append((facility_id, capacity_score))
        
        conn.close()
        
        # Sort by capacity score (higher is better)
        available_facilities.sort(key=lambda x: x[1], reverse=True)
        return available_facilities
    
    def optimize_job_assignment(self, jobs: List[ProductionJob]) -> Dict[str, str]:
        """Optimize job assignment to facilities"""
        assignments = {}
        
        # Sort jobs by priority and deadline
        sorted_jobs = sorted(jobs, key=lambda j: (j.priority.value, j.deadline or '9999-12-31'), reverse=True)
        
        for job in sorted_jobs:
            if job.assigned_facility:
                assignments[job.job_id] = job.assigned_facility
                continue
            
            # Find best facility for this job
            target_date = job.deadline or (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            available_facilities = self.find_available_capacity(
                job.requirements, target_date, job.estimated_duration
            )
            
            if available_facilities:
                best_facility = available_facilities[0][0]
                assignments[job.job_id] = best_facility
                
                # Update job assignment
                self._assign_job_to_facility(job.job_id, best_facility)
        
        return assignments
    
    def _assign_job_to_facility(self, job_id: str, facility_id: str):
        """Assign job to facility in database"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE production_jobs SET assigned_facility = ? WHERE job_id = ?',
                      (facility_id, job_id))
        
        conn.commit()
        conn.close()

class ProductionScheduler:
    """Production scheduling and timeline optimization"""
    
    def __init__(self, database: ManufacturingDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
    
    def create_schedule(self, facility_id: str, date: str, jobs: List[ProductionJob]) -> ProductionSchedule:
        """Create optimized production schedule for facility"""
        # Get facility operating hours
        facility = self._get_facility(facility_id)
        if not facility:
            raise ValueError(f"Facility not found: {facility_id}")
        
        # Get available resources
        resources = self._get_facility_resources(facility_id)
        
        # Sort jobs by priority and dependencies
        scheduled_jobs = []
        current_time = self._parse_start_time(facility.operating_hours.get(date.split('-')[2], '08:00'))
        end_time = self._parse_end_time(facility.operating_hours.get(date.split('-')[2], '17:00'))
        
        # Simple scheduling algorithm (can be enhanced with more sophisticated optimization)
        sorted_jobs = sorted(jobs, key=lambda j: (j.priority.value, j.estimated_duration), reverse=True)
        
        resource_allocation = {r.resource_id: 0.0 for r in resources}
        
        for job in sorted_jobs:
            if current_time >= end_time:
                break  # No more time in the day
            
            # Check resource requirements
            if self._can_schedule_job(job, resource_allocation, resources):
                job_start = current_time
                job_end = min(current_time + job.estimated_duration, end_time)
                
                scheduled_jobs.append({
                    'job_id': job.job_id,
                    'start_time': self._time_to_string(job_start),
                    'end_time': self._time_to_string(job_end),
                    'resources': job.requirements
                })
                
                # Update resource allocation
                for resource_type, required in job.requirements.items():
                    if resource_type != 'capabilities':
                        for resource in resources:
                            if resource.resource_type.value == resource_type:
                                resource_allocation[resource.resource_id] += required
                
                current_time = job_end
        
        # Calculate total utilization
        total_capacity = sum(r.capacity for r in resources)
        total_used = sum(resource_allocation.values())
        capacity_used = (total_used / total_capacity) * 100 if total_capacity > 0 else 0
        
        schedule = ProductionSchedule(
            facility_id=facility_id,
            date=date,
            scheduled_jobs=scheduled_jobs,
            resource_utilization={r.resource_id: resource_allocation[r.resource_id] for r in resources},
            total_capacity_used=capacity_used
        )
        
        # Store schedule in database
        self._store_schedule(schedule)
        
        return schedule
    
    def reschedule_due_to_delay(self, facility_id: str, delayed_job_id: str, 
                               new_estimated_duration: float) -> ProductionSchedule:
        """Reschedule facility due to job delay"""
        # Get current schedule
        today = datetime.now().strftime('%Y-%m-%d')
        current_schedule = self._get_schedule(facility_id, today)
        
        if not current_schedule:
            return None
        
        # Find delayed job and reschedule downstream jobs
        delayed_job_index = None
        for i, job in enumerate(current_schedule.scheduled_jobs):
            if job['job_id'] == delayed_job_id:
                delayed_job_index = i
                break
        
        if delayed_job_index is None:
            return current_schedule
        
        # Update delayed job duration
        delayed_job = current_schedule.scheduled_jobs[delayed_job_index]
        old_end_time = self._string_to_time(delayed_job['end_time'])
        start_time = self._string_to_time(delayed_job['start_time'])
        new_end_time = start_time + new_estimated_duration
        
        delayed_job['end_time'] = self._time_to_string(new_end_time)
        
        # Shift subsequent jobs
        time_shift = new_end_time - old_end_time
        
        for i in range(delayed_job_index + 1, len(current_schedule.scheduled_jobs)):
            job = current_schedule.scheduled_jobs[i]
            job_start = self._string_to_time(job['start_time']) + time_shift
            job_end = self._string_to_time(job['end_time']) + time_shift
            
            job['start_time'] = self._time_to_string(job_start)
            job['end_time'] = self._time_to_string(job_end)
        
        # Update and store schedule
        self._store_schedule(current_schedule)
        
        return current_schedule
    
    def _get_facility(self, facility_id: str) -> Optional[Facility]:
        """Get facility information"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM facilities WHERE facility_id = ?', (facility_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return Facility(
            facility_id=row[0], name=row[1], location=row[2],
            facility_type=FacilityType(row[3]),
            capabilities=json.loads(row[4]) if row[4] else [],
            capacity=json.loads(row[5]) if row[5] else {},
            current_utilization=json.loads(row[6]) if row[6] else {},
            operating_hours=json.loads(row[7]) if row[7] else {},
            timezone=row[8], contact_info=json.loads(row[9]) if row[9] else {},
            certifications=json.loads(row[10]) if row[10] else [],
            equipment=json.loads(row[11]) if row[11] else [],
            specializations=json.loads(row[12]) if row[12] else []
        )
    
    def _get_facility_resources(self, facility_id: str) -> List[Resource]:
        """Get all resources for a facility"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM resources WHERE facility_id = ?', (facility_id,))
        rows = cursor.fetchall()
        conn.close()
        
        resources = []
        for row in rows:
            resource = Resource(
                resource_id=row[0], resource_type=ResourceType(row[1]),
                name=row[2], facility_id=row[3], capacity=row[4],
                current_allocation=row[5],
                availability_schedule=json.loads(row[6]) if row[6] else {},
                maintenance_schedule=json.loads(row[7]) if row[7] else [],
                specifications=json.loads(row[8]) if row[8] else {},
                cost_per_hour=row[9]
            )
            resources.append(resource)
        
        return resources
    
    def _can_schedule_job(self, job: ProductionJob, resource_allocation: Dict[str, float],
                         resources: List[Resource]) -> bool:
        """Check if job can be scheduled with current resource allocation"""
        for resource_type, required in job.requirements.items():
            if resource_type == 'capabilities':
                continue
            
            available_capacity = 0
            for resource in resources:
                if resource.resource_type.value == resource_type:
                    available_capacity += resource.capacity - resource_allocation.get(resource.resource_id, 0)
            
            if required > available_capacity:
                return False
        
        return True
    
    def _parse_start_time(self, time_str: str) -> float:
        """Parse time string to hours (e.g., '08:00' -> 8.0)"""
        parts = time_str.split(':')
        return float(parts[0]) + float(parts[1]) / 60
    
    def _parse_end_time(self, time_str: str) -> float:
        """Parse time string to hours"""
        return self._parse_start_time(time_str)
    
    def _time_to_string(self, time_hours: float) -> str:
        """Convert hours to time string"""
        hours = int(time_hours)
        minutes = int((time_hours - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    def _string_to_time(self, time_str: str) -> float:
        """Convert time string to hours"""
        return self._parse_start_time(time_str)
    
    def _store_schedule(self, schedule: ProductionSchedule):
        """Store schedule in database"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO production_schedules 
            (schedule_id, facility_id, date, scheduled_jobs, resource_utilization, 
             total_capacity_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), schedule.facility_id, schedule.date,
            json.dumps(schedule.scheduled_jobs),
            json.dumps(schedule.resource_utilization),
            schedule.total_capacity_used,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _get_schedule(self, facility_id: str, date: str) -> Optional[ProductionSchedule]:
        """Get schedule from database"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT facility_id, date, scheduled_jobs, resource_utilization, total_capacity_used
            FROM production_schedules WHERE facility_id = ? AND date = ?
        ''', (facility_id, date))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return ProductionSchedule(
            facility_id=row[0], date=row[1],
            scheduled_jobs=json.loads(row[2]),
            resource_utilization=json.loads(row[3]),
            total_capacity_used=row[4]
        )

class SupplyChainMonitor:
    """Supply chain monitoring and event handling"""
    
    def __init__(self, database: ManufacturingDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
        self.event_handlers: Dict[str, List] = {}
    
    def monitor_supply_chain(self) -> List[SupplyChainEvent]:
        """Monitor supply chain for disruptions"""
        events = []
        
        # Check for material shortages
        material_events = self._check_material_availability()
        events.extend(material_events)
        
        # Check for supplier delays
        supplier_events = self._check_supplier_status()
        events.extend(supplier_events)
        
        # Check for logistics issues
        logistics_events = self._check_logistics_status()
        events.extend(logistics_events)
        
        # Store events in database
        for event in events:
            self._store_event(event)
        
        # Trigger event handlers
        for event in events:
            self._trigger_event_handlers(event)
        
        return events
    
    def _check_material_availability(self) -> List[SupplyChainEvent]:
        """Check for material shortages"""
        events = []
        
        # Mock implementation - would integrate with inventory systems
        # This would check actual inventory levels vs requirements
        
        return events
    
    def _check_supplier_status(self) -> List[SupplyChainEvent]:
        """Check supplier delivery status"""
        events = []
        
        # Mock implementation - would integrate with supplier systems
        # This would check delivery confirmations, delays, etc.
        
        return events
    
    def _check_logistics_status(self) -> List[SupplyChainEvent]:
        """Check logistics and transportation status"""
        events = []
        
        # Mock implementation - would integrate with logistics providers
        # This would check shipping delays, route disruptions, etc.
        
        return events
    
    def _store_event(self, event: SupplyChainEvent):
        """Store supply chain event in database"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO supply_chain_events 
            (event_id, event_type, severity, affected_jobs, description, 
             timestamp, expected_resolution, mitigation_actions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.event_id, event.event_type, event.severity,
            json.dumps(event.affected_jobs), event.description,
            event.timestamp, event.expected_resolution,
            json.dumps(event.mitigation_actions)
        ))
        
        conn.commit()
        conn.close()
    
    def _trigger_event_handlers(self, event: SupplyChainEvent):
        """Trigger registered event handlers"""
        handlers = self.event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Event handler error: {e}")
    
    def register_event_handler(self, event_type: str, handler):
        """Register event handler for specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

class DistributedManufacturingCoordinator:
    """Main coordinator for distributed manufacturing operations"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.database = ManufacturingDatabase(self.config.get('database_path', 'manufacturing.db'))
        
        # Initialize components
        self.capacity_planner = CapacityPlanner(self.database)
        self.scheduler = ProductionScheduler(self.database)
        self.supply_chain_monitor = SupplyChainMonitor(self.database)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # WebSocket connections for real-time updates
        self.facility_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        # Background tasks
        self.monitoring_task = None
        self.running = False
    
    async def start(self):
        """Start the distributed manufacturing coordinator"""
        self.running = True
        self.logger.info("Starting Distributed Manufacturing Coordinator...")
        
        # Start background monitoring
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Start WebSocket server for real-time facility communication
        websocket_server = await websockets.serve(
            self._handle_facility_connection,
            "localhost", 8766
        )
        
        self.logger.info("Manufacturing coordinator started on ws://localhost:8766")
        
        try:
            await asyncio.gather(
                self.monitoring_task,
                websocket_server.wait_closed()
            )
        finally:
            self.running = False
    
    def add_facility(self, facility: Facility) -> str:
        """Add manufacturing facility to the network"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO facilities 
            (facility_id, name, location, facility_type, capabilities, capacity,
             current_utilization, operating_hours, timezone, contact_info,
             certifications, equipment, specializations, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            facility.facility_id, facility.name, facility.location,
            facility.facility_type.value, json.dumps(facility.capabilities),
            json.dumps(facility.capacity), json.dumps(facility.current_utilization),
            json.dumps(facility.operating_hours), facility.timezone,
            json.dumps(facility.contact_info), json.dumps(facility.certifications),
            json.dumps(facility.equipment), json.dumps(facility.specializations),
            datetime.now().isoformat(), datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Added facility: {facility.name} ({facility.facility_id})")
        return facility.facility_id
    
    def create_production_job(self, job: ProductionJob) -> str:
        """Create new production job"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO production_jobs 
            (job_id, product_id, quantity, priority, requirements, estimated_duration,
             deadline, dependencies, assigned_facility, status, created_at, progress, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job.job_id, job.product_id, job.quantity, job.priority.value,
            json.dumps(job.requirements), job.estimated_duration,
            job.deadline, json.dumps(job.dependencies), job.assigned_facility,
            job.status.value, job.created_at, job.progress, job.notes
        ))
        
        conn.commit()
        conn.close()
        
        # Trigger job assignment optimization
        self._optimize_job_assignments()
        
        self.logger.info(f"Created production job: {job.job_id}")
        return job.job_id
    
    def get_global_capacity_overview(self) -> Dict[str, Any]:
        """Get overview of capacity across all facilities"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        # Get all facilities
        cursor.execute('SELECT facility_id, name, capacity, current_utilization FROM facilities')
        facilities = cursor.fetchall()
        
        # Get production jobs
        cursor.execute('SELECT COUNT(*), status FROM production_jobs GROUP BY status')
        job_status_counts = dict(cursor.fetchall())
        
        conn.close()
        
        # Calculate total capacity and utilization
        total_capacity = {}
        total_utilization = {}
        
        for facility_id, name, capacity_json, utilization_json in facilities:
            capacity = json.loads(capacity_json) if capacity_json else {}
            utilization = json.loads(utilization_json) if utilization_json else {}
            
            for resource_type, cap in capacity.items():
                total_capacity[resource_type] = total_capacity.get(resource_type, 0) + cap
                current_util = utilization.get(resource_type, 0)
                total_utilization[resource_type] = total_utilization.get(resource_type, 0) + current_util
        
        # Calculate utilization percentages
        utilization_percentages = {}
        for resource_type in total_capacity:
            if total_capacity[resource_type] > 0:
                utilization_percentages[resource_type] = (
                    total_utilization[resource_type] / total_capacity[resource_type]
                ) * 100
        
        return {
            'total_facilities': len(facilities),
            'total_capacity': total_capacity,
            'current_utilization': total_utilization,
            'utilization_percentages': utilization_percentages,
            'job_status_counts': job_status_counts,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                # Monitor supply chain
                events = self.supply_chain_monitor.monitor_supply_chain()
                
                if events:
                    self.logger.info(f"Detected {len(events)} supply chain events")
                    
                    # Broadcast events to connected facilities
                    await self._broadcast_supply_chain_events(events)
                
                # Update capacity utilization
                await self._update_facility_utilizations()
                
                # Check for schedule conflicts
                await self._check_schedule_conflicts()
                
                # Sleep for monitoring interval
                await asyncio.sleep(self.config.get('monitoring_interval', 60))
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)  # Short sleep on error
    
    async def _handle_facility_connection(self, websocket, path):
        """Handle WebSocket connection from facility"""
        facility_id = None
        
        try:
            # Wait for facility identification
            message = await websocket.recv()
            data = json.loads(message)
            
            if data.get('type') == 'facility_connect':
                facility_id = data.get('facility_id')
                if facility_id:
                    self.facility_connections[facility_id] = websocket
                    await websocket.send(json.dumps({
                        'type': 'connection_confirmed',
                        'facility_id': facility_id
                    }))
                    self.logger.info(f"Facility connected: {facility_id}")
            
            # Handle ongoing messages
            async for message in websocket:
                data = json.loads(message)
                await self._handle_facility_message(facility_id, data)
        
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if facility_id and facility_id in self.facility_connections:
                del self.facility_connections[facility_id]
                self.logger.info(f"Facility disconnected: {facility_id}")
    
    async def _handle_facility_message(self, facility_id: str, message: Dict[str, Any]):
        """Handle message from facility"""
        message_type = message.get('type')
        
        if message_type == 'status_update':
            await self._handle_status_update(facility_id, message)
        elif message_type == 'job_progress':
            await self._handle_job_progress(facility_id, message)
        elif message_type == 'resource_update':
            await self._handle_resource_update(facility_id, message)
        elif message_type == 'emergency_alert':
            await self._handle_emergency_alert(facility_id, message)
    
    async def _handle_status_update(self, facility_id: str, message: Dict[str, Any]):
        """Handle facility status update"""
        # Update facility status in database
        pass
    
    async def _handle_job_progress(self, facility_id: str, message: Dict[str, Any]):
        """Handle job progress update"""
        job_id = message.get('job_id')
        progress = message.get('progress', 0)
        status = message.get('status')
        
        if job_id:
            conn = sqlite3.connect(self.database.db_path)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE production_jobs SET progress = ?, status = ? WHERE job_id = ?',
                          (progress, status, job_id))
            
            conn.commit()
            conn.close()
    
    async def _handle_resource_update(self, facility_id: str, message: Dict[str, Any]):
        """Handle resource utilization update"""
        pass
    
    async def _handle_emergency_alert(self, facility_id: str, message: Dict[str, Any]):
        """Handle emergency alert from facility"""
        self.logger.warning(f"Emergency alert from {facility_id}: {message.get('description')}")
        
        # Create emergency supply chain event
        event = SupplyChainEvent(
            event_id=str(uuid.uuid4()),
            event_type="facility_emergency",
            severity="critical",
            affected_jobs=message.get('affected_jobs', []),
            description=message.get('description', 'Emergency at facility'),
            timestamp=datetime.now().isoformat()
        )
        
        # Broadcast to all facilities
        await self._broadcast_supply_chain_events([event])
    
    async def _broadcast_supply_chain_events(self, events: List[SupplyChainEvent]):
        """Broadcast supply chain events to all connected facilities"""
        message = {
            'type': 'supply_chain_events',
            'events': [asdict(event) for event in events]
        }
        
        disconnected_facilities = []
        
        for facility_id, websocket in self.facility_connections.items():
            try:
                await websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_facilities.append(facility_id)
        
        # Clean up disconnected facilities
        for facility_id in disconnected_facilities:
            del self.facility_connections[facility_id]
    
    async def _update_facility_utilizations(self):
        """Update facility capacity utilizations"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT facility_id FROM facilities')
        facility_ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        for facility_id in facility_ids:
            try:
                utilization = self.capacity_planner.calculate_capacity_utilization(facility_id, today)
                
                # Update database
                conn = sqlite3.connect(self.database.db_path)
                cursor = conn.cursor()
                
                cursor.execute('UPDATE facilities SET current_utilization = ?, updated_at = ? WHERE facility_id = ?',
                              (json.dumps(utilization), datetime.now().isoformat(), facility_id))
                
                conn.commit()
                conn.close()
                
            except Exception as e:
                self.logger.error(f"Error updating utilization for {facility_id}: {e}")
    
    async def _check_schedule_conflicts(self):
        """Check for scheduling conflicts and resolve them"""
        # Implementation would check for resource conflicts, deadline misses, etc.
        pass
    
    def _optimize_job_assignments(self):
        """Optimize job assignments across facilities"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        # Get unassigned jobs
        cursor.execute('SELECT * FROM production_jobs WHERE assigned_facility IS NULL AND status = "planned"')
        job_rows = cursor.fetchall()
        
        jobs = []
        for row in job_rows:
            job = ProductionJob(
                job_id=row[0], product_id=row[1], quantity=row[2],
                priority=Priority(row[3]), requirements=json.loads(row[4]),
                estimated_duration=row[5], deadline=row[6],
                dependencies=json.loads(row[7]) if row[7] else [],
                assigned_facility=row[8], status=ProductionStatus(row[9]),
                created_at=row[10], started_at=row[11], completed_at=row[12],
                progress=row[13], notes=row[14]
            )
            jobs.append(job)
        
        conn.close()
        
        if jobs:
            assignments = self.capacity_planner.optimize_job_assignment(jobs)
            self.logger.info(f"Optimized assignments for {len(assignments)} jobs")

async def main():
    """Example usage of distributed manufacturing system"""
    # Initialize coordinator
    coordinator = DistributedManufacturingCoordinator({
        'database_path': 'manufacturing_test.db',
        'monitoring_interval': 30
    })
    
    # Add test facilities
    facility1 = Facility(
        facility_id="FAC001",
        name="Main Assembly Plant",
        location="Detroit, MI",
        facility_type=FacilityType.ASSEMBLY,
        capabilities=["assembly", "testing", "packaging"],
        capacity={"machines": 10, "operators": 20},
        current_utilization={"machines": 0, "operators": 0},
        operating_hours={"monday": "08:00-17:00", "tuesday": "08:00-17:00"},
        timezone="America/Detroit",
        contact_info={"manager": "john.doe@company.com"}
    )
    
    coordinator.add_facility(facility1)
    
    # Create test production job
    job = ProductionJob(
        job_id="JOB001",
        product_id="PROD001",
        quantity=100,
        priority=Priority.HIGH,
        requirements={"machines": 2, "operators": 4, "capabilities": ["assembly"]},
        estimated_duration=8.0,
        deadline="2024-12-31"
    )
    
    coordinator.create_production_job(job)
    
    # Get capacity overview
    overview = coordinator.get_global_capacity_overview()
    print("Global Capacity Overview:", json.dumps(overview, indent=2))
    
    # Start coordinator
    await coordinator.start()

if __name__ == "__main__":
    asyncio.run(main())