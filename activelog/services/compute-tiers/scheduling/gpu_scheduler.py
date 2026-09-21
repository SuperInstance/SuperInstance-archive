#!/usr/bin/env python3
"""
GPU Scheduler for ActiveLog Compute Tiers
Intelligent GPU instance scheduling and resource optimization
"""

import boto3
import json
import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

class GPUInstanceType(Enum):
    """GPU instance type categories"""
    TRAINING = "training"
    INFERENCE = "inference"
    DEVELOPMENT = "development"
    RENDERING = "rendering"
    COMPUTE = "compute"

class JobPriority(Enum):
    """Job priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"

@dataclass
class GPURequirement:
    """GPU resource requirements"""
    gpu_memory_gb: float
    gpu_count: int
    gpu_type: Optional[str]  # V100, A100, T4, etc.
    cuda_version: Optional[str]
    memory_bandwidth_gbps: Optional[float]
    compute_capability: Optional[float]

@dataclass
class GPUJob:
    """GPU compute job specification"""
    job_id: str
    job_name: str
    job_type: GPUInstanceType
    priority: JobPriority
    gpu_requirements: GPURequirement
    estimated_duration_hours: float
    max_cost_per_hour: Optional[float]
    preemptible: bool
    deadline: Optional[datetime]

@dataclass
class GPUInstance:
    """GPU instance specification"""
    instance_type: str
    gpu_type: str
    gpu_count: int
    gpu_memory_gb: float
    cpu_cores: int
    system_memory_gb: float
    storage_gb: float
    network_performance: str
    cost_per_hour: float
    spot_price: Optional[float]
    availability_zones: List[str]

@dataclass
class SchedulingResult:
    """GPU job scheduling result"""
    job_id: str
    scheduled: bool
    instance_type: Optional[str]
    estimated_cost: Optional[float]
    estimated_start_time: Optional[datetime]
    estimated_completion_time: Optional[datetime]
    reason: str
    alternatives: List[Dict[str, Any]]

class GPUScheduler:
    """Manages GPU instance scheduling and optimization"""
    
    def __init__(self, ec2_client, batch_client):
        self.ec2 = ec2_client
        self.batch = batch_client
        
        # GPU instance catalog with current specifications
        self.gpu_instances = {
            'p3.2xlarge': GPUInstance(
                instance_type='p3.2xlarge',
                gpu_type='V100',
                gpu_count=1,
                gpu_memory_gb=16,
                cpu_cores=8,
                system_memory_gb=61,
                storage_gb=0,
                network_performance='Up to 10 Gigabit',
                cost_per_hour=3.06,
                spot_price=None,  # Updated dynamically
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b']
            ),
            'p3.8xlarge': GPUInstance(
                instance_type='p3.8xlarge',
                gpu_type='V100',
                gpu_count=4,
                gpu_memory_gb=64,
                cpu_cores=32,
                system_memory_gb=244,
                storage_gb=0,
                network_performance='10 Gigabit',
                cost_per_hour=12.24,
                spot_price=None,
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b']
            ),
            'p3.16xlarge': GPUInstance(
                instance_type='p3.16xlarge',
                gpu_type='V100',
                gpu_count=8,
                gpu_memory_gb=128,
                cpu_cores=64,
                system_memory_gb=488,
                storage_gb=0,
                network_performance='25 Gigabit',
                cost_per_hour=24.48,
                spot_price=None,
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b']
            ),
            'p4d.24xlarge': GPUInstance(
                instance_type='p4d.24xlarge',
                gpu_type='A100',
                gpu_count=8,
                gpu_memory_gb=320,
                cpu_cores=96,
                system_memory_gb=1152,
                storage_gb=8000,
                network_performance='400 Gigabit',
                cost_per_hour=32.77,
                spot_price=None,
                availability_zones=['us-east-1a', 'us-west-2a']
            ),
            'g4dn.xlarge': GPUInstance(
                instance_type='g4dn.xlarge',
                gpu_type='T4',
                gpu_count=1,
                gpu_memory_gb=16,
                cpu_cores=4,
                system_memory_gb=16,
                storage_gb=125,
                network_performance='Up to 25 Gigabit',
                cost_per_hour=0.526,
                spot_price=None,
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b']
            ),
            'g4dn.2xlarge': GPUInstance(
                instance_type='g4dn.2xlarge',
                gpu_type='T4',
                gpu_count=1,
                gpu_memory_gb=16,
                cpu_cores=8,
                system_memory_gb=32,
                storage_gb=225,
                network_performance='Up to 25 Gigabit',
                cost_per_hour=0.752,
                spot_price=None,
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b']
            ),
            'g4dn.4xlarge': GPUInstance(
                instance_type='g4dn.4xlarge',
                gpu_type='T4',
                gpu_count=1,
                gpu_memory_gb=16,
                cpu_cores=16,
                system_memory_gb=64,
                storage_gb=225,
                network_performance='Up to 25 Gigabit',
                cost_per_hour=1.204,
                spot_price=None,
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b']
            ),
            'g4dn.8xlarge': GPUInstance(
                instance_type='g4dn.8xlarge',
                gpu_type='T4',
                gpu_count=1,
                gpu_memory_gb=16,
                cpu_cores=32,
                system_memory_gb=128,
                storage_gb=900,
                network_performance='50 Gigabit',
                cost_per_hour=2.176,
                spot_price=None,
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b']
            ),
            'g4dn.12xlarge': GPUInstance(
                instance_type='g4dn.12xlarge',
                gpu_type='T4',
                gpu_count=4,
                gpu_memory_gb=64,
                cpu_cores=48,
                system_memory_gb=192,
                storage_gb=900,
                network_performance='50 Gigabit',
                cost_per_hour=3.912,
                spot_price=None,
                availability_zones=['us-east-1a', 'us-east-1b', 'us-west-2a', 'us-west-2b']
            )
        }
        
        # Job queue for scheduling
        self.job_queue: List[GPUJob] = []
        self.running_jobs: Dict[str, Dict[str, Any]] = {}
        
        # Performance characteristics by GPU type
        self.gpu_performance = {
            'V100': {
                'fp32_tflops': 15.7,
                'fp16_tflops': 125,
                'memory_bandwidth': 900,
                'nvlink': True,
                'best_for': ['training', 'large_models']
            },
            'A100': {
                'fp32_tflops': 19.5,
                'fp16_tflops': 312,
                'memory_bandwidth': 2039,
                'nvlink': True,
                'best_for': ['training', 'large_models', 'inference']
            },
            'T4': {
                'fp32_tflops': 8.1,
                'fp16_tflops': 65,
                'memory_bandwidth': 300,
                'nvlink': False,
                'best_for': ['inference', 'development', 'small_models']
            }
        }

    def schedule_job(self, job_definition: Dict[str, Any], resource_requirements: Dict[str, Any], 
                    priority: str = 'normal') -> SchedulingResult:
        """Schedule a GPU compute job"""
        try:
            # Parse job requirements
            job = self._parse_job_definition(job_definition, resource_requirements, priority)
            
            # Find suitable instances
            suitable_instances = self._find_suitable_instances(job)
            
            if not suitable_instances:
                return SchedulingResult(
                    job_id=job.job_id,
                    scheduled=False,
                    instance_type=None,
                    estimated_cost=None,
                    estimated_start_time=None,
                    estimated_completion_time=None,
                    reason="No suitable GPU instances found for requirements",
                    alternatives=[]
                )
            
            # Select best instance based on cost and performance
            selected_instance = self._select_optimal_instance(job, suitable_instances)
            
            # Calculate scheduling details
            estimated_cost = selected_instance.cost_per_hour * job.estimated_duration_hours
            estimated_start_time = datetime.utcnow() + timedelta(minutes=5)  # Launch time
            estimated_completion_time = estimated_start_time + timedelta(hours=job.estimated_duration_hours)
            
            # Add to queue or schedule immediately
            if self._can_schedule_immediately(job, selected_instance):
                self._schedule_immediately(job, selected_instance)
                scheduled = True
            else:
                self.job_queue.append(job)
                estimated_start_time = self._estimate_queue_wait_time(job)
                estimated_completion_time = estimated_start_time + timedelta(hours=job.estimated_duration_hours)
                scheduled = False
            
            # Generate alternatives
            alternatives = self._generate_alternatives(job, suitable_instances, selected_instance)
            
            return SchedulingResult(
                job_id=job.job_id,
                scheduled=scheduled,
                instance_type=selected_instance.instance_type,
                estimated_cost=estimated_cost,
                estimated_start_time=estimated_start_time,
                estimated_completion_time=estimated_completion_time,
                reason="Scheduled successfully" if scheduled else "Added to queue",
                alternatives=alternatives
            )
            
        except Exception as e:
            logger.error(f"Failed to schedule GPU job: {e}")
            return SchedulingResult(
                job_id=job_definition.get('job_id', 'unknown'),
                scheduled=False,
                instance_type=None,
                estimated_cost=None,
                estimated_start_time=None,
                estimated_completion_time=None,
                reason=f"Scheduling error: {str(e)}",
                alternatives=[]
            )

    def _parse_job_definition(self, job_def: Dict[str, Any], resource_req: Dict[str, Any], 
                             priority: str) -> GPUJob:
        """Parse job definition into GPUJob object"""
        gpu_req = GPURequirement(
            gpu_memory_gb=resource_req.get('gpu_memory_gb', 16),
            gpu_count=resource_req.get('gpu_count', 1),
            gpu_type=resource_req.get('gpu_type'),
            cuda_version=resource_req.get('cuda_version'),
            memory_bandwidth_gbps=resource_req.get('memory_bandwidth_gbps'),
            compute_capability=resource_req.get('compute_capability')
        )
        
        return GPUJob(
            job_id=job_def.get('job_id', f'job_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}'),
            job_name=job_def.get('job_name', 'GPU Job'),
            job_type=GPUInstanceType(job_def.get('job_type', 'training')),
            priority=JobPriority(priority),
            gpu_requirements=gpu_req,
            estimated_duration_hours=job_def.get('estimated_duration_hours', 1.0),
            max_cost_per_hour=job_def.get('max_cost_per_hour'),
            preemptible=job_def.get('preemptible', True),
            deadline=datetime.fromisoformat(job_def['deadline']) if job_def.get('deadline') else None
        )

    def _find_suitable_instances(self, job: GPUJob) -> List[GPUInstance]:
        """Find GPU instances that meet job requirements"""
        suitable = []
        
        for instance in self.gpu_instances.values():
            # Check GPU memory requirement
            if instance.gpu_memory_gb * instance.gpu_count < job.gpu_requirements.gpu_memory_gb:
                continue
            
            # Check GPU count requirement
            if instance.gpu_count < job.gpu_requirements.gpu_count:
                continue
            
            # Check specific GPU type if requested
            if job.gpu_requirements.gpu_type and instance.gpu_type != job.gpu_requirements.gpu_type:
                continue
            
            # Check cost constraints
            if job.max_cost_per_hour and instance.cost_per_hour > job.max_cost_per_hour:
                continue
            
            # Check job type suitability
            gpu_perf = self.gpu_performance[instance.gpu_type]
            if job.job_type.value not in gpu_perf['best_for'] and job.job_type != GPUInstanceType.COMPUTE:
                # Allow if no better option, but with lower priority
                pass
            
            suitable.append(instance)
        
        return suitable

    def _select_optimal_instance(self, job: GPUJob, suitable_instances: List[GPUInstance]) -> GPUInstance:
        """Select the optimal instance based on job requirements and cost efficiency"""
        if not suitable_instances:
            raise ValueError("No suitable instances provided")
        
        scored_instances = []
        
        for instance in suitable_instances:
            score = self._calculate_instance_score(job, instance)
            scored_instances.append((score, instance))
        
        # Sort by score (higher is better)
        scored_instances.sort(key=lambda x: x[0], reverse=True)
        
        return scored_instances[0][1]

    def _calculate_instance_score(self, job: GPUJob, instance: GPUInstance) -> float:
        """Calculate suitability score for instance-job combination"""
        score = 0.0
        
        # Cost efficiency (40% of score)
        cost_efficiency = 1.0 / (instance.cost_per_hour + 0.1)  # Avoid division by zero
        score += cost_efficiency * 0.4
        
        # Performance match (30% of score)
        gpu_perf = self.gpu_performance[instance.gpu_type]
        if job.job_type.value in gpu_perf['best_for']:
            score += 30.0
        elif job.job_type == GPUInstanceType.COMPUTE:
            score += 20.0  # Generic compute jobs
        else:
            score += 10.0  # Not ideal but usable
        
        # Resource utilization (20% of score)
        gpu_utilization = min(1.0, job.gpu_requirements.gpu_memory_gb / (instance.gpu_memory_gb * instance.gpu_count))
        score += gpu_utilization * 20.0
        
        # Priority bonus (10% of score)
        priority_bonus = {
            JobPriority.CRITICAL: 10.0,
            JobPriority.HIGH: 7.5,
            JobPriority.NORMAL: 5.0,
            JobPriority.LOW: 2.5,
            JobPriority.BACKGROUND: 1.0
        }
        score += priority_bonus.get(job.priority, 5.0)
        
        return score

    def _can_schedule_immediately(self, job: GPUJob, instance: GPUInstance) -> bool:
        """Check if job can be scheduled immediately"""
        # For now, assume we can always schedule (would check actual capacity in production)
        return True

    def _schedule_immediately(self, job: GPUJob, instance: GPUInstance):
        """Schedule job to run immediately"""
        job_info = {
            'job': job,
            'instance': instance,
            'start_time': datetime.utcnow(),
            'status': 'running'
        }
        self.running_jobs[job.job_id] = job_info
        logger.info(f"Scheduled job {job.job_id} on {instance.instance_type}")

    def _estimate_queue_wait_time(self, job: GPUJob) -> datetime:
        """Estimate how long job will wait in queue"""
        # Simple estimation based on queue position and average job duration
        queue_position = len(self.job_queue)
        avg_job_duration = 2.0  # hours
        estimated_wait_hours = queue_position * avg_job_duration * 0.5  # Assume 50% parallel execution
        
        return datetime.utcnow() + timedelta(hours=estimated_wait_hours)

    def _generate_alternatives(self, job: GPUJob, suitable_instances: List[GPUInstance], 
                              selected: GPUInstance) -> List[Dict[str, Any]]:
        """Generate alternative scheduling options"""
        alternatives = []
        
        for instance in suitable_instances:
            if instance.instance_type == selected.instance_type:
                continue
            
            cost_per_hour = instance.spot_price if instance.spot_price else instance.cost_per_hour
            total_cost = cost_per_hour * job.estimated_duration_hours
            
            alternatives.append({
                'instance_type': instance.instance_type,
                'gpu_type': instance.gpu_type,
                'gpu_count': instance.gpu_count,
                'cost_per_hour': cost_per_hour,
                'total_estimated_cost': total_cost,
                'performance_tier': self._get_performance_tier(instance),
                'availability': 'high'  # Would check actual availability
            })
        
        # Sort alternatives by cost
        alternatives.sort(key=lambda x: x['total_estimated_cost'])
        
        return alternatives[:5]  # Return top 5 alternatives

    def _get_performance_tier(self, instance: GPUInstance) -> str:
        """Get performance tier for instance"""
        gpu_perf = self.gpu_performance[instance.gpu_type]
        
        if gpu_perf['fp16_tflops'] > 200:
            return 'high'
        elif gpu_perf['fp16_tflops'] > 100:
            return 'medium'
        else:
            return 'low'

    def get_queue_status(self, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """Get GPU job queue status"""
        try:
            queue_status = {
                'timestamp': datetime.utcnow().isoformat(),
                'queued_jobs': len(self.job_queue),
                'running_jobs': len(self.running_jobs),
                'queue_details': [],
                'running_details': [],
                'estimated_wait_time_hours': 0
            }
            
            # Queue details
            for i, job in enumerate(self.job_queue):
                queue_status['queue_details'].append({
                    'position': i + 1,
                    'job_id': job.job_id,
                    'job_name': job.job_name,
                    'priority': job.priority.value,
                    'estimated_duration_hours': job.estimated_duration_hours,
                    'gpu_requirements': {
                        'gpu_count': job.gpu_requirements.gpu_count,
                        'gpu_memory_gb': job.gpu_requirements.gpu_memory_gb,
                        'gpu_type': job.gpu_requirements.gpu_type
                    }
                })
            
            # Running job details
            for job_id, job_info in self.running_jobs.items():
                runtime = datetime.utcnow() - job_info['start_time']
                remaining_hours = max(0, job_info['job'].estimated_duration_hours - (runtime.total_seconds() / 3600))
                
                queue_status['running_details'].append({
                    'job_id': job_id,
                    'job_name': job_info['job'].job_name,
                    'instance_type': job_info['instance'].instance_type,
                    'runtime_hours': runtime.total_seconds() / 3600,
                    'estimated_remaining_hours': remaining_hours,
                    'status': job_info['status']
                })
            
            # Estimate total queue wait time
            if self.job_queue:
                total_running_time = sum(
                    max(0, job_info['job'].estimated_duration_hours - 
                        (datetime.utcnow() - job_info['start_time']).total_seconds() / 3600)
                    for job_info in self.running_jobs.values()
                )
                queue_status['estimated_wait_time_hours'] = total_running_time / max(1, len(self.running_jobs))
            
            return queue_status
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {'error': str(e)}

    async def optimize_gpu_usage(self):
        """Optimize GPU resource usage and scheduling"""
        try:
            # Update spot prices
            await self._update_spot_prices()
            
            # Process job queue
            await self._process_job_queue()
            
            # Check for completed jobs
            await self._check_completed_jobs()
            
            # Optimize instance usage
            await self._optimize_instance_allocation()
            
            logger.info(f"GPU optimization cycle completed. Queue: {len(self.job_queue)}, Running: {len(self.running_jobs)}")
            
        except Exception as e:
            logger.error(f"Error in GPU usage optimization: {e}")

    async def _update_spot_prices(self):
        """Update spot prices for GPU instances"""
        try:
            instance_types = list(self.gpu_instances.keys())
            
            response = self.ec2.describe_spot_price_history(
                InstanceTypes=instance_types,
                ProductDescriptions=['Linux/UNIX'],
                MaxResults=len(instance_types) * 3,  # Multiple AZs
                StartTime=datetime.utcnow() - timedelta(hours=1)
            )
            
            # Update spot prices
            for price_info in response['SpotPriceHistory']:
                instance_type = price_info['InstanceType']
                if instance_type in self.gpu_instances:
                    spot_price = float(price_info['SpotPrice'])
                    self.gpu_instances[instance_type].spot_price = spot_price
                    logger.debug(f"Updated spot price for {instance_type}: ${spot_price}")
            
        except Exception as e:
            logger.error(f"Failed to update spot prices: {e}")

    async def _process_job_queue(self):
        """Process jobs waiting in queue"""
        if not self.job_queue:
            return
        
        # Sort queue by priority and deadline
        self.job_queue.sort(key=lambda job: (
            job.priority.value,  # Higher priority first
            job.deadline if job.deadline else datetime.max  # Earlier deadline first
        ))
        
        jobs_to_schedule = []
        for job in self.job_queue[:5]:  # Process up to 5 jobs per cycle
            suitable_instances = self._find_suitable_instances(job)
            if suitable_instances:
                selected_instance = self._select_optimal_instance(job, suitable_instances)
                if self._can_schedule_immediately(job, selected_instance):
                    jobs_to_schedule.append((job, selected_instance))
        
        # Schedule selected jobs
        for job, instance in jobs_to_schedule:
            self._schedule_immediately(job, instance)
            self.job_queue.remove(job)

    async def _check_completed_jobs(self):
        """Check for completed jobs and clean up"""
        completed_jobs = []
        
        for job_id, job_info in self.running_jobs.items():
            runtime = datetime.utcnow() - job_info['start_time']
            if runtime.total_seconds() / 3600 >= job_info['job'].estimated_duration_hours:
                completed_jobs.append(job_id)
                logger.info(f"Job {job_id} completed after {runtime.total_seconds()/3600:.1f} hours")
        
        # Remove completed jobs
        for job_id in completed_jobs:
            del self.running_jobs[job_id]

    async def _optimize_instance_allocation(self):
        """Optimize GPU instance allocation"""
        # Check for underutilized instances
        # In production, this would check actual GPU utilization metrics
        
        # Check for cost optimization opportunities
        for job_id, job_info in self.running_jobs.items():
            instance = job_info['instance']
            spot_price = instance.spot_price
            
            if spot_price and spot_price < instance.cost_per_hour * 0.7:
                logger.info(f"Job {job_id} could save {((instance.cost_per_hour - spot_price) / instance.cost_per_hour * 100):.1f}% with spot instances")

    def get_gpu_utilization_metrics(self) -> Dict[str, Any]:
        """Get GPU utilization metrics"""
        try:
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'total_gpu_instances': len(self.gpu_instances),
                'active_jobs': len(self.running_jobs),
                'queued_jobs': len(self.job_queue),
                'instance_utilization': {},
                'cost_metrics': {},
                'performance_metrics': {}
            }
            
            # Calculate utilization by instance type
            instance_usage = {}
            for job_info in self.running_jobs.values():
                instance_type = job_info['instance'].instance_type
                instance_usage[instance_type] = instance_usage.get(instance_type, 0) + 1
            
            for instance_type, instance in self.gpu_instances.items():
                utilization = instance_usage.get(instance_type, 0)
                metrics['instance_utilization'][instance_type] = {
                    'active_instances': utilization,
                    'utilization_rate': min(100, utilization * 25),  # Assume 4 instances max per type
                    'cost_per_hour': instance.cost_per_hour,
                    'spot_price': instance.spot_price,
                    'potential_savings': ((instance.cost_per_hour - (instance.spot_price or instance.cost_per_hour)) / instance.cost_per_hour * 100) if instance.spot_price else 0
                }
            
            # Cost metrics
            total_hourly_cost = sum(
                job_info['instance'].cost_per_hour 
                for job_info in self.running_jobs.values()
            )
            
            metrics['cost_metrics'] = {
                'current_hourly_cost': total_hourly_cost,
                'estimated_daily_cost': total_hourly_cost * 24,
                'queue_cost_if_all_scheduled': sum(
                    self._select_optimal_instance(job, self._find_suitable_instances(job)).cost_per_hour
                    for job in self.job_queue
                    if self._find_suitable_instances(job)
                )
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get GPU utilization metrics: {e}")
            return {'error': str(e)}

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a queued or running GPU job"""
        try:
            # Check if job is running
            if job_id in self.running_jobs:
                job_info = self.running_jobs[job_id]
                runtime = datetime.utcnow() - job_info['start_time']
                
                # In production, would terminate the actual instance/job
                del self.running_jobs[job_id]
                
                return {
                    'job_id': job_id,
                    'status': 'cancelled',
                    'runtime_hours': runtime.total_seconds() / 3600,
                    'cost_incurred': job_info['instance'].cost_per_hour * (runtime.total_seconds() / 3600)
                }
            
            # Check if job is queued
            for i, job in enumerate(self.job_queue):
                if job.job_id == job_id:
                    self.job_queue.pop(i)
                    return {
                        'job_id': job_id,
                        'status': 'cancelled_from_queue',
                        'queue_position': i + 1,
                        'cost_incurred': 0
                    }
            
            return {
                'job_id': job_id,
                'status': 'not_found',
                'message': 'Job not found in queue or running jobs'
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return {'error': str(e)}