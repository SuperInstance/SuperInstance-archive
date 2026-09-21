"""
Global test configuration for ActiveLog
Provides shared fixtures and test utilities
"""

import os
import sys
import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Generator
from unittest.mock import Mock, MagicMock, patch
import json
import uuid

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'services'))

# Test configuration
TEST_CONFIG = {
    'redis': {
        'host': 'localhost',
        'port': 6379,
        'db': 15,  # Use separate DB for tests
        'decode_responses': True
    },
    'database': {
        'url': 'postgresql://test_user:test_pass@localhost:5432/activelog_test',
        'echo': False
    },
    'storage': {
        'bucket': 'activelog-test-bucket',
        'region': 'us-east-1'
    },
    'openai': {
        'api_key': 'test-key-123',
        'model': 'gpt-3.5-turbo'
    }
}


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration"""
    return TEST_CONFIG


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_dir = tempfile.mkdtemp(prefix="activelog_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_user():
    """Sample user data for testing"""
    return {
        'id': str(uuid.uuid4()),
        'email': 'test@example.com',
        'name': 'Test User',
        'password_hash': 'hashed_password_123',
        'is_active': True,
        'created_at': datetime.utcnow(),
        'permissions': ['read', 'write']
    }


@pytest.fixture
def sample_file():
    """Sample file data for testing"""
    return {
        'id': str(uuid.uuid4()),
        'name': 'test_document.pdf',
        'path': '/user/documents/test_document.pdf',
        'size': 1024000,
        'file_type': 'document',
        'mime_type': 'application/pdf',
        'checksum': 'abc123def456',
        'sync_status': 'synced',
        'user_id': str(uuid.uuid4()),
        'created_at': datetime.utcnow(),
        'modified_at': datetime.utcnow(),
        'metadata': {
            'title': 'Test Document',
            'author': 'Test Author',
            'pages': 10
        }
    }


@pytest.fixture
def sample_embedding():
    """Sample embedding data for testing"""
    return {
        'id': str(uuid.uuid4()),
        'file_id': str(uuid.uuid4()),
        'embedding_model': 'text-embedding-ada-002',
        'embedding_vector': [0.1] * 1536,  # Mock embedding vector
        'chunk_text': 'This is a sample text chunk for testing embeddings.',
        'chunk_index': 0,
        'confidence_score': 0.95,
        'created_at': datetime.utcnow()
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    with patch('cache.redis_client.redis') as mock_redis:
        mock_client = MagicMock()
        mock_redis.Redis.return_value = mock_client
        mock_redis.ConnectionPool.return_value = MagicMock()
        
        # Mock common Redis operations
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_client.set.return_value = True
        mock_client.delete.return_value = 1
        mock_client.exists.return_value = False
        mock_client.keys.return_value = []
        mock_client.hget.return_value = None
        mock_client.hset.return_value = True
        mock_client.hgetall.return_value = {}
        mock_client.sadd.return_value = 1
        mock_client.smembers.return_value = set()
        mock_client.zadd.return_value = 1
        mock_client.zrange.return_value = []
        
        yield mock_client


@pytest.fixture
def mock_database():
    """Mock database connection for testing"""
    with patch('sqlalchemy.create_engine') as mock_engine:
        mock_session = MagicMock()
        mock_engine.return_value.connect.return_value = mock_session
        yield mock_session


@pytest.fixture
def mock_openai():
    """Mock OpenAI API for testing"""
    with patch('openai.ChatCompletion.create') as mock_create:
        mock_response = {
            'choices': [{
                'message': {
                    'content': 'This is a mock OpenAI response for testing.'
                }
            }],
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 15,
                'total_tokens': 25
            }
        }
        mock_create.return_value = mock_response
        yield mock_create


@pytest.fixture
def mock_s3():
    """Mock AWS S3 client for testing"""
    with patch('boto3.client') as mock_boto_client:
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        
        # Mock S3 operations
        mock_s3_client.upload_fileobj.return_value = None
        mock_s3_client.download_fileobj.return_value = None
        mock_s3_client.head_object.return_value = {
            'ContentLength': 1024,
            'LastModified': datetime.utcnow(),
            'ETag': '"abc123def456"'
        }
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': []
        }
        mock_s3_client.delete_object.return_value = {}
        
        yield mock_s3_client


@pytest.fixture
def mock_elasticsearch():
    """Mock Elasticsearch client for testing"""
    with patch('elasticsearch.Elasticsearch') as mock_es:
        mock_client = MagicMock()
        mock_es.return_value = mock_client
        
        # Mock search response
        mock_client.search.return_value = {
            'hits': {
                'total': {'value': 1},
                'hits': [{
                    '_id': 'test_doc_1',
                    '_score': 0.95,
                    '_source': {
                        'title': 'Test Document',
                        'content': 'This is test content',
                        'file_id': str(uuid.uuid4())
                    }
                }]
            }
        }
        
        mock_client.index.return_value = {'result': 'created'}
        mock_client.delete.return_value = {'result': 'deleted'}
        
        yield mock_client


@pytest.fixture
def mock_file_watcher():
    """Mock file system watcher for testing"""
    with patch('watchdog.observers.Observer') as mock_observer:
        mock_handler = MagicMock()
        mock_observer.return_value.start.return_value = None
        mock_observer.return_value.stop.return_value = None
        mock_observer.return_value.join.return_value = None
        yield mock_observer, mock_handler


@pytest.fixture
def test_files():
    """Create test files for file operations"""
    test_files = []
    
    def create_test_file(name: str, content: str = "Test content", size: int = None):
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=name, delete=False)
        temp_file.write(content)
        temp_file.close()
        
        if size:
            # Pad file to specific size
            with open(temp_file.name, 'ab') as f:
                current_size = os.path.getsize(temp_file.name)
                if size > current_size:
                    f.write(b'0' * (size - current_size))
        
        test_files.append(temp_file.name)
        return temp_file.name
    
    yield create_test_file
    
    # Cleanup
    for file_path in test_files:
        try:
            os.unlink(file_path)
        except FileNotFoundError:
            pass


@pytest.fixture
def mock_jwt():
    """Mock JWT token operations"""
    with patch('jwt.encode') as mock_encode, patch('jwt.decode') as mock_decode:
        mock_encode.return_value = 'mock.jwt.token'
        mock_decode.return_value = {
            'user_id': str(uuid.uuid4()),
            'email': 'test@example.com',
            'exp': (datetime.utcnow() + timedelta(hours=1)).timestamp()
        }
        yield mock_encode, mock_decode


@pytest.fixture
def api_headers(sample_user):
    """Generate API headers with authentication"""
    return {
        'Authorization': f'Bearer mock.jwt.token',
        'Content-Type': 'application/json',
        'User-Agent': 'ActiveLog-Test/1.0'
    }


@pytest.fixture
def websocket_mock():
    """Mock WebSocket connection for testing"""
    mock_websocket = MagicMock()
    mock_websocket.send.return_value = None
    mock_websocket.recv.return_value = json.dumps({'type': 'test', 'data': {}})
    mock_websocket.close.return_value = None
    return mock_websocket


class MockAsyncContext:
    """Mock async context manager for testing"""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aaxit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_async_session():
    """Mock async database session"""
    session = MagicMock()
    session.execute.return_value = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None
    
    # Make it work as async context manager
    session.__aenter__ = lambda self: self
    session.__aexit__ = lambda self, *args: None
    
    return session


@pytest.fixture
def performance_monitor():
    """Monitor test performance"""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.metrics = {}
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self, operation_name: str):
            if self.start_time:
                elapsed = time.time() - self.start_time
                self.metrics[operation_name] = elapsed
                self.start_time = None
                return elapsed
        
        def get_metrics(self):
            return self.metrics
    
    return PerformanceMonitor()


@pytest.fixture
def cleanup_manager():
    """Manage test cleanup operations"""
    cleanup_functions = []
    
    def register_cleanup(func, *args, **kwargs):
        cleanup_functions.append((func, args, kwargs))
    
    yield register_cleanup
    
    # Execute cleanup functions
    for func, args, kwargs in cleanup_functions:
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"Cleanup error: {e}")


# Test markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "load: mark test as load test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "external: mark test as requiring external services")


# Async test utilities
def pytest_runtest_setup(item):
    """Setup for each test"""
    if 'asyncio' in item.keywords:
        # Ensure event loop is available for async tests
        if not hasattr(item.session, '_event_loop'):
            item.session._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(item.session._event_loop)


def pytest_runtest_teardown(item):
    """Teardown for each test"""
    # Clean up any remaining async tasks
    try:
        loop = asyncio.get_event_loop()
        pending = asyncio.all_tasks(loop)
        if pending:
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except RuntimeError:
        pass  # No event loop running


# Test data generators
class TestDataGenerator:
    """Generate test data for various scenarios"""
    
    @staticmethod
    def generate_users(count: int = 10) -> list:
        """Generate multiple test users"""
        users = []
        for i in range(count):
            users.append({
                'id': str(uuid.uuid4()),
                'email': f'user{i}@example.com',
                'name': f'User {i}',
                'password_hash': f'hash_{i}',
                'is_active': True,
                'created_at': datetime.utcnow(),
                'permissions': ['read', 'write'] if i % 2 == 0 else ['read']
            })
        return users
    
    @staticmethod
    def generate_files(user_id: str, count: int = 20) -> list:
        """Generate multiple test files for a user"""
        files = []
        file_types = ['document', 'image', 'video', 'audio', 'archive']
        
        for i in range(count):
            file_type = file_types[i % len(file_types)]
            files.append({
                'id': str(uuid.uuid4()),
                'name': f'test_file_{i}.{file_type}',
                'path': f'/user/files/test_file_{i}.{file_type}',
                'size': 1024 * (i + 1),
                'file_type': file_type,
                'mime_type': f'application/{file_type}',
                'checksum': f'checksum_{i}',
                'sync_status': 'synced' if i % 3 == 0 else 'local',
                'user_id': user_id,
                'created_at': datetime.utcnow(),
                'modified_at': datetime.utcnow()
            })
        return files


@pytest.fixture
def test_data_generator():
    """Provide test data generator"""
    return TestDataGenerator()


# Environment setup
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables"""
    test_env = {
        'ENVIRONMENT': 'test',
        'REDIS_URL': 'redis://localhost:6379/15',
        'DATABASE_URL': TEST_CONFIG['database']['url'],
        'AWS_ACCESS_KEY_ID': 'test-access-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
        'OPENAI_API_KEY': TEST_CONFIG['openai']['api_key'],
        'JWT_SECRET_KEY': 'test-jwt-secret-key',
        'ELASTICSEARCH_URL': 'http://localhost:9200',
        'LOG_LEVEL': 'DEBUG'
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)