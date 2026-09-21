"""
Heist planning generator for complex theft scenarios
"""

from typing import List, Optional, Dict, Any
from ..models.base import BaseTemplate, ComplexityLevel, DifficultyLevel
from ..models.encounter import HeistPlan, HeistPhase, SecurityMeasure, HeistRole
from ..models.character import NPCProfile
from .base_generator import BaseGenerator
from ..config import HEIST_CONFIG


class HeistGenerator(BaseGenerator):
    """Generates complex heist planning scenarios"""
    
    async def generate_heist_plan(self, 
                                target_type: str = "bank", 
                                complexity: str = "moderate",
                                party_level: int = 8,
                                crew_size: int = 4) -> HeistPlan:
        """Generate a complete heist plan"""
        
        target_config = HEIST_CONFIG["targets"].get(target_type, HEIST_CONFIG["targets"]["bank"])
        
        # Generate the target
        target = await self._generate_heist_target(target_type, party_level, complexity)
        
        # Generate security measures
        security_measures = await self._generate_security_measures(
            target_type, party_level, complexity
        )
        
        # Generate heist phases
        phases = await self._generate_heist_phases(
            target_type, complexity, security_measures
        )
        
        # Generate crew roles
        crew_roles = await self._generate_crew_roles(
            target_type, crew_size, complexity
        )
        
        # Generate contingency plans
        contingencies = await self._generate_contingency_plans(
            target_type, complexity, phases
        )
        
        heist_plan = HeistPlan(
            name=f"Operation {self._generate_heist_codename()}",
            description=f"A {complexity} heist targeting {target['name']}",
            target_location=target["name"],
            target_description=target["description"],
            complexity=ComplexityLevel(complexity),
            estimated_duration=self._calculate_duration(complexity, len(phases)),
            crew_size_required=crew_size,
            phases=phases,
            security_measures=security_measures,
            required_skills=self._determine_required_skills(phases, security_measures),
            equipment_needed=self._determine_equipment_needed(phases, security_measures),
            crew_roles=crew_roles,
            contingency_plans=contingencies,
            success_conditions=target_config.get("success_conditions", []),
            failure_consequences=target_config.get("failure_consequences", []),
            payout_potential=self._calculate_payout(target_type, party_level, complexity),
            heat_level=self._calculate_heat_level(target_type, complexity),
            tags=[target_type, complexity, f"level_{party_level}", f"crew_{crew_size}"]
        )
        
        return heist_plan
    
    async def _generate_heist_target(self, target_type: str, party_level: int, complexity: str) -> Dict[str, Any]:
        """Generate the heist target location"""
        
        target_templates = HEIST_CONFIG["targets"][target_type]["locations"]
        template = self.rng.choice(target_templates)
        
        target = {
            "name": template["name"],
            "description": template["description"],
            "layout": template.get("layout", {}),
            "notable_features": template.get("features", []),
            "access_points": template.get("access_points", []),
            "valuable_items": self._scale_valuables(template.get("valuables", []), party_level)
        }
        
        return target
    
    async def _generate_security_measures(self, 
                                        target_type: str, 
                                        party_level: int, 
                                        complexity: str) -> List[SecurityMeasure]:
        """Generate security measures for the target"""
        
        security_templates = HEIST_CONFIG["security_measures"].get(target_type, 
                                                                 HEIST_CONFIG["security_measures"]["generic"])
        
        # Number of security measures based on complexity
        measure_count = {"simple": 2, "moderate": 3, "complex": 5, "epic": 7}.get(complexity, 3)
        
        security_measures = []
        selected_templates = self.rng.sample(security_templates, 
                                           min(len(security_templates), measure_count))
        
        for template in selected_templates:
            # Scale DC to party level
            base_dc = template.get("bypass_dc", 15)
            scaled_dc = max(10, base_dc + (party_level // 3))
            
            measure = SecurityMeasure(
                name=template["name"],
                description=template["description"],
                security_type=template["type"],
                bypass_methods=template.get("bypass_methods", []),
                detection_chance=template.get("detection_chance", 50),
                alert_level=template.get("alert_level", "medium"),
                countermeasures=template.get("countermeasures", [])
            )
            
            security_measures.append(measure)
        
        return security_measures
    
    async def _generate_heist_phases(self, 
                                   target_type: str, 
                                   complexity: str,
                                   security_measures: List[SecurityMeasure]) -> List[HeistPhase]:
        """Generate phases of the heist"""
        
        phase_templates = HEIST_CONFIG["phase_templates"]
        phases = []
        
        # Always include these core phases
        core_phases = ["reconnaissance", "infiltration", "execution", "escape"]
        
        # Add optional phases based on complexity
        optional_phases = ["preparation", "misdirection", "cleanup"]
        if complexity in ["complex", "epic"]:
            core_phases.extend(self.rng.sample(optional_phases, 
                                             2 if complexity == "complex" else 3))
        
        for i, phase_type in enumerate(core_phases):
            template = phase_templates.get(phase_type, phase_templates["generic"])
            
            phase = HeistPhase(
                name=f"Phase {i+1}: {template['name']}",
                description=template["description"],
                phase_type=phase_type,
                duration_minutes=template.get("duration", 30),
                required_actions=template.get("required_actions", []),
                skill_challenges=template.get("skill_challenges", []),
                risk_factors=template.get("risk_factors", []),
                success_conditions=template.get("success_conditions", []),
                failure_consequences=template.get("failure_consequences", [])
            )
            
            phases.append(phase)
        
        return phases
    
    async def _generate_crew_roles(self, 
                                 target_type: str, 
                                 crew_size: int, 
                                 complexity: str) -> List[HeistRole]:
        """Generate required crew roles for the heist"""
        
        role_templates = HEIST_CONFIG["crew_roles"]
        roles = []
        
        # Core roles always needed
        core_roles = ["mastermind", "infiltrator"]
        
        # Additional roles based on crew size and complexity
        additional_roles = ["lookout", "tech_specialist", "muscle", "face", "driver", "safecracker"]
        
        total_roles = core_roles + self.rng.sample(additional_roles, crew_size - len(core_roles))
        
        for role_type in total_roles[:crew_size]:
            template = role_templates.get(role_type, role_templates["generic"])
            
            role = HeistRole(
                name=template["name"],
                description=template["description"],
                role_type=role_type,
                required_skills=template.get("required_skills", []),
                key_abilities=template.get("abilities", []),
                responsibilities=template.get("responsibilities", []),
                backup_plans=template.get("backup_plans", [])
            )
            
            roles.append(role)
        
        return roles
    
    async def _generate_contingency_plans(self, 
                                        target_type: str, 
                                        complexity: str,
                                        phases: List[HeistPhase]) -> List[str]:
        """Generate contingency plans for when things go wrong"""
        
        base_contingencies = HEIST_CONFIG["contingencies"].get(target_type, 
                                                             HEIST_CONFIG["contingencies"]["generic"])
        
        # Number of contingencies based on complexity
        contingency_count = {"simple": 2, "moderate": 3, "complex": 4, "epic": 5}.get(complexity, 3)
        
        return self.rng.sample(base_contingencies, min(len(base_contingencies), contingency_count))
    
    def _determine_required_skills(self, 
                                 phases: List[HeistPhase], 
                                 security_measures: List[SecurityMeasure]) -> List[str]:
        """Determine skills required for the heist"""
        
        skills = set()
        
        # Skills from phases
        for phase in phases:
            for challenge in phase.skill_challenges:
                if isinstance(challenge, dict) and "skill" in challenge:
                    skills.add(challenge["skill"])
        
        # Skills from security measures
        for measure in security_measures:
            for method in measure.bypass_methods:
                if isinstance(method, dict) and "skill" in method:
                    skills.add(method["skill"])
        
        return list(skills)
    
    def _determine_equipment_needed(self, 
                                  phases: List[HeistPhase], 
                                  security_measures: List[SecurityMeasure]) -> List[str]:
        """Determine equipment needed for the heist"""
        
        equipment = set()
        
        # Base equipment for most heists
        base_equipment = ["lockpicks", "rope", "grappling_hook", "dark_clothing", "communication_devices"]
        equipment.update(self.rng.sample(base_equipment, 3))
        
        # Equipment from security measures
        for measure in security_measures:
            for method in measure.bypass_methods:
                if isinstance(method, dict) and "equipment" in method:
                    equipment.add(method["equipment"])
        
        return list(equipment)
    
    def _generate_heist_codename(self) -> str:
        """Generate a codename for the heist"""
        
        adjectives = ["Silent", "Golden", "Shadow", "Midnight", "Perfect", "Crimson", "Steel", "Ghost"]
        nouns = ["Thunder", "Falcon", "Serpent", "Phoenix", "Wolf", "Tiger", "Dragon", "Raven"]
        
        return f"{self.rng.choice(adjectives)} {self.rng.choice(nouns)}"
    
    def _calculate_duration(self, complexity: str, phase_count: int) -> int:
        """Calculate estimated heist duration in hours"""
        
        base_hours = {"simple": 2, "moderate": 4, "complex": 6, "epic": 8}.get(complexity, 4)
        return base_hours + (phase_count // 2)
    
    def _calculate_payout(self, target_type: str, party_level: int, complexity: str) -> Dict[str, int]:
        """Calculate potential payout for the heist"""
        
        base_values = {
            "bank": 5000,
            "mansion": 3000,
            "museum": 8000,
            "casino": 4000,
            "warehouse": 2000
        }
        
        base = base_values.get(target_type, 3000)
        level_multiplier = 1 + (party_level * 0.2)
        complexity_multiplier = {"simple": 0.8, "moderate": 1.0, "complex": 1.5, "epic": 2.0}.get(complexity, 1.0)
        
        total = int(base * level_multiplier * complexity_multiplier)
        
        return {
            "minimum": int(total * 0.6),
            "expected": total,
            "maximum": int(total * 1.4)
        }
    
    def _calculate_heat_level(self, target_type: str, complexity: str) -> str:
        """Calculate heat level (law enforcement response)"""
        
        base_heat = {
            "bank": "high",
            "mansion": "medium",
            "museum": "high",
            "casino": "high",
            "warehouse": "low"
        }
        
        heat = base_heat.get(target_type, "medium")
        
        # Complexity can increase heat
        if complexity == "epic" and heat != "high":
            heat_levels = ["low", "medium", "high"]
            current_index = heat_levels.index(heat)
            heat = heat_levels[min(current_index + 1, len(heat_levels) - 1)]
        
        return heat
    
    def _scale_valuables(self, base_valuables: List[Dict], party_level: int) -> List[Dict]:
        """Scale valuable items to party level"""
        
        scaled = []
        for item in base_valuables:
            scaled_item = item.copy()
            if "value" in scaled_item:
                scaled_item["value"] = int(scaled_item["value"] * (1 + party_level * 0.1))
            scaled.append(scaled_item)
        
        return scaled
    
    async def generate_quick_heist(self, target_type: str = "bank") -> HeistPlan:
        """Generate a quick heist with default settings"""
        
        return await self.generate_heist_plan(
            target_type=target_type,
            complexity="moderate",
            party_level=8,
            crew_size=4
        )