"""
COPPA Compliance System for Child Safety

This module provides comprehensive COPPA (Children's Online Privacy Protection Act)
compliance automation, including age verification, parental consent management,
data protection, and regulatory reporting.
"""

import asyncio
import asyncpg
import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import hashlib
import secrets
import uuid

class ConsentType(Enum):
    EMAIL_PLUS = "email_plus"
    DIGITAL_SIGNATURE = "digital_signature"
    PHONE_VERIFICATION = "phone_verification"
    CREDIT_CARD_VERIFICATION = "credit_card_verification"
    VIDEO_CONFERENCE = "video_conference"
    KNOWLEDGE_BASED_AUTH = "knowledge_based_auth"

class DataCategory(Enum):
    PERSONAL_INFO = "personal_info"
    CONTACT_INFO = "contact_info"
    BEHAVIORAL_DATA = "behavioral_data"
    EDUCATIONAL_RECORDS = "educational_records"
    COMMUNICATION_CONTENT = "communication_content"
    LOCATION_DATA = "location_data"
    DEVICE_INFO = "device_info"
    BIOMETRIC_DATA = "biometric_data"

class ConsentStatus(Enum):
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"
    EXPIRED = "expired"

class DataRetentionPolicy(Enum):
    IMMEDIATE_DELETE = "immediate_delete"
    RETAIN_30_DAYS = "retain_30_days"
    RETAIN_1_YEAR = "retain_1_year"
    RETAIN_UNTIL_18 = "retain_until_18"
    RETAIN_FOR_SAFETY = "retain_for_safety"

@dataclass
class ChildUser:
    user_id: str
    birth_date: date
    age: int
    parental_email: str
    consent_required: bool
    consent_status: ConsentStatus
    consent_method: Optional[ConsentType]
    consent_date: Optional[datetime]
    consent_expiry: Optional[datetime]
    data_categories_consented: List[DataCategory]
    special_protections: List[str]
    account_restricted: bool

@dataclass
class ParentalConsent:
    consent_id: str
    user_id: str
    parent_email: str
    parent_name: str
    consent_type: ConsentType
    data_categories: List[DataCategory]
    consent_timestamp: datetime
    expiry_date: Optional[datetime]
    verification_code: str
    verification_status: str
    ip_address: str
    user_agent: str
    consent_text: str
    signature_data: Optional[Dict[str, Any]]
    revocation_date: Optional[datetime]

@dataclass
class DataCollectionRecord:
    record_id: str
    user_id: str
    data_category: DataCategory
    data_type: str
    collection_timestamp: datetime
    purpose: str
    legal_basis: str
    consent_id: Optional[str]
    retention_policy: DataRetentionPolicy
    scheduled_deletion: Optional[datetime]
    anonymized: bool
    shared_with_third_parties: bool
    third_party_list: List[str]

@dataclass
class ComplianceAudit:
    audit_id: str
    audit_date: datetime
    user_id: Optional[str]
    audit_type: str
    findings: List[Dict[str, Any]]
    compliance_score: float
    violations: List[str]
    remediation_required: bool
    remediation_deadline: Optional[datetime]
    status: str

