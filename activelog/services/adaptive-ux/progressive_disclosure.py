#!/usr/bin/env python3
"""
Progressive Disclosure Engine for Adaptive UX System

This module implements progressive disclosure of UI features based on user expertise,
context, and learning progress. It manages the gradual revelation of advanced features
as users demonstrate readiness for increased complexity.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

# Import from interface intelligence
from interface_intelligence import (
    ExpertiseLevel, InteractionContext, UserProfile, 
    InteractionEvent, InterfaceIntelligence
)

class FeatureComplexity(Enum):
    """Feature complexity levels for progressive disclosure"""
    ESSENTIAL = "essential"          # Core functionality everyone needs
    BASIC = "basic"                 # Common but not critical features
    INTERMEDIATE = "intermediate"    # Features for regular users
    ADVANCED = "advanced"           # Power user features
    EXPERT = "expert"               # Technical/expert-only features

class DisclosureStrategy(Enum):
    """Strategies for revealing features"""
    USAGE_BASED = "usage_based"      # Based on usage patterns
    TIME_BASED = "time_based"        # Based on time spent in system
    SUCCESS_BASED = "success_based"  # Based on successful task completion
    REQUEST_BASED = "request_based"  # Based on explicit user requests
    CONTEXT_BASED = "context_based"  # Based on current task context

class FeatureReadiness(Enum):
    """Readiness states for feature disclosure"""
    NOT_READY = "not_ready"
    READY = "ready"
    SUGGESTED = "suggested"
    REVEALED = "revealed"
    MASTERED = "mastered"
    HIDDEN = "hidden"  # Explicitly hidden by user

@dataclass
class Feature:
    """Represents a UI feature with disclosure metadata"""
    feature_id: str
    name: str
    description: str
    complexity: FeatureComplexity
    category: str
    prerequisites: List[str] = None  # Required features to master first
    usage_threshold: int = 5  # Times prerequisite features must be used
    success_threshold: float = 0.8  # Success rate required for prerequisites
    time_threshold_hours: int = 2  # Hours of system usage before availability
    contextual_triggers: List[InteractionContext] = None
    keywords: List[str] = None  # Keywords that might indicate user needs this
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []
        if self.contextual_triggers is None:
            self.contextual_triggers = []
        if self.keywords is None:
            self.keywords = []

@dataclass
class FeatureUsage:
    """Tracks usage statistics for a feature"""
    feature_id: str
    total_uses: int = 0
    successful_uses: int = 0
    last_used: Optional[datetime] = None
    first_used: Optional[datetime] = None
    average_duration: float = 0.0
    contexts_used: Set[InteractionContext] = None
    
    def __post_init__(self):
        if self.contexts_used is None:
            self.contexts_used = set()
    
    @property
    def success_rate(self) -> float:
        return self.successful_uses / self.total_uses if self.total_uses > 0 else 0.0
    
    @property
    def is_mastered(self) -> bool:
        return self.total_uses >= 10 and self.success_rate >= 0.9

@dataclass
class DisclosureRule:
    """Rule for when to disclose a feature"""
    feature_id: str
    strategy: DisclosureStrategy
    conditions: Dict[str, Any]
    priority: int = 1  # Higher priority rules are checked first
    active: bool = True

@dataclass
class LearningPath:
    """Represents a structured learning progression"""
    path_id: str
    name: str
    description: str
    features: List[str]  # Ordered list of feature IDs
    estimated_duration_hours: int
    difficulty_progression: List[FeatureComplexity]
    
@dataclass
class DisclosureState:
    """Current disclosure state for a user"""
    user_id: str
    revealed_features: Set[str] = None
    hidden_features: Set[str] = None  # Explicitly hidden by user
    suggested_features: Set[str] = None
    completed_paths: Set[str] = None
    current_path: Optional[str] = None
    customization_level: int = 0  # How much user has customized their interface
    
    def __post_init__(self):
        if self.revealed_features is None:
            self.revealed_features = set()
        if self.hidden_features is None:
            self.hidden_features = set()
        if self.suggested_features is None:
            self.suggested_features = set()
        if self.completed_paths is None:
            self.completed_paths = set()

class ProgressiveDisclosureEngine:
    """
    Main engine for progressive disclosure of UI features
    
    This engine analyzes user behavior, expertise level, and context to
    intelligently reveal new features at the optimal time for learning
    and productivity.
    """
    
    def __init__(self, interface_intelligence: InterfaceIntelligence):
        self.interface_intelligence = interface_intelligence
        self.features: Dict[str, Feature] = {}
        self.feature_usage: Dict[str, Dict[str, FeatureUsage]] = defaultdict(dict)
        self.disclosure_rules: List[DisclosureRule] = []
        self.learning_paths: Dict[str, LearningPath] = {}
        self.user_states: Dict[str, DisclosureState] = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize default features and rules
        self._initialize_default_features()
        self._initialize_default_rules()
        self._initialize_learning_paths()
    
    def _initialize_default_features(self):
        """Initialize a comprehensive set of default features"""
        default_features = [
            # Essential features - always visible
            Feature("save_document", "Save", "Save current document", 
                   FeatureComplexity.ESSENTIAL, "file_operations"),
            Feature("open_document", "Open", "Open existing document", 
                   FeatureComplexity.ESSENTIAL, "file_operations"),
            Feature("basic_edit", "Edit Text", "Basic text editing", 
                   FeatureComplexity.ESSENTIAL, "editing"),
            
            # Basic features
            Feature("undo_redo", "Undo/Redo", "Undo and redo actions", 
                   FeatureComplexity.BASIC, "editing", 
                   prerequisites=["basic_edit"], usage_threshold=3),
            Feature("find_replace", "Find & Replace", "Search and replace text", 
                   FeatureComplexity.BASIC, "editing",
                   prerequisites=["basic_edit"], usage_threshold=5),
            Feature("formatting", "Text Formatting", "Bold, italic, underline", 
                   FeatureComplexity.BASIC, "formatting",
                   prerequisites=["basic_edit"], usage_threshold=3),
            
            # Intermediate features
            Feature("advanced_formatting", "Advanced Formatting", "Styles, fonts, colors", 
                   FeatureComplexity.INTERMEDIATE, "formatting",
                   prerequisites=["formatting"], usage_threshold=8),
            Feature("keyboard_shortcuts", "Keyboard Shortcuts", "Efficiency shortcuts", 
                   FeatureComplexity.INTERMEDIATE, "productivity",
                   prerequisites=["undo_redo", "find_replace"], time_threshold_hours=5),
            Feature("templates", "Templates", "Document templates", 
                   FeatureComplexity.INTERMEDIATE, "productivity",
                   prerequisites=["save_document", "formatting"], usage_threshold=10),
            
            # Advanced features
            Feature("macros", "Macros", "Automated action sequences", 
                   FeatureComplexity.ADVANCED, "automation",
                   prerequisites=["keyboard_shortcuts", "advanced_formatting"], 
                   usage_threshold=15, time_threshold_hours=10),
            Feature("scripting", "Scripting", "Custom scripts and automation", 
                   FeatureComplexity.ADVANCED, "automation",
                   prerequisites=["macros"], usage_threshold=20),
            Feature("plugin_system", "Plugins", "Third-party extensions", 
                   FeatureComplexity.ADVANCED, "extensibility",
                   prerequisites=["templates", "macros"], usage_threshold=25),
            
            # Expert features
            Feature("api_access", "API Access", "Programmatic interface", 
                   FeatureComplexity.EXPERT, "technical",
                   prerequisites=["scripting", "plugin_system"], 
                   usage_threshold=30, time_threshold_hours=20),
            Feature("advanced_debugging", "Debug Tools", "Advanced debugging capabilities", 
                   FeatureComplexity.EXPERT, "technical",
                   prerequisites=["scripting"], usage_threshold=25),
        ]
        
        for feature in default_features:
            self.features[feature.feature_id] = feature
    
    def _initialize_default_rules(self):
        """Initialize default disclosure rules"""
        self.disclosure_rules = [
            # Time-based rules for gradual revelation
            DisclosureRule("keyboard_shortcuts", DisclosureStrategy.TIME_BASED,
                         {"hours_threshold": 3}, priority=5),
            DisclosureRule("templates", DisclosureStrategy.SUCCESS_BASED,
                         {"success_rate_threshold": 0.8, "usage_threshold": 8}, priority=4),
            
            # Context-based rules
            DisclosureRule("find_replace", DisclosureStrategy.CONTEXT_BASED,
                         {"contexts": [InteractionContext.PRODUCTIVE, InteractionContext.FOCUSED]}, priority=3),
            DisclosureRule("advanced_formatting", DisclosureStrategy.USAGE_BASED,
                         {"prerequisite_mastery": True}, priority=3),
            
            # Request-based rules (respond to user searching/asking)
            DisclosureRule("macros", DisclosureStrategy.REQUEST_BASED,
                         {"keywords": ["automate", "repeat", "macro", "batch"]}, priority=2),
        ]
    
    def _initialize_learning_paths(self):
        """Initialize structured learning paths"""
        self.learning_paths = {
            "beginner_path": LearningPath(
                "beginner_path", "Getting Started", 
                "Essential features for new users",
                ["save_document", "open_document", "basic_edit", "undo_redo", "formatting"],
                2, [FeatureComplexity.ESSENTIAL, FeatureComplexity.BASIC]
            ),
            "productivity_path": LearningPath(
                "productivity_path", "Productivity Booster",
                "Features to speed up your work",
                ["keyboard_shortcuts", "templates", "find_replace", "advanced_formatting"],
                5, [FeatureComplexity.BASIC, FeatureComplexity.INTERMEDIATE]
            ),
            "power_user_path": LearningPath(
                "power_user_path", "Power User",
                "Advanced automation and customization",
                ["macros", "scripting", "plugin_system", "advanced_debugging"],
                10, [FeatureComplexity.ADVANCED, FeatureComplexity.EXPERT]
            ),
        }
    
    async def record_feature_usage(self, user_id: str, feature_id: str, 
                                 duration: float = None, success: bool = True,
                                 context: InteractionContext = None) -> None:
        """Record usage of a feature for progressive disclosure analysis"""
        if user_id not in self.feature_usage:
            self.feature_usage[user_id] = {}
        
        if feature_id not in self.feature_usage[user_id]:
            self.feature_usage[user_id][feature_id] = FeatureUsage(feature_id)
        
        usage = self.feature_usage[user_id][feature_id]
        usage.total_uses += 1
        if success:
            usage.successful_uses += 1
        
        now = datetime.utcnow()
        if usage.first_used is None:
            usage.first_used = now
        usage.last_used = now
        
        if duration is not None:
            # Update running average
            if usage.average_duration == 0:
                usage.average_duration = duration
            else:
                usage.average_duration = (usage.average_duration * (usage.total_uses - 1) + duration) / usage.total_uses
        
        if context:
            usage.contexts_used.add(context)
        
        # Check if this usage triggers new feature revelations
        await self._evaluate_disclosure_triggers(user_id, feature_id)
    
    async def _evaluate_disclosure_triggers(self, user_id: str, recently_used_feature: str) -> None:
        """Evaluate if recent usage should trigger disclosure of new features"""
        user_profile = await self.interface_intelligence.get_user_profile(user_id)
        if not user_profile:
            return
        
        # Get current disclosure state
        if user_id not in self.user_states:
            self.user_states[user_id] = DisclosureState(user_id)
        
        state = self.user_states[user_id]
        
        # Check each undisclosed feature
        for feature_id, feature in self.features.items():
            if (feature_id in state.revealed_features or 
                feature_id in state.hidden_features):
                continue
            
            readiness = await self._evaluate_feature_readiness(user_id, feature_id, user_profile)
            
            if readiness == FeatureReadiness.READY:
                await self._suggest_feature(user_id, feature_id)
            elif readiness == FeatureReadiness.SUGGESTED:
                # Feature was already suggested, check if conditions are met for auto-reveal
                if await self._should_auto_reveal(user_id, feature_id):
                    await self._reveal_feature(user_id, feature_id)
    
    async def _evaluate_feature_readiness(self, user_id: str, feature_id: str, 
                                        user_profile: UserProfile) -> FeatureReadiness:
        """Evaluate if a user is ready for a specific feature"""
        feature = self.features.get(feature_id)
        if not feature:
            return FeatureReadiness.NOT_READY
        
        # Check complexity vs expertise level
        if not self._complexity_matches_expertise(feature.complexity, user_profile.expertise_level):
            return FeatureReadiness.NOT_READY
        
        # Check prerequisites
        if not await self._prerequisites_met(user_id, feature):
            return FeatureReadiness.NOT_READY
        
        # Check time threshold
        if not self._time_threshold_met(user_id, feature):
            return FeatureReadiness.NOT_READY
        
        # Apply disclosure rules
        for rule in sorted(self.disclosure_rules, key=lambda r: r.priority, reverse=True):
            if rule.feature_id == feature_id and rule.active:
                if await self._rule_conditions_met(user_id, rule, user_profile):
                    return FeatureReadiness.READY
        
        # Default readiness based on prerequisites and thresholds
        if (await self._prerequisites_met(user_id, feature) and 
            self._time_threshold_met(user_id, feature)):
            return FeatureReadiness.READY
        
        return FeatureReadiness.NOT_READY
    
    def _complexity_matches_expertise(self, complexity: FeatureComplexity, 
                                    expertise: ExpertiseLevel) -> bool:
        """Check if feature complexity is appropriate for user expertise"""
        complexity_map = {
            FeatureComplexity.ESSENTIAL: [ExpertiseLevel.BEGINNER, ExpertiseLevel.INTERMEDIATE, 
                                        ExpertiseLevel.ADVANCED, ExpertiseLevel.EXPERT],
            FeatureComplexity.BASIC: [ExpertiseLevel.BEGINNER, ExpertiseLevel.INTERMEDIATE,
                                    ExpertiseLevel.ADVANCED, ExpertiseLevel.EXPERT],
            FeatureComplexity.INTERMEDIATE: [ExpertiseLevel.INTERMEDIATE, ExpertiseLevel.ADVANCED, 
                                           ExpertiseLevel.EXPERT],
            FeatureComplexity.ADVANCED: [ExpertiseLevel.ADVANCED, ExpertiseLevel.EXPERT],
            FeatureComplexity.EXPERT: [ExpertiseLevel.EXPERT]
        }
        
        return expertise in complexity_map.get(complexity, [])
    
    async def _prerequisites_met(self, user_id: str, feature: Feature) -> bool:
        """Check if all prerequisites for a feature are met"""
        if not feature.prerequisites:
            return True
        
        user_usage = self.feature_usage.get(user_id, {})
        
        for prereq_id in feature.prerequisites:
            usage = user_usage.get(prereq_id)
            if not usage:
                return False
            
            if usage.total_uses < feature.usage_threshold:
                return False
            
            if usage.success_rate < feature.success_threshold:
                return False
        
        return True
    
    def _time_threshold_met(self, user_id: str, feature: Feature) -> bool:
        """Check if user has spent enough time in system for this feature"""
        if feature.time_threshold_hours <= 0:
            return True
        
        user_usage = self.feature_usage.get(user_id, {})
        if not user_usage:
            return False
        
        # Calculate total time spent (approximate from usage data)
        total_time_hours = 0
        for usage in user_usage.values():
            if usage.first_used and usage.last_used:
                session_hours = (usage.last_used - usage.first_used).total_seconds() / 3600
                total_time_hours += min(session_hours, usage.total_uses * 0.5)  # Cap per feature
        
        return total_time_hours >= feature.time_threshold_hours
    
    async def _rule_conditions_met(self, user_id: str, rule: DisclosureRule, 
                                 user_profile: UserProfile) -> bool:
        """Check if a disclosure rule's conditions are met"""
        conditions = rule.conditions
        
        if rule.strategy == DisclosureStrategy.TIME_BASED:
            hours_threshold = conditions.get("hours_threshold", 0)
            return self._get_user_hours(user_id) >= hours_threshold
        
        elif rule.strategy == DisclosureStrategy.SUCCESS_BASED:
            success_threshold = conditions.get("success_rate_threshold", 0.8)
            usage_threshold = conditions.get("usage_threshold", 5)
            
            total_uses = sum(usage.total_uses for usage in self.feature_usage.get(user_id, {}).values())
            if total_uses < usage_threshold:
                return False
            
            total_success = sum(usage.successful_uses for usage in self.feature_usage.get(user_id, {}).values())
            return (total_success / total_uses) >= success_threshold
        
        elif rule.strategy == DisclosureStrategy.CONTEXT_BASED:
            required_contexts = set(conditions.get("contexts", []))
            recent_events = await self.interface_intelligence.get_recent_interactions(user_id, 30)
            user_contexts = set()
            
            for event in recent_events[-10:]:  # Check last 10 interactions
                context = await self.interface_intelligence.context_detector.detect_current_context([event])
                user_contexts.add(context)
            
            return bool(required_contexts.intersection(user_contexts))
        
        elif rule.strategy == DisclosureStrategy.USAGE_BASED:
            if conditions.get("prerequisite_mastery"):
                feature = self.features.get(rule.feature_id)
                return await self._prerequisites_met(user_id, feature) if feature else False
        
        return False
    
    def _get_user_hours(self, user_id: str) -> float:
        """Calculate approximate hours user has spent in system"""
        user_usage = self.feature_usage.get(user_id, {})
        total_hours = 0
        
        for usage in user_usage.values():
            if usage.first_used and usage.last_used:
                session_hours = (usage.last_used - usage.first_used).total_seconds() / 3600
                total_hours += min(session_hours, usage.total_uses * 0.5)
        
        return total_hours
    
    async def _suggest_feature(self, user_id: str, feature_id: str) -> None:
        """Suggest a feature to the user"""
        if user_id not in self.user_states:
            self.user_states[user_id] = DisclosureState(user_id)
        
        self.user_states[user_id].suggested_features.add(feature_id)
        
        self.logger.info(f"Suggested feature {feature_id} to user {user_id}")
    
    async def _reveal_feature(self, user_id: str, feature_id: str) -> None:
        """Reveal a feature to the user"""
        if user_id not in self.user_states:
            self.user_states[user_id] = DisclosureState(user_id)
        
        state = self.user_states[user_id]
        state.revealed_features.add(feature_id)
        state.suggested_features.discard(feature_id)
        
        self.logger.info(f"Revealed feature {feature_id} to user {user_id}")
    
    async def _should_auto_reveal(self, user_id: str, feature_id: str) -> bool:
        """Determine if a suggested feature should be automatically revealed"""
        # For now, don't auto-reveal - let user choose
        # In the future, this could be based on continued usage patterns
        return False
    
    async def get_interface_configuration(self, user_id: str, 
                                        context: InteractionContext = None) -> Dict[str, Any]:
        """
        Generate interface configuration based on progressive disclosure state
        
        Returns configuration specifying which features should be visible,
        suggested, or hidden in the current context.
        """
        if user_id not in self.user_states:
            self.user_states[user_id] = DisclosureState(user_id)
        
        state = self.user_states[user_id]
        user_profile = await self.interface_intelligence.get_user_profile(user_id)
        
        config = {
            "visible_features": [],
            "suggested_features": [],
            "hidden_features": [],
            "feature_groups": defaultdict(list),
            "disclosure_hints": {},
            "learning_suggestions": []
        }
        
        # Always show essential features
        for feature_id, feature in self.features.items():
            if feature.complexity == FeatureComplexity.ESSENTIAL:
                config["visible_features"].append(feature_id)
                config["feature_groups"][feature.category].append({
                    "feature_id": feature_id,
                    "name": feature.name,
                    "description": feature.description,
                    "complexity": feature.complexity.value
                })
        
        # Show revealed features
        for feature_id in state.revealed_features:
            if feature_id not in config["visible_features"]:
                feature = self.features[feature_id]
                config["visible_features"].append(feature_id)
                config["feature_groups"][feature.category].append({
                    "feature_id": feature_id,
                    "name": feature.name,
                    "description": feature.description,
                    "complexity": feature.complexity.value
                })
        
        # Add suggested features
        for feature_id in state.suggested_features:
            feature = self.features[feature_id]
            config["suggested_features"].append({
                "feature_id": feature_id,
                "name": feature.name,
                "description": feature.description,
                "complexity": feature.complexity.value,
                "category": feature.category
            })
            config["disclosure_hints"][feature_id] = await self._generate_disclosure_hint(user_id, feature_id)
        
        # Add learning path suggestions
        if user_profile:
            config["learning_suggestions"] = await self._get_learning_suggestions(user_id, user_profile)
        
        # Hide explicitly hidden features
        config["hidden_features"] = list(state.hidden_features)
        
        return config
    
    async def _generate_disclosure_hint(self, user_id: str, feature_id: str) -> str:
        """Generate a helpful hint for why a feature is being suggested"""
        feature = self.features[feature_id]
        user_usage = self.feature_usage.get(user_id, {})
        
        # Check what prerequisites are mastered
        mastered_prereqs = []
        for prereq_id in feature.prerequisites:
            usage = user_usage.get(prereq_id)
            if usage and usage.is_mastered:
                mastered_prereqs.append(self.features[prereq_id].name)
        
        if mastered_prereqs:
            return f"Since you've mastered {', '.join(mastered_prereqs)}, you might find {feature.name} useful for {feature.description.lower()}"
        else:
            return f"{feature.name} can help with {feature.description.lower()}"
    
    async def _get_learning_suggestions(self, user_id: str, user_profile: UserProfile) -> List[Dict[str, Any]]:
        """Get personalized learning path suggestions"""
        suggestions = []
        state = self.user_states.get(user_id)
        
        for path_id, path in self.learning_paths.items():
            if state and path_id in state.completed_paths:
                continue
            
            # Check if user is ready for this path
            if self._is_ready_for_path(user_profile.expertise_level, path):
                progress = self._calculate_path_progress(user_id, path)
                suggestions.append({
                    "path_id": path_id,
                    "name": path.name,
                    "description": path.description,
                    "progress": progress,
                    "estimated_hours": path.estimated_duration_hours,
                    "next_feature": self._get_next_path_feature(user_id, path)
                })
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def _is_ready_for_path(self, expertise: ExpertiseLevel, path: LearningPath) -> bool:
        """Check if user expertise level matches learning path"""
        path_complexity = path.difficulty_progression[0] if path.difficulty_progression else FeatureComplexity.BASIC
        return self._complexity_matches_expertise(path_complexity, expertise)
    
    def _calculate_path_progress(self, user_id: str, path: LearningPath) -> float:
        """Calculate user's progress through a learning path"""
        user_usage = self.feature_usage.get(user_id, {})
        mastered_features = 0
        
        for feature_id in path.features:
            usage = user_usage.get(feature_id)
            if usage and usage.is_mastered:
                mastered_features += 1
        
        return mastered_features / len(path.features) if path.features else 0.0
    
    def _get_next_path_feature(self, user_id: str, path: LearningPath) -> Optional[str]:
        """Get the next feature to learn in a path"""
        user_usage = self.feature_usage.get(user_id, {})
        
        for feature_id in path.features:
            usage = user_usage.get(feature_id)
            if not usage or not usage.is_mastered:
                return feature_id
        
        return None
    
    async def accept_feature_suggestion(self, user_id: str, feature_id: str) -> bool:
        """User accepts a suggested feature - reveal it"""
        if user_id not in self.user_states:
            return False
        
        state = self.user_states[user_id]
        if feature_id in state.suggested_features:
            await self._reveal_feature(user_id, feature_id)
            return True
        
        return False
    
    async def dismiss_feature_suggestion(self, user_id: str, feature_id: str, 
                                       hide_permanently: bool = False) -> bool:
        """User dismisses a suggested feature"""
        if user_id not in self.user_states:
            return False
        
        state = self.user_states[user_id]
        if feature_id in state.suggested_features:
            state.suggested_features.discard(feature_id)
            if hide_permanently:
                state.hidden_features.add(feature_id)
            return True
        
        return False
    
    async def toggle_feature_visibility(self, user_id: str, feature_id: str) -> bool:
        """Toggle visibility of a feature (show/hide)"""
        if user_id not in self.user_states:
            self.user_states[user_id] = DisclosureState(user_id)
        
        state = self.user_states[user_id]
        
        if feature_id in state.hidden_features:
            state.hidden_features.discard(feature_id)
            state.revealed_features.add(feature_id)
        elif feature_id in state.revealed_features:
            state.revealed_features.discard(feature_id)
            state.hidden_features.add(feature_id)
        else:
            # Feature not yet revealed, reveal it
            state.revealed_features.add(feature_id)
        
        state.customization_level += 1
        return True
    
    async def start_learning_path(self, user_id: str, path_id: str) -> bool:
        """Start a user on a specific learning path"""
        if path_id not in self.learning_paths:
            return False
        
        if user_id not in self.user_states:
            self.user_states[user_id] = DisclosureState(user_id)
        
        self.user_states[user_id].current_path = path_id
        
        # Reveal the first feature in the path if not already visible
        path = self.learning_paths[path_id]
        if path.features:
            first_feature = path.features[0]
            await self._reveal_feature(user_id, first_feature)
        
        return True
    
    def get_feature_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics about feature usage and disclosure effectiveness"""
        user_usage = self.feature_usage.get(user_id, {})
        state = self.user_states.get(user_id)
        
        analytics = {
            "total_features_used": len(user_usage),
            "features_mastered": sum(1 for usage in user_usage.values() if usage.is_mastered),
            "total_interactions": sum(usage.total_uses for usage in user_usage.values()),
            "overall_success_rate": 0.0,
            "complexity_distribution": defaultdict(int),
            "category_usage": defaultdict(int),
            "disclosure_effectiveness": {
                "suggestions_made": len(state.suggested_features) if state else 0,
                "suggestions_accepted": 0,
                "features_revealed": len(state.revealed_features) if state else 0,
                "customization_level": state.customization_level if state else 0
            }
        }
        
        if user_usage:
            total_uses = sum(usage.total_uses for usage in user_usage.values())
            total_successes = sum(usage.successful_uses for usage in user_usage.values())
            analytics["overall_success_rate"] = total_successes / total_uses if total_uses > 0 else 0.0
        
        # Analyze complexity and category distribution
        for feature_id, usage in user_usage.items():
            feature = self.features.get(feature_id)
            if feature:
                analytics["complexity_distribution"][feature.complexity.value] += usage.total_uses
                analytics["category_usage"][feature.category] += usage.total_uses
        
        return analytics