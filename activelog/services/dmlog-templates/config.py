"""
Configuration settings for the D&D Template System
"""

import os
from typing import Dict, List, Any

# Base configuration
BASE_CONFIG = {
    "service_name": "DMLog Templates",
    "version": "1.0.0",
    "debug": os.getenv("DEBUG", "false").lower() == "true",
    "host": os.getenv("HOST", "0.0.0.0"),
    "port": int(os.getenv("PORT", 8001))
}

# Template generation settings
TEMPLATE_CONFIG = {
    "max_adventure_length": 50,  # Maximum number of encounters per adventure
    "min_adventure_length": 3,   # Minimum number of encounters per adventure
    "default_party_size": 4,     # Default party size for balancing
    "challenge_variance": 0.2,   # Variance in encounter difficulty
    "story_complexity_levels": ["simple", "moderate", "complex", "epic"],
    "supported_themes": [
        "heroic_fantasy", "dark_fantasy", "horror", "mystery", "political",
        "exploration", "dungeon_crawl", "urban", "wilderness", "planar"
    ]
}

# Adventure generation by level tiers
LEVEL_TIERS = {
    "tier1": {"levels": [1, 2, 3, 4], "name": "Local Heroes", "scope": "village/town"},
    "tier2": {"levels": [5, 6, 7, 8, 9, 10], "name": "Regional Champions", "scope": "kingdom/region"},
    "tier3": {"levels": [11, 12, 13, 14, 15, 16], "name": "World Shapers", "scope": "continent/plane"},
    "tier4": {"levels": [17, 18, 19, 20], "name": "Epic Heroes", "scope": "multiverse"}
}

# Character backstory generation
BACKSTORY_CONFIG = {
    "background_weights": {
        "acolyte": 0.08, "charlatan": 0.06, "criminal": 0.07, "entertainer": 0.08,
        "folk_hero": 0.09, "guild_artisan": 0.08, "hermit": 0.05, "noble": 0.06,
        "outlander": 0.08, "sage": 0.07, "sailor": 0.06, "soldier": 0.08,
        "urchin": 0.07, "custom": 0.07
    },
    "relationship_types": [
        "family", "friend", "mentor", "rival", "enemy", "love_interest",
        "business_partner", "guild_member", "former_companion"
    ],
    "motivation_categories": [
        "revenge", "redemption", "knowledge", "power", "love", "family",
        "duty", "freedom", "justice", "survival", "discovery", "legacy"
    ]
}

# Plot generation settings
PLOT_CONFIG = {
    "twist_categories": [
        "identity_reveal", "betrayal", "false_information", "hidden_connection",
        "power_corruption", "time_manipulation", "parallel_reality", "moral_dilemma"
    ],
    "story_structures": {
        "three_act": ["setup", "confrontation", "resolution"],
        "hero_journey": [
            "ordinary_world", "call_to_adventure", "refusal_of_call",
            "meeting_mentor", "crossing_threshold", "tests_allies_enemies",
            "approach_inmost_cave", "ordeal", "reward", "road_back",
            "resurrection", "return_with_elixir"
        ],
        "mystery": [
            "inciting_incident", "investigation", "red_herrings",
            "revelation", "climax", "denouement"
        ]
    }
}

# Encounter generation
ENCOUNTER_CONFIG = {
    "encounter_types": {
        "combat": 0.4,
        "social": 0.2,
        "exploration": 0.15,
        "puzzle": 0.1,
        "trap": 0.1,
        "chase": 0.05
    },
    "difficulty_distribution": {
        "easy": 0.3,
        "medium": 0.4,
        "hard": 0.25,
        "deadly": 0.05
    },
    "environment_types": [
        "dungeon", "urban", "wilderness", "underground", "coastal",
        "mountain", "forest", "desert", "arctic", "swamp", "planar"
    ]
}

# Puzzle and trap configuration
PUZZLE_CONFIG = {
    "complexity_levels": {
        "simple": {"min_steps": 1, "max_steps": 3, "dc_range": [10, 13]},
        "moderate": {"min_steps": 2, "max_steps": 5, "dc_range": [12, 16]},
        "complex": {"min_steps": 4, "max_steps": 8, "dc_range": [15, 19]},
        "legendary": {"min_steps": 6, "max_steps": 12, "dc_range": [18, 25]}
    },
    "puzzle_types": [
        "riddle", "logic", "pattern", "mechanical", "magical",
        "social", "environmental", "mathematical", "linguistic"
    ]
}

TRAP_CONFIG = {
    "trap_types": [
        "mechanical", "magical", "environmental", "illusory", "social"
    ],
    "trigger_types": [
        "pressure_plate", "tripwire", "motion", "touch", "sound",
        "light", "proximity", "time", "condition", "keyword"
    ],
    "damage_types": [
        "piercing", "slashing", "bludgeoning", "fire", "cold", "lightning",
        "thunder", "poison", "acid", "necrotic", "radiant", "force",
        "psychic", "charm", "frightened", "paralyzed", "restrained"
    ],
    "dc_scaling": {
        1: {"detect": 12, "disarm": 12},
        5: {"detect": 14, "disarm": 14},
        10: {"detect": 16, "disarm": 16},
        15: {"detect": 18, "disarm": 18},
        20: {"detect": 20, "disarm": 20}
    }
}

