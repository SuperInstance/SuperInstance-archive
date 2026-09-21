#!/usr/bin/env python3
"""
ActiveLog Real-Time Event System - Event Replay & Persistence
Handles event persistence and replay for missed messages
"""

import asyncio
import json
import time
import uuid
import sqlite3
import threading
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import logging
import gzip
import pickle

logger = logging.getLogger(__name__)

class EventPersistenceLevel(Enum):
    """Event persistence levels"""
    NONE = "none"           # No persistence
    MEMORY = "memory"       # In-memory only 
    DISK = "disk"           # Persist to disk
    COMPRESSED = "compressed"  # Compressed persistence

@dataclass
class PersistedEvent:
    """Event stored for replay"""
    id: str
    type: str
    namespace: str
    room: Optional[str]
    user_id: Optional[str]
    data: Dict[str, Any]
    timestamp: float
    sequence_number: int
    persistence_level: EventPersistenceLevel
    compressed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": self.type,
            "namespace": self.namespace,
            "room": self.room,
            "user_id": self.user_id,
            "data": self.data,
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number
        }

@dataclass
class ReplayRequest:
    """Request for event replay"""
    user_id: str
    namespaces: Set[str] = None
    rooms: Set[str] = None
    event_types: Set[str] = None
    since_timestamp: float = 0
    since_sequence: int = 0
    limit: int = 1000
    include_own_events: bool = False
    
    def __post_init__(self):
        if self.namespaces is None:
            self.namespaces = set()
        if self.rooms is None:
            self.rooms = set()
        if self.event_types is None:
            self.event_types = set()

