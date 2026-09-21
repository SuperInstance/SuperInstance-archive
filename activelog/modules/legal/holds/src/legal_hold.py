from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union, Any
from enum import Enum
import json
import hashlib
import re
from pathlib import Path


class HoldStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RELEASED = "released"
    EXPIRED = "expired"


class CustodianStatus(Enum):
    NOTIFIED = "notified"
    ACKNOWLEDGED = "acknowledged"
    NON_RESPONSIVE = "non_responsive"
    ESCALATED = "escalated"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"


class DocumentStatus(Enum):
    PRESERVED = "preserved"
    AT_RISK = "at_risk"
    DESTROYED = "destroyed"
    RECOVERED = "recovered"
    VERIFIED = "verified"


class NotificationType(Enum):
    INITIAL = "initial"
    REMINDER = "reminder"
    ESCALATION = "escalation"
    RELEASE = "release"
    MODIFICATION = "modification"


class HoldScope(Enum):
    EMAIL = "email"
    DOCUMENTS = "documents"
    DATABASES = "databases"
    SOCIAL_MEDIA = "social_media"
    INSTANT_MESSAGES = "instant_messages"
    VOICE_RECORDINGS = "voice_recordings"
    VIDEO_RECORDINGS = "video_recordings"
    BACKUPS = "backups"
    MOBILE_DATA = "mobile_data"
    CLOUD_STORAGE = "cloud_storage"


@dataclass
class Custodian:
    custodian_id: str
    name: str
    email: str
    department: str
    role: str
    manager: Optional[str] = None
    status: CustodianStatus = CustodianStatus.NOTIFIED
    notification_date: Optional[datetime] = None
    acknowledgment_date: Optional[datetime] = None
    last_reminder_date: Optional[datetime] = None
    escalation_count: int = 0
    compliance_score: float = 0.0
    notes: str = ""


@dataclass
class PreservationRule:
    rule_id: str
    scope: HoldScope
    description: str
    keywords: List[str]
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    file_types: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    retention_period_days: Optional[int] = None


@dataclass
class HoldNotification:
    notification_id: str
    hold_id: str
    custodian_id: str
    notification_type: NotificationType
    sent_date: datetime
    delivery_status: str
    acknowledgment_required: bool = True
    acknowledgment_date: Optional[datetime] = None
    template_used: str = ""
    content: str = ""
    attachments: List[str] = field(default_factory=list)


@dataclass
class ComplianceCheck:
    check_id: str
    hold_id: str
    custodian_id: str
    check_date: datetime
    check_type: str
    result: str
    details: Dict[str, Any] = field(default_factory=dict)
    issues_found: List[str] = field(default_factory=list)
    remediation_actions: List[str] = field(default_factory=list)


@dataclass
class LegalHold:
    hold_id: str
    matter_id: str
    title: str
    description: str
    created_by: str
    created_date: datetime
    status: HoldStatus = HoldStatus.DRAFT
    effective_date: Optional[datetime] = None
    release_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    custodians: List[Custodian] = field(default_factory=list)
    preservation_rules: List[PreservationRule] = field(default_factory=list)
    notifications: List[HoldNotification] = field(default_factory=list)
    compliance_checks: List[ComplianceCheck] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)


