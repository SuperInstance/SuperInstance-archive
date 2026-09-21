#!/usr/bin/env python3
"""
ActiveLog Instance Orchestrator
Monitors system resources and automatically scales infrastructure

Features:
- Monitors CPU/Memory usage on current t3.micro instance
- Launches t3.medium when usage > 70%
- Migrates all services to new instance
- Updates Route53 DNS records
- Terminates old instance safely
"""

import os
import sys
import json
import time
import psutil
import boto3
import logging
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from flask import Flask, jsonify, render_template
import subprocess
import requests

# Configuration
@dataclass
class OrchestratorConfig:
    # Monitoring thresholds
    cpu_threshold: float = 70.0
    memory_threshold: float = 70.0
    check_interval: int = 60  # seconds
    threshold_duration: int = 300  # 5 minutes sustained
    
    # AWS Configuration  
    region: str = "us-west-2"
    current_instance_type: str = "t3.micro"
    target_instance_type: str = "t3.medium"
    
    # Instance configuration
    ami_id: str = "ami-0c02fb55956c7d316"  # Amazon Linux 2023
    key_name: str = "personallog_key"
    security_group_id: str = "sg-06ffa55bce9e97a7f"
    subnet_id: Optional[str] = None
    
    # Services configuration
    services: List[str] = None
    service_ports: Dict[str, int] = None
    
    # Route53 configuration
    hosted_zones: Dict[str, str] = None
    
    def __post_init__(self):
        if self.services is None:
            self.services = ["personallog-backend", "fishinglog", "dmlog-session-logger"]
        
        if self.service_ports is None:
            self.service_ports = {
                "personallog-backend": 8000,
                "fishinglog": 8001,
                "dmlog-session-logger": 8002
            }
        
        if self.hosted_zones is None:
            self.hosted_zones = {
                "personallog.ai": "Z030571913A76XOUMOYWT",
                "fishinglog.ai": "Z02826911OP8QDECKH3ER", 
                "dmlog.ai": "Z00635201R85H6U037R0F"
            }

