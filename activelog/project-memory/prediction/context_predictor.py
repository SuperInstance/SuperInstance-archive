"""
ActiveLog Project Memory - Context Prediction Engine
AI-powered predictive loading with pattern recognition and preemptive caching
"""

from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import numpy as np
import time
import hashlib
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque, Counter
import pickle
import math

class PredictionType(Enum):
    """Types of predictions the engine can make"""
    CONCEPT_ACCESS = "concept_access"      # Which concepts will be accessed next
    CONTEXT_EXPANSION = "context_expand"   # When context will need expansion
    BOT_CAPABILITY = "bot_capability"      # What bot capabilities will be needed
    CATEGORY_SEARCH = "category_search"    # What categories will be searched
    DOCUMENTATION_REQUEST = "doc_request"  # What documentation will be needed

class PredictionConfidence(Enum):
    """Confidence levels for predictions"""
    VERY_HIGH = 0.9   # Almost certain (>90%)
    HIGH = 0.75       # Very likely (75-90%)
    MEDIUM = 0.5      # Possible (50-75%)
    LOW = 0.25        # Unlikely (25-50%)
    VERY_LOW = 0.1    # Very unlikely (<25%)

@dataclass
class PredictionResult:
    """Result of a prediction operation"""
    prediction_type: PredictionType
    predicted_items: List[str]
    confidence: float
    reasoning: str
    context_factors: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expiry_time: Optional[datetime] = None

@dataclass
class ContextSession:
    """Represents a bot's context session for tracking"""
    session_id: str
    bot_type: str
    start_time: datetime
    last_activity: datetime
    accessed_concepts: List[str] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)
    task_context: Dict[str, Any] = field(default_factory=dict)
    predicted_needs: List[PredictionResult] = field(default_factory=list)

