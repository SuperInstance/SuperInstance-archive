"""
AI DM Assistant Configuration
"""

import os
from typing import Dict, List, Any
from enum import Enum


class DifficultyLevel(Enum):
    TRIVIAL = "trivial"
    EASY = "easy" 
    MODERATE = "moderate"
    HARD = "hard"
    LEGENDARY = "legendary"


class EngagementLevel(Enum):
    DISENGAGED = "disengaged"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    IMMERSED = "immersed"


class TensionLevel(Enum):
    CALM = "calm"
    BUILDING = "building"
    MODERATE = "moderate"
    HIGH = "high"
    CLIMACTIC = "climactic"


class StorylineStatus(Enum):
    DORMANT = "dormant"
    ACTIVE = "active"
    ESCALATING = "escalating"
    CLIMAXING = "climaxing"
    RESOLVED = "resolved"


# Core AI DM Configuration
AI_DM_CONFIG = {
    "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    "model": "gpt-4-1106-preview",
    "temperature": 0.7,
    "max_tokens": 2000,
    "session_timeout": 3600,  # 1 hour in seconds
}

# Narrative Flow Configuration
NARRATIVE_CONFIG = {
    "story_coherence_threshold": 0.8,
    "plot_thread_limit": 5,
    "narrative_memory_window": 10,  # sessions
    "coherence_check_frequency": 5,  # every 5 actions
    
    "story_beats": {
        "introduction": {"weight": 0.1, "duration": 15},  # 15 minutes
        "rising_action": {"weight": 0.3, "duration": 90},
        "climax": {"weight": 0.2, "duration": 30},
        "falling_action": {"weight": 0.2, "duration": 45},
        "resolution": {"weight": 0.2, "duration": 30}
    },
    
    "transition_triggers": [
        "major_goal_achieved",
        "critical_failure",
        "revelation_discovered",
        "character_death",
        "time_pressure_activated"
    ]
}

# Adaptive Difficulty Configuration
DIFFICULTY_CONFIG = {
    "success_tracking_window": 10,  # last 10 rolls/encounters
    "adjustment_threshold": 0.2,   # 20% deviation triggers adjustment
    "max_adjustment_per_session": 2,  # CR levels
    "min_adjustment_interval": 300,  # 5 minutes
    
    "success_rates": {
        DifficultyLevel.TRIVIAL: 0.9,
        DifficultyLevel.EASY: 0.75,
        DifficultyLevel.MODERATE: 0.6,
        DifficultyLevel.HARD: 0.4,
        DifficultyLevel.LEGENDARY: 0.2
    },
    
    "adjustment_factors": {
        "combat_encounters": 1.0,
        "skill_challenges": 0.8,
        "saving_throws": 0.6,
        "ability_checks": 0.5
    },
    
    "player_metrics": [
        "success_rate",
        "resource_depletion",
        "health_percentage",
        "engagement_level",
        "strategic_thinking"
    ]
}

# Dramatic Timing Configuration
TIMING_CONFIG = {
    "reveal_patterns": {
        "slow_burn": {"sessions": [3, 6, 9], "intensity": [0.3, 0.6, 1.0]},
        "gradual": {"sessions": [2, 4, 6, 8], "intensity": [0.25, 0.5, 0.75, 1.0]},
        "explosive": {"sessions": [1, 3], "intensity": [0.8, 1.0]}
    },
    
    "timing_factors": {
        "player_curiosity": 0.3,
        "story_pacing": 0.25,
        "tension_level": 0.2,
        "session_time_remaining": 0.15,
        "dramatic_appropriateness": 0.1
    },
    
    "reveal_types": {
        "character_secret": {"buildup": 2, "impact": 0.7},
        "plot_twist": {"buildup": 3, "impact": 0.9},
        "villain_identity": {"buildup": 4, "impact": 1.0},
        "world_truth": {"buildup": 5, "impact": 0.8},
        "prophecy_fulfillment": {"buildup": 3, "impact": 0.6}
    }
}