class EventPersistence:
    """High-performance event persistence and replay system"""
    
    def __init__(self, db_path: str = "events.db", max_memory_events: int = 100000):
        self.db_path = db_path
        self.max_memory_events = max_memory_events
        
        # Sequence counter for ordering
        self.sequence_counter = 0
        self.sequence_lock = threading.Lock()
        
        # In-memory event storage for fast access
        self.memory_events = deque(maxlen=max_memory_events)
        self.namespace_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.room_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5000))
        self.user_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Event type indexes for fast filtering
        self.type_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        
        # User subscriptions for selective persistence
        self.user_subscriptions: Dict[str, ReplayRequest] = {}
        
        # Database connection pool
        self.db_lock = threading.Lock()
        self._init_database()
        
        # Compression settings
        self.compression_threshold = 1024  # Compress events larger than 1KB
        
        # Background tasks
        self.persistence_task = None
        self.cleanup_task = None
        self.start_background_tasks()
        
        # Statistics
        self.stats = {
            "events_stored": 0,
            "events_compressed": 0,
            "replay_requests": 0,
            "events_replayed": 0,
            "disk_writes": 0,
            "compression_ratio": 0.0
        }
    
    def _init_database(self):
        """Initialize SQLite database for persistent storage"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            
            # Main events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    sequence_number INTEGER PRIMARY KEY,
                    id TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    room TEXT,
                    user_id TEXT,
                    data BLOB,
                    timestamp REAL NOT NULL,
                    compressed BOOLEAN DEFAULT FALSE,
                    INDEX(namespace),
                    INDEX(room),
                    INDEX(user_id),
                    INDEX(type),
                    INDEX(timestamp)
                )
            """)
            
            # User subscriptions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    user_id TEXT PRIMARY KEY,
                    namespaces TEXT,
                    rooms TEXT,
                    event_types TEXT,
                    last_sequence INTEGER DEFAULT 0,
                    created_at REAL NOT NULL
                )
            """)
            
            # Event replay log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS replay_log (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    request_data TEXT,
                    events_returned INTEGER,
                    timestamp REAL NOT NULL,
                    INDEX(user_id),
                    INDEX(timestamp)
                )
            """)
            
            conn.commit()
            conn.close()
            
        logger.info("Event persistence database initialized")
    
    def start_background_tasks(self):
        """Start background tasks"""
        if not self.persistence_task:
            self.persistence_task = asyncio.create_task(self._background_persistence())
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_old_events())
    
    def _get_next_sequence(self) -> int:
        """Get next sequence number"""
        with self.sequence_lock:
            self.sequence_counter += 1
            return self.sequence_counter
    
    async def store_event(self, event_id: str, event_type: str, namespace: str,
                         data: Dict[str, Any], user_id: str = None, room: str = None,
                         persistence_level: EventPersistenceLevel = EventPersistenceLevel.MEMORY) -> int:
        """Store an event for potential replay"""
        sequence_number = self._get_next_sequence()
        
        # Create persisted event
        persisted_event = PersistedEvent(
            id=event_id,
            type=event_type,
            namespace=namespace,
            room=room,
            user_id=user_id,
            data=data,
            timestamp=time.time(),
            sequence_number=sequence_number,
            persistence_level=persistence_level
        )
        
        # Store in memory structures
        self.memory_events.append(persisted_event)
        self.namespace_events[namespace].append(persisted_event)
        self.type_events[event_type].append(persisted_event)
        
        if room:
            room_key = f"{namespace}:{room}"
            self.room_events[room_key].append(persisted_event)
        
        if user_id:
            self.user_events[user_id].append(persisted_event)
        
        # Persist to disk if required
        if persistence_level in [EventPersistenceLevel.DISK, EventPersistenceLevel.COMPRESSED]:
            await self._persist_to_disk(persisted_event)
        
        self.stats["events_stored"] += 1
        logger.debug(f"Stored event {event_id} with sequence {sequence_number}")
        
        return sequence_number
    
    async def _persist_to_disk(self, event: PersistedEvent):
        """Persist event to disk storage"""
        def _db_insert():
            # Serialize data
            if event.persistence_level == EventPersistenceLevel.COMPRESSED:
                # Compress data if it's large enough
                data_str = json.dumps(event.data)
                if len(data_str) > self.compression_threshold:
                    data_blob = gzip.compress(data_str.encode('utf-8'))
                    event.compressed = True
                    self.stats["events_compressed"] += 1
                else:
                    data_blob = data_str.encode('utf-8')
            else:
                data_blob = json.dumps(event.data).encode('utf-8')
            
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT OR REPLACE INTO events 
                    (sequence_number, id, type, namespace, room, user_id, data, timestamp, compressed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.sequence_number, event.id, event.type, event.namespace,
                    event.room, event.user_id, data_blob, event.timestamp, event.compressed
                ))
                conn.commit()
                conn.close()
                
            self.stats["disk_writes"] += 1
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _db_insert)
    
    async def replay_events(self, request: ReplayRequest) -> List[Dict[str, Any]]:
        """Replay events for a user based on request criteria"""
        self.stats["replay_requests"] += 1
        
        # Try memory first for recent events
        memory_events = self._get_memory_events(request)
        
        # If we need more events or older events, query disk
        disk_events = []
        if len(memory_events) < request.limit or request.since_timestamp > 0:
            disk_events = await self._get_disk_events(request)
        
        # Merge and deduplicate events
        all_events = self._merge_events(memory_events, disk_events, request.limit)
        
        # Log replay request
        await self._log_replay_request(request, len(all_events))
        
        self.stats["events_replayed"] += len(all_events)
        logger.info(f"Replayed {len(all_events)} events for user {request.user_id}")
        
        return [event.to_dict() for event in all_events]
    
    def _get_memory_events(self, request: ReplayRequest) -> List[PersistedEvent]:
        """Get events from memory based on request"""
        events = []
        
        # Determine source based on filters
        if len(request.namespaces) == 1 and not request.rooms:
            namespace = next(iter(request.namespaces))
            source_events = list(self.namespace_events[namespace])
        elif len(request.rooms) == 1 and len(request.namespaces) == 1:
            namespace = next(iter(request.namespaces))
            room = next(iter(request.rooms))
            room_key = f"{namespace}:{room}"
            source_events = list(self.room_events[room_key])
        elif len(request.event_types) == 1:
            event_type = next(iter(request.event_types))
            source_events = list(self.type_events[event_type])
        else:
            source_events = list(self.memory_events)
        
        # Filter events
        for event in reversed(source_events):  # Most recent first
            if self._matches_request(event, request):
                events.append(event)
                
            if len(events) >= request.limit:
                break
        
        return events
    
    async def _get_disk_events(self, request: ReplayRequest) -> List[PersistedEvent]:
        """Get events from disk storage"""
        def _db_query():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                
                # Build query
                where_clauses = []
                params = []
                
                if request.namespaces:
                    placeholders = ",".join(["?" for _ in request.namespaces])
                    where_clauses.append(f"namespace IN ({placeholders})")
                    params.extend(request.namespaces)
                
                if request.rooms:
                    placeholders = ",".join(["?" for _ in request.rooms])
                    where_clauses.append(f"room IN ({placeholders})")
                    params.extend(request.rooms)
                
                if request.event_types:
                    placeholders = ",".join(["?" for _ in request.event_types])
                    where_clauses.append(f"type IN ({placeholders})")
                    params.extend(request.event_types)
                
                if request.since_timestamp:
                    where_clauses.append("timestamp >= ?")
                    params.append(request.since_timestamp)
                
                if request.since_sequence:
                    where_clauses.append("sequence_number > ?")
                    params.append(request.since_sequence)
                
                if not request.include_own_events:
                    where_clauses.append("user_id != ? OR user_id IS NULL")
                    params.append(request.user_id)
                
                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                query = f"""
                    SELECT sequence_number, id, type, namespace, room, user_id, data, timestamp, compressed
                    FROM events 
                    WHERE {where_clause}
                    ORDER BY sequence_number DESC
                    LIMIT ?
                """
                params.append(request.limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                conn.close()
                
                return rows
        
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, _db_query)
        
        events = []
        for row in rows:
            # Deserialize data
            data_blob = row[6]
            compressed = row[8]
            
            if compressed:
                data_str = gzip.decompress(data_blob).decode('utf-8')
            else:
                data_str = data_blob.decode('utf-8')
            
            data = json.loads(data_str)
            
            event = PersistedEvent(
                sequence_number=row[0],
                id=row[1],
                type=row[2],
                namespace=row[3],
                room=row[4],
                user_id=row[5],
                data=data,
                timestamp=row[7],
                persistence_level=EventPersistenceLevel.DISK,
                compressed=compressed
            )
            events.append(event)
        
        return events
    
    def _matches_request(self, event: PersistedEvent, request: ReplayRequest) -> bool:
        """Check if event matches replay request criteria"""
        # Check namespace filter
        if request.namespaces and event.namespace not in request.namespaces:
            return False
        
        # Check room filter
        if request.rooms and event.room not in request.rooms:
            return False
        
        # Check event type filter
        if request.event_types and event.type not in request.event_types:
            return False
        
        # Check timestamp filter
        if request.since_timestamp and event.timestamp < request.since_timestamp:
            return False
        
        # Check sequence filter
        if request.since_sequence and event.sequence_number <= request.since_sequence:
            return False
        
        # Check if should include own events
        if not request.include_own_events and event.user_id == request.user_id:
            return False
        
        return True
    
    def _merge_events(self, memory_events: List[PersistedEvent], 
                     disk_events: List[PersistedEvent], limit: int) -> List[PersistedEvent]:
        """Merge memory and disk events, removing duplicates"""
        # Use set to track seen events
        seen_ids = set()
        merged = []
        
        # Combine and sort by sequence number (descending)
        all_events = sorted(
            memory_events + disk_events,
            key=lambda x: x.sequence_number,
            reverse=True
        )
        
        for event in all_events:
            if event.id not in seen_ids:
                seen_ids.add(event.id)
                merged.append(event)
                
                if len(merged) >= limit:
                    break
        
        return merged
    
    async def _log_replay_request(self, request: ReplayRequest, events_returned: int):
        """Log replay request for analytics"""
        def _db_insert():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT INTO replay_log 
                    (id, user_id, request_data, events_returned, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    request.user_id,
                    json.dumps(asdict(request), default=lambda x: list(x) if isinstance(x, set) else x),
                    events_returned,
                    time.time()
                ))
                conn.commit()
                conn.close()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _db_insert)
    
    async def subscribe_user(self, user_id: str, subscription: ReplayRequest):
        """Subscribe user for selective event persistence"""
        self.user_subscriptions[user_id] = subscription
        
        # Persist subscription
        def _db_upsert():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT OR REPLACE INTO user_subscriptions 
                    (user_id, namespaces, rooms, event_types, last_sequence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    json.dumps(list(subscription.namespaces)),
                    json.dumps(list(subscription.rooms)),
                    json.dumps(list(subscription.event_types)),
                    subscription.since_sequence,
                    time.time()
                ))
                conn.commit()
                conn.close()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _db_upsert)
        
        logger.info(f"User {user_id} subscribed for event replay")
    
    async def get_user_missed_events(self, user_id: str, since_sequence: int = 0) -> List[Dict[str, Any]]:
        """Get events missed by user since last seen sequence"""
        subscription = self.user_subscriptions.get(user_id)
        if not subscription:
            return []
        
        # Update request with since_sequence
        request = ReplayRequest(
            user_id=user_id,
            namespaces=subscription.namespaces,
            rooms=subscription.rooms,
            event_types=subscription.event_types,
            since_sequence=since_sequence,
            limit=subscription.limit,
            include_own_events=subscription.include_own_events
        )
        
        return await self.replay_events(request)
    
    async def _background_persistence(self):
        """Background task for batch persistence"""
        while True:
            try:
                # This could implement batch writing for better performance
                await asyncio.sleep(10)  # Run every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in background persistence: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_old_events(self):
        """Background task to clean up old events"""
        while True:
            try:
                current_time = time.time()
                
                def _db_cleanup():
                    with self.db_lock:
                        conn = sqlite3.connect(self.db_path)
                        
                        # Delete events older than 30 days
                        cutoff = current_time - (30 * 86400)
                        conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
                        
                        # Delete old replay logs (keep for 7 days)
                        log_cutoff = current_time - (7 * 86400)
                        conn.execute("DELETE FROM replay_log WHERE timestamp < ?", (log_cutoff,))
                        
                        deleted = conn.total_changes
                        conn.commit()
                        conn.close()
                        
                        return deleted
                
                loop = asyncio.get_event_loop()
                deleted = await loop.run_in_executor(None, _db_cleanup)
                
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old events")
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get persistence statistics"""
        memory_usage = {
            "total_events": len(self.memory_events),
            "namespace_events": {ns: len(events) for ns, events in self.namespace_events.items()},
            "room_events": {room: len(events) for room, events in self.room_events.items()},
            "type_events": {event_type: len(events) for event_type, events in self.type_events.items()}
        }
        
        return {
            **self.stats,
            "current_sequence": self.sequence_counter,
            "subscribed_users": len(self.user_subscriptions),
            "memory_usage": memory_usage
        }