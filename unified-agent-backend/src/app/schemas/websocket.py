"""
WebSocket message schemas and data models.

This module defines Pydantic models for WebSocket messages, including
message types, subscription requests, status updates, and error messages.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message types."""
    # Connection management
    WELCOME = "welcome"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"

    # Subscription management
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIPTION_CONFIRMED = "subscription_confirmed"
    UNSUBSCRIPTION_CONFIRMED = "unsubscription_confirmed"
    ROOMS_LIST = "rooms_list"

    # Execution updates
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"
    EXECUTION_PROGRESS = "execution_progress"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    EXECUTION_LOG = "execution_log"

    # Agent updates
    AGENT_STATUS_CHANGED = "agent_status_changed"
    AGENT_HEALTH_UPDATE = "agent_health_update"
    AGENT_TASK_ASSIGNED = "agent_task_assigned"
    AGENT_TASK_COMPLETED = "agent_task_completed"
    AGENT_METRICS_UPDATE = "agent_metrics_update"

    # Workflow updates
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_UPDATED = "workflow_updated"
    WORKFLOW_DELETED = "workflow_deleted"
    WORKFLOW_DEPLOYED = "workflow_deployed"
    WORKFLOW_VALIDATION_RESULT = "workflow_validation_result"

    # System notifications
    NOTIFICATION = "notification"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    MAINTENANCE_NOTICE = "maintenance_notice"

    # Data updates
    DATA_UPDATE = "data_update"
    BATCH_UPDATE = "batch_update"

    # Real-time events
    REALTIME_EVENT = "realtime_event"
    CUSTOM_EVENT = "custom_event"


class RoomType(str, Enum):
    """Room subscription types."""
    EXECUTION = "execution"
    AGENT = "agent"
    WORKFLOW = "workflow"
    USER = "user"
    GLOBAL = "global"
    SYSTEM = "system"
    CUSTOM = "custom"


class BaseWebSocketMessage(BaseModel):
    """Base WebSocket message model."""
    type: MessageType
    timestamp: Optional[float] = Field(None, description="Message timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Message data")
    room_id: Optional[str] = Field(None, description="Target room ID")
    connection_id: Optional[str] = Field(None, description="Source connection ID")


class WelcomeMessage(BaseModel):
    """Welcome message sent when client connects."""
    type: str = Field(default=MessageType.WELCOME)
    message: str = Field(..., description="Welcome message")
    user_info: Dict[str, Any] = Field(..., description="User information")
    connection_id: str = Field(..., description="Connection ID")


class ErrorMessage(BaseModel):
    """Error message model."""
    type: str = Field(default=MessageType.ERROR)
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    timestamp: float = Field(..., description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")


class PingMessage(BaseModel):
    """Ping message for connection health check."""
    type: str = Field(default=MessageType.PING)
    timestamp: float = Field(..., description="Ping timestamp")


class PongMessage(BaseModel):
    """Pong message response to ping."""
    type: str = Field(default=MessageType.PONG)
    timestamp: float = Field(..., description="Pong timestamp")
    ping_data: Optional[Dict[str, Any]] = Field(None, description="Original ping data")


# Subscription Messages
class SubscriptionRequest(BaseModel):
    """WebSocket subscription request."""
    type: str = Field(default=MessageType.SUBSCRIBE)
    room_id: str = Field(..., description="Room ID to subscribe to")
    room_type: RoomType = Field(..., description="Type of room")
    resource_id: Optional[str] = Field(None, description="Resource ID for room")
    filters: Optional[Dict[str, Any]] = Field(None, description="Subscription filters")


class UnsubscriptionRequest(BaseModel):
    """WebSocket unsubscription request."""
    type: str = Field(default=MessageType.UNSUBSCRIBE)
    room_id: str = Field(..., description="Room ID to unsubscribe from")


class SubscriptionConfirmed(BaseModel):
    """Subscription confirmation message."""
    type: str = Field(default=MessageType.SUBSCRIPTION_CONFIRMED)
    room_id: str = Field(..., description="Subscribed room ID")
    room_type: RoomType = Field(..., description="Room type")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    message: str = Field(..., description="Confirmation message")


class RoomInfo(BaseModel):
    """Room information model."""
    room_id: str = Field(..., description="Room ID")
    room_type: RoomType = Field(..., description="Room type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Room metadata")
    connection_count: int = Field(..., description="Number of connections in room")


class RoomsListMessage(BaseModel):
    """Message containing list of subscribed rooms."""
    type: str = Field(default=MessageType.ROOMS_LIST)
    rooms: List[RoomInfo] = Field(..., description="List of rooms")


# Execution Messages
class ExecutionStatus(str, Enum):
    """Execution status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class NodeStatus(str, Enum):
    """Node execution status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ExecutionStartedMessage(BaseModel):
    """Execution started notification."""
    type: str = Field(default=MessageType.EXECUTION_STARTED)
    execution_id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID")
    user_id: str = Field(..., description="User who started execution")
    started_at: datetime = Field(..., description="Start timestamp")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Execution input data")


class ExecutionCompletedMessage(BaseModel):
    """Execution completed notification."""
    type: str = Field(default=MessageType.EXECUTION_COMPLETED)
    execution_id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID")
    status: ExecutionStatus = Field(..., description="Final execution status")
    completed_at: datetime = Field(..., description="Completion timestamp")
    duration_seconds: float = Field(..., description="Execution duration")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Execution output")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Execution metrics")


