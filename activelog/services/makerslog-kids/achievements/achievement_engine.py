import asyncio
import asyncpg
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import json
import uuid


class AchievementType(Enum):
    LEARNING = "learning"
    CREATIVITY = "creativity"
    PERSISTENCE = "persistence"
    COLLABORATION = "collaboration"
    EXPLORATION = "exploration"
    SKILL_BUILDING = "skill_building"
    MILESTONE = "milestone"
    SPECIAL_EVENT = "special_event"


class AchievementTier(Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    LEGENDARY = "legendary"


@dataclass
class Achievement:
    achievement_id: str
    name: str
    description: str
    category: AchievementType
    tier: AchievementTier
    badge_icon: str
    age_min: int
    age_max: int
    requirements: Dict[str, Any]
    rewards: Dict[str, Any]
    is_hidden: bool = False
    is_active: bool = True
    unlock_message: str = ""
    celebration_animation: str = ""


@dataclass
class UserAchievement:
    user_id: str
    achievement_id: str
    progress: Dict[str, Any]
    completed: bool
    completed_at: Optional[datetime]
    progress_percentage: float
    next_milestone: Optional[str]


@dataclass
class AchievementProgress:
    achievement_id: str
    current_value: int
    target_value: int
    progress_percentage: float
    completed: bool
    requirements_met: Dict[str, bool]


class AchievementEngine:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.achievement_definitions = {}
        self.progress_trackers = {}
        
    async def initialize_tables(self):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS achievements (
                    id SERIAL PRIMARY KEY,
                    achievement_id VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    tier VARCHAR(20) NOT NULL,
                    badge_icon VARCHAR(100),
                    age_min INTEGER NOT NULL,
                    age_max INTEGER NOT NULL,
                    requirements JSONB NOT NULL,
                    rewards JSONB NOT NULL,
                    is_hidden BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    unlock_message TEXT,
                    celebration_animation VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    achievement_id VARCHAR(50) NOT NULL,
                    progress JSONB DEFAULT '{}',
                    completed BOOLEAN DEFAULT FALSE,
                    completed_at TIMESTAMP,
                    notified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, achievement_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS achievement_events (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    event_data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS achievement_milestones (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    milestone_type VARCHAR(50) NOT NULL,
                    current_value INTEGER DEFAULT 0,
                    best_value INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, milestone_type)
                )
            """)

        # Initialize default achievements
        await self.setup_default_achievements()

    async def setup_default_achievements(self):
        """Set up the default achievement definitions"""
        default_achievements = [
            # Learning Achievements
            Achievement(
                achievement_id="first_lesson",
                name="Getting Started",
                description="Complete your very first lesson",
                category=AchievementType.LEARNING,
                tier=AchievementTier.BRONZE,
                badge_icon="🎓",
                age_min=5,
                age_max=18,
                requirements={"lessons_completed": 1},
                rewards={"coins": 10, "title": "Eager Learner"},
                unlock_message="🎉 Welcome to your learning journey! You've taken the first step!",
                celebration_animation="confetti"
            ),
            
            Achievement(
                achievement_id="lesson_streak_7",
                name="Week Warrior",
                description="Complete lessons for 7 days in a row",
                category=AchievementType.PERSISTENCE,
                tier=AchievementTier.SILVER,
                badge_icon="🔥",
                age_min=5,
                age_max=18,
                requirements={"daily_streak": 7},
                rewards={"coins": 50, "multiplier": 1.2, "title": "Consistent Learner"},
                unlock_message="🔥 Amazing dedication! Your consistency is paying off!",
                celebration_animation="fire"
            ),
            
            Achievement(
                achievement_id="project_creator",
                name="First Creation",
                description="Complete your first coding project",
                category=AchievementType.CREATIVITY,
                tier=AchievementTier.BRONZE,
                badge_icon="🚀",
                age_min=6,
                age_max=18,
                requirements={"projects_completed": 1},
                rewards={"coins": 25, "tools": ["advanced_editor"], "title": "Creator"},
                unlock_message="🚀 You're now officially a creator! What will you build next?",
                celebration_animation="rocket"
            ),
            
            Achievement(
                achievement_id="helping_hand",
                name="Helpful Friend",
                description="Help other users 5 times",
                category=AchievementType.COLLABORATION,
                tier=AchievementTier.SILVER,
                badge_icon="🤝",
                age_min=7,
                age_max=18,
                requirements={"help_count": 5},
                rewards={"coins": 40, "badge": "helper_badge", "title": "Community Helper"},
                unlock_message="🤝 Thank you for being such a helpful community member!",
                celebration_animation="hearts"
            ),
            
            Achievement(
                achievement_id="code_explorer",
                name="Code Explorer",
                description="Try 3 different programming languages",
                category=AchievementType.EXPLORATION,
                tier=AchievementTier.GOLD,
                badge_icon="🌟",
                age_min=8,
                age_max=18,
                requirements={"languages_tried": 3},
                rewards={"coins": 75, "unlock": ["advanced_tutorials"], "title": "Polyglot"},
                unlock_message="🌟 You're a true explorer of the coding world!",
                celebration_animation="stars"
            ),
            
            Achievement(
                achievement_id="problem_solver",
                name="Problem Solver",
                description="Debug and fix 10 code issues",
                category=AchievementType.SKILL_BUILDING,
                tier=AchievementTier.SILVER,
                badge_icon="🔧",
                age_min=9,
                age_max=18,
                requirements={"bugs_fixed": 10},
                rewards={"coins": 60, "tools": ["debug_helper"], "title": "Debugger"},
                unlock_message="🔧 Your problem-solving skills are impressive!",
                celebration_animation="tools"
            ),
            
            Achievement(
                achievement_id="marathon_coder",
                name="Marathon Coder",
                description="Code for 2 hours in a single session",
                category=AchievementType.PERSISTENCE,
                tier=AchievementTier.GOLD,
                badge_icon="⏰",
                age_min=10,
                age_max=18,
                requirements={"session_duration": 120},  # minutes
                rewards={"coins": 80, "multiplier": 1.5, "title": "Focused Coder"},
                unlock_message="⏰ Your focus and dedication are remarkable!",
                celebration_animation="clock"
            ),
            
            Achievement(
                achievement_id="creative_genius",
                name="Creative Genius",
                description="Create 5 unique and original projects",
                category=AchievementType.CREATIVITY,
                tier=AchievementTier.PLATINUM,
                badge_icon="🎨",
                age_min=8,
                age_max=18,
                requirements={"original_projects": 5, "creativity_score": 80},
                rewards={"coins": 120, "unlock": ["premium_assets"], "title": "Genius Creator"},
                unlock_message="🎨 Your creativity knows no bounds! You're a true artist!",
                celebration_animation="rainbow"
            ),
            
            Achievement(
                achievement_id="knowledge_master",
                name="Knowledge Master",
                description="Complete 50 lessons across different topics",
                category=AchievementType.MILESTONE,
                tier=AchievementTier.GOLD,
                badge_icon="📚",
                age_min=6,
                age_max=18,
                requirements={"lessons_completed": 50, "topics_covered": 5},
                rewards={"coins": 100, "unlock": ["master_courses"], "title": "Scholar"},
                unlock_message="📚 You've become a true scholar! Knowledge is power!",
                celebration_animation="books"
            ),
            
            Achievement(
                achievement_id="community_champion",
                name="Community Champion", 
                description="Be active in the community for 30 days",
                category=AchievementType.COLLABORATION,
                tier=AchievementTier.PLATINUM,
                badge_icon="👑",
                age_min=10,
                age_max=18,
                requirements={"active_days": 30, "interactions": 50},
                rewards={"coins": 150, "status": "champion", "title": "Community Champion"},
                unlock_message="👑 You're a true champion of our community!",
                celebration_animation="crown"
            ),
            
            # Age-specific achievements
            Achievement(
                achievement_id="young_explorer",
                name="Young Explorer",
                description="Complete your first 10 activities (ages 5-8)",
                category=AchievementType.MILESTONE,
                tier=AchievementTier.SILVER,
                badge_icon="🧸",
                age_min=5,
                age_max=8,
                requirements={"activities_completed": 10},
                rewards={"coins": 30, "stickers": 5, "title": "Little Explorer"},
                unlock_message="🧸 You're such a smart little explorer!",
                celebration_animation="balloons"
            ),
            
            Achievement(
                achievement_id="teen_innovator",
                name="Teen Innovator",
                description="Create an innovative project that helps others (ages 13+)",
                category=AchievementType.CREATIVITY,
                tier=AchievementTier.LEGENDARY,
                badge_icon="💡",
                age_min=13,
                age_max=18,
                requirements={"innovation_project": 1, "peer_rating": 4.5},
                rewards={"coins": 200, "featured": True, "title": "Innovator"},
                unlock_message="💡 Your innovation will inspire others for years to come!",
                celebration_animation="innovation"
            )
        ]
        
        # Store achievements in database and cache
        for achievement in default_achievements:
            await self.create_achievement(achievement)

    async def create_achievement(self, achievement: Achievement):
        """Create a new achievement definition"""
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO achievements (
                        achievement_id, name, description, category, tier, badge_icon,
                        age_min, age_max, requirements, rewards, is_hidden, is_active,
                        unlock_message, celebration_animation
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT (achievement_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    requirements = EXCLUDED.requirements,
                    rewards = EXCLUDED.rewards
                """,
                    achievement.achievement_id, achievement.name, achievement.description,
                    achievement.category.value, achievement.tier.value, achievement.badge_icon,
                    achievement.age_min, achievement.age_max,
                    json.dumps(achievement.requirements), json.dumps(achievement.rewards),
                    achievement.is_hidden, achievement.is_active,
                    achievement.unlock_message, achievement.celebration_animation
                )
                
                # Cache the achievement
                self.achievement_definitions[achievement.achievement_id] = achievement
                
            except Exception as e:
                print(f"Failed to create achievement {achievement.achievement_id}: {e}")

    async def track_user_event(self, user_id: str, event_type: str, event_data: Dict):
        """Track user event that might trigger achievement progress"""
        # Log the event
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO achievement_events (user_id, event_type, event_data)
                VALUES ($1, $2, $3)
            """, user_id, event_type, json.dumps(event_data))
        
        # Update relevant milestones
        await self.update_milestones(user_id, event_type, event_data)
        
        # Check for achievement progress
        await self.check_achievement_progress(user_id, event_type, event_data)

    async def update_milestones(self, user_id: str, event_type: str, event_data: Dict):
        """Update user milestone counters"""
        milestone_updates = self._get_milestone_updates(event_type, event_data)
        
        async with self.db_pool.acquire() as conn:
            for milestone_type, value_change in milestone_updates.items():
                await conn.execute("""
                    INSERT INTO achievement_milestones (user_id, milestone_type, current_value, best_value, last_updated)
                    VALUES ($1, $2, $3, $3, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id, milestone_type)
                    DO UPDATE SET 
                        current_value = achievement_milestones.current_value + $3,
                        best_value = GREATEST(achievement_milestones.best_value, achievement_milestones.current_value + $3),
                        last_updated = CURRENT_TIMESTAMP
                """, user_id, milestone_type, value_change)

    def _get_milestone_updates(self, event_type: str, event_data: Dict) -> Dict[str, int]:
        """Map events to milestone updates"""
        updates = {}
        
        if event_type == "lesson_completed":
            updates["lessons_completed"] = 1
            updates["topics_covered"] = 1 if event_data.get("new_topic") else 0
            
        elif event_type == "project_completed":
            updates["projects_completed"] = 1
            if event_data.get("original"):
                updates["original_projects"] = 1
                
        elif event_type == "help_provided":
            updates["help_count"] = 1
            updates["interactions"] = 1
            
        elif event_type == "bug_fixed":
            updates["bugs_fixed"] = 1
            
        elif event_type == "language_used":
            # This would be handled differently - checking unique languages
            pass
            
        elif event_type == "session_completed":
            duration = event_data.get("duration_minutes", 0)
            updates["total_session_time"] = duration
            
        elif event_type == "daily_active":
            updates["active_days"] = 1
            updates["daily_streak"] = self._calculate_streak_increment(event_data)
            
        return updates

    async def check_achievement_progress(self, user_id: str, event_type: str, event_data: Dict):
        """Check if any achievements should be unlocked or updated"""
        user_age = await self.get_user_age(user_id)
        
        # Get relevant achievements for this user's age
        relevant_achievements = await self.get_age_appropriate_achievements(user_age)
        
        # Check each achievement
        for achievement in relevant_achievements:
            current_progress = await self.get_user_achievement_progress(user_id, achievement.achievement_id)
            
            if current_progress.completed:
                continue  # Already completed
            
            # Check if this event affects this achievement
            if self._event_affects_achievement(event_type, achievement):
                new_progress = await self.calculate_achievement_progress(user_id, achievement)
                
                if new_progress.completed and not current_progress.completed:
                    # Achievement just completed!
                    await self.unlock_achievement(user_id, achievement)
                elif new_progress.progress_percentage > current_progress.progress_percentage:
                    # Progress updated
                    await self.update_achievement_progress(user_id, achievement.achievement_id, new_progress)

    async def unlock_achievement(self, user_id: str, achievement: Achievement):
        """Unlock an achievement for a user"""
        async with self.db_pool.acquire() as conn:
            # Mark achievement as completed
            await conn.execute("""
                INSERT INTO user_achievements (user_id, achievement_id, completed, completed_at, progress)
                VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP, $3)
                ON CONFLICT (user_id, achievement_id)
                DO UPDATE SET 
                    completed = TRUE,
                    completed_at = CURRENT_TIMESTAMP,
                    progress = EXCLUDED.progress
            """, user_id, achievement.achievement_id, json.dumps({"completed": True}))
        
        # Award rewards
        await self.award_achievement_rewards(user_id, achievement)
        
        # Create celebration notification
        await self.create_achievement_notification(user_id, achievement)
        
        # Check for chain achievements (achievements that unlock other achievements)
        await self.check_chain_achievements(user_id, achievement)

    async def award_achievement_rewards(self, user_id: str, achievement: Achievement):
        """Award the rewards for completing an achievement"""
        rewards = achievement.rewards
        
        # Award coins
        if "coins" in rewards:
            # This would integrate with the currency system
            from ..virtual_currency.currency_system import EarnReason
            # await currency_system.award_currency(user_id, EarnReason.ACHIEVEMENT_UNLOCKED, 
            #                                     {"amount": rewards["coins"]})
            pass
        
        # Award titles
        if "title" in rewards:
            await self.award_title(user_id, rewards["title"])
        
        # Award tools/features
        if "tools" in rewards:
            await self.award_tools(user_id, rewards["tools"])
        
        # Award multipliers
        if "multiplier" in rewards:
            await self.award_multiplier(user_id, rewards["multiplier"])

    async def get_user_achievements(self, user_id: str, include_locked: bool = False) -> Dict:
        """Get user's achievements and progress"""
        user_age = await self.get_user_age(user_id)
        
        async with self.db_pool.acquire() as conn:
            # Get user's completed achievements
            completed = await conn.fetch("""
                SELECT ua.*, a.name, a.description, a.badge_icon, a.tier, a.category,
                       a.unlock_message, a.rewards
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.achievement_id
                WHERE ua.user_id = $1 AND ua.completed = TRUE
                ORDER BY ua.completed_at DESC
            """, user_id)
            
            # Get user's in-progress achievements
            if include_locked:
                in_progress = await conn.fetch("""
                    SELECT ua.*, a.name, a.description, a.badge_icon, a.tier, a.category,
                           a.requirements
                    FROM user_achievements ua
                    JOIN achievements a ON ua.achievement_id = a.achievement_id
                    WHERE ua.user_id = $1 AND ua.completed = FALSE
                    ORDER BY ua.created_at DESC
                """, user_id)
            else:
                in_progress = []
            
            # Get available but not started achievements
            if include_locked:
                available = await conn.fetch("""
                    SELECT a.* FROM achievements a
                    WHERE a.is_active = TRUE 
                    AND a.age_min <= $2 AND a.age_max >= $2
                    AND a.is_hidden = FALSE
                    AND a.achievement_id NOT IN (
                        SELECT achievement_id FROM user_achievements 
                        WHERE user_id = $1
                    )
                """, user_id, user_age)
            else:
                available = []
        
        # Calculate progress for in-progress and available achievements
        progress_data = {}
        for achievement_row in in_progress + available:
            achievement = self._row_to_achievement(achievement_row)
            progress = await self.calculate_achievement_progress(user_id, achievement)
            progress_data[achievement.achievement_id] = progress
        
        return {
            "completed": [
                {
                    "achievement_id": row["achievement_id"],
                    "name": row["name"],
                    "description": row["description"],
                    "badge_icon": row["badge_icon"],
                    "tier": row["tier"],
                    "category": row["category"],
                    "completed_at": row["completed_at"].isoformat(),
                    "rewards": json.loads(row["rewards"])
                } for row in completed
            ],
            "in_progress": [
                {
                    "achievement_id": row["achievement_id"],
                    "name": row["name"],
                    "description": row["description"],
                    "badge_icon": row["badge_icon"],
                    "tier": row["tier"],
                    "category": row["category"],
                    "progress": progress_data.get(row["achievement_id"], {}).__dict__
                } for row in in_progress
            ],
            "available": [
                {
                    "achievement_id": row["achievement_id"],
                    "name": row["name"],
                    "description": row["description"],
                    "badge_icon": row["badge_icon"],
                    "tier": row["tier"],
                    "category": row["category"],
                    "requirements": json.loads(row["requirements"]),
                    "progress": progress_data.get(row["achievement_id"], {}).__dict__
                } for row in available
            ] if include_locked else [],
            "statistics": await self.get_achievement_statistics(user_id),
            "next_milestones": await self.get_next_milestones(user_id)
        }

    async def calculate_achievement_progress(self, user_id: str, achievement: Achievement) -> AchievementProgress:
        """Calculate current progress toward an achievement"""
        requirements = achievement.requirements
        requirements_met = {}
        total_progress = 0
        requirement_count = len(requirements)
        
        async with self.db_pool.acquire() as conn:
            for req_type, target_value in requirements.items():
                current_value = 0
                
                if req_type in ["lessons_completed", "projects_completed", "help_count", 
                               "bugs_fixed", "active_days", "original_projects", "topics_covered"]:
                    # Get from milestones table
                    current_value = await conn.fetchval("""
                        SELECT COALESCE(current_value, 0) FROM achievement_milestones
                        WHERE user_id = $1 AND milestone_type = $2
                    """, user_id, req_type) or 0
                
                elif req_type == "daily_streak":
                    current_value = await self.calculate_current_streak(user_id)
                
                elif req_type == "session_duration":
                    # Check recent sessions for this specific requirement
                    current_value = await self.get_max_session_duration(user_id)
                
                elif req_type == "languages_tried":
                    current_value = await self.count_unique_languages(user_id)
                
                elif req_type == "creativity_score":
                    current_value = await self.get_creativity_score(user_id)
                
                # Calculate progress for this requirement
                req_progress = min(current_value / target_value, 1.0) if target_value > 0 else 1.0
                requirements_met[req_type] = current_value >= target_value
                total_progress += req_progress
        
        overall_progress = (total_progress / requirement_count) if requirement_count > 0 else 0
        completed = all(requirements_met.values())
        
        return AchievementProgress(
            achievement_id=achievement.achievement_id,
            current_value=int(total_progress),
            target_value=requirement_count,
            progress_percentage=overall_progress * 100,
            completed=completed,
            requirements_met=requirements_met
        )

    async def get_achievement_leaderboard(self, category: AchievementType = None, 
                                        time_period: str = "all_time") -> List[Dict]:
        """Get achievement leaderboard"""
        async with self.db_pool.acquire() as conn:
            if category:
                # Leaderboard for specific category
                query = """
                    SELECT u.user_id, u.display_name,
                           COUNT(ua.achievement_id) as achievement_count,
                           SUM(CASE 
                               WHEN a.tier = 'bronze' THEN 1
                               WHEN a.tier = 'silver' THEN 2
                               WHEN a.tier = 'gold' THEN 3
                               WHEN a.tier = 'platinum' THEN 4
                               WHEN a.tier = 'legendary' THEN 5
                               ELSE 1 END) as points
                    FROM user_achievements ua
                    JOIN achievements a ON ua.achievement_id = a.achievement_id
                    JOIN user_profiles u ON ua.user_id = u.user_id
                    WHERE ua.completed = TRUE AND a.category = $1
                """
                params = [category.value]
            else:
                # Overall leaderboard
                query = """
                    SELECT u.user_id, u.display_name,
                           COUNT(ua.achievement_id) as achievement_count,
                           SUM(CASE 
                               WHEN a.tier = 'bronze' THEN 1
                               WHEN a.tier = 'silver' THEN 2
                               WHEN a.tier = 'gold' THEN 3
                               WHEN a.tier = 'platinum' THEN 4
                               WHEN a.tier = 'legendary' THEN 5
                               ELSE 1 END) as points
                    FROM user_achievements ua
                    JOIN achievements a ON ua.achievement_id = a.achievement_id
                    JOIN user_profiles u ON ua.user_id = u.user_id
                    WHERE ua.completed = TRUE
                """
                params = []
            
            if time_period == "week":
                query += " AND ua.completed_at >= CURRENT_DATE - INTERVAL '7 days'"
            elif time_period == "month":
                query += " AND ua.completed_at >= CURRENT_DATE - INTERVAL '30 days'"
            
            query += """
                GROUP BY u.user_id, u.display_name
                ORDER BY points DESC, achievement_count DESC
                LIMIT 20
            """
            
            leaderboard = await conn.fetch(query, *params)
        
        return [
            {
                "rank": idx + 1,
                "user_id": row["user_id"],
                "display_name": row["display_name"],
                "achievement_count": row["achievement_count"],
                "points": row["points"]
            } for idx, row in enumerate(leaderboard)
        ]

    async def get_achievement_suggestions(self, user_id: str) -> List[Dict]:
        """Get personalized achievement suggestions"""
        user_age = await self.get_user_age(user_id)
        
        # Get user's current progress
        milestones = await self.get_user_milestones(user_id)
        
        suggestions = []
        
        # Suggest achievements close to completion
        available_achievements = await self.get_age_appropriate_achievements(user_age)
        
        for achievement in available_achievements:
            if await self.user_has_achievement(user_id, achievement.achievement_id):
                continue
            
            progress = await self.calculate_achievement_progress(user_id, achievement)
            
            if progress.progress_percentage >= 60:  # Close to completion
                suggestions.append({
                    "achievement": {
                        "id": achievement.achievement_id,
                        "name": achievement.name,
                        "description": achievement.description,
                        "badge_icon": achievement.badge_icon,
                        "tier": achievement.tier.value,
                        "rewards": achievement.rewards
                    },
                    "progress": progress.progress_percentage,
                    "next_steps": self._generate_next_steps(achievement, progress),
                    "estimated_time": self._estimate_completion_time(achievement, progress),
                    "priority": "high" if progress.progress_percentage >= 80 else "medium"
                })
        
        # Sort by progress percentage and priority
        suggestions.sort(key=lambda x: x["progress"], reverse=True)
        
        return suggestions[:5]  # Return top 5 suggestions

    def _generate_next_steps(self, achievement: Achievement, progress: AchievementProgress) -> List[str]:
        """Generate actionable next steps for an achievement"""
        steps = []
        
        for req_type, is_met in progress.requirements_met.items():
            if not is_met:
                if req_type == "lessons_completed":
                    steps.append(f"Complete more lessons")
                elif req_type == "projects_completed":
                    steps.append(f"Finish more coding projects")
                elif req_type == "help_count":
                    steps.append(f"Help other community members")
                elif req_type == "daily_streak":
                    steps.append(f"Keep up your daily learning routine")
                elif req_type == "languages_tried":
                    steps.append(f"Try learning a new programming language")
                elif req_type == "bugs_fixed":
                    steps.append(f"Practice debugging code")
        
        return steps

    def _estimate_completion_time(self, achievement: Achievement, progress: AchievementProgress) -> str:
        """Estimate how long it would take to complete the achievement"""
        remaining = 100 - progress.progress_percentage
        
        if remaining <= 20:
            return "1-2 days"
        elif remaining <= 50:
            return "1 week"
        elif remaining <= 80:
            return "2-3 weeks"
        else:
            return "1 month+"

    # Helper methods
    async def get_user_age(self, user_id: str) -> int:
        """Get user age from profile"""
        # This would integrate with user profile system
        return 10  # Default age

    async def get_age_appropriate_achievements(self, user_age: int) -> List[Achievement]:
        """Get achievements appropriate for user's age"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM achievements
                WHERE is_active = TRUE AND age_min <= $1 AND age_max >= $1
            """, user_age)
        
        return [self._row_to_achievement(row) for row in rows]

    def _row_to_achievement(self, row) -> Achievement:
        """Convert database row to Achievement object"""
        return Achievement(
            achievement_id=row["achievement_id"],
            name=row["name"],
            description=row["description"],
            category=AchievementType(row["category"]),
            tier=AchievementTier(row["tier"]),
            badge_icon=row["badge_icon"],
            age_min=row["age_min"],
            age_max=row["age_max"],
            requirements=json.loads(row["requirements"]),
            rewards=json.loads(row["rewards"]),
            is_hidden=row["is_hidden"],
            is_active=row["is_active"],
            unlock_message=row.get("unlock_message", ""),
            celebration_animation=row.get("celebration_animation", "")
        )

    async def get_user_achievement_progress(self, user_id: str, achievement_id: str) -> AchievementProgress:
        """Get specific achievement progress for user"""
        async with self.db_pool.acquire() as conn:
            achievement_row = await conn.fetchrow("""
                SELECT * FROM achievements WHERE achievement_id = $1
            """, achievement_id)
            
            if not achievement_row:
                return AchievementProgress(achievement_id, 0, 1, 0, False, {})
            
            achievement = self._row_to_achievement(achievement_row)
            return await self.calculate_achievement_progress(user_id, achievement)

    def _event_affects_achievement(self, event_type: str, achievement: Achievement) -> bool:
        """Check if an event type affects an achievement's progress"""
        event_to_requirements = {
            "lesson_completed": ["lessons_completed", "topics_covered"],
            "project_completed": ["projects_completed", "original_projects"],
            "help_provided": ["help_count", "interactions"],
            "bug_fixed": ["bugs_fixed"],
            "daily_active": ["daily_streak", "active_days"],
            "session_completed": ["session_duration"],
            "language_used": ["languages_tried"]
        }
        
        affected_requirements = event_to_requirements.get(event_type, [])
        return any(req in achievement.requirements for req in affected_requirements)

    async def calculate_current_streak(self, user_id: str) -> int:
        """Calculate user's current daily streak"""
        # This would check for consecutive days of activity
        return 3  # Mock value

    async def get_max_session_duration(self, user_id: str) -> int:
        """Get user's longest session duration in minutes"""
        # This would integrate with time tracking system
        return 45  # Mock value

    async def count_unique_languages(self, user_id: str) -> int:
        """Count unique programming languages user has tried"""
        # This would track languages used in projects
        return 2  # Mock value

    async def get_creativity_score(self, user_id: str) -> float:
        """Get user's creativity score based on projects"""
        # This would analyze project originality and creativity
        return 75.0  # Mock value

    async def _calculate_streak_increment(self, event_data: Dict) -> int:
        """Calculate how much to increment streak (could be 0 if not consecutive)"""
        # This would check if the activity maintains a streak
        return 1

    async def user_has_achievement(self, user_id: str, achievement_id: str) -> bool:
        """Check if user has completed an achievement"""
        async with self.db_pool.acquire() as conn:
            exists = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM user_achievements 
                WHERE user_id = $1 AND achievement_id = $2 AND completed = TRUE)
            """, user_id, achievement_id)
            
            return exists

    async def get_user_milestones(self, user_id: str) -> Dict:
        """Get user's current milestone values"""
        async with self.db_pool.acquire() as conn:
            milestones = await conn.fetch("""
                SELECT milestone_type, current_value, best_value
                FROM achievement_milestones
                WHERE user_id = $1
            """, user_id)
        
        return {
            milestone["milestone_type"]: {
                "current": milestone["current_value"],
                "best": milestone["best_value"]
            } for milestone in milestones
        }

    async def get_achievement_statistics(self, user_id: str) -> Dict:
        """Get user's overall achievement statistics"""
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_completed,
                    COUNT(*) FILTER (WHERE a.tier = 'bronze') as bronze_count,
                    COUNT(*) FILTER (WHERE a.tier = 'silver') as silver_count,
                    COUNT(*) FILTER (WHERE a.tier = 'gold') as gold_count,
                    COUNT(*) FILTER (WHERE a.tier = 'platinum') as platinum_count,
                    COUNT(*) FILTER (WHERE a.tier = 'legendary') as legendary_count
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.achievement_id
                WHERE ua.user_id = $1 AND ua.completed = TRUE
            """, user_id)
            
            total_points = (
                (stats["bronze_count"] or 0) * 1 +
                (stats["silver_count"] or 0) * 2 +
                (stats["gold_count"] or 0) * 3 +
                (stats["platinum_count"] or 0) * 4 +
                (stats["legendary_count"] or 0) * 5
            )
        
        return {
            "total_achievements": stats["total_completed"] or 0,
            "total_points": total_points,
            "by_tier": {
                "bronze": stats["bronze_count"] or 0,
                "silver": stats["silver_count"] or 0,
                "gold": stats["gold_count"] or 0,
                "platinum": stats["platinum_count"] or 0,
                "legendary": stats["legendary_count"] or 0
            },
            "completion_rate": await self.calculate_completion_rate(user_id)
        }

    async def calculate_completion_rate(self, user_id: str) -> float:
        """Calculate what percentage of available achievements user has completed"""
        user_age = await self.get_user_age(user_id)
        
        async with self.db_pool.acquire() as conn:
            total_available = await conn.fetchval("""
                SELECT COUNT(*) FROM achievements
                WHERE is_active = TRUE AND is_hidden = FALSE
                AND age_min <= $1 AND age_max >= $1
            """, user_age)
            
            completed = await conn.fetchval("""
                SELECT COUNT(*) FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.achievement_id
                WHERE ua.user_id = $1 AND ua.completed = TRUE
                AND a.age_min <= $2 AND a.age_max >= $2
            """, user_id, user_age)
        
        return (completed / total_available * 100) if total_available > 0 else 0

    async def get_next_milestones(self, user_id: str) -> List[Dict]:
        """Get user's next upcoming milestones"""
        milestones = await self.get_user_milestones(user_id)
        next_milestones = []
        
        # Common milestone thresholds
        milestone_thresholds = {
            "lessons_completed": [5, 10, 25, 50, 100],
            "projects_completed": [1, 3, 5, 10, 20],
            "help_count": [1, 5, 10, 25, 50],
            "daily_streak": [3, 7, 14, 30, 100]
        }
        
        for milestone_type, thresholds in milestone_thresholds.items():
            current_value = milestones.get(milestone_type, {}).get("current", 0)
            
            # Find next threshold
            next_threshold = None
            for threshold in thresholds:
                if current_value < threshold:
                    next_threshold = threshold
                    break
            
            if next_threshold:
                next_milestones.append({
                    "type": milestone_type,
                    "current": current_value,
                    "target": next_threshold,
                    "progress": (current_value / next_threshold) * 100,
                    "description": self._get_milestone_description(milestone_type, next_threshold)
                })
        
        return sorted(next_milestones, key=lambda x: x["progress"], reverse=True)[:3]

    def _get_milestone_description(self, milestone_type: str, threshold: int) -> str:
        """Get human-readable description of milestone"""
        descriptions = {
            "lessons_completed": f"Complete {threshold} lessons",
            "projects_completed": f"Finish {threshold} projects",
            "help_count": f"Help others {threshold} times",
            "daily_streak": f"Learn for {threshold} days in a row"
        }
        
        return descriptions.get(milestone_type, f"Reach {threshold} in {milestone_type}")

    # Additional helper methods for integration
    async def award_title(self, user_id: str, title: str):
        """Award a title to user"""
        # This would integrate with user profile system
        pass

    async def award_tools(self, user_id: str, tools: List[str]):
        """Award tools/features to user"""
        # This would integrate with feature unlock system
        pass

    async def award_multiplier(self, user_id: str, multiplier: float):
        """Award earning multiplier to user"""
        # This would integrate with currency system
        pass

    async def create_achievement_notification(self, user_id: str, achievement: Achievement):
        """Create notification for achievement unlock"""
        # This would integrate with notification system
        pass

    async def check_chain_achievements(self, user_id: str, completed_achievement: Achievement):
        """Check for achievements that are unlocked by completing other achievements"""
        # This would handle achievements with prerequisites
        pass

    async def update_achievement_progress(self, user_id: str, achievement_id: str, progress: AchievementProgress):
        """Update achievement progress in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_achievements (user_id, achievement_id, progress)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, achievement_id)
                DO UPDATE SET progress = EXCLUDED.progress
            """, user_id, achievement_id, json.dumps(progress.__dict__))