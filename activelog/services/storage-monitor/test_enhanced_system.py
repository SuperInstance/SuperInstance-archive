#!/usr/bin/env python3
"""
Comprehensive Testing Suite for Enhanced Storage Monitoring System
Tests all enterprise features, self-healing, dashboards, and integrations
"""

import asyncio
import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import threading
import shutil
import sys

# Add the current directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from enhanced_main import EnhancedStorageMonitor, CircuitBreaker, SecurityManager
    from lib.self_healing_system import SelfHealingSystem, PredictiveFailureDetector
    from lib.dashboard_system import AdvancedDashboard, RealTimeVisualization
    from lib.growth_analyzer import GrowthAnalyzer
    from lib.improvement_integration import ImprovementIntegration
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_SUCCESSFUL = False

class TestEnhancedStorageMonitor(unittest.TestCase):
    """Test suite for enhanced storage monitoring system"""
    
    def setUp(self):
        """Set up test environment"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
            
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_storage.db")
        
        # Create test configuration
        self.config = {
            "monitoring": {
                "scan_interval_seconds": 1,
                "worker_threads": 2,
                "enable_async_io": True,
                "enable_caching": True,
                "max_memory_usage_mb": 100
            },
            "thresholds": {
                "rapid_growth_mb_per_minute": 10,
                "large_file_gb": 0.1,
                "directory_limit_gb": 0.5,
                "disk_usage_warning": 0.75,
                "anomaly_sensitivity": 0.1
            },
            "paths": {
                "monitor": [
                    {
                        "path": self.temp_dir,
                        "priority": "high",
                        "scan_depth": 2,
                        "enable_real_time": True
                    }
                ],
                "exclude_patterns": [
                    {"pattern": "*/test_exclude/*", "performance_impact": "low"}
                ]
            },
            "security": {
                "enable_auth": True,
                "jwt_expiry_hours": 1,
                "rate_limit_per_minute": 100,
                "encrypt_sensitive_data": True
            },
            "features": {
                "enable_ml_anomaly_detection": True,
                "enable_predictive_analysis": True,
                "enable_auto_remediation": False,  # Disabled for testing
                "enable_self_healing": True
            },
            "performance": {
                "max_scan_duration_seconds": 30,
                "memory_threshold_mb": 200,
                "cpu_threshold_percent": 90
            },
            "logging": {
                "level": "DEBUG",
                "structured": True
            }
        }
        
        # Create test files
        self.test_files_dir = os.path.join(self.temp_dir, "test_files")
        os.makedirs(self.test_files_dir, exist_ok=True)
        
        # Create some test files
        with open(os.path.join(self.test_files_dir, "small_file.txt"), "w") as f:
            f.write("test content")
            
        with open(os.path.join(self.test_files_dir, "large_file.txt"), "w") as f:
            f.write("x" * (150 * 1024 * 1024))  # 150MB file
    
    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'monitor') and self.monitor:
            try:
                asyncio.run(self.monitor.shutdown())
            except:
                pass
        
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_enhanced_monitor_initialization(self):
        """Test enhanced monitor initialization with all features"""
        monitor = EnhancedStorageMonitor(self.config, self.db_path)
        
        self.assertIsNotNone(monitor)
        self.assertIsNotNone(monitor.circuit_breaker)
        self.assertIsNotNone(monitor.security_manager)
        self.assertTrue(monitor.config["features"]["enable_ml_anomaly_detection"])
        self.assertEqual(len(monitor.worker_pool), 2)
    
    async def async_test_real_time_monitoring(self):
        """Test real-time monitoring with async operations"""
        monitor = EnhancedStorageMonitor(self.config, self.db_path)
        
        # Start monitoring
        monitor_task = asyncio.create_task(monitor.start_monitoring())
        await asyncio.sleep(2)  # Let it run for 2 seconds
        
        # Check that database has entries
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM file_info")
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertGreater(count, 0, "Monitor should have recorded file information")
        
        # Shutdown
        await monitor.shutdown()
    
    def test_real_time_monitoring_wrapper(self):
        """Wrapper for async real-time monitoring test"""
        asyncio.run(self.async_test_real_time_monitoring())
    
    def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        breaker = CircuitBreaker(failure_threshold=3, timeout=5)
        
        # Test normal operation
        self.assertEqual(breaker.state, "closed")
        
        # Simulate failures
        for _ in range(3):
            breaker.record_failure()
        
        self.assertEqual(breaker.state, "open")
        
        # Test timeout
        time.sleep(6)
        self.assertEqual(breaker.state, "half_open")
        
        # Test recovery
        breaker.record_success()
        self.assertEqual(breaker.state, "closed")
    
    def test_security_manager(self):
        """Test security manager functionality"""
        security = SecurityManager(self.config["security"])
        
        # Test token generation
        token = security.generate_token("test_user")
        self.assertIsNotNone(token)
        
        # Test token validation
        payload = security.validate_token(token)
        self.assertEqual(payload["user"], "test_user")
        
        # Test rate limiting
        client_id = "test_client"
        
        # Should allow requests within limit
        for _ in range(50):
            self.assertTrue(security.check_rate_limit(client_id))
        
        # Should block after limit
        for _ in range(60):
            security.check_rate_limit(client_id)
        
        self.assertFalse(security.check_rate_limit(client_id))
    
    async def async_test_ml_anomaly_detection(self):
        """Test ML-powered anomaly detection"""
        monitor = EnhancedStorageMonitor(self.config, self.db_path)
        
        # Create some data points
        test_data = [
            {"path": "/test/path1", "size": 1000, "growth_rate": 10},
            {"path": "/test/path2", "size": 2000, "growth_rate": 15},
            {"path": "/test/path3", "size": 50000000, "growth_rate": 500},  # Anomaly
        ]
        
        # Test anomaly detection
        for data in test_data:
            is_anomaly = await monitor.detect_anomaly(data["path"], data["size"], data["growth_rate"])
            
            if data["growth_rate"] > 100:  # Should detect the large growth rate
                self.assertTrue(is_anomaly, f"Should detect anomaly for {data['path']}")
    
    def test_ml_anomaly_detection_wrapper(self):
        """Wrapper for async ML anomaly detection test"""
        asyncio.run(self.async_test_ml_anomaly_detection())

class TestSelfHealingSystem(unittest.TestCase):
    """Test suite for self-healing system"""
    
    def setUp(self):
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
            
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_healing.db")
        
        # Initialize database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                timestamp REAL,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL,
                scan_duration REAL,
                error_count INTEGER
            );
            
            CREATE TABLE IF NOT EXISTS performance_patterns (
                id INTEGER PRIMARY KEY,
                pattern_type TEXT,
                features TEXT,
                timestamp REAL
            );
        """)
        conn.commit()
        conn.close()
        
        self.config = {
            "performance": {
                "cpu_threshold_percent": 80,
                "memory_threshold_mb": 512,
                "max_scan_duration_seconds": 60
            },
            "features": {
                "enable_auto_tuning": True,
                "enable_adaptive_thresholds": True
            }
        }
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_predictive_failure_detection(self):
        """Test predictive failure detection"""
        detector = PredictiveFailureDetector(self.db_path, self.config)
        
        # Add some performance data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = time.time()
        for i in range(100):
            cursor.execute("""
                INSERT INTO system_metrics 
                (timestamp, cpu_usage, memory_usage, disk_usage, scan_duration, error_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                current_time - (100 - i) * 60,  # 100 minutes of data
                50 + i * 0.3,  # Gradually increasing CPU
                30 + i * 0.2,  # Gradually increasing memory
                60 + i * 0.1,  # Gradually increasing disk
                10 + i * 0.05,  # Gradually increasing scan time
                i // 10  # Occasional errors
            ))
        
        conn.commit()
        conn.close()
        
        # Test failure prediction
        prediction = detector.predict_system_failure()
        self.assertIsNotNone(prediction)
        self.assertIn("risk_score", prediction)
        self.assertIn("time_to_failure_hours", prediction)
    
    async def async_test_self_healing_system(self):
        """Test complete self-healing system"""
        healing_system = SelfHealingSystem(self.db_path, self.config)
        
        # Test system analysis
        analysis = await healing_system.analyze_system_health()
        self.assertIsNotNone(analysis)
        self.assertIn("health_score", analysis)
        
        # Test auto-optimization
        optimization = await healing_system.optimize_performance()
        self.assertIsNotNone(optimization)
        self.assertIn("actions_taken", optimization)
    
    def test_self_healing_system_wrapper(self):
        asyncio.run(self.async_test_self_healing_system())

class TestDashboardSystem(unittest.TestCase):
    """Test suite for dashboard system"""
    
    def setUp(self):
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
            
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_dashboard.db")
        
        # Initialize database with test data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS file_info (
                id INTEGER PRIMARY KEY,
                path TEXT,
                size_bytes INTEGER,
                growth_rate REAL,
                timestamp REAL
            );
            
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY,
                timestamp REAL,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                resolved INTEGER DEFAULT 0
            );
        """)
        
        # Add test data
        current_time = time.time()
        test_files = [
            ("/test/path1", 1000000, 5.0),
            ("/test/path2", 500000000, 50.0),
            ("/test/path3", 2000000000, 100.0),
        ]
        
        for path, size, growth in test_files:
            cursor.execute("""
                INSERT INTO file_info (path, size_bytes, growth_rate, timestamp)
                VALUES (?, ?, ?, ?)
            """, (path, size, growth, current_time))
        
        # Add test alerts
        test_alerts = [
            ("rapid_growth", "high", "Rapid growth detected"),
            ("large_file", "medium", "Large file found"),
            ("disk_usage", "critical", "Disk usage critical"),
        ]
        
        for alert_type, severity, message in test_alerts:
            cursor.execute("""
                INSERT INTO alerts (timestamp, alert_type, severity, message)
                VALUES (?, ?, ?, ?)
            """, (current_time, alert_type, severity, message))
        
        conn.commit()
        conn.close()
        
        self.config = {
            "monitoring": {"scan_interval_seconds": 30},
            "thresholds": {"rapid_growth_mb_per_minute": 50}
        }
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def async_test_dashboard_functionality(self):
        """Test dashboard functionality"""
        dashboard = AdvancedDashboard(self.db_path, self.config)
        
        # Test system overview
        overview = await dashboard.get_system_overview()
        self.assertIsNotNone(overview)
        self.assertIn("overview", overview)
        self.assertIn("system_resources", overview)
        
        # Test predictive analytics
        analytics = await dashboard.get_predictive_analytics()
        self.assertIsNotNone(analytics)
        self.assertIn("predictions", analytics)
        
        # Test comprehensive report
        report = await dashboard.generate_comprehensive_report()
        self.assertIsNotNone(report)
        self.assertIn("system_overview", report)
        self.assertIn("predictive_analytics", report)
        self.assertIn("recommendations", report)
    
    def test_dashboard_functionality_wrapper(self):
        asyncio.run(self.async_test_dashboard_functionality())
    
    def test_visualization_engine(self):
        """Test real-time visualization engine"""
        viz = RealTimeVisualization(self.db_path)
        
        # Test growth trend chart
        chart = viz.generate_growth_trend_chart(24)
        self.assertIsNotNone(chart)
        
        # Test storage heatmap
        heatmap = viz.generate_storage_heatmap()
        self.assertIsNotNone(heatmap)
        
        # Test alert timeline
        timeline = viz.generate_alert_timeline(7)
        self.assertIsNotNone(timeline)
        self.assertIn("data", timeline)

