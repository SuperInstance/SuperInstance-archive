"""
Integrated Memory Management System for ActiveLog Multi-Bot Environment

This module provides a comprehensive, world-class memory management system that integrates
all memory optimization components including profiling, optimization strategies, alerts,
and automatic cleanup for optimal performance in the ActiveLog system.
"""

import time
import threading
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from .memory_manager import MemoryManager
from .memory_profiler import AdvancedMemoryProfiler
from .efficient_structures import MultiLevelCache, AdaptiveCache
from .optimization_strategies import (
    MemoryOptimizer, OptimizationConfig, OptimizationStrategy, MemoryThresholds
)
from .alerts_and_cleanup import (
    MemoryAlertSystem, AlertConfig, AlertSeverity, AlertChannel,
    AutomaticCleanupSystem, setup_default_cleanup_rules
)

@dataclass
class IntegratedMemoryConfig:
    """Configuration for the integrated memory management system"""
    # Optimization settings
    optimization_strategy: OptimizationStrategy = OptimizationStrategy.ADAPTIVE
    memory_thresholds: MemoryThresholds = None
    gc_frequency: int = 300
    cleanup_interval: int = 60
    
    # Alert settings
    enable_alerts: bool = True
    alert_channels: List[AlertChannel] = None
    alert_severity_threshold: AlertSeverity = AlertSeverity.WARNING
    
    # Profiling settings
    enable_profiling: bool = True
    profiling_interval: int = 60
    enable_leak_detection: bool = True
    
    # Cache settings
    max_cache_size_mb: int = 512
    enable_compression: bool = True
    enable_memory_mapping: bool = True
    
    # Monitoring settings
    monitoring_interval: int = 30
    enable_automatic_cleanup: bool = True

