"""
Patient Consent Management System
Manages patient consent for healthcare data access and sharing.
"""
import datetime
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib


class ConsentStatus(Enum):
    """Consent status values"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class ConsentType(Enum):
    """Types of consent"""
    TREATMENT = "treatment"
    PAYMENT = "payment"
    OPERATIONS = "operations"
    RESEARCH = "research"
    MARKETING = "marketing"
    SHARING = "sharing"
    EMERGENCY = "emergency"


class ConsentScope(Enum):
    """Scope of consent"""
    GENERAL = "general"
    SPECIFIC_PROVIDER = "specific_provider"
    SPECIFIC_PURPOSE = "specific_purpose"
    SPECIFIC_DATA = "specific_data"
    TIME_LIMITED = "time_limited"


class DataCategory(Enum):
    """Categories of healthcare data"""
    DEMOGRAPHICS = "demographics"
    CLINICAL_NOTES = "clinical_notes"
    LAB_RESULTS = "lab_results"
    IMAGING = "imaging"
    PRESCRIPTIONS = "prescriptions"
    MENTAL_HEALTH = "mental_health"
    SUBSTANCE_ABUSE = "substance_abuse"
    HIV_AIDS = "hiv_aids"
    GENETIC_INFO = "genetic_info"
    REPRODUCTIVE_HEALTH = "reproductive_health"


@dataclass
class ConsentParty:
    """Party involved in consent (patient, provider, organization)"""
    id: str
    type: str  # patient, practitioner, organization
    name: str
    identifier: Optional[str] = None
    contact_info: Optional[Dict] = None


@dataclass
class ConsentProvision:
    """Specific provision within a consent"""
    id: str
    type: str  # permit, deny
    purpose: List[ConsentType]
    data_categories: List[DataCategory]
    actors: List[ConsentParty]
    period_start: Optional[datetime.datetime] = None
    period_end: Optional[datetime.datetime] = None
    conditions: Optional[List[str]] = None


@dataclass
class PatientConsent:
    """Complete patient consent record"""
    id: str
    patient_id: str
    status: ConsentStatus
    scope: ConsentScope
    category: List[ConsentType]
    provisions: List[ConsentProvision]
    date_recorded: datetime.datetime
    effective_date: datetime.datetime
    expiry_date: Optional[datetime.datetime] = None
    grantor: Optional[ConsentParty] = None
    grantee: List[ConsentParty] = None
    source_document: Optional[str] = None
    verification_method: Optional[str] = None
    witness: Optional[ConsentParty] = None
    policy_rule: Optional[str] = None


class ConsentValidator:
    """Validates consent records and access requests"""
    
    def __init__(self):
        self.special_categories = {
            DataCategory.MENTAL_HEALTH,
            DataCategory.SUBSTANCE_ABUSE,
            DataCategory.HIV_AIDS,
            DataCategory.GENETIC_INFO,
            DataCategory.REPRODUCTIVE_HEALTH
        }
    
    def validate_consent(self, consent: PatientConsent) -> List[str]:
        """Validate consent record for completeness and compliance"""
        errors = []
        
        # Basic validation
        if not consent.patient_id:
            errors.append("Patient ID is required")
        
        if not consent.provisions:
            errors.append("At least one provision is required")
        
        if consent.expiry_date and consent.expiry_date <= consent.effective_date:
            errors.append("Expiry date must be after effective date")
        
        # Validate provisions
        for provision in consent.provisions:
            provision_errors = self._validate_provision(provision)
            errors.extend(provision_errors)
        
        # Special category validation
        for provision in consent.provisions:
            for category in provision.data_categories:
                if category in self.special_categories:
                    if not self._has_explicit_consent_for_category(consent, category):
                        errors.append(f"Explicit consent required for {category.value}")
        
        return errors
    
    def _validate_provision(self, provision: ConsentProvision) -> List[str]:
        """Validate individual consent provision"""
        errors = []
        
        if not provision.purpose:
            errors.append("Provision must specify purpose")
        
        if not provision.data_categories:
            errors.append("Provision must specify data categories")
        
        if provision.period_end and provision.period_start:
            if provision.period_end <= provision.period_start:
                errors.append("Provision end date must be after start date")
        
        return errors
    
    def _has_explicit_consent_for_category(self, consent: PatientConsent, 
                                         category: DataCategory) -> bool:
        """Check if consent has explicit approval for special category"""
        for provision in consent.provisions:
            if (provision.type == "permit" and 
                category in provision.data_categories and
                consent.scope != ConsentScope.GENERAL):
                return True
        return False


class ConsentManager:
    """Main consent management system"""
    
    def __init__(self, storage_backend=None):
        self.storage = storage_backend or {}
        self.validator = ConsentValidator()
        self.access_log = []
    
    def create_consent(self, patient_id: str, consent_data: Dict[str, Any]) -> str:
        """Create new patient consent record"""
        consent_id = str(uuid.uuid4())
        
        # Convert provisions
        provisions = []
        for prov_data in consent_data.get('provisions', []):
            provision = ConsentProvision(
                id=str(uuid.uuid4()),
                type=prov_data['type'],
                purpose=[ConsentType(p) for p in prov_data.get('purpose', [])],
                data_categories=[DataCategory(c) for c in prov_data.get('data_categories', [])],
                actors=[ConsentParty(**actor) for actor in prov_data.get('actors', [])],
                period_start=prov_data.get('period_start'),
                period_end=prov_data.get('period_end'),
                conditions=prov_data.get('conditions')
            )
            provisions.append(provision)
        
        # Create consent record
        consent = PatientConsent(
            id=consent_id,
            patient_id=patient_id,
            status=ConsentStatus(consent_data.get('status', 'active')),
            scope=ConsentScope(consent_data.get('scope', 'general')),
            category=[ConsentType(c) for c in consent_data.get('category', [])],
            provisions=provisions,
            date_recorded=datetime.datetime.utcnow(),
            effective_date=consent_data.get('effective_date', datetime.datetime.utcnow()),
            expiry_date=consent_data.get('expiry_date'),
            grantor=ConsentParty(**consent_data['grantor']) if 'grantor' in consent_data else None,
            grantee=[ConsentParty(**g) for g in consent_data.get('grantee', [])],
            source_document=consent_data.get('source_document'),
            verification_method=consent_data.get('verification_method'),
            witness=ConsentParty(**consent_data['witness']) if 'witness' in consent_data else None,
            policy_rule=consent_data.get('policy_rule')
        )
        
        # Validate consent
        errors = self.validator.validate_consent(consent)
        if errors:
            raise ValueError(f"Consent validation failed: {'; '.join(errors)}")
        
        # Store consent
        self.storage[consent_id] = consent
        
        # Log creation
        self._log_consent_action('create', consent_id, patient_id)
        
        return consent_id
    
    def get_consent(self, consent_id: str) -> Optional[PatientConsent]:
        """Retrieve consent record by ID"""
        consent = self.storage.get(consent_id)
        if consent:
            self._log_consent_action('read', consent_id, consent.patient_id)
        return consent
    
    def get_patient_consents(self, patient_id: str, 
                           status_filter: Optional[ConsentStatus] = None) -> List[PatientConsent]:
        """Get all consent records for a patient"""
        consents = []
        
        for consent in self.storage.values():
            if consent.patient_id == patient_id:
                if not status_filter or consent.status == status_filter:
                    consents.append(consent)
        
        # Log access
        if consents:
            self._log_consent_action('read_patient', None, patient_id, 
                                   additional_info={'count': len(consents)})
        
        return consents
    
    def update_consent_status(self, consent_id: str, new_status: ConsentStatus) -> bool:
        """Update consent status"""
        consent = self.storage.get(consent_id)
        if not consent:
            return False
        
        old_status = consent.status
        consent.status = new_status
        
        # Log status change
        self._log_consent_action('update_status', consent_id, consent.patient_id,
                               additional_info={'old_status': old_status.value, 
                                              'new_status': new_status.value})
        
        return True
    
    def withdraw_consent(self, consent_id: str, reason: Optional[str] = None) -> bool:
        """Withdraw patient consent"""
        consent = self.storage.get(consent_id)
        if not consent:
            return False
        
        consent.status = ConsentStatus.WITHDRAWN
        
        # Log withdrawal
        self._log_consent_action('withdraw', consent_id, consent.patient_id,
                               additional_info={'reason': reason})
        
        return True
    
    def check_access_permission(self, patient_id: str, requester_id: str,
                              purpose: ConsentType, data_categories: List[DataCategory]) -> Dict[str, Any]:
        """Check if access is permitted based on patient consent"""
        result = {
            'permitted': False,
            'applicable_consents': [],
            'denied_categories': [],
            'conditions': [],
            'expires_at': None
        }
        
        # Get active consents for patient
        consents = self.get_patient_consents(patient_id, ConsentStatus.ACTIVE)
        
        # Check each consent
        permitted_categories = set()
        denied_categories = set(data_categories)
        earliest_expiry = None
        
        for consent in consents:
            # Check if consent has expired
            if consent.expiry_date and consent.expiry_date <= datetime.datetime.utcnow():
                self.update_consent_status(consent.id, ConsentStatus.EXPIRED)
                continue
            
            # Check provisions
            for provision in consent.provisions:
                if self._provision_applies(provision, requester_id, purpose, data_categories):
                    result['applicable_consents'].append(consent.id)
                    
                    if provision.type == "permit":
                        for category in provision.data_categories:
                            if category in data_categories:
                                permitted_categories.add(category)
                                denied_categories.discard(category)
                    
                    elif provision.type == "deny":
                        for category in provision.data_categories:
                            if category in data_categories:
                                denied_categories.add(category)
                                permitted_categories.discard(category)
                    
                    # Track conditions and expiry
                    if provision.conditions:
                        result['conditions'].extend(provision.conditions)
                    
                    if provision.period_end:
                        if not earliest_expiry or provision.period_end < earliest_expiry:
                            earliest_expiry = provision.period_end
        
        # Emergency override check
        if purpose == ConsentType.EMERGENCY:
            permitted_categories = set(data_categories)
            denied_categories = set()
            result['conditions'].append('Emergency access - full audit required')
        
        result['permitted'] = len(denied_categories) == 0
        result['denied_categories'] = list(denied_categories)
        result['expires_at'] = earliest_expiry
        
        # Log access check
        self._log_consent_action('access_check', None, patient_id,
                               additional_info={
                                   'requester_id': requester_id,
                                   'purpose': purpose.value,
                                   'permitted': result['permitted']
                               })
        
        return result
    
    def _provision_applies(self, provision: ConsentProvision, requester_id: str,
                          purpose: ConsentType, data_categories: List[DataCategory]) -> bool:
        """Check if provision applies to the request"""
        # Check purpose
        if purpose not in provision.purpose:
            return False
        
        # Check if any requested categories are covered
        if not any(cat in provision.data_categories for cat in data_categories):
            return False
        
        # Check actors (if specified)
        if provision.actors:
            requester_found = any(actor.id == requester_id for actor in provision.actors)
            if not requester_found:
                return False
        
        # Check time period
        now = datetime.datetime.utcnow()
        if provision.period_start and now < provision.period_start:
            return False
        if provision.period_end and now > provision.period_end:
            return False
        
        return True
    
    def generate_consent_summary(self, patient_id: str) -> Dict[str, Any]:
        """Generate summary of patient's consent status"""
        consents = self.get_patient_consents(patient_id)
        
        summary = {
            'patient_id': patient_id,
            'total_consents': len(consents),
            'active_consents': 0,
            'withdrawn_consents': 0,
            'expired_consents': 0,
            'permitted_purposes': set(),
            'permitted_categories': set(),
            'special_restrictions': [],
            'generated_at': datetime.datetime.utcnow().isoformat()
        }
        
        for consent in consents:
            if consent.status == ConsentStatus.ACTIVE:
                summary['active_consents'] += 1
            elif consent.status == ConsentStatus.WITHDRAWN:
                summary['withdrawn_consents'] += 1
            elif consent.status == ConsentStatus.EXPIRED:
                summary['expired_consents'] += 1
            
            # Analyze provisions
            for provision in consent.provisions:
                if provision.type == "permit":
                    summary['permitted_purposes'].update(purpose.value for purpose in provision.purpose)
                    summary['permitted_categories'].update(cat.value for cat in provision.data_categories)
                
                if provision.conditions:
                    summary['special_restrictions'].extend(provision.conditions)
        
        # Convert sets to lists for JSON serialization
        summary['permitted_purposes'] = list(summary['permitted_purposes'])
        summary['permitted_categories'] = list(summary['permitted_categories'])
        
        return summary
    
    def audit_consent_access(self, start_date: datetime.datetime, 
                           end_date: datetime.datetime) -> List[Dict[str, Any]]:
        """Get consent access audit log for date range"""
        filtered_log = []
        
        for entry in self.access_log:
            entry_date = datetime.datetime.fromisoformat(entry['timestamp'])
            if start_date <= entry_date <= end_date:
                filtered_log.append(entry)
        
        return filtered_log
    
    def expire_old_consents(self) -> int:
        """Expire consents that have passed their expiry date"""
        expired_count = 0
        now = datetime.datetime.utcnow()
        
        for consent in self.storage.values():
            if (consent.status == ConsentStatus.ACTIVE and 
                consent.expiry_date and 
                consent.expiry_date <= now):
                
                consent.status = ConsentStatus.EXPIRED
                expired_count += 1
                
                self._log_consent_action('auto_expire', consent.id, consent.patient_id)
        
        return expired_count
    
    def _log_consent_action(self, action: str, consent_id: Optional[str], 
                          patient_id: str, additional_info: Optional[Dict] = None):
        """Log consent-related actions for audit"""
        log_entry = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'action': action,
            'consent_id': consent_id,
            'patient_id': hashlib.sha256(patient_id.encode()).hexdigest()[:16],  # Hash for privacy
            'additional_info': additional_info or {}
        }
        
        self.access_log.append(log_entry)
        logging.info(f"Consent action logged: {log_entry}")


