#!/usr/bin/env python3
"""
Comprehensive Test Suite for Storage Monitoring System
Tests all components including real-time monitoring, remediation, analytics, and integration
"""

import unittest
import tempfile
import shutil
import os
import sqlite3
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import threading
from unittest.mock import patch, MagicMock

# Import the modules we're testing
import sys
sys.path.append('/home/activeloguser/activelog/services/storage-monitor')
sys.path.append('/home/activeloguser/activelog/services/storage-monitor/lib')

from main import StorageMonitor
from lib.growth_analyzer import GrowthAnalyzer
from lib.analytics_engine import StorageAnalyticsEngine
from lib.improvement_integration import ImprovementSystemIntegration

class TestStorageMonitor(unittest.TestCase):
    """Test the main StorageMonitor class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test_storage.db")
        self.test_config = os.path.join(self.test_dir, "test_config.json")
        
        # Create test config
        test_config = {
            "thresholds": {
                "rapid_growth_mb": 50,
                "large_file_gb": 0.1,
                "directory_limit_gb": 1.0,
                "scan_interval_seconds": 5
            },
            "paths_to_monitor": [self.test_dir],
            "paths_to_exclude": [],
            "remediation": {
                "auto_remediate": True,
                "quarantine_dir": os.path.join(self.test_dir, "quarantine")
            }
        }
        
        with open(self.test_config, 'w') as f:
            json.dump(test_config, f)
            
        # Initialize monitor with test config
        self.monitor = StorageMonitor(config_path=self.test_config)
        self.monitor.db_path = self.test_db
        self.monitor.setup_database()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_directory_size_calculation(self):
        """Test directory size calculation"""
        # Create test files
        test_subdir = os.path.join(self.test_dir, "test_subdir")
        os.makedirs(test_subdir, exist_ok=True)
        
        # Create files of known sizes
        with open(os.path.join(test_subdir, "small.txt"), 'w') as f:
            f.write("x" * 1000)  # 1KB
            
        with open(os.path.join(test_subdir, "large.txt"), 'w') as f:
            f.write("x" * 100000)  # 100KB
        
        # Test size calculation
        size, file_count = self.monitor.get_directory_size_and_count(Path(test_subdir))
        
        self.assertGreater(size, 100000)  # Should be > 100KB
        self.assertEqual(file_count, 2)   # Should find 2 files
    
    def test_large_file_detection(self):
        """Test large file detection and handling"""
        # Create a large test file (200MB equivalent for test)
        large_file = os.path.join(self.test_dir, "large_test.dat")
        with open(large_file, 'w') as f:
            f.write("x" * 200_000_000)  # 200MB
        
        # Test large file handling
        self.monitor.handle_large_file(large_file, 200_000_000)
        
        # Check database
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT path, size_bytes FROM large_files WHERE path = ?", (large_file,))
            result = cursor.fetchone()
            
            self.assertIsNotNone(result)
            self.assertEqual(result[1], 200_000_000)
    
    def test_growth_rate_calculation(self):
        """Test growth rate calculation"""
        test_path = os.path.join(self.test_dir, "growth_test")
        os.makedirs(test_path, exist_ok=True)
        
        # Insert test data directly into database
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            
            # Create historical data points
            base_time = datetime.now() - timedelta(hours=2)
            for i in range(5):
                timestamp = base_time + timedelta(minutes=30*i)
                size = 100_000_000 + (i * 50_000_000)  # Growing by 50MB every 30 min
                
                cursor.execute('''
                    INSERT INTO directory_history (path, size_bytes, file_count, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (test_path, size, 10, timestamp))
            
            conn.commit()
        
        # Test growth rate calculation
        growth_rate = self.monitor.calculate_growth_rate(test_path)
        
        self.assertIsNotNone(growth_rate)
        self.assertGreater(growth_rate, 0)  # Should detect positive growth
    
    def test_emergency_remediation(self):
        """Test emergency remediation procedures"""
        test_path = os.path.join(self.test_dir, "emergency_test")
        os.makedirs(test_path, exist_ok=True)
        
        # Create files to be remediated
        for i in range(3):
            large_file = os.path.join(test_path, f"emergency_{i}.log")
            with open(large_file, 'w') as f:
                f.write("x" * 50_000_000)  # 50MB each
        
        # Test emergency remediation
        self.monitor.emergency_remediation(test_path, 150.0)  # 150MB/hour growth
        
        # Check that remediation was logged
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM remediation_log WHERE target_path = ?", (test_path,))
            count = cursor.fetchone()[0]
            
            self.assertGreater(count, 0)  # Should have logged remediation actions

class TestGrowthAnalyzer(unittest.TestCase):
    """Test the GrowthAnalyzer class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test_growth.db")
        
        # Initialize database
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE directory_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    file_count INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            ''')
            conn.commit()
        
        self.analyzer = GrowthAnalyzer(self.test_db)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _insert_test_data(self, path: str, data_points: list):
        """Insert test data points into database"""
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            for timestamp, size_mb in data_points:
                cursor.execute('''
                    INSERT INTO directory_history (path, size_bytes, file_count, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (path, size_mb * 1_000_000, 100, timestamp))
            conn.commit()
    
    def test_linear_growth_detection(self):
        """Test linear growth detection"""
        test_path = "/test/linear"
        
        # Create linear growth pattern (10MB/hour)
        base_time = datetime.now() - timedelta(hours=5)
        data_points = [
            (base_time + timedelta(hours=i), 100 + (i * 10))
            for i in range(6)
        ]
        
        self._insert_test_data(test_path, data_points)
        
        # Test growth velocity calculation
        velocity = self.analyzer.calculate_growth_velocity(test_path, hours_back=6)
        
        self.assertNotIn("error", velocity)
        self.assertAlmostEqual(velocity["linear_growth_mb_per_hour"], 10.0, delta=1.0)
    
    def test_exponential_growth_detection(self):
        """Test exponential growth detection"""
        test_path = "/test/exponential"
        
        # Create exponential growth pattern
        base_time = datetime.now() - timedelta(hours=4)
        data_points = []
        
        for i in range(5):
            timestamp = base_time + timedelta(hours=i)
            size = 100 * (1.5 ** i)  # 50% growth per hour
            data_points.append((timestamp, size))
        
        self._insert_test_data(test_path, data_points)
        
        # Test exponential detection
        velocity = self.analyzer.calculate_growth_velocity(test_path, hours_back=5)
        
        self.assertNotIn("error", velocity)
        self.assertGreater(velocity["exponential_growth_factor"], 1.4)  # Should detect > 40% growth
    
    def test_growth_prediction(self):
        """Test future growth prediction"""
        test_path = "/test/prediction"
        
        # Create steady growth pattern
        base_time = datetime.now() - timedelta(hours=24)
        data_points = [
            (base_time + timedelta(hours=i), 100 + (i * 5))
            for i in range(25)
        ]
        
        self._insert_test_data(test_path, data_points)
        
        # Test prediction
        prediction = self.analyzer.predict_future_growth(test_path, hours_ahead=24)
        
        self.assertNotIn("error", prediction)
        self.assertIn("predictions", prediction)
        self.assertGreater(prediction["predictions"]["linear_mb"], prediction["current_size_mb"])
    
    def test_risk_assessment(self):
        """Test risk assessment algorithm"""
        test_path = "/test/risk"
        
        # Create high-risk growth pattern (rapid acceleration)
        base_time = datetime.now() - timedelta(hours=6)
        data_points = [
            (base_time, 100),
            (base_time + timedelta(hours=1), 110),
            (base_time + timedelta(hours=2), 125),
            (base_time + timedelta(hours=3), 150),
            (base_time + timedelta(hours=4), 200),
            (base_time + timedelta(hours=5), 300),
            (base_time + timedelta(hours=6), 500)
        ]
        
        self._insert_test_data(test_path, data_points)
        
        # Test risk assessment
        prediction = self.analyzer.predict_future_growth(test_path, hours_ahead=12)
        
        self.assertNotIn("error", prediction)
        risk_level = prediction.get("risk_assessment", {}).get("risk_level", "low")
        self.assertIn(risk_level, ["high", "critical"])  # Should detect high risk

