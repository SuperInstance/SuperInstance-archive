"""
Access Control Manager for HIPAA compliance
Implements role-based access control (RBAC) and attribute-based access control (ABAC)
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
from enum import Enum
import json

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security")

class HealthcareRole(str, Enum):
    """Healthcare-specific roles"""
    PHYSICIAN = "physician"
    NURSE = "nurse"
    PHARMACIST = "pharmacist"
    TECHNICIAN = "technician"
    ADMINISTRATOR = "administrator"
    RESEARCHER = "researcher"
    PATIENT = "patient"
    EMERGENCY_RESPONDER = "emergency_responder"
    BILLING_STAFF = "billing_staff"
    INSURANCE_REVIEWER = "insurance_reviewer"

class ResourceType(str, Enum):
    """Healthcare resource types"""
    PATIENT_RECORD = "patient_record"
    MEDICAL_IMAGE = "medical_image"
    LAB_RESULT = "lab_result"
    PRESCRIPTION = "prescription"
    CLINICAL_NOTE = "clinical_note"
    BILLING_RECORD = "billing_record"
    INSURANCE_CLAIM = "insurance_claim"
    RESEARCH_DATA = "research_data"
    DEVICE_DATA = "device_data"
    AUDIT_LOG = "audit_log"

class AccessAction(str, Enum):
    """Access actions"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"
    PRINT = "print"
    SHARE = "share"
    ANONYMIZE = "anonymize"
    ADMIN = "admin"

