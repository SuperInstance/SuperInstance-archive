"""
Instance monitoring system for user instances
"""
import boto3
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict
import httpx

logger = logging.getLogger(__name__)

@dataclass
class MetricData:
    """CloudWatch metric data"""
    timestamp: datetime
    value: float
    unit: str

@dataclass  
class InstanceMetrics:
    """Complete instance metrics"""
    instance_id: str
    timestamp: datetime
    cpu_utilization: float
    memory_utilization: float
    disk_utilization: float
    network_in: float
    network_out: float
    disk_read_iops: float
    disk_write_iops: float
    status_check_failed: int

class InstanceMonitor:
    """
    Monitors user instances using CloudWatch and custom metrics
    """
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.ec2 = boto3.client('ec2')
        self.monitoring_tasks = {}
        self.metric_cache = {}
        self.cache_ttl = 300  # 5 minutes cache
    
    async def start_monitoring(self, user_id: str, instance_id: str):
        """Start monitoring for a user instance"""
        try:
            logger.info(f"Starting monitoring for instance {instance_id} (user: {user_id})")
            
            # Create CloudWatch alarms for the instance
            await self._create_cloudwatch_alarms(user_id, instance_id)
            
            # Start monitoring task
            task = asyncio.create_task(
                self._monitor_instance_loop(user_id, instance_id)
            )
            self.monitoring_tasks[user_id] = task
            
        except Exception as e:
            logger.error(f"Failed to start monitoring for {instance_id}: {e}")
            raise
    
    async def stop_monitoring(self, user_id: str):
        """Stop monitoring for a user"""
        try:
            if user_id in self.monitoring_tasks:
                self.monitoring_tasks[user_id].cancel()
                del self.monitoring_tasks[user_id]
                
            # Clean up CloudWatch alarms
            await self._cleanup_cloudwatch_alarms(user_id)
            
            # Remove from cache
            if user_id in self.metric_cache:
                del self.metric_cache[user_id]
                
            logger.info(f"Stopped monitoring for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring for user {user_id}: {e}")
    
    async def get_instance_metrics(self, instance_id: str) -> Dict[str, float]:
        """Get current instance metrics"""
        try:
            # Check cache first
            cache_key = f"metrics:{instance_id}"
            if cache_key in self.metric_cache:
                cached_data = self.metric_cache[cache_key]
                if datetime.utcnow() - cached_data['timestamp'] < timedelta(seconds=self.cache_ttl):
                    return cached_data['data']
            
            # Fetch fresh metrics
            metrics = await self._fetch_cloudwatch_metrics(instance_id)
            
            # Cache the results
            self.metric_cache[cache_key] = {
                'timestamp': datetime.utcnow(),
                'data': metrics
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics for {instance_id}: {e}")
            return {}
    
    async def _fetch_cloudwatch_metrics(self, instance_id: str) -> Dict[str, float]:
        """Fetch metrics from CloudWatch"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=10)
            
            metrics = {}
            
            # CPU Utilization
            cpu_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if cpu_response['Datapoints']:
                latest_cpu = sorted(cpu_response['Datapoints'], key=lambda x: x['Timestamp'])[-1]
                metrics['cpu_utilization'] = latest_cpu['Average']
            else:
                metrics['cpu_utilization'] = 0.0
            
            # Network In/Out
            network_in_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkIn',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            if network_in_response['Datapoints']:
                latest_net_in = sorted(network_in_response['Datapoints'], key=lambda x: x['Timestamp'])[-1]
                metrics['network_in'] = latest_net_in['Sum']
            else:
                metrics['network_in'] = 0.0
            
            network_out_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkOut',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            if network_out_response['Datapoints']:
                latest_net_out = sorted(network_out_response['Datapoints'], key=lambda x: x['Timestamp'])[-1]
                metrics['network_out'] = latest_net_out['Sum']
            else:
                metrics['network_out'] = 0.0
            
            # Status checks
            status_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='StatusCheckFailed',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Maximum']
            )
            
            if status_response['Datapoints']:
                latest_status = sorted(status_response['Datapoints'], key=lambda x: x['Timestamp'])[-1]
                metrics['status_check_failed'] = latest_status['Maximum']
            else:
                metrics['status_check_failed'] = 0
            
            # Memory utilization (requires CloudWatch agent)
            try:
                memory_response = self.cloudwatch.get_metric_statistics(
                    Namespace='CWAgent',
                    MetricName='mem_used_percent',
                    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Average']
                )
                
                if memory_response['Datapoints']:
                    latest_memory = sorted(memory_response['Datapoints'], key=lambda x: x['Timestamp'])[-1]
                    metrics['memory_utilization'] = latest_memory['Average']
                else:
                    metrics['memory_utilization'] = 0.0
            except Exception:
                # CloudWatch agent may not be installed
                metrics['memory_utilization'] = 0.0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to fetch CloudWatch metrics: {e}")
            return {}
    
    async def _create_cloudwatch_alarms(self, user_id: str, instance_id: str):
        """Create CloudWatch alarms for the instance"""
        try:
            # High CPU alarm
            self.cloudwatch.put_metric_alarm(
                AlarmName=f'activelog-{user_id}-high-cpu',
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=2,
                MetricName='CPUUtilization',
                Namespace='AWS/EC2',
                Period=300,
                Statistic='Average',
                Threshold=80.0,
                ActionsEnabled=True,
                AlarmActions=[
                    f'arn:aws:sns:us-east-1:ACCOUNT:activelog-alerts'
                ],
                AlarmDescription=f'High CPU for user {user_id} instance',
                Dimensions=[
                    {'Name': 'InstanceId', 'Value': instance_id}
                ],
                Unit='Percent',
                Tags=[
                    {'Key': 'User', 'Value': user_id},
                    {'Key': 'Service', 'Value': 'ActiveLog'}
                ]
            )
            
            # Instance status check alarm
            self.cloudwatch.put_metric_alarm(
                AlarmName=f'activelog-{user_id}-status-check',
                ComparisonOperator='GreaterThanOrEqualToThreshold',
                EvaluationPeriods=2,
                MetricName='StatusCheckFailed',
                Namespace='AWS/EC2',
                Period=300,
                Statistic='Maximum',
                Threshold=1.0,
                ActionsEnabled=True,
                AlarmActions=[
                    f'arn:aws:sns:us-east-1:ACCOUNT:activelog-alerts'
                ],
                AlarmDescription=f'Status check failed for user {user_id} instance',
                Dimensions=[
                    {'Name': 'InstanceId', 'Value': instance_id}
                ]
            )
            
        except Exception as e:
            logger.error(f"Failed to create CloudWatch alarms: {e}")
    
    async def _cleanup_cloudwatch_alarms(self, user_id: str):
        """Clean up CloudWatch alarms for a user"""
        try:
            alarm_names = [
                f'activelog-{user_id}-high-cpu',
                f'activelog-{user_id}-status-check'
            ]
            
            self.cloudwatch.delete_alarms(AlarmNames=alarm_names)
            
        except Exception as e:
            logger.error(f"Failed to cleanup CloudWatch alarms: {e}")
    
    async def _monitor_instance_loop(self, user_id: str, instance_id: str):
        """Continuous monitoring loop for an instance"""
        try:
            while True:
                # Get instance metrics
                metrics = await self.get_instance_metrics(instance_id)
                
                # Check for alerts
                await self._check_alert_conditions(user_id, instance_id, metrics)
                
                # Send metrics to monitoring service
                await self._send_metrics_to_service(user_id, instance_id, metrics)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
        except asyncio.CancelledError:
            logger.info(f"Monitoring cancelled for user {user_id}")
        except Exception as e:
            logger.error(f"Error in monitoring loop for user {user_id}: {e}")
    
    async def _check_alert_conditions(self, user_id: str, instance_id: str, metrics: Dict[str, float]):
        """Check if any alert conditions are met"""
        try:
            alerts = []
            
            # High CPU usage
            if metrics.get('cpu_utilization', 0) > 90:
                alerts.append({
                    'type': 'high_cpu',
                    'severity': 'warning',
                    'message': f'CPU utilization is {metrics["cpu_utilization"]:.1f}%'
                })
            
            # Memory usage (if available)
            if metrics.get('memory_utilization', 0) > 90:
                alerts.append({
                    'type': 'high_memory',
                    'severity': 'warning', 
                    'message': f'Memory utilization is {metrics["memory_utilization"]:.1f}%'
                })
            
            # Status check failures
            if metrics.get('status_check_failed', 0) > 0:
                alerts.append({
                    'type': 'status_check_failed',
                    'severity': 'critical',
                    'message': 'Instance status checks are failing'
                })
            
            # Send alerts if any
            if alerts:
                await self._send_user_alerts(user_id, instance_id, alerts)
                
        except Exception as e:
            logger.error(f"Error checking alert conditions: {e}")
    
    async def _send_user_alerts(self, user_id: str, instance_id: str, alerts: List[Dict[str, str]]):
        """Send alerts to user notification service"""
        try:
            notification_service_url = os.getenv('NOTIFICATION_SERVICE_URL', 'http://localhost:8010')
            
            alert_payload = {
                'user_id': user_id,
                'instance_id': instance_id,
                'timestamp': datetime.utcnow().isoformat(),
                'alerts': alerts
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{notification_service_url}/instance-alerts",
                    json=alert_payload,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Sent {len(alerts)} alerts for user {user_id}")
                else:
                    logger.warning(f"Failed to send alerts: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to send user alerts: {e}")
    
    async def _send_metrics_to_service(self, user_id: str, instance_id: str, metrics: Dict[str, float]):
        """Send metrics to monitoring service for storage and analysis"""
        try:
            monitoring_service_url = os.getenv('MONITORING_SERVICE_URL', 'http://localhost:8020')
            
            metrics_payload = {
                'user_id': user_id,
                'instance_id': instance_id,
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': metrics
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{monitoring_service_url}/instance-metrics",
                    json=metrics_payload,
                    timeout=5.0
                )
                
        except Exception as e:
            logger.debug(f"Failed to send metrics to monitoring service: {e}")
    
    async def get_instance_health_score(self, instance_id: str) -> float:
        """Calculate health score for an instance (0-100)"""
        try:
            metrics = await self.get_instance_metrics(instance_id)
            
            if not metrics:
                return 0.0
            
            # Calculate health based on various metrics
            health_factors = []
            
            # CPU health (lower is better, but some usage is good)
            cpu = metrics.get('cpu_utilization', 0)
            if cpu < 5:
                cpu_health = 90  # Very idle
            elif cpu < 50:
                cpu_health = 100  # Good usage
            elif cpu < 80:
                cpu_health = 80  # High but ok
            else:
                cpu_health = 20  # Too high
            health_factors.append(cpu_health)
            
            # Memory health
            memory = metrics.get('memory_utilization', 0)
            if memory < 10:
                memory_health = 90
            elif memory < 70:
                memory_health = 100
            elif memory < 90:
                memory_health = 70
            else:
                memory_health = 20
            health_factors.append(memory_health)
            
            # Status check health
            status_failed = metrics.get('status_check_failed', 0)
            status_health = 100 if status_failed == 0 else 0
            health_factors.append(status_health)
            
            # Calculate weighted average
            health_score = sum(health_factors) / len(health_factors)
            return round(health_score, 1)
            
        except Exception as e:
            logger.error(f"Failed to calculate health score: {e}")
            return 0.0