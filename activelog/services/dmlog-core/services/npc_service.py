"""
NPC generator service with stats, personalities, and motivations.
"""

import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from models.base import (
    AttributeType, CreatureType, Size, AlignmentType, 
    DamageType, ConditionType, calculate_modifier
)


class NPCRole(str, Enum):
    """NPC roles in the story."""
    QUEST_GIVER = "quest_giver"
    MERCHANT = "merchant"
    GUARD = "guard"
    NOBLE = "noble"
    COMMONER = "commoner"
    SCHOLAR = "scholar"
    PRIEST = "priest"
    CRIMINAL = "criminal"
    SOLDIER = "soldier"
    ARTISAN = "artisan"
    INNKEEPER = "innkeeper"
    INFORMANT = "informant"
    RIVAL = "rival"
    ALLY = "ally"
    NEUTRAL = "neutral"
    VILLAIN = "villain"
    MINION = "minion"
    BOSS = "boss"


class PersonalityTrait(str, Enum):
    """Personality traits for NPCs."""
    # Positive traits
    BRAVE = "brave"
    HONEST = "honest"
    KIND = "kind"
    LOYAL = "loyal"
    WISE = "wise"
    CHARISMATIC = "charismatic"
    PATIENT = "patient"
    GENEROUS = "generous"
    
    # Negative traits
    COWARDLY = "cowardly"
    DISHONEST = "dishonest"
    CRUEL = "cruel"
    TREACHEROUS = "treacherous"
    FOOLISH = "foolish"
    ARROGANT = "arrogant"
    IMPATIENT = "impatient"
    GREEDY = "greedy"
    
    # Neutral traits
    CURIOUS = "curious"
    SECRETIVE = "secretive"
    TALKATIVE = "talkative"
    QUIET = "quiet"
    ECCENTRIC = "eccentric"
    PRACTICAL = "practical"


class Motivation(str, Enum):
    """NPC motivations."""
    POWER = "power"
    WEALTH = "wealth"
    KNOWLEDGE = "knowledge"
    REVENGE = "revenge"
    LOVE = "love"
    FAMILY = "family"
    HONOR = "honor"
    SURVIVAL = "survival"
    FREEDOM = "freedom"
    JUSTICE = "justice"
    CHAOS = "chaos"
    ORDER = "order"
    REDEMPTION = "redemption"
    LEGACY = "legacy"
    DISCOVERY = "discovery"
    PROTECTION = "protection"


@dataclass
class NPCPersonality:
    """NPC personality profile."""
    traits: List[PersonalityTrait] = field(default_factory=list)
    motivations: List[Motivation] = field(default_factory=list)
    quirks: List[str] = field(default_factory=list)
    mannerisms: List[str] = field(default_factory=list)
    speech_patterns: List[str] = field(default_factory=list)
    fears: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)


@dataclass
class NPCStats:
    """NPC statistics."""
    # Ability scores
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    # Derived stats
    armor_class: int = 10
    hit_points: int = 8
    speed: int = 30
    proficiency_bonus: int = 2
    
    # Skills
    skills: Dict[str, int] = field(default_factory=dict)
    saving_throws: Dict[str, int] = field(default_factory=dict)
    
    # Combat
    damage_resistances: List[DamageType] = field(default_factory=list)
    damage_immunities: List[DamageType] = field(default_factory=list)
    condition_immunities: List[ConditionType] = field(default_factory=list)
    
    # Senses
    passive_perception: int = 10
    languages: List[str] = field(default_factory=list)
    
    # Challenge rating and XP
    challenge_rating: float = 0.125
    experience_points: int = 25


