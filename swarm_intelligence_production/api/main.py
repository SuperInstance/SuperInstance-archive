"""
Swarm Intelligence Platform - FastAPI Backend
Universal API for swarm-based creative and computational systems
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import asyncio
import uuid
import time
from datetime import datetime, timedelta
import json

from .models import (
    SwarmCreateRequest, SwarmResponse, SwarmStatus,
    TaskSubmitRequest, TaskResponse, TaskStatus,
    MetricsResponse, APIKey, User, RateLimitTier
)
from .middleware.auth import verify_api_key, create_access_token, get_current_user
from .middleware.rate_limit import RateLimiter
from .routes import swarms, tasks, metrics, webhooks
from .websocket_manager import WebSocketManager

# Global state
swarm_registry = {}
task_queue = asyncio.Queue()
websocket_manager = WebSocketManager()
rate_limiter = RateLimiter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("Starting Swarm Intelligence API Platform...")
    asyncio.create_task(process_task_queue())
    yield
    # Shutdown
    print("Shutting down Swarm Intelligence API Platform...")
    await websocket_manager.disconnect_all()


app = FastAPI(
    title="Swarm Intelligence Platform API",
    description="Universal API for distributed swarm-based computing and creativity",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# AUTHENTICATION & AUTHORIZATION
# ============================================================================

@app.post("/api/v1/auth/token", tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth 2.0 token endpoint"""
    # Validate credentials (integrate with your auth system)
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username, "tier": user.tier}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "tier": user.tier,
        "rate_limits": rate_limiter.get_tier_limits(user.tier)
    }


@app.post("/api/v1/auth/api-key", tags=["Authentication"])
async def generate_api_key(current_user: User = Depends(get_current_user)):
    """Generate new API key"""
    api_key = str(uuid.uuid4())
    # Store API key in database with user association
    await store_api_key(api_key, current_user.id)

    return {
        "api_key": api_key,
        "user_id": current_user.id,
        "tier": current_user.tier,
        "created_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# SWARM MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/v1/swarms", response_model=SwarmResponse, tags=["Swarms"])
async def create_swarm(
    request: SwarmCreateRequest,
    api_key: str = Depends(verify_api_key),
    _rate_limit: None = Depends(rate_limiter.check_rate_limit)
):
    """
    Create a new swarm

    - **name**: Unique name for the swarm
    - **agent_count**: Number of agents (1-10000)
    - **agent_type**: Type of agents (WORKER, COORDINATOR, SCOUT)
    - **config**: Optional configuration object
    """
    swarm_id = f"swarm_{uuid.uuid4().hex[:12]}"

    swarm = {
        "swarm_id": swarm_id,
        "name": request.name,
        "agent_count": request.agent_count,
        "agent_type": request.agent_type,
        "status": SwarmStatus.INITIALIZING,
        "config": request.config or {},
        "created_at": datetime.utcnow(),
        "agents": [],
        "metrics": {}
    }

    # Start swarm initialization (async background task)
    asyncio.create_task(initialize_swarm(swarm_id, request))

    swarm_registry[swarm_id] = swarm

    return SwarmResponse(**swarm)


