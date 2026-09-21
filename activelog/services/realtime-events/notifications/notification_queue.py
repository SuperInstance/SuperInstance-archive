#!/usr/bin/env python3
"""
ActiveLog Real-Time Event System - Push Notification Queue
Handles push notifications for offline users with delivery guarantees
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import logging
import sqlite3
import threading

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Types of notifications"""
    MESSAGE = "message"
    DOCUMENT_EDIT = "document_edit" 
    MENTION = "mention"
    COLLABORATION_INVITE = "collaboration_invite"
    SYSTEM_ALERT = "system_alert"
    DEADLINE_REMINDER = "deadline_reminder"
    ACTIVITY_DIGEST = "activity_digest"
    CUSTOM = "custom"

class NotificationPriority(Enum):
    """Notification priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

class DeliveryStatus(Enum):
    """Notification delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"

@dataclass
class Notification:
    """Push notification structure"""
    id: str
    user_id: str
    type: NotificationType
    title: str
    body: str
    data: Dict[str, Any] = None
    namespace: str = "default"
    priority: NotificationPriority = NotificationPriority.MEDIUM
    created_at: float = 0
    expires_at: float = 0
    delivery_attempts: int = 0
    max_attempts: int = 3
    status: DeliveryStatus = DeliveryStatus.PENDING
    channels: List[str] = None  # ["push", "email", "sms", "in_app"]
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.channels is None:
            self.channels = ["push", "in_app"]
        if self.created_at == 0:
            self.created_at = time.time()
        if self.expires_at == 0:
            # Default expiry: 24 hours for normal, 7 days for critical
            default_ttl = 86400 if self.priority != NotificationPriority.CRITICAL else 604800
            self.expires_at = self.created_at + default_ttl

@dataclass
class NotificationSettings:
    """User notification preferences"""
    user_id: str
    enabled_channels: Set[str] = None
    enabled_types: Set[NotificationType] = None
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 8     # 8 AM
    timezone: str = "UTC"
    digest_frequency: str = "daily"  # "off", "hourly", "daily", "weekly"
    
    def __post_init__(self):
        if self.enabled_channels is None:
            self.enabled_channels = {"push", "in_app"}
        if self.enabled_types is None:
            self.enabled_types = set(NotificationType)

