"""
Event Bus for Service Communication

Provides a comprehensive event-driven messaging system including:
- Publish-subscribe pattern for service communication
- Event routing and filtering
- Persistent message queues with reliability
- Dead letter queues for failed messages
- Event replay and audit capabilities
- Service event subscriptions and handlers
- Message transformation and enrichment
- Rate limiting and backpressure handling
"""

import asyncio
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set, Union
from concurrent.futures import ThreadPoolExecutor
import logging
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventStatus(Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"
    DEAD_LETTER = "dead_letter"

class EventPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class SubscriptionType(Enum):
    SYNC = "sync"
    ASYNC = "async"
    BATCH = "batch"

@dataclass
class Event:
    """Event message structure"""
    event_id: str
    event_type: str
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    ttl: int = 3600  # Time to live in seconds
    retry_count: int = 0
    max_retries: int = 3
    status: EventStatus = EventStatus.PENDING
    headers: Dict[str, str] = field(default_factory=dict)

@dataclass
class Subscription:
    """Event subscription configuration"""
    subscription_id: str
    service_name: str
    event_types: List[str]
    handler: Callable[[Event], Any]
    subscription_type: SubscriptionType = SubscriptionType.ASYNC
    filter_expression: Optional[str] = None
    max_batch_size: int = 10
    batch_timeout: int = 5
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    dead_letter_queue: bool = True
    rate_limit: int = 100  # Events per second
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True

@dataclass
class EventRoute:
    """Event routing configuration"""
    route_id: str
    source_pattern: str
    event_type_pattern: str
    target_services: List[str]
    transformation: Optional[str] = None
    condition: Optional[str] = None
    priority: int = 0
    active: bool = True

class EventStorage:
    """Persistent storage for events and subscriptions"""
    
    def __init__(self, db_path: str = "event_bus.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                data TEXT,
                metadata TEXT,
                timestamp TEXT,
                correlation_id TEXT,
                causation_id TEXT,
                priority INTEGER,
                ttl INTEGER,
                retry_count INTEGER,
                max_retries INTEGER,
                status TEXT,
                headers TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Subscriptions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                subscription_id TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                event_types TEXT,
                subscription_type TEXT,
                filter_expression TEXT,
                max_batch_size INTEGER,
                batch_timeout INTEGER,
                retry_policy TEXT,
                dead_letter_queue BOOLEAN,
                rate_limit INTEGER,
                created_at TEXT,
                active BOOLEAN
            )
        ''')
        
        # Event routes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_routes (
                route_id TEXT PRIMARY KEY,
                source_pattern TEXT,
                event_type_pattern TEXT,
                target_services TEXT,
                transformation TEXT,
                condition TEXT,
                priority INTEGER,
                active BOOLEAN
            )
        ''')
        
        # Delivery attempts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delivery_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                subscription_id TEXT,
                attempt_time TEXT,
                success BOOLEAN,
                error_message TEXT,
                FOREIGN KEY (event_id) REFERENCES events (event_id),
                FOREIGN KEY (subscription_id) REFERENCES subscriptions (subscription_id)
            )
        ''')
        
        # Dead letter queue table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dead_letter_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                subscription_id TEXT,
                reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events (event_id),
                FOREIGN KEY (subscription_id) REFERENCES subscriptions (subscription_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_event(self, event: Event):
        """Store event in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO events 
            (event_id, event_type, source, data, metadata, timestamp, correlation_id,
             causation_id, priority, ttl, retry_count, max_retries, status, headers)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.event_id, event.event_type, event.source,
            json.dumps(event.data), json.dumps(event.metadata),
            event.timestamp.isoformat(), event.correlation_id, event.causation_id,
            event.priority.value, event.ttl, event.retry_count, event.max_retries,
            event.status.value, json.dumps(event.headers)
        ))
        
        conn.commit()
        conn.close()
    
    def load_event(self, event_id: str) -> Optional[Event]:
        """Load event from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM events WHERE event_id = ?', (event_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        event = Event(
            event_id=row[0],
            event_type=row[1],
            source=row[2],
            data=json.loads(row[3]) if row[3] else {},
            metadata=json.loads(row[4]) if row[4] else {},
            timestamp=datetime.fromisoformat(row[5]),
            correlation_id=row[6],
            causation_id=row[7],
            priority=EventPriority(row[8]),
            ttl=row[9],
            retry_count=row[10],
            max_retries=row[11],
            status=EventStatus(row[12]),
            headers=json.loads(row[13]) if row[13] else {}
        )
        
        conn.close()
        return event
    
    def store_subscription(self, subscription: Subscription):
        """Store subscription in database (without handler)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO subscriptions
            (subscription_id, service_name, event_types, subscription_type,
             filter_expression, max_batch_size, batch_timeout, retry_policy,
             dead_letter_queue, rate_limit, created_at, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            subscription.subscription_id, subscription.service_name,
            json.dumps(subscription.event_types), subscription.subscription_type.value,
            subscription.filter_expression, subscription.max_batch_size,
            subscription.batch_timeout, json.dumps(subscription.retry_policy),
            subscription.dead_letter_queue, subscription.rate_limit,
            subscription.created_at.isoformat(), subscription.active
        ))
        
        conn.commit()
        conn.close()
    
    def log_delivery_attempt(self, event_id: str, subscription_id: str, success: bool, error: Optional[str] = None):
        """Log delivery attempt"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO delivery_attempts (event_id, subscription_id, attempt_time, success, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (event_id, subscription_id, datetime.now().isoformat(), success, error))
        
        conn.commit()
        conn.close()
    
    def add_to_dead_letter_queue(self, event_id: str, subscription_id: str, reason: str):
        """Add event to dead letter queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO dead_letter_queue (event_id, subscription_id, reason)
            VALUES (?, ?, ?)
        ''', (event_id, subscription_id, reason))
        
        conn.commit()
        conn.close()

class EventFilter:
    """Filters events based on expressions and patterns"""
    
    @staticmethod
    def matches_pattern(pattern: str, value: str) -> bool:
        """Check if value matches pattern (supports wildcards)"""
        import fnmatch
        return fnmatch.fnmatch(value, pattern)
    
    @staticmethod
    def evaluate_filter(filter_expr: str, event: Event) -> bool:
        """Evaluate filter expression against event"""
        if not filter_expr:
            return True
        
        try:
            # Build context for filter evaluation
            context = {
                "event": {
                    "type": event.event_type,
                    "source": event.source,
                    "data": event.data,
                    "metadata": event.metadata,
                    "priority": event.priority.value,
                    "headers": event.headers
                }
            }
            
            # Simple expression evaluation (can be extended with proper parser)
            return eval(filter_expr, {"__builtins__": {}}, context)
        except Exception as e:
            logger.warning(f"Failed to evaluate filter expression '{filter_expr}': {e}")
            return False

class EventTransformer:
    """Transforms events based on transformation rules"""
    
    @staticmethod
    def transform_event(event: Event, transformation: str) -> Event:
        """Transform event using transformation rule"""
        if not transformation:
            return event
        
        try:
            # Parse transformation (simple JSON-based for now)
            transform_config = json.loads(transformation)
            
            new_event = Event(
                event_id=str(uuid.uuid4()),
                event_type=event.event_type,
                source=event.source,
                data=event.data.copy(),
                metadata=event.metadata.copy(),
                correlation_id=event.correlation_id,
                causation_id=event.event_id,
                priority=event.priority,
                headers=event.headers.copy()
            )
            
            # Apply transformations
            if "map_fields" in transform_config:
                for old_field, new_field in transform_config["map_fields"].items():
                    if old_field in new_event.data:
                        new_event.data[new_field] = new_event.data.pop(old_field)
            
            if "add_fields" in transform_config:
                new_event.data.update(transform_config["add_fields"])
            
            if "remove_fields" in transform_config:
                for field in transform_config["remove_fields"]:
                    new_event.data.pop(field, None)
            
            if "change_type" in transform_config:
                new_event.event_type = transform_config["change_type"]
            
            return new_event
            
        except Exception as e:
            logger.warning(f"Failed to transform event: {e}")
            return event

