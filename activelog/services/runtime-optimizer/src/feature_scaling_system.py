"""
Feature Scaling System

Automatic feature degradation and enhancement based on system resources,
providing adaptive quality scaling for optimal user experience.
"""

import asyncio
import time
import logging
import json
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from abc import ABC, abstractmethod

from config.settings import config, ResourceTier, FeatureProfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeatureCategory(Enum):
    """Categories of features that can be scaled"""
    VISUAL = "visual"
    COMPUTATIONAL = "computational"
    NETWORK = "network"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    UI_UX = "ui_ux"
    BACKGROUND = "background"

class ScalingDirection(Enum):
    """Direction of feature scaling"""
    DEGRADE = "degrade"
    ENHANCE = "enhance"
    MAINTAIN = "maintain"

class FeatureState(Enum):
    """Current state of a feature"""
    DISABLED = "disabled"
    MINIMAL = "minimal"
    REDUCED = "reduced"
    STANDARD = "standard"
    ENHANCED = "enhanced"
    MAXIMUM = "maximum"

@dataclass
class FeatureSettings:
    """Settings for a specific feature"""
    feature_id: str
    category: FeatureCategory
    current_state: FeatureState
    enabled: bool
    quality_level: float  # 0.0 - 1.0
    resource_cost: Dict[str, float]  # CPU, memory, network, etc.
    user_priority: int  # 0-10, higher is more important to user
    system_priority: int  # 0-10, higher is more critical to system
    dependencies: Set[str]  # Other features this depends on
    conflicts: Set[str]  # Features that conflict with this one
    min_quality: float = 0.1
    max_quality: float = 1.0
    scaling_factor: float = 0.1  # How much to change per step
    
    def to_dict(self):
        data = asdict(self)
        data['category'] = self.category.value
        data['current_state'] = self.current_state.value
        data['dependencies'] = list(self.dependencies)
        data['conflicts'] = list(self.conflicts)
        return data

@dataclass
class ScalingEvent:
    """Record of a scaling event"""
    timestamp: datetime
    feature_id: str
    direction: ScalingDirection
    old_state: FeatureState
    new_state: FeatureState
    old_quality: float
    new_quality: float
    trigger_reason: str
    resource_tier: ResourceTier
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['direction'] = self.direction.value
        data['old_state'] = self.old_state.value
        data['new_state'] = self.new_state.value
        data['resource_tier'] = self.resource_tier.value
        return data

class FeatureScaler(ABC):
    """Abstract base class for feature scalers"""
    
    @abstractmethod
    async def scale_up(self, feature: FeatureSettings, target_quality: float) -> bool:
        """Scale feature up to target quality level"""
        pass
    
    @abstractmethod
    async def scale_down(self, feature: FeatureSettings, target_quality: float) -> bool:
        """Scale feature down to target quality level"""
        pass
    
    @abstractmethod
    def get_current_resource_usage(self, feature: FeatureSettings) -> Dict[str, float]:
        """Get current resource usage for this feature"""
        pass

