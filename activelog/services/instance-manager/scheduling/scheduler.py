"""
Scheduler Manager
Handles automatic start/stop scheduling with timezone support and flexible scheduling patterns
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, time
from enum import Enum
import json
import uuid
from dataclasses import dataclass, asdict
import pytz
from croniter import croniter

logger = logging.getLogger(__name__)

class ScheduleType(Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    BUSINESS_HOURS = "business_hours"
    CRON = "cron"
    SMART = "smart"

class ActionType(Enum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    RESIZE = "resize"

@dataclass
class Schedule:
    id: str
    name: str
    schedule_type: ScheduleType
    action: ActionType
    instance_ids: List[str]
    timezone: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    # Schedule-specific parameters
    cron_expression: Optional[str] = None
    one_time_datetime: Optional[datetime] = None
    business_hours_start: Optional[time] = None
    business_hours_end: Optional[time] = None
    business_days: Optional[List[int]] = None  # 0=Monday, 6=Sunday
    
    # Smart scheduling parameters
    smart_pattern: Optional[str] = None
    smart_parameters: Optional[Dict[str, Any]] = None
    
    # Action parameters
    action_parameters: Optional[Dict[str, Any]] = None
    
    # Execution tracking
    last_execution: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    execution_count: int = 0
    failure_count: int = 0
    
    # Notifications
    notify_on_success: bool = False
    notify_on_failure: bool = True
    notification_emails: List[str] = None
    
    def __post_init__(self):
        if self.notification_emails is None:
            self.notification_emails = []
        if self.business_days is None:
            self.business_days = [0, 1, 2, 3, 4]  # Monday to Friday

class ScheduleManager:
    """Manages all instance scheduling operations"""
    
    def __init__(self, config):
        self.config = config
        self.schedules: Dict[str, Schedule] = {}
        self.running = False
        self._load_schedules()
    
    def _load_schedules(self):
        """Load schedules from persistent storage"""
        try:
            # In production, load from database
            # For now, load from file
            schedule_file = '/home/activeloguser/activelog/data/instance-manager/schedules.json'
            try:
                with open(schedule_file, 'r') as f:
                    schedules_data = json.load(f)
                    
                for schedule_data in schedules_data:
                    schedule = self._dict_to_schedule(schedule_data)
                    self.schedules[schedule.id] = schedule
                    
                logger.info(f"Loaded {len(self.schedules)} schedules")
            except FileNotFoundError:
                logger.info("No existing schedules file found")
            except Exception as e:
                logger.error(f"Failed to load schedules: {e}")
                
        except Exception as e:
            logger.error(f"Failed to initialize schedules: {e}")
    
    def _save_schedules(self):
        """Save schedules to persistent storage"""
        try:
            import os
            os.makedirs('/home/activeloguser/activelog/data/instance-manager', exist_ok=True)
            
            schedule_file = '/home/activeloguser/activelog/data/instance-manager/schedules.json'
            schedules_data = [self._schedule_to_dict(schedule) for schedule in self.schedules.values()]
            
            with open(schedule_file, 'w') as f:
                json.dump(schedules_data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")
    
    def _schedule_to_dict(self, schedule: Schedule) -> Dict[str, Any]:
        """Convert Schedule object to dictionary for serialization"""
        return {
            'id': schedule.id,
            'name': schedule.name,
            'schedule_type': schedule.schedule_type.value,
            'action': schedule.action.value,
            'instance_ids': schedule.instance_ids,
            'timezone': schedule.timezone,
            'enabled': schedule.enabled,
            'created_at': schedule.created_at.isoformat(),
            'updated_at': schedule.updated_at.isoformat(),
            'cron_expression': schedule.cron_expression,
            'one_time_datetime': schedule.one_time_datetime.isoformat() if schedule.one_time_datetime else None,
            'business_hours_start': schedule.business_hours_start.isoformat() if schedule.business_hours_start else None,
            'business_hours_end': schedule.business_hours_end.isoformat() if schedule.business_hours_end else None,
            'business_days': schedule.business_days,
            'smart_pattern': schedule.smart_pattern,
            'smart_parameters': schedule.smart_parameters,
            'action_parameters': schedule.action_parameters,
            'last_execution': schedule.last_execution.isoformat() if schedule.last_execution else None,
            'next_execution': schedule.next_execution.isoformat() if schedule.next_execution else None,
            'execution_count': schedule.execution_count,
            'failure_count': schedule.failure_count,
            'notify_on_success': schedule.notify_on_success,
            'notify_on_failure': schedule.notify_on_failure,
            'notification_emails': schedule.notification_emails
        }
    
    def _dict_to_schedule(self, data: Dict[str, Any]) -> Schedule:
        """Convert dictionary to Schedule object"""
        return Schedule(
            id=data['id'],
            name=data['name'],
            schedule_type=ScheduleType(data['schedule_type']),
            action=ActionType(data['action']),
            instance_ids=data['instance_ids'],
            timezone=data['timezone'],
            enabled=data['enabled'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            cron_expression=data.get('cron_expression'),
            one_time_datetime=datetime.fromisoformat(data['one_time_datetime']) if data.get('one_time_datetime') else None,
            business_hours_start=datetime.fromisoformat(data['business_hours_start']).time() if data.get('business_hours_start') else None,
            business_hours_end=datetime.fromisoformat(data['business_hours_end']).time() if data.get('business_hours_end') else None,
            business_days=data.get('business_days'),
            smart_pattern=data.get('smart_pattern'),
            smart_parameters=data.get('smart_parameters'),
            action_parameters=data.get('action_parameters'),
            last_execution=datetime.fromisoformat(data['last_execution']) if data.get('last_execution') else None,
            next_execution=datetime.fromisoformat(data['next_execution']) if data.get('next_execution') else None,
            execution_count=data.get('execution_count', 0),
            failure_count=data.get('failure_count', 0),
            notify_on_success=data.get('notify_on_success', False),
            notify_on_failure=data.get('notify_on_failure', True),
            notification_emails=data.get('notification_emails', [])
        )
    
    def create_schedule(self, schedule_data: Dict[str, Any]) -> str:
        """Create a new schedule"""
        try:
            schedule_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            schedule = Schedule(
                id=schedule_id,
                name=schedule_data['name'],
                schedule_type=ScheduleType(schedule_data['schedule_type']),
                action=ActionType(schedule_data['action']),
                instance_ids=schedule_data['instance_ids'],
                timezone=schedule_data.get('timezone', 'UTC'),
                enabled=schedule_data.get('enabled', True),
                created_at=now,
                updated_at=now,
                cron_expression=schedule_data.get('cron_expression'),
                one_time_datetime=datetime.fromisoformat(schedule_data['one_time_datetime']) if schedule_data.get('one_time_datetime') else None,
                business_hours_start=datetime.strptime(schedule_data['business_hours_start'], '%H:%M:%S').time() if schedule_data.get('business_hours_start') else None,
                business_hours_end=datetime.strptime(schedule_data['business_hours_end'], '%H:%M:%S').time() if schedule_data.get('business_hours_end') else None,
                business_days=schedule_data.get('business_days', [0, 1, 2, 3, 4]),
                smart_pattern=schedule_data.get('smart_pattern'),
                smart_parameters=schedule_data.get('smart_parameters'),
                action_parameters=schedule_data.get('action_parameters'),
                notify_on_success=schedule_data.get('notify_on_success', False),
                notify_on_failure=schedule_data.get('notify_on_failure', True),
                notification_emails=schedule_data.get('notification_emails', [])
            )
            
            # Calculate next execution time
            schedule.next_execution = self._calculate_next_execution(schedule)
            
            self.schedules[schedule_id] = schedule
            self._save_schedules()
            
            logger.info(f"Created schedule {schedule_id}: {schedule.name}")
            return schedule_id
            
        except Exception as e:
            logger.error(f"Failed to create schedule: {e}")
            raise
    
    def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing schedule"""
        try:
            if schedule_id not in self.schedules:
                raise ValueError(f"Schedule {schedule_id} not found")
            
            schedule = self.schedules[schedule_id]
            
            # Update fields
            for field, value in updates.items():
                if hasattr(schedule, field):
                    if field == 'schedule_type':
                        setattr(schedule, field, ScheduleType(value))
                    elif field == 'action':
                        setattr(schedule, field, ActionType(value))
                    elif field in ['one_time_datetime']:
                        setattr(schedule, field, datetime.fromisoformat(value) if value else None)
                    elif field in ['business_hours_start', 'business_hours_end']:
                        setattr(schedule, field, datetime.strptime(value, '%H:%M:%S').time() if value else None)
                    else:
                        setattr(schedule, field, value)
            
            schedule.updated_at = datetime.utcnow()
            
            # Recalculate next execution
            schedule.next_execution = self._calculate_next_execution(schedule)
            
            self._save_schedules()
            
            logger.info(f"Updated schedule {schedule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update schedule {schedule_id}: {e}")
            raise
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule"""
        try:
            if schedule_id not in self.schedules:
                raise ValueError(f"Schedule {schedule_id} not found")
            
            del self.schedules[schedule_id]
            self._save_schedules()
            
            logger.info(f"Deleted schedule {schedule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete schedule {schedule_id}: {e}")
            raise
    
    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific schedule"""
        if schedule_id in self.schedules:
            return self._schedule_to_dict(self.schedules[schedule_id])
        return None
    
    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedules"""
        return [self._schedule_to_dict(schedule) for schedule in self.schedules.values()]
    
    def _calculate_next_execution(self, schedule: Schedule) -> Optional[datetime]:
        """Calculate the next execution time for a schedule"""
        try:
            now = datetime.utcnow()
            tz = pytz.timezone(schedule.timezone)
            local_now = pytz.utc.localize(now).astimezone(tz)
            
            if schedule.schedule_type == ScheduleType.ONE_TIME:
                if schedule.one_time_datetime and schedule.one_time_datetime > now:
                    return schedule.one_time_datetime
                return None
            
            elif schedule.schedule_type == ScheduleType.CRON:
                if schedule.cron_expression:
                    cron = croniter(schedule.cron_expression, local_now)
                    next_local = cron.get_next(datetime)
                    return next_local.astimezone(pytz.utc).replace(tzinfo=None)
                return None
            
            elif schedule.schedule_type == ScheduleType.BUSINESS_HOURS:
                return self._calculate_next_business_hours(schedule, local_now)
            
            elif schedule.schedule_type == ScheduleType.SMART:
                return self._calculate_next_smart_execution(schedule, local_now)
            
            elif schedule.schedule_type == ScheduleType.RECURRING:
                # Default recurring pattern (daily)
                next_execution = now + timedelta(days=1)
                return next_execution
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to calculate next execution for schedule {schedule.id}: {e}")
            return None
    
    def _calculate_next_business_hours(self, schedule: Schedule, local_now: datetime) -> Optional[datetime]:
        """Calculate next business hours execution"""
        try:
            if not schedule.business_hours_start or not schedule.business_hours_end:
                return None
            
            current_weekday = local_now.weekday()
            current_time = local_now.time()
            
            # Check if today is a business day
            if current_weekday in schedule.business_days:
                if schedule.action == ActionType.START:
                    # Start at business hours start
                    if current_time < schedule.business_hours_start:
                        next_time = datetime.combine(local_now.date(), schedule.business_hours_start)
                        return pytz.timezone(schedule.timezone).localize(next_time).astimezone(pytz.utc).replace(tzinfo=None)
                
                elif schedule.action == ActionType.STOP:
                    # Stop at business hours end
                    if current_time < schedule.business_hours_end:
                        next_time = datetime.combine(local_now.date(), schedule.business_hours_end)
                        return pytz.timezone(schedule.timezone).localize(next_time).astimezone(pytz.utc).replace(tzinfo=None)
            
            # Find next business day
            days_ahead = 1
            while days_ahead < 7:
                future_date = local_now + timedelta(days=days_ahead)
                if future_date.weekday() in schedule.business_days:
                    target_time = schedule.business_hours_start if schedule.action == ActionType.START else schedule.business_hours_end
                    next_time = datetime.combine(future_date.date(), target_time)
                    return pytz.timezone(schedule.timezone).localize(next_time).astimezone(pytz.utc).replace(tzinfo=None)
                days_ahead += 1
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to calculate business hours: {e}")
            return None
    
    def _calculate_next_smart_execution(self, schedule: Schedule, local_now: datetime) -> Optional[datetime]:
        """Calculate next smart execution based on patterns"""
        try:
            if not schedule.smart_pattern:
                return None
            
            smart_params = schedule.smart_parameters or {}
            
            if schedule.smart_pattern == 'night_shutdown':
                # Shut down at night, start in morning
                night_hour = smart_params.get('night_hour', 22)  # 10 PM
                morning_hour = smart_params.get('morning_hour', 8)  # 8 AM
                
                if schedule.action == ActionType.STOP:
                    # Schedule stop for tonight
                    if local_now.hour < night_hour:
                        next_time = local_now.replace(hour=night_hour, minute=0, second=0, microsecond=0)
                    else:
                        next_time = (local_now + timedelta(days=1)).replace(hour=night_hour, minute=0, second=0, microsecond=0)
                
                elif schedule.action == ActionType.START:
                    # Schedule start for tomorrow morning
                    if local_now.hour < morning_hour:
                        next_time = local_now.replace(hour=morning_hour, minute=0, second=0, microsecond=0)
                    else:
                        next_time = (local_now + timedelta(days=1)).replace(hour=morning_hour, minute=0, second=0, microsecond=0)
                
                return pytz.timezone(schedule.timezone).localize(next_time).astimezone(pytz.utc).replace(tzinfo=None)
            
            elif schedule.smart_pattern == 'weekend_shutdown':
                # Shut down on weekends
                current_weekday = local_now.weekday()
                
                if schedule.action == ActionType.STOP:
                    # Stop on Friday evening
                    if current_weekday < 4:  # Monday to Thursday
                        days_to_friday = 4 - current_weekday
                        friday_evening = (local_now + timedelta(days=days_to_friday)).replace(hour=18, minute=0, second=0, microsecond=0)
                        return pytz.timezone(schedule.timezone).localize(friday_evening).astimezone(pytz.utc).replace(tzinfo=None)
                    elif current_weekday == 4 and local_now.hour < 18:  # Friday before 6 PM
                        friday_evening = local_now.replace(hour=18, minute=0, second=0, microsecond=0)
                        return pytz.timezone(schedule.timezone).localize(friday_evening).astimezone(pytz.utc).replace(tzinfo=None)
                
                elif schedule.action == ActionType.START:
                    # Start on Monday morning
                    if current_weekday <= 0:  # Monday
                        if local_now.hour < 8:
                            monday_morning = local_now.replace(hour=8, minute=0, second=0, microsecond=0)
                        else:
                            monday_morning = (local_now + timedelta(days=7)).replace(hour=8, minute=0, second=0, microsecond=0)
                    else:
                        days_to_monday = 7 - current_weekday
                        monday_morning = (local_now + timedelta(days=days_to_monday)).replace(hour=8, minute=0, second=0, microsecond=0)
                    
                    return pytz.timezone(schedule.timezone).localize(monday_morning).astimezone(pytz.utc).replace(tzinfo=None)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to calculate smart execution: {e}")
            return None
    
    async def execute_pending_schedules(self):
        """Execute all pending schedules"""
        now = datetime.utcnow()
        
        for schedule in self.schedules.values():
            if not schedule.enabled:
                continue
            
            if schedule.next_execution and schedule.next_execution <= now:
                try:
                    await self._execute_schedule(schedule)
                except Exception as e:
                    logger.error(f"Failed to execute schedule {schedule.id}: {e}")
                    schedule.failure_count += 1
                    
                    # Send failure notification
                    if schedule.notify_on_failure:
                        await self._send_notification(schedule, False, str(e))
                
                # Calculate next execution
                schedule.last_execution = now
                schedule.next_execution = self._calculate_next_execution(schedule)
                
                # Remove one-time schedules that have been executed
                if schedule.schedule_type == ScheduleType.ONE_TIME:
                    schedule.enabled = False
                
                self._save_schedules()
    
    async def _execute_schedule(self, schedule: Schedule):
        """Execute a single schedule"""
        logger.info(f"Executing schedule {schedule.id}: {schedule.name}")
        
        from core.instance_controller import InstanceController
        import boto3
        
        ec2_client = boto3.client('ec2', region_name=self.config.aws_region)
        controller = InstanceController(ec2_client)
        
        action_params = schedule.action_parameters or {}
        
        if schedule.action == ActionType.START:
            result = controller.batch_operation(schedule.instance_ids, 'start', action_params)
        elif schedule.action == ActionType.STOP:
            result = controller.batch_operation(schedule.instance_ids, 'stop', action_params)
        elif schedule.action == ActionType.RESTART:
            result = controller.batch_operation(schedule.instance_ids, 'restart', action_params)
        else:
            raise ValueError(f"Unsupported action: {schedule.action}")
        
        schedule.execution_count += 1
        
        # Check if execution was successful
        success = result['summary']['error'] == 0
        
        # Send notification
        if (success and schedule.notify_on_success) or (not success and schedule.notify_on_failure):
            await self._send_notification(schedule, success, result)
        
        logger.info(f"Schedule {schedule.id} executed. Success: {success}")
    
    async def _send_notification(self, schedule: Schedule, success: bool, result: Any):
        """Send notification about schedule execution"""
        try:
            if not schedule.notification_emails:
                return
            
            status = "SUCCESS" if success else "FAILED"
            subject = f"Schedule '{schedule.name}' {status}"
            
            message = f"""
