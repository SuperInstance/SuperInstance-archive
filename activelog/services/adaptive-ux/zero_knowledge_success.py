#!/usr/bin/env python3
"""
Zero-Knowledge Success System for Adaptive UX

This module creates intuitive first-run experiences that require no prior knowledge,
providing self-explanatory interfaces with progressive onboarding, contextual help,
and safe exploration environments.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque

# Import from other modules
from interface_intelligence import (
    UserProfile, ExpertiseLevel, InteractionContext, 
    InteractionEvent, InterfaceIntelligence
)
from progressive_disclosure import ProgressiveDisclosureEngine

class OnboardingStage(Enum):
    """Stages of the zero-knowledge onboarding process"""
    FIRST_VISIT = "first_visit"
    ORIENTATION = "orientation"
    GUIDED_EXPLORATION = "guided_exploration"
    FIRST_SUCCESS = "first_success"
    FEATURE_DISCOVERY = "feature_discovery"
    COMPETENCY_BUILDING = "competency_building"
    INDEPENDENCE = "independence"
    MASTERY = "mastery"

class HelpTrigger(Enum):
    """Conditions that trigger proactive help"""
    CONFUSION_DETECTED = "confusion_detected"
    ERROR_OCCURRED = "error_occurred"
    HESITATION_PATTERN = "hesitation_pattern"
    UNSUCCESSFUL_ATTEMPTS = "unsuccessful_attempts"
    NEW_FEATURE_ENCOUNTERED = "new_feature_encountered"
    TIME_THRESHOLD_EXCEEDED = "time_threshold_exceeded"
    SUCCESS_ACHIEVED = "success_achieved"

class TutorialType(Enum):
    """Types of interactive tutorials"""
    QUICK_START = "quick_start"          # 2-3 minutes essential overview
    GUIDED_TOUR = "guided_tour"          # 5-10 minutes comprehensive tour
    CONTEXTUAL_HELP = "contextual_help"  # Just-in-time specific help
    INTERACTIVE_DEMO = "interactive_demo" # Hands-on practice session
    VIDEO_WALKTHROUGH = "video_walkthrough" # Visual demonstration
    TEXT_GUIDE = "text_guide"            # Step-by-step written instructions

class SafetyLevel(Enum):
    """Levels of safety for exploration mode"""
    FULL_SAFETY = "full_safety"         # Nothing can go wrong
    GUIDED_SAFETY = "guided_safety"     # Limited actions, easy undo
    NORMAL_SAFETY = "normal_safety"     # Standard undo/redo available
    ADVANCED_MODE = "advanced_mode"     # Full functionality, user responsible

@dataclass
class OnboardingStep:
    """Individual step in the onboarding process"""
    step_id: str
    title: str
    description: str
    instructions: List[str]
    success_criteria: Dict[str, Any]
    help_text: str
    estimated_duration_seconds: int
    prerequisite_steps: List[str] = field(default_factory=list)
    optional: bool = False
    tutorial_available: bool = True
    
@dataclass
class UserProgress:
    """Tracks user progress through onboarding"""
    user_id: str
    current_stage: OnboardingStage
    completed_steps: Set[str] = field(default_factory=set)
    skipped_steps: Set[str] = field(default_factory=set)
    first_visit_time: Optional[datetime] = None
    last_activity_time: Optional[datetime] = None
    total_session_time: timedelta = field(default_factory=lambda: timedelta())
    success_count: int = 0
    error_count: int = 0
    help_requests: int = 0
    tutorial_completions: Set[str] = field(default_factory=set)
    confidence_indicators: Dict[str, float] = field(default_factory=dict)

@dataclass
class ContextualTooltip:
    """Smart tooltip that appears based on context"""
    tooltip_id: str
    target_element: str
    content: str
    trigger_conditions: Dict[str, Any]
    display_rules: Dict[str, Any]
    priority: int = 1
    max_displays: int = 3
    times_shown: int = 0
    
@dataclass
class InteractiveDemo:
    """Interactive demonstration with guided practice"""
    demo_id: str
    title: str
    description: str
    steps: List[Dict[str, Any]]
    practice_environment: Dict[str, Any]
    success_feedback: str
    estimated_duration_minutes: int

@dataclass
class ProblemDetection:
    """Detected user problem or confusion"""
    detection_id: str
    problem_type: str
    confidence: float
    context: Dict[str, Any]
    suggested_interventions: List[str]
    detected_at: datetime
    resolved: bool = False

class ConfusionDetector:
    """Detects when users are confused or struggling"""
    
    def __init__(self):
        self.confusion_indicators = {
            "rapid_clicking": {"threshold": 5, "timeframe": 10},  # 5 clicks in 10 seconds
            "cursor_wandering": {"threshold": 50, "timeframe": 30},  # Excessive mouse movement
            "element_hovering": {"threshold": 10, "timeframe": 15},  # Hovering without action
            "repeated_actions": {"threshold": 3, "timeframe": 20},   # Same action repeatedly
            "error_recovery": {"threshold": 2, "timeframe": 60},     # Multiple errors
            "help_seeking": {"threshold": 1, "timeframe": 300}       # Looking for help
        }
    
    def analyze_interaction_patterns(self, recent_events: List[InteractionEvent]) -> List[ProblemDetection]:
        """Analyze interaction patterns to detect confusion"""
        problems = []
        
        # Group events by time windows
        time_windows = self._create_time_windows(recent_events, window_size=30)
        
        for window_start, events_in_window in time_windows.items():
            problems.extend(self._detect_confusion_in_window(window_start, events_in_window))
        
        return problems
    
    def _create_time_windows(self, events: List[InteractionEvent], 
                           window_size: int) -> Dict[datetime, List[InteractionEvent]]:
        """Create overlapping time windows for analysis"""
        if not events:
            return {}
        
        windows = {}
        events_sorted = sorted(events, key=lambda e: e.timestamp)
        
        current_time = events_sorted[0].timestamp
        end_time = events_sorted[-1].timestamp
        
        while current_time <= end_time:
            window_events = [
                e for e in events_sorted 
                if current_time <= e.timestamp < current_time + timedelta(seconds=window_size)
            ]
            if window_events:
                windows[current_time] = window_events
            current_time += timedelta(seconds=window_size // 2)  # 50% overlap
        
        return windows
    
    def _detect_confusion_in_window(self, window_start: datetime, 
                                  events: List[InteractionEvent]) -> List[ProblemDetection]:
        """Detect confusion patterns within a time window"""
        problems = []
        
        # Rapid clicking detection
        click_events = [e for e in events if "click" in e.event_type.lower()]
        if len(click_events) >= self.confusion_indicators["rapid_clicking"]["threshold"]:
            problems.append(ProblemDetection(
                f"rapid_clicking_{window_start.isoformat()}",
                "rapid_clicking",
                0.8,
                {"click_count": len(click_events), "timeframe": "10s"},
                ["show_contextual_help", "slow_down_suggestion"],
                window_start
            ))
        
        # Error pattern detection
        error_events = [e for e in events if not e.success]
        if len(error_events) >= self.confusion_indicators["error_recovery"]["threshold"]:
            problems.append(ProblemDetection(
                f"error_pattern_{window_start.isoformat()}",
                "repeated_errors",
                0.9,
                {"error_count": len(error_events), "error_types": [e.event_type for e in error_events]},
                ["provide_tutorial", "suggest_alternative_method"],
                window_start
            ))
        
        # Repeated action detection
        action_counts = defaultdict(int)
        for event in events:
            if event.target_element:
                action_counts[f"{event.event_type}_{event.target_element}"] += 1
        
        for action, count in action_counts.items():
            if count >= self.confusion_indicators["repeated_actions"]["threshold"]:
                problems.append(ProblemDetection(
                    f"repeated_action_{action}_{window_start.isoformat()}",
                    "repeated_action",
                    0.7,
                    {"action": action, "count": count},
                    ["explain_feature", "show_alternative"],
                    window_start
                ))
        
        return problems

class TutorialEngine:
    """Creates and manages interactive tutorials"""
    
    def __init__(self):
        self.tutorial_templates = self._initialize_tutorial_templates()
        self.active_tutorials: Dict[str, Dict[str, Any]] = {}
    
    def _initialize_tutorial_templates(self) -> Dict[str, InteractiveDemo]:
        """Initialize tutorial templates for common tasks"""
        return {
            "first_save": InteractiveDemo(
                "first_save",
                "Saving Your Work",
                "Learn how to save your work safely",
                [
                    {"action": "highlight_element", "target": "save_button", "message": "This is the Save button"},
                    {"action": "wait_for_click", "target": "save_button", "message": "Click here to save"},
                    {"action": "show_dialog", "message": "Great! Your work is now saved safely."}
                ],
                {"sandbox_mode": True, "undo_available": True},
                "Perfect! You've learned how to save your work.",
                2
            ),
            "basic_navigation": InteractiveDemo(
                "basic_navigation",
                "Getting Around",
                "Learn the basics of navigating the interface",
                [
                    {"action": "highlight_area", "target": "main_menu", "message": "This is your main menu"},
                    {"action": "highlight_area", "target": "workspace", "message": "This is where you'll do most of your work"},
                    {"action": "highlight_area", "target": "help_button", "message": "Need help? Click here anytime"}
                ],
                {"read_only": True},
                "Now you know where everything is!",
                3
            ),
            "undo_redo": InteractiveDemo(
                "undo_redo",
                "Safe Experimentation",
                "Learn how to safely try things and undo mistakes",
                [
                    {"action": "demo_action", "message": "Watch me make a change..."},
                    {"action": "highlight_element", "target": "undo_button", "message": "Oops! Let's undo that"},
                    {"action": "wait_for_click", "target": "undo_button"},
                    {"action": "show_success", "message": "See? You can always undo changes!"}
                ],
                {"demo_mode": True, "safe_environment": True},
                "Excellent! Now you can experiment without worry.",
                3
            )
        }
    
    async def create_personalized_tutorial(self, user_id: str, task_context: str, 
                                         user_profile: UserProfile) -> InteractiveDemo:
        """Create a tutorial personalized for the user's context and skill level"""
        # Analyze what the user is trying to do
        if "save" in task_context.lower():
            base_tutorial = self.tutorial_templates["first_save"]
        elif "navigate" in task_context.lower():
            base_tutorial = self.tutorial_templates["basic_navigation"]
        else:
            base_tutorial = self.tutorial_templates["basic_navigation"]
        
        # Adapt tutorial based on expertise level
        if user_profile.expertise_level == ExpertiseLevel.BEGINNER:
            # Add more explanation and slower pace
            adapted_steps = []
            for step in base_tutorial.steps:
                adapted_steps.append(step)
                # Add breathing room between steps for beginners
                if step["action"] != "show_success":
                    adapted_steps.append({"action": "pause", "duration": 2})
        else:
            # Use original pace for more experienced users
            adapted_steps = base_tutorial.steps
        
        return InteractiveDemo(
            f"personalized_{user_id}_{datetime.utcnow().isoformat()}",
            base_tutorial.title,
            base_tutorial.description,
            adapted_steps,
            base_tutorial.practice_environment,
            base_tutorial.success_feedback,
            base_tutorial.estimated_duration_minutes
        )
    
    async def start_tutorial(self, user_id: str, tutorial_id: str) -> Dict[str, Any]:
        """Start an interactive tutorial for a user"""
        if tutorial_id not in self.tutorial_templates:
            return {"success": False, "error": "Tutorial not found"}
        
        tutorial = self.tutorial_templates[tutorial_id]
        
        # Create tutorial session
        session = {
            "tutorial": tutorial,
            "current_step": 0,
            "started_at": datetime.utcnow(),
            "user_responses": [],
            "completed": False
        }
        
        self.active_tutorials[f"{user_id}_{tutorial_id}"] = session
        
        return {
            "success": True,
            "tutorial_data": {
                "title": tutorial.title,
                "description": tutorial.description,
                "estimated_minutes": tutorial.estimated_duration_minutes,
                "first_step": tutorial.steps[0] if tutorial.steps else None
            }
        }

