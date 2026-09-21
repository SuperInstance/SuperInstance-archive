"""
Spell effect service for handling area of effect spells and abilities.
"""

import math
import random
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import logging

from ..models.base import Position, DamageType, ActionType
from ..models.battlefield import BattlefieldSchema, AreaOfEffect, AOEShape
from ..models.combatant import CombatantSchema
from ..models.combat import CombatEncounter, CombatAction, SpellResult
from ..config import Config

logger = logging.getLogger(__name__)

@dataclass
class SpellEffectTemplate:
    """Template for spell effects."""
    name: str
    level: int
    school: str
    damage_type: DamageType
    aoe_shape: Optional[AOEShape] = None
    aoe_size: int = 0
    damage_dice: str = ""
    save_dc_base: int = 15
    save_ability: str = "dexterity"
    duration_rounds: int = 0  # 0 = instantaneous
    concentration: bool = False
    ritual: bool = False
    components: List[str] = None
    range_feet: int = 60

    def __post_init__(self):
        if self.components is None:
            self.components = ["V", "S"]

class SpellEffectService:
    """Service for managing spell effects and AOE calculations."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.spell_templates = self._initialize_spell_templates()
    
    def _initialize_spell_templates(self) -> Dict[str, SpellEffectTemplate]:
        """Initialize common spell effect templates."""
        
        templates = {}
        
        # Damage spells
        templates["fireball"] = SpellEffectTemplate(
            name="Fireball",
            level=3,
            school="evocation",
            damage_type=DamageType.FIRE,
            aoe_shape=AOEShape.SPHERE,
            aoe_size=20,  # 20-foot radius
            damage_dice="8d6",
            save_ability="dexterity",
            range_feet=150
        )
        
        templates["lightning_bolt"] = SpellEffectTemplate(
            name="Lightning Bolt",
            level=3,
            school="evocation",
            damage_type=DamageType.LIGHTNING,
            aoe_shape=AOEShape.LINE,
            aoe_size=100,  # 100-foot line, 5-foot width
            damage_dice="8d6",
            save_ability="dexterity"
        )
        
        templates["cone_of_cold"] = SpellEffectTemplate(
            name="Cone of Cold",
            level=5,
            school="evocation",
            damage_type=DamageType.COLD,
            aoe_shape=AOEShape.CONE,
            aoe_size=60,  # 60-foot cone
            damage_dice="8d8",
            save_ability="constitution"
        )
        
        templates["burning_hands"] = SpellEffectTemplate(
            name="Burning Hands",
            level=1,
            school="evocation",
            damage_type=DamageType.FIRE,
            aoe_shape=AOEShape.CONE,
            aoe_size=15,  # 15-foot cone
            damage_dice="3d6",
            save_ability="dexterity",
            range_feet=15
        )
        
        # Control spells
        templates["web"] = SpellEffectTemplate(
            name="Web",
            level=2,
            school="conjuration",
            damage_type=DamageType.NONE,
            aoe_shape=AOEShape.CUBE,
            aoe_size=20,  # 20-foot cube
            damage_dice="",
            save_ability="dexterity",
            duration_rounds=600,  # 10 minutes
            concentration=True,
            range_feet=60
        )
        
        templates["entangle"] = SpellEffectTemplate(
            name="Entangle",
            level=1,
            school="conjuration",
            damage_type=DamageType.NONE,
            aoe_shape=AOEShape.CUBE,
            aoe_size=20,  # 20-foot square
            damage_dice="",
            save_ability="strength",
            duration_rounds=600,  # 10 minutes
            concentration=True,
            range_feet=90
        )
        
        # Healing spells
        templates["mass_cure_wounds"] = SpellEffectTemplate(
            name="Mass Cure Wounds",
            level=5,
            school="evocation",
            damage_type=DamageType.NONE,
            aoe_shape=AOEShape.SPHERE,
            aoe_size=30,  # 30-foot radius
            damage_dice="3d8+5",  # Healing
            save_ability="",
            range_feet=60
        )
        
        return templates
    
    def create_spell_aoe(
        self,
        spell_name: str,
        caster: CombatantSchema,
        origin: Position,
        target_position: Optional[Position] = None,
        spell_level: Optional[int] = None,
        direction: Optional[int] = None
    ) -> Optional[AreaOfEffect]:
        """Create an AOE effect for a spell."""
        
        template = self.spell_templates.get(spell_name.lower())
        if not template:
            logger.warning(f"Unknown spell: {spell_name}")
            return None
        
        # Use provided spell level or template level
        effective_level = spell_level if spell_level is not None else template.level
        
        # Create AOE effect
        aoe = AreaOfEffect(
            name=f"{template.name} (Level {effective_level})",
            shape=template.aoe_shape,
            origin=origin,
            size=template.aoe_size
        )
        
        # Set target for line/cone spells
        if template.aoe_shape in [AOEShape.LINE, AOEShape.CONE]:
            if target_position:
                aoe.target_position = target_position
            elif direction is not None:
                aoe.direction = direction
            else:
                # Default direction (north)
                aoe.direction = 0
        
        # Set width for line spells
        if template.aoe_shape == AOEShape.LINE:
            aoe.width = 5  # Standard 5-foot width
        
        # Set visual properties based on damage type
        color_map = {
            DamageType.FIRE: "red",
            DamageType.COLD: "lightblue", 
            DamageType.LIGHTNING: "yellow",
            DamageType.ACID: "green",
            DamageType.POISON: "purple",
            DamageType.NECROTIC: "darkpurple",
            DamageType.RADIANT: "gold",
            DamageType.FORCE: "blue",
            DamageType.PSYCHIC: "pink",
            DamageType.THUNDER: "cyan"
        }
        
        aoe.color = color_map.get(template.damage_type, "red")
        aoe.opacity = 0.6
        aoe.border_color = "darkred" if template.damage_type == DamageType.FIRE else "black"
        
        return aoe
    
    def resolve_spell_effect(
        self,
        encounter: CombatEncounter,
        spell_name: str,
        caster: CombatantSchema,
        aoe: AreaOfEffect,
        spell_level: Optional[int] = None,
        spell_attack_bonus: int = 0,
        spell_save_dc: int = 15
    ) -> SpellResult:
        """Resolve the effects of a spell."""
        
        template = self.spell_templates.get(spell_name.lower())
        if not template:
            return SpellResult(
                caster_id=caster.id,
                spell_name=spell_name,
                spell_level=spell_level or 1,
                spell_success=False,
                fizzled=True
            )
        
        effective_level = spell_level if spell_level is not None else template.level
        
        # Find affected creatures
        affected_creatures = self._get_creatures_in_aoe(encounter, aoe)
        
        result = SpellResult(
            caster_id=caster.id,
            spell_name=template.name,
            spell_level=effective_level,
            target_positions=aoe.affected_positions,
            area_of_effect=aoe,
            save_dc=spell_save_dc if template.save_ability else None
        )
        
        # Process each affected creature
        for creature in affected_creatures:
            result.target_ids.append(creature.id)
            
            if template.damage_dice:
                if template.save_ability:
                    # Saving throw spell
                    save_roll = random.randint(1, 20)
                    save_bonus = creature.get_save_bonus(template.save_ability)
                    save_total = save_roll + save_bonus
                    save_success = save_total >= spell_save_dc
                    
                    result.save_results[creature.id] = (save_total, save_success)
                    
                    # Calculate damage
                    damage = self._roll_damage(template.damage_dice, effective_level)
                    if save_success and template.school == "evocation":
                        damage = damage // 2  # Half damage on save for evocation spells
                    
                    if damage > 0:
                        actual_damage = creature.take_damage(damage, template.damage_type)
                        result.damage_dealt[creature.id] = actual_damage
                
                else:
                    # Spell attack or automatic effect
                    if template.school == "evocation" and template.damage_type != DamageType.NONE:
                        damage = self._roll_damage(template.damage_dice, effective_level)
                        actual_damage = creature.take_damage(damage, template.damage_type)
                        result.damage_dealt[creature.id] = actual_damage
                    
                    elif template.name == "Mass Cure Wounds":
                        # Healing spell
                        healing = self._roll_healing(template.damage_dice, effective_level)
                        actual_healing = creature.heal(healing)
                        result.healing_done[creature.id] = actual_healing
        
        # Apply ongoing effects for duration spells
        if template.duration_rounds > 0:
            self._apply_duration_effect(encounter, template, aoe, affected_creatures)
        
        # Use spell slot
        if caster.spell_slots.get(effective_level, 0) > 0:
            caster.spell_slots[effective_level] -= 1
            result.remaining_slots = caster.spell_slots.copy()
        
        result.spell_success = True
        return result
    
    def calculate_spell_damage(
        self,
        spell_name: str,
        caster_level: int,
        spell_level: int,
        is_critical: bool = False
    ) -> int:
        """Calculate damage for a spell."""
        
        template = self.spell_templates.get(spell_name.lower())
        if not template or not template.damage_dice:
            return 0
        
        damage = self._roll_damage(template.damage_dice, spell_level)
        
        if is_critical:
            # Critical hits double damage dice
            damage += self._roll_damage(template.damage_dice, spell_level)
        
        return damage
    
    def get_spell_targets_in_aoe(
        self,
        encounter: CombatEncounter,
        aoe: AreaOfEffect,
        caster: CombatantSchema,
        affects_allies: bool = True,
        affects_enemies: bool = True,
        affects_self: bool = False
    ) -> List[CombatantSchema]:
        """Get valid targets for a spell effect."""
        
        targets = []
        affected_creatures = self._get_creatures_in_aoe(encounter, aoe)
        
        for creature in affected_creatures:
            # Skip self if not allowed
            if creature.id == caster.id and not affects_self:
                continue
            
            # Check ally/enemy status
            is_ally = creature.creature_type == caster.creature_type
            
            if (is_ally and affects_allies) or (not is_ally and affects_enemies):
                targets.append(creature)
        
        return targets
    
    def preview_spell_effect(
        self,
        encounter: CombatEncounter,
        spell_name: str,
        caster: CombatantSchema,
        origin: Position,
        target_position: Optional[Position] = None,
        spell_level: Optional[int] = None
    ) -> Dict:
        """Preview the effects of a spell without casting it."""
        
        template = self.spell_templates.get(spell_name.lower())
        if not template:
            return {"error": f"Unknown spell: {spell_name}"}
        
        # Create temporary AOE
        aoe = self.create_spell_aoe(
            spell_name, caster, origin, target_position, spell_level
        )
        if not aoe:
            return {"error": f"Could not create AOE for {spell_name}"}
        
        # Calculate affected positions
        affected_positions = self._calculate_aoe_positions(encounter.battlefield, aoe)
        aoe.affected_positions = affected_positions
        
        # Get affected creatures
        affected_creatures = self._get_creatures_in_aoe(encounter, aoe)
        
        # Estimate damage/healing
        effective_level = spell_level if spell_level is not None else template.level
        estimated_damage = 0
        
        if template.damage_dice:
            estimated_damage = self._estimate_damage(template.damage_dice, effective_level)
        
        return {
            "spell_name": template.name,
            "level": effective_level,
            "aoe_shape": aoe.shape.value,
            "aoe_size": aoe.size,
            "affected_positions": len(affected_positions),
            "affected_creatures": len(affected_creatures),
            "creature_ids": [c.id for c in affected_creatures],
            "estimated_damage": estimated_damage,
            "damage_type": template.damage_type.value,
            "save_required": bool(template.save_ability),
            "save_ability": template.save_ability,
            "duration": template.duration_rounds,
            "concentration": template.concentration
        }
    
    def _get_creatures_in_aoe(
        self,
        encounter: CombatEncounter,
        aoe: AreaOfEffect
    ) -> List[CombatantSchema]:
        """Get all creatures within an AOE."""
        
        if not aoe.affected_positions:
            aoe.affected_positions = self._calculate_aoe_positions(encounter.battlefield, aoe)
        
        affected_creatures = []
        for creature in encounter.combatants:
            if creature.position and creature.is_alive():
                if creature.position in aoe.affected_positions:
                    affected_creatures.append(creature)
        
        return affected_creatures
    
    def _calculate_aoe_positions(
        self,
        battlefield: BattlefieldSchema,
        aoe: AreaOfEffect
    ) -> List[Position]:
        """Calculate positions affected by AOE."""
        
        positions = []
        
        if aoe.shape == AOEShape.SPHERE:
            radius_squares = aoe.size // battlefield.square_size_feet
            for y in range(battlefield.height):
                for x in range(battlefield.width):
                    pos = Position(x=x, y=y)
                    distance = aoe.origin.distance_to(pos)
                    if distance <= radius_squares:
                        positions.append(pos)
        
        elif aoe.shape == AOEShape.CUBE:
            half_size = (aoe.size // battlefield.square_size_feet) // 2
            for y in range(max(0, aoe.origin.y - half_size),
                          min(battlefield.height, aoe.origin.y + half_size + 1)):
                for x in range(max(0, aoe.origin.x - half_size),
                              min(battlefield.width, aoe.origin.x + half_size + 1)):
                    positions.append(Position(x=x, y=y))
        
        elif aoe.shape == AOEShape.LINE:
            if aoe.target_position:
                line_positions = self._get_line_positions(aoe.origin, aoe.target_position)
                positions = line_positions
        
        elif aoe.shape == AOEShape.CONE:
            radius_squares = aoe.size // battlefield.square_size_feet
            direction_rad = (aoe.direction or 0) * math.pi / 180
            cone_angle_rad = math.pi / 2  # 90 degree cone
            
            for y in range(max(0, aoe.origin.y - radius_squares),
                          min(battlefield.height, aoe.origin.y + radius_squares + 1)):
                for x in range(max(0, aoe.origin.x - radius_squares),
                              min(battlefield.width, aoe.origin.x + radius_squares + 1)):
                    pos = Position(x=x, y=y)
                    distance = aoe.origin.distance_to(pos)
                    
                    if distance <= radius_squares:
                        angle_to_pos = math.atan2(pos.y - aoe.origin.y, pos.x - aoe.origin.x)
                        angle_diff = abs(angle_to_pos - direction_rad)
                        
                        if angle_diff > math.pi:
                            angle_diff = 2 * math.pi - angle_diff
                        
                        if angle_diff <= cone_angle_rad / 2:
                            positions.append(pos)
        
        return positions
    
    def _get_line_positions(self, start: Position, end: Position) -> List[Position]:
        """Get positions along a line."""
        positions = []
        dx = abs(end.x - start.x)
        dy = abs(end.y - start.y)
        
        x, y = start.x, start.y
        x_inc = 1 if start.x < end.x else -1
        y_inc = 1 if start.y < end.y else -1
        
        error = dx - dy
        
        while True:
            positions.append(Position(x=x, y=y))
            if x == end.x and y == end.y:
                break
            
            error2 = 2 * error
            if error2 > -dy:
                error -= dy
                x += x_inc
            if error2 < dx:
                error += dx
                y += y_inc
        
        return positions
    
    def _roll_damage(self, damage_dice: str, spell_level: int) -> int:
        """Roll damage dice for a spell."""
        # Parse damage dice string like "8d6" or "3d8+5"
        parts = damage_dice.split('+')
        dice_part = parts[0]
        bonus = int(parts[1]) if len(parts) > 1 else 0
        
        if 'd' in dice_part:
            num_dice, die_size = map(int, dice_part.split('d'))
            total = sum(random.randint(1, die_size) for _ in range(num_dice))
            return total + bonus
        else:
            return int(dice_part) + bonus
    
    def _roll_healing(self, healing_dice: str, spell_level: int) -> int:
        """Roll healing for a spell."""
        return self._roll_damage(healing_dice, spell_level)
    
    def _estimate_damage(self, damage_dice: str, spell_level: int) -> int:
        """Estimate average damage for a spell."""
        parts = damage_dice.split('+')
        dice_part = parts[0]
        bonus = int(parts[1]) if len(parts) > 1 else 0
        
        if 'd' in dice_part:
            num_dice, die_size = map(int, dice_part.split('d'))
            average_per_die = (die_size + 1) / 2
            return int(num_dice * average_per_die) + bonus
        else:
            return int(dice_part) + bonus
    
    def _apply_duration_effect(
        self,
        encounter: CombatEncounter,
        template: SpellEffectTemplate,
        aoe: AreaOfEffect,
        affected_creatures: List[CombatantSchema]
    ) -> None:
        """Apply ongoing effects for duration spells."""
        
        # This would handle effects like Web, Entangle, etc.
        # For now, just log the effect
        logger.info(f"Applied {template.name} effect to {len(affected_creatures)} creatures for {template.duration_rounds} rounds")