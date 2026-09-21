"""
Trap Generator with DC Scaling

Generates various types of traps with appropriate difficulty scaling,
damage calculations, and creative trigger mechanisms for D&D sessions.
"""

import random
import math
from typing import List, Dict, Any, Optional, Tuple

from ..models.encounter import Trap
from ..models.base import DiceRoll, DamageType, SkillType, SkillCheck
from ..config import TRAP_CONFIG
from .base_generator import BaseGenerator


class TrapGenerator(BaseGenerator):
    """Generates traps with level-appropriate scaling"""
    
    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.trap_templates = self._load_trap_templates()
        self.trigger_mechanisms = self._load_trigger_mechanisms()
        self.trap_effects = self._load_trap_effects()
    
    def _load_trap_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load trap templates by type"""
        return {
            "mechanical": {
                "dart_trap": {
                    "description": "Hidden darts shoot from the walls",
                    "triggers": ["pressure_plate", "tripwire", "door_handle"],
                    "damage_types": ["piercing"],
                    "areas": ["single_target", "line"],
                    "complexity": "simple"
                },
                "pit_trap": {
                    "description": "A concealed pit opens beneath victims",
                    "triggers": ["false_floor", "weight_trigger"],
                    "damage_types": ["bludgeoning"],
                    "areas": ["single_target", "small_area"],
                    "complexity": "moderate",
                    "special": ["fall_damage", "difficult_escape"]
                },
                "crushing_walls": {
                    "description": "Walls close in to crush intruders",
                    "triggers": ["entering_room", "touching_altar"],
                    "damage_types": ["bludgeoning"],
                    "areas": ["room_wide"],
                    "complexity": "complex",
                    "special": ["continuous_damage", "escape_time_limit"]
                },
                "scythe_blade": {
                    "description": "A massive blade swings across the passage",
                    "triggers": ["beam_break", "pressure_plate"],
                    "damage_types": ["slashing"],
                    "areas": ["line", "cone"],
                    "complexity": "moderate"
                },
                "arrow_volley": {
                    "description": "Multiple arrows fire from hidden slots",
                    "triggers": ["tripwire", "door_opening"],
                    "damage_types": ["piercing"],
                    "areas": ["cone", "room_wide"],
                    "complexity": "moderate"
                }
            },
            "magical": {
                "fire_rune": {
                    "description": "Magical runes explode in flame when triggered",
                    "triggers": ["proximity", "touch", "keyword"],
                    "damage_types": ["fire"],
                    "areas": ["blast_radius", "cone"],
                    "complexity": "moderate",
                    "special": ["magical_detection", "dispellable"]
                },
                "lightning_trap": {
                    "description": "Electrical energy arcs between conducting surfaces",
                    "triggers": ["metal_contact", "spell_detection"],
                    "damage_types": ["lightning"],
                    "areas": ["chain", "area"],
                    "complexity": "complex",
                    "special": ["conductive_spread", "stunning_effect"]
                },
                "teleportation_circle": {
                    "description": "Victims are teleported to a dangerous location",
                    "triggers": ["stepping_on_circle", "breaking_seal"],
                    "damage_types": ["force"],
                    "areas": ["single_target"],
                    "complexity": "complex",
                    "special": ["displacement", "return_difficulty"]
                },
                "charm_trap": {
                    "description": "Enchantment compels victims to harmful actions",
                    "triggers": ["looking_at_symbol", "hearing_sound"],
                    "damage_types": ["psychic"],
                    "areas": ["single_target", "multiple_targets"],
                    "complexity": "complex",
                    "special": ["mind_control", "friendly_fire"]
                },
                "necrotic_drain": {
                    "description": "Dark energy drains life force from victims",
                    "triggers": ["touching_cursed_item", "proximity"],
                    "damage_types": ["necrotic"],
                    "areas": ["aura", "single_target"],
                    "complexity": "complex",
                    "special": ["life_drain", "undead_immunity"]
                }
            },
            "environmental": {
                "flood_trap": {
                    "description": "Chamber rapidly fills with water",
                    "triggers": ["door_seal", "valve_break"],
                    "damage_types": ["bludgeoning"],
                    "areas": ["room_wide"],
                    "complexity": "complex",
                    "special": ["drowning_risk", "time_pressure", "strength_escape"]
                },
                "poisonous_gas": {
                    "description": "Toxic gas fills the area",
                    "triggers": ["air_disturbance", "container_break"],
                    "damage_types": ["poison"],
                    "areas": ["room_wide", "spreading"],
                    "complexity": "moderate",
                    "special": ["gradual_damage", "constitution_save"]
                },
                "unstable_ceiling": {
                    "description": "The ceiling collapses when supports are weakened",
                    "triggers": ["vibration", "support_damage"],
                    "damage_types": ["bludgeoning"],
                    "areas": ["room_wide"],
                    "complexity": "moderate",
                    "special": ["burial_risk", "debris_cover"]
                },
                "quicksand_floor": {
                    "description": "The floor turns to quicksand",
                    "triggers": ["weight_threshold", "magical_activation"],
                    "damage_types": ["restraint"],
                    "areas": ["floor_area"],
                    "complexity": "moderate",
                    "special": ["gradual_sinking", "strength_escape"]
                }
            },
            "illusory": {
                "false_floor": {
                    "description": "Illusory floor conceals a real pit",
                    "triggers": ["stepping_on_illusion"],
                    "damage_types": ["bludgeoning"],
                    "areas": ["single_target"],
                    "complexity": "moderate",
                    "special": ["investigation_reveals", "fall_surprise"]
                },
                "mirror_trap": {
                    "description": "Mirrors create confusing duplicates and false paths",
                    "triggers": ["looking_in_mirror"],
                    "damage_types": ["psychic"],
                    "areas": ["single_target"],
                    "complexity": "complex",
                    "special": ["confusion_effect", "false_directions"]
                },
                "phantom_walls": {
                    "description": "Solid-seeming walls are actually illusions hiding dangers",
                    "triggers": ["trying_to_pass_through"],
                    "damage_types": ["varies"],
                    "areas": ["line"],
                    "complexity": "complex",
                    "special": ["hidden_dangers", "investigation_needed"]
                }
            }
        }
    
    def _load_trigger_mechanisms(self) -> Dict[str, Dict[str, Any]]:
        """Load detailed trigger mechanisms"""
        return {
            "pressure_plate": {
                "description": "Activates when weight is applied",
                "sensitivity": ["5 lbs", "25 lbs", "100 lbs", "200 lbs"],
                "reset": True,
                "detection_hints": ["slight depression", "different sound when stepped on"],
                "bypass_methods": ["distribute weight", "wedge in place", "magical floating"]
            },
            "tripwire": {
                "description": "Thin wire or magical strand across path",
                "visibility": ["nearly invisible", "camouflaged", "clearly visible"],
                "height": ["ankle", "shin", "knee", "waist"],
                "reset": True,
                "detection_hints": ["glint of wire", "unnatural shadow"],
                "bypass_methods": ["duck under", "step over", "cut carefully"]
            },
            "proximity": {
                "description": "Activates when creature comes within range",
                "range": ["5 feet", "10 feet", "15 feet", "30 feet"],
                "reset": False,
                "detection_hints": ["magical aura", "temperature change"],
                "bypass_methods": ["magical invisibility", "teleportation", "dispel magic"]
            },
            "touch": {
                "description": "Activates when object is touched",
                "sensitivity": ["light touch", "firm grasp", "pressure"],
                "reset": True,
                "detection_hints": ["magical glow", "unusual temperature"],
                "bypass_methods": ["mage hand", "tools", "protective gloves"]
            },
            "motion": {
                "description": "Detects movement in the area",
                "sensitivity": ["any motion", "rapid motion", "large motion"],
                "range": ["5 feet", "15 feet", "30 feet"],
                "reset": True,
                "detection_hints": ["faint humming", "slight air current"],
                "bypass_methods": ["move very slowly", "magical stillness", "teleportation"]
            },
            "sound": {
                "description": "Triggered by specific sounds or noise levels",
                "triggers": ["whispers", "normal speech", "loud noise", "specific word"],
                "reset": True,
                "detection_hints": ["acoustic properties", "echoes"],
                "bypass_methods": ["silence spell", "muffle sounds", "different route"]
            },
            "light": {
                "description": "Activated by light sources or shadows",
                "triggers": ["any light", "bright light", "shadow broken", "darkness"],
                "reset": True,
                "detection_hints": ["light-sensitive crystals", "shadow patterns"],
                "bypass_methods": ["specific lighting", "magical darkness", "illusion"]
            }
        }
    
    def _load_trap_effects(self) -> Dict[str, Dict[str, Any]]:
        """Load trap effect templates"""
        return {
            "immediate_damage": {
                "description": "Instant damage to victims",
                "save_types": ["dexterity", "constitution", "none"],
                "damage_scaling": "level_based"
            },
            "ongoing_damage": {
                "description": "Damage continues each turn",
                "save_types": ["constitution", "strength"],
                "duration": ["1d4 rounds", "1 minute", "until_escaped"],
                "damage_scaling": "reduced_per_turn"
            },
            "condition_effect": {
                "description": "Applies status condition",
                "conditions": ["poisoned", "paralyzed", "charmed", "frightened", "restrained"],
                "duration": ["1 round", "1 minute", "until_dispelled"],
                "save_types": ["constitution", "wisdom", "charisma"]
            },
            "displacement": {
                "description": "Moves victims to different location",
                "destinations": ["nearby_room", "lower_level", "outside_building", "random"],
                "damage_on_arrival": ["none", "minor", "moderate"]
            },
            "alarm": {
                "description": "Alerts guards or other dangers",
                "alert_types": ["sound", "light", "magical_signal", "summoning"],
                "response_time": ["immediate", "1d4 rounds", "1 minute"],
                "coverage": ["local", "building_wide", "area_wide"]
            }
        }
    
    async def generate_trap(self, trap_type: str = None, party_level: int = 5,
                          complexity: str = "moderate", location_theme: str = "dungeon") -> Trap:
        """Generate a trap with appropriate scaling"""
        
        # Select trap type if not specified
        if not trap_type:
            trap_type = self.weighted_choice(TRAP_CONFIG["trap_types"])
        
        # Get available traps of this type
        available_traps = self.trap_templates.get(trap_type, self.trap_templates["mechanical"])
        trap_template_name = self.rng.choice(list(available_traps.keys()))
        trap_template = available_traps[trap_template_name]
        
        # Create base trap
        trap = Trap(
            name=f"{trap_template_name.replace('_', ' ').title()}",
            description=trap_template["description"],
            trap_type=trap_type,
            party_level=party_level,
            complexity=complexity
        )
        
        # Set trigger mechanism
        trigger_type = self.rng.choice(trap_template["triggers"])
        trap.trigger_type = trigger_type
        trap.trigger_description = await self._generate_trigger_description(trigger_type)
        
        # Set detection and disarm DCs
        trap.detect_dc, trap.disarm_dc = self._calculate_trap_dcs(party_level, complexity)
        
        # Set damage
        damage_type = self.rng.choice(trap_template["damage_types"])
        trap.damage_type = damage_type
        trap.damage_dice = self._calculate_trap_damage(party_level, damage_type, complexity)
        
        # Set save DC and type
        trap.save_dc = self._calculate_save_dc(party_level, complexity)
        trap.save_type = self._determine_save_type(damage_type, trap_template)
        
        # Set area of effect
        if "areas" in trap_template:
            trap.area_of_effect = self.rng.choice(trap_template["areas"])
        
        # Add special properties
        if "special" in trap_template:
            trap.special_conditions.extend(trap_template["special"])
        
        # Generate bypass methods
        trap.bypass_methods = await self._generate_bypass_methods(trigger_type, trap_template)
        
        # Add thematic elements
        await self._add_thematic_elements(trap, location_theme)
        
        # Set reset mechanism
        trap.reset_mechanism = self.rng.random() < 0.3  # 30% chance of reset
        
        # Generate linked traps for complex traps
        if complexity == "complex" and self.rng.random() < 0.4:
            trap.combination_trap = True
            trap.linked_traps = await self._generate_linked_trap_names()
        
        # Add DM notes
        trap.dm_notes = await self._generate_trap_dm_notes(trap)
        
        return trap
    
    def _calculate_trap_dcs(self, party_level: int, complexity: str) -> Tuple[int, int]:
        """Calculate detection and disarm DCs based on level and complexity"""
        
        # Base DCs from config, scaled by level
        base_scaling = TRAP_CONFIG["dc_scaling"]
        
        # Find appropriate level bracket
        level_brackets = sorted(base_scaling.keys(), reverse=True)
        bracket_level = next((lvl for lvl in level_brackets if party_level >= lvl), 1)
        
        base_detect = base_scaling[bracket_level]["detect"]
        base_disarm = base_scaling[bracket_level]["disarm"]
        
        # Adjust for complexity
        complexity_modifiers = {
            "simple": -2,
            "moderate": 0,
            "complex": +3,
            "legendary": +5
        }
        
        modifier = complexity_modifiers.get(complexity, 0)
        
        detect_dc = max(10, base_detect + modifier)
        disarm_dc = max(10, base_disarm + modifier)
        
        return detect_dc, disarm_dc
    
    def _calculate_trap_damage(self, party_level: int, damage_type: str, 
                              complexity: str) -> DiceRoll:
        """Calculate appropriate trap damage"""
        
        # Base damage scaling by level
        if party_level <= 4:
            base_dice = 1
            die_size = 6
        elif party_level <= 10:
            base_dice = 2
            die_size = 6
        elif party_level <= 16:
            base_dice = 3
            die_size = 8
        else:
            base_dice = 4
            die_size = 10
        
        # Adjust for complexity
        complexity_multipliers = {
            "simple": 0.75,
            "moderate": 1.0,
            "complex": 1.5,
            "legendary": 2.0
        }
        
        multiplier = complexity_multipliers.get(complexity, 1.0)
        adjusted_dice = max(1, int(base_dice * multiplier))
        
        # Some damage types do more/less damage
        damage_type_modifiers = {
            DamageType.FIRE: 1.0,
            DamageType.COLD: 1.0,
            DamageType.LIGHTNING: 1.1,
            DamageType.THUNDER: 1.0,
            DamageType.POISON: 0.8,  # Usually ongoing
            DamageType.ACID: 1.0,
            DamageType.NECROTIC: 1.2,
            DamageType.RADIANT: 1.2,
            DamageType.FORCE: 1.3,
            DamageType.PSYCHIC: 1.1,
            DamageType.PIERCING: 1.0,
            DamageType.SLASHING: 1.0,
            DamageType.BLUDGEONING: 1.0
        }
        
        type_multiplier = damage_type_modifiers.get(damage_type, 1.0)
        final_dice = max(1, int(adjusted_dice * type_multiplier))
        
        # Add flat modifier for higher levels
        modifier = max(0, party_level // 4)
        
        return DiceRoll(dice_count=final_dice, dice_sides=die_size, modifier=modifier)
    
    def _calculate_save_dc(self, party_level: int, complexity: str) -> int:
        """Calculate saving throw DC"""
        base_dc = 8 + (party_level // 2)
        
        complexity_modifiers = {
            "simple": 0,
            "moderate": 1,
            "complex": 3,
            "legendary": 5
        }
        
        modifier = complexity_modifiers.get(complexity, 1)
        return min(25, base_dc + modifier)
    
    def _determine_save_type(self, damage_type: str, trap_template: Dict[str, Any]) -> str:
        """Determine appropriate saving throw type"""
        
        # Physical damage usually uses Dex saves
        physical_damage = [DamageType.PIERCING, DamageType.SLASHING, DamageType.BLUDGEONING]
        if damage_type in physical_damage:
            return "dexterity"
        
        # Environmental effects often use Constitution
        environmental_damage = [DamageType.POISON, DamageType.COLD, DamageType.FIRE]
        if damage_type in environmental_damage:
            return "constitution"
        
        # Mental effects use Wisdom or Charisma
        if damage_type == DamageType.PSYCHIC:
            return self.rng.choice(["wisdom", "charisma"])
        
        # Energy damage typically uses Dexterity
        energy_damage = [DamageType.LIGHTNING, DamageType.THUNDER, DamageType.FORCE]
        if damage_type in energy_damage:
            return "dexterity"
        
        # Default to Dexterity for avoidance
        return "dexterity"
    
    async def _generate_trigger_description(self, trigger_type: str) -> str:
        """Generate detailed trigger description"""
        trigger_data = self.trigger_mechanisms.get(trigger_type, {})
        base_description = trigger_data.get("description", "Activates when disturbed")
        
        # Add specific details based on trigger type
        if trigger_type == "pressure_plate":
            sensitivity = self.rng.choice(trigger_data.get("sensitivity", ["25 lbs"]))
            return f"{base_description} (threshold: {sensitivity})"
        
        elif trigger_type == "proximity":
            range_val = self.rng.choice(trigger_data.get("range", ["10 feet"]))
            return f"{base_description} (range: {range_val})"
        
        elif trigger_type == "tripwire":
            height = self.rng.choice(trigger_data.get("height", ["shin"]))
            visibility = self.rng.choice(trigger_data.get("visibility", ["nearly invisible"]))
            return f"{base_description} ({visibility} at {height} height)"
        
        return base_description
    
    async def _generate_bypass_methods(self, trigger_type: str, 
                                     trap_template: Dict[str, Any]) -> List[str]:
        """Generate ways to bypass the trap"""
        bypass_methods = []
        
        # Get trigger-specific bypasses
        trigger_data = self.trigger_mechanisms.get(trigger_type, {})
        if "bypass_methods" in trigger_data:
            bypass_methods.extend(
                self.rng.sample(trigger_data["bypass_methods"], 
                               min(2, len(trigger_data["bypass_methods"])))
            )
        
        # Add general bypass methods
        general_bypasses = [
            "Disable mechanism with thieves' tools",
            "Jam the trigger mechanism",
            "Use magic to avoid triggering",
            "Find alternate route around trap",
            "Trigger safely from distance"
        ]
        
        bypass_methods.extend(
            self.rng.sample(general_bypasses, min(2, len(general_bypasses)))
        )
        
        return list(set(bypass_methods))[:4]  # Remove duplicates, limit to 4
    
    async def _add_thematic_elements(self, trap: Trap, theme: str):
        """Add thematic flavor to trap based on location"""
        
        theme_descriptions = {
            "dungeon": {
                "mechanical": "ancient stonework and corroded metal mechanisms",
                "magical": "glowing runes carved into weathered stone",
                "environmental": "dank conditions and structural decay"
            },
            "temple": {
                "mechanical": "sacred geometry and divine machinery",
                "magical": "holy symbols and blessed enchantments",
                "environmental": "sanctified elements and divine wrath"
            },
            "tomb": {
                "mechanical": "burial chamber mechanisms and grave goods",
                "magical": "necromantic wards and death magic",
                "environmental": "disturbed rest and undead guardians"
            },
            "wizard_tower": {
                "mechanical": "arcane contraptions and magical automation",
                "magical": "experimental spells and volatile magic",
                "environmental": "magical accidents and unstable enchantments"
            }
        }
        
        theme_data = theme_descriptions.get(theme, theme_descriptions["dungeon"])
        trap_type_theme = theme_data.get(trap.trap_type, "mysterious construction")
        
        # Add thematic description
        trap.effect_description = f"The trap utilizes {trap_type_theme} to create its dangerous effect."
        
        # Add theme-appropriate detection hints
        if theme == "temple":
            trap.dm_notes.append("Religious characters might notice the divine nature of the trap")
        elif theme == "wizard_tower":
            trap.dm_notes.append("Characters with Arcana skill get advantage on detection")
        elif theme == "tomb":
            trap.dm_notes.append("Undead creatures are immune to this trap's effects")
    
    async def _generate_linked_trap_names(self) -> List[str]:
        """Generate names for linked traps in a combination"""
        linked_names = [
            "Secondary Pressure Plate",
            "Backup Dart Launcher", 
            "Overflow Gas Release",
            "Emergency Lock System",
            "Alarm Trigger Mechanism"
        ]
        
        num_linked = self.rng.randint(1, 3)
        return self.rng.sample(linked_names, min(num_linked, len(linked_names)))
    
    async def _generate_trap_dm_notes(self, trap: Trap) -> List[str]:
        """Generate helpful DM notes for running the trap"""
        notes = []
        
        # General notes
        notes.append(f"Detection DC: {trap.detect_dc}, Disarm DC: {trap.disarm_dc}")
        notes.append(f"Save: DC {trap.save_dc} {trap.save_type.title()} for half damage")
        
        # Trigger-specific notes
        if trap.trigger_type == "pressure_plate":
            notes.append("Can be triggered by objects thrown onto it")
        elif trap.trigger_type == "proximity":
            notes.append("Triggers even if creature is invisible")
        elif trap.trigger_type == "tripwire":
            notes.append("Can be seen with careful examination")
        
        # Damage notes
        if trap.damage_dice:
            avg_damage = (trap.damage_dice.dice_count * (trap.damage_dice.dice_sides + 1) / 2) + trap.damage_dice.modifier
            notes.append(f"Average damage: {int(avg_damage)} {trap.damage_type}")
        
        # Reset notes
        if trap.reset_mechanism:
            notes.append("Trap resets after 1 minute")
        else:
            notes.append("Trap is single-use only")
        
        # Combination trap notes
        if trap.combination_trap:
            notes.append("Part of a combination - other traps activate if this one is triggered")
        
        return notes
    
    async def generate_trap_sequence(self, party_level: int, num_traps: int = 3,
                                   escalating: bool = True) -> List[Trap]:
        """Generate a sequence of traps with escalating difficulty"""
        traps = []
        
        complexities = ["simple", "moderate", "complex"]
        if not escalating:
            complexities = ["moderate"] * num_traps
        elif num_traps <= 3:
            complexities = complexities[:num_traps]
        else:
            # Extend pattern for longer sequences
            extended = (complexities * ((num_traps // 3) + 1))[:num_traps]
            complexities = extended
        
        # Vary trap types
        trap_types = list(TRAP_CONFIG["trap_types"].keys())
        
        for i, complexity in enumerate(complexities):
            trap_type = self.rng.choice(trap_types)
            trap = await self.generate_trap(trap_type, party_level, complexity)
            trap.name = f"Trap {i + 1}: {trap.name}"
            traps.append(trap)
        
        return traps
    
    async def generate_combination_trap(self, party_level: int, num_components: int = 3) -> Trap:
        """Generate a complex combination trap with multiple components"""
        
        # Create main trap
        main_trap = await self.generate_trap("mechanical", party_level, "complex")
        main_trap.name = f"Multi-Stage {main_trap.name}"
        main_trap.combination_trap = True
        
        # Add component traps
        component_types = ["dart_trap", "pressure_trigger", "alarm_system"]
        main_trap.linked_traps = self.rng.sample(component_types, min(num_components, len(component_types)))
        
        # Increase detection difficulty for combination
        main_trap.detect_dc += 2
        main_trap.disarm_dc += 3
        
        # Add special combination mechanics
        main_trap.special_conditions.extend([
            "requires_multiple_disarm_attempts",
            "components_must_be_disabled_in_order",
            "failure_triggers_all_components"
        ])
        
        main_trap.description += f" This trap has {len(main_trap.linked_traps)} interconnected components."
        
        main_trap.dm_notes.extend([
            f"Has {len(main_trap.linked_traps)} components that must be handled separately",
            "Each component requires its own check to detect and disarm",
            "Failing to disarm one component triggers all others"
        ])
        
        return main_trap
    
    async def generate_guardian_trap(self, party_level: int, guardian_type: str = "construct") -> Trap:
        """Generate a trap that summons or activates guardians"""
        
        trap = await self.generate_trap("magical", party_level, "complex")
        trap.name = f"Guardian Summoning {trap.name}"
        
        # Modify to summon guardians instead of direct damage
        trap.damage_dice = None  # No direct damage
        trap.damage_type = "summoning"
        
        guardians = {
            "construct": ["animated armor", "stone golem", "clockwork sentinel"],
            "undead": ["skeleton warrior", "wight guardian", "specter"],
            "elemental": ["fire elemental", "air elemental", "earth elemental"],
            "fiend": ["imp", "quasit", "minor demon"],
            "celestial": ["deva", "solar guardian", "angelic protector"]
        }
        
        guardian_list = guardians.get(guardian_type, guardians["construct"])
        summoned_guardian = self.rng.choice(guardian_list)
        
        trap.effect_description = f"Summons a {summoned_guardian} to defend the area"
        
        trap.special_conditions.extend([
            f"summons_{guardian_type}",
            "guardian_fights_until_destroyed",
            "trap_resets_after_guardian_defeated"
        ])
        
        trap.dm_notes.extend([
            f"Summons 1 {summoned_guardian} (use appropriate stat block)",
            "Guardian appears within 10 feet of triggered area",
            "Guardian follows basic commands to defend the area",
            "Trap cannot be triggered again until guardian is defeated"
        ])
        
        return trap
    
    async def generate_environmental_hazard(self, party_level: int, 
                                          environment: str = "dungeon") -> Trap:
        """Generate environmental hazards that act like traps"""
        
        hazard_types = {
            "dungeon": ["unstable_ceiling", "poisonous_gas", "flood_trap"],
            "wilderness": ["quicksand", "avalanche", "forest_fire"],
            "urban": ["building_collapse", "sewer_gas", "crowd_panic"],
            "underground": ["cave_in", "gas_pocket", "underground_river"],
            "coastal": ["tide_trap", "unstable_cliff", "sea_cave_flooding"],
            "mountain": ["rockslide", "thin_air", "avalanche"],
            "desert": ["sandstorm", "mirage_trap", "sand_sinkhole"],
            "arctic": ["ice_crack", "blizzard", "hypothermia_zone"],
            "swamp": ["bog_trap", "disease_mist", "predator_ambush"]
        }
        
        available_hazards = hazard_types.get(environment, hazard_types["dungeon"])
        hazard_type = self.rng.choice(available_hazards)
        
        trap = Trap(
            name=f"Environmental Hazard: {hazard_type.replace('_', ' ').title()}",
            description=f"A natural {hazard_type.replace('_', ' ')} poses danger to travelers",
            trap_type="environmental",
            party_level=party_level
        )
        
        # Environmental hazards often have different mechanics
        trap.detect_dc = 12 + party_level // 3  # Easier to detect
        trap.disarm_dc = 15 + party_level // 2  # May be harder to "disarm"
        
        # Environmental hazards often affect larger areas
        trap.area_of_effect = self.rng.choice(["large_area", "room_wide", "regional"])
        
        # Usually ongoing effects
        trap.special_conditions.extend([
            "ongoing_effect",
            "area_denial",
            "requires_environmental_solution"
        ])
        
        return trap