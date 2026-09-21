"""
Introduction Facilitator

AI-powered system for smart matchmaking and connection facilitation,
analyzing compatibility and creating meaningful introductions between people.
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any, Set
from enum import Enum
import json
import random
from collections import defaultdict

class ConnectionType(Enum):
    PROFESSIONAL = "professional"
    SOCIAL = "social"
    ROMANTIC = "romantic"
    MENTORSHIP = "mentorship"
    COLLABORATION = "collaboration"
    NETWORKING = "networking"
    FRIENDSHIP = "friendship"

class MatchingCriteria(Enum):
    SHARED_INTERESTS = "shared_interests"
    COMPLEMENTARY_SKILLS = "complementary_skills"
    PERSONALITY_COMPATIBILITY = "personality_compatibility"
    LOCATION_PROXIMITY = "location_proximity"
    PROFESSIONAL_SYNERGY = "professional_synergy"
    MUTUAL_CONNECTIONS = "mutual_connections"
    GOAL_ALIGNMENT = "goal_alignment"

class IntroductionStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"
    EXPIRED = "expired"

@dataclass
class PersonProfile:
    id: str = ""
    name: str = ""
    email: str = ""
    bio: str = ""
    interests: List[str] = None
    skills: List[str] = None
    goals: List[str] = None
    personality_traits: Dict[str, float] = None  # Big Five traits
    location: str = ""
    industry: str = ""
    job_title: str = ""
    experience_level: str = ""
    availability: str = "open"  # open, limited, unavailable
    connection_preferences: List[ConnectionType] = None
    introduction_history: List[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    def __post_init__(self):
        if self.interests is None:
            self.interests = []
        if self.skills is None:
            self.skills = []
        if self.goals is None:
            self.goals = []
        if self.personality_traits is None:
            self.personality_traits = {}
        if self.connection_preferences is None:
            self.connection_preferences = []
        if self.introduction_history is None:
            self.introduction_history = []

@dataclass
class MatchScore:
    person1_id: str = ""
    person2_id: str = ""
    overall_score: float = 0.0
    criteria_scores: Dict[str, float] = None
    matching_reasons: List[str] = None
    potential_synergies: List[str] = None
    conversation_starters: List[str] = None
    recommendation_strength: str = "medium"  # low, medium, high, excellent
    calculated_at: datetime = datetime.now()

    def __post_init__(self):
        if self.criteria_scores is None:
            self.criteria_scores = {}
        if self.matching_reasons is None:
            self.matching_reasons = []
        if self.potential_synergies is None:
            self.potential_synergies = []
        if self.conversation_starters is None:
            self.conversation_starters = []

@dataclass
class Introduction:
    id: Optional[int] = None
    facilitator_id: str = ""
    person1_id: str = ""
    person2_id: str = ""
    connection_type: ConnectionType = ConnectionType.NETWORKING
    introduction_message: str = ""
    match_score: float = 0.0
    status: IntroductionStatus = IntroductionStatus.PENDING
    context: str = ""
    meeting_suggestions: List[str] = None
    follow_up_date: Optional[datetime] = None
    outcome_notes: str = ""
    created_at: datetime = datetime.now()
    responded_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def __post_init__(self):
        if self.meeting_suggestions is None:
            self.meeting_suggestions = []

class IntroductionFacilitator:
    """AI-powered introduction and matchmaking system"""
    
    def __init__(self, db_path: str = "introductions.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the introduction facilitation database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS person_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                bio TEXT,
                interests TEXT,
                skills TEXT,
                goals TEXT,
                personality_traits TEXT,
                location TEXT,
                industry TEXT,
                job_title TEXT,
                experience_level TEXT,
                availability TEXT DEFAULT 'open',
                connection_preferences TEXT,
                introduction_history TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_scores (
                id INTEGER PRIMARY KEY,
                person1_id TEXT NOT NULL,
                person2_id TEXT NOT NULL,
                overall_score REAL NOT NULL,
                criteria_scores TEXT,
                matching_reasons TEXT,
                potential_synergies TEXT,
                conversation_starters TEXT,
                recommendation_strength TEXT DEFAULT 'medium',
                calculated_at TEXT,
                FOREIGN KEY (person1_id) REFERENCES person_profiles (id),
                FOREIGN KEY (person2_id) REFERENCES person_profiles (id),
                UNIQUE(person1_id, person2_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS introductions (
                id INTEGER PRIMARY KEY,
                facilitator_id TEXT NOT NULL,
                person1_id TEXT NOT NULL,
                person2_id TEXT NOT NULL,
                connection_type TEXT NOT NULL,
                introduction_message TEXT,
                match_score REAL,
                status TEXT DEFAULT 'pending',
                context TEXT,
                meeting_suggestions TEXT,
                follow_up_date TEXT,
                outcome_notes TEXT,
                created_at TEXT,
                responded_at TEXT,
                expires_at TEXT,
                FOREIGN KEY (person1_id) REFERENCES person_profiles (id),
                FOREIGN KEY (person2_id) REFERENCES person_profiles (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def add_person_profile(self, profile: PersonProfile) -> str:
        """Add or update a person's profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO person_profiles 
            (id, name, email, bio, interests, skills, goals, personality_traits,
             location, industry, job_title, experience_level, availability,
             connection_preferences, introduction_history, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.id, profile.name, profile.email, profile.bio,
            json.dumps(profile.interests), json.dumps(profile.skills), json.dumps(profile.goals),
            json.dumps(profile.personality_traits), profile.location, profile.industry,
            profile.job_title, profile.experience_level, profile.availability,
            json.dumps([cp.value for cp in profile.connection_preferences]),
            json.dumps(profile.introduction_history),
            profile.created_at.isoformat(), profile.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        return profile.id
    
    async def calculate_match_score(self, person1_id: str, person2_id: str) -> MatchScore:
        """Calculate comprehensive match score between two people"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get both profiles
        cursor.execute("SELECT * FROM person_profiles WHERE id IN (?, ?)", (person1_id, person2_id))
        profiles = cursor.fetchall()
        
        if len(profiles) != 2:
            conn.close()
            return MatchScore()
        
        # Convert to dictionaries
        cols = [description[0] for description in cursor.description]
        profile1_dict = dict(zip(cols, profiles[0]))
        profile2_dict = dict(zip(cols, profiles[1]))
        
        # Parse JSON fields
        for profile in [profile1_dict, profile2_dict]:
            profile['interests'] = json.loads(profile['interests']) if profile['interests'] else []
            profile['skills'] = json.loads(profile['skills']) if profile['skills'] else []
            profile['goals'] = json.loads(profile['goals']) if profile['goals'] else []
            profile['personality_traits'] = json.loads(profile['personality_traits']) if profile['personality_traits'] else {}
            profile['connection_preferences'] = json.loads(profile['connection_preferences']) if profile['connection_preferences'] else []
        
        # Calculate individual criteria scores
        criteria_scores = {}
        matching_reasons = []
        potential_synergies = []
        conversation_starters = []
        
        # 1. Shared interests scoring
        shared_interests = set(profile1_dict['interests']) & set(profile2_dict['interests'])
        total_interests = set(profile1_dict['interests']) | set(profile2_dict['interests'])
        
        if total_interests:
            interest_score = len(shared_interests) / len(total_interests)
            criteria_scores[MatchingCriteria.SHARED_INTERESTS.value] = interest_score
            
            if shared_interests:
                matching_reasons.append(f"Share {len(shared_interests)} common interests: {', '.join(list(shared_interests)[:3])}")
                for interest in list(shared_interests)[:2]:
                    conversation_starters.append(f"Ask about their experience with {interest}")
        
        # 2. Complementary skills scoring
        complementary_skills = set(profile1_dict['skills']) & set(profile2_dict['goals'])
        complementary_skills.update(set(profile2_dict['skills']) & set(profile1_dict['goals']))
        
        total_skills = set(profile1_dict['skills']) | set(profile2_dict['skills'])
        if total_skills:
            skill_score = len(complementary_skills) / len(total_skills) if total_skills else 0
            criteria_scores[MatchingCriteria.COMPLEMENTARY_SKILLS.value] = skill_score
            
            if complementary_skills:
                matching_reasons.append(f"Complementary skills: {', '.join(list(complementary_skills)[:2])}")
                potential_synergies.extend([f"Potential collaboration on {skill}" for skill in list(complementary_skills)[:2]])
        
        # 3. Personality compatibility (Big Five traits)
        personality_score = 0.0
        if profile1_dict['personality_traits'] and profile2_dict['personality_traits']:
            traits1 = profile1_dict['personality_traits']
            traits2 = profile2_dict['personality_traits']
            
            trait_differences = []
            for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
                if trait in traits1 and trait in traits2:
                    diff = abs(traits1[trait] - traits2[trait])
                    trait_differences.append(1 - diff)  # Convert difference to similarity
            
            if trait_differences:
                personality_score = sum(trait_differences) / len(trait_differences)
                criteria_scores[MatchingCriteria.PERSONALITY_COMPATIBILITY.value] = personality_score
                
                if personality_score > 0.7:
                    matching_reasons.append("High personality compatibility")
        
        # 4. Professional synergy
        professional_score = 0.0
        if profile1_dict['industry'] and profile2_dict['industry']:
            if profile1_dict['industry'] == profile2_dict['industry']:
                professional_score += 0.5
                matching_reasons.append("Same industry background")
            
            # Different but potentially synergistic industries
            synergistic_pairs = [
                ("technology", "marketing"), ("finance", "consulting"),
                ("healthcare", "technology"), ("education", "technology")
            ]
            
            industries = {profile1_dict['industry'].lower(), profile2_dict['industry'].lower()}
            for pair in synergistic_pairs:
                if set(pair) == industries:
                    professional_score += 0.3
                    potential_synergies.append(f"Cross-industry synergy: {pair[0]} + {pair[1]}")
                    break
        
        criteria_scores[MatchingCriteria.PROFESSIONAL_SYNERGY.value] = professional_score
        
        # 5. Goal alignment
        shared_goals = set(profile1_dict['goals']) & set(profile2_dict['goals'])
        total_goals = set(profile1_dict['goals']) | set(profile2_dict['goals'])
        
        goal_score = 0.0
        if total_goals:
            goal_score = len(shared_goals) / len(total_goals)
            criteria_scores[MatchingCriteria.GOAL_ALIGNMENT.value] = goal_score
            
            if shared_goals:
                matching_reasons.append(f"Aligned goals: {', '.join(list(shared_goals)[:2])}")
                for goal in list(shared_goals)[:2]:
                    conversation_starters.append(f"Discuss strategies for achieving {goal}")
        
        # Calculate overall score (weighted average)
        weights = {
            MatchingCriteria.SHARED_INTERESTS.value: 0.25,
            MatchingCriteria.COMPLEMENTARY_SKILLS.value: 0.20,
            MatchingCriteria.PERSONALITY_COMPATIBILITY.value: 0.20,
            MatchingCriteria.PROFESSIONAL_SYNERGY.value: 0.20,
            MatchingCriteria.GOAL_ALIGNMENT.value: 0.15
        }
        
        overall_score = sum(criteria_scores.get(criterion, 0) * weight 
                           for criterion, weight in weights.items())
        
        # Determine recommendation strength
        if overall_score >= 0.8:
            recommendation_strength = "excellent"
        elif overall_score >= 0.6:
            recommendation_strength = "high"
        elif overall_score >= 0.4:
            recommendation_strength = "medium"
        else:
            recommendation_strength = "low"
        
        # Add general conversation starters if specific ones weren't generated
        if not conversation_starters:
            conversation_starters = [
                "Ask about their professional journey",
                "Discuss current projects or interests",
                "Share experiences in your respective fields"
            ]
        
        match_score = MatchScore(
            person1_id=person1_id,
            person2_id=person2_id,
            overall_score=overall_score,
            criteria_scores=criteria_scores,
            matching_reasons=matching_reasons,
            potential_synergies=potential_synergies,
            conversation_starters=conversation_starters,
            recommendation_strength=recommendation_strength
        )
        
        # Store match score
        cursor.execute("""
            INSERT OR REPLACE INTO match_scores 
            (person1_id, person2_id, overall_score, criteria_scores, matching_reasons,
             potential_synergies, conversation_starters, recommendation_strength, calculated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            person1_id, person2_id, overall_score, json.dumps(criteria_scores),
            json.dumps(matching_reasons), json.dumps(potential_synergies),
            json.dumps(conversation_starters), recommendation_strength,
            match_score.calculated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return match_score
    
    async def find_best_matches(self, person_id: str, connection_type: ConnectionType = ConnectionType.NETWORKING,
                               limit: int = 5) -> List[Dict[str, Any]]:
        """Find best matches for a person based on connection type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all available people (excluding the person and those with unavailable status)
        cursor.execute("""
            SELECT id, name FROM person_profiles 
            WHERE id != ? AND availability != 'unavailable'
        """, (person_id,))
        
        potential_matches = cursor.fetchall()
        match_results = []
        
        for candidate_id, candidate_name in potential_matches:
            # Check if match score already calculated
            cursor.execute("""
                SELECT * FROM match_scores 
                WHERE (person1_id = ? AND person2_id = ?) OR (person1_id = ? AND person2_id = ?)
            """, (person_id, candidate_id, candidate_id, person_id))
            
            existing_score = cursor.fetchone()
            
            if existing_score:
                # Use existing score
                cols = [description[0] for description in cursor.description]
                score_dict = dict(zip(cols, existing_score))
                
                match_results.append({
                    'person_id': candidate_id,
                    'person_name': candidate_name,
                    'match_score': score_dict['overall_score'],
                    'recommendation_strength': score_dict['recommendation_strength'],
                    'matching_reasons': json.loads(score_dict['matching_reasons']) if score_dict['matching_reasons'] else [],
                    'potential_synergies': json.loads(score_dict['potential_synergies']) if score_dict['potential_synergies'] else [],
                    'conversation_starters': json.loads(score_dict['conversation_starters']) if score_dict['conversation_starters'] else []
                })
            else:
                # Calculate new match score
                match_score = await self.calculate_match_score(person_id, candidate_id)
                
                match_results.append({
                    'person_id': candidate_id,
                    'person_name': candidate_name,
                    'match_score': match_score.overall_score,
                    'recommendation_strength': match_score.recommendation_strength,
                    'matching_reasons': match_score.matching_reasons,
                    'potential_synergies': match_score.potential_synergies,
                    'conversation_starters': match_score.conversation_starters
                })
        
        # Sort by match score and return top matches
        match_results.sort(key=lambda x: x['match_score'], reverse=True)
        
        conn.close()
        return match_results[:limit]
    
    async def create_introduction(self, facilitator_id: str, person1_id: str, person2_id: str,
                                connection_type: ConnectionType, context: str = "") -> int:
        """Create a formal introduction between two people"""
        # Get match score
        match_score_obj = await self.calculate_match_score(person1_id, person2_id)
        
        # Get person details for personalized message
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, bio, job_title FROM person_profiles WHERE id IN (?, ?)", 
                      (person1_id, person2_id))
        profiles = cursor.fetchall()
        
        if len(profiles) != 2:
            conn.close()
            raise ValueError("Could not find both profiles")
        
        person1_name, person1_bio, person1_title = profiles[0]
        person2_name, person2_bio, person2_title = profiles[1]
        
        # Generate introduction message
        introduction_message = await self._generate_introduction_message(
            person1_name, person1_title, person2_name, person2_title,
            match_score_obj, connection_type, context
        )
        
        # Generate meeting suggestions
        meeting_suggestions = await self._generate_meeting_suggestions(
            connection_type, match_score_obj.potential_synergies
        )
        
        # Create introduction record
        introduction = Introduction(
            facilitator_id=facilitator_id,
            person1_id=person1_id,
            person2_id=person2_id,
            connection_type=connection_type,
            introduction_message=introduction_message,
            match_score=match_score_obj.overall_score,
            context=context,
            meeting_suggestions=meeting_suggestions,
            expires_at=datetime.now() + timedelta(days=14)  # 2 weeks to respond
        )
        
        cursor.execute("""
            INSERT INTO introductions 
            (facilitator_id, person1_id, person2_id, connection_type, introduction_message,
             match_score, status, context, meeting_suggestions, follow_up_date,
             created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            introduction.facilitator_id, introduction.person1_id, introduction.person2_id,
            introduction.connection_type.value, introduction.introduction_message,
            introduction.match_score, introduction.status.value, introduction.context,
            json.dumps(introduction.meeting_suggestions),
            introduction.follow_up_date.isoformat() if introduction.follow_up_date else None,
            introduction.created_at.isoformat(), introduction.expires_at.isoformat()
        ))
        
        introduction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return introduction_id
    
    async def _generate_introduction_message(self, person1_name: str, person1_title: str,
                                           person2_name: str, person2_title: str,
                                           match_score: MatchScore, connection_type: ConnectionType,
                                           context: str) -> str:
        """Generate personalized introduction message"""
        
        # Base introduction
        message = f"Hi {person1_name} and {person2_name},\n\n"
        message += f"I'd love to introduce you both! "
        
        # Add context if provided
        if context:
            message += f"{context} "
        
        # Add connection type specific intro
        if connection_type == ConnectionType.PROFESSIONAL:
            message += f"{person1_name} ({person1_title}) and {person2_name} ({person2_title}), I think you'd find great value in connecting professionally. "
        elif connection_type == ConnectionType.MENTORSHIP:
            message += f"I believe there's a great mentorship opportunity between you two. "
        elif connection_type == ConnectionType.COLLABORATION:
            message += f"I see exciting collaboration potential between your respective expertise areas. "
        else:
            message += f"I think you'd really enjoy getting to know each other. "
        
        # Add top matching reasons
        if match_score.matching_reasons:
            message += f"\nWhy I think you should connect:\n"
            for reason in match_score.matching_reasons[:3]:
                message += f"• {reason}\n"
        
        # Add potential synergies
        if match_score.potential_synergies:
            message += f"\nPotential collaboration areas:\n"
            for synergy in match_score.potential_synergies[:2]:
                message += f"• {synergy}\n"
        
        # Add conversation starters
        if match_score.conversation_starters:
            message += f"\nSome conversation starters:\n"
            for starter in match_score.conversation_starters[:2]:
                message += f"• {starter}\n"
        
        message += f"\nI'll leave you both to take it from here. Enjoy the conversation!\n\nBest regards"
        
        return message
    
    async def _generate_meeting_suggestions(self, connection_type: ConnectionType, 
                                          potential_synergies: List[str]) -> List[str]:
        """Generate contextual meeting suggestions"""
        suggestions = []
        
        if connection_type == ConnectionType.PROFESSIONAL:
            suggestions = [
                "Schedule a 30-minute coffee chat to explore mutual opportunities",
                "Have a virtual meeting to discuss industry trends and insights",
                "Meet for lunch to share experiences and network"
            ]
        elif connection_type == ConnectionType.MENTORSHIP:
            suggestions = [
                "Start with a 1-hour mentoring session over coffee",
                "Schedule regular monthly check-ins via video call",
                "Meet at a networking event for informal advice sharing"
            ]
        elif connection_type == ConnectionType.COLLABORATION:
            suggestions = [
                "Organize a working session to brainstorm project ideas",
                "Schedule a workshop to explore collaboration opportunities",
                "Meet to discuss potential joint ventures or partnerships"
            ]
        else:
            suggestions = [
                "Grab coffee and get to know each other better",
                "Meet for a casual lunch or dinner",
                "Attend a relevant industry event or meetup together"
            ]
        
        # Add synergy-specific suggestions
        if potential_synergies:
            for synergy in potential_synergies[:2]:
                suggestions.append(f"Discuss collaboration on {synergy.lower()}")
        
        return suggestions
    
    async def update_introduction_status(self, introduction_id: int, status: IntroductionStatus,
                                       outcome_notes: str = ""):
        """Update the status of an introduction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        update_time = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE introductions 
            SET status = ?, outcome_notes = ?, responded_at = ?
            WHERE id = ?
        """, (status.value, outcome_notes, update_time, introduction_id))
        
        conn.commit()
        conn.close()
    
    async def get_introduction_analytics(self, facilitator_id: str = None, 
                                       days_back: int = 30) -> Dict[str, Any]:
        """Get analytics on introduction success rates and patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        # Base query with optional facilitator filter
        base_where = "WHERE created_at >= ?"
        params = [start_date.isoformat()]
        
        if facilitator_id:
            base_where += " AND facilitator_id = ?"
            params.append(facilitator_id)
        
        # Total introductions
        cursor.execute(f"SELECT COUNT(*) FROM introductions {base_where}", params)
        total_introductions = cursor.fetchone()[0]
        
        # Status breakdown
        cursor.execute(f"""
            SELECT status, COUNT(*) as count 
            FROM introductions {base_where}
            GROUP BY status
        """, params)
        
        status_breakdown = {}
        for row in cursor.fetchall():
            status_breakdown[row[0]] = row[1]
        
        # Success rate (accepted + completed)
        successful = status_breakdown.get('accepted', 0) + status_breakdown.get('completed', 0)
        success_rate = (successful / total_introductions * 100) if total_introductions > 0 else 0
        
        # Connection type performance
        cursor.execute(f"""
            SELECT connection_type, 
                   COUNT(*) as total,
                   AVG(match_score) as avg_match_score,
                   SUM(CASE WHEN status IN ('accepted', 'completed') THEN 1 ELSE 0 END) as successful
            FROM introductions {base_where}
            GROUP BY connection_type
        """, params)
        
        connection_type_stats = {}
        for row in cursor.fetchall():
            conn_type, total, avg_score, successful = row
            success_rate_type = (successful / total * 100) if total > 0 else 0
            
            connection_type_stats[conn_type] = {
                'total_introductions': total,
                'average_match_score': round(avg_score, 3) if avg_score else 0,
                'successful_introductions': successful,
                'success_rate_percent': round(success_rate_type, 1)
            }
        
        # Match score correlation with success
        cursor.execute(f"""
            SELECT AVG(match_score) as avg_score
            FROM introductions {base_where}
            AND status IN ('accepted', 'completed')
        """, params)
        
        avg_successful_score = cursor.fetchone()[0] or 0
        
        cursor.execute(f"""
            SELECT AVG(match_score) as avg_score
            FROM introductions {base_where}
            AND status IN ('declined', 'expired')
        """, params)
        
        avg_failed_score = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'analysis_period_days': days_back,
            'total_introductions': total_introductions,
            'status_breakdown': status_breakdown,
            'overall_success_rate_percent': round(success_rate, 1),
            'successful_introductions': successful,
            'connection_type_performance': connection_type_stats,
            'match_score_analysis': {
                'average_successful_match_score': round(avg_successful_score, 3),
                'average_failed_match_score': round(avg_failed_score, 3),
                'score_correlation': round(avg_successful_score - avg_failed_score, 3)
            },
            'recommendations': {
                'optimal_match_threshold': 0.6 if avg_successful_score > 0.6 else 0.5,
                'best_connection_types': sorted(connection_type_stats.items(), 
                                              key=lambda x: x[1]['success_rate_percent'], reverse=True)[:2]
            }
        }

# Demo function
async def demo_introduction_facilitator():
    """Demonstrate the Introduction Facilitator functionality"""
    print("🤝 Introduction Facilitator Demo")
    print("=" * 50)
    
    facilitator = IntroductionFacilitator()
    
    # Create person profiles
    print("\n1. Creating Person Profiles...")
    profiles = [
        PersonProfile(
            id="alex_t",
            name="Alex Thompson",
            email="alex@example.com",
            bio="Senior software engineer passionate about AI and machine learning",
            interests=["machine learning", "hiking", "photography", "startup culture"],
            skills=["python", "tensorflow", "system design", "team leadership"],
            goals=["launch AI startup", "mentor junior developers", "publish research"],
            personality_traits={
                "openness": 0.8, "conscientiousness": 0.7, "extraversion": 0.6,
                "agreeableness": 0.8, "neuroticism": 0.3
            },
            location="San Francisco",
            industry="technology",
            job_title="Senior Software Engineer",
            experience_level="senior",
            connection_preferences=[ConnectionType.PROFESSIONAL, ConnectionType.MENTORSHIP, ConnectionType.COLLABORATION]
        ),
        PersonProfile(
            id="maria_l",
            name="Maria Lopez",
            email="maria@example.com",
            bio="Marketing director with expertise in growth hacking and data analytics",
            interests=["data analytics", "growth hacking", "photography", "travel"],
            skills=["marketing strategy", "data analysis", "A/B testing", "product management"],
            goals=["start consulting business", "learn AI applications in marketing", "build personal brand"],
            personality_traits={
                "openness": 0.7, "conscientiousness": 0.8, "extraversion": 0.9,
                "agreeableness": 0.7, "neuroticism": 0.2
            },
            location="San Francisco",
            industry="marketing",
            job_title="Marketing Director",
            experience_level="senior",
            connection_preferences=[ConnectionType.PROFESSIONAL, ConnectionType.NETWORKING, ConnectionType.COLLABORATION]
        ),
        PersonProfile(
            id="david_k",
            name="David Kim",
            email="david@example.com",
            bio="Junior developer eager to learn and grow in machine learning",
            interests=["machine learning", "gaming", "startup culture", "mentorship"],
            skills=["python", "javascript", "data structures", "eager to learn"],
            goals=["become ML engineer", "find mentor", "contribute to open source"],
            personality_traits={
                "openness": 0.9, "conscientiousness": 0.6, "extraversion": 0.5,
                "agreeableness": 0.8, "neuroticism": 0.4
            },
            location="San Francisco",
            industry="technology",
            job_title="Junior Developer",
            experience_level="junior",
            connection_preferences=[ConnectionType.MENTORSHIP, ConnectionType.PROFESSIONAL, ConnectionType.NETWORKING]
        ),
        PersonProfile(
            id="sarah_w",
            name="Sarah Williams",
            email="sarah@example.com",
            bio="Product manager focused on AI-powered consumer applications",
            interests=["product strategy", "AI applications", "user experience", "hiking"],
            skills=["product management", "user research", "strategy", "cross-functional leadership"],
            goals=["launch AI product", "build team", "scale user growth"],
            personality_traits={
                "openness": 0.8, "conscientiousness": 0.9, "extraversion": 0.7,
                "agreeableness": 0.6, "neuroticism": 0.2
            },
            location="San Francisco",
            industry="technology",
            job_title="Product Manager",
            experience_level="senior",
            connection_preferences=[ConnectionType.PROFESSIONAL, ConnectionType.COLLABORATION, ConnectionType.NETWORKING]
        )
    ]
    
    for profile in profiles:
        await facilitator.add_person_profile(profile)
        print(f"✅ Added profile: {profile.name} ({profile.job_title})")
    
    # Calculate match scores
    print("\n2. Calculating Match Scores...")
    test_matches = [
        ("alex_t", "maria_l"),
        ("alex_t", "david_k"),
        ("maria_l", "sarah_w"),
        ("alex_t", "sarah_w")
    ]
    
    for person1, person2 in test_matches:
        match_score = await facilitator.calculate_match_score(person1, person2)
        print(f"🎯 {person1} ↔ {person2}: {match_score.overall_score:.3f} ({match_score.recommendation_strength})")
        
        if match_score.matching_reasons:
            print(f"   Reasons: {match_score.matching_reasons[0]}")
        if match_score.potential_synergies:
            print(f"   Synergy: {match_score.potential_synergies[0]}")
    
    # Find best matches
    print("\n3. Finding Best Matches for Alex...")
    matches = await facilitator.find_best_matches("alex_t", ConnectionType.PROFESSIONAL, 3)
    
    for i, match in enumerate(matches, 1):
        print(f"🏆 Match {i}: {match['person_name']}")
        print(f"   Score: {match['match_score']:.3f} ({match['recommendation_strength']})")
        if match['matching_reasons']:
            print(f"   Reason: {match['matching_reasons'][0]}")
        if match['conversation_starters']:
            print(f"   Starter: {match['conversation_starters'][0]}")
    
    # Create introductions
    print("\n4. Creating Introductions...")
    introductions = [
        {
            "person1": "alex_t", "person2": "david_k", "type": ConnectionType.MENTORSHIP,
            "context": "Alex has expressed interest in mentoring junior developers, and David is looking for ML guidance."
        },
        {
            "person1": "alex_t", "person2": "maria_l", "type": ConnectionType.COLLABORATION,
            "context": "Both are interested in AI applications and have complementary skills for potential startup collaboration."
        }
    ]
    
    created_intros = []
    for intro_data in introductions:
        intro_id = await facilitator.create_introduction(
            facilitator_id="system",
            person1_id=intro_data["person1"],
            person2_id=intro_data["person2"],
            connection_type=intro_data["type"],
            context=intro_data["context"]
        )
        created_intros.append(intro_id)
        
        person1_name = next(p.name for p in profiles if p.id == intro_data["person1"])
        person2_name = next(p.name for p in profiles if p.id == intro_data["person2"])
        
        print(f"✉️ Created {intro_data['type'].value} introduction: {person1_name} ↔ {person2_name}")
        print(f"   Introduction ID: {intro_id}")
    
    # Simulate some responses
    print("\n5. Simulating Introduction Responses...")
    await facilitator.update_introduction_status(
        created_intros[0], IntroductionStatus.ACCEPTED, 
        "Both parties are excited to connect for mentorship"
    )
    print("✅ Mentorship introduction accepted")
    
    await facilitator.update_introduction_status(
        created_intros[1], IntroductionStatus.COMPLETED,
        "Had a great coffee meeting and are exploring collaboration opportunities"
    )
    print("✅ Collaboration introduction completed successfully")
    
    # Get analytics
    print("\n6. Introduction Analytics...")
    analytics = await facilitator.get_introduction_analytics(days_back=30)
    
    print(f"📊 Total introductions: {analytics['total_introductions']}")
    print(f"📊 Success rate: {analytics['overall_success_rate_percent']}%")
    print(f"📊 Successful matches: {analytics['successful_introductions']}")
    
    print("\nStatus breakdown:")
    for status, count in analytics['status_breakdown'].items():
        print(f"   {status}: {count}")
    
    print("\nConnection type performance:")
    for conn_type, stats in analytics['connection_type_performance'].items():
        print(f"   {conn_type}: {stats['success_rate_percent']}% success ({stats['total_introductions']} total)")
    
    print(f"\nMatch score analysis:")
    score_analysis = analytics['match_score_analysis']
    print(f"   Successful intros avg score: {score_analysis['average_successful_match_score']}")
    print(f"   Failed intros avg score: {score_analysis['average_failed_match_score']}")
    print(f"   Score correlation: {score_analysis['score_correlation']}")
    
    print(f"\nRecommendations:")
    print(f"   Optimal match threshold: {analytics['recommendations']['optimal_match_threshold']}")
    if analytics['recommendations']['best_connection_types']:
        best_types = analytics['recommendations']['best_connection_types']
        print(f"   Best connection types: {', '.join([t[0] for t in best_types])}")
    
    print("\n✅ Introduction Facilitator Demo Complete!")

if __name__ == "__main__":
    asyncio.run(demo_introduction_facilitator())