class AccessControlManager:
    def __init__(self):
        self.access_policies = {}
        self.role_permissions = {}
        self.active_sessions = {}
        self.failed_attempts = {}
        
    async def initialize(self):
        """Initialize access control manager"""
        logger.info("Initializing access control manager")
        
        await self._load_access_policies()
        await self._load_role_permissions()
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up access control manager")
        
        self.access_policies.clear()
        self.role_permissions.clear()
        self.active_sessions.clear()
        self.failed_attempts.clear()
        
    async def _load_access_policies(self):
        """Load HIPAA-compliant access policies"""
        try:
            self.access_policies = {
                "minimum_necessary": {
                    "enabled": True,
                    "description": "Limit access to minimum necessary PHI"
                },
                "purpose_limitation": {
                    "enabled": True,
                    "description": "Access must have legitimate healthcare purpose"
                },
                "role_based_access": {
                    "enabled": True,
                    "description": "Access based on job function and role"
                },
                "patient_consent": {
                    "enabled": True,
                    "description": "Verify patient consent for access"
                },
                "emergency_access": {
                    "enabled": True,
                    "description": "Break-glass access for emergencies"
                },
                "audit_logging": {
                    "enabled": True,
                    "description": "Log all access attempts and activities"
                },
                "session_management": {
                    "enabled": True,
                    "timeout_minutes": 30,
                    "max_concurrent_sessions": 3
                },
                "failed_login_protection": {
                    "enabled": True,
                    "max_attempts": 3,
                    "lockout_duration_minutes": 30
                }
            }
            
            logger.info("Loaded access policies")
            
        except Exception as e:
            logger.error(f"Failed to load access policies: {e}")
            raise
            
    async def _load_role_permissions(self):
        """Load role-based permissions matrix"""
        try:
            self.role_permissions = {
                HealthcareRole.PHYSICIAN: {
                    ResourceType.PATIENT_RECORD: [AccessAction.READ, AccessAction.WRITE],
                    ResourceType.MEDICAL_IMAGE: [AccessAction.READ, AccessAction.WRITE],
                    ResourceType.LAB_RESULT: [AccessAction.READ, AccessAction.WRITE],
                    ResourceType.PRESCRIPTION: [AccessAction.READ, AccessAction.WRITE],
                    ResourceType.CLINICAL_NOTE: [AccessAction.READ, AccessAction.WRITE]
                },
                HealthcareRole.NURSE: {
                    ResourceType.PATIENT_RECORD: [AccessAction.READ, AccessAction.WRITE],
                    ResourceType.LAB_RESULT: [AccessAction.READ],
                    ResourceType.PRESCRIPTION: [AccessAction.READ],
                    ResourceType.CLINICAL_NOTE: [AccessAction.READ, AccessAction.WRITE]
                },
                HealthcareRole.PHARMACIST: {
                    ResourceType.PATIENT_RECORD: [AccessAction.READ],
                    ResourceType.PRESCRIPTION: [AccessAction.READ, AccessAction.WRITE],
                    ResourceType.LAB_RESULT: [AccessAction.READ]
                },
                HealthcareRole.TECHNICIAN: {
                    ResourceType.MEDICAL_IMAGE: [AccessAction.READ, AccessAction.WRITE],
                    ResourceType.LAB_RESULT: [AccessAction.READ, AccessAction.WRITE],
                    ResourceType.DEVICE_DATA: [AccessAction.READ, AccessAction.WRITE]
                },
                HealthcareRole.ADMINISTRATOR: {
                    ResourceType.PATIENT_RECORD: [AccessAction.READ],
                    ResourceType.BILLING_RECORD: [AccessAction.READ, AccessAction.WRITE],
                    ResourceType.INSURANCE_CLAIM: [AccessAction.READ, AccessAction.WRITE],
                    ResourceType.AUDIT_LOG: [AccessAction.READ, AccessAction.EXPORT]
                },
                HealthcareRole.RESEARCHER: {
                    ResourceType.RESEARCH_DATA: [AccessAction.READ, AccessAction.WRITE, AccessAction.ANONYMIZE],
                    ResourceType.PATIENT_RECORD: [AccessAction.READ],  # Only de-identified
                    ResourceType.LAB_RESULT: [AccessAction.READ]       # Only de-identified
                },
                HealthcareRole.PATIENT: {
                    ResourceType.PATIENT_RECORD: [AccessAction.READ, AccessAction.EXPORT],
                    ResourceType.MEDICAL_IMAGE: [AccessAction.READ],
                    ResourceType.LAB_RESULT: [AccessAction.READ],
                    ResourceType.PRESCRIPTION: [AccessAction.READ],
                    ResourceType.BILLING_RECORD: [AccessAction.READ]
                },
                HealthcareRole.EMERGENCY_RESPONDER: {
                    ResourceType.PATIENT_RECORD: [AccessAction.READ],
                    ResourceType.MEDICAL_IMAGE: [AccessAction.READ],
                    ResourceType.LAB_RESULT: [AccessAction.READ],
                    ResourceType.PRESCRIPTION: [AccessAction.READ]
                },
                HealthcareRole.BILLING_STAFF: {
                    ResourceType.PATIENT_RECORD: [AccessAction.READ],  # Demographics only
                    ResourceType.BILLING_RECORD: [AccessAction.READ, AccessAction.WRITE],
                    ResourceType.INSURANCE_CLAIM: [AccessAction.READ, AccessAction.WRITE]
                },
                HealthcareRole.INSURANCE_REVIEWER: {
                    ResourceType.PATIENT_RECORD: [AccessAction.READ],  # Limited fields
                    ResourceType.MEDICAL_IMAGE: [AccessAction.READ],
                    ResourceType.LAB_RESULT: [AccessAction.READ],
                    ResourceType.INSURANCE_CLAIM: [AccessAction.READ, AccessAction.WRITE]
                }
            }
            
            logger.info("Loaded role permissions matrix")
            
        except Exception as e:
            logger.error(f"Failed to load role permissions: {e}")
            raise
            
    async def check_access(self, user_id: str, resource_type: str, 
                         resource_id: str, action: str,
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Check if user has access to perform action on resource"""
        try:
            access_result = {
                "allowed": False,
                "reason": "",
                "conditions": [],
                "audit_required": True
            }
            
            # Get user information
            user_info = await self.get_user_info(user_id)
            if not user_info:
                access_result["reason"] = "User not found"
                return access_result
                
            # Check session validity
            if not await self._validate_session(user_id):
                access_result["reason"] = "Invalid or expired session"
                return access_result
                
            # Check account lockout
            if await self._is_account_locked(user_id):
                access_result["reason"] = "Account is locked due to failed login attempts"
                return access_result
                
            user_role = HealthcareRole(user_info["role"])
            resource_type_enum = ResourceType(resource_type)
            action_enum = AccessAction(action)
            
            # Check role-based permissions
            if not self._check_role_permission(user_role, resource_type_enum, action_enum):
                access_result["reason"] = f"Role {user_role.value} does not have {action} permission for {resource_type}"
                return access_result
                
            # Apply additional HIPAA-specific checks
            additional_checks = await self._apply_hipaa_checks(
                user_id, user_role, resource_type_enum, resource_id, action_enum, context
            )
            
            if not additional_checks["allowed"]:
                access_result["reason"] = additional_checks["reason"]
                access_result["conditions"] = additional_checks["conditions"]
                return access_result
                
            # Check patient consent if required
            if resource_type_enum == ResourceType.PATIENT_RECORD and context:
                patient_id = context.get("patient_id")
                if patient_id and not await self._check_patient_consent(patient_id, user_id, action):
                    access_result["reason"] = "Patient consent required for this access"
                    access_result["conditions"] = ["obtain_patient_consent"]
                    return access_result
                    
            # All checks passed
            access_result["allowed"] = True
            access_result["reason"] = "Access granted"
            access_result["conditions"] = additional_checks["conditions"]
            
            return access_result
            
        except Exception as e:
            logger.error(f"Failed to check access: {e}")
            access_result["reason"] = "Internal access check error"
            return access_result
            
    def _check_role_permission(self, role: HealthcareRole, resource_type: ResourceType, 
                              action: AccessAction) -> bool:
        """Check if role has permission for action on resource type"""
        try:
            role_permissions = self.role_permissions.get(role, {})
            allowed_actions = role_permissions.get(resource_type, [])
            return action in allowed_actions
            
        except Exception as e:
            logger.error(f"Failed to check role permission: {e}")
            return False
            
    async def _apply_hipaa_checks(self, user_id: str, user_role: HealthcareRole,
                                resource_type: ResourceType, resource_id: str,
                                action: AccessAction, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply HIPAA-specific access checks"""
        try:
            result = {
                "allowed": True,
                "reason": "",
                "conditions": []
            }
            
            # Check minimum necessary principle
            if resource_type == ResourceType.PATIENT_RECORD:
                if user_role not in [HealthcareRole.PHYSICIAN, HealthcareRole.NURSE]:
                    if action in [AccessAction.READ, AccessAction.WRITE]:
                        result["conditions"].append("minimum_necessary_justification")
                        
            # Check purpose limitation
            if context and "purpose" in context:
                if not await self._validate_access_purpose(user_role, context["purpose"]):
                    result["allowed"] = False
                    result["reason"] = "Access purpose not valid for user role"
                    return result
                    
            # Check for research access restrictions
            if user_role == HealthcareRole.RESEARCHER:
                if resource_type in [ResourceType.PATIENT_RECORD, ResourceType.LAB_RESULT]:
                    result["conditions"].append("de_identification_required")
                    
            # Check emergency access
            if context and context.get("emergency_access"):
                if user_role == HealthcareRole.EMERGENCY_RESPONDER:
                    result["conditions"].extend([
                        "emergency_justification_required",
                        "supervisor_notification",
                        "detailed_audit_logging"
                    ])
                else:
                    result["allowed"] = False
                    result["reason"] = "Emergency access not authorized for this role"
                    return result
                    
            # Check patient-specific access for own records
            if user_role == HealthcareRole.PATIENT and context:
                patient_id = context.get("patient_id")
                if patient_id != user_id:
                    result["allowed"] = False
                    result["reason"] = "Patients can only access their own records"
                    return result
                    
            # Check time-based access restrictions
            if not await self._check_time_based_access(user_role):
                result["conditions"].append("outside_normal_hours_justification")
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to apply HIPAA checks: {e}")
            return {"allowed": False, "reason": "Internal HIPAA check error", "conditions": []}
            
    async def _validate_access_purpose(self, user_role: HealthcareRole, purpose: str) -> bool:
        """Validate if access purpose is appropriate for user role"""
        try:
            valid_purposes_by_role = {
                HealthcareRole.PHYSICIAN: ["treatment", "diagnosis", "care_coordination"],
                HealthcareRole.NURSE: ["treatment", "care_coordination", "medication_administration"],
                HealthcareRole.PHARMACIST: ["medication_review", "drug_interaction_check"],
                HealthcareRole.ADMINISTRATOR: ["billing", "operations", "quality_assurance"],
                HealthcareRole.RESEARCHER: ["research", "quality_improvement"],
                HealthcareRole.PATIENT: ["personal_access", "care_coordination"],
                HealthcareRole.BILLING_STAFF: ["billing", "insurance_processing"],
                HealthcareRole.INSURANCE_REVIEWER: ["claim_review", "utilization_review"]
            }
            
            valid_purposes = valid_purposes_by_role.get(user_role, [])
            return purpose in valid_purposes
            
        except Exception as e:
            logger.error(f"Failed to validate access purpose: {e}")
            return False
            
    async def _check_time_based_access(self, user_role: HealthcareRole) -> bool:
        """Check if access is within normal business hours for role"""
        try:
            current_time = datetime.now(timezone.utc)
            current_hour = current_time.hour
            
            # Define normal hours by role (24-hour format)
            normal_hours = {
                HealthcareRole.PHYSICIAN: (6, 22),      # 6 AM to 10 PM
                HealthcareRole.NURSE: (0, 24),          # 24/7
                HealthcareRole.ADMINISTRATOR: (8, 18),   # 8 AM to 6 PM
                HealthcareRole.BILLING_STAFF: (8, 17),  # 8 AM to 5 PM
                HealthcareRole.RESEARCHER: (8, 18)      # 8 AM to 6 PM
            }
            
            # Emergency responders and patients have 24/7 access
            if user_role in [HealthcareRole.EMERGENCY_RESPONDER, HealthcareRole.PATIENT]:
                return True
                
            hours = normal_hours.get(user_role, (0, 24))
            return hours[0] <= current_hour < hours[1]
            
        except Exception as e:
            logger.error(f"Failed to check time-based access: {e}")
            return True  # Default to allowing access if check fails
            
    async def _validate_session(self, user_id: str) -> bool:
        """Validate user session"""
        try:
            session = self.active_sessions.get(user_id)
            if not session:
                return False
                
            # Check session expiry
            session_timeout = self.access_policies["session_management"]["timeout_minutes"]
            if datetime.now(timezone.utc) - session["last_activity"] > timedelta(minutes=session_timeout):
                # Session expired
                del self.active_sessions[user_id]
                return False
                
            # Update last activity
            session["last_activity"] = datetime.now(timezone.utc)
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate session: {e}")
            return False
            
    async def _is_account_locked(self, user_id: str) -> bool:
        """Check if account is locked due to failed login attempts"""
        try:
            failed_info = self.failed_attempts.get(user_id)
            if not failed_info:
                return False
                
            max_attempts = self.access_policies["failed_login_protection"]["max_attempts"]
            lockout_duration = self.access_policies["failed_login_protection"]["lockout_duration_minutes"]
            
            if failed_info["count"] >= max_attempts:
                # Check if lockout period has expired
                if datetime.now(timezone.utc) - failed_info["last_attempt"] > timedelta(minutes=lockout_duration):
                    # Reset failed attempts
                    del self.failed_attempts[user_id]
                    return False
                else:
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Failed to check account lock status: {e}")
            return False
            
    async def _check_patient_consent(self, patient_id: str, user_id: str, action: str) -> bool:
        """Check if patient has given consent for this access"""
        try:
            # This would integrate with the consent management system
            # For now, return True - would be implemented with actual consent records
            return True
            
        except Exception as e:
            logger.error(f"Failed to check patient consent: {e}")
            return False
            
    async def create_session(self, user_id: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create user session"""
        try:
            # Check concurrent session limit
            max_sessions = self.access_policies["session_management"]["max_concurrent_sessions"]
            user_sessions = [s for s in self.active_sessions.values() if s["user_id"] == user_id]
            
            if len(user_sessions) >= max_sessions:
                # Terminate oldest session
                oldest_session = min(user_sessions, key=lambda x: x["created_at"])
                del self.active_sessions[oldest_session["session_id"]]
                
            session_id = f"session_{user_id}_{datetime.now(timezone.utc).timestamp()}"
            
            session = {
                "session_id": session_id,
                "user_id": user_id,
                "user_info": user_info,
                "created_at": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc),
                "ip_address": "unknown",  # Would be populated from request
                "user_agent": "unknown"   # Would be populated from request
            }
            
            self.active_sessions[user_id] = session
            
            # Reset failed login attempts on successful login
            if user_id in self.failed_attempts:
                del self.failed_attempts[user_id]
                
            logger.info(f"Created session for user {user_id}")
            return {"session_id": session_id, "expires_in": 30 * 60}  # 30 minutes in seconds
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
            
    async def terminate_session(self, user_id: str):
        """Terminate user session"""
        try:
            if user_id in self.active_sessions:
                del self.active_sessions[user_id]
                logger.info(f"Terminated session for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to terminate session: {e}")
            
    async def record_failed_login(self, user_id: str):
        """Record failed login attempt"""
        try:
            if user_id not in self.failed_attempts:
                self.failed_attempts[user_id] = {"count": 0, "first_attempt": datetime.now(timezone.utc)}
                
            self.failed_attempts[user_id]["count"] += 1
            self.failed_attempts[user_id]["last_attempt"] = datetime.now(timezone.utc)
            
            # Log security event
            security_logger.warning(
                f"Failed login attempt for user {user_id}. "
                f"Total attempts: {self.failed_attempts[user_id]['count']}"
            )
            
        except Exception as e:
            logger.error(f"Failed to record failed login: {e}")
            
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information (would integrate with user management system)"""
        try:
            # This would integrate with actual user management system
            # For now, return mock data
            mock_users = {
                "doc001": {"role": "physician", "department": "cardiology", "active": True},
                "nurse001": {"role": "nurse", "department": "emergency", "active": True},
                "admin001": {"role": "administrator", "department": "it", "active": True},
                "patient001": {"role": "patient", "patient_id": "patient001", "active": True}
            }
            
            return mock_users.get(user_id)
            
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None
            
    async def get_access_summary(self, user_id: str) -> Dict[str, Any]:
        """Get access summary for user"""
        try:
            user_info = await self.get_user_info(user_id)
            if not user_info:
                return {}
                
            user_role = HealthcareRole(user_info["role"])
            permissions = self.role_permissions.get(user_role, {})
            
            return {
                "user_id": user_id,
                "role": user_role.value,
                "permissions": {
                    resource_type.value: [action.value for action in actions]
                    for resource_type, actions in permissions.items()
                },
                "session_active": user_id in self.active_sessions,
                "account_locked": await self._is_account_locked(user_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to get access summary: {e}")
            return {}