"""
Adventure Generator

Creates pre-made adventures for levels 1-20 with scaling encounters,
story progression, and appropriate challenges for each tier of play.
"""

import random
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.adventure import Adventure, Chapter, Scene, OneShot, AdventureHook, AdventureSite
from ..models.base import (
    ComplexityLevel, ThemeType, DifficultyLevel, PlotHook, Twist,
    Location, Reward, StatBlock, EnvironmentType
)
from ..config import LEVEL_TIERS, TEMPLATE_CONFIG, ENCOUNTER_CONFIG
from .base_generator import BaseGenerator


class AdventureGenerator(BaseGenerator):
    """Generates complete adventures for different level ranges"""
    
    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.adventure_templates = self._load_adventure_templates()
        self.encounter_scaling = self._setup_encounter_scaling()
    
    def _load_adventure_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load base adventure templates for each tier"""
        return {
            "tier1": {
                "goblin_caves": {
                    "title": "The Goblin Caves of Kraggmoor",
                    "theme": ThemeType.HEROIC_FANTASY,
                    "main_conflict": "Goblins have been raiding the village and taken prisoners",
                    "antagonist": "Grash the Goblin Chief",
                    "environments": [EnvironmentType.UNDERGROUND, EnvironmentType.WILDERNESS],
                    "key_encounters": ["goblin_ambush", "trapped_bridge", "chief_confrontation"]
                },
                "haunted_manor": {
                    "title": "The Haunted Manor of Ravenshollow",
                    "theme": ThemeType.HORROR,
                    "main_conflict": "Undead plague the old manor house",
                    "antagonist": "Wraith of Lord Ravenshollow",
                    "environments": [EnvironmentType.URBAN],
                    "key_encounters": ["ghostly_servants", "animated_armor", "wraith_confrontation"]
                },
                "missing_merchant": {
                    "title": "The Missing Merchant",
                    "theme": ThemeType.MYSTERY,
                    "main_conflict": "A wealthy merchant has vanished without a trace",
                    "antagonist": "Doppelganger infiltrator",
                    "environments": [EnvironmentType.URBAN, EnvironmentType.WILDERNESS],
                    "key_encounters": ["investigation", "bandit_encounter", "doppelganger_reveal"]
                }
            },
            "tier2": {
                "dragon_cult": {
                    "title": "The Dragon Cult Conspiracy",
                    "theme": ThemeType.POLITICAL,
                    "main_conflict": "A dragon cult infiltrates the royal court",
                    "antagonist": "Adult Green Dragon Vorthak",
                    "environments": [EnvironmentType.URBAN, EnvironmentType.FOREST, EnvironmentType.MOUNTAIN],
                    "key_encounters": ["court_intrigue", "cult_ritual", "dragon_confrontation"]
                },
                "planar_rifts": {
                    "title": "Rifts in Reality",
                    "theme": ThemeType.PLANAR,
                    "main_conflict": "Planar rifts threaten to tear apart the material plane",
                    "antagonist": "Demon Prince Graz'zt",
                    "environments": [EnvironmentType.PLANAR, EnvironmentType.URBAN],
                    "key_encounters": ["rift_investigation", "demon_invasion", "planar_battle"]
                },
                "lost_city": {
                    "title": "The Lost City of Zephyria",
                    "theme": ThemeType.EXPLORATION,
                    "main_conflict": "Ancient secrets lie buried in a forgotten city",
                    "antagonist": "Ancient Lich Valdris",
                    "environments": [EnvironmentType.DESERT, EnvironmentType.UNDERGROUND],
                    "key_encounters": ["desert_journey", "city_exploration", "lich_confrontation"]
                }
            },
            "tier3": {
                "elemental_war": {
                    "title": "The Elemental War",
                    "theme": ThemeType.PLANAR,
                    "main_conflict": "The elemental planes wage war across multiple realms",
                    "antagonist": "Primordial of Chaos",
                    "environments": [EnvironmentType.PLANAR],
                    "key_encounters": ["elemental_diplomacy", "planar_battles", "primordial_awakening"]
                },
                "gods_gambit": {
                    "title": "The Gods' Gambit",
                    "theme": ThemeType.EPIC,
                    "main_conflict": "Divine politics threaten the cosmic order",
                    "antagonist": "Fallen God Xerion",
                    "environments": [EnvironmentType.PLANAR, EnvironmentType.MOUNTAIN],
                    "key_encounters": ["divine_politics", "celestial_war", "god_confrontation"]
                },
                "world_tree": {
                    "title": "The Dying World Tree",
                    "theme": ThemeType.EXPLORATION,
                    "main_conflict": "The cosmic World Tree is withering and dying",
                    "antagonist": "Entropy Dragon Nihilus",
                    "environments": [EnvironmentType.PLANAR, EnvironmentType.FOREST],
                    "key_encounters": ["tree_investigation", "planar_travel", "entropy_battle"]
                }
            },
            "tier4": {
                "cosmic_threat": {
                    "title": "The Cosmic Devourer",
                    "theme": ThemeType.EPIC,
                    "main_conflict": "An entity from beyond reality seeks to devour existence",
                    "antagonist": "The Void Sovereign",
                    "environments": [EnvironmentType.PLANAR],
                    "key_encounters": ["reality_investigation", "multiverse_alliance", "void_confrontation"]
                },
                "time_war": {
                    "title": "The Time War",
                    "theme": ThemeType.EPIC,
                    "main_conflict": "A war across multiple timelines threatens causality",
                    "antagonist": "Chronarch Temporal",
                    "environments": [EnvironmentType.PLANAR],
                    "key_encounters": ["timeline_travel", "temporal_battles", "causality_restoration"]
                },
                "reality_forge": {
                    "title": "The Reality Forge",
                    "theme": ThemeType.EPIC,
                    "main_conflict": "An ancient artifact can rewrite the laws of reality",
                    "antagonist": "Overgod Supremus",
                    "environments": [EnvironmentType.PLANAR],
                    "key_encounters": ["forge_discovery", "divine_opposition", "reality_decision"]
                }
            }
        }
    
    def _setup_encounter_scaling(self) -> Dict[int, Dict[str, Any]]:
        """Setup encounter scaling by level"""
        scaling = {}
        
        for level in range(1, 21):
            tier = self._get_tier_for_level(level)
            scaling[level] = {
                "encounters_per_day": 6 - (level // 5),  # Fewer encounters at higher levels
                "short_rests_per_day": 2,
                "long_rest_healing": True,
                "average_encounter_xp": self._calculate_encounter_xp(level, 4),
                "boss_encounter_multiplier": 2.0,
                "environmental_complexity": min(level // 4 + 1, 4),
                "social_complexity": min(level // 3 + 1, 4),
                "puzzle_complexity": min(level // 5 + 1, 4),
                "tier_info": tier
            }
        
        return scaling
    
    def _get_tier_for_level(self, level: int) -> Dict[str, Any]:
        """Get tier information for a level"""
        for tier_name, tier_info in LEVEL_TIERS.items():
            if level in tier_info["levels"]:
                return tier_info
        return LEVEL_TIERS["tier1"]  # Fallback
    
    def _calculate_encounter_xp(self, level: int, party_size: int) -> int:
        """Calculate appropriate XP for encounters at this level"""
        # XP thresholds per level (simplified from DMG)
        xp_thresholds = {
            1: {"easy": 25, "medium": 50, "hard": 75, "deadly": 100},
            2: {"easy": 50, "medium": 100, "hard": 150, "deadly": 200},
            3: {"easy": 75, "medium": 150, "hard": 225, "deadly": 400},
            4: {"easy": 125, "medium": 250, "hard": 375, "deadly": 500},
            5: {"easy": 250, "medium": 500, "hard": 750, "deadly": 1100},
            # ... would continue for all levels
        }
        
        # Simplified scaling for now
        base_xp = 50 * (level ** 1.5)
        return int(base_xp * party_size)
    
    async def generate_adventure(self, level: int, complexity: ComplexityLevel = ComplexityLevel.MODERATE,
                               theme: Optional[ThemeType] = None, party_size: int = 4) -> Adventure:
        """Generate a complete adventure for the specified level"""
        
        tier = self._get_tier_for_level(level)
        tier_name = self._get_tier_name_for_level(level)
        
        # Select appropriate template
        available_templates = self.adventure_templates.get(tier_name, {})
        if not available_templates:
            available_templates = self.adventure_templates["tier1"]
        
        # Filter by theme if specified
        if theme:
            filtered_templates = {
                k: v for k, v in available_templates.items() 
                if v.get("theme") == theme
            }
            if filtered_templates:
                available_templates = filtered_templates
        
        template_key = self.rng.choice(list(available_templates.keys()))
        template = available_templates[template_key]
        
        # Generate the adventure
        adventure = Adventure(
            name=template["title"],
            description=f"An adventure designed for {tier['name']} (Level {level})",
            target_levels=[level],
            party_size=party_size,
            complexity=complexity,
            themes=[template["theme"]],
            main_conflict=template["main_conflict"],
            antagonist=template["antagonist"]
        )
        
        # Generate chapters based on complexity
        chapter_count = self._get_chapter_count(complexity, level)
        for i in range(chapter_count):
            chapter = await self._generate_chapter(
                i + 1, level, template, complexity, party_size
            )
            adventure.chapters.append(chapter)
        
        # Generate supporting elements
        adventure.plot_hook = await self._generate_plot_hook(template, level)
        adventure.major_npcs = await self._generate_major_npcs(template, level)
        adventure.key_locations = await self._generate_key_locations(template)
        
        # Calculate totals
        adventure.total_encounters = sum(len(ch.scenes) for ch in adventure.chapters)
        adventure.estimated_sessions = max(1, adventure.total_encounters // 4)
        adventure.total_experience = self._calculate_total_xp(adventure, level, party_size)
        
        # Add DM notes
        adventure.dm_notes = await self._generate_dm_notes(adventure, level)
        adventure.scaling_notes = await self._generate_scaling_notes(level, party_size)
        
        return adventure
    
    def _get_tier_name_for_level(self, level: int) -> str:
        """Get tier name for level"""
        if level <= 4:
            return "tier1"
        elif level <= 10:
            return "tier2"
        elif level <= 16:
            return "tier3"
        else:
            return "tier4"
    
    def _get_chapter_count(self, complexity: ComplexityLevel, level: int) -> int:
        """Determine number of chapters based on complexity and level"""
        base_chapters = {
            ComplexityLevel.SIMPLE: 3,
            ComplexityLevel.MODERATE: 5,
            ComplexityLevel.COMPLEX: 7,
            ComplexityLevel.EPIC: 10
        }
        
        chapter_count = base_chapters[complexity]
        
        # Adjust for level (higher level = potentially more complex)
        if level >= 11:
            chapter_count += 1
        if level >= 17:
            chapter_count += 1
        
        return min(chapter_count, 12)  # Cap at 12 chapters
    
    async def _generate_chapter(self, chapter_num: int, level: int, template: Dict[str, Any],
                              complexity: ComplexityLevel, party_size: int) -> Chapter:
        """Generate a single chapter"""
        
        chapter = Chapter(
            name=f"Chapter {chapter_num}",
            description=f"Chapter {chapter_num} of the adventure",
            chapter_number=chapter_num,
            level_range=[level, level + 1]
        )
        
        # Determine chapter type based on position
        if chapter_num == 1:
            chapter_type = "introduction"
            chapter.main_objective = "Introduce the main conflict and hook the party"
        elif chapter_num == self._get_chapter_count(complexity, level):
            chapter_type = "climax"
            chapter.main_objective = "Confront the main antagonist and resolve the conflict"
        else:
            chapter_type = self.rng.choice(["investigation", "exploration", "confrontation", "social"])
            chapter.main_objective = f"Progress the story through {chapter_type}"
        
        # Generate scenes for this chapter
        scene_count = self._get_scene_count_for_chapter(chapter_type, complexity)
        for i in range(scene_count):
            scene = await self._generate_scene(i + 1, chapter_type, level, template)
            chapter.scenes.append(scene)
        
        return chapter
    
    def _get_scene_count_for_chapter(self, chapter_type: str, complexity: ComplexityLevel) -> int:
        """Determine scene count based on chapter type and complexity"""
        base_scenes = {
            "introduction": 2,
            "investigation": 3,
            "exploration": 4,
            "confrontation": 3,
            "social": 2,
            "climax": 4
        }
        
        complexity_modifier = {
            ComplexityLevel.SIMPLE: -1,
            ComplexityLevel.MODERATE: 0,
            ComplexityLevel.COMPLEX: 1,
            ComplexityLevel.EPIC: 2
        }
        
        scene_count = base_scenes.get(chapter_type, 3) + complexity_modifier[complexity]
        return max(1, scene_count)
    
    async def _generate_scene(self, scene_num: int, chapter_type: str, level: int,
                            template: Dict[str, Any]) -> Scene:
        """Generate a single scene"""
        
        # Determine scene type based on chapter type and position
        scene_types = {
            "introduction": ["social", "exploration", "combat"],
            "investigation": ["social", "exploration", "puzzle"],
            "exploration": ["exploration", "trap", "combat"],
            "confrontation": ["combat", "social", "skill_challenge"],
            "social": ["social", "puzzle", "exploration"],
            "climax": ["combat", "skill_challenge", "social"]
        }
        
        available_scene_types = scene_types.get(chapter_type, ["combat", "social", "exploration"])
        scene_type = self.rng.choice(available_scene_types)
        
        scene = Scene(
            name=f"Scene {scene_num}: {scene_type.title()} Encounter",
            description=f"A {scene_type} encounter appropriate for level {level}",
            scene_type=scene_type,
            duration_minutes=30 + self.rng.randint(-10, 20)
        )
        
        # Generate scene-specific content
        scene.objectives = await self._generate_scene_objectives(scene_type, chapter_type)
        scene.location = await self._generate_scene_location(template, scene_type)
        scene.key_npcs = await self._generate_scene_npcs(scene_type, level)
        scene.dm_notes = await self._generate_scene_dm_notes(scene_type, level)
        
        if scene_type == "combat":
            scene.potential_encounters = [f"Level {level} combat encounter"]
        elif scene_type == "social":
            scene.skill_challenges = ["Persuasion", "Deception", "Insight"]
        elif scene_type == "exploration":
            scene.skill_challenges = ["Investigation", "Perception", "Survival"]
        
        return scene
    
    async def _generate_scene_objectives(self, scene_type: str, chapter_type: str) -> List[str]:
        """Generate objectives for a scene"""
        objectives_by_type = {
            "combat": [
                "Defeat the enemies",
                "Protect important NPCs",
                "Secure the area",
                "Retrieve important items"
            ],
            "social": [
                "Gather information",
                "Negotiate with NPCs",
                "Resolve conflicts peacefully",
                "Build relationships"
            ],
            "exploration": [
                "Discover hidden secrets",
                "Navigate challenges",
                "Map the area",
                "Find clues or items"
            ],
            "puzzle": [
                "Solve the puzzle",
                "Unlock barriers",
                "Decipher clues",
                "Activate mechanisms"
            ]
        }
        
        available_objectives = objectives_by_type.get(scene_type, ["Complete the challenge"])
        return self.rng.sample(available_objectives, min(2, len(available_objectives)))
    
    async def _generate_scene_location(self, template: Dict[str, Any], scene_type: str) -> Location:
        """Generate a location for the scene"""
        environments = template.get("environments", [EnvironmentType.WILDERNESS])
        environment = self.rng.choice(environments)
        
        location_names = {
            EnvironmentType.DUNGEON: ["Ancient Chamber", "Trapped Corridor", "Hidden Vault"],
            EnvironmentType.URBAN: ["City Street", "Noble's Manor", "Merchant Quarter"],
            EnvironmentType.WILDERNESS: ["Forest Clearing", "Rocky Outcrop", "River Crossing"],
            EnvironmentType.UNDERGROUND: ["Cave System", "Underground Lake", "Tunnel Network"]
        }
        
        names = location_names.get(environment, ["Mysterious Location"])
        
        return Location(
            name=self.rng.choice(names),
            description=f"A {environment.value} location suitable for {scene_type} encounters",
            environment_type=environment,
            features=self._generate_location_features(environment),
            atmosphere=self._generate_atmosphere(environment)
        )
    
    def _generate_location_features(self, environment: EnvironmentType) -> List[str]:
        """Generate features for a location"""
        feature_sets = {
            EnvironmentType.DUNGEON: ["Stone walls", "Torch sconces", "Ancient carvings"],
            EnvironmentType.URBAN: ["Cobblestone streets", "Market stalls", "Guard posts"],
            EnvironmentType.WILDERNESS: ["Dense foliage", "Animal tracks", "Natural cover"],
            EnvironmentType.UNDERGROUND: ["Stalactites", "Underground streams", "Echo chambers"]
        }
        
        features = feature_sets.get(environment, ["Natural features"])
        return self.rng.sample(features, min(2, len(features)))
    
    def _generate_atmosphere(self, environment: EnvironmentType) -> str:
        """Generate atmospheric description"""
        atmospheres = {
            EnvironmentType.DUNGEON: "Dark and foreboding with an ancient, musty smell",
            EnvironmentType.URBAN: "Bustling with activity and the sounds of city life",
            EnvironmentType.WILDERNESS: "Natural and wild with the sounds of nature",
            EnvironmentType.UNDERGROUND: "Deep and echoing with a cool, damp atmosphere"
        }
        
        return atmospheres.get(environment, "A place of mystery and adventure")
    
    async def _generate_scene_npcs(self, scene_type: str, level: int) -> List[str]:
        """Generate NPCs for the scene"""
        npc_types_by_scene = {
            "combat": ["Enemy leader", "Minion group"],
            "social": ["Important contact", "Information broker", "Authority figure"],
            "exploration": ["Guide", "Survivor", "Local expert"],
            "puzzle": ["Ancient guardian", "Helpful spirit", "Confused researcher"]
        }
        
        npc_types = npc_types_by_scene.get(scene_type, ["Generic NPC"])
        return self.rng.sample(npc_types, min(2, len(npc_types)))
    
    async def _generate_scene_dm_notes(self, scene_type: str, level: int) -> List[str]:
        """Generate DM notes for the scene"""
        notes_by_type = {
            "combat": [
                f"Use CR {level//2 + 1} creatures for appropriate challenge",
                "Consider terrain advantages for both sides",
                "Have backup creatures ready if combat is too easy"
            ],
            "social": [
                f"NPCs should have motivations and goals",
                "Allow multiple approaches to succeed",
                f"Set DCs between {10 + level//2} and {15 + level//2}"
            ],
            "exploration": [
                "Reward creative problem-solving",
                "Have multiple paths to success",
                "Include opportunities for different character skills"
            ]
        }
        
        return notes_by_type.get(scene_type, ["Standard encounter notes"])
    
    async def _generate_plot_hook(self, template: Dict[str, Any], level: int) -> AdventureHook:
        """Generate a plot hook for the adventure"""
        return AdventureHook(
            title=f"The Call to Adventure",
            description=f"Something draws the party into {template['main_conflict']}",
            hook_type="quest_giver",
            urgency="moderate",
            complexity=ComplexityLevel.MODERATE,
            themes=[template["theme"]],
            suitable_levels=[level],
            inciting_incident=f"The {template['antagonist']} begins their plan",
            stakes="The safety of innocents and the balance of the region",
            starting_location="Village tavern or town square"
        )
    
    async def _generate_major_npcs(self, template: Dict[str, Any], level: int) -> List[StatBlock]:
        """Generate major NPCs for the adventure"""
        # This would generate actual stat blocks in a full implementation
        npcs = []
        
        # Add the antagonist
        antagonist_cr = max(level, level + 2)  # Slightly above party level
        npcs.append(StatBlock(
            name=template["antagonist"],
            size="medium",  # Would be determined by creature type
            creature_type="humanoid",  # Would be determined by antagonist type
            alignment="chaotic evil",  # Default for antagonist
            armor_class=12 + level // 2,
            hit_points=20 * level,
            speed={"walk": 30},
            strength=14, dexterity=14, constitution=14,
            intelligence=14, wisdom=12, charisma=16,
            challenge_rating=antagonist_cr,
            proficiency_bonus=2 + (level - 1) // 4
        ))
        
        return npcs
    
    async def _generate_key_locations(self, template: Dict[str, Any]) -> List[Location]:
        """Generate key locations for the adventure"""
        locations = []
        
        for env in template.get("environments", []):
            location = Location(
                name=f"Key {env.value} Location",
                description=f"An important location in the {env.value}",
                environment_type=env,
                features=self._generate_location_features(env),
                atmosphere=self._generate_atmosphere(env)
            )
            locations.append(location)
        
        return locations
    
    def _calculate_total_xp(self, adventure: Adventure, level: int, party_size: int) -> int:
        """Calculate total XP for the adventure"""
        base_xp_per_scene = self._calculate_encounter_xp(level, party_size)
        total_scenes = sum(len(chapter.scenes) for chapter in adventure.chapters)
        return base_xp_per_scene * total_scenes
    
    async def _generate_dm_notes(self, adventure: Adventure, level: int) -> List[str]:
        """Generate DM notes for the adventure"""
        return [
            f"This adventure is designed for {adventure.party_size} characters of level {level}",
            f"Estimated play time: {adventure.estimated_sessions} sessions",
            f"Main theme: {adventure.themes[0].value if adventure.themes else 'General adventure'}",
            "Adjust encounter difficulty based on party composition and player experience",
            "Encourage creative problem-solving and roleplay opportunities",
            "Have backup encounters ready if sessions run short"
        ]
    
    async def _generate_scaling_notes(self, level: int, party_size: int) -> Dict[str, str]:
        """Generate scaling notes for different party configurations"""
        return {
            "smaller_party": f"For parties smaller than {party_size}, reduce enemy numbers by 25%",
            "larger_party": f"For parties larger than {party_size}, add extra minions to encounters",
            "lower_level": f"For parties below level {level}, reduce DCs by 2 and enemy CR by 1",
            "higher_level": f"For parties above level {level}, increase DCs by 2 and add environmental hazards"
        }
    
    async def generate_oneshot(self, level: int, session_hours: int = 4,
                             theme: Optional[ThemeType] = None) -> OneShot:
        """Generate a one-shot adventure"""
        # Get base adventure structure
        base_adventure = await self.generate_adventure(level, ComplexityLevel.SIMPLE, theme)
        
        # Convert to one-shot format
        oneshot = OneShot(
            name=f"{base_adventure.name} (One-Shot)",
            description=f"A {session_hours}-hour one-shot adventure for level {level}",
            target_levels=[level],
            session_length_hours=session_hours,
            themes=base_adventure.themes,
            complexity=ComplexityLevel.SIMPLE,
            main_conflict=base_adventure.main_conflict,
            antagonist=base_adventure.antagonist
        )
        
        # Simplify structure for one-shot
        oneshot.opening_hook = base_adventure.plot_hook.description
        oneshot.main_challenge = base_adventure.main_conflict
        oneshot.climax_encounter = f"Final confrontation with {base_adventure.antagonist}"
        
        # Add the first few chapters only
        oneshot.chapters = base_adventure.chapters[:3]  # Limit to 3 chapters max
        
        # Set pacing
        minutes_per_hour = 60
        total_minutes = session_hours * minutes_per_hour
        
        oneshot.act_timings = {
            "opening": total_minutes // 4,      # 25% for setup
            "middle": total_minutes // 2,       # 50% for main content  
            "climax": total_minutes // 4        # 25% for resolution
        }
        
        # Add one-shot specific elements
        oneshot.backup_encounters = ["Quick combat encounter", "Social challenge", "Puzzle obstacle"]
        oneshot.fast_forward_options = ["Skip travel scenes", "Summarize investigation", "Go straight to climax"]
        oneshot.quick_reference_rules = [
            "Advantage/Disadvantage rules",
            "Skill check DCs by level",
            "Combat action economy"
        ]
        
        return oneshot
    
    async def generate_campaign_adventures(self, start_level: int, end_level: int,
                                         theme: ThemeType = ThemeType.HEROIC_FANTASY) -> List[Adventure]:
        """Generate a series of connected adventures for a campaign"""
        adventures = []
        
        current_level = start_level
        while current_level <= end_level:
            # Determine adventure length based on level range
            if current_level <= 4:
                level_span = 1  # One level per adventure in tier 1
            elif current_level <= 10:
                level_span = 2  # Two levels per adventure in tier 2
            else:
                level_span = 3  # Three levels per adventure in higher tiers
            
            adventure_end_level = min(current_level + level_span - 1, end_level)
            
            adventure = await self.generate_adventure(current_level, ComplexityLevel.MODERATE, theme)
            adventure.target_levels = list(range(current_level, adventure_end_level + 1))
            adventure.name = f"{adventure.name} (Levels {current_level}-{adventure_end_level})"
            
            adventures.append(adventure)
            current_level = adventure_end_level + 1
        
        return adventures