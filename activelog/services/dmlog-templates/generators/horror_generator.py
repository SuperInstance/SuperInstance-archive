"""
Horror atmosphere generator for creating terrifying and suspenseful scenarios
"""

from typing import List, Optional, Dict, Any
from ..models.base import BaseTemplate, ComplexityLevel, DifficultyLevel
from ..models.encounter import Encounter, SkillCheck
from ..models.character import NPCProfile
from .base_generator import BaseGenerator
from .character_generator import CharacterGenerator
from ..config import HORROR_CONFIG


class HorrorElement(BaseTemplate):
    """A horror atmosphere element"""
    element_type: str = "atmosphere"  # atmosphere, threat, psychological, supernatural
    intensity: str = "mild"  # mild, moderate, intense, terrifying
    timing: str = "ongoing"  # immediate, gradual, ongoing, climactic
    sensory_effects: List[str] = []
    psychological_impact: List[str] = []
    mechanical_effects: List[str] = []


class HorrorEncounter(Encounter):
    """A horror-themed encounter with atmosphere elements"""
    horror_theme: str = "haunted"
    fear_level: str = "moderate"
    horror_elements: List[HorrorElement] = []
    escalation_triggers: List[str] = []
    resolution_methods: List[str] = []
    aftermath_effects: List[str] = []


class HorrorScenario(BaseTemplate):
    """A complete horror scenario with escalating tension"""
    horror_genre: str = "gothic"  # gothic, cosmic, body, psychological, survival
    setting_type: str = "haunted_house"
    fear_progression: List[str] = []
    key_encounters: List[HorrorEncounter] = []
    atmosphere_elements: List[HorrorElement] = []
    climax_encounter: Optional[HorrorEncounter] = None
    resolution_options: List[str] = []
    lasting_consequences: List[str] = []


