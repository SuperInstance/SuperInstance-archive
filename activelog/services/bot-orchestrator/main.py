import asyncio
import logging
import json
import os
import signal
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import uvicorn

# Import our orchestration components
from director.claude_director import ClaudeDirector, TaskPriority, TaskStatus
from coordination import (
    TaskQueueManager, QueuedTask, QueuePriority, 
    ParallelExecutor, ExecutionPlan, ExecutionStrategy,
    BotHealthMonitor, HealthStatus, AlertLevel
)
from context.context_manager import ContextManager, ContextType, ContextPriority
from context.knowledge_graph import KnowledgeGraph
from shared.information_sharing import InformationSharingSystem, InformationType, ShareScope, SharePriority
from security.authentication import AuthenticationManager, Permission, UserRole as Role
from security.encryption import DataEncryptionService as EncryptionService
from monitoring.alerting_system import AlertManager
from monitoring.metrics_dashboard import MetricsCollector, DashboardManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/logs/bot-orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Pydantic models for API
class TaskSubmissionRequest(BaseModel):
    description: str = Field(..., description="Task description")
    priority: str = Field(default="MEDIUM", description="Task priority: LOW, MEDIUM, HIGH, CRITICAL")
    estimated_tokens: int = Field(default=5000, description="Estimated token usage")
    context: str = Field(default="", description="Additional context for the task")
    tags: list[str] = Field(default_factory=list, description="Task tags")
    dependencies: list[str] = Field(default_factory=list, description="Task dependencies")

class ExecutionPlanRequest(BaseModel):
    tasks: list[str] = Field(..., description="List of task IDs")
    strategy: str = Field(default="PARALLEL", description="Execution strategy")
    max_parallel_tasks: int = Field(default=5, description="Maximum parallel tasks")
    timeout: int = Field(default=3600, description="Timeout in seconds")

class ContextAddRequest(BaseModel):
    context_type: str = Field(..., description="Context type")
    content: str = Field(..., description="Context content")
    priority: str = Field(default="MEDIUM", description="Context priority")
    tags: list[str] = Field(default_factory=list, description="Context tags")
    expires_in_hours: Optional[int] = Field(default=None, description="Expiration in hours")

class InformationShareRequest(BaseModel):
    info_type: str = Field(..., description="Information type")
    title: str = Field(..., description="Information title")
    content: str = Field(..., description="Information content")
    scope: str = Field(default="TEAM_LEVEL", description="Share scope")
    priority: str = Field(default="MEDIUM", description="Information priority")
    tags: list[str] = Field(default_factory=list, description="Information tags")
    expires_in_hours: Optional[int] = Field(default=None, description="Expiration in hours")

class BotRegistrationRequest(BaseModel):
    bot_id: str = Field(..., description="Bot ID")
    capabilities: Dict[str, Any] = Field(..., description="Bot capabilities")
    max_concurrent: int = Field(default=3, description="Max concurrent tasks")

class UserRegistrationRequest(BaseModel):
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password", min_length=8)
    full_name: str = Field(default="", description="Full name")

class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")
    totp_token: Optional[str] = Field(default=None, description="TOTP token for MFA")

class APIKeyRequest(BaseModel):
    name: str = Field(..., description="API key name")
    permissions: list[str] = Field(default_factory=list, description="Permissions")
    expires_in_days: Optional[int] = Field(default=None, description="Expiration in days")

