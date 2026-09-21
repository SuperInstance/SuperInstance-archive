#!/usr/bin/env python3
"""
Advanced Character Skill Trees and Specialization System

This module provides comprehensive skill tree development for Luciddreamer characters,
including skill progression, specialization paths, mastery levels, and cross-skill synergies.
"""

import json
import uuid
import math
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# SKILL TREE ARCHITECTURE
# ============================================================================

class SkillCategory(Enum):
    """Categories of skills"""
    COGNITIVE = "cognitive"
    SOCIAL = "social"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    EMOTIONAL = "emotional"
    PHYSICAL = "physical"
    LEADERSHIP = "leadership"
    WISDOM = "wisdom"

class MasteryLevel(Enum):
    """Mastery levels with visual indicators"""
    NOVICE = "Novice"
    APPRENTICE = "Apprentice"
    JOURNEYMAN = "Journeyman"
    EXPERT = "Expert"
    MASTER = "Master"
    GRANDMASTER = "Grandmaster"

@dataclass
class SkillPrerequisite:
    """Skill prerequisite with required level"""
    skill_name: str
    required_level: float
    optional: bool = False

@dataclass
class SkillSynergy:
    """Synergy between skills that provides bonuses"""
    primary_skill: str
    secondary_skill: str
    bonus_type: str  # "experience", "level", "success_rate"
    bonus_value: float
    activation_level: float

@dataclass
class SkillMilestone:
    """Milestone achievements for skill progression"""
    level: float
    title: str
    description: str
    unlocks: List[str]
    rewards: Dict[str, Any]

@dataclass
class AdvancedSkill:
    """Enhanced skill with full progression system"""
    name: str
    category: SkillCategory
    description: str
    current_level: float = 0.0
    max_level: float = 100.0
    experience_points: int = 0
    experience_to_next_level: int = 100

    # Skill progression
    prerequisites: List[SkillPrerequisite] = field(default_factory=list)
    synergies: List[SkillSynergy] = field(default_factory=list)
    milestones: List[SkillMilestone] = field(default_factory=list)

    # Specializations
    specializations: Dict[str, float] = field(default_factory=dict)  # name -> level
    current_specialization: Optional[str] = None

    # Usage tracking
    total_uses: int = 0
    successful_uses: int = 0
    last_used: Optional[datetime] = None

    # Learning factors
    learning_rate: float = 1.0  # Multiplier for experience gain
    difficulty: float = 1.0     # Base difficulty (higher = harder to level)

    # Metadata
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def mastery_level(self) -> MasteryLevel:
        """Get current mastery level based on skill level"""
        level_percentage = self.current_level / self.max_level

        if level_percentage >= 0.95:
            return MasteryLevel.GRANDMASTER
        elif level_percentage >= 0.80:
            return MasteryLevel.MASTER
        elif level_percentage >= 0.60:
            return MasteryLevel.EXPERT
        elif level_percentage >= 0.40:
            return MasteryLevel.JOURNEYMAN
        elif level_percentage >= 0.20:
            return MasteryLevel.APPRENTICE
        else:
            return MasteryLevel.NOVICE

    @property
    def success_rate(self) -> float:
        """Calculate success rate based on level and experience"""
        base_rate = self.current_level / self.max_level
        experience_bonus = math.log(max(1, self.total_uses)) * 0.01
        return min(0.95, base_rate + experience_bonus)

    def add_experience(self, amount: int) -> Tuple[bool, float]:
        """Add experience and return (leveled_up, new_level)"""
        self.experience_points += int(amount * self.learning_rate)
        self.total_uses += 1
        self.last_used = datetime.now()

        leveled_up = False
        old_level = self.current_level

        # Calculate new level based on experience
        while self.experience_points >= self.experience_to_next_level and self.current_level < self.max_level:
            self.experience_points -= self.experience_to_next_level
            self.current_level = min(self.max_level, self.current_level + 1.0)
            self.experience_to_next_level = int(self._calculate_next_level_exp())
            leveled_up = True

            # Check milestones
            self._check_milestones()

        self.updated_at = datetime.now()

        if leveled_up:
            logger.info(f"Skill {self.name} leveled up from {old_level:.1f} to {self.current_level:.1f}")

        return (leveled_up, self.current_level)

    def _calculate_next_level_exp(self) -> int:
        """Calculate experience needed for next level using exponential scaling"""
        base_exp = 100
        level_factor = math.pow(self.current_level + 1, self.difficulty * 1.5)
        return int(base_exp * level_factor)

    def _check_milestones(self):
        """Check if any milestones have been reached"""
        for milestone in self.milestones:
            if self.current_level >= milestone.level and milestone.title not in self.tags:
                self.tags.add(milestone.title)
                logger.info(f"Milestone reached: {milestone.title} for skill {self.name}")

    def can_specialize_in(self, specialization: str) -> bool:
        """Check if character can specialize in a specific area"""
        return self.current_level >= 20.0 and specialization not in self.specializations

    def add_specialization(self, name: str, initial_level: float = 1.0):
        """Add a specialization to this skill"""
        if self.can_specialize_in(name):
            self.specializations[name] = min(10.0, initial_level)
            self.updated_at = datetime.now()
            return True
        return False

    def practice_specialization(self, name: str, success: bool) -> float:
        """Practice a specific specialization"""
        if name not in self.specializations:
            return 0.0

        # Calculate improvement
        base_improvement = 0.1 if success else 0.05
        synergy_bonus = self._calculate_synergy_bonus(name)
        total_improvement = base_improvement * (1.0 + synergy_bonus)

        # Update specialization level
        current = self.specializations[name]
        new_level = min(10.0, current + total_improvement)
        self.specializations[name] = new_level
        self.updated_at = datetime.now()

        return new_level - current

    def _calculate_synergy_bonus(self, specialization: str) -> float:
        """Calculate synergy bonus from related skills"""
        total_bonus = 0.0

        for synergy in self.synergies:
            if synergy.secondary_skill == specialization:
                # This would reference the actual skill level in a full implementation
                # For now, we'll use a simplified calculation
                total_bonus += synergy.bonus_value * 0.1

        return total_bonus

