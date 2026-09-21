"""
ActiveLog Project Memory - Advanced Bot Profiling and Learning System
AI-powered bot behavior analysis, learning, and optimization
"""

from typing import Dict, List, Any, Optional, Tuple, Set, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import numpy as np
import time
import hashlib
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter, deque
import statistics
import pickle

class BotCapability(Enum):
    """Bot capability levels"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate" 
    ADVANCED = "advanced"
    EXPERT = "expert"
    SPECIALIZED = "specialized"

class LearningStyle(Enum):
    """Different learning styles for bots"""
    SEQUENTIAL = "sequential"      # Prefers step-by-step information
    CONTEXTUAL = "contextual"      # Needs full context before proceeding
    EXPLORATORY = "exploratory"    # Likes to explore related concepts
    FOCUSED = "focused"           # Prefers direct, specific information
    ANALYTICAL = "analytical"     # Needs detailed technical information

class TaskPreference(Enum):
    """Types of tasks bots prefer"""
    CODE_GENERATION = "code_generation"
    PROBLEM_SOLVING = "problem_solving"
    RESEARCH = "research"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    ANALYSIS = "analysis"

@dataclass
class InteractionPattern:
    """Pattern of bot interaction"""
    pattern_id: str
    frequency: int
    success_rate: float
    average_duration: float
    complexity_level: float
    context_switches: int
    follow_up_questions: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BotBehaviorProfile:
    """Comprehensive bot behavior profile"""
    bot_id: str
    bot_type: str
    capability_level: BotCapability
    learning_style: LearningStyle
    task_preferences: Dict[TaskPreference, float]  # Preference scores
    
    # Performance metrics
    average_session_duration: float = 0.0
    context_efficiency: float = 0.0  # How efficiently bot uses context
    learning_speed: float = 0.0      # How quickly bot adapts
    collaboration_score: float = 0.0 # How well bot works with others
    
    # Interaction patterns
    common_patterns: List[InteractionPattern] = field(default_factory=list)
    failure_patterns: List[InteractionPattern] = field(default_factory=list)
    
    # Preferences and behaviors
    preferred_context_size: int = 4000
    preferred_explanation_depth: str = "medium"
    retry_tolerance: int = 3
    complexity_comfort_zone: Tuple[float, float] = (0.3, 0.7)
    
    # Learning and adaptation
    adaptation_rate: float = 0.1
    memory_retention: float = 0.8
    pattern_recognition_threshold: float = 0.6
    
    # Statistics
    total_interactions: int = 0
    successful_interactions: int = 0
    failed_interactions: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Temporal patterns
    active_hours: Dict[int, float] = field(default_factory=dict)  # Hour -> activity level
    active_days: Dict[int, float] = field(default_factory=dict)   # Day -> activity level

class BotInteraction:
    """Single bot interaction for analysis"""
    
    def __init__(self, bot_id: str, session_id: str):
        self.bot_id = bot_id
        self.session_id = session_id
        self.start_time = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        
        # Interaction data
        self.concepts_accessed: List[str] = []
        self.search_queries: List[str] = []
        self.context_requests: List[Dict[str, Any]] = []
        self.errors_encountered: List[str] = []
        self.successful_completions: List[str] = []
        
        # Behavioral metrics
        self.context_switches: int = 0
        self.follow_up_questions: int = 0
        self.retry_attempts: int = 0
        self.help_requests: int = 0
        
        # Performance metrics
        self.response_times: List[float] = []
        self.satisfaction_score: Optional[float] = None
        self.completion_rate: float = 0.0
        
        # Metadata
        self.task_type: Optional[str] = None
        self.complexity_level: float = 0.5
        self.collaboration_partners: List[str] = []
    
    def end_interaction(self, success: bool = True):
        """Mark interaction as ended"""
        self.end_time = datetime.now(timezone.utc)
        if success:
            self.completion_rate = 1.0
        else:
            self.completion_rate = len(self.successful_completions) / max(1, 
                len(self.successful_completions) + len(self.errors_encountered))
    
    def get_duration(self) -> float:
        """Get interaction duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()
    
    def calculate_complexity(self) -> float:
        """Calculate complexity of the interaction"""
        complexity_factors = [
            len(self.concepts_accessed) * 0.1,
            len(self.search_queries) * 0.15,
            self.context_switches * 0.2,
            len(self.context_requests) * 0.1,
            self.retry_attempts * 0.25,
            len(self.errors_encountered) * 0.3
        ]
        
        return min(1.0, sum(complexity_factors))

