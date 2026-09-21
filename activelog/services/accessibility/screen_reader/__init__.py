"""
Screen Reader Support Module
Comprehensive screen reader integration and ARIA support
"""

from .screen_reader import (
    ScreenReaderSupport,
    ARIAElement,
    ScreenReaderAnnouncement,
    NavigationLandmark,
    AccessibilityDatabase,
    ARIARole,
    LiveRegionPoliteness,
    ScreenReaderEngine
)

__all__ = [
    'ScreenReaderSupport',
    'ARIAElement', 
    'ScreenReaderAnnouncement',
    'NavigationLandmark',
    'AccessibilityDatabase',
    'ARIARole',
    'LiveRegionPoliteness',
    'ScreenReaderEngine'
]