class VisualFeatureScaler(FeatureScaler):
    """Scaler for visual features"""
    
    async def scale_up(self, feature: FeatureSettings, target_quality: float) -> bool:
        """Enhance visual features"""
        try:
            if feature.feature_id == "animations":
                # Increase animation complexity and frame rate
                new_fps = int(30 + (target_quality * 90))  # 30-120 FPS
                await self._set_animation_fps(new_fps)
                
            elif feature.feature_id == "textures":
                # Increase texture resolution
                resolution_multiplier = 0.5 + (target_quality * 1.5)  # 0.5x - 2.0x
                await self._set_texture_resolution(resolution_multiplier)
                
            elif feature.feature_id == "visual_effects":
                # Enable more advanced effects
                effects_level = int(target_quality * 5)  # 0-5 effects levels
                await self._set_visual_effects_level(effects_level)
                
            elif feature.feature_id == "anti_aliasing":
                # Adjust anti-aliasing quality
                aa_samples = int(1 + (target_quality * 15))  # 1x - 16x MSAA
                await self._set_antialiasing(aa_samples)
                
            feature.quality_level = target_quality
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale up visual feature {feature.feature_id}: {e}")
            return False
    
    async def scale_down(self, feature: FeatureSettings, target_quality: float) -> bool:
        """Reduce visual features"""
        try:
            if feature.feature_id == "animations":
                # Reduce animation complexity and frame rate
                new_fps = max(15, int(15 + (target_quality * 45)))  # 15-60 FPS
                await self._set_animation_fps(new_fps)
                
            elif feature.feature_id == "textures":
                # Reduce texture resolution
                resolution_multiplier = max(0.25, 0.25 + (target_quality * 0.75))  # 0.25x - 1.0x
                await self._set_texture_resolution(resolution_multiplier)
                
            elif feature.feature_id == "visual_effects":
                # Disable or reduce effects
                effects_level = max(0, int(target_quality * 3))  # 0-3 effects levels
                await self._set_visual_effects_level(effects_level)
                
            elif feature.feature_id == "anti_aliasing":
                # Reduce anti-aliasing
                aa_samples = max(1, int(1 + (target_quality * 3)))  # 1x - 4x MSAA
                await self._set_antialiasing(aa_samples)
                
            feature.quality_level = target_quality
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale down visual feature {feature.feature_id}: {e}")
            return False
    
    def get_current_resource_usage(self, feature: FeatureSettings) -> Dict[str, float]:
        """Get resource usage for visual features"""
        base_gpu = feature.resource_cost.get('gpu', 10.0)
        base_cpu = feature.resource_cost.get('cpu', 5.0)
        base_memory = feature.resource_cost.get('memory', 50.0)  # MB
        
        # Scale resource usage with quality
        quality_multiplier = feature.quality_level ** 1.5  # Non-linear scaling
        
        return {
            'gpu': base_gpu * quality_multiplier,
            'cpu': base_cpu * quality_multiplier,
            'memory': base_memory * quality_multiplier
        }
    
    async def _set_animation_fps(self, fps: int):
        """Set animation frame rate"""
        # This would integrate with the actual UI framework
        logger.info(f"Setting animation FPS to {fps}")
        await asyncio.sleep(0.01)  # Simulate API call
    
    async def _set_texture_resolution(self, multiplier: float):
        """Set texture resolution multiplier"""
        logger.info(f"Setting texture resolution multiplier to {multiplier:.2f}")
        await asyncio.sleep(0.02)
    
    async def _set_visual_effects_level(self, level: int):
        """Set visual effects level"""
        logger.info(f"Setting visual effects level to {level}")
        await asyncio.sleep(0.01)
    
    async def _set_antialiasing(self, samples: int):
        """Set anti-aliasing samples"""
        logger.info(f"Setting anti-aliasing to {samples}x MSAA")
        await asyncio.sleep(0.01)

