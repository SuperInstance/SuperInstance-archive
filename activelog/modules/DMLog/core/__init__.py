"""
Core components of the DMLog.ai RPG engine.
"""

from .types import *
from .dice import DiceRoller, DiceRoll, RollResult, roll_dice, default_roller
from .character import BaseCharacter, HitPoints, SpellSlot
from .checks import CheckEngine, make_skill_check, make_ability_check, make_saving_throw
from .combat import CombatEngine, start_combat, default_combat_engine
from .spells import SpellcastingSystem, EnhancedSpell, cast_spell, default_spellcasting_system
from .campaign import CampaignManager, EnhancedCampaign, EnhancedSession, create_campaign, get_active_campaign

__all__ = [
    # Types
    'DiceType', 'AttributeType', 'SkillType', 'DamageType', 'ConditionType', 'SpellSchool',
    'DiceRoll', 'RollResult', 'Attribute', 'Skill', 'Condition', 'Equipment', 'Spell',
    'GameSystemInterface', 'CharacterInterface', 'DiceRollerInterface', 'CombatEngineInterface',
    'Campaign', 'Session', 'RPGEngineError',
    
    # Dice system
    'DiceRoller', 'roll_dice', 'default_roller',
    
    # Character system
    'BaseCharacter', 'HitPoints', 'SpellSlot',
    
    # Check system
    'CheckEngine', 'make_skill_check', 'make_ability_check', 'make_saving_throw',
    
    # Combat system
    'CombatEngine', 'start_combat', 'default_combat_engine',
    
    # Spell system
    'SpellcastingSystem', 'EnhancedSpell', 'cast_spell', 'default_spellcasting_system',
    
    # Campaign system
    'CampaignManager', 'EnhancedCampaign', 'EnhancedSession', 'create_campaign', 'get_active_campaign',
]