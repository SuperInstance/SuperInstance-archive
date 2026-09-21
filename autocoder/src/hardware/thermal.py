"""
Thermal Manager for Laptop
Monitors GPU temperature and prevents overheating
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import subprocess
import re


class ThermalManager:
    """
    Monitors and manages thermal conditions on laptop
    Prevents GPU overheating during local inference
    """

    def __init__(
        self,
        max_temp: int = 80,
        max_continuous_minutes: int = 30,
        cooldown_seconds: int = 60,
        nvidia_smi_path: str = "/usr/lib/wsl/lib/nvidia-smi"
    ):
        """
        Initialize thermal manager

        Args:
            max_temp: Maximum GPU temperature in Celsius
            max_continuous_minutes: Max continuous inference time
            cooldown_seconds: Cooldown period after throttling
            nvidia_smi_path: Path to nvidia-smi
        """
        self.max_temp = max_temp
        self.max_continuous = timedelta(minutes=max_continuous_minutes)
        self.cooldown_seconds = cooldown_seconds
        self.nvidia_smi_path = nvidia_smi_path

        self.inference_start: Optional[datetime] = None
        self.last_temp_check: Optional[datetime] = None
        self.current_temp: Optional[int] = None
        self.is_cooling: bool = False

    def get_gpu_temperature(self) -> Optional[int]:
        """
        Get current GPU temperature

        Returns:
            Temperature in Celsius or None if unavailable
        """
        try:
            result = subprocess.run(
                [self.nvidia_smi_path, "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0:
                temp = int(result.stdout.strip())
                self.current_temp = temp
                self.last_temp_check = datetime.now()
                return temp

        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            pass

        return None

    def get_gpu_power(self) -> Optional[float]:
        """
        Get current GPU power draw

        Returns:
            Power in Watts or None if unavailable
        """
        try:
            result = subprocess.run(
                [self.nvidia_smi_path, "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0:
                power = float(result.stdout.strip())
                return power

        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            pass

        return None

    def should_throttle(self) -> bool:
        """
        Check if should throttle inference

        Returns:
            True if should stop/throttle inference
        """
        if self.is_cooling:
            return True

        # Check temperature
        temp = self.get_gpu_temperature()
        if temp and temp > self.max_temp:
            return True

        # Check continuous usage time
        if self.inference_start:
            duration = datetime.now() - self.inference_start
            if duration > self.max_continuous:
                return True

        return False

    def start_inference(self):
        """Mark start of GPU inference"""
        if not self.inference_start:
            self.inference_start = datetime.now()

    def end_inference(self):
        """Mark end of GPU inference"""
        self.inference_start = None

    async def cooldown(self):
        """
        Execute cooldown period

        Waits for GPU to cool down
        """
        self.is_cooling = True
        start_temp = self.get_gpu_temperature()

        print(f"⏸️  GPU Cooldown: {start_temp}°C → Waiting {self.cooldown_seconds}s...")

        # Wait cooldown period
        await asyncio.sleep(self.cooldown_seconds)

        # Check if cooled down
        end_temp = self.get_gpu_temperature()
        if end_temp:
            print(f"✓ GPU Cooled: {end_temp}°C")

        self.is_cooling = False
        self.inference_start = None

    def get_status(self) -> dict:
        """
        Get thermal status

        Returns:
            Dict with thermal information
        """
        temp = self.get_gpu_temperature()
        power = self.get_gpu_power()

        status = {
            'temperature': temp,
            'power_draw': power,
            'max_temp': self.max_temp,
            'is_throttling': self.should_throttle(),
            'is_cooling': self.is_cooling
        }

        if self.inference_start:
            duration = datetime.now() - self.inference_start
            status['continuous_time_seconds'] = duration.total_seconds()

        return status

    def get_thermal_warning(self) -> Optional[str]:
        """
        Get thermal warning message if applicable

        Returns:
            Warning string or None
        """
        temp = self.current_temp

        if not temp:
            return None

        if temp > self.max_temp + 5:
            return f"⚠️  GPU CRITICAL: {temp}°C! Stopping inference"
        elif temp > self.max_temp:
            return f"⚠️  GPU HOT: {temp}°C (max {self.max_temp}°C)"
        elif temp > self.max_temp - 5:
            return f"⏰ GPU Warm: {temp}°C (approaching limit)"

        return None


class PowerManager:
    """
    Detects power status (battery vs plugged in) on laptop
    """

    def __init__(self):
        self._cached_status: Optional[bool] = None
        self._cache_time: Optional[datetime] = None
        self._cache_duration = timedelta(seconds=30)

    def is_on_battery(self) -> bool:
        """
        Check if laptop is on battery power

        Returns:
            True if on battery, False if plugged in
        """
        # Use cache if recent
        if self._cached_status is not None and self._cache_time:
            if datetime.now() - self._cache_time < self._cache_duration:
                return self._cached_status

        # Try to detect power status
        try:
            # On Linux (including WSL), check power supply
            import os
            import glob

            power_supply_paths = glob.glob('/sys/class/power_supply/*/online')

            for path in power_supply_paths:
                try:
                    with open(path, 'r') as f:
                        status = f.read().strip()
                        if status == '1':
                            # Plugged in
                            self._cached_status = False
                            self._cache_time = datetime.now()
                            return False
                except:
                    continue

            # If we get here, assume on battery
            self._cached_status = True
            self._cache_time = datetime.now()
            return True

        except:
            # If detection fails, assume plugged in (safer)
            return False

    def get_battery_percentage(self) -> Optional[int]:
        """
        Get battery percentage

        Returns:
            Battery percentage (0-100) or None if unavailable
        """
        try:
            import glob

            capacity_paths = glob.glob('/sys/class/power_supply/BAT*/capacity')

            if capacity_paths:
                with open(capacity_paths[0], 'r') as f:
                    return int(f.read().strip())

        except:
            pass

        return None
