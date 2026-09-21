"""
WebSocket integrations with various services.

This module provides integration utilities for connecting WebSocket functionality
with workflow executor, agent service, execution service, and other components.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.websocket.manager import WebSocketManager, websocket_manager
from app.schemas.websocket import (
    ExecutionStartedMessage, ExecutionCompletedMessage, ExecutionFailedMessage,
    ExecutionProgressMessage, NodeStartedMessage, NodeCompletedMessage, NodeFailedMessage,
    AgentStatusChangedMessage, AgentHealthUpdateMessage, AgentTaskAssignedMessage,
    AgentTaskCompletedMessage, WorkflowUpdatedMessage, WorkflowValidationResult,
    NotificationMessage, SystemAnnouncementMessage, create_execution_started_message,
    create_execution_completed_message, create_agent_status_changed_message,
    create_notification_message
)
from app.models.workflow_model import ExecutionStatus, NodeStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowExecutorWebSocketIntegration:
    """
    WebSocket integration for workflow executor.

    Provides real-time updates for workflow execution events including
    start, progress, completion, failures, and node-level updates.
    """

    def __init__(self, ws_manager: Optional[WebSocketManager] = None):
        """
        Initialize workflow executor WebSocket integration.

        Args:
            ws_manager: WebSocket manager instance (uses global if not provided)
        """
        self.ws_manager = ws_manager or websocket_manager

    async def notify_execution_started(
        self,
        execution_id: str,
        workflow_id: str,
        user_id: str,
        input_data: Dict[str, Any]
    ) -> None:
        """
        Notify about execution start.

        Args:
            execution_id: Execution ID
            workflow_id: Workflow ID
            user_id: User ID who started execution
            input_data: Execution input data
        """
        try:
            message = create_execution_started_message(
                execution_id=execution_id,
                workflow_id=workflow_id,
                user_id=user_id,
                input_data=input_data
            )

            # Send to execution room
            execution_room_id = f"execution:{execution_id}"
            await self.ws_manager.broadcast_to_room(
                execution_room_id,
                message.dict(),
                "execution_started"
            )

            # Send to workflow room
            workflow_room_id = f"workflow:{workflow_id}"
            await self.ws_manager.broadcast_to_room(
                workflow_room_id,
                message.dict(),
                "execution_started"
            )

            # Send to user room
            user_room_id = f"user:{user_id}"
            await self.ws_manager.broadcast_to_room(
                user_room_id,
                message.dict(),
                "execution_started"
            )

            logger.debug(f"Sent execution started notification for {execution_id}")

        except Exception as e:
            logger.error(f"Failed to send execution started notification: {str(e)}")

    async def notify_execution_completed(
        self,
        execution_id: str,
        workflow_id: str,
        status: ExecutionStatus,
        duration_seconds: float,
        output_data: Dict[str, Any],
        metrics: Dict[str, Any],
        user_id: str
    ) -> None:
        """
        Notify about execution completion.

        Args:
            execution_id: Execution ID
            workflow_id: Workflow ID
            status: Final execution status
            duration_seconds: Execution duration
            output_data: Execution output data
            metrics: Execution metrics
            user_id: User ID who started execution
        """
        try:
            message = create_execution_completed_message(
                execution_id=execution_id,
                workflow_id=workflow_id,
                status=ExecutionStatus(status.value) if isinstance(status, str) else status,
                duration_seconds=duration_seconds,
                output_data=output_data,
                metrics=metrics
            )

            # Send to execution room
            execution_room_id = f"execution:{execution_id}"
            await self.ws_manager.broadcast_to_room(
                execution_room_id,
                message.dict(),
                "execution_completed"
            )

            # Send to workflow room
            workflow_room_id = f"workflow:{workflow_id}"
            await self.ws_manager.broadcast_to_room(
                workflow_room_id,
                message.dict(),
                "execution_completed"
            )

            # Send to user room
            user_room_id = f"user:{user_id}"
            await self.ws_manager.broadcast_to_room(
                user_room_id,
                message.dict(),
                "execution_completed"
            )

            logger.debug(f"Sent execution completed notification for {execution_id}")

        except Exception as e:
            logger.error(f"Failed to send execution completed notification: {str(e)}")

    async def notify_execution_failed(
        self,
        execution_id: str,
        workflow_id: str,
        error_message: str,
        error_type: str,
        node_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """
        Notify about execution failure.

        Args:
            execution_id: Execution ID
            workflow_id: Workflow ID
            error_message: Error message
            error_type: Error type
            node_id: Node where failure occurred
            stack_trace: Error stack trace
            user_id: User ID who started execution
        """
        try:
            message = ExecutionFailedMessage(
                execution_id=execution_id,
                workflow_id=workflow_id,
                error_message=error_message,
                error_type=error_type,
                failed_at=datetime.utcnow(),
                node_id=node_id,
                stack_trace=stack_trace
            )

            # Send to execution room
            execution_room_id = f"execution:{execution_id}"
            await self.ws_manager.broadcast_to_room(
                execution_room_id,
                message.dict(),
                "execution_failed"
            )

            # Send to workflow room
            workflow_room_id = f"workflow:{workflow_id}"
            await self.ws_manager.broadcast_to_room(
                workflow_room_id,
                message.dict(),
                "execution_failed"
            )

            # Send to user room if available
            if user_id:
                user_room_id = f"user:{user_id}"
                await self.ws_manager.broadcast_to_room(
                    user_room_id,
                    message.dict(),
                    "execution_failed"
                )

            logger.debug(f"Sent execution failed notification for {execution_id}")

        except Exception as e:
            logger.error(f"Failed to send execution failed notification: {str(e)}")

    async def notify_execution_progress(
        self,
        execution_id: str,
        workflow_id: str,
        progress_percentage: float,
        current_node_id: Optional[str],
        completed_nodes: int,
        total_nodes: int,
        estimated_remaining_seconds: Optional[float] = None
    ) -> None:
        """
        Notify about execution progress.

        Args:
            execution_id: Execution ID
            workflow_id: Workflow ID
            progress_percentage: Progress percentage (0-100)
            current_node_id: Currently executing node ID
            completed_nodes: Number of completed nodes
            total_nodes: Total number of nodes
            estimated_remaining_seconds: Estimated remaining time
        """
        try:
            message = ExecutionProgressMessage(
                execution_id=execution_id,
                progress_percentage=progress_percentage,
                current_node_id=current_node_id,
                completed_nodes=completed_nodes,
                total_nodes=total_nodes,
                estimated_remaining_seconds=estimated_remaining_seconds
            )

            # Send to execution room
            execution_room_id = f"execution:{execution_id}"
            await self.ws_manager.broadcast_to_room(
                execution_room_id,
                message.dict(),
                "execution_progress"
            )

            # Send to workflow room
            workflow_room_id = f"workflow:{workflow_id}"
            await self.ws_manager.broadcast_to_room(
                workflow_room_id,
                message.dict(),
                "execution_progress"
            )

            logger.debug(f"Sent execution progress notification for {execution_id}: {progress_percentage}%")

        except Exception as e:
            logger.error(f"Failed to send execution progress notification: {str(e)}")

    async def notify_node_started(
        self,
        execution_id: str,
        node_id: str,
        node_type: str,
        input_data: Dict[str, Any]
    ) -> None:
        """
        Notify about node execution start.

        Args:
            execution_id: Execution ID
            node_id: Node ID
            node_type: Node type
            input_data: Node input data
        """
        try:
            message = NodeStartedMessage(
                execution_id=execution_id,
                node_id=node_id,
                node_type=node_type,
                started_at=datetime.utcnow(),
                input_data=input_data
            )

            # Send to execution room
            execution_room_id = f"execution:{execution_id}"
            await self.ws_manager.broadcast_to_room(
                execution_room_id,
                message.dict(),
                "node_started"
            )

            logger.debug(f"Sent node started notification for {node_id} in execution {execution_id}")

        except Exception as e:
            logger.error(f"Failed to send node started notification: {str(e)}")

    async def notify_node_completed(
        self,
        execution_id: str,
        node_id: str,
        duration_seconds: float,
        output_data: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> None:
        """
        Notify about node execution completion.

        Args:
            execution_id: Execution ID
            node_id: Node ID
            duration_seconds: Node execution duration
            output_data: Node output data
            metrics: Node execution metrics
        """
        try:
            message = NodeCompletedMessage(
                execution_id=execution_id,
                node_id=node_id,
                completed_at=datetime.utcnow(),
                duration_seconds=duration_seconds,
                output_data=output_data,
                metrics=metrics
            )

            # Send to execution room
            execution_room_id = f"execution:{execution_id}"
            await self.ws_manager.broadcast_to_room(
                execution_room_id,
                message.dict(),
                "node_completed"
            )

            logger.debug(f"Sent node completed notification for {node_id} in execution {execution_id}")

        except Exception as e:
            logger.error(f"Failed to send node completed notification: {str(e)}")

    async def notify_node_failed(
        self,
        execution_id: str,
        node_id: str,
        error_message: str,
        error_type: str,
        stack_trace: Optional[str] = None
    ) -> None:
        """
        Notify about node execution failure.

        Args:
            execution_id: Execution ID
            node_id: Node ID
            error_message: Error message
            error_type: Error type
            stack_trace: Error stack trace
        """
        try:
            message = NodeFailedMessage(
                execution_id=execution_id,
                node_id=node_id,
                error_message=error_message,
                error_type=error_type,
                failed_at=datetime.utcnow(),
                stack_trace=stack_trace
            )

            # Send to execution room
            execution_room_id = f"execution:{execution_id}"
            await self.ws_manager.broadcast_to_room(
                execution_room_id,
                message.dict(),
                "node_failed"
            )

            logger.debug(f"Sent node failed notification for {node_id} in execution {execution_id}")

        except Exception as e:
            logger.error(f"Failed to send node failed notification: {str(e)}")


class AgentServiceWebSocketIntegration:
    """
    WebSocket integration for agent service.

    Provides real-time updates for agent status changes, health updates,
    task assignments, and task completions.
    """

    def __init__(self, ws_manager: Optional[WebSocketManager] = None):
        """
        Initialize agent service WebSocket integration.

        Args:
            ws_manager: WebSocket manager instance (uses global if not provided)
        """
        self.ws_manager = ws_manager or websocket_manager

    async def notify_agent_status_changed(
        self,
        agent_id: str,
        old_status: str,
        new_status: str,
        reason: Optional[str] = None
    ) -> None:
        """
        Notify about agent status change.

        Args:
            agent_id: Agent ID
            old_status: Previous status
            new_status: New status
            reason: Reason for status change
        """
        try:
            message = create_agent_status_changed_message(
                agent_id=agent_id,
                old_status=old_status,
                new_status=new_status,
                reason=reason
            )

            # Send to agent room
            agent_room_id = f"agent:{agent_id}"
            await self.ws_manager.broadcast_to_room(
                agent_room_id,
                message.dict(),
                "agent_status_changed"
            )

            # Send to global agents room
            await self.ws_manager.broadcast_to_room_type(
                "agent",
                message.dict(),
                "agent_status_changed"
            )

            logger.debug(f"Sent agent status changed notification for {agent_id}")

        except Exception as e:
            logger.error(f"Failed to send agent status changed notification: {str(e)}")

    async def notify_agent_health_update(
        self,
        agent_id: str,
        health_status: str,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        disk_usage: Optional[float] = None,
        active_tasks: int = 0
    ) -> None:
        """
        Notify about agent health update.

        Args:
            agent_id: Agent ID
            health_status: Health status
            cpu_usage: CPU usage percentage
            memory_usage: Memory usage percentage
            disk_usage: Disk usage percentage
            active_tasks: Number of active tasks
        """
        try:
            message = AgentHealthUpdateMessage(
                agent_id=agent_id,
                health_status=health_status,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                active_tasks=active_tasks,
                last_heartbeat=datetime.utcnow()
            )

            # Send to agent room
            agent_room_id = f"agent:{agent_id}"
            await self.ws_manager.broadcast_to_room(
                agent_room_id,
                message.dict(),
                "agent_health_update"
            )

            logger.debug(f"Sent agent health update notification for {agent_id}")

        except Exception as e:
            logger.error(f"Failed to send agent health update notification: {str(e)}")

    async def notify_agent_task_assigned(
        self,
        agent_id: str,
        task_id: str,
        task_type: str,
        priority: str = "normal",
        estimated_duration: Optional[float] = None
    ) -> None:
        """
        Notify about agent task assignment.

        Args:
            agent_id: Agent ID
            task_id: Task ID
            task_type: Task type
            priority: Task priority
            estimated_duration: Estimated duration in seconds
        """
        try:
            message = AgentTaskAssignedMessage(
                agent_id=agent_id,
                task_id=task_id,
                task_type=task_type,
                assigned_at=datetime.utcnow(),
                priority=priority,
                estimated_duration=estimated_duration
            )

            # Send to agent room
            agent_room_id = f"agent:{agent_id}"
            await self.ws_manager.broadcast_to_room(
                agent_room_id,
                message.dict(),
                "agent_task_assigned"
            )

            logger.debug(f"Sent agent task assigned notification for {agent_id}")

        except Exception as e:
            logger.error(f"Failed to send agent task assigned notification: {str(e)}")

    async def notify_agent_task_completed(
        self,
        agent_id: str,
        task_id: str,
        status: str,
        result: Dict[str, Any],
        duration_seconds: float
    ) -> None:
        """
        Notify about agent task completion.

        Args:
            agent_id: Agent ID
            task_id: Task ID
            status: Task completion status
            result: Task result
            duration_seconds: Task execution duration
        """
        try:
            message = AgentTaskCompletedMessage(
                agent_id=agent_id,
                task_id=task_id,
                completed_at=datetime.utcnow(),
                status=status,
                result=result,
                duration_seconds=duration_seconds
            )

            # Send to agent room
            agent_room_id = f"agent:{agent_id}"
            await self.ws_manager.broadcast_to_room(
                agent_room_id,
                message.dict(),
                "agent_task_completed"
            )

            logger.debug(f"Sent agent task completed notification for {agent_id}")

        except Exception as e:
            logger.error(f"Failed to send agent task completed notification: {str(e)}")


class WorkflowServiceWebSocketIntegration:
    """
    WebSocket integration for workflow service.

    Provides real-time updates for workflow changes, validations,
    deployments, and other workflow-related events.
    """

    def __init__(self, ws_manager: Optional[WebSocketManager] = None):
        """
        Initialize workflow service WebSocket integration.

        Args:
            ws_manager: WebSocket manager instance (uses global if not provided)
        """
        self.ws_manager = ws_manager or websocket_manager

    async def notify_workflow_updated(
        self,
        workflow_id: str,
        updated_by: str,
        changes: List[str],
        version: str
    ) -> None:
        """
        Notify about workflow update.

        Args:
            workflow_id: Workflow ID
            updated_by: User who updated workflow
            changes: List of changes made
            version: New workflow version
        """
        try:
            message = WorkflowUpdatedMessage(
                workflow_id=workflow_id,
                updated_by=updated_by,
                updated_at=datetime.utcnow(),
                changes=changes,
                version=version
            )

            # Send to workflow room
            workflow_room_id = f"workflow:{workflow_id}"
            await self.ws_manager.broadcast_to_room(
                workflow_room_id,
                message.dict(),
                "workflow_updated"
            )

            # Send to user room
            user_room_id = f"user:{updated_by}"
            await self.ws_manager.broadcast_to_room(
                user_room_id,
                message.dict(),
                "workflow_updated"
            )

            logger.debug(f"Sent workflow updated notification for {workflow_id}")

        except Exception as e:
            logger.error(f"Failed to send workflow updated notification: {str(e)}")

    async def notify_workflow_validation_result(
        self,
        workflow_id: str,
        is_valid: bool,
        errors: List[str],
        warnings: List[str],
        user_id: Optional[str] = None
    ) -> None:
        """
        Notify about workflow validation result.

        Args:
            workflow_id: Workflow ID
            is_valid: Whether workflow is valid
            errors: Validation errors
            warnings: Validation warnings
            user_id: User who requested validation
        """
        try:
            message = WorkflowValidationResult(
                workflow_id=workflow_id,
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                validated_at=datetime.utcnow()
            )

            # Send to workflow room
            workflow_room_id = f"workflow:{workflow_id}"
            await self.ws_manager.broadcast_to_room(
                workflow_room_id,
                message.dict(),
                "workflow_validation_result"
            )

            # Send to user room if available
            if user_id:
                user_room_id = f"user:{user_id}"
                await self.ws_manager.broadcast_to_room(
                    user_room_id,
                    message.dict(),
                    "workflow_validation_result"
                )

            logger.debug(f"Sent workflow validation result notification for {workflow_id}")

        except Exception as e:
            logger.error(f"Failed to send workflow validation result notification: {str(e)}")


class NotificationServiceWebSocketIntegration:
    """
    WebSocket integration for notification service.

    Provides real-time delivery of user notifications and system announcements.
    """

    def __init__(self, ws_manager: Optional[WebSocketManager] = None):
        """
        Initialize notification service WebSocket integration.

        Args:
            ws_manager: WebSocket manager instance (uses global if not provided)
        """
        self.ws_manager = ws_manager or websocket_manager

    async def send_user_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        level: str = "info",
        action_url: Optional[str] = None
    ) -> None:
        """
        Send notification to a specific user.

        Args:
            user_id: User ID
            title: Notification title
            message: Notification message
            level: Notification level (info, warning, error, success)
            action_url: Optional action URL
        """
        try:
            notification = create_notification_message(
                title=title,
                message=message,
                level=level,
                user_id=user_id,
                action_url=action_url
            )

            # Send to user room
            user_room_id = f"user:{user_id}"
            await self.ws_manager.broadcast_to_room(
                user_room_id,
                notification.dict(),
                "notification"
            )

            logger.debug(f"Sent notification to user {user_id}: {title}")

        except Exception as e:
            logger.error(f"Failed to send user notification: {str(e)}")

    async def broadcast_system_announcement(
        self,
        title: str,
        message: str,
        severity: str = "info",
        affected_services: Optional[List[str]] = None
    ) -> None:
        """
        Broadcast system announcement to all users.

        Args:
            title: Announcement title
            message: Announcement message
            severity: Announcement severity
            affected_services: List of affected services
        """
        try:
            announcement = SystemAnnouncementMessage(
                type=MessageType.SYSTEM_ANNOUNCEMENT,
                title=title,
                message=message,
                severity=severity,
                starts_at=datetime.utcnow(),
                affected_services=affected_services or []
            )

            # Send to global room
            await self.ws_manager.broadcast_to_room_type(
                "global",
                announcement.dict(),
                "system_announcement"
            )

            logger.info(f"Broadcast system announcement: {title}")

        except Exception as e:
            logger.error(f"Failed to broadcast system announcement: {str(e)}")


# Global integration instances
workflow_executor_ws = WorkflowExecutorWebSocketIntegration()
agent_service_ws = AgentServiceWebSocketIntegration()
workflow_service_ws = WorkflowServiceWebSocketIntegration()
notification_service_ws = NotificationServiceWebSocketIntegration()