class NotificationTemplateManager:
    def __init__(self):
        self.templates = {
            NotificationType.INITIAL: self._get_initial_template(),
            NotificationType.REMINDER: self._get_reminder_template(),
            NotificationType.ESCALATION: self._get_escalation_template(),
            NotificationType.RELEASE: self._get_release_template(),
            NotificationType.MODIFICATION: self._get_modification_template()
        }
    
    def _get_initial_template(self) -> str:
        return """
Subject: Legal Hold Notice - {hold_title}

Dear {custodian_name},

You are receiving this notice because you have been identified as a custodian of documents and electronically stored information that may be relevant to the following matter: {matter_description}

PRESERVATION OBLIGATION:
You must immediately suspend any routine destruction of documents and data that may relate to this matter. This includes:
{preservation_scope}

ACKNOWLEDGMENT REQUIRED:
Please acknowledge receipt of this notice by {acknowledgment_deadline}.

Contact {legal_contact} with any questions.

Thank you for your cooperation.
        """
    
    def _get_reminder_template(self) -> str:
        return """
Subject: REMINDER - Legal Hold Acknowledgment Required - {hold_title}

Dear {custodian_name},

This is a reminder that you have not yet acknowledged receipt of the Legal Hold Notice issued on {initial_notice_date} for matter: {matter_description}

Please acknowledge receipt immediately by responding to this notice.

Contact {legal_contact} with any questions.
        """
    
    def _get_escalation_template(self) -> str:
        return """
Subject: ESCALATION - Legal Hold Non-Compliance - {hold_title}

Dear {manager_name},

Your team member {custodian_name} has not acknowledged the Legal Hold Notice for matter: {matter_description}

Initial notice sent: {initial_notice_date}
Reminders sent: {reminder_count}

Please ensure immediate compliance with this legal preservation obligation.

Contact {legal_contact} immediately.
        """
    
    def _get_release_template(self) -> str:
        return """
Subject: Legal Hold Release - {hold_title}

Dear {custodian_name},

The Legal Hold for matter {matter_description} has been released as of {release_date}.

You may resume normal document retention and destruction policies.

Thank you for your cooperation during this matter.
        """
    
    def _get_modification_template(self) -> str:
        return """
Subject: Legal Hold Modification - {hold_title}

Dear {custodian_name},

The Legal Hold for matter {matter_description} has been modified. Please review the updated preservation requirements:

{updated_requirements}

Contact {legal_contact} with any questions about these changes.
        """
    
    def get_template(self, notification_type: NotificationType) -> str:
        return self.templates.get(notification_type, "")
    
    def customize_template(self, template: str, variables: Dict[str, str]) -> str:
        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", str(value))
        return template


class HoldComplianceMonitor:
    def __init__(self):
        self.risk_keywords = [
            "delete", "destroy", "purge", "cleanup", "archive",
            "remove", "clear", "wipe", "overwrite", "dispose"
        ]
    
    def check_custodian_compliance(self, custodian: Custodian, hold: LegalHold) -> ComplianceCheck:
        check_id = f"comp_{custodian.custodian_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        issues = []
        remediation_actions = []
        
        # Check acknowledgment status
        if custodian.status == CustodianStatus.NON_RESPONSIVE:
            issues.append("Custodian has not acknowledged legal hold notice")
            remediation_actions.append("Send escalation notice to manager")
        
        # Check acknowledgment timing
        if custodian.notification_date and not custodian.acknowledgment_date:
            days_since_notification = (datetime.now() - custodian.notification_date).days
            if days_since_notification > 3:
                issues.append(f"No acknowledgment after {days_since_notification} days")
                remediation_actions.append("Send reminder notice")
        
        # Check compliance score
        if custodian.compliance_score < 0.7:
            issues.append(f"Low compliance score: {custodian.compliance_score}")
            remediation_actions.append("Conduct compliance interview")
        
        result = "COMPLIANT" if not issues else "NON_COMPLIANT"
        
        return ComplianceCheck(
            check_id=check_id,
            hold_id=hold.hold_id,
            custodian_id=custodian.custodian_id,
            check_date=datetime.now(),
            check_type="custodian_compliance",
            result=result,
            issues_found=issues,
            remediation_actions=remediation_actions
        )
    
    def scan_for_destruction_activities(self, custodian_id: str, activity_logs: List[str]) -> List[str]:
        suspicious_activities = []
        
        for log_entry in activity_logs:
            log_lower = log_entry.lower()
            for keyword in self.risk_keywords:
                if keyword in log_lower:
                    suspicious_activities.append(f"Potential destruction activity: {log_entry}")
                    break
        
        return suspicious_activities
    
    def calculate_compliance_score(self, custodian: Custodian, hold: LegalHold) -> float:
        score = 1.0
        
        # Deduct for late acknowledgment
        if custodian.notification_date and custodian.acknowledgment_date:
            response_time = (custodian.acknowledgment_date - custodian.notification_date).days
            if response_time > 1:
                score -= min(0.3, response_time * 0.05)
        elif custodian.notification_date and not custodian.acknowledgment_date:
            score -= 0.5
        
        # Deduct for escalations
        score -= min(0.3, custodian.escalation_count * 0.1)
        
        # Deduct for non-compliance status
        if custodian.status == CustodianStatus.NON_COMPLIANT:
            score -= 0.4
        elif custodian.status == CustodianStatus.NON_RESPONSIVE:
            score -= 0.3
        
        return max(0.0, score)


