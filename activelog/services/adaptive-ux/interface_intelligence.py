import asyncio
import json
import time
import random
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import uuid
import numpy as np
from collections import defaultdict, deque

class InputMethod(Enum):
    TOUCH = "touch"
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    VOICE = "voice"
    GAMEPAD = "gamepad"
    STYLUS = "stylus"
    GESTURE = "gesture"
    EYE_TRACKING = "eye_tracking"

class ScreenSize(Enum):
    MOBILE = "mobile"          # < 768px
    TABLET = "tablet"          # 768-1024px
    DESKTOP = "desktop"        # 1024-1440px
    WIDE_DESKTOP = "wide"      # > 1440px
    ULTRA_WIDE = "ultra_wide"  # > 2560px

class AccessibilityNeed(Enum):
    HIGH_CONTRAST = "high_contrast"
    LARGE_TEXT = "large_text"
    SCREEN_READER = "screen_reader"
    REDUCED_MOTION = "reduced_motion"
    COLOR_BLIND = "color_blind"
    MOTOR_IMPAIRMENT = "motor_impairment"
    COGNITIVE_ASSISTANCE = "cognitive_assistance"
    VOICE_CONTROL = "voice_control"

class ExpertiseLevel(Enum):
    BEGINNER = "beginner"
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class InteractionContext(Enum):
    FIRST_VISIT = "first_visit"
    LEARNING = "learning"
    PRODUCTIVE = "productive"
    TROUBLESHOOTING = "troubleshooting"
    EXPLORING = "exploring"
    RUSHED = "rushed"
    FOCUSED = "focused"

@dataclass
class UserProfile:
    user_id: str
    screen_size: ScreenSize
    primary_input: InputMethod
    secondary_inputs: List[InputMethod]
    accessibility_needs: List[AccessibilityNeed]
    expertise_level: ExpertiseLevel
    usage_patterns: Dict[str, Any]
    preferences: Dict[str, Any]
    interaction_history: List[Dict[str, Any]]
    created_at: datetime
    last_updated: datetime
    
    def __post_init__(self):
        if not self.secondary_inputs:
            self.secondary_inputs = []
        if not self.accessibility_needs:
            self.accessibility_needs = []
        if not self.usage_patterns:
            self.usage_patterns = {}
        if not self.preferences:
            self.preferences = {}
        if not self.interaction_history:
            self.interaction_history = []

@dataclass
class InterfaceConfiguration:
    layout_density: str  # compact, comfortable, spacious
    navigation_style: str  # tabs, sidebar, dropdown, breadcrumbs
    color_scheme: str  # light, dark, auto, high-contrast
    font_size: str  # small, medium, large, extra-large
    animation_level: str  # none, minimal, normal, enhanced
    feature_visibility: Dict[str, str]  # feature_id -> always/contextual/hidden
    shortcuts_enabled: bool
    tooltips_enabled: bool
    guided_mode: bool
    auto_save: bool

@dataclass
class InteractionEvent:
    event_id: str
    user_id: str
    event_type: str  # click, hover, keypress, voice_command, etc.
    target_element: str
    context: InteractionContext
    timestamp: datetime
    duration: Optional[float] = None
    success: bool = True
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class UsagePattern:
    pattern_id: str
    user_id: str
    feature_sequence: List[str]
    frequency: int
    avg_duration: float
    success_rate: float
    context: InteractionContext
    discovered_at: datetime
    last_seen: datetime

