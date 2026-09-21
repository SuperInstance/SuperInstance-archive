"""
Data Governance Manager
Implements comprehensive data governance, compliance, and policy management
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import logging
import hashlib
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete

from ..models.governance import (
    DataPolicy, DataClassification, DataLineage, 
    ComplianceRule, AuditLog, DataRetention, 
    AccessControl, PrivacyRule
)
from ..utils.config import Config

logger = logging.getLogger(__name__)


class DataClassificationLevel(Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal" 
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    NIST = "nist"


class PolicyType(Enum):
    """Types of data policies"""
    RETENTION = "retention"
    ACCESS_CONTROL = "access_control"
    PRIVACY = "privacy"
    QUALITY = "quality"
    USAGE = "usage"
    SHARING = "sharing"
    ARCHIVAL = "archival"
    DELETION = "deletion"


class AccessLevel(Enum):
    """Data access levels"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    NONE = "none"


@dataclass
class DataGovernancePolicy:
    """Data governance policy definition"""
    policy_id: str
    policy_name: str
    policy_type: PolicyType
    classification_level: DataClassificationLevel
    compliance_frameworks: List[ComplianceFramework]
    scope: Dict[str, Any]  # services, entities, fields
    rules: List[Dict[str, Any]]
    enforcement_mode: str  # 'enforce', 'warn', 'monitor'
    exceptions: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    effective_date: datetime
    expiration_date: Optional[datetime]
    is_active: bool
    created_by: str
    approved_by: Optional[str]


@dataclass
class DataLineageRecord:
    """Data lineage tracking record"""
    lineage_id: str
    source_service: str
    source_entity: str
    source_field: str
    target_service: str
    target_entity: str
    target_field: str
    transformation_type: str
    transformation_logic: Optional[str]
    data_flow_direction: str  # 'upstream', 'downstream'
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class ComplianceViolation:
    """Compliance violation record"""
    violation_id: str
    policy_id: str
    service_name: str
    entity_name: str
    field_name: Optional[str]
    violation_type: str
    severity: str
    description: str
    detected_at: datetime
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    false_positive: bool