class SafeExplorationEnvironment:
    """Creates safe environments for users to experiment"""
    
    def __init__(self):
        self.sandbox_sessions: Dict[str, Dict[str, Any]] = {}
        self.safety_rules = {
            SafetyLevel.FULL_SAFETY: {
                "can_delete": False,
                "can_modify_settings": False,
                "auto_save": True,
                "undo_limit": None,
                "warning_dialogs": True
            },
            SafetyLevel.GUIDED_SAFETY: {
                "can_delete": True,
                "can_modify_settings": True,
                "auto_save": True,
                "undo_limit": 50,
                "warning_dialogs": True
            },
            SafetyLevel.NORMAL_SAFETY: {
                "can_delete": True,
                "can_modify_settings": True,
                "auto_save": False,
                "undo_limit": 20,
                "warning_dialogs": False
            }
        }
    
    def create_sandbox_session(self, user_id: str, safety_level: SafetyLevel) -> str:
        """Create a safe sandbox environment for exploration"""
        session_id = f"sandbox_{user_id}_{datetime.utcnow().isoformat()}"
        
        session = {
            "user_id": user_id,
            "safety_level": safety_level,
            "rules": self.safety_rules[safety_level],
            "created_at": datetime.utcnow(),
            "actions_taken": [],
            "state_snapshots": [],
            "active": True
        }
        
        self.sandbox_sessions[session_id] = session
        return session_id
    
    def record_sandbox_action(self, session_id: str, action: Dict[str, Any]) -> bool:
        """Record an action taken in the sandbox"""
        if session_id not in self.sandbox_sessions:
            return False
        
        session = self.sandbox_sessions[session_id]
        if not session["active"]:
            return False
        
        # Create state snapshot before action (for undo)
        session["state_snapshots"].append({
            "timestamp": datetime.utcnow(),
            "action_count": len(session["actions_taken"]),
            "state": action.get("pre_state", {})
        })
        
        # Record the action
        session["actions_taken"].append({
            "timestamp": datetime.utcnow(),
            "action": action,
            "undoable": True
        })
        
        return True
    
    def undo_last_action(self, session_id: str) -> Dict[str, Any]:
        """Undo the last action in the sandbox"""
        if session_id not in self.sandbox_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.sandbox_sessions[session_id]
        
        if not session["actions_taken"]:
            return {"success": False, "error": "Nothing to undo"}
        
        # Remove last action
        last_action = session["actions_taken"].pop()
        
        # Restore previous state
        if session["state_snapshots"]:
            restore_point = session["state_snapshots"].pop()
            return {
                "success": True,
                "restored_state": restore_point["state"],
                "undone_action": last_action["action"]
            }
        
        return {"success": True, "undone_action": last_action["action"]}

