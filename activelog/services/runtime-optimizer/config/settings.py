"""
Runtime Optimizer Configuration Settings

Central configuration for all runtime optimization components
"""

import os
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

class ResourceTier(Enum):
    """Resource availability tiers"""
    CRITICAL = "critical"      # < 10% resources
    LOW = "low"               # 10-30% resources
    MODERATE = "moderate"     # 30-70% resources
    HIGH = "high"            # 70-90% resources
    ABUNDANT = "abundant"     # > 90% resources

class NetworkTier(Enum):
    """Network quality tiers"""
    OFFLINE = "offline"       # No connection
    POOR = "poor"            # < 1 Mbps
    SLOW = "slow"            # 1-5 Mbps
    MODERATE = "moderate"     # 5-25 Mbps
    FAST = "fast"            # 25-100 Mbps
    EXCELLENT = "excellent"   # > 100 Mbps

class PowerProfile(Enum):
    """Power management profiles"""
    MAXIMUM_BATTERY = "max_battery"
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    PLUGGED_IN = "plugged_in"

@dataclass
class ResourceThresholds:
    """System resource thresholds"""
    cpu_critical: float = 90.0      # % CPU usage
    cpu_high: float = 70.0
    cpu_moderate: float = 30.0
    cpu_low: float = 10.0
    
    memory_critical: float = 90.0    # % Memory usage
    memory_high: float = 70.0
    memory_moderate: float = 40.0
    memory_low: float = 20.0
    
    disk_critical: float = 95.0      # % Disk usage
    disk_high: float = 80.0
    disk_moderate: float = 60.0
    disk_low: float = 40.0
    
    temperature_critical: float = 85.0  # °C
    temperature_high: float = 75.0
    temperature_moderate: float = 65.0
    temperature_low: float = 50.0
    
    network_excellent: float = 100.0   # Mbps
    network_fast: float = 25.0
    network_moderate: float = 5.0
    network_slow: float = 1.0

@dataclass
class OptimizationSettings:
    """Optimization behavior settings"""
    # Resource monitoring
    monitoring_interval: float = 1.0     # seconds
    history_window: int = 300            # samples to keep
    prediction_window: int = 60          # seconds ahead
    
    # Feature scaling
    enable_auto_scaling: bool = True
    scaling_sensitivity: float = 0.8     # 0-1, higher = more aggressive
    hysteresis_factor: float = 0.1       # prevent oscillation
    
    # Network adaptation
    bandwidth_test_interval: int = 30    # seconds
    connection_timeout: float = 5.0      # seconds
    retry_attempts: int = 3
    
    # Cost optimization
    warn_expensive_threshold: float = 10.0  # USD
    batch_delay: float = 5.0             # seconds
    cache_size_mb: int = 500
    
    # Performance tuning
    max_threads: int = None              # None = auto-detect
    enable_gpu: bool = True
    enable_caching: bool = True
    compression_level: int = 6           # 1-9

@dataclass
class FeatureProfile:
    """Feature enablement profile"""
    # Visual features
    animations_enabled: bool = True
    high_quality_textures: bool = True
    visual_effects: bool = True
    real_time_updates: bool = True
    
    # Computational features
    advanced_algorithms: bool = True
    background_processing: bool = True
    predictive_features: bool = True
    precision_mode: bool = False
    
    # Network features
    auto_sync: bool = True
    prefetching: bool = True
    real_time_collaboration: bool = True
    cloud_backup: bool = True
    
    # Quality settings
    texture_resolution: float = 1.0      # 0.1-2.0 multiplier
    animation_fps: int = 60
    update_frequency: float = 1.0        # Hz
    compression_quality: float = 0.8     # 0-1

