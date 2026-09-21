"""
Next-Generation User Experience Module
Advanced UX/UI components, voice interactions, and adaptive interfaces
"""

from .interface_engine import (
    InterfaceEngine,
    AdaptiveInterface,
    UIComponentManager,
    ThemeManager,
    LayoutEngine
)

from .voice_assistant import (
    VoiceAssistant,
    SpeechRecognizer,
    TextToSpeech,
    ConversationManager,
    VoiceCommand
)

from .accessibility import (
    AccessibilityManager,
    ScreenReader,
    ColorBlindSupport,
    MotorAssistance,
    CognitiveSupport
)

from .personalization import (
    PersonalizationEngine,
    UserPreferences,
    BehaviorAnalyzer,
    RecommendationEngine,
    UserProfile
)

__all__ = [
    'InterfaceEngine',
    'AdaptiveInterface',
    'UIComponentManager',
    'ThemeManager',
    'LayoutEngine',
    'VoiceAssistant',
    'SpeechRecognizer',
    'TextToSpeech',
    'ConversationManager',
    'VoiceCommand',
    'AccessibilityManager',
    'ScreenReader',
    'ColorBlindSupport',
    'MotorAssistance',
    'CognitiveSupport',
    'PersonalizationEngine',
    'UserPreferences',
    'BehaviorAnalyzer',
    'RecommendationEngine',
    'UserProfile'
]