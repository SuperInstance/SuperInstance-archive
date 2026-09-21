"""
CLI Module
User interface components for AutoCoder
"""

from .interface import CLI
from .profiles import (
    ProfileManager,
    UserProfile,
    ExperienceLevel,
    get_welcome_message,
    get_error_suggestion,
    get_tips_for_level
)
from .wizard import WelcomeWizard, run_welcome_wizard_if_needed
from .examples import show_examples, show_quick_tips

__all__ = [
    'CLI',
    'ProfileManager',
    'UserProfile',
    'ExperienceLevel',
    'WelcomeWizard',
    'run_welcome_wizard_if_needed',
    'show_examples',
    'show_quick_tips',
    'get_welcome_message',
    'get_error_suggestion',
    'get_tips_for_level'
]