class ExecutionFailedMessage(BaseModel):
    """Execution failed notification."""
    type: str = Field(default=MessageType.EXECUTION_FAILED)
    execution_id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID")
    error_message: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type")
    failed_at: datetime = Field(..., description="Failure timestamp")
    node_id: Optional[str] = Field(None, description="Node where failure occurred")
    stack_trace: Optional[str] = Field(None, description="Error stack trace")


class ExecutionProgressMessage(BaseModel):
    """Execution progress update."""
    type: str = Field(default=MessageType.EXECUTION_PROGRESS)
    execution_id: str = Field(..., description="Execution ID")
    progress_percentage: float = Field(..., description="Progress percentage (0-100)")
    current_node_id: Optional[str] = Field(None, description="Currently executing node")
    completed_nodes: int = Field(..., description="Number of completed nodes")
    total_nodes: int = Field(..., description="Total number of nodes")
    estimated_remaining_seconds: Optional[float] = Field(None, description="Estimated remaining time")


class NodeStartedMessage(BaseModel):
    """Node execution started notification."""
    type: str = Field(default=MessageType.NODE_STARTED)
    execution_id: str = Field(..., description="Execution ID")
    node_id: str = Field(..., description="Node ID")
    node_type: str = Field(..., description="Node type")
    started_at: datetime = Field(..., description="Start timestamp")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Node input data")


class NodeCompletedMessage(BaseModel):
    """Node execution completed notification."""
    type: str = Field(default=MessageType.NODE_COMPLETED)
    execution_id: str = Field(..., description="Execution ID")
    node_id: str = Field(..., description="Node ID")
    completed_at: datetime = Field(..., description="Completion timestamp")
    duration_seconds: float = Field(..., description="Node execution duration")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Node output data")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Node execution metrics")


class NodeFailedMessage(BaseModel):
    """Node execution failed notification."""
    type: str = Field(default=MessageType.NODE_FAILED)
    execution_id: str = Field(..., description="Execution ID")
    node_id: str = Field(..., description="Node ID")
    error_message: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type")
    failed_at: datetime = Field(..., description="Failure timestamp")
    stack_trace: Optional[str] = Field(None, description="Error stack trace")


# Agent Messages
class AgentStatus(str, Enum):
    """Agent status enum."""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class AgentStatusChangedMessage(BaseModel):
    """Agent status change notification."""
    type: str = Field(default=MessageType.AGENT_STATUS_CHANGED)
    agent_id: str = Field(..., description="Agent ID")
    old_status: AgentStatus = Field(..., description="Previous status")
    new_status: AgentStatus = Field(..., description="New status")
    changed_at: datetime = Field(..., description="Status change timestamp")
    reason: Optional[str] = Field(None, description="Reason for status change")


class AgentHealthUpdateMessage(BaseModel):
    """Agent health update notification."""
    type: str = Field(default=MessageType.AGENT_HEALTH_UPDATE)
    agent_id: str = Field(..., description="Agent ID")
    health_status: str = Field(..., description="Health status")
    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(None, description="Memory usage percentage")
    disk_usage: Optional[float] = Field(None, description="Disk usage percentage")
    active_tasks: int = Field(..., description="Number of active tasks")
    last_heartbeat: datetime = Field(..., description="Last heartbeat timestamp")


class AgentTaskAssignedMessage(BaseModel):
    """Agent task assignment notification."""
    type: str = Field(default=MessageType.AGENT_TASK_ASSIGNED)
    agent_id: str = Field(..., description="Agent ID")
    task_id: str = Field(..., description="Task ID")
    task_type: str = Field(..., description="Task type")
    assigned_at: datetime = Field(..., description="Assignment timestamp")
    priority: str = Field(..., description="Task priority")
    estimated_duration: Optional[float] = Field(None, description="Estimated duration in seconds")


