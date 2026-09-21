"""
Push Notification Service for Mobile API
Supports FCM (Android), APNs (iOS), and Web Push
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

# Push notification libraries
try:
    from pyfcm import FCMNotification
except ImportError:
    FCMNotification = None

try:
    import aioapns
    from aioapns import APNs, NotificationRequest, Payload, Alert
except ImportError:
    aioapns = None
    APNs = None

try:
    from pywebpush import webpush, WebPushException
except ImportError:
    webpush = None
    WebPushException = Exception

import aioredis
from ..core.config import settings
from ..core.database import get_database

logger = logging.getLogger(__name__)

class NotificationPriority(Enum):
    MIN = "min"
    LOW = "low" 
    DEFAULT = "default"
    HIGH = "high"
    MAX = "max"

class PushPlatform(Enum):
    FCM = "fcm"         # Firebase Cloud Messaging (Android)
    APNS = "apns"       # Apple Push Notification Service (iOS)
    WEB = "web"         # Web Push Protocol
    UNKNOWN = "unknown"

@dataclass
class PushSubscription:
    user_id: str
    device_id: str
    platform: PushPlatform
    token: str
    endpoint: Optional[str] = None  # For web push
    p256dh_key: Optional[str] = None  # For web push
    auth_key: Optional[str] = None    # For web push
    topics: List[str] = None
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass 
class NotificationPayload:
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    icon: Optional[str] = None
    image: Optional[str] = None
    sound: Optional[str] = None
    badge: Optional[int] = None
    priority: NotificationPriority = NotificationPriority.DEFAULT
    ttl: Optional[int] = None  # Time to live in seconds
    collapse_key: Optional[str] = None  # For Android
    thread_id: Optional[str] = None     # For iOS
    actions: Optional[List[Dict[str, str]]] = None

@dataclass
class NotificationResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    canonical_id: Optional[str] = None  # For token updates
    should_retry: bool = False
    battery_impact: str = "minimal"

class PushNotificationService:
    """
    Mobile-optimized push notification service
    Features:
    - Multi-platform support (FCM, APNs, Web Push)
    - Battery-efficient delivery strategies
    - Automatic retry with exponential backoff
    - Token management and cleanup
    - Analytics and delivery tracking
    """
    
    def __init__(self):
        self.fcm_service = None
        self.apns_service = None
        self.redis_client = None
        self.database = None
        
        # Initialize platform services
        self._init_fcm()
        self._init_apns()
        
        # Notification queues for batching
        self.notification_queue = asyncio.Queue()
        self.batch_size = 100
        self.batch_timeout = 10  # seconds
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delays = [1, 5, 15]  # seconds
        
        # Analytics
        self.delivery_stats = {
            "sent": 0,
            "delivered": 0,
            "failed": 0,
            "retries": 0
        }
    
    def _init_fcm(self):
        """Initialize Firebase Cloud Messaging"""
        if settings.FCM_SERVER_KEY and FCMNotification:
            try:
                self.fcm_service = FCMNotification(api_key=settings.FCM_SERVER_KEY)
                logger.info("FCM service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize FCM: {e}")
        else:
            logger.warning("FCM not available (missing server key or library)")
    
    def _init_apns(self):
        """Initialize Apple Push Notification Service"""
        if all([settings.APNS_KEY_ID, settings.APNS_KEY_FILE, settings.APNS_TEAM_ID]) and aioapns:
            try:
                self.apns_service = APNs(
                    key=settings.APNS_KEY_FILE,
                    key_id=settings.APNS_KEY_ID,
                    team_id=settings.APNS_TEAM_ID,
                    topic="com.activelog.mobile",  # Your app bundle ID
                    use_sandbox=settings.DEBUG
                )
                logger.info("APNs service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize APNs: {e}")
        else:
            logger.warning("APNs not available (missing credentials or library)")
    
    async def initialize(self):
        """Initialize the push notification service"""
        try:
            # Connect to Redis for caching and queues
            self.redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            
            # Connect to database
            self.database = get_database()
            
            # Start background workers
            asyncio.create_task(self._notification_worker())
            asyncio.create_task(self._retry_worker())
            asyncio.create_task(self._cleanup_worker())
            
            logger.info("Push notification service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize push notification service: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup service resources"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            
            if self.apns_service:
                await self.apns_service.close()
                
            logger.info("Push notification service cleaned up")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def subscribe_device(
        self,
        user_id: str,
        device_id: str,
        platform: str,
        token: str,
        endpoint: Optional[str] = None,
        p256dh_key: Optional[str] = None,
        auth_key: Optional[str] = None,
        topics: Optional[List[str]] = None
    ) -> bool:
        """
        Subscribe a device for push notifications
        """
        try:
            platform_enum = PushPlatform(platform.lower())
        except ValueError:
            logger.error(f"Unsupported platform: {platform}")
            return False
        
        subscription = PushSubscription(
            user_id=user_id,
            device_id=device_id,
            platform=platform_enum,
            token=token,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_key=auth_key,
            topics=topics or [],
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            # Store in database
            query = """
                INSERT INTO push_subscriptions 
                (user_id, device_id, platform, token, endpoint, p256dh_key, auth_key, topics, enabled, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (user_id, device_id, platform) 
                DO UPDATE SET 
                    token = EXCLUDED.token,
                    endpoint = EXCLUDED.endpoint,
                    p256dh_key = EXCLUDED.p256dh_key,
                    auth_key = EXCLUDED.auth_key,
                    topics = EXCLUDED.topics,
                    enabled = EXCLUDED.enabled,
                    updated_at = EXCLUDED.updated_at
            """
            
            await self.database.execute(
                query,
                user_id, device_id, platform_enum.value, token, endpoint,
                p256dh_key, auth_key, json.dumps(topics or []), True,
                subscription.created_at, subscription.updated_at
            )
            
            # Cache subscription for quick access
            cache_key = f"push_subscription:{user_id}:{device_id}:{platform_enum.value}"
            await self.redis_client.hset(
                cache_key,
                mapping={
                    "token": token,
                    "endpoint": endpoint or "",
                    "p256dh_key": p256dh_key or "",
                    "auth_key": auth_key or "",
                    "topics": json.dumps(topics or []),
                    "enabled": "true"
                }
            )
            await self.redis_client.expire(cache_key, 3600)  # 1 hour cache
            
            logger.info(f"Device subscribed for push notifications: {device_id} ({platform})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe device: {e}")
            return False
    
    async def unsubscribe_device(
        self,
        user_id: str,
        device_id: str,
        platform: Optional[str] = None
    ) -> bool:
        """Unsubscribe a device from push notifications"""
        
        try:
            if platform:
                # Unsubscribe specific platform
                query = """
                    DELETE FROM push_subscriptions 
                    WHERE user_id = $1 AND device_id = $2 AND platform = $3
                """
                await self.database.execute(query, user_id, device_id, platform)
                
                # Remove from cache
                cache_key = f"push_subscription:{user_id}:{device_id}:{platform}"
                await self.redis_client.delete(cache_key)
                
            else:
                # Unsubscribe all platforms for device
                query = """
                    DELETE FROM push_subscriptions 
                    WHERE user_id = $1 AND device_id = $2
                """
                await self.database.execute(query, user_id, device_id)
                
                # Remove all cache entries for device
                pattern = f"push_subscription:{user_id}:{device_id}:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            
            logger.info(f"Device unsubscribed: {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe device: {e}")
            return False
    
    async def send_notification(
        self,
        user_id: str,
        notification: NotificationPayload,
        device_id: Optional[str] = None,
        topic: Optional[str] = None
    ) -> List[NotificationResult]:
        """
        Send push notification to user's devices
        """
        
        try:
            # Get subscriptions
            subscriptions = await self._get_subscriptions(user_id, device_id, topic)
            
            if not subscriptions:
                logger.warning(f"No push subscriptions found for user {user_id}")
                return []
            
            # Send to all subscriptions
            results = []
            for subscription in subscriptions:
                result = await self._send_to_subscription(subscription, notification)
                results.append(result)
                
                # Update delivery statistics
                if result.success:
                    self.delivery_stats["delivered"] += 1
                else:
                    self.delivery_stats["failed"] += 1
                    
                    # Queue for retry if appropriate
                    if result.should_retry:
                        await self._queue_for_retry(subscription, notification)
            
            self.delivery_stats["sent"] += len(results)
            return results
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return [NotificationResult(
                success=False,
                error=str(e),
                battery_impact="minimal"
            )]
    
    async def send_batch_notifications(
        self,
        notifications: List[Dict[str, Any]]
    ) -> List[NotificationResult]:
        """
        Send multiple notifications in batch for efficiency
        """
        
        results = []
        
        # Group notifications by platform for efficient delivery
        platform_groups = {}
        for notif_data in notifications:
            user_id = notif_data["user_id"]
            notification = NotificationPayload(**notif_data["notification"])
            device_id = notif_data.get("device_id")
            topic = notif_data.get("topic")
            
            subscriptions = await self._get_subscriptions(user_id, device_id, topic)
            
            for subscription in subscriptions:
                platform = subscription.platform.value
                if platform not in platform_groups:
                    platform_groups[platform] = []
                
                platform_groups[platform].append((subscription, notification))
        
        # Send to each platform group
        for platform, subscription_notifications in platform_groups.items():
            platform_results = await self._send_batch_to_platform(
                platform, subscription_notifications
            )
            results.extend(platform_results)
        
        return results
    
    async def get_delivery_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get push notification delivery statistics"""
        
        try:
            if user_id:
                # User-specific statistics
                query = """
                    SELECT 
                        COUNT(*) as total_sent,
                        COUNT(CASE WHEN delivered_at IS NOT NULL THEN 1 END) as delivered,
                        COUNT(CASE WHEN failed_at IS NOT NULL THEN 1 END) as failed,
                        AVG(CASE WHEN delivered_at IS NOT NULL THEN 
                            EXTRACT(EPOCH FROM delivered_at - created_at) END) as avg_delivery_time
                    FROM push_notification_logs 
                    WHERE user_id = $1 
                    AND created_at >= NOW() - INTERVAL '24 hours'
                """
                
                row = await self.database.fetch_one(query, user_id)
                return dict(row) if row else {}
            
            else:
                # Global statistics
                return {
                    **self.delivery_stats,
                    "queue_size": self.notification_queue.qsize(),
                    "active_subscriptions": await self._count_active_subscriptions()
                }
                
        except Exception as e:
            logger.error(f"Failed to get delivery statistics: {e}")
            return {}
    
    async def _get_subscriptions(
        self,
        user_id: str,
        device_id: Optional[str] = None,
        topic: Optional[str] = None
    ) -> List[PushSubscription]:
        """Get push subscriptions for user/device/topic"""
        
        try:
            # Try cache first
            if device_id:
                cache_pattern = f"push_subscription:{user_id}:{device_id}:*"
                cached_keys = await self.redis_client.keys(cache_pattern)
                
                if cached_keys:
                    subscriptions = []
                    for key in cached_keys:
                        cached_data = await self.redis_client.hgetall(key)
                        if cached_data and cached_data.get("enabled") == "true":
                            platform = key.split(":")[-1]
                            subscription = PushSubscription(
                                user_id=user_id,
                                device_id=device_id,
                                platform=PushPlatform(platform),
                                token=cached_data["token"],
                                endpoint=cached_data.get("endpoint") or None,
                                p256dh_key=cached_data.get("p256dh_key") or None,
                                auth_key=cached_data.get("auth_key") or None,
                                topics=json.loads(cached_data.get("topics", "[]"))
                            )
                            subscriptions.append(subscription)
                    
                    if subscriptions:
                        return subscriptions
            
            # Query database
            where_clause = "WHERE user_id = $1 AND enabled = true"
            params = [user_id]
            
            if device_id:
                where_clause += " AND device_id = $2"
                params.append(device_id)
            
            if topic:
                where_clause += f" AND topics::jsonb ? ${len(params) + 1}"
                params.append(topic)
            
            query = f"""
                SELECT user_id, device_id, platform, token, endpoint, 
                       p256dh_key, auth_key, topics, enabled, created_at, updated_at
                FROM push_subscriptions 
                {where_clause}
                ORDER BY updated_at DESC
            """
            
            rows = await self.database.fetch_all(query, *params)
            
            subscriptions = []
            for row in rows:
                subscription = PushSubscription(
                    user_id=row["user_id"],
                    device_id=row["device_id"],
                    platform=PushPlatform(row["platform"]),
                    token=row["token"],
                    endpoint=row["endpoint"],
                    p256dh_key=row["p256dh_key"],
                    auth_key=row["auth_key"],
                    topics=json.loads(row["topics"] or "[]"),
                    enabled=row["enabled"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                subscriptions.append(subscription)
            
            return subscriptions
            
        except Exception as e:
            logger.error(f"Failed to get subscriptions: {e}")
            return []
    
    async def _send_to_subscription(
        self,
        subscription: PushSubscription,
        notification: NotificationPayload
    ) -> NotificationResult:
        """Send notification to a specific subscription"""
        
        try:
            if subscription.platform == PushPlatform.FCM:
                return await self._send_fcm(subscription, notification)
            elif subscription.platform == PushPlatform.APNS:
                return await self._send_apns(subscription, notification)
            elif subscription.platform == PushPlatform.WEB:
                return await self._send_web_push(subscription, notification)
            else:
                return NotificationResult(
                    success=False,
                    error=f"Unsupported platform: {subscription.platform}",
                    battery_impact="minimal"
                )
                
        except Exception as e:
            logger.error(f"Failed to send to subscription: {e}")
            return NotificationResult(
                success=False,
                error=str(e),
                should_retry=True,
                battery_impact="minimal"
            )
    
    async def _send_fcm(
        self,
        subscription: PushSubscription,
        notification: NotificationPayload
    ) -> NotificationResult:
        """Send FCM notification"""
        
        if not self.fcm_service:
            return NotificationResult(
                success=False,
                error="FCM service not available",
                battery_impact="minimal"
            )
        
        try:
            # Build FCM message
            fcm_data = notification.data or {}
            fcm_data.update({
                "battery_impact": "minimal",
                "timestamp": str(int(datetime.utcnow().timestamp()))
            })
            
            # Send notification
            result = self.fcm_service.notify_single_device(
                registration_id=subscription.token,
                message_title=notification.title,
                message_body=notification.body,
                data_message=fcm_data,
                sound=notification.sound,
                collapse_key=notification.collapse_key,
                time_to_live=notification.ttl or 3600,
                priority=notification.priority.value
            )
            
            if result.get("success"):
                return NotificationResult(
                    success=True,
                    message_id=result.get("message_id"),
                    canonical_id=result.get("canonical_id"),
                    battery_impact="minimal"
                )
            else:
                error = result.get("failure") or "Unknown FCM error"
                should_retry = "InvalidRegistration" not in str(error)
                
                return NotificationResult(
                    success=False,
                    error=str(error),
                    should_retry=should_retry,
                    battery_impact="minimal"
                )
                
        except Exception as e:
            return NotificationResult(
                success=False,
                error=str(e),
                should_retry=True,
                battery_impact="minimal"
            )
    
    async def _send_apns(
        self,
        subscription: PushSubscription,
        notification: NotificationPayload
    ) -> NotificationResult:
        """Send APNs notification"""
        
        if not self.apns_service:
            return NotificationResult(
                success=False,
                error="APNs service not available",
                battery_impact="minimal"
            )
        
        try:
            # Build APNs payload
            alert = Alert(
                title=notification.title,
                body=notification.body
            )
            
            payload = Payload(
                alert=alert,
                sound=notification.sound or "default",
                badge=notification.badge,
                custom=notification.data or {}
            )
            
            # Add mobile-specific data
            payload.custom.update({
                "battery_impact": "minimal",
                "timestamp": int(datetime.utcnow().timestamp())
            })
            
            # Create notification request
            request = NotificationRequest(
                device_token=subscription.token,
                message=payload,
                time_to_live=notification.ttl or 3600,
                priority=10 if notification.priority == NotificationPriority.HIGH else 5,
                thread_id=notification.thread_id
            )
            
            # Send notification
            response = await self.apns_service.send_notification(request)
            
            if response.is_successful:
                return NotificationResult(
                    success=True,
                    message_id=response.id,
                    battery_impact="minimal"
                )
            else:
                should_retry = response.status not in ["400", "410"]
                
                return NotificationResult(
                    success=False,
                    error=response.description,
                    should_retry=should_retry,
                    battery_impact="minimal"
                )
                
        except Exception as e:
            return NotificationResult(
                success=False,
                error=str(e),
                should_retry=True,
                battery_impact="minimal"
            )
    
    async def _send_web_push(
        self,
        subscription: PushSubscription,
        notification: NotificationPayload
    ) -> NotificationResult:
        """Send Web Push notification"""
        
        if not webpush:
            return NotificationResult(
                success=False,
                error="Web Push library not available",
                battery_impact="minimal"
            )
        
        if not all([subscription.endpoint, subscription.p256dh_key, subscription.auth_key]):
            return NotificationResult(
                success=False,
                error="Missing Web Push subscription data",
                battery_impact="minimal"
            )
        
        try:
            # Build web push payload
            payload_data = {
                "title": notification.title,
                "body": notification.body,
                "icon": notification.icon,
                "image": notification.image,
                "data": notification.data or {},
                "actions": notification.actions or [],
                "battery_impact": "minimal",
                "timestamp": int(datetime.utcnow().timestamp())
            }
            
            subscription_info = {
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key
                }
            }
            
            # Send web push
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload_data),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": f"mailto:{settings.VAPID_EMAIL}"
                },
                ttl=notification.ttl or 3600
            )
            
            return NotificationResult(
                success=True,
                battery_impact="minimal"
            )
            
        except WebPushException as e:
            should_retry = e.response.status_code not in [400, 410, 413]
            
            return NotificationResult(
                success=False,
                error=str(e),
                should_retry=should_retry,
                battery_impact="minimal"
            )
        except Exception as e:
            return NotificationResult(
                success=False,
                error=str(e),
                should_retry=True,
                battery_impact="minimal"
            )
    
    async def _send_batch_to_platform(
        self,
        platform: str,
        subscription_notifications: List[tuple]
    ) -> List[NotificationResult]:
        """Send batch notifications to a specific platform"""
        
        results = []
        
        # For now, send individually
        # TODO: Implement true batch sending for platforms that support it
        for subscription, notification in subscription_notifications:
            result = await self._send_to_subscription(subscription, notification)
            results.append(result)
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.01)
        
        return results
    
    async def _queue_for_retry(
        self,
        subscription: PushSubscription,
        notification: NotificationPayload,
        attempt: int = 0
    ):
        """Queue failed notification for retry"""
        
        if attempt >= self.max_retries:
            logger.warning(f"Max retries exceeded for notification to {subscription.device_id}")
            return
        
        retry_data = {
            "subscription": {
                "user_id": subscription.user_id,
                "device_id": subscription.device_id,
                "platform": subscription.platform.value,
                "token": subscription.token,
                "endpoint": subscription.endpoint,
                "p256dh_key": subscription.p256dh_key,
                "auth_key": subscription.auth_key
            },
            "notification": {
                "title": notification.title,
                "body": notification.body,
                "data": notification.data,
                "icon": notification.icon,
                "image": notification.image,
                "sound": notification.sound,
                "badge": notification.badge,
                "priority": notification.priority.value,
                "ttl": notification.ttl,
                "collapse_key": notification.collapse_key,
                "thread_id": notification.thread_id,
                "actions": notification.actions
            },
            "attempt": attempt + 1,
            "retry_at": datetime.utcnow() + timedelta(seconds=self.retry_delays[attempt])
        }
        
        # Add to retry queue
        await self.redis_client.lpush(
            "push_notification_retries",
            json.dumps(retry_data, default=str)
        )
    
    async def _notification_worker(self):
        """Background worker for processing notification queue"""
        
        while True:
            try:
                notifications = []
                
                # Collect notifications for batch processing
                try:
                    # Wait for first notification
                    notification = await asyncio.wait_for(
                        self.notification_queue.get(), timeout=self.batch_timeout
                    )
                    notifications.append(notification)
                    
                    # Collect additional notifications up to batch size
                    for _ in range(self.batch_size - 1):
                        try:
                            notification = await asyncio.wait_for(
                                self.notification_queue.get(), timeout=0.1
                            )
                            notifications.append(notification)
                        except asyncio.TimeoutError:
                            break
                
                except asyncio.TimeoutError:
                    # No notifications in queue
                    continue
                
                # Process batch
                if notifications:
                    await self.send_batch_notifications(notifications)
                
            except Exception as e:
                logger.error(f"Error in notification worker: {e}")
                await asyncio.sleep(1)
    
    async def _retry_worker(self):
        """Background worker for processing retry queue"""
        
        while True:
            try:
                # Check retry queue
                retry_data = await self.redis_client.brpop("push_notification_retries", timeout=60)
                
                if not retry_data:
                    continue
                
                retry_info = json.loads(retry_data[1])
                retry_at = datetime.fromisoformat(retry_info["retry_at"])
                
                # Check if it's time to retry
                if datetime.utcnow() < retry_at:
                    # Put back in queue
                    await self.redis_client.lpush(
                        "push_notification_retries",
                        retry_data[1]
                    )
                    await asyncio.sleep(1)
                    continue
                
                # Recreate subscription and notification objects
                sub_data = retry_info["subscription"]
                subscription = PushSubscription(
                    user_id=sub_data["user_id"],
                    device_id=sub_data["device_id"],
                    platform=PushPlatform(sub_data["platform"]),
                    token=sub_data["token"],
                    endpoint=sub_data.get("endpoint"),
                    p256dh_key=sub_data.get("p256dh_key"),
                    auth_key=sub_data.get("auth_key")
                )
                
                notif_data = retry_info["notification"]
                notification = NotificationPayload(
                    title=notif_data["title"],
                    body=notif_data["body"],
                    data=notif_data.get("data"),
                    icon=notif_data.get("icon"),
                    image=notif_data.get("image"),
                    sound=notif_data.get("sound"),
                    badge=notif_data.get("badge"),
                    priority=NotificationPriority(notif_data.get("priority", "default")),
                    ttl=notif_data.get("ttl"),
                    collapse_key=notif_data.get("collapse_key"),
                    thread_id=notif_data.get("thread_id"),
                    actions=notif_data.get("actions")
                )
                
                # Retry sending
                result = await self._send_to_subscription(subscription, notification)
                
                if not result.success and result.should_retry:
                    # Queue for another retry
                    await self._queue_for_retry(
                        subscription, notification, retry_info["attempt"]
                    )
                
                self.delivery_stats["retries"] += 1
                
            except Exception as e:
                logger.error(f"Error in retry worker: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_worker(self):
        """Background worker for cleanup tasks"""
        
        while True:
            try:
                # Clean up expired subscriptions
                await self._cleanup_expired_subscriptions()
                
                # Clean up old notification logs
                await self._cleanup_old_logs()
                
                # Clean up retry queue
                await self._cleanup_retry_queue()
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                await asyncio.sleep(300)  # 5 minutes
    
    async def _cleanup_expired_subscriptions(self):
        """Remove expired push subscriptions"""
        
        try:
            # Remove subscriptions not updated in 30 days
            query = """
                DELETE FROM push_subscriptions 
                WHERE updated_at < NOW() - INTERVAL '30 days'
            """
            
            result = await self.database.execute(query)
            if result:
                logger.info(f"Cleaned up {result} expired subscriptions")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired subscriptions: {e}")
    
    async def _cleanup_old_logs(self):
        """Remove old notification logs"""
        
        try:
            # Remove logs older than 7 days
            query = """
                DELETE FROM push_notification_logs 
                WHERE created_at < NOW() - INTERVAL '7 days'
            """
            
            result = await self.database.execute(query)
            if result:
                logger.info(f"Cleaned up {result} old notification logs")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
    
    async def _cleanup_retry_queue(self):
        """Clean up old retry queue entries"""
        
        try:
            # Get all retry entries
            retry_entries = await self.redis_client.lrange("push_notification_retries", 0, -1)
            
            valid_entries = []
            for entry in retry_entries:
                try:
                    retry_info = json.loads(entry)
                    retry_at = datetime.fromisoformat(retry_info["retry_at"])
                    
                    # Keep entries that are not too old (older than 24 hours)
                    if datetime.utcnow() - retry_at < timedelta(hours=24):
                        valid_entries.append(entry)
                        
                except Exception:
                    # Skip invalid entries
                    continue
            
            # Replace queue with valid entries
            if len(valid_entries) != len(retry_entries):
                await self.redis_client.delete("push_notification_retries")
                if valid_entries:
                    await self.redis_client.lpush("push_notification_retries", *valid_entries)
                
                cleaned = len(retry_entries) - len(valid_entries)
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} old retry entries")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup retry queue: {e}")
    
    async def _count_active_subscriptions(self) -> int:
        """Count active push subscriptions"""
        
        try:
            query = "SELECT COUNT(*) FROM push_subscriptions WHERE enabled = true"
            result = await self.database.fetch_val(query)
            return result or 0
            
        except Exception as e:
            logger.error(f"Failed to count active subscriptions: {e}")
            return 0