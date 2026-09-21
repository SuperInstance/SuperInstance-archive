"""
Load testing configuration for ActiveLog using Locust
Tests system performance under various load conditions
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActiveLogUser(FastHttpUser):
    """Simulates a typical ActiveLog user"""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.user_id = None
        self.user_files = []
        self.session_data = {}
    
    def on_start(self):
        """Called when user starts - login and setup"""
        self.login()
        self.get_user_profile()
    
    def on_stop(self):
        """Called when user stops - cleanup"""
        if self.access_token:
            self.logout()
    
    def login(self):
        """Authenticate user"""
        login_data = {
            "email": f"loadtest_{random.randint(1, 10000)}@example.com",
            "password": "LoadTest123!",
            "device_info": {
                "platform": "web",
                "browser": "chrome",
                "version": "108.0"
            }
        }
        
        with self.client.post(
            "/auth/login",
            json=login_data,
            catch_response=True,
            name="auth_login"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        self.access_token = data.get("access_token")
                        self.user_id = data.get("user", {}).get("id")
                        self.session_data = data
                        response.success()
                    else:
                        response.failure(f"Login failed: {data.get('error', 'Unknown error')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 401:
                # For load testing, create user if doesn't exist
                self.register_user(login_data)
                # Retry login
                self.login()
            else:
                response.failure(f"Login failed with status {response.status_code}")
    
    def register_user(self, login_data):
        """Register new user for load testing"""
        registration_data = {
            "email": login_data["email"],
            "password": login_data["password"],
            "name": f"Load Test User {random.randint(1, 10000)}"
        }
        
        with self.client.post(
            "/auth/register",
            json=registration_data,
            catch_response=True,
            name="auth_register"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Registration failed with status {response.status_code}")
    
    def logout(self):
        """Logout user"""
        if not self.access_token:
            return
        
        with self.client.post(
            "/auth/logout",
            json={"session_id": self.session_data.get("session_id")},
            headers=self.get_auth_headers(),
            catch_response=True,
            name="auth_logout"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Logout failed with status {response.status_code}")
    
    def get_auth_headers(self):
        """Get authentication headers"""
        if self.access_token:
            return {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        return {"Content-Type": "application/json"}
    
    @task(3)
    def get_user_profile(self):
        """Get user profile information"""
        if not self.access_token:
            return
        
        with self.client.get(
            "/auth/me",
            headers=self.get_auth_headers(),
            catch_response=True,
            name="get_user_profile"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get profile failed with status {response.status_code}")
    
    @task(5)
    def list_user_files(self):
        """List user files"""
        if not self.access_token:
            return
        
        params = {
            "limit": random.randint(10, 50),
            "offset": random.randint(0, 100)
        }
        
        with self.client.get(
            f"/metadata/users/{self.user_id}/files",
            params=params,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="list_user_files"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        self.user_files = data.get("files", [])
                        response.success()
                    else:
                        response.failure(f"List files failed: {data.get('error')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"List files failed with status {response.status_code}")
    
    @task(4)
    def search_files(self):
        """Search for files"""
        if not self.access_token:
            return
        
        search_queries = [
            "document", "image", "presentation", "spreadsheet",
            "report", "analysis", "meeting", "project",
            "data", "research", "notes", "draft"
        ]
        
        search_data = {
            "query": random.choice(search_queries),
            "file_type": random.choice(["document", "image", "video", "audio", ""]),
            "limit": random.randint(5, 20),
            "similarity_threshold": random.uniform(0.5, 0.9)
        }
        
        with self.client.post(
            "/metadata/search",
            json=search_data,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="search_files"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        response.success()
                    else:
                        response.failure(f"Search failed: {data.get('error')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Search failed with status {response.status_code}")
    
    @task(2)
    def create_file_metadata(self):
        """Create new file metadata"""
        if not self.access_token:
            return
        
        file_types = ["document", "image", "video", "audio", "archive"]
        file_extensions = {
            "document": [".pdf", ".docx", ".txt", ".md"],
            "image": [".jpg", ".png", ".gif", ".svg"],
            "video": [".mp4", ".avi", ".mov", ".mkv"],
            "audio": [".mp3", ".wav", ".flac", ".ogg"],
            "archive": [".zip", ".tar", ".rar", ".7z"]
        }
        
        file_type = random.choice(file_types)
        extension = random.choice(file_extensions[file_type])
        
        file_data = {
            "name": f"loadtest_file_{random.randint(1, 10000)}{extension}",
            "path": f"/loadtest/files/loadtest_file_{random.randint(1, 10000)}{extension}",
            "size": random.randint(1024, 1024*1024*10),  # 1KB to 10MB
            "file_type": file_type,
            "mime_type": f"application/{file_type}",
            "checksum": f"checksum_{random.randint(100000, 999999)}",
            "sync_status": random.choice(["local", "synced", "cloud"]),
            "metadata": {
                "title": f"Load Test File {random.randint(1, 1000)}",
                "description": "Generated for load testing",
                "tags": random.sample(["test", "load", "performance", "automated"], 2)
            }
        }
        
        with self.client.post(
            "/metadata/files",
            json=file_data,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="create_file_metadata"
        ) as response:
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    if data.get("success"):
                        file_id = data.get("file", {}).get("id")
                        if file_id:
                            self.user_files.append(data["file"])
                        response.success()
                    else:
                        response.failure(f"Create file failed: {data.get('error')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Create file failed with status {response.status_code}")
    
    @task(2)
    def get_file_metadata(self):
        """Get specific file metadata"""
        if not self.access_token or not self.user_files:
            return
        
        file_info = random.choice(self.user_files)
        file_id = file_info.get("id")
        
        if not file_id:
            return
        
        with self.client.get(
            f"/metadata/files/{file_id}",
            headers=self.get_auth_headers(),
            catch_response=True,
            name="get_file_metadata"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        response.success()
                    else:
                        response.failure(f"Get file failed: {data.get('error')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Get file failed with status {response.status_code}")
    
    @task(1)
    def update_file_metadata(self):
        """Update file metadata"""
        if not self.access_token or not self.user_files:
            return
        
        file_info = random.choice(self.user_files)
        file_id = file_info.get("id")
        
        if not file_id:
            return
        
        update_data = {
            "name": f"updated_loadtest_file_{random.randint(1, 10000)}.pdf",
            "metadata": {
                "updated_at": datetime.utcnow().isoformat(),
                "update_reason": "load_test_update"
            }
        }
        
        with self.client.put(
            f"/metadata/files/{file_id}",
            json=update_data,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="update_file_metadata"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        response.success()
                    else:
                        response.failure(f"Update file failed: {data.get('error')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Update file failed with status {response.status_code}")
    
    @task(3)
    def semantic_search(self):
        """Perform semantic search"""
        if not self.access_token:
            return
        
        search_queries = [
            "machine learning algorithms",
            "data analysis techniques",
            "project management best practices",
            "financial report analysis",
            "marketing strategy documents",
            "technical documentation",
            "research papers on AI",
            "business process optimization"
        ]
        
        search_data = {
            "query": random.choice(search_queries),
            "similarity_threshold": random.uniform(0.6, 0.9),
            "limit": random.randint(5, 15),
            "include_embeddings": False
        }
        
        with self.client.post(
            "/ai/semantic-search",
            json=search_data,
            headers=self.get_auth_headers(),
            catch_response=True,
            name="semantic_search"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        response.success()
                    else:
                        response.failure(f"Semantic search failed: {data.get('error')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Semantic search failed with status {response.status_code}")
    
    @task(1)
    def generate_embeddings(self):
        """Generate embeddings for a file"""
        if not self.access_token or not self.user_files:
            return
        
        file_info = random.choice(self.user_files)
        file_id = file_info.get("id")
        
        if not file_id:
            return
        
        with self.client.post(
            "/ai/embeddings/generate",
            json={"file_id": file_id},
            headers=self.get_auth_headers(),
            catch_response=True,
            name="generate_embeddings"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        response.success()
                    else:
                        response.failure(f"Generate embeddings failed: {data.get('error')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Generate embeddings failed with status {response.status_code}")
    
    @task(1)
    def get_analytics(self):
        """Get user analytics data"""
        if not self.access_token:
            return
        
        with self.client.get(
            "/analytics/dashboard",
            headers=self.get_auth_headers(),
            catch_response=True,
            name="get_analytics"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        response.success()
                    else:
                        response.failure(f"Get analytics failed: {data.get('error')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Get analytics failed with status {response.status_code}")


class AdminUser(FastHttpUser):
    """Simulates an admin user with elevated privileges"""
    
    wait_time = between(2, 8)
    weight = 1  # Lower weight - fewer admin users
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.admin_id = None
    
    def on_start(self):
        """Admin login"""
        self.admin_login()
    
    def admin_login(self):
        """Authenticate as admin"""
        login_data = {
            "email": f"admin_loadtest_{random.randint(1, 100)}@example.com",
            "password": "AdminLoadTest123!",
            "device_info": {"platform": "admin_panel"}
        }
        
        with self.client.post(
            "/auth/login",
            json=login_data,
            catch_response=True,
            name="admin_login"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        self.access_token = data.get("access_token")
                        self.admin_id = data.get("user", {}).get("id")
                        response.success()
                    else:
                        response.failure(f"Admin login failed: {data.get('error')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
    
    @task(5)
    def get_system_stats(self):
        """Get system statistics"""
        if not self.access_token:
            return
        
        with self.client.get(
            "/admin/stats",
            headers={"Authorization": f"Bearer {self.access_token}"},
            catch_response=True,
            name="get_system_stats"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get system stats failed with status {response.status_code}")
    
    @task(3)
    def list_all_users(self):
        """List all users (admin operation)"""
        if not self.access_token:
            return
        
        params = {
            "limit": random.randint(20, 100),
            "offset": random.randint(0, 500)
        }
        
        with self.client.get(
            "/admin/users",
            params=params,
            headers={"Authorization": f"Bearer {self.access_token}"},
            catch_response=True,
            name="list_all_users"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List users failed with status {response.status_code}")
    
    @task(2)
    def get_system_health(self):
        """Check system health"""
        with self.client.get(
            "/health",
            catch_response=True,
            name="system_health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed with status {response.status_code}")


class ReadOnlyUser(FastHttpUser):
    """Simulates a read-only user for search and browse operations"""
    
    wait_time = between(0.5, 3)
    weight = 2  # More read-only users
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
    
    def on_start(self):
        """Login as read-only user"""
        self.login()
    
    def login(self):
        """Simple login for read-only operations"""
        login_data = {
            "email": f"readonly_{random.randint(1, 5000)}@example.com",
            "password": "ReadOnly123!"
        }
        
        with self.client.post(
            "/auth/login",
            json=login_data,
            catch_response=True,
            name="readonly_login"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        self.access_token = data.get("access_token")
                        response.success()
                except json.JSONDecodeError:
                    pass
    
    @task(10)
    def browse_files(self):
        """Browse files (read-only)"""
        if not self.access_token:
            return
        
        params = {
            "limit": random.randint(10, 30),
            "file_type": random.choice(["", "document", "image", "video"])
        }
        
        with self.client.get(
            "/metadata/files",
            params=params,
            headers={"Authorization": f"Bearer {self.access_token}"},
            catch_response=True,
            name="browse_files"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Browse failed with status {response.status_code}")
    
    @task(8)
    def quick_search(self):
        """Quick search operations"""
        if not self.access_token:
            return
        
        search_terms = ["document", "image", "data", "report", "presentation"]
        
        with self.client.get(
            "/metadata/search",
            params={"q": random.choice(search_terms), "limit": 10},
            headers={"Authorization": f"Bearer {self.access_token}"},
            catch_response=True,
            name="quick_search"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Quick search failed with status {response.status_code}")


# Custom Locust events and hooks
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    logger.info("Load test starting...")
    logger.info(f"Target host: {environment.host}")
    logger.info(f"User classes: {[cls.__name__ for cls in environment.user_classes]}")


@events.test_stop.add_listener  
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    logger.info("Load test completed")
    
    # Print summary statistics
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Total failures: {stats.total.num_failures}")
    logger.info(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    logger.info(f"Max response time: {stats.total.max_response_time:.2f}ms")
    logger.info(f"Requests per second: {stats.total.current_rps:.2f}")


@events.request_failure.add_listener
def on_request_failure(request_type, name, response_time, response_length, exception, **kwargs):
    """Called when a request fails"""
    logger.warning(f"Request failed: {request_type} {name} - {exception}")


# Performance thresholds for CI/CD integration
class PerformanceThresholds:
    """Define performance thresholds for automated testing"""
    
    MAX_RESPONSE_TIME_MS = 2000  # 2 seconds
    MAX_FAILURE_RATE = 0.05      # 5% failure rate
    MIN_RPS = 10                 # Minimum requests per second
    
    @classmethod
    def check_thresholds(cls, stats):
        """Check if performance meets thresholds"""
        failures = []
        
        if stats.total.avg_response_time > cls.MAX_RESPONSE_TIME_MS:
            failures.append(f"Average response time {stats.total.avg_response_time:.2f}ms exceeds threshold {cls.MAX_RESPONSE_TIME_MS}ms")
        
        failure_rate = stats.total.num_failures / max(stats.total.num_requests, 1)
        if failure_rate > cls.MAX_FAILURE_RATE:
            failures.append(f"Failure rate {failure_rate:.2%} exceeds threshold {cls.MAX_FAILURE_RATE:.2%}")
        
        if stats.total.current_rps < cls.MIN_RPS:
            failures.append(f"RPS {stats.total.current_rps:.2f} below threshold {cls.MIN_RPS}")
        
        return failures


# Locust configuration for different scenarios
class LoadTestScenarios:
    """Different load testing scenarios"""
    
    @staticmethod
    def light_load():
        """Light load scenario"""
        return {
            "users": 10,
            "spawn_rate": 2,
            "run_time": "5m"
        }
    
    @staticmethod
    def normal_load():
        """Normal load scenario"""
        return {
            "users": 50,
            "spawn_rate": 5,
            "run_time": "10m"
        }
    
    @staticmethod
    def heavy_load():
        """Heavy load scenario"""
        return {
            "users": 200,
            "spawn_rate": 10,
            "run_time": "15m"
        }
    
    @staticmethod
    def stress_test():
        """Stress test scenario"""
        return {
            "users": 500,
            "spawn_rate": 20,
            "run_time": "20m"
        }
    
    @staticmethod
    def spike_test():
        """Spike test scenario"""
        return {
            "users": 1000,
            "spawn_rate": 50,
            "run_time": "5m"
        }