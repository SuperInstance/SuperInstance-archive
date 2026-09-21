"""
Role-Based Permissions System
Comprehensive permission management for crew roles and operations
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import logging
from functools import wraps

from ..crew.crew_management import CrewRole

logger = logging.getLogger(__name__)

class Permission(Enum):
    # Navigation permissions
    VIEW_NAVIGATION = "view_navigation"
    CONTROL_AUTOPILOT = "control_autopilot"
    SET_COURSE = "set_course"
    OVERRIDE_AUTOPILOT = "override_autopilot"
    EMERGENCY_STOP = "emergency_stop"
    
    # Crew management permissions
    INVITE_CREW = "invite_crew"
    MANAGE_CREW = "manage_crew"
    VIEW_CREW_INFO = "view_crew_info"
    ASSIGN_TASKS = "assign_tasks"
    MANAGE_SCHEDULES = "manage_schedules"
    VIEW_SCHEDULES = "view_schedules"
    
    # Safety permissions
    INITIATE_EMERGENCY = "initiate_emergency"
    CONDUCT_SAFETY_DRILLS = "conduct_safety_drills"
    OVERRIDE_SAFETY_SYSTEMS = "override_safety_systems"
    VIEW_SAFETY_STATUS = "view_safety_status"
    MANAGE_SAFETY_EQUIPMENT = "manage_safety_equipment"
    
    # Fishing operations permissions
    VIEW_FISH_FINDER = "view_fish_finder"
    CONTROL_FISH_FINDER = "control_fish_finder"
    LOG_CATCHES = "log_catches"
    VIEW_CATCH_DATA = "view_catch_data"
    MANAGE_FISHING_SPOTS = "manage_fishing_spots"
    
    # Financial permissions
    VIEW_SHARES = "view_shares"
    CALCULATE_SHARES = "calculate_shares"
    MANAGE_EXPENSES = "manage_expenses"
    VIEW_FINANCIAL_REPORTS = "view_financial_reports"
    
    # System permissions
    VIEW_SYSTEM_STATUS = "view_system_status"
    MANAGE_SYSTEM_SETTINGS = "manage_system_settings"
    ACCESS_LOGS = "access_logs"
    BACKUP_DATA = "backup_data"
    
    # Communication permissions
    SEND_BROADCASTS = "send_broadcasts"
    MANAGE_COMMUNICATIONS = "manage_communications"
    DISTRESS_CALLS = "distress_calls"
    
    # Watch permissions
    STAND_WATCH = "stand_watch"
    ASSIGN_WATCH = "assign_watch"
    OVERRIDE_WATCH = "override_watch"

class PermissionScope(Enum):
    GLOBAL = "global"          # System-wide permission
    VESSEL = "vessel"          # Vessel-specific permission
    TRIP = "trip"             # Trip-specific permission
    WATCH = "watch"           # Watch-specific permission

class AccessLevel(Enum):
    NONE = 0
    READ = 1
    WRITE = 2
    ADMIN = 3

@dataclass
class PermissionGrant:
    permission: Permission
    scope: PermissionScope
    access_level: AccessLevel
    conditions: Optional[Dict[str, Any]] = None  # Time-based, location-based, etc.
    expires_at: Optional[datetime] = None
    granted_by: Optional[str] = None
    granted_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.granted_at is None:
            self.granted_at = datetime.now(timezone.utc)
        if self.conditions is None:
            self.conditions = {}
    
    def is_valid(self) -> bool:
        """Check if permission grant is still valid"""
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        
        # Check time-based conditions
        if 'valid_hours' in self.conditions:
            current_hour = datetime.now().hour
            valid_hours = self.conditions['valid_hours']
            if current_hour not in valid_hours:
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['permission'] = self.permission.value
        result['scope'] = self.scope.value
        result['access_level'] = self.access_level.value
        if result.get('expires_at'):
            result['expires_at'] = result['expires_at'].isoformat()
        if result.get('granted_at'):
            result['granted_at'] = result['granted_at'].isoformat()
        return result

@dataclass
class RolePermissionSet:
    role: CrewRole
    permissions: List[PermissionGrant]
    description: str = ""
    
    def has_permission(self, permission: Permission, scope: PermissionScope = PermissionScope.VESSEL,
                      access_level: AccessLevel = AccessLevel.READ) -> bool:
        """Check if role has specific permission"""
        for grant in self.permissions:
            if (grant.permission == permission and 
                grant.scope == scope and 
                grant.access_level.value >= access_level.value and
                grant.is_valid()):
                return True
        return False
    
    def get_permissions_by_scope(self, scope: PermissionScope) -> List[PermissionGrant]:
        """Get permissions for specific scope"""
        return [grant for grant in self.permissions if grant.scope == scope and grant.is_valid()]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'role': self.role.value,
            'permissions': [p.to_dict() for p in self.permissions],
            'description': self.description
        }

class PermissionManager:
    """Manages role-based permissions and access control"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.role_permissions: Dict[CrewRole, RolePermissionSet] = {}
        
        # Initialize default role permissions
        self._setup_default_permissions()
        
        # Permission cache
        self.permission_cache: Dict[str, bool] = {}
        
    def _setup_default_permissions(self):
        """Setup default permissions for each crew role"""
        
        # Captain permissions - Full access
        captain_permissions = [
            PermissionGrant(Permission.VIEW_NAVIGATION, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.CONTROL_AUTOPILOT, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.SET_COURSE, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.OVERRIDE_AUTOPILOT, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.EMERGENCY_STOP, PermissionScope.GLOBAL, AccessLevel.ADMIN),
            PermissionGrant(Permission.INVITE_CREW, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.MANAGE_CREW, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.VIEW_CREW_INFO, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.ASSIGN_TASKS, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.MANAGE_SCHEDULES, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.VIEW_SCHEDULES, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.INITIATE_EMERGENCY, PermissionScope.GLOBAL, AccessLevel.ADMIN),
            PermissionGrant(Permission.CONDUCT_SAFETY_DRILLS, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.OVERRIDE_SAFETY_SYSTEMS, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.VIEW_SAFETY_STATUS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.MANAGE_SAFETY_EQUIPMENT, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.VIEW_FISH_FINDER, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.CONTROL_FISH_FINDER, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.LOG_CATCHES, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_CATCH_DATA, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.MANAGE_FISHING_SPOTS, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.VIEW_SHARES, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.CALCULATE_SHARES, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.MANAGE_EXPENSES, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.VIEW_FINANCIAL_REPORTS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_SYSTEM_STATUS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.MANAGE_SYSTEM_SETTINGS, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.ACCESS_LOGS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.BACKUP_DATA, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.SEND_BROADCASTS, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.MANAGE_COMMUNICATIONS, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.DISTRESS_CALLS, PermissionScope.GLOBAL, AccessLevel.ADMIN),
            PermissionGrant(Permission.STAND_WATCH, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.ASSIGN_WATCH, PermissionScope.VESSEL, AccessLevel.ADMIN),
            PermissionGrant(Permission.OVERRIDE_WATCH, PermissionScope.VESSEL, AccessLevel.ADMIN),
        ]
        
        self.role_permissions[CrewRole.CAPTAIN] = RolePermissionSet(
            CrewRole.CAPTAIN, captain_permissions,
            "Full vessel command and operational authority"
        )
        
        # First Mate permissions - High level access
        first_mate_permissions = [
            PermissionGrant(Permission.VIEW_NAVIGATION, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.CONTROL_AUTOPILOT, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.SET_COURSE, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.OVERRIDE_AUTOPILOT, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.EMERGENCY_STOP, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_CREW_INFO, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.ASSIGN_TASKS, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.MANAGE_SCHEDULES, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_SCHEDULES, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.INITIATE_EMERGENCY, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.CONDUCT_SAFETY_DRILLS, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_SAFETY_STATUS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.MANAGE_SAFETY_EQUIPMENT, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_FISH_FINDER, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.CONTROL_FISH_FINDER, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.LOG_CATCHES, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_CATCH_DATA, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.MANAGE_FISHING_SPOTS, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_SHARES, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_SYSTEM_STATUS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.SEND_BROADCASTS, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.DISTRESS_CALLS, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.STAND_WATCH, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.ASSIGN_WATCH, PermissionScope.VESSEL, AccessLevel.WRITE),
        ]
        
        self.role_permissions[CrewRole.FIRST_MATE] = RolePermissionSet(
            CrewRole.FIRST_MATE, first_mate_permissions,
            "Senior officer with operational and safety responsibilities"
        )
        
        # Mate permissions - Moderate access
        mate_permissions = [
            PermissionGrant(Permission.VIEW_NAVIGATION, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.CONTROL_AUTOPILOT, PermissionScope.VESSEL, AccessLevel.WRITE, 
                          conditions={'valid_hours': list(range(6, 22))}),  # Daylight hours only
            PermissionGrant(Permission.EMERGENCY_STOP, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_CREW_INFO, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_SCHEDULES, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.INITIATE_EMERGENCY, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_SAFETY_STATUS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_FISH_FINDER, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.CONTROL_FISH_FINDER, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.LOG_CATCHES, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_CATCH_DATA, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_SHARES, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_SYSTEM_STATUS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.DISTRESS_CALLS, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.STAND_WATCH, PermissionScope.VESSEL, AccessLevel.WRITE),
        ]
        
        self.role_permissions[CrewRole.MATE] = RolePermissionSet(
            CrewRole.MATE, mate_permissions,
            "Watch officer with limited operational authority"
        )
        
        # Deckhand permissions - Basic access
        deckhand_permissions = [
            PermissionGrant(Permission.VIEW_NAVIGATION, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.EMERGENCY_STOP, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_SCHEDULES, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.INITIATE_EMERGENCY, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_SAFETY_STATUS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_FISH_FINDER, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.LOG_CATCHES, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_CATCH_DATA, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_SHARES, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.DISTRESS_CALLS, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.STAND_WATCH, PermissionScope.VESSEL, AccessLevel.WRITE),
        ]
        
        self.role_permissions[CrewRole.DECKHAND] = RolePermissionSet(
            CrewRole.DECKHAND, deckhand_permissions,
            "Crew member with basic operational access"
        )
        
        # Engineer permissions - Technical focus
        engineer_permissions = [
            PermissionGrant(Permission.VIEW_NAVIGATION, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.EMERGENCY_STOP, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_SCHEDULES, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.INITIATE_EMERGENCY, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_SAFETY_STATUS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.MANAGE_SAFETY_EQUIPMENT, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_SYSTEM_STATUS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.MANAGE_SYSTEM_SETTINGS, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.ACCESS_LOGS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.BACKUP_DATA, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.DISTRESS_CALLS, PermissionScope.VESSEL, AccessLevel.WRITE),
        ]
        
        self.role_permissions[CrewRole.ENGINEER] = RolePermissionSet(
            CrewRole.ENGINEER, engineer_permissions,
            "Technical specialist with system access"
        )
        
        # Cook permissions - Limited access
        cook_permissions = [
            PermissionGrant(Permission.VIEW_NAVIGATION, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.EMERGENCY_STOP, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_SCHEDULES, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.INITIATE_EMERGENCY, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.VIEW_SAFETY_STATUS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.DISTRESS_CALLS, PermissionScope.VESSEL, AccessLevel.WRITE),
        ]
        
        self.role_permissions[CrewRole.COOK] = RolePermissionSet(
            CrewRole.COOK, cook_permissions,
            "Galley crew with basic safety access"
        )
        
        # Observer permissions - Read-only
        observer_permissions = [
            PermissionGrant(Permission.VIEW_NAVIGATION, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_SCHEDULES, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_SAFETY_STATUS, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_FISH_FINDER, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.VIEW_CATCH_DATA, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.INITIATE_EMERGENCY, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.DISTRESS_CALLS, PermissionScope.VESSEL, AccessLevel.WRITE),
        ]
        
        self.role_permissions[CrewRole.OBSERVER] = RolePermissionSet(
            CrewRole.OBSERVER, observer_permissions,
            "Scientific or regulatory observer with read access"
        )
        
        # Guest permissions - Minimal access
        guest_permissions = [
            PermissionGrant(Permission.VIEW_NAVIGATION, PermissionScope.VESSEL, AccessLevel.READ),
            PermissionGrant(Permission.INITIATE_EMERGENCY, PermissionScope.VESSEL, AccessLevel.WRITE),
            PermissionGrant(Permission.DISTRESS_CALLS, PermissionScope.VESSEL, AccessLevel.WRITE),
        ]
        
        self.role_permissions[CrewRole.GUEST] = RolePermissionSet(
            CrewRole.GUEST, guest_permissions,
            "Guest with emergency access only"
        )
    
    def has_permission(self, crew_role: CrewRole, permission: Permission, 
                      scope: PermissionScope = PermissionScope.VESSEL,
                      access_level: AccessLevel = AccessLevel.READ) -> bool:
        """Check if role has specific permission"""
        role_permissions = self.role_permissions.get(crew_role)
        if not role_permissions:
            return False
        
        return role_permissions.has_permission(permission, scope, access_level)
    
    def get_role_permissions(self, crew_role: CrewRole) -> Optional[RolePermissionSet]:
        """Get all permissions for a role"""
        return self.role_permissions.get(crew_role)
    
    def get_permissions_by_scope(self, crew_role: CrewRole, scope: PermissionScope) -> List[PermissionGrant]:
        """Get permissions for specific scope and role"""
        role_permissions = self.role_permissions.get(crew_role)
        if not role_permissions:
            return []
        
        return role_permissions.get_permissions_by_scope(scope)
    
    def grant_temporary_permission(self, crew_role: CrewRole, permission: Permission,
                                 scope: PermissionScope, access_level: AccessLevel,
                                 duration_hours: int = 24, granted_by: Optional[str] = None) -> bool:
        """Grant temporary permission to role"""
        if crew_role not in self.role_permissions:
            return False
        
        expires_at = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        
        temp_permission = PermissionGrant(
            permission=permission,
            scope=scope,
            access_level=access_level,
            expires_at=expires_at,
            granted_by=granted_by
        )
        
        self.role_permissions[crew_role].permissions.append(temp_permission)
        logger.info(f"Granted temporary {permission.value} to {crew_role.value} for {duration_hours} hours")
        
        return True
    
    def revoke_permission(self, crew_role: CrewRole, permission: Permission, 
                         scope: PermissionScope) -> bool:
        """Revoke specific permission from role"""
        if crew_role not in self.role_permissions:
            return False
        
        role_perms = self.role_permissions[crew_role]
        original_count = len(role_perms.permissions)
        
        # Remove matching permissions
        role_perms.permissions = [
            p for p in role_perms.permissions 
            if not (p.permission == permission and p.scope == scope)
        ]
        
        removed_count = original_count - len(role_perms.permissions)
        if removed_count > 0:
            logger.info(f"Revoked {permission.value} from {crew_role.value} ({removed_count} grants removed)")
            return True
        
        return False
    
    def create_permission_hierarchy(self) -> Dict[str, List[str]]:
        """Create permission hierarchy for UI display"""
        hierarchy = {
            'navigation': [
                Permission.VIEW_NAVIGATION.value,
                Permission.CONTROL_AUTOPILOT.value,
                Permission.SET_COURSE.value,
                Permission.OVERRIDE_AUTOPILOT.value,
                Permission.EMERGENCY_STOP.value
            ],
            'crew_management': [
                Permission.INVITE_CREW.value,
                Permission.MANAGE_CREW.value,
                Permission.VIEW_CREW_INFO.value,
                Permission.ASSIGN_TASKS.value,
                Permission.MANAGE_SCHEDULES.value,
                Permission.VIEW_SCHEDULES.value
            ],
            'safety': [
                Permission.INITIATE_EMERGENCY.value,
                Permission.CONDUCT_SAFETY_DRILLS.value,
                Permission.OVERRIDE_SAFETY_SYSTEMS.value,
                Permission.VIEW_SAFETY_STATUS.value,
                Permission.MANAGE_SAFETY_EQUIPMENT.value
            ],
            'fishing': [
                Permission.VIEW_FISH_FINDER.value,
                Permission.CONTROL_FISH_FINDER.value,
                Permission.LOG_CATCHES.value,
                Permission.VIEW_CATCH_DATA.value,
                Permission.MANAGE_FISHING_SPOTS.value
            ],
            'financial': [
                Permission.VIEW_SHARES.value,
                Permission.CALCULATE_SHARES.value,
                Permission.MANAGE_EXPENSES.value,
                Permission.VIEW_FINANCIAL_REPORTS.value
            ],
            'system': [
                Permission.VIEW_SYSTEM_STATUS.value,
                Permission.MANAGE_SYSTEM_SETTINGS.value,
                Permission.ACCESS_LOGS.value,
                Permission.BACKUP_DATA.value
            ],
            'communication': [
                Permission.SEND_BROADCASTS.value,
                Permission.MANAGE_COMMUNICATIONS.value,
                Permission.DISTRESS_CALLS.value
            ],
            'watch': [
                Permission.STAND_WATCH.value,
                Permission.ASSIGN_WATCH.value,
                Permission.OVERRIDE_WATCH.value
            ]
        }
        
        return hierarchy
    
    def validate_permission_request(self, crew_role: CrewRole, requested_permission: Permission,
                                  context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate permission request with detailed response"""
        context = context or {}
        
        has_perm = self.has_permission(crew_role, requested_permission)
        
        result = {
            'allowed': has_perm,
            'role': crew_role.value,
            'permission': requested_permission.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'context': context
        }
        
        if not has_perm:
            # Suggest required role for permission
            required_roles = []
            for role, role_perms in self.role_permissions.items():
                if role_perms.has_permission(requested_permission):
                    required_roles.append(role.value)
            
            result['required_roles'] = required_roles
            result['reason'] = f"Role {crew_role.value} does not have {requested_permission.value} permission"
        
        return result

def require_permission(permission: Permission, scope: PermissionScope = PermissionScope.VESSEL,
                      access_level: AccessLevel = AccessLevel.READ):
    """Decorator to require specific permission for function access"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract crew role from function arguments
            # This would typically come from authentication/session context
            crew_role = kwargs.get('crew_role')
            if not crew_role:
                raise PermissionError("No crew role provided")
            
            # Check permission
            permission_manager = PermissionManager()
            if not permission_manager.has_permission(crew_role, permission, scope, access_level):
                raise PermissionError(f"Role {crew_role.value} lacks required permission: {permission.value}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

async def main():
    """Example usage of permission system"""
    
    # Initialize permission manager
    perm_manager = PermissionManager()
    
    print("=== Role-Based Permissions System Demo ===")
    
    # Test permissions for different roles
    test_cases = [
        (CrewRole.CAPTAIN, Permission.OVERRIDE_AUTOPILOT, PermissionScope.VESSEL, AccessLevel.ADMIN),
        (CrewRole.FIRST_MATE, Permission.SET_COURSE, PermissionScope.VESSEL, AccessLevel.WRITE),
        (CrewRole.DECKHAND, Permission.CONTROL_AUTOPILOT, PermissionScope.VESSEL, AccessLevel.WRITE),
        (CrewRole.GUEST, Permission.VIEW_NAVIGATION, PermissionScope.VESSEL, AccessLevel.READ),
        (CrewRole.ENGINEER, Permission.MANAGE_SYSTEM_SETTINGS, PermissionScope.VESSEL, AccessLevel.WRITE),
    ]
    
    print("Permission Tests:")
    for role, permission, scope, access_level in test_cases:
        has_perm = perm_manager.has_permission(role, permission, scope, access_level)
        status = "✓ ALLOWED" if has_perm else "✗ DENIED"
        print(f"  {status}: {role.value} -> {permission.value} ({access_level.name})")
    
    # Get role permissions
    print(f"\nCaptain Permissions:")
    captain_perms = perm_manager.get_role_permissions(CrewRole.CAPTAIN)
    if captain_perms:
        navigation_perms = captain_perms.get_permissions_by_scope(PermissionScope.VESSEL)
        print(f"  Vessel permissions: {len(navigation_perms)}")
        
        for perm in navigation_perms[:5]:  # Show first 5
            print(f"    • {perm.permission.value} ({perm.access_level.name})")
    
    # Test temporary permission grant
    print(f"\nGranting temporary autopilot control to deckhand...")
    success = perm_manager.grant_temporary_permission(
        CrewRole.DECKHAND,
        Permission.CONTROL_AUTOPILOT,
        PermissionScope.VESSEL,
        AccessLevel.WRITE,
        duration_hours=2
    )
    
    if success:
        has_temp_perm = perm_manager.has_permission(
            CrewRole.DECKHAND, Permission.CONTROL_AUTOPILOT, 
            PermissionScope.VESSEL, AccessLevel.WRITE
        )
        print(f"  Temporary permission granted: {has_temp_perm}")
    
    # Validate permission request
    validation = perm_manager.validate_permission_request(
        CrewRole.COOK, Permission.MANAGE_CREW
    )
    
    print(f"\nPermission Validation:")
    print(f"  Role: {validation['role']}")
    print(f"  Permission: {validation['permission']}")
    print(f"  Allowed: {validation['allowed']}")
    if not validation['allowed']:
        print(f"  Required roles: {validation.get('required_roles', [])}")
        print(f"  Reason: {validation.get('reason', 'Unknown')}")
    
    # Show permission hierarchy
    hierarchy = perm_manager.create_permission_hierarchy()
    print(f"\nPermission Categories:")
    for category, permissions in hierarchy.items():
        print(f"  {category.title()}: {len(permissions)} permissions")

if __name__ == "__main__":
    asyncio.run(main())