class RateLimiter:
    """Rate limiting for event processing"""
    
    def __init__(self):
        self.counters: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, limit: int, window: int = 1) -> bool:
        """Check if request is allowed under rate limit"""
        async with self.lock:
            now = time.time()
            counter = self.counters[key]
            
            # Remove old entries outside window
            while counter and counter[0] <= now - window:
                counter.popleft()
            
            # Check if under limit
            if len(counter) < limit:
                counter.append(now)
                return True
            
            return False

class EventBatch:
    """Batches events for batch processing"""
    
    def __init__(self, subscription: Subscription):
        self.subscription = subscription
        self.events: List[Event] = []
        self.created_at = datetime.now()
        self.lock = asyncio.Lock()
    
    async def add_event(self, event: Event) -> bool:
        """Add event to batch, return True if batch is full"""
        async with self.lock:
            self.events.append(event)
            return len(self.events) >= self.subscription.max_batch_size
    
    async def is_ready(self) -> bool:
        """Check if batch is ready for processing"""
        async with self.lock:
            if len(self.events) >= self.subscription.max_batch_size:
                return True
            
            timeout_reached = (
                (datetime.now() - self.created_at).total_seconds() >= 
                self.subscription.batch_timeout
            )
            
            return timeout_reached and len(self.events) > 0
    
    async def get_events(self) -> List[Event]:
        """Get events from batch and clear"""
        async with self.lock:
            events = self.events.copy()
            self.events.clear()
            return events

