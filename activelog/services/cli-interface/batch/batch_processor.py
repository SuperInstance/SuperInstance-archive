#!/usr/bin/env python3
"""
Batch Processor - Handles batch job processing for CLI operations
Provides job queuing, execution, monitoring, and result management
"""

import json
import uuid
import time
import os
import asyncio
import subprocess
import multiprocessing
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import threading
from queue import Queue, Empty, PriorityQueue
from enum import Enum
import sqlite3
import pickle
import tempfile
import shutil

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class JobPriority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


@dataclass
class BatchJob:
    """Batch job configuration"""
    id: str
    job_type: str
    command: str
    args: List[str]
    environment: Dict[str, str]
    priority: JobPriority = JobPriority.NORMAL
    timeout: int = 3600  # 1 hour default
    max_memory_mb: int = 1024  # 1GB default
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    log_file: Optional[str] = None
    output_files: List[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.output_files is None:
            self.output_files = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class JobResult:
    """Job execution result"""
    job_id: str
    status: JobStatus
    return_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    output_files: List[str] = None
    execution_time: Optional[float] = None
    memory_usage: Optional[int] = None
    error_message: Optional[str] = None


class BatchProcessor:
    """Manages batch job processing with queuing and resource management"""
    
    def __init__(self, config):
        self.config = config
        self.jobs = {}  # job_id -> BatchJob
        self.job_queue = PriorityQueue()
        self.running_jobs = {}  # job_id -> Process
        
        # Resource limits
        self.max_concurrent_jobs = config.get('max_concurrent_jobs', multiprocessing.cpu_count())
        self.max_memory_total_mb = config.get('max_memory_total_mb', 8192)  # 8GB default
        
        # Database for persistent storage
        self.db_path = Path("/home/activeloguser/activelog/data/cli-interface/batch_jobs.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Working directory for job execution
        self.work_dir = Path("/home/activeloguser/activelog/data/cli-interface/batch_work")
        self.work_dir.mkdir(exist_ok=True)
        
        # Load existing jobs
        self._load_jobs()
        
        # Start worker threads
        self.running = True
        self.worker_threads = []
        for i in range(self.max_concurrent_jobs):
            thread = threading.Thread(target=self._worker_thread, args=(i,), daemon=True)
            thread.start()
            self.worker_threads.append(thread)
        
        # Monitor thread for job cleanup and resource management
        self.monitor_thread = threading.Thread(target=self._monitor_jobs, daemon=True)
        self.monitor_thread.start()
        
        logger.info(f"Batch Processor initialized with {self.max_concurrent_jobs} workers")

    def submit_job(self, job_data: Dict[str, Any]) -> str:
        """Submit new batch job"""
        try:
            # Validate job data
            self._validate_job_data(job_data)
            
            # Create job
            job_id = str(uuid.uuid4())
            job = BatchJob(
                id=job_id,
                job_type=job_data['job_type'],
                command=job_data['command'],
                args=job_data.get('args', []),
                environment=job_data.get('environment', {}),
                priority=JobPriority(job_data.get('priority', JobPriority.NORMAL.value)),
                timeout=job_data.get('timeout', 3600),
                max_memory_mb=job_data.get('max_memory_mb', 1024),
                max_retries=job_data.get('max_retries', 3),
                retry_delay=job_data.get('retry_delay', 60),
                user_id=job_data.get('user_id'),
                metadata=job_data.get('metadata', {})
            )
            
            # Store job
            self.jobs[job_id] = job
            self._save_job(job)
            
            # Queue job for processing
            job.status = JobStatus.QUEUED
            self.job_queue.put((job.priority.value, time.time(), job_id))
            
            logger.info(f"Submitted batch job {job_id} of type {job.job_type}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to submit job: {e}")
            raise

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status and details"""
        try:
            job = self.jobs.get(job_id)
            if not job:
                return {'error': f'Job {job_id} not found'}
            
            status_info = {
                'job_id': job.id,
                'job_type': job.job_type,
                'status': job.status.value,
                'progress': job.progress,
                'created_at': job.created_at,
                'started_at': job.started_at,
                'completed_at': job.completed_at,
                'priority': job.priority.value,
                'timeout': job.timeout,
                'max_retries': job.max_retries,
                'user_id': job.user_id,
                'metadata': job.metadata
            }
            
            # Add result/error information
            if job.result:
                status_info['result'] = job.result
            if job.error:
                status_info['error'] = job.error
            if job.log_file and Path(job.log_file).exists():
                status_info['log_file'] = job.log_file
            if job.output_files:
                status_info['output_files'] = job.output_files
            
            return status_info
            
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return {'error': str(e)}

    def cancel_job(self, job_id: str) -> bool:
        """Cancel running or queued job"""
        try:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False  # Already finished
            
            # Update status
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow().isoformat()
            
            # Kill running process if exists
            if job_id in self.running_jobs:
                process = self.running_jobs[job_id]
                try:
                    process.terminate()
                    time.sleep(1)  # Give it a moment to terminate gracefully
                    if process.poll() is None:
                        process.kill()
                except:
                    pass  # Process might already be dead
                
                del self.running_jobs[job_id]
            
            # Save updated job
            self._save_job(job)
            
            logger.info(f"Cancelled job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    def list_jobs(self, status: Optional[str] = None, 
                  user_id: Optional[str] = None, 
                  limit: int = 100) -> List[Dict[str, Any]]:
        """List batch jobs with optional filtering"""
        try:
            jobs = []
            
            for job in self.jobs.values():
                # Apply filters
                if status and job.status.value != status:
                    continue
                if user_id and job.user_id != user_id:
                    continue
                
                job_info = {
                    'job_id': job.id,
                    'job_type': job.job_type,
                    'status': job.status.value,
                    'progress': job.progress,
                    'created_at': job.created_at,
                    'started_at': job.started_at,
                    'completed_at': job.completed_at,
                    'priority': job.priority.value,
                    'user_id': job.user_id
                }
                
                jobs.append(job_info)
            
            # Sort by creation time (newest first)
            jobs.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Limit results
            return jobs[:limit]
            
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []

    def get_job_logs(self, job_id: str) -> Dict[str, Any]:
        """Get job execution logs"""
        try:
            job = self.jobs.get(job_id)
            if not job:
                return {'error': f'Job {job_id} not found'}
            
            logs = {'job_id': job_id}
            
            if job.log_file and Path(job.log_file).exists():
                try:
                    with open(job.log_file, 'r') as f:
                        logs['log_content'] = f.read()
                except Exception as e:
                    logs['log_error'] = f'Failed to read log file: {e}'
            else:
                logs['log_content'] = 'No log file available'
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get logs for job {job_id}: {e}")
            return {'error': str(e)}

    def get_job_output_files(self, job_id: str) -> List[Dict[str, Any]]:
        """Get list of job output files"""
        try:
            job = self.jobs.get(job_id)
            if not job:
                return []
            
            output_files = []
            
            for file_path in job.output_files:
                path = Path(file_path)
                if path.exists():
                    output_files.append({
                        'path': str(path),
                        'name': path.name,
                        'size': path.stat().st_size,
                        'modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                    })
            
            return output_files
            
        except Exception as e:
            logger.error(f"Failed to get output files for job {job_id}: {e}")
            return []

    def retry_job(self, job_id: str) -> bool:
        """Retry failed job"""
        try:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            if job.status != JobStatus.FAILED:
                return False  # Can only retry failed jobs
            
            # Reset job state
            job.status = JobStatus.QUEUED
            job.started_at = None
            job.completed_at = None
            job.result = None
            job.error = None
            job.progress = 0.0
            
            # Re-queue job
            self.job_queue.put((job.priority.value, time.time(), job_id))
            
            # Save updated job
            self._save_job(job)
            
            logger.info(f"Re-queued job {job_id} for retry")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry job {job_id}: {e}")
            return False

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue and processing statistics"""
        try:
            status_counts = {}
            for status in JobStatus:
                status_counts[status.value] = 0
            
            for job in self.jobs.values():
                status_counts[job.status.value] += 1
            
            return {
                'queue_size': self.job_queue.qsize(),
                'running_jobs': len(self.running_jobs),
                'max_concurrent_jobs': self.max_concurrent_jobs,
                'total_jobs': len(self.jobs),
                'status_distribution': status_counts,
                'memory_usage_mb': self._get_current_memory_usage(),
                'max_memory_mb': self.max_memory_total_mb
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}

    def _validate_job_data(self, data: Dict[str, Any]):
        """Validate job submission data"""
        required_fields = ['job_type', 'command']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate job type
        valid_job_types = [
            'command', 'script', 'data_export', 'data_import', 
            'batch_search', 'file_processing', 'report_generation'
        ]
        if data['job_type'] not in valid_job_types:
            raise ValueError(f"Invalid job type: {data['job_type']}")

    def _worker_thread(self, worker_id: int):
        """Worker thread to process jobs"""
        logger.info(f"Batch worker {worker_id} started")
        
        while self.running:
            try:
                # Get job from queue (blocking with timeout)
                priority, queued_time, job_id = self.job_queue.get(timeout=5)
                
                job = self.jobs.get(job_id)
                if not job:
                    continue
                
                if job.status == JobStatus.CANCELLED:
                    continue
                
                # Check resource limits before starting
                if not self._check_resource_limits(job):
                    # Put job back in queue with lower priority
                    self.job_queue.put((priority + 1, queued_time, job_id))
                    time.sleep(10)  # Wait before retrying
                    continue
                
                logger.info(f"Worker {worker_id} starting job {job_id}")
                
                # Execute job
                self._execute_job(job)
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
        
        logger.info(f"Batch worker {worker_id} stopped")

    def _execute_job(self, job: BatchJob):
        """Execute a batch job"""
        try:
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow().isoformat()
            self._save_job(job)
            
            # Create job working directory
            job_work_dir = self.work_dir / job.id
            job_work_dir.mkdir(exist_ok=True)
            
            # Setup log file
            log_file = job_work_dir / "job.log"
            job.log_file = str(log_file)
            
            # Prepare command
            command = [job.command] + job.args
            
            # Prepare environment
            env = os.environ.copy()
            env.update(job.environment)
            env['JOB_ID'] = job.id
            env['JOB_WORK_DIR'] = str(job_work_dir)
            
            # Execute command
            start_time = time.time()
            
            with open(log_file, 'w') as log_f:
                process = subprocess.Popen(
                    command,
                    cwd=str(job_work_dir),
                    env=env,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                )
                
                # Store running process
                self.running_jobs[job.id] = process
                
                # Monitor process execution
                try:
                    return_code = process.wait(timeout=job.timeout)
                except subprocess.TimeoutExpired:
                    # Job timed out
                    process.kill()
                    job.status = JobStatus.TIMEOUT
                    job.error = f"Job timed out after {job.timeout} seconds"
                    return_code = -1
                finally:
                    # Remove from running jobs
                    if job.id in self.running_jobs:
                        del self.running_jobs[job.id]
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Read log output
            stdout_content = ""
            if log_file.exists():
                with open(log_file, 'r') as f:
                    stdout_content = f.read()
            
            # Collect output files
            output_files = []
            for item in job_work_dir.iterdir():
                if item.name != "job.log":
                    output_files.append(str(item))
            job.output_files = output_files
            
            # Create job result
            result = JobResult(
                job_id=job.id,
                status=JobStatus.COMPLETED if return_code == 0 and job.status != JobStatus.TIMEOUT else JobStatus.FAILED,
                return_code=return_code,
                stdout=stdout_content[:10000],  # Limit stdout size
                execution_time=execution_time,
                output_files=output_files
            )
            
            # Update job status
            job.status = result.status
            job.completed_at = datetime.utcnow().isoformat()
            job.progress = 100.0
            job.result = asdict(result)
            
            if job.status == JobStatus.FAILED and job.status != JobStatus.TIMEOUT:
                job.error = f"Command failed with return code {return_code}"
            
            logger.info(f"Job {job.id} completed with status {job.status.value}")
            
        except Exception as e:
            # Job execution failed
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow().isoformat()
            job.error = f"Execution error: {str(e)}"
            logger.error(f"Job {job.id} execution failed: {e}")
            
            # Remove from running jobs
            if job.id in self.running_jobs:
                del self.running_jobs[job.id]
        
        finally:
            # Always save job state
            self._save_job(job)

    def _check_resource_limits(self, job: BatchJob) -> bool:
        """Check if job can be started within resource limits"""
        try:
            # Check memory limit
            current_memory = self._get_current_memory_usage()
            if current_memory + job.max_memory_mb > self.max_memory_total_mb:
                return False
            
            # Check concurrent job limit
            if len(self.running_jobs) >= self.max_concurrent_jobs:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking resource limits: {e}")
            return True  # Allow on error

    def _get_current_memory_usage(self) -> int:
        """Get current memory usage in MB"""
        try:
            # Simple approximation - sum of running processes
            total_memory = 0
            for job_id in self.running_jobs:
                job = self.jobs.get(job_id)
                if job:
                    total_memory += job.max_memory_mb
            return total_memory
        except:
            return 0

    def _monitor_jobs(self):
        """Monitor job execution and cleanup"""
        while self.running:
            try:
                # Check for stuck jobs
                current_time = datetime.utcnow()
                
                for job_id, job in self.jobs.items():
                    if job.status == JobStatus.RUNNING and job.started_at:
                        started_time = datetime.fromisoformat(job.started_at)
                        if (current_time - started_time).total_seconds() > job.timeout + 60:
                            # Job has been running too long beyond timeout
                            logger.warning(f"Force cancelling stuck job {job_id}")
                            self.cancel_job(job_id)
                
                # Cleanup old completed jobs (older than 7 days)
                cutoff_time = current_time - timedelta(days=7)
                jobs_to_cleanup = []
                
                for job_id, job in self.jobs.items():
                    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                        if job.completed_at:
                            completed_time = datetime.fromisoformat(job.completed_at)
                            if completed_time < cutoff_time:
                                jobs_to_cleanup.append(job_id)
                
                # Remove old jobs
                for job_id in jobs_to_cleanup:
                    self._cleanup_job(job_id)
                
                # Sleep for 1 minute before next check
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in monitor thread: {e}")
                time.sleep(60)

    def _cleanup_job(self, job_id: str):
        """Cleanup job data and files"""
        try:
            job = self.jobs.get(job_id)
            if not job:
                return
            
            # Remove job work directory
            job_work_dir = self.work_dir / job_id
            if job_work_dir.exists():
                shutil.rmtree(job_work_dir, ignore_errors=True)
            
            # Remove from memory
            del self.jobs[job_id]
            
            # Remove from database
            self._delete_job(job_id)
            
            logger.info(f"Cleaned up old job {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup job {job_id}: {e}")

    def _init_database(self):
        """Initialize SQLite database for persistent storage"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_jobs (
                    id TEXT PRIMARY KEY,
                    job_data TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _load_jobs(self):
        """Load jobs from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT job_data FROM batch_jobs")
            rows = cursor.fetchall()
            
            for row in rows:
                job_data = pickle.loads(row[0])
                job = BatchJob(**job_data)
                
                # Reset running jobs to queued on startup
                if job.status == JobStatus.RUNNING:
                    job.status = JobStatus.QUEUED
                    self.job_queue.put((job.priority.value, time.time(), job.id))
                
                self.jobs[job.id] = job
            
            conn.close()
            logger.info(f"Loaded {len(self.jobs)} jobs from database")
            
        except Exception as e:
            logger.error(f"Failed to load jobs: {e}")

    def _save_job(self, job: BatchJob):
        """Save job to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            job_data = pickle.dumps(asdict(job))
            
            cursor.execute("""
                INSERT OR REPLACE INTO batch_jobs 
                (id, job_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                job.id,
                job_data,
                job.created_at,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save job {job.id}: {e}")

    def _delete_job(self, job_id: str):
        """Delete job from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM batch_jobs WHERE id = ?", (job_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")

    def shutdown(self):
        """Shutdown batch processor"""
        self.running = False
        
        # Cancel all running jobs
        for job_id in list(self.running_jobs.keys()):
            self.cancel_job(job_id)
        
        # Wait for worker threads to finish
        for thread in self.worker_threads:
            if thread.is_alive():
                thread.join(timeout=10)
        
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.info("Batch Processor shut down")