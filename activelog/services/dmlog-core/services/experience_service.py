"""
Experience and leveling service.
"""

import math
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from models.experience import (
    ExperienceGain, LevelProgression, MilestoneTracker,
    ExperienceGainSchema, LevelProgressionSchema, MilestoneSchema,
    ExperienceAward, LevelUpRequest, CharacterProgression, ExperienceCalculation,
    ExperienceType, GameSystem
)

class ExperienceCalculator:
    """Calculates experience points for different activities."""
    
    # Base XP values for different activities
    COMBAT_XP_BASE = {
        "kill": 1.0,
        "defeat": 0.75,
        "flee": 0.25,
        "negotiate": 0.5
    }
    
    QUEST_XP_MULTIPLIERS = {
        "main_quest": 2.0,
        "side_quest": 1.0,
        "minor_quest": 0.5,
        "fetch_quest": 0.3
    }
    
    DISCOVERY_XP_VALUES = {
        "new_location": 50,
        "secret_area": 100,
        "hidden_treasure": 75,
        "lore_discovery": 25,
        "map_completion": 150
    }
    
    SOCIAL_XP_MULTIPLIERS = {
        "critical_success": 1.5,
        "success": 1.0,
        "partial_success": 0.5,
        "failure_with_consequence": 0.25
    }
    
    @classmethod
    def calculate_combat_xp(cls, monster_cr: float, party_size: int, outcome: str = "kill") -> int:
        """Calculate XP for combat encounters."""
        # D&D 5e style XP calculation
        cr_xp_table = {
            0: 10, 0.125: 25, 0.25: 50, 0.5: 100,
            1: 200, 2: 450, 3: 700, 4: 1100, 5: 1800,
            6: 2300, 7: 2900, 8: 3900, 9: 5000, 10: 5900,
            11: 7200, 12: 8400, 13: 10000, 14: 11500, 15: 13000,
            16: 15000, 17: 18000, 18: 20000, 19: 22000, 20: 25000
        }
        
        base_xp = cr_xp_table.get(monster_cr, 0)
        outcome_multiplier = cls.COMBAT_XP_BASE.get(outcome, 1.0)
        
        # Divide by party size
        xp_per_character = int((base_xp * outcome_multiplier) / max(party_size, 1))
        
        return xp_per_character
    
    @classmethod
    def calculate_quest_xp(cls, base_xp: int, quest_type: str, difficulty_multiplier: float = 1.0) -> int:
        """Calculate XP for quest completion."""
        type_multiplier = cls.QUEST_XP_MULTIPLIERS.get(quest_type, 1.0)
        return int(base_xp * type_multiplier * difficulty_multiplier)
    
    @classmethod
    def calculate_discovery_xp(cls, discovery_type: str, significance_multiplier: float = 1.0) -> int:
        """Calculate XP for discoveries."""
        base_xp = cls.DISCOVERY_XP_VALUES.get(discovery_type, 25)
        return int(base_xp * significance_multiplier)
    
    @classmethod
    def calculate_social_xp(cls, base_xp: int, outcome: str, difficulty_multiplier: float = 1.0) -> int:
        """Calculate XP for social encounters."""
        outcome_multiplier = cls.SOCIAL_XP_MULTIPLIERS.get(outcome, 1.0)
        return int(base_xp * outcome_multiplier * difficulty_multiplier)
    
    @classmethod
    def calculate_roleplay_xp(cls, character_level: int, quality_multiplier: float = 1.0) -> int:
        """Calculate XP for roleplay activities."""
        # Base XP scales with level
        base_xp = max(10, character_level * 5)
        return int(base_xp * quality_multiplier)