class DataGovernanceManager:
    """Manages data governance across all DMLog services"""
    
    def __init__(self, service_registry, relationship_mapper, db_session_factory, config: Config):
        self.service_registry = service_registry
        self.relationship_mapper = relationship_mapper
        self.db_session_factory = db_session_factory
        self.config = config
        
        # Governance policies
        self.active_policies: Dict[str, DataGovernancePolicy] = {}
        self.compliance_rules: Dict[str, Any] = {}
        
        # Data classification
        self.data_classifications: Dict[str, DataClassificationLevel] = {}
        self.sensitive_data_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        }
        
        # Data lineage
        self.lineage_graph: Dict[str, List[DataLineageRecord]] = defaultdict(list)
        
        # Audit and compliance tracking
        self.audit_logs: List[Dict[str, Any]] = []
        self.compliance_violations: List[ComplianceViolation] = []
        
        # Access control
        self.access_policies: Dict[str, Dict[str, AccessLevel]] = {}
        
        # Background tasks
        self._governance_tasks: Set[asyncio.Task] = set()

    async def initialize(self):
        """Initialize the data governance manager"""
        logger.info("Initializing Data Governance Manager")
        
        try:
            # Load existing policies
            await self._load_governance_policies()
            
            # Create default DMLog governance policies
            await self._create_default_policies()
            
            # Initialize data classification
            await self._initialize_data_classification()
            
            # Build data lineage
            await self._build_data_lineage()
            
            # Start governance monitoring
            self._start_governance_monitoring()
            
            logger.info("Data Governance Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize data governance manager: {e}")
            raise

    async def _load_governance_policies(self):
        """Load governance policies from database"""
        async with self.db_session_factory() as session:
            result = await session.execute(select(DataPolicy))
            policies = result.scalars().all()
            
            for policy in policies:
                governance_policy = DataGovernancePolicy(
                    policy_id=policy.id,
                    policy_name=policy.policy_name,
                    policy_type=PolicyType(policy.policy_type),
                    classification_level=DataClassificationLevel(policy.classification_level),
                    compliance_frameworks=[ComplianceFramework(f) for f in json.loads(policy.compliance_frameworks)],
                    scope=json.loads(policy.scope),
                    rules=json.loads(policy.rules),
                    enforcement_mode=policy.enforcement_mode,
                    exceptions=json.loads(policy.exceptions or "[]"),
                    metadata=json.loads(policy.metadata or "{}"),
                    effective_date=policy.effective_date,
                    expiration_date=policy.expiration_date,
                    is_active=policy.is_active,
                    created_by=policy.created_by,
                    approved_by=policy.approved_by
                )
                
                self.active_policies[policy.id] = governance_policy

    async def _create_default_policies(self):
        """Create default governance policies for DMLog"""
        
        default_policies = [
            # User Data Privacy Policy (GDPR Compliance)
            DataGovernancePolicy(
                policy_id=str(uuid.uuid4()),
                policy_name="User Data Privacy Protection",
                policy_type=PolicyType.PRIVACY,
                classification_level=DataClassificationLevel.CONFIDENTIAL,
                compliance_frameworks=[ComplianceFramework.GDPR],
                scope={
                    "services": ["dmlog-core", "dmlog-characters", "dmlog-session"],
                    "entities": ["users", "characters", "sessions"],
                    "fields": ["email", "name", "personal_data"]
                },
                rules=[
                    {
                        "rule_type": "anonymization",
                        "description": "Anonymize user data after account deletion",
                        "conditions": {"user_deleted": True},
                        "actions": ["anonymize_personal_data", "update_references"]
                    },
                    {
                        "rule_type": "consent_tracking",
                        "description": "Track user consent for data processing",
                        "conditions": {"data_processing": True},
                        "actions": ["log_consent", "validate_consent"]
                    }
                ],
                enforcement_mode="enforce",
                exceptions=[],
                metadata={
                    "legal_basis": "Article 6(1)(a) - Consent",
                    "data_protection_officer": "dpo@dmlog.app"
                },
                effective_date=datetime.now(),
                expiration_date=None,
                is_active=True,
                created_by="system",
                approved_by="data-governance-team"
            ),
            
            # Campaign Data Retention Policy
            DataGovernancePolicy(
                policy_id=str(uuid.uuid4()),
                policy_name="Campaign Data Retention",
                policy_type=PolicyType.RETENTION,
                classification_level=DataClassificationLevel.INTERNAL,
                compliance_frameworks=[ComplianceFramework.ISO27001],
                scope={
                    "services": ["dmlog-core", "dmlog-session", "dmlog-stream"],
                    "entities": ["campaigns", "sessions", "recordings"],
                    "fields": ["*"]
                },
                rules=[
                    {
                        "rule_type": "retention_period",
                        "description": "Retain campaign data for 7 years",
                        "conditions": {"campaign_completed": True},
                        "actions": ["archive_after_7_years", "delete_after_10_years"]
                    },
                    {
                        "rule_type": "active_campaign",
                        "description": "Keep active campaign data indefinitely",
                        "conditions": {"campaign_active": True},
                        "actions": ["retain_indefinitely"]
                    }
                ],
                enforcement_mode="enforce",
                exceptions=[
                    {
                        "condition": {"premium_account": True},
                        "retention_extension": "indefinite"
                    }
                ],
                metadata={
                    "business_justification": "Campaign continuity and user experience"
                },
                effective_date=datetime.now(),
                expiration_date=None,
                is_active=True,
                created_by="system",
                approved_by="data-governance-team"
            ),
            
            # Payment Data Security Policy (PCI DSS)
            DataGovernancePolicy(
                policy_id=str(uuid.uuid4()),
                policy_name="Payment Data Security",
                policy_type=PolicyType.ACCESS_CONTROL,
                classification_level=DataClassificationLevel.RESTRICTED,
                compliance_frameworks=[ComplianceFramework.PCI_DSS],
                scope={
                    "services": ["dmlog-marketplace"],
                    "entities": ["payments", "subscriptions"],
                    "fields": ["card_number", "payment_token", "billing_address"]
                },
                rules=[
                    {
                        "rule_type": "encryption_required",
                        "description": "Encrypt all payment data at rest and in transit",
                        "conditions": {"contains_payment_data": True},
                        "actions": ["encrypt_at_rest", "encrypt_in_transit", "tokenize_sensitive_fields"]
                    },
                    {
                        "rule_type": "access_restriction",
                        "description": "Restrict access to payment data",
                        "conditions": {"accessing_payment_data": True},
                        "actions": ["require_mfa", "log_access", "validate_business_need"]
                    }
                ],
                enforcement_mode="enforce",
                exceptions=[],
                metadata={
                    "compliance_level": "PCI DSS Level 1",
                    "security_contact": "security@dmlog.app"
                },
                effective_date=datetime.now(),
                expiration_date=None,
                is_active=True,
                created_by="system",
                approved_by="security-team"
            ),
            
            # Data Quality Governance Policy
            DataGovernancePolicy(
                policy_id=str(uuid.uuid4()),
                policy_name="Data Quality Standards",
                policy_type=PolicyType.QUALITY,
                classification_level=DataClassificationLevel.INTERNAL,
                compliance_frameworks=[ComplianceFramework.ISO27001],
                scope={
                    "services": ["*"],
                    "entities": ["*"],
                    "fields": ["*"]
                },
                rules=[
                    {
                        "rule_type": "completeness_threshold",
                        "description": "Enforce minimum data completeness",
                        "conditions": {"critical_data": True},
                        "actions": ["reject_incomplete_data", "alert_data_steward"]
                    },
                    {
                        "rule_type": "consistency_validation",
                        "description": "Validate cross-service data consistency",
                        "conditions": {"cross_service_reference": True},
                        "actions": ["validate_references", "auto_reconcile"]
                    }
                ],
                enforcement_mode="warn",
                exceptions=[],
                metadata={
                    "data_steward": "data-team@dmlog.app"
                },
                effective_date=datetime.now(),
                expiration_date=None,
                is_active=True,
                created_by="system",
                approved_by="data-governance-team"
            ),
            
            # Cross-Border Data Transfer Policy
            DataGovernancePolicy(
                policy_id=str(uuid.uuid4()),
                policy_name="Cross-Border Data Transfer",
                policy_type=PolicyType.SHARING,
                classification_level=DataClassificationLevel.CONFIDENTIAL,
                compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.CCPA],
                scope={
                    "services": ["*"],
                    "entities": ["*"],
                    "fields": ["personal_data", "user_content"]
                },
                rules=[
                    {
                        "rule_type": "adequacy_decision",
                        "description": "Ensure adequate protection for international transfers",
                        "conditions": {"international_transfer": True},
                        "actions": ["check_adequacy_decision", "require_safeguards"]
                    },
                    {
                        "rule_type": "user_consent",
                        "description": "Obtain explicit consent for data transfers",
                        "conditions": {"transfer_to_third_country": True},
                        "actions": ["obtain_explicit_consent", "document_legal_basis"]
                    }
                ],
                enforcement_mode="enforce",
                exceptions=[
                    {
                        "condition": {"adequacy_decision_exists": True},
                        "action": "allow_transfer"
                    }
                ],
                metadata={
                    "legal_basis": "Article 49 GDPR",
                    "adequacy_countries": ["US", "Canada", "UK", "Switzerland"]
                },
                effective_date=datetime.now(),
                expiration_date=None,
                is_active=True,
                created_by="system",
                approved_by="legal-team"
            )
        ]
        
        # Store policies
        for policy in default_policies:
            if policy.policy_id not in self.active_policies:
                await self._store_governance_policy(policy)

    async def _store_governance_policy(self, policy: DataGovernancePolicy):
        """Store governance policy in database"""
        async with self.db_session_factory() as session:
            try:
                data_policy = DataPolicy(
                    id=policy.policy_id,
                    policy_name=policy.policy_name,
                    policy_type=policy.policy_type.value,
                    classification_level=policy.classification_level.value,
                    compliance_frameworks=json.dumps([f.value for f in policy.compliance_frameworks]),
                    scope=json.dumps(policy.scope),
                    rules=json.dumps(policy.rules),
                    enforcement_mode=policy.enforcement_mode,
                    exceptions=json.dumps(policy.exceptions),
                    metadata=json.dumps(policy.metadata),
                    effective_date=policy.effective_date,
                    expiration_date=policy.expiration_date,
                    is_active=policy.is_active,
                    created_by=policy.created_by,
                    approved_by=policy.approved_by,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                session.add(data_policy)
                await session.commit()
                
                self.active_policies[policy.policy_id] = policy
                
                logger.info(f"Stored governance policy: {policy.policy_name}")
                
            except Exception as e:
                logger.error(f"Failed to store governance policy: {e}")
                await session.rollback()

    async def _initialize_data_classification(self):
        """Initialize data classification for DMLog entities"""
        
        # Define classification rules
        classification_rules = {
            # User data - Confidential
            'dmlog-core.users.email': DataClassificationLevel.CONFIDENTIAL,
            'dmlog-core.users.password_hash': DataClassificationLevel.RESTRICTED,
            'dmlog-core.users.personal_info': DataClassificationLevel.CONFIDENTIAL,
            
            # Payment data - Restricted
            'dmlog-marketplace.payments.card_number': DataClassificationLevel.RESTRICTED,
            'dmlog-marketplace.payments.billing_address': DataClassificationLevel.CONFIDENTIAL,
            
            # Campaign data - Internal
            'dmlog-core.campaigns.name': DataClassificationLevel.INTERNAL,
            'dmlog-core.campaigns.description': DataClassificationLevel.INTERNAL,
            
            # Character data - Internal
            'dmlog-characters.characters.name': DataClassificationLevel.INTERNAL,
            'dmlog-characters.characters.backstory': DataClassificationLevel.INTERNAL,
            
            # Session recordings - Confidential (may contain personal conversations)
            'dmlog-stream.recordings.audio_data': DataClassificationLevel.CONFIDENTIAL,
            'dmlog-stream.recordings.video_data': DataClassificationLevel.CONFIDENTIAL,
            
            # System data - Public
            'dmlog-core.system.version': DataClassificationLevel.PUBLIC,
            'dmlog-core.system.health_status': DataClassificationLevel.PUBLIC
        }
        
        self.data_classifications = classification_rules
        
        # Store classifications in database
        for data_path, classification in classification_rules.items():
            await self._store_data_classification(data_path, classification)

    async def _store_data_classification(self, data_path: str, classification: DataClassificationLevel):
        """Store data classification in database"""
        async with self.db_session_factory() as session:
            try:
                parts = data_path.split('.')
                service_name = parts[0] if len(parts) > 0 else 'unknown'
                entity_name = parts[1] if len(parts) > 1 else 'unknown'
                field_name = parts[2] if len(parts) > 2 else 'unknown'
                
                data_classification = DataClassification(
                    id=str(uuid.uuid4()),
                    service_name=service_name,
                    entity_name=entity_name,
                    field_name=field_name,
                    classification_level=classification.value,
                    classification_reason="Default DMLog classification",
                    classified_by="system",
                    classified_at=datetime.now(),
                    created_at=datetime.now()
                )
                
                session.add(data_classification)
                await session.commit()
                
            except Exception as e:
                logger.error(f"Failed to store data classification: {e}")
                await session.rollback()

    async def _build_data_lineage(self):
        """Build data lineage from relationship mappings"""
        try:
            # Get all relationship mappings
            if hasattr(self.relationship_mapper, 'service_relationships'):
                for source_key, targets in self.relationship_mapper.service_relationships.items():
                    source_service, source_entity = source_key.split('.', 1)
                    
                    for target_key, mappings in targets.items():
                        target_service, target_entity = target_key.split('.', 1)
                        
                        for mapping in mappings:
                            lineage_record = DataLineageRecord(
                                lineage_id=str(uuid.uuid4()),
                                source_service=mapping.source_service,
                                source_entity=mapping.source_entity,
                                source_field=mapping.source_field,
                                target_service=mapping.target_service,
                                target_entity=mapping.target_entity,
                                target_field=mapping.target_field,
                                transformation_type=mapping.relationship_type.value if hasattr(mapping.relationship_type, 'value') else str(mapping.relationship_type),
                                transformation_logic=mapping.transformation_logic,
                                data_flow_direction="downstream",
                                created_at=datetime.now(),
                                metadata={
                                    'strength': mapping.strength.value if hasattr(mapping.strength, 'value') else str(mapping.strength),
                                    'bidirectional': mapping.is_bidirectional
                                }
                            )
                            
                            lineage_key = f"{mapping.source_service}.{mapping.source_entity}.{mapping.source_field}"
                            self.lineage_graph[lineage_key].append(lineage_record)
                            
                            # Store in database
                            await self._store_data_lineage(lineage_record)
            
            logger.info(f"Built data lineage for {len(self.lineage_graph)} data elements")
            
        except Exception as e:
            logger.error(f"Failed to build data lineage: {e}")

    async def _store_data_lineage(self, lineage_record: DataLineageRecord):
        """Store data lineage record in database"""
        async with self.db_session_factory() as session:
            try:
                data_lineage = DataLineage(
                    id=lineage_record.lineage_id,
                    source_service=lineage_record.source_service,
                    source_entity=lineage_record.source_entity,
                    source_field=lineage_record.source_field,
                    target_service=lineage_record.target_service,
                    target_entity=lineage_record.target_entity,
                    target_field=lineage_record.target_field,
                    transformation_type=lineage_record.transformation_type,
                    transformation_logic=lineage_record.transformation_logic,
                    data_flow_direction=lineage_record.data_flow_direction,
                    metadata=json.dumps(lineage_record.metadata),
                    created_at=lineage_record.created_at
                )
                
                session.add(data_lineage)
                await session.commit()
                
            except Exception as e:
                logger.error(f"Failed to store data lineage: {e}")
                await session.rollback()

    def _start_governance_monitoring(self):
        """Start governance monitoring tasks"""
        
        # Policy compliance monitoring
        task1 = asyncio.create_task(self._compliance_monitoring_loop())
        self._governance_tasks.add(task1)
        
        # Data classification scanning
        task2 = asyncio.create_task(self._classification_scanning_loop())
        self._governance_tasks.add(task2)
        
        # Access control monitoring
        task3 = asyncio.create_task(self._access_control_monitoring_loop())
        self._governance_tasks.add(task3)
        
        # Data retention enforcement
        task4 = asyncio.create_task(self._retention_enforcement_loop())
        self._governance_tasks.add(task4)
        
        # Audit logging
        task5 = asyncio.create_task(self._audit_logging_loop())
        self._governance_tasks.add(task5)

    async def _compliance_monitoring_loop(self):
        """Monitor policy compliance"""
        while True:
            try:
                await self._check_policy_compliance()
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in compliance monitoring: {e}")
                await asyncio.sleep(300)

    async def _check_policy_compliance(self):
        """Check compliance with all active policies"""
        try:
            for policy in self.active_policies.values():
                if not policy.is_active:
                    continue
                
                # Check if policy is in effect
                current_time = datetime.now()
                if current_time < policy.effective_date:
                    continue
                if policy.expiration_date and current_time > policy.expiration_date:
                    continue
                
                # Execute compliance checks based on policy type
                violations = await self._execute_policy_compliance_check(policy)
                
                for violation in violations:
                    self.compliance_violations.append(violation)
                    await self._handle_compliance_violation(violation)
                    
        except Exception as e:
            logger.error(f"Error checking policy compliance: {e}")

    async def _execute_policy_compliance_check(self, policy: DataGovernancePolicy) -> List[ComplianceViolation]:
        """Execute compliance check for a specific policy"""
        violations = []
        
        try:
            if policy.policy_type == PolicyType.PRIVACY:
                violations.extend(await self._check_privacy_compliance(policy))
            elif policy.policy_type == PolicyType.RETENTION:
                violations.extend(await self._check_retention_compliance(policy))
            elif policy.policy_type == PolicyType.ACCESS_CONTROL:
                violations.extend(await self._check_access_control_compliance(policy))
            elif policy.policy_type == PolicyType.QUALITY:
                violations.extend(await self._check_quality_compliance(policy))
            elif policy.policy_type == PolicyType.SHARING:
                violations.extend(await self._check_sharing_compliance(policy))
                
        except Exception as e:
            logger.error(f"Error executing compliance check for policy {policy.policy_name}: {e}")
        
        return violations

    async def _check_privacy_compliance(self, policy: DataGovernancePolicy) -> List[ComplianceViolation]:
        """Check privacy policy compliance"""
        violations = []
        
        # Check for GDPR compliance
        if ComplianceFramework.GDPR in policy.compliance_frameworks:
            # Check for consent tracking
            # Check for data anonymization
            # Check for right to be forgotten compliance
            
            # Mock violation for demonstration
            if datetime.now().hour % 12 == 0:  # Random trigger for demo
                violation = ComplianceViolation(
                    violation_id=str(uuid.uuid4()),
                    policy_id=policy.policy_id,
                    service_name="dmlog-core",
                    entity_name="users",
                    field_name="personal_data",
                    violation_type="missing_consent",
                    severity="high",
                    description="User data processed without explicit consent record",
                    detected_at=datetime.now(),
                    resolved_at=None,
                    resolution_notes=None,
                    false_positive=False
                )
                violations.append(violation)
        
        return violations

    async def _check_retention_compliance(self, policy: DataGovernancePolicy) -> List[ComplianceViolation]:
        """Check data retention policy compliance"""
        violations = []
        
        # Check for data that should have been archived or deleted
        # This would involve checking actual service data
        
        return violations

    async def _check_access_control_compliance(self, policy: DataGovernancePolicy) -> List[ComplianceViolation]:
        """Check access control policy compliance"""
        violations = []
        
        # Check for unauthorized access to restricted data
        # Check for MFA requirements
        # Check for access logging
        
        return violations

    async def _check_quality_compliance(self, policy: DataGovernancePolicy) -> List[ComplianceViolation]:
        """Check data quality policy compliance"""
        violations = []
        
        # This would integrate with the Data Quality Monitor
        # Check for data quality violations that breach governance policies
        
        return violations

    async def _check_sharing_compliance(self, policy: DataGovernancePolicy) -> List[ComplianceViolation]:
        """Check data sharing policy compliance"""
        violations = []
        
        # Check for unauthorized data sharing
        # Check for cross-border transfer compliance
        
        return violations

    async def _handle_compliance_violation(self, violation: ComplianceViolation):
        """Handle a compliance violation"""
        try:
            # Log the violation
            await self._log_audit_event("compliance_violation", {
                'violation_id': violation.violation_id,
                'policy_id': violation.policy_id,
                'service': violation.service_name,
                'severity': violation.severity,
                'description': violation.description
            })
            
            # Send alert based on severity
            if violation.severity in ['critical', 'high']:
                await self._send_compliance_alert(violation)
            
            # Auto-remediate if possible
            await self._attempt_auto_remediation(violation)
            
        except Exception as e:
            logger.error(f"Error handling compliance violation: {e}")

    async def _send_compliance_alert(self, violation: ComplianceViolation):
        """Send compliance violation alert"""
        alert_data = {
            'alert_type': 'governance_violation',
            'violation_id': violation.violation_id,
            'policy_id': violation.policy_id,
            'service': violation.service_name,
            'entity': violation.entity_name,
            'field': violation.field_name,
            'severity': violation.severity,
            'description': violation.description,
            'detected_at': violation.detected_at.isoformat()
        }
        
        logger.warning(f"GOVERNANCE ALERT: {alert_data}")
        
        # In production, send to alerting system

    async def _attempt_auto_remediation(self, violation: ComplianceViolation):
        """Attempt automatic remediation of compliance violation"""
        try:
            # Implement auto-remediation logic based on violation type
            if violation.violation_type == "missing_consent":
                # Flag for manual review
                logger.info(f"Flagging violation {violation.violation_id} for manual review")
            elif violation.violation_type == "data_retention_exceeded":
                # Archive old data
                logger.info(f"Triggering data archival for violation {violation.violation_id}")
            
        except Exception as e:
            logger.error(f"Error in auto-remediation: {e}")

    async def _classification_scanning_loop(self):
        """Periodically scan for sensitive data that needs classification"""
        while True:
            try:
                await self._scan_for_sensitive_data()
                await asyncio.sleep(1800)  # Scan every 30 minutes
                
            except Exception as e:
                logger.error(f"Error in classification scanning: {e}")
                await asyncio.sleep(1800)

    async def _scan_for_sensitive_data(self):
        """Scan services for sensitive data patterns"""
        try:
            # This would scan actual service data for PII patterns
            # For now, just log the activity
            logger.info("Scanning for sensitive data patterns")
            
            # In a real implementation, this would:
            # 1. Query each service for data samples
            # 2. Apply regex patterns to detect PII
            # 3. Classify newly discovered sensitive data
            # 4. Update data classifications
            
        except Exception as e:
            logger.error(f"Error scanning for sensitive data: {e}")

    async def _access_control_monitoring_loop(self):
        """Monitor access control compliance"""
        while True:
            try:
                await self._monitor_data_access()
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"Error in access control monitoring: {e}")
                await asyncio.sleep(60)

    async def _monitor_data_access(self):
        """Monitor data access for compliance"""
        # This would monitor actual data access patterns
        # Check for unauthorized access attempts
        # Validate access permissions
        pass

    async def _retention_enforcement_loop(self):
        """Enforce data retention policies"""
        while True:
            try:
                await self._enforce_data_retention()
                await asyncio.sleep(86400)  # Check daily
                
            except Exception as e:
                logger.error(f"Error in retention enforcement: {e}")
                await asyncio.sleep(86400)

    async def _enforce_data_retention(self):
        """Enforce data retention policies"""
        try:
            # Check for data that exceeds retention periods
            # Archive or delete data as required by policies
            
            logger.info("Enforcing data retention policies")
            
            for policy in self.active_policies.values():
                if policy.policy_type == PolicyType.RETENTION and policy.is_active:
                    await self._execute_retention_policy(policy)
                    
        except Exception as e:
            logger.error(f"Error enforcing data retention: {e}")

    async def _execute_retention_policy(self, policy: DataGovernancePolicy):
        """Execute a specific retention policy"""
        try:
            # Parse retention rules
            for rule in policy.rules:
                if rule['rule_type'] == 'retention_period':
                    # Check services in scope
                    for service in policy.scope.get('services', []):
                        # In real implementation, query service for old data
                        logger.info(f"Checking retention for {service}")
                        
        except Exception as e:
            logger.error(f"Error executing retention policy: {e}")

    async def _audit_logging_loop(self):
        """Continuous audit logging"""
        while True:
            try:
                # Flush audit logs to persistent storage
                await self._flush_audit_logs()
                await asyncio.sleep(300)  # Flush every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in audit logging: {e}")
                await asyncio.sleep(300)

    async def _log_audit_event(self, event_type: str, event_data: Dict[str, Any]):
        """Log an audit event"""
        try:
            audit_entry = {
                'audit_id': str(uuid.uuid4()),
                'event_type': event_type,
                'event_data': event_data,
                'timestamp': datetime.now(),
                'source': 'data-orchestrator'
            }
            
            self.audit_logs.append(audit_entry)
            
            # Store in database
            await self._store_audit_log(audit_entry)
            
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")

    async def _store_audit_log(self, audit_entry: Dict[str, Any]):
        """Store audit log entry in database"""
        async with self.db_session_factory() as session:
            try:
                audit_log = AuditLog(
                    id=audit_entry['audit_id'],
                    event_type=audit_entry['event_type'],
                    event_data=json.dumps(audit_entry['event_data']),
                    event_timestamp=audit_entry['timestamp'],
                    source_service='data-orchestrator',
                    created_at=datetime.now()
                )
                
                session.add(audit_log)
                await session.commit()
                
            except Exception as e:
                logger.error(f"Failed to store audit log: {e}")
                await session.rollback()

    async def _flush_audit_logs(self):
        """Flush audit logs to persistent storage"""
        try:
            if self.audit_logs:
                logger.info(f"Flushing {len(self.audit_logs)} audit log entries")
                
                # In production, this might batch write to a data lake
                # or audit system like Splunk, ELK, etc.
                
                # Clear the in-memory buffer (logs are already in DB)
                self.audit_logs.clear()
                
        except Exception as e:
            logger.error(f"Error flushing audit logs: {e}")

    async def run_governance_audit(self):
        """Run comprehensive governance audit"""
        logger.info("Running comprehensive governance audit")
        
        try:
            audit_results = {
                'audit_timestamp': datetime.now(),
                'policies_checked': 0,
                'violations_found': 0,
                'compliance_score': 0,
                'recommendations': []
            }
            
            # Check all active policies
            total_policies = 0
            total_violations = 0
            
            for policy in self.active_policies.values():
                if policy.is_active:
                    total_policies += 1
                    violations = await self._execute_policy_compliance_check(policy)
                    total_violations += len(violations)
            
            audit_results['policies_checked'] = total_policies
            audit_results['violations_found'] = total_violations
            
            # Calculate compliance score
            if total_policies > 0:
                compliance_rate = max(0, (total_policies - total_violations) / total_policies)
                audit_results['compliance_score'] = compliance_rate
            else:
                audit_results['compliance_score'] = 1.0
            
            # Generate recommendations
            if total_violations > 0:
                audit_results['recommendations'].append("Review and remediate compliance violations")
            
            if audit_results['compliance_score'] < 0.95:
                audit_results['recommendations'].append("Strengthen governance controls")
            
            # Log audit completion
            await self._log_audit_event("governance_audit_completed", audit_results)
            
            logger.info(f"Governance audit completed: {audit_results}")
            return audit_results
            
        except Exception as e:
            logger.error(f"Error running governance audit: {e}")
            return {}

    async def get_governance_dashboard_data(self) -> Dict[str, Any]:
        """Get data for governance dashboard"""
        try:
            recent_violations = [v for v in self.compliance_violations if v.detected_at > datetime.now() - timedelta(days=7)]
            
            dashboard_data = {
                'active_policies': len([p for p in self.active_policies.values() if p.is_active]),
                'compliance_frameworks': list(set([
                    f.value for p in self.active_policies.values() 
                    for f in p.compliance_frameworks
                ])),
                'data_classifications': {
                    level.value: len([c for c in self.data_classifications.values() if c == level])
                    for level in DataClassificationLevel
                },
                'recent_violations': len(recent_violations),
                'critical_violations': len([v for v in recent_violations if v.severity == 'critical']),
                'lineage_mappings': len(self.lineage_graph),
                'audit_events_last_24h': len([a for a in self.audit_logs if a['timestamp'] > datetime.now() - timedelta(hours=24)]),
                'policy_types': {
                    ptype.value: len([p for p in self.active_policies.values() if p.policy_type == ptype])
                    for ptype in PolicyType
                }
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting governance dashboard data: {e}")
            return {}

    async def get_data_lineage_for_field(self, service: str, entity: str, field: str) -> Dict[str, Any]:
        """Get complete data lineage for a specific field"""
        try:
            lineage_key = f"{service}.{entity}.{field}"
            direct_lineage = self.lineage_graph.get(lineage_key, [])
            
            # Build full lineage graph
            upstream_lineage = []
            downstream_lineage = direct_lineage
            
            # Find upstream dependencies
            for all_lineage in self.lineage_graph.values():
                for record in all_lineage:
                    if (record.target_service == service and 
                        record.target_entity == entity and 
                        record.target_field == field):
                        upstream_lineage.append(record)
            
            lineage_data = {
                'field': f"{service}.{entity}.{field}",
                'classification': self.data_classifications.get(lineage_key, DataClassificationLevel.INTERNAL).value,
                'upstream_dependencies': [asdict(record) for record in upstream_lineage],
                'downstream_dependencies': [asdict(record) for record in downstream_lineage],
                'governance_policies': [
                    policy.policy_name for policy in self.active_policies.values()
                    if service in policy.scope.get('services', []) and
                       entity in policy.scope.get('entities', [])
                ]
            }
            
            return lineage_data
            
        except Exception as e:
            logger.error(f"Error getting data lineage: {e}")
            return {}

    async def cleanup(self):
        """Cleanup governance manager resources"""
        logger.info("Cleaning up Data Governance Manager")
        
        # Cancel background tasks
        for task in self._governance_tasks:
            task.cancel()
        
        if self._governance_tasks:
            await asyncio.gather(*self._governance_tasks, return_exceptions=True)
        
        # Clear caches
        self.audit_logs.clear()
        self.compliance_violations.clear()
        
        logger.info("Data Governance Manager cleanup complete")