class BotLearningEngine:
    """Machine learning engine for bot behavior optimization"""
    
    def __init__(self):
        self.learning_models = {}
        self.pattern_library = defaultdict(list)
        self.success_predictors = {}
        self.adaptation_rules = []
        
    def analyze_interaction_patterns(self, interactions: List[BotInteraction]) -> List[InteractionPattern]:
        """Analyze interactions to find patterns"""
        patterns = []
        
        if not interactions:
            return patterns
        
        # Group interactions by similarity
        pattern_groups = self._group_similar_interactions(interactions)
        
        for group_id, group_interactions in pattern_groups.items():
            if len(group_interactions) < 3:  # Need at least 3 occurrences
                continue
            
            # Calculate pattern metrics
            durations = [interaction.get_duration() for interaction in group_interactions]
            success_rates = [interaction.completion_rate for interaction in group_interactions]
            complexities = [interaction.calculate_complexity() for interaction in group_interactions]
            
            pattern = InteractionPattern(
                pattern_id=group_id,
                frequency=len(group_interactions),
                success_rate=statistics.mean(success_rates),
                average_duration=statistics.mean(durations),
                complexity_level=statistics.mean(complexities),
                context_switches=int(statistics.mean([i.context_switches for i in group_interactions])),
                follow_up_questions=int(statistics.mean([i.follow_up_questions for i in group_interactions])),
                metadata={
                    "common_concepts": self._find_common_concepts(group_interactions),
                    "common_errors": self._find_common_errors(group_interactions),
                    "task_types": list(set(i.task_type for i in group_interactions if i.task_type))
                }
            )
            
            patterns.append(pattern)
        
        return sorted(patterns, key=lambda p: p.frequency, reverse=True)
    
    def _group_similar_interactions(self, interactions: List[BotInteraction]) -> Dict[str, List[BotInteraction]]:
        """Group similar interactions together"""
        groups = defaultdict(list)
        
        for interaction in interactions:
            # Create a signature for grouping
            signature_elements = [
                interaction.task_type or "unknown",
                str(len(interaction.concepts_accessed) // 5),  # Quantized concept count
                str(len(interaction.search_queries) // 2),     # Quantized query count
                str(interaction.context_switches // 2),       # Quantized context switches
                "success" if interaction.completion_rate > 0.8 else "partial" if interaction.completion_rate > 0.3 else "failure"
            ]
            
            signature = "_".join(signature_elements)
            groups[signature].append(interaction)
        
        return groups
    
    def _find_common_concepts(self, interactions: List[BotInteraction]) -> List[str]:
        """Find concepts commonly accessed across interactions"""
        concept_counts = Counter()
        
        for interaction in interactions:
            for concept in interaction.concepts_accessed:
                concept_counts[concept] += 1
        
        # Return concepts that appear in at least 50% of interactions
        threshold = len(interactions) * 0.5
        return [concept for concept, count in concept_counts.items() if count >= threshold]
    
    def _find_common_errors(self, interactions: List[BotInteraction]) -> List[str]:
        """Find errors commonly encountered"""
        error_counts = Counter()
        
        for interaction in interactions:
            for error in interaction.errors_encountered:
                error_counts[error] += 1
        
        return [error for error, count in error_counts.most_common(5)]
    
    def predict_success_probability(self, bot_profile: BotBehaviorProfile,
                                  task_context: Dict[str, Any]) -> float:
        """Predict probability of success for a task"""
        
        # Base probability from historical success rate
        if bot_profile.total_interactions > 0:
            base_probability = bot_profile.successful_interactions / bot_profile.total_interactions
        else:
            base_probability = 0.5
        
        # Adjust based on task type preference
        task_type = task_context.get("task_type")
        if task_type and hasattr(TaskPreference, task_type.upper()):
            task_pref = TaskPreference(task_type.lower())
            preference_score = bot_profile.task_preferences.get(task_pref, 0.5)
            base_probability = base_probability * 0.7 + preference_score * 0.3
        
        # Adjust based on complexity
        task_complexity = task_context.get("complexity", 0.5)
        comfort_min, comfort_max = bot_profile.complexity_comfort_zone
        
        if comfort_min <= task_complexity <= comfort_max:
            complexity_modifier = 1.1  # Comfortable with this complexity
        elif task_complexity < comfort_min:
            complexity_modifier = 0.9  # Might be too simple
        else:
            complexity_modifier = max(0.3, 1.0 - (task_complexity - comfort_max) * 2)
        
        adjusted_probability = base_probability * complexity_modifier
        
        # Adjust based on context size
        context_size = task_context.get("context_size", 2000)
        optimal_size = bot_profile.preferred_context_size
        
        if abs(context_size - optimal_size) > optimal_size * 0.5:
            context_modifier = 0.85
        else:
            context_modifier = 1.0
        
        final_probability = min(1.0, max(0.0, adjusted_probability * context_modifier))
        
        return final_probability
    
    def recommend_optimizations(self, bot_profile: BotBehaviorProfile) -> List[Dict[str, Any]]:
        """Recommend optimizations for bot performance"""
        recommendations = []
        
        # Check success rate
        if bot_profile.total_interactions > 10:
            success_rate = bot_profile.successful_interactions / bot_profile.total_interactions
            
            if success_rate < 0.7:
                recommendations.append({
                    "type": "performance",
                    "priority": "high",
                    "suggestion": "Consider adjusting task complexity or providing more context",
                    "reasoning": f"Success rate is {success_rate:.2%}, below optimal threshold"
                })
        
        # Check context efficiency
        if bot_profile.context_efficiency < 0.6:
            recommendations.append({
                "type": "context",
                "priority": "medium", 
                "suggestion": "Optimize context loading strategy",
                "reasoning": "Bot is not efficiently utilizing available context"
            })
        
        # Check learning speed
        if bot_profile.learning_speed < 0.3:
            recommendations.append({
                "type": "learning",
                "priority": "medium",
                "suggestion": "Increase pattern recognition sensitivity",
                "reasoning": "Bot is slow to adapt to new patterns"
            })
        
        # Check failure patterns
        if bot_profile.failure_patterns:
            high_frequency_failures = [p for p in bot_profile.failure_patterns if p.frequency > 5]
            if high_frequency_failures:
                recommendations.append({
                    "type": "failure_prevention",
                    "priority": "high",
                    "suggestion": "Address recurring failure patterns",
                    "reasoning": f"Found {len(high_frequency_failures)} high-frequency failure patterns",
                    "patterns": [p.pattern_id for p in high_frequency_failures]
                })
        
        return recommendations

class AdvancedBotProfiler:
    """
    Advanced bot profiling system with machine learning and optimization
    """
    
    def __init__(self, max_profiles: int = 10000):
        self.max_profiles = max_profiles
        self.bot_profiles: Dict[str, BotBehaviorProfile] = {}
        self.active_interactions: Dict[str, BotInteraction] = {}
        self.learning_engine = BotLearningEngine()
        
        # Analytics and tracking
        self.interaction_history: deque = deque(maxlen=100000)  # Keep recent interactions
        self.profile_updates: deque = deque(maxlen=10000)       # Track profile changes
        
        # Performance metrics
        self.profiler_stats = {
            "profiles_created": 0,
            "interactions_tracked": 0,
            "patterns_discovered": 0,
            "optimizations_suggested": 0
        }
        
        # Learning parameters
        self.min_interactions_for_profile = 5
        self.pattern_discovery_threshold = 3
        self.profile_update_frequency = timedelta(hours=1)
        
    async def start_interaction(self, bot_id: str, session_id: str,
                              task_context: Dict[str, Any]) -> str:
        """Start tracking a new bot interaction"""
        
        interaction = BotInteraction(bot_id, session_id)
        interaction.task_type = task_context.get("task_type")
        interaction.complexity_level = task_context.get("complexity", 0.5)
        
        interaction_key = f"{bot_id}_{session_id}"
        self.active_interactions[interaction_key] = interaction
        
        # Initialize profile if doesn't exist
        if bot_id not in self.bot_profiles:
            await self._create_bot_profile(bot_id, task_context)
        
        return interaction_key
    
    async def record_concept_access(self, interaction_key: str, concept_id: str,
                                  access_time: float, success: bool = True):
        """Record concept access during interaction"""
        
        if interaction_key not in self.active_interactions:
            return
        
        interaction = self.active_interactions[interaction_key]
        interaction.concepts_accessed.append(concept_id)
        interaction.response_times.append(access_time)
        
        if success:
            interaction.successful_completions.append(concept_id)
        else:
            interaction.errors_encountered.append(f"concept_access_failed_{concept_id}")
    
    async def record_search_query(self, interaction_key: str, query: str,
                                results_count: int, response_time: float):
        """Record search query during interaction"""
        
        if interaction_key not in self.active_interactions:
            return
        
        interaction = self.active_interactions[interaction_key]
        interaction.search_queries.append(query)
        interaction.response_times.append(response_time)
        
        if results_count == 0:
            interaction.errors_encountered.append(f"search_no_results_{query}")
    
    async def record_context_request(self, interaction_key: str, request_type: str,
                                   context_size: int, successful: bool = True):
        """Record context request during interaction"""
        
        if interaction_key not in self.active_interactions:
            return
        
        interaction = self.active_interactions[interaction_key]
        
        context_request = {
            "type": request_type,
            "size": context_size,
            "timestamp": datetime.now(timezone.utc),
            "successful": successful
        }
        
        interaction.context_requests.append(context_request)
        
        if request_type == "context_switch":
            interaction.context_switches += 1
        elif request_type == "follow_up":
            interaction.follow_up_questions += 1
        elif request_type == "retry":
            interaction.retry_attempts += 1
        elif request_type == "help":
            interaction.help_requests += 1
    
    async def end_interaction(self, interaction_key: str, success: bool = True,
                            satisfaction_score: Optional[float] = None):
        """End and analyze a bot interaction"""
        
        if interaction_key not in self.active_interactions:
            return
        
        interaction = self.active_interactions[interaction_key]
        interaction.end_interaction(success)
        interaction.satisfaction_score = satisfaction_score
        
        # Add to history
        self.interaction_history.append(interaction)
        self.profiler_stats["interactions_tracked"] += 1
        
        # Update bot profile
        await self._update_bot_profile(interaction)
        
        # Clean up active interaction
        del self.active_interactions[interaction_key]
    
    async def _create_bot_profile(self, bot_id: str, initial_context: Dict[str, Any]):
        """Create initial bot profile"""
        
        # Determine capability level from context
        capability = BotCapability.INTERMEDIATE  # Default
        if "capability" in initial_context:
            try:
                capability = BotCapability(initial_context["capability"])
            except ValueError:
                pass
        
        # Determine learning style (simplified heuristic)
        learning_style = LearningStyle.CONTEXTUAL  # Default
        bot_type = initial_context.get("bot_type", "").lower()
        
        if "expert" in bot_type:
            learning_style = LearningStyle.ANALYTICAL
        elif "simple" in bot_type:
            learning_style = LearningStyle.SEQUENTIAL
        elif "explore" in bot_type:
            learning_style = LearningStyle.EXPLORATORY
        elif "focus" in bot_type:
            learning_style = LearningStyle.FOCUSED
        
        # Initialize task preferences (all equal initially)
        task_preferences = {task: 0.5 for task in TaskPreference}
        
        profile = BotBehaviorProfile(
            bot_id=bot_id,
            bot_type=bot_type,
            capability_level=capability,
            learning_style=learning_style,
            task_preferences=task_preferences
        )
        
        self.bot_profiles[bot_id] = profile
        self.profiler_stats["profiles_created"] += 1
    
    async def _update_bot_profile(self, interaction: BotInteraction):
        """Update bot profile based on interaction"""
        
        if interaction.bot_id not in self.bot_profiles:
            return
        
        profile = self.bot_profiles[interaction.bot_id]
        
        # Update basic statistics
        profile.total_interactions += 1
        if interaction.completion_rate > 0.8:
            profile.successful_interactions += 1
        else:
            profile.failed_interactions += 1
        
        # Update session duration (running average)
        duration = interaction.get_duration()
        if profile.average_session_duration == 0:
            profile.average_session_duration = duration
        else:
            profile.average_session_duration = (
                profile.average_session_duration * 0.9 + duration * 0.1
            )
        
        # Update context efficiency
        if interaction.context_requests:
            successful_requests = sum(1 for req in interaction.context_requests if req["successful"])
            efficiency = successful_requests / len(interaction.context_requests)
            
            if profile.context_efficiency == 0:
                profile.context_efficiency = efficiency
            else:
                profile.context_efficiency = profile.context_efficiency * 0.9 + efficiency * 0.1
        
        # Update task preferences
        if interaction.task_type:
            try:
                task_pref = TaskPreference(interaction.task_type.lower())
                current_score = profile.task_preferences.get(task_pref, 0.5)
                
                # Increase preference for successful tasks, decrease for failed ones
                adjustment = 0.1 if interaction.completion_rate > 0.8 else -0.05
                new_score = max(0.0, min(1.0, current_score + adjustment))
                profile.task_preferences[task_pref] = new_score
                
            except ValueError:
                pass  # Unknown task type
        
        # Update temporal patterns
        interaction_hour = interaction.start_time.hour
        interaction_day = interaction.start_time.weekday()
        
        if interaction_hour not in profile.active_hours:
            profile.active_hours[interaction_hour] = 1
        else:
            profile.active_hours[interaction_hour] += 1
        
        if interaction_day not in profile.active_days:
            profile.active_days[interaction_day] = 1
        else:
            profile.active_days[interaction_day] += 1
        
        # Update complexity comfort zone based on success
        if interaction.completion_rate > 0.8:
            complexity = interaction.calculate_complexity()
            current_min, current_max = profile.complexity_comfort_zone
            
            # Expand comfort zone towards successful complexity levels
            expansion_rate = 0.05
            if complexity < current_min:
                new_min = current_min - (current_min - complexity) * expansion_rate
                profile.complexity_comfort_zone = (new_min, current_max)
            elif complexity > current_max:
                new_max = current_max + (complexity - current_max) * expansion_rate
                profile.complexity_comfort_zone = (current_min, new_max)
        
        profile.last_updated = datetime.now(timezone.utc)
        
        # Periodic pattern analysis
        if profile.total_interactions % 10 == 0:
            await self._analyze_bot_patterns(profile)
    
    async def _analyze_bot_patterns(self, profile: BotBehaviorProfile):
        """Analyze patterns for a specific bot"""
        
        # Get recent interactions for this bot
        bot_interactions = [
            interaction for interaction in self.interaction_history
            if interaction.bot_id == profile.bot_id
        ][-50:]  # Last 50 interactions
        
        if len(bot_interactions) < self.pattern_discovery_threshold:
            return
        
        # Analyze patterns
        patterns = self.learning_engine.analyze_interaction_patterns(bot_interactions)
        
        # Separate success and failure patterns
        success_patterns = [p for p in patterns if p.success_rate > 0.8]
        failure_patterns = [p for p in patterns if p.success_rate < 0.5]
        
        profile.common_patterns = success_patterns[:10]  # Keep top 10
        profile.failure_patterns = failure_patterns[:5]   # Keep top 5
        
        self.profiler_stats["patterns_discovered"] += len(patterns)
    
    async def get_bot_profile(self, bot_id: str) -> Optional[BotBehaviorProfile]:
        """Get bot profile by ID"""
        return self.bot_profiles.get(bot_id)
    
    async def get_optimization_recommendations(self, bot_id: str) -> List[Dict[str, Any]]:
        """Get optimization recommendations for a bot"""
        
        if bot_id not in self.bot_profiles:
            return []
        
        profile = self.bot_profiles[bot_id]
        recommendations = self.learning_engine.recommend_optimizations(profile)
        
        self.profiler_stats["optimizations_suggested"] += len(recommendations)
        
        return recommendations
    
    async def predict_task_success(self, bot_id: str, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Predict success probability for a bot on a specific task"""
        
        if bot_id not in self.bot_profiles:
            return {
                "success_probability": 0.5,
                "confidence": 0.0,
                "reasoning": "No profile available for bot"
            }
        
        profile = self.bot_profiles[bot_id]
        probability = self.learning_engine.predict_success_probability(profile, task_context)
        
        # Calculate confidence based on profile maturity
        confidence = min(1.0, profile.total_interactions / 50.0)  # Max confidence at 50+ interactions
        
        # Generate reasoning
        reasoning_factors = []
        
        if profile.total_interactions > 10:
            success_rate = profile.successful_interactions / profile.total_interactions
            reasoning_factors.append(f"Historical success rate: {success_rate:.1%}")
        
        task_type = task_context.get("task_type")
        if task_type:
            try:
                task_pref = TaskPreference(task_type.lower())
                pref_score = profile.task_preferences.get(task_pref, 0.5)
                reasoning_factors.append(f"Task preference score: {pref_score:.1%}")
            except ValueError:
                pass
        
        complexity = task_context.get("complexity", 0.5)
        comfort_min, comfort_max = profile.complexity_comfort_zone
        if comfort_min <= complexity <= comfort_max:
            reasoning_factors.append("Task complexity within comfort zone")
        else:
            reasoning_factors.append("Task complexity outside comfort zone")
        
        return {
            "success_probability": probability,
            "confidence": confidence,
            "reasoning": "; ".join(reasoning_factors),
            "factors": {
                "historical_success": profile.successful_interactions / max(1, profile.total_interactions),
                "task_preference": profile.task_preferences.get(TaskPreference(task_type.lower()), 0.5) if task_type else 0.5,
                "complexity_match": 1.0 if comfort_min <= complexity <= comfort_max else 0.5
            }
        }
    
    async def get_profile_analytics(self) -> Dict[str, Any]:
        """Get comprehensive profiler analytics"""
        
        # Calculate aggregate statistics
        total_bots = len(self.bot_profiles)
        
        if total_bots == 0:
            return {
                "total_bots": 0,
                "message": "No bot profiles available"
            }
        
        # Success rate statistics
        success_rates = []
        capability_distribution = Counter()
        learning_style_distribution = Counter()
        
        for profile in self.bot_profiles.values():
            if profile.total_interactions > 0:
                success_rate = profile.successful_interactions / profile.total_interactions
                success_rates.append(success_rate)
            
            capability_distribution[profile.capability_level.value] += 1
            learning_style_distribution[profile.learning_style.value] += 1
        
        # Calculate averages
        avg_success_rate = statistics.mean(success_rates) if success_rates else 0
        avg_session_duration = statistics.mean([
            p.average_session_duration for p in self.bot_profiles.values()
            if p.average_session_duration > 0
        ]) if any(p.average_session_duration > 0 for p in self.bot_profiles.values()) else 0
        
        # Top performing bots
        top_performers = sorted(
            self.bot_profiles.values(),
            key=lambda p: p.successful_interactions / max(1, p.total_interactions),
            reverse=True
        )[:5]
        
        return {
            "total_bots": total_bots,
            "total_interactions": sum(p.total_interactions for p in self.bot_profiles.values()),
            "average_success_rate": avg_success_rate,
            "average_session_duration": avg_session_duration,
            "capability_distribution": dict(capability_distribution),
            "learning_style_distribution": dict(learning_style_distribution),
            "top_performers": [
                {
                    "bot_id": p.bot_id,
                    "success_rate": p.successful_interactions / max(1, p.total_interactions),
                    "total_interactions": p.total_interactions
                }
                for p in top_performers
            ],
            "profiler_stats": self.profiler_stats,
            "active_interactions": len(self.active_interactions)
        }
    
    async def export_profiles(self, file_path: str) -> bool:
        """Export bot profiles to file"""
        try:
            export_data = {
                "profiles": {
                    bot_id: {
                        "bot_id": profile.bot_id,
                        "bot_type": profile.bot_type,
                        "capability_level": profile.capability_level.value,
                        "learning_style": profile.learning_style.value,
                        "task_preferences": {k.value: v for k, v in profile.task_preferences.items()},
                        "average_session_duration": profile.average_session_duration,
                        "context_efficiency": profile.context_efficiency,
                        "learning_speed": profile.learning_speed,
                        "total_interactions": profile.total_interactions,
                        "successful_interactions": profile.successful_interactions,
                        "last_updated": profile.last_updated.isoformat()
                    }
                    for bot_id, profile in self.bot_profiles.items()
                },
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "profiler_stats": self.profiler_stats
            }
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Failed to export profiles: {e}")
            return False
    
    async def import_profiles(self, file_path: str) -> bool:
        """Import bot profiles from file"""
        try:
            with open(file_path, 'r') as f:
                import_data = json.load(f)
            
            profiles_data = import_data.get("profiles", {})
            
            for bot_id, profile_data in profiles_data.items():
                # Reconstruct profile
                task_preferences = {
                    TaskPreference(k): v 
                    for k, v in profile_data["task_preferences"].items()
                }
                
                profile = BotBehaviorProfile(
                    bot_id=profile_data["bot_id"],
                    bot_type=profile_data["bot_type"],
                    capability_level=BotCapability(profile_data["capability_level"]),
                    learning_style=LearningStyle(profile_data["learning_style"]),
                    task_preferences=task_preferences
                )
                
                profile.average_session_duration = profile_data["average_session_duration"]
                profile.context_efficiency = profile_data["context_efficiency"]
                profile.learning_speed = profile_data["learning_speed"]
                profile.total_interactions = profile_data["total_interactions"]
                profile.successful_interactions = profile_data["successful_interactions"]
                profile.last_updated = datetime.fromisoformat(profile_data["last_updated"])
                
                self.bot_profiles[bot_id] = profile
            
            return True
            
        except Exception as e:
            print(f"Failed to import profiles: {e}")
            return False