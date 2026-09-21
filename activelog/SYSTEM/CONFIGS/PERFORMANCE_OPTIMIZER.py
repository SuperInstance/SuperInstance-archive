#!/usr/bin/env python3
"""
ProArt Laptop Performance Optimizer
- Optimizes AI Professor College for 2024 ProArt laptop capabilities
- Manages CPU, memory, and thermal constraints
- Ensures sustainable long-term operation
"""

import os
import psutil
import time
import json
from pathlib import Path
from datetime import datetime

class ProArtOptimizer:
    def __init__(self):
        self.base_path = Path("/home/activeloguser/activelog")
        self.config_path = self.base_path / "SYSTEM/CONFIGS/performance_config.json"
        self.load_hardware_profile()
        
    def load_hardware_profile(self):
        """Detect ProArt laptop capabilities and set optimal limits"""
        # Get system specs
        cpu_count = psutil.cpu_count(logical=True)
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # ProArt laptop conservative optimization profile
        self.hardware_profile = {
            "cpu_cores": cpu_count,
            "memory_gb": round(memory_gb, 1),
            "max_cpu_usage_percent": 60,  # Leave headroom for other apps
            "max_memory_usage_gb": memory_gb * 0.4,  # Use 40% of total RAM
            "thermal_management": True,
            "battery_optimization": True
        }
        
        # Bot orchestration limits based on hardware
        if cpu_count >= 16:  # High-end ProArt
            self.bot_limits = {
                "max_concurrent_professors": 4,
                "max_concurrent_committee": 3,
                "max_concurrent_agents": 8,
                "iteration_delay_seconds": 20
            }
        elif cpu_count >= 8:  # Mid-range ProArt
            self.bot_limits = {
                "max_concurrent_professors": 3,
                "max_concurrent_committee": 2,
                "max_concurrent_agents": 6,
                "iteration_delay_seconds": 30
            }
        else:  # Conservative fallback
            self.bot_limits = {
                "max_concurrent_professors": 2,
                "max_concurrent_committee": 2,
                "max_concurrent_agents": 4,
                "iteration_delay_seconds": 45
            }
        
        self.save_config()
        print(f"💻 ProArt Profile: {cpu_count} cores, {memory_gb:.1f}GB RAM")
        print(f"🎛️ Bot Limits: {self.bot_limits['max_concurrent_agents']} max concurrent")
    
    def save_config(self):
        """Save performance configuration"""
        config = {
            "hardware_profile": self.hardware_profile,
            "bot_limits": self.bot_limits,
            "last_optimization": datetime.now().isoformat()
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def monitor_performance(self):
        """Real-time performance monitoring"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        performance_data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": memory.used / (1024**3),
            "temperature_check": self.check_thermal_throttling()
        }
        
        # Adaptive scaling based on current load
        if cpu_percent > self.hardware_profile["max_cpu_usage_percent"]:
            self.scale_down_bots()
        elif cpu_percent < 30:  # Conservative utilization
            self.scale_up_bots()
        
        return performance_data
    
    def check_thermal_throttling(self):
        """Monitor for thermal throttling (basic check)"""
        try:
            # Check CPU frequency scaling as proxy for thermal management
            cpu_freq = psutil.cpu_freq()
            if cpu_freq and hasattr(cpu_freq, 'current'):
                frequency_ratio = cpu_freq.current / cpu_freq.max if cpu_freq.max else 1.0
                return frequency_ratio < 0.8  # Potential throttling
        except:
            pass
        return False
    
    def scale_down_bots(self):
        """Reduce bot activity when system under stress"""
        self.bot_limits["iteration_delay_seconds"] = min(120, self.bot_limits["iteration_delay_seconds"] * 1.5)
        print(f"🔽 Scaled down: {self.bot_limits['iteration_delay_seconds']}s delay")
    
    def scale_up_bots(self):
        """Increase bot activity when system resources available"""
        self.bot_limits["iteration_delay_seconds"] = max(15, self.bot_limits["iteration_delay_seconds"] * 0.8)
        print(f"🔼 Scaled up: {self.bot_limits['iteration_delay_seconds']}s delay")
    
    def get_current_limits(self):
        """Get current performance limits for bot orchestrator"""
        return self.bot_limits
    
    def optimize_python_process(self):
        """Optimize current Python process for laptop"""
        # Set process priority (lower = nicer to system)
        os.nice(5)
        
        # Set CPU affinity if available (use efficiency cores first on hybrid CPUs)
        try:
            available_cpus = list(range(psutil.cpu_count(logical=True)))
            # Use 60% of available cores
            target_cores = available_cpus[:int(len(available_cpus) * 0.6)]
            psutil.Process().cpu_affinity(target_cores)
            print(f"⚙️ CPU affinity set to cores: {target_cores}")
        except:
            print("⚙️ CPU affinity not available on this system")

if __name__ == "__main__":
    optimizer = ProArtOptimizer()
    optimizer.optimize_python_process()
    
    print("🚀 Performance monitoring active...")
    while True:
        perf_data = optimizer.monitor_performance()
        print(f"CPU: {perf_data['cpu_percent']:.1f}% | "
              f"RAM: {perf_data['memory_percent']:.1f}% | "
              f"Thermal: {'⚠️' if perf_data['temperature_check'] else '✅'}")
        time.sleep(30)