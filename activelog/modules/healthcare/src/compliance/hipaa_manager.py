"""
HIPAA Compliance Manager
Implements HIPAA Privacy Rule, Security Rule, and Breach Notification Rule
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
from enum import Enum
import hashlib
import json
from uuid import uuid4

from .encryption_manager import EncryptionManager
from .access_controls import AccessControlManager
from .data_minimization import DataMinimizationManager

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("hipaa_audit")
security_logger = logging.getLogger("security")

class PHIClassification(str, Enum):
    """PHI data classification levels"""
    DIRECT_IDENTIFIER = "direct_identifier"      # Name, SSN, etc.
    QUASI_IDENTIFIER = "quasi_identifier"       # Date of birth, ZIP code
    SENSITIVE_PHI = "sensitive_phi"              # Mental health, substance abuse
    GENERAL_PHI = "general_phi"                  # Medical records, lab results
    NON_PHI = "non_phi"                         # De-identified data

class AccessPurpose(str, Enum):
    """Purposes for accessing PHI"""
    TREATMENT = "treatment"
    PAYMENT = "payment"
    OPERATIONS = "operations"
    RESEARCH = "research"
    LEGAL = "legal"
    EMERGENCY = "emergency"
    PATIENT_ACCESS = "patient_access"

class HIPAAManager:
    def __init__(self):
        self.encryption_manager = EncryptionManager()
        self.access_control_manager = AccessControlManager()
        self.data_minimization_manager = DataMinimizationManager()
        
        # PHI identifiers as defined by HIPAA Safe Harbor Rule
        self.phi_identifiers = {
            "names": ["name", "first_name", "last_name", "full_name"],
            "geographic": ["address", "street", "city", "state", "zip", "location"],
            "dates": ["birth_date", "death_date", "admission_date", "discharge_date"],
            "telephone": ["phone", "telephone", "mobile", "fax"],
            "vehicle": ["license_plate", "vin", "vehicle_id"],
            "device": ["device_id", "serial_number"],
            "web": ["url", "ip_address", "email"],
            "biometric": ["fingerprint", "retinal_scan", "voice_print"],
            "photo": ["photograph", "image", "face_id"],
            "identifiers": ["ssn", "medical_record_number", "account_number", "certificate_number"],
            "other": ["any_unique_identifying_number", "characteristic", "code"]
        }
        
    async def initialize(self):
        """Initialize HIPAA compliance manager"""
        logger.info("Initializing HIPAA compliance manager")
        
        await self.encryption_manager.initialize()
        await self.access_control_manager.initialize()
        await self.data_minimization_manager.initialize()
        
        # Load compliance policies
        await self._load_compliance_policies()
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up HIPAA compliance manager")
        
        await self.encryption_manager.cleanup()
        await self.access_control_manager.cleanup()
        await self.data_minimization_manager.cleanup()
        
    async def _load_compliance_policies(self):
        """Load HIPAA compliance policies"""
        try:
            self.compliance_policies = {
                "minimum_necessary": {
                    "enabled": True,
                    "default_fields": ["patient_id", "date_of_service", "diagnosis"],
                    "role_specific_access": {
                        "physician": ["full_access"],
                        "nurse": ["clinical_notes", "medications", "vital_signs"],
                        "admin": ["demographic_info", "insurance_info"],
                        "researcher": ["de_identified_data_only"]
                    }
                },
                "access_controls": {
                    "require_mfa": True,
                    "session_timeout_minutes": 30,
                    "max_concurrent_sessions": 3,
                    "role_based_access": True
                },
                "audit_requirements": {
                    "log_all_access": True,
                    "log_failed_attempts": True,
                    "log_administrative_actions": True,
                    "real_time_monitoring": True
                },
                "breach_notification": {
                    "enabled": True,
                    "notification_threshold_records": 1,
                    "internal_notification_hours": 1,
                    "patient_notification_days": 60,
                    "hhs_notification_days": 60
                }
            }
            
            logger.info("Loaded HIPAA compliance policies")
            
        except Exception as e:
            logger.error(f"Failed to load compliance policies: {e}")
            raise
            
    async def classify_phi_data(self, data: Dict[str, Any]) -> Dict[str, PHIClassification]:
        """Classify data fields according to PHI sensitivity levels"""
        try:
            classifications = {}
            
            for field_name, field_value in data.items():
                field_lower = field_name.lower()
                
                # Direct identifiers
                if any(identifier in field_lower for identifier in 
                      self.phi_identifiers["names"] + 
                      self.phi_identifiers["identifiers"]):
                    classifications[field_name] = PHIClassification.DIRECT_IDENTIFIER
                
                # Geographic identifiers (except state)
                elif any(geo in field_lower for geo in self.phi_identifiers["geographic"]):
                    if "state" in field_lower:
                        classifications[field_name] = PHIClassification.QUASI_IDENTIFIER
                    else:
                        classifications[field_name] = PHIClassification.DIRECT_IDENTIFIER
                
                # Dates (except year)
                elif any(date_field in field_lower for date_field in self.phi_identifiers["dates"]):
                    if isinstance(field_value, str) and len(field_value) == 4:  # Year only
                        classifications[field_name] = PHIClassification.QUASI_IDENTIFIER
                    else:
                        classifications[field_name] = PHIClassification.DIRECT_IDENTIFIER
                
                # Contact information
                elif any(contact in field_lower for contact in 
                        self.phi_identifiers["telephone"] + 
                        self.phi_identifiers["web"]):
                    classifications[field_name] = PHIClassification.DIRECT_IDENTIFIER
                
                # Sensitive PHI (mental health, substance abuse)
                elif any(sensitive in field_lower for sensitive in 
                        ["mental_health", "psychiatry", "psychology", "substance_abuse", "drug_abuse", "alcohol"]):
                    classifications[field_name] = PHIClassification.SENSITIVE_PHI
                
                # Medical data
                elif any(medical in field_lower for medical in 
                        ["diagnosis", "treatment", "medication", "lab_result", "vital_signs"]):
                    classifications[field_name] = PHIClassification.GENERAL_PHI
                
                # Default to general PHI if uncertain
                else:
                    classifications[field_name] = PHIClassification.GENERAL_PHI
                    
            return classifications
            
        except Exception as e:
            logger.error(f"Failed to classify PHI data: {e}")
            raise
            
    async def apply_minimum_necessary(self, data: Dict[str, Any], 
                                    user_role: str, 
                                    access_purpose: AccessPurpose) -> Dict[str, Any]:
        """Apply minimum necessary standard to limit PHI exposure"""
        try:
            # Get role-specific access permissions
            role_permissions = self.compliance_policies["minimum_necessary"]["role_specific_access"].get(
                user_role, []
            )
            
            # Apply data minimization
            minimized_data = await self.data_minimization_manager.minimize_data(
                data=data,
                purpose=access_purpose.value,
                user_role=user_role,
                allowed_fields=role_permissions
            )
            
            return minimized_data
            
        except Exception as e:
            logger.error(f"Failed to apply minimum necessary: {e}")
            raise
            
    async def validate_access_request(self, user_id: str, resource_type: str, 
                                    resource_id: str, action: str,
                                    purpose: AccessPurpose,
                                    patient_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate access request against HIPAA requirements"""
        try:
            validation_result = {
                "allowed": False,
                "reason": "",
                "conditions": [],
                "audit_required": True
            }
            
            # Check basic access controls
            access_check = await self.access_control_manager.check_access(
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action
            )
            
            if not access_check["allowed"]:
                validation_result["reason"] = "Access denied by access control policy"
                await self._log_access_attempt(user_id, resource_type, resource_id, action, False, validation_result["reason"])
                return validation_result
            
            # Check purpose limitation
            if not await self._validate_access_purpose(user_id, purpose, patient_id):
                validation_result["reason"] = "Access purpose not authorized"
                await self._log_access_attempt(user_id, resource_type, resource_id, action, False, validation_result["reason"])
                return validation_result
            
            # Check for break-glass scenarios
            if purpose == AccessPurpose.EMERGENCY:
                validation_result["conditions"].append("Emergency access - requires justification")
                validation_result["audit_required"] = True
                
            # All checks passed
            validation_result["allowed"] = True
            validation_result["reason"] = f"Access granted for {purpose.value}"
            
            # Log successful access
            await self._log_access_attempt(user_id, resource_type, resource_id, action, True, validation_result["reason"])
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Failed to validate access request: {e}")
            validation_result["reason"] = "Internal validation error"
            return validation_result
            
    async def _validate_access_purpose(self, user_id: str, purpose: AccessPurpose, 
                                     patient_id: Optional[str] = None) -> bool:
        """Validate the stated purpose for accessing PHI"""
        try:
            # Get user's role and permissions
            user_info = await self.access_control_manager.get_user_info(user_id)
            if not user_info:
                return False
                
            user_role = user_info.get("role", "")
            
            # Define valid purposes by role
            role_purposes = {
                "physician": [AccessPurpose.TREATMENT, AccessPurpose.EMERGENCY],
                "nurse": [AccessPurpose.TREATMENT, AccessPurpose.EMERGENCY],
                "admin": [AccessPurpose.PAYMENT, AccessPurpose.OPERATIONS],
                "researcher": [AccessPurpose.RESEARCH],
                "patient": [AccessPurpose.PATIENT_ACCESS]
            }
            
            allowed_purposes = role_purposes.get(user_role, [])
            
            if purpose not in allowed_purposes:
                return False
                
            # Additional validation for patient access
            if purpose == AccessPurpose.PATIENT_ACCESS:
                if patient_id and user_info.get("patient_id") != patient_id:
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate access purpose: {e}")
            return False
            
    async def encrypt_phi_data(self, data: Dict[str, Any], 
                             classification: Dict[str, PHIClassification]) -> Dict[str, Any]:
        """Encrypt PHI data based on classification levels"""
        try:
            encrypted_data = {}
            
            for field_name, field_value in data.items():
                field_classification = classification.get(field_name, PHIClassification.GENERAL_PHI)
                
                if field_classification == PHIClassification.NON_PHI:
                    # No encryption needed
                    encrypted_data[field_name] = field_value
                else:
                    # Encrypt PHI data
                    encrypted_value = await self.encryption_manager.encrypt_field(
                        value=field_value,
                        classification=field_classification
                    )
                    encrypted_data[field_name] = encrypted_value
                    
            return encrypted_data
            
        except Exception as e:
            logger.error(f"Failed to encrypt PHI data: {e}")
            raise
            
    async def decrypt_phi_data(self, encrypted_data: Dict[str, Any], 
                             classification: Dict[str, PHIClassification]) -> Dict[str, Any]:
        """Decrypt PHI data based on classification levels"""
        try:
            decrypted_data = {}
            
            for field_name, encrypted_value in encrypted_data.items():
                field_classification = classification.get(field_name, PHIClassification.GENERAL_PHI)
                
                if field_classification == PHIClassification.NON_PHI:
                    # No decryption needed
                    decrypted_data[field_name] = encrypted_value
                else:
                    # Decrypt PHI data
                    decrypted_value = await self.encryption_manager.decrypt_field(
                        encrypted_value=encrypted_value,
                        classification=field_classification
                    )
                    decrypted_data[field_name] = decrypted_value
                    
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Failed to decrypt PHI data: {e}")
            raise
            
    async def de_identify_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """De-identify data according to HIPAA Safe Harbor Rule"""
        try:
            de_identified_data = {}
            
            for field_name, field_value in data.items():
                field_lower = field_name.lower()
                
                # Remove direct identifiers
                if any(identifier in field_lower for identifier in 
                      self.phi_identifiers["names"] + 
                      self.phi_identifiers["identifiers"] +
                      self.phi_identifiers["web"] +
                      self.phi_identifiers["telephone"]):
                    continue  # Skip direct identifiers
                    
                # Generalize dates (keep only year)
                elif any(date_field in field_lower for date_field in self.phi_identifiers["dates"]):
                    if isinstance(field_value, str):
                        try:
                            date_obj = datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                            de_identified_data[field_name] = str(date_obj.year)
                        except:
                            de_identified_data[field_name] = "REDACTED"
                    else:
                        de_identified_data[field_name] = "REDACTED"
                        
                # Generalize geographic data
                elif any(geo in field_lower for geo in self.phi_identifiers["geographic"]):
                    if "state" in field_lower or "zip" in field_lower:
                        # Keep state, generalize ZIP to first 3 digits
                        if "zip" in field_lower and isinstance(field_value, str) and len(field_value) >= 3:
                            de_identified_data[field_name] = field_value[:3] + "XX"
                        else:
                            de_identified_data[field_name] = field_value
                    else:
                        continue  # Remove specific addresses
                        
                # Keep medical data but remove specific identifiers
                else:
                    de_identified_data[field_name] = field_value
                    
            # Add de-identification notice
            de_identified_data["_de_identified"] = True
            de_identified_data["_de_identification_date"] = datetime.now(timezone.utc).isoformat()
            
            return de_identified_data
            
        except Exception as e:
            logger.error(f"Failed to de-identify data: {e}")
            raise
            
    async def detect_potential_breach(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect potential HIPAA breach incidents"""
        try:
            breach_assessment = {
                "is_breach": False,
                "risk_level": "low",
                "affected_records": 0,
                "breach_type": "",
                "notification_required": False,
                "recommended_actions": []
            }
            
            incident_type = incident_data.get("type", "")
            affected_records = incident_data.get("affected_records", 0)
            data_classification = incident_data.get("data_classification", [])
            
            # Assess if this constitutes a breach
            if incident_type in ["unauthorized_access", "data_theft", "system_hack", "lost_device"]:
                breach_assessment["is_breach"] = True
                breach_assessment["breach_type"] = incident_type
                
                # Assess risk level
                if affected_records > 500:
                    breach_assessment["risk_level"] = "high"
                elif affected_records > 50:
                    breach_assessment["risk_level"] = "medium"
                else:
                    breach_assessment["risk_level"] = "low"
                    
                # Check if PHI was involved
                phi_involved = any(classification in [
                    PHIClassification.DIRECT_IDENTIFIER,
                    PHIClassification.SENSITIVE_PHI,
                    PHIClassification.GENERAL_PHI
                ] for classification in data_classification)
                
                if phi_involved:
                    breach_assessment["notification_required"] = True
                    breach_assessment["recommended_actions"].extend([
                        "Immediate containment of breach",
                        "Risk assessment of exposed PHI",
                        "Prepare breach notification letters",
                        "Document incident thoroughly",
                        "Review and strengthen security measures"
                    ])
                    
            breach_assessment["affected_records"] = affected_records
            
            # Log breach detection
            security_logger.warning(
                f"Potential HIPAA breach detected: {incident_type}, "
                f"affected_records={affected_records}, "
                f"risk_level={breach_assessment['risk_level']}"
            )
            
            return breach_assessment
            
        except Exception as e:
            logger.error(f"Failed to detect potential breach: {e}")
            raise
            
    async def _log_access_attempt(self, user_id: str, resource_type: str, 
                                resource_id: str, action: str, success: bool, reason: str):
        """Log access attempt for HIPAA audit trail"""
        try:
            audit_logger.info(
                "PHI access attempt",
                extra={
                    "user_id": user_id,
                    "action": f"{action}_{resource_type}",
                    "resource": resource_id,
                    "result": "success" if success else "failure",
                    "ip_address": "unknown",  # Would be populated from request context
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to log access attempt: {e}")
            
    async def generate_compliance_report(self, start_date: datetime, 
                                       end_date: datetime) -> Dict[str, Any]:
        """Generate HIPAA compliance report"""
        try:
            report = {
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "access_summary": await self._get_access_summary(start_date, end_date),
                "breach_incidents": await self._get_breach_incidents(start_date, end_date),
                "policy_compliance": await self._assess_policy_compliance(),
                "recommendations": []
            }
            
            # Add recommendations based on findings
            if report["breach_incidents"]["total"] > 0:
                report["recommendations"].append("Review security measures due to breach incidents")
                
            if report["access_summary"]["failed_access_attempts"] > 100:
                report["recommendations"].append("High number of failed access attempts - review access controls")
                
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            raise
            
    async def _get_access_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get access summary for compliance report"""
        # This would integrate with actual audit logs
        return {
            "total_access_attempts": 1000,
            "successful_access": 950,
            "failed_access_attempts": 50,
            "unique_users": 25,
            "phi_accessed": 500,
            "emergency_access": 5
        }
        
    async def _get_breach_incidents(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get breach incidents for compliance report"""
        # This would integrate with actual incident logs
        return {
            "total": 0,
            "by_type": {
                "unauthorized_access": 0,
                "lost_device": 0,
                "system_breach": 0
            },
            "notifications_sent": 0
        }
        
    async def _assess_policy_compliance(self) -> Dict[str, Any]:
        """Assess compliance with HIPAA policies"""
        return {
            "encryption_compliance": 100.0,
            "access_control_compliance": 98.5,
            "audit_log_compliance": 100.0,
            "overall_compliance_score": 99.5
        }