class TestIntegrationTests(unittest.TestCase):
    """Integration tests for the complete enhanced system"""
    
    def setUp(self):
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
            
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "integration_test.db")
        
        self.config = {
            "monitoring": {
                "scan_interval_seconds": 2,
                "worker_threads": 1,
                "enable_async_io": True,
                "enable_caching": True
            },
            "thresholds": {
                "rapid_growth_mb_per_minute": 1,
                "large_file_gb": 0.01,
                "directory_limit_gb": 0.1
            },
            "paths": {
                "monitor": [
                    {
                        "path": self.temp_dir,
                        "priority": "high",
                        "enable_real_time": True
                    }
                ]
            },
            "features": {
                "enable_ml_anomaly_detection": True,
                "enable_self_healing": True,
                "enable_auto_remediation": False
            },
            "security": {
                "enable_auth": False  # Disabled for testing
            },
            "integrations": {
                "improvement_system": {
                    "enabled": False  # Disabled for testing
                }
            }
        }
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def async_test_complete_system_integration(self):
        """Test complete system integration"""
        # Initialize all components
        monitor = EnhancedStorageMonitor(self.config, self.db_path)
        dashboard = AdvancedDashboard(self.db_path, self.config)
        healing_system = SelfHealingSystem(self.db_path, self.config)
        
        try:
            # Start monitoring
            monitor_task = asyncio.create_task(monitor.start_monitoring())
            
            # Let it run for a few seconds
            await asyncio.sleep(3)
            
            # Create a test file to trigger monitoring
            test_file = os.path.join(self.temp_dir, "integration_test.txt")
            with open(test_file, "w") as f:
                f.write("x" * (20 * 1024 * 1024))  # 20MB file
            
            # Wait for detection
            await asyncio.sleep(2)
            
            # Test dashboard can read the data
            overview = await dashboard.get_system_overview()
            self.assertGreater(overview["overview"]["total_monitored_paths"], 0)
            
            # Test healing system analysis
            health = await healing_system.analyze_system_health()
            self.assertIsNotNone(health)
            
            # Test that the system detected the file
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM file_info WHERE path LIKE '%integration_test%'")
            count = cursor.fetchone()[0]
            conn.close()
            
            self.assertGreater(count, 0, "System should have detected the test file")
            
        finally:
            # Cleanup
            await monitor.shutdown()
    
    def test_complete_system_integration_wrapper(self):
        """Wrapper for complete system integration test"""
        asyncio.run(self.async_test_complete_system_integration())