@dataclass
class GeneratedNPC:
    """Complete generated NPC."""
    # Basic information
    name: str = ""
    race: str = "human"
    gender: str = "nonbinary"
    age: int = 25
    occupation: str = "commoner"
    role: NPCRole = NPCRole.COMMONER
    
    # Physical description
    appearance: str = ""
    height: str = "average"
    build: str = "average"
    distinctive_features: List[str] = field(default_factory=list)
    
    # Stats and abilities
    stats: NPCStats = field(default_factory=NPCStats)
    personality: NPCPersonality = field(default_factory=NPCPersonality)
    
    # Background
    background: str = ""
    backstory: str = ""
    current_situation: str = ""
    goals: List[str] = field(default_factory=list)
    
    # Relationships and connections
    allies: List[str] = field(default_factory=list)
    enemies: List[str] = field(default_factory=list)
    family: List[str] = field(default_factory=list)
    
    # Equipment and possessions
    equipment: List[str] = field(default_factory=list)
    wealth_level: str = "poor"
    notable_possessions: List[str] = field(default_factory=list)
    
    # Roleplay information
    voice_description: str = ""
    catchphrases: List[str] = field(default_factory=list)
    rumors: List[str] = field(default_factory=list)
    
    # Plot hooks
    plot_hooks: List[str] = field(default_factory=list)
    quest_ideas: List[str] = field(default_factory=list)


