"""
Configuration for the World Building Service.
"""

import os
from typing import Dict, List, Any

class Config:
    """Configuration class for world building service."""
    
    # Service configuration
    SERVICE_NAME = "DM Log World Building Service"
    SERVICE_VERSION = "1.0.0"
    SERVICE_PORT = int(os.getenv("DMLOG_WORLD_PORT", 8014))
    
    # Map generation settings
    MAP_GENERATION = {
        "dungeon": {
            "min_rooms": 5,
            "max_rooms": 15,
            "room_size_range": (3, 8),
            "corridor_width": 1,
            "tile_size": 32
        },
        "town": {
            "min_buildings": 10,
            "max_buildings": 50,
            "road_width": 2,
            "district_types": ["residential", "commercial", "noble", "industrial", "temple"]
        },
        "region": {
            "size": (100, 100),
            "biome_count": 3,
            "settlement_density": 0.1,
            "road_connectivity": 0.7
        },
        "world": {
            "size": (512, 512),
            "continent_count": 3,
            "island_count": 10,
            "climate_zones": 5
        }
    }
    
    # Weather system configuration
    WEATHER_SYSTEM = {
        "seasons": ["spring", "summer", "autumn", "winter"],
        "season_length_days": 90,
        "weather_patterns": {
            "temperate": {
                "spring": {"rain": 0.4, "sunny": 0.5, "cloudy": 0.1},
                "summer": {"sunny": 0.7, "rain": 0.2, "stormy": 0.1},
                "autumn": {"rain": 0.5, "cloudy": 0.3, "sunny": 0.2},
                "winter": {"snow": 0.4, "cloudy": 0.4, "sunny": 0.2}
            },
            "tropical": {
                "wet_season": {"rain": 0.7, "stormy": 0.2, "sunny": 0.1},
                "dry_season": {"sunny": 0.8, "cloudy": 0.2, "rain": 0.0}
            }
        },
        "temperature_ranges": {
            "arctic": (-30, 10),
            "temperate": (-10, 35),
            "tropical": (15, 40),
            "desert": (10, 50)
        }
    }
    
    # Calendar configuration
    CALENDAR_SYSTEM = {
        "months": [
            "Midwinter", "Late Winter", "The Claw of Winter", "The Claw of the Sunsets",
            "The Melting", "The Time of Flowers", "Flamerule", "Highsun",
            "The Fading", "Leaffall", "The Rotting", "The Drawing Down"
        ],
        "days_per_month": 30,
        "days_per_week": 10,
        "weeks_per_month": 3,
        "holidays": {
            "Midwinter": ["Winter Solstice", "New Year"],
            "The Time of Flowers": ["Spring Festival", "Planting Day"],
            "Flamerule": ["Midsummer", "Fire Festival"],
            "The Drawing Down": ["Harvest Festival", "Day of the Dead"]
        }
    }
    
    # Religion and pantheon configuration
    RELIGION_SYSTEM = {
        "deity_domains": [
            "war", "death", "life", "knowledge", "nature", "tempest", 
            "trickery", "light", "forge", "grave", "order", "peace"
        ],
        "pantheon_sizes": {
            "minor": (3, 5),
            "major": (6, 12),
            "complete": (13, 20)
        },
        "religion_types": [
            "monotheistic", "polytheistic", "pantheistic", "ancestor_worship",
            "elemental", "nature_worship", "cosmic", "philosophical"
        ]
    }
    
    # Political system configuration
    POLITICAL_SYSTEM = {
        "government_types": [
            "monarchy", "republic", "oligarchy", "theocracy", "magocracy",
            "military_junta", "confederation", "city_state", "tribal_council"
        ],
        "faction_types": [
            "noble_house", "merchant_guild", "religious_order", "military_order",
            "thieves_guild", "scholars_circle", "artisan_guild", "revolutionary_group"
        ],
        "relationship_types": [
            "allied", "friendly", "neutral", "suspicious", "hostile", "at_war"
        ]
    }
    
    # Economy configuration
    ECONOMY_SYSTEM = {
        "currencies": {
            "copper": 1,
            "silver": 10,
            "electrum": 50,
            "gold": 100,
            "platinum": 1000
        },
        "trade_goods": [
            "grain", "livestock", "textiles", "metals", "gems", "spices",
            "weapons", "armor", "tools", "pottery", "wine", "ale",
            "books", "art", "magical_components", "exotic_goods"
        ],
        "settlement_modifiers": {
            "village": {"supply": 0.5, "demand": 0.3, "variety": 0.2},
            "town": {"supply": 1.0, "demand": 0.8, "variety": 0.6},
            "city": {"supply": 1.5, "demand": 1.2, "variety": 1.0},
            "metropolis": {"supply": 2.0, "demand": 1.5, "variety": 1.5}
        }
    }
    
    # Encounter tables
    ENCOUNTER_TABLES = {
        "dungeon": {
            "undead": 0.3,
            "aberrations": 0.2,
            "constructs": 0.15,
            "traps": 0.2,
            "treasure": 0.15
        },
        "forest": {
            "beasts": 0.4,
            "fey": 0.2,
            "bandits": 0.2,
            "plants": 0.1,
            "druids": 0.1
        },
        "urban": {
            "criminals": 0.3,
            "guards": 0.2,
            "merchants": 0.2,
            "beggars": 0.15,
            "nobles": 0.15
        }
    }
    
    # Language configuration
    LANGUAGE_SYSTEM = {
        "language_families": [
            "human_common", "elvish", "dwarvish", "orcish", "draconic",
            "celestial", "infernal", "primordial", "sylvan", "deep_speech"
        ],
        "phoneme_sets": {
            "human_common": {
                "consonants": "bcdfghjklmnpqrstvwxyz",
                "vowels": "aeiou",
                "common_clusters": ["th", "ch", "sh", "st", "nd", "ng"]
            },
            "elvish": {
                "consonants": "bdfghlmnrstwy",
                "vowels": "aeiouä",
                "common_clusters": ["ll", "nn", "th", "dh"]
            },
            "dwarvish": {
                "consonants": "bcdgkmnprstvzh",
                "vowels": "aou",
                "common_clusters": ["kh", "dh", "rr", "ck"]
            }
        }
    }
    
    # Building generation
    BUILDING_TYPES = {
        "residential": ["cottage", "house", "mansion", "apartment", "hovel"],
        "commercial": ["shop", "market", "warehouse", "bank", "guild_hall"],
        "religious": ["temple", "shrine", "monastery", "cathedral", "chapel"],
        "civic": ["town_hall", "courthouse", "prison", "barracks", "library"],
        "entertainment": ["tavern", "inn", "theater", "arena", "brothel"]
    }
    
    # Quest generation
    QUEST_TEMPLATES = {
        "kill": {
            "objectives": ["eliminate_target", "clear_area", "hunt_creature"],
            "locations": ["dungeon", "forest", "mountains", "ruins"],
            "rewards": ["gold", "magic_item", "reputation", "information"]
        },
        "fetch": {
            "objectives": ["retrieve_item", "deliver_message", "collect_samples"],
            "locations": ["any"],
            "rewards": ["gold", "favor", "information"]
        },
        "escort": {
            "objectives": ["protect_npc", "guide_safely", "prevent_capture"],
            "locations": ["roads", "wilderness", "city"],
            "rewards": ["gold", "reputation", "contacts"]
        }
    }
    
    # File paths
    DATA_PATH = os.path.join(os.path.dirname(__file__), "data")
    MAPS_PATH = os.path.join(DATA_PATH, "maps")
    TEMPLATES_PATH = os.path.join(DATA_PATH, "templates")
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        for path in [cls.DATA_PATH, cls.MAPS_PATH, cls.TEMPLATES_PATH]:
            os.makedirs(path, exist_ok=True)