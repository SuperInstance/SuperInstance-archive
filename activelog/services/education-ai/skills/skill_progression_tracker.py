"""
Skill Progression Tracking System

Advanced AI system for tracking student skill development, competency mastery,
and learning progression through comprehensive assessment data analysis,
skill mapping, and adaptive progression pathways.
"""

import asyncio
import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MasteryLevel(Enum):
    NOT_STARTED = "not_started"
    NOVICE = "novice"
    DEVELOPING = "developing"
    PROFICIENT = "proficient"
    ADVANCED = "advanced"
    EXPERT = "expert"

class ProgressionStatus(Enum):
    ON_TRACK = "on_track"
    AHEAD = "ahead"
    BEHIND = "behind"
    STAGNANT = "stagnant"
    REGRESSING = "regressing"

class AssessmentType(Enum):
    FORMATIVE = "formative"
    SUMMATIVE = "summative"
    DIAGNOSTIC = "diagnostic"
    SELF_ASSESSMENT = "self_assessment"
    PEER_ASSESSMENT = "peer_assessment"

class SkillCategory(Enum):
    COGNITIVE = "cognitive"
    PROCEDURAL = "procedural"
    CONCEPTUAL = "conceptual"
    METACOGNITIVE = "metacognitive"
    COLLABORATIVE = "collaborative"

@dataclass
class SkillDefinition:
    skill_id: str
    skill_name: str
    category: SkillCategory
    description: str
    prerequisite_skills: List[str] = field(default_factory=list)
    dependent_skills: List[str] = field(default_factory=list)
    mastery_criteria: Dict[str, Any] = field(default_factory=dict)
    difficulty_level: int = 1
    estimated_learning_hours: float = 10.0

@dataclass
class SkillAssessment:
    assessment_id: str
    student_id: str
    skill_id: str
    assessment_type: AssessmentType
    score: float
    max_score: float
    timestamp: datetime = field(default_factory=datetime.now)
    assessor: str = "system"
    rubric_scores: Dict[str, float] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    feedback: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SkillProgression:
    student_id: str
    skill_id: str
    current_mastery_level: MasteryLevel
    mastery_score: float
    progression_rate: float
    time_to_mastery_estimate: Optional[float] = None
    progression_status: ProgressionStatus = ProgressionStatus.ON_TRACK
    recent_assessments: List[str] = field(default_factory=list)
    skill_milestones: Dict[str, datetime] = field(default_factory=dict)
    learning_interventions: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class LearningMilestone:
    milestone_id: str
    skill_id: str
    milestone_name: str
    description: str
    mastery_threshold: float
    evidence_required: List[str] = field(default_factory=list)
    competency_indicators: List[str] = field(default_factory=list)

@dataclass
class ProgressionAnalytics:
    student_id: str
    analysis_date: datetime
    overall_progression_rate: float
    skills_mastered: int
    skills_in_progress: int
    skills_at_risk: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    growth_areas: List[str] = field(default_factory=list)
    recommended_focus: List[str] = field(default_factory=list)
    predicted_outcomes: Dict[str, Any] = field(default_factory=dict)

