"""
Real-time Bot Synchronization and Coordination System
Provides synchronization mechanisms for multi-bot collaborative tasks
"""

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Optional, Callable, Any, Union
import json
import sqlite3
from datetime import datetime, timedelta
import weakref


class SynchronizationBarrierType(Enum):
    """Types of synchronization barriers"""
    PHASE_TRANSITION = "phase_transition"
    CHECKPOINT = "checkpoint"
    MILESTONE = "milestone"
    DECISION_POINT = "decision_point"
    RESOURCE_ACCESS = "resource_access"
    TERMINATION = "termination"


class CoordinationMode(Enum):
    """Bot coordination modes"""
    STRICT = "strict"  # All bots must proceed together
    FLEXIBLE = "flexible"  # Bots can proceed with majority
    LEADER_FOLLOWER = "leader_follower"  # Leader decides for group
    AUTONOMOUS = "autonomous"  # Bots coordinate but work independently


class SynchronizationState(Enum):
    """States for synchronization points"""
    WAITING = "waiting"
    READY = "ready"
    PROCEEDING = "proceeding"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class SynchronizationBarrier:
    """Represents a synchronization point where bots must coordinate"""
    barrier_id: str
    barrier_type: SynchronizationBarrierType
    required_bots: Set[str]
    coordination_mode: CoordinationMode
    timeout_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.now)
    ready_bots: Set[str] = field(default_factory=set)
    state: SynchronizationState = SynchronizationState.WAITING
    metadata: Dict[str, Any] = field(default_factory=dict)
    completion_callback: Optional[Callable] = None


@dataclass
class BotSyncState:
    """Tracks synchronization state for individual bots"""
    bot_id: str
    current_barriers: Set[str] = field(default_factory=set)
    completed_barriers: Set[str] = field(default_factory=set)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    sync_data: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class SharedResource:
    """Represents a shared resource that requires coordination"""
    resource_id: str
    resource_type: str
    max_concurrent_access: int
    current_holders: Set[str] = field(default_factory=set)
    wait_queue: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoordinationEvent:
    """Events in the coordination timeline"""
    event_id: str
    event_type: str
    timestamp: datetime
    bot_id: str
    barrier_id: Optional[str] = None
    resource_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


