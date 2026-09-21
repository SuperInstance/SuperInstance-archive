"""
Beta Integration Test Configuration
Extends the main conftest.py with beta-specific fixtures and utilities
"""

import os
import sys
import pytest
import asyncio
import httpx
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import uuid
import json
import time
import random

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'services'))

# Beta test configuration
BETA_TEST_CONFIG = {
    'services': {
        'api_gateway': 'http://localhost:8000',
        'dmlog_core': 'http://localhost:8300',
        'makerlog': 'http://localhost:8301',
        'cross_app_orders': 'http://localhost:8302',
        'studylog': 'http://localhost:8303',
        'payment_service': 'http://localhost:8004',
        'activeledger': 'http://localhost:8005',
        'migration_toolkit': 'http://localhost:8006',
        'data_export': 'http://localhost:8007',
        'import_service': 'http://localhost:8008',
        'compute_exchange': 'http://localhost:8009',
        'compute_market': 'http://localhost:8010',
        'monitoring': 'http://localhost:8011',
        'content_creator': 'http://localhost:8012',
        'ai_orchestrator': 'http://localhost:8013',
        'creative_suite': 'http://localhost:8014',
        'video_processor': 'http://localhost:8015',
        'gaming_platform': 'http://localhost:8016',
        'unity_integration': 'http://localhost:8017',
        'websocket_game': 'ws://localhost:8018',
        'studylog_adults': 'http://localhost:8319',
        'education_ai': 'http://localhost:8320',
        'skill_development': 'http://localhost:8321',
        'professional_certs': 'http://localhost:8322'
    },
    'timeouts': {
        'default': 30.0,
        'long_running': 300.0,
        'file_upload': 120.0,
        'video_processing': 600.0
    },
    'retry_settings': {
        'max_attempts': 3,
        'backoff_factor': 2,
        'initial_delay': 1.0
    }
}


@pytest.fixture(scope="session")
def beta_config():
    """Provide beta test configuration"""
    return BETA_TEST_CONFIG


@pytest.fixture(scope="session")
def service_urls():
    """Provide service URLs for beta testing"""
    return BETA_TEST_CONFIG['services']


@pytest.fixture(scope="session", autouse=True)
async def verify_services_available(service_urls):
    """Verify that required services are available before running tests"""
    unavailable_services = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for service_name, url in service_urls.items():
            if url.startswith('ws://'):
                continue  # Skip WebSocket URLs for now
                
            try:
                health_url = f"{url}/health" if not url.endswith('/health') else url
                response = await client.get(health_url)
                if response.status_code not in [200, 404]:  # 404 is ok if no health endpoint
                    unavailable_services.append(service_name)
            except Exception:
                unavailable_services.append(service_name)
    
    if unavailable_services:
        pytest.skip(f"Services not available: {unavailable_services}")


@pytest.fixture
async def http_client():
    """Provide HTTP client with proper timeout settings"""
    timeout = httpx.Timeout(
        connect=10.0,
        read=30.0,
        write=10.0,
        pool=30.0
    )
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        yield client


@pytest.fixture
def test_user_factory():
    """Factory for creating test users with different profiles"""
    
    def create_user(user_type='basic', **overrides):
        base_user = {
            'id': str(uuid.uuid4()),
            'email': f'test_{uuid.uuid4().hex[:8]}@example.com',
            'name': 'Test User',
            'created_at': datetime.utcnow().isoformat(),
            'is_active': True
        }
        
        # User type-specific defaults
        type_defaults = {
            'basic': {
                'permissions': ['read', 'write'],
                'subscription': 'basic'
            },
            'premium': {
                'permissions': ['read', 'write', 'premium_features'],
                'subscription': 'premium',
                'credits_balance': 100.0
            },
            'admin': {
                'permissions': ['read', 'write', 'admin'],
                'subscription': 'enterprise',
                'role': 'admin'
            },
            'creator': {
                'permissions': ['read', 'write', 'content_creation'],
                'subscription': 'creator',
                'content_creator': True
            },
            'corporate': {
                'permissions': ['read', 'write', 'corporate'],
                'subscription': 'corporate',
                'organization': 'Test Corporation'
            }
        }
        
        user_data = {**base_user, **type_defaults.get(user_type, {}), **overrides}
        return user_data
    
    return create_user


