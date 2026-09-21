"""
Event Streaming Hub
Creates event streaming infrastructure for real-time data flow
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import logging
import weakref
from collections import defaultdict, deque

import aioredis
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError
import websockets
from websockets.exceptions import ConnectionClosed

from ..models.streaming import (
    StreamEvent, StreamSubscription, EventType, 
    StreamMetrics, StreamPartition
)
from ..utils.config import Config

logger = logging.getLogger(__name__)


class StreamEventType(Enum):
    """Types of streaming events"""
    DATA_CHANGE = "data_change"
    SERVICE_STATUS = "service_status"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    BATCH_COMPLETE = "batch_complete"
    ERROR_OCCURRED = "error_occurred"
    HEALTH_CHECK = "health_check"


class DeliveryGuarantee(Enum):
    """Event delivery guarantees"""
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


@dataclass
class EventMessage:
    """Streaming event message"""
    event_id: str
    event_type: StreamEventType
    source_service: str
    target_services: List[str]
    timestamp: datetime
    payload: Dict[str, Any]
    metadata: Dict[str, Any]
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    version: str = "1.0"
    retry_count: int = 0
    max_retries: int = 3
    ttl_seconds: Optional[int] = None


@dataclass
class StreamConsumer:
    """Stream event consumer"""
    consumer_id: str
    service_name: str
    event_types: List[StreamEventType]
    callback: Callable
    is_active: bool
    last_processed: Optional[datetime]
    error_count: int
    processed_count: int
    websocket_connection: Optional[Any] = None


@dataclass
class StreamPartitionInfo:
    """Information about stream partition"""
    partition_id: str
    topic: str
    consumer_group: str
    offset: int
    lag: int
    last_update: datetime


class EventStreamingHub:
    """Central hub for event streaming across DMLog services"""
    
    def __init__(self, service_registry, redis_client, config: Config):
        self.service_registry = service_registry
        self.redis_client = redis_client
        self.config = config
        
        # Kafka configuration
        self.kafka_producer: Optional[AIOKafkaProducer] = None
        self.kafka_consumers: Dict[str, AIOKafkaConsumer] = {}
        self.kafka_topics = {
            'dmlog-events': 'dmlog.events',
            'dmlog-data-changes': 'dmlog.data.changes',
            'dmlog-system-events': 'dmlog.system.events',
            'dmlog-user-actions': 'dmlog.user.actions',
            'dmlog-service-status': 'dmlog.service.status',
            'dmlog-errors': 'dmlog.errors'
        }
        
        # WebSocket connections for real-time updates
        self.websocket_connections: Dict[str, Set[websockets.WebSocketServerProtocol]] = defaultdict(set)
        self.websocket_server = None
        
        # Event consumers and subscriptions
        self.consumers: Dict[str, StreamConsumer] = {}
        self.subscriptions: Dict[str, List[str]] = defaultdict(list)  # service -> consumer_ids
        
        # Event storage and replay
        self.event_store: deque = deque(maxlen=10000)  # Keep last 10k events
        self.event_snapshots: Dict[str, Any] = {}
        
        # Metrics and monitoring
        self.metrics = {
            'events_published': 0,
            'events_consumed': 0,
            'events_failed': 0,
            'consumer_errors': 0,
            'avg_processing_time': 0,
            'active_connections': 0
        }
        
        # Stream processing
        self.event_processors: Dict[str, Callable] = {}
        self.stream_transformers: Dict[str, Callable] = {}
        self.dead_letter_queue: deque = deque(maxlen=1000)
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()

    async def initialize(self):
        """Initialize the event streaming hub"""
        logger.info("Initializing Event Streaming Hub")
        
        try:
            # Initialize Kafka producer
            await self._initialize_kafka_producer()
            
            # Initialize Kafka consumers
            await self._initialize_kafka_consumers()
            
            # Create Kafka topics
            await self._create_kafka_topics()
            
            # Start WebSocket server
            await self._start_websocket_server()
            
            # Register default event processors
            self._register_default_processors()
            
            # Start background tasks
            self._start_background_tasks()
            
            # Subscribe to DMLog service events
            await self._subscribe_to_service_events()
            
            logger.info("Event Streaming Hub initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize event streaming hub: {e}")
            raise

    async def _initialize_kafka_producer(self):
        """Initialize Kafka producer"""
        try:
            self.kafka_producer = AIOKafkaProducer(
                bootstrap_servers=self.config.kafka.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                compression_type='gzip',
                acks='all',  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,
                enable_idempotence=True,
                batch_size=16384,
                linger_ms=10
            )
            
            await self.kafka_producer.start()
            logger.info("Kafka producer initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise

    async def _initialize_kafka_consumers(self):
        """Initialize Kafka consumers"""
        try:
            # Create consumers for each service
            for service in ['dmlog-core', 'dmlog-characters', 'dmlog-session', 'dmlog-ai-dm']:
                consumer = AIOKafkaConsumer(
                    *self.kafka_topics.values(),
                    bootstrap_servers=self.config.kafka.bootstrap_servers,
                    group_id=f'dmlog-{service}-consumer',
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    auto_commit_interval_ms=1000,
                    max_poll_records=100,
                    session_timeout_ms=30000,
                    heartbeat_interval_ms=10000
                )
                
                await consumer.start()
                self.kafka_consumers[service] = consumer
                
                # Start consumer task
                task = asyncio.create_task(self._kafka_consumer_loop(service, consumer))
                self._background_tasks.add(task)
            
            logger.info(f"Initialized {len(self.kafka_consumers)} Kafka consumers")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumers: {e}")
            raise

    async def _create_kafka_topics(self):
        """Create necessary Kafka topics"""
        # In production, topics should be created via Kafka admin tools
        # This is just for development/testing
        logger.info("Kafka topics should be created externally in production")

    async def _start_websocket_server(self):
        """Start WebSocket server for real-time connections"""
        try:
            async def websocket_handler(websocket, path):
                await self._handle_websocket_connection(websocket, path)
            
            # Start WebSocket server
            self.websocket_server = await websockets.serve(
                websocket_handler,
                "0.0.0.0",
                8205,  # WebSocket port
                ping_interval=20,
                ping_timeout=10,
                max_size=10 * 1024 * 1024  # 10MB max message size
            )
            
            logger.info("WebSocket server started on port 8205")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")

    async def _handle_websocket_connection(self, websocket, path):
        """Handle WebSocket connection"""
        connection_id = str(uuid.uuid4())
        service_name = path.strip('/') or 'default'
        
        try:
            # Add to connections
            self.websocket_connections[service_name].add(websocket)
            self.metrics['active_connections'] += 1
            
            logger.info(f"WebSocket connected: {connection_id} for service: {service_name}")
            
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'connection_established',
                'connection_id': connection_id,
                'service': service_name,
                'timestamp': datetime.now().isoformat()
            }))
            
            # Handle incoming messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_websocket_message(websocket, data, service_name)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid JSON format'
                    }))
        
        except ConnectionClosed:
            logger.info(f"WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Cleanup
            self.websocket_connections[service_name].discard(websocket)
            self.metrics['active_connections'] -= 1

    async def _handle_websocket_message(self, websocket, data: Dict[str, Any], service_name: str):
        """Handle incoming WebSocket message"""
        message_type = data.get('type', 'unknown')
        
        if message_type == 'subscribe':
            # Subscribe to event types
            event_types = data.get('event_types', [])
            consumer_id = str(uuid.uuid4())
            
            consumer = StreamConsumer(
                consumer_id=consumer_id,
                service_name=service_name,
                event_types=[StreamEventType(et) for et in event_types if et in StreamEventType.__members__],
                callback=lambda event: self._send_websocket_event(websocket, event),
                is_active=True,
                last_processed=None,
                error_count=0,
                processed_count=0,
                websocket_connection=websocket
            )
            
            self.consumers[consumer_id] = consumer
            self.subscriptions[service_name].append(consumer_id)
            
            await websocket.send(json.dumps({
                'type': 'subscription_confirmed',
                'consumer_id': consumer_id,
                'event_types': event_types
            }))
        
        elif message_type == 'publish_event':
            # Publish event from WebSocket client
            event_data = data.get('event', {})
            await self._publish_websocket_event(event_data, service_name)
        
        elif message_type == 'get_metrics':
            # Send current metrics
            await websocket.send(json.dumps({
                'type': 'metrics',
                'data': self.metrics
            }))

    async def _send_websocket_event(self, websocket, event: EventMessage):
        """Send event to WebSocket client"""
        try:
            await websocket.send(json.dumps({
                'type': 'event',
                'event_id': event.event_id,
                'event_type': event.event_type.value,
                'source_service': event.source_service,
                'timestamp': event.timestamp.isoformat(),
                'payload': event.payload,
                'metadata': event.metadata
            }))
        except Exception as e:
            logger.error(f"Failed to send WebSocket event: {e}")

    async def _publish_websocket_event(self, event_data: Dict[str, Any], source_service: str):
        """Publish event received from WebSocket"""
        try:
            event = EventMessage(
                event_id=str(uuid.uuid4()),
                event_type=StreamEventType(event_data.get('event_type', 'USER_ACTION')),
                source_service=source_service,
                target_services=event_data.get('target_services', []),
                timestamp=datetime.now(),
                payload=event_data.get('payload', {}),
                metadata=event_data.get('metadata', {}),
                correlation_id=event_data.get('correlation_id')
            )
            
            await self.publish_event(event)
            
        except Exception as e:
            logger.error(f"Failed to publish WebSocket event: {e}")

    def _register_default_processors(self):
        """Register default event processors"""
        
        # Data change processor
        self.event_processors['data_change'] = self._process_data_change_event
        
        # Service status processor
        self.event_processors['service_status'] = self._process_service_status_event
        
        # User action processor
        self.event_processors['user_action'] = self._process_user_action_event
        
        # System event processor
        self.event_processors['system_event'] = self._process_system_event
        
        # Error processor
        self.event_processors['error_occurred'] = self._process_error_event

    async def _process_data_change_event(self, event: EventMessage):
        """Process data change events"""
        logger.info(f"Processing data change event: {event.event_id}")
        
        # Update data lineage
        lineage_info = {
            'event_id': event.event_id,
            'source_service': event.source_service,
            'timestamp': event.timestamp,
            'entity': event.payload.get('entity'),
            'operation': event.payload.get('operation'),
            'affected_records': event.payload.get('affected_records', [])
        }
        
        # Store in Redis for lineage tracking
        await self.redis_client.lpush(
            f"lineage:{event.payload.get('entity', 'unknown')}", 
            json.dumps(lineage_info, default=str)
        )
        
        # Trigger dependent service updates
        await self._trigger_dependent_updates(event)

    async def _process_service_status_event(self, event: EventMessage):
        """Process service status events"""
        logger.info(f"Processing service status event: {event.event_id}")
        
        service_name = event.source_service
        status = event.payload.get('status', 'unknown')
        
        # Update service registry
        await self.service_registry.update_service_status(service_name, status)
        
        # Broadcast to all connected clients
        await self._broadcast_to_websockets('service_status', {
            'service': service_name,
            'status': status,
            'timestamp': event.timestamp.isoformat()
        })

    async def _process_user_action_event(self, event: EventMessage):
        """Process user action events"""
        logger.info(f"Processing user action event: {event.event_id}")
        
        # Log user action for analytics
        action_log = {
            'event_id': event.event_id,
            'user_id': event.payload.get('user_id'),
            'action': event.payload.get('action'),
            'service': event.source_service,
            'timestamp': event.timestamp,
            'session_id': event.metadata.get('session_id')
        }
        
        # Store in Redis for analytics
        await self.redis_client.lpush('user_actions', json.dumps(action_log, default=str))
        
        # Trigger real-time updates to other users
        await self._broadcast_user_action(event)

    async def _process_system_event(self, event: EventMessage):
        """Process system events"""
        logger.info(f"Processing system event: {event.event_id}")
        
        # Handle different system event types
        system_event_type = event.payload.get('system_event_type')
        
        if system_event_type == 'backup_completed':
            await self._handle_backup_completed(event)
        elif system_event_type == 'maintenance_started':
            await self._handle_maintenance_started(event)
        elif system_event_type == 'scale_event':
            await self._handle_scale_event(event)

    async def _process_error_event(self, event: EventMessage):
        """Process error events"""
        logger.error(f"Processing error event: {event.event_id}")
        
        # Store error for analysis
        error_info = {
            'event_id': event.event_id,
            'source_service': event.source_service,
            'error_type': event.payload.get('error_type'),
            'error_message': event.payload.get('error_message'),
            'stack_trace': event.payload.get('stack_trace'),
            'timestamp': event.timestamp
        }
        
        # Store in dead letter queue if critical
        if event.payload.get('severity') == 'critical':
            self.dead_letter_queue.append(error_info)
        
        # Alert monitoring systems
        await self._send_error_alert(error_info)

    def _start_background_tasks(self):
        """Start background processing tasks"""
        
        # Metrics collection task
        task1 = asyncio.create_task(self._metrics_collection_loop())
        self._background_tasks.add(task1)
        
        # Event cleanup task
        task2 = asyncio.create_task(self._event_cleanup_loop())
        self._background_tasks.add(task2)
        
        # Health check task
        task3 = asyncio.create_task(self._health_check_loop())
        self._background_tasks.add(task3)
        
        # Dead letter queue processor
        task4 = asyncio.create_task(self._dead_letter_queue_processor())
        self._background_tasks.add(task4)

    async def _kafka_consumer_loop(self, service: str, consumer: AIOKafkaConsumer):
        """Kafka consumer processing loop"""
        logger.info(f"Starting Kafka consumer loop for {service}")
        
        try:
            async for message in consumer:
                try:
                    # Deserialize event
                    event_data = message.value
                    event = EventMessage(
                        event_id=event_data.get('event_id'),
                        event_type=StreamEventType(event_data.get('event_type')),
                        source_service=event_data.get('source_service'),
                        target_services=event_data.get('target_services', []),
                        timestamp=datetime.fromisoformat(event_data.get('timestamp')),
                        payload=event_data.get('payload', {}),
                        metadata=event_data.get('metadata', {}),
                        correlation_id=event_data.get('correlation_id'),
                        version=event_data.get('version', '1.0')
                    )
                    
                    # Process event
                    await self._process_event(event)
                    
                    # Update metrics
                    self.metrics['events_consumed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing Kafka message: {e}")
                    self.metrics['events_failed'] += 1
                    
        except Exception as e:
            logger.error(f"Kafka consumer loop error for {service}: {e}")

    async def _process_event(self, event: EventMessage):
        """Process a single event"""
        start_time = datetime.now()
        
        try:
            # Add to event store
            self.event_store.append(event)
            
            # Get processor for event type
            processor = self.event_processors.get(event.event_type.value)
            
            if processor:
                await processor(event)
            else:
                logger.warning(f"No processor found for event type: {event.event_type.value}")
            
            # Notify consumers
            await self._notify_consumers(event)
            
            # Update processing time metric
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_avg_processing_time(processing_time)
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {e}")
            
            # Add to dead letter queue
            self.dead_letter_queue.append({
                'event': asdict(event),
                'error': str(e),
                'timestamp': datetime.now()
            })

    async def _notify_consumers(self, event: EventMessage):
        """Notify registered consumers about event"""
        for consumer in self.consumers.values():
            if not consumer.is_active:
                continue
            
            # Check if consumer is interested in this event type
            if event.event_type in consumer.event_types:
                try:
                    await consumer.callback(event)
                    consumer.processed_count += 1
                    consumer.last_processed = datetime.now()
                    
                except Exception as e:
                    logger.error(f"Consumer {consumer.consumer_id} failed to process event: {e}")
                    consumer.error_count += 1

    async def publish_event(self, event: EventMessage) -> str:
        """Publish event to the streaming infrastructure"""
        try:
            # Validate event
            if not event.event_id:
                event.event_id = str(uuid.uuid4())
            
            # Determine topic
            topic = self._get_topic_for_event(event.event_type)
            
            # Serialize event
            event_data = {
                'event_id': event.event_id,
                'event_type': event.event_type.value,
                'source_service': event.source_service,
                'target_services': event.target_services,
                'timestamp': event.timestamp.isoformat(),
                'payload': event.payload,
                'metadata': event.metadata,
                'correlation_id': event.correlation_id,
                'version': event.version
            }
            
            # Publish to Kafka
            if self.kafka_producer:
                await self.kafka_producer.send(topic, value=event_data)
            
            # Store in Redis for replay capability
            await self.redis_client.lpush(
                f"events:{event.source_service}",
                json.dumps(event_data, default=str)
            )
            
            # Update metrics
            self.metrics['events_published'] += 1
            
            logger.info(f"Published event: {event.event_id} to topic: {topic}")
            return event.event_id
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            self.metrics['events_failed'] += 1
            raise

    def _get_topic_for_event(self, event_type: StreamEventType) -> str:
        """Get appropriate Kafka topic for event type"""
        topic_mapping = {
            StreamEventType.DATA_CHANGE: self.kafka_topics['dmlog-data-changes'],
            StreamEventType.SERVICE_STATUS: self.kafka_topics['dmlog-service-status'],
            StreamEventType.USER_ACTION: self.kafka_topics['dmlog-user-actions'],
            StreamEventType.SYSTEM_EVENT: self.kafka_topics['dmlog-system-events'],
            StreamEventType.ERROR_OCCURRED: self.kafka_topics['dmlog-errors']
        }
        
        return topic_mapping.get(event_type, self.kafka_topics['dmlog-events'])

    async def subscribe_to_events(self, consumer: StreamConsumer) -> str:
        """Subscribe a consumer to events"""
        self.consumers[consumer.consumer_id] = consumer
        self.subscriptions[consumer.service_name].append(consumer.consumer_id)
        
        logger.info(f"Subscribed consumer {consumer.consumer_id} from {consumer.service_name}")
        return consumer.consumer_id

    async def unsubscribe_from_events(self, consumer_id: str):
        """Unsubscribe a consumer from events"""
        if consumer_id in self.consumers:
            consumer = self.consumers[consumer_id]
            consumer.is_active = False
            
            self.subscriptions[consumer.service_name].remove(consumer_id)
            del self.consumers[consumer_id]
            
            logger.info(f"Unsubscribed consumer {consumer_id}")

    async def _subscribe_to_service_events(self):
        """Subscribe to events from all DMLog services"""
        for service in ['dmlog-core', 'dmlog-characters', 'dmlog-session', 'dmlog-ai-dm']:
            consumer = StreamConsumer(
                consumer_id=f"orchestrator-{service}-consumer",
                service_name="data-orchestrator",
                event_types=list(StreamEventType),
                callback=self._handle_service_event,
                is_active=True,
                last_processed=None,
                error_count=0,
                processed_count=0
            )
            
            await self.subscribe_to_events(consumer)

    async def _handle_service_event(self, event: EventMessage):
        """Handle events from DMLog services"""
        logger.info(f"Handling service event: {event.event_id} from {event.source_service}")
        
        # Process based on event type
        if event.event_type == StreamEventType.DATA_CHANGE:
            # Trigger ETL pipelines that depend on this data
            await self._trigger_dependent_etl_pipelines(event)
        
        elif event.event_type == StreamEventType.SERVICE_STATUS:
            # Update service health status
            await self._update_service_health(event)

    async def _trigger_dependent_etl_pipelines(self, event: EventMessage):
        """Trigger ETL pipelines that depend on changed data"""
        # This would integrate with the ETL Pipeline Manager
        # For now, just log the trigger
        logger.info(f"Would trigger ETL pipelines for data change: {event.payload.get('entity')}")

    async def _broadcast_to_websockets(self, event_type: str, data: Dict[str, Any]):
        """Broadcast message to all WebSocket connections"""
        message = json.dumps({
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
        disconnected = set()
        
        for service, connections in self.websocket_connections.items():
            for websocket in connections.copy():
                try:
                    await websocket.send(message)
                except Exception:
                    disconnected.add((service, websocket))
        
        # Clean up disconnected websockets
        for service, websocket in disconnected:
            self.websocket_connections[service].discard(websocket)

    async def _metrics_collection_loop(self):
        """Background metrics collection"""
        while True:
            try:
                # Collect additional metrics
                self.metrics['active_consumers'] = len([c for c in self.consumers.values() if c.is_active])
                self.metrics['dead_letter_count'] = len(self.dead_letter_queue)
                self.metrics['event_store_size'] = len(self.event_store)
                
                await asyncio.sleep(60)  # Collect every minute
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(60)

    async def _event_cleanup_loop(self):
        """Background event cleanup"""
        while True:
            try:
                # Clean up old events from Redis
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                for service in self.service_registry.get_all_services():
                    # Keep only events from last 24 hours
                    key = f"events:{service}"
                    # Implementation would clean up old events
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                logger.error(f"Event cleanup error: {e}")
                await asyncio.sleep(3600)

    async def _health_check_loop(self):
        """Background health monitoring"""
        while True:
            try:
                # Publish health check event
                health_event = EventMessage(
                    event_id=str(uuid.uuid4()),
                    event_type=StreamEventType.HEALTH_CHECK,
                    source_service="data-orchestrator",
                    target_services=[],
                    timestamp=datetime.now(),
                    payload={
                        'component': 'event_streaming_hub',
                        'status': 'healthy',
                        'metrics': self.metrics
                    },
                    metadata={}
                )
                
                await self.publish_event(health_event)
                
                await asyncio.sleep(300)  # Health check every 5 minutes
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(300)

    async def _dead_letter_queue_processor(self):
        """Process dead letter queue"""
        while True:
            try:
                if self.dead_letter_queue:
                    failed_event = self.dead_letter_queue.popleft()
                    
                    # Try to reprocess or alert
                    logger.warning(f"Processing dead letter: {failed_event}")
                    
                    # In production, this might send to monitoring system
                
                await asyncio.sleep(30)  # Process every 30 seconds
                
            except Exception as e:
                logger.error(f"Dead letter queue processor error: {e}")
                await asyncio.sleep(30)

    def _update_avg_processing_time(self, processing_time: float):
        """Update average processing time metric"""
        current_avg = self.metrics['avg_processing_time']
        total_processed = self.metrics['events_consumed']
        
        if total_processed > 0:
            self.metrics['avg_processing_time'] = (
                (current_avg * (total_processed - 1) + processing_time) / total_processed
            )

    async def monitor_stream_health(self):
        """Monitor streaming infrastructure health"""
        health_status = {
            'kafka_producer_healthy': self.kafka_producer is not None,
            'kafka_consumers_healthy': len(self.kafka_consumers),
            'websocket_connections': self.metrics['active_connections'],
            'active_consumers': len([c for c in self.consumers.values() if c.is_active]),
            'events_in_store': len(self.event_store),
            'dead_letter_count': len(self.dead_letter_queue)
        }
        
        return health_status

    async def get_stream_metrics(self) -> Dict[str, Any]:
        """Get comprehensive streaming metrics"""
        return {
            **self.metrics,
            'kafka_topics': list(self.kafka_topics.values()),
            'consumer_stats': {
                consumer_id: {
                    'service': consumer.service_name,
                    'processed_count': consumer.processed_count,
                    'error_count': consumer.error_count,
                    'last_processed': consumer.last_processed.isoformat() if consumer.last_processed else None
                }
                for consumer_id, consumer in self.consumers.items()
            },
            'websocket_connections': {
                service: len(connections) 
                for service, connections in self.websocket_connections.items()
            }
        }

    async def cleanup(self):
        """Cleanup streaming hub resources"""
        logger.info("Cleaning up Event Streaming Hub")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Close Kafka producer
        if self.kafka_producer:
            await self.kafka_producer.stop()
        
        # Close Kafka consumers
        for consumer in self.kafka_consumers.values():
            await consumer.stop()
        
        # Close WebSocket server
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        logger.info("Event Streaming Hub cleanup complete")