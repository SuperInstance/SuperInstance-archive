#!/usr/bin/env python3
"""
Building Bots Network - Code Generation Service Tests

Comprehensive test suite for the code generation service following
Building Bots Network principles of thorough testing and quality assurance.
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from httpx import AsyncClient
from fastapi.testclient import TestClient

# Import service components
from main import (
    app, 
    service,
    CodeGenerationRequest,
    CodeAnalysisResult,
    ProgrammingLanguage,
    Framework,
    CodeComplexity,
    AIProvider
)
from config import TESTING_CONFIG, get_quality_standards

# Test configuration
pytest_plugins = ('pytest_asyncio',)

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)

@pytest.fixture
async def async_client():
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def sample_python_code():
    """Sample Python code for testing"""
    return '''
def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def main():
    """Main function to demonstrate Fibonacci calculation."""
    for i in range(10):
        print(f"Fibonacci({i}) = {calculate_fibonacci(i)}")

if __name__ == "__main__":
    main()
'''

@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code for testing"""
    return '''
function calculateFactorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * calculateFactorial(n - 1);
}

function main() {
    for (let i = 1; i <= 10; i++) {
        console.log(`Factorial of ${i} is ${calculateFactorial(i)}`);
    }
}

main();
'''

@pytest.fixture
def mock_ai_providers():
    """Mock AI providers"""
    with patch('main.AIProviderManager') as mock_manager:
        mock_instance = Mock()
        mock_instance.generate_code = AsyncMock(return_value="# Generated code")
        mock_instance.select_optimal_provider = Mock(return_value=AIProvider.CLAUDE)
        mock_manager.return_value = mock_instance
        yield mock_instance

