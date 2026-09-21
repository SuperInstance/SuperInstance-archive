"""
Collaboration Compatibility Scorer

AI-powered system for assessing collaboration potential between individuals
based on work styles, skills, personality traits, and historical collaboration data.
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any, Set
from enum import Enum
import json
import numpy as np
from collections import defaultdict
import math

class WorkingStyle(Enum):
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    COLLABORATIVE = "collaborative"
    INDEPENDENT = "independent"
    DETAIL_ORIENTED = "detail_oriented"
    BIG_PICTURE = "big_picture"
    STRUCTURED = "structured"
    FLEXIBLE = "flexible"

class CommunicationStyle(Enum):
    DIRECT = "direct"
    DIPLOMATIC = "diplomatic"
    ENTHUSIASTIC = "enthusiastic"
    RESERVED = "reserved"
    VISUAL = "visual"
    VERBAL = "verbal"
    WRITTEN = "written"

class CollaborationPreference(Enum):
    FACE_TO_FACE = "face_to_face"
    REMOTE = "remote"
    HYBRID = "hybrid"
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    SMALL_GROUPS = "small_groups"
    LARGE_GROUPS = "large_groups"

class CompatibilityDimension(Enum):
    WORK_STYLE = "work_style"
    COMMUNICATION = "communication"
    SKILLS = "skills"
    PERSONALITY = "personality"
    VALUES = "values"
    GOALS = "goals"
    AVAILABILITY = "availability"
    EXPERIENCE = "experience"

@dataclass
class CollaboratorProfile:
    id: str = ""
    name: str = ""
    role: str = ""
    department: str = ""
    working_styles: List[WorkingStyle] = None
    communication_styles: List[CommunicationStyle] = None
    collaboration_preferences: List[CollaborationPreference] = None
    technical_skills: List[str] = None
    soft_skills: List[str] = None
    personality_traits: Dict[str, float] = None  # Big Five + work-specific traits
    core_values: List[str] = None
    career_goals: List[str] = None
    availability_score: float = 5.0  # 1-10 scale
    timezone: str = ""
    languages: List[str] = None
    experience_level: str = "intermediate"  # junior, intermediate, senior, expert
    collaboration_history: List[Dict[str, Any]] = None
    feedback_scores: Dict[str, float] = None  # peer feedback on collaboration
    preferred_project_types: List[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    def __post_init__(self):
        if self.working_styles is None:
            self.working_styles = []
        if self.communication_styles is None:
            self.communication_styles = []
        if self.collaboration_preferences is None:
            self.collaboration_preferences = []
        if self.technical_skills is None:
            self.technical_skills = []
        if self.soft_skills is None:
            self.soft_skills = []
        if self.personality_traits is None:
            self.personality_traits = {}
        if self.core_values is None:
            self.core_values = []
        if self.career_goals is None:
            self.career_goals = []
        if self.languages is None:
            self.languages = []
        if self.collaboration_history is None:
            self.collaboration_history = []
        if self.feedback_scores is None:
            self.feedback_scores = {}
        if self.preferred_project_types is None:
            self.preferred_project_types = []

@dataclass
class CompatibilityScore:
    person1_id: str = ""
    person2_id: str = ""
    overall_compatibility: float = 0.0
    dimension_scores: Dict[str, float] = None
    compatibility_factors: List[str] = None
    potential_challenges: List[str] = None
    collaboration_recommendations: List[str] = None
    ideal_project_types: List[str] = None
    predicted_success_rate: float = 0.5
    confidence_level: str = "medium"  # low, medium, high
    calculated_at: datetime = datetime.now()

    def __post_init__(self):
        if self.dimension_scores is None:
            self.dimension_scores = {}
        if self.compatibility_factors is None:
            self.compatibility_factors = []
        if self.potential_challenges is None:
            self.potential_challenges = []
        if self.collaboration_recommendations is None:
            self.collaboration_recommendations = []
        if self.ideal_project_types is None:
            self.ideal_project_types = []

@dataclass
class CollaborationOutcome:
    id: Optional[int] = None
    person1_id: str = ""
    person2_id: str = ""
    project_type: str = ""
    duration_days: int = 0
    success_rating: float = 5.0  # 1-10 scale
    efficiency_rating: float = 5.0
    satisfaction_rating: float = 5.0
    communication_quality: float = 5.0
    conflict_level: float = 2.0  # 1-10, lower is better
    deliverable_quality: float = 5.0
    would_collaborate_again: bool = True
    feedback_notes: str = ""
    challenges_faced: List[str] = None
    success_factors: List[str] = None
    completed_at: datetime = datetime.now()

    def __post_init__(self):
        if self.challenges_faced is None:
            self.challenges_faced = []
        if self.success_factors is None:
            self.success_factors = []

class CollaborationScorer:
    """AI-powered collaboration compatibility assessment system"""
    
    def __init__(self, db_path: str = "collaboration_compatibility.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the collaboration compatibility database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collaborator_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT,
                department TEXT,
                working_styles TEXT,
                communication_styles TEXT,
                collaboration_preferences TEXT,
                technical_skills TEXT,
                soft_skills TEXT,
                personality_traits TEXT,
                core_values TEXT,
                career_goals TEXT,
                availability_score REAL DEFAULT 5.0,
                timezone TEXT,
                languages TEXT,
                experience_level TEXT DEFAULT 'intermediate',
                collaboration_history TEXT,
                feedback_scores TEXT,
                preferred_project_types TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compatibility_scores (
                id INTEGER PRIMARY KEY,
                person1_id TEXT NOT NULL,
                person2_id TEXT NOT NULL,
                overall_compatibility REAL NOT NULL,
                dimension_scores TEXT,
                compatibility_factors TEXT,
                potential_challenges TEXT,
                collaboration_recommendations TEXT,
                ideal_project_types TEXT,
                predicted_success_rate REAL DEFAULT 0.5,
                confidence_level TEXT DEFAULT 'medium',
                calculated_at TEXT,
                FOREIGN KEY (person1_id) REFERENCES collaborator_profiles (id),
                FOREIGN KEY (person2_id) REFERENCES collaborator_profiles (id),
                UNIQUE(person1_id, person2_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collaboration_outcomes (
                id INTEGER PRIMARY KEY,
                person1_id TEXT NOT NULL,
                person2_id TEXT NOT NULL,
                project_type TEXT,
                duration_days INTEGER,
                success_rating REAL DEFAULT 5.0,
                efficiency_rating REAL DEFAULT 5.0,
                satisfaction_rating REAL DEFAULT 5.0,
                communication_quality REAL DEFAULT 5.0,
                conflict_level REAL DEFAULT 2.0,
                deliverable_quality REAL DEFAULT 5.0,
                would_collaborate_again BOOLEAN DEFAULT TRUE,
                feedback_notes TEXT,
                challenges_faced TEXT,
                success_factors TEXT,
                completed_at TEXT,
                FOREIGN KEY (person1_id) REFERENCES collaborator_profiles (id),
                FOREIGN KEY (person2_id) REFERENCES collaborator_profiles (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def add_collaborator_profile(self, profile: CollaboratorProfile) -> str:
        """Add or update a collaborator profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO collaborator_profiles 
            (id, name, role, department, working_styles, communication_styles,
             collaboration_preferences, technical_skills, soft_skills, personality_traits,
             core_values, career_goals, availability_score, timezone, languages,
             experience_level, collaboration_history, feedback_scores, preferred_project_types,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.id, profile.name, profile.role, profile.department,
            json.dumps([ws.value for ws in profile.working_styles]),
            json.dumps([cs.value for cs in profile.communication_styles]),
            json.dumps([cp.value for cp in profile.collaboration_preferences]),
            json.dumps(profile.technical_skills), json.dumps(profile.soft_skills),
            json.dumps(profile.personality_traits), json.dumps(profile.core_values),
            json.dumps(profile.career_goals), profile.availability_score,
            profile.timezone, json.dumps(profile.languages), profile.experience_level,
            json.dumps(profile.collaboration_history), json.dumps(profile.feedback_scores),
            json.dumps(profile.preferred_project_types),
            profile.created_at.isoformat(), profile.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        return profile.id
    
    async def calculate_compatibility_score(self, person1_id: str, person2_id: str) -> CompatibilityScore:
        """Calculate comprehensive compatibility score between two collaborators"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get both profiles
        cursor.execute("SELECT * FROM collaborator_profiles WHERE id IN (?, ?)", (person1_id, person2_id))
        profiles = cursor.fetchall()
        
        if len(profiles) != 2:
            conn.close()
            return CompatibilityScore(person1_id=person1_id, person2_id=person2_id)
        
        # Convert to dictionaries and parse JSON fields
        cols = [description[0] for description in cursor.description]
        profile1 = dict(zip(cols, profiles[0]))
        profile2 = dict(zip(cols, profiles[1]))
        
        for profile in [profile1, profile2]:
            profile['working_styles'] = json.loads(profile['working_styles']) if profile['working_styles'] else []
            profile['communication_styles'] = json.loads(profile['communication_styles']) if profile['communication_styles'] else []
            profile['collaboration_preferences'] = json.loads(profile['collaboration_preferences']) if profile['collaboration_preferences'] else []
            profile['technical_skills'] = json.loads(profile['technical_skills']) if profile['technical_skills'] else []
            profile['soft_skills'] = json.loads(profile['soft_skills']) if profile['soft_skills'] else []
            profile['personality_traits'] = json.loads(profile['personality_traits']) if profile['personality_traits'] else {}
            profile['core_values'] = json.loads(profile['core_values']) if profile['core_values'] else []
            profile['career_goals'] = json.loads(profile['career_goals']) if profile['career_goals'] else []
            profile['languages'] = json.loads(profile['languages']) if profile['languages'] else []
            profile['feedback_scores'] = json.loads(profile['feedback_scores']) if profile['feedback_scores'] else {}
            profile['preferred_project_types'] = json.loads(profile['preferred_project_types']) if profile['preferred_project_types'] else []
        
        # Calculate dimension scores
        dimension_scores = {}
        compatibility_factors = []
        potential_challenges = []
        collaboration_recommendations = []
        ideal_project_types = []
        
        # 1. Work Style Compatibility
        work_style_score = await self._calculate_work_style_compatibility(profile1, profile2)
        dimension_scores[CompatibilityDimension.WORK_STYLE.value] = work_style_score
        
        if work_style_score > 0.7:
            compatibility_factors.append("Highly compatible working styles")
        elif work_style_score < 0.4:
            potential_challenges.append("Significant differences in working styles")
            collaboration_recommendations.append("Establish clear role definitions and work processes")
        
        # 2. Communication Compatibility
        comm_score = await self._calculate_communication_compatibility(profile1, profile2)
        dimension_scores[CompatibilityDimension.COMMUNICATION.value] = comm_score
        
        if comm_score > 0.6:
            compatibility_factors.append("Compatible communication styles")
        else:
            potential_challenges.append("Communication style differences may cause friction")
            collaboration_recommendations.append("Establish communication protocols and regular check-ins")
        
        # 3. Skills Complementarity
        skills_score = await self._calculate_skills_compatibility(profile1, profile2)
        dimension_scores[CompatibilityDimension.SKILLS.value] = skills_score
        
        if skills_score > 0.7:
            compatibility_factors.append("Excellent skill complementarity")
            ideal_project_types.extend(["cross-functional projects", "skill-building initiatives"])
        elif skills_score > 0.5:
            compatibility_factors.append("Good skill balance")
        
        # 4. Personality Compatibility
        personality_score = await self._calculate_personality_compatibility(profile1, profile2)
        dimension_scores[CompatibilityDimension.PERSONALITY.value] = personality_score
        
        if personality_score > 0.6:
            compatibility_factors.append("Complementary personality traits")
        elif personality_score < 0.4:
            potential_challenges.append("Personality differences may require adjustment")
            collaboration_recommendations.append("Focus on understanding each other's working preferences")
        
        # 5. Values Alignment
        values_score = await self._calculate_values_alignment(profile1, profile2)
        dimension_scores[CompatibilityDimension.VALUES.value] = values_score
        
        if values_score > 0.7:
            compatibility_factors.append("Strong alignment on core values")
        elif values_score < 0.4:
            potential_challenges.append("Different core values may create tension")
        
        # 6. Goals Alignment
        goals_score = await self._calculate_goals_alignment(profile1, profile2)
        dimension_scores[CompatibilityDimension.GOALS.value] = goals_score
        
        if goals_score > 0.6:
            compatibility_factors.append("Aligned career and project goals")
            ideal_project_types.append("strategic initiatives")
        
        # 7. Availability Compatibility
        availability_score = await self._calculate_availability_compatibility(profile1, profile2)
        dimension_scores[CompatibilityDimension.AVAILABILITY.value] = availability_score
        
        if availability_score > 0.8:
            compatibility_factors.append("Excellent availability alignment")
        elif availability_score < 0.5:
            potential_challenges.append("Scheduling conflicts may impact collaboration")
            collaboration_recommendations.append("Use asynchronous work methods when possible")
        
        # 8. Experience Level Compatibility
        experience_score = await self._calculate_experience_compatibility(profile1, profile2)
        dimension_scores[CompatibilityDimension.EXPERIENCE.value] = experience_score
        
        if experience_score > 0.7:
            compatibility_factors.append("Compatible experience levels")
        elif abs(profile1.get('experience_level', 'intermediate') != profile2.get('experience_level', 'intermediate')):
            collaboration_recommendations.append("Leverage experience differences for mentoring opportunities")
            ideal_project_types.append("mentorship projects")
        
        # Calculate overall compatibility (weighted average)
        weights = {
            CompatibilityDimension.WORK_STYLE.value: 0.20,
            CompatibilityDimension.COMMUNICATION.value: 0.18,
            CompatibilityDimension.SKILLS.value: 0.15,
            CompatibilityDimension.PERSONALITY.value: 0.15,
            CompatibilityDimension.VALUES.value: 0.12,
            CompatibilityDimension.GOALS.value: 0.10,
            CompatibilityDimension.AVAILABILITY.value: 0.05,
            CompatibilityDimension.EXPERIENCE.value: 0.05
        }
        
        overall_compatibility = sum(
            dimension_scores.get(dimension, 0) * weight 
            for dimension, weight in weights.items()
        )
        
        # Predict success rate based on historical data and compatibility
        predicted_success_rate = await self._predict_collaboration_success(
            person1_id, person2_id, overall_compatibility, conn
        )
        
        # Determine confidence level
        data_points = len(profile1.get('collaboration_history', [])) + len(profile2.get('collaboration_history', []))
        if data_points >= 10:
            confidence_level = "high"
        elif data_points >= 5:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        
        # Add general recommendations
        if overall_compatibility > 0.7:
            collaboration_recommendations.insert(0, "Excellent collaboration potential - leverage complementary strengths")
        elif overall_compatibility > 0.5:
            collaboration_recommendations.insert(0, "Good collaboration potential with proper planning")
        else:
            collaboration_recommendations.insert(0, "Requires careful management and clear structure")
        
        # Create compatibility score object
        compatibility_score = CompatibilityScore(
            person1_id=person1_id,
            person2_id=person2_id,
            overall_compatibility=overall_compatibility,
            dimension_scores=dimension_scores,
            compatibility_factors=compatibility_factors,
            potential_challenges=potential_challenges,
            collaboration_recommendations=collaboration_recommendations,
            ideal_project_types=list(set(ideal_project_types)),
            predicted_success_rate=predicted_success_rate,
            confidence_level=confidence_level
        )
        
        # Store the score
        await self._store_compatibility_score(compatibility_score, conn)
        
        conn.close()
        return compatibility_score
    
    async def _calculate_work_style_compatibility(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate work style compatibility score"""
        styles1 = set(profile1.get('working_styles', []))
        styles2 = set(profile2.get('working_styles', []))
        
        if not styles1 or not styles2:
            return 0.5  # Neutral score if no data
        
        # Define complementary and conflicting style pairs
        complementary_pairs = {
            ('analytical', 'creative'), ('detail_oriented', 'big_picture'),
            ('structured', 'flexible'), ('independent', 'collaborative')
        }
        
        conflicting_pairs = {
            ('structured', 'chaotic'), ('detail_oriented', 'careless'),
            ('collaborative', 'isolated')
        }
        
        # Calculate compatibility
        total_combinations = len(styles1) * len(styles2)
        compatibility_score = 0.0
        
        for style1 in styles1:
            for style2 in styles2:
                if style1 == style2:
                    compatibility_score += 0.8  # Same styles are mostly compatible
                elif (style1, style2) in complementary_pairs or (style2, style1) in complementary_pairs:
                    compatibility_score += 1.0  # Complementary styles are highly compatible
                elif (style1, style2) in conflicting_pairs or (style2, style1) in conflicting_pairs:
                    compatibility_score += 0.2  # Conflicting styles have low compatibility
                else:
                    compatibility_score += 0.6  # Neutral compatibility
        
        return min(1.0, compatibility_score / total_combinations) if total_combinations > 0 else 0.5
    
    async def _calculate_communication_compatibility(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate communication compatibility score"""
        comm1 = set(profile1.get('communication_styles', []))
        comm2 = set(profile2.get('communication_styles', []))
        
        if not comm1 or not comm2:
            return 0.5
        
        # Shared communication styles
        shared_styles = comm1 & comm2
        shared_score = len(shared_styles) / max(len(comm1), len(comm2)) if max(len(comm1), len(comm2)) > 0 else 0
        
        # Complementary communication styles
        complementary_pairs = {
            ('direct', 'diplomatic'), ('enthusiastic', 'reserved'),
            ('visual', 'verbal'), ('written', 'verbal')
        }
        
        complementary_score = 0.0
        total_pairs = len(comm1) * len(comm2)
        
        for c1 in comm1:
            for c2 in comm2:
                if (c1, c2) in complementary_pairs or (c2, c1) in complementary_pairs:
                    complementary_score += 0.8
        
        complementary_score = complementary_score / total_pairs if total_pairs > 0 else 0
        
        return min(1.0, (shared_score * 0.6) + (complementary_score * 0.4))
    
    async def _calculate_skills_compatibility(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate skills compatibility and complementarity"""
        tech_skills1 = set(profile1.get('technical_skills', []))
        tech_skills2 = set(profile2.get('technical_skills', []))
        soft_skills1 = set(profile1.get('soft_skills', []))
        soft_skills2 = set(profile2.get('soft_skills', []))
        
        # Technical skills overlap (some overlap is good, too much may be redundant)
        tech_overlap = len(tech_skills1 & tech_skills2)
        tech_total = len(tech_skills1 | tech_skills2)
        tech_complementarity = (tech_total - tech_overlap) / tech_total if tech_total > 0 else 0
        
        # Soft skills overlap (high overlap is generally good)
        soft_overlap = len(soft_skills1 & soft_skills2)
        soft_total = max(len(soft_skills1), len(soft_skills2))
        soft_compatibility = soft_overlap / soft_total if soft_total > 0 else 0
        
        # Ideal technical complementarity is around 60-80%
        if 0.6 <= tech_complementarity <= 0.8:
            tech_score = 1.0
        elif tech_complementarity > 0.8:
            tech_score = 0.8  # Too little overlap
        else:
            tech_score = tech_complementarity / 0.6  # Scale up low complementarity
        
        return (tech_score * 0.6) + (soft_compatibility * 0.4)
    
    async def _calculate_personality_compatibility(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate personality compatibility using Big Five traits"""
        traits1 = profile1.get('personality_traits', {})
        traits2 = profile2.get('personality_traits', {})
        
        if not traits1 or not traits2:
            return 0.5
        
        # Big Five traits and their collaboration implications
        trait_weights = {
            'openness': 0.2,        # Similar openness helps with idea generation
            'conscientiousness': 0.25,  # Both should be reasonably conscientious
            'extraversion': 0.15,   # Can be complementary
            'agreeableness': 0.25,  # High agreeableness helps collaboration
            'neuroticism': 0.15     # Lower neuroticism is generally better
        }
        
        compatibility_score = 0.0
        total_weight = 0.0
        
        for trait, weight in trait_weights.items():
            if trait in traits1 and trait in traits2:
                val1, val2 = traits1[trait], traits2[trait]
                
                if trait == 'neuroticism':
                    # For neuroticism, lower values are better, and similar low values are ideal
                    trait_score = 1.0 - (abs(val1 - val2) * 0.5) - (max(val1, val2) * 0.3)
                elif trait == 'extraversion':
                    # Extraversion can be complementary (one high, one medium is okay)
                    if abs(val1 - val2) <= 0.3:
                        trait_score = 1.0
                    else:
                        trait_score = 0.8  # Still okay if complementary
                else:
                    # For other traits, similarity is generally good
                    trait_score = 1.0 - abs(val1 - val2)
                
                compatibility_score += trait_score * weight
                total_weight += weight
        
        return min(1.0, compatibility_score / total_weight) if total_weight > 0 else 0.5
    
    async def _calculate_values_alignment(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate alignment on core values"""
        values1 = set(profile1.get('core_values', []))
        values2 = set(profile2.get('core_values', []))
        
        if not values1 or not values2:
            return 0.5
        
        shared_values = values1 & values2
        total_unique_values = values1 | values2
        
        return len(shared_values) / len(total_unique_values) if total_unique_values else 0
    
    async def _calculate_goals_alignment(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate alignment on career and project goals"""
        goals1 = set(profile1.get('career_goals', []))
        goals2 = set(profile2.get('career_goals', []))
        
        if not goals1 or not goals2:
            return 0.5
        
        shared_goals = goals1 & goals2
        total_goals = goals1 | goals2
        
        return len(shared_goals) / len(total_goals) if total_goals else 0
    
    async def _calculate_availability_compatibility(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate availability and timezone compatibility"""
        avail1 = profile1.get('availability_score', 5.0)
        avail2 = profile2.get('availability_score', 5.0)
        
        timezone1 = profile1.get('timezone', '')
        timezone2 = profile2.get('timezone', '')
        
        # Availability score compatibility (higher is better, similar is ideal)
        avail_score = 1.0 - (abs(avail1 - avail2) / 10.0)
        
        # Timezone compatibility (same timezone is best)
        timezone_score = 1.0 if timezone1 == timezone2 else 0.7
        
        return (avail_score * 0.6) + (timezone_score * 0.4)
    
    async def _calculate_experience_compatibility(self, profile1: Dict, profile2: Dict) -> float:
        """Calculate experience level compatibility"""
        exp_levels = {'junior': 1, 'intermediate': 2, 'senior': 3, 'expert': 4}
        
        exp1 = exp_levels.get(profile1.get('experience_level', 'intermediate'), 2)
        exp2 = exp_levels.get(profile2.get('experience_level', 'intermediate'), 2)
        
        exp_diff = abs(exp1 - exp2)
        
        if exp_diff == 0:
            return 1.0  # Same level is ideal
        elif exp_diff == 1:
            return 0.8  # One level difference can be complementary
        elif exp_diff == 2:
            return 0.6  # Two levels can work with mentoring
        else:
            return 0.4  # Large experience gaps may be challenging
    
    async def _predict_collaboration_success(self, person1_id: str, person2_id: str, 
                                           compatibility_score: float, conn) -> float:
        """Predict collaboration success based on compatibility and historical data"""
        cursor = conn.cursor()
        
        # Get historical collaboration outcomes for both people
        cursor.execute("""
            SELECT AVG(success_rating) as avg_success
            FROM collaboration_outcomes 
            WHERE person1_id = ? OR person2_id = ?
        """, (person1_id, person1_id))
        
        person1_history = cursor.fetchone()[0] or 5.0
        
        cursor.execute("""
            SELECT AVG(success_rating) as avg_success
            FROM collaboration_outcomes 
            WHERE person1_id = ? OR person2_id = ?
        """, (person2_id, person2_id))
        
        person2_history = cursor.fetchone()[0] or 5.0
        
        # Normalize historical success (convert from 1-10 to 0-1 scale)
        person1_success_rate = person1_history / 10.0
        person2_success_rate = person2_history / 10.0
        
        # Combine compatibility score with historical performance
        predicted_success = (
            compatibility_score * 0.6 +
            person1_success_rate * 0.2 +
            person2_success_rate * 0.2
        )
        
        return min(1.0, predicted_success)
    
    async def _store_compatibility_score(self, score: CompatibilityScore, conn):
        """Store compatibility score in database"""
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO compatibility_scores 
            (person1_id, person2_id, overall_compatibility, dimension_scores,
             compatibility_factors, potential_challenges, collaboration_recommendations,
             ideal_project_types, predicted_success_rate, confidence_level, calculated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            score.person1_id, score.person2_id, score.overall_compatibility,
            json.dumps(score.dimension_scores), json.dumps(score.compatibility_factors),
            json.dumps(score.potential_challenges), json.dumps(score.collaboration_recommendations),
            json.dumps(score.ideal_project_types), score.predicted_success_rate,
            score.confidence_level, score.calculated_at.isoformat()
        ))
    
    async def record_collaboration_outcome(self, outcome: CollaborationOutcome) -> int:
        """Record the outcome of a collaboration for learning and improvement"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO collaboration_outcomes 
            (person1_id, person2_id, project_type, duration_days, success_rating,
             efficiency_rating, satisfaction_rating, communication_quality, conflict_level,
             deliverable_quality, would_collaborate_again, feedback_notes,
             challenges_faced, success_factors, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            outcome.person1_id, outcome.person2_id, outcome.project_type, outcome.duration_days,
            outcome.success_rating, outcome.efficiency_rating, outcome.satisfaction_rating,
            outcome.communication_quality, outcome.conflict_level, outcome.deliverable_quality,
            outcome.would_collaborate_again, outcome.feedback_notes,
            json.dumps(outcome.challenges_faced), json.dumps(outcome.success_factors),
            outcome.completed_at.isoformat()
        ))
        
        outcome_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return outcome_id
    
    async def find_best_collaborators(self, person_id: str, project_type: str = "", 
                                    limit: int = 5) -> List[Dict[str, Any]]:
        """Find the best collaboration matches for a person"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all potential collaborators (excluding the person)
        cursor.execute("SELECT id, name, role FROM collaborator_profiles WHERE id != ?", (person_id,))
        potential_collaborators = cursor.fetchall()
        
        collaboration_matches = []
        
        for collaborator_id, name, role in potential_collaborators:
            # Check if compatibility score exists
            cursor.execute("""
                SELECT * FROM compatibility_scores 
                WHERE (person1_id = ? AND person2_id = ?) OR (person1_id = ? AND person2_id = ?)
            """, (person_id, collaborator_id, collaborator_id, person_id))
            
            existing_score = cursor.fetchone()
            
            if existing_score:
                cols = [description[0] for description in cursor.description]
                score_dict = dict(zip(cols, existing_score))
                
                compatibility_score = score_dict['overall_compatibility']
                ideal_projects = json.loads(score_dict['ideal_project_types']) if score_dict['ideal_project_types'] else []
                recommendations = json.loads(score_dict['collaboration_recommendations']) if score_dict['collaboration_recommendations'] else []
            else:
                # Calculate new compatibility score
                score_obj = await self.calculate_compatibility_score(person_id, collaborator_id)
                compatibility_score = score_obj.overall_compatibility
                ideal_projects = score_obj.ideal_project_types
                recommendations = score_obj.collaboration_recommendations
            
            # Filter by project type if specified
            project_match = True
            if project_type:
                project_match = any(project_type.lower() in proj.lower() for proj in ideal_projects)
                if not project_match:
                    # Still include if general compatibility is very high
                    project_match = compatibility_score > 0.8
            
            if project_match:
                collaboration_matches.append({
                    'person_id': collaborator_id,
                    'name': name,
                    'role': role,
                    'compatibility_score': compatibility_score,
                    'ideal_project_types': ideal_projects,
                    'recommendations': recommendations[:2]  # Top 2 recommendations
                })
        
        # Sort by compatibility score
        collaboration_matches.sort(key=lambda x: x['compatibility_score'], reverse=True)
        
        conn.close()
        return collaboration_matches[:limit]
    
    async def get_collaboration_analytics(self, days_back: int = 90) -> Dict[str, Any]:
        """Get analytics on collaboration patterns and success rates"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        # Overall success metrics
        cursor.execute("""
            SELECT AVG(success_rating) as avg_success,
                   AVG(efficiency_rating) as avg_efficiency,
                   AVG(satisfaction_rating) as avg_satisfaction,
                   AVG(communication_quality) as avg_communication,
                   AVG(conflict_level) as avg_conflict,
                   COUNT(*) as total_collaborations,
                   SUM(CASE WHEN would_collaborate_again THEN 1 ELSE 0 END) as would_repeat
            FROM collaboration_outcomes 
            WHERE completed_at >= ?
        """, (start_date.isoformat(),))
        
        overall_stats = cursor.fetchone()
        
        # Success rate by project type
        cursor.execute("""
            SELECT project_type, 
                   AVG(success_rating) as avg_success,
                   COUNT(*) as count
            FROM collaboration_outcomes 
            WHERE completed_at >= ?
            GROUP BY project_type
            ORDER BY avg_success DESC
        """, (start_date.isoformat(),))
        
        project_type_stats = {}
        for row in cursor.fetchall():
            project_type_stats[row[0]] = {
                'average_success': round(row[1], 2),
                'collaboration_count': row[2]
            }
        
        # Compatibility score vs actual success correlation
        cursor.execute("""
            SELECT cs.overall_compatibility, co.success_rating
            FROM compatibility_scores cs
            JOIN collaboration_outcomes co ON 
                (cs.person1_id = co.person1_id AND cs.person2_id = co.person2_id) OR
                (cs.person1_id = co.person2_id AND cs.person2_id = co.person1_id)
            WHERE co.completed_at >= ?
        """, (start_date.isoformat(),))
        
        compatibility_vs_success = cursor.fetchall()
        
        # Calculate correlation if we have data
        if compatibility_vs_success:
            comp_scores = [row[0] for row in compatibility_vs_success]
            success_scores = [row[1] / 10.0 for row in compatibility_vs_success]  # Normalize to 0-1
            
            if len(comp_scores) > 1:
                correlation = np.corrcoef(comp_scores, success_scores)[0, 1]
            else:
                correlation = 0.0
        else:
            correlation = 0.0
        
        conn.close()
        
        return {
            'analysis_period_days': days_back,
            'total_collaborations': overall_stats[5] if overall_stats else 0,
            'average_success_rating': round(overall_stats[0], 2) if overall_stats and overall_stats[0] else 0,
            'average_efficiency_rating': round(overall_stats[1], 2) if overall_stats and overall_stats[1] else 0,
            'average_satisfaction_rating': round(overall_stats[2], 2) if overall_stats and overall_stats[2] else 0,
            'average_communication_quality': round(overall_stats[3], 2) if overall_stats and overall_stats[3] else 0,
            'average_conflict_level': round(overall_stats[4], 2) if overall_stats and overall_stats[4] else 0,
            'repeat_collaboration_rate': round((overall_stats[6] / overall_stats[5] * 100), 1) if overall_stats and overall_stats[5] > 0 else 0,
            'project_type_performance': project_type_stats,
            'compatibility_success_correlation': round(correlation, 3) if not math.isnan(correlation) else 0,
            'model_accuracy': 'High' if abs(correlation) > 0.6 else 'Medium' if abs(correlation) > 0.3 else 'Low'
        }

# Demo function
async def demo_collaboration_scorer():
    """Demonstrate the Collaboration Scorer functionality"""
    print("🤝 Collaboration Compatibility Scorer Demo")
    print("=" * 60)
    
    scorer = CollaborationScorer()
    
    # Create collaborator profiles
    print("\n1. Creating Collaborator Profiles...")
    profiles = [
        CollaboratorProfile(
            id="emma_s",
            name="Emma Rodriguez",
            role="Product Manager",
            department="Product",
            working_styles=[WorkingStyle.ANALYTICAL, WorkingStyle.STRUCTURED, WorkingStyle.COLLABORATIVE],
            communication_styles=[CommunicationStyle.DIRECT, CommunicationStyle.VISUAL],
            collaboration_preferences=[CollaborationPreference.HYBRID, CollaborationPreference.SYNCHRONOUS, CollaborationPreference.SMALL_GROUPS],
            technical_skills=["product strategy", "data analysis", "user research", "agile methodology"],
            soft_skills=["leadership", "communication", "problem solving", "stakeholder management"],
            personality_traits={
                "openness": 0.7, "conscientiousness": 0.9, "extraversion": 0.6,
                "agreeableness": 0.8, "neuroticism": 0.2
            },
            core_values=["innovation", "user focus", "data-driven decisions", "collaboration"],
            career_goals=["lead product team", "launch successful product", "mentor others"],
            availability_score=8.0,
            timezone="PST",
            languages=["English", "Spanish"],
            experience_level="senior",
            feedback_scores={"collaboration": 8.5, "communication": 9.0, "leadership": 8.0},
            preferred_project_types=["product launches", "strategy projects", "cross-functional initiatives"]
        ),
        CollaboratorProfile(
            id="james_c",
            name="James Chen",
            role="Senior Engineer",
            department="Engineering",
            working_styles=[WorkingStyle.ANALYTICAL, WorkingStyle.DETAIL_ORIENTED, WorkingStyle.INDEPENDENT],
            communication_styles=[CommunicationStyle.WRITTEN, CommunicationStyle.DIRECT],
            collaboration_preferences=[CollaborationPreference.REMOTE, CollaborationPreference.ASYNCHRONOUS, CollaborationPreference.SMALL_GROUPS],
            technical_skills=["python", "system architecture", "machine learning", "API design"],
            soft_skills=["attention to detail", "technical mentoring", "problem solving"],
            personality_traits={
                "openness": 0.8, "conscientiousness": 0.9, "extraversion": 0.3,
                "agreeableness": 0.7, "neuroticism": 0.3
            },
            core_values=["technical excellence", "continuous learning", "quality", "efficiency"],
            career_goals=["become tech lead", "contribute to open source", "build scalable systems"],
            availability_score=7.0,
            timezone="PST",
            languages=["English", "Mandarin"],
            experience_level="senior",
            feedback_scores={"technical_skills": 9.5, "collaboration": 7.0, "mentoring": 8.5},
            preferred_project_types=["technical projects", "architecture design", "performance optimization"]
        ),
        CollaboratorProfile(
            id="maya_p",
            name="Maya Patel",
            role="UX Designer",
            department="Design",
            working_styles=[WorkingStyle.CREATIVE, WorkingStyle.COLLABORATIVE, WorkingStyle.FLEXIBLE],
            communication_styles=[CommunicationStyle.VISUAL, CommunicationStyle.ENTHUSIASTIC],
            collaboration_preferences=[CollaborationPreference.HYBRID, CollaborationPreference.SYNCHRONOUS, CollaborationPreference.SMALL_GROUPS],
            technical_skills=["user research", "prototyping", "design systems", "usability testing"],
            soft_skills=["creativity", "empathy", "communication", "user advocacy"],
            personality_traits={
                "openness": 0.9, "conscientiousness": 0.7, "extraversion": 0.8,
                "agreeableness": 0.9, "neuroticism": 0.2
            },
            core_values=["user experience", "inclusivity", "creativity", "collaboration"],
            career_goals=["lead design team", "create impactful designs", "mentor designers"],
            availability_score=8.5,
            timezone="EST",
            languages=["English", "Hindi"],
            experience_level="senior",
            feedback_scores={"design_quality": 9.0, "collaboration": 9.5, "user_advocacy": 9.0},
            preferred_project_types=["user experience projects", "design systems", "research projects"]
        ),
        CollaboratorProfile(
            id="alex_k",
            name="Alex Kim",
            role="Junior Developer",
            department="Engineering",
            working_styles=[WorkingStyle.DETAIL_ORIENTED, WorkingStyle.COLLABORATIVE, WorkingStyle.FLEXIBLE],
            communication_styles=[CommunicationStyle.ENTHUSIASTIC, CommunicationStyle.VERBAL],
            collaboration_preferences=[CollaborationPreference.HYBRID, CollaborationPreference.SYNCHRONOUS, CollaborationPreference.SMALL_GROUPS],
            technical_skills=["javascript", "react", "testing", "git"],
            soft_skills=["eagerness to learn", "adaptability", "teamwork"],
            personality_traits={
                "openness": 0.8, "conscientiousness": 0.8, "extraversion": 0.7,
                "agreeableness": 0.8, "neuroticism": 0.4
            },
            core_values=["learning", "growth", "teamwork", "quality"],
            career_goals=["become senior developer", "learn new technologies", "contribute meaningfully"],
            availability_score=9.0,
            timezone="PST",
            languages=["English", "Korean"],
            experience_level="junior",
            feedback_scores={"learning_attitude": 9.0, "collaboration": 8.0, "code_quality": 7.0},
            preferred_project_types=["feature development", "learning projects", "pair programming"]
        )
    ]
    
    for profile in profiles:
        await scorer.add_collaborator_profile(profile)
        print(f"✅ Added profile: {profile.name} ({profile.role})")
    
    # Calculate compatibility scores
    print("\n2. Calculating Compatibility Scores...")
    test_pairs = [
        ("emma_s", "james_c", "Product Manager ↔ Senior Engineer"),
        ("emma_s", "maya_p", "Product Manager ↔ UX Designer"),
        ("james_c", "alex_k", "Senior Engineer ↔ Junior Developer"),
        ("maya_p", "alex_k", "UX Designer ↔ Junior Developer")
    ]
    
    for person1, person2, description in test_pairs:
        compatibility = await scorer.calculate_compatibility_score(person1, person2)
        print(f"\n🎯 {description}:")
        print(f"   Overall Compatibility: {compatibility.overall_compatibility:.3f}")
        print(f"   Predicted Success Rate: {compatibility.predicted_success_rate:.3f}")
        print(f"   Confidence Level: {compatibility.confidence_level}")
        
        if compatibility.compatibility_factors:
            print(f"   ✅ Strengths: {compatibility.compatibility_factors[0]}")
        if compatibility.potential_challenges:
            print(f"   ⚠️  Challenges: {compatibility.potential_challenges[0]}")
        if compatibility.collaboration_recommendations:
            print(f"   💡 Recommendation: {compatibility.collaboration_recommendations[0]}")
    
    # Find best collaborators
    print("\n3. Finding Best Collaborators for Emma (Product Manager)...")
    best_matches = await scorer.find_best_collaborators("emma_s", "", 3)
    
    for i, match in enumerate(best_matches, 1):
        print(f"\n🏆 Match {i}: {match['name']} ({match['role']})")
        print(f"   Compatibility Score: {match['compatibility_score']:.3f}")
        if match['ideal_project_types']:
            print(f"   Ideal Projects: {', '.join(match['ideal_project_types'][:2])}")
        if match['recommendations']:
            print(f"   Key Recommendation: {match['recommendations'][0]}")
    
    # Record some collaboration outcomes
    print("\n4. Recording Collaboration Outcomes...")
    outcomes = [
        CollaborationOutcome(
            person1_id="emma_s",
            person2_id="maya_p",
            project_type="user experience project",
            duration_days=45,
            success_rating=8.5,
            efficiency_rating=8.0,
            satisfaction_rating=9.0,
            communication_quality=9.5,
            conflict_level=1.5,
            deliverable_quality=8.5,
            would_collaborate_again=True,
            feedback_notes="Excellent collaboration with great communication and shared vision",
            success_factors=["clear communication", "shared user focus", "complementary skills"],
            challenges_faced=["timezone differences", "initial scope creep"]
        ),
        CollaborationOutcome(
            person1_id="james_c",
            person2_id="alex_k",
            project_type="mentorship project",
            duration_days=90,
            success_rating=9.0,
            efficiency_rating=7.5,
            satisfaction_rating=9.5,
            communication_quality=8.0,
            conflict_level=1.0,
            deliverable_quality=8.0,
            would_collaborate_again=True,
            feedback_notes="Great mentoring relationship with significant skill development",
            success_factors=["patient mentoring", "eager learning", "structured approach"],
            challenges_faced=["initial knowledge gap", "time management"]
        )
    ]
    
    for outcome in outcomes:
        outcome_id = await scorer.record_collaboration_outcome(outcome)
        person1_name = next(p.name for p in profiles if p.id == outcome.person1_id)
        person2_name = next(p.name for p in profiles if p.id == outcome.person2_id)
        print(f"📝 Recorded outcome: {person1_name} & {person2_name} - Success: {outcome.success_rating}/10")
    
    # Get analytics
    print("\n5. Collaboration Analytics...")
    analytics = await scorer.get_collaboration_analytics(90)
    
    print(f"📊 Analysis Period: {analytics['analysis_period_days']} days")
    print(f"📊 Total Collaborations: {analytics['total_collaborations']}")
    print(f"📊 Average Success Rating: {analytics['average_success_rating']}/10")
    print(f"📊 Average Efficiency: {analytics['average_efficiency_rating']}/10")
    print(f"📊 Average Satisfaction: {analytics['average_satisfaction_rating']}/10")
    print(f"📊 Repeat Collaboration Rate: {analytics['repeat_collaboration_rate']}%")
    print(f"📊 Model Accuracy: {analytics['model_accuracy']}")
    print(f"📊 Compatibility-Success Correlation: {analytics['compatibility_success_correlation']}")
    
    if analytics['project_type_performance']:
        print(f"\nProject Type Performance:")
        for proj_type, stats in analytics['project_type_performance'].items():
            print(f"   {proj_type}: {stats['average_success']}/10 ({stats['collaboration_count']} collaborations)")
    
    print("\n✅ Collaboration Scorer Demo Complete!")

if __name__ == "__main__":
    asyncio.run(demo_collaboration_scorer())