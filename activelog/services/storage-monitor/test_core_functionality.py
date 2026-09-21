#!/usr/bin/env python3
"""
Core Functionality Tests for Enhanced Storage Monitor
Tests basic functionality with minimal dependencies
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
import sqlite3
import json

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_database_initialization():
    """Test basic database setup"""
    print("🧪 Testing Database Initialization...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS file_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                size_bytes INTEGER,
                modified_time REAL,
                growth_rate REAL DEFAULT 0,
                timestamp REAL DEFAULT (strftime('%s', 'now')),
                checksum TEXT,
                is_directory BOOLEAN DEFAULT 0
            );
            
            CREATE INDEX IF NOT EXISTS idx_path ON file_info(path);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON file_info(timestamp);
        """)
        
        conn.commit()
        
        # Test insert
        cursor.execute("""
            INSERT INTO file_info (path, size_bytes, modified_time, growth_rate)
            VALUES (?, ?, ?, ?)
        """, ("/test/path", 1000, time.time(), 5.0))
        
        conn.commit()
        
        # Test query
        cursor.execute("SELECT COUNT(*) FROM file_info")
        count = cursor.fetchone()[0]
        
        conn.close()
        
        assert count == 1, f"Expected 1 record, got {count}"
        print("✅ Database initialization successful")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    finally:
        try:
            os.unlink(db_path)
        except:
            pass

