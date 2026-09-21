#!/usr/bin/env python3
"""
Comprehensive Test Suite for Cloud Infrastructure System
Tests all major components: provisioning, billing, scaling, isolation, and API
"""

import asyncio
import json
import os
import pytest
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch
import sys

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import core components
from core.database_manager import DatabaseManager
from core.models import (
    User, UserTier, BillingStatus, EC2Instance, InstanceState, InstanceType,
    CreateInstanceRequest, BillingRecord, ScalingEvent, GameNightEvent,
    current_timestamp, generate_id
)
from provisioning.ec2_provisioner import EC2Provisioner
from billing.engine import BillingEngine
from billing.usage_tracker import UsageTracker
from scaling.auto_scaler import AutoScaler
from isolation.tenant_manager import TenantManager
from isolation.access_control import AccessControlManager, Permission
from api.gateway import create_app
from main import CloudInfrastructureOrchestrator

# Test configuration
TEST_CONFIG = {
    "aws": {
        "region": "us-west-2",
        "availability_zones": ["us-west-2a", "us-west-2b"],
        "default_instance_type": "t3.medium",
        "default_image_id": "ami-12345678",
        "max_instances_per_user": 5,
        "use_real_aws": False  # Use mocks for testing
    },
    "billing": {
        "billing_precision": "per_minute",
        "currency": "USD",
        "pricing": {
            "compute": {
                "t3.medium": 0.0067,
                "t3.large": 0.0133
            }
        }
    },
    "scaling": {
        "scaling_enabled": True,
        "scaling_interval_seconds": 5,  # Fast for testing
        "min_instances": 1,
        "max_instances": 10
    },
    "isolation": {
        "enable_strict_isolation": True,
        "isolation_level": "vpc"
    },
    "api": {
        "host": "127.0.0.1",
        "port": 8601  # Different port for testing
    }
}

@pytest.fixture
async def temp_database():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    db_manager = DatabaseManager(db_path)
    await db_manager.initialize()
    
    yield db_manager
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass

@pytest.fixture
async def test_user():
    """Create a test user"""
    return User(
        user_id="test-user-001",
        email="test@example.com",
        tier=UserTier.PREMIUM,
        created_at=current_timestamp(),
        billing_status=BillingStatus.ACTIVE,
        monthly_budget=100.0,
        current_spend=0.0
    )