class ResourceMonitor:
    """Monitors system CPU and memory usage"""
    
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.threshold_breaches = []
        self.running = False
        
    def get_current_usage(self) -> Tuple[float, float]:
        """Get current CPU and memory usage percentages"""
        cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        return cpu_percent, memory_percent
    
    def check_threshold_breach(self, cpu: float, memory: float) -> bool:
        """Check if either CPU or memory exceeds threshold"""
        cpu_breach = cpu > self.config.cpu_threshold
        memory_breach = memory > self.config.memory_threshold
        
        if cpu_breach or memory_breach:
            breach_time = datetime.now()
            self.threshold_breaches.append({
                'timestamp': breach_time,
                'cpu': cpu,
                'memory': memory,
                'cpu_breach': cpu_breach,
                'memory_breach': memory_breach
            })
            
            # Keep only recent breaches
            cutoff_time = breach_time - timedelta(seconds=self.config.threshold_duration)
            self.threshold_breaches = [
                b for b in self.threshold_breaches 
                if b['timestamp'] > cutoff_time
            ]
            
            return len(self.threshold_breaches) >= (self.config.threshold_duration / self.config.check_interval)
        
        else:
            # Clear breaches if under threshold
            self.threshold_breaches.clear()
            return False
    
    def start_monitoring(self) -> threading.Thread:
        """Start monitoring in a separate thread"""
        self.running = True
        
        def monitor_loop():
            while self.running:
                try:
                    cpu, memory = self.get_current_usage()
                    self.logger.info(f"Resource usage - CPU: {cpu:.1f}%, Memory: {memory:.1f}%")
                    
                    if self.check_threshold_breach(cpu, memory):
                        self.logger.warning(f"Sustained threshold breach detected! CPU: {cpu:.1f}%, Memory: {memory:.1f}%")
                        # Trigger scaling event
                        return True
                        
                    time.sleep(self.config.check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Monitoring error: {e}")
                    time.sleep(30)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        return thread

class EC2Manager:
    """Manages EC2 instance operations"""
    
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.ec2_client = boto3.client('ec2', region_name=config.region)
        self.ec2_resource = boto3.resource('ec2', region_name=config.region)
        self.current_instance_id = self._get_current_instance_id()
        self.current_instance_ip = None
    
    def _get_current_instance_id(self) -> str:
        """Get the current instance ID from metadata"""
        try:
            response = requests.get(
                'http://169.254.169.254/latest/meta-data/instance-id',
                timeout=5
            )
            return response.text
        except Exception as e:
            self.logger.error(f"Failed to get instance ID: {e}")
            return "i-unknown"
    
    def get_current_instance_details(self) -> Dict:
        """Get current instance details"""
        try:
            response = self.ec2_client.describe_instances(
                InstanceIds=[self.current_instance_id]
            )
            instance = response['Reservations'][0]['Instances'][0]
            
            return {
                'instance_id': instance['InstanceId'],
                'instance_type': instance['InstanceType'],
                'public_ip': instance.get('PublicIpAddress'),
                'private_ip': instance.get('PrivateIpAddress'),
                'state': instance['State']['Name'],
                'ami_id': instance['ImageId'],
                'key_name': instance.get('KeyName'),
                'security_groups': [sg['GroupId'] for sg in instance['SecurityGroups']],
                'subnet_id': instance.get('SubnetId')
            }
        except Exception as e:
            self.logger.error(f"Failed to get instance details: {e}")
            return {}
    
    def launch_new_instance(self) -> str:
        """Launch a new t3.medium instance"""
        try:
            current_details = self.get_current_instance_details()
            
            # Use current instance configuration as template
            launch_params = {
                'ImageId': current_details.get('ami_id', self.config.ami_id),
                'InstanceType': self.config.target_instance_type,
                'KeyName': current_details.get('key_name', self.config.key_name),
                'SecurityGroupIds': current_details.get('security_groups', [self.config.security_group_id]),
                'MinCount': 1,
                'MaxCount': 1,
                'TagSpecifications': [
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {'Key': 'Name', 'Value': 'ActiveLog-Scaled-Instance'},
                            {'Key': 'Environment', 'Value': 'production'},
                            {'Key': 'ManagedBy', 'Value': 'instance-orchestrator'},
                            {'Key': 'ScaledFrom', 'Value': self.current_instance_id}
                        ]
                    }
                ]
            }
            
            # Add subnet if available
            if current_details.get('subnet_id'):
                launch_params['SubnetId'] = current_details['subnet_id']
            
            self.logger.info(f"Launching new {self.config.target_instance_type} instance...")
            response = self.ec2_client.run_instances(**launch_params)
            
            new_instance_id = response['Instances'][0]['InstanceId']
            self.logger.info(f"New instance launched: {new_instance_id}")
            
            # Wait for instance to be running
            self._wait_for_instance_running(new_instance_id)
            
            return new_instance_id
            
        except Exception as e:
            self.logger.error(f"Failed to launch new instance: {e}")
            raise
    
    def _wait_for_instance_running(self, instance_id: str, timeout: int = 300) -> Dict:
        """Wait for instance to be in running state"""
        self.logger.info(f"Waiting for instance {instance_id} to be running...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
                instance = response['Reservations'][0]['Instances'][0]
                state = instance['State']['Name']
                
                if state == 'running':
                    self.logger.info(f"Instance {instance_id} is now running")
                    return {
                        'instance_id': instance_id,
                        'public_ip': instance.get('PublicIpAddress'),
                        'private_ip': instance.get('PrivateIpAddress')
                    }
                elif state in ['terminated', 'terminating']:
                    raise Exception(f"Instance {instance_id} was terminated")
                
                self.logger.info(f"Instance {instance_id} state: {state}")
                time.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error waiting for instance: {e}")
                time.sleep(30)
        
        raise Exception(f"Timeout waiting for instance {instance_id} to be running")
    
    def terminate_instance(self, instance_id: str):
        """Terminate an instance"""
        try:
            self.logger.info(f"Terminating instance {instance_id}...")
            self.ec2_client.terminate_instances(InstanceIds=[instance_id])
            self.logger.info(f"Instance {instance_id} termination initiated")
        except Exception as e:
            self.logger.error(f"Failed to terminate instance {instance_id}: {e}")
            raise

class ServiceMigrator:
    """Handles service migration between instances"""
    
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def prepare_new_instance(self, new_instance_ip: str) -> bool:
        """Prepare the new instance with required software and configuration"""
        try:
            self.logger.info(f"Preparing new instance {new_instance_ip}...")
            
            # Commands to prepare the instance
            prep_commands = [
                # Update system
                "sudo yum update -y",
                
                # Install required packages
                "sudo yum install -y python3 python3-pip nginx git rsync",
                
                # Install Node.js if needed
                "curl -sL https://rpm.nodesource.com/setup_18.x | sudo bash -",
                "sudo yum install -y nodejs",
                
                # Create application directory
                "sudo mkdir -p /home/ubuntu/activelog",
                "sudo chown ubuntu:ubuntu /home/ubuntu/activelog",
                
                # Install Python packages
                "pip3 install flask boto3 psutil requests"
            ]
            
            for cmd in prep_commands:
                result = self._run_remote_command(new_instance_ip, cmd)
                if result != 0:
                    self.logger.error(f"Failed to run preparation command: {cmd}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to prepare new instance: {e}")
            return False
    
    def migrate_services(self, old_ip: str, new_ip: str) -> bool:
        """Migrate all services from old instance to new instance"""
        try:
            self.logger.info(f"Migrating services from {old_ip} to {new_ip}...")
            
            # Copy service files
            for service in self.config.services:
                if not self._migrate_service(service, old_ip, new_ip):
                    return False
            
            # Copy nginx configuration
            if not self._migrate_nginx_config(old_ip, new_ip):
                return False
            
            # Start services on new instance
            if not self._start_services_on_new_instance(new_ip):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Service migration failed: {e}")
            return False
    
    def _migrate_service(self, service_name: str, old_ip: str, new_ip: str) -> bool:
        """Migrate a specific service"""
        try:
            self.logger.info(f"Migrating service: {service_name}")
            
            # Copy service directory
            rsync_cmd = f"""
                rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
                ubuntu@{old_ip}:/home/ubuntu/activelog/services/{service_name}/ \
                ubuntu@{new_ip}:/home/ubuntu/activelog/services/{service_name}/
            """
            
            result = subprocess.run(rsync_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"Failed to copy {service_name}: {result.stderr}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate service {service_name}: {e}")
            return False
    
    def _migrate_nginx_config(self, old_ip: str, new_ip: str) -> bool:
        """Migrate nginx configuration"""
        try:
            self.logger.info("Migrating nginx configuration...")
            
            # Copy nginx sites-available
            rsync_cmd = f"""
                rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
                ubuntu@{old_ip}:/etc/nginx/sites-available/ \
                ubuntu@{new_ip}:/tmp/nginx-sites/
            """
            
            subprocess.run(rsync_cmd, shell=True)
            
            # Install nginx config on new instance
            install_cmd = """
                sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled && \
                sudo cp /tmp/nginx-sites/* /etc/nginx/sites-available/ && \
                sudo ln -sf /etc/nginx/sites-available/multi-domain /etc/nginx/sites-enabled/ && \
                sudo nginx -t && \
                sudo systemctl enable nginx && \
                sudo systemctl start nginx
            """
            
            return self._run_remote_command(new_ip, install_cmd) == 0
            
        except Exception as e:
            self.logger.error(f"Failed to migrate nginx config: {e}")
            return False
    
    def _start_services_on_new_instance(self, new_ip: str) -> bool:
        """Start all services on the new instance"""
        try:
            self.logger.info("Starting services on new instance...")
            
            for service_name in self.config.services:
                port = self.config.service_ports.get(service_name, 8000)
                
                start_cmd = f"""
                    cd /home/ubuntu/activelog/services/{service_name} && \
                    nohup python3 main.py > service.log 2>&1 &
                """
                
                if self._run_remote_command(new_ip, start_cmd) != 0:
                    self.logger.error(f"Failed to start service {service_name}")
                    return False
                
                # Wait a bit for service to start
                time.sleep(5)
                
                # Verify service is responding
                if not self._verify_service_health(new_ip, port):
                    self.logger.error(f"Service {service_name} not responding on port {port}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start services: {e}")
            return False
    
    def _run_remote_command(self, ip: str, command: str) -> int:
        """Run a command on remote instance via SSH"""
        ssh_cmd = f'ssh -o StrictHostKeyChecking=no ubuntu@{ip} "{command}"'
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.logger.error(f"Command failed on {ip}: {result.stderr}")
        
        return result.returncode
    
    def _verify_service_health(self, ip: str, port: int) -> bool:
        """Verify service is responding on given port"""
        try:
            response = requests.get(f"http://{ip}:{port}/health", timeout=10)
            return response.status_code == 200
        except:
            return False

class Route53Manager:
    """Manages Route53 DNS updates"""
    
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.route53_client = boto3.client('route53', region_name=config.region)
    
    def update_dns_records(self, new_ip: str) -> bool:
        """Update all DNS records to point to new IP"""
        try:
            self.logger.info(f"Updating DNS records to point to {new_ip}...")
            
            for domain, hosted_zone_id in self.config.hosted_zones.items():
                if not self._update_a_record(domain, hosted_zone_id, new_ip):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"DNS update failed: {e}")
            return False
    
    def _update_a_record(self, domain: str, hosted_zone_id: str, new_ip: str) -> bool:
        """Update A record for a specific domain"""
        try:
            change_batch = {
                'Changes': [{
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': domain,
                        'Type': 'A',
                        'TTL': 60,  # Low TTL for faster propagation
                        'ResourceRecords': [{'Value': new_ip}]
                    }
                }]
            }
            
            response = self.route53_client.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch=change_batch
            )
            
            change_id = response['ChangeInfo']['Id']
            self.logger.info(f"DNS update initiated for {domain}: {change_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update DNS for {domain}: {e}")
            return False

