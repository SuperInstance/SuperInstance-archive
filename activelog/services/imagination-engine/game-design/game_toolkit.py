#!/usr/bin/env python3

import asyncio
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random
import uuid
import math

class GameGenre(Enum):
    ACTION = "action"
    ADVENTURE = "adventure"
    RPG = "rpg"
    STRATEGY = "strategy"
    PUZZLE = "puzzle"
    SIMULATION = "simulation"
    PLATFORMER = "platformer"
    RACING = "racing"
    SPORTS = "sports"
    HORROR = "horror"

class GamePlatform(Enum):
    PC = "pc"
    MOBILE = "mobile"
    CONSOLE = "console"
    WEB = "web"
    VR = "vr"
    AR = "ar"

class DifficultyLevel(Enum):
    VERY_EASY = "very_easy"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    VERY_HARD = "very_hard"

@dataclass
class GameMechanic:
    id: str
    name: str
    description: str
    complexity: int  # 1-10 scale
    fun_factor: int  # 1-10 scale
    implementation_difficulty: int  # 1-10 scale
    genre_compatibility: List[GameGenre]
    examples: List[str]
    variations: List[str]

@dataclass
class GameLevel:
    id: str
    name: str
    objective: str
    difficulty: DifficultyLevel
    estimated_play_time: int  # minutes
    mechanics_used: List[str]  # Mechanic IDs
    challenges: List[str]
    rewards: List[str]
    narrative_context: str
    layout_description: str
    enemy_types: List[str]
    collectibles: List[str]

@dataclass
class GameCharacter:
    id: str
    name: str
    role: str  # player, npc, enemy, boss
    description: str
    abilities: List[str]
    stats: Dict[str, int]
    personality_traits: List[str]
    backstory: str
    visual_design: str
    voice_characteristics: str
    gameplay_function: str

@dataclass
class GameSystem:
    id: str
    name: str
    description: str
    rules: List[str]
    interactions: Dict[str, str]  # How it interacts with other systems
    balancing_factors: List[str]
    player_impact: str
    complexity_level: int  # 1-10

@dataclass
class GameProject:
    id: str
    title: str
    genre: GameGenre
    platform: GamePlatform
    target_audience: str
    core_concept: str
    unique_selling_points: List[str]
    mechanics: List[GameMechanic]
    characters: List[GameCharacter]
    levels: List[GameLevel]
    systems: List[GameSystem]
    art_style: str
    audio_style: str
    monetization: str
    estimated_dev_time: int  # months
    team_size_needed: int
    technical_requirements: List[str]
    created_at: str
    updated_at: str

class MechanicLibrary:
    def __init__(self):
        self.base_mechanics = {
            "jump": GameMechanic(
                id="jump",
                name="Jumping",
                description="Player character can jump to overcome obstacles and reach higher platforms",
                complexity=2,
                fun_factor=7,
                implementation_difficulty=3,
                genre_compatibility=[GameGenre.PLATFORMER, GameGenre.ACTION, GameGenre.ADVENTURE],
                examples=["Super Mario Bros", "Sonic the Hedgehog", "Celeste"],
                variations=["Double jump", "Wall jump", "Variable height jump"]
            ),
            
            "combat": GameMechanic(
                id="combat",
                name="Combat System",
                description="Players engage in battles with enemies using various attacks and defenses",
                complexity=8,
                fun_factor=9,
                implementation_difficulty=7,
                genre_compatibility=[GameGenre.ACTION, GameGenre.RPG, GameGenre.ADVENTURE],
                examples=["Dark Souls", "Street Fighter", "The Witcher"],
                variations=["Turn-based", "Real-time", "Combo-based", "Tactical"]
            ),
            
            "resource_management": GameMechanic(
                id="resource_management",
                name="Resource Management",
                description="Players must collect, manage, and spend limited resources strategically",
                complexity=6,
                fun_factor=7,
                implementation_difficulty=5,
                genre_compatibility=[GameGenre.STRATEGY, GameGenre.SIMULATION, GameGenre.RPG],
                examples=["StarCraft", "Civilization", "Animal Crossing"],
                variations=["Energy/Mana", "Currency", "Materials", "Time"]
            ),
            
            "puzzle_solving": GameMechanic(
                id="puzzle_solving",
                name="Puzzle Solving",
                description="Players solve logical or spatial puzzles to progress",
                complexity=7,
                fun_factor=8,
                implementation_difficulty=6,
                genre_compatibility=[GameGenre.PUZZLE, GameGenre.ADVENTURE, GameGenre.STRATEGY],
                examples=["Portal", "Tetris", "Monument Valley"],
                variations=["Logic puzzles", "Physics puzzles", "Pattern matching"]
            ),
            
            "exploration": GameMechanic(
                id="exploration",
                name="Exploration",
                description="Players discover new areas, secrets, and content by exploring the game world",
                complexity=5,
                fun_factor=8,
                implementation_difficulty=4,
                genre_compatibility=[GameGenre.ADVENTURE, GameGenre.RPG, GameGenre.ACTION],
                examples=["Zelda: Breath of the Wild", "Metroid", "Skyrim"],
                variations=["Open world", "Metroidvania", "Linear progression"]
            ),
            
            "collection": GameMechanic(
                id="collection",
                name="Collection",
                description="Players gather items, achievements, or collectibles throughout the game",
                complexity=3,
                fun_factor=6,
                implementation_difficulty=3,
                genre_compatibility=[GameGenre.ADVENTURE, GameGenre.RPG, GameGenre.PLATFORMER],
                examples=["Pokemon", "Banjo-Kazooie", "Assassin's Creed"],
                variations=["Item collection", "Achievement hunting", "Card collection"]
            ),
            
            "progression": GameMechanic(
                id="progression",
                name="Character Progression",
                description="Players improve their character's abilities, stats, or equipment over time",
                complexity=7,
                fun_factor=9,
                implementation_difficulty=6,
                genre_compatibility=[GameGenre.RPG, GameGenre.ACTION, GameGenre.STRATEGY],
                examples=["Final Fantasy", "Diablo", "World of Warcraft"],
                variations=["Level-based", "Skill trees", "Equipment upgrades"]
            ),
            
            "crafting": GameMechanic(
                id="crafting",
                name="Crafting System",
                description="Players combine materials to create new items, tools, or equipment",
                complexity=6,
                fun_factor=7,
                implementation_difficulty=5,
                genre_compatibility=[GameGenre.SIMULATION, GameGenre.RPG, GameGenre.ADVENTURE],
                examples=["Minecraft", "Terraria", "Subnautica"],
                variations=["Recipe-based", "Experimental", "Skill-dependent"]
            ),
            
            "stealth": GameMechanic(
                id="stealth",
                name="Stealth",
                description="Players avoid detection by enemies through careful movement and timing",
                complexity=6,
                fun_factor=7,
                implementation_difficulty=7,
                genre_compatibility=[GameGenre.ACTION, GameGenre.ADVENTURE, GameGenre.STRATEGY],
                examples=["Metal Gear Solid", "Hitman", "Assassin's Creed"],
                variations=["Line of sight", "Sound-based", "Disguise system"]
            ),
            
            "time_manipulation": GameMechanic(
                id="time_manipulation",
                name="Time Manipulation",
                description="Players can control time flow to solve puzzles or gain advantages",
                complexity=9,
                fun_factor=9,
                implementation_difficulty=9,
                genre_compatibility=[GameGenre.PUZZLE, GameGenre.ACTION, GameGenre.ADVENTURE],
                examples=["Braid", "Prince of Persia", "Life is Strange"],
                variations=["Rewind", "Slow motion", "Time stop", "Time loops"]
            )
        }

    def get_mechanic(self, mechanic_id: str) -> Optional[GameMechanic]:
        return self.base_mechanics.get(mechanic_id)

    def get_mechanics_by_genre(self, genre: GameGenre) -> List[GameMechanic]:
        return [mechanic for mechanic in self.base_mechanics.values() 
                if genre in mechanic.genre_compatibility]

    def suggest_mechanic_combinations(self, primary_genre: GameGenre, 
                                    secondary_genre: GameGenre = None) -> List[Tuple[GameMechanic, GameMechanic]]:
        primary_mechanics = self.get_mechanics_by_genre(primary_genre)
        
        if secondary_genre:
            secondary_mechanics = self.get_mechanics_by_genre(secondary_genre)
            combinations = []
            
            for primary in primary_mechanics:
                for secondary in secondary_mechanics:
                    if primary.id != secondary.id:
                        combinations.append((primary, secondary))
            
            return combinations[:5]  # Top 5 combinations
        else:
            # Suggest complementary mechanics within the same genre
            combinations = []
            for i, mech1 in enumerate(primary_mechanics):
                for mech2 in primary_mechanics[i+1:]:
                    combinations.append((mech1, mech2))
            
            return combinations[:5]

class GameBalancer:
    def __init__(self):
        self.difficulty_curves = {
            "linear": lambda level: level * 1.2,
            "exponential": lambda level: math.pow(1.3, level),
            "logarithmic": lambda level: math.log(level + 1) * 3,
            "stepped": lambda level: (level // 3 + 1) * 2
        }

    def calculate_difficulty_progression(self, num_levels: int, 
                                       curve_type: str = "linear") -> List[float]:
        curve_func = self.difficulty_curves.get(curve_type, self.difficulty_curves["linear"])
        return [curve_func(i) for i in range(1, num_levels + 1)]

    def balance_character_stats(self, character: GameCharacter, 
                              target_power_level: int) -> Dict[str, int]:
        """Balance character stats to match target power level."""
        stats = character.stats.copy()
        current_total = sum(stats.values())
        
        if current_total == 0:
            # Initialize with balanced stats
            num_stats = len(stats)
            base_value = target_power_level // num_stats
            for stat in stats:
                stats[stat] = base_value
        else:
            # Scale existing stats
            scale_factor = target_power_level / current_total
            for stat in stats:
                stats[stat] = int(stats[stat] * scale_factor)
        
        return stats

    def suggest_level_pacing(self, total_levels: int, 
                           target_hours: int) -> Dict[str, Any]:
        """Suggest level pacing and structure."""
        
        # Basic pacing structure
        tutorial_levels = max(1, total_levels // 10)
        main_levels = total_levels - tutorial_levels - 1  # -1 for final boss
        boss_levels = max(1, total_levels // 8)
        
        minutes_per_level = (target_hours * 60) / total_levels
        
        pacing = {
            "total_levels": total_levels,
            "tutorial_levels": tutorial_levels,
            "main_levels": main_levels,
            "boss_levels": boss_levels,
            "average_minutes_per_level": round(minutes_per_level, 1),
            "progression_structure": [
                {"type": "tutorial", "levels": tutorial_levels, "description": "Learning basics"},
                {"type": "early_game", "levels": main_levels // 3, "description": "Establishing mechanics"},
                {"type": "mid_game", "levels": main_levels // 3, "description": "Complexity increases"},
                {"type": "late_game", "levels": main_levels // 3, "description": "Mastery required"},
                {"type": "finale", "levels": 1, "description": "Final challenge"}
            ]
        }
        
        return pacing

class GameGenerator:
    def __init__(self):
        self.mechanic_library = MechanicLibrary()
        self.game_balancer = GameBalancer()
        
        self.concept_templates = {
            GameGenre.ACTION: [
                "A fast-paced combat game where {player} fights {enemies} using {weapon} to {goal}",
                "An intense battle experience featuring {unique_mechanic} in a {setting} environment"
            ],
            GameGenre.ADVENTURE: [
                "An epic journey where {player} explores {world} to discover {mystery}",
                "A story-driven adventure combining {mechanic1} and {mechanic2} in {setting}"
            ],
            GameGenre.PUZZLE: [
                "A mind-bending puzzle game using {unique_mechanic} to solve {challenge_type} challenges",
                "A creative problem-solving experience where players must {action} using {tool}"
            ],
            GameGenre.RPG: [
                "A character-driven RPG where players develop {character_type} abilities to {quest_goal}",
                "An immersive world where {progression_system} meets {social_system}"
            ]
        }
        
        self.art_styles = [
            "Pixel Art", "Low Poly 3D", "Hand-drawn 2D", "Photorealistic 3D", 
            "Cel-shaded", "Minimalist", "Retro Synthwave", "Watercolor", 
            "Comic Book", "Abstract Geometric"
        ]
        
        self.audio_styles = [
            "Orchestral Epic", "Electronic Synthwave", "Ambient Atmospheric", 
            "Rock/Metal", "Jazzy Noir", "Folk Acoustic", "Chiptune Retro",
            "Minimalist Piano", "World Music", "Industrial Techno"
        ]

    def generate_game_concept(self, genre: GameGenre, 
                            platform: GamePlatform,
                            target_audience: str = "general") -> Dict[str, Any]:
        """Generate a complete game concept."""
        
        # Select appropriate mechanics for genre
        mechanics = self.mechanic_library.get_mechanics_by_genre(genre)
        core_mechanics = random.sample(mechanics, min(3, len(mechanics)))
        
        # Generate concept description
        template = random.choice(self.concept_templates.get(genre, [
            "An innovative {genre} game featuring unique gameplay mechanics"
        ]))
        
        concept_vars = {
            "player": random.choice(["hero", "adventurer", "protagonist", "character"]),
            "enemies": random.choice(["monsters", "robots", "aliens", "villains"]),
            "weapon": random.choice(["sword", "magic", "technology", "skills"]),
            "goal": random.choice(["save the world", "uncover truth", "restore peace", "find treasure"]),
            "setting": random.choice(["fantasy", "sci-fi", "modern", "historical"]),
            "world": random.choice(["mystical realm", "alien planet", "post-apocalyptic earth", "parallel dimension"]),
            "mystery": random.choice(["ancient secrets", "lost civilization", "hidden conspiracy", "magical phenomenon"]),
            "unique_mechanic": random.choice([mech.name.lower() for mech in core_mechanics]),
            "mechanic1": core_mechanics[0].name.lower() if len(core_mechanics) > 0 else "exploration",
            "mechanic2": core_mechanics[1].name.lower() if len(core_mechanics) > 1 else "combat"
        }
        
        core_concept = template.format(**concept_vars)
        
        return {
            "core_concept": core_concept,
            "mechanics": [mech.name for mech in core_mechanics],
            "art_style": random.choice(self.art_styles),
            "audio_style": random.choice(self.audio_styles),
            "unique_selling_points": self._generate_unique_selling_points(genre, core_mechanics),
            "target_platform_considerations": self._get_platform_considerations(platform)
        }

    def _generate_unique_selling_points(self, genre: GameGenre, 
                                      mechanics: List[GameMechanic]) -> List[str]:
        """Generate unique selling points for the game."""
        usps = []
        
        # Mechanic-based USPs
        for mechanic in mechanics:
            if mechanic.fun_factor >= 8:
                usps.append(f"Innovative {mechanic.name.lower()} system")
        
        # Genre-specific USPs
        genre_usps = {
            GameGenre.ACTION: ["Lightning-fast combat", "Adrenaline-pumping gameplay"],
            GameGenre.PUZZLE: ["Mind-bending challenges", "Creative problem solving"],
            GameGenre.RPG: ["Deep character customization", "Branching storylines"],
            GameGenre.ADVENTURE: ["Rich storytelling", "Immersive world exploration"]
        }
        
        usps.extend(random.sample(genre_usps.get(genre, ["Engaging gameplay"]), 2))
        
        # Add some general innovative features
        innovation_usps = [
            "Emergent gameplay possibilities",
            "Player choice consequences",
            "Dynamic difficulty adjustment",
            "Procedural content generation",
            "Cross-platform social features"
        ]
        
        usps.extend(random.sample(innovation_usps, 2))
        
        return usps[:5]  # Limit to 5 USPs

    def _get_platform_considerations(self, platform: GamePlatform) -> Dict[str, str]:
        """Get platform-specific considerations."""
        considerations = {
            GamePlatform.MOBILE: {
                "controls": "Touch-friendly interface with intuitive gestures",
                "performance": "Optimized for battery life and lower-end hardware",
                "monetization": "Free-to-play with optional in-app purchases",
                "session_length": "Short play sessions (5-15 minutes)"
            },
            GamePlatform.PC: {
                "controls": "Keyboard and mouse with optional controller support",
                "performance": "Scalable graphics settings for various hardware",
                "monetization": "Premium purchase or early access model",
                "session_length": "Medium to long play sessions (30+ minutes)"
            },
            GamePlatform.CONSOLE: {
                "controls": "Controller-optimized with haptic feedback",
                "performance": "Consistent performance targeting 60fps",
                "monetization": "Premium retail release with possible DLC",
                "session_length": "Long play sessions with save anywhere"
            },
            GamePlatform.WEB: {
                "controls": "Simple keyboard/mouse controls",
                "performance": "Lightweight for broad browser compatibility",
                "monetization": "Ad-supported or premium upgrade",
                "session_length": "Quick play sessions (10-30 minutes)"
            },
            GamePlatform.VR: {
                "controls": "Motion controllers with room-scale tracking",
                "performance": "High framerate (90fps+) for comfort",
                "monetization": "Premium purchase due to niche market",
                "session_length": "Short to medium sessions (20-45 minutes)"
            }
        }
        
        return considerations.get(platform, {
            "controls": "Standard input methods",
            "performance": "Optimized for target platform",
            "monetization": "Platform-appropriate model",
            "session_length": "Flexible play sessions"
        })

    def generate_level_structure(self, game_concept: Dict[str, Any], 
                                num_levels: int = 10) -> List[GameLevel]:
        """Generate level structure for the game."""
        levels = []
        
        difficulty_progression = self.game_balancer.calculate_difficulty_progression(
            num_levels, "exponential"
        )
        
        level_types = ["tutorial", "standard", "boss", "puzzle", "exploration"]
        
        for i in range(num_levels):
            level_id = str(uuid.uuid4())
            
            # Determine level type
            if i == 0:
                level_type = "tutorial"
            elif (i + 1) % 5 == 0:  # Every 5th level is a boss
                level_type = "boss"
            else:
                level_type = random.choice(["standard", "puzzle", "exploration"])
            
            # Calculate difficulty
            difficulty_value = difficulty_progression[i]
            if difficulty_value < 2:
                difficulty = DifficultyLevel.EASY
            elif difficulty_value < 4:
                difficulty = DifficultyLevel.MEDIUM
            elif difficulty_value < 6:
                difficulty = DifficultyLevel.HARD
            else:
                difficulty = DifficultyLevel.VERY_HARD
            
            level = GameLevel(
                id=level_id,
                name=f"Level {i + 1}: {self._generate_level_name(level_type)}",
                objective=self._generate_level_objective(level_type),
                difficulty=difficulty,
                estimated_play_time=self._estimate_level_time(level_type, difficulty),
                mechanics_used=game_concept["mechanics"][:2],  # Use core mechanics
                challenges=self._generate_level_challenges(level_type, difficulty),
                rewards=self._generate_level_rewards(level_type, i + 1),
                narrative_context=self._generate_narrative_context(i + 1, num_levels),
                layout_description=self._generate_layout_description(level_type),
                enemy_types=self._generate_enemy_types(level_type, difficulty),
                collectibles=self._generate_collectibles(level_type)
            )
            
            levels.append(level)
        
        return levels

    def _generate_level_name(self, level_type: str) -> str:
        names = {
            "tutorial": ["First Steps", "Training Grounds", "Learning the Ropes"],
            "standard": ["The Journey Begins", "Into the Unknown", "Trials Ahead"],
            "boss": ["Boss Confrontation", "Ultimate Test", "Final Stand"],
            "puzzle": ["Mind Bender", "The Riddle Chamber", "Logic Gate"],
            "exploration": ["Hidden Depths", "Secret Passages", "Uncharted Territory"]
        }
        
        return random.choice(names.get(level_type, ["Adventure Awaits"]))

    def _generate_level_objective(self, level_type: str) -> str:
        objectives = {
            "tutorial": "Learn the basic game mechanics and controls",
            "standard": "Navigate through the level while overcoming obstacles",
            "boss": "Defeat the powerful enemy using all learned skills",
            "puzzle": "Solve the complex puzzle to unlock the next area",
            "exploration": "Discover hidden secrets and collect valuable items"
        }
        
        return objectives.get(level_type, "Complete the level objectives")

    def _estimate_level_time(self, level_type: str, difficulty: DifficultyLevel) -> int:
        base_times = {
            "tutorial": 5,
            "standard": 15,
            "boss": 20,
            "puzzle": 12,
            "exploration": 18
        }
        
        difficulty_multipliers = {
            DifficultyLevel.VERY_EASY: 0.7,
            DifficultyLevel.EASY: 0.8,
            DifficultyLevel.MEDIUM: 1.0,
            DifficultyLevel.HARD: 1.3,
            DifficultyLevel.VERY_HARD: 1.6
        }
        
        base_time = base_times.get(level_type, 15)
        multiplier = difficulty_multipliers.get(difficulty, 1.0)
        
        return int(base_time * multiplier)

    def _generate_level_challenges(self, level_type: str, 
                                 difficulty: DifficultyLevel) -> List[str]:
        challenges = {
            "tutorial": ["Basic movement", "Simple interactions", "Gentle introduction"],
            "standard": ["Platforming sections", "Enemy encounters", "Environmental puzzles"],
            "boss": ["Multi-phase battle", "Pattern recognition", "Resource management"],
            "puzzle": ["Logic challenges", "Spatial reasoning", "Creative thinking"],
            "exploration": ["Hidden passages", "Secret areas", "Optional challenges"]
        }
        
        base_challenges = challenges.get(level_type, ["Standard gameplay"])
        
        # Add difficulty-appropriate modifiers
        if difficulty in [DifficultyLevel.HARD, DifficultyLevel.VERY_HARD]:
            base_challenges.extend(["Time pressure", "Limited resources", "Precision required"])
        
        return base_challenges

    def _generate_level_rewards(self, level_type: str, level_number: int) -> List[str]:
        rewards = ["Experience points", "Currency", "Progress toward next level"]
        
        if level_type == "boss":
            rewards.extend(["Special ability", "Major story revelation", "Access to new area"])
        elif level_type == "exploration":
            rewards.extend(["Hidden collectibles", "Lore items", "Optional upgrades"])
        elif level_number % 3 == 0:  # Every 3rd level
            rewards.append("New equipment or ability")
        
        return rewards

    def _generate_narrative_context(self, level_number: int, total_levels: int) -> str:
        progress = level_number / total_levels
        
        if progress < 0.3:
            return f"Early in the adventure, setting up the world and conflict"
        elif progress < 0.7:
            return f"Mid-journey complications arise, stakes increase"
        else:
            return f"Approaching the climax, final challenges await"

    def _generate_layout_description(self, level_type: str) -> str:
        layouts = {
            "tutorial": "Simple linear path with clear guidance and checkpoints",
            "standard": "Moderate complexity with multiple paths and optional areas",
            "boss": "Arena-style space designed for combat encounters",
            "puzzle": "Intricate environment where layout is part of the puzzle",
            "exploration": "Open-ended space with multiple routes and hidden areas"
        }
        
        return layouts.get(level_type, "Balanced layout suitable for gameplay")

    def _generate_enemy_types(self, level_type: str, 
                            difficulty: DifficultyLevel) -> List[str]:
        if level_type == "tutorial":
            return ["Training dummy", "Harmless creature"]
        
        basic_enemies = ["Basic soldier", "Wild animal", "Simple automaton"]
        advanced_enemies = ["Elite warrior", "Magical creature", "Advanced robot"]
        boss_enemies = ["Area boss", "Mini-boss", "Champion enemy"]
        
        if level_type == "boss":
            return boss_enemies
        elif difficulty in [DifficultyLevel.HARD, DifficultyLevel.VERY_HARD]:
            return basic_enemies + advanced_enemies
        else:
            return basic_enemies

    def _generate_collectibles(self, level_type: str) -> List[str]:
        collectibles = ["Coins/Currency", "Health items"]
        
        type_specific = {
            "exploration": ["Hidden treasures", "Lore collectibles", "Map fragments"],
            "puzzle": ["Key items", "Clue artifacts"],
            "boss": ["Rare materials", "Trophy items"],
            "standard": ["Power-ups", "Upgrade components"]
        }
        
        collectibles.extend(type_specific.get(level_type, ["Standard pickups"]))
        return collectibles

class GameDesignToolkit:
    def __init__(self, db_path: str = "game_design.db"):
        self.db_path = db_path
        self.game_generator = GameGenerator()
        self.mechanic_library = MechanicLibrary()
        self.game_balancer = GameBalancer()
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_projects (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            genre TEXT,
            platform TEXT,
            target_audience TEXT,
            core_concept TEXT,
            unique_selling_points TEXT,
            mechanics TEXT,
            characters TEXT,
            levels TEXT,
            systems TEXT,
            art_style TEXT,
            audio_style TEXT,
            monetization TEXT,
            estimated_dev_time INTEGER,
            team_size_needed INTEGER,
            technical_requirements TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS design_sessions (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            session_type TEXT,
            notes TEXT,
            decisions TEXT,
            next_steps TEXT,
            created_at TEXT,
            FOREIGN KEY (project_id) REFERENCES game_projects (id)
        )
        ''')
        
        conn.commit()
        conn.close()

    async def create_game_project(self, title: str, genre: str, platform: str, 
                                target_audience: str = "general") -> GameProject:
        """Create a new game design project."""
        
        genre_enum = GameGenre(genre)
        platform_enum = GamePlatform(platform)
        
        # Generate core concept
        concept = self.game_generator.generate_game_concept(
            genre_enum, platform_enum, target_audience
        )
        
        # Create core mechanics
        core_mechanics = []
        for mech_name in concept["mechanics"]:
            for mech_id, mechanic in self.mechanic_library.base_mechanics.items():
                if mechanic.name.lower() == mech_name.lower():
                    core_mechanics.append(mechanic)
                    break
        
        # Generate characters (basic templates)
        characters = self._generate_basic_characters(genre_enum)
        
        # Generate level structure
        levels = self.game_generator.generate_level_structure(concept, 10)
        
        # Generate game systems
        systems = self._generate_game_systems(genre_enum, core_mechanics)
        
        # Estimate development details
        dev_estimates = self._estimate_development_requirements(
            genre_enum, platform_enum, len(levels), len(characters)
        )
        
        project = GameProject(
            id=str(uuid.uuid4()),
            title=title,
            genre=genre_enum,
            platform=platform_enum,
            target_audience=target_audience,
            core_concept=concept["core_concept"],
            unique_selling_points=concept["unique_selling_points"],
            mechanics=core_mechanics,
            characters=characters,
            levels=levels,
            systems=systems,
            art_style=concept["art_style"],
            audio_style=concept["audio_style"],
            monetization=dev_estimates["monetization"],
            estimated_dev_time=dev_estimates["dev_time"],
            team_size_needed=dev_estimates["team_size"],
            technical_requirements=dev_estimates["tech_requirements"],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO game_projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project.id, project.title, project.genre.value, project.platform.value,
            project.target_audience, project.core_concept,
            json.dumps(project.unique_selling_points),
            json.dumps([asdict(mech) for mech in project.mechanics]),
            json.dumps([asdict(char) for char in project.characters]),
            json.dumps([asdict(level) for level in project.levels]),
            json.dumps([asdict(system) for system in project.systems]),
            project.art_style, project.audio_style, project.monetization,
            project.estimated_dev_time, project.team_size_needed,
            json.dumps(project.technical_requirements),
            project.created_at, project.updated_at
        ))
        
        conn.commit()
        conn.close()
        
        return project

    def _generate_basic_characters(self, genre: GameGenre) -> List[GameCharacter]:
        """Generate basic character templates for the genre."""
        characters = []
        
        # Player character
        player_char = GameCharacter(
            id=str(uuid.uuid4()),
            name="Player Character",
            role="player",
            description=f"The main character in this {genre.value} game",
            abilities=self._get_genre_abilities(genre, "player"),
            stats={"health": 100, "strength": 10, "agility": 10, "intelligence": 10},
            personality_traits=["brave", "determined", "curious"],
            backstory="A hero embarking on an epic journey",
            visual_design="Distinctive and memorable appearance",
            voice_characteristics="Heroic and inspiring",
            gameplay_function="Primary player avatar with core abilities"
        )
        characters.append(player_char)
        
        # Supporting NPC
        if genre in [GameGenre.RPG, GameGenre.ADVENTURE]:
            npc_char = GameCharacter(
                id=str(uuid.uuid4()),
                name="Guide Character",
                role="npc",
                description="A helpful guide who assists the player",
                abilities=["give_hints", "provide_lore", "offer_quests"],
                stats={"health": 80, "wisdom": 15, "charisma": 12},
                personality_traits=["wise", "helpful", "mysterious"],
                backstory="An experienced adventurer sharing knowledge",
                visual_design="Distinguished and trustworthy appearance",
                voice_characteristics="Calm and knowledgeable",
                gameplay_function="Tutorial and story exposition"
            )
            characters.append(npc_char)
        
        # Antagonist
        antagonist_char = GameCharacter(
            id=str(uuid.uuid4()),
            name="Primary Antagonist",
            role="enemy",
            description=f"The main villain in this {genre.value} adventure",
            abilities=self._get_genre_abilities(genre, "enemy"),
            stats={"health": 200, "strength": 15, "intelligence": 12, "menace": 20},
            personality_traits=["cunning", "powerful", "ruthless"],
            backstory="A formidable foe with compelling motivations",
            visual_design="Imposing and memorable villain design",
            voice_characteristics="Commanding and threatening",
            gameplay_function="Final boss and story driving force"
        )
        characters.append(antagonist_char)
        
        return characters

    def _get_genre_abilities(self, genre: GameGenre, role: str) -> List[str]:
        """Get appropriate abilities for genre and role."""
        abilities = {
            (GameGenre.ACTION, "player"): ["melee_attack", "ranged_attack", "dodge", "special_move"],
            (GameGenre.ACTION, "enemy"): ["attack", "block", "charge", "area_damage"],
            (GameGenre.RPG, "player"): ["cast_spell", "use_item", "level_up", "equip_gear"],
            (GameGenre.RPG, "enemy"): ["magic_attack", "summon", "curse", "heal"],
            (GameGenre.PUZZLE, "player"): ["interact", "combine_items", "analyze", "solve"],
            (GameGenre.ADVENTURE, "player"): ["explore", "talk", "climb", "swim"]
        }
        
        return abilities.get((genre, role), ["basic_action", "interact"])

    def _generate_game_systems(self, genre: GameGenre, 
                             mechanics: List[GameMechanic]) -> List[GameSystem]:
        """Generate game systems based on genre and mechanics."""
        systems = []
        
        # Core gameplay system
        core_system = GameSystem(
            id=str(uuid.uuid4()),
            name="Core Gameplay System",
            description="The primary gameplay loop and mechanics",
            rules=[f"Players use {mech.name.lower()}" for mech in mechanics[:2]],
            interactions={"ui": "provides feedback", "audio": "gives audio cues"},
            balancing_factors=["player skill", "progression curve", "difficulty scaling"],
            player_impact="Direct gameplay experience",
            complexity_level=7
        )
        systems.append(core_system)
        
        # Progression system (for RPG and similar genres)
        if genre in [GameGenre.RPG, GameGenre.ACTION, GameGenre.ADVENTURE]:
            progression_system = GameSystem(
                id=str(uuid.uuid4()),
                name="Character Progression",
                description="System for character growth and improvement",
                rules=["Gain experience from actions", "Level up increases stats", "Unlock new abilities"],
                interactions={"core_gameplay": "affects player power", "ui": "shows progress"},
                balancing_factors=["experience curve", "power scaling", "content gating"],
                player_impact="Long-term engagement and satisfaction",
                complexity_level=6
            )
            systems.append(progression_system)
        
        # Scoring/Achievement system
        scoring_system = GameSystem(
            id=str(uuid.uuid4()),
            name="Achievement System",
            description="Tracks and rewards player accomplishments",
            rules=["Complete objectives to earn achievements", "Track various statistics", "Unlock rewards"],
            interactions={"core_gameplay": "monitors player actions", "ui": "displays achievements"},
            balancing_factors=["achievement difficulty", "reward value", "completion rate"],
            player_impact="Additional goals and replay value",
            complexity_level=4
        )
        systems.append(scoring_system)
        
        return systems

    def _estimate_development_requirements(self, genre: GameGenre, 
                                         platform: GamePlatform,
                                         num_levels: int, 
                                         num_characters: int) -> Dict[str, Any]:
        """Estimate development time, team size, and technical requirements."""
        
        # Base development time (months)
        base_times = {
            GameGenre.PUZZLE: 6,
            GameGenre.PLATFORMER: 8,
            GameGenre.ACTION: 12,
            GameGenre.ADVENTURE: 15,
            GameGenre.RPG: 18,
            GameGenre.STRATEGY: 16,
            GameGenre.SIMULATION: 20
        }
        
        base_dev_time = base_times.get(genre, 12)
        
        # Adjust for content volume
        content_multiplier = 1 + (num_levels * 0.1) + (num_characters * 0.05)
        estimated_dev_time = int(base_dev_time * content_multiplier)
        
        # Team size estimation
        team_sizes = {
            GameGenre.PUZZLE: 3,
            GameGenre.PLATFORMER: 5,
            GameGenre.ACTION: 8,
            GameGenre.ADVENTURE: 10,
            GameGenre.RPG: 12,
            GameGenre.STRATEGY: 10,
            GameGenre.SIMULATION: 15
        }
        
        base_team_size = team_sizes.get(genre, 8)
        platform_multiplier = 1.2 if platform == GamePlatform.CONSOLE else 1.0
        team_size = int(base_team_size * platform_multiplier)
        
        # Technical requirements
        tech_requirements = ["Game engine", "Version control", "Bug tracking"]
        
        if platform == GamePlatform.MOBILE:
            tech_requirements.extend(["Mobile SDK", "App store integration", "Analytics"])
        elif platform == GamePlatform.CONSOLE:
            tech_requirements.extend(["Console SDK", "Certification process", "Platform integration"])
        elif platform == GamePlatform.VR:
            tech_requirements.extend(["VR SDK", "Motion tracking", "Performance optimization"])
        
        # Monetization strategy
        monetization_strategies = {
            GamePlatform.MOBILE: "Free-to-play with in-app purchases",
            GamePlatform.PC: "Premium purchase with optional DLC",
            GamePlatform.CONSOLE: "Premium retail release",
            GamePlatform.WEB: "Ad-supported or premium subscription",
            GamePlatform.VR: "Premium purchase (niche market)"
        }
        
        return {
            "dev_time": estimated_dev_time,
            "team_size": team_size,
            "tech_requirements": tech_requirements,
            "monetization": monetization_strategies.get(platform, "Premium purchase")
        }

    async def analyze_game_balance(self, project_id: str) -> Dict[str, Any]:
        """Analyze game balance and suggest improvements."""
        project = await self.get_game_project(project_id)
        if not project:
            return {"error": "Project not found"}
        
        analysis = {
            "project_title": project.title,
            "difficulty_curve": self._analyze_difficulty_curve(project.levels),
            "mechanic_balance": self._analyze_mechanic_usage(project.mechanics, project.levels),
            "character_balance": self._analyze_character_balance(project.characters),
            "pacing_analysis": self._analyze_game_pacing(project.levels),
            "recommendations": []
        }
        
        # Generate recommendations based on analysis
        if analysis["difficulty_curve"]["curve_type"] == "too_steep":
            analysis["recommendations"].append("Consider adding more tutorial or easier levels")
        
        if analysis["pacing_analysis"]["average_level_time"] > 30:
            analysis["recommendations"].append("Levels might be too long for the target platform")
        
        if len(analysis["character_balance"]["underpowered"]) > 0:
            analysis["recommendations"].append("Some characters need stat balancing")
        
        return analysis

    def _analyze_difficulty_curve(self, levels: List[GameLevel]) -> Dict[str, Any]:
        """Analyze the difficulty progression across levels."""
        difficulties = [level.difficulty.value for level in levels]
        difficulty_values = {
            "very_easy": 1, "easy": 2, "medium": 3, "hard": 4, "very_hard": 5
        }
        
        numeric_difficulties = [difficulty_values[d] for d in difficulties]
        
        # Check for appropriate progression
        average_increase = (numeric_difficulties[-1] - numeric_difficulties[0]) / len(numeric_difficulties)
        
        curve_type = "balanced"
        if average_increase > 0.5:
            curve_type = "too_steep"
        elif average_increase < 0.1:
            curve_type = "too_flat"
        
        return {
            "curve_type": curve_type,
            "difficulty_range": f"{min(difficulties)} to {max(difficulties)}",
            "average_increase": round(average_increase, 2),
            "spike_levels": [i for i, (curr, next_) in enumerate(zip(numeric_difficulties, numeric_difficulties[1:])) 
                           if next_ - curr > 1]
        }

    def _analyze_mechanic_usage(self, mechanics: List[GameMechanic], 
                               levels: List[GameLevel]) -> Dict[str, Any]:
        """Analyze how mechanics are distributed across levels."""
        mechanic_names = [mech.name for mech in mechanics]
        usage_count = {name: 0 for name in mechanic_names}
        
        for level in levels:
            for mechanic_name in level.mechanics_used:
                if mechanic_name in usage_count:
                    usage_count[mechanic_name] += 1
        
        total_levels = len(levels)
        usage_percentages = {name: (count / total_levels) * 100 
                           for name, count in usage_count.items()}
        
        return {
            "usage_distribution": usage_percentages,
            "underused_mechanics": [name for name, pct in usage_percentages.items() if pct < 30],
            "overused_mechanics": [name for name, pct in usage_percentages.items() if pct > 80],
            "balanced_mechanics": [name for name, pct in usage_percentages.items() if 30 <= pct <= 80]
        }

    def _analyze_character_balance(self, characters: List[GameCharacter]) -> Dict[str, Any]:
        """Analyze character stat balance."""
        if not characters:
            return {"error": "No characters to analyze"}
        
        # Calculate average power level for each character
        power_levels = {}
        for char in characters:
            if char.stats:
                power_levels[char.name] = sum(char.stats.values())
        
        if not power_levels:
            return {"error": "No character stats to analyze"}
        
        average_power = sum(power_levels.values()) / len(power_levels)
        
        underpowered = [name for name, power in power_levels.items() 
                       if power < average_power * 0.8]
        overpowered = [name for name, power in power_levels.items() 
                      if power > average_power * 1.2]
        
        return {
            "average_power_level": round(average_power, 1),
            "power_distribution": power_levels,
            "underpowered": underpowered,
            "overpowered": overpowered,
            "balanced_characters": [name for name in power_levels.keys() 
                                  if name not in underpowered and name not in overpowered]
        }

    def _analyze_game_pacing(self, levels: List[GameLevel]) -> Dict[str, Any]:
        """Analyze the pacing of gameplay across levels."""
        level_times = [level.estimated_play_time for level in levels]
        
        return {
            "total_playtime": sum(level_times),
            "average_level_time": round(sum(level_times) / len(level_times), 1),
            "shortest_level": min(level_times),
            "longest_level": max(level_times),
            "time_variance": round(max(level_times) - min(level_times), 1),
            "pacing_issues": [i for i, time in enumerate(level_times) 
                            if abs(time - (sum(level_times) / len(level_times))) > 10]
        }

    async def get_game_project(self, project_id: str) -> Optional[GameProject]:
        """Retrieve a game project from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM game_projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Reconstruct objects from JSON
        mechanics_data = json.loads(row[7])
        mechanics = [GameMechanic(**mech_data) for mech_data in mechanics_data]
        
        characters_data = json.loads(row[8])
        characters = [GameCharacter(**char_data) for char_data in characters_data]
        
        levels_data = json.loads(row[9])
        levels = [GameLevel(**level_data) for level_data in levels_data]
        
        systems_data = json.loads(row[10])
        systems = [GameSystem(**sys_data) for sys_data in systems_data]
        
        return GameProject(
            id=row[0], title=row[1], genre=GameGenre(row[2]), platform=GamePlatform(row[3]),
            target_audience=row[4], core_concept=row[5],
            unique_selling_points=json.loads(row[6]),
            mechanics=mechanics, characters=characters, levels=levels, systems=systems,
            art_style=row[11], audio_style=row[12], monetization=row[13],
            estimated_dev_time=row[14], team_size_needed=row[15],
            technical_requirements=json.loads(row[16]),
            created_at=row[17], updated_at=row[18]
        )

    async def generate_design_document(self, project_id: str) -> Dict[str, Any]:
        """Generate a comprehensive game design document."""
        project = await self.get_game_project(project_id)
        if not project:
            return {"error": "Project not found"}
        
        document = {
            "title": project.title,
            "executive_summary": {
                "genre": project.genre.value,
                "platform": project.platform.value,
                "target_audience": project.target_audience,
                "core_concept": project.core_concept,
                "unique_selling_points": project.unique_selling_points
            },
            "gameplay_mechanics": [
                {
                    "name": mech.name,
                    "description": mech.description,
                    "complexity": mech.complexity,
                    "examples": mech.examples
                }
                for mech in project.mechanics
            ],
            "character_designs": [
                {
                    "name": char.name,
                    "role": char.role,
                    "description": char.description,
                    "abilities": char.abilities,
                    "personality": char.personality_traits
                }
                for char in project.characters
            ],
            "level_structure": [
                {
                    "name": level.name,
                    "objective": level.objective,
                    "difficulty": level.difficulty.value,
                    "estimated_time": level.estimated_play_time,
                    "challenges": level.challenges
                }
                for level in project.levels[:5]  # First 5 levels for summary
            ],
            "art_and_audio": {
                "art_style": project.art_style,
                "audio_style": project.audio_style,
                "visual_themes": ["Consistent with art style", "Platform appropriate"]
            },
            "technical_specifications": {
                "platform": project.platform.value,
                "requirements": project.technical_requirements,
                "estimated_dev_time": f"{project.estimated_dev_time} months",
                "team_size": f"{project.team_size_needed} people"
            },
            "monetization_strategy": project.monetization,
            "production_timeline": self._generate_production_phases(project.estimated_dev_time)
        }
        
        return document

    def _generate_production_phases(self, total_months: int) -> List[Dict[str, Any]]:
        """Generate production timeline phases."""
        phases = [
            {"name": "Pre-production", "duration_pct": 0.15, "description": "Concept development and planning"},
            {"name": "Production", "duration_pct": 0.60, "description": "Core development and asset creation"},
            {"name": "Alpha", "duration_pct": 0.15, "description": "Feature complete, internal testing"},
            {"name": "Beta", "duration_pct": 0.10, "description": "External testing and bug fixes"}
        ]
        
        timeline = []
        current_month = 0
        
        for phase in phases:
            duration = max(1, int(total_months * phase["duration_pct"]))
            timeline.append({
                "phase": phase["name"],
                "start_month": current_month + 1,
                "end_month": current_month + duration,
                "duration": f"{duration} months",
                "description": phase["description"]
            })
            current_month += duration
        
        return timeline

if __name__ == "__main__":
    async def main():
        toolkit = GameDesignToolkit()
        
        # Create a sample game project
        project = await toolkit.create_game_project(
            title="Mystic Platformer Adventure",
            genre="adventure",
            platform="pc",
            target_audience="teens and young adults"
        )
        
        print(f"Created game project: {project.title}")
        print(f"Genre: {project.genre.value}")
        print(f"Core concept: {project.core_concept}")
        print(f"Number of mechanics: {len(project.mechanics)}")
        print(f"Number of levels: {len(project.levels)}")
        print(f"Estimated development: {project.estimated_dev_time} months")
        print(f"Team size needed: {project.team_size_needed} people")
        
        # Analyze game balance
        balance_analysis = await toolkit.analyze_game_balance(project.id)
        print(f"\nBalance analysis:")
        print(f"Difficulty curve: {balance_analysis['difficulty_curve']['curve_type']}")
        print(f"Recommendations: {len(balance_analysis['recommendations'])}")
        
        # Generate design document
        design_doc = await toolkit.generate_design_document(project.id)
        print(f"\nDesign document generated for: {design_doc['title']}")
        print(f"Production phases: {len(design_doc['production_timeline'])}")
    
    asyncio.run(main())