class ComputationalFeatureScaler(FeatureScaler):
    """Scaler for computational features"""
    
    async def scale_up(self, feature: FeatureSettings, target_quality: float) -> bool:
        """Enhance computational features"""
        try:
            if feature.feature_id == "algorithms":
                # Switch to more accurate but expensive algorithms
                algorithm_complexity = int(target_quality * 5)  # 0-5 complexity levels
                await self._set_algorithm_complexity(algorithm_complexity)
                
            elif feature.feature_id == "precision":
                # Increase numerical precision
                precision_bits = int(32 + (target_quality * 32))  # 32-64 bit precision
                await self._set_precision(precision_bits)
                
            elif feature.feature_id == "background_processing":
                # Enable more background tasks
                max_background_tasks = int(1 + (target_quality * 9))  # 1-10 tasks
                await self._set_max_background_tasks(max_background_tasks)
                
            elif feature.feature_id == "predictive_features":
                # Enable predictive algorithms
                prediction_window = int(target_quality * 300)  # 0-300 seconds
                await self._set_prediction_window(prediction_window)
                
            feature.quality_level = target_quality
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale up computational feature {feature.feature_id}: {e}")
            return False
    
    async def scale_down(self, feature: FeatureSettings, target_quality: float) -> bool:
        """Reduce computational features"""
        try:
            if feature.feature_id == "algorithms":
                # Switch to simpler, faster algorithms
                algorithm_complexity = max(0, int(target_quality * 3))  # 0-3 complexity
                await self._set_algorithm_complexity(algorithm_complexity)
                
            elif feature.feature_id == "precision":
                # Reduce precision
                precision_bits = max(16, int(16 + (target_quality * 16)))  # 16-32 bit
                await self._set_precision(precision_bits)
                
            elif feature.feature_id == "background_processing":
                # Reduce background tasks
                max_background_tasks = max(0, int(target_quality * 5))  # 0-5 tasks
                await self._set_max_background_tasks(max_background_tasks)
                
            elif feature.feature_id == "predictive_features":
                # Disable or reduce predictions
                prediction_window = max(0, int(target_quality * 60))  # 0-60 seconds
                await self._set_prediction_window(prediction_window)
                
            feature.quality_level = target_quality
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale down computational feature {feature.feature_id}: {e}")
            return False
    
    def get_current_resource_usage(self, feature: FeatureSettings) -> Dict[str, float]:
        """Get resource usage for computational features"""
        base_cpu = feature.resource_cost.get('cpu', 20.0)
        base_memory = feature.resource_cost.get('memory', 100.0)  # MB
        
        # Exponential scaling for computational complexity
        quality_multiplier = feature.quality_level ** 2
        
        return {
            'cpu': base_cpu * quality_multiplier,
            'memory': base_memory * quality_multiplier
        }
    
    async def _set_algorithm_complexity(self, level: int):
        """Set algorithm complexity level"""
        logger.info(f"Setting algorithm complexity to level {level}")
        await asyncio.sleep(0.01)
    
    async def _set_precision(self, bits: int):
        """Set numerical precision"""
        logger.info(f"Setting precision to {bits} bits")
        await asyncio.sleep(0.01)
    
    async def _set_max_background_tasks(self, max_tasks: int):
        """Set maximum background tasks"""
        logger.info(f"Setting max background tasks to {max_tasks}")
        await asyncio.sleep(0.01)
    
    async def _set_prediction_window(self, window_seconds: int):
        """Set prediction window"""
        logger.info(f"Setting prediction window to {window_seconds} seconds")
        await asyncio.sleep(0.01)

class NetworkFeatureScaler(FeatureScaler):
    """Scaler for network-related features"""
    
    async def scale_up(self, feature: FeatureSettings, target_quality: float) -> bool:
        """Enhance network features"""
        try:
            if feature.feature_id == "sync_frequency":
                # Increase sync frequency
                sync_interval = max(1, int(60 - (target_quality * 55)))  # 5-60 seconds
                await self._set_sync_interval(sync_interval)
                
            elif feature.feature_id == "compression":
                # Reduce compression for better quality
                compression_level = max(1, int(1 + (target_quality * 8)))  # 1-9
                await self._set_compression_level(compression_level)
                
            elif feature.feature_id == "prefetching":
                # Increase prefetching aggressiveness
                prefetch_items = int(target_quality * 100)  # 0-100 items
                await self._set_prefetch_count(prefetch_items)
                
            elif feature.feature_id == "real_time_updates":
                # Enable real-time features
                update_rate = target_quality * 10  # 0-10 Hz
                await self._set_update_rate(update_rate)
                
            feature.quality_level = target_quality
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale up network feature {feature.feature_id}: {e}")
            return False
    
    async def scale_down(self, feature: FeatureSettings, target_quality: float) -> bool:
        """Reduce network features"""
        try:
            if feature.feature_id == "sync_frequency":
                # Reduce sync frequency
                sync_interval = int(60 + (target_quality * 240))  # 60-300 seconds
                await self._set_sync_interval(sync_interval)
                
            elif feature.feature_id == "compression":
                # Increase compression
                compression_level = max(1, int(9 - (target_quality * 8)))  # 1-9
                await self._set_compression_level(compression_level)
                
            elif feature.feature_id == "prefetching":
                # Reduce prefetching
                prefetch_items = max(0, int(target_quality * 20))  # 0-20 items
                await self._set_prefetch_count(prefetch_items)
                
            elif feature.feature_id == "real_time_updates":
                # Reduce update rate
                update_rate = target_quality * 2  # 0-2 Hz
                await self._set_update_rate(update_rate)
                
            feature.quality_level = target_quality
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale down network feature {feature.feature_id}: {e}")
            return False
    
    def get_current_resource_usage(self, feature: FeatureSettings) -> Dict[str, float]:
        """Get resource usage for network features"""
        base_network = feature.resource_cost.get('network', 1.0)  # Mbps
        base_cpu = feature.resource_cost.get('cpu', 5.0)
        
        return {
            'network': base_network * feature.quality_level,
            'cpu': base_cpu * feature.quality_level
        }
    
    async def _set_sync_interval(self, seconds: int):
        """Set synchronization interval"""
        logger.info(f"Setting sync interval to {seconds} seconds")
        await asyncio.sleep(0.01)
    
    async def _set_compression_level(self, level: int):
        """Set compression level"""
        logger.info(f"Setting compression level to {level}")
        await asyncio.sleep(0.01)
    
    async def _set_prefetch_count(self, count: int):
        """Set prefetch item count"""
        logger.info(f"Setting prefetch count to {count} items")
        await asyncio.sleep(0.01)
    
    async def _set_update_rate(self, rate: float):
        """Set real-time update rate"""
        logger.info(f"Setting update rate to {rate:.1f} Hz")
        await asyncio.sleep(0.01)