# Social encounter configuration
SOCIAL_CONFIG = {
    "npc_archetypes": [
        "ally", "neutral", "rival", "enemy", "informant", "merchant",
        "authority", "commoner", "expert", "noble", "criminal"
    ],
    "interaction_types": [
        "negotiation", "persuasion", "intimidation", "deception",
        "insight", "investigation", "performance", "bribery"
    ],
    "social_complexities": {
        "simple": {"participants": 1, "objectives": 1, "complications": 0},
        "moderate": {"participants": 2, "objectives": 2, "complications": 1},
        "complex": {"participants": 3, "objectives": 3, "complications": 2},
        "intricate": {"participants": 4, "objectives": 4, "complications": 3}
    }
}

# Chase and heist configuration
CHASE_CONFIG = {
    "chase_types": ["foot", "mounted", "vehicle", "aerial", "magical", "underwater"],
    "terrain_types": ["urban", "wilderness", "underground", "rooftop", "water", "aerial"],
    "complications": [
        "obstacles", "crowds", "weather", "pursuit", "traps",
        "environmental_hazards", "magical_interference"
    ],
    "success_conditions": [
        "distance", "time_limit", "stealth", "endurance", "skill_challenges"
    ]
}

HEIST_CONFIG = {
    "heist_types": ["theft", "infiltration", "espionage", "rescue", "sabotage"],
    "security_levels": {
        "minimal": {"guards": 1, "traps": 1, "magical_wards": 0},
        "light": {"guards": 2, "traps": 2, "magical_wards": 1},
        "moderate": {"guards": 4, "traps": 4, "magical_wards": 2},
        "heavy": {"guards": 8, "traps": 6, "magical_wards": 4},
        "maximum": {"guards": 12, "traps": 10, "magical_wards": 6}
    },
    "phases": ["reconnaissance", "planning", "infiltration", "execution", "escape"]
}

# Mystery and horror configuration
MYSTERY_CONFIG = {
    "mystery_types": ["murder", "theft", "disappearance", "conspiracy", "supernatural"],
    "clue_types": ["physical", "testimonial", "circumstantial", "documentary", "digital"],
    "red_herring_ratio": 0.3,  # 30% of clues are red herrings
    "suspect_archetypes": [
        "obvious_suspect", "innocent_bystander", "hidden_culprit",
        "accomplice", "witness", "victim_relative", "authority_figure"
    ]
}

HORROR_CONFIG = {
    "fear_types": [
        "psychological", "body_horror", "supernatural", "cosmic",
        "survival", "isolation", "corruption", "unknown"
    ],
    "atmosphere_elements": [
        "lighting", "sound", "weather", "temperature", "smell",
        "texture", "isolation", "time_pressure", "false_security"
    ],
    "horror_escalation": {
        "unease": {"tension": 1, "supernatural": 0},
        "dread": {"tension": 3, "supernatural": 1},
        "terror": {"tension": 6, "supernatural": 3},
        "horror": {"tension": 9, "supernatural": 6},
        "despair": {"tension": 10, "supernatural": 10}
    }
}

# Political intrigue configuration
POLITICAL_CONFIG = {
    "faction_types": [
        "government", "religious", "criminal", "mercantile", "military",
        "academic", "noble_house", "secret_society", "foreign_power"
    ],
    "intrigue_elements": [
        "blackmail", "assassination", "espionage", "corruption",
        "succession", "rebellion", "diplomacy", "trade_war"
    ],
    "complexity_levels": {
        "simple": {"factions": 2, "plots": 1, "layers": 1},
        "moderate": {"factions": 3, "plots": 2, "layers": 2},
        "complex": {"factions": 4, "plots": 3, "layers": 3},
        "byzantine": {"factions": 6, "plots": 5, "layers": 4}
    }
}

# File paths
TEMPLATE_PATHS = {
    "adventures": "templates/adventures/",
    "oneshots": "templates/oneshots/",
    "encounters": "templates/encounters/",
    "npcs": "templates/npcs/",
    "locations": "templates/locations/",
    "items": "templates/items/"
}

DATA_PATHS = {
    "names": "data/names/",
    "descriptions": "data/descriptions/",
    "plot_hooks": "data/plot_hooks/",
    "encounters": "data/encounters/",
    "puzzles": "data/puzzles/",
    "traps": "data/traps/"
}

# Export formats
EXPORT_FORMATS = {
    "json": {"extension": "json", "mime_type": "application/json"},
    "yaml": {"extension": "yaml", "mime_type": "application/x-yaml"},
    "markdown": {"extension": "md", "mime_type": "text/markdown"},
    "pdf": {"extension": "pdf", "mime_type": "application/pdf"},
    "html": {"extension": "html", "mime_type": "text/html"}
}