class SkillProgressionTracker:
    def __init__(self, db_path: str = "education_ai.db"):
        self.db_path = db_path
        self.ml_model = LinearRegression()
        self.scaler = StandardScaler()
        self.skill_definitions = {}
        self.mastery_thresholds = {
            MasteryLevel.NOT_STARTED: 0.0,
            MasteryLevel.NOVICE: 0.25,
            MasteryLevel.DEVELOPING: 0.50,
            MasteryLevel.PROFICIENT: 0.75,
            MasteryLevel.ADVANCED: 0.90,
            MasteryLevel.EXPERT: 0.95
        }
        self.init_database()
        self._load_skill_definitions()
        
    def init_database(self):
        """Initialize database tables for skill progression tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_definitions (
                skill_id TEXT PRIMARY KEY,
                skill_name TEXT,
                category TEXT,
                description TEXT,
                prerequisite_skills TEXT,
                dependent_skills TEXT,
                mastery_criteria TEXT,
                difficulty_level INTEGER,
                estimated_learning_hours REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_assessments (
                assessment_id TEXT PRIMARY KEY,
                student_id TEXT,
                skill_id TEXT,
                assessment_type TEXT,
                score REAL,
                max_score REAL,
                timestamp TIMESTAMP,
                assessor TEXT,
                rubric_scores TEXT,
                evidence TEXT,
                feedback TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_progressions (
                progression_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                skill_id TEXT,
                current_mastery_level TEXT,
                mastery_score REAL,
                progression_rate REAL,
                time_to_mastery_estimate REAL,
                progression_status TEXT,
                recent_assessments TEXT,
                skill_milestones TEXT,
                learning_interventions TEXT,
                last_updated TIMESTAMP,
                UNIQUE(student_id, skill_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_milestones (
                milestone_id TEXT PRIMARY KEY,
                skill_id TEXT,
                milestone_name TEXT,
                description TEXT,
                mastery_threshold REAL,
                evidence_required TEXT,
                competency_indicators TEXT,
                FOREIGN KEY (skill_id) REFERENCES skill_definitions (skill_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS progression_analytics (
                analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                analysis_date TIMESTAMP,
                overall_progression_rate REAL,
                skills_mastered INTEGER,
                skills_in_progress INTEGER,
                skills_at_risk TEXT,
                strengths TEXT,
                growth_areas TEXT,
                recommended_focus TEXT,
                predicted_outcomes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competency_badges (
                badge_id TEXT PRIMARY KEY,
                student_id TEXT,
                skill_id TEXT,
                badge_name TEXT,
                earned_date TIMESTAMP,
                evidence_portfolio TEXT,
                verifier TEXT,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Skill progression tracking database initialized")

    def _load_skill_definitions(self):
        """Load predefined skill definitions and create sample skills"""
        skill_definitions = [
            SkillDefinition(
                "reading_comprehension",
                "Reading Comprehension",
                SkillCategory.COGNITIVE,
                "Ability to understand and interpret written text",
                [],
                ["literary_analysis", "research_skills"],
                {"accuracy": 0.8, "speed": 200, "complexity_level": 3},
                1,
                20.0
            ),
            SkillDefinition(
                "mathematical_reasoning",
                "Mathematical Reasoning",
                SkillCategory.COGNITIVE,
                "Logical thinking and problem-solving with mathematical concepts",
                ["basic_arithmetic"],
                ["advanced_mathematics", "statistics"],
                {"problem_solving": 0.75, "logical_steps": 0.8},
                3,
                30.0
            ),
            SkillDefinition(
                "scientific_inquiry",
                "Scientific Inquiry",
                SkillCategory.PROCEDURAL,
                "Process of investigating and understanding natural phenomena",
                ["reading_comprehension"],
                ["experimental_design", "data_analysis"],
                {"hypothesis_formation": 0.7, "data_collection": 0.8},
                4,
                40.0
            ),
            SkillDefinition(
                "collaborative_problem_solving",
                "Collaborative Problem Solving",
                SkillCategory.COLLABORATIVE,
                "Working effectively with others to solve complex problems",
                [],
                ["leadership", "project_management"],
                {"teamwork": 0.8, "communication": 0.75, "conflict_resolution": 0.7},
                3,
                25.0
            ),
            SkillDefinition(
                "critical_thinking",
                "Critical Thinking",
                SkillCategory.METACOGNITIVE,
                "Analyzing and evaluating information to form reasoned judgments",
                ["reading_comprehension"],
                ["research_skills", "academic_writing"],
                {"analysis": 0.8, "evaluation": 0.75, "inference": 0.7},
                4,
                35.0
            ),
            SkillDefinition(
                "digital_literacy",
                "Digital Literacy",
                SkillCategory.PROCEDURAL,
                "Competency in using digital technologies effectively",
                [],
                ["programming", "data_analysis"],
                {"technology_use": 0.8, "digital_citizenship": 0.75},
                2,
                15.0
            )
        ]
        
        # Create milestones for skills
        milestones = [
            LearningMilestone(
                "reading_comp_basic",
                "reading_comprehension",
                "Basic Comprehension",
                "Understands main ideas in simple texts",
                0.6,
                ["reading_assessment", "comprehension_quiz"],
                ["identifies_main_idea", "understands_vocabulary"]
            ),
            LearningMilestone(
                "reading_comp_advanced",
                "reading_comprehension",
                "Advanced Analysis",
                "Analyzes complex texts and infers meaning",
                0.85,
                ["analytical_essay", "inference_tasks"],
                ["analyzes_themes", "makes_inferences", "evaluates_arguments"]
            ),
            LearningMilestone(
                "math_reasoning_basic",
                "mathematical_reasoning",
                "Problem Solving Foundation",
                "Applies mathematical concepts to solve routine problems",
                0.7,
                ["problem_set", "mathematical_explanation"],
                ["applies_formulas", "shows_work", "explains_reasoning"]
            ),
            LearningMilestone(
                "math_reasoning_advanced",
                "mathematical_reasoning",
                "Complex Problem Solving",
                "Solves multi-step, non-routine mathematical problems",
                0.9,
                ["complex_problem_portfolio", "mathematical_proof"],
                ["constructs_proofs", "generalizes_patterns", "creates_models"]
            )
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert skill definitions
        for skill in skill_definitions:
            cursor.execute('''
                INSERT OR IGNORE INTO skill_definitions
                (skill_id, skill_name, category, description, prerequisite_skills,
                 dependent_skills, mastery_criteria, difficulty_level, estimated_learning_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (skill.skill_id, skill.skill_name, skill.category.value,
                  skill.description, json.dumps(skill.prerequisite_skills),
                  json.dumps(skill.dependent_skills), json.dumps(skill.mastery_criteria),
                  skill.difficulty_level, skill.estimated_learning_hours))
            
            self.skill_definitions[skill.skill_id] = skill
        
        # Insert milestones
        for milestone in milestones:
            cursor.execute('''
                INSERT OR IGNORE INTO learning_milestones
                (milestone_id, skill_id, milestone_name, description,
                 mastery_threshold, evidence_required, competency_indicators)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (milestone.milestone_id, milestone.skill_id, milestone.milestone_name,
                  milestone.description, milestone.mastery_threshold,
                  json.dumps(milestone.evidence_required),
                  json.dumps(milestone.competency_indicators)))
        
        conn.commit()
        conn.close()

    async def record_assessment(self, assessment: SkillAssessment) -> SkillProgression:
        """
        Record a skill assessment and update progression tracking
        
        Args:
            assessment: SkillAssessment object
            
        Returns:
            Updated skill progression
        """
        # Save assessment
        await self._save_assessment(assessment)
        
        # Update skill progression
        progression = await self.update_skill_progression(assessment.student_id, assessment.skill_id)
        
        logger.info(f"Recorded assessment for student {assessment.student_id}, skill {assessment.skill_id}")
        return progression

    async def update_skill_progression(self, student_id: str, skill_id: str) -> SkillProgression:
        """
        Update skill progression based on recent assessments
        
        Args:
            student_id: Student identifier
            skill_id: Skill identifier
            
        Returns:
            Updated skill progression
        """
        # Get recent assessments
        assessments = await self._get_recent_assessments(student_id, skill_id)
        
        if not assessments:
            logger.warning(f"No assessments found for student {student_id}, skill {skill_id}")
            return await self._create_initial_progression(student_id, skill_id)
        
        # Calculate current mastery score
        mastery_score = self._calculate_mastery_score(assessments)
        
        # Determine mastery level
        mastery_level = self._determine_mastery_level(mastery_score)
        
        # Calculate progression rate
        progression_rate = self._calculate_progression_rate(assessments)
        
        # Estimate time to mastery
        time_to_mastery = self._estimate_time_to_mastery(mastery_score, progression_rate, skill_id)
        
        # Determine progression status
        progression_status = self._determine_progression_status(progression_rate, mastery_score)
        
        # Check milestones achieved
        milestones = await self._check_milestones_achieved(student_id, skill_id, mastery_score)
        
        # Create or update progression
        progression = SkillProgression(
            student_id=student_id,
            skill_id=skill_id,
            current_mastery_level=mastery_level,
            mastery_score=mastery_score,
            progression_rate=progression_rate,
            time_to_mastery_estimate=time_to_mastery,
            progression_status=progression_status,
            recent_assessments=[a.assessment_id for a in assessments[-10:]],  # Keep last 10
            skill_milestones=milestones
        )
        
        await self._save_progression(progression)
        
        # Generate learning interventions if needed
        if progression_status in [ProgressionStatus.BEHIND, ProgressionStatus.STAGNANT]:
            interventions = await self._generate_interventions(progression)
            progression.learning_interventions = [i.intervention_id for i in interventions]
            await self._save_progression(progression)
        
        return progression

    def _calculate_mastery_score(self, assessments: List[SkillAssessment]) -> float:
        """Calculate overall mastery score from assessments"""
        if not assessments:
            return 0.0
        
        # Weight recent assessments more heavily
        weighted_scores = []
        total_weight = 0
        
        for i, assessment in enumerate(assessments):
            # More recent assessments get higher weight
            weight = (i + 1) / len(assessments)
            
            # Assessment type weights
            type_weights = {
                AssessmentType.SUMMATIVE: 1.0,
                AssessmentType.FORMATIVE: 0.7,
                AssessmentType.DIAGNOSTIC: 0.8,
                AssessmentType.SELF_ASSESSMENT: 0.5,
                AssessmentType.PEER_ASSESSMENT: 0.6
            }
            
            type_weight = type_weights.get(assessment.assessment_type, 0.7)
            final_weight = weight * type_weight
            
            score_ratio = assessment.score / assessment.max_score if assessment.max_score > 0 else 0
            weighted_scores.append(score_ratio * final_weight)
            total_weight += final_weight
        
        return sum(weighted_scores) / total_weight if total_weight > 0 else 0.0

    def _determine_mastery_level(self, mastery_score: float) -> MasteryLevel:
        """Determine mastery level from score"""
        for level in reversed(list(MasteryLevel)):
            if mastery_score >= self.mastery_thresholds[level]:
                return level
        return MasteryLevel.NOT_STARTED

    def _calculate_progression_rate(self, assessments: List[SkillAssessment]) -> float:
        """Calculate rate of progression over time"""
        if len(assessments) < 2:
            return 0.0
        
        # Sort assessments by timestamp
        sorted_assessments = sorted(assessments, key=lambda x: x.timestamp)
        
        # Calculate score improvements over time
        scores = []
        timestamps = []
        
        for assessment in sorted_assessments:
            score_ratio = assessment.score / assessment.max_score if assessment.max_score > 0 else 0
            scores.append(score_ratio)
            timestamps.append(assessment.timestamp.timestamp())
        
        if len(scores) < 2:
            return 0.0
        
        # Simple linear regression to find trend
        try:
            X = np.array(timestamps).reshape(-1, 1)
            y = np.array(scores)
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Return slope (rate of change per second, converted to per day)
            return model.coef_[0] * 86400  # seconds per day
        except:
            # Fallback: simple difference
            time_diff = (timestamps[-1] - timestamps[0]) / 86400  # days
            score_diff = scores[-1] - scores[0]
            
            return score_diff / time_diff if time_diff > 0 else 0.0

    def _estimate_time_to_mastery(self, current_score: float, progression_rate: float, skill_id: str) -> Optional[float]:
        """Estimate days to reach mastery"""
        mastery_threshold = 0.85  # Target mastery score
        
        if current_score >= mastery_threshold:
            return 0.0
        
        if progression_rate <= 0:
            return None  # No progress or regressing
        
        score_gap = mastery_threshold - current_score
        days_to_mastery = score_gap / progression_rate
        
        # Apply skill difficulty modifier
        skill_def = self.skill_definitions.get(skill_id)
        if skill_def:
            difficulty_modifier = skill_def.difficulty_level * 0.2
            days_to_mastery *= (1 + difficulty_modifier)
        
        # Cap at reasonable maximum
        return min(days_to_mastery, 365.0) if days_to_mastery > 0 else None

    def _determine_progression_status(self, progression_rate: float, mastery_score: float) -> ProgressionStatus:
        """Determine progression status"""
        if mastery_score >= 0.85:
            return ProgressionStatus.ON_TRACK
        elif progression_rate < -0.01:  # Significant regression
            return ProgressionStatus.REGRESSING
        elif progression_rate < 0.005:  # Very slow progress
            return ProgressionStatus.STAGNANT
        elif progression_rate < 0.02:  # Slow but steady
            return ProgressionStatus.BEHIND if mastery_score < 0.5 else ProgressionStatus.ON_TRACK
        else:  # Good progress
            return ProgressionStatus.AHEAD if mastery_score > 0.7 else ProgressionStatus.ON_TRACK

    async def _check_milestones_achieved(self, student_id: str, skill_id: str, mastery_score: float) -> Dict[str, datetime]:
        """Check which milestones have been achieved"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT milestone_id, milestone_name, mastery_threshold
            FROM learning_milestones
            WHERE skill_id = ?
        ''', (skill_id,))
        
        milestones = cursor.fetchall()
        conn.close()
        
        achieved_milestones = {}
        
        for milestone_id, milestone_name, threshold in milestones:
            if mastery_score >= threshold:
                # Check if already recorded
                existing_progression = await self.get_skill_progression(student_id, skill_id)
                if existing_progression and milestone_id not in existing_progression.skill_milestones:
                    achieved_milestones[milestone_id] = datetime.now()
                    logger.info(f"Student {student_id} achieved milestone {milestone_name} for skill {skill_id}")
        
        return achieved_milestones

    async def analyze_student_progress(self, student_id: str) -> ProgressionAnalytics:
        """
        Comprehensive analysis of student's skill progression
        
        Args:
            student_id: Student identifier
            
        Returns:
            Detailed progression analytics
        """
        # Get all skill progressions for student
        progressions = await self._get_all_student_progressions(student_id)
        
        if not progressions:
            return ProgressionAnalytics(
                student_id=student_id,
                analysis_date=datetime.now(),
                overall_progression_rate=0.0,
                skills_mastered=0,
                skills_in_progress=0
            )
        
        # Calculate overall metrics
        overall_rate = np.mean([p.progression_rate for p in progressions])
        skills_mastered = sum(1 for p in progressions if p.current_mastery_level in [MasteryLevel.PROFICIENT, MasteryLevel.ADVANCED, MasteryLevel.EXPERT])
        skills_in_progress = len(progressions) - skills_mastered
        
        # Identify at-risk skills
        skills_at_risk = [
            p.skill_id for p in progressions
            if p.progression_status in [ProgressionStatus.BEHIND, ProgressionStatus.STAGNANT, ProgressionStatus.REGRESSING]
        ]
        
        # Identify strengths and growth areas
        strengths = [
            p.skill_id for p in progressions
            if p.progression_status == ProgressionStatus.AHEAD or p.mastery_score >= 0.8
        ]
        
        growth_areas = [
            p.skill_id for p in progressions
            if p.mastery_score < 0.5 and p.progression_rate < 0.01
        ]
        
        # Generate recommendations
        recommended_focus = await self._generate_focus_recommendations(progressions)
        
        # Predict future outcomes
        predicted_outcomes = self._predict_future_outcomes(progressions)
        
        analytics = ProgressionAnalytics(
            student_id=student_id,
            analysis_date=datetime.now(),
            overall_progression_rate=overall_rate,
            skills_mastered=skills_mastered,
            skills_in_progress=skills_in_progress,
            skills_at_risk=skills_at_risk,
            strengths=strengths,
            growth_areas=growth_areas,
            recommended_focus=recommended_focus,
            predicted_outcomes=predicted_outcomes
        )
        
        await self._save_analytics(analytics)
        return analytics

    def _predict_future_outcomes(self, progressions: List[SkillProgression]) -> Dict[str, Any]:
        """Predict future skill development outcomes"""
        predictions = {}
        
        # Predict skills likely to be mastered in next 30 days
        likely_mastery = []
        for progression in progressions:
            if (progression.time_to_mastery_estimate and
                progression.time_to_mastery_estimate <= 30 and
                progression.current_mastery_level != MasteryLevel.EXPERT):
                likely_mastery.append(progression.skill_id)
        
        predictions["skills_mastery_30_days"] = likely_mastery
        
        # Predict overall progress trajectory
        positive_trend_count = sum(1 for p in progressions if p.progression_rate > 0.01)
        total_skills = len(progressions)
        
        if total_skills > 0:
            progress_momentum = positive_trend_count / total_skills
            predictions["progress_momentum"] = progress_momentum
            
            if progress_momentum >= 0.8:
                predictions["trajectory"] = "accelerating"
            elif progress_momentum >= 0.6:
                predictions["trajectory"] = "steady"
            elif progress_momentum >= 0.4:
                predictions["trajectory"] = "mixed"
            else:
                predictions["trajectory"] = "concerning"
        
        return predictions

    async def _generate_focus_recommendations(self, progressions: List[SkillProgression]) -> List[str]:
        """Generate personalized focus recommendations"""
        recommendations = []
        
        # Priority 1: Address regressing skills
        regressing = [p for p in progressions if p.progression_status == ProgressionStatus.REGRESSING]
        for progression in regressing:
            skill_name = self.skill_definitions.get(progression.skill_id, {}).get('skill_name', progression.skill_id)
            recommendations.append(f"Urgent: Review and reinforce {skill_name} - showing regression")
        
        # Priority 2: Focus on stagnant skills with prerequisites met
        stagnant = [p for p in progressions if p.progression_status == ProgressionStatus.STAGNANT]
        for progression in stagnant:
            if await self._prerequisites_met(progression.student_id, progression.skill_id):
                skill_name = self.skill_definitions.get(progression.skill_id, {}).get('skill_name', progression.skill_id)
                recommendations.append(f"Focus on {skill_name} - ready for breakthrough")
        
        # Priority 3: Build on strengths
        ahead = [p for p in progressions if p.progression_status == ProgressionStatus.AHEAD]
        for progression in ahead[:2]:  # Top 2 strengths
            dependent_skills = self.skill_definitions.get(progression.skill_id, SkillDefinition("", "", SkillCategory.COGNITIVE, "")).dependent_skills
            if dependent_skills:
                recommendations.append(f"Leverage strength in {progression.skill_id} to advance to {dependent_skills[0]}")
        
        return recommendations[:5]  # Top 5 recommendations

    async def _prerequisites_met(self, student_id: str, skill_id: str) -> bool:
        """Check if prerequisites are met for a skill"""
        skill_def = self.skill_definitions.get(skill_id)
        if not skill_def or not skill_def.prerequisite_skills:
            return True
        
        for prereq_skill in skill_def.prerequisite_skills:
            prereq_progression = await self.get_skill_progression(student_id, prereq_skill)
            if not prereq_progression or prereq_progression.mastery_score < 0.7:
                return False
        
        return True

    async def generate_competency_badge(self, student_id: str, skill_id: str) -> Optional[Dict[str, Any]]:
        """Generate competency badge for mastered skill"""
        progression = await self.get_skill_progression(student_id, skill_id)
        
        if not progression or progression.current_mastery_level not in [MasteryLevel.PROFICIENT, MasteryLevel.ADVANCED, MasteryLevel.EXPERT]:
            return None
        
        skill_def = self.skill_definitions.get(skill_id)
        skill_name = skill_def.skill_name if skill_def else skill_id
        
        badge_id = f"badge_{student_id}_{skill_id}_{int(datetime.now().timestamp())}"
        
        # Collect evidence portfolio
        evidence = await self._collect_skill_evidence(student_id, skill_id)
        
        badge = {
            "badge_id": badge_id,
            "student_id": student_id,
            "skill_id": skill_id,
            "badge_name": f"{skill_name} Competency",
            "earned_date": datetime.now(),
            "mastery_level": progression.current_mastery_level.value,
            "mastery_score": progression.mastery_score,
            "evidence_portfolio": evidence,
            "verifier": "system"
        }
        
        await self._save_competency_badge(badge)
        logger.info(f"Generated competency badge for student {student_id}, skill {skill_id}")
        
        return badge

    async def _collect_skill_evidence(self, student_id: str, skill_id: str) -> List[Dict[str, Any]]:
        """Collect evidence portfolio for skill competency"""
        assessments = await self._get_recent_assessments(student_id, skill_id, limit=20)
        
        evidence = []
        for assessment in assessments:
            if assessment.score / assessment.max_score >= 0.8:  # High-quality evidence
                evidence_item = {
                    "assessment_id": assessment.assessment_id,
                    "type": assessment.assessment_type.value,
                    "score": f"{assessment.score}/{assessment.max_score}",
                    "date": assessment.timestamp.isoformat(),
                    "evidence_files": assessment.evidence
                }
                evidence.append(evidence_item)
        
        return evidence[:10]  # Top 10 pieces of evidence

    async def get_skill_progression(self, student_id: str, skill_id: str) -> Optional[SkillProgression]:
        """Get current skill progression for student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT student_id, skill_id, current_mastery_level, mastery_score,
                   progression_rate, time_to_mastery_estimate, progression_status,
                   recent_assessments, skill_milestones, learning_interventions,
                   last_updated
            FROM skill_progressions
            WHERE student_id = ? AND skill_id = ?
        ''', (student_id, skill_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return SkillProgression(
            student_id=row[0],
            skill_id=row[1],
            current_mastery_level=MasteryLevel(row[2]),
            mastery_score=row[3],
            progression_rate=row[4],
            time_to_mastery_estimate=row[5],
            progression_status=ProgressionStatus(row[6]),
            recent_assessments=json.loads(row[7]) if row[7] else [],
            skill_milestones=json.loads(row[8]) if row[8] else {},
            learning_interventions=json.loads(row[9]) if row[9] else [],
            last_updated=datetime.fromisoformat(row[10])
        )

    async def _create_initial_progression(self, student_id: str, skill_id: str) -> SkillProgression:
        """Create initial progression record for new student-skill combination"""
        progression = SkillProgression(
            student_id=student_id,
            skill_id=skill_id,
            current_mastery_level=MasteryLevel.NOT_STARTED,
            mastery_score=0.0,
            progression_rate=0.0
        )
        
        await self._save_progression(progression)
        return progression

    async def _get_recent_assessments(self, student_id: str, skill_id: str, 
                                    limit: int = 20) -> List[SkillAssessment]:
        """Get recent assessments for a student-skill combination"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT assessment_id, student_id, skill_id, assessment_type, score, max_score,
                   timestamp, assessor, rubric_scores, evidence, feedback, metadata
            FROM skill_assessments
            WHERE student_id = ? AND skill_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (student_id, skill_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        assessments = []
        for row in rows:
            assessment = SkillAssessment(
                assessment_id=row[0],
                student_id=row[1],
                skill_id=row[2],
                assessment_type=AssessmentType(row[3]),
                score=row[4],
                max_score=row[5],
                timestamp=datetime.fromisoformat(row[6]),
                assessor=row[7],
                rubric_scores=json.loads(row[8]) if row[8] else {},
                evidence=json.loads(row[9]) if row[9] else [],
                feedback=row[10],
                metadata=json.loads(row[11]) if row[11] else {}
            )
            assessments.append(assessment)
        
        return assessments

    async def _get_all_student_progressions(self, student_id: str) -> List[SkillProgression]:
        """Get all skill progressions for a student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT student_id, skill_id, current_mastery_level, mastery_score,
                   progression_rate, time_to_mastery_estimate, progression_status,
                   recent_assessments, skill_milestones, learning_interventions,
                   last_updated
            FROM skill_progressions
            WHERE student_id = ?
        ''', (student_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        progressions = []
        for row in rows:
            progression = SkillProgression(
                student_id=row[0],
                skill_id=row[1],
                current_mastery_level=MasteryLevel(row[2]),
                mastery_score=row[3],
                progression_rate=row[4],
                time_to_mastery_estimate=row[5],
                progression_status=ProgressionStatus(row[6]),
                recent_assessments=json.loads(row[7]) if row[7] else [],
                skill_milestones=json.loads(row[8]) if row[8] else {},
                learning_interventions=json.loads(row[9]) if row[9] else [],
                last_updated=datetime.fromisoformat(row[10])
            )
            progressions.append(progression)
        
        return progressions

    async def _generate_interventions(self, progression: SkillProgression) -> List[Dict[str, Any]]:
        """Generate learning interventions for struggling skills"""
        interventions = []
        
        skill_def = self.skill_definitions.get(progression.skill_id)
        skill_name = skill_def.skill_name if skill_def else progression.skill_id
        
        if progression.progression_status == ProgressionStatus.REGRESSING:
            interventions.append({
                "intervention_id": f"remediation_{progression.student_id}_{progression.skill_id}",
                "type": "remediation",
                "description": f"Intensive review and practice for {skill_name}",
                "priority": 1
            })
        
        elif progression.progression_status == ProgressionStatus.STAGNANT:
            interventions.append({
                "intervention_id": f"alternative_{progression.student_id}_{progression.skill_id}",
                "type": "alternative_approach",
                "description": f"Try different learning approaches for {skill_name}",
                "priority": 2
            })
        
        elif progression.progression_status == ProgressionStatus.BEHIND:
            interventions.append({
                "intervention_id": f"support_{progression.student_id}_{progression.skill_id}",
                "type": "additional_support",
                "description": f"Additional practice and support for {skill_name}",
                "priority": 2
            })
        
        return interventions

    async def _save_assessment(self, assessment: SkillAssessment):
        """Save skill assessment to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO skill_assessments
            (assessment_id, student_id, skill_id, assessment_type, score, max_score,
             timestamp, assessor, rubric_scores, evidence, feedback, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (assessment.assessment_id, assessment.student_id, assessment.skill_id,
              assessment.assessment_type.value, assessment.score, assessment.max_score,
              assessment.timestamp, assessment.assessor,
              json.dumps(assessment.rubric_scores), json.dumps(assessment.evidence),
              assessment.feedback, json.dumps(assessment.metadata)))
        
        conn.commit()
        conn.close()

    async def _save_progression(self, progression: SkillProgression):
        """Save skill progression to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO skill_progressions
            (student_id, skill_id, current_mastery_level, mastery_score,
             progression_rate, time_to_mastery_estimate, progression_status,
             recent_assessments, skill_milestones, learning_interventions,
             last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (progression.student_id, progression.skill_id,
              progression.current_mastery_level.value, progression.mastery_score,
              progression.progression_rate, progression.time_to_mastery_estimate,
              progression.progression_status.value, json.dumps(progression.recent_assessments),
              json.dumps(progression.skill_milestones), json.dumps(progression.learning_interventions),
              progression.last_updated))
        
        conn.commit()
        conn.close()

    async def _save_analytics(self, analytics: ProgressionAnalytics):
        """Save progression analytics to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO progression_analytics
            (student_id, analysis_date, overall_progression_rate, skills_mastered,
             skills_in_progress, skills_at_risk, strengths, growth_areas,
             recommended_focus, predicted_outcomes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (analytics.student_id, analytics.analysis_date,
              analytics.overall_progression_rate, analytics.skills_mastered,
              analytics.skills_in_progress, json.dumps(analytics.skills_at_risk),
              json.dumps(analytics.strengths), json.dumps(analytics.growth_areas),
              json.dumps(analytics.recommended_focus), json.dumps(analytics.predicted_outcomes)))
        
        conn.commit()
        conn.close()

    async def _save_competency_badge(self, badge: Dict[str, Any]):
        """Save competency badge to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO competency_badges
            (badge_id, student_id, skill_id, badge_name, earned_date,
             evidence_portfolio, verifier, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (badge["badge_id"], badge["student_id"], badge["skill_id"],
              badge["badge_name"], badge["earned_date"],
              json.dumps(badge["evidence_portfolio"]), badge["verifier"],
              json.dumps({"mastery_level": badge["mastery_level"], 
                         "mastery_score": badge["mastery_score"]})))
        
        conn.commit()
        conn.close()

async def demo_skill_progression_tracking():
    """Demonstrate skill progression tracking system"""
    tracker = SkillProgressionTracker()
    
    print("=== Skill Progression Tracking Demo ===")
    
    # Simulate assessments for a student
    student_id = "student_maya"
    skill_id = "reading_comprehension"
    
    assessments = [
        SkillAssessment("assess_1", student_id, skill_id, AssessmentType.DIAGNOSTIC, 6, 10, 
                       datetime.now() - timedelta(days=30), feedback="Good foundation, needs practice"),
        SkillAssessment("assess_2", student_id, skill_id, AssessmentType.FORMATIVE, 7, 10,
                       datetime.now() - timedelta(days=20), feedback="Improving comprehension"),
        SkillAssessment("assess_3", student_id, skill_id, AssessmentType.SUMMATIVE, 8, 10,
                       datetime.now() - timedelta(days=10), feedback="Strong progress"),
        SkillAssessment("assess_4", student_id, skill_id, AssessmentType.FORMATIVE, 8.5, 10,
                       datetime.now() - timedelta(days=5), feedback="Excellent work"),
        SkillAssessment("assess_5", student_id, skill_id, AssessmentType.SUMMATIVE, 9, 10,
                       datetime.now() - timedelta(days=1), feedback="Mastery demonstrated")
    ]
    
    print(f"Recording {len(assessments)} assessments for {student_id}...")
    
    for assessment in assessments:
        progression = await tracker.record_assessment(assessment)
        print(f"Assessment {assessment.assessment_id}: Score {assessment.score}/{assessment.max_score}")
    
    # Get final progression
    final_progression = await tracker.get_skill_progression(student_id, skill_id)
    print(f"\nFinal Skill Progression for {skill_id}:")
    print(f"Mastery Level: {final_progression.current_mastery_level.value}")
    print(f"Mastery Score: {final_progression.mastery_score:.2f}")
    print(f"Progression Rate: {final_progression.progression_rate:.4f}/day")
    print(f"Status: {final_progression.progression_status.value}")
    
    if final_progression.time_to_mastery_estimate:
        print(f"Estimated days to mastery: {final_progression.time_to_mastery_estimate:.1f}")
    
    # Simulate assessments for other skills
    other_skills = ["mathematical_reasoning", "scientific_inquiry", "critical_thinking"]
    for skill in other_skills:
        for i in range(3):
            score = np.random.uniform(5, 9)
            assessment = SkillAssessment(
                f"assess_{skill}_{i}", student_id, skill, AssessmentType.FORMATIVE,
                score, 10, datetime.now() - timedelta(days=15-i*5)
            )
            await tracker.record_assessment(assessment)
    
    # Generate comprehensive analytics
    analytics = await tracker.analyze_student_progress(student_id)
    
    print(f"\nComprehensive Progress Analytics:")
    print(f"Overall Progression Rate: {analytics.overall_progression_rate:.4f}/day")
    print(f"Skills Mastered: {analytics.skills_mastered}")
    print(f"Skills in Progress: {analytics.skills_in_progress}")
    
    if analytics.strengths:
        print(f"Strengths: {', '.join(analytics.strengths)}")
    
    if analytics.skills_at_risk:
        print(f"Skills at Risk: {', '.join(analytics.skills_at_risk)}")
    
    if analytics.recommended_focus:
        print(f"Recommendations:")
        for rec in analytics.recommended_focus:
            print(f"  • {rec}")
    
    # Check for competency badges
    if final_progression.current_mastery_level in [MasteryLevel.PROFICIENT, MasteryLevel.ADVANCED, MasteryLevel.EXPERT]:
        badge = await tracker.generate_competency_badge(student_id, skill_id)
        if badge:
            print(f"\n🏆 Competency Badge Earned: {badge['badge_name']}")
            print(f"   Mastery Level: {badge['mastery_level']}")
            print(f"   Evidence Items: {len(badge['evidence_portfolio'])}")

if __name__ == "__main__":
    asyncio.run(demo_skill_progression_tracking())