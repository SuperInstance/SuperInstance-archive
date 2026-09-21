"""
Digest Service - Handles batch digest emails and scheduling
"""

import asyncio
import logging
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Optional, Any
import json
import uuid

from core.config import settings
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class DigestService:
    """Handles digest email generation and scheduling"""
    
    def __init__(self, db_manager: DatabaseManager, email_service=None, template_service=None):
        self.db_manager = db_manager
        self.email_service = email_service
        self.template_service = template_service
        
        # Scheduler state
        self.scheduler_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "digests_generated": 0,
            "digests_sent": 0,
            "digest_errors": 0,
            "users_processed": 0,
            "service_start": datetime.now(),
            "last_digest_run": None
        }
        
        logger.info("Digest service initialized")
    
    async def start_digest_scheduler(self):
        """Start background digest scheduler"""
        if self.scheduler_running:
            logger.warning("Digest scheduler already running")
            return
        
        if not settings.DIGEST_ENABLED:
            logger.info("Digest emails disabled in configuration")
            return
        
        self.scheduler_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Digest scheduler started")
    
    async def stop_digest_scheduler(self):
        """Stop background digest scheduler"""
        if not self.scheduler_running:
            return
        
        self.scheduler_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Digest scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.scheduler_running:
            try:
                # Check every 15 minutes
                await asyncio.sleep(900)
                
                if not self.scheduler_running:
                    break
                
                # Process scheduled digests
                await self._process_scheduled_digests()
                
                # Generate new digest schedules if needed
                await self._schedule_daily_digests()
                
                self.stats["last_digest_run"] = datetime.now()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in digest scheduler loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _process_scheduled_digests(self):
        """Process digests that are due to be sent"""
        try:
            # Get digests scheduled for the past (including now)
            due_digests = await self.db_manager.execute_query("""
                SELECT id, user_id, tenant_id, digest_type, notifications, scheduled_for
                FROM digest_queue 
                WHERE status = 'pending' AND scheduled_for <= NOW()
                ORDER BY scheduled_for ASC
                LIMIT 50
            """)
            
            for digest in due_digests:
                try:
                    # Mark as processing
                    await self.db_manager.execute_command("""
                        UPDATE digest_queue SET status = 'processing' WHERE id = $1
                    """, digest["id"])
                    
                    # Generate and send digest
                    success = await self._generate_and_send_digest(digest)
                    
                    # Update status
                    if success:
                        await self.db_manager.execute_command("""
                            UPDATE digest_queue SET status = 'sent', sent_at = NOW() WHERE id = $1
                        """, digest["id"])
                        self.stats["digests_sent"] += 1
                    else:
                        await self.db_manager.execute_command("""
                            UPDATE digest_queue SET status = 'failed' WHERE id = $1
                        """, digest["id"])
                        self.stats["digest_errors"] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing digest {digest['id']}: {e}")
                    await self.db_manager.execute_command("""
                        UPDATE digest_queue SET status = 'failed' WHERE id = $1
                    """, digest["id"])
                    self.stats["digest_errors"] += 1
                    
        except Exception as e:
            logger.error(f"Error processing scheduled digests: {e}")
    
    async def _generate_and_send_digest(self, digest_data: Dict) -> bool:
        """Generate and send a digest email"""
        try:
            user_id = digest_data["user_id"]
            tenant_id = digest_data["tenant_id"]
            digest_type = digest_data["digest_type"]
            notifications = digest_data["notifications"]
            
            # Get user information
            user_info = await self._get_user_info(user_id)
            if not user_info or not user_info.get("email"):
                logger.warning(f"No email found for user {user_id}")
                return False
            
            # Generate digest content
            digest_content = await self._generate_digest_content(
                user_id=user_id,
                tenant_id=tenant_id,
                digest_type=digest_type,
                notifications=notifications
            )
            
            if not digest_content:
                logger.warning(f"No digest content generated for user {user_id}")
                return False
            
            # Send digest email
            success = await self.email_service.send_notification(
                user_id=user_id,
                to_email=user_info["email"],
                subject=digest_content["subject"],
                body=digest_content["body"],
                tenant_id=tenant_id,
                template_id=f"digest_{digest_type}",
                template_vars=digest_content["variables"]
            )
            
            if success:
                self.stats["digests_generated"] += 1
                logger.debug(f"Sent digest email to user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error generating and sending digest: {e}")
            return False
    
    async def _generate_digest_content(self,
                                      user_id: str,
                                      tenant_id: Optional[str],
                                      digest_type: str,
                                      notifications: List[Dict]) -> Optional[Dict]:
        """Generate digest email content"""
        try:
            # Get user activity data for the digest period
            if digest_type == "daily":
                period_start = datetime.now() - timedelta(days=1)
            elif digest_type == "weekly":
                period_start = datetime.now() - timedelta(days=7)
            else:
                period_start = datetime.now() - timedelta(days=1)
            
            # Get activity summary
            activity_data = await self._get_user_activity_summary(user_id, period_start)
            
            # Prepare template variables
            template_vars = {
                "user_id": user_id,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "period_type": digest_type,
                "files_uploaded": activity_data.get("files_uploaded", 0),
                "total_size": activity_data.get("total_size", 0),
                "sync_operations": activity_data.get("sync_operations", 0),
                "recent_files": activity_data.get("recent_files", []),
                "notifications": notifications[:10],  # Limit to recent notifications
                "unsubscribe_url": f"{settings.ACTIVELOG_API_URL}/preferences?user_id={user_id}"
            }
            
            # Render template
            if self.template_service:
                rendered = await self.template_service.render_template(
                    template_id=f"digest_{digest_type}",
                    variables=template_vars,
                    output_type="email",
                    tenant_id=tenant_id
                )
                
                if rendered:
                    return {
                        "subject": rendered.get("subject", f"{digest_type.title()} Activity Summary"),
                        "body": rendered.get("body", ""),
                        "variables": template_vars
                    }
            
            # Fallback to simple digest
            return self._generate_simple_digest(template_vars, digest_type)
            
        except Exception as e:
            logger.error(f"Error generating digest content: {e}")
            return None
    
    def _generate_simple_digest(self, vars: Dict, digest_type: str) -> Dict:
        """Generate simple digest when template is not available"""
        subject = f"{digest_type.title()} Activity Summary - {vars['date']}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1>ActiveLog {digest_type.title()} Summary</h1>
                <p>Here's your activity summary for {vars['date']}:</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Activity Overview</h3>
                    <ul>
                        <li>Files Uploaded: {vars['files_uploaded']}</li>
                        <li>Total Size: {self._format_filesize(vars['total_size'])}</li>
                        <li>Sync Operations: {vars['sync_operations']}</li>
                    </ul>
                </div>
                
                {self._format_recent_files(vars.get('recent_files', []))}
                {self._format_notifications(vars.get('notifications', []))}
                
                <p style="margin-top: 30px; color: #6c757d; font-size: 0.9em;">
                    <a href="{vars['unsubscribe_url']}">Update your notification preferences</a>
                </p>
            </div>
        </body>
        </html>
        """
        
        return {
            "subject": subject,
            "body": body,
            "variables": vars
        }
    
    def _format_recent_files(self, files: List[Dict]) -> str:
        """Format recent files for digest"""
        if not files:
            return ""
        
        files_html = "<div style='margin: 20px 0;'><h3>Recent Files</h3><ul>"
        for file in files[:5]:  # Limit to 5 files
            size = self._format_filesize(file.get('size', 0))
            files_html += f"<li>{file.get('name', 'Unknown')} ({size})</li>"
        files_html += "</ul></div>"
        
        return files_html
    
    def _format_notifications(self, notifications: List[Dict]) -> str:
        """Format notifications for digest"""
        if not notifications:
            return ""
        
        notif_html = "<div style='margin: 20px 0;'><h3>Recent Notifications</h3>"
        for notif in notifications[:5]:  # Limit to 5 notifications
            notif_html += f"""
            <div style="border-left: 3px solid #007bff; padding-left: 10px; margin: 10px 0;">
                <strong>{notif.get('title', 'Notification')}</strong><br>
                <span style="color: #6c757d; font-size: 0.9em;">{notif.get('created_at', '')}</span>
            </div>
            """
        notif_html += "</div>"
        
        return notif_html
    
    def _format_filesize(self, bytes_value):
        """Format file size in human readable format"""
        if not isinstance(bytes_value, (int, float)) or bytes_value == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    async def _get_user_activity_summary(self, user_id: str, since: datetime) -> Dict:
        """Get user activity summary for digest period"""
        try:
            # This would typically query the analytics service or main database
            # For now, we'll simulate some data
            
            # In a real implementation, you'd query:
            # - File uploads from analytics service
            # - Sync operations from sync engine
            # - Recent files from file service
            
            return {
                "files_uploaded": 0,  # Query from analytics
                "total_size": 0,      # Query from analytics
                "sync_operations": 0, # Query from sync engine
                "recent_files": []    # Query from file service
            }
            
        except Exception as e:
            logger.error(f"Error getting user activity summary: {e}")
            return {}
    
    async def _get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get user information including email"""
        try:
            # This would typically query the user service
            # For now, we'll return a placeholder
            return {
                "user_id": user_id,
                "email": f"user{user_id}@example.com",  # Placeholder
                "name": f"User {user_id}"
            }
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    async def _schedule_daily_digests(self):
        """Schedule daily digests for users who have them enabled"""
        try:
            # Get users with daily digest enabled
            from main import preference_service
            
            if not preference_service:
                return
            
            daily_users = await preference_service.get_digest_users("daily")
            
            for user in daily_users:
                user_id = user["user_id"]
                tenant_id = user["tenant_id"]
                timezone = user.get("timezone", "UTC")
                
                # Check if user already has a digest scheduled for today
                today = datetime.now().date()
                existing = await self.db_manager.execute_scalar("""
                    SELECT EXISTS(SELECT 1 FROM digest_queue 
                    WHERE user_id = $1 AND digest_type = 'daily' 
                    AND DATE(scheduled_for) = $2 AND status IN ('pending', 'processing'))
                """, user_id, today)
                
                if not existing:
                    # Schedule digest for configured times
                    for schedule_time in settings.DIGEST_SCHEDULE_TIMES:
                        try:
                            hour, minute = map(int, schedule_time.split(":"))
                            scheduled_datetime = datetime.combine(today, dt_time(hour, minute))
                            
                            # Only schedule if time hasn't passed
                            if scheduled_datetime > datetime.now():
                                await self._schedule_digest(
                                    user_id=user_id,
                                    tenant_id=tenant_id,
                                    digest_type="daily",
                                    scheduled_for=scheduled_datetime
                                )
                                break  # Only schedule one digest per day
                                
                        except ValueError:
                            logger.error(f"Invalid digest schedule time: {schedule_time}")
                            
        except Exception as e:
            logger.error(f"Error scheduling daily digests: {e}")
    
    async def _schedule_digest(self,
                              user_id: str,
                              digest_type: str,
                              scheduled_for: datetime,
                              tenant_id: Optional[str] = None):
        """Schedule a digest for a user"""
        try:
            # Get recent notifications for the user
            notifications = await self._get_user_notifications_for_digest(user_id, digest_type)
            
            # Only schedule if there are notifications to include
            if notifications:
                await self.db_manager.execute_command("""
                    INSERT INTO digest_queue (user_id, tenant_id, digest_type, notifications, scheduled_for)
                    VALUES ($1, $2, $3, $4, $5)
                """, user_id, tenant_id, digest_type, json.dumps(notifications), scheduled_for)
                
                logger.debug(f"Scheduled {digest_type} digest for user {user_id} at {scheduled_for}")
                
        except Exception as e:
            logger.error(f"Error scheduling digest: {e}")
    
    async def _get_user_notifications_for_digest(self, user_id: str, digest_type: str) -> List[Dict]:
        """Get notifications to include in digest"""
        try:
            # Determine lookback period
            if digest_type == "daily":
                since = datetime.now() - timedelta(days=1)
            elif digest_type == "weekly":
                since = datetime.now() - timedelta(days=7)
            else:
                since = datetime.now() - timedelta(days=1)
            
            # Get recent notifications
            notifications = await self.db_manager.execute_query("""
                SELECT notification_id, type, title, message, created_at
                FROM inapp_notifications 
                WHERE user_id = $1 AND created_at >= $2
                ORDER BY created_at DESC
                LIMIT 20
            """, user_id, since)
            
            # Format for digest
            return [
                {
                    "id": notif["notification_id"],
                    "type": notif["type"],
                    "title": notif["title"],
                    "message": notif["message"][:100] + "..." if len(notif["message"]) > 100 else notif["message"],
                    "created_at": notif["created_at"].isoformat()
                }
                for notif in notifications
            ]
            
        except Exception as e:
            logger.error(f"Error getting notifications for digest: {e}")
            return []
    
    async def send_immediate_digest(self,
                                   user_id: str,
                                   digest_type: str = "daily",
                                   tenant_id: Optional[str] = None) -> bool:
        """Send an immediate digest to a user"""
        try:
            # Get notifications
            notifications = await self._get_user_notifications_for_digest(user_id, digest_type)
            
            # Create digest data
            digest_data = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "digest_type": digest_type,
                "notifications": notifications,
                "scheduled_for": datetime.now()
            }
            
            # Generate and send
            success = await self._generate_and_send_digest(digest_data)
            
            if success:
                self.stats["users_processed"] += 1
                logger.info(f"Sent immediate digest to user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending immediate digest: {e}")
            return False
    
    async def get_digest_queue_status(self) -> Dict:
        """Get status of digest queue"""
        try:
            status = await self.db_manager.execute_query("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM digest_queue 
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY status
            """)
            
            return {row["status"]: row["count"] for row in status}
            
        except Exception as e:
            logger.error(f"Error getting digest queue status: {e}")
            return {}
    
    def is_running(self) -> bool:
        """Check if digest scheduler is running"""
        return self.scheduler_running
    
    async def get_stats(self) -> Dict:
        """Get digest service statistics"""
        stats = self.stats.copy()
        stats["uptime_seconds"] = (datetime.now() - stats["service_start"]).total_seconds()
        stats["scheduler_running"] = self.scheduler_running
        stats["digest_enabled"] = settings.DIGEST_ENABLED
        
        # Get queue status
        try:
            queue_status = await self.get_digest_queue_status()
            stats["queue_status"] = queue_status
        except Exception as e:
            logger.error(f"Error getting queue status for stats: {e}")
            stats["queue_status"] = {}
        
        return stats