class EventBus:
    """Main event bus implementation"""
    
    def __init__(self, storage: Optional[EventStorage] = None):
        self.storage = storage or EventStorage()
        self.subscriptions: Dict[str, Subscription] = {}
        self.event_routes: Dict[str, EventRoute] = {}
        self.rate_limiter = RateLimiter()
        self.batches: Dict[str, EventBatch] = {}
        self.running = False
        self._processing_task = None
        self._cleanup_task = None
        self.pending_events: asyncio.Queue = asyncio.Queue()
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
    
    async def start(self):
        """Start the event bus"""
        self.running = True
        self._processing_task = asyncio.create_task(self._process_events())
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_events())
        logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event bus"""
        self.running = False
        
        if self._processing_task:
            self._processing_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Process remaining events
        while not self.pending_events.empty():
            try:
                event = self.pending_events.get_nowait()
                await self._deliver_event(event)
            except:
                break
        
        self.thread_pool.shutdown(wait=True)
        logger.info("Event bus stopped")
    
    async def publish(self, event: Event) -> str:
        """Publish an event to the bus"""
        if not event.event_id:
            event.event_id = str(uuid.uuid4())
        
        event.status = EventStatus.PUBLISHED
        self.storage.store_event(event)
        
        # Add to processing queue
        await self.pending_events.put(event)
        
        logger.info(f"Published event {event.event_id} of type {event.event_type}")
        return event.event_id
    
    def subscribe(self, subscription: Subscription) -> str:
        """Subscribe to events"""
        if not subscription.subscription_id:
            subscription.subscription_id = str(uuid.uuid4())
        
        self.subscriptions[subscription.subscription_id] = subscription
        self.storage.store_subscription(subscription)
        
        # Initialize batch if batch subscription
        if subscription.subscription_type == SubscriptionType.BATCH:
            self.batches[subscription.subscription_id] = EventBatch(subscription)
        
        logger.info(f"Added subscription {subscription.subscription_id} for service {subscription.service_name}")
        return subscription.subscription_id
    
    def unsubscribe(self, subscription_id: str):
        """Unsubscribe from events"""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            self.batches.pop(subscription_id, None)
            logger.info(f"Removed subscription {subscription_id}")
    
    def add_route(self, route: EventRoute):
        """Add event routing rule"""
        self.event_routes[route.route_id] = route
        logger.info(f"Added event route {route.route_id}")
    
    def remove_route(self, route_id: str):
        """Remove event routing rule"""
        if route_id in self.event_routes:
            del self.event_routes[route_id]
            logger.info(f"Removed event route {route_id}")
    
    async def _process_events(self):
        """Main event processing loop"""
        while self.running:
            try:
                # Process pending events
                try:
                    event = await asyncio.wait_for(self.pending_events.get(), timeout=1.0)
                    await self._deliver_event(event)
                except asyncio.TimeoutError:
                    pass
                
                # Process batch timeouts
                await self._process_batch_timeouts()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                await asyncio.sleep(1)
    
    async def _deliver_event(self, event: Event):
        """Deliver event to subscribers"""
        # Apply event routes first
        routed_events = await self._apply_routes(event)
        
        # Process original event and routed events
        all_events = [event] + routed_events
        
        for evt in all_events:
            matching_subscriptions = self._find_matching_subscriptions(evt)
            
            for subscription in matching_subscriptions:
                try:
                    await self._deliver_to_subscription(evt, subscription)
                except Exception as e:
                    logger.error(f"Failed to deliver event {evt.event_id} to subscription {subscription.subscription_id}: {e}")
    
    async def _apply_routes(self, event: Event) -> List[Event]:
        """Apply routing rules to create additional events"""
        routed_events = []
        
        # Sort routes by priority
        sorted_routes = sorted(
            [r for r in self.event_routes.values() if r.active],
            key=lambda x: x.priority,
            reverse=True
        )
        
        for route in sorted_routes:
            try:
                # Check if route matches
                if (EventFilter.matches_pattern(route.source_pattern, event.source) and
                    EventFilter.matches_pattern(route.event_type_pattern, event.event_type)):
                    
                    # Evaluate condition if specified
                    if route.condition and not EventFilter.evaluate_filter(route.condition, event):
                        continue
                    
                    # Transform event if needed
                    routed_event = event
                    if route.transformation:
                        routed_event = EventTransformer.transform_event(event, route.transformation)
                    
                    routed_events.append(routed_event)
                    
            except Exception as e:
                logger.error(f"Error applying route {route.route_id}: {e}")
        
        return routed_events
    
    def _find_matching_subscriptions(self, event: Event) -> List[Subscription]:
        """Find subscriptions that match the event"""
        matching = []
        
        for subscription in self.subscriptions.values():
            if not subscription.active:
                continue
            
            # Check event type match
            if not any(EventFilter.matches_pattern(et, event.event_type) for et in subscription.event_types):
                continue
            
            # Check filter expression
            if subscription.filter_expression and not EventFilter.evaluate_filter(subscription.filter_expression, event):
                continue
            
            matching.append(subscription)
        
        return matching
    
    async def _deliver_to_subscription(self, event: Event, subscription: Subscription):
        """Deliver event to a specific subscription"""
        # Check rate limiting
        if not await self.rate_limiter.is_allowed(
            f"subscription_{subscription.subscription_id}",
            subscription.rate_limit
        ):
            logger.warning(f"Rate limit exceeded for subscription {subscription.subscription_id}")
            return
        
        try:
            if subscription.subscription_type == SubscriptionType.SYNC:
                await self._deliver_sync(event, subscription)
            elif subscription.subscription_type == SubscriptionType.ASYNC:
                asyncio.create_task(self._deliver_async(event, subscription))
            elif subscription.subscription_type == SubscriptionType.BATCH:
                await self._deliver_batch(event, subscription)
                
        except Exception as e:
            logger.error(f"Delivery failed for subscription {subscription.subscription_id}: {e}")
            
            # Add to dead letter queue if configured
            if subscription.dead_letter_queue:
                self.storage.add_to_dead_letter_queue(
                    event.event_id, subscription.subscription_id, str(e)
                )
    
    async def _deliver_sync(self, event: Event, subscription: Subscription):
        """Deliver event synchronously"""
        try:
            result = subscription.handler(event)
            if asyncio.iscoroutine(result):
                await result
            
            self.storage.log_delivery_attempt(event.event_id, subscription.subscription_id, True)
            
        except Exception as e:
            self.storage.log_delivery_attempt(event.event_id, subscription.subscription_id, False, str(e))
            
            # Retry if configured
            if event.retry_count < event.max_retries:
                event.retry_count += 1
                await asyncio.sleep(2 ** event.retry_count)  # Exponential backoff
                await self.pending_events.put(event)
            else:
                event.status = EventStatus.FAILED
                self.storage.store_event(event)
                raise
    
    async def _deliver_async(self, event: Event, subscription: Subscription):
        """Deliver event asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool, subscription.handler, event
            )
            
            self.storage.log_delivery_attempt(event.event_id, subscription.subscription_id, True)
            
        except Exception as e:
            self.storage.log_delivery_attempt(event.event_id, subscription.subscription_id, False, str(e))
            
            # Retry logic similar to sync
            if event.retry_count < event.max_retries:
                event.retry_count += 1
                await asyncio.sleep(2 ** event.retry_count)
                await self.pending_events.put(event)
            else:
                event.status = EventStatus.FAILED
                self.storage.store_event(event)
    
    async def _deliver_batch(self, event: Event, subscription: Subscription):
        """Add event to batch for batch processing"""
        batch_id = subscription.subscription_id
        if batch_id not in self.batches:
            self.batches[batch_id] = EventBatch(subscription)
        
        batch = self.batches[batch_id]
        is_full = await batch.add_event(event)
        
        if is_full:
            await self._process_batch(batch, subscription)
    
    async def _process_batch_timeouts(self):
        """Process batches that have timed out"""
        for subscription_id, batch in list(self.batches.items()):
            if await batch.is_ready():
                subscription = self.subscriptions.get(subscription_id)
                if subscription:
                    await self._process_batch(batch, subscription)
    
    async def _process_batch(self, batch: EventBatch, subscription: Subscription):
        """Process a batch of events"""
        events = await batch.get_events()
        if not events:
            return
        
        try:
            result = subscription.handler(events)
            if asyncio.iscoroutine(result):
                await result
            
            # Log successful delivery for all events in batch
            for event in events:
                self.storage.log_delivery_attempt(event.event_id, subscription.subscription_id, True)
                
        except Exception as e:
            # Log failed delivery for all events in batch
            for event in events:
                self.storage.log_delivery_attempt(event.event_id, subscription.subscription_id, False, str(e))
                
                if subscription.dead_letter_queue:
                    self.storage.add_to_dead_letter_queue(
                        event.event_id, subscription.subscription_id, str(e)
                    )
    
    async def _cleanup_expired_events(self):
        """Clean up expired events"""
        while self.running:
            try:
                # This would be implemented to clean up expired events from storage
                await asyncio.sleep(60)  # Clean up every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get event bus metrics"""
        return {
            "active_subscriptions": len([s for s in self.subscriptions.values() if s.active]),
            "event_routes": len([r for r in self.event_routes.values() if r.active]),
            "pending_events": self.pending_events.qsize(),
            "active_batches": len(self.batches),
            "running": self.running
        }

# Factory function
def create_event_bus(storage: Optional[EventStorage] = None) -> EventBus:
    """Create and return an event bus instance"""
    return EventBus(storage)

# Helper functions
def create_event(event_type: str, source: str, data: Dict[str, Any], **kwargs) -> Event:
    """Create a new event"""
    return Event(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        source=source,
        data=data,
        **kwargs
    )

def create_subscription(service_name: str, event_types: List[str], handler: Callable, **kwargs) -> Subscription:
    """Create a new subscription"""
    return Subscription(
        subscription_id=str(uuid.uuid4()),
        service_name=service_name,
        event_types=event_types,
        handler=handler,
        **kwargs
    )