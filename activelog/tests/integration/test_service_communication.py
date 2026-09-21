"""
Integration tests for service communication
Tests inter-service communication, API endpoints, and data flow
"""

import pytest
import asyncio
import aiohttp
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import test utilities
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services'))


@pytest.mark.integration
class TestAuthServiceIntegration:
    """Test authentication service integration"""
    
    @pytest.fixture
    def auth_service_url(self):
        """Auth service URL for testing"""
        return "http://localhost:8001"
    
    @pytest.fixture
    async def http_session(self):
        """HTTP session for making requests"""
        async with aiohttp.ClientSession() as session:
            yield session
    
    async def test_user_registration_flow(self, http_session, auth_service_url):
        """Test complete user registration flow"""
        registration_data = {
            "email": f"test_{uuid.uuid4()}@example.com",
            "password": "TestPassword123!",
            "name": "Test User"
        }
        
        # Mock auth service response
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "user": {
                    "id": str(uuid.uuid4()),
                    "email": registration_data["email"],
                    "name": registration_data["name"],
                    "is_active": True
                }
            })
            mock_post.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_post.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.post(
                f"{auth_service_url}/auth/register",
                json=registration_data
            ) as response:
                assert response.status == 201
                data = await response.json()
                
                assert data["success"] is True
                assert data["user"]["email"] == registration_data["email"]
                assert "id" in data["user"]
    
    async def test_user_login_flow(self, http_session, auth_service_url, sample_user):
        """Test complete user login flow"""
        login_data = {
            "email": sample_user["email"],
            "password": "TestPassword123!",
            "device_info": {
                "platform": "web",
                "browser": "chrome"
            }
        }
        
        # Mock auth service response
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "access_token": "mock.jwt.token",
                "refresh_token": "mock.refresh.token",
                "user": sample_user
            })
            mock_post.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_post.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.post(
                f"{auth_service_url}/auth/login",
                json=login_data
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["success"] is True
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["user"]["id"] == sample_user["id"]
    
    async def test_token_refresh_flow(self, http_session, auth_service_url):
        """Test token refresh flow"""
        refresh_data = {
            "refresh_token": "mock.refresh.token"
        }
        
        # Mock auth service response
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "access_token": "new.jwt.token",
                "refresh_token": "new.refresh.token"
            })
            mock_post.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_post.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.post(
                f"{auth_service_url}/auth/refresh",
                json=refresh_data
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["success"] is True
                assert "access_token" in data
    
    async def test_protected_endpoint_access(self, http_session, auth_service_url, api_headers):
        """Test accessing protected endpoints"""
        # Mock auth service response
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "user": {
                    "id": str(uuid.uuid4()),
                    "email": "test@example.com",
                    "name": "Test User"
                }
            })
            mock_get.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_get.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.get(
                f"{auth_service_url}/auth/me",
                headers=api_headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["success"] is True
                assert "user" in data


@pytest.mark.integration
class TestMetadataServiceIntegration:
    """Test metadata service integration"""
    
    @pytest.fixture
    def metadata_service_url(self):
        """Metadata service URL for testing"""
        return "http://localhost:8002"
    
    @pytest.fixture
    async def http_session(self):
        """HTTP session for making requests"""
        async with aiohttp.ClientSession() as session:
            yield session
    
    async def test_file_metadata_crud_flow(self, http_session, metadata_service_url, 
                                         sample_file, api_headers):
        """Test complete file metadata CRUD flow"""
        
        # Create file metadata
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "file": sample_file
            })
            mock_post.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_post.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.post(
                f"{metadata_service_url}/metadata/files",
                json=sample_file,
                headers=api_headers
            ) as response:
                assert response.status == 201
                data = await response.json()
                
                assert data["success"] is True
                file_id = data["file"]["id"]
        
        # Get file metadata
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "file": sample_file
            })
            mock_get.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_get.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.get(
                f"{metadata_service_url}/metadata/files/{file_id}",
                headers=api_headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["success"] is True
                assert data["file"]["id"] == file_id
        
        # Update file metadata
        update_data = {"name": "updated_file.pdf"}
        
        with patch('aiohttp.ClientSession.put') as mock_put:
            updated_file = sample_file.copy()
            updated_file["name"] = "updated_file.pdf"
            
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "file": updated_file
            })
            mock_put.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_put.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.put(
                f"{metadata_service_url}/metadata/files/{file_id}",
                json=update_data,
                headers=api_headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["success"] is True
                assert data["file"]["name"] == "updated_file.pdf"
        
        # Delete file metadata
        with patch('aiohttp.ClientSession.delete') as mock_delete:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "message": "File deleted successfully"
            })
            mock_delete.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_delete.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.delete(
                f"{metadata_service_url}/metadata/files/{file_id}",
                headers=api_headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["success"] is True
    
    async def test_file_search_integration(self, http_session, metadata_service_url, 
                                         api_headers):
        """Test file search integration"""
        search_params = {
            "query": "machine learning",
            "file_type": "document",
            "limit": 10
        }
        
        mock_search_results = [
            {
                "id": str(uuid.uuid4()),
                "name": "ml_paper.pdf",
                "path": "/documents/ml_paper.pdf",
                "relevance_score": 0.95
            },
            {
                "id": str(uuid.uuid4()),
                "name": "ai_research.pdf",
                "path": "/documents/ai_research.pdf",
                "relevance_score": 0.88
            }
        ]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "files": mock_search_results,
                "total_count": len(mock_search_results)
            })
            mock_post.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_post.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.post(
                f"{metadata_service_url}/metadata/search",
                json=search_params,
                headers=api_headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["success"] is True
                assert len(data["files"]) == 2
                assert data["files"][0]["relevance_score"] >= data["files"][1]["relevance_score"]
    
    async def test_embedding_generation_integration(self, http_session, metadata_service_url,
                                                  sample_file, api_headers):
        """Test embedding generation integration"""
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "embedding": {
                    "file_id": sample_file["id"],
                    "vector": [0.1] * 1536,
                    "chunks": 3,
                    "model": "text-embedding-ada-002"
                }
            })
            mock_post.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_post.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.post(
                f"{metadata_service_url}/metadata/embeddings/generate",
                json={"file_id": sample_file["id"]},
                headers=api_headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["success"] is True
                assert "embedding" in data
                assert len(data["embedding"]["vector"]) == 1536


@pytest.mark.integration
class TestAPIGatewayIntegration:
    """Test API Gateway integration and routing"""
    
    @pytest.fixture
    def gateway_url(self):
        """API Gateway URL for testing"""
        return "http://localhost:8000"
    
    @pytest.fixture
    async def http_session(self):
        """HTTP session for making requests"""
        async with aiohttp.ClientSession() as session:
            yield session
    
    async def test_service_routing(self, http_session, gateway_url, api_headers):
        """Test API Gateway service routing"""
        
        # Test auth service routing
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "service": "auth",
                "status": "healthy"
            })
            mock_get.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_get.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.get(
                f"{gateway_url}/auth/health",
                headers=api_headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                assert data["service"] == "auth"
        
        # Test metadata service routing
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "service": "metadata",
                "status": "healthy"
            })
            mock_get.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_get.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.get(
                f"{gateway_url}/metadata/health",
                headers=api_headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                assert data["service"] == "metadata"
    
    async def test_request_authentication(self, http_session, gateway_url):
        """Test API Gateway request authentication"""
        
        # Test unauthenticated request
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status = 401
            mock_response.json = asyncio.coroutine(lambda: {
                "error": "Authentication required"
            })
            mock_get.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_get.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.get(
                f"{gateway_url}/metadata/files"
            ) as response:
                assert response.status == 401
                data = await response.json()
                assert "error" in data
    
    async def test_rate_limiting(self, http_session, gateway_url, api_headers):
        """Test API Gateway rate limiting"""
        
        # Simulate multiple rapid requests
        request_count = 0
        
        async def mock_request(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            
            mock_response = MagicMock()
            if request_count > 100:  # Rate limit threshold
                mock_response.status = 429
                mock_response.json = asyncio.coroutine(lambda: {
                    "error": "Rate limit exceeded"
                })
            else:
                mock_response.status = 200
                mock_response.json = asyncio.coroutine(lambda: {"status": "ok"})
            
            mock_response.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_response.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            return mock_response
        
        with patch('aiohttp.ClientSession.get', side_effect=mock_request):
            # Make requests until rate limited
            for i in range(105):
                async with http_session.get(
                    f"{gateway_url}/auth/health",
                    headers=api_headers
                ) as response:
                    if i < 100:
                        assert response.status == 200
                    else:
                        assert response.status == 429
    
    async def test_load_balancing(self, http_session, gateway_url, api_headers):
        """Test API Gateway load balancing"""
        
        service_responses = []
        
        async def mock_request(*args, **kwargs):
            # Simulate different service instances
            instance_id = len(service_responses) % 3 + 1
            
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "service": "metadata",
                "instance": f"instance-{instance_id}",
                "status": "healthy"
            })
            mock_response.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_response.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            response_data = {
                "service": "metadata",
                "instance": f"instance-{instance_id}",
                "status": "healthy"
            }
            service_responses.append(response_data)
            
            return mock_response
        
        with patch('aiohttp.ClientSession.get', side_effect=mock_request):
            # Make multiple requests
            for i in range(6):
                async with http_session.get(
                    f"{gateway_url}/metadata/health",
                    headers=api_headers
                ) as response:
                    assert response.status == 200
                    data = await response.json()
                    assert "instance" in data
        
        # Verify load balancing (should hit different instances)
        instances = [resp["instance"] for resp in service_responses]
        unique_instances = set(instances)
        assert len(unique_instances) > 1  # Should distribute across instances


