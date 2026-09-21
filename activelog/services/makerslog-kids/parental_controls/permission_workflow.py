#!/usr/bin/env python3
"""
Permission Request Workflow System for MakersLog Kids
Handles permission requests, notifications, and approval workflows
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import asyncpg
import uuid
import smtplib
from email.mime.text import MIMEText, MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NotificationType(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"

class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class NotificationTemplate:
    """Notification template configuration"""
    template_id: str
    notification_type: NotificationType
    subject_template: str
    body_template: str
    variables: List[str]

@dataclass
class NotificationPreference:
    """Parent notification preferences"""
    parent_id: str
    email_enabled: bool
    sms_enabled: bool
    push_enabled: bool
    quiet_hours_start: str  # HH:MM format
    quiet_hours_end: str    # HH:MM format
    permission_notifications: bool
    activity_alerts: bool
    spending_alerts: bool
    time_limit_warnings: bool

class NotificationService:
    """Handles notifications for permission requests and alerts"""
    
    def __init__(self, db_pool: asyncpg.Pool, config: Dict[str, Any]):
        self.db_pool = db_pool
        self.config = config
        
        # Initialize notification templates
        self.templates = {
            'permission_request': NotificationTemplate(
                'permission_request',
                NotificationType.EMAIL,
                'Permission Request from {child_name}',
                '''
                <h2>Permission Request</h2>
                <p>Your child <strong>{child_name}</strong> is requesting permission for:</p>
                <p><strong>Request Type:</strong> {permission_type}</p>
                <p><strong>Details:</strong> {request_details}</p>
                <p><strong>Reason:</strong> {reason}</p>
                <p><strong>Requested at:</strong> {requested_at}</p>
                
                <div style="margin: 20px 0;">
                    <a href="{approval_link}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Approve</a>
                    <a href="{deny_link}" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Deny</a>
                </div>
                
                <p>You can also manage this request in the parent dashboard: <a href="{dashboard_link}">View Dashboard</a></p>
                ''',
                ['child_name', 'permission_type', 'request_details', 'reason', 'requested_at', 'approval_link', 'deny_link', 'dashboard_link']
            ),
            
            'spending_alert': NotificationTemplate(
                'spending_alert',
                NotificationType.EMAIL,
                'Spending Alert - {child_name}',
                '''
                <h2>Spending Alert</h2>
                <p><strong>{child_name}</strong> has reached a spending threshold:</p>
                <p><strong>Current Spending:</strong> ${current_amount}</p>
                <p><strong>Limit:</strong> ${limit_amount}</p>
                <p><strong>Period:</strong> {period}</p>
                <p><strong>Time:</strong> {alert_time}</p>
                
                <p>View spending details: <a href="{dashboard_link}">Parent Dashboard</a></p>
                ''',
                ['child_name', 'current_amount', 'limit_amount', 'period', 'alert_time', 'dashboard_link']
            ),
            
            'time_warning': NotificationTemplate(
                'time_warning',
                NotificationType.PUSH,
                'Screen Time Warning - {child_name}',
                '''
                {child_name} has {minutes_remaining} minutes of screen time remaining today.
                Daily limit: {daily_limit} minutes
                ''',
                ['child_name', 'minutes_remaining', 'daily_limit']
            ),
            
            'activity_alert': NotificationTemplate(
                'activity_alert',
                NotificationType.EMAIL,
                'Activity Alert - {child_name}',
                '''
                <h2>Activity Alert</h2>
                <p><strong>{child_name}</strong> has triggered an activity alert:</p>
                <p><strong>Alert Type:</strong> {alert_type}</p>
                <p><strong>Details:</strong> {alert_details}</p>
                <p><strong>Time:</strong> {alert_time}</p>
                
                <p>View full activity log: <a href="{dashboard_link}">Parent Dashboard</a></p>
                ''',
                ['child_name', 'alert_type', 'alert_details', 'alert_time', 'dashboard_link']
            )
        }
    
    async def send_permission_request_notification(self, request_data: Dict[str, Any]):
        """Send notification for a new permission request"""
        try:
            # Get parent notification preferences
            parent_id = request_data['parent_id']
            preferences = await self.get_notification_preferences(parent_id)
            
            if not preferences.permission_notifications:
                logger.info(f"Permission notifications disabled for parent {parent_id}")
                return
            
            # Check quiet hours
            if self._is_quiet_hours(preferences):
                await self._schedule_notification(request_data, 'permission_request')
                return
            
            # Get parent contact info
            parent_info = await self._get_parent_contact_info(parent_id)
            child_name = await self._get_child_name(request_data['child_id'])
            
            # Prepare notification data
            notification_data = {
                'child_name': child_name,
                'permission_type': request_data['permission_type'].replace('_', ' ').title(),
                'request_details': self._format_request_details(request_data),
                'reason': request_data.get('reason', 'No reason provided'),
                'requested_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'approval_link': f"{self.config['base_url']}/approve/{request_data['request_id']}",
                'deny_link': f"{self.config['base_url']}/deny/{request_data['request_id']}",
                'dashboard_link': f"{self.config['base_url']}/parent-dashboard"
            }
            
            # Send notifications based on preferences
            if preferences.email_enabled and parent_info.get('email'):
                await self._send_email_notification('permission_request', parent_info['email'], notification_data)
            
            if preferences.sms_enabled and parent_info.get('phone'):
                await self._send_sms_notification('permission_request', parent_info['phone'], notification_data)
            
            if preferences.push_enabled:
                await self._send_push_notification('permission_request', parent_id, notification_data)
            
            # Always create in-app notification
            await self._create_in_app_notification(parent_id, 'permission_request', notification_data)
            
        except Exception as e:
            logger.error(f"Failed to send permission request notification: {e}")
    
    async def send_spending_alert(self, child_id: str, spending_data: Dict[str, Any]):
        """Send spending limit alert to parent"""
        try:
            parent_id = await self._get_parent_id(child_id)
            preferences = await self.get_notification_preferences(parent_id)
            
            if not preferences.spending_alerts:
                return
            
            child_name = await self._get_child_name(child_id)
            parent_info = await self._get_parent_contact_info(parent_id)
            
            notification_data = {
                'child_name': child_name,
                'current_amount': f"{spending_data['current_amount']:.2f}",
                'limit_amount': f"{spending_data['limit_amount']:.2f}",
                'period': spending_data['period'],
                'alert_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'dashboard_link': f"{self.config['base_url']}/parent-dashboard"
            }
            
            if preferences.email_enabled and parent_info.get('email'):
                await self._send_email_notification('spending_alert', parent_info['email'], notification_data)
            
            await self._create_in_app_notification(parent_id, 'spending_alert', notification_data)
            
        except Exception as e:
            logger.error(f"Failed to send spending alert: {e}")
    
    async def send_time_warning(self, child_id: str, minutes_remaining: int, daily_limit: int):
        """Send screen time warning"""
        try:
            parent_id = await self._get_parent_id(child_id)
            preferences = await self.get_notification_preferences(parent_id)
            
            if not preferences.time_limit_warnings:
                return
            
            child_name = await self._get_child_name(child_id)
            
            notification_data = {
                'child_name': child_name,
                'minutes_remaining': str(minutes_remaining),
                'daily_limit': str(daily_limit)
            }
            
            if preferences.push_enabled:
                await self._send_push_notification('time_warning', parent_id, notification_data)
            
            await self._create_in_app_notification(parent_id, 'time_warning', notification_data)
            
        except Exception as e:
            logger.error(f"Failed to send time warning: {e}")
    
    async def send_activity_alert(self, child_id: str, alert_type: str, alert_details: str):
        """Send activity alert to parent"""
        try:
            parent_id = await self._get_parent_id(child_id)
            preferences = await self.get_notification_preferences(parent_id)
            
            if not preferences.activity_alerts:
                return
            
            child_name = await self._get_child_name(child_id)
            parent_info = await self._get_parent_contact_info(parent_id)
            
            notification_data = {
                'child_name': child_name,
                'alert_type': alert_type,
                'alert_details': alert_details,
                'alert_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'dashboard_link': f"{self.config['base_url']}/parent-dashboard"
            }
            
            if preferences.email_enabled and parent_info.get('email'):
                await self._send_email_notification('activity_alert', parent_info['email'], notification_data)
            
            await self._create_in_app_notification(parent_id, 'activity_alert', notification_data)
            
        except Exception as e:
            logger.error(f"Failed to send activity alert: {e}")
    
    async def get_notification_preferences(self, parent_id: str) -> NotificationPreference:
        """Get parent notification preferences"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM notification_preferences WHERE parent_id = $1
            ''', parent_id)
            
            if row:
                return NotificationPreference(**dict(row))
            else:
                # Return default preferences
                return NotificationPreference(
                    parent_id=parent_id,
                    email_enabled=True,
                    sms_enabled=False,
                    push_enabled=True,
                    quiet_hours_start="22:00",
                    quiet_hours_end="08:00",
                    permission_notifications=True,
                    activity_alerts=True,
                    spending_alerts=True,
                    time_limit_warnings=True
                )
    
    async def update_notification_preferences(self, parent_id: str, preferences: Dict[str, Any]) -> bool:
        """Update parent notification preferences"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO notification_preferences 
                    (parent_id, email_enabled, sms_enabled, push_enabled,
                     quiet_hours_start, quiet_hours_end, permission_notifications,
                     activity_alerts, spending_alerts, time_limit_warnings, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (parent_id) DO UPDATE SET
                        email_enabled = EXCLUDED.email_enabled,
                        sms_enabled = EXCLUDED.sms_enabled,
                        push_enabled = EXCLUDED.push_enabled,
                        quiet_hours_start = EXCLUDED.quiet_hours_start,
                        quiet_hours_end = EXCLUDED.quiet_hours_end,
                        permission_notifications = EXCLUDED.permission_notifications,
                        activity_alerts = EXCLUDED.activity_alerts,
                        spending_alerts = EXCLUDED.spending_alerts,
                        time_limit_warnings = EXCLUDED.time_limit_warnings,
                        updated_at = EXCLUDED.updated_at
                ''',
                parent_id,
                preferences.get('email_enabled', True),
                preferences.get('sms_enabled', False),
                preferences.get('push_enabled', True),
                preferences.get('quiet_hours_start', '22:00'),
                preferences.get('quiet_hours_end', '08:00'),
                preferences.get('permission_notifications', True),
                preferences.get('activity_alerts', True),
                preferences.get('spending_alerts', True),
                preferences.get('time_limit_warnings', True),
                datetime.now()
                )
                return True
                
        except Exception as e:
            logger.error(f"Failed to update notification preferences: {e}")
            return False
    
    def _is_quiet_hours(self, preferences: NotificationPreference) -> bool:
        """Check if current time is within quiet hours"""
        now = datetime.now().time()
        start_time = datetime.strptime(preferences.quiet_hours_start, '%H:%M').time()
        end_time = datetime.strptime(preferences.quiet_hours_end, '%H:%M').time()
        
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:  # Quiet hours cross midnight
            return now >= start_time or now <= end_time
    
    async def _schedule_notification(self, notification_data: Dict[str, Any], template_id: str):
        """Schedule notification for after quiet hours"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO scheduled_notifications 
                (parent_id, template_id, notification_data, scheduled_for)
                VALUES ($1, $2, $3, $4)
            ''',
            notification_data['parent_id'],
            template_id,
            json.dumps(notification_data),
            datetime.now() + timedelta(hours=8)  # Schedule for 8 hours later
            )
    
    async def _send_email_notification(self, template_id: str, email: str, data: Dict[str, Any]):
        """Send email notification"""
        try:
            template = self.templates[template_id]
            
            # Format subject and body
            subject = template.subject_template.format(**data)
            body = template.body_template.format(**data)
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config['email']['from_address']
            msg['To'] = email
            
            # Add HTML body
            html_part = MIMEText(body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.config['email']['smtp_server'], self.config['email']['smtp_port']) as server:
                server.starttls()
                server.login(self.config['email']['username'], self.config['email']['password'])
                server.send_message(msg)
            
            logger.info(f"Email notification sent to {email}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    async def _send_sms_notification(self, template_id: str, phone: str, data: Dict[str, Any]):
        """Send SMS notification"""
        try:
            # This would integrate with SMS provider like Twilio
            logger.info(f"SMS notification would be sent to {phone}")
            # TODO: Implement actual SMS sending
            
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
    
    async def _send_push_notification(self, template_id: str, parent_id: str, data: Dict[str, Any]):
        """Send push notification"""
        try:
            # This would integrate with push notification service
            template = self.templates[template_id]
            title = template.subject_template.format(**data)
            
            logger.info(f"Push notification would be sent to parent {parent_id}: {title}")
            # TODO: Implement actual push notification
            
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
    
    async def _create_in_app_notification(self, parent_id: str, template_id: str, data: Dict[str, Any]):
        """Create in-app notification"""
        try:
            template = self.templates[template_id]
            title = template.subject_template.format(**data)
            
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO in_app_notifications 
                    (parent_id, title, template_id, notification_data, created_at, is_read)
                    VALUES ($1, $2, $3, $4, $5, $6)
                ''',
                parent_id, title, template_id, json.dumps(data), datetime.now(), False
                )
            
        except Exception as e:
            logger.error(f"Failed to create in-app notification: {e}")
    
    def _format_request_details(self, request_data: Dict[str, Any]) -> str:
        """Format request details for notification"""
        permission_type = request_data['permission_type']
        details = request_data.get('request_data', {})
        
        if permission_type == 'compute_quota':
            return f"Additional compute resources: {details.get('cpu_minutes', 0)} CPU minutes, {details.get('memory_mb', 0)} MB memory"
        elif permission_type == 'purchase':
            return f"Purchase ${details.get('amount', 0):.2f} in {details.get('category', 'unknown')} category"
        elif permission_type == 'extended_time':
            return f"Extended screen time: {details.get('extra_minutes', 0)} additional minutes"
        elif permission_type == 'project_share':
            return f"Share project '{details.get('project_name', 'Unknown')}' with {details.get('share_with', 'others')}"
        else:
            return str(details)
    
    async def _get_parent_id(self, child_id: str) -> str:
        """Get parent ID for a child"""
        async with self.db_pool.acquire() as conn:
            parent_id = await conn.fetchval('''
                SELECT parent_id FROM child_profiles WHERE child_id = $1
            ''', child_id)
            return parent_id
    
    async def _get_child_name(self, child_id: str) -> str:
        """Get child name"""
        async with self.db_pool.acquire() as conn:
            name = await conn.fetchval('''
                SELECT name FROM child_profiles WHERE child_id = $1
            ''', child_id)
            return name or "Unknown Child"
    
    async def _get_parent_contact_info(self, parent_id: str) -> Dict[str, str]:
        """Get parent contact information"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT email, phone FROM users WHERE id = $1
            ''', parent_id)
            
            if row:
                return {'email': row['email'], 'phone': row['phone']}
            else:
                return {}

class PermissionWorkflowEngine:
    """Manages permission request workflows"""
    
    def __init__(self, db_pool: asyncpg.Pool, notification_service: NotificationService):
        self.db_pool = db_pool
        self.notification_service = notification_service
    
    async def create_permission_request(self, child_id: str, permission_type: str,
                                      request_data: Dict[str, Any], reason: str) -> str:
        """Create a new permission request"""
        request_id = str(uuid.uuid4())
        
        # Get parent ID
        async with self.db_pool.acquire() as conn:
            parent_id = await conn.fetchval('''
                SELECT parent_id FROM child_profiles WHERE child_id = $1
            ''', child_id)
            
            if not parent_id:
                raise ValueError("Child profile not found")
            
            # Create request
            await conn.execute('''
                INSERT INTO permission_requests 
                (request_id, child_id, parent_id, permission_type, request_data, 
                 reason, status, requested_at, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''',
            request_id, child_id, parent_id, permission_type,
            json.dumps(request_data), reason, 'pending',
            datetime.now(), datetime.now() + timedelta(hours=24)
            )
        
        # Send notification
        await self.notification_service.send_permission_request_notification({
            'request_id': request_id,
            'child_id': child_id,
            'parent_id': parent_id,
            'permission_type': permission_type,
            'request_data': request_data,
            'reason': reason
        })
        
        return request_id
    
    async def approve_request(self, request_id: str, parent_id: str, response_reason: str = None) -> bool:
        """Approve a permission request"""
        return await self._respond_to_request(request_id, parent_id, True, response_reason)
    
    async def deny_request(self, request_id: str, parent_id: str, response_reason: str = None) -> bool:
        """Deny a permission request"""
        return await self._respond_to_request(request_id, parent_id, False, response_reason)
    
    async def _respond_to_request(self, request_id: str, parent_id: str, 
                                approved: bool, response_reason: str = None) -> bool:
        """Respond to a permission request"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get request details
                request = await conn.fetchrow('''
                    SELECT * FROM permission_requests 
                    WHERE request_id = $1 AND parent_id = $2
                ''', request_id, parent_id)
                
                if not request:
                    return False
                
                # Check if request is still valid
                if request['expires_at'] < datetime.now():
                    status = 'expired'
                else:
                    status = 'approved' if approved else 'denied'
                
                # Update request
                await conn.execute('''
                    UPDATE permission_requests 
                    SET status = $1, responded_at = $2, response_reason = $3
                    WHERE request_id = $4
                ''', status, datetime.now(), response_reason, request_id)
                
                # Apply permission if approved
                if approved and status == 'approved':
                    await self._apply_permission(request)
                
                # Send confirmation notification to child
                await self._notify_child_of_response(request, approved, response_reason)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to respond to permission request: {e}")
            return False
    
    async def _apply_permission(self, request: Dict[str, Any]):
        """Apply the approved permission"""
        permission_type = request['permission_type']
        request_data = json.loads(request['request_data'])
        child_id = request['child_id']
        
        async with self.db_pool.acquire() as conn:
            if permission_type == 'extended_time':
                # Grant extended time for today
                await conn.execute('''
                    INSERT INTO temporary_permissions 
                    (child_id, permission_type, permission_data, expires_at)
                    VALUES ($1, $2, $3, $4)
                ''',
                child_id, permission_type, json.dumps(request_data),
                datetime.now().replace(hour=23, minute=59, second=59)
                )
                
            elif permission_type == 'compute_quota':
                # Increase compute quota temporarily
                await conn.execute('''
                    INSERT INTO temporary_permissions 
                    (child_id, permission_type, permission_data, expires_at)
                    VALUES ($1, $2, $3, $4)
                ''',
                child_id, permission_type, json.dumps(request_data),
                datetime.now() + timedelta(hours=24)
                )
                
            elif permission_type == 'purchase':
                # Approve specific purchase
                purchase_id = request_data.get('purchase_id')
                if purchase_id:
                    await conn.execute('''
                        UPDATE purchases SET status = 'approved', approved_at = $1
                        WHERE purchase_id = $2 AND child_id = $3
                    ''', datetime.now(), purchase_id, child_id)
    
    async def _notify_child_of_response(self, request: Dict[str, Any], approved: bool, reason: str):
        """Notify child of parent's response"""
        try:
            async with self.db_pool.acquire() as conn:
                status_message = "approved" if approved else "denied"
                notification_title = f"Permission Request {status_message.title()}"
                notification_body = f"Your request for {request['permission_type'].replace('_', ' ')} has been {status_message}."
                
                if reason:
                    notification_body += f" Reason: {reason}"
                
                await conn.execute('''
                    INSERT INTO child_notifications 
                    (child_id, title, message, created_at, is_read)
                    VALUES ($1, $2, $3, $4, $5)
                ''',
                request['child_id'], notification_title, notification_body, datetime.now(), False
                )
                
        except Exception as e:
            logger.error(f"Failed to notify child of response: {e}")
    
    async def get_pending_requests(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get pending permission requests for a parent"""
        async with self.db_pool.acquire() as conn:
            requests = await conn.fetch('''
                SELECT pr.*, cp.name as child_name
                FROM permission_requests pr
                JOIN child_profiles cp ON pr.child_id = cp.child_id
                WHERE pr.parent_id = $1 AND pr.status = 'pending' 
                AND pr.expires_at > NOW()
                ORDER BY pr.requested_at DESC
            ''', parent_id)
            
            return [dict(request) for request in requests]
    
    async def get_request_history(self, parent_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get permission request history for a parent"""
        since_date = datetime.now() - timedelta(days=days)
        
        async with self.db_pool.acquire() as conn:
            requests = await conn.fetch('''
                SELECT pr.*, cp.name as child_name
                FROM permission_requests pr
                JOIN child_profiles cp ON pr.child_id = cp.child_id
                WHERE pr.parent_id = $1 AND pr.requested_at >= $2
                ORDER BY pr.requested_at DESC
            ''', parent_id, since_date)
            
            return [dict(request) for request in requests]
    
    async def expire_old_requests(self):
        """Expire old permission requests"""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute('''
                    UPDATE permission_requests 
                    SET status = 'expired' 
                    WHERE status = 'pending' AND expires_at < NOW()
                ''')
                
                # Extract number of updated rows
                updated_count = int(result.split()[-1]) if result.startswith('UPDATE') else 0
                
                if updated_count > 0:
                    logger.info(f"Expired {updated_count} old permission requests")
                    
        except Exception as e:
            logger.error(f"Failed to expire old requests: {e}")

def main():
    """Example usage"""
    async def test_permission_workflow():
        print("Permission workflow system example")
        
        # This would be initialized with actual database and config
        # notification_service = NotificationService(db_pool, config)
        # workflow_engine = PermissionWorkflowEngine(db_pool, notification_service)
        
        # Example workflow:
        # 1. Child requests permission
        # request_id = await workflow_engine.create_permission_request(
        #     "child123", "extended_time", {"extra_minutes": 30}, "Need to finish homework project"
        # )
        
        # 2. Parent receives notification
        # 3. Parent approves/denies request
        # await workflow_engine.approve_request(request_id, "parent123", "Okay, but only for homework")
        
    asyncio.run(test_permission_workflow())

if __name__ == '__main__':
    main()