#!/usr/bin/env python3
"""
Comprehensive test suite for PersonalLog.ai Backend API
Tests all endpoints with proper authentication, validation, and edge cases
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
import tempfile
import os
from datetime import datetime, timedelta
import jwt

# Import the app and backend
import sys
sys.path.append('..')
from main import app, backend, SecurityManager

# Test configuration
TEST_USER_DATA = {
    "email": "test@personallog.ai",
    "name": "Test User",
    "password": "SecurePass123!"
}

TEST_ENTRY_DATA = {
    "title": "Test Entry",
    "content": "This is a test journal entry for automated testing.",
    "tags": ["test", "automation"],
    "mood": "happy",
    "privacy_level": "private"
}

class TestPersonalLogAPI:
    """Comprehensive API test suite"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment with clean database"""
        # Create test database in memory
        backend.db_path = ":memory:"
        backend.init_database()
        
        self.client = TestClient(app)
        self.test_user_token = None
        self.test_user_id = None
        
        yield
        
        # Cleanup after tests
        try:
            backend.get_db_connection().close()
        except:
            pass
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["service"] == "PersonalLog.ai Backend"
        assert data["version"] == "2.0.0"
        assert "timestamp" in data
    
    def test_user_registration_success(self):
        """Test successful user registration"""
        response = self.client.post("/api/auth/register", json=TEST_USER_DATA)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user_profile" in data
        
        # Store for other tests
        self.test_user_token = data["access_token"]
        self.test_user_id = data["user_profile"]["id"]
        
        # Verify user profile
        profile = data["user_profile"]
        assert profile["email"] == TEST_USER_DATA["email"]
        assert profile["name"] == TEST_USER_DATA["name"]
        assert profile["tier"] == "free"
        assert profile["is_active"] is True
    
    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        # First registration
        self.client.post("/api/auth/register", json=TEST_USER_DATA)
        
        # Second registration with same email
        response = self.client.post("/api/auth/register", json=TEST_USER_DATA)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_user_registration_invalid_password(self):
        """Test registration with invalid password"""
        invalid_data = TEST_USER_DATA.copy()
        invalid_data["password"] = "weak"
        
        response = self.client.post("/api/auth/register", json=invalid_data)
        assert response.status_code == 422
    
    def test_user_login_success(self):
        """Test successful user login"""
        # Register user first
        self.client.post("/api/auth/register", json=TEST_USER_DATA)
        
        # Login
        login_data = {
            "email": TEST_USER_DATA["email"],
            "password": TEST_USER_DATA["password"]
        }
        
        response = self.client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Store for other tests
        self.test_user_token = data["access_token"]
        self.test_user_id = data["user_profile"]["id"]
    
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = self.client.post("/api/auth/login", json=login_data)
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()
    
    def test_get_user_profile_success(self):
        """Test getting user profile with valid token"""
        # Setup authenticated user
        self._setup_authenticated_user()
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        response = self.client.get("/api/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_USER_DATA["email"]
        assert data["name"] == TEST_USER_DATA["name"]
    
    def test_get_user_profile_unauthorized(self):
        """Test getting user profile without token"""
        response = self.client.get("/api/users/me")
        assert response.status_code == 403
    
    def test_create_entry_success(self):
        """Test creating journal entry successfully"""
        self._setup_authenticated_user()
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        response = self.client.post("/api/entries", 
                                  json=TEST_ENTRY_DATA, 
                                  headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == TEST_ENTRY_DATA["title"]
        assert data["content"] == TEST_ENTRY_DATA["content"]
        assert data["tags"] == TEST_ENTRY_DATA["tags"]
        assert data["mood"] == TEST_ENTRY_DATA["mood"]
        assert data["user_id"] == self.test_user_id
        assert "id" in data
        assert "created_at" in data
    
    def test_create_entry_invalid_data(self):
        """Test creating entry with invalid data"""
        self._setup_authenticated_user()
        
        invalid_entry = {
            "title": "",  # Empty title
            "content": "x" * 60000,  # Too long content
            "mood": "invalid_mood"  # Invalid mood
        }
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        response = self.client.post("/api/entries", 
                                  json=invalid_entry, 
                                  headers=headers)
        
        assert response.status_code == 422
    
    def test_get_entries_success(self):
        """Test retrieving user entries"""
        self._setup_authenticated_user()
        
        # Create a test entry first
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        self.client.post("/api/entries", json=TEST_ENTRY_DATA, headers=headers)
        
        # Get entries
        response = self.client.get("/api/entries", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert len(data["entries"]) >= 1
        assert data["entries"][0]["title"] == TEST_ENTRY_DATA["title"]
    
    def test_get_entries_with_filters(self):
        """Test retrieving entries with filters"""
        self._setup_authenticated_user()
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Create multiple entries with different moods
        entry1 = TEST_ENTRY_DATA.copy()
        entry1["mood"] = "happy"
        entry1["title"] = "Happy Entry"
        
        entry2 = TEST_ENTRY_DATA.copy()
        entry2["mood"] = "sad"
        entry2["title"] = "Sad Entry"
        
        self.client.post("/api/entries", json=entry1, headers=headers)
        self.client.post("/api/entries", json=entry2, headers=headers)
        
        # Filter by mood
        response = self.client.get("/api/entries?mood=happy", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["entries"]) >= 1
        assert all(entry["mood"] == "happy" for entry in data["entries"])
    
    def test_update_entry_success(self):
        """Test updating journal entry"""
        self._setup_authenticated_user()
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Create entry
        create_response = self.client.post("/api/entries", 
                                         json=TEST_ENTRY_DATA, 
                                         headers=headers)
        entry_id = create_response.json()["id"]
        
        # Update entry
        updates = {
            "title": "Updated Title",
            "content": "Updated content for the entry.",
            "mood": "peaceful"
        }
        
        response = self.client.put(f"/api/entries/{entry_id}", 
                                 json=updates, 
                                 headers=headers)
        
        assert response.status_code == 200
        assert "updated successfully" in response.json()["message"]
    
    def test_delete_entry_success(self):
        """Test deleting journal entry"""
        self._setup_authenticated_user()
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Create entry
        create_response = self.client.post("/api/entries", 
                                         json=TEST_ENTRY_DATA, 
                                         headers=headers)
        entry_id = create_response.json()["id"]
        
        # Delete entry
        response = self.client.delete(f"/api/entries/{entry_id}", headers=headers)
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify entry is not accessible
        get_response = self.client.get(f"/api/entries/{entry_id}", headers=headers)
        assert get_response.status_code == 404
    
    def test_sync_data_success(self):
        """Test data synchronization"""
        self._setup_authenticated_user()
        
        sync_request = {
            "user_id": self.test_user_id,
            "last_sync_version": 0,
            "device_id": "test_device_123",
            "device_type": "web",
            "client_version": "2.0.0",
            "local_changes": []
        }
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        response = self.client.post("/api/sync", 
                                  json=sync_request, 
                                  headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "sync_version" in data
        assert "server_changes" in data
        assert "applied_changes" in data
    
    def test_get_insights_success(self):
        """Test retrieving AI insights"""
        self._setup_authenticated_user()
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Create entry first
        create_response = self.client.post("/api/entries", 
                                         json=TEST_ENTRY_DATA, 
                                         headers=headers)
        entry_id = create_response.json()["id"]
        
        # Mock AI insights in database
        conn = backend.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_insights (id, entry_id, user_id, insight_type, content, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("test_insight_123", entry_id, self.test_user_id, "sentiment", "Positive sentiment", 0.9))
        conn.commit()
        conn.close()
        
        # Get insights
        response = self.client.get(f"/api/insights/{entry_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
        assert len(data["insights"]) >= 1
    
    def test_get_user_analytics_success(self):
        """Test retrieving user analytics"""
        self._setup_authenticated_user()
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Create some entries for analytics
        for i in range(3):
            entry = TEST_ENTRY_DATA.copy()
            entry["title"] = f"Entry {i+1}"
            self.client.post("/api/entries", json=entry, headers=headers)
        
        response = self.client.get("/api/analytics/user", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "writing_stats" in data
        assert "mood_distribution" in data
        assert "writing_patterns" in data
        assert data["writing_stats"]["total_entries"] >= 3
    
    def test_create_backup_success(self):
        """Test creating user backup"""
        self._setup_authenticated_user()
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Create some entries first
        self.client.post("/api/entries", json=TEST_ENTRY_DATA, headers=headers)
        
        backup_request = {
            "user_id": self.test_user_id,
            "backup_type": "full",
            "include_insights": True,
            "encryption_enabled": True
        }
        
        response = self.client.post("/api/backup", 
                                  json=backup_request, 
                                  headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "backup_id" in data
        assert "message" in data
        assert data["entries_count"] >= 1
    
    def test_rate_limiting(self):
        """Test rate limiting on endpoints"""
        # Try to hit registration endpoint multiple times
        responses = []
        for i in range(7):  # Exceed 5/minute limit
            test_data = TEST_USER_DATA.copy()
            test_data["email"] = f"test{i}@example.com"
            response = self.client.post("/api/auth/register", json=test_data)
            responses.append(response.status_code)
        
        # Should get rate limited
        assert 429 in responses
    
    def test_websocket_connection(self):
        """Test WebSocket connection"""
        self._setup_authenticated_user()
        
        with self.client.websocket_connect(f"/ws/{self.test_user_id}") as websocket:
            # Should receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["data"]["user_id"] == self.test_user_id
            
            # Send ping
            websocket.send_json({"type": "ping"})
            pong = websocket.receive_json()
            assert pong["type"] == "pong"
    
    def test_metrics_endpoint(self):
        """Test system metrics endpoint"""
        response = self.client.get("/api/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data
        assert "metrics" in data
        assert "database" in data
    
    def test_security_audit_logging(self):
        """Test that security events are logged"""
        # Failed login should be logged
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = self.client.post("/api/auth/login", json=login_data)
        assert response.status_code == 401
        
        # Check if security event was logged (would need to check database in real test)
        conn = backend.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM security_audit 
            WHERE event_type = 'login_attempt_failed' 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        audit_log = cursor.fetchone()
        conn.close()
        
        assert audit_log is not None
        assert audit_log['event_type'] == 'login_attempt_failed'
    
    def test_input_sanitization(self):
        """Test input sanitization and XSS protection"""
        self._setup_authenticated_user()
        
        # Try to create entry with malicious script
        malicious_entry = {
            "title": "<script>alert('XSS')</script>",
            "content": "This content has <script>alert('XSS')</script> in it",
            "tags": ["<script>", "normal_tag"],
            "mood": "happy"
        }
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        response = self.client.post("/api/entries", 
                                  json=malicious_entry, 
                                  headers=headers)
        
        # Should be rejected due to validation
        assert response.status_code == 422
    
    def _setup_authenticated_user(self):
        """Helper method to setup authenticated test user"""
        if not self.test_user_token:
            # Register user
            response = self.client.post("/api/auth/register", json=TEST_USER_DATA)
            if response.status_code == 200:
                data = response.json()
                self.test_user_token = data["access_token"]
                self.test_user_id = data["user_profile"]["id"]
            else:
                # Try login instead
                login_data = {
                    "email": TEST_USER_DATA["email"],
                    "password": TEST_USER_DATA["password"]
                }
                login_response = self.client.post("/api/auth/login", json=login_data)
                if login_response.status_code == 200:
                    data = login_response.json()
                    self.test_user_token = data["access_token"]
                    self.test_user_id = data["user_profile"]["id"]

class TestSecurityFeatures:
    """Test security-specific features"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "TestPassword123!"
        hashed = SecurityManager.hash_password(password)
        
        assert hashed != password
        assert SecurityManager.verify_password(password, hashed)
        assert not SecurityManager.verify_password("wrong_password", hashed)
    
    def test_jwt_token_generation(self):
        """Test JWT token generation and verification"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = SecurityManager.create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token
        payload = SecurityManager.verify_token(token, "access")
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
    
    def test_data_encryption(self):
        """Test data encryption and decryption"""
        original_data = "This is sensitive journal content"
        encrypted = SecurityManager.encrypt_data(original_data)
        
        assert encrypted != original_data
        
        decrypted = SecurityManager.decrypt_data(encrypted)
        assert decrypted == original_data

# Performance tests
class TestPerformance:
    """Test performance aspects"""
    
    def test_database_performance(self):
        """Test database query performance"""
        import time
        
        # Setup test data
        backend.init_database()
        conn = backend.get_db_connection()
        cursor = conn.cursor()
        
        # Time a simple query
        start_time = time.time()
        cursor.execute('SELECT COUNT(*) FROM users')
        end_time = time.time()
        
        conn.close()
        
        # Should be very fast for simple queries
        assert (end_time - start_time) < 0.1
    
    def test_cache_performance(self):
        """Test caching system performance"""
        cache = backend.cache
        
        # Test cache set/get performance
        import time
        
        start_time = time.time()
        for i in range(1000):
            cache.set('test', f'key_{i}', f'value_{i}')
        
        for i in range(1000):
            value = cache.get('test', f'key_{i}')
            assert value == f'value_{i}'
        
        end_time = time.time()
        
        # Should be fast for 1000 operations
        assert (end_time - start_time) < 1.0

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])