class LegalHoldManager:
    def __init__(self):
        self.holds: Dict[str, LegalHold] = {}
        self.template_manager = NotificationTemplateManager()
        self.compliance_monitor = HoldComplianceMonitor()
    
    def create_hold(self, hold_id: str, matter_id: str, title: str, description: str, created_by: str) -> LegalHold:
        hold = LegalHold(
            hold_id=hold_id,
            matter_id=matter_id,
            title=title,
            description=description,
            created_by=created_by,
            created_date=datetime.now()
        )
        
        self.holds[hold_id] = hold
        self._add_audit_entry(hold, "hold_created", {"created_by": created_by})
        return hold
    
    def add_custodian(self, hold_id: str, custodian: Custodian) -> bool:
        if hold_id not in self.holds:
            return False
        
        hold = self.holds[hold_id]
        
        # Check if custodian already exists
        existing_custodian_ids = {c.custodian_id for c in hold.custodians}
        if custodian.custodian_id in existing_custodian_ids:
            return False
        
        hold.custodians.append(custodian)
        self._add_audit_entry(hold, "custodian_added", {"custodian_id": custodian.custodian_id})
        return True
    
    def add_preservation_rule(self, hold_id: str, rule: PreservationRule) -> bool:
        if hold_id not in self.holds:
            return False
        
        hold = self.holds[hold_id]
        hold.preservation_rules.append(rule)
        self._add_audit_entry(hold, "preservation_rule_added", {"rule_id": rule.rule_id})
        return True
    
    def activate_hold(self, hold_id: str) -> bool:
        if hold_id not in self.holds:
            return False
        
        hold = self.holds[hold_id]
        hold.status = HoldStatus.ACTIVE
        hold.effective_date = datetime.now()
        
        # Send initial notifications to all custodians
        for custodian in hold.custodians:
            self._send_notification(hold, custodian, NotificationType.INITIAL)
        
        self._add_audit_entry(hold, "hold_activated", {"effective_date": hold.effective_date.isoformat()})
        return True
    
    def release_hold(self, hold_id: str, released_by: str) -> bool:
        if hold_id not in self.holds:
            return False
        
        hold = self.holds[hold_id]
        hold.status = HoldStatus.RELEASED
        hold.release_date = datetime.now()
        
        # Send release notifications to all custodians
        for custodian in hold.custodians:
            self._send_notification(hold, custodian, NotificationType.RELEASE)
        
        self._add_audit_entry(hold, "hold_released", {
            "released_by": released_by,
            "release_date": hold.release_date.isoformat()
        })
        return True
    
    def _send_notification(self, hold: LegalHold, custodian: Custodian, notification_type: NotificationType) -> HoldNotification:
        notification_id = f"notif_{hold.hold_id}_{custodian.custodian_id}_{len(hold.notifications)}"
        
        template = self.template_manager.get_template(notification_type)
        variables = {
            "hold_title": hold.title,
            "custodian_name": custodian.name,
            "matter_description": hold.description,
            "legal_contact": "legal@company.com",
            "acknowledgment_deadline": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        }
        
        content = self.template_manager.customize_template(template, variables)
        
        notification = HoldNotification(
            notification_id=notification_id,
            hold_id=hold.hold_id,
            custodian_id=custodian.custodian_id,
            notification_type=notification_type,
            sent_date=datetime.now(),
            delivery_status="sent",
            content=content
        )
        
        hold.notifications.append(notification)
        
        # Update custodian status
        if notification_type == NotificationType.INITIAL:
            custodian.notification_date = notification.sent_date
            custodian.status = CustodianStatus.NOTIFIED
        elif notification_type == NotificationType.REMINDER:
            custodian.last_reminder_date = notification.sent_date
        elif notification_type == NotificationType.ESCALATION:
            custodian.escalation_count += 1
            custodian.status = CustodianStatus.ESCALATED
        
        return notification
    
    def acknowledge_hold(self, hold_id: str, custodian_id: str) -> bool:
        if hold_id not in self.holds:
            return False
        
        hold = self.holds[hold_id]
        custodian = self._find_custodian(hold, custodian_id)
        
        if not custodian:
            return False
        
        custodian.acknowledgment_date = datetime.now()
        custodian.status = CustodianStatus.ACKNOWLEDGED
        custodian.compliance_score = self.compliance_monitor.calculate_compliance_score(custodian, hold)
        
        self._add_audit_entry(hold, "hold_acknowledged", {
            "custodian_id": custodian_id,
            "acknowledgment_date": custodian.acknowledgment_date.isoformat()
        })
        
        return True
    
    def run_compliance_checks(self, hold_id: str) -> List[ComplianceCheck]:
        if hold_id not in self.holds:
            return []
        
        hold = self.holds[hold_id]
        checks = []
        
        for custodian in hold.custodians:
            check = self.compliance_monitor.check_custodian_compliance(custodian, hold)
            checks.append(check)
            hold.compliance_checks.append(check)
            
            # Update custodian compliance score
            custodian.compliance_score = self.compliance_monitor.calculate_compliance_score(custodian, hold)
        
        return checks
    
    def send_reminders(self, hold_id: str) -> int:
        if hold_id not in self.holds:
            return 0
        
        hold = self.holds[hold_id]
        reminders_sent = 0
        
        for custodian in hold.custodians:
            if custodian.status == CustodianStatus.NOTIFIED and not custodian.acknowledgment_date:
                days_since_notification = (datetime.now() - custodian.notification_date).days if custodian.notification_date else 0
                
                if days_since_notification >= 3:
                    self._send_notification(hold, custodian, NotificationType.REMINDER)
                    reminders_sent += 1
        
        return reminders_sent
    
    def get_hold_status_report(self, hold_id: str) -> Dict[str, Any]:
        if hold_id not in self.holds:
            return {}
        
        hold = self.holds[hold_id]
        
        custodian_stats = {
            "total": len(hold.custodians),
            "acknowledged": len([c for c in hold.custodians if c.status == CustodianStatus.ACKNOWLEDGED]),
            "non_responsive": len([c for c in hold.custodians if c.status == CustodianStatus.NON_RESPONSIVE]),
            "escalated": len([c for c in hold.custodians if c.status == CustodianStatus.ESCALATED])
        }
        
        avg_compliance_score = sum(c.compliance_score for c in hold.custodians) / len(hold.custodians) if hold.custodians else 0
        
        return {
            "hold_id": hold.hold_id,
            "title": hold.title,
            "status": hold.status.value,
            "created_date": hold.created_date.isoformat(),
            "effective_date": hold.effective_date.isoformat() if hold.effective_date else None,
            "custodian_stats": custodian_stats,
            "notifications_sent": len(hold.notifications),
            "compliance_checks": len(hold.compliance_checks),
            "average_compliance_score": round(avg_compliance_score, 2),
            "preservation_rules": len(hold.preservation_rules)
        }
    
    def export_hold_data(self, hold_id: str, format_type: str = "json") -> str:
        if hold_id not in self.holds:
            return ""
        
        hold = self.holds[hold_id]
        
        if format_type == "json":
            return self._export_to_json(hold)
        else:
            return ""
    
    def _export_to_json(self, hold: LegalHold) -> str:
        export_data = {
            "hold_id": hold.hold_id,
            "matter_id": hold.matter_id,
            "title": hold.title,
            "description": hold.description,
            "created_by": hold.created_by,
            "created_date": hold.created_date.isoformat(),
            "status": hold.status.value,
            "effective_date": hold.effective_date.isoformat() if hold.effective_date else None,
            "release_date": hold.release_date.isoformat() if hold.release_date else None,
            "custodians": [
                {
                    "custodian_id": c.custodian_id,
                    "name": c.name,
                    "email": c.email,
                    "department": c.department,
                    "role": c.role,
                    "status": c.status.value,
                    "compliance_score": c.compliance_score,
                    "notification_date": c.notification_date.isoformat() if c.notification_date else None,
                    "acknowledgment_date": c.acknowledgment_date.isoformat() if c.acknowledgment_date else None
                } for c in hold.custodians
            ],
            "preservation_rules": [
                {
                    "rule_id": r.rule_id,
                    "scope": r.scope.value,
                    "description": r.description,
                    "keywords": r.keywords,
                    "date_range_start": r.date_range_start.isoformat() if r.date_range_start else None,
                    "date_range_end": r.date_range_end.isoformat() if r.date_range_end else None
                } for r in hold.preservation_rules
            ],
            "notifications": len(hold.notifications),
            "compliance_checks": len(hold.compliance_checks),
            "audit_trail": hold.audit_trail
        }
        
        return json.dumps(export_data, indent=2)
    
    def _find_custodian(self, hold: LegalHold, custodian_id: str) -> Optional[Custodian]:
        for custodian in hold.custodians:
            if custodian.custodian_id == custodian_id:
                return custodian
        return None
    
    def _add_audit_entry(self, hold: LegalHold, action: str, details: Dict[str, Any]):
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "hold_id": hold.hold_id
        }
        hold.audit_trail.append(audit_entry)


