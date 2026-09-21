"""
Encounter balancing and generation service.
"""

import math
import random
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session
from uuid import uuid4

from models.encounter import (
    Encounter, EncounterParticipant, EncounterSchema, ParticipantStats,
    EncounterBalance, EncounterRequest, EncounterSuggestion, MonsterChallengeRating,
    EncounterType, ParticipantType
)
from models.base import DifficultyLevel

class EncounterBalancer:
    """Calculates encounter balance and difficulty."""
    
    # XP thresholds per character level
    XP_THRESHOLDS = {
        1: {"easy": 25, "medium": 50, "hard": 75, "deadly": 100},
        2: {"easy": 50, "medium": 100, "hard": 150, "deadly": 200},
        3: {"easy": 75, "medium": 150, "hard": 225, "deadly": 400},
        4: {"easy": 125, "medium": 250, "hard": 375, "deadly": 500},
        5: {"easy": 250, "medium": 500, "hard": 750, "deadly": 1100},
        6: {"easy": 300, "medium": 600, "hard": 900, "deadly": 1400},
        7: {"easy": 350, "medium": 750, "hard": 1100, "deadly": 1700},
        8: {"easy": 450, "medium": 900, "hard": 1400, "deadly": 2100},
        9: {"easy": 550, "medium": 1100, "hard": 1600, "deadly": 2400},
        10: {"easy": 600, "medium": 1200, "hard": 1900, "deadly": 2800},
        11: {"easy": 800, "medium": 1600, "hard": 2400, "deadly": 3600},
        12: {"easy": 1000, "medium": 2000, "hard": 3000, "deadly": 4500},
        13: {"easy": 1100, "medium": 2200, "hard": 3400, "deadly": 5100},
        14: {"easy": 1250, "medium": 2500, "hard": 3800, "deadly": 5700},
        15: {"easy": 1400, "medium": 2800, "hard": 4300, "deadly": 6400},
        16: {"easy": 1600, "medium": 3200, "hard": 4800, "deadly": 7200},
        17: {"easy": 2000, "medium": 3900, "hard": 5900, "deadly": 8800},
        18: {"easy": 2100, "medium": 4200, "hard": 6300, "deadly": 9500},
        19: {"easy": 2400, "medium": 4900, "hard": 7300, "deadly": 10900},
        20: {"easy": 2800, "medium": 5700, "hard": 8500, "deadly": 12700}
    }
    
    # Encounter multipliers based on number of monsters
    ENCOUNTER_MULTIPLIERS = {
        1: 1.0,
        2: 1.5,
        3: 2.0,
        4: 2.0,
        5: 2.5,
        6: 2.5,
        7: 3.0,
        8: 3.0,
        9: 3.5,
        10: 3.5,
        11: 4.0,
        12: 4.0,
        13: 4.5,
        14: 4.5,
        15: 5.0
    }
    
    # CR to XP mapping
    CR_XP_VALUES = {
        0: 10, 0.125: 25, 0.25: 50, 0.5: 100,
        1: 200, 2: 450, 3: 700, 4: 1100, 5: 1800,
        6: 2300, 7: 2900, 8: 3900, 9: 5000, 10: 5900,
        11: 7200, 12: 8400, 13: 10000, 14: 11500, 15: 13000,
        16: 15000, 17: 18000, 18: 20000, 19: 22000, 20: 25000,
        21: 33000, 22: 41000, 23: 50000, 24: 62000, 25: 75000,
        26: 90000, 27: 105000, 28: 120000, 29: 135000, 30: 155000
    }
    
    @classmethod
    def calculate_party_thresholds(cls, party_levels: List[int]) -> Dict[str, int]:
        """Calculate XP thresholds for the entire party."""
        thresholds = {"easy": 0, "medium": 0, "hard": 0, "deadly": 0}
        
        for level in party_levels:
            if level in cls.XP_THRESHOLDS:
                level_thresholds = cls.XP_THRESHOLDS[level]
                for difficulty in thresholds:
                    thresholds[difficulty] += level_thresholds[difficulty]
        
        return thresholds
    
    @classmethod
    def calculate_encounter_xp(cls, participants: List[ParticipantStats]) -> Tuple[int, int]:
        """Calculate encounter XP and adjusted XP."""
        base_xp = 0
        monster_count = 0
        
        for participant in participants:
            if participant.participant_type in [ParticipantType.NPC, ParticipantType.MONSTER]:
                if participant.challenge_rating is not None:
                    cr_xp = cls.CR_XP_VALUES.get(participant.challenge_rating, 0)
                    base_xp += int(cr_xp * participant.multiplier)
                    monster_count += 1
        
        # Apply encounter multiplier
        multiplier = cls.ENCOUNTER_MULTIPLIERS.get(monster_count, 5.0)
        adjusted_xp = int(base_xp * multiplier)
        
        return base_xp, adjusted_xp
    
    @classmethod
    def determine_difficulty(cls, adjusted_xp: int, thresholds: Dict[str, int]) -> DifficultyLevel:
        """Determine encounter difficulty based on adjusted XP."""
        if adjusted_xp >= thresholds["deadly"]:
            return DifficultyLevel.DEADLY
        elif adjusted_xp >= thresholds["hard"]:
            return DifficultyLevel.HARD
        elif adjusted_xp >= thresholds["medium"]:
            return DifficultyLevel.MEDIUM
        else:
            return DifficultyLevel.EASY
    
    @classmethod
    def calculate_balance_rating(cls, adjusted_xp: int, thresholds: Dict[str, int], target_difficulty: DifficultyLevel) -> float:
        """Calculate balance rating (0.0 to 1.0, where 0.5 is perfect)."""
        target_xp = thresholds[target_difficulty.value]
        
        if target_xp == 0:
            return 0.0
        
        ratio = adjusted_xp / target_xp
        
        # Perfect balance is when ratio is 1.0
        # Rating of 0.5 means perfectly balanced
        # Higher rating means too easy, lower rating means too hard
        if ratio <= 1.0:
            return 0.5 * ratio
        else:
            return min(1.0, 0.5 + (0.5 * (2.0 - ratio)))
    
    @classmethod
    def generate_recommendations(cls, balance: EncounterBalance) -> List[str]:
        """Generate balance recommendations."""
        recommendations = []
        
        if balance.balance_rating < 0.3:
            recommendations.append("Encounter may be too difficult - consider reducing monster CR or quantity")
            recommendations.append("Add environmental advantages for players (cover, elevation, etc.)")
        elif balance.balance_rating > 0.7:
            recommendations.append("Encounter may be too easy - consider adding more monsters or increasing CR")
            recommendations.append("Add terrain hazards or time pressure to increase challenge")
        
        if balance.party_size < 3:
            recommendations.append("Small party - consider reducing monster count or adding NPC ally")
        elif balance.party_size > 6:
            recommendations.append("Large party - increase monster count or use legendary/lair actions")
        
        if balance.average_party_level < 3:
            recommendations.append("Low-level party - avoid save-or-die effects and high burst damage")
        elif balance.average_party_level > 10:
            recommendations.append("High-level party - use monsters with varied resistances and abilities")
        
        return recommendations

class MonsterDatabase:
    """Database of monster statistics for encounter generation."""
    
    SAMPLE_MONSTERS = {
        0: [
            {"name": "Rat", "hp": 1, "ac": 10, "xp": 10, "type": "beast"},
            {"name": "Spider", "hp": 1, "ac": 12, "xp": 10, "type": "beast"},
        ],
        0.125: [
            {"name": "Bandit", "hp": 11, "ac": 12, "xp": 25, "type": "humanoid"},
            {"name": "Kobold", "hp": 5, "ac": 12, "xp": 25, "type": "humanoid"},
        ],
        0.25: [
            {"name": "Goblin", "hp": 7, "ac": 15, "xp": 50, "type": "humanoid"},
            {"name": "Skeleton", "hp": 13, "ac": 13, "xp": 50, "type": "undead"},
        ],
        0.5: [
            {"name": "Orc", "hp": 15, "ac": 13, "xp": 100, "type": "humanoid"},
            {"name": "Hobgoblin", "hp": 11, "ac": 18, "xp": 100, "type": "humanoid"},
        ],
        1: [
            {"name": "Dire Wolf", "hp": 37, "ac": 14, "xp": 200, "type": "beast"},
            {"name": "Bugbear", "hp": 27, "ac": 16, "xp": 200, "type": "humanoid"},
        ],
        2: [
            {"name": "Brown Bear", "hp": 34, "ac": 11, "xp": 450, "type": "beast"},
            {"name": "Ogre", "hp": 59, "ac": 11, "xp": 450, "type": "giant"},
        ],
        3: [
            {"name": "Owlbear", "hp": 59, "ac": 13, "xp": 700, "type": "monstrosity"},
            {"name": "Veteran", "hp": 58, "ac": 17, "xp": 700, "type": "humanoid"},
        ],
        4: [
            {"name": "Ettin", "hp": 85, "ac": 12, "xp": 1100, "type": "giant"},
            {"name": "Flameskull", "hp": 40, "ac": 13, "xp": 1100, "type": "undead"},
        ],
        5: [
            {"name": "Hill Giant", "hp": 105, "ac": 13, "xp": 1800, "type": "giant"},
            {"name": "Troll", "hp": 84, "ac": 15, "xp": 1800, "type": "giant"},
        ]
    }
    
    @classmethod
    def get_monsters_by_cr(cls, cr: float) -> List[Dict[str, Any]]:
        """Get monsters of a specific CR."""
        return cls.SAMPLE_MONSTERS.get(cr, [])
    
    @classmethod
    def find_suitable_monsters(cls, target_xp: int, max_cr: float = None) -> List[Dict[str, Any]]:
        """Find monsters suitable for the target XP budget."""
        suitable = []
        
        for cr, monsters in cls.SAMPLE_MONSTERS.items():
            if max_cr and cr > max_cr:
                continue
                
            cr_xp = EncounterBalancer.CR_XP_VALUES.get(cr, 0)
            if cr_xp <= target_xp:
                for monster in monsters:
                    suitable.append({**monster, "cr": cr})
        
        return suitable