class RuntimeOptimizerConfig:
    """Main configuration class"""
    
    def __init__(self):
        self.port = int(os.getenv("PORT", 8431))
        self.host = os.getenv("HOST", "0.0.0.0")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Service configuration
        self.service_name = "runtime-optimizer"
        self.version = "1.0.0"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Resource thresholds
        self.thresholds = ResourceThresholds()
        
        # Optimization settings
        self.optimization = OptimizationSettings()
        
        # Feature profiles by resource tier
        self.feature_profiles = {
            ResourceTier.CRITICAL: FeatureProfile(
                animations_enabled=False,
                high_quality_textures=False,
                visual_effects=False,
                real_time_updates=False,
                advanced_algorithms=False,
                background_processing=False,
                predictive_features=False,
                auto_sync=False,
                prefetching=False,
                real_time_collaboration=False,
                cloud_backup=False,
                texture_resolution=0.25,
                animation_fps=15,
                update_frequency=0.1,
                compression_quality=0.3
            ),
            ResourceTier.LOW: FeatureProfile(
                animations_enabled=True,
                high_quality_textures=False,
                visual_effects=False,
                real_time_updates=False,
                advanced_algorithms=False,
                background_processing=False,
                predictive_features=False,
                auto_sync=False,
                prefetching=True,
                real_time_collaboration=False,
                cloud_backup=False,
                texture_resolution=0.5,
                animation_fps=30,
                update_frequency=0.5,
                compression_quality=0.5
            ),
            ResourceTier.MODERATE: FeatureProfile(
                animations_enabled=True,
                high_quality_textures=True,
                visual_effects=False,
                real_time_updates=True,
                advanced_algorithms=False,
                background_processing=True,
                predictive_features=False,
                auto_sync=True,
                prefetching=True,
                real_time_collaboration=False,
                cloud_backup=True,
                texture_resolution=0.75,
                animation_fps=45,
                update_frequency=0.75,
                compression_quality=0.65
            ),
            ResourceTier.HIGH: FeatureProfile(
                animations_enabled=True,
                high_quality_textures=True,
                visual_effects=True,
                real_time_updates=True,
                advanced_algorithms=True,
                background_processing=True,
                predictive_features=True,
                auto_sync=True,
                prefetching=True,
                real_time_collaboration=True,
                cloud_backup=True,
                texture_resolution=1.0,
                animation_fps=60,
                update_frequency=1.0,
                compression_quality=0.8
            ),
            ResourceTier.ABUNDANT: FeatureProfile(
                animations_enabled=True,
                high_quality_textures=True,
                visual_effects=True,
                real_time_updates=True,
                advanced_algorithms=True,
                background_processing=True,
                predictive_features=True,
                precision_mode=True,
                auto_sync=True,
                prefetching=True,
                real_time_collaboration=True,
                cloud_backup=True,
                texture_resolution=1.5,
                animation_fps=120,
                update_frequency=2.0,
                compression_quality=0.95
            )
        }
        
        # Network profiles by connection tier
        self.network_profiles = {
            NetworkTier.OFFLINE: {
                "sync_enabled": False,
                "prefetch_enabled": False,
                "quality": "minimum",
                "compression": 0.2,
                "batch_size": 1000,
                "timeout": 1.0
            },
            NetworkTier.POOR: {
                "sync_enabled": False,
                "prefetch_enabled": False,
                "quality": "low",
                "compression": 0.3,
                "batch_size": 500,
                "timeout": 10.0
            },
            NetworkTier.SLOW: {
                "sync_enabled": True,
                "prefetch_enabled": False,
                "quality": "medium",
                "compression": 0.5,
                "batch_size": 200,
                "timeout": 5.0
            },
            NetworkTier.MODERATE: {
                "sync_enabled": True,
                "prefetch_enabled": True,
                "quality": "good",
                "compression": 0.7,
                "batch_size": 100,
                "timeout": 3.0
            },
            NetworkTier.FAST: {
                "sync_enabled": True,
                "prefetch_enabled": True,
                "quality": "high",
                "compression": 0.85,
                "batch_size": 50,
                "timeout": 2.0
            },
            NetworkTier.EXCELLENT: {
                "sync_enabled": True,
                "prefetch_enabled": True,
                "quality": "maximum",
                "compression": 0.95,
                "batch_size": 10,
                "timeout": 1.0
            }
        }
        
        # Cost optimization settings
        self.cost_settings = {
            "data_cost_per_gb": 0.10,           # USD per GB
            "compute_cost_per_hour": 0.05,      # USD per compute hour
            "storage_cost_per_gb_month": 0.02,  # USD per GB per month
            "api_call_cost": 0.001,             # USD per API call
            "warn_daily_limit": 5.0,            # USD per day
            "warn_monthly_limit": 50.0,         # USD per month
            "free_tier_data_gb": 1.0,           # GB per month
            "free_tier_compute_hours": 10.0,    # Hours per month
            "free_tier_api_calls": 1000,        # Calls per month
        }
        
    def get_resource_tier(self, cpu_percent: float, memory_percent: float, 
                         temperature: Optional[float] = None) -> ResourceTier:
        """Determine resource tier based on system metrics"""
        # Use the most constrained resource as the limiting factor
        constraints = []
        
        if cpu_percent >= self.thresholds.cpu_critical:
            constraints.append(ResourceTier.CRITICAL)
        elif cpu_percent >= self.thresholds.cpu_high:
            constraints.append(ResourceTier.LOW)
        elif cpu_percent >= self.thresholds.cpu_moderate:
            constraints.append(ResourceTier.MODERATE)
        elif cpu_percent >= self.thresholds.cpu_low:
            constraints.append(ResourceTier.HIGH)
        else:
            constraints.append(ResourceTier.ABUNDANT)
            
        if memory_percent >= self.thresholds.memory_critical:
            constraints.append(ResourceTier.CRITICAL)
        elif memory_percent >= self.thresholds.memory_high:
            constraints.append(ResourceTier.LOW)
        elif memory_percent >= self.thresholds.memory_moderate:
            constraints.append(ResourceTier.MODERATE)
        elif memory_percent >= self.thresholds.memory_low:
            constraints.append(ResourceTier.HIGH)
        else:
            constraints.append(ResourceTier.ABUNDANT)
            
        if temperature is not None:
            if temperature >= self.thresholds.temperature_critical:
                constraints.append(ResourceTier.CRITICAL)
            elif temperature >= self.thresholds.temperature_high:
                constraints.append(ResourceTier.LOW)
            elif temperature >= self.thresholds.temperature_moderate:
                constraints.append(ResourceTier.MODERATE)
            else:
                constraints.append(ResourceTier.HIGH)
        
        # Return the most restrictive tier
        tier_order = [ResourceTier.CRITICAL, ResourceTier.LOW, ResourceTier.MODERATE, 
                     ResourceTier.HIGH, ResourceTier.ABUNDANT]
        
        for tier in tier_order:
            if tier in constraints:
                return tier
        
        return ResourceTier.MODERATE
    
    def get_network_tier(self, bandwidth_mbps: float, latency_ms: float = None) -> NetworkTier:
        """Determine network tier based on connection metrics"""
        if bandwidth_mbps == 0:
            return NetworkTier.OFFLINE
        elif bandwidth_mbps >= self.thresholds.network_excellent:
            return NetworkTier.EXCELLENT
        elif bandwidth_mbps >= self.thresholds.network_fast:
            return NetworkTier.FAST
        elif bandwidth_mbps >= self.thresholds.network_moderate:
            return NetworkTier.MODERATE
        elif bandwidth_mbps >= self.thresholds.network_slow:
            return NetworkTier.SLOW
        else:
            return NetworkTier.POOR
    
    def get_feature_profile(self, tier: ResourceTier) -> FeatureProfile:
        """Get feature profile for resource tier"""
        return self.feature_profiles.get(tier, self.feature_profiles[ResourceTier.MODERATE])
    
    def get_network_profile(self, tier: NetworkTier) -> Dict[str, Any]:
        """Get network profile for connection tier"""
        return self.network_profiles.get(tier, self.network_profiles[NetworkTier.MODERATE])

# Global configuration instance
config = RuntimeOptimizerConfig()