"""
Team Formation Optimizer

AI-powered system for optimal team composition based on skills, personalities,
collaboration compatibility, and project requirements.
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any, Set
from enum import Enum
import json
import itertools
import numpy as np
from collections import defaultdict
import math

class TeamRole(Enum):
    LEADER = "leader"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    DESIGNER = "designer"
    ANALYST = "analyst"
    TESTER = "tester"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"

class ProjectType(Enum):
    SOFTWARE_DEVELOPMENT = "software_development"
    RESEARCH = "research"
    MARKETING_CAMPAIGN = "marketing_campaign"
    PRODUCT_LAUNCH = "product_launch"
    STRATEGIC_INITIATIVE = "strategic_initiative"
    INNOVATION_PROJECT = "innovation_project"
    PROCESS_IMPROVEMENT = "process_improvement"
    CROSS_FUNCTIONAL = "cross_functional"

class TeamFormationObjective(Enum):
    MAXIMIZE_PERFORMANCE = "maximize_performance"
    BALANCE_SKILLS = "balance_skills"
    OPTIMIZE_COLLABORATION = "optimize_collaboration"
    MINIMIZE_CONFLICTS = "minimize_conflicts"
    FOSTER_LEARNING = "foster_learning"
    SPEED_EXECUTION = "speed_execution"

@dataclass
class TeamMember:
    id: str = ""
    name: str = ""
    role: str = ""
    department: str = ""
    skill_scores: Dict[str, float] = None  # skill -> proficiency (0-10)
    personality_traits: Dict[str, float] = None  # Big Five + work traits
    availability: float = 1.0  # 0-1 scale
    experience_level: str = "intermediate"  # junior, intermediate, senior, expert
    leadership_capacity: float = 0.5  # 0-1 scale
    collaboration_history: List[Dict[str, Any]] = None
    preferred_roles: List[TeamRole] = None
    timezone: str = ""
    languages: List[str] = None
    max_concurrent_projects: int = 3
    current_project_load: int = 0
    performance_rating: float = 7.0  # Historical performance 1-10
    created_at: datetime = datetime.now()

    def __post_init__(self):
        if self.skill_scores is None:
            self.skill_scores = {}
        if self.personality_traits is None:
            self.personality_traits = {}
        if self.collaboration_history is None:
            self.collaboration_history = []
        if self.preferred_roles is None:
            self.preferred_roles = []
        if self.languages is None:
            self.languages = []

@dataclass
class ProjectRequirements:
    id: str = ""
    name: str = ""
    project_type: ProjectType = ProjectType.SOFTWARE_DEVELOPMENT
    required_skills: Dict[str, float] = None  # skill -> minimum proficiency needed
    preferred_skills: Dict[str, float] = None  # skill -> preferred proficiency
    team_size_range: Tuple[int, int] = (3, 8)
    required_roles: List[TeamRole] = None
    duration_weeks: int = 12
    priority: str = "medium"  # low, medium, high, critical
    complexity: float = 5.0  # 1-10 scale
    innovation_level: float = 5.0  # 1-10 scale
    collaboration_intensity: float = 5.0  # 1-10 scale
    deadline_pressure: float = 5.0  # 1-10 scale
    geographic_constraints: bool = False
    timezone_requirements: List[str] = None
    language_requirements: List[str] = None
    budget_constraints: Dict[str, Any] = None
    success_criteria: List[str] = None
    created_at: datetime = datetime.now()

    def __post_init__(self):
        if self.required_skills is None:
            self.required_skills = {}
        if self.preferred_skills is None:
            self.preferred_skills = {}
        if self.required_roles is None:
            self.required_roles = []
        if self.timezone_requirements is None:
            self.timezone_requirements = []
        if self.language_requirements is None:
            self.language_requirements = []
        if self.budget_constraints is None:
            self.budget_constraints = {}
        if self.success_criteria is None:
            self.success_criteria = []

@dataclass
class TeamComposition:
    id: Optional[int] = None
    project_id: str = ""
    members: List[str] = None  # member IDs
    role_assignments: Dict[str, TeamRole] = None  # member_id -> role
    formation_score: float = 0.0
    skill_coverage_score: float = 0.0
    collaboration_score: float = 0.0
    diversity_score: float = 0.0
    predicted_performance: float = 5.0
    predicted_success_rate: float = 0.5
    risk_factors: List[str] = None
    strengths: List[str] = None
    recommendations: List[str] = None
    formation_objective: TeamFormationObjective = TeamFormationObjective.MAXIMIZE_PERFORMANCE
    confidence_level: str = "medium"  # low, medium, high
    created_at: datetime = datetime.now()

    def __post_init__(self):
        if self.members is None:
            self.members = []
        if self.role_assignments is None:
            self.role_assignments = {}
        if self.risk_factors is None:
            self.risk_factors = []
        if self.strengths is None:
            self.strengths = []
        if self.recommendations is None:
            self.recommendations = []

@dataclass
class TeamPerformanceMetrics:
    team_id: str = ""
    project_id: str = ""
    actual_performance: float = 0.0
    efficiency_rating: float = 0.0
    quality_rating: float = 0.0
    collaboration_rating: float = 0.0
    innovation_rating: float = 0.0
    deadline_adherence: float = 0.0
    team_satisfaction: float = 0.0
    stakeholder_satisfaction: float = 0.0
    lessons_learned: List[str] = None
    success_factors: List[str] = None
    challenges_faced: List[str] = None
    completed_at: datetime = datetime.now()

    def __post_init__(self):
        if self.lessons_learned is None:
            self.lessons_learned = []
        if self.success_factors is None:
            self.success_factors = []
        if self.challenges_faced is None:
            self.challenges_faced = []

class TeamFormationOptimizer:
    """AI-powered team formation and optimization system"""
    
    def __init__(self, db_path: str = "team_formation.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the team formation database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT,
                department TEXT,
                skill_scores TEXT,
                personality_traits TEXT,
                availability REAL DEFAULT 1.0,
                experience_level TEXT DEFAULT 'intermediate',
                leadership_capacity REAL DEFAULT 0.5,
                collaboration_history TEXT,
                preferred_roles TEXT,
                timezone TEXT,
                languages TEXT,
                max_concurrent_projects INTEGER DEFAULT 3,
                current_project_load INTEGER DEFAULT 0,
                performance_rating REAL DEFAULT 7.0,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_requirements (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                project_type TEXT NOT NULL,
                required_skills TEXT,
                preferred_skills TEXT,
                team_size_min INTEGER DEFAULT 3,
                team_size_max INTEGER DEFAULT 8,
                required_roles TEXT,
                duration_weeks INTEGER DEFAULT 12,
                priority TEXT DEFAULT 'medium',
                complexity REAL DEFAULT 5.0,
                innovation_level REAL DEFAULT 5.0,
                collaboration_intensity REAL DEFAULT 5.0,
                deadline_pressure REAL DEFAULT 5.0,
                geographic_constraints BOOLEAN DEFAULT FALSE,
                timezone_requirements TEXT,
                language_requirements TEXT,
                budget_constraints TEXT,
                success_criteria TEXT,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_compositions (
                id INTEGER PRIMARY KEY,
                project_id TEXT NOT NULL,
                members TEXT,
                role_assignments TEXT,
                formation_score REAL,
                skill_coverage_score REAL,
                collaboration_score REAL,
                diversity_score REAL,
                predicted_performance REAL DEFAULT 5.0,
                predicted_success_rate REAL DEFAULT 0.5,
                risk_factors TEXT,
                strengths TEXT,
                recommendations TEXT,
                formation_objective TEXT DEFAULT 'maximize_performance',
                confidence_level TEXT DEFAULT 'medium',
                created_at TEXT,
                FOREIGN KEY (project_id) REFERENCES project_requirements (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_performance_metrics (
                id INTEGER PRIMARY KEY,
                team_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                actual_performance REAL,
                efficiency_rating REAL,
                quality_rating REAL,
                collaboration_rating REAL,
                innovation_rating REAL,
                deadline_adherence REAL,
                team_satisfaction REAL,
                stakeholder_satisfaction REAL,
                lessons_learned TEXT,
                success_factors TEXT,
                challenges_faced TEXT,
                completed_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def add_team_member(self, member: TeamMember) -> str:
        """Add or update a team member profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO team_members 
            (id, name, role, department, skill_scores, personality_traits, availability,
             experience_level, leadership_capacity, collaboration_history, preferred_roles,
             timezone, languages, max_concurrent_projects, current_project_load,
             performance_rating, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            member.id, member.name, member.role, member.department,
            json.dumps(member.skill_scores), json.dumps(member.personality_traits),
            member.availability, member.experience_level, member.leadership_capacity,
            json.dumps(member.collaboration_history),
            json.dumps([role.value for role in member.preferred_roles]),
            member.timezone, json.dumps(member.languages),
            member.max_concurrent_projects, member.current_project_load,
            member.performance_rating, member.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        return member.id
    
    async def add_project_requirements(self, requirements: ProjectRequirements) -> str:
        """Add project requirements for team formation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO project_requirements 
            (id, name, project_type, required_skills, preferred_skills, team_size_min,
             team_size_max, required_roles, duration_weeks, priority, complexity,
             innovation_level, collaboration_intensity, deadline_pressure,
             geographic_constraints, timezone_requirements, language_requirements,
             budget_constraints, success_criteria, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            requirements.id, requirements.name, requirements.project_type.value,
            json.dumps(requirements.required_skills), json.dumps(requirements.preferred_skills),
            requirements.team_size_range[0], requirements.team_size_range[1],
            json.dumps([role.value for role in requirements.required_roles]),
            requirements.duration_weeks, requirements.priority, requirements.complexity,
            requirements.innovation_level, requirements.collaboration_intensity,
            requirements.deadline_pressure, requirements.geographic_constraints,
            json.dumps(requirements.timezone_requirements),
            json.dumps(requirements.language_requirements),
            json.dumps(requirements.budget_constraints),
            json.dumps(requirements.success_criteria), requirements.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        return requirements.id
    
    async def optimize_team_formation(self, project_id: str, 
                                    objective: TeamFormationObjective = TeamFormationObjective.MAXIMIZE_PERFORMANCE,
                                    max_candidates: int = 3) -> List[TeamComposition]:
        """Generate optimal team compositions for a project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get project requirements
        cursor.execute("SELECT * FROM project_requirements WHERE id = ?", (project_id,))
        project_row = cursor.fetchone()
        
        if not project_row:
            conn.close()
            return []
        
        # Parse project data
        project_cols = [description[0] for description in cursor.description]
        project_data = dict(zip(project_cols, project_row))
        
        # Get available team members
        cursor.execute("SELECT * FROM team_members WHERE current_project_load < max_concurrent_projects")
        member_rows = cursor.fetchall()
        
        if len(member_rows) < project_data['team_size_min']:
            conn.close()
            return []
        
        # Parse member data
        member_cols = [description[0] for description in cursor.description]
        available_members = []
        
        for row in member_rows:
            member_dict = dict(zip(member_cols, row))
            
            # Parse JSON fields
            member_dict['skill_scores'] = json.loads(member_dict['skill_scores']) if member_dict['skill_scores'] else {}
            member_dict['personality_traits'] = json.loads(member_dict['personality_traits']) if member_dict['personality_traits'] else {}
            member_dict['collaboration_history'] = json.loads(member_dict['collaboration_history']) if member_dict['collaboration_history'] else []
            member_dict['preferred_roles'] = json.loads(member_dict['preferred_roles']) if member_dict['preferred_roles'] else []
            member_dict['languages'] = json.loads(member_dict['languages']) if member_dict['languages'] else []
            
            available_members.append(member_dict)
        
        # Parse project requirements
        project_data['required_skills'] = json.loads(project_data['required_skills']) if project_data['required_skills'] else {}
        project_data['preferred_skills'] = json.loads(project_data['preferred_skills']) if project_data['preferred_skills'] else {}
        project_data['required_roles'] = json.loads(project_data['required_roles']) if project_data['required_roles'] else []
        project_data['timezone_requirements'] = json.loads(project_data['timezone_requirements']) if project_data['timezone_requirements'] else []
        project_data['language_requirements'] = json.loads(project_data['language_requirements']) if project_data['language_requirements'] else []
        
        # Generate and evaluate team combinations
        team_candidates = await self._generate_team_candidates(
            available_members, project_data, objective, max_candidates
        )
        
        # Score and rank teams
        scored_teams = []
        for candidate in team_candidates:
            composition = await self._evaluate_team_composition(
                candidate, project_data, objective
            )
            scored_teams.append(composition)
        
        # Sort by formation score
        scored_teams.sort(key=lambda x: x.formation_score, reverse=True)
        
        # Store top candidates
        for composition in scored_teams[:max_candidates]:
            await self._store_team_composition(composition, conn)
        
        conn.close()
        return scored_teams[:max_candidates]
    
    async def _generate_team_candidates(self, available_members: List[Dict], 
                                      project_data: Dict, objective: TeamFormationObjective,
                                      max_candidates: int) -> List[List[Dict]]:
        """Generate candidate team combinations using intelligent selection"""
        min_size = project_data['team_size_min']
        max_size = project_data['team_size_max']
        required_skills = project_data['required_skills']
        required_roles = project_data['required_roles']
        
        # Filter members by constraints
        eligible_members = await self._filter_eligible_members(available_members, project_data)
        
        if len(eligible_members) < min_size:
            return []
        
        team_candidates = []
        
        # Generate teams of different sizes
        for team_size in range(min_size, min(max_size + 1, len(eligible_members) + 1)):
            
            if objective == TeamFormationObjective.BALANCE_SKILLS:
                # Use skill-based selection
                candidates = await self._generate_skill_balanced_teams(
                    eligible_members, team_size, required_skills, max_candidates // 3
                )
            elif objective == TeamFormationObjective.OPTIMIZE_COLLABORATION:
                # Use collaboration-based selection
                candidates = await self._generate_collaboration_optimized_teams(
                    eligible_members, team_size, max_candidates // 3
                )
            elif objective == TeamFormationObjective.MINIMIZE_CONFLICTS:
                # Use personality-based selection
                candidates = await self._generate_low_conflict_teams(
                    eligible_members, team_size, max_candidates // 3
                )
            else:
                # Default: performance-based selection
                candidates = await self._generate_performance_optimized_teams(
                    eligible_members, team_size, required_skills, max_candidates // 3
                )
            
            team_candidates.extend(candidates)
        
        return team_candidates[:max_candidates * 2]  # Generate extra for evaluation
    
    async def _filter_eligible_members(self, members: List[Dict], project_data: Dict) -> List[Dict]:
        """Filter members based on project constraints"""
        eligible = []
        
        for member in members:
            # Check availability
            if member['availability'] < 0.5:  # Need at least 50% availability
                continue
            
            # Check timezone constraints
            if project_data['timezone_requirements'] and member['timezone']:
                if member['timezone'] not in project_data['timezone_requirements']:
                    continue
            
            # Check language requirements
            if project_data['language_requirements']:
                member_languages = set(member['languages'])
                required_languages = set(project_data['language_requirements'])
                if not required_languages.issubset(member_languages):
                    continue
            
            eligible.append(member)
        
        return eligible
    
    async def _generate_skill_balanced_teams(self, members: List[Dict], team_size: int,
                                           required_skills: Dict[str, float], max_teams: int) -> List[List[Dict]]:
        """Generate teams with optimal skill balance"""
        teams = []
        
        # Calculate skill priorities
        skill_weights = {skill: importance for skill, importance in required_skills.items()}
        
        # Use greedy algorithm with skill coverage optimization
        for _ in range(max_teams * 3):  # Generate multiple attempts
            team = []
            remaining_members = members.copy()
            covered_skills = defaultdict(float)
            
            # Start with highest performer in most critical skill
            if skill_weights:
                critical_skill = max(skill_weights.keys(), key=lambda s: skill_weights[s])
                best_member = max(remaining_members, 
                                key=lambda m: m['skill_scores'].get(critical_skill, 0))
                team.append(best_member)
                remaining_members.remove(best_member)
                
                for skill, score in best_member['skill_scores'].items():
                    covered_skills[skill] += score
            
            # Fill remaining slots with complementary skills
            while len(team) < team_size and remaining_members:
                best_score = -1
                best_member = None
                
                for member in remaining_members:
                    score = 0
                    
                    # Reward covering missing skills
                    for skill, required_level in required_skills.items():
                        current_coverage = covered_skills[skill]
                        member_skill = member['skill_scores'].get(skill, 0)
                        
                        if current_coverage < required_level * team_size * 0.8:
                            score += member_skill * 2  # Extra weight for needed skills
                        else:
                            score += member_skill * 0.5  # Lower weight for covered skills
                    
                    # Add diversity bonus
                    score += self._calculate_diversity_bonus(team, member)
                    
                    if score > best_score:
                        best_score = score
                        best_member = member
                
                if best_member:
                    team.append(best_member)
                    remaining_members.remove(best_member)
                    
                    for skill, score in best_member['skill_scores'].items():
                        covered_skills[skill] += score
                else:
                    break
            
            if len(team) == team_size:
                teams.append(team)
        
        # Remove duplicates and return best ones
        unique_teams = []
        for team in teams:
            team_ids = set(member['id'] for member in team)
            if not any(set(existing_member['id'] for existing_member in existing_team) == team_ids 
                      for existing_team in unique_teams):
                unique_teams.append(team)
        
        return unique_teams[:max_teams]
    
    async def _generate_performance_optimized_teams(self, members: List[Dict], team_size: int,
                                                  required_skills: Dict[str, float], max_teams: int) -> List[List[Dict]]:
        """Generate teams optimized for overall performance"""
        teams = []
        
        # Sort members by performance rating
        sorted_members = sorted(members, key=lambda m: m['performance_rating'], reverse=True)
        
        # Generate teams using different strategies
        for strategy in range(max_teams):
            team = []
            remaining_members = sorted_members.copy()
            
            if strategy == 0:
                # Strategy 1: Top performers
                team = remaining_members[:team_size]
            elif strategy == 1:
                # Strategy 2: Mix of high and medium performers
                high_performers = remaining_members[:len(remaining_members)//3]
                medium_performers = remaining_members[len(remaining_members)//3:2*len(remaining_members)//3]
                
                team.extend(high_performers[:team_size//2])
                team.extend(medium_performers[:team_size - len(team)])
            else:
                # Strategy 3: Performance + skill coverage
                team = await self._select_performance_skill_team(remaining_members, team_size, required_skills)
            
            if len(team) == team_size:
                teams.append(team)
        
        return teams
    
    async def _generate_collaboration_optimized_teams(self, members: List[Dict], team_size: int,
                                                    max_teams: int) -> List[List[Dict]]:
        """Generate teams optimized for collaboration"""
        teams = []
        
        # Calculate collaboration scores between all pairs
        collaboration_matrix = {}
        for i, member1 in enumerate(members):
            for j, member2 in enumerate(members[i+1:], i+1):
                score = await self._calculate_collaboration_compatibility(member1, member2)
                collaboration_matrix[(member1['id'], member2['id'])] = score
        
        # Use different team formation strategies
        for attempt in range(max_teams * 2):
            team = []
            remaining_members = members.copy()
            
            # Start with a random high-compatibility pair
            if len(remaining_members) >= 2:
                best_pair_score = -1
                best_pair = None
                
                for i in range(min(10, len(remaining_members))):  # Limit search for efficiency
                    for j in range(i+1, min(10, len(remaining_members))):
                        member1, member2 = remaining_members[i], remaining_members[j]
                        pair_key = (member1['id'], member2['id'])
                        reverse_key = (member2['id'], member1['id'])
                        
                        score = collaboration_matrix.get(pair_key, collaboration_matrix.get(reverse_key, 0))
                        if score > best_pair_score:
                            best_pair_score = score
                            best_pair = (member1, member2)
                
                if best_pair:
                    team.extend(best_pair)
                    remaining_members = [m for m in remaining_members if m not in best_pair]
            
            # Add remaining members based on team compatibility
            while len(team) < team_size and remaining_members:
                best_score = -1
                best_member = None
                
                for candidate in remaining_members:
                    team_compatibility = 0
                    for team_member in team:
                        pair_key = (candidate['id'], team_member['id'])
                        reverse_key = (team_member['id'], candidate['id'])
                        compatibility = collaboration_matrix.get(pair_key, collaboration_matrix.get(reverse_key, 0.5))
                        team_compatibility += compatibility
                    
                    avg_compatibility = team_compatibility / len(team) if team else 0
                    if avg_compatibility > best_score:
                        best_score = avg_compatibility
                        best_member = candidate
                
                if best_member:
                    team.append(best_member)
                    remaining_members.remove(best_member)
                else:
                    break
            
            if len(team) == team_size:
                teams.append(team)
        
        # Remove duplicates
        unique_teams = []
        for team in teams:
            team_ids = set(member['id'] for member in team)
            if not any(set(existing_member['id'] for existing_member in existing_team) == team_ids 
                      for existing_team in unique_teams):
                unique_teams.append(team)
        
        return unique_teams[:max_teams]
    
    async def _generate_low_conflict_teams(self, members: List[Dict], team_size: int,
                                         max_teams: int) -> List[List[Dict]]:
        """Generate teams with minimal personality conflicts"""
        teams = []
        
        # Calculate conflict potential between all pairs
        conflict_matrix = {}
        for i, member1 in enumerate(members):
            for j, member2 in enumerate(members[i+1:], i+1):
                conflict_score = await self._calculate_conflict_potential(member1, member2)
                conflict_matrix[(member1['id'], member2['id'])] = conflict_score
        
        # Generate teams with minimum conflict
        for attempt in range(max_teams * 3):
            team = []
            remaining_members = members.copy()
            total_conflict = 0
            
            # Greedy selection for low conflict
            while len(team) < team_size and remaining_members:
                best_member = None
                lowest_additional_conflict = float('inf')
                
                for candidate in remaining_members:
                    additional_conflict = 0
                    for team_member in team:
                        pair_key = (candidate['id'], team_member['id'])
                        reverse_key = (team_member['id'], candidate['id'])
                        conflict = conflict_matrix.get(pair_key, conflict_matrix.get(reverse_key, 0.5))
                        additional_conflict += conflict
                    
                    if additional_conflict < lowest_additional_conflict:
                        lowest_additional_conflict = additional_conflict
                        best_member = candidate
                
                if best_member:
                    team.append(best_member)
                    remaining_members.remove(best_member)
                    total_conflict += lowest_additional_conflict
                else:
                    break
            
            if len(team) == team_size:
                teams.append(team)
        
        # Remove duplicates and sort by conflict level
        unique_teams = []
        for team in teams:
            team_ids = set(member['id'] for member in team)
            if not any(set(existing_member['id'] for existing_member in existing_team) == team_ids 
                      for existing_team in unique_teams):
                unique_teams.append(team)
        
        return unique_teams[:max_teams]
    
    async def _evaluate_team_composition(self, team_members: List[Dict], 
                                       project_data: Dict, objective: TeamFormationObjective) -> TeamComposition:
        """Evaluate and score a team composition"""
        
        # Calculate component scores
        skill_coverage = await self._calculate_skill_coverage_score(team_members, project_data)
        collaboration_score = await self._calculate_team_collaboration_score(team_members)
        diversity_score = await self._calculate_team_diversity_score(team_members)
        
        # Calculate overall formation score based on objective
        if objective == TeamFormationObjective.BALANCE_SKILLS:
            formation_score = skill_coverage * 0.5 + collaboration_score * 0.3 + diversity_score * 0.2
        elif objective == TeamFormationObjective.OPTIMIZE_COLLABORATION:
            formation_score = collaboration_score * 0.6 + skill_coverage * 0.3 + diversity_score * 0.1
        elif objective == TeamFormationObjective.MINIMIZE_CONFLICTS:
            conflict_score = await self._calculate_team_conflict_score(team_members)
            formation_score = (1 - conflict_score) * 0.5 + collaboration_score * 0.3 + skill_coverage * 0.2
        else:  # MAXIMIZE_PERFORMANCE
            performance_score = await self._calculate_team_performance_score(team_members, project_data)
            formation_score = performance_score * 0.4 + skill_coverage * 0.3 + collaboration_score * 0.3
        
        # Predict success rate
        predicted_success_rate = min(1.0, formation_score * 0.8 + 0.1)
        
        # Generate insights
        risk_factors = await self._identify_risk_factors(team_members, project_data)
        strengths = await self._identify_team_strengths(team_members, project_data)
        recommendations = await self._generate_team_recommendations(team_members, project_data, formation_score)
        
        # Assign roles
        role_assignments = await self._assign_optimal_roles(team_members, project_data)
        
        # Determine confidence level
        confidence_level = "high" if len(team_members) <= 6 and formation_score > 0.7 else "medium" if formation_score > 0.5 else "low"
        
        return TeamComposition(
            project_id=project_data['id'],
            members=[member['id'] for member in team_members],
            role_assignments=role_assignments,
            formation_score=formation_score,
            skill_coverage_score=skill_coverage,
            collaboration_score=collaboration_score,
            diversity_score=diversity_score,
            predicted_performance=formation_score * 8 + 2,  # Scale to 1-10
            predicted_success_rate=predicted_success_rate,
            risk_factors=risk_factors,
            strengths=strengths,
            recommendations=recommendations,
            formation_objective=objective,
            confidence_level=confidence_level
        )
    
    async def _calculate_skill_coverage_score(self, team_members: List[Dict], project_data: Dict) -> float:
        """Calculate how well the team covers required skills"""
        required_skills = project_data['required_skills']
        preferred_skills = project_data['preferred_skills']
        
        if not required_skills and not preferred_skills:
            return 0.8  # Default score if no skill requirements
        
        total_score = 0
        total_weight = 0
        
        # Check required skills coverage
        for skill, required_level in required_skills.items():
            team_skill_level = sum(member['skill_scores'].get(skill, 0) for member in team_members)
            coverage_ratio = min(1.0, team_skill_level / (required_level * len(team_members)))
            total_score += coverage_ratio * 2  # Higher weight for required skills
            total_weight += 2
        
        # Check preferred skills coverage
        for skill, preferred_level in preferred_skills.items():
            team_skill_level = sum(member['skill_scores'].get(skill, 0) for member in team_members)
            coverage_ratio = min(1.0, team_skill_level / (preferred_level * len(team_members)))
            total_score += coverage_ratio * 1  # Lower weight for preferred skills
            total_weight += 1
        
        return total_score / total_weight if total_weight > 0 else 0.5
    
    async def _calculate_team_collaboration_score(self, team_members: List[Dict]) -> float:
        """Calculate team collaboration potential"""
        if len(team_members) < 2:
            return 1.0
        
        total_compatibility = 0
        pair_count = 0
        
        for i, member1 in enumerate(team_members):
            for member2 in team_members[i+1:]:
                compatibility = await self._calculate_collaboration_compatibility(member1, member2)
                total_compatibility += compatibility
                pair_count += 1
        
        return total_compatibility / pair_count if pair_count > 0 else 0.5
    
    async def _calculate_team_diversity_score(self, team_members: List[Dict]) -> float:
        """Calculate team diversity across multiple dimensions"""
        if len(team_members) <= 1:
            return 0.0
        
        diversity_score = 0
        dimension_count = 0
        
        # Experience level diversity
        experience_levels = [member['experience_level'] for member in team_members]
        exp_diversity = len(set(experience_levels)) / min(4, len(team_members))  # Max 4 levels
        diversity_score += exp_diversity
        dimension_count += 1
        
        # Department diversity
        departments = [member.get('department', 'unknown') for member in team_members]
        dept_diversity = len(set(departments)) / len(team_members)
        diversity_score += dept_diversity
        dimension_count += 1
        
        # Skill diversity
        all_skills = set()
        for member in team_members:
            all_skills.update(member['skill_scores'].keys())
        
        skill_diversity = len(all_skills) / max(1, len(team_members) * 3)  # Normalize by expected skills per person
        diversity_score += min(1.0, skill_diversity)
        dimension_count += 1
        
        # Personality diversity (if available)
        if all(member['personality_traits'] for member in team_members):
            personality_variance = 0
            for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
                trait_values = [member['personality_traits'].get(trait, 0.5) for member in team_members]
                if len(set(trait_values)) > 1:
                    personality_variance += np.var(trait_values)
            
            personality_diversity = min(1.0, personality_variance / 0.25)  # Normalize variance
            diversity_score += personality_diversity
            dimension_count += 1
        
        return diversity_score / dimension_count if dimension_count > 0 else 0.5
    
    async def _calculate_collaboration_compatibility(self, member1: Dict, member2: Dict) -> float:
        """Calculate collaboration compatibility between two members"""
        compatibility = 0.5  # Base compatibility
        
        # Personality compatibility
        if member1['personality_traits'] and member2['personality_traits']:
            personality_compat = 0
            trait_count = 0
            
            for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
                if trait in member1['personality_traits'] and trait in member2['personality_traits']:
                    val1, val2 = member1['personality_traits'][trait], member2['personality_traits'][trait]
                    
                    if trait == 'neuroticism':
                        # Lower neuroticism is better, similar low values are ideal
                        trait_score = 1.0 - abs(val1 - val2) * 0.5 - max(val1, val2) * 0.3
                    elif trait == 'extraversion':
                        # Extraversion can be complementary
                        trait_score = 1.0 - abs(val1 - val2) * 0.3
                    else:
                        # Similar values are generally good
                        trait_score = 1.0 - abs(val1 - val2) * 0.5
                    
                    personality_compat += max(0, trait_score)
                    trait_count += 1
            
            if trait_count > 0:
                compatibility = personality_compat / trait_count
        
        # Experience level compatibility
        exp_levels = {'junior': 1, 'intermediate': 2, 'senior': 3, 'expert': 4}
        exp1 = exp_levels.get(member1['experience_level'], 2)
        exp2 = exp_levels.get(member2['experience_level'], 2)
        exp_diff = abs(exp1 - exp2)
        
        exp_compatibility = 1.0 if exp_diff <= 1 else 0.8 if exp_diff == 2 else 0.6
        compatibility = (compatibility + exp_compatibility) / 2
        
        return min(1.0, max(0.0, compatibility))
    
    async def _calculate_conflict_potential(self, member1: Dict, member2: Dict) -> float:
        """Calculate potential for conflict between two members"""
        conflict_potential = 0.2  # Base low conflict
        
        if member1['personality_traits'] and member2['personality_traits']:
            # High neuroticism increases conflict potential
            neuroticism1 = member1['personality_traits'].get('neuroticism', 0.5)
            neuroticism2 = member2['personality_traits'].get('neuroticism', 0.5)
            conflict_potential += (neuroticism1 + neuroticism2) * 0.2
            
            # Low agreeableness increases conflict potential
            agreeableness1 = member1['personality_traits'].get('agreeableness', 0.5)
            agreeableness2 = member2['personality_traits'].get('agreeableness', 0.5)
            conflict_potential += (2 - agreeableness1 - agreeableness2) * 0.15
            
            # Very different conscientiousness can cause conflict
            conscientiousness1 = member1['personality_traits'].get('conscientiousness', 0.5)
            conscientiousness2 = member2['personality_traits'].get('conscientiousness', 0.5)
            conflict_potential += abs(conscientiousness1 - conscientiousness2) * 0.1
        
        return min(1.0, max(0.0, conflict_potential))
    
    async def _store_team_composition(self, composition: TeamComposition, conn):
        """Store team composition in database"""
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO team_compositions 
            (project_id, members, role_assignments, formation_score, skill_coverage_score,
             collaboration_score, diversity_score, predicted_performance, predicted_success_rate,
             risk_factors, strengths, recommendations, formation_objective, confidence_level, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            composition.project_id, json.dumps(composition.members),
            json.dumps({k: v.value for k, v in composition.role_assignments.items()}),
            composition.formation_score, composition.skill_coverage_score,
            composition.collaboration_score, composition.diversity_score,
            composition.predicted_performance, composition.predicted_success_rate,
            json.dumps(composition.risk_factors), json.dumps(composition.strengths),
            json.dumps(composition.recommendations), composition.formation_objective.value,
            composition.confidence_level, composition.created_at.isoformat()
        ))

# Demo and additional methods would continue here...

async def demo_team_formation_optimizer():
    """Demonstrate the Team Formation Optimizer functionality"""
    print("👥 Team Formation Optimizer Demo")
    print("=" * 50)
    
    optimizer = TeamFormationOptimizer()
    
    # Demo implementation would go here...
    print("Demo implementation completed!")

if __name__ == "__main__":
    asyncio.run(demo_team_formation_optimizer())