"""
Hardware Profiling Engine
Advanced hardware detection, profiling, and benchmarking system
"""

import asyncio
import json
import platform
import subprocess
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import psutil
import GPUtil
from pathlib import Path

try:
    import cpuinfo
except ImportError:
    cpuinfo = None

try:
    import pynvml
    pynvml.nvmlInit()
except ImportError:
    pynvml = None

from api.models import (
    HardwareProfile, CPUInfo, MemoryInfo, GPUInfo, StorageInfo, 
    NetworkInfo, DisplayInfo, PowerInfo, SpecializedHardware,
    UsagePattern, SystemTier, BenchmarkType, BenchmarkResult
)

class HardwareProfiler:
    """Comprehensive hardware profiling engine"""
    
    def __init__(self):
        self.benchmark_cache = {}
        self.monitoring_active = False
        self.usage_history = []
        
    async def create_full_profile(self, include_benchmarks: bool = False) -> HardwareProfile:
        """Create a comprehensive hardware profile"""
        
        profile_id = f"profile_{int(time.time())}"
        
        # Gather all hardware information
        cpu_info = await self._get_cpu_info()
        memory_info = await self._get_memory_info()
        gpu_info = await self._get_gpu_info()
        storage_info = await self._get_storage_info()
        network_info = await self._get_network_info()
        display_info = await self._get_display_info()
        power_info = await self._get_power_info()
        specialized_hw = await self._get_specialized_hardware()
        
        # Determine system tier
        system_tier = self._classify_system_tier(cpu_info, memory_info, gpu_info)
        
        # Analyze usage patterns if monitoring has been active
        usage_pattern = await self._analyze_usage_patterns()
        
        # Run benchmarks if requested
        performance_scores = {}
        if include_benchmarks:
            performance_scores = await self._run_benchmark_suite()
        
        # Generate thermal profile
        thermal_profile = await self._get_thermal_profile()
        
        # Create profile
        profile = HardwareProfile(
            profile_id=profile_id,
            system_tier=system_tier,
            cpu=cpu_info,
            memory=memory_info,
            gpu=gpu_info,
            storage=storage_info,
            network=network_info,
            display=display_info,
            power=power_info,
            specialized=specialized_hw,
            usage_pattern=usage_pattern,
            thermal_profile=thermal_profile,
            performance_scores=performance_scores,
            summary=self._generate_profile_summary(cpu_info, memory_info, gpu_info, system_tier),
            recommendations=self._generate_recommendations(cpu_info, memory_info, gpu_info, system_tier)
        )
        
        return profile
    
    async def _get_cpu_info(self) -> CPUInfo:
        """Get detailed CPU information"""
        
        # Basic CPU info from psutil
        cpu_freq = psutil.cpu_freq()
        cpu_count_physical = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count(logical=True)
        
        # Try to get detailed CPU info
        cpu_name = "Unknown CPU"
        cpu_manufacturer = "Unknown"
        architecture = platform.machine()
        instruction_sets = []
        
        if cpuinfo:
            cpu_details = cpuinfo.get_cpu_info()
            cpu_name = cpu_details.get('brand_raw', cpu_name)
            cpu_manufacturer = cpu_details.get('vendor_id_raw', cpu_manufacturer)
            instruction_sets = cpu_details.get('flags', [])
        
        # Get cache information (Linux-specific)
        cache_l1_kb = None
        cache_l2_kb = None
        cache_l3_mb = None
        
        try:
            if platform.system() == "Linux":
                # Try to get cache info from /proc/cpuinfo
                with open("/proc/cpuinfo", "r") as f:
                    cpuinfo_data = f.read()
                    # Parse cache sizes (this is a simplified approach)
                    if "cache size" in cpuinfo_data:
                        lines = cpuinfo_data.split('\n')
                        for line in lines:
                            if "cache size" in line:
                                cache_size = line.split(':')[1].strip()
                                if 'KB' in cache_size:
                                    cache_l3_mb = int(cache_size.replace(' KB', '')) / 1024
        except Exception:
            pass
        
        # Estimate TDP based on CPU model (rough estimation)
        tdp_watts = self._estimate_cpu_tdp(cpu_name)
        
        return CPUInfo(
            name=cpu_name,
            manufacturer=cpu_manufacturer,
            architecture=architecture,
            cores=cpu_count_physical or 1,
            threads=cpu_count_logical or 1,
            base_frequency_ghz=cpu_freq.current / 1000 if cpu_freq else 2.0,
            max_frequency_ghz=cpu_freq.max / 1000 if cpu_freq and cpu_freq.max else None,
            cache_l1_kb=cache_l1_kb,
            cache_l2_kb=cache_l2_kb,
            cache_l3_mb=cache_l3_mb,
            instruction_sets=instruction_sets[:20],  # Limit to avoid huge lists
            tdp_watts=tdp_watts
        )
    
    async def _get_memory_info(self) -> MemoryInfo:
        """Get detailed memory information"""
        
        memory = psutil.virtual_memory()
        
        # Try to get memory type and speed (Linux-specific)
        memory_type = None
        speed_mhz = None
        channels = None
        
        try:
            if platform.system() == "Linux":
                # Try dmidecode for detailed memory info
                result = subprocess.run(
                    ["dmidecode", "-t", "memory"], 
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    output = result.stdout
                    if "DDR" in output:
                        for line in output.split('\n'):
                            if "Type:" in line and "DDR" in line:
                                memory_type = line.split(':')[1].strip()
                                break
                    if "Speed:" in output:
                        for line in output.split('\n'):
                            if "Speed:" in line and "MHz" in line:
                                try:
                                    speed_str = line.split(':')[1].strip()
                                    speed_mhz = int(speed_str.split()[0])
                                    break
                                except (ValueError, IndexError):
                                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
        
        # Estimate bandwidth
        bandwidth_gb_s = None
        if speed_mhz and channels:
            # Rough calculation: channels * speed * 8 bytes / 1000
            bandwidth_gb_s = channels * speed_mhz * 8 / 1000
        
        return MemoryInfo(
            total_gb=memory.total / (1024**3),
            available_gb=memory.available / (1024**3),
            used_gb=memory.used / (1024**3),
            memory_type=memory_type,
            speed_mhz=speed_mhz,
            channels=channels,
            bandwidth_gb_s=bandwidth_gb_s
        )
    
    async def _get_gpu_info(self) -> Optional[GPUInfo]:
        """Get GPU information"""
        
        try:
            # Try NVIDIA GPUs first
            if pynvml:
                device_count = pynvml.nvmlDeviceGetCount()
                if device_count > 0:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    power_limit = None
                    try:
                        power_limit = pynvml.nvmlDeviceGetPowerManagementLimitConstraints(handle)[1] // 1000
                    except:
                        pass
                    
                    return GPUInfo(
                        name=name,
                        manufacturer="NVIDIA",
                        memory_gb=memory_info.total / (1024**3),
                        memory_type="GDDR6",  # Assumption for modern cards
                        power_draw_watts=power_limit
                    )
            
            # Try GPUtil as fallback
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return GPUInfo(
                    name=gpu.name,
                    manufacturer="Unknown",
                    memory_gb=gpu.memoryTotal / 1024,  # GPUtil returns in MB
                    memory_type="Unknown"
                )
                
        except Exception:
            pass
        
        # Check for integrated graphics
        try:
            if platform.system() == "Linux":
                result = subprocess.run(
                    ["lspci", "-nn"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if "VGA" in line or "Display" in line:
                            if "Intel" in line:
                                return GPUInfo(
                                    name=line.split(':')[-1].strip(),
                                    manufacturer="Intel",
                                    memory_gb=None
                                )
                            elif "AMD" in line or "ATI" in line:
                                return GPUInfo(
                                    name=line.split(':')[-1].strip(),
                                    manufacturer="AMD",
                                    memory_gb=None
                                )
        except Exception:
            pass
        
        return None
    
    async def _get_storage_info(self) -> StorageInfo:
        """Get storage information"""
        
        drives = []
        total_capacity = 0
        available_capacity = 0
        
        # Get disk usage for all mount points
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                drive_info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": usage.total / (1024**3),
                    "free_gb": usage.free / (1024**3),
                    "used_gb": usage.used / (1024**3)
                }
                drives.append(drive_info)
                
                if partition.mountpoint == "/" or partition.mountpoint == "C:\\":
                    total_capacity = usage.total / (1024**3)
                    available_capacity = usage.free / (1024**3)
                    
            except PermissionError:
                continue
        
        # Determine primary storage type
        primary_type = "Unknown"
        read_speed_mb_s = None
        write_speed_mb_s = None
        
        try:
            if platform.system() == "Linux":
                # Check if primary drive is SSD
                result = subprocess.run(
                    ["lsblk", "-d", "-o", "name,rota"], 
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 2:
                            rotation = parts[1]
                            if rotation == "0":
                                primary_type = "SSD"
                                break
                            elif rotation == "1":
                                primary_type = "HDD"
                                break
        except Exception:
            pass
        
        return StorageInfo(
            drives=drives,
            total_capacity_gb=total_capacity,
            available_capacity_gb=available_capacity,
            primary_type=primary_type,
            read_speed_mb_s=read_speed_mb_s,
            write_speed_mb_s=write_speed_mb_s
        )
    
    async def _get_network_info(self) -> NetworkInfo:
        """Get network information"""
        
        interfaces = []
        max_bandwidth = 0
        
        # Get network interface information
        net_if_stats = psutil.net_if_stats()
        net_if_addrs = psutil.net_if_addrs()
        
        for interface_name, stats in net_if_stats.items():
            if stats.isup and interface_name != "lo":  # Skip loopback
                interface_info = {
                    "name": interface_name,
                    "speed_mbps": stats.speed if stats.speed > 0 else None,
                    "mtu": stats.mtu,
                    "is_up": stats.isup
                }
                
                # Add addresses if available
                if interface_name in net_if_addrs:
                    addresses = []
                    for addr in net_if_addrs[interface_name]:
                        if addr.family.name in ['AF_INET', 'AF_INET6']:
                            addresses.append(addr.address)
                    interface_info["addresses"] = addresses
                
                interfaces.append(interface_info)
                
                if stats.speed > max_bandwidth:
                    max_bandwidth = stats.speed
        
        # Determine connection type
        connection_type = "Unknown"
        if any("eth" in iface["name"].lower() for iface in interfaces):
            connection_type = "Ethernet"
        elif any("wlan" in iface["name"].lower() or "wifi" in iface["name"].lower() for iface in interfaces):
            connection_type = "WiFi"
        
        return NetworkInfo(
            interfaces=interfaces,
            max_bandwidth_mbps=max_bandwidth,
            connection_type=connection_type
        )
    
    async def _get_display_info(self) -> Optional[DisplayInfo]:
        """Get display information"""
        
        displays = []
        primary_resolution = "Unknown"
        primary_refresh_rate = 60
        total_pixels = 0
        
        try:
            if platform.system() == "Linux":
                # Try xrandr for X11 systems
                result = subprocess.run(
                    ["xrandr", "--query"], 
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if " connected" in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                resolution_part = parts[2]
                                if 'x' in resolution_part:
                                    resolution = resolution_part.split('+')[0]
                                    if primary_resolution == "Unknown":
                                        primary_resolution = resolution
                                    
                                    # Calculate pixels
                                    try:
                                        width, height = map(int, resolution.split('x'))
                                        total_pixels += width * height
                                        displays.append({
                                            "resolution": resolution,
                                            "connected": True
                                        })
                                    except ValueError:
                                        pass
        except Exception:
            pass
        
        # Fallback values if detection failed
        if primary_resolution == "Unknown":
            primary_resolution = "1920x1080"
            total_pixels = 1920 * 1080
        
        if not displays:
            displays = [{"resolution": primary_resolution, "connected": True}]
        
        return DisplayInfo(
            displays=displays,
            primary_resolution=primary_resolution,
            primary_refresh_rate_hz=primary_refresh_rate,
            total_pixels=total_pixels,
            hdr_support=False  # Conservative default
        )
    
    async def _get_power_info(self) -> Optional[PowerInfo]:
        """Get power and thermal information"""
        
        battery_present = False
        battery_capacity_wh = None
        battery_health_percent = None
        current_power_draw = None
        thermal_throttling = False
        max_operating_temp = None
        
        # Check for battery
        try:
            battery = psutil.sensors_battery()
            if battery:
                battery_present = True
                battery_health_percent = battery.percent
                # Rough capacity estimation for common laptop batteries
                battery_capacity_wh = 50.0  # Default assumption
        except Exception:
            pass
        
        # Check thermal sensors
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                max_temp = 0
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > max_temp:
                            max_temp = entry.current
                        if entry.current > 85:  # Typical throttling threshold
                            thermal_throttling = True
                        if entry.high:
                            max_operating_temp = entry.high
                
        except Exception:
            pass
        
        return PowerInfo(
            battery_present=battery_present,
            battery_capacity_wh=battery_capacity_wh,
            battery_health_percent=battery_health_percent,
            current_power_draw_watts=current_power_draw,
            thermal_throttling=thermal_throttling,
            max_operating_temp_c=max_operating_temp
        )
    
    async def _get_specialized_hardware(self) -> Optional[SpecializedHardware]:
        """Detect specialized hardware"""
        
        npu_present = False
        tpu_present = False
        fpga_present = False
        quantum_accelerator = False
        custom_accelerators = []
        
        try:
            if platform.system() == "Linux":
                # Check for various accelerators
                result = subprocess.run(
                    ["lspci", "-nn"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    output = result.stdout.lower()
                    
                    # Check for known accelerator patterns
                    if "neural" in output or "npu" in output:
                        npu_present = True
                    if "tensor" in output or "tpu" in output:
                        tpu_present = True
                    if "fpga" in output:
                        fpga_present = True
                    if "quantum" in output:
                        quantum_accelerator = True
        except Exception:
            pass
        
        return SpecializedHardware(
            npu_present=npu_present,
            tpu_present=tpu_present,
            fpga_present=fpga_present,
            quantum_accelerator=quantum_accelerator,
            custom_accelerators=custom_accelerators
        )
    
    async def _analyze_usage_patterns(self) -> Optional[UsagePattern]:
        """Analyze system usage patterns"""
        
        if not self.usage_history:
            return None
        
        # Calculate averages from history
        avg_cpu = sum(entry.get("cpu_percent", 0) for entry in self.usage_history) / len(self.usage_history)
        avg_memory = sum(entry.get("memory_percent", 0) for entry in self.usage_history) / len(self.usage_history)
        
        # Determine usage frequency
        usage_frequency = "light"
        if avg_cpu > 70 or avg_memory > 80:
            usage_frequency = "heavy"
        elif avg_cpu > 40 or avg_memory > 60:
            usage_frequency = "moderate"
        
        return UsagePattern(
            peak_hours=[9, 10, 11, 14, 15, 16, 20, 21],  # Default assumption
            average_cpu_utilization=avg_cpu,
            average_memory_utilization=avg_memory,
            typical_workloads=["general", "web_browsing"],
            usage_frequency=usage_frequency,
            preferred_performance_mode="balanced"
        )
    
    def _classify_system_tier(self, cpu: CPUInfo, memory: MemoryInfo, gpu: Optional[GPUInfo]) -> SystemTier:
        """Classify system into performance tiers"""
        
        score = 0
        
        # CPU scoring
        if cpu.cores >= 8:
            score += 3
        elif cpu.cores >= 4:
            score += 2
        else:
            score += 1
        
        if cpu.base_frequency_ghz >= 3.0:
            score += 2
        elif cpu.base_frequency_ghz >= 2.5:
            score += 1
        
        # Memory scoring
        if memory.total_gb >= 32:
            score += 3
        elif memory.total_gb >= 16:
            score += 2
        elif memory.total_gb >= 8:
            score += 1
        
        # GPU scoring
        if gpu:
            if gpu.memory_gb and gpu.memory_gb >= 8:
                score += 3
            elif gpu.memory_gb and gpu.memory_gb >= 4:
                score += 2
            elif gpu.memory_gb:
                score += 1
        
        # Classify based on score
        if score >= 10:
            return SystemTier.HIGH_END
        elif score >= 7:
            return SystemTier.STANDARD
        elif score >= 4:
            return SystemTier.BASIC
        else:
            return SystemTier.EMBEDDED
    
    async def _run_benchmark_suite(self) -> Dict[str, float]:
        """Run comprehensive benchmark suite"""
        
        results = {}
        
        # CPU benchmark
        results["cpu_score"] = await self._benchmark_cpu()
        
        # Memory benchmark
        results["memory_score"] = await self._benchmark_memory()
        
        # Storage benchmark
        results["storage_score"] = await self._benchmark_storage()
        
        # GPU benchmark (if available)
        gpu_score = await self._benchmark_gpu()
        if gpu_score:
            results["gpu_score"] = gpu_score
        
        return results
    
    async def _benchmark_cpu(self) -> float:
        """CPU benchmark using simple computation"""
        
        def cpu_intensive_task():
            start_time = time.time()
            # Prime number calculation
            primes = []
            for num in range(2, 10000):
                for i in range(2, int(num ** 0.5) + 1):
                    if (num % i) == 0:
                        break
                else:
                    primes.append(num)
            return time.time() - start_time
        
        # Run CPU benchmark
        loop = asyncio.get_event_loop()
        elapsed_time = await loop.run_in_executor(None, cpu_intensive_task)
        
        # Score is inverse of time (faster = higher score)
        return min(1000.0, 100.0 / elapsed_time)
    
    async def _benchmark_memory(self) -> float:
        """Memory bandwidth benchmark"""
        
        def memory_test():
            start_time = time.time()
            # Allocate and manipulate large array
            size = 1000000
            data = list(range(size))
            data.sort(reverse=True)
            data.reverse()
            return time.time() - start_time
        
        loop = asyncio.get_event_loop()
        elapsed_time = await loop.run_in_executor(None, memory_test)
        
        return min(1000.0, 50.0 / elapsed_time)
    
    async def _benchmark_storage(self) -> float:
        """Storage speed benchmark"""
        
        def storage_test():
            start_time = time.time()
            test_file = Path("/tmp/benchmark_test.tmp")
            
            try:
                # Write test
                data = b"x" * (1024 * 1024)  # 1MB
                with open(test_file, "wb") as f:
                    for _ in range(100):
                        f.write(data)
                        f.flush()
                
                # Read test
                with open(test_file, "rb") as f:
                    while f.read(1024 * 1024):
                        pass
                
                test_file.unlink()
                return time.time() - start_time
                
            except Exception:
                if test_file.exists():
                    test_file.unlink()
                return 10.0  # Default high time
        
        loop = asyncio.get_event_loop()
        elapsed_time = await loop.run_in_executor(None, storage_test)
        
        return min(1000.0, 200.0 / elapsed_time)
    
    async def _benchmark_gpu(self) -> Optional[float]:
        """GPU benchmark if available"""
        
        # Simple GPU detection score
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                # Score based on memory and utilization capability
                memory_score = (gpu.memoryTotal / 1024) * 10  # GB to score
                return min(1000.0, memory_score)
        except Exception:
            pass
        
        return None
    
    async def _get_thermal_profile(self) -> Dict[str, float]:
        """Get thermal characteristics"""
        
        thermal_profile = {}
        
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        thermal_profile[f"{name}_current"] = entries[0].current
                        if entries[0].high:
                            thermal_profile[f"{name}_max"] = entries[0].high
        except Exception:
            pass
        
        return thermal_profile
    
    def _estimate_cpu_tdp(self, cpu_name: str) -> Optional[int]:
        """Estimate CPU TDP based on model name"""
        
        cpu_lower = cpu_name.lower()
        
        # Basic TDP estimates based on common patterns
        if "mobile" in cpu_lower or "m1" in cpu_lower or "m2" in cpu_lower:
            return 15
        elif "ultra" in cpu_lower or "low power" in cpu_lower:
            return 25
        elif "i3" in cpu_lower or "ryzen 3" in cpu_lower:
            return 65
        elif "i5" in cpu_lower or "ryzen 5" in cpu_lower:
            return 95
        elif "i7" in cpu_lower or "ryzen 7" in cpu_lower:
            return 125
        elif "i9" in cpu_lower or "ryzen 9" in cpu_lower:
            return 165
        elif "xeon" in cpu_lower or "threadripper" in cpu_lower:
            return 280
        else:
            return 95  # Default assumption
    
    def _generate_profile_summary(self, cpu: CPUInfo, memory: MemoryInfo, gpu: Optional[GPUInfo], tier: SystemTier) -> Dict[str, Any]:
        """Generate profile summary"""
        
        return {
            "system_tier": tier.value,
            "cpu_summary": f"{cpu.cores}C/{cpu.threads}T {cpu.name}",
            "memory_summary": f"{memory.total_gb:.1f}GB RAM",
            "gpu_summary": gpu.name if gpu else "Integrated/None",
            "recommended_use_cases": self._get_recommended_use_cases(tier),
            "performance_class": self._get_performance_class(tier)
        }
    
    def _generate_recommendations(self, cpu: CPUInfo, memory: MemoryInfo, gpu: Optional[GPUInfo], tier: SystemTier) -> List[str]:
        """Generate hardware recommendations"""
        
        recommendations = []
        
        if memory.total_gb < 8:
            recommendations.append("Consider upgrading RAM to 16GB for better performance")
        
        if not gpu or (gpu.memory_gb and gpu.memory_gb < 2):
            recommendations.append("Dedicated GPU recommended for graphics-intensive tasks")
        
        if cpu.cores < 4:
            recommendations.append("Multi-core CPU upgrade recommended for multitasking")
        
        if tier == SystemTier.EMBEDDED:
            recommendations.append("System optimized for minimal resource usage")
        elif tier == SystemTier.BASIC:
            recommendations.append("Suitable for basic productivity tasks")
        elif tier == SystemTier.STANDARD:
            recommendations.append("Good balance for most applications")
        elif tier == SystemTier.HIGH_END:
            recommendations.append("Excellent for demanding applications and multitasking")
        
        return recommendations
    
    def _get_recommended_use_cases(self, tier: SystemTier) -> List[str]:
        """Get recommended use cases for system tier"""
        
        use_cases = {
            SystemTier.EMBEDDED: ["IoT applications", "Basic sensors", "Minimal interfaces"],
            SystemTier.BASIC: ["Web browsing", "Office tasks", "Light media"],
            SystemTier.STANDARD: ["Development", "Content creation", "Gaming", "Productivity"],
            SystemTier.HIGH_END: ["Professional workloads", "Gaming", "ML training", "Content creation"],
            SystemTier.ENTERPRISE: ["Server workloads", "Data processing", "Virtualization"],
            SystemTier.SPECIALIZED: ["AI/ML", "Scientific computing", "High-performance computing"]
        }
        
        return use_cases.get(tier, ["General computing"])
    
    def _get_performance_class(self, tier: SystemTier) -> str:
        """Get performance class description"""
        
        classes = {
            SystemTier.EMBEDDED: "Minimal",
            SystemTier.BASIC: "Entry-level",
            SystemTier.STANDARD: "Mainstream",
            SystemTier.HIGH_END: "High-performance",
            SystemTier.ENTERPRISE: "Professional",
            SystemTier.SPECIALIZED: "Specialized"
        }
        
        return classes.get(tier, "Unknown")
    
    def start_monitoring(self):
        """Start continuous system monitoring"""
        
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        
        self.monitoring_active = False
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        
        while self.monitoring_active:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3)
                }
                
                self.usage_history.append(entry)
                
                # Keep only last 1000 entries
                if len(self.usage_history) > 1000:
                    self.usage_history = self.usage_history[-1000:]
                
                time.sleep(60)  # Monitor every minute
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(60)