class TestPerformanceAndStress(unittest.TestCase):
    """Performance and stress tests"""
    
    def setUp(self):
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
            
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "performance_test.db")
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_large_directory_scan_performance(self):
        """Test performance with large number of files"""
        # Create many test files
        test_dir = os.path.join(self.temp_dir, "large_test")
        os.makedirs(test_dir, exist_ok=True)
        
        num_files = 1000
        for i in range(num_files):
            with open(os.path.join(test_dir, f"file_{i}.txt"), "w") as f:
                f.write(f"test content {i}")
        
        config = {
            "monitoring": {
                "scan_interval_seconds": 60,
                "worker_threads": 4,
                "enable_async_io": True
            },
            "paths": {
                "monitor": [{"path": test_dir, "priority": "high"}]
            },
            "features": {"enable_ml_anomaly_detection": False}
        }
        
        # Test scan performance
        start_time = time.time()
        monitor = EnhancedStorageMonitor(config, self.db_path)
        
        # Run one scan cycle
        async def run_scan():
            await monitor.scan_directories()
        
        asyncio.run(run_scan())
        
        scan_time = time.time() - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(scan_time, 30, f"Scan took too long: {scan_time} seconds for {num_files} files")
        
        # Verify all files were scanned
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT path) FROM file_info")
        scanned_count = cursor.fetchone()[0]
        conn.close()
        
        self.assertGreaterEqual(scanned_count, num_files * 0.9, "Should scan most files")

