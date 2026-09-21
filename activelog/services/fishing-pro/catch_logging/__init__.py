"""
Catch Logging Module
GPS-enabled catch logging with environmental data
"""

from .gps_logger import (
    CatchLogger,
    CatchEntry,
    CatchMethod,
    FishCondition,
    WeatherCondition,
    GPSCoordinate,
    EnvironmentalData,
    GPSService,
    EnvironmentalSensorService,
    CatchDatabase
)

__all__ = [
    'CatchLogger',
    'CatchEntry',
    'CatchMethod',
    'FishCondition',
    'WeatherCondition',
    'GPSCoordinate',
    'EnvironmentalData',
    'GPSService',
    'EnvironmentalSensorService',
    'CatchDatabase'
]