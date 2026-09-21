#!/usr/bin/env python3
"""
ActiveLog Smart Notification Manager
Intelligent notification system with multiple channels and smart filtering
"""

import json
import boto3
import smtplib
import requests
import datetime
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from jinja2 import Template
import os
import argparse
import asyncio
import websockets
from pathlib import Path

# Colors for console output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Unicode symbols
SYMBOLS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'bell': '🔔',
    'mail': '📧',
    'slack': '💬',
    'sms': '📱',
    'webhook': '🔗'
}

class NotificationLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class NotificationChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"
    TEAMS = "teams"
    DISCORD = "discord"
    CONSOLE = "console"

@dataclass
class NotificationConfig:
    channel: NotificationChannel
    enabled: bool
    level_threshold: NotificationLevel
    config: Dict[str, Any]
    rate_limit: int = 10  # notifications per hour
    quiet_hours: Optional[Dict[str, str]] = None  # {"start": "22:00", "end": "08:00"}

@dataclass
class NotificationEvent:
    title: str
    message: str
    level: NotificationLevel
    category: str
    deployment_id: Optional[str] = None
    environment: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class NotificationResult:
    channel: NotificationChannel
    success: bool
    message: str
    timestamp: datetime.datetime

class SmartNotificationManager:
    def __init__(self, config_file: str = "notification_config.json"):
        self.config_file = config_file
        self.channels = {}
        self.rate_limits = {}
        self.notification_history = []
        
        # AWS clients
        self.sns = boto3.client('sns')
        self.ses = boto3.client('ses')
        
        # Load configuration
        self.load_configuration()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        print(f"{SYMBOLS['bell']} {Colors.OKBLUE}Smart Notification Manager initialized{Colors.ENDC}")

    def load_configuration(self):
        """Load notification configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    
                for channel_config in config_data.get('channels', []):
                    channel = NotificationChannel(channel_config['channel'])
                    self.channels[channel] = NotificationConfig(**channel_config)
                    
                print(f"{SYMBOLS['success']} {Colors.OKGREEN}Loaded configuration for {len(self.channels)} channels{Colors.ENDC}")
            else:
                self.create_default_configuration()
        except Exception as e:
            print(f"{SYMBOLS['error']} {Colors.FAIL}Error loading configuration: {e}{Colors.ENDC}")
            self.create_default_configuration()

    def create_default_configuration(self):
        """Create default notification configuration"""
        default_config = {
            "channels": [
                {
                    "channel": "email",
                    "enabled": False,
                    "level_threshold": "warning",
                    "rate_limit": 5,
                    "config": {
                        "smtp_server": "smtp.gmail.com",
                        "smtp_port": 587,
                        "sender_email": "your-email@domain.com",
                        "sender_password": "your-app-password",
                        "recipients": ["admin@domain.com"]
                    },
                    "quiet_hours": {
                        "start": "22:00",
                        "end": "08:00"
                    }
                },
                {
                    "channel": "slack",
                    "enabled": False,
                    "level_threshold": "error",
                    "rate_limit": 10,
                    "config": {
                        "webhook_url": "https://hooks.slack.com/services/...",
                        "channel": "#activelog-alerts",
                        "username": "ActiveLog Bot"
                    }
                },
                {
                    "channel": "sms",
                    "enabled": False,
                    "level_threshold": "critical",
                    "rate_limit": 3,
                    "config": {
                        "sns_topic_arn": "arn:aws:sns:us-west-2:123456789012:activelog-alerts"
                    }
                },
                {
                    "channel": "console",
                    "enabled": True,
                    "level_threshold": "info",
                    "rate_limit": 100,
                    "config": {}
                }
            ]
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
            
        print(f"{SYMBOLS['info']} {Colors.WARNING}Created default configuration: {self.config_file}{Colors.ENDC}")
        print(f"{Colors.WARNING}Please update the configuration with your actual credentials{Colors.ENDC}")

    def should_send_notification(self, channel: NotificationChannel, level: NotificationLevel) -> bool:
        """Check if notification should be sent based on rules"""
        if channel not in self.channels:
            return False
            
        config = self.channels[channel]
        
        # Check if channel is enabled
        if not config.enabled:
            return False
        
        # Check level threshold
        level_order = {
            NotificationLevel.DEBUG: 0,
            NotificationLevel.INFO: 1,
            NotificationLevel.WARNING: 2,
            NotificationLevel.ERROR: 3,
            NotificationLevel.CRITICAL: 4
        }
        
        if level_order[level] < level_order[config.level_threshold]:
            return False
        
        # Check rate limits
        now = datetime.datetime.now()
        hour_ago = now - datetime.timedelta(hours=1)
        
        if channel not in self.rate_limits:
            self.rate_limits[channel] = []
        
        # Clean old entries
        self.rate_limits[channel] = [
            ts for ts in self.rate_limits[channel] if ts > hour_ago
        ]
        
        if len(self.rate_limits[channel]) >= config.rate_limit:
            return False
        
        # Check quiet hours
        if config.quiet_hours and level != NotificationLevel.CRITICAL:
            current_time = now.strftime("%H:%M")
            start_time = config.quiet_hours.get("start", "22:00")
            end_time = config.quiet_hours.get("end", "08:00")
            
            if start_time <= current_time or current_time <= end_time:
                return False
        
        return True

    def send_email_notification(self, event: NotificationEvent, config: Dict[str, Any]) -> NotificationResult:
        """Send email notification"""
        try:
            smtp_server = config.get('smtp_server')
            smtp_port = config.get('smtp_port', 587)
            sender_email = config.get('sender_email')
            sender_password = config.get('sender_password')
            recipients = config.get('recipients', [])
            
            if not all([smtp_server, sender_email, sender_password, recipients]):
                return NotificationResult(
                    channel=NotificationChannel.EMAIL,
                    success=False,
                    message="Missing email configuration",
                    timestamp=datetime.datetime.now()
                )
            
            # Create email content
            subject = f"[ActiveLog {event.level.value.upper()}] {event.title}"
            
            email_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .header { background-color: {% if level == 'critical' %}#dc3545{% elif level == 'error' %}#fd7e14{% elif level == 'warning' %}#ffc107{% else %}#007bff{% endif %}; color: white; padding: 20px; border-radius: 5px; }
        .content { padding: 20px; background-color: #f8f9fa; margin: 10px 0; border-radius: 5px; }
        .metadata { background-color: #e9ecef; padding: 10px; border-radius: 3px; margin-top: 15px; }
        .footer { color: #6c757d; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h2>{{ symbols[level] }} {{ title }}</h2>
        <p>Level: {{ level.upper() }}</p>
    </div>
    
    <div class="content">
        <p>{{ message }}</p>
        
        {% if deployment_id %}
        <p><strong>Deployment ID:</strong> {{ deployment_id }}</p>
        {% endif %}
        
        {% if environment %}
        <p><strong>Environment:</strong> {{ environment }}</p>
        {% endif %}
        
        <p><strong>Category:</strong> {{ category }}</p>
        <p><strong>Timestamp:</strong> {{ timestamp }}</p>
    </div>
    
    {% if metadata %}
    <div class="metadata">
        <h4>Additional Information:</h4>
        {% for key, value in metadata.items() %}
        <p><strong>{{ key }}:</strong> {{ value }}</p>
        {% endfor %}
    </div>
    {% endif %}
    
    <div class="footer">
        <p>This is an automated notification from ActiveLog Deployment System.</p>
        <p>Dashboard: <a href="http://localhost:3001">http://localhost:3001</a></p>
    </div>
</body>
</html>
            """)
            
            level_symbols = {
                'critical': '🚨',
                'error': '❌',
                'warning': '⚠️',
                'info': 'ℹ️',
                'debug': '🔍'
            }
            
            html_content = email_template.render(
                title=event.title,
                message=event.message,
                level=event.level.value,
                symbols=level_symbols,
                category=event.category,
                deployment_id=event.deployment_id,
                environment=event.environment,
                timestamp=event.timestamp or datetime.datetime.now(),
                metadata=event.metadata
            )
            
            # Create message
            msg = MimeMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipients)
            
            # Add HTML content
            html_part = MimeText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                success=True,
                message=f"Email sent to {len(recipients)} recipients",
                timestamp=datetime.datetime.now()
            )
            
        except Exception as e:
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                success=False,
                message=f"Email send failed: {str(e)}",
                timestamp=datetime.datetime.now()
            )

    def send_slack_notification(self, event: NotificationEvent, config: Dict[str, Any]) -> NotificationResult:
        """Send Slack notification"""
        try:
            webhook_url = config.get('webhook_url')
            channel = config.get('channel', '#general')
            username = config.get('username', 'ActiveLog Bot')
            
            if not webhook_url:
                return NotificationResult(
                    channel=NotificationChannel.SLACK,
                    success=False,
                    message="Missing Slack webhook URL",
                    timestamp=datetime.datetime.now()
                )
            
            # Color coding based on level
            color_map = {
                NotificationLevel.CRITICAL: "#dc3545",
                NotificationLevel.ERROR: "#fd7e14",
                NotificationLevel.WARNING: "#ffc107",
                NotificationLevel.INFO: "#007bff",
                NotificationLevel.DEBUG: "#6c757d"
            }
            
            # Emoji mapping
            emoji_map = {
                NotificationLevel.CRITICAL: "🚨",
                NotificationLevel.ERROR: "❌",
                NotificationLevel.WARNING: "⚠️",
                NotificationLevel.INFO: "ℹ️",
                NotificationLevel.DEBUG: "🔍"
            }
            
            # Create Slack message
            payload = {
                "channel": channel,
                "username": username,
                "icon_emoji": ":rocket:",
                "attachments": [
                    {
                        "color": color_map.get(event.level, "#007bff"),
                        "title": f"{emoji_map.get(event.level, 'ℹ️')} {event.title}",
                        "text": event.message,
                        "fields": [
                            {
                                "title": "Level",
                                "value": event.level.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Category",
                                "value": event.category,
                                "short": True
                            }
                        ],
                        "footer": "ActiveLog Deployment System",
                        "ts": int((event.timestamp or datetime.datetime.now()).timestamp())
                    }
                ]
            }
            
            # Add deployment info if available
            if event.deployment_id:
                payload["attachments"][0]["fields"].append({
                    "title": "Deployment ID",
                    "value": event.deployment_id,
                    "short": True
                })
            
            if event.environment:
                payload["attachments"][0]["fields"].append({
                    "title": "Environment",
                    "value": event.environment.upper(),
                    "short": True
                })
            
            # Add metadata if available
            if event.metadata:
                for key, value in event.metadata.items():
                    if len(payload["attachments"][0]["fields"]) < 10:  # Slack limit
                        payload["attachments"][0]["fields"].append({
                            "title": key.replace('_', ' ').title(),
                            "value": str(value),
                            "short": True
                        })
            
            # Send to Slack
            response = requests.post(webhook_url, json=payload, timeout=30)
            response.raise_for_status()
            
            return NotificationResult(
                channel=NotificationChannel.SLACK,
                success=True,
                message=f"Slack notification sent to {channel}",
                timestamp=datetime.datetime.now()
            )
            
        except Exception as e:
            return NotificationResult(
                channel=NotificationChannel.SLACK,
                success=False,
                message=f"Slack send failed: {str(e)}",
                timestamp=datetime.datetime.now()
            )

    def send_sms_notification(self, event: NotificationEvent, config: Dict[str, Any]) -> NotificationResult:
        """Send SMS notification via AWS SNS"""
        try:
            sns_topic_arn = config.get('sns_topic_arn')
            
            if not sns_topic_arn:
                return NotificationResult(
                    channel=NotificationChannel.SMS,
                    success=False,
                    message="Missing SNS topic ARN",
                    timestamp=datetime.datetime.now()
                )
            
            # Create SMS message (160 character limit)
            emoji = "🚨" if event.level == NotificationLevel.CRITICAL else "⚠️"
            sms_message = f"{emoji} ActiveLog: {event.title} - {event.message[:100]}..."
            
            if event.deployment_id:
                sms_message += f" (Deploy: {event.deployment_id[:8]}...)"
            
            # Send SMS
            response = self.sns.publish(
                TopicArn=sns_topic_arn,
                Message=sms_message,
                Subject=f"ActiveLog {event.level.value.upper()}"
            )
            
            return NotificationResult(
                channel=NotificationChannel.SMS,
                success=True,
                message=f"SMS sent via SNS: {response['MessageId']}",
                timestamp=datetime.datetime.now()
            )
            
        except Exception as e:
            return NotificationResult(
                channel=NotificationChannel.SMS,
                success=False,
                message=f"SMS send failed: {str(e)}",
                timestamp=datetime.datetime.now()
            )

    def send_webhook_notification(self, event: NotificationEvent, config: Dict[str, Any]) -> NotificationResult:
        """Send generic webhook notification"""
        try:
            url = config.get('url')
            method = config.get('method', 'POST')
            headers = config.get('headers', {'Content-Type': 'application/json'})
            
            if not url:
                return NotificationResult(
                    channel=NotificationChannel.WEBHOOK,
                    success=False,
                    message="Missing webhook URL",
                    timestamp=datetime.datetime.now()
                )
            
            # Create webhook payload
            payload = {
                "title": event.title,
                "message": event.message,
                "level": event.level.value,
                "category": event.category,
                "deployment_id": event.deployment_id,
                "environment": event.environment,
                "timestamp": (event.timestamp or datetime.datetime.now()).isoformat(),
                "metadata": event.metadata
            }
            
            # Send webhook
            if method.upper() == 'POST':
                response = requests.post(url, json=payload, headers=headers, timeout=30)
            else:
                response = requests.get(url, params=payload, headers=headers, timeout=30)
            
            response.raise_for_status()
            
            return NotificationResult(
                channel=NotificationChannel.WEBHOOK,
                success=True,
                message=f"Webhook sent to {url}",
                timestamp=datetime.datetime.now()
            )
            
        except Exception as e:
            return NotificationResult(
                channel=NotificationChannel.WEBHOOK,
                success=False,
                message=f"Webhook send failed: {str(e)}",
                timestamp=datetime.datetime.now()
            )

    def send_console_notification(self, event: NotificationEvent, config: Dict[str, Any]) -> NotificationResult:
        """Send console notification (print to terminal)"""
        try:
            # Color coding
            color_map = {
                NotificationLevel.CRITICAL: Colors.FAIL,
                NotificationLevel.ERROR: Colors.FAIL,
                NotificationLevel.WARNING: Colors.WARNING,
                NotificationLevel.INFO: Colors.OKBLUE,
                NotificationLevel.DEBUG: Colors.OKCYAN
            }
            
            symbol_map = {
                NotificationLevel.CRITICAL: SYMBOLS['error'],
                NotificationLevel.ERROR: SYMBOLS['error'],
                NotificationLevel.WARNING: SYMBOLS['warning'],
                NotificationLevel.INFO: SYMBOLS['info'],
                NotificationLevel.DEBUG: SYMBOLS['info']
            }
            
            color = color_map.get(event.level, Colors.OKBLUE)
            symbol = symbol_map.get(event.level, SYMBOLS['info'])
            
            # Format timestamp
            timestamp = (event.timestamp or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
            
            # Print notification
            print(f"\n{color}{'='*60}{Colors.ENDC}")
            print(f"{color}{symbol} {Colors.BOLD}[{event.level.value.upper()}] {event.title}{Colors.ENDC}")
            print(f"{color}{'='*60}{Colors.ENDC}")
            print(f"{Colors.BOLD}Message:{Colors.ENDC} {event.message}")
            print(f"{Colors.BOLD}Category:{Colors.ENDC} {event.category}")
            print(f"{Colors.BOLD}Timestamp:{Colors.ENDC} {timestamp}")
            
            if event.deployment_id:
                print(f"{Colors.BOLD}Deployment ID:{Colors.ENDC} {event.deployment_id}")
            
            if event.environment:
                print(f"{Colors.BOLD}Environment:{Colors.ENDC} {event.environment}")
            
            if event.metadata:
                print(f"{Colors.BOLD}Additional Info:{Colors.ENDC}")
                for key, value in event.metadata.items():
                    print(f"  {key}: {value}")
            
            print(f"{color}{'='*60}{Colors.ENDC}\n")
            
            return NotificationResult(
                channel=NotificationChannel.CONSOLE,
                success=True,
                message="Console notification displayed",
                timestamp=datetime.datetime.now()
            )
            
        except Exception as e:
            return NotificationResult(
                channel=NotificationChannel.CONSOLE,
                success=False,
                message=f"Console notification failed: {str(e)}",
                timestamp=datetime.datetime.now()
            )

    def send_notification(self, event: NotificationEvent) -> List[NotificationResult]:
        """Send notification to all configured channels"""
        results = []
        
        # Set timestamp if not provided
        if not event.timestamp:
            event.timestamp = datetime.datetime.now()
        
        for channel, config in self.channels.items():
            if self.should_send_notification(channel, event.level):
                # Record rate limit
                self.rate_limits.setdefault(channel, []).append(datetime.datetime.now())
                
                # Send based on channel type
                if channel == NotificationChannel.EMAIL:
                    result = self.send_email_notification(event, config.config)
                elif channel == NotificationChannel.SLACK:
                    result = self.send_slack_notification(event, config.config)
                elif channel == NotificationChannel.SMS:
                    result = self.send_sms_notification(event, config.config)
                elif channel == NotificationChannel.WEBHOOK:
                    result = self.send_webhook_notification(event, config.config)
                elif channel == NotificationChannel.CONSOLE:
                    result = self.send_console_notification(event, config.config)
                else:
                    result = NotificationResult(
                        channel=channel,
                        success=False,
                        message=f"Unsupported channel: {channel}",
                        timestamp=datetime.datetime.now()
                    )
                
                results.append(result)
                
                # Log result
                if result.success:
                    self.logger.info(f"Notification sent via {channel.value}: {result.message}")
                else:
                    self.logger.error(f"Notification failed via {channel.value}: {result.message}")
        
        # Add to history
        self.notification_history.append({
            'event': asdict(event),
            'results': [asdict(r) for r in results],
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        return results

    def send_deployment_started(self, deployment_id: str, environment: str, domains: List[str]):
        """Send deployment started notification"""
        event = NotificationEvent(
            title="Deployment Started",
            message=f"ActiveLog deployment {deployment_id} has been initiated",
            level=NotificationLevel.INFO,
            category="deployment",
            deployment_id=deployment_id,
            environment=environment,
            metadata={
                "domains": ", ".join(domains),
                "status": "started"
            }
        )
        return self.send_notification(event)

    def send_deployment_completed(self, deployment_id: str, environment: str, duration: str):
        """Send deployment completed notification"""
        event = NotificationEvent(
            title="Deployment Completed Successfully",
            message=f"ActiveLog deployment {deployment_id} completed in {duration}",
            level=NotificationLevel.INFO,
            category="deployment",
            deployment_id=deployment_id,
            environment=environment,
            metadata={
                "duration": duration,
                "status": "completed"
            }
        )
        return self.send_notification(event)

    def send_deployment_failed(self, deployment_id: str, environment: str, error: str):
        """Send deployment failed notification"""
        event = NotificationEvent(
            title="Deployment Failed",
            message=f"ActiveLog deployment {deployment_id} failed: {error}",
            level=NotificationLevel.ERROR,
            category="deployment",
            deployment_id=deployment_id,
            environment=environment,
            metadata={
                "error": error,
                "status": "failed"
            }
        )
        return self.send_notification(event)

    def send_cost_alert(self, monthly_cost: float, threshold: float, environment: str):
        """Send cost threshold alert"""
        percentage = (monthly_cost / threshold * 100)
        level = NotificationLevel.CRITICAL if percentage > 150 else NotificationLevel.WARNING
        
        event = NotificationEvent(
            title="Cost Alert",
            message=f"Monthly cost ${monthly_cost:.2f} exceeds threshold ${threshold:.2f} ({percentage:.1f}%)",
            level=level,
            category="cost",
            environment=environment,
            metadata={
                "monthly_cost": monthly_cost,
                "threshold": threshold,
                "percentage": percentage
            }
        )
        return self.send_notification(event)

    def send_health_check_failed(self, service: str, environment: str, details: str):
        """Send health check failure notification"""
        event = NotificationEvent(
            title="Health Check Failed",
            message=f"Service {service} health check failed in {environment}",
            level=NotificationLevel.ERROR,
            category="health",
            environment=environment,
            metadata={
                "service": service,
                "details": details
            }
        )
        return self.send_notification(event)

    def send_security_alert(self, alert_type: str, details: str, environment: str):
        """Send security alert notification"""
        event = NotificationEvent(
            title=f"Security Alert: {alert_type}",
            message=f"Security issue detected: {details}",
            level=NotificationLevel.CRITICAL,
            category="security",
            environment=environment,
            metadata={
                "alert_type": alert_type,
                "details": details
            }
        )
        return self.send_notification(event)

    def test_notifications(self):
        """Test all configured notification channels"""
        print(f"{SYMBOLS['info']} {Colors.OKBLUE}Testing notification channels...{Colors.ENDC}")
        
        test_event = NotificationEvent(
            title="Notification Test",
            message="This is a test notification from ActiveLog deployment system",
            level=NotificationLevel.INFO,
            category="test",
            deployment_id="test-123",
            environment="test",
            metadata={
                "test_type": "channel_verification",
                "timestamp": datetime.datetime.now().isoformat()
            }
        )
        
        results = self.send_notification(test_event)
        
        print(f"\n{Colors.BOLD}Test Results:{Colors.ENDC}")
        for result in results:
            status = f"{SYMBOLS['success']} {Colors.OKGREEN}SUCCESS{Colors.ENDC}" if result.success else f"{SYMBOLS['error']} {Colors.FAIL}FAILED{Colors.ENDC}"
            print(f"  {result.channel.value}: {status} - {result.message}")
        
        return results

    def get_notification_history(self, limit: int = 50) -> List[Dict]:
        """Get recent notification history"""
        return self.notification_history[-limit:]

    def clear_notification_history(self):
        """Clear notification history"""
        self.notification_history.clear()
        print(f"{SYMBOLS['success']} {Colors.OKGREEN}Notification history cleared{Colors.ENDC}")

def main():
    parser = argparse.ArgumentParser(description='ActiveLog Smart Notification Manager')
    parser.add_argument('--config', '-c', default='notification_config.json', help='Configuration file path')
    parser.add_argument('--test', action='store_true', help='Test all notification channels')
    parser.add_argument('--send', help='Send a test notification with custom message')
    parser.add_argument('--level', choices=['debug', 'info', 'warning', 'error', 'critical'], 
                       default='info', help='Notification level for test message')
    parser.add_argument('--environment', '-e', default='test', help='Environment for test')
    parser.add_argument('--deployment-id', help='Deployment ID for test')
    
    args = parser.parse_args()
    
    try:
        manager = SmartNotificationManager(args.config)
        
        if args.test:
            manager.test_notifications()
        elif args.send:
            event = NotificationEvent(
                title="Custom Test Message",
                message=args.send,
                level=NotificationLevel(args.level),
                category="manual",
                deployment_id=args.deployment_id,
                environment=args.environment
            )
            results = manager.send_notification(event)
            print(f"\n{SYMBOLS['success']} {Colors.OKGREEN}Sent notification to {len(results)} channels{Colors.ENDC}")
        else:
            print("Use --test to test channels or --send 'message' to send a custom notification")
            
    except KeyboardInterrupt:
        print(f"\n{SYMBOLS['warning']} {Colors.WARNING}Notification manager interrupted{Colors.ENDC}")
    except Exception as e:
        print(f"{SYMBOLS['error']} {Colors.FAIL}Error: {e}{Colors.ENDC}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())