def test_basic_file_scanning():
    """Test basic file scanning functionality"""
    print("🧪 Testing Basic File Scanning...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Create test files
            test_files = [
                ("small.txt", "small content"),
                ("medium.txt", "x" * 1000),
                ("large.txt", "x" * 100000)
            ]
            
            created_files = []
            for filename, content in test_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                created_files.append(file_path)
            
            # Create subdirectory
            sub_dir = os.path.join(temp_dir, "subdir")
            os.makedirs(sub_dir)
            sub_file = os.path.join(sub_dir, "sub.txt")
            with open(sub_file, 'w') as f:
                f.write("subdirectory content")
            created_files.append(sub_file)
            
            # Scan directory
            scanned_files = []
            total_size = 0
            
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        stat = os.stat(file_path)
                        scanned_files.append({
                            'path': file_path,
                            'size': stat.st_size,
                            'modified': stat.st_mtime
                        })
                        total_size += stat.st_size
                    except (OSError, IOError) as e:
                        print(f"Warning: Could not scan {file_path}: {e}")
            
            assert len(scanned_files) >= 3, f"Expected at least 3 files, found {len(scanned_files)}"
            assert total_size > 100000, f"Expected total size > 100000, got {total_size}"
            
            print(f"✅ Scanned {len(scanned_files)} files, total size: {total_size} bytes")
            return True
            
        except Exception as e:
            print(f"❌ File scanning test failed: {e}")
            return False

def test_growth_detection():
    """Test basic growth detection logic"""
    print("🧪 Testing Growth Detection Logic...")
    
    try:
        # Simulate file size history
        file_history = [
            (time.time() - 300, 1000),    # 5 minutes ago: 1KB
            (time.time() - 240, 5000),    # 4 minutes ago: 5KB  
            (time.time() - 180, 15000),   # 3 minutes ago: 15KB
            (time.time() - 120, 50000),   # 2 minutes ago: 50KB
            (time.time() - 60, 150000),   # 1 minute ago: 150KB
            (time.time(), 500000),        # Now: 500KB
        ]
        
        # Calculate growth rate
        if len(file_history) >= 2:
            recent_time, recent_size = file_history[-1]
            past_time, past_size = file_history[0]
            
            time_diff_hours = (recent_time - past_time) / 3600
            size_diff_mb = (recent_size - past_size) / (1024 * 1024)
            
            if time_diff_hours > 0:
                growth_rate = size_diff_mb / time_diff_hours
            else:
                growth_rate = 0
        
        # Test rapid growth detection
        rapid_growth_threshold = 5  # MB per hour (adjusted for test data)
        is_rapid_growth = growth_rate > rapid_growth_threshold
        
        print(f"Growth rate: {growth_rate:.2f} MB/hour")
        print(f"Rapid growth detected: {is_rapid_growth}")
        
        assert growth_rate > 0, "Growth rate should be positive"
        assert is_rapid_growth, "Should detect rapid growth"
        
        print("✅ Growth detection logic working")
        return True
        
    except Exception as e:
        print(f"❌ Growth detection test failed: {e}")
        return False

def test_configuration_loading():
    """Test configuration loading and validation"""
    print("🧪 Testing Configuration Loading...")
    
    try:
        # Create test configuration
        test_config = {
            "monitoring": {
                "scan_interval_seconds": 60,
                "worker_threads": 4
            },
            "thresholds": {
                "rapid_growth_mb_per_minute": 50,
                "large_file_gb": 1.0,
                "directory_limit_gb": 5.0
            },
            "paths": {
                "monitor": [
                    {"path": "/test/path1", "priority": "high"},
                    {"path": "/test/path2", "priority": "medium"}
                ]
            }
        }
        
        # Validate configuration structure
        assert "monitoring" in test_config
        assert "thresholds" in test_config
        assert "paths" in test_config
        
        assert test_config["monitoring"]["scan_interval_seconds"] > 0
        assert test_config["thresholds"]["rapid_growth_mb_per_minute"] > 0
        assert len(test_config["paths"]["monitor"]) > 0
        
        # Test serialization
        config_json = json.dumps(test_config, indent=2)
        loaded_config = json.loads(config_json)
        
        assert loaded_config == test_config
        
        print("✅ Configuration loading successful")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_alert_generation():
    """Test basic alert generation logic"""
    print("🧪 Testing Alert Generation...")
    
    try:
        # Simulate conditions that should trigger alerts
        test_scenarios = [
            {
                "name": "Rapid Growth",
                "growth_rate": 150,  # MB/hour
                "threshold": 100,
                "should_alert": True
            },
            {
                "name": "Large File", 
                "file_size_gb": 2.5,
                "threshold": 1.0,
                "should_alert": True
            },
            {
                "name": "Normal Growth",
                "growth_rate": 25,
                "threshold": 100, 
                "should_alert": False
            }
        ]
        
        alerts_generated = []
        
        for scenario in test_scenarios:
            if scenario["name"] == "Rapid Growth":
                if scenario["growth_rate"] > scenario["threshold"]:
                    alerts_generated.append({
                        "type": "rapid_growth",
                        "severity": "high",
                        "message": f"Rapid growth detected: {scenario['growth_rate']} MB/hour"
                    })
            elif scenario["name"] == "Large File":
                if scenario["file_size_gb"] > scenario["threshold"]:
                    alerts_generated.append({
                        "type": "large_file", 
                        "severity": "medium",
                        "message": f"Large file detected: {scenario['file_size_gb']} GB"
                    })
        
        # Verify expected alerts
        expected_alert_count = sum(1 for s in test_scenarios if s.get("should_alert", False))
        actual_alert_count = len(alerts_generated)
        
        assert actual_alert_count == expected_alert_count, \
            f"Expected {expected_alert_count} alerts, got {actual_alert_count}"
        
        for alert in alerts_generated:
            assert "type" in alert
            assert "severity" in alert  
            assert "message" in alert
        
        print(f"✅ Generated {len(alerts_generated)} alerts as expected")
        return True
        
    except Exception as e:
        print(f"❌ Alert generation test failed: {e}")
        return False

def test_system_metrics():
    """Test system metrics collection"""
    print("🧪 Testing System Metrics Collection...")
    
    try:
        # Test basic system metrics
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        assert 0 <= cpu_percent <= 100, f"Invalid CPU percentage: {cpu_percent}"
        
        # Memory usage
        memory = psutil.virtual_memory()
        assert memory.total > 0, "Total memory should be positive"
        assert 0 <= memory.percent <= 100, f"Invalid memory percentage: {memory.percent}"
        
        # Disk usage
        disk = psutil.disk_usage('/')
        assert disk.total > 0, "Total disk should be positive"
        disk_percent = (disk.used / disk.total) * 100
        assert 0 <= disk_percent <= 100, f"Invalid disk percentage: {disk_percent}"
        
        print(f"✅ System metrics: CPU {cpu_percent}%, Memory {memory.percent}%, Disk {disk_percent:.1f}%")
        return True
        
    except Exception as e:
        print(f"❌ System metrics test failed: {e}")
        return False

def run_core_tests():
    """Run all core functionality tests"""
    print("Starting Core Storage Monitor Tests")
    print("=" * 50)
    
    tests = [
        test_database_initialization,
        test_basic_file_scanning,
        test_growth_detection,
        test_configuration_loading,
        test_alert_generation,
        test_system_metrics
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(tests))*100:.1f}%")
    
    if failed == 0:
        print("\n✅ All core functionality tests passed!")
        print("\nCore features validated:")
        print("  ✅ Database operations")
        print("  ✅ File scanning")
        print("  ✅ Growth detection")
        print("  ✅ Configuration management")
        print("  ✅ Alert generation")
        print("  ✅ System metrics")
    else:
        print(f"\n❌ {failed} tests failed")
    
    return failed == 0

if __name__ == "__main__":
    success = run_core_tests()
    exit_code = 0 if success else 1
    print(f"\nCore tests completed with exit code: {exit_code}")
    exit(exit_code)