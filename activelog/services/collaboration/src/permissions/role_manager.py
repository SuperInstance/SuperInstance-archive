"""
Role-based access control and management
"""

import logging
from typing import Dict, Set, List, Any, Optional
from enum import Enum

from core.database import WorkspaceRole, DocumentPermission

logger = logging.getLogger(__name__)

class SystemRole(str, Enum):
    """System-wide roles"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class RoleManager:
    def __init__(self):
        # Define role hierarchy (higher roles inherit lower role permissions)
        self.role_hierarchy = {
            WorkspaceRole.OWNER: 4,
            WorkspaceRole.ADMIN: 3,
            WorkspaceRole.MEMBER: 2,
            WorkspaceRole.VIEWER: 1
        }
        
        # Define default permissions for each workspace role
        self.default_role_permissions = {
            WorkspaceRole.OWNER: {
                "workspace": {
                    "read", "write", "delete", "manage_members", "manage_settings", 
                    "manage_permissions", "manage_integrations", "view_analytics"
                },
                "document": {
                    DocumentPermission.READ, DocumentPermission.WRITE, 
                    DocumentPermission.COMMENT, DocumentPermission.ADMIN
                },
                "annotation": {"read", "write", "delete", "resolve", "moderate"},
                "comment": {"read", "write", "delete", "moderate"},
                "version": {"read", "create", "restore", "delete"},
                "activity": {"read", "export"}
            },
            WorkspaceRole.ADMIN: {
                "workspace": {
                    "read", "write", "manage_members", "manage_settings", 
                    "manage_permissions", "view_analytics"
                },
                "document": {
                    DocumentPermission.READ, DocumentPermission.WRITE, 
                    DocumentPermission.COMMENT, DocumentPermission.ADMIN
                },
                "annotation": {"read", "write", "delete", "resolve", "moderate"},
                "comment": {"read", "write", "delete", "moderate"},
                "version": {"read", "create", "restore"},
                "activity": {"read", "export"}
            },
            WorkspaceRole.MEMBER: {
                "workspace": {"read"},
                "document": {
                    DocumentPermission.READ, DocumentPermission.WRITE, DocumentPermission.COMMENT
                },
                "annotation": {"read", "write", "delete_own", "resolve"},
                "comment": {"read", "write", "delete_own"},
                "version": {"read", "create"},
                "activity": {"read"}
            },
            WorkspaceRole.VIEWER: {
                "workspace": {"read"},
                "document": {DocumentPermission.READ, DocumentPermission.COMMENT},
                "annotation": {"read"},
                "comment": {"read", "write"},
                "version": {"read"},
                "activity": {"read"}
            }
        }
        
        # Define system role permissions
        self.system_role_permissions = {
            SystemRole.SUPER_ADMIN: {
                "system": {"manage_users", "manage_workspaces", "manage_settings", "view_logs", "backup_restore"},
                "workspace": {"all"},  # All workspace permissions
                "document": {"all"},   # All document permissions
            },
            SystemRole.ADMIN: {
                "system": {"manage_users", "view_logs"},
                "workspace": {"read", "manage_members"},
                "document": {DocumentPermission.READ, DocumentPermission.WRITE, DocumentPermission.COMMENT}
            },
            SystemRole.USER: {
                "workspace": {"read", "create"},
                "document": {DocumentPermission.READ, DocumentPermission.WRITE, DocumentPermission.COMMENT}
            },
            SystemRole.GUEST: {
                "workspace": {"read"},
                "document": {DocumentPermission.READ, DocumentPermission.COMMENT}
            }
        }
        
    async def initialize(self):
        """Initialize role manager"""
        logger.info("Initializing role manager")
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up role manager")
        
    def get_role_permissions(self, role: WorkspaceRole, resource_type: str = "document") -> Set[str]:
        """Get permissions for a workspace role and resource type"""
        try:
            role_perms = self.default_role_permissions.get(role, {})
            return role_perms.get(resource_type, set())
            
        except Exception as e:
            logger.error(f"Failed to get role permissions: {e}")
            return set()
            
    def get_system_role_permissions(self, role: SystemRole, resource_type: str) -> Set[str]:
        """Get permissions for a system role and resource type"""
        try:
            role_perms = self.system_role_permissions.get(role, {})
            permissions = role_perms.get(resource_type, set())
            
            # Handle "all" permission
            if "all" in permissions:
                if resource_type == "document":
                    return {perm.value for perm in DocumentPermission}
                elif resource_type == "workspace":
                    return {"read", "write", "delete", "manage_members", "manage_settings", 
                           "manage_permissions", "manage_integrations", "view_analytics"}
                
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get system role permissions: {e}")
            return set()
            
    def can_role_perform_action(self, role: WorkspaceRole, resource_type: str, action: str) -> bool:
        """Check if a role can perform a specific action on a resource type"""
        try:
            permissions = self.get_role_permissions(role, resource_type)
            
            # Handle ownership-based permissions
            if action.endswith("_own"):
                base_action = action.replace("_own", "")
                return base_action in permissions or action in permissions
                
            return action in permissions
            
        except Exception as e:
            logger.error(f"Failed to check role action: {e}")
            return False
            
    def can_system_role_perform_action(self, role: SystemRole, resource_type: str, action: str) -> bool:
        """Check if a system role can perform a specific action"""
        try:
            permissions = self.get_system_role_permissions(role, resource_type)
            return action in permissions or "all" in permissions
            
        except Exception as e:
            logger.error(f"Failed to check system role action: {e}")
            return False
            
    def get_role_hierarchy_level(self, role: WorkspaceRole) -> int:
        """Get hierarchy level for a workspace role (higher number = more permissions)"""
        return self.role_hierarchy.get(role, 0)
        
    def is_role_higher_than(self, role1: WorkspaceRole, role2: WorkspaceRole) -> bool:
        """Check if role1 has higher privileges than role2"""
        return self.get_role_hierarchy_level(role1) > self.get_role_hierarchy_level(role2)
        
    def can_role_manage_role(self, manager_role: WorkspaceRole, target_role: WorkspaceRole) -> bool:
        """Check if manager role can manage (assign/remove) target role"""
        try:
            # Only owners can manage other owners
            if target_role == WorkspaceRole.OWNER:
                return manager_role == WorkspaceRole.OWNER
                
            # Admins can manage members and viewers
            if manager_role == WorkspaceRole.ADMIN:
                return target_role in [WorkspaceRole.MEMBER, WorkspaceRole.VIEWER]
                
            # Owners can manage all roles
            if manager_role == WorkspaceRole.OWNER:
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to check role management: {e}")
            return False
            
    def get_assignable_roles(self, assigner_role: WorkspaceRole) -> List[WorkspaceRole]:
        """Get list of roles that can be assigned by the assigner role"""
        try:
            if assigner_role == WorkspaceRole.OWNER:
                return [WorkspaceRole.ADMIN, WorkspaceRole.MEMBER, WorkspaceRole.VIEWER]
            elif assigner_role == WorkspaceRole.ADMIN:
                return [WorkspaceRole.MEMBER, WorkspaceRole.VIEWER]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get assignable roles: {e}")
            return []
            
    def get_effective_permissions(self, workspace_role: Optional[WorkspaceRole], 
                                system_role: Optional[SystemRole],
                                resource_type: str,
                                is_owner: bool = False) -> Set[str]:
        """Get effective permissions combining workspace role, system role, and ownership"""
        try:
            permissions = set()
            
            # Add workspace role permissions
            if workspace_role:
                permissions.update(self.get_role_permissions(workspace_role, resource_type))
            
            # Add system role permissions
            if system_role:
                permissions.update(self.get_system_role_permissions(system_role, resource_type))
            
            # Add owner permissions
            if is_owner and resource_type == "document":
                permissions.update({perm.value for perm in DocumentPermission})
            elif is_owner and resource_type == "workspace":
                permissions.update({"read", "write", "delete", "manage_members", "manage_settings", 
                                   "manage_permissions", "manage_integrations", "view_analytics"})
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get effective permissions: {e}")
            return set()
            
    def validate_role_transition(self, current_role: WorkspaceRole, 
                                new_role: WorkspaceRole,
                                changer_role: WorkspaceRole) -> bool:
        """Validate if a role transition is allowed"""
        try:
            # Check if changer can manage both roles
            can_manage_current = self.can_role_manage_role(changer_role, current_role)
            can_manage_new = self.can_role_manage_role(changer_role, new_role)
            
            return can_manage_current and can_manage_new
            
        except Exception as e:
            logger.error(f"Failed to validate role transition: {e}")
            return False
            
    def get_role_description(self, role: WorkspaceRole) -> Dict[str, Any]:
        """Get detailed description of a workspace role"""
        descriptions = {
            WorkspaceRole.OWNER: {
                "name": "Owner",
                "description": "Full control over the workspace including deletion and ownership transfer",
                "key_permissions": [
                    "Delete workspace",
                    "Transfer ownership", 
                    "Manage all members and roles",
                    "Configure workspace settings",
                    "Full document access"
                ],
                "limitations": []
            },
            WorkspaceRole.ADMIN: {
                "name": "Admin", 
                "description": "Manage workspace members, settings, and have full document access",
                "key_permissions": [
                    "Manage members (except owners)",
                    "Configure workspace settings",
                    "Manage document permissions",
                    "Full document access",
                    "View analytics"
                ],
                "limitations": [
                    "Cannot delete workspace",
                    "Cannot manage other admins or owners",
                    "Cannot transfer ownership"
                ]
            },
            WorkspaceRole.MEMBER: {
                "name": "Member",
                "description": "Standard workspace member with document collaboration access",
                "key_permissions": [
                    "Read, write, and comment on documents",
                    "Create annotations and comments", 
                    "Create document versions",
                    "View workspace activity"
                ],
                "limitations": [
                    "Cannot manage workspace settings",
                    "Cannot manage other members",
                    "Cannot manage permissions"
                ]
            },
            WorkspaceRole.VIEWER: {
                "name": "Viewer",
                "description": "Read-only access with ability to comment and view discussions",
                "key_permissions": [
                    "Read documents",
                    "Add comments to discussions",
                    "View annotations",
                    "View workspace activity"
                ],
                "limitations": [
                    "Cannot edit documents",
                    "Cannot create annotations",
                    "Cannot create document versions",
                    "No management permissions"
                ]
            }
        }
        
        return descriptions.get(role, {"name": "Unknown", "description": "", "key_permissions": [], "limitations": []})
        
    def get_permission_matrix(self) -> Dict[str, Dict[str, Dict[str, bool]]]:
        """Get complete permission matrix for all roles and resource types"""
        try:
            matrix = {}
            
            for role in WorkspaceRole:
                matrix[role.value] = {}
                
                for resource_type in ["workspace", "document", "annotation", "comment", "version", "activity"]:
                    matrix[role.value][resource_type] = {}
                    permissions = self.get_role_permissions(role, resource_type)
                    
                    # Common actions for each resource type
                    common_actions = {
                        "workspace": ["read", "write", "delete", "manage_members", "manage_settings", "manage_permissions"],
                        "document": ["read", "write", "comment", "admin"],
                        "annotation": ["read", "write", "delete", "resolve", "moderate"],
                        "comment": ["read", "write", "delete", "moderate"],
                        "version": ["read", "create", "restore", "delete"],
                        "activity": ["read", "export"]
                    }
                    
                    for action in common_actions.get(resource_type, []):
                        matrix[role.value][resource_type][action] = action in permissions or f"{action}_own" in permissions
                        
            return matrix
            
        except Exception as e:
            logger.error(f"Failed to get permission matrix: {e}")
            return {}
            
    def suggest_role_for_permissions(self, required_permissions: Set[str], 
                                   resource_type: str = "document") -> Optional[WorkspaceRole]:
        """Suggest the minimal role that provides the required permissions"""
        try:
            # Check each role starting from lowest privilege
            roles_by_privilege = sorted(WorkspaceRole, key=lambda r: self.get_role_hierarchy_level(r))
            
            for role in roles_by_privilege:
                role_permissions = self.get_role_permissions(role, resource_type)
                if required_permissions.issubset(role_permissions):
                    return role
                    
            return None
            
        except Exception as e:
            logger.error(f"Failed to suggest role: {e}")
            return None
            
    def get_role_conflicts(self, user_roles: Dict[str, WorkspaceRole]) -> List[Dict[str, Any]]:
        """Identify potential conflicts in user's roles across workspaces"""
        try:
            conflicts = []
            
            # Check for inconsistent role assignments
            role_levels = [self.get_role_hierarchy_level(role) for role in user_roles.values()]
            
            if len(set(role_levels)) > 2:  # More than 2 different privilege levels
                conflicts.append({
                    "type": "inconsistent_privileges",
                    "description": "User has significantly different privilege levels across workspaces",
                    "workspaces": user_roles,
                    "severity": "medium"
                })
            
            # Check for too many high-privilege roles
            high_privilege_roles = sum(1 for role in user_roles.values() 
                                     if role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN])
            
            if high_privilege_roles > len(user_roles) * 0.7:  # More than 70% high privilege
                conflicts.append({
                    "type": "excessive_privileges", 
                    "description": "User has admin/owner roles in most workspaces",
                    "high_privilege_count": high_privilege_roles,
                    "total_workspaces": len(user_roles),
                    "severity": "high"
                })
                
            return conflicts
            
        except Exception as e:
            logger.error(f"Failed to get role conflicts: {e}")
            return []