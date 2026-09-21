"""
Webhook Service - Handles webhook notifications to external systems
"""

import asyncio
import aiohttp
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import uuid

from ..core.config import settings
from ..core.database import DatabaseManager
from ..core.logging import logger

class WebhookService:
    """Handles webhook notifications with retry logic and security"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.retry_processor_running = False
        self.retry_task: Optional[asyncio.Task] = None
        
        # HTTP session for making requests
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Statistics
        self.stats = {
            "webhooks_sent": 0,
            "webhooks_failed": 0,
            "webhooks_retried": 0,
            "active_endpoints": 0,
            "last_sent": None,
            "service_start": datetime.now()
        }
        
        logger.info("Webhook service initialized")
    
    async def _ensure_session(self):
        """Ensure HTTP session is available"""
        if not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=settings.WEBHOOK_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def start_retry_processor(self):
        """Start background retry processor"""
        if self.retry_processor_running:
            logger.warning("Webhook retry processor already running")
            return
        
        self.retry_processor_running = True
        self.retry_task = asyncio.create_task(self._retry_processor_loop())
        logger.info("Webhook retry processor started")
    
    async def stop_retry_processor(self):
        """Stop background retry processor"""
        if not self.retry_processor_running:
            return
        
        self.retry_processor_running = False
        
        if self.retry_task:
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                pass
        
        if self.session:
            await self.session.close()
        
        logger.info("Webhook retry processor stopped")
    
    async def _retry_processor_loop(self):
        """Background loop to retry failed webhooks"""
        while self.retry_processor_running:
            try:
                await asyncio.sleep(settings.WEBHOOK_RETRY_DELAY)
                
                if not self.retry_processor_running:
                    break
                
                await self._retry_failed_webhooks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in webhook retry processor: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def send_webhook(self,
                          user_id: str,
                          webhook_url: str,
                          payload: Dict[str, Any],
                          tenant_id: Optional[str] = None,
                          notification_type: str = "generic",
                          headers: Optional[Dict[str, str]] = None,
                          secret_key: Optional[str] = None) -> bool:
        """Send webhook notification"""
        try:
            notification_id = str(uuid.uuid4())
            
            # Prepare headers
            request_headers = {
                "Content-Type": "application/json",
                "User-Agent": f"ActiveLog-Webhooks/1.0",
                "X-ActiveLog-Event": notification_type,
                "X-ActiveLog-Delivery": notification_id,
                "X-ActiveLog-Timestamp": str(int(datetime.now().timestamp()))
            }
            
            if headers:
                request_headers.update(headers)
            
            # Add signature if secret key provided
            if secret_key:
                signature = self._generate_signature(payload, secret_key)
                request_headers["X-ActiveLog-Signature"] = signature
            
            # Log webhook to database
            await self.db_manager.execute_command("""
                INSERT INTO webhook_notifications (
                    notification_id, user_id, tenant_id, webhook_url, payload, headers, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, 
                notification_id, user_id, tenant_id, webhook_url,
                json.dumps(payload), json.dumps(request_headers), "pending"
            )
            
            # Send webhook
            success = await self._send_webhook_request(
                notification_id=notification_id,
                webhook_url=webhook_url,
                payload=payload,
                headers=request_headers
            )
            
            # Update statistics
            if success:
                self.stats["webhooks_sent"] += 1
                self.stats["last_sent"] = datetime.now()
            else:
                self.stats["webhooks_failed"] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            self.stats["webhooks_failed"] += 1
            return False
    
    async def _send_webhook_request(self,
                                   notification_id: str,
                                   webhook_url: str,
                                   payload: Dict[str, Any],
                                   headers: Dict[str, str]) -> bool:
        """Send the actual webhook HTTP request"""
        try:
            await self._ensure_session()
            
            async with self.session.post(
                webhook_url,
                json=payload,
                headers=headers
            ) as response:
                response_body = await response.text()
                
                # Check if request was successful
                if 200 <= response.status < 300:
                    # Update database with success
                    await self.db_manager.execute_command("""
                        UPDATE webhook_notifications 
                        SET status = 'sent', response_status = $1, response_body = $2, sent_at = NOW()
                        WHERE notification_id = $3
                    """, response.status, response_body[:1000], notification_id)  # Limit response body size
                    
                    logger.debug(f"Webhook sent successfully: {notification_id} -> {webhook_url}")
                    return True
                else:
                    # Update database with failure
                    await self.db_manager.execute_command("""
                        UPDATE webhook_notifications 
                        SET status = 'failed', response_status = $1, response_body = $2,
                            error_message = $3
                        WHERE notification_id = $4
                    """, 
                        response.status, response_body[:1000], 
                        f"HTTP {response.status}", notification_id
                    )
                    
                    logger.warning(f"Webhook failed with status {response.status}: {notification_id}")
                    return False
                    
        except asyncio.TimeoutError:
            error_msg = "Request timeout"
            await self.db_manager.execute_command("""
                UPDATE webhook_notifications 
                SET status = 'failed', error_message = $1
                WHERE notification_id = $2
            """, error_msg, notification_id)
            
            logger.warning(f"Webhook timeout: {notification_id} -> {webhook_url}")
            return False
            
        except Exception as e:
            error_msg = str(e)
            await self.db_manager.execute_command("""
                UPDATE webhook_notifications 
                SET status = 'failed', error_message = $1
                WHERE notification_id = $2
            """, error_msg, notification_id)
            
            logger.error(f"Webhook request failed: {notification_id} -> {webhook_url}: {e}")
            return False
    
    def _generate_signature(self, payload: Dict[str, Any], secret_key: str) -> str:
        """Generate HMAC signature for webhook security"""
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            secret_key.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    async def send_webhooks_to_user_endpoints(self,
                                             user_id: str,
                                             notification_type: str,
                                             payload: Dict[str, Any],
                                             tenant_id: Optional[str] = None) -> List[bool]:
        """Send webhooks to all configured endpoints for a user"""
        try:
            # Get user's webhook endpoints for this notification type
            endpoints = await self.db_manager.execute_query("""
                SELECT id, url, secret_key, name
                FROM webhook_endpoints 
                WHERE user_id = $1 AND is_active = TRUE
                AND ($2 = ANY(notification_types) OR array_length(notification_types, 1) IS NULL)
            """, user_id, notification_type)
            
            if not endpoints:
                return []
            
            # Send to all endpoints concurrently
            tasks = []
            for endpoint in endpoints:
                task = self.send_webhook(
                    user_id=user_id,
                    webhook_url=endpoint["url"],
                    payload=payload,
                    tenant_id=tenant_id,
                    notification_type=notification_type,
                    secret_key=endpoint["secret_key"]
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert exceptions to False
            success_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Webhook task failed: {result}")
                    success_results.append(False)
                else:
                    success_results.append(result)
            
            return success_results
            
        except Exception as e:
            logger.error(f"Error sending webhooks to user endpoints: {e}")
            return []
    
    async def register_webhook_endpoint(self,
                                       user_id: str,
                                       name: str,
                                       url: str,
                                       tenant_id: Optional[str] = None,
                                       notification_types: Optional[List[str]] = None,
                                       secret_key: Optional[str] = None) -> int:
        """Register a new webhook endpoint for a user"""
        try:
            # Validate URL format
            if not url.startswith(('http://', 'https://')):
                raise ValueError("Webhook URL must start with http:// or https://")
            
            # Generate secret key if not provided
            if not secret_key:
                secret_key = str(uuid.uuid4())
            
            # Insert webhook endpoint
            endpoint_id = await self.db_manager.execute_scalar("""
                INSERT INTO webhook_endpoints (
                    user_id, tenant_id, name, url, secret_key, notification_types
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, 
                user_id, tenant_id, name, url, secret_key, 
                notification_types or []
            )
            
            # Update active endpoints count
            self.stats["active_endpoints"] = await self.db_manager.execute_scalar(
                "SELECT COUNT(*) FROM webhook_endpoints WHERE is_active = TRUE"
            )
            
            logger.info(f"Registered webhook endpoint for user {user_id}: {name} -> {url}")
            return endpoint_id
            
        except Exception as e:
            logger.error(f"Error registering webhook endpoint: {e}")
            raise
    
    async def update_webhook_endpoint(self,
                                     endpoint_id: int,
                                     user_id: str,
                                     name: Optional[str] = None,
                                     url: Optional[str] = None,
                                     notification_types: Optional[List[str]] = None,
                                     is_active: Optional[bool] = None) -> bool:
        """Update webhook endpoint configuration"""
        try:
            # Build update query dynamically
            updates = []
            params = []
            param_count = 0
            
            if name is not None:
                param_count += 1
                updates.append(f"name = ${param_count}")
                params.append(name)
            
            if url is not None:
                if not url.startswith(('http://', 'https://')):
                    raise ValueError("Webhook URL must start with http:// or https://")
                param_count += 1
                updates.append(f"url = ${param_count}")
                params.append(url)
            
            if notification_types is not None:
                param_count += 1
                updates.append(f"notification_types = ${param_count}")
                params.append(notification_types)
            
            if is_active is not None:
                param_count += 1
                updates.append(f"is_active = ${param_count}")
                params.append(is_active)
            
            if not updates:
                return True  # Nothing to update
            
            # Add WHERE clause parameters
            param_count += 1
            params.append(endpoint_id)
            param_count += 1
            params.append(user_id)
            
            updates.append("updated_at = NOW()")
            
            query = f"""
                UPDATE webhook_endpoints 
                SET {', '.join(updates)}
                WHERE id = ${param_count - 1} AND user_id = ${param_count}
            """
            
            result = await self.db_manager.execute_command(query, *params)
            
            # Update active endpoints count
            self.stats["active_endpoints"] = await self.db_manager.execute_scalar(
                "SELECT COUNT(*) FROM webhook_endpoints WHERE is_active = TRUE"
            )
            
            return "1" in result  # Check if one row was updated
            
        except Exception as e:
            logger.error(f"Error updating webhook endpoint: {e}")
            return False
    
    async def delete_webhook_endpoint(self, endpoint_id: int, user_id: str) -> bool:
        """Delete webhook endpoint"""
        try:
            result = await self.db_manager.execute_command("""
                DELETE FROM webhook_endpoints 
                WHERE id = $1 AND user_id = $2
            """, endpoint_id, user_id)
            
            # Update active endpoints count
            self.stats["active_endpoints"] = await self.db_manager.execute_scalar(
                "SELECT COUNT(*) FROM webhook_endpoints WHERE is_active = TRUE"
            )
            
            return "1" in result
            
        except Exception as e:
            logger.error(f"Error deleting webhook endpoint: {e}")
            return False
    
    async def get_user_webhooks(self, user_id: str) -> List[Dict]:
        """Get all webhook endpoints for a user"""
        try:
            endpoints = await self.db_manager.execute_query("""
                SELECT id, name, url, notification_types, is_active, created_at, updated_at
                FROM webhook_endpoints 
                WHERE user_id = $1
                ORDER BY created_at DESC
            """, user_id)
            
            return endpoints
            
        except Exception as e:
            logger.error(f"Error getting user webhooks: {e}")
            return []
    
    async def test_webhook_endpoint(self, endpoint_id: int, user_id: str) -> Dict[str, Any]:
        """Test a webhook endpoint with a ping payload"""
        try:
            # Get endpoint details
            endpoint = await self.db_manager.execute_query("""
                SELECT url, secret_key FROM webhook_endpoints 
                WHERE id = $1 AND user_id = $2
            """, endpoint_id, user_id)
            
            if not endpoint:
                return {"success": False, "error": "Endpoint not found"}
            
            # Send test payload
            test_payload = {
                "event": "ping",
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "message": "This is a test webhook from ActiveLog"
            }
            
            success = await self.send_webhook(
                user_id=user_id,
                webhook_url=endpoint[0]["url"],
                payload=test_payload,
                notification_type="ping",
                secret_key=endpoint[0]["secret_key"]
            )
            
            return {
                "success": success,
                "message": "Test webhook sent successfully" if success else "Test webhook failed"
            }
            
        except Exception as e:
            logger.error(f"Error testing webhook endpoint: {e}")
            return {"success": False, "error": str(e)}
    
    async def _retry_failed_webhooks(self):
        """Retry failed webhook notifications"""
        try:
            # Get failed webhooks that haven't exceeded retry limit
            failed_webhooks = await self.db_manager.execute_query("""
                SELECT notification_id, user_id, tenant_id, webhook_url, payload, headers, retry_count
                FROM webhook_notifications 
                WHERE status = 'failed' AND retry_count < $1
                AND created_at > NOW() - INTERVAL '24 hours'
                ORDER BY created_at ASC
                LIMIT 50
            """, settings.WEBHOOK_RETRY_ATTEMPTS)
            
            for webhook in failed_webhooks:
                try:
                    # Increment retry count
                    await self.db_manager.execute_command("""
                        UPDATE webhook_notifications 
                        SET retry_count = retry_count + 1, status = 'pending'
                        WHERE notification_id = $1
                    """, webhook['notification_id'])
                    
                    # Retry sending
                    success = await self._send_webhook_request(
                        notification_id=webhook['notification_id'],
                        webhook_url=webhook['webhook_url'],
                        payload=webhook['payload'],
                        headers=webhook['headers']
                    )
                    
                    if success:
                        self.stats["webhooks_retried"] += 1
                        logger.debug(f"Successfully retried webhook: {webhook['notification_id']}")
                
                except Exception as e:
                    logger.error(f"Error retrying webhook {webhook['notification_id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in retry failed webhooks: {e}")
    
    async def get_webhook_status(self, notification_id: str) -> Optional[Dict]:
        """Get status of a webhook notification"""
        try:
            result = await self.db_manager.execute_query("""
                SELECT notification_id, status, response_status, response_body,
                       error_message, retry_count, sent_at, created_at
                FROM webhook_notifications 
                WHERE notification_id = $1
            """, notification_id)
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error getting webhook status: {e}")
            return None
    
    async def get_stats(self) -> Dict:
        """Get webhook service statistics"""
        stats = self.stats.copy()
        stats["uptime_seconds"] = (datetime.now() - stats["service_start"]).total_seconds()
        stats["retry_processor_running"] = self.retry_processor_running
        
        # Get recent activity
        try:
            last_24h = datetime.now() - timedelta(hours=24)
            recent_stats = await self.db_manager.execute_query("""
                SELECT status, COUNT(*) as count
                FROM webhook_notifications 
                WHERE created_at >= $1
                GROUP BY status
            """, last_24h)
            
            stats["last_24h"] = {row["status"]: row["count"] for row in recent_stats}
            
        except Exception as e:
            logger.error(f"Error getting recent webhook stats: {e}")
            stats["last_24h"] = {}
        
        return stats