@pytest.fixture
def auth_token_factory():
    """Factory for creating authentication tokens"""
    
    def create_token(user_id, permissions=None, expires_in_hours=24):
        # In a real implementation, this would create actual JWT tokens
        # For testing, we'll create mock tokens
        token_data = {
            'user_id': user_id,
            'permissions': permissions or ['read', 'write'],
            'expires_at': (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat(),
            'token_type': 'Bearer'
        }
        
        # Create a simple mock token (in real implementation, use JWT)
        mock_token = f"mock_token_{user_id}_{uuid.uuid4().hex[:8]}"
        
        return {
            'access_token': mock_token,
            'token_data': token_data,
            'headers': {'Authorization': f'Bearer {mock_token}'}
        }
    
    return create_token


@pytest.fixture
async def authenticated_sessions(test_user_factory, auth_token_factory):
    """Create multiple authenticated user sessions for testing"""
    
    sessions = {}
    user_types = ['basic', 'premium', 'admin', 'creator', 'corporate']
    
    for user_type in user_types:
        user = test_user_factory(user_type)
        token = auth_token_factory(user['id'], user.get('permissions'))
        
        sessions[user_type] = {
            'user': user,
            'token': token['access_token'],
            'headers': token['headers'],
            'permissions': user.get('permissions', [])
        }
    
    return sessions


@pytest.fixture
def beta_test_data_generator():
    """Generate test data for beta integration tests"""
    
    class BetaTestDataGenerator:
        @staticmethod
        def campaign_data(campaign_type='d&d', **overrides):
            base_campaign = {
                'id': str(uuid.uuid4()),
                'name': f'Test Campaign {uuid.uuid4().hex[:8]}',
                'created_at': datetime.utcnow().isoformat(),
                'status': 'active'
            }
            
            type_defaults = {
                'd&d': {
                    'system': 'D&D 5e',
                    'level_range': '1-5',
                    'max_players': 6,
                    'setting': 'fantasy'
                },
                'educational': {
                    'subject': 'mathematics',
                    'grade_level': '6-8',
                    'learning_objectives': ['problem_solving', 'critical_thinking']
                },
                'corporate': {
                    'program_type': 'leadership_development',
                    'duration_weeks': 12,
                    'participants': 25
                }
            }
            
            return {**base_campaign, **type_defaults.get(campaign_type, {}), **overrides}
        
        @staticmethod
        def order_data(order_type='custom_item', **overrides):
            base_order = {
                'id': str(uuid.uuid4()),
                'created_at': datetime.utcnow().isoformat(),
                'status': 'pending'
            }
            
            type_defaults = {
                'custom_item': {
                    'item_name': 'Custom Dice Tower',
                    'description': 'Wooden dice tower with custom engraving',
                    'price': 45.00,
                    'delivery_days': 14
                },
                'bulk_order': {
                    'items': [
                        {'name': 'Item 1', 'quantity': 5},
                        {'name': 'Item 2', 'quantity': 3}
                    ],
                    'total_price': 150.00,
                    'delivery_days': 21
                }
            }
            
            return {**base_order, **type_defaults.get(order_type, {}), **overrides}
        
        @staticmethod
        def learning_content(**overrides):
            base_content = {
                'id': str(uuid.uuid4()),
                'title': f'Learning Module {uuid.uuid4().hex[:8]}',
                'type': 'interactive_lesson',
                'difficulty': 'intermediate',
                'estimated_duration': 45
            }
            
            return {**base_content, **overrides}
    
    return BetaTestDataGenerator()


@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during tests"""
    
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {}
            self.start_times = {}
        
        def start_measurement(self, operation_name: str):
            self.start_times[operation_name] = time.time()
        
        def end_measurement(self, operation_name: str):
            if operation_name in self.start_times:
                elapsed = time.time() - self.start_times[operation_name]
                if operation_name not in self.metrics:
                    self.metrics[operation_name] = []
                self.metrics[operation_name].append(elapsed)
                del self.start_times[operation_name]
                return elapsed
            return None
        
        def get_average(self, operation_name: str):
            if operation_name in self.metrics:
                return sum(self.metrics[operation_name]) / len(self.metrics[operation_name])
            return None
        
        def get_all_metrics(self):
            return {
                op: {
                    'count': len(times),
                    'average': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times)
                }
                for op, times in self.metrics.items()
            }
    
    return PerformanceMonitor()


@pytest.fixture
def temp_file_manager():
    """Manage temporary files for testing"""
    
    class TempFileManager:
        def __init__(self):
            self.temp_dirs = []
            self.temp_files = []
        
        def create_temp_dir(self, prefix="beta_test_"):
            temp_dir = tempfile.mkdtemp(prefix=prefix)
            self.temp_dirs.append(temp_dir)
            return temp_dir
        
        def create_temp_file(self, content="", suffix=".txt", prefix="test_"):
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix=suffix, 
                prefix=prefix, 
                delete=False
            )
            temp_file.write(content)
            temp_file.close()
            self.temp_files.append(temp_file.name)
            return temp_file.name
        
        def cleanup(self):
            for temp_file in self.temp_files:
                try:
                    os.unlink(temp_file)
                except FileNotFoundError:
                    pass
            
            for temp_dir in self.temp_dirs:
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except FileNotFoundError:
                    pass
            
            self.temp_files.clear()
            self.temp_dirs.clear()
    
    manager = TempFileManager()
    yield manager
    manager.cleanup()


@pytest.fixture
def mock_external_services():
    """Mock external service responses for consistent testing"""
    
    class MockExternalServices:
        def __init__(self):
            self.mocked_responses = {}
        
        def mock_service(self, service_name: str, endpoint: str, response_data: dict, status_code: int = 200):
            key = f"{service_name}:{endpoint}"
            self.mocked_responses[key] = {
                'data': response_data,
                'status_code': status_code
            }
        
        def get_mock_response(self, service_name: str, endpoint: str):
            key = f"{service_name}:{endpoint}"
            return self.mocked_responses.get(key)
        
        def mock_stripe_payment_success(self):
            self.mock_service('stripe', 'payment_intents', {
                'id': 'pi_test_success',
                'status': 'succeeded',
                'amount': 5000,
                'currency': 'usd'
            })
        
        def mock_ai_service_response(self, content_type='text'):
            if content_type == 'text':
                response_data = {
                    'generated_content': 'This is AI-generated test content.',
                    'confidence_score': 0.95,
                    'processing_time': 1.2
                }
            elif content_type == 'image':
                response_data = {
                    'image_url': 'https://example.com/generated_image.jpg',
                    'generation_seed': 12345,
                    'processing_time': 3.5
                }
            else:
                response_data = {
                    'content': 'Generic AI response',
                    'metadata': {'type': content_type}
                }
            
            self.mock_service('ai_service', 'generate', response_data)
    
    return MockExternalServices()


@pytest.fixture(autouse=True)
def ensure_test_isolation():
    """Ensure tests are properly isolated"""
    # This runs before each test
    yield
    # This runs after each test - cleanup can go here
    pass


@pytest.fixture
def retry_with_backoff():
    """Utility for retrying operations with exponential backoff"""
    
    async def retry(operation, max_attempts=3, backoff_factor=2, initial_delay=1.0):
        """
        Retry an async operation with exponential backoff
        
        Args:
            operation: Async function to retry
            max_attempts: Maximum number of attempts
            backoff_factor: Multiplier for delay between attempts
            initial_delay: Initial delay in seconds
        
        Returns:
            Result of the operation if successful
        
        Raises:
            Last exception if all attempts fail
        """
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    delay = initial_delay * (backoff_factor ** attempt)
                    await asyncio.sleep(delay)
                else:
                    break
        
        raise last_exception
    
    return retry


# Custom markers for beta tests
def pytest_configure(config):
    """Configure custom pytest markers for beta tests"""
    config.addinivalue_line("markers", "beta: mark test as beta integration test")
    config.addinivalue_line("markers", "cross_app: mark test as cross-application workflow test")
    config.addinivalue_line("markers", "real_time: mark test as real-time feature test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add automatic markers"""
    for item in items:
        # Add beta marker to all tests in beta directory
        if 'beta' in str(item.fspath):
            item.add_marker(pytest.mark.beta)
        
        # Add markers based on test names
        if 'cross_app' in item.name or 'cross_platform' in item.name:
            item.add_marker(pytest.mark.cross_app)
        
        if 'real_time' in item.name or 'websocket' in item.name:
            item.add_marker(pytest.mark.real_time)
        
        if 'load' in item.name or 'concurrent' in item.name:
            item.add_marker(pytest.mark.load)


# Test result hooks
def pytest_runtest_makereport(item, call):
    """Hook to capture test results for reporting"""
    if call.when == "call":
        # Log test performance
        duration = call.duration
        if duration > 10:  # Log slow tests
            print(f"SLOW TEST: {item.nodeid} took {duration:.2f}s")


# Session hooks
def pytest_sessionstart(session):
    """Called after the Session object has been created"""
    print("\n" + "="*80)
    print("ActiveLog Beta Integration Test Suite Starting")
    print("="*80)


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished"""
    print("\n" + "="*80)
    print(f"ActiveLog Beta Integration Test Suite Completed (Exit Status: {exitstatus})")
    print("="*80)