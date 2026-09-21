"""
Battery-efficient sync and operation strategies for mobile clients

Implements intelligent strategies to minimize battery drain:
- Connection-aware sync scheduling
- Battery level monitoring
- Background task optimization
- Power-efficient data structures
- Adaptive sync intervals
"""

import asyncio
import logging
import time
import math
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import json

from ..config import settings
from ..protobuf.generated.mobile_pb import (
    BatteryInfo, ConnectionType, PerformanceTier, SyncMode,
    BatteryImpact, SyncRequest, SyncResponse
)

logger = logging.getLogger(__name__)

class PowerMode(Enum):
    """Power management modes"""
    PERFORMANCE = "performance"      # Maximum features, higher power usage
    BALANCED = "balanced"           # Default mode, balanced power usage
    POWER_SAVER = "power_saver"     # Reduced features, minimal power usage
    CRITICAL = "critical"           # Emergency mode, essential functions only

class SyncStrategy(Enum):
    """Sync strategy types"""
    IMMEDIATE = "immediate"         # Sync immediately
    BATCHED = "batched"            # Batch multiple operations
    SCHEDULED = "scheduled"        # Sync at optimal times
    ON_DEMAND = "on_demand"        # Only sync when requested
    DISABLED = "disabled"          # No background sync

@dataclass
class BatteryProfile:
    """Battery usage profile for operations"""
    level: int                      # Battery level 0-100
    is_charging: bool               # Is device charging
    low_power_mode: bool           # Is low power mode enabled
    temperature: float             # Battery temperature
    estimated_time_remaining: int   # Minutes of usage remaining
    power_mode: PowerMode          # Current power management mode
    last_updated: datetime         # When profile was last updated

@dataclass
class ConnectionProfile:
    """Network connection profile"""
    type: ConnectionType.Type       # Connection type
    speed_mbps: float              # Connection speed
    is_metered: bool               # Is connection metered
    signal_strength: int           # Signal strength 0-100
    latency_ms: int               # Network latency
    quality_score: float          # Overall connection quality 0-1

@dataclass
class SyncPlan:
    """Optimized sync execution plan"""
    strategy: SyncStrategy
    interval_seconds: int
    max_items_per_batch: int
    use_compression: bool
    priority_files_only: bool
    estimated_battery_cost: float  # Estimated battery cost 0-1
    estimated_duration_ms: int
    next_sync_time: Optional[datetime]

