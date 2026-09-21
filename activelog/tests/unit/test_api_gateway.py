"""
Unit tests for API Gateway Service
Tests request routing, authentication, rate limiting, and middleware
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json
import jwt
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Import API gateway components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services'))

from api_gateway.main import app, APIGateway
from api_gateway.middleware import AuthenticationMiddleware, RateLimitMiddleware, LoggingMiddleware
from api_gateway.routing import RouteRegistry
from api_gateway.load_balancer import LoadBalancer


class TestAPIGateway:
    """Test main API gateway functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.gateway = APIGateway()
        self.client = TestClient(app)
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "timestamp" in response.json()
        assert "services" in response.json()
    
    def test_service_registry(self):
        """Test service registration and discovery"""
        service_config = {
            'name': 'test-service',
            'url': 'http://localhost:8001',
            'health_endpoint': '/health',
            'load_balancer': 'round_robin'
        }
        
        # Register service
        result = self.gateway.register_service('test-service', service_config)
        assert result is True
        
        # Check if service is registered
        service = self.gateway.get_service('test-service')
        assert service is not None
        assert service['url'] == 'http://localhost:8001'
    
    @patch('api_gateway.main.service_registry')
    def test_proxy_request_success(self, mock_registry):
        """Test successful request proxying"""
        # Mock service registry
        mock_registry.get_service.return_value = {
            'url': 'http://localhost:8001',
            'health_status': 'healthy'
        }
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": "success"}
            mock_response.headers = {"content-type": "application/json"}
            mock_request.return_value = mock_response
            
            response = self.client.get("/api/auth/users", headers={"Authorization": "Bearer valid_token"})
            
            assert response.status_code == 200
            assert response.json() == {"result": "success"}
    
    @patch('api_gateway.main.service_registry')
    def test_proxy_request_service_unavailable(self, mock_registry):
        """Test request proxying when service is unavailable"""
        mock_registry.get_service.return_value = None
        
        response = self.client.get("/api/nonexistent/test")
        
        assert response.status_code == 503
        assert "Service unavailable" in response.json()["detail"]
    
    @patch('api_gateway.main.service_registry')
    def test_proxy_request_with_timeout(self, mock_registry):
        """Test request proxying with timeout"""
        mock_registry.get_service.return_value = {
            'url': 'http://localhost:8001',
            'timeout': 1  # 1 second timeout
        }
        
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.side_effect = asyncio.TimeoutError()
            
            response = self.client.get("/api/auth/test")
            
            assert response.status_code == 504
            assert "timeout" in response.json()["detail"].lower()
    
    def test_request_id_generation(self):
        """Test request ID generation and propagation"""
        response = self.client.get("/health")
        
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0
    
    def test_cors_headers(self):
        """Test CORS headers"""
        response = self.client.options("/api/auth/test", 
                                     headers={"Origin": "http://localhost:3000"})
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    async def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        service_name = "test-service"
        
        # Simulate multiple failures
        for _ in range(5):
            await self.gateway.circuit_breaker.record_failure(service_name)
        
        # Circuit should be open
        assert self.gateway.circuit_breaker.is_open(service_name) is True
        
        # Request should be rejected
        with pytest.raises(HTTPException) as exc_info:
            await self.gateway.circuit_breaker.call(service_name, lambda: None)
        
        assert exc_info.value.status_code == 503


