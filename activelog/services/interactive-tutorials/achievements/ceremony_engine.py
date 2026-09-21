"""
Achievement Ceremony System for Interactive Tutorials

This module provides comprehensive achievement ceremony management, including
badge systems, milestone celebrations, ceremony orchestration, and personalized
recognition experiences for learning accomplishments.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
import sqlite3
from pathlib import Path
import random


class AchievementType(Enum):
    """Types of achievements that can be earned"""
    SKILL_MASTERY = "skill_mastery"
    TIME_MILESTONE = "time_milestone"
    CONSISTENCY = "consistency"
    EXPLORATION = "exploration"
    COLLABORATION = "collaboration"
    INNOVATION = "innovation"
    PERSEVERANCE = "perseverance"
    TEACHING = "teaching"
    LEADERSHIP = "leadership"
    SPECIAL_EVENT = "special_event"


class AchievementRarity(Enum):
    """Rarity levels for achievements"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class CeremonyType(Enum):
    """Types of achievement ceremonies"""
    INSTANT_BADGE = "instant_badge"
    MINI_CEREMONY = "mini_ceremony"
    FULL_CEREMONY = "full_ceremony"
    MILESTONE_CELEBRATION = "milestone_celebration"
    SPECIAL_EVENT = "special_event"
    PRIVATE_MOMENT = "private_moment"
    PUBLIC_RECOGNITION = "public_recognition"


class CeremonyStyle(Enum):
    """Visual styles for ceremonies"""
    FIREWORKS = "fireworks"
    CONFETTI = "confetti"
    GOLDEN_LIGHT = "golden_light"
    PARTICLE_BURST = "particle_burst"
    ROYAL_FANFARE = "royal_fanfare"
    NATURE_BLOOM = "nature_bloom"
    COSMIC_EXPLOSION = "cosmic_explosion"
    MINIMALIST = "minimalist"


@dataclass
class Achievement:
    """Individual achievement definition"""
    achievement_id: str
    name: str
    description: str
    achievement_type: AchievementType
    rarity: AchievementRarity
    criteria: Dict[str, Any]
    points_value: int
    icon: str
    badge_design: Dict[str, Any] = field(default_factory=dict)
    unlock_message: str = ""
    category_tags: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    hidden: bool = False
    ceremony_config: Optional[Dict[str, Any]] = None


@dataclass
class UserAchievement:
    """User's earned achievement record"""
    user_id: str
    achievement_id: str
    earned_at: datetime
    progress_snapshot: Dict[str, Any] = field(default_factory=dict)
    ceremony_shown: bool = False
    shared: bool = False
    notes: str = ""


@dataclass
class CeremonyElement:
    """Individual element in a ceremony"""
    element_type: str  # animation, sound, text, image, effect
    content: Dict[str, Any]
    timing: float  # When to trigger (seconds from start)
    duration: float = 3.0
    position: Optional[Dict[str, float]] = None
    priority: int = 0


@dataclass
class CeremonyScript:
    """Complete ceremony orchestration"""
    ceremony_id: str
    achievement: Achievement
    ceremony_type: CeremonyType
    ceremony_style: CeremonyStyle
    total_duration: float
    elements: List[CeremonyElement]
    background_music: Optional[str] = None
    personalization: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserCeremonyPreferences:
    """User's ceremony preferences"""
    user_id: str
    preferred_styles: List[CeremonyStyle] = field(default_factory=list)
    ceremony_duration_preference: str = "normal"  # short, normal, long
    sound_enabled: bool = True
    animation_intensity: str = "normal"  # low, normal, high
    auto_share_achievements: bool = False
    private_celebrations_only: bool = False
    favorite_themes: List[str] = field(default_factory=list)