class NotificationQueue:
    """High-performance notification queue with persistence"""
    
    def __init__(self, db_path: str = ":memory:", max_queue_size: int = 100000):
        self.db_path = db_path
        self.max_queue_size = max_queue_size
        
        # In-memory queues for fast access
        self.pending_queue = deque(maxlen=max_queue_size)
        self.user_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.priority_queues: Dict[NotificationPriority, deque] = {
            priority: deque(maxlen=max_queue_size // 4) for priority in NotificationPriority
        }
        
        # User settings
        self.user_settings: Dict[str, NotificationSettings] = {}
        
        # Delivery handlers for different channels
        self.delivery_handlers: Dict[str, Callable] = {}
        
        # Statistics
        self.stats = {
            "notifications_created": 0,
            "notifications_delivered": 0,
            "notifications_failed": 0,
            "notifications_expired": 0,
            "delivery_attempts": 0
        }
        
        # Database connection
        self.db_lock = threading.Lock()
        self._init_database()
        
        # Background tasks
        self.processor_task = None
        self.cleanup_task = None
        self.start_background_tasks()
    
    def _init_database(self):
        """Initialize SQLite database for persistence"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    data TEXT,
                    namespace TEXT DEFAULT 'default',
                    priority INTEGER DEFAULT 3,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    delivery_attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    status TEXT DEFAULT 'pending',
                    channels TEXT,
                    INDEX(user_id),
                    INDEX(status),
                    INDEX(created_at),
                    INDEX(expires_at)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id TEXT PRIMARY KEY,
                    enabled_channels TEXT,
                    enabled_types TEXT,
                    quiet_hours_start INTEGER DEFAULT 22,
                    quiet_hours_end INTEGER DEFAULT 8,
                    timezone TEXT DEFAULT 'UTC',
                    digest_frequency TEXT DEFAULT 'daily'
                )
            """)
            
            conn.commit()
            conn.close()
    
    def start_background_tasks(self):
        """Start background processing tasks"""
        if not self.processor_task:
            self.processor_task = asyncio.create_task(self._process_queue())
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_expired())
    
    async def create_notification(self, user_id: str, notification_type: str, 
                                title: str, body: str, data: Dict[str, Any] = None,
                                namespace: str = "default", priority: str = "medium",
                                channels: List[str] = None, ttl: int = None) -> Notification:
        """Create a new notification"""
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=NotificationType(notification_type),
            title=title,
            body=body,
            data=data or {},
            namespace=namespace,
            priority=NotificationPriority[priority.upper()],
            channels=channels or ["push", "in_app"]
        )
        
        # Set custom TTL if provided
        if ttl:
            notification.expires_at = notification.created_at + ttl
        
        await self.enqueue_notification(notification)
        return notification
    
    async def enqueue_notification(self, notification: Notification):
        """Add notification to queue"""
        # Check user preferences
        settings = await self.get_user_settings(notification.user_id)
        
        # Check if notification type is enabled
        if notification.type not in settings.enabled_types:
            logger.debug(f"Notification type {notification.type} disabled for user {notification.user_id}")
            return
        
        # Filter channels based on user preferences
        enabled_channels = [
            channel for channel in notification.channels
            if channel in settings.enabled_channels
        ]
        notification.channels = enabled_channels
        
        if not enabled_channels:
            logger.debug(f"No enabled channels for notification {notification.id}")
            return
        
        # Add to queues
        self.pending_queue.append(notification)
        self.user_queues[notification.user_id].append(notification)
        self.priority_queues[notification.priority].append(notification)
        
        # Persist to database
        await self._persist_notification(notification)
        
        self.stats["notifications_created"] += 1
        logger.info(f"Enqueued notification {notification.id} for user {notification.user_id}")
    
    async def _persist_notification(self, notification: Notification):
        """Persist notification to database"""
        def _db_insert():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT INTO notifications 
                    (id, user_id, type, title, body, data, namespace, priority, 
                     created_at, expires_at, delivery_attempts, max_attempts, status, channels)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    notification.id,
                    notification.user_id,
                    notification.type.value,
                    notification.title,
                    notification.body,
                    json.dumps(notification.data),
                    notification.namespace,
                    notification.priority.value,
                    notification.created_at,
                    notification.expires_at,
                    notification.delivery_attempts,
                    notification.max_attempts,
                    notification.status.value,
                    json.dumps(notification.channels)
                ))
                conn.commit()
                conn.close()
        
        # Run database operation in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _db_insert)
    
    async def _process_queue(self):
        """Background task to process notification queue"""
        while True:
            try:
                # Process high-priority notifications first
                for priority in [NotificationPriority.CRITICAL, NotificationPriority.HIGH,
                               NotificationPriority.MEDIUM, NotificationPriority.LOW]:
                    queue = self.priority_queues[priority]
                    
                    # Process up to 10 notifications per priority level
                    for _ in range(min(10, len(queue))):
                        if queue:
                            notification = queue.popleft()
                            await self._deliver_notification(notification)
                
                await asyncio.sleep(1)  # Process every second
                
            except Exception as e:
                logger.error(f"Error in notification processor: {e}")
                await asyncio.sleep(5)
    
    async def _deliver_notification(self, notification: Notification):
        """Attempt to deliver a notification"""
        if notification.status != DeliveryStatus.PENDING:
            return
        
        # Check if expired
        if time.time() > notification.expires_at:
            notification.status = DeliveryStatus.EXPIRED
            await self._update_notification_status(notification)
            self.stats["notifications_expired"] += 1
            return
        
        # Check quiet hours
        settings = await self.get_user_settings(notification.user_id)
        if self._is_quiet_hours(settings) and notification.priority not in [NotificationPriority.CRITICAL]:
            # Reschedule for later
            return
        
        # Attempt delivery on each channel
        delivery_success = False
        for channel in notification.channels:
            handler = self.delivery_handlers.get(channel)
            if handler:
                try:
                    success = await handler(notification)
                    if success:
                        delivery_success = True
                        logger.debug(f"Delivered notification {notification.id} via {channel}")
                except Exception as e:
                    logger.error(f"Delivery failed for {notification.id} via {channel}: {e}")
        
        # Update delivery status
        notification.delivery_attempts += 1
        self.stats["delivery_attempts"] += 1
        
        if delivery_success:
            notification.status = DeliveryStatus.DELIVERED
            self.stats["notifications_delivered"] += 1
        elif notification.delivery_attempts >= notification.max_attempts:
            notification.status = DeliveryStatus.FAILED
            self.stats["notifications_failed"] += 1
        
        await self._update_notification_status(notification)
    
    async def _update_notification_status(self, notification: Notification):
        """Update notification status in database"""
        def _db_update():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    UPDATE notifications 
                    SET delivery_attempts = ?, status = ?
                    WHERE id = ?
                """, (notification.delivery_attempts, notification.status.value, notification.id))
                conn.commit()
                conn.close()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _db_update)
    
    def register_delivery_handler(self, channel: str, handler: Callable):
        """Register delivery handler for a channel"""
        self.delivery_handlers[channel] = handler
        logger.info(f"Registered delivery handler for channel: {channel}")
    
    async def get_user_notifications(self, user_id: str, status: str = None, 
                                   limit: int = 100) -> List[Notification]:
        """Get notifications for a user"""
        def _db_query():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                
                if status:
                    cursor = conn.execute("""
                        SELECT * FROM notifications 
                        WHERE user_id = ? AND status = ?
                        ORDER BY created_at DESC LIMIT ?
                    """, (user_id, status, limit))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM notifications 
                        WHERE user_id = ?
                        ORDER BY created_at DESC LIMIT ?
                    """, (user_id, limit))
                
                rows = cursor.fetchall()
                conn.close()
                return rows
        
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, _db_query)
        
        notifications = []
        for row in rows:
            notification = Notification(
                id=row[0],
                user_id=row[1],
                type=NotificationType(row[2]),
                title=row[3],
                body=row[4],
                data=json.loads(row[5]) if row[5] else {},
                namespace=row[6],
                priority=NotificationPriority(row[7]),
                created_at=row[8],
                expires_at=row[9],
                delivery_attempts=row[10],
                max_attempts=row[11],
                status=DeliveryStatus(row[12]),
                channels=json.loads(row[13]) if row[13] else []
            )
            notifications.append(notification)
        
        return notifications
    
    async def mark_as_read(self, notification_ids: List[str], user_id: str):
        """Mark notifications as read"""
        def _db_update():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                placeholders = ",".join(["?" for _ in notification_ids])
                conn.execute(f"""
                    UPDATE notifications 
                    SET status = 'delivered'
                    WHERE id IN ({placeholders}) AND user_id = ?
                """, notification_ids + [user_id])
                conn.commit()
                conn.close()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _db_update)
    
    async def get_user_settings(self, user_id: str) -> NotificationSettings:
        """Get user notification settings"""
        if user_id in self.user_settings:
            return self.user_settings[user_id]
        
        def _db_query():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute("""
                    SELECT * FROM user_settings WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                conn.close()
                return row
        
        loop = asyncio.get_event_loop()
        row = await loop.run_in_executor(None, _db_query)
        
        if row:
            settings = NotificationSettings(
                user_id=row[0],
                enabled_channels=set(json.loads(row[1])) if row[1] else {"push", "in_app"},
                enabled_types=set(NotificationType(t) for t in json.loads(row[2])) if row[2] else set(NotificationType),
                quiet_hours_start=row[3],
                quiet_hours_end=row[4],
                timezone=row[5],
                digest_frequency=row[6]
            )
        else:
            settings = NotificationSettings(user_id=user_id)
        
        self.user_settings[user_id] = settings
        return settings
    
    async def update_user_settings(self, user_id: str, settings: NotificationSettings):
        """Update user notification settings"""
        self.user_settings[user_id] = settings
        
        def _db_upsert():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT OR REPLACE INTO user_settings 
                    (user_id, enabled_channels, enabled_types, quiet_hours_start, 
                     quiet_hours_end, timezone, digest_frequency)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    json.dumps(list(settings.enabled_channels)),
                    json.dumps([t.value for t in settings.enabled_types]),
                    settings.quiet_hours_start,
                    settings.quiet_hours_end,
                    settings.timezone,
                    settings.digest_frequency
                ))
                conn.commit()
                conn.close()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _db_upsert)
    
    def _is_quiet_hours(self, settings: NotificationSettings) -> bool:
        """Check if current time is within user's quiet hours"""
        # Simplified - in production would handle timezone properly
        current_hour = int((time.time() % 86400) // 3600)
        
        if settings.quiet_hours_start <= settings.quiet_hours_end:
            return settings.quiet_hours_start <= current_hour < settings.quiet_hours_end
        else:
            # Overnight quiet hours (e.g., 22:00 to 08:00)
            return current_hour >= settings.quiet_hours_start or current_hour < settings.quiet_hours_end
    
    async def _cleanup_expired(self):
        """Background task to clean up expired notifications"""
        while True:
            try:
                current_time = time.time()
                
                def _db_cleanup():
                    with self.db_lock:
                        conn = sqlite3.connect(self.db_path)
                        # Delete notifications older than 30 days
                        cutoff = current_time - (30 * 86400)
                        conn.execute("""
                            DELETE FROM notifications 
                            WHERE created_at < ? OR expires_at < ?
                        """, (cutoff, current_time))
                        
                        deleted = conn.total_changes
                        conn.commit()
                        conn.close()
                        return deleted
                
                loop = asyncio.get_event_loop()
                deleted = await loop.run_in_executor(None, _db_cleanup)
                
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} expired notifications")
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification queue statistics"""
        return {
            **self.stats,
            "pending_notifications": len(self.pending_queue),
            "priority_queue_lengths": {
                priority.name: len(queue) 
                for priority, queue in self.priority_queues.items()
            },
            "users_with_notifications": len(self.user_queues),
            "registered_channels": list(self.delivery_handlers.keys())
        }

# Example delivery handlers
async def push_notification_handler(notification: Notification) -> bool:
    """Example push notification handler"""
    # In production, integrate with Firebase, APNs, etc.
    logger.info(f"PUSH: {notification.title} -> {notification.user_id}")
    return True

async def email_notification_handler(notification: Notification) -> bool:
    """Example email notification handler"""
    # In production, integrate with email service
    logger.info(f"EMAIL: {notification.title} -> {notification.user_id}")
    return True

async def in_app_notification_handler(notification: Notification) -> bool:
    """Example in-app notification handler"""
    # This would typically send via WebSocket
    logger.info(f"IN_APP: {notification.title} -> {notification.user_id}")
    return True