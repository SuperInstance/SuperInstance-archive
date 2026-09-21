"""
Easy Memory Management for ActiveLog Bots

This module provides the simplest possible interface for world-class memory management.
Just import and call a few functions to get enterprise-grade memory optimization.

Quick Start:
    import memory.easy_memory as memory
    
    # Start memory management (one-time setup)
    memory.start()
    
    # That's it! Your bots now have world-class memory management
    
Advanced Usage:
    # Get memory status
    status = memory.status()
    
    # Force optimization
    memory.optimize()
    
    # Register a bot for tracking
    memory.track_bot("my_bot_id", bot_cache, [bot_objects])
"""

import threading
import time
from typing import Dict, Any, Optional, List

# Import the comprehensive system
from .integrated_memory_system import (
    IntegratedMemorySystem, IntegratedMemoryConfig, 
    OptimizationStrategy, AlertSeverity, AlertChannel
)
from .security import (
    SecurityManager, SecurityConfig, SecurityLevel, AccessLevel,
    SecureMemoryWrapper, create_secure_memory_wrapper
)

# Global system instances
_memory_system: Optional[IntegratedMemorySystem] = None
_security_wrapper: Optional[SecureMemoryWrapper] = None
_admin_session: Optional[str] = None
_system_lock = threading.Lock()

def start(aggressive: bool = False, secure: bool = True) -> bool:
    """
    Start world-class memory management for your bots.
    
    Args:
        aggressive: If True, uses more aggressive optimization (may impact performance)
        secure: If True, enables security features (recommended)
        
    Returns:
        bool: True if started successfully
        
    Example:
        >>> import memory.easy_memory as memory
        >>> memory.start()
        True
        >>> # Your bots now have automatic memory optimization with security!
    """
    global _memory_system, _security_wrapper, _admin_session
    
    with _system_lock:
        if _memory_system is not None and _memory_system.is_running:
            print("Memory management is already running!")
            return True
            
        try:
            # Simple configuration based on user preference
            config = IntegratedMemoryConfig(
                optimization_strategy=OptimizationStrategy.AGGRESSIVE if aggressive else OptimizationStrategy.ADAPTIVE,
                enable_alerts=True,
                alert_channels=[AlertChannel.CONSOLE],  # Simple console output
                alert_severity_threshold=AlertSeverity.WARNING,
                enable_profiling=True,
                monitoring_interval=30,  # Check every 30 seconds
                enable_automatic_cleanup=True
            )
            
            _memory_system = IntegratedMemorySystem(config)
            _memory_system.start()
            
            # Initialize security if requested
            if secure:
                security_config = SecurityConfig(
                    security_level=SecurityLevel.HIGH,
                    enable_encryption=True,
                    enable_audit_logging=True,
                    enable_access_control=True,
                    require_authentication=False  # Simplified for easy use
                )
                
                _security_wrapper = create_secure_memory_wrapper(_memory_system, security_config)
                
                # Create auto-admin session for simplified usage
                _admin_session = _security_wrapper.security_manager.authenticate_user(
                    "system", "activelog_system_key", "127.0.0.1"
                )
                
                print("✅ Secure memory management started!")
                print("   - Automatic optimization: ON")
                print("   - Memory leak detection: ON") 
                print("   - Smart garbage collection: ON")
                print("   - Performance monitoring: ON")
                print("   - Security & encryption: ON")
                print("   - Audit logging: ON")
            else:
                print("✅ Memory management started!")
                print("   - Automatic optimization: ON")
                print("   - Memory leak detection: ON") 
                print("   - Smart garbage collection: ON")
                print("   - Performance monitoring: ON")
                print("   - Security: DISABLED")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start memory management: {e}")
            return False

def stop() -> bool:
    """
    Stop memory management.
    
    Returns:
        bool: True if stopped successfully
    """
    global _memory_system
    
    with _system_lock:
        if _memory_system is None or not _memory_system.is_running:
            print("Memory management is not running.")
            return True
            
        try:
            _memory_system.stop()
            print("✅ Memory management stopped.")
            return True
        except Exception as e:
            print(f"❌ Error stopping memory management: {e}")
            return False

def status() -> Dict[str, Any]:
    """
    Get simple memory status.
    
    Returns:
        dict: Easy-to-read memory status
        
    Example:
        >>> status = memory.status()
        >>> print(f"Memory usage: {status['memory_mb']}MB")
        >>> print(f"System health: {status['health']}")
    """
    if _memory_system is None:
        return {
            'running': False,
            'memory_mb': 0,
            'system_usage': '0%', 
            'health': 'not_started',
            'secure': False,
            'message': 'Call memory.start() first!'
        }
        
    try:
        # Use secure wrapper if available
        if _security_wrapper and _admin_session:
            full_status = _security_wrapper.secure_get_status(_admin_session)
        else:
            full_status = _memory_system.get_memory_status()
        
        # Simplify for easy reading
        memory_usage = full_status['memory_usage']
        
        # Determine health status
        system_percent = memory_usage['system_percent']
        if system_percent < 0.6:
            health = 'excellent'
        elif system_percent < 0.75:
            health = 'good'
        elif system_percent < 0.85:
            health = 'warning' 
        else:
            health = 'critical'
            
        return {
            'running': full_status['system_running'],
            'memory_mb': round(memory_usage['rss_mb'], 1),
            'system_usage': f"{system_percent:.1%}",
            'health': health,
            'optimizations': full_status['system_stats']['optimizations_performed'],
            'uptime_hours': round(full_status['uptime_seconds'] / 3600, 1),
            'secure': _security_wrapper is not None,
            'message': 'Memory management is running smoothly!' if health in ['excellent', 'good'] else 'Consider running memory.optimize()'
        }
        
    except Exception as e:
        return {
            'running': False,
            'error': str(e),
            'secure': _security_wrapper is not None,
            'message': 'Error getting status. Try restarting with memory.start()'
        }

