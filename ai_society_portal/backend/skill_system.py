"""
AI Society Portal - Skill System
================================
A comprehensive skill acquisition and practice system for AI characters.
Characters can develop expertise through repeated practice and experience.
"""

import json
import math
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import uuid


# ============================================================================
# SKILL CATEGORIES AND TYPES
# ============================================================================

class SkillCategory(Enum):
    """Main categories of skills"""
    COGNITIVE = "cognitive"           # Reasoning, analysis, creativity
    SOCIAL = "social"                 # Communication, empathy, leadership
    TECHNICAL = "technical"           # Coding, research, problem-solving
    CREATIVE = "creative"             # Art, writing, innovation
    METACOGNITIVE = "metacognitive"   # Self-reflection, learning strategies


class SkillType(Enum):
    """Specific skill types within categories"""
    # Cognitive skills
    LOGICAL_REASONING = "logical_reasoning"
    ANALYTICAL_THINKING = "analytical_thinking"
    PROBLEM_SOLVING = "problem_solving"
    CRITICAL_THINKING = "critical_thinking"
    MATHEMATICAL_APTITUDE = "mathematical_aptitude"

    # Social skills
    COMMUNICATION = "communication"
    EMPATHY = "empathy"
    LEADERSHIP = "leadership"
    NEGOTIATION = "negotiation"
    TEAMWORK = "teamwork"

    # Technical skills
    PROGRAMMING = "programming"
    RESEARCH = "research"
    DATA_ANALYSIS = "data_analysis"
    SYSTEM_DESIGN = "system_design"
    DEBUGGING = "debugging"

    # Creative skills
    WRITING = "writing"
    ARTISTIC_CREATION = "artistic_creation"
    INNOVATION = "innovation"
    STORYTELLING = "storytelling"
    DESIGN_THINKING = "design_thinking"

    # Metacognitive skills
    SELF_REFLECTION = "self_reflection"
    LEARNING_STRATEGIES = "learning_strategies"
    GOAL_SETTING = "goal_setting"
    ADAPTABILITY = "adaptability"
    METACOGNITION = "metacognition"


class SkillLevel(Enum):
    """Mastery levels for skills"""
    NOVICE = "novice"         # 0-20 XP
    BEGINNER = "beginner"     # 20-50 XP
    COMPETENT = "competent"   # 50-100 XP
    PROFICIENT = "proficient" # 100-200 XP
    ADVANCED = "advanced"     # 200-350 XP
    EXPERT = "expert"         # 350-500 XP
    MASTER = "master"         # 500+ XP


# Mapping of skill types to categories
SKILL_CATEGORY_MAPPING = {
    SkillType.LOGICAL_REASONING: SkillCategory.COGNITIVE,
    SkillType.ANALYTICAL_THINKING: SkillCategory.COGNITIVE,
    SkillType.PROBLEM_SOLVING: SkillCategory.COGNITIVE,
    SkillType.CRITICAL_THINKING: SkillCategory.COGNITIVE,
    SkillType.MATHEMATICAL_APTITUDE: SkillCategory.COGNITIVE,

    SkillType.COMMUNICATION: SkillCategory.SOCIAL,
    SkillType.EMPATHY: SkillCategory.SOCIAL,
    SkillType.LEADERSHIP: SkillCategory.SOCIAL,
    SkillType.NEGOTIATION: SkillCategory.SOCIAL,
    SkillType.TEAMWORK: SkillCategory.SOCIAL,

    SkillType.PROGRAMMING: SkillCategory.TECHNICAL,
    SkillType.RESEARCH: SkillCategory.TECHNICAL,
    SkillType.DATA_ANALYSIS: SkillCategory.TECHNICAL,
    SkillType.SYSTEM_DESIGN: SkillCategory.TECHNICAL,
    SkillType.DEBUGGING: SkillCategory.TECHNICAL,

    SkillType.WRITING: SkillCategory.CREATIVE,
    SkillType.ARTISTIC_CREATION: SkillCategory.CREATIVE,
    SkillType.INNOVATION: SkillCategory.CREATIVE,
    SkillType.STORYTELLING: SkillCategory.CREATIVE,
    SkillType.DESIGN_THINKING: SkillCategory.CREATIVE,

    SkillType.SELF_REFLECTION: SkillCategory.METACOGNITIVE,
    SkillType.LEARNING_STRATEGIES: SkillCategory.METACOGNITIVE,
    SkillType.GOAL_SETTING: SkillCategory.METACOGNITIVE,
    SkillType.ADAPTABILITY: SkillCategory.METACOGNITIVE,
    SkillType.METACOGNITION: SkillCategory.METACOGNITIVE,
}