class DeviceCapabilityDetector:
    def __init__(self):
        self.detection_methods = {}
        
    def detect_screen_size(self, viewport_width: int, viewport_height: int, dpi: float = 96) -> ScreenSize:
        """Detect screen size category"""
        # Consider DPI for accurate sizing
        physical_width = viewport_width / (dpi / 96)
        
        if physical_width < 768:
            return ScreenSize.MOBILE
        elif physical_width < 1024:
            return ScreenSize.TABLET
        elif physical_width < 1440:
            return ScreenSize.DESKTOP
        elif physical_width < 2560:
            return ScreenSize.WIDE_DESKTOP
        else:
            return ScreenSize.ULTRA_WIDE
    
    def detect_input_methods(self, user_agent: str, capabilities: Dict[str, Any]) -> Tuple[InputMethod, List[InputMethod]]:
        """Detect available input methods"""
        primary = InputMethod.MOUSE
        secondary = []
        
        # Touch detection
        if capabilities.get("touchscreen", False) or "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
            if "Mobile" in user_agent:
                primary = InputMethod.TOUCH
            else:
                secondary.append(InputMethod.TOUCH)
        
        # Keyboard detection
        if not capabilities.get("virtual_keyboard_only", False):
            if primary != InputMethod.TOUCH:
                secondary.append(InputMethod.KEYBOARD)
            else:
                secondary.insert(0, InputMethod.KEYBOARD)
        
        # Voice detection
        if capabilities.get("speech_recognition", False):
            secondary.append(InputMethod.VOICE)
        
        # Stylus detection (common on tablets)
        if capabilities.get("stylus_support", False) or "Surface" in user_agent:
            secondary.append(InputMethod.STYLUS)
        
        # Gamepad detection
        if capabilities.get("gamepad_support", False):
            secondary.append(InputMethod.GAMEPAD)
        
        # Eye tracking (specialized hardware)
        if capabilities.get("eye_tracking", False):
            secondary.append(InputMethod.EYE_TRACKING)
        
        return primary, secondary
    
    def detect_accessibility_needs(self, system_settings: Dict[str, Any], user_preferences: Dict[str, Any]) -> List[AccessibilityNeed]:
        """Detect accessibility requirements"""
        needs = []
        
        # High contrast
        if system_settings.get("high_contrast_mode", False) or user_preferences.get("prefer_high_contrast", False):
            needs.append(AccessibilityNeed.HIGH_CONTRAST)
        
        # Large text
        if system_settings.get("font_size_multiplier", 1.0) > 1.2:
            needs.append(AccessibilityNeed.LARGE_TEXT)
        
        # Screen reader
        if system_settings.get("screen_reader_active", False):
            needs.append(AccessibilityNeed.SCREEN_READER)
        
        # Reduced motion
        if system_settings.get("reduce_motion", False):
            needs.append(AccessibilityNeed.REDUCED_MOTION)
        
        # Color blindness
        if user_preferences.get("colorblind_friendly", False):
            needs.append(AccessibilityNeed.COLOR_BLIND)
        
        # Motor impairment indicators
        if system_settings.get("sticky_keys", False) or system_settings.get("mouse_keys", False):
            needs.append(AccessibilityNeed.MOTOR_IMPAIRMENT)
        
        # Voice control
        if system_settings.get("voice_control_enabled", False):
            needs.append(AccessibilityNeed.VOICE_CONTROL)
        
        return needs

class ExpertiseLevelAnalyzer:
    def __init__(self):
        self.feature_complexity_map = {
            # Basic features - any user can use
            "basic_view": 1,
            "simple_settings": 1,
            "help": 1,
            
            # Intermediate features
            "advanced_settings": 3,
            "custom_workflows": 3,
            "data_export": 3,
            
            # Advanced features
            "api_integration": 4,
            "scripting": 5,
            "system_administration": 5,
        }
    
    def analyze_expertise_level(self, interaction_history: List[InteractionEvent], time_window_days: int = 30) -> ExpertiseLevel:
        """Analyze user expertise based on interaction patterns"""
        if not interaction_history:
            return ExpertiseLevel.BEGINNER
        
        # Filter recent interactions
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        recent_interactions = [e for e in interaction_history if e.timestamp > cutoff_date]
        
        if not recent_interactions:
            return ExpertiseLevel.BEGINNER
        
        # Calculate expertise indicators
        complexity_scores = []
        feature_breadth = set()
        keyboard_shortcut_usage = 0
        error_recovery_success = 0
        total_errors = 0
        
        for event in recent_interactions:
            # Track feature complexity
            feature = event.target_element
            if feature in self.feature_complexity_map:
                complexity_scores.append(self.feature_complexity_map[feature])
                feature_breadth.add(feature)
            
            # Track keyboard shortcut usage
            if event.event_type == "keyboard_shortcut":
                keyboard_shortcut_usage += 1
            
            # Track error handling
            if not event.success:
                total_errors += 1
                # Check if user successfully recovered in next few actions
                event_index = recent_interactions.index(event)
                next_events = recent_interactions[event_index + 1:event_index + 4]
                if any(e.success and e.target_element == event.target_element for e in next_events):
                    error_recovery_success += 1
        
        # Calculate metrics
        avg_complexity = np.mean(complexity_scores) if complexity_scores else 1
        feature_breadth_score = len(feature_breadth)
        shortcut_ratio = keyboard_shortcut_usage / max(len(recent_interactions), 1)
        error_recovery_ratio = error_recovery_success / max(total_errors, 1)
        
        # Determine expertise level
        expertise_score = (
            avg_complexity * 0.4 +
            min(feature_breadth_score / 10, 1) * 0.3 +
            min(shortcut_ratio * 10, 1) * 0.2 +
            error_recovery_ratio * 0.1
        )
        
        if expertise_score < 1.5:
            return ExpertiseLevel.BEGINNER
        elif expertise_score < 2.5:
            return ExpertiseLevel.NOVICE
        elif expertise_score < 3.5:
            return ExpertiseLevel.INTERMEDIATE
        elif expertise_score < 4.5:
            return ExpertiseLevel.ADVANCED
        else:
            return ExpertiseLevel.EXPERT

