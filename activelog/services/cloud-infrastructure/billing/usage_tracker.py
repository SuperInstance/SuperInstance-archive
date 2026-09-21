"""
Usage Tracking System
Tracks detailed resource usage for accurate per-minute billing
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import asdict
import json
import psutil

from core.models import (
    EC2Instance, BillingRecord, InstanceType, User,
    current_timestamp, generate_id
)

class UsageTracker:
    """Tracks detailed resource usage for billing purposes"""
    
    def __init__(self, config: Dict[str, Any], database_manager):
        self.config = config
        self.db = database_manager
        self.logger = logging.getLogger(__name__)
        
        # Usage tracking state
        self.tracking_active = False
        self.tracking_task = None
        self.usage_cache = {}  # Cache recent usage data
        
        # Metrics collection
        self.metrics_enabled = config.get('monitoring', {}).get('enable_monitoring', True)
        self.metrics_interval = config.get('monitoring', {}).get('metrics_interval_seconds', 30)
        
    async def start_usage_tracking(self):
        """Start usage tracking"""
        if self.tracking_active:
            return
            
        self.tracking_active = True
        self.tracking_task = asyncio.create_task(self._usage_tracking_loop())
        self.logger.info("Usage tracking started")
    
    async def stop_usage_tracking(self):
        """Stop usage tracking"""
        self.tracking_active = False
        if self.tracking_task:
            self.tracking_task.cancel()
            try:
                await self.tracking_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Usage tracking stopped")
    
    async def _usage_tracking_loop(self):
        """Main usage tracking loop"""
        while self.tracking_active:
            try:
                await self._collect_usage_metrics()
                await asyncio.sleep(self.metrics_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Usage tracking error: {e}")
                await asyncio.sleep(self.metrics_interval)
    
    async def _collect_usage_metrics(self):
        """Collect usage metrics for all running instances"""
        try:
            # Get all running instances
            running_instances = await self.db.get_instances_by_state("running")
            
            collection_tasks = []
            for instance in running_instances:
                task = self._collect_instance_metrics(instance)
                collection_tasks.append(task)
            
            if collection_tasks:
                await asyncio.gather(*collection_tasks, return_exceptions=True)
                
            self.logger.debug(f"Collected metrics for {len(running_instances)} instances")
            
        except Exception as e:
            self.logger.error(f"Error collecting usage metrics: {e}")
    
    async def _collect_instance_metrics(self, instance: EC2Instance):
        """Collect metrics for a single instance"""
        try:
            current_time = current_timestamp()
            
            # Mock metrics collection (in production, use CloudWatch or similar)
            metrics = {
                'instance_id': instance.instance_id,
                'user_id': instance.user_id,
                'instance_type': instance.instance_type.value,
                'timestamp': current_time,
                'cpu_utilization': self._get_mock_cpu_utilization(instance),
                'memory_utilization': self._get_mock_memory_utilization(instance),
                'network_in_bytes': self._get_mock_network_in(instance),
                'network_out_bytes': self._get_mock_network_out(instance),
                'disk_read_bytes': self._get_mock_disk_read(instance),
                'disk_write_bytes': self._get_mock_disk_write(instance)
            }
            
            # Store in cache for real-time access
            self.usage_cache[instance.instance_id] = metrics
            
            # Persist to database for historical analysis
            await self.db.store_usage_metrics(metrics)
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics for instance {instance.instance_id}: {e}")
    
    def _get_mock_cpu_utilization(self, instance: EC2Instance) -> float:
        """Mock CPU utilization (replace with actual metrics)"""
        # Simulate different utilization based on instance type
        base_utilization = {
            't3.nano': 10.0,
            't3.micro': 15.0,
            't3.small': 20.0,
            't3.medium': 25.0,
            't3.large': 30.0,
            'c5.large': 40.0,
            'c5.xlarge': 50.0,
            'c5.4xlarge_game': 75.0,  # Game servers run hot
            'r5.large': 35.0
        }
        
        base = base_utilization.get(instance.instance_type.value, 25.0)
        
        # Add some randomness
        import random
        variation = random.uniform(-10, 15)
        return max(0, min(100, base + variation))
    
    def _get_mock_memory_utilization(self, instance: EC2Instance) -> float:
        """Mock memory utilization"""
        # Memory optimized instances use more memory
        if instance.instance_type.value.startswith('r5'):
            base = 60.0
        elif 'game' in instance.instance_type.value:
            base = 70.0
        else:
            base = 45.0
            
        import random
        variation = random.uniform(-15, 20)
        return max(0, min(100, base + variation))
    
    def _get_mock_network_in(self, instance: EC2Instance) -> int:
        """Mock network input bytes"""
        import random
        # Game servers have higher network usage
        if 'game' in instance.instance_type.value:
            return random.randint(1000000, 10000000)  # 1-10 MB
        else:
            return random.randint(100000, 1000000)  # 100KB-1MB
    
    def _get_mock_network_out(self, instance: EC2Instance) -> int:
        """Mock network output bytes"""
        import random
        if 'game' in instance.instance_type.value:
            return random.randint(2000000, 15000000)  # 2-15 MB
        else:
            return random.randint(50000, 500000)  # 50KB-500KB
    
    def _get_mock_disk_read(self, instance: EC2Instance) -> int:
        """Mock disk read bytes"""
        import random
        return random.randint(1000000, 50000000)  # 1-50 MB
    
    def _get_mock_disk_write(self, instance: EC2Instance) -> int:
        """Mock disk write bytes"""
        import random
        return random.randint(500000, 25000000)  # 500KB-25 MB
    
    async def record_usage(self, user_id: str, instance_id: str, instance_type: InstanceType,
                          start_time: datetime, end_time: datetime, 
                          duration_minutes: int) -> BillingRecord:
        """Record usage and create billing record"""
        try:
            # Calculate cost
            pricing = self.config['billing']['pricing']['compute']
            cost_per_minute = pricing.get(instance_type.value, 0.0)
            total_cost = cost_per_minute * duration_minutes
            
            # Create billing record
            billing_record = BillingRecord(
                record_id=generate_id("bill"),
                user_id=user_id,
                instance_id=instance_id,
                instance_type=instance_type,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                cost_per_minute=cost_per_minute,
                total_cost=total_cost,
                billing_tags={}
            )
            
            # Save to database
            await self.db.create_billing_record(billing_record)
            
            self.logger.debug(
                f"Recorded usage for {instance_id}: "
                f"{duration_minutes} minutes, ${total_cost:.4f}"
            )
            
            return billing_record
            
        except Exception as e:
            self.logger.error(f"Error recording usage: {e}")
            raise
    
    async def get_real_time_metrics(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time metrics for an instance"""
        try:
            if instance_id in self.usage_cache:
                metrics = self.usage_cache[instance_id].copy()
                metrics['timestamp'] = metrics['timestamp'].isoformat()
                return metrics
            else:
                # Get latest metrics from database
                return await self.db.get_latest_usage_metrics(instance_id)
                
        except Exception as e:
            self.logger.error(f"Error getting real-time metrics for {instance_id}: {e}")
            return None
    
    async def get_user_usage_summary(self, user_id: str, 
                                   time_range_hours: int = 24) -> Dict[str, Any]:
        """Get usage summary for a user"""
        try:
            end_time = current_timestamp()
            start_time = end_time - timedelta(hours=time_range_hours)
            
            # Get user's instances
            user_instances = await self.db.get_user_instances(user_id)
            
            summary = {
                'user_id': user_id,
                'time_range_hours': time_range_hours,
                'period': {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                },
                'instances': {},
                'totals': {
                    'total_cost': 0.0,
                    'total_runtime_minutes': 0,
                    'average_cpu_utilization': 0.0,
                    'total_network_gb': 0.0
                }
            }
            
            total_cpu = 0.0
            cpu_readings = 0
            
            for instance in user_instances:
                # Get billing records for the period
                billing_records = await self.db.get_billing_records(
                    user_id=user_id,
                    instance_id=instance.instance_id,
                    start_date=start_time,
                    end_date=end_time
                )
                
                instance_cost = sum(r.total_cost for r in billing_records)
                instance_minutes = sum(r.duration_minutes for r in billing_records)
                
                # Get latest metrics
                latest_metrics = await self.get_real_time_metrics(instance.instance_id)
                
                instance_summary = {
                    'instance_id': instance.instance_id,
                    'instance_type': instance.instance_type.value,
                    'state': instance.state.value,
                    'cost': round(instance_cost, 4),
                    'runtime_minutes': instance_minutes,
                    'current_metrics': latest_metrics
                }
                
                summary['instances'][instance.instance_id] = instance_summary
                summary['totals']['total_cost'] += instance_cost
                summary['totals']['total_runtime_minutes'] += instance_minutes
                
                if latest_metrics:
                    total_cpu += latest_metrics.get('cpu_utilization', 0)
                    cpu_readings += 1
            
            # Calculate averages
            if cpu_readings > 0:
                summary['totals']['average_cpu_utilization'] = round(total_cpu / cpu_readings, 2)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting usage summary for user {user_id}: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }
    
    async def detect_usage_anomalies(self, user_id: str) -> List[Dict[str, Any]]:
        """Detect unusual usage patterns that might indicate issues"""
        try:
            anomalies = []
            
            # Get user's instances
            user_instances = await self.db.get_user_instances(user_id)
            
            for instance in user_instances:
                if instance.state.value != 'running':
                    continue
                
                # Get recent metrics
                metrics = await self.get_real_time_metrics(instance.instance_id)
                if not metrics:
                    continue
                
                instance_anomalies = []
                
                # High CPU utilization
                cpu_utilization = metrics.get('cpu_utilization', 0)
                if cpu_utilization > 90:
                    instance_anomalies.append({
                        'type': 'high_cpu',
                        'severity': 'high',
                        'message': f"CPU utilization at {cpu_utilization:.1f}%",
                        'threshold': 90,
                        'current_value': cpu_utilization
                    })
                
                # High memory utilization
                memory_utilization = metrics.get('memory_utilization', 0)
                if memory_utilization > 90:
                    instance_anomalies.append({
                        'type': 'high_memory',
                        'severity': 'high',
                        'message': f"Memory utilization at {memory_utilization:.1f}%",
                        'threshold': 90,
                        'current_value': memory_utilization
                    })
                
                # Unusual network activity (basic detection)
                network_out = metrics.get('network_out_bytes', 0)
                if network_out > 100000000:  # >100MB
                    instance_anomalies.append({
                        'type': 'high_network_out',
                        'severity': 'medium',
                        'message': f"High network output: {network_out / 1000000:.1f} MB",
                        'threshold': 100000000,
                        'current_value': network_out
                    })
                
                if instance_anomalies:
                    anomalies.append({
                        'instance_id': instance.instance_id,
                        'instance_type': instance.instance_type.value,
                        'anomalies': instance_anomalies,
                        'timestamp': metrics['timestamp']
                    })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error detecting usage anomalies for user {user_id}: {e}")
            return []
    
    async def calculate_cost_efficiency(self, user_id: str) -> Dict[str, Any]:
        """Calculate cost efficiency metrics for a user"""
        try:
            # Get recent usage data
            usage_summary = await self.get_user_usage_summary(user_id, 24)
            
            if 'error' in usage_summary:
                return usage_summary
            
            efficiency_metrics = {
                'user_id': user_id,
                'cost_per_hour': 0.0,
                'utilization_efficiency': 0.0,
                'instance_efficiency': {},
                'recommendations': []
            }
            
            total_cost = usage_summary['totals']['total_cost']
            total_hours = usage_summary['totals']['total_runtime_minutes'] / 60
            
            if total_hours > 0:
                efficiency_metrics['cost_per_hour'] = round(total_cost / total_hours, 4)
            
            # Analyze each instance
            total_efficiency = 0.0
            efficiency_count = 0
            
            for instance_id, instance_data in usage_summary['instances'].items():
                if not instance_data['current_metrics']:
                    continue
                
                metrics = instance_data['current_metrics']
                cpu_utilization = metrics.get('cpu_utilization', 0)
                memory_utilization = metrics.get('memory_utilization', 0)
                
                # Simple efficiency calculation (average of CPU and memory utilization)
                efficiency = (cpu_utilization + memory_utilization) / 2
                
                efficiency_metrics['instance_efficiency'][instance_id] = {
                    'instance_type': instance_data['instance_type'],
                    'efficiency_score': round(efficiency, 2),
                    'cpu_utilization': cpu_utilization,
                    'memory_utilization': memory_utilization,
                    'cost_24h': instance_data['cost']
                }
                
                total_efficiency += efficiency
                efficiency_count += 1
                
                # Generate recommendations
                if efficiency < 30:  # Low utilization
                    efficiency_metrics['recommendations'].append({
                        'instance_id': instance_id,
                        'type': 'downsize',
                        'message': f"Instance {instance_id} has low utilization ({efficiency:.1f}%). Consider downsizing.",
                        'potential_savings': instance_data['cost'] * 0.5  # Estimated 50% savings
                    })
                elif efficiency > 85:  # High utilization
                    efficiency_metrics['recommendations'].append({
                        'instance_id': instance_id,
                        'type': 'upsize',
                        'message': f"Instance {instance_id} has high utilization ({efficiency:.1f}%). Consider upsizing for better performance.",
                        'performance_impact': 'high'
                    })
            
            if efficiency_count > 0:
                efficiency_metrics['utilization_efficiency'] = round(total_efficiency / efficiency_count, 2)
            
            return efficiency_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating cost efficiency for user {user_id}: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for usage tracker"""
        try:
            # Check tracking loop status
            tracking_healthy = self.tracking_active and (
                self.tracking_task and not self.tracking_task.done()
            )
            
            # Check cache status
            cache_size = len(self.usage_cache)
            
            # Check recent metrics collection
            recent_metrics_count = 0
            cutoff_time = current_timestamp() - timedelta(minutes=5)
            
            for metrics in self.usage_cache.values():
                if metrics['timestamp'] > cutoff_time:
                    recent_metrics_count += 1
            
            return {
                'service': 'usage_tracker',
                'healthy': tracking_healthy,
                'tracking_loop_active': tracking_healthy,
                'cached_instances': cache_size,
                'recent_metrics_collected': recent_metrics_count,
                'metrics_collection_interval': self.metrics_interval,
                'timestamp': current_timestamp().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Usage tracker health check failed: {e}")
            return {
                'service': 'usage_tracker',
                'healthy': False,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }