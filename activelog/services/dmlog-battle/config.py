"""
Configuration for the Combat Simulation Service.
"""

import os
from typing import Dict, List, Any

class Config:
    """Configuration class for combat simulation service."""
    
    # Service configuration
    SERVICE_NAME = "DM Log Combat Simulation Service"
    SERVICE_VERSION = "1.0.0"
    SERVICE_PORT = int(os.getenv("DMLOG_BATTLE_PORT", 8015))
    
    # Grid system settings
    GRID_SYSTEM = {
        "default_size": (30, 30),  # Default battlefield size
        "max_size": (100, 100),    # Maximum battlefield size
        "min_size": (5, 5),        # Minimum battlefield size
        "square_size_feet": 5,     # Each grid square = 5 feet
        "diagonal_movement": True,  # Allow diagonal movement
        "diagonal_cost": 1.5,      # Cost multiplier for diagonal movement
    }
    
    # Line of sight settings
    LINE_OF_SIGHT = {
        "algorithms": ["bresenham", "shadowcasting", "raycasting"],
        "default_algorithm": "bresenham",
        "vision_ranges": {
            "blind": 0,
            "dim": 10,     # 10 feet
            "normal": 30,   # 30 feet  
            "darkvision": 60,  # 60 feet
            "superior": 120,   # 120 feet
            "truesight": 120   # 120 feet, ignores illusions
        },
        "light_levels": {
            "bright": 1.0,
            "dim": 0.5,
            "darkness": 0.0,
            "magical_darkness": -1.0
        }
    }
    
    # Cover system
    COVER_SYSTEM = {
        "types": {
            "none": {"ac_bonus": 0, "dex_save_bonus": 0, "description": "No cover"},
            "half": {"ac_bonus": 2, "dex_save_bonus": 2, "description": "Half cover"},
            "three_quarters": {"ac_bonus": 5, "dex_save_bonus": 5, "description": "Three-quarters cover"},
            "total": {"ac_bonus": 999, "dex_save_bonus": 999, "description": "Total cover"}
        },
        "corner_rules": True,  # Use corner-to-corner line rules
        "size_modifiers": {
            "tiny": -2,
            "small": 0,
            "medium": 0,
            "large": 1,
            "huge": 2,
            "gargantuan": 3
        }
    }
    
    # Area of effect settings
    AOE_SYSTEM = {
        "shapes": ["sphere", "cube", "cone", "cylinder", "line", "wall"],
        "default_visualization": "filled",
        "templates": {
            "fireball": {"shape": "sphere", "radius": 20, "origin": "point"},
            "lightning_bolt": {"shape": "line", "length": 100, "width": 5},
            "cone_of_cold": {"shape": "cone", "length": 60, "width": 60},
            "wall_of_fire": {"shape": "wall", "length": 60, "height": 20, "thickness": 1}
        }
    }
    
    # Combat resolution settings
    COMBAT_RESOLUTION = {
        "initiative_types": ["individual", "group", "side"],
        "default_initiative": "individual",
        "auto_resolve_options": {
            "simple": "Basic attack/damage resolution",
            "advanced": "Full combat simulation with all rules",
            "mass": "Large battle simplified resolution"
        },
        "round_limit": 100,  # Maximum combat rounds
        "turn_timeout": 300   # 5 minutes per turn in seconds
    }
    
    # Damage system
    DAMAGE_SYSTEM = {
        "types": [
            "acid", "bludgeoning", "cold", "fire", "force", "lightning",
            "necrotic", "piercing", "poison", "psychic", "radiant", "slashing", "thunder"
        ],
        "resistance_types": ["resistance", "immunity", "vulnerability"],
        "critical_hit": {
            "natural_20": True,
            "double_dice": True,
            "max_plus_roll": False,  # Alternative crit rule
            "threat_ranges": {  # Expanded crit ranges for some weapons
                "rapier": [19, 20],
                "scimitar": [19, 20],
                "longsword": [20]
            }
        },
        "death_saves": {
            "dc": 10,
            "success_threshold": 3,
            "failure_threshold": 3,
            "natural_1_counts_as": 2,  # 2 failures
            "natural_20_effect": "regain_1_hp"
        }
    }
    
    # Environmental hazards
    ENVIRONMENTAL_HAZARDS = {
        "types": {
            "fire": {"damage": "1d6 fire", "save": "dex", "dc": 15},
            "acid": {"damage": "2d4 acid", "save": "dex", "dc": 12},
            "poison_gas": {"damage": "1d8 poison", "save": "con", "dc": 14},
            "spike_trap": {"damage": "2d6 piercing", "save": "dex", "dc": 15},
            "pit_trap": {"damage": "2d6 bludgeoning", "save": "dex", "dc": 15},
            "magic_circle": {"effect": "advantage_spell_saves", "save": None},
            "difficult_terrain": {"movement_cost": 2, "save": None},
            "ice": {"save": "acrobatics", "dc": 12, "effect": "prone"},
            "darkness": {"vision_penalty": "blind", "save": None}
        },
        "interactive_terrain": {
            "lever": {"action": "activate_trap", "uses": -1},
            "door": {"action": "open_close", "hp": 15, "ac": 15},
            "window": {"action": "break", "hp": 5, "ac": 13},
            "brazier": {"action": "light_extinguish", "effect": "illumination"},
            "altar": {"action": "activate", "effect": "blessing_curse"}
        }
    }
    
    # Mounted combat
    MOUNTED_COMBAT = {
        "mount_types": {
            "horse": {"speed": 60, "size": "large", "hp": 19, "ac": 11},
            "warhorse": {"speed": 60, "size": "large", "hp": 19, "ac": 11},
            "pony": {"speed": 40, "size": "medium", "hp": 11, "ac": 10},
            "mastiff": {"speed": 40, "size": "medium", "hp": 5, "ac": 12},
            "griffin": {"speed": 80, "fly": 80, "size": "large", "hp": 59, "ac": 15}
        },
        "mounting_rules": {
            "action_cost": "half_movement",
            "size_requirement": "one_smaller",
            "willing_mount": True
        },
        "combat_rules": {
            "controlled_mount": "acts_on_rider_turn",
            "independent_mount": "acts_on_own_initiative",
            "mount_saves": "rider_can_force_reroll"
        }
    }
    
    # Mass combat
    MASS_COMBAT = {
        "unit_sizes": {
            "squad": 5,
            "section": 10,
            "platoon": 30,
            "company": 100,
            "battalion": 500
        },
        "battle_phases": ["deployment", "skirmish", "main_battle", "rout"],
        "morale_system": {
            "base_morale": 10,
            "modifiers": {
                "outnumbered_2_to_1": -2,
                "outnumbered_3_to_1": -4,
                "commander_present": 2,
                "elite_troops": 3,
                "fresh_troops": 1,
                "exhausted_troops": -2
            }
        }
    }
    
    # Critical hit and fumble tables
    CRITICAL_TABLES = {
        "critical_hits": {
            "slashing": [
                "Severe cut - target bleeds 1d4 damage per turn for 3 turns",
                "Precise strike - ignore armor, deal maximum damage",
                "Crippling blow - target speed reduced by half until healed"
            ],
            "piercing": [
                "Deep wound - target has disadvantage on Constitution saves",
                "Vital strike - deal additional 1d8 damage",
                "Pinning blow - target cannot move until they spend action to free themselves"
            ],
            "bludgeoning": [
                "Stunning blow - target stunned until end of their next turn",
                "Bone crushing - target has disadvantage on Strength checks",
                "Knockdown - target knocked prone and takes 1d4 additional damage"
            ]
        },
        "fumbles": {
            "melee": [
                "Weapon flies 1d4 squares in random direction",
                "Strike ally within reach instead",
                "Fall prone after overextending",
                "Weapon breaks (if not magical)"
            ],
            "ranged": [
                "Ammunition breaks/is lost",
                "Hit random target within 30 feet",
                "Bowstring snaps (lose next turn)",
                "Miss by so much you provoke opportunity attacks"
            ],
            "spell": [
                "Spell targets random creature within range",
                "Spell effect reversed (heal becomes harm, etc)",
                "Wild magic surge (if applicable)",
                "Lose spell slot but no effect occurs"
            ]
        }
    }
    
    # Combat analysis
    ANALYSIS_SYSTEM = {
        "metrics": [
            "damage_per_round", "hit_percentage", "critical_frequency",
            "spell_usage", "healing_efficiency", "positioning_score",
            "action_economy", "resource_management", "survivability"
        ],
        "balance_indicators": {
            "encounter_difficulty": ["easy", "medium", "hard", "deadly"],
            "action_economy_ratio": 1.5,  # Actions per side balance point
            "damage_variance": 0.3,       # Acceptable damage variance
            "duration_target": {"min": 3, "max": 8}  # Target combat duration in rounds
        }
    }
    
    # File paths
    DATA_PATH = os.path.join(os.path.dirname(__file__), "data")
    BATTLEFIELDS_PATH = os.path.join(DATA_PATH, "battlefields")
    REPLAYS_PATH = os.path.join(DATA_PATH, "replays")
    ANALYSIS_PATH = os.path.join(DATA_PATH, "analysis")
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        for path in [cls.DATA_PATH, cls.BATTLEFIELDS_PATH, cls.REPLAYS_PATH, cls.ANALYSIS_PATH]:
            os.makedirs(path, exist_ok=True)