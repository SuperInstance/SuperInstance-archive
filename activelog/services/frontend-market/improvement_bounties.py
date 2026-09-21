"""
Frontend Improvement Bounties System
Crowdsourced improvement platform with rewards and gamification
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
import logging
import json
import sqlite3
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

class BountyType(str, Enum):
    BUG_FIX = "bug_fix"
    FEATURE_REQUEST = "feature_request"
    PERFORMANCE = "performance"
    SECURITY = "security"
    UI_UX = "ui_ux"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ACCESSIBILITY = "accessibility"

class BountyStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class BountyReward(BaseModel):
    id: str
    bounty_id: str
    
    # Reward details
    amount: Decimal
    currency: str = "USD"
    reward_type: str = "monetary"  # monetary, credits, reputation, nft
    
    # Conditions
    milestone_based: bool = False
    milestones: List[Dict[str, Any]] = []
    
    # Distribution
    winner_percentage: float = 70.0
    runner_up_percentage: float = 20.0
    participation_percentage: float = 10.0
    
    # Metadata
    sponsored_by: Optional[str] = None
    expires_at: Optional[datetime] = None

class Bounty(BaseModel):
    id: str
    frontend_id: str
    created_by: str
    
    # Basic information
    title: str
    description: str
    bounty_type: BountyType
    priority: Priority
    skill_level: SkillLevel
    
    # Requirements
    requirements: List[str] = []
    acceptance_criteria: List[str] = []
    technical_specifications: Dict[str, Any] = {}
    
    # Rewards
    reward: BountyReward
    
    # Timeline
    status: BountyStatus = BountyStatus.DRAFT
    created_at: datetime
    expires_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Participation
    max_participants: int = 5
    current_participants: List[str] = []
    submissions: List[str] = []
    
    # Evaluation
    judging_criteria: Dict[str, float] = {}
    judges: List[str] = []
    
    # Metadata
    tags: List[str] = []
    estimated_hours: int = 8
    difficulty_score: float = 3.0  # 1-5 scale
    
    # Tracking
    views: int = 0
    favorites: int = 0
    questions: List[str] = []

class BountySubmission(BaseModel):
    id: str
    bounty_id: str
    participant_id: str
    
    # Submission details
    title: str
    description: str
    solution_type: str = "code"  # code, design, document, other
    
    # Files and links
    repository_url: Optional[str] = None
    demo_url: Optional[str] = None
    documentation_url: Optional[str] = None
    file_attachments: List[str] = []
    
    # Technical details
    changes_made: List[str] = []
    testing_notes: str = ""
    performance_impact: Dict[str, Any] = {}
    
    # Status
    submitted_at: datetime
    status: str = "submitted"  # submitted, under_review, approved, rejected
    
    # Evaluation
    scores: Dict[str, float] = {}
    feedback: List[Dict[str, Any]] = []
    final_score: Optional[float] = None
    
    # Metadata
    time_spent_hours: int = 0
    collaboration_notes: str = ""

class BountyParticipant(BaseModel):
    id: str
    user_id: str
    bounty_id: str
    
    # Participation details
    joined_at: datetime
    role: str = "contributor"  # contributor, reviewer, mentor
    
    # Progress tracking
    progress_percentage: float = 0.0
    milestones_completed: List[str] = []
    last_activity: Optional[datetime] = None
    
    # Communication
    status_updates: List[Dict[str, Any]] = []
    questions_asked: List[str] = []
    
    # Profile
    skill_assessment: Dict[str, float] = {}
    previous_bounties: List[str] = []

class BountyManager:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/frontend-market/data/improvement_bounties.db"
        self.init_database()
        
        # Scoring weights for different criteria
        self.judging_criteria_weights = {
            "code_quality": 0.25,
            "functionality": 0.30,
            "performance": 0.15,
            "usability": 0.15,
            "documentation": 0.10,
            "innovation": 0.05
        }
        
        # Skill level multipliers for bounty rewards
        self.skill_multipliers = {
            SkillLevel.BEGINNER: 1.0,
            SkillLevel.INTERMEDIATE: 1.5,
            SkillLevel.ADVANCED: 2.0,
            SkillLevel.EXPERT: 3.0
        }
    
    def init_database(self):
        """Initialize bounties database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Bounties table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bounties (
                id TEXT PRIMARY KEY,
                frontend_id TEXT NOT NULL,
                created_by TEXT NOT NULL,
                title TEXT NOT NULL,
                bounty_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                skill_level TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                reward_amount DECIMAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # Submissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bounty_submissions (
                id TEXT PRIMARY KEY,
                bounty_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'submitted',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                final_score REAL,
                data TEXT NOT NULL,
                FOREIGN KEY (bounty_id) REFERENCES bounties (id)
            )
        ''')
        
        # Participants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bounty_participants (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                bounty_id TEXT NOT NULL,
                role TEXT DEFAULT 'contributor',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                progress_percentage REAL DEFAULT 0.0,
                data TEXT NOT NULL,
                FOREIGN KEY (bounty_id) REFERENCES bounties (id),
                UNIQUE(user_id, bounty_id)
            )
        ''')
        
        # Rewards tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bounty_rewards (
                id TEXT PRIMARY KEY,
                bounty_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                amount DECIMAL NOT NULL,
                reward_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (bounty_id) REFERENCES bounties (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_bounty(self, bounty_data: Dict[str, Any]) -> Bounty:
        """Create a new improvement bounty"""
        
        bounty_id = f"BOUNTY_{uuid.uuid4().hex[:8].upper()}"
        reward_id = f"REWARD_{uuid.uuid4().hex[:8].upper()}"
        
        # Create reward
        reward_amount = Decimal(str(bounty_data["reward_amount"]))
        skill_multiplier = self.skill_multipliers.get(
            SkillLevel(bounty_data.get("skill_level", "intermediate")), 
            1.0
        )
        
        adjusted_reward = reward_amount * Decimal(str(skill_multiplier))
        
        reward = BountyReward(
            id=reward_id,
            bounty_id=bounty_id,
            amount=adjusted_reward,
            currency=bounty_data.get("currency", "USD"),
            reward_type=bounty_data.get("reward_type", "monetary"),
            milestone_based=bounty_data.get("milestone_based", False),
            milestones=bounty_data.get("milestones", []),
            sponsored_by=bounty_data.get("sponsored_by"),
            expires_at=datetime.now() + timedelta(days=bounty_data.get("duration_days", 30))
        )
        
        # Create bounty
        bounty = Bounty(
            id=bounty_id,
            frontend_id=bounty_data["frontend_id"],
            created_by=bounty_data["created_by"],
            title=bounty_data["title"],
            description=bounty_data["description"],
            bounty_type=BountyType(bounty_data["bounty_type"]),
            priority=Priority(bounty_data.get("priority", "medium")),
            skill_level=SkillLevel(bounty_data.get("skill_level", "intermediate")),
            requirements=bounty_data.get("requirements", []),
            acceptance_criteria=bounty_data.get("acceptance_criteria", []),
            technical_specifications=bounty_data.get("technical_specifications", {}),
            reward=reward,
            created_at=datetime.now(),
            expires_at=reward.expires_at,
            max_participants=bounty_data.get("max_participants", 5),
            judging_criteria=bounty_data.get("judging_criteria", self.judging_criteria_weights),
            judges=bounty_data.get("judges", []),
            tags=bounty_data.get("tags", []),
            estimated_hours=bounty_data.get("estimated_hours", 8),
            difficulty_score=bounty_data.get("difficulty_score", 3.0)
        )
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bounties 
            (id, frontend_id, created_by, title, bounty_type, priority, skill_level, 
             reward_amount, expires_at, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bounty.id, bounty.frontend_id, bounty.created_by,
            bounty.title, bounty.bounty_type.value, bounty.priority.value,
            bounty.skill_level.value, float(bounty.reward.amount),
            bounty.expires_at.isoformat() if bounty.expires_at else None,
            bounty.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created bounty {bounty_id}: {bounty.title}")
        return bounty
    
    async def publish_bounty(self, bounty_id: str) -> bool:
        """Publish a bounty to make it available for participation"""
        
        bounty = await self.get_bounty(bounty_id)
        if not bounty:
            return False
        
        # Validate bounty is ready for publishing
        if not bounty.requirements or not bounty.acceptance_criteria:
            raise ValueError("Bounty must have requirements and acceptance criteria")
        
        if bounty.reward.amount <= 0:
            raise ValueError("Bounty must have a positive reward amount")
        
        # Update status
        bounty.status = BountyStatus.OPEN
        bounty.started_at = datetime.now()
        
        # Update in database
        await self._update_bounty(bounty)
        
        # Notify interested developers (mock)
        await self._notify_bounty_published(bounty)
        
        logger.info(f"Published bounty {bounty_id}")
        return True
    
    async def join_bounty(self, bounty_id: str, user_id: str, 
                         skill_assessment: Dict[str, float] = None) -> BountyParticipant:
        """Join a bounty as a participant"""
        
        bounty = await self.get_bounty(bounty_id)
        if not bounty:
            raise ValueError(f"Bounty {bounty_id} not found")
        
        if bounty.status != BountyStatus.OPEN:
            raise ValueError("Bounty is not open for participation")
        
        if len(bounty.current_participants) >= bounty.max_participants:
            raise ValueError("Bounty has reached maximum participants")
        
        if user_id in bounty.current_participants:
            raise ValueError("User already participating in this bounty")
        
        # Create participant record
        participant_id = f"PARTICIPANT_{uuid.uuid4().hex[:8].upper()}"
        
        participant = BountyParticipant(
            id=participant_id,
            user_id=user_id,
            bounty_id=bounty_id,
            joined_at=datetime.now(),
            skill_assessment=skill_assessment or {},
            last_activity=datetime.now()
        )
        
        # Store participant
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bounty_participants 
            (id, user_id, bounty_id, role, joined_at, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            participant.id, participant.user_id, participant.bounty_id,
            participant.role, participant.joined_at.isoformat(),
            participant.model_dump_json()
        ))
        
        # Update bounty participants list
        bounty.current_participants.append(user_id)
        if len(bounty.current_participants) == bounty.max_participants:
            bounty.status = BountyStatus.IN_PROGRESS
        
        await self._update_bounty(bounty)
        
        conn.commit()
        conn.close()
        
        logger.info(f"User {user_id} joined bounty {bounty_id}")
        return participant
    
    async def submit_solution(self, submission_data: Dict[str, Any]) -> BountySubmission:
        """Submit a solution for a bounty"""
        
        bounty = await self.get_bounty(submission_data["bounty_id"])
        if not bounty:
            raise ValueError("Bounty not found")
        
        if submission_data["participant_id"] not in bounty.current_participants:
            raise ValueError("User is not a participant in this bounty")
        
        if bounty.status not in [BountyStatus.OPEN, BountyStatus.IN_PROGRESS]:
            raise ValueError("Bounty is not accepting submissions")
        
        # Create submission
        submission_id = f"SUBMISSION_{uuid.uuid4().hex[:8].upper()}"
        
        submission = BountySubmission(
            id=submission_id,
            bounty_id=submission_data["bounty_id"],
            participant_id=submission_data["participant_id"],
            title=submission_data["title"],
            description=submission_data["description"],
            solution_type=submission_data.get("solution_type", "code"),
            repository_url=submission_data.get("repository_url"),
            demo_url=submission_data.get("demo_url"),
            documentation_url=submission_data.get("documentation_url"),
            file_attachments=submission_data.get("file_attachments", []),
            changes_made=submission_data.get("changes_made", []),
            testing_notes=submission_data.get("testing_notes", ""),
            performance_impact=submission_data.get("performance_impact", {}),
            submitted_at=datetime.now(),
            time_spent_hours=submission_data.get("time_spent_hours", 0),
            collaboration_notes=submission_data.get("collaboration_notes", "")
        )
        
        # Store submission
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bounty_submissions 
            (id, bounty_id, participant_id, title, submitted_at, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            submission.id, submission.bounty_id, submission.participant_id,
            submission.title, submission.submitted_at.isoformat(),
            submission.model_dump_json()
        ))
        
        # Update bounty submissions list
        bounty.submissions.append(submission_id)
        bounty.status = BountyStatus.UNDER_REVIEW
        await self._update_bounty(bounty)
        
        conn.commit()
        conn.close()
        
        # Notify judges
        await self._notify_new_submission(bounty, submission)
        
        logger.info(f"Received submission {submission_id} for bounty {bounty.id}")
        return submission
    
    async def evaluate_submission(self, submission_id: str, judge_id: str,
                                scores: Dict[str, float], feedback: str) -> BountySubmission:
        """Evaluate a bounty submission"""
        
        submission = await self.get_submission(submission_id)
        if not submission:
            raise ValueError("Submission not found")
        
        bounty = await self.get_bounty(submission.bounty_id)
        if not bounty:
            raise ValueError("Associated bounty not found")
        
        if judge_id not in bounty.judges:
            raise ValueError("User is not authorized to judge this bounty")
        
        # Calculate weighted score
        weighted_score = 0.0
        total_weight = 0.0
        
        for criterion, score in scores.items():
            weight = bounty.judging_criteria.get(criterion, 0.0)
            weighted_score += score * weight
            total_weight += weight
        
        final_score = weighted_score / total_weight if total_weight > 0 else 0.0
        
        # Update submission
        submission.scores[judge_id] = scores
        submission.feedback.append({
            "judge_id": judge_id,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat(),
            "score": final_score
        })
        submission.final_score = final_score
        
        # Update submission in database
        await self._update_submission(submission)
        
        logger.info(f"Evaluated submission {submission_id} with score {final_score:.2f}")
        return submission
    
    async def complete_bounty(self, bounty_id: str, winning_submission_id: str) -> Dict[str, Any]:
        """Complete a bounty and distribute rewards"""
        
        bounty = await self.get_bounty(bounty_id)
        if not bounty:
            raise ValueError("Bounty not found")
        
        winning_submission = await self.get_submission(winning_submission_id)
        if not winning_submission:
            raise ValueError("Winning submission not found")
        
        # Get all submissions for ranking
        all_submissions = []
        for sub_id in bounty.submissions:
            submission = await self.get_submission(sub_id)
            if submission and submission.final_score is not None:
                all_submissions.append(submission)
        
        # Sort by score
        all_submissions.sort(key=lambda x: x.final_score, reverse=True)
        
        # Distribute rewards
        reward_distributions = []
        
        if len(all_submissions) > 0:
            # Winner reward
            winner_amount = bounty.reward.amount * Decimal(str(bounty.reward.winner_percentage / 100))
            winner_reward = await self._create_reward_distribution(
                bounty_id, all_submissions[0].participant_id, winner_amount, "winner"
            )
            reward_distributions.append(winner_reward)
            
            # Runner-up reward
            if len(all_submissions) > 1:
                runner_up_amount = bounty.reward.amount * Decimal(str(bounty.reward.runner_up_percentage / 100))
                runner_up_reward = await self._create_reward_distribution(
                    bounty_id, all_submissions[1].participant_id, runner_up_amount, "runner_up"
                )
                reward_distributions.append(runner_up_reward)
            
            # Participation rewards
            participation_amount = bounty.reward.amount * Decimal(str(bounty.reward.participation_percentage / 100))
            participant_share = participation_amount / len(all_submissions[2:]) if len(all_submissions) > 2 else Decimal('0')
            
            for submission in all_submissions[2:]:
                if participant_share > 0:
                    participant_reward = await self._create_reward_distribution(
                        bounty_id, submission.participant_id, participant_share, "participation"
                    )
                    reward_distributions.append(participant_reward)
        
        # Update bounty status
        bounty.status = BountyStatus.COMPLETED
        bounty.completed_at = datetime.now()
        await self._update_bounty(bounty)
        
        # Notification and analytics
        completion_summary = {
            "bounty_id": bounty_id,
            "winning_submission": winning_submission_id,
            "winner_id": winning_submission.participant_id,
            "total_submissions": len(all_submissions),
            "total_rewards_distributed": sum(r["amount"] for r in reward_distributions),
            "completion_time": (datetime.now() - bounty.created_at).days,
            "reward_distributions": reward_distributions
        }
        
        logger.info(f"Completed bounty {bounty_id} with {len(reward_distributions)} rewards distributed")
        return completion_summary
    
    async def get_bounty_leaderboard(self, frontend_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get bounty participation leaderboard"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Query for user statistics
        query = '''
            SELECT 
                bp.user_id,
                COUNT(DISTINCT bp.bounty_id) as bounties_joined,
                COUNT(DISTINCT bs.id) as submissions_made,
                AVG(COALESCE(bs.final_score, 0)) as avg_score,
                SUM(CASE WHEN br.reward_type = 'winner' THEN br.amount ELSE 0 END) as total_winnings,
                COUNT(CASE WHEN br.reward_type = 'winner' THEN 1 END) as wins
            FROM bounty_participants bp
            LEFT JOIN bounty_submissions bs ON bp.user_id = bs.participant_id
            LEFT JOIN bounty_rewards br ON bp.user_id = br.recipient_id
        '''
        
        if frontend_id:
            query += ' JOIN bounties b ON bp.bounty_id = b.id WHERE b.frontend_id = ?'
            cursor.execute(query + ' GROUP BY bp.user_id ORDER BY total_winnings DESC, wins DESC LIMIT 50', 
                          (frontend_id,))
        else:
            cursor.execute(query + ' GROUP BY bp.user_id ORDER BY total_winnings DESC, wins DESC LIMIT 50')
        
        results = cursor.fetchall()
        conn.close()
        
        leaderboard = []
        for i, row in enumerate(results):
            leaderboard.append({
                "rank": i + 1,
                "user_id": row[0],
                "bounties_joined": row[1],
                "submissions_made": row[2],
                "average_score": round(row[3], 2) if row[3] else 0.0,
                "total_winnings": float(row[4]) if row[4] else 0.0,
                "wins": row[5],
                "success_rate": round(row[5] / row[1] * 100, 1) if row[1] > 0 else 0.0
            })
        
        return leaderboard
    
    async def get_bounty_analytics(self, frontend_id: str) -> Dict[str, Any]:
        """Get bounty analytics for a frontend"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Basic statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_bounties,
                COUNT(CASE WHEN status = 'open' THEN 1 END) as open_bounties,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_bounties,
                AVG(reward_amount) as avg_reward,
                SUM(reward_amount) as total_rewards
            FROM bounties
            WHERE frontend_id = ?
        ''', (frontend_id,))
        
        stats = cursor.fetchone()
        
        # Bounty types distribution
        cursor.execute('''
            SELECT bounty_type, COUNT(*) 
            FROM bounties 
            WHERE frontend_id = ?
            GROUP BY bounty_type
        ''', (frontend_id,))
        
        type_distribution = dict(cursor.fetchall())
        
        # Average completion time
        cursor.execute('''
            SELECT AVG(julianday(completed_at) - julianday(created_at)) * 24 as avg_hours
            FROM bounties 
            WHERE frontend_id = ? AND status = 'completed' AND completed_at IS NOT NULL
        ''', (frontend_id,))
        
        avg_completion_time = cursor.fetchone()[0] or 0
        
        # Top participants
        cursor.execute('''
            SELECT bp.user_id, COUNT(*) as participation_count
            FROM bounty_participants bp
            JOIN bounties b ON bp.bounty_id = b.id
            WHERE b.frontend_id = ?
            GROUP BY bp.user_id
            ORDER BY participation_count DESC
            LIMIT 5
        ''', (frontend_id,))
        
        top_participants = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_bounties": stats[0],
            "open_bounties": stats[1], 
            "completed_bounties": stats[2],
            "average_reward": float(stats[3]) if stats[3] else 0.0,
            "total_rewards_budget": float(stats[4]) if stats[4] else 0.0,
            "completion_rate": round(stats[2] / stats[0] * 100, 1) if stats[0] > 0 else 0.0,
            "average_completion_time_hours": round(avg_completion_time, 1),
            "bounty_types": type_distribution,
            "top_participants": top_participants
        }
    
    async def get_bounty(self, bounty_id: str) -> Optional[Bounty]:
        """Get bounty by ID"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT data FROM bounties WHERE id = ?', (bounty_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            bounty_data = json.loads(result[0])
            return Bounty(**bounty_data)
        
        return None
    
    async def get_submission(self, submission_id: str) -> Optional[BountySubmission]:
        """Get submission by ID"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT data FROM bounty_submissions WHERE id = ?', (submission_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            submission_data = json.loads(result[0])
            return BountySubmission(**submission_data)
        
        return None
    
    async def search_bounties(self, filters: Dict[str, Any], 
                            limit: int = 50) -> List[Bounty]:
        """Search bounties with filters"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT data FROM bounties WHERE 1=1"
        params = []
        
        if filters.get("frontend_id"):
            query += " AND frontend_id = ?"
            params.append(filters["frontend_id"])
        
        if filters.get("status"):
            query += " AND status = ?"
            params.append(filters["status"])
        
        if filters.get("bounty_type"):
            query += " AND bounty_type = ?"
            params.append(filters["bounty_type"])
        
        if filters.get("skill_level"):
            query += " AND skill_level = ?"
            params.append(filters["skill_level"])
        
        if filters.get("min_reward"):
            query += " AND reward_amount >= ?"
            params.append(filters["min_reward"])
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [Bounty(**json.loads(result[0])) for result in results]
    
    async def _update_bounty(self, bounty: Bounty):
        """Update bounty in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE bounties 
            SET status = ?, data = ?
            WHERE id = ?
        ''', (bounty.status.value, bounty.model_dump_json(), bounty.id))
        
        conn.commit()
        conn.close()
    
    async def _update_submission(self, submission: BountySubmission):
        """Update submission in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE bounty_submissions 
            SET final_score = ?, data = ?
            WHERE id = ?
        ''', (submission.final_score, submission.model_dump_json(), submission.id))
        
        conn.commit()
        conn.close()
    
    async def _create_reward_distribution(self, bounty_id: str, recipient_id: str,
                                        amount: Decimal, reward_type: str) -> Dict[str, Any]:
        """Create reward distribution record"""
        
        reward_id = f"DIST_{uuid.uuid4().hex[:8].upper()}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        reward_data = {
            "id": reward_id,
            "bounty_id": bounty_id,
            "recipient_id": recipient_id,
            "amount": float(amount),
            "reward_type": reward_type,
            "status": "pending",
            "awarded_at": datetime.now().isoformat()
        }
        
        cursor.execute('''
            INSERT INTO bounty_rewards 
            (id, bounty_id, recipient_id, amount, reward_type, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            reward_id, bounty_id, recipient_id, float(amount),
            reward_type, json.dumps(reward_data)
        ))
        
        conn.commit()
        conn.close()
        
        return reward_data
    
    async def _notify_bounty_published(self, bounty: Bounty):
        """Notify interested developers about new bounty"""
        # Mock notification system
        logger.info(f"Notified developers about new bounty: {bounty.title}")
    
    async def _notify_new_submission(self, bounty: Bounty, submission: BountySubmission):
        """Notify judges about new submission"""
        # Mock notification system
        logger.info(f"Notified judges about new submission for bounty: {bounty.title}")

# Global instance
bounty_manager = BountyManager()