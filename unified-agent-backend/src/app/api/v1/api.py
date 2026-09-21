"""
Main API v1 router.

This module defines the main API router for version 1 of the API,
including all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import agents, workflows, executions, tools, health
from app.api.v1.websocket import websocket_router

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health Checks"]
)

api_router.include_router(
    agents.router,
    prefix="/agents",
    tags=["Agents"]
)

api_router.include_router(
    workflows.router,
    prefix="/workflows",
    tags=["Workflows"]
)

api_router.include_router(
    executions.router,
    prefix="/executions",
    tags=["Executions"]
)

api_router.include_router(
    tools.router,
    prefix="/tools",
    tags=["Tools"]
)

api_router.include_router(
    websocket_router,
    prefix="/websocket",
    tags=["WebSocket"]
)