#!/usr/bin/env python3
"""
ActiveLog Edge Power Management Agent
Implements power-efficient processing modes for edge devices
"""

import asyncio
import json
import logging
import os
import psutil
import signal
import subprocess
import time
import threading
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

class PowerMode(Enum):
    """Power management modes"""
    FULL_POWER = "full_power"
    BALANCED = "balanced"  
    POWER_SAVER = "power_saver"
    ULTRA_SAVER = "ultra_saver"
    ADAPTIVE = "adaptive"

class ProcessingPriority(Enum):
    """Processing priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    DEFERRED = "deferred"

@dataclass
class PowerPolicy:
    """Power management policy configuration"""
    mode: PowerMode
    cpu_governor: str
    cpu_max_freq: Optional[int] = None
    gpu_power_limit: Optional[int] = None
    idle_timeout: int = 300  # seconds
    suspend_threshold: float = 0.05  # CPU usage threshold
    wake_triggers: List[str] = None
    processing_limits: Dict[str, int] = None

    def __post_init__(self):
        if self.wake_triggers is None:
            self.wake_triggers = ["network", "motion", "audio"]
        if self.processing_limits is None:
            self.processing_limits = {"batch_size": 1, "concurrent_tasks": 2}

class TaskScheduler:
    """Intelligent task scheduling for power efficiency"""
    
    def __init__(self, power_agent):
        self.power_agent = power_agent
        self.task_queue = asyncio.PriorityQueue()
        self.running_tasks = {}
        self.deferred_tasks = []
        self.logger = logging.getLogger(__name__)
        
    async def schedule_task(self, task_id: str, task_func: Callable, 
                          priority: ProcessingPriority, 
                          estimated_duration: int = 60,
                          power_requirement: int = 50):
        """Schedule a task with power-aware priority"""
        
        current_mode = self.power_agent.current_mode
        
        # Adjust priority based on power mode
        if current_mode in [PowerMode.POWER_SAVER, PowerMode.ULTRA_SAVER]:
            if priority in [ProcessingPriority.NORMAL, ProcessingPriority.LOW]:
                priority = ProcessingPriority.DEFERRED
        
        task_info = {
            "id": task_id,
            "func": task_func,
            "priority": priority,
            "duration": estimated_duration,
            "power_req": power_requirement,
            "queued_at": time.time()
        }
        
        if priority == ProcessingPriority.DEFERRED:
            self.deferred_tasks.append(task_info)
            self.logger.info(f"Task {task_id} deferred due to power constraints")
        else:
            # Convert priority to numeric value for queue (lower = higher priority)
            priority_value = {
                ProcessingPriority.CRITICAL: 0,
                ProcessingPriority.HIGH: 1,
                ProcessingPriority.NORMAL: 2,
                ProcessingPriority.LOW: 3
            }[priority]
            
            await self.task_queue.put((priority_value, time.time(), task_info))
            self.logger.info(f"Task {task_id} queued with priority {priority.value}")
    
    async def process_tasks(self):
        """Main task processing loop"""
        while True:
            try:
                # Check if we should process deferred tasks
                if self.power_agent.current_mode in [PowerMode.FULL_POWER, PowerMode.BALANCED]:
                    await self._process_deferred_tasks()
                
                # Get next task from queue
                if not self.task_queue.empty():
                    _, _, task_info = await self.task_queue.get()
                    
                    # Check power constraints
                    if self._can_execute_task(task_info):
                        await self._execute_task(task_info)
                    else:
                        # Re-queue with lower priority or defer
                        if task_info["priority"] != ProcessingPriority.DEFERRED:
                            task_info["priority"] = ProcessingPriority.DEFERRED
                            self.deferred_tasks.append(task_info)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Task processing error: {e}")
                await asyncio.sleep(1)
    
    def _can_execute_task(self, task_info: Dict) -> bool:
        """Check if task can be executed given current power constraints"""
        current_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        
        # Get power policy limits
        policy = self.power_agent.current_policy
        max_concurrent = policy.processing_limits.get("concurrent_tasks", 2)
        
        # Check concurrent task limit
        if len(self.running_tasks) >= max_concurrent:
            return False
        
        # Check resource usage
        if current_usage > 80 and task_info["power_req"] > 30:
            return False
            
        if memory_usage > 90:
            return False
        
        return True
    
    async def _execute_task(self, task_info: Dict):
        """Execute a task with monitoring"""
        task_id = task_info["id"]
        
        try:
            self.running_tasks[task_id] = {
                "started_at": time.time(),
                "info": task_info
            }
            
            self.logger.info(f"Executing task {task_id}")
            
            # Execute the task function
            result = await task_info["func"]()
            
            self.logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Task {task_id} failed: {e}")
            
        finally:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _process_deferred_tasks(self):
        """Process deferred tasks when power allows"""
        if not self.deferred_tasks:
            return
        
        # Sort deferred tasks by original priority
        self.deferred_tasks.sort(key=lambda x: x["queued_at"])
        
        tasks_to_process = []
        for task in self.deferred_tasks[:]:
            if len(tasks_to_process) >= 3:  # Limit batch processing
                break
                
            if self._can_execute_task(task):
                tasks_to_process.append(task)
                self.deferred_tasks.remove(task)
        
        # Execute deferred tasks
        for task in tasks_to_process:
            await self.task_queue.put((2, time.time(), task))  # Normal priority

class ThermalManager:
    """Thermal management and throttling"""
    
    def __init__(self):
        self.thermal_zones = self._discover_thermal_zones()
        self.temperature_history = {}
        self.throttle_active = False
        self.logger = logging.getLogger(__name__)
    
    def _discover_thermal_zones(self) -> Dict[str, str]:
        """Discover available thermal sensors"""
        zones = {}
        thermal_path = Path("/sys/class/thermal")
        
        if not thermal_path.exists():
            return zones
        
        for zone_dir in thermal_path.glob("thermal_zone*"):
            zone_num = zone_dir.name.replace("thermal_zone", "")
            type_file = zone_dir / "type"
            
            if type_file.exists():
                try:
                    zone_type = type_file.read_text().strip()
                    zones[zone_type] = str(zone_dir / "temp")
                except:
                    zones[f"zone_{zone_num}"] = str(zone_dir / "temp")
        
        return zones
    
    def get_temperatures(self) -> Dict[str, float]:
        """Get current temperatures from all sensors"""
        temps = {}
        
        for zone_name, temp_file in self.thermal_zones.items():
            try:
                with open(temp_file, 'r') as f:
                    temp_millicelsius = int(f.read().strip())
                    temps[zone_name] = temp_millicelsius / 1000.0
            except Exception as e:
                self.logger.debug(f"Failed to read temperature from {zone_name}: {e}")
        
        return temps
    
    def update_history(self, temps: Dict[str, float]):
        """Update temperature history for trend analysis"""
        timestamp = time.time()
        
        for zone, temp in temps.items():
            if zone not in self.temperature_history:
                self.temperature_history[zone] = []
            
            self.temperature_history[zone].append((timestamp, temp))
            
            # Keep only last hour of data
            cutoff = timestamp - 3600
            self.temperature_history[zone] = [
                (t, temp) for t, temp in self.temperature_history[zone] 
                if t > cutoff
            ]
    
    def check_thermal_throttling(self, critical_temp: float = 80.0) -> bool:
        """Check if thermal throttling should be activated"""
        temps = self.get_temperatures()
        self.update_history(temps)
        
        if not temps:
            return False
        
        max_temp = max(temps.values())
        
        # Activate throttling if any sensor exceeds critical temperature
        if max_temp > critical_temp:
            if not self.throttle_active:
                self.logger.warning(f"Thermal throttling activated: {max_temp:.1f}°C")
                self.throttle_active = True
            return True
        
        # Deactivate throttling with hysteresis
        elif max_temp < (critical_temp - 5) and self.throttle_active:
            self.logger.info(f"Thermal throttling deactivated: {max_temp:.1f}°C")
            self.throttle_active = False
            return False
        
        return self.throttle_active

class PowerAgent:
    """Main power management agent"""
    
    def __init__(self, config_path: str = "/etc/activelog/power.conf"):
        self.config_path = config_path
        self.config = self._load_config()
        self.current_mode = PowerMode.BALANCED
        self.current_policy = None
        self.running = False
        
        # Initialize components
        self.logger = self._setup_logging()
        self.task_scheduler = TaskScheduler(self)
        self.thermal_manager = ThermalManager()
        
        # Power monitoring
        self.power_history = []
        self.usage_monitor = None
        self.last_activity_time = time.time()
        
        # Define power policies
        self.policies = {
            PowerMode.FULL_POWER: PowerPolicy(
                mode=PowerMode.FULL_POWER,
                cpu_governor="performance",
                cpu_max_freq=None,
                gpu_power_limit=None,
                idle_timeout=600,
                suspend_threshold=0.1,
                processing_limits={"batch_size": 10, "concurrent_tasks": 8}
            ),
            PowerMode.BALANCED: PowerPolicy(
                mode=PowerMode.BALANCED,
                cpu_governor="schedutil",
                cpu_max_freq=None,
                gpu_power_limit=80,
                idle_timeout=300,
                suspend_threshold=0.05,
                processing_limits={"batch_size": 5, "concurrent_tasks": 4}
            ),
            PowerMode.POWER_SAVER: PowerPolicy(
                mode=PowerMode.POWER_SAVER,
                cpu_governor="powersave",
                cpu_max_freq=50,  # Percentage of max frequency
                gpu_power_limit=60,
                idle_timeout=180,
                suspend_threshold=0.02,
                processing_limits={"batch_size": 2, "concurrent_tasks": 2}
            ),
            PowerMode.ULTRA_SAVER: PowerPolicy(
                mode=PowerMode.ULTRA_SAVER,
                cpu_governor="powersave",
                cpu_max_freq=30,
                gpu_power_limit=40,
                idle_timeout=60,
                suspend_threshold=0.01,
                processing_limits={"batch_size": 1, "concurrent_tasks": 1}
            )
        }
        
        self.current_policy = self.policies[self.current_mode]
        
        self.logger.info("PowerAgent initialized")
    
    def _load_config(self) -> Dict:
        """Load configuration"""
        default_config = {
            "power": {
                "default_mode": "balanced",
                "adaptive_enabled": True,
                "thermal_throttling": True,
                "thermal_threshold": 75.0,
                "battery_thresholds": {
                    "critical": 10,
                    "low": 25,
                    "normal": 50
                }
            },
            "monitoring": {
                "interval": 30,
                "history_size": 1000,
                "log_level": "INFO"
            },
            "scheduling": {
                "enable_deferred_processing": True,
                "max_deferred_tasks": 100,
                "batch_processing_window": 300
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    self._merge_config(default_config, loaded_config)
        except Exception as e:
            print(f"Error loading config: {e}")
        
        return default_config
    
    def _merge_config(self, default: Dict, loaded: Dict):
        """Recursively merge configurations"""
        for key, value in loaded.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_config(default[key], value)
            else:
                default[key] = value
    
    def _setup_logging(self):
        """Setup logging"""
        log_level = getattr(logging, self.config["monitoring"]["log_level"])
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("/var/log/activelog/power.log"),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    async def start(self):
        """Start the power management agent"""
        self.running = True
        self.logger.info("Starting ActiveLog Power Management Agent")
        
        # Apply initial power mode
        await self.apply_power_mode(self.current_mode)
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._monitoring_loop()),
            asyncio.create_task(self._adaptive_mode_loop()),
            asyncio.create_task(self.task_scheduler.process_tasks()),
            asyncio.create_task(self._idle_management_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the power management agent"""
        self.running = False
        self.logger.info("Power Management Agent stopped")
    
    async def set_power_mode(self, mode: PowerMode):
        """Set power management mode"""
        if mode not in self.policies:
            raise ValueError(f"Unknown power mode: {mode}")
        
        old_mode = self.current_mode
        self.current_mode = mode
        self.current_policy = self.policies[mode]
        
        await self.apply_power_mode(mode)
        
        self.logger.info(f"Power mode changed from {old_mode.value} to {mode.value}")
    
    async def apply_power_mode(self, mode: PowerMode):
        """Apply power management settings"""
        policy = self.policies[mode]
        
        try:
            # Apply CPU governor
            await self._set_cpu_governor(policy.cpu_governor)
            
            # Apply CPU frequency limits
            if policy.cpu_max_freq:
                await self._set_cpu_frequency_limit(policy.cpu_max_freq)
            
            # Apply GPU power limits (NVIDIA only)
            if policy.gpu_power_limit:
                await self._set_gpu_power_limit(policy.gpu_power_limit)
            
            self.logger.info(f"Applied power policy for mode: {mode.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to apply power mode {mode.value}: {e}")
    
    async def _set_cpu_governor(self, governor: str):
        """Set CPU governor"""
        try:
            cpu_dirs = Path("/sys/devices/system/cpu").glob("cpu[0-9]*")
            for cpu_dir in cpu_dirs:
                governor_file = cpu_dir / "cpufreq" / "scaling_governor"
                if governor_file.exists():
                    with open(governor_file, 'w') as f:
                        f.write(governor)
            
            self.logger.debug(f"Set CPU governor to: {governor}")
        except Exception as e:
            self.logger.warning(f"Failed to set CPU governor: {e}")
    
    async def _set_cpu_frequency_limit(self, max_percent: int):
        """Set CPU maximum frequency as percentage of max"""
        try:
            cpu_dirs = Path("/sys/devices/system/cpu").glob("cpu[0-9]*")
            for cpu_dir in cpu_dirs:
                max_freq_file = cpu_dir / "cpufreq" / "cpuinfo_max_freq"
                scaling_max_file = cpu_dir / "cpufreq" / "scaling_max_freq"
                
                if max_freq_file.exists() and scaling_max_file.exists():
                    max_freq = int(max_freq_file.read_text().strip())
                    target_freq = int(max_freq * max_percent / 100)
                    
                    with open(scaling_max_file, 'w') as f:
                        f.write(str(target_freq))
            
            self.logger.debug(f"Set CPU frequency limit to {max_percent}%")
        except Exception as e:
            self.logger.warning(f"Failed to set CPU frequency limit: {e}")
    
    async def _set_gpu_power_limit(self, power_percent: int):
        """Set GPU power limit (NVIDIA only)"""
        try:
            # Get max power limit
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=power.max_limit',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                max_power = float(result.stdout.strip())
                target_power = int(max_power * power_percent / 100)
                
                # Set power limit
                subprocess.run([
                    'nvidia-smi', '-pl', str(target_power)
                ], timeout=10)
                
                self.logger.debug(f"Set GPU power limit to {target_power}W ({power_percent}%)")
        except Exception as e:
            self.logger.debug(f"GPU power limit not set (NVIDIA GPU not available): {e}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Collect system metrics
                stats = await self._collect_system_stats()
                
                # Update power history
                self.power_history.append({
                    "timestamp": time.time(),
                    "stats": stats
                })
                
                # Limit history size
                max_history = self.config["monitoring"]["history_size"]
                if len(self.power_history) > max_history:
                    self.power_history = self.power_history[-max_history:]
                
                # Check thermal throttling
                if self.config["power"]["thermal_throttling"]:
                    thermal_threshold = self.config["power"]["thermal_threshold"]
                    if self.thermal_manager.check_thermal_throttling(thermal_threshold):
                        await self._handle_thermal_throttling()
                
                await asyncio.sleep(self.config["monitoring"]["interval"])
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)
    
    async def _collect_system_stats(self) -> Dict:
        """Collect comprehensive system statistics"""
        stats = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
            "network_io": psutil.net_io_counters()._asdict(),
            "temperatures": self.thermal_manager.get_temperatures(),
            "power_mode": self.current_mode.value,
            "running_tasks": len(self.task_scheduler.running_tasks),
            "deferred_tasks": len(self.task_scheduler.deferred_tasks)
        }
        
        # Add battery info if available
        battery = psutil.sensors_battery()
        if battery:
            stats["battery"] = {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "secsleft": battery.secsleft
            }
        
        # Add GPU stats if available
        try:
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                gpu_data = result.stdout.strip().split(', ')
                if len(gpu_data) >= 4:
                    stats["gpu"] = {
                        "utilization": float(gpu_data[0]),
                        "memory_used": float(gpu_data[1]),
                        "memory_total": float(gpu_data[2]),
                        "temperature": float(gpu_data[3]),
                        "power_draw": float(gpu_data[4]) if len(gpu_data) > 4 else None
                    }
        except:
            pass
        
        return stats
    
    async def _adaptive_mode_loop(self):
        """Adaptive power mode management"""
        if not self.config["power"]["adaptive_enabled"]:
            return
        
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Get recent system activity
                recent_stats = self.power_history[-10:] if len(self.power_history) >= 10 else self.power_history
                
                if not recent_stats:
                    continue
                
                # Calculate average utilization
                avg_cpu = sum(s["stats"]["cpu_percent"] for s in recent_stats) / len(recent_stats)
                avg_memory = sum(s["stats"]["memory_percent"] for s in recent_stats) / len(recent_stats)
                
                # Get battery status
                battery_level = None
                if recent_stats[-1]["stats"].get("battery"):
                    battery_level = recent_stats[-1]["stats"]["battery"]["percent"]
                
                # Determine optimal power mode
                optimal_mode = self._determine_optimal_mode(avg_cpu, avg_memory, battery_level)
                
                if optimal_mode != self.current_mode:
                    self.logger.info(f"Adaptive mode suggests changing to: {optimal_mode.value}")
                    await self.set_power_mode(optimal_mode)
                
            except Exception as e:
                self.logger.error(f"Adaptive mode error: {e}")
                await asyncio.sleep(60)
    
    def _determine_optimal_mode(self, avg_cpu: float, avg_memory: float, 
                              battery_level: Optional[int]) -> PowerMode:
        """Determine optimal power mode based on system state"""
        
        # Battery-based decisions
        if battery_level is not None:
            battery_config = self.config["power"]["battery_thresholds"]
            
            if battery_level <= battery_config["critical"]:
                return PowerMode.ULTRA_SAVER
            elif battery_level <= battery_config["low"]:
                return PowerMode.POWER_SAVER
        
        # Activity-based decisions
        if avg_cpu > 70 or avg_memory > 80:
            return PowerMode.FULL_POWER
        elif avg_cpu > 40 or avg_memory > 60:
            return PowerMode.BALANCED
        elif avg_cpu < 10 and avg_memory < 30:
            return PowerMode.POWER_SAVER
        else:
            return PowerMode.BALANCED
    
    async def _handle_thermal_throttling(self):
        """Handle thermal throttling event"""
        current_temps = self.thermal_manager.get_temperatures()
        max_temp = max(current_temps.values()) if current_temps else 0
        
        self.logger.warning(f"Thermal throttling active - max temp: {max_temp:.1f}°C")
        
        # Force power saver mode during thermal throttling
        if self.current_mode not in [PowerMode.POWER_SAVER, PowerMode.ULTRA_SAVER]:
            await self.set_power_mode(PowerMode.POWER_SAVER)
        
        # Pause non-critical tasks
        deferred_count = len(self.task_scheduler.deferred_tasks)
        running_count = len(self.task_scheduler.running_tasks)
        
        if running_count > 1:
            self.logger.info("Throttling active tasks due to thermal conditions")
            # In a real implementation, would implement task pausing
    
    async def _idle_management_loop(self):
        """Monitor system idle time and manage power accordingly"""
        while self.running:
            try:
                current_time = time.time()
                
                # Check if system has been idle
                recent_stats = self.power_history[-5:] if len(self.power_history) >= 5 else []
                
                if recent_stats:
                    recent_cpu_avg = sum(s["stats"]["cpu_percent"] for s in recent_stats) / len(recent_stats)
                    
                    # Update last activity time
                    if recent_cpu_avg > self.current_policy.suspend_threshold:
                        self.last_activity_time = current_time
                    
                    # Check idle timeout
                    idle_duration = current_time - self.last_activity_time
                    
                    if idle_duration > self.current_policy.idle_timeout:
                        self.logger.info(f"System idle for {idle_duration:.0f}s, entering power saving")
                        
                        # Move to more aggressive power saving
                        if self.current_mode == PowerMode.FULL_POWER:
                            await self.set_power_mode(PowerMode.BALANCED)
                        elif self.current_mode == PowerMode.BALANCED:
                            await self.set_power_mode(PowerMode.POWER_SAVER)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Idle management error: {e}")
                await asyncio.sleep(30)
    
    async def schedule_task(self, task_id: str, task_func: Callable, 
                          priority: ProcessingPriority = ProcessingPriority.NORMAL,
                          estimated_duration: int = 60,
                          power_requirement: int = 50):
        """Public interface to schedule tasks"""
        await self.task_scheduler.schedule_task(
            task_id, task_func, priority, estimated_duration, power_requirement
        )
    
    def get_status(self) -> Dict:
        """Get power management status"""
        recent_stats = self.power_history[-1]["stats"] if self.power_history else {}
        
        return {
            "current_mode": self.current_mode.value,
            "thermal_throttling": self.thermal_manager.throttle_active,
            "running_tasks": len(self.task_scheduler.running_tasks),
            "deferred_tasks": len(self.task_scheduler.deferred_tasks),
            "idle_time": time.time() - self.last_activity_time,
            "recent_stats": recent_stats,
            "available_modes": [mode.value for mode in PowerMode]
        }
    
    def get_power_history(self, hours: int = 1) -> List[Dict]:
        """Get power usage history"""
        cutoff_time = time.time() - (hours * 3600)
        return [
            entry for entry in self.power_history 
            if entry["timestamp"] > cutoff_time
        ]

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Power Management Agent")
    parser.add_argument("--config", default="/etc/activelog/power.conf",
                        help="Configuration file path")
    parser.add_argument("--mode", choices=[m.value for m in PowerMode],
                        help="Set initial power mode")
    
    args = parser.parse_args()
    
    # Create power agent
    agent = PowerAgent(args.config)
    
    # Set initial mode if specified
    if args.mode:
        initial_mode = PowerMode(args.mode)
        agent.current_mode = initial_mode
        agent.current_policy = agent.policies[initial_mode]
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        agent.logger.info(f"Received signal {signum}")
        agent.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        print("Power management agent stopped")

if __name__ == "__main__":
    asyncio.run(main())