class ProactiveHelpSystem:
    """Provides proactive help based on user behavior analysis"""
    
    def __init__(self, confusion_detector: ConfusionDetector):
        self.confusion_detector = confusion_detector
        self.help_interventions = self._initialize_help_interventions()
        self.user_help_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def _initialize_help_interventions(self) -> Dict[str, Callable]:
        """Initialize help intervention strategies"""
        return {
            "show_contextual_help": self._show_contextual_help,
            "provide_tutorial": self._provide_tutorial,
            "suggest_alternative_method": self._suggest_alternative_method,
            "explain_feature": self._explain_feature,
            "celebrate_success": self._celebrate_success,
            "offer_break_suggestion": self._offer_break_suggestion
        }
    
    async def analyze_and_offer_help(self, user_id: str, 
                                   recent_events: List[InteractionEvent]) -> List[Dict[str, Any]]:
        """Analyze user behavior and offer appropriate help"""
        # Detect problems
        problems = self.confusion_detector.analyze_interaction_patterns(recent_events)
        
        help_offers = []
        
        for problem in problems:
            if not problem.resolved:
                # Check if we've already helped with this recently
                if not self._recently_helped_with(user_id, problem.problem_type):
                    interventions = await self._select_interventions(user_id, problem)
                    help_offers.extend(interventions)
                    
                    # Record that we offered help
                    self.user_help_history[user_id].append({
                        "timestamp": datetime.utcnow(),
                        "problem_type": problem.problem_type,
                        "interventions_offered": [i["type"] for i in interventions]
                    })
        
        return help_offers
    
    def _recently_helped_with(self, user_id: str, problem_type: str, 
                            window_minutes: int = 10) -> bool:
        """Check if we recently helped with this type of problem"""
        if user_id not in self.user_help_history:
            return False
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_help = [
            h for h in self.user_help_history[user_id] 
            if h["timestamp"] > cutoff_time and h["problem_type"] == problem_type
        ]
        
        return len(recent_help) > 0
    
    async def _select_interventions(self, user_id: str, 
                                  problem: ProblemDetection) -> List[Dict[str, Any]]:
        """Select appropriate interventions for a detected problem"""
        interventions = []
        
        for intervention_name in problem.suggested_interventions:
            if intervention_name in self.help_interventions:
                intervention_func = self.help_interventions[intervention_name]
                intervention_data = await intervention_func(user_id, problem)
                if intervention_data:
                    interventions.append(intervention_data)
        
        return interventions
    
    async def _show_contextual_help(self, user_id: str, 
                                  problem: ProblemDetection) -> Dict[str, Any]:
        """Generate contextual help intervention"""
        return {
            "type": "contextual_help",
            "title": "Need a hand?",
            "message": "It looks like you might be having trouble. Would you like some guidance?",
            "options": ["Show me how", "I'll figure it out", "Not now"],
            "priority": "medium",
            "context": problem.context
        }
    
    async def _provide_tutorial(self, user_id: str, 
                              problem: ProblemDetection) -> Dict[str, Any]:
        """Generate tutorial intervention"""
        return {
            "type": "tutorial_offer",
            "title": "Quick Tutorial Available",
            "message": "Would you like a 2-minute walkthrough of this feature?",
            "options": ["Yes, show me", "Maybe later"],
            "priority": "high",
            "tutorial_id": "contextual_help"
        }
    
    async def _suggest_alternative_method(self, user_id: str, 
                                        problem: ProblemDetection) -> Dict[str, Any]:
        """Suggest alternative way to accomplish the task"""
        return {
            "type": "alternative_suggestion",
            "title": "Try This Instead",
            "message": "There might be an easier way to do what you're trying to accomplish.",
            "options": ["Show me the easier way", "I'll keep trying"],
            "priority": "medium"
        }
    
    async def _explain_feature(self, user_id: str, 
                             problem: ProblemDetection) -> Dict[str, Any]:
        """Provide feature explanation"""
        return {
            "type": "feature_explanation",
            "title": "About This Feature",
            "message": "Let me explain what this feature does and how to use it effectively.",
            "priority": "low",
            "expandable": True
        }
    
    async def _celebrate_success(self, user_id: str, 
                               problem: ProblemDetection) -> Dict[str, Any]:
        """Celebrate user success"""
        return {
            "type": "success_celebration",
            "title": "Nice work! 🎉",
            "message": "You've successfully completed that task. You're getting the hang of this!",
            "priority": "positive",
            "auto_dismiss": 3000  # Auto-dismiss after 3 seconds
        }
    
    async def _offer_break_suggestion(self, user_id: str, 
                                    problem: ProblemDetection) -> Dict[str, Any]:
        """Suggest taking a break if user seems frustrated"""
        return {
            "type": "break_suggestion",
            "title": "Take a breather?",
            "message": "It looks like you've been working hard. Sometimes a short break can help!",
            "options": ["Good idea", "I'll keep going"],
            "priority": "low"
        }

