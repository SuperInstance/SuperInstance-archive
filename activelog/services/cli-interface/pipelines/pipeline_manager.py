#!/usr/bin/env python3
"""
Pipeline Manager - Handles data pipeline creation, execution, and monitoring
Provides workflow orchestration for CLI operations and data processing
"""

import json
import uuid
import time
import os
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from pathlib import Path
import logging
import threading
from queue import Queue, Empty
from enum import Enum
import sqlite3
import yaml
import subprocess
from copy import deepcopy

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class StepType(Enum):
    COMMAND = "command"
    HTTP_REQUEST = "http_request"
    FILE_OPERATION = "file_operation"
    DATA_TRANSFORM = "data_transform"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    WEBHOOK = "webhook"
    NOTIFICATION = "notification"


@dataclass
class PipelineStep:
    """Individual pipeline step configuration"""
    id: str
    name: str
    step_type: StepType
    config: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    timeout: int = 300  # 5 minutes default
    retry_count: int = 0
    retry_delay: int = 30
    condition: Optional[str] = None  # Conditional execution
    enabled: bool = True
    
    def __post_init__(self):
        if isinstance(self.step_type, str):
            self.step_type = StepType(self.step_type)


@dataclass
class Pipeline:
    """Pipeline configuration"""
    id: str
    name: str
    description: str
    steps: List[PipelineStep]
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    status: PipelineStatus = PipelineStatus.DRAFT
    created_at: str = None
    updated_at: str = None
    created_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if isinstance(self.status, str):
            self.status = PipelineStatus(self.status)


@dataclass
class PipelineExecution:
    """Pipeline execution instance"""
    id: str
    pipeline_id: str
    status: ExecutionStatus
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, Any] = field(default_factory=dict)
    started_at: str = None
    completed_at: str = None
    error_message: Optional[str] = None
    triggered_by: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = ExecutionStatus(self.status)


@dataclass 
class StepExecution:
    """Individual step execution details"""
    step_id: str
    execution_id: str
    status: ExecutionStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    attempt: int = 1
    logs: List[str] = field(default_factory=list)


