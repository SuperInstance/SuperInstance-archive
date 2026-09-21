"""
Difficulty scaling converter for adjusting challenge levels between systems
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from ..models.base import ConversionResult
from ..config.systems import GameSystem, POWER_LEVEL_MAPPINGS


class DifficultyTier(Enum):
    TRIVIAL = "trivial"
    EASY = "easy" 
    MODERATE = "moderate"
    HARD = "hard"
    SEVERE = "severe"
    EXTREME = "extreme"
    IMPOSSIBLE = "impossible"


class DifficultyConverter:
    """Converts difficulty scaling between different game systems"""
    
    def __init__(self):
        # System-specific difficulty curves
        self.difficulty_curves = {
            GameSystem.D_AND_D_5E: {
                "cr_by_level": {
                    1: 0.25, 2: 0.5, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 7, 10: 8,
                    11: 9, 12: 10, 13: 11, 14: 12, 15: 13, 16: 14, 17: 15, 18: 16, 19: 17, 20: 18
                },
                "dc_by_level": {
                    1: 10, 2: 11, 3: 12, 4: 13, 5: 13, 6: 14, 7: 14, 8: 15, 9: 15, 10: 16,
                    11: 16, 12: 17, 13: 17, 14: 18, 15: 18, 16: 19, 17: 19, 18: 20, 19: 20, 20: 21
                },
                "damage_by_level": {
                    1: 4, 2: 7, 3: 10, 4: 14, 5: 18, 6: 22, 7: 26, 8: 30, 9: 35, 10: 40,
                    11: 45, 12: 50, 13: 56, 14: 62, 15: 68, 16: 74, 17: 80, 18: 86, 19: 92, 20: 98
                }
            },
            GameSystem.PATHFINDER_2E: {
                "level_by_level": {
                    1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10,
                    11: 11, 12: 12, 13: 13, 14: 14, 15: 15, 16: 16, 17: 17, 18: 18, 19: 19, 20: 20
                },
                "dc_by_level": {
                    1: 14, 2: 16, 3: 18, 4: 19, 5: 20, 6: 22, 7: 23, 8: 24, 9: 26, 10: 27,
                    11: 28, 12: 30, 13: 31, 14: 32, 15: 34, 16: 35, 17: 36, 18: 38, 19: 39, 20: 40
                },
                "damage_by_level": {
                    1: 6, 2: 10, 3: 14, 4: 18, 5: 22, 6: 26, 7: 30, 8: 35, 9: 40, 10: 45,
                    11: 50, 12: 55, 13: 60, 14: 65, 15: 70, 16: 75, 17: 80, 18: 85, 19: 90, 20: 95
                }
            }
        }
        
        # Difficulty tier multipliers
        self.tier_multipliers = {
            DifficultyTier.TRIVIAL: 0.25,
            DifficultyTier.EASY: 0.5,
            DifficultyTier.MODERATE: 1.0,
            DifficultyTier.HARD: 1.5,
            DifficultyTier.SEVERE: 2.0,
            DifficultyTier.EXTREME: 3.0,
            DifficultyTier.IMPOSSIBLE: 4.0
        }
    
    def convert_challenge_rating(
        self, 
        cr: float, 
        party_level: int,
        source_system: GameSystem, 
        target_system: GameSystem,
        difficulty_tier: DifficultyTier = DifficultyTier.MODERATE
    ) -> ConversionResult:
        """Convert challenge rating between systems"""
        
        result = ConversionResult(
            success=True,
            source_system=source_system,
            target_system=target_system
        )
        
        try:
            if source_system == target_system:
                result.converted_data = {"challenge_rating": cr}
                result.conversion_notes = ["No conversion needed - same system"]
                return result
            
            # Convert CR to target system
            if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
                converted_cr = self._dnd5e_cr_to_pf2e_level(cr, party_level)
            elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
                converted_cr = self._pf2e_level_to_dnd5e_cr(cr, party_level)
            else:
                # Generic conversion
                converted_cr = self._generic_cr_conversion(cr, source_system, target_system, party_level)
            
            # Apply difficulty tier adjustment
            tier_adjustment = self._calculate_tier_adjustment(difficulty_tier, target_system)
            final_cr = max(0, converted_cr + tier_adjustment)
            
            result.converted_data = {
                "challenge_rating": final_cr,
                "original_cr": cr,
                "difficulty_tier": difficulty_tier.value,
                "party_level": party_level,
                "tier_adjustment": tier_adjustment
            }
            
            result.conversion_confidence = self._calculate_cr_confidence(
                cr, converted_cr, source_system, target_system
            )
            
            if abs(cr - converted_cr) > 2:
                result.warnings.append("Significant CR change - verify balance")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"CR conversion failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def convert_difficulty_class(
        self, 
        dc: int, 
        party_level: int,
        source_system: GameSystem, 
        target_system: GameSystem,
        difficulty_tier: DifficultyTier = DifficultyTier.MODERATE
    ) -> ConversionResult:
        """Convert DC values between systems"""
        
        result = ConversionResult(
            success=True,
            source_system=source_system,
            target_system=target_system
        )
        
        try:
            if source_system == target_system:
                result.converted_data = {"dc": dc}
                result.conversion_notes = ["No conversion needed - same system"]
                return result
            
            # Get baseline DC for level in both systems
            source_baseline = self._get_baseline_dc(party_level, source_system)
            target_baseline = self._get_baseline_dc(party_level, target_system)
            
            # Calculate relative difficulty
            if source_baseline > 0:
                difficulty_ratio = dc / source_baseline
            else:
                difficulty_ratio = 1.0
            
            # Convert to target system
            converted_dc = int(target_baseline * difficulty_ratio)
            
            # Apply difficulty tier adjustment
            tier_adjustment = self._calculate_dc_tier_adjustment(
                difficulty_tier, party_level, target_system
            )
            final_dc = max(5, converted_dc + tier_adjustment)
            
            result.converted_data = {
                "dc": final_dc,
                "original_dc": dc,
                "difficulty_tier": difficulty_tier.value,
                "party_level": party_level,
                "source_baseline": source_baseline,
                "target_baseline": target_baseline,
                "tier_adjustment": tier_adjustment
            }
            
            result.conversion_confidence = self._calculate_dc_confidence(
                dc, converted_dc, source_system, target_system
            )
            
        except Exception as e:
            result.success = False
            result.errors.append(f"DC conversion failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def convert_damage_values(
        self, 
        damage: Dict[str, Any], 
        party_level: int,
        source_system: GameSystem, 
        target_system: GameSystem,
        difficulty_tier: DifficultyTier = DifficultyTier.MODERATE
    ) -> ConversionResult:
        """Convert damage values between systems"""
        
        result = ConversionResult(
            success=True,
            source_system=source_system,
            target_system=target_system
        )
        
        try:
            if source_system == target_system:
                result.converted_data = damage.copy()
                result.conversion_notes = ["No conversion needed - same system"]
                return result
            
            converted_damage = {}
            
            # Convert average damage
            if "average" in damage:
                converted_avg = self._convert_damage_value(
                    damage["average"], party_level, source_system, target_system, difficulty_tier
                )
                converted_damage["average"] = converted_avg
            
            # Convert dice notation
            if "dice" in damage:
                converted_dice = self._convert_damage_dice(
                    damage["dice"], party_level, source_system, target_system, difficulty_tier
                )
                converted_damage["dice"] = converted_dice
            
            # Convert damage type (usually stays the same)
            if "type" in damage:
                converted_damage["type"] = damage["type"]
            
            # Copy other properties
            for key, value in damage.items():
                if key not in converted_damage:
                    converted_damage[key] = value
            
            result.converted_data = converted_damage
            result.conversion_confidence = 0.85
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Damage conversion failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def _dnd5e_cr_to_pf2e_level(self, cr: float, party_level: int) -> int:
        """Convert D&D 5E CR to Pathfinder 2E creature level"""
        
        # Rough CR to level mapping
        cr_to_level = {
            0: party_level - 4, 0.125: party_level - 3, 0.25: party_level - 2,
            0.5: party_level - 1, 1: party_level, 2: party_level + 1,
            3: party_level + 1, 4: party_level + 2, 5: party_level + 2,
            6: party_level + 3, 7: party_level + 3, 8: party_level + 4
        }
        
        # For higher CRs, use linear progression
        if cr in cr_to_level:
            return max(-1, cr_to_level[cr])
        elif cr > 8:
            return party_level + int(cr / 2)
        else:
            return party_level - 1
    
    def _pf2e_level_to_dnd5e_cr(self, level: int, party_level: int) -> float:
        """Convert Pathfinder 2E creature level to D&D 5E CR"""
        
        level_diff = level - party_level
        
        # Level difference to CR mapping
        if level_diff <= -4:
            return 0
        elif level_diff == -3:
            return 0.125
        elif level_diff == -2:
            return 0.25
        elif level_diff == -1:
            return 0.5
        elif level_diff == 0:
            return 1
        elif level_diff == 1:
            return 2
        elif level_diff == 2:
            return 4
        elif level_diff == 3:
            return 6
        elif level_diff == 4:
            return 8
        else:
            return max(1, level_diff * 2)
    
    def _generic_cr_conversion(
        self, 
        cr: float, 
        source_system: GameSystem, 
        target_system: GameSystem, 
        party_level: int
    ) -> float:
        """Generic CR conversion for other system pairs"""
        
        # Use power level mappings if available
        mapping_key = (source_system, target_system)
        if mapping_key in POWER_LEVEL_MAPPINGS:
            level_mapping = POWER_LEVEL_MAPPINGS[mapping_key]
            cr_int = int(cr)
            if cr_int in level_mapping:
                return float(level_mapping[cr_int])
        
        # Fallback: assume similar power scales
        return cr
    
    def _get_baseline_dc(self, level: int, system: GameSystem) -> int:
        """Get baseline DC for a given level in a system"""
        
        if system in self.difficulty_curves:
            dc_curve = self.difficulty_curves[system].get("dc_by_level", {})
            return dc_curve.get(level, 10 + level // 2)
        
        # Generic baseline
        return 10 + level // 2
    
    def _convert_damage_value(
        self, 
        damage: int, 
        party_level: int, 
        source_system: GameSystem, 
        target_system: GameSystem,
        difficulty_tier: DifficultyTier
    ) -> int:
        """Convert a single damage value between systems"""
        
        # Get baseline damage for level in both systems
        source_baseline = self._get_baseline_damage(party_level, source_system)
        target_baseline = self._get_baseline_damage(party_level, target_system)
        
        # Calculate relative damage
        if source_baseline > 0:
            damage_ratio = damage / source_baseline
        else:
            damage_ratio = 1.0
        
        # Convert to target system
        converted_damage = int(target_baseline * damage_ratio)
        
        # Apply difficulty tier multiplier
        tier_multiplier = self.tier_multipliers[difficulty_tier]
        return max(1, int(converted_damage * tier_multiplier))
    
    def _convert_damage_dice(
        self, 
        dice_str: str, 
        party_level: int, 
        source_system: GameSystem, 
        target_system: GameSystem,
        difficulty_tier: DifficultyTier
    ) -> str:
        """Convert damage dice notation between systems"""
        
        import re
        
        # Parse dice notation (e.g., "2d6+3")
        match = re.match(r"(\d+)d(\d+)([+-]\d+)?", dice_str)
        if not match:
            return dice_str
        
        num_dice, die_size, modifier = match.groups()
        num_dice = int(num_dice)
        die_size = int(die_size)
        modifier = int(modifier) if modifier else 0
        
        # Calculate average damage
        average_damage = (num_dice * (die_size + 1) // 2) + modifier
        
        # Convert average damage
        converted_average = self._convert_damage_value(
            average_damage, party_level, source_system, target_system, difficulty_tier
        )
        
        # Scale dice to match converted average
        if average_damage > 0:
            scale_factor = converted_average / average_damage
        else:
            scale_factor = 1.0
        
        # Apply scaling to modifier first, then dice if needed
        new_modifier = int(modifier * scale_factor)
        remaining_damage = converted_average - (num_dice * (die_size + 1) // 2) - new_modifier
        
        if remaining_damage > 0:
            # Need more dice or larger dice
            if remaining_damage > num_dice:
                # Increase dice size
                new_die_size = min(12, die_size + 2)
                return f"{num_dice}d{new_die_size}+{new_modifier}" if new_modifier > 0 else f"{num_dice}d{new_die_size}"
            else:
                # Add to modifier
                new_modifier += remaining_damage
        
        # Build result
        result = f"{num_dice}d{die_size}"
        if new_modifier > 0:
            result += f"+{new_modifier}"
        elif new_modifier < 0:
            result += str(new_modifier)
        
        return result
    
    def _get_baseline_damage(self, level: int, system: GameSystem) -> int:
        """Get baseline damage for a given level in a system"""
        
        if system in self.difficulty_curves:
            damage_curve = self.difficulty_curves[system].get("damage_by_level", {})
            return damage_curve.get(level, level * 4)
        
        # Generic baseline
        return level * 4
    
    def _calculate_tier_adjustment(
        self, 
        tier: DifficultyTier, 
        system: GameSystem
    ) -> float:
        """Calculate CR adjustment for difficulty tier"""
        
        tier_adjustments = {
            DifficultyTier.TRIVIAL: -2,
            DifficultyTier.EASY: -1,
            DifficultyTier.MODERATE: 0,
            DifficultyTier.HARD: 1,
            DifficultyTier.SEVERE: 2,
            DifficultyTier.EXTREME: 3,
            DifficultyTier.IMPOSSIBLE: 4
        }
        
        return tier_adjustments[tier]
    
    def _calculate_dc_tier_adjustment(
        self, 
        tier: DifficultyTier, 
        level: int, 
        system: GameSystem
    ) -> int:
        """Calculate DC adjustment for difficulty tier"""
        
        base_adjustments = {
            DifficultyTier.TRIVIAL: -5,
            DifficultyTier.EASY: -2,
            DifficultyTier.MODERATE: 0,
            DifficultyTier.HARD: 2,
            DifficultyTier.SEVERE: 5,
            DifficultyTier.EXTREME: 8,
            DifficultyTier.IMPOSSIBLE: 10
        }
        
        return base_adjustments[tier]
    
    def _calculate_cr_confidence(
        self, 
        original_cr: float, 
        converted_cr: float, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> float:
        """Calculate confidence for CR conversion"""
        
        # Confidence decreases with larger changes
        cr_diff = abs(original_cr - converted_cr)
        
        if cr_diff <= 0.5:
            return 0.95
        elif cr_diff <= 1:
            return 0.85
        elif cr_diff <= 2:
            return 0.75
        elif cr_diff <= 4:
            return 0.6
        else:
            return 0.4
    
    def _calculate_dc_confidence(
        self, 
        original_dc: int, 
        converted_dc: int, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> float:
        """Calculate confidence for DC conversion"""
        
        dc_diff = abs(original_dc - converted_dc)
        
        if dc_diff <= 1:
            return 0.95
        elif dc_diff <= 2:
            return 0.85
        elif dc_diff <= 5:
            return 0.75
        elif dc_diff <= 8:
            return 0.6
        else:
            return 0.4
    
    def scale_encounter_budget(
        self, 
        budget: Dict[str, Any], 
        party_size: int,
        party_level: int,
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> ConversionResult:
        """Scale encounter budget between systems"""
        
        result = ConversionResult(
            success=True,
            source_system=source_system,
            target_system=target_system
        )
        
        try:
            converted_budget = budget.copy()
            
            # Scale XP budget
            if "xp_budget" in budget:
                converted_budget["xp_budget"] = self._convert_xp_budget(
                    budget["xp_budget"], party_size, party_level, source_system, target_system
                )
            
            # Scale creature count recommendations
            if "creature_count" in budget:
                converted_budget["creature_count"] = self._scale_creature_count(
                    budget["creature_count"], source_system, target_system
                )
            
            # Convert difficulty thresholds
            if "difficulty_thresholds" in budget:
                converted_budget["difficulty_thresholds"] = self._convert_difficulty_thresholds(
                    budget["difficulty_thresholds"], party_level, source_system, target_system
                )
            
            result.converted_data = converted_budget
            result.conversion_confidence = 0.8
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Budget scaling failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def _convert_xp_budget(
        self, 
        xp_budget: int, 
        party_size: int, 
        party_level: int,
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> int:
        """Convert XP budget between systems"""
        
        # XP per level scaling varies by system
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # PF2E doesn't use XP budgets in the same way
            return 0
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            # Convert to D&D 5E XP budget
            base_xp_per_character = [25, 50, 75, 125, 250, 300, 350, 450, 550, 600,
                                   800, 1000, 1100, 1250, 1400, 1600, 2000, 2100, 2400, 2800]
            if 1 <= party_level <= 20:
                return base_xp_per_character[party_level - 1] * party_size
        
        # For other conversions, scale proportionally
        scaling_factor = self._get_xp_scaling_factor(source_system, target_system)
        return int(xp_budget * scaling_factor)
    
    def _get_xp_scaling_factor(
        self, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> float:
        """Get XP scaling factor between systems"""
        
        # System-specific XP scaling
        scaling_factors = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_1E): 1.2,
            (GameSystem.PATHFINDER_1E, GameSystem.D_AND_D_5E): 0.8,
            (GameSystem.D_AND_D_5E, GameSystem.D_AND_D_3_5E): 0.9,
            (GameSystem.D_AND_D_3_5E, GameSystem.D_AND_D_5E): 1.1
        }
        
        return scaling_factors.get((source_system, target_system), 1.0)
    
    def _scale_creature_count(
        self, 
        count_data: Dict[str, Any], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Scale creature count recommendations between systems"""
        
        scaled_data = count_data.copy()
        
        # Different systems have different action economies
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # PF2E handles multiple enemies differently
            if "max_creatures" in count_data:
                scaled_data["max_creatures"] = min(count_data["max_creatures"], 6)
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            # D&D 5E can handle more creatures due to simpler action economy
            if "max_creatures" in count_data:
                scaled_data["max_creatures"] = count_data["max_creatures"] + 2
        
        return scaled_data
    
    def _convert_difficulty_thresholds(
        self, 
        thresholds: Dict[str, int], 
        party_level: int,
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, int]:
        """Convert difficulty thresholds between systems"""
        
        converted_thresholds = {}
        
        for difficulty_name, threshold_value in thresholds.items():
            # Map difficulty names between systems
            mapped_difficulty = self._map_difficulty_name(
                difficulty_name, source_system, target_system
            )
            
            # Scale threshold value
            baseline_dc = self._get_baseline_dc(party_level, target_system)
            source_baseline = self._get_baseline_dc(party_level, source_system)
            
            if source_baseline > 0:
                scaling_ratio = baseline_dc / source_baseline
                converted_value = int(threshold_value * scaling_ratio)
            else:
                converted_value = threshold_value
            
            converted_thresholds[mapped_difficulty] = converted_value
        
        return converted_thresholds
    
    def _map_difficulty_name(
        self, 
        difficulty: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Map difficulty names between systems"""
        
        difficulty_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "easy": "low",
                "medium": "moderate", 
                "hard": "severe",
                "deadly": "extreme"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "trivial": "easy",
                "low": "easy",
                "moderate": "medium",
                "severe": "hard",
                "extreme": "deadly"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key in difficulty_mappings:
            return difficulty_mappings[mapping_key].get(difficulty.lower(), difficulty)
        
        return difficulty