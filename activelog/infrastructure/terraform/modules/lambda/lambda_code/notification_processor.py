"""
Notification Processor Lambda Function
Handles notification processing for ActiveLog
"""

import json
import os
import boto3
import logging
from typing import Dict, Any, List
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ses_client = boto3.client('ses')
sns_client = boto3.client('sns')
secrets_client = boto3.client('secretsmanager')

def process_notification(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process notification requests from SQS
    """
    try:
        records = event.get('Records', [])
        results = []
        
        for record in records:
            try:
                # Parse message body
                message_body = json.loads(record['body'])
                notification_type = message_body.get('type')
                recipient = message_body.get('recipient')
                subject = message_body.get('subject')
                content = message_body.get('content')
                metadata = message_body.get('metadata', {})
                
                logger.info(f"Processing {notification_type} notification for {recipient}")
                
                # Route to appropriate notification handler
                if notification_type == 'email':
                    result = await send_email_notification(recipient, subject, content, metadata)
                elif notification_type == 'sms':
                    result = await send_sms_notification(recipient, content, metadata)
                elif notification_type == 'push':
                    result = await send_push_notification(recipient, subject, content, metadata)
                elif notification_type == 'in_app':
                    result = await send_in_app_notification(recipient, subject, content, metadata)
                else:
                    logger.warning(f"Unknown notification type: {notification_type}")
                    continue
                
                results.append({
                    'recipient': recipient,
                    'type': notification_type,
                    'result': result,
                    'status': 'sent' if result.get('success') else 'failed'
                })
                
                # Store notification in database
                await store_notification_record(notification_type, recipient, subject, content, result)
                
            except Exception as e:
                logger.error(f"Error processing notification: {e}")
                results.append({
                    'recipient': recipient if 'recipient' in locals() else 'unknown',
                    'type': notification_type if 'notification_type' in locals() else 'unknown',
                    'error': str(e),
                    'status': 'failed'
                })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {len(records)} notification(s)',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Error in notification processor: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process notifications'
            })
        }


async def send_email_notification(recipient: str, subject: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send email notification using Amazon SES
    """
    try:
        # Get sender email from environment or secrets
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@activelog.com')
        
        # Create email message
        if metadata.get('html_content'):
            # Send HTML email
            response = ses_client.send_email(
                Source=sender_email,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': content, 'Charset': 'UTF-8'},
                        'Text': {'Data': strip_html_tags(content), 'Charset': 'UTF-8'}
                    }
                }
            )
        else:
            # Send plain text email
            response = ses_client.send_email(
                Source=sender_email,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {'Text': {'Data': content, 'Charset': 'UTF-8'}}
                }
            )
        
        message_id = response['MessageId']
        logger.info(f"Email sent successfully to {recipient}, MessageId: {message_id}")
        
        return {
            'success': True,
            'message_id': message_id,
            'provider': 'ses',
            'sent_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending email to {recipient}: {e}")
        return {
            'success': False,
            'error': str(e),
            'provider': 'ses'
        }


async def send_sms_notification(recipient: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send SMS notification using Amazon SNS
    """
    try:
        # Send SMS via SNS
        response = sns_client.publish(
            PhoneNumber=recipient,
            Message=content,
            MessageAttributes={
                'AWS.SNS.SMS.SenderID': {
                    'DataType': 'String',
                    'StringValue': 'ActiveLog'
                },
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'
                }
            }
        )
        
        message_id = response['MessageId']
        logger.info(f"SMS sent successfully to {recipient}, MessageId: {message_id}")
        
        return {
            'success': True,
            'message_id': message_id,
            'provider': 'sns',
            'sent_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending SMS to {recipient}: {e}")
        return {
            'success': False,
            'error': str(e),
            'provider': 'sns'
        }


async def send_push_notification(recipient: str, subject: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send push notification using Amazon SNS
    """
    try:
        # Get the platform application ARN from metadata
        platform_arn = metadata.get('platform_arn')
        device_token = metadata.get('device_token', recipient)
        
        if not platform_arn:
            return {
                'success': False,
                'error': 'Platform ARN not provided',
                'provider': 'sns'
            }
        
        # Create platform endpoint
        endpoint_response = sns_client.create_platform_endpoint(
            PlatformApplicationArn=platform_arn,
            Token=device_token
        )
        
        endpoint_arn = endpoint_response['EndpointArn']
        
        # Prepare message payload
        message_payload = {
            'default': content,
            'APNS': json.dumps({
                'aps': {
                    'alert': {
                        'title': subject,
                        'body': content
                    },
                    'badge': metadata.get('badge', 1),
                    'sound': 'default'
                }
            }),
            'GCM': json.dumps({
                'data': {
                    'title': subject,
                    'body': content,
                    'click_action': metadata.get('click_action', '')
                }
            })
        }
        
        # Send push notification
        response = sns_client.publish(
            TargetArn=endpoint_arn,
            Message=json.dumps(message_payload),
            MessageStructure='json'
        )
        
        message_id = response['MessageId']
        logger.info(f"Push notification sent successfully to {recipient}, MessageId: {message_id}")
        
        return {
            'success': True,
            'message_id': message_id,
            'endpoint_arn': endpoint_arn,
            'provider': 'sns',
            'sent_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending push notification to {recipient}: {e}")
        return {
            'success': False,
            'error': str(e),
            'provider': 'sns'
        }


async def send_in_app_notification(recipient: str, subject: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send in-app notification (store in database for real-time display)
    """
    try:
        # Store notification in database for in-app display
        notification_data = {
            'user_id': recipient,
            'title': subject,
            'message': content,
            'type': metadata.get('notification_type', 'info'),
            'is_read': False,
            'created_at': datetime.now().isoformat(),
            'metadata': metadata
        }
        
        # This would insert into the notifications table
        # For now, we'll log the notification
        logger.info(f"In-app notification created for {recipient}: {notification_data}")
        
        # In a real implementation, you would:
        # 1. Connect to PostgreSQL
        # 2. Insert into notifications table
        # 3. Optionally trigger WebSocket notification for real-time updates
        
        return {
            'success': True,
            'notification_id': f"notif_{int(datetime.now().timestamp())}",
            'provider': 'in_app',
            'created_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating in-app notification for {recipient}: {e}")
        return {
            'success': False,
            'error': str(e),
            'provider': 'in_app'
        }


async def store_notification_record(notification_type: str, recipient: str, subject: str, content: str, result: Dict[str, Any]):
    """
    Store notification record in database for tracking
    """
    try:
        # Store notification record for auditing and tracking
        record = {
            'type': notification_type,
            'recipient': recipient,
            'subject': subject,
            'content': content,
            'success': result.get('success', False),
            'message_id': result.get('message_id'),
            'error': result.get('error'),
            'provider': result.get('provider'),
            'sent_at': result.get('sent_at', datetime.now().isoformat())
        }
        
        logger.info(f"Notification record stored: {record}")
        
        # In a real implementation, you would:
        # 1. Connect to PostgreSQL
        # 2. Insert into notification_logs table
        # 3. Handle any database errors
        
    except Exception as e:
        logger.error(f"Error storing notification record: {e}")


def strip_html_tags(html_content: str) -> str:
    """
    Strip HTML tags from content for plain text version
    """
    import re
    # Simple HTML tag removal
    clean = re.compile('<.*?>')
    return re.sub(clean, '', html_content)


def format_email_template(template_name: str, data: Dict[str, Any]) -> str:
    """
    Format email content using template
    """
    templates = {
        'welcome': """
        <h2>Welcome to ActiveLog!</h2>
        <p>Hello {name},</p>
        <p>Thank you for joining ActiveLog. Your account has been successfully created.</p>
        <p>You can now start uploading and organizing your files with our AI-powered platform.</p>
        <p>Best regards,<br>The ActiveLog Team</p>
        """,
        
        'file_processed': """
        <h2>File Processing Complete</h2>
        <p>Hello {name},</p>
        <p>Your file "{filename}" has been successfully processed and is now available in your ActiveLog account.</p>
        <p>Processing results:</p>
        <ul>
            <li>File size: {file_size}</li>
            <li>Processing time: {processing_time}</li>
            <li>Tags generated: {tags_count}</li>
        </ul>
        <p>You can view and search your file at: <a href="{file_url}">View File</a></p>
        <p>Best regards,<br>The ActiveLog Team</p>
        """,
        
        'password_reset': """
        <h2>Password Reset Request</h2>
        <p>Hello {name},</p>
        <p>We received a request to reset your password for your ActiveLog account.</p>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>This link will expire in 24 hours.</p>
        <p>If you didn't request this reset, please ignore this email.</p>
        <p>Best regards,<br>The ActiveLog Team</p>
        """
    }
    
    template = templates.get(template_name, "{content}")
    
    try:
        return template.format(**data)
    except KeyError as e:
        logger.warning(f"Missing template variable: {e}")
        return template


# Helper function for testing
def create_test_notification(notification_type: str = 'email') -> Dict[str, Any]:
    """
    Create a test notification for development/testing
    """
    test_notifications = {
        'email': {
            'type': 'email',
            'recipient': 'test@example.com',
            'subject': 'Test Email from ActiveLog',
            'content': 'This is a test email notification.',
            'metadata': {'html_content': False}
        },
        'sms': {
            'type': 'sms',
            'recipient': '+1234567890',
            'content': 'Test SMS from ActiveLog',
            'metadata': {}
        },
        'in_app': {
            'type': 'in_app',
            'recipient': 'user123',
            'subject': 'Test In-App Notification',
            'content': 'This is a test in-app notification.',
            'metadata': {'notification_type': 'info'}
        }
    }
    
    return test_notifications.get(notification_type, test_notifications['email'])