@dataclass
class SkillTree:
    """Complete skill tree with interconnected skills"""
    name: str
    description: str
    root_skills: List[str] = field(default_factory=list)
    skills: Dict[str, AdvancedSkill] = field(default_factory=dict)
    connections: Dict[str, List[str]] = field(default_factory=dict)  # skill -> list of connected skills

    # Tree progression
    total_points_spent: int = 0
    available_points: int = 0
    unlock_requirements: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Mastery achievements
    completed_paths: List[str] = field(default_factory=list)
    mastery_bonuses: Dict[str, float] = field(default_factory=dict)

    # Metadata
    tree_type: str = "general"
    difficulty_modifier: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)

    def add_skill(self, skill: AdvancedSkill, parent_skills: List[str] = None):
        """Add a skill to the tree"""
        self.skills[skill.name] = skill

        if parent_skills:
            self.connections[skill.name] = parent_skills
            for parent in parent_skills:
                if parent not in self.connections:
                    self.connections[parent] = []
                if skill.name not in self.connections[parent]:
                    self.connections[parent].append(skill.name)
        elif not self.root_skills:
            self.root_skills.append(skill.name)

    def can_unlock_skill(self, skill_name: str) -> Tuple[bool, str]:
        """Check if a skill can be unlocked"""
        if skill_name not in self.skills:
            return False, "Skill not found in tree"

        skill = self.skills[skill_name]

        # Check prerequisites
        for prereq in skill.prerequisites:
            if not prereq.optional:
                if prereq.skill_name not in self.skills:
                    return False, f"Missing prerequisite: {prereq.skill_name}"
                elif self.skills[prereq.skill_name].current_level < prereq.required_level:
                    return False, f"Prerequisite {prereq.skill_name} needs level {prereq.required_level}"

        # Check point requirements
        if skill_name in self.unlock_requirements:
            reqs = self.unlock_requirements[skill_name]
            if reqs.get('points', 0) > self.available_points:
                return False, f"Need {reqs['points']} skill points"

        return True, "Can unlock"

    def unlock_skill(self, skill_name: str, point_cost: int = 1) -> bool:
        """Unlock a skill using skill points"""
        can_unlock, reason = self.can_unlock_skill(skill_name)

        if not can_unlock:
            logger.warning(f"Cannot unlock {skill_name}: {reason}")
            return False

        if self.available_points < point_cost:
            logger.warning(f"Insufficient skill points for {skill_name}")
            return False

        # Deduct points and unlock skill
        self.available_points -= point_cost
        self.total_points_spent += point_cost

        # Initialize skill if it's at level 0
        if self.skills[skill_name].current_level == 0:
            self.skills[skill_name].current_level = 1.0

        logger.info(f"Unlocked skill: {skill_name}")
        return True

    def get_skill_progression_path(self, skill_name: str) -> List[str]:
        """Get the progression path to unlock a skill"""
        if skill_name not in self.skills:
            return []

        path = []
        visited = set()

        def dfs(current_skill: str):
            if current_skill in visited or current_skill not in self.skills:
                return

            visited.add(current_skill)

            # Add prerequisites first
            for prereq in self.skills[current_skill].prerequisites:
                if not prereq.optional:
                    dfs(prereq.skill_name)
                    if prereq.skill_name not in path:
                        path.append(prereq.skill_name)

            # Add current skill
            if current_skill not in path:
                path.append(current_skill)

        dfs(skill_name)
        return path

    def calculate_mastery_level(self) -> float:
        """Calculate overall mastery level of the tree"""
        if not self.skills:
            return 0.0

        total_levels = sum(skill.current_level for skill in self.skills.values())
        max_possible = sum(skill.max_level for skill in self.skills.values())

        return (total_levels / max_possible) * 100.0

    def get_tree_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the skill tree"""
        total_skills = len(self.skills)
        mastered_skills = sum(1 for skill in self.skills.values()
                            if skill.mastery_level in [MasteryLevel.MASTER, MasteryLevel.GRANDMASTER])

        total_specializations = sum(len(skill.specializations) for skill in self.skills.values())

        return {
            'tree_name': self.name,
            'total_skills': total_skills,
            'mastered_skills': mastered_skills,
            'mastery_percentage': (mastered_skills / max(1, total_skills)) * 100,
            'total_specializations': total_specializations,
            'available_points': self.available_points,
            'total_points_spent': self.total_points_spent,
            'overall_mastery': self.calculate_mastery_level(),
            'completed_paths': len(self.completed_paths),
            'created_at': self.created_at.isoformat()
        }

# ============================================================================
# PREDEFINED SKILL TREES FOR ARCHETYPES
# ============================================================================

class ArchetypeSkillTrees:
    """Predefined skill trees for each character archetype"""

    @staticmethod
    def create_innovator_tree() -> SkillTree:
        """Create skill tree for The Innovator archetype"""
        tree = SkillTree(
            name="The Innovator's Path",
            description="Master the arts of discovery, creativity, and groundbreaking innovation",
            tree_type="innovator",
            difficulty_modifier=0.9  # Slightly easier progression
        )

        # Core Skills
        creativity = AdvancedSkill(
            name="Creative Thinking",
            category=SkillCategory.CREATIVE,
            description="Generate novel ideas and think outside conventional boundaries",
            learning_rate=1.2,
            difficulty=0.8,
            tags={"core", "innovation"}
        )
        creativity.add_specialization("divergent_thinking", 3.0)
        creativity.add_specialization("conceptual_blending", 2.0)

        problem_solving = AdvancedSkill(
            name="Problem Solving",
            category=SkillCategory.COGNITIVE,
            description="Analyze complex problems and develop effective solutions",
            learning_rate=1.1,
            difficulty=0.9,
            tags={"core", "analytical"}
        )

        research = AdvancedSkill(
            name="Research Methodology",
            category=SkillCategory.TECHNICAL,
            description="Conduct systematic research and gather meaningful insights",
            learning_rate=1.0,
            difficulty=1.0,
            tags={"core", "methodical"}
        )

        # Specialized Skills
        innovation = AdvancedSkill(
            name="Innovation Management",
            category=SkillCategory.LEADERSHIP,
            description="Lead innovation initiatives and manage creative teams",
            learning_rate=0.9,
            difficulty=1.1,
            tags={"advanced", "leadership"}
        )

        systems_thinking = AdvancedSkill(
            name="Systems Thinking",
            category=SkillCategory.COGNITIVE,
            description="Understand complex systems and their interconnections",
            learning_rate=0.8,
            difficulty=1.2,
            tags={"advanced", "analytical"}
        )

        # Add prerequisites
        innovation.prerequisites = [
            SkillPrerequisite("Creative Thinking", 15.0),
            SkillPrerequisite("Problem Solving", 10.0)
        ]

        systems_thinking.prerequisites = [
            SkillPrerequisite("Problem Solving", 20.0),
            SkillPrerequisite("Research Methodology", 15.0)
        ]

        # Add synergies
        creativity.synergies = [
            SkillSynergy("Creative Thinking", "Innovation Management", "experience", 1.5, 10.0),
            SkillSynergy("Creative Thinking", "Systems Thinking", "level", 0.2, 15.0)
        ]

        # Add milestones
        creativity.milestones = [
            SkillMilestone(10.0, "Creative Spark", "First signs of creative genius",
                         ["basic_ideation"], {"inspiration_bonus": 0.1}),
            SkillMilestone(25.0, "Creative Flow", "Consistent creative output",
                         ["advanced_ideation"], {"flow_state_chance": 0.2}),
            SkillMilestone(50.0, "Innovation Catalyst", "Inspire creativity in others",
                         ["creative_leadership"], {"team_creativity_bonus": 0.3}),
            SkillMilestone(75.0, "Creative Visionary", "Transformative creative thinking",
                         ["paradigm_shift"], {"breakthrough_chance": 0.4}),
            SkillMilestone(90.0, "Creative Genius", "Master of innovation",
                         ["legendary_innovator"], {"breakthrough_multiplier": 2.0})
        ]

        # Build tree structure
        tree.add_skill(creativity)  # Root skill
        tree.add_skill(problem_solving, ["Creative Thinking"])
        tree.add_skill(research, ["Problem Solving"])
        tree.add_skill(innovation, ["Creative Thinking", "Problem Solving"])
        tree.add_skill(systems_thinking, ["Problem Solving", "Research Methodology"])

        # Set unlock requirements
        tree.unlock_requirements["Innovation Management"] = {"points": 3, "level": 10}
        tree.unlock_requirements["Systems Thinking"] = {"points": 5, "level": 15}

        tree.available_points = 10

        return tree

    @staticmethod
    def create_educator_tree() -> SkillTree:
        """Create skill tree for The Educator archetype"""
        tree = SkillTree(
            name="The Educator's Journey",
            description="Master the arts of teaching, mentoring, and knowledge transmission",
            tree_type="educator",
            difficulty_modifier=0.8  # Easier progression - teaching builds on itself
        )

        # Core Skills
        teaching = AdvancedSkill(
            name="Teaching",
            category=SkillCategory.SOCIAL,
            description="Effectively convey knowledge and facilitate learning",
            learning_rate=1.3,
            difficulty=0.7,
            tags={"core", "communication"}
        )
        teaching.add_specialization("curriculum_design", 2.0)
        teaching.add_specialization("assessment", 1.5)

        communication = AdvancedSkill(
            name="Communication",
            category=SkillCategory.SOCIAL,
            description="Clearly articulate ideas and listen actively",
            learning_rate=1.2,
            difficulty=0.8,
            tags={"core", "social"}
        )

        patience = AdvancedSkill(
            name="Patience",
            category=SkillCategory.EMOTIONAL,
            description="Maintain composure and provide consistent support",
            learning_rate=1.1,
            difficulty=0.9,
            tags={"core", "emotional"}
        )

        # Specialized Skills
        mentoring = AdvancedSkill(
            name="Mentoring",
            category=SkillCategory.LEADERSHIP,
            description="Guide others through personal and professional development",
            learning_rate=1.0,
            difficulty=1.0,
            tags={"advanced", "leadership"}
        )

        wisdom = AdvancedSkill(
            name="Wisdom",
            category=SkillCategory.WISDOM,
            description="Apply knowledge with deep understanding and judgment",
            learning_rate=0.7,
            difficulty=1.3,
            tags={"advanced", "wisdom"}
        )

        # Add prerequisites and structure
        mentoring.prerequisites = [
            SkillPrerequisite("Teaching", 20.0),
            SkillPrerequisite("Communication", 15.0),
            SkillPrerequisite("Patience", 10.0)
        ]

        wisdom.prerequisites = [
            SkillPrerequisite("Teaching", 30.0),
            SkillPrerequisite("Communication", 25.0),
            SkillPrerequisite("Patience", 20.0)
        ]

        # Add milestones for teaching
        teaching.milestones = [
            SkillMilestone(10.0, "Natural Teacher", "Gift for explaining concepts",
                         ["clear_explanations"], {"comprehension_bonus": 0.2}),
            SkillMilestone(25.0, "Inspiring Educator", "Motivate students to excel",
                         ["inspiration_techniques"], {"student_motivation": 0.3}),
            SkillMilestone(50.0, "Master Teacher", "Transform educational approaches",
                         ["educational_innovation"], {"learning_efficiency": 0.4}),
            SkillMilestone(75.0, "Educational Visionary", "Revolutionize learning",
                         ["paradigm_education"], ["educational_breakthrough"]),
            SkillMilestone(90.0, "Legendary Mentor", "Shape generations of thinkers",
                         ["immortal_educator"], ["legacy_multiplier"])
        ]

        # Build tree
        tree.add_skill(teaching)  # Root
        tree.add_skill(communication, ["Teaching"])
        tree.add_skill(patience, ["Communication"])
        tree.add_skill(mentoring, ["Teaching", "Communication", "Patience"])
        tree.add_skill(wisdom, ["Teaching", "Communication", "Patience"])

        tree.available_points = 12
        return tree

    @staticmethod
    def create_empath_tree() -> SkillTree:
        """Create skill tree for The Empath archetype"""
        tree = SkillTree(
            name="The Empath's Path",
            description="Master emotional intelligence, deep listening, and compassionate support",
            tree_type="empath",
            difficulty_modifier=0.85
        )

        # Core Skills
        empathy = AdvancedSkill(
            name="Empathy",
            category=SkillCategory.EMOTIONAL,
            description="Deeply understand and share the feelings of others",
            learning_rate=1.4,
            difficulty=0.6,
            tags={"core", "emotional"}
        )
        empathy.add_specialization("emotional_resonance", 4.0)
        empathy.add_specialization("compassionate_action", 3.0)

        listening = AdvancedSkill(
            name="Active Listening",
            category=SkillCategory.SOCIAL,
            description="Listen with full attention and understanding",
            learning_rate=1.3,
            difficulty=0.7,
            tags={"core", "social"}
        )

        emotional_intelligence = AdvancedSkill(
            name="Emotional Intelligence",
            category=SkillCategory.EMOTIONAL,
            description="Recognize, understand, and manage emotions",
            learning_rate=1.2,
            difficulty=0.8,
            tags={"core", "emotional"}
        )

        # Specialized Skills
        healing = AdvancedSkill(
            name="Emotional Healing",
            category=SkillCategory.WISDOM,
            description="Help others process and heal from emotional wounds",
            learning_rate=0.9,
            difficulty=1.1,
            tags={"advanced", "wisdom"}
        )

        conflict_resolution = AdvancedSkill(
            name="Conflict Resolution",
            category=SkillCategory.SOCIAL,
            description="Mediate conflicts and find harmonious solutions",
            learning_rate=1.0,
            difficulty=1.0,
            tags={"advanced", "social"}
        )

        # Build structure
        healing.prerequisites = [
            SkillPrerequisite("Empathy", 25.0),
            SkillPrerequisite("Active Listening", 20.0),
            SkillPrerequisite("Emotional Intelligence", 15.0)
        ]

        conflict_resolution.prerequisites = [
            SkillPrerequisite("Active Listening", 15.0),
            SkillPrerequisite("Emotional Intelligence", 20.0)
        ]

        # Add milestones
        empathy.milestones = [
            SkillMilestone(10.0, "Natural Empath", "Instinctive understanding of others",
                         ["intuitive_empathy"], {"emotional_accuracy": 0.3}),
            SkillMilestone(25.0, "Deep Listener", "Hear what's unsaid",
                         ["profound_listening"], ["hidden_meaning_detection"]),
            SkillMilestone(50.0, "Emotional Guide", "Help others navigate feelings",
                         ["emotional_guidance"], {"healing_effectiveness": 0.4}),
            SkillMilestone(75.0, "Compassionate Healer", "Facilitate deep healing",
                         ["transformative_empathy"], ["emotional_breakthrough"]),
            SkillMilestone(90.0, "Master Empath", "Transcendent emotional connection",
                         ["emotional_transcendence"], ["emotional_mastery"])
        ]

        # Build tree
        tree.add_skill(empathy)  # Root
        tree.add_skill(listening, ["Empathy"])
        tree.add_skill(emotional_intelligence, ["Empathy", "Active Listening"])
        tree.add_skill(healing, ["Empathy", "Active Listening", "Emotional Intelligence"])
        tree.add_skill(conflict_resolution, ["Active Listening", "Emotional Intelligence"])

        tree.available_points = 11
        return tree

    @staticmethod
    def create_engineer_tree() -> SkillTree:
        """Create skill tree for The Engineer archetype"""
        tree = SkillTree(
            name="The Engineer's Craft",
            description="Master system design, problem-solving, and technical innovation",
            tree_type="engineer",
            difficulty_modifier=1.0
        )

        # Core Skills
        system_design = AdvancedSkill(
            name="System Design",
            category=SkillCategory.TECHNICAL,
            description="Design complex, efficient systems",
            learning_rate=1.1,
            difficulty=0.9,
            tags={"core", "technical"}
        )
        system_design.add_specialization("architecture", 3.0)
        system_design.add_specialization("optimization", 2.5)

        problem_solving = AdvancedSkill(
            name="Technical Problem Solving",
            category=SkillCategory.COGNITIVE,
            description="Solve complex technical challenges",
            learning_rate=1.1,
            difficulty=0.9,
            tags={"core", "analytical"}
        )

        innovation = AdvancedSkill(
            name="Technical Innovation",
            category=SkillCategory.CREATIVE,
            description="Create novel technical solutions",
            learning_rate=1.0,
            difficulty=1.0,
            tags={"core", "creative"}
        )

        # Specialized Skills
        prototyping = AdvancedSkill(
            name="Prototyping",
            category=SkillCategory.TECHNICAL,
            description="Build and test rapid prototypes",
            learning_rate=1.2,
            difficulty=0.8,
            tags={"advanced", "technical"}
        )

        optimization = AdvancedSkill(
            name="System Optimization",
            category=SkillCategory.TECHNICAL,
            description="Maximize system efficiency and performance",
            learning_rate=0.9,
            difficulty=1.1,
            tags={"advanced", "technical"}
        )

        # Build structure
        prototyping.prerequisites = [
            SkillPrerequisite("System Design", 15.0),
            SkillPrerequisite("Technical Problem Solving", 10.0)
        ]

        optimization.prerequisites = [
            SkillPrerequisite("System Design", 20.0),
            SkillPrerequisite("Technical Problem Solving", 25.0),
            SkillPrerequisite("Technical Innovation", 15.0)
        ]

        # Build tree
        tree.add_skill(system_design)  # Root
        tree.add_skill(problem_solving, ["System Design"])
        tree.add_skill(innovation, ["System Design", "Technical Problem Solving"])
        tree.add_skill(prototyping, ["System Design", "Technical Problem Solving"])
        tree.add_skill(optimization, ["System Design", "Technical Problem Solving", "Technical Innovation"])

        tree.available_points = 10
        return tree

# ============================================================================
# SKILL TREE MANAGER
# ============================================================================

class SkillTreeManager:
    """Manages skill trees for character development"""

    def __init__(self):
        self.skill_trees: Dict[str, SkillTree] = {}
        self.character_trees: Dict[str, List[str]] = {}  # character_id -> list of tree_ids
        self.global_skill_registry: Dict[str, AdvancedSkill] = {}  # Global skill database

    def create_tree_for_character(self, character_id: str, archetype: str) -> SkillTree:
        """Create appropriate skill tree for character archetype"""
        tree_creators = {
            "The Innovator": ArchetypeSkillTrees.create_innovator_tree,
            "The Educator": ArchetypeSkillTrees.create_educator_tree,
            "The Empath": ArchetypeSkillTrees.create_empath_tree,
            "The Engineer": ArchetypeSkillTrees.create_engineer_tree,
        }

        creator = tree_creators.get(archetype, ArchetypeSkillTrees.create_innovator_tree)
        tree = creator()

        tree_id = str(uuid.uuid4())
        self.skill_trees[tree_id] = tree

        if character_id not in self.character_trees:
            self.character_trees[character_id] = []
        self.character_trees[character_id].append(tree_id)

        # Register skills globally
        for skill in tree.skills.values():
            self.global_skill_registry[skill.name] = skill

        logger.info(f"Created {tree.name} for character {character_id}")
        return tree

    def get_character_trees(self, character_id: str) -> List[SkillTree]:
        """Get all skill trees for a character"""
        if character_id not in self.character_trees:
            return []

        return [self.skill_trees[tree_id] for tree_id in self.character_trees[character_id]]

    def practice_skill(self, character_id: str, skill_name: str,
                      success: bool, difficulty: float, time_spent: float) -> Dict[str, Any]:
        """Practice a skill and return results"""
        results = {
            'skill_name': skill_name,
            'success': success,
            'experience_gained': 0,
            'level_up': False,
            'new_level': 0,
            'specialization_improvement': 0
        }

        # Find the skill in character's trees
        trees = self.get_character_trees(character_id)
        target_skill = None

        for tree in trees:
            if skill_name in tree.skills:
                target_skill = tree.skills[skill_name]
                break

        if not target_skill:
            logger.warning(f"Skill {skill_name} not found for character {character_id}")
            return results

        # Calculate experience gain
        base_experience = int(difficulty * time_spent * 10)
        if success:
            base_experience = int(base_experience * 1.5)

        # Add experience
        leveled_up, new_level = target_skill.add_experience(base_experience)

        results.update({
            'experience_gained': base_experience,
            'level_up': leveled_up,
            'new_level': new_level
        })

        # Practice specialization if applicable
        if target_skill.current_specialization:
            spec_improvement = target_skill.practice_specialization(
                target_skill.current_specialization, success
            )
            results['specialization_improvement'] = spec_improvement

        return results

    def get_skill_progress_summary(self, character_id: str) -> Dict[str, Any]:
        """Get comprehensive skill progress summary for character"""
        trees = self.get_character_trees(character_id)

        if not trees:
            return {'error': 'No skill trees found for character'}

        summary = {
            'character_id': character_id,
            'total_trees': len(trees),
            'tree_statistics': [],
            'total_skills': 0,
            'mastered_skills': 0,
            'total_specializations': 0,
            'available_points': 0,
            'overall_mastery': 0.0
        }

        for tree in trees:
            stats = tree.get_tree_statistics()
            summary['tree_statistics'].append(stats)
            summary['total_skills'] += stats['total_skills']
            summary['mastered_skills'] += stats['mastered_skills']
            summary['total_specializations'] += stats['total_specializations']
            summary['available_points'] += stats['available_points']
            summary['overall_mastery'] += stats['overall_mastery']

        # Calculate averages
        if len(trees) > 0:
            summary['overall_mastery'] /= len(trees)

        return summary

    def recommend_next_skills(self, character_id: str, count: int = 5) -> List[Dict[str, Any]]:
        """Recommend next skills to learn based on current progress"""
        trees = self.get_character_trees(character_id)
        recommendations = []

        for tree in trees:
            for skill_name, skill in tree.skills.items():
                if skill.current_level < 5.0:  # Focus on underdeveloped skills
                    can_unlock, reason = tree.can_unlock_skill(skill_name)

                    if can_unlock or skill.current_level > 0:
                        # Calculate priority based on prerequisites and utility
                        priority = self._calculate_skill_priority(tree, skill_name)

                        recommendations.append({
                            'skill_name': skill_name,
                            'current_level': skill.current_level,
                            'can_unlock': can_unlock,
                            'reason': reason,
                            'priority': priority,
                            'tree_name': tree.name,
                            'category': skill.category.value,
                            'description': skill.description
                        })

        # Sort by priority and return top recommendations
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        return recommendations[:count]

    def _calculate_skill_priority(self, tree: SkillTree, skill_name: str) -> float:
        """Calculate priority score for a skill"""
        skill = tree.skills[skill_name]
        priority = 0.0

        # Lower level skills get higher priority
        priority += (10.0 - skill.current_level) * 0.5

        # Skills that unlock other abilities get priority
        dependent_count = len([s for s in tree.skills.values()
                             if any(prereq.skill_name == skill_name for prereq in s.prerequisites)])
        priority += dependent_count * 2.0

        # Core skills get priority
        if 'core' in skill.tags:
            priority += 3.0

        # Synergistic skills get priority
        synergy_count = len(skill.synergies)
        priority += synergy_count * 1.0

        return priority

    def unlock_skill_for_character(self, character_id: str, tree_id: str,
                                 skill_name: str) -> Dict[str, Any]:
        """Unlock a skill for a character"""
        if tree_id not in self.skill_trees:
            return {'success': False, 'reason': 'Tree not found'}

        tree = self.skill_trees[tree_id]

        if character_id not in self.character_trees or tree_id not in self.character_trees[character_id]:
            return {'success': False, 'reason': 'Tree not assigned to character'}

        success = tree.unlock_skill(skill_name)

        if success:
            return {
                'success': True,
                'skill_name': skill_name,
                'new_level': tree.skills[skill_name].current_level,
                'remaining_points': tree.available_points
            }
        else:
            can_unlock, reason = tree.can_unlock_skill(skill_name)
            return {'success': False, 'reason': reason}

# ============================================================================
# DEMONSTRATION
# ============================================================================

if __name__ == "__main__":
    def demonstrate_skill_trees():
        """Demonstrate the skill tree system"""
        print("Advanced Character Skill Trees and Specialization System")
        print("=" * 60)

        # Create skill tree manager
        manager = SkillTreeManager()

        # Create skill trees for different archetypes
        print("\nCreating Skill Trees for Archetypes:")

        # Innovator Tree
        innovator_tree = ArchetypeSkillTrees.create_innovator_tree()
        print(f"✓ Created: {innovator_tree.name}")
        print(f"  Root skills: {innovator_tree.root_skills}")
        print(f"  Total skills: {len(innovator_tree.skills)}")
        print(f"  Available points: {innovator_tree.available_points}")

        # Educator Tree
        educator_tree = ArchetypeSkillTrees.create_educator_tree()
        print(f"✓ Created: {educator_tree.name}")
        print(f"  Root skills: {educator_tree.root_skills}")

        # Empath Tree
        empath_tree = ArchetypeSkillTrees.create_empath_tree()
        print(f"✓ Created: {empath_tree.name}")
        print(f"  Root skills: {empath_tree.root_skills}")

        # Demonstrate skill progression
        print("\nDemonstrating Skill Progression:")

        # Get a sample skill
        creativity = innovator_tree.skills["Creative Thinking"]
        print(f"\nInitial state of {creativity.name}:")
        print(f"  Level: {creativity.current_level:.1f}/{creativity.max_level}")
        print(f"  Mastery: {creativity.mastery_level.value}")
        print(f"  Success Rate: {creativity.success_rate:.1%}")

        # Practice the skill
        print(f"\nPracticing {creativity.name}...")

        for i in range(5):
            success = i % 4 != 0  # 75% success rate
            leveled_up, new_level = creativity.add_experience(50)

            if leveled_up:
                print(f"  Level up! Now level {new_level:.1f}")

            if creativity.current_specialization:
                spec_improvement = creativity.practice_specialization(
                    creativity.current_specialization, success
                )
                if spec_improvement > 0:
                    print(f"  {creativity.current_specialization} improved by {spec_improvement:.2f}")

        print(f"\nFinal state of {creativity.name}:")
        print(f"  Level: {creativity.current_level:.1f}/{creativity.max_level}")
        print(f"  Mastery: {creativity.mastery_level.value}")
        print(f"  Success Rate: {creativity.success_rate:.1%}")
        print(f"  Total Uses: {creativity.total_uses}")
        print(f"  Specializations: {list(creativity.specializations.keys())}")

        # Demonstrate skill unlocking
        print(f"\nDemonstrating Skill Unlocking:")

        # Try to unlock innovation (requires prerequisites)
        innovation_skill = innovator_tree.skills["Innovation Management"]
        print(f"Trying to unlock {innovation_skill.name}...")

        can_unlock, reason = innovator_tree.can_unlock_skill("Innovation Management")
        print(f"  Can unlock: {can_unlock}")
        print(f"  Reason: {reason}")

        # Manually level up prerequisites for demonstration
        print(f"\nLeveling up prerequisites...")
        innovator_tree.skills["Creative Thinking"].current_level = 20.0
        innovator_tree.skills["Problem Solving"].current_level = 15.0

        can_unlock, reason = innovator_tree.can_unlock_skill("Innovation Management")
        print(f"  Can unlock now: {can_unlock}")
        print(f"  Reason: {reason}")

        if can_unlock:
            success = innovator_tree.unlock_skill("Innovation Management")
            print(f"  Unlock successful: {success}")
            print(f"  Innovation level: {innovation_skill.current_level:.1f}")
            print(f"  Remaining points: {innovator_tree.available_points}")

        # Show skill tree statistics
        print(f"\nSkill Tree Statistics:")
        stats = innovator_tree.get_tree_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Demonstrate skill progression paths
        print(f"\nSkill Progression Paths:")

        path = innovator_tree.get_skill_progression_path("Systems Thinking")
        print(f"  Path to Systems Thinking: {' → '.join(path)}")

        # Demonstrate skill recommendations
        print(f"\nSkill Recommendations:")

        # Create a character tree assignment
        character_id = "demo_character_001"
        manager.skill_trees["innovator_demo"] = innovator_tree
        manager.character_trees[character_id] = ["innovator_demo"]

        recommendations = manager.recommend_next_skills(character_id)
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"  {i}. {rec['skill_name']} (Priority: {rec['priority']:.1f})")
            print(f"     {rec['description']}")
            print(f"     Current level: {rec['current_level']:.1f}")

        print(f"\nSkill Tree Integration Complete!")
        print("Characters can now develop complex specializations and master their archetypal paths.")

    demonstrate_skill_trees()