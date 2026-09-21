"""
Advanced Benchmarking Engine
Comprehensive performance testing and validation system
"""

import asyncio
import time
import json
import subprocess
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path
import tempfile
import hashlib

from api.models import BenchmarkType, BenchmarkRequest, BenchmarkResult

class BenchmarkEngine:
    """Advanced benchmarking system for hardware performance testing"""
    
    def __init__(self):
        self.active_benchmarks = {}
        self.benchmark_history = {}
        self.benchmark_cache = {}
    
    async def run_benchmark(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Run a specific benchmark based on request"""
        
        benchmark_id = self._generate_benchmark_id(request)
        
        # Check cache first
        cache_key = self._get_cache_key(request)
        if cache_key in self.benchmark_cache:
            cached_result = self.benchmark_cache[cache_key]
            if self._is_cache_valid(cached_result, max_age_hours=24):
                return cached_result
        
        # Mark benchmark as active
        self.active_benchmarks[benchmark_id] = {
            'status': 'running',
            'start_time': datetime.now(),
            'request': request
        }
        
        try:
            # Route to appropriate benchmark function
            if request.benchmark_type == BenchmarkType.CPU_COMPUTE:
                result = await self._benchmark_cpu_compute(request)
            elif request.benchmark_type == BenchmarkType.GPU_COMPUTE:
                result = await self._benchmark_gpu_compute(request)
            elif request.benchmark_type == BenchmarkType.MEMORY_BANDWIDTH:
                result = await self._benchmark_memory_bandwidth(request)
            elif request.benchmark_type == BenchmarkType.STORAGE_SPEED:
                result = await self._benchmark_storage_speed(request)
            elif request.benchmark_type == BenchmarkType.NETWORK_THROUGHPUT:
                result = await self._benchmark_network_throughput(request)
            elif request.benchmark_type == BenchmarkType.THERMAL_STABILITY:
                result = await self._benchmark_thermal_stability(request)
            elif request.benchmark_type == BenchmarkType.POWER_CONSUMPTION:
                result = await self._benchmark_power_consumption(request)
            elif request.benchmark_type == BenchmarkType.ML_INFERENCE:
                result = await self._benchmark_ml_inference(request)
            elif request.benchmark_type == BenchmarkType.GAMING_PERFORMANCE:
                result = await self._benchmark_gaming_performance(request)
            else:
                raise ValueError(f"Unknown benchmark type: {request.benchmark_type}")
            
            # Cache the result
            self.benchmark_cache[cache_key] = result
            
            # Store in history
            if request.benchmark_type.value not in self.benchmark_history:
                self.benchmark_history[request.benchmark_type.value] = []
            self.benchmark_history[request.benchmark_type.value].append(result)
            
            return result
            
        finally:
            # Remove from active benchmarks
            if benchmark_id in self.active_benchmarks:
                del self.active_benchmarks[benchmark_id]
    
    async def _benchmark_cpu_compute(self, request: BenchmarkRequest) -> BenchmarkResult:
        """CPU computational performance benchmark"""
        
        intensity_multiplier = self._get_intensity_multiplier(request.intensity)
        duration = request.duration
        
        def cpu_workload():
            start_time = time.time()
            operations = 0
            
            # Prime number calculation with variable intensity
            max_num = int(50000 * intensity_multiplier)
            
            while time.time() - start_time < duration:
                primes = []
                for num in range(2, max_num):
                    is_prime = True
                    for i in range(2, int(num ** 0.5) + 1):
                        if (num % i) == 0:
                            is_prime = False
                            break
                    if is_prime:
                        primes.append(num)
                operations += 1
                
                # Adjust workload if too fast/slow
                if operations == 1:
                    elapsed = time.time() - start_time
                    if elapsed < duration / 10:  # Too fast
                        max_num = int(max_num * 1.5)
                    elif elapsed > duration / 5:  # Too slow
                        max_num = int(max_num * 0.7)
            
            return {
                'operations': operations,
                'elapsed_time': time.time() - start_time,
                'primes_found': len(primes)
            }
        
        # Run benchmark in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result_data = await loop.run_in_executor(None, cpu_workload)
        
        # Calculate score (operations per second * 100)
        ops_per_second = result_data['operations'] / result_data['elapsed_time']
        score = ops_per_second * 100
        
        # Calculate percentile (simplified)
        percentile = self._calculate_percentile(score, 'cpu_compute')
        
        return BenchmarkResult(
            benchmark_type=request.benchmark_type,
            score=score,
            percentile=percentile,
            results={
                'operations_per_second': ops_per_second,
                'total_operations': result_data['operations'],
                'duration': result_data['elapsed_time'],
                'intensity': request.intensity,
                'primes_calculated': result_data['primes_found']
            },
            system_info=await self._get_system_snapshot(),
            timestamp=datetime.now().isoformat()
        )
    
    async def _benchmark_memory_bandwidth(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Memory bandwidth benchmark"""
        
        intensity_multiplier = self._get_intensity_multiplier(request.intensity)
        duration = request.duration
        
        def memory_workload():
            start_time = time.time()
            bytes_processed = 0
            
            # Array size based on intensity
            array_size = int(1000000 * intensity_multiplier)
            
            while time.time() - start_time < duration:
                # Allocate and manipulate large arrays
                data1 = list(range(array_size))
                data2 = [x * 2 for x in data1]
                data3 = [a + b for a, b in zip(data1, data2)]
                
                bytes_processed += array_size * 3 * 8  # 3 arrays * 8 bytes per int
                
                # Clear arrays
                del data1, data2, data3
            
            elapsed_time = time.time() - start_time
            return {
                'bytes_processed': bytes_processed,
                'elapsed_time': elapsed_time,
                'bandwidth_mb_s': (bytes_processed / (1024 * 1024)) / elapsed_time
            }
        
        loop = asyncio.get_event_loop()
        result_data = await loop.run_in_executor(None, memory_workload)
        
        score = result_data['bandwidth_mb_s']
        percentile = self._calculate_percentile(score, 'memory_bandwidth')
        
        return BenchmarkResult(
            benchmark_type=request.benchmark_type,
            score=score,
            percentile=percentile,
            results={
                'bandwidth_mb_s': result_data['bandwidth_mb_s'],
                'bytes_processed': result_data['bytes_processed'],
                'duration': result_data['elapsed_time'],
                'intensity': request.intensity
            },
            system_info=await self._get_system_snapshot(),
            timestamp=datetime.now().isoformat()
        )
    
    async def _benchmark_storage_speed(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Storage I/O performance benchmark"""
        
        intensity_multiplier = self._get_intensity_multiplier(request.intensity)
        duration = request.duration
        
        def storage_workload():
            start_time = time.time()
            bytes_written = 0
            bytes_read = 0
            
            # File size based on intensity (MB)
            file_size_mb = int(10 * intensity_multiplier)
            chunk_size = 1024 * 1024  # 1MB chunks
            
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = Path(temp_file.name)
                
                try:
                    # Write test
                    write_start = time.time()
                    data_chunk = b'x' * chunk_size
                    
                    for _ in range(file_size_mb):
                        if time.time() - start_time >= duration:
                            break
                        temp_file.write(data_chunk)
                        temp_file.flush()
                        bytes_written += chunk_size
                    
                    write_time = time.time() - write_start
                    
                    # Read test
                    temp_file.seek(0)
                    read_start = time.time()
                    
                    while time.time() - start_time < duration:
                        chunk = temp_file.read(chunk_size)
                        if not chunk:
                            temp_file.seek(0)
                            continue
                        bytes_read += len(chunk)
                    
                    read_time = time.time() - read_start
                    
                    return {
                        'bytes_written': bytes_written,
                        'bytes_read': bytes_read,
                        'write_time': write_time,
                        'read_time': read_time,
                        'write_speed_mb_s': (bytes_written / (1024 * 1024)) / write_time if write_time > 0 else 0,
                        'read_speed_mb_s': (bytes_read / (1024 * 1024)) / read_time if read_time > 0 else 0
                    }
                
                finally:
                    # Clean up
                    try:
                        temp_path.unlink()
                    except:
                        pass
        
        loop = asyncio.get_event_loop()
        result_data = await loop.run_in_executor(None, storage_workload)
        
        # Score is average of read and write speeds
        score = (result_data['write_speed_mb_s'] + result_data['read_speed_mb_s']) / 2
        percentile = self._calculate_percentile(score, 'storage_speed')
        
        return BenchmarkResult(
            benchmark_type=request.benchmark_type,
            score=score,
            percentile=percentile,
            results=result_data,
            system_info=await self._get_system_snapshot(),
            timestamp=datetime.now().isoformat()
        )
    
    async def _benchmark_gpu_compute(self, request: BenchmarkRequest) -> BenchmarkResult:
        """GPU computational performance benchmark"""
        
        # Simplified GPU benchmark - in real implementation would use CUDA/OpenCL
        score = 0
        results = {
            'gpu_available': False,
            'compute_units': 0,
            'memory_bandwidth': 0,
            'note': 'GPU benchmarking requires specialized libraries (CUDA/OpenCL)'
        }
        
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                results['gpu_available'] = True
                results['gpu_name'] = gpu.name
                results['memory_total'] = gpu.memoryTotal
                results['memory_free'] = gpu.memoryFree
                
                # Simplified scoring based on memory size
                score = gpu.memoryTotal / 1024 * 100  # GB to score conversion
        except ImportError:
            pass
        
        percentile = self._calculate_percentile(score, 'gpu_compute')
        
        return BenchmarkResult(
            benchmark_type=request.benchmark_type,
            score=score,
            percentile=percentile,
            results=results,
            system_info=await self._get_system_snapshot(),
            timestamp=datetime.now().isoformat()
        )
    
    async def _benchmark_network_throughput(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Network throughput benchmark"""
        
        # Simplified network test - measures local interface capabilities
        results = {
            'test_type': 'local_interface_test',
            'note': 'Full network benchmark requires external test servers'
        }
        
        try:
            import psutil
            
            # Get network interface stats
            net_io_start = psutil.net_io_counters()
            await asyncio.sleep(1)  # Sample for 1 second
            net_io_end = psutil.net_io_counters()
            
            bytes_sent = net_io_end.bytes_sent - net_io_start.bytes_sent
            bytes_recv = net_io_end.bytes_recv - net_io_start.bytes_recv
            
            # Convert to Mbps
            mbps_sent = (bytes_sent * 8) / (1024 * 1024)
            mbps_recv = (bytes_recv * 8) / (1024 * 1024)
            
            results.update({
                'bytes_sent_per_sec': bytes_sent,
                'bytes_recv_per_sec': bytes_recv,
                'mbps_sent': mbps_sent,
                'mbps_recv': mbps_recv
            })
            
            score = max(mbps_sent, mbps_recv)
            
        except Exception as e:
            score = 0
            results['error'] = str(e)
        
        percentile = self._calculate_percentile(score, 'network_throughput')
        
        return BenchmarkResult(
            benchmark_type=request.benchmark_type,
            score=score,
            percentile=percentile,
            results=results,
            system_info=await self._get_system_snapshot(),
            timestamp=datetime.now().isoformat()
        )
    
    async def _benchmark_thermal_stability(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Thermal stability benchmark"""
        
        duration = min(request.duration, 300)  # Max 5 minutes for safety
        
        def thermal_test():
            import psutil
            
            temperatures = []
            start_time = time.time()
            
            # Light CPU load while monitoring temperatures
            while time.time() - start_time < duration:
                # Light computational load
                _ = sum(range(10000))
                
                try:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for name, entries in temps.items():
                            for entry in entries:
                                temperatures.append({
                                    'timestamp': time.time() - start_time,
                                    'sensor': name,
                                    'temperature': entry.current
                                })
                except:
                    pass
                
                time.sleep(1)
            
            return temperatures
        
        loop = asyncio.get_event_loop()
        temperature_data = await loop.run_in_executor(None, thermal_test)
        
        # Analyze temperature stability
        if temperature_data:
            temps = [t['temperature'] for t in temperature_data]
            avg_temp = sum(temps) / len(temps)
            max_temp = max(temps)
            min_temp = min(temps)
            temp_range = max_temp - min_temp
            
            # Score based on stability (lower range = higher score)
            score = max(0, 100 - temp_range)
            
            results = {
                'average_temperature': avg_temp,
                'max_temperature': max_temp,
                'min_temperature': min_temp,
                'temperature_range': temp_range,
                'sample_count': len(temperature_data),
                'duration': duration
            }
        else:
            score = 0
            results = {
                'error': 'No temperature sensors available',
                'duration': duration
            }
        
        percentile = self._calculate_percentile(score, 'thermal_stability')
        
        return BenchmarkResult(
            benchmark_type=request.benchmark_type,
            score=score,
            percentile=percentile,
            results=results,
            system_info=await self._get_system_snapshot(),
            timestamp=datetime.now().isoformat()
        )
    
    async def _benchmark_power_consumption(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Power consumption benchmark"""
        
        duration = min(request.duration, 300)  # Max 5 minutes
        
        results = {
            'test_duration': duration,
            'note': 'Power measurement requires specialized hardware sensors'
        }
        
        score = 0
        
        try:
            import psutil
            
            # Check for battery information
            battery = psutil.sensors_battery()
            if battery:
                start_percent = battery.percent
                start_time = time.time()
                
                # Light load for power measurement
                await asyncio.sleep(duration)
                
                end_battery = psutil.sensors_battery()
                if end_battery:
                    end_percent = end_battery.percent
                    power_drain_percent = start_percent - end_percent
                    
                    results.update({
                        'battery_available': True,
                        'initial_battery_percent': start_percent,
                        'final_battery_percent': end_percent,
                        'power_drain_percent': power_drain_percent,
                        'estimated_battery_life_hours': 100 / max(power_drain_percent, 0.1) if power_drain_percent > 0 else None
                    })
                    
                    # Score based on efficiency (lower drain = higher score)
                    score = max(0, 100 - power_drain_percent * 10)
            else:
                results['battery_available'] = False
                
        except Exception as e:
            results['error'] = str(e)
        
        percentile = self._calculate_percentile(score, 'power_consumption')
        
        return BenchmarkResult(
            benchmark_type=request.benchmark_type,
            score=score,
            percentile=percentile,
            results=results,
            system_info=await self._get_system_snapshot(),
            timestamp=datetime.now().isoformat()
        )
    
    async def _benchmark_ml_inference(self, request: BenchmarkRequest) -> BenchmarkResult:
        """ML inference performance benchmark"""
        
        results = {
            'test_type': 'synthetic_ml_workload',
            'note': 'Real ML benchmarking requires trained models and frameworks'
        }
        
        def ml_simulation():
            import random
            import time
            
            start_time = time.time()
            iterations = 0
            
            # Simulate matrix operations common in ML
            while time.time() - start_time < request.duration:
                # Simulate neural network forward pass
                matrix_a = [[random.random() for _ in range(100)] for _ in range(100)]
                matrix_b = [[random.random() for _ in range(100)] for _ in range(100)]
                
                # Matrix multiplication simulation
                result = [[sum(a * b for a, b in zip(row_a, col_b)) 
                          for col_b in zip(*matrix_b)] for row_a in matrix_a]
                
                iterations += 1
            
            elapsed = time.time() - start_time
            return {
                'iterations': iterations,
                'elapsed_time': elapsed,
                'operations_per_second': iterations / elapsed
            }
        
        loop = asyncio.get_event_loop()
        result_data = await loop.run_in_executor(None, ml_simulation)
        
        score = result_data['operations_per_second'] * 10  # Scale for readability
        results.update(result_data)
        
        percentile = self._calculate_percentile(score, 'ml_inference')
        
        return BenchmarkResult(
            benchmark_type=request.benchmark_type,
            score=score,
            percentile=percentile,
            results=results,
            system_info=await self._get_system_snapshot(),
            timestamp=datetime.now().isoformat()
        )
    
    async def _benchmark_gaming_performance(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Gaming performance benchmark"""
        
        results = {
            'test_type': 'synthetic_gaming_workload',
            'note': 'Real gaming benchmarks require actual games or graphics APIs'
        }
        
        def gaming_simulation():
            import time
            import math
            
            start_time = time.time()
            frames = 0
            
            # Simulate graphics computations
            while time.time() - start_time < request.duration:
                # Simulate frame rendering calculations
                for _ in range(1000):
                    # Vector operations
                    x = math.sin(frames * 0.01)
                    y = math.cos(frames * 0.01)
                    z = math.sqrt(x*x + y*y)
                    
                    # Lighting calculations
                    intensity = abs(math.sin(x + y + z))
                
                frames += 1
            
            elapsed = time.time() - start_time
            fps = frames / elapsed
            
            return {
                'total_frames': frames,
                'elapsed_time': elapsed,
                'average_fps': fps,
                'frame_time_ms': 1000 / fps if fps > 0 else 0
            }
        
        loop = asyncio.get_event_loop()
        result_data = await loop.run_in_executor(None, gaming_simulation)
        
        score = result_data['average_fps']
        results.update(result_data)
        
        percentile = self._calculate_percentile(score, 'gaming_performance')
        
        return BenchmarkResult(
            benchmark_type=request.benchmark_type,
            score=score,
            percentile=percentile,
            results=results,
            system_info=await self._get_system_snapshot(),
            timestamp=datetime.now().isoformat()
        )
    
    def _get_intensity_multiplier(self, intensity: str) -> float:
        """Get multiplier based on intensity level"""
        
        multipliers = {
            'low': 0.5,
            'medium': 1.0,
            'high': 2.0
        }
        return multipliers.get(intensity, 1.0)
    
    def _generate_benchmark_id(self, request: BenchmarkRequest) -> str:
        """Generate unique benchmark ID"""
        
        content = f"{request.benchmark_type.value}_{request.duration}_{request.intensity}_{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _get_cache_key(self, request: BenchmarkRequest) -> str:
        """Generate cache key for benchmark request"""
        
        content = f"{request.benchmark_type.value}_{request.duration}_{request.intensity}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_cache_valid(self, cached_result: BenchmarkResult, max_age_hours: int = 24) -> bool:
        """Check if cached result is still valid"""
        
        try:
            result_time = datetime.fromisoformat(cached_result.timestamp.replace('Z', '+00:00'))
            age_hours = (datetime.now() - result_time.replace(tzinfo=None)).total_seconds() / 3600
            return age_hours < max_age_hours
        except:
            return False
    
    def _calculate_percentile(self, score: float, benchmark_type: str) -> Optional[float]:
        """Calculate percentile ranking for score"""
        
        # Get historical scores for this benchmark type
        if benchmark_type not in self.benchmark_history:
            return None
        
        historical_scores = [r.score for r in self.benchmark_history[benchmark_type]]
        if not historical_scores:
            return None
        
        # Calculate percentile
        sorted_scores = sorted(historical_scores)
        position = sum(1 for s in sorted_scores if s < score)
        percentile = (position / len(sorted_scores)) * 100
        
        return min(99.9, max(0.1, percentile))
    
    async def _get_system_snapshot(self) -> Dict[str, Any]:
        """Get current system state snapshot"""
        
        try:
            import psutil
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                'timestamp': datetime.now().isoformat()
            }
        except:
            return {'timestamp': datetime.now().isoformat()}
    
    def get_benchmark_status(self, benchmark_id: str) -> Optional[Dict[str, Any]]:
        """Get status of active benchmark"""
        
        return self.active_benchmarks.get(benchmark_id)
    
    def get_benchmark_history(self, benchmark_type: Optional[str] = None) -> Dict[str, List[BenchmarkResult]]:
        """Get benchmark history"""
        
        if benchmark_type:
            return {benchmark_type: self.benchmark_history.get(benchmark_type, [])}
        return self.benchmark_history.copy()
    
    def clear_cache(self):
        """Clear benchmark cache"""
        
        self.benchmark_cache.clear()
    
    def cancel_benchmark(self, benchmark_id: str) -> bool:
        """Cancel active benchmark"""
        
        if benchmark_id in self.active_benchmarks:
            # In a real implementation, this would signal the benchmark thread to stop
            del self.active_benchmarks[benchmark_id]
            return True
        return False