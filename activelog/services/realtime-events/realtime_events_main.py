#!/usr/bin/env python3
"""
ActiveLog Real-Time Event System - Main Server
Comprehensive real-time event system with WebSocket hub supporting 10,000+ connections
"""

import asyncio
import json
import logging
import time
from pathlib import Path
import sys

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import all components
from websocket.websocket_hub import WebSocketHub, Event
from collaboration.operational_transforms import OperationalTransform
from events.activity_feeds import ActivityFeed, ActivityEvent, ActivityType, FilterCriteria
from notifications.notification_queue import (
    NotificationQueue, push_notification_handler, 
    email_notification_handler, in_app_notification_handler
)
from persistence.event_replay import EventPersistence, ReplayRequest, EventPersistenceLevel
from webrtc.signaling_server import WebRTCSignalingServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealTimeEventSystem:
    """Main real-time event system orchestrating all components"""
    
    def __init__(self, host: str = "localhost", port: int = 8101):
        self.host = host
        self.port = port
        
        # Initialize core components
        logger.info("🚀 Initializing ActiveLog Real-Time Event System")
        
        # WebSocket hub - supports 10,000+ concurrent connections
        self.websocket_hub = WebSocketHub(host=host, port=port)
        
        # Collaborative editing with operational transforms
        self.operational_transform = OperationalTransform()
        
        # Live activity feeds with advanced filtering
        self.activity_feed = ActivityFeed()
        
        # Push notification queue for offline users
        self.notification_queue = NotificationQueue()
        
        # Event persistence and replay system
        self.event_persistence = EventPersistence()
        
        # WebRTC signaling server for P2P connections
        self.webrtc_signaling = WebRTCSignalingServer()
        
        # Connect components
        self._setup_integrations()
        
        # Performance tracking
        self.start_time = time.time()
        
        logger.info("✅ All components initialized successfully")
    
    def _setup_integrations(self):
        """Setup integrations between components"""
        logger.info("🔗 Setting up component integrations")
        
        # Connect WebRTC signaling to WebSocket hub
        self.webrtc_signaling.set_websocket_hub(self.websocket_hub)
        
        # Register notification delivery handlers
        self.notification_queue.register_delivery_handler("push", push_notification_handler)
        self.notification_queue.register_delivery_handler("email", email_notification_handler)
        self.notification_queue.register_delivery_handler("in_app", in_app_notification_handler)
        
        # Register WebSocket event handlers
        self._register_event_handlers()
        
        logger.info("✅ Component integrations complete")
    
    def _register_event_handlers(self):
        """Register event handlers for different message types"""
        
        # Collaborative editing events
        self.websocket_hub.register_event_handler("document.operation", self._handle_document_operation)
        self.websocket_hub.register_event_handler("document.create", self._handle_document_create)
        
        # Activity feed events
        self.websocket_hub.register_event_handler("activity.subscribe", self._handle_activity_subscribe)
        self.websocket_hub.register_event_handler("activity.get", self._handle_activity_get)
        
        # Notification events
        self.websocket_hub.register_event_handler("notification.create", self._handle_notification_create)
        self.websocket_hub.register_event_handler("notification.get", self._handle_notification_get)
        self.websocket_hub.register_event_handler("notification.mark_read", self._handle_notification_mark_read)
        
        # Event replay events
        self.websocket_hub.register_event_handler("replay.request", self._handle_replay_request)
        self.websocket_hub.register_event_handler("replay.subscribe", self._handle_replay_subscribe)
        
        # WebRTC signaling events
        self.websocket_hub.register_event_handler("webrtc.signal", self._handle_webrtc_signal)
        self.websocket_hub.register_event_handler("webrtc.room_list", self._handle_webrtc_room_list)
        
        # Presence events
        self.websocket_hub.register_event_handler("presence.get", self._handle_presence_get)
        
        logger.info("📡 Event handlers registered")
    
    async def _handle_document_operation(self, connection_id: str, data: Dict[str, Any]):
        """Handle document operation for collaborative editing"""
        try:
            doc_id = data.get("document_id")
            operation_data = data.get("operation", {})
            
            if not doc_id or not operation_data:
                return
            
            # Create operation
            operation = self.operational_transform.create_operation(
                op_type=operation_data.get("type"),
                position=operation_data.get("position", 0),
                content=operation_data.get("content", ""),
                length=operation_data.get("length", 0),
                author=data.get("user_id", connection_id)
            )
            
            # Apply operation
            success, document, transformed_ops = self.operational_transform.apply_operation(doc_id, operation)
            
            if success:
                # Broadcast to collaborators
                namespace = data.get("namespace", "default")
                room = f"document:{doc_id}"
                
                await self.websocket_hub.broadcast_to_room(namespace, room, Event(
                    id=str(uuid.uuid4()),
                    type="document.operation_applied",
                    namespace=namespace,
                    room=room,
                    data={
                        "document_id": doc_id,
                        "operation": {
                            "type": operation.type.value,
                            "position": operation.position,
                            "content": operation.content,
                            "length": operation.length,
                            "author": operation.author
                        },
                        "document_version": document.version
                    }
                ), exclude=[connection_id])
                
                # Store event for replay
                await self.event_persistence.store_event(
                    event_id=str(uuid.uuid4()),
                    event_type="document.operation",
                    namespace=namespace,
                    data={
                        "document_id": doc_id,
                        "operation": operation_data,
                        "version": document.version
                    },
                    user_id=operation.author,
                    room=room,
                    persistence_level=EventPersistenceLevel.DISK
                )
                
                # Create activity
                await self.activity_feed.create_activity(
                    activity_type="document.edit",
                    namespace=namespace,
                    user_id=operation.author,
                    target_id=doc_id,
                    target_type="document",
                    data={
                        "operation_type": operation.type.value,
                        "characters_changed": len(operation.content) if operation.content else operation.length
                    },
                    room=room
                )
            
        except Exception as e:
            logger.error(f"Error handling document operation: {e}")
    
    async def _handle_document_create(self, connection_id: str, data: Dict[str, Any]):
        """Handle document creation"""
        try:
            doc_id = data.get("document_id")
            initial_content = data.get("content", "")
            author = data.get("user_id", connection_id)
            
            if not doc_id:
                return
            
            # Create document
            document = self.operational_transform.create_document(doc_id, initial_content, author)
            
            # Send confirmation
            await self.websocket_hub.send_to_connection(connection_id, Event(
                id=str(uuid.uuid4()),
                type="document.created",
                namespace=data.get("namespace", "default"),
                data={
                    "document_id": doc_id,
                    "version": document.version,
                    "content": document.content
                }
            ))
            
        except Exception as e:
            logger.error(f"Error handling document creation: {e}")
    
    async def _handle_activity_subscribe(self, connection_id: str, data: Dict[str, Any]):
        """Handle activity feed subscription"""
        try:
            criteria = FilterCriteria(
                namespaces=set(data.get("namespaces", [])),
                activity_types=set(ActivityType(t) for t in data.get("activity_types", [])),
                user_ids=set(data.get("user_ids", [])),
                rooms=set(data.get("rooms", [])),
                max_results=data.get("max_results", 100)
            )
            
            # Create callback to send updates
            async def activity_callback(event: ActivityEvent):
                await self.websocket_hub.send_to_connection(connection_id, Event(
                    id=str(uuid.uuid4()),
                    type="activity.update",
                    namespace=event.namespace,
                    data={
                        "activity": {
                            "id": event.id,
                            "type": event.type.value,
                            "user_id": event.user_id,
                            "target_id": event.target_id,
                            "target_type": event.target_type,
                            "data": event.data,
                            "timestamp": event.timestamp,
                            "room": event.room
                        }
                    }
                ))
            
            # Subscribe
            self.activity_feed.subscribe(connection_id, criteria, activity_callback)
            
        except Exception as e:
            logger.error(f"Error handling activity subscription: {e}")
    
    async def _handle_activity_get(self, connection_id: str, data: Dict[str, Any]):
        """Handle activity feed get request"""
        try:
            criteria = FilterCriteria(
                namespaces=set(data.get("namespaces", [])),
                activity_types=set(ActivityType(t) for t in data.get("activity_types", [])),
                user_ids=set(data.get("user_ids", [])),
                rooms=set(data.get("rooms", [])),
                since_timestamp=data.get("since_timestamp", 0),
                max_results=data.get("max_results", 100)
            )
            
            activities = self.activity_feed.get_activities(criteria)
            
            await self.websocket_hub.send_to_connection(connection_id, Event(
                id=str(uuid.uuid4()),
                type="activity.list",
                namespace=data.get("namespace", "default"),
                data={
                    "activities": [
                        {
                            "id": activity.id,
                            "type": activity.type.value,
                            "user_id": activity.user_id,
                            "target_id": activity.target_id,
                            "target_type": activity.target_type,
                            "data": activity.data,
                            "timestamp": activity.timestamp,
                            "room": activity.room
                        }
                        for activity in activities
                    ]
                }
            ))
            
        except Exception as e:
            logger.error(f"Error handling activity get: {e}")
    
    async def _handle_notification_create(self, connection_id: str, data: Dict[str, Any]):
        """Handle notification creation"""
        try:
            notification = await self.notification_queue.create_notification(
                user_id=data.get("user_id"),
                notification_type=data.get("type"),
                title=data.get("title"),
                body=data.get("body"),
                data=data.get("data", {}),
                namespace=data.get("namespace", "default"),
                priority=data.get("priority", "medium"),
                channels=data.get("channels", ["push", "in_app"]),
                ttl=data.get("ttl")
            )
            
            await self.websocket_hub.send_to_connection(connection_id, Event(
                id=str(uuid.uuid4()),
                type="notification.created",
                namespace=data.get("namespace", "default"),
                data={"notification_id": notification.id}
            ))
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
    
    async def _handle_notification_get(self, connection_id: str, data: Dict[str, Any]):
        """Handle get notifications request"""
        try:
            user_id = data.get("user_id")
            status = data.get("status")
            limit = data.get("limit", 100)
            
            notifications = await self.notification_queue.get_user_notifications(user_id, status, limit)
            
            await self.websocket_hub.send_to_connection(connection_id, Event(
                id=str(uuid.uuid4()),
                type="notification.list",
                namespace=data.get("namespace", "default"),
                data={
                    "notifications": [
                        {
                            "id": notif.id,
                            "type": notif.type.value,
                            "title": notif.title,
                            "body": notif.body,
                            "data": notif.data,
                            "created_at": notif.created_at,
                            "status": notif.status.value
                        }
                        for notif in notifications
                    ]
                }
            ))
            
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
    
    async def _handle_notification_mark_read(self, connection_id: str, data: Dict[str, Any]):
        """Handle mark notifications as read"""
        try:
            notification_ids = data.get("notification_ids", [])
            user_id = data.get("user_id")
            
            await self.notification_queue.mark_as_read(notification_ids, user_id)
            
            await self.websocket_hub.send_to_connection(connection_id, Event(
                id=str(uuid.uuid4()),
                type="notification.marked_read",
                namespace=data.get("namespace", "default"),
                data={"success": True}
            ))
            
        except Exception as e:
            logger.error(f"Error marking notifications as read: {e}")
    
    async def _handle_replay_request(self, connection_id: str, data: Dict[str, Any]):
        """Handle event replay request"""
        try:
            request = ReplayRequest(
                user_id=data.get("user_id"),
                namespaces=set(data.get("namespaces", [])),
                rooms=set(data.get("rooms", [])),
                event_types=set(data.get("event_types", [])),
                since_timestamp=data.get("since_timestamp", 0),
                since_sequence=data.get("since_sequence", 0),
                limit=data.get("limit", 1000),
                include_own_events=data.get("include_own_events", False)
            )
            
            events = await self.event_persistence.replay_events(request)
            
            await self.websocket_hub.send_to_connection(connection_id, Event(
                id=str(uuid.uuid4()),
                type="replay.events",
                namespace=data.get("namespace", "default"),
                data={
                    "events": events,
                    "total_events": len(events)
                }
            ))
            
        except Exception as e:
            logger.error(f"Error handling replay request: {e}")
    
    async def _handle_replay_subscribe(self, connection_id: str, data: Dict[str, Any]):
        """Handle replay subscription for missed events"""
        try:
            request = ReplayRequest(
                user_id=data.get("user_id"),
                namespaces=set(data.get("namespaces", [])),
                rooms=set(data.get("rooms", [])),
                event_types=set(data.get("event_types", [])),
                since_sequence=data.get("since_sequence", 0),
                limit=data.get("limit", 1000)
            )
            
            await self.event_persistence.subscribe_user(data.get("user_id"), request)
            
            await self.websocket_hub.send_to_connection(connection_id, Event(
                id=str(uuid.uuid4()),
                type="replay.subscribed",
                namespace=data.get("namespace", "default"),
                data={"success": True}
            ))
            
        except Exception as e:
            logger.error(f"Error handling replay subscription: {e}")
    
    async def _handle_webrtc_signal(self, connection_id: str, data: Dict[str, Any]):
        """Handle WebRTC signaling message"""
        try:
            await self.webrtc_signaling.handle_signaling_message(connection_id, data)
        except Exception as e:
            logger.error(f"Error handling WebRTC signal: {e}")
    
    async def _handle_webrtc_room_list(self, connection_id: str, data: Dict[str, Any]):
        """Handle WebRTC room list request"""
        try:
            namespace = data.get("namespace")
            rooms = self.webrtc_signaling.list_rooms(namespace)
            
            await self.websocket_hub.send_to_connection(connection_id, Event(
                id=str(uuid.uuid4()),
                type="webrtc.room_list",
                namespace=data.get("namespace", "default"),
                data={"rooms": rooms}
            ))
            
        except Exception as e:
            logger.error(f"Error handling WebRTC room list: {e}")
    
    async def _handle_presence_get(self, connection_id: str, data: Dict[str, Any]):
        """Handle presence information request"""
        try:
            namespace = data.get("namespace")
            room = data.get("room")
            
            presence_info = self.websocket_hub.get_presence_info(namespace, room)
            
            await self.websocket_hub.send_to_connection(connection_id, Event(
                id=str(uuid.uuid4()),
                type="presence.info",
                namespace=namespace or "default",
                data=presence_info
            ))
            
        except Exception as e:
            logger.error(f"Error handling presence get: {e}")
    
    async def start_server(self):
        """Start the real-time event system"""
        logger.info("🚀 Starting ActiveLog Real-Time Event System")
        logger.info("📊 System Features:")
        logger.info("  • WebSocket Hub supporting 10,000+ concurrent connections")
        logger.info("  • Event namespacing for different apps (PersonalLog, BusinessLog, etc.)")
        logger.info("  • Real-time presence system")
        logger.info("  • Collaborative editing with operational transforms")
        logger.info("  • Real-time cursor tracking")
        logger.info("  • Live activity feeds with advanced filtering")
        logger.info("  • Push notification queue for offline users")
        logger.info("  • Event replay for missed messages")
        logger.info("  • Bandwidth-adaptive streaming")
        logger.info("  • Event persistence with replay capability")
        logger.info("  • Room-based broadcasting")
        logger.info("  • WebRTC signaling server for P2P connections")
        logger.info("="*80)
        
        # Start the WebSocket server
        await self.websocket_hub.start_server()
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        uptime = time.time() - self.start_time
        
        return {
            "uptime": uptime,
            "websocket_hub": self.websocket_hub.stats,
            "operational_transform": self.operational_transform.get_stats(),
            "activity_feed": self.activity_feed.get_activity_stats(),
            "notification_queue": self.notification_queue.get_stats(),
            "event_persistence": self.event_persistence.get_stats(),
            "webrtc_signaling": self.webrtc_signaling.get_stats()
        }

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Real-Time Event System")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8101, help="Server port")
    args = parser.parse_args()
    
    # Create and start system
    system = RealTimeEventSystem(host=args.host, port=args.port)
    
    try:
        asyncio.run(system.start_server())
    except KeyboardInterrupt:
        logger.info("👋 Real-Time Event System stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start Real-Time Event System: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()