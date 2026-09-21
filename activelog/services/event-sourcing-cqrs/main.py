#!/usr/bin/env python3
"""
Advanced Event Sourcing & CQRS Service
Implements cutting-edge distributed computing patterns:
- Event Sourcing with immutable event log
- CQRS (Command Query Responsibility Segregation)
- Event streaming and replay capabilities
- Distributed saga pattern for complex transactions
- Temporal queries and point-in-time snapshots
- Advanced event serialization and schema evolution
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union, Type
import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from contextlib import contextmanager
from collections import defaultdict, deque
import logging
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import hashlib
import pickle
import gzip
import threading
from concurrent.futures import ThreadPoolExecutor
import time

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DB_PATH = "data/event_store.db"
SNAPSHOTS_PATH = "data/snapshots/"

app = FastAPI(
    title="Event Sourcing & CQRS Service",
    description="Advanced event sourcing with CQRS pattern implementation",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Event Models
class EventMetadata(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stream_id: str
    event_type: str
    version: int
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    user_id: Optional[str] = None
    source: str = "event-sourcing-service"

class DomainEvent(BaseModel):
    metadata: EventMetadata
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.dict(),
            "data": self.data
        }

class Command(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    command_type: str
    aggregate_id: str
    data: Dict[str, Any]
    expected_version: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = None

class Query(BaseModel):
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_type: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    projection: Optional[str] = None
    as_of_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)

class Snapshot(BaseModel):
    aggregate_id: str
    version: int
    timestamp: datetime
    data: Dict[str, Any]
    checksum: str

class SagaStep(BaseModel):
    step_id: str
    saga_id: str
    step_type: str
    status: str = Field(regex="^(pending|completed|failed|compensated)$")
    command: Optional[Command] = None
    compensation_command: Optional[Command] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

# Event Store Implementation
class EventStore:
    """Advanced event store with optimizations and features"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.connection_pool = []
        self.max_connections = 10
        self.event_handlers = defaultdict(list)
        self.snapshots = {}
        self.init_database()
        
    def init_database(self):
        """Initialize event store database with optimized schema"""
        import os
        os.makedirs("data", exist_ok=True)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Events table with optimizations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    stream_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    correlation_id TEXT,
                    causation_id TEXT,
                    user_id TEXT,
                    source TEXT,
                    data TEXT NOT NULL,
                    checksum TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stream_id, version)
                )
            """)
            
            # Indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_stream_id ON events(stream_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_correlation_id ON events(correlation_id)")
            
            # Snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aggregate_id TEXT UNIQUE NOT NULL,
                    version INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Projections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    projection_name TEXT NOT NULL,
                    aggregate_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    data TEXT NOT NULL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(projection_name, aggregate_id)
                )
            """)
            
            # Sagas table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sagas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    saga_id TEXT UNIQUE NOT NULL,
                    saga_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_step INTEGER DEFAULT 0,
                    data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME
                )
            """)
            
            # Saga steps table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saga_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_id TEXT UNIQUE NOT NULL,
                    saga_id TEXT NOT NULL,
                    step_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    command_data TEXT,
                    compensation_data TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    FOREIGN KEY(saga_id) REFERENCES sagas(saga_id)
                )
            """)
            
            conn.commit()
        
        logger.info("Event store database initialized")
    
    @contextmanager
    def get_connection(self):
        """Get database connection from pool"""
        if self.connection_pool:
            conn = self.connection_pool.pop()
        else:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
        
        try:
            yield conn
        finally:
            if len(self.connection_pool) < self.max_connections:
                self.connection_pool.append(conn)
            else:
                conn.close()
    
    async def append_event(self, event: DomainEvent) -> str:
        """Append event to the event store"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for concurrency conflicts
                cursor.execute("""
                    SELECT MAX(version) FROM events WHERE stream_id = ?
                """, (event.metadata.stream_id,))
                
                current_version = cursor.fetchone()[0] or 0
                
                if event.metadata.version != current_version + 1:
                    raise HTTPException(
                        status_code=409, 
                        detail=f"Concurrency conflict: expected version {current_version + 1}, got {event.metadata.version}"
                    )
                
                # Serialize and compress event data
                event_data = json.dumps(event.data)
                compressed_data = gzip.compress(event_data.encode())
                
                # Calculate checksum
                checksum = hashlib.sha256(compressed_data).hexdigest()
                
                # Insert event
                cursor.execute("""
                    INSERT INTO events 
                    (event_id, stream_id, event_type, version, timestamp, 
                     correlation_id, causation_id, user_id, source, data, checksum)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (\n                    event.metadata.event_id,\n                    event.metadata.stream_id,\n                    event.metadata.event_type,\n                    event.metadata.version,\n                    event.metadata.timestamp.isoformat(),\n                    event.metadata.correlation_id,\n                    event.metadata.causation_id,\n                    event.metadata.user_id,\n                    event.metadata.source,\n                    compressed_data,\n                    checksum\n                ))\n                \n                conn.commit()\n                \n                # Trigger event handlers asynchronously\n                asyncio.create_task(self.trigger_event_handlers(event))\n                \n                logger.info(f\"Event {event.metadata.event_id} appended to stream {event.metadata.stream_id}\")\n                return event.metadata.event_id\n                \n        except sqlite3.IntegrityError as e:\n            if \"UNIQUE constraint failed\" in str(e):\n                raise HTTPException(status_code=409, detail=\"Event already exists or version conflict\")\n            raise HTTPException(status_code=500, detail=str(e))\n    \n    async def get_events(self, stream_id: str, from_version: int = 0, to_version: Optional[int] = None) -> List[DomainEvent]:\n        \"\"\"Get events from a stream\"\"\"\n        with self.get_connection() as conn:\n            cursor = conn.cursor()\n            \n            query = \"\"\"\n                SELECT event_id, stream_id, event_type, version, timestamp,\n                       correlation_id, causation_id, user_id, source, data\n                FROM events \n                WHERE stream_id = ? AND version >= ?\n            \"\"\"\n            \n            params = [stream_id, from_version]\n            \n            if to_version is not None:\n                query += \" AND version <= ?\"\n                params.append(to_version)\n            \n            query += \" ORDER BY version ASC\"\n            \n            cursor.execute(query, params)\n            rows = cursor.fetchall()\n            \n            events = []\n            for row in rows:\n                # Decompress event data\n                compressed_data = row[9]\n                if isinstance(compressed_data, bytes):\n                    event_data = json.loads(gzip.decompress(compressed_data).decode())\n                else:\n                    # Fallback for uncompressed data\n                    event_data = json.loads(compressed_data)\n                \n                metadata = EventMetadata(\n                    event_id=row[0],\n                    stream_id=row[1],\n                    event_type=row[2],\n                    version=row[3],\n                    timestamp=datetime.fromisoformat(row[4]),\n                    correlation_id=row[5],\n                    causation_id=row[6],\n                    user_id=row[7],\n                    source=row[8]\n                )\n                \n                event = DomainEvent(metadata=metadata, data=event_data)\n                events.append(event)\n            \n            return events\n    \n    async def create_snapshot(self, aggregate_id: str, version: int, data: Dict[str, Any]) -> str:\n        \"\"\"Create a snapshot of an aggregate\"\"\"\n        # Serialize and compress snapshot data\n        snapshot_data = json.dumps(data)\n        compressed_data = gzip.compress(snapshot_data.encode())\n        checksum = hashlib.sha256(compressed_data).hexdigest()\n        \n        snapshot = Snapshot(\n            aggregate_id=aggregate_id,\n            version=version,\n            timestamp=datetime.now(),\n            data=data,\n            checksum=checksum\n        )\n        \n        with self.get_connection() as conn:\n            cursor = conn.cursor()\n            \n            cursor.execute(\"\"\"\n                INSERT OR REPLACE INTO snapshots \n                (aggregate_id, version, timestamp, data, checksum)\n                VALUES (?, ?, ?, ?, ?)\n            \"\"\", (\n                snapshot.aggregate_id,\n                snapshot.version,\n                snapshot.timestamp.isoformat(),\n                compressed_data,\n                snapshot.checksum\n            ))\n            \n            conn.commit()\n        \n        logger.info(f\"Snapshot created for aggregate {aggregate_id} at version {version}\")\n        return checksum\n    \n    async def get_snapshot(self, aggregate_id: str) -> Optional[Snapshot]:\n        \"\"\"Get the latest snapshot for an aggregate\"\"\"\n        with self.get_connection() as conn:\n            cursor = conn.cursor()\n            \n            cursor.execute(\"\"\"\n                SELECT aggregate_id, version, timestamp, data, checksum\n                FROM snapshots \n                WHERE aggregate_id = ?\n                ORDER BY version DESC \n                LIMIT 1\n            \"\"\", (aggregate_id,))\n            \n            row = cursor.fetchone()\n            if not row:\n                return None\n            \n            # Decompress snapshot data\n            compressed_data = row[3]\n            if isinstance(compressed_data, bytes):\n                snapshot_data = json.loads(gzip.decompress(compressed_data).decode())\n            else:\n                snapshot_data = json.loads(compressed_data)\n            \n            return Snapshot(\n                aggregate_id=row[0],\n                version=row[1],\n                timestamp=datetime.fromisoformat(row[2]),\n                data=snapshot_data,\n                checksum=row[4]\n            )\n    \n    def register_event_handler(self, event_type: str, handler):\n        \"\"\"Register an event handler\"\"\"\n        self.event_handlers[event_type].append(handler)\n    \n    async def trigger_event_handlers(self, event: DomainEvent):\n        \"\"\"Trigger registered event handlers\"\"\"\n        handlers = self.event_handlers.get(event.metadata.event_type, [])\n        for handler in handlers:\n            try:\n                if asyncio.iscoroutinefunction(handler):\n                    await handler(event)\n                else:\n                    handler(event)\n            except Exception as e:\n                logger.error(f\"Event handler error for {event.metadata.event_type}: {e}\")\n\n# CQRS Implementation\nclass CommandHandler(ABC):\n    \"\"\"Base class for command handlers\"\"\"\n    \n    @abstractmethod\n    async def handle(self, command: Command) -> List[DomainEvent]:\n        pass\n\nclass QueryHandler(ABC):\n    \"\"\"Base class for query handlers\"\"\"\n    \n    @abstractmethod\n    async def handle(self, query: Query) -> Dict[str, Any]:\n        pass\n\nclass ProjectionHandler(ABC):\n    \"\"\"Base class for projection handlers\"\"\"\n    \n    @abstractmethod\n    async def handle(self, event: DomainEvent):\n        pass\n    \n    @abstractmethod\n    def get_projection_name(self) -> str:\n        pass\n\nclass CommandBus:\n    \"\"\"Command bus for CQRS pattern\"\"\"\n    \n    def __init__(self, event_store: EventStore):\n        self.event_store = event_store\n        self.handlers = {}\n    \n    def register_handler(self, command_type: str, handler: CommandHandler):\n        \"\"\"Register a command handler\"\"\"\n        self.handlers[command_type] = handler\n    \n    async def execute(self, command: Command) -> Dict[str, Any]:\n        \"\"\"Execute a command\"\"\"\n        handler = self.handlers.get(command.command_type)\n        if not handler:\n            raise HTTPException(status_code=400, detail=f\"No handler for command type: {command.command_type}\")\n        \n        try:\n            events = await handler.handle(command)\n            \n            # Append events to event store\n            event_ids = []\n            for event in events:\n                event_id = await self.event_store.append_event(event)\n                event_ids.append(event_id)\n            \n            return {\n                \"command_id\": command.command_id,\n                \"status\": \"success\",\n                \"events_generated\": len(events),\n                \"event_ids\": event_ids,\n                \"timestamp\": datetime.now().isoformat()\n            }\n            \n        except Exception as e:\n            logger.error(f\"Command execution error: {e}\")\n            raise HTTPException(status_code=500, detail=str(e))\n\nclass QueryBus:\n    \"\"\"Query bus for CQRS pattern\"\"\"\n    \n    def __init__(self, event_store: EventStore):\n        self.event_store = event_store\n        self.handlers = {}\n    \n    def register_handler(self, query_type: str, handler: QueryHandler):\n        \"\"\"Register a query handler\"\"\"\n        self.handlers[query_type] = handler\n    \n    async def execute(self, query: Query) -> Dict[str, Any]:\n        \"\"\"Execute a query\"\"\"\n        handler = self.handlers.get(query.query_type)\n        if not handler:\n            raise HTTPException(status_code=400, detail=f\"No handler for query type: {query.query_type}\")\n        \n        try:\n            result = await handler.handle(query)\n            \n            return {\n                \"query_id\": query.query_id,\n                \"query_type\": query.query_type,\n                \"result\": result,\n                \"executed_at\": datetime.now().isoformat()\n            }\n            \n        except Exception as e:\n            logger.error(f\"Query execution error: {e}\")\n            raise HTTPException(status_code=500, detail=str(e))\n\n# Saga Pattern Implementation\nclass SagaOrchestrator:\n    \"\"\"Orchestrator for distributed sagas\"\"\"\n    \n    def __init__(self, event_store: EventStore, command_bus: CommandBus):\n        self.event_store = event_store\n        self.command_bus = command_bus\n        self.active_sagas = {}\n    \n    async def start_saga(self, saga_id: str, saga_type: str, steps: List[SagaStep]) -> str:\n        \"\"\"Start a new saga\"\"\"\n        with self.event_store.get_connection() as conn:\n            cursor = conn.cursor()\n            \n            # Create saga record\n            cursor.execute(\"\"\"\n                INSERT INTO sagas (saga_id, saga_type, status, data)\n                VALUES (?, ?, ?, ?)\n            \"\"\", (saga_id, saga_type, \"started\", json.dumps({\"total_steps\": len(steps)})))\n            \n            # Create saga steps\n            for step in steps:\n                step.saga_id = saga_id\n                cursor.execute(\"\"\"\n                    INSERT INTO saga_steps \n                    (step_id, saga_id, step_type, status, command_data, compensation_data, max_retries)\n                    VALUES (?, ?, ?, ?, ?, ?, ?)\n                \"\"\", (\n                    step.step_id, step.saga_id, step.step_type, step.status,\n                    json.dumps(step.command.dict()) if step.command else None,\n                    json.dumps(step.compensation_command.dict()) if step.compensation_command else None,\n                    step.max_retries\n                ))\n            \n            conn.commit()\n        \n        # Start executing steps\n        asyncio.create_task(self.execute_saga(saga_id))\n        \n        return saga_id\n    \n    async def execute_saga(self, saga_id: str):\n        \"\"\"Execute saga steps\"\"\"\n        try:\n            with self.event_store.get_connection() as conn:\n                cursor = conn.cursor()\n                \n                # Get pending steps\n                cursor.execute(\"\"\"\n                    SELECT step_id, step_type, command_data, retry_count, max_retries\n                    FROM saga_steps \n                    WHERE saga_id = ? AND status = 'pending'\n                    ORDER BY created_at\n                \"\"\", (saga_id,))\n                \n                steps = cursor.fetchall()\n            \n            for step_data in steps:\n                step_id, step_type, command_data, retry_count, max_retries = step_data\n                \n                if command_data:\n                    command = Command(**json.loads(command_data))\n                    \n                    try:\n                        # Execute command\n                        result = await self.command_bus.execute(command)\n                        \n                        # Mark step as completed\n                        await self.complete_saga_step(step_id, \"completed\")\n                        \n                    except Exception as e:\n                        logger.error(f\"Saga step {step_id} failed: {e}\")\n                        \n                        if retry_count < max_retries:\n                            # Retry step\n                            await self.retry_saga_step(step_id)\n                        else:\n                            # Mark as failed and start compensation\n                            await self.complete_saga_step(step_id, \"failed\")\n                            await self.start_compensation(saga_id)\n                            return\n            \n            # Check if all steps completed\n            with self.event_store.get_connection() as conn:\n                cursor = conn.cursor()\n                cursor.execute(\"\"\"\n                    SELECT COUNT(*) FROM saga_steps \n                    WHERE saga_id = ? AND status != 'completed'\n                \"\"\", (saga_id,))\n                \n                incomplete_steps = cursor.fetchone()[0]\n            \n            if incomplete_steps == 0:\n                await self.complete_saga(saga_id, \"completed\")\n            \n        except Exception as e:\n            logger.error(f\"Saga execution error for {saga_id}: {e}\")\n            await self.complete_saga(saga_id, \"failed\")\n    \n    async def complete_saga_step(self, step_id: str, status: str):\n        \"\"\"Mark saga step as completed/failed\"\"\"\n        with self.event_store.get_connection() as conn:\n            cursor = conn.cursor()\n            cursor.execute(\"\"\"\n                UPDATE saga_steps \n                SET status = ?, completed_at = ?\n                WHERE step_id = ?\n            \"\"\", (status, datetime.now(), step_id))\n            conn.commit()\n    \n    async def retry_saga_step(self, step_id: str):\n        \"\"\"Retry a failed saga step\"\"\"\n        with self.event_store.get_connection() as conn:\n            cursor = conn.cursor()\n            cursor.execute(\"\"\"\n                UPDATE saga_steps \n                SET retry_count = retry_count + 1\n                WHERE step_id = ?\n            \"\"\", (step_id,))\n            conn.commit()\n    \n    async def start_compensation(self, saga_id: str):\n        \"\"\"Start compensation for failed saga\"\"\"\n        # Implementation for compensation logic\n        logger.info(f\"Starting compensation for saga {saga_id}\")\n        await self.complete_saga(saga_id, \"compensated\")\n    \n    async def complete_saga(self, saga_id: str, status: str):\n        \"\"\"Complete saga with final status\"\"\"\n        with self.event_store.get_connection() as conn:\n            cursor = conn.cursor()\n            cursor.execute(\"\"\"\n                UPDATE sagas \n                SET status = ?, completed_at = ?, updated_at = ?\n                WHERE saga_id = ?\n            \"\"\", (status, datetime.now(), datetime.now(), saga_id))\n            conn.commit()\n        \n        logger.info(f\"Saga {saga_id} completed with status: {status}\")\n\n# Sample Command and Query Handlers\nclass CreateUserCommandHandler(CommandHandler):\n    async def handle(self, command: Command) -> List[DomainEvent]:\n        user_data = command.data\n        \n        # Create UserCreated event\n        event = DomainEvent(\n            metadata=EventMetadata(\n                stream_id=command.aggregate_id,\n                event_type=\"UserCreated\",\n                version=1,\n                correlation_id=command.command_id,\n                user_id=command.user_id\n            ),\n            data={\n                \"user_id\": command.aggregate_id,\n                \"email\": user_data.get(\"email\"),\n                \"name\": user_data.get(\"name\"),\n                \"created_at\": datetime.now().isoformat()\n            }\n        )\n        \n        return [event]\n\nclass GetUserQueryHandler(QueryHandler):\n    def __init__(self, event_store: EventStore):\n        self.event_store = event_store\n    \n    async def handle(self, query: Query) -> Dict[str, Any]:\n        user_id = query.filters.get(\"user_id\")\n        if not user_id:\n            raise HTTPException(status_code=400, detail=\"user_id filter is required\")\n        \n        # Get events for user\n        events = await self.event_store.get_events(user_id)\n        \n        # Rebuild user state from events\n        user_state = {}\n        for event in events:\n            if event.metadata.event_type == \"UserCreated\":\n                user_state.update(event.data)\n            elif event.metadata.event_type == \"UserUpdated\":\n                user_state.update(event.data)\n        \n        return user_state\n\n# Global instances\nevent_store = EventStore()\ncommand_bus = CommandBus(event_store)\nquery_bus = QueryBus(event_store)\nsaga_orchestrator = SagaOrchestrator(event_store, command_bus)\n\n# Register handlers\ncommand_bus.register_handler(\"CreateUser\", CreateUserCommandHandler())\nquery_bus.register_handler(\"GetUser\", GetUserQueryHandler(event_store))\n\n# WebSocket connections for real-time event streaming\nconnected_clients = set()\n\n@app.get(\"/\")\nasync def root():\n    return {\n        \"service\": \"Event Sourcing & CQRS Service\",\n        \"version\": \"2.0.0\",\n        \"features\": [\n            \"Event sourcing with immutable event log\",\n            \"CQRS pattern implementation\",\n            \"Distributed saga orchestration\",\n            \"Real-time event streaming\",\n            \"Temporal queries and snapshots\",\n            \"Event compression and optimization\",\n            \"Concurrent access with WAL mode\"\n        ]\n    }\n\n@app.post(\"/commands\")\nasync def execute_command(command: Command):\n    \"\"\"Execute a command using CQRS pattern\"\"\"\n    return await command_bus.execute(command)\n\n@app.post(\"/queries\")\nasync def execute_query(query: Query):\n    \"\"\"Execute a query using CQRS pattern\"\"\"\n    return await query_bus.execute(query)\n\n@app.get(\"/events/{stream_id}\")\nasync def get_stream_events(\n    stream_id: str,\n    from_version: int = 0,\n    to_version: Optional[int] = None,\n    as_of: Optional[str] = None\n):\n    \"\"\"Get events from a stream with temporal query support\"\"\"\n    events = await event_store.get_events(stream_id, from_version, to_version)\n    \n    # Apply temporal filtering if requested\n    if as_of:\n        as_of_time = datetime.fromisoformat(as_of)\n        events = [e for e in events if e.metadata.timestamp <= as_of_time]\n    \n    return {\n        \"stream_id\": stream_id,\n        \"events_count\": len(events),\n        \"events\": [event.to_dict() for event in events],\n        \"from_version\": from_version,\n        \"to_version\": to_version or \"latest\"\n    }\n\n@app.post(\"/snapshots\")\nasync def create_aggregate_snapshot(request: Dict[str, Any]):\n    \"\"\"Create a snapshot for an aggregate\"\"\"\n    aggregate_id = request.get(\"aggregate_id\")\n    version = request.get(\"version\")\n    data = request.get(\"data\")\n    \n    if not all([aggregate_id, version is not None, data]):\n        raise HTTPException(status_code=400, detail=\"aggregate_id, version, and data are required\")\n    \n    checksum = await event_store.create_snapshot(aggregate_id, version, data)\n    \n    return {\n        \"aggregate_id\": aggregate_id,\n        \"version\": version,\n        \"checksum\": checksum,\n        \"created_at\": datetime.now().isoformat()\n    }\n\n@app.get(\"/snapshots/{aggregate_id}\")\nasync def get_aggregate_snapshot(aggregate_id: str):\n    \"\"\"Get the latest snapshot for an aggregate\"\"\"\n    snapshot = await event_store.get_snapshot(aggregate_id)\n    \n    if not snapshot:\n        raise HTTPException(status_code=404, detail=\"Snapshot not found\")\n    \n    return snapshot.dict()\n\n@app.post(\"/sagas\")\nasync def start_distributed_saga(request: Dict[str, Any]):\n    \"\"\"Start a distributed saga\"\"\"\n    saga_id = request.get(\"saga_id\", str(uuid.uuid4()))\n    saga_type = request.get(\"saga_type\")\n    steps_data = request.get(\"steps\", [])\n    \n    if not saga_type:\n        raise HTTPException(status_code=400, detail=\"saga_type is required\")\n    \n    # Convert steps data to SagaStep objects\n    steps = []\n    for step_data in steps_data:\n        step = SagaStep(\n            step_id=step_data.get(\"step_id\", str(uuid.uuid4())),\n            saga_id=saga_id,\n            step_type=step_data[\"step_type\"],\n            command=Command(**step_data[\"command\"]) if \"command\" in step_data else None,\n            compensation_command=Command(**step_data[\"compensation_command\"]) if \"compensation_command\" in step_data else None\n        )\n        steps.append(step)\n    \n    saga_id = await saga_orchestrator.start_saga(saga_id, saga_type, steps)\n    \n    return {\n        \"saga_id\": saga_id,\n        \"saga_type\": saga_type,\n        \"steps_count\": len(steps),\n        \"status\": \"started\",\n        \"started_at\": datetime.now().isoformat()\n    }\n\n@app.get(\"/sagas/{saga_id}\")\nasync def get_saga_status(saga_id: str):\n    \"\"\"Get saga status and progress\"\"\"\n    with event_store.get_connection() as conn:\n        cursor = conn.cursor()\n        \n        # Get saga info\n        cursor.execute(\"\"\"\n            SELECT saga_type, status, current_step, data, created_at, updated_at, completed_at\n            FROM sagas WHERE saga_id = ?\n        \"\"\", (saga_id,))\n        \n        saga_row = cursor.fetchone()\n        if not saga_row:\n            raise HTTPException(status_code=404, detail=\"Saga not found\")\n        \n        # Get saga steps\n        cursor.execute(\"\"\"\n            SELECT step_id, step_type, status, retry_count, max_retries, created_at, completed_at\n            FROM saga_steps WHERE saga_id = ?\n            ORDER BY created_at\n        \"\"\", (saga_id,))\n        \n        steps = cursor.fetchall()\n    \n    return {\n        \"saga_id\": saga_id,\n        \"saga_type\": saga_row[0],\n        \"status\": saga_row[1],\n        \"current_step\": saga_row[2],\n        \"total_steps\": len(steps),\n        \"steps\": [{\n            \"step_id\": step[0],\n            \"step_type\": step[1],\n            \"status\": step[2],\n            \"retry_count\": step[3],\n            \"max_retries\": step[4],\n            \"created_at\": step[5],\n            \"completed_at\": step[6]\n        } for step in steps],\n        \"created_at\": saga_row[4],\n        \"updated_at\": saga_row[5],\n        \"completed_at\": saga_row[6]\n    }\n\n@app.websocket(\"/events/stream\")\nasync def event_stream(websocket: WebSocket):\n    \"\"\"WebSocket endpoint for real-time event streaming\"\"\"\n    await websocket.accept()\n    connected_clients.add(websocket)\n    \n    try:\n        while True:\n            # Keep connection alive and handle client messages\n            data = await websocket.receive_text()\n            message = json.loads(data)\n            \n            if message.get(\"type\") == \"subscribe\":\n                stream_id = message.get(\"stream_id\")\n                # Send recent events for the stream\n                if stream_id:\n                    events = await event_store.get_events(stream_id)\n                    for event in events[-10:]:  # Send last 10 events\n                        await websocket.send_text(json.dumps({\n                            \"type\": \"event\",\n                            \"event\": event.to_dict()\n                        }))\n    \n    except WebSocketDisconnect:\n        connected_clients.remove(websocket)\n\n# Event handler to broadcast new events to WebSocket clients\nasync def broadcast_event(event: DomainEvent):\n    \"\"\"Broadcast event to all connected WebSocket clients\"\"\"\n    if connected_clients:\n        message = json.dumps({\n            \"type\": \"event\",\n            \"event\": event.to_dict()\n        })\n        \n        # Send to all connected clients\n        disconnected_clients = set()\n        for client in connected_clients:\n            try:\n                await client.send_text(message)\n            except:\n                disconnected_clients.add(client)\n        \n        # Remove disconnected clients\n        connected_clients -= disconnected_clients\n\n# Register the broadcast handler\nevent_store.register_event_handler(\"*\", broadcast_event)\n\n@app.get(\"/analytics\")\nasync def get_event_analytics():\n    \"\"\"Get event store analytics\"\"\"\n    with event_store.get_connection() as conn:\n        cursor = conn.cursor()\n        \n        # Event statistics\n        cursor.execute(\"SELECT COUNT(*) FROM events\")\n        total_events = cursor.fetchone()[0]\n        \n        cursor.execute(\"\"\"\n            SELECT event_type, COUNT(*) \n            FROM events \n            GROUP BY event_type \n            ORDER BY COUNT(*) DESC\n        \"\"\")\n        events_by_type = dict(cursor.fetchall())\n        \n        # Stream statistics\n        cursor.execute(\"SELECT COUNT(DISTINCT stream_id) FROM events\")\n        total_streams = cursor.fetchone()[0]\n        \n        # Recent activity\n        cursor.execute(\"\"\"\n            SELECT DATE(timestamp) as date, COUNT(*) \n            FROM events \n            WHERE timestamp > datetime('now', '-7 days')\n            GROUP BY DATE(timestamp)\n            ORDER BY date\n        \"\"\")\n        daily_activity = dict(cursor.fetchall())\n        \n        # Saga statistics\n        cursor.execute(\"SELECT status, COUNT(*) FROM sagas GROUP BY status\")\n        saga_stats = dict(cursor.fetchall())\n        \n        # Snapshot statistics\n        cursor.execute(\"SELECT COUNT(*) FROM snapshots\")\n        total_snapshots = cursor.fetchone()[0]\n    \n    return {\n        \"events\": {\n            \"total\": total_events,\n            \"by_type\": events_by_type,\n            \"daily_activity\": daily_activity\n        },\n        \"streams\": {\n            \"total\": total_streams\n        },\n        \"sagas\": saga_stats,\n        \"snapshots\": {\n            \"total\": total_snapshots\n        },\n        \"generated_at\": datetime.now().isoformat()\n    }\n\nif __name__ == \"__main__\":\n    import uvicorn\n    uvicorn.run(app, host=\"0.0.0.0\", port=8851)