class InstanceOrchestrator:
    """Main orchestrator that coordinates all scaling operations"""
    
    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()
        self.setup_logging()
        
        self.resource_monitor = ResourceMonitor(self.config)
        self.ec2_manager = EC2Manager(self.config)
        self.service_migrator = ServiceMigrator(self.config)
        self.route53_manager = Route53Manager(self.config)
        
        self.scaling_in_progress = False
        self.last_scale_time = None
        
        # Flask app for monitoring dashboard
        self.app = Flask(__name__)
        self.setup_flask_routes()
    
    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/instance-orchestrator.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_flask_routes(self):
        """Setup Flask routes for monitoring dashboard"""
        
        @self.app.route('/')
        def dashboard():
            return render_template('dashboard.html')
        
        @self.app.route('/api/status')
        def api_status():
            cpu, memory = self.resource_monitor.get_current_usage()
            instance_details = self.ec2_manager.get_current_instance_details()
            
            return jsonify({
                'status': 'running',
                'scaling_in_progress': self.scaling_in_progress,
                'last_scale_time': self.last_scale_time.isoformat() if self.last_scale_time else None,
                'current_usage': {
                    'cpu_percent': cpu,
                    'memory_percent': memory
                },
                'thresholds': {
                    'cpu_threshold': self.config.cpu_threshold,
                    'memory_threshold': self.config.memory_threshold
                },
                'instance_details': instance_details,
                'threshold_breaches': len(self.resource_monitor.threshold_breaches),
                'services': self.config.services
            })
        
        @self.app.route('/health')
        def health():
            return jsonify({'status': 'healthy', 'service': 'instance-orchestrator'})
        
        @self.app.route('/trigger-scale', methods=['POST'])
        def trigger_manual_scale():
            if not self.scaling_in_progress:
                threading.Thread(target=self.perform_scaling, daemon=True).start()
                return jsonify({'status': 'scaling_triggered'})
            else:
                return jsonify({'status': 'scaling_already_in_progress'})
    
    def perform_scaling(self) -> bool:
        """Perform the complete scaling operation"""
        if self.scaling_in_progress:
            self.logger.warning("Scaling already in progress, skipping...")
            return False
        
        self.scaling_in_progress = True
        self.last_scale_time = datetime.now()
        
        try:
            self.logger.info("=== STARTING SCALING OPERATION ===")
            
            # Step 1: Launch new instance
            self.logger.info("Step 1: Launching new t3.medium instance...")
            new_instance_id = self.ec2_manager.launch_new_instance()
            
            # Get new instance IP
            time.sleep(30)  # Wait for IP assignment
            new_instance_details = self.ec2_manager._wait_for_instance_running(new_instance_id)
            new_instance_ip = new_instance_details['public_ip']
            
            if not new_instance_ip:
                raise Exception("New instance has no public IP")
            
            # Step 2: Prepare new instance
            self.logger.info("Step 2: Preparing new instance...")
            if not self.service_migrator.prepare_new_instance(new_instance_ip):
                raise Exception("Failed to prepare new instance")
            
            # Step 3: Migrate services
            self.logger.info("Step 3: Migrating services...")
            current_instance_details = self.ec2_manager.get_current_instance_details()
            current_ip = current_instance_details['public_ip']
            
            if not self.service_migrator.migrate_services(current_ip, new_instance_ip):
                raise Exception("Service migration failed")
            
            # Step 4: Update DNS
            self.logger.info("Step 4: Updating DNS records...")
            if not self.route53_manager.update_dns_records(new_instance_ip):
                raise Exception("DNS update failed")
            
            # Step 5: Wait for DNS propagation and verify
            self.logger.info("Step 5: Waiting for DNS propagation...")
            time.sleep(120)  # Wait 2 minutes for DNS
            
            # Verify services are accessible via new IP
            for service_name in self.config.services:
                port = self.config.service_ports.get(service_name, 8000)
                if not self.service_migrator._verify_service_health(new_instance_ip, port):
                    self.logger.error(f"Service {service_name} not accessible after migration")
                    # Continue anyway, services might need more time
            
            # Step 6: Terminate old instance
            self.logger.info("Step 6: Terminating old instance...")
            old_instance_id = self.ec2_manager.current_instance_id
            
            # Wait a bit more to ensure everything is stable
            time.sleep(180)  # Wait 3 minutes
            
            self.ec2_manager.terminate_instance(old_instance_id)
            
            self.logger.info("=== SCALING OPERATION COMPLETED SUCCESSFULLY ===")
            self.logger.info(f"Scaled from {current_ip} to {new_instance_ip}")
            return True
            
        except Exception as e:
            self.logger.error(f"Scaling operation failed: {e}")
            # TODO: Implement rollback logic
            return False
        
        finally:
            self.scaling_in_progress = False
    
    def start(self, port: int = 8500):
        """Start the instance orchestrator"""
        self.logger.info("Starting Instance Orchestrator...")
        
        # Start resource monitoring
        monitor_thread = self.resource_monitor.start_monitoring()
        
        # Start Flask dashboard
        self.logger.info(f"Starting monitoring dashboard on port {port}")
        self.app.run(host='0.0.0.0', port=port, debug=False)

def main():
    """Main entry point"""
    config = OrchestratorConfig()
    
    # Override config from environment variables if available
    config.cpu_threshold = float(os.environ.get('CPU_THRESHOLD', config.cpu_threshold))
    config.memory_threshold = float(os.environ.get('MEMORY_THRESHOLD', config.memory_threshold))
    config.region = os.environ.get('AWS_REGION', config.region)
    
    orchestrator = InstanceOrchestrator(config)
    
    # Start monitoring loop in background
    def monitoring_loop():
        while True:
            try:
                if not orchestrator.scaling_in_progress:
                    cpu, memory = orchestrator.resource_monitor.get_current_usage()
                    
                    if orchestrator.resource_monitor.check_threshold_breach(cpu, memory):
                        orchestrator.logger.warning("Threshold breach detected, triggering scaling...")
                        threading.Thread(target=orchestrator.perform_scaling, daemon=True).start()
                
                time.sleep(orchestrator.config.check_interval)
                
            except Exception as e:
                orchestrator.logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)
    
    # Start monitoring in background
    threading.Thread(target=monitoring_loop, daemon=True).start()
    
    # Start the Flask dashboard
    port = int(os.environ.get('PORT', 8500))
    orchestrator.start(port)

if __name__ == "__main__":
    main()