"""
Billing Alert and Notification Manager
Real-time alerts for cost thresholds, usage anomalies, and billing events
"""

import asyncio
import json
import logging
import smtplib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import redis
import aiohttp
from decimal import Decimal

class AlertType(Enum):
    COST_THRESHOLD = "cost_threshold"
    BUDGET_EXCEEDED = "budget_exceeded"
    USAGE_ANOMALY = "usage_anomaly"
    BILLING_ERROR = "billing_error"
    PAYMENT_FAILED = "payment_failed"
    SERVICE_LIMIT = "service_limit"
    OPTIMIZATION_OPPORTUNITY = "optimization_opportunity"
    SCHEDULED_REPORT = "scheduled_report"

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class NotificationChannel(Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"
    SLACK = "slack"
    TEAMS = "teams"
    IN_APP = "in_app"

@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    user_id: str
    alert_type: AlertType
    severity: AlertSeverity
    
    # Trigger conditions
    threshold_value: float
    comparison_operator: str  # >=, <=, ==, !=, >, <
    evaluation_period: int  # seconds
    
    # Notification settings
    notification_channels: List[NotificationChannel]
    notification_template: str
    cooldown_period: int = 3600  # 1 hour default
    
    # Targeting
    session_id: Optional[str] = None
    service_type: Optional[str] = None
    
    # Status
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    total_triggers: int = 0
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""

@dataclass
class Alert:
    """Alert instance"""
    alert_id: str
    rule_id: str
    user_id: str
    alert_type: AlertType
    severity: AlertSeverity
    
    # Alert details
    title: str
    message: str
    current_value: float
    threshold_value: float
    
    # Context
    session_id: Optional[str] = None
    service_type: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    status: str = "active"  # active, acknowledged, resolved
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Notifications
    notifications_sent: List[str] = field(default_factory=list)
    failed_notifications: List[str] = field(default_factory=list)

@dataclass
class NotificationConfig:
    """Notification channel configuration"""
    user_id: str
    channel: NotificationChannel
    enabled: bool = True
    
    # Channel-specific settings
    email_address: Optional[str] = None
    webhook_url: Optional[str] = None
    phone_number: Optional[str] = None
    slack_channel: Optional[str] = None
    teams_webhook: Optional[str] = None
    
    # Preferences
    quiet_hours_start: Optional[str] = None  # "22:00"
    quiet_hours_end: Optional[str] = None    # "08:00"
    timezone: str = "UTC"
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class BillingAlertManager:
    """
    Comprehensive billing alert and notification manager
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Alert management
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.notification_configs: Dict[str, Dict[NotificationChannel, NotificationConfig]] = {}
        
        # Notification handlers
        self.notification_handlers: Dict[NotificationChannel, Callable] = {
            NotificationChannel.EMAIL: self._send_email_notification,
            NotificationChannel.WEBHOOK: self._send_webhook_notification,
            NotificationChannel.SMS: self._send_sms_notification,
            NotificationChannel.SLACK: self._send_slack_notification,
            NotificationChannel.TEAMS: self._send_teams_notification,
            NotificationChannel.IN_APP: self._send_in_app_notification
        }
        
        # Alert processor state
        self.alert_processor_running = False
        
        # Email configuration
        self.email_config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "",  # Configure externally
            "password": "",  # Configure externally
            "from_address": "noreply@activelog.com"
        }
        
        # Performance metrics
        self.metrics = {
            "alerts_triggered": 0,
            "notifications_sent": 0,
            "notification_failures": 0,
            "average_notification_time": 0.0,
            "rules_evaluated": 0
        }
        
        # Alert templates
        self.alert_templates = self._initialize_alert_templates()

    def _initialize_alert_templates(self) -> Dict[AlertType, Dict[str, str]]:
        """Initialize alert message templates"""
        return {
            AlertType.COST_THRESHOLD: {
                "email_subject": "Cost Threshold Alert - ${current_value}",
                "email_body": """
Dear User,

Your current usage cost has reached ${current_value}, which exceeds your configured threshold of ${threshold_value}.

Session: ${session_id}
Service: ${service_type}
Time: ${timestamp}

Please review your usage to avoid unexpected charges.

Best regards,
ActiveLog Billing Team
""",
                "webhook_payload": {
                    "alert_type": "cost_threshold",
                    "message": "Cost threshold exceeded",
                    "current_value": "${current_value}",
                    "threshold_value": "${threshold_value}",
                    "timestamp": "${timestamp}"
                }
            },
            AlertType.BUDGET_EXCEEDED: {
                "email_subject": "Budget Exceeded Alert - ${current_value}",
                "email_body": """
Dear User,

Your monthly budget of ${threshold_value} has been exceeded. Current usage: ${current_value}.

This may result in service limitations to prevent further charges.

Please review your usage or increase your budget limit.

Best regards,
ActiveLog Billing Team
""",
                "webhook_payload": {
                    "alert_type": "budget_exceeded",
                    "message": "Monthly budget exceeded",
                    "current_value": "${current_value}",
                    "threshold_value": "${threshold_value}",
                    "timestamp": "${timestamp}"
                }
            },
            AlertType.USAGE_ANOMALY: {
                "email_subject": "Unusual Usage Pattern Detected",
                "email_body": """
Dear User,

We've detected unusual usage patterns that may indicate an issue or optimization opportunity.

Current usage: ${current_value}
Expected usage: ${threshold_value}

Please review your applications and scaling policies.

Best regards,
ActiveLog Billing Team
""",
                "webhook_payload": {
                    "alert_type": "usage_anomaly",
                    "message": "Unusual usage pattern detected",
                    "current_value": "${current_value}",
                    "expected_value": "${threshold_value}",
                    "timestamp": "${timestamp}"
                }
            },
            AlertType.OPTIMIZATION_OPPORTUNITY: {
                "email_subject": "Cost Optimization Opportunity",
                "email_body": """
Dear User,

We've identified potential cost savings of up to ${potential_savings} based on your usage patterns.

Recommendations:
${recommendations}

Review your cost optimization suggestions in the dashboard.

Best regards,
ActiveLog Billing Team
""",
                "webhook_payload": {
                    "alert_type": "optimization_opportunity",
                    "message": "Cost optimization opportunity identified",
                    "potential_savings": "${potential_savings}",
                    "recommendations": "${recommendations}",
                    "timestamp": "${timestamp}"
                }
            }
        }

    async def configure_alerts(self, alert_config: Dict[str, Any]):
        """Configure alert rules and notification settings"""
        try:
            user_id = alert_config["user_id"]
            
            # Configure alert rules
            if "rules" in alert_config:
                for rule_data in alert_config["rules"]:
                    rule = AlertRule(
                        rule_id=f"{user_id}_{rule_data['alert_type']}_{int(datetime.now().timestamp())}",
                        user_id=user_id,
                        alert_type=AlertType(rule_data["alert_type"]),
                        severity=AlertSeverity(rule_data.get("severity", "medium")),
                        threshold_value=float(rule_data["threshold_value"]),
                        comparison_operator=rule_data.get("comparison_operator", ">="),
                        evaluation_period=rule_data.get("evaluation_period", 300),
                        notification_channels=[
                            NotificationChannel(ch) for ch in rule_data.get("notification_channels", ["email"])
                        ],
                        notification_template=rule_data.get("notification_template", "default"),
                        cooldown_period=rule_data.get("cooldown_period", 3600),
                        session_id=rule_data.get("session_id"),
                        service_type=rule_data.get("service_type"),
                        description=rule_data.get("description", "")
                    )
                    
                    self.alert_rules[rule.rule_id] = rule
            
            # Configure notification channels
            if "notifications" in alert_config:
                if user_id not in self.notification_configs:
                    self.notification_configs[user_id] = {}
                
                for channel_data in alert_config["notifications"]:
                    channel = NotificationChannel(channel_data["channel"])
                    
                    config = NotificationConfig(
                        user_id=user_id,
                        channel=channel,
                        enabled=channel_data.get("enabled", True),
                        email_address=channel_data.get("email_address"),
                        webhook_url=channel_data.get("webhook_url"),
                        phone_number=channel_data.get("phone_number"),
                        slack_channel=channel_data.get("slack_channel"),
                        teams_webhook=channel_data.get("teams_webhook"),
                        quiet_hours_start=channel_data.get("quiet_hours_start"),
                        quiet_hours_end=channel_data.get("quiet_hours_end"),
                        timezone=channel_data.get("timezone", "UTC")
                    )
                    
                    self.notification_configs[user_id][channel] = config
            
            # Store configuration in Redis
            if self.redis_client:
                await self._store_alert_config_in_redis(user_id, alert_config)
            
            self.logger.info(f"Configured alerts for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to configure alerts: {e}")
            raise

    async def get_user_alerts(self, user_id: str) -> Dict[str, Any]:
        """Get active alerts for user"""
        try:
            user_alerts = [
                alert for alert in self.active_alerts.values()
                if alert.user_id == user_id
            ]
            
            return {
                "user_id": user_id,
                "active_alerts": len(user_alerts),
                "alerts": [
                    {
                        "alert_id": alert.alert_id,
                        "alert_type": alert.alert_type.value,
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "message": alert.message,
                        "current_value": alert.current_value,
                        "threshold_value": alert.threshold_value,
                        "status": alert.status,
                        "created_at": alert.created_at.isoformat(),
                        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                        "session_id": alert.session_id,
                        "service_type": alert.service_type
                    }
                    for alert in user_alerts
                ],
                "alert_rules": [
                    {
                        "rule_id": rule.rule_id,
                        "alert_type": rule.alert_type.value,
                        "severity": rule.severity.value,
                        "threshold_value": rule.threshold_value,
                        "enabled": rule.enabled,
                        "total_triggers": rule.total_triggers,
                        "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None,
                        "description": rule.description
                    }
                    for rule in self.alert_rules.values()
                    if rule.user_id == user_id
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get user alerts: {e}")
            return {"error": str(e)}

    async def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert"""
        try:
            if alert_id not in self.active_alerts:
                raise ValueError(f"Alert {alert_id} not found")
            
            alert = self.active_alerts[alert_id]
            alert.status = "acknowledged"
            alert.acknowledged_at = datetime.now(timezone.utc)
            
            # Store acknowledgment in Redis
            if self.redis_client:
                await self._store_alert_acknowledgment_in_redis(alert)
            
            self.logger.info(f"Alert {alert_id} acknowledged")
            
        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            raise

    async def start_alert_monitor(self):
        """Start continuous alert monitoring"""
        if self.alert_processor_running:
            return
        
        self.alert_processor_running = True
        self.logger.info("Starting billing alert monitor")
        
        try:
            # Start monitoring tasks
            monitoring_tasks = [
                asyncio.create_task(self._evaluate_alert_rules_loop()),
                asyncio.create_task(self._process_notification_queue_loop()),
                asyncio.create_task(self._cleanup_resolved_alerts_loop())
            ]
            
            # Wait for all tasks
            await asyncio.gather(*monitoring_tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            self.logger.info("Alert monitor cancelled")
        except Exception as e:
            self.logger.error(f"Alert monitor error: {e}")
        finally:
            self.alert_processor_running = False

    async def _evaluate_alert_rules_loop(self):
        """Continuously evaluate alert rules"""
        try:
            while self.alert_processor_running:
                # Evaluate all active alert rules
                for rule_id, rule in self.alert_rules.items():
                    if not rule.enabled:
                        continue
                    
                    try:
                        # Check cooldown period
                        if rule.last_triggered:
                            time_since_last = (datetime.now(timezone.utc) - rule.last_triggered).total_seconds()
                            if time_since_last < rule.cooldown_period:
                                continue
                        
                        # Evaluate rule condition
                        should_trigger = await self._evaluate_alert_condition(rule)
                        
                        if should_trigger:
                            await self._trigger_alert(rule)
                        
                        self.metrics["rules_evaluated"] += 1
                    
                    except Exception as e:
                        self.logger.error(f"Failed to evaluate alert rule {rule_id}: {e}")
                
                # Wait before next evaluation cycle
                await asyncio.sleep(60)  # Evaluate every minute
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Alert rules evaluation loop error: {e}")

    async def _process_notification_queue_loop(self):
        """Process notification queue"""
        try:
            while self.alert_processor_running:
                # Process pending notifications
                notifications_processed = 0
                
                for alert in list(self.active_alerts.values()):
                    if alert.status == "active":
                        try:
                            await self._send_alert_notifications(alert)
                            notifications_processed += 1
                        except Exception as e:
                            self.logger.error(f"Failed to send notifications for alert {alert.alert_id}: {e}")
                
                if notifications_processed > 0:
                    self.logger.debug(f"Processed {notifications_processed} notification batches")
                
                # Wait before next processing cycle
                await asyncio.sleep(30)  # Process every 30 seconds
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Notification queue processing loop error: {e}")

    async def _cleanup_resolved_alerts_loop(self):
        """Clean up old resolved alerts"""
        try:
            while self.alert_processor_running:
                current_time = datetime.now(timezone.utc)
                cleanup_cutoff = current_time - timedelta(days=7)  # Keep for 7 days
                
                resolved_alerts = [
                    alert_id for alert_id, alert in self.active_alerts.items()
                    if alert.status in ["resolved", "acknowledged"] and alert.created_at < cleanup_cutoff
                ]
                
                for alert_id in resolved_alerts:
                    # Archive alert before deletion
                    if self.redis_client:
                        await self._archive_alert_in_redis(self.active_alerts[alert_id])
                    
                    del self.active_alerts[alert_id]
                
                if resolved_alerts:
                    self.logger.info(f"Cleaned up {len(resolved_alerts)} resolved alerts")
                
                # Wait 6 hours before next cleanup
                await asyncio.sleep(21600)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Alert cleanup loop error: {e}")

    async def _evaluate_alert_condition(self, rule: AlertRule) -> bool:
        """Evaluate if alert condition is met"""
        try:
            # Get current metric value based on alert type
            current_value = await self._get_current_metric_value(rule)
            
            if current_value is None:
                return False
            
            # Evaluate condition
            operator = rule.comparison_operator
            threshold = rule.threshold_value
            
            if operator == ">=":
                return current_value >= threshold
            elif operator == "<=":
                return current_value <= threshold
            elif operator == ">":
                return current_value > threshold
            elif operator == "<":
                return current_value < threshold
            elif operator == "==":
                return abs(current_value - threshold) < 0.01
            elif operator == "!=":
                return abs(current_value - threshold) >= 0.01
            else:
                self.logger.warning(f"Unknown comparison operator: {operator}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate alert condition: {e}")
            return False

    async def _get_current_metric_value(self, rule: AlertRule) -> Optional[float]:
        """Get current metric value for alert evaluation"""
        try:
            if rule.alert_type == AlertType.COST_THRESHOLD:
                # Get current cost for user/session
                return await self._get_current_cost(rule.user_id, rule.session_id)
            
            elif rule.alert_type == AlertType.BUDGET_EXCEEDED:
                # Get monthly accumulated cost
                return await self._get_monthly_cost(rule.user_id)
            
            elif rule.alert_type == AlertType.USAGE_ANOMALY:
                # Get current usage level
                return await self._get_current_usage_level(rule.user_id, rule.session_id)
            
            elif rule.alert_type == AlertType.SERVICE_LIMIT:
                # Get current service usage
                return await self._get_service_usage_level(rule.user_id, rule.service_type)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get current metric value: {e}")
            return None

    async def _get_current_cost(self, user_id: str, session_id: Optional[str]) -> Optional[float]:
        """Get current cost for user/session"""
        try:
            if self.redis_client:
                if session_id:
                    # Get session-specific cost
                    session_key = f"billing_session:{session_id}"
                    cost_data = await self.redis_client.hget(session_key, "accumulated_cost")
                    return float(cost_data) if cost_data else 0.0
                else:
                    # Get total cost for user
                    user_sessions_key = f"user_sessions:{user_id}"
                    session_ids = await self.redis_client.smembers(user_sessions_key)
                    
                    total_cost = 0.0
                    for sid in session_ids:
                        session_key = f"billing_session:{sid}"
                        cost_data = await self.redis_client.hget(session_key, "accumulated_cost")
                        if cost_data:
                            total_cost += float(cost_data)
                    
                    return total_cost
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to get current cost: {e}")
            return None

    async def _get_monthly_cost(self, user_id: str) -> Optional[float]:
        """Get monthly accumulated cost for user"""
        try:
            if self.redis_client:
                # Get costs from current month
                current_month = datetime.now(timezone.utc).strftime("%Y-%m")
                monthly_cost_key = f"monthly_cost:{user_id}:{current_month}"
                
                cost_data = await self.redis_client.get(monthly_cost_key)
                if cost_data:
                    return float(cost_data)
                
                # Calculate from archived billing data
                user_sessions_key = f"user_sessions:{user_id}"
                session_ids = await self.redis_client.smembers(user_sessions_key)
                
                monthly_cost = 0.0
                for session_id in session_ids:
                    archive_key = f"billing_archive:{user_id}:{session_id}"
                    archive_data = await self.redis_client.hgetall(archive_key)
                    
                    if archive_data and "stopped_at" in archive_data:
                        stopped_at = datetime.fromisoformat(archive_data["stopped_at"])
                        if stopped_at.strftime("%Y-%m") == current_month:
                            monthly_cost += float(archive_data.get("total_cost", 0))
                
                # Cache the calculated monthly cost
                await self.redis_client.setex(monthly_cost_key, 3600, str(monthly_cost))
                
                return monthly_cost
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to get monthly cost: {e}")
            return None

    async def _get_current_usage_level(self, user_id: str, session_id: Optional[str]) -> Optional[float]:
        """Get current usage level (placeholder)"""
        try:
            # This would integrate with usage tracking
            # For now, return a placeholder value
            return 75.0  # 75% usage level
            
        except Exception as e:
            self.logger.error(f"Failed to get current usage level: {e}")
            return None

    async def _get_service_usage_level(self, user_id: str, service_type: Optional[str]) -> Optional[float]:
        """Get service-specific usage level"""
        try:
            # This would get service-specific metrics
            # For now, return a placeholder value
            return 80.0  # 80% of service limit
            
        except Exception as e:
            self.logger.error(f"Failed to get service usage level: {e}")
            return None

    async def _trigger_alert(self, rule: AlertRule):
        """Trigger an alert"""
        try:
            current_value = await self._get_current_metric_value(rule)
            
            if current_value is None:
                return
            
            # Create alert
            alert_id = f"alert_{rule.user_id}_{rule.alert_type.value}_{int(datetime.now().timestamp())}"
            
            alert = Alert(
                alert_id=alert_id,
                rule_id=rule.rule_id,
                user_id=rule.user_id,
                alert_type=rule.alert_type,
                severity=rule.severity,
                title=self._generate_alert_title(rule, current_value),
                message=self._generate_alert_message(rule, current_value),
                current_value=current_value,
                threshold_value=rule.threshold_value,
                session_id=rule.session_id,
                service_type=rule.service_type,
                additional_data={
                    "rule_description": rule.description,
                    "evaluation_period": rule.evaluation_period,
                    "comparison_operator": rule.comparison_operator
                }
            )
            
            # Store alert
            self.active_alerts[alert_id] = alert
            
            # Update rule statistics
            rule.last_triggered = datetime.now(timezone.utc)
            rule.total_triggers += 1
            
            # Store alert in Redis
            if self.redis_client:
                await self._store_alert_in_redis(alert)
            
            # Update metrics
            self.metrics["alerts_triggered"] += 1
            
            self.logger.warning(f"Alert triggered: {alert.title} for user {rule.user_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to trigger alert: {e}")

    def _generate_alert_title(self, rule: AlertRule, current_value: float) -> str:
        """Generate alert title"""
        titles = {
            AlertType.COST_THRESHOLD: f"Cost Alert: ${current_value:.2f} exceeds ${rule.threshold_value:.2f}",
            AlertType.BUDGET_EXCEEDED: f"Budget Exceeded: ${current_value:.2f} over ${rule.threshold_value:.2f} budget",
            AlertType.USAGE_ANOMALY: f"Usage Anomaly: {current_value:.1f}% above normal",
            AlertType.BILLING_ERROR: "Billing Error Detected",
            AlertType.PAYMENT_FAILED: "Payment Processing Failed",
            AlertType.SERVICE_LIMIT: f"Service Limit: {current_value:.1f}% of limit reached",
            AlertType.OPTIMIZATION_OPPORTUNITY: "Cost Optimization Opportunity"
        }
        
        return titles.get(rule.alert_type, f"Alert: {rule.alert_type.value}")

    def _generate_alert_message(self, rule: AlertRule, current_value: float) -> str:
        """Generate alert message"""
        messages = {
            AlertType.COST_THRESHOLD: f"Your current usage cost of ${current_value:.2f} has exceeded the configured threshold of ${rule.threshold_value:.2f}.",
            AlertType.BUDGET_EXCEEDED: f"Your monthly budget of ${rule.threshold_value:.2f} has been exceeded. Current usage: ${current_value:.2f}.",
            AlertType.USAGE_ANOMALY: f"Unusual usage pattern detected: {current_value:.1f}% above expected levels.",
            AlertType.SERVICE_LIMIT: f"Service usage is at {current_value:.1f}% of the configured limit.",
            AlertType.OPTIMIZATION_OPPORTUNITY: f"Potential cost savings identified: ${current_value:.2f} per month."
        }
        
        message = messages.get(rule.alert_type, f"Alert condition met: {current_value} {rule.comparison_operator} {rule.threshold_value}")
        
        if rule.description:
            message += f"\n\nRule: {rule.description}"
        
        return message

    async def _send_alert_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        try:
            if alert.user_id not in self.notification_configs:
                self.logger.warning(f"No notification config for user {alert.user_id}")
                return
            
            rule = self.alert_rules.get(alert.rule_id)
            if not rule:
                self.logger.warning(f"Rule not found for alert {alert.alert_id}")
                return
            
            user_configs = self.notification_configs[alert.user_id]
            
            # Send notifications through configured channels
            for channel in rule.notification_channels:
                if channel in user_configs and user_configs[channel].enabled:
                    config = user_configs[channel]
                    
                    # Check quiet hours
                    if await self._is_quiet_hours(config):
                        continue
                    
                    try:
                        handler = self.notification_handlers.get(channel)
                        if handler:
                            start_time = datetime.now()
                            
                            success = await handler(alert, config)
                            
                            notification_time = (datetime.now() - start_time).total_seconds()
                            self.metrics["average_notification_time"] = (
                                self.metrics["average_notification_time"] * 0.9 + notification_time * 0.1
                            )
                            
                            if success:
                                alert.notifications_sent.append(channel.value)
                                self.metrics["notifications_sent"] += 1
                            else:
                                alert.failed_notifications.append(channel.value)
                                self.metrics["notification_failures"] += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to send {channel.value} notification: {e}")
                        alert.failed_notifications.append(channel.value)
                        self.metrics["notification_failures"] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to send alert notifications: {e}")

    async def _is_quiet_hours(self, config: NotificationConfig) -> bool:
        """Check if current time is within quiet hours"""
        try:
            if not config.quiet_hours_start or not config.quiet_hours_end:
                return False
            
            # For simplicity, assume UTC time
            current_time = datetime.now(timezone.utc).time()
            
            start_time = datetime.strptime(config.quiet_hours_start, "%H:%M").time()
            end_time = datetime.strptime(config.quiet_hours_end, "%H:%M").time()
            
            if start_time <= end_time:
                # Same day quiet hours
                return start_time <= current_time <= end_time
            else:
                # Overnight quiet hours
                return current_time >= start_time or current_time <= end_time
                
        except Exception as e:
            self.logger.error(f"Failed to check quiet hours: {e}")
            return False

    async def _send_email_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send email notification"""
        try:
            if not config.email_address or not self.email_config.get("username"):
                return False
            
            # Get template
            template = self.alert_templates.get(alert.alert_type, {})
            subject = template.get("email_subject", "ActiveLog Alert")
            body = template.get("email_body", alert.message)
            
            # Replace template variables
            variables = {
                "current_value": f"{alert.current_value:.2f}",
                "threshold_value": f"{alert.threshold_value:.2f}",
                "session_id": alert.session_id or "N/A",
                "service_type": alert.service_type or "N/A",
                "timestamp": alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value
            }
            
            for key, value in variables.items():
                subject = subject.replace(f"${{{key}}}", str(value))
                body = body.replace(f"${{{key}}}", str(value))
            
            # Create email
            msg = MIMEMultipart()
            msg["From"] = self.email_config["from_address"]
            msg["To"] = config.email_address
            msg["Subject"] = subject
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"]) as server:
                server.starttls()
                server.login(self.email_config["username"], self.email_config["password"])
                server.send_message(msg)
            
            self.logger.info(f"Email notification sent to {config.email_address}")
            return True
            
        except Exception as e:
            self.logger.error(f"Email notification failed: {e}")
            return False

    async def _send_webhook_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send webhook notification"""
        try:
            if not config.webhook_url:
                return False
            
            # Get template payload
            template = self.alert_templates.get(alert.alert_type, {})
            payload = template.get("webhook_payload", {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type.value,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "timestamp": alert.created_at.isoformat()
            })
            
            # Replace template variables
            payload_str = json.dumps(payload)
            variables = {
                "current_value": f"{alert.current_value:.2f}",
                "threshold_value": f"{alert.threshold_value:.2f}",
                "timestamp": alert.created_at.isoformat(),
                "alert_id": alert.alert_id,
                "user_id": alert.user_id,
                "session_id": alert.session_id or "N/A",
                "service_type": alert.service_type or "N/A"
            }
            
            for key, value in variables.items():
                payload_str = payload_str.replace(f"${{{key}}}", str(value))
            
            final_payload = json.loads(payload_str)
            
            # Send webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config.webhook_url,
                    json=final_payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Webhook notification sent to {config.webhook_url}")
                        return True
                    else:
                        self.logger.warning(f"Webhook returned status {response.status}")
                        return False
            
        except Exception as e:
            self.logger.error(f"Webhook notification failed: {e}")
            return False

    async def _send_sms_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send SMS notification (placeholder)"""
        try:
            # This would integrate with SMS provider (Twilio, etc.)
            self.logger.info(f"SMS notification would be sent to {config.phone_number}")
            return True
            
        except Exception as e:
            self.logger.error(f"SMS notification failed: {e}")
            return False

    async def _send_slack_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send Slack notification (placeholder)"""
        try:
            # This would integrate with Slack API
            self.logger.info(f"Slack notification would be sent to {config.slack_channel}")
            return True
            
        except Exception as e:
            self.logger.error(f"Slack notification failed: {e}")
            return False

    async def _send_teams_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send Microsoft Teams notification (placeholder)"""
        try:
            # This would integrate with Teams webhook
            self.logger.info(f"Teams notification would be sent to {config.teams_webhook}")
            return True
            
        except Exception as e:
            self.logger.error(f"Teams notification failed: {e}")
            return False

    async def _send_in_app_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send in-app notification"""
        try:
            if self.redis_client:
                # Store in-app notification
                notification_key = f"in_app_notifications:{alert.user_id}"
                
                notification_data = {
                    "alert_id": alert.alert_id,
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity.value,
                    "created_at": alert.created_at.isoformat(),
                    "read": False
                }
                
                await self.redis_client.lpush(notification_key, json.dumps(notification_data))
                await self.redis_client.expire(notification_key, 2592000)  # 30 days
                
                self.logger.info(f"In-app notification stored for user {alert.user_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"In-app notification failed: {e}")
            return False

    async def _store_alert_config_in_redis(self, user_id: str, config: Dict[str, Any]):
        """Store alert configuration in Redis"""
        try:
            if not self.redis_client:
                return
            
            config_key = f"alert_config:{user_id}"
            await self.redis_client.hset(config_key, mapping={
                "config": json.dumps(config),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            
            await self.redis_client.expire(config_key, 2592000)  # 30 days
            
        except Exception as e:
            self.logger.error(f"Failed to store alert config in Redis: {e}")

    async def _store_alert_in_redis(self, alert: Alert):
        """Store alert in Redis"""
        try:
            if not self.redis_client:
                return
            
            alert_key = f"alert:{alert.alert_id}"
            
            alert_data = {
                "alert_id": alert.alert_id,
                "rule_id": alert.rule_id,
                "user_id": alert.user_id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "status": alert.status,
                "created_at": alert.created_at.isoformat(),
                "session_id": alert.session_id or "",
                "service_type": alert.service_type or ""
            }
            
            await self.redis_client.hset(alert_key, mapping=alert_data)
            await self.redis_client.expire(alert_key, 604800)  # 7 days
            
        except Exception as e:
            self.logger.error(f"Failed to store alert in Redis: {e}")

    async def _store_alert_acknowledgment_in_redis(self, alert: Alert):
        """Store alert acknowledgment in Redis"""
        try:
            if not self.redis_client:
                return
            
            alert_key = f"alert:{alert.alert_id}"
            await self.redis_client.hset(alert_key, mapping={
                "status": alert.status,
                "acknowledged_at": alert.acknowledged_at.isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Failed to store alert acknowledgment in Redis: {e}")

    async def _archive_alert_in_redis(self, alert: Alert):
        """Archive alert in Redis"""
        try:
            if not self.redis_client:
                return
            
            archive_key = f"alert_archive:{alert.user_id}:{alert.alert_id}"
            
            alert_data = {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "status": alert.status,
                "created_at": alert.created_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "notifications_sent": json.dumps(alert.notifications_sent)
            }
            
            await self.redis_client.hset(archive_key, mapping=alert_data)
            await self.redis_client.expire(archive_key, 7776000)  # 90 days
            
        except Exception as e:
            self.logger.error(f"Failed to archive alert in Redis: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get alert manager status"""
        return {
            "alert_processor_running": self.alert_processor_running,
            "active_alerts": len(self.active_alerts),
            "alert_rules": len(self.alert_rules),
            "notification_configs": sum(len(configs) for configs in self.notification_configs.values()),
            "metrics": self.metrics,
            "supported_channels": [channel.value for channel in NotificationChannel],
            "redis_connected": self.redis_client is not None
        }

    async def shutdown(self):
        """Shutdown alert manager"""
        try:
            self.logger.info("Shutting down billing alert manager...")
            
            # Stop alert processor
            self.alert_processor_running = False
            
            # Archive active alerts
            for alert in self.active_alerts.values():
                if self.redis_client:
                    await self._archive_alert_in_redis(alert)
            
            self.logger.info("Billing alert manager shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during alert manager shutdown: {e}")