class UsagePatternAnalyzer:
    def __init__(self):
        self.min_pattern_frequency = 3
        self.pattern_window_days = 14
        
    def discover_patterns(self, interaction_history: List[InteractionEvent]) -> List[UsagePattern]:
        """Discover common usage patterns from interaction history"""
        patterns = []
        
        # Filter recent interactions
        cutoff_date = datetime.now() - timedelta(days=self.pattern_window_days)
        recent_interactions = [e for e in interaction_history if e.timestamp > cutoff_date]
        
        if len(recent_interactions) < 10:  # Need sufficient data
            return patterns
        
        # Group interactions by session (assuming 30-minute gaps indicate new sessions)
        sessions = self._group_into_sessions(recent_interactions)
        
        # Find common feature sequences
        sequences = self._extract_feature_sequences(sessions)
        pattern_candidates = self._find_frequent_sequences(sequences)
        
        # Create pattern objects
        for sequence, frequency in pattern_candidates.items():
            if frequency >= self.min_pattern_frequency:
                pattern = self._create_usage_pattern(sequence, frequency, sessions)
                patterns.append(pattern)
        
        return patterns
    
    def _group_into_sessions(self, interactions: List[InteractionEvent], gap_minutes: int = 30) -> List[List[InteractionEvent]]:
        """Group interactions into sessions based on time gaps"""
        if not interactions:
            return []
        
        sessions = []
        current_session = [interactions[0]]
        
        for i in range(1, len(interactions)):
            time_gap = (interactions[i].timestamp - interactions[i-1].timestamp).total_seconds() / 60
            
            if time_gap <= gap_minutes:
                current_session.append(interactions[i])
            else:
                sessions.append(current_session)
                current_session = [interactions[i]]
        
        sessions.append(current_session)
        return sessions
    
    def _extract_feature_sequences(self, sessions: List[List[InteractionEvent]], max_sequence_length: int = 5) -> List[Tuple[str, ...]]:
        """Extract feature usage sequences from sessions"""
        sequences = []
        
        for session in sessions:
            if len(session) < 2:
                continue
                
            features = [event.target_element for event in session]
            
            # Extract sequences of various lengths
            for length in range(2, min(max_sequence_length + 1, len(features) + 1)):
                for i in range(len(features) - length + 1):
                    sequence = tuple(features[i:i + length])
                    sequences.append(sequence)
        
        return sequences
    
    def _find_frequent_sequences(self, sequences: List[Tuple[str, ...]]) -> Dict[Tuple[str, ...], int]:
        """Find frequently occurring sequences"""
        sequence_counts = defaultdict(int)
        
        for sequence in sequences:
            sequence_counts[sequence] += 1
        
        return dict(sequence_counts)
    
    def _create_usage_pattern(self, sequence: Tuple[str, ...], frequency: int, sessions: List[List[InteractionEvent]]) -> UsagePattern:
        """Create a UsagePattern object from sequence data"""
        # Calculate metrics for this pattern
        durations = []
        success_count = 0
        total_occurrences = 0
        contexts = []
        
        for session in sessions:
            features = [event.target_element for event in session]
            
            # Find occurrences of this sequence in the session
            for i in range(len(features) - len(sequence) + 1):
                if tuple(features[i:i + len(sequence)]) == sequence:
                    total_occurrences += 1
                    
                    # Calculate duration for this occurrence
                    start_time = session[i].timestamp
                    end_time = session[i + len(sequence) - 1].timestamp
                    duration = (end_time - start_time).total_seconds()
                    durations.append(duration)
                    
                    # Check success
                    occurrence_events = session[i:i + len(sequence)]
                    if all(event.success for event in occurrence_events):
                        success_count += 1
                    
                    # Track contexts
                    contexts.append(session[i].context)
        
        avg_duration = np.mean(durations) if durations else 0
        success_rate = success_count / max(total_occurrences, 1)
        most_common_context = max(set(contexts), key=contexts.count) if contexts else InteractionContext.PRODUCTIVE
        
        return UsagePattern(
            pattern_id=f"pattern_{hash(sequence)}",
            user_id="",  # Will be set by caller
            feature_sequence=list(sequence),
            frequency=frequency,
            avg_duration=avg_duration,
            success_rate=success_rate,
            context=most_common_context,
            discovered_at=datetime.now(),
            last_seen=datetime.now()
        )