# Global orchestration system
class BotOrchestrationSystem:
    def __init__(self):
        self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.claude_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        # Core components
        self.claude_director = None
        self.task_queue_manager = None
        self.parallel_executor = None
        self.health_monitor = None
        self.context_manager = None
        self.knowledge_graph = None
        self.information_sharing = None
        
        # Security components
        self.auth_manager = None
        self.encryption_service = None
        
        # Monitoring components
        self.alert_manager = None
        self.metrics_collector = None
        self.dashboard_manager = None
        
        # System state
        self.running = False
        self.startup_time = None
    
    async def start(self):
        """Start all orchestration components"""
        try:
            logger.info("Starting Bot Orchestration System...")
            
            # Initialize security components first
            self.encryption_service = EncryptionService()
            # EncryptionService doesn't have async start method
            
            self.auth_manager = AuthenticationManager()
            # AuthenticationManager doesn't have async start method
            
            # Initialize monitoring components
            self.alert_manager = AlertManager()
            # AlertManager doesn't have async start method based on the code
            
            self.metrics_collector = MetricsCollector()
            # MetricsCollector doesn't have async start method based on the code
            
            self.dashboard_manager = DashboardManager()
            # DashboardManager doesn't have async start method based on the code
            
            # Initialize Claude Director
            self.claude_director = ClaudeDirector(self.claude_api_key)
            await self.claude_director.start()
            
            # Initialize Task Queue Manager
            self.task_queue_manager = TaskQueueManager()
            await self.task_queue_manager.start()
            
            # Initialize Parallel Executor
            self.parallel_executor = ParallelExecutor()
            await self.parallel_executor.start()
            
            # Initialize Health Monitor
            self.health_monitor = BotHealthMonitor()
            await self.health_monitor.start()
            
            # Initialize Context Manager  
            self.context_manager = ContextManager(self.claude_director.claude_api)
            # ContextManager doesn't have async start method
            
            # Initialize Knowledge Graph
            self.knowledge_graph = KnowledgeGraph(self.claude_director.claude_api)
            await self.knowledge_graph.start()
            
            # Initialize Information Sharing
            self.information_sharing = InformationSharingSystem(self.claude_director.claude_api)
            await self.information_sharing.start()
            
            self.running = True
            self.startup_time = datetime.now()
            
            logger.info("Bot Orchestration System started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Bot Orchestration System: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop all orchestration components"""
        logger.info("Stopping Bot Orchestration System...")
        self.running = False
        
        # Only stop components that have async stop methods
        async_components = [
            (self.information_sharing, "Information Sharing"),
            (self.knowledge_graph, "Knowledge Graph"),
            (self.health_monitor, "Health Monitor"),
            (self.parallel_executor, "Parallel Executor"),
            (self.task_queue_manager, "Task Queue Manager"),
            (self.claude_director, "Claude Director")
        ]
        
        for component, name in async_components:
            if component:
                try:
                    await component.stop()
                    logger.info(f"Stopped {name}")
                except Exception as e:
                    logger.error(f"Error stopping {name}: {e}")
        
        # Clean up other components
        self.context_manager = None
        self.dashboard_manager = None
        self.metrics_collector = None
        self.alert_manager = None
        self.auth_manager = None
        self.encryption_service = None
        
        logger.info("Bot Orchestration System stopped")

# Global system instance
orchestration_system = BotOrchestrationSystem()

# FastAPI lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await orchestration_system.start()
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(orchestration_system.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    yield
    
    # Shutdown
    await orchestration_system.stop()

# FastAPI app
app = FastAPI(
    title="Bot Orchestration System",
    description="Intelligent bot orchestration with Claude Director integration",
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

# Security setup
security = HTTPBearer()

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from JWT token"""
    try:
        token = credentials.credentials
        user = await orchestration_system.auth_manager.validate_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# API key authentication dependency
async def verify_api_key(request: Request):
    """Verify API key from header or query parameter"""
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    is_valid = await orchestration_system.auth_manager.validate_api_key(api_key)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return api_key

# Permission checking dependency
def require_permission(permission: Permission):
    """Dependency factory for permission checking"""
    async def check_permission(user = Depends(get_current_user)):
        if not orchestration_system.auth_manager.has_permission(user.id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}"
            )
        return user
    return check_permission

# Alternative API key authentication endpoints (for service-to-service communication)
@app.get("/api/tasks/queue/status")
async def get_queue_status_api_key(api_key: str = Depends(verify_api_key)):
    """Get task queue status (API key authenticated)"""
    try:
        status = await orchestration_system.task_queue_manager.get_system_status()
        return status
    
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check_api_key(api_key: str = Depends(verify_api_key)):
    """System health check (API key authenticated)"""
    if not orchestration_system.running:
        raise HTTPException(status_code=503, detail="System not running")
    
    return {
        "status": "healthy",
        "uptime_seconds": (datetime.now() - orchestration_system.startup_time).total_seconds(),
        "authenticated_via": "api_key"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    if not orchestration_system.running:
        raise HTTPException(status_code=503, detail="System not running")
    
    return {
        "status": "healthy",
        "uptime_seconds": (datetime.now() - orchestration_system.startup_time).total_seconds(),
        "components": {
            "claude_director": hasattr(orchestration_system.claude_director, 'running') and orchestration_system.claude_director.running,
            "task_queue": hasattr(orchestration_system.task_queue_manager, 'running') and orchestration_system.task_queue_manager.running,
            "parallel_executor": hasattr(orchestration_system.parallel_executor, 'running') and orchestration_system.parallel_executor.running,
            "health_monitor": hasattr(orchestration_system.health_monitor, 'running') and orchestration_system.health_monitor.running,
            "context_manager": hasattr(orchestration_system.context_manager, 'running') and orchestration_system.context_manager.running,
            "knowledge_graph": hasattr(orchestration_system.knowledge_graph, 'running') and orchestration_system.knowledge_graph.running,
            "information_sharing": hasattr(orchestration_system.information_sharing, 'running') and orchestration_system.information_sharing.running
        }
    }

# Task Management Endpoints
@app.post("/tasks/submit")
async def submit_task(request: TaskSubmissionRequest):
    """Submit a new task for execution"""
    try:
        priority = TaskPriority[request.priority.upper()]
        
        task_id = await orchestration_system.claude_director.submit_task(
            description=request.description,
            priority=priority,
            estimated_tokens=request.estimated_tokens,
            context=request.context
        )
        
        return {
            "task_id": task_id,
            "status": "submitted",
            "message": f"Task {task_id} submitted successfully"
        }
    
    except Exception as e:
        logger.error(f"Task submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks/{task_id}/execute")
async def execute_task(task_id: str, background_tasks: BackgroundTasks):
    """Execute a specific task"""
    try:
        # Execute task in background
        result = await orchestration_system.claude_director.execute_task(task_id)
        
        return {
            "task_id": task_id,
            "execution_result": result
        }
    
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """Get task status and details"""
    try:
        status = await orchestration_system.claude_director.get_task_status(task_id)
        return status
    
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/queue/status")
async def get_queue_status():
    """Get task queue status"""
    try:
        status = await orchestration_system.task_queue_manager.get_system_status()
        return status
    
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Parallel Execution Endpoints
@app.post("/execution/plan")
async def create_execution_plan(request: ExecutionPlanRequest):
    """Create and execute a parallel execution plan"""
    try:
        from coordination.parallel_executor import ExecutionPlan, ExecutionStrategy
        
        strategy = ExecutionStrategy(request.strategy.lower())
        
        plan = ExecutionPlan(
            id=f"plan_{int(datetime.now().timestamp())}",
            tasks=request.tasks,
            strategy=strategy,
            max_parallel_tasks=request.max_parallel_tasks,
            timeout=request.timeout
        )
        
        # Simple task executor function
        def simple_task_executor(task_id: str, context: dict) -> str:
            return f"Executed task {task_id} with context {context}"
        
        result = await orchestration_system.parallel_executor.execute_plan(
            plan, simple_task_executor
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Execution plan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/execution/status")
async def get_execution_status():
    """Get parallel execution system status"""
    try:
        status = orchestration_system.parallel_executor.get_system_status()
        return status
    
    except Exception as e:
        logger.error(f"Failed to get execution status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bot Management Endpoints
@app.post("/bots/register")
async def register_bot(request: BotRegistrationRequest):
    """Register a new bot with the orchestration system"""
    try:
        # Register with parallel executor
        orchestration_system.parallel_executor.register_bot(
            request.bot_id, 
            request.capabilities, 
            request.max_concurrent
        )
        
        # Register with health monitor
        orchestration_system.health_monitor.register_bot(request.bot_id)
        
        return {
            "bot_id": request.bot_id,
            "status": "registered",
            "message": f"Bot {request.bot_id} registered successfully"
        }
    
    except Exception as e:
        logger.error(f"Bot registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/bots/{bot_id}")
async def unregister_bot(bot_id: str):
    """Unregister a bot from the orchestration system"""
    try:
        orchestration_system.parallel_executor.unregister_bot(bot_id)
        orchestration_system.health_monitor.unregister_bot(bot_id)
        
        return {
            "bot_id": bot_id,
            "status": "unregistered",
            "message": f"Bot {bot_id} unregistered successfully"
        }
    
    except Exception as e:
        logger.error(f"Bot unregistration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bots/{bot_id}/health")
async def get_bot_health(bot_id: str):
    """Get bot health information"""
    try:
        health = orchestration_system.health_monitor.get_bot_health(bot_id)
        if health is None:
            raise HTTPException(status_code=404, detail=f"Bot {bot_id} not found")
        return health
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get bot health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bots/health/overview")
async def get_health_overview():
    """Get system-wide health overview"""
    try:
        overview = orchestration_system.health_monitor.get_system_health_overview()
        return overview
    
    except Exception as e:
        logger.error(f"Failed to get health overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Context Management Endpoints
@app.post("/context/add")
async def add_context(request: ContextAddRequest):
    """Add context information"""
    try:
        context_type = ContextType[request.context_type.upper()]
        priority = ContextPriority[request.priority.upper()]
        
        context_id = await orchestration_system.context_manager.add_context(
            context_type=context_type,
            content=request.content,
            priority=priority,
            tags=set(request.tags),
            expires_in_hours=request.expires_in_hours
        )
        
        return {
            "context_id": context_id,
            "status": "added",
            "message": f"Context {context_id} added successfully"
        }
    
    except Exception as e:
        logger.error(f"Context addition failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/context/optimized")
async def get_optimized_context(
    task_description: str,
    max_tokens: Optional[int] = None,
    include_types: Optional[str] = None
):
    """Get optimized context for a task"""
    try:
        include_type_list = None
        if include_types:
            include_type_list = [ContextType[t.upper()] for t in include_types.split(",")]
        
        context = await orchestration_system.context_manager.get_optimized_context(
            task_description=task_description,
            max_tokens=max_tokens,
            include_types=include_type_list
        )
        
        return {
            "context": context,
            "task_description": task_description
        }
    
    except Exception as e:
        logger.error(f"Failed to get optimized context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/context/stats")
async def get_context_stats():
    """Get context management statistics"""
    try:
        stats = await orchestration_system.context_manager.get_context_stats()
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get context stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Knowledge Graph Endpoints
@app.post("/knowledge/add")
async def add_knowledge(
    content: str,
    content_type: str = "",
    source: str = "",
    metadata: Optional[Dict[str, Any]] = None
):
    """Add content to knowledge graph"""
    try:
        result = await orchestration_system.knowledge_graph.add_content(
            content=content,
            content_type=content_type,
            source=source,
            metadata=metadata or {}
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Knowledge addition failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge/context")
async def get_knowledge_context(
    query: str,
    max_depth: int = 2,
    max_nodes: int = 50
):
    """Get related context from knowledge graph"""
    try:
        context = await orchestration_system.knowledge_graph.get_related_context(
            query=query,
            max_depth=max_depth,
            max_nodes=max_nodes
        )
        
        return context
    
    except Exception as e:
        logger.error(f"Knowledge context retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge/stats")
async def get_knowledge_stats():
    """Get knowledge graph statistics"""
    try:
        stats = orchestration_system.knowledge_graph.get_graph_stats()
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get knowledge stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Information Sharing Endpoints
@app.post("/information/share")
async def share_information(request: InformationShareRequest, bot_id: str = "api_user"):
    """Share information between bots"""
    try:
        info_type = InformationType[request.info_type.upper()]
        scope = ShareScope[request.scope.upper()]
        priority = SharePriority[request.priority.upper()]
        
        info_id = await orchestration_system.information_sharing.share_information(
            bot_id=bot_id,
            info_type=info_type,
            title=request.title,
            content=request.content,
            scope=scope,
            priority=priority,
            tags=set(request.tags),
            expires_in_hours=request.expires_in_hours
        )
        
        return {
            "information_id": info_id,
            "status": "shared",
            "message": f"Information {info_id} shared successfully"
        }
    
    except Exception as e:
        logger.error(f"Information sharing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/information/relevant")
async def get_relevant_information(
    query: str,
    bot_id: str = "api_user",
    info_types: Optional[str] = None,
    max_results: int = 20
):
    """Get information relevant to a query"""
    try:
        info_type_list = None
        if info_types:
            info_type_list = [InformationType[t.upper()] for t in info_types.split(",")]
        
        information = await orchestration_system.information_sharing.get_relevant_information(
            bot_id=bot_id,
            query=query,
            info_types=info_type_list,
            max_results=max_results
        )
        
        return {
            "query": query,
            "information": [info.to_dict() for info in information]
        }
    
    except Exception as e:
        logger.error(f"Information retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/information/synthesize")
async def synthesize_knowledge(topic: str, bot_id: str = "api_user"):
    """Synthesize knowledge on a topic"""
    try:
        synthesis = await orchestration_system.information_sharing.synthesize_knowledge(
            bot_id=bot_id,
            topic=topic
        )
        
        if synthesis is None:
            return {
                "topic": topic,
                "status": "insufficient_data",
                "message": "Insufficient information to synthesize knowledge"
            }
        
        return {
            "topic": topic,
            "synthesis": synthesis.to_dict(),
            "status": "synthesized"
        }
    
    except Exception as e:
        logger.error(f"Knowledge synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/information/stats")
async def get_sharing_stats():
    """Get information sharing statistics"""
    try:
        stats = orchestration_system.information_sharing.get_sharing_stats()
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get sharing stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System Metrics Endpoint
@app.get("/metrics")
async def get_system_metrics():
    """Get comprehensive system metrics"""
    try:
        metrics = await orchestration_system.claude_director.get_system_metrics()
        
        # Add additional metrics from other components
        metrics["queue_status"] = await orchestration_system.task_queue_manager.get_system_status()
        metrics["health_overview"] = orchestration_system.health_monitor.get_system_health_overview()
        metrics["context_stats"] = await orchestration_system.context_manager.get_context_stats()
        metrics["knowledge_stats"] = orchestration_system.knowledge_graph.get_graph_stats()
        metrics["sharing_stats"] = orchestration_system.information_sharing.get_sharing_stats()
        
        return metrics
    
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Main application entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Bot Orchestration System")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8450, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    # Configure uvicorn
    uvicorn_config = {
        "app": "main:app",
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "access_log": True,
    }
    
    if args.reload:
        uvicorn_config["reload"] = True
    else:
        uvicorn_config["workers"] = args.workers
    
    # Start server
    logger.info(f"Starting Bot Orchestration System on {args.host}:{args.port}")
    uvicorn.run(**uvicorn_config)