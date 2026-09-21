#!/usr/bin/env python3

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
import json
import logging
import time
import argparse
from typing import Dict, List, Tuple, Optional
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceRegressionDetector:
    def __init__(self, config_path: str = "/etc/regression-detector/config.yaml"):
        """Initialize the regression detector with configuration."""
        self.config = self._load_config(config_path)
        self.prometheus_url = self.config['prometheus']['url']
        self.alertmanager_url = self.config['alertmanager']['url']
        self.metrics = self.config['metrics']
        self.thresholds = self.config['thresholds']
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Return default configuration."""
        return {
            'prometheus': {
                'url': 'http://prometheus:9090'
            },
            'alertmanager': {
                'url': 'http://alertmanager:9093'
            },
            'metrics': {
                'latency_metrics': [
                    'http_request_duration_seconds',
                    'grpc_server_handling_seconds',
                    'ai_model_inference_duration_seconds',
                    'database_query_duration_seconds'
                ],
                'throughput_metrics': [
                    'http_requests_total',
                    'grpc_server_started_total',
                    'ai_model_inference_total',
                    'database_queries_total'
                ],
                'error_metrics': [
                    'http_requests_total{status=~"5.."}',
                    'grpc_server_started_total{grpc_code!="OK"}',
                    'ai_model_inference_errors_total',
                    'database_query_errors_total'
                ]
            },
            'thresholds': {
                'latency_increase_percentage': 50,
                'throughput_decrease_percentage': 30,
                'error_rate_increase_multiplier': 2.0,
                'statistical_significance': 0.05
            }
        }
    
    def query_prometheus(self, query: str, start_time: datetime, end_time: datetime, step: str = '1m') -> Dict:
        """Query Prometheus for metrics data."""
        url = f"{self.prometheus_url}/api/v1/query_range"
        params = {
            'query': query,
            'start': start_time.timestamp(),
            'end': end_time.timestamp(),
            'step': step
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to query Prometheus: {e}")
            return {'data': {'result': []}}
    
    def calculate_percentile(self, metric_name: str, percentile: float, start_time: datetime, end_time: datetime) -> List[Tuple[datetime, float]]:
        """Calculate percentile values for a metric over time."""
        query = f"histogram_quantile({percentile/100}, rate({metric_name}_bucket[5m]))"
        result = self.query_prometheus(query, start_time, end_time)
        
        data_points = []
        for series in result['data']['result']:
            for timestamp, value in series['values']:
                try:
                    data_points.append((datetime.fromtimestamp(float(timestamp)), float(value)))
                except (ValueError, TypeError):
                    continue
        
        return sorted(data_points)
    
    def calculate_rate(self, metric_name: str, start_time: datetime, end_time: datetime) -> List[Tuple[datetime, float]]:
        """Calculate rate of increase for a counter metric."""
        query = f"rate({metric_name}[5m])"
        result = self.query_prometheus(query, start_time, end_time)
        
        data_points = []
        for series in result['data']['result']:
            for timestamp, value in series['values']:
                try:
                    data_points.append((datetime.fromtimestamp(float(timestamp)), float(value)))
                except (ValueError, TypeError):
                    continue
        
        return sorted(data_points)
    
    def detect_latency_regression(self, service: str) -> List[Dict]:
        """Detect latency regressions by comparing current vs historical performance."""
        regressions = []
        current_time = datetime.now()
        
        # Compare last hour vs same hour yesterday
        current_start = current_time - timedelta(hours=1)
        baseline_start = current_time - timedelta(days=1, hours=1)
        baseline_end = current_time - timedelta(days=1)
        
        for metric in self.metrics['latency_metrics']:
            # Get current performance data
            current_p95 = self.calculate_percentile(metric, 95, current_start, current_time)
            current_p99 = self.calculate_percentile(metric, 99, current_start, current_time)
            
            # Get baseline performance data
            baseline_p95 = self.calculate_percentile(metric, 95, baseline_start, baseline_end)
            baseline_p99 = self.calculate_percentile(metric, 99, baseline_start, baseline_end)
            
            if not current_p95 or not baseline_p95:
                continue
            
            # Calculate averages
            current_avg_p95 = np.mean([point[1] for point in current_p95])
            baseline_avg_p95 = np.mean([point[1] for point in baseline_p95])
            
            current_avg_p99 = np.mean([point[1] for point in current_p99])
            baseline_avg_p99 = np.mean([point[1] for point in baseline_p99])
            
            # Check for regression
            p95_increase = ((current_avg_p95 - baseline_avg_p95) / baseline_avg_p95) * 100
            p99_increase = ((current_avg_p99 - baseline_avg_p99) / baseline_avg_p99) * 100
            
            if p95_increase > self.thresholds['latency_increase_percentage']:
                regressions.append({
                    'type': 'latency_regression',
                    'metric': metric,
                    'percentile': 95,
                    'service': service,
                    'current_value': current_avg_p95,
                    'baseline_value': baseline_avg_p95,
                    'increase_percentage': p95_increase,
                    'severity': 'high' if p95_increase > 100 else 'medium',
                    'timestamp': current_time.isoformat()
                })
            
            if p99_increase > self.thresholds['latency_increase_percentage']:
                regressions.append({
                    'type': 'latency_regression',
                    'metric': metric,
                    'percentile': 99,
                    'service': service,
                    'current_value': current_avg_p99,
                    'baseline_value': baseline_avg_p99,
                    'increase_percentage': p99_increase,
                    'severity': 'critical' if p99_increase > 200 else 'high',
                    'timestamp': current_time.isoformat()
                })
        
        return regressions
    
    def detect_throughput_regression(self, service: str) -> List[Dict]:
        """Detect throughput regressions."""
        regressions = []
        current_time = datetime.now()
        
        current_start = current_time - timedelta(hours=1)
        baseline_start = current_time - timedelta(days=1, hours=1)
        baseline_end = current_time - timedelta(days=1)
        
        for metric in self.metrics['throughput_metrics']:
            current_rates = self.calculate_rate(metric, current_start, current_time)
            baseline_rates = self.calculate_rate(metric, baseline_start, baseline_end)
            
            if not current_rates or not baseline_rates:
                continue
            
            current_avg = np.mean([point[1] for point in current_rates])
            baseline_avg = np.mean([point[1] for point in baseline_rates])
            
            if baseline_avg == 0:
                continue
            
            decrease_percentage = ((baseline_avg - current_avg) / baseline_avg) * 100
            
            if decrease_percentage > self.thresholds['throughput_decrease_percentage']:
                regressions.append({
                    'type': 'throughput_regression',
                    'metric': metric,
                    'service': service,
                    'current_value': current_avg,
                    'baseline_value': baseline_avg,
                    'decrease_percentage': decrease_percentage,
                    'severity': 'critical' if decrease_percentage > 70 else 'high',
                    'timestamp': current_time.isoformat()
                })
        
        return regressions
    
    def detect_error_rate_regression(self, service: str) -> List[Dict]:
        """Detect error rate regressions."""
        regressions = []
        current_time = datetime.now()
        
        current_start = current_time - timedelta(hours=1)
        baseline_start = current_time - timedelta(days=1, hours=1)
        baseline_end = current_time - timedelta(days=1)
        
        for metric in self.metrics['error_metrics']:
            current_errors = self.calculate_rate(metric, current_start, current_time)
            baseline_errors = self.calculate_rate(metric, baseline_start, baseline_end)
            
            if not current_errors or not baseline_errors:
                continue
            
            current_avg = np.mean([point[1] for point in current_errors])
            baseline_avg = np.mean([point[1] for point in baseline_errors])
            
            if baseline_avg == 0 and current_avg > 0:
                # New errors appeared
                regressions.append({
                    'type': 'error_rate_regression',
                    'metric': metric,
                    'service': service,
                    'current_value': current_avg,
                    'baseline_value': baseline_avg,
                    'increase_multiplier': float('inf'),
                    'severity': 'critical',
                    'timestamp': current_time.isoformat()
                })
            elif baseline_avg > 0:
                increase_multiplier = current_avg / baseline_avg
                
                if increase_multiplier > self.thresholds['error_rate_increase_multiplier']:
                    regressions.append({
                        'type': 'error_rate_regression',
                        'metric': metric,
                        'service': service,
                        'current_value': current_avg,
                        'baseline_value': baseline_avg,
                        'increase_multiplier': increase_multiplier,
                        'severity': 'critical' if increase_multiplier > 5 else 'high',
                        'timestamp': current_time.isoformat()
                    })
        
        return regressions
    
    def send_alert(self, regression: Dict):
        """Send alert to AlertManager."""
        alert = {
            'labels': {
                'alertname': 'PerformanceRegression',
                'service': regression['service'],
                'type': regression['type'],
                'severity': regression['severity'],
                'metric': regression['metric']
            },
            'annotations': {
                'summary': f"Performance regression detected in {regression['service']}",
                'description': f"Regression in {regression['metric']}: {json.dumps(regression, indent=2)}"
            },
            'startsAt': regression['timestamp']
        }
        
        try:
            response = requests.post(
                f"{self.alertmanager_url}/api/v1/alerts",
                json=[alert],
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Alert sent for regression: {regression['type']} in {regression['service']}")
        except requests.RequestException as e:
            logger.error(f"Failed to send alert: {e}")
    
    def run_detection_cycle(self):
        """Run a complete detection cycle for all services."""
        services = [
            'api-gateway', 'auth-service', 'metadata-service', 'file-processor-service',
            'ai-orchestrator-service', 'notification-service', 'backup-service',
            'collaboration-service', 'data-export-service', 'document-ai-service',
            'graphql-service', 'mobile-api-service', 'ml-pipeline-service',
            'smart-folders-service', 'sync-engine-service', 'video-pipeline-service',
            'video-processor-service', 'workflows-service', 'analytics-service',
            'batch-import-service', 'cache-service', 'p2p-sync-service', 'file-watcher-service'
        ]
        
        all_regressions = []
        
        for service in services:
            logger.info(f"Checking performance for service: {service}")
            
            try:
                latency_regressions = self.detect_latency_regression(service)
                throughput_regressions = self.detect_throughput_regression(service)
                error_regressions = self.detect_error_rate_regression(service)
                
                all_regressions.extend(latency_regressions)
                all_regressions.extend(throughput_regressions)
                all_regressions.extend(error_regressions)
                
                # Send alerts for any regressions found
                for regression in latency_regressions + throughput_regressions + error_regressions:
                    self.send_alert(regression)
                    
            except Exception as e:
                logger.error(f"Error checking service {service}: {e}")
                continue
        
        logger.info(f"Detection cycle complete. Found {len(all_regressions)} regressions.")
        return all_regressions

def main():
    parser = argparse.ArgumentParser(description='Performance Regression Detector')
    parser.add_argument('--config', default='/etc/regression-detector/config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--interval', type=int, default=300,
                       help='Detection interval in seconds (default: 5 minutes)')
    parser.add_argument('--single-run', action='store_true',
                       help='Run detection once and exit')
    
    args = parser.parse_args()
    
    detector = PerformanceRegressionDetector(args.config)
    
    if args.single_run:
        regressions = detector.run_detection_cycle()
        print(json.dumps(regressions, indent=2))
    else:
        logger.info(f"Starting continuous detection with {args.interval}s interval")
        while True:
            try:
                detector.run_detection_cycle()
                time.sleep(args.interval)
            except KeyboardInterrupt:
                logger.info("Stopping detection...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(60)  # Wait a minute before retrying

if __name__ == '__main__':
    main()