class PatternMatcher:
    """Identifies patterns in user behavior for prediction"""
    
    def __init__(self, pattern_window: int = 100):
        self.pattern_window = pattern_window
        self.sequence_patterns = defaultdict(list)
        self.temporal_patterns = defaultdict(list)
        self.categorical_patterns = defaultdict(list)
        
    def learn_sequence_pattern(self, sequence: List[str], next_item: str):
        """Learn from access sequences"""
        if len(sequence) >= 2:
            # Learn from different sequence lengths
            for length in range(2, min(6, len(sequence) + 1)):
                pattern = tuple(sequence[-length:])
                self.sequence_patterns[pattern].append(next_item)
                
                # Limit pattern storage
                if len(self.sequence_patterns[pattern]) > self.pattern_window:
                    self.sequence_patterns[pattern].pop(0)
    
    def learn_temporal_pattern(self, hour: int, day_of_week: int, accessed_item: str):
        """Learn from time-based patterns"""
        time_pattern = (hour, day_of_week)
        self.temporal_patterns[time_pattern].append(accessed_item)
        
        if len(self.temporal_patterns[time_pattern]) > self.pattern_window:
            self.temporal_patterns[time_pattern].pop(0)
    
    def learn_categorical_pattern(self, category: str, task_type: str, accessed_item: str):
        """Learn from category and task patterns"""
        cat_pattern = (category, task_type)
        self.categorical_patterns[cat_pattern].append(accessed_item)
        
        if len(self.categorical_patterns[cat_pattern]) > self.pattern_window:
            self.categorical_patterns[cat_pattern].pop(0)
    
    def predict_from_sequence(self, sequence: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """Predict next items based on sequence patterns"""
        predictions = defaultdict(float)
        
        # Try different sequence lengths
        for length in range(2, min(6, len(sequence) + 1)):
            if len(sequence) >= length:
                pattern = tuple(sequence[-length:])
                
                if pattern in self.sequence_patterns:
                    candidates = self.sequence_patterns[pattern]
                    candidate_counts = Counter(candidates)
                    
                    # Calculate probabilities with length weighting
                    weight = length * 0.2  # Longer patterns get more weight
                    total_count = len(candidates)
                    
                    for item, count in candidate_counts.items():
                        probability = (count / total_count) * weight
                        predictions[item] += probability
        
        # Normalize and return top predictions
        if predictions:
            max_score = max(predictions.values())
            normalized_predictions = [
                (item, score / max_score) for item, score in predictions.items()
            ]
            
            return sorted(normalized_predictions, key=lambda x: x[1], reverse=True)[:top_k]
        
        return []
    
    def predict_from_time(self, current_hour: int, current_day: int, 
                         top_k: int = 5) -> List[Tuple[str, float]]:
        """Predict based on temporal patterns"""
        time_pattern = (current_hour, current_day)
        
        if time_pattern in self.temporal_patterns:
            candidates = self.temporal_patterns[time_pattern]
            candidate_counts = Counter(candidates)
            
            total_count = len(candidates)
            predictions = [
                (item, count / total_count) 
                for item, count in candidate_counts.items()
            ]
            
            return sorted(predictions, key=lambda x: x[1], reverse=True)[:top_k]
        
        return []
    
    def predict_from_category(self, category: str, task_type: str,
                            top_k: int = 5) -> List[Tuple[str, float]]:
        """Predict based on categorical patterns"""
        cat_pattern = (category, task_type)
        
        if cat_pattern in self.categorical_patterns:
            candidates = self.categorical_patterns[cat_pattern]
            candidate_counts = Counter(candidates)
            
            total_count = len(candidates)
            predictions = [
                (item, count / total_count)
                for item, count in candidate_counts.items()
            ]
            
            return sorted(predictions, key=lambda x: x[1], reverse=True)[:top_k]
        
        return []

class ContextPredictor:
    """
    Advanced context prediction engine with multiple prediction strategies
    """
    
    def __init__(self, max_sessions: int = 1000):
        self.max_sessions = max_sessions
        self.active_sessions: Dict[str, ContextSession] = {}
        self.pattern_matcher = PatternMatcher()
        
        # Prediction models
        self.concept_transition_matrix = defaultdict(lambda: defaultdict(float))
        self.bot_behavior_profiles = defaultdict(lambda: {
            "preferred_categories": Counter(),
            "average_session_length": 0,
            "common_patterns": [],
            "complexity_preference": "medium"
        })
        
        # Performance tracking
        self.prediction_accuracy = defaultdict(float)
        self.prediction_history = deque(maxlen=1000)
        
        # Preloading components
        self.preload_queue = asyncio.Queue()
        self.preload_callbacks: Dict[str, Callable] = {}
        self.preload_cache = {}
        
    async def start_session(self, session_id: str, bot_type: str, 
                           task_context: Dict[str, Any]) -> ContextSession:
        """Start tracking a new context session"""
        
        session = ContextSession(
            session_id=session_id,
            bot_type=bot_type,
            start_time=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            task_context=task_context
        )
        
        self.active_sessions[session_id] = session
        
        # Make initial predictions based on session start
        await self._make_session_start_predictions(session)
        
        # Clean up old sessions if needed
        if len(self.active_sessions) > self.max_sessions:
            await self._cleanup_old_sessions()
        
        return session
    
    async def record_access(self, session_id: str, concept_id: str, 
                          category: str, context: Dict[str, Any]):
        """Record concept access for learning and prediction"""
        
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session.accessed_concepts.append(concept_id)
        session.last_activity = datetime.now(timezone.utc)
        
        # Learn patterns from this access
        await self._learn_from_access(session, concept_id, category, context)
        
        # Make new predictions based on this access
        await self._update_session_predictions(session, concept_id, category)
        
        # Trigger preemptive loading
        await self._trigger_preemptive_loading(session)
    
    async def record_search(self, session_id: str, query: str, 
                          results: List[str], context: Dict[str, Any]):
        """Record search activity for pattern learning"""
        
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session.search_queries.append(query)
        session.last_activity = datetime.now(timezone.utc)
        
        # Learn from search patterns
        await self._learn_from_search(session, query, results, context)
        
        # Update predictions based on search
        await self._update_search_predictions(session, query, results)
    
    async def predict_next_concepts(self, session_id: str, 
                                  count: int = 5) -> List[PredictionResult]:
        """Predict which concepts the bot will likely access next"""
        
        if session_id not in self.active_sessions:
            return []
        
        session = self.active_sessions[session_id]
        predictions = []
        
        # Strategy 1: Sequence-based prediction
        if session.accessed_concepts:
            sequence_predictions = self.pattern_matcher.predict_from_sequence(
                session.accessed_concepts, count
            )
            
            if sequence_predictions:
                predictions.append(PredictionResult(
                    prediction_type=PredictionType.CONCEPT_ACCESS,
                    predicted_items=[item for item, _ in sequence_predictions],
                    confidence=max(score for _, score in sequence_predictions),
                    reasoning="Based on recent access sequence pattern",
                    context_factors={
                        "sequence_length": len(session.accessed_concepts),
                        "pattern_strength": sequence_predictions[0][1] if sequence_predictions else 0
                    }
                ))
        
        # Strategy 2: Category-based prediction
        if session.task_context.get("task_type"):
            category_predictions = self.pattern_matcher.predict_from_category(
                session.task_context.get("current_category", ""),
                session.task_context["task_type"],
                count
            )
            
            if category_predictions:
                predictions.append(PredictionResult(
                    prediction_type=PredictionType.CATEGORY_SEARCH,
                    predicted_items=[item for item, _ in category_predictions],
                    confidence=max(score for _, score in category_predictions),
                    reasoning="Based on task category patterns",
                    context_factors={
                        "task_type": session.task_context["task_type"],
                        "category": session.task_context.get("current_category", "")
                    }
                ))
        
        # Strategy 3: Bot behavior profile prediction
        bot_profile = self.bot_behavior_profiles[session.bot_type]
        if bot_profile["common_patterns"]:
            profile_predictions = await self._predict_from_bot_profile(session, bot_profile, count)
            if profile_predictions:
                predictions.extend(profile_predictions)
        
        # Strategy 4: Temporal prediction
        now = datetime.now(timezone.utc)
        temporal_predictions = self.pattern_matcher.predict_from_time(
            now.hour, now.weekday(), count
        )
        
        if temporal_predictions:
            predictions.append(PredictionResult(
                prediction_type=PredictionType.CONCEPT_ACCESS,
                predicted_items=[item for item, _ in temporal_predictions],
                confidence=max(score for _, score in temporal_predictions) * 0.5,  # Lower weight for time
                reasoning="Based on temporal access patterns",
                context_factors={
                    "hour": now.hour,
                    "day_of_week": now.weekday()
                }
            ))
        
        return sorted(predictions, key=lambda x: x.confidence, reverse=True)
    
    async def predict_context_expansion(self, session_id: str) -> Optional[PredictionResult]:
        """Predict when context will need expansion"""
        
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        # Calculate expansion probability based on factors
        factors = {
            "session_age": (datetime.now(timezone.utc) - session.start_time).total_seconds(),
            "concepts_accessed": len(session.accessed_concepts),
            "search_queries": len(session.search_queries),
            "complexity_trend": await self._calculate_complexity_trend(session)
        }
        
        # Simple heuristic for expansion prediction
        expansion_probability = 0
        
        # More concepts accessed = higher chance of expansion
        if factors["concepts_accessed"] > 10:
            expansion_probability += 0.3
        
        # Multiple searches suggest expanding needs
        if factors["search_queries"] > 3:
            expansion_probability += 0.25
        
        # Increasing complexity suggests need for more context
        if factors["complexity_trend"] > 0.5:
            expansion_probability += 0.2
        
        # Longer sessions more likely to expand
        if factors["session_age"] > 1800:  # 30 minutes
            expansion_probability += 0.15
        
        if expansion_probability > 0.5:
            return PredictionResult(
                prediction_type=PredictionType.CONTEXT_EXPANSION,
                predicted_items=["context_expansion_needed"],
                confidence=min(expansion_probability, 0.95),
                reasoning="Session patterns indicate context expansion will be needed",
                context_factors=factors
            )
        
        return None
    
    async def predict_bot_capability_needs(self, session_id: str) -> List[PredictionResult]:
        """Predict what bot capabilities will be needed"""
        
        if session_id not in self.active_sessions:
            return []
        
        session = self.active_sessions[session_id]
        predictions = []
        
        # Analyze current session to predict capabilities
        task_type = session.task_context.get("task_type", "")
        
        capability_mappings = {
            "api": ["advanced", "technical_analysis"],
            "development": ["expert", "code_generation"],
            "business": ["intermediate", "data_analysis"],
            "troubleshooting": ["expert", "debugging"],
            "documentation": ["intermediate", "explanation"]
        }
        
        if task_type in capability_mappings:
            predicted_capabilities = capability_mappings[task_type]
            
            predictions.append(PredictionResult(
                prediction_type=PredictionType.BOT_CAPABILITY,
                predicted_items=predicted_capabilities,
                confidence=0.7,
                reasoning=f"Task type '{task_type}' typically requires these capabilities",
                context_factors={
                    "current_bot_type": session.bot_type,
                    "task_type": task_type
                }
            ))
        
        return predictions
    
    async def _learn_from_access(self, session: ContextSession, concept_id: str,
                               category: str, context: Dict[str, Any]):
        """Learn patterns from concept access"""
        
        # Update sequence patterns
        if len(session.accessed_concepts) > 1:
            previous_concepts = session.accessed_concepts[:-1]  # All but the last (current)
            self.pattern_matcher.learn_sequence_pattern(previous_concepts, concept_id)
        
        # Update temporal patterns
        now = datetime.now(timezone.utc)
        self.pattern_matcher.learn_temporal_pattern(now.hour, now.weekday(), concept_id)
        
        # Update categorical patterns
        task_type = session.task_context.get("task_type", "unknown")
        self.pattern_matcher.learn_categorical_pattern(category, task_type, concept_id)
        
        # Update bot behavior profile
        profile = self.bot_behavior_profiles[session.bot_type]
        profile["preferred_categories"][category] += 1
        
        # Update concept transition matrix
        if len(session.accessed_concepts) > 1:
            prev_concept = session.accessed_concepts[-2]
            self.concept_transition_matrix[prev_concept][concept_id] += 1
    
    async def _learn_from_search(self, session: ContextSession, query: str,
                               results: List[str], context: Dict[str, Any]):
        """Learn from search patterns"""
        
        # Extract keywords from query for pattern learning
        query_keywords = query.lower().split()
        
        # Associate search terms with result categories
        for result_id in results[:3]:  # Top 3 results
            for keyword in query_keywords:
                if len(keyword) > 3:  # Skip short words
                    self.pattern_matcher.learn_sequence_pattern([keyword], result_id)
    
    async def _make_session_start_predictions(self, session: ContextSession):
        """Make initial predictions when session starts"""
        
        # Predict based on bot type and task context
        bot_profile = self.bot_behavior_profiles[session.bot_type]
        
        if bot_profile["preferred_categories"]:
            # Predict initial categories of interest
            top_categories = bot_profile["preferred_categories"].most_common(3)
            
            prediction = PredictionResult(
                prediction_type=PredictionType.CATEGORY_SEARCH,
                predicted_items=[cat for cat, _ in top_categories],
                confidence=0.6,
                reasoning="Based on bot type historical preferences",
                context_factors={
                    "bot_type": session.bot_type,
                    "historical_preferences": dict(top_categories)
                }
            )
            
            session.predicted_needs.append(prediction)
    
    async def _update_session_predictions(self, session: ContextSession,
                                        concept_id: str, category: str):
        """Update predictions based on new access"""
        
        # Remove expired predictions
        current_time = datetime.now(timezone.utc)
        session.predicted_needs = [
            pred for pred in session.predicted_needs
            if not pred.expiry_time or pred.expiry_time > current_time
        ]
        
        # Make new predictions based on current access
        new_predictions = await self.predict_next_concepts(session.session_id, 3)
        
        # Add predictions with expiry times
        for prediction in new_predictions:
            prediction.expiry_time = current_time + timedelta(minutes=30)
            session.predicted_needs.append(prediction)
    
    async def _update_search_predictions(self, session: ContextSession,
                                       query: str, results: List[str]):
        """Update predictions based on search activity"""
        
        # Predict follow-up searches
        if results:
            prediction = PredictionResult(
                prediction_type=PredictionType.DOCUMENTATION_REQUEST,
                predicted_items=results[:3],
                confidence=0.5,
                reasoning="Likely to request documentation for search results",
                context_factors={
                    "search_query": query,
                    "result_count": len(results)
                },
                expiry_time=datetime.now(timezone.utc) + timedelta(minutes=15)
            )
            
            session.predicted_needs.append(prediction)
    
    async def _predict_from_bot_profile(self, session: ContextSession,
                                      bot_profile: Dict[str, Any],
                                      count: int) -> List[PredictionResult]:
        """Predict based on bot behavioral profile"""
        
        predictions = []
        
        # Predict based on complexity preference
        complexity_pref = bot_profile.get("complexity_preference", "medium")
        
        if complexity_pref == "high" and len(session.accessed_concepts) > 5:
            predictions.append(PredictionResult(
                prediction_type=PredictionType.CONTEXT_EXPANSION,
                predicted_items=["advanced_concepts", "technical_documentation"],
                confidence=0.65,
                reasoning="High-complexity bot likely to need advanced concepts",
                context_factors={
                    "complexity_preference": complexity_pref,
                    "session_depth": len(session.accessed_concepts)
                }
            ))
        
        return predictions
    
    async def _calculate_complexity_trend(self, session: ContextSession) -> float:
        """Calculate if session complexity is increasing"""
        
        if len(session.accessed_concepts) < 3:
            return 0.5
        
        # Simple heuristic: more concepts = higher complexity
        early_concepts = len(session.accessed_concepts[:len(session.accessed_concepts)//2])
        late_concepts = len(session.accessed_concepts[len(session.accessed_concepts)//2:])
        
        if early_concepts == 0:
            return 1.0
        
        return min(1.0, late_concepts / early_concepts)
    
    async def _trigger_preemptive_loading(self, session: ContextSession):
        """Trigger preemptive loading of predicted concepts"""
        
        # Get high-confidence predictions
        predictions = await self.predict_next_concepts(session.session_id, 3)
        
        for prediction in predictions:
            if prediction.confidence > 0.7:
                for item in prediction.predicted_items[:2]:  # Top 2 items
                    if item not in self.preload_cache:
                        await self.preload_queue.put((session.session_id, item, prediction.confidence))
    
    async def _cleanup_old_sessions(self):
        """Clean up old inactive sessions"""
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=2)
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if session.last_activity < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            # Store final patterns before removing
            session = self.active_sessions[session_id]
            await self._finalize_session_learning(session)
            del self.active_sessions[session_id]
    
    async def _finalize_session_learning(self, session: ContextSession):
        """Extract final learning from completed session"""
        
        # Update bot profile with session data
        profile = self.bot_behavior_profiles[session.bot_type]
        
        session_duration = (session.last_activity - session.start_time).total_seconds()
        
        # Update average session length
        if profile["average_session_length"] == 0:
            profile["average_session_length"] = session_duration
        else:
            profile["average_session_length"] = (
                profile["average_session_length"] * 0.9 + session_duration * 0.1
            )
        
        # Extract common patterns from this session
        if len(session.accessed_concepts) > 3:
            for i in range(len(session.accessed_concepts) - 2):
                pattern = tuple(session.accessed_concepts[i:i+3])
                if pattern not in profile["common_patterns"]:
                    profile["common_patterns"].append(pattern)
    
    def register_preload_callback(self, prediction_type: PredictionType,
                                callback: Callable[[str, float], Any]):
        """Register callback for preemptive loading"""
        self.preload_callbacks[prediction_type.value] = callback
    
    async def start_preload_worker(self):
        """Start background worker for preemptive loading"""
        while True:
            try:
                session_id, item_id, confidence = await self.preload_queue.get()
                
                # Only preload high-confidence predictions
                if confidence > 0.75:
                    # Check if we have a callback for this type
                    for callback in self.preload_callbacks.values():
                        try:
                            result = await callback(item_id, confidence)
                            if result:
                                self.preload_cache[item_id] = {
                                    "data": result,
                                    "loaded_at": datetime.now(timezone.utc),
                                    "confidence": confidence
                                }
                        except Exception as e:
                            # Log error but continue
                            pass
                
            except Exception as e:
                await asyncio.sleep(1)
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific session"""
        
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "bot_type": session.bot_type,
            "duration_minutes": (
                session.last_activity - session.start_time
            ).total_seconds() / 60,
            "concepts_accessed": len(session.accessed_concepts),
            "search_queries": len(session.search_queries),
            "active_predictions": len(session.predicted_needs),
            "high_confidence_predictions": len([
                p for p in session.predicted_needs if p.confidence > 0.7
            ]),
            "last_activity": session.last_activity.isoformat()
        }
    
    def get_prediction_analytics(self) -> Dict[str, Any]:
        """Get comprehensive prediction analytics"""
        
        return {
            "active_sessions": len(self.active_sessions),
            "total_patterns_learned": (
                len(self.pattern_matcher.sequence_patterns) +
                len(self.pattern_matcher.temporal_patterns) +
                len(self.pattern_matcher.categorical_patterns)
            ),
            "bot_profiles": len(self.bot_behavior_profiles),
            "preload_cache_size": len(self.preload_cache),
            "prediction_types": {
                pred_type.value: len([
                    p for session in self.active_sessions.values()
                    for p in session.predicted_needs
                    if p.prediction_type == pred_type
                ]) for pred_type in PredictionType
            },
            "average_confidence": (
                sum(p.confidence for session in self.active_sessions.values()
                    for p in session.predicted_needs) /
                max(1, sum(len(session.predicted_needs) 
                          for session in self.active_sessions.values()))
            )
        }