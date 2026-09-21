"""
Task Automation System
Workflow automation, task scheduling, and business process management
"""

import sqlite3
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import uuid
import re
import threading
import time
from queue import Queue, PriorityQueue
import schedule


class TriggerType(Enum):
    """Automation trigger types"""
    CONTACT_CREATED = "contact_created"
    LEAD_SCORED = "lead_scored"
    OPPORTUNITY_CREATED = "opportunity_created"
    OPPORTUNITY_STAGE_CHANGED = "opportunity_stage_changed"
    CALL_COMPLETED = "call_completed"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    TASK_COMPLETED = "task_completed"
    FORM_SUBMITTED = "form_submitted"
    DATE_BASED = "date_based"
    FIELD_CHANGED = "field_changed"
    INACTIVITY = "inactivity"


class ActionType(Enum):
    """Automation action types"""
    CREATE_TASK = "create_task"
    SEND_EMAIL = "send_email"
    UPDATE_LEAD_SCORE = "update_lead_score"
    ASSIGN_TO_USER = "assign_to_user"
    ADD_TO_CAMPAIGN = "add_to_campaign"
    CREATE_OPPORTUNITY = "create_opportunity"
    SCHEDULE_CALL = "schedule_call"
    UPDATE_FIELD = "update_field"
    SEND_NOTIFICATION = "send_notification"
    WEBHOOK = "webhook"
    WAIT = "wait"


class WorkflowStatus(Enum):
    """Workflow status"""
    ACTIVE = "active"
    PAUSED = "paused"
    DRAFT = "draft"
    ARCHIVED = "archived"


