"""
WebSocket endpoints for real-time updates.

This module provides WebSocket endpoints for different types of real-time updates
including general connections, execution-specific updates, agent monitoring, and workflow updates.
"""

import asyncio
from typing import Optional, Dict, Any

from fastapi import (
    APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException,
    status
)

from app.websocket.manager import WebSocketManager, websocket_manager
from app.dependencies import get_current_user_optional
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


async def get_websocket_manager() -> WebSocketManager:
    """Get WebSocket manager dependency."""
    return websocket_manager


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT authentication token"),
    api_key: Optional[str] = Query(None, description="API key for authentication"),
    manager: WebSocketManager = Depends(get_websocket_manager)
):
    """
    General WebSocket endpoint for real-time updates.

    This endpoint provides a general-purpose WebSocket connection for real-time
    communication. Clients can subscribe to various rooms and receive updates
    about workflows, executions, agents, and other system events.

    Authentication:
    - Either JWT token or API key is required
    - For development, user_id query parameter is accepted

    Usage:
    - Connect: ws://localhost:8000/api/v1/websocket/ws?token=your_jwt_token
    - Subscribe: Send {"type": "subscribe", "data": {"room_id": "room_name", "room_type": "execution"}}
    - Unsubscribe: Send {"type": "unsubscribe", "data": {"room_id": "room_name"}}
    """
    connection_info = None

    try:
        # Ensure WebSocket manager is started
        if not manager._started:
            await manager.start()

        # Handle connection
        connection_info = await manager.handle_connection(
            websocket=websocket,
            token=token,
            api_key=api_key
        )

        if not connection_info:
            return

        # Handle messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()

                # Handle the message
                await manager.handle_message(connection_info.connection_id, message)

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected normally: {connection_info.connection_id}")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {str(e)}")
                # Send error to client and continue
                await manager.send_error_to_connection(
                    connection_info.connection_id,
                    f"Error processing message: {str(e)}"
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during connection")
    except Exception as e:
        logger.error(f"WebSocket endpoint error: {str(e)}")
    finally:
        # Clean up connection
        if connection_info:
            await manager.handle_disconnect(connection_info.connection_id)


@router.websocket("/ws/executions/{execution_id}")
async def execution_websocket(
    websocket: WebSocket,
    execution_id: str,
    token: Optional[str] = Query(None, description="JWT authentication token"),
    api_key: Optional[str] = Query(None, description="API key for authentication"),
    manager: WebSocketManager = Depends(get_websocket_manager)
):
    """
    WebSocket endpoint for execution-specific updates.

    This endpoint provides real-time updates for a specific workflow execution.
    Clients are automatically subscribed to the execution room and receive updates
    about execution status, node progress, errors, and completion.

    Authentication:
    - Either JWT token or API key is required
    - User must have permission to access the execution

    Usage:
    - Connect: ws://localhost:8000/api/v1/websocket/ws/executions/{execution_id}?token=your_jwt_token
    """
    connection_info = None
    room_id = f"execution:{execution_id}"

    try:
        # Ensure WebSocket manager is started
        if not manager._started:
            await manager.start()

        # Handle connection
        connection_info = await manager.handle_connection(
            websocket=websocket,
            token=token,
            api_key=api_key,
            execution_id=execution_id
        )

        if not connection_info:
            return

        # Auto-subscribe to execution room
        subscription_success = await manager.room_manager.subscribe_connection(
            connection_info.connection_id,
            room_id,
            "execution",
            {"execution_id": execution_id}
        )

        if not subscription_success:
            await websocket.close(code=4003, reason="Failed to subscribe to execution updates")
            return

        # Send subscription confirmation
        await manager.send_message_to_connection(
            connection_info.connection_id,
            {
                "type": "execution_subscription_confirmed",
                "execution_id": execution_id,
                "room_id": room_id,
                "message": f"Subscribed to execution {execution_id} updates"
            }
        )

        # Handle messages (mainly keep-alive and status requests)
        while True:
            try:
                message = await websocket.receive_text()
                await manager.handle_message(connection_info.connection_id, message)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in execution WebSocket: {str(e)}")
                await manager.send_error_to_connection(
                    connection_info.connection_id,
                    f"Error processing message: {str(e)}"
                )

    except WebSocketDisconnect:
        logger.info(f"Execution WebSocket disconnected: {execution_id}")
    except Exception as e:
        logger.error(f"Execution WebSocket endpoint error: {str(e)}")
    finally:
        if connection_info:
            await manager.handle_disconnect(connection_info.connection_id)


@router.websocket("/ws/agents/{agent_id}")
async def agent_websocket(
    websocket: WebSocket,
    agent_id: str,
    token: Optional[str] = Query(None, description="JWT authentication token"),
    api_key: Optional[str] = Query(None, description="API key for authentication"),
    manager: WebSocketManager = Depends(get_websocket_manager)
):
    """
    WebSocket endpoint for agent monitoring and updates.

    This endpoint provides real-time updates for a specific agent, including
    health status, task updates, performance metrics, and state changes.

    Authentication:
    - Either JWT token or API key is required
    - User must have permission to monitor the agent

    Usage:
    - Connect: ws://localhost:8000/api/v1/websocket/ws/agents/{agent_id}?token=your_jwt_token
    """
    connection_info = None
    room_id = f"agent:{agent_id}"

    try:
        # Ensure WebSocket manager is started
        if not manager._started:
            await manager.start()

        # Handle connection
        connection_info = await manager.handle_connection(
            websocket=websocket,
            token=token,
            api_key=api_key,
            agent_id=agent_id
        )

        if not connection_info:
            return

        # Auto-subscribe to agent room
        subscription_success = await manager.room_manager.subscribe_connection(
            connection_info.connection_id,
            room_id,
            "agent",
            {"agent_id": agent_id}
        )

        if not subscription_success:
            await websocket.close(code=4003, reason="Failed to subscribe to agent updates")
            return

        # Send subscription confirmation
        await manager.send_message_to_connection(
            connection_info.connection_id,
            {
                "type": "agent_subscription_confirmed",
                "agent_id": agent_id,
                "room_id": room_id,
                "message": f"Subscribed to agent {agent_id} updates"
            }
        )

        # Handle messages
        while True:
            try:
                message = await websocket.receive_text()
                await manager.handle_message(connection_info.connection_id, message)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in agent WebSocket: {str(e)}")
                await manager.send_error_to_connection(
                    connection_info.connection_id,
                    f"Error processing message: {str(e)}"
                )

    except WebSocketDisconnect:
        logger.info(f"Agent WebSocket disconnected: {agent_id}")
    except Exception as e:
        logger.error(f"Agent WebSocket endpoint error: {str(e)}")
    finally:
        if connection_info:
            await manager.handle_disconnect(connection_info.connection_id)


@router.websocket("/ws/workflows/{workflow_id}")
async def workflow_websocket(
    websocket: WebSocket,
    workflow_id: str,
    token: Optional[str] = Query(None, description="JWT authentication token"),
    api_key: Optional[str] = Query(None, description="API key for authentication"),
    manager: WebSocketManager = Depends(get_websocket_manager)
):
    """
    WebSocket endpoint for workflow updates.

    This endpoint provides real-time updates for a specific workflow, including
    execution events, status changes, node updates, and workflow modifications.

    Authentication:
    - Either JWT token or API key is required
    - User must have permission to access the workflow

    Usage:
    - Connect: ws://localhost:8000/api/v1/websocket/ws/workflows/{workflow_id}?token=your_jwt_token
    """
    connection_info = None
    room_id = f"workflow:{workflow_id}"

    try:
        # Ensure WebSocket manager is started
        if not manager._started:
            await manager.start()

        # Handle connection
        connection_info = await manager.handle_connection(
            websocket=websocket,
            token=token,
            api_key=api_key,
            workflow_id=workflow_id
        )

        if not connection_info:
            return

        # Auto-subscribe to workflow room
        subscription_success = await manager.room_manager.subscribe_connection(
            connection_info.connection_id,
            room_id,
            "workflow",
            {"workflow_id": workflow_id}
        )

        if not subscription_success:
            await websocket.close(code=4003, reason="Failed to subscribe to workflow updates")
            return

        # Send subscription confirmation
        await manager.send_message_to_connection(
            connection_info.connection_id,
            {
                "type": "workflow_subscription_confirmed",
                "workflow_id": workflow_id,
                "room_id": room_id,
                "message": f"Subscribed to workflow {workflow_id} updates"
            }
        )

        # Handle messages
        while True:
            try:
                message = await websocket.receive_text()
                await manager.handle_message(connection_info.connection_id, message)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in workflow WebSocket: {str(e)}")
                await manager.send_error_to_connection(
                    connection_info.connection_id,
                    f"Error processing message: {str(e)}"
                )

    except WebSocketDisconnect:
        logger.info(f"Workflow WebSocket disconnected: {workflow_id}")
    except Exception as e:
        logger.error(f"Workflow WebSocket endpoint error: {str(e)}")
    finally:
        if connection_info:
            await manager.handle_disconnect(connection_info.connection_id)


@router.get("/stats")
async def get_websocket_stats(
    manager: WebSocketManager = Depends(get_websocket_manager)
) -> Dict[str, Any]:
    """
    Get WebSocket manager statistics.

    Returns information about active connections, room subscriptions,
    and other WebSocket-related metrics.
    """
    return manager.get_stats()


@router.post("/broadcast/{room_id}")
async def broadcast_to_room(
    room_id: str,
    message: Dict[str, Any],
    manager: WebSocketManager = Depends(get_websocket_manager)
) -> Dict[str, Any]:
    """
    Broadcast a message to all connections in a room.

    This endpoint allows external services to send messages to WebSocket clients
    subscribed to specific rooms.

    Args:
        room_id: Target room ID
        message: Message to broadcast

    Returns:
        Information about the broadcast result
    """
    try:
        sent_count = await manager.broadcast_to_room(room_id, message)
        return {
            "success": True,
            "room_id": room_id,
            "sent_count": sent_count,
            "message": "Message broadcast successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to broadcast message: {str(e)}"
        )


@router.post("/notify/user/{user_id}")
async def notify_user(
    user_id: str,
    message: Dict[str, Any],
    manager: WebSocketManager = Depends(get_websocket_manager)
) -> Dict[str, Any]:
    """
    Send a notification message to all connections for a user.

    This endpoint allows external services to send notifications to specific users
    via their WebSocket connections.

    Args:
        user_id: Target user ID
        message: Notification message

    Returns:
        Information about the notification result
    """
    try:
        sent_count = await manager.send_message_to_user(
            user_id,
            {
                **message,
                "type": "notification",
                "user_id": user_id
            }
        )
        return {
            "success": True,
            "user_id": user_id,
            "sent_count": sent_count,
            "message": "Notification sent successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )