"""
Collaborative Study Groups System

AI-powered system for creating optimal study groups, facilitating peer learning,
managing group dynamics, and tracking collaborative learning outcomes through
intelligent matching and group management algorithms.
"""

import asyncio
import sqlite3
import json
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GroupType(Enum):
    STUDY = "study"
    PROJECT = "project"
    DISCUSSION = "discussion"
    PEER_TUTORING = "peer_tutoring"

class GroupStatus(Enum):
    FORMING = "forming"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    DISBANDED = "disbanded"

class ParticipationLevel(Enum):
    LEADER = "leader"
    ACTIVE = "active"
    MODERATE = "moderate"
    OBSERVER = "observer"

class LearningStyle(Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    READING_WRITING = "reading_writing"

@dataclass
class StudentProfile:
    student_id: str
    name: str
    grade_level: int
    learning_style: LearningStyle
    skill_levels: Dict[str, float] = field(default_factory=dict)
    availability: Dict[str, List[str]] = field(default_factory=dict)
    personality_traits: Dict[str, float] = field(default_factory=dict)
    collaboration_history: Dict[str, Any] = field(default_factory=dict)
    preferred_group_size: int = 4
    leadership_score: float = 0.5

@dataclass
class StudyGroup:
    group_id: str
    group_name: str
    group_type: GroupType
    subject: str
    topic: str
    max_size: int = 6
    current_members: List[str] = field(default_factory=list)
    leader_id: Optional[str] = None
    schedule: Dict[str, Any] = field(default_factory=dict)
    learning_objectives: List[str] = field(default_factory=list)
    group_status: GroupStatus = GroupStatus.FORMING
    creation_date: datetime = field(default_factory=datetime.now)
    completion_date: Optional[datetime] = None
    group_dynamics: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)

@dataclass
class GroupActivity:
    activity_id: str
    group_id: str
    activity_type: str
    topic: str
    scheduled_time: datetime
    duration: int
    participants: List[str] = field(default_factory=list)
    materials_needed: List[str] = field(default_factory=list)
    learning_outcomes: List[str] = field(default_factory=list)
    completion_status: str = "scheduled"

@dataclass
class GroupInteraction:
    interaction_id: str
    group_id: str
    participant_id: str
    interaction_type: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    engagement_score: float = 0.0
    contribution_quality: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GroupRecommendation:
    student_id: str
    recommended_groups: List[str]
    reasoning: str
    compatibility_score: float
    expected_benefit: str

