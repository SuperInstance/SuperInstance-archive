"""
Fitness Goal Tracking for ActiveLog Health Suite
Comprehensive fitness goal setting, tracking, and achievement system with AI-powered insights
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta, date
import json
import numpy as np
import uuid
from abc import ABC, abstractmethod

from ..devices.wearable_ingestion import DataType, wearable_ingestion

logger = logging.getLogger(__name__)

class GoalType(Enum):
    """Types of fitness goals"""
    STEPS = "steps"
    DISTANCE = "distance"
    CALORIES_BURNED = "calories_burned"
    ACTIVE_MINUTES = "active_minutes"
    EXERCISE_SESSIONS = "exercise_sessions"
    HEART_RATE_ZONE = "heart_rate_zone"
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    BODY_FAT_PERCENTAGE = "body_fat_percentage"
    MUSCLE_GAIN = "muscle_gain"
    STRENGTH = "strength"
    ENDURANCE = "endurance"
    FLEXIBILITY = "flexibility"
    SLEEP_DURATION = "sleep_duration"
    WATER_INTAKE = "water_intake"
    CUSTOM = "custom"

class GoalFrequency(Enum):
    """Goal frequency/duration"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"

class GoalStatus(Enum):
    """Goal status"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DifficultyLevel(Enum):
    """Goal difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class ProgressStatus(Enum):
    """Progress status"""
    ON_TRACK = "on_track"
    AHEAD = "ahead"
    BEHIND = "behind"
    AT_RISK = "at_risk"

@dataclass
class FitnessGoal:
    """Fitness goal definition"""
    goal_id: str
    user_id: str
    title: str
    description: str
    goal_type: GoalType
    target_value: Union[int, float]
    current_value: Union[int, float] = 0
    unit: str = ""
    frequency: GoalFrequency = GoalFrequency.DAILY
    start_date: datetime = field(default_factory=datetime.now)
    target_date: Optional[datetime] = None
    status: GoalStatus = GoalStatus.ACTIVE
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    priority: int = 1  # 1-5 scale
    tags: List[str] = field(default_factory=list)
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    reward_points: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completion_date: Optional[datetime] = None

@dataclass
class GoalProgress:
    """Goal progress tracking"""
    progress_id: str
    goal_id: str
    user_id: str
    date: date
    value: Union[int, float]
    percentage: float
    status: ProgressStatus
    notes: str = ""
    data_sources: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Milestone:
    """Goal milestone"""
    milestone_id: str
    goal_id: str
    title: str
    description: str
    target_value: Union[int, float]
    target_date: Optional[datetime] = None
    achieved: bool = False
    achieved_date: Optional[datetime] = None
    reward_points: int = 0

@dataclass
class Achievement:
    """User achievement/badge"""
    achievement_id: str
    user_id: str
    title: str
    description: str
    icon: str
    category: str
    earned_date: datetime
    goal_ids: List[str] = field(default_factory=list)
    points_earned: int = 0

@dataclass
class GoalRecommendation:
    """AI-generated goal recommendation"""
    recommendation_id: str
    user_id: str
    goal_type: GoalType
    suggested_target: Union[int, float]
    rationale: str
    confidence: float
    difficulty: DifficultyLevel
    timeline_days: int
    data_basis: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ProgressInsight:
    """Progress analysis insight"""
    insight_id: str
    goal_id: str
    user_id: str
    insight_type: str
    title: str
    description: str
    severity: str  # "info", "warning", "alert"
    recommendations: List[str] = field(default_factory=list)
    data_points: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

class GoalProgressCalculator(ABC):
    """Abstract base for goal progress calculation"""
    
    @abstractmethod
    async def calculate_progress(self, goal: FitnessGoal, data: List[Any]) -> float:
        """Calculate current progress for a goal"""
        pass
    
    @abstractmethod
    async def predict_completion(self, goal: FitnessGoal, progress_history: List[GoalProgress]) -> Optional[datetime]:
        """Predict when goal will be completed"""
        pass

