"""
Shift Scheduling System
Comprehensive crew shift scheduling with rotation management and compliance tracking
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone, time
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
import json

from ..roles.permissions import CrewRole, Permission, PermissionManager
from ..crew.crew_management import CrewManager

logger = logging.getLogger(__name__)


class ShiftType(Enum):
    """Types of shifts"""
    WATCH = "watch"
    ENGINE_ROOM = "engine_room"
    DECK = "deck"
    FISHING = "fishing"
    GALLEY = "galley"
    MAINTENANCE = "maintenance"
    LOOKOUT = "lookout"
    RADIO = "radio"
    STANDBY = "standby"
    EMERGENCY = "emergency"


class ShiftStatus(Enum):
    """Shift status"""
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    EARLY_RELIEF = "early_relief"
    EXTENDED = "extended"


@dataclass
class RestRequirement:
    """Rest period requirements between shifts"""
    role: CrewRole
    minimum_rest_hours: float
    maximum_work_hours_per_day: float
    minimum_rest_hours_per_week: float
    maximum_work_hours_per_week: float
    special_requirements: List[str] = field(default_factory=list)


@dataclass
class ShiftTemplate:
    """Template for recurring shifts"""
    template_id: str
    name: str
    shift_type: ShiftType
    duration_hours: float
    required_role: CrewRole
    minimum_crew: int
    maximum_crew: int
    start_time: time  # Time of day
    required_qualifications: List[str] = field(default_factory=list)
    location: Optional[str] = None
    description: Optional[str] = None
    priority: int = 1  # Higher number = higher priority


@dataclass
class Shift:
    """Individual shift instance"""
    shift_id: str
    vessel_id: str
    trip_id: Optional[str]
    shift_type: ShiftType
    status: ShiftStatus
    
    # Timing
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    
    # Crew requirements
    required_role: CrewRole
    minimum_crew: int
    maximum_crew: int
    required_qualifications: List[str] = field(default_factory=list)
    
    # Assignment details
    assigned_crew: List[str] = field(default_factory=list)
    primary_assignee: Optional[str] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Shift details
    location: Optional[str] = None
    description: Optional[str] = None
    notes: List[Dict[str, Any]] = field(default_factory=list)
    template_id: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ShiftAssignment:
    """Individual crew member assignment to shift"""
    assignment_id: str
    shift_id: str
    crew_member_id: str
    role: CrewRole
    assigned_by: str
    assigned_at: datetime
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime] = None
    notes: Optional[str] = None


@dataclass
class ShiftRotation:
    """Rotating shift pattern"""
    rotation_id: str
    name: str
    vessel_id: str
    pattern: List[str]  # List of shift template IDs
    crew_assignments: Dict[str, List[str]]  # crew_member_id -> list of positions in rotation
    rotation_length_days: int
    start_date: datetime
    active: bool = True
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ScheduleConflict:
    """Detected scheduling conflict"""
    conflict_id: str
    conflict_type: str  # 'overlap', 'rest_violation', 'qualification_missing', etc.
    severity: str  # 'minor', 'major', 'critical'
    crew_member_id: str
    shift_ids: List[str]
    description: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None


class ShiftScheduler:
    """Main shift scheduling system"""
    
    def __init__(self, crew_manager: CrewManager, permission_manager: PermissionManager):
        self.crew_manager = crew_manager
        self.permission_manager = permission_manager
        
        # Storage
        self.shifts: Dict[str, Shift] = {}
        self.shift_assignments: Dict[str, ShiftAssignment] = {}
        self.shift_templates: Dict[str, ShiftTemplate] = {}
        self.rotations: Dict[str, ShiftRotation] = {}
        self.conflicts: Dict[str, ScheduleConflict] = {}
        
        # Rest requirements
        self.rest_requirements = self._setup_rest_requirements()
        
        # Indices for efficient querying
        self.shifts_by_crew: Dict[str, Set[str]] = {}
        self.shifts_by_vessel: Dict[str, Set[str]] = {}
        self.shifts_by_date: Dict[str, Set[str]] = {}  # YYYY-MM-DD -> shift_ids
        
        # WebSocket connections
        self.websocket_connections: Dict[str, Any] = {}
        
        # Setup default templates
        self._setup_default_templates()
        
        logger.info("Shift Scheduler initialized")
    
    def _setup_rest_requirements(self) -> Dict[CrewRole, RestRequirement]:
        """Setup maritime rest requirements"""
        return {
            CrewRole.CAPTAIN: RestRequirement(
                role=CrewRole.CAPTAIN,
                minimum_rest_hours=6.0,  # Minimum 6 hours rest per 24-hour period
                maximum_work_hours_per_day=14.0,
                minimum_rest_hours_per_week=70.0,
                maximum_work_hours_per_week=91.0,
                special_requirements=["Can work extended hours in emergency"]
            ),
            CrewRole.FIRST_MATE: RestRequirement(
                role=CrewRole.FIRST_MATE,
                minimum_rest_hours=10.0,
                maximum_work_hours_per_day=14.0,
                minimum_rest_hours_per_week=77.0,
                maximum_work_hours_per_week=72.0
            ),
            CrewRole.ENGINEER: RestRequirement(
                role=CrewRole.ENGINEER,
                minimum_rest_hours=10.0,
                maximum_work_hours_per_day=12.0,
                minimum_rest_hours_per_week=77.0,
                maximum_work_hours_per_week=72.0
            ),
            CrewRole.COOK: RestRequirement(
                role=CrewRole.COOK,
                minimum_rest_hours=10.0,
                maximum_work_hours_per_day=12.0,
                minimum_rest_hours_per_week=77.0,
                maximum_work_hours_per_week=72.0
            ),
            CrewRole.DECK_HAND: RestRequirement(
                role=CrewRole.DECK_HAND,
                minimum_rest_hours=10.0,
                maximum_work_hours_per_day=12.0,
                minimum_rest_hours_per_week=77.0,
                maximum_work_hours_per_week=72.0
            )
        }
    
    def _setup_default_templates(self) -> None:
        """Setup default shift templates"""
        templates = [
            ShiftTemplate(
                template_id="watch_0000_0600",
                name="Middle Watch (00:00-06:00)",
                shift_type=ShiftType.WATCH,
                duration_hours=6.0,
                required_role=CrewRole.DECK_HAND,
                minimum_crew=1,
                maximum_crew=2,
                start_time=time(0, 0),
                required_qualifications=["Basic Watch", "Radio Operation"],
                location="Bridge",
                description="Night watch duty with navigation monitoring"
            ),
            ShiftTemplate(
                template_id="watch_0600_1200",
                name="Morning Watch (06:00-12:00)",
                shift_type=ShiftType.WATCH,
                duration_hours=6.0,
                required_role=CrewRole.FIRST_MATE,
                minimum_crew=1,
                maximum_crew=2,
                start_time=time(6, 0),
                required_qualifications=["Navigation", "Radio Operation"],
                location="Bridge",
                description="Morning watch with increased activity"
            ),
            ShiftTemplate(
                template_id="watch_1200_1800",
                name="Afternoon Watch (12:00-18:00)",
                shift_type=ShiftType.WATCH,
                duration_hours=6.0,
                required_role=CrewRole.DECK_HAND,
                minimum_crew=1,
                maximum_crew=2,
                start_time=time(12, 0),
                required_qualifications=["Basic Watch", "Radio Operation"],
                location="Bridge",
                description="Afternoon watch during active fishing"
            ),
            ShiftTemplate(
                template_id="watch_1800_0000",
                name="Evening Watch (18:00-00:00)",
                shift_type=ShiftType.WATCH,
                duration_hours=6.0,
                required_role=CrewRole.FIRST_MATE,
                minimum_crew=1,
                maximum_crew=2,
                start_time=time(18, 0),
                required_qualifications=["Navigation", "Radio Operation"],
                location="Bridge",
                description="Evening watch with fishing operations"
            ),
            ShiftTemplate(
                template_id="engine_room_day",
                name="Engine Room Day Shift",
                shift_type=ShiftType.ENGINE_ROOM,
                duration_hours=8.0,
                required_role=CrewRole.ENGINEER,
                minimum_crew=1,
                maximum_crew=1,
                start_time=time(6, 0),
                required_qualifications=["Marine Engineering", "Diesel Engine Maintenance"],
                location="Engine Room",
                description="Daily engine maintenance and monitoring"
            ),
            ShiftTemplate(
                template_id="galley_day",
                name="Galley Day Shift",
                shift_type=ShiftType.GALLEY,
                duration_hours=10.0,
                required_role=CrewRole.COOK,
                minimum_crew=1,
                maximum_crew=1,
                start_time=time(5, 0),
                required_qualifications=["Food Safety", "Marine Cooking"],
                location="Galley",
                description="Meal preparation and galley management"
            )
        ]
        
        for template in templates:
            self.shift_templates[template.template_id] = template
    
    async def create_shift(self, vessel_id: str, shift_type: ShiftType,
                          scheduled_start: datetime, duration_hours: float,
                          required_role: CrewRole, created_by: str,
                          template_id: Optional[str] = None,
                          trip_id: Optional[str] = None,
                          minimum_crew: int = 1,
                          maximum_crew: int = 1,
                          location: Optional[str] = None,
                          description: Optional[str] = None) -> Optional[str]:
        """Create a new shift"""
        try:
            # Verify creator permissions
            creator = await self.crew_manager.get_crew_member(created_by)
            if not creator:
                logger.error(f"Creator {created_by} not found")
                return None
            
            can_schedule = self.permission_manager.has_permission(
                creator.role, Permission.ASSIGN_TASKS  # Using this as scheduling permission
            )
            if not can_schedule:
                logger.error(f"User {created_by} cannot create shifts")
                return None
            
            shift_id = str(uuid.uuid4())
            scheduled_end = scheduled_start + timedelta(hours=duration_hours)
            
            # Apply template if provided
            if template_id and template_id in self.shift_templates:
                template = self.shift_templates[template_id]
                shift_type = template.shift_type
                required_role = template.required_role
                minimum_crew = template.minimum_crew
                maximum_crew = template.maximum_crew
                location = location or template.location
                description = description or template.description
            
            shift = Shift(
                shift_id=shift_id,
                vessel_id=vessel_id,
                trip_id=trip_id,
                shift_type=shift_type,
                status=ShiftStatus.SCHEDULED,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                required_role=required_role,
                minimum_crew=minimum_crew,
                maximum_crew=maximum_crew,
                location=location,
                description=description,
                template_id=template_id,
                created_by=created_by
            )
            
            # Store shift
            self.shifts[shift_id] = shift
            self._update_shift_indices(shift, add=True)
            
            logger.info(f"Created shift {shift_id}: {shift_type.value} on {scheduled_start}")
            
            # Check for conflicts
            await self._check_shift_conflicts(shift_id)
            
            # Broadcast update
            await self._broadcast_shift_update(shift, 'created')
            
            return shift_id
            
        except Exception as e:
            logger.error(f"Failed to create shift: {e}")
            return None
    
    async def assign_crew_to_shift(self, shift_id: str, crew_member_id: str,
                                  assigner_id: str, notes: Optional[str] = None) -> Optional[str]:
        """Assign crew member to shift"""
        try:
            shift = self.shifts.get(shift_id)
            if not shift:
                logger.error(f"Shift {shift_id} not found")
                return None
            
            # Verify assigner permissions
            assigner = await self.crew_manager.get_crew_member(assigner_id)
            if not assigner:
                return None
            
            can_assign = self.permission_manager.has_permission(
                assigner.role, Permission.ASSIGN_TASKS
            )
            if not can_assign:
                logger.error(f"User {assigner_id} cannot assign shifts")
                return None
            
            # Check if shift is full
            if len(shift.assigned_crew) >= shift.maximum_crew:
                logger.error(f"Shift {shift_id} is already at maximum capacity")
                return None
            
            # Verify crew member exists and qualifications
            crew_member = await self.crew_manager.get_crew_member(crew_member_id)
            if not crew_member:
                logger.error(f"Crew member {crew_member_id} not found")
                return None
            
            # Check role compatibility
            if crew_member.role != shift.required_role:
                # Check if role can cover the required role
                role_hierarchy = {
                    CrewRole.CAPTAIN: [CrewRole.CAPTAIN, CrewRole.FIRST_MATE, CrewRole.DECK_HAND],
                    CrewRole.FIRST_MATE: [CrewRole.FIRST_MATE, CrewRole.DECK_HAND],
                    CrewRole.ENGINEER: [CrewRole.ENGINEER],
                    CrewRole.COOK: [CrewRole.COOK],
                    CrewRole.DECK_HAND: [CrewRole.DECK_HAND]
                }
                
                if shift.required_role not in role_hierarchy.get(crew_member.role, []):
                    logger.error(f"Crew member role {crew_member.role} cannot cover {shift.required_role}")
                    return None
            
            # Check for conflicts
            conflicts = await self._check_crew_shift_conflicts(crew_member_id, shift)
            if conflicts:
                logger.warning(f"Conflicts detected for assignment: {[c.description for c in conflicts]}")
                # You might want to return the conflicts instead of failing
            
            # Create assignment
            assignment_id = str(uuid.uuid4())
            assignment = ShiftAssignment(
                assignment_id=assignment_id,
                shift_id=shift_id,
                crew_member_id=crew_member_id,
                role=crew_member.role,
                assigned_by=assigner_id,
                assigned_at=datetime.now(timezone.utc),
                notes=notes
            )
            
            # Update shift
            self._update_shift_indices(shift, add=False)
            shift.assigned_crew.append(crew_member_id)
            if not shift.primary_assignee:
                shift.primary_assignee = crew_member_id
            self._update_shift_indices(shift, add=True)
            
            # Store assignment
            self.shift_assignments[assignment_id] = assignment
            
            logger.info(f"Assigned crew {crew_member_id} to shift {shift_id}")
            
            # Broadcast update
            await self._broadcast_shift_update(shift, 'assigned')
            
            return assignment_id
            
        except Exception as e:
            logger.error(f"Failed to assign crew to shift: {e}")
            return None
    
    async def start_shift(self, shift_id: str, started_by: str) -> bool:
        """Start a shift"""
        try:
            shift = self.shifts.get(shift_id)
            if not shift:
                logger.error(f"Shift {shift_id} not found")
                return False
            
            if shift.status != ShiftStatus.SCHEDULED:
                logger.error(f"Shift {shift_id} cannot be started (status: {shift.status})")
                return False
            
            # Verify starter is assigned to shift or has override permission
            if started_by not in shift.assigned_crew:
                user = await self.crew_manager.get_crew_member(started_by)
                if not user:
                    return False
                
                can_override = self.permission_manager.has_permission(
                    user.role, Permission.OVERRIDE_ALARMS
                )
                if not can_override:
                    logger.error(f"User {started_by} cannot start shift")
                    return False
            
            # Update shift
            self._update_shift_indices(shift, add=False)
            shift.status = ShiftStatus.ACTIVE
            shift.actual_start = datetime.now(timezone.utc)
            self._update_shift_indices(shift, add=True)
            
            # Add note
            shift.notes.append({
                'type': 'started',
                'message': f"Shift started by {started_by}",
                'timestamp': shift.actual_start,
                'author': started_by
            })
            
            logger.info(f"Started shift {shift_id}")
            
            # Broadcast update
            await self._broadcast_shift_update(shift, 'started')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start shift: {e}")
            return False
    
    async def end_shift(self, shift_id: str, ended_by: str,
                       notes: Optional[str] = None) -> bool:
        """End a shift"""
        try:
            shift = self.shifts.get(shift_id)
            if not shift:
                logger.error(f"Shift {shift_id} not found")
                return False
            
            if shift.status != ShiftStatus.ACTIVE:
                logger.error(f"Shift {shift_id} is not active")
                return False
            
            # Verify ender is assigned to shift or has override permission
            if ended_by not in shift.assigned_crew:
                user = await self.crew_manager.get_crew_member(ended_by)
                if not user:
                    return False
                
                can_override = self.permission_manager.has_permission(
                    user.role, Permission.OVERRIDE_ALARMS
                )
                if not can_override:
                    logger.error(f"User {ended_by} cannot end shift")
                    return False
            
            # Update shift
            self._update_shift_indices(shift, add=False)
            shift.status = ShiftStatus.COMPLETED
            shift.actual_end = datetime.now(timezone.utc)
            self._update_shift_indices(shift, add=True)
            
            # Add note
            end_note = {
                'type': 'completed',
                'message': f"Shift ended by {ended_by}",
                'timestamp': shift.actual_end,
                'author': ended_by
            }
            if notes:
                end_note['additional_notes'] = notes
            shift.notes.append(end_note)
            
            logger.info(f"Ended shift {shift_id}")
            
            # Broadcast update
            await self._broadcast_shift_update(shift, 'completed')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to end shift: {e}")
            return False
    
    async def create_rotation(self, name: str, vessel_id: str,
                             pattern: List[str], crew_assignments: Dict[str, List[str]],
                             rotation_length_days: int, start_date: datetime,
                             created_by: str) -> Optional[str]:
        """Create a shift rotation pattern"""
        try:
            # Verify creator permissions
            creator = await self.crew_manager.get_crew_member(created_by)
            if not creator:
                return None
            
            can_create = self.permission_manager.has_permission(
                creator.role, Permission.ASSIGN_TASKS
            )
            if not can_create:
                logger.error(f"User {created_by} cannot create rotations")
                return None
            
            # Validate pattern templates exist
            for template_id in pattern:
                if template_id not in self.shift_templates:
                    logger.error(f"Template {template_id} not found")
                    return None
            
            # Validate crew members exist
            for crew_id in crew_assignments.keys():
                crew_member = await self.crew_manager.get_crew_member(crew_id)
                if not crew_member:
                    logger.error(f"Crew member {crew_id} not found")
                    return None
            
            rotation_id = str(uuid.uuid4())
            rotation = ShiftRotation(
                rotation_id=rotation_id,
                name=name,
                vessel_id=vessel_id,
                pattern=pattern,
                crew_assignments=crew_assignments,
                rotation_length_days=rotation_length_days,
                start_date=start_date,
                created_by=created_by
            )
            
            self.rotations[rotation_id] = rotation
            
            logger.info(f"Created rotation {rotation_id}: {name}")
            
            # Generate initial shifts from rotation
            await self._generate_rotation_shifts(rotation)
            
            return rotation_id
            
        except Exception as e:
            logger.error(f"Failed to create rotation: {e}")
            return None
    
    async def _generate_rotation_shifts(self, rotation: ShiftRotation) -> None:
        """Generate shifts from rotation pattern"""
        try:
            current_date = rotation.start_date.date()
            end_date = current_date + timedelta(days=rotation.rotation_length_days)
            
            pattern_index = 0
            
            while current_date < end_date:
                for template_id in rotation.pattern:
                    template = self.shift_templates.get(template_id)
                    if not template:
                        continue
                    
                    # Calculate shift start time
                    shift_datetime = datetime.combine(
                        current_date,
                        template.start_time,
                        tzinfo=timezone.utc
                    )
                    
                    # Create shift
                    shift_id = await self.create_shift(
                        vessel_id=rotation.vessel_id,
                        shift_type=template.shift_type,
                        scheduled_start=shift_datetime,
                        duration_hours=template.duration_hours,
                        required_role=template.required_role,
                        created_by=rotation.created_by,
                        template_id=template_id,
                        minimum_crew=template.minimum_crew,
                        maximum_crew=template.maximum_crew,
                        location=template.location,
                        description=template.description
                    )
                    
                    if shift_id:
                        # Assign crew based on rotation
                        for crew_id, positions in rotation.crew_assignments.items():
                            if pattern_index % len(positions) < len(positions):
                                await self.assign_crew_to_shift(
                                    shift_id, crew_id, rotation.created_by
                                )
                    
                    pattern_index += 1
                
                current_date += timedelta(days=1)
            
        except Exception as e:
            logger.error(f"Failed to generate rotation shifts: {e}")
    
    async def _check_shift_conflicts(self, shift_id: str) -> List[ScheduleConflict]:
        """Check for conflicts with a shift"""
        conflicts = []
        shift = self.shifts.get(shift_id)
        if not shift:
            return conflicts
        
        for crew_id in shift.assigned_crew:
            crew_conflicts = await self._check_crew_shift_conflicts(crew_id, shift)
            conflicts.extend(crew_conflicts)
        
        return conflicts
    
    async def _check_crew_shift_conflicts(self, crew_member_id: str, 
                                        shift: Shift) -> List[ScheduleConflict]:
        """Check for conflicts between crew member and shift"""
        conflicts = []
        
        # Get crew member's other shifts
        crew_shifts = self.shifts_by_crew.get(crew_member_id, set())
        
        for other_shift_id in crew_shifts:
            if other_shift_id == shift.shift_id:
                continue
            
            other_shift = self.shifts.get(other_shift_id)
            if not other_shift or other_shift.status in [ShiftStatus.CANCELLED, ShiftStatus.COMPLETED]:
                continue
            
            # Check for time overlap
            if self._shifts_overlap(shift, other_shift):
                conflict = ScheduleConflict(
                    conflict_id=str(uuid.uuid4()),
                    conflict_type='overlap',
                    severity='major',
                    crew_member_id=crew_member_id,
                    shift_ids=[shift.shift_id, other_shift.shift_id],
                    description=f"Overlapping shifts for crew member {crew_member_id}"
                )
                conflicts.append(conflict)
                self.conflicts[conflict.conflict_id] = conflict
            
            # Check rest period violations
            rest_violation = self._check_rest_violation(crew_member_id, shift, other_shift)
            if rest_violation:
                conflicts.append(rest_violation)
                self.conflicts[rest_violation.conflict_id] = rest_violation
        
        return conflicts
    
    def _shifts_overlap(self, shift1: Shift, shift2: Shift) -> bool:
        """Check if two shifts overlap in time"""
        return (shift1.scheduled_start < shift2.scheduled_end and 
                shift1.scheduled_end > shift2.scheduled_start)
    
    def _check_rest_violation(self, crew_member_id: str, shift1: Shift, 
                            shift2: Shift) -> Optional[ScheduleConflict]:
        """Check if shifts violate rest requirements"""
        # Get rest requirements for crew member
        crew_member_role = CrewRole.DECK_HAND  # Default, should get from crew_manager
        rest_req = self.rest_requirements.get(crew_member_role)
        if not rest_req:
            return None
        
        # Calculate time between shifts
        if shift1.scheduled_end <= shift2.scheduled_start:
            rest_time = (shift2.scheduled_start - shift1.scheduled_end).total_seconds() / 3600
            if rest_time < rest_req.minimum_rest_hours:
                return ScheduleConflict(
                    conflict_id=str(uuid.uuid4()),
                    conflict_type='rest_violation',
                    severity='critical',
                    crew_member_id=crew_member_id,
                    shift_ids=[shift1.shift_id, shift2.shift_id],
                    description=f"Insufficient rest period: {rest_time:.1f}h (required: {rest_req.minimum_rest_hours}h)"
                )
        elif shift2.scheduled_end <= shift1.scheduled_start:
            rest_time = (shift1.scheduled_start - shift2.scheduled_end).total_seconds() / 3600
            if rest_time < rest_req.minimum_rest_hours:
                return ScheduleConflict(
                    conflict_id=str(uuid.uuid4()),
                    conflict_type='rest_violation',
                    severity='critical',
                    crew_member_id=crew_member_id,
                    shift_ids=[shift2.shift_id, shift1.shift_id],
                    description=f"Insufficient rest period: {rest_time:.1f}h (required: {rest_req.minimum_rest_hours}h)"
                )
        
        return None
    
    def get_schedule_for_crew(self, crew_member_id: str, 
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get schedule for specific crew member"""
        if not start_date:
            start_date = datetime.now(timezone.utc)
        if not end_date:
            end_date = start_date + timedelta(days=7)
        
        crew_shift_ids = self.shifts_by_crew.get(crew_member_id, set())
        
        schedule = []
        for shift_id in crew_shift_ids:
            shift = self.shifts.get(shift_id)
            if not shift:
                continue
            
            # Filter by date range
            if shift.scheduled_start >= end_date or shift.scheduled_end <= start_date:
                continue
            
            schedule.append(self._shift_to_dict(shift))
        
        # Sort by start time
        return sorted(schedule, key=lambda x: x['scheduled_start'])
    
    def get_schedule_for_vessel(self, vessel_id: str,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get complete schedule for vessel"""
        if not start_date:
            start_date = datetime.now(timezone.utc)
        if not end_date:
            end_date = start_date + timedelta(days=7)
        
        vessel_shift_ids = self.shifts_by_vessel.get(vessel_id, set())
        
        schedule = []
        for shift_id in vessel_shift_ids:
            shift = self.shifts.get(shift_id)
            if not shift:
                continue
            
            # Filter by date range
            if shift.scheduled_start >= end_date or shift.scheduled_end <= start_date:
                continue
            
            schedule.append(self._shift_to_dict(shift))
        
        return sorted(schedule, key=lambda x: x['scheduled_start'])
    
    def get_shift_statistics(self, vessel_id: Optional[str] = None) -> Dict[str, Any]:
        """Get shift statistics"""
        if vessel_id:
            shift_ids = self.shifts_by_vessel.get(vessel_id, set())
        else:
            shift_ids = set(self.shifts.keys())
        
        stats = {
            'total_shifts': len(shift_ids),
            'by_status': {status.value: 0 for status in ShiftStatus},
            'by_type': {shift_type.value: 0 for shift_type in ShiftType},
            'conflicts': len([c for c in self.conflicts.values() if not c.resolved]),
            'coverage': {},
            'rest_compliance': 0.0
        }
        
        for shift_id in shift_ids:
            shift = self.shifts.get(shift_id)
            if not shift:
                continue
            
            stats['by_status'][shift.status.value] += 1
            stats['by_type'][shift.shift_type.value] += 1
        
        return stats
    
    def _update_shift_indices(self, shift: Shift, add: bool = True) -> None:
        """Update shift indices for efficient querying"""
        date_key = shift.scheduled_start.date().isoformat()
        
        if add:
            # Add to indices
            for crew_id in shift.assigned_crew:
                self.shifts_by_crew.setdefault(crew_id, set()).add(shift.shift_id)
            self.shifts_by_vessel.setdefault(shift.vessel_id, set()).add(shift.shift_id)
            self.shifts_by_date.setdefault(date_key, set()).add(shift.shift_id)
        else:
            # Remove from indices
            for crew_id in shift.assigned_crew:
                if crew_id in self.shifts_by_crew:
                    self.shifts_by_crew[crew_id].discard(shift.shift_id)
            if shift.vessel_id in self.shifts_by_vessel:
                self.shifts_by_vessel[shift.vessel_id].discard(shift.shift_id)
            if date_key in self.shifts_by_date:
                self.shifts_by_date[date_key].discard(shift.shift_id)
    
    def _shift_to_dict(self, shift: Shift) -> Dict[str, Any]:
        """Convert shift to dictionary"""
        return {
            'shift_id': shift.shift_id,
            'vessel_id': shift.vessel_id,
            'trip_id': shift.trip_id,
            'shift_type': shift.shift_type.value,
            'status': shift.status.value,
            'scheduled_start': shift.scheduled_start.isoformat(),
            'scheduled_end': shift.scheduled_end.isoformat(),
            'actual_start': shift.actual_start.isoformat() if shift.actual_start else None,
            'actual_end': shift.actual_end.isoformat() if shift.actual_end else None,
            'required_role': shift.required_role.value,
            'minimum_crew': shift.minimum_crew,
            'maximum_crew': shift.maximum_crew,
            'assigned_crew': shift.assigned_crew,
            'primary_assignee': shift.primary_assignee,
            'location': shift.location,
            'description': shift.description,
            'template_id': shift.template_id,
            'notes': [
                {
                    **note,
                    'timestamp': note['timestamp'].isoformat() if isinstance(note['timestamp'], datetime) else note['timestamp']
                }
                for note in shift.notes
            ]
        }
    
    async def _broadcast_shift_update(self, shift: Shift, action: str) -> None:
        """Broadcast shift update to connected clients"""
        message = {
            'type': 'shift_update',
            'action': action,
            'shift': self._shift_to_dict(shift)
        }
        
        await self._broadcast_to_websockets(message)
    
    async def _broadcast_to_websockets(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for connection_id, websocket in self.websocket_connections.items():
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            del self.websocket_connections[connection_id]
    
    def register_websocket(self, connection_id: str, websocket: Any) -> None:
        """Register WebSocket connection for real-time updates"""
        self.websocket_connections[connection_id] = websocket
        logger.info(f"Registered WebSocket connection {connection_id}")
    
    def unregister_websocket(self, connection_id: str) -> None:
        """Unregister WebSocket connection"""
        if connection_id in self.websocket_connections:
            del self.websocket_connections[connection_id]
            logger.info(f"Unregistered WebSocket connection {connection_id}")