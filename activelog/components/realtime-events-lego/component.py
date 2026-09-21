# SUPERINSTANCE LEGO COMPONENT: Real-time Events
# EXTRACTED FROM: services/realtime-events/realtime_events_main.py
# LEGO PRINCIPLE: Software = Data + Tools + Configuration

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional, Set, Callable
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque
import uuid
from contextlib import asynccontextmanager

class RealtimeEventsLego:
    """
    🧩 LEGO COMPONENT: Real-time Events System
    
    DATA: WebSocket connections, event streams, activity feeds, notification queues, message history
    TOOLS: WebSocket management, event broadcasting, activity tracking, notification delivery
    CONFIGURATION: Connection limits, event types, notification channels, persistence settings
    
    INTERFACES:
    - Input: WebSocket connections, event subscriptions, broadcast messages, notifications
    - Output: Real-time events, activity streams, collaborative updates, push notifications
    - Integration: Chat systems, collaborative editors, live dashboards, gaming platforms
    
    DEPLOYMENT OPTIONS:
    - Device: Local real-time events for personal applications
    - Edge: Regional event hubs with intelligent routing
    - Cloud: Global real-time infrastructure with massive scale
    
    SUPERINSTANCE MISSION:
    Revolutionary $2/month real-time infrastructure that makes any live collaboration
    possible through perfect Lego interfaces and intelligent event orchestration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.deployment_mode = config.get("deployment_mode", "edge")
        self.max_connections = config.get("max_connections", 10000)
        self.message_history_limit = config.get("message_history_limit", 1000)
        
        # Connection management
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict] = {}
        self.subscription_registry: Dict[str, Set[str]] = defaultdict(set)  # event_type -> connection_ids
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)  # user_id -> connection_ids
        
        # Event management
        self.event_handlers: Dict[str, Callable] = {}
        self.event_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.message_history_limit))
        self.activity_feed: deque = deque(maxlen=5000)  # Global activity feed
        
        # Notification system
        self.notification_queue: Dict[str, List] = defaultdict(list)
        self.notification_handlers: Dict[str, Callable] = {}
        
        # Performance tracking
        self.start_time = time.time()
        self.message_count = 0
        self.connection_stats = {
            "total_connections": 0,
            "current_connections": 0,
            "peak_connections": 0,
            "messages_sent": 0,
            "messages_received": 0
        }
        
        # FastAPI app
        self.app = FastAPI(
            title="SuperInstance Real-time Events Lego",
            description="Revolutionary $2/month real-time infrastructure for infinite live possibilities",
            version="1.0.0"
        )
        self._setup_routes()
        
        # Background tasks
        self.cleanup_task = None
        self.stats_task = None
        
    def _setup_routes(self):
        """Setup SuperInstance real-time event routes"""
        
        @self.app.get("/health")
        async def events_health():
            """Real-time events health check - core LEGO function"""
            uptime = time.time() - self.start_time
            return {
                "service": "superinstance-realtime-events",
                "status": "healthy",
                "deployment_mode": self.deployment_mode,
                "active_connections": len(self.active_connections),
                "max_connections": self.max_connections,
                "total_events": sum(len(history) for history in self.event_history.values()),
                "uptime_seconds": uptime,
                "connection_stats": self.connection_stats,
                "mission": "$2/month real-time infrastructure for infinite live possibilities",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            """Main WebSocket endpoint - core LEGO function"""
            await self.connect_client(websocket, client_id)
            try:
                while True:
                    # Receive message from client
                    data = await websocket.receive_text()
                    await self.handle_message(client_id, data)
            except WebSocketDisconnect:
                await self.disconnect_client(client_id)
        
        @self.app.post("/broadcast")
        async def broadcast_message(broadcast_request: dict):
            """Broadcast message to subscribers - core LEGO function"""
            try:
                event_type = broadcast_request.get("event_type", "general")
                message = broadcast_request.get("message")
                target_users = broadcast_request.get("target_users", [])  # Optional user targeting
                
                if not message:
                    raise HTTPException(400, "Message required")
                
                # Create event object
                event = {
                    "id": str(uuid.uuid4()),
                    "type": event_type,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "api_broadcast"
                }
                
                # Broadcast to subscribers
                recipient_count = await self._broadcast_event(event, target_users)
                
                # Record in activity feed
                self.activity_feed.append({
                    "event_id": event["id"],
                    "type": "broadcast",
                    "event_type": event_type,
                    "recipients": recipient_count,
                    "timestamp": event["timestamp"]
                })
                
                return {
                    "status": "broadcasted",
                    "event_id": event["id"],
                    "recipients": recipient_count,
                    "deployment_mode": self.deployment_mode
                }
                
            except Exception as e:
                raise HTTPException(500, f"Broadcast failed: {str(e)}")
        
        @self.app.post("/subscribe")
        async def subscribe_to_events(subscription_request: dict):
            """Subscribe connection to event types - subscription LEGO function"""
            try:
                client_id = subscription_request.get("client_id")
                event_types = subscription_request.get("event_types", [])
                user_id = subscription_request.get("user_id")
                
                if not client_id or not event_types:
                    raise HTTPException(400, "Client ID and event types required")
                
                # Update subscriptions
                for event_type in event_types:
                    self.subscription_registry[event_type].add(client_id)
                
                # Update user mapping
                if user_id:
                    self.user_connections[user_id].add(client_id)
                
                # Update connection metadata
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id]["subscriptions"] = event_types
                    self.connection_metadata[client_id]["user_id"] = user_id
                
                return {
                    "status": "subscribed",
                    "client_id": client_id,
                    "event_types": event_types,
                    "active_subscriptions": len(self.subscription_registry)
                }
                
            except Exception as e:
                raise HTTPException(500, f"Subscription failed: {str(e)}")
        
        @self.app.get("/activity-feed")
        async def get_activity_feed(limit: int = 50):
            """Get activity feed - monitoring LEGO function"""
            activities = list(self.activity_feed)[-limit:]
            activities.reverse()  # Most recent first
            
            return {
                "activities": activities,
                "total_activities": len(self.activity_feed),
                "limit": limit,
                "deployment_mode": self.deployment_mode
            }
        
        @self.app.get("/connections")
        async def get_connection_info():
            """Get connection information - monitoring LEGO function"""
            return {
                "total_connections": len(self.active_connections),
                "connection_details": [
                    {
                        "client_id": client_id,
                        "connected_at": metadata.get("connected_at"),
                        "user_id": metadata.get("user_id"),
                        "subscriptions": metadata.get("subscriptions", []),
                        "message_count": metadata.get("message_count", 0)
                    }
                    for client_id, metadata in self.connection_metadata.items()
                ],
                "subscription_registry": {
                    event_type: len(subscribers)
                    for event_type, subscribers in self.subscription_registry.items()
                },
                "stats": self.connection_stats
            }
        
        @self.app.post("/notify")
        async def send_notification(notification_request: dict):
            """Send notification - notification LEGO function"""
            try:
                user_ids = notification_request.get("user_ids", [])
                notification_type = notification_request.get("type", "info")
                title = notification_request.get("title", "Notification")
                message = notification_request.get("message")
                channels = notification_request.get("channels", ["in_app"])
                
                if not user_ids or not message:
                    raise HTTPException(400, "User IDs and message required")
                
                notification = {
                    "id": str(uuid.uuid4()),
                    "type": notification_type,
                    "title": title,
                    "message": message,
                    "channels": channels,
                    "created_at": datetime.utcnow().isoformat(),
                    "superinstance_notification": True
                }
                
                # Queue notifications for users
                delivered_count = 0
                for user_id in user_ids:
                    if user_id in self.user_connections and self.user_connections[user_id]:
                        # User is online, send immediately
                        await self._deliver_notification_to_user(user_id, notification)
                        delivered_count += 1
                    else:
                        # User is offline, queue for later
                        self.notification_queue[user_id].append(notification)
                
                return {
                    "status": "notification_sent",
                    "notification_id": notification["id"],
                    "target_users": len(user_ids),
                    "delivered_immediately": delivered_count,
                    "queued": len(user_ids) - delivered_count
                }
                
            except Exception as e:
                raise HTTPException(500, f"Notification failed: {str(e)}")
    
    async def connect_client(self, websocket: WebSocket, client_id: str):
        """Connect new WebSocket client"""
        if len(self.active_connections) >= self.max_connections:
            await websocket.close(code=1008, reason="Maximum connections reached")
            return
        
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_metadata[client_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "message_count": 0,
            "subscriptions": [],
            "user_id": None
        }
        
        # Update stats
        self.connection_stats["total_connections"] += 1
        self.connection_stats["current_connections"] = len(self.active_connections)
        self.connection_stats["peak_connections"] = max(
            self.connection_stats["peak_connections"],
            self.connection_stats["current_connections"]
        )
        
        # Send welcome message
        welcome_event = {
            "type": "connection.established",
            "client_id": client_id,
            "deployment_mode": self.deployment_mode,
            "superinstance_welcome": "Connected to $2/month real-time infrastructure",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._send_to_client(client_id, welcome_event)
        
        # Deliver queued notifications if user reconnects
        await self._deliver_queued_notifications(client_id)
    
    async def disconnect_client(self, client_id: str):
        """Disconnect WebSocket client"""
        if client_id in self.active_connections:
            # Clean up subscriptions
            for event_type, subscribers in self.subscription_registry.items():
                subscribers.discard(client_id)
            
            # Clean up user connections
            user_id = self.connection_metadata.get(client_id, {}).get("user_id")
            if user_id:
                self.user_connections[user_id].discard(client_id)
            
            # Remove connection
            del self.active_connections[client_id]
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]
            
            # Update stats
            self.connection_stats["current_connections"] = len(self.active_connections)
    
    async def handle_message(self, client_id: str, data: str):
        """Handle incoming message from client"""
        try:
            message = json.loads(data)
            event_type = message.get("type", "unknown")
            
            # Update message count
            if client_id in self.connection_metadata:
                self.connection_metadata[client_id]["message_count"] += 1
            
            self.connection_stats["messages_received"] += 1
            
            # Handle different event types
            if event_type in self.event_handlers:
                await self.event_handlers[event_type](client_id, message)
            else:
                # Default handling - broadcast to subscribers
                await self._broadcast_event(message)
            
            # Store in event history
            self.event_history[event_type].append({
                "client_id": client_id,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except json.JSONDecodeError:
            await self._send_error_to_client(client_id, "Invalid JSON message")
        except Exception as e:
            await self._send_error_to_client(client_id, f"Message handling failed: {str(e)}")
    
    async def _broadcast_event(self, event: Dict, target_users: List[str] = None) -> int:
        """Broadcast event to subscribers"""
        event_type = event.get("type", "general")
        recipient_count = 0
        
        if target_users:
            # Targeted broadcast to specific users
            for user_id in target_users:
                if user_id in self.user_connections:
                    for client_id in self.user_connections[user_id]:
                        if client_id in self.active_connections:
                            await self._send_to_client(client_id, event)
                            recipient_count += 1
        else:
            # Broadcast to all subscribers of this event type
            if event_type in self.subscription_registry:
                for client_id in self.subscription_registry[event_type]:
                    if client_id in self.active_connections:
                        await self._send_to_client(client_id, event)
                        recipient_count += 1
        
        self.connection_stats["messages_sent"] += recipient_count
        return recipient_count
    
    async def _send_to_client(self, client_id: str, message: Dict):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                # Connection might be broken, clean it up
                await self.disconnect_client(client_id)
    
    async def _send_error_to_client(self, client_id: str, error_message: str):
        """Send error message to client"""
        error_event = {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self._send_to_client(client_id, error_event)
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register custom event handler"""
        self.event_handlers[event_type] = handler
    
    def get_app(self):
        """Get FastAPI app for deployment"""
        return self.app

