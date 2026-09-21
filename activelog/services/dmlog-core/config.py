"""
Configuration settings for DMLog Core RPG Rules Engine.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    SERVICE_NAME: str = "DMLog Core RPG Rules Engine"
    SERVICE_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8012
    DEBUG: bool = False
    RELOAD: bool = False
    
    # Database configuration
    DATABASE_URL: str = "postgresql://user:password@postgres:5432/dmlog_core"
    DATABASE_ECHO: bool = False
    
    # Redis configuration
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # Security configuration
    SECRET_KEY: str = "dmlog-core-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # File storage
    DATA_DIR: str = "./data"
    RULES_DIR: str = "./data/rules"
    CHARACTERS_DIR: str = "./data/characters"
    CAMPAIGNS_DIR: str = "./data/campaigns"
    
    # Game system configurations
    SUPPORTED_SYSTEMS: List[str] = [
        "dnd5e", "pathfinder1e", "pathfinder2e", "callofcthulhu",
        "shadowrun", "vampire", "savage_worlds", "fate_core"
    ]
    
    # Dice rolling settings
    MAX_DICE_COUNT: int = 1000
    MAX_DICE_SIDES: int = 1000
    MAX_MODIFIER: int = 10000
    
    # Combat settings
    MAX_INITIATIVE_ORDER: int = 100
    MAX_CONDITIONS_PER_CHARACTER: int = 50
    
    # Spell/ability settings
    MAX_SPELL_SLOTS: int = 20
    MAX_ABILITIES_PER_CHARACTER: int = 500
    
    # Inventory settings
    MAX_INVENTORY_SIZE: int = 1000
    WEIGHT_PRECISION: int = 2
    
    # NPC generation settings
    NPC_NAME_POOLS: List[str] = [
        "fantasy", "modern", "sci_fi", "historical", "custom"
    ]
    
    # Encounter balancing
    ENCOUNTER_DIFFICULTY_RANGES: dict = {
        "trivial": (0.0, 0.25),
        "easy": (0.25, 0.5),
        "medium": (0.5, 0.75),
        "hard": (0.75, 1.0),
        "deadly": (1.0, 2.0),
        "impossible": (2.0, float('inf'))
    }
    
    # Experience and leveling
    XP_CALCULATION_METHODS: List[str] = [
        "milestone", "encounter_based", "story_based", "hybrid"
    ]
    
    # Loot generation
    LOOT_RARITY_WEIGHTS: dict = {
        "common": 60,
        "uncommon": 25,
        "rare": 10,
        "very_rare": 4,
        "legendary": 1
    }
    
    # Rule lookup settings
    FUZZY_SEARCH_THRESHOLD: float = 0.6
    MAX_SEARCH_RESULTS: int = 50
    
    # Relationship mapping
    MAX_RELATIONSHIPS_PER_CHARACTER: int = 100
    RELATIONSHIP_TYPES: List[str] = [
        "ally", "enemy", "neutral", "family", "friend", "rival",
        "mentor", "student", "lover", "business", "unknown"
    ]
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Game system specific configurations
GAME_SYSTEM_CONFIGS = {
    "dnd5e": {
        "name": "Dungeons & Dragons 5th Edition",
        "attributes": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
        "skills": ["athletics", "acrobatics", "sleight_of_hand", "stealth", "arcana", "history", 
                  "investigation", "nature", "religion", "animal_handling", "insight", "medicine",
                  "perception", "survival", "deception", "intimidation", "performance", "persuasion"],
        "armor_classes": {"light": 11, "medium": 13, "heavy": 16},
        "hit_dice": {"d6": 6, "d8": 8, "d10": 10, "d12": 12},
        "spell_levels": 9,
        "max_level": 20,
        "proficiency_bonus": {1: 2, 5: 3, 9: 4, 13: 5, 17: 6}
    },
    "pathfinder1e": {
        "name": "Pathfinder 1st Edition",
        "attributes": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
        "armor_classes": {"light": 12, "medium": 15, "heavy": 18},
        "hit_dice": {"d6": 6, "d8": 8, "d10": 10, "d12": 12},
        "spell_levels": 9,
        "max_level": 20,
        "base_attack_bonus": "variable"
    },
    "callofcthulhu": {
        "name": "Call of Cthulhu 7th Edition",
        "attributes": ["strength", "dexterity", "constitution", "appearance", "education",
                      "intelligence", "power", "size"],
        "sanity_system": True,
        "luck_mechanic": True,
        "skill_system": "percentile",
        "max_skill": 99
    },
    "shadowrun": {
        "name": "Shadowrun 5th Edition",
        "attributes": ["body", "agility", "reaction", "strength", "willpower", "logic",
                      "intuition", "charisma", "edge"],
        "dice_system": "dice_pool",
        "magic_system": "drain",
        "cybernetics": True,
        "matrix_rules": True
    }
}

# Create global settings instance
settings = Settings()