class AchievementTracker:
    """Tracks and evaluates achievement progress"""
    
    def __init__(self, db_path: str = "achievements.db"):
        self.db_path = Path(db_path)
        self.achievements: Dict[str, Achievement] = {}
        self.achievement_checkers: Dict[str, Callable] = {}
        self.init_database()
        self.create_default_achievements()
    
    def init_database(self):
        """Initialize achievement tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id TEXT,
                    achievement_id TEXT,
                    earned_at DATETIME,
                    progress_snapshot TEXT,
                    ceremony_shown BOOLEAN DEFAULT 0,
                    shared BOOLEAN DEFAULT 0,
                    notes TEXT,
                    PRIMARY KEY (user_id, achievement_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS achievement_progress (
                    user_id TEXT,
                    achievement_id TEXT,
                    progress_data TEXT,
                    last_checked DATETIME,
                    PRIMARY KEY (user_id, achievement_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ceremony_preferences (
                    user_id TEXT PRIMARY KEY,
                    preferred_styles TEXT,
                    duration_preference TEXT,
                    sound_enabled BOOLEAN,
                    animation_intensity TEXT,
                    auto_share BOOLEAN,
                    private_only BOOLEAN,
                    favorite_themes TEXT
                )
            """)
    
    def create_default_achievements(self):
        """Create the default set of achievements"""
        # Skill mastery achievements
        self.add_achievement(Achievement(
            "first_skill", "First Steps", "Complete your first skill",
            AchievementType.SKILL_MASTERY, AchievementRarity.COMMON,
            {"skills_completed": 1}, 100, "trophy",
            unlock_message="Congratulations on completing your first skill! The journey begins!"
        ))
        
        self.add_achievement(Achievement(
            "skill_collector", "Skill Collector", "Complete 10 different skills",
            AchievementType.SKILL_MASTERY, AchievementRarity.UNCOMMON,
            {"skills_completed": 10}, 500, "collection",
            unlock_message="You're building an impressive skill collection!"
        ))
        
        self.add_achievement(Achievement(
            "master_learner", "Master Learner", "Complete 50 skills across all categories",
            AchievementType.SKILL_MASTERY, AchievementRarity.EPIC,
            {"skills_completed": 50, "categories_touched": 5}, 2500, "crown",
            unlock_message="You are truly a master of learning! Exceptional dedication!"
        ))
        
        # Time-based achievements
        self.add_achievement(Achievement(
            "dedicated_hour", "Dedicated Hour", "Spend 1 hour learning",
            AchievementType.TIME_MILESTONE, AchievementRarity.COMMON,
            {"total_minutes": 60}, 200, "clock",
            unlock_message="An hour well spent! Your dedication shows."
        ))
        
        self.add_achievement(Achievement(
            "weekend_warrior", "Weekend Warrior", "Learn for 5 hours over a weekend",
            AchievementType.TIME_MILESTONE, AchievementRarity.RARE,
            {"weekend_hours": 5}, 1000, "weekend",
            unlock_message="Your weekend dedication is inspiring!"
        ))
        
        # Consistency achievements
        self.add_achievement(Achievement(
            "daily_learner", "Daily Learner", "Learn something every day for a week",
            AchievementType.CONSISTENCY, AchievementRarity.UNCOMMON,
            {"consecutive_days": 7}, 750, "calendar",
            unlock_message="Consistency is the key to mastery! Keep it up!"
        ))
        
        self.add_achievement(Achievement(
            "unstoppable", "Unstoppable", "Learn something every day for 30 days",
            AchievementType.CONSISTENCY, AchievementRarity.LEGENDARY,
            {"consecutive_days": 30}, 5000, "fire",
            unlock_message="You are absolutely unstoppable! This is legendary dedication!"
        ))
        
        # Special achievements
        self.add_achievement(Achievement(
            "night_owl", "Night Owl", "Complete learning sessions after 10 PM",
            AchievementType.SPECIAL_EVENT, AchievementRarity.RARE,
            {"late_sessions": 5}, 800, "moon",
            unlock_message="The night is your time to shine!"
        ))
        
        self.add_achievement(Achievement(
            "early_bird", "Early Bird", "Complete learning sessions before 6 AM",
            AchievementType.SPECIAL_EVENT, AchievementRarity.RARE,
            {"early_sessions": 5}, 800, "sunrise",
            unlock_message="The early bird catches the knowledge!"
        ))
        
        self.add_achievement(Achievement(
            "perfectionist", "Perfectionist", "Complete 10 skills with 100% accuracy",
            AchievementType.SKILL_MASTERY, AchievementRarity.EPIC,
            {"perfect_skills": 10}, 3000, "diamond",
            unlock_message="Perfection is your standard! Absolutely remarkable!"
        ))
    
    def add_achievement(self, achievement: Achievement):
        """Add an achievement to the system"""
        self.achievements[achievement.achievement_id] = achievement
    
    def register_achievement_checker(self, achievement_id: str, checker_func: Callable):
        """Register a function to check achievement progress"""
        self.achievement_checkers[achievement_id] = checker_func
    
    def check_achievements(self, user_id: str, user_data: Dict[str, Any]) -> List[str]:
        """Check if user has earned any new achievements"""
        newly_earned = []
        
        # Get user's existing achievements
        existing_achievements = set(self.get_user_achievements(user_id))
        
        for achievement_id, achievement in self.achievements.items():
            if achievement_id in existing_achievements:
                continue
            
            # Check if prerequisites are met
            if achievement.prerequisites:
                if not all(prereq in existing_achievements for prereq in achievement.prerequisites):
                    continue
            
            # Use custom checker if available
            if achievement_id in self.achievement_checkers:
                if self.achievement_checkers[achievement_id](user_data):
                    self.award_achievement(user_id, achievement_id, user_data)
                    newly_earned.append(achievement_id)
            else:
                # Use default criteria checking
                if self._check_default_criteria(achievement.criteria, user_data):
                    self.award_achievement(user_id, achievement_id, user_data)
                    newly_earned.append(achievement_id)
        
        return newly_earned
    
    def _check_default_criteria(self, criteria: Dict[str, Any], user_data: Dict[str, Any]) -> bool:
        """Check default achievement criteria against user data"""
        for key, required_value in criteria.items():
            user_value = user_data.get(key, 0)
            
            if isinstance(required_value, (int, float)):
                if user_value < required_value:
                    return False
            elif isinstance(required_value, str):
                if user_data.get(key, "") != required_value:
                    return False
            elif isinstance(required_value, list):
                if not all(item in user_data.get(key, []) for item in required_value):
                    return False
        
        return True
    
    def award_achievement(self, user_id: str, achievement_id: str, progress_snapshot: Dict[str, Any]):
        """Award an achievement to a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO user_achievements
                (user_id, achievement_id, earned_at, progress_snapshot)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                achievement_id,
                datetime.now().isoformat(),
                json.dumps(progress_snapshot)
            ))
    
    def get_user_achievements(self, user_id: str) -> List[UserAchievement]:
        """Get all achievements earned by a user"""
        achievements = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT achievement_id, earned_at, progress_snapshot, ceremony_shown, shared, notes
                FROM user_achievements WHERE user_id = ?
                ORDER BY earned_at DESC
            """, (user_id,))
            
            for row in cursor.fetchall():
                achievement_id, earned_at, progress_snapshot, ceremony_shown, shared, notes = row
                achievements.append(UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement_id,
                    earned_at=datetime.fromisoformat(earned_at),
                    progress_snapshot=json.loads(progress_snapshot) if progress_snapshot else {},
                    ceremony_shown=bool(ceremony_shown),
                    shared=bool(shared),
                    notes=notes or ""
                ))
        
        return achievements
    
    def get_pending_ceremonies(self, user_id: str) -> List[UserAchievement]:
        """Get achievements that haven't had their ceremony shown yet"""
        achievements = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT achievement_id, earned_at, progress_snapshot, ceremony_shown, shared, notes
                FROM user_achievements 
                WHERE user_id = ? AND ceremony_shown = 0
                ORDER BY earned_at ASC
            """, (user_id,))
            
            for row in cursor.fetchall():
                achievement_id, earned_at, progress_snapshot, ceremony_shown, shared, notes = row
                achievements.append(UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement_id,
                    earned_at=datetime.fromisoformat(earned_at),
                    progress_snapshot=json.loads(progress_snapshot) if progress_snapshot else {},
                    ceremony_shown=bool(ceremony_shown),
                    shared=bool(shared),
                    notes=notes or ""
                ))
        
        return achievements
    
    def mark_ceremony_shown(self, user_id: str, achievement_id: str):
        """Mark that the ceremony for an achievement has been shown"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE user_achievements 
                SET ceremony_shown = 1
                WHERE user_id = ? AND achievement_id = ?
            """, (user_id, achievement_id))


class CeremonyOrchestrator:
    """Orchestrates achievement ceremonies with personalization"""
    
    def __init__(self, achievement_tracker: AchievementTracker):
        self.tracker = achievement_tracker
        self.ceremony_templates: Dict[CeremonyType, Dict[CeremonyStyle, List[CeremonyElement]]] = {}
        self.create_ceremony_templates()
    
    def create_ceremony_templates(self):
        """Create ceremony templates for different types and styles"""
        # Instant badge templates
        self.ceremony_templates[CeremonyType.INSTANT_BADGE] = {
            CeremonyStyle.MINIMALIST: [
                CeremonyElement("badge_appear", {"animation": "fadeIn", "scale": 1.2}, 0.0, 1.0),
                CeremonyElement("text_display", {"message": "Achievement Unlocked!"}, 0.5, 2.0),
                CeremonyElement("sound", {"effect": "gentle_chime"}, 0.0, 0.5)
            ],
            CeremonyStyle.CONFETTI: [
                CeremonyElement("confetti_burst", {"particles": 50, "colors": ["gold", "silver"]}, 0.0, 2.0),
                CeremonyElement("badge_appear", {"animation": "bounceIn", "glow": True}, 0.2, 1.5),
                CeremonyElement("text_display", {"message": "Achievement Unlocked!", "style": "celebration"}, 0.5, 2.0),
                CeremonyElement("sound", {"effect": "celebration_chime"}, 0.0, 1.0)
            ]
        }
        
        # Full ceremony templates
        self.ceremony_templates[CeremonyType.FULL_CEREMONY] = {
            CeremonyStyle.ROYAL_FANFARE: [
                CeremonyElement("screen_darken", {"opacity": 0.8}, 0.0, 0.5),
                CeremonyElement("golden_light", {"intensity": "high", "spread": "wide"}, 0.5, 3.0),
                CeremonyElement("fanfare_sound", {"style": "royal"}, 0.5, 4.0),
                CeremonyElement("badge_ceremony", {"animation": "royal_descent", "glow": True}, 1.0, 2.0),
                CeremonyElement("achievement_title", {"style": "royal_proclamation"}, 1.5, 2.5),
                CeremonyElement("achievement_description", {"style": "elegant_scroll"}, 2.0, 3.0),
                CeremonyElement("points_award", {"animation": "counting_up", "style": "golden"}, 3.0, 2.0),
                CeremonyElement("spotlight_fade", {}, 4.5, 1.0)
            ],
            CeremonyStyle.FIREWORKS: [
                CeremonyElement("sky_background", {"gradient": "night_sky"}, 0.0, 6.0),
                CeremonyElement("firework_launch", {"count": 3, "colors": ["red", "blue", "gold"]}, 1.0, 2.0),
                CeremonyElement("badge_firework", {"explosion_style": "spectacular"}, 1.5, 2.0),
                CeremonyElement("firework_finale", {"count": 5, "intensity": "high"}, 3.0, 2.0),
                CeremonyElement("achievement_display", {"style": "firework_text"}, 2.0, 3.0),
                CeremonyElement("sound", {"effect": "fireworks_spectacular"}, 1.0, 4.0)
            ]
        }
        
        # Special milestone ceremonies
        self.ceremony_templates[CeremonyType.MILESTONE_CELEBRATION] = {
            CeremonyStyle.COSMIC_EXPLOSION: [
                CeremonyElement("space_background", {"stars": True, "nebula": True}, 0.0, 8.0),
                CeremonyElement("cosmic_buildup", {"energy_gathering": True}, 0.0, 2.0),
                CeremonyElement("star_formation", {"achievement_constellation": True}, 2.0, 3.0),
                CeremonyElement("cosmic_explosion", {"particle_count": 1000}, 3.0, 2.0),
                CeremonyElement("achievement_emerge", {"from_cosmos": True}, 3.5, 2.5),
                CeremonyElement("milestone_proclamation", {"style": "cosmic_text"}, 4.0, 3.0),
                CeremonyElement("cosmic_music", {"style": "epic_orchestral"}, 0.0, 8.0)
            ]
        }
    
    def create_personalized_ceremony(self, user_id: str, achievement: Achievement,
                                   preferences: UserCeremonyPreferences) -> CeremonyScript:
        """Create a personalized ceremony for a specific achievement"""
        # Determine ceremony type based on achievement rarity
        ceremony_type = self._determine_ceremony_type(achievement, preferences)
        
        # Choose ceremony style based on preferences and achievement
        ceremony_style = self._choose_ceremony_style(achievement, preferences)
        
        # Get base template
        base_elements = self.ceremony_templates.get(ceremony_type, {}).get(
            ceremony_style, self.ceremony_templates[CeremonyType.INSTANT_BADGE][CeremonyStyle.MINIMALIST]
        )
        
        # Personalize elements
        personalized_elements = []
        for element in base_elements:
            personalized_element = self._personalize_element(element, user_id, achievement, preferences)
            personalized_elements.append(personalized_element)
        
        # Add achievement-specific customizations
        customized_elements = self._add_achievement_customizations(
            personalized_elements, achievement, preferences
        )
        
        # Calculate total duration
        total_duration = max(elem.timing + elem.duration for elem in customized_elements)
        
        # Adjust duration based on preferences
        if preferences.ceremony_duration_preference == "short":
            total_duration *= 0.7
            customized_elements = self._compress_ceremony_timing(customized_elements, 0.7)
        elif preferences.ceremony_duration_preference == "long":
            total_duration *= 1.3
            customized_elements = self._expand_ceremony_timing(customized_elements, 1.3)
        
        return CeremonyScript(
            ceremony_id=f"{user_id}_{achievement.achievement_id}_{int(datetime.now().timestamp())}",
            achievement=achievement,
            ceremony_type=ceremony_type,
            ceremony_style=ceremony_style,
            total_duration=total_duration,
            elements=customized_elements,
            background_music=self._select_background_music(achievement, ceremony_style),
            personalization={
                "user_id": user_id,
                "achievement_rarity": achievement.rarity.value,
                "user_preferences": preferences.__dict__
            }
        )
    
    def _determine_ceremony_type(self, achievement: Achievement, 
                               preferences: UserCeremonyPreferences) -> CeremonyType:
        """Determine the type of ceremony based on achievement and preferences"""
        if preferences.private_celebrations_only:
            return CeremonyType.PRIVATE_MOMENT
        
        rarity_to_ceremony = {
            AchievementRarity.COMMON: CeremonyType.INSTANT_BADGE,
            AchievementRarity.UNCOMMON: CeremonyType.MINI_CEREMONY,
            AchievementRarity.RARE: CeremonyType.FULL_CEREMONY,
            AchievementRarity.EPIC: CeremonyType.MILESTONE_CELEBRATION,
            AchievementRarity.LEGENDARY: CeremonyType.MILESTONE_CELEBRATION,
            AchievementRarity.MYTHIC: CeremonyType.SPECIAL_EVENT
        }
        
        return rarity_to_ceremony.get(achievement.rarity, CeremonyType.INSTANT_BADGE)
    
    def _choose_ceremony_style(self, achievement: Achievement, 
                             preferences: UserCeremonyPreferences) -> CeremonyStyle:
        """Choose ceremony style based on preferences and achievement"""
        if preferences.preferred_styles:
            # Use user's preferred style
            return random.choice(preferences.preferred_styles)
        
        # Default style based on achievement type
        type_to_style = {
            AchievementType.SKILL_MASTERY: CeremonyStyle.GOLDEN_LIGHT,
            AchievementType.TIME_MILESTONE: CeremonyStyle.FIREWORKS,
            AchievementType.CONSISTENCY: CeremonyStyle.PARTICLE_BURST,
            AchievementType.SPECIAL_EVENT: CeremonyStyle.COSMIC_EXPLOSION
        }
        
        return type_to_style.get(achievement.achievement_type, CeremonyStyle.CONFETTI)
    
    def _personalize_element(self, element: CeremonyElement, user_id: str,
                           achievement: Achievement, preferences: UserCeremonyPreferences) -> CeremonyElement:
        """Personalize a ceremony element for the user"""
        personalized_content = element.content.copy()
        
        # Add user-specific personalizations
        if element.element_type == "text_display":
            if "message" in personalized_content:
                personalized_content["message"] = personalized_content["message"].replace(
                    "Achievement Unlocked!", f"🎉 {achievement.name} Unlocked!"
                )
        
        # Adjust animation intensity
        if "animation" in personalized_content and preferences.animation_intensity == "low":
            personalized_content["intensity"] = "subtle"
        elif "animation" in personalized_content and preferences.animation_intensity == "high":
            personalized_content["intensity"] = "dramatic"
        
        # Disable sound if requested
        if element.element_type == "sound" and not preferences.sound_enabled:
            return CeremonyElement("silent", {}, element.timing, 0.0)
        
        return CeremonyElement(
            element.element_type,
            personalized_content,
            element.timing,
            element.duration,
            element.position,
            element.priority
        )
    
    def _add_achievement_customizations(self, elements: List[CeremonyElement],
                                      achievement: Achievement, 
                                      preferences: UserCeremonyPreferences) -> List[CeremonyElement]:
        """Add achievement-specific customizations"""
        customized_elements = elements.copy()
        
        # Add achievement-specific messages
        if achievement.unlock_message:
            message_element = CeremonyElement(
                "achievement_message",
                {
                    "message": achievement.unlock_message,
                    "style": "personal_message",
                    "icon": achievement.icon
                },
                max(elem.timing for elem in elements) * 0.6,
                3.0
            )
            customized_elements.append(message_element)
        
        # Add points display
        points_element = CeremonyElement(
            "points_display",
            {
                "points": achievement.points_value,
                "animation": "count_up",
                "style": f"rarity_{achievement.rarity.value}"
            },
            max(elem.timing for elem in elements) * 0.8,
            2.0
        )
        customized_elements.append(points_element)
        
        # Add rarity indicator
        rarity_element = CeremonyElement(
            "rarity_indicator",
            {
                "rarity": achievement.rarity.value,
                "color": self._get_rarity_color(achievement.rarity),
                "effect": f"rarity_{achievement.rarity.value}"
            },
            0.0,
            max(elem.timing + elem.duration for elem in elements)
        )
        customized_elements.append(rarity_element)
        
        return customized_elements
    
    def _get_rarity_color(self, rarity: AchievementRarity) -> str:
        """Get color associated with achievement rarity"""
        colors = {
            AchievementRarity.COMMON: "#95a5a6",
            AchievementRarity.UNCOMMON: "#27ae60",
            AchievementRarity.RARE: "#3498db",
            AchievementRarity.EPIC: "#9b59b6",
            AchievementRarity.LEGENDARY: "#f1c40f",
            AchievementRarity.MYTHIC: "#e74c3c"
        }
        return colors.get(rarity, "#95a5a6")
    
    def _compress_ceremony_timing(self, elements: List[CeremonyElement], factor: float) -> List[CeremonyElement]:
        """Compress ceremony timing by a factor"""
        compressed = []
        for element in elements:
            compressed.append(CeremonyElement(
                element.element_type,
                element.content,
                element.timing * factor,
                element.duration * factor,
                element.position,
                element.priority
            ))
        return compressed
    
    def _expand_ceremony_timing(self, elements: List[CeremonyElement], factor: float) -> List[CeremonyElement]:
        """Expand ceremony timing by a factor"""
        expanded = []
        for element in elements:
            expanded.append(CeremonyElement(
                element.element_type,
                element.content,
                element.timing * factor,
                element.duration * factor,
                element.position,
                element.priority
            ))
        return expanded
    
    def _select_background_music(self, achievement: Achievement, style: CeremonyStyle) -> Optional[str]:
        """Select appropriate background music for the ceremony"""
        music_map = {
            CeremonyStyle.ROYAL_FANFARE: "royal_fanfare.mp3",
            CeremonyStyle.FIREWORKS: "celebration_orchestral.mp3",
            CeremonyStyle.COSMIC_EXPLOSION: "epic_space_theme.mp3",
            CeremonyStyle.GOLDEN_LIGHT: "inspiring_achievement.mp3",
            CeremonyStyle.NATURE_BLOOM: "peaceful_accomplishment.mp3"
        }
        return music_map.get(style)


class CeremonyEngine:
    """Main achievement ceremony engine"""
    
    def __init__(self, db_path: str = "achievements.db"):
        self.tracker = AchievementTracker(db_path)
        self.orchestrator = CeremonyOrchestrator(self.tracker)
        self.active_ceremonies: Dict[str, CeremonyScript] = {}
    
    def check_and_trigger_ceremonies(self, user_id: str, user_data: Dict[str, Any]) -> List[CeremonyScript]:
        """Check for new achievements and create ceremonies"""
        # Check for new achievements
        newly_earned = self.tracker.check_achievements(user_id, user_data)
        
        ceremonies = []
        if newly_earned:
            # Get user preferences
            preferences = self.get_user_preferences(user_id)
            
            # Create ceremonies for new achievements
            for achievement_id in newly_earned:
                achievement = self.tracker.achievements[achievement_id]
                ceremony = self.orchestrator.create_personalized_ceremony(
                    user_id, achievement, preferences
                )
                ceremonies.append(ceremony)
                self.active_ceremonies[ceremony.ceremony_id] = ceremony
        
        return ceremonies
    
    def get_pending_ceremonies(self, user_id: str) -> List[CeremonyScript]:
        """Get pending ceremonies that haven't been shown"""
        pending_achievements = self.tracker.get_pending_ceremonies(user_id)
        preferences = self.get_user_preferences(user_id)
        
        ceremonies = []
        for user_achievement in pending_achievements:
            achievement = self.tracker.achievements[user_achievement.achievement_id]
            ceremony = self.orchestrator.create_personalized_ceremony(
                user_id, achievement, preferences
            )
            ceremonies.append(ceremony)
        
        return ceremonies
    
    def mark_ceremony_complete(self, ceremony_id: str):
        """Mark a ceremony as complete"""
        if ceremony_id in self.active_ceremonies:
            ceremony = self.active_ceremonies[ceremony_id]
            self.tracker.mark_ceremony_shown(
                ceremony.personalization["user_id"], 
                ceremony.achievement.achievement_id
            )
            del self.active_ceremonies[ceremony_id]
    
    def get_user_preferences(self, user_id: str) -> UserCeremonyPreferences:
        """Get user's ceremony preferences"""
        with sqlite3.connect(self.tracker.db_path) as conn:
            cursor = conn.execute("""
                SELECT preferred_styles, duration_preference, sound_enabled,
                       animation_intensity, auto_share, private_only, favorite_themes
                FROM ceremony_preferences WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                preferred_styles_json, duration_pref, sound_enabled, animation_intensity, auto_share, private_only, favorite_themes_json = row
                
                preferred_styles = [CeremonyStyle(style) for style in json.loads(preferred_styles_json)] if preferred_styles_json else []
                favorite_themes = json.loads(favorite_themes_json) if favorite_themes_json else []
                
                return UserCeremonyPreferences(
                    user_id=user_id,
                    preferred_styles=preferred_styles,
                    ceremony_duration_preference=duration_pref or "normal",
                    sound_enabled=bool(sound_enabled) if sound_enabled is not None else True,
                    animation_intensity=animation_intensity or "normal",
                    auto_share_achievements=bool(auto_share) if auto_share is not None else False,
                    private_celebrations_only=bool(private_only) if private_only is not None else False,
                    favorite_themes=favorite_themes
                )
        
        return UserCeremonyPreferences(user_id=user_id)  # Default preferences
    
    def update_user_preferences(self, preferences: UserCeremonyPreferences):
        """Update user's ceremony preferences"""
        with sqlite3.connect(self.tracker.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ceremony_preferences
                (user_id, preferred_styles, duration_preference, sound_enabled,
                 animation_intensity, auto_share, private_only, favorite_themes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                preferences.user_id,
                json.dumps([style.value for style in preferences.preferred_styles]),
                preferences.ceremony_duration_preference,
                preferences.sound_enabled,
                preferences.animation_intensity,
                preferences.auto_share_achievements,
                preferences.private_celebrations_only,
                json.dumps(preferences.favorite_themes)
            ))
    
    def get_achievement_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get achievement statistics for a user"""
        user_achievements = self.tracker.get_user_achievements(user_id)
        
        # Calculate statistics
        total_achievements = len(user_achievements)
        total_points = sum(self.tracker.achievements[ua.achievement_id].points_value 
                          for ua in user_achievements 
                          if ua.achievement_id in self.tracker.achievements)
        
        # Group by rarity
        rarity_counts = {}
        for ua in user_achievements:
            if ua.achievement_id in self.tracker.achievements:
                rarity = self.tracker.achievements[ua.achievement_id].rarity
                rarity_counts[rarity.value] = rarity_counts.get(rarity.value, 0) + 1
        
        # Recent achievements
        recent_achievements = sorted(user_achievements, key=lambda x: x.earned_at, reverse=True)[:5]
        
        return {
            "user_id": user_id,
            "total_achievements": total_achievements,
            "total_points": total_points,
            "rarity_breakdown": rarity_counts,
            "recent_achievements": [
                {
                    "id": ua.achievement_id,
                    "name": self.tracker.achievements[ua.achievement_id].name if ua.achievement_id in self.tracker.achievements else "Unknown",
                    "earned_at": ua.earned_at.isoformat(),
                    "rarity": self.tracker.achievements[ua.achievement_id].rarity.value if ua.achievement_id in self.tracker.achievements else "common"
                }
                for ua in recent_achievements
            ]
        }


# Example usage and testing
if __name__ == "__main__":
    # Initialize ceremony engine
    engine = CeremonyEngine("test_ceremonies.db")
    
    # Simulate user data
    user_id = "user123"
    user_data = {
        "skills_completed": 1,
        "total_minutes": 65,
        "consecutive_days": 1,
        "categories_touched": 2
    }
    
    # Check for ceremonies
    ceremonies = engine.check_and_trigger_ceremonies(user_id, user_data)
    print(f"Generated {len(ceremonies)} ceremonies")
    
    for ceremony in ceremonies:
        print(f"Ceremony: {ceremony.achievement.name}")
        print(f"Type: {ceremony.ceremony_type.value}")
        print(f"Style: {ceremony.ceremony_style.value}")
        print(f"Duration: {ceremony.total_duration:.1f}s")
        print(f"Elements: {len(ceremony.elements)}")
        print("---")
    
    # Get statistics
    stats = engine.get_achievement_statistics(user_id)
    print(f"User has {stats['total_achievements']} achievements worth {stats['total_points']} points")
    print("Achievement system working successfully!")