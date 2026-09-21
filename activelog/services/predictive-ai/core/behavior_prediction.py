"""
Behavior Prediction Engine - Advanced AI system that learns user patterns and predicts future actions.
Uses machine learning to understand user behavior patterns and provide proactive suggestions.
"""

import asyncio
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import math
import random
from collections import defaultdict, deque

class ActionType(Enum):
    FILE_ACCESS = "file_access"
    FOLDER_CREATE = "folder_create"
    FILE_UPLOAD = "file_upload"
    SEARCH_QUERY = "search_query"
    MODULE_USE = "module_use"
    DATA_ENTRY = "data_entry"
    EXPORT_DATA = "export_data"
    SETTING_CHANGE = "setting_change"

class PredictionConfidence(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class UserAction:
    """Individual user action record."""
    user_id: str
    action_type: ActionType
    context: Dict[str, Any]
    timestamp: datetime
    session_id: str
    metadata: Dict[str, Any] = None

@dataclass
class BehaviorPattern:
    """Identified behavior pattern."""
    pattern_id: str
    user_id: str
    pattern_type: str
    frequency: float  # actions per day/week
    typical_times: List[int]  # hours of day
    typical_days: List[int]  # days of week
    context_triggers: List[str]
    confidence: float
    last_seen: datetime
    created_at: datetime

@dataclass
class Prediction:
    """Predicted user action or need."""
    user_id: str
    predicted_action: ActionType
    context: Dict[str, Any]
    confidence: PredictionConfidence
    predicted_time: datetime
    reasoning: str
    supporting_patterns: List[str]
    expires_at: datetime

class TemporalPatternAnalyzer:
    """Analyzes temporal patterns in user behavior."""
    
    def __init__(self):
        self.time_buckets = 24  # hourly buckets
        self.day_buckets = 7   # daily buckets
        
    def analyze_temporal_patterns(self, actions: List[UserAction]) -> Dict[str, Any]:
        """Analyze when user typically performs actions."""
        if not actions:
            return {}
        
        # Group by action type
        action_times = defaultdict(list)
        for action in actions:
            action_times[action.action_type.value].append(action.timestamp)
        
        patterns = {}
        for action_type, timestamps in action_times.items():
            patterns[action_type] = self._analyze_time_distribution(timestamps)
        
        return patterns
    
    def _analyze_time_distribution(self, timestamps: List[datetime]) -> Dict[str, Any]:
        """Analyze time distribution for specific action type."""
        if not timestamps:
            return {}
        
        # Hour of day analysis
        hours = [ts.hour for ts in timestamps]
        hour_distribution = np.histogram(hours, bins=24, range=(0, 24))[0]
        peak_hours = np.argsort(hour_distribution)[-3:].tolist()  # Top 3 hours
        
        # Day of week analysis
        days = [ts.weekday() for ts in timestamps]
        day_distribution = np.histogram(days, bins=7, range=(0, 7))[0]
        peak_days = np.argsort(day_distribution)[-3:].tolist()  # Top 3 days
        
        # Frequency analysis
        date_range = (max(timestamps) - min(timestamps)).days
        frequency = len(timestamps) / max(date_range, 1)
        
        return {
            "peak_hours": peak_hours,
            "peak_days": peak_days,
            "frequency_per_day": frequency,
            "total_occurrences": len(timestamps),
            "date_range_days": date_range,
            "hour_distribution": hour_distribution.tolist(),
            "day_distribution": day_distribution.tolist()
        }

class ContextualPatternAnalyzer:
    """Analyzes contextual patterns in user behavior."""
    
    def __init__(self):
        self.context_weights = {
            "location": 0.3,
            "previous_action": 0.4,
            "module_context": 0.2,
            "file_type": 0.1
        }
    
    def analyze_context_patterns(self, actions: List[UserAction]) -> Dict[str, Any]:
        """Analyze contextual triggers and sequences."""
        if len(actions) < 2:
            return {}
        
        # Sequence analysis
        sequences = self._extract_action_sequences(actions)
        
        # Context trigger analysis
        context_triggers = self._analyze_context_triggers(actions)
        
        # Co-occurrence analysis
        co_occurrences = self._analyze_co_occurrences(actions)
        
        return {
            "action_sequences": sequences,
            "context_triggers": context_triggers,
            "co_occurrences": co_occurrences
        }
    
    def _extract_action_sequences(self, actions: List[UserAction]) -> Dict[str, Any]:
        """Extract common action sequences."""
        sequences = defaultdict(int)
        
        # Look for 2-action sequences
        for i in range(len(actions) - 1):
            current = actions[i].action_type.value
            next_action = actions[i + 1].action_type.value
            
            # Only count if actions are within reasonable time window (1 hour)
            time_diff = (actions[i + 1].timestamp - actions[i].timestamp).total_seconds()
            if time_diff <= 3600:  # 1 hour
                sequences[f"{current} -> {next_action}"] += 1
        
        # Convert to probabilities
        total_sequences = sum(sequences.values())
        if total_sequences > 0:
            sequence_probs = {seq: count / total_sequences for seq, count in sequences.items()}
        else:
            sequence_probs = {}
        
        return {
            "sequences": dict(sequences),
            "probabilities": sequence_probs,
            "total_sequences": total_sequences
        }
    
    def _analyze_context_triggers(self, actions: List[UserAction]) -> Dict[str, Any]:
        """Analyze what contexts trigger specific actions."""
        context_action_map = defaultdict(lambda: defaultdict(int))
        
        for action in actions:
            action_type = action.action_type.value
            context = action.context
            
            # Extract key context features
            for key, value in context.items():
                if isinstance(value, (str, int, float)):
                    context_action_map[f"{key}:{value}"][action_type] += 1
        
        # Find strong correlations
        strong_triggers = {}
        for context_key, action_counts in context_action_map.items():
            total_actions = sum(action_counts.values())
            if total_actions >= 3:  # Minimum occurrence threshold
                dominant_action = max(action_counts.items(), key=lambda x: x[1])
                confidence = dominant_action[1] / total_actions
                if confidence >= 0.7:  # 70% confidence threshold
                    strong_triggers[context_key] = {
                        "action": dominant_action[0],
                        "confidence": confidence,
                        "occurrences": dominant_action[1]
                    }
        
        return strong_triggers
    
    def _analyze_co_occurrences(self, actions: List[UserAction]) -> Dict[str, Any]:
        """Analyze actions that frequently occur together."""
        # Group actions by session
        session_actions = defaultdict(list)
        for action in actions:
            session_actions[action.session_id].append(action.action_type.value)
        
        # Find co-occurrences within sessions
        co_occurrences = defaultdict(int)
        for session_id, action_types in session_actions.items():
            unique_actions = list(set(action_types))
            # Generate pairs
            for i, action1 in enumerate(unique_actions):
                for action2 in unique_actions[i + 1:]:
                    pair = tuple(sorted([action1, action2]))
                    co_occurrences[pair] += 1
        
        return dict(co_occurrences)

class PatternLearningEngine:
    """Machine learning engine for pattern recognition and prediction."""
    
    def __init__(self):
        self.min_pattern_occurrences = 3
        self.confidence_threshold = 0.6
        self.pattern_decay_days = 30
    
    def learn_patterns(self, user_id: str, actions: List[UserAction]) -> List[BehaviorPattern]:
        """Learn behavior patterns from user actions."""
        if len(actions) < self.min_pattern_occurrences:
            return []
        
        temporal_analyzer = TemporalPatternAnalyzer()
        contextual_analyzer = ContextualPatternAnalyzer()
        
        # Analyze patterns
        temporal_patterns = temporal_analyzer.analyze_temporal_patterns(actions)
        contextual_patterns = contextual_analyzer.analyze_context_patterns(actions)
        
        # Generate behavior patterns
        patterns = []
        
        # Create patterns for each action type
        for action_type, temporal_data in temporal_patterns.items():
            if temporal_data.get("total_occurrences", 0) >= self.min_pattern_occurrences:
                pattern = self._create_behavior_pattern(
                    user_id, action_type, temporal_data, contextual_patterns
                )
                if pattern:
                    patterns.append(pattern)
        
        return patterns
    
    def _create_behavior_pattern(self, user_id: str, action_type: str, 
                               temporal_data: Dict, contextual_data: Dict) -> Optional[BehaviorPattern]:
        """Create a behavior pattern from analyzed data."""
        
        # Calculate confidence based on frequency and consistency
        frequency = temporal_data.get("frequency_per_day", 0)
        occurrences = temporal_data.get("total_occurrences", 0)
        
        # Confidence based on regularity
        hour_distribution = np.array(temporal_data.get("hour_distribution", []))
        day_distribution = np.array(temporal_data.get("day_distribution", []))
        
        # Calculate entropy (lower entropy = more predictable)
        hour_entropy = self._calculate_entropy(hour_distribution)
        day_entropy = self._calculate_entropy(day_distribution)
        
        # Normalize entropy (0-1, where 1 is most predictable)
        max_hour_entropy = math.log(24)
        max_day_entropy = math.log(7)
        hour_predictability = 1 - (hour_entropy / max_hour_entropy)
        day_predictability = 1 - (day_entropy / max_day_entropy)
        
        # Overall confidence
        confidence = (hour_predictability + day_predictability) / 2
        confidence *= min(1.0, occurrences / 10)  # Scale by occurrence count
        
        if confidence < self.confidence_threshold:
            return None
        
        # Extract context triggers
        context_triggers = []
        for trigger, data in contextual_data.get("context_triggers", {}).items():
            if data["action"] == action_type and data["confidence"] >= 0.6:
                context_triggers.append(trigger)
        
        pattern_id = f"pattern_{user_id}_{action_type}_{datetime.now().timestamp()}"
        
        return BehaviorPattern(
            pattern_id=pattern_id,
            user_id=user_id,
            pattern_type=action_type,
            frequency=frequency,
            typical_times=temporal_data.get("peak_hours", []),
            typical_days=temporal_data.get("peak_days", []),
            context_triggers=context_triggers,
            confidence=confidence,
            last_seen=datetime.now(),
            created_at=datetime.now()
        )
    
    def _calculate_entropy(self, distribution: np.ndarray) -> float:
        """Calculate entropy of a probability distribution."""
        # Add small epsilon to avoid log(0)
        epsilon = 1e-10
        normalized = distribution / (distribution.sum() + epsilon)
        normalized = normalized + epsilon
        
        return -np.sum(normalized * np.log(normalized))

class PredictionEngine:
    """Engine for generating predictions based on learned patterns."""
    
    def __init__(self):
        self.prediction_horizon_hours = 24
        self.confidence_boost_factors = {
            "temporal_match": 0.3,
            "context_match": 0.4,
            "sequence_match": 0.2,
            "frequency_boost": 0.1
        }
    
    def generate_predictions(self, user_id: str, patterns: List[BehaviorPattern], 
                           current_context: Dict[str, Any],
                           recent_actions: List[UserAction]) -> List[Prediction]:
        """Generate predictions based on learned patterns and current context."""
        predictions = []
        current_time = datetime.now()
        
        for pattern in patterns:
            if pattern.user_id != user_id:
                continue
            
            # Check if pattern is still relevant
            if self._is_pattern_stale(pattern, current_time):
                continue
            
            # Predict next occurrence
            prediction = self._predict_from_pattern(
                pattern, current_context, recent_actions, current_time
            )
            
            if prediction:
                predictions.append(prediction)
        
        # Sort by confidence and predicted time
        predictions.sort(key=lambda p: (p.confidence.value, p.predicted_time))
        
        return predictions[:10]  # Return top 10 predictions
    
    def _is_pattern_stale(self, pattern: BehaviorPattern, current_time: datetime) -> bool:
        """Check if pattern is too old to be relevant."""
        days_since_seen = (current_time - pattern.last_seen).days
        return days_since_seen > 30  # Pattern expires after 30 days
    
    def _predict_from_pattern(self, pattern: BehaviorPattern, current_context: Dict[str, Any],
                            recent_actions: List[UserAction], current_time: datetime) -> Optional[Prediction]:
        """Generate prediction from a specific pattern."""
        
        # Calculate when this action is likely to occur next
        predicted_time = self._predict_next_occurrence_time(pattern, current_time)
        
        if not predicted_time:
            return None
        
        # Calculate confidence
        base_confidence = pattern.confidence
        
        # Boost confidence based on context matching
        context_boost = self._calculate_context_boost(pattern, current_context)
        
        # Boost confidence based on recent action sequences
        sequence_boost = self._calculate_sequence_boost(pattern, recent_actions)
        
        # Final confidence
        final_confidence = min(1.0, base_confidence + context_boost + sequence_boost)
        
        # Convert to confidence enum
        if final_confidence >= 0.9:
            confidence_level = PredictionConfidence.VERY_HIGH
        elif final_confidence >= 0.75:
            confidence_level = PredictionConfidence.HIGH
        elif final_confidence >= 0.6:
            confidence_level = PredictionConfidence.MEDIUM
        else:
            confidence_level = PredictionConfidence.LOW
        
        # Generate reasoning
        reasoning = self._generate_reasoning(pattern, context_boost, sequence_boost)
        
        return Prediction(
            user_id=pattern.user_id,
            predicted_action=ActionType(pattern.pattern_type),
            context=current_context,
            confidence=confidence_level,
            predicted_time=predicted_time,
            reasoning=reasoning,
            supporting_patterns=[pattern.pattern_id],
            expires_at=predicted_time + timedelta(hours=2)
        )
    
    def _predict_next_occurrence_time(self, pattern: BehaviorPattern, 
                                    current_time: datetime) -> Optional[datetime]:
        """Predict when the action will next occur based on temporal patterns."""
        
        # Get typical hours and days
        typical_hours = pattern.typical_times
        typical_days = pattern.typical_days
        
        if not typical_hours:
            return None
        
        # Find next occurrence
        current_hour = current_time.hour
        current_day = current_time.weekday()
        
        # Check if we're in a typical time period
        next_times = []
        
        # Today's remaining typical hours
        for hour in typical_hours:
            if hour > current_hour:
                next_time = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)
                next_times.append(next_time)
        
        # Tomorrow's typical hours if today doesn't have good times
        if not next_times or current_day not in typical_days:
            tomorrow = current_time + timedelta(days=1)
            next_day = tomorrow.weekday()
            
            if next_day in typical_days:
                for hour in typical_hours:
                    next_time = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
                    next_times.append(next_time)
        
        # Check frequency to adjust timing
        if pattern.frequency > 1:  # More than once per day
            # Prefer sooner times
            next_times = [t for t in next_times if t <= current_time + timedelta(hours=12)]
        
        return min(next_times) if next_times else None
    
    def _calculate_context_boost(self, pattern: BehaviorPattern, 
                               current_context: Dict[str, Any]) -> float:
        """Calculate confidence boost based on context matching."""
        boost = 0.0
        
        for trigger in pattern.context_triggers:
            if ":" in trigger:
                key, value = trigger.split(":", 1)
                if key in current_context:
                    try:
                        # Handle different value types
                        current_value = str(current_context[key])
                        if current_value == value:
                            boost += self.confidence_boost_factors["context_match"]
                    except:
                        continue
        
        return min(boost, 0.4)  # Cap context boost
    
    def _calculate_sequence_boost(self, pattern: BehaviorPattern, 
                                recent_actions: List[UserAction]) -> float:
        """Calculate confidence boost based on recent action sequences."""
        if not recent_actions:
            return 0.0
        
        # Look at last few actions
        last_actions = [action.action_type.value for action in recent_actions[-3:]]
        
        # This is a simplified sequence matching
        # In a real implementation, you'd use the sequence patterns learned earlier
        sequence_boost = 0.0
        
        # If user just performed actions that typically lead to this pattern
        if len(last_actions) >= 2:
            # Simple heuristic: if user did file operations, they might do more
            if pattern.pattern_type == ActionType.FILE_ACCESS.value:
                if ActionType.FILE_UPLOAD.value in last_actions:
                    sequence_boost += 0.2
        
        return sequence_boost
    
    def _generate_reasoning(self, pattern: BehaviorPattern, context_boost: float, 
                          sequence_boost: float) -> str:
        """Generate human-readable reasoning for the prediction."""
        reasons = []
        
        # Pattern-based reason
        if pattern.frequency >= 1:
            reasons.append(f"You typically {pattern.pattern_type.replace('_', ' ')} daily")
        else:
            reasons.append(f"You {pattern.pattern_type.replace('_', ' ')} regularly")
        
        # Time-based reason
        if pattern.typical_times:
            hours = [f"{h}:00" for h in pattern.typical_times[:2]]
            reasons.append(f"usually around {' or '.join(hours)}")
        
        # Context-based reason
        if context_boost > 0:
            reasons.append("current context matches your usual patterns")
        
        # Sequence-based reason
        if sequence_boost > 0:
            reasons.append("your recent actions suggest this is next")
        
        return ". ".join(reasons).capitalize() + "."