class StepsGoalCalculator(GoalProgressCalculator):
    """Steps goal progress calculator"""
    
    async def calculate_progress(self, goal: FitnessGoal, data: List[Any]) -> float:
        """Calculate steps progress"""
        if goal.frequency == GoalFrequency.DAILY:
            # Get today's steps
            today_steps = sum(dp.value for dp in data 
                            if dp.data_type == DataType.STEPS and 
                            dp.timestamp.date() == datetime.now().date())
            
            return min(today_steps / goal.target_value, 1.0) if goal.target_value > 0 else 0
        
        elif goal.frequency == GoalFrequency.WEEKLY:
            # Get this week's steps
            week_start = datetime.now().date() - timedelta(days=datetime.now().weekday())
            week_steps = sum(dp.value for dp in data 
                           if dp.data_type == DataType.STEPS and 
                           dp.timestamp.date() >= week_start)
            
            return min(week_steps / goal.target_value, 1.0) if goal.target_value > 0 else 0
        
        return 0
    
    async def predict_completion(self, goal: FitnessGoal, progress_history: List[GoalProgress]) -> Optional[datetime]:
        """Predict steps goal completion"""
        if len(progress_history) < 3:
            return None
        
        # Calculate average daily progress rate
        recent_progress = progress_history[-7:]  # Last 7 days
        daily_rates = []
        
        for i in range(1, len(recent_progress)):
            days_diff = (recent_progress[i].date - recent_progress[i-1].date).days
            value_diff = recent_progress[i].value - recent_progress[i-1].value
            
            if days_diff > 0:
                daily_rates.append(value_diff / days_diff)
        
        if not daily_rates:
            return None
        
        avg_daily_rate = np.mean(daily_rates)
        remaining_value = goal.target_value - goal.current_value
        
        if avg_daily_rate <= 0:
            return None
        
        days_to_completion = remaining_value / avg_daily_rate
        return datetime.now() + timedelta(days=days_to_completion)

class WeightGoalCalculator(GoalProgressCalculator):
    """Weight goal progress calculator"""
    
    async def calculate_progress(self, goal: FitnessGoal, data: List[Any]) -> float:
        """Calculate weight goal progress"""
        # Get latest weight measurement
        weight_data = [dp for dp in data if dp.data_type == DataType.WEIGHT]
        
        if not weight_data:
            return 0
        
        latest_weight = sorted(weight_data, key=lambda x: x.timestamp)[-1].value
        start_weight = goal.current_value if goal.current_value > 0 else latest_weight
        
        if goal.goal_type == GoalType.WEIGHT_LOSS:
            progress = (start_weight - latest_weight) / (start_weight - goal.target_value)
        else:  # Weight gain
            progress = (latest_weight - start_weight) / (goal.target_value - start_weight)
        
        return min(max(progress, 0), 1.0)
    
    async def predict_completion(self, goal: FitnessGoal, progress_history: List[GoalProgress]) -> Optional[datetime]:
        """Predict weight goal completion"""
        if len(progress_history) < 5:
            return None
        
        # Fit trend line to recent weight measurements
        recent_values = [p.value for p in progress_history[-14:]]  # Last 2 weeks
        
        if len(recent_values) < 3:
            return None
        
        # Simple linear regression
        x = np.arange(len(recent_values))
        y = np.array(recent_values)
        
        slope, intercept = np.polyfit(x, y, 1)
        
        if abs(slope) < 0.001:  # No meaningful trend
            return None
        
        # Calculate when target will be reached
        remaining_change = goal.target_value - goal.current_value
        days_to_completion = remaining_change / slope if slope != 0 else None
        
        if days_to_completion and days_to_completion > 0:
            return datetime.now() + timedelta(days=days_to_completion)
        
        return None

