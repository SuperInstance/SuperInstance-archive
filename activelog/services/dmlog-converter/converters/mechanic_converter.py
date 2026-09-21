"""
Mechanic translation system for converting game mechanics between systems
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from ..models.base import Mechanic, ConversionResult
from ..config.systems import GameSystem, MECHANIC_MAPPINGS


class MechanicConverter:
    """Converts game mechanics between different systems"""
    
    def __init__(self):
        self.dice_patterns = {
            "advantage": re.compile(r"with advantage", re.IGNORECASE),
            "disadvantage": re.compile(r"with disadvantage", re.IGNORECASE),
            "dice_roll": re.compile(r"(\d+d\d+(?:[+-]\d+)?)", re.IGNORECASE),
            "dc_check": re.compile(r"DC (\d+)", re.IGNORECASE),
            "saving_throw": re.compile(r"(\w+) saving throw", re.IGNORECASE)
        }
    
    def convert_mechanic(
        self, 
        mechanic: Mechanic, 
        target_system: GameSystem
    ) -> ConversionResult:
        """Convert a game mechanic to target system"""
        
        if mechanic.system == target_system:
            return ConversionResult(
                success=True,
                source_system=mechanic.system,
                target_system=target_system,
                converted_data=mechanic.dict(),
                conversion_notes=["No conversion needed - same system"]
            )
        
        result = ConversionResult(
            success=True,
            source_system=mechanic.system,
            target_system=target_system
        )
        
        try:
            # Convert procedure steps
            converted_procedure = self._convert_procedure(
                mechanic.procedure, mechanic.system, target_system
            )
            
            # Convert modifiers
            converted_modifiers = self._convert_modifiers(
                mechanic.modifiers, mechanic.system, target_system
            )
            
            # Convert trigger conditions
            converted_trigger = self._convert_trigger(
                mechanic.trigger, mechanic.system, target_system
            )
            
            # Convert examples
            converted_examples = self._convert_examples(
                mechanic.examples, mechanic.system, target_system
            )
            
            # Check for system-specific mappings
            mapped_mechanic = self._apply_mechanic_mappings(
                mechanic, target_system
            )
            
            # Build converted mechanic
            converted_mechanic = Mechanic(
                name=mapped_mechanic.get("name", mechanic.name),
                system=target_system,
                category=mechanic.category,
                description=mapped_mechanic.get("description", mechanic.description),
                trigger=converted_trigger,
                procedure=converted_procedure,
                modifiers=converted_modifiers,
                requires=mechanic.requires.copy(),
                conflicts_with=mechanic.conflicts_with.copy(),
                examples=converted_examples,
                system_specific={}
            )
            
            result.converted_data = converted_mechanic.dict()
            result.conversion_confidence = self._calculate_mechanic_confidence(
                mechanic, converted_mechanic
            )
            
            if result.conversion_confidence < 0.6:
                result.manual_review_required = True
                result.warnings.append("Complex mechanic conversion needs review")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Mechanic conversion failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def _convert_procedure(
        self, 
        procedure: List[str], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[str]:
        """Convert procedure steps between systems"""
        
        converted_steps = []
        
        for step in procedure:
            converted_step = step
            
            # Convert dice mechanics
            converted_step = self._convert_dice_mechanics(
                converted_step, source_system, target_system
            )
            
            # Convert DC references
            converted_step = self._convert_dc_references(
                converted_step, source_system, target_system
            )
            
            # Convert saving throw references
            converted_step = self._convert_saving_throw_references(
                converted_step, source_system, target_system
            )
            
            # Convert skill references
            converted_step = self._convert_skill_references(
                converted_step, source_system, target_system
            )
            
            # Convert action economy terms
            converted_step = self._convert_action_economy(
                converted_step, source_system, target_system
            )
            
            converted_steps.append(converted_step)
        
        return converted_steps
    
    def _convert_dice_mechanics(
        self, 
        text: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert dice roll mechanics in text"""
        
        # D&D 5E advantage/disadvantage to Pathfinder 2E fortune/misfortune
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            text = re.sub(r"with advantage", "with fortune", text, flags=re.IGNORECASE)
            text = re.sub(r"with disadvantage", "with misfortune", text, flags=re.IGNORECASE)
            text = re.sub(r"advantage", "fortune", text, flags=re.IGNORECASE)
            text = re.sub(r"disadvantage", "misfortune", text, flags=re.IGNORECASE)
        
        # Pathfinder 2E fortune/misfortune to D&D 5E advantage/disadvantage
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            text = re.sub(r"with fortune", "with advantage", text, flags=re.IGNORECASE)
            text = re.sub(r"with misfortune", "with disadvantage", text, flags=re.IGNORECASE)
            text = re.sub(r"fortune", "advantage", text, flags=re.IGNORECASE)
            text = re.sub(r"misfortune", "disadvantage", text, flags=re.IGNORECASE)
        
        # Convert dice notation where needed
        dice_matches = self.dice_patterns["dice_roll"].findall(text)
        for dice_notation in dice_matches:
            converted_dice = self._convert_dice_notation(
                dice_notation, source_system, target_system
            )
            if converted_dice != dice_notation:
                text = text.replace(dice_notation, converted_dice)
        
        return text
    
    def _convert_dice_notation(
        self, 
        dice_str: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert dice notation between systems"""
        
        # Parse dice string (e.g., "2d6+3")
        match = re.match(r"(\d+)d(\d+)([+-]\d+)?", dice_str)
        if not match:
            return dice_str
        
        num_dice, die_size, modifier = match.groups()
        num_dice = int(num_dice)
        die_size = int(die_size)
        modifier = int(modifier) if modifier else 0
        
        # System-specific dice conversions
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # Pathfinder 2E tends to use slightly higher damage values
            if die_size == 6 and num_dice <= 2:
                # Keep same for small amounts
                pass
            elif die_size == 6 and num_dice > 2:
                # Slightly increase for larger amounts
                modifier += 1
        
        # Rebuild dice string
        result = f"{num_dice}d{die_size}"
        if modifier > 0:
            result += f"+{modifier}"
        elif modifier < 0:
            result += str(modifier)
        
        return result
    
    def _convert_dc_references(
        self, 
        text: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert DC values in text"""
        
        dc_matches = self.dice_patterns["dc_check"].findall(text)
        for dc_str in dc_matches:
            dc_value = int(dc_str)
            converted_dc = self._convert_dc_value(dc_value, source_system, target_system)
            if converted_dc != dc_value:
                text = text.replace(f"DC {dc_value}", f"DC {converted_dc}")
        
        return text
    
    def _convert_dc_value(
        self, 
        dc: int, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> int:
        """Convert DC values between systems"""
        
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # D&D 5E to Pathfinder 2E DC conversion
            dc_mapping = {5: 10, 10: 14, 15: 18, 20: 22, 25: 26, 30: 30}
            for threshold in sorted(dc_mapping.keys()):
                if dc <= threshold:
                    return dc_mapping[threshold]
            return dc + 5
        
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            # Pathfinder 2E to D&D 5E DC conversion
            dc_mapping = {10: 5, 14: 10, 18: 15, 22: 20, 26: 25, 30: 30}
            for threshold in sorted(dc_mapping.keys()):
                if dc <= threshold:
                    return dc_mapping[threshold]
            return max(5, dc - 5)
        
        return dc
    
    def _convert_saving_throw_references(
        self, 
        text: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert saving throw references in text"""
        
        save_matches = self.dice_patterns["saving_throw"].findall(text)
        for save_name in save_matches:
            converted_save = self._convert_save_name(save_name, source_system, target_system)
            if converted_save != save_name:
                text = text.replace(f"{save_name} saving throw", f"{converted_save} saving throw")
        
        return text
    
    def _convert_save_name(
        self, 
        save: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert saving throw names between systems"""
        
        save_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "strength": "fortitude",
                "dexterity": "reflex",
                "constitution": "fortitude", 
                "intelligence": "will",
                "wisdom": "will",
                "charisma": "will"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "fortitude": "constitution",
                "reflex": "dexterity",
                "will": "wisdom"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key in save_mappings:
            return save_mappings[mapping_key].get(save.lower(), save)
        
        return save
    
    def _convert_skill_references(
        self, 
        text: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert skill names in text"""
        
        from ..config.systems import SKILL_MAPPINGS
        
        mapping_key = (source_system, target_system)
        if mapping_key not in SKILL_MAPPINGS:
            return text
        
        skill_mapping = SKILL_MAPPINGS[mapping_key]
        
        # Replace skill names in text (case insensitive)
        for source_skill, target_skill in skill_mapping.items():
            if source_skill != target_skill:
                # Use word boundaries to avoid partial matches
                pattern = rf"\b{re.escape(source_skill)}\b"
                text = re.sub(pattern, target_skill, text, flags=re.IGNORECASE)
        
        return text
    
    def _convert_action_economy(
        self, 
        text: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert action economy terms"""
        
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # D&D 5E to Pathfinder 2E action conversions
            text = re.sub(r"\baction\b", "action (1 action)", text, flags=re.IGNORECASE)
            text = re.sub(r"\bbonus action\b", "action (1 action)", text, flags=re.IGNORECASE)
            text = re.sub(r"\breaction\b", "reaction", text, flags=re.IGNORECASE)
            text = re.sub(r"\bfree action\b", "free action", text, flags=re.IGNORECASE)
        
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            # Pathfinder 2E to D&D 5E action conversions
            text = re.sub(r"\b1 action\b", "action", text, flags=re.IGNORECASE)
            text = re.sub(r"\b2 actions\b", "action", text, flags=re.IGNORECASE)
            text = re.sub(r"\b3 actions\b", "action", text, flags=re.IGNORECASE)
            text = re.sub(r"\bfree action\b", "free action", text, flags=re.IGNORECASE)
        
        return text
    
    def _convert_modifiers(
        self, 
        modifiers: Dict[str, Any], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Convert modifier values and types"""
        
        converted_modifiers = {}
        
        for modifier_name, modifier_value in modifiers.items():
            # Convert modifier names
            converted_name = self._convert_modifier_name(
                modifier_name, source_system, target_system
            )
            
            # Convert modifier values
            if isinstance(modifier_value, (int, float)):
                converted_value = self._convert_modifier_value(
                    modifier_value, modifier_name, source_system, target_system
                )
            else:
                converted_value = modifier_value
            
            converted_modifiers[converted_name] = converted_value
        
        return converted_modifiers
    
    def _convert_modifier_name(
        self, 
        modifier_name: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert modifier names between systems"""
        
        modifier_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "proficiency_bonus": "proficiency_bonus",
                "ability_modifier": "ability_modifier",
                "circumstance": "circumstance",
                "enhancement": "item",
                "magical": "item"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "proficiency_bonus": "proficiency_bonus",
                "ability_modifier": "ability_modifier", 
                "circumstance": "circumstance",
                "item": "enhancement",
                "status": "magical"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key in modifier_mappings:
            return modifier_mappings[mapping_key].get(modifier_name.lower(), modifier_name)
        
        return modifier_name
    
    def _convert_modifier_value(
        self, 
        value: float, 
        modifier_name: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> float:
        """Convert modifier values between systems"""
        
        # Most modifier values translate directly
        # But some systems have different scaling
        if "damage" in modifier_name.lower():
            return self._scale_damage_modifier(value, source_system, target_system)
        
        return value
    
    def _scale_damage_modifier(
        self, 
        value: float, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> float:
        """Scale damage modifier values between systems"""
        
        scaling_factors = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): 1.1,
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): 0.9
        }
        
        scaling_key = (source_system, target_system)
        if scaling_key in scaling_factors:
            return value * scaling_factors[scaling_key]
        
        return value
    
    def _convert_trigger(
        self, 
        trigger: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert trigger conditions between systems"""
        
        converted_trigger = trigger
        
        # Convert dice mechanics in trigger
        converted_trigger = self._convert_dice_mechanics(
            converted_trigger, source_system, target_system
        )
        
        # Convert action economy references
        converted_trigger = self._convert_action_economy(
            converted_trigger, source_system, target_system
        )
        
        # Convert skill references
        converted_trigger = self._convert_skill_references(
            converted_trigger, source_system, target_system
        )
        
        return converted_trigger
    
    def _convert_examples(
        self, 
        examples: List[str], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[str]:
        """Convert example text between systems"""
        
        converted_examples = []
        
        for example in examples:
            converted_example = example
            
            # Apply all text conversions
            converted_example = self._convert_dice_mechanics(
                converted_example, source_system, target_system
            )
            converted_example = self._convert_dc_references(
                converted_example, source_system, target_system
            )
            converted_example = self._convert_saving_throw_references(
                converted_example, source_system, target_system
            )
            converted_example = self._convert_skill_references(
                converted_example, source_system, target_system
            )
            converted_example = self._convert_action_economy(
                converted_example, source_system, target_system
            )
            
            converted_examples.append(converted_example)
        
        return converted_examples
    
    def _apply_mechanic_mappings(
        self, 
        mechanic: Mechanic, 
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Apply system-specific mechanic mappings"""
        
        mapping_key = (mechanic.system, target_system)
        if mapping_key not in MECHANIC_MAPPINGS:
            return {}
        
        mechanic_mappings = MECHANIC_MAPPINGS[mapping_key]
        mechanic_key = f"{mechanic.category}:{mechanic.name}".lower()
        
        return mechanic_mappings.get(mechanic_key, {})
    
    def _calculate_mechanic_confidence(
        self, 
        original: Mechanic, 
        converted: Mechanic
    ) -> float:
        """Calculate confidence score for mechanic conversion"""
        
        confidence_factors = []
        
        # Procedure conversion confidence
        if len(converted.procedure) >= len(original.procedure) * 0.8:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.5)
        
        # Modifier preservation confidence
        if len(converted.modifiers) >= len(original.modifiers) * 0.7:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.6)
        
        # Category preservation confidence
        if converted.category == original.category:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.7)
        
        # Text complexity assessment
        total_text = " ".join(original.procedure + original.examples)
        complexity_score = self._assess_text_complexity(total_text)
        confidence_factors.append(max(0.4, 1.0 - complexity_score * 0.3))
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _assess_text_complexity(self, text: str) -> float:
        """Assess complexity of mechanic text for conversion difficulty"""
        
        complexity_indicators = [
            r"\badvantage\b|\bdisadvantage\b",  # Advantage/disadvantage mechanics
            r"\bDC \d+\b",  # DC checks
            r"\d+d\d+",  # Dice rolls
            r"\bsaving throw\b",  # Saving throws
            r"\baction\b|\bbonus action\b|\breaction\b",  # Action economy
            r"\bproficiency\b",  # Proficiency bonuses
            r"\bspell\b|\bcantrip\b",  # Magic system references
        ]
        
        complexity_score = 0
        for indicator in complexity_indicators:
            matches = len(re.findall(indicator, text, re.IGNORECASE))
            complexity_score += matches * 0.1
        
        return min(1.0, complexity_score)
    
    def batch_convert_mechanics(
        self, 
        mechanics: List[Mechanic], 
        target_system: GameSystem
    ) -> List[ConversionResult]:
        """Convert multiple mechanics at once"""
        
        results = []
        for mechanic in mechanics:
            result = self.convert_mechanic(mechanic, target_system)
            results.append(result)
        
        return results
    
    def get_mechanic_conversion_preview(
        self, 
        mechanic: Mechanic, 
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Get preview of mechanic conversion changes"""
        
        preview = {
            "source_system": mechanic.system.value,
            "target_system": target_system.value,
            "mechanic_name": mechanic.name,
            "category": mechanic.category,
            "changes": []
        }
        
        # Preview procedure changes
        converted_procedure = self._convert_procedure(
            mechanic.procedure, mechanic.system, target_system
        )
        
        for i, (original_step, converted_step) in enumerate(zip(mechanic.procedure, converted_procedure)):
            if original_step != converted_step:
                preview["changes"].append({
                    "type": "procedure_step",
                    "step_number": i + 1,
                    "old_text": original_step,
                    "new_text": converted_step
                })
        
        # Preview modifier changes
        converted_modifiers = self._convert_modifiers(
            mechanic.modifiers, mechanic.system, target_system
        )
        
        for mod_name, old_value in mechanic.modifiers.items():
            converted_name = self._convert_modifier_name(mod_name, mechanic.system, target_system)
            new_value = converted_modifiers.get(converted_name, old_value)
            
            if mod_name != converted_name or old_value != new_value:
                preview["changes"].append({
                    "type": "modifier",
                    "old_name": mod_name,
                    "new_name": converted_name,
                    "old_value": old_value,
                    "new_value": new_value
                })
        
        return preview