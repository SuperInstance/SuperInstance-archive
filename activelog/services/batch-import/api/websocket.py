"""
WebSocket endpoints for real-time updates
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)

websocket_router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "start_time": datetime.now()
        }
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.active_connections)
        
        logger.info(f"WebSocket connected. Active connections: {len(self.active_connections)}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "message": "Connected to ActiveLog Batch Import Service",
            "timestamp": datetime.now().isoformat(),
            "connection_id": id(websocket)
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.stats["active_connections"] = len(self.active_connections)
            logger.info(f"WebSocket disconnected. Active connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket"""
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_text(json.dumps(message, default=str))
                self.stats["messages_sent"] += 1
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSockets"""
        if not self.active_connections:
            return
        
        # Create list of connections to avoid modification during iteration
        connections_to_remove = []
        
        for connection in self.active_connections.copy():
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(json.dumps(message, default=str))
                    self.stats["messages_sent"] += 1
                else:
                    connections_to_remove.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                connections_to_remove.append(connection)
        
        # Remove failed connections
        for connection in connections_to_remove:
            self.disconnect(connection)
    
    def get_stats(self) -> dict:
        """Get connection manager statistics"""
        stats = self.stats.copy()
        stats["uptime_seconds"] = (datetime.now() - stats["start_time"]).total_seconds()
        return stats

# Global connection manager
manager = ConnectionManager()

@websocket_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_websocket_message(message, websocket)
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

async def handle_websocket_message(message: dict, websocket: WebSocket):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping with pong
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, websocket)
    
    elif message_type == "subscribe":
        # Handle subscription requests
        subscription_type = message.get("subscription")
        
        if subscription_type == "batch_updates":
            await manager.send_personal_message({
                "type": "subscription_confirmed",
                "subscription": "batch_updates",
                "message": "Subscribed to batch processing updates",
                "timestamp": datetime.now().isoformat()
            }, websocket)
        
        elif subscription_type == "file_events":
            await manager.send_personal_message({
                "type": "subscription_confirmed",
                "subscription": "file_events",
                "message": "Subscribed to file monitoring events",
                "timestamp": datetime.now().isoformat()
            }, websocket)
        
        else:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Unknown subscription type: {subscription_type}",
                "timestamp": datetime.now().isoformat()
            }, websocket)
    
    elif message_type == "get_status":
        # Send current status
        await send_status_update(websocket)
    
    else:
        await manager.send_personal_message({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.now().isoformat()
        }, websocket)

async def send_status_update(websocket: WebSocket = None):
    """Send current status update"""
    try:
        # Import here to avoid circular imports
        from main import import_monitor, batch_processor, report_service
        
        status_data = {
            "type": "status_update",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "service_running": True,
                "monitor_stats": import_monitor.get_stats() if import_monitor else {},
                "processor_stats": batch_processor.get_stats() if batch_processor else {},
                "report_stats": report_service.get_stats() if report_service else {},
                "websocket_stats": manager.get_stats()
            }
        }
        
        if websocket:
            await manager.send_personal_message(status_data, websocket)
        else:
            await manager.broadcast(status_data)
            
    except Exception as e:
        logger.error(f"Error sending status update: {e}")

# Functions to be called by other services for real-time updates

async def notify_file_detected(file_path: str, event_type: str):
    """Notify about new file detection"""
    await manager.broadcast({
        "type": "file_detected",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "file_path": file_path,
            "event_type": event_type
        }
    })

async def notify_batch_started(batch_id: str, file_count: int):
    """Notify about batch processing start"""
    await manager.broadcast({
        "type": "batch_started",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "batch_id": batch_id,
            "file_count": file_count
        }
    })

async def notify_batch_completed(batch_id: str, result_summary: dict):
    """Notify about batch processing completion"""
    await manager.broadcast({
        "type": "batch_completed",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "batch_id": batch_id,
            "summary": result_summary
        }
    })

async def notify_file_processed(file_path: str, success: bool, error: str = None):
    """Notify about individual file processing"""
    await manager.broadcast({
        "type": "file_processed",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "file_path": file_path,
            "success": success,
            "error": error
        }
    })

async def notify_error(error_message: str, context: dict = None):
    """Notify about errors"""
    await manager.broadcast({
        "type": "error",
        "timestamp": datetime.now().isoformat(),
        "message": error_message,
        "context": context or {}
    })

async def notify_stats_update():
    """Send periodic stats update"""
    await send_status_update()

# Background task for periodic updates
async def periodic_stats_broadcast():
    """Periodically broadcast stats to connected clients"""
    while True:
        try:
            if manager.active_connections:
                await notify_stats_update()
            await asyncio.sleep(30)  # Send stats every 30 seconds
        except Exception as e:
            logger.error(f"Error in periodic stats broadcast: {e}")
            await asyncio.sleep(60)  # Wait longer on error

# Start periodic task when module is imported
asyncio.create_task(periodic_stats_broadcast())