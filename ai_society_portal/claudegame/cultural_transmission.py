"""
AI Society Portal - Cultural Transmission System
=================================================
Implements knowledge, skill, and behavioral transmission between AI characters.
Foundation for cumulative cultural evolution and emergent society dynamics.

Weeks 4-5: Cultural Knowledge Transfer & Learning
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
import random
import numpy as np


# ============================================================================
# SKILL & KNOWLEDGE ENCODING
# ============================================================================

class TransmissionMode(Enum):
    """How knowledge is transmitted"""
    EXPLICIT_TEACHING = "explicit_teaching"    # Deliberate instruction
    IMITATION_LEARNING = "imitation_learning"  # Learning by observation
    SHARED_EXPERIENCE = "shared_experience"    # Learning together
    PASSIVE_OBSERVATION = "passive_observation"  # Witnessing without participation


@dataclass
class SkillPackage:
    """Encoded skill ready for transmission"""
    skill_id: str
    skill_name: str
    teacher_id: str
    teacher_name: str
    teacher_proficiency: float  # 0.0-1.0
    
    # Encoded skill structure
    encoded_steps: List[str] = field(default_factory=list)  # Procedural memory
    success_examples: List[str] = field(default_factory=list)  # What works
    failure_examples: List[str] = field(default_factory=list)  # What doesn't
    prerequisites: List[str] = field(default_factory=list)  # Required skills
    
    # Transmission metadata
    difficulty: float = 0.5  # 0.0-1.0
    transmission_fidelity_target: float = 0.8  # Desired accuracy
    created_at: datetime = field(default_factory=datetime.now)
    taught_times: int = 0
    successful_adoptions: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def estimate_teaching_success(self, learner_proficiency: Dict[str, float]) -> float:
        """Estimate likelihood of successful transmission"""
        score = 0.0
        
        # Teacher quality
        score += self.teacher_proficiency * 0.3
        
        # Has prerequisites?
        prerequisite_met = all(
            learner_proficiency.get(prereq, 0.0) >= 0.3
            for prereq in self.prerequisites
        )
        score += 0.4 if prerequisite_met else 0.0
        
        # Difficulty vs learner ability
        avg_learner_skill = np.mean(list(learner_proficiency.values())) if learner_proficiency else 0.3
        difficulty_match = 1.0 - abs(self.difficulty - avg_learner_skill)
        score += difficulty_match * 0.3
        
        return score


@dataclass
class AdoptedSkill:
    """Skill adopted by a learner character"""
    skill_id: str
    learned_from_character_id: str
    learned_from_name: str
    adoption_date: datetime
    
    # Proficiency tracking
    proficiency: float = 0.2  # Starts low
    usage_count: int = 0
    last_used: Optional[datetime] = None
    
    # Personalization
    personalized_steps: List[str] = field(default_factory=list)
    personal_success_examples: List[str] = field(default_factory=list)
    personal_adaptations: Dict[str, str] = field(default_factory=dict)
    
    # Learning history
    improvement_rate: float = 0.02  # Proficiency increase per use
    total_improvement: float = 0.0
    
    def use_skill(self, success: bool = True) -> float:
        """Track skill usage and proficiency improvement"""
        self.usage_count += 1
        self.last_used = datetime.now()
        
        if success:
            improvement = self.improvement_rate * (1.0 - self.proficiency)
            self.proficiency = min(self.proficiency + improvement, 1.0)
            self.total_improvement += improvement
        
        return self.proficiency
    
    def personalize_step(self, original_step: str, personalization: str):
        """Add personal adaptation to a skill step"""
        if original_step not in self.personalized_steps:
            self.personalized_steps.append(original_step)
        
        self.personal_adaptations[original_step] = personalization


# ============================================================================
# TEACHING & LEARNING SYSTEM
# ============================================================================

class CulturalTransmissionEngine:
    """
    Manages skill transmission, teaching, learning, and cultural accumulation.
    Inspired by research on human cultural transmission and animal cultures.
    """
    
    def __init__(self):
        # Global skill repository
        self.skill_library: Dict[str, SkillPackage] = {}
        
        # Character skills (character_id -> {skill_id -> AdoptedSkill})
        self.character_skills: Dict[str, Dict[str, AdoptedSkill]] = {}
        
        # Teaching history
        self.teaching_events: List[Dict[str, Any]] = []
        
        # Cultural landmarks (skills that became traditions)
        self.cultural_landmarks: Dict[str, Dict[str, Any]] = {}
        
        # Character relationships for teaching (mentor-apprentice bonds)
        self.teaching_relationships: Dict[Tuple[str, str], Dict[str, Any]] = {}
        
        # Parameters (from cultural evolution research)
        self.TRANSMISSION_FIDELITY_TARGET = 0.75  # 75% accuracy target
        self.MIN_ADOPTERS_FOR_CULTURE = 5         # 5+ adopters = culture
        self.TEACHING_DECISION_THRESHOLD = 60.0   # Score threshold for teaching vs imitation
        self.CONFORMIST_BIAS = 0.7                # 70% of learners use majority variant
        self.INNOVATION_RATE = 0.15               # 15% chance of variation
    
    def create_skill(self, skill_name: str, teacher_id: str, teacher_name: str,
                    teacher_proficiency: float,
                    encoded_steps: List[str],
                    success_examples: List[str] = None,
                    prerequisites: List[str] = None,
                    difficulty: float = 0.5) -> SkillPackage:
        """
        Teacher creates a teachable skill from their proficiency.
        """
        skill_id = hashlib.md5(
            f"{teacher_id}{skill_name}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        skill = SkillPackage(
            skill_id=skill_id,
            skill_name=skill_name,
            teacher_id=teacher_id,
            teacher_name=teacher_name,
            teacher_proficiency=teacher_proficiency,
            encoded_steps=encoded_steps,
            success_examples=success_examples or [],
            prerequisites=prerequisites or [],
            difficulty=difficulty,
            created_at=datetime.now()
        )
        
        self.skill_library[skill_id] = skill
        return skill
    
    def determine_transmission_mode(self, teacher_id: str, learner_id: str,
                                   skill: SkillPackage,
                                   relationship_strength: float = 0.5) -> Tuple[TransmissionMode, str]:
        """
        Decide whether to use explicit teaching or imitation learning.
        Based on teacher proficiency, relationship, skill complexity, etc.
        
        Returns: (transmission_mode, personalization_level)
        """
        score = 0.0
        
        # Teacher quality (high proficiency → teaching)
        if skill.teacher_proficiency > 0.7:
            score += 30
        
        # Teacher personality (agreeableness → teaching)
        # Would integrate with character personality system
        score += 20
        
        # Skill complexity (complex → explicit teaching)
        score += min(skill.difficulty * 25, 25)
        
        # Relationship strength (strong → teaching)
        score += relationship_strength * 15
        
        # Learner motivation (would check character goals)
        score += 15  # Default mid-level
        
        # Teaching context (workshop/classroom → teaching)
        score += 10  # Default
        
        if score >= self.TEACHING_DECISION_THRESHOLD:
            # Explicit teaching with personalization level based on relationship
            personalization = "moderate" if relationship_strength > 0.6 else "high"
            return (TransmissionMode.EXPLICIT_TEACHING, personalization)
        else:
            # Imitation learning with innovation potential
            personalization = "innovate" if random.random() < self.INNOVATION_RATE else "imitate"
            return (TransmissionMode.IMITATION_LEARNING, personalization)
    
    def teach_skill(self, teacher_id: str, learner_id: str,
                   skill_id: str, transmission_mode: TransmissionMode,
                   personalization_level: str = "moderate") -> Optional[AdoptedSkill]:
        """
        Execute skill transmission from teacher to learner.
        """
        if skill_id not in self.skill_library:
            return None
        
        skill = self.skill_library[skill_id]
        
        # Initialize learner skill dict if needed
        if learner_id not in self.character_skills:
            self.character_skills[learner_id] = {}
        
        # Create adopted skill
        adopted = AdoptedSkill(
            skill_id=skill_id,
            learned_from_character_id=teacher_id,
            learned_from_name=skill.teacher_name,
            adoption_date=datetime.now(),
            proficiency=0.2  # Start low
        )
        
        # Apply transmission fidelity based on mode and personalization
        fidelity_map = {
            "imitate": 0.9,      # 90% fidelity when imitating
            "moderate": 0.7,     # 70% fidelity with moderate personalization
            "innovate": 0.5      # 50% fidelity with innovation (more variation)
        }
        fidelity = fidelity_map.get(personalization_level, 0.7)
        
        # Apply personalization: learner adapts steps to their style
        for step in skill.encoded_steps:
            if random.random() < fidelity:
                # Keep original step
                adopted.personalized_steps.append(step)
            else:
                # Personalize: this is where individual variation emerges
                personalized = self._personalize_step(step, learner_id)
                adopted.personalized_steps.append(personalized)
        
        # Copy success examples
        adopted.personal_success_examples = skill.success_examples.copy()
        
        # Store adopted skill
        self.character_skills[learner_id][skill_id] = adopted
        
        # Record teaching event
        self.teaching_events.append({
            "timestamp": datetime.now().isoformat(),
            "teacher_id": teacher_id,
            "teacher_name": skill.teacher_name,
            "learner_id": learner_id,
            "skill_id": skill_id,
            "skill_name": skill.skill_name,
            "transmission_mode": transmission_mode.value,
            "personalization_level": personalization_level,
            "fidelity": fidelity
        })
        
        # Update relationship
        rel_key = (teacher_id, learner_id)
        if rel_key not in self.teaching_relationships:
            self.teaching_relationships[rel_key] = {
                "teaching_events": 0,
                "learning_success": 0,
                "mentorship_strength": 0.0
            }
        self.teaching_relationships[rel_key]["teaching_events"] += 1
        self.teaching_relationships[rel_key]["mentorship_strength"] = min(
            self.teaching_relationships[rel_key]["mentorship_strength"] + 0.1,
            1.0
        )
        
        # Check if this skill becomes a cultural landmark
        self._check_cultural_landmark(skill_id)
        
        # Update teacher's successful adoptions
        skill.taught_times += 1
        skill.successful_adoptions += 1
        
        return adopted
    
    def learn_skill_by_observation(self, learner_id: str, observed_character_id: str,
                                  skill_id: str) -> Optional[AdoptedSkill]:
        """
        Learner observes someone else using a skill and learns by imitation.
        """
        # Get the observed character's adopted skill
        if observed_character_id not in self.character_skills:
            return None
        
        if skill_id not in self.character_skills[observed_character_id]:
            return None
        
        observed_skill = self.character_skills[observed_character_id][skill_id]
        
        # Get original skill package
        if skill_id not in self.skill_library:
            return None
        
        original_skill = self.skill_library[skill_id]
        
        # Create adopted skill based on observation
        adopted = AdoptedSkill(
            skill_id=skill_id,
            learned_from_character_id=observed_character_id,
            learned_from_name="[Observed]",
            adoption_date=datetime.now(),
            proficiency=observed_skill.proficiency * 0.8  # Start lower than observer
        )
        
        # Copy observed character's personalized version (with variation)
        adopted.personalized_steps = observed_skill.personalized_steps.copy()
        
        # Add learner's own variations (5-15% difference)
        if random.random() < 0.1:  # 10% chance of variation
            idx = random.randint(0, len(adopted.personalized_steps) - 1)
            adopted.personalized_steps[idx] = self._personalize_step(
                adopted.personalized_steps[idx],
                learner_id
            )
        
        # Store
        if learner_id not in self.character_skills:
            self.character_skills[learner_id] = {}
        
        self.character_skills[learner_id][skill_id] = adopted
        
        return adopted
    
    def _personalize_step(self, original_step: str, character_id: str) -> str:
        """Personalize a skill step to a character's style"""
        # Would integrate with character personality to make personalization meaningful
        personalizations = [
            f"My way: {original_step}",
            f"Adapted for my approach: {original_step}",
            f"In my style: {original_step}",
            f"How I'd do it: {original_step}"
        ]
        return random.choice(personalizations)
    
    def _check_cultural_landmark(self, skill_id: str):
        """
        Check if a skill has become a cultural tradition.
        Requires MIN_ADOPTERS_FOR_CULTURE adopters.
        """
        # Count adopters
        adopters = []
        for char_id, skills in self.character_skills.items():
            if skill_id in skills:
                adopters.append(char_id)
        
        if len(adopters) >= self.MIN_ADOPTERS_FOR_CULTURE:
            if skill_id not in self.cultural_landmarks:
                # Create cultural landmark
                self.cultural_landmarks[skill_id] = {
                    "skill_id": skill_id,
                    "skill_name": self.skill_library[skill_id].skill_name,
                    "established_at": datetime.now().isoformat(),
                    "participants": adopters,
                    "status": "established",
                    "variant_count": self._count_skill_variants(skill_id, adopters),
                    "adoption_rate": len(adopters),
                    "persistence_score": self._calculate_persistence(skill_id)
                }
    
    def _count_skill_variants(self, skill_id: str, adopters: List[str]) -> int:
        """Count distinct variants of a skill in population"""
        variants = set()
        
        for char_id in adopters:
            if char_id in self.character_skills and skill_id in self.character_skills[char_id]:
                skill = self.character_skills[char_id][skill_id]
                # Use first step as variant signature (simplified)
                variant_sig = tuple(skill.personalized_steps[:2]) if skill.personalized_steps else ("base",)
                variants.add(variant_sig)
        
        return len(variants)
    
    def _calculate_persistence(self, skill_id: str) -> float:
        """
        Calculate how persistent a cultural skill is.
        Range: 0-1, where 1 = perfectly persistent
        
        Factors:
        - Age of skill
        - Adoption consistency
        - Usage frequency
        """
        if skill_id not in self.skill_library:
            return 0.0
        
        skill = self.skill_library[skill_id]
        
        # Age factor (older skills = more persistent)
        age_days = (datetime.now() - skill.created_at).days
        age_score = min(age_days / 30.0, 0.3)  # Max 30% from age
        
        # Adoption consistency
        adoption_score = min(skill.successful_adoptions / 10.0, 0.4)  # Max 40%
        
        # Usage frequency (would track actual usage)
        usage_score = 0.3  # Default
        
        return min(age_score + adoption_score + usage_score, 1.0)
    
    def get_character_skills(self, character_id: str) -> Dict[str, AdoptedSkill]:
        """Get all skills learned by a character"""
        return self.character_skills.get(character_id, {})
    
    def get_cultural_status(self) -> Dict[str, Any]:
        """Get overall cultural transmission status"""
        return {
            "total_skills_created": len(self.skill_library),
            "total_skills_adopted": sum(
                len(skills) for skills in self.character_skills.values()
            ),
            "cultural_landmarks": len(self.cultural_landmarks),
            "teaching_events": len(self.teaching_events),
            "average_adoption_per_skill": np.mean([
                len(adopters) for adopters in [
                    [c for c, s in self.character_skills.items()
                     if skill_id in s]
                    for skill_id in self.skill_library
                ]
            ]) if self.skill_library else 0.0
        }


