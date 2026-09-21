#!/usr/bin/env python3
"""
Event Streamer - Provides real-time event streaming capabilities
Handles Server-Sent Events (SSE), WebSocket connections, and event filtering
"""

import asyncio
import json
import uuid
import time
import logging
from typing import Dict, List, Any, Optional, Set, Callable, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from queue import Queue, Empty
import sqlite3
from flask import Response
import websockets
import aiohttp
from aiohttp import web, WSMsgType
from aiohttp_sse import sse_response

logger = logging.getLogger(__name__)


@dataclass
class EventSubscription:
    """Event subscription configuration"""
    id: str
    user_id: Optional[str]
    events: List[str]  # Event types to subscribe to
    filters: Dict[str, Any]  # Event filters
    connection_type: str  # 'sse' or 'websocket'
    created_at: str
    last_heartbeat: str
    active: bool = True
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.last_heartbeat:
            self.last_heartbeat = self.created_at


@dataclass
class StreamEvent:
    """Streaming event data"""
    id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: str
    source: str
    target_subscriptions: Optional[List[str]] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class EventStreamer:
    """Manages real-time event streaming via SSE and WebSockets"""
    
    def __init__(self, config):
        self.config = config
        self.subscriptions = {}  # subscription_id -> EventSubscription
        self.sse_connections = {}  # subscription_id -> SSE generator
        self.websocket_connections = {}  # subscription_id -> WebSocket
        self.event_queue = Queue()
        
        # Database for persistent storage
        self.db_path = Path("/home/activeloguser/activelog/data/cli-interface/events.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Event distribution thread
        self.running = True
        self.distributor_thread = threading.Thread(target=self._distribute_events, daemon=True)
        self.distributor_thread.start()
        
        # Cleanup thread for inactive subscriptions
        self.cleanup_thread = threading.Thread(target=self._cleanup_inactive_subscriptions, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("Event Streamer initialized")

    def create_subscription(self, subscription_data: Dict[str, Any]) -> str:
        """Create new event subscription"""
        try:
            subscription_id = str(uuid.uuid4())
            
            subscription = EventSubscription(
                id=subscription_id,
                user_id=subscription_data.get('user_id'),
                events=subscription_data.get('events', ['*']),
                filters=subscription_data.get('filters', {}),
                connection_type=subscription_data.get('connection_type', 'sse'),
                created_at=datetime.utcnow().isoformat(),
                last_heartbeat=datetime.utcnow().isoformat()
            )
            
            self.subscriptions[subscription_id] = subscription
            self._save_subscription(subscription)
            
            logger.info(f"Created subscription {subscription_id} for events: {subscription.events}")
            return subscription_id
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            raise

    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete event subscription"""
        try:
            if subscription_id in self.subscriptions:
                # Close connections
                if subscription_id in self.sse_connections:
                    del self.sse_connections[subscription_id]
                
                if subscription_id in self.websocket_connections:
                    ws = self.websocket_connections[subscription_id]
                    if not ws.closed:
                        asyncio.create_task(ws.close())
                    del self.websocket_connections[subscription_id]
                
                # Remove subscription
                del self.subscriptions[subscription_id]
                self._delete_subscription(subscription_id)
                
                logger.info(f"Deleted subscription {subscription_id}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete subscription {subscription_id}: {e}")
            return False

    def stream_events(self, subscription_id: str) -> Response:
        """Create SSE stream for subscription"""
        try:
            subscription = self.subscriptions.get(subscription_id)
            if not subscription:
                return Response("Subscription not found", status=404)
            
            if not subscription.active:
                return Response("Subscription inactive", status=410)
            
            # Create SSE generator
            def generate_events():
                # Send initial connection event
                yield f"data: {json.dumps({'event_type': 'connection.established', 'subscription_id': subscription_id, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                
                # Create event queue for this subscription
                subscription_queue = Queue()
                self.sse_connections[subscription_id] = subscription_queue
                
                try:
                    while subscription.active:
                        try:
                            # Get event from queue (blocking with timeout)
                            event_data = subscription_queue.get(timeout=30)  # 30 second timeout
                            
                            if event_data is None:  # Shutdown signal
                                break
                            
                            # Format as SSE
                            if isinstance(event_data, dict):
                                yield f"data: {json.dumps(event_data)}\n\n"
                            else:
                                yield f"data: {event_data}\n\n"
                            
                        except Empty:
                            # Send heartbeat to keep connection alive
                            heartbeat = {
                                'event_type': 'heartbeat',
                                'timestamp': datetime.utcnow().isoformat(),
                                'subscription_id': subscription_id
                            }
                            yield f"data: {json.dumps(heartbeat)}\n\n"
                            
                            # Update last heartbeat
                            subscription.last_heartbeat = datetime.utcnow().isoformat()
                            
                except GeneratorExit:
                    # Client disconnected
                    logger.info(f"SSE client disconnected for subscription {subscription_id}")
                finally:
                    # Cleanup
                    if subscription_id in self.sse_connections:
                        del self.sse_connections[subscription_id]
            
            return Response(generate_events(), mimetype='text/event-stream',
                          headers={'Cache-Control': 'no-cache',
                                 'Connection': 'keep-alive',
                                 'Access-Control-Allow-Origin': '*'})
            
        except Exception as e:
            logger.error(f"Failed to create SSE stream for {subscription_id}: {e}")
            return Response("Internal server error", status=500)

    async def websocket_handler(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        subscription_id = None
        
        try:
            # Wait for subscription message
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        
                        if data.get('action') == 'subscribe':
                            # Create subscription
                            subscription_data = data.get('subscription', {})
                            subscription_data['connection_type'] = 'websocket'
                            subscription_id = self.create_subscription(subscription_data)
                            
                            # Store WebSocket connection
                            self.websocket_connections[subscription_id] = ws
                            
                            # Send confirmation
                            await ws.send_str(json.dumps({
                                'event_type': 'subscription.created',
                                'subscription_id': subscription_id,
                                'timestamp': datetime.utcnow().isoformat()
                            }))
                            
                        elif data.get('action') == 'unsubscribe' and subscription_id:
                            self.delete_subscription(subscription_id)
                            break
                            
                        elif data.get('action') == 'ping':
                            # Update heartbeat
                            if subscription_id and subscription_id in self.subscriptions:
                                self.subscriptions[subscription_id].last_heartbeat = datetime.utcnow().isoformat()
                                await ws.send_str(json.dumps({
                                    'event_type': 'pong',
                                    'timestamp': datetime.utcnow().isoformat()
                                }))
                        
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            'event_type': 'error',
                            'error': 'Invalid JSON',
                            'timestamp': datetime.utcnow().isoformat()
                        }))
                        
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    break
        
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        
        finally:
            # Cleanup
            if subscription_id:
                self.delete_subscription(subscription_id)
        
        return ws

    def publish_event(self, event_type: str, data: Dict[str, Any], 
                     source: str = "cli-interface", 
                     target_subscriptions: Optional[List[str]] = None) -> str:
        """Publish event to all matching subscriptions"""
        try:
            event = StreamEvent(
                id=str(uuid.uuid4()),
                event_type=event_type,
                data=data,
                timestamp=datetime.utcnow().isoformat(),
                source=source,
                target_subscriptions=target_subscriptions
            )
            
            # Queue event for distribution
            self.event_queue.put(event)
            
            logger.info(f"Published event {event_type} with ID {event.id}")
            return event.id
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            raise

    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        try:
            total_subscriptions = len(self.subscriptions)
            active_subscriptions = sum(1 for s in self.subscriptions.values() if s.active)
            sse_connections = len(self.sse_connections)
            ws_connections = len(self.websocket_connections)
            
            # Count by event type
            event_type_counts = {}
            for subscription in self.subscriptions.values():
                for event_type in subscription.events:
                    event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            
            return {
                'total_subscriptions': total_subscriptions,
                'active_subscriptions': active_subscriptions,
                'sse_connections': sse_connections,
                'websocket_connections': ws_connections,
                'event_type_distribution': event_type_counts,
                'queue_size': self.event_queue.qsize()
            }
            
        except Exception as e:
            logger.error(f"Failed to get subscription stats: {e}")
            return {}

    def list_subscriptions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active subscriptions"""
        try:
            subscriptions = []
            for subscription in self.subscriptions.values():
                if user_id and subscription.user_id != user_id:
                    continue
                
                subscriptions.append({
                    'id': subscription.id,
                    'user_id': subscription.user_id,
                    'events': subscription.events,
                    'connection_type': subscription.connection_type,
                    'created_at': subscription.created_at,
                    'last_heartbeat': subscription.last_heartbeat,
                    'active': subscription.active
                })
            
            return subscriptions
            
        except Exception as e:
            logger.error(f"Failed to list subscriptions: {e}")
            return []

    def _distribute_events(self):
        """Background thread to distribute events to subscriptions"""
        while self.running:
            try:
                # Get event from queue (blocking with timeout)
                event = self.event_queue.get(timeout=1)
                
                # Find matching subscriptions
                matching_subscriptions = self._find_matching_subscriptions(event)
                
                # Distribute to each matching subscription
                for subscription_id in matching_subscriptions:
                    self._send_event_to_subscription(event, subscription_id)
                
                # Save event to database for history
                self._save_event(event)
                
                self.event_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error distributing event: {e}")

    def _find_matching_subscriptions(self, event: StreamEvent) -> List[str]:
        """Find subscriptions that match the event"""
        matching = []
        
        for subscription_id, subscription in self.subscriptions.items():
            if not subscription.active:
                continue
            
            # Check target subscriptions first
            if event.target_subscriptions:
                if subscription_id not in event.target_subscriptions:
                    continue
            
            # Check event type match
            if event.event_type in subscription.events or '*' in subscription.events:
                # Apply filters
                if self._event_matches_filters(event, subscription.filters):
                    matching.append(subscription_id)
        
        return matching

    def _event_matches_filters(self, event: StreamEvent, filters: Dict[str, Any]) -> bool:
        """Check if event matches subscription filters"""
        if not filters:
            return True
        
        try:
            for filter_key, filter_value in filters.items():
                if filter_key == 'source':
                    if event.source != filter_value:
                        return False
                elif filter_key == 'user_id':
                    if event.data.get('user_id') != filter_value:
                        return False
                elif filter_key in event.data:
                    if event.data[filter_key] != filter_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying event filters: {e}")
            return True  # Default to include on error

    def _send_event_to_subscription(self, event: StreamEvent, subscription_id: str):
        """Send event to specific subscription"""
        try:
            event_data = {
                'event_id': event.id,
                'event_type': event.event_type,
                'timestamp': event.timestamp,
                'source': event.source,
                'data': event.data
            }
            
            # Send to SSE connection
            if subscription_id in self.sse_connections:
                queue = self.sse_connections[subscription_id]
                try:
                    queue.put_nowait(event_data)
                except:
                    # Queue full or connection closed
                    logger.warning(f"Failed to queue event for SSE subscription {subscription_id}")
                    del self.sse_connections[subscription_id]
            
            # Send to WebSocket connection
            if subscription_id in self.websocket_connections:
                ws = self.websocket_connections[subscription_id]
                if not ws.closed:
                    try:
                        # Use asyncio to send WebSocket message
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(ws.send_str(json.dumps(event_data)))
                        loop.close()
                    except Exception as e:
                        logger.warning(f"Failed to send WebSocket event to {subscription_id}: {e}")
                        del self.websocket_connections[subscription_id]
                else:
                    del self.websocket_connections[subscription_id]
            
        except Exception as e:
            logger.error(f"Failed to send event to subscription {subscription_id}: {e}")

    def _cleanup_inactive_subscriptions(self):
        """Background thread to cleanup inactive subscriptions"""
        while self.running:
            try:
                current_time = datetime.utcnow()
                inactive_timeout = timedelta(minutes=10)  # 10 minutes timeout
                
                inactive_subscriptions = []
                
                for subscription_id, subscription in self.subscriptions.items():
                    last_heartbeat = datetime.fromisoformat(subscription.last_heartbeat)
                    if current_time - last_heartbeat > inactive_timeout:
                        inactive_subscriptions.append(subscription_id)
                
                # Remove inactive subscriptions
                for subscription_id in inactive_subscriptions:
                    logger.info(f"Cleaning up inactive subscription {subscription_id}")
                    self.delete_subscription(subscription_id)
                
                # Sleep for 1 minute before next cleanup
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
                time.sleep(60)

    def _init_database(self):
        """Initialize SQLite database for persistent storage"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create subscriptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    events TEXT NOT NULL,
                    filters TEXT,
                    connection_type TEXT DEFAULT 'sse',
                    created_at TEXT,
                    last_heartbeat TEXT,
                    active INTEGER DEFAULT 1
                )
            """)
            
            # Create events table for history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp TEXT,
                    source TEXT,
                    target_subscriptions TEXT
                )
            """)
            
            # Create index on timestamp for efficient queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON events(timestamp)
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _save_subscription(self, subscription: EventSubscription):
        """Save subscription to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO subscriptions 
                (id, user_id, events, filters, connection_type, created_at, last_heartbeat, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subscription.id,
                subscription.user_id,
                json.dumps(subscription.events),
                json.dumps(subscription.filters),
                subscription.connection_type,
                subscription.created_at,
                subscription.last_heartbeat,
                int(subscription.active)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save subscription {subscription.id}: {e}")

    def _delete_subscription(self, subscription_id: str):
        """Delete subscription from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to delete subscription {subscription_id}: {e}")

    def _save_event(self, event: StreamEvent):
        """Save event to database for history"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO events 
                (id, event_type, data, timestamp, source, target_subscriptions)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event.id,
                event.event_type,
                json.dumps(event.data),
                event.timestamp,
                event.source,
                json.dumps(event.target_subscriptions) if event.target_subscriptions else None
            ))
            
            conn.commit()
            conn.close()
            
            # Cleanup old events (keep only last 10000)
            self._cleanup_old_events()
            
        except Exception as e:
            logger.error(f"Failed to save event {event.id}: {e}")

    def _cleanup_old_events(self):
        """Cleanup old events from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Keep only the most recent 10000 events
            cursor.execute("""
                DELETE FROM events WHERE id NOT IN (
                    SELECT id FROM events 
                    ORDER BY timestamp DESC 
                    LIMIT 10000
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")

    def get_event_history(self, event_type: Optional[str] = None, 
                         limit: int = 100, 
                         since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get event history from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            query = "SELECT * FROM events"
            params = []
            
            conditions = []
            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type)
            
            if since:
                conditions.append("timestamp >= ?")
                params.append(since)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            events = []
            for row in rows:
                events.append({
                    'id': row[0],
                    'event_type': row[1],
                    'data': json.loads(row[2]),
                    'timestamp': row[3],
                    'source': row[4],
                    'target_subscriptions': json.loads(row[5]) if row[5] else None
                })
            
            conn.close()
            return events
            
        except Exception as e:
            logger.error(f"Failed to get event history: {e}")
            return []

    def shutdown(self):
        """Shutdown event streamer"""
        self.running = False
        
        # Close all connections
        for subscription_id in list(self.sse_connections.keys()):
            queue = self.sse_connections[subscription_id]
            queue.put(None)  # Shutdown signal
        
        for subscription_id in list(self.websocket_connections.keys()):
            ws = self.websocket_connections[subscription_id]
            if not ws.closed:
                asyncio.create_task(ws.close())
        
        # Wait for threads to finish
        if self.distributor_thread.is_alive():
            self.distributor_thread.join(timeout=5)
        
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        
        logger.info("Event Streamer shut down")