# ============================================================================
# SKILL DATA STRUCTURES
# ============================================================================

@dataclass
class Skill:
    """Represents a single skill with its progression data"""
    skill_type: SkillType
    experience_points: float = 0.0
    practice_count: int = 0
    successful_practices: int = 0
    last_practiced: Optional[datetime] = None
    skill_level: SkillLevel = SkillLevel.NOVICE

    # Learning characteristics
    learning_rate: float = 1.0  # Individual learning speed modifier
    plateau_resistance: float = 1.0  # Resistance to learning plateaus
    decay_rate: float = 0.01  # How quickly skill decays without practice

    # Breakthrough mechanics
    breakthrough_required: bool = False
    breakthrough_progress: float = 0.0

    def __post_init__(self):
        if self.last_practiced is None:
            self.last_practiced = datetime.now()
        self._update_level()

    @property
    def category(self) -> SkillCategory:
        """Get the category of this skill"""
        return SKILL_CATEGORY_MAPPING.get(self.skill_type, SkillCategory.COGNITIVE)

    @property
    def level_thresholds(self) -> Dict[SkillLevel, float]:
        """XP thresholds for each level"""
        return {
            SkillLevel.NOVICE: 0,
            SkillLevel.BEGINNER: 20,
            SkillLevel.COMPETENT: 50,
            SkillLevel.PROFICIENT: 100,
            SkillLevel.ADVANCED: 200,
            SkillLevel.EXPERT: 350,
            SkillLevel.MASTER: 500
        }

    @property
    def success_rate(self) -> float:
        """Calculate current success rate based on skill level"""
        base_success = {
            SkillLevel.NOVICE: 0.3,
            SkillLevel.BEGINNER: 0.5,
            SkillLevel.COMPETENT: 0.7,
            SkillLevel.PROFICIENT: 0.8,
            SkillLevel.ADVANCED: 0.9,
            SkillLevel.EXPERT: 0.95,
            SkillLevel.MASTER: 0.98
        }
        return base_success.get(self.skill_level, 0.5)

    @property
    def next_level_xp(self) -> float:
        """Get XP needed for next level"""
        thresholds = self.level_thresholds
        current_level = self.skill_level

        # Find next level
        levels = list(thresholds.keys())
        current_index = levels.index(current_level)

        if current_index < len(levels) - 1:
            next_level = levels[current_index + 1]
            return thresholds[next_level]
        return float('inf')  # Already at max level

    @property
    def progress_to_next_level(self) -> float:
        """Get progress percentage to next level (0-1)"""
        if self.skill_level == SkillLevel.MASTER:
            return 1.0

        current_threshold = self.level_thresholds[self.skill_level]
        next_threshold = self.next_level_xp

        if next_threshold == float('inf'):
            return 1.0

        progress = (self.experience_points - current_threshold) / (next_threshold - current_threshold)
        return max(0.0, min(1.0, progress))

    def _update_level(self):
        """Update skill level based on experience points"""
        thresholds = self.level_thresholds

        for level, threshold in thresholds.items():
            if self.experience_points >= threshold:
                self.skill_level = level
            else:
                break

    def calculate_practice_success(self, difficulty: float = 0.5) -> Tuple[bool, float]:
        """Calculate if a practice attempt is successful"""
        # Base success rate from skill level
        base_success = self.success_rate

        # Modify by difficulty (0.0 = easy, 1.0 = very hard)
        difficulty_modifier = 1.0 - (difficulty * 0.5)

        # Apply plateau penalty if stuck
        plateau_penalty = 1.0
        if self.breakthrough_required:
            plateau_penalty = 0.7

        # Apply learning rate
        learning_modifier = self.learning_rate

        # Calculate final success probability
        success_probability = base_success * difficulty_modifier * plateau_penalty * learning_modifier
        success_probability = max(0.1, min(0.99, success_probability))

        # Determine success
        is_success = random.random() < success_probability

        return is_success, success_probability

    def calculate_experience_gain(self, was_successful: bool, difficulty: float = 0.5) -> float:
        """Calculate XP gained from practice"""
        base_xp = 1.0

        # Success bonus
        if was_successful:
            base_xp *= 2.0

        # Difficulty bonus
        difficulty_bonus = 0.5 + (difficulty * 1.5)
        base_xp *= difficulty_bonus

        # Diminishing returns at higher levels
        level_modifier = 1.0 / (1.0 + (self.experience_points * 0.002))
        base_xp *= level_modifier

        # Learning plateau detection
        if self.skill_level in [SkillLevel.ADVANCED, SkillLevel.EXPERT, SkillLevel.MASTER]:
            # Higher chance of hitting plateau
            if random.random() < 0.3:  # 30% chance
                self.breakthrough_required = True
                base_xp *= 0.3  # Severely reduced gains on plateau

        # Breakthrough progress
        if self.breakthrough_required:
            self.breakthrough_progress += base_xp * 0.5
            if self.breakthrough_progress >= 10.0:
                self.breakthrough_required = False
                self.breakthrough_progress = 0.0
                base_xp *= 3.0  # Breakthrough bonus!

        return max(0.1, base_xp)

    def practice(self, difficulty: float = 0.5) -> Dict[str, Any]:
        """Practice the skill and return results"""
        # Calculate success
        was_successful, success_probability = self.calculate_practice_success(difficulty)

        # Calculate experience gain
        xp_gained = self.calculate_experience_gain(was_successful, difficulty)

        # Update skill
        old_level = self.skill_level
        self.experience_points += xp_gained
        self.practice_count += 1
        if was_successful:
            self.successful_practices += 1
        self.last_practiced = datetime.now()

        # Check for level up
        self._update_level()
        leveled_up = self.skill_level != old_level

        # Apply skill decay (very slow)
        self.apply_decay()

        return {
            "skill_type": self.skill_type.value,
            "was_successful": was_successful,
            "success_probability": success_probability,
            "xp_gained": xp_gained,
            "total_xp": self.experience_points,
            "practice_count": self.practice_count,
            "success_rate": self.successful_practices / max(1, self.practice_count),
            "leveled_up": leveled_up,
            "new_level": self.skill_level.value if leveled_up else None,
            "old_level": old_level.value,
            "breakthrough_required": self.breakthrough_required,
            "breakthrough_progress": self.breakthrough_progress
        }

    def apply_decay(self):
        """Apply skill decay based on time since last practice"""
        days_since_practice = (datetime.now() - self.last_practiced).days

        if days_since_practice > 7:  # Only decay after a week of no practice
            decay_amount = self.decay_rate * days_since_practice * 0.1
            self.experience_points = max(0, self.experience_points - decay_amount)
            self._update_level()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "skill_type": self.skill_type.value,
            "experience_points": self.experience_points,
            "practice_count": self.practice_count,
            "successful_practices": self.successful_practices,
            "last_practiced": self.last_practiced.isoformat() if self.last_practiced else None,
            "skill_level": self.skill_level.value,
            "learning_rate": self.learning_rate,
            "plateau_resistance": self.plateau_resistance,
            "decay_rate": self.decay_rate,
            "breakthrough_required": self.breakthrough_required,
            "breakthrough_progress": self.breakthrough_progress,
            "category": self.category.value,
            "success_rate": self.success_rate,
            "next_level_xp": self.next_level_xp,
            "progress_to_next_level": self.progress_to_next_level
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Skill':
        """Create from dictionary"""
        # Handle enum conversions
        data["skill_type"] = SkillType(data["skill_type"])
        data["skill_level"] = SkillLevel(data["skill_level"])

        # Handle datetime
        if data.get("last_practiced"):
            data["last_practiced"] = datetime.fromisoformat(data["last_practiced"])

        skill = cls(**{k: v for k, v in data.items() if k != "category"})
        return skill