class HorrorGenerator(BaseGenerator):
    """Generates horror atmosphere tools and scenarios"""
    
    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.character_generator = CharacterGenerator(seed)
    
    async def generate_horror_scenario(self, 
                                     horror_genre: str = "gothic",
                                     setting: str = "haunted_house",
                                     complexity: str = "moderate",
                                     party_level: int = 6,
                                     session_length: str = "standard") -> HorrorScenario:
        """Generate a complete horror scenario"""
        
        genre_config = HORROR_CONFIG["genres"].get(horror_genre, 
                                                 HORROR_CONFIG["genres"]["gothic"])
        setting_config = HORROR_CONFIG["settings"].get(setting,
                                                     HORROR_CONFIG["settings"]["haunted_house"])
        
        # Generate fear progression
        fear_progression = self._generate_fear_progression(complexity, session_length)
        
        # Generate atmosphere elements
        atmosphere_elements = await self._generate_atmosphere_elements(
            horror_genre, setting, complexity, len(fear_progression)
        )
        
        # Generate key encounters
        key_encounters = await self._generate_horror_encounters(
            horror_genre, setting, party_level, complexity, fear_progression
        )
        
        # Generate climax encounter
        climax_encounter = await self._generate_climax_encounter(
            horror_genre, setting, party_level, complexity
        )
        
        scenario = HorrorScenario(
            name=f"{genre_config['name']}: {setting_config['name']}",
            description=f"A {complexity} {horror_genre} horror scenario set in {setting}",
            horror_genre=horror_genre,
            setting_type=setting,
            fear_progression=fear_progression,
            key_encounters=key_encounters,
            atmosphere_elements=atmosphere_elements,
            climax_encounter=climax_encounter,
            resolution_options=self._generate_resolution_options(horror_genre, complexity),
            lasting_consequences=self._generate_lasting_consequences(horror_genre),
            tags=[horror_genre, setting, complexity, f"level_{party_level}"]
        )
        
        return scenario
    
    async def generate_horror_atmosphere(self, 
                                       setting: str = "haunted_house",
                                       intensity: str = "moderate") -> List[HorrorElement]:
        """Generate horror atmosphere elements for a scene"""
        
        elements = []
        element_count = {"mild": 2, "moderate": 4, "intense": 6, "terrifying": 8}.get(intensity, 4)
        
        # Generate different types of elements
        element_types = ["atmosphere", "sensory", "psychological", "supernatural"]
        
        for i in range(element_count):
            element_type = self.rng.choice(element_types)
            element = await self._generate_horror_element(element_type, setting, intensity)
            elements.append(element)
        
        return elements
    
    async def _generate_horror_element(self, 
                                     element_type: str,
                                     setting: str,
                                     intensity: str) -> HorrorElement:
        """Generate a single horror element"""
        
        element_templates = HORROR_CONFIG["element_types"].get(element_type,
                                                             HORROR_CONFIG["element_types"]["atmosphere"])
        setting_templates = HORROR_CONFIG["settings"].get(setting, {})
        
        # Combine generic and setting-specific templates
        all_templates = element_templates.copy()
        if element_type in setting_templates:
            all_templates.extend(setting_templates[element_type])
        
        template = self.rng.choice(all_templates)
        
        # Scale effects based on intensity
        sensory_effects = self._scale_effects(template.get("sensory", []), intensity)
        psychological_effects = self._scale_effects(template.get("psychological", []), intensity)
        mechanical_effects = self._scale_mechanical_effects(template.get("mechanical", []), intensity)
        
        element = HorrorElement(
            name=template["name"],
            description=template["description"],
            element_type=element_type,
            intensity=intensity,
            timing=template.get("timing", "ongoing"),
            sensory_effects=sensory_effects,
            psychological_impact=psychological_effects,
            mechanical_effects=mechanical_effects,
            tags=[element_type, setting, intensity]
        )
        
        return element
    
    async def _generate_horror_encounters(self, 
                                        horror_genre: str,
                                        setting: str,
                                        party_level: int,
                                        complexity: str,
                                        fear_progression: List[str]) -> List[HorrorEncounter]:
        """Generate horror encounters that build tension"""
        
        encounters = []
        encounter_count = len(fear_progression) - 1  # -1 for climax
        
        encounter_templates = HORROR_CONFIG["encounter_templates"].get(horror_genre,
                                                                     HORROR_CONFIG["encounter_templates"]["gothic"])
        
        for i, fear_level in enumerate(fear_progression[:-1]):  # Exclude climax
            template = self.rng.choice(encounter_templates)
            
            # Generate horror elements for this encounter
            horror_elements = await self._generate_encounter_elements(
                horror_genre, setting, fear_level, i + 1
            )
            
            # Scale encounter to party level
            encounter_cr = self._calculate_horror_cr(party_level, fear_level)
            
            encounter = HorrorEncounter(
                name=f"{template['name']} #{i+1}",
                description=template["description"],
                encounter_type="horror",
                difficulty=DifficultyLevel.MODERATE,
                cr=encounter_cr,
                horror_theme=template.get("theme", horror_genre),
                fear_level=fear_level,
                horror_elements=horror_elements,
                escalation_triggers=template.get("escalation", []),
                resolution_methods=template.get("resolution", []),
                aftermath_effects=template.get("aftermath", []),
                environmental_effects=self._generate_environmental_effects(setting, fear_level),
                skill_checks=self._generate_horror_skill_checks(fear_level, party_level),
                tags=[horror_genre, setting, fear_level, f"encounter_{i+1}"]
            )
            
            encounters.append(encounter)
        
        return encounters
    
    async def _generate_climax_encounter(self, 
                                       horror_genre: str,
                                       setting: str,
                                       party_level: int,
                                       complexity: str) -> HorrorEncounter:
        """Generate the climactic horror encounter"""
        
        climax_templates = HORROR_CONFIG["climax_encounters"].get(horror_genre,
                                                                HORROR_CONFIG["climax_encounters"]["gothic"])
        template = self.rng.choice(climax_templates)
        
        # Climax is always terrifying intensity
        horror_elements = await self._generate_encounter_elements(
            horror_genre, setting, "terrifying", 999  # Max encounter number
        )
        
        # Scale to be challenging for the party
        encounter_cr = party_level + 2
        
        climax_encounter = HorrorEncounter(
            name=template["name"],
            description=template["description"],
            encounter_type="horror_boss",
            difficulty=DifficultyLevel.HARD,
            cr=encounter_cr,
            horror_theme=template.get("theme", horror_genre),
            fear_level="terrifying",
            horror_elements=horror_elements,
            escalation_triggers=template.get("escalation", []),
            resolution_methods=template.get("resolution", []),
            aftermath_effects=template.get("aftermath", []),
            environmental_effects=self._generate_environmental_effects(setting, "terrifying"),
            skill_checks=self._generate_horror_skill_checks("terrifying", party_level),
            special_mechanics=template.get("special_mechanics", []),
            tags=[horror_genre, setting, "climax", "terrifying"]
        )
        
        return climax_encounter
    
    async def _generate_encounter_elements(self, 
                                         horror_genre: str,
                                         setting: str,
                                         fear_level: str,
                                         encounter_number: int) -> List[HorrorElement]:
        """Generate horror elements for a specific encounter"""
        
        elements = []
        element_count = {"mild": 1, "moderate": 2, "intense": 3, "terrifying": 4}.get(fear_level, 2)
        
        for i in range(element_count):
            element_type = self.rng.choice(["atmosphere", "psychological", "supernatural"])
            element = await self._generate_horror_element(element_type, setting, fear_level)
            
            # Make elements more specific to encounter
            element.name = f"Encounter {encounter_number}: {element.name}"
            element.timing = "encounter_specific"
            
            elements.append(element)
        
        return elements
    
    def _generate_fear_progression(self, complexity: str, session_length: str) -> List[str]:
        """Generate fear level progression throughout scenario"""
        
        # Base progression patterns
        progressions = {
            "simple": ["mild", "moderate", "intense"],
            "moderate": ["mild", "moderate", "intense", "terrifying"],
            "complex": ["mild", "mild", "moderate", "intense", "terrifying"],
            "epic": ["mild", "mild", "moderate", "moderate", "intense", "terrifying"]
        }
        
        base_progression = progressions.get(complexity, progressions["moderate"])
        
        # Adjust for session length
        if session_length == "short":
            return base_progression[:3]
        elif session_length == "long":
            return base_progression + ["intense"]  # Extended tension
        
        return base_progression
    
    def _scale_effects(self, base_effects: List[str], intensity: str) -> List[str]:
        """Scale effects based on intensity"""
        
        if not base_effects:
            return []
        
        scale_multiplier = {"mild": 1, "moderate": 1, "intense": 2, "terrifying": 2}.get(intensity, 1)
        effect_count = min(len(base_effects), scale_multiplier)
        
        return self.rng.sample(base_effects, effect_count)
    
    def _scale_mechanical_effects(self, base_effects: List[str], intensity: str) -> List[str]:
        """Scale mechanical effects based on intensity"""
        
        if not base_effects:
            return []
        
        # Add intensity-specific modifiers
        intensity_modifiers = {
            "mild": [],
            "moderate": ["Disadvantage on next roll"],
            "intense": ["Disadvantage on next roll", "Must make Wisdom save or be frightened"],
            "terrifying": ["Disadvantage on next roll", "Must make Wisdom save or be frightened", "Speed reduced by 10 feet"]
        }
        
        scaled_effects = base_effects.copy()
        scaled_effects.extend(intensity_modifiers.get(intensity, []))
        
        return scaled_effects
    
    def _calculate_horror_cr(self, party_level: int, fear_level: str) -> int:
        """Calculate appropriate CR for horror encounter"""
        
        base_cr = party_level // 2
        
        fear_modifiers = {
            "mild": -1,
            "moderate": 0,
            "intense": +1,
            "terrifying": +2
        }
        
        return max(1, base_cr + fear_modifiers.get(fear_level, 0))
    
    def _generate_environmental_effects(self, setting: str, fear_level: str) -> List[str]:
        """Generate environmental effects for horror"""
        
        setting_effects = HORROR_CONFIG["environmental_effects"].get(setting, [])
        
        if not setting_effects:
            setting_effects = [
                "Dim lighting creates shadows",
                "Strange sounds echo",
                "Temperature drops noticeably",
                "Air feels thick and oppressive"
            ]
        
        effect_count = {"mild": 1, "moderate": 2, "intense": 3, "terrifying": 4}.get(fear_level, 2)
        return self.rng.sample(setting_effects, min(len(setting_effects), effect_count))
    
    def _generate_horror_skill_checks(self, fear_level: str, party_level: int) -> List[SkillCheck]:
        """Generate skill checks for horror encounters"""
        
        checks = []
        base_dc = 10 + (party_level // 2)
        
        fear_dc_modifiers = {
            "mild": 0,
            "moderate": +2,
            "intense": +4,
            "terrifying": +6
        }
        
        dc = base_dc + fear_dc_modifiers.get(fear_level, 0)
        
        # Common horror skill checks
        horror_checks = [
            {"skill": "Wisdom", "dc": dc, "purpose": "Resist fear"},
            {"skill": "Investigation", "dc": dc - 2, "purpose": "Notice details"},
            {"skill": "Perception", "dc": dc - 1, "purpose": "Detect threats"},
            {"skill": "Insight", "dc": dc, "purpose": "Read intentions"},
            {"skill": "Medicine", "dc": dc + 2, "purpose": "Treat horror effects"}
        ]
        
        check_count = {"mild": 1, "moderate": 2, "intense": 3, "terrifying": 4}.get(fear_level, 2)
        selected_checks = self.rng.sample(horror_checks, min(len(horror_checks), check_count))
        
        for check_data in selected_checks:
            skill_check = SkillCheck(
                skill=check_data["skill"],
                dc=check_data["dc"],
                description=f"{check_data['skill']} check to {check_data['purpose']}"
            )
            checks.append(skill_check)
        
        return checks
    
    def _generate_resolution_options(self, horror_genre: str, complexity: str) -> List[str]:
        """Generate resolution options for the horror scenario"""
        
        base_resolutions = [
            "Confront the source of horror directly",
            "Find and destroy the source of evil",
            "Escape and seal the location",
            "Appease the supernatural force",
            "Break the curse or ritual"
        ]
        
        genre_resolutions = HORROR_CONFIG["resolution_options"].get(horror_genre, [])
        
        all_resolutions = base_resolutions + genre_resolutions
        resolution_count = {"simple": 2, "moderate": 3, "complex": 4, "epic": 5}.get(complexity, 3)
        
        return self.rng.sample(all_resolutions, min(len(all_resolutions), resolution_count))
    
    def _generate_lasting_consequences(self, horror_genre: str) -> List[str]:
        """Generate lasting consequences of the horror experience"""
        
        base_consequences = [
            "Nightmares haunt the characters",
            "Permanent fear of similar situations",
            "Heightened sensitivity to supernatural",
            "Scars that won't fully heal",
            "Memory gaps from traumatic events"
        ]
        
        genre_consequences = HORROR_CONFIG["lasting_consequences"].get(horror_genre, [])
        
        all_consequences = base_consequences + genre_consequences
        return self.rng.sample(all_consequences, min(len(all_consequences), 3))
    
    async def generate_horror_npc(self, 
                                horror_type: str = "victim",
                                party_level: int = 6) -> NPCProfile:
        """Generate an NPC for horror scenarios"""
        
        npc_templates = HORROR_CONFIG["horror_npcs"].get(horror_type,
                                                        HORROR_CONFIG["horror_npcs"]["victim"])
        
        template = self.rng.choice(npc_templates)
        
        # Generate base NPC
        base_npc = await self.character_generator.generate_npc(
            template["name"],
            party_level=party_level
        )
        
        # Add horror-specific elements
        base_npc.description = template["description"]
        base_npc.role = template["role"]
        base_npc.personality_traits = template.get("personality", [])
        base_npc.secrets = template.get("secrets", [])
        base_npc.fears = template.get("fears", [])
        base_npc.horror_connection = template.get("connection", "")
        base_npc.tags.extend([horror_type, "horror_npc"])
        
        return base_npc
    
    async def generate_atmospheric_description(self, 
                                             setting: str = "haunted_house",
                                             time_of_day: str = "night",
                                             weather: str = "storm") -> str:
        """Generate atmospheric description for horror scenes"""
        
        setting_descriptions = HORROR_CONFIG["atmospheric_descriptions"].get(setting, {})
        time_descriptions = setting_descriptions.get(time_of_day, [])
        weather_descriptions = HORROR_CONFIG["weather_descriptions"].get(weather, [])
        
        if not time_descriptions:
            time_descriptions = [
                f"The {setting} looms before you",
                f"Shadows dance across the {setting}",
                f"An eerie stillness surrounds the {setting}"
            ]
        
        base_description = self.rng.choice(time_descriptions)
        weather_element = self.rng.choice(weather_descriptions) if weather_descriptions else ""
        
        if weather_element:
            return f"{base_description}. {weather_element}"
        else:
            return base_description
    
    async def generate_quick_horror_encounter(self, 
                                            horror_type: str = "gothic") -> HorrorEncounter:
        """Generate a quick horror encounter"""
        
        return await self._generate_horror_encounters(
            horror_genre=horror_type,
            setting="haunted_house",
            party_level=5,
            complexity="moderate",
            fear_progression=["moderate"]
        )[0]  # Return first encounter
    
    async def generate_sanity_system(self) -> Dict[str, Any]:
        """Generate optional sanity system mechanics for horror games"""
        
        return {
            "sanity_score": "Start with Wisdom score + level",
            "sanity_loss_triggers": [
                "Witnessing gruesome death: 1d4 sanity",
                "Encountering supernatural horror: 1d6 sanity",
                "Being attacked by undead: 1d3 sanity",
                "Discovering horrible truth: 1d8 sanity"
            ],
            "sanity_recovery": [
                "Long rest in safe place: 1d3 sanity",
                "Completing quest objective: 1d6 sanity",
                "Acting according to ideals: 1 sanity"
            ],
            "sanity_thresholds": {
                "75-100%": "No effect",
                "50-74%": "Disadvantage on Wisdom saves",
                "25-49%": "Gain random short-term madness",
                "1-24%": "Gain random long-term madness",
                "0%": "Gain indefinite madness"
            },
            "optional_rules": [
                "Group sanity pool",
                "Sanity damage resistance",
                "Horror immunity after multiple exposures"
            ]
        }