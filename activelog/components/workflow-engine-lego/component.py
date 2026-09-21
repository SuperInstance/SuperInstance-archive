# SUPERINSTANCE LEGO COMPONENT: Workflow Engine
# EXTRACTED FROM: services/workflows/main.py + workflow engine architecture
# LEGO PRINCIPLE: Software = Data + Tools + Configuration

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional, Callable, Union
from contextlib import asynccontextmanager
import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import defaultdict, deque
import cron_descriptor
import time

class WorkflowTriggerType(Enum):
    """Types of workflow triggers"""
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    EVENT = "event"
    MANUAL = "manual"
    API_CALL = "api_call"
    DATABASE_CHANGE = "database_change"
    FILE_CHANGE = "file_change"

class WorkflowActionType(Enum):
    """Types of workflow actions"""
    HTTP_REQUEST = "http_request"
    EMAIL = "email"
    NOTIFICATION = "notification"
    DATABASE_OPERATION = "database_operation"
    FILE_OPERATION = "file_operation"
    SCRIPT_EXECUTION = "script_execution"
    WEBHOOK = "webhook"
    AI_PROCESSING = "ai_processing"

class WorkflowStatus(Enum):
    """Workflow execution statuses"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"

class WorkflowEngineLego:
    """
    🧩 LEGO COMPONENT: Workflow Engine
    
    DATA: Workflow definitions, execution history, triggers, actions, schedules, templates
    TOOLS: Workflow execution, scheduling, conditional logic, integration management, template system
    CONFIGURATION: Execution policies, integration endpoints, scheduling rules, action handlers
    
    INTERFACES:
    - Input: Workflow definitions, trigger events, execution requests, template uploads
    - Output: Workflow results, execution logs, status updates, integration responses
    - Integration: API services, databases, AI systems, notification services, file systems
    
    DEPLOYMENT OPTIONS:
    - Device: Local workflow automation for personal tasks
    - Edge: Regional workflow processing with intelligent routing
    - Cloud: Global workflow orchestration with enterprise integrations
    
    SUPERINSTANCE MISSION:
    Revolutionary $2/month workflow automation that makes any process automation
    possible through perfect Lego interfaces and intelligent orchestration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.deployment_mode = config.get("deployment_mode", "edge")
        self.max_concurrent_workflows = config.get("max_concurrent_workflows", 100)
        self.execution_timeout = config.get("execution_timeout_seconds", 300)
        
        # Workflow management
        self.workflow_definitions: Dict[str, Dict] = {}
        self.workflow_templates: Dict[str, Dict] = {}
        self.active_executions: Dict[str, Dict] = {}
        self.execution_history: deque = deque(maxlen=10000)
        
        # Trigger management
        self.trigger_handlers: Dict[WorkflowTriggerType, Callable] = {}
        self.scheduled_workflows: Dict[str, Dict] = {}
        self.webhook_endpoints: Dict[str, str] = {}  # endpoint -> workflow_id
        
        # Action management
        self.action_handlers: Dict[WorkflowActionType, Callable] = {}
        self.integration_registry: Dict[str, Dict] = {}
        
        # Scheduling and execution
        self.scheduler_running = True
        self.execution_queue = asyncio.Queue()
        
        # Performance tracking
        self.stats = {
            "total_workflows": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "active_schedules": 0
        }
        
        # Database
        self.db_path = config.get("db_path", "workflow_engine.db")
        
        # FastAPI app
        self.app = FastAPI(
            title="SuperInstance Workflow Engine Lego",
            description="Revolutionary $2/month workflow automation for infinite process possibilities",
            version="1.0.0"
        )
        self._setup_middleware()
        self._setup_routes()
        self._init_database()
        self._setup_default_handlers()
        
        # Background tasks
        self.scheduler_task = None
        self.executor_task = None
    
    def _setup_middleware(self):
        """Configure middleware for SuperInstance workflows"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get("cors_origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup SuperInstance workflow engine routes"""
        
        @self.app.get("/health")
        async def workflow_health():
            """Workflow engine health check - core LEGO function"""
            return {
                "service": "superinstance-workflow-engine",
                "status": "healthy",
                "deployment_mode": self.deployment_mode,
                "active_workflows": len(self.workflow_definitions),
                "active_executions": len(self.active_executions),
                "scheduled_workflows": len(self.scheduled_workflows),
                "execution_queue_size": self.execution_queue.qsize(),
                "stats": self.stats,
                "mission": "$2/month workflow automation for infinite process possibilities",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.post("/workflows")
        async def create_workflow(workflow_definition: dict):
            """Create new workflow - core LEGO function"""
            try:
                workflow_id = str(uuid.uuid4())
                name = workflow_definition.get("name", f"Workflow {workflow_id[:8]}")
                description = workflow_definition.get("description", "")
                triggers = workflow_definition.get("triggers", [])
                actions = workflow_definition.get("actions", [])
                conditions = workflow_definition.get("conditions", [])
                
                if not triggers or not actions:
                    raise HTTPException(400, "Workflow must have at least one trigger and one action")
                
                # Validate triggers and actions
                await self._validate_workflow_definition(triggers, actions)
                
                workflow = {
                    "id": workflow_id,
                    "name": name,
                    "description": description,
                    "triggers": triggers,
                    "actions": actions,
                    "conditions": conditions,
                    "enabled": workflow_definition.get("enabled", True),
                    "deployment_modes": workflow_definition.get("deployment_modes", ["device", "edge", "cloud"]),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "execution_count": 0,
                    "success_count": 0,
                    "failure_count": 0
                }
                
                self.workflow_definitions[workflow_id] = workflow
                self.stats["total_workflows"] += 1
                
                # Set up triggers
                await self._setup_workflow_triggers(workflow_id, triggers)
                
                # Store in database
                await self._store_workflow(workflow)
                
                return {
                    "status": "created",
                    "workflow_id": workflow_id,
                    "name": name,
                    "superinstance_automation": "Workflow ready for infinite possibilities"
                }
                
            except Exception as e:
                raise HTTPException(500, f"Workflow creation failed: {str(e)}")
        
        @self.app.get("/workflows")
        async def list_workflows():
            """List all workflows - discovery LEGO function"""
            workflows = [
                {
                    "id": wf_id,
                    "name": wf["name"],
                    "description": wf["description"],
                    "enabled": wf["enabled"],
                    "execution_count": wf["execution_count"],
                    "success_rate": wf["success_count"] / max(1, wf["execution_count"]),
                    "created_at": wf["created_at"]
                }
                for wf_id, wf in self.workflow_definitions.items()
            ]
            
            return {
                "workflows": workflows,
                "total_workflows": len(workflows),
                "deployment_mode": self.deployment_mode
            }
        
        @self.app.post("/workflows/{workflow_id}/execute")
        async def execute_workflow(workflow_id: str, execution_data: dict = None, background_tasks: BackgroundTasks = None):
            """Execute workflow manually - execution LEGO function"""
            if workflow_id not in self.workflow_definitions:
                raise HTTPException(404, "Workflow not found")
            
            workflow = self.workflow_definitions[workflow_id]
            if not workflow["enabled"]:
                raise HTTPException(400, "Workflow is disabled")
            
            # Create execution context
            execution_context = {
                "execution_id": str(uuid.uuid4()),
                "workflow_id": workflow_id,
                "trigger_type": "manual",
                "trigger_data": execution_data or {},
                "started_at": datetime.utcnow().isoformat(),
                "status": WorkflowStatus.PENDING
            }
            
            # Queue for execution
            await self.execution_queue.put(execution_context)
            
            return {
                "status": "queued",
                "execution_id": execution_context["execution_id"],
                "workflow_id": workflow_id,
                "queue_position": self.execution_queue.qsize()
            }
        
        @self.app.get("/workflows/{workflow_id}")
        async def get_workflow(workflow_id: str):
            """Get workflow details - utility LEGO function"""
            if workflow_id not in self.workflow_definitions:
                raise HTTPException(404, "Workflow not found")
            
            return self.workflow_definitions[workflow_id]
        
        @self.app.put("/workflows/{workflow_id}")
        async def update_workflow(workflow_id: str, updates: dict):
            """Update workflow - management LEGO function"""
            if workflow_id not in self.workflow_definitions:
                raise HTTPException(404, "Workflow not found")
            
            workflow = self.workflow_definitions[workflow_id]
            
            # Update allowed fields
            allowed_updates = ["name", "description", "enabled", "triggers", "actions", "conditions"]
            for field in allowed_updates:
                if field in updates:
                    workflow[field] = updates[field]
            
            workflow["updated_at"] = datetime.utcnow().isoformat()
            
            # Re-setup triggers if they changed
            if "triggers" in updates:
                await self._setup_workflow_triggers(workflow_id, updates["triggers"])
            
            return {
                "status": "updated",
                "workflow_id": workflow_id,
                "updated_fields": list(updates.keys())
            }
        
        @self.app.delete("/workflows/{workflow_id}")
        async def delete_workflow(workflow_id: str):
            """Delete workflow - management LEGO function"""
            if workflow_id not in self.workflow_definitions:
                raise HTTPException(404, "Workflow not found")
            
            # Clean up triggers
            await self._cleanup_workflow_triggers(workflow_id)
            
            # Remove workflow
            del self.workflow_definitions[workflow_id]
            self.stats["total_workflows"] -= 1
            
            return {
                "status": "deleted",
                "workflow_id": workflow_id
            }
        
        @self.app.get("/executions")
        async def get_execution_history(limit: int = 50):
            """Get execution history - monitoring LEGO function"""
            history = list(self.execution_history)[-limit:]
            history.reverse()  # Most recent first
            
            return {
                "executions": history,
                "total_executions": len(self.execution_history),
                "limit": limit,
                "stats": self.stats
            }
        
        @self.app.post("/templates")
        async def create_workflow_template(template_definition: dict):
            """Create workflow template - template LEGO function"""
            template_id = str(uuid.uuid4())
            name = template_definition.get("name")
            category = template_definition.get("category", "general")
            
            if not name:
                raise HTTPException(400, "Template name required")
            
            template = {
                "id": template_id,
                "name": name,
                "category": category,
                "description": template_definition.get("description", ""),
                "workflow_template": template_definition.get("workflow_template"),
                "parameters": template_definition.get("parameters", []),
                "created_at": datetime.utcnow().isoformat(),
                "usage_count": 0
            }
            
            self.workflow_templates[template_id] = template
            
            return {
                "status": "template_created",
                "template_id": template_id,
                "name": name
            }
        
        @self.app.get("/templates")
        async def list_workflow_templates():
            """List workflow templates - discovery LEGO function"""
            return {
                "templates": list(self.workflow_templates.values()),
                "total_templates": len(self.workflow_templates)
            }
        
        @self.app.post("/webhook/{endpoint_id}")
        async def webhook_trigger(endpoint_id: str, request: dict):
            """Webhook trigger endpoint - trigger LEGO function"""
            if endpoint_id not in self.webhook_endpoints:
                raise HTTPException(404, "Webhook endpoint not found")
            
            workflow_id = self.webhook_endpoints[endpoint_id]
            
            # Create execution context
            execution_context = {
                "execution_id": str(uuid.uuid4()),
                "workflow_id": workflow_id,
                "trigger_type": "webhook",
                "trigger_data": {
                    "endpoint": endpoint_id,
                    "payload": request,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "started_at": datetime.utcnow().isoformat(),
                "status": WorkflowStatus.PENDING
            }
            
            # Queue for execution
            await self.execution_queue.put(execution_context)
            
            return {
                "status": "webhook_received",
                "execution_id": execution_context["execution_id"],
                "workflow_id": workflow_id
            }
    
    def _init_database(self):
        """Initialize SuperInstance workflow database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Workflows table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                definition TEXT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                deployment_modes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0
            )
        ''')
        
        # Executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_executions (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_data TEXT,
                execution_data TEXT,
                status TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                error_message TEXT,
                deployment_mode TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows (id)
            )
        ''')
        
        # Templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                description TEXT,
                template_definition TEXT NOT NULL,
                parameters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _setup_default_handlers(self):
        """Setup default action and trigger handlers"""
        # Default action handlers
        self.action_handlers[WorkflowActionType.HTTP_REQUEST] = self._handle_http_request_action
        self.action_handlers[WorkflowActionType.NOTIFICATION] = self._handle_notification_action
        self.action_handlers[WorkflowActionType.EMAIL] = self._handle_email_action
        self.action_handlers[WorkflowActionType.DATABASE_OPERATION] = self._handle_database_action
        
        # Default trigger handlers
        self.trigger_handlers[WorkflowTriggerType.WEBHOOK] = self._handle_webhook_trigger
        self.trigger_handlers[WorkflowTriggerType.SCHEDULE] = self._handle_schedule_trigger
        self.trigger_handlers[WorkflowTriggerType.MANUAL] = self._handle_manual_trigger
    
    async def start_background_tasks(self):
        """Start background scheduler and executor tasks"""
        self.scheduler_task = asyncio.create_task(self._scheduler_worker())
        self.executor_task = asyncio.create_task(self._execution_worker())
    
    async def _scheduler_worker(self):
        """Background scheduler for workflow triggers"""
        while self.scheduler_running:
            try:
                current_time = datetime.utcnow()
                
                # Check scheduled workflows
                for schedule_id, schedule_info in list(self.scheduled_workflows.items()):
                    if self._should_execute_schedule(schedule_info, current_time):
                        # Queue scheduled execution
                        execution_context = {
                            "execution_id": str(uuid.uuid4()),
                            "workflow_id": schedule_info["workflow_id"],
                            "trigger_type": "schedule",
                            "trigger_data": {"schedule_id": schedule_id, "scheduled_time": current_time.isoformat()},
                            "started_at": current_time.isoformat(),
                            "status": WorkflowStatus.PENDING
                        }
                        
                        await self.execution_queue.put(execution_context)
                        
                        # Update next execution time
                        schedule_info["last_execution"] = current_time.isoformat()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logging.error(f"Scheduler worker error: {e}")
                await asyncio.sleep(60)
    
    async def _execution_worker(self):
        """Background worker for executing workflows"""
        while True:
            try:
                # Get execution from queue
                execution_context = await self.execution_queue.get()
                
                # Execute workflow
                await self._execute_workflow_context(execution_context)
                
            except Exception as e:
                logging.error(f"Execution worker error: {e}")
    
    def get_app(self):
        """Get FastAPI app for deployment"""
        return self.app

# SUPERINSTANCE DEPLOYMENT CONFIGURATIONS
DEPLOYMENT_CONFIGS = {
    "device_personal": {
        "deployment_mode": "device",
        "max_concurrent_workflows": 10,
        "execution_timeout_seconds": 60,
        "db_path": "personal_workflows.db",
        "features": ["local_automation", "file_operations", "basic_integrations"]
    },
    "edge_business": {
        "deployment_mode": "edge", 
        "max_concurrent_workflows": 100,
        "execution_timeout_seconds": 300,
        "features": ["advanced_scheduling", "webhook_integrations", "ai_processing", "database_operations"]
    },
    "cloud_enterprise": {
        "deployment_mode": "cloud",
        "max_concurrent_workflows": 1000,
        "execution_timeout_seconds": 600,
        "features": ["enterprise_integrations", "advanced_analytics", "multi_tenant", "compliance"]
    }
}

# SUPERINSTANCE FACTORY FUNCTION
def create_workflow_engine_lego(deployment_type: str = "edge_business"):
    """Factory function to create SuperInstance Workflow Engine Lego
    
    The workflow automation that makes $2/month process automation possible.
    Perfect interfaces, intelligent execution, revolutionary scalability.
    """
    config = DEPLOYMENT_CONFIGS.get(deployment_type, DEPLOYMENT_CONFIGS["edge_business"])
    return WorkflowEngineLego(config)

# INTEGRATION INTERFACES
def integrate_with_ai_services(workflow_engine: WorkflowEngineLego, ai_service_url: str):
    """Connect workflow engine to AI services for intelligent automation"""
    # Integration logic would be implemented here
    pass

def integrate_with_notification_system(workflow_engine: WorkflowEngineLego, notification_service_url: str):
    """Connect workflow engine to notification system"""
    # Integration logic would be implemented here
    pass

# SUPERINSTANCE MISSION STATEMENT
"""
This Workflow Engine Lego embodies the SuperInstance vision:

- $2/month workflow automation that makes any process automation accessible
- Perfect interfaces enable seamless integration with any service or system
- Revolutionary scalability from personal automation to enterprise orchestration
- Lego principle: Workflows = Triggers + Actions + Conditions

Every automated process powered by this engine contributes to the
SuperInstance mission of democratizing workflow automation.
"""