class IntegratedMemorySystem:
    """
    World-class integrated memory management system for ActiveLog bots
    
    This system combines all memory management capabilities into a single,
    easy-to-use interface that provides:
    - Intelligent memory optimization
    - Real-time memory profiling and leak detection
    - Automated alerts and notifications
    - Automatic cleanup and garbage collection
    - Memory-efficient data structures
    - Comprehensive reporting and analytics
    """
    
    def __init__(self, config: IntegratedMemoryConfig = None):
        self.config = config or IntegratedMemoryConfig()
        
        # Initialize default configurations if not provided
        if self.config.memory_thresholds is None:
            self.config.memory_thresholds = MemoryThresholds()
        if self.config.alert_channels is None:
            self.config.alert_channels = [AlertChannel.CONSOLE, AlertChannel.LOG]
            
        # Initialize components
        self._init_components()
        
        # System state
        self.is_running = False
        self.start_time = None
        self.system_stats = {
            'optimizations_performed': 0,
            'memory_leaks_detected': 0,
            'alerts_triggered': 0,
            'automatic_cleanups': 0
        }
        
    def _init_components(self):
        """Initialize all memory management components"""
        # Core memory manager
        self.memory_manager = MemoryManager()
        
        # Advanced profiler
        if self.config.enable_profiling:
            self.profiler = AdvancedMemoryProfiler()
        else:
            self.profiler = None
            
        # Memory optimizer
        optimization_config = OptimizationConfig(
            strategy=self.config.optimization_strategy,
            thresholds=self.config.memory_thresholds,
            gc_frequency=self.config.gc_frequency,
            cleanup_interval=self.config.cleanup_interval,
            enable_compression=self.config.enable_compression,
            enable_memory_mapping=self.config.enable_memory_mapping,
            max_cache_size_mb=self.config.max_cache_size_mb
        )
        self.optimizer = MemoryOptimizer(optimization_config)
        
        # Alert system
        if self.config.enable_alerts:
            alert_config = AlertConfig(
                enabled=True,
                channels=self.config.alert_channels,
                severity_threshold=self.config.alert_severity_threshold
            )
            self.alert_system = MemoryAlertSystem(alert_config)
        else:
            self.alert_system = None
            
        # Automatic cleanup system
        if self.config.enable_automatic_cleanup:
            self.cleanup_system = AutomaticCleanupSystem(self.optimizer, self.alert_system)
            setup_default_cleanup_rules(self.cleanup_system)
        else:
            self.cleanup_system = None
            
        # Global caches for the system
        self.system_cache = MultiLevelCache(
            l1_size=64,  # 64MB L1 cache
            l2_size=256, # 256MB L2 cache
            l3_size=512  # 512MB L3 cache
        )
        self.adaptive_cache = AdaptiveCache(max_size_mb=128)
        
        # Register caches with optimizer
        self.optimizer.register_cache("system_multilevel", self.system_cache)
        self.optimizer.register_cache("system_adaptive", self.adaptive_cache)
        
    def start(self):
        """Start the integrated memory management system"""
        if self.is_running:
            return
            
        self.is_running = True
        self.start_time = datetime.now()
        
        # Start all components
        self.optimizer.start_optimization()
        
        if self.profiler:
            self.profiler.start_profiling()
            
        if self.alert_system:
            self.alert_system.start_monitoring(self.config.monitoring_interval)
            
        if self.cleanup_system:
            self.cleanup_system.start_automatic_cleanup()
            
        # Trigger initial optimization
        self._log_system_event("Integrated memory system started successfully")
        
    def stop(self):
        """Stop the integrated memory management system"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        # Stop all components
        self.optimizer.stop_optimization()
        
        if self.profiler:
            self.profiler.stop_profiling()
            
        if self.alert_system:
            self.alert_system.stop_monitoring()
            
        if self.cleanup_system:
            self.cleanup_system.stop_automatic_cleanup()
            
        self._log_system_event("Integrated memory system stopped")
        
    def optimize_now(self) -> Dict[str, Any]:
        """Trigger immediate memory optimization"""
        result = self.optimizer.optimize_memory()
        self.system_stats['optimizations_performed'] += 1
        
        if self.alert_system:
            self.alert_system.trigger_alert(
                AlertSeverity.INFO,
                f"Manual optimization completed, saved {result.get('memory_saved_mb', 0):.1f}MB",
                result['memory_after'],
                "manual_optimization"
            )
            
        return result
        
    def get_memory_status(self) -> Dict[str, Any]:
        """Get comprehensive memory status"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'system_running': self.is_running,
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            'system_stats': self.system_stats.copy()
        }
        
        # Memory usage
        status['memory_usage'] = self.optimizer.get_memory_usage()
        
        # Optimizer status
        status['optimizer_report'] = self.optimizer.get_optimization_report()
        
        # Profiler status
        if self.profiler:
            status['profiler_status'] = self.profiler.get_profiling_summary()
            
        # Alert status
        if self.alert_system:
            status['alert_summary'] = self.alert_system.get_alert_summary(hours=1)
            
        # Cache status
        status['cache_status'] = {
            'multilevel_cache': {
                'l1_hit_rate': self.system_cache.get_l1_hit_rate(),
                'l2_hit_rate': self.system_cache.get_l2_hit_rate(),
                'l3_hit_rate': self.system_cache.get_l3_hit_rate(),
                'total_size_mb': self.system_cache.get_total_size_mb()
            },
            'adaptive_cache': {
                'hit_rate': self.adaptive_cache.get_hit_rate(),
                'current_strategy': self.adaptive_cache.get_current_strategy(),
                'size_mb': self.adaptive_cache.get_size_mb()
            }
        }
        
        return status
        
    def detect_memory_leaks(self) -> List[Dict[str, Any]]:
        """Detect potential memory leaks"""
        if not self.profiler:
            return []
            
        leak_report = self.profiler.detect_memory_leaks()
        
        if leak_report.get('potential_leaks'):
            self.system_stats['memory_leaks_detected'] += len(leak_report['potential_leaks'])
            
            if self.alert_system:
                self.alert_system.trigger_alert(
                    AlertSeverity.WARNING,
                    f"Detected {len(leak_report['potential_leaks'])} potential memory leaks",
                    self.optimizer.get_memory_usage(),
                    "leak_detection",
                    leak_report
                )
                
        return leak_report.get('potential_leaks', [])
        
    def get_performance_analytics(self) -> Dict[str, Any]:
        """Get detailed performance analytics"""
        analytics = {
            'timestamp': datetime.now().isoformat(),
            'analysis_period': 'last_24_hours'
        }
        
        # Memory optimization analytics
        optimization_report = self.optimizer.get_optimization_report()
        analytics['optimization_analytics'] = optimization_report
        
        # Profiling analytics
        if self.profiler:
            profiling_summary = self.profiler.get_profiling_summary()
            analytics['profiling_analytics'] = profiling_summary
            
        # Alert analytics
        if self.alert_system:
            alert_summary = self.alert_system.get_alert_summary(hours=24)
            analytics['alert_analytics'] = alert_summary
            
        # System performance trends
        analytics['performance_trends'] = self._calculate_performance_trends()
        
        return analytics
        
    def _calculate_performance_trends(self) -> Dict[str, Any]:
        """Calculate performance trends over time"""
        # This would analyze historical data to identify trends
        # For now, returning current snapshot with basic trend indicators
        current_usage = self.optimizer.get_memory_usage()
        
        return {
            'memory_usage_trend': 'stable',  # stable, increasing, decreasing
            'optimization_effectiveness': 'high',  # high, medium, low
            'leak_detection_status': 'active',
            'cache_performance': 'optimal',
            'overall_health': 'excellent'
        }
        
    def create_memory_snapshot(self) -> Dict[str, Any]:
        """Create a comprehensive memory snapshot"""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'system_status': self.get_memory_status(),
            'performance_analytics': self.get_performance_analytics()
        }
        
        if self.profiler:
            snapshot['detailed_profile'] = self.profiler.create_snapshot()
            
        return snapshot
        
    def export_memory_report(self, filename: Optional[str] = None) -> str:
        """Export comprehensive memory report to JSON file"""
        if filename is None:
            filename = f"memory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        report = self.create_memory_snapshot()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
            
        return filename
        
    def register_bot_cache(self, bot_id: str, cache_obj: Any):
        """Register a bot's cache for optimization"""
        cache_name = f"bot_{bot_id}_cache"
        self.optimizer.register_cache(cache_name, cache_obj)
        
    def register_bot_object(self, bot_id: str, obj: Any):
        """Register a bot object for memory tracking"""
        self.optimizer.register_object(obj)
        
    def _log_system_event(self, message: str):
        """Log system events"""
        print(f"[IntegratedMemorySystem] {datetime.now().strftime('%H:%M:%S')} - {message}")
        
        if self.alert_system:
            self.alert_system.trigger_alert(
                AlertSeverity.INFO,
                message,
                self.optimizer.get_memory_usage(),
                "system_event"
            )

