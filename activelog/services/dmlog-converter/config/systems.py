"""
Game System Definitions and Configuration
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field


class GameSystem(Enum):
    """Supported game systems"""
    D_AND_D_5E = "dnd5e"
    D_AND_D_3_5E = "dnd3.5e"
    D_AND_D_4E = "dnd4e"
    PATHFINDER_1E = "pathfinder1e"
    PATHFINDER_2E = "pathfinder2e"
    D_AND_D_2E = "dnd2e"
    D_AND_D_1E = "dnd1e"
    GURPS = "gurps"
    WORLD_OF_DARKNESS = "world_of_darkness"
    SAVAGE_WORLDS = "savage_worlds"
    FATE_CORE = "fate_core"
    CALL_OF_CTHULHU = "call_of_cthulhu"
    VAMPIRE_MASQUERADE = "vampire_masquerade"
    SHADOWRUN = "shadowrun"
    CYBERPUNK_RED = "cyberpunk_red"


@dataclass
class SystemInfo:
    """Information about a game system"""
    name: str
    short_name: str
    publisher: str
    edition: str
    year_published: int
    
    # Core mechanics
    primary_die: str  # "d20", "d100", "3d6", etc.
    attribute_system: str  # "six_stats", "nine_attributes", "aspects", etc.
    skill_system: str  # "skills", "proficiency", "dots", etc.
    
    # Power scaling
    level_range: tuple  # (min_level, max_level)
    power_scale: str  # "linear", "exponential", "milestone", etc.
    
    # Supported content types
    has_classes: bool = True
    has_races: bool = True
    has_spells: bool = True
    has_feats: bool = True
    has_equipment: bool = True
    has_monsters: bool = True
    
    # System-specific features
    special_features: List[str] = field(default_factory=list)


# System definitions
SYSTEM_DEFINITIONS = {
    GameSystem.D_AND_D_5E: SystemInfo(
        name="Dungeons & Dragons 5th Edition",
        short_name="D&D 5e",
        publisher="Wizards of the Coast",
        edition="5th",
        year_published=2014,
        primary_die="d20",
        attribute_system="six_stats",
        skill_system="proficiency",
        level_range=(1, 20),
        power_scale="bounded_accuracy",
        has_classes=True,
        has_races=True,
        has_spells=True,
        has_feats=True,
        has_equipment=True,
        has_monsters=True,
        special_features=["advantage_disadvantage", "inspiration", "bounded_accuracy", "cantrips_at_will"]
    ),
    
    GameSystem.PATHFINDER_2E: SystemInfo(
        name="Pathfinder Second Edition",
        short_name="PF2e",
        publisher="Paizo",
        edition="2nd",
        year_published=2019,
        primary_die="d20",
        attribute_system="six_stats",
        skill_system="proficiency_degrees",
        level_range=(1, 20),
        power_scale="linear_with_degrees",
        has_classes=True,
        has_races=True,
        has_spells=True,
        has_feats=True,
        has_equipment=True,
        has_monsters=True,
        special_features=["degrees_of_success", "three_actions", "focus_spells", "ancestry_heritage"]
    ),
    
    GameSystem.D_AND_D_3_5E: SystemInfo(
        name="Dungeons & Dragons 3.5 Edition",
        short_name="D&D 3.5e",
        publisher="Wizards of the Coast",
        edition="3.5",
        year_published=2003,
        primary_die="d20",
        attribute_system="six_stats",
        skill_system="skill_ranks",
        level_range=(1, 20),
        power_scale="exponential",
        has_classes=True,
        has_races=True,
        has_spells=True,
        has_feats=True,
        has_equipment=True,
        has_monsters=True,
        special_features=["skill_ranks", "base_attack_bonus", "save_progression", "spell_preparation"]
    ),
    
    GameSystem.FATE_CORE: SystemInfo(
        name="Fate Core",
        short_name="Fate",
        publisher="Evil Hat Productions",
        edition="Core",
        year_published=2013,
        primary_die="4dF",
        attribute_system="approaches_or_skills",
        skill_system="skill_pyramid",
        level_range=(0, 8),
        power_scale="narrative",
        has_classes=False,
        has_races=False,
        has_spells=False,
        has_feats=True,  # Stunts
        has_equipment=True,
        has_monsters=True,
        special_features=["aspects", "fate_points", "stunts", "stress_consequences", "narrative_permission"]
    ),
    
    GameSystem.CALL_OF_CTHULHU: SystemInfo(
        name="Call of Cthulhu",
        short_name="CoC",
        publisher="Chaosium",
        edition="7th",
        year_published=2014,
        primary_die="d100",
        attribute_system="chaosium_stats",
        skill_system="percentile",
        level_range=(1, 1),  # No levels
        power_scale="investigative",
        has_classes=False,
        has_races=False,
        has_spells=True,  # Mythos spells
        has_feats=False,
        has_equipment=True,
        has_monsters=True,
        special_features=["sanity", "luck_points", "push_rolls", "bonus_penalty_dice", "investigative_focus"]
    )
}


# Conversion difficulty matrix
CONVERSION_DIFFICULTY = {
    # Easy conversions (similar systems)
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): "moderate",
    (GameSystem.D_AND_D_3_5E, GameSystem.PATHFINDER_1E): "easy",
    (GameSystem.D_AND_D_5E, GameSystem.D_AND_D_3_5E): "moderate",
    
    # Moderate conversions (different mechanics but similar concepts)
    (GameSystem.D_AND_D_5E, GameSystem.D_AND_D_4E): "moderate",
    (GameSystem.PATHFINDER_1E, GameSystem.PATHFINDER_2E): "hard",
    
    # Hard conversions (very different systems)
    (GameSystem.D_AND_D_5E, GameSystem.FATE_CORE): "hard",
    (GameSystem.D_AND_D_5E, GameSystem.CALL_OF_CTHULHU): "very_hard",
    (GameSystem.PATHFINDER_2E, GameSystem.GURPS): "very_hard",
    
    # Narrative vs mechanical systems
    (GameSystem.FATE_CORE, GameSystem.SAVAGE_WORLDS): "moderate",
    (GameSystem.WORLD_OF_DARKNESS, GameSystem.SHADOWRUN): "hard",
}


# Attribute mapping between systems
ATTRIBUTE_MAPPINGS = {
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
        "strength": "strength",
        "dexterity": "dexterity", 
        "constitution": "constitution",
        "intelligence": "intelligence",
        "wisdom": "wisdom",
        "charisma": "charisma"
    },
    
    (GameSystem.D_AND_D_5E, GameSystem.FATE_CORE): {
        "strength": "forceful",
        "dexterity": "quick",
        "constitution": "forceful",
        "intelligence": "clever",
        "wisdom": "careful",
        "charisma": "flashy"
    },
    
    (GameSystem.D_AND_D_5E, GameSystem.CALL_OF_CTHULHU): {
        "strength": "str",
        "dexterity": "dex",
        "constitution": "con",
        "intelligence": "int",
        "wisdom": "pow",  # Power in CoC
        "charisma": "app"  # Appearance in CoC
    }
}


# Skill system mappings
SKILL_MAPPINGS = {
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
        "acrobatics": "acrobatics",
        "animal_handling": "nature",
        "arcana": "arcana",
        "athletics": "athletics",
        "deception": "deception",
        "history": "society",
        "insight": "sense_motive",
        "intimidation": "intimidation",
        "investigation": "investigation",
        "medicine": "medicine",
        "nature": "nature",
        "perception": "perception",
        "performance": "performance",
        "persuasion": "diplomacy",
        "religion": "religion",
        "sleight_of_hand": "thievery",
        "stealth": "stealth",
        "survival": "survival"
    }
}


# Power level equivalencies
POWER_LEVEL_EQUIVALENCIES = {
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
        1: 1, 2: 2, 3: 3, 4: 4, 5: 5,
        6: 6, 7: 7, 8: 8, 9: 9, 10: 10,
        11: 11, 12: 12, 13: 13, 14: 14, 15: 15,
        16: 16, 17: 17, 18: 18, 19: 19, 20: 20
    },
    
    (GameSystem.D_AND_D_5E, GameSystem.FATE_CORE): {
        1: 0, 2: 0, 3: 1, 4: 1, 5: 2,
        6: 2, 7: 3, 8: 3, 9: 4, 10: 4,
        11: 5, 12: 5, 13: 6, 14: 6, 15: 7,
        16: 7, 17: 8, 18: 8, 19: 8, 20: 8
    },
    
    (GameSystem.D_AND_D_5E, GameSystem.CALL_OF_CTHULHU): {
        # CoC doesn't have levels, but we can map to skill competency
        1: 25, 2: 30, 3: 35, 4: 40, 5: 45,
        6: 50, 7: 55, 8: 60, 9: 65, 10: 70,
        11: 75, 12: 80, 13: 85, 14: 90, 15: 95,
        16: 95, 17: 95, 18: 95, 19: 95, 20: 95  # Cap at 95% in CoC
    }
}


# Damage type mappings
DAMAGE_TYPE_MAPPINGS = {
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
        "acid": "acid",
        "bludgeoning": "bludgeoning",
        "cold": "cold",
        "fire": "fire",
        "force": "force",
        "lightning": "electricity",
        "necrotic": "negative",
        "piercing": "piercing",
        "poison": "poison",
        "psychic": "mental",
        "radiant": "positive",
        "slashing": "slashing",
        "thunder": "sonic"
    }
}


# Spell level mappings
SPELL_LEVEL_MAPPINGS = {
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
        0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5,
        6: 6, 7: 7, 8: 8, 9: 9, 10: 10
    },
    
    (GameSystem.D_AND_D_5E, GameSystem.D_AND_D_3_5E): {
        0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5,
        6: 6, 7: 7, 8: 8, 9: 9
    }
}


# Challenge Rating mappings
CR_MAPPINGS = {
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
        0: -1, 0.125: 0, 0.25: 0, 0.5: 1, 1: 2,
        2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9,
        9: 10, 10: 11, 11: 12, 12: 13, 13: 14, 14: 15,
        15: 16, 16: 17, 17: 18, 18: 19, 19: 20, 20: 21,
        21: 22, 22: 23, 23: 24, 24: 25, 25: 26, 26: 27,
        27: 28, 28: 29, 29: 30, 30: 30
    }
}


# Currency conversion rates
CURRENCY_MAPPINGS = {
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
        "cp": "cp",  # copper piece
        "sp": "sp",  # silver piece  
        "gp": "gp",  # gold piece
        "pp": "pp"   # platinum piece
    },
    
    (GameSystem.D_AND_D_5E, GameSystem.CALL_OF_CTHULHU): {
        # Approximate 1920s USD conversion
        "cp": 0.01,   # penny
        "sp": 0.10,   # dime
        "gp": 1.00,   # dollar
        "pp": 10.00   # ten dollar bill
    }
}


# Equipment category mappings
EQUIPMENT_CATEGORIES = {
    "weapons": ["simple_weapons", "martial_weapons", "exotic_weapons"],
    "armor": ["light_armor", "medium_armor", "heavy_armor", "shields"],
    "tools": ["artisan_tools", "gaming_sets", "instruments", "kits"],
    "gear": ["adventuring_gear", "ammunition", "arcane_focus", "druidcraft_focus"],
    "mounts": ["mounts", "vehicles", "tack_harness"],
    "trade_goods": ["trade_goods", "gems", "art_objects"],
    "magic_items": ["consumables", "magic_weapons", "magic_armor", "wondrous_items"]
}


# Rarity mappings
RARITY_MAPPINGS = {
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
        "common": "common",
        "uncommon": "uncommon", 
        "rare": "rare",
        "very_rare": "rare",
        "legendary": "unique",
        "artifact": "artifact"
    }
}


# Action economy mappings
ACTION_MAPPINGS = {
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
        "action": "2_actions",
        "bonus_action": "1_action",
        "reaction": "reaction",
        "free_action": "free_action",
        "movement": "1_action"
    },
    
    (GameSystem.D_AND_D_5E, GameSystem.FATE_CORE): {
        "action": "overcome_or_attack",
        "bonus_action": "create_advantage",
        "reaction": "defend",
        "free_action": "free_invoke",
        "movement": "overcome"
    }
}


# Special ability type mappings
ABILITY_TYPE_MAPPINGS = {
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
        "spell": "spell",
        "feature": "class_feature",
        "feat": "feat",
        "trait": "ancestry_feature",
        "action": "activity"
    }
}


# Condition mappings
CONDITION_MAPPINGS = {
    (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
        "blinded": "blinded",
        "charmed": "controlled",
        "deafened": "deafened", 
        "frightened": "frightened",
        "grappled": "grabbed",
        "incapacitated": "stunned",
        "invisible": "invisible",
        "paralyzed": "paralyzed",
        "petrified": "petrified",
        "poisoned": "sickened",
        "prone": "prone",
        "restrained": "immobilized",
        "stunned": "stunned",
        "unconscious": "unconscious"
    }
}


# System-specific conversion rules
CONVERSION_RULES = {
    GameSystem.D_AND_D_5E: {
        "proficiency_bonus_progression": [2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6],
        "ability_score_increase_levels": [4, 8, 12, 16, 19],
        "cantrips_scale_levels": [1, 5, 11, 17],
        "spell_slot_progression": "full_caster_progression",
        "hit_die_types": {"d6": "weak", "d8": "average", "d10": "good", "d12": "excellent"},
        "saving_throw_proficiencies": 2,  # Each class gets 2
        "skill_proficiencies_range": (2, 4)
    },
    
    GameSystem.PATHFINDER_2E: {
        "proficiency_progression": "TEML",  # Trained, Expert, Master, Legendary
        "ability_boost_levels": [5, 10, 15, 20],
        "class_feat_levels": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20],
        "general_feat_levels": [3, 7, 11, 15, 19],
        "ancestry_feat_levels": [1, 5, 9, 13, 17],
        "skill_feat_levels": "every_even_level",
        "spell_attack_progression": "trained_at_1",
        "skill_proficiencies_range": (7, 11)
    }
}


def get_system_info(system: GameSystem) -> SystemInfo:
    """Get system information"""
    return SYSTEM_DEFINITIONS.get(system)


def get_conversion_difficulty(source: GameSystem, target: GameSystem) -> str:
    """Get conversion difficulty between two systems"""
    return CONVERSION_DIFFICULTY.get((source, target)) or \
           CONVERSION_DIFFICULTY.get((target, source)) or \
           "unknown"


def get_attribute_mapping(source: GameSystem, target: GameSystem) -> Dict[str, str]:
    """Get attribute mapping between systems"""
    return ATTRIBUTE_MAPPINGS.get((source, target)) or \
           {v: k for k, v in ATTRIBUTE_MAPPINGS.get((target, source), {}).items()} or \
           {}


def get_power_level_mapping(source: GameSystem, target: GameSystem, level: int) -> Optional[int]:
    """Get equivalent power level between systems"""
    mapping = POWER_LEVEL_EQUIVALENCIES.get((source, target))
    if mapping:
        return mapping.get(level)
    
    # Try reverse mapping
    reverse_mapping = POWER_LEVEL_EQUIVALENCIES.get((target, source))
    if reverse_mapping:
        # Find the key that maps to our level
        for k, v in reverse_mapping.items():
            if v == level:
                return k
    
    return None


def is_conversion_supported(source: GameSystem, target: GameSystem) -> bool:
    """Check if conversion between systems is supported"""
    return (source, target) in CONVERSION_DIFFICULTY or \
           (target, source) in CONVERSION_DIFFICULTY


def get_supported_systems() -> List[GameSystem]:
    """Get list of all supported systems"""
    return list(SYSTEM_DEFINITIONS.keys())


def get_compatible_systems(system: GameSystem) -> List[GameSystem]:
    """Get list of systems that can be converted to/from the given system"""
    compatible = []
    for source, target in CONVERSION_DIFFICULTY.keys():
        if source == system and target not in compatible:
            compatible.append(target)
        elif target == system and source not in compatible:
            compatible.append(source)
    return compatible