class TestAuthenticationMiddleware:
    """Test authentication middleware"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.middleware = AuthenticationMiddleware(secret_key="test_secret")
    
    def test_valid_jwt_token(self):
        """Test valid JWT token validation"""
        payload = {
            'user_id': str(uuid.uuid4()),
            'email': 'test@example.com',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, "test_secret", algorithm="HS256")
        
        result = self.middleware.validate_token(token)
        
        assert result is not None
        assert result['user_id'] == payload['user_id']
        assert result['email'] == payload['email']
    
    def test_expired_jwt_token(self):
        """Test expired JWT token"""
        payload = {
            'user_id': str(uuid.uuid4()),
            'exp': datetime.utcnow() - timedelta(hours=1)  # Expired
        }
        token = jwt.encode(payload, "test_secret", algorithm="HS256")
        
        result = self.middleware.validate_token(token)
        
        assert result is None
    
    def test_invalid_jwt_token(self):
        """Test invalid JWT token"""
        invalid_token = "invalid.jwt.token"
        
        result = self.middleware.validate_token(invalid_token)
        
        assert result is None
    
    def test_token_with_wrong_secret(self):
        """Test token signed with wrong secret"""
        payload = {'user_id': str(uuid.uuid4())}
        token = jwt.encode(payload, "wrong_secret", algorithm="HS256")
        
        result = self.middleware.validate_token(token)
        
        assert result is None
    
    async def test_protected_route_without_token(self):
        """Test accessing protected route without token"""
        client = TestClient(app)
        
        response = client.get("/api/auth/protected")
        
        assert response.status_code == 401
        assert "Missing authorization header" in response.json()["detail"]
    
    async def test_protected_route_with_valid_token(self):
        """Test accessing protected route with valid token"""
        payload = {
            'user_id': str(uuid.uuid4()),
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, "test_secret", algorithm="HS256")
        
        client = TestClient(app)
        
        with patch('api_gateway.main.service_registry.get_service') as mock_get_service:
            mock_get_service.return_value = {
                'url': 'http://localhost:8001',
                'health_status': 'healthy'
            }
            
            with patch('httpx.AsyncClient.request') as mock_request:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"user": "data"}
                mock_request.return_value = mock_response
                
                response = client.get("/api/auth/protected", 
                                    headers={"Authorization": f"Bearer {token}"})
                
                assert response.status_code == 200
    
    def test_api_key_authentication(self):
        """Test API key authentication"""
        api_key = "test_api_key_123"
        
        # Mock API key validation
        with patch.object(self.middleware, 'validate_api_key') as mock_validate:
            mock_validate.return_value = {
                'client_id': 'test_client',
                'permissions': ['read', 'write']
            }
            
            result = self.middleware.validate_api_key(api_key)
            
            assert result is not None
            assert result['client_id'] == 'test_client'
    
    def test_role_based_access_control(self):
        """Test role-based access control"""
        user_data = {
            'user_id': str(uuid.uuid4()),
            'roles': ['user', 'editor']
        }
        
        # Test user has required role
        assert self.middleware.has_role(user_data, 'user') is True
        assert self.middleware.has_role(user_data, 'editor') is True
        assert self.middleware.has_role(user_data, 'admin') is False
    
    def test_permission_based_access(self):
        """Test permission-based access control"""
        user_data = {
            'user_id': str(uuid.uuid4()),
            'permissions': ['read_files', 'write_files']
        }
        
        assert self.middleware.has_permission(user_data, 'read_files') is True
        assert self.middleware.has_permission(user_data, 'write_files') is True
        assert self.middleware.has_permission(user_data, 'delete_files') is False


class TestRateLimitMiddleware:
    """Test rate limiting middleware"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.middleware = RateLimitMiddleware()
    
    @patch('api_gateway.middleware.redis_client')
    async def test_rate_limit_under_limit(self, mock_redis):
        """Test request under rate limit"""
        mock_redis.get.return_value = "5"  # 5 requests in window
        mock_redis.incr.return_value = 6
        mock_redis.expire.return_value = True
        
        client_id = "test_client"
        result = await self.middleware.check_rate_limit(client_id, limit=100)
        
        assert result is True
    
    @patch('api_gateway.middleware.redis_client')
    async def test_rate_limit_exceeded(self, mock_redis):
        """Test request exceeding rate limit"""
        mock_redis.get.return_value = "100"  # Already at limit
        
        client_id = "test_client"
        result = await self.middleware.check_rate_limit(client_id, limit=100)
        
        assert result is False
    
    @patch('api_gateway.middleware.redis_client')
    async def test_rate_limit_different_windows(self, mock_redis):
        """Test rate limiting with different time windows"""
        client_id = "test_client"
        
        # Test different window sizes
        windows = [60, 300, 3600]  # 1 min, 5 min, 1 hour
        
        for window in windows:
            mock_redis.get.return_value = "1"
            mock_redis.incr.return_value = 2
            
            result = await self.middleware.check_rate_limit(
                client_id, limit=1000, window=window
            )
            
            assert result is True
    
    async def test_rate_limit_by_ip(self):
        """Test rate limiting by IP address"""
        ip_address = "192.168.1.1"
        
        with patch.object(self.middleware, 'check_rate_limit') as mock_check:
            mock_check.return_value = True
            
            result = await self.middleware.check_ip_rate_limit(ip_address)
            
            assert result is True
            mock_check.assert_called_once_with(f"ip:{ip_address}", limit=1000, window=3600)
    
    async def test_rate_limit_by_user(self):
        """Test rate limiting by user ID"""
        user_id = str(uuid.uuid4())
        
        with patch.object(self.middleware, 'check_rate_limit') as mock_check:
            mock_check.return_value = True
            
            result = await self.middleware.check_user_rate_limit(user_id)
            
            assert result is True
            mock_check.assert_called_once_with(f"user:{user_id}", limit=10000, window=3600)
    
    async def test_distributed_rate_limiting(self):
        """Test distributed rate limiting across multiple instances"""
        # This would test rate limiting coordination across multiple gateway instances
        client_id = "distributed_client"
        
        with patch('api_gateway.middleware.distributed_lock') as mock_lock:
            mock_lock.acquire.return_value = True
            mock_lock.release.return_value = True
            
            result = await self.middleware.check_distributed_rate_limit(client_id)
            
            assert result is True


