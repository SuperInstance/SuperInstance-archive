"""
Safety Drill Tracking System
Comprehensive management and tracking of safety drills and compliance requirements
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
import json

from ..roles.permissions import CrewRole, Permission, PermissionManager
from ..crew.crew_management import CrewManager

logger = logging.getLogger(__name__)


class DrillType(Enum):
    """Types of safety drills"""
    FIRE_DRILL = "fire_drill"
    ABANDON_SHIP = "abandon_ship"
    MAN_OVERBOARD = "man_overboard"
    COLLISION = "collision"
    FLOODING = "flooding"
    MEDICAL_EMERGENCY = "medical_emergency"
    SEARCH_RESCUE = "search_rescue"
    POLLUTION_RESPONSE = "pollution_response"
    SECURITY = "security"
    GENERAL_ALARM = "general_alarm"
    LIFEBOAT_LAUNCH = "lifeboat_launch"
    FIRE_SUPPRESSION = "fire_suppression"
    DAMAGE_CONTROL = "damage_control"


class DrillStatus(Enum):
    """Status of safety drills"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"
    FAILED = "failed"


@dataclass
class SafetyRequirement:
    """Safety compliance requirement"""
    requirement_id: str
    name: str
    drill_type: DrillType
    frequency_days: int  # How often drill must be conducted
    mandatory_participants: List[CrewRole]  # Roles that must participate
    minimum_participants: int
    regulatory_basis: str  # SOLAS, STCW, etc.
    description: str
    certification_required: bool = False
    seasonal_requirements: List[str] = field(default_factory=list)  # Special seasonal requirements
    vessel_type_specific: bool = False


@dataclass
class DrillParticipant:
    """Individual drill participant"""
    crew_member_id: str
    role: CrewRole
    attended: bool
    performance_rating: Optional[int] = None  # 1-5 scale
    notes: Optional[str] = None
    certification_status: Optional[str] = None  # valid, expired, not_required
    special_responsibilities: List[str] = field(default_factory=list)


@dataclass
class DrillResult:
    """Results and evaluation of a drill"""
    drill_id: str
    overall_rating: int  # 1-5 scale
    objectives_met: List[str] = field(default_factory=list)
    objectives_failed: List[str] = field(default_factory=list)
    equipment_tested: Dict[str, str] = field(default_factory=dict)  # equipment -> status
    response_time_seconds: Optional[int] = None
    areas_for_improvement: List[str] = field(default_factory=list)
    safety_issues_identified: List[str] = field(default_factory=list)
    corrective_actions_required: List[str] = field(default_factory=list)
    evaluator_comments: Optional[str] = None
    weather_conditions: Optional[str] = None
    sea_conditions: Optional[str] = None


@dataclass
class SafetyDrill:
    """Safety drill record"""
    drill_id: str
    drill_type: DrillType
    status: DrillStatus
    vessel_id: str
    trip_id: Optional[str]
    
    # Scheduling
    scheduled_date: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    
    # Drill details
    drill_master: str  # Crew member conducting the drill
    scenario_description: str = ""
    objectives: List[str] = field(default_factory=list)
    equipment_required: List[str] = field(default_factory=list)
    
    # Participation
    participants: List[DrillParticipant] = field(default_factory=list)
    required_participants: List[CrewRole] = field(default_factory=list)
    excused_absences: Dict[str, str] = field(default_factory=dict)  # crew_id -> reason
    
    # Results
    drill_result: Optional[DrillResult] = None
    compliance_met: Optional[bool] = None
    regulatory_compliance: List[str] = field(default_factory=list)  # Which regulations satisfied
    
    # Administration
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Documentation
    photos: List[str] = field(default_factory=list)  # Photo file paths
    documents: List[str] = field(default_factory=list)  # Document file paths
    witness_signatures: Dict[str, datetime] = field(default_factory=dict)  # crew_id -> signature_time
    
    notes: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DrillSchedule:
    """Scheduled drill series"""
    schedule_id: str
    vessel_id: str
    drill_type: DrillType
    frequency_days: int
    next_due_date: datetime
    last_completed_drill_id: Optional[str] = None
    last_completed_date: Optional[datetime] = None
    overdue_grace_days: int = 7
    active: bool = True
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ComplianceRecord:
    """Compliance tracking record"""
    record_id: str
    vessel_id: str
    regulation_type: str  # SOLAS, STCW, USCG, etc.
    requirement_name: str
    last_satisfied_date: Optional[datetime] = None
    next_due_date: Optional[datetime] = None
    compliance_status: str = "unknown"  # compliant, non_compliant, overdue, unknown
    related_drills: List[str] = field(default_factory=list)  # drill_ids that satisfy this requirement
    grace_period_days: int = 0
    notes: List[str] = field(default_factory=list)