def optimize() -> Dict[str, Any]:
    """
    Force immediate memory optimization.
    
    Returns:
        dict: Optimization results in simple format
        
    Example:
        >>> result = memory.optimize()
        >>> print(f"Freed {result['saved_mb']}MB of memory!")
    """
    if _memory_system is None:
        return {
            'success': False,
            'message': 'Call memory.start() first!'
        }
        
    try:
        # Use secure wrapper if available
        if _security_wrapper and _admin_session:
            result = _security_wrapper.secure_optimize(_admin_session)
        else:
            result = _memory_system.optimize_now()
        
        return {
            'success': True,
            'saved_mb': round(result.get('memory_saved_mb', 0), 1),
            'time_seconds': round(result.get('optimization_time', 0), 2),
            'secure': _security_wrapper is not None,
            'message': f"Optimization complete! Freed {result.get('memory_saved_mb', 0):.1f}MB"
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'secure': _security_wrapper is not None,
            'message': 'Optimization failed. Check system status.'
        }

def track_bot(bot_id: str, bot_cache: Any = None, bot_objects: List[Any] = None) -> bool:
    """
    Register a bot for memory tracking and optimization.
    
    Args:
        bot_id: Unique identifier for the bot
        bot_cache: Bot's cache object (optional)
        bot_objects: List of bot objects to track (optional)
        
    Returns:
        bool: True if registered successfully
        
    Example:
        >>> memory.track_bot("chatbot_1", my_cache, [bot_instance])
        True
    """
    if _memory_system is None:
        print("⚠️  Start memory management first with memory.start()")
        return False
        
    try:
        if bot_cache:
            _memory_system.register_bot_cache(bot_id, bot_cache)
            
        if bot_objects:
            for obj in bot_objects:
                _memory_system.register_bot_object(bot_id, obj)
                
        print(f"✅ Bot '{bot_id}' registered for memory management")
        return True
        
    except Exception as e:
        print(f"❌ Failed to register bot '{bot_id}': {e}")
        return False

def health_check() -> str:
    """
    Get simple health status.
    
    Returns:
        str: One of 'excellent', 'good', 'warning', 'critical', 'not_started'
        
    Example:
        >>> if memory.health_check() == 'critical':
        ...     memory.optimize()
    """
    status_info = status()
    return status_info.get('health', 'unknown')

def is_running() -> bool:
    """Check if memory management is running."""
    return _memory_system is not None and _memory_system.is_running

def get_report() -> str:
    """
    Export detailed memory report to file.
    
    Returns:
        str: Path to the generated report file
        
    Example:
        >>> report_file = memory.get_report()
        >>> print(f"Report saved to: {report_file}")
    """
    if _memory_system is None:
        return "ERROR: Memory management not started"
        
    try:
        return _memory_system.export_memory_report()
    except Exception as e:
        return f"ERROR: {e}"

# Convenience functions for one-liners
def quick_start():
    """One-liner to start memory management with good defaults."""
    return start(aggressive=False)

def emergency_optimize():
    """Emergency optimization with aggressive settings."""
    if _memory_system:
        _memory_system.config.optimization_strategy = OptimizationStrategy.AGGRESSIVE
    return optimize()

# Auto-start option (uncomment to auto-start when imported)
# quick_start()

if __name__ == "__main__":
    # Demo the easy interface
    print("🚀 ActiveLog Memory Management Demo")
    print("=" * 40)
    
    # Start system
    print("Starting memory management...")
    start()
    
    # Show initial status
    print(f"\nInitial status: {status()}")
    
    # Wait a bit
    print("\nWaiting 10 seconds for system to initialize...")
    time.sleep(10)
    
    # Show updated status
    print(f"Updated status: {status()}")
    
    # Test optimization
    print("\nTesting optimization...")
    opt_result = optimize()
    print(f"Optimization result: {opt_result}")
    
    # Final status
    print(f"\nFinal status: {status()}")
    
    # Generate report
    report_path = get_report()
    print(f"\nDetailed report saved to: {report_path}")
    
    print("\n✅ Demo complete! Memory management is running.")
    print("   Use Ctrl+C to stop the demo (memory management will continue)")
    
    try:
        # Keep running for demonstration
        while True:
            time.sleep(30)
            current_status = status()
            print(f"[{time.strftime('%H:%M:%S')}] Health: {current_status['health']}, "
                  f"Memory: {current_status['memory_mb']}MB")
    except KeyboardInterrupt:
        print("\n\n👋 Demo stopped. Memory management continues in background.")
        print("   Call memory.stop() to stop it completely.")