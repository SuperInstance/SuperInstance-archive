#!/usr/bin/env python3
"""
Custom Workflow Designer System
Advanced visual workflow builder with drag-and-drop interface,
custom step definitions, conditional logic, and execution engine.
"""

import asyncio
import json
import logging
import sqlite3
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import networkx as nx
from dataclasses import dataclass, asdict
import yaml

logger = logging.getLogger(__name__)

class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    ERROR = "error"

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class StepType(str, Enum):
    ACTION = "action"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    DELAY = "delay"
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    API_CALL = "api_call"
    DATABASE = "database"
    CUSTOM = "custom"

class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    EVENT = "event"
    API = "api"
    EMAIL = "email"
    FILE_UPLOAD = "file_upload"

@dataclass
class WorkflowStep:
    id: str
    name: str
    step_type: StepType
    configuration: Dict[str, Any]
    position: Dict[str, float]
    inputs: List[str]
    outputs: List[str]
    conditions: List[Dict[str, Any]]
    timeout: Optional[int] = None
    retry_count: int = 0
    created_at: str = ""

@dataclass
class WorkflowConnection:
    id: str
    source_step: str
    target_step: str
    condition: Optional[Dict[str, Any]] = None
    label: str = ""

class CustomWorkflowSystem:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/enterprise-custom/data/enterprise_custom.db"
        self.workflows = {}
        self.workflow_executions = {}
        self.step_templates = {}
        self.execution_engine = None
        self.scheduler = None
        
    async def initialize(self):
        """Initialize the workflow system"""
        try:
            await self._setup_database_tables()
            await self._load_step_templates()
            await self._load_existing_workflows()
            await self._start_execution_engine()
            await self._start_scheduler()
            logger.info("Custom workflow system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize workflow system: {e}")
            raise

    async def _setup_database_tables(self):
        """Setup database tables for workflows"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Workflows table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                trigger_type TEXT NOT NULL,
                trigger_config TEXT,
                status TEXT DEFAULT 'draft',
                version INTEGER DEFAULT 1,
                steps TEXT NOT NULL,
                connections TEXT,
                variables TEXT,
                permissions TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES enterprise_organizations (id)
            )
        ''')
        
        # Workflow executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_executions (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                trigger_data TEXT,
                status TEXT DEFAULT 'pending',
                current_step TEXT,
                execution_context TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                execution_log TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workflow_id) REFERENCES workflows (id)
            )
        ''')
        
        # Step executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS step_executions (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                input_data TEXT,
                output_data TEXT,
                error_message TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_ms INTEGER,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (execution_id) REFERENCES workflow_executions (id)
            )
        ''')
        
        # Workflow templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                template_data TEXT NOT NULL,
                is_public BOOLEAN DEFAULT FALSE,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

    async def _load_step_templates(self):
        """Load predefined step templates"""
        self.step_templates = {
            "send_email": {
                "name": "Send Email",
                "type": StepType.NOTIFICATION,
                "description": "Send email notification",
                "inputs": {
                    "to": {"type": "string", "required": True},
                    "subject": {"type": "string", "required": True},
                    "body": {"type": "text", "required": True},
                    "cc": {"type": "string", "required": False},
                    "bcc": {"type": "string", "required": False}
                },
                "outputs": {
                    "success": {"type": "boolean"},
                    "message_id": {"type": "string"}
                },
                "icon": "mail",
                "color": "#4CAF50"
            },
            "http_request": {
                "name": "HTTP Request",
                "type": StepType.API_CALL,
                "description": "Make HTTP API call",
                "inputs": {
                    "url": {"type": "string", "required": True},
                    "method": {"type": "select", "options": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
                    "headers": {"type": "object", "required": False},
                    "body": {"type": "text", "required": False},
                    "timeout": {"type": "number", "default": 30}
                },
                "outputs": {
                    "status_code": {"type": "number"},
                    "response_body": {"type": "string"},
                    "headers": {"type": "object"}
                },
                "icon": "globe",
                "color": "#2196F3"
            },
            "condition": {
                "name": "Condition",
                "type": StepType.CONDITION,
                "description": "Conditional branching logic",
                "inputs": {
                    "condition": {"type": "expression", "required": True},
                    "true_path": {"type": "connection"},
                    "false_path": {"type": "connection"}
                },
                "outputs": {
                    "result": {"type": "boolean"}
                },
                "icon": "fork",
                "color": "#FF9800"
            },
            "delay": {
                "name": "Delay",
                "type": StepType.DELAY,
                "description": "Wait for specified duration",
                "inputs": {
                    "duration": {"type": "number", "required": True},
                    "unit": {"type": "select", "options": ["seconds", "minutes", "hours", "days"], "default": "minutes"}
                },
                "outputs": {
                    "completed": {"type": "boolean"}
                },
                "icon": "clock",
                "color": "#9C27B0"
            },
            "approval": {
                "name": "Approval",
                "type": StepType.APPROVAL,
                "description": "Request approval from user(s)",
                "inputs": {
                    "approvers": {"type": "array", "required": True},
                    "message": {"type": "text", "required": True},
                    "timeout_hours": {"type": "number", "default": 24},
                    "required_approvals": {"type": "number", "default": 1}
                },
                "outputs": {
                    "approved": {"type": "boolean"},
                    "approver": {"type": "string"},
                    "comments": {"type": "string"}
                },
                "icon": "check-circle",
                "color": "#FF5722"
            },
            "database_query": {
                "name": "Database Query",
                "type": StepType.DATABASE,
                "description": "Execute database query",
                "inputs": {
                    "connection_string": {"type": "string", "required": True},
                    "query": {"type": "text", "required": True},
                    "parameters": {"type": "object", "required": False}
                },
                "outputs": {
                    "rows": {"type": "array"},
                    "row_count": {"type": "number"}
                },
                "icon": "database",
                "color": "#607D8B"
            },
            "parallel_execution": {
                "name": "Parallel Execution",
                "type": StepType.PARALLEL,
                "description": "Execute multiple steps in parallel",
                "inputs": {
                    "branches": {"type": "array", "required": True},
                    "wait_for_all": {"type": "boolean", "default": True}
                },
                "outputs": {
                    "completed_branches": {"type": "array"},
                    "failed_branches": {"type": "array"}
                },
                "icon": "share-alt",
                "color": "#795548"
            }
        }

    async def _load_existing_workflows(self):
        """Load existing workflows from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, organization_id, data FROM workflows
            ''')
            
            workflows = cursor.fetchall()
            for workflow_id, org_id, data_json in workflows:
                workflow_data = json.loads(data_json)
                self.workflows[workflow_id] = workflow_data
                
            conn.close()
            logger.info(f"Loaded {len(workflows)} existing workflows")
        except Exception as e:
            logger.error(f"Failed to load existing workflows: {e}")

    async def _start_execution_engine(self):
        """Start the workflow execution engine"""
        self.execution_engine = asyncio.create_task(self._execution_engine_loop())

    async def _start_scheduler(self):
        """Start the workflow scheduler"""
        self.scheduler = asyncio.create_task(self._scheduler_loop())

    async def create_workflow(self, workflow_data: dict) -> Dict[str, Any]:
        """Create new workflow"""
        try:
            workflow_id = f"WF_{uuid.uuid4().hex[:12].upper()}"
            
            # Build workflow configuration
            workflow = {
                "id": workflow_id,
                "organization_id": workflow_data["organization_id"],
                "name": workflow_data["name"],
                "description": workflow_data.get("description", ""),
                "trigger_type": TriggerType(workflow_data["trigger_type"]),
                "trigger_config": workflow_data.get("trigger_config", {}),
                "status": WorkflowStatus.DRAFT,
                "version": 1,
                "steps": workflow_data.get("steps", []),
                "connections": workflow_data.get("connections", []),
                "variables": workflow_data.get("variables", {}),
                "permissions": {
                    "edit": workflow_data.get("editors", []),
                    "execute": workflow_data.get("executors", []),
                    "view": workflow_data.get("viewers", [])
                },
                "settings": {
                    "timeout_minutes": workflow_data.get("timeout_minutes", 60),
                    "retry_attempts": workflow_data.get("retry_attempts", 3),
                    "parallel_execution": workflow_data.get("parallel_execution", False),
                    "error_handling": workflow_data.get("error_handling", "stop")
                },
                "created_by": workflow_data.get("created_by", "system"),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Validate workflow
            validation_result = await self._validate_workflow(workflow)
            if not validation_result["valid"]:
                return {
                    "status": "error",
                    "message": "Workflow validation failed",
                    "errors": validation_result["errors"]
                }
            
            # Store workflow
            await self._store_workflow(workflow)
            
            self.workflows[workflow_id] = workflow
            
            return {
                "status": "success",
                "workflow_id": workflow_id,
                "name": workflow["name"],
                "trigger_type": workflow["trigger_type"],
                "step_count": len(workflow["steps"]),
                "editor_url": f"/workflows/{workflow_id}/editor",
                "next_steps": [
                    "Add workflow steps",
                    "Configure step connections",
                    "Test workflow execution",
                    "Activate workflow"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to create workflow: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _validate_workflow(self, workflow: dict) -> Dict[str, Any]:
        """Validate workflow configuration"""
        errors = []
        
        # Required fields
        required_fields = ["name", "organization_id", "trigger_type"]
        for field in required_fields:
            if not workflow.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate steps
        steps = workflow.get("steps", [])
        step_ids = set()
        
        for step in steps:
            step_id = step.get("id")
            if not step_id:
                errors.append("Step missing ID")
                continue
                
            if step_id in step_ids:
                errors.append(f"Duplicate step ID: {step_id}")
            step_ids.add(step_id)
            
            if not step.get("name"):
                errors.append(f"Step {step_id} missing name")
            
            if not step.get("step_type"):
                errors.append(f"Step {step_id} missing type")
        
        # Validate connections
        connections = workflow.get("connections", [])
        for connection in connections:
            source = connection.get("source_step")
            target = connection.get("target_step")
            
            if source not in step_ids:
                errors.append(f"Connection references unknown source step: {source}")
            if target not in step_ids:
                errors.append(f"Connection references unknown target step: {target}")
        
        # Check for circular dependencies
        if steps and connections:
            try:
                graph = nx.DiGraph()
                for step in steps:
                    graph.add_node(step["id"])
                for connection in connections:
                    graph.add_edge(connection["source_step"], connection["target_step"])
                
                if not nx.is_directed_acyclic_graph(graph):
                    errors.append("Workflow contains circular dependencies")
            except Exception:
                errors.append("Failed to validate workflow graph")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    async def _store_workflow(self, workflow: dict):
        """Store workflow in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO workflows 
                (id, organization_id, name, description, trigger_type, trigger_config,
                 status, version, steps, connections, variables, permissions,
                 created_by, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                workflow["id"], workflow["organization_id"], workflow["name"],
                workflow["description"], workflow["trigger_type"],
                json.dumps(workflow["trigger_config"]), workflow["status"],
                workflow["version"], json.dumps(workflow["steps"]),
                json.dumps(workflow["connections"]), json.dumps(workflow["variables"]),
                json.dumps(workflow["permissions"]), workflow["created_by"],
                json.dumps(workflow)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store workflow: {e}")
            raise

    async def get_organization_workflows(self, org_id: str) -> Dict[str, Any]:
        """Get workflows for organization"""
        try:
            org_workflows = [
                workflow for workflow in self.workflows.values()
                if workflow.get("organization_id") == org_id
            ]
            
            # Get execution statistics
            workflow_stats = []
            for workflow in org_workflows:
                stats = await self._get_workflow_statistics(workflow["id"])
                workflow_info = {
                    "id": workflow["id"],
                    "name": workflow["name"],
                    "description": workflow["description"],
                    "status": workflow["status"],
                    "trigger_type": workflow["trigger_type"],
                    "step_count": len(workflow.get("steps", [])),
                    "created_at": workflow["created_at"],
                    "updated_at": workflow["updated_at"],
                    "statistics": stats
                }
                workflow_stats.append(workflow_info)
            
            return {
                "status": "success",
                "workflows": workflow_stats,
                "total_count": len(org_workflows),
                "active_count": len([w for w in org_workflows if w["status"] == WorkflowStatus.ACTIVE]),
                "draft_count": len([w for w in org_workflows if w["status"] == WorkflowStatus.DRAFT])
            }
            
        except Exception as e:
            logger.error(f"Failed to get organization workflows: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _get_workflow_statistics(self, workflow_id: str) -> Dict[str, Any]:
        """Get execution statistics for workflow"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total executions
            cursor.execute('''
                SELECT COUNT(*) FROM workflow_executions WHERE workflow_id = ?
            ''', (workflow_id,))
            total_executions = cursor.fetchone()[0]
            
            # Successful executions
            cursor.execute('''
                SELECT COUNT(*) FROM workflow_executions 
                WHERE workflow_id = ? AND status = 'completed'
            ''', (workflow_id,))
            successful_executions = cursor.fetchone()[0]
            
            # Failed executions
            cursor.execute('''
                SELECT COUNT(*) FROM workflow_executions 
                WHERE workflow_id = ? AND status = 'failed'
            ''', (workflow_id,))
            failed_executions = cursor.fetchone()[0]
            
            # Average execution time
            cursor.execute('''
                SELECT AVG(
                    (JULIANDAY(completed_at) - JULIANDAY(started_at)) * 24 * 60
                ) as avg_minutes
                FROM workflow_executions 
                WHERE workflow_id = ? AND started_at IS NOT NULL AND completed_at IS NOT NULL
            ''', (workflow_id,))
            avg_duration = cursor.fetchone()[0] or 0
            
            # Last execution
            cursor.execute('''
                SELECT started_at, status FROM workflow_executions 
                WHERE workflow_id = ? ORDER BY started_at DESC LIMIT 1
            ''', (workflow_id,))
            last_execution = cursor.fetchone()
            
            conn.close()
            
            return {
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "failed_executions": failed_executions,
                "success_rate": (successful_executions / max(total_executions, 1)) * 100,
                "average_duration_minutes": round(avg_duration, 2),
                "last_execution": {
                    "date": last_execution[0] if last_execution else None,
                    "status": last_execution[1] if last_execution else None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get workflow statistics: {e}")
            return {}

    async def execute_workflow(self, workflow_id: str, execution_data: dict) -> Dict[str, Any]:
        """Execute workflow"""
        try:
            if workflow_id not in self.workflows:
                return {
                    "status": "error",
                    "message": "Workflow not found"
                }
            
            workflow = self.workflows[workflow_id]
            
            if workflow["status"] != WorkflowStatus.ACTIVE:
                return {
                    "status": "error",
                    "message": f"Workflow is not active (current status: {workflow['status']})"
                }
            
            # Create execution record
            execution_id = f"EXEC_{uuid.uuid4().hex[:12].upper()}"
            
            execution = {
                "id": execution_id,
                "workflow_id": workflow_id,
                "trigger_data": execution_data.get("trigger_data", {}),
                "status": ExecutionStatus.PENDING,
                "execution_context": {
                    "variables": workflow.get("variables", {}).copy(),
                    "input_data": execution_data.get("input_data", {}),
                    "user_id": execution_data.get("user_id"),
                    "started_by": execution_data.get("started_by", "system")
                },
                "execution_log": [],
                "current_step": None,
                "created_at": datetime.now().isoformat()
            }
            
            # Store execution record
            await self._store_execution(execution)
            
            self.workflow_executions[execution_id] = execution
            
            # Start execution (async)
            asyncio.create_task(self._execute_workflow_async(execution_id))
            
            return {
                "status": "success",
                "execution_id": execution_id,
                "workflow_name": workflow["name"],
                "execution_status": execution["status"],
                "monitor_url": f"/workflows/executions/{execution_id}"
            }
            
        except Exception as e:
            logger.error(f"Failed to execute workflow: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _store_execution(self, execution: dict):
        """Store execution record in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO workflow_executions
                (id, workflow_id, trigger_data, status, execution_context, execution_log)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                execution["id"], execution["workflow_id"],
                json.dumps(execution["trigger_data"]), execution["status"],
                json.dumps(execution["execution_context"]),
                json.dumps(execution["execution_log"])
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store execution: {e}")
            raise

    async def _execute_workflow_async(self, execution_id: str):
        """Execute workflow asynchronously"""
        try:
            execution = self.workflow_executions[execution_id]
            workflow = self.workflows[execution["workflow_id"]]
            
            # Update execution status
            execution["status"] = ExecutionStatus.RUNNING
            execution["started_at"] = datetime.now().isoformat()
            
            self._log_execution_event(execution_id, "info", "Workflow execution started")
            
            # Build execution graph
            execution_graph = self._build_execution_graph(workflow)
            
            # Execute steps
            success = await self._execute_steps(execution_id, execution_graph)
            
            # Update final status
            if success:
                execution["status"] = ExecutionStatus.COMPLETED
                self._log_execution_event(execution_id, "info", "Workflow execution completed successfully")
            else:
                execution["status"] = ExecutionStatus.FAILED
                self._log_execution_event(execution_id, "error", "Workflow execution failed")
            
            execution["completed_at"] = datetime.now().isoformat()
            
            # Update database
            await self._update_execution_status(execution_id, execution["status"])
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            execution = self.workflow_executions.get(execution_id)
            if execution:
                execution["status"] = ExecutionStatus.FAILED
                execution["error_message"] = str(e)
                await self._update_execution_status(execution_id, ExecutionStatus.FAILED)

    def _build_execution_graph(self, workflow: dict) -> nx.DiGraph:
        """Build execution graph from workflow"""
        graph = nx.DiGraph()
        
        # Add nodes (steps)
        for step in workflow.get("steps", []):
            graph.add_node(step["id"], step_data=step)
        
        # Add edges (connections)
        for connection in workflow.get("connections", []):
            graph.add_edge(
                connection["source_step"],
                connection["target_step"],
                connection_data=connection
            )
        
        return graph

    async def _execute_steps(self, execution_id: str, graph: nx.DiGraph) -> bool:
        """Execute workflow steps"""
        try:
            # Find starting nodes (no incoming edges)
            start_nodes = [node for node in graph.nodes() if graph.in_degree(node) == 0]
            
            if not start_nodes:
                self._log_execution_event(execution_id, "error", "No starting steps found")
                return False
            
            # Track completed steps
            completed_steps = set()
            failed_steps = set()
            
            # Execute in topological order
            for step_id in nx.topological_sort(graph):
                # Check if all prerequisites are met
                predecessors = list(graph.predecessors(step_id))
                if predecessors and not all(pred in completed_steps for pred in predecessors):
                    continue
                
                # Execute step
                step_data = graph.nodes[step_id]["step_data"]
                success = await self._execute_step(execution_id, step_data)
                
                if success:
                    completed_steps.add(step_id)
                else:
                    failed_steps.add(step_id)
                    # Depending on error handling strategy, might stop here
                    workflow = self.workflows[self.workflow_executions[execution_id]["workflow_id"]]
                    error_handling = workflow.get("settings", {}).get("error_handling", "stop")
                    
                    if error_handling == "stop":
                        self._log_execution_event(
                            execution_id, "error",
                            f"Step {step_id} failed, stopping execution"
                        )
                        return False
            
            return len(failed_steps) == 0
            
        except Exception as e:
            logger.error(f"Failed to execute steps: {e}")
            return False

    async def _execute_step(self, execution_id: str, step_data: dict) -> bool:
        """Execute individual step"""
        try:
            step_id = step_data["id"]
            step_type = step_data["step_type"]
            
            # Create step execution record
            step_execution_id = f"STEP_{uuid.uuid4().hex[:8].upper()}"
            
            step_execution = {
                "id": step_execution_id,
                "execution_id": execution_id,
                "step_id": step_id,
                "step_name": step_data["name"],
                "status": ExecutionStatus.RUNNING,
                "started_at": datetime.now().isoformat()
            }
            
            self._log_execution_event(
                execution_id, "info",
                f"Executing step: {step_data['name']} ({step_type})"
            )
            
            # Execute based on step type
            if step_type == StepType.NOTIFICATION:
                result = await self._execute_notification_step(step_data)
            elif step_type == StepType.API_CALL:
                result = await self._execute_api_call_step(step_data)
            elif step_type == StepType.CONDITION:
                result = await self._execute_condition_step(step_data)
            elif step_type == StepType.DELAY:
                result = await self._execute_delay_step(step_data)
            elif step_type == StepType.APPROVAL:
                result = await self._execute_approval_step(step_data)
            elif step_type == StepType.DATABASE:
                result = await self._execute_database_step(step_data)
            else:
                result = {"success": False, "error": f"Unknown step type: {step_type}"}
            
            # Update step execution
            step_execution["completed_at"] = datetime.now().isoformat()
            step_execution["output_data"] = json.dumps(result.get("output", {}))
            
            if result.get("success", False):
                step_execution["status"] = ExecutionStatus.COMPLETED
                self._log_execution_event(
                    execution_id, "info",
                    f"Step completed: {step_data['name']}"
                )
            else:
                step_execution["status"] = ExecutionStatus.FAILED
                step_execution["error_message"] = result.get("error", "Unknown error")
                self._log_execution_event(
                    execution_id, "error",
                    f"Step failed: {step_data['name']} - {result.get('error', 'Unknown error')}"
                )
            
            # Store step execution
            await self._store_step_execution(step_execution)
            
            return result.get("success", False)
            
        except Exception as e:
            logger.error(f"Failed to execute step: {e}")
            self._log_execution_event(
                execution_id, "error",
                f"Step execution error: {str(e)}"
            )
            return False

    async def _execute_notification_step(self, step_data: dict) -> Dict[str, Any]:
        """Execute notification step (email)"""
        try:
            config = step_data.get("configuration", {})
            
            # Simulate email sending
            await asyncio.sleep(0.5)  # Simulate processing time
            
            return {
                "success": True,
                "output": {
                    "message_id": f"MSG_{uuid.uuid4().hex[:8]}",
                    "sent_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_api_call_step(self, step_data: dict) -> Dict[str, Any]:
        """Execute API call step"""
        try:
            config = step_data.get("configuration", {})
            
            # Simulate API call
            await asyncio.sleep(1)  # Simulate network delay
            
            return {
                "success": True,
                "output": {
                    "status_code": 200,
                    "response_body": '{"result": "success"}',
                    "headers": {"content-type": "application/json"}
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_condition_step(self, step_data: dict) -> Dict[str, Any]:
        """Execute condition step"""
        try:
            config = step_data.get("configuration", {})
            condition = config.get("condition", "true")
            
            # Simple condition evaluation (in production, use safe expression evaluator)
            result = condition.lower() == "true"
            
            return {
                "success": True,
                "output": {
                    "result": result,
                    "condition": condition
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_delay_step(self, step_data: dict) -> Dict[str, Any]:
        """Execute delay step"""
        try:
            config = step_data.get("configuration", {})
            duration = config.get("duration", 1)
            unit = config.get("unit", "seconds")
            
            # Convert to seconds
            multipliers = {
                "seconds": 1,
                "minutes": 60,
                "hours": 3600,
                "days": 86400
            }
            
            delay_seconds = duration * multipliers.get(unit, 1)
            
            # For demo purposes, limit delay to 10 seconds
            delay_seconds = min(delay_seconds, 10)
            
            await asyncio.sleep(delay_seconds)
            
            return {
                "success": True,
                "output": {
                    "completed": True,
                    "delayed_seconds": delay_seconds
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_approval_step(self, step_data: dict) -> Dict[str, Any]:
        """Execute approval step"""
        try:
            # For demo purposes, simulate approval
            # In production, this would create approval requests
            
            config = step_data.get("configuration", {})
            
            # Simulate approval process
            await asyncio.sleep(2)
            
            return {
                "success": True,
                "output": {
                    "approved": True,
                    "approver": "demo_user",
                    "comments": "Auto-approved for demo"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_database_step(self, step_data: dict) -> Dict[str, Any]:
        """Execute database step"""
        try:
            config = step_data.get("configuration", {})
            
            # Simulate database query
            await asyncio.sleep(0.5)
            
            return {
                "success": True,
                "output": {
                    "rows": [{"id": 1, "name": "Sample"}, {"id": 2, "name": "Data"}],
                    "row_count": 2
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _store_step_execution(self, step_execution: dict):
        """Store step execution record"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO step_executions
                (id, execution_id, step_id, step_name, status, output_data,
                 error_message, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                step_execution["id"], step_execution["execution_id"],
                step_execution["step_id"], step_execution["step_name"],
                step_execution["status"], step_execution.get("output_data"),
                step_execution.get("error_message"), step_execution["started_at"],
                step_execution.get("completed_at")
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store step execution: {e}")

    def _log_execution_event(self, execution_id: str, level: str, message: str):
        """Log execution event"""
        if execution_id in self.workflow_executions:
            execution = self.workflow_executions[execution_id]
            execution["execution_log"].append({
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message
            })

    async def _update_execution_status(self, execution_id: str, status: ExecutionStatus):
        """Update execution status in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE workflow_executions 
                SET status = ?, execution_log = ?
                WHERE id = ?
            ''', (
                status,
                json.dumps(self.workflow_executions[execution_id]["execution_log"]),
                execution_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update execution status: {e}")

    async def _execution_engine_loop(self):
        """Main execution engine loop"""
        while True:
            try:
                # Process pending executions
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in execution engine loop: {e}")
                await asyncio.sleep(60)

    async def _scheduler_loop(self):
        """Scheduler loop for scheduled workflows"""
        while True:
            try:
                # Check for scheduled workflows
                current_time = datetime.now()
                
                for workflow in self.workflows.values():
                    if (workflow.get("trigger_type") == TriggerType.SCHEDULED and 
                        workflow.get("status") == WorkflowStatus.ACTIVE):
                        
                        trigger_config = workflow.get("trigger_config", {})
                        # Check if workflow should be triggered
                        # (Implementation would depend on schedule format)
                        pass
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(300)

# Global instance
custom_workflow_system = CustomWorkflowSystem()