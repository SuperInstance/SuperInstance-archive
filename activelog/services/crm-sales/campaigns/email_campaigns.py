"""
Email Campaigns System
Comprehensive email marketing and campaign management
"""

import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import re
import html
import threading
import time
from queue import Queue
import uuid


class CampaignType(Enum):
    """Email campaign types"""
    NEWSLETTER = "newsletter"
    PROMOTIONAL = "promotional"
    DRIP = "drip"
    FOLLOW_UP = "follow_up"
    NURTURE = "nurture"
    REACTIVATION = "reactivation"
    WEBINAR = "webinar"
    PRODUCT_ANNOUNCEMENT = "product_announcement"


class CampaignStatus(Enum):
    """Campaign status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class EmailStatus(Enum):
    """Individual email status"""
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    SPAM = "spam"


@dataclass
class EmailTemplate:
    """Email template data structure"""
    template_id: str
    name: str
    subject: str
    html_content: str
    text_content: str
    template_type: CampaignType
    variables: List[str]
    created_at: datetime
    

@dataclass
class Campaign:
    """Campaign data structure"""
    campaign_id: str
    name: str
    campaign_type: CampaignType
    subject: str
    template_id: str
    sender_name: str
    sender_email: str
    recipients_count: int
    status: CampaignStatus
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    created_at: datetime


class EmailCampaignSystem:
    """Email campaigns management system"""
    
    def __init__(self, db_path: str = "data/crm_sales.db", smtp_config: Dict[str, Any] = None):
        self.db_path = db_path
        self.smtp_config = smtp_config or {}
        self.send_queue = Queue()
        self.sending_thread = None
        self.is_sending = False
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new email template"""
        
        template_id = str(uuid.uuid4())
        
        # Extract variables from template content
        variables = self._extract_template_variables(
            template_data.get('html_content', '') + template_data.get('text_content', '')
        )
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO email_templates (
                    template_id, name, subject, html_content, text_content,
                    template_type, variables, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                template_id,
                template_data['name'],
                template_data['subject'],
                template_data.get('html_content', ''),
                template_data.get('text_content', ''),
                template_data.get('template_type', CampaignType.NEWSLETTER.value),
                json.dumps(variables),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()
            
            # Log activity
            self._log_activity('template_created', f"Template '{template_data['name']}' created", {
                'template_id': template_id
            })
            
            return {
                'template_id': template_id,
                'name': template_data['name'],
                'variables': variables,
                'created_at': datetime.utcnow().isoformat()
            }
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get email template by ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM email_templates 
                WHERE template_id = ?
            """, [template_id])
            
            result = cursor.fetchone()
            if result:
                return {
                    'template_id': result['template_id'],
                    'name': result['name'],
                    'subject': result['subject'],
                    'html_content': result['html_content'],
                    'text_content': result['text_content'],
                    'template_type': result['template_type'],
                    'variables': json.loads(result['variables']) if result['variables'] else [],
                    'created_at': result['created_at'],
                    'updated_at': result['updated_at']
                }
            return None
    
    def list_templates(self, template_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all email templates"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM email_templates"
            params = []
            
            if template_type:
                query += " WHERE template_type = ?"
                params.append(template_type)
                
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            templates = []
            for result in results:
                templates.append({
                    'template_id': result['template_id'],
                    'name': result['name'],
                    'subject': result['subject'],
                    'template_type': result['template_type'],
                    'variables': json.loads(result['variables']) if result['variables'] else [],
                    'created_at': result['created_at'],
                    'updated_at': result['updated_at']
                })
                
            return templates
    
    def create_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new email campaign"""
        
        campaign_id = str(uuid.uuid4())
        
        # Get recipient count
        recipients_count = len(campaign_data.get('recipients', []))
        if campaign_data.get('recipient_list_id'):
            recipients_count = self._get_list_size(campaign_data['recipient_list_id'])
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO email_campaigns (
                    campaign_id, name, campaign_type, subject, template_id,
                    sender_name, sender_email, recipients_count, recipient_list_id,
                    status, scheduled_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                campaign_id,
                campaign_data['name'],
                campaign_data.get('campaign_type', CampaignType.NEWSLETTER.value),
                campaign_data['subject'],
                campaign_data['template_id'],
                campaign_data.get('sender_name', 'CRM System'),
                campaign_data.get('sender_email', self.smtp_config.get('from_email')),
                recipients_count,
                campaign_data.get('recipient_list_id'),
                CampaignStatus.DRAFT.value,
                campaign_data.get('scheduled_at'),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            # Add recipients
            if 'recipients' in campaign_data:
                for recipient in campaign_data['recipients']:
                    self._add_campaign_recipient(cursor, campaign_id, recipient)
            
            conn.commit()
            
            # Log activity
            self._log_activity('campaign_created', f"Campaign '{campaign_data['name']}' created", {
                'campaign_id': campaign_id,
                'recipients_count': recipients_count
            })
            
            return {
                'campaign_id': campaign_id,
                'name': campaign_data['name'],
                'status': CampaignStatus.DRAFT.value,
                'recipients_count': recipients_count,
                'created_at': datetime.utcnow().isoformat()
            }
    
    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign by ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM email_campaigns 
                WHERE campaign_id = ?
            """, [campaign_id])
            
            result = cursor.fetchone()
            if result:
                # Get campaign stats
                stats = self._get_campaign_stats(cursor, campaign_id)
                
                return {
                    'campaign_id': result['campaign_id'],
                    'name': result['name'],
                    'campaign_type': result['campaign_type'],
                    'subject': result['subject'],
                    'template_id': result['template_id'],
                    'sender_name': result['sender_name'],
                    'sender_email': result['sender_email'],
                    'recipients_count': result['recipients_count'],
                    'status': result['status'],
                    'scheduled_at': result['scheduled_at'],
                    'sent_at': result['sent_at'],
                    'created_at': result['created_at'],
                    'stats': stats
                }
            return None
    
    def list_campaigns(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all campaigns"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT ec.*, et.name as template_name
                FROM email_campaigns ec
                LEFT JOIN email_templates et ON ec.template_id = et.template_id
            """
            params = []
            
            if status:
                query += " WHERE ec.status = ?"
                params.append(status)
                
            query += " ORDER BY ec.created_at DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            campaigns = []
            for result in results:
                stats = self._get_campaign_stats(cursor, result['campaign_id'])
                
                campaigns.append({
                    'campaign_id': result['campaign_id'],
                    'name': result['name'],
                    'campaign_type': result['campaign_type'],
                    'subject': result['subject'],
                    'template_name': result['template_name'],
                    'recipients_count': result['recipients_count'],
                    'status': result['status'],
                    'scheduled_at': result['scheduled_at'],
                    'sent_at': result['sent_at'],
                    'created_at': result['created_at'],
                    'stats': stats
                })
                
            return campaigns
    
    def schedule_campaign(self, campaign_id: str, scheduled_at: str) -> Dict[str, Any]:
        """Schedule a campaign for sending"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE email_campaigns 
                SET status = ?, scheduled_at = ?, updated_at = ?
                WHERE campaign_id = ?
            """, [
                CampaignStatus.SCHEDULED.value,
                scheduled_at,
                datetime.utcnow().isoformat(),
                campaign_id
            ])
            
            conn.commit()
            
            # Log activity
            self._log_activity('campaign_scheduled', f"Campaign {campaign_id} scheduled for {scheduled_at}", {
                'campaign_id': campaign_id,
                'scheduled_at': scheduled_at
            })
            
            return {
                'campaign_id': campaign_id,
                'status': CampaignStatus.SCHEDULED.value,
                'scheduled_at': scheduled_at
            }
    
    def send_campaign(self, campaign_id: str, send_immediately: bool = False) -> Dict[str, Any]:
        """Send campaign immediately or add to queue"""
        
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
            
        if campaign['status'] not in [CampaignStatus.DRAFT.value, CampaignStatus.SCHEDULED.value]:
            raise ValueError(f"Cannot send campaign with status: {campaign['status']}")
        
        # Update campaign status
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE email_campaigns 
                SET status = ?, sent_at = ?, updated_at = ?
                WHERE campaign_id = ?
            """, [
                CampaignStatus.SENDING.value,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                campaign_id
            ])
            
            conn.commit()
        
        if send_immediately:
            return self._send_campaign_now(campaign_id)
        else:
            # Add to queue
            self.send_queue.put(campaign_id)
            if not self.is_sending:
                self._start_sending_thread()
            
            return {
                'campaign_id': campaign_id,
                'status': 'queued',
                'message': 'Campaign added to sending queue'
            }
    
    def pause_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Pause a sending campaign"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE email_campaigns 
                SET status = ?, updated_at = ?
                WHERE campaign_id = ? AND status = ?
            """, [
                CampaignStatus.PAUSED.value,
                datetime.utcnow().isoformat(),
                campaign_id,
                CampaignStatus.SENDING.value
            ])
            
            conn.commit()
            
            if cursor.rowcount == 0:
                raise ValueError("Campaign not found or not in sending status")
            
            return {
                'campaign_id': campaign_id,
                'status': CampaignStatus.PAUSED.value
            }
    
    def get_campaign_analytics(self, campaign_id: str) -> Dict[str, Any]:
        """Get detailed campaign analytics"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get basic stats
            stats = self._get_campaign_stats(cursor, campaign_id)
            
            # Get click analytics
            cursor.execute("""
                SELECT url, COUNT(*) as click_count
                FROM email_clicks ec
                JOIN campaign_emails ce ON ec.email_id = ce.email_id
                WHERE ce.campaign_id = ?
                GROUP BY url
                ORDER BY click_count DESC
            """, [campaign_id])
            
            click_analytics = []
            for result in cursor.fetchall():
                click_analytics.append({
                    'url': result['url'],
                    'click_count': result['click_count']
                })
            
            # Get geographic analytics (if available)
            cursor.execute("""
                SELECT c.country, COUNT(*) as recipient_count
                FROM campaign_emails ce
                JOIN contacts c ON ce.contact_id = c.contact_id
                WHERE ce.campaign_id = ? AND c.country IS NOT NULL
                GROUP BY c.country
                ORDER BY recipient_count DESC
                LIMIT 10
            """, [campaign_id])
            
            geographic_data = []
            for result in cursor.fetchall():
                geographic_data.append({
                    'country': result['country'],
                    'recipient_count': result['recipient_count']
                })
            
            # Get engagement timeline
            cursor.execute("""
                SELECT 
                    DATE(sent_at) as date,
                    COUNT(CASE WHEN status = 'opened' THEN 1 END) as opens,
                    COUNT(CASE WHEN status = 'clicked' THEN 1 END) as clicks
                FROM campaign_emails
                WHERE campaign_id = ?
                GROUP BY DATE(sent_at)
                ORDER BY date
            """, [campaign_id])
            
            timeline_data = []
            for result in cursor.fetchall():
                timeline_data.append({
                    'date': result['date'],
                    'opens': result['opens'],
                    'clicks': result['clicks']
                })
            
            return {
                'campaign_id': campaign_id,
                'basic_stats': stats,
                'click_analytics': click_analytics,
                'geographic_data': geographic_data,
                'engagement_timeline': timeline_data,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def create_drip_campaign(self, drip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a drip campaign (sequence of emails)"""
        
        drip_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create drip campaign
            cursor.execute("""
                INSERT INTO drip_campaigns (
                    drip_id, name, description, trigger_event,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, [
                drip_id,
                drip_data['name'],
                drip_data.get('description', ''),
                drip_data['trigger_event'],
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            # Add drip steps
            for i, step in enumerate(drip_data['steps']):
                cursor.execute("""
                    INSERT INTO drip_steps (
                        drip_id, step_order, template_id, delay_days,
                        subject, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    drip_id,
                    i + 1,
                    step['template_id'],
                    step['delay_days'],
                    step['subject'],
                    datetime.utcnow().isoformat()
                ])
            
            conn.commit()
            
            return {
                'drip_id': drip_id,
                'name': drip_data['name'],
                'steps_count': len(drip_data['steps']),
                'created_at': datetime.utcnow().isoformat()
            }
    
    def trigger_drip_campaign(self, drip_id: str, contact_id: str, trigger_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Trigger drip campaign for a contact"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if contact is already in this drip
            cursor.execute("""
                SELECT * FROM drip_enrollments 
                WHERE drip_id = ? AND contact_id = ? AND status = 'active'
            """, [drip_id, contact_id])
            
            if cursor.fetchone():
                return {
                    'message': 'Contact already enrolled in this drip campaign',
                    'drip_id': drip_id,
                    'contact_id': contact_id
                }
            
            # Enroll contact
            enrollment_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO drip_enrollments (
                    enrollment_id, drip_id, contact_id, status,
                    enrolled_at, current_step, trigger_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                enrollment_id,
                drip_id,
                contact_id,
                'active',
                datetime.utcnow().isoformat(),
                1,
                json.dumps(trigger_data or {})
            ])
            
            conn.commit()
            
            # Schedule first step
            self._schedule_drip_step(drip_id, contact_id, 1)
            
            return {
                'enrollment_id': enrollment_id,
                'drip_id': drip_id,
                'contact_id': contact_id,
                'status': 'enrolled'
            }
    
    def process_scheduled_campaigns(self) -> Dict[str, Any]:
        """Process campaigns scheduled to be sent"""
        
        now = datetime.utcnow()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT campaign_id FROM email_campaigns 
                WHERE status = ? AND scheduled_at <= ?
            """, [CampaignStatus.SCHEDULED.value, now.isoformat()])
            
            campaigns = cursor.fetchall()
            
            processed = []
            for campaign in campaigns:
                try:
                    result = self.send_campaign(campaign['campaign_id'], send_immediately=True)
                    processed.append(result)
                except Exception as e:
                    processed.append({
                        'campaign_id': campaign['campaign_id'],
                        'status': 'error',
                        'error': str(e)
                    })
            
            return {
                'processed_campaigns': len(processed),
                'campaigns': processed
            }
    
    def handle_bounce(self, email_id: str, bounce_type: str, reason: str) -> Dict[str, Any]:
        """Handle email bounce"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Update email status
            cursor.execute("""
                UPDATE campaign_emails 
                SET status = ?, bounce_type = ?, bounce_reason = ?, updated_at = ?
                WHERE email_id = ?
            """, [
                EmailStatus.BOUNCED.value,
                bounce_type,
                reason,
                datetime.utcnow().isoformat(),
                email_id
            ])
            
            # If hard bounce, mark contact as bounced
            if bounce_type == 'hard':
                cursor.execute("""
                    UPDATE contacts 
                    SET email_status = 'bounced', updated_at = ?
                    WHERE contact_id = (
                        SELECT contact_id FROM campaign_emails WHERE email_id = ?
                    )
                """, [datetime.utcnow().isoformat(), email_id])
            
            conn.commit()
            
            return {
                'email_id': email_id,
                'status': 'bounce_processed',
                'bounce_type': bounce_type
            }
    
    def handle_unsubscribe(self, email_id: str, unsubscribe_reason: str = None) -> Dict[str, Any]:
        """Handle email unsubscribe"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get contact info
            cursor.execute("""
                SELECT contact_id FROM campaign_emails WHERE email_id = ?
            """, [email_id])
            
            result = cursor.fetchone()
            if not result:
                raise ValueError("Email not found")
                
            contact_id = result['contact_id']
            
            # Update email status
            cursor.execute("""
                UPDATE campaign_emails 
                SET status = ?, updated_at = ?
                WHERE email_id = ?
            """, [
                EmailStatus.UNSUBSCRIBED.value,
                datetime.utcnow().isoformat(),
                email_id
            ])
            
            # Add to unsubscribe list
            cursor.execute("""
                INSERT OR REPLACE INTO email_unsubscribes (
                    contact_id, email, unsubscribed_at, reason
                ) VALUES (
                    ?, 
                    (SELECT email FROM contacts WHERE contact_id = ?),
                    ?, ?
                )
            """, [
                contact_id,
                contact_id,
                datetime.utcnow().isoformat(),
                unsubscribe_reason
            ])
            
            # Update contact
            cursor.execute("""
                UPDATE contacts 
                SET email_status = 'unsubscribed', updated_at = ?
                WHERE contact_id = ?
            """, [datetime.utcnow().isoformat(), contact_id])
            
            conn.commit()
            
            return {
                'contact_id': contact_id,
                'status': 'unsubscribed',
                'unsubscribed_at': datetime.utcnow().isoformat()
            }
    
    def _extract_template_variables(self, content: str) -> List[str]:
        """Extract template variables from content"""
        
        # Find variables in {{variable}} format
        pattern = r'\{\{([^}]+)\}\}'
        variables = re.findall(pattern, content)
        
        # Clean up variable names
        variables = [var.strip() for var in variables]
        
        return list(set(variables))  # Remove duplicates
    
    def _add_campaign_recipient(self, cursor, campaign_id: str, recipient: Dict[str, Any]):
        """Add recipient to campaign"""
        
        email_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO campaign_emails (
                email_id, campaign_id, contact_id, email,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, [
            email_id,
            campaign_id,
            recipient.get('contact_id'),
            recipient['email'],
            EmailStatus.QUEUED.value,
            datetime.utcnow().isoformat()
        ])
    
    def _get_list_size(self, list_id: str) -> int:
        """Get size of recipient list"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM email_list_members 
                WHERE list_id = ?
            """, [list_id])
            
            result = cursor.fetchone()
            return result['count'] if result else 0
    
    def _get_campaign_stats(self, cursor, campaign_id: str) -> Dict[str, Any]:
        """Get campaign statistics"""
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sent,
                COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered,
                COUNT(CASE WHEN status = 'opened' THEN 1 END) as opened,
                COUNT(CASE WHEN status = 'clicked' THEN 1 END) as clicked,
                COUNT(CASE WHEN status = 'bounced' THEN 1 END) as bounced,
                COUNT(CASE WHEN status = 'unsubscribed' THEN 1 END) as unsubscribed
            FROM campaign_emails
            WHERE campaign_id = ?
        """, [campaign_id])
        
        result = cursor.fetchone()
        
        if result and result['total_sent'] > 0:
            return {
                'total_sent': result['total_sent'],
                'delivered': result['delivered'],
                'opened': result['opened'],
                'clicked': result['clicked'],
                'bounced': result['bounced'],
                'unsubscribed': result['unsubscribed'],
                'delivery_rate': (result['delivered'] / result['total_sent']) * 100,
                'open_rate': (result['opened'] / result['delivered']) * 100 if result['delivered'] > 0 else 0,
                'click_rate': (result['clicked'] / result['delivered']) * 100 if result['delivered'] > 0 else 0,
                'bounce_rate': (result['bounced'] / result['total_sent']) * 100,
                'unsubscribe_rate': (result['unsubscribed'] / result['total_sent']) * 100
            }
        
        return {
            'total_sent': 0,
            'delivered': 0,
            'opened': 0,
            'clicked': 0,
            'bounced': 0,
            'unsubscribed': 0,
            'delivery_rate': 0,
            'open_rate': 0,
            'click_rate': 0,
            'bounce_rate': 0,
            'unsubscribe_rate': 0
        }
    
    def _send_campaign_now(self, campaign_id: str) -> Dict[str, Any]:
        """Send campaign immediately"""
        
        # This is a simplified implementation
        # In production, you would integrate with actual SMTP services
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get campaign emails
            cursor.execute("""
                SELECT * FROM campaign_emails 
                WHERE campaign_id = ? AND status = ?
            """, [campaign_id, EmailStatus.QUEUED.value])
            
            emails = cursor.fetchall()
            sent_count = 0
            
            for email in emails:
                try:
                    # Simulate sending email
                    # In production: send via SMTP, SES, SendGrid, etc.
                    
                    cursor.execute("""
                        UPDATE campaign_emails 
                        SET status = ?, sent_at = ?, updated_at = ?
                        WHERE email_id = ?
                    """, [
                        EmailStatus.SENT.value,
                        datetime.utcnow().isoformat(),
                        datetime.utcnow().isoformat(),
                        email['email_id']
                    ])
                    
                    sent_count += 1
                    
                except Exception as e:
                    # Mark as failed
                    cursor.execute("""
                        UPDATE campaign_emails 
                        SET status = 'failed', updated_at = ?
                        WHERE email_id = ?
                    """, [datetime.utcnow().isoformat(), email['email_id']])
            
            # Update campaign status
            cursor.execute("""
                UPDATE email_campaigns 
                SET status = ?, updated_at = ?
                WHERE campaign_id = ?
            """, [
                CampaignStatus.SENT.value,
                datetime.utcnow().isoformat(),
                campaign_id
            ])
            
            conn.commit()
            
            return {
                'campaign_id': campaign_id,
                'status': 'sent',
                'emails_sent': sent_count,
                'total_emails': len(emails)
            }
    
    def _start_sending_thread(self):
        """Start background sending thread"""
        
        if self.sending_thread and self.sending_thread.is_alive():
            return
            
        self.is_sending = True
        self.sending_thread = threading.Thread(target=self._sending_worker)
        self.sending_thread.daemon = True
        self.sending_thread.start()
    
    def _sending_worker(self):
        """Background worker for sending campaigns"""
        
        while self.is_sending:
            try:
                if not self.send_queue.empty():
                    campaign_id = self.send_queue.get(timeout=1)
                    self._send_campaign_now(campaign_id)
                else:
                    time.sleep(5)  # Wait before checking again
            except Exception as e:
                # Log error and continue
                self._log_activity('sending_error', f"Error sending campaign: {str(e)}", {
                    'error': str(e)
                })
                time.sleep(5)
    
    def _schedule_drip_step(self, drip_id: str, contact_id: str, step_number: int):
        """Schedule a drip campaign step"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get step details
            cursor.execute("""
                SELECT * FROM drip_steps 
                WHERE drip_id = ? AND step_order = ?
            """, [drip_id, step_number])
            
            step = cursor.fetchone()
            if not step:
                return
            
            # Calculate send time
            send_at = datetime.utcnow() + timedelta(days=step['delay_days'])
            
            # Create scheduled email
            cursor.execute("""
                INSERT INTO scheduled_emails (
                    drip_id, contact_id, template_id, step_number,
                    scheduled_at, subject, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                drip_id,
                contact_id,
                step['template_id'],
                step_number,
                send_at.isoformat(),
                step['subject'],
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()
    
    def _log_activity(self, activity_type: str, description: str, metadata: Dict[str, Any]):
        """Log campaign activity"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO activities (
                    activity_type, description, metadata, created_at
                ) VALUES (?, ?, ?, ?)
            """, [
                activity_type,
                description,
                json.dumps(metadata),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()