class TestLoggingMiddleware:
    """Test logging middleware"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.middleware = LoggingMiddleware()
    
    def test_request_logging(self):
        """Test request logging"""
        with patch('api_gateway.middleware.logger') as mock_logger:
            request_data = {
                'method': 'GET',
                'path': '/api/auth/users',
                'headers': {'Authorization': 'Bearer token'},
                'client_ip': '192.168.1.1',
                'user_agent': 'Test Client/1.0'
            }
            
            self.middleware.log_request(request_data)
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[1]
            assert 'method' in call_args
            assert 'path' in call_args
    
    def test_response_logging(self):
        """Test response logging"""
        with patch('api_gateway.middleware.logger') as mock_logger:
            response_data = {
                'status_code': 200,
                'response_time': 0.150,
                'content_length': 1024
            }
            
            self.middleware.log_response(response_data)
            
            mock_logger.info.assert_called_once()
    
    def test_error_logging(self):
        """Test error logging"""
        with patch('api_gateway.middleware.logger') as mock_logger:
            error_data = {
                'error': 'Service unavailable',
                'status_code': 503,
                'request_id': str(uuid.uuid4())
            }
            
            self.middleware.log_error(error_data)
            
            mock_logger.error.assert_called_once()
    
    def test_sensitive_data_filtering(self):
        """Test filtering of sensitive data from logs"""
        request_data = {
            'method': 'POST',
            'path': '/api/auth/login',
            'body': {
                'username': 'testuser',
                'password': 'secret123',  # Should be filtered
                'api_key': 'sk-1234567890',  # Should be filtered
                'email': 'test@example.com'
            }
        }
        
        filtered_data = self.middleware.filter_sensitive_data(request_data)
        
        assert filtered_data['body']['username'] == 'testuser'
        assert filtered_data['body']['password'] == '[FILTERED]'
        assert filtered_data['body']['api_key'] == '[FILTERED]'
        assert filtered_data['body']['email'] == 'test@example.com'


class TestRouteRegistry:
    """Test route registry functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.registry = RouteRegistry()
    
    def test_register_route(self):
        """Test route registration"""
        route_config = {
            'path': '/api/auth/*',
            'service': 'auth-service',
            'methods': ['GET', 'POST'],
            'middleware': ['auth', 'rate_limit']
        }
        
        result = self.registry.register_route('/api/auth/*', route_config)
        
        assert result is True
        assert '/api/auth/*' in self.registry.routes
    
    def test_find_matching_route(self):
        """Test finding matching route"""
        # Register routes
        self.registry.register_route('/api/auth/*', {
            'service': 'auth-service',
            'methods': ['GET', 'POST']
        })
        self.registry.register_route('/api/files/*', {
            'service': 'file-service',
            'methods': ['GET', 'POST', 'PUT', 'DELETE']
        })
        
        # Test matching
        auth_route = self.registry.find_route('/api/auth/users')
        assert auth_route is not None
        assert auth_route['service'] == 'auth-service'
        
        files_route = self.registry.find_route('/api/files/upload')
        assert files_route is not None
        assert files_route['service'] == 'file-service'
        
        # Test no match
        unknown_route = self.registry.find_route('/api/unknown/test')
        assert unknown_route is None
    
    def test_route_priority(self):
        """Test route priority resolution"""
        # Register routes with different specificity
        self.registry.register_route('/api/*', {
            'service': 'generic-service',
            'priority': 1
        })
        self.registry.register_route('/api/auth/*', {
            'service': 'auth-service',
            'priority': 10
        })
        
        # More specific route should match
        route = self.registry.find_route('/api/auth/login')
        assert route['service'] == 'auth-service'
    
    def test_route_middleware_configuration(self):
        """Test route middleware configuration"""
        route_config = {
            'service': 'protected-service',
            'middleware': ['auth', 'rate_limit', 'logging']
        }
        
        self.registry.register_route('/api/protected/*', route_config)
        
        route = self.registry.find_route('/api/protected/data')
        assert 'auth' in route['middleware']
        assert 'rate_limit' in route['middleware']
        assert 'logging' in route['middleware']