class EncounterGenerator:
    """Generates balanced encounters."""
    
    def __init__(self):
        self.balancer = EncounterBalancer()
        self.monster_db = MonsterDatabase()
    
    def generate_encounter_suggestions(self, request: EncounterRequest) -> List[EncounterSuggestion]:
        """Generate encounter suggestions based on request."""
        suggestions = []
        
        # Calculate party thresholds
        thresholds = self.balancer.calculate_party_thresholds(request.party_levels)
        target_xp = thresholds[request.desired_difficulty.value]
        
        # Generate different encounter configurations
        suggestions.extend(self._generate_single_monster_encounters(target_xp, request))
        suggestions.extend(self._generate_multi_monster_encounters(target_xp, request))
        suggestions.extend(self._generate_swarm_encounters(target_xp, request))
        
        # Sort by balance score
        suggestions.sort(key=lambda x: abs(0.5 - x.balance_score))
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _generate_single_monster_encounters(self, target_xp: int, request: EncounterRequest) -> List[EncounterSuggestion]:
        """Generate encounters with single powerful monsters."""
        suggestions = []
        
        # Find monsters that alone are close to target XP
        suitable_monsters = self.monster_db.find_suitable_monsters(target_xp)
        
        for monster in suitable_monsters:
            if monster["xp"] >= target_xp * 0.8:  # Monster should be at least 80% of target
                encounter_xp = monster["xp"]
                adjusted_xp = encounter_xp  # Single monster, no multiplier
                
                balance_score = self._calculate_balance_score(adjusted_xp, target_xp)
                
                suggestions.append(EncounterSuggestion(
                    name=f"Single {monster['name']}",
                    description=f"A challenging encounter against a single {monster['name']}.",
                    monsters=[{"name": monster["name"], "count": 1, "cr": monster["cr"]}],
                    total_xp=encounter_xp,
                    adjusted_xp=adjusted_xp,
                    difficulty=request.desired_difficulty,
                    balance_score=balance_score
                ))
        
        return suggestions
    
    def _generate_multi_monster_encounters(self, target_xp: int, request: EncounterRequest) -> List[EncounterSuggestion]:
        """Generate encounters with 2-4 monsters."""
        suggestions = []
        
        for monster_count in [2, 3, 4]:
            multiplier = self.balancer.ENCOUNTER_MULTIPLIERS[monster_count]
            base_xp_budget = int(target_xp / multiplier)
            per_monster_budget = base_xp_budget // monster_count
            
            suitable_monsters = self.monster_db.find_suitable_monsters(per_monster_budget)
            
            for monster in suitable_monsters:
                if monster["xp"] <= per_monster_budget:
                    encounter_xp = monster["xp"] * monster_count
                    adjusted_xp = int(encounter_xp * multiplier)
                    
                    balance_score = self._calculate_balance_score(adjusted_xp, target_xp)
                    
                    suggestions.append(EncounterSuggestion(
                        name=f"{monster_count} {monster['name']}s",
                        description=f"An encounter against {monster_count} {monster['name']}s.",
                        monsters=[{"name": monster["name"], "count": monster_count, "cr": monster["cr"]}],
                        total_xp=encounter_xp,
                        adjusted_xp=adjusted_xp,
                        difficulty=request.desired_difficulty,
                        balance_score=balance_score
                    ))
        
        return suggestions
    
    def _generate_swarm_encounters(self, target_xp: int, request: EncounterRequest) -> List[EncounterSuggestion]:
        """Generate encounters with many weak monsters."""
        suggestions = []
        
        for monster_count in [6, 8, 10]:
            multiplier = self.balancer.ENCOUNTER_MULTIPLIERS.get(monster_count, 5.0)
            base_xp_budget = int(target_xp / multiplier)
            per_monster_budget = base_xp_budget // monster_count
            
            # Focus on low-CR monsters for swarms
            suitable_monsters = [
                monster for monster in self.monster_db.find_suitable_monsters(per_monster_budget)
                if monster["cr"] <= 0.5
            ]
            
            for monster in suitable_monsters:
                encounter_xp = monster["xp"] * monster_count
                adjusted_xp = int(encounter_xp * multiplier)
                
                balance_score = self._calculate_balance_score(adjusted_xp, target_xp)
                
                suggestions.append(EncounterSuggestion(
                    name=f"Swarm of {monster_count} {monster['name']}s",
                    description=f"A swarm encounter against {monster_count} {monster['name']}s.",
                    monsters=[{"name": monster["name"], "count": monster_count, "cr": monster["cr"]}],
                    total_xp=encounter_xp,
                    adjusted_xp=adjusted_xp,
                    difficulty=request.desired_difficulty,
                    balance_score=balance_score
                ))
        
        return suggestions
    
    def _calculate_balance_score(self, adjusted_xp: int, target_xp: int) -> float:
        """Calculate how well balanced the encounter is (0.0 to 1.0, 0.5 is perfect)."""
        if target_xp == 0:
            return 0.0
        
        ratio = adjusted_xp / target_xp
        
        # Perfect balance when ratio is 1.0
        if ratio <= 1.0:
            return 0.5 * ratio
        else:
            return min(1.0, 0.5 + (0.5 * (2.0 - ratio)))

