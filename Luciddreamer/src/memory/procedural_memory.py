"""
Procedural Memory System

Stores skills, abilities, and procedural knowledge with mastery tracking.
Implements skill trees, practice effects, forgetting curves, and skill transfer.
Supports both individual skills and complex procedural sequences.
"""

import time
import uuid
import math
import json
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MasteryLevel(Enum):
    """Mastery levels for skills"""
    NOVICE = "novice"           # 0.0-0.2
    BEGINNER = "beginner"       # 0.2-0.4
    COMPETENT = "competent"     # 0.4-0.6
    PROFICIENT = "proficient"   # 0.6-0.8
    EXPERT = "expert"          # 0.8-0.95
    MASTER = "master"          # 0.95-1.0

class SkillType(Enum):
    """Types of procedural skills"""
    MOTOR = "motor"                    # Physical actions and movements
    COGNITIVE = "cognitive"            # Problem-solving and reasoning
    SOCIAL = "social"                  # Communication and interaction
    CREATIVE = "creative"              # Artistic and generative skills
    TECHNICAL = "technical"            # Tools and technologies
    STRATEGIC = "strategic"            # Planning and tactics
    LANGUAGE = "language"              # Linguistic abilities
    SURVIVAL = "survival"              # Basic survival skills

class PracticeResult(Enum):
    """Results of skill practice"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    IMPROVEMENT = "improvement"
    REGRESSION = "regression"

@dataclass
class SkillPrerequisite:
    """Prerequisite requirement for a skill"""
    skill_id: str
    required_mastery: float  # Minimum mastery level required

@dataclass
class SkillPractice:
    """Record of skill practice session"""
    practice_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    result: PracticeResult = PracticeResult.SUCCESS
    difficulty: float = 0.5  # 0-1 difficulty of the practice attempt
    time_spent: float = 0.0  # Time spent practicing in seconds
    context: str = ""  # Context/environment of practice
    performance_rating: float = 0.5  # 0-1 subjective performance rating
    feedback: str = ""  # Feedback received
    improvement: float = 0.0  # Actual mastery improvement observed

@dataclass
class SkillTransfer:
    """Knowledge transfer between related skills"""
    source_skill_id: str
    target_skill_id: str
    transfer_strength: float  # 0-1 how much source helps target
    last_applied: float = field(default_factory=time.time)
    transfer_count: int = 0

@dataclass
class Skill:
    """Individual procedural skill with mastery tracking"""

    # Core identity
    skill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    skill_type: SkillType = SkillType.MOTOR
    category: str = ""

    # Mastery tracking
    mastery_level: float = 0.0  # 0-1 continuous mastery
    innate_talent: float = 0.5  # 0-1 natural aptitude
    learning_rate: float = 0.1  # Base learning rate
    forgetting_rate: float = 0.01  # Forgetting rate per day

    # Practice history
    total_practice_time: float = 0.0  # Total time practiced in seconds
    practice_count: int = 0
    last_practice: float = 0.0
    practice_history: List[SkillPractice] = field(default_factory=list)

    # Prerequisites and dependencies
    prerequisites: List[SkillPrerequisite] = field(default_factory=list)
    child_skills: List[str] = field(default_factory=list)  # Skills that depend on this one
    transfer_skills: List[SkillTransfer] = field(default_factory=list)

    # Performance metrics
    success_rate: float = 0.0  # Recent success rate
    average_performance: float = 0.0  # Average performance rating
    peak_performance: float = 0.0  # Best performance achieved
    consistency_score: float = 0.0  # How consistent performance is

    # Metadata
    created_timestamp: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    tags: Set[str] = field(default_factory=set)
    difficulty: float = 0.5  # Inherent difficulty of skill

    def get_mastery_level_enum(self) -> MasteryLevel:
        """Get mastery level as enum"""
        if self.mastery_level < 0.2:
            return MasteryLevel.NOVICE
        elif self.mastery_level < 0.4:
            return MasteryLevel.BEGINNER
        elif self.mastery_level < 0.6:
            return MasteryLevel.COMPETENT
        elif self.mastery_level < 0.8:
            return MasteryLevel.PROFICIENT
        elif self.mastery_level < 0.95:
            return MasteryLevel.EXPERT
        else:
            return MasteryLevel.MASTER

    def get_days_since_practice(self) -> float:
        """Get days since last practice"""
        if self.last_practice == 0.0:
            return float('inf')
        return (time.time() - self.last_practice) / 86400.0

    def calculate_forgetting(self) -> float:
        """Calculate mastery loss due to forgetting"""
        days_without_practice = self.get_days_since_practice()
        if days_without_practice < 1.0:
            return 0.0

        # Exponential forgetting curve
        forgetting_factor = math.exp(-self.forgetting_rate * days_without_practice)
        return self.mastery_level * (1.0 - forgetting_factor)

    def is_prerequisite_satisfied(self, skill_id: str, mastery: float) -> bool:
        """Check if a prerequisite skill requirement is satisfied"""
        for prereq in self.prerequisites:
            if prereq.skill_id == skill_id:
                return mastery >= prereq.required_mastery
        return False

    def can_practice(self, available_skills: Dict[str, 'Skill']) -> bool:
        """Check if skill can be practiced given available skills"""
        for prereq in self.prerequisites:
            if prereq.skill_id not in available_skills:
                return False
            if available_skills[prereq.skill_id].mastery_level < prereq.required_mastery:
                return False
        return True

    def get_practice_difficulty_modifier(self) -> float:
        """Get difficulty modifier based on current mastery"""
        # Skills become easier as mastery increases
        base_difficulty = self.difficulty
        mastery_bonus = self.mastery_level * 0.5
        return max(0.1, base_difficulty - mastery_bonus)

    def update_performance_metrics(self):
        """Update performance metrics based on recent practice"""
        if not self.practice_history:
            return

        # Consider only recent practices (last 10 or last 30 days)
        recent_practices = []
        cutoff_time = time.time() - (30 * 24 * 3600)  # 30 days ago

        for practice in self.practice_history:
            if practice.timestamp >= cutoff_time:
                recent_practices.append(practice)

        if len(recent_practices) < 5:  # Not enough data
            # Use all practices if fewer than 5 recent ones
            recent_practices = self.practice_history[-10:]  # Last 10 practices

        if not recent_practices:
            return

        # Calculate success rate
        successes = sum(1 for p in recent_practices if p.result in [PracticeResult.SUCCESS, PracticeResult.IMPROVEMENT])
        self.success_rate = successes / len(recent_practices)

        # Calculate average performance
        self.average_performance = sum(p.performance_rating for p in recent_practices) / len(recent_practices)

        # Update peak performance
        self.peak_performance = max(self.peak_performance, max(p.performance_rating for p in recent_practices))

        # Calculate consistency (inverse of performance variance)
        if len(recent_practices) > 1:
            performances = [p.performance_rating for p in recent_practices]
            mean_performance = sum(performances) / len(performances)
            variance = sum((p - mean_performance) ** 2 for p in performances) / len(performances)
            self.consistency_score = max(0.0, 1.0 - math.sqrt(variance))
        else:
            self.consistency_score = 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = asdict(self)
        # Convert enums to strings
        data['skill_type'] = self.skill_type.value
        # Convert practice history
        data['practice_history'] = [asdict(p) for p in self.practice_history]
        for p_data in data['practice_history']:
            p_data['result'] = p_data['result'].value
        # Convert sets to lists
        data['tags'] = list(self.tags)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Skill':
        """Create from dictionary representation"""
        # Convert enum strings back to enums
        data['skill_type'] = SkillType[data['skill_type']]
        # Convert practice history
        practice_history = []
        for p_data in data.get('practice_history', []):
            p_data['result'] = PracticeResult[p_data['result']]
            practice_history.append(SkillPractice(**p_data))
        data['practice_history'] = practice_history
        # Convert lists back to sets
        data['tags'] = set(data.get('tags', []))
        return cls(**data)

class ProceduralMemory:
    """
    Procedural memory system for storing and managing skills and abilities.
    Implements skill trees, practice effects, and mastery tracking.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize procedural memory system

        Args:
            storage_path: Path for persistent storage
        """
        self.skills: Dict[str, Skill] = {}
        self.skill_name_index: Dict[str, str] = {}  # name -> skill_id
        self.skill_category_index: Dict[str, Set[str]] = {}  # category -> set of skill_ids
        self.skill_type_index: Dict[SkillType, Set[str]] = {}  # type -> set of skill_ids

        self.storage_path = storage_path
        self._load_skills()

        # Statistics
        self.total_practice_sessions = 0
        self.total_mastery_improvements = 0.0
        self.total_forgetting_events = 0

    def add_skill(self, name: str, description: str = "", skill_type: SkillType = SkillType.MOTOR,
                 category: str = "", difficulty: float = 0.5, innate_talent: float = 0.5,
                 learning_rate: float = 0.1, forgetting_rate: float = 0.01,
                 prerequisites: List[SkillPrerequisite] = None,
                 tags: Set[str] = None) -> str:
        """
        Add a new skill to procedural memory

        Args:
            name: Skill name
            description: Skill description
            skill_type: Type of skill
            category: Skill category
            difficulty: Inherent difficulty (0-1)
            innate_talent: Natural aptitude (0-1)
            learning_rate: Base learning rate
            forgetting_rate: Forgetting rate per day
            prerequisites: Required prerequisite skills
            tags: Descriptive tags

        Returns:
            Skill ID
        """
        skill = Skill(
            name=name,
            description=description,
            skill_type=skill_type,
            category=category,
            difficulty=difficulty,
            innate_talent=innate_talent,
            learning_rate=learning_rate,
            forgetting_rate=forgetting_rate,
            prerequisites=prerequisites or [],
            tags=tags or set()
        )

        # Check for existing skill with same name
        if name.lower() in self.skill_name_index:
            existing_id = self.skill_name_index[name.lower()]
            logger.warning(f"Skill '{name}' already exists (ID: {existing_id})")
            return existing_id

        # Store skill
        self.skills[skill.skill_id] = skill
        self.skill_name_index[name.lower()] = skill.skill_id

        # Update indexes
        if category not in self.skill_category_index:
            self.skill_category_index[category] = set()
        self.skill_category_index[category].add(skill.skill_id)

        if skill_type not in self.skill_type_index:
            self.skill_type_index[skill_type] = set()
        self.skill_type_index[skill_type].add(skill.skill_id)

        logger.debug(f"Added skill: {name} ({skill.skill_id[:8]}...)")
        return skill.skill_id

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID"""
        return self.skills.get(skill_id)

    def find_skill_by_name(self, name: str) -> Optional[Skill]:
        """Find skill by name"""
        skill_id = self.skill_name_index.get(name.lower())
        if skill_id:
            return self.get_skill(skill_id)
        return None

    def practice_skill(self, skill_id: str, result: PracticeResult = PracticeResult.SUCCESS,
                      difficulty: float = 0.5, time_spent: float = 0.0,
                      context: str = "", performance_rating: float = 0.5,
                      feedback: str = "") -> float:
        """
        Practice a skill and update mastery

        Args:
            skill_id: Skill to practice
            result: Practice result
            difficulty: Difficulty of practice attempt
            time_spent: Time spent practicing
            context: Practice context
            performance_rating: Subjective performance rating
            feedback: Feedback received

        Returns:
            Mastery improvement amount
        """
        if skill_id not in self.skills:
            logger.warning(f"Skill not found: {skill_id}")
            return 0.0

        skill = self.skills[skill_id]

        # Check if prerequisites are satisfied
        if not skill.can_practice(self.skills):
            logger.warning(f"Prerequisites not satisfied for skill: {skill.name}")
            return 0.0

        # Apply forgetting first
        forgetting_loss = skill.calculate_forgetting()
        skill.mastery_level = max(0.0, skill.mastery_level - forgetting_loss)
        if forgetting_loss > 0.01:
            self.total_forgetting_events += 1
            logger.debug(f"Applied forgetting to {skill.name}: -{forgetting_loss:.3f}")

        # Calculate mastery improvement
        improvement = self._calculate_mastery_improvement(skill, result, difficulty, time_spent, performance_rating)

        # Update skill
        old_mastery = skill.mastery_level
        skill.mastery_level = min(1.0, skill.mastery_level + improvement)
        skill.last_practice = time.time()
        skill.total_practice_time += time_spent
        skill.practice_count += 1
        skill.last_updated = time.time()

        # Record practice session
        practice = SkillPractice(
            result=result,
            difficulty=difficulty,
            time_spent=time_spent,
            context=context,
            performance_rating=performance_rating,
            feedback=feedback,
            improvement=improvement
        )
        skill.practice_history.append(practice)

        # Keep only recent practice history (last 100 sessions)
        if len(skill.practice_history) > 100:
            skill.practice_history = skill.practice_history[-100:]

        # Update performance metrics
        skill.update_performance_metrics()

        # Apply skill transfer effects
        self._apply_skill_transfer(skill_id, improvement)

        # Update statistics
        self.total_practice_sessions += 1
        self.total_mastery_improvements += improvement

        logger.debug(f"Practiced {skill.name}: {old_mastery:.3f} -> {skill.mastery_level:.3f} (+{improvement:.3f})")

        return improvement

    def _calculate_mastery_improvement(self, skill: Skill, result: PracticeResult,
                                      difficulty: float, time_spent: float,
                                      performance_rating: float) -> float:
        """Calculate mastery improvement based on practice parameters"""
        # Base improvement from time spent
        time_factor = min(1.0, time_spent / 3600.0)  # Normalize to hours, cap at 1 hour

        # Result multiplier
        result_multipliers = {
            PracticeResult.SUCCESS: 1.0,
            PracticeResult.PARTIAL_SUCCESS: 0.6,
            PracticeResult.FAILURE: 0.2,
            PracticeResult.IMPROVEMENT: 1.5,
            PracticeResult.REGRESSION: -0.3
        }
        result_multiplier = result_multipliers.get(result, 1.0)

        # Performance rating factor
        performance_factor = performance_rating

        # Difficulty factor (harder practice yields more improvement)
        difficulty_factor = 0.5 + difficulty * 0.5

        # Learning rate modified by talent and current mastery
        # Diminishing returns as mastery increases
        mastery_factor = 1.0 - (skill.mastery_level * 0.5)  # Skills become harder to improve
        talent_factor = 0.5 + skill.innate_talent * 0.5

        # Combined learning rate
        effective_learning_rate = skill.learning_rate * mastery_factor * talent_factor

        # Calculate improvement
        improvement = (effective_learning_rate * time_factor * result_multiplier *
                      performance_factor * difficulty_factor)

        # Small chance of negative improvement (bad practice sessions)
        if result == PracticeResult.FAILURE and performance_rating < 0.3:
            improvement *= -0.5

        return improvement

    def _apply_skill_transfer(self, source_skill_id: str, improvement: float):
        """Apply skill transfer effects to related skills"""
        if source_skill_id not in self.skills:
            return

        source_skill = self.skills[source_skill_id]

        for transfer in source_skill.transfer_skills:
            if transfer.target_skill_id not in self.skills:
                continue

            target_skill = self.skills[transfer.target_skill_id]
            transfer_improvement = improvement * transfer.transfer_strength * 0.3  # Reduced effect

            if transfer_improvement > 0.001:  # Only apply significant transfers
                target_skill.mastery_level = min(1.0, target_skill.mastery_level + transfer_improvement)
                target_skill.last_updated = time.time()

                transfer.last_applied = time.time()
                transfer.transfer_count += 1

                logger.debug(f"Transfer effect: {source_skill.name} -> {target_skill.name} (+{transfer_improvement:.3f})")

    def add_skill_transfer(self, source_skill_id: str, target_skill_id: str, transfer_strength: float):
        """
        Add a skill transfer relationship

        Args:
            source_skill_id: Source skill ID
            target_skill_id: Target skill ID
            transfer_strength: Transfer strength (0-1)
        """
        if source_skill_id not in self.skills or target_skill_id not in self.skills:
            return

        source_skill = self.skills[source_skill_id]

        # Check if transfer already exists
        for transfer in source_skill.transfer_skills:
            if transfer.target_skill_id == target_skill_id:
                transfer.transfer_strength = max(transfer.transfer_strength, transfer_strength)
                return

        # Add new transfer
        transfer = SkillTransfer(
            source_skill_id=source_skill_id,
            target_skill_id=target_skill_id,
            transfer_strength=transfer_strength
        )
        source_skill.transfer_skills.append(transfer)

        logger.debug(f"Added skill transfer: {source_skill_id[:8]} -> {target_skill_id[:8]} ({transfer_strength:.2f})")

    def get_skills_by_type(self, skill_type: SkillType) -> List[Skill]:
        """Get all skills of a specific type"""
        skill_ids = self.skill_type_index.get(skill_type, set())
        return [self.skills[sid] for sid in skill_ids if sid in self.skills]

    def get_skills_by_category(self, category: str) -> List[Skill]:
        """Get all skills in a specific category"""
        skill_ids = self.skill_category_index.get(category, set())
        return [self.skills[sid] for sid in skill_ids if sid in self.skills]

    def get_available_skills(self, mastered_skills: Set[str] = None) -> List[Skill]:
        """
        Get skills that can be practiced given current mastered skills

        Args:
            mastered_skills: Set of mastered skill IDs

        Returns:
            List of available skills
        """
        if mastered_skills is None:
            mastered_skills = set()

        available = []
        for skill in self.skills.values():
            # Check if all prerequisites are satisfied
            prerequisites_met = True
            for prereq in skill.prerequisites:
                if prereq.skill_id not in mastered_skills:
                    prerequisites_met = False
                    break

            if prerequisites_met:
                available.append(skill)

        return available

    def get_skill_prerequisites(self, skill_id: str) -> List[Skill]:
        """Get prerequisite skills for a given skill"""
        if skill_id not in self.skills:
            return []

        skill = self.skills[skill_id]
        prerequisites = []

        for prereq in skill.prerequisites:
            if prereq.skill_id in self.skills:
                prerequisites.append(self.skills[prereq.skill_id])

        return prerequisites

    def get_skill_dependencies(self, skill_id: str) -> List[Skill]:
        """Get skills that depend on a given skill"""
        if skill_id not in self.skills:
            return []

        skill = self.skills[skill_id]
        dependencies = []

        for dep_id in skill.child_skills:
            if dep_id in self.skills:
                dependencies.append(self.skills[dep_id])

        return dependencies

    def get_skill_tree(self, root_skill_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        Get skill tree starting from a root skill

        Args:
            root_skill_id: Root skill ID
            max_depth: Maximum depth to traverse

        Returns:
            Hierarchical representation of skill tree
        """
        if root_skill_id not in self.skills:
            return {}

        def build_subtree(skill_id: str, depth: int, visited: Set[str]) -> Dict[str, Any]:
            if depth >= max_depth or skill_id in visited or skill_id not in self.skills:
                return {}

            visited.add(skill_id)
            skill = self.skills[skill_id]

            subtree = {
                "id": skill_id,
                "name": skill.name,
                "mastery": skill.mastery_level,
                "mastery_level": skill.get_mastery_level_enum().value,
                "type": skill.skill_type.value,
                "category": skill.category,
                "prerequisites": [],
                "dependencies": []
            }

            # Add prerequisites
            for prereq in skill.prerequisites:
                prereq_skill = self.skills.get(prereq.skill_id)
                if prereq_skill:
                    subtree["prerequisites"].append({
                        "id": prereq.skill_id,
                        "name": prereq_skill.name,
                        "required_mastery": prereq.required_mastery,
                        "current_mastery": prereq_skill.mastery_level
                    })

            # Add dependencies (skills that depend on this one)
            for dep_id in skill.child_skills:
                dep_subtree = build_subtree(dep_id, depth + 1, visited.copy())
                if dep_subtree:
                    subtree["dependencies"].append(dep_subtree)

            return subtree

        return build_subtree(root_skill_id, 0, set())

    def get_top_skills(self, limit: int = 10, sort_by: str = "mastery") -> List[Skill]:
        """
        Get top skills by various metrics

        Args:
            limit: Maximum number of skills to return
            sort_by: Sorting criteria ("mastery", "practice_time", "success_rate", "recent")

        Returns:
            List of top skills
        """
        skills = list(self.skills.values())

        if sort_by == "mastery":
            skills.sort(key=lambda s: s.mastery_level, reverse=True)
        elif sort_by == "practice_time":
            skills.sort(key=lambda s: s.total_practice_time, reverse=True)
        elif sort_by == "success_rate":
            skills.sort(key=lambda s: s.success_rate, reverse=True)
        elif sort_by == "recent":
            skills.sort(key=lambda s: s.last_practice, reverse=True)
        else:
            skills.sort(key=lambda s: s.mastery_level, reverse=True)

        return skills[:limit]

    def apply_forgetting_to_all(self, days_passed: float = 1.0):
        """Apply forgetting effects to all skills"""
        current_time = time.time()

        for skill in self.skills.values():
            days_since_practice = (current_time - skill.last_practice) / 86400.0

            if days_since_practice >= days_passed:
                forgetting_loss = skill.calculate_forgetting()
                if forgetting_loss > 0.001:
                    skill.mastery_level = max(0.0, skill.mastery_level - forgetting_loss)
                    skill.last_updated = current_time
                    self.total_forgetting_events += 1

    def get_skill_recommendations(self, agent_mastery_profile: Dict[str, float] = None,
                                 goal_skills: Set[str] = None, limit: int = 5) -> List[Tuple[Skill, float]]:
        """
        Get skill practice recommendations based on current abilities and goals

        Args:
            agent_mastery_profile: Current skill mastery levels
            goal_skills: Target skills to achieve
            limit: Maximum recommendations

        Returns:
            List of (skill, recommendation_score) tuples
        """
        if agent_mastery_profile is None:
            agent_mastery_profile = {}

        if goal_skills is None:
            goal_skills = set()

        recommendations = []

        for skill in self.skills.values():
            # Calculate recommendation score
            score = 0.0

            # Current mastery factor (lower mastery = higher priority)
            mastery_factor = 1.0 - skill.mastery_level
            score += mastery_factor * 0.3

            # Goal relevance factor
            if skill.skill_id in goal_skills:
                score += 0.4
            # Check if skill is prerequisite for goal skills
            for goal_id in goal_skills:
                goal_skill = self.skills.get(goal_id)
                if goal_skill and skill.skill_id in [p.skill_id for p in goal_skill.prerequisites]:
                    score += 0.2

            # Recent practice factor (avoid over-practicing)
            days_since_practice = skill.get_days_since_practice()
            if days_since_practice > 7:  # Haven't practiced in a week
                score += 0.2
            elif days_since_practice < 1:  # Practiced recently
                score -= 0.1

            # Performance factor (practice struggling skills)
            if skill.success_rate < 0.5 and skill.practice_count > 5:
                score += 0.1

            # Prerequisite availability factor
            if skill.can_practice(self.skills):
                score += 0.2
            else:
                score -= 0.5  # Can't practice yet

            recommendations.append((skill, max(0.0, score)))

        # Sort by recommendation score
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about procedural memory"""
        if not self.skills:
            return {
                "total_skills": 0,
                "average_mastery": 0.0,
                "total_practice_time": 0.0,
                "mastery_distribution": {}
            }

        # Calculate statistics
        mastery_levels = [skill.mastery_level for skill in self.skills.values()]
        total_practice_time = sum(skill.total_practice_time for skill in self.skills.values())
        total_practice_sessions = sum(skill.practice_count for skill in self.skills.values())

        # Mastery level distribution
        mastery_distribution = {}
        for level in MasteryLevel:
            count = sum(1 for skill in self.skills.values() if skill.get_mastery_level_enum() == level)
            mastery_distribution[level.value] = count

        # Skill type distribution
        type_distribution = {}
        for skill_type in SkillType:
            count = sum(1 for skill in self.skills.values() if skill.skill_type == skill_type)
            type_distribution[skill_type.value] = count

        return {
            "total_skills": len(self.skills),
            "total_practice_sessions": self.total_practice_sessions,
            "total_practice_time": total_practice_time / 3600.0,  # Convert to hours
            "total_mastery_improvements": self.total_mastery_improvements,
            "total_forgetting_events": self.total_forgetting_events,
            "average_mastery": sum(mastery_levels) / len(mastery_levels),
            "max_mastery": max(mastery_levels),
            "mastery_distribution": mastery_distribution,
            "skill_type_distribution": type_distribution,
            "average_practice_count": total_practice_sessions / len(self.skills) if self.skills else 0.0,
            "skills_practiced_last_week": sum(1 for skill in self.skills.values() if skill.get_days_since_practice() <= 7)
        }

    def _save_skills(self):
        """Save skills to persistent storage"""
        if not self.storage_path:
            return

        try:
            data = {
                "skills": {sid: skill.to_dict() for sid, skill in self.skills.items()},
                "skill_name_index": self.skill_name_index,
                "skill_category_index": {cat: list(ids) for cat, ids in self.skill_category_index.items()},
                "skill_type_index": {stype.value: list(ids) for stype, ids in self.skill_type_index.items()},
                "statistics": {
                    "total_practice_sessions": self.total_practice_sessions,
                    "total_mastery_improvements": self.total_mastery_improvements,
                    "total_forgetting_events": self.total_forgetting_events
                }
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save procedural memory: {e}")

    def _load_skills(self):
        """Load skills from persistent storage"""
        if not self.storage_path:
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            # Load skills
            for skill_id, skill_data in data.get("skills", {}).items():
                skill = Skill.from_dict(skill_data)
                self.skills[skill_id] = skill

            # Load indexes
            self.skill_name_index = data.get("skill_name_index", {})

            # Convert category index back to sets
            category_data = data.get("skill_category_index", {})
            self.skill_category_index = {cat: set(ids) for cat, ids in category_data.items()}

            # Convert type index back to sets
            type_data = data.get("skill_type_index", {})
            self.skill_type_index = {SkillType[stype]: set(ids) for stype, ids in type_data.items()}

            # Load statistics
            stats = data.get("statistics", {})
            self.total_practice_sessions = stats.get("total_practice_sessions", 0)
            self.total_mastery_improvements = stats.get("total_mastery_improvements", 0.0)
            self.total_forgetting_events = stats.get("total_forgetting_events", 0)

            logger.info(f"Loaded {len(self.skills)} skills from procedural memory")

        except FileNotFoundError:
            logger.info("No existing procedural memory storage found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load procedural memory: {e}")

    def __len__(self) -> int:
        """Return number of stored skills"""
        return len(self.skills)