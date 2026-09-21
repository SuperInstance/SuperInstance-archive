#!/usr/bin/env python3
"""
GPU Compute Optimizer and Workload Distribution

Provides intelligent GPU compute optimization including workload scheduling,
memory management, multi-GPU orchestration, and heterogeneous computing.
"""

import asyncio
import threading
import time
import json
import logging
import math
import numpy as np
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import heapq
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import psutil
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GPUType(Enum):
    """GPU types and architectures"""
    NVIDIA_GTX = "nvidia_gtx"
    NVIDIA_RTX = "nvidia_rtx"
    NVIDIA_TESLA = "nvidia_tesla"
    NVIDIA_A100 = "nvidia_a100"
    AMD_RADEON = "amd_radeon"
    AMD_INSTINCT = "amd_instinct"
    INTEL_ARC = "intel_arc"
    APPLE_M_SERIES = "apple_m_series"
    INTEGRATED = "integrated"
    UNKNOWN = "unknown"


class ComputeType(Enum):
    """Types of compute workloads"""
    GRAPHICS = "graphics"
    COMPUTE = "compute"
    AI_INFERENCE = "ai_inference"
    AI_TRAINING = "ai_training"
    SCIENTIFIC = "scientific"
    CRYPTOCURRENCY = "cryptocurrency"
    VIDEO_ENCODING = "video_encoding"
    RAY_TRACING = "ray_tracing"
    GENERAL = "general"


class WorkloadPriority(Enum):
    """Workload priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class GPUSchedulingStrategy(Enum):
    """GPU scheduling strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    AFFINITY = "affinity"
    HETEROGENEOUS = "heterogeneous"
    POWER_EFFICIENT = "power_efficient"
    PERFORMANCE_FIRST = "performance_first"


@dataclass
class GPUDevice:
    """GPU device information"""
    id: int
    name: str
    gpu_type: GPUType
    memory_total_mb: int
    memory_free_mb: int
    memory_used_mb: int
    utilization_percent: float
    power_usage_watts: float
    temperature_celsius: float
    compute_capability: str
    driver_version: str
    cuda_cores: int = 0
    tensor_cores: int = 0
    rt_cores: int = 0
    base_clock_mhz: int = 0
    boost_clock_mhz: int = 0
    memory_bandwidth_gbps: float = 0.0
    pcie_gen: int = 3
    pcie_lanes: int = 16
    is_available: bool = True
    last_updated: float = 0.0
    
    def memory_utilization_percent(self) -> float:
        """Calculate memory utilization percentage"""
        if self.memory_total_mb == 0:
            return 0.0
        return (self.memory_used_mb / self.memory_total_mb) * 100.0
    
    def compute_score(self) -> float:
        """Calculate relative compute performance score"""
        base_score = self.cuda_cores * (self.boost_clock_mhz / 1000.0)
        
        # Adjust for architecture improvements
        if self.gpu_type in [GPUType.NVIDIA_RTX, GPUType.NVIDIA_A100]:
            base_score *= 1.5  # Modern architecture bonus
        
        if self.tensor_cores > 0:
            base_score += self.tensor_cores * 10  # AI workload bonus
        
        if self.rt_cores > 0:
            base_score += self.rt_cores * 5  # Ray tracing bonus
        
        return base_score
    
    def power_efficiency_score(self) -> float:
        """Calculate power efficiency (performance per watt)"""
        if self.power_usage_watts == 0:
            return 0.0
        return self.compute_score() / self.power_usage_watts