# Player Engagement Configuration
ENGAGEMENT_CONFIG = {
    "monitoring_intervals": 120,  # 2 minutes
    "engagement_factors": {
        "speech_frequency": 0.2,
        "decision_speed": 0.15,
        "creative_solutions": 0.2,
        "roleplay_quality": 0.15,
        "rule_engagement": 0.1,
        "question_frequency": 0.1,
        "initiative_taking": 0.1
    },
    
    "engagement_thresholds": {
        EngagementLevel.DISENGAGED: 0.2,
        EngagementLevel.LOW: 0.4,
        EngagementLevel.MODERATE: 0.6,
        EngagementLevel.HIGH: 0.8,
        EngagementLevel.IMMERSED: 1.0
    },
    
    "intervention_strategies": {
        EngagementLevel.DISENGAGED: [
            "direct_character_spotlight",
            "personal_stakes_introduction",
            "immediate_action_required"
        ],
        EngagementLevel.LOW: [
            "backstory_callback",
            "skill_showcase_opportunity",
            "moral_dilemma_introduction"
        ]
    }
}

# Improvisation Assistant Configuration
IMPROVISATION_CONFIG = {
    "response_time_limit": 30,  # seconds
    "creativity_boost_threshold": 0.8,
    
    "scenario_categories": {
        "unexpected_combat": {
            "triggers": ["player_attacks_npc", "violence_escalation"],
            "responses": ["justify_stats", "environmental_advantages", "escape_routes"]
        },
        "off_script_exploration": {
            "triggers": ["unexpected_location", "unplanned_investigation"],
            "responses": ["procedural_generation", "connection_to_plot", "new_plot_hook"]
        },
        "creative_problem_solving": {
            "triggers": ["unconventional_approach", "rule_bending_request"],
            "responses": ["fair_adjudication", "consequence_evaluation", "alternative_outcomes"]
        },
        "social_improvisation": {
            "triggers": ["unplanned_npc_interaction", "unexpected_diplomacy"],
            "responses": ["personality_generation", "motivation_assignment", "relationship_establishment"]
        }
    },
    
    "improvisation_tools": [
        "random_tables",
        "procedural_generation",
        "story_connection_finder",
        "balanced_ruling_assistant",
        "consequence_predictor"
    ]
}

# Lore Consistency Configuration
LORE_CONFIG = {
    "consistency_threshold": 0.9,
    "fact_checking_enabled": True,
    "auto_correction": False,  # Suggest rather than auto-correct
    
    "lore_categories": {
        "world_facts": {"weight": 1.0, "importance": "critical"},
        "character_details": {"weight": 0.9, "importance": "high"},
        "historical_events": {"weight": 0.8, "importance": "high"},
        "geographical_info": {"weight": 0.7, "importance": "moderate"},
        "cultural_details": {"weight": 0.6, "importance": "moderate"},
        "minor_npcs": {"weight": 0.4, "importance": "low"}
    },
    
    "consistency_checks": [
        "character_knowledge",
        "timeline_accuracy",
        "power_level_consistency",
        "relationship_continuity",
        "world_rule_adherence"
    ]
}

# Foreshadowing and Callback Configuration
FORESHADOWING_CONFIG = {
    "callback_memory_sessions": 20,
    "foreshadowing_density": 0.3,  # 30% of scenes include foreshadowing
    "minimum_callback_gap": 2,     # sessions
    
    "foreshadowing_types": {
        "subtle_hint": {"frequency": 0.5, "impact": 0.3},
        "symbolic_reference": {"frequency": 0.3, "impact": 0.5},
        "prophetic_statement": {"frequency": 0.15, "impact": 0.8},
        "ominous_warning": {"frequency": 0.05, "impact": 1.0}
    },
    
    "callback_triggers": [
        "location_revisit",
        "character_return",
        "item_reappearance",
        "theme_reinforcement",
        "parallel_situation"
    ],
    
    "payoff_timing": {
        "immediate": 1,    # same session
        "short_term": 3,   # within 3 sessions
        "medium_term": 8,  # within 8 sessions
        "long_term": 20    # campaign arc
    }
}

