#!/usr/bin/env python3
"""
DMLog SuperInstance Cluster Manager
Intelligent load balancing and auto-scaling for D&D gaming
"""

import boto3
import time
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DMLogClusterManager:
    """Manages DMLog SuperInstance cluster for optimal gaming performance"""
    
    def __init__(self):
        self.ec2 = boto3.client('ec2', region_name='us-west-2')
        self.elbv2 = boto3.client('elbv2', region_name='us-west-2')
        self.cloudwatch = boto3.client('cloudwatch', region_name='us-west-2')
        
        # Cluster configuration
        self.cluster_config = {
            'instances': [],
            'load_balancer_arn': '',
            'target_group_arn': '',
            'min_instances': 1,
            'max_instances': 3,
            'scale_up_threshold': 70,    # CPU % to add instance
            'scale_down_threshold': 30,  # CPU % to remove instance
            'gaming_session_threshold': 25  # Active users per instance
        }
        
        # Load existing cluster info
        self.discover_cluster()
    
    def discover_cluster(self):
        """Discover existing DMLog cluster infrastructure"""
        try:
            # Find DMLog instances
            response = self.ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Project', 'Values': ['DMLog']},
                    {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
                ]
            )
            
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        'instance_id': instance['InstanceId'],
                        'state': instance['State']['Name'],
                        'ip': instance.get('PublicIpAddress', ''),
                        'private_ip': instance.get('PrivateIpAddress', ''),
                        'type': instance['InstanceType'],
                        'role': self._get_tag_value(instance.get('Tags', []), 'Role', 'unknown')
                    })
            
            self.cluster_config['instances'] = instances
            logger.info(f"Discovered {len(instances)} DMLog instances")
            
            # Find load balancer
            albs = self.elbv2.describe_load_balancers()
            for alb in albs['LoadBalancers']:
                if 'dmlog' in alb['LoadBalancerName'].lower():
                    self.cluster_config['load_balancer_arn'] = alb['LoadBalancerArn']
                    self.cluster_config['dns_name'] = alb['DNSName']
                    break
                    
        except Exception as e:
            logger.error(f"Error discovering cluster: {e}")
    
    def _get_tag_value(self, tags: List[Dict], key: str, default: str = '') -> str:
        """Get tag value from tags list"""
        for tag in tags:
            if tag['Key'] == key:
                return tag['Value']
        return default
    
    def start_cluster(self, target_instances: int = 1) -> Dict[str, Any]:
        """Start DMLog cluster with specified number of instances"""
        logger.info(f"Starting DMLog cluster with {target_instances} instances")
        
        available_instances = [
            inst for inst in self.cluster_config['instances'] 
            if inst['state'] == 'stopped'
        ]
        
        if len(available_instances) < target_instances:
            return {
                'success': False,
                'message': f"Only {len(available_instances)} stopped instances available"
            }
        
        # Start instances in priority order (primary first)
        instances_to_start = sorted(
            available_instances[:target_instances],
            key=lambda x: {'primary': 0, 'secondary': 1, 'tertiary': 2}.get(x['role'], 3)
        )
        
        instance_ids = [inst['instance_id'] for inst in instances_to_start]
        
        try:
            self.ec2.start_instances(InstanceIds=instance_ids)
            
            # Wait for instances to be running
            logger.info("Waiting for instances to start...")
            self.ec2.get_waiter('instance_running').wait(InstanceIds=instance_ids)
            
            # Wait for services to be healthy
            time.sleep(60)  # Give services time to start
            
            healthy_count = 0
            for instance in instances_to_start:
                if self._check_instance_health(instance['instance_id']):
                    healthy_count += 1
            
            return {
                'success': True,
                'started_instances': len(instance_ids),
                'healthy_instances': healthy_count,
                'gaming_url': f"http://{self.cluster_config.get('dns_name', 'cluster-not-ready')}",
                'instance_ids': instance_ids
            }
            
        except Exception as e:
            logger.error(f"Error starting cluster: {e}")
            return {'success': False, 'message': str(e)}
    
    def stop_cluster(self) -> Dict[str, Any]:
        """Stop all running DMLog instances"""
        logger.info("Stopping DMLog cluster")
        
        running_instances = [
            inst for inst in self.cluster_config['instances'] 
            if inst['state'] == 'running'
        ]
        
        if not running_instances:
            return {'success': True, 'message': 'No running instances to stop'}
        
        instance_ids = [inst['instance_id'] for inst in running_instances]
        
        try:
            self.ec2.stop_instances(InstanceIds=instance_ids)
            logger.info(f"Stopped {len(instance_ids)} instances")
            
            return {
                'success': True,
                'stopped_instances': len(instance_ids),
                'cost_savings': f"~${len(instance_ids) * 2}/hour"
            }
            
        except Exception as e:
            logger.error(f"Error stopping cluster: {e}")
            return {'success': False, 'message': str(e)}
    
    def _check_instance_health(self, instance_id: str) -> bool:
        """Check if instance gaming services are healthy"""
        try:
            # Get instance public IP
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            public_ip = instance.get('PublicIpAddress')
            
            if not public_ip:
                return False
            
            # Check health endpoint
            health_response = requests.get(f"http://{public_ip}/health", timeout=10)
            return health_response.status_code == 200
            
        except Exception as e:
            logger.debug(f"Health check failed for {instance_id}: {e}")
            return False
    
    def get_gaming_metrics(self) -> Dict[str, Any]:
        """Get gaming-specific metrics from all instances"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cluster_health': 'unknown',
            'total_instances': len(self.cluster_config['instances']),
            'running_instances': 0,
            'active_gaming_sessions': 0,
            'total_voice_connections': 0,
            'ai_requests_per_minute': 0,
            'average_response_time': 0,
            'cost_per_hour': 0
        }
        
        running_instances = []
        for instance in self.cluster_config['instances']:
            if instance['state'] == 'running':
                running_instances.append(instance)
                metrics['running_instances'] += 1
                
                # Estimate cost (GPU instances)
                if 'g4dn' in instance['type']:
                    metrics['cost_per_hour'] += 1.5  # ~$1.5/hour per GPU instance
                else:
                    metrics['cost_per_hour'] += 0.5  # CPU instances
        
        # Check cluster health
        healthy_instances = 0
        for instance in running_instances:
            try:
                if self._check_instance_health(instance['instance_id']):
                    healthy_instances += 1
                    
                    # Get gaming metrics from instance
                    public_ip = instance['ip']
                    if public_ip:
                        gaming_response = requests.get(
                            f"http://{public_ip}/api/gaming_metrics", 
                            timeout=5
                        )
                        if gaming_response.status_code == 200:
                            instance_metrics = gaming_response.json()
                            metrics['active_gaming_sessions'] += instance_metrics.get('active_sessions', 0)
                            metrics['total_voice_connections'] += instance_metrics.get('voice_connections', 0)
                            metrics['ai_requests_per_minute'] += instance_metrics.get('ai_requests_per_min', 0)
                            
            except Exception as e:
                logger.debug(f"Error getting metrics from {instance['instance_id']}: {e}")
        
        # Determine cluster health
        if healthy_instances == 0:
            metrics['cluster_health'] = 'down'
        elif healthy_instances == metrics['running_instances']:
            metrics['cluster_health'] = 'healthy'
        else:
            metrics['cluster_health'] = 'degraded'
        
        return metrics
    
    def auto_scale_decision(self) -> Dict[str, Any]:
        """Make intelligent scaling decisions based on gaming load"""
        metrics = self.get_gaming_metrics()
        
        decision = {
            'action': 'none',
            'reason': '',
            'recommended_instances': metrics['running_instances']
        }
        
        current_instances = metrics['running_instances']
        active_sessions = metrics['active_gaming_sessions']
        
        # Calculate load per instance
        if current_instances > 0:
            sessions_per_instance = active_sessions / current_instances
            
            # Scale up if too many sessions per instance
            if sessions_per_instance > self.cluster_config['gaming_session_threshold']:
                if current_instances < self.cluster_config['max_instances']:
                    decision['action'] = 'scale_up'
                    decision['reason'] = f'High gaming load: {sessions_per_instance:.1f} sessions/instance'
                    decision['recommended_instances'] = min(current_instances + 1, self.cluster_config['max_instances'])
            
            # Scale down if very low load
            elif sessions_per_instance < 5 and current_instances > self.cluster_config['min_instances']:
                decision['action'] = 'scale_down'
                decision['reason'] = f'Low gaming load: {sessions_per_instance:.1f} sessions/instance'
                decision['recommended_instances'] = max(current_instances - 1, self.cluster_config['min_instances'])
        
        return decision
    
    def execute_scaling(self, target_instances: int) -> Dict[str, Any]:
        """Execute scaling to target number of instances"""
        current_running = len([
            inst for inst in self.cluster_config['instances'] 
            if inst['state'] == 'running'
        ])
        
        if target_instances > current_running:
            # Scale up
            additional_needed = target_instances - current_running
            return self.start_cluster(current_running + additional_needed)
        
        elif target_instances < current_running:
            # Scale down (stop least critical instances first)
            instances_to_stop = current_running - target_instances
            running_instances = [
                inst for inst in self.cluster_config['instances'] 
                if inst['state'] == 'running'
            ]
            
            # Sort by role priority (tertiary first)
            instances_by_priority = sorted(
                running_instances,
                key=lambda x: {'tertiary': 0, 'secondary': 1, 'primary': 2}.get(x['role'], 1)
            )
            
            stop_instances = instances_by_priority[:instances_to_stop]
            instance_ids = [inst['instance_id'] for inst in stop_instances]
            
            try:
                self.ec2.stop_instances(InstanceIds=instance_ids)
                return {
                    'success': True,
                    'action': 'scaled_down',
                    'stopped_instances': len(instance_ids)
                }
            except Exception as e:
                return {'success': False, 'message': str(e)}
        
        return {'success': True, 'action': 'no_change'}

def main():
    """CLI interface for DMLog cluster management"""
    import sys
    
    manager = DMLogClusterManager()
    
    if len(sys.argv) < 2:
        print("Usage: python3 dmlog-cluster-manager.py [start|stop|status|metrics|scale]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        instances = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        result = manager.start_cluster(instances)
        print(json.dumps(result, indent=2))
    
    elif command == 'stop':
        result = manager.stop_cluster()
        print(json.dumps(result, indent=2))
    
    elif command == 'status':
        manager.discover_cluster()
        print(json.dumps(manager.cluster_config, indent=2))
    
    elif command == 'metrics':
        metrics = manager.get_gaming_metrics()
        print(json.dumps(metrics, indent=2))
    
    elif command == 'scale':
        decision = manager.auto_scale_decision()
        print("Scaling Decision:", json.dumps(decision, indent=2))
        
        if decision['action'] != 'none':
            if len(sys.argv) > 2 and sys.argv[2] == '--execute':
                result = manager.execute_scaling(decision['recommended_instances'])
                print("Scaling Result:", json.dumps(result, indent=2))
            else:
                print("Add --execute to apply scaling decision")

if __name__ == "__main__":
    main()