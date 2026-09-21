"""
WebSocket endpoints for real-time in-app notifications
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Set, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import uuid

logger = logging.getLogger(__name__)

websocket_router = APIRouter()

class NotificationConnectionManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # user_id -> websocket
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        self.connection_users: Dict[str, str] = {}  # connection_id -> user_id
        
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "notifications_delivered": 0,
            "start_time": datetime.now()
        }
    
    async def connect(self, websocket: WebSocket, user_id: str, tenant_id: Optional[str] = None):
        """Accept new WebSocket connection for a user"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        
        # Store connection
        self.active_connections[connection_id] = websocket
        self.connection_users[connection_id] = user_id
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Update stats
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.active_connections)
        
        logger.info(f"Notification WebSocket connected for user {user_id}. Active connections: {len(self.active_connections)}")
        
        # Send welcome message
        await self.send_to_connection({
            "type": "connection_established",
            "message": "Connected to ActiveLog Notifications",
            "timestamp": datetime.now().isoformat(),
            "connection_id": connection_id
        }, connection_id)
        
        # Send pending notifications
        await self._send_pending_notifications(user_id, connection_id)
        
        return connection_id
    
    def disconnect(self, connection_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            # Get user_id before removing connection
            user_id = self.connection_users.get(connection_id)
            
            # Remove connection
            del self.active_connections[connection_id]
            del self.connection_users[connection_id]
            
            # Update user connections
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            self.stats["active_connections"] = len(self.active_connections)
            logger.info(f"Notification WebSocket disconnected for user {user_id}. Active connections: {len(self.active_connections)}")
    
    async def send_to_connection(self, message: Dict[str, Any], connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_text(json.dumps(message, default=str))
                    self.stats["messages_sent"] += 1
                except Exception as e:
                    logger.error(f"Error sending message to connection {connection_id}: {e}")
                    self.disconnect(connection_id)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """Send message to all connections for a user"""
        if user_id in self.user_connections:
            connection_ids = self.user_connections[user_id].copy()
            
            failed_connections = []
            
            for connection_id in connection_ids:
                websocket = self.active_connections.get(connection_id)
                if websocket and websocket.client_state == WebSocketState.CONNECTED:
                    try:
                        await websocket.send_text(json.dumps(message, default=str))
                        self.stats["messages_sent"] += 1
                    except Exception as e:
                        logger.error(f"Error sending message to user {user_id}, connection {connection_id}: {e}")
                        failed_connections.append(connection_id)
                else:
                    failed_connections.append(connection_id)
            
            # Remove failed connections
            for connection_id in failed_connections:
                self.disconnect(connection_id)
            
            return len(connection_ids) - len(failed_connections)
        
        return 0
    
    async def broadcast_to_tenant(self, message: Dict[str, Any], tenant_id: str):
        """Broadcast message to all users in a tenant"""
        # This would require tenant membership tracking
        # For now, we'll implement a simpler version
        pass
    
    async def _send_pending_notifications(self, user_id: str, connection_id: str):
        """Send pending notifications to newly connected user"""
        try:
            # Import here to avoid circular imports
            from main import db_manager
            
            if db_manager:
                # Get unread notifications for user
                notifications = await db_manager.execute_query("""
                    SELECT notification_id, type, title, message, data, priority, created_at
                    FROM inapp_notifications 
                    WHERE user_id = $1 AND is_read = FALSE
                    ORDER BY created_at DESC
                    LIMIT 50
                """, user_id)
                
                for notification in notifications:
                    await self.send_to_connection({
                        "type": "notification",
                        "data": {
                            "id": notification["notification_id"],
                            "type": notification["type"],
                            "title": notification["title"],
                            "message": notification["message"],
                            "data": notification["data"],
                            "priority": notification["priority"],
                            "created_at": notification["created_at"].isoformat()
                        }
                    }, connection_id)
                
                if notifications:
                    logger.debug(f"Sent {len(notifications)} pending notifications to user {user_id}")
                    
        except Exception as e:
            logger.error(f"Error sending pending notifications: {e}")
    
    def get_user_connections(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        return len(self.user_connections.get(user_id, set()))
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if user has any active connections"""
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0
    
    def get_stats(self) -> Dict:
        """Get connection manager statistics"""
        stats = self.stats.copy()
        stats["uptime_seconds"] = (datetime.now() - stats["start_time"]).total_seconds()
        stats["unique_users"] = len(self.user_connections)
        return stats

# Global connection manager
manager = NotificationConnectionManager()

@websocket_router.websocket("/ws/notifications")
async def notification_websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    tenant_id: Optional[str] = None
):
    """Main WebSocket endpoint for real-time notifications"""
    connection_id = await manager.connect(websocket, user_id, tenant_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_notification_message(message, connection_id, user_id)
            except json.JSONDecodeError:
                await manager.send_to_connection({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }, connection_id)
            
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"Notification WebSocket error: {e}")
        manager.disconnect(connection_id)

async def handle_notification_message(message: Dict[str, Any], connection_id: str, user_id: str):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping with pong
        await manager.send_to_connection({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, connection_id)
    
    elif message_type == "mark_read":
        # Mark notification as read
        notification_id = message.get("notification_id")
        if notification_id:
            await mark_notification_read(notification_id, user_id)
    
    elif message_type == "mark_all_read":
        # Mark all notifications as read for user
        await mark_all_notifications_read(user_id)
    
    elif message_type == "get_notifications":
        # Get recent notifications
        limit = message.get("limit", 20)
        await send_user_notifications(user_id, connection_id, limit)
    
    elif message_type == "delete_notification":
        # Delete notification
        notification_id = message.get("notification_id")
        if notification_id:
            await delete_notification(notification_id, user_id)
    
    else:
        await manager.send_to_connection({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "supported_types": ["ping", "mark_read", "mark_all_read", "get_notifications", "delete_notification"]
        }, connection_id)

async def mark_notification_read(notification_id: str, user_id: str):
    """Mark a notification as read"""
    try:
        from main import db_manager
        
        if db_manager:
            await db_manager.execute_command("""
                UPDATE inapp_notifications 
                SET is_read = TRUE, read_at = NOW()
                WHERE notification_id = $1 AND user_id = $2
            """, notification_id, user_id)
            
            # Send confirmation
            connections = manager.user_connections.get(user_id, set())
            for connection_id in connections:
                await manager.send_to_connection({
                    "type": "notification_read",
                    "notification_id": notification_id
                }, connection_id)
                
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")

async def mark_all_notifications_read(user_id: str):
    """Mark all notifications as read for a user"""
    try:
        from main import db_manager
        
        if db_manager:
            result = await db_manager.execute_command("""
                UPDATE inapp_notifications 
                SET is_read = TRUE, read_at = NOW()
                WHERE user_id = $1 AND is_read = FALSE
            """, user_id)
            
            # Send confirmation
            connections = manager.user_connections.get(user_id, set())
            for connection_id in connections:
                await manager.send_to_connection({
                    "type": "all_notifications_read",
                    "updated_count": result
                }, connection_id)
                
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")

async def send_user_notifications(user_id: str, connection_id: str, limit: int = 20):
    """Send user's notifications"""
    try:
        from main import db_manager
        
        if db_manager:
            notifications = await db_manager.execute_query("""
                SELECT notification_id, type, title, message, data, priority, 
                       is_read, created_at
                FROM inapp_notifications 
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, user_id, limit)
            
            await manager.send_to_connection({
                "type": "notifications_list",
                "notifications": [
                    {
                        "id": notif["notification_id"],
                        "type": notif["type"],
                        "title": notif["title"],
                        "message": notif["message"],
                        "data": notif["data"],
                        "priority": notif["priority"],
                        "is_read": notif["is_read"],
                        "created_at": notif["created_at"].isoformat()
                    }
                    for notif in notifications
                ],
                "count": len(notifications)
            }, connection_id)
            
    except Exception as e:
        logger.error(f"Error getting user notifications: {e}")

async def delete_notification(notification_id: str, user_id: str):
    """Delete a notification"""
    try:
        from main import db_manager
        
        if db_manager:
            await db_manager.execute_command("""
                DELETE FROM inapp_notifications 
                WHERE notification_id = $1 AND user_id = $2
            """, notification_id, user_id)
            
            # Send confirmation
            connections = manager.user_connections.get(user_id, set())
            for connection_id in connections:
                await manager.send_to_connection({
                    "type": "notification_deleted",
                    "notification_id": notification_id
                }, connection_id)
                
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")

# Functions to be called by other services for sending notifications

async def send_notification_to_user(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict] = None,
    priority: int = 2,
    tenant_id: Optional[str] = None,
    expires_at: Optional[datetime] = None
) -> str:
    """Send real-time notification to user"""
    try:
        from main import db_manager
        
        notification_id = str(uuid.uuid4())
        
        if db_manager:
            # Store notification in database
            await db_manager.execute_command("""
                INSERT INTO inapp_notifications (
                    notification_id, user_id, tenant_id, type, title, message,
                    data, priority, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, 
                notification_id, user_id, tenant_id, notification_type, title,
                message, json.dumps(data or {}), priority, expires_at
            )
        
        # Send to connected users
        sent_count = await manager.send_to_user({
            "type": "notification",
            "data": {
                "id": notification_id,
                "type": notification_type,
                "title": title,
                "message": message,
                "data": data or {},
                "priority": priority,
                "created_at": datetime.now().isoformat()
            }
        }, user_id)
        
        if sent_count > 0:
            manager.stats["notifications_delivered"] += 1
            logger.debug(f"Sent notification to {sent_count} connections for user {user_id}")
        
        return notification_id
        
    except Exception as e:
        logger.error(f"Error sending notification to user: {e}")
        return ""

async def send_notification_to_tenant(
    tenant_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict] = None,
    priority: int = 2,
    exclude_users: Optional[List[str]] = None
) -> List[str]:
    """Send notification to all users in a tenant"""
    try:
        from main import db_manager
        
        if not db_manager:
            return []
        
        # Get all users in tenant
        users = await db_manager.execute_query("""
            SELECT DISTINCT user_id 
            FROM notification_preferences 
            WHERE tenant_id = $1
        """, tenant_id)
        
        notification_ids = []
        exclude_users = exclude_users or []
        
        for user in users:
            user_id = user["user_id"]
            if user_id not in exclude_users:
                notification_id = await send_notification_to_user(
                    user_id=user_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    data=data,
                    priority=priority,
                    tenant_id=tenant_id
                )
                if notification_id:
                    notification_ids.append(notification_id)
        
        return notification_ids
        
    except Exception as e:
        logger.error(f"Error sending notification to tenant: {e}")
        return []

async def broadcast_system_notification(
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict] = None,
    priority: int = 3
) -> int:
    """Broadcast system notification to all connected users"""
    try:
        notification_data = {
            "type": "system_notification",
            "data": {
                "id": str(uuid.uuid4()),
                "type": notification_type,
                "title": title,
                "message": message,
                "data": data or {},
                "priority": priority,
                "created_at": datetime.now().isoformat()
            }
        }
        
        sent_count = 0
        for user_id in manager.user_connections.keys():
            user_sent = await manager.send_to_user(notification_data, user_id)
            sent_count += user_sent
        
        logger.info(f"Broadcasted system notification to {sent_count} connections")
        return sent_count
        
    except Exception as e:
        logger.error(f"Error broadcasting system notification: {e}")
        return 0

# Background task for cleanup
async def cleanup_expired_notifications():
    """Clean up expired notifications"""
    while True:
        try:
            from main import db_manager
            
            if db_manager:
                # Delete expired notifications
                await db_manager.execute_command("""
                    DELETE FROM inapp_notifications 
                    WHERE expires_at < NOW()
                """)
                
                # Delete old read notifications (older than retention period)
                retention_date = datetime.now() - timedelta(days=30)  # settings.INAPP_RETENTION_DAYS
                await db_manager.execute_command("""
                    DELETE FROM inapp_notifications 
                    WHERE is_read = TRUE AND created_at < $1
                """, retention_date)
            
            # Sleep for 1 hour
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Error in notification cleanup: {e}")
            await asyncio.sleep(3600)

# Start cleanup task when module is imported
asyncio.create_task(cleanup_expired_notifications())