"""
Data Minimization Manager for HIPAA compliance
Implements minimum necessary standard and data usage limitation
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from enum import Enum
import json
import hashlib

logger = logging.getLogger(__name__)

class DataPurpose(str, Enum):
    """Data usage purposes"""
    TREATMENT = "treatment"
    PAYMENT = "payment"
    OPERATIONS = "operations"
    RESEARCH = "research"
    QUALITY_ASSURANCE = "quality_assurance"
    LEGAL_COMPLIANCE = "legal_compliance"
    EMERGENCY = "emergency"
    PATIENT_ACCESS = "patient_access"

class MinimizationLevel(str, Enum):
    """Data minimization levels"""
    FULL_ACCESS = "full_access"      # All data available
    ROLE_LIMITED = "role_limited"    # Limited by role
    PURPOSE_LIMITED = "purpose_limited"  # Limited by purpose
    MINIMUM_NECESSARY = "minimum_necessary"  # Strict minimum
    DE_IDENTIFIED = "de_identified"  # De-identified data only

class DataMinimizationManager:
    def __init__(self):
        self.field_mappings = {}
        self.purpose_requirements = {}
        self.role_field_access = {}
        
    async def initialize(self):
        """Initialize data minimization manager"""
        logger.info("Initializing data minimization manager")
        
        await self._load_field_mappings()
        await self._load_purpose_requirements()
        await self._load_role_field_access()
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up data minimization manager")
        
        self.field_mappings.clear()
        self.purpose_requirements.clear()
        self.role_field_access.clear()
        
    async def _load_field_mappings(self):
        """Load field classification and sensitivity mappings"""
        try:
            self.field_mappings = {
                # Patient demographics
                "patient_id": {"sensitivity": "high", "category": "identifier"},
                "first_name": {"sensitivity": "high", "category": "identifier"},
                "last_name": {"sensitivity": "high", "category": "identifier"},
                "date_of_birth": {"sensitivity": "high", "category": "identifier"},
                "ssn": {"sensitivity": "maximum", "category": "identifier"},
                "address": {"sensitivity": "high", "category": "identifier"},
                "phone_number": {"sensitivity": "medium", "category": "contact"},
                "email": {"sensitivity": "medium", "category": "contact"},
                
                # Medical information
                "diagnosis": {"sensitivity": "high", "category": "medical"},
                "treatment": {"sensitivity": "high", "category": "medical"},
                "medications": {"sensitivity": "high", "category": "medical"},
                "lab_results": {"sensitivity": "medium", "category": "medical"},
                "vital_signs": {"sensitivity": "low", "category": "medical"},
                "allergies": {"sensitivity": "high", "category": "medical"},
                "medical_history": {"sensitivity": "high", "category": "medical"},
                
                # Sensitive conditions
                "mental_health": {"sensitivity": "maximum", "category": "sensitive_medical"},
                "substance_abuse": {"sensitivity": "maximum", "category": "sensitive_medical"},
                "genetic_info": {"sensitivity": "maximum", "category": "sensitive_medical"},
                "reproductive_health": {"sensitivity": "maximum", "category": "sensitive_medical"},
                
                # Financial information
                "insurance_info": {"sensitivity": "medium", "category": "financial"},
                "billing_address": {"sensitivity": "medium", "category": "financial"},
                "payment_method": {"sensitivity": "high", "category": "financial"},
                "claim_amount": {"sensitivity": "low", "category": "financial"},
                
                # Administrative
                "provider_id": {"sensitivity": "low", "category": "administrative"},
                "facility_id": {"sensitivity": "low", "category": "administrative"},
                "department": {"sensitivity": "low", "category": "administrative"},
                "visit_date": {"sensitivity": "medium", "category": "administrative"},
                "admission_date": {"sensitivity": "medium", "category": "administrative"}
            }
            
            logger.info("Loaded field mappings")
            
        except Exception as e:
            logger.error(f"Failed to load field mappings: {e}")
            raise
            
    async def _load_purpose_requirements(self):
        """Load data requirements by purpose"""
        try:
            self.purpose_requirements = {
                DataPurpose.TREATMENT: {
                    "required_fields": [
                        "patient_id", "first_name", "last_name", "date_of_birth",
                        "diagnosis", "treatment", "medications", "allergies",
                        "lab_results", "vital_signs", "medical_history"
                    ],
                    "optional_fields": [
                        "phone_number", "emergency_contact", "insurance_info"
                    ]
                },
                DataPurpose.PAYMENT: {
                    "required_fields": [
                        "patient_id", "first_name", "last_name", "date_of_birth",
                        "diagnosis", "treatment", "insurance_info", "billing_address",
                        "visit_date", "provider_id", "facility_id"
                    ],
                    "optional_fields": [
                        "phone_number", "claim_amount"
                    ]
                },
                DataPurpose.OPERATIONS: {
                    "required_fields": [
                        "patient_id", "diagnosis", "treatment", "provider_id",
                        "facility_id", "department", "visit_date"
                    ],
                    "optional_fields": [
                        "age_group", "gender", "insurance_type"
                    ]
                },
                DataPurpose.RESEARCH: {
                    "required_fields": [
                        "de_identified_id", "age_group", "gender", "diagnosis",
                        "treatment", "lab_results", "outcomes"
                    ],
                    "optional_fields": [
                        "geographic_region", "facility_type"
                    ],
                    "prohibited_fields": [
                        "first_name", "last_name", "ssn", "address", "phone_number",
                        "email", "patient_id", "exact_date_of_birth"
                    ]
                },
                DataPurpose.QUALITY_ASSURANCE: {
                    "required_fields": [
                        "patient_id", "diagnosis", "treatment", "outcomes",
                        "provider_id", "facility_id", "visit_date"
                    ],
                    "optional_fields": [
                        "demographics", "complications"
                    ]
                },
                DataPurpose.PATIENT_ACCESS: {
                    "required_fields": [
                        "patient_id", "first_name", "last_name", "date_of_birth",
                        "diagnosis", "treatment", "medications", "lab_results",
                        "vital_signs", "allergies", "medical_history", "visit_date"
                    ],
                    "optional_fields": [
                        "provider_notes", "billing_info"
                    ]
                },
                DataPurpose.EMERGENCY: {
                    "required_fields": [
                        "patient_id", "first_name", "last_name", "date_of_birth",
                        "allergies", "medications", "medical_history",
                        "emergency_contact"
                    ],
                    "optional_fields": [
                        "diagnosis", "lab_results", "vital_signs"
                    ]
                }
            }
            
            logger.info("Loaded purpose requirements")
            
        except Exception as e:
            logger.error(f"Failed to load purpose requirements: {e}")
            raise
            
    async def _load_role_field_access(self):
        """Load field access permissions by role"""
        try:
            self.role_field_access = {
                "physician": {
                    "full_access": [
                        "patient_id", "first_name", "last_name", "date_of_birth",
                        "diagnosis", "treatment", "medications", "lab_results",
                        "vital_signs", "allergies", "medical_history", "mental_health",
                        "substance_abuse", "reproductive_health"
                    ],
                    "read_only": ["insurance_info", "billing_address"],
                    "prohibited": []
                },
                "nurse": {
                    "full_access": [
                        "patient_id", "first_name", "last_name", "date_of_birth",
                        "medications", "allergies", "vital_signs", "nursing_notes"
                    ],
                    "read_only": [
                        "diagnosis", "treatment", "lab_results", "medical_history"
                    ],
                    "prohibited": ["mental_health", "substance_abuse", "genetic_info"]
                },
                "pharmacist": {
                    "full_access": [
                        "patient_id", "first_name", "last_name", "date_of_birth",
                        "medications", "allergies", "drug_interactions"
                    ],
                    "read_only": ["diagnosis", "lab_results", "kidney_function"],
                    "prohibited": [
                        "mental_health", "substance_abuse", "reproductive_health",
                        "address", "phone_number", "ssn"
                    ]
                },
                "administrator": {
                    "full_access": [
                        "patient_id", "first_name", "last_name", "date_of_birth",
                        "insurance_info", "billing_address", "payment_method"
                    ],
                    "read_only": ["diagnosis", "visit_date", "provider_id"],
                    "prohibited": [
                        "treatment", "medications", "lab_results", "medical_history",
                        "mental_health", "substance_abuse", "genetic_info"
                    ]
                },
                "researcher": {
                    "full_access": [
                        "de_identified_id", "age_group", "gender", "diagnosis",
                        "treatment", "lab_results", "outcomes"
                    ],
                    "read_only": ["geographic_region", "facility_type"],
                    "prohibited": [
                        "patient_id", "first_name", "last_name", "ssn", "address",
                        "phone_number", "email", "exact_date_of_birth"
                    ]
                },
                "billing_staff": {
                    "full_access": [
                        "patient_id", "first_name", "last_name", "date_of_birth",
                        "insurance_info", "billing_address", "claim_amount",
                        "visit_date", "provider_id"
                    ],
                    "read_only": ["diagnosis", "treatment"],
                    "prohibited": [
                        "lab_results", "medications", "medical_history",
                        "mental_health", "substance_abuse", "genetic_info"
                    ]
                }
            }
            
            logger.info("Loaded role field access permissions")
            
        except Exception as e:
            logger.error(f"Failed to load role field access: {e}")
            raise
            
    async def minimize_data(self, data: Dict[str, Any], purpose: str, 
                          user_role: str, allowed_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply data minimization based on purpose and role"""
        try:
            minimized_data = {}
            
            # Get purpose requirements
            purpose_enum = DataPurpose(purpose) if purpose in [p.value for p in DataPurpose] else None
            purpose_reqs = self.purpose_requirements.get(purpose_enum, {}) if purpose_enum else {}
            
            # Get role permissions
            role_perms = self.role_field_access.get(user_role, {})
            
            # Process each field
            for field_name, field_value in data.items():
                if await self._should_include_field(
                    field_name, purpose_reqs, role_perms, allowed_fields
                ):
                    # Apply field-level minimization
                    minimized_value = await self._minimize_field_value(
                        field_name, field_value, purpose, user_role
                    )
                    minimized_data[field_name] = minimized_value
                    
            # Add minimization metadata
            minimized_data["_minimization_applied"] = True
            minimized_data["_purpose"] = purpose
            minimized_data["_user_role"] = user_role
            minimized_data["_minimization_timestamp"] = datetime.now(timezone.utc).isoformat()
            
            return minimized_data
            
        except Exception as e:
            logger.error(f"Failed to minimize data: {e}")
            raise
            
    async def _should_include_field(self, field_name: str, purpose_reqs: Dict[str, Any],
                                  role_perms: Dict[str, List[str]], 
                                  allowed_fields: Optional[List[str]]) -> bool:
        """Determine if field should be included based on requirements and permissions"""
        try:
            # Check if field is prohibited for this purpose
            prohibited_fields = purpose_reqs.get("prohibited_fields", [])
            if field_name in prohibited_fields:
                return False
                
            # Check if field is prohibited for this role
            role_prohibited = role_perms.get("prohibited", [])
            if field_name in role_prohibited:
                return False
                
            # Check if field is in allowed fields list (if provided)
            if allowed_fields and field_name not in allowed_fields:
                return False
                
            # Check if field is required for purpose
            required_fields = purpose_reqs.get("required_fields", [])
            if field_name in required_fields:
                return True
                
            # Check if field is in role's allowed fields
            role_full_access = role_perms.get("full_access", [])
            role_read_only = role_perms.get("read_only", [])
            
            if field_name in role_full_access or field_name in role_read_only:
                return True
                
            # Check if field is optional for purpose
            optional_fields = purpose_reqs.get("optional_fields", [])
            if field_name in optional_fields:
                return True
                
            # Default to excluding unknown fields
            return False
            
        except Exception as e:
            logger.error(f"Failed to check field inclusion: {e}")
            return False
            
    async def _minimize_field_value(self, field_name: str, field_value: Any,
                                  purpose: str, user_role: str) -> Any:
        """Apply field-level minimization transformations"""
        try:
            field_info = self.field_mappings.get(field_name, {})
            field_category = field_info.get("category", "unknown")
            field_sensitivity = field_info.get("sensitivity", "low")
            
            # Apply purpose-specific transformations
            if purpose == DataPurpose.RESEARCH.value:
                return await self._apply_research_minimization(field_name, field_value)
            
            # Apply sensitivity-based transformations
            if field_sensitivity == "maximum":
                return await self._apply_maximum_minimization(field_name, field_value, user_role)
            elif field_sensitivity == "high":
                return await self._apply_high_minimization(field_name, field_value, user_role)
            
            # Apply category-specific transformations
            if field_category == "identifier":
                return await self._apply_identifier_minimization(field_name, field_value, purpose, user_role)
            elif field_category == "medical":
                return await self._apply_medical_minimization(field_name, field_value, purpose, user_role)
                
            return field_value
            
        except Exception as e:
            logger.error(f"Failed to minimize field value: {e}")
            return field_value
            
    async def _apply_research_minimization(self, field_name: str, field_value: Any) -> Any:
        """Apply research-specific data minimization"""
        try:
            # Transform direct identifiers
            if field_name in ["patient_id", "medical_record_number"]:
                # Generate de-identified research ID
                return self._generate_research_id(str(field_value))
            
            # Generalize dates to age ranges
            if field_name == "date_of_birth" and isinstance(field_value, str):
                try:
                    birth_date = datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                    age = datetime.now(timezone.utc).year - birth_date.year
                    return self._get_age_group(age)
                except:
                    return "age_unknown"
                    
            # Generalize geographic information
            if field_name == "address" and isinstance(field_value, str):
                # Extract only state/region
                return self._extract_region(field_value)
                
            # Remove or generalize other identifiers
            if field_name in ["first_name", "last_name", "ssn", "phone_number", "email"]:
                return None  # Remove completely for research
                
            return field_value
            
        except Exception as e:
            logger.error(f"Failed to apply research minimization: {e}")
            return field_value
            
    async def _apply_maximum_minimization(self, field_name: str, field_value: Any, user_role: str) -> Any:
        """Apply maximum security minimization for highly sensitive fields"""
        try:
            # Only allow access to highly privileged roles
            privileged_roles = ["physician", "psychiatrist", "substance_abuse_counselor"]
            
            if user_role not in privileged_roles:
                return "[RESTRICTED]"
                
            return field_value
            
        except Exception as e:
            logger.error(f"Failed to apply maximum minimization: {e}")
            return field_value
            
    async def _apply_high_minimization(self, field_name: str, field_value: Any, user_role: str) -> Any:
        """Apply high-level minimization for sensitive fields"""
        try:
            # Apply role-based restrictions
            if user_role in ["billing_staff", "insurance_reviewer"]:
                if field_name in ["medications", "lab_results", "medical_history"]:
                    return "[CLINICAL_DATA_RESTRICTED]"
                    
            # Generalize sensitive data
            if field_name == "diagnosis" and user_role not in ["physician", "nurse"]:
                return self._generalize_diagnosis(field_value)
                
            return field_value
            
        except Exception as e:
            logger.error(f"Failed to apply high minimization: {e}")
            return field_value
            
    async def _apply_identifier_minimization(self, field_name: str, field_value: Any,
                                           purpose: str, user_role: str) -> Any:
        """Apply minimization for identifier fields"""
        try:
            # For research purposes, remove or generalize identifiers
            if purpose == DataPurpose.RESEARCH.value:
                return None
                
            # For billing staff, limit access to certain identifiers
            if user_role == "billing_staff" and field_name == "ssn":
                if isinstance(field_value, str) and len(field_value) >= 4:
                    return "XXX-XX-" + field_value[-4:]
                    
            return field_value
            
        except Exception as e:
            logger.error(f"Failed to apply identifier minimization: {e}")
            return field_value
            
    async def _apply_medical_minimization(self, field_name: str, field_value: Any,
                                        purpose: str, user_role: str) -> Any:
        """Apply minimization for medical fields"""
        try:
            # For payment purposes, may need to generalize some medical details
            if purpose == DataPurpose.PAYMENT.value and field_name == "treatment":
                return self._generalize_treatment(field_value)
                
            # For operations purposes, may aggregate data
            if purpose == DataPurpose.OPERATIONS.value:
                return self._aggregate_medical_data(field_name, field_value)
                
            return field_value
            
        except Exception as e:
            logger.error(f"Failed to apply medical minimization: {e}")
            return field_value
            
    def _generate_research_id(self, original_id: str) -> str:
        """Generate de-identified research ID"""
        try:
            # Create hash-based research ID
            hash_input = f"research_salt_{original_id}".encode()
            hash_obj = hashlib.sha256(hash_input)
            return f"R{hash_obj.hexdigest()[:8].upper()}"
            
        except Exception as e:
            logger.error(f"Failed to generate research ID: {e}")
            return "R_UNKNOWN"
            
    def _get_age_group(self, age: int) -> str:
        """Convert age to age group"""
        try:
            if age < 1:
                return "infant"
            elif age < 18:
                return "pediatric"
            elif age < 65:
                return "adult"
            else:
                return "geriatric"
                
        except Exception as e:
            logger.error(f"Failed to get age group: {e}")
            return "age_unknown"
            
    def _extract_region(self, address: str) -> str:
        """Extract region from address"""
        try:
            # Simple extraction - in practice would use more sophisticated parsing
            parts = address.split(',')
            if len(parts) >= 2:
                return parts[-2].strip()  # State/region
            return "region_unknown"
            
        except Exception as e:
            logger.error(f"Failed to extract region: {e}")
            return "region_unknown"
            
    def _generalize_diagnosis(self, diagnosis: Any) -> str:
        """Generalize diagnosis to category level"""
        try:
            # Simple generalization - in practice would use medical coding systems
            if isinstance(diagnosis, str):
                if "diabetes" in diagnosis.lower():
                    return "endocrine_disorder"
                elif "hypertension" in diagnosis.lower():
                    return "cardiovascular_disorder"
                elif "infection" in diagnosis.lower():
                    return "infectious_disease"
                else:
                    return "medical_condition"
            return "condition_unknown"
            
        except Exception as e:
            logger.error(f"Failed to generalize diagnosis: {e}")
            return "condition_unknown"
            
    def _generalize_treatment(self, treatment: Any) -> str:
        """Generalize treatment information"""
        try:
            if isinstance(treatment, str):
                if "surgery" in treatment.lower():
                    return "surgical_intervention"
                elif "medication" in treatment.lower():
                    return "pharmacological_treatment"
                elif "therapy" in treatment.lower():
                    return "therapeutic_intervention"
                else:
                    return "medical_treatment"
            return "treatment_provided"
            
        except Exception as e:
            logger.error(f"Failed to generalize treatment: {e}")
            return "treatment_provided"
            
    def _aggregate_medical_data(self, field_name: str, field_value: Any) -> Any:
        """Aggregate medical data for operations purposes"""
        try:
            # For operations, might return aggregated or categorical data
            if field_name == "lab_results" and isinstance(field_value, dict):
                # Return only abnormal flags, not specific values
                return {key: "normal" if "normal" in str(value).lower() else "abnormal" 
                       for key, value in field_value.items()}
                       
            return field_value
            
        except Exception as e:
            logger.error(f"Failed to aggregate medical data: {e}")
            return field_value
            
    async def create_data_usage_log(self, user_id: str, purpose: str, 
                                  data_accessed: List[str], minimization_level: MinimizationLevel):
        """Log data usage for compliance tracking"""
        try:
            usage_log = {
                "user_id": user_id,
                "purpose": purpose,
                "data_fields_accessed": data_accessed,
                "minimization_level": minimization_level.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "compliance_check": True
            }
            
            # In practice, this would be stored in a secure audit database
            logger.info(f"Data usage logged: {json.dumps(usage_log)}")
            
        except Exception as e:
            logger.error(f"Failed to create data usage log: {e}")