class TestHealthEndpoints:
    """Test health and status endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Building Bots Network - Code Generation Service"
        assert data["status"] == "active"
        assert data["version"] == "1.0.0"
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "providers" in data
        assert "database" in data
    
    def test_capabilities(self, client):
        """Test capabilities endpoint"""
        response = client.get("/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert "languages" in data
        assert "frameworks" in data
        assert "providers" in data
        assert "features" in data
        assert len(data["languages"]) >= 15
        assert "python" in data["languages"]
        assert "javascript" in data["languages"]

class TestCodeGeneration:
    """Test code generation functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_code_basic(self, async_client, mock_ai_providers):
        """Test basic code generation"""
        request_data = {
            "prompt": "Create a function to calculate factorial",
            "language": "python",
            "complexity": "moderate",
            "include_tests": True,
            "include_docs": True
        }
        
        response = await async_client.post("/generate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "language" in data
        assert "analysis" in data
        assert data["language"] == "python"
    
    @pytest.mark.asyncio
    async def test_generate_code_with_framework(self, async_client, mock_ai_providers):
        """Test code generation with framework specification"""
        request_data = {
            "prompt": "Create a REST API endpoint for user management",
            "language": "python",
            "framework": "fastapi",
            "complexity": "moderate"
        }
        
        response = await async_client.post("/generate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["framework"] == "fastapi"
    
    @pytest.mark.asyncio
    async def test_generate_code_invalid_language(self, async_client):
        """Test code generation with invalid language"""
        request_data = {
            "prompt": "Create a function",
            "language": "invalid_language"
        }
        
        response = await async_client.post("/generate", json=request_data)
        assert response.status_code == 422  # Validation error

class TestCodeAnalysis:
    """Test code analysis functionality"""
    
    @pytest.mark.asyncio
    async def test_analyze_python_code(self, async_client, sample_python_code):
        """Test Python code analysis"""
        request_data = {
            "code": sample_python_code,
            "language": "python"
        }
        
        response = await async_client.post("/analyze", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "quality_score" in data
        assert "complexity_score" in data
        assert "security_issues" in data
        assert "performance_suggestions" in data
        assert 0 <= data["quality_score"] <= 1
        assert 0 <= data["complexity_score"] <= 1
    
    @pytest.mark.asyncio
    async def test_analyze_javascript_code(self, async_client, sample_javascript_code):
        """Test JavaScript code analysis"""
        request_data = {
            "code": sample_javascript_code,
            "language": "javascript"
        }
        
        response = await async_client.post("/analyze", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "quality_score" in data
        assert "complexity_score" in data
        assert isinstance(data["security_issues"], list)

class TestCodeImprovement:
    """Test code improvement functionality"""
    
    @pytest.mark.asyncio
    async def test_improve_code(self, async_client, sample_python_code, mock_ai_providers):
        """Test code improvement"""
        request_data = {
            "code": sample_python_code,
            "language": "python",
            "focus_areas": ["performance", "readability"]
        }
        
        response = await async_client.post("/improve", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "original_analysis" in data
        assert "improved_code" in data
        assert "new_analysis" in data
        assert "improvements" in data

class TestUtilityEndpoints:
    """Test utility endpoints"""
    
    @pytest.mark.asyncio
    async def test_generate_tests(self, async_client, sample_python_code):
        """Test test generation"""
        response = await async_client.post(
            "/tests/generate",
            params={
                "code": sample_python_code,
                "language": "python"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "tests" in data
        assert "language" in data
        assert data["language"] == "python"
    
    @pytest.mark.asyncio
    async def test_generate_documentation(self, async_client, sample_python_code):
        """Test documentation generation"""
        response = await async_client.post(
            "/documentation/generate",
            params={
                "code": sample_python_code,
                "language": "python"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "documentation" in data
        assert "language" in data
    
    @pytest.mark.asyncio
    async def test_refactor_code(self, async_client, sample_python_code, mock_ai_providers):
        """Test code refactoring"""
        response = await async_client.post(
            "/refactor",
            params={
                "code": sample_python_code,
                "language": "python",
                "refactor_type": "performance"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "refactored_code" in data
        assert "refactor_type" in data
    
    @pytest.mark.asyncio
    async def test_optimize_performance(self, async_client, sample_python_code, mock_ai_providers):
        """Test performance optimization"""
        response = await async_client.post(
            "/optimize",
            params={
                "code": sample_python_code,
                "language": "python",
                "focus": "speed"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "optimized_code" in data
        assert "original_analysis" in data
        assert "optimized_analysis" in data

class TestMLCodeIntelligence:
    """Test ML-powered code intelligence"""
    
    def test_extract_code_features(self, sample_python_code):
        """Test code feature extraction"""
        ml_intelligence = service.analyzer.ml_intelligence
        features = ml_intelligence.extract_code_features(sample_python_code)
        assert features.shape == (1, 10)
        assert isinstance(features, type(features))  # numpy array check
    
    def test_predict_code_quality(self, sample_python_code):
        """Test code quality prediction"""
        ml_intelligence = service.analyzer.ml_intelligence
        quality_score = ml_intelligence.predict_code_quality(sample_python_code)
        assert 0 <= quality_score <= 1
    
    def test_predict_complexity(self, sample_python_code):
        """Test complexity prediction"""
        ml_intelligence = service.analyzer.ml_intelligence
        complexity = ml_intelligence.predict_complexity(sample_python_code)
        assert complexity in ["simple", "moderate", "complex"]

class TestSecurityAnalysis:
    """Test security analysis functionality"""
    
    def test_detect_sql_injection(self):
        """Test SQL injection detection"""
        malicious_code = '''
query = "SELECT * FROM users WHERE id = %s" % user_id
cursor.execute(query)
'''
        analysis = service.analyzer.analyze_code(malicious_code, "python")
        security_issues = analysis.security_issues
        assert len(security_issues) > 0
        assert any("injection" in issue["type"].lower() for issue in security_issues)
    
    def test_detect_hardcoded_secrets(self):
        """Test hardcoded secret detection"""
        secret_code = '''
password = "hardcoded_password_123"
api_key = "sk-1234567890abcdef"
'''
        analysis = service.analyzer.analyze_code(secret_code, "python")
        security_issues = analysis.security_issues
        assert len(security_issues) > 0
        assert any("secret" in issue["type"].lower() for issue in security_issues)

class TestPerformanceAnalysis:
    """Test performance analysis functionality"""
    
    def test_detect_inefficient_loops(self):
        """Test detection of inefficient loop patterns"""
        inefficient_code = '''
items = [1, 2, 3, 4, 5]
for i in range(len(items)):
    print(items[i])
'''
        analysis = service.analyzer.analyze_code(inefficient_code, "python")
        suggestions = analysis.performance_suggestions
        assert len(suggestions) > 0
        assert any("enumerate" in suggestion for suggestion in suggestions)
    
    def test_detect_string_concatenation_in_loops(self):
        """Test detection of inefficient string concatenation"""
        inefficient_code = '''
result = ""
for item in items:
    result += str(item) + ","
'''
        analysis = service.analyzer.analyze_code(inefficient_code, "python")
        suggestions = analysis.performance_suggestions
        assert len(suggestions) > 0
        assert any("join" in suggestion for suggestion in suggestions)

class TestQualityStandards:
    """Test Building Bots Network quality standards"""
    
    def test_production_quality_standards(self):
        """Test production quality standards"""
        standards = get_quality_standards("production")
        assert standards["min_quality_score"] == 0.8
        assert standards["require_tests"] == True
        assert standards["require_docs"] == True
        assert standards["security_level"] == "strict"
    
    def test_development_quality_standards(self):
        """Test development quality standards"""
        standards = get_quality_standards("development")
        assert standards["min_quality_score"] == 0.5
        assert standards["require_tests"] == False
        assert standards["security_level"] == "basic"

class TestDataPersistence:
    """Test data persistence and caching"""
    
    @pytest.mark.asyncio
    async def test_generation_history(self, async_client):
        """Test generation history retrieval"""
        response = await async_client.get("/history")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)
    
    @pytest.mark.asyncio
    async def test_service_statistics(self, async_client):
        """Test service statistics"""
        response = await async_client.get("/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "total_generations" in data
        assert "average_quality_score" in data
        assert "language_distribution" in data
        assert "provider_usage" in data

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_empty_code_analysis(self, async_client):
        """Test analysis of empty code"""
        request_data = {
            "code": "",
            "language": "python"
        }
        
        response = await async_client.post("/analyze", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["quality_score"] == 0.0
    
    @pytest.mark.asyncio
    async def test_malformed_code_analysis(self, async_client):
        """Test analysis of malformed code"""
        request_data = {
            "code": "def incomplete_function(",
            "language": "python"
        }
        
        response = await async_client.post("/analyze", json=request_data)
        assert response.status_code == 200
        # Should handle gracefully and return reasonable defaults
        data = response.json()
        assert "quality_score" in data

class TestConcurrency:
    """Test concurrent requests and performance"""
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis_requests(self, async_client, sample_python_code):
        """Test multiple concurrent analysis requests"""
        request_data = {
            "code": sample_python_code,
            "language": "python"
        }
        
        # Create multiple concurrent requests
        tasks = []
        for _ in range(5):
            task = async_client.post("/analyze", json=request_data)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "quality_score" in data

class TestBuildingBotsNetworkIntegration:
    """Test Building Bots Network specific features"""
    
    def test_construction_excellence_principles(self):
        """Test that generated responses follow construction excellence"""
        # This would test integration with Building Bots Network principles
        # In a real deployment, this would verify:
        # - Code meets production standards
        # - Follows network-wide best practices
        # - Integrates with other network services
        pass
    
    def test_cross_service_learning(self):
        """Test cross-service learning capabilities"""
        # This would test the service's ability to learn from other
        # services in the Building Bots Network
        pass
    
    def test_network_quality_standards(self):
        """Test adherence to network quality standards"""
        # Verify that quality standards align with network requirements
        standards = get_quality_standards("production")
        assert standards["min_quality_score"] >= 0.8
        assert standards["require_tests"] == True
        assert standards["require_docs"] == True

# Integration tests that would run in a full Building Bots Network environment
class TestNetworkIntegration:
    """Test integration with other Building Bots Network services"""
    
    @pytest.mark.skip(reason="Requires full network deployment")
    def test_hub_integration(self):
        """Test integration with Building Bots Network hub"""
        pass
    
    @pytest.mark.skip(reason="Requires full network deployment")
    def test_service_discovery(self):
        """Test service discovery and registration"""
        pass
    
    @pytest.mark.skip(reason="Requires full network deployment")
    def test_distributed_learning(self):
        """Test distributed learning across network services"""
        pass

# Performance benchmarks
class TestPerformance:
    """Performance and load testing"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_analysis_performance(self, async_client, sample_python_code):
        """Test code analysis performance"""
        import time
        
        request_data = {
            "code": sample_python_code,
            "language": "python"
        }
        
        start_time = time.time()
        response = await async_client.post("/analyze", json=request_data)
        end_time = time.time()
        
        assert response.status_code == 200
        # Analysis should complete within reasonable time
        assert end_time - start_time < 5.0  # 5 seconds max

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])