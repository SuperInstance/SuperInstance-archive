import asyncio
import logging
import json
import time
import smtplib
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import websockets
from jinja2 import Template

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertStatus(Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class NotificationChannel(Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    SMS = "sms"
    WEBSOCKET = "websocket"

@dataclass
class Alert:
    id: str
    title: str
    description: str
    severity: AlertSeverity
    source: str
    status: AlertStatus = AlertStatus.ACTIVE
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    escalation_level: int = 0
    suppress_until: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "source": self.source,
            "status": self.status.value,
            "tags": list(self.tags),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "escalation_level": self.escalation_level,
            "suppress_until": self.suppress_until.isoformat() if self.suppress_until else None
        }
    
    def is_suppressed(self) -> bool:
        """Check if alert is currently suppressed"""
        return (self.suppress_until is not None and 
                datetime.now() < self.suppress_until)

@dataclass
class NotificationRule:
    id: str
    name: str
    enabled: bool = True
    severity_filter: Set[AlertSeverity] = field(default_factory=lambda: {AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL})
    source_filter: Set[str] = field(default_factory=set)
    tag_filter: Set[str] = field(default_factory=set)
    channels: List[NotificationChannel] = field(default_factory=list)
    escalation_delay_minutes: int = 30
    max_escalations: int = 3
    quiet_hours: Optional[Dict[str, str]] = None  # {"start": "22:00", "end": "08:00"}
    rate_limit_minutes: int = 5
    
    def matches_alert(self, alert: Alert) -> bool:
        """Check if this rule matches the given alert"""
        if not self.enabled:
            return False
        
        # Check severity filter
        if self.severity_filter and alert.severity not in self.severity_filter:
            return False
        
        # Check source filter
        if self.source_filter and alert.source not in self.source_filter:
            return False
        
        # Check tag filter (any tag must match)
        if self.tag_filter and not self.tag_filter.intersection(alert.tags):
            return False
        
        # Check quiet hours
        if self.quiet_hours:
            current_time = datetime.now().time()
            start_time = datetime.strptime(self.quiet_hours["start"], "%H:%M").time()
            end_time = datetime.strptime(self.quiet_hours["end"], "%H:%M").time()
            
            if start_time <= end_time:  # Same day
                if start_time <= current_time <= end_time:
                    return False
            else:  # Crosses midnight
                if current_time >= start_time or current_time <= end_time:
                    return False
        
        return True

class EmailNotifier:
    def __init__(self, smtp_server: str, smtp_port: int, 
                 username: str, password: str, from_email: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        
        self.email_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        .alert { padding: 20px; margin: 10px 0; border-radius: 5px; }
        .critical { background-color: #ffebee; border-left: 5px solid #f44336; }
        .error { background-color: #fff3e0; border-left: 5px solid #ff9800; }
        .warning { background-color: #fffde7; border-left: 5px solid #fbc02d; }
        .info { background-color: #e8f5e8; border-left: 5px solid #4caf50; }
        .metadata { margin-top: 10px; padding: 10px; background-color: #f5f5f5; }
    </style>
</head>
<body>
    <div class="alert {{ severity }}">
        <h2>{{ title }}</h2>
        <p><strong>Severity:</strong> {{ severity.upper() }}</p>
        <p><strong>Source:</strong> {{ source }}</p>
        <p><strong>Time:</strong> {{ created_at }}</p>
        <p><strong>Description:</strong></p>
        <p>{{ description }}</p>
        
        {% if tags %}
        <p><strong>Tags:</strong> {{ tags | join(', ') }}</p>
        {% endif %}
        
        {% if metadata %}
        <div class="metadata">
            <strong>Additional Information:</strong>
            <ul>
            {% for key, value in metadata.items() %}
                <li><strong>{{ key }}:</strong> {{ value }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}
    </div>
</body>
</html>
        """)
    
    async def send_notification(self, alert: Alert, recipients: List[str]) -> bool:
        """Send email notification"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)
            
            # Generate HTML content
            html_content = self.email_template.render(
                title=alert.title,
                severity=alert.severity.value,
                source=alert.source,
                created_at=alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                description=alert.description,
                tags=list(alert.tags),
                metadata=alert.metadata
            )
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent for alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification for alert {alert.id}: {e}")
            return False

class WebhookNotifier:
    def __init__(self):
        self.session = None
    
    async def start(self):
        self.session = aiohttp.ClientSession()
    
    async def stop(self):
        if self.session:
            await self.session.close()
    
    async def send_notification(self, alert: Alert, webhook_urls: List[str]) -> bool:
        """Send webhook notification"""
        if not self.session:
            return False
        
        success_count = 0
        payload = {
            "alert": alert.to_dict(),
            "timestamp": datetime.now().isoformat(),
            "event_type": "alert_notification"
        }
        
        for url in webhook_urls:
            try:
                async with self.session.post(
                    url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status < 400:
                        success_count += 1
                        logger.debug(f"Webhook notification sent to {url}")
                    else:
                        logger.warning(f"Webhook notification failed to {url}: {response.status}")
            
            except Exception as e:
                logger.error(f"Failed to send webhook notification to {url}: {e}")
        
        return success_count > 0

class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session = None
    
    async def start(self):
        self.session = aiohttp.ClientSession()
    
    async def stop(self):
        if self.session:
            await self.session.close()
    
    async def send_notification(self, alert: Alert, channels: List[str] = None) -> bool:
        """Send Slack notification"""
        if not self.session:
            return False
        
        # Create Slack message
        color = {
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.ERROR: "warning", 
            AlertSeverity.WARNING: "warning",
            AlertSeverity.INFO: "good"
        }.get(alert.severity, "good")
        
        attachment = {
            "color": color,
            "title": alert.title,
            "text": alert.description,
            "fields": [
                {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                {"title": "Source", "value": alert.source, "short": True},
                {"title": "Status", "value": alert.status.value.upper(), "short": True},
                {"title": "Time", "value": alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'), "short": True}
            ],
            "footer": "Bot Orchestrator Alert System",
            "ts": int(alert.created_at.timestamp())
        }
        
        if alert.tags:
            attachment["fields"].append({
                "title": "Tags", 
                "value": ", ".join(alert.tags), 
                "short": False
            })
        
        payload = {
            "username": "Bot Orchestrator",
            "icon_emoji": ":warning:",
            "attachments": [attachment]
        }
        
        if channels:
            payload["channel"] = channels[0]  # Send to first channel specified
        
        try:
            async with self.session.post(
                self.webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info(f"Slack notification sent for alert {alert.id}")
                    return True
                else:
                    logger.error(f"Slack notification failed: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

class WebSocketNotifier:
    def __init__(self):
        self.connections = set()
        self.server = None
    
    async def start(self, host: str = "localhost", port: int = 8451):
        """Start WebSocket server for real-time notifications"""
        try:
            self.server = await websockets.serve(
                self.handle_connection, host, port
            )
            logger.info(f"WebSocket notification server started on {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
    
    async def stop(self):
        """Stop WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket notification server stopped")
    
    async def handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        self.connections.add(websocket)
        logger.info(f"New WebSocket connection: {websocket.remote_address}")
        
        try:
            await websocket.wait_closed()
        finally:
            self.connections.remove(websocket)
            logger.info(f"WebSocket connection closed: {websocket.remote_address}")
    
    async def send_notification(self, alert: Alert) -> bool:
        """Send notification to all connected WebSocket clients"""
        if not self.connections:
            return False
        
        message = json.dumps({
            "type": "alert",
            "alert": alert.to_dict(),
            "timestamp": datetime.now().isoformat()
        })
        
        # Send to all connected clients
        disconnected = set()
        for websocket in self.connections.copy():
            try:
                await websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(websocket)
            except Exception as e:
                logger.error(f"Failed to send WebSocket notification: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.connections -= disconnected
        
        success_count = len(self.connections) - len(disconnected)
        if success_count > 0:
            logger.debug(f"WebSocket notification sent to {success_count} clients")
        
        return success_count > 0

class AlertManager:
    def __init__(self):
        self.alerts = {}
        self.notification_rules = {}
        self.notification_history = deque(maxlen=10000)
        
        # Notifiers
        self.email_notifier = None
        self.webhook_notifier = WebhookNotifier()
        self.slack_notifier = None
        self.websocket_notifier = WebSocketNotifier()
        
        # Rate limiting
        self.notification_rate_limits = defaultdict(lambda: defaultdict(float))
        
        # Statistics
        self.stats = {
            "total_alerts": 0,
            "active_alerts": 0,
            "resolved_alerts": 0,
            "notifications_sent": 0,
            "escalations": 0
        }
        
        # Background tasks
        self.escalation_task = None
        self.cleanup_task = None
        self.running = False
        self.lock = threading.RLock()
    
    async def start(self, config: Dict[str, Any] = None):
        """Start alert manager"""
        config = config or {}
        
        self.running = True
        
        # Initialize notifiers
        if config.get("email"):
            email_config = config["email"]
            self.email_notifier = EmailNotifier(
                smtp_server=email_config["smtp_server"],
                smtp_port=email_config["smtp_port"],
                username=email_config["username"],
                password=email_config["password"],
                from_email=email_config["from_email"]
            )
        
        if config.get("slack"):
            self.slack_notifier = SlackNotifier(config["slack"]["webhook_url"])
            await self.slack_notifier.start()
        
        await self.webhook_notifier.start()
        
        # Start WebSocket server
        websocket_config = config.get("websocket", {})
        await self.websocket_notifier.start(
            host=websocket_config.get("host", "localhost"),
            port=websocket_config.get("port", 8451)
        )
        
        # Start background tasks
        self.escalation_task = asyncio.create_task(self._escalation_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Alert Manager started")
    
    async def stop(self):
        """Stop alert manager"""
        self.running = False
        
        # Stop background tasks
        for task in [self.escalation_task, self.cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Stop notifiers
        await self.webhook_notifier.stop()
        if self.slack_notifier:
            await self.slack_notifier.stop()
        await self.websocket_notifier.stop()
        
        logger.info("Alert Manager stopped")
    
    async def create_alert(self, title: str, description: str, 
                          severity: AlertSeverity, source: str,
                          tags: Set[str] = None, metadata: Dict[str, Any] = None) -> str:
        """Create a new alert"""
        alert_id = f"alert_{int(time.time() * 1000)}"
        
        alert = Alert(
            id=alert_id,
            title=title,
            description=description,
            severity=severity,
            source=source,
            tags=tags or set(),
            metadata=metadata or {}
        )
        
        with self.lock:
            self.alerts[alert_id] = alert
            self.stats["total_alerts"] += 1
            self.stats["active_alerts"] += 1
        
        # Send notifications
        await self._send_notifications(alert)
        
        logger.info(f"Alert created: {alert_id} - {title}")
        return alert_id
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        with self.lock:
            if alert_id not in self.alerts:
                return False
            
            alert = self.alerts[alert_id]
            if alert.status == AlertStatus.ACTIVE:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now()
                alert.acknowledged_by = acknowledged_by
                alert.updated_at = datetime.now()
                
                logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
                return True
            
            return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve an alert"""
        with self.lock:
            if alert_id not in self.alerts:
                return False
            
            alert = self.alerts[alert_id]
            if alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                alert.resolved_by = resolved_by
                alert.updated_at = datetime.now()
                
                self.stats["active_alerts"] -= 1
                self.stats["resolved_alerts"] += 1
                
                logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
                return True
            
            return False
    
    async def suppress_alert(self, alert_id: str, duration_minutes: int) -> bool:
        """Suppress an alert for a specified duration"""
        with self.lock:
            if alert_id not in self.alerts:
                return False
            
            alert = self.alerts[alert_id]
            alert.suppress_until = datetime.now() + timedelta(minutes=duration_minutes)
            alert.updated_at = datetime.now()
            
            logger.info(f"Alert suppressed: {alert_id} for {duration_minutes} minutes")
            return True
    
    def add_notification_rule(self, rule: NotificationRule):
        """Add a notification rule"""
        with self.lock:
            self.notification_rules[rule.id] = rule
            logger.info(f"Notification rule added: {rule.name}")
    
    def remove_notification_rule(self, rule_id: str) -> bool:
        """Remove a notification rule"""
        with self.lock:
            if rule_id in self.notification_rules:
                del self.notification_rules[rule_id]
                logger.info(f"Notification rule removed: {rule_id}")
                return True
            return False
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        if alert.is_suppressed():
            logger.debug(f"Alert {alert.id} is suppressed, skipping notifications")
            return
        
        # Find matching notification rules
        matching_rules = []
        with self.lock:
            for rule in self.notification_rules.values():
                if rule.matches_alert(alert):
                    matching_rules.append(rule)
        
        # Send notifications for each matching rule
        for rule in matching_rules:
            # Check rate limiting
            if not self._check_rate_limit(rule, alert):
                continue
            
            # Send notifications for each channel
            for channel in rule.channels:
                await self._send_channel_notification(alert, channel, rule)
    
    def _check_rate_limit(self, rule: NotificationRule, alert: Alert) -> bool:
        """Check if notification is within rate limits"""
        with self.lock:
            rule_key = f"{rule.id}:{alert.source}"
            last_notification = self.notification_rate_limits[rule_key]
            
            if last_notification.get("last_sent", 0) == 0:
                self.notification_rate_limits[rule_key]["last_sent"] = time.time()
                return True
            
            time_since_last = time.time() - last_notification["last_sent"]
            if time_since_last >= rule.rate_limit_minutes * 60:
                self.notification_rate_limits[rule_key]["last_sent"] = time.time()
                return True
            
            return False
    
    async def _send_channel_notification(self, alert: Alert, channel: NotificationChannel, rule: NotificationRule):
        """Send notification to a specific channel"""
        try:
            success = False
            
            if channel == NotificationChannel.EMAIL and self.email_notifier:
                recipients = rule.metadata.get("email_recipients", [])
                if recipients:
                    success = await self.email_notifier.send_notification(alert, recipients)
            
            elif channel == NotificationChannel.WEBHOOK:
                webhook_urls = rule.metadata.get("webhook_urls", [])
                if webhook_urls:
                    success = await self.webhook_notifier.send_notification(alert, webhook_urls)
            
            elif channel == NotificationChannel.SLACK and self.slack_notifier:
                slack_channels = rule.metadata.get("slack_channels", [])
                success = await self.slack_notifier.send_notification(alert, slack_channels)
            
            elif channel == NotificationChannel.WEBSOCKET:
                success = await self.websocket_notifier.send_notification(alert)
            
            if success:
                self.stats["notifications_sent"] += 1
                self.notification_history.append({
                    "alert_id": alert.id,
                    "rule_id": rule.id,
                    "channel": channel.value,
                    "timestamp": datetime.now(),
                    "success": True
                })
            
        except Exception as e:
            logger.error(f"Failed to send notification via {channel.value}: {e}")
            self.notification_history.append({
                "alert_id": alert.id,
                "rule_id": rule.id,
                "channel": channel.value,
                "timestamp": datetime.now(),
                "success": False,
                "error": str(e)
            })
    
    async def _escalation_loop(self):
        """Handle alert escalation"""
        while self.running:
            try:
                await self._process_escalations()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Escalation loop error: {e}")
                await asyncio.sleep(30)
    
    async def _process_escalations(self):
        """Process alert escalations"""
        current_time = datetime.now()
        
        with self.lock:
            for alert in self.alerts.values():
                if (alert.status == AlertStatus.ACTIVE and 
                    alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]):
                    
                    # Check if escalation is needed
                    time_since_created = (current_time - alert.created_at).total_seconds() / 60
                    
                    # Find applicable rules for escalation
                    for rule in self.notification_rules.values():
                        if (rule.matches_alert(alert) and 
                            alert.escalation_level < rule.max_escalations and
                            time_since_created >= rule.escalation_delay_minutes * (alert.escalation_level + 1)):
                            
                            alert.escalation_level += 1
                            self.stats["escalations"] += 1
                            
                            logger.warning(f"Escalating alert {alert.id} to level {alert.escalation_level}")
                            await self._send_notifications(alert)
                            break
    
    async def _cleanup_loop(self):
        """Cleanup resolved alerts and old data"""
        while self.running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Cleanup every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(1800)
    
    async def _cleanup_old_data(self):
        """Clean up old resolved alerts and notification history"""
        cutoff_time = datetime.now() - timedelta(days=7)
        
        with self.lock:
            # Remove old resolved alerts
            old_alerts = [
                alert_id for alert_id, alert in self.alerts.items()
                if (alert.status == AlertStatus.RESOLVED and 
                    alert.resolved_at and alert.resolved_at < cutoff_time)
            ]
            
            for alert_id in old_alerts:
                del self.alerts[alert_id]
            
            if old_alerts:
                logger.info(f"Cleaned up {len(old_alerts)} old resolved alerts")
            
            # Clean up old notification history
            old_history_cutoff = datetime.now() - timedelta(days=1)
            self.notification_history = deque(
                [entry for entry in self.notification_history 
                 if entry["timestamp"] > old_history_cutoff],
                maxlen=10000
            )
    
    def get_alerts(self, status: Optional[AlertStatus] = None, 
                   severity: Optional[AlertSeverity] = None,
                   source: Optional[str] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """Get alerts with optional filtering"""
        with self.lock:
            alerts = list(self.alerts.values())
            
            # Apply filters
            if status:
                alerts = [a for a in alerts if a.status == status]
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            if source:
                alerts = [a for a in alerts if a.source == source]
            
            # Sort by creation time (newest first)
            alerts.sort(key=lambda a: a.created_at, reverse=True)
            
            # Limit results
            alerts = alerts[:limit]
            
            return [alert.to_dict() for alert in alerts]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get alerting system statistics"""
        with self.lock:
            return {
                **self.stats,
                "notification_rules_count": len(self.notification_rules),
                "notification_history_count": len(self.notification_history),
                "rate_limits_active": len(self.notification_rate_limits)
            }
    
    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific alert"""
        with self.lock:
            if alert_id in self.alerts:
                return self.alerts[alert_id].to_dict()
            return None