"""
Crew Task Management System
Comprehensive task assignment, tracking, and completion system for crew operations
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


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """Task status states"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"
    BLOCKED = "blocked"


class TaskCategory(Enum):
    """Task categories"""
    SAFETY = "safety"
    MAINTENANCE = "maintenance"
    FISHING = "fishing"
    NAVIGATION = "navigation"
    DOCUMENTATION = "documentation"
    CLEANING = "cleaning"
    INVENTORY = "inventory"
    TRAINING = "training"
    INSPECTION = "inspection"
    EMERGENCY_DRILL = "emergency_drill"
    WATCH_DUTY = "watch_duty"
    GENERAL = "general"


@dataclass
class TaskDependency:
    """Task dependency relationship"""
    task_id: str
    depends_on_task_id: str
    dependency_type: str = "finish_to_start"  # finish_to_start, start_to_start, etc.
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TaskTemplate:
    """Reusable task template"""
    template_id: str
    title: str
    description: str
    category: TaskCategory
    priority: TaskPriority
    estimated_duration_minutes: Optional[int]
    required_roles: List[CrewRole]
    required_permissions: List[Permission]
    checklist_items: List[str] = field(default_factory=list)
    safety_requirements: List[str] = field(default_factory=list)
    tools_required: List[str] = field(default_factory=list)
    location: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Task:
    """Individual task"""
    task_id: str
    title: str
    description: str
    category: TaskCategory
    priority: TaskPriority
    status: TaskStatus
    vessel_id: str
    trip_id: Optional[str]
    
    # Assignment details
    created_by: str
    assigned_to: Optional[str] = None
    assigned_by: Optional[str] = None
    assigned_at: Optional[datetime] = None
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    due_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = None
    
    # Task details
    checklist_items: List[Dict[str, Any]] = field(default_factory=list)  # {item: str, completed: bool}
    progress_notes: List[Dict[str, Any]] = field(default_factory=list)  # {note: str, author: str, timestamp: datetime}
    attachments: List[str] = field(default_factory=list)  # file paths/URLs
    location: Optional[str] = None
    
    # Requirements
    required_roles: List[CrewRole] = field(default_factory=list)
    required_permissions: List[Permission] = field(default_factory=list)
    safety_requirements: List[str] = field(default_factory=list)
    tools_required: List[str] = field(default_factory=list)
    
    # Metadata
    template_id: Optional[str] = None
    recurring_pattern: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskAssignment:
    """Task assignment record"""
    assignment_id: str
    task_id: str
    assignee_id: str
    assigner_id: str
    assigned_at: datetime
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class RecurringTask:
    """Recurring task definition"""
    recurring_id: str
    template_id: str
    vessel_id: str
    pattern: str  # cron-like pattern or simple intervals
    next_due: datetime
    last_created: Optional[datetime] = None
    active: bool = True
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TaskManager:
    """Main task management system"""
    
    def __init__(self, crew_manager: CrewManager, permission_manager: PermissionManager):
        self.crew_manager = crew_manager
        self.permission_manager = permission_manager
        
        # Task storage
        self.tasks: Dict[str, Task] = {}
        self.task_assignments: Dict[str, TaskAssignment] = {}
        self.task_templates: Dict[str, TaskTemplate] = {}
        self.recurring_tasks: Dict[str, RecurringTask] = {}
        self.task_dependencies: Dict[str, List[TaskDependency]] = {}
        
        # Task indices for efficient querying
        self.tasks_by_assignee: Dict[str, Set[str]] = {}
        self.tasks_by_vessel: Dict[str, Set[str]] = {}
        self.tasks_by_status: Dict[TaskStatus, Set[str]] = {}
        self.tasks_by_category: Dict[TaskCategory, Set[str]] = {}
        
        # WebSocket connections for real-time updates
        self.websocket_connections: Dict[str, Any] = {}
        
        # Initialize default templates
        self._setup_default_templates()
        
        logger.info("Task Manager initialized")
    
    def _setup_default_templates(self) -> None:
        """Setup default task templates"""
        templates = [
            TaskTemplate(
                template_id="safety_drill_fire",
                title="Fire Safety Drill",
                description="Conduct fire safety drill with all crew members",
                category=TaskCategory.EMERGENCY_DRILL,
                priority=TaskPriority.HIGH,
                estimated_duration_minutes=30,
                required_roles=[CrewRole.CAPTAIN, CrewRole.FIRST_MATE],
                required_permissions=[Permission.CONDUCT_DRILLS],
                checklist_items=[
                    "Sound general alarm",
                    "Verify all crew at muster stations",
                    "Test fire suppression equipment",
                    "Review evacuation procedures",
                    "Document drill results"
                ],
                safety_requirements=[
                    "All crew must participate",
                    "Life jackets must be worn",
                    "Emergency equipment checked"
                ]
            ),
            TaskTemplate(
                template_id="engine_maintenance_daily",
                title="Daily Engine Maintenance Check",
                description="Daily inspection and maintenance of main engine",
                category=TaskCategory.MAINTENANCE,
                priority=TaskPriority.NORMAL,
                estimated_duration_minutes=45,
                required_roles=[CrewRole.ENGINEER, CrewRole.DECK_HAND],
                required_permissions=[Permission.MAINTAIN_EQUIPMENT],
                checklist_items=[
                    "Check oil levels",
                    "Inspect cooling system",
                    "Check fuel filters",
                    "Test alarm systems",
                    "Log readings"
                ],
                tools_required=[
                    "Oil dipstick",
                    "Thermometer",
                    "Pressure gauges",
                    "Logbook"
                ],
                location="Engine Room"
            ),
            TaskTemplate(
                template_id="deck_cleaning",
                title="Deck Cleaning and Maintenance",
                description="Clean and maintain deck areas",
                category=TaskCategory.CLEANING,
                priority=TaskPriority.LOW,
                estimated_duration_minutes=60,
                required_roles=[CrewRole.DECK_HAND],
                required_permissions=[],
                checklist_items=[
                    "Sweep and wash deck",
                    "Coil lines properly",
                    "Check deck equipment",
                    "Store loose items"
                ],
                tools_required=[
                    "Broom",
                    "Mop",
                    "Deck brush",
                    "Cleaning supplies"
                ]
            )
        ]
        
        for template in templates:
            self.task_templates[template.template_id] = template
    
    async def create_task(self, title: str, description: str, category: TaskCategory,
                         priority: TaskPriority, vessel_id: str, created_by: str,
                         template_id: Optional[str] = None, trip_id: Optional[str] = None,
                         due_date: Optional[datetime] = None,
                         estimated_duration: Optional[int] = None,
                         assigned_to: Optional[str] = None) -> Optional[str]:
        """Create a new task"""
        try:
            # Verify creator permissions
            creator = await self.crew_manager.get_crew_member(created_by)
            if not creator:
                logger.error(f"Creator {created_by} not found")
                return None
            
            can_create = self.permission_manager.has_permission(
                creator.role, Permission.ASSIGN_TASKS
            )
            if not can_create:
                logger.error(f"User {created_by} cannot create tasks")
                return None
            
            task_id = str(uuid.uuid4())
            
            # Start with template if provided
            task_data = {}
            if template_id and template_id in self.task_templates:
                template = self.task_templates[template_id]
                task_data = {
                    'checklist_items': [
                        {'item': item, 'completed': False} 
                        for item in template.checklist_items
                    ],
                    'required_roles': template.required_roles[:],
                    'required_permissions': template.required_permissions[:],
                    'safety_requirements': template.safety_requirements[:],
                    'tools_required': template.tools_required[:],
                    'location': template.location,
                    'estimated_duration_minutes': template.estimated_duration_minutes
                }
            
            # Override with provided values
            task = Task(
                task_id=task_id,
                title=title,
                description=description,
                category=category,
                priority=priority,
                status=TaskStatus.PENDING if not assigned_to else TaskStatus.ASSIGNED,
                vessel_id=vessel_id,
                trip_id=trip_id,
                created_by=created_by,
                due_date=due_date,
                estimated_duration_minutes=estimated_duration or task_data.get('estimated_duration_minutes'),
                template_id=template_id,
                **{k: v for k, v in task_data.items() if k != 'estimated_duration_minutes'}
            )
            
            # Auto-assign if specified
            if assigned_to:
                assignment_result = await self._assign_task_internal(
                    task, assigned_to, created_by
                )
                if not assignment_result:
                    logger.warning(f"Failed to assign task {task_id} to {assigned_to}")
            
            # Store task
            self.tasks[task_id] = task
            self._update_task_indices(task, add=True)
            
            logger.info(f"Created task {task_id}: {title}")
            
            # Broadcast update
            await self._broadcast_task_update(task, 'created')
            
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return None
    
    async def assign_task(self, task_id: str, assignee_id: str, 
                         assigner_id: str, notes: Optional[str] = None) -> bool:
        """Assign task to crew member"""
        try:
            task = self.tasks.get(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            # Verify assigner permissions
            assigner = await self.crew_manager.get_crew_member(assigner_id)
            if not assigner:
                return False
            
            can_assign = self.permission_manager.has_permission(
                assigner.role, Permission.ASSIGN_TASKS
            )
            if not can_assign:
                logger.error(f"User {assigner_id} cannot assign tasks")
                return False
            
            return await self._assign_task_internal(task, assignee_id, assigner_id, notes)
            
        except Exception as e:
            logger.error(f"Failed to assign task: {e}")
            return False
    
    async def _assign_task_internal(self, task: Task, assignee_id: str, 
                                   assigner_id: str, notes: Optional[str] = None) -> bool:
        """Internal task assignment logic"""
        try:
            # Verify assignee exists and can perform task
            assignee = await self.crew_manager.get_crew_member(assignee_id)
            if not assignee:
                logger.error(f"Assignee {assignee_id} not found")
                return False
            
            # Check role requirements
            if task.required_roles and assignee.role not in task.required_roles:
                logger.error(f"Assignee role {assignee.role} not in required roles")
                return False
            
            # Check permission requirements
            for permission in task.required_permissions:
                if not self.permission_manager.has_permission(assignee.role, permission):
                    logger.error(f"Assignee lacks required permission {permission}")
                    return False
            
            # Create assignment record
            assignment_id = str(uuid.uuid4())
            assignment = TaskAssignment(
                assignment_id=assignment_id,
                task_id=task.task_id,
                assignee_id=assignee_id,
                assigner_id=assigner_id,
                assigned_at=datetime.now(timezone.utc),
                notes=notes
            )
            
            # Update task
            self._update_task_indices(task, add=False)
            task.assigned_to = assignee_id
            task.assigned_by = assigner_id
            task.assigned_at = assignment.assigned_at
            task.status = TaskStatus.ASSIGNED
            self._update_task_indices(task, add=True)
            
            # Store assignment
            self.task_assignments[assignment_id] = assignment
            
            logger.info(f"Assigned task {task.task_id} to {assignee_id}")
            
            # Broadcast update
            await self._broadcast_task_update(task, 'assigned')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign task internally: {e}")
            return False
    
    async def start_task(self, task_id: str, user_id: str) -> bool:
        """Start working on a task"""
        try:
            task = self.tasks.get(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            # Verify user can start task
            if task.assigned_to != user_id:
                # Check if user has override permission
                user = await self.crew_manager.get_crew_member(user_id)
                if not user:
                    return False
                
                can_override = self.permission_manager.has_permission(
                    user.role, Permission.OVERRIDE_ALARMS  # Using this as general override
                )
                if not can_override:
                    logger.error(f"User {user_id} cannot start unassigned task")
                    return False
            
            if task.status not in [TaskStatus.ASSIGNED, TaskStatus.PENDING]:
                logger.error(f"Task {task_id} cannot be started (status: {task.status})")
                return False
            
            # Update task
            self._update_task_indices(task, add=False)
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now(timezone.utc)
            if not task.assigned_to:
                task.assigned_to = user_id
                task.assigned_at = task.started_at
            self._update_task_indices(task, add=True)
            
            logger.info(f"Started task {task_id}")
            
            # Broadcast update
            await self._broadcast_task_update(task, 'started')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start task: {e}")
            return False
    
    async def complete_task(self, task_id: str, user_id: str, 
                           completion_notes: Optional[str] = None) -> bool:
        """Complete a task"""
        try:
            task = self.tasks.get(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            # Verify user can complete task
            if task.assigned_to != user_id:
                user = await self.crew_manager.get_crew_member(user_id)
                if not user:
                    return False
                
                can_override = self.permission_manager.has_permission(
                    user.role, Permission.OVERRIDE_ALARMS
                )
                if not can_override:
                    logger.error(f"User {user_id} cannot complete task")
                    return False
            
            if task.status != TaskStatus.IN_PROGRESS:
                logger.error(f"Task {task_id} is not in progress")
                return False
            
            # Update task
            self._update_task_indices(task, add=False)
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            
            if completion_notes:
                task.progress_notes.append({
                    'note': completion_notes,
                    'author': user_id,
                    'timestamp': task.completed_at,
                    'type': 'completion'
                })
            
            self._update_task_indices(task, add=True)
            
            logger.info(f"Completed task {task_id}")
            
            # Check for dependent tasks
            await self._check_task_dependencies(task_id)
            
            # Broadcast update
            await self._broadcast_task_update(task, 'completed')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete task: {e}")
            return False
    
    async def add_progress_note(self, task_id: str, user_id: str, note: str) -> bool:
        """Add progress note to task"""
        try:
            task = self.tasks.get(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            # Verify user can add notes
            if task.assigned_to != user_id:
                user = await self.crew_manager.get_crew_member(user_id)
                if not user or not self.permission_manager.has_permission(
                    user.role, Permission.ASSIGN_TASKS
                ):
                    logger.error(f"User {user_id} cannot add progress notes")
                    return False
            
            task.progress_notes.append({
                'note': note,
                'author': user_id,
                'timestamp': datetime.now(timezone.utc),
                'type': 'progress'
            })
            
            logger.info(f"Added progress note to task {task_id}")
            
            # Broadcast update
            await self._broadcast_task_update(task, 'updated')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add progress note: {e}")
            return False
    
    async def update_checklist_item(self, task_id: str, user_id: str, 
                                   item_index: int, completed: bool) -> bool:
        """Update checklist item status"""
        try:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if item_index >= len(task.checklist_items):
                return False
            
            # Verify permissions
            if task.assigned_to != user_id:
                user = await self.crew_manager.get_crew_member(user_id)
                if not user or not self.permission_manager.has_permission(
                    user.role, Permission.ASSIGN_TASKS
                ):
                    return False
            
            task.checklist_items[item_index]['completed'] = completed
            
            # Add progress note
            action = "completed" if completed else "unchecked"
            item_text = task.checklist_items[item_index]['item']
            task.progress_notes.append({
                'note': f"Checklist item {action}: {item_text}",
                'author': user_id,
                'timestamp': datetime.now(timezone.utc),
                'type': 'checklist'
            })
            
            # Broadcast update
            await self._broadcast_task_update(task, 'updated')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update checklist: {e}")
            return False
    
    def get_tasks_for_user(self, user_id: str, status_filter: Optional[List[TaskStatus]] = None) -> List[Dict[str, Any]]:
        """Get tasks assigned to a user"""
        user_tasks = self.tasks_by_assignee.get(user_id, set())
        
        tasks = []
        for task_id in user_tasks:
            task = self.tasks.get(task_id)
            if not task:
                continue
            
            if status_filter and task.status not in status_filter:
                continue
            
            tasks.append(self._task_to_dict(task))
        
        # Sort by priority and due date
        return sorted(tasks, key=lambda x: (
            -self._priority_weight(TaskPriority(x['priority'])),
            x['due_date'] or '9999-12-31'
        ))
    
    def get_tasks_for_vessel(self, vessel_id: str, status_filter: Optional[List[TaskStatus]] = None) -> List[Dict[str, Any]]:
        """Get all tasks for a vessel"""
        vessel_tasks = self.tasks_by_vessel.get(vessel_id, set())
        
        tasks = []
        for task_id in vessel_tasks:
            task = self.tasks.get(task_id)
            if not task:
                continue
            
            if status_filter and task.status not in status_filter:
                continue
            
            tasks.append(self._task_to_dict(task))
        
        return sorted(tasks, key=lambda x: (
            -self._priority_weight(TaskPriority(x['priority'])),
            x['created_at']
        ))
    
    def get_task_statistics(self, vessel_id: Optional[str] = None) -> Dict[str, Any]:
        """Get task statistics"""
        if vessel_id:
            task_ids = self.tasks_by_vessel.get(vessel_id, set())
        else:
            task_ids = set(self.tasks.keys())
        
        stats = {
            'total': len(task_ids),
            'by_status': {status.value: 0 for status in TaskStatus},
            'by_priority': {priority.value: 0 for priority in TaskPriority},
            'by_category': {category.value: 0 for category in TaskCategory},
            'overdue': 0,
            'due_today': 0,
            'due_this_week': 0
        }
        
        now = datetime.now(timezone.utc)
        today = now.date()
        week_end = now + timedelta(days=7)
        
        for task_id in task_ids:
            task = self.tasks.get(task_id)
            if not task:
                continue
            
            stats['by_status'][task.status.value] += 1
            stats['by_priority'][task.priority.value] += 1
            stats['by_category'][task.category.value] += 1
            
            if task.due_date:
                due_date = task.due_date.date() if hasattr(task.due_date, 'date') else task.due_date
                
                if due_date < today and task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                    stats['overdue'] += 1
                elif due_date == today:
                    stats['due_today'] += 1
                elif due_date <= week_end.date():
                    stats['due_this_week'] += 1
        
        return stats
    
    async def create_recurring_task(self, template_id: str, vessel_id: str, 
                                   pattern: str, created_by: str) -> Optional[str]:
        """Create recurring task pattern"""
        try:
            if template_id not in self.task_templates:
                logger.error(f"Template {template_id} not found")
                return None
            
            recurring_id = str(uuid.uuid4())
            next_due = self._calculate_next_due(pattern)
            
            recurring_task = RecurringTask(
                recurring_id=recurring_id,
                template_id=template_id,
                vessel_id=vessel_id,
                pattern=pattern,
                next_due=next_due,
                created_by=created_by
            )
            
            self.recurring_tasks[recurring_id] = recurring_task
            
            logger.info(f"Created recurring task {recurring_id}")
            return recurring_id
            
        except Exception as e:
            logger.error(f"Failed to create recurring task: {e}")
            return None
    
    async def process_recurring_tasks(self) -> None:
        """Process due recurring tasks"""
        now = datetime.now(timezone.utc)
        
        for recurring_task in self.recurring_tasks.values():
            if not recurring_task.active or recurring_task.next_due > now:
                continue
            
            template = self.task_templates.get(recurring_task.template_id)
            if not template:
                continue
            
            # Create new task from template
            task_id = await self.create_task(
                title=template.title,
                description=template.description,
                category=template.category,
                priority=template.priority,
                vessel_id=recurring_task.vessel_id,
                created_by=recurring_task.created_by,
                template_id=template.template_id,
                due_date=now + timedelta(hours=24)  # Default 24 hour due date
            )
            
            if task_id:
                # Update recurring task
                recurring_task.last_created = now
                recurring_task.next_due = self._calculate_next_due(recurring_task.pattern, now)
                
                logger.info(f"Created recurring task instance {task_id} from {recurring_task.recurring_id}")
    
    def _calculate_next_due(self, pattern: str, from_time: Optional[datetime] = None) -> datetime:
        """Calculate next due date from pattern"""
        if not from_time:
            from_time = datetime.now(timezone.utc)
        
        # Simple patterns for now - could extend with cron-like syntax
        if pattern == "daily":
            return from_time + timedelta(days=1)
        elif pattern == "weekly":
            return from_time + timedelta(weeks=1)
        elif pattern == "monthly":
            return from_time + timedelta(days=30)
        else:
            # Default to daily
            return from_time + timedelta(days=1)
    
    async def _check_task_dependencies(self, completed_task_id: str) -> None:
        """Check and update dependent tasks"""
        # Find tasks that depend on this completed task
        for task_id, dependencies in self.task_dependencies.items():
            for dep in dependencies:
                if dep.depends_on_task_id == completed_task_id:
                    dependent_task = self.tasks.get(task_id)
                    if dependent_task and dependent_task.status == TaskStatus.BLOCKED:
                        # Check if all dependencies are complete
                        all_complete = True
                        for task_dep in dependencies:
                            dep_task = self.tasks.get(task_dep.depends_on_task_id)
                            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                                all_complete = False
                                break
                        
                        if all_complete:
                            self._update_task_indices(dependent_task, add=False)
                            dependent_task.status = TaskStatus.PENDING
                            self._update_task_indices(dependent_task, add=True)
                            
                            await self._broadcast_task_update(dependent_task, 'unblocked')
    
    def _update_task_indices(self, task: Task, add: bool = True) -> None:
        """Update task indices for efficient querying"""
        if add:
            # Add to indices
            if task.assigned_to:
                self.tasks_by_assignee.setdefault(task.assigned_to, set()).add(task.task_id)
            self.tasks_by_vessel.setdefault(task.vessel_id, set()).add(task.task_id)
            self.tasks_by_status.setdefault(task.status, set()).add(task.task_id)
            self.tasks_by_category.setdefault(task.category, set()).add(task.task_id)
        else:
            # Remove from indices
            if task.assigned_to and task.assigned_to in self.tasks_by_assignee:
                self.tasks_by_assignee[task.assigned_to].discard(task.task_id)
            if task.vessel_id in self.tasks_by_vessel:
                self.tasks_by_vessel[task.vessel_id].discard(task.task_id)
            if task.status in self.tasks_by_status:
                self.tasks_by_status[task.status].discard(task.task_id)
            if task.category in self.tasks_by_category:
                self.tasks_by_category[task.category].discard(task.task_id)
    
    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            'task_id': task.task_id,
            'title': task.title,
            'description': task.description,
            'category': task.category.value,
            'priority': task.priority.value,
            'status': task.status.value,
            'vessel_id': task.vessel_id,
            'trip_id': task.trip_id,
            'created_by': task.created_by,
            'assigned_to': task.assigned_to,
            'assigned_by': task.assigned_by,
            'created_at': task.created_at.isoformat(),
            'assigned_at': task.assigned_at.isoformat() if task.assigned_at else None,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'estimated_duration_minutes': task.estimated_duration_minutes,
            'checklist_items': task.checklist_items,
            'progress_notes': [
                {
                    **note,
                    'timestamp': note['timestamp'].isoformat() if isinstance(note['timestamp'], datetime) else note['timestamp']
                }
                for note in task.progress_notes
            ],
            'location': task.location,
            'tools_required': task.tools_required,
            'safety_requirements': task.safety_requirements,
            'template_id': task.template_id,
            'metadata': task.metadata
        }
    
    def _priority_weight(self, priority: TaskPriority) -> int:
        """Get numeric weight for priority sorting"""
        weights = {
            TaskPriority.CRITICAL: 5,
            TaskPriority.URGENT: 4,
            TaskPriority.HIGH: 3,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 1
        }
        return weights.get(priority, 0)
    
    async def _broadcast_task_update(self, task: Task, action: str) -> None:
        """Broadcast task update to connected clients"""
        message = {
            'type': 'task_update',
            'action': action,
            'task': self._task_to_dict(task)
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