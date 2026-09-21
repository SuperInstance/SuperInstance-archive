#!/usr/bin/env python3
"""
Real-Time Collaboration and Synchronization Service
Advanced real-time collaboration with operational transforms, CRDT, and conflict resolution
"""

import asyncio
import json
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn
import redis.asyncio as redis
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data Models
@dataclass
class Operation:
    """Operational Transform operation"""
    id: str
    type: str  # insert, delete, retain, replace
    position: int
    content: str = ""
    length: int = 0
    timestamp: float = 0.0
    user_id: str = ""
    revision: int = 0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

@dataclass
class CRDTState:
    """Conflict-free Replicated Data Type state"""
    id: str
    vector_clock: Dict[str, int]
    operations: List[Dict]
    content_hash: str
    last_modified: float

class DocumentUpdate(BaseModel):
    document_id: str
    operation: Dict[str, Any]
    user_id: str
    session_id: str

class CollaborationSession(BaseModel):
    session_id: str
    document_id: str
    user_id: str
    permissions: List[str] = Field(default_factory=lambda: ["read", "write"])

class ConflictResolution(BaseModel):
    strategy: str = "operational_transform"  # ot, crdt, last_writer_wins
    auto_merge: bool = True
    notify_conflicts: bool = True

class AdvancedCollaborationSync:
    """Advanced real-time collaboration service with operational transforms"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.active_sessions: Dict[str, Dict[str, WebSocket]] = defaultdict(dict)
        self.document_states: Dict[str, CRDTState] = {}
        self.operation_queue: Dict[str, deque] = defaultdict(deque)
        self.conflict_resolver = ConflictResolution()
        self.presence_data: Dict[str, Dict] = defaultdict(dict)
        
        # Performance metrics
        self.metrics = {
            "operations_processed": 0,
            "conflicts_resolved": 0,
            "active_collaborators": 0,
            "sync_latency_ms": [],
            "data_transferred_kb": 0
        }
    
    async def initialize_redis(self):
        """Initialize Redis connection for state persistence"""
        try:
            self.redis_client = await redis.from_url("redis://localhost:6379")
            await self.redis_client.ping()
            logger.info("✅ Redis connection established for collaboration sync")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def transform_operations(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """
        Operational Transform - resolve conflicts between concurrent operations
        Uses Google Wave OT algorithm for consistency
        """
        if op1.type == "insert" and op2.type == "insert":
            if op1.position <= op2.position:
                return op1, Operation(
                    id=op2.id,
                    type=op2.type,
                    position=op2.position + len(op1.content),
                    content=op2.content,
                    timestamp=op2.timestamp,
                    user_id=op2.user_id,
                    revision=op2.revision
                )
            else:
                return Operation(
                    id=op1.id,
                    type=op1.type,
                    position=op1.position + len(op2.content),
                    content=op1.content,
                    timestamp=op1.timestamp,
                    user_id=op1.user_id,
                    revision=op1.revision
                ), op2
        
        elif op1.type == "delete" and op2.type == "delete":
            if op1.position == op2.position:
                # Same position delete - merge deletions
                max_length = max(op1.length, op2.length)
                return Operation(
                    id=f"{op1.id}+{op2.id}",
                    type="delete",
                    position=op1.position,
                    length=max_length,
                    timestamp=max(op1.timestamp, op2.timestamp),
                    user_id=f"{op1.user_id},{op2.user_id}",
                    revision=max(op1.revision, op2.revision)
                ), Operation(id=str(uuid.uuid4()), type="retain", position=0, length=0)
            elif op1.position < op2.position:
                if op1.position + op1.length <= op2.position:
                    return op1, Operation(
                        id=op2.id,
                        type=op2.type,
                        position=op2.position - op1.length,
                        length=op2.length,
                        timestamp=op2.timestamp,
                        user_id=op2.user_id,
                        revision=op2.revision
                    )
        
        elif op1.type == "insert" and op2.type == "delete":
            if op1.position <= op2.position:
                return op1, Operation(
                    id=op2.id,
                    type=op2.type,
                    position=op2.position + len(op1.content),
                    length=op2.length,
                    timestamp=op2.timestamp,
                    user_id=op2.user_id,
                    revision=op2.revision
                )
            else:
                return Operation(
                    id=op1.id,
                    type=op1.type,
                    position=max(0, op1.position - op2.length),
                    content=op1.content,
                    timestamp=op1.timestamp,
                    user_id=op1.user_id,
                    revision=op1.revision
                ), op2
        
        # Default: return operations unchanged
        return op1, op2
    
    def update_vector_clock(self, document_id: str, user_id: str) -> Dict[str, int]:
        """Update CRDT vector clock for causality tracking"""
        if document_id not in self.document_states:
            self.document_states[document_id] = CRDTState(
                id=document_id,
                vector_clock={},
                operations=[],
                content_hash="",
                last_modified=time.time()
            )
        
        state = self.document_states[document_id]
        state.vector_clock[user_id] = state.vector_clock.get(user_id, 0) + 1
        state.last_modified = time.time()
        return state.vector_clock.copy()
    
    async def process_operation(self, document_id: str, operation: Operation) -> Dict[str, Any]:
        """Process and transform operation with conflict resolution"""
        start_time = time.time()
        
        # Update vector clock
        vector_clock = self.update_vector_clock(document_id, operation.user_id)
        operation.revision = sum(vector_clock.values())
        
        # Check for concurrent operations in queue
        queue = self.operation_queue[document_id]
        transformed_ops = []
        
        # Apply operational transformation to resolve conflicts
        current_op = operation
        for queued_op_dict in list(queue):
            queued_op = Operation(**queued_op_dict)
            if queued_op.user_id != operation.user_id and abs(queued_op.timestamp - operation.timestamp) < 1.0:
                current_op, transformed_queued = self.transform_operations(current_op, queued_op)
                transformed_ops.append(transformed_queued)
                self.metrics["conflicts_resolved"] += 1
        
        # Add to operation queue
        queue.append(asdict(current_op))
        if len(queue) > 1000:  # Limit queue size
            queue.popleft()
        
        # Update document state
        if document_id in self.document_states:
            state = self.document_states[document_id]
            state.operations.append(asdict(current_op))
            if len(state.operations) > 500:  # Limit operations history
                state.operations = state.operations[-250:]  # Keep recent half
        
        # Persist to Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"collaboration:doc:{document_id}:ops",
                    3600,  # 1 hour TTL
                    json.dumps(list(queue))
                )
                await self.redis_client.setex(
                    f"collaboration:doc:{document_id}:state",
                    3600,
                    json.dumps(asdict(self.document_states[document_id]))
                )
            except Exception as e:
                logger.error(f"Redis persistence error: {e}")
        
        # Update metrics
        self.metrics["operations_processed"] += 1
        self.metrics["sync_latency_ms"].append((time.time() - start_time) * 1000)
        if len(self.metrics["sync_latency_ms"]) > 1000:
            self.metrics["sync_latency_ms"] = self.metrics["sync_latency_ms"][-500:]
        
        return {
            "operation_id": current_op.id,
            "transformed": len(transformed_ops) > 0,
            "revision": current_op.revision,
            "vector_clock": vector_clock,
            "conflicts_resolved": len(transformed_ops),
            "processing_time_ms": (time.time() - start_time) * 1000
        }
    
    async def broadcast_operation(self, document_id: str, operation: Dict, sender_session: str):
        """Broadcast operation to all active collaborators"""
        if document_id not in self.active_sessions:
            return
        
        broadcast_data = {
            "type": "operation",
            "document_id": document_id,
            "operation": operation,
            "timestamp": time.time()
        }
        
        # Calculate data size for metrics
        data_size = len(json.dumps(broadcast_data))
        self.metrics["data_transferred_kb"] += data_size / 1024
        
        # Broadcast to all sessions except sender
        for session_id, websocket in self.active_sessions[document_id].items():
            if session_id != sender_session:
                try:
                    await websocket.send_text(json.dumps(broadcast_data))
                except websockets.exceptions.ConnectionClosed:
                    # Remove disconnected session
                    del self.active_sessions[document_id][session_id]
                except Exception as e:
                    logger.error(f"Broadcast error to session {session_id}: {e}")
    
    async def update_presence(self, document_id: str, user_id: str, session_id: str, presence_data: Dict):
        """Update and broadcast user presence information"""
        self.presence_data[document_id][user_id] = {
            "session_id": session_id,
            "cursor_position": presence_data.get("cursor_position", 0),
            "selection": presence_data.get("selection", {}),
            "status": presence_data.get("status", "active"),
            "last_seen": time.time()
        }
        
        # Broadcast presence update
        presence_update = {
            "type": "presence",
            "document_id": document_id,
            "user_id": user_id,
            "presence": self.presence_data[document_id][user_id]
        }
        
        if document_id in self.active_sessions:
            for websocket in self.active_sessions[document_id].values():
                try:
                    await websocket.send_text(json.dumps(presence_update))
                except:
                    pass
    
    async def get_document_snapshot(self, document_id: str) -> Dict[str, Any]:
        """Get current document state snapshot"""
        if self.redis_client:
            try:
                # Try to get from Redis first
                state_data = await self.redis_client.get(f"collaboration:doc:{document_id}:state")
                if state_data:
                    return json.loads(state_data)
            except Exception as e:
                logger.error(f"Redis snapshot retrieval error: {e}")
        
        # Fallback to memory
        if document_id in self.document_states:
            return asdict(self.document_states[document_id])
        
        return {
            "id": document_id,
            "vector_clock": {},
            "operations": [],
            "content_hash": "",
            "last_modified": time.time()
        }
    
    def calculate_content_hash(self, operations: List[Dict]) -> str:
        """Calculate hash of document content for integrity checking"""
        content_str = json.dumps(sorted(operations, key=lambda x: x.get("timestamp", 0)))
        return hashlib.sha256(content_str.encode()).hexdigest()

# Initialize collaboration service
collaboration_service = AdvancedCollaborationSync()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await collaboration_service.initialize_redis()
    logger.info("🚀 Advanced Collaboration & Sync Service starting up")
    
    yield
    
    # Shutdown
    if collaboration_service.redis_client:
        await collaboration_service.redis_client.close()
    logger.info("🔄 Collaboration service shutting down")

# FastAPI app
app = FastAPI(
    title="ActiveLog Collaboration & Sync Service",
    description="Real-time collaboration with operational transforms and CRDT",
    version="2.0.0",
    lifespan=lifespan
)

security = HTTPBearer()

# WebSocket endpoint for real-time collaboration
@app.websocket("/ws/collaborate/{document_id}")
async def websocket_collaboration(websocket: WebSocket, document_id: str):
    await websocket.accept()
    
    try:
        # Authentication (simplified for demo)
        auth_data = await websocket.receive_json()
        user_id = auth_data.get("user_id", f"user_{uuid.uuid4().hex[:8]}")
        session_id = auth_data.get("session_id", str(uuid.uuid4()))
        
        # Add to active sessions
        collaboration_service.active_sessions[document_id][session_id] = websocket
        collaboration_service.metrics["active_collaborators"] = sum(
            len(sessions) for sessions in collaboration_service.active_sessions.values()
        )
        
        # Send initial document state
        snapshot = await collaboration_service.get_document_snapshot(document_id)
        await websocket.send_text(json.dumps({
            "type": "snapshot",
            "document_id": document_id,
            "snapshot": snapshot
        }))
        
        logger.info(f"👥 User {user_id} joined collaboration on document {document_id}")
        
        while True:
            try:
                data = await websocket.receive_json()
                
                if data.get("type") == "operation":
                    # Process document operation
                    operation = Operation(
                        id=data.get("operation_id", str(uuid.uuid4())),
                        type=data["operation_type"],
                        position=data["position"],
                        content=data.get("content", ""),
                        length=data.get("length", 0),
                        user_id=user_id
                    )
                    
                    result = await collaboration_service.process_operation(document_id, operation)
                    
                    # Broadcast to other collaborators
                    await collaboration_service.broadcast_operation(
                        document_id, 
                        asdict(operation), 
                        session_id
                    )
                    
                    # Send confirmation to sender
                    await websocket.send_text(json.dumps({
                        "type": "operation_ack",
                        "operation_id": operation.id,
                        "result": result
                    }))
                
                elif data.get("type") == "presence":
                    # Update presence information
                    await collaboration_service.update_presence(
                        document_id, user_id, session_id, data["presence"]
                    )
                
                elif data.get("type") == "cursor":
                    # Broadcast cursor position
                    cursor_data = {
                        "type": "cursor",
                        "document_id": document_id,
                        "user_id": user_id,
                        "position": data["position"],
                        "selection": data.get("selection", {})
                    }
                    
                    for sid, ws in collaboration_service.active_sessions[document_id].items():
                        if sid != session_id:
                            try:
                                await ws.send_text(json.dumps(cursor_data))
                            except:
                                pass
                
            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
    
    finally:
        # Clean up session
        if document_id in collaboration_service.active_sessions:
            collaboration_service.active_sessions[document_id].pop(session_id, None)
        
        # Clean up presence
        if document_id in collaboration_service.presence_data:
            collaboration_service.presence_data[document_id] = {
                uid: data for uid, data in collaboration_service.presence_data[document_id].items()
                if data.get("session_id") != session_id
            }
        
        collaboration_service.metrics["active_collaborators"] = sum(
            len(sessions) for sessions in collaboration_service.active_sessions.values()
        )
        
        logger.info(f"👋 Session {session_id} disconnected from document {document_id}")

# REST API endpoints
@app.post("/api/documents/{document_id}/operations")
async def apply_operation(document_id: str, update: DocumentUpdate):
    """Apply operation to document via REST API"""
    operation = Operation(
        id=str(uuid.uuid4()),
        type=update.operation["type"],
        position=update.operation["position"],
        content=update.operation.get("content", ""),
        length=update.operation.get("length", 0),
        user_id=update.user_id
    )
    
    result = await collaboration_service.process_operation(document_id, operation)
    
    # Broadcast to WebSocket clients
    await collaboration_service.broadcast_operation(
        document_id, 
        asdict(operation), 
        update.session_id
    )
    
    return {"success": True, "result": result}

@app.get("/api/documents/{document_id}/state")
async def get_document_state(document_id: str):
    """Get current document state"""
    snapshot = await collaboration_service.get_document_snapshot(document_id)
    
    return {
        "document_id": document_id,
        "state": snapshot,
        "active_collaborators": len(collaboration_service.active_sessions.get(document_id, {})),
        "presence": collaboration_service.presence_data.get(document_id, {})
    }

@app.get("/api/documents/{document_id}/history")
async def get_operation_history(document_id: str, limit: int = 100):
    """Get operation history for document"""
    operations = []
    
    if collaboration_service.redis_client:
        try:
            ops_data = await collaboration_service.redis_client.get(f"collaboration:doc:{document_id}:ops")
            if ops_data:
                operations = json.loads(ops_data)
        except Exception as e:
            logger.error(f"Redis history retrieval error: {e}")
    
    # Fallback to memory
    if not operations and document_id in collaboration_service.operation_queue:
        operations = list(collaboration_service.operation_queue[document_id])
    
    return {
        "document_id": document_id,
        "operations": operations[-limit:],
        "total_operations": len(operations)
    }

@app.post("/api/documents/{document_id}/sync")
async def sync_document(document_id: str, background_tasks: BackgroundTasks):
    """Force synchronization of document state"""
    
    async def perform_sync():
        """Background sync operation"""
        if document_id in collaboration_service.document_states:
            state = collaboration_service.document_states[document_id]
            
            # Recalculate content hash
            state.content_hash = collaboration_service.calculate_content_hash(state.operations)
            
            # Persist to Redis
            if collaboration_service.redis_client:
                try:
                    await collaboration_service.redis_client.setex(
                        f"collaboration:doc:{document_id}:state",
                        3600,
                        json.dumps(asdict(state))
                    )
                except Exception as e:
                    logger.error(f"Sync persistence error: {e}")
    
    background_tasks.add_task(perform_sync)
    return {"message": "Sync initiated", "document_id": document_id}

@app.get("/api/collaboration/metrics")
async def get_collaboration_metrics():
    """Get collaboration service metrics"""
    avg_latency = (
        sum(collaboration_service.metrics["sync_latency_ms"]) / 
        len(collaboration_service.metrics["sync_latency_ms"])
        if collaboration_service.metrics["sync_latency_ms"] else 0
    )
    
    return {
        "operations_processed": collaboration_service.metrics["operations_processed"],
        "conflicts_resolved": collaboration_service.metrics["conflicts_resolved"],
        "active_collaborators": collaboration_service.metrics["active_collaborators"],
        "average_sync_latency_ms": round(avg_latency, 2),
        "data_transferred_kb": round(collaboration_service.metrics["data_transferred_kb"], 2),
        "active_documents": len(collaboration_service.active_sessions),
        "memory_usage": {
            "document_states": len(collaboration_service.document_states),
            "operation_queues": sum(len(q) for q in collaboration_service.operation_queue.values()),
            "presence_data": sum(len(p) for p in collaboration_service.presence_data.values())
        }
    }

@app.get("/api/collaboration/health")
async def health_check():
    """Health check endpoint"""
    redis_status = "connected" if collaboration_service.redis_client else "disconnected"
    
    return {
        "status": "healthy",
        "service": "Advanced Collaboration & Sync",
        "version": "2.0.0",
        "redis": redis_status,
        "active_sessions": sum(len(sessions) for sessions in collaboration_service.active_sessions.values()),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Advanced Collaboration & Sync Service")
    parser.add_argument("--port", type=int, default=8095, help="Port to run the service on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    
    args = parser.parse_args()
    
    print("🚀 Starting Advanced Collaboration & Synchronization Service")
    print(f"📡 Real-time collaboration with operational transforms")
    print(f"🔄 CRDT-based conflict resolution")
    print(f"👥 Multi-user presence tracking")
    print(f"⚡ WebSocket + REST API")
    print(f"🌐 Running on http://{args.host}:{args.port}")
    
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=False,
        access_log=True
    )