"""
Watch Alarm System
Comprehensive attention monitoring and escalating alarm system for crew watch duties
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import json

from ..roles.permissions import CrewRole, Permission, PermissionManager
from ..crew.crew_management import CrewManager

logger = logging.getLogger(__name__)


class AlarmLevel(Enum):
    """Alarm severity levels with escalation"""
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlarmType(Enum):
    """Types of watch alarms"""
    ATTENTION_CHECK = "attention_check"
    WATCH_TIMEOUT = "watch_timeout"
    NO_RESPONSE = "no_response"
    SAFETY_ALERT = "safety_alert"
    SYSTEM_ALERT = "system_alert"
    CAPTAIN_CALL = "captain_call"


class WatchStatus(Enum):
    """Watch duty status"""
    ON_WATCH = "on_watch"
    RESPONDING = "responding"
    ATTENTION_REQUIRED = "attention_required"
    UNRESPONSIVE = "unresponsive"
    OFF_WATCH = "off_watch"
    EMERGENCY_OVERRIDE = "emergency_override"


class OverrideReason(Enum):
    """Reasons for captain alarm override"""
    FALSE_ALARM = "false_alarm"
    CREW_CONFIRMED_SAFE = "crew_confirmed_safe"
    EMERGENCY_SITUATION = "emergency_situation"
    TECHNICAL_ISSUE = "technical_issue"
    MAINTENANCE_MODE = "maintenance_mode"


@dataclass
class AlarmEscalationRule:
    """Rules for alarm escalation"""
    alarm_type: AlarmType
    initial_level: AlarmLevel
    escalation_intervals: List[int]  # seconds
    escalation_levels: List[AlarmLevel]
    requires_response: bool = True
    auto_escalate: bool = True
    max_escalation_level: AlarmLevel = AlarmLevel.EMERGENCY


@dataclass
class AlarmEvent:
    """Individual alarm event"""
    event_id: str
    alarm_type: AlarmType
    level: AlarmLevel
    crew_member_id: str
    vessel_id: str
    watch_id: str
    timestamp: datetime
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    response_required: bool = True
    escalation_count: int = 0
    override_by: Optional[str] = None
    override_reason: Optional[OverrideReason] = None


@dataclass
class WatchSession:
    """Active watch session"""
    watch_id: str
    crew_member_id: str
    vessel_id: str
    role: CrewRole
    start_time: datetime
    scheduled_end: Optional[datetime]
    status: WatchStatus = WatchStatus.ON_WATCH
    last_response: Optional[datetime] = None
    attention_interval: int = 300  # 5 minutes default
    consecutive_misses: int = 0
    active_alarms: List[str] = field(default_factory=list)


class AttentionMonitor:
    """Monitors crew attention during watch duties"""
    
    def __init__(self, default_interval: int = 300):
        self.default_interval = default_interval
        self.custom_intervals: Dict[str, int] = {}
        self.last_checks: Dict[str, datetime] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
    async def start_monitoring(self, watch_session: WatchSession) -> bool:
        """Start attention monitoring for a watch session"""
        try:
            watch_id = watch_session.watch_id
            
            # Stop existing monitoring if any
            await self.stop_monitoring(watch_id)
            
            # Start new monitoring task
            interval = self.custom_intervals.get(
                watch_session.crew_member_id, 
                self.default_interval
            )
            
            task = asyncio.create_task(
                self._monitor_attention(watch_session, interval)
            )
            self.monitoring_tasks[watch_id] = task
            
            self.last_checks[watch_id] = datetime.now(timezone.utc)
            
            logger.info(f"Started attention monitoring for watch {watch_id} "
                       f"with {interval}s interval")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start attention monitoring: {e}")
            return False
    
    async def stop_monitoring(self, watch_id: str) -> None:
        """Stop attention monitoring for a watch session"""
        if watch_id in self.monitoring_tasks:
            self.monitoring_tasks[watch_id].cancel()
            del self.monitoring_tasks[watch_id]
            
        if watch_id in self.last_checks:
            del self.last_checks[watch_id]
    
    async def record_response(self, watch_id: str) -> bool:
        """Record crew member response to attention check"""
        try:
            self.last_checks[watch_id] = datetime.now(timezone.utc)
            logger.info(f"Recorded response for watch {watch_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to record response: {e}")
            return False
    
    def set_custom_interval(self, crew_member_id: str, interval: int) -> None:
        """Set custom attention interval for crew member"""
        self.custom_intervals[crew_member_id] = interval
        logger.info(f"Set custom interval {interval}s for crew {crew_member_id}")
    
    async def _monitor_attention(self, watch_session: WatchSession, interval: int) -> None:
        """Internal attention monitoring loop"""
        try:
            while watch_session.status == WatchStatus.ON_WATCH:
                await asyncio.sleep(interval)
                
                # Check if response received
                last_check = self.last_checks.get(watch_session.watch_id)
                if not last_check:
                    continue
                
                time_since_check = datetime.now(timezone.utc) - last_check
                
                if time_since_check.total_seconds() >= interval:
                    # Attention check needed
                    await self._trigger_attention_check(watch_session)
                    
        except asyncio.CancelledError:
            logger.info(f"Attention monitoring cancelled for watch {watch_session.watch_id}")
        except Exception as e:
            logger.error(f"Error in attention monitoring: {e}")
    
    async def _trigger_attention_check(self, watch_session: WatchSession) -> None:
        """Trigger attention check for watch session"""
        # This would be implemented with the alarm manager
        logger.info(f"Triggering attention check for watch {watch_session.watch_id}")


class WatchAlarmManager:
    """Main watch alarm management system"""
    
    def __init__(self, crew_manager: CrewManager, permission_manager: PermissionManager):
        self.crew_manager = crew_manager
        self.permission_manager = permission_manager
        self.attention_monitor = AttentionMonitor()
        
        # Active sessions and alarms
        self.active_watches: Dict[str, WatchSession] = {}
        self.active_alarms: Dict[str, AlarmEvent] = {}
        self.alarm_history: List[AlarmEvent] = []
        
        # Escalation rules
        self.escalation_rules = self._setup_default_escalation_rules()
        
        # Event handlers
        self.alarm_handlers: Dict[AlarmLevel, List[Callable]] = {
            level: [] for level in AlarmLevel
        }
        
        # WebSocket connections for real-time updates
        self.websocket_connections: Dict[str, Any] = {}
        
        logger.info("Watch Alarm Manager initialized")
    
    def _setup_default_escalation_rules(self) -> Dict[AlarmType, AlarmEscalationRule]:
        """Setup default alarm escalation rules"""
        return {
            AlarmType.ATTENTION_CHECK: AlarmEscalationRule(
                alarm_type=AlarmType.ATTENTION_CHECK,
                initial_level=AlarmLevel.INFO,
                escalation_intervals=[60, 180, 300],  # 1min, 3min, 5min
                escalation_levels=[AlarmLevel.WARNING, AlarmLevel.URGENT, AlarmLevel.CRITICAL]
            ),
            AlarmType.WATCH_TIMEOUT: AlarmEscalationRule(
                alarm_type=AlarmType.WATCH_TIMEOUT,
                initial_level=AlarmLevel.WARNING,
                escalation_intervals=[300, 600],  # 5min, 10min
                escalation_levels=[AlarmLevel.URGENT, AlarmLevel.CRITICAL]
            ),
            AlarmType.NO_RESPONSE: AlarmEscalationRule(
                alarm_type=AlarmType.NO_RESPONSE,
                initial_level=AlarmLevel.URGENT,
                escalation_intervals=[180, 300],  # 3min, 5min
                escalation_levels=[AlarmLevel.CRITICAL, AlarmLevel.EMERGENCY]
            ),
            AlarmType.SAFETY_ALERT: AlarmEscalationRule(
                alarm_type=AlarmType.SAFETY_ALERT,
                initial_level=AlarmLevel.CRITICAL,
                escalation_intervals=[60],  # 1min
                escalation_levels=[AlarmLevel.EMERGENCY]
            ),
            AlarmType.CAPTAIN_CALL: AlarmEscalationRule(
                alarm_type=AlarmType.CAPTAIN_CALL,
                initial_level=AlarmLevel.EMERGENCY,
                escalation_intervals=[],
                escalation_levels=[],
                auto_escalate=False
            )
        }
    
    async def start_watch(self, crew_member_id: str, vessel_id: str, 
                         scheduled_duration: Optional[int] = None) -> Optional[str]:
        """Start a new watch session"""
        try:
            # Verify crew member permissions
            crew_member = await self.crew_manager.get_crew_member(crew_member_id)
            if not crew_member:
                logger.error(f"Crew member {crew_member_id} not found")
                return None
            
            # Check if crew member can stand watch
            can_watch = self.permission_manager.has_permission(
                crew_member.role, Permission.STAND_WATCH
            )
            if not can_watch:
                logger.error(f"Crew member {crew_member_id} cannot stand watch")
                return None
            
            # Create watch session
            watch_id = f"watch_{vessel_id}_{crew_member_id}_{int(time.time())}"
            scheduled_end = None
            if scheduled_duration:
                scheduled_end = datetime.now(timezone.utc) + timedelta(seconds=scheduled_duration)
            
            watch_session = WatchSession(
                watch_id=watch_id,
                crew_member_id=crew_member_id,
                vessel_id=vessel_id,
                role=crew_member.role,
                start_time=datetime.now(timezone.utc),
                scheduled_end=scheduled_end,
                status=WatchStatus.ON_WATCH
            )
            
            self.active_watches[watch_id] = watch_session
            
            # Start attention monitoring
            await self.attention_monitor.start_monitoring(watch_session)
            
            logger.info(f"Started watch session {watch_id} for crew {crew_member_id}")
            
            # Notify other crew members
            await self._broadcast_watch_update(watch_session)
            
            return watch_id
            
        except Exception as e:
            logger.error(f"Failed to start watch: {e}")
            return None
    
    async def end_watch(self, watch_id: str, ended_by: str) -> bool:
        """End an active watch session"""
        try:
            watch_session = self.active_watches.get(watch_id)
            if not watch_session:
                logger.error(f"Watch session {watch_id} not found")
                return False
            
            # Verify permission to end watch
            if watch_session.crew_member_id != ended_by:
                crew_member = await self.crew_manager.get_crew_member(ended_by)
                if not crew_member:
                    return False
                
                can_override = self.permission_manager.has_permission(
                    crew_member.role, Permission.OVERRIDE_ALARMS
                )
                if not can_override:
                    logger.error(f"User {ended_by} cannot end watch {watch_id}")
                    return False
            
            # Stop monitoring
            await self.attention_monitor.stop_monitoring(watch_id)
            
            # Update status
            watch_session.status = WatchStatus.OFF_WATCH
            
            # Clear any active alarms for this watch
            await self._clear_watch_alarms(watch_id)
            
            # Remove from active watches
            del self.active_watches[watch_id]
            
            logger.info(f"Ended watch session {watch_id}")
            
            # Notify crew
            await self._broadcast_watch_update(watch_session)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to end watch: {e}")
            return False
    
    async def trigger_alarm(self, alarm_type: AlarmType, crew_member_id: str, 
                          vessel_id: str, watch_id: str, message: str,
                          metadata: Dict[str, Any] = None) -> Optional[str]:
        """Trigger a new alarm"""
        try:
            event_id = f"alarm_{alarm_type.value}_{int(time.time())}"
            
            rule = self.escalation_rules.get(alarm_type)
            if not rule:
                logger.error(f"No escalation rule for alarm type {alarm_type}")
                return None
            
            alarm_event = AlarmEvent(
                event_id=event_id,
                alarm_type=alarm_type,
                level=rule.initial_level,
                crew_member_id=crew_member_id,
                vessel_id=vessel_id,
                watch_id=watch_id,
                timestamp=datetime.now(timezone.utc),
                message=message,
                metadata=metadata or {},
                response_required=rule.requires_response
            )
            
            self.active_alarms[event_id] = alarm_event
            self.alarm_history.append(alarm_event)
            
            # Add to watch session
            if watch_id in self.active_watches:
                self.active_watches[watch_id].active_alarms.append(event_id)
            
            logger.warning(f"Triggered {alarm_type.value} alarm: {message}")
            
            # Execute alarm handlers
            await self._execute_alarm_handlers(alarm_event)
            
            # Start escalation if enabled
            if rule.auto_escalate and rule.escalation_intervals:
                asyncio.create_task(self._handle_escalation(alarm_event))
            
            # Broadcast to connected clients
            await self._broadcast_alarm(alarm_event)
            
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to trigger alarm: {e}")
            return None
    
    async def respond_to_alarm(self, alarm_id: str, responder_id: str, 
                             response_message: Optional[str] = None) -> bool:
        """Respond to an active alarm"""
        try:
            alarm = self.active_alarms.get(alarm_id)
            if not alarm:
                logger.error(f"Alarm {alarm_id} not found")
                return False
            
            if alarm.acknowledged:
                logger.info(f"Alarm {alarm_id} already acknowledged")
                return True
            
            # Verify responder permissions
            crew_member = await self.crew_manager.get_crew_member(responder_id)
            if not crew_member:
                return False
            
            # Update alarm
            alarm.acknowledged = True
            alarm.acknowledged_by = responder_id
            alarm.acknowledged_at = datetime.now(timezone.utc)
            
            if response_message:
                alarm.metadata['response_message'] = response_message
            
            # Update watch session if applicable
            watch_session = self.active_watches.get(alarm.watch_id)
            if watch_session:
                watch_session.last_response = datetime.now(timezone.utc)
                if alarm.alarm_type == AlarmType.ATTENTION_CHECK:
                    watch_session.consecutive_misses = 0
                    await self.attention_monitor.record_response(alarm.watch_id)
            
            logger.info(f"Alarm {alarm_id} acknowledged by {responder_id}")
            
            # Broadcast update
            await self._broadcast_alarm_update(alarm)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to respond to alarm: {e}")
            return False
    
    async def override_alarm(self, alarm_id: str, override_by: str, 
                           reason: OverrideReason, notes: Optional[str] = None) -> bool:
        """Override an alarm (captain only)"""
        try:
            # Verify override permissions
            crew_member = await self.crew_manager.get_crew_member(override_by)
            if not crew_member:
                return False
            
            can_override = self.permission_manager.has_permission(
                crew_member.role, Permission.OVERRIDE_ALARMS
            )
            if not can_override:
                logger.error(f"User {override_by} cannot override alarms")
                return False
            
            alarm = self.active_alarms.get(alarm_id)
            if not alarm:
                logger.error(f"Alarm {alarm_id} not found")
                return False
            
            # Record override
            alarm.override_by = override_by
            alarm.override_reason = reason
            alarm.acknowledged = True
            alarm.acknowledged_by = override_by
            alarm.acknowledged_at = datetime.now(timezone.utc)
            
            if notes:
                alarm.metadata['override_notes'] = notes
            
            # Update watch if emergency override
            if reason == OverrideReason.EMERGENCY_SITUATION:
                watch_session = self.active_watches.get(alarm.watch_id)
                if watch_session:
                    watch_session.status = WatchStatus.EMERGENCY_OVERRIDE
            
            logger.warning(f"Alarm {alarm_id} overridden by {override_by}: {reason.value}")
            
            # Broadcast update
            await self._broadcast_alarm_update(alarm)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to override alarm: {e}")
            return False
    
    async def get_watch_status(self, watch_id: str) -> Optional[Dict[str, Any]]:
        """Get current watch status"""
        watch_session = self.active_watches.get(watch_id)
        if not watch_session:
            return None
        
        active_alarms = [
            self.active_alarms[alarm_id] 
            for alarm_id in watch_session.active_alarms
            if alarm_id in self.active_alarms
        ]
        
        return {
            'watch_id': watch_session.watch_id,
            'crew_member_id': watch_session.crew_member_id,
            'role': watch_session.role.value,
            'status': watch_session.status.value,
            'start_time': watch_session.start_time.isoformat(),
            'last_response': watch_session.last_response.isoformat() if watch_session.last_response else None,
            'consecutive_misses': watch_session.consecutive_misses,
            'active_alarms': len(active_alarms),
            'attention_interval': watch_session.attention_interval
        }
    
    def add_alarm_handler(self, level: AlarmLevel, handler: Callable) -> None:
        """Add handler for specific alarm level"""
        self.alarm_handlers[level].append(handler)
    
    async def _handle_escalation(self, alarm_event: AlarmEvent) -> None:
        """Handle alarm escalation"""
        try:
            rule = self.escalation_rules.get(alarm_event.alarm_type)
            if not rule or not rule.auto_escalate:
                return
            
            for i, (interval, next_level) in enumerate(zip(rule.escalation_intervals, rule.escalation_levels)):
                await asyncio.sleep(interval)
                
                # Check if alarm was acknowledged
                if alarm_event.acknowledged or alarm_event.override_by:
                    logger.info(f"Alarm {alarm_event.event_id} resolved, stopping escalation")
                    return
                
                # Check if we've reached max escalation
                if next_level.value >= rule.max_escalation_level.value:
                    break
                
                # Escalate alarm
                alarm_event.level = next_level
                alarm_event.escalation_count += 1
                
                logger.warning(f"Escalating alarm {alarm_event.event_id} to {next_level.value}")
                
                # Execute handlers for new level
                await self._execute_alarm_handlers(alarm_event)
                
                # Broadcast escalation
                await self._broadcast_alarm_update(alarm_event)
                
                # Update watch status for unresponsive crew
                if alarm_event.alarm_type == AlarmType.ATTENTION_CHECK:
                    watch_session = self.active_watches.get(alarm_event.watch_id)
                    if watch_session:
                        watch_session.consecutive_misses += 1
                        if next_level == AlarmLevel.CRITICAL:
                            watch_session.status = WatchStatus.UNRESPONSIVE
                
        except asyncio.CancelledError:
            logger.info(f"Escalation cancelled for alarm {alarm_event.event_id}")
        except Exception as e:
            logger.error(f"Error in alarm escalation: {e}")
    
    async def _execute_alarm_handlers(self, alarm_event: AlarmEvent) -> None:
        """Execute all handlers for alarm level"""
        handlers = self.alarm_handlers.get(alarm_event.level, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alarm_event)
                else:
                    handler(alarm_event)
            except Exception as e:
                logger.error(f"Error executing alarm handler: {e}")
    
    async def _broadcast_alarm(self, alarm_event: AlarmEvent) -> None:
        """Broadcast new alarm to connected clients"""
        message = {
            'type': 'new_alarm',
            'alarm': {
                'event_id': alarm_event.event_id,
                'alarm_type': alarm_event.alarm_type.value,
                'level': alarm_event.level.value,
                'crew_member_id': alarm_event.crew_member_id,
                'vessel_id': alarm_event.vessel_id,
                'watch_id': alarm_event.watch_id,
                'timestamp': alarm_event.timestamp.isoformat(),
                'message': alarm_event.message,
                'metadata': alarm_event.metadata
            }
        }
        
        await self._broadcast_to_websockets(message)
    
    async def _broadcast_alarm_update(self, alarm_event: AlarmEvent) -> None:
        """Broadcast alarm acknowledgment/override to connected clients"""
        message = {
            'type': 'alarm_update',
            'alarm': {
                'event_id': alarm_event.event_id,
                'acknowledged': alarm_event.acknowledged,
                'acknowledged_by': alarm_event.acknowledged_by,
                'acknowledged_at': alarm_event.acknowledged_at.isoformat() if alarm_event.acknowledged_at else None,
                'override_by': alarm_event.override_by,
                'override_reason': alarm_event.override_reason.value if alarm_event.override_reason else None,
                'level': alarm_event.level.value,
                'escalation_count': alarm_event.escalation_count
            }
        }
        
        await self._broadcast_to_websockets(message)
    
    async def _broadcast_watch_update(self, watch_session: WatchSession) -> None:
        """Broadcast watch status update"""
        message = {
            'type': 'watch_update',
            'watch': {
                'watch_id': watch_session.watch_id,
                'crew_member_id': watch_session.crew_member_id,
                'vessel_id': watch_session.vessel_id,
                'status': watch_session.status.value,
                'start_time': watch_session.start_time.isoformat(),
                'last_response': watch_session.last_response.isoformat() if watch_session.last_response else None
            }
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
    
    async def _clear_watch_alarms(self, watch_id: str) -> None:
        """Clear all active alarms for a watch"""
        watch_session = self.active_watches.get(watch_id)
        if not watch_session:
            return
        
        for alarm_id in watch_session.active_alarms[:]:
            alarm = self.active_alarms.get(alarm_id)
            if alarm and not alarm.acknowledged:
                alarm.acknowledged = True
                alarm.acknowledged_by = "system"
                alarm.acknowledged_at = datetime.now(timezone.utc)
                alarm.metadata['auto_cleared'] = True
        
        watch_session.active_alarms.clear()
    
    def register_websocket(self, connection_id: str, websocket: Any) -> None:
        """Register WebSocket connection for real-time updates"""
        self.websocket_connections[connection_id] = websocket
        logger.info(f"Registered WebSocket connection {connection_id}")
    
    def unregister_websocket(self, connection_id: str) -> None:
        """Unregister WebSocket connection"""
        if connection_id in self.websocket_connections:
            del self.websocket_connections[connection_id]
            logger.info(f"Unregistered WebSocket connection {connection_id}")