class ExecutionStatus(Enum):
    """Execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class Trigger:
    """Automation trigger configuration"""
    trigger_type: TriggerType
    conditions: Dict[str, Any]
    
    
@dataclass
class Action:
    """Automation action configuration"""
    action_type: ActionType
    parameters: Dict[str, Any]
    delay_minutes: int = 0
    

@dataclass
class Workflow:
    """Automation workflow"""
    workflow_id: str
    name: str
    description: str
    trigger: Trigger
    actions: List[Action]
    status: WorkflowStatus
    created_at: datetime


class TaskAutomationSystem:
    """Task automation and workflow management system"""
    
    def __init__(self, db_path: str = "data/crm_sales.db"):
        self.db_path = db_path
        self.action_handlers = {}
        self.execution_queue = PriorityQueue()
        self.executor_thread = None
        self.is_running = False
        self._register_default_handlers()
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new automation workflow"""
        
        workflow_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert workflow
            cursor.execute("""
                INSERT INTO automation_workflows (
                    workflow_id, name, description, trigger_type,
                    trigger_conditions, actions, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                workflow_id,
                workflow_data['name'],
                workflow_data.get('description', ''),
                workflow_data['trigger']['trigger_type'],
                json.dumps(workflow_data['trigger'].get('conditions', {})),
                json.dumps([action.__dict__ for action in workflow_data['actions']]),
                WorkflowStatus.DRAFT.value,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()
            
            # Log activity
            self._log_activity('workflow_created', f"Workflow '{workflow_data['name']}' created", {
                'workflow_id': workflow_id
            })
            
            return {
                'workflow_id': workflow_id,
                'name': workflow_data['name'],
                'status': WorkflowStatus.DRAFT.value,
                'created_at': datetime.utcnow().isoformat()
            }
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow by ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM automation_workflows 
                WHERE workflow_id = ?
            """, [workflow_id])
            
            result = cursor.fetchone()
            if result:
                # Get execution statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_executions,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_executions,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_executions,
                        MAX(executed_at) as last_execution
                    FROM workflow_executions
                    WHERE workflow_id = ?
                """, [workflow_id])
                
                stats = cursor.fetchone()
                
                return {
                    'workflow_id': result['workflow_id'],
                    'name': result['name'],
                    'description': result['description'],
                    'trigger': {
                        'trigger_type': result['trigger_type'],
                        'conditions': json.loads(result['trigger_conditions']) if result['trigger_conditions'] else {}
                    },
                    'actions': json.loads(result['actions']) if result['actions'] else [],
                    'status': result['status'],
                    'created_at': result['created_at'],
                    'updated_at': result['updated_at'],
                    'stats': {
                        'total_executions': stats['total_executions'] or 0,
                        'successful_executions': stats['successful_executions'] or 0,
                        'failed_executions': stats['failed_executions'] or 0,
                        'last_execution': stats['last_execution']
                    }
                }
            return None
    
    def list_workflows(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List automation workflows"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM automation_workflows"
            params = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status)
                
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            workflows = []
            for result in results:
                # Get basic stats
                cursor.execute("""
                    SELECT 
                        COUNT(*) as executions,
                        MAX(executed_at) as last_execution
                    FROM workflow_executions
                    WHERE workflow_id = ?
                """, [result['workflow_id']])
                
                stats = cursor.fetchone()
                
                workflows.append({
                    'workflow_id': result['workflow_id'],
                    'name': result['name'],
                    'description': result['description'],
                    'trigger_type': result['trigger_type'],
                    'status': result['status'],
                    'created_at': result['created_at'],
                    'executions': stats['executions'] or 0,
                    'last_execution': stats['last_execution']
                })
                
            return workflows
    
    def activate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Activate a workflow"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE automation_workflows 
                SET status = ?, updated_at = ?
                WHERE workflow_id = ?
            """, [
                WorkflowStatus.ACTIVE.value,
                datetime.utcnow().isoformat(),
                workflow_id
            ])
            
            if cursor.rowcount == 0:
                raise ValueError("Workflow not found")
            
            conn.commit()
            
            return {
                'workflow_id': workflow_id,
                'status': WorkflowStatus.ACTIVE.value,
                'activated_at': datetime.utcnow().isoformat()
            }
    
    def pause_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Pause a workflow"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE automation_workflows 
                SET status = ?, updated_at = ?
                WHERE workflow_id = ?
            """, [
                WorkflowStatus.PAUSED.value,
                datetime.utcnow().isoformat(),
                workflow_id
            ])
            
            conn.commit()
            
            return {
                'workflow_id': workflow_id,
                'status': WorkflowStatus.PAUSED.value
            }
    
    def trigger_event(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger automation based on event"""
        
        triggered_workflows = []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Find matching active workflows
            cursor.execute("""
                SELECT * FROM automation_workflows 
                WHERE trigger_type = ? AND status = ?
            """, [event_type, WorkflowStatus.ACTIVE.value])
            
            workflows = cursor.fetchall()
            
            for workflow in workflows:
                trigger_conditions = json.loads(workflow['trigger_conditions']) if workflow['trigger_conditions'] else {}
                
                # Check if conditions match
                if self._evaluate_conditions(trigger_conditions, event_data):
                    execution_id = self._schedule_workflow_execution(
                        workflow['workflow_id'], 
                        event_data
                    )
                    
                    triggered_workflows.append({
                        'workflow_id': workflow['workflow_id'],
                        'workflow_name': workflow['name'],
                        'execution_id': execution_id
                    })
        
        return {
            'event_type': event_type,
            'triggered_workflows': len(triggered_workflows),
            'workflows': triggered_workflows
        }
    
    def create_task_automation(self, automation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create simple task automation"""
        
        # Convert to workflow format
        workflow_data = {
            'name': automation_data['name'],
            'description': automation_data.get('description', ''),
            'trigger': {
                'trigger_type': automation_data['trigger_type'],
                'conditions': automation_data.get('conditions', {})
            },
            'actions': [
                Action(
                    action_type=ActionType.CREATE_TASK,
                    parameters=automation_data['task_parameters'],
                    delay_minutes=automation_data.get('delay_minutes', 0)
                )
            ]
        }
        
        return self.create_workflow(workflow_data)
    
    def schedule_recurring_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule recurring task"""
        
        task_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create recurring task
            cursor.execute("""
                INSERT INTO recurring_tasks (
                    task_id, title, description, recurrence_pattern,
                    next_due_date, assigned_to, task_type, priority,
                    metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                task_id,
                task_data['title'],
                task_data.get('description', ''),
                task_data['recurrence_pattern'],  # daily, weekly, monthly
                task_data['start_date'],
                task_data['assigned_to'],
                task_data.get('task_type', 'general'),
                task_data.get('priority', 'medium'),
                json.dumps(task_data.get('metadata', {})),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()
            
            return {
                'task_id': task_id,
                'status': 'scheduled',
                'next_due_date': task_data['start_date']
            }
    
    def process_recurring_tasks(self) -> Dict[str, Any]:
        """Process and create due recurring tasks"""
        
        now = datetime.utcnow()
        processed_tasks = []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get due recurring tasks
            cursor.execute("""
                SELECT * FROM recurring_tasks 
                WHERE next_due_date <= ? AND status = 'active'
            """, [now.isoformat()])
            
            recurring_tasks = cursor.fetchall()
            
            for recurring_task in recurring_tasks:
                try:
                    # Create actual task
                    task_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO tasks (
                            task_id, title, description, due_date, priority,
                            assigned_to, task_type, status, metadata,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        task_id,
                        recurring_task['title'],
                        recurring_task['description'],
                        recurring_task['next_due_date'],
                        recurring_task['priority'],
                        recurring_task['assigned_to'],
                        recurring_task['task_type'],
                        'pending',
                        recurring_task['metadata'],
                        now.isoformat(),
                        now.isoformat()
                    ])
                    
                    # Calculate next due date
                    next_due = self._calculate_next_due_date(
                        recurring_task['next_due_date'],
                        recurring_task['recurrence_pattern']
                    )
                    
                    # Update recurring task
                    cursor.execute("""
                        UPDATE recurring_tasks 
                        SET next_due_date = ?, updated_at = ?
                        WHERE task_id = ?
                    """, [
                        next_due.isoformat(),
                        now.isoformat(),
                        recurring_task['task_id']
                    ])
                    
                    processed_tasks.append({
                        'recurring_task_id': recurring_task['task_id'],
                        'created_task_id': task_id,
                        'title': recurring_task['title'],
                        'next_due_date': next_due.isoformat()
                    })
                    
                except Exception as e:
                    processed_tasks.append({
                        'recurring_task_id': recurring_task['task_id'],
                        'error': str(e)
                    })
            
            conn.commit()
            
        return {
            'processed_count': len(processed_tasks),
            'tasks': processed_tasks
        }
    
    def create_lead_nurture_sequence(self, sequence_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create lead nurturing automation sequence"""
        
        sequence_id = str(uuid.uuid4())
        
        # Create workflow for lead nurturing
        actions = []
        
        for i, step in enumerate(sequence_data['steps']):
            if step['type'] == 'email':
                actions.append(Action(
                    action_type=ActionType.SEND_EMAIL,
                    parameters={
                        'template_id': step['template_id'],
                        'subject': step['subject']
                    },
                    delay_minutes=step.get('delay_days', 0) * 24 * 60
                ))
            elif step['type'] == 'task':
                actions.append(Action(
                    action_type=ActionType.CREATE_TASK,
                    parameters={
                        'title': step['title'],
                        'description': step['description'],
                        'priority': step.get('priority', 'medium')
                    },
                    delay_minutes=step.get('delay_days', 0) * 24 * 60
                ))
        
        workflow_data = {
            'name': f"Lead Nurture: {sequence_data['name']}",
            'description': sequence_data.get('description', ''),
            'trigger': {
                'trigger_type': TriggerType.LEAD_SCORED.value,
                'conditions': {
                    'score_threshold': sequence_data.get('trigger_score', 50),
                    'lead_status': sequence_data.get('trigger_status', 'new')
                }
            },
            'actions': actions
        }
        
        workflow_result = self.create_workflow(workflow_data)
        
        # Activate immediately
        self.activate_workflow(workflow_result['workflow_id'])
        
        return {
            'sequence_id': sequence_id,
            'workflow_id': workflow_result['workflow_id'],
            'name': sequence_data['name'],
            'steps_count': len(actions),
            'status': 'active'
        }
    
    def get_automation_analytics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get automation analytics"""
        
        start_date = (datetime.utcnow() - timedelta(days=period_days)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Workflow execution stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_executions,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_executions,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_executions,
                    COUNT(DISTINCT workflow_id) as active_workflows
                FROM workflow_executions
                WHERE executed_at >= ?
            """, [start_date])
            
            execution_stats = cursor.fetchone()
            
            # Most triggered workflows
            cursor.execute("""
                SELECT 
                    aw.workflow_id,
                    aw.name,
                    COUNT(we.execution_id) as execution_count
                FROM automation_workflows aw
                LEFT JOIN workflow_executions we ON aw.workflow_id = we.workflow_id
                    AND we.executed_at >= ?
                WHERE aw.status = 'active'
                GROUP BY aw.workflow_id, aw.name
                ORDER BY execution_count DESC
                LIMIT 10
            """, [start_date])
            
            top_workflows = []
            for result in cursor.fetchall():
                top_workflows.append({
                    'workflow_id': result['workflow_id'],
                    'name': result['name'],
                    'executions': result['execution_count']
                })
            
            # Daily execution volume
            cursor.execute("""
                SELECT 
                    DATE(executed_at) as date,
                    COUNT(*) as executions,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful
                FROM workflow_executions
                WHERE executed_at >= ?
                GROUP BY DATE(executed_at)
                ORDER BY date
            """, [start_date])
            
            daily_volume = []
            for result in cursor.fetchall():
                daily_volume.append({
                    'date': result['date'],
                    'executions': result['executions'],
                    'successful': result['successful']
                })
            
            # Calculate success rate
            total_executions = execution_stats['total_executions'] or 0
            successful_executions = execution_stats['successful_executions'] or 0
            success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
            
            return {
                'period_days': period_days,
                'execution_stats': {
                    'total_executions': total_executions,
                    'successful_executions': successful_executions,
                    'failed_executions': execution_stats['failed_executions'] or 0,
                    'active_workflows': execution_stats['active_workflows'] or 0,
                    'success_rate': success_rate
                },
                'top_workflows': top_workflows,
                'daily_volume': daily_volume,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def start_automation_engine(self):
        """Start the automation execution engine"""
        
        if self.is_running:
            return
            
        self.is_running = True
        self.executor_thread = threading.Thread(target=self._execution_worker)
        self.executor_thread.daemon = True
        self.executor_thread.start()
        
        # Schedule recurring task processing
        schedule.every(1).hours.do(self.process_recurring_tasks)
        
    def stop_automation_engine(self):
        """Stop the automation execution engine"""
        
        self.is_running = False
        if self.executor_thread:
            self.executor_thread.join(timeout=5)
    
    def register_action_handler(self, action_type: ActionType, handler: Callable):
        """Register custom action handler"""
        
        self.action_handlers[action_type.value] = handler
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Evaluate trigger conditions against event data"""
        
        if not conditions:
            return True
            
        for condition_key, condition_value in conditions.items():
            if condition_key not in event_data:
                return False
                
            event_value = event_data[condition_key]
            
            # Handle different condition types
            if isinstance(condition_value, dict):
                operator = condition_value.get('operator', 'equals')
                compare_value = condition_value.get('value')
                
                if operator == 'equals' and event_value != compare_value:
                    return False
                elif operator == 'greater_than' and event_value <= compare_value:
                    return False
                elif operator == 'less_than' and event_value >= compare_value:
                    return False
                elif operator == 'contains' and compare_value not in str(event_value):
                    return False
                elif operator == 'not_equals' and event_value == compare_value:
                    return False
            else:
                if event_value != condition_value:
                    return False
        
        return True
    
    def _schedule_workflow_execution(self, workflow_id: str, trigger_data: Dict[str, Any]) -> str:
        """Schedule workflow execution"""
        
        execution_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO workflow_executions (
                    execution_id, workflow_id, trigger_data, status,
                    scheduled_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, [
                execution_id,
                workflow_id,
                json.dumps(trigger_data),
                ExecutionStatus.PENDING.value,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()
        
        # Add to execution queue
        priority = 1  # Higher priority = lower number
        self.execution_queue.put((priority, execution_id))
        
        return execution_id
    
    def _execution_worker(self):
        """Background worker for executing workflows"""
        
        while self.is_running:
            try:
                # Process scheduled tasks
                schedule.run_pending()
                
                # Execute workflows from queue
                if not self.execution_queue.empty():
                    _, execution_id = self.execution_queue.get(timeout=1)
                    self._execute_workflow(execution_id)
                else:
                    time.sleep(1)
                    
            except Exception as e:
                # Log error and continue
                self._log_activity('execution_error', f"Execution error: {str(e)}", {
                    'error': str(e)
                })
                time.sleep(1)
    
    def _execute_workflow(self, execution_id: str):
        """Execute a workflow"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get execution details
            cursor.execute("""
                SELECT we.*, aw.actions, aw.name
                FROM workflow_executions we
                JOIN automation_workflows aw ON we.workflow_id = aw.workflow_id
                WHERE we.execution_id = ?
            """, [execution_id])
            
            execution = cursor.fetchone()
            if not execution:
                return
            
            try:
                # Update status to running
                cursor.execute("""
                    UPDATE workflow_executions 
                    SET status = ?, executed_at = ?
                    WHERE execution_id = ?
                """, [
                    ExecutionStatus.RUNNING.value,
                    datetime.utcnow().isoformat(),
                    execution_id
                ])
                
                conn.commit()
                
                # Execute actions
                actions = json.loads(execution['actions']) if execution['actions'] else []
                trigger_data = json.loads(execution['trigger_data']) if execution['trigger_data'] else {}
                
                for action in actions:
                    # Apply delay if specified
                    if action.get('delay_minutes', 0) > 0:
                        time.sleep(action['delay_minutes'] * 60)
                    
                    self._execute_action(action, trigger_data)
                
                # Mark as completed
                cursor.execute("""
                    UPDATE workflow_executions 
                    SET status = ?, completed_at = ?
                    WHERE execution_id = ?
                """, [
                    ExecutionStatus.COMPLETED.value,
                    datetime.utcnow().isoformat(),
                    execution_id
                ])
                
                conn.commit()
                
            except Exception as e:
                # Mark as failed
                cursor.execute("""
                    UPDATE workflow_executions 
                    SET status = ?, error_message = ?
                    WHERE execution_id = ?
                """, [
                    ExecutionStatus.FAILED.value,
                    str(e),
                    execution_id
                ])
                
                conn.commit()
                
                self._log_activity('workflow_execution_failed', f"Workflow execution failed: {str(e)}", {
                    'execution_id': execution_id,
                    'error': str(e)
                })
    
    def _execute_action(self, action: Dict[str, Any], context_data: Dict[str, Any]):
        """Execute a single action"""
        
        action_type = action['action_type']
        parameters = action.get('parameters', {})
        
        # Check for custom handler
        if action_type in self.action_handlers:
            self.action_handlers[action_type](parameters, context_data)
            return
        
        # Built-in action handlers
        if action_type == ActionType.CREATE_TASK.value:
            self._handle_create_task(parameters, context_data)
        elif action_type == ActionType.SEND_EMAIL.value:
            self._handle_send_email(parameters, context_data)
        elif action_type == ActionType.UPDATE_LEAD_SCORE.value:
            self._handle_update_lead_score(parameters, context_data)
        elif action_type == ActionType.SEND_NOTIFICATION.value:
            self._handle_send_notification(parameters, context_data)
        # Add more handlers as needed
    
    def _handle_create_task(self, parameters: Dict[str, Any], context_data: Dict[str, Any]):
        """Handle create task action"""
        
        task_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO tasks (
                    task_id, title, description, due_date, priority,
                    assigned_to, contact_id, task_type, status,
                    metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                task_id,
                parameters['title'],
                parameters.get('description', ''),
                parameters.get('due_date', (datetime.utcnow() + timedelta(days=1)).isoformat()),
                parameters.get('priority', 'medium'),
                parameters.get('assigned_to'),
                context_data.get('contact_id'),
                parameters.get('task_type', 'general'),
                'pending',
                json.dumps({'automation_created': True}),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()
    
    def _handle_send_email(self, parameters: Dict[str, Any], context_data: Dict[str, Any]):
        """Handle send email action"""
        
        # This would integrate with the email campaigns system
        # For now, just log the action
        self._log_activity('automation_email_sent', f"Email sent via automation", {
            'template_id': parameters.get('template_id'),
            'contact_id': context_data.get('contact_id'),
            'subject': parameters.get('subject')
        })
    
    def _handle_update_lead_score(self, parameters: Dict[str, Any], context_data: Dict[str, Any]):
        """Handle update lead score action"""
        
        if 'contact_id' not in context_data:
            return
            
        score_change = parameters.get('score_change', 0)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE contacts 
                SET lead_score = COALESCE(lead_score, 0) + ?,
                    updated_at = ?
                WHERE contact_id = ?
            """, [
                score_change,
                datetime.utcnow().isoformat(),
                context_data['contact_id']
            ])
            
            conn.commit()
    
    def _handle_send_notification(self, parameters: Dict[str, Any], context_data: Dict[str, Any]):
        """Handle send notification action"""
        
        # Log notification (in production, would send actual notifications)
        self._log_activity('automation_notification', parameters.get('message', ''), {
            'recipient': parameters.get('recipient'),
            'type': parameters.get('notification_type', 'info')
        })
    
    def _calculate_next_due_date(self, current_due: str, pattern: str) -> datetime:
        """Calculate next due date for recurring task"""
        
        current = datetime.fromisoformat(current_due)
        
        if pattern == 'daily':
            return current + timedelta(days=1)
        elif pattern == 'weekly':
            return current + timedelta(weeks=1)
        elif pattern == 'monthly':
            return current + timedelta(days=30)  # Simplified
        elif pattern == 'quarterly':
            return current + timedelta(days=90)
        elif pattern == 'yearly':
            return current + timedelta(days=365)
        else:
            return current + timedelta(days=1)
    
    def _register_default_handlers(self):
        """Register default action handlers"""
        
        # Default handlers are built into the _execute_action method
        # Custom handlers can be registered using register_action_handler
        pass
    
    def _log_activity(self, activity_type: str, description: str, metadata: Dict[str, Any]):
        """Log automation activity"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO activities (
                    activity_type, description, metadata, created_at
                ) VALUES (?, ?, ?, ?)
            """, [
                activity_type,
                description,
                json.dumps(metadata),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()