class PipelineManager:
    """Manages data pipelines for CLI operations"""
    
    def __init__(self, config):
        self.config = config
        self.pipelines = {}  # pipeline_id -> Pipeline
        self.executions = {}  # execution_id -> PipelineExecution
        self.step_executions = {}  # step_execution_id -> StepExecution
        
        # Execution queue
        self.execution_queue = Queue()
        self.running_executions = {}  # execution_id -> thread
        
        # Database for persistent storage
        self.db_path = Path("/home/activeloguser/activelog/data/cli-interface/pipelines.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Working directory for pipeline executions
        self.work_dir = Path("/home/activeloguser/activelog/data/cli-interface/pipeline_work")
        self.work_dir.mkdir(exist_ok=True)
        
        # Load existing pipelines
        self._load_pipelines()
        
        # Start execution worker
        self.running = True
        self.executor_thread = threading.Thread(target=self._execution_worker, daemon=True)
        self.executor_thread.start()
        
        logger.info("Pipeline Manager initialized")

    def create_pipeline(self, pipeline_data: Dict[str, Any]) -> str:
        """Create new data pipeline"""
        try:
            # Validate pipeline data
            self._validate_pipeline_data(pipeline_data)
            
            # Create pipeline
            pipeline_id = str(uuid.uuid4())
            
            # Parse steps
            steps = []
            for step_data in pipeline_data.get('steps', []):
                step = PipelineStep(
                    id=step_data.get('id', str(uuid.uuid4())),
                    name=step_data['name'],
                    step_type=StepType(step_data['step_type']),
                    config=step_data.get('config', {}),
                    depends_on=step_data.get('depends_on', []),
                    timeout=step_data.get('timeout', 300),
                    retry_count=step_data.get('retry_count', 0),
                    retry_delay=step_data.get('retry_delay', 30),
                    condition=step_data.get('condition'),
                    enabled=step_data.get('enabled', True)
                )
                steps.append(step)
            
            pipeline = Pipeline(
                id=pipeline_id,
                name=pipeline_data['name'],
                description=pipeline_data.get('description', ''),
                steps=steps,
                triggers=pipeline_data.get('triggers', []),
                variables=pipeline_data.get('variables', {}),
                status=PipelineStatus(pipeline_data.get('status', 'draft')),
                created_by=pipeline_data.get('created_by'),
                tags=pipeline_data.get('tags', [])
            )
            
            # Validate pipeline structure
            self._validate_pipeline_structure(pipeline)
            
            # Store pipeline
            self.pipelines[pipeline_id] = pipeline
            self._save_pipeline(pipeline)
            
            logger.info(f"Created pipeline {pipeline_id}: {pipeline.name}")
            return pipeline_id
            
        except Exception as e:
            logger.error(f"Failed to create pipeline: {e}")
            raise

    def update_pipeline(self, pipeline_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing pipeline"""
        try:
            pipeline = self.pipelines.get(pipeline_id)
            if not pipeline:
                return False
            
            # Update fields
            if 'name' in updates:
                pipeline.name = updates['name']
            if 'description' in updates:
                pipeline.description = updates['description']
            if 'status' in updates:
                pipeline.status = PipelineStatus(updates['status'])
            if 'variables' in updates:
                pipeline.variables = updates['variables']
            if 'tags' in updates:
                pipeline.tags = updates['tags']
            
            # Update steps if provided
            if 'steps' in updates:
                steps = []
                for step_data in updates['steps']:
                    step = PipelineStep(
                        id=step_data.get('id', str(uuid.uuid4())),
                        name=step_data['name'],
                        step_type=StepType(step_data['step_type']),
                        config=step_data.get('config', {}),
                        depends_on=step_data.get('depends_on', []),
                        timeout=step_data.get('timeout', 300),
                        retry_count=step_data.get('retry_count', 0),
                        retry_delay=step_data.get('retry_delay', 30),
                        condition=step_data.get('condition'),
                        enabled=step_data.get('enabled', True)
                    )
                    steps.append(step)
                pipeline.steps = steps
                
                # Re-validate structure
                self._validate_pipeline_structure(pipeline)
            
            pipeline.updated_at = datetime.utcnow().isoformat()
            
            # Save changes
            self._save_pipeline(pipeline)
            
            logger.info(f"Updated pipeline {pipeline_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update pipeline {pipeline_id}: {e}")
            return False

    def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete pipeline"""
        try:
            if pipeline_id not in self.pipelines:
                return False
            
            # Cannot delete if there are running executions
            running_executions = [
                ex for ex in self.executions.values()
                if ex.pipeline_id == pipeline_id and ex.status == ExecutionStatus.RUNNING
            ]
            
            if running_executions:
                raise ValueError("Cannot delete pipeline with running executions")
            
            # Remove pipeline
            del self.pipelines[pipeline_id]
            self._delete_pipeline(pipeline_id)
            
            logger.info(f"Deleted pipeline {pipeline_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete pipeline {pipeline_id}: {e}")
            return False

    def execute_pipeline(self, pipeline_id: str, input_data: Dict[str, Any] = None, 
                        triggered_by: str = None) -> str:
        """Execute pipeline with input data"""
        try:
            pipeline = self.pipelines.get(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")
            
            if pipeline.status != PipelineStatus.ACTIVE:
                raise ValueError(f"Pipeline {pipeline_id} is not active (status: {pipeline.status.value})")
            
            # Create execution
            execution_id = str(uuid.uuid4())
            execution = PipelineExecution(
                id=execution_id,
                pipeline_id=pipeline_id,
                status=ExecutionStatus.PENDING,
                input_data=input_data or {},
                triggered_by=triggered_by
            )
            
            # Store execution
            self.executions[execution_id] = execution
            self._save_execution(execution)
            
            # Queue for processing
            self.execution_queue.put(execution_id)
            
            logger.info(f"Queued execution {execution_id} for pipeline {pipeline_id}")
            return execution_id
            
        except Exception as e:
            logger.error(f"Failed to execute pipeline {pipeline_id}: {e}")
            raise

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get pipeline configuration"""
        try:
            pipeline = self.pipelines.get(pipeline_id)
            if not pipeline:
                return None
            
            return {
                'id': pipeline.id,
                'name': pipeline.name,
                'description': pipeline.description,
                'status': pipeline.status.value,
                'created_at': pipeline.created_at,
                'updated_at': pipeline.updated_at,
                'created_by': pipeline.created_by,
                'tags': pipeline.tags,
                'steps': [
                    {
                        'id': step.id,
                        'name': step.name,
                        'step_type': step.step_type.value,
                        'config': step.config,
                        'depends_on': step.depends_on,
                        'timeout': step.timeout,
                        'retry_count': step.retry_count,
                        'condition': step.condition,
                        'enabled': step.enabled
                    }
                    for step in pipeline.steps
                ],
                'triggers': pipeline.triggers,
                'variables': pipeline.variables
            }
            
        except Exception as e:
            logger.error(f"Failed to get pipeline {pipeline_id}: {e}")
            return None

    def list_pipelines(self, status: Optional[str] = None, 
                      created_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """List pipelines with optional filtering"""
        try:
            pipelines = []
            
            for pipeline in self.pipelines.values():
                # Apply filters
                if status and pipeline.status.value != status:
                    continue
                if created_by and pipeline.created_by != created_by:
                    continue
                
                pipeline_info = {
                    'id': pipeline.id,
                    'name': pipeline.name,
                    'description': pipeline.description,
                    'status': pipeline.status.value,
                    'created_at': pipeline.created_at,
                    'updated_at': pipeline.updated_at,
                    'created_by': pipeline.created_by,
                    'tags': pipeline.tags,
                    'step_count': len(pipeline.steps)
                }
                
                pipelines.append(pipeline_info)
            
            # Sort by updated time (newest first)
            pipelines.sort(key=lambda x: x['updated_at'], reverse=True)
            
            return pipelines
            
        except Exception as e:
            logger.error(f"Failed to list pipelines: {e}")
            return []

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status and details"""
        try:
            execution = self.executions.get(execution_id)
            if not execution:
                return None
            
            # Get step statuses
            step_statuses = []
            for step_exec_id, step_exec in self.step_executions.items():
                if step_exec.execution_id == execution_id:
                    step_statuses.append({
                        'step_id': step_exec.step_id,
                        'status': step_exec.status.value,
                        'started_at': step_exec.started_at,
                        'completed_at': step_exec.completed_at,
                        'error_message': step_exec.error_message,
                        'attempt': step_exec.attempt
                    })
            
            return {
                'execution_id': execution.id,
                'pipeline_id': execution.pipeline_id,
                'status': execution.status.value,
                'started_at': execution.started_at,
                'completed_at': execution.completed_at,
                'error_message': execution.error_message,
                'triggered_by': execution.triggered_by,
                'input_data': execution.input_data,
                'output_data': execution.output_data,
                'step_results': execution.step_results,
                'step_statuses': step_statuses
            }
            
        except Exception as e:
            logger.error(f"Failed to get execution status for {execution_id}: {e}")
            return None

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel running execution"""
        try:
            execution = self.executions.get(execution_id)
            if not execution:
                return False
            
            if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                return False
            
            # Update execution status
            execution.status = ExecutionStatus.CANCELLED
            execution.completed_at = datetime.utcnow().isoformat()
            
            # Cancel running thread if exists
            if execution_id in self.running_executions:
                # Note: Thread cancellation is complex in Python
                # For now, we just mark as cancelled and the thread will check this
                pass
            
            # Cancel all running step executions
            for step_exec in self.step_executions.values():
                if (step_exec.execution_id == execution_id and 
                    step_exec.status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]):
                    step_exec.status = ExecutionStatus.CANCELLED
                    step_exec.completed_at = datetime.utcnow().isoformat()
            
            self._save_execution(execution)
            
            logger.info(f"Cancelled execution {execution_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel execution {execution_id}: {e}")
            return False

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        try:
            total_pipelines = len(self.pipelines)
            
            status_counts = {}
            for status in PipelineStatus:
                status_counts[status.value] = 0
                
            for pipeline in self.pipelines.values():
                status_counts[pipeline.status.value] += 1
            
            # Execution statistics
            total_executions = len(self.executions)
            execution_status_counts = {}
            for status in ExecutionStatus:
                execution_status_counts[status.value] = 0
                
            for execution in self.executions.values():
                execution_status_counts[execution.status.value] += 1
            
            return {
                'total_pipelines': total_pipelines,
                'pipeline_status_distribution': status_counts,
                'total_executions': total_executions,
                'execution_status_distribution': execution_status_counts,
                'running_executions': len(self.running_executions),
                'queue_size': self.execution_queue.qsize()
            }
            
        except Exception as e:
            logger.error(f"Failed to get pipeline stats: {e}")
            return {}

    def _validate_pipeline_data(self, data: Dict[str, Any]):
        """Validate pipeline creation data"""
        required_fields = ['name', 'steps']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        if not isinstance(data['steps'], list) or not data['steps']:
            raise ValueError("Pipeline must have at least one step")
        
        # Validate each step
        for i, step_data in enumerate(data['steps']):
            if 'name' not in step_data:
                raise ValueError(f"Step {i} missing name")
            if 'step_type' not in step_data:
                raise ValueError(f"Step {i} missing step_type")
            
            try:
                StepType(step_data['step_type'])
            except ValueError:
                raise ValueError(f"Step {i} has invalid step_type: {step_data['step_type']}")

    def _validate_pipeline_structure(self, pipeline: Pipeline):
        """Validate pipeline structure and dependencies"""
        step_ids = {step.id for step in pipeline.steps}
        
        for step in pipeline.steps:
            # Check dependencies exist
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    raise ValueError(f"Step {step.id} depends on non-existent step {dep_id}")
        
        # Check for circular dependencies
        self._check_circular_dependencies(pipeline.steps)

    def _check_circular_dependencies(self, steps: List[PipelineStep]):
        """Check for circular dependencies in pipeline steps"""
        def has_cycle(step_id: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            
            step = next((s for s in steps if s.id == step_id), None)
            if step:
                for dep_id in step.depends_on:
                    if dep_id not in visited:
                        if has_cycle(dep_id, visited, rec_stack):
                            return True
                    elif dep_id in rec_stack:
                        return True
            
            rec_stack.remove(step_id)
            return False
        
        visited = set()
        for step in steps:
            if step.id not in visited:
                if has_cycle(step.id, visited, set()):
                    raise ValueError("Circular dependency detected in pipeline steps")

    def _execution_worker(self):
        """Background worker to process pipeline executions"""
        logger.info("Pipeline execution worker started")
        
        while self.running:
            try:
                # Get execution from queue
                execution_id = self.execution_queue.get(timeout=5)
                
                execution = self.executions.get(execution_id)
                if not execution:
                    continue
                
                if execution.status == ExecutionStatus.CANCELLED:
                    continue
                
                # Start execution in separate thread
                exec_thread = threading.Thread(
                    target=self._execute_pipeline,
                    args=(execution,),
                    daemon=True
                )
                exec_thread.start()
                self.running_executions[execution_id] = exec_thread
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Execution worker error: {e}")
        
        logger.info("Pipeline execution worker stopped")

    def _execute_pipeline(self, execution: PipelineExecution):
        """Execute a pipeline"""
        try:
            pipeline = self.pipelines[execution.pipeline_id]
            
            logger.info(f"Starting execution {execution.id} for pipeline {pipeline.name}")
            
            # Update execution status
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.utcnow().isoformat()
            execution.context = deepcopy(pipeline.variables)
            execution.context.update(execution.input_data)
            self._save_execution(execution)
            
            # Create execution work directory
            exec_work_dir = self.work_dir / execution.id
            exec_work_dir.mkdir(exist_ok=True)
            execution.context['WORK_DIR'] = str(exec_work_dir)
            
            try:
                # Execute steps in dependency order
                self._execute_steps(pipeline, execution)
                
                # Check if all steps completed successfully
                all_success = True
                for step_exec in self.step_executions.values():
                    if (step_exec.execution_id == execution.id and 
                        step_exec.status == ExecutionStatus.FAILED):
                        all_success = False
                        break
                
                if all_success and execution.status != ExecutionStatus.CANCELLED:
                    execution.status = ExecutionStatus.COMPLETED
                else:
                    execution.status = ExecutionStatus.FAILED
                    
            except Exception as e:
                execution.status = ExecutionStatus.FAILED
                execution.error_message = str(e)
                logger.error(f"Pipeline execution {execution.id} failed: {e}")
            
            execution.completed_at = datetime.utcnow().isoformat()
            self._save_execution(execution)
            
            logger.info(f"Completed execution {execution.id} with status {execution.status.value}")
            
        except Exception as e:
            logger.error(f"Failed to execute pipeline: {e}")
        finally:
            # Remove from running executions
            if execution.id in self.running_executions:
                del self.running_executions[execution.id]

    def _execute_steps(self, pipeline: Pipeline, execution: PipelineExecution):
        """Execute pipeline steps in dependency order"""
        # Build dependency graph
        steps_by_id = {step.id: step for step in pipeline.steps if step.enabled}
        completed_steps = set()
        failed_steps = set()
        
        while len(completed_steps) + len(failed_steps) < len(steps_by_id):
            # Check if execution was cancelled
            if execution.status == ExecutionStatus.CANCELLED:
                break
            
            # Find steps ready to execute
            ready_steps = []
            for step in steps_by_id.values():
                if step.id in completed_steps or step.id in failed_steps:
                    continue
                
                # Check if all dependencies are met
                dependencies_met = all(dep_id in completed_steps for dep_id in step.depends_on)
                
                if dependencies_met:
                    # Check condition if specified
                    if step.condition and not self._evaluate_condition(step.condition, execution.context):
                        completed_steps.add(step.id)  # Skip step
                        continue
                    
                    ready_steps.append(step)
            
            if not ready_steps:
                # No steps ready - check if we're stuck
                remaining_steps = set(steps_by_id.keys()) - completed_steps - failed_steps
                if remaining_steps:
                    raise RuntimeError(f"Pipeline stuck - cannot proceed with steps: {remaining_steps}")
                break
            
            # Execute ready steps
            for step in ready_steps:
                try:
                    success = self._execute_step(step, execution)
                    if success:
                        completed_steps.add(step.id)
                    else:
                        failed_steps.add(step.id)
                        
                        # Stop execution on first failure (could be configurable)
                        if not pipeline.variables.get('continue_on_failure', False):
                            return
                            
                except Exception as e:
                    logger.error(f"Step {step.id} execution failed: {e}")
                    failed_steps.add(step.id)
                    
                    if not pipeline.variables.get('continue_on_failure', False):
                        raise

    def _execute_step(self, step: PipelineStep, execution: PipelineExecution) -> bool:
        """Execute individual pipeline step"""
        try:
            # Create step execution record
            step_exec_id = f"{execution.id}_{step.id}"
            step_exec = StepExecution(
                step_id=step.id,
                execution_id=execution.id,
                status=ExecutionStatus.RUNNING,
                started_at=datetime.utcnow().isoformat(),
                input_data=deepcopy(execution.context)
            )
            
            self.step_executions[step_exec_id] = step_exec
            
            logger.info(f"Executing step {step.name} ({step.step_type.value})")
            
            # Execute step based on type
            if step.step_type == StepType.COMMAND:
                success, output = self._execute_command_step(step, execution, step_exec)
            elif step.step_type == StepType.HTTP_REQUEST:
                success, output = self._execute_http_step(step, execution, step_exec)
            elif step.step_type == StepType.FILE_OPERATION:
                success, output = self._execute_file_step(step, execution, step_exec)
            elif step.step_type == StepType.DATA_TRANSFORM:
                success, output = self._execute_transform_step(step, execution, step_exec)
            elif step.step_type == StepType.CONDITION:
                success, output = self._execute_condition_step(step, execution, step_exec)
            elif step.step_type == StepType.WEBHOOK:
                success, output = self._execute_webhook_step(step, execution, step_exec)
            else:
                raise ValueError(f"Unsupported step type: {step.step_type}")
            
            # Update step execution
            step_exec.status = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED
            step_exec.completed_at = datetime.utcnow().isoformat()
            step_exec.output_data = output
            
            # Update execution context with step output
            if success and output:
                execution.context[f"step_{step.id}"] = output
                execution.step_results[step.id] = output
            
            return success
            
        except Exception as e:
            step_exec.status = ExecutionStatus.FAILED
            step_exec.completed_at = datetime.utcnow().isoformat()
            step_exec.error_message = str(e)
            logger.error(f"Step {step.id} failed: {e}")
            return False

    def _execute_command_step(self, step: PipelineStep, execution: PipelineExecution, 
                            step_exec: StepExecution) -> tuple[bool, Dict[str, Any]]:
        """Execute command step"""
        try:
            config = step.config
            command = config.get('command', '')
            args = config.get('args', [])
            env = config.get('environment', {})
            
            # Substitute variables
            command = self._substitute_variables(command, execution.context)
            args = [self._substitute_variables(arg, execution.context) for arg in args]
            
            # Setup environment
            exec_env = os.environ.copy()
            exec_env.update(env)
            exec_env.update({k: str(v) for k, v in execution.context.items()})
            
            # Execute command
            full_command = [command] + args
            result = subprocess.run(
                full_command,
                cwd=execution.context.get('WORK_DIR'),
                env=exec_env,
                capture_output=True,
                text=True,
                timeout=step.timeout
            )
            
            output = {
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(full_command)
            }
            
            step_exec.logs.append(f"Command: {' '.join(full_command)}")
            step_exec.logs.append(f"Return code: {result.returncode}")
            if result.stdout:
                step_exec.logs.append(f"Stdout: {result.stdout[:1000]}")
            if result.stderr:
                step_exec.logs.append(f"Stderr: {result.stderr[:1000]}")
            
            return result.returncode == 0, output
            
        except subprocess.TimeoutExpired:
            return False, {'error': f'Command timed out after {step.timeout} seconds'}
        except Exception as e:
            return False, {'error': str(e)}

    def _execute_http_step(self, step: PipelineStep, execution: PipelineExecution,
                         step_exec: StepExecution) -> tuple[bool, Dict[str, Any]]:
        """Execute HTTP request step"""
        try:
            import requests
            
            config = step.config
            url = self._substitute_variables(config.get('url', ''), execution.context)
            method = config.get('method', 'GET').upper()
            headers = config.get('headers', {})
            data = config.get('data', {})
            params = config.get('params', {})
            
            # Substitute variables in data
            if isinstance(data, dict):
                data = {k: self._substitute_variables(str(v), execution.context) for k, v in data.items()}
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if method in ['POST', 'PUT', 'PATCH'] else None,
                params=params,
                timeout=step.timeout
            )
            
            output = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': response.text[:10000],  # Limit response size
                'url': url,
                'method': method
            }
            
            try:
                output['json'] = response.json()
            except:
                pass
            
            step_exec.logs.append(f"HTTP {method} {url}")
            step_exec.logs.append(f"Status: {response.status_code}")
            
            return response.status_code < 400, output
            
        except Exception as e:
            return False, {'error': str(e)}

    def _execute_file_step(self, step: PipelineStep, execution: PipelineExecution,
                         step_exec: StepExecution) -> tuple[bool, Dict[str, Any]]:
        """Execute file operation step"""
        try:
            config = step.config
            operation = config.get('operation', 'read')
            file_path = self._substitute_variables(config.get('path', ''), execution.context)
            
            if operation == 'read':
                with open(file_path, 'r') as f:
                    content = f.read()
                return True, {'content': content, 'path': file_path}
                
            elif operation == 'write':
                content = self._substitute_variables(config.get('content', ''), execution.context)
                with open(file_path, 'w') as f:
                    f.write(content)
                return True, {'path': file_path, 'bytes_written': len(content)}
                
            elif operation == 'copy':
                source = self._substitute_variables(config.get('source', ''), execution.context)
                dest = self._substitute_variables(config.get('destination', ''), execution.context)
                shutil.copy2(source, dest)
                return True, {'source': source, 'destination': dest}
                
            else:
                return False, {'error': f'Unsupported file operation: {operation}'}
                
        except Exception as e:
            return False, {'error': str(e)}

    def _execute_transform_step(self, step: PipelineStep, execution: PipelineExecution,
                              step_exec: StepExecution) -> tuple[bool, Dict[str, Any]]:
        """Execute data transformation step"""
        try:
            config = step.config
            transform_type = config.get('type', 'json')
            source_key = config.get('source_key', '')
            
            # Get source data
            source_data = execution.context.get(source_key, execution.context)
            
            if transform_type == 'json':
                # JSON transformation
                if isinstance(source_data, str):
                    result = json.loads(source_data)
                else:
                    result = json.dumps(source_data)
                    
            elif transform_type == 'filter':
                # Filter data
                filter_expr = config.get('filter', '')
                # Simple filtering (could be expanded)
                if isinstance(source_data, list):
                    result = [item for item in source_data if self._evaluate_condition(filter_expr, {'item': item})]
                else:
                    result = source_data
                    
            else:
                return False, {'error': f'Unsupported transform type: {transform_type}'}
            
            return True, {'result': result, 'transform_type': transform_type}
            
        except Exception as e:
            return False, {'error': str(e)}

    def _execute_condition_step(self, step: PipelineStep, execution: PipelineExecution,
                              step_exec: StepExecution) -> tuple[bool, Dict[str, Any]]:
        """Execute condition step"""
        try:
            config = step.config
            condition = config.get('condition', 'true')
            
            result = self._evaluate_condition(condition, execution.context)
            
            return True, {'condition_result': result, 'condition': condition}
            
        except Exception as e:
            return False, {'error': str(e)}

    def _execute_webhook_step(self, step: PipelineStep, execution: PipelineExecution,
                            step_exec: StepExecution) -> tuple[bool, Dict[str, Any]]:
        """Execute webhook step"""
        try:
            # This would integrate with the webhook manager
            config = step.config
            webhook_id = config.get('webhook_id', '')
            payload = config.get('payload', {})
            
            # Substitute variables in payload
            payload = {k: self._substitute_variables(str(v), execution.context) for k, v in payload.items()}
            
            # For now, just simulate webhook trigger
            return True, {'webhook_id': webhook_id, 'payload': payload}
            
        except Exception as e:
            return False, {'error': str(e)}

    def _substitute_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Substitute variables in text"""
        try:
            # Simple variable substitution using {{ variable }} syntax
            import re
            
            def replace_var(match):
                var_name = match.group(1).strip()
                return str(context.get(var_name, match.group(0)))
            
            return re.sub(r'\{\{\s*([^}]+)\s*\}\}', replace_var, text)
            
        except Exception:
            return text

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate condition expression"""
        try:
            # Simple condition evaluation - could be expanded with proper expression parser
            # For safety, only allow basic comparisons
            condition = condition.strip()
            
            if condition in ['true', 'True', '1']:
                return True
            elif condition in ['false', 'False', '0']:
                return False
            
            # Simple variable checks
            if condition.startswith('exists:'):
                var_name = condition[7:].strip()
                return var_name in context
            
            # Basic equality check
            if '==' in condition:
                left, right = condition.split('==', 1)
                left_val = context.get(left.strip(), left.strip())
                right_val = right.strip().strip('"\'')
                return str(left_val) == right_val
            
            return False
            
        except Exception:
            return False

    def _init_database(self):
        """Initialize SQLite database for persistent storage"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create pipelines table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipelines (
                    id TEXT PRIMARY KEY,
                    pipeline_data TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Create executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_executions (
                    id TEXT PRIMARY KEY,
                    execution_data TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _load_pipelines(self):
        """Load pipelines from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT pipeline_data FROM pipelines")
            rows = cursor.fetchall()
            
            for row in rows:
                pipeline_data = json.loads(row[0])
                
                # Reconstruct pipeline object
                steps = []
                for step_data in pipeline_data.get('steps', []):
                    step = PipelineStep(**step_data)
                    steps.append(step)
                
                pipeline_data['steps'] = steps
                pipeline = Pipeline(**pipeline_data)
                
                self.pipelines[pipeline.id] = pipeline
            
            conn.close()
            logger.info(f"Loaded {len(self.pipelines)} pipelines from database")
            
        except Exception as e:
            logger.error(f"Failed to load pipelines: {e}")

    def _save_pipeline(self, pipeline: Pipeline):
        """Save pipeline to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            pipeline_data = asdict(pipeline)
            
            cursor.execute("""
                INSERT OR REPLACE INTO pipelines 
                (id, pipeline_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                pipeline.id,
                json.dumps(pipeline_data),
                pipeline.created_at,
                pipeline.updated_at
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save pipeline {pipeline.id}: {e}")

    def _delete_pipeline(self, pipeline_id: str):
        """Delete pipeline from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM pipelines WHERE id = ?", (pipeline_id,))
            cursor.execute("DELETE FROM pipeline_executions WHERE id LIKE ?", (f"{pipeline_id}_%",))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to delete pipeline {pipeline_id}: {e}")

    def _save_execution(self, execution: PipelineExecution):
        """Save execution to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            execution_data = asdict(execution)
            
            cursor.execute("""
                INSERT OR REPLACE INTO pipeline_executions 
                (id, execution_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                execution.id,
                json.dumps(execution_data),
                execution.started_at or datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save execution {execution.id}: {e}")

    def shutdown(self):
        """Shutdown pipeline manager"""
        self.running = False
        
        # Cancel all running executions
        for execution_id in list(self.running_executions.keys()):
            self.cancel_execution(execution_id)
        
        # Wait for executor thread to finish
        if self.executor_thread.is_alive():
            self.executor_thread.join(timeout=10)
        
        logger.info("Pipeline Manager shut down")