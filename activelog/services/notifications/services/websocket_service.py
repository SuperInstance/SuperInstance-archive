"""
WebSocket service for real-time in-app notifications
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect

from ..core.config import settings
from ..core.logging import logger
from ..core.database import DatabaseManager


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self):
        # Active connections: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Connection metadata: {connection_id: {user_id, tenant_id, connected_at}}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "connection_errors": 0,
            "start_time": datetime.utcnow()
        }
    
    async def connect(self, websocket: WebSocket, user_id: str, 
                     connection_id: str, tenant_id: Optional[str] = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Initialize user connections if not exists
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        # Store connection
        self.active_connections[user_id][connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.connection_metadata)
        
        logger.info("WebSocket connected", 
                   user_id=user_id,
                   connection_id=connection_id,
                   tenant_id=tenant_id,
                   total_connections=self.stats["active_connections"])
    
    def disconnect(self, user_id: str, connection_id: str):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            if connection_id in self.active_connections[user_id]:
                del self.active_connections[user_id][connection_id]
                
                # Clean up empty user entry
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        self.stats["active_connections"] = len(self.connection_metadata)
        
        logger.info("WebSocket disconnected", 
                   user_id=user_id,
                   connection_id=connection_id,
                   total_connections=self.stats["active_connections"])
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> int:
        """Send message to all connections of a specific user"""
        if user_id not in self.active_connections:
            return 0
        
        sent_count = 0
        dead_connections = []
        
        for connection_id, websocket in self.active_connections[user_id].items():
            try:
                await websocket.send_text(json.dumps(message))
                sent_count += 1
                self.stats["messages_sent"] += 1
            except Exception as e:
                logger.warning("Failed to send WebSocket message", 
                             user_id=user_id,
                             connection_id=connection_id,
                             error=str(e))
                dead_connections.append((user_id, connection_id))
                self.stats["connection_errors"] += 1
        
        # Clean up dead connections
        for user_id, connection_id in dead_connections:
            self.disconnect(user_id, connection_id)
        
        return sent_count
    
    async def send_to_tenant(self, tenant_id: str, message: Dict[str, Any]) -> int:
        """Send message to all users in a tenant"""
        sent_count = 0
        
        for connection_id, metadata in self.connection_metadata.items():
            if metadata.get("tenant_id") == tenant_id:
                user_id = metadata["user_id"]
                try:
                    websocket = self.active_connections[user_id][connection_id]
                    await websocket.send_text(json.dumps(message))
                    sent_count += 1
                    self.stats["messages_sent"] += 1
                except Exception as e:
                    logger.warning("Failed to send WebSocket message to tenant", 
                                 tenant_id=tenant_id,
                                 user_id=user_id,
                                 connection_id=connection_id,
                                 error=str(e))
                    self.disconnect(user_id, connection_id)
                    self.stats["connection_errors"] += 1
        
        return sent_count
    
    async def broadcast(self, message: Dict[str, Any]) -> int:
        """Broadcast message to all connected users"""
        sent_count = 0
        dead_connections = []
        
        for user_id, connections in self.active_connections.items():
            for connection_id, websocket in connections.items():
                try:
                    await websocket.send_text(json.dumps(message))
                    sent_count += 1
                    self.stats["messages_sent"] += 1
                except Exception as e:
                    logger.warning("Failed to broadcast WebSocket message", 
                                 user_id=user_id,
                                 connection_id=connection_id,
                                 error=str(e))
                    dead_connections.append((user_id, connection_id))
                    self.stats["connection_errors"] += 1
        
        # Clean up dead connections
        for user_id, connection_id in dead_connections:
            self.disconnect(user_id, connection_id)
        
        return sent_count
    
    def get_user_connections(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, {}))
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if user has any active connections"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    async def ping_connections(self):
        """Send ping to all connections to keep them alive"""
        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(ping_message)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        uptime = (datetime.utcnow() - self.stats["start_time"]).total_seconds()
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "users_online": len(self.active_connections),
            "connections_per_user": {
                user_id: len(connections) 
                for user_id, connections in self.active_connections.items()
            }
        }


class InAppNotificationService:
    """Service for managing in-app notifications via WebSocket"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.connection_manager = ConnectionManager()
        self._heartbeat_task = None
    
    async def start(self):
        """Start the WebSocket service"""
        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("In-app notification service started")
    
    async def stop(self):
        """Stop the WebSocket service"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        logger.info("In-app notification service stopped")
    
    async def connect_user(self, websocket: WebSocket, user_id: str, 
                          connection_id: str, tenant_id: Optional[str] = None):
        """Connect a user's WebSocket"""
        await self.connection_manager.connect(websocket, user_id, connection_id, tenant_id)
        
        # Send recent unread notifications
        await self._send_unread_notifications(user_id)
    
    def disconnect_user(self, user_id: str, connection_id: str):
        """Disconnect a user's WebSocket"""
        self.connection_manager.disconnect(user_id, connection_id)
    
    async def create_notification(self, user_id: str, title: str, message: str,
                                notification_type: str, data: Optional[Dict[str, Any]] = None,
                                tenant_id: Optional[str] = None,
                                priority: int = 2, expires_at: Optional[datetime] = None) -> str:
        """Create a new in-app notification"""
        notification_id = str(uuid.uuid4())
        
        # Store in database
        await self.db.execute_command("""
            INSERT INTO inapp_notifications (
                notification_id, user_id, tenant_id, type, title, message, 
                data, priority, expires_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, notification_id, user_id, tenant_id, notification_type, 
             title, message, json.dumps(data or {}), priority, expires_at)
        
        # Send real-time notification if user is online
        if self.connection_manager.is_user_online(user_id):
            notification_message = {
                "type": "notification",
                "id": notification_id,
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "data": data or {},
                "priority": priority,
                "timestamp": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None
            }
            
            await self.connection_manager.send_to_user(user_id, notification_message)
        
        logger.info("In-app notification created", 
                   notification_id=notification_id,
                   user_id=user_id,
                   type=notification_type,
                   online=self.connection_manager.is_user_online(user_id))
        
        return notification_id
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        result = await self.db.execute_command("""
            UPDATE inapp_notifications 
            SET is_read = TRUE, read_at = NOW() 
            WHERE notification_id = $1 AND user_id = $2
        """, notification_id, user_id)
        
        # Notify user about read status change
        if self.connection_manager.is_user_online(user_id):
            read_message = {
                "type": "notification_read",
                "notification_id": notification_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.connection_manager.send_to_user(user_id, read_message)
        
        return "UPDATE 1" in result
    
    async def get_user_notifications(self, user_id: str, limit: int = 50, 
                                   unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get user's in-app notifications"""
        query = """
            SELECT * FROM inapp_notifications 
            WHERE user_id = $1 AND (expires_at IS NULL OR expires_at > NOW())
        """
        params = [user_id]
        
        if unread_only:
            query += " AND is_read = FALSE"
        
        query += " ORDER BY created_at DESC LIMIT $2"
        params.append(limit)
        
        notifications = await self.db.execute_query(query, *params)
        
        # Parse JSON data fields
        for notification in notifications:
            if notification.get('data'):
                try:
                    notification['data'] = json.loads(notification['data'])
                except (json.JSONDecodeError, TypeError):
                    notification['data'] = {}
        
        return notifications
    
    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for user"""
        return await self.db.execute_scalar("""
            SELECT COUNT(*) FROM inapp_notifications 
            WHERE user_id = $1 AND is_read = FALSE 
                AND (expires_at IS NULL OR expires_at > NOW())
        """, user_id)
    
    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification"""
        result = await self.db.execute_command("""
            DELETE FROM inapp_notifications 
            WHERE notification_id = $1 AND user_id = $2
        """, notification_id, user_id)
        
        # Notify user about deletion
        if self.connection_manager.is_user_online(user_id):
            delete_message = {
                "type": "notification_deleted",
                "notification_id": notification_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.connection_manager.send_to_user(user_id, delete_message)
        
        return "DELETE 1" in result
    
    async def broadcast_system_notification(self, title: str, message: str,
                                          notification_type: str = "system_announcement",
                                          priority: int = 3,
                                          tenant_id: Optional[str] = None):
        """Broadcast system notification to all or tenant users"""
        system_message = {
            "type": "system_notification",
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if tenant_id:
            sent_count = await self.connection_manager.send_to_tenant(tenant_id, system_message)
        else:
            sent_count = await self.connection_manager.broadcast(system_message)
        
        logger.info("System notification broadcasted", 
                   title=title,
                   type=notification_type,
                   tenant_id=tenant_id,
                   recipients=sent_count)
    
    async def _send_unread_notifications(self, user_id: str):
        """Send unread notifications to newly connected user"""
        try:
            unread_notifications = await self.get_user_notifications(user_id, unread_only=True)
            
            if unread_notifications:
                sync_message = {
                    "type": "notifications_sync",
                    "notifications": [
                        {
                            "id": notif["notification_id"],
                            "notification_type": notif["type"],
                            "title": notif["title"],
                            "message": notif["message"],
                            "data": notif.get("data", {}),
                            "priority": notif["priority"],
                            "timestamp": notif["created_at"].isoformat(),
                            "expires_at": notif["expires_at"].isoformat() if notif.get("expires_at") else None
                        }
                        for notif in unread_notifications
                    ],
                    "unread_count": len(unread_notifications)
                }
                
                await self.connection_manager.send_to_user(user_id, sync_message)
        
        except Exception as e:
            logger.error("Failed to send unread notifications", 
                        user_id=user_id, error=str(e))
    
    async def _heartbeat_loop(self):
        """Periodic heartbeat to keep connections alive"""
        while True:
            try:
                await asyncio.sleep(settings.WEBSOCKET_HEARTBEAT_INTERVAL)
                await self.connection_manager.ping_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat error", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return self.connection_manager.get_stats()