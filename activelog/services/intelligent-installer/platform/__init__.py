"""
Cross-Platform Compatibility Module
Universal platform abstraction layer for seamless cross-platform deployment
"""

from .platform_detector import (
    PlatformDetector,
    PlatformInfo,
    SystemCapabilities,
    HardwareArchitecture
)

from .platform_manager import (
    PlatformManager,
    UniversalInstaller,
    CrossPlatformOptimizer,
    PlatformSpecificHandler
)

from .mobile_support import (
    MobileSupport,
    MobileDeviceManager,
    MobileOptimizer,
    DeviceCapabilities
)

__all__ = [
    'PlatformDetector',
    'PlatformInfo',
    'SystemCapabilities', 
    'HardwareArchitecture',
    'PlatformManager',
    'UniversalInstaller',
    'CrossPlatformOptimizer',
    'PlatformSpecificHandler',
    'MobileSupport',
    'MobileDeviceManager',
    'MobileOptimizer',
    'DeviceCapabilities'
]