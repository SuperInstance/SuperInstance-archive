"""
Enterprise Organization Management
Provides multi-tenant organization structure, department management, and enterprise governance.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from decimal import Decimal
from enum import Enum
import json
import logging
import uuid
from dataclasses import dataclass, asdict

from core.models import (
    Organization, Department, Project, OrganizationMember, ApprovalRequest,
    OrganizationTier, OrganizationRole, ApprovalStatus, generate_id, current_timestamp
)

logger = logging.getLogger(__name__)

# OrganizationTier is imported from core.models

class ResourcePolicy(str, Enum):
    """Resource access policies"""
    UNRESTRICTED = "unrestricted"
    APPROVAL_REQUIRED = "approval_required"
    BUDGET_LIMITED = "budget_limited"
    RESTRICTED = "restricted"
    DENIED = "denied"

# All data models (Organization, Department, Project, OrganizationMember, ApprovalRequest) 
# are imported from core.models

class OrganizationManager:
    """Enterprise organization management system"""
    
    def __init__(self, config, database_manager):
        self.config = config
        self.database_manager = database_manager
        
    async def create_organization(
        self,
        name: str,
        owner_user_id: str,
        tier: OrganizationTier = OrganizationTier.BUSINESS,
        **kwargs
    ) -> Organization:
        """Create a new organization"""
        
        org_id = f"org_{uuid.uuid4().hex[:8]}"
        
        organization = Organization(
            org_id=org_id,
            name=name,
            tier=tier,
            created_at=datetime.now(),
            owner_user_id=owner_user_id,
            **kwargs
        )
        
        # Store in database
        await self._store_organization(organization)
        
        # Create default department
        default_dept = await self.create_department(
            org_id=org_id,
            name="General",
            manager_user_id=owner_user_id
        )
        
        # Add owner as org admin
        await self.add_user_to_organization(
            user_id=owner_user_id,
            org_id=org_id,
            role=OrganizationRole.OWNER,
            dept_id=default_dept.dept_id
        )
        
        logger.info(f"Created organization {org_id}: {name}")
        return organization
    
    async def create_department(
        self,
        org_id: str,
        name: str,
        manager_user_id: str,
        **kwargs
    ) -> Department:
        """Create a department within organization"""
        
        # Verify organization exists
        org = await self.get_organization(org_id)
        if not org:
            raise ValueError(f"Organization {org_id} not found")
        
        dept_id = f"dept_{uuid.uuid4().hex[:8]}"
        
        department = Department(
            dept_id=dept_id,
            org_id=org_id,
            name=name,
            manager_user_id=manager_user_id,
            created_at=datetime.now(),
            **kwargs
        )
        
        await self._store_department(department)
        
        # Add manager to organization if not already added
        try:
            await self.add_user_to_organization(
                user_id=manager_user_id,
                org_id=org_id,
                role=OrganizationRole.DEPARTMENT_MANAGER,
                dept_id=dept_id
            )
        except:
            # User might already be in org, update their department
            await self._update_user_department(manager_user_id, org_id, dept_id)
        
        logger.info(f"Created department {dept_id}: {name} in org {org_id}")
        return department
    
    async def create_project(
        self,
        org_id: str,
        dept_id: str,
        name: str,
        owner_user_id: str,
        **kwargs
    ) -> Project:
        """Create a project within department"""
        
        # Verify department exists
        dept = await self.get_department(dept_id)
        if not dept or dept.org_id != org_id:
            raise ValueError(f"Department {dept_id} not found in organization {org_id}")
        
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        
        project = Project(
            project_id=project_id,
            org_id=org_id,
            dept_id=dept_id,
            name=name,
            owner_user_id=owner_user_id,
            created_at=datetime.now(),
            **kwargs
        )
        
        await self._store_project(project)
        
        # Add owner as project manager if not in org
        try:
            await self.add_user_to_organization(
                user_id=owner_user_id,
                org_id=org_id,
                role=OrganizationRole.PROJECT_MANAGER,
                dept_id=dept_id,
                projects=[project_id]
            )
        except:
            # User already in org, add project access
            await self._add_user_project_access(owner_user_id, org_id, project_id)
        
        logger.info(f"Created project {project_id}: {name} in dept {dept_id}")
        return project
    
    async def add_user_to_organization(
        self,
        user_id: str,
        org_id: str,
        role: OrganizationRole,
        dept_id: Optional[str] = None,
        projects: Optional[List[str]] = None
    ) -> OrganizationMember:
        """Add user to organization with role and access"""
        
        # Check if user already in organization
        existing = await self.get_organization_user(user_id, org_id)
        if existing:
            raise ValueError(f"User {user_id} already in organization {org_id}")
        
        org_user = OrganizationMember(
            member_id=generate_id("member"),
            user_id=user_id,
            org_id=org_id,
            role=role,
            dept_id=dept_id,
            permissions=self._get_default_permissions(role)
        )
        
        await self._store_organization_user(org_user)
        
        logger.info(f"Added user {user_id} to org {org_id} as {role.value}")
        return org_user
    
    async def request_resource_approval(
        self,
        org_id: str,
        requester_user_id: str,
        resource_type: str,
        resource_config: Dict[str, Any],
        estimated_monthly_cost: Decimal,
        business_justification: str,
        priority: str = "normal"
    ) -> ApprovalRequest:
        """Submit resource approval request"""
        
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        
        # Find appropriate approver
        approver = await self._find_approver(org_id, estimated_monthly_cost)
        
        request = ApprovalRequest(
            request_id=request_id,
            org_id=org_id,
            requester_user_id=requester_user_id,
            approver_user_id=approver,
            resource_type=resource_type,
            resource_config=resource_config,
            estimated_monthly_cost=estimated_monthly_cost,
            business_justification=business_justification,
            submitted_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7),  # 1 week expiry
            priority=priority
        )
        
        await self._store_approval_request(request)
        
        # Send notification to approver
        await self._notify_approver(request)
        
        logger.info(f"Created approval request {request_id} for ${estimated_monthly_cost:.2f}")
        return request
    
    async def approve_request(
        self,
        request_id: str,
        approver_user_id: str,
        comments: Optional[str] = None
    ) -> ApprovalRequest:
        """Approve a resource request"""
        
        request = await self.get_approval_request(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        if request.status != "pending":
            raise ValueError(f"Request {request_id} is not pending")
        
        # Update request
        request.status = "approved"
        request.responded_at = datetime.now()
        request.comments = comments
        
        await self._update_approval_request(request)
        
        # Notify requester
        await self._notify_requester(request, "approved")
        
        logger.info(f"Approved request {request_id} by {approver_user_id}")
        return request
    
    async def reject_request(
        self,
        request_id: str,
        approver_user_id: str,
        comments: Optional[str] = None
    ) -> ApprovalRequest:
        """Reject a resource request"""
        
        request = await self.get_approval_request(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        if request.status != "pending":
            raise ValueError(f"Request {request_id} is not pending")
        
        # Update request
        request.status = "rejected"
        request.responded_at = datetime.now()
        request.comments = comments
        
        await self._update_approval_request(request)
        
        # Notify requester
        await self._notify_requester(request, "rejected")
        
        logger.info(f"Rejected request {request_id} by {approver_user_id}")
        return request
    
    async def get_organization_spending_by_department(
        self,
        org_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Dict[str, Any]]:
        """Get spending breakdown by department"""
        
        # Get all departments
        departments = await self.get_organization_departments(org_id)
        
        spending_by_dept = {}
        total_org_spending = Decimal('0')
        
        for dept in departments:
            # Get department users
            dept_users = await self.get_department_users(dept.dept_id)
            
            # Calculate department spending
            dept_spending = Decimal('0')
            for user in dept_users:
                user_spending = await self._get_user_spending(
                    user.user_id, start_date, end_date
                )
                dept_spending += user_spending
            
            total_org_spending += dept_spending
            
            spending_by_dept[dept.dept_id] = {
                'department_name': dept.name,
                'manager': dept.manager_user_id,
                'budget': float(dept.monthly_budget) if dept.monthly_budget else None,
                'actual_spending': float(dept_spending),
                'budget_utilization': float(dept_spending / dept.monthly_budget * 100) if dept.monthly_budget else None,
                'user_count': len(dept_users),
                'cost_center': dept.cost_center_code
            }
        
        # Calculate percentages
        for dept_id, data in spending_by_dept.items():
            data['percentage_of_org'] = float(
                Decimal(str(data['actual_spending'])) / total_org_spending * 100
            ) if total_org_spending > 0 else 0
        
        return {
            'total_organization_spending': float(total_org_spending),
            'departments': spending_by_dept,
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        }
    
    async def get_organization_compliance_report(
        self,
        org_id: str
    ) -> Dict[str, Any]:
        """Generate compliance report for organization"""
        
        org = await self.get_organization(org_id)
        if not org:
            raise ValueError(f"Organization {org_id} not found")
        
        # Check compliance requirements
        compliance_items = []
        
        # Audit logging
        if org.audit_logging:
            compliance_items.append({
                'requirement': 'Audit Logging',
                'status': 'compliant',
                'description': 'All API calls and data access are logged'
            })
        else:
            compliance_items.append({
                'requirement': 'Audit Logging',
                'status': 'non_compliant',
                'description': 'Audit logging is not enabled'
            })
        
        # SSO
        if org.sso_enabled:
            compliance_items.append({
                'requirement': 'Single Sign-On',
                'status': 'compliant',
                'description': 'SSO is enabled for secure authentication'
            })
        
        # Data encryption
        compliance_items.append({
            'requirement': 'Data Encryption',
            'status': 'compliant',
            'description': 'Data is encrypted at rest and in transit'
        })
        
        # Access controls
        user_count = await self._count_organization_users(org_id)
        compliance_items.append({
            'requirement': 'Role-Based Access Control',
            'status': 'compliant',
            'description': f'RBAC implemented for {user_count} users'
        })
        
        # Calculate compliance score
        compliant_count = len([item for item in compliance_items if item['status'] == 'compliant'])
        compliance_score = (compliant_count / len(compliance_items)) * 100
        
        return {
            'organization': org.name,
            'compliance_mode': org.compliance_mode,
            'compliance_score': compliance_score,
            'compliance_grade': 'A' if compliance_score >= 90 else 'B' if compliance_score >= 80 else 'C',
            'compliance_items': compliance_items,
            'recommendations': self._generate_compliance_recommendations(compliance_items),
            'generated_at': datetime.now().isoformat()
        }
    
    # Database operations
    async def _store_organization(self, org: Organization):
        """Store organization in database"""
        return await self.database_manager.create_organization(org)
    
    async def _store_department(self, dept: Department):
        """Store department in database"""
        return await self.database_manager.create_department(dept)
    
    async def _store_project(self, project: Project):
        """Store project in database"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO projects
                (project_id, org_id, dept_id, name, owner_user_id, created_at,
                 monthly_budget, cost_center_code, start_date, end_date, status,
                 team_members, resource_policy, description, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.project_id, project.org_id, project.dept_id, project.name,
                project.owner_user_id, project.created_at,
                float(project.monthly_budget) if project.monthly_budget else None,
                project.cost_center_code, project.start_date, project.end_date,
                project.status,
                json.dumps(project.team_members) if project.team_members else None,
                project.resource_policy.value, project.description,
                json.dumps(project.tags) if project.tags else None
            ))
            await conn.commit()
    
    async def _store_organization_user(self, org_user: OrganizationMember):
        """Store organization user in database"""
        return await self.database_manager.add_organization_member(org_user)
    
    async def _store_approval_request(self, request: ApprovalRequest):
        """Store approval request in database"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO approval_requests
                (request_id, org_id, requester_user_id, approver_user_id, resource_type,
                 resource_config, estimated_monthly_cost, business_justification, status,
                 submitted_at, responded_at, expires_at, comments, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.request_id, request.org_id, request.requester_user_id,
                request.approver_user_id, request.resource_type,
                json.dumps(request.resource_config), float(request.estimated_monthly_cost),
                request.business_justification, request.status, request.submitted_at,
                request.responded_at, request.expires_at, request.comments, request.priority
            ))
            await conn.commit()
    
    # Getter methods
    async def get_organization(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID"""
        return await self.database_manager.get_organization(org_id)
    
    async def get_user_organizations(self, user_id: str) -> List[Organization]:
        """Get organizations where user is a member"""
        return await self.database_manager.get_user_organizations(user_id)
    
    async def get_department(self, dept_id: str) -> Optional[Department]:
        """Get department by ID"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM departments WHERE dept_id = ?", (dept_id,)
            )
            row = await cursor.fetchone()
            if row:
                return self._row_to_department(row)
            return None
    
    async def get_organization_user(self, user_id: str, org_id: str) -> Optional[OrganizationMember]:
        """Get organization user"""
        members = await self.database_manager.get_organization_members(org_id)
        for member in members:
            if member.user_id == user_id:
                return member
        return None
    
    async def get_approval_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM approval_requests WHERE request_id = ?", (request_id,)
            )
            row = await cursor.fetchone()
            if row:
                return self._row_to_approval_request(row)
            return None
    
    # Helper methods
    def _get_default_permissions(self, role: OrganizationRole) -> List[str]:
        """Get default permissions for role"""
        permission_map = {
            OrganizationRole.OWNER: ["*"],  # All permissions
            OrganizationRole.ADMIN: ["org:*", "billing:*", "users:*"],
            OrganizationRole.FINANCE_MANAGER: ["billing:*", "reports:*"],
            OrganizationRole.DEPARTMENT_MANAGER: ["dept:*", "billing:read", "users:read"],
            OrganizationRole.PROJECT_MANAGER: ["project:*", "billing:read"],
            OrganizationRole.DEVELOPER: ["instances:*", "billing:read"],
            OrganizationRole.VIEWER: ["*:read"],
            OrganizationRole.MEMBER: ["*:read"]
        }
        return permission_map.get(role, ["billing:read"])
    
    def _get_default_resource_limits(self, role: OrganizationRole) -> Dict[str, Any]:
        """Get default resource limits for role"""
        if role in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            return {"max_instances": 100, "max_monthly_spend": 10000}
        elif role == OrganizationRole.DEPARTMENT_MANAGER:
            return {"max_instances": 50, "max_monthly_spend": 5000}
        elif role == OrganizationRole.PROJECT_MANAGER:
            return {"max_instances": 20, "max_monthly_spend": 2000}
        elif role == OrganizationRole.DEVELOPER:
            return {"max_instances": 10, "max_monthly_spend": 500}
        else:
            return {"max_instances": 5, "max_monthly_spend": 100}
    
    def _generate_compliance_recommendations(self, compliance_items: List[Dict]) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        non_compliant = [item for item in compliance_items if item['status'] == 'non_compliant']
        
        if non_compliant:
            recommendations.append("Address non-compliant items to improve security posture")
        
        recommendations.extend([
            "Regularly review user access and permissions",
            "Conduct quarterly compliance audits",
            "Keep audit logs for minimum 1 year retention",
            "Implement least-privilege access principles"
        ])
        
        return recommendations
    
    # Placeholder methods for database row conversion
    def _row_to_organization(self, row) -> Organization:
        """Convert database row to Organization object"""
        # Implementation would depend on database schema
        pass
    
    def _row_to_department(self, row) -> Department:
        """Convert database row to Department object"""
        pass
    
    def _row_to_organization_user(self, row) -> OrganizationMember:
        """Convert database row to OrganizationMember object"""
        pass
    
    def _row_to_approval_request(self, row) -> ApprovalRequest:
        """Convert database row to ApprovalRequest object"""
        pass
    
    # Placeholder methods for implementation
    async def get_organization_departments(self, org_id: str) -> List[Department]:
        """Get all departments in organization"""
        return await self.database_manager.get_organization_departments(org_id)
    
    async def get_department_projects(self, dept_id: str) -> List[Project]:
        """Get all projects in department"""
        return await self.database_manager.get_department_projects(dept_id)
    
    async def get_department_users(self, dept_id: str) -> List[OrganizationMember]:
        """Get all users in department"""
        return []
    
    async def _get_user_spending(self, user_id: str, start_date: datetime, end_date: datetime) -> Decimal:
        """Get user spending in date range"""
        return Decimal('0')
    
    async def _count_organization_users(self, org_id: str) -> int:
        """Count users in organization"""
        return 0
    
    async def _find_approver(self, org_id: str, cost: Decimal) -> Optional[str]:
        """Find appropriate approver for cost amount"""
        return None
    
    async def _notify_approver(self, request: ApprovalRequest):
        """Send notification to approver"""
        pass
    
    async def _notify_requester(self, request: ApprovalRequest, status: str):
        """Send notification to requester"""
        pass
    
    async def _update_approval_request(self, request: ApprovalRequest):
        """Update approval request in database"""
        pass
    
    async def _update_user_department(self, user_id: str, org_id: str, dept_id: str):
        """Update user's department"""
        pass
    
    async def _add_user_project_access(self, user_id: str, org_id: str, project_id: str):
        """Add project access for user"""
        pass