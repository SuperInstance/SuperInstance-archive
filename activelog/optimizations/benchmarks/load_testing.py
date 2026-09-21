"""
Load testing implementation using Locust for ActiveLog.
Provides comprehensive load testing scenarios and user behavior simulation.
"""
import os
import sys
import random
import time
import json
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
from datetime import datetime

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from locust import HttpUser, task, between, events
    from locust.runners import MasterRunner, WorkerRunner
    from locust.env import Environment
    from locust.stats import stats_printer, stats_history
    from locust.log import setup_logging
except ImportError:
    print("Locust not installed. Install with: pip install locust")
    sys.exit(1)

logger = logging.getLogger(__name__)


class ActiveLogUser(HttpUser):
    """Base user class for ActiveLog load testing."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts."""
        self.auth_token = None
        self.user_id = None
        self.files = []
        self.login()
    
    def login(self):
        """Authenticate user and get token."""
        # Use test credentials or generate random ones
        username = f"test_user_{random.randint(1000, 9999)}"
        password = "test_password_123"
        
        # Try to login, if fails, register first
        login_data = {
            "username": username,
            "password": password
        }
        
        with self.client.post("/api/v1/auth/login", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.user_id = data.get("user_id")
                self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
            elif response.status_code == 401:
                # Try to register
                self.register_and_login(username, password)
            else:
                response.failure(f"Login failed: {response.status_code}")
    
    def register_and_login(self, username: str, password: str):
        """Register new user and login."""
        register_data = {
            "username": username,
            "email": f"{username}@test.com",
            "password": password,
            "name": f"Test User {username}"
        }
        
        with self.client.post("/api/v1/auth/register", json=register_data, catch_response=True) as response:
            if response.status_code == 201:
                # Now login
                login_data = {"username": username, "password": password}
                with self.client.post("/api/v1/auth/login", json=login_data) as login_response:
                    if login_response.status_code == 200:
                        data = login_response.json()
                        self.auth_token = data.get("access_token")
                        self.user_id = data.get("user_id")
                        self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
            else:
                response.failure(f"Registration failed: {response.status_code}")
    
    @task(10)
    def view_dashboard(self):
        """View user dashboard."""
        self.client.get("/api/v1/dashboard", name="dashboard")
    
    @task(15)
    def list_files(self):
        """List user files with pagination."""
        page = random.randint(1, 5)
        limit = random.choice([20, 50, 100])
        
        with self.client.get(
            f"/api/v1/files?page={page}&limit={limit}",
            name="list_files"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.files = data.get("items", [])[:10]  # Keep track of some files
    
    @task(8)
    def search_files(self):
        """Search files."""
        search_terms = ["document", "image", "report", "presentation", "data"]
        query = random.choice(search_terms)
        
        self.client.get(
            f"/api/v1/files/search?q={query}&limit=20",
            name="search_files"
        )
    
    @task(12)
    def view_file_details(self):
        """View details of a specific file."""
        if self.files:
            file_info = random.choice(self.files)
            file_id = file_info.get("id")
            if file_id:
                self.client.get(f"/api/v1/files/{file_id}", name="view_file_details")
    
    @task(5)
    def upload_file(self):
        """Upload a test file."""
        # Generate test file content
        file_sizes = [1024, 5120, 10240, 51200]  # 1KB to 50KB for testing
        file_size = random.choice(file_sizes)
        file_content = b"0" * file_size
        
        files = {
            "file": ("test_file.txt", file_content, "text/plain")
        }
        
        with self.client.post(
            "/api/v1/files/upload",
            files=files,
            name="upload_file"
        ) as response:
            if response.status_code == 201:
                data = response.json()
                # Add uploaded file to our list
                self.files.append(data)
    
    @task(6)
    def download_file(self):
        """Download a file."""
        if self.files:
            file_info = random.choice(self.files)
            file_id = file_info.get("id")
            if file_id:
                self.client.get(f"/api/v1/files/{file_id}/download", name="download_file")
    
    @task(3)
    def share_file(self):
        """Share a file with another user."""
        if self.files:
            file_info = random.choice(self.files)
            file_id = file_info.get("id")
            if file_id:
                share_data = {
                    "shared_with": f"test_user_{random.randint(1000, 9999)}@test.com",
                    "permissions": random.choice(["read", "write"]),
                    "expires_at": None
                }
                self.client.post(
                    f"/api/v1/files/{file_id}/share",
                    json=share_data,
                    name="share_file"
                )
    
    @task(4)
    def view_activity(self):
        """View user activity logs."""
        self.client.get("/api/v1/users/activity", name="view_activity")
    
    @task(2)
    def update_profile(self):
        """Update user profile."""
        profile_data = {
            "name": f"Updated User {random.randint(1000, 9999)}",
            "preferences": {
                "theme": random.choice(["light", "dark"]),
                "notifications": random.choice([True, False])
            }
        }
        self.client.put("/api/v1/users/profile", json=profile_data, name="update_profile")
    
    @task(1)
    def ai_analysis(self):
        """Request AI analysis for a file."""
        if self.files:
            file_info = random.choice(self.files)
            file_id = file_info.get("id")
            if file_id:
                analysis_data = {
                    "analysis_type": random.choice(["summary", "keywords", "sentiment"])
                }
                self.client.post(
                    f"/api/v1/files/{file_id}/ai/analyze",
                    json=analysis_data,
                    name="ai_analysis"
                )


class AdminUser(HttpUser):
    """Admin user with different behavior patterns."""
    
    wait_time = between(2, 5)
    weight = 1  # Lower weight means fewer admin users
    
    def on_start(self):
        """Login as admin."""
        self.auth_token = None
        self.login_as_admin()
    
    def login_as_admin(self):
        """Login with admin credentials."""
        admin_data = {
            "username": "admin",
            "password": "admin_password_123"
        }
        
        with self.client.post("/api/v1/auth/login", json=admin_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
    
    @task(5)
    def view_admin_dashboard(self):
        """View admin dashboard."""
        self.client.get("/api/v1/admin/dashboard", name="admin_dashboard")
    
    @task(8)
    def list_all_users(self):
        """List all users."""
        page = random.randint(1, 3)
        self.client.get(f"/api/v1/admin/users?page={page}", name="admin_list_users")
    
    @task(6)
    def system_analytics(self):
        """View system analytics."""
        timeframe = random.choice(["1d", "7d", "30d"])
        self.client.get(f"/api/v1/admin/analytics?timeframe={timeframe}", name="admin_analytics")
    
    @task(3)
    def system_health(self):
        """Check system health."""
        self.client.get("/api/v1/admin/health", name="admin_health")
    
    @task(4)
    def audit_logs(self):
        """View audit logs."""
        self.client.get("/api/v1/admin/audit", name="admin_audit")
    
    @task(2)
    def manage_storage(self):
        """View storage management."""
        self.client.get("/api/v1/admin/storage", name="admin_storage")


class ReadOnlyUser(HttpUser):
    """Read-only user that only performs GET requests."""
    
    wait_time = between(1, 2)
    weight = 3  # More read-only users
    
    def on_start(self):
        """Login as read-only user."""
        self.auth_token = None
        self.files = []
        self.login()
    
    def login(self):
        """Login as regular user."""
        username = f"readonly_user_{random.randint(1000, 9999)}"
        password = "readonly_password_123"
        
        login_data = {"username": username, "password": password}
        
        with self.client.post("/api/v1/auth/login", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
            elif response.status_code == 401:
                # Register first
                register_data = {
                    "username": username,
                    "email": f"{username}@test.com",
                    "password": password,
                    "name": f"Read Only User {username}"
                }
                
                with self.client.post("/api/v1/auth/register", json=register_data):
                    pass
                
                # Login again
                with self.client.post("/api/v1/auth/login", json=login_data) as login_response:
                    if login_response.status_code == 200:
                        data = login_response.json()
                        self.auth_token = data.get("access_token")
                        self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
    
    @task(20)
    def browse_files(self):
        """Browse files frequently."""
        page = random.randint(1, 10)
        self.client.get(f"/api/v1/files?page={page}", name="browse_files")
    
    @task(15)
    def search_content(self):
        """Search for content."""
        queries = ["report", "image", "document", "data", "presentation"]
        query = random.choice(queries)
        self.client.get(f"/api/v1/files/search?q={query}", name="search_content")
    
    @task(10)
    def view_public_files(self):
        """View public/shared files."""
        self.client.get("/api/v1/files/public", name="view_public_files")
    
    @task(8)
    def view_file_preview(self):
        """View file previews."""
        # Simulate viewing different file types
        file_types = ["pdf", "image", "text", "video"]
        file_type = random.choice(file_types)
        file_id = f"sample_{file_type}_{random.randint(1, 100)}"
        self.client.get(f"/api/v1/files/{file_id}/preview", name="view_file_preview")
    
    @task(5)
    def check_notifications(self):
        """Check notifications."""
        self.client.get("/api/v1/notifications", name="check_notifications")


class LoadTestScenarios:
    """Predefined load testing scenarios."""
    
    @staticmethod
    def light_load():
        """Light load scenario - normal business hours."""
        return {
            "users": 50,
            "spawn_rate": 2,
            "run_time": "5m",
            "user_classes": [
                {"class": ActiveLogUser, "weight": 5},
                {"class": ReadOnlyUser, "weight": 8},
                {"class": AdminUser, "weight": 1}
            ]
        }
    
    @staticmethod
    def normal_load():
        """Normal load scenario - peak business hours."""
        return {
            "users": 200,
            "spawn_rate": 5,
            "run_time": "10m",
            "user_classes": [
                {"class": ActiveLogUser, "weight": 6},
                {"class": ReadOnlyUser, "weight": 10},
                {"class": AdminUser, "weight": 1}
            ]
        }
    
    @staticmethod
    def heavy_load():
        """Heavy load scenario - high traffic."""
        return {
            "users": 500,
            "spawn_rate": 10,
            "run_time": "15m",
            "user_classes": [
                {"class": ActiveLogUser, "weight": 7},
                {"class": ReadOnlyUser, "weight": 12},
                {"class": AdminUser, "weight": 2}
            ]
        }
    
    @staticmethod
    def stress_test():
        """Stress test scenario - breaking point."""
        return {
            "users": 1000,
            "spawn_rate": 20,
            "run_time": "20m",
            "user_classes": [
                {"class": ActiveLogUser, "weight": 8},
                {"class": ReadOnlyUser, "weight": 15},
                {"class": AdminUser, "weight": 3}
            ]
        }
    
    @staticmethod
    def spike_test():
        """Spike test scenario - sudden traffic spike."""
        return {
            "users": 800,
            "spawn_rate": 50,  # Very fast spawn
            "run_time": "10m",
            "user_classes": [
                {"class": ActiveLogUser, "weight": 10},
                {"class": ReadOnlyUser, "weight": 20},
                {"class": AdminUser, "weight": 2}
            ]
        }


class LoadTestRunner:
    """Custom load test runner with advanced features."""
    
    def __init__(self, host: str, output_dir: str = "load_test_results"):
        self.host = host
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Setup logging
        setup_logging("INFO", None)
        
        # Statistics collection
        self.stats_history = []
    
    def run_scenario(
        self,
        scenario_name: str,
        scenario_config: Dict[str, Any],
        headless: bool = True
    ):
        """Run a specific load test scenario."""
        logger.info(f"Starting load test scenario: {scenario_name}")
        
        # Create environment
        env = Environment(
            user_classes=[ActiveLogUser, ReadOnlyUser, AdminUser],
            host=self.host,
            events=events
        )
        
        # Setup event listeners
        self._setup_event_listeners(scenario_name)
        
        # Start runner
        if headless:
            runner = env.create_local_runner()
        else:
            runner = env.create_web_ui_runner()
        
        # Start load test
        users = scenario_config["users"]
        spawn_rate = scenario_config["spawn_rate"]
        run_time = scenario_config["run_time"]
        
        runner.start(users, spawn_rate=spawn_rate)
        
        # Run for specified time
        if headless:
            # Parse run_time (e.g., "5m", "30s")
            if run_time.endswith('m'):
                duration = int(run_time[:-1]) * 60
            elif run_time.endswith('s'):
                duration = int(run_time[:-1])
            else:
                duration = int(run_time)
            
            time.sleep(duration)
            
            # Stop the test
            runner.stop()
            
            # Generate report
            self._generate_load_test_report(scenario_name, env.stats)
        
        return env.stats
    
    def _setup_event_listeners(self, scenario_name: str):
        """Setup event listeners for statistics collection."""
        
        @events.request.add_listener
        def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
            """Record request statistics."""
            self.stats_history.append({
                "timestamp": datetime.now().isoformat(),
                "request_type": request_type,
                "name": name,
                "response_time": response_time,
                "response_length": response_length,
                "exception": str(exception) if exception else None
            })
        
        @events.user_error.add_listener
        def on_user_error(user_instance, exception, tb, **kwargs):
            """Record user errors."""
            logger.error(f"User error: {exception}")
    
    def _generate_load_test_report(self, scenario_name: str, stats):
        """Generate comprehensive load test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Statistics summary
        stats_summary = {
            "scenario": scenario_name,
            "timestamp": timestamp,
            "total_requests": stats.total.num_requests,
            "total_failures": stats.total.num_failures,
            "average_response_time": stats.total.avg_response_time,
            "median_response_time": stats.total.median_response_time,
            "percentiles": {
                "95th": stats.total.get_response_time_percentile(0.95),
                "99th": stats.total.get_response_time_percentile(0.99)
            },
            "requests_per_second": stats.total.total_rps,
            "failures_per_second": stats.total.fail_ratio
        }
        
        # Per-endpoint statistics
        endpoint_stats = []
        for name, stat in stats.entries.items():
            if name != "Aggregated":
                endpoint_stats.append({
                    "name": name,
                    "requests": stat.num_requests,
                    "failures": stat.num_failures,
                    "avg_response_time": stat.avg_response_time,
                    "median_response_time": stat.median_response_time,
                    "min_response_time": stat.min_response_time,
                    "max_response_time": stat.max_response_time,
                    "rps": stat.total_rps
                })
        
        # Complete report
        report_data = {
            "summary": stats_summary,
            "endpoints": endpoint_stats,
            "request_history": self.stats_history[-1000:]  # Last 1000 requests
        }
        
        # Save JSON report
        json_file = self.output_dir / f"load_test_{scenario_name}_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Save HTML report
        html_report = self._generate_html_load_report(report_data)
        html_file = self.output_dir / f"load_test_{scenario_name}_{timestamp}.html"
        with open(html_file, 'w') as f:
            f.write(html_report)
        
        logger.info(f"Load test report saved: {json_file}")
        logger.info(f"HTML report saved: {html_file}")
        
        return report_data
    
    def _generate_html_load_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML load test report."""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ActiveLog Load Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .pass { color: green; }
                .fail { color: red; }
                .warning { color: orange; }
            </style>
        </head>
        <body>
            <h1>ActiveLog Load Test Report</h1>
            <h2>Scenario: {scenario}</h2>
            <p><strong>Generated:</strong> {timestamp}</p>
            
            <h2>Summary</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Requests</td><td>{total_requests}</td></tr>
                <tr><td>Total Failures</td><td class="{failure_class}">{total_failures}</td></tr>
                <tr><td>Average Response Time</td><td>{avg_response_time:.2f} ms</td></tr>
                <tr><td>95th Percentile</td><td>{p95:.2f} ms</td></tr>
                <tr><td>99th Percentile</td><td>{p99:.2f} ms</td></tr>
                <tr><td>Requests/Second</td><td>{rps:.2f}</td></tr>
            </table>
            
            <h2>Endpoint Performance</h2>
            <table>
                <thead>
                    <tr>
                        <th>Endpoint</th>
                        <th>Requests</th>
                        <th>Failures</th>
                        <th>Avg Time (ms)</th>
                        <th>Min Time (ms)</th>
                        <th>Max Time (ms)</th>
                        <th>RPS</th>
                    </tr>
                </thead>
                <tbody>
                    {endpoint_rows}
                </tbody>
            </table>
        </body>
        </html>
        """
        
        summary = report_data["summary"]
        
        # Generate endpoint rows
        endpoint_rows = []
        for endpoint in report_data["endpoints"]:
            failure_class = "fail" if endpoint["failures"] > 0 else "pass"
            endpoint_rows.append(f"""
                <tr>
                    <td>{endpoint['name']}</td>
                    <td>{endpoint['requests']}</td>
                    <td class="{failure_class}">{endpoint['failures']}</td>
                    <td>{endpoint['avg_response_time']:.2f}</td>
                    <td>{endpoint['min_response_time']:.2f}</td>
                    <td>{endpoint['max_response_time']:.2f}</td>
                    <td>{endpoint['rps']:.2f}</td>
                </tr>
            """)
        
        failure_class = "fail" if summary["total_failures"] > 0 else "pass"
        
        return html_template.format(
            scenario=summary["scenario"],
            timestamp=summary["timestamp"],
            total_requests=summary["total_requests"],
            total_failures=summary["total_failures"],
            failure_class=failure_class,
            avg_response_time=summary["average_response_time"],
            p95=summary["percentiles"]["95th"],
            p99=summary["percentiles"]["99th"],
            rps=summary["requests_per_second"],
            endpoint_rows="".join(endpoint_rows)
        )


def main():
    """CLI interface for load testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Load Testing")
    parser.add_argument('--host', required=True, help="Target host URL")
    parser.add_argument('--scenario', default="normal_load", 
                       choices=["light_load", "normal_load", "heavy_load", "stress_test", "spike_test"],
                       help="Load test scenario")
    parser.add_argument('--output-dir', default="load_test_results", help="Output directory")
    parser.add_argument('--headless', action='store_true', help="Run in headless mode")
    
    args = parser.parse_args()
    
    # Get scenario configuration
    scenarios = LoadTestScenarios()
    scenario_config = getattr(scenarios, args.scenario)()
    
    # Run load test
    runner = LoadTestRunner(args.host, args.output_dir)
    stats = runner.run_scenario(args.scenario, scenario_config, args.headless)
    
    print(f"Load test completed: {args.scenario}")
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f} ms")


if __name__ == "__main__":
    main()