class ContextDetector:
    def __init__(self):
        self.context_indicators = {
            InteractionContext.FIRST_VISIT: {
                "help_views": 0.3,
                "tutorial_engagement": 0.4,
                "exploration_ratio": 0.3
            },
            InteractionContext.LEARNING: {
                "help_views": 0.2,
                "feature_discovery": 0.3,
                "trial_and_error": 0.3,
                "documentation_access": 0.2
            },
            InteractionContext.PRODUCTIVE: {
                "direct_feature_usage": 0.4,
                "keyboard_shortcuts": 0.3,
                "minimal_help_seeking": 0.3
            },
            InteractionContext.TROUBLESHOOTING: {
                "error_encounters": 0.4,
                "help_seeking": 0.3,
                "retry_attempts": 0.3
            },
            InteractionContext.RUSHED: {
                "rapid_interactions": 0.4,
                "shortcut_usage": 0.3,
                "minimal_exploration": 0.3
            }
        }
    
    def detect_current_context(self, recent_events: List[InteractionEvent], time_window_minutes: int = 15) -> InteractionContext:
        """Detect current user context based on recent interactions"""
        if not recent_events:
            return InteractionContext.EXPLORING
        
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        relevant_events = [e for e in recent_events if e.timestamp > cutoff_time]
        
        if not relevant_events:
            return InteractionContext.EXPLORING
        
        # Calculate context indicators
        context_scores = {}
        
        for context, indicators in self.context_indicators.items():
            score = 0
            
            if context == InteractionContext.FIRST_VISIT:
                help_ratio = sum(1 for e in relevant_events if "help" in e.target_element) / len(relevant_events)
                tutorial_ratio = sum(1 for e in relevant_events if "tutorial" in e.target_element) / len(relevant_events)
                unique_features = len(set(e.target_element for e in relevant_events))
                exploration_ratio = unique_features / len(relevant_events)
                
                score = (help_ratio * indicators["help_views"] +
                        tutorial_ratio * indicators["tutorial_engagement"] +
                        exploration_ratio * indicators["exploration_ratio"])
            
            elif context == InteractionContext.TROUBLESHOOTING:
                error_ratio = sum(1 for e in relevant_events if not e.success) / len(relevant_events)
                help_ratio = sum(1 for e in relevant_events if "help" in e.target_element) / len(relevant_events)
                retry_ratio = len([e for e in relevant_events if relevant_events.count(e.target_element) > 1]) / len(relevant_events)
                
                score = (error_ratio * indicators["error_encounters"] +
                        help_ratio * indicators["help_seeking"] +
                        retry_ratio * indicators["retry_attempts"])
            
            elif context == InteractionContext.RUSHED:
                avg_duration = np.mean([e.duration or 1.0 for e in relevant_events])
                rapid_ratio = sum(1 for e in relevant_events if (e.duration or 1.0) < avg_duration * 0.5) / len(relevant_events)
                shortcut_ratio = sum(1 for e in relevant_events if e.event_type == "keyboard_shortcut") / len(relevant_events)
                
                score = rapid_ratio * indicators["rapid_interactions"] + shortcut_ratio * indicators["shortcut_usage"]
            
            context_scores[context] = score
        
        # Return context with highest score
        return max(context_scores, key=context_scores.get)