@dataclass 
class GPUWorkload:
    """GPU workload specification"""
    id: str
    name: str
    compute_type: ComputeType
    priority: WorkloadPriority
    memory_required_mb: int
    estimated_duration_seconds: float
    compute_units_required: float  # Relative compute requirement (0.0-1.0)
    can_split: bool = False
    requires_double_precision: bool = False
    requires_tensor_cores: bool = False
    requires_rt_cores: bool = False
    preferred_gpu_types: List[GPUType] = None
    exclusivity_required: bool = False
    callback: Optional[Callable] = None
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    assigned_gpu_id: Optional[int] = None
    progress: float = 0.0
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        if self.preferred_gpu_types is None:
            self.preferred_gpu_types = []
    
    def is_compatible_with_gpu(self, gpu: GPUDevice) -> bool:
        """Check if workload is compatible with GPU"""
        # Memory check
        if self.memory_required_mb > gpu.memory_free_mb:
            return False
        
        # GPU type preference
        if self.preferred_gpu_types and gpu.gpu_type not in self.preferred_gpu_types:
            return False
        
        # Feature requirements
        if self.requires_tensor_cores and gpu.tensor_cores == 0:
            return False
        
        if self.requires_rt_cores and gpu.rt_cores == 0:
            return False
        
        return True
    
    def calculate_fit_score(self, gpu: GPUDevice) -> float:
        """Calculate how well this workload fits on the GPU"""
        if not self.is_compatible_with_gpu(gpu):
            return 0.0
        
        # Base score from compute capability
        score = gpu.compute_score()
        
        # Adjust for memory efficiency
        memory_efficiency = 1.0 - (self.memory_required_mb / gpu.memory_total_mb)
        score *= (0.5 + 0.5 * memory_efficiency)
        
        # Adjust for utilization
        utilization_penalty = gpu.utilization_percent / 100.0
        score *= (1.0 - 0.3 * utilization_penalty)
        
        # Workload-specific bonuses
        if self.compute_type == ComputeType.AI_TRAINING and gpu.tensor_cores > 0:
            score *= 1.3
        elif self.compute_type == ComputeType.RAY_TRACING and gpu.rt_cores > 0:
            score *= 1.3
        
        return score