class BotSynchronizer:
    """Real-time synchronization and coordination system for multi-bot collaboration"""
    
    def __init__(self, db_path: str = "/home/activeloguser/activelog/data/bot_synchronization.db"):
        self.db_path = db_path
        self.barriers: Dict[str, SynchronizationBarrier] = {}
        self.bot_states: Dict[str, BotSyncState] = {}
        self.shared_resources: Dict[str, SharedResource] = {}
        self.coordination_events: List[CoordinationEvent] = []
        self.event_listeners: Dict[str, List[Callable]] = {}
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 90  # seconds
        self.sync_lock = threading.RLock()
        self._running = False
        self._heartbeat_task = None
        self._cleanup_task = None
        
        # Initialize database
        self._init_database()
        
        # Start background tasks
        self.start_background_tasks()
    
    def _init_database(self):
        """Initialize SQLite database for persistence"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS barriers (
                    barrier_id TEXT PRIMARY KEY,
                    barrier_type TEXT NOT NULL,
                    required_bots TEXT NOT NULL,
                    coordination_mode TEXT NOT NULL,
                    timeout_seconds INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    ready_bots TEXT NOT NULL,
                    state TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_states (
                    bot_id TEXT PRIMARY KEY,
                    current_barriers TEXT NOT NULL,
                    completed_barriers TEXT NOT NULL,
                    last_heartbeat TEXT NOT NULL,
                    sync_data TEXT,
                    is_active BOOLEAN NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shared_resources (
                    resource_id TEXT PRIMARY KEY,
                    resource_type TEXT NOT NULL,
                    max_concurrent_access INTEGER NOT NULL,
                    current_holders TEXT NOT NULL,
                    wait_queue TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coordination_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    bot_id TEXT NOT NULL,
                    barrier_id TEXT,
                    resource_id TEXT,
                    data TEXT
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_barriers_state ON barriers(state)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON coordination_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_bot_id ON coordination_events(bot_id)")
    
    def start_background_tasks(self):
        """Start background synchronization tasks"""
        if not self._running:
            self._running = True
            self._heartbeat_task = threading.Thread(target=self._heartbeat_monitor, daemon=True)
            self._cleanup_task = threading.Thread(target=self._cleanup_monitor, daemon=True)
            self._heartbeat_task.start()
            self._cleanup_task.start()
    
    def stop_background_tasks(self):
        """Stop background tasks"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.join(timeout=5)
        if self._cleanup_task:
            self._cleanup_task.join(timeout=5)
    
    def _heartbeat_monitor(self):
        """Monitor bot heartbeats and handle timeouts"""
        while self._running:
            try:
                current_time = datetime.now()
                timeout_threshold = current_time - timedelta(seconds=self.heartbeat_timeout)
                
                with self.sync_lock:
                    inactive_bots = []
                    for bot_id, bot_state in self.bot_states.items():
                        if bot_state.last_heartbeat < timeout_threshold and bot_state.is_active:
                            inactive_bots.append(bot_id)
                            bot_state.is_active = False
                            self._record_event("bot_timeout", bot_id, data={"timeout_threshold": timeout_threshold.isoformat()})
                    
                    # Handle inactive bots in barriers
                    for bot_id in inactive_bots:
                        self._handle_bot_timeout(bot_id)
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                print(f"Error in heartbeat monitor: {e}")
                time.sleep(self.heartbeat_interval)
    
    def _cleanup_monitor(self):
        """Clean up completed barriers and old events"""
        while self._running:
            try:
                current_time = datetime.now()
                cleanup_threshold = current_time - timedelta(hours=24)
                
                with self.sync_lock:
                    # Clean up completed barriers older than threshold
                    completed_barriers = [
                        barrier_id for barrier_id, barrier in self.barriers.items()
                        if barrier.state in [SynchronizationState.COMPLETED, SynchronizationState.FAILED, SynchronizationState.TIMEOUT]
                        and barrier.created_at < cleanup_threshold
                    ]
                    
                    for barrier_id in completed_barriers:
                        del self.barriers[barrier_id]
                    
                    # Clean up old events
                    self.coordination_events = [
                        event for event in self.coordination_events
                        if event.timestamp > cleanup_threshold
                    ]
                
                # Sleep for 1 hour between cleanup cycles
                time.sleep(3600)
                
            except Exception as e:
                print(f"Error in cleanup monitor: {e}")
                time.sleep(3600)
    
    def register_bot(self, bot_id: str, sync_data: Optional[Dict[str, Any]] = None) -> bool:
        """Register a bot for synchronization"""
        with self.sync_lock:
            if bot_id not in self.bot_states:
                self.bot_states[bot_id] = BotSyncState(
                    bot_id=bot_id,
                    sync_data=sync_data or {}
                )
            else:
                # Reactivate existing bot
                self.bot_states[bot_id].is_active = True
                self.bot_states[bot_id].last_heartbeat = datetime.now()
                if sync_data:
                    self.bot_states[bot_id].sync_data.update(sync_data)
            
            self._record_event("bot_registered", bot_id)
            self._persist_bot_state(bot_id)
            return True
    
    def unregister_bot(self, bot_id: str) -> bool:
        """Unregister a bot from synchronization"""
        with self.sync_lock:
            if bot_id in self.bot_states:
                self.bot_states[bot_id].is_active = False
                self._handle_bot_timeout(bot_id)
                self._record_event("bot_unregistered", bot_id)
                self._persist_bot_state(bot_id)
                return True
            return False
    
    def heartbeat(self, bot_id: str, sync_data: Optional[Dict[str, Any]] = None) -> bool:
        """Update bot heartbeat and sync data"""
        with self.sync_lock:
            if bot_id in self.bot_states:
                self.bot_states[bot_id].last_heartbeat = datetime.now()
                self.bot_states[bot_id].is_active = True
                if sync_data:
                    self.bot_states[bot_id].sync_data.update(sync_data)
                self._persist_bot_state(bot_id)
                return True
            return False
    
    def create_barrier(
        self,
        barrier_type: SynchronizationBarrierType,
        required_bots: Set[str],
        coordination_mode: CoordinationMode = CoordinationMode.STRICT,
        timeout_seconds: int = 300,
        metadata: Optional[Dict[str, Any]] = None,
        completion_callback: Optional[Callable] = None
    ) -> str:
        """Create a synchronization barrier"""
        barrier_id = str(uuid.uuid4())
        
        with self.sync_lock:
            barrier = SynchronizationBarrier(
                barrier_id=barrier_id,
                barrier_type=barrier_type,
                required_bots=required_bots.copy(),
                coordination_mode=coordination_mode,
                timeout_seconds=timeout_seconds,
                metadata=metadata or {},
                completion_callback=completion_callback
            )
            
            self.barriers[barrier_id] = barrier
            
            # Add barrier to relevant bot states
            for bot_id in required_bots:
                if bot_id in self.bot_states:
                    self.bot_states[bot_id].current_barriers.add(barrier_id)
                    self._persist_bot_state(bot_id)
            
            self._record_event("barrier_created", "", barrier_id=barrier_id, data={"coordination_mode": coordination_mode.value})
            self._persist_barrier(barrier_id)
            
            # Start timeout timer
            threading.Timer(timeout_seconds, self._handle_barrier_timeout, [barrier_id]).start()
            
            return barrier_id
    
    def signal_barrier_ready(self, bot_id: str, barrier_id: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Signal that a bot is ready at a synchronization barrier"""
        with self.sync_lock:
            if barrier_id not in self.barriers or bot_id not in self.bot_states:
                return False
            
            barrier = self.barriers[barrier_id]
            if barrier.state != SynchronizationState.WAITING:
                return False
            
            if bot_id not in barrier.required_bots:
                return False
            
            # Mark bot as ready
            barrier.ready_bots.add(bot_id)
            if data:
                barrier.metadata[f"bot_data_{bot_id}"] = data
            
            self._record_event("barrier_ready", bot_id, barrier_id=barrier_id, data=data or {})
            
            # Check if barrier can proceed
            self._evaluate_barrier_readiness(barrier_id)
            
            self._persist_barrier(barrier_id)
            return True
    
    def _evaluate_barrier_readiness(self, barrier_id: str):
        """Evaluate if a barrier is ready to proceed"""
        barrier = self.barriers[barrier_id]
        active_required_bots = {
            bot_id for bot_id in barrier.required_bots
            if bot_id in self.bot_states and self.bot_states[bot_id].is_active
        }
        
        can_proceed = False
        
        if barrier.coordination_mode == CoordinationMode.STRICT:
            can_proceed = barrier.ready_bots >= active_required_bots
        elif barrier.coordination_mode == CoordinationMode.FLEXIBLE:
            can_proceed = len(barrier.ready_bots) >= len(active_required_bots) * 0.7  # 70% threshold
        elif barrier.coordination_mode == CoordinationMode.LEADER_FOLLOWER:
            # Check if leader is ready (assume first bot is leader)
            leader_id = next(iter(barrier.required_bots), None)
            can_proceed = leader_id in barrier.ready_bots
        elif barrier.coordination_mode == CoordinationMode.AUTONOMOUS:
            can_proceed = len(barrier.ready_bots) > 0  # Any bot can trigger
        
        if can_proceed and barrier.state == SynchronizationState.WAITING:
            barrier.state = SynchronizationState.PROCEEDING
            self._record_event("barrier_proceeding", "", barrier_id=barrier_id)
            
            # Move barrier from current to completed for ready bots
            for bot_id in barrier.ready_bots:
                if bot_id in self.bot_states:
                    self.bot_states[bot_id].current_barriers.discard(barrier_id)
                    self.bot_states[bot_id].completed_barriers.add(barrier_id)
                    self._persist_bot_state(bot_id)
            
            # Execute completion callback
            if barrier.completion_callback:
                try:
                    barrier.completion_callback(barrier)
                except Exception as e:
                    print(f"Error in barrier completion callback: {e}")
            
            # Notify listeners
            self._notify_listeners("barrier_ready", {"barrier_id": barrier_id, "barrier": barrier})
            
            barrier.state = SynchronizationState.COMPLETED
            self._record_event("barrier_completed", "", barrier_id=barrier_id)
    
    def _handle_barrier_timeout(self, barrier_id: str):
        """Handle barrier timeout"""
        with self.sync_lock:
            if barrier_id in self.barriers:
                barrier = self.barriers[barrier_id]
                if barrier.state == SynchronizationState.WAITING:
                    barrier.state = SynchronizationState.TIMEOUT
                    self._record_event("barrier_timeout", "", barrier_id=barrier_id)
                    
                    # Remove barrier from bot states
                    for bot_id in barrier.required_bots:
                        if bot_id in self.bot_states:
                            self.bot_states[bot_id].current_barriers.discard(barrier_id)
                            self._persist_bot_state(bot_id)
                    
                    self._persist_barrier(barrier_id)
    
    def _handle_bot_timeout(self, bot_id: str):
        """Handle bot timeout by updating barriers"""
        for barrier_id in list(self.bot_states[bot_id].current_barriers):
            if barrier_id in self.barriers:
                barrier = self.barriers[barrier_id]
                barrier.ready_bots.discard(bot_id)
                # Re-evaluate barrier with remaining active bots
                self._evaluate_barrier_readiness(barrier_id)
    
    def acquire_resource(self, bot_id: str, resource_id: str, resource_type: str, max_concurrent: int = 1) -> bool:
        """Acquire access to a shared resource"""
        with self.sync_lock:
            if resource_id not in self.shared_resources:
                self.shared_resources[resource_id] = SharedResource(
                    resource_id=resource_id,
                    resource_type=resource_type,
                    max_concurrent_access=max_concurrent
                )
            
            resource = self.shared_resources[resource_id]
            
            if len(resource.current_holders) < resource.max_concurrent_access:
                resource.current_holders.add(bot_id)
                self._record_event("resource_acquired", bot_id, resource_id=resource_id)
                self._persist_resource(resource_id)
                return True
            else:
                if bot_id not in resource.wait_queue:
                    resource.wait_queue.append(bot_id)
                    self._record_event("resource_queued", bot_id, resource_id=resource_id)
                    self._persist_resource(resource_id)
                return False
    
    def release_resource(self, bot_id: str, resource_id: str) -> bool:
        """Release access to a shared resource"""
        with self.sync_lock:
            if resource_id not in self.shared_resources:
                return False
            
            resource = self.shared_resources[resource_id]
            if bot_id not in resource.current_holders:
                return False
            
            resource.current_holders.remove(bot_id)
            self._record_event("resource_released", bot_id, resource_id=resource_id)
            
            # Grant access to next in queue
            if resource.wait_queue:
                next_bot = resource.wait_queue.pop(0)
                if next_bot in self.bot_states and self.bot_states[next_bot].is_active:
                    resource.current_holders.add(next_bot)
                    self._record_event("resource_granted", next_bot, resource_id=resource_id)
                    self._notify_listeners("resource_granted", {"bot_id": next_bot, "resource_id": resource_id})
            
            self._persist_resource(resource_id)
            return True
    
    def get_synchronization_status(self) -> Dict[str, Any]:
        """Get current synchronization status"""
        with self.sync_lock:
            return {
                "active_bots": len([b for b in self.bot_states.values() if b.is_active]),
                "total_bots": len(self.bot_states),
                "active_barriers": len([b for b in self.barriers.values() if b.state == SynchronizationState.WAITING]),
                "completed_barriers": len([b for b in self.barriers.values() if b.state == SynchronizationState.COMPLETED]),
                "shared_resources": len(self.shared_resources),
                "recent_events": len(self.coordination_events[-100:])
            }
    
    def get_bot_status(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get status for a specific bot"""
        with self.sync_lock:
            if bot_id not in self.bot_states:
                return None
            
            bot_state = self.bot_states[bot_id]
            return {
                "bot_id": bot_id,
                "is_active": bot_state.is_active,
                "last_heartbeat": bot_state.last_heartbeat.isoformat(),
                "current_barriers": len(bot_state.current_barriers),
                "completed_barriers": len(bot_state.completed_barriers),
                "sync_data": bot_state.sync_data
            }
    
    def add_event_listener(self, event_type: str, callback: Callable):
        """Add event listener for coordination events"""
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        self.event_listeners[event_type].append(callback)
    
    def remove_event_listener(self, event_type: str, callback: Callable):
        """Remove event listener"""
        if event_type in self.event_listeners:
            self.event_listeners[event_type] = [
                cb for cb in self.event_listeners[event_type] if cb != callback
            ]
    
    def _notify_listeners(self, event_type: str, data: Dict[str, Any]):
        """Notify event listeners"""
        if event_type in self.event_listeners:
            for callback in self.event_listeners[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in event listener: {e}")
    
    def _record_event(self, event_type: str, bot_id: str, barrier_id: Optional[str] = None, 
                     resource_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """Record coordination event"""
        event = CoordinationEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            bot_id=bot_id,
            barrier_id=barrier_id,
            resource_id=resource_id,
            data=data or {}
        )
        
        self.coordination_events.append(event)
        self._persist_event(event)
    
    def _persist_barrier(self, barrier_id: str):
        """Persist barrier to database"""
        barrier = self.barriers[barrier_id]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO barriers 
                (barrier_id, barrier_type, required_bots, coordination_mode, timeout_seconds, 
                 created_at, ready_bots, state, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                barrier.barrier_id,
                barrier.barrier_type.value,
                json.dumps(list(barrier.required_bots)),
                barrier.coordination_mode.value,
                barrier.timeout_seconds,
                barrier.created_at.isoformat(),
                json.dumps(list(barrier.ready_bots)),
                barrier.state.value,
                json.dumps(barrier.metadata)
            ))
    
    def _persist_bot_state(self, bot_id: str):
        """Persist bot state to database"""
        bot_state = self.bot_states[bot_id]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO bot_states 
                (bot_id, current_barriers, completed_barriers, last_heartbeat, sync_data, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                bot_state.bot_id,
                json.dumps(list(bot_state.current_barriers)),
                json.dumps(list(bot_state.completed_barriers)),
                bot_state.last_heartbeat.isoformat(),
                json.dumps(bot_state.sync_data),
                bot_state.is_active
            ))
    
    def _persist_resource(self, resource_id: str):
        """Persist shared resource to database"""
        resource = self.shared_resources[resource_id]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO shared_resources 
                (resource_id, resource_type, max_concurrent_access, current_holders, wait_queue, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                resource.resource_id,
                resource.resource_type,
                resource.max_concurrent_access,
                json.dumps(list(resource.current_holders)),
                json.dumps(resource.wait_queue),
                json.dumps(resource.metadata)
            ))
    
    def _persist_event(self, event: CoordinationEvent):
        """Persist coordination event to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO coordination_events 
                (event_id, event_type, timestamp, bot_id, barrier_id, resource_id, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.event_type,
                event.timestamp.isoformat(),
                event.bot_id,
                event.barrier_id,
                event.resource_id,
                json.dumps(event.data)
            ))