# ============================================================================
# CULTURAL TRANSMISSION METRICS
# ============================================================================

class CulturalMetrics:
    """Calculate metrics for cultural transmission health"""
    
    @staticmethod
    def adoption_rate(engine: CulturalTransmissionEngine,
                     window_days: int = 7) -> float:
        """Adoptions per day (target: >0.05)"""
        cutoff = datetime.now() - timedelta(days=window_days)
        recent_adoptions = sum(
            1 for event in engine.teaching_events
            if datetime.fromisoformat(event["timestamp"]) > cutoff
        )
        return recent_adoptions / window_days if window_days > 0 else 0.0
    
    @staticmethod
    def transmission_fidelity(engine: CulturalTransmissionEngine) -> float:
        """
        Accuracy of skill transmission (target: 0.6-0.8 for moderate innovation).
        0.8+ = high fidelity, 0.5-0.8 = moderate, <0.5 = high innovation
        """
        if not engine.teaching_events:
            return 0.7  # Default
        
        fidelities = [
            event["fidelity"] for event in engine.teaching_events[-100:]  # Last 100
        ]
        return np.mean(fidelities)
    
    @staticmethod
    def innovation_index(engine: CulturalTransmissionEngine) -> float:
        """
        Diversity of variants (target: 0.3-0.5).
        Measures uniqueness of personalized skill variants.
        """
        variant_counts = []
        
        for skill_id in engine.skill_library:
            variants = set()
            for char_id in engine.character_skills:
                if skill_id in engine.character_skills[char_id]:
                    skill = engine.character_skills[char_id][skill_id]
                    variant_sig = tuple(skill.personalized_steps[:2]) if skill.personalized_steps else ("base",)
                    variants.add(variant_sig)
            
            if variants:
                # Count adopters of this skill
                adopters = [
                    c for c in engine.character_skills
                    if skill_id in engine.character_skills[c]
                ]
                if adopters:
                    variant_counts.append(len(variants) / len(adopters))
        
        return np.mean(variant_counts) if variant_counts else 0.3
    
    @staticmethod
    def cultural_persistence(engine: CulturalTransmissionEngine,
                            skill_id: str = None) -> float:
        """
        How stable is cultural knowledge? (target: >0.7 for established).
        0-0.4 fragile | 0.4-0.7 developing | >0.7 established
        """
        if not engine.skill_library:
            return 0.0
        
        if skill_id:
            return engine._calculate_persistence(skill_id)
        
        # Average persistence across all skills
        persistences = [
            engine._calculate_persistence(skill_id)
            for skill_id in engine.skill_library
        ]
        
        return np.mean(persistences) if persistences else 0.5