@pytest.fixture
async def orchestrator():
    """Create test orchestrator"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, "test_config.yaml")
        
        # Write test config
        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(TEST_CONFIG, f)
        
        orchestrator = CloudInfrastructureOrchestrator(config_path)
        yield orchestrator

class TestDatabaseManager:
    """Test database operations"""
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, temp_database):
        """Test database initialization"""
        db = temp_database
        assert db.initialized
        
        # Test basic query
        user_count = await db.count_total_users()
        assert user_count == 0
    
    @pytest.mark.asyncio
    async def test_user_operations(self, temp_database, test_user):
        """Test user CRUD operations"""
        db = temp_database
        
        # Create user
        success = await db.create_user(test_user)
        assert success
        
        # Read user
        retrieved_user = await db.get_user(test_user.user_id)
        assert retrieved_user is not None
        assert retrieved_user.user_id == test_user.user_id
        assert retrieved_user.email == test_user.email
        
        # Update user
        test_user.current_spend = 25.50
        success = await db.update_user(test_user)
        assert success
        
        # Verify update
        updated_user = await db.get_user(test_user.user_id)
        assert updated_user.current_spend == 25.50
        
        # Count users
        user_count = await db.count_total_users()
        assert user_count == 1
    
    @pytest.mark.asyncio
    async def test_instance_operations(self, temp_database, test_user):
        """Test instance CRUD operations"""
        db = temp_database
        
        # Create user first
        await db.create_user(test_user)
        
        # Create instance
        instance = EC2Instance(
            instance_id="i-12345678",
            user_id=test_user.user_id,
            instance_type=InstanceType.T3_MEDIUM,
            state=InstanceState.RUNNING,
            created_at=current_timestamp(),
            vpc_id="vpc-test",
            subnet_id="subnet-test",
            security_groups=["sg-test"],
            tags={"Test": "True"}
        )
        
        success = await db.create_instance(instance)
        assert success
        
        # Read instance
        retrieved_instance = await db.get_instance(instance.instance_id)
        assert retrieved_instance is not None
        assert retrieved_instance.instance_id == instance.instance_id
        assert retrieved_instance.user_id == test_user.user_id
        
        # Get user instances
        user_instances = await db.get_user_instances(test_user.user_id)
        assert len(user_instances) == 1
        assert user_instances[0].instance_id == instance.instance_id
        
        # Count instances
        instance_count = await db.count_user_instances(test_user.user_id)
        assert instance_count == 1

class TestEC2Provisioner:
    """Test EC2 provisioning functionality"""
    
    @pytest.mark.asyncio
    async def test_provisioner_initialization(self, temp_database):
        """Test provisioner initialization"""
        provisioner = EC2Provisioner(TEST_CONFIG, temp_database)
        assert provisioner is not None
        assert provisioner.use_mock  # Should use mock for testing
    
    @pytest.mark.asyncio
    async def test_instance_provisioning(self, temp_database, test_user):
        """Test instance provisioning"""
        db = temp_database
        provisioner = EC2Provisioner(TEST_CONFIG, db)
        
        # Create user
        await db.create_user(test_user)
        
        # Create provisioning request
        request = CreateInstanceRequest(
            user_id=test_user.user_id,
            instance_type=InstanceType.T3_MEDIUM,
            image_id="ami-12345678",
            tags={"Purpose": "Testing"}
        )
        
        # Provision instance
        response = await provisioner.provision_instance(request)
        assert response is not None
        assert response.instance_type == InstanceType.T3_MEDIUM
        
        # Verify instance was created in database
        user_instances = await db.get_user_instances(test_user.user_id)
        assert len(user_instances) == 1
    
    @pytest.mark.asyncio
    async def test_instance_termination(self, temp_database, test_user):
        """Test instance termination"""
        db = temp_database
        provisioner = EC2Provisioner(TEST_CONFIG, db)
        
        # Create user and instance
        await db.create_user(test_user)
        
        request = CreateInstanceRequest(
            user_id=test_user.user_id,
            instance_type=InstanceType.T3_MEDIUM,
            image_id="ami-12345678"
        )
        
        response = await provisioner.provision_instance(request)
        instance_id = response.instance_id
        
        # Terminate instance
        success = await provisioner.terminate_instance(test_user.user_id, instance_id)
        assert success
        
        # Verify instance state changed
        instance = await db.get_instance(instance_id)
        assert instance.state in [InstanceState.TERMINATING, InstanceState.TERMINATED]
    
    @pytest.mark.asyncio
    async def test_user_limits(self, temp_database, test_user):
        """Test user instance limits"""
        db = temp_database
        provisioner = EC2Provisioner(TEST_CONFIG, db)
        
        await db.create_user(test_user)
        
        # Create instances up to limit
        max_instances = TEST_CONFIG["aws"]["max_instances_per_user"]
        
        for i in range(max_instances):
            request = CreateInstanceRequest(
                user_id=test_user.user_id,
                instance_type=InstanceType.T3_MEDIUM,
                image_id="ami-12345678"
            )
            
            response = await provisioner.provision_instance(request)
            assert response is not None
        
        # Try to create one more (should fail)
        request = CreateInstanceRequest(
            user_id=test_user.user_id,
            instance_type=InstanceType.T3_MEDIUM,
            image_id="ami-12345678"
        )
        
        with pytest.raises(ValueError, match="maximum instance limit"):
            await provisioner.provision_instance(request)

class TestBillingEngine:
    """Test billing engine functionality"""
    
    @pytest.mark.asyncio
    async def test_billing_engine_initialization(self, temp_database):
        """Test billing engine initialization"""
        billing_engine = BillingEngine(TEST_CONFIG, temp_database)
        assert billing_engine is not None
        assert not billing_engine.billing_active  # Should start inactive
    
    @pytest.mark.asyncio
    async def test_billing_calculation(self, temp_database, test_user):
        """Test billing calculations"""
        db = temp_database
        billing_engine = BillingEngine(TEST_CONFIG, db)
        
        # Create user and instance
        await db.create_user(test_user)
        
        instance = EC2Instance(
            instance_id="i-billing-test",
            user_id=test_user.user_id,
            instance_type=InstanceType.T3_MEDIUM,
            state=InstanceState.RUNNING,
            created_at=current_timestamp() - timedelta(minutes=60),  # 1 hour ago
            last_billed_at=current_timestamp() - timedelta(minutes=60)
        )
        await db.create_instance(instance)
        
        # Process billing for the instance
        await billing_engine._bill_instance_minute(instance)
        
        # Check that billing record was created
        billing_records = await db.get_billing_records(test_user.user_id)
        assert len(billing_records) > 0
        
        # Verify billing calculation
        record = billing_records[0]
        expected_cost = TEST_CONFIG["billing"]["pricing"]["compute"]["t3.medium"] * 60  # 60 minutes
        assert abs(record.total_cost - expected_cost) < 0.001  # Allow for floating point precision
    
    @pytest.mark.asyncio
    async def test_usage_projection(self, temp_database, test_user):
        """Test cost projection"""
        db = temp_database
        billing_engine = BillingEngine(TEST_CONFIG, db)
        
        await db.create_user(test_user)
        
        # Create some billing history
        for i in range(7):  # 7 days of history
            record = BillingRecord(
                record_id=generate_id("bill"),
                user_id=test_user.user_id,
                instance_id="i-test",
                instance_type=InstanceType.T3_MEDIUM,
                start_time=current_timestamp() - timedelta(days=7-i, hours=1),
                end_time=current_timestamp() - timedelta(days=7-i),
                duration_minutes=60,
                cost_per_minute=0.0067,
                total_cost=0.4020  # 60 minutes * $0.0067
            )
            await db.create_billing_record(record)
        
        # Test projection
        projection = await billing_engine.calculate_projected_cost(test_user.user_id, 30)
        
        assert "projected_cost" in projection
        assert projection["projected_cost"] > 0
        assert "daily_average_cost" in projection

class TestAutoScaler:
    """Test auto-scaling functionality"""
    
    @pytest.mark.asyncio
    async def test_scaler_initialization(self, temp_database):
        """Test auto-scaler initialization"""
        # Mock EC2 provisioner
        mock_provisioner = Mock()
        scaler = AutoScaler(TEST_CONFIG, temp_database, mock_provisioner)
        
        assert scaler is not None
        assert not scaler.scaling_active  # Should start inactive
    
    @pytest.mark.asyncio
    async def test_game_night_scheduling(self, temp_database, test_user):
        """Test game night event scheduling"""
        db = temp_database
        mock_provisioner = Mock()
        scaler = AutoScaler(TEST_CONFIG, db, mock_provisioner)
        
        await db.create_user(test_user)
        
        # Create game night event
        game_night = GameNightEvent(
            event_id=generate_id("game"),
            user_id=test_user.user_id,
            name="Test Game Night",
            start_time=current_timestamp() + timedelta(hours=1),
            duration_hours=4,
            expected_players=100,
            scale_multiplier=3.0,
            pre_scale_instances=0
        )
        
        # Schedule the event
        success = await scaler.schedule_game_night(game_night)
        assert success
        
        # Verify event was saved
        events = await db.get_active_game_night_events(test_user.user_id)
        assert len(events) == 1
        assert events[0].name == "Test Game Night"

class TestTenantManager:
    """Test tenant isolation functionality"""
    
    @pytest.mark.asyncio
    async def test_tenant_manager_initialization(self, temp_database):
        """Test tenant manager initialization"""
        tenant_manager = TenantManager(TEST_CONFIG, temp_database)
        assert tenant_manager is not None
        assert tenant_manager.enable_strict_isolation
    
    @pytest.mark.asyncio
    async def test_user_isolation_creation(self, temp_database, test_user):
        """Test user isolation environment creation"""
        db = temp_database
        tenant_manager = TenantManager(TEST_CONFIG, db)
        
        await db.create_user(test_user)
        
        # Create isolation environment
        isolation_info = await tenant_manager.create_user_isolation(test_user)
        
        assert isolation_info is not None
        assert isolation_info.user_id == test_user.user_id
        assert isolation_info.vpc_id is not None
        assert len(isolation_info.subnet_ids) > 0
        assert len(isolation_info.security_group_ids) > 0
    
    @pytest.mark.asyncio
    async def test_access_validation(self, temp_database, test_user):
        """Test resource access validation"""
        db = temp_database
        tenant_manager = TenantManager(TEST_CONFIG, db)
        
        await db.create_user(test_user)
        
        # Create isolation and instance
        isolation_info = await tenant_manager.create_user_isolation(test_user)
        
        instance = EC2Instance(
            instance_id="i-access-test",
            user_id=test_user.user_id,
            instance_type=InstanceType.T3_MEDIUM,
            state=InstanceState.RUNNING,
            created_at=current_timestamp(),
            vpc_id=isolation_info.vpc_id,
            subnet_id=isolation_info.subnet_ids[0]
        )
        await db.create_instance(instance)
        
        # Test access validation
        has_access = await tenant_manager.validate_user_access(
            test_user.user_id, instance.instance_id, "instance"
        )
        assert has_access
        
        # Test access denial for different user
        no_access = await tenant_manager.validate_user_access(
            "different-user", instance.instance_id, "instance"
        )
        assert not no_access

class TestAccessControl:
    """Test access control and permissions"""
    
    @pytest.mark.asyncio
    async def test_access_control_initialization(self, temp_database):
        """Test access control initialization"""
        access_control = AccessControlManager(TEST_CONFIG, temp_database)
        assert access_control is not None
        assert access_control.rbac_enabled
    
    @pytest.mark.asyncio
    async def test_permission_checking(self, temp_database, test_user):
        """Test permission checking"""
        db = temp_database
        access_control = AccessControlManager(TEST_CONFIG, db)
        
        await db.create_user(test_user)
        
        # Test permission for premium user
        has_permission, reason = await access_control.check_permission(
            test_user.user_id, Permission.INSTANCE_CREATE
        )
        assert has_permission
        
        # Test permission that should be denied
        has_permission, reason = await access_control.check_permission(
            test_user.user_id, Permission.ADMIN_SYSTEM_CONFIG
        )
        assert not has_permission
    
    @pytest.mark.asyncio
    async def test_api_key_management(self, temp_database, test_user):
        """Test API key creation and validation"""
        db = temp_database
        access_control = AccessControlManager(TEST_CONFIG, db)
        
        await db.create_user(test_user)
        
        # Create API key
        permissions = [Permission.INSTANCE_READ, Permission.BILLING_READ]
        api_key_info = await access_control.create_api_key(
            test_user.user_id, "Test Key", permissions
        )
        
        assert "api_key" in api_key_info
        assert api_key_info["user_id"] == test_user.user_id
        
        # Validate API key
        validation_result = await access_control.validate_api_key(api_key_info["api_key"])
        assert validation_result is not None
        assert validation_result["user_id"] == test_user.user_id
        assert Permission.INSTANCE_READ in validation_result["permissions"]

class TestSystemIntegration:
    """Test full system integration"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        """Test system orchestrator initialization"""
        # Initialize services
        await orchestrator.initialize_services()
        
        assert orchestrator.database_manager is not None
        assert orchestrator.ec2_provisioner is not None
        assert orchestrator.billing_engine is not None
        assert orchestrator.auto_scaler is not None
        assert orchestrator.tenant_manager is not None
        assert orchestrator.access_control is not None
    
    @pytest.mark.asyncio
    async def test_demo_user_creation(self, orchestrator):
        """Test demo user creation"""
        await orchestrator.initialize_services()
        
        demo_user_id = await orchestrator.create_demo_user()
        assert demo_user_id is not None
        
        # Verify user was created
        user = await orchestrator.database_manager.get_user(demo_user_id)
        assert user is not None
        assert user.tier == UserTier.PREMIUM
    
    @pytest.mark.asyncio
    async def test_health_check(self, orchestrator):
        """Test system health check"""
        await orchestrator.initialize_services()
        
        health = await orchestrator.health_check()
        assert health["system"] == "cloud_infrastructure"
        assert "services" in health
        
        # Check that all services are represented
        expected_services = [
            "database_manager", "ec2_provisioner", "billing_engine",
            "usage_tracker", "auto_scaler", "tenant_manager", "access_control"
        ]
        
        for service in expected_services:
            assert service in health["services"]

# Test the API endpoints (simplified)
class TestAPIEndpoints:
    """Test API functionality"""
    
    @pytest.mark.asyncio
    async def test_api_creation(self, temp_database):
        """Test API application creation"""
        # Create minimal services for API
        services = {
            "database_manager": temp_database,
            "access_control": AccessControlManager(TEST_CONFIG, temp_database)
        }
        
        app = create_app(TEST_CONFIG, **services)
        assert app is not None

def run_comprehensive_tests():
    """Run all test suites"""
    print("Starting Comprehensive Cloud Infrastructure Tests")
    print("=" * 60)
    
    # Get the test file path
    test_file = __file__
    
    # Run pytest with verbose output
    pytest_args = [
        test_file,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    # Run the tests
    exit_code = pytest.main(pytest_args)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if exit_code == 0:
        print("✅ All tests passed!")
        print("\nCore functionality validated:")
        print("  ✅ Database operations")
        print("  ✅ EC2 provisioning")
        print("  ✅ Billing engine")
        print("  ✅ Auto-scaling")
        print("  ✅ Tenant isolation")
        print("  ✅ Access control")
        print("  ✅ System integration")
    else:
        print("❌ Some tests failed")
    
    return exit_code == 0

if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit_code = 0 if success else 1
    print(f"\nTest execution completed with exit code: {exit_code}")
    exit(exit_code)