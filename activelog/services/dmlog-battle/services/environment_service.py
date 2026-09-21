"""
Environmental hazards and interactive terrain service.
"""

import random
import math
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import logging

from ..models.base import Position, TerrainType, DamageType
from ..models.battlefield import (
    BattlefieldSchema, EnvironmentalHazard, InteractiveObject, 
    LightSource, GridArea
)
from ..models.combatant import CombatantSchema
from ..models.combat import CombatEncounter, CombatAction
from ..config import Config

logger = logging.getLogger(__name__)

@dataclass
class HazardActivation:
    """Result of a hazard activation."""
    hazard_id: str
    triggered_by: str  # combatant ID
    trigger_type: str
    damage_dealt: Dict[str, int]
    conditions_applied: Dict[str, List[str]]
    description: str
    timestamp: datetime

@dataclass
class ObjectInteraction:
    """Result of object interaction."""
    object_id: str
    interacted_by: str  # combatant ID
    interaction_type: str
    success: bool
    effects: List[str]
    damage_to_object: int
    changes_to_battlefield: List[str]
    timestamp: datetime

class EnvironmentService:
    """Service for managing environmental hazards and interactive terrain."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.hazard_templates = self._initialize_hazard_templates()
        self.object_templates = self._initialize_object_templates()
    
    def _initialize_hazard_templates(self) -> Dict[str, Dict]:
        """Initialize common environmental hazard templates."""
        
        templates = {
            "fire_trap": {
                "name": "Fire Trap",
                "hazard_type": "fire",
                "damage_per_turn": ["2d6"],
                "save_dc": 15,
                "save_ability": "dexterity",
                "triggers_on": ["entry", "start_turn"],
                "duration_rounds": -1,  # Permanent
                "recharges": False,
                "visible": True,
                "detectable": True,
                "detection_dc": 15,
                "disarmable": True,
                "disarm_dc": 20
            },
            
            "acid_pool": {
                "name": "Acid Pool", 
                "hazard_type": "acid",
                "damage_per_turn": ["1d6"],
                "save_dc": None,
                "save_ability": None,
                "triggers_on": ["entry", "start_turn", "end_turn"],
                "duration_rounds": -1,
                "recharges": True,
                "visible": True,
                "detectable": True,
                "detection_dc": 0,  # Obvious
                "disarmable": False,
                "disarm_dc": 0
            },
            
            "poison_gas": {
                "name": "Poison Gas",
                "hazard_type": "poison",
                "damage_per_turn": ["1d4"],
                "save_dc": 12,
                "save_ability": "constitution",
                "triggers_on": ["start_turn"],
                "duration_rounds": 10,
                "recharges": False,
                "visible": False,
                "detectable": True,
                "detection_dc": 18,
                "disarmable": False,
                "disarm_dc": 0
            },
            
            "spike_trap": {
                "name": "Spike Trap",
                "hazard_type": "piercing",
                "damage_per_turn": ["2d10"],
                "save_dc": 15,
                "save_ability": "dexterity", 
                "triggers_on": ["entry"],
                "duration_rounds": 0,  # One-time
                "recharges": False,
                "visible": False,
                "detectable": True,
                "detection_dc": 18,
                "disarmable": True,
                "disarm_dc": 20
            },
            
            "lightning_storm": {
                "name": "Lightning Storm",
                "hazard_type": "lightning",
                "damage_per_turn": ["3d8"],
                "save_dc": 16,
                "save_ability": "dexterity",
                "triggers_on": ["start_turn"],
                "duration_rounds": 5,
                "recharges": True,
                "recharge_time": 3,
                "visible": True,
                "detectable": True,
                "detection_dc": 0,
                "disarmable": False,
                "disarm_dc": 0
            }
        }
        
        return templates
    
    def _initialize_object_templates(self) -> Dict[str, Dict]:
        """Initialize interactive object templates."""
        
        templates = {
            "door": {
                "name": "Door",
                "blocks_movement": True,
                "blocks_vision": True,
                "provides_cover": "total",
                "interaction_types": ["open", "close", "break"],
                "action_required": "action",
                "range_required": 5,
                "armor_class": 15,
                "hit_points": 18,
                "damage_threshold": 5,
                "damage_immunities": ["poison", "psychic"],
                "damage_resistances": [],
                "effects": ["opens_passage", "blocks_passage"]
            },
            
            "chest": {
                "name": "Chest",
                "blocks_movement": True,
                "blocks_vision": False,
                "provides_cover": "half",
                "interaction_types": ["open", "search", "break"],
                "action_required": "action",
                "range_required": 5,
                "armor_class": 15,
                "hit_points": 10,
                "damage_threshold": 0,
                "damage_immunities": ["poison", "psychic"],
                "damage_resistances": [],
                "effects": ["contains_loot"]
            },
            
            "lever": {
                "name": "Lever",
                "blocks_movement": False,
                "blocks_vision": False,
                "provides_cover": "none",
                "interaction_types": ["activate"],
                "action_required": "action",
                "range_required": 5,
                "armor_class": 12,
                "hit_points": 5,
                "damage_threshold": 0,
                "damage_immunities": [],
                "damage_resistances": [],
                "effects": ["triggers_mechanism"],
                "uses_remaining": -1
            },
            
            "pillar": {
                "name": "Pillar",
                "blocks_movement": True,
                "blocks_vision": True,
                "provides_cover": "total",
                "interaction_types": ["break", "climb"],
                "action_required": "action",
                "range_required": 0,
                "armor_class": 17,
                "hit_points": 50,
                "damage_threshold": 10,
                "damage_immunities": ["poison", "psychic"],
                "damage_resistances": ["fire", "cold"],
                "effects": ["structural_collapse"]
            },
            
            "altar": {
                "name": "Altar",
                "blocks_movement": True,
                "blocks_vision": False,
                "provides_cover": "half",
                "interaction_types": ["activate", "desecrate"],
                "action_required": "action",
                "range_required": 5,
                "armor_class": 18,
                "hit_points": 30,
                "damage_threshold": 5,
                "damage_immunities": ["poison", "psychic"],
                "damage_resistances": ["necrotic", "radiant"],
                "effects": ["magical_effect"],
                "uses_remaining": 3
            }
        }
        
        return templates
    
    def create_hazard(
        self,
        hazard_type: str,
        positions: List[Position],
        battlefield: BattlefieldSchema,
        custom_properties: Optional[Dict] = None
    ) -> EnvironmentalHazard:
        """Create an environmental hazard."""
        
        template = self.hazard_templates.get(hazard_type, {})
        properties = template.copy()
        
        if custom_properties:
            properties.update(custom_properties)
        
        hazard = EnvironmentalHazard(
            name=properties.get("name", f"Unknown Hazard ({hazard_type})"),
            description=properties.get("description", f"A {hazard_type} hazard"),
            affected_positions=positions,
            hazard_type=properties.get("hazard_type", hazard_type),
            damage_per_turn=properties.get("damage_per_turn", []),
            save_dc=properties.get("save_dc"),
            save_ability=properties.get("save_ability"),
            triggers_on=properties.get("triggers_on", ["entry"]),
            duration_rounds=properties.get("duration_rounds", -1),
            recharges=properties.get("recharges", True),
            recharge_time=properties.get("recharge_time", 1),
            visible=properties.get("visible", True),
            detectable=properties.get("detectable", True),
            detection_dc=properties.get("detection_dc", 15),
            disarmable=properties.get("disarmable", False),
            disarm_dc=properties.get("disarm_dc", 20),
            active=True,
            triggered_this_round=False
        )
        
        return hazard
    
    def create_interactive_object(
        self,
        object_type: str,
        position: Position,
        battlefield: BattlefieldSchema,
        custom_properties: Optional[Dict] = None
    ) -> InteractiveObject:
        """Create an interactive object."""
        
        template = self.object_templates.get(object_type, {})
        properties = template.copy()
        
        if custom_properties:
            properties.update(custom_properties)
        
        from ..models.base import CoverType
        cover_map = {
            "none": CoverType.NONE,
            "half": CoverType.HALF,
            "three_quarters": CoverType.THREE_QUARTERS,
            "total": CoverType.TOTAL
        }
        
        obj = InteractiveObject(
            name=properties.get("name", f"Unknown Object ({object_type})"),
            description=properties.get("description", f"A {object_type} object"),
            position=position,
            size=properties.get("size", (1, 1)),
            blocks_movement=properties.get("blocks_movement", False),
            blocks_vision=properties.get("blocks_vision", False),
            provides_cover=cover_map.get(properties.get("provides_cover", "none"), CoverType.NONE),
            interaction_types=properties.get("interaction_types", []),
            action_required=properties.get("action_required", "action"),
            range_required=properties.get("range_required", 5),
            armor_class=properties.get("armor_class", 15),
            hit_points=properties.get("hit_points", 10),
            max_hit_points=properties.get("hit_points", 10),
            damage_threshold=properties.get("damage_threshold", 0),
            damage_immunities=properties.get("damage_immunities", []),
            damage_resistances=properties.get("damage_resistances", []),
            effects=properties.get("effects", []),
            uses_remaining=properties.get("uses_remaining", -1),
            destroyed=False,
            activated=False
        )
        
        return obj
    
    def process_environmental_triggers(
        self,
        encounter: CombatEncounter,
        combatant: CombatantSchema,
        trigger_type: str,
        old_position: Optional[Position] = None
    ) -> List[HazardActivation]:
        """Process environmental hazard triggers."""
        
        activations = []
        
        if not combatant.position:
            return activations
        
        for hazard in encounter.battlefield.hazards:
            if not hazard.active or trigger_type not in hazard.triggers_on:
                continue
            
            # Check if combatant is in hazard area
            is_in_hazard = combatant.position in hazard.affected_positions
            was_in_hazard = old_position and old_position in hazard.affected_positions if old_position else False
            
            should_trigger = False
            
            if trigger_type == "entry" and is_in_hazard and not was_in_hazard:
                should_trigger = True
            elif trigger_type in ["start_turn", "end_turn"] and is_in_hazard:
                should_trigger = True
            
            if should_trigger and not hazard.triggered_this_round:
                activation = self._trigger_hazard(encounter, hazard, combatant, trigger_type)
                if activation:
                    activations.append(activation)
                    hazard.triggered_this_round = True
        
        return activations
    
    def interact_with_object(
        self,
        encounter: CombatEncounter,
        combatant: CombatantSchema,
        object_id: str,
        interaction_type: str
    ) -> ObjectInteraction:
        """Handle interaction with an interactive object."""
        
        # Find the object
        obj = None
        for interactive_obj in encounter.battlefield.interactive_objects:
            if interactive_obj.id == object_id:
                obj = interactive_obj
                break
        
        if not obj:
            return ObjectInteraction(
                object_id=object_id,
                interacted_by=combatant.id,
                interaction_type=interaction_type,
                success=False,
                effects=["Object not found"],
                damage_to_object=0,
                changes_to_battlefield=[],
                timestamp=datetime.utcnow()
            )
        
        # Check range
        if combatant.position:
            distance = combatant.position.distance_to(obj.position)
            if distance * encounter.battlefield.square_size_feet > obj.range_required:
                return ObjectInteraction(
                    object_id=object_id,
                    interacted_by=combatant.id,
                    interaction_type=interaction_type,
                    success=False,
                    effects=["Out of range"],
                    damage_to_object=0,
                    changes_to_battlefield=[],
                    timestamp=datetime.utcnow()
                )
        
        # Check if interaction type is valid
        if interaction_type not in obj.interaction_types:
            return ObjectInteraction(
                object_id=object_id,
                interacted_by=combatant.id,
                interaction_type=interaction_type,
                success=False,
                effects=["Invalid interaction type"],
                damage_to_object=0,
                changes_to_battlefield=[],
                timestamp=datetime.utcnow()
            )
        
        # Check uses remaining
        if obj.uses_remaining == 0:
            return ObjectInteraction(
                object_id=object_id,
                interacted_by=combatant.id,
                interaction_type=interaction_type,
                success=False,
                effects=["No uses remaining"],
                damage_to_object=0,
                changes_to_battlefield=[],
                timestamp=datetime.utcnow()
            )
        
        # Process interaction
        return self._process_object_interaction(encounter, obj, combatant, interaction_type)
    
    def detect_hazards(
        self,
        encounter: CombatEncounter,
        combatant: CombatantSchema,
        search_area: Optional[List[Position]] = None
    ) -> List[str]:
        """Attempt to detect hidden hazards in an area."""
        
        detected_hazards = []
        
        # Default to adjacent positions if no search area specified
        if not search_area and combatant.position:
            search_area = combatant.position.adjacent_positions(include_diagonals=True)
            search_area.append(combatant.position)
        
        if not search_area:
            return detected_hazards
        
        for hazard in encounter.battlefield.hazards:
            if not hazard.detectable or hazard.detection_dc == 0:
                continue
            
            # Check if any hazard positions overlap with search area
            if any(pos in hazard.affected_positions for pos in search_area):
                # Make detection roll
                perception_roll = random.randint(1, 20)
                perception_bonus = combatant.get_ability_modifier("wisdom")  # Assuming Wisdom for perception
                
                if perception_roll + perception_bonus >= hazard.detection_dc:
                    detected_hazards.append(hazard.id)
        
        return detected_hazards
    
    def disarm_hazard(
        self,
        encounter: CombatEncounter,
        combatant: CombatantSchema,
        hazard_id: str
    ) -> Tuple[bool, str]:
        """Attempt to disarm a hazard."""
        
        hazard = None
        for h in encounter.battlefield.hazards:
            if h.id == hazard_id:
                hazard = h
                break
        
        if not hazard:
            return False, "Hazard not found"
        
        if not hazard.disarmable:
            return False, "Hazard cannot be disarmed"
        
        # Check range (must be adjacent)
        if combatant.position:
            in_range = any(combatant.position.distance_to(pos) <= 1 
                          for pos in hazard.affected_positions)
            if not in_range:
                return False, "Too far from hazard"
        
        # Make disarm roll (using dexterity + proficiency)
        disarm_roll = random.randint(1, 20)
        dex_bonus = combatant.get_ability_modifier("dexterity")
        # Assuming thieves' tools proficiency for disarming
        proficiency_bonus = combatant.proficiency_bonus
        
        total_roll = disarm_roll + dex_bonus + proficiency_bonus
        
        if total_roll >= hazard.disarm_dc:
            hazard.active = False
            return True, f"Successfully disarmed {hazard.name}"
        else:
            # Failure might trigger the hazard
            if disarm_roll == 1:  # Critical failure
                # Trigger hazard on the disarmer
                activation = self._trigger_hazard(encounter, hazard, combatant, "disarm_failure")
                return False, f"Critical failure! {hazard.name} triggered during disarm attempt"
            else:
                return False, f"Failed to disarm {hazard.name}"
    
    def update_light_sources(
        self,
        battlefield: BattlefieldSchema,
        encounter: CombatEncounter
    ) -> None:
        """Update light sources and their effects on the battlefield."""
        
        for light_source in battlefield.light_sources:
            if not light_source.active:
                continue
            
            # Reduce fuel if applicable
            if light_source.fuel_duration > 0:
                light_source.remaining_fuel -= 1
                if light_source.remaining_fuel <= 0:
                    light_source.active = False
                    logger.info(f"Light source {light_source.name} ran out of fuel")
            
            # Update light levels on battlefield
            self._update_light_levels(battlefield, light_source)
    
    def _trigger_hazard(
        self,
        encounter: CombatEncounter,
        hazard: EnvironmentalHazard,
        combatant: CombatantSchema,
        trigger_type: str
    ) -> Optional[HazardActivation]:
        """Trigger a hazard and apply its effects."""
        
        damage_dealt = {}
        conditions_applied = {}
        
        # Apply damage
        for damage_dice in hazard.damage_per_turn:
            damage = self._roll_hazard_damage(damage_dice)
            
            # Apply saving throw if applicable
            if hazard.save_dc and hazard.save_ability:
                save_roll = random.randint(1, 20)
                save_bonus = combatant.get_save_bonus(hazard.save_ability)
                if save_roll + save_bonus >= hazard.save_dc:
                    damage = damage // 2
            
            # Apply damage based on hazard type
            damage_type_map = {
                "fire": DamageType.FIRE,
                "acid": DamageType.ACID,
                "poison": DamageType.POISON,
                "piercing": DamageType.PIERCING,
                "lightning": DamageType.LIGHTNING
            }
            
            damage_type = damage_type_map.get(hazard.hazard_type, DamageType.FIRE)
            actual_damage = combatant.take_damage(damage, damage_type)
            damage_dealt[combatant.id] = actual_damage
        
        # Apply conditions based on hazard type
        condition_effects = {
            "poison": ["poisoned"],
            "fire": ["burning"],
            "acid": ["corroded"],
            "lightning": ["stunned"]
        }
        
        if hazard.hazard_type in condition_effects:
            from ..models.base import Condition
            for condition_name in condition_effects[hazard.hazard_type]:
                condition = Condition(
                    name=condition_name,
                    duration_rounds=3  # Default duration
                )
                combatant.add_condition(condition)
                
                if combatant.id not in conditions_applied:
                    conditions_applied[combatant.id] = []
                conditions_applied[combatant.id].append(condition_name)
        
        return HazardActivation(
            hazard_id=hazard.id,
            triggered_by=combatant.id,
            trigger_type=trigger_type,
            damage_dealt=damage_dealt,
            conditions_applied=conditions_applied,
            description=f"{combatant.name} triggered {hazard.name}",
            timestamp=datetime.utcnow()
        )
    
    def _process_object_interaction(
        self,
        encounter: CombatEncounter,
        obj: InteractiveObject,
        combatant: CombatantSchema,
        interaction_type: str
    ) -> ObjectInteraction:
        """Process the actual object interaction."""
        
        effects = []
        damage_to_object = 0
        changes_to_battlefield = []
        success = True
        
        if interaction_type == "break":
            # Attack the object
            attack_roll = random.randint(1, 20)
            attack_bonus = combatant.get_ability_modifier("strength") + combatant.proficiency_bonus
            
            if attack_roll + attack_bonus >= obj.armor_class:
                # Hit - roll damage
                if combatant.weapons:
                    weapon = combatant.weapons[0]
                    # Simplified damage calculation
                    damage = random.randint(1, 8) + combatant.get_ability_modifier("strength")
                else:
                    # Unarmed strike
                    damage = 1 + combatant.get_ability_modifier("strength")
                
                damage = max(0, damage)
                
                # Apply damage threshold
                if damage >= obj.damage_threshold:
                    damage_to_object = damage
                    obj.hit_points = max(0, obj.hit_points - damage)
                    
                    if obj.hit_points <= 0:
                        obj.destroyed = True
                        effects.append("Object destroyed")
                        
                        # Apply destruction effects
                        if "structural_collapse" in obj.effects:
                            effects.append("Structure collapsed - area becomes difficult terrain")
                            changes_to_battlefield.append("add_difficult_terrain")
                    else:
                        effects.append(f"Object damaged for {damage} points")
                else:
                    effects.append("Damage below threshold - no effect")
            else:
                success = False
                effects.append("Attack missed")
        
        elif interaction_type == "open":
            if "door" in obj.name.lower():
                if obj.uses_remaining != 0:  # Not locked
                    obj.activated = True
                    obj.blocks_movement = False
                    obj.blocks_vision = False
                    effects.append("Door opened")
                    changes_to_battlefield.append("passage_opened")
                else:
                    success = False
                    effects.append("Door is locked")
            else:
                effects.append(f"{obj.name} opened")
        
        elif interaction_type == "activate":
            if obj.uses_remaining > 0:
                obj.uses_remaining -= 1
                obj.activated = True
                effects.append(f"{obj.name} activated")
                
                # Apply activation effects
                if "triggers_mechanism" in obj.effects:
                    effects.append("Mechanism triggered")
                    changes_to_battlefield.append("mechanism_activated")
                
                if "magical_effect" in obj.effects:
                    effects.append("Magical effect activated")
                    # Could heal or buff the activator
                    heal_amount = random.randint(1, 8)
                    combatant.heal(heal_amount)
                    effects.append(f"Healed {heal_amount} hit points")
            else:
                success = False
                effects.append("No uses remaining")
        
        return ObjectInteraction(
            object_id=obj.id,
            interacted_by=combatant.id,
            interaction_type=interaction_type,
            success=success,
            effects=effects,
            damage_to_object=damage_to_object,
            changes_to_battlefield=changes_to_battlefield,
            timestamp=datetime.utcnow()
        )
    
    def _roll_hazard_damage(self, damage_dice: str) -> int:
        """Roll damage for environmental hazards."""
        
        # Parse dice string like "2d6" or "1d4+2"
        parts = damage_dice.split('+')
        dice_part = parts[0]
        modifier = int(parts[1]) if len(parts) > 1 else 0
        
        if 'd' in dice_part:
            num_dice, die_size = map(int, dice_part.split('d'))
            total = sum(random.randint(1, die_size) for _ in range(num_dice))
            return total + modifier
        else:
            return int(dice_part) + modifier
    
    def _update_light_levels(
        self,
        battlefield: BattlefieldSchema,
        light_source: LightSource
    ) -> None:
        """Update light levels on battlefield based on light source."""
        
        bright_squares = light_source.bright_radius // battlefield.square_size_feet
        dim_squares = light_source.dim_radius // battlefield.square_size_feet
        
        for y in range(battlefield.height):
            for x in range(battlefield.width):
                pos = Position(x=x, y=y)
                distance = light_source.position.distance_to(pos)
                
                cell = battlefield.get_cell(pos)
                if not cell:
                    continue
                
                if distance <= bright_squares:
                    cell.light_level = max(cell.light_level, 1.0)
                elif distance <= dim_squares:
                    cell.light_level = max(cell.light_level, 0.5)