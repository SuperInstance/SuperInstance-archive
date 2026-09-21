"""
Spell and ability management service with cooldowns, slots, and resources.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from models.spells import (
    Spell, Ability, CharacterResource, CharacterSpellAbility, SpellCasting, 
    AbilityCooldown, SpellSchema, AbilitySchema, CharacterResourceSchema,
    SpellCastingSchema, AbilityCooldownSchema,
    CastSpellRequest, UseAbilityRequest, RestoreResourcesRequest,
    SpellCastingResponse, AbilityUsageResponse, ResourceType, RechargeType
)
from models.character import Character
from .dice_service import DiceService, DiceRollRequest


class SpellService:
    """Service for managing spells and abilities."""
    
    def __init__(self, db: Session, dice_service: Optional[DiceService] = None):
        self.db = db
        self.dice_service = dice_service or DiceService()
    
    def cast_spell(self, request: CastSpellRequest) -> SpellCastingResponse:
        """Cast a spell for a character."""
        try:
            # Get character and spell
            character = self._get_character(request.character_id)
            spell = self._get_spell(request.spell_name)
            
            if not spell:
                return SpellCastingResponse(
                    success=False,
                    error_message=f"Spell '{request.spell_name}' not found"
                )
            
            # Determine actual casting level
            cast_level = request.upcast_level or max(spell.level, request.spell_level)
            
            # Check if character knows/has prepared the spell
            character_spell = self._get_character_spell(request.character_id, spell.name)
            if not character_spell and spell.level > 0:  # Cantrips don't need to be known
                return SpellCastingResponse(
                    success=False,
                    error_message=f"Character does not know spell '{spell.name}'"
                )
            
            if character_spell and not character_spell.prepared and not character_spell.always_prepared:
                return SpellCastingResponse(
                    success=False,
                    error_message=f"Spell '{spell.name}' is not prepared"
                )
            
            # Check for spell slot availability (skip for cantrips)
            resources_consumed = {}
            if spell.level > 0 and request.use_slot:
                slot_consumed = self._consume_spell_slot(request.character_id, cast_level)
                if not slot_consumed:
                    return SpellCastingResponse(
                        success=False,
                        error_message=f"No spell slots available for level {cast_level}"
                    )
                resources_consumed[f"spell_slot_level_{cast_level}"] = 1
            
            # Handle concentration
            concentration_ended = None
            concentration_started = False
            
            if spell.concentration:
                # End any existing concentration
                concentration_ended = self._end_concentration(request.character_id)
                
                # Start new concentration
                self._start_concentration(request.character_id, spell.name)
                concentration_started = True
            
            # Apply metamagic costs if any
            for metamagic in request.metamagic:
                cost = self._get_metamagic_cost(metamagic)
                if cost > 0:
                    sorcery_consumed = self._consume_resource(
                        request.character_id, 
                        ResourceType.SORCERY_POINT, 
                        cost
                    )
                    if not sorcery_consumed:
                        return SpellCastingResponse(
                            success=False,
                            error_message=f"Not enough sorcery points for {metamagic}"
                        )
                    resources_consumed[ResourceType.SORCERY_POINT] = resources_consumed.get(ResourceType.SORCERY_POINT, 0) + cost
            
            # Calculate spell effects
            effects = self._calculate_spell_effects(spell, cast_level, request.target_ids)
            
            # Update last used timestamp for prepared spell
            if character_spell:
                character_spell.last_used = datetime.utcnow()
            
            self.db.commit()
            
            return SpellCastingResponse(
                success=True,
                spell=SpellSchema.from_orm(spell),
                spell_level_used=cast_level,
                resources_consumed=resources_consumed,
                concentration_started=concentration_started,
                concentration_ended=concentration_ended,
                effects=effects
            )
            
        except Exception as e:
            self.db.rollback()
            return SpellCastingResponse(
                success=False,
                error_message=f"Failed to cast spell: {str(e)}"
            )
    
    def use_ability(self, request: UseAbilityRequest) -> AbilityUsageResponse:
        """Use a character ability."""
        try:
            # Get character and ability
            character = self._get_character(request.character_id)
            character_ability = self._get_character_ability(request.ability_id)
            
            if not character_ability:
                return AbilityUsageResponse(
                    success=False,
                    error_message=f"Ability '{request.ability_id}' not found"
                )
            
            # Check if ability is on cooldown
            if self._is_ability_on_cooldown(request.ability_id):
                cooldown = self._get_ability_cooldown(request.ability_id)
                return AbilityUsageResponse(
                    success=False,
                    error_message=f"Ability on cooldown for {cooldown.cooldown_remaining} more {cooldown.cooldown_type}"
                )
            
            # Check usage limits
            if character_ability.uses_remaining is not None and character_ability.uses_remaining <= 0:
                return AbilityUsageResponse(
                    success=False,
                    error_message=f"No uses remaining for '{character_ability.name}'"
                )
            
            # Get ability details
            ability = None
            if character_ability.ability_id:
                ability = self.db.query(Ability).filter(
                    Ability.id == character_ability.ability_id
                ).first()
            
            # Check resource costs
            resource_costs = {}
            if ability and ability.resource_cost:
                resource_costs = ability.resource_cost.copy()
            
            # Apply overrides
            if request.resource_override:
                resource_costs.update(request.resource_override)
            
            # Consume resources
            resources_consumed = {}
            for resource_type, amount in resource_costs.items():
                if not self._consume_resource(request.character_id, resource_type, amount):
                    return AbilityUsageResponse(
                        success=False,
                        error_message=f"Not enough {resource_type} (need {amount})"
                    )
                resources_consumed[resource_type] = amount
            
            # Consume usage if limited
            if character_ability.uses_remaining is not None:
                character_ability.uses_remaining -= 1
                resources_consumed["uses"] = 1
            
            # Apply cooldown if needed
            cooldown_applied = None
            if ability and ability.recharge_type != RechargeType.NONE:
                cooldown_applied = self._apply_cooldown(request.ability_id, ability.recharge_type)
            
            # Update last used
            character_ability.last_used = datetime.utcnow()
            
            # Calculate effects
            effects = []
            if ability:
                effects = self._calculate_ability_effects(ability, request.target_ids, request.modifications)
            
            self.db.commit()
            
            return AbilityUsageResponse(
                success=True,
                ability=AbilitySchema.from_orm(ability) if ability else None,
                resources_consumed=resources_consumed,
                cooldown_applied=cooldown_applied,
                effects=effects
            )
            
        except Exception as e:
            self.db.rollback()
            return AbilityUsageResponse(
                success=False,
                error_message=f"Failed to use ability: {str(e)}"
            )
    
    def restore_resources(self, request: RestoreResourcesRequest) -> Dict[str, Any]:
        """Restore character resources after a rest."""
        try:
            character = self._get_character(request.character_id)
            
            # Get all character resources
            resources = self.db.query(CharacterResource).filter(
                CharacterResource.character_id == request.character_id
            ).all()
            
            # Filter resources to restore
            if request.resources_to_restore:
                resources = [r for r in resources if r.resource_type in request.resources_to_restore]
            
            restored = {}
            
            for resource in resources:
                if self._should_restore_resource(resource, request.rest_type):
                    old_current = resource.current
                    resource.current = resource.maximum
                    resource.last_recharged = datetime.utcnow()
                    
                    restored[resource.resource_type] = {
                        "level": resource.resource_level,
                        "restored": resource.current - old_current,
                        "new_total": resource.current
                    }
            
            # Restore ability uses
            character_abilities = self.db.query(CharacterSpellAbility).filter(
                CharacterSpellAbility.character_id == request.character_id
            ).all()
            
            abilities_restored = []
            for char_ability in character_abilities:
                if self._should_restore_ability(char_ability, request.rest_type):
                    # Get the base ability to check uses_per_recharge
                    if char_ability.ability_id:
                        base_ability = self.db.query(Ability).filter(
                            Ability.id == char_ability.ability_id
                        ).first()
                        
                        if base_ability and base_ability.uses_per_recharge:
                            char_ability.uses_remaining = base_ability.uses_per_recharge
                            abilities_restored.append({
                                "name": char_ability.name,
                                "uses_restored": base_ability.uses_per_recharge
                            })
            
            # Clear appropriate cooldowns
            cooldowns_cleared = self._clear_cooldowns(request.character_id, request.rest_type)
            
            self.db.commit()
            
            return {
                "success": True,
                "rest_type": request.rest_type,
                "resources_restored": restored,
                "abilities_restored": abilities_restored,
                "cooldowns_cleared": cooldowns_cleared
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "error_message": f"Failed to restore resources: {str(e)}"
            }
    
    def get_character_spellcasting(self, character_id: str) -> List[SpellCastingSchema]:
        """Get all spellcasting information for a character."""
        spellcasting_entries = self.db.query(SpellCasting).filter(
            SpellCasting.character_id == character_id
        ).all()
        
        return [SpellCastingSchema.from_orm(entry) for entry in spellcasting_entries]
    
    def get_character_resources(self, character_id: str) -> List[CharacterResourceSchema]:
        """Get all resources for a character."""
        resources = self.db.query(CharacterResource).filter(
            CharacterResource.character_id == character_id
        ).order_by(CharacterResource.resource_type, CharacterResource.resource_level).all()
        
        return [CharacterResourceSchema.from_orm(resource) for resource in resources]
    
    def get_character_abilities(self, character_id: str) -> List[Dict[str, Any]]:
        """Get all abilities for a character."""
        abilities = self.db.query(CharacterSpellAbility).filter(
            CharacterSpellAbility.character_id == character_id
        ).order_by(CharacterSpellAbility.ability_type, CharacterSpellAbility.name).all()
        
        return [dict(ability) for ability in abilities]
    
    def get_character_spells(self, character_id: str, prepared_only: bool = False) -> List[Dict[str, Any]]:
        """Get all spells for a character with full details."""
        query = self.db.query(CharacterSpellAbility).filter(
            CharacterSpellAbility.character_id == character_id,
            CharacterSpellAbility.ability_type.in_(["spell", "cantrip"])
        )
        
        if prepared_only:
            query = query.filter(
                (CharacterSpellAbility.prepared == True) | (CharacterSpellAbility.always_prepared == True)
            )
        
        character_spells = query.order_by(CharacterSpellAbility.name).all()
        
        result = []
        for char_spell in character_spells:
            # Try to get full spell details
            spell = self.db.query(Spell).filter(Spell.name == char_spell.name).first()
            
            spell_data = {
                "character_ability": dict(char_spell),
                "spell_details": SpellSchema.from_orm(spell) if spell else None,
                "prepared": char_spell.prepared or char_spell.always_prepared,
                "uses_remaining": char_spell.uses_remaining,
                "last_used": char_spell.last_used
            }
            
            result.append(spell_data)
        
        return result
    
    def update_spell_preparation(self, character_id: str, spell_changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update spell preparation for a character."""
        try:
            changes_made = []
            
            for change in spell_changes:
                spell_name = change.get("spell_name")
                prepare = change.get("prepare", True)
                
                character_spell = self.db.query(CharacterSpellAbility).filter(
                    CharacterSpellAbility.character_id == character_id,
                    CharacterSpellAbility.name == spell_name,
                    CharacterSpellAbility.ability_type.in_(["spell", "cantrip"])
                ).first()
                
                if character_spell and not character_spell.always_prepared:
                    old_prepared = character_spell.prepared
                    character_spell.prepared = prepare
                    
                    if old_prepared != prepare:
                        changes_made.append({
                            "spell_name": spell_name,
                            "action": "prepared" if prepare else "unprepared"
                        })
            
            self.db.commit()
            
            return {
                "success": True,
                "changes_made": changes_made
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "error_message": f"Failed to update spell preparation: {str(e)}"
            }
    
    def _get_character(self, character_id: str) -> Character:
        """Get character by ID or raise exception."""
        character = self.db.query(Character).filter(Character.id == character_id).first()
        if not character:
            raise ValueError(f"Character {character_id} not found")
        return character
    
    def _get_spell(self, spell_name: str) -> Optional[Spell]:
        """Get spell by name."""
        return self.db.query(Spell).filter(Spell.name == spell_name).first()
    
    def _get_character_spell(self, character_id: str, spell_name: str) -> Optional[CharacterSpellAbility]:
        """Get character's spell ability."""
        return self.db.query(CharacterSpellAbility).filter(
            CharacterSpellAbility.character_id == character_id,
            CharacterSpellAbility.name == spell_name,
            CharacterSpellAbility.ability_type.in_(["spell", "cantrip"])
        ).first()
    
    def _get_character_ability(self, ability_id: str) -> Optional[CharacterSpellAbility]:
        """Get character ability by ID."""
        return self.db.query(CharacterSpellAbility).filter(
            CharacterSpellAbility.id == ability_id
        ).first()
    
    def _consume_spell_slot(self, character_id: str, level: int) -> bool:
        """Consume a spell slot of the given level or higher."""
        # Look for available spell slots at this level or higher
        for slot_level in range(level, 10):
            resource = self.db.query(CharacterResource).filter(
                CharacterResource.character_id == character_id,
                CharacterResource.resource_type == ResourceType.SPELL_SLOT,
                CharacterResource.resource_level == slot_level,
                CharacterResource.current > 0
            ).first()
            
            if resource:
                resource.current -= 1
                return True
        
        return False
    
    def _consume_resource(self, character_id: str, resource_type: str, amount: int) -> bool:
        """Consume a specified amount of a resource."""
        resource = self.db.query(CharacterResource).filter(
            CharacterResource.character_id == character_id,
            CharacterResource.resource_type == resource_type,
            CharacterResource.current >= amount
        ).first()
        
        if resource:
            resource.current -= amount
            return True
        
        return False
    
    def _start_concentration(self, character_id: str, spell_name: str) -> None:
        """Start concentration on a spell."""
        # This would typically update a concentration tracking table
        # For now, we'll add it to character metadata
        character = self._get_character(character_id)
        if not hasattr(character, 'system_data'):
            character.system_data = {}
        character.system_data["concentrating_on"] = spell_name
        character.system_data["concentration_started"] = datetime.utcnow().isoformat()
    
    def _end_concentration(self, character_id: str) -> Optional[str]:
        """End concentration and return the spell that was being concentrated on."""
        character = self._get_character(character_id)
        
        if not hasattr(character, 'system_data') or not character.system_data:
            return None
        
        concentrating_on = character.system_data.get("concentrating_on")
        
        if concentrating_on:
            character.system_data.pop("concentrating_on", None)
            character.system_data.pop("concentration_started", None)
            return concentrating_on
        
        return None
    
    def _get_metamagic_cost(self, metamagic: str) -> int:
        """Get the sorcery point cost for metamagic options."""
        metamagic_costs = {
            "careful": 1,
            "distant": 1,
            "empowered": 1,
            "extended": 1,
            "heightened": 3,
            "quickened": 2,
            "subtle": 1,
            "twinned": 1  # Base cost, may vary by spell level
        }
        return metamagic_costs.get(metamagic.lower(), 0)
    
    def _is_ability_on_cooldown(self, ability_id: str) -> bool:
        """Check if an ability is on cooldown."""
        cooldown = self.db.query(AbilityCooldown).filter(
            AbilityCooldown.character_ability_id == ability_id,
            AbilityCooldown.cooldown_remaining > 0
        ).first()
        
        if cooldown and cooldown.expires_at and cooldown.expires_at <= datetime.utcnow():
            # Cooldown has expired, remove it
            self.db.delete(cooldown)
            return False
        
        return cooldown is not None
    
    def _get_ability_cooldown(self, ability_id: str) -> Optional[AbilityCooldown]:
        """Get ability cooldown information."""
        return self.db.query(AbilityCooldown).filter(
            AbilityCooldown.character_ability_id == ability_id
        ).first()
    
    def _apply_cooldown(self, ability_id: str, recharge_type: str) -> Optional[AbilityCooldownSchema]:
        """Apply cooldown to an ability."""
        # Remove existing cooldown
        self.db.query(AbilityCooldown).filter(
            AbilityCooldown.character_ability_id == ability_id
        ).delete()
        
        # Determine cooldown duration
        cooldown_mapping = {
            RechargeType.ROUND: ("rounds", 1),
            RechargeType.TURN: ("turns", 1),
            RechargeType.MINUTE: ("minutes", 1),
            RechargeType.HOUR: ("hours", 1),
            RechargeType.DAY: ("days", 1),
            RechargeType.SHORT_REST: ("short_rest", 1),
            RechargeType.LONG_REST: ("long_rest", 1)
        }
        
        if recharge_type not in cooldown_mapping:
            return None
        
        cooldown_type, duration = cooldown_mapping[recharge_type]
        
        # Calculate expiration time for time-based cooldowns
        expires_at = None
        if cooldown_type in ["rounds", "minutes", "hours", "days"]:
            time_multiplier = {
                "rounds": 6,  # Assuming 6 seconds per round
                "minutes": 60,
                "hours": 3600,
                "days": 86400
            }
            expires_at = datetime.utcnow() + timedelta(seconds=duration * time_multiplier[cooldown_type])
        
        cooldown = AbilityCooldown(
            character_ability_id=ability_id,
            cooldown_type=cooldown_type,
            cooldown_remaining=duration,
            expires_at=expires_at,
            triggered_by="ability_use",
            triggered_at=datetime.utcnow()
        )
        
        self.db.add(cooldown)
        self.db.flush()
        
        return AbilityCooldownSchema.from_orm(cooldown)
    
    def _should_restore_resource(self, resource: CharacterResource, rest_type: str) -> bool:
        """Determine if a resource should be restored by this rest type."""
        if resource.recharge_type == RechargeType.SHORT_REST:
            return True  # Both short and long rests restore short rest resources
        elif resource.recharge_type == RechargeType.LONG_REST:
            return rest_type == "long"
        elif resource.recharge_type == RechargeType.DAWN:
            return rest_type == "long"  # Assuming long rest includes dawn
        
        return False
    
    def _should_restore_ability(self, character_ability: CharacterSpellAbility, rest_type: str) -> bool:
        """Determine if an ability should be restored by this rest type."""
        # This would need to check the base ability's recharge type
        return character_ability.recharge_type in [RechargeType.SHORT_REST] or (
            rest_type == "long" and character_ability.recharge_type == RechargeType.LONG_REST
        )
    
    def _clear_cooldowns(self, character_id: str, rest_type: str) -> List[str]:
        """Clear cooldowns based on rest type."""
        cooldown_types_to_clear = []
        
        if rest_type == "short":
            cooldown_types_to_clear = ["short_rest"]
        elif rest_type == "long":
            cooldown_types_to_clear = ["short_rest", "long_rest"]
        
        # Get character abilities
        character_abilities = self.db.query(CharacterSpellAbility).filter(
            CharacterSpellAbility.character_id == character_id
        ).all()
        
        ability_ids = [ab.id for ab in character_abilities]
        
        # Find cooldowns to clear
        cooldowns_to_clear = self.db.query(AbilityCooldown).filter(
            AbilityCooldown.character_ability_id.in_(ability_ids),
            AbilityCooldown.cooldown_type.in_(cooldown_types_to_clear)
        ).all()
        
        cleared_abilities = []
        for cooldown in cooldowns_to_clear:
            # Get the ability name for reporting
            char_ability = next(
                (ab for ab in character_abilities if ab.id == cooldown.character_ability_id),
                None
            )
            if char_ability:
                cleared_abilities.append(char_ability.name)
            
            self.db.delete(cooldown)
        
        return cleared_abilities
    
    def _calculate_spell_effects(self, spell: Spell, cast_level: int, target_ids: List[str]) -> List[Dict[str, Any]]:
        """Calculate the effects of casting a spell."""
        effects = []
        
        # Damage effects
        if spell.damage_dice:
            damage_effect = {
                "type": "damage",
                "damage_dice": spell.damage_dice,
                "damage_type": spell.damage_type,
                "spell_level": cast_level,
                "targets": target_ids,
                "save_attribute": spell.save_attribute,
                "attack_type": spell.attack_type
            }
            effects.append(damage_effect)
        
        # Healing effects
        if spell.healing_dice:
            healing_effect = {
                "type": "healing",
                "healing_dice": spell.healing_dice,
                "spell_level": cast_level,
                "targets": target_ids
            }
            effects.append(healing_effect)
        
        # Condition effects
        for condition in spell.conditions_applied:
            condition_effect = {
                "type": "condition",
                "condition": condition,
                "targets": target_ids,
                "save_attribute": spell.save_attribute,
                "duration": spell.duration
            }
            effects.append(condition_effect)
        
        # Other effects
        for effect in spell.other_effects:
            other_effect = {
                "type": "other",
                "effect": effect,
                "targets": target_ids
            }
            effects.append(other_effect)
        
        return effects
    
    def _calculate_ability_effects(self, ability: Ability, target_ids: List[str], 
                                 modifications: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate the effects of using an ability."""
        effects = []
        
        # Process mechanics from the ability
        for mechanic_type, mechanic_data in ability.mechanics.items():
            effect = {
                "type": mechanic_type,
                "data": mechanic_data,
                "targets": target_ids,
                "modifications": modifications
            }
            effects.append(effect)
        
        return effects