class HoldMetricsCalculator:
    @staticmethod
    def calculate_acknowledgment_rate(hold: LegalHold) -> float:
        if not hold.custodians:
            return 0.0
        
        acknowledged = len([c for c in hold.custodians if c.status == CustodianStatus.ACKNOWLEDGED])
        return acknowledged / len(hold.custodians)
    
    @staticmethod
    def calculate_average_response_time(hold: LegalHold) -> Optional[float]:
        response_times = []
        
        for custodian in hold.custodians:
            if custodian.notification_date and custodian.acknowledgment_date:
                response_time = (custodian.acknowledgment_date - custodian.notification_date).total_seconds() / 3600  # hours
                response_times.append(response_time)
        
        return sum(response_times) / len(response_times) if response_times else None
    
    @staticmethod
    def identify_high_risk_custodians(hold: LegalHold, threshold: float = 0.5) -> List[Custodian]:
        return [c for c in hold.custodians if c.compliance_score < threshold]
    
    @staticmethod
    def get_hold_effectiveness_score(hold: LegalHold) -> float:
        if not hold.custodians:
            return 0.0
        
        acknowledgment_rate = HoldMetricsCalculator.calculate_acknowledgment_rate(hold)
        avg_compliance = sum(c.compliance_score for c in hold.custodians) / len(hold.custodians)
        
        # Weight acknowledgment rate (40%) and compliance score (60%)
        effectiveness_score = (acknowledgment_rate * 0.4) + (avg_compliance * 0.6)
        return effectiveness_score