@app.get("/api/v1/swarms/{swarm_id}", response_model=SwarmResponse, tags=["Swarms"])
async def get_swarm(
    swarm_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get swarm details by ID"""
    if swarm_id not in swarm_registry:
        raise HTTPException(status_code=404, detail="Swarm not found")

    return SwarmResponse(**swarm_registry[swarm_id])


@app.get("/api/v1/swarms", tags=["Swarms"])
async def list_swarms(
    status: Optional[SwarmStatus] = None,
    limit: int = 20,
    offset: int = 0,
    api_key: str = Depends(verify_api_key)
):
    """List all swarms with optional filtering"""
    swarms = list(swarm_registry.values())

    if status:
        swarms = [s for s in swarms if s["status"] == status]

    total = len(swarms)
    swarms = swarms[offset:offset + limit]

    return {
        "swarms": swarms,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.patch("/api/v1/swarms/{swarm_id}/scale", tags=["Swarms"])
async def scale_swarm(
    swarm_id: str,
    agent_count: int,
    api_key: str = Depends(verify_api_key)
):
    """Scale swarm to specified number of agents"""
    if swarm_id not in swarm_registry:
        raise HTTPException(status_code=404, detail="Swarm not found")

    swarm = swarm_registry[swarm_id]
    previous_count = swarm["agent_count"]

    swarm["agent_count"] = agent_count
    swarm["status"] = SwarmStatus.SCALING

    # Trigger scaling operation
    asyncio.create_task(perform_scaling(swarm_id, agent_count))

    return {
        "swarm_id": swarm_id,
        "previous_count": previous_count,
        "new_count": agent_count,
        "status": SwarmStatus.SCALING
    }


@app.delete("/api/v1/swarms/{swarm_id}", tags=["Swarms"])
async def terminate_swarm(
    swarm_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Terminate swarm and clean up resources"""
    if swarm_id not in swarm_registry:
        raise HTTPException(status_code=404, detail="Swarm not found")

    # Cleanup operation
    await cleanup_swarm(swarm_id)
    del swarm_registry[swarm_id]

    return {"message": f"Swarm {swarm_id} terminated successfully"}


# ============================================================================
# TASK MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/v1/swarms/{swarm_id}/tasks", response_model=TaskResponse, tags=["Tasks"])
async def submit_task(
    swarm_id: str,
    request: TaskSubmitRequest,
    api_key: str = Depends(verify_api_key),
    _rate_limit: None = Depends(rate_limiter.check_rate_limit)
):
    """
    Submit a task to the swarm

    - **type**: Task type (must match swarm capabilities)
    - **payload**: Task-specific data
    - **priority**: Task priority (LOW, NORMAL, HIGH, CRITICAL)
    - **timeout**: Optional timeout in seconds
    """
    if swarm_id not in swarm_registry:
        raise HTTPException(status_code=404, detail="Swarm not found")

    task_id = f"task_{uuid.uuid4().hex[:12]}"

    task = {
        "task_id": task_id,
        "swarm_id": swarm_id,
        "type": request.type,
        "payload": request.payload,
        "priority": request.priority,
        "timeout": request.timeout,
        "status": TaskStatus.QUEUED,
        "created_at": datetime.utcnow(),
        "result": None
    }

    # Add to task queue
    await task_queue.put(task)

    # Notify via WebSocket
    await websocket_manager.broadcast_to_swarm(
        swarm_id,
        {"type": "task.queued", "task_id": task_id}
    )

    return TaskResponse(**task)


@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task_status(
    task_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get task status and result"""
    # Fetch from task storage
    task = await fetch_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(**task)


@app.get("/api/v1/swarms/{swarm_id}/tasks", tags=["Tasks"])
async def list_tasks(
    swarm_id: str,
    status: Optional[TaskStatus] = None,
    limit: int = 50,
    api_key: str = Depends(verify_api_key)
):
    """List tasks for a swarm"""
    tasks = await fetch_swarm_tasks(swarm_id, status, limit)
    return {"tasks": tasks, "total": len(tasks)}


# ============================================================================
# METRICS & MONITORING ENDPOINTS
# ============================================================================

@app.get("/api/v1/swarms/{swarm_id}/metrics", response_model=MetricsResponse, tags=["Metrics"])
async def get_swarm_metrics(
    swarm_id: str,
    window: str = "LAST_HOUR",
    api_key: str = Depends(verify_api_key)
):
    """
    Get real-time swarm metrics

    - **window**: Time window (LAST_HOUR, LAST_DAY, LAST_WEEK)
    """
    if swarm_id not in swarm_registry:
        raise HTTPException(status_code=404, detail="Swarm not found")

    metrics = await calculate_metrics(swarm_id, window)

    return MetricsResponse(
        swarm_id=swarm_id,
        window=window,
        metrics=metrics
    )


@app.get("/api/v1/swarms/{swarm_id}/metrics/stream", tags=["Metrics"])
async def stream_metrics(
    swarm_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Stream real-time metrics via Server-Sent Events"""
    async def metric_generator():
        while True:
            metrics = await calculate_metrics(swarm_id, "LAST_MINUTE")
            yield f"data: {json.dumps(metrics)}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(
        metric_generator(),
        media_type="text/event-stream"
    )


# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

@app.websocket("/ws/{swarm_id}")
async def websocket_endpoint(websocket: WebSocket, swarm_id: str):
    """
    WebSocket connection for real-time swarm updates

    Events:
    - agent_status: Agent state changes
    - task_progress: Task completion progress
    - metrics: Real-time metrics
    - errors: Error notifications
    """
    await websocket.accept()

    # Authenticate WebSocket connection
    try:
        auth_message = await websocket.receive_json()
        if auth_message.get("type") != "auth":
            await websocket.close(code=1008)
            return

        api_key = auth_message.get("api_key")
        if not await validate_api_key(api_key):
            await websocket.close(code=1008)
            return
    except:
        await websocket.close(code=1008)
        return

    # Register connection
    connection_id = await websocket_manager.connect(swarm_id, websocket)

    try:
        while True:
            # Handle incoming messages
            data = await websocket.receive_json()

            if data.get("type") == "subscribe":
                events = data.get("events", [])
                await websocket_manager.subscribe(connection_id, events)

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": time.time()})

    except WebSocketDisconnect:
        await websocket_manager.disconnect(connection_id)


# ============================================================================
# CREATIVE PRODUCTION ENDPOINTS
# ============================================================================

@app.post("/api/v1/creative/batch", tags=["Creative Production"])
async def batch_process(
    swarm_id: str,
    tasks: List[Dict[str, Any]],
    api_key: str = Depends(verify_api_key)
):
    """
    Batch processing for render farms and large-scale content generation

    Submit multiple tasks for parallel processing by swarm
    """
    if swarm_id not in swarm_registry:
        raise HTTPException(status_code=404, detail="Swarm not found")

    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    task_ids = []

    for task_data in tasks:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = {
            "task_id": task_id,
            "batch_id": batch_id,
            "swarm_id": swarm_id,
            "status": TaskStatus.QUEUED,
            **task_data
        }
        await task_queue.put(task)
        task_ids.append(task_id)

    return {
        "batch_id": batch_id,
        "task_count": len(task_ids),
        "task_ids": task_ids,
        "status": "processing"
    }


@app.get("/api/v1/creative/batch/{batch_id}", tags=["Creative Production"])
async def get_batch_status(
    batch_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get status of batch processing job"""
    tasks = await fetch_batch_tasks(batch_id)

    completed = sum(1 for t in tasks if t["status"] == TaskStatus.COMPLETED)
    failed = sum(1 for t in tasks if t["status"] == TaskStatus.FAILED)

    return {
        "batch_id": batch_id,
        "total_tasks": len(tasks),
        "completed": completed,
        "failed": failed,
        "in_progress": len(tasks) - completed - failed,
        "tasks": tasks
    }


@app.post("/api/v1/creative/stream", tags=["Creative Production"])
async def stream_creative_generation(
    swarm_id: str,
    task_type: str,
    payload: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
):
    """
    Streaming API for real-time content generation

    Returns progressive results as swarm generates content
    """
    async def content_generator():
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        # Initialize streaming task
        async for chunk in generate_streaming_content(swarm_id, task_type, payload):
            yield json.dumps(chunk) + "\n"

    return StreamingResponse(
        content_generator(),
        media_type="application/x-ndjson"
    )


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@app.post("/api/v1/webhooks", tags=["Webhooks"])
async def create_webhook(
    url: str,
    events: List[str],
    secret: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """
    Register webhook for event notifications

    Events:
    - task.completed
    - task.failed
    - swarm.error
    - agent.failed
    - metrics.threshold
    """
    webhook_id = f"webhook_{uuid.uuid4().hex[:12]}"

    webhook = {
        "webhook_id": webhook_id,
        "url": url,
        "events": events,
        "secret": secret or str(uuid.uuid4()),
        "created_at": datetime.utcnow()
    }

    await store_webhook(webhook)

    return webhook


@app.get("/api/v1/webhooks", tags=["Webhooks"])
async def list_webhooks(api_key: str = Depends(verify_api_key)):
    """List all registered webhooks"""
    webhooks = await fetch_webhooks(api_key)
    return {"webhooks": webhooks}


@app.delete("/api/v1/webhooks/{webhook_id}", tags=["Webhooks"])
async def delete_webhook(
    webhook_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Delete webhook"""
    await remove_webhook(webhook_id)
    return {"message": f"Webhook {webhook_id} deleted"}


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "active_swarms": len(swarm_registry),
        "queue_size": task_queue.qsize()
    }


@app.get("/api/v1/status", tags=["System"])
async def system_status(api_key: str = Depends(verify_api_key)):
    """Detailed system status"""
    return {
        "platform": "Swarm Intelligence",
        "version": "1.0.0",
        "uptime_seconds": time.time() - startup_time,
        "statistics": {
            "total_swarms": len(swarm_registry),
            "active_swarms": sum(1 for s in swarm_registry.values() if s["status"] == SwarmStatus.RUNNING),
            "total_agents": sum(s["agent_count"] for s in swarm_registry.values()),
            "queued_tasks": task_queue.qsize()
        }
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user credentials"""
    # Implement actual authentication logic
    pass


async def initialize_swarm(swarm_id: str, request: SwarmCreateRequest):
    """Initialize swarm agents (background task)"""
    await asyncio.sleep(2)  # Simulate initialization
    swarm_registry[swarm_id]["status"] = SwarmStatus.RUNNING


async def perform_scaling(swarm_id: str, agent_count: int):
    """Scale swarm agents"""
    await asyncio.sleep(1)
    swarm_registry[swarm_id]["status"] = SwarmStatus.RUNNING


async def cleanup_swarm(swarm_id: str):
    """Cleanup swarm resources"""
    pass


async def process_task_queue():
    """Background task processor"""
    while True:
        task = await task_queue.get()
        # Process task
        await asyncio.sleep(0.1)


async def calculate_metrics(swarm_id: str, window: str) -> Dict[str, Any]:
    """Calculate swarm metrics"""
    return {
        "tasks_completed": 156,
        "average_latency_ms": 234,
        "agent_utilization": 0.78,
        "error_rate": 0.02,
        "throughput_per_second": 2.6
    }


async def fetch_task(task_id: str) -> Optional[Dict]:
    """Fetch task from storage"""
    pass


async def fetch_swarm_tasks(swarm_id: str, status: Optional[TaskStatus], limit: int) -> List[Dict]:
    """Fetch tasks for swarm"""
    return []


async def fetch_batch_tasks(batch_id: str) -> List[Dict]:
    """Fetch tasks in batch"""
    return []


async def generate_streaming_content(swarm_id: str, task_type: str, payload: Dict):
    """Generate streaming content"""
    for i in range(10):
        yield {"chunk": i, "data": f"content_{i}"}
        await asyncio.sleep(0.5)


async def store_webhook(webhook: Dict):
    """Store webhook configuration"""
    pass


async def fetch_webhooks(api_key: str) -> List[Dict]:
    """Fetch user webhooks"""
    return []


async def remove_webhook(webhook_id: str):
    """Remove webhook"""
    pass


async def validate_api_key(api_key: str) -> bool:
    """Validate API key"""
    return True


async def store_api_key(api_key: str, user_id: str):
    """Store API key"""
    pass


# Global startup time
startup_time = time.time()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
