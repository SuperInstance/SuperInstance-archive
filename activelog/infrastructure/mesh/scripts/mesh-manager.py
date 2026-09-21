#!/usr/bin/env python3

import os
import sys
import json
import yaml
import requests
import subprocess
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import argparse
from dataclasses import dataclass
import threading
import signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ServiceHealth:
    name: str
    status: str
    last_check: datetime
    error_count: int
    response_time: float

class MeshManager:
    def __init__(self, config_path: str = "/app/configs/mesh-config.yaml"):
        """Initialize the Mesh Manager with configuration."""
        self.config = self._load_config(config_path)
        self.consul_url = os.getenv('CONSUL_HTTP_ADDR', 'http://consul-server:8500')
        self.envoy_admin_url = os.getenv('ENVOY_ADMIN_ADDR', 'http://envoy-gateway:9901')
        self.prometheus_url = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
        self.running = False
        self.services_health = {}
        
    def _load_config(self, config_path: str) -> Dict:
        """Load mesh configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"Configuration file {config_path} not found")
            return {}
    
    def start(self):
        """Start the mesh manager."""
        logger.info("Starting ActiveLog Service Mesh Manager")
        self.running = True
        
        # Start background threads
        health_thread = threading.Thread(target=self._health_check_loop)
        health_thread.daemon = True
        health_thread.start()
        
        metrics_thread = threading.Thread(target=self._metrics_collection_loop)
        metrics_thread.daemon = True
        metrics_thread.start()
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info("Mesh Manager started successfully")
        
        # Main loop
        try:
            while self.running:
                self._process_events()
                time.sleep(10)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the mesh manager."""
        logger.info("Stopping Mesh Manager")
        self.running = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def _health_check_loop(self):
        """Background loop for health checking services."""
        while self.running:
            try:
                self._check_all_services_health()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(10)
    
    def _metrics_collection_loop(self):
        """Background loop for collecting mesh metrics."""
        while self.running:
            try:
                self._collect_mesh_metrics()
                time.sleep(60)  # Collect every minute
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(30)
    
    def _process_events(self):
        """Process mesh events and take actions."""
        # Check for service failures
        failed_services = [s for s, h in self.services_health.items() 
                          if h.status == 'unhealthy' and h.error_count > 3]
        
        for service in failed_services:
            logger.warning(f"Service {service} is consistently failing")
            self._handle_service_failure(service)
        
        # Check circuit breaker states
        self._check_circuit_breakers()
        
        # Update traffic routing if needed
        self._update_traffic_routing()
    
    def _check_all_services_health(self):
        """Check health of all registered services."""
        services = self.config.get('mesh', {}).get('services', {})
        
        for service_name, service_config in services.items():
            health = self._check_service_health(service_name, service_config)
            self.services_health[service_name] = health
            
            if health.status == 'unhealthy':
                logger.warning(f"Service {service_name} is unhealthy: {health.error_count} errors")
    
    def _check_service_health(self, service_name: str, config: Dict) -> ServiceHealth:
        """Check health of a specific service."""
        port = config.get('port', 8000)
        health_endpoint = config.get('health_check', '/health')
        
        try:
            # Get service instances from Consul
            consul_response = requests.get(
                f"{self.consul_url}/v1/health/service/{service_name}",
                timeout=5
            )
            consul_response.raise_for_status()
            
            instances = consul_response.json()
            if not instances:
                return ServiceHealth(
                    name=service_name,
                    status='no_instances',
                    last_check=datetime.now(),
                    error_count=1,
                    response_time=0
                )
            
            # Check health of first available instance
            instance = instances[0]
            service_ip = instance['Service']['Address']
            service_port = instance['Service']['Port']
            
            start_time = time.time()
            health_response = requests.get(
                f"http://{service_ip}:{service_port}{health_endpoint}",
                timeout=10
            )
            response_time = (time.time() - start_time) * 1000  # ms
            
            if health_response.status_code == 200:
                return ServiceHealth(
                    name=service_name,
                    status='healthy',
                    last_check=datetime.now(),
                    error_count=0,
                    response_time=response_time
                )
            else:
                return ServiceHealth(
                    name=service_name,
                    status='unhealthy',
                    last_check=datetime.now(),
                    error_count=1,
                    response_time=response_time
                )
                
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            current_health = self.services_health.get(service_name)
            error_count = (current_health.error_count + 1) if current_health else 1
            
            return ServiceHealth(
                name=service_name,
                status='unhealthy',
                last_check=datetime.now(),
                error_count=error_count,
                response_time=0
            )
    
    def _handle_service_failure(self, service_name: str):
        """Handle service failure by updating routing or triggering alerts."""
        logger.warning(f"Handling failure for service: {service_name}")
        
        # Remove unhealthy instances from load balancer
        self._update_service_weights(service_name, 0)
        
        # Trigger circuit breaker if configured
        self._trigger_circuit_breaker(service_name)
        
        # Send alert
        self._send_alert(f"Service {service_name} has failed multiple health checks")
    
    def _check_circuit_breakers(self):
        """Check and manage circuit breaker states."""
        try:
            # Get circuit breaker stats from Envoy
            stats_response = requests.get(f"{self.envoy_admin_url}/stats", timeout=5)
            stats_response.raise_for_status()
            
            stats_text = stats_response.text
            
            # Parse circuit breaker stats
            for line in stats_text.split('\n'):
                if 'circuit_breakers' in line and 'open' in line:
                    parts = line.split(': ')
                    if len(parts) == 2 and int(parts[1]) > 0:
                        logger.warning(f"Circuit breaker detected: {parts[0]}")
                        
        except Exception as e:
            logger.error(f"Error checking circuit breakers: {e}")
    
    def _update_traffic_routing(self):
        """Update traffic routing based on current conditions."""
        # This would implement dynamic traffic routing logic
        pass
    
    def _update_service_weights(self, service_name: str, weight: int):
        """Update service weight in Consul."""
        try:
            # Update service weight in Consul KV store
            kv_key = f"service/{service_name}/weight"
            requests.put(
                f"{self.consul_url}/v1/kv/{kv_key}",
                data=str(weight),
                timeout=5
            )
            logger.info(f"Updated weight for {service_name} to {weight}")
            
        except Exception as e:
            logger.error(f"Error updating service weight: {e}")
    
    def _trigger_circuit_breaker(self, service_name: str):
        """Trigger circuit breaker for a service."""
        try:
            # Update Envoy configuration to open circuit breaker
            config_update = {
                "version_info": str(int(time.time())),
                "resources": [{
                    "@type": "type.googleapis.com/envoy.config.cluster.v3.Cluster",
                    "name": f"{service_name}-cluster",
                    "circuit_breakers": {
                        "thresholds": [{
                            "priority": "DEFAULT",
                            "max_connections": 0,
                            "max_pending_requests": 0,
                            "max_requests": 0,
                            "max_retries": 0
                        }]
                    }
                }]
            }
            
            # This would be sent to Envoy's xDS API
            logger.info(f"Circuit breaker triggered for {service_name}")
            
        except Exception as e:
            logger.error(f"Error triggering circuit breaker: {e}")
    
    def _collect_mesh_metrics(self):
        """Collect and process mesh-wide metrics."""
        try:
            # Collect metrics from Prometheus
            metrics_queries = [
                'up{job=~".*-service"}',
                'rate(http_requests_total[5m])',
                'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
                'rate(http_requests_total{status=~"5.."}[5m])'
            ]
            
            for query in metrics_queries:
                response = requests.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={'query': query},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._process_metric_data(query, data)
                    
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    def _process_metric_data(self, query: str, data: Dict):
        """Process metric data and take actions if needed."""
        results = data.get('data', {}).get('result', [])
        
        for result in results:
            metric_name = result.get('metric', {})
            value = result.get('value', [None, None])[1]
            
            if value is not None:
                value = float(value)
                
                # Process different types of metrics
                if 'up{' in query and value == 0:
                    service = metric_name.get('job', 'unknown')
                    logger.warning(f"Service {service} is down")
                    
                elif 'error' in query and value > 0.05:  # 5% error rate
                    service = metric_name.get('service', 'unknown')
                    logger.warning(f"High error rate detected for {service}: {value:.2%}")
                    
                elif 'duration' in query and value > 2.0:  # 2 second latency
                    service = metric_name.get('service', 'unknown')
                    logger.warning(f"High latency detected for {service}: {value:.2f}s")
    
    def _send_alert(self, message: str):
        """Send alert notification."""
        timestamp = datetime.now().isoformat()
        alert_data = {
            "timestamp": timestamp,
            "message": message,
            "severity": "warning",
            "source": "mesh-manager"
        }
        
        logger.warning(f"ALERT: {message}")
        
        # Send to Slack if configured
        slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        if slack_webhook:
            try:
                requests.post(
                    slack_webhook,
                    json={"text": f"🚨 Mesh Alert: {message}"},
                    timeout=5
                )
            except Exception as e:
                logger.error(f"Error sending Slack alert: {e}")
    
    def get_mesh_status(self) -> Dict:
        """Get current mesh status."""
        return {
            "timestamp": datetime.now().isoformat(),
            "services": {
                name: {
                    "status": health.status,
                    "last_check": health.last_check.isoformat(),
                    "error_count": health.error_count,
                    "response_time_ms": health.response_time
                }
                for name, health in self.services_health.items()
            },
            "mesh_config": self.config.get('mesh', {}),
            "running": self.running
        }
    
    # CLI Commands
    def deploy_blue_green(self, service: str, new_image: str, target_color: str = "green"):
        """Deploy using blue-green strategy."""
        logger.info(f"Starting blue-green deployment for {service}")
        
        try:
            # Update deployment with new image
            subprocess.run([
                "kubectl", "set", "image", 
                f"deployment/{service}-{target_color}",
                f"{service}={new_image}",
                "-n", "activelog"
            ], check=True)
            
            # Wait for rollout
            subprocess.run([
                "kubectl", "rollout", "status",
                f"deployment/{service}-{target_color}",
                "-n", "activelog", "--timeout=300s"
            ], check=True)
            
            # Health check
            time.sleep(10)
            health = self._check_service_health(service, self.config['mesh']['services'][service])
            
            if health.status == 'healthy':
                logger.info(f"Blue-green deployment successful for {service}")
                return True
            else:
                logger.error(f"Blue-green deployment failed health check for {service}")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Blue-green deployment failed: {e}")
            return False
    
    def deploy_canary(self, service: str, new_image: str, percentage: int = 10):
        """Deploy using canary strategy."""
        logger.info(f"Starting canary deployment for {service} at {percentage}%")
        
        try:
            # Update canary deployment
            subprocess.run([
                "kubectl", "set", "image",
                f"deployment/{service}-canary",
                f"{service}={new_image}",
                "-n", "activelog"
            ], check=True)
            
            # Scale canary
            stable_replicas = int(subprocess.check_output([
                "kubectl", "get", "deployment", f"{service}-stable",
                "-o", "jsonpath={.spec.replicas}",
                "-n", "activelog"
            ]).decode().strip())
            
            canary_replicas = max(1, int(stable_replicas * percentage / 100))
            
            subprocess.run([
                "kubectl", "scale", "deployment", f"{service}-canary",
                f"--replicas={canary_replicas}",
                "-n", "activelog"
            ], check=True)
            
            # Update traffic weights
            stable_weight = 100 - percentage
            self._update_consul_weights(service, stable_weight, percentage)
            
            logger.info(f"Canary deployment started for {service}: {stable_weight}% stable, {percentage}% canary")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Canary deployment failed: {e}")
            return False
    
    def _update_consul_weights(self, service: str, stable_weight: int, canary_weight: int):
        """Update traffic weights in Consul."""
        try:
            requests.put(
                f"{self.consul_url}/v1/kv/service/{service}/stable/weight",
                data=str(stable_weight),
                timeout=5
            )
            
            requests.put(
                f"{self.consul_url}/v1/kv/service/{service}/canary/weight",
                data=str(canary_weight),
                timeout=5
            )
            
        except Exception as e:
            logger.error(f"Error updating Consul weights: {e}")

