"""
API routes for workflow automation service
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path, Body, Depends
from pydantic import BaseModel, Field

from core.database import db_manager, WorkflowStatus, ExecutionStatus

logger = logging.getLogger(__name__)

# Global references (set by main.py)
workflow_engine = None
workflow_scheduler = None
webhook_manager = None
integration_manager = None
template_manager = None

def get_workflow_engine():
    """Get workflow engine instance"""
    if not workflow_engine:
        raise HTTPException(status_code=503, detail="Workflow engine not available")
    return workflow_engine

def get_webhook_manager():
    """Get webhook manager instance"""
    if not webhook_manager:
        raise HTTPException(status_code=503, detail="Webhook manager not available")
    return webhook_manager

def get_scheduler():
    """Get workflow scheduler instance"""
    if not workflow_scheduler:
        raise HTTPException(status_code=503, detail="Workflow scheduler not available")
    return workflow_scheduler

def get_integration_manager():
    """Get integration manager instance"""
    if not integration_manager:
        raise HTTPException(status_code=503, detail="Integration manager not available")
    return integration_manager

def get_template_manager():
    """Get template manager instance"""
    if not template_manager:
        raise HTTPException(status_code=503, detail="Template manager not available")
    return template_manager

# Create router
router = APIRouter()

# Pydantic models for request/response
class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    owner_id: str = Field(..., description="Owner user ID")
    trigger_config: Dict[str, Any] = Field(..., description="Trigger configuration")
    actions: List[Dict[str, Any]] = Field(..., description="List of workflow actions")
    timeout_seconds: Optional[int] = Field(300, description="Workflow timeout in seconds")
    max_retries: Optional[int] = Field(3, description="Maximum retry attempts")
    retry_delay_seconds: Optional[int] = Field(60, description="Delay between retries")
    schedule_config: Optional[Dict[str, Any]] = Field(None, description="Schedule configuration")
    tags: Optional[List[str]] = Field(default_factory=list, description="Workflow tags")

class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    status: Optional[str] = Field(None, description="Workflow status")
    trigger_config: Optional[Dict[str, Any]] = Field(None, description="Trigger configuration")
    actions: Optional[List[Dict[str, Any]]] = Field(None, description="List of workflow actions")
    timeout_seconds: Optional[int] = Field(None, description="Workflow timeout in seconds")
    max_retries: Optional[int] = Field(None, description="Maximum retry attempts")
    retry_delay_seconds: Optional[int] = Field(None, description="Delay between retries")
    schedule_config: Optional[Dict[str, Any]] = Field(None, description="Schedule configuration")

class ExecutionTriggerRequest(BaseModel):
    trigger_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Data to trigger workflow with")

class WebhookEndpointRequest(BaseModel):
    workflow_id: str = Field(..., description="Workflow ID")
    name: Optional[str] = Field(None, description="Endpoint name")
    description: Optional[str] = Field(None, description="Endpoint description")
    secret_token: Optional[str] = Field(None, description="Secret token for verification")
    allowed_origins: Optional[List[str]] = Field(default_factory=list, description="Allowed origins")
    allowed_methods: Optional[List[str]] = Field(["POST"], description="Allowed HTTP methods")
    zapier_compatible: Optional[bool] = Field(True, description="Zapier compatibility")

class IntegrationRequest(BaseModel):
    service_name: str = Field(..., description="Service name")
    integration_name: str = Field(..., description="Integration name")
    config: Dict[str, Any] = Field(..., description="Integration configuration")
    auth_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Authentication data")

# Workflow endpoints
@router.post("/workflows", response_model=Dict[str, Any])
async def create_workflow(request: WorkflowCreateRequest, background_tasks: BackgroundTasks):
    """Create a new workflow"""
    try:
        workflow_data = {
            "name": request.name,
            "description": request.description,
            "owner_id": request.owner_id,
            "trigger_config": request.trigger_config,
            "actions": request.actions,
            "timeout_seconds": request.timeout_seconds,
            "max_retries": request.max_retries,
            "retry_delay_seconds": request.retry_delay_seconds,
            "schedule_config": request.schedule_config
        }
        
        workflow_id = await db_manager.create_workflow(workflow_data)
        
        # Create webhook endpoint if trigger is webhook
        webhook_url = None
        if request.trigger_config.get("type") == "webhook":
            webhook_manager = get_webhook_manager()
            from webhooks.webhook_manager import WebhookEndpointConfig
            
            webhook_config = WebhookEndpointConfig(
                workflow_id=workflow_id,
                name=f"Webhook for {request.name}",
                description=request.description
            )
            
            endpoint_id = await webhook_manager.create_endpoint(webhook_config)
            webhook_url = f"/webhook/{endpoint_id}"
        
        # Schedule workflow if trigger is schedule
        if request.trigger_config.get("type") == "schedule" and request.schedule_config:
            scheduler = get_scheduler()
            await scheduler.schedule_workflow(workflow_id, request.schedule_config)
        
        return {
            "workflow_id": workflow_id,
            "name": request.name,
            "status": WorkflowStatus.DRAFT.value,
            "webhook_url": webhook_url,
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows", response_model=List[Dict[str, Any]])
async def list_workflows(
    owner_id: str = Query(..., description="Owner user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum number of workflows to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """List workflows for a user"""
    try:
        workflows = await db_manager.list_user_workflows(owner_id, limit, offset)
        
        # Filter by status if provided
        if status:
            workflows = [w for w in workflows if w.get("status") == status]
        
        # Format response
        formatted_workflows = []
        for workflow in workflows:
            formatted_workflow = {
                "workflow_id": workflow["id"],
                "name": workflow["name"],
                "description": workflow.get("description"),
                "status": workflow["status"],
                "created_at": workflow["created_at"].isoformat(),
                "updated_at": workflow["updated_at"].isoformat(),
                "total_executions": workflow.get("total_executions", 0),
                "successful_executions": workflow.get("successful_executions", 0),
                "last_execution_at": workflow["last_execution_at"].isoformat() if workflow.get("last_execution_at") else None
            }
            formatted_workflows.append(formatted_workflow)
        
        return formatted_workflows
        
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow(workflow_id: str = Path(..., description="Workflow ID")):
    """Get workflow details"""
    try:
        workflow = await db_manager.get_workflow(workflow_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Parse JSON fields
        trigger_config = json.loads(workflow["trigger_config"]) if isinstance(workflow["trigger_config"], str) else workflow["trigger_config"]
        actions = json.loads(workflow["actions"]) if isinstance(workflow["actions"], str) else workflow["actions"]
        schedule_config = json.loads(workflow["schedule_config"]) if workflow.get("schedule_config") and isinstance(workflow["schedule_config"], str) else workflow.get("schedule_config")
        
        return {
            "workflow_id": workflow["id"],
            "name": workflow["name"],
            "description": workflow.get("description"),
            "owner_id": workflow["owner_id"],
            "status": workflow["status"],
            "version": workflow.get("version", 1),
            "trigger_config": trigger_config,
            "actions": actions,
            "timeout_seconds": workflow["timeout_seconds"],
            "max_retries": workflow["max_retries"],
            "retry_delay_seconds": workflow["retry_delay_seconds"],
            "schedule_config": schedule_config,
            "total_executions": workflow.get("total_executions", 0),
            "successful_executions": workflow.get("successful_executions", 0),
            "failed_executions": workflow.get("failed_executions", 0),
            "last_execution_at": workflow["last_execution_at"].isoformat() if workflow.get("last_execution_at") else None,
            "created_at": workflow["created_at"].isoformat(),
            "updated_at": workflow["updated_at"].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/workflows/{workflow_id}", response_model=Dict[str, Any])
async def update_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    request: WorkflowUpdateRequest = Body(...)
):
    """Update workflow"""
    try:
        # Get existing workflow
        workflow = await db_manager.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Build update query dynamically
        update_fields = []
        values = {"workflow_id": workflow_id}
        
        if request.name is not None:
            update_fields.append("name = :name")
            values["name"] = request.name
        
        if request.description is not None:
            update_fields.append("description = :description")
            values["description"] = request.description
        
        if request.status is not None:
            update_fields.append("status = :status")
            values["status"] = request.status
        
        if request.trigger_config is not None:
            update_fields.append("trigger_config = :trigger_config")
            values["trigger_config"] = json.dumps(request.trigger_config)
        
        if request.actions is not None:
            update_fields.append("actions = :actions")
            values["actions"] = json.dumps(request.actions)
        
        if request.timeout_seconds is not None:
            update_fields.append("timeout_seconds = :timeout_seconds")
            values["timeout_seconds"] = request.timeout_seconds
        
        if request.max_retries is not None:
            update_fields.append("max_retries = :max_retries")
            values["max_retries"] = request.max_retries
        
        if request.retry_delay_seconds is not None:
            update_fields.append("retry_delay_seconds = :retry_delay_seconds")
            values["retry_delay_seconds"] = request.retry_delay_seconds
        
        if request.schedule_config is not None:
            update_fields.append("schedule_config = :schedule_config")
            values["schedule_config"] = json.dumps(request.schedule_config)
        
        if update_fields:
            update_fields.append("updated_at = :updated_at")
            values["updated_at"] = datetime.utcnow()
            
            query = f"""
            UPDATE workflows 
            SET {', '.join(update_fields)}
            WHERE id = :workflow_id
            """
            
            await db_manager.database.execute(query, values)
        
        # Return updated workflow
        return await get_workflow(workflow_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/workflows/{workflow_id}", response_model=Dict[str, Any])
async def delete_workflow(workflow_id: str = Path(..., description="Workflow ID")):
    """Delete workflow"""
    try:
        # Get workflow to check if it exists
        workflow = await db_manager.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Soft delete - set status to archived
        query = """
        UPDATE workflows 
        SET status = :status, updated_at = :updated_at
        WHERE id = :workflow_id
        """
        
        await db_manager.database.execute(query, {
            "status": WorkflowStatus.ARCHIVED.value,
            "updated_at": datetime.utcnow(),
            "workflow_id": workflow_id
        })
        
        return {
            "workflow_id": workflow_id,
            "deleted": True,
            "deleted_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Execution endpoints
@router.post("/workflows/{workflow_id}/execute", response_model=Dict[str, Any])
async def execute_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    request: ExecutionTriggerRequest = Body(...)
):
    """Execute workflow manually"""
    try:
        engine = get_workflow_engine()
        execution_id = await engine.execute_workflow(workflow_id, request.trigger_data)
        
        return {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": ExecutionStatus.PENDING.value,
            "triggered_at": datetime.utcnow().isoformat(),
            "trigger_data": request.trigger_data
        }
        
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows/{workflow_id}/executions", response_model=List[Dict[str, Any]])
async def list_workflow_executions(
    workflow_id: str = Path(..., description="Workflow ID"),
    limit: int = Query(50, description="Maximum number of executions to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """List workflow executions"""
    try:
        query = """
        SELECT * FROM workflow_executions
        WHERE workflow_id = :workflow_id
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
        
        rows = await db_manager.database.fetch_all(query, {
            "workflow_id": workflow_id,
            "limit": limit,
            "offset": offset
        })
        
        executions = []
        for row in rows:
            execution = {
                "execution_id": row["id"],
                "workflow_id": row["workflow_id"],
                "status": row["status"],
                "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                "duration_ms": row["duration_ms"],
                "created_at": row["created_at"].isoformat(),
                "retry_count": row.get("retry_count", 0)
            }
            
            if row["error_message"]:
                execution["error_message"] = row["error_message"]
            
            executions.append(execution)
        
        return executions
        
    except Exception as e:
        logger.error(f"Error listing executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
async def get_execution_status(execution_id: str = Path(..., description="Execution ID")):
    """Get execution status and details"""
    try:
        engine = get_workflow_engine()
        status = await engine.get_execution_status(execution_id)
        
        if status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/executions/{execution_id}/cancel", response_model=Dict[str, Any])
async def cancel_execution(execution_id: str = Path(..., description="Execution ID")):
    """Cancel running execution"""
    try:
        engine = get_workflow_engine()
        success = await engine.cancel_execution(execution_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Execution not found or cannot be cancelled")
        
        return {
            "execution_id": execution_id,
            "cancelled": True,
            "cancelled_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Webhook endpoints
@router.post("/workflows/{workflow_id}/webhooks", response_model=Dict[str, Any])
async def create_webhook_endpoint(
    workflow_id: str = Path(..., description="Workflow ID"),
    request: WebhookEndpointRequest = Body(...)
):
    """Create webhook endpoint for workflow"""
    try:
        webhook_manager = get_webhook_manager()
        from webhooks.webhook_manager import WebhookEndpointConfig
        
        config = WebhookEndpointConfig(
            workflow_id=workflow_id,
            name=request.name or f"Webhook for workflow {workflow_id}",
            description=request.description
        )
        
        config.secret_token = request.secret_token
        config.allowed_origins = request.allowed_origins
        config.allowed_methods = request.allowed_methods
        config.zapier_compatible = request.zapier_compatible
        
        endpoint_id = await webhook_manager.create_endpoint(config)
        
        return {
            "endpoint_id": endpoint_id,
            "workflow_id": workflow_id,
            "webhook_url": f"/webhook/{endpoint_id}",
            "config": config.to_dict(),
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/webhooks/{endpoint_id}", response_model=Dict[str, Any])
async def get_webhook_endpoint(endpoint_id: str = Path(..., description="Endpoint ID")):
    """Get webhook endpoint information"""
    try:
        webhook_manager = get_webhook_manager()
        endpoint_info = await webhook_manager.get_endpoint_info(endpoint_id)
        
        if not endpoint_info:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        return endpoint_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/webhooks/{endpoint_id}", response_model=Dict[str, Any])
async def delete_webhook_endpoint(endpoint_id: str = Path(..., description="Endpoint ID")):
    """Delete webhook endpoint"""
    try:
        webhook_manager = get_webhook_manager()
        success = await webhook_manager.delete_endpoint(endpoint_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        return {
            "endpoint_id": endpoint_id,
            "deleted": True,
            "deleted_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Designer API endpoints
@router.get("/designer/triggers", response_model=List[Dict[str, Any]])
async def get_available_triggers():
    """Get list of available trigger types"""
    try:
        engine = get_workflow_engine()
        trigger_types = engine.trigger_registry.get_trigger_types()
        
        triggers = []
        for trigger_type in trigger_types:
            trigger_info = {
                "type": trigger_type,
                "name": trigger_type.replace("_", " ").title(),
                "description": f"{trigger_type.title()} trigger",
                "config_schema": _get_trigger_schema(trigger_type)
            }
            triggers.append(trigger_info)
        
        return triggers
        
    except Exception as e:
        logger.error(f"Error getting trigger types: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/designer/actions", response_model=List[Dict[str, Any]])
async def get_available_actions():
    """Get list of available action types"""
    try:
        engine = get_workflow_engine()
        action_types = engine.action_registry.get_action_types()
        
        actions = []
        for action_type in action_types:
            action_info = {
                "type": action_type,
                "name": action_type.replace("_", " ").title(),
                "description": f"{action_type.title()} action",
                "config_schema": _get_action_schema(action_type)
            }
            actions.append(action_info)
        
        return actions
        
    except Exception as e:
        logger.error(f"Error getting action types: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/designer/conditions", response_model=List[Dict[str, Any]])
async def get_available_conditions():
    """Get list of available condition operators"""
    try:
        from workflow.conditions import ConditionEvaluator
        
        evaluator = ConditionEvaluator()
        operators = evaluator.get_supported_operators()
        
        conditions = []
        for operator in operators:
            condition_info = {
                "operator": operator,
                "name": operator.replace("_", " ").title(),
                "description": f"{operator.title()} condition",
                "schema": _get_condition_schema(operator)
            }
            conditions.append(condition_info)
        
        return conditions
        
    except Exception as e:
        logger.error(f"Error getting condition operators: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/designer/validate-workflow", response_model=Dict[str, Any])
async def validate_workflow_design(workflow: Dict[str, Any] = Body(...)):
    """Validate workflow design"""
    try:
        errors = []
        warnings = []
        
        # Validate basic structure
        if "trigger_config" not in workflow:
            errors.append("Trigger configuration is required")
        elif not workflow["trigger_config"].get("type"):
            errors.append("Trigger type is required")
        
        if "actions" not in workflow or not workflow["actions"]:
            errors.append("At least one action is required")
        
        # Validate actions
        action_ids = set()
        for i, action in enumerate(workflow.get("actions", [])):
            action_id = action.get("id", f"action_{i}")
            
            if action_id in action_ids:
                errors.append(f"Duplicate action ID: {action_id}")
            else:
                action_ids.add(action_id)
            
            if not action.get("type"):
                errors.append(f"Action {action_id} missing type")
            
            # Check dependencies
            depends_on = action.get("depends_on", [])
            for dep in depends_on:
                if dep not in action_ids and dep not in [f"action_{j}" for j in range(i)]:
                    warnings.append(f"Action {action_id} depends on non-existent action: {dep}")
        
        # Validate conditions
        for i, action in enumerate(workflow.get("actions", [])):
            condition = action.get("condition")
            if condition:
                from workflow.conditions import ConditionEvaluator
                evaluator = ConditionEvaluator()
                validation_result = await evaluator.validate_condition(condition)
                
                if not validation_result["valid"]:
                    errors.extend([f"Action {i} condition: {err}" for err in validation_result["errors"]])
                
                warnings.extend([f"Action {i} condition: {warn}" for warn in validation_result["warnings"]])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "action_count": len(workflow.get("actions", [])),
            "has_conditions": any(action.get("condition") for action in workflow.get("actions", [])),
            "has_dependencies": any(action.get("depends_on") for action in workflow.get("actions", []))
        }
        
    except Exception as e:
        logger.error(f"Error validating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_trigger_schema(trigger_type: str) -> Dict[str, Any]:
    """Get configuration schema for trigger type"""
    schemas = {
        "webhook": {
            "type": "object",
            "properties": {
                "endpoint_id": {"type": "string", "description": "Webhook endpoint ID"},
                "secret_token": {"type": "string", "description": "Secret token for verification"},
                "allowed_methods": {"type": "array", "items": {"type": "string"}, "default": ["POST"]}
            }
        },
        "schedule": {
            "type": "object",
            "properties": {
                "cron_expression": {"type": "string", "description": "Cron expression for scheduling"},
                "timezone": {"type": "string", "default": "UTC"}
            },
            "required": ["cron_expression"]
        },
        "event": {
            "type": "object",
            "properties": {
                "event_types": {"type": "array", "items": {"type": "string"}},
                "filters": {"type": "object"}
            },
            "required": ["event_types"]
        },
        "manual": {
            "type": "object",
            "properties": {}
        }
    }
    
    return schemas.get(trigger_type, {"type": "object"})

def _get_action_schema(action_type: str) -> Dict[str, Any]:
    """Get configuration schema for action type"""
    schemas = {
        "http_request": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Request URL"},
                "method": {"type": "string", "default": "GET", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
                "headers": {"type": "object"},
                "data": {"type": "object"},
                "json": {"type": "object"},
                "timeout": {"type": "integer", "default": 30}
            },
            "required": ["url"]
        },
        "email": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email"},
                "from": {"type": "string", "description": "Sender email"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body"},
                "smtp_host": {"type": "string", "default": "localhost"},
                "smtp_port": {"type": "integer", "default": 587}
            },
            "required": ["to", "from", "subject"]
        },
        "slack": {
            "type": "object",
            "properties": {
                "webhook_url": {"type": "string", "description": "Slack webhook URL"},
                "channel": {"type": "string", "description": "Slack channel"},
                "text": {"type": "string", "description": "Message text"},
                "username": {"type": "string", "default": "Workflow Bot"}
            },
            "required": ["webhook_url", "text"]
        },
        "delay": {
            "type": "object",
            "properties": {
                "seconds": {"type": "number", "description": "Delay in seconds"}
            },
            "required": ["seconds"]
        }
    }
    
    return schemas.get(action_type, {"type": "object"})

def _get_condition_schema(operator: str) -> Dict[str, Any]:
    """Get schema for condition operator"""
    comparison_schema = {
        "type": "object",
        "properties": {
            "left": {"description": "Left value or variable"},
            "right": {"description": "Right value or variable"}
        },
        "required": ["left", "right"]
    }
    
    value_schema = {
        "type": "object",
        "properties": {
            "value": {"description": "Value to check"}
        },
        "required": ["value"]
    }
    
    logical_schema = {
        "type": "object",
        "properties": {
            "conditions": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Array of conditions"
            }
        },
        "required": ["conditions"]
    }
    
    if operator in ["equals", "not_equals", "greater_than", "less_than", "contains", "starts_with"]:
        return comparison_schema
    elif operator in ["is_empty", "is_null"]:
        return value_schema
    elif operator in ["and", "or"]:
        return logical_schema
    else:
        return {"type": "object"}