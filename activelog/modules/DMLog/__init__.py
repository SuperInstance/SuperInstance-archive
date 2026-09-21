"""
DMLog.ai - Comprehensive Tabletop RPG Engine

A powerful, flexible RPG engine supporting multiple game systems including:
- D&D 5th Edition
- Pathfinder
- Call of Cthulhu  
- Shadowrun
- Vampire the Masquerade
- And more!

Features:
- Advanced dice rolling with various mechanics
- Flexible character sheet system
- Combat engine with initiative tracking
- Comprehensive spellcasting system
- Campaign and session management
- Skill and ability check framework
"""

from .core import *
from .systems import *

# Engine version
__version__ = "1.0.0"
__author__ = "DMLog.ai Team"

# Main engine components
__all__ = [
    # Core engine
    'DiceRoller', 'BaseCharacter', 'CombatEngine', 'SpellcastingSystem', 'CampaignManager',
    
    # Game systems
    'DnD5eSystem', 'DnD5eCharacter',
    
    # Convenience functions
    'roll_dice', 'make_skill_check', 'make_ability_check', 'make_saving_throw',
    'start_combat', 'cast_spell', 'create_campaign',
    
    # System info
    '__version__', '__author__',
]


def get_supported_systems():
    """Get list of supported game systems."""
    return [
        {
            'name': 'Dungeons & Dragons 5th Edition',
            'code': 'dnd5e',
            'version': '5.0',
            'class': 'DnD5eSystem'
        },
        # Future systems will be added here
    ]


def create_character(name: str, system: str = "dnd5e", **kwargs):
    """
    Create a character for the specified game system.
    
    Args:
        name: Character name
        system: Game system code (default: "dnd5e")
        **kwargs: Additional character creation parameters
    
    Returns:
        Character instance for the specified system
    """
    if system == "dnd5e":
        from .systems import DnD5eSystem
        game_system = DnD5eSystem()
        return game_system.create_character(name, **kwargs)
    else:
        raise ValueError(f"Unsupported game system: {system}")


def get_engine_info():
    """Get information about the DMLog.ai engine."""
    return {
        'name': 'DMLog.ai RPG Engine',
        'version': __version__,
        'author': __author__,
        'supported_systems': get_supported_systems(),
        'features': [
            'Advanced dice mechanics',
            'Flexible character sheets', 
            'Combat management',
            'Spellcasting system',
            'Campaign tracking',
            'Session management',
            'Multi-system support'
        ]
    }