class FitnessGoalTracker:
    """Comprehensive fitness goal tracking system"""
    
    def __init__(self):
        self.goals: Dict[str, FitnessGoal] = {}
        self.progress: Dict[str, List[GoalProgress]] = {}
        self.achievements: Dict[str, List[Achievement]] = {}
        self.recommendations: Dict[str, List[GoalRecommendation]] = {}
        self.insights: Dict[str, List[ProgressInsight]] = {}
        
        # Progress calculators
        self.calculators: Dict[GoalType, GoalProgressCalculator] = {
            GoalType.STEPS: StepsGoalCalculator(),
            GoalType.WEIGHT_LOSS: WeightGoalCalculator(),
            GoalType.WEIGHT_GAIN: WeightGoalCalculator(),
            # Add more calculators as needed
        }
        
        # Predefined achievements
        self.achievement_definitions = self._initialize_achievements()
        
        # Start background tasks
        asyncio.create_task(self._progress_tracker())
        asyncio.create_task(self._insight_generator())
    
    def _initialize_achievements(self) -> List[Dict[str, Any]]:
        """Initialize achievement definitions"""
        return [
            {
                'id': 'first_goal',
                'title': 'Goal Setter',
                'description': 'Set your first fitness goal',
                'icon': '🎯',
                'category': 'getting_started',
                'points': 10,
                'condition': lambda user_id: len([g for g in self.goals.values() if g.user_id == user_id]) >= 1
            },
            {
                'id': 'goal_achiever',
                'title': 'Goal Achiever',
                'description': 'Complete your first fitness goal',
                'icon': '🏆',
                'category': 'achievement',
                'points': 50,
                'condition': lambda user_id: len([g for g in self.goals.values() 
                                               if g.user_id == user_id and g.status == GoalStatus.COMPLETED]) >= 1
            },
            {
                'id': 'streak_master',
                'title': 'Streak Master',
                'description': 'Achieve daily goals for 7 consecutive days',
                'icon': '🔥',
                'category': 'consistency',
                'points': 100,
                'condition': self._check_streak_achievement
            },
            {
                'id': 'step_champion',
                'title': 'Step Champion',
                'description': 'Walk 100,000 steps in a month',
                'icon': '👟',
                'category': 'steps',
                'points': 200,
                'condition': self._check_step_champion
            }
        ]
    
    async def create_goal(self, goal: FitnessGoal) -> str:
        """Create a new fitness goal"""
        try:
            # Validate goal
            await self._validate_goal(goal)
            
            # Store goal
            self.goals[goal.goal_id] = goal
            self.progress[goal.goal_id] = []
            
            # Initialize progress tracking
            await self._initialize_goal_progress(goal)
            
            # Check for achievements
            await self._check_achievements(goal.user_id)
            
            logger.info(f"Created fitness goal: {goal.title} ({goal.goal_id})")
            return goal.goal_id
            
        except Exception as e:
            logger.error(f"Failed to create fitness goal: {e}")
            raise
    
    async def _validate_goal(self, goal: FitnessGoal):
        """Validate goal parameters"""
        if goal.target_value <= 0:
            raise ValueError("Target value must be positive")
        
        if goal.target_date and goal.target_date <= goal.start_date:
            raise ValueError("Target date must be after start date")
        
        if goal.priority < 1 or goal.priority > 5:
            raise ValueError("Priority must be between 1 and 5")
    
    async def _initialize_goal_progress(self, goal: FitnessGoal):
        """Initialize progress tracking for a new goal"""
        # Create initial progress entry
        initial_progress = GoalProgress(
            progress_id=str(uuid.uuid4()),
            goal_id=goal.goal_id,
            user_id=goal.user_id,
            date=datetime.now().date(),
            value=goal.current_value,
            percentage=0.0,
            status=ProgressStatus.ON_TRACK
        )
        
        self.progress[goal.goal_id].append(initial_progress)
    
    async def update_goal_progress(self, goal_id: str) -> Optional[GoalProgress]:
        """Update progress for a specific goal"""
        if goal_id not in self.goals:
            return None
        
        goal = self.goals[goal_id]
        
        if goal.status != GoalStatus.ACTIVE:
            return None
        
        try:
            # Get relevant health data
            health_data = await self._get_goal_data(goal)
            
            # Calculate progress
            if goal.goal_type in self.calculators:
                calculator = self.calculators[goal.goal_type]
                progress_value = await calculator.calculate_progress(goal, health_data)
            else:
                progress_value = goal.current_value / goal.target_value if goal.target_value > 0 else 0
            
            progress_percentage = min(progress_value * 100, 100)
            
            # Determine status
            if progress_percentage >= 100:
                status = ProgressStatus.AHEAD
                goal.status = GoalStatus.COMPLETED
                goal.completion_date = datetime.now()
            elif self._is_ahead_of_schedule(goal, progress_percentage):
                status = ProgressStatus.AHEAD
            elif self._is_behind_schedule(goal, progress_percentage):
                status = ProgressStatus.BEHIND
            elif self._is_at_risk(goal, progress_percentage):
                status = ProgressStatus.AT_RISK
            else:
                status = ProgressStatus.ON_TRACK
            
            # Create progress entry
            progress = GoalProgress(
                progress_id=str(uuid.uuid4()),
                goal_id=goal_id,
                user_id=goal.user_id,
                date=datetime.now().date(),
                value=progress_value * goal.target_value,
                percentage=progress_percentage,
                status=status,
                data_sources=[dp.device_id for dp in health_data]
            )
            
            # Update goal current value
            goal.current_value = progress.value
            goal.updated_at = datetime.now()
            
            # Store progress
            self.progress[goal_id].append(progress)
            
            # Check milestones
            await self._check_milestones(goal, progress)
            
            # Check achievements
            await self._check_achievements(goal.user_id)
            
            logger.info(f"Updated progress for goal {goal_id}: {progress_percentage:.1f}%")
            return progress
            
        except Exception as e:
            logger.error(f"Failed to update progress for goal {goal_id}: {e}")
            return None
    
    async def _get_goal_data(self, goal: FitnessGoal) -> List[Any]:
        """Get health data relevant to a goal"""
        
        # Determine time range based on goal frequency
        if goal.frequency == GoalFrequency.DAILY:
            since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif goal.frequency == GoalFrequency.WEEKLY:
            since = datetime.now() - timedelta(days=7)
        elif goal.frequency == GoalFrequency.MONTHLY:
            since = datetime.now() - timedelta(days=30)
        else:
            since = goal.start_date
        
        # Get data from wearable devices
        all_data = []
        devices = await wearable_ingestion.list_devices()
        
        for device_id in devices.keys():
            device_data = await wearable_ingestion.get_device_data(
                device_id, 
                self._get_relevant_data_types(goal.goal_type),
                since
            )
            all_data.extend(device_data)
        
        return all_data
    
    def _get_relevant_data_types(self, goal_type: GoalType) -> List[DataType]:
        """Get relevant data types for a goal type"""
        mapping = {
            GoalType.STEPS: [DataType.STEPS],
            GoalType.DISTANCE: [DataType.DISTANCE],
            GoalType.CALORIES_BURNED: [DataType.CALORIES],
            GoalType.ACTIVE_MINUTES: [DataType.ACTIVITY],
            GoalType.HEART_RATE_ZONE: [DataType.HEART_RATE],
            GoalType.WEIGHT_LOSS: [DataType.WEIGHT],
            GoalType.WEIGHT_GAIN: [DataType.WEIGHT],
            GoalType.SLEEP_DURATION: [DataType.SLEEP],
        }
        
        return mapping.get(goal_type, [])
    
    def _is_ahead_of_schedule(self, goal: FitnessGoal, progress_percentage: float) -> bool:
        """Check if goal progress is ahead of schedule"""
        if not goal.target_date:
            return progress_percentage > 100
        
        total_days = (goal.target_date - goal.start_date).days
        elapsed_days = (datetime.now() - goal.start_date).days
        
        if total_days <= 0:
            return False
        
        expected_percentage = (elapsed_days / total_days) * 100
        return progress_percentage > expected_percentage * 1.2  # 20% ahead
    
    def _is_behind_schedule(self, goal: FitnessGoal, progress_percentage: float) -> bool:
        """Check if goal progress is behind schedule"""
        if not goal.target_date:
            return False
        
        total_days = (goal.target_date - goal.start_date).days
        elapsed_days = (datetime.now() - goal.start_date).days
        
        if total_days <= 0:
            return False
        
        expected_percentage = (elapsed_days / total_days) * 100
        return progress_percentage < expected_percentage * 0.8  # 20% behind
    
    def _is_at_risk(self, goal: FitnessGoal, progress_percentage: float) -> bool:
        """Check if goal is at risk of not being completed"""
        if not goal.target_date:
            return False
        
        # Check if severely behind schedule
        total_days = (goal.target_date - goal.start_date).days
        elapsed_days = (datetime.now() - goal.start_date).days
        remaining_days = (goal.target_date - datetime.now()).days
        
        if total_days <= 0 or remaining_days <= 0:
            return progress_percentage < 100
        
        expected_percentage = (elapsed_days / total_days) * 100
        return progress_percentage < expected_percentage * 0.5  # 50% behind
    
    async def _check_milestones(self, goal: FitnessGoal, progress: GoalProgress):
        """Check and update milestone achievements"""
        for milestone_data in goal.milestones:
            if milestone_data.get('achieved'):
                continue
            
            target_value = milestone_data.get('target_value', 0)
            
            if progress.value >= target_value:
                milestone_data['achieved'] = True
                milestone_data['achieved_date'] = datetime.now().isoformat()
                
                # Award points
                points = milestone_data.get('reward_points', 10)
                goal.reward_points += points
                
                logger.info(f"Milestone achieved for goal {goal.goal_id}: {milestone_data.get('title')}")
    
    async def _check_achievements(self, user_id: str):
        """Check and award achievements"""
        
        if user_id not in self.achievements:
            self.achievements[user_id] = []
        
        earned_achievement_ids = {a.achievement_id for a in self.achievements[user_id]}
        
        for achievement_def in self.achievement_definitions:
            achievement_id = achievement_def['id']
            
            if achievement_id in earned_achievement_ids:
                continue
            
            # Check condition
            try:
                if achievement_def['condition'](user_id):
                    achievement = Achievement(
                        achievement_id=achievement_id,
                        user_id=user_id,
                        title=achievement_def['title'],
                        description=achievement_def['description'],
                        icon=achievement_def['icon'],
                        category=achievement_def['category'],
                        earned_date=datetime.now(),
                        points_earned=achievement_def['points']
                    )
                    
                    self.achievements[user_id].append(achievement)
                    logger.info(f"Achievement earned by {user_id}: {achievement.title}")
                    
            except Exception as e:
                logger.warning(f"Error checking achievement {achievement_id}: {e}")
    
    def _check_streak_achievement(self, user_id: str) -> bool:
        """Check if user has achieved 7-day streak"""
        # Get daily goals for user
        daily_goals = [g for g in self.goals.values() 
                      if g.user_id == user_id and g.frequency == GoalFrequency.DAILY]
        
        if not daily_goals:
            return False
        
        # Check last 7 days
        streak_days = 0
        for days_back in range(7):
            check_date = datetime.now().date() - timedelta(days=days_back)
            
            # Check if any daily goal was completed on this date
            completed_today = False
            
            for goal in daily_goals:
                goal_progress = self.progress.get(goal.goal_id, [])
                day_progress = [p for p in goal_progress if p.date == check_date]
                
                if day_progress and any(p.percentage >= 100 for p in day_progress):
                    completed_today = True
                    break
            
            if completed_today:
                streak_days += 1
            else:
                break
        
        return streak_days >= 7
    
    def _check_step_champion(self, user_id: str) -> bool:
        """Check if user walked 100,000 steps in a month"""
        # Get step goals for user
        step_goals = [g for g in self.goals.values() 
                     if g.user_id == user_id and g.goal_type == GoalType.STEPS]
        
        if not step_goals:
            return False
        
        # Calculate total steps in last 30 days
        month_start = datetime.now().date() - timedelta(days=30)
        total_steps = 0
        
        for goal in step_goals:
            goal_progress = self.progress.get(goal.goal_id, [])
            month_progress = [p for p in goal_progress if p.date >= month_start]
            total_steps += sum(p.value for p in month_progress)
        
        return total_steps >= 100000
    
    async def generate_goal_recommendations(self, user_id: str) -> List[GoalRecommendation]:
        """Generate AI-powered goal recommendations"""
        
        try:
            recommendations = []
            
            # Get user's historical data
            user_goals = [g for g in self.goals.values() if g.user_id == user_id]
            
            # Analyze current fitness level
            fitness_profile = await self._analyze_fitness_profile(user_id)
            
            # Generate recommendations based on profile
            if fitness_profile.get('average_daily_steps', 0) > 0:
                steps_recommendation = await self._recommend_steps_goal(user_id, fitness_profile)
                if steps_recommendation:
                    recommendations.append(steps_recommendation)
            
            if fitness_profile.get('has_weight_data'):
                weight_recommendation = await self._recommend_weight_goal(user_id, fitness_profile)
                if weight_recommendation:
                    recommendations.append(weight_recommendation)
            
            # Store recommendations
            if user_id not in self.recommendations:
                self.recommendations[user_id] = []
            
            self.recommendations[user_id].extend(recommendations)
            
            logger.info(f"Generated {len(recommendations)} goal recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations for user {user_id}: {e}")
            return []
    
    async def _analyze_fitness_profile(self, user_id: str) -> Dict[str, Any]:
        """Analyze user's fitness profile"""
        profile = {}
        
        # Get recent health data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        all_data = []
        devices = await wearable_ingestion.list_devices()
        
        for device_id in devices.keys():
            device_data = await wearable_ingestion.get_device_data(
                device_id, None, start_date
            )
            all_data.extend(device_data)
        
        # Analyze steps
        step_data = [dp for dp in all_data if dp.data_type == DataType.STEPS]
        if step_data:
            daily_steps = {}
            for dp in step_data:
                day = dp.timestamp.date()
                daily_steps[day] = daily_steps.get(day, 0) + dp.value
            
            if daily_steps:
                profile['average_daily_steps'] = np.mean(list(daily_steps.values()))
                profile['max_daily_steps'] = max(daily_steps.values())
                profile['active_days'] = len([v for v in daily_steps.values() if v > 1000])
        
        # Analyze weight data
        weight_data = [dp for dp in all_data if dp.data_type == DataType.WEIGHT]
        profile['has_weight_data'] = len(weight_data) > 0
        
        if weight_data:
            recent_weights = sorted(weight_data, key=lambda x: x.timestamp)
            profile['current_weight'] = recent_weights[-1].value
            
            if len(recent_weights) > 1:
                weight_trend = recent_weights[-1].value - recent_weights[0].value
                profile['weight_trend'] = weight_trend  # Positive = gaining, Negative = losing
        
        # Analyze activity level
        activity_data = [dp for dp in all_data if dp.data_type == DataType.ACTIVITY]
        if activity_data:
            profile['has_activity_data'] = True
        
        return profile
    
    async def _recommend_steps_goal(self, user_id: str, profile: Dict[str, Any]) -> Optional[GoalRecommendation]:
        """Recommend a steps goal based on user profile"""
        
        avg_steps = profile.get('average_daily_steps', 0)
        
        if avg_steps < 1000:
            # Beginner level
            target = 3000
            difficulty = DifficultyLevel.BEGINNER
            rationale = "Start with a basic daily steps goal to build a walking habit"
        elif avg_steps < 5000:
            # Intermediate level
            target = int(avg_steps * 1.25)  # 25% increase
            difficulty = DifficultyLevel.INTERMEDIATE
            rationale = f"Increase your daily steps by 25% from your current average of {int(avg_steps)}"
        elif avg_steps < 10000:
            # Advanced level
            target = 10000
            difficulty = DifficultyLevel.ADVANCED
            rationale = "Reach the recommended 10,000 steps per day"
        else:
            # Expert level
            target = int(avg_steps * 1.15)  # 15% increase
            difficulty = DifficultyLevel.EXPERT
            rationale = f"Challenge yourself with a 15% increase from your current average"
        
        return GoalRecommendation(
            recommendation_id=str(uuid.uuid4()),
            user_id=user_id,
            goal_type=GoalType.STEPS,
            suggested_target=target,
            rationale=rationale,
            confidence=0.8,
            difficulty=difficulty,
            timeline_days=30,
            data_basis=['steps_analysis']
        )
    
    async def _recommend_weight_goal(self, user_id: str, profile: Dict[str, Any]) -> Optional[GoalRecommendation]:
        """Recommend a weight goal based on user profile"""
        
        if not profile.get('has_weight_data'):
            return None
        
        current_weight = profile.get('current_weight', 0)
        weight_trend = profile.get('weight_trend', 0)
        
        if abs(weight_trend) < 0.5:  # Stable weight
            # Maintenance goal
            target = current_weight
            rationale = "Maintain your current weight with consistent healthy habits"
            goal_type = GoalType.WEIGHT_LOSS  # Use as maintenance
        elif weight_trend > 0:  # Gaining weight
            # Weight loss recommendation
            target = current_weight - (current_weight * 0.05)  # 5% reduction
            rationale = "A healthy 5% weight reduction can improve overall health"
            goal_type = GoalType.WEIGHT_LOSS
        else:  # Losing weight
            # Check if loss is too rapid
            if abs(weight_trend) > 2:  # More than 2kg in 30 days
                target = current_weight  # Maintenance
                rationale = "Consider maintaining current weight as your loss rate is quite rapid"
                goal_type = GoalType.WEIGHT_LOSS
            else:
                target = current_weight - 1  # Continue gradual loss
                rationale = "Continue your gradual weight loss journey"
                goal_type = GoalType.WEIGHT_LOSS
        
        return GoalRecommendation(
            recommendation_id=str(uuid.uuid4()),
            user_id=user_id,
            goal_type=goal_type,
            suggested_target=target,
            rationale=rationale,
            confidence=0.7,
            difficulty=DifficultyLevel.INTERMEDIATE,
            timeline_days=90,
            data_basis=['weight_analysis']
        )
    
    async def generate_progress_insights(self, goal_id: str) -> List[ProgressInsight]:
        """Generate insights about goal progress"""
        
        if goal_id not in self.goals:
            return []
        
        goal = self.goals[goal_id]
        progress_history = self.progress.get(goal_id, [])
        
        if len(progress_history) < 2:
            return []
        
        insights = []
        
        try:
            # Trend analysis
            trend_insight = await self._analyze_progress_trend(goal, progress_history)
            if trend_insight:
                insights.append(trend_insight)
            
            # Consistency analysis
            consistency_insight = await self._analyze_consistency(goal, progress_history)
            if consistency_insight:
                insights.append(consistency_insight)
            
            # Completion prediction
            prediction_insight = await self._analyze_completion_prediction(goal, progress_history)
            if prediction_insight:
                insights.append(prediction_insight)
            
            # Store insights
            if goal.user_id not in self.insights:
                self.insights[goal.user_id] = []
            
            self.insights[goal.user_id].extend(insights)
            
        except Exception as e:
            logger.error(f"Failed to generate insights for goal {goal_id}: {e}")
        
        return insights
    
    async def _analyze_progress_trend(self, goal: FitnessGoal, progress_history: List[GoalProgress]) -> Optional[ProgressInsight]:
        """Analyze progress trend"""
        
        if len(progress_history) < 5:
            return None
        
        recent_progress = progress_history[-7:]  # Last week
        values = [p.percentage for p in recent_progress]
        
        # Calculate trend
        x = np.arange(len(values))
        slope, _ = np.polyfit(x, values, 1)
        
        if slope > 5:  # Improving trend
            return ProgressInsight(
                insight_id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                user_id=goal.user_id,
                insight_type="trend",
                title="Great Progress Trend",
                description=f"Your progress is accelerating! You've improved by {slope:.1f}% per day recently.",
                severity="info",
                recommendations=["Keep up the excellent work!", "Consider setting a more challenging goal next time"],
                data_points={'slope': slope, 'trend_period': 7}
            )
        elif slope < -5:  # Declining trend
            return ProgressInsight(
                insight_id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                user_id=goal.user_id,
                insight_type="trend",
                title="Progress Declining",
                description=f"Your progress has been declining by {abs(slope):.1f}% per day recently.",
                severity="warning",
                recommendations=[
                    "Review what might be affecting your progress",
                    "Consider adjusting your approach or goal timeline",
                    "Don't get discouraged - setbacks are normal"
                ],
                data_points={'slope': slope, 'trend_period': 7}
            )
        
        return None
    
    async def _analyze_consistency(self, goal: FitnessGoal, progress_history: List[GoalProgress]) -> Optional[ProgressInsight]:
        """Analyze consistency of progress"""
        
        if len(progress_history) < 7:
            return None
        
        # Check for gaps in progress tracking
        recent_progress = progress_history[-14:]  # Last 2 weeks
        dates = [p.date for p in recent_progress]
        
        # Count consecutive days with progress
        consecutive_days = 1
        max_consecutive = 1
        
        sorted_dates = sorted(dates)
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                consecutive_days += 1
                max_consecutive = max(max_consecutive, consecutive_days)
            else:
                consecutive_days = 1
        
        if max_consecutive >= 7:
            return ProgressInsight(
                insight_id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                user_id=goal.user_id,
                insight_type="consistency",
                title="Excellent Consistency",
                description=f"You've been consistent for {max_consecutive} days in a row!",
                severity="info",
                recommendations=["Your consistency is key to success", "Keep building on this strong foundation"],
                data_points={'max_consecutive_days': max_consecutive}
            )
        elif max_consecutive < 3:
            return ProgressInsight(
                insight_id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                user_id=goal.user_id,
                insight_type="consistency",
                title="Consistency Opportunity",
                description="Building more consistent daily habits could accelerate your progress.",
                severity="warning",
                recommendations=[
                    "Try to engage with your goal daily, even in small ways",
                    "Set up reminders to help build consistency",
                    "Focus on small, achievable daily actions"
                ],
                data_points={'max_consecutive_days': max_consecutive}
            )
        
        return None
    
    async def _analyze_completion_prediction(self, goal: FitnessGoal, progress_history: List[GoalProgress]) -> Optional[ProgressInsight]:
        """Analyze goal completion prediction"""
        
        if not goal.target_date or len(progress_history) < 5:
            return None
        
        # Use calculator to predict completion
        if goal.goal_type in self.calculators:
            calculator = self.calculators[goal.goal_type]
            predicted_completion = await calculator.predict_completion(goal, progress_history)
            
            if predicted_completion:
                days_until_target = (goal.target_date - datetime.now()).days
                days_until_prediction = (predicted_completion - datetime.now()).days
                
                if days_until_prediction <= days_until_target * 0.8:  # Will finish early
                    return ProgressInsight(
                        insight_id=str(uuid.uuid4()),
                        goal_id=goal.goal_id,
                        user_id=goal.user_id,
                        insight_type="prediction",
                        title="Early Completion Predicted",
                        description=f"At your current pace, you'll complete this goal {days_until_target - days_until_prediction} days early!",
                        severity="info",
                        recommendations=[
                            "Consider setting a more ambitious target",
                            "You're doing great - keep up the momentum!"
                        ],
                        data_points={
                            'predicted_completion': predicted_completion.isoformat(),
                            'days_early': days_until_target - days_until_prediction
                        }
                    )
                elif days_until_prediction > days_until_target * 1.2:  # Will finish late
                    return ProgressInsight(
                        insight_id=str(uuid.uuid4()),
                        goal_id=goal.goal_id,
                        user_id=goal.user_id,
                        insight_type="prediction",
                        title="Goal At Risk",
                        description=f"At your current pace, you might finish {days_until_prediction - days_until_target} days after your target date.",
                        severity="alert",
                        recommendations=[
                            "Consider increasing your daily effort",
                            "Review what's preventing faster progress",
                            "It might be worth adjusting your target date"
                        ],
                        data_points={
                            'predicted_completion': predicted_completion.isoformat(),
                            'days_late': days_until_prediction - days_until_target
                        }
                    )
        
        return None
    
    async def _progress_tracker(self):
        """Background task to track goal progress"""
        
        while True:
            try:
                # Update progress for all active goals
                active_goals = [g for g in self.goals.values() if g.status == GoalStatus.ACTIVE]
                
                for goal in active_goals:
                    await self.update_goal_progress(goal.goal_id)
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Progress tracker error: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error
    
    async def _insight_generator(self):
        """Background task to generate insights"""
        
        while True:
            try:
                # Generate insights for goals with sufficient progress data
                for goal_id, progress_list in self.progress.items():
                    if len(progress_list) >= 5:  # Minimum data for insights
                        await self.generate_progress_insights(goal_id)
                
                # Sleep for 6 hours
                await asyncio.sleep(21600)
                
            except Exception as e:
                logger.error(f"Insight generator error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def get_user_goals(self, user_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get all goals for a user"""
        
        user_goals = [g for g in self.goals.values() if g.user_id == user_id]
        
        if not include_inactive:
            user_goals = [g for g in user_goals if g.status == GoalStatus.ACTIVE]
        
        goals_with_progress = []
        
        for goal in user_goals:
            latest_progress = None
            progress_list = self.progress.get(goal.goal_id, [])
            
            if progress_list:
                latest_progress = max(progress_list, key=lambda x: x.date)
            
            goals_with_progress.append({
                'goal': goal.__dict__,
                'latest_progress': latest_progress.__dict__ if latest_progress else None,
                'total_progress_entries': len(progress_list)
            })
        
        return sorted(goals_with_progress, key=lambda x: x['goal']['priority'], reverse=True)
    
    async def get_user_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all achievements for a user"""
        
        user_achievements = self.achievements.get(user_id, [])
        
        return [a.__dict__ for a in sorted(user_achievements, key=lambda x: x.earned_date, reverse=True)]
    
    async def get_goal_insights(self, goal_id: str) -> List[Dict[str, Any]]:
        """Get insights for a specific goal"""
        
        if goal_id not in self.goals:
            return []
        
        goal = self.goals[goal_id]
        user_insights = self.insights.get(goal.user_id, [])
        goal_insights = [i for i in user_insights if i.goal_id == goal_id]
        
        return [i.__dict__ for i in sorted(goal_insights, key=lambda x: x.created_at, reverse=True)]
    
    async def get_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive dashboard data for a user"""
        
        return {
            'active_goals': await self.get_user_goals(user_id),
            'recent_achievements': (await self.get_user_achievements(user_id))[:5],
            'recommendations': [r.__dict__ for r in self.recommendations.get(user_id, [])][:3],
            'insights': [i.__dict__ for i in self.insights.get(user_id, [])[:10]],
            'statistics': await self._get_user_statistics(user_id)
        }
    
    async def _get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        
        user_goals = [g for g in self.goals.values() if g.user_id == user_id]
        
        return {
            'total_goals': len(user_goals),
            'active_goals': len([g for g in user_goals if g.status == GoalStatus.ACTIVE]),
            'completed_goals': len([g for g in user_goals if g.status == GoalStatus.COMPLETED]),
            'total_achievements': len(self.achievements.get(user_id, [])),
            'total_points': sum(a.points_earned for a in self.achievements.get(user_id, [])),
            'completion_rate': len([g for g in user_goals if g.status == GoalStatus.COMPLETED]) / len(user_goals) * 100 if user_goals else 0
        }

# Global singleton instance
fitness_goal_tracker = FitnessGoalTracker()