class TestAnalyticsEngine(unittest.TestCase):
    """Test the StorageAnalyticsEngine class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test_analytics.db")
        self.output_dir = os.path.join(self.test_dir, "output")
        
        # Initialize test database with sample data
        self._setup_test_database()
        
        # Skip matplotlib-dependent tests if not available
        try:
            import matplotlib.pyplot as plt
            self.has_matplotlib = True
        except ImportError:
            self.has_matplotlib = False
        
        self.analytics = StorageAnalyticsEngine(self.test_db, self.output_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _setup_test_database(self):
        """Set up test database with sample data"""
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE directory_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    file_count INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    disk_total_gb REAL NOT NULL,
                    disk_used_gb REAL NOT NULL,
                    disk_free_gb REAL NOT NULL,
                    disk_usage_percent REAL NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE growth_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    growth_rate_mb INTEGER NOT NULL,
                    alert_time DATETIME NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Insert sample data
            base_time = datetime.now() - timedelta(days=7)
            for i in range(7):
                timestamp = base_time + timedelta(days=i)
                
                # Directory history
                cursor.execute('''
                    INSERT INTO directory_history (path, size_bytes, file_count, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (f"/test/path_{i}", (i + 1) * 1_000_000_000, 100 * (i + 1), timestamp))
                
                # System metrics
                cursor.execute('''
                    INSERT INTO system_metrics 
                    (timestamp, disk_total_gb, disk_used_gb, disk_free_gb, disk_usage_percent, cpu_percent, memory_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, 100.0, 50.0 + i * 5, 50.0 - i * 5, (50.0 + i * 5), 25.0, 60.0))
            
            conn.commit()
    
    def test_dashboard_data_generation(self):
        """Test dashboard data generation"""
        dashboard_data = self.analytics.generate_dashboard_data()
        
        self.assertNotIn("error", dashboard_data)
        self.assertIn("system_metrics", dashboard_data)
        self.assertIn("growth_trends", dashboard_data)
        self.assertIn("top_consumers", dashboard_data)
        self.assertIn("risk_assessment", dashboard_data)
    
    def test_system_metrics_analysis(self):
        """Test system metrics analysis"""
        with sqlite3.connect(self.test_db) as conn:
            system_metrics = self.analytics._get_system_metrics(conn)
        
        self.assertNotEqual(system_metrics, {"error": "no_data"})
        self.assertIn("current", system_metrics)
        self.assertIn("averages_24h", system_metrics)
        self.assertIn("status", system_metrics)
    
    def test_growth_trends_analysis(self):
        """Test growth trends analysis"""
        with sqlite3.connect(self.test_db) as conn:
            growth_trends = self.analytics._get_growth_trends(conn)
        
        self.assertIn("avg_daily_growth_gb", growth_trends)
        self.assertIn("trend_direction", growth_trends)
        self.assertIn("growth_acceleration", growth_trends)

class TestImprovementIntegration(unittest.TestCase):
    """Test the ImprovementSystemIntegration class"""
    
    def setUp(self):
        """Set up test environment"""
        self.integration = ImprovementSystemIntegration(
            improvement_system_url="http://localhost:8500",
            storage_monitor_url="http://localhost:8490"
        )
    
    @patch('requests.Session.post')
    def test_emergency_notification(self, mock_post):
        """Test emergency notification to improvement system"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Test notification
        result = self.integration.notify_storage_emergency(
            "/test/path", 150.0, ["quarantine", "compress"]
        )
        
        self.assertTrue(result)
        mock_post.assert_called_once()
    
    @patch('requests.Session.get')
    def test_health_check(self, mock_get):
        """Test improvement system health check"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "active", "version": "2.0"}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_get.return_value = mock_response
        
        # Test health check
        health = self.integration.check_improvement_system_health()
        
        self.assertTrue(health["healthy"])
        self.assertEqual(health["status"], "active")
        self.assertGreater(health["response_time_ms"], 0)
    
    def test_response_plan_creation(self):
        """Test incident response plan creation"""
        details = {"path": "/test", "growth_rate": 200}
        
        response_plan = self.integration._create_response_plan(
            "runaway_storage_growth", "critical", details
        )
        
        self.assertIsInstance(response_plan, list)
        self.assertGreater(len(response_plan), 0)
        
        # Check that steps have required fields
        for step in response_plan:
            self.assertIn("step", step)
            self.assertIn("action", step)
            self.assertIn("system", step)
            self.assertIn("timeout_minutes", step)

class TestEndToEndIntegration(unittest.TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        """Set up test environment for integration tests"""
        self.test_dir = tempfile.mkdtemp()
        self.test_config = {
            "thresholds": {
                "rapid_growth_mb": 10,  # Low threshold for testing
                "scan_interval_seconds": 2
            },
            "paths_to_monitor": [self.test_dir],
            "remediation": {"auto_remediate": True}
        }
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_rapid_growth_detection_and_response(self):
        """Test complete flow from growth detection to remediation"""
        # This test simulates the complete workflow but is simplified
        # In a real environment, this would test the full monitoring loop
        
        # Create initial directory structure
        test_subdir = os.path.join(self.test_dir, "rapid_growth_test")
        os.makedirs(test_subdir, exist_ok=True)
        
        # Create small initial file
        with open(os.path.join(test_subdir, "initial.txt"), 'w') as f:
            f.write("initial content")
        
        # Simulate rapid growth by creating large file
        large_file = os.path.join(test_subdir, "rapidly_growing.log")
        with open(large_file, 'w') as f:
            f.write("x" * 50_000_000)  # 50MB
        
        # The monitor would detect this in its monitoring loop
        # For testing, we verify that the detection logic works
        monitor = StorageMonitor()
        size, file_count = monitor.get_directory_size_and_count(Path(test_subdir))
        
        self.assertGreater(size, 50_000_000)
        self.assertEqual(file_count, 2)

class TestSystemStressTest(unittest.TestCase):
    """Stress tests for the storage monitoring system"""
    
    def setUp(self):
        """Set up stress test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.stress_test_timeout = 30  # seconds
    
    def tearDown(self):
        """Clean up stress test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_large_directory_scan_performance(self):
        """Test performance with large number of files"""
        # Create many small files
        stress_dir = os.path.join(self.test_dir, "stress_test")
        os.makedirs(stress_dir, exist_ok=True)
        
        file_count = 1000  # Create 1000 files
        for i in range(file_count):
            with open(os.path.join(stress_dir, f"file_{i:04d}.txt"), 'w') as f:
                f.write(f"content_{i}")
        
        # Time the directory scan
        monitor = StorageMonitor()
        start_time = time.time()
        
        size, counted_files = monitor.get_directory_size_and_count(Path(stress_dir))
        
        scan_time = time.time() - start_time
        
        self.assertEqual(counted_files, file_count)
        self.assertLess(scan_time, 10.0)  # Should complete within 10 seconds
        self.assertGreater(size, 0)
    
    def test_database_performance_with_large_dataset(self):
        """Test database performance with large datasets"""
        test_db = os.path.join(self.test_dir, "stress_test.db")
        
        # Initialize database
        with sqlite3.connect(test_db) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE directory_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    file_count INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            ''')
            
            # Insert large number of records
            records = []
            base_time = datetime.now() - timedelta(days=30)
            
            for day in range(30):
                for hour in range(24):
                    timestamp = base_time + timedelta(days=day, hours=hour)
                    for path_id in range(10):  # 10 paths per hour
                        records.append((
                            f"/test/path_{path_id}",
                            1_000_000 * (day + 1),
                            100,
                            timestamp
                        ))
            
            # Batch insert
            start_time = time.time()
            cursor.executemany('''
                INSERT INTO directory_history (path, size_bytes, file_count, timestamp)
                VALUES (?, ?, ?, ?)
            ''', records)
            conn.commit()
            
            insert_time = time.time() - start_time
            
            self.assertLess(insert_time, 10.0)  # Should complete within 10 seconds
            self.assertEqual(len(records), 30 * 24 * 10)  # 7200 records

def run_comprehensive_tests():
    """Run all comprehensive tests"""
    
    # Test suites
    test_suites = [
        unittest.TestLoader().loadTestsFromTestCase(TestStorageMonitor),
        unittest.TestLoader().loadTestsFromTestCase(TestGrowthAnalyzer),
        unittest.TestLoader().loadTestsFromTestCase(TestAnalyticsEngine),
        unittest.TestLoader().loadTestsFromTestCase(TestImprovementIntegration),
        unittest.TestLoader().loadTestsFromTestCase(TestEndToEndIntegration),
        unittest.TestLoader().loadTestsFromTestCase(TestSystemStressTest)
    ]
    
    # Combine all test suites
    combined_suite = unittest.TestSuite(test_suites)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(combined_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"STORAGE MONITOR COMPREHENSIVE TEST RESULTS")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError: ')[-1].split(chr(10))[0]}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split(chr(10))[-2]}")
    
    print(f"\n{'='*60}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_comprehensive_tests()
    exit(0 if success else 1)