@dataclass
class PracticeSession:
    """Represents a practice session for tracking progress"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    character_id: str = ""
    skill_type: SkillType = SkillType.PROBLEM_SOLVING
    session_start: datetime = field(default_factory=datetime.now)
    session_end: Optional[datetime] = None
    duration_minutes: int = 30
    difficulty: float = 0.5
    results: List[Dict[str, Any]] = field(default_factory=list)

    # Session outcomes
    total_xp_gained: float = 0.0
    successful_practices: int = 0
    total_practices: int = 0
    breakthrough_achieved: bool = False

    def start_session(self):
        """Mark the session as started"""
        self.session_start = datetime.now()

    def end_session(self):
        """Mark the session as ended"""
        self.session_end = datetime.now()

    def add_practice_result(self, result: Dict[str, Any]):
        """Add a practice result to this session"""
        self.results.append(result)
        self.total_xp_gained += result.get("xp_gained", 0)
        if result.get("was_successful", False):
            self.successful_practices += 1
        self.total_practices += 1

        if result.get("breakthrough_achieved", False):
            self.breakthrough_achieved = True

    @property
    def session_success_rate(self) -> float:
        """Calculate success rate for this session"""
        if self.total_practices == 0:
            return 0.0
        return self.successful_practices / self.total_practices

    @property
    def xp_per_minute(self) -> float:
        """Calculate XP gained per minute"""
        actual_duration = (self.session_end - self.session_start).total_seconds() / 60 if self.session_end else self.duration_minutes
        if actual_duration <= 0:
            return 0.0
        return self.total_xp_gained / actual_duration

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "character_id": self.character_id,
            "skill_type": self.skill_type.value,
            "session_start": self.session_start.isoformat(),
            "session_end": self.session_end.isoformat() if self.session_end else None,
            "duration_minutes": self.duration_minutes,
            "difficulty": self.difficulty,
            "total_xp_gained": self.total_xp_gained,
            "successful_practices": self.successful_practices,
            "total_practices": self.total_practices,
            "session_success_rate": self.session_success_rate,
            "xp_per_minute": self.xp_per_minute,
            "breakthrough_achieved": self.breakthrough_achieved,
            "practice_count": len(self.results)
        }


@dataclass
class SkillBadge:
    """Represents earned badges for skill achievements"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    character_id: str = ""
    skill_type: SkillType = SkillType.PROBLEM_SOLVING
    badge_type: str = ""  # milestone, streak, breakthrough, mastery
    badge_name: str = ""
    description: str = ""
    earned_at: datetime = field(default_factory=datetime.now)
    requirements_met: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "character_id": self.character_id,
            "skill_type": self.skill_type.value,
            "badge_type": self.badge_type,
            "badge_name": self.badge_name,
            "description": self.description,
            "earned_at": self.earned_at.isoformat(),
            "requirements_met": self.requirements_met
        }


