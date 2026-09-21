"""
Mood Detection Module for Emotional AI
Analyzes writing patterns to detect emotional states and mood
"""

from .mood_detector import (
    MoodDetector,
    MoodDetectionConfig,
    MoodAnalysis,
    MoodTrend,
    WritingPatterns,
    MoodState,
    EmotionalIntensity
)

__all__ = [
    'MoodDetector',
    'MoodDetectionConfig',
    'MoodAnalysis',
    'MoodTrend',
    'WritingPatterns',
    'MoodState',
    'EmotionalIntensity'
]