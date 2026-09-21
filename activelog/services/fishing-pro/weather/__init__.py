"""
Weather Module for Fishing
Weather analysis and optimal fishing window prediction
"""

from .fishing_weather import (
    FishingWeatherService,
    FishingWindow,
    WeatherData,
    MarineWeatherData,
    FishingWeatherAnalyzer,
    WeatherAPI,
    WeatherCondition,
    SeaState,
    FishingConditionRating
)

__all__ = [
    'FishingWeatherService',
    'FishingWindow',
    'WeatherData',
    'MarineWeatherData',
    'FishingWeatherAnalyzer',
    'WeatherAPI',
    'WeatherCondition',
    'SeaState',
    'FishingConditionRating'
]