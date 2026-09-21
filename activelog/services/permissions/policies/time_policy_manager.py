"""
Time-based Permission Policy Manager
Handles time-based permissions with expiration, scheduling, and temporal restrictions
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import calendar

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimeRestrictionType(Enum):
    """Types of time restrictions"""
    DAILY_SCHEDULE = "daily_schedule"
    WEEKLY_SCHEDULE = "weekly_schedule"
    DATE_RANGE = "date_range"
    BUSINESS_HOURS = "business_hours"
    MAINTENANCE_WINDOW = "maintenance_window"
    EMERGENCY_HOURS = "emergency_hours"
    ABSOLUTE_EXPIRY = "absolute_expiry"


class RecurrencePattern(Enum):
    """Recurrence patterns for scheduled permissions"""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    WEEKDAYS = "weekdays"
    WEEKENDS = "weekends"
    CUSTOM = "custom"


@dataclass
class TimeWindow:
    """Defines a time window with start and end times"""
    start_time: time
    end_time: time
    days_of_week: List[int]  # 0=Monday, 6=Sunday
    timezone: str


@dataclass
class ScheduledPermission:
    """Permission that is active during specific time periods"""
    schedule_id: str
    permission_grant_id: str
    user_id: str
    resource_id: str
    restriction_type: TimeRestrictionType
    recurrence: RecurrencePattern
    time_windows: List[TimeWindow]
    start_date: datetime
    end_date: Optional[datetime]
    is_active: bool
    created_by: str
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class DeviceRestriction:
    """Device-specific permission restrictions"""
    restriction_id: str
    user_id: str
    device_id: str
    device_type: str
    device_name: str
    allowed_resources: List[str]
    blocked_resources: List[str]
    time_restrictions: List[TimeWindow]
    location_restrictions: List[str]
    is_trusted_device: bool
    requires_additional_auth: bool
    max_session_duration: int
    created_at: datetime
    last_used: Optional[datetime]
    metadata: Dict[str, Any]


class TimePolicyManager:
    """Manages time-based permissions and device restrictions"""
    
    def __init__(self, data_dir: str = "time_policies"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # In-memory storage
        self.scheduled_permissions: Dict[str, ScheduledPermission] = {}
        self.device_restrictions: Dict[str, DeviceRestriction] = {}
        
        # Background task for permission scheduling
        self.scheduler_running = False
        self.check_interval = 60  # Check every minute
        
        # Default business hours
        self.default_business_hours = {
            "start_time": time(9, 0),
            "end_time": time(17, 0),
            "days_of_week": [0, 1, 2, 3, 4],  # Monday to Friday
            "timezone": "UTC"
        }
        
        logger.info("TimePolicyManager initialized")
    
    async def start_scheduler(self):
        """Start the background permission scheduler"""
        if self.scheduler_running:
            return
        
        self.scheduler_running = True
        asyncio.create_task(self._scheduler_loop())
        logger.info("Permission scheduler started")
    
    async def stop_scheduler(self):
        """Stop the background permission scheduler"""
        self.scheduler_running = False
        logger.info("Permission scheduler stopped")
    
    async def _scheduler_loop(self):
        """Background loop for checking and updating scheduled permissions"""
        while self.scheduler_running:
            try:
                await self._check_scheduled_permissions()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_scheduled_permissions(self):
        """Check and update scheduled permissions"""
        try:
            current_time = datetime.now(timezone.utc)
            
            for schedule_id, scheduled_perm in self.scheduled_permissions.items():
                try:
                    should_be_active = await self._should_permission_be_active(
                        scheduled_perm, current_time
                    )
                    
                    if should_be_active != scheduled_perm.is_active:
                        scheduled_perm.is_active = should_be_active
                        
                        # Log the state change
                        action = "activated" if should_be_active else "deactivated"
                        logger.info(f"Scheduled permission {schedule_id} {action}")
                        
                        # Notify permission manager (would integrate with main system)
                        await self._notify_permission_state_change(
                            scheduled_perm, should_be_active
                        )
                        
                except Exception as e:
                    logger.error(f"Error processing scheduled permission {schedule_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error checking scheduled permissions: {e}")
    
    async def _should_permission_be_active(
        self, 
        scheduled_perm: ScheduledPermission,
        current_time: datetime
    ) -> bool:
        """Determine if a scheduled permission should be active at given time"""
        try:
            # Check if within overall date range
            if current_time < scheduled_perm.start_date:
                return False
            
            if scheduled_perm.end_date and current_time > scheduled_perm.end_date:
                return False
            
            # Check recurrence pattern
            if scheduled_perm.recurrence == RecurrencePattern.ONCE:
                # For one-time permissions, check if we're within any time window today
                return await self._is_within_time_windows(
                    scheduled_perm.time_windows, current_time
                )
            
            elif scheduled_perm.recurrence == RecurrencePattern.DAILY:
                return await self._is_within_time_windows(
                    scheduled_perm.time_windows, current_time
                )
            
            elif scheduled_perm.recurrence == RecurrencePattern.WEEKLY:
                # Check if current day of week matches
                current_weekday = current_time.weekday()
                for window in scheduled_perm.time_windows:
                    if current_weekday in window.days_of_week:
                        if await self._is_within_time_window(window, current_time):
                            return True
                return False
            
            elif scheduled_perm.recurrence == RecurrencePattern.WEEKDAYS:
                current_weekday = current_time.weekday()
                if 0 <= current_weekday <= 4:  # Monday to Friday
                    return await self._is_within_time_windows(
                        scheduled_perm.time_windows, current_time
                    )
                return False
            
            elif scheduled_perm.recurrence == RecurrencePattern.WEEKENDS:
                current_weekday = current_time.weekday()
                if current_weekday >= 5:  # Saturday and Sunday
                    return await self._is_within_time_windows(
                        scheduled_perm.time_windows, current_time
                    )
                return False
            
            elif scheduled_perm.recurrence == RecurrencePattern.MONTHLY:
                # Check if we're on the same day of month as start date
                if current_time.day == scheduled_perm.start_date.day:
                    return await self._is_within_time_windows(
                        scheduled_perm.time_windows, current_time
                    )
                return False
            
            else:  # CUSTOM or unknown
                return await self._is_within_time_windows(
                    scheduled_perm.time_windows, current_time
                )
                
        except Exception as e:
            logger.error(f"Error determining permission active state: {e}")
            return False
    
    async def _is_within_time_windows(
        self,
        time_windows: List[TimeWindow],
        current_time: datetime
    ) -> bool:
        """Check if current time is within any of the time windows"""
        for window in time_windows:
            if await self._is_within_time_window(window, current_time):
                return True
        return False
    
    async def _is_within_time_window(
        self,
        window: TimeWindow,
        current_time: datetime
    ) -> bool:
        """Check if current time is within a specific time window"""
        try:
            # Convert current time to window timezone if needed
            # (Simplified - in production would use proper timezone handling)
            current_weekday = current_time.weekday()
            
            # Check if current day is allowed
            if window.days_of_week and current_weekday not in window.days_of_week:
                return False
            
            # Check time range
            current_time_only = current_time.time()
            
            # Handle overnight windows (e.g., 22:00 to 06:00)
            if window.start_time > window.end_time:
                return (current_time_only >= window.start_time or 
                       current_time_only <= window.end_time)
            else:
                return (window.start_time <= current_time_only <= window.end_time)
                
        except Exception as e:
            logger.error(f"Error checking time window: {e}")
            return False
    
    async def _notify_permission_state_change(
        self,
        scheduled_perm: ScheduledPermission,
        is_active: bool
    ):
        """Notify the main permission system of state changes"""
        # This would integrate with the main PermissionManager
        logger.info(
            f"Permission state change: {scheduled_perm.permission_grant_id} "
            f"{'activated' if is_active else 'deactivated'}"
        )
    
    async def create_scheduled_permission(
        self,
        permission_grant_id: str,
        user_id: str,
        resource_id: str,
        restriction_type: TimeRestrictionType,
        recurrence: RecurrencePattern,
        time_windows: List[TimeWindow],
        start_date: datetime,
        end_date: Optional[datetime] = None,
        created_by: str = "system"
    ) -> str:
        """Create a new scheduled permission"""
        try:
            schedule_id = f"sched_{len(self.scheduled_permissions)}_{int(datetime.now().timestamp())}"
            
            scheduled_perm = ScheduledPermission(
                schedule_id=schedule_id,
                permission_grant_id=permission_grant_id,
                user_id=user_id,
                resource_id=resource_id,
                restriction_type=restriction_type,
                recurrence=recurrence,
                time_windows=time_windows,
                start_date=start_date,
                end_date=end_date,
                is_active=False,  # Will be determined by scheduler
                created_by=created_by,
                created_at=datetime.now(timezone.utc),
                metadata={}
            )
            
            self.scheduled_permissions[schedule_id] = scheduled_perm
            
            # Immediately check if it should be active
            current_time = datetime.now(timezone.utc)
            scheduled_perm.is_active = await self._should_permission_be_active(
                scheduled_perm, current_time
            )
            
            await self.save_data()
            
            logger.info(f"Created scheduled permission {schedule_id}")
            return schedule_id
            
        except Exception as e:
            logger.error(f"Error creating scheduled permission: {e}")
            raise
    
    async def create_device_restriction(
        self,
        user_id: str,
        device_id: str,
        device_type: str,
        device_name: str,
        allowed_resources: Optional[List[str]] = None,
        blocked_resources: Optional[List[str]] = None,
        time_restrictions: Optional[List[TimeWindow]] = None,
        location_restrictions: Optional[List[str]] = None,
        is_trusted_device: bool = False,
        requires_additional_auth: bool = False,
        max_session_duration: int = 28800  # 8 hours default
    ) -> str:
        """Create a new device restriction"""
        try:
            restriction_id = f"dev_{len(self.device_restrictions)}_{int(datetime.now().timestamp())}"
            
            device_restriction = DeviceRestriction(
                restriction_id=restriction_id,
                user_id=user_id,
                device_id=device_id,
                device_type=device_type,
                device_name=device_name,
                allowed_resources=allowed_resources or [],
                blocked_resources=blocked_resources or [],
                time_restrictions=time_restrictions or [],
                location_restrictions=location_restrictions or [],
                is_trusted_device=is_trusted_device,
                requires_additional_auth=requires_additional_auth,
                max_session_duration=max_session_duration,
                created_at=datetime.now(timezone.utc),
                last_used=None,
                metadata={}
            )
            
            self.device_restrictions[restriction_id] = device_restriction
            await self.save_data()
            
            logger.info(f"Created device restriction {restriction_id}")
            return restriction_id
            
        except Exception as e:
            logger.error(f"Error creating device restriction: {e}")
            raise
    
    async def check_device_access(
        self,
        user_id: str,
        device_id: str,
        resource_id: str,
        current_time: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """Check if device access is allowed for user and resource"""
        try:
            if not current_time:
                current_time = datetime.now(timezone.utc)
            
            # Find device restrictions for this user and device
            user_device_restrictions = [
                restriction for restriction in self.device_restrictions.values()
                if restriction.user_id == user_id and restriction.device_id == device_id
            ]
            
            if not user_device_restrictions:
                # No specific restrictions, allow access
                return True, "No device restrictions found"
            
            for restriction in user_device_restrictions:
                # Check if resource is explicitly blocked
                if resource_id in restriction.blocked_resources:
                    return False, f"Resource {resource_id} is blocked for device {device_id}"
                
                # Check if resource is in allowed list (if allowed list exists)
                if restriction.allowed_resources and resource_id not in restriction.allowed_resources:
                    return False, f"Resource {resource_id} not in allowed list for device {device_id}"
                
                # Check time restrictions
                if restriction.time_restrictions:
                    time_allowed = await self._is_within_time_windows(
                        restriction.time_restrictions, current_time
                    )
                    if not time_allowed:
                        return False, f"Device {device_id} not allowed at current time"
                
                # Update last used timestamp
                restriction.last_used = current_time
            
            return True, "Device access allowed"
            
        except Exception as e:
            logger.error(f"Error checking device access: {e}")
            return False, f"Device access check failed: {str(e)}"
    
    async def create_business_hours_restriction(
        self,
        user_id: str,
        resource_id: str,
        permission_grant_id: str,
        start_time: time = None,
        end_time: time = None,
        days_of_week: List[int] = None,
        timezone_str: str = "UTC"
    ) -> str:
        """Create a business hours time restriction"""
        start_time = start_time or self.default_business_hours["start_time"]
        end_time = end_time or self.default_business_hours["end_time"]
        days_of_week = days_of_week or self.default_business_hours["days_of_week"]
        
        time_window = TimeWindow(
            start_time=start_time,
            end_time=end_time,
            days_of_week=days_of_week,
            timezone=timezone_str
        )
        
        return await self.create_scheduled_permission(
            permission_grant_id=permission_grant_id,
            user_id=user_id,
            resource_id=resource_id,
            restriction_type=TimeRestrictionType.BUSINESS_HOURS,
            recurrence=RecurrencePattern.WEEKDAYS,
            time_windows=[time_window],
            start_date=datetime.now(timezone.utc),
            end_date=None
        )
    
    async def create_maintenance_window(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
        recurrence: RecurrencePattern = RecurrencePattern.ONCE,
        affected_users: Optional[List[str]] = None
    ) -> List[str]:
        """Create maintenance window that blocks access during specified times"""
        try:
            created_schedules = []
            
            # Convert to time window
            duration = end_time - start_time
            time_window = TimeWindow(
                start_time=start_time.time(),
                end_time=end_time.time(),
                days_of_week=list(range(7)) if recurrence != RecurrencePattern.ONCE else [start_time.weekday()],
                timezone="UTC"
            )
            
            # Create blocked schedules for affected users
            users_to_block = affected_users or []  # In real system, would query all users with access
            
            for user_id in users_to_block:
                schedule_id = await self.create_scheduled_permission(
                    permission_grant_id=f"maintenance_block_{user_id}_{resource_id}",
                    user_id=user_id,
                    resource_id=resource_id,
                    restriction_type=TimeRestrictionType.MAINTENANCE_WINDOW,
                    recurrence=recurrence,
                    time_windows=[time_window],
                    start_date=start_time,
                    end_date=end_time if recurrence == RecurrencePattern.ONCE else None
                )
                created_schedules.append(schedule_id)
            
            logger.info(f"Created maintenance window for {len(users_to_block)} users")
            return created_schedules
            
        except Exception as e:
            logger.error(f"Error creating maintenance window: {e}")
            raise
    
    async def get_active_permissions(self, user_id: str) -> List[ScheduledPermission]:
        """Get all currently active scheduled permissions for a user"""
        active_permissions = []
        current_time = datetime.now(timezone.utc)
        
        for scheduled_perm in self.scheduled_permissions.values():
            if (scheduled_perm.user_id == user_id and 
                scheduled_perm.is_active and
                await self._should_permission_be_active(scheduled_perm, current_time)):
                active_permissions.append(scheduled_perm)
        
        return active_permissions
    
    async def get_upcoming_expirations(self, days_ahead: int = 7) -> List[ScheduledPermission]:
        """Get permissions that will expire in the specified number of days"""
        expiring_permissions = []
        cutoff_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)
        
        for scheduled_perm in self.scheduled_permissions.values():
            if (scheduled_perm.end_date and 
                scheduled_perm.end_date <= cutoff_date and
                scheduled_perm.is_active):
                expiring_permissions.append(scheduled_perm)
        
        return expiring_permissions
    
    async def load_data(self):
        """Load time policies data from disk"""
        try:
            # Load scheduled permissions
            sched_file = self.data_dir / "scheduled_permissions.json"
            if sched_file.exists():
                with open(sched_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        # Convert datetime strings back to datetime objects
                        item["start_date"] = datetime.fromisoformat(item["start_date"])
                        item["created_at"] = datetime.fromisoformat(item["created_at"])
                        if item["end_date"]:
                            item["end_date"] = datetime.fromisoformat(item["end_date"])
                        
                        # Convert time window time strings back to time objects
                        for window in item["time_windows"]:
                            window["start_time"] = datetime.strptime(window["start_time"], "%H:%M:%S").time()
                            window["end_time"] = datetime.strptime(window["end_time"], "%H:%M:%S").time()
                        
                        # Convert enums
                        item["restriction_type"] = TimeRestrictionType(item["restriction_type"])
                        item["recurrence"] = RecurrencePattern(item["recurrence"])
                        
                        scheduled_perm = ScheduledPermission(**item)
                        self.scheduled_permissions[scheduled_perm.schedule_id] = scheduled_perm
            
            # Load device restrictions
            device_file = self.data_dir / "device_restrictions.json"
            if device_file.exists():
                with open(device_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        # Convert datetime strings
                        item["created_at"] = datetime.fromisoformat(item["created_at"])
                        if item["last_used"]:
                            item["last_used"] = datetime.fromisoformat(item["last_used"])
                        
                        # Convert time restrictions
                        for window in item.get("time_restrictions", []):
                            window["start_time"] = datetime.strptime(window["start_time"], "%H:%M:%S").time()
                            window["end_time"] = datetime.strptime(window["end_time"], "%H:%M:%S").time()
                        
                        device_restriction = DeviceRestriction(**item)
                        self.device_restrictions[device_restriction.restriction_id] = device_restriction
            
            logger.info("Loaded time policies data from disk")
            
        except Exception as e:
            logger.error(f"Error loading time policies data: {e}")
    
    async def save_data(self):
        """Save time policies data to disk"""
        try:
            # Save scheduled permissions
            sched_file = self.data_dir / "scheduled_permissions.json"
            with open(sched_file, 'w') as f:
                data = []
                for scheduled_perm in self.scheduled_permissions.values():
                    item = asdict(scheduled_perm)
                    # Convert datetime objects to strings
                    item["start_date"] = scheduled_perm.start_date.isoformat()
                    item["created_at"] = scheduled_perm.created_at.isoformat()
                    if scheduled_perm.end_date:
                        item["end_date"] = scheduled_perm.end_date.isoformat()
                    
                    # Convert time objects to strings
                    for window in item["time_windows"]:
                        window["start_time"] = window["start_time"].strftime("%H:%M:%S")
                        window["end_time"] = window["end_time"].strftime("%H:%M:%S")
                    
                    # Convert enums to strings
                    item["restriction_type"] = scheduled_perm.restriction_type.value
                    item["recurrence"] = scheduled_perm.recurrence.value
                    
                    data.append(item)
                
                json.dump(data, f, indent=2)
            
            # Save device restrictions
            device_file = self.data_dir / "device_restrictions.json"
            with open(device_file, 'w') as f:
                data = []
                for device_restriction in self.device_restrictions.values():
                    item = asdict(device_restriction)
                    # Convert datetime objects
                    item["created_at"] = device_restriction.created_at.isoformat()
                    if device_restriction.last_used:
                        item["last_used"] = device_restriction.last_used.isoformat()
                    
                    # Convert time restrictions
                    for window in item.get("time_restrictions", []):
                        window["start_time"] = window["start_time"].strftime("%H:%M:%S")
                        window["end_time"] = window["end_time"].strftime("%H:%M:%S")
                    
                    data.append(item)
                
                json.dump(data, f, indent=2)
            
            logger.info("Saved time policies data to disk")
            
        except Exception as e:
            logger.error(f"Error saving time policies data: {e}")