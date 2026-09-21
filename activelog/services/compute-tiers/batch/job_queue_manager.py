#!/usr/bin/env python3
"""
Job Queue Manager for ActiveLog Compute Tiers
Advanced queue-based processing with intelligent prioritization and resource allocation
"""

import boto3
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import heapq
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    """Job status enumeration"""
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"

class JobPriority(Enum):
    """Job priority levels"""
    EMERGENCY = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5

class ResourceType(Enum):
    """Resource type requirements"""
    CPU_INTENSIVE = "cpu_intensive"
    MEMORY_INTENSIVE = "memory_intensive"
    GPU_COMPUTE = "gpu_compute"
    IO_INTENSIVE = "io_intensive"
    NETWORK_INTENSIVE = "network_intensive"
    MIXED = "mixed"

@dataclass
class ResourceRequirement:
    """Resource requirements for a job"""
    cpu_cores: int
    memory_gb: float
    gpu_count: int
    storage_gb: float
    network_bandwidth_mbps: Optional[float]
    resource_type: ResourceType
    preferred_instance_family: Optional[str]

@dataclass
class QueuedJob:
    """Queued job specification"""
    job_id: str
    job_name: str
    priority: JobPriority
    resource_requirements: ResourceRequirement
    estimated_duration_minutes: int
    submitted_at: datetime
    deadline: Optional[datetime]
    retry_count: int
    max_retries: int
    status: JobStatus
    dependencies: List[str]
    metadata: Dict[str, Any]
    
    def __lt__(self, other):
        """Priority queue comparison (lower priority value = higher priority)"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # If same priority, use deadline, then submission time
        if self.deadline and other.deadline:
            return self.deadline < other.deadline
        elif self.deadline:
            return True
        elif other.deadline:
            return False
        return self.submitted_at < other.submitted_at

@dataclass
class QueueMetrics:
    """Queue performance metrics"""
    timestamp: datetime
    total_jobs: int
    queued_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    avg_queue_wait_time_minutes: float
    avg_job_duration_minutes: float
    queue_throughput_jobs_per_hour: float
    resource_utilization_percent: Dict[str, float]

class JobQueueManager:
    """Manages intelligent job queuing and processing"""
    
    def __init__(self, batch_client, max_concurrent_jobs: int = 100):
        self.batch = batch_client
        self.max_concurrent_jobs = max_concurrent_jobs
        
        # Job queues - using priority queue for intelligent scheduling
        self.job_queue = []  # Priority queue
        self.running_jobs: Dict[str, QueuedJob] = {}
        self.completed_jobs: List[QueuedJob] = []
        self.job_history: Dict[str, QueuedJob] = {}
        
        # Resource tracking
        self.available_resources = {
            'cpu_cores': 1000,  # Total available CPU cores
            'memory_gb': 4000,   # Total available memory
            'gpu_count': 50,     # Total available GPUs
            'storage_gb': 10000  # Total available storage
        }
        
        self.used_resources = {
            'cpu_cores': 0,
            'memory_gb': 0,
            'gpu_count': 0,
            'storage_gb': 0
        }
        
        # Queue configuration
        self.queue_config = {
            'max_queue_size': 10000,
            'job_timeout_minutes': 480,  # 8 hours default
            'max_retry_attempts': 3,
            'priority_aging_minutes': 120,  # Boost priority after 2 hours
            'resource_reservation_minutes': 30
        }
        
        # Performance metrics
        self.metrics_history: List[QueueMetrics] = []
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10)

    def submit_job(self, job_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a job to the queue"""
        try:
            # Parse job specification
            job = self._parse_job_spec(job_spec)
            
            # Validate job
            validation_result = self._validate_job(job)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'job_id': None,
                    'error': validation_result['error'],
                    'queue_position': None
                }
            
            # Check dependencies
            dependency_check = self._check_dependencies(job.dependencies)
            if not dependency_check['satisfied']:
                return {
                    'success': False,
                    'job_id': job.job_id,
                    'error': f"Dependencies not satisfied: {dependency_check['missing']}",
                    'queue_position': None
                }
            
            # Add to queue
            heapq.heappush(self.job_queue, job)
            self.job_history[job.job_id] = job
            
            # Calculate queue position estimate
            queue_position = self._estimate_queue_position(job)
            estimated_wait_time = self._estimate_wait_time(job, queue_position)
            
            logger.info(f"Job {job.job_id} submitted to queue at position ~{queue_position}")
            
            return {
                'success': True,
                'job_id': job.job_id,
                'queue_position': queue_position,
                'estimated_wait_time_minutes': estimated_wait_time,
                'estimated_start_time': datetime.utcnow() + timedelta(minutes=estimated_wait_time),
                'status': job.status.value
            }
            
        except Exception as e:
            logger.error(f"Failed to submit job: {e}")
            return {
                'success': False,
                'job_id': None,
                'error': str(e),
                'queue_position': None
            }

    def _parse_job_spec(self, job_spec: Dict[str, Any]) -> QueuedJob:
        """Parse job specification into QueuedJob object"""
        resource_req = ResourceRequirement(
            cpu_cores=job_spec.get('cpu_cores', 1),
            memory_gb=job_spec.get('memory_gb', 2),
            gpu_count=job_spec.get('gpu_count', 0),
            storage_gb=job_spec.get('storage_gb', 10),
            network_bandwidth_mbps=job_spec.get('network_bandwidth_mbps'),
            resource_type=ResourceType(job_spec.get('resource_type', 'mixed')),
            preferred_instance_family=job_spec.get('preferred_instance_family')
        )
        
        return QueuedJob(
            job_id=job_spec.get('job_id', str(uuid.uuid4())),
            job_name=job_spec.get('job_name', 'Unnamed Job'),
            priority=JobPriority(job_spec.get('priority', 3)),  # Normal priority default
            resource_requirements=resource_req,
            estimated_duration_minutes=job_spec.get('estimated_duration_minutes', 60),
            submitted_at=datetime.utcnow(),
            deadline=datetime.fromisoformat(job_spec['deadline']) if job_spec.get('deadline') else None,
            retry_count=0,
            max_retries=job_spec.get('max_retries', 3),
            status=JobStatus.QUEUED,
            dependencies=job_spec.get('dependencies', []),
            metadata=job_spec.get('metadata', {})
        )

    def _validate_job(self, job: QueuedJob) -> Dict[str, Any]:
        """Validate job requirements"""
        # Check queue capacity
        if len(self.job_queue) >= self.queue_config['max_queue_size']:
            return {'valid': False, 'error': 'Queue at maximum capacity'}
        
        # Check resource requirements are reasonable
        if job.resource_requirements.cpu_cores > self.available_resources['cpu_cores']:
            return {'valid': False, 'error': 'CPU requirements exceed available resources'}
        
        if job.resource_requirements.memory_gb > self.available_resources['memory_gb']:
            return {'valid': False, 'error': 'Memory requirements exceed available resources'}
        
        if job.resource_requirements.gpu_count > self.available_resources['gpu_count']:
            return {'valid': False, 'error': 'GPU requirements exceed available resources'}
        
        # Check deadline is reasonable
        if job.deadline and job.deadline < datetime.utcnow():
            return {'valid': False, 'error': 'Deadline is in the past'}
        
        return {'valid': True, 'error': None}

    def _check_dependencies(self, dependencies: List[str]) -> Dict[str, Any]:
        """Check if job dependencies are satisfied"""
        if not dependencies:
            return {'satisfied': True, 'missing': []}
        
        missing_deps = []
        for dep_job_id in dependencies:
            if dep_job_id not in self.job_history:
                missing_deps.append(dep_job_id)
            else:
                dep_job = self.job_history[dep_job_id]
                if dep_job.status not in [JobStatus.COMPLETED]:
                    missing_deps.append(dep_job_id)
        
        return {
            'satisfied': len(missing_deps) == 0,
            'missing': missing_deps
        }

    def _estimate_queue_position(self, job: QueuedJob) -> int:
        """Estimate position in queue considering priority"""
        position = 1
        
        for queued_job in self.job_queue:
            if job < queued_job:  # job has higher priority
                break
            position += 1
        
        return min(position, len(self.job_queue) + 1)

    def _estimate_wait_time(self, job: QueuedJob, queue_position: int) -> int:
        """Estimate wait time in minutes"""
        if queue_position <= 1:
            return 5  # Minimum startup time
        
        # Calculate based on average job duration and concurrency
        avg_job_duration = self._get_average_job_duration()
        concurrent_capacity = min(self.max_concurrent_jobs, 
                                self._estimate_concurrent_capacity(job.resource_requirements))
        
        # Estimate how many jobs ahead will be processed in parallel
        jobs_ahead = max(0, queue_position - concurrent_capacity)
        estimated_wait = (jobs_ahead * avg_job_duration) / concurrent_capacity
        
        return int(estimated_wait)

    def _get_average_job_duration(self) -> float:
        """Get average job duration from history"""
        if not self.completed_jobs:
            return 60.0  # Default 1 hour
        
        total_duration = sum(job.estimated_duration_minutes for job in self.completed_jobs[-100:])
        return total_duration / len(self.completed_jobs[-100:])

    def _estimate_concurrent_capacity(self, resource_req: ResourceRequirement) -> int:
        """Estimate how many similar jobs can run concurrently"""
        cpu_capacity = self.available_resources['cpu_cores'] // max(1, resource_req.cpu_cores)
        memory_capacity = int(self.available_resources['memory_gb'] // max(1, resource_req.memory_gb))
        
        if resource_req.gpu_count > 0:
            gpu_capacity = self.available_resources['gpu_count'] // resource_req.gpu_count
            return min(cpu_capacity, memory_capacity, gpu_capacity)
        
        return min(cpu_capacity, memory_capacity)

    def process_queue(self) -> Dict[str, Any]:
        """Process jobs from the queue"""
        try:
            processed_count = 0
            started_jobs = []
            
            # Age priorities (boost jobs that have been waiting)
            self._age_job_priorities()
            
            # Process jobs while resources are available
            while (self.job_queue and 
                   len(self.running_jobs) < self.max_concurrent_jobs and
                   processed_count < 10):  # Limit processing batch size
                
                # Get highest priority job
                job = heapq.heappop(self.job_queue)
                
                # Check if dependencies are now satisfied
                if not self._check_dependencies(job.dependencies)['satisfied']:
                    # Put back in queue
                    heapq.heappush(self.job_queue, job)
                    break
                
                # Check resource availability
                if self._can_allocate_resources(job.resource_requirements):
                    # Start job
                    success = self._start_job(job)
                    if success:
                        self._allocate_resources(job.resource_requirements)
                        self.running_jobs[job.job_id] = job
                        started_jobs.append(job.job_id)
                        processed_count += 1
                        
                        logger.info(f"Started job {job.job_id} ({job.job_name})")
                    else:
                        # Failed to start, put back in queue with retry
                        job.retry_count += 1
                        if job.retry_count <= job.max_retries:
                            job.status = JobStatus.RETRY
                            heapq.heappush(self.job_queue, job)
                        else:
                            job.status = JobStatus.FAILED
                            self._complete_job(job)
                else:
                    # Insufficient resources, put back and stop processing
                    heapq.heappush(self.job_queue, job)
                    break
            
            # Check for completed jobs
            completed_jobs = self._check_completed_jobs()
            
            return {
                'processed_jobs': processed_count,
                'started_jobs': started_jobs,
                'completed_jobs': completed_jobs,
                'queue_length': len(self.job_queue),
                'running_jobs': len(self.running_jobs),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing queue: {e}")
            return {'error': str(e)}

    def _age_job_priorities(self):
        """Boost priority of jobs that have been waiting too long"""
        aging_threshold = datetime.utcnow() - timedelta(minutes=self.queue_config['priority_aging_minutes'])
        
        aged_jobs = []
        remaining_jobs = []
        
        # Separate aged jobs
        while self.job_queue:
            job = heapq.heappop(self.job_queue)
            if job.submitted_at < aging_threshold and job.priority != JobPriority.EMERGENCY:
                # Boost priority
                if job.priority == JobPriority.HIGH:
                    job.priority = JobPriority.EMERGENCY
                elif job.priority == JobPriority.NORMAL:
                    job.priority = JobPriority.HIGH
                elif job.priority == JobPriority.LOW:
                    job.priority = JobPriority.NORMAL
                elif job.priority == JobPriority.BACKGROUND:
                    job.priority = JobPriority.LOW
                
                aged_jobs.append(job)
                logger.info(f"Aged job {job.job_id} priority to {job.priority.name}")
            else:
                remaining_jobs.append(job)
        
        # Rebuild queue
        for job in aged_jobs + remaining_jobs:
            heapq.heappush(self.job_queue, job)

    def _can_allocate_resources(self, resource_req: ResourceRequirement) -> bool:
        """Check if resources are available for job"""
        return (
            self.used_resources['cpu_cores'] + resource_req.cpu_cores <= self.available_resources['cpu_cores'] and
            self.used_resources['memory_gb'] + resource_req.memory_gb <= self.available_resources['memory_gb'] and
            self.used_resources['gpu_count'] + resource_req.gpu_count <= self.available_resources['gpu_count'] and
            self.used_resources['storage_gb'] + resource_req.storage_gb <= self.available_resources['storage_gb']
        )

    def _allocate_resources(self, resource_req: ResourceRequirement):
        """Allocate resources for job"""
        self.used_resources['cpu_cores'] += resource_req.cpu_cores
        self.used_resources['memory_gb'] += resource_req.memory_gb
        self.used_resources['gpu_count'] += resource_req.gpu_count
        self.used_resources['storage_gb'] += resource_req.storage_gb

    def _deallocate_resources(self, resource_req: ResourceRequirement):
        """Deallocate resources after job completion"""
        self.used_resources['cpu_cores'] = max(0, self.used_resources['cpu_cores'] - resource_req.cpu_cores)
        self.used_resources['memory_gb'] = max(0, self.used_resources['memory_gb'] - resource_req.memory_gb)
        self.used_resources['gpu_count'] = max(0, self.used_resources['gpu_count'] - resource_req.gpu_count)
        self.used_resources['storage_gb'] = max(0, self.used_resources['storage_gb'] - resource_req.storage_gb)

    def _start_job(self, job: QueuedJob) -> bool:
        """Start a job (integrate with actual batch system)"""
        try:
            job.status = JobStatus.SCHEDULED
            
            # In a real implementation, this would submit to AWS Batch
            # For now, simulate job start
            logger.info(f"Starting job {job.job_id} with resources: "
                       f"CPU={job.resource_requirements.cpu_cores}, "
                       f"Memory={job.resource_requirements.memory_gb}GB, "
                       f"GPU={job.resource_requirements.gpu_count}")
            
            job.status = JobStatus.RUNNING
            return True
            
        except Exception as e:
            logger.error(f"Failed to start job {job.job_id}: {e}")
            return False

    def _check_completed_jobs(self) -> List[str]:
        """Check for completed running jobs"""
        completed_job_ids = []
        
        for job_id, job in list(self.running_jobs.items()):
            # Simulate job completion based on estimated duration
            # In reality, this would check actual job status
            runtime = datetime.utcnow() - job.submitted_at
            if runtime.total_seconds() / 60 >= job.estimated_duration_minutes:
                # Job completed
                job.status = JobStatus.COMPLETED
                self._complete_job(job)
                completed_job_ids.append(job_id)
                del self.running_jobs[job_id]
        
        return completed_job_ids

    def _complete_job(self, job: QueuedJob):
        """Handle job completion"""
        # Deallocate resources
        self._deallocate_resources(job.resource_requirements)
        
        # Add to completed jobs
        self.completed_jobs.append(job)
        
        # Keep only last 1000 completed jobs in memory
        if len(self.completed_jobs) > 1000:
            self.completed_jobs = self.completed_jobs[-1000:]
        
        logger.info(f"Job {job.job_id} completed with status {job.status.value}")

    def get_queue_status(self, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive queue status"""
        try:
            # Calculate metrics
            current_metrics = self._calculate_current_metrics()
            
            # Queue details
            queue_details = []
            temp_queue = []
            
            # Extract queue for analysis (preserve order)
            while self.job_queue:
                job = heapq.heappop(self.job_queue)
                temp_queue.append(job)
                
                queue_details.append({
                    'job_id': job.job_id,
                    'job_name': job.job_name,
                    'priority': job.priority.name,
                    'status': job.status.value,
                    'submitted_at': job.submitted_at.isoformat(),
                    'estimated_duration_minutes': job.estimated_duration_minutes,
                    'resource_requirements': asdict(job.resource_requirements),
                    'retry_count': job.retry_count,
                    'dependencies': job.dependencies,
                    'wait_time_minutes': (datetime.utcnow() - job.submitted_at).total_seconds() / 60
                })
            
            # Restore queue
            for job in temp_queue:
                heapq.heappush(self.job_queue, job)
            
            # Running job details
            running_details = []
            for job in self.running_jobs.values():
                running_details.append({
                    'job_id': job.job_id,
                    'job_name': job.job_name,
                    'priority': job.priority.name,
                    'status': job.status.value,
                    'started_at': job.submitted_at.isoformat(),
                    'estimated_duration_minutes': job.estimated_duration_minutes,
                    'resource_requirements': asdict(job.resource_requirements),
                    'runtime_minutes': (datetime.utcnow() - job.submitted_at).total_seconds() / 60
                })
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': asdict(current_metrics),
                'queue_details': queue_details[:10],  # First 10 jobs
                'running_details': running_details,
                'resource_utilization': {
                    'cpu_cores': {
                        'used': self.used_resources['cpu_cores'],
                        'available': self.available_resources['cpu_cores'],
                        'utilization_percent': (self.used_resources['cpu_cores'] / self.available_resources['cpu_cores']) * 100
                    },
                    'memory_gb': {
                        'used': self.used_resources['memory_gb'],
                        'available': self.available_resources['memory_gb'],
                        'utilization_percent': (self.used_resources['memory_gb'] / self.available_resources['memory_gb']) * 100
                    },
                    'gpu_count': {
                        'used': self.used_resources['gpu_count'],
                        'available': self.available_resources['gpu_count'],
                        'utilization_percent': (self.used_resources['gpu_count'] / self.available_resources['gpu_count']) * 100 if self.available_resources['gpu_count'] > 0 else 0
                    }
                },
                'queue_configuration': self.queue_config
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {'error': str(e)}

    def _calculate_current_metrics(self) -> QueueMetrics:
        """Calculate current queue metrics"""
        now = datetime.utcnow()
        
        # Calculate average wait times
        wait_times = []
        temp_queue = []
        
        while self.job_queue:
            job = heapq.heappop(self.job_queue)
            temp_queue.append(job)
            wait_time = (now - job.submitted_at).total_seconds() / 60
            wait_times.append(wait_time)
        
        # Restore queue
        for job in temp_queue:
            heapq.heappush(self.job_queue, job)
        
        avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0
        
        # Calculate job durations
        job_durations = [job.estimated_duration_minutes for job in self.completed_jobs[-100:]]
        avg_duration = sum(job_durations) / len(job_durations) if job_durations else 60
        
        # Calculate throughput (jobs per hour in last hour)
        hour_ago = now - timedelta(hours=1)
        recent_completions = len([job for job in self.completed_jobs 
                                if job.status == JobStatus.COMPLETED and 
                                job.submitted_at >= hour_ago])
        
        # Resource utilization
        resource_util = {}
        for resource, used in self.used_resources.items():
            available = self.available_resources[resource]
            resource_util[resource] = (used / available * 100) if available > 0 else 0
        
        return QueueMetrics(
            timestamp=now,
            total_jobs=len(self.job_history),
            queued_jobs=len(self.job_queue),
            running_jobs=len(self.running_jobs),
            completed_jobs=len([j for j in self.completed_jobs if j.status == JobStatus.COMPLETED]),
            failed_jobs=len([j for j in self.completed_jobs if j.status == JobStatus.FAILED]),
            avg_queue_wait_time_minutes=avg_wait_time,
            avg_job_duration_minutes=avg_duration,
            queue_throughput_jobs_per_hour=recent_completions,
            resource_utilization_percent=resource_util
        )

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a queued or running job"""
        try:
            # Check if job is running
            if job_id in self.running_jobs:
                job = self.running_jobs[job_id]
                job.status = JobStatus.CANCELLED
                self._complete_job(job)
                del self.running_jobs[job_id]
                
                return {
                    'success': True,
                    'job_id': job_id,
                    'status': 'cancelled_running',
                    'message': 'Running job cancelled successfully'
                }
            
            # Check if job is queued
            temp_queue = []
            found_job = None
            
            while self.job_queue:
                job = heapq.heappop(self.job_queue)
                if job.job_id == job_id:
                    found_job = job
                    break
                temp_queue.append(job)
            
            # Restore remaining jobs to queue
            for job in temp_queue:
                heapq.heappush(self.job_queue, job)
            
            if found_job:
                found_job.status = JobStatus.CANCELLED
                return {
                    'success': True,
                    'job_id': job_id,
                    'status': 'cancelled_queued',
                    'message': 'Queued job cancelled successfully'
                }
            
            return {
                'success': False,
                'job_id': job_id,
                'message': 'Job not found in queue or running jobs'
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return {'success': False, 'error': str(e)}

    def get_job_details(self, job_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific job"""
        try:
            job = self.job_history.get(job_id)
            
            if not job:
                return {'error': f'Job {job_id} not found'}
            
            # Determine current location of job
            location = 'completed'
            if job_id in self.running_jobs:
                location = 'running'
            else:
                # Check if in queue
                for queued_job in self.job_queue:
                    if queued_job.job_id == job_id:
                        location = 'queued'
                        break
            
            job_details = {
                'job_id': job.job_id,
                'job_name': job.job_name,
                'status': job.status.value,
                'location': location,
                'priority': job.priority.name,
                'submitted_at': job.submitted_at.isoformat(),
                'estimated_duration_minutes': job.estimated_duration_minutes,
                'retry_count': job.retry_count,
                'max_retries': job.max_retries,
                'dependencies': job.dependencies,
                'resource_requirements': asdict(job.resource_requirements),
                'metadata': job.metadata
            }
            
            # Add timing information
            if location == 'running':
                job_details['runtime_minutes'] = (datetime.utcnow() - job.submitted_at).total_seconds() / 60
            elif location == 'queued':
                job_details['wait_time_minutes'] = (datetime.utcnow() - job.submitted_at).total_seconds() / 60
                job_details['estimated_queue_position'] = self._estimate_queue_position(job)
            
            return job_details
            
        except Exception as e:
            logger.error(f"Failed to get job details for {job_id}: {e}")
            return {'error': str(e)}

    async def continuous_processing(self):
        """Continuously process the job queue"""
        while True:
            try:
                result = self.process_queue()
                logger.debug(f"Queue processing result: {result}")
                
                # Update metrics
                current_metrics = self._calculate_current_metrics()
                self.metrics_history.append(current_metrics)
                
                # Keep only last 24 hours of metrics
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                self.metrics_history = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
                
                # Wait before next processing cycle
                await asyncio.sleep(30)  # Process every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in continuous processing: {e}")
                await asyncio.sleep(60)  # Wait longer on error