class AgentTaskCompletedMessage(BaseModel):
    """Agent task completion notification."""
    type: str = Field(default=MessageType.AGENT_TASK_COMPLETED)
    agent_id: str = Field(..., description="Agent ID")
    task_id: str = Field(..., description="Task ID")
    completed_at: datetime = Field(..., description="Completion timestamp")
    status: str = Field(..., description="Task completion status")
    result: Dict[str, Any] = Field(default_factory=dict, description="Task result")
    duration_seconds: float = Field(..., description="Task execution duration")


# Workflow Messages
class WorkflowUpdatedMessage(BaseModel):
    """Workflow update notification."""
    type: str = Field(default=MessageType.WORKFLOW_UPDATED)
    workflow_id: str = Field(..., description="Workflow ID")
    updated_by: str = Field(..., description="User who updated workflow")
    updated_at: datetime = Field(..., description="Update timestamp")
    changes: List[str] = Field(..., description="List of changes made")
    version: str = Field(..., description="New workflow version")


class WorkflowValidationResult(BaseModel):
    """Workflow validation result notification."""
    type: str = Field(default=MessageType.WORKFLOW_VALIDATION_RESULT)
    workflow_id: str = Field(..., description="Workflow ID")
    is_valid: bool = Field(..., description="Whether workflow is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    validated_at: datetime = Field(..., description="Validation timestamp")


# System Messages
class NotificationMessage(BaseModel):
    """General notification message."""
    type: str = Field(default=MessageType.NOTIFICATION)
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    level: str = Field(..., description="Notification level (info, warning, error, success)")
    user_id: Optional[str] = Field(None, description="Target user ID")
    action_url: Optional[str] = Field(None, description="Action URL for notification")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")


class SystemAnnouncementMessage(BaseModel):
    """System announcement message."""
    type: str = Field(default=MessageType.SYSTEM_ANNOUNCEMENT)
    title: str = Field(..., description="Announcement title")
    message: str = Field(..., description="Announcement message")
    severity: str = Field(..., description="Announcement severity")
    starts_at: datetime = Field(..., description="Start timestamp")
    ends_at: Optional[datetime] = Field(None, description="End timestamp")
    affected_services: List[str] = Field(default_factory=list, description="Affected services")


# Utility Models
class WebSocketEvent(BaseModel):
    """Generic WebSocket event model."""
    event_type: str = Field(..., description="Event type")
    event_data: Dict[str, Any] = Field(..., description="Event data")
    source: str = Field(..., description="Event source")
    timestamp: datetime = Field(..., description="Event timestamp")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")


# Message factory functions
def create_execution_started_message(
    execution_id: str,
    workflow_id: str,
    user_id: str,
    input_data: Dict[str, Any]
) -> ExecutionStartedMessage:
    """Create an execution started message."""
    return ExecutionStartedMessage(
        execution_id=execution_id,
        workflow_id=workflow_id,
        user_id=user_id,
        started_at=datetime.utcnow(),
        input_data=input_data
    )


def create_execution_completed_message(
    execution_id: str,
    workflow_id: str,
    status: ExecutionStatus,
    duration_seconds: float,
    output_data: Dict[str, Any],
    metrics: Dict[str, Any]
) -> ExecutionCompletedMessage:
    """Create an execution completed message."""
    return ExecutionCompletedMessage(
        execution_id=execution_id,
        workflow_id=workflow_id,
        status=status,
        completed_at=datetime.utcnow(),
        duration_seconds=duration_seconds,
        output_data=output_data,
        metrics=metrics
    )


def create_agent_status_changed_message(
    agent_id: str,
    old_status: AgentStatus,
    new_status: AgentStatus,
    reason: Optional[str] = None
) -> AgentStatusChangedMessage:
    """Create an agent status changed message."""
    return AgentStatusChangedMessage(
        agent_id=agent_id,
        old_status=old_status,
        new_status=new_status,
        changed_at=datetime.utcnow(),
        reason=reason
    )


def create_notification_message(
    title: str,
    message: str,
    level: str = "info",
    user_id: Optional[str] = None,
    action_url: Optional[str] = None
) -> NotificationMessage:
    """Create a notification message."""
    return NotificationMessage(
        title=title,
        message=message,
        level=level,
        user_id=user_id,
        action_url=action_url
    )