@pytest.mark.integration
class TestAIServiceIntegration:
    """Test AI service integration"""
    
    @pytest.fixture
    def ai_service_url(self):
        """AI service URL for testing"""
        return "http://localhost:8003"
    
    @pytest.fixture
    async def http_session(self):
        """HTTP session for making requests"""
        async with aiohttp.ClientSession() as session:
            yield session
    
    async def test_semantic_search_integration(self, http_session, ai_service_url, api_headers):
        """Test semantic search integration"""
        search_request = {
            "query": "machine learning algorithms",
            "similarity_threshold": 0.7,
            "limit": 10
        }
        
        mock_results = [
            {
                "file_id": str(uuid.uuid4()),
                "similarity_score": 0.92,
                "file_name": "ml_algorithms.pdf",
                "snippet": "Introduction to machine learning algorithms..."
            },
            {
                "file_id": str(uuid.uuid4()),
                "similarity_score": 0.85,
                "file_name": "deep_learning.pdf",
                "snippet": "Deep learning is a subset of machine learning..."
            }
        ]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "results": mock_results,
                "query_embedding": [0.1] * 1536
            })
            mock_post.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_post.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.post(
                f"{ai_service_url}/ai/semantic-search",
                json=search_request,
                headers=api_headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["success"] is True
                assert len(data["results"]) == 2
                assert data["results"][0]["similarity_score"] > 0.8
    
    async def test_text_analysis_integration(self, http_session, ai_service_url, api_headers):
        """Test text analysis integration"""
        analysis_request = {
            "text": "This is a research paper about artificial intelligence and machine learning.",
            "analysis_types": ["sentiment", "keywords", "entities"]
        }
        
        mock_analysis = {
            "sentiment": {
                "polarity": 0.1,
                "subjectivity": 0.4,
                "label": "neutral"
            },
            "keywords": [
                {"word": "artificial intelligence", "score": 0.95},
                {"word": "machine learning", "score": 0.90},
                {"word": "research", "score": 0.75}
            ],
            "entities": [
                {"text": "artificial intelligence", "type": "TECHNOLOGY"},
                {"text": "machine learning", "type": "TECHNOLOGY"}
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "analysis": mock_analysis
            })
            mock_post.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_post.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with http_session.post(
                f"{ai_service_url}/ai/analyze-text",
                json=analysis_request,
                headers=api_headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["success"] is True
                assert "sentiment" in data["analysis"]
                assert "keywords" in data["analysis"]
                assert "entities" in data["analysis"]


@pytest.mark.integration  
class TestWebSocketIntegration:
    """Test WebSocket integration for real-time updates"""
    
    @pytest.fixture
    def websocket_url(self):
        """WebSocket URL for testing"""
        return "ws://localhost:8000/ws"
    
    async def test_websocket_connection(self, websocket_url, websocket_mock):
        """Test WebSocket connection establishment"""
        
        # Mock WebSocket connection
        with patch('aiohttp.ClientSession.ws_connect') as mock_ws_connect:
            mock_ws_connect.return_value.__aenter__ = asyncio.coroutine(lambda self: websocket_mock)
            mock_ws_connect.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(websocket_url) as ws:
                    # Test connection
                    assert ws is not None
                    
                    # Test sending message
                    test_message = {"type": "ping", "data": {}}
                    await ws.send_str(json.dumps(test_message))
                    
                    # Mock response
                    websocket_mock.recv.return_value = json.dumps({
                        "type": "pong",
                        "data": {},
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    response = await ws.recv()
                    response_data = json.loads(response)
                    
                    assert response_data["type"] == "pong"
    
    async def test_real_time_file_updates(self, websocket_url, websocket_mock, sample_file):
        """Test real-time file update notifications"""
        
        with patch('aiohttp.ClientSession.ws_connect') as mock_ws_connect:
            mock_ws_connect.return_value.__aenter__ = asyncio.coroutine(lambda self: websocket_mock)
            mock_ws_connect.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(websocket_url) as ws:
                    # Subscribe to file updates
                    subscribe_message = {
                        "type": "subscribe",
                        "channel": "file_updates",
                        "user_id": sample_file["user_id"]
                    }
                    await ws.send_str(json.dumps(subscribe_message))
                    
                    # Mock file update notification
                    update_notification = {
                        "type": "file_updated",
                        "data": {
                            "file_id": sample_file["id"],
                            "file_name": sample_file["name"],
                            "operation": "modified",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                    
                    websocket_mock.recv.return_value = json.dumps(update_notification)
                    
                    response = await ws.recv()
                    response_data = json.loads(response)
                    
                    assert response_data["type"] == "file_updated"
                    assert response_data["data"]["file_id"] == sample_file["id"]


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database integration across services"""
    
    async def test_transaction_handling(self, mock_database):
        """Test database transaction handling"""
        
        # Mock database operations
        mock_database.execute.return_value = MagicMock()
        mock_database.commit.return_value = None
        mock_database.rollback.return_value = None
        
        try:
            # Simulate transaction
            await mock_database.execute("BEGIN TRANSACTION")
            await mock_database.execute("INSERT INTO files ...")
            await mock_database.execute("INSERT INTO file_metadata ...")
            await mock_database.commit()
            
            # Verify transaction was committed
            mock_database.commit.assert_called_once()
            
        except Exception:
            await mock_database.rollback()
            # Verify rollback was called on error
            mock_database.rollback.assert_called_once()
    
    async def test_concurrent_access(self, mock_database):
        """Test concurrent database access"""
        
        # Mock concurrent operations
        operations = []
        
        async def mock_operation(operation_id):
            mock_database.execute.return_value = f"result_{operation_id}"
            result = await mock_database.execute(f"SELECT * FROM files WHERE id = {operation_id}")
            operations.append(result)
            return result
        
        # Run concurrent operations
        tasks = [mock_operation(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert len(operations) == 5


@pytest.mark.integration
class TestCacheIntegration:
    """Test cache integration across services"""
    
    async def test_cache_consistency(self, mock_redis):
        """Test cache consistency across services"""
        
        # Mock cache operations
        mock_redis.set.return_value = True
        mock_redis.get.return_value = json.dumps({"test": "data"})
        mock_redis.delete.return_value = True
        
        # Test cache set
        cache_key = "test:key:123"
        cache_data = {"test": "data"}
        
        result = mock_redis.set(cache_key, json.dumps(cache_data), 300)
        assert result is True
        
        # Test cache get
        cached_result = mock_redis.get(cache_key)
        assert json.loads(cached_result) == cache_data
        
        # Test cache invalidation
        invalidation_result = mock_redis.delete(cache_key)
        assert invalidation_result is True
    
    async def test_distributed_cache_coordination(self, mock_redis):
        """Test distributed cache coordination"""
        
        # Mock multiple cache instances
        cache_instances = [MagicMock() for _ in range(3)]
        
        for cache in cache_instances:
            cache.set.return_value = True
            cache.get.return_value = json.dumps({"coordinated": "data"})
            cache.delete.return_value = True
        
        # Test coordinated cache operations
        cache_key = "coordinated:key:456"
        cache_data = {"coordinated": "data"}
        
        # Set in all instances
        for cache in cache_instances:
            result = cache.set(cache_key, json.dumps(cache_data), 300)
            assert result is True
        
        # Verify consistency across instances
        for cache in cache_instances:
            cached_result = cache.get(cache_key)
            assert json.loads(cached_result) == cache_data


@pytest.mark.integration
class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""
    
    async def test_file_upload_workflow(self, sample_user, sample_file, api_headers):
        """Test complete file upload workflow"""
        
        # 1. Authenticate user
        with patch('aiohttp.ClientSession.post') as mock_auth:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "access_token": "mock.jwt.token",
                "user": sample_user
            })
            mock_auth.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_auth.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/auth/login",
                    json={"email": sample_user["email"], "password": "test123"}
                ) as response:
                    auth_data = await response.json()
                    access_token = auth_data["access_token"]
        
        # 2. Upload file
        with patch('aiohttp.ClientSession.post') as mock_upload:
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "file": sample_file
            })
            mock_upload.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_upload.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/metadata/files",
                    json=sample_file,
                    headers={"Authorization": f"Bearer {access_token}"}
                ) as response:
                    upload_data = await response.json()
                    file_id = upload_data["file"]["id"]
        
        # 3. Generate embeddings
        with patch('aiohttp.ClientSession.post') as mock_embeddings:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "embedding": {"vector": [0.1] * 1536}
            })
            mock_embeddings.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_embeddings.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/ai/embeddings/generate",
                    json={"file_id": file_id},
                    headers={"Authorization": f"Bearer {access_token}"}
                ) as response:
                    embedding_data = await response.json()
                    assert embedding_data["success"] is True
        
        # 4. Search for uploaded file
        with patch('aiohttp.ClientSession.post') as mock_search:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "files": [sample_file],
                "total_count": 1
            })
            mock_search.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_search.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/metadata/search",
                    json={"query": sample_file["name"]},
                    headers={"Authorization": f"Bearer {access_token}"}
                ) as response:
                    search_data = await response.json()
                    assert search_data["success"] is True
                    assert len(search_data["files"]) == 1
    
    async def test_collaborative_workflow(self, test_data_generator):
        """Test collaborative workflow with multiple users"""
        
        # Generate test users
        users = test_data_generator.generate_users(3)
        
        # Mock user authentication for all users
        user_tokens = {}
        
        for user in users:
            with patch('aiohttp.ClientSession.post') as mock_auth:
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.json = asyncio.coroutine(lambda u=user: {
                    "success": True,
                    "access_token": f"token_{u['id']}",
                    "user": u
                })
                mock_auth.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
                mock_auth.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:8000/auth/login",
                        json={"email": user["email"], "password": "test123"}
                    ) as response:
                        auth_data = await response.json()
                        user_tokens[user["id"]] = auth_data["access_token"]
        
        # Test shared file access
        shared_file = test_data_generator.generate_files(users[0]["id"], 1)[0]
        
        # Owner uploads file
        with patch('aiohttp.ClientSession.post') as mock_upload:
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.json = asyncio.coroutine(lambda: {
                "success": True,
                "file": shared_file
            })
            mock_upload.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
            mock_upload.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
            
            # Owner shares file with other users
            for user in users[1:]:
                with patch('aiohttp.ClientSession.post') as mock_share:
                    mock_response = MagicMock()
                    mock_response.status = 200
                    mock_response.json = asyncio.coroutine(lambda: {
                        "success": True,
                        "message": "File shared successfully"
                    })
                    mock_share.return_value.__aenter__ = asyncio.coroutine(lambda self: mock_response)
                    mock_share.return_value.__aexit__ = asyncio.coroutine(lambda self, *args: None)
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"http://localhost:8000/metadata/files/{shared_file['id']}/share",
                            json={"user_id": user["id"], "permission": "read"},
                            headers={"Authorization": f"Bearer {user_tokens[users[0]['id']]}"}
                        ) as response:
                            share_data = await response.json()
                            assert share_data["success"] is True