class BehaviorPredictionEngine:
    """Main behavior prediction engine orchestrator."""
    
    def __init__(self):
        self.learning_engine = PatternLearningEngine()
        self.prediction_engine = PredictionEngine()
        self.user_actions = defaultdict(list)
        self.user_patterns = defaultdict(list)
        self.active_predictions = defaultdict(list)
        
        print("🧠 Behavior Prediction Engine initialized")
    
    async def record_action(self, user_id: str, action_type: ActionType, 
                          context: Dict[str, Any], session_id: str,
                          metadata: Dict[str, Any] = None) -> None:
        """Record a user action for learning."""
        action = UserAction(
            user_id=user_id,
            action_type=action_type,
            context=context,
            timestamp=datetime.now(),
            session_id=session_id,
            metadata=metadata or {}
        )
        
        self.user_actions[user_id].append(action)
        
        # Keep only recent actions (last 1000 per user)
        if len(self.user_actions[user_id]) > 1000:
            self.user_actions[user_id] = self.user_actions[user_id][-1000:]
        
        # Trigger pattern learning if we have enough actions
        if len(self.user_actions[user_id]) >= 10:
            await self._update_patterns(user_id)
    
    async def _update_patterns(self, user_id: str) -> None:
        """Update learned patterns for a user."""
        actions = self.user_actions[user_id]
        
        # Learn new patterns
        new_patterns = self.learning_engine.learn_patterns(user_id, actions)
        
        # Update existing patterns or add new ones
        existing_pattern_types = {p.pattern_type for p in self.user_patterns[user_id]}
        
        for pattern in new_patterns:
            # Replace existing pattern of same type or add new
            self.user_patterns[user_id] = [
                p for p in self.user_patterns[user_id] 
                if p.pattern_type != pattern.pattern_type
            ]
            self.user_patterns[user_id].append(pattern)
        
        print(f"🔄 Updated patterns for {user_id}: {len(self.user_patterns[user_id])} total patterns")
    
    async def get_predictions(self, user_id: str, current_context: Dict[str, Any] = None) -> List[Prediction]:
        """Get current predictions for a user."""
        if user_id not in self.user_patterns:
            return []
        
        current_context = current_context or {}
        recent_actions = self.user_actions[user_id][-10:]  # Last 10 actions
        
        predictions = self.prediction_engine.generate_predictions(
            user_id, self.user_patterns[user_id], current_context, recent_actions
        )
        
        # Cache predictions
        self.active_predictions[user_id] = predictions
        
        return predictions
    
    async def get_user_patterns(self, user_id: str) -> List[BehaviorPattern]:
        """Get learned patterns for a user."""
        return self.user_patterns.get(user_id, [])
    
    async def get_pattern_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user behavior patterns."""
        patterns = self.user_patterns.get(user_id, [])
        actions = self.user_actions.get(user_id, [])
        
        if not patterns:
            return {"message": "No patterns learned yet"}
        
        # Analyze pattern insights
        total_patterns = len(patterns)
        avg_confidence = sum(p.confidence for p in patterns) / total_patterns
        
        # Most frequent actions
        action_counts = defaultdict(int)
        for action in actions[-100:]:  # Last 100 actions
            action_counts[action.action_type.value] += 1
        
        most_common = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Temporal analysis
        if actions:
            hours = [a.timestamp.hour for a in actions[-100:]]
            most_active_hour = max(set(hours), key=hours.count)
            
            days = [a.timestamp.weekday() for a in actions[-100:]]
            most_active_day = max(set(days), key=days.count)
        else:
            most_active_hour = None
            most_active_day = None
        
        return {
            "total_patterns": total_patterns,
            "average_confidence": round(avg_confidence, 2),
            "total_actions_recorded": len(actions),
            "most_common_actions": most_common,
            "most_active_hour": most_active_hour,
            "most_active_day": most_active_day,
            "pattern_types": [p.pattern_type for p in patterns]
        }

# CLI interface for testing
async def main():
    """CLI interface for Behavior Prediction Engine testing."""
    engine = BehaviorPredictionEngine()
    
    print("🧠 Behavior Prediction Engine Test Suite")
    print("=" * 50)
    
    # Test 1: Record various user actions
    print("\n1. Recording user actions...")
    
    user_id = "test_user"
    session_id = "session_123"
    
    # Simulate a typical user session
    actions_to_record = [
        (ActionType.MODULE_USE, {"module": "fishing", "time_spent": 300}),
        (ActionType.FILE_UPLOAD, {"file_type": "image", "module": "fishing"}),
        (ActionType.FILE_ACCESS, {"file_type": "image", "action": "view"}),
        (ActionType.SEARCH_QUERY, {"query": "fishing gear", "module": "fishing"}),
        (ActionType.DATA_ENTRY, {"type": "catch_log", "module": "fishing"}),
    ]
    
    for action_type, context in actions_to_record:
        await engine.record_action(user_id, action_type, context, session_id)
    
    print(f"✅ Recorded {len(actions_to_record)} actions")
    
    # Test 2: Simulate more actions over time to build patterns
    print("\n2. Simulating pattern-building actions...")
    
    # Simulate daily fishing module usage for pattern learning
    for day in range(7):
        for hour in [9, 14, 18]:  # 9 AM, 2 PM, 6 PM
            session_id = f"session_{day}_{hour}"
            
            await engine.record_action(
                user_id, ActionType.MODULE_USE,
                {"module": "fishing", "time_spent": 180 + random.randint(-60, 60)},
                session_id
            )
            
            await engine.record_action(
                user_id, ActionType.FILE_ACCESS,
                {"file_type": "catch_log", "action": "review"},
                session_id
            )
    
    print("✅ Simulated 7 days of fishing activity")
    
    # Test 3: Get predictions
    print("\n3. Getting predictions...")
    
    current_context = {
        "current_time": datetime.now().hour,
        "current_module": "fishing",
        "recent_activity": "login"
    }
    
    predictions = await engine.get_predictions(user_id, current_context)
    
    print(f"✅ Generated {len(predictions)} predictions:")
    for i, prediction in enumerate(predictions[:3], 1):
        print(f"   {i}. {prediction.predicted_action.value} at {prediction.predicted_time.strftime('%H:%M')}")
        print(f"      Confidence: {prediction.confidence.value}")
        print(f"      Reasoning: {prediction.reasoning}")
    
    # Test 4: Get user patterns
    print("\n4. Analyzing learned patterns...")
    
    patterns = await engine.get_user_patterns(user_id)
    print(f"✅ Learned {len(patterns)} behavior patterns:")
    for pattern in patterns:
        print(f"   - {pattern.pattern_type}: {pattern.confidence:.2f} confidence")
        print(f"     Typical times: {pattern.typical_times}")
        print(f"     Frequency: {pattern.frequency:.2f}/day")
    
    # Test 5: Get pattern insights
    print("\n5. Getting pattern insights...")
    
    insights = await engine.get_pattern_insights(user_id)
    if "message" not in insights:
        print(f"✅ Pattern insights:")
        print(f"   - Total patterns: {insights['total_patterns']}")
        print(f"   - Average confidence: {insights['average_confidence']}")
        print(f"   - Total actions: {insights['total_actions_recorded']}")
        print(f"   - Most common: {insights['most_common_actions'][:3]}")
        print(f"   - Most active hour: {insights['most_active_hour']}:00")
    
    print("\n🎉 Behavior Prediction Engine tests completed!")

if __name__ == "__main__":
    asyncio.run(main())