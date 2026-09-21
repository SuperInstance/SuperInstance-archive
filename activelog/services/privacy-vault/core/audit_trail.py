import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import uuid
import ipaddress
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_WITHDRAWN = "consent_withdrawn"
    POLICY_CREATED = "policy_created"
    POLICY_MODIFIED = "policy_modified"
    USER_AUTHENTICATION = "user_authentication"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    SECURITY_INCIDENT = "security_incident"
    COMPLIANCE_VIOLATION = "compliance_violation"
    SYSTEM_CONFIGURATION = "system_configuration"
    BACKUP_OPERATION = "backup_operation"
    RESTORE_OPERATION = "restore_operation"

class AccessType(Enum):
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    COPY = "copy"
    PRINT = "print"
    DOWNLOAD = "download"

class AuditStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNAUTHORIZED = "unauthorized"
    ERROR = "error"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceFramework(Enum):
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"

@dataclass
class AuditEvent:
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    actor_id: str
    actor_type: str  # user, system, service, api
    session_id: Optional[str]
    source_ip: str
    user_agent: Optional[str]
    resource_type: str
    resource_id: Optional[str]
    action: AccessType
    status: AuditStatus
    risk_level: RiskLevel
    details: Dict[str, Any]
    data_categories: List[str]
    legal_basis: Optional[str]
    purpose: Optional[str]
    retention_period: Optional[int]
    geographic_location: Optional[str]
    compliance_frameworks: List[ComplianceFramework]
    sensitive_data_involved: bool
    data_volume: Optional[int]
    duration_ms: Optional[int]
    error_message: Optional[str]
    correlation_id: Optional[str]
    metadata: Dict[str, Any]

@dataclass
class DataAccessPattern:
    pattern_id: str
    actor_id: str
    resource_patterns: List[str]
    access_frequency: int
    typical_hours: List[int]  # 0-23
    typical_days: List[int]   # 0-6 (Monday-Sunday)
    typical_locations: List[str]
    risk_score: float
    anomaly_threshold: float
    created_date: datetime
    last_updated: datetime

@dataclass
class AuditAlert:
    alert_id: str
    event_id: str
    alert_type: str
    severity: RiskLevel
    description: str
    triggered_rules: List[str]
    created_date: datetime
    acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_date: Optional[datetime]
    resolved: bool
    resolved_by: Optional[str]
    resolved_date: Optional[datetime]
    false_positive: bool
    investigation_notes: List[str]

@dataclass
class ComplianceReport:
    report_id: str
    framework: ComplianceFramework
    report_period_start: datetime
    report_period_end: datetime
    total_events: int
    compliant_events: int
    violations: List[Dict[str, Any]]
    risk_summary: Dict[str, int]
    recommendations: List[str]
    generated_date: datetime
    generated_by: str

