"""
Rest and recovery management system
"""

from datetime import datetime, date
from typing import Dict, List, Any, Optional
from ..models.base import RestRecord, RestType, Character


class RestManager:
    """Manages character rest and recovery"""
    
    def __init__(self):
        self.rest_records: Dict[str, List[RestRecord]] = {}  # character_id -> records
        self.rest_templates: Dict[RestType, Dict[str, Any]] = {
            RestType.SHORT_REST: {
                "duration_hours": 1.0,
                "recovers_hit_dice": True,
                "recovers_spell_slots": False,
                "recovers_features": ["action_surge", "second_wind"]
            },
            RestType.LONG_REST: {
                "duration_hours": 8.0,
                "recovers_hit_dice": True,
                "recovers_spell_slots": True,
                "recovers_features": ["all"]
            },
            RestType.EXTENDED_REST: {
                "duration_hours": 24.0,
                "recovers_hit_dice": True,
                "recovers_spell_slots": True,
                "recovers_features": ["all"]
            }
        }
    
    def take_rest(
        self, 
        character: Character,
        rest_type: RestType,
        duration_hours: Optional[float] = None,
        interrupted: bool = False,
        location: str = "",
        notes: str = ""
    ) -> RestRecord:
        """Process a character rest"""
        
        # Store pre-rest state
        hp_before = character.hit_points.get("current", 0)
        spell_slots_before = {k: v.get("used", 0) for k, v in character.spell_slots.items()}
        hit_dice_before = character.hit_dice.copy()
        
        # Apply rest benefits
        if not interrupted:
            self._apply_rest_benefits(character, rest_type)
        
        # Store post-rest state
        hp_after = character.hit_points.get("current", 0)
        spell_slots_after = {k: v.get("used", 0) for k, v in character.spell_slots.items()}
        hit_dice_after = character.hit_dice.copy()
        
        # Calculate recovery amounts
        hit_dice_recovered = {}
        for die_type in hit_dice_after:
            before = hit_dice_before.get(die_type, 0)
            after = hit_dice_after.get(die_type, 0)
            if after > before:
                hit_dice_recovered[die_type] = after - before
        
        spell_slots_recovered = {}
        for level in spell_slots_after:
            before_used = spell_slots_before.get(level, 0)
            after_used = spell_slots_after.get(level, 0)
            if after_used < before_used:
                spell_slots_recovered[level] = before_used - after_used
        
        # Create rest record
        rest_record = RestRecord(
            character_id=character.id,
            rest_type=rest_type,
            hp_before=hp_before,
            spell_slots_before=spell_slots_before,
            hit_dice_before=hit_dice_before,
            hp_after=hp_after,
            spell_slots_after=spell_slots_after,
            hit_dice_after=hit_dice_after,
            duration_hours=duration_hours or self.rest_templates[rest_type]["duration_hours"],
            interrupted=interrupted,
            location=location,
            notes=notes,
            hit_dice_recovered=hit_dice_recovered,
            spell_slots_recovered=spell_slots_recovered,
            features_recovered=self._get_recovered_features(rest_type)
        )
        
        # Store record
        if character.id not in self.rest_records:
            self.rest_records[character.id] = []
        self.rest_records[character.id].append(rest_record)
        
        return rest_record
    
    def _apply_rest_benefits(self, character: Character, rest_type: RestType):
        """Apply rest benefits to character"""
        
        template = self.rest_templates[rest_type]
        
        if rest_type == RestType.SHORT_REST:
            # Short rest: can spend hit dice to recover HP
            # Let player decide how many to spend
            pass
        
        elif rest_type == RestType.LONG_REST:
            # Long rest: recover all HP, spell slots, and features
            max_hp = character.hit_points.get("max", 0)
            character.hit_points["current"] = max_hp
            
            # Recover spell slots
            for level_str in character.spell_slots:
                character.spell_slots[level_str]["used"] = 0
            
            # Recover hit dice (half of total)
            total_hit_dice = character.level
            current_hit_dice = sum(character.hit_dice.values())
            missing_hit_dice = total_hit_dice - current_hit_dice
            
            if missing_hit_dice > 0:
                # Recover half the missing hit dice (minimum 1)
                recovery_amount = max(1, missing_hit_dice // 2)
                
                # Add to primary class hit dice (would need class info)
                primary_die = "d8"  # Default, would be based on class
                character.hit_dice[primary_die] = character.hit_dice.get(primary_die, 0) + recovery_amount
        
        elif rest_type == RestType.EXTENDED_REST:
            # Extended rest: full recovery including all hit dice
            max_hp = character.hit_points.get("max", 0)
            character.hit_points["current"] = max_hp
            
            # Recover all spell slots
            for level_str in character.spell_slots:
                character.spell_slots[level_str]["used"] = 0
            
            # Recover all hit dice
            character.hit_dice = {"d8": character.level}  # Simplified
    
    def spend_hit_dice(
        self, 
        character: Character,
        die_type: str,
        num_dice: int
    ) -> Dict[str, Any]:
        """Spend hit dice during short rest"""
        
        if die_type not in character.hit_dice:
            return {"success": False, "error": "No hit dice of that type"}
        
        available = character.hit_dice[die_type]
        if num_dice > available:
            return {"success": False, "error": "Not enough hit dice available"}
        
        # Roll hit dice and add CON modifier
        con_modifier = (character.attributes.get("constitution", 10) - 10) // 2
        die_size = int(die_type[1:])  # Extract number from "d8", "d10", etc.
        
        total_healing = 0
        rolls = []
        
        for _ in range(num_dice):
            # Simulate roll (would use actual dice in real implementation)
            import random
            roll = random.randint(1, die_size)
            healing = roll + con_modifier
            total_healing += healing
            rolls.append({"roll": roll, "modifier": con_modifier, "total": healing})
        
        # Apply healing
        current_hp = character.hit_points.get("current", 0)
        max_hp = character.hit_points.get("max", 0)
        new_hp = min(max_hp, current_hp + total_healing)
        
        character.hit_points["current"] = new_hp
        character.hit_dice[die_type] -= num_dice
        
        return {
            "success": True,
            "rolls": rolls,
            "total_healing": total_healing,
            "hp_before": current_hp,
            "hp_after": new_hp,
            "hit_dice_spent": num_dice
        }
    
    def get_rest_history(self, character_id: str, days: int = 30) -> List[RestRecord]:
        """Get character's rest history"""
        
        if character_id not in self.rest_records:
            return []
        
        cutoff_date = datetime.utcnow() - datetime.timedelta(days=days)
        recent_rests = [
            record for record in self.rest_records[character_id]
            if record.rest_date >= cutoff_date
        ]
        
        return sorted(recent_rests, key=lambda r: r.rest_date, reverse=True)
    
    def get_rest_statistics(self, character_id: str) -> Dict[str, Any]:
        """Get rest statistics for character"""
        
        records = self.rest_records.get(character_id, [])
        
        if not records:
            return {
                "total_rests": 0,
                "short_rests": 0,
                "long_rests": 0,
                "extended_rests": 0,
                "average_recovery": 0,
                "interrupted_rests": 0
            }
        
        # Count by type
        type_counts = {}
        for record in records:
            rest_type = record.rest_type.value
            type_counts[rest_type] = type_counts.get(rest_type, 0) + 1
        
        # Calculate average HP recovery
        hp_recoveries = [r.hp_after - r.hp_before for r in records if r.hp_after > r.hp_before]
        avg_recovery = sum(hp_recoveries) / len(hp_recoveries) if hp_recoveries else 0
        
        # Count interruptions
        interrupted_count = sum(1 for r in records if r.interrupted)
        
        return {
            "total_rests": len(records),
            "short_rests": type_counts.get("short_rest", 0),
            "long_rests": type_counts.get("long_rest", 0),
            "extended_rests": type_counts.get("extended_rest", 0),
            "average_hp_recovery": avg_recovery,
            "interrupted_rests": interrupted_count,
            "interruption_rate": interrupted_count / len(records) * 100 if records else 0
        }
    
    def suggest_rest_timing(self, character: Character) -> Dict[str, Any]:
        """Suggest when character should rest"""
        
        suggestions = []
        urgency = "none"
        
        # Check HP
        current_hp = character.hit_points.get("current", 0)
        max_hp = character.hit_points.get("max", 1)
        hp_percentage = (current_hp / max_hp) * 100
        
        if hp_percentage <= 25:
            suggestions.append("HP critically low - consider immediate rest")
            urgency = "critical"
        elif hp_percentage <= 50:
            suggestions.append("HP below half - short rest recommended")
            urgency = "high" if urgency != "critical" else urgency
        
        # Check spell slots
        total_slots = sum(slot_data.get("max", 0) for slot_data in character.spell_slots.values())
        used_slots = sum(slot_data.get("used", 0) for slot_data in character.spell_slots.values())
        
        if total_slots > 0:
            slots_remaining = total_slots - used_slots
            slot_percentage = (slots_remaining / total_slots) * 100
            
            if slot_percentage <= 25:
                suggestions.append("Most spell slots used - long rest recommended")
                urgency = "high" if urgency not in ["critical"] else urgency
            elif slot_percentage <= 50:
                suggestions.append("Half spell slots used - consider rest soon")
                urgency = "medium" if urgency == "none" else urgency
        
        # Check hit dice
        total_hit_dice = character.level
        current_hit_dice = sum(character.hit_dice.values())
        hit_dice_percentage = (current_hit_dice / total_hit_dice) * 100 if total_hit_dice > 0 else 100
        
        if hit_dice_percentage <= 25:
            suggestions.append("Few hit dice remaining - long rest needed soon")
            urgency = "medium" if urgency == "none" else urgency
        
        return {
            "urgency": urgency,
            "suggestions": suggestions,
            "current_status": {
                "hp_percentage": hp_percentage,
                "spell_slots_remaining": (slots_remaining / total_slots * 100) if total_slots > 0 else 100,
                "hit_dice_percentage": hit_dice_percentage
            }
        }
    
    def _get_recovered_features(self, rest_type: RestType) -> List[str]:
        """Get list of features recovered by rest type"""
        
        template = self.rest_templates[rest_type]
        return template.get("recovers_features", [])


class SkillTracker:
    """Track skill usage and development"""
    
    def __init__(self):
        self.skill_records: Dict[str, Dict[str, Any]] = {}  # character_id -> skill_data
        self.language_progress: Dict[str, Dict[str, Any]] = {}  # character_id -> language_data
    
    def track_skill_use(
        self, 
        character_id: str,
        skill_name: str,
        dc: int,
        roll_result: int,
        success: bool,
        critical: bool = False
    ):
        """Track a skill usage"""
        
        if character_id not in self.skill_records:
            self.skill_records[character_id] = {}
        
        if skill_name not in self.skill_records[character_id]:
            self.skill_records[character_id][skill_name] = {
                "total_uses": 0,
                "successes": 0,
                "failures": 0,
                "critical_successes": 0,
                "critical_failures": 0,
                "total_dc": 0,
                "total_roll": 0,
                "recent_uses": []
            }
        
        skill_data = self.skill_records[character_id][skill_name]
        
        # Update counters
        skill_data["total_uses"] += 1
        skill_data["total_dc"] += dc
        skill_data["total_roll"] += roll_result
        
        if success:
            skill_data["successes"] += 1
            if critical:
                skill_data["critical_successes"] += 1
        else:
            skill_data["failures"] += 1
            if critical:
                skill_data["critical_failures"] += 1
        
        # Add to recent uses (keep last 10)
        skill_data["recent_uses"].append({
            "dc": dc,
            "roll": roll_result,
            "success": success,
            "critical": critical,
            "date": datetime.utcnow()
        })
        
        if len(skill_data["recent_uses"]) > 10:
            skill_data["recent_uses"] = skill_data["recent_uses"][-10:]
    
    def get_skill_statistics(self, character_id: str) -> Dict[str, Any]:
        """Get skill usage statistics"""
        
        if character_id not in self.skill_records:
            return {}
        
        skill_stats = {}
        
        for skill_name, skill_data in self.skill_records[character_id].items():
            total_uses = skill_data["total_uses"]
            if total_uses == 0:
                continue
            
            success_rate = skill_data["successes"] / total_uses * 100
            average_dc = skill_data["total_dc"] / total_uses
            average_roll = skill_data["total_roll"] / total_uses
            
            skill_stats[skill_name] = {
                "total_uses": total_uses,
                "success_rate": success_rate,
                "average_dc": average_dc,
                "average_roll": average_roll,
                "critical_successes": skill_data["critical_successes"],
                "critical_failures": skill_data["critical_failures"]
            }
        
        return skill_stats