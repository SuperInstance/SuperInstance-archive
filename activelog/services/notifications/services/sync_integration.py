"""
Sync Engine Integration - Handles notifications for sync conflicts and events
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import aiohttp

from ..core.config import settings
from ..core.database import DatabaseManager
from ..core.logging import logger

class SyncIntegration:
    """Integrates with sync engine to send conflict and sync event notifications"""
    
    def __init__(self, db_manager: DatabaseManager, notification_service=None):
        self.db_manager = db_manager
        self.notification_service = notification_service
        
        # HTTP session for API calls
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Statistics
        self.stats = {
            "sync_notifications_sent": 0,
            "conflict_alerts_sent": 0,
            "sync_complete_notifications": 0,
            "api_calls_made": 0,
            "api_errors": 0,
            "service_start": datetime.now()
        }
        
        logger.info("Sync integration service initialized")
    
    async def _ensure_session(self):
        """Ensure HTTP session is available"""
        if not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def handle_sync_conflict(self,
                                  user_id: str,
                                  tenant_id: Optional[str],
                                  conflict_data: Dict[str, Any]) -> bool:
        """Handle sync conflict notification"""
        try:
            # Extract conflict information
            filename = conflict_data.get("filename", "Unknown file")
            filepath = conflict_data.get("filepath", "")
            conflict_type = conflict_data.get("conflict_type", "modification")
            last_modified = conflict_data.get("last_modified")
            conflicting_version = conflict_data.get("conflicting_version")
            resolution_url = conflict_data.get("resolution_url")
            
            # Prepare notification data
            notification_data = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "notification_type": "sync_conflict",
                "title": f"Sync conflict detected - {filename}",
                "message": f"A sync conflict has been detected for {filename}. Please review and resolve.",
                "data": {
                    "filename": filename,
                    "filepath": filepath,
                    "conflict_type": conflict_type,
                    "last_modified": last_modified,
                    "conflicting_version": conflicting_version,
                    "resolution_url": resolution_url
                },
                "priority": 4,  # High priority
                "template_vars": {
                    "filename": filename,
                    "filepath": filepath,
                    "conflict_type": conflict_type,
                    "last_modified": last_modified,
                    "conflicting_version": conflicting_version,
                    "resolution_url": resolution_url
                }
            }
            
            # Send notification through all enabled channels
            success = await self._send_multi_channel_notification(notification_data)
            
            if success:
                self.stats["conflict_alerts_sent"] += 1
                logger.info(f"Sent sync conflict notification for user {user_id}: {filename}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error handling sync conflict: {e}")
            return False
    
    async def handle_sync_complete(self,
                                  user_id: str,
                                  tenant_id: Optional[str],
                                  sync_data: Dict[str, Any]) -> bool:
        """Handle sync completion notification"""
        try:
            # Extract sync information
            files_synced = sync_data.get("files_synced", 0)
            files_uploaded = sync_data.get("files_uploaded", 0)
            files_downloaded = sync_data.get("files_downloaded", 0)
            sync_duration = sync_data.get("sync_duration", "Unknown")
            total_size = sync_data.get("total_size", 0)
            conflicts_resolved = sync_data.get("conflicts_resolved", 0)
            
            # Only send notification if significant activity
            if files_synced == 0 and conflicts_resolved == 0:
                return True  # No notification needed for empty sync
            
            # Prepare notification data
            notification_data = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "notification_type": "sync_complete",
                "title": f"Sync completed - {files_synced} files",
                "message": f"Sync completed successfully. {files_synced} files synchronized.",
                "data": {
                    "files_synced": files_synced,
                    "files_uploaded": files_uploaded,
                    "files_downloaded": files_downloaded,
                    "sync_duration": sync_duration,
                    "total_size": total_size,
                    "conflicts_resolved": conflicts_resolved
                },
                "priority": 2,  # Normal priority
                "template_vars": {
                    "files_synced": files_synced,
                    "files_uploaded": files_uploaded,
                    "files_downloaded": files_downloaded,
                    "sync_duration": sync_duration,
                    "total_size": total_size,
                    "conflicts_resolved": conflicts_resolved
                }
            }
            
            # Send notification (typically just in-app for sync completion)
            success = await self._send_multi_channel_notification(
                notification_data,
                channels=["inapp"]  # Usually only in-app for sync completion
            )
            
            if success:
                self.stats["sync_complete_notifications"] += 1
                logger.debug(f"Sent sync complete notification for user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error handling sync complete: {e}")
            return False
    
    async def handle_sync_error(self,
                               user_id: str,
                               tenant_id: Optional[str],
                               error_data: Dict[str, Any]) -> bool:
        """Handle sync error notification"""
        try:
            # Extract error information
            error_type = error_data.get("error_type", "Unknown error")
            error_message = error_data.get("error_message", "")
            affected_files = error_data.get("affected_files", [])
            retry_possible = error_data.get("retry_possible", True)
            
            # Prepare notification data
            notification_data = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "notification_type": "sync_error",
                "title": f"Sync error: {error_type}",
                "message": f"Sync encountered an error: {error_message}",
                "data": {
                    "error_type": error_type,
                    "error_message": error_message,
                    "affected_files": affected_files,
                    "retry_possible": retry_possible
                },
                "priority": 3,  # High priority for errors
                "template_vars": {
                    "error_type": error_type,
                    "error_message": error_message,
                    "affected_files_count": len(affected_files),
                    "retry_possible": retry_possible
                }
            }
            
            # Send notification
            success = await self._send_multi_channel_notification(notification_data)
            
            if success:
                self.stats["sync_notifications_sent"] += 1
                logger.info(f"Sent sync error notification for user {user_id}: {error_type}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error handling sync error: {e}")
            return False
    
    async def handle_quota_warning(self,
                                  user_id: str,
                                  tenant_id: Optional[str],
                                  quota_data: Dict[str, Any]) -> bool:
        """Handle storage quota warning"""
        try:
            # Extract quota information
            usage_percentage = quota_data.get("usage_percentage", 0)
            used_storage = quota_data.get("used_storage", 0)
            total_storage = quota_data.get("total_storage", 0)
            available_storage = total_storage - used_storage
            upgrade_url = quota_data.get("upgrade_url")
            
            # Determine notification urgency based on usage
            if usage_percentage >= 95:
                priority = 5  # Critical
                notification_type = "quota_exceeded"
                title = "Storage quota exceeded"
            elif usage_percentage >= 90:
                priority = 4  # High
                notification_type = "quota_warning"
                title = f"Storage quota warning - {usage_percentage}% used"
            else:
                priority = 3  # Medium
                notification_type = "quota_warning"
                title = f"Storage quota warning - {usage_percentage}% used"
            
            # Prepare notification data
            notification_data = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "notification_type": notification_type,
                "title": title,
                "message": f"Your storage is {usage_percentage}% full. Consider upgrading your plan.",
                "data": {
                    "usage_percentage": usage_percentage,
                    "used_storage": used_storage,
                    "total_storage": total_storage,
                    "available_storage": available_storage,
                    "upgrade_url": upgrade_url
                },
                "priority": priority,
                "template_vars": {
                    "usage_percentage": usage_percentage,
                    "used_storage": used_storage,
                    "total_storage": total_storage,
                    "available_storage": available_storage,
                    "upgrade_url": upgrade_url
                }
            }
            
            # Send notification
            success = await self._send_multi_channel_notification(notification_data)
            
            if success:
                self.stats["sync_notifications_sent"] += 1
                logger.info(f"Sent quota warning for user {user_id}: {usage_percentage}%")
            
            return success
            
        except Exception as e:
            logger.error(f"Error handling quota warning: {e}")
            return False
    
    async def _send_multi_channel_notification(self,
                                              notification_data: Dict[str, Any],
                                              channels: Optional[List[str]] = None) -> bool:
        """Send notification through multiple channels based on user preferences"""
        try:
            if not self.notification_service:
                logger.warning("Notification service not available")
                return False
            
            user_id = notification_data["user_id"]
            tenant_id = notification_data.get("tenant_id")
            notification_type = notification_data["notification_type"]
            
            # Get user's enabled channels if not specified
            if not channels:
                from main import preference_service
                if preference_service:
                    channels = await preference_service.get_notification_channels(user_id, notification_type)
                else:
                    channels = ["inapp"]  # Default to in-app only
            
            results = []
            
            # Send in-app notification
            if "inapp" in channels:
                from api.websocket import send_notification_to_user
                
                inapp_result = await send_notification_to_user(
                    user_id=user_id,
                    notification_type=notification_type,
                    title=notification_data["title"],
                    message=notification_data["message"],
                    data=notification_data.get("data", {}),
                    priority=notification_data.get("priority", 2),
                    tenant_id=tenant_id
                )
                results.append(bool(inapp_result))
            
            # Send email notification
            if "email" in channels and self.notification_service.email_service:
                # Get user email
                user_email = await self._get_user_email(user_id)
                if user_email:
                    email_result = await self.notification_service.email_service.send_notification(
                        user_id=user_id,
                        to_email=user_email,
                        subject=notification_data["title"],
                        body=notification_data["message"],
                        tenant_id=tenant_id,
                        template_id=notification_type,
                        template_vars=notification_data.get("template_vars", {})
                    )
                    results.append(email_result)
            
            # Send SMS notification
            if "sms" in channels and self.notification_service.sms_service:
                # Get user phone
                user_phone = await self._get_user_phone(user_id)
                if user_phone:
                    sms_result = await self.notification_service.sms_service.send_notification(
                        user_id=user_id,
                        to_phone=user_phone,
                        message=notification_data["message"],
                        tenant_id=tenant_id,
                        template_id=notification_type,
                        template_vars=notification_data.get("template_vars", {})
                    )
                    results.append(sms_result)
            
            # Send webhook notification
            if "webhook" in channels and self.notification_service.webhook_service:
                webhook_result = await self.notification_service.webhook_service.send_webhooks_to_user_endpoints(
                    user_id=user_id,
                    notification_type=notification_type,
                    payload={
                        "event": notification_type,
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "title": notification_data["title"],
                        "message": notification_data["message"],
                        "data": notification_data.get("data", {}),
                        "timestamp": datetime.now().isoformat()
                    },
                    tenant_id=tenant_id
                )
                results.extend(webhook_result)
            
            # Consider success if any channel succeeded
            return any(results) if results else False
            
        except Exception as e:
            logger.error(f"Error sending multi-channel notification: {e}")
            return False
    
    async def _get_user_email(self, user_id: str) -> Optional[str]:
        """Get user's email address"""
        try:
            # This would typically query the user service
            # For now, we'll use a placeholder
            return f"user{user_id}@example.com"
            
        except Exception as e:
            logger.error(f"Error getting user email: {e}")
            return None
    
    async def _get_user_phone(self, user_id: str) -> Optional[str]:
        """Get user's phone number"""
        try:
            # This would typically query the user service
            # For now, we'll return None (no phone configured)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user phone: {e}")
            return None
    
    async def register_sync_webhook(self, webhook_url: str, secret_key: Optional[str] = None):
        """Register to receive sync events from sync engine"""
        try:
            await self._ensure_session()
            
            # Register webhook with sync engine
            webhook_data = {
                "url": webhook_url,
                "secret_key": secret_key or settings.WEBHOOK_SECRET_KEY,
                "events": [
                    "sync.conflict",
                    "sync.complete",
                    "sync.error",
                    "quota.warning",
                    "quota.exceeded"
                ]
            }
            
            async with self.session.post(
                f"{settings.SYNC_ENGINE_URL}/api/v1/webhooks/register",
                json=webhook_data
            ) as response:
                if response.status == 200:
                    logger.info("Successfully registered sync webhook")
                    return True
                else:
                    logger.error(f"Failed to register sync webhook: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error registering sync webhook: {e}")
            return False
    
    async def handle_sync_webhook(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Handle incoming webhook from sync engine"""
        try:
            user_id = payload.get("user_id")
            tenant_id = payload.get("tenant_id")
            
            if not user_id:
                logger.error("No user_id in sync webhook payload")
                return False
            
            # Route to appropriate handler
            if event_type == "sync.conflict":
                return await self.handle_sync_conflict(user_id, tenant_id, payload)
            elif event_type == "sync.complete":
                return await self.handle_sync_complete(user_id, tenant_id, payload)
            elif event_type == "sync.error":
                return await self.handle_sync_error(user_id, tenant_id, payload)
            elif event_type in ["quota.warning", "quota.exceeded"]:
                return await self.handle_quota_warning(user_id, tenant_id, payload)
            else:
                logger.warning(f"Unknown sync event type: {event_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling sync webhook: {e}")
            return False
    
    async def get_sync_status(self, user_id: str) -> Optional[Dict]:
        """Get current sync status for a user"""
        try:
            await self._ensure_session()
            
            self.stats["api_calls_made"] += 1
            
            async with self.session.get(
                f"{settings.SYNC_ENGINE_URL}/api/v1/sync/status/{user_id}"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.stats["api_errors"] += 1
                    logger.error(f"Failed to get sync status: {response.status}")
                    return None
                    
        except Exception as e:
            self.stats["api_errors"] += 1
            logger.error(f"Error getting sync status: {e}")
            return None
    
    async def trigger_sync(self, user_id: str, sync_type: str = "full") -> bool:
        """Trigger a sync operation for a user"""
        try:
            await self._ensure_session()
            
            self.stats["api_calls_made"] += 1
            
            sync_data = {
                "user_id": user_id,
                "sync_type": sync_type,
                "triggered_by": "notification_service"
            }
            
            async with self.session.post(
                f"{settings.SYNC_ENGINE_URL}/api/v1/sync/trigger",
                json=sync_data
            ) as response:
                if response.status == 200:
                    logger.info(f"Triggered sync for user {user_id}")
                    return True
                else:
                    self.stats["api_errors"] += 1
                    logger.error(f"Failed to trigger sync: {response.status}")
                    return False
                    
        except Exception as e:
            self.stats["api_errors"] += 1
            logger.error(f"Error triggering sync: {e}")
            return False
    
    async def get_stats(self) -> Dict:
        """Get sync integration statistics"""
        stats = self.stats.copy()
        stats["uptime_seconds"] = (datetime.now() - stats["service_start"]).total_seconds()
        return stats
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()