# Memory Optimization System for Multi-Bot Environment

"""
World-Class Memory Management System for ActiveLog

This module provides a comprehensive memory management solution designed specifically
for the ActiveLog multi-bot environment, featuring:

- Intelligent memory optimization with adaptive strategies
- Real-time memory profiling and leak detection
- Memory-efficient data structures and caching
- Automated alerts and cleanup systems
- Integrated monitoring and analytics

Usage:
    from memory import initialize_memory_system_for_activelog
    
    # Initialize the complete system
    memory_system = initialize_memory_system_for_activelog()
    
    # Or use convenience functions
    from memory import optimize_bot_memory, get_bot_memory_status
    
    status = get_bot_memory_status()
    optimize_bot_memory()
"""

# Core memory management components
from .memory_manager import MemoryManager
from .memory_profiler import AdvancedMemoryProfiler

# Memory-efficient data structures
from .efficient_structures import (
    CompactArray, SparseArray, RingBuffer, MemoryMappedDict,
    MultiLevelCache, BloomFilter, AdaptiveCache
)

# Optimization strategies and garbage collection
from .optimization_strategies import (
    MemoryOptimizer, OptimizationConfig, OptimizationStrategy, 
    MemoryThresholds, SmartGarbageCollector, get_memory_optimizer,
    optimize_memory_for_bots
)

# Alert and cleanup systems
from .alerts_and_cleanup import (
    MemoryAlertSystem, AlertConfig, AlertSeverity, AlertChannel,
    AutomaticCleanupSystem, get_alert_system, get_cleanup_system
)

# Security features
from .security import (
    SecurityManager, SecurityConfig, SecurityLevel, AccessLevel,
    SecureMemoryWrapper, create_secure_memory_wrapper
)

# Integrated system (main interface)
from .integrated_memory_system import (
    IntegratedMemorySystem, IntegratedMemoryConfig,
    initialize_memory_system_for_activelog, get_memory_system,
    optimize_bot_memory, get_bot_memory_status,
    register_bot_for_memory_management
)

# Export main interfaces
__all__ = [
    # Main system interface
    'initialize_memory_system_for_activelog',
    'get_memory_system',
    'IntegratedMemorySystem',
    'IntegratedMemoryConfig',
    
    # Convenience functions
    'optimize_bot_memory',
    'get_bot_memory_status', 
    'register_bot_for_memory_management',
    
    # Core components
    'MemoryManager',
    'AdvancedMemoryProfiler',
    'MemoryOptimizer',
    'MemoryAlertSystem',
    'AutomaticCleanupSystem',
    
    # Security components
    'SecurityManager',
    'SecureMemoryWrapper',
    'create_secure_memory_wrapper',
    
    # Data structures
    'CompactArray',
    'SparseArray', 
    'RingBuffer',
    'MemoryMappedDict',
    'MultiLevelCache',
    'BloomFilter',
    'AdaptiveCache',
    
    # Configurations and enums
    'OptimizationConfig',
    'OptimizationStrategy',
    'MemoryThresholds',
    'AlertConfig',
    'AlertSeverity',
    'AlertChannel',
    'SecurityConfig',
    'SecurityLevel',
    'AccessLevel',
]