class LevelingSystem:
    """Handles character leveling mechanics for different game systems."""
    
    # D&D 5e XP requirements per level
    DND5E_XP_TABLE = {
        1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500,
        6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000,
        11: 85000, 12: 100000, 13: 120000, 14: 140000, 15: 165000,
        16: 195000, 17: 225000, 18: 265000, 19: 305000, 20: 355000
    }
    
    # Proficiency bonus progression
    PROFICIENCY_BONUS = {
        1: 2, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3, 8: 3,
        9: 4, 10: 4, 11: 4, 12: 4, 13: 5, 14: 5, 15: 5, 16: 5,
        17: 6, 18: 6, 19: 6, 20: 6
    }
    
    # Hit die by class (simplified)
    HIT_DICE = {
        "barbarian": 12, "fighter": 10, "paladin": 10, "ranger": 10,
        "bard": 8, "cleric": 8, "druid": 8, "monk": 8, "rogue": 8, "warlock": 8,
        "artificer": 8, "sorcerer": 6, "wizard": 6
    }
    
    @classmethod
    def get_xp_for_level(cls, level: int, system: GameSystem = GameSystem.DND5E) -> int:
        """Get XP required for a specific level."""
        if system == GameSystem.DND5E:
            return cls.DND5E_XP_TABLE.get(level, 355000)
        return 0  # Other systems not implemented yet
    
    @classmethod
    def get_level_from_xp(cls, xp: int, system: GameSystem = GameSystem.DND5E) -> int:
        """Determine character level from total XP."""
        if system == GameSystem.DND5E:
            for level in range(20, 0, -1):
                if xp >= cls.DND5E_XP_TABLE[level]:
                    return level
        return 1
    
    @classmethod
    def get_proficiency_bonus(cls, level: int) -> int:
        """Get proficiency bonus for a level."""
        return cls.PROFICIENCY_BONUS.get(level, 2)
    
    @classmethod
    def calculate_hp_gain(cls, character_class: str, constitution_modifier: int, use_average: bool = True) -> int:
        """Calculate HP gain on level up."""
        hit_die = cls.HIT_DICE.get(character_class.lower(), 8)
        
        if use_average:
            # Use average HP gain
            average = (hit_die // 2) + 1
            return max(1, average + constitution_modifier)
        else:
            # Would normally roll, but for now return average
            return max(1, (hit_die // 2) + 1 + constitution_modifier)
    
    @classmethod
    def get_class_features(cls, character_class: str, level: int) -> List[str]:
        """Get class features gained at a specific level."""
        # Simplified feature list - in a real implementation, this would be comprehensive
        features = []
        
        if level == 1:
            features.append(f"{character_class} starting features")
        
        # ASI levels
        if level in [4, 8, 12, 16, 19]:
            features.append("Ability Score Improvement")
        
        # Proficiency bonus increases
        if level in [5, 9, 13, 17]:
            features.append(f"Proficiency Bonus increases to +{cls.get_proficiency_bonus(level)}")
        
        return features
    
    @classmethod
    def get_spell_slots(cls, character_class: str, level: int) -> Dict[str, int]:
        """Get spell slots for a spellcasting class at a specific level."""
        # Simplified spell slot progression - full caster
        if character_class.lower() in ["wizard", "sorcerer", "cleric", "druid"]:
            slots = {}
            
            # Spell slot progression (simplified)
            if level >= 1:
                slots["1st"] = min(4, 2 + (level - 1) // 2)
            if level >= 3:
                slots["2nd"] = min(3, 1 + (level - 3) // 2)
            if level >= 5:
                slots["3rd"] = min(3, 1 + (level - 5) // 2)
            if level >= 7:
                slots["4th"] = min(3, 1 + (level - 7) // 3)
            if level >= 9:
                slots["5th"] = min(3, 1 + (level - 9) // 3)
            
            return slots
        
        return {}

class ExperienceService:
    """Main experience service handling database operations."""
    
    def __init__(self):
        self.calculator = ExperienceCalculator()
        self.leveling_system = LevelingSystem()
    
    def award_experience(self, award: ExperienceAward, db: Session) -> List[ExperienceGain]:
        """Award experience to characters."""
        gains = []
        
        for character_id in award.character_ids:
            # Get current character level and XP (would query character table)
            current_level = 5  # Placeholder
            current_xp = 6500  # Placeholder
            
            # Calculate new totals
            new_total_xp = current_xp + award.amount
            new_level = self.leveling_system.get_level_from_xp(new_total_xp)
            
            # Create experience gain record
            gain = ExperienceGain(
                id=str(uuid4()),
                character_id=character_id,
                campaign_id=award.campaign_id,
                session_id=award.session_id,
                experience_type=award.experience_type.value,
                amount=award.amount,
                description=award.description,
                source=award.source,
                level_before=current_level,
                level_after=new_level,
                total_xp_before=current_xp,
                total_xp_after=new_total_xp,
                awarded_by=award.awarded_by,
                notes=award.notes
            )
            
            db.add(gain)
            gains.append(gain)
            
            # If character leveled up, create progression record
            if new_level > current_level:
                self._handle_level_up(character_id, current_level, new_level, new_total_xp, db)
        
        db.commit()
        return gains
    
    def _handle_level_up(self, character_id: str, old_level: int, new_level: int, total_xp: int, db: Session):
        """Handle character level up."""
        # Get character class and constitution (would query character table)
        character_class = "fighter"  # Placeholder
        con_modifier = 2  # Placeholder
        
        for level in range(old_level + 1, new_level + 1):
            # Calculate HP gain
            hp_gained = self.leveling_system.calculate_hp_gain(character_class, con_modifier)
            
            # Get new features
            features = self.leveling_system.get_class_features(character_class, level)
            
            # Get spell slots
            spell_slots = self.leveling_system.get_spell_slots(character_class, level)
            
            # Create progression record
            progression = LevelProgression(
                id=str(uuid4()),
                character_id=character_id,
                old_level=level - 1,
                new_level=level,
                experience_required=self.leveling_system.get_xp_for_level(level),
                experience_gained=total_xp - self.leveling_system.get_xp_for_level(level - 1),
                hit_points_gained=hp_gained,
                features_gained=features,
                spell_slots_gained=spell_slots,
                proficiency_bonus_old=self.leveling_system.get_proficiency_bonus(level - 1),
                proficiency_bonus_new=self.leveling_system.get_proficiency_bonus(level)
            )
            
            db.add(progression)
    
    def level_up_character(self, request: LevelUpRequest, db: Session) -> LevelProgression:
        """Manually level up a character."""
        # Get current character data (would query character table)
        current_level = 5  # Placeholder
        current_xp = 6500  # Placeholder
        character_class = "fighter"  # Placeholder
        con_modifier = 2  # Placeholder
        
        if request.new_level <= current_level:
            raise ValueError("New level must be higher than current level")
        
        # Calculate HP gain
        if request.hit_die_roll:
            hp_gained = max(1, request.hit_die_roll + con_modifier)
        else:
            hp_gained = self.leveling_system.calculate_hp_gain(character_class, con_modifier, request.use_average)
        
        # Get new features
        features = self.leveling_system.get_class_features(character_class, request.new_level)
        
        # Get spell slots
        spell_slots = self.leveling_system.get_spell_slots(character_class, request.new_level)
        
        # Create progression record
        progression = LevelProgression(
            id=str(uuid4()),
            character_id=request.character_id,
            old_level=current_level,
            new_level=request.new_level,
            experience_required=self.leveling_system.get_xp_for_level(request.new_level),
            experience_gained=0,  # Manual level up
            hit_points_gained=hp_gained,
            hit_die_rolls=[request.hit_die_roll] if request.hit_die_roll else None,
            features_gained=features,
            spell_slots_gained=spell_slots,
            attribute_increases=request.attribute_increases,
            proficiency_bonus_old=self.leveling_system.get_proficiency_bonus(current_level),
            proficiency_bonus_new=self.leveling_system.get_proficiency_bonus(request.new_level),
            notes=request.notes
        )
        
        db.add(progression)
        db.commit()
        db.refresh(progression)
        
        return progression
    
    def create_milestone(self, milestone: MilestoneSchema, db: Session) -> MilestoneTracker:
        """Create a milestone tracker."""
        milestone_tracker = MilestoneTracker(
            id=str(uuid4()),
            campaign_id=milestone.campaign_id,
            character_id=milestone.character_id,
            milestone_name=milestone.milestone_name,
            description=milestone.description,
            experience_value=milestone.experience_value,
            prerequisites=milestone.prerequisites,
            is_repeatable=milestone.is_repeatable
        )
        
        db.add(milestone_tracker)
        db.commit()
        db.refresh(milestone_tracker)
        
        return milestone_tracker
    
    def complete_milestone(self, milestone_id: str, character_ids: List[str], db: Session) -> MilestoneTracker:
        """Complete a milestone."""
        milestone = db.query(MilestoneTracker).filter(MilestoneTracker.id == milestone_id).first()
        if not milestone:
            raise ValueError("Milestone not found")
        
        if milestone.is_completed and not milestone.is_repeatable:
            raise ValueError("Milestone already completed")
        
        # Award experience to characters
        award = ExperienceAward(
            character_ids=character_ids,
            experience_type=ExperienceType.MILESTONE,
            amount=milestone.experience_value,
            description=f"Milestone: {milestone.milestone_name}",
            source=milestone_id
        )
        
        self.award_experience(award, db)
        
        # Mark milestone as completed
        milestone.is_completed = True
        milestone.completed_at = datetime.utcnow()
        milestone.completed_by = character_ids
        
        db.commit()
        db.refresh(milestone)
        
        return milestone
    
    def get_character_progression(self, character_id: str, db: Session) -> CharacterProgression:
        """Get comprehensive character progression data."""
        # Get experience gains
        gains = db.query(ExperienceGain).filter(
            ExperienceGain.character_id == character_id
        ).order_by(ExperienceGain.created_at.desc()).limit(10).all()
        
        # Get level progressions
        progressions = db.query(LevelProgression).filter(
            LevelProgression.character_id == character_id
        ).order_by(LevelProgression.leveled_at.desc()).all()
        
        # Calculate current stats (would get from character table)
        current_level = 5  # Placeholder
        current_xp = 6500  # Placeholder
        
        next_level_xp = self.leveling_system.get_xp_for_level(current_level + 1)
        xp_to_next = next_level_xp - current_xp
        
        # Calculate session stats
        total_sessions = len(set(gain.session_id for gain in gains if gain.session_id))
        avg_xp = sum(gain.amount for gain in gains) / max(len(gains), 1)
        
        return CharacterProgression(
            character_id=character_id,
            current_level=current_level,
            current_xp=current_xp,
            next_level_xp=next_level_xp,
            xp_to_next_level=xp_to_next,
            total_sessions=total_sessions,
            average_xp_per_session=avg_xp,
            recent_gains=[ExperienceGainSchema.from_orm(gain) for gain in gains],
            level_history=[LevelProgressionSchema.from_orm(prog) for prog in progressions],
            milestones_completed=[],  # Would query milestone completions
            milestones_available=[]   # Would query available milestones
        )
    
    def calculate_experience(self, experience_type: ExperienceType, **kwargs) -> ExperienceCalculation:
        """Calculate experience with detailed breakdown."""
        base_xp = 0
        multipliers = {}
        bonuses = {}
        penalties = {}
        breakdown = []
        
        if experience_type == ExperienceType.COMBAT:
            monster_cr = kwargs.get("monster_cr", 1)
            party_size = kwargs.get("party_size", 4)
            outcome = kwargs.get("outcome", "kill")
            
            base_xp = self.calculator.calculate_combat_xp(monster_cr, party_size, outcome)
            breakdown.append(f"Base combat XP for CR {monster_cr}: {base_xp}")
            
        elif experience_type == ExperienceType.QUEST:
            base_amount = kwargs.get("base_xp", 100)
            quest_type = kwargs.get("quest_type", "side_quest")
            difficulty = kwargs.get("difficulty_multiplier", 1.0)
            
            base_xp = self.calculator.calculate_quest_xp(base_amount, quest_type, difficulty)
            breakdown.append(f"Quest XP ({quest_type}): {base_xp}")
            
        elif experience_type == ExperienceType.DISCOVERY:
            discovery_type = kwargs.get("discovery_type", "new_location")
            significance = kwargs.get("significance_multiplier", 1.0)
            
            base_xp = self.calculator.calculate_discovery_xp(discovery_type, significance)
            breakdown.append(f"Discovery XP ({discovery_type}): {base_xp}")
        
        # Apply multipliers and bonuses
        final_xp = base_xp
        for name, multiplier in multipliers.items():
            final_xp = int(final_xp * multiplier)
            breakdown.append(f"Applied {name} multiplier ({multiplier}x)")
        
        for name, bonus in bonuses.items():
            final_xp += bonus
            breakdown.append(f"Applied {name} bonus (+{bonus})")
        
        for name, penalty in penalties.items():
            final_xp -= penalty
            breakdown.append(f"Applied {name} penalty (-{penalty})")
        
        final_xp = max(0, final_xp)
        
        return ExperienceCalculation(
            base_xp=base_xp,
            multipliers=multipliers,
            bonuses=bonuses,
            penalties=penalties,
            final_xp=final_xp,
            breakdown=breakdown
        )