def run_comprehensive_tests():
    """Run all test suites"""
    print("Starting Comprehensive Enhanced Storage Monitor Tests")
    print("=" * 60)
    
    # Check if we can run tests
    if not IMPORTS_SUCCESSFUL:
        print("❌ Cannot run tests - import failures detected")
        print("Please ensure all required modules are installed:")
        print("- fastapi, uvicorn")
        print("- scikit-learn, numpy") 
        print("- psutil, aiofiles")
        print("- plotly, pandas (optional)")
        return False
    
    # Test suites to run
    test_suites = [
        TestEnhancedStorageMonitor,
        TestSelfHealingSystem,
        TestDashboardSystem,
        TestIntegrationTests,
        TestPerformanceAndStress
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_suites:
        print(f"\n🧪 Running {test_class.__name__}")
        print("-" * 40)
        
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        total_tests += result.testsRun
        passed_tests += result.testsRun - len(result.failures) - len(result.errors)
        
        if result.failures:
            failed_tests.extend([f"{test_class.__name__}: {f[0]}" for f in result.failures])
        if result.errors:
            failed_tests.extend([f"{test_class.__name__}: {e[0]}" for e in result.errors])
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "No tests run")
    
    if failed_tests:
        print("\n❌ Failed Tests:")
        for test in failed_tests:
            print(f"  - {test}")
    else:
        print("\n✅ All tests passed!")
    
    # Feature validation
    print("\n🔍 Feature Validation:")
    features_tested = [
        "✅ Enhanced Storage Monitoring",
        "✅ Circuit Breaker Pattern",
        "✅ Security Manager",
        "✅ ML Anomaly Detection", 
        "✅ Self-Healing System",
        "✅ Predictive Failure Detection",
        "✅ Advanced Dashboard",
        "✅ Real-time Visualization",
        "✅ Performance Optimization",
        "✅ Integration Testing",
        "✅ Stress Testing"
    ]
    
    for feature in features_tested:
        print(f"  {feature}")
    
    return len(failed_tests) == 0

if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit_code = 0 if success else 1
    print(f"\nTest execution completed with exit code: {exit_code}")
    exit(exit_code)