class EncounterService:
    """Main encounter service handling database operations."""
    
    def __init__(self):
        self.balancer = EncounterBalancer()
        self.generator = EncounterGenerator()
    
    def analyze_encounter_balance(self, party_levels: List[int], participants: List[ParticipantStats]) -> EncounterBalance:
        """Analyze the balance of an encounter."""
        # Calculate party stats
        total_party_level = sum(party_levels)
        average_party_level = total_party_level / len(party_levels)
        party_size = len(party_levels)
        
        # Calculate thresholds
        thresholds = self.balancer.calculate_party_thresholds(party_levels)
        
        # Calculate encounter XP
        base_xp, adjusted_xp = self.balancer.calculate_encounter_xp(participants)
        
        # Determine difficulty
        difficulty = self.balancer.determine_difficulty(adjusted_xp, thresholds)
        
        # Calculate balance rating
        balance_rating = self.balancer.calculate_balance_rating(adjusted_xp, thresholds, difficulty)
        
        # Generate recommendations
        balance = EncounterBalance(
            total_party_level=total_party_level,
            average_party_level=average_party_level,
            party_size=party_size,
            encounter_xp=base_xp,
            adjusted_xp=adjusted_xp,
            difficulty_threshold=thresholds,
            difficulty_level=difficulty,
            balance_rating=balance_rating,
            recommendations=[]
        )
        
        balance.recommendations = self.balancer.generate_recommendations(balance)
        
        return balance
    
    def generate_encounter(self, request: EncounterRequest) -> List[EncounterSuggestion]:
        """Generate encounter suggestions."""
        return self.generator.generate_encounter_suggestions(request)
    
    def create_encounter(self, encounter_data: EncounterSchema, db: Session) -> Encounter:
        """Create a new encounter in the database."""
        encounter = Encounter(
            id=str(uuid4()),
            name=encounter_data.name,
            description=encounter_data.description,
            encounter_type=encounter_data.encounter_type.value,
            difficulty_level=encounter_data.difficulty_level.value,
            challenge_rating=encounter_data.challenge_rating,
            expected_duration_minutes=encounter_data.expected_duration_minutes,
            environment=encounter_data.environment,
            objectives=encounter_data.objectives,
            rewards=encounter_data.rewards,
            notes=encounter_data.notes,
            campaign_id=encounter_data.campaign_id
        )
        
        db.add(encounter)
        
        # Add participants
        if encounter_data.participants:
            for participant_data in encounter_data.participants:
                participant = EncounterParticipant(
                    id=str(uuid4()),
                    encounter_id=encounter.id,
                    participant_type=participant_data.participant_type.value,
                    participant_id=participant_data.participant_id,
                    participant_name=participant_data.name,
                    level=participant_data.level,
                    hit_points_max=participant_data.hit_points_max,
                    armor_class=participant_data.armor_class,
                    challenge_rating=participant_data.challenge_rating,
                    multiplier=participant_data.multiplier,
                    is_active=participant_data.is_active
                )
                db.add(participant)
        
        db.commit()
        db.refresh(encounter)
        return encounter
    
    def get_encounter(self, encounter_id: str, db: Session) -> Optional[Encounter]:
        """Get an encounter by ID."""
        return db.query(Encounter).filter(Encounter.id == encounter_id).first()
    
    def list_encounters(self, campaign_id: str = None, encounter_type: EncounterType = None, db: Session = None) -> List[Encounter]:
        """List encounters with optional filtering."""
        query = db.query(Encounter)
        
        if campaign_id:
            query = query.filter(Encounter.campaign_id == campaign_id)
        if encounter_type:
            query = query.filter(Encounter.encounter_type == encounter_type.value)
        
        return query.all()