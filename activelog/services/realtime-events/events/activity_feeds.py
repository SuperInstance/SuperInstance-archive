#!/usr/bin/env python3
"""
ActiveLog Real-Time Event System - Live Activity Feeds
Real-time activity feeds with advanced filtering and aggregation
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ActivityType(Enum):
    """Types of activities that can be tracked"""
    USER_JOIN = "user.join"
    USER_LEAVE = "user.leave"
    DOCUMENT_EDIT = "document.edit"
    DOCUMENT_CREATE = "document.create"
    DOCUMENT_DELETE = "document.delete"
    MESSAGE_SEND = "message.send"
    FILE_UPLOAD = "file.upload"
    COMMENT_ADD = "comment.add"
    COLLABORATION_START = "collaboration.start"
    COLLABORATION_END = "collaboration.end"
    CURSOR_MOVE = "cursor.move"
    PRESENCE_UPDATE = "presence.update"
    CUSTOM = "custom"

@dataclass
class ActivityEvent:
    """Represents a single activity event"""
    id: str
    type: ActivityType
    namespace: str
    user_id: str
    target_id: Optional[str] = None  # Document ID, file ID, etc.
    target_type: Optional[str] = None  # "document", "file", etc.
    data: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    timestamp: float = 0
    room: Optional[str] = None
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp == 0:
            self.timestamp = time.time()

@dataclass
class FilterCriteria:
    """Criteria for filtering activity feeds"""
    namespaces: Set[str] = None
    activity_types: Set[ActivityType] = None
    user_ids: Set[str] = None
    target_types: Set[str] = None
    rooms: Set[str] = None
    since_timestamp: float = 0
    until_timestamp: float = 0
    max_results: int = 100
    priority_min: int = 1
    priority_max: int = 3
    
    def __post_init__(self):
        if self.namespaces is None:
            self.namespaces = set()
        if self.activity_types is None:
            self.activity_types = set()
        if self.user_ids is None:
            self.user_ids = set()
        if self.target_types is None:
            self.target_types = set()
        if self.rooms is None:
            self.rooms = set()

class ActivityAggregator:
    """Aggregates similar activities to reduce noise"""
    
    def __init__(self, window_size: float = 30.0):
        self.window_size = window_size  # seconds
        self.aggregation_rules: Dict[ActivityType, Callable] = {
            ActivityType.CURSOR_MOVE: self._aggregate_cursor_moves,
            ActivityType.DOCUMENT_EDIT: self._aggregate_document_edits,
            ActivityType.PRESENCE_UPDATE: self._aggregate_presence_updates,
        }
    
    def should_aggregate(self, event1: ActivityEvent, event2: ActivityEvent) -> bool:
        """Check if two events should be aggregated"""
        if event1.type != event2.type:
            return False
        
        if event1.user_id != event2.user_id:
            return False
        
        if event1.target_id != event2.target_id:
            return False
        
        time_diff = abs(event1.timestamp - event2.timestamp)
        if time_diff > self.window_size:
            return False
        
        return True
    
    def aggregate_events(self, events: List[ActivityEvent]) -> List[ActivityEvent]:
        """Aggregate similar events"""
        if not events:
            return []
        
        # Group events by type and user
        groups = defaultdict(list)
        for event in events:
            key = (event.type, event.user_id, event.target_id)
            groups[key].append(event)
        
        aggregated = []
        for group in groups.values():
            if len(group) == 1:
                aggregated.extend(group)
            else:
                # Try to aggregate
                group.sort(key=lambda x: x.timestamp)
                aggregated_event = self._aggregate_group(group)
                aggregated.append(aggregated_event)
        
        return aggregated
    
    def _aggregate_group(self, events: List[ActivityEvent]) -> ActivityEvent:
        """Aggregate a group of similar events"""
        if not events:
            return None
        
        event_type = events[0].type
        if event_type in self.aggregation_rules:
            return self.aggregation_rules[event_type](events)
        else:
            return self._default_aggregation(events)
    
    def _aggregate_cursor_moves(self, events: List[ActivityEvent]) -> ActivityEvent:
        """Aggregate cursor movement events"""
        latest = events[-1]
        count = len(events)
        
        return ActivityEvent(
            id=str(uuid.uuid4()),
            type=ActivityType.CURSOR_MOVE,
            namespace=latest.namespace,
            user_id=latest.user_id,
            target_id=latest.target_id,
            target_type=latest.target_type,
            data={
                **latest.data,
                "movement_count": count,
                "duration": events[-1].timestamp - events[0].timestamp
            },
            room=latest.room,
            timestamp=latest.timestamp,
            priority=latest.priority
        )
    
    def _aggregate_document_edits(self, events: List[ActivityEvent]) -> ActivityEvent:
        """Aggregate document edit events"""
        latest = events[-1]
        count = len(events)
        
        # Calculate total characters changed
        total_chars = sum(
            event.data.get("characters_changed", 0) for event in events
        )
        
        return ActivityEvent(
            id=str(uuid.uuid4()),
            type=ActivityType.DOCUMENT_EDIT,
            namespace=latest.namespace,
            user_id=latest.user_id,
            target_id=latest.target_id,
            target_type=latest.target_type,
            data={
                **latest.data,
                "edit_count": count,
                "total_characters_changed": total_chars,
                "duration": events[-1].timestamp - events[0].timestamp
            },
            room=latest.room,
            timestamp=latest.timestamp,
            priority=latest.priority
        )
    
    def _aggregate_presence_updates(self, events: List[ActivityEvent]) -> ActivityEvent:
        """Aggregate presence update events"""
        latest = events[-1]
        return latest  # Just use latest presence
    
    def _default_aggregation(self, events: List[ActivityEvent]) -> ActivityEvent:
        """Default aggregation for events without specific rules"""
        latest = events[-1]
        count = len(events)
        
        return ActivityEvent(
            id=str(uuid.uuid4()),
            type=latest.type,
            namespace=latest.namespace,
            user_id=latest.user_id,
            target_id=latest.target_id,
            target_type=latest.target_type,
            data={
                **latest.data,
                "aggregated_count": count,
                "duration": events[-1].timestamp - events[0].timestamp
            },
            room=latest.room,
            timestamp=latest.timestamp,
            priority=latest.priority
        )

class ActivityFeed:
    """Live activity feed with real-time updates and filtering"""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.events = deque(maxlen=max_events)
        self.namespace_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.user_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self.room_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Subscribers for real-time updates
        self.subscribers: Dict[str, Dict[str, Any]] = {}
        
        # Activity aggregator
        self.aggregator = ActivityAggregator()
        
        # Background tasks
        self.cleanup_task = None
        self.start_background_tasks()
    
    def start_background_tasks(self):
        """Start background tasks for cleanup and aggregation"""
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def add_activity(self, event: ActivityEvent):
        """Add a new activity event"""
        # Store in main feed
        self.events.append(event)
        
        # Store in namespace-specific feed
        self.namespace_events[event.namespace].append(event)
        
        # Store in user-specific feed
        self.user_events[event.user_id].append(event)
        
        # Store in room-specific feed if room specified
        if event.room:
            room_key = f"{event.namespace}:{event.room}"
            self.room_events[room_key].append(event)
        
        # Notify subscribers
        await self._notify_subscribers(event)
        
        logger.debug(f"Added activity: {event.type.value} by {event.user_id}")
    
    async def _notify_subscribers(self, event: ActivityEvent):
        """Notify subscribers of new activity"""
        tasks = []
        
        for sub_id, subscription in self.subscribers.items():
            if self._matches_subscription(event, subscription):
                callback = subscription.get("callback")
                if callback:
                    tasks.append(callback(event))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def _matches_subscription(self, event: ActivityEvent, subscription: Dict[str, Any]) -> bool:
        """Check if event matches subscription criteria"""
        criteria = subscription.get("criteria")
        if not criteria:
            return True
        
        # Check namespace filter
        if criteria.namespaces and event.namespace not in criteria.namespaces:
            return False
        
        # Check activity type filter
        if criteria.activity_types and event.type not in criteria.activity_types:
            return False
        
        # Check user filter
        if criteria.user_ids and event.user_id not in criteria.user_ids:
            return False
        
        # Check target type filter
        if criteria.target_types and event.target_type not in criteria.target_types:
            return False
        
        # Check room filter
        if criteria.rooms and event.room not in criteria.rooms:
            return False
        
        # Check timestamp range
        if criteria.since_timestamp and event.timestamp < criteria.since_timestamp:
            return False
        
        if criteria.until_timestamp and event.timestamp > criteria.until_timestamp:
            return False
        
        # Check priority range
        if event.priority < criteria.priority_min or event.priority > criteria.priority_max:
            return False
        
        return True
    
    def subscribe(self, subscriber_id: str, criteria: FilterCriteria, callback: Callable) -> bool:
        """Subscribe to activity feed updates"""
        self.subscribers[subscriber_id] = {
            "criteria": criteria,
            "callback": callback,
            "created_at": time.time()
        }
        
        logger.info(f"Added activity feed subscriber: {subscriber_id}")
        return True
    
    def unsubscribe(self, subscriber_id: str) -> bool:
        """Unsubscribe from activity feed updates"""
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
            logger.info(f"Removed activity feed subscriber: {subscriber_id}")
            return True
        return False
    
    def get_activities(self, criteria: FilterCriteria) -> List[ActivityEvent]:
        """Get activities matching criteria"""
        # Choose the most specific event source
        if len(criteria.namespaces) == 1 and not criteria.rooms and not criteria.user_ids:
            namespace = next(iter(criteria.namespaces))
            source_events = list(self.namespace_events[namespace])
        elif len(criteria.user_ids) == 1 and not criteria.rooms:
            user_id = next(iter(criteria.user_ids))
            source_events = list(self.user_events[user_id])
        elif len(criteria.rooms) == 1 and len(criteria.namespaces) == 1:
            namespace = next(iter(criteria.namespaces))
            room = next(iter(criteria.rooms))
            room_key = f"{namespace}:{room}"
            source_events = list(self.room_events[room_key])
        else:
            source_events = list(self.events)
        
        # Filter events
        filtered_events = []
        for event in reversed(source_events):  # Most recent first
            if self._matches_criteria(event, criteria):
                filtered_events.append(event)
            
            if len(filtered_events) >= criteria.max_results:
                break
        
        # Aggregate if needed
        if len(filtered_events) > criteria.max_results // 2:
            filtered_events = self.aggregator.aggregate_events(filtered_events)
        
        return filtered_events[:criteria.max_results]
    
    def _matches_criteria(self, event: ActivityEvent, criteria: FilterCriteria) -> bool:
        """Check if event matches filter criteria"""
        # Check namespace filter
        if criteria.namespaces and event.namespace not in criteria.namespaces:
            return False
        
        # Check activity type filter
        if criteria.activity_types and event.type not in criteria.activity_types:
            return False
        
        # Check user filter
        if criteria.user_ids and event.user_id not in criteria.user_ids:
            return False
        
        # Check target type filter
        if criteria.target_types and event.target_type not in criteria.target_types:
            return False
        
        # Check room filter
        if criteria.rooms and event.room not in criteria.rooms:
            return False
        
        # Check timestamp range
        if criteria.since_timestamp and event.timestamp < criteria.since_timestamp:
            return False
        
        if criteria.until_timestamp and event.timestamp > criteria.until_timestamp:
            return False
        
        # Check priority range
        if event.priority < criteria.priority_min or event.priority > criteria.priority_max:
            return False
        
        return True
    
    async def create_activity(self, activity_type: str, namespace: str, user_id: str, 
                            target_id: str = None, target_type: str = None, 
                            data: Dict[str, Any] = None, room: str = None, 
                            priority: int = 1) -> ActivityEvent:
        """Create and add a new activity event"""
        event = ActivityEvent(
            id=str(uuid.uuid4()),
            type=ActivityType(activity_type),
            namespace=namespace,
            user_id=user_id,
            target_id=target_id,
            target_type=target_type,
            data=data or {},
            room=room,
            priority=priority
        )
        
        await self.add_activity(event)
        return event
    
    def get_activity_stats(self) -> Dict[str, Any]:
        """Get activity feed statistics"""
        type_counts = defaultdict(int)
        namespace_counts = defaultdict(int)
        user_counts = defaultdict(int)
        
        for event in self.events:
            type_counts[event.type.value] += 1
            namespace_counts[event.namespace] += 1
            user_counts[event.user_id] += 1
        
        return {
            "total_events": len(self.events),
            "subscribers": len(self.subscribers),
            "activity_types": dict(type_counts),
            "namespaces": dict(namespace_counts),
            "top_users": dict(sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "events_by_namespace": {
                ns: len(events) for ns, events in self.namespace_events.items()
            },
            "events_by_room": {
                room: len(events) for room, events in self.room_events.items()
            }
        }
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old events and stale subscriptions"""
        while True:
            try:
                current_time = time.time()
                cleanup_threshold = current_time - 3600  # 1 hour
                
                # Clean up stale subscriptions
                stale_subscribers = []
                for sub_id, subscription in self.subscribers.items():
                    if current_time - subscription["created_at"] > 3600:  # 1 hour
                        stale_subscribers.append(sub_id)
                
                for sub_id in stale_subscribers:
                    del self.subscribers[sub_id]
                    logger.info(f"Cleaned up stale subscriber: {sub_id}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(300)
    
    def get_user_activity_summary(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get activity summary for a specific user"""
        since_timestamp = time.time() - (hours * 3600)
        user_events = list(self.user_events[user_id])
        
        recent_events = [
            event for event in user_events
            if event.timestamp >= since_timestamp
        ]
        
        activity_counts = defaultdict(int)
        target_types = defaultdict(int)
        hourly_activity = defaultdict(int)
        
        for event in recent_events:
            activity_counts[event.type.value] += 1
            if event.target_type:
                target_types[event.target_type] += 1
            
            hour = int((event.timestamp % 86400) // 3600)
            hourly_activity[hour] += 1
        
        return {
            "user_id": user_id,
            "total_activities": len(recent_events),
            "activity_types": dict(activity_counts),
            "target_types": dict(target_types),
            "hourly_distribution": dict(hourly_activity),
            "most_recent": recent_events[-1] if recent_events else None,
            "period_hours": hours
        }