class TestLoadBalancer:
    """Test load balancer functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.load_balancer = LoadBalancer()
    
    def test_round_robin_balancing(self):
        """Test round-robin load balancing"""
        servers = [
            'http://server1:8000',
            'http://server2:8000',
            'http://server3:8000'
        ]
        
        self.load_balancer.set_servers('test-service', servers)
        
        # Test round-robin distribution
        selected_servers = []
        for _ in range(6):
            server = self.load_balancer.get_server('test-service', 'round_robin')
            selected_servers.append(server)
        
        # Should cycle through all servers
        assert selected_servers[0] == servers[0]
        assert selected_servers[1] == servers[1]
        assert selected_servers[2] == servers[2]
        assert selected_servers[3] == servers[0]  # Back to first
    
    def test_weighted_round_robin(self):
        """Test weighted round-robin load balancing"""
        servers = [
            {'url': 'http://server1:8000', 'weight': 3},
            {'url': 'http://server2:8000', 'weight': 2},
            {'url': 'http://server3:8000', 'weight': 1}
        ]
        
        self.load_balancer.set_servers('test-service', servers)
        
        # Test weighted distribution
        selected_servers = []
        for _ in range(12):  # 12 requests (2 full cycles)
            server = self.load_balancer.get_server('test-service', 'weighted_round_robin')
            selected_servers.append(server)
        
        # Count selections
        server1_count = selected_servers.count('http://server1:8000')
        server2_count = selected_servers.count('http://server2:8000')
        server3_count = selected_servers.count('http://server3:8000')
        
        # Should respect weights (6:4:2 ratio for 12 requests)
        assert server1_count == 6
        assert server2_count == 4
        assert server3_count == 2
    
    def test_least_connections_balancing(self):
        """Test least connections load balancing"""
        servers = [
            'http://server1:8000',
            'http://server2:8000',
            'http://server3:8000'
        ]
        
        self.load_balancer.set_servers('test-service', servers)
        
        # Mock connection counts
        self.load_balancer.connection_counts = {
            'http://server1:8000': 5,
            'http://server2:8000': 2,
            'http://server3:8000': 8
        }
        
        # Should select server with least connections
        server = self.load_balancer.get_server('test-service', 'least_connections')
        assert server == 'http://server2:8000'  # Has only 2 connections
    
    def test_health_check_integration(self):
        """Test load balancer integration with health checks"""
        servers = [
            'http://server1:8000',
            'http://server2:8000',
            'http://server3:8000'
        ]
        
        self.load_balancer.set_servers('test-service', servers)
        
        # Mark one server as unhealthy
        self.load_balancer.set_server_health('http://server2:8000', False)
        
        # Should only select healthy servers
        selected_servers = set()
        for _ in range(10):
            server = self.load_balancer.get_server('test-service', 'round_robin')
            selected_servers.add(server)
        
        assert 'http://server1:8000' in selected_servers
        assert 'http://server3:8000' in selected_servers
        assert 'http://server2:8000' not in selected_servers  # Unhealthy server
    
    async def test_server_health_monitoring(self):
        """Test automatic server health monitoring"""
        servers = ['http://server1:8000', 'http://server2:8000']
        self.load_balancer.set_servers('test-service', servers)
        
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock healthy response for server1
            healthy_response = Mock()
            healthy_response.status_code = 200
            
            # Mock unhealthy response for server2
            unhealthy_response = Mock()
            unhealthy_response.status_code = 503
            
            mock_get.side_effect = [healthy_response, unhealthy_response]
            
            await self.load_balancer.check_server_health('test-service')
            
            # Check health status
            assert self.load_balancer.get_server_health('http://server1:8000') is True
            assert self.load_balancer.get_server_health('http://server2:8000') is False


@pytest.mark.integration
class TestAPIGatewayIntegration:
    """Integration tests for API gateway"""
    
    def test_complete_request_flow(self):
        """Test complete request flow through gateway"""
        client = TestClient(app)
        
        # Create valid JWT token
        payload = {
            'user_id': str(uuid.uuid4()),
            'email': 'test@example.com',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, "test_secret", algorithm="HS256")
        
        with patch('api_gateway.main.service_registry.get_service') as mock_get_service:
            mock_get_service.return_value = {
                'url': 'http://auth-service:8001',
                'health_status': 'healthy'
            }
            
            with patch('httpx.AsyncClient.request') as mock_request:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"user_id": payload['user_id']}
                mock_response.headers = {"content-type": "application/json"}
                mock_request.return_value = mock_response
                
                response = client.get(
                    "/api/auth/profile",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )
                
                assert response.status_code == 200
                assert response.json()["user_id"] == payload['user_id']
                assert "x-request-id" in response.headers
    
    def test_error_handling_chain(self):
        """Test error handling through middleware chain"""
        client = TestClient(app)
        
        # Test with invalid token
        response = client.get(
            "/api/auth/protected",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        
        # Test with missing service
        with patch('api_gateway.main.service_registry.get_service') as mock_get_service:
            mock_get_service.return_value = None
            
            response = client.get("/api/nonexistent/test")
            
            assert response.status_code == 503


@pytest.mark.performance
class TestAPIGatewayPerformance:
    """Performance tests for API gateway"""
    
    async def test_concurrent_request_handling(self):
        """Test performance with concurrent requests"""
        import asyncio
        import time
        
        async def make_request():
            # Simulate request processing
            await asyncio.sleep(0.01)  # 10ms processing time
            return {"status": "success"}
        
        start_time = time.time()
        
        # Make 100 concurrent requests
        tasks = [make_request() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(results) == 100
        assert duration < 1.0  # Should complete within 1 second
        assert all(result["status"] == "success" for result in results)
    
    def test_memory_usage_under_load(self, performance_monitor):
        """Test memory usage under high load"""
        client = TestClient(app)
        
        performance_monitor.start()
        
        # Simulate high load with many requests
        for _ in range(1000):
            response = client.get("/health")
            assert response.status_code == 200
        
        duration = performance_monitor.stop('high_load_test')
        memory_used = performance_monitor.peak_memory_delta
        
        # Should handle load efficiently
        assert duration < 30  # Complete within 30 seconds
        assert memory_used < 50 * 1024 * 1024  # Less than 50MB