# ============================================================================
# SKILL SYSTEM MANAGER
# ============================================================================

class SkillSystem:
    """Manages skill acquisition and practice for characters"""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.character_skills: Dict[str, Dict[SkillType, Skill]] = {}
        self.practice_history: Dict[str, List[PracticeSession]] = {}
        self.earned_badges: Dict[str, List[SkillBadge]] = {}

    def get_character_skills(self, character_id: str) -> Dict[SkillType, Skill]:
        """Get all skills for a character"""
        if character_id not in self.character_skills:
            self.character_skills[character_id] = {}
        return self.character_skills[character_id]

    def get_skill(self, character_id: str, skill_type: SkillType) -> Optional[Skill]:
        """Get a specific skill for a character"""
        skills = self.get_character_skills(character_id)
        return skills.get(skill_type)

    def add_skill(self, character_id: str, skill_type: SkillType,
                  learning_rate: float = 1.0, plateau_resistance: float = 1.0) -> Skill:
        """Add a new skill for a character"""
        skills = self.get_character_skills(character_id)

        if skill_type not in skills:
            skill = Skill(
                skill_type=skill_type,
                learning_rate=learning_rate,
                plateau_resistance=plateau_resistance
            )
            skills[skill_type] = skill

        return skills[skill_type]

    def practice_skill(self, character_id: str, skill_type: SkillType,
                      difficulty: float = 0.5, duration_minutes: int = 30) -> Dict[str, Any]:
        """Have a character practice a skill"""
        skills = self.get_character_skills(character_id)

        # Add skill if it doesn't exist
        if skill_type not in skills:
            self.add_skill(character_id, skill_type)

        skill = skills[skill_type]

        # Create practice session
        session = PracticeSession(
            character_id=character_id,
            skill_type=skill_type,
            duration_minutes=duration_minutes,
            difficulty=difficulty
        )
        session.start_session()

        # Determine number of practice attempts based on duration
        practice_attempts = max(1, duration_minutes // 10)  # One attempt per 10 minutes

        results = []
        for _ in range(practice_attempts):
            result = skill.practice(difficulty)
            results.append(result)
            session.add_practice_result(result)

        session.end_session()

        # Store practice session
        if character_id not in self.practice_history:
            self.practice_history[character_id] = []
        self.practice_history[character_id].append(session)

        # Check for badge achievements
        new_badges = self._check_badge_achievements(character_id, skill_type)

        # Limit practice history
        if len(self.practice_history[character_id]) > 100:
            self.practice_history[character_id] = self.practice_history[character_id][-50:]

        return {
            "session_id": session.id,
            "skill_type": skill_type.value,
            "character_id": character_id,
            "practice_attempts": practice_attempts,
            "session_results": {
                "total_xp_gained": session.total_xp_gained,
                "successful_practices": session.successful_practices,
                "total_practices": session.total_practices,
                "session_success_rate": session.session_success_rate,
                "xp_per_minute": session.xp_per_minute,
                "breakthrough_achieved": session.breakthrough_achieved
            },
            "skill_after_practice": skill.to_dict(),
            "new_badges": [badge.to_dict() for badge in new_badges]
        }

    def _check_badge_achievements(self, character_id: str, skill_type: SkillType) -> List[SkillBadge]:
        """Check if character earned any new badges"""
        skill = self.get_skill(character_id, skill_type)
        if not skill:
            return []

        new_badges = []

        # Initialize badges list for character
        if character_id not in self.earned_badges:
            self.earned_badges[character_id] = []

        existing_badges = {badge.badge_name for badge in self.earned_badges[character_id]}

        # Check for milestone badges (level achievements)
        milestone_badges = {
            SkillLevel.BEGINNER: f"Novice {skill_type.value.title()}",
            SkillLevel.COMPETENT: f"Competent {skill_type.value.title()}",
            SkillLevel.PROFICIENT: f"Proficient {skill_type.value.title()}",
            SkillLevel.ADVANCED: f"Advanced {skill_type.value.title()}",
            SkillLevel.EXPERT: f"Expert {skill_type.value.title()}",
            SkillLevel.MASTER: f"Master {skill_type.value.title()}"
        }

        if skill.skill_level in milestone_badges:
            badge_name = milestone_badges[skill.skill_level]
            if badge_name not in existing_badges:
                badge = SkillBadge(
                    character_id=character_id,
                    skill_type=skill_type,
                    badge_type="milestone",
                    badge_name=badge_name,
                    description=f"Reached {skill.skill_level.value} level in {skill_type.value}",
                    requirements_met={"level": skill.skill_level.value, "xp": skill.experience_points}
                )
                new_badges.append(badge)
                self.earned_badges[character_id].append(badge)

        # Check for streak badges
        recent_sessions = [s for s in self.practice_history.get(character_id, [])
                          if s.skill_type == skill_type and
                          (datetime.now() - s.session_start).days <= 7]

        if len(recent_sessions) >= 5 and f"Practitioner {skill_type.value.title()}" not in existing_badges:
            badge = SkillBadge(
                character_id=character_id,
                skill_type=skill_type,
                badge_type="streak",
                badge_name=f"Practitioner {skill_type.value.title()}",
                description=f"Practiced {skill_type.value} 5+ times in the last week",
                requirements_met={"recent_sessions": len(recent_sessions)}
            )
            new_badges.append(badge)
            self.earned_badges[character_id].append(badge)

        # Check for breakthrough badge
        if skill.breakthrough_required and f"Breakthrough Ready {skill_type.value.title()}" not in existing_badges:
            badge = SkillBadge(
                character_id=character_id,
                skill_type=skill_type,
                badge_type="breakthrough",
                badge_name=f"Breakthrough Ready {skill_type.value.title()}",
                description=f"Ready for a breakthrough in {skill_type.value}",
                requirements_met={"breakthrough_progress": skill.breakthrough_progress}
            )
            new_badges.append(badge)
            self.earned_badges[character_id].append(badge)

        return new_badges

    def get_skill_progress(self, character_id: str, skill_type: SkillType) -> Dict[str, Any]:
        """Get detailed progress information for a skill"""
        skill = self.get_skill(character_id, skill_type)
        if not skill:
            return {"error": "Skill not found"}

        # Get practice history for this skill
        practice_sessions = [s for s in self.practice_history.get(character_id, [])
                           if s.skill_type == skill_type]

        # Calculate trends
        recent_sessions = practice_sessions[-10:] if practice_sessions else []
        avg_success_rate = sum(s.session_success_rate for s in recent_sessions) / len(recent_sessions) if recent_sessions else 0
        avg_xp_per_minute = sum(s.xp_per_minute for s in recent_sessions) / len(recent_sessions) if recent_sessions else 0

        # Get badges for this skill
        skill_badges = [b for b in self.earned_badges.get(character_id, []) if b.skill_type == skill_type]

        return {
            "skill": skill.to_dict(),
            "practice_history": {
                "total_sessions": len(practice_sessions),
                "recent_sessions": len(recent_sessions),
                "average_success_rate": avg_success_rate,
                "average_xp_per_minute": avg_xp_per_minute,
                "last_practice": practice_sessions[-1].session_start.isoformat() if practice_sessions else None
            },
            "badges": [badge.to_dict() for badge in skill_badges],
            "recommendations": self._get_practice_recommendations(character_id, skill_type)
        }

    def _get_practice_recommendations(self, character_id: str, skill_type: SkillType) -> List[str]:
        """Get personalized practice recommendations"""
        skill = self.get_skill(character_id, skill_type)
        if not skill:
            return []

        recommendations = []

        # Level-based recommendations
        if skill.skill_level == SkillLevel.NOVICE:
            recommendations.append("Focus on basic exercises to build foundation")
            recommendations.append("Practice with lower difficulty (0.2-0.4)")
        elif skill.skill_level == SkillLevel.BEGINNER:
            recommendations.append("Gradually increase difficulty as you improve")
            recommendations.append("Practice consistently to build momentum")
        elif skill.skill_level == SkillLevel.COMPETENT:
            recommendations.append("Challenge yourself with moderate difficulty (0.5-0.7)")
            recommendations.append("Try different approaches to the same problems")
        elif skill.skill_level in [SkillLevel.PROFICIENT, SkillLevel.ADVANCED]:
            recommendations.append("Work on complex, challenging problems")
            recommendations.append("Teach others to deepen your understanding")
        elif skill.skill_level == SkillLevel.EXPERT:
            recommendations.append("Push your boundaries with expert-level challenges")
            recommendations.append("Innovate and create new techniques")
        elif skill.skill_level == SkillLevel.MASTER:
            recommendations.append("Mentor others and share your expertise")
            recommendations.append("Explore interdisciplinary applications")

        # Plateau-specific recommendations
        if skill.breakthrough_required:
            recommendations.append("🚀 BREAKTHROUGH NEEDED: Try a completely new approach")
            recommendations.append("Take a break and return with fresh perspective")
            recommendations.append("Collaborate with others to gain new insights")

        # Practice frequency recommendations
        days_since_practice = (datetime.now() - skill.last_practiced).days
        if days_since_practice > 7:
            recommendations.append("⚠️ SKILL DECAY: Practice soon to maintain your level")
        elif days_since_practice > 3:
            recommendations.append("📅 Practice soon to keep your skills sharp")

        return recommendations

    def get_all_skills_overview(self, character_id: str) -> Dict[str, Any]:
        """Get overview of all skills for a character"""
        skills = self.get_character_skills(character_id)

        if not skills:
            return {"message": "No skills developed yet"}

        # Group by category
        by_category = {}
        for skill_type, skill in skills.items():
            category = skill.category.value
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(skill.to_dict())

        # Calculate overall stats
        total_xp = sum(skill.experience_points for skill in skills.values())
        avg_level = sum(self._level_to_number(skill.skill_level) for skill in skills.values()) / len(skills)

        # Get top skills
        sorted_skills = sorted(skills.values(), key=lambda s: s.experience_points, reverse=True)
        top_skills = sorted_skills[:5]

        # Get all badges
        all_badges = self.earned_badges.get(character_id, [])

        return {
            "character_id": character_id,
            "total_skills": len(skills),
            "total_experience_points": total_xp,
            "average_skill_level": round(avg_level, 2),
            "skills_by_category": by_category,
            "top_skills": [skill.to_dict() for skill in top_skills],
            "total_badges": len(all_badges),
            "recent_badges": [badge.to_dict() for badge in all_badges[-5:]],
            "overall_mastery_level": self._calculate_overall_mastery(avg_level)
        }

    def _level_to_number(self, level: SkillLevel) -> int:
        """Convert skill level to numeric value"""
        level_mapping = {
            SkillLevel.NOVICE: 0,
            SkillLevel.BEGINNER: 1,
            SkillLevel.COMPETENT: 2,
            SkillLevel.PROFICIENT: 3,
            SkillLevel.ADVANCED: 4,
            SkillLevel.EXPERT: 5,
            SkillLevel.MASTER: 6
        }
        return level_mapping.get(level, 0)

    def _calculate_overall_mastery(self, avg_level: float) -> str:
        """Calculate overall mastery level based on average skill level"""
        if avg_level >= 5.5:
            return "Grand Master"
        elif avg_level >= 4.5:
            return "Expert"
        elif avg_level >= 3.5:
            return "Advanced"
        elif avg_level >= 2.5:
            return "Proficient"
        elif avg_level >= 1.5:
            return "Competent"
        elif avg_level >= 0.5:
            return "Beginner"
        else:
            return "Novice"

    def conduct_skill_workshop(self, character_ids: List[str], skill_type: SkillType,
                             duration_minutes: int = 60) -> Dict[str, Any]:
        """Conduct a group skill workshop for multiple characters"""
        workshop_results = {
            "workshop_id": str(uuid.uuid4()),
            "skill_type": skill_type.value,
            "participants": character_ids,
            "duration_minutes": duration_minutes,
            "individual_results": {},
            "group_benefits": {},
            "total_xp_earned": 0.0
        }

        # Individual practice
        for character_id in character_ids:
            result = self.practice_skill(character_id, skill_type, difficulty=0.6, duration_minutes=duration_minutes)
            workshop_results["individual_results"][character_id] = result
            workshop_results["total_xp_earned"] += result["session_results"]["total_xp_gained"]

        # Group benefits (collaborative learning bonus)
        collaboration_bonus = 0.1 * len(character_ids)  # 10% bonus per participant
        for character_id in character_ids:
            skill = self.get_skill(character_id, skill_type)
            if skill:
                bonus_xp = workshop_results["individual_results"][character_id]["session_results"]["total_xp_gained"] * collaboration_bonus
                skill.experience_points += bonus_xp
                skill._update_level()

        workshop_results["group_benefits"] = {
            "collaboration_bonus_percent": collaboration_bonus * 100,
            "total_bonus_xp": workshop_results["total_xp_earned"] * collaboration_bonus
        }

        return workshop_results

    def save_to_disk(self):
        """Save skill data to disk"""
        import os
        os.makedirs(self.storage_path, exist_ok=True)

        # Save character skills
        skills_data = {}
        for character_id, skills in self.character_skills.items():
            skills_data[character_id] = {
                skill_type.value: skill.to_dict()
                for skill_type, skill in skills.items()
            }

        with open(os.path.join(self.storage_path, "character_skills.json"), "w") as f:
            json.dump(skills_data, f, indent=2)

        # Save practice history
        practice_data = {}
        for character_id, sessions in self.practice_history.items():
            practice_data[character_id] = [session.to_dict() for session in sessions]

        with open(os.path.join(self.storage_path, "practice_history.json"), "w") as f:
            json.dump(practice_data, f, indent=2)

        # Save badges
        badges_data = {}
        for character_id, badges in self.earned_badges.items():
            badges_data[character_id] = [badge.to_dict() for badge in badges]

        with open(os.path.join(self.storage_path, "earned_badges.json"), "w") as f:
            json.dump(badges_data, f, indent=2)

    def load_from_disk(self):
        """Load skill data from disk"""
        import os

        skills_file = os.path.join(self.storage_path, "character_skills.json")
        practice_file = os.path.join(self.storage_path, "practice_history.json")
        badges_file = os.path.join(self.storage_path, "earned_badges.json")

        # Load character skills
        if os.path.exists(skills_file):
            with open(skills_file, "r") as f:
                skills_data = json.load(f)

            for character_id, skills_dict in skills_data.items():
                self.character_skills[character_id] = {}
                for skill_type_str, skill_dict in skills_dict.items():
                    skill = Skill.from_dict(skill_dict)
                    self.character_skills[character_id][skill.skill_type] = skill

        # Load practice history
        if os.path.exists(practice_file):
            with open(practice_file, "r") as f:
                practice_data = json.load(f)

            for character_id, sessions_list in practice_data.items():
                self.practice_history[character_id] = []
                for session_dict in sessions_list:
                    session = PracticeSession(
                        id=session_dict["id"],
                        character_id=session_dict["character_id"],
                        skill_type=SkillType(session_dict["skill_type"]),
                        session_start=datetime.fromisoformat(session_dict["session_start"]),
                        session_end=datetime.fromisoformat(session_dict["session_end"]) if session_dict["session_end"] else None,
                        duration_minutes=session_dict["duration_minutes"],
                        difficulty=session_dict["difficulty"]
                    )
                    # Note: Individual practice results would need to be reconstructed
                    self.practice_history[character_id].append(session)

        # Load badges
        if os.path.exists(badges_file):
            with open(badges_file, "r") as f:
                badges_data = json.load(f)

            for character_id, badges_list in badges_data.items():
                self.earned_badges[character_id] = []
                for badge_dict in badges_list:
                    badge = SkillBadge(
                        id=badge_dict["id"],
                        character_id=badge_dict["character_id"],
                        skill_type=SkillType(badge_dict["skill_type"]),
                        badge_type=badge_dict["badge_type"],
                        badge_name=badge_dict["badge_name"],
                        description=badge_dict["description"],
                        earned_at=datetime.fromisoformat(badge_dict["earned_at"]),
                        requirements_met=badge_dict["requirements_met"]
                    )
                    self.earned_badges[character_id].append(badge)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_available_skills() -> Dict[str, List[str]]:
    """Get all available skills grouped by category"""
    skills_by_category = {}

    for skill_type, category in SKILL_CATEGORY_MAPPING.items():
        category_name = category.value
        if category_name not in skills_by_category:
            skills_by_category[category_name] = []
        skills_by_category[category_name].append(skill_type.value)

    return skills_by_category


def recommend_starter_skills(specialization: str) -> List[SkillType]:
    """Recommend starter skills based on character specialization"""
    recommendations = {
        "scientist": [SkillType.RESEARCH, SkillType.ANALYTICAL_THINKING, SkillType.PROBLEM_SOLVING],
        "artist": [SkillType.ARTISTIC_CREATION, SkillType.INNOVATION, SkillType.STORYTELLING],
        "programmer": [SkillType.PROGRAMMING, SkillType.LOGICAL_REASONING, SkillType.DEBUGGING],
        "philosopher": [SkillType.CRITICAL_THINKING, SkillType.LOGICAL_REASONING, SkillType.COMMUNICATION],
        "writer": [SkillType.WRITING, SkillType.STORYTELLING, SkillType.INNOVATION],
        "teacher": [SkillType.COMMUNICATION, SkillType.EMPATHY, SkillType.LEADERSHIP],
        "leader": [SkillType.LEADERSHIP, SkillType.COMMUNICATION, SkillType.NEGOTIATION],
        "researcher": [SkillType.RESEARCH, SkillType.DATA_ANALYSIS, SkillType.ANALYTICAL_THINKING]
    }

    # Find matching specialization (case insensitive)
    for key, skills in recommendations.items():
        if key.lower() in specialization.lower():
            return skills

    # Default recommendations
    return [SkillType.PROBLEM_SOLVING, SkillType.COMMUNICATION, SkillType.LEARNING_STRATEGIES]