class ZeroKnowledgeSuccessSystem:
    """
    Main system for creating zero-knowledge success experiences
    
    This system ensures users can succeed without prior knowledge through
    intuitive interfaces, proactive help, safe exploration, and adaptive tutorials.
    """
    
    def __init__(self, interface_intelligence: InterfaceIntelligence,
                 disclosure_engine: ProgressiveDisclosureEngine):
        self.interface_intelligence = interface_intelligence
        self.disclosure_engine = disclosure_engine
        self.confusion_detector = ConfusionDetector()
        self.tutorial_engine = TutorialEngine()
        self.safe_environment = SafeExplorationEnvironment()
        self.proactive_help = ProactiveHelpSystem(self.confusion_detector)
        
        self.user_progress: Dict[str, UserProgress] = {}
        self.onboarding_flow = self._initialize_onboarding_flow()
        self.contextual_tooltips = self._initialize_tooltips()
        
        self.logger = logging.getLogger(__name__)
    
    def _initialize_onboarding_flow(self) -> Dict[str, OnboardingStep]:
        """Initialize the zero-knowledge onboarding flow"""
        return {
            "welcome": OnboardingStep(
                "welcome",
                "Welcome!",
                "Get oriented with the basics",
                [
                    "Take a moment to look around",
                    "Notice the main areas of the interface",
                    "Don't worry about understanding everything yet"
                ],
                {"time_spent": 30, "areas_viewed": 3},
                "This is your workspace. Everything is designed to be discoverable.",
                60
            ),
            "first_success": OnboardingStep(
                "first_success",
                "Your First Success",
                "Complete a simple, meaningful task",
                [
                    "We'll guide you through one simple task",
                    "This will show you how easy it can be",
                    "You can't break anything, so feel free to explore"
                ],
                {"task_completed": True, "confidence_boost": True},
                "Success builds confidence. Let's get you a quick win!",
                120,
                ["welcome"]
            ),
            "safe_exploration": OnboardingStep(
                "safe_exploration",
                "Safe Exploration",
                "Try things out in a safe environment",
                [
                    "Explore different features safely",
                    "Everything you do can be easily undone",
                    "Click around and see what happens"
                ],
                {"features_tried": 3, "undo_used": True},
                "Experimentation is learning. You're in a completely safe environment.",
                300,
                ["first_success"]
            ),
            "personalization": OnboardingStep(
                "personalization",
                "Make It Yours",
                "Customize the interface to your preferences",
                [
                    "Adjust settings to match your workflow",
                    "Hide features you don't need right now",
                    "Set up shortcuts for things you'll use often"
                ],
                {"customizations_made": 2, "comfort_level": "high"},
                "The best interface is one that works the way you think.",
                240,
                ["safe_exploration"]
            )
        }
    
    def _initialize_tooltips(self) -> List[ContextualTooltip]:
        """Initialize contextual tooltips for common interface elements"""
        return [
            ContextualTooltip(
                "save_button_first_time",
                "save_button",
                "💾 This saves your work safely. Click anytime to protect your progress.",
                {"first_visit": True, "unsaved_changes": True},
                {"position": "bottom", "arrow": True, "delay": 2000},
                priority=10
            ),
            ContextualTooltip(
                "undo_discovery",
                "undo_button",
                "↩️ Made a mistake? This undoes your last action. It's always safe to experiment!",
                {"error_occurred": True, "attempts": 1},
                {"position": "top", "highlight": True},
                priority=9
            ),
            ContextualTooltip(
                "menu_exploration",
                "main_menu",
                "📋 Explore features here. Don't worry - you can't break anything!",
                {"hesitation_detected": True, "exploration_mode": True},
                {"position": "right", "encouragement": True},
                priority=5
            )
        ]
    
    async def initialize_user_journey(self, user_id: str, 
                                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Initialize the zero-knowledge success journey for a new user"""
        if user_id in self.user_progress:
            return {"status": "already_initialized", "current_stage": self.user_progress[user_id].current_stage.value}
        
        # Create user progress tracking
        progress = UserProgress(
            user_id=user_id,
            current_stage=OnboardingStage.FIRST_VISIT,
            first_visit_time=datetime.utcnow(),
            last_activity_time=datetime.utcnow()
        )
        
        self.user_progress[user_id] = progress
        
        # Get user profile for personalization
        user_profile = await self.interface_intelligence.get_user_profile(user_id)
        
        # Create personalized welcome experience
        welcome_config = await self._create_welcome_experience(user_id, user_profile, context)
        
        # Set up safe exploration environment
        sandbox_session = self.safe_environment.create_sandbox_session(
            user_id, SafetyLevel.FULL_SAFETY
        )
        
        return {
            "status": "initialized",
            "welcome_config": welcome_config,
            "sandbox_session": sandbox_session,
            "next_steps": self._get_next_steps(user_id)
        }
    
    async def _create_welcome_experience(self, user_id: str, user_profile: Optional[UserProfile], 
                                       context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a personalized welcome experience"""
        welcome_config = {
            "greeting": "Welcome! Let's get you started with confidence.",
            "approach": "gentle_guidance",
            "safety_assurance": True,
            "quick_wins_available": True,
            "exploration_encouraged": True
        }
        
        # Personalize based on detected expertise
        if user_profile and user_profile.expertise_level == ExpertiseLevel.EXPERT:
            welcome_config.update({
                "greeting": "Welcome! You look like you know your way around interfaces.",
                "approach": "accelerated_overview",
                "show_advanced_features": True
            })
        elif user_profile and user_profile.expertise_level == ExpertiseLevel.BEGINNER:
            welcome_config.update({
                "greeting": "Welcome! Don't worry if this is new to you - we'll take it step by step.",
                "approach": "extra_gentle",
                "reassurance_level": "high",
                "success_celebration": "enthusiastic"
            })
        
        # Add contextual elements based on device
        if user_profile and hasattr(user_profile, 'device_info'):
            device_type = user_profile.device_info.get('device_type', 'desktop')
            if device_type == 'mobile':
                welcome_config.update({
                    "touch_optimized": True,
                    "gesture_hints": True,
                    "screen_adaptation": "mobile"
                })
        
        return welcome_config
    
    def _get_next_steps(self, user_id: str) -> List[Dict[str, Any]]:
        """Get personalized next steps for the user"""
        progress = self.user_progress.get(user_id)
        if not progress:
            return []
        
        current_stage = progress.current_stage
        
        # Get appropriate onboarding step
        if current_stage == OnboardingStage.FIRST_VISIT:
            step = self.onboarding_flow["welcome"]
        elif current_stage == OnboardingStage.ORIENTATION:
            step = self.onboarding_flow["first_success"]
        else:
            step = self.onboarding_flow.get("safe_exploration")
        
        if not step:
            return []
        
        return [{
            "step_id": step.step_id,
            "title": step.title,
            "description": step.description,
            "instructions": step.instructions[:2],  # Show first 2 instructions
            "estimated_time": f"{step.estimated_duration_seconds // 60} minutes",
            "help_available": step.tutorial_available
        }]
    
    async def record_user_interaction(self, user_id: str, interaction: InteractionEvent) -> None:
        """Record user interaction and update progress"""
        if user_id not in self.user_progress:
            await self.initialize_user_journey(user_id)
        
        progress = self.user_progress[user_id]
        progress.last_activity_time = datetime.utcnow()
        
        # Update success/error counts
        if interaction.success:
            progress.success_count += 1
            await self._check_for_celebration(user_id, interaction)
        else:
            progress.error_count += 1
        
        # Check for confusion and offer help
        recent_events = await self.interface_intelligence.get_recent_interactions(user_id, 30)
        help_offers = await self.proactive_help.analyze_and_offer_help(user_id, recent_events)
        
        if help_offers:
            await self._present_help_offers(user_id, help_offers)
        
        # Check for stage progression
        await self._check_stage_progression(user_id)
    
    async def _check_for_celebration(self, user_id: str, interaction: InteractionEvent) -> None:
        """Check if we should celebrate user success"""
        progress = self.user_progress[user_id]
        
        # Celebrate milestones
        milestones = [1, 5, 10, 25, 50]
        if progress.success_count in milestones:
            celebration = {
                "type": "milestone_celebration",
                "message": f"🎉 Great job! You've successfully completed {progress.success_count} actions!",
                "encouragement": "You're getting the hang of this!",
                "confidence_boost": True
            }
            
            await self._show_celebration(user_id, celebration)
    
    async def _check_stage_progression(self, user_id: str) -> None:
        """Check if user should progress to the next onboarding stage"""
        progress = self.user_progress[user_id]
        current_stage = progress.current_stage
        
        # Define progression criteria
        stage_criteria = {
            OnboardingStage.FIRST_VISIT: {
                "time_spent_minutes": 2,
                "interactions_count": 5
            },
            OnboardingStage.ORIENTATION: {
                "success_count": 3,
                "completion_rate": 0.8
            },
            OnboardingStage.GUIDED_EXPLORATION: {
                "features_explored": 3,
                "confidence_indicators": {"comfort": 0.7}
            }
        }
        
        criteria = stage_criteria.get(current_stage)
        if criteria and await self._criteria_met(user_id, criteria):
            await self._progress_to_next_stage(user_id)
    
    async def _criteria_met(self, user_id: str, criteria: Dict[str, Any]) -> bool:
        """Check if progression criteria are met"""
        progress = self.user_progress[user_id]
        
        for criterion, threshold in criteria.items():
            if criterion == "time_spent_minutes":
                minutes_spent = (datetime.utcnow() - progress.first_visit_time).total_seconds() / 60
                if minutes_spent < threshold:
                    return False
            elif criterion == "success_count":
                if progress.success_count < threshold:
                    return False
            elif criterion == "completion_rate":
                total_interactions = progress.success_count + progress.error_count
                if total_interactions == 0 or (progress.success_count / total_interactions) < threshold:
                    return False
        
        return True
    
    async def _progress_to_next_stage(self, user_id: str) -> None:
        """Progress user to the next onboarding stage"""
        progress = self.user_progress[user_id]
        current_stage = progress.current_stage
        
        stage_progression = {
            OnboardingStage.FIRST_VISIT: OnboardingStage.ORIENTATION,
            OnboardingStage.ORIENTATION: OnboardingStage.GUIDED_EXPLORATION,
            OnboardingStage.GUIDED_EXPLORATION: OnboardingStage.FIRST_SUCCESS,
            OnboardingStage.FIRST_SUCCESS: OnboardingStage.FEATURE_DISCOVERY,
            OnboardingStage.FEATURE_DISCOVERY: OnboardingStage.COMPETENCY_BUILDING,
            OnboardingStage.COMPETENCY_BUILDING: OnboardingStage.INDEPENDENCE
        }
        
        next_stage = stage_progression.get(current_stage)
        if next_stage:
            progress.current_stage = next_stage
            await self._announce_stage_progression(user_id, next_stage)
    
    async def _announce_stage_progression(self, user_id: str, new_stage: OnboardingStage) -> None:
        """Announce progression to new stage"""
        stage_announcements = {
            OnboardingStage.ORIENTATION: {
                "title": "You're getting oriented! 🧭",
                "message": "Great start! Now let's explore some key features together."
            },
            OnboardingStage.GUIDED_EXPLORATION: {
                "title": "Ready to explore! 🔍",
                "message": "You're doing well! Feel free to try different features - you're in a safe space."
            },
            OnboardingStage.FIRST_SUCCESS: {
                "title": "Building confidence! 💪",
                "message": "Excellent progress! You're becoming more comfortable with the interface."
            }
        }
        
        announcement = stage_announcements.get(new_stage)
        if announcement:
            await self._show_progression_announcement(user_id, announcement)
    
    async def get_contextual_help(self, user_id: str, context: str) -> Dict[str, Any]:
        """Get contextual help based on current user context"""
        progress = self.user_progress.get(user_id)
        if not progress:
            return {"error": "User not initialized"}
        
        # Analyze context and provide appropriate help
        help_content = {
            "type": "contextual_help",
            "suggestions": [],
            "tutorials_available": [],
            "confidence_builders": []
        }
        
        # Get recent interactions for context
        recent_events = await self.interface_intelligence.get_recent_interactions(user_id, 10)
        
        # Detect current user state
        if len(recent_events) > 5 and all(not e.success for e in recent_events[-3:]):
            # User struggling
            help_content["suggestions"].append({
                "type": "encouragement",
                "message": "It's okay to make mistakes - that's how we learn! Would you like a quick tutorial?",
                "action": "offer_tutorial"
            })
        elif progress.success_count > 0:
            # User having some success
            help_content["suggestions"].append({
                "type": "progression",
                "message": "You're doing great! Ready to try something new?",
                "action": "suggest_next_feature"
            })
        
        # Add stage-appropriate tutorials
        stage_tutorials = {
            OnboardingStage.FIRST_VISIT: ["basic_navigation", "interface_overview"],
            OnboardingStage.ORIENTATION: ["first_save", "undo_redo"],
            OnboardingStage.GUIDED_EXPLORATION: ["feature_exploration", "customization_basics"]
        }
        
        available_tutorials = stage_tutorials.get(progress.current_stage, [])
        for tutorial_id in available_tutorials:
            if tutorial_id in self.tutorial_engine.tutorial_templates:
                tutorial = self.tutorial_engine.tutorial_templates[tutorial_id]
                help_content["tutorials_available"].append({
                    "id": tutorial_id,
                    "title": tutorial.title,
                    "description": tutorial.description,
                    "duration_minutes": tutorial.estimated_duration_minutes
                })
        
        return help_content
    
    async def start_safe_exploration(self, user_id: str, exploration_type: str = "general") -> Dict[str, Any]:
        """Start a safe exploration session"""
        # Determine appropriate safety level
        progress = self.user_progress.get(user_id)
        if not progress:
            safety_level = SafetyLevel.FULL_SAFETY
        elif progress.current_stage in [OnboardingStage.FIRST_VISIT, OnboardingStage.ORIENTATION]:
            safety_level = SafetyLevel.FULL_SAFETY
        elif progress.current_stage == OnboardingStage.GUIDED_EXPLORATION:
            safety_level = SafetyLevel.GUIDED_SAFETY
        else:
            safety_level = SafetyLevel.NORMAL_SAFETY
        
        session_id = self.safe_environment.create_sandbox_session(user_id, safety_level)
        
        return {
            "session_id": session_id,
            "safety_level": safety_level.value,
            "features": {
                "undo_unlimited": safety_level in [SafetyLevel.FULL_SAFETY, SafetyLevel.GUIDED_SAFETY],
                "auto_save": True,
                "destructive_actions_blocked": safety_level == SafetyLevel.FULL_SAFETY,
                "guidance_available": True
            },
            "encouragement": "Feel free to explore! You can't break anything in this environment."
        }
    
    def get_user_progress_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user's progress through the zero-knowledge journey"""
        progress = self.user_progress.get(user_id)
        if not progress:
            return {"error": "User not found"}
        
        # Calculate confidence indicators
        total_interactions = progress.success_count + progress.error_count
        success_rate = progress.success_count / total_interactions if total_interactions > 0 else 0
        
        # Determine confidence level
        if success_rate > 0.8 and progress.success_count > 10:
            confidence_level = "high"
        elif success_rate > 0.6 and progress.success_count > 5:
            confidence_level = "moderate"
        else:
            confidence_level = "building"
        
        time_in_system = datetime.utcnow() - progress.first_visit_time
        
        return {
            "user_id": user_id,
            "current_stage": progress.current_stage.value,
            "confidence_level": confidence_level,
            "success_count": progress.success_count,
            "success_rate": round(success_rate, 2),
            "time_in_system_minutes": round(time_in_system.total_seconds() / 60, 1),
            "help_requests": progress.help_requests,
            "tutorials_completed": len(progress.tutorial_completions),
            "next_milestone": self._get_next_milestone(progress),
            "achievements": self._get_user_achievements(progress)
        }
    
    def _get_next_milestone(self, progress: UserProgress) -> Dict[str, Any]:
        """Get the next milestone for the user"""
        milestones = [
            {"success_count": 1, "title": "First Success", "description": "Complete your first successful action"},
            {"success_count": 5, "title": "Getting Started", "description": "Successfully complete 5 actions"},
            {"success_count": 10, "title": "Building Confidence", "description": "Successfully complete 10 actions"},
            {"success_count": 25, "title": "Comfortable User", "description": "Successfully complete 25 actions"},
        ]
        
        for milestone in milestones:
            if progress.success_count < milestone["success_count"]:
                return {
                    "target": milestone["success_count"],
                    "title": milestone["title"],
                    "description": milestone["description"],
                    "progress": progress.success_count,
                    "percentage": round((progress.success_count / milestone["success_count"]) * 100, 1)
                }
        
        return {"title": "Expert User", "description": "You've mastered the basics!"}
    
    def _get_user_achievements(self, progress: UserProgress) -> List[Dict[str, Any]]:
        """Get list of user achievements"""
        achievements = []
        
        if progress.success_count >= 1:
            achievements.append({"name": "First Success", "icon": "🎯", "unlocked": True})
        
        if progress.success_count >= 5:
            achievements.append({"name": "Quick Learner", "icon": "⚡", "unlocked": True})
        
        if progress.success_count >= 10:
            achievements.append({"name": "Confident User", "icon": "💪", "unlocked": True})
        
        if progress.error_count > 0 and progress.success_count > progress.error_count:
            achievements.append({"name": "Overcomer", "icon": "🏆", "unlocked": True})
        
        if len(progress.tutorial_completions) >= 1:
            achievements.append({"name": "Eager Student", "icon": "📚", "unlocked": True})
        
        return achievements
    
    # Helper methods for UI integration
    async def _present_help_offers(self, user_id: str, help_offers: List[Dict[str, Any]]) -> None:
        """Present help offers to the user (to be implemented by UI layer)"""
        self.logger.info(f"Presenting help offers to user {user_id}: {help_offers}")
    
    async def _show_celebration(self, user_id: str, celebration: Dict[str, Any]) -> None:
        """Show celebration to the user (to be implemented by UI layer)"""
        self.logger.info(f"Celebrating success for user {user_id}: {celebration}")
    
    async def _show_progression_announcement(self, user_id: str, announcement: Dict[str, Any]) -> None:
        """Show stage progression announcement (to be implemented by UI layer)"""
        self.logger.info(f"Stage progression for user {user_id}: {announcement}")