# SUPERINSTANCE DEPLOYMENT CONFIGURATIONS
DEPLOYMENT_CONFIGS = {
    "device_local": {
        "deployment_mode": "device",
        "max_connections": 100,
        "message_history_limit": 500,
        "features": ["local_events", "offline_queue", "personal_collaboration"]
    },
    "edge_regional": {
        "deployment_mode": "edge",
        "max_connections": 5000,
        "message_history_limit": 2000,
        "features": ["regional_events", "intelligent_routing", "collaborative_editing"]
    },
    "cloud_global": {
        "deployment_mode": "cloud",
        "max_connections": 50000,
        "message_history_limit": 10000,
        "features": ["global_events", "massive_scale", "enterprise_collaboration", "analytics"]
    }
}

# SUPERINSTANCE FACTORY FUNCTION
def create_realtime_events_lego(deployment_type: str = "edge_regional"):
    """Factory function to create SuperInstance Real-time Events Lego
    
    The real-time infrastructure that makes $2/month live collaboration possible.
    Perfect interfaces, massive scale, revolutionary event orchestration.
    """
    config = DEPLOYMENT_CONFIGS.get(deployment_type, DEPLOYMENT_CONFIGS["edge_regional"])
    return RealtimeEventsLego(config)

# INTEGRATION INTERFACES
def integrate_with_chat_system(events_lego: RealtimeEventsLego, chat_service_url: str):
    """Connect real-time events to chat system"""
    # Integration logic would be implemented here
    pass

def integrate_with_collaborative_editor(events_lego: RealtimeEventsLego, editor_service_url: str):
    """Connect real-time events to collaborative editing"""
    # Integration logic would be implemented here
    pass

# SUPERINSTANCE MISSION STATEMENT
"""
This Real-time Events Lego embodies the SuperInstance vision:

- $2/month real-time infrastructure that enables infinite live possibilities
- Perfect interfaces support any real-time collaboration scenario
- Revolutionary scalability from personal to enterprise deployments  
- Lego principle: Real-time = Connections + Events + Broadcasting

Every real-time interaction powered by this Lego contributes to the
SuperInstance mission of democratizing live collaboration.
"""