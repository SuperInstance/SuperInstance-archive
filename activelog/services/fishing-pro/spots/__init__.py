"""
Fishing Spots Module
GPS-based fishing spot database and management
"""

from .fishing_spots import (
    FishingSpotManager,
    FishingSpot,
    GPSCoordinate,
    FishingConditions,
    SpotVisit,
    FishingSpotDatabase,
    SpotType,
    BottomType,
    WaterType
)

__all__ = [
    'FishingSpotManager',
    'FishingSpot',
    'GPSCoordinate',
    'FishingConditions',
    'SpotVisit',
    'FishingSpotDatabase',
    'SpotType',
    'BottomType',
    'WaterType'
]