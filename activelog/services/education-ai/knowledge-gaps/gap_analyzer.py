"""
Knowledge Gap Identification System

Advanced AI system for identifying, analyzing, and prioritizing student knowledge gaps
through prerequisite mapping, assessment integration, and targeted intervention
recommendations based on educational research and learning analytics.
"""

import asyncio
import sqlite3
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import networkx as nx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GapSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class InterventionType(Enum):
    PREREQUISITE_REVIEW = "prerequisite_review"
    SCAFFOLDED_PRACTICE = "scaffolded_practice"
    PEER_TUTORING = "peer_tutoring"
    REMEDIATION = "remediation"
    CONCEPTUAL_REINFORCEMENT = "conceptual_reinforcement"

@dataclass
class KnowledgeGap:
    gap_id: str
    student_id: str
    skill_id: str
    skill_name: str
    gap_severity: GapSeverity
    confidence: float
    prerequisite_gaps: List[str] = field(default_factory=list)
    affected_skills: List[str] = field(default_factory=list)
    detection_method: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    identified_date: datetime = field(default_factory=datetime.now)
    last_assessed: Optional[datetime] = None

@dataclass
class PrerequisiteMapping:
    skill_id: str
    skill_name: str
    prerequisites: List[str] = field(default_factory=list)
    dependent_skills: List[str] = field(default_factory=list)
    difficulty_level: int = 1
    cognitive_load: float = 1.0
    mastery_threshold: float = 0.75

@dataclass
class AssessmentResult:
    assessment_id: str
    student_id: str
    skill_id: str
    score: float
    max_score: float
    completion_time: int
    question_breakdown: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class InterventionRecommendation:
    gap_id: str
    intervention_type: InterventionType
    priority: int
    estimated_duration: int
    resources: List[str] = field(default_factory=list)
    success_probability: float = 0.0
    reasoning: str = ""

