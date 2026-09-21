"""
Email Service - Handles email notifications with multiple provider support
"""

import asyncio
import aiosmtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any
import json
import uuid

# Optional imports for different providers
try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_SES_AVAILABLE = True
except ImportError:
    AWS_SES_AVAILABLE = False

from ..core.config import settings
from ..core.database import DatabaseManager
from ..core.logging import logger

class EmailService:
    """Handles email notifications with multiple provider support"""
    
    def __init__(self, db_manager: DatabaseManager, template_service=None):
        self.db_manager = db_manager
        self.template_service = template_service
        
        # Provider instances
        self.smtp_configured = False
        self.sendgrid_client = None
        self.ses_client = None
        
        # Statistics
        self.stats = {
            "emails_sent": 0,
            "emails_failed": 0,
            "provider_stats": {},
            "last_sent": None,
            "service_start": datetime.now()
        }
        
        # Initialize providers
        self._initialize_providers()
        
        logger.info("Email service initialized")
    
    def _initialize_providers(self):
        """Initialize email providers based on configuration"""
        
        # Initialize SMTP
        if self._is_smtp_configured():
            self.smtp_configured = True
            self.stats["provider_stats"]["smtp"] = {"sent": 0, "failed": 0}
            logger.info("SMTP email provider configured")
        
        # Initialize SendGrid
        if SENDGRID_AVAILABLE and settings.SENDGRID_API_KEY:
            try:
                self.sendgrid_client = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
                self.stats["provider_stats"]["sendgrid"] = {"sent": 0, "failed": 0}
                logger.info("SendGrid email provider configured")
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid: {e}")
        
        # Initialize AWS SES
        if AWS_SES_AVAILABLE and settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            try:
                self.ses_client = boto3.client(
                    'ses',
                    region_name=settings.AWS_SES_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                self.stats["provider_stats"]["aws_ses"] = {"sent": 0, "failed": 0}
                logger.info("AWS SES email provider configured")
            except Exception as e:
                logger.error(f"Failed to initialize AWS SES: {e}")
    
    def _is_smtp_configured(self) -> bool:
        """Check if SMTP is properly configured"""
        return bool(
            settings.SMTP_HOST and 
            settings.SMTP_USERNAME and 
            settings.SMTP_PASSWORD
        )
    
    def is_configured(self) -> bool:
        """Check if at least one email provider is configured"""
        return (
            self.smtp_configured or 
            self.sendgrid_client is not None or 
            self.ses_client is not None
        )
    
    async def send_notification(self,
                               user_id: str,
                               to_email: str,
                               subject: str,
                               body: str,
                               tenant_id: Optional[str] = None,
                               template_id: Optional[str] = None,
                               template_vars: Optional[Dict] = None,
                               from_email: Optional[str] = None,
                               from_name: Optional[str] = None,
                               priority: str = "normal",
                               attachments: Optional[List[Dict]] = None) -> bool:
        """Send email notification"""
        
        try:
            # Generate notification ID
            notification_id = str(uuid.uuid4())
            
            # Process template if provided
            if template_id and self.template_service:
                template_result = await self.template_service.render_template(
                    template_id, template_vars or {}, "email"
                )
                if template_result:
                    subject = template_result.get("subject", subject)
                    body = template_result.get("body", body)
            
            # Set default from address
            if not from_email:
                from_email = settings.DEFAULT_FROM_EMAIL
            if not from_name:
                from_name = settings.DEFAULT_FROM_NAME
            
            # Log notification to database
            await self.db_manager.execute_command("""
                INSERT INTO email_notifications (
                    notification_id, user_id, tenant_id, to_email, from_email,
                    subject, body, template_id, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, 
                notification_id, user_id, tenant_id, to_email, from_email,
                subject, body, template_id, "pending"
            )
            
            # Send email using configured provider
            success = await self._send_email_with_fallback(
                notification_id=notification_id,
                to_email=to_email,
                subject=subject,
                body=body,
                from_email=from_email,
                from_name=from_name,
                attachments=attachments
            )
            
            # Update statistics
            if success:
                self.stats["emails_sent"] += 1
                self.stats["last_sent"] = datetime.now()
            else:
                self.stats["emails_failed"] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            self.stats["emails_failed"] += 1
            return False
    
    async def _send_email_with_fallback(self,
                                       notification_id: str,
                                       to_email: str,
                                       subject: str,
                                       body: str,
                                       from_email: str,
                                       from_name: str,
                                       attachments: Optional[List[Dict]] = None) -> bool:
        """Send email with provider fallback"""
        
        # Determine provider order
        providers = [settings.EMAIL_PROVIDER] + settings.EMAIL_FALLBACK_PROVIDERS
        providers = list(dict.fromkeys(providers))  # Remove duplicates while preserving order
        
        for provider in providers:
            try:
                success = False
                provider_message_id = None
                
                if provider == "sendgrid" and self.sendgrid_client:
                    success, provider_message_id = await self._send_with_sendgrid(
                        to_email, subject, body, from_email, from_name, attachments
                    )
                elif provider == "aws_ses" and self.ses_client:
                    success, provider_message_id = await self._send_with_ses(
                        to_email, subject, body, from_email, from_name, attachments
                    )
                elif provider == "smtp" and self.smtp_configured:
                    success, provider_message_id = await self._send_with_smtp(
                        to_email, subject, body, from_email, from_name, attachments
                    )
                else:
                    continue  # Provider not available
                
                if success:
                    # Update database with success
                    await self.db_manager.execute_command("""
                        UPDATE email_notifications 
                        SET status = 'sent', provider = $1, provider_message_id = $2, sent_at = NOW()
                        WHERE notification_id = $3
                    """, provider, provider_message_id, notification_id)
                    
                    # Update provider stats
                    if provider in self.stats["provider_stats"]:
                        self.stats["provider_stats"][provider]["sent"] += 1
                    
                    logger.debug(f"Email sent successfully via {provider}: {notification_id}")
                    return True
                    
            except Exception as e:
                logger.error(f"Error sending email via {provider}: {e}")
                
                # Update provider stats
                if provider in self.stats["provider_stats"]:
                    self.stats["provider_stats"][provider]["failed"] += 1
                
                continue  # Try next provider
        
        # All providers failed
        await self.db_manager.execute_command("""
            UPDATE email_notifications 
            SET status = 'failed', error_message = $1
            WHERE notification_id = $2
        """, "All email providers failed", notification_id)
        
        return False
    
    async def _send_with_smtp(self, 
                             to_email: str,
                             subject: str,
                             body: str,
                             from_email: str,
                             from_name: str,
                             attachments: Optional[List[Dict]] = None) -> tuple[bool, Optional[str]]:
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{from_name} <{from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'html' if '<html>' in body.lower() else 'plain'))
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Send email
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_USE_TLS,
                start_tls=not settings.SMTP_USE_SSL
            )
            
            return True, None
            
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return False, None
    
    async def _send_with_sendgrid(self,
                                 to_email: str,
                                 subject: str,
                                 body: str,
                                 from_email: str,
                                 from_name: str,
                                 attachments: Optional[List[Dict]] = None) -> tuple[bool, Optional[str]]:
        """Send email via SendGrid"""
        try:
            from_email_obj = Email(from_email, from_name)
            to_email_obj = To(to_email)
            
            # Determine content type
            content_type = "text/html" if '<html>' in body.lower() else "text/plain"
            content = Content(content_type, body)
            
            mail = Mail(from_email_obj, to_email_obj, subject, content)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    self._add_sendgrid_attachment(mail, attachment)
            
            # Send email
            response = self.sendgrid_client.send(mail)
            
            if response.status_code in [200, 201, 202]:
                message_id = response.headers.get('X-Message-Id')
                return True, message_id
            else:
                logger.error(f"SendGrid send failed with status {response.status_code}")
                return False, None
                
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            return False, None
    
    async def _send_with_ses(self,
                            to_email: str,
                            subject: str,
                            body: str,
                            from_email: str,
                            from_name: str,
                            attachments: Optional[List[Dict]] = None) -> tuple[bool, Optional[str]]:
        """Send email via AWS SES"""
        try:
            # For simple emails without attachments
            if not attachments:
                response = self.ses_client.send_email(
                    Source=f"{from_name} <{from_email}>",
                    Destination={'ToAddresses': [to_email]},
                    Message={
                        'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                        'Body': {
                            'Html': {'Data': body, 'Charset': 'UTF-8'} if '<html>' in body.lower() else {},
                            'Text': {'Data': body, 'Charset': 'UTF-8'} if '<html>' not in body.lower() else {}
                        }
                    }
                )
            else:
                # For emails with attachments, use raw email
                msg = MIMEMultipart()
                msg['From'] = f"{from_name} <{from_email}>"
                msg['To'] = to_email
                msg['Subject'] = subject
                
                msg.attach(MIMEText(body, 'html' if '<html>' in body.lower() else 'plain'))
                
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
                
                response = self.ses_client.send_raw_email(
                    Source=from_email,
                    Destinations=[to_email],
                    RawMessage={'Data': msg.as_string()}
                )
            
            message_id = response['MessageId']
            return True, message_id
            
        except ClientError as e:
            logger.error(f"AWS SES send failed: {e}")
            return False, None
        except Exception as e:
            logger.error(f"AWS SES send failed: {e}")
            return False, None
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict):
        """Add attachment to MIME message"""
        try:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['content'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment["filename"]}'
            )
            msg.attach(part)
        except Exception as e:
            logger.error(f"Error adding attachment: {e}")
    
    def _add_sendgrid_attachment(self, mail, attachment: Dict):
        """Add attachment to SendGrid mail object"""
        try:
            from sendgrid.helpers.mail import Attachment
            import base64
            
            encoded_content = base64.b64encode(attachment['content']).decode()
            
            mail_attachment = Attachment(
                file_content=encoded_content,
                file_name=attachment['filename'],
                file_type=attachment.get('content_type', 'application/octet-stream'),
                disposition='attachment'
            )
            
            mail.add_attachment(mail_attachment)
        except Exception as e:
            logger.error(f"Error adding SendGrid attachment: {e}")
    
    async def send_bulk_emails(self, notifications: List[Dict]) -> Dict[str, int]:
        """Send multiple emails in batch"""
        results = {"sent": 0, "failed": 0}
        
        # Process in batches to avoid overwhelming the providers
        batch_size = 10
        for i in range(0, len(notifications), batch_size):
            batch = notifications[i:i + batch_size]
            
            # Send batch concurrently
            tasks = []
            for notification in batch:
                task = self.send_notification(**notification)
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results["failed"] += 1
                elif result:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
            
            # Rate limiting pause
            if i + batch_size < len(notifications):
                await asyncio.sleep(1)
        
        return results
    
    async def retry_failed_emails(self, max_retries: int = 3) -> int:
        """Retry failed email notifications"""
        try:
            # Get failed emails that haven't exceeded retry limit
            failed_emails = await self.db_manager.execute_query("""
                SELECT notification_id, user_id, tenant_id, to_email, from_email,
                       subject, body, template_id, retry_count
                FROM email_notifications 
                WHERE status = 'failed' AND retry_count < $1
                ORDER BY created_at ASC
                LIMIT 50
            """, max_retries)
            
            retried_count = 0
            
            for email in failed_emails:
                # Increment retry count
                await self.db_manager.execute_command("""
                    UPDATE email_notifications 
                    SET retry_count = retry_count + 1, status = 'pending'
                    WHERE notification_id = $1
                """, email['notification_id'])
                
                # Retry sending
                success = await self._send_email_with_fallback(
                    notification_id=email['notification_id'],
                    to_email=email['to_email'],
                    subject=email['subject'],
                    body=email['body'],
                    from_email=email['from_email'],
                    from_name=settings.DEFAULT_FROM_NAME
                )
                
                if success:
                    retried_count += 1
            
            return retried_count
            
        except Exception as e:
            logger.error(f"Error retrying failed emails: {e}")
            return 0
    
    async def get_email_status(self, notification_id: str) -> Optional[Dict]:
        """Get status of an email notification"""
        try:
            result = await self.db_manager.execute_query("""
                SELECT notification_id, status, provider, provider_message_id,
                       error_message, retry_count, sent_at, created_at
                FROM email_notifications 
                WHERE notification_id = $1
            """, notification_id)
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error getting email status: {e}")
            return None
    
    async def get_stats(self) -> Dict:
        """Get email service statistics"""
        stats = self.stats.copy()
        stats["uptime_seconds"] = (datetime.now() - stats["service_start"]).total_seconds()
        stats["configured_providers"] = []
        
        if self.smtp_configured:
            stats["configured_providers"].append("smtp")
        if self.sendgrid_client:
            stats["configured_providers"].append("sendgrid")
        if self.ses_client:
            stats["configured_providers"].append("aws_ses")
        
        return stats