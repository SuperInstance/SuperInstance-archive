#!/usr/bin/env python3
"""
Quick Analysis Portal - Monitoring and Health Check System
"""

import time
import requests
import sqlite3
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

class SystemMonitor:
    """System monitoring and alerting"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.base_url = self.config.get('base_url', 'http://localhost:8420')
        self.db_path = self.config.get('db_path', 'data/quick_analysis.db')
        self.alert_threshold = self.config.get('alert_threshold', {
            'response_time': 2.0,  # seconds
            'cpu_usage': 80.0,     # percentage
            'memory_usage': 85.0,  # percentage
            'disk_usage': 90.0,    # percentage
            'error_rate': 5.0      # percentage
        })
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/monitoring.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def check_health(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        # HTTP health check
        health_status['checks']['http'] = self._check_http_health()
        
        # Database health check
        health_status['checks']['database'] = self._check_database_health()
        
        # System resources check
        health_status['checks']['system'] = self._check_system_resources()
        
        # Performance metrics
        health_status['checks']['performance'] = self._check_performance_metrics()
        
        # Determine overall status
        failed_checks = [name for name, check in health_status['checks'].items() 
                        if check['status'] != 'healthy']
        
        if failed_checks:
            health_status['overall_status'] = 'unhealthy'
            health_status['failed_checks'] = failed_checks
            
        return health_status

    def _check_http_health(self) -> Dict[str, Any]:
        """Check HTTP endpoint health"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                status = 'healthy' if response_time < self.alert_threshold['response_time'] else 'degraded'
                return {
                    'status': status,
                    'response_time': round(response_time, 3),
                    'status_code': response.status_code,
                    'message': 'HTTP endpoint responding'
                }
            else:
                return {
                    'status': 'unhealthy',
                    'response_time': round(response_time, 3),
                    'status_code': response.status_code,
                    'message': f'HTTP endpoint returned {response.status_code}'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'HTTP endpoint not accessible'
            }

    def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and integrity"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Test basic query
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                # Test write operation
                test_query = "SELECT datetime('now')"
                cursor.execute(test_query)
                
                return {
                    'status': 'healthy',
                    'user_count': user_count,
                    'message': 'Database accessible and functional'
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Database connection failed'
            }

    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Load average
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            # Determine status
            status = 'healthy'
            alerts = []
            
            if cpu_percent > self.alert_threshold['cpu_usage']:
                status = 'degraded'
                alerts.append(f'High CPU usage: {cpu_percent}%')
                
            if memory_percent > self.alert_threshold['memory_usage']:
                status = 'degraded'
                alerts.append(f'High memory usage: {memory_percent}%')
                
            if disk_percent > self.alert_threshold['disk_usage']:
                status = 'degraded'
                alerts.append(f'High disk usage: {disk_percent}%')
            
            return {
                'status': status,
                'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory_percent, 1),
                'disk_percent': round(disk_percent, 1),
                'load_average': [round(load, 2) for load in load_avg],
                'alerts': alerts,
                'message': 'System resources monitored'
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Failed to check system resources'
            }

    def _check_performance_metrics(self) -> Dict[str, Any]:
        """Check application performance metrics"""
        try:
            # Get recent search history for metrics
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Searches in last hour
                one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) FROM search_history 
                    WHERE timestamp > ?
                """, (one_hour_ago,))
                searches_last_hour = cursor.fetchone()[0]
                
                # Total searches today
                today = datetime.now().date().isoformat()
                cursor.execute("""
                    SELECT COUNT(*) FROM search_history 
                    WHERE DATE(timestamp) = ?
                """, (today,))
                searches_today = cursor.fetchone()[0]
                
                # Active users today
                cursor.execute("""
                    SELECT COUNT(DISTINCT session_id) FROM search_history 
                    WHERE DATE(timestamp) = ?
                """, (today,))
                active_users_today = cursor.fetchone()[0]
                
                return {
                    'status': 'healthy',
                    'searches_last_hour': searches_last_hour,
                    'searches_today': searches_today,
                    'active_users_today': active_users_today,
                    'message': 'Performance metrics collected'
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Failed to collect performance metrics'
            }

    def generate_report(self) -> str:
        """Generate detailed monitoring report"""
        health_data = self.check_health()
        
        report = f"""