class ConsentTemplateManager:
    """Manages consent templates for different purposes"""
    
    def __init__(self):
        self.templates = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize standard consent templates"""
        # General treatment consent
        self.templates['general_treatment'] = {
            'name': 'General Treatment Consent',
            'description': 'Standard consent for treatment, payment, and operations',
            'scope': ConsentScope.GENERAL.value,
            'category': [ConsentType.TREATMENT.value, ConsentType.PAYMENT.value, ConsentType.OPERATIONS.value],
            'provisions': [{
                'type': 'permit',
                'purpose': [ConsentType.TREATMENT.value, ConsentType.PAYMENT.value, ConsentType.OPERATIONS.value],
                'data_categories': [
                    DataCategory.DEMOGRAPHICS.value,
                    DataCategory.CLINICAL_NOTES.value,
                    DataCategory.LAB_RESULTS.value,
                    DataCategory.PRESCRIPTIONS.value
                ]
            }]
        }
        
        # Research consent
        self.templates['research_consent'] = {
            'name': 'Research Participation Consent',
            'description': 'Consent for research purposes',
            'scope': ConsentScope.SPECIFIC_PURPOSE.value,
            'category': [ConsentType.RESEARCH.value],
            'provisions': [{
                'type': 'permit',
                'purpose': [ConsentType.RESEARCH.value],
                'data_categories': [
                    DataCategory.DEMOGRAPHICS.value,
                    DataCategory.CLINICAL_NOTES.value,
                    DataCategory.LAB_RESULTS.value
                ],
                'conditions': ['Data must be de-identified', 'Research must be IRB approved']
            }]
        }
        
        # Mental health specific consent
        self.templates['mental_health'] = {
            'name': 'Mental Health Treatment Consent',
            'description': 'Specific consent for mental health treatment',
            'scope': ConsentScope.SPECIFIC_DATA.value,
            'category': [ConsentType.TREATMENT.value],
            'provisions': [{
                'type': 'permit',
                'purpose': [ConsentType.TREATMENT.value],
                'data_categories': [DataCategory.MENTAL_HEALTH.value],
                'conditions': ['Requires additional privacy protections']
            }]
        }
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        """Get consent template by ID"""
        return self.templates.get(template_id)
    
    def create_consent_from_template(self, template_id: str, patient_id: str,
                                   customizations: Optional[Dict] = None) -> Dict:
        """Create consent data from template"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        consent_data = template.copy()
        
        # Apply customizations
        if customizations:
            consent_data.update(customizations)
        
        # Set dates
        consent_data['effective_date'] = datetime.datetime.utcnow()
        
        return consent_data