class NPCGenerator:
    """Service for generating NPCs with personalities and stats."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize NPC generator with optional random seed."""
        self.random = random.Random(seed)
        self._load_name_tables()
        self._load_description_tables()
        self._load_personality_tables()
        self._load_background_tables()
    
    def generate_npc(
        self, 
        role: Optional[NPCRole] = None,
        race: Optional[str] = None,
        level: Optional[int] = None,
        challenge_rating: Optional[float] = None,
        customization: Optional[Dict[str, Any]] = None
    ) -> GeneratedNPC:
        """Generate a complete NPC."""
        npc = GeneratedNPC()
        
        # Basic information
        npc.role = role or self.random.choice(list(NPCRole))
        npc.race = race or self._generate_race()
        npc.gender = self._generate_gender()
        npc.age = self._generate_age(npc.race)
        npc.name = self._generate_name(npc.race, npc.gender)
        
        # Physical description
        npc.appearance = self._generate_appearance(npc.race, npc.gender)
        npc.height = self._generate_height(npc.race, npc.gender)
        npc.build = self._generate_build()
        npc.distinctive_features = self._generate_distinctive_features()
        
        # Generate stats
        npc.stats = self._generate_stats(npc.role, level, challenge_rating)
        
        # Generate personality
        npc.personality = self._generate_personality(npc.role)
        
        # Background and story
        npc.occupation = self._generate_occupation(npc.role)
        npc.background = self._generate_background(npc.race, npc.role)
        npc.backstory = self._generate_backstory(npc)
        npc.current_situation = self._generate_current_situation(npc)
        npc.goals = self._generate_goals(npc.personality.motivations)
        
        # Equipment and wealth
        npc.wealth_level = self._generate_wealth_level(npc.role, npc.occupation)
        npc.equipment = self._generate_equipment(npc.role, npc.occupation)
        npc.notable_possessions = self._generate_notable_possessions(npc)
        
        # Roleplay elements
        npc.voice_description = self._generate_voice_description()
        npc.catchphrases = self._generate_catchphrases(npc.personality)
        npc.rumors = self._generate_rumors(npc)
        
        # Plot integration
        npc.plot_hooks = self._generate_plot_hooks(npc)
        npc.quest_ideas = self._generate_quest_ideas(npc)
        
        # Apply customizations
        if customization:
            self._apply_customizations(npc, customization)
        
        return npc
    
    def generate_npc_group(
        self, 
        count: int, 
        group_type: str = "random",
        shared_background: bool = True
    ) -> List[GeneratedNPC]:
        """Generate a group of related NPCs."""
        npcs = []
        
        # Determine group roles
        if group_type == "village":
            roles = [NPCRole.COMMONER] * (count - 3) + [
                NPCRole.MERCHANT, NPCRole.GUARD, NPCRole.INNKEEPER
            ]
        elif group_type == "noble_court":
            roles = [NPCRole.NOBLE] * (count - 2) + [NPCRole.GUARD, NPCRole.SCHOLAR]
        elif group_type == "criminal_gang":
            roles = [NPCRole.CRIMINAL] * (count - 1) + [NPCRole.VILLAIN]
        elif group_type == "merchant_caravan":
            roles = [NPCRole.MERCHANT] + [NPCRole.GUARD] * (count - 1)
        else:  # random
            roles = [self.random.choice(list(NPCRole)) for _ in range(count)]
        
        # Generate shared background elements if requested
        shared_location = None
        shared_event = None
        
        if shared_background:
            shared_location = self.random.choice([
                "the same village", "the same noble house", "the same guild",
                "the same military unit", "the same temple", "the same criminal organization"
            ])
            shared_event = self.random.choice([
                "survived a great war together", "witnessed a mysterious event",
                "served under the same master", "escaped from captivity together",
                "discovered a secret together", "lost someone important to them"
            ])
        
        # Generate NPCs
        for i, role in enumerate(roles):
            npc = self.generate_npc(role=role)
            
            if shared_background:
                npc.backstory += f" They have connections to {shared_location} and {shared_event}."
                
                # Add relationships to other group members
                for j, other_npc in enumerate(npcs):
                    if i != j:
                        relationship = self.random.choice([
                            "ally", "friend", "colleague", "former_colleague", 
                            "acquaintance", "family", "rival"
                        ])
                        npc.personality.relationships[other_npc.name] = relationship
            
            npcs.append(npc)
        
        return npcs
    
    def _load_name_tables(self):
        """Load name generation tables."""
        self.names = {
            "human": {
                "male": ["Aerdric", "Ahvak", "Aramil", "Aranor", "Berris", "Cithreth", "Dayereth", "Enna", "Galinndan", "Hadarai"],
                "female": ["Adrie", "Ahvna", "Aramil", "Aranor", "Berris", "Caelynn", "Dayereth", "Enna", "Galinndan", "Hadarai"],
                "nonbinary": ["Ari", "Ash", "Bay", "Cam", "Drew", "Fern", "Gray", "Kai", "River", "Sky"]
            },
            "elf": {
                "male": ["Adran", "Aelar", "Aramil", "Aranor", "Berris", "Dayereth", "Enna", "Galinndan", "Hadarai", "Halimath"],
                "female": ["Adrie", "Ahvna", "Aramil", "Aranor", "Berris", "Caelynn", "Dayereth", "Enna", "Galinndan", "Hadarai"],
                "nonbinary": ["Aerdric", "Ahvak", "Berrian", "Carric", "Drannor", "Enna", "Galinndan", "Hadarai", "Halimath", "Heian"]
            },
            "dwarf": {
                "male": ["Adrik", "Baern", "Darrak", "Eberk", "Fargrim", "Gardain", "Harbek", "Kildrak", "Morgran", "Orsik"],
                "female": ["Amber", "Bardryn", "Diesa", "Eldeth", "Gunnloda", "Gvanna", "Hlin", "Kathra", "Kristryd", "Ilde"],
                "nonbinary": ["Baern", "Darrak", "Diesa", "Eberk", "Fargrim", "Gunnloda", "Harbek", "Kathra", "Kildrak", "Morgran"]
            }
        }
    
    def _load_description_tables(self):
        """Load physical description tables."""
        self.descriptions = {
            "height": ["very short", "short", "below average", "average", "above average", "tall", "very tall"],
            "build": ["skeletal", "thin", "lean", "average", "stocky", "muscular", "heavy", "obese"],
            "hair_color": ["bald", "black", "brown", "auburn", "red", "blonde", "gray", "white", "unusual"],
            "eye_color": ["brown", "blue", "green", "hazel", "gray", "amber", "violet", "heterochromatic"],
            "skin_tone": ["pale", "fair", "light", "medium", "olive", "tan", "dark", "very dark"],
            "distinctive_features": [
                "scar across face", "missing finger", "distinctive birthmark", "unusual eye color",
                "prominent nose", "gap-toothed smile", "distinctive voice", "nervous tic",
                "elaborate tattoo", "unusual hair style", "limp", "stutter",
                "always wears a hat", "carries unusual item", "smells of herbs", "has a pet"
            ]
        }
    
    def _load_personality_tables(self):
        """Load personality generation tables."""
        self.personality_data = {
            "quirks": [
                "always speaks in rhyme", "collects unusual items", "never sits down",
                "constantly snacking", "hums while working", "afraid of the dark",
                "superstitious about numbers", "talks to animals", "never removes gloves",
                "always cold", "laughs at inappropriate times", "counts everything"
            ],
            "mannerisms": [
                "drums fingers when thinking", "adjusts clothing frequently", "avoids eye contact",
                "gestures wildly when speaking", "whispers secrets", "speaks very loudly",
                "picks at fingernails", "fidgets with jewelry", "stands too close",
                "backs away when nervous", "touches their nose when lying"
            ],
            "speech_patterns": [
                "speaks in short sentences", "uses big words incorrectly", "repeats themselves",
                "asks lots of questions", "never finishes sentences", "speaks in metaphors",
                "uses unusual expressions", "mixes languages", "has a strong accent",
                "speaks very slowly", "talks very fast", "uses formal language"
            ]
        }
    
    def _load_background_tables(self):
        """Load background generation tables."""
        self.backgrounds = {
            "origins": [
                "born into poverty", "raised by relatives", "noble birth", "merchant family",
                "military family", "religious upbringing", "criminal background", "scholarly family",
                "artisan tradition", "farming family", "orphaned young", "mysterious past"
            ],
            "life_events": [
                "survived a plague", "witnessed a great battle", "discovered a secret",
                "lost everything in a fire", "found a treasure", "made a powerful enemy",
                "gained a mentor", "fell in love", "broke an oath", "performed a great deed",
                "committed a crime", "received a prophetic vision"
            ]
        }
    
    def _generate_race(self) -> str:
        """Generate a random race."""
        races = ["human", "elf", "dwarf", "halfling", "gnome", "half-elf", "half-orc", "dragonborn", "tiefling"]
        return self.random.choice(races)
    
    def _generate_gender(self) -> str:
        """Generate a random gender."""
        return self.random.choice(["male", "female", "nonbinary"])
    
    def _generate_age(self, race: str) -> int:
        """Generate age appropriate for race."""
        age_ranges = {
            "human": (18, 80),
            "elf": (100, 750),
            "dwarf": (50, 350),
            "halfling": (25, 150),
            "gnome": (40, 400),
            "half-elf": (20, 180),
            "half-orc": (15, 75),
            "dragonborn": (15, 80),
            "tiefling": (18, 100)
        }
        
        min_age, max_age = age_ranges.get(race, (18, 80))
        return self.random.randint(min_age, max_age)
    
    def _generate_name(self, race: str, gender: str) -> str:
        """Generate a name based on race and gender."""
        race_names = self.names.get(race, self.names["human"])
        names = race_names.get(gender, race_names["nonbinary"])
        return self.random.choice(names)
    
    def _generate_appearance(self, race: str, gender: str) -> str:
        """Generate physical appearance description."""
        features = []
        
        # Basic features
        hair_color = self.random.choice(self.descriptions["hair_color"])
        eye_color = self.random.choice(self.descriptions["eye_color"])
        skin_tone = self.random.choice(self.descriptions["skin_tone"])
        
        if hair_color != "bald":
            features.append(f"{hair_color} hair")
        else:
            features.append("bald")
        
        features.append(f"{eye_color} eyes")
        features.append(f"{skin_tone} skin")
        
        return ", ".join(features)
    
    def _generate_height(self, race: str, gender: str) -> str:
        """Generate height description."""
        return self.random.choice(self.descriptions["height"])
    
    def _generate_build(self) -> str:
        """Generate build description."""
        return self.random.choice(self.descriptions["build"])
    
    def _generate_distinctive_features(self) -> List[str]:
        """Generate distinctive features."""
        count = self.random.choices([0, 1, 2, 3], weights=[20, 50, 25, 5])[0]
        return self.random.sample(self.descriptions["distinctive_features"], count)
    
    def _generate_stats(
        self, 
        role: NPCRole, 
        level: Optional[int] = None,
        challenge_rating: Optional[float] = None
    ) -> NPCStats:
        """Generate NPC statistics."""
        stats = NPCStats()
        
        # Determine level and CR
        if level is None:
            level = self._get_default_level_for_role(role)
        
        if challenge_rating is None:
            challenge_rating = self._get_default_cr_for_role(role)
        
        # Generate ability scores based on role
        ability_arrays = self._get_ability_array_for_role(role)
        stats.strength = self.random.randint(*ability_arrays.get("strength", (8, 12)))
        stats.dexterity = self.random.randint(*ability_arrays.get("dexterity", (8, 12)))
        stats.constitution = self.random.randint(*ability_arrays.get("constitution", (8, 12)))
        stats.intelligence = self.random.randint(*ability_arrays.get("intelligence", (8, 12)))
        stats.wisdom = self.random.randint(*ability_arrays.get("wisdom", (8, 12)))
        stats.charisma = self.random.randint(*ability_arrays.get("charisma", (8, 12)))
        
        # Calculate derived stats
        stats.proficiency_bonus = max(2, ((level - 1) // 4) + 2)
        
        # AC calculation (simplified)
        dex_mod = calculate_modifier(stats.dexterity)
        stats.armor_class = 10 + dex_mod + self._get_armor_bonus_for_role(role)
        
        # HP calculation
        hit_die = self._get_hit_die_for_role(role)
        con_mod = calculate_modifier(stats.constitution)
        stats.hit_points = hit_die + con_mod + ((level - 1) * ((hit_die // 2) + 1 + con_mod))
        stats.hit_points = max(1, stats.hit_points)
        
        # Skills based on role
        stats.skills = self._get_skills_for_role(role, stats)
        
        # Passive Perception
        perception_bonus = stats.skills.get("perception", calculate_modifier(stats.wisdom))
        stats.passive_perception = 10 + perception_bonus
        
        # Languages
        stats.languages = ["Common"] + self._get_additional_languages(role)
        
        # Challenge rating and XP
        stats.challenge_rating = challenge_rating
        stats.experience_points = self._calculate_xp_from_cr(challenge_rating)
        
        return stats
    
    def _generate_personality(self, role: NPCRole) -> NPCPersonality:
        """Generate NPC personality."""
        personality = NPCPersonality()
        
        # Generate traits based on role
        trait_weights = self._get_trait_weights_for_role(role)
        trait_count = self.random.choices([1, 2, 3], weights=[50, 35, 15])[0]
        
        all_traits = list(PersonalityTrait)
        personality.traits = self.random.choices(all_traits, weights=trait_weights, k=trait_count)
        
        # Generate motivations
        motivation_weights = self._get_motivation_weights_for_role(role)
        motivation_count = self.random.choices([1, 2], weights=[70, 30])[0]
        
        all_motivations = list(Motivation)
        personality.motivations = self.random.choices(all_motivations, weights=motivation_weights, k=motivation_count)
        
        # Generate quirks, mannerisms, etc.
        quirk_count = self.random.choices([0, 1, 2], weights=[40, 50, 10])[0]
        personality.quirks = self.random.sample(self.personality_data["quirks"], quirk_count)
        
        mannerism_count = self.random.choices([1, 2], weights=[80, 20])[0]
        personality.mannerisms = self.random.sample(self.personality_data["mannerisms"], mannerism_count)
        
        speech_count = self.random.choices([0, 1, 2], weights=[30, 60, 10])[0]
        personality.speech_patterns = self.random.sample(self.personality_data["speech_patterns"], speech_count)
        
        # Generate fears and secrets
        fear_count = self.random.choices([0, 1, 2], weights=[60, 35, 5])[0]
        personality.fears = self._generate_fears(fear_count)
        
        secret_count = self.random.choices([0, 1, 2], weights=[40, 50, 10])[0]
        personality.secrets = self._generate_secrets(secret_count, role)
        
        return personality
    
    def _generate_occupation(self, role: NPCRole) -> str:
        """Generate occupation based on role."""
        occupations = {
            NPCRole.QUEST_GIVER: ["village elder", "guild master", "retired adventurer", "local noble"],
            NPCRole.MERCHANT: ["shopkeeper", "trader", "peddler", "caravan master", "fence"],
            NPCRole.GUARD: ["town guard", "city watch", "bouncer", "bodyguard", "soldier"],
            NPCRole.NOBLE: ["lord", "lady", "baron", "count", "duke", "heir"],
            NPCRole.COMMONER: ["farmer", "laborer", "servant", "baker", "brewer", "tailor"],
            NPCRole.SCHOLAR: ["sage", "librarian", "scribe", "wizard", "researcher", "teacher"],
            NPCRole.PRIEST: ["cleric", "acolyte", "temple keeper", "missionary", "healer"],
            NPCRole.CRIMINAL: ["thief", "smuggler", "con artist", "pickpocket", "burglar", "assassin"],
            NPCRole.SOLDIER: ["warrior", "knight", "mercenary", "veteran", "sergeant", "captain"],
            NPCRole.ARTISAN: ["blacksmith", "carpenter", "jeweler", "mason", "potter", "weaver"],
            NPCRole.INNKEEPER: ["innkeeper", "barkeep", "tavern owner", "cook", "stable master"]
        }
        
        role_occupations = occupations.get(role, ["commoner"])
        return self.random.choice(role_occupations)
    
    def _get_default_level_for_role(self, role: NPCRole) -> int:
        """Get default level for role."""
        level_ranges = {
            NPCRole.COMMONER: (1, 3),
            NPCRole.GUARD: (2, 4),
            NPCRole.MERCHANT: (1, 5),
            NPCRole.SCHOLAR: (3, 8),
            NPCRole.NOBLE: (2, 6),
            NPCRole.PRIEST: (3, 7),
            NPCRole.CRIMINAL: (2, 6),
            NPCRole.SOLDIER: (3, 8),
            NPCRole.VILLAIN: (5, 15),
            NPCRole.BOSS: (8, 20)
        }
        
        min_level, max_level = level_ranges.get(role, (1, 3))
        return self.random.randint(min_level, max_level)
    
    def _get_default_cr_for_role(self, role: NPCRole) -> float:
        """Get default challenge rating for role."""
        cr_ranges = {
            NPCRole.COMMONER: [0, 0.125, 0.25],
            NPCRole.GUARD: [0.25, 0.5, 1],
            NPCRole.MERCHANT: [0.125, 0.25, 0.5],
            NPCRole.SCHOLAR: [0.25, 0.5, 1],
            NPCRole.NOBLE: [0.5, 1, 2],
            NPCRole.PRIEST: [1, 2, 3],
            NPCRole.CRIMINAL: [0.5, 1, 2],
            NPCRole.SOLDIER: [1, 2, 3],
            NPCRole.VILLAIN: [3, 5, 8],
            NPCRole.BOSS: [8, 12, 16]
        }
        
        cr_options = cr_ranges.get(role, [0.125, 0.25, 0.5])
        return self.random.choice(cr_options)
    
    def _generate_backstory(self, npc: GeneratedNPC) -> str:
        """Generate a backstory for the NPC."""
        origin = self.random.choice(self.backgrounds["origins"])
        life_event = self.random.choice(self.backgrounds["life_events"])
        
        backstory_templates = [
            f"{npc.name} was {origin}. During their youth, they {life_event}.",
            f"Having been {origin}, {npc.name} later {life_event}, which shaped their worldview.",
            f"{npc.name}'s story begins with being {origin}. A defining moment came when they {life_event}."
        ]
        
        return self.random.choice(backstory_templates)
    
    def _generate_plot_hooks(self, npc: GeneratedNPC) -> List[str]:
        """Generate plot hooks involving this NPC."""
        hooks = []
        
        # Hooks based on role
        role_hooks = {
            NPCRole.QUEST_GIVER: [
                "Has a dangerous mission that needs capable adventurers",
                "Knows the location of a lost treasure",
                "Seeks revenge against a powerful enemy"
            ],
            NPCRole.MERCHANT: [
                "Is being extorted by criminals", 
                "Has rare items for sale",
                "Knows about smuggling operations"
            ],
            NPCRole.SCHOLAR: [
                "Has discovered dangerous knowledge",
                "Is researching ancient mysteries",
                "Has been threatened by mysterious figures"
            ],
            NPCRole.CRIMINAL: [
                "Is planning a major heist",
                "Has information about corruption",
                "Is being hunted by the law"
            ]
        }
        
        hooks.extend(role_hooks.get(npc.role, ["Has a secret that could change everything"]))
        
        # Hooks based on personality
        if Motivation.REVENGE in npc.personality.motivations:
            hooks.append("Seeks vengeance against those who wronged them")
        
        if Motivation.KNOWLEDGE in npc.personality.motivations:
            hooks.append("Will trade valuable information for the right price")
        
        return self.random.sample(hooks, min(3, len(hooks)))
    
    def _apply_customizations(self, npc: GeneratedNPC, customization: Dict[str, Any]):
        """Apply customizations to the generated NPC."""
        for key, value in customization.items():
            if hasattr(npc, key):
                setattr(npc, key, value)
            elif hasattr(npc.stats, key):
                setattr(npc.stats, key, value)
            elif hasattr(npc.personality, key):
                setattr(npc.personality, key, value)
    
    # Helper methods for stats generation
    def _get_ability_array_for_role(self, role: NPCRole) -> Dict[str, Tuple[int, int]]:
        """Get ability score ranges for role."""
        # This is a simplified version - could be much more detailed
        arrays = {
            NPCRole.SCHOLAR: {
                "intelligence": (14, 18),
                "wisdom": (12, 16)
            },
            NPCRole.GUARD: {
                "strength": (13, 16),
                "constitution": (12, 15)
            },
            NPCRole.MERCHANT: {
                "charisma": (13, 16),
                "intelligence": (11, 14)
            }
        }
        
        return arrays.get(role, {})
    
    def _get_armor_bonus_for_role(self, role: NPCRole) -> int:
        """Get armor bonus for role."""
        bonuses = {
            NPCRole.GUARD: 4,  # Chain mail
            NPCRole.SOLDIER: 5,  # Splint armor
            NPCRole.NOBLE: 2,   # Leather armor
            NPCRole.CRIMINAL: 1  # Studded leather
        }
        
        return bonuses.get(role, 0)
    
    def _get_hit_die_for_role(self, role: NPCRole) -> int:
        """Get hit die size for role."""
        hit_dice = {
            NPCRole.COMMONER: 4,
            NPCRole.SCHOLAR: 6,
            NPCRole.MERCHANT: 6,
            NPCRole.PRIEST: 8,
            NPCRole.CRIMINAL: 8,
            NPCRole.GUARD: 8,
            NPCRole.SOLDIER: 10,
            NPCRole.NOBLE: 8,
            NPCRole.VILLAIN: 10,
            NPCRole.BOSS: 12
        }
        
        return hit_dice.get(role, 8)
    
    def _calculate_xp_from_cr(self, cr: float) -> int:
        """Calculate XP reward from challenge rating."""
        xp_table = {
            0: 10, 0.125: 25, 0.25: 50, 0.5: 100,
            1: 200, 2: 450, 3: 700, 4: 1100, 5: 1800,
            6: 2300, 7: 2900, 8: 3900, 9: 5000, 10: 5900
        }
        
        return xp_table.get(cr, 25)
    
    # Additional helper methods would go here...