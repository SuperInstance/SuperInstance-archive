"""
Real-time Notifications and Alerts System
Comprehensive notification system with multiple delivery channels and smart alerting
"""

import asyncio
import json
import logging
import smtplib
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import threading
from collections import defaultdict, deque
import uuid
import os

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


class NotificationChannel(Enum):
    """Available notification channels"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    SMS = "sms"
    DESKTOP = "desktop"
    WEBSOCKET = "websocket"
    LOG = "log"


class NotificationType(Enum):
    """Types of notifications"""
    SYSTEM_ALERT = "system_alert"
    TASK_UPDATE = "task_update"
    BOT_STATUS = "bot_status"
    COLLABORATION_EVENT = "collaboration_event"
    PERFORMANCE_WARNING = "performance_warning"
    SECURITY_ALERT = "security_alert"
    RESOURCE_ALERT = "resource_alert"
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"


class AlertCondition(Enum):
    """Conditions that can trigger alerts"""
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    THRESHOLD_BELOW = "threshold_below"
    STATUS_CHANGE = "status_change"
    TIME_ELAPSED = "time_elapsed"
    COUNT_EXCEEDED = "count_exceeded"
    PATTERN_DETECTED = "pattern_detected"
    ANOMALY_DETECTED = "anomaly_detected"


@dataclass
class NotificationTemplate:
    """Template for notification formatting"""
    template_id: str
    name: str
    subject_template: str
    body_template: str
    channels: List[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.NORMAL
    variables: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Notification:
    """Individual notification"""
    notification_id: str
    notification_type: NotificationType
    priority: NotificationPriority
    subject: str
    message: str
    metadata: Dict[str, Any]
    channels: List[NotificationChannel]
    created_at: datetime
    recipient_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivery_status: Dict[NotificationChannel, str] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    expires_at: Optional[datetime] = None


@dataclass
class AlertRule:
    """Rule for triggering automatic alerts"""
    rule_id: str
    name: str
    condition: AlertCondition
    metric_name: str
    threshold_value: Any
    comparison_operator: str  # ">=", "<=", "==", "!=", "contains", etc.
    time_window_minutes: int
    notification_template_id: str
    enabled: bool = True
    cooldown_minutes: int = 30  # Prevent spam
    recipients: List[str] = field(default_factory=list)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


@dataclass
class NotificationRecipient:
    """Notification recipient configuration"""
    recipient_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    webhook_url: Optional[str] = None
    slack_webhook: Optional[str] = None
    discord_webhook: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    preferred_channels: List[NotificationChannel] = field(default_factory=list)
    notification_filters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    quiet_hours: Dict[str, str] = field(default_factory=dict)  # {"start": "22:00", "end": "08:00"}


class NotificationSystem:
    """Comprehensive real-time notification and alerting system"""
    
    def __init__(
        self,
        db_path: str = "/home/activeloguser/activelog/data/notifications.db",
        smtp_config: Optional[Dict[str, str]] = None,
        webhook_timeout: int = 10
    ):
        self.db_path = db_path
        self.smtp_config = smtp_config or {}
        self.webhook_timeout = webhook_timeout
        
        # Core components
        self.templates: Dict[str, NotificationTemplate] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.recipients: Dict[str, NotificationRecipient] = {}
        self.pending_notifications: deque = deque()
        self.sent_notifications: Dict[str, Notification] = {}
        
        # Real-time tracking
        self.metrics_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.websocket_connections: Set[Any] = set()
        self.notification_listeners: Dict[str, List[Callable]] = defaultdict(list)
        
        # Processing state
        self.processing_lock = threading.RLock()
        self.running = False
        self.processor_task = None
        self.alert_evaluator_task = None
        
        # Rate limiting
        self.rate_limits: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.max_notifications_per_hour = 50
        
        # Initialize database and default templates
        self._init_database()
        self._create_default_templates()
        self.start_background_tasks()
    
    def _init_database(self):
        """Initialize SQLite database for persistent storage"""
        with sqlite3.connect(self.db_path) as conn:
            # Notification templates
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_templates (
                    template_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    subject_template TEXT NOT NULL,
                    body_template TEXT NOT NULL,
                    channels TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    variables TEXT,
                    conditions TEXT
                )
            """)
            
            # Alert rules
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    threshold_value TEXT NOT NULL,
                    comparison_operator TEXT NOT NULL,
                    time_window_minutes INTEGER NOT NULL,
                    notification_template_id TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL,
                    cooldown_minutes INTEGER NOT NULL,
                    recipients TEXT,
                    last_triggered TEXT,
                    trigger_count INTEGER DEFAULT 0
                )
            """)
            
            # Recipients
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_recipients (
                    recipient_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    webhook_url TEXT,
                    slack_webhook TEXT,
                    discord_webhook TEXT,
                    telegram_chat_id TEXT,
                    preferred_channels TEXT,
                    notification_filters TEXT,
                    enabled BOOLEAN NOT NULL,
                    quiet_hours TEXT
                )
            """)
            
            # Notification history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_history (
                    notification_id TEXT PRIMARY KEY,
                    notification_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata TEXT,
                    channels TEXT NOT NULL,
                    recipient_id TEXT,
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    delivery_status TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            
            # Metrics for alert evaluation
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name_time ON notification_metrics(metric_name, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_created ON notification_history(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_type ON notification_history(notification_type)")
    
    def _create_default_templates(self):
        """Create default notification templates"""
        default_templates = [
            NotificationTemplate(
                template_id="system_alert_critical",
                name="Critical System Alert",
                subject_template="🚨 CRITICAL: {alert_title}",
                body_template="Critical system alert detected:\n\n{message}\n\nTimestamp: {timestamp}\nSystem: {system_name}\n\nImmediate attention required!",
                channels=[NotificationChannel.EMAIL, NotificationChannel.WEBHOOK, NotificationChannel.WEBSOCKET],
                priority=NotificationPriority.CRITICAL,
                variables=["alert_title", "message", "timestamp", "system_name"]
            ),
            NotificationTemplate(
                template_id="task_completed",
                name="Task Completion",
                subject_template="✅ Task Completed: {task_id}",
                body_template="Task has been completed successfully:\n\nTask ID: {task_id}\nDescription: {description}\nBot: {bot_id}\nDuration: {duration}\nCost: ${cost}",
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.LOG],
                priority=NotificationPriority.NORMAL,
                variables=["task_id", "description", "bot_id", "duration", "cost"]
            ),
            NotificationTemplate(
                template_id="bot_offline",
                name="Bot Offline Alert",
                subject_template="⚠️ Bot Offline: {bot_id}",
                body_template="Bot has gone offline:\n\nBot ID: {bot_id}\nLast seen: {last_seen}\nActive tasks: {active_tasks}\n\nPlease investigate.",
                channels=[NotificationChannel.EMAIL, NotificationChannel.WEBSOCKET],
                priority=NotificationPriority.HIGH,
                variables=["bot_id", "last_seen", "active_tasks"]
            ),
            NotificationTemplate(
                template_id="collaboration_failed",
                name="Collaboration Failure",
                subject_template="❌ Collaboration Failed: {session_id}",
                body_template="Multi-bot collaboration has failed:\n\nSession ID: {session_id}\nPattern: {pattern}\nParticipating bots: {bots}\nFailure reason: {reason}\n\nFailover initiated.",
                channels=[NotificationChannel.EMAIL, NotificationChannel.WEBHOOK, NotificationChannel.WEBSOCKET],
                priority=NotificationPriority.HIGH,
                variables=["session_id", "pattern", "bots", "reason"]
            ),
            NotificationTemplate(
                template_id="performance_degraded",
                name="Performance Degradation",
                subject_template="📉 Performance Alert: {metric_name}",
                body_template="System performance has degraded:\n\nMetric: {metric_name}\nCurrent value: {current_value}\nThreshold: {threshold}\nTime window: {time_window}\n\nOptimization recommended.",
                channels=[NotificationChannel.EMAIL, NotificationChannel.WEBSOCKET],
                priority=NotificationPriority.HIGH,
                variables=["metric_name", "current_value", "threshold", "time_window"]
            ),
            NotificationTemplate(
                template_id="cost_alert",
                name="Cost Threshold Alert",
                subject_template="💰 Cost Alert: Budget threshold exceeded",
                body_template="Cost threshold has been exceeded:\n\nCurrent spend: ${current_cost}\nThreshold: ${threshold}\nTime period: {period}\nTop expensive operations: {top_operations}",
                channels=[NotificationChannel.EMAIL, NotificationChannel.WEBHOOK],
                priority=NotificationPriority.HIGH,
                variables=["current_cost", "threshold", "period", "top_operations"]
            )
        ]
        
        for template in default_templates:
            self.templates[template.template_id] = template
            self._persist_template(template)
    
    def start_background_tasks(self):
        """Start background processing tasks"""
        if not self.running:
            self.running = True
            self.processor_task = threading.Thread(target=self._notification_processor, daemon=True)
            self.alert_evaluator_task = threading.Thread(target=self._alert_evaluator, daemon=True)
            self.processor_task.start()
            self.alert_evaluator_task.start()
    
    def stop_background_tasks(self):
        """Stop background tasks"""
        self.running = False
        if self.processor_task:
            self.processor_task.join(timeout=5)
        if self.alert_evaluator_task:
            self.alert_evaluator_task.join(timeout=5)
    
    def add_template(self, template: NotificationTemplate) -> bool:
        """Add a new notification template"""
        try:
            self.templates[template.template_id] = template
            self._persist_template(template)
            return True
        except Exception as e:
            logger.error(f"Error adding template: {e}")
            return False
    
    def add_recipient(self, recipient: NotificationRecipient) -> bool:
        """Add a new notification recipient"""
        try:
            self.recipients[recipient.recipient_id] = recipient
            self._persist_recipient(recipient)
            return True
        except Exception as e:
            logger.error(f"Error adding recipient: {e}")
            return False
    
    def add_alert_rule(self, rule: AlertRule) -> bool:
        """Add a new alert rule"""
        try:
            self.alert_rules[rule.rule_id] = rule
            self._persist_alert_rule(rule)
            return True
        except Exception as e:
            logger.error(f"Error adding alert rule: {e}")
            return False
    
    def send_notification(
        self,
        notification_type: NotificationType,
        subject: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[NotificationChannel]] = None,
        recipient_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        template_id: Optional[str] = None,
        template_variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send a notification"""
        notification_id = str(uuid.uuid4())
        
        # Use template if provided
        if template_id and template_id in self.templates:
            template = self.templates[template_id]
            variables = template_variables or {}
            
            try:
                subject = template.subject_template.format(**variables)
                message = template.body_template.format(**variables)
                channels = channels or template.channels
                priority = template.priority
            except KeyError as e:
                logger.error(f"Missing template variable: {e}")
                return ""
        
        # Create notification
        notification = Notification(
            notification_id=notification_id,
            notification_type=notification_type,
            priority=priority,
            subject=subject,
            message=message,
            metadata=metadata or {},
            channels=channels or [NotificationChannel.WEBSOCKET],
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24)  # Default 24h expiry
        )
        
        # Add to processing queue for each recipient
        if recipient_ids:
            for recipient_id in recipient_ids:
                recipient_notification = Notification(**asdict(notification))
                recipient_notification.notification_id = str(uuid.uuid4())
                recipient_notification.recipient_id = recipient_id
                self.pending_notifications.append(recipient_notification)
        else:
            # Broadcast notification
            self.pending_notifications.append(notification)
        
        return notification_id
    
    def send_alert(
        self,
        alert_title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.HIGH,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send a system alert using the default critical template"""
        return self.send_notification(
            notification_type=NotificationType.SYSTEM_ALERT,
            subject="",  # Will be overridden by template
            message="",  # Will be overridden by template
            priority=priority,
            template_id="system_alert_critical" if priority == NotificationPriority.CRITICAL else "system_alert_critical",
            template_variables={
                "alert_title": alert_title,
                "message": message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "system_name": "Multi-Bot Orchestrator",
                **(metadata or {})
            }
        )
    
    def record_metric(self, metric_name: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        """Record a metric value for alert evaluation"""
        timestamp = datetime.now()
        
        # Add to buffer for real-time evaluation
        self.metrics_buffer[metric_name].append((timestamp, value, metadata or {}))
        
        # Persist to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO notification_metrics (metric_name, metric_value, timestamp, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                metric_name,
                value,
                timestamp.isoformat(),
                json.dumps(metadata) if metadata else None
            ))
    
    def add_websocket_connection(self, websocket):
        """Add WebSocket connection for real-time notifications"""
        self.websocket_connections.add(websocket)
    
    def remove_websocket_connection(self, websocket):
        """Remove WebSocket connection"""
        self.websocket_connections.discard(websocket)
    
    def add_notification_listener(self, event_type: str, callback: Callable):
        """Add listener for notification events"""
        self.notification_listeners[event_type].append(callback)
    
    def _notification_processor(self):
        """Background task to process pending notifications"""
        while self.running:
            try:
                if self.pending_notifications:
                    with self.processing_lock:
                        notification = self.pending_notifications.popleft()
                    
                    asyncio.run(self._process_notification(notification))
                else:
                    # No notifications to process
                    import time
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in notification processor: {e}")
                import time
                time.sleep(5)
    
    async def _process_notification(self, notification: Notification):
        """Process a single notification"""
        try:
            # Check rate limiting
            if not self._check_rate_limit(notification):
                logger.warning(f"Rate limit exceeded for notification {notification.notification_id}")
                return
            
            # Check quiet hours if recipient specified
            if notification.recipient_id and not self._check_quiet_hours(notification):
                # Reschedule for later
                self.pending_notifications.append(notification)
                return
            
            # Process each channel
            delivery_results = {}
            
            for channel in notification.channels:
                try:
                    success = await self._deliver_notification(notification, channel)
                    delivery_results[channel] = "delivered" if success else "failed"
                except Exception as e:
                    logger.error(f"Error delivering to {channel}: {e}")
                    delivery_results[channel] = f"error: {str(e)}"
            
            # Update delivery status
            notification.delivery_status = delivery_results
            notification.sent_at = datetime.now()
            
            # Store in sent notifications
            self.sent_notifications[notification.notification_id] = notification
            
            # Persist to database
            self._persist_notification(notification)
            
            # Notify listeners
            await self._notify_listeners("notification_sent", {
                "notification_id": notification.notification_id,
                "type": notification.notification_type.value,
                "delivery_status": delivery_results
            })
            
        except Exception as e:
            logger.error(f"Error processing notification {notification.notification_id}: {e}")
            
            # Retry logic
            if notification.retry_count < notification.max_retries:
                notification.retry_count += 1
                self.pending_notifications.append(notification)
    
    async def _deliver_notification(self, notification: Notification, channel: NotificationChannel) -> bool:
        """Deliver notification through specific channel"""
        try:
            if channel == NotificationChannel.EMAIL:
                return await self._send_email(notification)
            elif channel == NotificationChannel.WEBHOOK:
                return await self._send_webhook(notification)
            elif channel == NotificationChannel.SLACK:
                return await self._send_slack(notification)
            elif channel == NotificationChannel.DISCORD:
                return await self._send_discord(notification)
            elif channel == NotificationChannel.WEBSOCKET:
                return await self._send_websocket(notification)
            elif channel == NotificationChannel.LOG:
                return self._log_notification(notification)
            else:
                logger.warning(f"Unsupported notification channel: {channel}")
                return False
                
        except Exception as e:
            logger.error(f"Error delivering notification via {channel}: {e}")
            return False
    
    async def _send_email(self, notification: Notification) -> bool:
        """Send notification via email"""
        if not self.smtp_config or not notification.recipient_id:
            return False
        
        recipient = self.recipients.get(notification.recipient_id)
        if not recipient or not recipient.email:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config.get('from_email', '')
            msg['To'] = recipient.email
            msg['Subject'] = notification.subject
            
            body = MIMEText(notification.message, 'plain')
            msg.attach(body)
            
            server = smtplib.SMTP(self.smtp_config.get('smtp_host', ''), int(self.smtp_config.get('smtp_port', 587)))
            server.starttls()
            server.login(self.smtp_config.get('username', ''), self.smtp_config.get('password', ''))
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def _send_webhook(self, notification: Notification) -> bool:
        """Send notification via webhook"""
        webhook_url = None
        
        if notification.recipient_id:
            recipient = self.recipients.get(notification.recipient_id)
            if recipient:
                webhook_url = recipient.webhook_url
        
        if not webhook_url:
            # Use system default webhook if configured
            webhook_url = os.getenv('DEFAULT_WEBHOOK_URL')
        
        if not webhook_url:
            return False
        
        try:
            payload = {
                "notification_id": notification.notification_id,
                "type": notification.notification_type.value,
                "priority": notification.priority.value,
                "subject": notification.subject,
                "message": notification.message,
                "timestamp": notification.created_at.isoformat(),
                "metadata": notification.metadata
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=self.webhook_timeout,
                headers={"Content-Type": "application/json"}
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            return False
    
    async def _send_slack(self, notification: Notification) -> bool:
        """Send notification via Slack webhook"""
        slack_webhook = None
        
        if notification.recipient_id:
            recipient = self.recipients.get(notification.recipient_id)
            if recipient:
                slack_webhook = recipient.slack_webhook
        
        if not slack_webhook:
            return False
        
        try:
            # Map priority to Slack colors
            color_map = {
                NotificationPriority.LOW: "#36a64f",      # Green
                NotificationPriority.NORMAL: "#2eb886",   # Teal
                NotificationPriority.HIGH: "#ff9500",     # Orange
                NotificationPriority.CRITICAL: "#ff0000", # Red
                NotificationPriority.URGENT: "#8b0000"    # Dark Red
            }
            
            payload = {
                "attachments": [{
                    "color": color_map.get(notification.priority, "#2eb886"),
                    "title": notification.subject,
                    "text": notification.message,
                    "fields": [
                        {
                            "title": "Priority",
                            "value": notification.priority.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Type",
                            "value": notification.notification_type.value.replace("_", " ").title(),
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": notification.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                            "short": False
                        }
                    ],
                    "footer": "Multi-Bot Orchestrator",
                    "ts": int(notification.created_at.timestamp())
                }]
            }
            
            response = requests.post(
                slack_webhook,
                json=payload,
                timeout=self.webhook_timeout
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False
    
    async def _send_discord(self, notification: Notification) -> bool:
        """Send notification via Discord webhook"""
        discord_webhook = None
        
        if notification.recipient_id:
            recipient = self.recipients.get(notification.recipient_id)
            if recipient:
                discord_webhook = recipient.discord_webhook
        
        if not discord_webhook:
            return False
        
        try:
            # Map priority to Discord colors
            color_map = {
                NotificationPriority.LOW: 0x36a64f,      # Green
                NotificationPriority.NORMAL: 0x2eb886,   # Teal
                NotificationPriority.HIGH: 0xff9500,     # Orange
                NotificationPriority.CRITICAL: 0xff0000, # Red
                NotificationPriority.URGENT: 0x8b0000    # Dark Red
            }
            
            payload = {
                "embeds": [{
                    "title": notification.subject,
                    "description": notification.message,
                    "color": color_map.get(notification.priority, 0x2eb886),
                    "fields": [
                        {
                            "name": "Priority",
                            "value": notification.priority.value.upper(),
                            "inline": True
                        },
                        {
                            "name": "Type",
                            "value": notification.notification_type.value.replace("_", " ").title(),
                            "inline": True
                        }
                    ],
                    "timestamp": notification.created_at.isoformat(),
                    "footer": {
                        "text": "Multi-Bot Orchestrator"
                    }
                }]
            }
            
            response = requests.post(
                discord_webhook,
                json=payload,
                timeout=self.webhook_timeout
            )
            
            return response.status_code == 204  # Discord returns 204 for success
            
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False
    
    async def _send_websocket(self, notification: Notification) -> bool:
        """Send notification via WebSocket connections"""
        if not self.websocket_connections:
            return False
        
        try:
            payload = {
                "type": "notification",
                "data": {
                    "notification_id": notification.notification_id,
                    "notification_type": notification.notification_type.value,
                    "priority": notification.priority.value,
                    "subject": notification.subject,
                    "message": notification.message,
                    "timestamp": notification.created_at.isoformat(),
                    "metadata": notification.metadata
                }
            }
            
            # Send to all active WebSocket connections
            disconnected = set()
            for websocket in self.websocket_connections:
                try:
                    # This would depend on your WebSocket implementation
                    # await websocket.send_text(json.dumps(payload))
                    pass  # Placeholder
                except:
                    disconnected.add(websocket)
            
            # Remove disconnected WebSockets
            self.websocket_connections -= disconnected
            
            return len(self.websocket_connections) > len(disconnected)
            
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")
            return False
    
    def _log_notification(self, notification: Notification) -> bool:
        """Log notification to system logs"""
        try:
            log_level = {
                NotificationPriority.LOW: logging.INFO,
                NotificationPriority.NORMAL: logging.INFO,
                NotificationPriority.HIGH: logging.WARNING,
                NotificationPriority.CRITICAL: logging.ERROR,
                NotificationPriority.URGENT: logging.CRITICAL
            }.get(notification.priority, logging.INFO)
            
            logger.log(
                log_level,
                f"[{notification.notification_type.value.upper()}] {notification.subject}: {notification.message}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging notification: {e}")
            return False
    
    def _alert_evaluator(self):
        """Background task to evaluate alert rules"""
        while self.running:
            try:
                current_time = datetime.now()
                
                for rule in self.alert_rules.values():
                    if not rule.enabled:
                        continue
                    
                    # Check cooldown
                    if rule.last_triggered:
                        time_since_trigger = current_time - rule.last_triggered
                        if time_since_trigger.total_seconds() < rule.cooldown_minutes * 60:
                            continue
                    
                    # Evaluate rule condition
                    if self._evaluate_alert_rule(rule, current_time):
                        self._trigger_alert(rule, current_time)
                
                # Sleep before next evaluation
                import time
                time.sleep(30)  # Evaluate every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in alert evaluator: {e}")
                import time
                time.sleep(60)
    
    def _evaluate_alert_rule(self, rule: AlertRule, current_time: datetime) -> bool:
        """Evaluate if an alert rule should trigger"""
        try:
            # Get metric values within time window
            window_start = current_time - timedelta(minutes=rule.time_window_minutes)
            
            if rule.metric_name not in self.metrics_buffer:
                return False
            
            # Filter values within time window
            relevant_values = [
                (timestamp, value, metadata) 
                for timestamp, value, metadata in self.metrics_buffer[rule.metric_name]
                if timestamp >= window_start
            ]
            
            if not relevant_values:
                return False
            
            # Apply condition logic
            if rule.condition == AlertCondition.THRESHOLD_EXCEEDED:
                latest_value = relevant_values[-1][1]
                return self._compare_values(latest_value, rule.threshold_value, rule.comparison_operator)
            
            elif rule.condition == AlertCondition.THRESHOLD_BELOW:
                latest_value = relevant_values[-1][1]
                return self._compare_values(latest_value, rule.threshold_value, rule.comparison_operator)
            
            elif rule.condition == AlertCondition.COUNT_EXCEEDED:
                count = len(relevant_values)
                return count > float(rule.threshold_value)
            
            elif rule.condition == AlertCondition.ANOMALY_DETECTED:
                # Simple anomaly detection based on standard deviation
                values = [v[1] for v in relevant_values]
                if len(values) < 3:
                    return False
                
                import statistics
                mean = statistics.mean(values)
                stdev = statistics.stdev(values)
                latest_value = values[-1]
                
                # Trigger if latest value is more than 2 standard deviations away
                return abs(latest_value - mean) > 2 * stdev
            
            else:
                logger.warning(f"Unsupported alert condition: {rule.condition}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating alert rule {rule.rule_id}: {e}")
            return False
    
    def _compare_values(self, value: float, threshold: Any, operator: str) -> bool:
        """Compare values based on operator"""
        threshold_float = float(threshold)
        
        if operator == ">=":
            return value >= threshold_float
        elif operator == "<=":
            return value <= threshold_float
        elif operator == "==":
            return abs(value - threshold_float) < 0.001  # Float comparison tolerance
        elif operator == "!=":
            return abs(value - threshold_float) >= 0.001
        elif operator == ">":
            return value > threshold_float
        elif operator == "<":
            return value < threshold_float
        else:
            logger.warning(f"Unsupported comparison operator: {operator}")
            return False
    
    def _trigger_alert(self, rule: AlertRule, current_time: datetime):
        """Trigger an alert rule"""
        try:
            rule.last_triggered = current_time
            rule.trigger_count += 1
            
            # Get recent metric value for context
            recent_value = None
            if rule.metric_name in self.metrics_buffer and self.metrics_buffer[rule.metric_name]:
                recent_value = self.metrics_buffer[rule.metric_name][-1][1]
            
            # Send notification using template
            self.send_notification(
                notification_type=NotificationType.SYSTEM_ALERT,
                subject="",  # Will be filled by template
                message="",  # Will be filled by template
                priority=NotificationPriority.HIGH,
                recipient_ids=rule.recipients,
                template_id=rule.notification_template_id,
                template_variables={
                    "rule_name": rule.name,
                    "metric_name": rule.metric_name,
                    "current_value": recent_value,
                    "threshold": rule.threshold_value,
                    "time_window": f"{rule.time_window_minutes} minutes",
                    "trigger_count": rule.trigger_count,
                    "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
                }
            )
            
            # Update rule in database
            self._persist_alert_rule(rule)
            
        except Exception as e:
            logger.error(f"Error triggering alert for rule {rule.rule_id}: {e}")
    
    def _check_rate_limit(self, notification: Notification) -> bool:
        """Check if notification exceeds rate limits"""
        try:
            current_time = datetime.now()
            hour_ago = current_time - timedelta(hours=1)
            
            key = f"{notification.notification_type.value}_{notification.recipient_id or 'broadcast'}"
            
            # Remove old entries
            while self.rate_limits[key] and self.rate_limits[key][0] < hour_ago:
                self.rate_limits[key].popleft()
            
            # Check if under limit
            if len(self.rate_limits[key]) >= self.max_notifications_per_hour:
                return False
            
            # Add current notification
            self.rate_limits[key].append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    def _check_quiet_hours(self, notification: Notification) -> bool:
        """Check if notification should be sent during quiet hours"""
        if not notification.recipient_id:
            return True
        
        recipient = self.recipients.get(notification.recipient_id)
        if not recipient or not recipient.quiet_hours:
            return True
        
        try:
            current_time = datetime.now().time()
            quiet_start = datetime.strptime(recipient.quiet_hours.get("start", "22:00"), "%H:%M").time()
            quiet_end = datetime.strptime(recipient.quiet_hours.get("end", "08:00"), "%H:%M").time()
            
            # Handle quiet hours spanning midnight
            if quiet_start > quiet_end:
                return not (current_time >= quiet_start or current_time <= quiet_end)
            else:
                return not (quiet_start <= current_time <= quiet_end)
                
        except Exception as e:
            logger.error(f"Error checking quiet hours: {e}")
            return True  # Allow on error
    
    async def _notify_listeners(self, event_type: str, data: Dict[str, Any]):
        """Notify event listeners"""
        for callback in self.notification_listeners[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in notification listener: {e}")
    
    def _persist_template(self, template: NotificationTemplate):
        """Persist template to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO notification_templates 
                (template_id, name, subject_template, body_template, channels, priority, variables, conditions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template.template_id,
                template.name,
                template.subject_template,
                template.body_template,
                json.dumps([c.value for c in template.channels]),
                template.priority.value,
                json.dumps(template.variables),
                json.dumps(template.conditions)
            ))
    
    def _persist_recipient(self, recipient: NotificationRecipient):
        """Persist recipient to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO notification_recipients 
                (recipient_id, name, email, phone, webhook_url, slack_webhook, discord_webhook, 
                 telegram_chat_id, preferred_channels, notification_filters, enabled, quiet_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recipient.recipient_id,
                recipient.name,
                recipient.email,
                recipient.phone,
                recipient.webhook_url,
                recipient.slack_webhook,
                recipient.discord_webhook,
                recipient.telegram_chat_id,
                json.dumps([c.value for c in recipient.preferred_channels]),
                json.dumps(recipient.notification_filters),
                recipient.enabled,
                json.dumps(recipient.quiet_hours)
            ))
    
    def _persist_alert_rule(self, rule: AlertRule):
        """Persist alert rule to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO alert_rules 
                (rule_id, name, condition, metric_name, threshold_value, comparison_operator,
                 time_window_minutes, notification_template_id, enabled, cooldown_minutes,
                 recipients, last_triggered, trigger_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.rule_id,
                rule.name,
                rule.condition.value,
                rule.metric_name,
                str(rule.threshold_value),
                rule.comparison_operator,
                rule.time_window_minutes,
                rule.notification_template_id,
                rule.enabled,
                rule.cooldown_minutes,
                json.dumps(rule.recipients),
                rule.last_triggered.isoformat() if rule.last_triggered else None,
                rule.trigger_count
            ))
    
    def _persist_notification(self, notification: Notification):
        """Persist notification to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO notification_history 
                (notification_id, notification_type, priority, subject, message, metadata,
                 channels, recipient_id, created_at, sent_at, delivery_status, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notification.notification_id,
                notification.notification_type.value,
                notification.priority.value,
                notification.subject,
                notification.message,
                json.dumps(notification.metadata),
                json.dumps([c.value for c in notification.channels]),
                notification.recipient_id,
                notification.created_at.isoformat(),
                notification.sent_at.isoformat() if notification.sent_at else None,
                json.dumps({k.value: v for k, v in notification.delivery_status.items()}),
                notification.retry_count
            ))
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification system statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total notifications sent
                cursor.execute("SELECT COUNT(*) FROM notification_history")
                total_sent = cursor.fetchone()[0]
                
                # Notifications by type
                cursor.execute("""
                    SELECT notification_type, COUNT(*) 
                    FROM notification_history 
                    GROUP BY notification_type
                """)
                by_type = dict(cursor.fetchall())
                
                # Recent notifications (last hour)
                hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) FROM notification_history 
                    WHERE created_at > ?
                """, (hour_ago,))
                recent_count = cursor.fetchone()[0]
            
            return {
                "total_notifications_sent": total_sent,
                "notifications_by_type": by_type,
                "recent_notifications_last_hour": recent_count,
                "pending_notifications": len(self.pending_notifications),
                "active_websocket_connections": len(self.websocket_connections),
                "active_alert_rules": len([r for r in self.alert_rules.values() if r.enabled]),
                "registered_recipients": len(self.recipients)
            }
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {}


# Convenience functions for common use cases
def create_default_notification_system() -> NotificationSystem:
    """Create notification system with sensible defaults"""
    return NotificationSystem()

def send_critical_alert(system: NotificationSystem, title: str, message: str, metadata: Optional[Dict] = None) -> str:
    """Send a critical system alert"""
    return system.send_alert(title, message, NotificationPriority.CRITICAL, metadata)

def send_task_notification(system: NotificationSystem, task_id: str, status: str, details: Dict[str, Any]) -> str:
    """Send a task status notification"""
    return system.send_notification(
        notification_type=NotificationType.TASK_UPDATE,
        subject=f"Task {status.title()}: {task_id}",
        message=f"Task {task_id} is now {status}",
        metadata={"task_id": task_id, "status": status, **details}
    )