class DrillTracker:
    """Main safety drill tracking and compliance system"""
    
    def __init__(self, crew_manager: CrewManager, permission_manager: PermissionManager):
        self.crew_manager = crew_manager
        self.permission_manager = permission_manager
        
        # Storage
        self.drills: Dict[str, SafetyDrill] = {}
        self.drill_schedules: Dict[str, DrillSchedule] = {}
        self.compliance_records: Dict[str, ComplianceRecord] = {}
        self.safety_requirements: Dict[str, SafetyRequirement] = {}
        
        # Indices
        self.drills_by_vessel: Dict[str, Set[str]] = {}
        self.drills_by_type: Dict[DrillType, Set[str]] = {}
        self.drills_by_status: Dict[DrillStatus, Set[str]] = {}
        self.schedules_by_vessel: Dict[str, Set[str]] = {}
        
        # WebSocket connections
        self.websocket_connections: Dict[str, Any] = {}
        
        # Setup default requirements
        self._setup_default_requirements()
        
        logger.info("Drill Tracker initialized")
    
    def _setup_default_requirements(self) -> None:
        """Setup default safety requirements based on maritime regulations"""
        requirements = [
            SafetyRequirement(
                requirement_id="solas_fire_drill_weekly",
                name="Weekly Fire Drill",
                drill_type=DrillType.FIRE_DRILL,
                frequency_days=7,
                mandatory_participants=[CrewRole.CAPTAIN, CrewRole.FIRST_MATE],
                minimum_participants=3,
                regulatory_basis="SOLAS Chapter III, Regulation 19.3.1",
                description="Weekly fire drill with different scenarios",
                certification_required=True
            ),
            SafetyRequirement(
                requirement_id="solas_abandon_ship_monthly",
                name="Monthly Abandon Ship Drill",
                drill_type=DrillType.ABANDON_SHIP,
                frequency_days=30,
                mandatory_participants=[CrewRole.CAPTAIN, CrewRole.FIRST_MATE],
                minimum_participants=4,
                regulatory_basis="SOLAS Chapter III, Regulation 19.3.2",
                description="Complete abandon ship drill with lifeboat/life raft deployment",
                certification_required=True
            ),
            SafetyRequirement(
                requirement_id="man_overboard_quarterly",
                name="Quarterly Man Overboard Drill",
                drill_type=DrillType.MAN_OVERBOARD,
                frequency_days=90,
                mandatory_participants=[CrewRole.CAPTAIN, CrewRole.FIRST_MATE, CrewRole.DECK_HAND],
                minimum_participants=3,
                regulatory_basis="USCG 46 CFR 97.15-10",
                description="Man overboard recovery procedures",
                certification_required=False
            ),
            SafetyRequirement(
                requirement_id="medical_emergency_biannual",
                name="Biannual Medical Emergency Drill",
                drill_type=DrillType.MEDICAL_EMERGENCY,
                frequency_days=180,
                mandatory_participants=[CrewRole.CAPTAIN, CrewRole.FIRST_MATE, CrewRole.COOK],
                minimum_participants=2,
                regulatory_basis="STCW A-VI/4-1",
                description="Medical emergency response and first aid procedures",
                certification_required=True
            ),
            SafetyRequirement(
                requirement_id="damage_control_quarterly",
                name="Quarterly Damage Control Drill",
                drill_type=DrillType.DAMAGE_CONTROL,
                frequency_days=90,
                mandatory_participants=[CrewRole.CAPTAIN, CrewRole.ENGINEER, CrewRole.DECK_HAND],
                minimum_participants=3,
                regulatory_basis="SOLAS Chapter II-1, Regulation 19",
                description="Damage control and flooding response procedures",
                certification_required=False
            )
        ]
        
        for requirement in requirements:
            self.safety_requirements[requirement.requirement_id] = requirement
    
    async def schedule_drill(self, vessel_id: str, drill_type: DrillType,
                           scheduled_date: datetime, drill_master_id: str,
                           scenario_description: str, objectives: List[str],
                           created_by: str, trip_id: Optional[str] = None,
                           equipment_required: Optional[List[str]] = None) -> Optional[str]:
        """Schedule a new safety drill"""
        try:
            # Verify creator permissions
            creator = await self.crew_manager.get_crew_member(created_by)
            if not creator:
                logger.error(f"Creator {created_by} not found")
                return None
            
            can_schedule = self.permission_manager.has_permission(
                creator.role, Permission.CONDUCT_DRILLS
            )
            if not can_schedule:
                logger.error(f"User {created_by} cannot schedule drills")
                return None
            
            # Verify drill master exists and has permission
            drill_master = await self.crew_manager.get_crew_member(drill_master_id)
            if not drill_master:
                logger.error(f"Drill master {drill_master_id} not found")
                return None
            
            can_conduct = self.permission_manager.has_permission(
                drill_master.role, Permission.CONDUCT_DRILLS
            )
            if not can_conduct:
                logger.error(f"Drill master {drill_master_id} cannot conduct drills")
                return None
            
            drill_id = str(uuid.uuid4())
            
            # Get required participants for drill type
            required_participants = []
            for requirement in self.safety_requirements.values():
                if requirement.drill_type == drill_type:
                    required_participants = requirement.mandatory_participants
                    break
            
            drill = SafetyDrill(
                drill_id=drill_id,
                drill_type=drill_type,
                status=DrillStatus.SCHEDULED,
                vessel_id=vessel_id,
                trip_id=trip_id,
                scheduled_date=scheduled_date,
                drill_master=drill_master_id,
                scenario_description=scenario_description,
                objectives=objectives,
                equipment_required=equipment_required or [],
                required_participants=required_participants,
                created_by=created_by
            )
            
            # Store drill
            self.drills[drill_id] = drill
            self._update_drill_indices(drill, add=True)
            
            logger.info(f"Scheduled {drill_type.value} drill {drill_id} for {scheduled_date}")
            
            # Create drill schedule if none exists
            await self._ensure_drill_schedule(vessel_id, drill_type, created_by)
            
            # Broadcast update
            await self._broadcast_drill_update(drill, 'scheduled')
            
            return drill_id
            
        except Exception as e:
            logger.error(f"Failed to schedule drill: {e}")
            return None
    
    async def start_drill(self, drill_id: str, started_by: str) -> bool:
        """Start a scheduled drill"""
        try:
            drill = self.drills.get(drill_id)
            if not drill:
                logger.error(f"Drill {drill_id} not found")
                return False
            
            if drill.status != DrillStatus.SCHEDULED:
                logger.error(f"Drill {drill_id} cannot be started (status: {drill.status})")
                return False
            
            # Verify starter permissions
            starter = await self.crew_manager.get_crew_member(started_by)
            if not starter:
                return False
            
            # Must be drill master or have override permission
            if started_by != drill.drill_master:
                can_override = self.permission_manager.has_permission(
                    starter.role, Permission.OVERRIDE_ALARMS
                )
                if not can_override:
                    logger.error(f"User {started_by} cannot start drill")
                    return False
            
            # Update drill
            self._update_drill_indices(drill, add=False)
            drill.status = DrillStatus.IN_PROGRESS
            drill.actual_start = datetime.now(timezone.utc)
            self._update_drill_indices(drill, add=True)
            
            # Add note
            drill.notes.append({
                'type': 'started',
                'message': f"Drill started by {started_by}",
                'timestamp': drill.actual_start,
                'author': started_by
            })
            
            logger.info(f"Started drill {drill_id}")
            
            # Broadcast update
            await self._broadcast_drill_update(drill, 'started')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start drill: {e}")
            return False
    
    async def complete_drill(self, drill_id: str, completed_by: str,
                           participants: List[Dict[str, Any]],
                           drill_result: Dict[str, Any]) -> bool:
        """Complete a drill with results"""
        try:
            drill = self.drills.get(drill_id)
            if not drill:
                logger.error(f"Drill {drill_id} not found")
                return False
            
            if drill.status != DrillStatus.IN_PROGRESS:
                logger.error(f"Drill {drill_id} is not in progress")
                return False
            
            # Verify completer permissions
            completer = await self.crew_manager.get_crew_member(completed_by)
            if not completer:
                return False
            
            if completed_by != drill.drill_master:
                can_override = self.permission_manager.has_permission(
                    completer.role, Permission.OVERRIDE_ALARMS
                )
                if not can_override:
                    logger.error(f"User {completed_by} cannot complete drill")
                    return False
            
            # Process participants
            drill_participants = []
            for participant_data in participants:
                crew_id = participant_data['crew_member_id']
                crew_member = await self.crew_manager.get_crew_member(crew_id)
                if not crew_member:
                    continue
                
                participant = DrillParticipant(
                    crew_member_id=crew_id,
                    role=crew_member.role,
                    attended=participant_data.get('attended', True),
                    performance_rating=participant_data.get('performance_rating'),
                    notes=participant_data.get('notes'),
                    certification_status=participant_data.get('certification_status'),
                    special_responsibilities=participant_data.get('special_responsibilities', [])
                )
                
                drill_participants.append(participant)
            
            # Create drill result
            result = DrillResult(
                drill_id=drill_id,
                overall_rating=drill_result.get('overall_rating', 3),
                objectives_met=drill_result.get('objectives_met', []),
                objectives_failed=drill_result.get('objectives_failed', []),
                equipment_tested=drill_result.get('equipment_tested', {}),
                response_time_seconds=drill_result.get('response_time_seconds'),
                areas_for_improvement=drill_result.get('areas_for_improvement', []),
                safety_issues_identified=drill_result.get('safety_issues_identified', []),
                corrective_actions_required=drill_result.get('corrective_actions_required', []),
                evaluator_comments=drill_result.get('evaluator_comments'),
                weather_conditions=drill_result.get('weather_conditions'),
                sea_conditions=drill_result.get('sea_conditions')
            )
            
            # Update drill
            self._update_drill_indices(drill, add=False)
            drill.status = DrillStatus.COMPLETED
            drill.actual_end = datetime.now(timezone.utc)
            if drill.actual_start:
                drill.duration_minutes = int((drill.actual_end - drill.actual_start).total_seconds() / 60)
            drill.participants = drill_participants
            drill.drill_result = result
            drill.last_modified = datetime.now(timezone.utc)
            self._update_drill_indices(drill, add=True)
            
            # Check compliance
            compliance_met = self._check_drill_compliance(drill)
            drill.compliance_met = compliance_met
            
            # Update drill schedules
            await self._update_drill_schedule_completion(drill)
            
            # Update compliance records
            await self._update_compliance_records(drill)
            
            # Add completion note
            drill.notes.append({
                'type': 'completed',
                'message': f"Drill completed by {completed_by}. Rating: {result.overall_rating}/5",
                'timestamp': drill.actual_end,
                'author': completed_by
            })
            
            logger.info(f"Completed drill {drill_id} with rating {result.overall_rating}/5")
            
            # Broadcast update
            await self._broadcast_drill_update(drill, 'completed')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete drill: {e}")
            return False
    
    async def add_drill_note(self, drill_id: str, note: str, author_id: str) -> bool:
        """Add note to drill"""
        try:
            drill = self.drills.get(drill_id)
            if not drill:
                return False
            
            # Verify author permissions
            author = await self.crew_manager.get_crew_member(author_id)
            if not author:
                return False
            
            can_note = self.permission_manager.has_permission(
                author.role, Permission.CONDUCT_DRILLS
            )
            if not can_note:
                return False
            
            drill.notes.append({
                'type': 'note',
                'message': note,
                'timestamp': datetime.now(timezone.utc),
                'author': author_id
            })
            
            drill.last_modified = datetime.now(timezone.utc)
            
            logger.info(f"Added note to drill {drill_id}")
            
            # Broadcast update
            await self._broadcast_drill_update(drill, 'updated')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add drill note: {e}")
            return False
    
    def get_vessel_drills(self, vessel_id: str, 
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         drill_type: Optional[DrillType] = None) -> List[Dict[str, Any]]:
        """Get drills for vessel with optional filters"""
        vessel_drill_ids = self.drills_by_vessel.get(vessel_id, set())
        
        drills = []
        for drill_id in vessel_drill_ids:
            drill = self.drills.get(drill_id)
            if not drill:
                continue
            
            # Apply filters
            if start_date and drill.scheduled_date < start_date:
                continue
            if end_date and drill.scheduled_date > end_date:
                continue
            if drill_type and drill.drill_type != drill_type:
                continue
            
            drills.append(self._drill_to_dict(drill))
        
        # Sort by scheduled date (newest first)
        return sorted(drills, key=lambda x: x['scheduled_date'], reverse=True)
    
    def get_drill_compliance_status(self, vessel_id: str) -> Dict[str, Any]:
        """Get compliance status for vessel"""
        status = {
            'vessel_id': vessel_id,
            'overall_status': 'compliant',
            'requirements': {},
            'overdue_drills': [],
            'upcoming_drills': [],
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Check each requirement
        for req_id, requirement in self.safety_requirements.items():
            req_status = self._check_requirement_compliance(vessel_id, requirement)
            status['requirements'][req_id] = req_status
            
            if req_status['status'] == 'overdue':
                status['overall_status'] = 'non_compliant'
                status['overdue_drills'].append({
                    'drill_type': requirement.drill_type.value,
                    'requirement_name': requirement.name,
                    'days_overdue': req_status.get('days_overdue', 0)
                })
            elif req_status['status'] == 'due_soon':
                status['upcoming_drills'].append({
                    'drill_type': requirement.drill_type.value,
                    'requirement_name': requirement.name,
                    'days_until_due': req_status.get('days_until_due', 0)
                })
        
        return status
    
    def get_drill_statistics(self, vessel_id: Optional[str] = None,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get drill statistics"""
        if vessel_id:
            drill_ids = self.drills_by_vessel.get(vessel_id, set())
        else:
            drill_ids = set(self.drills.keys())
        
        stats = {
            'total_drills': 0,
            'by_type': {drill_type.value: 0 for drill_type in DrillType},
            'by_status': {status.value: 0 for status in DrillStatus},
            'average_rating': 0.0,
            'compliance_rate': 0.0,
            'overdue_requirements': 0,
            'safety_issues_identified': 0,
            'corrective_actions_required': 0
        }
        
        total_ratings = 0
        rating_count = 0
        compliant_drills = 0
        
        for drill_id in drill_ids:
            drill = self.drills.get(drill_id)
            if not drill:
                continue
            
            # Apply date filters
            if start_date and drill.scheduled_date < start_date:
                continue
            if end_date and drill.scheduled_date > end_date:
                continue
            
            stats['total_drills'] += 1
            stats['by_type'][drill.drill_type.value] += 1
            stats['by_status'][drill.status.value] += 1
            
            if drill.drill_result:
                total_ratings += drill.drill_result.overall_rating
                rating_count += 1
                
                stats['safety_issues_identified'] += len(drill.drill_result.safety_issues_identified)
                stats['corrective_actions_required'] += len(drill.drill_result.corrective_actions_required)
            
            if drill.compliance_met:
                compliant_drills += 1
        
        if rating_count > 0:
            stats['average_rating'] = total_ratings / rating_count
        
        if stats['total_drills'] > 0:
            stats['compliance_rate'] = (compliant_drills / stats['total_drills']) * 100
        
        return stats
    
    def _check_drill_compliance(self, drill: SafetyDrill) -> bool:
        """Check if drill meets compliance requirements"""
        # Find applicable requirement
        requirement = None
        for req in self.safety_requirements.values():
            if req.drill_type == drill.drill_type:
                requirement = req
                break
        
        if not requirement:
            return True  # No specific requirement found
        
        # Check minimum participants
        attendees = [p for p in drill.participants if p.attended]
        if len(attendees) < requirement.minimum_participants:
            return False
        
        # Check mandatory participants
        attendee_roles = {p.role for p in attendees}
        for required_role in requirement.mandatory_participants:
            if required_role not in attendee_roles:
                return False
        
        # Check overall rating (must be at least 3/5 for compliance)
        if drill.drill_result and drill.drill_result.overall_rating < 3:
            return False
        
        return True
    
    def _check_requirement_compliance(self, vessel_id: str, 
                                    requirement: SafetyRequirement) -> Dict[str, Any]:
        """Check compliance status for a specific requirement"""
        # Find most recent completed drill of this type
        vessel_drills = self.drills_by_vessel.get(vessel_id, set())
        type_drills = self.drills_by_type.get(requirement.drill_type, set())
        
        relevant_drills = vessel_drills.intersection(type_drills)
        
        last_compliant_drill = None
        last_drill_date = None
        
        for drill_id in relevant_drills:
            drill = self.drills.get(drill_id)
            if not drill or drill.status != DrillStatus.COMPLETED:
                continue
            
            if drill.compliance_met and drill.actual_end:
                if not last_drill_date or drill.actual_end > last_drill_date:
                    last_compliant_drill = drill
                    last_drill_date = drill.actual_end
        
        now = datetime.now(timezone.utc)
        
        if not last_drill_date:
            return {
                'requirement_id': requirement.requirement_id,
                'status': 'overdue',
                'last_compliant_date': None,
                'days_overdue': None,
                'next_due_date': None
            }
        
        # Calculate next due date
        next_due = last_drill_date + timedelta(days=requirement.frequency_days)
        
        if now > next_due:
            days_overdue = (now - next_due).days
            return {
                'requirement_id': requirement.requirement_id,
                'status': 'overdue',
                'last_compliant_date': last_drill_date.isoformat(),
                'days_overdue': days_overdue,
                'next_due_date': next_due.isoformat()
            }
        elif (next_due - now).days <= 7:  # Due within a week
            return {
                'requirement_id': requirement.requirement_id,
                'status': 'due_soon',
                'last_compliant_date': last_drill_date.isoformat(),
                'days_until_due': (next_due - now).days,
                'next_due_date': next_due.isoformat()
            }
        else:
            return {
                'requirement_id': requirement.requirement_id,
                'status': 'compliant',
                'last_compliant_date': last_drill_date.isoformat(),
                'next_due_date': next_due.isoformat()
            }
    
    async def _ensure_drill_schedule(self, vessel_id: str, drill_type: DrillType, 
                                   created_by: str) -> None:
        """Ensure drill schedule exists for vessel and drill type"""
        # Check if schedule already exists
        vessel_schedules = self.schedules_by_vessel.get(vessel_id, set())
        
        for schedule_id in vessel_schedules:
            schedule = self.drill_schedules.get(schedule_id)
            if schedule and schedule.drill_type == drill_type:
                return  # Schedule already exists
        
        # Find requirement for this drill type
        requirement = None
        for req in self.safety_requirements.values():
            if req.drill_type == drill_type:
                requirement = req
                break
        
        if not requirement:
            return  # No requirement found
        
        # Create schedule
        schedule_id = str(uuid.uuid4())
        schedule = DrillSchedule(
            schedule_id=schedule_id,
            vessel_id=vessel_id,
            drill_type=drill_type,
            frequency_days=requirement.frequency_days,
            next_due_date=datetime.now(timezone.utc) + timedelta(days=requirement.frequency_days),
            created_by=created_by
        )
        
        self.drill_schedules[schedule_id] = schedule
        self.schedules_by_vessel.setdefault(vessel_id, set()).add(schedule_id)
    
    async def _update_drill_schedule_completion(self, drill: SafetyDrill) -> None:
        """Update drill schedule when drill is completed"""
        if not drill.compliance_met or not drill.actual_end:
            return
        
        vessel_schedules = self.schedules_by_vessel.get(drill.vessel_id, set())
        
        for schedule_id in vessel_schedules:
            schedule = self.drill_schedules.get(schedule_id)
            if not schedule or schedule.drill_type != drill.drill_type:
                continue
            
            # Update schedule
            schedule.last_completed_drill_id = drill.drill_id
            schedule.last_completed_date = drill.actual_end
            schedule.next_due_date = drill.actual_end + timedelta(days=schedule.frequency_days)
            
            break
    
    async def _update_compliance_records(self, drill: SafetyDrill) -> None:
        """Update compliance records based on drill completion"""
        # Find relevant requirements
        for requirement in self.safety_requirements.values():
            if requirement.drill_type != drill.drill_type:
                continue
            
            # Update or create compliance record
            record_id = f"{drill.vessel_id}_{requirement.requirement_id}"
            
            if record_id in self.compliance_records:
                record = self.compliance_records[record_id]
            else:
                record = ComplianceRecord(
                    record_id=record_id,
                    vessel_id=drill.vessel_id,
                    regulation_type=requirement.regulatory_basis.split()[0],
                    requirement_name=requirement.name
                )
                self.compliance_records[record_id] = record
            
            if drill.compliance_met and drill.actual_end:
                record.last_satisfied_date = drill.actual_end
                record.next_due_date = drill.actual_end + timedelta(days=requirement.frequency_days)
                record.compliance_status = "compliant"
            
            record.related_drills.append(drill.drill_id)
    
    def _update_drill_indices(self, drill: SafetyDrill, add: bool = True) -> None:
        """Update drill indices for efficient querying"""
        if add:
            self.drills_by_vessel.setdefault(drill.vessel_id, set()).add(drill.drill_id)
            self.drills_by_type.setdefault(drill.drill_type, set()).add(drill.drill_id)
            self.drills_by_status.setdefault(drill.status, set()).add(drill.drill_id)
        else:
            if drill.vessel_id in self.drills_by_vessel:
                self.drills_by_vessel[drill.vessel_id].discard(drill.drill_id)
            if drill.drill_type in self.drills_by_type:
                self.drills_by_type[drill.drill_type].discard(drill.drill_id)
            if drill.status in self.drills_by_status:
                self.drills_by_status[drill.status].discard(drill.drill_id)
    
    def _drill_to_dict(self, drill: SafetyDrill) -> Dict[str, Any]:
        """Convert drill to dictionary"""
        return {
            'drill_id': drill.drill_id,
            'drill_type': drill.drill_type.value,
            'status': drill.status.value,
            'vessel_id': drill.vessel_id,
            'trip_id': drill.trip_id,
            'scheduled_date': drill.scheduled_date.isoformat(),
            'actual_start': drill.actual_start.isoformat() if drill.actual_start else None,
            'actual_end': drill.actual_end.isoformat() if drill.actual_end else None,
            'duration_minutes': drill.duration_minutes,
            'drill_master': drill.drill_master,
            'scenario_description': drill.scenario_description,
            'objectives': drill.objectives,
            'equipment_required': drill.equipment_required,
            'participants': [
                {
                    'crew_member_id': p.crew_member_id,
                    'role': p.role.value,
                    'attended': p.attended,
                    'performance_rating': p.performance_rating,
                    'notes': p.notes,
                    'certification_status': p.certification_status
                }
                for p in drill.participants
            ],
            'drill_result': {
                'overall_rating': drill.drill_result.overall_rating,
                'objectives_met': drill.drill_result.objectives_met,
                'objectives_failed': drill.drill_result.objectives_failed,
                'response_time_seconds': drill.drill_result.response_time_seconds,
                'areas_for_improvement': drill.drill_result.areas_for_improvement,
                'safety_issues_identified': drill.drill_result.safety_issues_identified,
                'corrective_actions_required': drill.drill_result.corrective_actions_required,
                'evaluator_comments': drill.drill_result.evaluator_comments
            } if drill.drill_result else None,
            'compliance_met': drill.compliance_met,
            'regulatory_compliance': drill.regulatory_compliance,
            'created_by': drill.created_by,
            'created_at': drill.created_at.isoformat(),
            'last_modified': drill.last_modified.isoformat(),
            'notes': [
                {
                    **note,
                    'timestamp': note['timestamp'].isoformat() if isinstance(note['timestamp'], datetime) else note['timestamp']
                }
                for note in drill.notes
            ]
        }
    
    async def _broadcast_drill_update(self, drill: SafetyDrill, action: str) -> None:
        """Broadcast drill update to connected clients"""
        message = {
            'type': 'drill_update',
            'action': action,
            'drill': self._drill_to_dict(drill)
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