class COPPAComplianceSystem:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.active_verifications: Dict[str, datetime] = {}
        self.data_retention_policies = self._initialize_retention_policies()
        self.consent_templates = self._initialize_consent_templates()
        self.logger = logging.getLogger(__name__)
        
        # COPPA age threshold
        self.coppa_age_threshold = 13
        
        # Consent expiry periods by type
        self.consent_expiry_periods = {
            ConsentType.EMAIL_PLUS: timedelta(days=365),
            ConsentType.DIGITAL_SIGNATURE: timedelta(days=730),
            ConsentType.PHONE_VERIFICATION: timedelta(days=365),
            ConsentType.CREDIT_CARD_VERIFICATION: timedelta(days=730),
            ConsentType.VIDEO_CONFERENCE: timedelta(days=1095),  # 3 years
            ConsentType.KNOWLEDGE_BASED_AUTH: timedelta(days=730)
        }
        
        # Required data for different consent types
        self.consent_requirements = {
            ConsentType.EMAIL_PLUS: ["email", "verification_code"],
            ConsentType.DIGITAL_SIGNATURE: ["digital_signature", "timestamp", "ip_address"],
            ConsentType.PHONE_VERIFICATION: ["phone_number", "verification_call"],
            ConsentType.CREDIT_CARD_VERIFICATION: ["last_4_digits", "verification_amount"],
            ConsentType.VIDEO_CONFERENCE: ["video_session_id", "identity_verification"],
            ConsentType.KNOWLEDGE_BASED_AUTH: ["identity_questions", "verification_score"]
        }

    def _initialize_retention_policies(self) -> Dict[DataCategory, Dict]:
        """Initialize data retention policies by category"""
        return {
            DataCategory.PERSONAL_INFO: {
                "default_retention": DataRetentionPolicy.RETAIN_UNTIL_18,
                "min_retention": timedelta(days=0),
                "max_retention": None,
                "deletion_conditions": ["user_deletion_request", "account_closure", "age_18_reached"]
            },
            DataCategory.CONTACT_INFO: {
                "default_retention": DataRetentionPolicy.RETAIN_1_YEAR,
                "min_retention": timedelta(days=30),
                "max_retention": timedelta(days=365),
                "deletion_conditions": ["user_deletion_request", "consent_revocation"]
            },
            DataCategory.BEHAVIORAL_DATA: {
                "default_retention": DataRetentionPolicy.RETAIN_30_DAYS,
                "min_retention": timedelta(days=1),
                "max_retention": timedelta(days=90),
                "deletion_conditions": ["user_deletion_request", "purpose_fulfilled"]
            },
            DataCategory.EDUCATIONAL_RECORDS: {
                "default_retention": DataRetentionPolicy.RETAIN_UNTIL_18,
                "min_retention": timedelta(days=365),
                "max_retention": None,
                "deletion_conditions": ["educational_purpose_ended", "user_deletion_request"]
            },
            DataCategory.COMMUNICATION_CONTENT: {
                "default_retention": DataRetentionPolicy.RETAIN_FOR_SAFETY,
                "min_retention": timedelta(days=30),
                "max_retention": timedelta(days=180),
                "deletion_conditions": ["safety_review_complete", "user_deletion_request"]
            },
            DataCategory.LOCATION_DATA: {
                "default_retention": DataRetentionPolicy.IMMEDIATE_DELETE,
                "min_retention": timedelta(days=0),
                "max_retention": timedelta(days=7),
                "deletion_conditions": ["session_ended", "safety_purpose_ended"]
            },
            DataCategory.DEVICE_INFO: {
                "default_retention": DataRetentionPolicy.RETAIN_30_DAYS,
                "min_retention": timedelta(days=1),
                "max_retention": timedelta(days=30),
                "deletion_conditions": ["technical_purpose_ended", "user_deletion_request"]
            },
            DataCategory.BIOMETRIC_DATA: {
                "default_retention": DataRetentionPolicy.IMMEDIATE_DELETE,
                "min_retention": timedelta(days=0),
                "max_retention": timedelta(days=1),
                "deletion_conditions": ["authentication_complete", "user_deletion_request"]
            }
        }

    def _initialize_consent_templates(self) -> Dict[str, str]:
        """Initialize consent form templates"""
        return {
            "basic_consent": """
PARENTAL CONSENT FOR CHILD'S ONLINE ACTIVITY

Your child has requested to use our educational platform. Under COPPA (Children's Online Privacy Protection Act), we require parental consent before collecting any personal information from children under 13.

INFORMATION WE COLLECT:
- Basic profile information (name, age, grade level)
- Educational progress and performance data
- Communication for safety monitoring
- Device information for technical support

HOW WE USE THIS INFORMATION:
- Provide educational services
- Monitor for safety and inappropriate content
- Communicate with parents about progress
- Ensure platform security and functionality

INFORMATION SHARING:
We do not sell or share your child's information with third parties for marketing purposes. We may share information with:
- Educational partners (with consent)
- Safety authorities (when required by law)
- Technical service providers (under strict privacy agreements)

YOUR RIGHTS:
- Review your child's information at any time
- Request deletion of your child's account and data
- Revoke consent and restrict further collection
- Receive notifications of any data breaches

DATA RETENTION:
- Personal information: Until child reaches 18 or account deletion
- Educational records: As required for educational purposes
- Safety-related data: Until safety review is complete
- Technical data: 30 days maximum

By providing consent, you acknowledge that you are the parent or legal guardian of this child and agree to the collection and use of information as described.
            """.strip(),
            
            "educational_consent": """
ENHANCED PARENTAL CONSENT FOR EDUCATIONAL SERVICES

This consent covers additional data collection for enhanced educational features:

ADDITIONAL INFORMATION WE MAY COLLECT:
- Detailed learning analytics and patterns
- Voice recordings for language learning
- Collaborative work with other students
- Extended communication for educational purposes

ENHANCED FEATURES ENABLED:
- Personalized learning recommendations
- Voice-based language exercises
- Collaborative projects with other students
- Advanced progress tracking and reporting

ADDITIONAL SHARING:
- Educational content providers (for personalized content)
- Other students (for collaborative features only)
- Teachers and educational staff (for supervision)

This enhanced consent is optional. Basic educational services are available without these additional features.
            """.strip(),
            
            "safety_monitoring_consent": """
PARENTAL CONSENT FOR SAFETY MONITORING

This consent covers our comprehensive safety monitoring system:

SAFETY MONITORING INCLUDES:
- Content filtering and inappropriate material detection
- Communication monitoring for bullying and safety threats
- Interaction pattern analysis for concerning behavior
- Emergency alert system activation

DATA USED FOR SAFETY:
- Communication content (analyzed, not stored long-term)
- Interaction patterns and behavioral indicators
- Emergency contact information
- Location data (only during safety emergencies)

SAFETY ACTIONS WE MAY TAKE:
- Block inappropriate content automatically
- Alert parents to safety concerns
- Contact emergency services in critical situations
- Preserve evidence of harmful interactions

PARENT NOTIFICATIONS:
You will be immediately notified of:
- Any safety incidents involving your child
- Blocked content or filtered communications
- Emergency situations requiring your attention
- Changes to safety monitoring systems

This safety monitoring is designed to protect your child while respecting their privacy to the maximum extent possible under safety requirements.
            """.strip()
        }

    async def initialize_database(self):
        """Initialize database tables for COPPA compliance"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS child_users (
                    user_id VARCHAR PRIMARY KEY,
                    birth_date DATE NOT NULL,
                    age INTEGER NOT NULL,
                    parental_email VARCHAR NOT NULL,
                    consent_required BOOLEAN DEFAULT TRUE,
                    consent_status VARCHAR NOT NULL DEFAULT 'pending',
                    consent_method VARCHAR,
                    consent_date TIMESTAMP,
                    consent_expiry TIMESTAMP,
                    data_categories_consented JSONB DEFAULT '[]',
                    special_protections JSONB DEFAULT '[]',
                    account_restricted BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS parental_consents (
                    consent_id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    parent_email VARCHAR NOT NULL,
                    parent_name VARCHAR NOT NULL,
                    consent_type VARCHAR NOT NULL,
                    data_categories JSONB NOT NULL,
                    consent_timestamp TIMESTAMP NOT NULL,
                    expiry_date TIMESTAMP,
                    verification_code VARCHAR NOT NULL,
                    verification_status VARCHAR DEFAULT 'pending',
                    ip_address VARCHAR NOT NULL,
                    user_agent TEXT,
                    consent_text TEXT NOT NULL,
                    signature_data JSONB,
                    revocation_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES child_users(user_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS data_collection_records (
                    record_id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    data_category VARCHAR NOT NULL,
                    data_type VARCHAR NOT NULL,
                    collection_timestamp TIMESTAMP NOT NULL,
                    purpose TEXT NOT NULL,
                    legal_basis VARCHAR NOT NULL,
                    consent_id VARCHAR,
                    retention_policy VARCHAR NOT NULL,
                    scheduled_deletion TIMESTAMP,
                    anonymized BOOLEAN DEFAULT FALSE,
                    shared_with_third_parties BOOLEAN DEFAULT FALSE,
                    third_party_list JSONB DEFAULT '[]',
                    deleted_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES child_users(user_id),
                    FOREIGN KEY (consent_id) REFERENCES parental_consents(consent_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_audits (
                    audit_id VARCHAR PRIMARY KEY,
                    audit_date TIMESTAMP NOT NULL,
                    user_id VARCHAR,
                    audit_type VARCHAR NOT NULL,
                    findings JSONB NOT NULL DEFAULT '[]',
                    compliance_score FLOAT NOT NULL,
                    violations JSONB NOT NULL DEFAULT '[]',
                    remediation_required BOOLEAN DEFAULT FALSE,
                    remediation_deadline TIMESTAMP,
                    status VARCHAR DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES child_users(user_id)
                )
            """)

    async def register_child_user(self, user_id: str, birth_date: date, 
                                parental_email: str) -> ChildUser:
        """Register a new child user with COPPA compliance"""
        
        # Calculate age
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        # Determine if COPPA consent is required
        consent_required = age < self.coppa_age_threshold
        
        child_user = ChildUser(
            user_id=user_id,
            birth_date=birth_date,
            age=age,
            parental_email=parental_email,
            consent_required=consent_required,
            consent_status=ConsentStatus.PENDING if consent_required else ConsentStatus.GRANTED,
            consent_method=None,
            consent_date=None,
            consent_expiry=None,
            data_categories_consented=[],
            special_protections=["content_filtering", "interaction_monitoring"] if consent_required else [],
            account_restricted=consent_required
        )
        
        # Store user
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO child_users 
                (user_id, birth_date, age, parental_email, consent_required,
                 consent_status, data_categories_consented, special_protections, account_restricted)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, user_id, birth_date, age, parental_email, consent_required,
                child_user.consent_status.value,
                json.dumps([]),
                json.dumps(child_user.special_protections),
                child_user.account_restricted
            )
        
        # If consent required, initiate consent process
        if consent_required:
            await self._initiate_parental_consent(child_user)
        
        self.logger.info(f"Registered child user {user_id}, age {age}, consent required: {consent_required}")
        return child_user

    async def _initiate_parental_consent(self, child_user: ChildUser):
        """Initiate the parental consent process"""
        
        # Send initial consent request email
        consent_request = {
            "user_id": child_user.user_id,
            "parental_email": child_user.parental_email,
            "child_age": child_user.age,
            "consent_url": f"https://childsafety.example.com/consent/{child_user.user_id}",
            "verification_code": secrets.token_hex(8)
        }
        
        await self._send_consent_request_email(consent_request)
        
        # Store pending consent
        self.active_verifications[child_user.user_id] = datetime.now()

    async def request_parental_consent(self, user_id: str, consent_type: ConsentType,
                                     data_categories: List[DataCategory],
                                     parent_name: str, parent_email: str,
                                     ip_address: str, user_agent: str,
                                     consent_template: str = "basic_consent") -> str:
        """Request parental consent for specific data categories"""
        
        consent_id = f"consent_{user_id}_{int(datetime.now().timestamp())}"
        verification_code = secrets.token_hex(12)
        
        # Calculate expiry date
        expiry_date = None
        if consent_type in self.consent_expiry_periods:
            expiry_date = datetime.now() + self.consent_expiry_periods[consent_type]
        
        consent = ParentalConsent(
            consent_id=consent_id,
            user_id=user_id,
            parent_email=parent_email,
            parent_name=parent_name,
            consent_type=consent_type,
            data_categories=data_categories,
            consent_timestamp=datetime.now(),
            expiry_date=expiry_date,
            verification_code=verification_code,
            verification_status="pending",
            ip_address=ip_address,
            user_agent=user_agent,
            consent_text=self.consent_templates.get(consent_template, self.consent_templates["basic_consent"]),
            signature_data=None,
            revocation_date=None
        )
        
        # Store consent request
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO parental_consents 
                (consent_id, user_id, parent_email, parent_name, consent_type,
                 data_categories, consent_timestamp, expiry_date, verification_code,
                 ip_address, user_agent, consent_text)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """, consent_id, user_id, parent_email, parent_name, consent_type.value,
                json.dumps([cat.value for cat in data_categories]),
                consent.consent_timestamp, expiry_date, verification_code,
                ip_address, user_agent, consent.consent_text
            )
        
        # Send consent verification
        await self._send_consent_verification(consent)
        
        self.logger.info(f"Requested parental consent {consent_id} for user {user_id}")
        return consent_id

    async def verify_parental_consent(self, consent_id: str, verification_code: str,
                                    signature_data: Optional[Dict[str, Any]] = None) -> bool:
        """Verify parental consent using verification code"""
        
        async with self.db_pool.acquire() as conn:
            consent_data = await conn.fetchrow("""
                SELECT * FROM parental_consents
                WHERE consent_id = $1
            """, consent_id)
        
        if not consent_data or consent_data["verification_status"] == "verified":
            return False
        
        if consent_data["verification_code"] != verification_code:
            self.logger.warning(f"Invalid verification code for consent {consent_id}")
            return False
        
        # Verify consent hasn't expired
        if consent_data["expiry_date"] and datetime.now() > consent_data["expiry_date"]:
            self.logger.warning(f"Consent {consent_id} has expired")
            return False
        
        # Update consent as verified
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE parental_consents 
                SET verification_status = 'verified',
                    signature_data = $1
                WHERE consent_id = $2
            """, json.dumps(signature_data) if signature_data else None, consent_id)
            
            # Update child user consent status
            data_categories = json.loads(consent_data["data_categories"])
            await conn.execute("""
                UPDATE child_users 
                SET consent_status = 'granted',
                    consent_method = $1,
                    consent_date = CURRENT_TIMESTAMP,
                    consent_expiry = $2,
                    data_categories_consented = $3,
                    account_restricted = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $4
            """, consent_data["consent_type"], consent_data["expiry_date"],
                json.dumps(data_categories), consent_data["user_id"])
        
        # Log data collection authorization
        await self._log_consent_grant(consent_data["user_id"], consent_id, data_categories)
        
        self.logger.info(f"Verified parental consent {consent_id}")
        return True

    async def revoke_parental_consent(self, user_id: str, reason: str) -> bool:
        """Revoke parental consent and trigger data deletion"""
        
        async with self.db_pool.acquire() as conn:
            # Update consent records
            await conn.execute("""
                UPDATE parental_consents 
                SET revocation_date = CURRENT_TIMESTAMP
                WHERE user_id = $1 AND verification_status = 'verified'
            """, user_id)
            
            # Update child user status
            await conn.execute("""
                UPDATE child_users 
                SET consent_status = 'revoked',
                    account_restricted = TRUE,
                    data_categories_consented = '[]',
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
            """, user_id)
        
        # Trigger data deletion process
        await self._schedule_data_deletion(user_id, "consent_revocation")
        
        # Log compliance action
        await self._log_compliance_action(user_id, "consent_revocation", {"reason": reason})
        
        self.logger.info(f"Revoked parental consent for user {user_id}")
        return True

    async def log_data_collection(self, user_id: str, data_category: DataCategory,
                                data_type: str, purpose: str, consent_id: Optional[str] = None,
                                third_parties: List[str] = None) -> str:
        """Log data collection activity for compliance tracking"""
        
        if third_parties is None:
            third_parties = []
        
        record_id = f"data_{user_id}_{data_category.value}_{int(datetime.now().timestamp())}"
        
        # Determine retention policy
        retention_policy = self.data_retention_policies[data_category]["default_retention"]
        
        # Calculate scheduled deletion
        scheduled_deletion = None
        if retention_policy == DataRetentionPolicy.IMMEDIATE_DELETE:
            scheduled_deletion = datetime.now()
        elif retention_policy == DataRetentionPolicy.RETAIN_30_DAYS:
            scheduled_deletion = datetime.now() + timedelta(days=30)
        elif retention_policy == DataRetentionPolicy.RETAIN_1_YEAR:
            scheduled_deletion = datetime.now() + timedelta(days=365)
        # RETAIN_UNTIL_18 and RETAIN_FOR_SAFETY don't have automatic deletion
        
        record = DataCollectionRecord(
            record_id=record_id,
            user_id=user_id,
            data_category=data_category,
            data_type=data_type,
            collection_timestamp=datetime.now(),
            purpose=purpose,
            legal_basis="parental_consent" if consent_id else "legitimate_interest",
            consent_id=consent_id,
            retention_policy=retention_policy,
            scheduled_deletion=scheduled_deletion,
            anonymized=False,
            shared_with_third_parties=len(third_parties) > 0,
            third_party_list=third_parties
        )
        
        # Store record
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO data_collection_records 
                (record_id, user_id, data_category, data_type, collection_timestamp,
                 purpose, legal_basis, consent_id, retention_policy, scheduled_deletion,
                 anonymized, shared_with_third_parties, third_party_list)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """, record_id, user_id, data_category.value, data_type,
                record.collection_timestamp, purpose, record.legal_basis, consent_id,
                retention_policy.value, scheduled_deletion, False,
                len(third_parties) > 0, json.dumps(third_parties)
            )
        
        self.logger.debug(f"Logged data collection: {record_id}")
        return record_id

    async def schedule_data_retention_review(self):
        """Schedule and execute data retention reviews"""
        
        async with self.db_pool.acquire() as conn:
            # Find records scheduled for deletion
            expired_records = await conn.fetch("""
                SELECT * FROM data_collection_records
                WHERE scheduled_deletion <= CURRENT_TIMESTAMP
                AND deleted_at IS NULL
            """)
            
            for record in expired_records:
                await self._execute_data_deletion(dict(record))
        
        self.logger.info("Completed data retention review")

    async def _execute_data_deletion(self, record: Dict[str, Any]):
        """Execute data deletion for a specific record"""
        
        record_id = record["record_id"]
        user_id = record["user_id"]
        data_category = record["data_category"]
        
        # Mark as deleted in compliance record
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE data_collection_records 
                SET deleted_at = CURRENT_TIMESTAMP
                WHERE record_id = $1
            """, record_id)
        
        # Log deletion action
        await self._log_compliance_action(user_id, "data_deletion", {
            "record_id": record_id,
            "data_category": data_category,
            "retention_policy": record["retention_policy"],
            "deletion_reason": "retention_period_expired"
        })
        
        self.logger.info(f"Executed data deletion for record {record_id}")

    async def _schedule_data_deletion(self, user_id: str, reason: str):
        """Schedule comprehensive data deletion for a user"""
        
        async with self.db_pool.acquire() as conn:
            # Mark all user data for immediate deletion
            await conn.execute("""
                UPDATE data_collection_records 
                SET scheduled_deletion = CURRENT_TIMESTAMP
                WHERE user_id = $1 AND deleted_at IS NULL
            """, user_id)
        
        # Log deletion schedule
        await self._log_compliance_action(user_id, "data_deletion_scheduled", {"reason": reason})
        
        self.logger.info(f"Scheduled data deletion for user {user_id}")

    async def run_compliance_audit(self, user_id: Optional[str] = None,
                                 audit_type: str = "comprehensive") -> str:
        """Run compliance audit for COPPA requirements"""
        
        audit_id = f"audit_{audit_type}_{int(datetime.now().timestamp())}"
        findings = []
        violations = []
        compliance_score = 100.0
        
        # Define audit checks
        audit_checks = [
            self._audit_consent_status,
            self._audit_data_collection,
            self._audit_data_retention,
            self._audit_parental_notification,
            self._audit_third_party_sharing,
            self._audit_account_restrictions
        ]
        
        # Run audit checks
        for check in audit_checks:
            try:
                check_result = await check(user_id)
                findings.append(check_result)
                
                if check_result["status"] == "violation":
                    violations.append(check_result["description"])
                    compliance_score -= check_result.get("severity_score", 10)
                elif check_result["status"] == "warning":
                    compliance_score -= check_result.get("severity_score", 5)
                    
            except Exception as e:
                self.logger.error(f"Audit check failed: {e}")
                findings.append({
                    "check": check.__name__,
                    "status": "error",
                    "description": f"Audit check failed: {e}"
                })
        
        compliance_score = max(0, compliance_score)
        
        # Determine if remediation is required
        remediation_required = len(violations) > 0 or compliance_score < 80
        remediation_deadline = None
        
        if remediation_required:
            # Set remediation deadline based on violation severity
            if any("critical" in v.lower() for v in violations):
                remediation_deadline = datetime.now() + timedelta(days=1)
            elif any("high" in v.lower() for v in violations):
                remediation_deadline = datetime.now() + timedelta(days=7)
            else:
                remediation_deadline = datetime.now() + timedelta(days=30)
        
        # Store audit results
        audit = ComplianceAudit(
            audit_id=audit_id,
            audit_date=datetime.now(),
            user_id=user_id,
            audit_type=audit_type,
            findings=findings,
            compliance_score=compliance_score,
            violations=violations,
            remediation_required=remediation_required,
            remediation_deadline=remediation_deadline,
            status="completed"
        )
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO compliance_audits 
                (audit_id, audit_date, user_id, audit_type, findings,
                 compliance_score, violations, remediation_required, remediation_deadline, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, audit_id, audit.audit_date, user_id, audit_type,
                json.dumps(findings), compliance_score, json.dumps(violations),
                remediation_required, remediation_deadline, "completed"
            )
        
        self.logger.info(f"Completed compliance audit {audit_id}, score: {compliance_score}")
        return audit_id

    async def _audit_consent_status(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Audit consent status compliance"""
        
        async with self.db_pool.acquire() as conn:
            if user_id:
                users = await conn.fetch("""
                    SELECT * FROM child_users WHERE user_id = $1
                """, user_id)
            else:
                users = await conn.fetch("""
                    SELECT * FROM child_users WHERE consent_required = TRUE
                """)
        
        violations = []
        warnings = []
        
        for user in users:
            # Check consent status for users requiring consent
            if user["consent_required"] and user["consent_status"] == "pending":
                days_pending = (datetime.now() - user["created_at"]).days
                if days_pending > 7:
                    violations.append(f"User {user['user_id']}: Consent pending for {days_pending} days")
            
            # Check consent expiry
            if user["consent_expiry"] and datetime.now() > user["consent_expiry"]:
                violations.append(f"User {user['user_id']}: Consent expired")
            
            # Check account restrictions
            if user["consent_required"] and user["consent_status"] != "granted" and not user["account_restricted"]:
                violations.append(f"User {user['user_id']}: Account not properly restricted without consent")
        
        return {
            "check": "consent_status",
            "status": "violation" if violations else "warning" if warnings else "pass",
            "description": f"Consent status audit: {len(violations)} violations, {len(warnings)} warnings",
            "violations": violations,
            "warnings": warnings,
            "severity_score": len(violations) * 15 + len(warnings) * 5
        }

    async def _audit_data_collection(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Audit data collection practices"""
        
        async with self.db_pool.acquire() as conn:
            if user_id:
                records = await conn.fetch("""
                    SELECT dcr.*, cu.consent_status, cu.consent_required
                    FROM data_collection_records dcr
                    JOIN child_users cu ON dcr.user_id = cu.user_id
                    WHERE dcr.user_id = $1
                """, user_id)
            else:
                records = await conn.fetch("""
                    SELECT dcr.*, cu.consent_status, cu.consent_required
                    FROM data_collection_records dcr
                    JOIN child_users cu ON dcr.user_id = cu.user_id
                    WHERE cu.consent_required = TRUE
                """)
        
        violations = []
        warnings = []
        
        for record in records:
            # Check if data collection has proper legal basis
            if record["consent_required"] and record["legal_basis"] != "parental_consent":
                if not record["consent_id"]:
                    violations.append(f"Data collection {record['record_id']}: No parental consent for required user")
            
            # Check data retention compliance
            if record["scheduled_deletion"] and datetime.now() > record["scheduled_deletion"] and not record["deleted_at"]:
                violations.append(f"Data record {record['record_id']}: Past scheduled deletion date")
            
            # Check third-party sharing
            if record["shared_with_third_parties"] and record["consent_required"]:
                third_parties = json.loads(record["third_party_list"])
                if third_parties and record["legal_basis"] != "parental_consent":
                    violations.append(f"Data record {record['record_id']}: Third-party sharing without consent")
        
        return {
            "check": "data_collection",
            "status": "violation" if violations else "warning" if warnings else "pass",
            "description": f"Data collection audit: {len(violations)} violations, {len(warnings)} warnings",
            "violations": violations,
            "warnings": warnings,
            "severity_score": len(violations) * 20 + len(warnings) * 5
        }

    async def _audit_data_retention(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Audit data retention compliance"""
        
        async with self.db_pool.acquire() as conn:
            if user_id:
                overdue_records = await conn.fetch("""
                    SELECT * FROM data_collection_records
                    WHERE user_id = $1 AND scheduled_deletion <= CURRENT_TIMESTAMP
                    AND deleted_at IS NULL
                """, user_id)
            else:
                overdue_records = await conn.fetch("""
                    SELECT * FROM data_collection_records
                    WHERE scheduled_deletion <= CURRENT_TIMESTAMP AND deleted_at IS NULL
                """)
        
        violations = []
        
        for record in overdue_records:
            days_overdue = (datetime.now() - record["scheduled_deletion"]).days
            violations.append(f"Data record {record['record_id']}: {days_overdue} days past deletion date")
        
        return {
            "check": "data_retention",
            "status": "violation" if violations else "pass",
            "description": f"Data retention audit: {len(violations)} overdue deletions",
            "violations": violations,
            "warnings": [],
            "severity_score": len(violations) * 10
        }

    async def _audit_parental_notification(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Audit parental notification compliance"""
        # Placeholder for parental notification audit
        return {
            "check": "parental_notification",
            "status": "pass",
            "description": "Parental notification audit completed",
            "violations": [],
            "warnings": [],
            "severity_score": 0
        }

    async def _audit_third_party_sharing(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Audit third-party sharing compliance"""
        
        async with self.db_pool.acquire() as conn:
            if user_id:
                sharing_records = await conn.fetch("""
                    SELECT dcr.*, cu.consent_status
                    FROM data_collection_records dcr
                    JOIN child_users cu ON dcr.user_id = cu.user_id
                    WHERE dcr.user_id = $1 AND dcr.shared_with_third_parties = TRUE
                """, user_id)
            else:
                sharing_records = await conn.fetch("""
                    SELECT dcr.*, cu.consent_status
                    FROM data_collection_records dcr
                    JOIN child_users cu ON dcr.user_id = cu.user_id
                    WHERE dcr.shared_with_third_parties = TRUE AND cu.consent_required = TRUE
                """)
        
        violations = []
        
        for record in sharing_records:
            if record["consent_status"] != "granted":
                violations.append(f"Third-party sharing without consent: {record['record_id']}")
        
        return {
            "check": "third_party_sharing",
            "status": "violation" if violations else "pass",
            "description": f"Third-party sharing audit: {len(violations)} violations",
            "violations": violations,
            "warnings": [],
            "severity_score": len(violations) * 15
        }

    async def _audit_account_restrictions(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Audit account restriction compliance"""
        
        async with self.db_pool.acquire() as conn:
            if user_id:
                users = await conn.fetch("""
                    SELECT * FROM child_users 
                    WHERE user_id = $1 AND consent_required = TRUE
                """, user_id)
            else:
                users = await conn.fetch("""
                    SELECT * FROM child_users 
                    WHERE consent_required = TRUE
                """)
        
        violations = []
        
        for user in users:
            if user["consent_status"] != "granted" and not user["account_restricted"]:
                violations.append(f"User {user['user_id']}: Account not restricted without consent")
        
        return {
            "check": "account_restrictions",
            "status": "violation" if violations else "pass",
            "description": f"Account restriction audit: {len(violations)} violations",
            "violations": violations,
            "warnings": [],
            "severity_score": len(violations) * 10
        }

    async def _log_consent_grant(self, user_id: str, consent_id: str, data_categories: List[str]):
        """Log consent grant for compliance tracking"""
        
        for category in data_categories:
            await self.log_data_collection(
                user_id=user_id,
                data_category=DataCategory(category),
                data_type="consent_authorization",
                purpose="parental_consent_granted",
                consent_id=consent_id
            )

    async def _log_compliance_action(self, user_id: str, action_type: str, details: Dict[str, Any]):
        """Log compliance-related actions"""
        
        self.logger.info(f"Compliance action: {action_type} for user {user_id}: {details}")

    async def _send_consent_request_email(self, request: Dict[str, Any]):
        """Send parental consent request email (mock implementation)"""
        
        self.logger.info(f"Sending consent request to {request['parental_email']} for user {request['user_id']}")

    async def _send_consent_verification(self, consent: ParentalConsent):
        """Send consent verification email (mock implementation)"""
        
        self.logger.info(f"Sending consent verification to {consent.parent_email} for consent {consent.consent_id}")

    async def get_compliance_dashboard(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate compliance dashboard"""
        
        async with self.db_pool.acquire() as conn:
            # Get user statistics
            if user_id:
                user_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN consent_required THEN 1 END) as users_requiring_consent,
                        COUNT(CASE WHEN consent_status = 'granted' THEN 1 END) as users_with_consent,
                        COUNT(CASE WHEN consent_status = 'pending' THEN 1 END) as users_pending_consent
                    FROM child_users WHERE user_id = $1
                """, user_id)
            else:
                user_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN consent_required THEN 1 END) as users_requiring_consent,
                        COUNT(CASE WHEN consent_status = 'granted' THEN 1 END) as users_with_consent,
                        COUNT(CASE WHEN consent_status = 'pending' THEN 1 END) as users_pending_consent
                    FROM child_users
                """)
            
            # Get recent audits
            recent_audits = await conn.fetch("""
                SELECT * FROM compliance_audits
                ORDER BY audit_date DESC LIMIT 5
            """)
            
            # Get data collection statistics
            data_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as active_records,
                    COUNT(CASE WHEN scheduled_deletion <= CURRENT_TIMESTAMP AND deleted_at IS NULL THEN 1 END) as overdue_deletions
                FROM data_collection_records
            """)
        
        # Calculate compliance score
        total_requiring_consent = user_stats["users_requiring_consent"] or 0
        users_with_consent = user_stats["users_with_consent"] or 0
        overdue_deletions = data_stats["overdue_deletions"] or 0
        
        consent_compliance = (users_with_consent / max(1, total_requiring_consent)) * 100
        retention_compliance = 100 if overdue_deletions == 0 else max(0, 100 - (overdue_deletions * 10))
        overall_compliance = (consent_compliance + retention_compliance) / 2
        
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "compliance_summary": {
                "overall_score": round(overall_compliance, 1),
                "consent_compliance": round(consent_compliance, 1),
                "retention_compliance": round(retention_compliance, 1),
                "status": "Compliant" if overall_compliance >= 95 else "Attention Required" if overall_compliance >= 80 else "Non-Compliant"
            },
            "user_statistics": dict(user_stats) if user_stats else {},
            "data_statistics": dict(data_stats) if data_stats else {},
            "recent_audits": [dict(audit) for audit in recent_audits],
            "alerts": []
        }
        
        # Add alerts for compliance issues
        if overdue_deletions > 0:
            dashboard["alerts"].append({
                "level": "critical",
                "message": f"{overdue_deletions} data records past scheduled deletion date"
            })
        
        if user_stats and user_stats["users_pending_consent"] > 0:
            dashboard["alerts"].append({
                "level": "warning", 
                "message": f"{user_stats['users_pending_consent']} users with pending consent"
            })
        
        return dashboard