class BatteryOptimizer:
    """Battery-efficient operation optimizer"""
    
    def __init__(self):
        self.device_profiles: Dict[str, BatteryProfile] = {}
        self.connection_profiles: Dict[str, ConnectionProfile] = {}
        self.sync_history: Dict[str, List[Dict]] = {}
        self.power_thresholds = self._init_power_thresholds()
        self.sync_intervals = self._init_sync_intervals()
        
    def _init_power_thresholds(self) -> Dict[str, Dict]:
        """Initialize battery level thresholds for different modes"""
        return {
            'critical': {'max_level': 5, 'operations': ['emergency_sync']},
            'power_saver': {'max_level': 20, 'operations': ['essential_sync', 'notifications']},
            'balanced': {'max_level': 50, 'operations': ['normal_sync', 'background_tasks']},
            'performance': {'min_level': 30, 'operations': ['full_sync', 'media_processing']}
        }
    
    def _init_sync_intervals(self) -> Dict[PowerMode, Dict[str, int]]:
        """Initialize sync intervals by power mode (in seconds)"""
        return {
            PowerMode.PERFORMANCE: {
                'immediate': 0,
                'frequent': 30,
                'normal': 300,      # 5 minutes
                'background': 900   # 15 minutes
            },
            PowerMode.BALANCED: {
                'immediate': 0,
                'frequent': 120,    # 2 minutes
                'normal': 600,      # 10 minutes
                'background': 1800  # 30 minutes
            },
            PowerMode.POWER_SAVER: {
                'immediate': 0,
                'frequent': 300,    # 5 minutes
                'normal': 1800,     # 30 minutes
                'background': 3600  # 1 hour
            },
            PowerMode.CRITICAL: {
                'immediate': 0,
                'frequent': 1800,   # 30 minutes
                'normal': 7200,     # 2 hours
                'background': 21600 # 6 hours
            }
        }
    
    async def update_battery_profile(self, device_id: str, battery_info: BatteryInfo):
        """Update device battery profile"""
        
        # Determine power mode based on battery state
        power_mode = self._determine_power_mode(battery_info)
        
        # Estimate remaining time (simplified calculation)
        estimated_time = self._estimate_battery_life(battery_info, power_mode)
        
        profile = BatteryProfile(
            level=battery_info.level,
            is_charging=battery_info.is_charging,
            low_power_mode=battery_info.low_power_mode,
            temperature=battery_info.temperature,
            estimated_time_remaining=estimated_time,
            power_mode=power_mode,
            last_updated=datetime.utcnow()
        )
        
        self.device_profiles[device_id] = profile
        
        logger.info(f"Updated battery profile for {device_id}: "
                   f"{battery_info.level}%, {power_mode.value} mode")
    
    async def update_connection_profile(self, device_id: str, connection: ConnectionType):
        """Update device connection profile"""
        
        # Calculate quality score based on multiple factors
        quality_score = self._calculate_connection_quality(connection)
        
        profile = ConnectionProfile(
            type=connection.type,
            speed_mbps=connection.speed_mbps,
            is_metered=connection.is_metered,
            signal_strength=connection.signal_strength,
            latency_ms=self._estimate_latency(connection),
            quality_score=quality_score
        )
        
        self.connection_profiles[device_id] = profile
        
        logger.info(f"Updated connection profile for {device_id}: "
                   f"{connection.type}, {connection.speed_mbps}Mbps, quality: {quality_score:.2f}")
    
    def _determine_power_mode(self, battery_info: BatteryInfo) -> PowerMode:
        """Determine optimal power mode based on battery state"""
        
        if battery_info.level <= 5:
            return PowerMode.CRITICAL
        elif battery_info.low_power_mode or battery_info.level <= 20:
            return PowerMode.POWER_SAVER
        elif battery_info.is_charging or battery_info.level >= 80:
            return PowerMode.PERFORMANCE
        else:
            return PowerMode.BALANCED
    
    def _estimate_battery_life(self, battery_info: BatteryInfo, power_mode: PowerMode) -> int:
        """Estimate remaining battery life in minutes"""
        
        if battery_info.is_charging:
            return -1  # Charging, no time limit
        
        # Base drain rates per hour by power mode
        drain_rates = {
            PowerMode.PERFORMANCE: 15,   # 15% per hour
            PowerMode.BALANCED: 10,      # 10% per hour
            PowerMode.POWER_SAVER: 5,    # 5% per hour
            PowerMode.CRITICAL: 2        # 2% per hour
        }
        
        drain_rate = drain_rates.get(power_mode, 10)
        
        # Adjust for temperature (higher temp = higher drain)
        if battery_info.temperature > 35:  # Celsius
            drain_rate *= 1.2
        
        # Calculate remaining time
        remaining_hours = battery_info.level / drain_rate
        return int(remaining_hours * 60)  # Convert to minutes
    
    def _calculate_connection_quality(self, connection: ConnectionType) -> float:
        """Calculate connection quality score (0-1)"""
        
        speed_score = min(connection.speed_mbps / 50.0, 1.0)  # Normalize to 50Mbps
        signal_score = connection.signal_strength / 100.0
        
        # Penalty for metered connections
        metered_penalty = 0.3 if connection.is_metered else 0.0
        
        # Type-based baseline scores
        type_scores = {
            ConnectionType.Type.WIFI: 0.9,
            ConnectionType.Type.ETHERNET: 1.0,
            ConnectionType.Type.CELLULAR_5G: 0.8,
            ConnectionType.Type.CELLULAR_4G: 0.6,
            ConnectionType.Type.CELLULAR_3G: 0.4,
            ConnectionType.Type.CELLULAR_2G: 0.2,
            ConnectionType.Type.UNKNOWN: 0.3
        }
        
        base_score = type_scores.get(connection.type, 0.3)
        
        # Weighted combination
        quality = (base_score * 0.4 + speed_score * 0.4 + signal_score * 0.2) - metered_penalty
        
        return max(0.0, min(1.0, quality))
    
    def _estimate_latency(self, connection: ConnectionType) -> int:
        """Estimate network latency based on connection type"""
        
        latency_estimates = {
            ConnectionType.Type.ETHERNET: 5,
            ConnectionType.Type.WIFI: 20,
            ConnectionType.Type.CELLULAR_5G: 30,
            ConnectionType.Type.CELLULAR_4G: 60,
            ConnectionType.Type.CELLULAR_3G: 150,
            ConnectionType.Type.CELLULAR_2G: 500,
            ConnectionType.Type.UNKNOWN: 100
        }
        
        base_latency = latency_estimates.get(connection.type, 100)
        
        # Adjust based on signal strength
        if connection.signal_strength < 50:
            base_latency *= 1.5
        elif connection.signal_strength < 25:
            base_latency *= 2.0
        
        return int(base_latency)
    
    async def create_sync_plan(self, device_id: str, sync_request: SyncRequest) -> SyncPlan:
        """Create optimized sync plan for device"""
        
        battery_profile = self.device_profiles.get(device_id)
        connection_profile = self.connection_profiles.get(device_id)
        
        if not battery_profile or not connection_profile:
            # Use default conservative plan
            return SyncPlan(
                strategy=SyncStrategy.SCHEDULED,
                interval_seconds=1800,
                max_items_per_batch=10,
                use_compression=True,
                priority_files_only=True,
                estimated_battery_cost=0.1,
                estimated_duration_ms=5000,
                next_sync_time=datetime.utcnow() + timedelta(minutes=30)
            )
        
        # Determine sync strategy based on conditions
        strategy = self._select_sync_strategy(battery_profile, connection_profile)
        
        # Calculate optimal parameters
        interval = self._calculate_sync_interval(strategy, battery_profile, connection_profile)
        batch_size = self._calculate_batch_size(battery_profile, connection_profile)
        
        # Estimate costs
        battery_cost = self._estimate_battery_cost(strategy, batch_size, connection_profile)
        duration = self._estimate_sync_duration(batch_size, connection_profile)
        
        # Calculate next sync time
        next_sync = self._calculate_next_sync_time(strategy, interval, battery_profile)
        
        plan = SyncPlan(
            strategy=strategy,
            interval_seconds=interval,
            max_items_per_batch=batch_size,
            use_compression=connection_profile.is_metered or connection_profile.quality_score < 0.5,
            priority_files_only=battery_profile.power_mode in [PowerMode.POWER_SAVER, PowerMode.CRITICAL],
            estimated_battery_cost=battery_cost,
            estimated_duration_ms=duration,
            next_sync_time=next_sync
        )
        
        logger.info(f"Created sync plan for {device_id}: {strategy.value}, "
                   f"interval: {interval}s, batch: {batch_size}, cost: {battery_cost:.3f}")
        
        return plan
    
    def _select_sync_strategy(self, 
                            battery_profile: BatteryProfile,
                            connection_profile: ConnectionProfile) -> SyncStrategy:
        """Select optimal sync strategy"""
        
        # Critical battery - minimal sync
        if battery_profile.power_mode == PowerMode.CRITICAL:
            return SyncStrategy.ON_DEMAND
        
        # Power saver mode - scheduled sync only
        if battery_profile.power_mode == PowerMode.POWER_SAVER:
            return SyncStrategy.SCHEDULED
        
        # Poor connection - batch operations
        if connection_profile.quality_score < 0.3:
            return SyncStrategy.BATCHED
        
        # Good conditions - immediate sync
        if (battery_profile.power_mode == PowerMode.PERFORMANCE and 
            connection_profile.quality_score > 0.7):
            return SyncStrategy.IMMEDIATE
        
        # Default to batched sync
        return SyncStrategy.BATCHED
    
    def _calculate_sync_interval(self,
                               strategy: SyncStrategy,
                               battery_profile: BatteryProfile,
                               connection_profile: ConnectionProfile) -> int:
        """Calculate optimal sync interval"""
        
        if strategy == SyncStrategy.IMMEDIATE:
            return 0
        
        base_intervals = self.sync_intervals[battery_profile.power_mode]
        
        if strategy == SyncStrategy.BATCHED:
            interval = base_intervals['frequent']
        elif strategy == SyncStrategy.SCHEDULED:
            interval = base_intervals['normal']
        else:  # ON_DEMAND
            interval = base_intervals['background']
        
        # Adjust for connection quality
        if connection_profile.quality_score < 0.5:
            interval *= 2  # Slower sync on poor connections
        elif connection_profile.is_metered:
            interval *= 1.5  # Less frequent on metered connections
        
        return int(interval)
    
    def _calculate_batch_size(self,
                            battery_profile: BatteryProfile,
                            connection_profile: ConnectionProfile) -> int:
        """Calculate optimal batch size for operations"""
        
        # Base batch sizes by power mode
        base_sizes = {
            PowerMode.PERFORMANCE: 100,
            PowerMode.BALANCED: 50,
            PowerMode.POWER_SAVER: 20,
            PowerMode.CRITICAL: 5
        }
        
        batch_size = base_sizes[battery_profile.power_mode]
        
        # Adjust for connection quality
        if connection_profile.quality_score < 0.3:
            batch_size = max(5, batch_size // 4)  # Smaller batches on poor connections
        elif connection_profile.is_metered:
            batch_size = max(10, batch_size // 2)  # Smaller batches on metered
        elif connection_profile.quality_score > 0.8:
            batch_size = min(200, int(batch_size * 1.5))  # Larger batches on good connections
        
        return batch_size
    
    def _estimate_battery_cost(self,
                             strategy: SyncStrategy,
                             batch_size: int,
                             connection_profile: ConnectionProfile) -> float:
        """Estimate battery cost for sync operation (0-1 scale)"""
        
        # Base costs by strategy
        strategy_costs = {
            SyncStrategy.IMMEDIATE: 0.05,
            SyncStrategy.BATCHED: 0.03,
            SyncStrategy.SCHEDULED: 0.02,
            SyncStrategy.ON_DEMAND: 0.01,
            SyncStrategy.DISABLED: 0.0
        }
        
        base_cost = strategy_costs[strategy]
        
        # Scale by batch size
        size_multiplier = 1.0 + (batch_size - 20) / 200.0  # Normalized around 20 items
        
        # Connection type multipliers
        connection_multipliers = {
            ConnectionType.Type.WIFI: 0.8,
            ConnectionType.Type.ETHERNET: 0.7,
            ConnectionType.Type.CELLULAR_5G: 1.2,
            ConnectionType.Type.CELLULAR_4G: 1.5,
            ConnectionType.Type.CELLULAR_3G: 2.0,
            ConnectionType.Type.CELLULAR_2G: 3.0,
            ConnectionType.Type.UNKNOWN: 1.0
        }
        
        connection_multiplier = connection_multipliers.get(connection_profile.type, 1.0)
        
        # Poor signal increases cost
        if connection_profile.signal_strength < 50:
            connection_multiplier *= 1.3
        
        total_cost = base_cost * size_multiplier * connection_multiplier
        
        return min(1.0, max(0.0, total_cost))
    
    def _estimate_sync_duration(self,
                              batch_size: int,
                              connection_profile: ConnectionProfile) -> int:
        """Estimate sync duration in milliseconds"""
        
        # Base time per item in milliseconds
        base_time_per_item = 100
        
        # Connection speed factor
        speed_factor = max(0.1, min(2.0, 10.0 / max(connection_profile.speed_mbps, 0.1)))
        
        # Latency overhead
        latency_overhead = connection_profile.latency_ms * batch_size * 0.1
        
        # Calculate total time
        processing_time = batch_size * base_time_per_item * speed_factor
        total_time = processing_time + latency_overhead
        
        return int(total_time)
    
    def _calculate_next_sync_time(self,
                                strategy: SyncStrategy,
                                interval_seconds: int,
                                battery_profile: BatteryProfile) -> Optional[datetime]:
        """Calculate when next sync should occur"""
        
        if strategy == SyncStrategy.IMMEDIATE:
            return None  # No scheduled time for immediate sync
        
        if strategy == SyncStrategy.ON_DEMAND:
            return None  # Only sync when requested
        
        base_next_time = datetime.utcnow() + timedelta(seconds=interval_seconds)
        
        # Adjust for charging state
        if battery_profile.is_charging:
            # Sync more frequently when charging
            base_next_time = datetime.utcnow() + timedelta(seconds=max(60, interval_seconds // 2))
        
        # Avoid syncing during likely sleep hours (11 PM - 6 AM local time)
        hour = base_next_time.hour
        if 23 <= hour or hour <= 6:
            # Delay until 6 AM
            next_morning = base_next_time.replace(hour=6, minute=0, second=0, microsecond=0)
            if hour <= 6:
                # Same day
                base_next_time = next_morning
            else:
                # Next day
                base_next_time = next_morning + timedelta(days=1)
        
        return base_next_time
    
    async def record_sync_completion(self,
                                   device_id: str,
                                   duration_ms: int,
                                   items_synced: int,
                                   bytes_transferred: int,
                                   battery_cost: float):
        """Record sync completion for learning"""
        
        sync_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'duration_ms': duration_ms,
            'items_synced': items_synced,
            'bytes_transferred': bytes_transferred,
            'battery_cost': battery_cost,
            'battery_level_before': self.device_profiles.get(device_id, {}).level if device_id in self.device_profiles else None,
            'connection_quality': self.connection_profiles.get(device_id, {}).quality_score if device_id in self.connection_profiles else None
        }
        
        if device_id not in self.sync_history:
            self.sync_history[device_id] = []
        
        self.sync_history[device_id].append(sync_record)
        
        # Keep only last 100 records per device
        if len(self.sync_history[device_id]) > 100:
            self.sync_history[device_id] = self.sync_history[device_id][-100:]
        
        logger.info(f"Recorded sync completion for {device_id}: "
                   f"{items_synced} items, {duration_ms}ms, cost: {battery_cost:.3f}")
    
    def should_defer_sync(self, device_id: str, urgency: str = "normal") -> Tuple[bool, str]:
        """Check if sync should be deferred based on current conditions"""
        
        battery_profile = self.device_profiles.get(device_id)
        connection_profile = self.connection_profiles.get(device_id)
        
        if not battery_profile:
            return False, "No battery profile available"
        
        # Never defer urgent syncs
        if urgency == "urgent":
            return False, "Urgent sync requested"
        
        # Defer in critical battery mode
        if battery_profile.power_mode == PowerMode.CRITICAL and urgency != "urgent":
            return True, f"Critical battery level: {battery_profile.level}%"
        
        # Defer on very poor connection for non-priority syncs
        if connection_profile and connection_profile.quality_score < 0.2 and urgency == "background":
            return True, f"Poor connection quality: {connection_profile.quality_score:.2f}"
        
        # Defer if charging and can wait for better conditions
        if (battery_profile.is_charging and battery_profile.level < 30 and 
            urgency == "background"):
            return True, f"Charging at low battery: {battery_profile.level}%"
        
        return False, "Conditions suitable for sync"
    
    def get_battery_impact_summary(self, device_id: str) -> BatteryImpact:
        """Get battery impact summary for device"""
        
        battery_profile = self.device_profiles.get(device_id)
        sync_history = self.sync_history.get(device_id, [])
        
        if not battery_profile:
            impact = BatteryImpact()
            impact.level = BatteryImpact.Level.IMPACT_UNKNOWN
            impact.estimated_drain_percent = 0
            impact.optimization_hint = "No battery data available"
            return impact
        
        # Calculate recent battery impact
        recent_syncs = [s for s in sync_history[-10:] if 'battery_cost' in s]
        avg_cost = sum(s['battery_cost'] for s in recent_syncs) / len(recent_syncs) if recent_syncs else 0.1
        
        # Determine impact level
        if avg_cost < 0.02:
            level = BatteryImpact.Level.IMPACT_MINIMAL
            hint = "Optimal sync strategy active"
        elif avg_cost < 0.05:
            level = BatteryImpact.Level.IMPACT_LOW
            hint = "Efficient sync with minor battery impact"
        elif avg_cost < 0.1:
            level = BatteryImpact.Level.IMPACT_MEDIUM
            hint = "Moderate battery usage, consider reducing sync frequency"
        else:
            level = BatteryImpact.Level.IMPACT_HIGH
            hint = "High battery impact, sync optimization recommended"
        
        # Estimate drain percentage
        estimated_drain = min(10, int(avg_cost * 100))
        
        # Add specific hints based on current state
        if battery_profile.power_mode == PowerMode.CRITICAL:
            hint = "Critical battery - minimal sync only"
        elif battery_profile.low_power_mode:
            hint = "Low power mode active - reduced background activity"
        elif battery_profile.is_charging:
            hint = "Device charging - opportunistic sync enabled"
        
        impact = BatteryImpact()
        impact.level = level
        impact.estimated_drain_percent = estimated_drain
        impact.optimization_hint = hint
        
        return impact

# Global battery optimizer instance
battery_optimizer = BatteryOptimizer()

async def optimize_for_battery(device_id: str, 
                             battery_info: BatteryInfo,
                             connection: ConnectionType) -> SyncPlan:
    """
    Create battery-optimized operation plan
    
    Args:
        device_id: Unique device identifier
        battery_info: Current battery status
        connection: Current connection info
        
    Returns:
        Optimized sync plan
    """
    
    # Update profiles
    await battery_optimizer.update_battery_profile(device_id, battery_info)
    await battery_optimizer.update_connection_profile(device_id, connection)
    
    # Create dummy sync request for planning
    sync_request = SyncRequest()
    sync_request.sync_token = ""
    sync_request.mode = SyncMode.SYNC_MODE_INCREMENTAL
    
    # Generate optimized plan
    return await battery_optimizer.create_sync_plan(device_id, sync_request)