class GPUMonitor:
    """Monitors GPU status and performance"""
    
    def __init__(self, update_interval: float = 1.0):
        self.update_interval = update_interval
        self.devices: Dict[int, GPUDevice] = {}
        self._monitoring = False
        self._monitor_task = None
        self._lock = threading.Lock()
        self.has_nvidia = self._check_nvidia()
        self.has_amd = self._check_amd()
        
    def _check_nvidia(self) -> bool:
        """Check if NVIDIA GPUs are available"""
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=count', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _check_amd(self) -> bool:
        """Check if AMD GPUs are available"""
        try:
            result = subprocess.run(['rocm-smi', '--showid'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    async def start(self):
        """Start GPU monitoring"""
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        # Initial scan
        await self._scan_gpus()
        
        logger.info(f"GPU monitoring started. Found {len(self.devices)} GPUs")
    
    async def stop(self):
        """Stop GPU monitoring"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("GPU monitoring stopped")
    
    async def _monitor_loop(self):
        """GPU monitoring loop"""
        while self._monitoring:
            try:
                await self._scan_gpus()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"GPU monitoring error: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _scan_gpus(self):
        """Scan and update GPU information"""
        new_devices = {}
        
        if self.has_nvidia:
            nvidia_devices = await self._scan_nvidia_gpus()
            new_devices.update(nvidia_devices)
        
        if self.has_amd:
            amd_devices = await self._scan_amd_gpus()
            new_devices.update(amd_devices)
        
        # Update devices
        with self._lock:
            self.devices = new_devices
            current_time = time.time()
            for device in self.devices.values():
                device.last_updated = current_time
    
    async def _scan_nvidia_gpus(self) -> Dict[int, GPUDevice]:
        """Scan NVIDIA GPUs using nvidia-ml-py or nvidia-smi"""
        devices = {}
        
        try:
            # Try nvidia-ml-py first (more accurate)
            try:
                import pynvml
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    
                    name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    
                    try:
                        power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to watts
                    except:
                        power_usage = 0.0
                    
                    try:
                        temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    except:
                        temperature = 0.0
                    
                    # Determine GPU type
                    gpu_type = self._classify_nvidia_gpu(name)
                    
                    devices[i] = GPUDevice(
                        id=i,
                        name=name,
                        gpu_type=gpu_type,
                        memory_total_mb=memory_info.total // (1024 * 1024),
                        memory_free_mb=memory_info.free // (1024 * 1024),
                        memory_used_mb=memory_info.used // (1024 * 1024),
                        utilization_percent=float(utilization.gpu),
                        power_usage_watts=power_usage,
                        temperature_celsius=float(temperature),
                        compute_capability="",  # Would need additional queries
                        driver_version="",     # Would need additional queries
                        cuda_cores=self._estimate_cuda_cores(name),
                        tensor_cores=self._estimate_tensor_cores(name),
                        rt_cores=self._estimate_rt_cores(name)
                    )
                
                pynvml.nvmlShutdown()
                
            except ImportError:
                # Fall back to nvidia-smi
                devices = await self._scan_nvidia_smi()
                
        except Exception as e:
            logger.error(f"Error scanning NVIDIA GPUs: {e}")
        
        return devices
    
    async def _scan_nvidia_smi(self) -> Dict[int, GPUDevice]:
        """Scan NVIDIA GPUs using nvidia-smi command"""
        devices = {}
        
        try:
            cmd = [
                'nvidia-smi',
                '--query-gpu=index,name,memory.total,memory.free,memory.used,utilization.gpu,power.draw,temperature.gpu',
                '--format=csv,noheader,nounits'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 8:
                        gpu_id = int(parts[0])
                        name = parts[1]
                        
                        devices[gpu_id] = GPUDevice(
                            id=gpu_id,
                            name=name,
                            gpu_type=self._classify_nvidia_gpu(name),
                            memory_total_mb=int(parts[2]),
                            memory_free_mb=int(parts[3]),
                            memory_used_mb=int(parts[4]),
                            utilization_percent=float(parts[5]) if parts[5] != '[Not Supported]' else 0.0,
                            power_usage_watts=float(parts[6]) if parts[6] != '[Not Supported]' else 0.0,
                            temperature_celsius=float(parts[7]) if parts[7] != '[Not Supported]' else 0.0,
                            compute_capability="",
                            driver_version="",
                            cuda_cores=self._estimate_cuda_cores(name),
                            tensor_cores=self._estimate_tensor_cores(name),
                            rt_cores=self._estimate_rt_cores(name)
                        )
        
        except Exception as e:
            logger.error(f"Error running nvidia-smi: {e}")
        
        return devices
    
    async def _scan_amd_gpus(self) -> Dict[int, GPUDevice]:
        """Scan AMD GPUs using ROCm tools"""
        devices = {}
        
        try:
            # Use rocm-smi to get GPU information
            result = subprocess.run(['rocm-smi', '--showid', '--showtemp', '--showuse', '--showmeminfo', 'all'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse rocm-smi output (format varies)
                # This is a simplified parser - real implementation would be more robust
                lines = result.stdout.strip().split('\n')
                current_gpu = None
                
                for line in lines:
                    if 'GPU' in line and ':' in line:
                        try:
                            gpu_id = int(line.split()[1])
                            current_gpu = gpu_id
                            
                            devices[gpu_id] = GPUDevice(
                                id=gpu_id,
                                name="AMD GPU",  # Would need additional parsing
                                gpu_type=GPUType.AMD_RADEON,  # Default, would classify better
                                memory_total_mb=0,  # Would parse from output
                                memory_free_mb=0,
                                memory_used_mb=0,
                                utilization_percent=0.0,
                                power_usage_watts=0.0,
                                temperature_celsius=0.0,
                                compute_capability="",
                                driver_version=""
                            )
                        except (ValueError, IndexError):
                            continue
        
        except Exception as e:
            logger.error(f"Error scanning AMD GPUs: {e}")
        
        return devices
    
    def _classify_nvidia_gpu(self, name: str) -> GPUType:
        """Classify NVIDIA GPU by name"""
        name_lower = name.lower()
        
        if 'a100' in name_lower:
            return GPUType.NVIDIA_A100
        elif 'tesla' in name_lower:
            return GPUType.NVIDIA_TESLA
        elif 'rtx' in name_lower:
            return GPUType.NVIDIA_RTX
        elif 'gtx' in name_lower:
            return GPUType.NVIDIA_GTX
        else:
            return GPUType.NVIDIA_GTX
    
    def _estimate_cuda_cores(self, name: str) -> int:
        """Estimate CUDA cores based on GPU name"""
        name_lower = name.lower()
        
        # Simplified estimation - real implementation would have comprehensive database
        if '4090' in name_lower:
            return 16384
        elif '4080' in name_lower:
            return 9728
        elif '3090' in name_lower:
            return 10496
        elif '3080' in name_lower:
            return 8704
        elif 'a100' in name_lower:
            return 6912
        else:
            return 2048  # Conservative estimate
    
    def _estimate_tensor_cores(self, name: str) -> int:
        """Estimate Tensor cores based on GPU name"""
        name_lower = name.lower()
        
        if any(x in name_lower for x in ['rtx', 'a100', 'tesla v100']):
            # Modern cards have tensor cores
            if '4090' in name_lower:
                return 128
            elif '4080' in name_lower:
                return 76
            elif '3090' in name_lower:
                return 328
            elif 'a100' in name_lower:
                return 432
            else:
                return 64  # Conservative estimate
        
        return 0
    
    def _estimate_rt_cores(self, name: str) -> int:
        """Estimate RT cores based on GPU name"""
        name_lower = name.lower()
        
        if 'rtx' in name_lower:
            if '4090' in name_lower:
                return 128
            elif '4080' in name_lower:
                return 76
            elif '3090' in name_lower:
                return 82
            else:
                return 48  # Conservative estimate
        
        return 0
    
    def get_devices(self) -> Dict[int, GPUDevice]:
        """Get current GPU devices"""
        with self._lock:
            return self.devices.copy()
    
    def get_device(self, gpu_id: int) -> Optional[GPUDevice]:
        """Get specific GPU device"""
        with self._lock:
            return self.devices.get(gpu_id)


class GPUScheduler:
    """Intelligent GPU workload scheduler"""
    
    def __init__(self, gpu_monitor: GPUMonitor, strategy: GPUSchedulingStrategy = GPUSchedulingStrategy.LEAST_LOADED):
        self.gpu_monitor = gpu_monitor
        self.strategy = strategy
        
        # Workload queues by priority
        self.workload_queues: Dict[WorkloadPriority, deque] = {
            priority: deque() for priority in WorkloadPriority
        }
        
        # Active workloads
        self.active_workloads: Dict[str, GPUWorkload] = {}
        
        # GPU assignments
        self.gpu_assignments: Dict[int, Set[str]] = defaultdict(set)
        
        # Scheduling history and statistics
        self.scheduling_history: List[Dict[str, Any]] = []
        self.scheduling_stats = {
            'total_scheduled': 0,
            'total_completed': 0,
            'total_failed': 0,
            'average_queue_time': 0.0,
            'average_execution_time': 0.0
        }
        
        self._scheduling = False
        self._scheduler_task = None
        self._lock = threading.Lock()
    
    async def start(self):
        """Start the GPU scheduler"""
        self._scheduling = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("GPU scheduler started")
    
    async def stop(self):
        """Stop the GPU scheduler"""
        self._scheduling = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("GPU scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self._scheduling:
            try:
                await self._process_workloads()
                await asyncio.sleep(0.1)  # High frequency scheduling
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(1.0)
    
    async def _process_workloads(self):
        """Process pending workloads"""
        with self._lock:
            available_gpus = self._get_available_gpus()
            
            if not available_gpus:
                return
            
            # Process workloads by priority
            for priority in [WorkloadPriority.CRITICAL, WorkloadPriority.HIGH, 
                           WorkloadPriority.NORMAL, WorkloadPriority.LOW, 
                           WorkloadPriority.BACKGROUND]:
                
                queue = self.workload_queues[priority]
                
                while queue and available_gpus:
                    workload = queue.popleft()
                    
                    # Find best GPU for this workload
                    best_gpu = self._select_best_gpu(workload, available_gpus)
                    
                    if best_gpu:
                        await self._assign_workload(workload, best_gpu)
                        available_gpus.remove(best_gpu.id)
                        
                        self.scheduling_stats['total_scheduled'] += 1
                    else:
                        # No suitable GPU available, put back in queue
                        queue.appendleft(workload)
                        break
    
    def _get_available_gpus(self) -> List[GPUDevice]:
        """Get list of available GPUs"""
        devices = self.gpu_monitor.get_devices()
        available = []
        
        for gpu_id, device in devices.items():
            if not device.is_available:
                continue
                
            # Check if GPU is overloaded
            if device.utilization_percent > 95:
                continue
            
            # Check if GPU has enough memory
            if device.memory_free_mb < 100:  # At least 100MB free
                continue
                
            available.append(device)
        
        return available
    
    def _select_best_gpu(self, workload: GPUWorkload, available_gpus: List[GPUDevice]) -> Optional[GPUDevice]:
        """Select the best GPU for a workload based on strategy"""
        compatible_gpus = [gpu for gpu in available_gpus if workload.is_compatible_with_gpu(gpu)]
        
        if not compatible_gpus:
            return None
        
        if self.strategy == GPUSchedulingStrategy.ROUND_ROBIN:
            return min(compatible_gpus, key=lambda gpu: len(self.gpu_assignments[gpu.id]))
        
        elif self.strategy == GPUSchedulingStrategy.LEAST_LOADED:
            return min(compatible_gpus, key=lambda gpu: gpu.utilization_percent)
        
        elif self.strategy == GPUSchedulingStrategy.AFFINITY:
            # Prefer GPUs already handling similar workloads
            def affinity_score(gpu):
                base_score = workload.calculate_fit_score(gpu)
                
                # Check for similar workloads on this GPU
                similar_workloads = 0
                for wid in self.gpu_assignments[gpu.id]:
                    if wid in self.active_workloads:
                        if self.active_workloads[wid].compute_type == workload.compute_type:
                            similar_workloads += 1
                
                return base_score * (1.0 + 0.1 * similar_workloads)
            
            return max(compatible_gpus, key=affinity_score)
        
        elif self.strategy == GPUSchedulingStrategy.HETEROGENEOUS:
            # Distribute different workload types across GPUs
            def heterogeneous_score(gpu):
                base_score = workload.calculate_fit_score(gpu)
                
                # Penalize if GPU already has same workload type
                same_type_penalty = 0
                for wid in self.gpu_assignments[gpu.id]:
                    if wid in self.active_workloads:
                        if self.active_workloads[wid].compute_type == workload.compute_type:
                            same_type_penalty += 0.2
                
                return base_score * (1.0 - same_type_penalty)
            
            return max(compatible_gpus, key=heterogeneous_score)
        
        elif self.strategy == GPUSchedulingStrategy.POWER_EFFICIENT:
            return max(compatible_gpus, key=lambda gpu: gpu.power_efficiency_score())
        
        elif self.strategy == GPUSchedulingStrategy.PERFORMANCE_FIRST:
            return max(compatible_gpus, key=lambda gpu: gpu.compute_score())
        
        else:
            # Default to least loaded
            return min(compatible_gpus, key=lambda gpu: gpu.utilization_percent)
    
    async def _assign_workload(self, workload: GPUWorkload, gpu: GPUDevice):
        """Assign workload to GPU"""
        workload.assigned_gpu_id = gpu.id
        workload.started_at = time.time()
        
        self.active_workloads[workload.id] = workload
        self.gpu_assignments[gpu.id].add(workload.id)
        
        # Record scheduling event
        self.scheduling_history.append({
            'timestamp': time.time(),
            'workload_id': workload.id,
            'gpu_id': gpu.id,
            'queue_time': workload.started_at - workload.created_at,
            'action': 'assigned'
        })
        
        # Start workload execution (this would be expanded for real workloads)
        asyncio.create_task(self._execute_workload(workload))
        
        logger.info(f"Assigned workload {workload.id} to GPU {gpu.id}")
    
    async def _execute_workload(self, workload: GPUWorkload):
        """Execute workload (placeholder for actual execution)"""
        try:
            # Simulate workload execution
            total_duration = workload.estimated_duration_seconds
            steps = max(1, int(total_duration / 0.1))  # Update progress every 100ms
            
            for step in range(steps + 1):
                if workload.id not in self.active_workloads:
                    # Workload was cancelled
                    return
                
                workload.progress = step / steps
                await asyncio.sleep(0.1)
            
            # Mark as completed
            await self._complete_workload(workload.id, success=True)
            
        except Exception as e:
            logger.error(f"Workload {workload.id} execution failed: {e}")
            await self._complete_workload(workload.id, success=False)
    
    async def _complete_workload(self, workload_id: str, success: bool):
        """Complete workload execution"""
        with self._lock:
            if workload_id not in self.active_workloads:
                return
            
            workload = self.active_workloads.pop(workload_id)
            workload.completed_at = time.time()
            
            if workload.assigned_gpu_id is not None:
                self.gpu_assignments[workload.assigned_gpu_id].discard(workload_id)
            
            # Update statistics
            if success:
                self.scheduling_stats['total_completed'] += 1
            else:
                self.scheduling_stats['total_failed'] += 1
            
            execution_time = workload.completed_at - (workload.started_at or workload.created_at)
            self.scheduling_stats['average_execution_time'] = (
                (self.scheduling_stats['average_execution_time'] * (self.scheduling_stats['total_completed'] - 1) + execution_time) /
                self.scheduling_stats['total_completed']
            ) if self.scheduling_stats['total_completed'] > 0 else 0.0
            
            # Record completion event
            self.scheduling_history.append({
                'timestamp': time.time(),
                'workload_id': workload.id,
                'gpu_id': workload.assigned_gpu_id,
                'execution_time': execution_time,
                'success': success,
                'action': 'completed'
            })
            
            # Execute callback if provided
            if workload.callback and success:
                try:
                    if asyncio.iscoroutinefunction(workload.callback):
                        await workload.callback(workload)
                    else:
                        workload.callback(workload)
                except Exception as e:
                    logger.error(f"Workload callback error: {e}")
            
            logger.info(f"Workload {workload_id} {'completed' if success else 'failed'}")
    
    def submit_workload(self, workload: GPUWorkload) -> str:
        """Submit workload for execution"""
        with self._lock:
            self.workload_queues[workload.priority].append(workload)
            
            logger.info(f"Submitted workload {workload.id} with priority {workload.priority.value}")
            return workload.id
    
    def cancel_workload(self, workload_id: str) -> bool:
        """Cancel a workload"""
        with self._lock:
            # Check if it's currently running
            if workload_id in self.active_workloads:
                workload = self.active_workloads.pop(workload_id)
                if workload.assigned_gpu_id is not None:
                    self.gpu_assignments[workload.assigned_gpu_id].discard(workload_id)
                
                logger.info(f"Cancelled running workload {workload_id}")
                return True
            
            # Check if it's in queue
            for queue in self.workload_queues.values():
                for i, workload in enumerate(queue):
                    if workload.id == workload_id:
                        del queue[i]
                        logger.info(f"Cancelled queued workload {workload_id}")
                        return True
            
            return False
    
    def get_workload_status(self, workload_id: str) -> Optional[Dict[str, Any]]:
        """Get workload status"""
        with self._lock:
            # Check active workloads
            if workload_id in self.active_workloads:
                workload = self.active_workloads[workload_id]
                return {
                    'id': workload.id,
                    'status': 'running',
                    'progress': workload.progress,
                    'assigned_gpu': workload.assigned_gpu_id,
                    'started_at': workload.started_at,
                    'estimated_completion': workload.started_at + workload.estimated_duration_seconds if workload.started_at else None
                }
            
            # Check queues
            for priority, queue in self.workload_queues.items():
                for workload in queue:
                    if workload.id == workload_id:
                        return {
                            'id': workload.id,
                            'status': 'queued',
                            'priority': priority.value,
                            'queue_position': list(queue).index(workload) + 1,
                            'created_at': workload.created_at
                        }
            
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        with self._lock:
            queue_lengths = {priority.value: len(queue) for priority, queue in self.workload_queues.items()}
            
            return {
                'scheduling_stats': self.scheduling_stats.copy(),
                'queue_lengths': queue_lengths,
                'active_workloads': len(self.active_workloads),
                'gpu_assignments': {gpu_id: len(workloads) for gpu_id, workloads in self.gpu_assignments.items()},
                'strategy': self.strategy.value
            }


class GPUComputeOptimizer:
    """Main GPU compute optimization coordinator"""
    
    def __init__(self, 
                 scheduling_strategy: GPUSchedulingStrategy = GPUSchedulingStrategy.LEAST_LOADED,
                 monitoring_interval: float = 1.0):
        
        self.gpu_monitor = GPUMonitor(monitoring_interval)
        self.gpu_scheduler = GPUScheduler(self.gpu_monitor, scheduling_strategy)
        
        self.optimization_callbacks: List[Callable] = []
        self._optimization_task = None
        self._running = False
        
    async def start(self):
        """Start the GPU compute optimizer"""
        await self.gpu_monitor.start()
        await self.gpu_scheduler.start()
        
        self._running = True
        self._optimization_task = asyncio.create_task(self._optimization_loop())
        
        logger.info("GPU Compute Optimizer started")
    
    async def stop(self):
        """Stop the GPU compute optimizer"""
        self._running = False
        
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
        
        await self.gpu_scheduler.stop()
        await self.gpu_monitor.stop()
        
        logger.info("GPU Compute Optimizer stopped")
    
    async def _optimization_loop(self):
        """Background optimization loop"""
        while self._running:
            try:
                await self._perform_optimization()
                await asyncio.sleep(5.0)  # Optimize every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"GPU optimization error: {e}")
                await asyncio.sleep(5.0)
    
    async def _perform_optimization(self):
        """Perform GPU optimization tasks"""
        devices = self.gpu_monitor.get_devices()
        
        # Check for overheated GPUs
        for gpu_id, device in devices.items():
            if device.temperature_celsius > 85.0:  # Critical temperature
                await self._handle_thermal_throttling(gpu_id, device)
        
        # Rebalance workloads if needed
        await self._rebalance_workloads()
        
        # Notify callbacks
        for callback in self.optimization_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback({
                        'type': 'gpu_optimization',
                        'devices': devices,
                        'scheduler_stats': self.gpu_scheduler.get_statistics()
                    })
                else:
                    callback({
                        'type': 'gpu_optimization',
                        'devices': devices,
                        'scheduler_stats': self.gpu_scheduler.get_statistics()
                    })
            except Exception as e:
                logger.error(f"GPU optimization callback error: {e}")
    
    async def _handle_thermal_throttling(self, gpu_id: int, device: GPUDevice):
        """Handle overheated GPU"""
        logger.warning(f"GPU {gpu_id} temperature critical: {device.temperature_celsius}°C")
        
        # Consider moving some workloads to other GPUs
        # This would be implemented based on specific requirements
        pass
    
    async def _rebalance_workloads(self):
        """Rebalance workloads across GPUs for optimal performance"""
        # This would implement workload migration logic
        pass
    
    def submit_workload(self, workload: GPUWorkload) -> str:
        """Submit GPU workload"""
        return self.gpu_scheduler.submit_workload(workload)
    
    def cancel_workload(self, workload_id: str) -> bool:
        """Cancel GPU workload"""
        return self.gpu_scheduler.cancel_workload(workload_id)
    
    def get_workload_status(self, workload_id: str) -> Optional[Dict[str, Any]]:
        """Get workload status"""
        return self.gpu_scheduler.get_workload_status(workload_id)
    
    def get_gpu_status(self) -> Dict[str, Any]:
        """Get comprehensive GPU status"""
        devices = self.gpu_monitor.get_devices()
        scheduler_stats = self.gpu_scheduler.get_statistics()
        
        return {
            'devices': {gpu_id: asdict(device) for gpu_id, device in devices.items()},
            'scheduler': scheduler_stats,
            'total_gpus': len(devices),
            'available_gpus': len([d for d in devices.values() if d.is_available]),
            'total_memory_mb': sum(d.memory_total_mb for d in devices.values()),
            'used_memory_mb': sum(d.memory_used_mb for d in devices.values()),
            'average_utilization': sum(d.utilization_percent for d in devices.values()) / len(devices) if devices else 0.0,
            'average_temperature': sum(d.temperature_celsius for d in devices.values()) / len(devices) if devices else 0.0
        }
    
    def add_optimization_callback(self, callback: Callable):
        """Add optimization callback"""
        self.optimization_callbacks.append(callback)
    
    def set_scheduling_strategy(self, strategy: GPUSchedulingStrategy):
        """Change scheduling strategy"""
        self.gpu_scheduler.strategy = strategy
        logger.info(f"GPU scheduling strategy changed to {strategy.value}")


# Create global instance
gpu_optimizer = GPUComputeOptimizer()


# Convenience functions for creating common workload types
def create_ai_training_workload(name: str, memory_mb: int, duration_seconds: float, 
                               priority: WorkloadPriority = WorkloadPriority.HIGH) -> GPUWorkload:
    """Create AI training workload"""
    return GPUWorkload(
        id=f"ai_training_{int(time.time())}_{name}",
        name=name,
        compute_type=ComputeType.AI_TRAINING,
        priority=priority,
        memory_required_mb=memory_mb,
        estimated_duration_seconds=duration_seconds,
        compute_units_required=0.8,
        requires_tensor_cores=True,
        preferred_gpu_types=[GPUType.NVIDIA_RTX, GPUType.NVIDIA_A100, GPUType.NVIDIA_TESLA]
    )


def create_ai_inference_workload(name: str, memory_mb: int, duration_seconds: float,
                                priority: WorkloadPriority = WorkloadPriority.NORMAL) -> GPUWorkload:
    """Create AI inference workload"""
    return GPUWorkload(
        id=f"ai_inference_{int(time.time())}_{name}",
        name=name,
        compute_type=ComputeType.AI_INFERENCE,
        priority=priority,
        memory_required_mb=memory_mb,
        estimated_duration_seconds=duration_seconds,
        compute_units_required=0.3,
        can_split=True
    )


def create_scientific_workload(name: str, memory_mb: int, duration_seconds: float,
                              requires_fp64: bool = False) -> GPUWorkload:
    """Create scientific computing workload"""
    return GPUWorkload(
        id=f"scientific_{int(time.time())}_{name}",
        name=name,
        compute_type=ComputeType.SCIENTIFIC,
        priority=WorkloadPriority.NORMAL,
        memory_required_mb=memory_mb,
        estimated_duration_seconds=duration_seconds,
        compute_units_required=0.7,
        requires_double_precision=requires_fp64
    )