Schedule Execution Report

Schedule: {schedule.name} ({schedule.id})
Action: {schedule.action.value}
Status: {status}
Execution Time: {datetime.utcnow().isoformat()}
Instances: {', '.join(schedule.instance_ids)}

Result Details:
{json.dumps(result, indent=2, default=str)}

---
ActiveLog Instance Manager
            """.strip()
            
            # In production, integrate with actual email service
            logger.info(f"Notification sent for schedule {schedule.id}: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send notification for schedule {schedule.id}: {e}")
    
    def get_schedule_history(self, schedule_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for a schedule"""
        # In production, this would query a database
        # For now, return basic info from the schedule object
        if schedule_id not in self.schedules:
            return []
        
        schedule = self.schedules[schedule_id]
        
        # Mock history data
        history = []
        if schedule.last_execution:
            history.append({
                'execution_time': schedule.last_execution.isoformat(),
                'status': 'success',
                'action': schedule.action.value,
                'instances_affected': len(schedule.instance_ids)
            })
        
        return history
    
    def validate_schedule_data(self, schedule_data: Dict[str, Any]) -> List[str]:
        """Validate schedule data and return list of errors"""
        errors = []
        
        required_fields = ['name', 'schedule_type', 'action', 'instance_ids']
        for field in required_fields:
            if field not in schedule_data:
                errors.append(f"Missing required field: {field}")
        
        if 'schedule_type' in schedule_data:
            try:
                ScheduleType(schedule_data['schedule_type'])
            except ValueError:
                errors.append(f"Invalid schedule_type: {schedule_data['schedule_type']}")
        
        if 'action' in schedule_data:
            try:
                ActionType(schedule_data['action'])
            except ValueError:
                errors.append(f"Invalid action: {schedule_data['action']}")
        
        if 'instance_ids' in schedule_data:
            if not isinstance(schedule_data['instance_ids'], list):
                errors.append("instance_ids must be a list")
            elif not schedule_data['instance_ids']:
                errors.append("instance_ids cannot be empty")
        
        # Validate schedule type specific fields
        if schedule_data.get('schedule_type') == 'cron':
            if 'cron_expression' not in schedule_data:
                errors.append("cron_expression is required for cron schedules")
            else:
                try:
                    croniter(schedule_data['cron_expression'])
                except:
                    errors.append("Invalid cron expression")
        
        elif schedule_data.get('schedule_type') == 'one_time':
            if 'one_time_datetime' not in schedule_data:
                errors.append("one_time_datetime is required for one-time schedules")
            else:
                try:
                    datetime.fromisoformat(schedule_data['one_time_datetime'])
                except:
                    errors.append("Invalid one_time_datetime format")
        
        elif schedule_data.get('schedule_type') == 'business_hours':
            if 'business_hours_start' not in schedule_data:
                errors.append("business_hours_start is required for business hours schedules")
            if 'business_hours_end' not in schedule_data:
                errors.append("business_hours_end is required for business hours schedules")
        
        return errors