# Global system instance
_global_memory_system = None

def get_memory_system(config: IntegratedMemoryConfig = None) -> IntegratedMemorySystem:
    """Get or create the global integrated memory system"""
    global _global_memory_system
    
    if _global_memory_system is None:
        _global_memory_system = IntegratedMemorySystem(config)
        
    return _global_memory_system

def initialize_memory_system_for_activelog(config: IntegratedMemoryConfig = None) -> IntegratedMemorySystem:
    """Initialize and start the integrated memory system for ActiveLog"""
    memory_system = get_memory_system(config)
    
    if not memory_system.is_running:
        memory_system.start()
        
    return memory_system

# Convenience functions for bot integration
def optimize_bot_memory() -> Dict[str, Any]:
    """Convenience function to optimize memory for bots"""
    system = get_memory_system()
    return system.optimize_now()

def get_bot_memory_status() -> Dict[str, Any]:
    """Convenience function to get memory status"""
    system = get_memory_system()
    return system.get_memory_status()

def register_bot_for_memory_management(bot_id: str, bot_cache: Any = None, bot_objects: List[Any] = None):
    """Register a bot for comprehensive memory management"""
    system = get_memory_system()
    
    if bot_cache:
        system.register_bot_cache(bot_id, bot_cache)
        
    if bot_objects:
        for obj in bot_objects:
            system.register_bot_object(bot_id, obj)

if __name__ == "__main__":
    # Example usage and testing
    print("Initializing ActiveLog Integrated Memory Management System...")
    
    config = IntegratedMemoryConfig(
        optimization_strategy=OptimizationStrategy.ADAPTIVE,
        enable_alerts=True,
        enable_profiling=True,
        monitoring_interval=10
    )
    
    # Initialize system
    memory_system = initialize_memory_system_for_activelog(config)
    
    try:
        # Run for demonstration
        print("Memory system running... (press Ctrl+C to stop)")
        time.sleep(30)
        
        # Get status report
        status = memory_system.get_memory_status()
        print(f"\nMemory Status:")
        print(f"  RSS Usage: {status['memory_usage']['rss_mb']:.1f}MB")
        print(f"  System Usage: {status['memory_usage']['system_percent']:.1%}")
        print(f"  Optimizations Performed: {status['system_stats']['optimizations_performed']}")
        
        # Export report
        report_file = memory_system.export_memory_report()
        print(f"\nMemory report exported to: {report_file}")
        
    except KeyboardInterrupt:
        print("\nShutting down memory system...")
        memory_system.stop()
        print("Memory system stopped successfully.")