class KnowledgeGapAnalyzer:
    def __init__(self, db_path: str = "education_ai.db"):
        self.db_path = db_path
        self.ml_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.prerequisite_graph = nx.DiGraph()
        self.is_trained = False
        self.init_database()
        self._load_prerequisite_mappings()
        
    def init_database(self):
        """Initialize database tables for knowledge gap analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                gap_id TEXT PRIMARY KEY,
                student_id TEXT,
                skill_id TEXT,
                skill_name TEXT,
                gap_severity TEXT,
                confidence REAL,
                prerequisite_gaps TEXT,
                affected_skills TEXT,
                detection_method TEXT,
                evidence TEXT,
                identified_date TIMESTAMP,
                last_assessed TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prerequisite_mappings (
                skill_id TEXT PRIMARY KEY,
                skill_name TEXT,
                prerequisites TEXT,
                dependent_skills TEXT,
                difficulty_level INTEGER,
                cognitive_load REAL,
                mastery_threshold REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assessment_results (
                assessment_id TEXT,
                student_id TEXT,
                skill_id TEXT,
                score REAL,
                max_score REAL,
                completion_time INTEGER,
                question_breakdown TEXT,
                timestamp TIMESTAMP,
                PRIMARY KEY (assessment_id, student_id, skill_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intervention_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gap_id TEXT,
                intervention_type TEXT,
                priority INTEGER,
                estimated_duration INTEGER,
                resources TEXT,
                success_probability REAL,
                reasoning TEXT,
                created_date TIMESTAMP,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (gap_id) REFERENCES knowledge_gaps (gap_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Knowledge gap analysis database initialized")

    def _load_prerequisite_mappings(self):
        """Load and create default prerequisite mappings"""
        default_mappings = [
            PrerequisiteMapping("basic_arithmetic", "Basic Arithmetic", [], ["fractions", "decimals"], 1, 0.5, 0.80),
            PrerequisiteMapping("fractions", "Fractions", ["basic_arithmetic"], ["ratios", "percentages", "algebra_basics"], 2, 1.0, 0.75),
            PrerequisiteMapping("decimals", "Decimals", ["basic_arithmetic"], ["percentages", "scientific_notation"], 2, 0.8, 0.75),
            PrerequisiteMapping("percentages", "Percentages", ["fractions", "decimals"], ["statistics", "probability"], 3, 1.2, 0.75),
            PrerequisiteMapping("algebra_basics", "Basic Algebra", ["fractions"], ["linear_equations", "quadratic_equations"], 4, 1.5, 0.70),
            PrerequisiteMapping("linear_equations", "Linear Equations", ["algebra_basics"], ["systems_equations", "graphing"], 5, 1.8, 0.70),
            PrerequisiteMapping("quadratic_equations", "Quadratic Equations", ["algebra_basics", "linear_equations"], ["polynomials"], 6, 2.0, 0.65),
            PrerequisiteMapping("geometry_basics", "Basic Geometry", [], ["area_perimeter", "volume"], 3, 1.0, 0.75),
            PrerequisiteMapping("area_perimeter", "Area and Perimeter", ["geometry_basics"], ["trigonometry"], 4, 1.3, 0.70),
            PrerequisiteMapping("trigonometry", "Trigonometry", ["area_perimeter", "algebra_basics"], ["calculus"], 7, 2.2, 0.65),
            PrerequisiteMapping("statistics", "Statistics", ["percentages"], ["probability", "data_analysis"], 5, 1.5, 0.70),
            PrerequisiteMapping("probability", "Probability", ["percentages", "statistics"], ["advanced_statistics"], 6, 1.8, 0.65),
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for mapping in default_mappings:
            cursor.execute('''
                INSERT OR IGNORE INTO prerequisite_mappings
                (skill_id, skill_name, prerequisites, dependent_skills, 
                 difficulty_level, cognitive_load, mastery_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (mapping.skill_id, mapping.skill_name,
                  json.dumps(mapping.prerequisites), json.dumps(mapping.dependent_skills),
                  mapping.difficulty_level, mapping.cognitive_load, mapping.mastery_threshold))
        
        conn.commit()
        conn.close()
        
        self._build_prerequisite_graph()

    def _build_prerequisite_graph(self):
        """Build prerequisite dependency graph"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT skill_id, prerequisites FROM prerequisite_mappings')
        mappings = cursor.fetchall()
        conn.close()
        
        self.prerequisite_graph.clear()
        
        for skill_id, prerequisites_json in mappings:
            prerequisites = json.loads(prerequisites_json) if prerequisites_json else []
            self.prerequisite_graph.add_node(skill_id)
            
            for prereq in prerequisites:
                self.prerequisite_graph.add_edge(prereq, skill_id)
        
        logger.info(f"Built prerequisite graph with {self.prerequisite_graph.number_of_nodes()} skills")

    async def record_assessment(self, result: AssessmentResult):
        """Record assessment result for gap analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO assessment_results
            (assessment_id, student_id, skill_id, score, max_score, 
             completion_time, question_breakdown, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (result.assessment_id, result.student_id, result.skill_id,
              result.score, result.max_score, result.completion_time,
              json.dumps(result.question_breakdown), result.timestamp))
        
        conn.commit()
        conn.close()
        
        # Trigger gap analysis after assessment
        await self.analyze_student_gaps(result.student_id)

    async def analyze_student_gaps(self, student_id: str) -> List[KnowledgeGap]:
        """
        Comprehensive analysis of student knowledge gaps
        
        Args:
            student_id: Student identifier
            
        Returns:
            List of identified knowledge gaps
        """
        logger.info(f"Analyzing knowledge gaps for student {student_id}")
        
        gaps = []
        
        # Get all assessment results for the student
        assessments = await self._get_student_assessments(student_id)
        
        if not assessments:
            logger.warning(f"No assessments found for student {student_id}")
            return gaps
        
        # Analyze each skill
        skill_performance = {}
        for assessment in assessments:
            skill_id = assessment.skill_id
            mastery_ratio = assessment.score / assessment.max_score
            
            if skill_id not in skill_performance:
                skill_performance[skill_id] = []
            skill_performance[skill_id].append(mastery_ratio)
        
        # Calculate average performance per skill
        skill_averages = {
            skill: np.mean(scores) for skill, scores in skill_performance.items()
        }
        
        # Get mastery thresholds
        mastery_thresholds = await self._get_mastery_thresholds()
        
        # Identify gaps
        for skill_id, avg_score in skill_averages.items():
            threshold = mastery_thresholds.get(skill_id, 0.75)
            
            if avg_score < threshold:
                gap_severity = self._determine_severity(avg_score, threshold)
                confidence = min(1.0, (threshold - avg_score) * 2)
                
                # Find prerequisite gaps
                prereq_gaps = await self._find_prerequisite_gaps(student_id, skill_id, skill_averages, mastery_thresholds)
                
                # Find affected skills
                affected_skills = self._find_affected_skills(skill_id)
                
                gap = KnowledgeGap(
                    gap_id=f"{student_id}_{skill_id}_{int(datetime.now().timestamp())}",
                    student_id=student_id,
                    skill_id=skill_id,
                    skill_name=await self._get_skill_name(skill_id),
                    gap_severity=gap_severity,
                    confidence=confidence,
                    prerequisite_gaps=prereq_gaps,
                    affected_skills=affected_skills,
                    detection_method="assessment_analysis",
                    evidence={
                        "average_score": avg_score,
                        "mastery_threshold": threshold,
                        "assessment_count": len(skill_performance[skill_id]),
                        "recent_scores": skill_performance[skill_id][-3:]
                    }
                )
                
                gaps.append(gap)
                await self._save_gap(gap)
        
        # Prioritize gaps
        gaps = self._prioritize_gaps(gaps)
        
        # Generate intervention recommendations
        for gap in gaps:
            recommendations = await self._generate_interventions(gap)
            for rec in recommendations:
                await self._save_intervention(rec)
        
        logger.info(f"Identified {len(gaps)} knowledge gaps for student {student_id}")
        return gaps

    def _determine_severity(self, score: float, threshold: float) -> GapSeverity:
        """Determine gap severity based on performance"""
        gap_size = threshold - score
        
        if gap_size >= 0.5:
            return GapSeverity.CRITICAL
        elif gap_size >= 0.3:
            return GapSeverity.HIGH
        elif gap_size >= 0.15:
            return GapSeverity.MEDIUM
        else:
            return GapSeverity.LOW

    async def _find_prerequisite_gaps(self, student_id: str, skill_id: str, 
                                    skill_averages: Dict[str, float], 
                                    mastery_thresholds: Dict[str, float]) -> List[str]:
        """Find prerequisite skills that are also gaps"""
        prereq_gaps = []
        
        try:
            predecessors = list(self.prerequisite_graph.predecessors(skill_id))
            for prereq_skill in predecessors:
                if prereq_skill in skill_averages:
                    threshold = mastery_thresholds.get(prereq_skill, 0.75)
                    if skill_averages[prereq_skill] < threshold:
                        prereq_gaps.append(prereq_skill)
        except nx.NetworkXError:
            logger.warning(f"Skill {skill_id} not found in prerequisite graph")
        
        return prereq_gaps

    def _find_affected_skills(self, skill_id: str) -> List[str]:
        """Find skills that depend on this skill"""
        try:
            return list(self.prerequisite_graph.successors(skill_id))
        except nx.NetworkXError:
            return []

    async def _generate_interventions(self, gap: KnowledgeGap) -> List[InterventionRecommendation]:
        """Generate intervention recommendations for a knowledge gap"""
        recommendations = []
        
        # Prioritize interventions based on gap characteristics
        if gap.prerequisite_gaps:
            # Focus on prerequisite review first
            rec = InterventionRecommendation(
                gap_id=gap.gap_id,
                intervention_type=InterventionType.PREREQUISITE_REVIEW,
                priority=1,
                estimated_duration=len(gap.prerequisite_gaps) * 30,
                resources=[f"prerequisite_{prereq}" for prereq in gap.prerequisite_gaps],
                success_probability=0.85,
                reasoning="Prerequisites not mastered - fundamental review needed"
            )
            recommendations.append(rec)
        
        # Scaffolded practice
        practice_duration = 45 if gap.gap_severity in [GapSeverity.CRITICAL, GapSeverity.HIGH] else 30
        rec = InterventionRecommendation(
            gap_id=gap.gap_id,
            intervention_type=InterventionType.SCAFFOLDED_PRACTICE,
            priority=2,
            estimated_duration=practice_duration,
            resources=[f"practice_{gap.skill_id}", f"guided_examples_{gap.skill_id}"],
            success_probability=0.75,
            reasoning="Targeted practice with gradually increasing difficulty"
        )
        recommendations.append(rec)
        
        # Peer tutoring for high-level gaps
        if gap.gap_severity in [GapSeverity.HIGH, GapSeverity.MEDIUM]:
            rec = InterventionRecommendation(
                gap_id=gap.gap_id,
                intervention_type=InterventionType.PEER_TUTORING,
                priority=3,
                estimated_duration=60,
                resources=[f"peer_matching_{gap.skill_id}"],
                success_probability=0.70,
                reasoning="Peer explanation can provide alternative perspectives"
            )
            recommendations.append(rec)
        
        # Conceptual reinforcement
        rec = InterventionRecommendation(
            gap_id=gap.gap_id,
            intervention_type=InterventionType.CONCEPTUAL_REINFORCEMENT,
            priority=4,
            estimated_duration=25,
            resources=[f"concept_map_{gap.skill_id}", f"visual_aids_{gap.skill_id}"],
            success_probability=0.65,
            reasoning="Strengthen conceptual understanding through multiple representations"
        )
        recommendations.append(rec)
        
        return recommendations

    async def get_student_gaps(self, student_id: str, severity_filter: Optional[GapSeverity] = None) -> List[KnowledgeGap]:
        """Get knowledge gaps for a student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT gap_id, student_id, skill_id, skill_name, gap_severity, confidence,
                   prerequisite_gaps, affected_skills, detection_method, evidence,
                   identified_date, last_assessed
            FROM knowledge_gaps
            WHERE student_id = ?
        '''
        params = [student_id]
        
        if severity_filter:
            query += ' AND gap_severity = ?'
            params.append(severity_filter.value)
        
        query += ' ORDER BY gap_severity, confidence DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        gaps = []
        for row in rows:
            gap = KnowledgeGap(
                gap_id=row[0],
                student_id=row[1],
                skill_id=row[2],
                skill_name=row[3],
                gap_severity=GapSeverity(row[4]),
                confidence=row[5],
                prerequisite_gaps=json.loads(row[6]) if row[6] else [],
                affected_skills=json.loads(row[7]) if row[7] else [],
                detection_method=row[8],
                evidence=json.loads(row[9]) if row[9] else {},
                identified_date=datetime.fromisoformat(row[10]),
                last_assessed=datetime.fromisoformat(row[11]) if row[11] else None
            )
            gaps.append(gap)
        
        return gaps

    async def get_intervention_recommendations(self, gap_id: str) -> List[InterventionRecommendation]:
        """Get intervention recommendations for a specific gap"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT gap_id, intervention_type, priority, estimated_duration,
                   resources, success_probability, reasoning
            FROM intervention_recommendations
            WHERE gap_id = ? AND status = 'pending'
            ORDER BY priority
        ''', (gap_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        recommendations = []
        for row in rows:
            rec = InterventionRecommendation(
                gap_id=row[0],
                intervention_type=InterventionType(row[1]),
                priority=row[2],
                estimated_duration=row[3],
                resources=json.loads(row[4]) if row[4] else [],
                success_probability=row[5],
                reasoning=row[6]
            )
            recommendations.append(rec)
        
        return recommendations

    def _prioritize_gaps(self, gaps: List[KnowledgeGap]) -> List[KnowledgeGap]:
        """Prioritize gaps based on severity, impact, and prerequisites"""
        def priority_score(gap: KnowledgeGap) -> float:
            severity_weights = {
                GapSeverity.CRITICAL: 4.0,
                GapSeverity.HIGH: 3.0,
                GapSeverity.MEDIUM: 2.0,
                GapSeverity.LOW: 1.0
            }
            
            base_score = severity_weights[gap.gap_severity] * gap.confidence
            
            # Boost priority for foundational skills (those with many dependents)
            dependent_count = len(gap.affected_skills)
            foundation_boost = min(dependent_count * 0.2, 1.0)
            
            # Reduce priority if prerequisites aren't met
            prereq_penalty = len(gap.prerequisite_gaps) * 0.1
            
            return base_score + foundation_boost - prereq_penalty
        
        return sorted(gaps, key=priority_score, reverse=True)

    async def _get_student_assessments(self, student_id: str) -> List[AssessmentResult]:
        """Get all assessments for a student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT assessment_id, student_id, skill_id, score, max_score,
                   completion_time, question_breakdown, timestamp
            FROM assessment_results
            WHERE student_id = ?
            ORDER BY timestamp DESC
        ''', (student_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        assessments = []
        for row in rows:
            assessment = AssessmentResult(
                assessment_id=row[0],
                student_id=row[1],
                skill_id=row[2],
                score=row[3],
                max_score=row[4],
                completion_time=row[5],
                question_breakdown=json.loads(row[6]) if row[6] else {},
                timestamp=datetime.fromisoformat(row[7])
            )
            assessments.append(assessment)
        
        return assessments

    async def _get_mastery_thresholds(self) -> Dict[str, float]:
        """Get mastery thresholds for all skills"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT skill_id, mastery_threshold FROM prerequisite_mappings')
        rows = cursor.fetchall()
        conn.close()
        
        return {row[0]: row[1] for row in rows}

    async def _get_skill_name(self, skill_id: str) -> str:
        """Get human-readable skill name"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT skill_name FROM prerequisite_mappings WHERE skill_id = ?', (skill_id,))
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else skill_id

    async def _save_gap(self, gap: KnowledgeGap):
        """Save knowledge gap to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO knowledge_gaps
            (gap_id, student_id, skill_id, skill_name, gap_severity, confidence,
             prerequisite_gaps, affected_skills, detection_method, evidence,
             identified_date, last_assessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (gap.gap_id, gap.student_id, gap.skill_id, gap.skill_name,
              gap.gap_severity.value, gap.confidence,
              json.dumps(gap.prerequisite_gaps), json.dumps(gap.affected_skills),
              gap.detection_method, json.dumps(gap.evidence),
              gap.identified_date, gap.last_assessed))
        
        conn.commit()
        conn.close()

    async def _save_intervention(self, intervention: InterventionRecommendation):
        """Save intervention recommendation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO intervention_recommendations
            (gap_id, intervention_type, priority, estimated_duration,
             resources, success_probability, reasoning, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (intervention.gap_id, intervention.intervention_type.value,
              intervention.priority, intervention.estimated_duration,
              json.dumps(intervention.resources), intervention.success_probability,
              intervention.reasoning, datetime.now()))
        
        conn.commit()
        conn.close()

async def demo_knowledge_gap_analysis():
    """Demonstrate knowledge gap analysis"""
    analyzer = KnowledgeGapAnalyzer()
    
    print("=== Knowledge Gap Analysis Demo ===")
    
    # Simulate assessment results for a struggling student
    assessments = [
        AssessmentResult("math_test_1", "student_alex", "basic_arithmetic", 85, 100, 1200),
        AssessmentResult("math_test_2", "student_alex", "fractions", 45, 100, 1800),
        AssessmentResult("math_test_3", "student_alex", "decimals", 60, 100, 1500),
        AssessmentResult("math_test_4", "student_alex", "percentages", 30, 100, 2100),
        AssessmentResult("math_test_5", "student_alex", "algebra_basics", 25, 100, 2400),
        AssessmentResult("math_quiz_1", "student_alex", "fractions", 50, 100, 900),
        AssessmentResult("math_quiz_2", "student_alex", "decimals", 65, 100, 800),
    ]
    
    for assessment in assessments:
        await analyzer.record_assessment(assessment)
    
    # Analyze gaps
    gaps = await analyzer.analyze_student_gaps("student_alex")
    
    print(f"\nIdentified {len(gaps)} knowledge gaps for Alex:")
    for i, gap in enumerate(gaps, 1):
        print(f"\n{i}. {gap.skill_name} ({gap.skill_id})")
        print(f"   Severity: {gap.gap_severity.value.upper()} (confidence: {gap.confidence:.2f})")
        print(f"   Average Score: {gap.evidence.get('average_score', 0):.2f}")
        print(f"   Mastery Threshold: {gap.evidence.get('mastery_threshold', 0.75):.2f}")
        
        if gap.prerequisite_gaps:
            print(f"   Prerequisite Gaps: {', '.join(gap.prerequisite_gaps)}")
        
        if gap.affected_skills:
            print(f"   Affected Skills: {', '.join(gap.affected_skills)}")
        
        # Get intervention recommendations
        interventions = await analyzer.get_intervention_recommendations(gap.gap_id)
        if interventions:
            print(f"   Recommended Interventions:")
            for j, intervention in enumerate(interventions, 1):
                print(f"     {j}. {intervention.intervention_type.value.replace('_', ' ').title()}")
                print(f"        Duration: {intervention.estimated_duration} min")
                print(f"        Success Rate: {intervention.success_probability:.0%}")
                print(f"        Reasoning: {intervention.reasoning}")

if __name__ == "__main__":
    asyncio.run(demo_knowledge_gap_analysis())