"""
Swarm Intelligence Platform - Python SDK
Async-first SDK for interacting with swarm intelligence systems
"""

__version__ = "1.0.0"

from .client import SwarmClient, AsyncSwarmClient
from .models import (
    Swarm, Agent, Task, Metrics,
    SwarmConfig, SwarmStatus, AgentType, TaskStatus, Priority
)
from .exceptions import (
    SwarmError, SwarmCreationError, TaskSubmissionError,
    AuthenticationError, RateLimitError
)

__all__ = [
    "SwarmClient",
    "AsyncSwarmClient",
    "Swarm",
    "Agent",
    "Task",
    "Metrics",
    "SwarmConfig",
    "SwarmStatus",
    "AgentType",
    "TaskStatus",
    "Priority",
    "SwarmError",
    "SwarmCreationError",
    "TaskSubmissionError",
    "AuthenticationError",
    "RateLimitError",
]
