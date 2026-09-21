"""
WebSocket API endpoints for real-time updates.

This package provides WebSocket endpoints for real-time communication including
general connections, execution-specific updates, agent monitoring, and workflow updates.
"""

from .endpoints import router as websocket_router

__all__ = ["websocket_router"]