def main():
    parser = argparse.ArgumentParser(description='ActiveLog Service Mesh Manager')
    parser.add_argument('command', choices=['start', 'status', 'deploy-blue-green', 'deploy-canary'],
                       help='Command to execute')
    parser.add_argument('--service', help='Service name for deployment commands')
    parser.add_argument('--image', help='New image for deployment')
    parser.add_argument('--target-color', default='green', help='Target color for blue-green deployment')
    parser.add_argument('--percentage', type=int, default=10, help='Percentage for canary deployment')
    parser.add_argument('--config', default='/app/configs/mesh-config.yaml', help='Configuration file path')
    
    args = parser.parse_args()
    
    manager = MeshManager(args.config)
    
    if args.command == 'start':
        manager.start()
    elif args.command == 'status':
        status = manager.get_mesh_status()
        print(json.dumps(status, indent=2))
    elif args.command == 'deploy-blue-green':
        if not args.service or not args.image:
            print("Error: --service and --image are required for blue-green deployment")
            sys.exit(1)
        success = manager.deploy_blue_green(args.service, args.image, args.target_color)
        sys.exit(0 if success else 1)
    elif args.command == 'deploy-canary':
        if not args.service or not args.image:
            print("Error: --service and --image are required for canary deployment")
            sys.exit(1)
        success = manager.deploy_canary(args.service, args.image, args.percentage)
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()