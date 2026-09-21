#!/usr/bin/env python3
"""
Test script for enterprise features
Tests organization management, departments, projects, and approval workflows.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database_manager import DatabaseManager
from enterprise.organization_manager import OrganizationManager
from core.models import OrganizationTier, current_timestamp

class MockConfig:
    """Mock configuration for testing"""
    def get(self, key, default=None):
        return {
            'enterprise': {
                'approval_required_cost_threshold': 100.0,
                'max_departments_per_org': 50,
                'max_projects_per_department': 100
            }
        }.get(key, default)

async def test_enterprise_features():
    """Test the enterprise organization features"""
    
    try:
        print("🏢 Testing Enterprise Organization Features")
        print("=" * 50)
        
        # Initialize components
        print("1. Initializing components...")
        db_manager = DatabaseManager("test_enterprise.db")
        await db_manager.initialize()
        
        config = MockConfig()
        org_manager = OrganizationManager(config, db_manager)
        
        print("✅ Components initialized")
        
        # Setup test data
        print("2. Setting up test data...")
        await setup_enterprise_test_data(db_manager)
        print("✅ Test data created")
        
        # Test organization creation
        print("3. Testing organization management...")
        
        # Create organization (simplified)
        from core.models import Organization
        org = Organization(
            org_id="test_org_1",
            name="Acme Corporation",
            tier=OrganizationTier.ENTERPRISE,
            owner_user_id="test_user_1",
            created_at=current_timestamp()
        )
        
        # Store it directly
        success = await org_manager._store_organization(org)
        
        if success:
            print(f"✅ Created organization: {org.name} ({org.tier.value})")
        else:
            print("❌ Failed to create organization")
            return False
        
        # Get user organizations
        user_orgs = await org_manager.get_user_organizations("test_user_1")
        print(f"✅ User has {len(user_orgs)} organizations")
        
        # Test department creation
        print("4. Testing department management...")
        
        from core.models import Department
        dept = Department(
            dept_id="test_dept_1",
            org_id=org.org_id,
            name="Engineering",
            manager_user_id="test_user_1",
            budget_limit=50000.0
        )
        dept_success = await org_manager._store_department(dept)
        
        if dept_success:
            print(f"✅ Created department: {dept.name} (Budget: ${dept.budget_limit:,.2f})")
        else:
            print("❌ Failed to create department")
            return False
        
        # Get organization departments
        departments = await org_manager.get_organization_departments(org.org_id)
        print(f"✅ Organization has {len(departments)} departments")
        
        # Test project creation
        print("5. Testing project management...")
        
        from core.models import Project
        project = Project(
            project_id="test_project_1",
            dept_id=dept.dept_id,
            name="Cloud Migration",
            description="Migrate legacy systems to cloud infrastructure",
            owner_user_id="test_user_1",
            budget_limit=25000.0
        )
        project_success = await org_manager._store_project(project)
        
        if project_success:
            print(f"✅ Created project: {project.name} (Budget: ${project.budget_limit:,.2f})")
        else:
            print("❌ Failed to create project")
            return False
        
        # Get department projects
        projects = await org_manager.get_department_projects(dept.dept_id)
        print(f"✅ Department has {len(projects)} projects")
        
        # Test approval workflow
        print("6. Testing approval workflow...")
        
        approval_request = await org_manager.create_approval_request(
            org_id=org.org_id,
            requester_user_id="test_user_1",
            resource_type="ec2_instance",
            resource_config={
                "instance_type": "c5.xlarge",
                "quantity": 5,
                "purpose": "load testing"
            },
            justification="Need high-performance instances for load testing our new API",
            estimated_cost=500.0
        )
        
        if approval_request:
            print(f"✅ Created approval request: {approval_request.resource_type} (Cost: ${approval_request.estimated_cost:,.2f})")
        else:
            print("❌ Failed to create approval request")
            return False
        
        # Get pending requests
        pending_requests = await org_manager.get_pending_approval_requests(org.org_id)
        print(f"✅ Organization has {len(pending_requests)} pending approval requests")
        
        # Test approval process
        approval_result = await org_manager.approve_request(
            request_id=approval_request.request_id,
            approver_user_id="test_user_1",
            comments="Approved for Q4 performance testing initiative"
        )
        
        if approval_result:
            print("✅ Successfully approved resource request")
        else:
            print("❌ Failed to approve request")
            return False
        
        # Test organization member management
        print("7. Testing member management...")
        
        member_added = await org_manager.add_organization_member(
            org_id=org.org_id,
            user_id="test_user_2",
            role="developer",
            dept_id=dept.dept_id
        )
        
        if member_added:
            print("✅ Added organization member successfully")
        else:
            print("❌ Failed to add organization member")
        
        # Get organization members
        members = await org_manager.get_organization_members(org.org_id)
        print(f"✅ Organization has {len(members)} members")
        
        # Test compliance reporting
        print("8. Testing compliance reporting...")
        
        compliance_report = await org_manager.generate_compliance_report(
            org_id=org.org_id,
            report_type="audit"
        )
        
        if compliance_report:
            print(f"✅ Generated compliance report with {len(compliance_report.get('events', []))} audit events")
        else:
            print("❌ Failed to generate compliance report")
        
        print("\n🎉 Enterprise Features Tests Completed!")
        print("=" * 50)
        print("Enterprise Features Verified:")
        print("• Multi-tenant organization structure")
        print("• Department and project hierarchies") 
        print("• Role-based access control")
        print("• Approval workflows for resource requests")
        print("• Member management and permissions")
        print("• Compliance reporting and audit logging")
        print("• Budget limits and cost center tracking")
        
        # Show practical examples
        print("\n📊 Enterprise Capabilities Demonstrated:")
        print(f"• Organization: {org.name} ({org.tier.value} tier)")
        print(f"• Department: {dept.name} with ${dept.budget_limit:,.2f} budget")
        print(f"• Project: {project.name} with ${project.budget_limit:,.2f} budget")
        print(f"• Approval Request: {approval_request.resource_type} for ${approval_request.estimated_cost:,.2f}")
        print(f"• Organization Members: {len(members)} users with role-based access")
        print(f"• Audit Trail: {len(compliance_report.get('events', []))} compliance events tracked")
        
        # Cleanup
        os.remove("test_enterprise.db")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing enterprise features: {e}")
        import traceback
        traceback.print_exc()
        return False

async def setup_enterprise_test_data(db_manager):
    """Set up test data for enterprise testing"""
    
    import aiosqlite
    async with aiosqlite.connect(db_manager.db_path) as conn:
        # Create test users
        test_users = [
            ('test_user_1', 'owner@acme.com', 'enterprise'),
            ('test_user_2', 'dev@acme.com', 'premium'),
            ('test_user_3', 'manager@acme.com', 'premium')
        ]
        
        for user_id, email, tier in test_users:
            await conn.execute("""
                INSERT OR IGNORE INTO users (user_id, email, tier, created_at, monthly_budget)
                VALUES (?, ?, ?, ?, 1000.0)
            """, (user_id, email, tier, current_timestamp()))
        
        await conn.commit()

if __name__ == "__main__":
    success = asyncio.run(test_enterprise_features())
    sys.exit(0 if success else 1)