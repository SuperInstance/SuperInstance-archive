"""
Preference Service - Manages user notification preferences
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Any
import json

from core.config import settings
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class PreferenceService:
    """Manages user notification preferences and settings"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
        # Preference cache
        self.preference_cache: Dict[str, Dict] = {}
        self.cache_expiry = {}
        
        # Statistics
        self.stats = {
            "preferences_updated": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "service_start": datetime.now()
        }
        
        logger.info("Preference service initialized")
    
    async def get_user_preferences(self, 
                                  user_id: str,
                                  notification_type: Optional[str] = None) -> Dict[str, Any]:
        """Get user's notification preferences"""
        try:
            # Check cache first
            cache_key = f"{user_id}_{notification_type or 'all'}"
            if cache_key in self.preference_cache:
                cache_time = self.cache_expiry.get(cache_key, datetime.min)
                if (datetime.now() - cache_time).total_seconds() < 300:  # 5 minute cache
                    self.stats["cache_hits"] += 1
                    return self.preference_cache[cache_key]
            
            # Query database
            if notification_type:
                prefs = await self.db_manager.execute_query("""
                    SELECT * FROM notification_preferences 
                    WHERE user_id = $1 AND notification_type = $2
                """, user_id, notification_type)
            else:
                prefs = await self.db_manager.execute_query("""
                    SELECT * FROM notification_preferences 
                    WHERE user_id = $1
                """, user_id)
            
            # If no preferences found, create defaults
            if not prefs:
                if notification_type:
                    await self._create_default_preference(user_id, notification_type)
                    prefs = await self.db_manager.execute_query("""
                        SELECT * FROM notification_preferences 
                        WHERE user_id = $1 AND notification_type = $2
                    """, user_id, notification_type)
                else:
                    # Create defaults for all notification types
                    await self._create_all_default_preferences(user_id)
                    prefs = await self.db_manager.execute_query("""
                        SELECT * FROM notification_preferences 
                        WHERE user_id = $1
                    """, user_id)
            
            # Format preferences
            if notification_type:
                result = prefs[0] if prefs else self._get_default_preferences(notification_type)
            else:
                result = {pref["notification_type"]: pref for pref in prefs}
            
            # Cache the result
            self.preference_cache[cache_key] = result
            self.cache_expiry[cache_key] = datetime.now()
            self.stats["cache_misses"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return self._get_default_preferences(notification_type) if notification_type else {}
    
    async def update_user_preferences(self,
                                     user_id: str,
                                     notification_type: str,
                                     email_enabled: Optional[bool] = None,
                                     inapp_enabled: Optional[bool] = None,
                                     sms_enabled: Optional[bool] = None,
                                     webhook_enabled: Optional[bool] = None,
                                     digest_frequency: Optional[str] = None,
                                     quiet_hours_start: Optional[time] = None,
                                     quiet_hours_end: Optional[time] = None,
                                     timezone: Optional[str] = None,
                                     tenant_id: Optional[str] = None) -> bool:
        """Update user's notification preferences"""
        try:
            # Check if preference exists
            exists = await self.db_manager.execute_scalar("""
                SELECT EXISTS(SELECT 1 FROM notification_preferences 
                WHERE user_id = $1 AND notification_type = $2)
            """, user_id, notification_type)
            
            if exists:
                # Update existing preference
                updates = []
                params = []
                param_count = 0
                
                for field, value in [
                    ("email_enabled", email_enabled),
                    ("inapp_enabled", inapp_enabled),
                    ("sms_enabled", sms_enabled),
                    ("webhook_enabled", webhook_enabled),
                    ("digest_frequency", digest_frequency),
                    ("quiet_hours_start", quiet_hours_start),
                    ("quiet_hours_end", quiet_hours_end),
                    ("timezone", timezone)
                ]:
                    if value is not None:
                        param_count += 1
                        updates.append(f"{field} = ${param_count}")
                        params.append(value)
                
                if updates:
                    param_count += 1
                    params.append(user_id)
                    param_count += 1
                    params.append(notification_type)
                    
                    updates.append("updated_at = NOW()")
                    
                    await self.db_manager.execute_command(f"""
                        UPDATE notification_preferences 
                        SET {', '.join(updates)}
                        WHERE user_id = ${param_count - 1} AND notification_type = ${param_count}
                    """, *params)
            else:
                # Create new preference
                await self.db_manager.execute_command("""
                    INSERT INTO notification_preferences (
                        user_id, tenant_id, notification_type, email_enabled, inapp_enabled,
                        sms_enabled, webhook_enabled, digest_frequency, quiet_hours_start,
                        quiet_hours_end, timezone
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """, 
                    user_id, tenant_id, notification_type,
                    email_enabled if email_enabled is not None else settings.DEFAULT_EMAIL_ENABLED,
                    inapp_enabled if inapp_enabled is not None else settings.DEFAULT_INAPP_ENABLED,
                    sms_enabled if sms_enabled is not None else settings.DEFAULT_SMS_ENABLED,
                    webhook_enabled if webhook_enabled is not None else settings.DEFAULT_WEBHOOK_ENABLED,
                    digest_frequency or "daily",
                    quiet_hours_start,
                    quiet_hours_end,
                    timezone or "UTC"
                )
            
            # Clear cache
            self._clear_user_cache(user_id)
            
            self.stats["preferences_updated"] += 1
            logger.debug(f"Updated preferences for user {user_id}, type {notification_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            return False
    
    async def update_bulk_preferences(self,
                                     user_id: str,
                                     preferences: Dict[str, Dict[str, Any]],
                                     tenant_id: Optional[str] = None) -> bool:
        """Update multiple notification type preferences at once"""
        try:
            success_count = 0
            
            for notification_type, prefs in preferences.items():
                success = await self.update_user_preferences(
                    user_id=user_id,
                    notification_type=notification_type,
                    tenant_id=tenant_id,
                    **prefs
                )
                if success:
                    success_count += 1
            
            return success_count == len(preferences)
            
        except Exception as e:
            logger.error(f"Error updating bulk preferences: {e}")
            return False
    
    async def should_send_notification(self,
                                      user_id: str,
                                      notification_type: str,
                                      channel: str,
                                      tenant_id: Optional[str] = None) -> bool:
        """Check if notification should be sent based on user preferences"""
        try:
            # Get user preferences
            prefs = await self.get_user_preferences(user_id, notification_type)
            
            if not prefs:
                # Use defaults if no preferences found
                prefs = self._get_default_preferences(notification_type)
            
            # Check channel-specific setting
            channel_enabled = prefs.get(f"{channel}_enabled", False)
            if not channel_enabled:
                return False
            
            # Check quiet hours (for non-urgent notifications)
            if channel in ["email", "sms"] and not self._is_urgent_notification(notification_type):
                if not await self._is_outside_quiet_hours(user_id, prefs):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking notification permissions: {e}")
            return False  # Fail safe - don't send if we can't determine
    
    async def get_digest_users(self, frequency: str) -> List[Dict[str, str]]:
        """Get users who should receive digest notifications"""
        try:
            users = await self.db_manager.execute_query("""
                SELECT DISTINCT user_id, tenant_id, timezone
                FROM notification_preferences 
                WHERE digest_frequency = $1 AND email_enabled = TRUE
            """, frequency)
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting digest users: {e}")
            return []
    
    async def get_notification_channels(self, user_id: str, notification_type: str) -> List[str]:
        """Get enabled notification channels for a user and notification type"""
        try:
            prefs = await self.get_user_preferences(user_id, notification_type)
            
            if not prefs:
                prefs = self._get_default_preferences(notification_type)
            
            channels = []
            
            if prefs.get("email_enabled", False):
                channels.append("email")
            if prefs.get("inapp_enabled", False):
                channels.append("inapp")
            if prefs.get("sms_enabled", False):
                channels.append("sms")
            if prefs.get("webhook_enabled", False):
                channels.append("webhook")
            
            return channels
            
        except Exception as e:
            logger.error(f"Error getting notification channels: {e}")
            return []
    
    async def _create_default_preference(self, user_id: str, notification_type: str):
        """Create default preference for a user and notification type"""
        try:
            await self.db_manager.execute_command("""
                INSERT INTO notification_preferences (
                    user_id, notification_type, email_enabled, inapp_enabled,
                    sms_enabled, webhook_enabled, digest_frequency, timezone
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (user_id, notification_type) DO NOTHING
            """, 
                user_id, notification_type,
                settings.DEFAULT_EMAIL_ENABLED,
                settings.DEFAULT_INAPP_ENABLED,
                settings.DEFAULT_SMS_ENABLED,
                settings.DEFAULT_WEBHOOK_ENABLED,
                "daily",
                "UTC"
            )
            
        except Exception as e:
            logger.error(f"Error creating default preference: {e}")
    
    async def _create_all_default_preferences(self, user_id: str):
        """Create default preferences for all notification types"""
        try:
            notification_types = list(settings.NOTIFICATION_TYPES.keys())
            
            for notification_type in notification_types:
                await self._create_default_preference(user_id, notification_type)
                
        except Exception as e:
            logger.error(f"Error creating all default preferences: {e}")
    
    def _get_default_preferences(self, notification_type: Optional[str] = None) -> Dict[str, Any]:
        """Get default preferences structure"""
        defaults = {
            "email_enabled": settings.DEFAULT_EMAIL_ENABLED,
            "inapp_enabled": settings.DEFAULT_INAPP_ENABLED,
            "sms_enabled": settings.DEFAULT_SMS_ENABLED,
            "webhook_enabled": settings.DEFAULT_WEBHOOK_ENABLED,
            "digest_frequency": "daily",
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "timezone": "UTC"
        }
        
        if notification_type:
            defaults["notification_type"] = notification_type
        
        return defaults
    
    async def _is_outside_quiet_hours(self, user_id: str, prefs: Dict[str, Any]) -> bool:
        """Check if current time is outside user's quiet hours"""
        try:
            quiet_start = prefs.get("quiet_hours_start")
            quiet_end = prefs.get("quiet_hours_end")
            user_timezone = prefs.get("timezone", "UTC")
            
            if not quiet_start or not quiet_end:
                return True  # No quiet hours set
            
            # For simplicity, we'll use UTC time
            # In production, you'd want to properly handle timezone conversion
            current_time = datetime.now().time()
            
            # Convert string times to time objects if needed
            if isinstance(quiet_start, str):
                quiet_start = time.fromisoformat(quiet_start)
            if isinstance(quiet_end, str):
                quiet_end = time.fromisoformat(quiet_end)
            
            # Check if current time is outside quiet hours
            if quiet_start <= quiet_end:
                # Normal case: quiet hours don't cross midnight
                return current_time < quiet_start or current_time > quiet_end
            else:
                # Quiet hours cross midnight
                return quiet_end < current_time < quiet_start
                
        except Exception as e:
            logger.error(f"Error checking quiet hours: {e}")
            return True  # Default to allowing notifications
    
    def _is_urgent_notification(self, notification_type: str) -> bool:
        """Check if notification type is considered urgent"""
        urgent_types = [
            "security_alert",
            "sync_conflict",
            "quota_exceeded",
            "system_maintenance"
        ]
        return notification_type in urgent_types
    
    def _clear_user_cache(self, user_id: str):
        """Clear cache entries for a user"""
        keys_to_remove = [key for key in self.preference_cache.keys() if key.startswith(f"{user_id}_")]
        for key in keys_to_remove:
            del self.preference_cache[key]
            if key in self.cache_expiry:
                del self.cache_expiry[key]
    
    async def export_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Export all preferences for a user"""
        try:
            prefs = await self.get_user_preferences(user_id)
            
            # Format for export
            export_data = {
                "user_id": user_id,
                "exported_at": datetime.now().isoformat(),
                "preferences": {}
            }
            
            for notification_type, pref_data in prefs.items():
                export_data["preferences"][notification_type] = {
                    "email_enabled": pref_data.get("email_enabled", False),
                    "inapp_enabled": pref_data.get("inapp_enabled", True),
                    "sms_enabled": pref_data.get("sms_enabled", False),
                    "webhook_enabled": pref_data.get("webhook_enabled", False),
                    "digest_frequency": pref_data.get("digest_frequency", "daily"),
                    "quiet_hours_start": pref_data.get("quiet_hours_start"),
                    "quiet_hours_end": pref_data.get("quiet_hours_end"),
                    "timezone": pref_data.get("timezone", "UTC")
                }
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting user preferences: {e}")
            return {}
    
    async def import_user_preferences(self, user_id: str, preferences_data: Dict[str, Any]) -> bool:
        """Import preferences for a user"""
        try:
            preferences = preferences_data.get("preferences", {})
            
            success = await self.update_bulk_preferences(
                user_id=user_id,
                preferences=preferences
            )
            
            if success:
                logger.info(f"Imported preferences for user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error importing user preferences: {e}")
            return False
    
    async def get_stats(self) -> Dict:
        """Get preference service statistics"""
        stats = self.stats.copy()
        stats["uptime_seconds"] = (datetime.now() - stats["service_start"]).total_seconds()
        stats["cached_preferences"] = len(self.preference_cache)
        
        # Get preference statistics from database
        try:
            pref_stats = await self.db_manager.execute_query("""
                SELECT 
                    COUNT(DISTINCT user_id) as total_users,
                    COUNT(*) as total_preferences,
                    COUNT(CASE WHEN email_enabled = TRUE THEN 1 END) as email_enabled_count,
                    COUNT(CASE WHEN inapp_enabled = TRUE THEN 1 END) as inapp_enabled_count,
                    COUNT(CASE WHEN sms_enabled = TRUE THEN 1 END) as sms_enabled_count,
                    COUNT(CASE WHEN webhook_enabled = TRUE THEN 1 END) as webhook_enabled_count
                FROM notification_preferences
            """)
            
            if pref_stats:
                stats.update(pref_stats[0])
                
        except Exception as e:
            logger.error(f"Error getting preference stats: {e}")
        
        return stats