class InterfaceIntelligence:
    def __init__(self):
        self.user_profiles = {}
        self.device_detector = DeviceCapabilityDetector()
        self.expertise_analyzer = ExpertiseLevelAnalyzer()
        self.pattern_analyzer = UsagePatternAnalyzer()
        self.context_detector = ContextDetector()
        
        # Feature usage tracking
        self.feature_usage_stats = defaultdict(lambda: {
            'total_uses': 0,
            'successful_uses': 0,
            'avg_duration': 0,
            'user_ratings': []
        })
        
        # Interface adaptation rules
        self.adaptation_rules = self._initialize_adaptation_rules()
    
    def _initialize_adaptation_rules(self) -> Dict[str, Any]:
        """Initialize rules for interface adaptation"""
        return {
            'layout': {
                ScreenSize.MOBILE: {'density': 'comfortable', 'navigation': 'bottom_tabs'},
                ScreenSize.TABLET: {'density': 'comfortable', 'navigation': 'sidebar'},
                ScreenSize.DESKTOP: {'density': 'compact', 'navigation': 'top_tabs'},
                ScreenSize.WIDE_DESKTOP: {'density': 'compact', 'navigation': 'sidebar'},
            },
            'accessibility': {
                AccessibilityNeed.HIGH_CONTRAST: {'color_scheme': 'high_contrast', 'border_emphasis': True},
                AccessibilityNeed.LARGE_TEXT: {'font_size': 'large', 'spacing_increase': 1.2},
                AccessibilityNeed.REDUCED_MOTION: {'animation_level': 'none', 'transitions': 'fade_only'},
                AccessibilityNeed.SCREEN_READER: {'semantic_markup': True, 'aria_labels': True},
            },
            'expertise': {
                ExpertiseLevel.BEGINNER: {'guided_mode': True, 'tooltips': True, 'feature_limit': 10},
                ExpertiseLevel.NOVICE: {'guided_mode': True, 'tooltips': True, 'feature_limit': 15},
                ExpertiseLevel.INTERMEDIATE: {'guided_mode': False, 'tooltips': 'contextual', 'feature_limit': 25},
                ExpertiseLevel.ADVANCED: {'guided_mode': False, 'tooltips': 'minimal', 'shortcuts_enabled': True},
                ExpertiseLevel.EXPERT: {'guided_mode': False, 'tooltips': 'off', 'advanced_features': True},
            }
        }
    
    async def create_user_profile(self, user_id: str, device_info: Dict[str, Any], system_settings: Dict[str, Any], user_preferences: Dict[str, Any] = None) -> UserProfile:
        """Create initial user profile based on device capabilities and settings"""
        
        # Detect screen size
        screen_size = self.device_detector.detect_screen_size(
            device_info.get('viewport_width', 1920),
            device_info.get('viewport_height', 1080),
            device_info.get('dpi', 96)
        )
        
        # Detect input methods
        primary_input, secondary_inputs = self.device_detector.detect_input_methods(
            device_info.get('user_agent', ''),
            device_info.get('capabilities', {})
        )
        
        # Detect accessibility needs
        accessibility_needs = self.device_detector.detect_accessibility_needs(
            system_settings,
            user_preferences or {}
        )
        
        profile = UserProfile(
            user_id=user_id,
            screen_size=screen_size,
            primary_input=primary_input,
            secondary_inputs=secondary_inputs,
            accessibility_needs=accessibility_needs,
            expertise_level=ExpertiseLevel.BEGINNER,  # Will be updated as user interacts
            usage_patterns={},
            preferences=user_preferences or {},
            interaction_history=[],
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        self.user_profiles[user_id] = profile
        return profile
    
    async def record_interaction(self, user_id: str, event_type: str, target_element: str, duration: float = None, success: bool = True, metadata: Dict[str, Any] = None) -> InteractionEvent:
        """Record user interaction event"""
        
        profile = self.user_profiles.get(user_id)
        if not profile:
            # Create basic profile if it doesn't exist
            profile = await self.create_user_profile(user_id, {}, {})
        
        # Detect current context
        current_context = self.context_detector.detect_current_context(profile.interaction_history[-20:])
        
        # Create interaction event
        event = InteractionEvent(
            event_id=f"event_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            event_type=event_type,
            target_element=target_element,
            context=current_context,
            timestamp=datetime.now(),
            duration=duration,
            success=success,
            metadata=metadata or {}
        )
        
        # Add to profile history
        profile.interaction_history.append(event)
        
        # Keep history manageable (last 1000 events)
        if len(profile.interaction_history) > 1000:
            profile.interaction_history = profile.interaction_history[-1000:]
        
        # Update feature usage stats
        self._update_feature_stats(target_element, duration, success)
        
        # Trigger profile updates if needed
        await self._maybe_update_profile(user_id)
        
        return event
    
    def _update_feature_stats(self, feature: str, duration: float, success: bool):
        """Update global feature usage statistics"""
        stats = self.feature_usage_stats[feature]
        stats['total_uses'] += 1
        
        if success:
            stats['successful_uses'] += 1
        
        if duration is not None:
            # Update rolling average
            current_avg = stats['avg_duration']
            total_uses = stats['total_uses']
            stats['avg_duration'] = ((current_avg * (total_uses - 1)) + duration) / total_uses
    
    async def _maybe_update_profile(self, user_id: str):
        """Update user profile if enough new data has accumulated"""
        profile = self.user_profiles.get(user_id)
        if not profile:
            return
        
        # Update expertise level every 50 interactions
        if len(profile.interaction_history) % 50 == 0:
            old_level = profile.expertise_level
            profile.expertise_level = self.expertise_analyzer.analyze_expertise_level(profile.interaction_history)
            
            if profile.expertise_level != old_level:
                print(f"User {user_id} expertise level updated: {old_level.value} -> {profile.expertise_level.value}")
        
        # Update usage patterns every 100 interactions
        if len(profile.interaction_history) % 100 == 0:
            patterns = self.pattern_analyzer.discover_patterns(profile.interaction_history)
            profile.usage_patterns = {
                p.pattern_id: asdict(p) for p in patterns
            }
        
        profile.last_updated = datetime.now()
    
    def generate_interface_config(self, user_id: str, current_context: InteractionContext = None) -> InterfaceConfiguration:
        """Generate adaptive interface configuration for user"""
        profile = self.user_profiles.get(user_id)
        if not profile:
            # Return default configuration
            return self._get_default_config()
        
        config = InterfaceConfiguration(
            layout_density="comfortable",
            navigation_style="top_tabs",
            color_scheme="auto",
            font_size="medium",
            animation_level="normal",
            feature_visibility={},
            shortcuts_enabled=False,
            tooltips_enabled=True,
            guided_mode=True,
            auto_save=True
        )
        
        # Apply screen size adaptations
        layout_rules = self.adaptation_rules['layout'].get(profile.screen_size, {})
        config.layout_density = layout_rules.get('density', config.layout_density)
        config.navigation_style = layout_rules.get('navigation', config.navigation_style)
        
        # Apply accessibility adaptations
        for need in profile.accessibility_needs:
            accessibility_rules = self.adaptation_rules['accessibility'].get(need, {})
            
            if 'color_scheme' in accessibility_rules:
                config.color_scheme = accessibility_rules['color_scheme']
            if 'font_size' in accessibility_rules:
                config.font_size = accessibility_rules['font_size']
            if 'animation_level' in accessibility_rules:
                config.animation_level = accessibility_rules['animation_level']
        
        # Apply expertise level adaptations
        expertise_rules = self.adaptation_rules['expertise'].get(profile.expertise_level, {})
        config.guided_mode = expertise_rules.get('guided_mode', config.guided_mode)
        config.shortcuts_enabled = expertise_rules.get('shortcuts_enabled', config.shortcuts_enabled)
        
        if expertise_rules.get('tooltips') == True:
            config.tooltips_enabled = True
        elif expertise_rules.get('tooltips') == 'contextual':
            config.tooltips_enabled = True  # Will be contextually shown
        elif expertise_rules.get('tooltips') in ['minimal', 'off']:
            config.tooltips_enabled = False
        
        # Apply feature visibility based on usage patterns and expertise
        config.feature_visibility = self._determine_feature_visibility(profile, current_context)
        
        # Apply context-specific adaptations
        if current_context:
            config = self._apply_context_adaptations(config, current_context)
        
        return config
    
    def _determine_feature_visibility(self, profile: UserProfile, context: InteractionContext = None) -> Dict[str, str]:
        """Determine which features should be visible, contextual, or hidden"""
        visibility = {}
        
        # Get frequently used features from patterns
        frequently_used = set()
        if profile.usage_patterns:
            for pattern_data in profile.usage_patterns.values():
                if pattern_data['frequency'] >= 5:  # Used frequently
                    frequently_used.update(pattern_data['feature_sequence'])
        
        # Get rarely used features (from global stats)
        rarely_used = set()
        for feature, stats in self.feature_usage_stats.items():
            if stats['total_uses'] > 0:
                success_rate = stats['successful_uses'] / stats['total_uses']
                if success_rate < 0.5 or stats['total_uses'] < 3:  # Low success or rare use
                    rarely_used.add(feature)
        
        # Determine visibility for each feature category
        basic_features = ['home', 'settings', 'help', 'save', 'load']
        intermediate_features = ['export', 'import', 'customize', 'advanced_settings']
        advanced_features = ['api_access', 'scripting', 'admin_panel', 'system_config']
        
        # Basic features - always visible for beginners/novices
        for feature in basic_features:
            if profile.expertise_level in [ExpertiseLevel.BEGINNER, ExpertiseLevel.NOVICE]:
                visibility[feature] = 'always'
            else:
                visibility[feature] = 'contextual'
        
        # Intermediate features
        for feature in intermediate_features:
            if profile.expertise_level in [ExpertiseLevel.BEGINNER]:
                visibility[feature] = 'hidden'
            elif feature in frequently_used:
                visibility[feature] = 'always'
            else:
                visibility[feature] = 'contextual'
        
        # Advanced features
        for feature in advanced_features:
            if profile.expertise_level in [ExpertiseLevel.BEGINNER, ExpertiseLevel.NOVICE]:
                visibility[feature] = 'hidden'
            elif profile.expertise_level == ExpertiseLevel.EXPERT:
                visibility[feature] = 'always'
            else:
                visibility[feature] = 'contextual'
        
        # Hide rarely used features for beginners
        if profile.expertise_level == ExpertiseLevel.BEGINNER:
            for feature in rarely_used:
                visibility[feature] = 'hidden'
        
        return visibility
    
    def _apply_context_adaptations(self, config: InterfaceConfiguration, context: InteractionContext) -> InterfaceConfiguration:
        """Apply context-specific interface adaptations"""
        
        if context == InteractionContext.FIRST_VISIT:
            config.guided_mode = True
            config.tooltips_enabled = True
            config.layout_density = "spacious"
        
        elif context == InteractionContext.LEARNING:
            config.tooltips_enabled = True
            config.guided_mode = True
        
        elif context == InteractionContext.PRODUCTIVE:
            config.shortcuts_enabled = True
            config.tooltips_enabled = False
            config.layout_density = "compact"
        
        elif context == InteractionContext.TROUBLESHOOTING:
            config.tooltips_enabled = True
            config.guided_mode = True
            # Show help-related features prominently
            config.feature_visibility.update({
                'help': 'always',
                'documentation': 'always',
                'support': 'always'
            })
        
        elif context == InteractionContext.RUSHED:
            config.shortcuts_enabled = True
            config.tooltips_enabled = False
            config.auto_save = True
            config.layout_density = "compact"
        
        return config
    
    def _get_default_config(self) -> InterfaceConfiguration:
        """Get default interface configuration"""
        return InterfaceConfiguration(
            layout_density="comfortable",
            navigation_style="top_tabs",
            color_scheme="auto",
            font_size="medium",
            animation_level="normal",
            feature_visibility={},
            shortcuts_enabled=False,
            tooltips_enabled=True,
            guided_mode=True,
            auto_save=True
        )
    
    def get_feature_recommendations(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get personalized feature recommendations"""
        profile = self.user_profiles.get(user_id)
        if not profile:
            return []
        
        recommendations = []
        
        # Recommend features based on usage patterns
        unused_features = set(self.feature_usage_stats.keys())
        if profile.interaction_history:
            used_features = set(event.target_element for event in profile.interaction_history)
            unused_features -= used_features
        
        # Score unused features based on popularity and relevance
        for feature in unused_features:
            stats = self.feature_usage_stats[feature]
            if stats['total_uses'] > 10:  # Only recommend popular features
                success_rate = stats['successful_uses'] / stats['total_uses']
                
                if success_rate > 0.7:  # High success rate
                    recommendations.append({
                        'feature': feature,
                        'reason': 'popular_and_successful',
                        'success_rate': success_rate,
                        'usage_count': stats['total_uses']
                    })
        
        # Sort by success rate and usage
        recommendations.sort(key=lambda x: (x['success_rate'], x['usage_count']), reverse=True)
        
        return recommendations[:limit]
    
    def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user behavior and preferences"""
        profile = self.user_profiles.get(user_id)
        if not profile:
            return {'error': 'User profile not found'}
        
        # Calculate insights
        total_interactions = len(profile.interaction_history)
        if total_interactions == 0:
            return {'message': 'Insufficient interaction data'}
        
        # Success rate
        successful_interactions = sum(1 for event in profile.interaction_history if event.success)
        success_rate = successful_interactions / total_interactions
        
        # Most used features
        feature_counts = defaultdict(int)
        for event in profile.interaction_history:
            feature_counts[event.target_element] += 1
        
        most_used = sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Context distribution
        context_counts = defaultdict(int)
        for event in profile.interaction_history:
            context_counts[event.context] += 1
        
        # Time-based patterns
        hourly_activity = defaultdict(int)
        for event in profile.interaction_history:
            hour = event.timestamp.hour
            hourly_activity[hour] += 1
        
        most_active_hour = max(hourly_activity, key=hourly_activity.get) if hourly_activity else 0
        
        return {
            'user_id': user_id,
            'expertise_level': profile.expertise_level.value,
            'screen_size': profile.screen_size.value,
            'primary_input': profile.primary_input.value,
            'accessibility_needs': [need.value for need in profile.accessibility_needs],
            'total_interactions': total_interactions,
            'success_rate': success_rate,
            'most_used_features': most_used,
            'usage_patterns_discovered': len(profile.usage_patterns),
            'most_active_hour': most_active_hour,
            'context_distribution': dict(context_counts),
            'profile_age_days': (datetime.now() - profile.created_at).days
        }

if __name__ == "__main__":
    print("Interface Intelligence System")
    print("=" * 50)
    
    async def demo():
        # Create interface intelligence system
        intelligence = InterfaceIntelligence()
        
        # Create demo user profile
        device_info = {
            'viewport_width': 1920,
            'viewport_height': 1080,
            'dpi': 96,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'capabilities': {
                'touchscreen': False,
                'speech_recognition': True,
                'gamepad_support': False
            }
        }
        
        system_settings = {
            'high_contrast_mode': False,
            'font_size_multiplier': 1.0,
            'reduce_motion': False
        }
        
        user_preferences = {
            'prefer_dark_mode': True,
            'keyboard_shortcuts': True
        }
        
        # Create user profile
        profile = await intelligence.create_user_profile(
            'demo_user', device_info, system_settings, user_preferences
        )
        
        print(f"Created profile for user: {profile.user_id}")
        print(f"Screen size: {profile.screen_size.value}")
        print(f"Primary input: {profile.primary_input.value}")
        print(f"Accessibility needs: {[need.value for need in profile.accessibility_needs]}")
        
        # Simulate user interactions
        print(f"\nSimulating user interactions...")
        
        interactions = [
            ('click', 'home', 2.0, True),
            ('click', 'settings', 3.5, True),
            ('click', 'help', 8.0, True),
            ('click', 'advanced_settings', 15.0, False),
            ('click', 'help', 5.0, True),
            ('click', 'advanced_settings', 12.0, True),
            ('keyboard_shortcut', 'save', 0.5, True),
            ('click', 'export', 4.0, True),
            ('keyboard_shortcut', 'copy', 0.3, True),
            ('click', 'api_access', 20.0, True),
        ]
        
        for event_type, target, duration, success in interactions:
            await intelligence.record_interaction(
                'demo_user', event_type, target, duration, success
            )
        
        # Generate interface configuration
        config = intelligence.generate_interface_config('demo_user')
        
        print(f"\nGenerated Interface Configuration:")
        print(f"Layout density: {config.layout_density}")
        print(f"Navigation style: {config.navigation_style}")
        print(f"Color scheme: {config.color_scheme}")
        print(f"Font size: {config.font_size}")
        print(f"Shortcuts enabled: {config.shortcuts_enabled}")
        print(f"Tooltips enabled: {config.tooltips_enabled}")
        print(f"Guided mode: {config.guided_mode}")
        print(f"Feature visibility: {len(config.feature_visibility)} rules")
        
        # Get user insights
        insights = intelligence.get_user_insights('demo_user')
        print(f"\nUser Insights:")
        print(f"Expertise level: {insights['expertise_level']}")
        print(f"Success rate: {insights['success_rate']:.1%}")
        print(f"Most used features: {insights['most_used_features'][:3]}")
        
        # Get feature recommendations
        recommendations = intelligence.get_feature_recommendations('demo_user')
        print(f"\nFeature Recommendations:")
        for rec in recommendations[:3]:
            print(f"- {rec['feature']}: {rec['reason']} (success rate: {rec['success_rate']:.1%})")
        
        print("\nInterface Intelligence demo completed")
    
    asyncio.run(demo())