"""
Chase scene generator for dynamic pursuit encounters
"""

from typing import List, Optional, Dict, Any
from ..models.base import BaseTemplate, ComplexityLevel, DifficultyLevel
from ..models.encounter import ChaseScene, ChaseObstacle, ChasePhase
from ..models.character import NPCProfile
from .base_generator import BaseGenerator
from ..config import CHASE_CONFIG


class ChaseGenerator(BaseGenerator):
    """Generates dynamic chase scene encounters"""
    
    async def generate_chase_scene(self, 
                                 chase_type: str = "foot", 
                                 complexity: str = "moderate",
                                 party_level: int = 5,
                                 terrain: str = "urban") -> ChaseScene:
        """Generate a complete chase scene"""
        
        chase_config = CHASE_CONFIG["chase_types"].get(chase_type, CHASE_CONFIG["chase_types"]["foot"])
        
        # Generate phases
        phase_count = self._get_phase_count(complexity)
        phases = []
        
        for i in range(phase_count):
            phase = await self._generate_chase_phase(
                phase_number=i + 1,
                chase_type=chase_type,
                terrain=terrain,
                party_level=party_level,
                complexity=complexity
            )
            phases.append(phase)
        
        # Generate obstacles
        obstacles = await self._generate_chase_obstacles(
            chase_type=chase_type,
            terrain=terrain,
            party_level=party_level,
            phase_count=phase_count
        )
        
        # Generate pursuers/pursued
        participants = await self._generate_chase_participants(
            chase_type=chase_type,
            party_level=party_level
        )
        
        chase_scene = ChaseScene(
            name=f"{chase_type.title()} Chase through {terrain.title()}",
            description=f"A {complexity} {chase_type} chase scene through {terrain} terrain",
            chase_type=chase_type,
            complexity=ComplexityLevel(complexity),
            terrain=terrain,
            phases=phases,
            obstacles=obstacles,
            success_conditions=self._generate_success_conditions(chase_type),
            failure_consequences=self._generate_failure_consequences(chase_type),
            participants=participants,
            distance_mechanics=chase_config.get("distance_mechanics", {}),
            environmental_effects=self._generate_environmental_effects(terrain),
            tags=[chase_type, terrain, complexity, f"level_{party_level}"]
        )
        
        return chase_scene
    
    async def _generate_chase_phase(self, 
                                  phase_number: int,
                                  chase_type: str,
                                  terrain: str,
                                  party_level: int,
                                  complexity: str) -> ChasePhase:
        """Generate a single phase of the chase"""
        
        phase_templates = CHASE_CONFIG["phase_templates"].get(terrain, CHASE_CONFIG["phase_templates"]["urban"])
        phase_template = self.rng.choice(phase_templates)
        
        # Calculate DC based on party level and complexity
        base_dc = 10 + (party_level // 2)
        complexity_mod = {"simple": -2, "moderate": 0, "complex": +2, "epic": +4}.get(complexity, 0)
        dc = max(8, base_dc + complexity_mod)
        
        phase = ChasePhase(
            name=f"Phase {phase_number}: {phase_template['name']}",
            description=phase_template["description"],
            phase_number=phase_number,
            terrain_type=terrain,
            movement_options=phase_template.get("movement_options", []),
            skill_challenges=phase_template.get("skill_challenges", []),
            dc_modifier=complexity_mod,
            special_rules=phase_template.get("special_rules", []),
            narrative_elements=phase_template.get("narrative_elements", [])
        )
        
        return phase
    
    async def _generate_chase_obstacles(self, 
                                      chase_type: str,
                                      terrain: str,
                                      party_level: int,
                                      phase_count: int) -> List[ChaseObstacle]:
        """Generate obstacles for the chase"""
        
        obstacles = []
        obstacle_templates = CHASE_CONFIG["obstacles"].get(terrain, CHASE_CONFIG["obstacles"]["urban"])
        
        # Generate 1-2 obstacles per phase
        obstacle_count = phase_count + self.rng.randint(0, phase_count)
        
        for i in range(obstacle_count):
            template = self.rng.choice(obstacle_templates)
            
            # Scale DC to party level
            base_dc = template.get("base_dc", 12)
            scaled_dc = max(8, base_dc + (party_level // 3))
            
            obstacle = ChaseObstacle(
                name=template["name"],
                description=template["description"],
                obstacle_type=template.get("type", "physical"),
                difficulty=DifficultyLevel.MODERATE,
                required_checks=template.get("required_checks", []),
                success_effect=template.get("success_effect", "Continue chase normally"),
                failure_effect=template.get("failure_effect", "Fall behind in chase"),
                alternative_solutions=template.get("alternatives", []),
                timing=template.get("timing", "during_movement")
            )
            
            obstacles.append(obstacle)
        
        return obstacles
    
    async def _generate_chase_participants(self, 
                                         chase_type: str,
                                         party_level: int) -> List[NPCProfile]:
        """Generate NPCs involved in the chase"""
        
        participant_templates = CHASE_CONFIG["participants"].get(chase_type, CHASE_CONFIG["participants"]["foot"])
        participants = []
        
        # Generate 1-3 key participants
        for i in range(self.rng.randint(1, 3)):
            template = self.rng.choice(participant_templates)
            
            participant = NPCProfile(
                name=template["name"] + f" #{i+1}",
                description=template["description"],
                role=template["role"],
                stats=template.get("stats", {}),
                abilities=template.get("abilities", []),
                motivations=template.get("motivations", []),
                personality_traits=template.get("personality", []),
                tags=[chase_type, "participant"]
            )
            
            participants.append(participant)
        
        return participants
    
    def _generate_success_conditions(self, chase_type: str) -> List[str]:
        """Generate success conditions for the chase"""
        
        base_conditions = CHASE_CONFIG["success_conditions"].get(chase_type, [
            "Escape pursuit completely",
            "Reach safe destination",
            "Lose pursuers in terrain"
        ])
        
        return self.rng.sample(base_conditions, min(len(base_conditions), 3))
    
    def _generate_failure_consequences(self, chase_type: str) -> List[str]:
        """Generate failure consequences for the chase"""
        
        base_consequences = CHASE_CONFIG["failure_consequences"].get(chase_type, [
            "Caught by pursuers",
            "Injured during escape attempt",
            "Lost in unfamiliar territory"
        ])
        
        return self.rng.sample(base_consequences, min(len(base_consequences), 3))
    
    def _generate_environmental_effects(self, terrain: str) -> List[str]:
        """Generate environmental effects for the chase"""
        
        effects = CHASE_CONFIG["environmental_effects"].get(terrain, [
            "Difficult terrain slows movement",
            "Weather affects visibility",
            "Crowds provide cover but slow progress"
        ])
        
        return self.rng.sample(effects, min(len(effects), 2))
    
    def _get_phase_count(self, complexity: str) -> int:
        """Determine number of phases based on complexity"""
        
        phase_counts = {
            "simple": 2,
            "moderate": 3,
            "complex": 4,
            "epic": 5
        }
        
        base_count = phase_counts.get(complexity, 3)
        return base_count + self.rng.randint(-1, 1)
    
    async def generate_quick_chase(self, chase_type: str = "foot") -> ChaseScene:
        """Generate a quick chase scene with default settings"""
        
        return await self.generate_chase_scene(
            chase_type=chase_type,
            complexity="moderate",
            party_level=5,
            terrain="urban"
        )