class AuditTrailManager:
    def __init__(self):
        self.audit_events: Dict[str, AuditEvent] = {}
        self.access_patterns: Dict[str, DataAccessPattern] = {}
        self.audit_alerts: Dict[str, AuditAlert] = {}
        self.compliance_rules: Dict[str, Dict] = {}
        self.alert_rules: Dict[str, Dict] = {}
        self.retention_policies: Dict[str, int] = {}  # framework -> days
        self.anonymized_events: Set[str] = set()
        logger.info("Audit Trail Manager initialized")

    async def initialize(self):
        await self._initialize_compliance_rules()
        await self._initialize_alert_rules()
        await self._initialize_retention_policies()
        logger.info("Audit Trail Manager initialization completed")

    async def _initialize_compliance_rules(self):
        self.compliance_rules = {
            ComplianceFramework.GDPR.value: {
                "required_fields": [
                    "actor_id", "timestamp", "resource_type", "action", "legal_basis", "purpose"
                ],
                "retention_period": 2555,  # 7 years in days
                "anonymization_required": True,
                "data_subject_access": True,
                "breach_notification_threshold": 72  # hours
            },
            ComplianceFramework.HIPAA.value: {
                "required_fields": [
                    "actor_id", "timestamp", "resource_type", "action", "purpose"
                ],
                "retention_period": 2190,  # 6 years in days
                "anonymization_required": False,
                "minimum_necessary_logging": True,
                "breach_notification_threshold": 60  # days
            },
            ComplianceFramework.SOX.value: {
                "required_fields": [
                    "actor_id", "timestamp", "resource_type", "action", "details"
                ],
                "retention_period": 2555,  # 7 years in days
                "immutable_logs": True,
                "segregation_of_duties": True
            },
            ComplianceFramework.PCI_DSS.value: {
                "required_fields": [
                    "actor_id", "timestamp", "resource_type", "action", "status"
                ],
                "retention_period": 365,  # 1 year minimum
                "real_time_monitoring": True,
                "cardholder_data_access": True
            }
        }
        logger.info("Initialized compliance rules")

    async def _initialize_alert_rules(self):
        self.alert_rules = {
            "suspicious_access_pattern": {
                "description": "Unusual access pattern detected",
                "conditions": {
                    "access_frequency_threshold": 100,  # per hour
                    "off_hours_access": True,
                    "unusual_location": True
                },
                "severity": RiskLevel.MEDIUM,
                "action": "investigate"
            },
            "unauthorized_access_attempt": {
                "description": "Unauthorized access attempt",
                "conditions": {
                    "status": AuditStatus.UNAUTHORIZED,
                    "failed_attempts_threshold": 5
                },
                "severity": RiskLevel.HIGH,
                "action": "alert_security_team"
            },
            "sensitive_data_bulk_access": {
                "description": "Bulk access to sensitive data",
                "conditions": {
                    "sensitive_data_involved": True,
                    "data_volume_threshold": 1000
                },
                "severity": RiskLevel.HIGH,
                "action": "immediate_review"
            },
            "privileged_user_activity": {
                "description": "Privileged user performing sensitive operations",
                "conditions": {
                    "actor_type": "admin",
                    "event_types": [AuditEventType.DATA_DELETION, AuditEventType.POLICY_MODIFIED]
                },
                "severity": RiskLevel.MEDIUM,
                "action": "log_and_notify"
            },
            "compliance_violation": {
                "description": "Potential compliance violation detected",
                "conditions": {
                    "missing_legal_basis": True,
                    "retention_violation": True,
                    "consent_violation": True
                },
                "severity": RiskLevel.CRITICAL,
                "action": "immediate_escalation"
            }
        }
        logger.info("Initialized alert rules")

    async def _initialize_retention_policies(self):
        self.retention_policies = {
            ComplianceFramework.GDPR.value: 2555,  # 7 years
            ComplianceFramework.HIPAA.value: 2190,  # 6 years
            ComplianceFramework.SOX.value: 2555,   # 7 years
            ComplianceFramework.PCI_DSS.value: 365, # 1 year
            ComplianceFramework.CCPA.value: 1095,  # 3 years
            ComplianceFramework.ISO27001.value: 1095  # 3 years
        }
        logger.info("Initialized retention policies")

    async def log_event(
        self,
        event_type: AuditEventType,
        actor_id: str,
        actor_type: str,
        resource_type: str,
        action: AccessType,
        status: AuditStatus,
        **kwargs
    ) -> str:
        event_id = f"audit_{uuid.uuid4().hex[:12]}"
        
        # Determine risk level
        risk_level = await self._assess_risk_level(
            event_type, actor_type, resource_type, status, kwargs
        )
        
        # Extract and validate required fields
        source_ip = kwargs.get("source_ip", "unknown")
        if source_ip != "unknown":
            source_ip = await self._validate_and_anonymize_ip(source_ip)
        
        # Determine compliance frameworks
        compliance_frameworks = await self._determine_compliance_frameworks(
            event_type, resource_type, kwargs.get("data_categories", [])
        )
        
        # Create audit event
        event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.now(),
            event_type=event_type,
            actor_id=actor_id,
            actor_type=actor_type,
            session_id=kwargs.get("session_id"),
            source_ip=source_ip,
            user_agent=kwargs.get("user_agent"),
            resource_type=resource_type,
            resource_id=kwargs.get("resource_id"),
            action=action,
            status=status,
            risk_level=risk_level,
            details=kwargs.get("details", {}),
            data_categories=kwargs.get("data_categories", []),
            legal_basis=kwargs.get("legal_basis"),
            purpose=kwargs.get("purpose"),
            retention_period=kwargs.get("retention_period"),
            geographic_location=kwargs.get("geographic_location"),
            compliance_frameworks=compliance_frameworks,
            sensitive_data_involved=kwargs.get("sensitive_data_involved", False),
            data_volume=kwargs.get("data_volume"),
            duration_ms=kwargs.get("duration_ms"),
            error_message=kwargs.get("error_message"),
            correlation_id=kwargs.get("correlation_id"),
            metadata=kwargs.get("metadata", {})
        )
        
        # Store event
        self.audit_events[event_id] = event
        
        # Update access patterns
        await self._update_access_patterns(event)
        
        # Check for alerts
        await self._evaluate_alert_rules(event)
        
        # Validate compliance
        await self._validate_compliance(event)
        
        logger.info(f"Logged audit event {event_id}: {event_type.value} by {actor_id}")
        return event_id

    async def _assess_risk_level(
        self,
        event_type: AuditEventType,
        actor_type: str,
        resource_type: str,
        status: AuditStatus,
        kwargs: Dict[str, Any]
    ) -> RiskLevel:
        risk_score = 0
        
        # Event type scoring
        high_risk_events = [
            AuditEventType.DATA_DELETION,
            AuditEventType.DATA_EXPORT,
            AuditEventType.SECURITY_INCIDENT,
            AuditEventType.COMPLIANCE_VIOLATION
        ]
        
        if event_type in high_risk_events:
            risk_score += 3
        elif event_type in [AuditEventType.DATA_MODIFICATION, AuditEventType.POLICY_MODIFIED]:
            risk_score += 2
        else:
            risk_score += 1
        
        # Status scoring
        if status in [AuditStatus.FAILURE, AuditStatus.UNAUTHORIZED]:
            risk_score += 2
        elif status == AuditStatus.ERROR:
            risk_score += 1
        
        # Actor type scoring
        if actor_type in ["admin", "system"]:
            risk_score += 1
        elif actor_type == "anonymous":
            risk_score += 2
        
        # Sensitive data scoring
        if kwargs.get("sensitive_data_involved", False):
            risk_score += 2
        
        # Data volume scoring
        data_volume = kwargs.get("data_volume", 0)
        if data_volume > 10000:
            risk_score += 2
        elif data_volume > 1000:
            risk_score += 1
        
        # Convert to risk level
        if risk_score >= 8:
            return RiskLevel.CRITICAL
        elif risk_score >= 6:
            return RiskLevel.HIGH
        elif risk_score >= 4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    async def _validate_and_anonymize_ip(self, ip_address: str) -> str:
        try:
            ip = ipaddress.ip_address(ip_address)
            if isinstance(ip, ipaddress.IPv4Address):
                # Anonymize last octet
                octets = str(ip).split('.')
                return f"{octets[0]}.{octets[1]}.{octets[2]}.xxx"
            else:  # IPv6
                # Anonymize last 64 bits
                return f"{str(ip)[:19]}:xxxx:xxxx:xxxx:xxxx"
        except ValueError:
            return "invalid_ip"

    async def _determine_compliance_frameworks(
        self,
        event_type: AuditEventType,
        resource_type: str,
        data_categories: List[str]
    ) -> List[ComplianceFramework]:
        frameworks = []
        
        # GDPR applies to personal data
        if "personal_data" in data_categories or "special_category" in data_categories:
            frameworks.append(ComplianceFramework.GDPR)
        
        # HIPAA applies to healthcare data
        if "health_data" in data_categories or resource_type == "patient_record":
            frameworks.append(ComplianceFramework.HIPAA)
        
        # PCI DSS applies to payment data
        if "payment_data" in data_categories or "credit_card" in data_categories:
            frameworks.append(ComplianceFramework.PCI_DSS)
        
        # SOX applies to financial data
        if resource_type in ["financial_report", "audit_record"]:
            frameworks.append(ComplianceFramework.SOX)
        
        # Default to ISO27001 for security events
        if event_type == AuditEventType.SECURITY_INCIDENT:
            frameworks.append(ComplianceFramework.ISO27001)
        
        return frameworks

    async def _update_access_patterns(self, event: AuditEvent):
        pattern_key = f"{event.actor_id}_{event.resource_type}"
        
        if pattern_key not in self.access_patterns:
            # Create new pattern
            pattern = DataAccessPattern(
                pattern_id=f"pattern_{uuid.uuid4().hex[:8]}",
                actor_id=event.actor_id,
                resource_patterns=[event.resource_type],
                access_frequency=1,
                typical_hours=[event.timestamp.hour],
                typical_days=[event.timestamp.weekday()],
                typical_locations=[event.geographic_location or "unknown"],
                risk_score=0.0,
                anomaly_threshold=2.0,
                created_date=datetime.now(),
                last_updated=datetime.now()
            )
            self.access_patterns[pattern_key] = pattern
        else:
            # Update existing pattern
            pattern = self.access_patterns[pattern_key]
            pattern.access_frequency += 1
            
            # Update temporal patterns
            if event.timestamp.hour not in pattern.typical_hours:
                pattern.typical_hours.append(event.timestamp.hour)
            
            if event.timestamp.weekday() not in pattern.typical_days:
                pattern.typical_days.append(event.timestamp.weekday())
            
            # Update location patterns
            if event.geographic_location and event.geographic_location not in pattern.typical_locations:
                pattern.typical_locations.append(event.geographic_location)
            
            pattern.last_updated = datetime.now()
            
            # Calculate anomaly score
            anomaly_score = await self._calculate_anomaly_score(event, pattern)
            pattern.risk_score = (pattern.risk_score + anomaly_score) / 2

    async def _calculate_anomaly_score(self, event: AuditEvent, pattern: DataAccessPattern) -> float:
        score = 0.0
        
        # Time-based anomalies
        if event.timestamp.hour not in pattern.typical_hours:
            score += 0.3
        
        if event.timestamp.weekday() not in pattern.typical_days:
            score += 0.2
        
        # Location-based anomalies
        if event.geographic_location and event.geographic_location not in pattern.typical_locations:
            score += 0.3
        
        # Frequency-based anomalies
        recent_events = await self._count_recent_events(event.actor_id, hours=1)
        if recent_events > pattern.access_frequency * 2:
            score += 0.2
        
        return min(score, 1.0)

    async def _count_recent_events(self, actor_id: str, hours: int = 1) -> int:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        count = 0
        
        for event in self.audit_events.values():
            if event.actor_id == actor_id and event.timestamp > cutoff_time:
                count += 1
        
        return count

    async def _evaluate_alert_rules(self, event: AuditEvent):
        for rule_name, rule_config in self.alert_rules.items():
            if await self._check_alert_condition(event, rule_config):
                await self._create_alert(event, rule_name, rule_config)

    async def _check_alert_condition(self, event: AuditEvent, rule_config: Dict) -> bool:
        conditions = rule_config.get("conditions", {})
        
        # Check access frequency
        if "access_frequency_threshold" in conditions:
            recent_count = await self._count_recent_events(event.actor_id, hours=1)
            if recent_count >= conditions["access_frequency_threshold"]:
                return True
        
        # Check unauthorized access
        if "status" in conditions and event.status == conditions["status"]:
            if conditions["status"] == AuditStatus.UNAUTHORIZED:
                failed_attempts = await self._count_failed_attempts(event.actor_id, hours=1)
                if failed_attempts >= conditions.get("failed_attempts_threshold", 5):
                    return True
        
        # Check sensitive data bulk access
        if "sensitive_data_involved" in conditions and event.sensitive_data_involved:
            if event.data_volume and event.data_volume >= conditions.get("data_volume_threshold", 1000):
                return True
        
        # Check privileged user activity
        if "actor_type" in conditions and event.actor_type == conditions["actor_type"]:
            if event.event_type in conditions.get("event_types", []):
                return True
        
        # Check compliance violations
        if "missing_legal_basis" in conditions and not event.legal_basis:
            return True
        
        return False

    async def _count_failed_attempts(self, actor_id: str, hours: int = 1) -> int:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        count = 0
        
        for event in self.audit_events.values():
            if (event.actor_id == actor_id and 
                event.timestamp > cutoff_time and
                event.status in [AuditStatus.FAILURE, AuditStatus.UNAUTHORIZED]):
                count += 1
        
        return count

    async def _create_alert(self, event: AuditEvent, rule_name: str, rule_config: Dict):
        alert_id = f"alert_{uuid.uuid4().hex[:8]}"
        
        alert = AuditAlert(
            alert_id=alert_id,
            event_id=event.event_id,
            alert_type=rule_name,
            severity=rule_config.get("severity", RiskLevel.MEDIUM),
            description=rule_config.get("description", "Security alert triggered"),
            triggered_rules=[rule_name],
            created_date=datetime.now(),
            acknowledged=False,
            acknowledged_by=None,
            acknowledged_date=None,
            resolved=False,
            resolved_by=None,
            resolved_date=None,
            false_positive=False,
            investigation_notes=[]
        )
        
        self.audit_alerts[alert_id] = alert
        logger.warning(f"Security alert created: {alert_id} for event {event.event_id}")

    async def _validate_compliance(self, event: AuditEvent):
        for framework in event.compliance_frameworks:
            rules = self.compliance_rules.get(framework.value, {})
            
            # Check required fields
            required_fields = rules.get("required_fields", [])
            missing_fields = []
            
            for field in required_fields:
                if not getattr(event, field, None):
                    missing_fields.append(field)
            
            if missing_fields:
                await self._create_compliance_violation_alert(event, framework, missing_fields)

    async def _create_compliance_violation_alert(
        self,
        event: AuditEvent,
        framework: ComplianceFramework,
        missing_fields: List[str]
    ):
        alert_id = f"compliance_{uuid.uuid4().hex[:8]}"
        
        alert = AuditAlert(
            alert_id=alert_id,
            event_id=event.event_id,
            alert_type="compliance_violation",
            severity=RiskLevel.HIGH,
            description=f"{framework.value.upper()} compliance violation: missing fields {missing_fields}",
            triggered_rules=[f"{framework.value}_required_fields"],
            created_date=datetime.now(),
            acknowledged=False,
            acknowledged_by=None,
            acknowledged_date=None,
            resolved=False,
            resolved_by=None,
            resolved_date=None,
            false_positive=False,
            investigation_notes=[]
        )
        
        self.audit_alerts[alert_id] = alert
        logger.error(f"Compliance violation alert created: {alert_id}")

    async def search_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        actor_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        resource_type: Optional[str] = None,
        risk_level: Optional[RiskLevel] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        events = list(self.audit_events.values())
        
        # Apply filters
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]
        
        if actor_id:
            events = [e for e in events if e.actor_id == actor_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if resource_type:
            events = [e for e in events if e.resource_type == resource_type]
        
        if risk_level:
            events = [e for e in events if e.risk_level == risk_level]
        
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    async def get_user_activity_summary(
        self,
        actor_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        start_date = datetime.now() - timedelta(days=days)
        user_events = await self.search_events(
            start_date=start_date,
            actor_id=actor_id
        )
        
        summary = {
            "actor_id": actor_id,
            "period_days": days,
            "total_events": len(user_events),
            "event_types": {},
            "resource_types": {},
            "risk_levels": {},
            "recent_alerts": [],
            "access_patterns": {},
            "compliance_status": "compliant"
        }
        
        # Analyze events
        for event in user_events:
            event_type = event.event_type.value
            resource_type = event.resource_type
            risk_level = event.risk_level.value
            
            summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1
            summary["resource_types"][resource_type] = summary["resource_types"].get(resource_type, 0) + 1
            summary["risk_levels"][risk_level] = summary["risk_levels"].get(risk_level, 0) + 1
        
        # Get recent alerts
        recent_alerts = [
            alert for alert in self.audit_alerts.values()
            if any(event.actor_id == actor_id and event.event_id == alert.event_id 
                   for event in user_events)
        ]
        summary["recent_alerts"] = len(recent_alerts)
        
        # Get access patterns
        user_patterns = {
            k: v for k, v in self.access_patterns.items()
            if v.actor_id == actor_id
        }
        summary["access_patterns"] = {
            "total_patterns": len(user_patterns),
            "high_risk_patterns": len([p for p in user_patterns.values() if p.risk_score > 0.7])
        }
        
        return summary

    async def generate_compliance_report(
        self,
        framework: ComplianceFramework,
        start_date: datetime,
        end_date: datetime
    ) -> ComplianceReport:
        report_id = f"compliance_{uuid.uuid4().hex[:8]}"
        
        # Get events for the period
        events = await self.search_events(start_date=start_date, end_date=end_date, limit=10000)
        
        # Filter events relevant to the framework
        relevant_events = [
            e for e in events 
            if framework in e.compliance_frameworks
        ]
        
        # Analyze compliance
        rules = self.compliance_rules.get(framework.value, {})
        required_fields = rules.get("required_fields", [])
        
        violations = []
        compliant_count = 0
        
        for event in relevant_events:
            is_compliant = True
            missing_fields = []
            
            for field in required_fields:
                if not getattr(event, field, None):
                    missing_fields.append(field)
                    is_compliant = False
            
            if is_compliant:
                compliant_count += 1
            else:
                violations.append({
                    "event_id": event.event_id,
                    "timestamp": event.timestamp.isoformat(),
                    "violation_type": "missing_required_fields",
                    "missing_fields": missing_fields,
                    "actor_id": event.actor_id,
                    "resource_type": event.resource_type
                })
        
        # Risk summary
        risk_summary = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for event in relevant_events:
            risk_summary[event.risk_level.value] += 1
        
        # Generate recommendations
        recommendations = await self._generate_compliance_recommendations(
            framework, violations, risk_summary
        )
        
        report = ComplianceReport(
            report_id=report_id,
            framework=framework,
            report_period_start=start_date,
            report_period_end=end_date,
            total_events=len(relevant_events),
            compliant_events=compliant_count,
            violations=violations,
            risk_summary=risk_summary,
            recommendations=recommendations,
            generated_date=datetime.now(),
            generated_by="system"
        )
        
        logger.info(f"Generated compliance report {report_id} for {framework.value}")
        return report

    async def _generate_compliance_recommendations(
        self,
        framework: ComplianceFramework,
        violations: List[Dict],
        risk_summary: Dict[str, int]
    ) -> List[str]:
        recommendations = []
        
        # Field-based recommendations
        if violations:
            missing_fields = set()
            for violation in violations:
                missing_fields.update(violation.get("missing_fields", []))
            
            if missing_fields:
                recommendations.append(
                    f"Ensure all audit logs include required fields: {', '.join(missing_fields)}"
                )
        
        # Risk-based recommendations
        high_risk_events = risk_summary.get("high", 0) + risk_summary.get("critical", 0)
        if high_risk_events > 10:
            recommendations.append("Review and mitigate high-risk activities")
        
        # Framework-specific recommendations
        if framework == ComplianceFramework.GDPR:
            recommendations.append("Ensure data subject access rights are properly logged")
            recommendations.append("Verify legal basis is documented for all personal data processing")
        
        elif framework == ComplianceFramework.HIPAA:
            recommendations.append("Implement minimum necessary access logging")
            recommendations.append("Ensure all PHI access is properly authorized and logged")
        
        elif framework == ComplianceFramework.PCI_DSS:
            recommendations.append("Monitor cardholder data access in real-time")
            recommendations.append("Implement strong access controls for payment systems")
        
        return recommendations

    async def cleanup_expired_events(self) -> int:
        cleaned_count = 0
        current_time = datetime.now()
        
        expired_events = []
        for event_id, event in self.audit_events.items():
            # Determine retention period based on compliance frameworks
            max_retention = 0
            for framework in event.compliance_frameworks:
                retention_days = self.retention_policies.get(framework.value, 365)
                max_retention = max(max_retention, retention_days)
            
            if max_retention == 0:
                max_retention = 365  # Default retention
            
            # Check if event is expired
            if (current_time - event.timestamp).days > max_retention:
                expired_events.append(event_id)
        
        # Remove expired events (or anonymize for GDPR compliance)
        for event_id in expired_events:
            event = self.audit_events[event_id]
            
            # Check if anonymization is required
            gdpr_applicable = ComplianceFramework.GDPR in event.compliance_frameworks
            if gdpr_applicable and event_id not in self.anonymized_events:
                await self._anonymize_event(event_id)
                self.anonymized_events.add(event_id)
            else:
                del self.audit_events[event_id]
                cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} expired audit events")
        return cleaned_count

    async def _anonymize_event(self, event_id: str):
        if event_id not in self.audit_events:
            return
        
        event = self.audit_events[event_id]
        
        # Anonymize personal identifiers
        event.actor_id = f"anonymous_{hashlib.sha256(event.actor_id.encode()).hexdigest()[:8]}"
        event.source_ip = "xxx.xxx.xxx.xxx"
        event.user_agent = None
        event.session_id = None
        
        # Remove detailed personal information from metadata
        if event.metadata:
            personal_fields = ["email", "name", "phone", "address"]
            for field in personal_fields:
                if field in event.metadata:
                    del event.metadata[field]
        
        logger.info(f"Anonymized audit event {event_id}")

    async def export_audit_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json"
    ) -> Dict[str, Any]:
        events = await self.search_events(
            start_date=start_date,
            end_date=end_date,
            limit=100000
        )
        
        export_data = {
            "export_date": datetime.now().isoformat(),
            "period_start": start_date.isoformat() if start_date else None,
            "period_end": end_date.isoformat() if end_date else None,
            "total_events": len(events),
            "events": []
        }
        
        for event in events:
            event_data = asdict(event)
            # Convert enums to strings
            event_data["event_type"] = event.event_type.value
            event_data["action"] = event.action.value
            event_data["status"] = event.status.value
            event_data["risk_level"] = event.risk_level.value
            event_data["compliance_frameworks"] = [f.value for f in event.compliance_frameworks]
            event_data["timestamp"] = event.timestamp.isoformat()
            
            export_data["events"].append(event_data)
        
        logger.info(f"Exported {len(events)} audit events")
        return export_data