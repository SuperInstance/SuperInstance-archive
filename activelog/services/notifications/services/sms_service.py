"""
SMS Service - Handles SMS notifications using Twilio
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import uuid

# Optional Twilio import
try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

from ..core.config import settings
from ..core.database import DatabaseManager
from ..core.logging import logger

class SMSService:
    """Handles SMS notifications with Twilio integration"""
    
    def __init__(self, db_manager: DatabaseManager, template_service=None):
        self.db_manager = db_manager
        self.template_service = template_service
        
        # Twilio client
        self.twilio_client = None
        self.twilio_configured = False
        
        # Statistics
        self.stats = {
            "sms_sent": 0,
            "sms_failed": 0,
            "sms_delivered": 0,
            "rate_limited": 0,
            "last_sent": None,
            "service_start": datetime.now()
        }
        
        # Initialize Twilio if configured
        self._initialize_twilio()
        
        logger.info("SMS service initialized")
    
    def _initialize_twilio(self):
        """Initialize Twilio client if configured"""
        if not TWILIO_AVAILABLE:
            logger.warning("Twilio SDK not available. Install with: pip install twilio")
            return
        
        if not settings.sms_configured:
            logger.info("SMS not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_PHONE")
            return
        
        try:
            self.twilio_client = TwilioClient(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            # Test connection by getting account info
            account = self.twilio_client.api.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
            if account.status == "active":
                self.twilio_configured = True
                logger.info("Twilio SMS service configured successfully")
            else:
                logger.error(f"Twilio account status: {account.status}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Twilio: {e}")
    
    def is_configured(self) -> bool:
        """Check if SMS service is properly configured"""
        return self.twilio_configured and self.twilio_client is not None
    
    async def send_notification(self,
                               user_id: str,
                               to_phone: str,
                               message: str,
                               tenant_id: Optional[str] = None,
                               template_id: Optional[str] = None,
                               template_vars: Optional[Dict] = None,
                               priority: str = "normal") -> bool:
        """Send SMS notification"""
        
        if not self.is_configured():
            logger.error("SMS service not configured")
            return False
        
        try:
            # Generate notification ID
            notification_id = str(uuid.uuid4())
            
            # Process template if provided
            if template_id and self.template_service:
                template_result = await self.template_service.render_template(
                    template_id, template_vars or {}, "sms"
                )
                if template_result and "sms" in template_result:
                    message = template_result["sms"]
            
            # Validate phone number format
            formatted_phone = self._format_phone_number(to_phone)
            if not formatted_phone:
                logger.error(f"Invalid phone number format: {to_phone}")
                return False
            
            # Truncate message if too long (SMS limit is 160 chars for single message)
            if len(message) > 160:
                message = message[:157] + "..."
            
            # Log SMS to database
            await self.db_manager.execute_command("""
                INSERT INTO sms_notifications (
                    notification_id, user_id, tenant_id, to_phone, message, template_id, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, 
                notification_id, user_id, tenant_id, formatted_phone, message, template_id, "pending"
            )
            
            # Send SMS
            success = await self._send_sms(
                notification_id=notification_id,
                to_phone=formatted_phone,
                message=message
            )
            
            # Update statistics
            if success:
                self.stats["sms_sent"] += 1
                self.stats["last_sent"] = datetime.now()
            else:
                self.stats["sms_failed"] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {e}")
            self.stats["sms_failed"] += 1
            return False
    
    async def _send_sms(self, notification_id: str, to_phone: str, message: str) -> bool:
        """Send the actual SMS using Twilio"""
        try:
            # Send SMS in thread pool to avoid blocking
            def send_sync():
                return self.twilio_client.messages.create(
                    body=message,
                    from_=settings.TWILIO_FROM_PHONE,
                    to=to_phone
                )
            
            # Execute in thread pool
            loop = asyncio.get_event_loop()
            twilio_message = await loop.run_in_executor(None, send_sync)
            
            # Update database with success
            await self.db_manager.execute_command("""
                UPDATE sms_notifications 
                SET status = 'sent', provider = 'twilio', provider_message_id = $1, sent_at = NOW()
                WHERE notification_id = $2
            """, twilio_message.sid, notification_id)
            
            logger.debug(f"SMS sent successfully: {notification_id} -> {to_phone}")
            return True
            
        except TwilioRestException as e:
            error_msg = f"Twilio error {e.code}: {e.msg}"
            
            # Update database with failure
            await self.db_manager.execute_command("""
                UPDATE sms_notifications 
                SET status = 'failed', error_message = $1
                WHERE notification_id = $2
            """, error_msg, notification_id)
            
            # Check for rate limiting
            if e.code == 20429:  # Rate limit exceeded
                self.stats["rate_limited"] += 1
                logger.warning(f"SMS rate limit exceeded: {notification_id}")
            else:
                logger.error(f"Twilio SMS failed: {error_msg}")
            
            return False
            
        except Exception as e:
            error_msg = str(e)
            
            # Update database with failure
            await self.db_manager.execute_command("""
                UPDATE sms_notifications 
                SET status = 'failed', error_message = $1
                WHERE notification_id = $2
            """, error_msg, notification_id)
            
            logger.error(f"SMS send failed: {notification_id} -> {to_phone}: {e}")
            return False
    
    def _format_phone_number(self, phone: str) -> Optional[str]:
        """Format and validate phone number"""
        try:
            # Remove all non-digit characters
            digits_only = ''.join(filter(str.isdigit, phone))
            
            # Check minimum length
            if len(digits_only) < 10:
                return None
            
            # Add country code if not present
            if len(digits_only) == 10:
                # Assume US number if 10 digits
                formatted = f"+1{digits_only}"
            elif len(digits_only) == 11 and digits_only.startswith('1'):
                # US number with country code
                formatted = f"+{digits_only}"
            elif digits_only.startswith(('1', '44', '33', '49')):  # Common country codes
                formatted = f"+{digits_only}"
            else:
                # Already has country code or international format
                formatted = f"+{digits_only}"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting phone number {phone}: {e}")
            return None
    
    async def send_bulk_sms(self, notifications: List[Dict]) -> Dict[str, int]:
        """Send multiple SMS notifications in batch"""
        results = {"sent": 0, "failed": 0}
        
        if not self.is_configured():
            logger.error("SMS service not configured for bulk sending")
            return results
        
        # Process in smaller batches to respect rate limits
        batch_size = 5  # Conservative batch size for SMS
        for i in range(0, len(notifications), batch_size):
            batch = notifications[i:i + batch_size]
            
            # Send batch with delay between messages
            for notification in batch:
                try:
                    success = await self.send_notification(**notification)
                    if success:
                        results["sent"] += 1
                    else:
                        results["failed"] += 1
                        
                    # Rate limiting delay
                    await asyncio.sleep(1)  # 1 second between SMS
                    
                except Exception as e:
                    logger.error(f"Error in bulk SMS: {e}")
                    results["failed"] += 1
            
            # Longer pause between batches
            if i + batch_size < len(notifications):
                await asyncio.sleep(5)
        
        return results
    
    async def get_delivery_status(self, notification_id: str) -> Optional[Dict]:
        """Get delivery status of an SMS notification"""
        try:
            # Get notification from database
            result = await self.db_manager.execute_query("""
                SELECT notification_id, status, provider_message_id, error_message, sent_at, created_at
                FROM sms_notifications 
                WHERE notification_id = $1
            """, notification_id)
            
            if not result:
                return None
            
            sms_data = result[0]
            
            # If we have a Twilio message ID, check delivery status
            if sms_data["provider_message_id"] and self.is_configured():
                try:
                    def get_message_sync():
                        return self.twilio_client.messages(sms_data["provider_message_id"]).fetch()
                    
                    loop = asyncio.get_event_loop()
                    twilio_message = await loop.run_in_executor(None, get_message_sync)
                    
                    # Update database if status changed
                    if twilio_message.status == "delivered" and sms_data["status"] != "delivered":
                        await self.db_manager.execute_command("""
                            UPDATE sms_notifications SET status = 'delivered' WHERE notification_id = $1
                        """, notification_id)
                        self.stats["sms_delivered"] += 1
                    
                    sms_data["twilio_status"] = twilio_message.status
                    sms_data["twilio_error_code"] = twilio_message.error_code
                    sms_data["twilio_error_message"] = twilio_message.error_message
                    
                except Exception as e:
                    logger.error(f"Error getting Twilio status: {e}")
            
            return sms_data
            
        except Exception as e:
            logger.error(f"Error getting SMS delivery status: {e}")
            return None
    
    async def retry_failed_sms(self, max_retries: int = 2) -> int:
        """Retry failed SMS notifications"""
        if not self.is_configured():
            return 0
        
        try:
            # Get failed SMS that haven't exceeded retry limit
            failed_sms = await self.db_manager.execute_query("""
                SELECT notification_id, user_id, tenant_id, to_phone, message, template_id, retry_count
                FROM sms_notifications 
                WHERE status = 'failed' AND retry_count < $1
                AND created_at > NOW() - INTERVAL '24 hours'
                ORDER BY created_at ASC
                LIMIT 20
            """, max_retries)
            
            retried_count = 0
            
            for sms in failed_sms:
                try:
                    # Increment retry count
                    await self.db_manager.execute_command("""
                        UPDATE sms_notifications 
                        SET retry_count = retry_count + 1, status = 'pending'
                        WHERE notification_id = $1
                    """, sms['notification_id'])
                    
                    # Retry sending
                    success = await self._send_sms(
                        notification_id=sms['notification_id'],
                        to_phone=sms['to_phone'],
                        message=sms['message']
                    )
                    
                    if success:
                        retried_count += 1
                    
                    # Rate limiting delay
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error retrying SMS {sms['notification_id']}: {e}")
            
            return retried_count
            
        except Exception as e:
            logger.error(f"Error retrying failed SMS: {e}")
            return 0
    
    async def validate_phone_number(self, phone: str) -> Dict[str, Any]:
        """Validate phone number using Twilio Lookup API"""
        if not self.is_configured():
            return {"valid": False, "error": "SMS service not configured"}
        
        try:
            formatted_phone = self._format_phone_number(phone)
            if not formatted_phone:
                return {"valid": False, "error": "Invalid phone number format"}
            
            def lookup_sync():
                return self.twilio_client.lookups.phone_numbers(formatted_phone).fetch()
            
            loop = asyncio.get_event_loop()
            lookup_result = await loop.run_in_executor(None, lookup_sync)
            
            return {
                "valid": True,
                "formatted": lookup_result.phone_number,
                "country_code": lookup_result.country_code,
                "national_format": lookup_result.national_format
            }
            
        except TwilioRestException as e:
            return {"valid": False, "error": f"Twilio error: {e.msg}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def get_sms_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get SMS history for a user"""
        try:
            history = await self.db_manager.execute_query("""
                SELECT notification_id, to_phone, message, status, error_message, sent_at, created_at
                FROM sms_notifications 
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, user_id, limit)
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting SMS history: {e}")
            return []
    
    async def update_twilio_config(self,
                                  account_sid: Optional[str] = None,
                                  auth_token: Optional[str] = None,
                                  from_phone: Optional[str] = None) -> bool:
        """Update Twilio configuration"""
        try:
            # Update settings if provided
            if account_sid:
                settings.TWILIO_ACCOUNT_SID = account_sid
            if auth_token:
                settings.TWILIO_AUTH_TOKEN = auth_token
            if from_phone:
                settings.TWILIO_FROM_PHONE = from_phone
            
            # Reinitialize Twilio client
            self._initialize_twilio()
            
            return self.is_configured()
            
        except Exception as e:
            logger.error(f"Error updating Twilio config: {e}")
            return False
    
    async def get_account_info(self) -> Optional[Dict]:
        """Get Twilio account information"""
        if not self.is_configured():
            return None
        
        try:
            def get_account_sync():
                account = self.twilio_client.api.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
                balance = self.twilio_client.api.accounts(settings.TWILIO_ACCOUNT_SID).balance.fetch()
                
                return {
                    "account_sid": account.sid,
                    "friendly_name": account.friendly_name,
                    "status": account.status,
                    "type": account.type,
                    "balance": balance.balance,
                    "currency": balance.currency
                }
            
            loop = asyncio.get_event_loop()
            account_info = await loop.run_in_executor(None, get_account_sync)
            
            return account_info
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    async def get_stats(self) -> Dict:
        """Get SMS service statistics"""
        stats = self.stats.copy()
        stats["uptime_seconds"] = (datetime.now() - stats["service_start"]).total_seconds()
        stats["configured"] = self.is_configured()
        stats["twilio_available"] = TWILIO_AVAILABLE
        
        # Get recent activity from database
        try:
            last_24h = datetime.now() - timedelta(hours=24)
            recent_stats = await self.db_manager.execute_query("""
                SELECT status, COUNT(*) as count
                FROM sms_notifications 
                WHERE created_at >= $1
                GROUP BY status
            """, last_24h)
            
            stats["last_24h"] = {row["status"]: row["count"] for row in recent_stats}
            
        except Exception as e:
            logger.error(f"Error getting recent SMS stats: {e}")
            stats["last_24h"] = {}
        
        return stats