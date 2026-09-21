"""
Skill Tree Display System for Interactive Tutorials

This module provides comprehensive skill tree visualization, progression tracking,
prerequisite management, and dynamic path generation for learning experiences.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
import json
import sqlite3
from pathlib import Path
import math


class SkillStatus(Enum):
    """Status of individual skills in the tree"""
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MASTERED = "mastered"


class SkillCategory(Enum):
    """Categories of skills"""
    FOUNDATION = "foundation"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    COLLABORATIVE = "collaborative"
    ADVANCED = "advanced"
    SPECIALIZED = "specialized"
    EXPERT = "expert"


class TreeLayout(Enum):
    """Layout types for skill trees"""
    HIERARCHICAL = "hierarchical"
    RADIAL = "radial"
    NETWORK = "network"
    LINEAR = "linear"
    BRANCHING = "branching"
    CONSTELLATION = "constellation"


class PathType(Enum):
    """Types of learning paths through the skill tree"""
    SHORTEST = "shortest"
    COMPREHENSIVE = "comprehensive"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    CUSTOM = "custom"


@dataclass
class Skill:
    """Individual skill node in the tree"""
    skill_id: str
    name: str
    description: str
    category: SkillCategory
    difficulty_level: int  # 1-10
    estimated_hours: float
    prerequisites: List[str] = field(default_factory=list)
    unlocks: List[str] = field(default_factory=list)
    status: SkillStatus = SkillStatus.LOCKED
    progress_percentage: float = 0.0
    mastery_criteria: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    resources: List[Dict[str, str]] = field(default_factory=list)
    position: Optional[Tuple[float, float]] = None
    icon: str = "skill"
    color: str = "#3498db"


@dataclass
class SkillConnection:
    """Connection between skills in the tree"""
    from_skill: str
    to_skill: str
    connection_type: str = "prerequisite"  # prerequisite, unlocks, related
    strength: float = 1.0  # Connection strength for layout
    description: Optional[str] = None


@dataclass
class LearningPath:
    """Ordered path through skills"""
    path_id: str
    name: str
    description: str
    path_type: PathType
    skills: List[str]  # Ordered list of skill IDs
    estimated_total_hours: float
    difficulty_progression: List[int]
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class UserProgress:
    """User's progress through the skill tree"""
    user_id: str
    skill_statuses: Dict[str, SkillStatus] = field(default_factory=dict)
    skill_progress: Dict[str, float] = field(default_factory=dict)
    completed_skills: Set[str] = field(default_factory=set)
    current_focus: List[str] = field(default_factory=list)
    active_paths: List[str] = field(default_factory=list)
    total_hours_invested: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class TreeVisualization:
    """Visual representation of skill tree"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    layout_data: Dict[str, Any]
    user_progress: UserProgress
    recommended_next: List[str]
    available_paths: List[LearningPath]


class SkillTreeBuilder:
    """Builds and manages skill tree structure"""
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.connections: List[SkillConnection] = []
        self.paths: Dict[str, LearningPath] = {}
    
    def add_skill(self, skill: Skill) -> 'SkillTreeBuilder':
        """Add a skill to the tree"""
        self.skills[skill.skill_id] = skill
        return self
    
    def add_connection(self, connection: SkillConnection) -> 'SkillTreeBuilder':
        """Add a connection between skills"""
        self.connections.append(connection)
        
        # Update skill prerequisites and unlocks
        if connection.connection_type == "prerequisite":
            if connection.to_skill in self.skills:
                self.skills[connection.to_skill].prerequisites.append(connection.from_skill)
            if connection.from_skill in self.skills:
                self.skills[connection.from_skill].unlocks.append(connection.to_skill)
        
        return self
    
    def create_foundation_skills(self) -> 'SkillTreeBuilder':
        """Create foundation skills that are prerequisites for everything"""
        foundation_skills = [
            Skill("basic_navigation", "Basic Navigation", "Learn to navigate the interface",
                  SkillCategory.FOUNDATION, 1, 0.5, color="#e74c3c"),
            Skill("understanding_goals", "Understanding Goals", "Learn what you want to achieve",
                  SkillCategory.FOUNDATION, 1, 1.0, color="#e74c3c"),
            Skill("learning_methods", "Learning Methods", "Understand different ways to learn",
                  SkillCategory.FOUNDATION, 2, 1.5, color="#e74c3c"),
        ]
        
        for skill in foundation_skills:
            self.add_skill(skill)
        
        # Chain foundation skills
        self.add_connection(SkillConnection("basic_navigation", "understanding_goals"))
        self.add_connection(SkillConnection("understanding_goals", "learning_methods"))
        
        return self
    
    def create_technical_branch(self) -> 'SkillTreeBuilder':
        """Create technical skills branch"""
        technical_skills = [
            Skill("programming_basics", "Programming Basics", "Learn fundamental programming concepts",
                  SkillCategory.TECHNICAL, 3, 10.0, color="#3498db"),
            Skill("data_structures", "Data Structures", "Master arrays, lists, trees, graphs",
                  SkillCategory.TECHNICAL, 5, 15.0, color="#3498db"),
            Skill("algorithms", "Algorithms", "Learn sorting, searching, optimization",
                  SkillCategory.TECHNICAL, 6, 20.0, color="#3498db"),
            Skill("system_design", "System Design", "Design scalable systems",
                  SkillCategory.ADVANCED, 8, 25.0, color="#9b59b6"),
        ]
        
        for skill in technical_skills:
            self.add_skill(skill)
        
        # Create technical progression
        self.add_connection(SkillConnection("learning_methods", "programming_basics"))
        self.add_connection(SkillConnection("programming_basics", "data_structures"))
        self.add_connection(SkillConnection("data_structures", "algorithms"))
        self.add_connection(SkillConnection("algorithms", "system_design"))
        
        return self
    
    def create_creative_branch(self) -> 'SkillTreeBuilder':
        """Create creative skills branch"""
        creative_skills = [
            Skill("design_thinking", "Design Thinking", "Learn human-centered design",
                  SkillCategory.CREATIVE, 3, 8.0, color="#f39c12"),
            Skill("ui_design", "UI Design", "Create beautiful user interfaces",
                  SkillCategory.CREATIVE, 5, 12.0, color="#f39c12"),
            Skill("ux_research", "UX Research", "Understand user needs and behaviors",
                  SkillCategory.CREATIVE, 6, 15.0, color="#f39c12"),
            Skill("visual_storytelling", "Visual Storytelling", "Communicate through visuals",
                  SkillCategory.CREATIVE, 7, 18.0, color="#f39c12"),
        ]
        
        for skill in creative_skills:
            self.add_skill(skill)
        
        # Create creative progression
        self.add_connection(SkillConnection("learning_methods", "design_thinking"))
        self.add_connection(SkillConnection("design_thinking", "ui_design"))
        self.add_connection(SkillConnection("design_thinking", "ux_research"))
        self.add_connection(SkillConnection("ui_design", "visual_storytelling"))
        self.add_connection(SkillConnection("ux_research", "visual_storytelling"))
        
        return self
    
    def create_analytical_branch(self) -> 'SkillTreeBuilder':
        """Create analytical skills branch"""
        analytical_skills = [
            Skill("data_analysis", "Data Analysis", "Extract insights from data",
                  SkillCategory.ANALYTICAL, 4, 12.0, color="#27ae60"),
            Skill("statistics", "Statistics", "Understand statistical methods",
                  SkillCategory.ANALYTICAL, 5, 15.0, color="#27ae60"),
            Skill("machine_learning", "Machine Learning", "Build predictive models",
                  SkillCategory.ADVANCED, 7, 25.0, color="#9b59b6"),
            Skill("data_visualization", "Data Visualization", "Present data effectively",
                  SkillCategory.ANALYTICAL, 5, 10.0, color="#27ae60"),
        ]
        
        for skill in analytical_skills:
            self.add_skill(skill)
        
        # Create analytical progression
        self.add_connection(SkillConnection("learning_methods", "data_analysis"))
        self.add_connection(SkillConnection("data_analysis", "statistics"))
        self.add_connection(SkillConnection("statistics", "machine_learning"))
        self.add_connection(SkillConnection("data_analysis", "data_visualization"))
        
        # Cross-branch connections
        self.add_connection(SkillConnection("programming_basics", "data_analysis"))
        
        return self
    
    def create_learning_path(self, path_id: str, name: str, path_type: PathType, 
                           skill_sequence: List[str]) -> LearningPath:
        """Create a learning path through the skills"""
        total_hours = sum(self.skills[skill_id].estimated_hours for skill_id in skill_sequence)
        difficulty_progression = [self.skills[skill_id].difficulty_level for skill_id in skill_sequence]
        
        path = LearningPath(
            path_id=path_id,
            name=name,
            description=f"Structured path covering {len(skill_sequence)} skills",
            path_type=path_type,
            skills=skill_sequence,
            estimated_total_hours=total_hours,
            difficulty_progression=difficulty_progression
        )
        
        self.paths[path_id] = path
        return path
    
    def get_available_skills(self, user_progress: UserProgress) -> List[str]:
        """Get skills that are available to learn (prerequisites met)"""
        available = []
        
        for skill_id, skill in self.skills.items():
            if skill_id in user_progress.completed_skills:
                continue
            
            # Check if all prerequisites are completed
            prerequisites_met = all(
                prereq in user_progress.completed_skills 
                for prereq in skill.prerequisites
            )
            
            if prerequisites_met:
                available.append(skill_id)
        
        return available
    
    def get_recommended_next(self, user_progress: UserProgress, limit: int = 3) -> List[str]:
        """Get recommended next skills to learn"""
        available = self.get_available_skills(user_progress)
        
        # Score skills based on various factors
        skill_scores = []
        for skill_id in available:
            skill = self.skills[skill_id]
            score = 0
            
            # Prefer foundation skills
            if skill.category == SkillCategory.FOUNDATION:
                score += 100
            
            # Prefer skills with lower difficulty if user is beginning
            completed_count = len(user_progress.completed_skills)
            if completed_count < 5:
                score += (10 - skill.difficulty_level) * 10
            
            # Prefer skills that unlock many others
            score += len(skill.unlocks) * 5
            
            # Prefer skills in active paths
            for path_id in user_progress.active_paths:
                if path_id in self.paths and skill_id in self.paths[path_id].skills:
                    score += 20
            
            skill_scores.append((skill_id, score))
        
        # Sort by score and return top recommendations
        skill_scores.sort(key=lambda x: x[1], reverse=True)
        return [skill_id for skill_id, _ in skill_scores[:limit]]


class LayoutEngine:
    """Generates visual layouts for skill trees"""
    
    def generate_hierarchical_layout(self, skills: Dict[str, Skill], 
                                   connections: List[SkillConnection]) -> Dict[str, Tuple[float, float]]:
        """Generate hierarchical layout based on skill levels"""
        positions = {}
        
        # Group skills by difficulty level
        levels = {}
        for skill_id, skill in skills.items():
            level = skill.difficulty_level
            if level not in levels:
                levels[level] = []
            levels[level].append(skill_id)
        
        # Position skills in levels
        max_width = 800
        level_height = 100
        
        for level, skill_ids in levels.items():
            y = level * level_height
            count = len(skill_ids)
            
            for i, skill_id in enumerate(skill_ids):
                x = (i + 1) * max_width / (count + 1)
                positions[skill_id] = (x, y)
        
        return positions
    
    def generate_radial_layout(self, skills: Dict[str, Skill], 
                             connections: List[SkillConnection]) -> Dict[str, Tuple[float, float]]:
        """Generate radial layout with categories as spokes"""
        positions = {}
        center_x, center_y = 400, 300
        
        # Group by category
        categories = {}
        for skill_id, skill in skills.items():
            cat = skill.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(skill_id)
        
        # Arrange categories radially
        num_categories = len(categories)
        angle_per_category = 2 * math.pi / num_categories
        
        for i, (category, skill_ids) in enumerate(categories.items()):
            base_angle = i * angle_per_category
            
            for j, skill_id in enumerate(skill_ids):
                skill = skills[skill_id]
                # Radius based on difficulty level
                radius = 50 + skill.difficulty_level * 30
                # Slight angle offset for skills in same category
                angle = base_angle + (j - len(skill_ids)/2) * 0.2
                
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                positions[skill_id] = (x, y)
        
        return positions
    
    def generate_network_layout(self, skills: Dict[str, Skill], 
                              connections: List[SkillConnection]) -> Dict[str, Tuple[float, float]]:
        """Generate force-directed network layout"""
        positions = {}
        
        # Initialize random positions
        import random
        for skill_id in skills:
            positions[skill_id] = (random.uniform(100, 700), random.uniform(100, 500))
        
        # Simple force-directed algorithm
        iterations = 100
        for _ in range(iterations):
            forces = {skill_id: [0, 0] for skill_id in skills}
            
            # Repulsive forces between all nodes
            for skill1 in skills:
                for skill2 in skills:
                    if skill1 != skill2:
                        x1, y1 = positions[skill1]
                        x2, y2 = positions[skill2]
                        dx, dy = x2 - x1, y2 - y1
                        distance = math.sqrt(dx*dx + dy*dy) + 0.1
                        
                        # Repulsive force
                        force = 1000 / (distance * distance)
                        forces[skill1][0] -= force * dx / distance
                        forces[skill1][1] -= force * dy / distance
            
            # Attractive forces for connected nodes
            for conn in connections:
                if conn.from_skill in positions and conn.to_skill in positions:
                    x1, y1 = positions[conn.from_skill]
                    x2, y2 = positions[conn.to_skill]
                    dx, dy = x2 - x1, y2 - y1
                    distance = math.sqrt(dx*dx + dy*dy) + 0.1
                    
                    # Attractive force
                    force = distance * 0.01 * conn.strength
                    forces[conn.from_skill][0] += force * dx / distance
                    forces[conn.from_skill][1] += force * dy / distance
                    forces[conn.to_skill][0] -= force * dx / distance
                    forces[conn.to_skill][1] -= force * dy / distance
            
            # Apply forces
            for skill_id in skills:
                x, y = positions[skill_id]
                fx, fy = forces[skill_id]
                positions[skill_id] = (
                    max(50, min(750, x + fx * 0.1)),
                    max(50, min(550, y + fy * 0.1))
                )
        
        return positions


class SkillTreeEngine:
    """Main skill tree management system"""
    
    def __init__(self, db_path: str = "skill_tree.db"):
        self.db_path = Path(db_path)
        self.builder = SkillTreeBuilder()
        self.layout_engine = LayoutEngine()
        self.init_database()
        self.create_default_tree()
    
    def init_database(self):
        """Initialize skill tree database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                    user_id TEXT,
                    skill_id TEXT,
                    status TEXT,
                    progress_percentage REAL,
                    last_updated DATETIME,
                    PRIMARY KEY (user_id, skill_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_paths (
                    user_id TEXT,
                    path_id TEXT,
                    started_at DATETIME,
                    completed_at DATETIME,
                    is_active BOOLEAN,
                    PRIMARY KEY (user_id, path_id)
                )
            """)
    
    def create_default_tree(self):
        """Create the default skill tree structure"""
        (self.builder
         .create_foundation_skills()
         .create_technical_branch()
         .create_creative_branch()
         .create_analytical_branch())
        
        # Create some learning paths
        self.builder.create_learning_path(
            "beginner_tech", 
            "Beginner Technical Path",
            PathType.BEGINNER,
            ["basic_navigation", "understanding_goals", "learning_methods", "programming_basics"]
        )
        
        self.builder.create_learning_path(
            "full_stack_dev",
            "Full Stack Developer",
            PathType.COMPREHENSIVE,
            ["basic_navigation", "understanding_goals", "learning_methods", 
             "programming_basics", "data_structures", "algorithms", "design_thinking", "ui_design"]
        )
        
        self.builder.create_learning_path(
            "data_scientist",
            "Data Scientist",
            PathType.ADVANCED,
            ["basic_navigation", "understanding_goals", "learning_methods",
             "programming_basics", "data_analysis", "statistics", "machine_learning", "data_visualization"]
        )
    
    def get_user_progress(self, user_id: str) -> UserProgress:
        """Get user's current progress"""
        progress = UserProgress(user_id=user_id)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get skill progress
            cursor = conn.execute("""
                SELECT skill_id, status, progress_percentage, last_updated
                FROM user_progress WHERE user_id = ?
            """, (user_id,))
            
            for row in cursor.fetchall():
                skill_id, status, progress_pct, last_updated = row
                progress.skill_statuses[skill_id] = SkillStatus(status)
                progress.skill_progress[skill_id] = progress_pct
                
                if status == SkillStatus.COMPLETED.value:
                    progress.completed_skills.add(skill_id)
            
            # Get active paths
            cursor = conn.execute("""
                SELECT path_id FROM user_paths 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            progress.active_paths = [row[0] for row in cursor.fetchall()]
        
        return progress
    
    def update_skill_progress(self, user_id: str, skill_id: str, 
                            status: SkillStatus, progress_percentage: float = 0.0):
        """Update user's progress on a specific skill"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_progress 
                (user_id, skill_id, status, progress_percentage, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, skill_id, status.value, progress_percentage, datetime.now().isoformat()))
    
    def activate_learning_path(self, user_id: str, path_id: str):
        """Activate a learning path for user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_paths
                (user_id, path_id, started_at, is_active)
                VALUES (?, ?, ?, 1)
            """, (user_id, path_id, datetime.now().isoformat()))
    
    def generate_tree_visualization(self, user_id: str, layout: TreeLayout = TreeLayout.HIERARCHICAL) -> TreeVisualization:
        """Generate complete tree visualization for user"""
        user_progress = self.get_user_progress(user_id)
        
        # Generate layout positions
        if layout == TreeLayout.HIERARCHICAL:
            positions = self.layout_engine.generate_hierarchical_layout(
                self.builder.skills, self.builder.connections)
        elif layout == TreeLayout.RADIAL:
            positions = self.layout_engine.generate_radial_layout(
                self.builder.skills, self.builder.connections)
        elif layout == TreeLayout.NETWORK:
            positions = self.layout_engine.generate_network_layout(
                self.builder.skills, self.builder.connections)
        else:
            positions = self.layout_engine.generate_hierarchical_layout(
                self.builder.skills, self.builder.connections)
        
        # Create visualization nodes
        nodes = []
        for skill_id, skill in self.builder.skills.items():
            position = positions.get(skill_id, (400, 300))
            status = user_progress.skill_statuses.get(skill_id, SkillStatus.LOCKED)
            progress = user_progress.skill_progress.get(skill_id, 0.0)
            
            node = {
                'id': skill_id,
                'label': skill.name,
                'description': skill.description,
                'category': skill.category.value,
                'difficulty': skill.difficulty_level,
                'estimated_hours': skill.estimated_hours,
                'status': status.value,
                'progress': progress,
                'position': {'x': position[0], 'y': position[1]},
                'color': self._get_status_color(status, skill.color),
                'icon': skill.icon,
                'tags': skill.tags,
                'resources': skill.resources
            }
            nodes.append(node)
        
        # Create visualization edges
        edges = []
        for conn in self.builder.connections:
            edge = {
                'from': conn.from_skill,
                'to': conn.to_skill,
                'type': conn.connection_type,
                'strength': conn.strength,
                'description': conn.description
            }
            edges.append(edge)
        
        # Get recommendations and available paths
        recommended_next = self.builder.get_recommended_next(user_progress)
        available_paths = [path for path in self.builder.paths.values() 
                          if path.path_id not in user_progress.active_paths]
        
        return TreeVisualization(
            nodes=nodes,
            edges=edges,
            layout_data={'type': layout.value, 'positions': positions},
            user_progress=user_progress,
            recommended_next=recommended_next,
            available_paths=available_paths
        )
    
    def _get_status_color(self, status: SkillStatus, base_color: str) -> str:
        """Get color based on skill status"""
        color_map = {
            SkillStatus.LOCKED: "#95a5a6",      # Gray
            SkillStatus.AVAILABLE: "#f39c12",   # Orange
            SkillStatus.IN_PROGRESS: "#3498db", # Blue
            SkillStatus.COMPLETED: "#27ae60",   # Green
            SkillStatus.MASTERED: "#f1c40f"     # Gold
        }
        return color_map.get(status, base_color)
    
    def get_skill_details(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific skill"""
        if skill_id not in self.builder.skills:
            return None
        
        skill = self.builder.skills[skill_id]
        return {
            'id': skill.skill_id,
            'name': skill.name,
            'description': skill.description,
            'category': skill.category.value,
            'difficulty_level': skill.difficulty_level,
            'estimated_hours': skill.estimated_hours,
            'prerequisites': skill.prerequisites,
            'unlocks': skill.unlocks,
            'mastery_criteria': skill.mastery_criteria,
            'tags': skill.tags,
            'resources': skill.resources,
            'icon': skill.icon,
            'color': skill.color
        }
    
    def get_learning_path_details(self, path_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a learning path"""
        if path_id not in self.builder.paths:
            return None
        
        path = self.builder.paths[path_id]
        skill_details = [self.get_skill_details(skill_id) for skill_id in path.skills]
        
        return {
            'id': path.path_id,
            'name': path.name,
            'description': path.description,
            'type': path.path_type.value,
            'skills': skill_details,
            'estimated_total_hours': path.estimated_total_hours,
            'difficulty_progression': path.difficulty_progression,
            'milestones': path.milestones,
            'tags': path.tags
        }
    
    def get_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive dashboard data for user"""
        user_progress = self.get_user_progress(user_id)
        tree_viz = self.generate_tree_visualization(user_id)
        
        # Calculate statistics
        total_skills = len(self.builder.skills)
        completed_skills = len(user_progress.completed_skills)
        completion_percentage = (completed_skills / total_skills) * 100 if total_skills > 0 else 0
        
        # Get active path progress
        active_path_progress = []
        for path_id in user_progress.active_paths:
            if path_id in self.builder.paths:
                path = self.builder.paths[path_id]
                path_completed = sum(1 for skill_id in path.skills 
                                   if skill_id in user_progress.completed_skills)
                path_progress = (path_completed / len(path.skills)) * 100
                
                active_path_progress.append({
                    'path_id': path_id,
                    'name': path.name,
                    'progress_percentage': path_progress,
                    'completed_skills': path_completed,
                    'total_skills': len(path.skills)
                })
        
        return {
            'user_id': user_id,
            'generated_at': datetime.now().isoformat(),
            'statistics': {
                'total_skills': total_skills,
                'completed_skills': completed_skills,
                'completion_percentage': completion_percentage,
                'active_paths': len(user_progress.active_paths)
            },
            'tree_visualization': tree_viz,
            'active_path_progress': active_path_progress,
            'recommended_skills': tree_viz.recommended_next,
            'available_paths': [
                {'id': path.path_id, 'name': path.name, 'type': path.path_type.value}
                for path in tree_viz.available_paths
            ]
        }


# Example usage and testing
if __name__ == "__main__":
    # Initialize skill tree engine
    engine = SkillTreeEngine("test_skill_tree.db")
    
    # Simulate user progress
    user_id = "user123"
    
    # Complete some foundation skills
    engine.update_skill_progress(user_id, "basic_navigation", SkillStatus.COMPLETED, 100.0)
    engine.update_skill_progress(user_id, "understanding_goals", SkillStatus.COMPLETED, 100.0)
    engine.update_skill_progress(user_id, "learning_methods", SkillStatus.IN_PROGRESS, 75.0)
    
    # Activate a learning path
    engine.activate_learning_path(user_id, "beginner_tech")
    
    # Generate visualization
    viz = engine.generate_tree_visualization(user_id, TreeLayout.HIERARCHICAL)
    print(f"Generated skill tree with {len(viz.nodes)} nodes and {len(viz.edges)} edges")
    print(f"Recommended next skills: {viz.recommended_next}")
    
    # Get dashboard
    dashboard = engine.get_dashboard_data(user_id)
    print(f"User completion: {dashboard['statistics']['completion_percentage']:.1f}%")
    print("Dashboard generated successfully!")