Quick Analysis Portal - Health Report
=====================================
Generated: {health_data['timestamp']}
Overall Status: {health_data['overall_status'].upper()}

HTTP Service Health:
- Status: {health_data['checks']['http']['status']}
- Response Time: {health_data['checks']['http'].get('response_time', 'N/A')}s
- Status Code: {health_data['checks']['http'].get('status_code', 'N/A')}

Database Health:
- Status: {health_data['checks']['database']['status']}
- User Count: {health_data['checks']['database'].get('user_count', 'N/A')}

System Resources:
- Status: {health_data['checks']['system']['status']}
- CPU Usage: {health_data['checks']['system'].get('cpu_percent', 'N/A')}%
- Memory Usage: {health_data['checks']['system'].get('memory_percent', 'N/A')}%
- Disk Usage: {health_data['checks']['system'].get('disk_percent', 'N/A')}%

Performance Metrics:
- Searches Last Hour: {health_data['checks']['performance'].get('searches_last_hour', 'N/A')}
- Searches Today: {health_data['checks']['performance'].get('searches_today', 'N/A')}
- Active Users Today: {health_data['checks']['performance'].get('active_users_today', 'N/A')}
"""

        if health_data['overall_status'] != 'healthy':
            report += f"\n⚠️  ALERTS:\n"
            for check_name, check_data in health_data['checks'].items():
                if check_data['status'] != 'healthy':
                    report += f"- {check_name.upper()}: {check_data.get('message', 'Issue detected')}\n"
                    if 'alerts' in check_data:
                        for alert in check_data['alerts']:
                            report += f"  • {alert}\n"

        return report

    def run_continuous_monitoring(self, interval: int = 60):
        """Run continuous monitoring with specified interval"""
        self.logger.info(f"Starting continuous monitoring (interval: {interval}s)")
        
        while True:
            try:
                health_data = self.check_health()
                
                # Log current status
                self.logger.info(f"Health check completed - Status: {health_data['overall_status']}")
                
                # Alert on issues
                if health_data['overall_status'] != 'healthy':
                    self.logger.warning(f"System health degraded: {health_data.get('failed_checks', [])}")
                    # Here you could integrate with alerting systems (email, Slack, etc.)
                
                # Store metrics for historical analysis
                self._store_metrics(health_data)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                time.sleep(interval)

    def _store_metrics(self, health_data: Dict[str, Any]):
        """Store health metrics for historical analysis"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create metrics table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS health_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        overall_status TEXT,
                        http_response_time REAL,
                        cpu_percent REAL,
                        memory_percent REAL,
                        disk_percent REAL,
                        searches_last_hour INTEGER,
                        active_users_today INTEGER
                    )
                """)
                
                # Insert current metrics
                cursor.execute("""
                    INSERT INTO health_metrics 
                    (timestamp, overall_status, http_response_time, cpu_percent, 
                     memory_percent, disk_percent, searches_last_hour, active_users_today)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    health_data['timestamp'],
                    health_data['overall_status'],
                    health_data['checks']['http'].get('response_time'),
                    health_data['checks']['system'].get('cpu_percent'),
                    health_data['checks']['system'].get('memory_percent'),
                    health_data['checks']['system'].get('disk_percent'),
                    health_data['checks']['performance'].get('searches_last_hour'),
                    health_data['checks']['performance'].get('active_users_today')
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to store metrics: {e}")


def main():
    """Main monitoring function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Quick Analysis Portal Monitoring')
    parser.add_argument('--mode', choices=['check', 'monitor', 'report'], 
                       default='check', help='Monitoring mode')
    parser.add_argument('--interval', type=int, default=60, 
                       help='Monitoring interval in seconds')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    monitor = SystemMonitor(config)
    
    if args.mode == 'check':
        health_data = monitor.check_health()
        print(json.dumps(health_data, indent=2))
        
    elif args.mode == 'report':
        report = monitor.generate_report()
        print(report)
        
    elif args.mode == 'monitor':
        monitor.run_continuous_monitoring(args.interval)


if __name__ == '__main__':
    main()