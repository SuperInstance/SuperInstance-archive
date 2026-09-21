"""
Emergency Override System
Provides emergency access mechanisms with strong audit trails and approval workflows
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmergencyType(Enum):
    """Types of emergency situations"""
    SECURITY_INCIDENT = "security_incident"
    SYSTEM_OUTAGE = "system_outage"
    DATA_BREACH = "data_breach"
    BUSINESS_CRITICAL = "business_critical"
    SAFETY_EMERGENCY = "safety_emergency"
    COMPLIANCE_ISSUE = "compliance_issue"
    DISASTER_RECOVERY = "disaster_recovery"
    MAINTENANCE_EMERGENCY = "maintenance_emergency"


class OverrideStatus(Enum):
    """Status of emergency override requests"""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    COMPLETED = "completed"


class ApprovalLevel(Enum):
    """Levels of approval required"""
    SELF_APPROVE = "self_approve"
    SUPERVISOR = "supervisor" 
    MANAGER = "manager"
    SENIOR_MANAGER = "senior_manager"
    EXECUTIVE = "executive"
    BOARD_LEVEL = "board_level"


@dataclass
class EmergencyOverride:
    """Emergency permission override request"""
    override_id: str
    requester_id: str
    emergency_type: EmergencyType
    resource_id: str
    resource_type: str
    requested_permissions: List[str]
    justification: str
    business_impact: str
    duration_hours: int
    status: OverrideStatus
    approval_level: ApprovalLevel
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    activated_at: Optional[datetime]
    expires_at: Optional[datetime]
    revoked_by: Optional[str]
    revoked_at: Optional[datetime]
    created_at: datetime
    emergency_contact: str
    witness_required: bool
    requires_documentation: bool
    follow_up_required: bool
    metadata: Dict[str, Any]


@dataclass
class BreakGlassAccess:
    """Break-glass emergency access configuration"""
    access_id: str
    name: str
    description: str
    resource_patterns: List[str]
    emergency_types: List[EmergencyType]
    max_duration_hours: int
    approval_required: bool
    approval_level: ApprovalLevel
    witness_required: bool
    auto_revoke: bool
    requires_incident_number: bool
    allowed_roles: List[str]
    created_by: str
    created_at: datetime
    is_active: bool


@dataclass
class EmergencySession:
    """Active emergency access session"""
    session_id: str
    override_id: str
    user_id: str
    resource_id: str
    permissions: List[str]
    started_at: datetime
    expires_at: datetime
    last_activity: datetime
    actions_performed: List[Dict[str, Any]]
    is_monitored: bool
    monitor_frequency: int
    witness_id: Optional[str]
    status: str


class EmergencyOverrideManager:
    """Manages emergency override requests and break-glass access"""
    
    def __init__(self, data_dir: str = "emergency_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # In-memory storage
        self.overrides: Dict[str, EmergencyOverride] = {}
        self.break_glass_configs: Dict[str, BreakGlassAccess] = {}
        self.active_sessions: Dict[str, EmergencySession] = {}
        
        # Emergency configuration
        self.max_override_duration = 24  # hours
        self.default_approval_timeout = 30  # minutes
        self.require_witness_for_critical = True
        self.auto_escalation_enabled = True
        self.emergency_contacts = []
        
        # Approval chains
        self.approval_chains = {
            ApprovalLevel.SELF_APPROVE: [],
            ApprovalLevel.SUPERVISOR: ["supervisor"],
            ApprovalLevel.MANAGER: ["supervisor", "manager"],
            ApprovalLevel.SENIOR_MANAGER: ["supervisor", "manager", "senior_manager"],
            ApprovalLevel.EXECUTIVE: ["supervisor", "manager", "senior_manager", "executive"],
            ApprovalLevel.BOARD_LEVEL: ["supervisor", "manager", "senior_manager", "executive", "board_member"]
        }
        
        logger.info("EmergencyOverrideManager initialized")
    
    async def initialize_break_glass_configs(self):
        """Initialize default break-glass access configurations"""
        try:
            default_configs = [
                {
                    "name": "Security Incident Response",
                    "description": "Emergency access for security incident response team",
                    "resource_patterns": ["security/*", "logs/*", "audit/*"],
                    "emergency_types": [EmergencyType.SECURITY_INCIDENT, EmergencyType.DATA_BREACH],
                    "max_duration_hours": 8,
                    "approval_required": True,
                    "approval_level": ApprovalLevel.MANAGER,
                    "witness_required": True,
                    "auto_revoke": True,
                    "requires_incident_number": True,
                    "allowed_roles": ["security_analyst", "incident_responder", "security_manager"]
                },
                {
                    "name": "System Recovery",
                    "description": "Emergency system recovery access",
                    "resource_patterns": ["system/*", "database/*", "infrastructure/*"],
                    "emergency_types": [EmergencyType.SYSTEM_OUTAGE, EmergencyType.DISASTER_RECOVERY],
                    "max_duration_hours": 12,
                    "approval_required": True,
                    "approval_level": ApprovalLevel.SENIOR_MANAGER,
                    "witness_required": False,
                    "auto_revoke": True,
                    "requires_incident_number": True,
                    "allowed_roles": ["system_admin", "devops_engineer", "infrastructure_manager"]
                },
                {
                    "name": "Business Critical Operations",
                    "description": "Emergency access for business-critical operations",
                    "resource_patterns": ["production/*", "customer_data/*", "financial/*"],
                    "emergency_types": [EmergencyType.BUSINESS_CRITICAL, EmergencyType.COMPLIANCE_ISSUE],
                    "max_duration_hours": 6,
                    "approval_required": True,
                    "approval_level": ApprovalLevel.EXECUTIVE,
                    "witness_required": True,
                    "auto_revoke": True,
                    "requires_incident_number": True,
                    "allowed_roles": ["business_manager", "compliance_officer", "executive"]
                }
            ]
            
            for config_data in default_configs:
                access_id = f"bg_{len(self.break_glass_configs)}_{int(datetime.now().timestamp())}"
                
                break_glass = BreakGlassAccess(
                    access_id=access_id,
                    name=config_data["name"],
                    description=config_data["description"],
                    resource_patterns=config_data["resource_patterns"],
                    emergency_types=config_data["emergency_types"],
                    max_duration_hours=config_data["max_duration_hours"],
                    approval_required=config_data["approval_required"],
                    approval_level=config_data["approval_level"],
                    witness_required=config_data["witness_required"],
                    auto_revoke=config_data["auto_revoke"],
                    requires_incident_number=config_data["requires_incident_number"],
                    allowed_roles=config_data["allowed_roles"],
                    created_by="system",
                    created_at=datetime.now(timezone.utc),
                    is_active=True
                )
                
                self.break_glass_configs[access_id] = break_glass
            
            logger.info("Initialized default break-glass configurations")
            
        except Exception as e:
            logger.error(f"Error initializing break-glass configs: {e}")
            raise
    
    async def request_emergency_override(
        self,
        requester_id: str,
        emergency_type: EmergencyType,
        resource_id: str,
        resource_type: str,
        requested_permissions: List[str],
        justification: str,
        business_impact: str,
        duration_hours: int,
        emergency_contact: str,
        incident_number: Optional[str] = None
    ) -> str:
        """Request an emergency permission override"""
        try:
            override_id = f"emergency_{uuid.uuid4().hex[:12]}"
            
            # Validate duration
            if duration_hours > self.max_override_duration:
                raise ValueError(f"Requested duration ({duration_hours}h) exceeds maximum ({self.max_override_duration}h)")
            
            # Determine required approval level
            approval_level = await self._determine_approval_level(
                emergency_type, resource_type, requested_permissions
            )
            
            # Check if witness is required
            witness_required = await self._requires_witness(emergency_type, resource_type)
            
            override = EmergencyOverride(
                override_id=override_id,
                requester_id=requester_id,
                emergency_type=emergency_type,
                resource_id=resource_id,
                resource_type=resource_type,
                requested_permissions=requested_permissions,
                justification=justification,
                business_impact=business_impact,
                duration_hours=duration_hours,
                status=OverrideStatus.PENDING,
                approval_level=approval_level,
                approved_by=None,
                approved_at=None,
                activated_at=None,
                expires_at=None,
                revoked_by=None,
                revoked_at=None,
                created_at=datetime.now(timezone.utc),
                emergency_contact=emergency_contact,
                witness_required=witness_required,
                requires_documentation=True,
                follow_up_required=True,
                metadata={
                    "incident_number": incident_number,
                    "ip_address": "unknown",  # Would be filled from request context
                    "user_agent": "unknown"
                }
            )
            
            self.overrides[override_id] = override
            
            # If self-approval is allowed, auto-approve
            if approval_level == ApprovalLevel.SELF_APPROVE:
                await self._approve_override(override_id, requester_id, "Auto-approved (self-approval allowed)")
            else:
                # Notify approvers
                await self._notify_approvers(override)
            
            await self.save_data()
            
            # Log the request
            logger.critical(
                f"EMERGENCY OVERRIDE REQUESTED - ID: {override_id}, "
                f"User: {requester_id}, Type: {emergency_type.value}, "
                f"Resource: {resource_id}, Duration: {duration_hours}h"
            )
            
            return override_id
            
        except Exception as e:
            logger.error(f"Error requesting emergency override: {e}")
            raise
    
    async def _determine_approval_level(
        self,
        emergency_type: EmergencyType,
        resource_type: str,
        requested_permissions: List[str]
    ) -> ApprovalLevel:
        """Determine the required approval level for an override request"""
        
        # Critical resources require executive approval
        critical_resources = ["financial", "customer_data", "security", "production"]
        if any(cr in resource_type.lower() for cr in critical_resources):
            return ApprovalLevel.EXECUTIVE
        
        # High-privilege permissions require senior manager approval
        high_privilege = ["admin", "owner", "delete", "modify"]
        if any(hp in perm.lower() for perm in requested_permissions for hp in high_privilege):
            return ApprovalLevel.SENIOR_MANAGER
        
        # Security incidents require manager approval
        if emergency_type in [EmergencyType.SECURITY_INCIDENT, EmergencyType.DATA_BREACH]:
            return ApprovalLevel.MANAGER
        
        # Business critical situations require manager approval
        if emergency_type == EmergencyType.BUSINESS_CRITICAL:
            return ApprovalLevel.MANAGER
        
        # Default to supervisor approval
        return ApprovalLevel.SUPERVISOR
    
    async def _requires_witness(self, emergency_type: EmergencyType, resource_type: str) -> bool:
        """Determine if a witness is required for the override"""
        if not self.require_witness_for_critical:
            return False
        
        critical_types = [
            EmergencyType.SECURITY_INCIDENT,
            EmergencyType.DATA_BREACH,
            EmergencyType.BUSINESS_CRITICAL
        ]
        
        critical_resources = ["financial", "customer_data", "security"]
        
        return (emergency_type in critical_types or 
                any(cr in resource_type.lower() for cr in critical_resources))
    
    async def _notify_approvers(self, override: EmergencyOverride):
        """Notify appropriate approvers of the override request"""
        logger.info(f"Notifying approvers for override {override.override_id} (level: {override.approval_level.value})")
        
        # In a real system, this would send notifications via email, SMS, etc.
        # For now, just log the notification
        approver_chain = self.approval_chains.get(override.approval_level, [])
        logger.info(f"Notification sent to approver chain: {approver_chain}")
    
    async def approve_override(
        self,
        override_id: str,
        approver_id: str,
        approval_comment: str = ""
    ) -> bool:
        """Approve an emergency override request"""
        try:
            return await self._approve_override(override_id, approver_id, approval_comment)
        except Exception as e:
            logger.error(f"Error approving override: {e}")
            return False
    
    async def _approve_override(
        self,
        override_id: str,
        approver_id: str,
        approval_comment: str = ""
    ) -> bool:
        """Internal method to approve an override"""
        override = self.overrides.get(override_id)
        if not override:
            raise ValueError(f"Override {override_id} not found")
        
        if override.status != OverrideStatus.PENDING:
            raise ValueError(f"Override {override_id} is not pending approval")
        
        override.status = OverrideStatus.APPROVED
        override.approved_by = approver_id
        override.approved_at = datetime.now(timezone.utc)
        override.metadata["approval_comment"] = approval_comment
        
        await self.save_data()
        
        logger.critical(
            f"EMERGENCY OVERRIDE APPROVED - ID: {override_id}, "
            f"Approver: {approver_id}, Comment: {approval_comment}"
        )
        
        return True
    
    async def deny_override(
        self,
        override_id: str,
        approver_id: str,
        denial_reason: str
    ) -> bool:
        """Deny an emergency override request"""
        try:
            override = self.overrides.get(override_id)
            if not override:
                raise ValueError(f"Override {override_id} not found")
            
            if override.status != OverrideStatus.PENDING:
                raise ValueError(f"Override {override_id} is not pending approval")
            
            override.status = OverrideStatus.DENIED
            override.metadata["denial_reason"] = denial_reason
            override.metadata["denied_by"] = approver_id
            override.metadata["denied_at"] = datetime.now(timezone.utc).isoformat()
            
            await self.save_data()
            
            logger.warning(
                f"EMERGENCY OVERRIDE DENIED - ID: {override_id}, "
                f"Denier: {approver_id}, Reason: {denial_reason}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error denying override: {e}")
            return False
    
    async def activate_override(
        self,
        override_id: str,
        user_id: str,
        witness_id: Optional[str] = None
    ) -> str:
        """Activate an approved emergency override"""
        try:
            override = self.overrides.get(override_id)
            if not override:
                raise ValueError(f"Override {override_id} not found")
            
            if override.status != OverrideStatus.APPROVED:
                raise ValueError(f"Override {override_id} is not approved")
            
            if override.requester_id != user_id:
                raise ValueError("Only the requester can activate their override")
            
            if override.witness_required and not witness_id:
                raise ValueError("Witness required for this override")
            
            # Create emergency session
            session_id = f"session_{uuid.uuid4().hex[:12]}"
            expires_at = datetime.now(timezone.utc) + timedelta(hours=override.duration_hours)
            
            session = EmergencySession(
                session_id=session_id,
                override_id=override_id,
                user_id=user_id,
                resource_id=override.resource_id,
                permissions=override.requested_permissions,
                started_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                last_activity=datetime.now(timezone.utc),
                actions_performed=[],
                is_monitored=True,
                monitor_frequency=5,  # minutes
                witness_id=witness_id,
                status="active"
            )
            
            self.active_sessions[session_id] = session
            
            # Update override status
            override.status = OverrideStatus.ACTIVE
            override.activated_at = datetime.now(timezone.utc)
            override.expires_at = expires_at
            
            await self.save_data()
            
            logger.critical(
                f"EMERGENCY OVERRIDE ACTIVATED - Session: {session_id}, "
                f"Override: {override_id}, User: {user_id}, Witness: {witness_id}, "
                f"Expires: {expires_at.isoformat()}"
            )
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error activating override: {e}")
            raise
    
    async def revoke_override(
        self,
        override_id: str,
        revoker_id: str,
        revocation_reason: str
    ) -> bool:
        """Revoke an active emergency override"""
        try:
            override = self.overrides.get(override_id)
            if not override:
                raise ValueError(f"Override {override_id} not found")
            
            if override.status not in [OverrideStatus.ACTIVE, OverrideStatus.APPROVED]:
                raise ValueError(f"Override {override_id} is not active or approved")
            
            # Find and terminate any active sessions
            for session in self.active_sessions.values():
                if session.override_id == override_id:
                    session.status = "revoked"
            
            override.status = OverrideStatus.REVOKED
            override.revoked_by = revoker_id
            override.revoked_at = datetime.now(timezone.utc)
            override.metadata["revocation_reason"] = revocation_reason
            
            await self.save_data()
            
            logger.critical(
                f"EMERGENCY OVERRIDE REVOKED - ID: {override_id}, "
                f"Revoker: {revoker_id}, Reason: {revocation_reason}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error revoking override: {e}")
            return False
    
    async def check_emergency_access(
        self,
        user_id: str,
        resource_id: str,
        requested_permission: str,
        session_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check if user has emergency access to resource"""
        try:
            # Check active emergency sessions
            if session_id:
                session = self.active_sessions.get(session_id)
                if (session and 
                    session.user_id == user_id and
                    session.resource_id == resource_id and
                    session.status == "active" and
                    datetime.now(timezone.utc) < session.expires_at and
                    requested_permission in session.permissions):
                    
                    # Update last activity
                    session.last_activity = datetime.now(timezone.utc)
                    return True, session_id
            
            # Check all active sessions for user
            for session in self.active_sessions.values():
                if (session.user_id == user_id and
                    session.resource_id == resource_id and
                    session.status == "active" and
                    datetime.now(timezone.utc) < session.expires_at and
                    requested_permission in session.permissions):
                    
                    session.last_activity = datetime.now(timezone.utc)
                    return True, session.session_id
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking emergency access: {e}")
            return False, None
    
    async def log_emergency_action(
        self,
        session_id: str,
        action: str,
        resource_affected: str,
        details: Dict[str, Any]
    ):
        """Log an action performed during emergency access"""
        try:
            session = self.active_sessions.get(session_id)
            if session:
                action_record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": action,
                    "resource_affected": resource_affected,
                    "details": details
                }
                session.actions_performed.append(action_record)
                session.last_activity = datetime.now(timezone.utc)
                
                logger.warning(
                    f"EMERGENCY ACTION LOGGED - Session: {session_id}, "
                    f"Action: {action}, Resource: {resource_affected}"
                )
                
        except Exception as e:
            logger.error(f"Error logging emergency action: {e}")
    
    async def get_active_overrides(self) -> List[EmergencyOverride]:
        """Get all currently active emergency overrides"""
        active_overrides = []
        current_time = datetime.now(timezone.utc)
        
        for override in self.overrides.values():
            if (override.status == OverrideStatus.ACTIVE and
                (not override.expires_at or override.expires_at > current_time)):
                active_overrides.append(override)
        
        return active_overrides
    
    async def get_pending_approvals(self, approver_id: str) -> List[EmergencyOverride]:
        """Get pending override requests that require approval from the specified approver"""
        # This is a simplified implementation
        # In practice, would check approver's role and position in approval chain
        pending_overrides = []
        
        for override in self.overrides.values():
            if override.status == OverrideStatus.PENDING:
                pending_overrides.append(override)
        
        return pending_overrides
    
    async def cleanup_expired_sessions(self):
        """Clean up expired emergency sessions"""
        try:
            current_time = datetime.now(timezone.utc)
            expired_sessions = []
            
            for session_id, session in self.active_sessions.items():
                if session.expires_at < current_time and session.status == "active":
                    session.status = "expired"
                    expired_sessions.append(session_id)
                    
                    # Mark associated override as expired
                    override = self.overrides.get(session.override_id)
                    if override and override.status == OverrideStatus.ACTIVE:
                        override.status = OverrideStatus.EXPIRED
            
            if expired_sessions:
                logger.info(f"Expired {len(expired_sessions)} emergency sessions")
                await self.save_data()
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
    
    async def load_data(self):
        """Load emergency data from disk"""
        try:
            # Load overrides
            override_file = self.data_dir / "emergency_overrides.json"
            if override_file.exists():
                with open(override_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        # Convert datetime strings and enums
                        item["emergency_type"] = EmergencyType(item["emergency_type"])
                        item["status"] = OverrideStatus(item["status"])
                        item["approval_level"] = ApprovalLevel(item["approval_level"])
                        item["created_at"] = datetime.fromisoformat(item["created_at"])
                        
                        if item["approved_at"]:
                            item["approved_at"] = datetime.fromisoformat(item["approved_at"])
                        if item["activated_at"]:
                            item["activated_at"] = datetime.fromisoformat(item["activated_at"])
                        if item["expires_at"]:
                            item["expires_at"] = datetime.fromisoformat(item["expires_at"])
                        if item["revoked_at"]:
                            item["revoked_at"] = datetime.fromisoformat(item["revoked_at"])
                        
                        override = EmergencyOverride(**item)
                        self.overrides[override.override_id] = override
            
            # Load break-glass configs
            bg_file = self.data_dir / "break_glass_configs.json"
            if bg_file.exists():
                with open(bg_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        item["emergency_types"] = [EmergencyType(et) for et in item["emergency_types"]]
                        item["approval_level"] = ApprovalLevel(item["approval_level"])
                        item["created_at"] = datetime.fromisoformat(item["created_at"])
                        
                        break_glass = BreakGlassAccess(**item)
                        self.break_glass_configs[break_glass.access_id] = break_glass
            
            # Load active sessions
            session_file = self.data_dir / "active_sessions.json"
            if session_file.exists():
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        item["started_at"] = datetime.fromisoformat(item["started_at"])
                        item["expires_at"] = datetime.fromisoformat(item["expires_at"])
                        item["last_activity"] = datetime.fromisoformat(item["last_activity"])
                        
                        session = EmergencySession(**item)
                        self.active_sessions[session.session_id] = session
            
            logger.info("Loaded emergency data from disk")
            
        except Exception as e:
            logger.error(f"Error loading emergency data: {e}")
    
    async def save_data(self):
        """Save emergency data to disk"""
        try:
            # Save overrides
            override_file = self.data_dir / "emergency_overrides.json"
            with open(override_file, 'w') as f:
                data = []
                for override in self.overrides.values():
                    item = asdict(override)
                    # Convert enums and datetimes to strings
                    item["emergency_type"] = override.emergency_type.value
                    item["status"] = override.status.value
                    item["approval_level"] = override.approval_level.value
                    item["created_at"] = override.created_at.isoformat()
                    
                    if override.approved_at:
                        item["approved_at"] = override.approved_at.isoformat()
                    if override.activated_at:
                        item["activated_at"] = override.activated_at.isoformat()
                    if override.expires_at:
                        item["expires_at"] = override.expires_at.isoformat()
                    if override.revoked_at:
                        item["revoked_at"] = override.revoked_at.isoformat()
                    
                    data.append(item)
                
                json.dump(data, f, indent=2)
            
            # Save break-glass configs
            bg_file = self.data_dir / "break_glass_configs.json"
            with open(bg_file, 'w') as f:
                data = []
                for break_glass in self.break_glass_configs.values():
                    item = asdict(break_glass)
                    item["emergency_types"] = [et.value for et in break_glass.emergency_types]
                    item["approval_level"] = break_glass.approval_level.value
                    item["created_at"] = break_glass.created_at.isoformat()
                    data.append(item)
                
                json.dump(data, f, indent=2)
            
            # Save active sessions
            session_file = self.data_dir / "active_sessions.json"
            with open(session_file, 'w') as f:
                data = []
                for session in self.active_sessions.values():
                    item = asdict(session)
                    item["started_at"] = session.started_at.isoformat()
                    item["expires_at"] = session.expires_at.isoformat()
                    item["last_activity"] = session.last_activity.isoformat()
                    data.append(item)
                
                json.dump(data, f, indent=2)
            
            logger.info("Saved emergency data to disk")
            
        except Exception as e:
            logger.error(f"Error saving emergency data: {e}")