class CollaborativeGroupManager:
    def __init__(self, db_path: str = "education_ai.db"):
        self.db_path = db_path
        self.clustering_model = KMeans(n_clusters=5, random_state=42)
        self.scaler = StandardScaler()
        self.init_database()
        
    def init_database(self):
        """Initialize database tables for collaborative groups"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_profiles (
                student_id TEXT PRIMARY KEY,
                name TEXT,
                grade_level INTEGER,
                learning_style TEXT,
                skill_levels TEXT,
                availability TEXT,
                personality_traits TEXT,
                collaboration_history TEXT,
                preferred_group_size INTEGER,
                leadership_score REAL,
                last_updated TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_groups (
                group_id TEXT PRIMARY KEY,
                group_name TEXT,
                group_type TEXT,
                subject TEXT,
                topic TEXT,
                max_size INTEGER,
                current_members TEXT,
                leader_id TEXT,
                schedule TEXT,
                learning_objectives TEXT,
                group_status TEXT,
                creation_date TIMESTAMP,
                completion_date TIMESTAMP,
                group_dynamics TEXT,
                performance_metrics TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_activities (
                activity_id TEXT PRIMARY KEY,
                group_id TEXT,
                activity_type TEXT,
                topic TEXT,
                scheduled_time TIMESTAMP,
                duration INTEGER,
                participants TEXT,
                materials_needed TEXT,
                learning_outcomes TEXT,
                completion_status TEXT,
                FOREIGN KEY (group_id) REFERENCES study_groups (group_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_interactions (
                interaction_id TEXT PRIMARY KEY,
                group_id TEXT,
                participant_id TEXT,
                interaction_type TEXT,
                content TEXT,
                timestamp TIMESTAMP,
                engagement_score REAL,
                contribution_quality REAL,
                metadata TEXT,
                FOREIGN KEY (group_id) REFERENCES study_groups (group_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_memberships (
                membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                group_id TEXT,
                join_date TIMESTAMP,
                leave_date TIMESTAMP,
                participation_level TEXT,
                contribution_score REAL,
                satisfaction_rating REAL,
                FOREIGN KEY (student_id) REFERENCES student_profiles (student_id),
                FOREIGN KEY (group_id) REFERENCES study_groups (group_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Collaborative groups database initialized")

    async def create_student_profile(self, student_id: str, name: str, grade_level: int,
                                   learning_style: LearningStyle,
                                   skill_levels: Dict[str, float] = None,
                                   personality_traits: Dict[str, float] = None) -> StudentProfile:
        """
        Create or update student profile for group matching
        
        Args:
            student_id: Unique student identifier
            name: Student name
            grade_level: Academic grade level
            learning_style: Primary learning style
            skill_levels: Dictionary of skill assessments
            personality_traits: Personality trait scores
            
        Returns:
            Created student profile
        """
        profile = StudentProfile(
            student_id=student_id,
            name=name,
            grade_level=grade_level,
            learning_style=learning_style,
            skill_levels=skill_levels or {},
            personality_traits=personality_traits or {
                "extroversion": random.uniform(0.2, 0.8),
                "conscientiousness": random.uniform(0.3, 0.9),
                "openness": random.uniform(0.4, 0.9),
                "agreeableness": random.uniform(0.3, 0.8),
                "leadership": random.uniform(0.2, 0.8)
            }
        )
        
        # Calculate leadership score
        profile.leadership_score = (
            profile.personality_traits.get("leadership", 0.5) * 0.4 +
            profile.personality_traits.get("extroversion", 0.5) * 0.3 +
            profile.personality_traits.get("conscientiousness", 0.5) * 0.3
        )
        
        await self._save_student_profile(profile)
        logger.info(f"Created student profile for {name} ({student_id})")
        return profile

    async def create_study_group(self, group_name: str, group_type: GroupType,
                               subject: str, topic: str, creator_id: str,
                               learning_objectives: List[str] = None,
                               max_size: int = 6) -> StudyGroup:
        """
        Create a new study group
        
        Args:
            group_name: Name of the group
            group_type: Type of group activity
            subject: Academic subject
            topic: Specific topic focus
            creator_id: Student who created the group
            learning_objectives: Learning goals
            max_size: Maximum group size
            
        Returns:
            Created study group
        """
        group_id = f"group_{subject}_{topic}_{int(datetime.now().timestamp())}"
        
        group = StudyGroup(
            group_id=group_id,
            group_name=group_name,
            group_type=group_type,
            subject=subject,
            topic=topic,
            max_size=max_size,
            current_members=[creator_id],
            leader_id=creator_id,
            learning_objectives=learning_objectives or []
        )
        
        await self._save_study_group(group)
        
        # Add creator as member
        await self._add_group_membership(creator_id, group_id, ParticipationLevel.LEADER)
        
        logger.info(f"Created study group {group_name} ({group_id}) for {subject}: {topic}")
        return group

    async def find_optimal_groups(self, student_id: str, subject: str,
                                topic: str = None, group_type: GroupType = None) -> List[GroupRecommendation]:
        """
        Find optimal study groups for a student using AI matching
        
        Args:
            student_id: Student seeking group
            subject: Subject area
            topic: Optional specific topic
            group_type: Optional group type preference
            
        Returns:
            List of group recommendations ranked by compatibility
        """
        student_profile = await self.get_student_profile(student_id)
        if not student_profile:
            logger.warning(f"Student profile not found for {student_id}")
            return []
        
        # Get available groups
        available_groups = await self._get_available_groups(subject, topic, group_type)
        
        if not available_groups:
            return []
        
        recommendations = []
        
        for group in available_groups:
            compatibility_score = await self._calculate_group_compatibility(student_profile, group)
            
            if compatibility_score > 0.5:  # Minimum compatibility threshold
                reasoning = await self._generate_recommendation_reasoning(student_profile, group, compatibility_score)
                
                recommendation = GroupRecommendation(
                    student_id=student_id,
                    recommended_groups=[group.group_id],
                    reasoning=reasoning,
                    compatibility_score=compatibility_score,
                    expected_benefit=self._predict_learning_benefit(student_profile, group)
                )
                
                recommendations.append(recommendation)
        
        # Sort by compatibility score
        recommendations.sort(key=lambda x: x.compatibility_score, reverse=True)
        
        logger.info(f"Found {len(recommendations)} group recommendations for student {student_id}")
        return recommendations[:5]  # Return top 5

    async def form_optimal_group(self, students: List[str], subject: str, topic: str,
                               group_type: GroupType = GroupType.STUDY,
                               target_size: int = 4) -> StudyGroup:
        """
        Form an optimal group from a pool of students using clustering
        
        Args:
            students: List of student IDs
            subject: Subject area
            topic: Topic focus
            group_type: Type of group
            target_size: Target group size
            
        Returns:
            Formed study group with optimal member selection
        """
        if len(students) < 2:
            raise ValueError("Need at least 2 students to form a group")
        
        # Get student profiles
        profiles = []
        for student_id in students:
            profile = await self.get_student_profile(student_id)
            if profile:
                profiles.append(profile)
        
        if len(profiles) < 2:
            raise ValueError("Insufficient valid student profiles")
        
        # Select optimal group composition
        optimal_members = await self._select_optimal_members(profiles, subject, target_size)
        
        # Select group leader
        leader_id = self._select_group_leader(optimal_members)
        
        # Create group
        group_name = f"{subject}: {topic} Study Group"
        group = StudyGroup(
            group_id=f"optimal_group_{subject}_{int(datetime.now().timestamp())}",
            group_name=group_name,
            group_type=group_type,
            subject=subject,
            topic=topic,
            max_size=target_size + 2,  # Allow some flexibility
            current_members=[p.student_id for p in optimal_members],
            leader_id=leader_id
        )
        
        await self._save_study_group(group)
        
        # Add all members
        for profile in optimal_members:
            level = ParticipationLevel.LEADER if profile.student_id == leader_id else ParticipationLevel.ACTIVE
            await self._add_group_membership(profile.student_id, group.group_id, level)
        
        logger.info(f"Formed optimal group {group.group_name} with {len(optimal_members)} members")
        return group

    async def join_group(self, student_id: str, group_id: str) -> bool:
        """
        Add student to existing group with compatibility check
        
        Args:
            student_id: Student requesting to join
            group_id: Target group
            
        Returns:
            True if successfully joined, False otherwise
        """
        group = await self.get_study_group(group_id)
        if not group or group.group_status != GroupStatus.FORMING:
            logger.warning(f"Group {group_id} not available for joining")
            return False
        
        if len(group.current_members) >= group.max_size:
            logger.warning(f"Group {group_id} is full")
            return False
        
        if student_id in group.current_members:
            logger.warning(f"Student {student_id} already in group {group_id}")
            return False
        
        # Check compatibility
        student_profile = await self.get_student_profile(student_id)
        if not student_profile:
            logger.warning(f"Student profile not found for {student_id}")
            return False
        
        compatibility = await self._calculate_group_compatibility(student_profile, group)
        if compatibility < 0.4:  # Minimum compatibility for joining
            logger.info(f"Low compatibility ({compatibility:.2f}) for student {student_id} joining group {group_id}")
            return False
        
        # Add to group
        group.current_members.append(student_id)
        await self._save_study_group(group)
        await self._add_group_membership(student_id, group_id, ParticipationLevel.ACTIVE)
        
        logger.info(f"Student {student_id} joined group {group_id}")
        return True

    async def schedule_group_activity(self, group_id: str, activity_type: str,
                                    topic: str, duration: int,
                                    preferred_time: datetime = None) -> GroupActivity:
        """
        Schedule a group activity with optimal timing
        
        Args:
            group_id: Group identifier
            activity_type: Type of activity
            topic: Activity topic
            duration: Duration in minutes
            preferred_time: Preferred scheduling time
            
        Returns:
            Scheduled group activity
        """
        group = await self.get_study_group(group_id)
        if not group:
            raise ValueError(f"Group {group_id} not found")
        
        # Find optimal time based on member availability
        optimal_time = await self._find_optimal_meeting_time(group.current_members, duration, preferred_time)
        
        activity_id = f"activity_{group_id}_{int(datetime.now().timestamp())}"
        
        activity = GroupActivity(
            activity_id=activity_id,
            group_id=group_id,
            activity_type=activity_type,
            topic=topic,
            scheduled_time=optimal_time,
            duration=duration,
            participants=group.current_members.copy(),
            learning_outcomes=self._generate_activity_outcomes(activity_type, topic)
        )
        
        await self._save_group_activity(activity)
        
        logger.info(f"Scheduled {activity_type} activity for group {group_id} at {optimal_time}")
        return activity

    async def track_group_interaction(self, group_id: str, participant_id: str,
                                    interaction_type: str, content: str) -> GroupInteraction:
        """
        Track and analyze group interactions for dynamics monitoring
        
        Args:
            group_id: Group identifier
            participant_id: Participating student
            interaction_type: Type of interaction
            content: Interaction content
            
        Returns:
            Recorded interaction with analysis
        """
        interaction_id = f"interaction_{group_id}_{participant_id}_{int(datetime.now().timestamp())}"
        
        # Analyze interaction quality
        engagement_score = self._analyze_engagement(content, interaction_type)
        contribution_quality = self._analyze_contribution_quality(content, interaction_type)
        
        interaction = GroupInteraction(
            interaction_id=interaction_id,
            group_id=group_id,
            participant_id=participant_id,
            interaction_type=interaction_type,
            content=content,
            engagement_score=engagement_score,
            contribution_quality=contribution_quality,
            metadata={
                "content_length": len(content),
                "question_count": content.count("?"),
                "exclamation_count": content.count("!")
            }
        )
        
        await self._save_group_interaction(interaction)
        
        # Update group dynamics
        await self._update_group_dynamics(group_id)
        
        return interaction

    async def _calculate_group_compatibility(self, student_profile: StudentProfile, group: StudyGroup) -> float:
        """Calculate compatibility score between student and group"""
        score = 0.0
        
        # Get group member profiles
        member_profiles = []
        for member_id in group.current_members:
            profile = await self.get_student_profile(member_id)
            if profile:
                member_profiles.append(profile)
        
        if not member_profiles:
            return 0.5  # Neutral score for empty group
        
        # Learning style compatibility
        learning_style_diversity = len(set(p.learning_style for p in member_profiles))
        if learning_style_diversity <= 2:
            score += 0.2  # Encourage diversity
        
        # Skill level compatibility
        if group.subject in student_profile.skill_levels:
            student_skill = student_profile.skill_levels[group.subject]
            member_skills = [p.skill_levels.get(group.subject, 0.5) for p in member_profiles]
            avg_member_skill = np.mean(member_skills)
            
            # Prefer slight skill level differences for peer learning
            skill_diff = abs(student_skill - avg_member_skill)
            if skill_diff < 0.3:
                score += 0.3 * (0.3 - skill_diff) / 0.3
        
        # Personality compatibility
        student_extroversion = student_profile.personality_traits.get("extroversion", 0.5)
        member_extroversions = [p.personality_traits.get("extroversion", 0.5) for p in member_profiles]
        avg_extroversion = np.mean(member_extroversions)
        
        # Balance of extroversion levels
        extroversion_balance = 1 - abs(student_extroversion - avg_extroversion)
        score += 0.2 * extroversion_balance
        
        # Group size preference
        current_size = len(group.current_members)
        if current_size <= student_profile.preferred_group_size:
            score += 0.2
        
        # Leadership balance
        current_leadership = np.mean([p.leadership_score for p in member_profiles])
        if (student_profile.leadership_score > 0.7 and current_leadership < 0.5) or \
           (student_profile.leadership_score < 0.4 and current_leadership > 0.6):
            score += 0.1
        
        return min(1.0, score)

    async def _select_optimal_members(self, profiles: List[StudentProfile], subject: str, target_size: int) -> List[StudentProfile]:
        """Select optimal group members using clustering and optimization"""
        if len(profiles) <= target_size:
            return profiles
        
        # Create feature matrix for clustering
        features = []
        for profile in profiles:
            feature_vector = [
                profile.grade_level,
                profile.skill_levels.get(subject, 0.5),
                profile.personality_traits.get("extroversion", 0.5),
                profile.personality_traits.get("conscientiousness", 0.5),
                profile.personality_traits.get("openness", 0.5),
                profile.leadership_score,
                len(profile.learning_style.value)  # Simple encoding
            ]
            features.append(feature_vector)
        
        features = np.array(features)
        features_scaled = self.scaler.fit_transform(features)
        
        # Use diversity-based selection
        selected_indices = self._diversity_selection(features_scaled, target_size)
        
        return [profiles[i] for i in selected_indices]

    def _diversity_selection(self, features: np.ndarray, target_size: int) -> List[int]:
        """Select diverse group members using greedy diversity maximization"""
        if len(features) <= target_size:
            return list(range(len(features)))
        
        selected = []
        remaining = list(range(len(features)))
        
        # Start with most central point
        centroid = np.mean(features, axis=0)
        distances_to_center = [np.linalg.norm(features[i] - centroid) for i in remaining]
        first_idx = remaining[np.argmin(distances_to_center)]
        selected.append(first_idx)
        remaining.remove(first_idx)
        
        # Greedily select most diverse remaining points
        while len(selected) < target_size and remaining:
            best_diversity = -1
            best_idx = -1
            
            for candidate in remaining:
                # Calculate minimum distance to already selected points
                min_distance = min(np.linalg.norm(features[candidate] - features[selected_idx]) 
                                 for selected_idx in selected)
                
                if min_distance > best_diversity:
                    best_diversity = min_distance
                    best_idx = candidate
            
            if best_idx != -1:
                selected.append(best_idx)
                remaining.remove(best_idx)
        
        return selected

    def _select_group_leader(self, members: List[StudentProfile]) -> str:
        """Select optimal group leader based on leadership scores and traits"""
        leadership_scores = []
        
        for member in members:
            # Composite leadership score
            composite_score = (
                member.leadership_score * 0.4 +
                member.personality_traits.get("conscientiousness", 0.5) * 0.3 +
                member.personality_traits.get("extroversion", 0.5) * 0.2 +
                len(member.collaboration_history) * 0.1  # Experience factor
            )
            leadership_scores.append((member.student_id, composite_score))
        
        # Select member with highest leadership score
        leader_id, _ = max(leadership_scores, key=lambda x: x[1])
        return leader_id

    async def _find_optimal_meeting_time(self, member_ids: List[str], duration: int,
                                       preferred_time: datetime = None) -> datetime:
        """Find optimal meeting time based on member availability"""
        if preferred_time:
            return preferred_time
        
        # Simple heuristic: schedule for tomorrow at 3 PM
        tomorrow = datetime.now() + timedelta(days=1)
        optimal_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
        
        return optimal_time

    def _analyze_engagement(self, content: str, interaction_type: str) -> float:
        """Analyze engagement level from interaction content"""
        base_score = 0.5
        
        # Length factor
        if len(content) > 100:
            base_score += 0.2
        elif len(content) < 20:
            base_score -= 0.1
        
        # Question asking (shows engagement)
        question_count = content.count("?")
        base_score += min(0.2, question_count * 0.1)
        
        # Enthusiasm indicators
        exclamation_count = content.count("!")
        base_score += min(0.1, exclamation_count * 0.05)
        
        # Interaction type factor
        if interaction_type in ["question", "explanation", "discussion"]:
            base_score += 0.1
        
        return min(1.0, base_score)

    def _analyze_contribution_quality(self, content: str, interaction_type: str) -> float:
        """Analyze quality of contribution"""
        base_score = 0.5
        
        # Educational keywords
        educational_terms = ["because", "therefore", "example", "explain", "understand", "concept", "idea"]
        term_count = sum(1 for term in educational_terms if term in content.lower())
        base_score += min(0.3, term_count * 0.05)
        
        # Constructive phrases
        constructive_phrases = ["i think", "maybe we could", "what if", "another way", "building on"]
        phrase_count = sum(1 for phrase in constructive_phrases if phrase in content.lower())
        base_score += min(0.2, phrase_count * 0.1)
        
        return min(1.0, base_score)

    def _generate_activity_outcomes(self, activity_type: str, topic: str) -> List[str]:
        """Generate learning outcomes for group activities"""
        outcomes = []
        
        if activity_type == "discussion":
            outcomes = [
                f"Develop deeper understanding of {topic}",
                "Practice articulating concepts clearly",
                "Learn from diverse perspectives"
            ]
        elif activity_type == "problem_solving":
            outcomes = [
                f"Apply {topic} concepts to solve problems",
                "Develop collaborative problem-solving skills",
                "Practice explaining solution strategies"
            ]
        elif activity_type == "peer_teaching":
            outcomes = [
                f"Master {topic} through teaching",
                "Develop communication and presentation skills",
                "Reinforce learning through explanation"
            ]
        
        return outcomes

    def _predict_learning_benefit(self, student_profile: StudentProfile, group: StudyGroup) -> str:
        """Predict expected learning benefit from joining group"""
        benefits = []
        
        # Skill level analysis
        if group.subject in student_profile.skill_levels:
            student_skill = student_profile.skill_levels[group.subject]
            if student_skill < 0.6:
                benefits.append("Improve understanding through peer support")
            elif student_skill > 0.8:
                benefits.append("Reinforce knowledge by helping others")
            else:
                benefits.append("Collaborative learning and knowledge sharing")
        
        # Learning style benefits
        if student_profile.learning_style == LearningStyle.VISUAL:
            benefits.append("Visual learners benefit from group diagrams and demonstrations")
        elif student_profile.learning_style == LearningStyle.AUDITORY:
            benefits.append("Auditory learners thrive in discussion-based group activities")
        
        return "; ".join(benefits) if benefits else "General collaborative learning benefits"

    async def _generate_recommendation_reasoning(self, student_profile: StudentProfile, 
                                               group: StudyGroup, compatibility_score: float) -> str:
        """Generate reasoning for group recommendation"""
        reasons = []
        
        if compatibility_score > 0.8:
            reasons.append("Excellent compatibility match")
        elif compatibility_score > 0.6:
            reasons.append("Good compatibility match")
        else:
            reasons.append("Moderate compatibility match")
        
        # Group size factor
        current_size = len(group.current_members)
        if current_size < student_profile.preferred_group_size:
            reasons.append(f"Group size ({current_size}) matches your preference")
        
        # Subject match
        if group.subject in student_profile.skill_levels:
            skill_level = student_profile.skill_levels[group.subject]
            if skill_level > 0.7:
                reasons.append("Your strong skills in this subject would help the group")
            elif skill_level < 0.5:
                reasons.append("This group could help improve your understanding")
        
        return "; ".join(reasons)

    async def _update_group_dynamics(self, group_id: str):
        """Update group dynamics based on recent interactions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get recent interactions
        cutoff_date = datetime.now() - timedelta(days=7)
        cursor.execute('''
            SELECT participant_id, engagement_score, contribution_quality
            FROM group_interactions
            WHERE group_id = ? AND timestamp > ?
        ''', (group_id, cutoff_date))
        
        interactions = cursor.fetchall()
        conn.close()
        
        if not interactions:
            return
        
        # Calculate group dynamics metrics
        participant_engagement = {}
        for participant_id, engagement, quality in interactions:
            if participant_id not in participant_engagement:
                participant_engagement[participant_id] = {"engagement": [], "quality": []}
            participant_engagement[participant_id]["engagement"].append(engagement)
            participant_engagement[participant_id]["quality"].append(quality)
        
        dynamics = {
            "overall_engagement": np.mean([eng for _, eng, _ in interactions]),
            "overall_quality": np.mean([qual for _, _, qual in interactions]),
            "participation_balance": self._calculate_participation_balance(participant_engagement),
            "last_updated": datetime.now().isoformat()
        }
        
        # Update group record
        group = await self.get_study_group(group_id)
        if group:
            group.group_dynamics = dynamics
            await self._save_study_group(group)

    def _calculate_participation_balance(self, participant_data: Dict) -> float:
        """Calculate how balanced participation is across group members"""
        if not participant_data:
            return 1.0
        
        engagement_averages = []
        for participant, data in participant_data.items():
            avg_engagement = np.mean(data["engagement"])
            engagement_averages.append(avg_engagement)
        
        if len(engagement_averages) <= 1:
            return 1.0
        
        # Calculate coefficient of variation (lower = more balanced)
        std_dev = np.std(engagement_averages)
        mean_engagement = np.mean(engagement_averages)
        
        if mean_engagement == 0:
            return 0.0
        
        cv = std_dev / mean_engagement
        balance_score = max(0.0, 1.0 - cv)  # Convert to balance score
        
        return balance_score

    async def get_student_profile(self, student_id: str) -> Optional[StudentProfile]:
        """Get student profile by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT student_id, name, grade_level, learning_style, skill_levels,
                   availability, personality_traits, collaboration_history,
                   preferred_group_size, leadership_score
            FROM student_profiles
            WHERE student_id = ?
        ''', (student_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return StudentProfile(
            student_id=row[0],
            name=row[1],
            grade_level=row[2],
            learning_style=LearningStyle(row[3]),
            skill_levels=json.loads(row[4]) if row[4] else {},
            availability=json.loads(row[5]) if row[5] else {},
            personality_traits=json.loads(row[6]) if row[6] else {},
            collaboration_history=json.loads(row[7]) if row[7] else {},
            preferred_group_size=row[8],
            leadership_score=row[9]
        )

    async def get_study_group(self, group_id: str) -> Optional[StudyGroup]:
        """Get study group by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT group_id, group_name, group_type, subject, topic, max_size,
                   current_members, leader_id, schedule, learning_objectives,
                   group_status, creation_date, completion_date, group_dynamics,
                   performance_metrics
            FROM study_groups
            WHERE group_id = ?
        ''', (group_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return StudyGroup(
            group_id=row[0],
            group_name=row[1],
            group_type=GroupType(row[2]),
            subject=row[3],
            topic=row[4],
            max_size=row[5],
            current_members=json.loads(row[6]) if row[6] else [],
            leader_id=row[7],
            schedule=json.loads(row[8]) if row[8] else {},
            learning_objectives=json.loads(row[9]) if row[9] else [],
            group_status=GroupStatus(row[10]),
            creation_date=datetime.fromisoformat(row[11]),
            completion_date=datetime.fromisoformat(row[12]) if row[12] else None,
            group_dynamics=json.loads(row[13]) if row[13] else {},
            performance_metrics=json.loads(row[14]) if row[14] else {}
        )

    async def _get_available_groups(self, subject: str, topic: str = None, 
                                  group_type: GroupType = None) -> List[StudyGroup]:
        """Get available groups for joining"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT group_id, group_name, group_type, subject, topic, max_size,
                   current_members, leader_id, schedule, learning_objectives,
                   group_status, creation_date, completion_date, group_dynamics,
                   performance_metrics
            FROM study_groups
            WHERE subject = ? AND group_status = 'forming'
        '''
        params = [subject]
        
        if topic:
            query += ' AND topic = ?'
            params.append(topic)
        
        if group_type:
            query += ' AND group_type = ?'
            params.append(group_type.value)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        groups = []
        for row in rows:
            current_members = json.loads(row[6]) if row[6] else []
            if len(current_members) < row[5]:  # Group not full
                group = StudyGroup(
                    group_id=row[0],
                    group_name=row[1],
                    group_type=GroupType(row[2]),
                    subject=row[3],
                    topic=row[4],
                    max_size=row[5],
                    current_members=current_members,
                    leader_id=row[7],
                    schedule=json.loads(row[8]) if row[8] else {},
                    learning_objectives=json.loads(row[9]) if row[9] else [],
                    group_status=GroupStatus(row[10]),
                    creation_date=datetime.fromisoformat(row[11]),
                    completion_date=datetime.fromisoformat(row[12]) if row[12] else None,
                    group_dynamics=json.loads(row[13]) if row[13] else {},
                    performance_metrics=json.loads(row[14]) if row[14] else {}
                )
                groups.append(group)
        
        return groups

    async def _save_student_profile(self, profile: StudentProfile):
        """Save student profile to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO student_profiles
            (student_id, name, grade_level, learning_style, skill_levels,
             availability, personality_traits, collaboration_history,
             preferred_group_size, leadership_score, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (profile.student_id, profile.name, profile.grade_level,
              profile.learning_style.value, json.dumps(profile.skill_levels),
              json.dumps(profile.availability), json.dumps(profile.personality_traits),
              json.dumps(profile.collaboration_history), profile.preferred_group_size,
              profile.leadership_score, datetime.now()))
        
        conn.commit()
        conn.close()

    async def _save_study_group(self, group: StudyGroup):
        """Save study group to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO study_groups
            (group_id, group_name, group_type, subject, topic, max_size,
             current_members, leader_id, schedule, learning_objectives,
             group_status, creation_date, completion_date, group_dynamics,
             performance_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (group.group_id, group.group_name, group.group_type.value,
              group.subject, group.topic, group.max_size,
              json.dumps(group.current_members), group.leader_id,
              json.dumps(group.schedule), json.dumps(group.learning_objectives),
              group.group_status.value, group.creation_date, group.completion_date,
              json.dumps(group.group_dynamics), json.dumps(group.performance_metrics)))
        
        conn.commit()
        conn.close()

    async def _save_group_activity(self, activity: GroupActivity):
        """Save group activity to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO group_activities
            (activity_id, group_id, activity_type, topic, scheduled_time,
             duration, participants, materials_needed, learning_outcomes,
             completion_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (activity.activity_id, activity.group_id, activity.activity_type,
              activity.topic, activity.scheduled_time, activity.duration,
              json.dumps(activity.participants), json.dumps(activity.materials_needed),
              json.dumps(activity.learning_outcomes), activity.completion_status))
        
        conn.commit()
        conn.close()

    async def _save_group_interaction(self, interaction: GroupInteraction):
        """Save group interaction to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO group_interactions
            (interaction_id, group_id, participant_id, interaction_type, content,
             timestamp, engagement_score, contribution_quality, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (interaction.interaction_id, interaction.group_id, interaction.participant_id,
              interaction.interaction_type, interaction.content, interaction.timestamp,
              interaction.engagement_score, interaction.contribution_quality,
              json.dumps(interaction.metadata)))
        
        conn.commit()
        conn.close()

    async def _add_group_membership(self, student_id: str, group_id: str, level: ParticipationLevel):
        """Add group membership record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO group_memberships
            (student_id, group_id, join_date, participation_level, contribution_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (student_id, group_id, datetime.now(), level.value, 0.0))
        
        conn.commit()
        conn.close()

async def demo_collaborative_groups():
    """Demonstrate collaborative study groups system"""
    manager = CollaborativeGroupManager()
    
    print("=== Collaborative Study Groups Demo ===")
    
    # Create student profiles
    students = [
        ("alice", "Alice Johnson", 10, LearningStyle.VISUAL, {"mathematics": 0.8, "science": 0.7}),
        ("bob", "Bob Smith", 10, LearningStyle.AUDITORY, {"mathematics": 0.6, "science": 0.8}),
        ("carol", "Carol Brown", 10, LearningStyle.KINESTHETIC, {"mathematics": 0.7, "science": 0.6}),
        ("david", "David Wilson", 10, LearningStyle.READING_WRITING, {"mathematics": 0.5, "science": 0.9}),
        ("emma", "Emma Davis", 10, LearningStyle.VISUAL, {"mathematics": 0.9, "science": 0.5}),
        ("frank", "Frank Miller", 10, LearningStyle.AUDITORY, {"mathematics": 0.4, "science": 0.7})
    ]
    
    profiles = []
    for student_id, name, grade, learning_style, skills in students:
        profile = await manager.create_student_profile(student_id, name, grade, learning_style, skills)
        profiles.append(profile)
    
    print(f"\nCreated {len(profiles)} student profiles")
    
    # Form optimal group
    student_ids = [p.student_id for p in profiles]
    optimal_group = await manager.form_optimal_group(
        student_ids[:4],  # Use first 4 students
        subject="mathematics",
        topic="algebra",
        group_type=GroupType.STUDY,
        target_size=4
    )
    
    print(f"\nFormed optimal study group: {optimal_group.group_name}")
    print(f"Members: {', '.join(optimal_group.current_members)}")
    print(f"Leader: {optimal_group.leader_id}")
    
    # Create another group for remaining students to find
    second_group = await manager.create_study_group(
        "Calculus Prep Group",
        GroupType.STUDY,
        "mathematics",
        "calculus",
        "emma"
    )
    
    # Find group recommendations for remaining student
    recommendations = await manager.find_optimal_groups("frank", "mathematics")
    
    print(f"\nGroup recommendations for Frank:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. Group compatibility: {rec.compatibility_score:.2f}")
        print(f"   Reasoning: {rec.reasoning}")
        print(f"   Expected benefit: {rec.expected_benefit}")
    
    # Simulate group interactions
    interactions = [
        ("alice", "question", "Can someone explain how to factor this quadratic?"),
        ("bob", "explanation", "Sure! First, we need to find two numbers that multiply to give us c and add to give us b."),
        ("carol", "discussion", "I like to use the visual method with the rectangle. Let me show you."),
        ("david", "question", "What if the coefficient of x² isn't 1? How does that change things?")
    ]
    
    print(f"\nSimulating group interactions for {optimal_group.group_name}:")
    for participant, interaction_type, content in interactions:
        interaction = await manager.track_group_interaction(
            optimal_group.group_id,
            participant,
            interaction_type,
            content
        )
        print(f"{participant}: {content[:50]}... (engagement: {interaction.engagement_score:.2f})")
    
    # Schedule group activity
    activity = await manager.schedule_group_activity(
        optimal_group.group_id,
        "problem_solving",
        "Quadratic Equations Practice",
        60
    )
    
    print(f"\nScheduled activity: {activity.topic}")
    print(f"Time: {activity.scheduled_time}")
    print(f"Expected outcomes: {', '.join(activity.learning_outcomes)}")

if __name__ == "__main__":
    asyncio.run(demo_collaborative_groups())