class FeatureScalingSystem:
    """Main feature scaling system"""
    
    def __init__(self):
        self.features: Dict[str, FeatureSettings] = {}
        self.scalers: Dict[FeatureCategory, FeatureScaler] = {
            FeatureCategory.VISUAL: VisualFeatureScaler(),
            FeatureCategory.COMPUTATIONAL: ComputationalFeatureScaler(),
            FeatureCategory.NETWORK: NetworkFeatureScaler()
        }
        self.scaling_history = deque(maxlen=1000)
        self.current_resource_tier = ResourceTier.MODERATE
        self.scaling_callbacks: List[Callable] = []
        self.auto_scaling_enabled = True
        self.scaling_sensitivity = config.optimization.scaling_sensitivity
        self.hysteresis_factor = config.optimization.hysteresis_factor
        
        # Initialize default features
        self._initialize_default_features()
    
    def _initialize_default_features(self):
        """Initialize default feature set"""
        default_features = [
            # Visual features
            FeatureSettings(
                feature_id="animations",
                category=FeatureCategory.VISUAL,
                current_state=FeatureState.STANDARD,
                enabled=True,
                quality_level=0.8,
                resource_cost={'gpu': 15.0, 'cpu': 5.0, 'memory': 50.0},
                user_priority=7,
                system_priority=3,
                dependencies=set(),
                conflicts={'battery_saver'}
            ),
            FeatureSettings(
                feature_id="textures",
                category=FeatureCategory.VISUAL,
                current_state=FeatureState.STANDARD,
                enabled=True,
                quality_level=0.8,
                resource_cost={'gpu': 25.0, 'cpu': 3.0, 'memory': 200.0},
                user_priority=8,
                system_priority=2,
                dependencies=set(),
                conflicts=set()
            ),
            FeatureSettings(
                feature_id="visual_effects",
                category=FeatureCategory.VISUAL,
                current_state=FeatureState.STANDARD,
                enabled=True,
                quality_level=0.7,
                resource_cost={'gpu': 20.0, 'cpu': 8.0, 'memory': 100.0},
                user_priority=6,
                system_priority=1,
                dependencies={'textures'},
                conflicts={'low_power_mode'}
            ),
            
            # Computational features
            FeatureSettings(
                feature_id="algorithms",
                category=FeatureCategory.COMPUTATIONAL,
                current_state=FeatureState.STANDARD,
                enabled=True,
                quality_level=0.7,
                resource_cost={'cpu': 30.0, 'memory': 150.0},
                user_priority=8,
                system_priority=7,
                dependencies=set(),
                conflicts=set()
            ),
            FeatureSettings(
                feature_id="background_processing",
                category=FeatureCategory.COMPUTATIONAL,
                current_state=FeatureState.STANDARD,
                enabled=True,
                quality_level=0.6,
                resource_cost={'cpu': 15.0, 'memory': 100.0},
                user_priority=4,
                system_priority=5,
                dependencies=set(),
                conflicts={'battery_saver', 'thermal_throttle'}
            ),
            FeatureSettings(
                feature_id="predictive_features",
                category=FeatureCategory.COMPUTATIONAL,
                current_state=FeatureState.STANDARD,
                enabled=True,
                quality_level=0.5,
                resource_cost={'cpu': 10.0, 'memory': 75.0, 'network': 0.5},
                user_priority=5,
                system_priority=3,
                dependencies={'background_processing'},
                conflicts={'offline_mode'}
            ),
            
            # Network features
            FeatureSettings(
                feature_id="sync_frequency",
                category=FeatureCategory.NETWORK,
                current_state=FeatureState.STANDARD,
                enabled=True,
                quality_level=0.7,
                resource_cost={'network': 2.0, 'cpu': 5.0},
                user_priority=7,
                system_priority=6,
                dependencies=set(),
                conflicts={'offline_mode'}
            ),
            FeatureSettings(
                feature_id="prefetching",
                category=FeatureCategory.NETWORK,
                current_state=FeatureState.STANDARD,
                enabled=True,
                quality_level=0.6,
                resource_cost={'network': 5.0, 'cpu': 3.0, 'memory': 200.0},
                user_priority=6,
                system_priority=4,
                dependencies=set(),
                conflicts={'data_saver', 'offline_mode'}
            ),
            FeatureSettings(
                feature_id="real_time_updates",
                category=FeatureCategory.NETWORK,
                current_state=FeatureState.STANDARD,
                enabled=True,
                quality_level=0.8,
                resource_cost={'network': 1.0, 'cpu': 5.0},
                user_priority=9,
                system_priority=8,
                dependencies=set(),
                conflicts={'offline_mode', 'data_saver'}
            )
        ]
        
        for feature in default_features:
            self.features[feature.feature_id] = feature
    
    def add_scaling_callback(self, callback: Callable):
        """Add callback for scaling events"""
        self.scaling_callbacks.append(callback)
    
    async def update_resource_tier(self, new_tier: ResourceTier, trigger_reason: str = "external"):
        """Update resource tier and scale features accordingly"""
        if new_tier == self.current_resource_tier:
            return
        
        old_tier = self.current_resource_tier
        self.current_resource_tier = new_tier
        
        logger.info(f"Resource tier changed: {old_tier.value} -> {new_tier.value}")
        
        if self.auto_scaling_enabled:
            await self._auto_scale_features(new_tier, trigger_reason)
    
    async def _auto_scale_features(self, target_tier: ResourceTier, trigger_reason: str):
        """Automatically scale features based on resource tier"""
        target_profile = config.get_feature_profile(target_tier)
        
        scaling_tasks = []
        
        for feature_id, feature in self.features.items():
            # Determine target quality based on feature profile
            target_quality = self._get_target_quality_for_feature(feature, target_profile)
            
            # Apply hysteresis to prevent oscillation
            current_quality = feature.quality_level
            quality_diff = abs(target_quality - current_quality)
            
            if quality_diff > self.hysteresis_factor:
                direction = ScalingDirection.ENHANCE if target_quality > current_quality else ScalingDirection.DEGRADE
                scaling_tasks.append(self._scale_feature(feature, target_quality, direction, trigger_reason))
        
        # Execute scaling operations in parallel
        if scaling_tasks:
            await asyncio.gather(*scaling_tasks, return_exceptions=True)
    
    def _get_target_quality_for_feature(self, feature: FeatureSettings, profile: FeatureProfile) -> float:
        """Get target quality level for a feature based on profile"""
        if feature.feature_id == "animations":
            return 1.0 if profile.animations_enabled else 0.0
        elif feature.feature_id == "textures":
            return profile.texture_resolution
        elif feature.feature_id == "visual_effects":
            return 1.0 if profile.visual_effects else 0.0
        elif feature.feature_id == "algorithms":
            return 1.0 if profile.advanced_algorithms else 0.5
        elif feature.feature_id == "background_processing":
            return 1.0 if profile.background_processing else 0.0
        elif feature.feature_id == "predictive_features":
            return 1.0 if profile.predictive_features else 0.0
        elif feature.feature_id == "sync_frequency":
            return 1.0 if profile.auto_sync else 0.3
        elif feature.feature_id == "prefetching":
            return 1.0 if profile.prefetching else 0.0
        elif feature.feature_id == "real_time_updates":
            return 1.0 if profile.real_time_updates else 0.2
        else:
            # Default scaling based on profile quality
            return profile.compression_quality
    
    async def _scale_feature(self, feature: FeatureSettings, target_quality: float, 
                           direction: ScalingDirection, trigger_reason: str) -> bool:
        """Scale a specific feature"""
        try:
            # Check dependencies and conflicts
            if not self._can_scale_feature(feature, target_quality, direction):
                return False
            
            old_state = feature.current_state
            old_quality = feature.quality_level
            
            # Get appropriate scaler
            scaler = self.scalers.get(feature.category)
            if not scaler:
                logger.warning(f"No scaler available for category {feature.category.value}")
                return False
            
            # Perform scaling
            success = False
            if direction == ScalingDirection.ENHANCE:
                success = await scaler.scale_up(feature, target_quality)
            else:
                success = await scaler.scale_down(feature, target_quality)
            
            if success:
                # Update feature state
                new_state = self._quality_to_state(target_quality)
                feature.current_state = new_state
                
                # Record scaling event
                event = ScalingEvent(
                    timestamp=datetime.now(),
                    feature_id=feature.feature_id,
                    direction=direction,
                    old_state=old_state,
                    new_state=new_state,
                    old_quality=old_quality,
                    new_quality=target_quality,
                    trigger_reason=trigger_reason,
                    resource_tier=self.current_resource_tier
                )
                self.scaling_history.append(event)
                
                logger.info(f"Scaled {feature.feature_id}: {old_quality:.2f} -> {target_quality:.2f} ({direction.value})")
                
                # Notify callbacks
                await self._notify_scaling_callbacks(event)
                
                return True
            else:
                logger.warning(f"Failed to scale {feature.feature_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error scaling feature {feature.feature_id}: {e}")
            return False
    
    def _can_scale_feature(self, feature: FeatureSettings, target_quality: float, 
                          direction: ScalingDirection) -> bool:
        """Check if feature can be scaled"""
        # Check quality bounds
        if target_quality < feature.min_quality or target_quality > feature.max_quality:
            return False
        
        # Check dependencies
        for dep_id in feature.dependencies:
            if dep_id in self.features:
                dep_feature = self.features[dep_id]
                if not dep_feature.enabled or dep_feature.quality_level < 0.3:
                    logger.info(f"Cannot scale {feature.feature_id}: dependency {dep_id} not satisfied")
                    return False
        
        # Check conflicts
        for conflict_id in feature.conflicts:
            if conflict_id in self.features:
                conflict_feature = self.features[conflict_id]
                if conflict_feature.enabled and conflict_feature.quality_level > 0.5:
                    logger.info(f"Cannot scale {feature.feature_id}: conflicts with {conflict_id}")
                    return False
        
        return True
    
    def _quality_to_state(self, quality: float) -> FeatureState:
        """Convert quality level to feature state"""
        if quality <= 0.1:
            return FeatureState.DISABLED
        elif quality <= 0.3:
            return FeatureState.MINIMAL
        elif quality <= 0.6:
            return FeatureState.REDUCED
        elif quality <= 0.8:
            return FeatureState.STANDARD
        elif quality <= 0.95:
            return FeatureState.ENHANCED
        else:
            return FeatureState.MAXIMUM
    
    async def _notify_scaling_callbacks(self, event: ScalingEvent):
        """Notify callbacks of scaling event"""
        for callback in self.scaling_callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Scaling callback error: {e}")
    
    async def manual_scale_feature(self, feature_id: str, target_quality: float) -> bool:
        """Manually scale a specific feature"""
        if feature_id not in self.features:
            logger.warning(f"Feature {feature_id} not found")
            return False
        
        feature = self.features[feature_id]
        current_quality = feature.quality_level
        direction = ScalingDirection.ENHANCE if target_quality > current_quality else ScalingDirection.DEGRADE
        
        return await self._scale_feature(feature, target_quality, direction, "manual")
    
    async def enable_feature(self, feature_id: str) -> bool:
        """Enable a feature"""
        if feature_id not in self.features:
            return False
        
        feature = self.features[feature_id]
        if not feature.enabled:
            feature.enabled = True
            # Scale to minimum viable quality
            return await self.manual_scale_feature(feature_id, 0.5)
        return True
    
    async def disable_feature(self, feature_id: str) -> bool:
        """Disable a feature"""
        if feature_id not in self.features:
            return False
        
        feature = self.features[feature_id]
        if feature.enabled:
            feature.enabled = False
            # Scale to minimum quality
            return await self.manual_scale_feature(feature_id, 0.0)
        return True
    
    def get_feature_status(self, feature_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific feature"""
        if feature_id not in self.features:
            return None
        
        feature = self.features[feature_id]
        scaler = self.scalers.get(feature.category)
        
        status = feature.to_dict()
        if scaler:
            status['current_resource_usage'] = scaler.get_current_resource_usage(feature)
        
        return status
    
    def get_all_features_status(self) -> Dict[str, Any]:
        """Get status of all features"""
        features_status = {}
        total_resource_usage = defaultdict(float)
        
        for feature_id, feature in self.features.items():
            status = self.get_feature_status(feature_id)
            features_status[feature_id] = status
            
            # Accumulate resource usage
            if status and 'current_resource_usage' in status:
                for resource, usage in status['current_resource_usage'].items():
                    total_resource_usage[resource] += usage
        
        return {
            'features': features_status,
            'total_resource_usage': dict(total_resource_usage),
            'current_tier': self.current_resource_tier.value,
            'auto_scaling_enabled': self.auto_scaling_enabled,
            'scaling_sensitivity': self.scaling_sensitivity,
            'scaling_events_count': len(self.scaling_history)
        }
    
    def get_scaling_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get scaling history for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_events = [
            event.to_dict() for event in self.scaling_history
            if event.timestamp >= cutoff_time
        ]
        
        return recent_events
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Get suggestions for manual optimization"""
        suggestions = []
        
        # Analyze recent scaling events
        recent_events = self.get_scaling_history(hours=1)
        
        # Find frequently degraded features
        degraded_features = defaultdict(int)
        for event in recent_events:
            if event['direction'] == 'degrade':
                degraded_features[event['feature_id']] += 1
        
        for feature_id, count in degraded_features.items():
            if count >= 3:  # Degraded 3+ times in past hour
                feature = self.features.get(feature_id)
                if feature:
                    suggestions.append({
                        'type': 'frequently_degraded',
                        'feature_id': feature_id,
                        'description': f"Feature '{feature_id}' has been degraded {count} times in the past hour",
                        'suggestion': "Consider permanently reducing this feature's priority or quality",
                        'user_priority': feature.user_priority,
                        'current_quality': feature.quality_level
                    })
        
        # Find resource-heavy features
        for feature_id, feature in self.features.items():
            scaler = self.scalers.get(feature.category)
            if scaler:
                usage = scaler.get_current_resource_usage(feature)
                if usage.get('cpu', 0) > 30 or usage.get('gpu', 0) > 40:
                    suggestions.append({
                        'type': 'resource_heavy',
                        'feature_id': feature_id,
                        'description': f"Feature '{feature_id}' is using significant resources",
                        'suggestion': "Consider reducing quality or disabling if not essential",
                        'resource_usage': usage,
                        'user_priority': feature.user_priority
                    })
        
        return suggestions

# Global feature scaling system
feature_scaler = FeatureScalingSystem()

if __name__ == "__main__":
    # Demo usage
    async def scaling_callback(event: ScalingEvent):
        print(f"Feature {event.feature_id} scaled {event.direction.value}: "
              f"{event.old_quality:.2f} -> {event.new_quality:.2f}")
    
    async def main():
        # Add callback
        feature_scaler.add_scaling_callback(scaling_callback)
        
        # Simulate resource tier changes
        print("Initial state:")
        status = feature_scaler.get_all_features_status()
        print(json.dumps(status, indent=2))
        
        print("\nSimulating resource pressure (degrading to LOW tier)...")
        await feature_scaler.update_resource_tier(ResourceTier.LOW, "system_pressure")
        
        await asyncio.sleep(1)
        
        print("\nResource pressure relieved (upgrading to HIGH tier)...")
        await feature_scaler.update_resource_tier(ResourceTier.HIGH, "pressure_relief")
        
        await asyncio.sleep(1)
        
        print("\nFinal state:")
        status = feature_scaler.get_all_features_status()
        print(json.dumps(status, indent=2))
        
        print("\nScaling history:")
        history = feature_scaler.get_scaling_history(hours=1)
        for event in history[-5:]:  # Last 5 events
            print(f"  {event['timestamp']}: {event['feature_id']} {event['direction']} "
                  f"({event['trigger_reason']})")
        
        print("\nOptimization suggestions:")
        suggestions = feature_scaler.get_optimization_suggestions()
        for suggestion in suggestions:
            print(f"  - {suggestion['description']}")
            print(f"    {suggestion['suggestion']}")
    
    asyncio.run(main())