# Multiple Storyline Configuration
STORYLINE_CONFIG = {
    "max_active_storylines": 4,
    "storyline_priority_levels": 5,
    "balance_check_frequency": 300,  # 5 minutes
    
    "storyline_types": {
        "main_quest": {"priority": 5, "time_allocation": 0.4},
        "character_arc": {"priority": 4, "time_allocation": 0.25},
        "side_quest": {"priority": 3, "time_allocation": 0.2},
        "world_event": {"priority": 2, "time_allocation": 0.1},
        "comedic_relief": {"priority": 1, "time_allocation": 0.05}
    },
    
    "transition_strategies": [
        "natural_intersection",
        "character_motivation",
        "time_jump",
        "scene_cut",
        "parallel_action"
    ]
}

# Tension and Pacing Configuration
PACING_CONFIG = {
    "session_duration": 240,  # 4 hours in minutes
    "tension_curve_segments": 8,
    "pacing_adjustment_frequency": 600,  # 10 minutes
    
    "tension_patterns": {
        "classic_arc": [0.2, 0.3, 0.5, 0.4, 0.6, 0.8, 1.0, 0.3],
        "slow_burn": [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.9, 1.0],
        "roller_coaster": [0.3, 0.7, 0.4, 0.8, 0.5, 0.9, 1.0, 0.2],
        "mystery": [0.4, 0.5, 0.6, 0.7, 0.8, 0.6, 0.9, 1.0]
    },
    
    "pacing_elements": {
        "combat_intensity": 0.3,
        "roleplay_depth": 0.25,
        "exploration_discovery": 0.2,
        "puzzle_complexity": 0.15,
        "social_stakes": 0.1
    }
}

# Player Backstory Integration Configuration
BACKSTORY_CONFIG = {
    "integration_frequency": 0.4,  # 40% of sessions
    "backstory_elements": [
        "family_connections",
        "past_trauma",
        "unfinished_business",
        "old_enemies",
        "forgotten_allies",
        "mysterious_origins",
        "unfulfilled_promises"
    ],
    
    "integration_methods": {
        "direct_encounter": 0.3,
        "indirect_reference": 0.25,
        "environmental_callback": 0.2,
        "npc_knowledge": 0.15,
        "item_significance": 0.1
    },
    
    "emotional_beats": [
        "triumph_over_past",
        "confronting_fear",
        "redemption_opportunity",
        "legacy_building",
        "relationship_healing"
    ]
}

# Rule Arbitration Configuration
ARBITRATION_CONFIG = {
    "rule_sources": [
        "phb",  # Player's Handbook
        "dmg",  # Dungeon Master's Guide
        "xgte", # Xanathar's Guide
        "tcoe", # Tasha's Cauldron
        "house_rules"
    ],
    
    "arbitration_principles": {
        "player_fun_priority": 0.4,
        "narrative_consistency": 0.25,
        "mechanical_balance": 0.2,
        "precedent_maintenance": 0.15
    },
    
    "common_rulings": {
        "advantage_stacking": "no_stack",
        "spell_component_flexibility": "lenient",
        "creative_skill_use": "encouraged",
        "rule_of_cool": "enabled"
    }
}

# Session Zero Configuration
SESSION_ZERO_CONFIG = {
    "checklist_categories": [
        "player_expectations",
        "content_boundaries",
        "character_creation_guidelines",
        "house_rules",
        "campaign_themes",
        "communication_preferences",
        "scheduling_logistics"
    ],
    
    "safety_tools": [
        "x_card",
        "lines_and_veils",
        "open_door_policy",
        "check_in_system"
    ],
    
    "character_integration_depth": {
        "minimal": ["name", "class", "background"],
        "standard": ["backstory_summary", "motivations", "connections"],
        "detailed": ["full_backstory", "relationships", "secrets", "goals"]
    },
    
    "world_building_participation": {
        "dm_controlled": 0.1,
        "collaborative_light": 0.3,
        "collaborative_heavy": 0.5,
        "player_driven": 0.1
    }
}

# Database Configuration
DATABASE_CONFIG = {
    "url": "sqlite:///./ai_dm_assistant.db",
    "echo": False,
    "track_modifications": False
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "ai_dm_assistant.log"
}