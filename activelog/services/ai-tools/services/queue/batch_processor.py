"""
Batch processing queue for expensive AI operations.
Handles priority-based queuing, batching optimization, and resource management.
"""

import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from ...database import get_session
from ...database.models import BatchJob, BatchJobStatus, QueuePriority
from ...settings import settings
from ..compute.optimizer import ComputeOptimizer
from ..cost.estimator import CostEstimator
from ...exceptions import BatchProcessingError


class JobType(Enum):
    TEXT_GENERATION = "text_generation"
    IMAGE_GENERATION = "image_generation"
    VOICE_SYNTHESIS = "voice_synthesis"
    VIDEO_GENERATION = "video_generation"
    LORA_TRAINING = "lora_training"
    BATCH_INFERENCE = "batch_inference"


@dataclass
class BatchJobRequest:
    job_type: JobType
    priority: QueuePriority
    user_id: str
    params: Dict[str, Any]
    callback_url: Optional[str] = None
    max_cost_cc: Optional[Decimal] = None
    deadline: Optional[datetime] = None
    batch_compatible: bool = True


@dataclass
class BatchGroup:
    job_type: JobType
    jobs: List[BatchJob]
    estimated_cost: Decimal
    estimated_time: timedelta
    can_batch: bool


class BatchProcessor:
    def __init__(self):
        self.compute_optimizer = ComputeOptimizer()
        self.cost_estimator = CostEstimator()
        self.worker_pools = {
            JobType.TEXT_GENERATION: asyncio.Semaphore(settings.batch_queue.text_workers),
            JobType.IMAGE_GENERATION: asyncio.Semaphore(settings.batch_queue.image_workers),
            JobType.VOICE_SYNTHESIS: asyncio.Semaphore(settings.batch_queue.voice_workers),
            JobType.VIDEO_GENERATION: asyncio.Semaphore(settings.batch_queue.video_workers),
            JobType.LORA_TRAINING: asyncio.Semaphore(1),  # Resource intensive
            JobType.BATCH_INFERENCE: asyncio.Semaphore(settings.batch_queue.batch_workers)
        }
        self.processing_tasks = {}
        self.batch_groups = {}
        
    async def submit_job(self, request: BatchJobRequest) -> str:
        """Submit a new job to the batch queue."""
        async with get_session() as session:
            # Estimate cost first
            cost_estimate = await self.cost_estimator.estimate_operation_cost(
                request.job_type.value, request.params
            )
            
            # Check if user can afford the operation
            if request.max_cost_cc and cost_estimate["estimated_cost_cc"] > request.max_cost_cc:
                raise BatchProcessingError(
                    f"Estimated cost {cost_estimate['estimated_cost_cc']} CC exceeds maximum {request.max_cost_cc} CC"
                )
            
            # Create job record
            job = BatchJob(
                user_id=request.user_id,
                job_type=request.job_type.value,
                priority=request.priority,
                status=BatchJobStatus.QUEUED,
                params=request.params,
                callback_url=request.callback_url,
                max_cost_cc=request.max_cost_cc,
                estimated_cost_cc=cost_estimate["estimated_cost_cc"],
                estimated_time_minutes=cost_estimate["estimated_time_minutes"],
                deadline=request.deadline,
                batch_compatible=request.batch_compatible,
                created_at=datetime.utcnow()
            )
            
            session.add(job)
            await session.commit()
            await session.refresh(job)
            
            # Trigger queue processing
            asyncio.create_task(self._process_queue())
            
            return job.id
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the current status of a job."""
        async with get_session() as session:
            result = await session.execute(
                select(BatchJob).where(BatchJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                raise BatchProcessingError(f"Job {job_id} not found")
            
            return {
                "id": job.id,
                "status": job.status.value,
                "progress": job.progress,
                "estimated_cost_cc": job.estimated_cost_cc,
                "actual_cost_cc": job.actual_cost_cc,
                "estimated_completion": job.estimated_completion_time,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error_message": job.error_message,
                "result": job.result
            }
    
    async def cancel_job(self, job_id: str, user_id: str) -> bool:
        """Cancel a queued or running job."""
        async with get_session() as session:
            result = await session.execute(
                select(BatchJob).where(
                    and_(BatchJob.id == job_id, BatchJob.user_id == user_id)
                )
            )
            job = result.scalar_one_or_none()
            
            if not job:
                raise BatchProcessingError(f"Job {job_id} not found or not owned by user")
            
            if job.status == BatchJobStatus.COMPLETED:
                return False
            
            if job.status == BatchJobStatus.RUNNING:
                # Cancel the running task
                if job_id in self.processing_tasks:
                    self.processing_tasks[job_id].cancel()
            
            job.status = BatchJobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            await session.commit()
            
            return True
    
    async def _process_queue(self):
        """Main queue processing loop."""
        try:
            async with get_session() as session:
                # Get all queued jobs ordered by priority and creation time
                result = await session.execute(
                    select(BatchJob).where(
                        BatchJob.status == BatchJobStatus.QUEUED
                    ).order_by(
                        BatchJob.priority.desc(),
                        BatchJob.created_at.asc()
                    )
                )
                queued_jobs = result.scalars().all()
                
                if not queued_jobs:
                    return
                
                # Group jobs by type and batching potential
                batch_groups = await self._create_batch_groups(queued_jobs)
                
                # Process each batch group
                for group in batch_groups:
                    await self._process_batch_group(group)
                    
        except Exception as e:
            print(f"Error in queue processing: {e}")
    
    async def _create_batch_groups(self, jobs: List[BatchJob]) -> List[BatchGroup]:
        """Group jobs for optimal batch processing."""
        job_groups = {}
        
        for job in jobs:
            job_type = JobType(job.job_type)
            
            if job_type not in job_groups:
                job_groups[job_type] = []
            
            job_groups[job_type].append(job)
        
        batch_groups = []
        
        for job_type, type_jobs in job_groups.items():
            if job_type in [JobType.TEXT_GENERATION, JobType.BATCH_INFERENCE]:
                # These can be batched effectively
                batch_groups.extend(await self._create_batchable_groups(job_type, type_jobs))
            else:
                # Process individually
                for job in type_jobs:
                    group = BatchGroup(
                        job_type=job_type,
                        jobs=[job],
                        estimated_cost=job.estimated_cost_cc,
                        estimated_time=timedelta(minutes=float(job.estimated_time_minutes)),
                        can_batch=False
                    )
                    batch_groups.append(group)
        
        return batch_groups
    
    async def _create_batchable_groups(self, job_type: JobType, jobs: List[BatchJob]) -> List[BatchGroup]:
        """Create optimally sized batch groups for batchable job types."""
        batch_groups = []
        current_batch = []
        current_cost = Decimal('0')
        current_time = timedelta()
        
        max_batch_size = settings.batch_queue.max_batch_size
        max_batch_cost = Decimal(str(settings.batch_queue.max_batch_cost_cc))
        
        for job in jobs:
            if not job.batch_compatible:
                # Process individually
                group = BatchGroup(
                    job_type=job_type,
                    jobs=[job],
                    estimated_cost=job.estimated_cost_cc,
                    estimated_time=timedelta(minutes=float(job.estimated_time_minutes)),
                    can_batch=False
                )
                batch_groups.append(group)
                continue
            
            job_cost = job.estimated_cost_cc
            job_time = timedelta(minutes=float(job.estimated_time_minutes))
            
            # Check if adding this job exceeds limits
            if (len(current_batch) >= max_batch_size or
                current_cost + job_cost > max_batch_cost or
                len(current_batch) > 0 and job.priority != current_batch[0].priority):
                
                # Finalize current batch
                if current_batch:
                    group = BatchGroup(
                        job_type=job_type,
                        jobs=current_batch,
                        estimated_cost=current_cost,
                        estimated_time=current_time,
                        can_batch=True
                    )
                    batch_groups.append(group)
                
                # Start new batch
                current_batch = [job]
                current_cost = job_cost
                current_time = job_time
            else:
                current_batch.append(job)
                current_cost += job_cost
                current_time = max(current_time, job_time)  # Parallel processing
        
        # Add final batch
        if current_batch:
            group = BatchGroup(
                job_type=job_type,
                jobs=current_batch,
                estimated_cost=current_cost,
                estimated_time=current_time,
                can_batch=True
            )
            batch_groups.append(group)
        
        return batch_groups
    
    async def _process_batch_group(self, group: BatchGroup):
        """Process a batch group of jobs."""
        semaphore = self.worker_pools[group.job_type]
        
        async with semaphore:
            # Update job statuses to running
            async with get_session() as session:
                for job in group.jobs:
                    job.status = BatchJobStatus.RUNNING
                    job.started_at = datetime.utcnow()
                    job.estimated_completion_time = datetime.utcnow() + group.estimated_time
                    
                    # Store task reference for cancellation
                    if len(group.jobs) == 1:
                        task = asyncio.create_task(self._process_single_job(job))
                        self.processing_tasks[job.id] = task
                    
                await session.commit()
            
            try:
                if group.can_batch and len(group.jobs) > 1:
                    await self._process_batch_jobs(group)
                else:
                    # Process single job or non-batchable
                    for job in group.jobs:
                        await self._process_single_job(job)
                        
            except Exception as e:
                # Mark all jobs in group as failed
                async with get_session() as session:
                    for job in group.jobs:
                        job.status = BatchJobStatus.FAILED
                        job.error_message = str(e)
                        job.completed_at = datetime.utcnow()
                        if job.id in self.processing_tasks:
                            del self.processing_tasks[job.id]
                    await session.commit()
    
    async def _process_single_job(self, job: BatchJob):
        """Process a single job."""
        try:
            # Get compute recommendation
            compute_rec = await self.compute_optimizer.optimize_for_operation(
                job.job_type, job.params
            )
            
            # Execute job based on type and compute recommendation
            result = await self._execute_job(job, compute_rec)
            
            # Update job as completed
            async with get_session() as session:
                job.status = BatchJobStatus.COMPLETED
                job.result = result
                job.actual_cost_cc = result.get('actual_cost_cc', job.estimated_cost_cc)
                job.completed_at = datetime.utcnow()
                job.progress = 100
                
                if job.id in self.processing_tasks:
                    del self.processing_tasks[job.id]
                
                await session.commit()
            
            # Call callback if provided
            if job.callback_url:
                await self._call_callback(job.callback_url, job.id, result)
                
        except Exception as e:
            async with get_session() as session:
                job.status = BatchJobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                
                if job.id in self.processing_tasks:
                    del self.processing_tasks[job.id]
                
                await session.commit()
            raise
    
    async def _process_batch_jobs(self, group: BatchGroup):
        """Process multiple jobs as a batch for optimization."""
        try:
            # Combine parameters for batch processing
            batch_params = {
                'jobs': [{'id': job.id, 'params': job.params} for job in group.jobs],
                'job_type': group.job_type.value
            }
            
            # Get compute recommendation for batch
            compute_rec = await self.compute_optimizer.optimize_for_operation(
                group.job_type.value, batch_params
            )
            
            # Execute batch job
            batch_result = await self._execute_batch_job(group, compute_rec)
            
            # Update individual job results
            async with get_session() as session:
                for i, job in enumerate(group.jobs):
                    job_result = batch_result.get(f'job_{i}', {})
                    job.status = BatchJobStatus.COMPLETED
                    job.result = job_result
                    job.actual_cost_cc = job_result.get('actual_cost_cc', job.estimated_cost_cc)
                    job.completed_at = datetime.utcnow()
                    job.progress = 100
                    
                    if job.id in self.processing_tasks:
                        del self.processing_tasks[job.id]
                    
                    # Call callback if provided
                    if job.callback_url:
                        await self._call_callback(job.callback_url, job.id, job_result)
                
                await session.commit()
                
        except Exception as e:
            # Mark all jobs as failed
            async with get_session() as session:
                for job in group.jobs:
                    job.status = BatchJobStatus.FAILED
                    job.error_message = str(e)
                    job.completed_at = datetime.utcnow()
                    
                    if job.id in self.processing_tasks:
                        del self.processing_tasks[job.id]
                
                await session.commit()
            raise
    
    async def _execute_job(self, job: BatchJob, compute_rec: Dict) -> Dict[str, Any]:
        """Execute a single job based on its type."""
        job_type = JobType(job.job_type)
        
        if job_type == JobType.TEXT_GENERATION:
            return await self._execute_text_generation(job, compute_rec)
        elif job_type == JobType.IMAGE_GENERATION:
            return await self._execute_image_generation(job, compute_rec)
        elif job_type == JobType.VOICE_SYNTHESIS:
            return await self._execute_voice_synthesis(job, compute_rec)
        elif job_type == JobType.VIDEO_GENERATION:
            return await self._execute_video_generation(job, compute_rec)
        elif job_type == JobType.LORA_TRAINING:
            return await self._execute_lora_training(job, compute_rec)
        else:
            raise BatchProcessingError(f"Unknown job type: {job_type}")
    
    async def _execute_batch_job(self, group: BatchGroup, compute_rec: Dict) -> Dict[str, Any]:
        """Execute a batch of jobs together."""
        if group.job_type == JobType.TEXT_GENERATION:
            return await self._execute_batch_text_generation(group, compute_rec)
        elif group.job_type == JobType.BATCH_INFERENCE:
            return await self._execute_batch_inference(group, compute_rec)
        else:
            raise BatchProcessingError(f"Batch processing not supported for: {group.job_type}")
    
    async def _execute_text_generation(self, job: BatchJob, compute_rec: Dict) -> Dict[str, Any]:
        """Execute text generation job."""
        # Import here to avoid circular imports
        from ..llm.llm_router import LLMRouter
        
        router = LLMRouter()
        result = await router.generate_text(
            prompt=job.params.get('prompt', ''),
            model=job.params.get('model', 'auto'),
            max_tokens=job.params.get('max_tokens', 1000),
            temperature=job.params.get('temperature', 0.7)
        )
        
        return {
            'text': result['text'],
            'model_used': result['model_used'],
            'tokens_used': result['tokens_used'],
            'actual_cost_cc': result['cost_cc']
        }
    
    async def _execute_batch_text_generation(self, group: BatchGroup, compute_rec: Dict) -> Dict[str, Any]:
        """Execute batch text generation."""
        from ..llm.llm_router import LLMRouter
        
        router = LLMRouter()
        batch_results = {}
        
        # Process all prompts in batch
        prompts = [job.params.get('prompt', '') for job in group.jobs]
        results = await router.batch_generate_text(prompts)
        
        for i, result in enumerate(results):
            batch_results[f'job_{i}'] = {
                'text': result['text'],
                'model_used': result['model_used'],
                'tokens_used': result['tokens_used'],
                'actual_cost_cc': result['cost_cc']
            }
        
        return batch_results
    
    async def _execute_image_generation(self, job: BatchJob, compute_rec: Dict) -> Dict[str, Any]:
        """Execute image generation job."""
        from ..image.image_generator import ImageGenerator
        
        generator = ImageGenerator()
        result = await generator.generate_image(
            prompt=job.params.get('prompt', ''),
            model=job.params.get('model', 'auto'),
            size=job.params.get('size', '1024x1024'),
            quality=job.params.get('quality', 'standard')
        )
        
        return {
            'image_url': result['image_url'],
            'image_path': result.get('image_path'),
            'model_used': result['model_used'],
            'actual_cost_cc': result['cost_cc']
        }
    
    async def _execute_voice_synthesis(self, job: BatchJob, compute_rec: Dict) -> Dict[str, Any]:
        """Execute voice synthesis job."""
        from ..voice.voice_synthesizer import VoiceSynthesizer
        
        synthesizer = VoiceSynthesizer()
        result = await synthesizer.synthesize_speech(
            text=job.params.get('text', ''),
            voice_id=job.params.get('voice_id', 'default'),
            model=job.params.get('model', 'auto')
        )
        
        return {
            'audio_url': result['audio_url'],
            'audio_path': result.get('audio_path'),
            'model_used': result['model_used'],
            'duration_seconds': result['duration_seconds'],
            'actual_cost_cc': result['cost_cc']
        }
    
    async def _execute_video_generation(self, job: BatchJob, compute_rec: Dict) -> Dict[str, Any]:
        """Execute video generation job."""
        # Placeholder - will be implemented with video generation pipeline
        return {
            'video_url': 'placeholder',
            'actual_cost_cc': job.estimated_cost_cc
        }
    
    async def _execute_lora_training(self, job: BatchJob, compute_rec: Dict) -> Dict[str, Any]:
        """Execute LORA training job."""
        # Placeholder - will be implemented with LORA training interface
        return {
            'model_path': 'placeholder',
            'actual_cost_cc': job.estimated_cost_cc
        }
    
    async def _execute_batch_inference(self, group: BatchGroup, compute_rec: Dict) -> Dict[str, Any]:
        """Execute batch inference job."""
        # Placeholder for batch inference processing
        batch_results = {}
        
        for i, job in enumerate(group.jobs):
            batch_results[f'job_{i}'] = {
                'result': 'placeholder',
                'actual_cost_cc': job.estimated_cost_cc
            }
        
        return batch_results
    
    async def _call_callback(self, callback_url: str, job_id: str, result: Dict[str, Any]):
        """Call the callback URL with job results."""
        try:
            import aiohttp
            
            callback_data = {
                'job_id': job_id,
                'status': 'completed',
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                await session.post(
                    callback_url,
                    json=callback_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                )
                
        except Exception as e:
            print(f"Failed to call callback for job {job_id}: {e}")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics."""
        async with get_session() as session:
            # Count jobs by status
            result = await session.execute(
                select(BatchJob.status, BatchJob.job_type).where(
                    BatchJob.status.in_([
                        BatchJobStatus.QUEUED,
                        BatchJobStatus.RUNNING,
                        BatchJobStatus.COMPLETED,
                        BatchJobStatus.FAILED
                    ])
                )
            )
            
            stats = {
                'total_queued': 0,
                'total_running': 0,
                'by_type': {},
                'by_priority': {}
            }
            
            for status, job_type in result:
                if job_type not in stats['by_type']:
                    stats['by_type'][job_type] = {'queued': 0, 'running': 0}
                
                if status == BatchJobStatus.QUEUED:
                    stats['total_queued'] += 1
                    stats['by_type'][job_type]['queued'] += 1
                elif status == BatchJobStatus.RUNNING:
                    stats['total_running'] += 1
                    stats['by_type'][job_type]['running'] += 1
            
            return stats


# Global instance
batch_processor = BatchProcessor()